"""
웹 배포용 경량 papers.json 생성
--------------------------------
all_enriched.json에서 필요한 필드만 추출하고 abstracts를 truncate해
파일 크기를 GitHub 100MB 제한 이내로 줄입니다.

Output: ../papers.json
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from venues_config import VENUES_CFG

IN_FILE  = Path(__file__).parent / "all_enriched.json"
OUT_FILE = Path(__file__).parent.parent / "papers.json"

LABEL_TO_ID = {v["label"]: v["id"] for v in VENUES_CFG}
ABSTRACT_LIMIT = 400   # 초록 최대 글자 수 (키워드 검색용)
MAX_AUTHORS    = 5     # 저자 최대 표시 수

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
    r"|^Index\b"                                  # "Index to ..."
    r"|^(Front\s+Matter|Back\s+Matter)"           # 표지/후면
    r"|^(Front|Back|Inside)\s+(Cover|Matter)\b"   # Front Cover, Back Cover 등
    r"|^Cover\s+(Page|Image)\b"                   # Cover Page, Cover Image
    r"|^Table\s+of\s+Contents"                    # 목차
    r"|^(Errata|Erratum|Correction\s+to\b)"       # 정오표
    r"|^(Obituary|In\s+Memoriam)\b"               # 부고
    r"|^Masthead\b"                               # 판권면
    r"|^</",                                      # XML 오염 레코드 (</title> 등으로 시작)
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
        authors = authors_raw[:MAX_AUTHORS]
    else:
        authors = str(authors_raw or "").split("; ")[:MAX_AUTHORS]

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


def main():
    print(f"Loading {IN_FILE}…")
    with open(IN_FILE, encoding="utf-8") as f:
        papers = json.load(f)
    print(f"  {len(papers):,} papers")

    before = len(papers)
    papers = [p for p in papers if not is_junk(p)]
    print(f"  비논문 항목 제거: {before - len(papers):,}개 제외 → {len(papers):,}개 남음")
    slimmed = [slim(p) for p in papers]

    # 최소 분리자로 직렬화 (공백 없음)
    out = json.dumps(slimmed, ensure_ascii=False, separators=(",", ":"))

    size_mb = len(out.encode("utf-8")) / 1024 / 1024
    print(f"  Slim JSON: {size_mb:.1f} MB")

    OUT_FILE.write_text(out, encoding="utf-8")
    print(f"✓ {OUT_FILE}")


if __name__ == "__main__":
    main()
