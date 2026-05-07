"""
Step 2 (빠른 버전): openalex_raw 캐시에서 인용수·초록 직접 추출
-----------------------------------------------------------------
step1_extra_openalex.py가 저장한 raw JSON 파일들을 다시 읽어서
citation_count와 abstract를 추출합니다.
API를 추가로 호출하지 않으므로 수 분 내에 완료됩니다.

Usage:
    python step2_from_cache.py

Output:
    all_enriched.json
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from venues_config import OPENALEX_VENUES

RAW_DIR  = Path(__file__).parent / "openalex_raw"
IN_FILE  = Path(__file__).parent / "all_dblp.json"
OUT_FILE = Path(__file__).parent / "all_enriched.json"


def extract_abstract(inv_index: dict | None) -> str:
    if not inv_index:
        return ""
    word_pos: list[tuple[int, str]] = []
    for word, positions in inv_index.items():
        for pos in positions:
            word_pos.append((pos, word))
    word_pos.sort()
    return " ".join(w for _, w in word_pos)


def build_doi_index() -> dict[str, dict]:
    """openalex_raw 파일 전체를 읽어 DOI → {citation_count, abstract} 인덱스 생성"""
    index: dict[str, dict] = {}
    raw_files = sorted(RAW_DIR.glob("*.json"))
    print(f"캐시 파일 {len(raw_files)}개 읽는 중…")

    for i, fpath in enumerate(raw_files, 1):
        if i % 50 == 0:
            print(f"  {i}/{len(raw_files)} 처리 중…")
        try:
            with open(fpath, encoding="utf-8") as f:
                records = json.load(f)
        except Exception:
            continue

        for rec in records:
            doi = (rec.get("doi") or "").lower().strip()
            if not doi:
                continue
            index[doi] = {
                "citation_count": rec.get("citation_count", 0),
                "abstract":       rec.get("abstract", ""),
                "open_access":    rec.get("open_access", False),
            }

    print(f"  DOI 인덱스 크기: {len(index):,}")
    return index


def main():
    print(f"Loading {IN_FILE}…")
    with open(IN_FILE, encoding="utf-8") as f:
        papers = json.load(f)
    print(f"  {len(papers):,} papers")

    doi_index = build_doi_index()

    enriched = []
    hit = 0
    for p in papers:
        doi = (p.get("doi") or "").lower().strip()
        if doi and doi in doi_index:
            p.update(doi_index[doi])
            hit += 1
        enriched.append(p)

    print(f"\n인용수·초록 보강: {hit:,} / {len(papers):,} papers")

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)
    print(f"✓ {OUT_FILE} 저장 완료")


if __name__ == "__main__":
    main()
