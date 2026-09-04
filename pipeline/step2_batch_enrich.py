"""
Step 2 (배치 버전): OpenAlex ID 배치 조회로 인용수·초록 보강
--------------------------------------------------------------
openalex_raw 캐시에 저장된 OpenAlex ID를 50개씩 묶어 한 번에 조회합니다.
150k papers 기준 약 3,000 요청 → 10~20분 소요.

인용수는 시간이 지나면 증가하므로, 캐시에 있는 항목도 일정 기간이 지나면
다시 조회합니다(기본 30일). 타임스탬프가 없는 옛 캐시 항목은 오래된 것으로
간주해 갱신 대상에 포함됩니다.

Usage:
    python step2_batch_enrich.py                    # 신규 + 30일 지난 항목 갱신
    python step2_batch_enrich.py --max-age-days 7   # 7일 지난 항목까지 갱신
    python step2_batch_enrich.py --refresh-all      # 전체 강제 갱신
    python step2_batch_enrich.py --no-refresh       # 신규만 (옛 동작)

Output:
    enrich_cache.json     (중간 저장)
    all_enriched.json     (최종)
"""

import argparse
import json
import time
from pathlib import Path

import requests

TS_KEY = "_ts"   # 캐시 항목을 마지막으로 조회한 unix time


class BudgetExhausted(Exception):
    """OpenAlex 일일 무료 예산 소진 — 자정(UTC) 이후 재실행 필요"""


def _budget_error(resp) -> bool:
    try:
        j = resp.json()
    except Exception:
        return False
    text = f"{j.get('error','')} {j.get('message','')}".lower()
    return "budget" in text or j.get("dailyRemainingUsd") == 0

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
                if _budget_error(r):
                    raise BudgetExhausted(
                        "OpenAlex 일일 무료 예산 소진 (자정 UTC = 한국 오전 9시에 리셋)")
                wait = 60 * (attempt + 1)
                print(f"  Rate-limited, waiting {wait}s…")
                time.sleep(wait)
                continue
            r.raise_for_status()
            now = int(time.time())
            results = {}
            for w in r.json().get("results", []):
                oa_id = w.get("id", "")
                results[oa_id] = {
                    "citation_count": w.get("cited_by_count", 0),
                    "abstract":       extract_abstract(w.get("abstract_inverted_index")),
                    "open_access":    w.get("open_access", {}).get("is_oa", False),
                    TS_KEY:           now,
                }
            return results
        except requests.RequestException as e:
            print(f"  Error: {e}, retry {attempt+1}/4")
            time.sleep(10)
    return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--max-age-days", type=float, default=30,
                        help="이 기간이 지난 캐시 항목은 인용수를 다시 조회 (기본 30일)")
    parser.add_argument("--refresh-all", action="store_true",
                        help="캐시 신선도와 무관하게 전체 재조회")
    parser.add_argument("--no-refresh", action="store_true",
                        help="갱신 없이 신규 논문만 조회")
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

    # 조회 대상 선별: 신규(캐시 없음) + 오래된 항목(인용수 갱신)
    now = time.time()
    max_age_sec = args.max_age_days * 86400

    def needs_fetch(oa_id: str) -> bool:
        entry = enrich_cache.get(oa_id)
        if entry is None:
            return True                      # 신규
        if args.no_refresh:
            return False
        if args.refresh_all:
            return True
        # 타임스탬프가 없는 옛 항목은 오래된 것으로 간주
        return (now - entry.get(TS_KEY, 0)) > max_age_sec

    new_cnt = stale_cnt = 0
    todo_ids = []
    for p in papers:
        k = p.get("key", "")
        if not k.startswith("https://openalex.org/"):
            continue
        # step1이 이미 인용수를 채운 논문은 건너뛴다 (보조 역할)
        if p.get("citation_count") is not None and not args.refresh_all:
            continue
        if not needs_fetch(k):
            continue
        todo_ids.append(k)
        if k in enrich_cache:
            stale_cnt += 1
        else:
            new_cnt += 1

    # 중복 제거(같은 논문이 여러 번 들어간 경우 대비)
    todo_ids = list(dict.fromkeys(todo_ids))
    print(f"  조회 대상: {len(todo_ids):,} papers "
          f"(신규 {new_cnt:,} + 갱신 {stale_cnt:,})")

    batch_size = args.batch_size
    total_batches = (len(todo_ids) + batch_size - 1) // batch_size

    try:
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
    except BudgetExhausted as e:
        print(f"\n[중단] {e}")
        print("  여기까지의 결과는 캐시에 저장되며, 재실행 시 이어서 진행됩니다.")
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(enrich_cache, f, ensure_ascii=False)

    # 최종 병합
    enriched = []
    hit = 0
    for p in papers:
        oa_id = p.get("key", "")
        entry = enrich_cache.get(oa_id)
        if entry:
            # step1이 채운 값이 최신이므로 덮어쓰지 않고 빈 항목만 보완
            for k, v in entry.items():
                if k == TS_KEY:
                    continue
                if k not in p or p[k] is None:
                    p[k] = v
            hit += 1
        enriched.append(p)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 인용수 보강: {hit:,}/{len(papers):,} papers → {OUT_FILE}")


if __name__ == "__main__":
    main()
