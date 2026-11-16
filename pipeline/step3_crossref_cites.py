"""
Step 3: 저널 논문의 인용수를 Crossref 기준으로 갱신
------------------------------------------------------
OpenAlex는 유료 크레딧제로 전환되어 일일 예산 제약이 크다. Crossref는 무료·무제한이고
ISSN 필터로 1요청에 1000건까지 가져올 수 있어, 전체 갱신이 250요청 수준으로 끝난다.

주의: 여기서는 hard filter(issn)만 쓰므로 cursor 페이징이 안전하다.
      (관련도 검색 query.* 와 cursor를 함께 쓰면 정렬이 깨진다 — step1c 참고)

초록은 갱신하지 않는다. 초록은 변하지 않는 값이고 OpenAlex 쪽 품질이 더 좋기 때문.

Usage:
    python step3_crossref_cites.py                 # 전체 저널
    python step3_crossref_cites.py --only tac ral  # 특정 저널만
    python step3_crossref_cites.py --no-merge      # 캐시만 갱신

Output:
    crossref_cites/<key>.json   ({doi: citation_count})
    all_dblp.json               (citation_count 갱신)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from venues_config import OPENALEX_VENUES

CROSSREF_API = "https://api.crossref.org/works"
CITE_DIR = Path(__file__).parent / "crossref_cites"
ALL_FILE = Path(__file__).parent / "all_dblp.json"
CITE_DIR.mkdir(exist_ok=True)

MAILTO = os.environ.get("CONTACT_EMAIL", "").strip()   # 설정 시 polite pool 사용 (없어도 동작)
ROWS = 1000


def fetch_journal_cites(venue: dict) -> dict[str, int]:
    """한 저널의 모든 논문 인용수를 {doi: count} 로 수집"""
    key, label, issn = venue["key"], venue["label"], venue["issn_l"]
    years = list(venue["years"])
    cache = CITE_DIR / f"{key}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))

    cites: dict[str, int] = {}
    cursor = "*"
    pages = 0
    while True:
        params = {
            "filter": f"issn:{issn},from-pub-date:{years[0]}-01-01",
            "rows": ROWS,
            "cursor": cursor,
            "select": "DOI,is-referenced-by-count",
        }
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
                break
            except requests.RequestException as e:
                print(f"    요청 오류({e}) 재시도 {attempt+1}/4")
                time.sleep(10)
        else:
            raise RuntimeError(f"{label} 수집 실패 — 캐시를 기록하지 않음")

        msg = r.json().get("message", {})
        items = msg.get("items", []) or []
        if not items:
            break
        for it in items:
            doi = (it.get("DOI") or "").strip().lower()
            if doi:
                cites[doi] = it.get("is-referenced-by-count", 0) or 0
        pages += 1
        cursor = msg.get("next-cursor")
        if not cursor or len(items) < ROWS:
            break
        time.sleep(0.4)

    cache.write_text(json.dumps(cites, ensure_ascii=False), encoding="utf-8")
    print(f"  {label:<14} {len(cites):>7,}건 ({pages} 요청)")
    return cites


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="+", metavar="KEY")
    ap.add_argument("--no-merge", action="store_true")
    args = ap.parse_args()

    venues = OPENALEX_VENUES
    if args.only:
        venues = [v for v in venues if v["key"] in args.only]

    print(f"=== Crossref 인용수 수집 ({len(venues)}개 저널) ===")
    all_cites: dict[str, int] = {}
    for v in venues:
        all_cites.update(fetch_journal_cites(v))
        time.sleep(0.3)
    print(f"\n총 {len(all_cites):,}개 DOI의 인용수 확보")

    if args.no_merge:
        print("--no-merge 지정: 병합 생략")
        return

    papers = json.loads(ALL_FILE.read_text(encoding="utf-8"))
    updated = miss = 0
    delta_sum = 0
    for p in papers:
        doi = (p.get("doi") or "").strip().lower()
        if not doi or doi not in all_cites:
            miss += 1
            continue
        new = all_cites[doi]
        old = p.get("citation_count")
        if isinstance(old, int):
            delta_sum += new - old
        p["citation_count"] = new
        updated += 1

    ALL_FILE.write_text(json.dumps(papers, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ 인용수 갱신 {updated:,}편 / 미매칭 {miss:,}편 → {ALL_FILE}")
    if updated:
        print(f"  평균 변화량: {delta_sum/updated:+.1f} (OpenAlex 대비 Crossref는 대체로 낮음)")


if __name__ == "__main__":
    main()
