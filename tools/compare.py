"""
성공 기준 계산 — 기준선 기간 vs 설치후 기간의 평균 '고습 시간'을 비교해
감소율(%)을 구하고, 목표(기본 30%) 달성 여부를 판정한다.

experiment.md 성공 기준: "고습 시간 평균을 기준선보다 30% 줄인다."

실행:
  python3 tools/compare.py 기준선.csv 설치후.csv [--target 30]
기본값(인자 없을 때):
  data/sample_baseline.csv 와 data/sample_after.csv 를 비교
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from vent_metrics import load_rows, average_high_humidity

TARGET_REDUCTION = 30.0   # 목표 감소율(%) — experiment.md


def summarize(label, path):
    rows = load_rows(path)
    avg, cycles = average_high_humidity(rows)
    done = [c for c in cycles if c["seconds"] is not None]
    print(f"[{label}] {os.path.normpath(path)}")
    if avg is None:
        print("  완결된 사이클 없음")
    else:
        print(f"  사이클 {len(done)}개, 평균 고습 시간 {avg:.0f}초 ({avg / 60:.1f}분)")
        for k, c in enumerate(done, 1):
            print(f"    #{k}: {c['seconds']}초")
    return avg


def main():
    here = os.path.dirname(__file__)
    parser = argparse.ArgumentParser(description="기준선 vs 설치후 고습 시간 비교")
    parser.add_argument("baseline", nargs="?",
                        default=os.path.join(here, "..", "data", "sample_baseline.csv"),
                        help="기준선(알림 끔) CSV")
    parser.add_argument("after", nargs="?",
                        default=os.path.join(here, "..", "data", "sample_after.csv"),
                        help="설치후(알림 켬) CSV")
    parser.add_argument("--target", type=float, default=TARGET_REDUCTION,
                        help="목표 감소율(%%), 기본 30")
    args = parser.parse_args()

    for p in (args.baseline, args.after):
        if not os.path.exists(p):
            print(f"CSV를 찾을 수 없음: {p}")
            print("먼저 샘플을 만드세요: "
                  "python3 tools/simulate.py --scenario baseline / --scenario after")
            return 1

    print("=" * 56)
    base_avg = summarize("기준선", args.baseline)
    print()
    after_avg = summarize("설치후", args.after)
    print("=" * 56)

    if not base_avg or not after_avg:
        print("비교 불가: 한쪽에 완결된 환기 사이클이 없습니다.")
        return 1

    reduction = (base_avg - after_avg) / base_avg * 100
    print(f"평균 고습 시간: 기준선 {base_avg:.0f}초 → 설치후 {after_avg:.0f}초")
    print(f"감소율: {reduction:.1f}%  (목표 {args.target:.0f}%)")

    if reduction >= args.target:
        print(f"판정: ✅ 성공 — 목표 {args.target:.0f}% 이상 감소")
        return 0
    else:
        print(f"판정: ❌ 미달 — 목표 {args.target:.0f}%에 {args.target - reduction:.1f}%p 부족")
        return 0   # 미달도 정상 종료(판정 결과일 뿐)


if __name__ == "__main__":
    sys.exit(main())
