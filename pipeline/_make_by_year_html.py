"""
by_year.html 생성기
--------------------
연도별 논문 수 트렌드를 시각화하는 HTML을 생성합니다.

Usage:
    python _make_by_year_html.py
Output:
    ../by_year.html
"""

import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from venues_config import VENUES_CFG, CATEGORY_COLORS

IN_FILE  = Path(__file__).parent / "all_enriched.json"
OUT_FILE = Path(__file__).parent.parent / "by_year.html"
TODAY    = date.today().isoformat()


def load_papers() -> list[dict]:
    src = IN_FILE if IN_FILE.exists() else Path(__file__).parent / "all_dblp.json"
    with open(src, encoding="utf-8") as f:
        return json.load(f)


def build_pivot(papers: list[dict]) -> tuple[list[int], dict[str, list[int]]]:
    years_set: set[int] = set()
    counts: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for p in papers:
        yr = int(p.get("year", 0) or 0)
        if yr < 1990 or yr > date.today().year:
            continue
        years_set.add(yr)
        counts[p.get("venue", "")][yr] += 1

    years = sorted(years_set)
    per_venue: dict[str, list[int]] = {}
    for v in VENUES_CFG:
        lbl = v["label"]
        per_venue[lbl] = [counts[lbl].get(y, 0) for y in years]
    return years, per_venue


