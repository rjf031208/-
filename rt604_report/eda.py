# -*- coding: utf-8 -*-
"""
RT604 Take-Home Quiz — Quantitative EDA
Topic: Predictor-based control for time-delay systems (UAV applications)
Data source: author's own "Paper Search" atlas (27 venues), file papers.json
Reproducible filter (mirrors the Explorer tool):
    keyword1 = "predict"  AND  keyword2 = "delay"   (scope = Title + Abstract)
    matching = accent-stripped, lowercased substring (same as the website)
"""
import json, re, unicodedata, csv
from collections import Counter, defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(r"C:\Users\user\Downloads\rt604_report")
OUT.mkdir(parents=True, exist_ok=True)
PAPERS = Path(r"C:\Users\user\Documents\논문 찾기\claude\papers.json")

# venue colors (same palette as the atlas)
VENUE_COLORS = {"tro":"#1f77b4","ijrr":"#4c9fda","scirob":"#17becf","ral":"#0a5fa8","jirs":"#6baed6",
 "tcst":"#1a7a1a","tac":"#2ca02c","automatica":"#52be52","cep":"#27ae60","jas":"#16a085","ijrnc":"#98df8a",
 "nonlindyn":"#3d8c3d","jfi":"#74c476","mechatronics":"#e67e22","tmech":"#ff7f0e","tie":"#d62728","tii":"#e07070",
 "eswa":"#f39c12","jaircraft":"#6a1b9a","taes":"#9467bd","jgcd":"#c5b0d5","ast":"#7b4d9e","unmanned":"#e74c3c",
 "drones":"#c0392b","tits":"#8c564b","tvt":"#c49c94","tiv":"#5b3a29"}

def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()

STOP = set("""the a an of for and or to in on with via using use used based from by at as is are be this
that these those its it we our can new novel approach approaches method methods study analysis toward
towards under over into between their they than when which while also such some non vol no pp part case
cases paper results result two three one high low large small more most about through within without
during each both all has have""".split())

def is_word(w):
    return len(w) >= 3 and w not in STOP and not w.isdigit() and not set(w) <= {"-"}

UAV_RE = re.compile(r"uav|quadrotor|multirotor|drone|aerial|helicopter|aircraft|rotorcraft|fixed-wing")

print("Loading", PAPERS)
data = json.loads(PAPERS.read_text(encoding="utf-8"))
print("  total papers:", len(data))

# ---- filter: predict AND delay in (title+abstract) ----
sel = []
for p in data:
    hay = norm((p.get("t","") or "") + " " + (p.get("ab","") or ""))
    if "predict" in hay and "delay" in hay:
        sel.append(p)
print("  filtered (predict & delay):", len(sel))

uav = [p for p in sel if UAV_RE.search(norm((p.get("t","") or "")+" "+(p.get("ab","") or "")))]
print("  UAV sub-slice:", len(uav))

# ---- venue distribution ----
venue_counts = Counter(p.get("j","?") for p in sel)
vid_of = {}
for p in sel:
    vid_of[p.get("j","?")] = p.get("v","")
venue_sorted = venue_counts.most_common()

# ---- yearly counts by venue (stacked) ----
years = [p.get("y",0) for p in sel if 1990 <= (p.get("y",0) or 0) <= 2026]
ymin, ymax = min(years), max(years)
year_range = list(range(ymin, ymax+1))
# venue -> {year: count}
yv = defaultdict(lambda: defaultdict(int))
for p in sel:
    y = p.get("y",0)
    if ymin <= y <= ymax:
        yv[p.get("j","?")][y] += 1
# order venues by total
venue_order = [v for v,_ in venue_sorted]

# ---- keywords (title unigram + bigram) ----
uni, bi = Counter(), Counter()
for p in sel:
    words = re.sub(r"[^a-z0-9\s-]", " ", norm(p.get("t",""))).split()
    for i, w in enumerate(words):
        if is_word(w):
            uni[w] += 1
        if i+1 < len(words):
            w2 = words[i+1]
            if is_word(w) and is_word(w2):
                bi[w+" "+w2] += 1
top_uni = uni.most_common(20)
top_bi  = bi.most_common(15)

# ---- top cited ----
top_cited = sorted(sel, key=lambda p: p.get("c",0) or 0, reverse=True)[:20]

