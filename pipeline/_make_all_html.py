"""
explorer.html 생성기
--------------------
all_enriched.json 데이터를 읽어 논문 검색/필터 인터페이스를 생성합니다.

Usage:
    python _make_all_html.py
Output:
    ../explorer.html
"""

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from venues_config import VENUES_CFG, CATEGORY_COLORS

IN_FILE  = Path(__file__).parent / "all_enriched.json"
OUT_FILE = Path(__file__).parent.parent / "explorer.html"

TODAY = date.today().isoformat()


def load_papers() -> list[dict]:
    if not IN_FILE.exists():
        fallback = Path(__file__).parent / "all_dblp.json"
        with open(fallback, encoding="utf-8") as f:
            return json.load(f)
    with open(IN_FILE, encoding="utf-8") as f:
        return json.load(f)


def make_venue_checkboxes() -> str:
    lines = []
    current_cat = None
    for v in VENUES_CFG:
        cat = v["category"]
        if cat != current_cat:
            if current_cat is not None:
                lines.append("</div>")
            cat_color = CATEGORY_COLORS.get(cat, "#999")
            lines.append(
                f'<div class="venue-group">'
                f'<span class="group-label" style="color:{cat_color}">{cat}</span>'
            )
            current_cat = cat
        color = v["color"]
        vid   = v["id"]
        label = v["label"]
        lines.append(
            f'<label class="venue-cb">'
            f'<input type="checkbox" value="{vid}" checked onchange="applyFilters()">'
            f'<span class="dot" style="background:{color}"></span>{label}'
            f'</label>'
        )
    if current_cat:
        lines.append("</div>")
    return "\n".join(lines)


def build_venue_color_js() -> str:
    mapping = {v["id"]: v["color"] for v in VENUES_CFG}
    return f"const VENUE_COLORS = {json.dumps(mapping, ensure_ascii=False)};"


