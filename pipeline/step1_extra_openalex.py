"""
Step 1b: DBLP에 없는 저널을 OpenAlex API로 수집
-------------------------------------------------
대상 저널 목록은 venues_config.py의 OPENALEX_VENUES에서 관리합니다.
수집 결과를 all_dblp.json에 병합(DOI/제목 기반 중복 제거)합니다.

Usage:
    python step1_extra_openalex.py                    # 전체
    python step1_extra_openalex.py --only scirob jgcd # 특정 저널만
    python step1_extra_openalex.py --no-merge         # 병합 생략

Output:
    openalex_raw/<key>_<year>.json  (연도별 캐시)
    all_dblp.json                   (기존 데이터에 병합)
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

OPENALEX_API = "https://api.openalex.org/works"
RAW_DIR = Path(__file__).parent / "openalex_raw"
ALL_FILE = Path(__file__).parent / "all_dblp.json"
RAW_DIR.mkdir(exist_ok=True)

# OpenAlex 요청 시 식별용 이메일 (rate limit 완화)
MAILTO = "your_email@example.com"


def fetch_venue_year(issn: str, year: int, label: str, key: str) -> list[dict]:
    cache = RAW_DIR / f"{key}_{year}.json"
    if cache.exists():
        with open(cache, encoding="utf-8") as f:
            return json.load(f)

    results = []
    cursor = "*"
    while True:
        params = {
            "filter":  f"primary_location.source.issn:{issn},publication_year:{year}",
            "select":  "id,title,authorships,doi,publication_year,biblio",
            "per-page": 200,
            "cursor":  cursor,
            "mailto":  MAILTO,
        }
        for attempt in range(5):
            try:
                r = requests.get(OPENALEX_API, params=params, timeout=30)
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
            print(f"  Failed to fetch {label} {year}")
            break

        data = r.json()
        works = data.get("results", [])
        if not works:
            break

        for w in works:
            authorships = w.get("authorships", [])
            authors = [
                a.get("author", {}).get("display_name", "")
                for a in authorships
            ]
            doi_raw = w.get("doi", "") or ""
            doi = doi_raw.replace("https://doi.org/", "").strip()
            biblio = w.get("biblio", {}) or {}
            results.append({
                "venue":   label,
                "year":    int(w.get("publication_year", year)),
                "title":   (w.get("title", "") or "").strip(),
                "authors": authors,
                "doi":     doi,
                "url":     doi_raw,
                "pages":   f"{biblio.get('first_page','')}--{biblio.get('last_page','')}".strip("-"),
                "key":     w.get("id", ""),
            })

        next_cursor = data.get("meta", {}).get("next_cursor")
        if not next_cursor:
            break
        cursor = next_cursor
        time.sleep(0.3)

    with open(cache, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    print(f"  {label} {year}: {len(results)} papers → cached")
    return results


def load_existing() -> tuple[list[dict], set[str], set[str]]:
    if not ALL_FILE.exists():
        return [], set(), set()
    with open(ALL_FILE, encoding="utf-8") as f:
        existing = json.load(f)
    doi_set = {p["doi"].lower() for p in existing if p.get("doi")}
    title_set = {p["title"].lower() for p in existing if p.get("title")}
    return existing, doi_set, title_set


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="+", metavar="KEY",
                        help="특정 저널 key만 수집 (예: scirob jgcd)")
    parser.add_argument("--no-merge", action="store_true",
                        help="all_dblp.json에 병합하지 않음")
    parser.add_argument("--from-year", type=int, default=None)
    args = parser.parse_args()

    venues = OPENALEX_VENUES
    if args.only:
        venues = [v for v in venues if v["key"] in args.only]

    new_papers: list[dict] = []
    for venue in venues:
        key, label, issn = venue["key"], venue["label"], venue["issn_l"]
        years = list(venue["years"])
        if args.from_year:
            years = [y for y in years if y >= args.from_year]
        print(f"\n[{label}] ISSN={issn}  {years[0]}–{years[-1]}")
        for year in years:
            papers = fetch_venue_year(issn, year, label, key)
            new_papers.extend(papers)
            time.sleep(0.2)

    if args.no_merge:
        print(f"\n--no-merge 지정: {len(new_papers)} papers 수집 완료 (병합 생략)")
        return

    existing, doi_set, title_set = load_existing()
    added = 0
    for p in new_papers:
        doi = (p.get("doi") or "").lower().strip()
        title = (p.get("title") or "").lower().strip()
        if doi and doi in doi_set:
            continue
        if title and title in title_set:
            continue
        existing.append(p)
        if doi:
            doi_set.add(doi)
        if title:
            title_set.add(title)
        added += 1

    with open(ALL_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"\n✓ {added} papers 추가 → {ALL_FILE} (total {len(existing)})")


if __name__ == "__main__":
    main()
