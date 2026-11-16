"""
Step 2c: 학회 논문 초록 보충 (OpenAlex, DOI 조회)
--------------------------------------------------
학회 논문은 Crossref로 수집하는데 Crossref에는 초록이 없다. OpenAlex는 학회 논문의
소속 학회 정보는 비어 있어도 초록은 갖고 있으므로, DOI 50개씩 묶어 초록만 받아온다.

OpenAlex는 하루 무료 요청 한도가 있다. 한도가 소진되면 여기까지 받은 것을 저장하고
정상 종료한다(실패가 아님). 다음 실행 때 남은 것부터 이어서 받는다.
초록이 없다고 확인된 DOI도 기록해 두어 다시 묻지 않는다.

Usage:
    python step2c_conf_abstracts.py              # 남은 것 전부
    python step2c_conf_abstracts.py --max 200    # 요청 수 제한

Output:
    conf_abstracts.json   ({doi: abstract}, 초록 없음은 "")
    all_dblp.json         (학회 논문의 abstract 채움)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from venues_config import CROSSREF_CONFS

OA_WORKS   = "https://api.openalex.org/works"
ALL_FILE   = Path(__file__).parent / "all_dblp.json"
CACHE_FILE = Path(__file__).parent / "conf_abstracts.json"
MAILTO     = os.environ.get("CONTACT_EMAIL", "").strip()
API_KEY    = os.environ.get("OPENALEX_API_KEY", "").strip()
BATCH      = 50          # OpenAlex OR-필터 최대 개수


class BudgetExhausted(Exception):
    pass


def extract_abstract(inv_index) -> str:
    if not inv_index:
        return ""
    word_pos = [(pos, word) for word, positions in inv_index.items() for pos in positions]
    word_pos.sort()
    return " ".join(w for _, w in word_pos)


def fetch(dois: list[str]) -> dict[str, str]:
    params = {
        "filter": "doi:" + "|".join(dois),
        "select": "doi,abstract_inverted_index",
        "per-page": BATCH,
    }
    if MAILTO:
        params["mailto"] = MAILTO
    if API_KEY:
        params["api_key"] = API_KEY
    for attempt in range(4):
        try:
            r = requests.get(OA_WORKS, params=params, timeout=60)
            if r.status_code == 429:
                try:
                    j = r.json()
                except Exception:
                    j = {}
                if "budget" in f"{j.get('error','')} {j.get('message','')}".lower() \
                        or j.get("dailyRemainingUsd") == 0:
                    raise BudgetExhausted()
                time.sleep(30 * (attempt + 1))
                continue
            r.raise_for_status()
            out = {}
            for w in r.json().get("results", []):
                doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
                if doi:
                    out[doi] = extract_abstract(w.get("abstract_inverted_index"))
            return out
        except requests.RequestException as e:
            print(f"  요청 오류({e}) 재시도 {attempt+1}/4", flush=True)
            time.sleep(10)
    raise RuntimeError("OpenAlex 요청 실패")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=0, help="최대 요청 수 (0 = 제한 없음)")
    args = ap.parse_args()

    labels = {c["label"] for c in CROSSREF_CONFS}
    papers = json.loads(ALL_FILE.read_text(encoding="utf-8"))
    cache: dict[str, str] = {}
    if CACHE_FILE.exists():
        cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))

    todo = [p["doi"].lower() for p in papers
            if p.get("venue") in labels and p.get("doi") and p["doi"].lower() not in cache]
    todo = list(dict.fromkeys(todo))
    n_req = (len(todo) + BATCH - 1) // BATCH
    print(f"학회 논문 초록: 확보 {len(cache):,} / 남음 {len(todo):,} ({n_req:,} 요청)", flush=True)

    done = 0
    stopped = False
    try:
        for i in range(0, len(todo), BATCH):
            if args.max and done >= args.max:
                break
            batch = todo[i:i + BATCH]
            got = fetch(batch)
            for d in batch:
                cache[d] = got.get(d, "")      # 응답에 없으면 '초록 없음'으로 기록
            done += 1
            if done % 50 == 0:
                CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
                print(f"  {done}/{n_req} 요청", flush=True)
            time.sleep(0.15)
    except BudgetExhausted:
        stopped = True
        print("  OpenAlex 하루 무료 한도 소진 — 여기까지 저장하고 종료 (다음 실행 때 이어서)", flush=True)
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    # 수집에 시간이 오래 걸리므로, 그사이 다른 단계가 고쳤을 수 있는 파일을 다시 읽어 반영한다
    papers = json.loads(ALL_FILE.read_text(encoding="utf-8"))
    filled = 0
    for p in papers:
        if p.get("venue") in labels:
            ab = cache.get((p.get("doi") or "").lower())
            if ab:
                p["abstract"] = ab
                filled += 1
    ALL_FILE.write_text(json.dumps(papers, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(1 for p in papers if p.get("venue") in labels)
    print(f"✓ 학회 논문 {total:,}편 중 초록 보유 {filled:,}편"
          + (" (한도 소진으로 일부 미수집)" if stopped else ""), flush=True)


if __name__ == "__main__":
    main()
