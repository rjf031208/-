# Paper Search — 데이터 수집·업데이트 가이드

사이트: https://rjf031208.github.io/-/

## 한 줄 요약

```bash
cd pipeline
GH_TOKEN=ghp_... python update.py --push
```

수집 → 학회 → 인용수 → 학회 초록 → 배포 파일 생성 → 커밋·푸시 → GitHub Pages 배포 확인까지 한 번에 실행한다.
한 단계라도 실패하거나, OpenAlex 하루 무료 한도가 소진되거나, 논문 수가 2% 넘게 줄면 배포하지 않고 멈춘다.

| 옵션 | 뜻 |
|---|---|
| (없음) | 데이터만 갱신, git 조작 없음 |
| `--push` | 커밋·푸시 + 배포 확인 (`GH_TOKEN` 필요) |
| `--skip-collect` | 수집 생략, 배포 파일만 다시 생성 |
| `--from-year 2024` | 수집 시작 연도 (기본: 작년) |
| `--force` | 논문 수 감소 안전장치 무시 |

환경변수

| 이름 | 필요 여부 | 용도 |
|---|---|---|
| `GH_TOKEN` | `--push` 시 필수 | GitHub Personal Access Token (classic, `repo` 권한) |
| `OPENALEX_API_KEY` | 선택 | 있으면 OpenAlex cursor 페이징 사용 (없으면 page 방식, 쿼리당 1만 건 한도) |
| `CONTACT_EMAIL` | 선택 | OpenAlex·Crossref 요청에 `mailto`로 붙임 (polite pool). 저장소에 이메일을 적지 말 것 |

준비물: `pip install requests`

## 데이터가 오는 곳

| 대상 | 출처 | 스크립트 | 비고 |
|---|---|---|---|
| 저널 28종의 논문·초록 | OpenAlex (ISSN) | `step1_extra_openalex.py` | 하루 무료 요청 한도가 있음. 소진되면 `[중단]`을 출력하고 멈추며, 한국 시간 오전 9시 이후 다시 실행하면 이어서 진행 |
| 학회 3종 (ICRA·IROS·AIM) | Crossref (프로시딩 제목) | `step1c_crossref_conf.py` | OpenAlex는 학회 논문의 소속 정보가 비어 있어 목록 수집에는 쓸 수 없음 |
| 학회 논문 초록 | OpenAlex (DOI) | `step2c_conf_abstracts.py` | 하루 한도가 소진되면 받은 데까지 저장하고 다음 실행 때 이어받음 |
| 인용수 (전체) | Crossref (ISSN) | `step3_crossref_cites.py` | 무료·무제한. 매 업데이트마다 전량 갱신 |
| 초록 보충 | 로컬 캐시 | `step2_batch_enrich.py --no-refresh` | API 호출 없음 |
| 배포 파일 | — | `_make_papers_json.py` | `data/` 아래 4개 파일 + `papers.json`(로컬용) |

중간 산출물(`openalex_raw/`, `crossref_raw/`, `crossref_cites/`, `all_dblp.json`, `all_enriched.json`, `enrich_cache.json`)은 git에 올리지 않는다.

## 저널·학회 추가

1. `pipeline/venues_config.py`
   - 저널: `OPENALEX_VENUES`에 `key / label / issn_l / years` 추가
   - 학회: `CROSSREF_CONFS`에 `key / label / query / pattern / doi_stems / years` 추가
   - 둘 다 `VENUES_CFG`에 `label / id / color / category` 추가
2. `python update.py --from-year 2000` 으로 전체 연도 수집

사이트의 사이드바·색상·Coverage 목록·날짜·논문 수는 전부 `data/meta.json`에서 읽으므로 HTML은 고칠 필요가 없다.

## 사이트가 데이터를 읽는 방식

1. `data/meta.json`(수 KB)을 매번 새로 받는다. 여기 든 빌드 ID가 나머지 파일의 캐시 키다.
2. `core` → 검색 가능 → `doi` → `abs` 순으로 받는다. 초록이 오기 전에는 제목·저자 검색만 된다.
3. 받은 파일은 브라우저 Cache Storage에 저장한다. 빌드 ID가 같으면 재방문 때 다운로드가 없다.

첫 화면까지 받는 양이 로딩 시간을 결정하므로 `core`에 필드를 추가할 때는 크기를 확인할 것.

## 알아둘 함정

- **Crossref 관련도 검색에 cursor 페이징을 쓰면 안 된다.** 정렬이 무시되어 엉뚱한 학회가 반환된다. 학회 수집은 offset 페이징만 쓴다. (ISSN 필터만 쓰는 인용수 수집은 cursor가 안전하다.)
- **학회 이름이 비슷한 다른 학회가 섞인다.** "International Conference on Robotics and Automation"은 ICRAE·ICRAS·ICRAI와도 일치한다. 그래서 프로시딩 제목 패턴과 DOI 어간(`doi_stems`)을 둘 다 확인한다.
- **IEEE의 옛 학회 레코드(대략 2010년 이전)는 발행일이 비어 있다.** 발행일 필터만 쓰면 ICRA 2005 같은 연도가 통째로 빠진다. `step1c`는 이 구간을 등록일 기준으로 한 번 더 훑는다.
- **수집 규칙을 바꿨으면** `crossref_raw/`를 비우고 `python step1c_crossref_conf.py --prune`으로 전체 재수집해야 옛 규칙으로 들어온 레코드가 지워진다.
- **부분 수집분은 캐시하지 않는다.** 요청이 끝내 실패하면 예외로 멈춘다. 캐시 파일이 있다는 것은 그 연도가 끝까지 수집됐다는 뜻이다.
- **수집 종료 연도는 `END_YEAR`(올해 + 1)로 자동 계산된다.** 연도를 숫자로 적어 넣지 말 것.
- **로컬에서 사이트를 보려면** `serve.bat`을 실행한다. `explorer.html`을 파일로 직접 열면 브라우저가 데이터 로딩을 막는다.

## 파일 구조

```
├── index.html              ← 시작 페이지
├── explorer.html           ← 검색·분석·Excel 내보내기 (손으로 관리하는 파일)
├── data/                   ← 사이트가 읽는 데이터 (생성물)
│   ├── meta.json           ← 빌드 ID·갱신일·저널 목록
│   ├── core.json.gz        ← 제목·저자·연도·인용수 (첫 화면에 필요한 전부)
│   ├── doi.json.gz
│   └── abs.json.gz         ← 초록 (뒤에서 이어받음)
├── serve.bat               ← 로컬 서버
├── rt604_report/           ← RT604 과제 EDA 코드·데이터
└── pipeline/
    ├── update.py                 ← 원클릭 최신화
    ├── venues_config.py          ← 저널·학회 목록
    ├── step1_extra_openalex.py   ← 저널 수집
    ├── step1c_crossref_conf.py   ← 학회 수집
    ├── step3_crossref_cites.py   ← 인용수 갱신
    ├── step2c_conf_abstracts.py  ← 학회 초록 보충
    ├── step2_batch_enrich.py     ← 저널 초록 병합
    └── _make_papers_json.py      ← 배포 파일 생성 (비논문 필터 포함)
```
