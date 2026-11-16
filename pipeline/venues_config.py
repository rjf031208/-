"""
Central venue configuration for the paper atlas pipeline.
Modify OPENALEX_VENUES (journals) and CROSSREF_CONFS (conferences) to change what is collected.
Modify VENUES_CFG to change visualization settings.
"""

import datetime

# 수집 종료연도(미포함) — 올해까지 자동 포함. 하드코딩하면 해가 바뀔 때
# 신규 논문이 조용히 누락되므로 반드시 동적으로 계산한다.
END_YEAR = datetime.date.today().year + 1

# ── OpenAlex ISSN 수집 대상 ────────────────────────────────────────────────────
# 저널은 전부 OpenAlex에서 ISSN으로 수집한다.
# issn_l : 저널의 print ISSN

OPENALEX_VENUES = [
    # ── Robotics ──────────────────────────────────────────────────────────────
    {
        "key":    "tro",
        "label":  "T-RO",
        "issn_l": "1552-3098",   # IEEE Transactions on Robotics
        "years":  range(2004, END_YEAR),
    },
    {
        "key":    "ijrr",
        "label":  "IJRR",
        "issn_l": "0278-3649",   # The International Journal of Robotics Research
        "years":  range(2000, END_YEAR),
    },
    {
        "key":    "scirob",
        "label":  "Sci-Rob",
        "issn_l": "2470-9476",   # Science Robotics
        "years":  range(2016, END_YEAR),
    },
    {
        "key":    "ral",
        "label":  "RAL",
        "issn_l": "2377-3766",   # IEEE Robotics and Automation Letters
        "years":  range(2016, END_YEAR),
    },
    {
        "key":    "jirs",
        "label":  "JIRS",
        "issn_l": "0921-0296",   # Journal of Intelligent & Robotic Systems
        "years":  range(2000, END_YEAR),
    },

    # ── Control Theory ────────────────────────────────────────────────────────
    {
        "key":    "tcst",
        "label":  "T-CST",
        "issn_l": "1063-6536",   # IEEE Transactions on Control Systems Technology
        "years":  range(1993, END_YEAR),
    },
    {
        "key":    "cep",
        "label":  "CEP",
        "issn_l": "0967-0661",   # Control Engineering Practice (IFAC/Elsevier)
        "years":  range(1993, END_YEAR),
    },
    {
        "key":    "jas",
        "label":  "JAS",
        "issn_l": "2329-9266",   # IEEE/CAA Journal of Automatica Sinica
        "years":  range(2014, END_YEAR),
    },
    {
        "key":    "tac",
        "label":  "T-AC",
        "issn_l": "0018-9286",   # IEEE Transactions on Automatic Control
        "years":  range(2000, END_YEAR),
    },
    {
        "key":    "automatica",
        "label":  "Automatica",
        "issn_l": "0005-1098",   # Automatica
        "years":  range(2000, END_YEAR),
    },
    {
        "key":    "ijrnc",
        "label":  "IJRNC",
        "issn_l": "1049-8923",   # Intl. Journal of Robust and Nonlinear Control
        "years":  range(2000, END_YEAR),
    },
    {
        "key":    "nonlindyn",
        "label":  "NonlinDyn",
        "issn_l": "0924-090X",   # Nonlinear Dynamics
        "years":  range(2000, END_YEAR),
    },
    {
        "key":    "jfi",
        "label":  "JFI",
        "issn_l": "0016-0032",   # Journal of the Franklin Institute
        "years":  range(2000, END_YEAR),
    },

    # ── Mechatronics ──────────────────────────────────────────────────────────
    {
        "key":    "mechatronics",
        "label":  "Mechatronics",
        "issn_l": "0957-4158",   # Mechatronics (Elsevier/IFAC)
        "years":  range(1991, END_YEAR),
    },
    {
        "key":    "tmech",
        "label":  "T-Mech",
        "issn_l": "1083-4435",   # IEEE/ASME Transactions on Mechatronics
        "years":  range(2000, END_YEAR),
    },
    {
        "key":    "tie",
        "label":  "T-IE",
        "issn_l": "0278-0046",   # IEEE Transactions on Industrial Electronics
        "years":  range(2000, END_YEAR),
    },
    {
        "key":    "tii",
        "label":  "T-II",
        "issn_l": "1551-3203",   # IEEE Transactions on Industrial Informatics
        "years":  range(2005, END_YEAR),
    },

    # ── Aerospace ─────────────────────────────────────────────────────────────
    {
        "key":    "jaircraft",
        "label":  "J.Aircraft",
        "issn_l": "0021-8669",   # Journal of Aircraft (AIAA)
        "years":  range(2000, END_YEAR),
    },
    {
        "key":    "taes",
        "label":  "T-AES",
        "issn_l": "0018-9251",   # IEEE Transactions on Aerospace and Electronic Systems
        "years":  range(2000, END_YEAR),
    },
    {
        "key":    "jgcd",
        "label":  "JGCD",
        "issn_l": "0731-5090",   # Journal of Guidance, Control, and Dynamics
        "years":  range(2000, END_YEAR),
    },
    {
        "key":    "ast",
        "label":  "AST",
        "issn_l": "1270-9638",   # Aerospace Science and Technology
        "years":  range(2000, END_YEAR),
    },

    # ── AI & Systems ─────────────────────────────────────────────────────────
    {
        "key":    "eswa",
        "label":  "ESWA",
        "issn_l": "0957-4174",   # Expert Systems with Applications (Elsevier)
        "years":  range(2000, END_YEAR),
    },
    {
        "key":    "iotj",
        "label":  "IoT-J",
        "issn_l": "2327-4662",   # IEEE Internet of Things Journal
        "years":  range(2014, END_YEAR),
    },

    # ── UAV ──────────────────────────────────────────────────────────────────
    {
        "key":    "unmanned",
        "label":  "UnmannedSys",
        "issn_l": "2301-3850",   # Unmanned Systems (World Scientific)
        "years":  range(2013, END_YEAR),
    },
    {
        "key":    "drones",
        "label":  "Drones",
        "issn_l": "2504-446X",   # Drones (MDPI)
        "years":  range(2017, END_YEAR),
    },

    # ── Vehicle / Transportation ──────────────────────────────────────────────
    {
        "key":    "tits",
        "label":  "T-ITS",
        "issn_l": "1524-9050",   # IEEE Transactions on Intelligent Transportation Systems
        "years":  range(2000, END_YEAR),
    },
    {
        "key":    "tvt",
        "label":  "T-VT",
        "issn_l": "0018-9545",   # IEEE Transactions on Vehicular Technology
        "years":  range(2000, END_YEAR),
    },
    {
        "key":    "tiv",
        "label":  "T-IV",
        "issn_l": "2379-8858",   # IEEE Transactions on Intelligent Vehicles
        "years":  range(2016, END_YEAR),
    },
]

