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

# 200편/요청으로 인용수·초록까지 함께 받아온다 (step2의 ID 개별조회 불필요)
SELECT_FIELDS = ("id,title,authorships,doi,publication_year,biblio,"
                 "cited_by_count,abstract_inverted_index")


class BudgetExhausted(Exception):
    """OpenAlex 일일 무료 예산 소진 — 자정(UTC) 이후 재실행 필요"""


def _budget_error(resp) -> bool:
    """429 응답이 '예산 소진'인지 판별 (단순 속도 제한과 구분)"""
    try:
        j = resp.json()
    except Exception:
        return False
    text = f"{j.get('error','')} {j.get('message','')}".lower()
    return "budget" in text or j.get("dailyRemainingUsd") == 0


def extract_abstract(inv_index: dict | None) -> str:
    if not inv_index:
        return ""
    word_pos: list[tuple[int, str]] = []
    for word, positions in inv_index.items():
        for pos in positions:
            word_pos.append((pos, word))
    word_pos.sort()
    return " ".join(w for _, w in word_pos)


def _cache_is_current(path: Path) -> bool:
    """이전 스키마(인용수 없음)로 저장된 캐시는 갱신 대상"""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return False
    if not data:            # 빈 연도는 판별 불가 → 그대로 사용
        return True
    return "citation_count" in data[0]


def fetch_venue_year(issn: str, year: int, label: str, key: str,
                     force: bool = False) -> list[dict]:
    cache = RAW_DIR / f"{key}_{year}.json"
    if cache.exists() and not force and _cache_is_current(cache):
        with open(cache, encoding="utf-8") as f:
            return json.load(f)

    results = []
    cursor = "*"
    while True:
        params = {
            "filter":  f"primary_location.source.issn:{issn},publication_year:{year}",
            "select":  SELECT_FIELDS,
            "per-page": 200,
            "cursor":  cursor,
            "mailto":  MAILTO,
        }
        for attempt in range(5):
            try:
                r = requests.get(OPENALEX_API, params=params, timeout=60)
                if r.status_code == 429:
                    if _budget_error(r):
                        raise BudgetExhausted(
                            "OpenAlex 일일 무료 예산 소진 (자정 UTC = 한국 오전 9시에 리셋)")
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
            # 부분 수집분을 완료본처럼 캐시하면 데이터가 조용히 손상되므로 중단
            raise RuntimeError(f"{label} {year} 수집 실패 — 캐시를 기록하지 않음")

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
                "citation_count": w.get("cited_by_count", 0),
                "abstract": extract_abstract(w.get("abstract_inverted_index")),
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
    parser.add_argument("--refetch", action="store_true",
                        help="캐시가 있어도 강제로 다시 수집 (인용수 갱신용)")
    args = parser.parse_args()

    venues = OPENALEX_VENUES
    if args.only:
        venues = [v for v in venues if v["key"] in args.only]

    new_papers: list[dict] = []
    budget_hit = False
    try:
        for venue in venues:
            key, label, issn = venue["key"], venue["label"], venue["issn_l"]
            years = list(venue["years"])
            if args.from_year:
                years = [y for y in years if y >= args.from_year]
            print(f"\n[{label}] ISSN={issn}  {years[0]}-{years[-1]}")
            for year in years:
                papers = fetch_venue_year(issn, year, label, key, force=args.refetch)
                new_papers.extend(papers)
                time.sleep(0.2)
    except BudgetExhausted as e:
        budget_hit = True
        print(f"\n[중단] {e}")
        print("  완료된 연도는 캐시에 저장되어 있습니다. 예산 리셋 후 같은 명령을 다시 실행하면 이어서 진행됩니다.")

    if args.no_merge:
        print(f"\n--no-merge 지정: {len(new_papers)} papers 수집 완료 (병합 생략)")
        return

    existing, doi_set, title_set = load_existing()

    # 기존 논문을 찾아 인용수를 갱신하기 위한 색인
    by_key = {p["key"]: p for p in existing if p.get("key")}
    by_doi = {p["doi"].lower(): p for p in existing if p.get("doi")}

    added = updated = 0
    for p in new_papers:
        doi = (p.get("doi") or "").lower().strip()
        title = (p.get("title") or "").lower().strip()
        oa_id = p.get("key") or ""

        old = by_key.get(oa_id) or (by_doi.get(doi) if doi else None)
        if old is not None:
            # 이미 있는 논문 → 인용수·초록을 최신 값으로 갱신
            if p.get("citation_count") is not None:
                old["citation_count"] = p["citation_count"]
            if p.get("abstract"):
                old["abstract"] = p["abstract"]
            updated += 1
            continue

        if doi and doi in doi_set:
            continue
        if title and title in title_set:
            continue

        existing.append(p)
        if oa_id:
            by_key[oa_id] = p
        if doi:
            doi_set.add(doi)
            by_doi[doi] = p
        if title:
            title_set.add(title)
        added += 1

    with open(ALL_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 신규 {added} / 갱신 {updated} → {ALL_FILE} (total {len(existing)})")
    if budget_hit:
        print("  ※ 예산 소진으로 일부 연도가 미수집 상태입니다. 내일 다시 실행하세요.")


if __name__ == "__main__":
    main()