def main():
    papers = load_papers()
    years, per_venue = build_pivot(papers)

    datasets_js = []
    for v in VENUES_CFG:
        lbl = v["label"]
        if lbl not in per_venue:
            continue
        datasets_js.append({
            "label":           lbl,
            "data":            per_venue[lbl],
            "backgroundColor": v["color"],
            "borderColor":     v["color"],
            "borderWidth":     2,
            "fill":            False,
            "tension":         0.3,
            "pointRadius":     2,
        })

    chart_data = json.dumps({"labels": years, "datasets": datasets_js}, ensure_ascii=False)

    # 카테고리별 범례 HTML
    legend_html_parts = []
    current_cat = None
    for v in VENUES_CFG:
        cat = v["category"]
        if cat != current_cat:
            if current_cat is not None:
                legend_html_parts.append("</div>")
            cat_color = CATEGORY_COLORS.get(cat, "#999")
            legend_html_parts.append(
                f'<div class="legend-group"><span class="legend-group-title" style="color:{cat_color}">{cat}</span>'
            )
            current_cat = cat
        legend_html_parts.append(
            f'<label class="legend-item">'
            f'<input type="checkbox" class="toggle-venue" data-label="{v["label"]}" checked>'
            f'<span class="legend-dot" style="background:{v["color"]}"></span>'
            f'{v["label"]}</label>'
        )
    if current_cat:
        legend_html_parts.append("</div>")
    legend_html = "\n".join(legend_html_parts)

    # 요약 통계
    total_by_venue = {v["label"]: sum(per_venue.get(v["label"], [])) for v in VENUES_CFG}

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Paper Atlas — By Year</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {{ --bg:#0f1117; --surface:#1a1d27; --border:#2d3148; --text:#e2e8f0; --muted:#718096; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text); font-family:system-ui,sans-serif; }}
  header {{ padding:16px 24px; border-bottom:1px solid var(--border); display:flex; align-items:center; gap:16px; }}
  header h1 {{ font-size:18px; font-weight:700; }}
  .stamp {{ color:var(--muted); font-size:12px; }}
  .container {{ display:flex; height:calc(100vh - 57px); }}
  aside {{ width:200px; min-width:200px; border-right:1px solid var(--border); overflow-y:auto; padding:12px; }}
  main {{ flex:1; padding:16px; overflow:auto; }}
  canvas {{ max-height:420px; }}
  .chart-mode {{ display:flex; gap:8px; margin-bottom:12px; }}
  .chart-mode button {{ background:var(--surface); border:1px solid var(--border); color:var(--text);
                        border-radius:6px; padding:4px 12px; cursor:pointer; font-size:13px; }}
  .chart-mode button.active {{ border-color:#4f9cf9; color:#4f9cf9; }}
  .legend-group {{ margin-bottom:8px; }}
  .legend-group-title {{ font-size:11px; font-weight:700; text-transform:uppercase;
                         letter-spacing:.5px; display:block; margin-bottom:4px; }}
  .legend-item {{ display:flex; align-items:center; gap:5px; cursor:pointer;
                  font-size:12px; padding:2px 0; white-space:nowrap; }}
  .legend-item input {{ accent-color:#4f9cf9; }}
  .legend-dot {{ width:10px; height:10px; border-radius:50%; flex-shrink:0; }}
  .summary-table {{ margin-top:24px; width:100%; border-collapse:collapse; font-size:13px; }}
  .summary-table th {{ background:var(--surface); padding:6px 10px; text-align:left;
                       border-bottom:1px solid var(--border); color:var(--muted); font-size:11px; }}
  .summary-table td {{ padding:6px 10px; border-bottom:1px solid var(--border); }}
</style>
</head>
<body>
<header>
  <h1>📊 Paper Atlas — By Year</h1>
  <span class="stamp">Updated {TODAY}</span>
  <span class="stamp" style="margin-left:auto">{len(papers):,} total papers</span>
</header>
<div class="container">
  <aside>
    <div style="font-size:11px;color:var(--muted);margin-bottom:8px;font-weight:700;text-transform:uppercase;">Journals</div>
    <label style="display:flex;align-items:center;gap:5px;font-size:12px;margin-bottom:8px;cursor:pointer;">
      <input type="checkbox" id="checkAll" checked onchange="toggleAll(this)"> All
    </label>
    {legend_html}
  </aside>
  <main>
    <div class="chart-mode">
      <button class="active" onclick="setMode('line',this)">Line</button>
      <button onclick="setMode('bar',this)">Stacked Bar</button>
    </div>
    <canvas id="chart"></canvas>
    <table class="summary-table">
      <thead><tr><th>Journal</th><th>Category</th><th>Since</th><th>Total Papers</th></tr></thead>
      <tbody>
        {"".join(
            f'<tr><td><b>{v["label"]}</b></td><td>{v["category"]}</td><td>{v["since"]}</td>'
            f'<td>{total_by_venue.get(v["label"], 0):,}</td></tr>'
            for v in VENUES_CFG
        )}
      </tbody>
    </table>
  </main>
</div>
<script>
const RAW = {chart_data};
let chartObj = null;
let currentMode = 'line';

function buildDatasets(mode) {{
  return RAW.datasets.map(ds => ({{
    ...ds,
    type: mode === 'bar' ? 'bar' : 'line',
    stack: mode === 'bar' ? 'stack' : undefined,
    fill: mode === 'bar',
  }}));
}}

function initChart(mode) {{
  if (chartObj) chartObj.destroy();
  const ctx = document.getElementById('chart').getContext('2d');
  chartObj = new Chart(ctx, {{
    type: mode === 'bar' ? 'bar' : 'line',
    data: {{ labels: RAW.labels, datasets: buildDatasets(mode) }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ ticks: {{ color: '#718096' }}, grid: {{ color: '#2d3148' }} }},
        y: {{ stacked: mode === 'bar', ticks: {{ color: '#718096' }}, grid: {{ color: '#2d3148' }} }},
      }},
    }},
  }});
}}

function setMode(mode, btn) {{
  document.querySelectorAll('.chart-mode button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentMode = mode;
  initChart(mode);
  syncVisibility();
}}

function toggleAll(cb) {{
  document.querySelectorAll('.toggle-venue').forEach(c => c.checked = cb.checked);
  syncVisibility();
}}

function syncVisibility() {{
  const checked = new Set([...document.querySelectorAll('.toggle-venue:checked')].map(c => c.dataset.label));
  chartObj.data.datasets.forEach(ds => {{
    ds.hidden = !checked.has(ds.label);
  }});
  chartObj.update();
}}

document.querySelectorAll('.toggle-venue').forEach(cb => {{
  cb.addEventListener('change', syncVisibility);
}});

initChart('line');
</script>
</body>
</html>"""

    OUT_FILE.write_text(html, encoding="utf-8")
    print(f"✓ {OUT_FILE}")


if __name__ == "__main__":
    main()