def main():
    papers = load_papers()

    venue_checkboxes = make_venue_checkboxes()
    venue_color_js   = build_venue_color_js()
    n_papers = len(papers)
    del papers  # 메모리 절약 — HTML에는 인라인으로 넣지 않음

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Paper Atlas — Explorer</title>
<style>
  :root {{
    --bg: #0f1117; --surface: #1a1d27; --border: #2d3148;
    --text: #e2e8f0; --muted: #718096; --accent: #4f9cf9;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: system-ui, sans-serif; font-size: 14px; }}
  header {{ padding: 16px 24px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 16px; }}
  header h1 {{ font-size: 18px; font-weight: 700; }}
  header .stamp {{ color: var(--muted); font-size: 12px; }}
  .layout {{ display: flex; height: calc(100vh - 57px); }}
  aside {{ width: 220px; min-width: 220px; border-right: 1px solid var(--border); overflow-y: auto; padding: 12px; }}
  .search-bar {{ padding: 8px 16px; border-bottom: 1px solid var(--border); display: flex; gap: 8px; align-items: center; }}
  .search-bar input {{ flex: 1; background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
                       color: var(--text); padding: 6px 10px; outline: none; }}
  .search-bar select {{ background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
                        color: var(--text); padding: 6px 8px; outline: none; }}
  main {{ flex: 1; overflow-y: auto; }}
  table {{ width: 100%; border-collapse: collapse; }}
  thead th {{ background: var(--surface); padding: 8px 12px; text-align: left; font-size: 12px;
              color: var(--muted); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 1; cursor: pointer; }}
  thead th:hover {{ color: var(--text); }}
  tbody tr {{ border-bottom: 1px solid var(--border); transition: background .1s; }}
  tbody tr:hover {{ background: var(--surface); }}
  td {{ padding: 8px 12px; vertical-align: top; }}
  td.title a {{ color: var(--accent); text-decoration: none; font-weight: 500; }}
  td.title a:hover {{ text-decoration: underline; }}
  td.authors {{ color: var(--muted); font-size: 12px; max-width: 220px; }}
  td.cite {{ text-align: right; color: #f6c90e; font-weight: 600; }}
  .badge {{ display: inline-block; padding: 2px 7px; border-radius: 10px; font-size: 11px;
            font-weight: 600; color: #fff; white-space: nowrap; }}
  .venue-group {{ margin-bottom: 8px; }}
  .group-label {{ font-size: 11px; font-weight: 700; text-transform: uppercase;
                  letter-spacing: .5px; display: block; margin-bottom: 4px; }}
  .venue-cb {{ display: flex; align-items: center; gap: 5px; cursor: pointer;
               font-size: 12px; padding: 2px 0; white-space: nowrap; }}
  .venue-cb input {{ accent-color: var(--accent); }}
  .dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}
  #count {{ color: var(--muted); font-size: 12px; padding: 0 16px; line-height: 36px; }}
  .year-filter {{ display: flex; gap: 8px; align-items: center; font-size: 12px; color: var(--muted); }}
  .year-filter input {{ width: 60px; background: var(--surface); border: 1px solid var(--border);
                        border-radius: 4px; color: var(--text); padding: 3px 6px; }}
  /* keyword search */
  .kw-row {{ display: flex; align-items: center; gap: 6px; padding: 6px 16px;
             border-bottom: 1px solid var(--border); flex-wrap: wrap; }}
  .kw-input {{ background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
               color: var(--text); padding: 5px 10px; outline: none; width: 180px; font-size: 13px; }}
  .kw-input:focus {{ border-color: var(--accent); }}
  .kw-input.has-value {{ border-color: var(--accent); background: #1a2035; }}
  .op-btn {{ display: flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }}
  .op-btn button {{ background: var(--surface); border: none; color: var(--muted); padding: 4px 10px;
                    font-size: 11px; font-weight: 700; cursor: pointer; letter-spacing: .5px; }}
  .op-btn button.active {{ background: var(--accent); color: #fff; }}
  .kw-scope {{ background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
               color: var(--text); padding: 4px 8px; font-size: 12px; outline: none; }}
  .kw-clear {{ background: none; border: 1px solid var(--border); border-radius: 6px; color: var(--muted);
               padding: 4px 10px; font-size: 12px; cursor: pointer; }}
  .kw-clear:hover {{ color: var(--text); border-color: var(--text); }}
  .kw-label {{ font-size: 11px; color: var(--muted); font-weight: 600; white-space: nowrap; }}
</style>
</head>
<body>
<header>
  <h1>📄 Paper Atlas — Explorer</h1>
  <span class="stamp">Updated {TODAY}</span>
  <span class="stamp" style="margin-left:auto">
    {n_papers:,} papers · {len(VENUES_CFG)} journals
  </span>
</header>
<div class="layout">
  <aside>
    <div style="font-size:11px;color:var(--muted);margin-bottom:8px;font-weight:700;text-transform:uppercase;">Journals</div>
    <label style="display:flex;align-items:center;gap:5px;font-size:12px;margin-bottom:8px;cursor:pointer;">
      <input type="checkbox" id="checkAll" checked onchange="toggleAll(this)"> All
    </label>
    {venue_checkboxes}
  </aside>
  <div style="flex:1;display:flex;flex-direction:column;overflow:hidden;">
    <!-- 키워드 검색 행 -->
    <div class="kw-row">
      <span class="kw-label">KEYWORD</span>
      <input class="kw-input" id="kw1" placeholder="Keyword 1…" oninput="onKwInput(this,'kw1')">
      <div class="op-btn" id="op12">
        <button class="active" onclick="setOp('op12','AND',this)">AND</button>
        <button onclick="setOp('op12','OR',this)">OR</button>
      </div>
      <input class="kw-input" id="kw2" placeholder="Keyword 2…" oninput="onKwInput(this,'kw2')">
      <div class="op-btn" id="op23">
        <button class="active" onclick="setOp('op23','AND',this)">AND</button>
        <button onclick="setOp('op23','OR',this)">OR</button>
      </div>
      <input class="kw-input" id="kw3" placeholder="Keyword 3…" oninput="onKwInput(this,'kw3')">
      <select class="kw-scope" id="kwScope" onchange="applyFilters()" title="검색 범위">
        <option value="title">Title</option>
        <option value="title_abstract" selected>Title + Abstract</option>
        <option value="all">Title + Abstract + Authors</option>
      </select>
      <button class="kw-clear" onclick="clearKeywords()">✕ Clear</button>
    </div>
    <!-- 기본 필터 행 -->
    <div class="search-bar">
      <div class="year-filter">
        <span>Year</span>
        <input type="number" id="yearFrom" placeholder="from" oninput="applyFilters()">
        <span>–</span>
        <input type="number" id="yearTo" placeholder="to" oninput="applyFilters()">
      </div>
      <select id="sortBy" onchange="applyFilters()">
        <option value="year_desc">Year ↓</option>
        <option value="year_asc">Year ↑</option>
        <option value="cite_desc">Citations ↓</option>
        <option value="title_asc">Title ↑</option>
      </select>
      <span id="count"></span>
    </div>
    <main>
      <table>
        <thead>
          <tr>
            <th style="width:60px">Year</th>
            <th style="width:90px">Journal</th>
            <th>Title</th>
            <th style="width:200px">Authors</th>
            <th style="width:70px" title="Citation count">Cited</th>
          </tr>
        </thead>
        <tbody id="tbody"></tbody>
      </table>
    </main>
  </div>
</div>
<script>
{venue_color_js}
// papers.json을 fetch로 로드 (필드 단축키: v=venue_id, j=venue, y=year, t=title, a=authors, d=doi, c=citation_count, ab=abstract)
let ALL_PAPERS = [];
const PAGE_SIZE = 200;
let filtered = [];
let page = 0;
let loading = false;
let dataLoaded = false;

// ── AND/OR 키워드 상태 ──────────────────────────────────────────────
const OPS = {{ op12: 'AND', op23: 'AND' }};

function setOp(groupId, op, btn) {{
  OPS[groupId] = op;
  document.querySelectorAll(`#${{groupId}} button`).forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}}

function onKwInput(el, id) {{
  el.classList.toggle('has-value', el.value.trim() !== '');
  applyFilters();
}}

function clearKeywords() {{
  ['kw1','kw2','kw3'].forEach(id => {{
    const el = document.getElementById(id);
    el.value = '';
    el.classList.remove('has-value');
  }});
  applyFilters();
}}

function kwMatch(haystack, kws, ops) {{
  // kws = [kw1, kw2, kw3], ops = [op12, op23]
  // 빈 키워드 무시, 왼쪽부터 순서대로 AND/OR 적용
  const terms = kws.map(k => k.toLowerCase().trim()).filter(k => k);
  if (!terms.length) return true;

  let result = haystack.includes(terms[0]);
  for (let i = 1; i < terms.length; i++) {{
    const op  = ops[i - 1];
    const hit = haystack.includes(terms[i]);
    result = op === 'AND' ? (result && hit) : (result || hit);
  }}
  return result;
}}

function toggleAll(cb) {{
  document.querySelectorAll('.venue-cb input').forEach(c => {{ c.checked = cb.checked; }});
  applyFilters();
}}

function applyFilters() {{
  if (!dataLoaded) return;
  const kw1   = document.getElementById('kw1').value;
  const kw2   = document.getElementById('kw2').value;
  const kw3   = document.getElementById('kw3').value;
  const scope = document.getElementById('kwScope').value;
  const yearFrom = parseInt(document.getElementById('yearFrom').value) || 0;
  const yearTo   = parseInt(document.getElementById('yearTo').value)   || 9999;
  const checked  = new Set([...document.querySelectorAll('.venue-cb input:checked')].map(c => c.value));
  const sort     = document.getElementById('sortBy').value;
  const ops = [OPS.op12, OPS.op23];

  filtered = ALL_PAPERS.filter(p => {{
    if (!checked.has(p.venue_id)) return false;
    const yr = parseInt(p.year) || 0;
    if (yr < yearFrom || yr > yearTo) return false;

    const title    = (p.title || '').toLowerCase();
    const abstract = (p.abstract || '').toLowerCase();
    const authors  = (Array.isArray(p.authors) ? p.authors.join(' ') : (p.authors || '')).toLowerCase();

    let haystack;
    if      (scope === 'title')           haystack = title;
    else if (scope === 'title_abstract')  haystack = title + ' ' + abstract;
    else                                   haystack = title + ' ' + abstract + ' ' + authors;

    if (!kwMatch(haystack, [kw1, kw2, kw3], ops)) return false;
    return true;
  }});

  if      (sort === 'year_desc') filtered.sort((a,b) => (b.year||0)-(a.year||0));
  else if (sort === 'year_asc')  filtered.sort((a,b) => (a.year||0)-(b.year||0));
  else if (sort === 'cite_desc') filtered.sort((a,b) => (b.citation_count||0)-(a.citation_count||0));
  else if (sort === 'title_asc') filtered.sort((a,b) => (a.title||'').localeCompare(b.title||''));

  document.getElementById('count').textContent = filtered.length.toLocaleString() + ' papers';
  page = 0;
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = '';
  renderPage();
}}

function renderPage() {{
  if (loading) return;
  const start = page * PAGE_SIZE;
  const slice = filtered.slice(start, start + PAGE_SIZE);
  if (!slice.length) return;
  loading = true;
  const frag = document.createDocumentFragment();
  slice.forEach(p => {{
    const tr = document.createElement('tr');
    const color = VENUE_COLORS[p.venue_id] || '#999';
    const doi   = p.doi ? `https://doi.org/${{p.doi}}` : (p.url || '#');
    const authors = Array.isArray(p.authors) ? p.authors.join(', ') : (p.authors || '');
    const short_authors = authors.length > 80 ? authors.slice(0,80)+'…' : authors;
    tr.innerHTML = `
      <td>${{p.year||''}}</td>
      <td><span class="badge" style="background:${{color}}">${{p.venue||''}}</span></td>
      <td class="title"><a href="${{doi}}" target="_blank" rel="noopener">${{escHtml(p.title||'')}}</a></td>
      <td class="authors" title="${{escHtml(authors)}}">${{escHtml(short_authors)}}</td>
      <td class="cite">${{p.citation_count||''}}</td>
    `;
    frag.appendChild(tr);
  }});
  document.getElementById('tbody').appendChild(frag);
  page++;
  loading = false;
}}

function escHtml(s) {{
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

// infinite scroll
document.querySelector('main').addEventListener('scroll', function() {{
  if (this.scrollTop + this.clientHeight >= this.scrollHeight - 200) renderPage();
}});

// papers.json 로드
(async function() {{
  const status = document.getElementById('count');
  status.textContent = '데이터 로딩 중…';
  try {{
    const res = await fetch('papers.json');
    if (!res.ok) throw new Error('papers.json 로드 실패: ' + res.status);
    const raw = await res.json();
    // 단축 필드 → 표준 필드로 변환
    ALL_PAPERS = raw.map(p => ({{
      venue_id:       p.v || '',
      venue:          p.j || '',
      year:           p.y || 0,
      title:          p.t || '',
      authors:        p.a || [],
      doi:            p.d || '',
      citation_count: p.c || 0,
      abstract:       p.ab || '',
    }}));
    dataLoaded = true;
    applyFilters();
  }} catch(e) {{
    status.textContent = '⚠️ 데이터 로드 실패: ' + e.message;
    console.error(e);
  }}
}})();
</script>
</body>
</html>"""

    OUT_FILE.write_text(html, encoding="utf-8")
    print(f"✓ {OUT_FILE} ({n_papers:,} papers)")


if __name__ == "__main__":
    main()
