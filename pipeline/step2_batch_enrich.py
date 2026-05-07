"""
Step 2 (배치 버전): OpenAlex ID 배치 조회로 인용수·초록 보강
--------------------------------------------------------------
openalex_raw 캐시에 저장된 OpenAlex ID를 50개씩 묶어 한 번에 조회합니다.
150k papers 기준 약 3,000 요청 → 10~20분 소요.

Usage:
    python step2_batch_enrich.py
    python step2_batch_enrich.py --batch-size 50  # 기본값

Output:
    enrich_cache.json     (중간 저장)
    all_enriched.json     (최종)
"""

import argparse
import json
import time
from pathlib import Path

import requests

IN_FILE     = Path(__file__).parent / "all_dblp.json"
OUT_FILE    = Path(__file__).parent / "all_enriched.json"
CACHE_FILE  = Path(__file__).parent / "enrich_cache.json"
MAILTO      = "your_email@example.com"
OA_WORKS    = "https://api.openalex.org/works"


def extract_abstract(inv_index: dict | None) -> str:
    if not inv_index:
        return ""
    word_pos: list[tuple[int, str]] = []
    for word, positions in (inv_index or {}).items():
        for pos in positions:
            word_pos.append((pos, word))
    word_pos.sort()
    return " ".join(w for _, w in word_pos)


def fetch_batch(openalex_ids: list[str]) -> dict[str, dict]:
    """OpenAlex ID 목록을 한 번에 조회하여 {id: {citation_count, abstract}} 반환"""
    ids_str = "|".join(openalex_ids)
    params = {
        "filter":  f"openalex_id:{ids_str}",
        "select":  "id,cited_by_count,abstract_inverted_index,open_access",
        "per-page": len(openalex_ids),
        "mailto":  MAILTO,
    }
    for attempt in range(4):
        try:
            r = requests.get(OA_WORKS, params=params, timeout=30)
            if r.status_code == 429:
                wait = 60 * (attempt + 1)
                print(f"  Rate-limited, waiting {wait}s…")
                time.sleep(wait)
                continue
            r.raise_for_status()
            results = {}
            for w in r.json().get("results", []):
                oa_id = w.get("id", "")
                results[oa_id] = {
                    "citation_count": w.get("cited_by_count", 0),
                    "abstract":       extract_abstract(w.get("abstract_inverted_index")),
                    "open_access":    w.get("open_access", {}).get("is_oa", False),
                }
            return results
        except requests.RequestException as e:
            print(f"  Error: {e}, retry {attempt+1}/4")
            time.sleep(10)
    return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()

    print(f"Loading {IN_FILE}…")
    with open(IN_FILE, encoding="utf-8") as f:
        papers = json.load(f)
    print(f"  {len(papers):,} papers")

    # 이미 완료된 캐시 로드
    enrich_cache: dict[str, dict] = {}
    if CACHE_FILE.exists():
        with open(CACHE_FILE, encoding="utf-8") as f:
            enrich_cache = json.load(f)
        print(f"  기존 캐시: {len(enrich_cache):,} entries")

    # OpenAlex ID가 있는 논문들만 배치 처리
    todo_ids = [
        p["key"] for p in papers
        if p.get("key", "").startswith("https://openalex.org/")
        and p["key"] not in enrich_cache
    ]
    print(f"  조회 대상: {len(todo_ids):,} papers")

    batch_size = args.batch_size
    total_batches = (len(todo_ids) + batch_size - 1) // batch_size

    for i in range(0, len(todo_ids), batch_size):
        batch = todo_ids[i:i + batch_size]
        batch_num = i // batch_size + 1
        results = fetch_batch(batch)
        enrich_cache.update(results)
        time.sleep(0.12)

        if batch_num % 100 == 0 or batch_num == total_batches:
            # 중간 저장
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(enrich_cache, f, ensure_ascii=False)
            pct = batch_num / total_batches * 100
            print(f"  [{pct:.0f}%] {batch_num}/{total_batches} batches, cache={len(enrich_cache):,}")

    # 최종 병합
    enriched = []
    hit = 0
    for p in papers:
        oa_id = p.get("key", "")
        if oa_id in enrich_cache:
            p.update(enrich_cache[oa_id])
            hit += 1
        enriched.append(p)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 인용수 보강: {hit:,}/{len(papers):,} papers → {OUT_FILE}")


if __name__ == "__main__":
    main()
