"""
Step 2: OpenAlex로 인용수 및 초록 보강
---------------------------------------
all_dblp.json의 각 논문에 대해 DOI → OpenAlex Works API로 조회하여
citation_count, abstract, open_access 정보를 추가합니다.

중단해도 checkpoint 파일 덕분에 이어서 실행 가능합니다.

Usage:
    python step2_openalex.py
    python step2_openalex.py --batch-size 500  # 체크포인트 간격 조정

Output:
    enriched_checkpoint_<N>.json
    all_enriched.json  (최종)
"""

import argparse
import json
import time
from pathlib import Path

import requests

IN_FILE   = Path(__file__).parent / "all_dblp.json"
OUT_FILE  = Path(__file__).parent / "all_enriched.json"
CKPT_DIR  = Path(__file__).parent
MAILTO    = "your_email@example.com"
OA_WORKS  = "https://api.openalex.org/works"


def query_openalex_doi(doi: str) -> dict:
    url = f"{OA_WORKS}/https://doi.org/{doi}"
    for attempt in range(4):
        try:
            r = requests.get(url, params={"mailto": MAILTO}, timeout=20)
            if r.status_code == 404:
                return {}
            if r.status_code == 429:
                time.sleep(60 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            time.sleep(10)
    return {}


def extract_abstract(inv_index: dict | None) -> str:
    if not inv_index:
        return ""
    word_pos: list[tuple[int, str]] = []
    for word, positions in inv_index.items():
        for pos in positions:
            word_pos.append((pos, word))
    word_pos.sort()
    return " ".join(w for _, w in word_pos)


def enrich(paper: dict) -> dict:
    doi = paper.get("doi", "").strip()
    if not doi:
        return paper
    data = query_openalex_doi(doi)
    if not data:
        return paper
    paper["citation_count"] = data.get("cited_by_count", 0)
    paper["abstract"] = extract_abstract(data.get("abstract_inverted_index"))
    paper["open_access"] = data.get("open_access", {}).get("is_oa", False)
    paper["openalex_id"] = data.get("id", "")
    return paper


def find_latest_checkpoint() -> tuple[list[dict], int]:
    ckpts = sorted(CKPT_DIR.glob("enriched_checkpoint_*.json"))
    if not ckpts:
        return [], 0
    latest = ckpts[-1]
    idx = int(latest.stem.split("_")[-1])
    with open(latest, encoding="utf-8") as f:
        return json.load(f), idx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--reset", action="store_true", help="체크포인트 무시하고 처음부터")
    args = parser.parse_args()

    with open(IN_FILE, encoding="utf-8") as f:
        papers = json.load(f)

    if args.reset:
        enriched, start_idx = [], 0
    else:
        enriched, start_idx = find_latest_checkpoint()

    print(f"총 {len(papers)} papers, {start_idx} 이미 처리됨")
    todo = papers[len(enriched):]

    for i, paper in enumerate(todo, start=len(enriched)):
        enriched.append(enrich(paper))
        time.sleep(0.12)

        if (i + 1) % args.batch_size == 0:
            ckpt_n = (i + 1) // args.batch_size
            ckpt_file = CKPT_DIR / f"enriched_checkpoint_{ckpt_n:02d}.json"
            with open(ckpt_file, "w", encoding="utf-8") as f:
                json.dump(enriched, f, ensure_ascii=False, indent=2)
            print(f"  checkpoint {ckpt_file.name} 저장 ({i+1}/{len(papers)})")

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 완료 → {OUT_FILE} ({len(enriched)} papers)")


if __name__ == "__main__":
    main()
