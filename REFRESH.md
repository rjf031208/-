# Paper Atlas — 데이터 수집 및 업데이트 가이드

## 저널 구성

| 카테고리 | 약어 | 전체 이름 | 출처 |
|---|---|---|---|
| Mechatronics | T-Mech | IEEE/ASME Transactions on Mechatronics | DBLP |
| Mechatronics | T-IE | IEEE Transactions on Industrial Electronics | DBLP |
| Mechatronics | T-II | IEEE Transactions on Industrial Informatics | DBLP |
| Aerospace | T-AES | IEEE Transactions on Aerospace and Electronic Systems | DBLP |
| Aerospace | JGCD | Journal of Guidance, Control, and Dynamics | OpenAlex |
| Aerospace | AST | Aerospace Science and Technology | OpenAlex |
| Control Theory | T-AC | IEEE Transactions on Automatic Control | DBLP |
| Control Theory | Automatica | Automatica | DBLP |
| Control Theory | IJRNC | Intl. Journal of Robust and Nonlinear Control | OpenAlex |
| Control Theory | NonlinDyn | Nonlinear Dynamics | OpenAlex |
| Control Theory | JFI | Journal of the Franklin Institute | OpenAlex |
| Robotics | T-RO | IEEE Transactions on Robotics | DBLP |
| Robotics | IJRR | The International Journal of Robotics Research | DBLP |
| Robotics | Sci-Rob | Science Robotics | OpenAlex |
| Vehicle | T-ITS | IEEE Transactions on Intelligent Transportation Systems | DBLP |
| Vehicle | T-VT | IEEE Transactions on Vehicular Technology | DBLP |
| Vehicle | T-IV | IEEE Transactions on Intelligent Vehicles | DBLP |

---

## 사전 준비

```bash
pip install requests pandas openpyxl xlsxwriter
```

`step1_extra_openalex.py`와 `step2_openalex.py` 상단의 `MAILTO` 변수에
본인 이메일을 입력하면 OpenAlex rate limit이 완화됩니다.

```python
MAILTO = "your_email@example.com"   # ← 본인 이메일로 교체
```

---

## 전체 수집 (최초 실행)

```bash
cd pipeline

# 1a. DBLP에서 수집 (예상 소요: 30–60분)
python step1_dblp.py

# 1b. OpenAlex에서 DBLP 누락 저널 수집 (예상: 10–20분)
python step1_extra_openalex.py

# 2. 인용수 · 초록 보강 (예상: 1–3시간, 중단 후 재실행 가능)
python step2_openalex.py

# 3. Excel 출력
python step3_excel.py

# HTML 생성
python _make_all_html.py
python _make_by_year_html.py
```

완료 후 `index.html`을 브라우저로 열면 됩니다.

---

## 정기 업데이트 (최근 2년만)

```bash
cd pipeline
python refresh_recent.py          # 최근 2년
python refresh_recent.py --years 3  # 최근 3년
```

---

## 저널 추가/제거

`pipeline/venues_config.py`만 수정하면 됩니다.

- **DBLP에 있는 저널** → `DBLP_VENUES` 리스트에 추가
  ```python
  ("key", "journals/dblp-stream", "Label", range(start_year, 2027)),
  ```
  DBLP stream 키는 https://dblp.org/db/journals/ 에서 확인

- **DBLP에 없는 저널** → `OPENALEX_VENUES` 리스트에 추가
  ```python
  {"key": "key", "label": "Label", "issn_l": "XXXX-XXXX", "years": range(start_year, 2027)},
  ```
  ISSN은 https://portal.issn.org 또는 저널 홈페이지에서 확인

- **시각화 설정** → `VENUES_CFG`에도 동일 항목 추가
  ```python
  {"label": "Label", "id": "key", "color": "#hexcolor", "since": start_year, "category": "Category"},
  ```

---

## 파일 구조

```
claude/
├── index.html          ← 랜딩 페이지
├── explorer.html       ← 논문 검색 (생성 후 표시)
├── by_year.html        ← 연도별 트렌드 (생성 후 표시)
├── atlas_all.xlsx      ← 전체 데이터 Excel (생성 후 표시)
├── by_venue/           ← 저널별 xlsx
└── pipeline/
    ├── venues_config.py          ← ★ 저널 목록 (여기만 수정)
    ├── step1_dblp.py             ← DBLP 수집
    ├── step1_extra_openalex.py   ← OpenAlex 수집
    ├── step2_openalex.py         ← 인용수/초록 보강
    ├── step3_excel.py            ← Excel 출력
    ├── _make_all_html.py         ← explorer.html 생성
    ├── _make_by_year_html.py     ← by_year.html 생성
    ├── refresh_recent.py         ← 빠른 업데이트
    ├── dblp_raw/                 ← DBLP 캐시
    └── openalex_raw/             ← OpenAlex 캐시
```
