"""
웹 배포용 경량 papers.json 생성
--------------------------------
all_enriched.json에서 필요한 필드만 추출하고 abstracts를 truncate해
파일 크기를 GitHub 100MB 제한 이내로 줄입니다.

Output: ../papers.json
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from venues_config import VENUES_CFG

IN_FILE  = Path(__file__).parent / "all_enriched.json"
OUT_FILE = Path(__file__).parent.parent / "papers.json"

LABEL_TO_ID = {v["label"]: v["id"] for v in VENUES_CFG}
ABSTRACT_LIMIT = 400   # 초록 최대 글자 수 (키워드 검색용)
MAX_AUTHORS    = 5     # 저자 최대 표시 수


def slim(p: dict) -> dict:
    authors_raw = p.get("authors", [])
    if isinstance(authors_raw, list):
        authors = authors_raw[:MAX_AUTHORS]
    else:
        authors = str(authors_raw or "").split("; ")[:MAX_AUTHORS]

    abstract = (p.get("abstract") or "").strip()
    if len(abstract) > ABSTRACT_LIMIT:
        abstract = abstract[:ABSTRACT_LIMIT] + "…"

    venue = p.get("venue", "")
    return {
        "v":  LABEL_TO_ID.get(venue, venue.lower()),  # venue_id
        "j":  venue,                                    # journal label
        "y":  int(p.get("year") or 0),
        "t":  (p.get("title") or "").strip(),
        "a":  authors,
        "d":  (p.get("doi") or "").strip(),
        "c":  int(p.get("citation_count") or 0),
        "ab": abstract,
    }


def main():
    print(f"Loading {IN_FILE}…")
    with open(IN_FILE, encoding="utf-8") as f:
        papers = json.load(f)
    print(f"  {len(papers):,} papers")

    slimmed = [slim(p) for p in papers]

    # 최소 분리자로 직렬화 (공백 없음)
    out = json.dumps(slimmed, ensure_ascii=False, separators=(",", ":"))

    size_mb = len(out.encode("utf-8")) / 1024 / 1024
    print(f"  Slim JSON: {size_mb:.1f} MB")

    OUT_FILE.write_text(out, encoding="utf-8")
    print(f"✓ {OUT_FILE}")


if __name__ == "__main__":
    main()
