"""
Step 3: 정제된 데이터를 Excel로 출력
--------------------------------------
all_enriched.json → 저널별 xlsx + 통합 atlas_all.xlsx 생성

Output:
    ../by_venue/<LABEL>.xlsx   (저널별)
    ../atlas_all.xlsx          (전체 통합)
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from venues_config import VENUES_CFG, DEDUP_ORDER

IN_FILE      = Path(__file__).parent / "all_enriched.json"
BY_VENUE_DIR = Path(__file__).parent.parent / "by_venue"
ATLAS_FILE   = Path(__file__).parent.parent / "atlas_all.xlsx"
BY_VENUE_DIR.mkdir(exist_ok=True)

COLUMNS = ["venue", "year", "title", "authors", "doi", "citation_count",
           "abstract", "open_access", "url", "pages", "key"]


def load_and_dedup(path: Path) -> pd.DataFrame:
    with open(path, encoding="utf-8") as f:
        papers = json.load(f)

    # venue 우선순위 기반 cross-venue 중복 제거
    priority = {label: i for i, label in enumerate(DEDUP_ORDER)}
    papers.sort(key=lambda p: priority.get(p.get("venue", ""), 9999))

    seen_doi:   set[str] = set()
    seen_title: set[str] = set()
    deduped = []
    for p in papers:
        doi   = (p.get("doi",   "") or "").lower().strip()
        title = (p.get("title", "") or "").lower().strip()
        if doi   and doi   in seen_doi:   continue
        if title and title in seen_title: continue
        if doi:   seen_doi.add(doi)
        if title: seen_title.add(title)
        deduped.append(p)

    df = pd.DataFrame(deduped)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df["authors"] = df["authors"].apply(
        lambda a: "; ".join(a) if isinstance(a, list) else str(a or "")
    )
    df["citation_count"] = pd.to_numeric(df["citation_count"], errors="coerce").fillna(0).astype(int)
    return df[COLUMNS].sort_values(["year", "venue", "title"], ascending=[False, True, True])


def write_by_venue(df: pd.DataFrame):
    label_to_id = {v["label"]: v["id"] for v in VENUES_CFG}
    for label, group in df.groupby("venue"):
        safe = label.replace("/", "-").replace(" ", "_")
        out = BY_VENUE_DIR / f"{safe}.xlsx"
        group.to_excel(out, index=False)
        print(f"  {out.name}: {len(group)} papers")


def write_atlas(df: pd.DataFrame):
    # Sheet 1: 전체 데이터
    # Sheet 2: 연도×저널 피벗
    # Sheet 3: 저널별 요약

    pivot = df.pivot_table(index="year", columns="venue", values="title",
                           aggfunc="count", fill_value=0)
    pivot = pivot.sort_index(ascending=False)

    summary_rows = []
    for v in VENUES_CFG:
        sub = df[df["venue"] == v["label"]]
        if sub.empty:
            continue
        top = sub.nlargest(1, "citation_count").iloc[0]
        summary_rows.append({
            "venue":        v["label"],
            "category":     v["category"],
            "total_papers": len(sub),
            "since":        v["since"],
            "avg_citations": round(sub["citation_count"].mean(), 1),
            "top_cited_title": top["title"],
            "top_cited_count": int(top["citation_count"]),
        })
    summary = pd.DataFrame(summary_rows)

    with pd.ExcelWriter(ATLAS_FILE, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="All Papers", index=False)
        pivot.to_excel(writer, sheet_name="By Year")
        summary.to_excel(writer, sheet_name="Summary", index=False)
    print(f"\n✓ {ATLAS_FILE.name}: {len(df)} papers, {df['venue'].nunique()} venues")


def main():
    if not IN_FILE.exists():
        print(f"ERROR: {IN_FILE} not found. Run step2_openalex.py first.")
        return

    print(f"Loading {IN_FILE}…")
    df = load_and_dedup(IN_FILE)
    print(f"  {len(df)} papers after deduplication")

    print("\nWriting by-venue xlsx…")
    write_by_venue(df)

    print("\nWriting atlas_all.xlsx…")
    write_atlas(df)


if __name__ == "__main__":
    main()