# ── Crossref 수집 대상 (학회) ─────────────────────────────────────────────────
# ICRA/IROS/AIM 등 학회 논문은 OpenAlex에서 primary_location.source 가 비어 있어
# ISSN으로 수집할 수 없다. Crossref는 container-title(프로시딩 제목)로 조회 가능.
#   query   : Crossref 관련도 검색어 (해당 학회 논문이 상위에 정렬됨)
#   pattern : container-title 정규식 — 이 패턴에 맞는 것만 채택(오검출 차단)

CROSSREF_CONFS = [
    {
        "key":     "icra",
        "doi_stems": ["icra", "robot"],   # 이 학회의 DOI 어간 (10.1109/<어간>…)
        "label":   "ICRA",
        "query":   "IEEE International Conference on Robotics and Automation",
        "pattern": r"international conference on robotics and automation",
        "years":   range(2000, END_YEAR),
    },
    {
        "key":     "iros",
        "doi_stems": ["iros", "irds"],   # 이 학회의 DOI 어간 (10.1109/<어간>…)
        "label":   "IROS",
        "query":   "IEEE/RSJ International Conference on Intelligent Robots and Systems",
        "pattern": r"intelligent robots and systems?",   # 2002년은 단수 "System"
        "years":   range(2000, END_YEAR),
    },
    {
        "key":     "aim",
        "doi_stems": ["aim"],   # 이 학회의 DOI 어간 (10.1109/<어간>…)
        "label":   "AIM",
        "query":   "IEEE/ASME International Conference on Advanced Intelligent Mechatronics",
        "pattern": r"advanced intelligent mechatronics",
        "years":   range(2000, END_YEAR),
    },
]

