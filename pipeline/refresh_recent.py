"""
최근 데이터 빠른 업데이트
--------------------------
전체 재수집 대신 최근 N년 데이터만 다시 받아서 병합합니다.
주기적 업데이트(월 1회 등)에 사용합니다.

Usage:
    python refresh_recent.py           # 최근 2년
    python refresh_recent.py --years 3  # 최근 3년
"""

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

THIS_DIR = Path(__file__).parent
CURRENT_YEAR = date.today().year


def run(cmd: list[str]):
    print(f"\n$ {' '.join(cmd)}")
    subprocess.run([sys.executable, *cmd], cwd=THIS_DIR, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=2, help="최근 몇 년치 업데이트 (기본 2)")
    args = parser.parse_args()

    from_year = CURRENT_YEAR - args.years + 1
    print(f"=== {from_year}–{CURRENT_YEAR} 데이터 업데이트 ===")

    run(["step1_dblp.py", "--from-year", str(from_year)])
    run(["step1_extra_openalex.py", "--from-year", str(from_year)])
    run(["step2_openalex.py"])
    run(["step3_excel.py"])
    run(["_make_all_html.py"])
    run(["_make_by_year_html.py"])

    print("\n✓ 업데이트 완료")


if __name__ == "__main__":
    main()
