"""
웹 배포용 데이터 파일 생성
---------------------------
all_enriched.json에서 비논문을 걸러내고, 사이트가 읽는 파일을 만든다.

    data/meta.json      빌드 ID·갱신일·논문 수·저널 목록 (사이트의 헤더·사이드바가 이걸 읽음)
    data/core.json.gz   제목·저자·연도·인용수·저널 — 이것만 받으면 검색 시작
    data/doi.json.gz    DOI
    data/abs.json.gz    초록(앞 ABSTRACT_LIMIT자) — 뒤에서 이어받음
    papers.json         로컬 도구용 행 단위 사본 (배포 안 함)

세 데이터 파일은 같은 순서(최신순)의 배열이라 순번으로 서로 맞춘다.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from venues_config import VENUES_CFG, CATEGORY_COLORS

IN_FILE  = Path(__file__).parent / "all_enriched.json"
OUT_FILE = Path(__file__).parent.parent / "papers.json"
DATA_DIR = Path(__file__).parent.parent / "data"

LABEL_TO_ID = {v["label"]: v["id"] for v in VENUES_CFG}
# 초록은 화면에 표시하지 않고 키워드 검색·Excel에만 쓴다. 길수록 검색 재현율은 오르지만
# 브라우저 메모리(원문 + 검색용 정규화본)가 2배로 늘어난다.
ABSTRACT_LIMIT = 600
# 저자는 자르지 않는다. 교신저자는 대개 마지막이라, 앞 N명만 남기면 저자 검색에 구멍이 생긴다.

import re
import html as html_mod

# ── HTML 정제 ────────────────────────────────────────────────────────────
# <inline-formula> 및 <formula> 블록 제거
_FORMULA_BLOCK = re.compile(
    r'<(inline-formula|formula)\b[^>]*>.*?</(inline-formula|formula)>',
    re.IGNORECASE | re.DOTALL,
)
_HTML_TAG    = re.compile(r'<[^>]+>')
_MULTI_SPACE = re.compile(r'\s{2,}')

def clean_title(title: str) -> str:
    if not title:
        return ''
    # 1. HTML 엔티티 먼저 디코딩 (&lt;inline-formula&gt; → <inline-formula>)
    title = html_mod.unescape(title)
    # 2. 수식 블록 제거 (<inline-formula>, <formula>)
    title = _FORMULA_BLOCK.sub('', title)
    # 3. 남은 HTML 태그 제거 (<b>, <i>, <tex>, <italic> 등)
    title = _HTML_TAG.sub('', title)
    # 4. 한 번 더 엔티티 디코딩 (이중 인코딩 대응)
    title = html_mod.unescape(title)
    # 5. 연속 공백 정리
    title = _MULTI_SPACE.sub(' ', title).strip()
    return title

# ── 비논문 필터 ──────────────────────────────────────────────────────────
_JUNK_PATTERNS = re.compile(
    r"^\s*$"                                      # 빈 제목
    r"|^\[.*?(cover|contents|index|masthead|blank|erratum|errata)\b.*?\]$"  # [Cover page], [Back cover] 등
    r"|^\[?Blank\s+[Pp]age\]?"                    # Blank Page
    r"|^\d{4}\s+(Index|IEEE\b)"                   # "2004 Index", "2006 IEEE International..."
    r"|^Index$|^Index\s+(to|for\s+vol|of\s+(authors|papers))\b|^\[front\s+matter\]$"                                  # "Index to ..."
    r"|^(Front\s+Matter|Back\s+Matter)"           # 표지/후면
    r"|^(Front|Back|Inside)\s+(Cover|Matter)\b"   # Front Cover, Back Cover 등
    r"|^Cover\s+(Page|Image)\b"                   # Cover Page, Cover Image
    r"|^Table\s+of\s+Contents"                    # 목차
    r"|^(Errata|Erratum|Correction\s+to\b)"       # 정오표
    r"|^(Obituary|In\s+Memoriam)\b"               # 부고
    r"|^Masthead\b"                               # 판권면
    r"|^</"                                       # XML 오염 레코드 (</title> 등으로 시작)
    # ── 학회 프로시딩 부속물 ──
    r"|^authors?'?\s+index|^(keyword|categor(y|ies)'?|subject)\s+index"
    r"|^(conference\s+)?(organi[sz]ing\s+|technical\s+program\s+|program\s+|steering\s+)?committees?(\s+of.*)?$"
    r"|^breaker\s+page|^\[?copyright(\s+(page|notice))?\]?$|^\[?title\s+page\]?$"
    r"|^(preface|foreword|sponsors?|schedule|program|cover|top\s+menu|content\s+list)$"
    r"|^front-?cover|^.*cover\s+page$|^program\s+at\s+a\s+glance|^welcome(\s+message)?$|^message\s+from"
    r"|^workshops\s+and\s+tutorials$|^plenary\s+and\s+keynote\s+talks$|^(list\s+of\s+)?reviewers?(\s+list)?$"
    r"|^organi[sz]ation\s+of\s+(the\s+)?(ieee|\d{4})|^proceedings\s+\d{4}|^(\d{4}\s+)?ieee(/\w+)?\s+international\s+conference\s+on"
    r"|^ieee\s+icra-\d{4}$",
    re.IGNORECASE,
)

# NICT/JST 기계번역 레코드 감지 (제목 끝에 붙는 태그)
_MACHINE_TRANS = re.compile(
    r"【Powered\s+by\s+NICT】"
    r"|【JST[・･]京大機械翻訳】"
    r"|【機械翻訳】",
)

# 비영어 스크립트 감지 (목표 저널은 전부 영어 출판)
_HIRAGANA_KATAKANA = re.compile(r'[぀-ヿ]')   # 히라가나·가타카나
_ARABIC_CHAR       = re.compile(r'[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]')

def has_non_english_script(title: str) -> bool:
    if _HIRAGANA_KATAKANA.search(title):
        return True
    arabic_count = len(_ARABIC_CHAR.findall(title))
    if arabic_count > 3 and arabic_count / max(len(title), 1) > 0.2:
        return True
    return False

def is_junk(p: dict) -> bool:
    title = clean_title(p.get("title") or "")
    if not title:
        return True
    if _JUNK_PATTERNS.search(title):
        return True
    if _MACHINE_TRANS.search(title):
        return True
    if has_non_english_script(title):
        return True
    return False


def slim(p: dict) -> dict:
    authors_raw = p.get("authors", [])
    if isinstance(authors_raw, list):
        authors = [a for a in authors_raw if a]
    else:
        authors = [a for a in str(authors_raw or "").split("; ") if a]

    abstract = (p.get("abstract") or "").strip()
    if len(abstract) > ABSTRACT_LIMIT:
        abstract = abstract[:ABSTRACT_LIMIT] + "…"

    venue = p.get("venue", "")
    return {
        "v":  LABEL_TO_ID.get(venue, venue.lower()),
        "j":  venue,
        "y":  int(p.get("year") or 0),
        "t":  clean_title(p.get("title") or ""),
        "a":  authors,
        "d":  (p.get("doi") or "").strip(),
        "c":  int(p.get("citation_count") or 0),
        "ab": abstract,
    }


def _gz(obj) -> bytes:
    import gzip
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return gzip.compress(raw, compresslevel=9, mtime=0)   # mtime=0 → 같은 내용이면 같은 바이트


def main():
    import datetime
    import hashlib

    print(f"Loading {IN_FILE}…")
    with open(IN_FILE, encoding="utf-8") as f:
        papers = json.load(f)
    print(f"  {len(papers):,} papers")

    before = len(papers)
    papers = [p for p in papers if not is_junk(p)]
    print(f"  비논문 항목 제거: {before - len(papers):,}개 제외 → {len(papers):,}개 남음")
    slimmed = [slim(p) for p in papers]
    # 기본 화면(최신순)과 같은 순서로 저장
    slimmed.sort(key=lambda p: (-p["y"], -p["c"]))

    # 로컬 도구(eda.py, 검증 스크립트)용 행 단위 JSON — 배포하지 않음
    OUT_FILE.write_text(json.dumps(slimmed, ensure_ascii=False, separators=(",", ":")),
                        encoding="utf-8")
    print(f"✓ {OUT_FILE} (로컬용)")

    # ── 웹 배포용: 열 단위로 3개 파일 ────────────────────────────────────────
    # 사이트는 core만 받으면 바로 검색할 수 있고, doi·abs는 뒤에서 이어받는다.
    # 첫 화면까지 받아야 하는 양을 줄이는 것이 목적이므로 core는 작게 유지할 것.
    cfg = [v for v in VENUES_CFG]
    vidx = {v["id"]: i for i, v in enumerate(cfg)}
    core = {
        "v": [vidx[p["v"]] for p in slimmed],          # venues 목록의 인덱스
        "y": [p["y"] for p in slimmed],
        "c": [p["c"] for p in slimmed],
        "t": [p["t"] for p in slimmed],
        "a": ["; ".join(p["a"]) for p in slimmed],
    }
    files = {
        "core": _gz(core),
        "doi":  _gz([p["d"] for p in slimmed]),
        "abs":  _gz([p["ab"] for p in slimmed]),
    }
    DATA_DIR.mkdir(exist_ok=True)
    h = hashlib.sha1()
    for name in ("core", "doi", "abs"):
        (DATA_DIR / f"{name}.json.gz").write_bytes(files[name])
        h.update(files[name])
        print(f"✓ data/{name}.json.gz  {len(files[name])/1024/1024:5.1f} MB")

    counts = {}
    for p in slimmed:
        counts[p["v"]] = counts.get(p["v"], 0) + 1
    meta = {
        "build":   h.hexdigest()[:12],                  # 캐시 무효화 키
        "updated": datetime.date.today().isoformat(),
        "papers":  len(slimmed),
        "with_abstract": sum(1 for p in slimmed if p["ab"]),
        "files":   {n: {"name": f"{n}.json.gz", "bytes": len(b)} for n, b in files.items()},
        "categories": [{"name": k, "color": c} for k, c in CATEGORY_COLORS.items()],
        "venues":  [{"id": v["id"], "label": v["label"], "color": v["color"],
                     "category": v["category"], "n": counts.get(v["id"], 0)} for v in cfg],
    }
    (DATA_DIR / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    print(f"✓ data/meta.json  build={meta['build']}  {meta['papers']:,} papers, "
          f"초록 {meta['with_abstract']:,}편")


if __name__ == "__main__":
    main()