# ── 시각화 설정 (HTML 생성기에서 사용) ─────────────────────────────────────────
# 카테고리별 색상 그룹으로 구성
VENUES_CFG = [
    # ── Robotics (파란 계열) ──────────────────────────────────────────────────
    {"label": "T-RO",       "id": "tro",        "color": "#1f77b4", "since": 2004, "category": "Robotics"},
    {"label": "IJRR",       "id": "ijrr",       "color": "#4c9fda", "since": 1982, "category": "Robotics"},
    {"label": "Sci-Rob",    "id": "scirob",     "color": "#17becf", "since": 2016, "category": "Robotics"},
    {"label": "RAL",        "id": "ral",        "color": "#0a5fa8", "since": 2016, "category": "Robotics"},
    {"label": "JIRS",       "id": "jirs",       "color": "#6baed6", "since": 1990, "category": "Robotics"},
    {"label": "ICRA",       "id": "icra",       "color": "#08306b", "since": 2000, "category": "Robotics"},
    {"label": "IROS",       "id": "iros",       "color": "#2b7bba", "since": 2000, "category": "Robotics"},

    # ── Control Theory (초록 계열) ────────────────────────────────────────────
    {"label": "T-CST",      "id": "tcst",       "color": "#1a7a1a", "since": 1993, "category": "Control Theory"},
    {"label": "T-AC",       "id": "tac",        "color": "#2ca02c", "since": 1990, "category": "Control Theory"},
    {"label": "Automatica", "id": "automatica", "color": "#52be52", "since": 1990, "category": "Control Theory"},
    {"label": "CEP",        "id": "cep",        "color": "#27ae60", "since": 1993, "category": "Control Theory"},
    {"label": "JAS",        "id": "jas",        "color": "#16a085", "since": 2014, "category": "Control Theory"},
    {"label": "IJRNC",      "id": "ijrnc",      "color": "#98df8a", "since": 2000, "category": "Control Theory"},
    {"label": "NonlinDyn",  "id": "nonlindyn",  "color": "#3d8c3d", "since": 2000, "category": "Control Theory"},
    {"label": "JFI",        "id": "jfi",        "color": "#74c476", "since": 2000, "category": "Control Theory"},

    # ── Mechatronics (주황/빨강 계열) ─────────────────────────────────────────
    {"label": "Mechatronics","id": "mechatronics","color": "#e67e22","since": 1991, "category": "Mechatronics"},
    {"label": "T-Mech",     "id": "tmech",      "color": "#ff7f0e", "since": 1996, "category": "Mechatronics"},
    {"label": "T-IE",       "id": "tie",        "color": "#d62728", "since": 2000, "category": "Mechatronics"},
    {"label": "T-II",       "id": "tii",        "color": "#e07070", "since": 2005, "category": "Mechatronics"},
    {"label": "AIM",        "id": "aim",        "color": "#a63603", "since": 2000, "category": "Mechatronics"},

    # ── AI & Systems (노란/황금 계열) ─────────────────────────────────────────
    {"label": "ESWA",       "id": "eswa",       "color": "#f39c12", "since": 2000, "category": "AI & Systems"},
    {"label": "IoT-J",      "id": "iotj",       "color": "#d4ac0d", "since": 2014, "category": "AI & Systems"},

    # ── Aerospace (보라 계열) ─────────────────────────────────────────────────
    {"label": "J.Aircraft", "id": "jaircraft",  "color": "#6a1b9a", "since": 2000, "category": "Aerospace"},
    {"label": "T-AES",      "id": "taes",       "color": "#9467bd", "since": 1990, "category": "Aerospace"},
    {"label": "JGCD",       "id": "jgcd",       "color": "#c5b0d5", "since": 2000, "category": "Aerospace"},
    {"label": "AST",        "id": "ast",        "color": "#7b4d9e", "since": 2000, "category": "Aerospace"},

    # ── UAV (빨강 계열) ───────────────────────────────────────────────────────
    {"label": "UnmannedSys","id": "unmanned",   "color": "#e74c3c", "since": 2013, "category": "UAV"},
    {"label": "Drones",     "id": "drones",     "color": "#c0392b", "since": 2017, "category": "UAV"},

    # ── Vehicle / Transportation (갈색/회색 계열) ─────────────────────────────
    {"label": "T-ITS",      "id": "tits",       "color": "#8c564b", "since": 2000, "category": "Vehicle"},
    {"label": "T-VT",       "id": "tvt",        "color": "#c49c94", "since": 2000, "category": "Vehicle"},
    {"label": "T-IV",       "id": "tiv",        "color": "#5b3a29", "since": 2016, "category": "Vehicle"},
]


CATEGORY_COLORS = {
    "Robotics":       "#1f77b4",
    "Control Theory": "#2ca02c",
    "Mechatronics":   "#ff7f0e",
    "Aerospace":      "#9467bd",
    "UAV":            "#e74c3c",
    "Vehicle":        "#8c564b",
    "AI & Systems":   "#f39c12",
}
