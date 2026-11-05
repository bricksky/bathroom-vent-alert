"""
데모 시뮬레이터 — 하드웨어 없이 한 번의 '샤워 → 환기 → 완료' 사이클을 흉내 낸
센서 데이터를 만들어 CSV로 기록한다. 발표 시연·로직 확인용.

실행: python3 tools/simulate.py [출력CSV경로]
기본 출력: data/sample_vent_log.csv
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "python"))

from vent_logic import VentStateMachine, ensure_csv, append_row, SAMPLE_SECONDS


def build_profile():
    """(humidity, temp, light) 샘플 시퀀스를 만든다. 2초 간격 가정."""
    samples = []

    # 1) 평소(대기): 습도 50, 불 꺼짐
    for _ in range(5):
        samples.append((50.0, 23.0, 120))

    # 2) 샤워 시작: 불 켜지고 습도 50→88 급상승
    for i in range(10):
        h = 50.0 + (88.0 - 50.0) * (i + 1) / 10
        samples.append((round(h, 1), 24.0 + i * 0.2, 820))

    # 3) 샤워 지속: 높은 습도 유지, 불 켜짐
    for _ in range(5):
        samples.append((88.0, 26.0, 820))

    # 4) 환기 시작: 불 꺼지고 습도 88→54 완만히 하강
    for i in range(20):
        h = 88.0 - (88.0 - 54.0) * (i + 1) / 20
        samples.append((round(h, 1), 26.0 - i * 0.1, 110))

    # 5) 환기 후 안정: 습도 낮게 유지
    for _ in range(3):
        samples.append((54.0, 24.0, 110))

    return samples


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "data", "sample_vent_log.csv"
    )

    # 기존 샘플 파일은 새로 생성 (재현성)
    if os.path.exists(out_path):
        os.remove(out_path)
    ensure_csv(out_path)

    sm = VentStateMachine()
    # 재현 가능한 고정 시작 시각 (2초 간격)
    t = datetime(2026, 11, 5, 20, 0, 0)

    rang_at = None
    for i, (humidity, temp, light) in enumerate(build_profile()):
        state, buzzed, _cmd = sm.update(humidity, temp, light)
        append_row(out_path, t.isoformat(timespec="seconds"),
                   humidity, temp, light, state, buzzed)
        if buzzed:
            rang_at = t
        t += timedelta(seconds=SAMPLE_SECONDS)

    print(f"샘플 CSV 생성: {os.path.normpath(out_path)}")
    if rang_at:
        print(f"환기 완료 알림(부저) 발생 시각: {rang_at.isoformat(timespec='seconds')}")
    else:
        print("경고: 이번 프로파일에서 알림이 발생하지 않았습니다.")


if __name__ == "__main__":
    main()
