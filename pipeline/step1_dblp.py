"""
Step 1a: DBLP에서 저널 메타데이터 수집
--------------------------------------
대상 저널 목록은 venues_config.py의 DBLP_VENUES에서 관리합니다.

Usage:
    python step1_dblp.py                 # 전체 수집
    python step1_dblp.py --only tro tac  # 특정 저널만
    python step1_dblp.py --from-year 2020  # 특정 연도부터

Output:
    dblp_raw/<key>_<year>.json   (연도별 캐시)
    all_dblp.json                (통합 파일)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from venues_config import DBLP_VENUES

DBLP_API = "https://dblp.org/search/publ/api"
RAW_DIR = Path(__file__).parent / "dblp_raw"
OUT_FILE = Path(__file__).parent / "all_dblp.json"
RAW_DIR.mkdir(exist_ok=True)


def fetch_dblp_year(stream: str, year: int, label: str) -> list[dict]:
    cache = RAW_DIR / f"{stream.replace('/', '_')}_{year}.json"
    if cache.exists():
        with open(cache, encoding="utf-8") as f:
            return json.load(f)

    results, offset = [], 0
    while True:
        params = {
            "q":      f"stream:{stream} year:{year}",
            "format": "json",
            "h":      1000,
            "f":      offset,
        }
        for attempt in range(5):
            try:
                r = requests.get(DBLP_API, params=params, timeout=30)
                if r.status_code == 429:
                    wait = 60 * (attempt + 1)
                    print(f"  Rate-limited. Waiting {wait}s…")
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                break
            except requests.RequestException as e:
                print(f"  Request error ({e}), retry {attempt+1}/5")
                time.sleep(10)
        else:
            print(f"  Failed to fetch {stream} {year} offset={offset}")
            break

        data = r.json().get("result", {})
        hits = data.get("hits", {})
        hit_list = hits.get("hit", [])
        if not hit_list:
            break

        for h in hit_list:
            info = h.get("info", {})
            authors_raw = info.get("authors", {}).get("author", [])
            if isinstance(authors_raw, dict):
                authors_raw = [authors_raw]
            results.append({
                "venue":   label,
                "year":    int(info.get("year", year)),
                "title":   info.get("title", "").strip(),
                "authors": [a.get("text", "") for a in authors_raw],
                "doi":     info.get("doi", ""),
                "url":     info.get("url", ""),
                "pages":   info.get("pages", ""),
                "key":     info.get("key", ""),
            })

        total = int(hits.get("@total", 0))
        offset += len(hit_list)
        if offset >= total:
            break
        time.sleep(0.5)

    with open(cache, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    print(f"  {label} {year}: {len(results)} papers → cached")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="+", metavar="KEY",
                        help="특정 저널 key만 수집 (예: tro tac)")
    parser.add_argument("--from-year", type=int, default=None,
                        help="이 연도 이후 데이터만 수집")
    args = parser.parse_args()

    venues = DBLP_VENUES
    if args.only:
        venues = [v for v in venues if v[0] in args.only]

    all_papers: list[dict] = []
    for key, stream, label, year_range in venues:
        years = list(year_range)
        if args.from_year:
            years = [y for y in years if y >= args.from_year]
        print(f"\n[{label}] ({stream}) {years[0]}-{years[-1]}")
        for year in years:
            papers = fetch_dblp_year(stream, year, label)
            all_papers.extend(papers)
            time.sleep(0.3)

    # DOI 기반 중복 제거 (같은 저널 내)
    seen_doi: set[str] = set()
    seen_title: set[str] = set()
    deduped: list[dict] = []
    for p in all_papers:
        doi = p.get("doi", "").strip().lower()
        title = p.get("title", "").strip().lower()
        key_doi = doi if doi else None
        key_title = title if title else None
        if key_doi and key_doi in seen_doi:
            continue
        if key_title and key_title in seen_title:
            continue
        if key_doi:
            seen_doi.add(key_doi)
        if key_title:
            seen_title.add(key_title)
        deduped.append(p)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)
    print(f"\n✓ {len(deduped)} papers saved → {OUT_FILE}")


if __name__ == "__main__":
    main()
