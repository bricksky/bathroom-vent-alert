"""
데모 시뮬레이터 — 하드웨어 없이 '샤워 → 환기 → 완료' 사이클을 흉내 낸 센서
데이터를 만들어 CSV로 기록한다. 발표 시연·로직 확인·성공 기준 비교용.

시나리오:
  demo     : 1사이클 (기본). 출력 data/sample_vent_log.csv
  baseline : 알림 끔 + 환기 비효율(습도 천천히 빠짐) → 고습 시간 김. data/sample_baseline.csv
  after    : 알림 켬 + 환기 효율적(습도 빨리 빠짐) → 고습 시간 짧음. data/sample_after.csv

실행:
  python3 tools/simulate.py                         # demo 1사이클
  python3 tools/simulate.py --scenario baseline      # 기준선용 3사이클
  python3 tools/simulate.py --scenario after         # 설치후용 3사이클
  python3 tools/simulate.py out.csv --scenario after --cycles 5
"""

import argparse
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "python"))

from vent_logic import VentStateMachine, ensure_csv, append_row, SAMPLE_SECONDS

# 시나리오별 설정: (사이클 수, 환기 감쇠 스텝, 알림 끔 여부, 기본 출력파일)
#   vent_steps 가 클수록 습도가 천천히 빠져 '고습 시간'이 길어진다.
SCENARIOS = {
    "demo":     dict(cycles=1, vent_steps=20, baseline_mode=False, out="sample_vent_log.csv"),
    "baseline": dict(cycles=3, vent_steps=30, baseline_mode=True,  out="sample_baseline.csv"),
    "after":    dict(cycles=3, vent_steps=14, baseline_mode=False, out="sample_after.csv"),
}


def build_profile(cycles, vent_steps):
    """(humidity, temp, light) 샘플 시퀀스를 만든다. 2초 간격 가정."""
    samples = []
    for _ in range(cycles):
        # 1) 평소(대기): 습도 50, 불 꺼짐
        for _ in range(3):
            samples.append((50.0, 23.0, 120))
        # 2) 샤워 시작: 불 켜지고 습도 50→88 급상승
        for i in range(10):
            h = 50.0 + (88.0 - 50.0) * (i + 1) / 10
            samples.append((round(h, 1), 24.0 + i * 0.2, 820))
        # 3) 샤워 지속: 높은 습도 유지, 불 켜짐
        for _ in range(5):
            samples.append((88.0, 26.0, 820))
        # 4) 환기: 불 꺼지고 습도 88→50 하강 (vent_steps 가 클수록 천천히)
        for i in range(vent_steps):
            h = 88.0 - (88.0 - 50.0) * (i + 1) / vent_steps
            samples.append((round(h, 1), 26.0 - i * 0.05, 110))
        # 5) 환기 후 안정
        for _ in range(3):
            samples.append((50.0, 24.0, 110))
    return samples


def main():
    here = os.path.dirname(__file__)
    parser = argparse.ArgumentParser(description="환기 알림 센서 데이터 시뮬레이터")
    parser.add_argument("output", nargs="?", default=None, help="출력 CSV 경로")
    parser.add_argument("--scenario", choices=list(SCENARIOS), default="demo")
    parser.add_argument("--cycles", type=int, default=None, help="사이클 수 (기본: 시나리오값)")
    args = parser.parse_args()

    cfg = SCENARIOS[args.scenario]
    cycles = args.cycles if args.cycles is not None else cfg["cycles"]
    out_path = args.output or os.path.join(here, "..", "data", cfg["out"])

    if os.path.exists(out_path):   # 재현성 위해 새로 생성
        os.remove(out_path)
    ensure_csv(out_path)

    sm = VentStateMachine(baseline_mode=cfg["baseline_mode"])
    t = datetime(2026, 11, 13, 20, 0, 0)   # 재현 가능한 고정 시작 시각

    rang = 0
    for humidity, temp, light in build_profile(cycles, cfg["vent_steps"]):
        state, buzzed, _cmd = sm.update(humidity, temp, light)
        append_row(out_path, t.isoformat(timespec="seconds"),
                   humidity, temp, light, state, buzzed)
        rang += buzzed
        t += timedelta(seconds=SAMPLE_SECONDS)

    print(f"[{args.scenario}] 샘플 CSV 생성: {os.path.normpath(out_path)} "
          f"({cycles}사이클, 환기 비효율도 vent_steps={cfg['vent_steps']})")
    print(f"  부저 알림 발생 횟수: {rang} "
          f"{'(기준선 모드 — 알림 꺼짐)' if cfg['baseline_mode'] else ''}")


if __name__ == "__main__":
    main()
