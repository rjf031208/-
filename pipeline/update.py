"""
원클릭 최신화
==============
수집 → 학회 → 인용수 → 학회 초록 → 배포파일 생성 → (선택) 커밋·푸시·배포 확인
을 한 번에 실행한다.

Usage:
    python update.py                    # 데이터 갱신까지 (git 조작 없음)
    python update.py --push             # + 커밋/푸시 + GitHub Pages 배포 확인
    python update.py --skip-collect     # 수집 생략 (배포파일만 다시 생성)
    python update.py --from-year 2024   # 수집 시작연도 지정 (기본: 작년)

환경변수:
    GH_TOKEN          --push 시 필요 (repo 권한 Personal Access Token)
    OPENALEX_API_KEY  선택. 있으면 OpenAlex cursor 페이징 사용
    CONTACT_EMAIL     선택. 있으면 OpenAlex/Crossref 요청에 mailto로 붙여 polite pool 사용

안전장치:
    - 각 단계 실패 시 즉시 중단 (부분 데이터로 배포하지 않음)
    - 저널 수집 중 OpenAlex 예산 소진 감지 시 배포 중단
      (학회 초록 보충은 예산이 떨어지면 받은 데까지만 반영하고 계속 진행)
    - 새 논문 수가 이전보다 2% 넘게 줄면 데이터 손실로 보고 중단 (--force로 무시)
    - 토큰은 출력하지 않고, 원격 URL은 항상 원래대로 복구
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PIPE = Path(__file__).resolve().parent
ROOT = PIPE.parent
META_JSON = ROOT / "data" / "meta.json"     # 날짜·논문 수·저널 목록 — 사이트가 직접 읽는다

GH_OWNER, GH_REPO = "rjf031208", "-"
PAGES_URL = f"https://{GH_OWNER}.github.io/{GH_REPO}/"
REMOTE_CLEAN = f"https://github.com/{GH_OWNER}/{GH_REPO}.git"


def banner(msg):
    print(f"\n{'=' * 60}\n▶ {msg}\n{'=' * 60}", flush=True)


def run_step(label, args, fail_markers=()):
    """하위 스크립트를 실시간 출력(-u, 버퍼링 없음)으로 실행. 실패/중단 표식이 있으면 종료."""
    banner(label)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.Popen([sys.executable, "-u", *args], cwd=PIPE, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    lines = []
    for line in proc.stdout:
        print(line, end="", flush=True)
        lines.append(line)
    proc.wait()
    out = "".join(lines)
    if proc.returncode != 0:
        raise SystemExit(f"\n✗ [{label}] 실패 (exit {proc.returncode}) — 배포하지 않고 중단합니다.")
    for m in fail_markers:
        if m in out:
            raise SystemExit(f"\n✗ [{label}] '{m}' 감지 — 데이터가 불완전하므로 배포하지 않고 중단합니다.")
    return out


def clear_caches(from_year):
    banner(f"캐시 정리 ({from_year}년 이후 + 인용수)")
    this_year = datetime.date.today().year
    n = 0
    for d in ("openalex_raw", "crossref_raw"):
        for y in range(from_year, this_year + 1):
            for f in (PIPE / d).glob(f"*_{y}.json"):
                f.unlink()
                n += 1
    for f in (PIPE / "crossref_cites").glob("*.json"):
        f.unlink()
        n += 1
    print(f"  {n}개 캐시 파일 삭제")


def read_meta():
    return json.loads(META_JSON.read_text(encoding="utf-8")) if META_JSON.exists() else None


def git(*args, check=True):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        # 토큰이 섞일 수 있는 원격 URL은 출력에서 가린다
        err = re.sub(r"https://[^@\s]+@", "https://***@", r.stderr.strip())
        raise SystemExit(f"✗ git {args[0]} 실패:\n{err}")
    return r


def gh_api(path, token, method="GET"):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}{path}", method=method,
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
        return json.loads(body) if body else {}


def push_and_deploy(n_papers, today, build, trailer):
    token = os.environ.get("GH_TOKEN", "").strip()
    if not token:
        raise SystemExit("✗ --push 에는 GH_TOKEN 환경변수가 필요합니다.")

    banner("커밋 & 푸시")
    git("add", "data", "explorer.html", "index.html")
    if git("diff", "--cached", "--quiet", check=False).returncode == 0:
        print("  변경 사항 없음 — 커밋/배포 생략")
        return
    msg = f"Refresh to {n_papers:,} papers ({today})"
    if trailer:
        msg += f"\n\n{trailer}"
    git("commit", "-m", msg)
    try:
        git("remote", "set-url", "origin",
            f"https://{GH_OWNER}:{token}@github.com/{GH_OWNER}/{GH_REPO}.git")
        git("push")
    finally:
        git("remote", "set-url", "origin", REMOTE_CLEAN, check=False)
    print("  ✓ push 완료")

    banner("GitHub Pages 배포 확인")
    time.sleep(15)
    for attempt in range(1, 4):
        while True:
            run = gh_api("/actions/runs?per_page=1", token)["workflow_runs"][0]
            if run["status"] == "completed":
                break
            time.sleep(20)
        print(f"  시도 {attempt}: {run['conclusion']}")
        if run["conclusion"] == "success":
            break
        print("  → 재빌드 요청")
        gh_api("/pages/builds", token, method="POST")
        time.sleep(25)
    else:
        raise SystemExit("✗ 배포 3회 실패 — GitHub Actions 탭을 확인하세요.")

    live = json.loads(urllib.request.urlopen(
        f"{PAGES_URL}data/meta.json?nocache={int(time.time())}", timeout=60).read())
    ok = live.get("build") == build
    print(f"  라이브 확인: {'✓ 반영됨' if ok else '… 아직 CDN 캐시 (수 분 내 반영)'}")


def main():
    ap = argparse.ArgumentParser(description="논문 데이터 원클릭 최신화")
    ap.add_argument("--from-year", type=int, default=datetime.date.today().year - 1)
    ap.add_argument("--skip-collect", action="store_true", help="수집 생략, 생성·헤더만")
    ap.add_argument("--push", action="store_true", help="커밋/푸시 + 배포 확인 (GH_TOKEN 필요)")
    ap.add_argument("--force", action="store_true", help="논문 수 감소 안전장치 무시")
    ap.add_argument("--commit-trailer", default="", help="커밋 메시지 끝에 붙일 문구")
    args = ap.parse_args()

    today = datetime.date.today().isoformat()
    prev = (read_meta() or {}).get("papers")
    t0 = time.time()

    if not args.skip_collect:
        clear_caches(args.from_year)
        run_step("1/6 저널 신규 논문 (OpenAlex)",
                 ["step1_extra_openalex.py", "--from-year", str(args.from_year)], ("[중단]",))
        run_step("2/6 학회 신규 논문 (Crossref)",
                 ["step1c_crossref_conf.py", "--from-year", str(args.from_year)])
        run_step("3/6 인용수 전량 갱신 (Crossref)", ["step3_crossref_cites.py"])
        # 예산이 떨어지면 받은 데까지만 저장하고 정상 종료한다 — 다음 실행 때 이어받음
        run_step("4/6 학회 초록 보충 (OpenAlex)", ["step2c_conf_abstracts.py"])
    run_step("5/6 초록 병합", ["step2_batch_enrich.py", "--no-refresh"], ("[중단]",))
    run_step("6/6 배포 파일 생성", ["_make_papers_json.py"])

    meta = read_meta()
    n_papers, n_venues = meta["papers"], len(meta["venues"])
    if prev and n_papers < prev * 0.98 and not args.force:
        raise SystemExit(f"✗ 논문 수 급감 ({prev:,} → {n_papers:,}) — 데이터 손실 의심, 중단. "
                         f"의도한 변경이면 --force")

    if args.push:
        push_and_deploy(n_papers, today, meta["build"], args.commit_trailer)

    diff = f"{n_papers - prev:+,}" if prev else "-"
    banner(f"완료 ({(time.time() - t0) / 60:.1f}분)")
    print(f"  논문 {prev or 0:,} → {n_papers:,} ({diff})  ·  {n_venues} venues  ·  {today}")
    if not args.push:
        print("  ※ 커밋/푸시는 하지 않았습니다. 배포: GH_TOKEN=... python update.py --skip-collect --push")


if __name__ == "__main__":
    main()