# =================== OUTPUTS ===================
# CSV export of the filtered set
with open(OUT/"filtered_set.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Year","Venue","Title","Authors","DOI","Citations"])
    for p in sorted(sel, key=lambda p:(-(p.get("c",0) or 0))):
        au = "; ".join(p.get("a",[])) if isinstance(p.get("a"),list) else (p.get("a") or "")
        doi = ("https://doi.org/"+p["d"]) if p.get("d") else ""
        w.writerow([p.get("y",""), p.get("j",""), p.get("t",""), au, doi, p.get("c",0)])

# summary text
with open(OUT/"summary.txt","w",encoding="utf-8") as f:
    f.write(f"TOTAL atlas papers: {len(data)}\n")
    f.write(f"FILTERED (predict AND delay, title+abstract): {len(sel)}\n")
    f.write(f"UAV sub-slice: {len(uav)}\n")
    f.write(f"Year span: {ymin}-{ymax}\n")
    f.write(f"Venues represented: {len(venue_counts)}\n\n")
    f.write("VENUE DISTRIBUTION:\n")
    for v,c in venue_sorted:
        f.write(f"  {v:14s} {c:5d}  ({c/len(sel)*100:4.1f}%)\n")
    f.write("\nTOP UNIGRAMS:\n")
    for w,c in top_uni: f.write(f"  {w:22s} {c}\n")
    f.write("\nTOP BIGRAMS:\n")
    for w,c in top_bi: f.write(f"  {w:30s} {c}\n")
    f.write("\nTOP CITED:\n")
    for p in top_cited:
        f.write(f"  [{p.get('c',0):5d}] {p.get('y','')} {p.get('j','')}: {p.get('t','')[:90]}\n")

plt.rcParams.update({"font.size":9, "figure.dpi":150})

# Fig 1: yearly stacked by venue (top venues, rest = Other)
TOPN = 8
top_venues = venue_order[:TOPN]
fig, ax = plt.subplots(figsize=(7.2,3.6))
bottom = [0]*len(year_range)
for v in top_venues:
    vals = [yv[v].get(y,0) for y in year_range]
    ax.bar(year_range, vals, bottom=bottom, label=v, color=VENUE_COLORS.get(vid_of.get(v,""), "#888"))
    bottom = [b+x for b,x in zip(bottom,vals)]
# other venues
other = [sum(yv[v].get(y,0) for v in venue_order[TOPN:]) for y in year_range]
if any(other):
    ax.bar(year_range, other, bottom=bottom, label="Other", color="#555")
ax.set_xlabel("Year"); ax.set_ylabel("Papers"); ax.set_title("Yearly publications (stacked by venue)")
ax.legend(fontsize=7, ncol=3, loc="upper left")
fig.tight_layout(); fig.savefig(OUT/"fig_year.pdf"); fig.savefig(OUT/"fig_year.png"); plt.close(fig)

# Fig 2: venue distribution (horizontal bar)
fig, ax = plt.subplots(figsize=(7.2,4.2))
labels = [v for v,_ in venue_sorted]
vals = [c for _,c in venue_sorted]
colors = [VENUE_COLORS.get(vid_of.get(v,""), "#888") for v in labels]
ax.barh(labels[::-1], vals[::-1], color=colors[::-1])
ax.set_xlabel("Papers"); ax.set_title("Venue distribution of the filtered set")
for i,val in enumerate(vals[::-1]):
    ax.text(val+0.5, i, str(val), va="center", fontsize=7)
fig.tight_layout(); fig.savefig(OUT/"fig_venue.pdf"); fig.savefig(OUT/"fig_venue.png"); plt.close(fig)

# Fig 3: top unigrams
fig, ax = plt.subplots(figsize=(7.2,4.2))
kw = [w for w,_ in top_uni][::-1]; kc=[c for _,c in top_uni][::-1]
ax.barh(kw, kc, color="#4f9cf9")
ax.set_xlabel("Title frequency"); ax.set_title("Top-20 title keywords (unigrams)")
fig.tight_layout(); fig.savefig(OUT/"fig_kw.pdf"); fig.savefig(OUT/"fig_kw.png"); plt.close(fig)

print("Done. Outputs in", OUT)
