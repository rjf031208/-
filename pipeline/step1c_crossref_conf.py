"""
Step 1c: 학회 논문(ICRA/IROS/AIM)을 Crossref로 수집
------------------------------------------------------
OpenAlex는 이 학회 논문들의 primary_location.source 가 비어 있어 ISSN 수집이
불가능하다. Crossref는 프로시딩 제목(container-title)을 갖고 있으므로,
관련도 검색으로 해당 학회 논문을 상위에 모은 뒤 정규식으로 정확히 걸러낸다.

Crossref는 무료·무제한이며 1요청에 최대 1000건을 가져올 수 있다.

Usage:
    python step1c_crossref_conf.py                     # 전체
    python step1c_crossref_conf.py --only icra         # 특정 학회만
    python step1c_crossref_conf.py --from-year 2020    # 연도 제한
    python step1c_crossref_conf.py --no-merge          # 캐시만 갱신
    python step1c_crossref_conf.py --prune             # 전체 재수집 + 규칙에 안 맞는 옛 레코드 제거

환경변수 CONTACT_EMAIL 을 설정하면 Crossref polite pool(더 안정적)을 사용한다.

Output:
    crossref_raw/<key>_<year>.json   (연도별 캐시)
    all_dblp.json                    (기존 데이터에 병합)
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from venues_config import CROSSREF_CONFS

CROSSREF_API = "https://api.crossref.org/works"
RAW_DIR  = Path(__file__).parent / "crossref_raw"
ALL_FILE = Path(__file__).parent / "all_dblp.json"
RAW_DIR.mkdir(exist_ok=True)

MAILTO   = os.environ.get("CONTACT_EMAIL", "").strip()   # 설정 시 Crossref polite pool 사용
ROWS     = 1000                      # Crossref 1요청 최대치
MAX_OFFSET = 10000                   # Crossref offset 상한
# 주의: cursor 페이징을 쓰면 query.container-title의 관련도 정렬이 무시되어
#       엉뚱한 학회가 반환된다. 반드시 offset 페이징을 사용할 것.

# IEEE의 옛 레코드(대략 2010년 이전)는 발행일(issued)이 비어 있는 경우가 많아
# 발행일 필터로는 잡히지 않는다. 이 연도까지는 '등록일(created)' 창으로 한 번 더
# 훑어서 발행일 없는 레코드를 DOI/프로시딩 제목의 연도로 귀속시킨다.
LEGACY_UNDATED_UNTIL = 2010

_DOI_STEM = re.compile(r"^10\.1109/([a-z\-]+)")
_DOI_YEAR = re.compile(r"\.((?:19|20)\d\d)\.")
_CT_YEAR  = re.compile(r"\b((?:19|20)\d\d)\b")


def _doi_stem(doi: str) -> str:
    m = _DOI_STEM.match(doi)
    return m.group(1) if m else ""


def _issued_year(item: dict):
    for field in ("published-print", "published-online", "issued"):
        parts = (item.get(field) or {}).get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            return int(parts[0][0])
    return None


def _legacy_year(item: dict):
    """발행일 없는 레코드의 연도: DOI(robot.2005.…) → 프로시딩 제목 순으로 추정"""
    m = _DOI_YEAR.search((item.get("DOI") or "").lower())
    if m:
        return int(m.group(1))
    m = _CT_YEAR.search((item.get("container-title") or [""])[0])
    return int(m.group(1)) if m else None


def _authors(item: dict) -> list[str]:
    out = []
    for a in item.get("author", []) or []:
        name = " ".join(x for x in [a.get("given"), a.get("family")] if x).strip()
        if not name:
            name = a.get("name", "") or ""
        if name:
            out.append(name)
    return out


def _year(item: dict, fallback: int) -> int:
    for field in ("published-print", "published-online", "issued", "created"):
        parts = (item.get(field) or {}).get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            return int(parts[0][0])
    return fallback


def _get(params: dict, label: str, year: int) -> dict:
    if MAILTO:
        params["mailto"] = MAILTO
    for attempt in range(4):
        try:
            r = requests.get(CROSSREF_API, params=params, timeout=120)
            if r.status_code in (429, 503):
                wait = 20 * (attempt + 1)
                print(f"    혼잡, {wait}s 대기…")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json().get("message", {})
        except requests.RequestException as e:
            print(f"    요청 오류({e}) 재시도 {attempt+1}/4")
            time.sleep(10)
    raise RuntimeError(f"{label} {year} 수집 실패 — 캐시를 기록하지 않음")


def _record(it: dict, label: str, year: int) -> dict:
    doi = (it.get("DOI") or "").strip().lower()
    return {
        "venue":   label,
        "year":    year,
        "title":   (it.get("title") or [""])[0].strip(),
        "authors": _authors(it),
        "doi":     doi,
        "url":     f"https://doi.org/{doi}" if doi else "",
        "pages":   "",
        "key":     f"crossref:{doi}" if doi else "",
        "citation_count": it.get("is-referenced-by-count", 0) or 0,
        "abstract": "",
    }


def _scan(conf: dict, year: int, query: str, date_filter: str, accept) -> list[dict]:
    """관련도순으로 훑으며 accept(item)이 연도를 돌려준 것만 채택. 학회 구간이 끝나면 중단."""
    rx = re.compile(conf["pattern"], re.I)
    stems = set(conf["doi_stems"])
    out, offset = [], 0
    while offset < MAX_OFFSET:
        msg = _get({
            "query.container-title": query,
            "filter": f"type:proceedings-article,{date_filter},prefix:10.1109",
            "rows": ROWS, "offset": offset,
            "select": "DOI,title,container-title,issued,published-print,published-online,author,is-referenced-by-count",
        }, conf["label"], year)
        items = msg.get("items", []) or []
        in_conf = 0
        for it in items:
            ct = (it.get("container-title") or [""])[0]
            # 제목 패턴만으로는 ICRAE·ICRAS 같은 유사 명칭 학회가 섞이므로 DOI 어간도 확인
            if not rx.search(ct) or _doi_stem((it.get("DOI") or "").lower()) not in stems:
                continue
            in_conf += 1
            y = accept(it)
            if y is not None:
                out.append(_record(it, conf["label"], y))
        if in_conf == 0 or len(items) < ROWS:
            break
        offset += ROWS
        time.sleep(0.5)
    return out


def fetch_conf_year(conf: dict, year: int) -> list[dict]:
    """한 학회-연도의 논문을 모두 수집."""
    key, label = conf["key"], conf["label"]
    cache = RAW_DIR / f"{key}_{year}.json"
    if cache.exists():
        with open(cache, encoding="utf-8") as f:
            return json.load(f)

    # 1) 발행일이 해당 연도인 레코드
    results = _scan(conf, year, conf["query"],
                    f"from-pub-date:{year}-01-01,until-pub-date:{year}-12-31",
                    lambda it: _year(it, year))

    # 2) 발행일이 비어 있는 옛 레코드 (등록일 창으로 조회, 연도는 DOI/제목에서 추정)
    if year <= LEGACY_UNDATED_UNTIL:
        undated = _scan(conf, year, f"{year} {conf['query']}",
                        f"from-created-date:{year}-01-01,until-created-date:{year + 3}-12-31",
                        lambda it: year if (_issued_year(it) is None
                                            and _legacy_year(it) == year) else None)
        have = {p["doi"] for p in results}
        results += [p for p in undated if p["doi"] not in have]

    with open(cache, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    print(f"  {label} {year}: {len(results)} papers → cached", flush=True)
    return results


def load_existing():
    if not ALL_FILE.exists():
        return [], set(), set()
    with open(ALL_FILE, encoding="utf-8") as f:
        existing = json.load(f)
    doi_set = {p["doi"].lower() for p in existing if p.get("doi")}
    title_set = {p["title"].lower() for p in existing if p.get("title")}
    return existing, doi_set, title_set


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="+", metavar="KEY")
    ap.add_argument("--from-year", type=int, default=None)
    ap.add_argument("--no-merge", action="store_true")
    ap.add_argument("--prune", action="store_true",
                    help="이번 수집 결과에 없는 기존 학회 레코드를 제거 (수집 규칙을 바꾼 뒤 전체 재수집할 때)")
    args = ap.parse_args()

    confs = CROSSREF_CONFS
    if args.only:
        confs = [c for c in confs if c["key"] in args.only]

    new_papers: list[dict] = []
    for conf in confs:
        years = list(conf["years"])
        if args.from_year:
            years = [y for y in years if y >= args.from_year]
        print(f"\n[{conf['label']}] {years[0]}-{years[-1]}")
        for year in years:
            new_papers.extend(fetch_conf_year(conf, year))
            time.sleep(0.3)

    print(f"\n수집 합계: {len(new_papers):,} papers")
    if args.no_merge:
        print("--no-merge 지정: 병합 생략")
        return

    existing, doi_set, title_set = load_existing()
    if args.prune:
        if args.only or args.from_year:
            raise SystemExit("--prune 은 전체 수집(--only/--from-year 없이)에서만 쓸 수 있습니다")
        labels = {c["label"] for c in confs}
        valid = {p["doi"] for p in new_papers if p.get("doi")}
        before = len(existing)
        existing = [p for p in existing
                    if not (p.get("venue") in labels and (p.get("doi") or "").lower() not in valid)]
        doi_set = {p["doi"].lower() for p in existing if p.get("doi")}
        print(f"  prune: 기존 학회 레코드 {before - len(existing):,}건 제거")
    by_doi = {p["doi"].lower(): p for p in existing if p.get("doi")}

    added = updated = 0
    for p in new_papers:
        doi = (p.get("doi") or "").lower().strip()
        old = by_doi.get(doi) if doi else None
        if old is not None:
            if p.get("citation_count") is not None:
                old["citation_count"] = p["citation_count"]
            updated += 1
            continue
        # 학회 논문은 제목 중복 판정을 쓰지 않는다
        # (같은 제목의 저널 확장판이 별개 논문으로 존재하기 때문)
        if doi and doi in doi_set:
            continue
        existing.append(p)
        if doi:
            doi_set.add(doi)
            by_doi[doi] = p
        added += 1

    with open(ALL_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"✓ 신규 {added:,} / 갱신 {updated:,} → {ALL_FILE} (total {len(existing):,})")


if __name__ == "__main__":
    main()
