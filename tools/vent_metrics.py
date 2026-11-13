"""
공용 분석 로직 — CSV에서 '고습 시간'을 계산한다.

analyze.py(단일 CSV)와 compare.py(기준선 vs 설치후)가 공유한다.
고습 시간 정의(experiment.md 성공 기준): state가 VENT로 바뀐 행부터 humidity가 70
미만이 되는 행까지 걸린 시간 = (행 수) × 2초. 샤워 사이클마다 구해 평균을 낸다.
"""

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "python"))

from vent_logic import SAMPLE_SECONDS, VENT

HIGH_HUM = 70.0   # 이 값 이상이면 '고습'으로 본다


def load_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def find_cycles(rows):
    """VENT 진입 ~ 습도<70 구간을 찾아 각 사이클의 고습 시간(초)을 반환.

    반환: [{"start": 시작시각, "drop": 70미만시각 or None, "seconds": 초 or None}, ...]
    """
    cycles = []
    i = 0
    n = len(rows)
    prev_state = None
    while i < n:
        state = rows[i]["state"]
        # VENT로 '바뀐' 행 탐지
        if state == VENT and prev_state != VENT:
            j = i
            while j < n and float(rows[j]["humidity"]) >= HIGH_HUM:
                j += 1
            if j < n:
                cycles.append({
                    "start": rows[i]["time"],
                    "drop": rows[j]["time"],
                    "seconds": (j - i) * SAMPLE_SECONDS,
                })
                prev_state = rows[j]["state"]
                i = j + 1
                continue
            else:
                cycles.append({
                    "start": rows[i]["time"],
                    "drop": None,          # 데이터 내에서 70 미만으로 안 떨어짐
                    "seconds": None,
                })
        prev_state = state
        i += 1
    return cycles


def average_high_humidity(rows):
    """완결된 사이클들의 평균 고습 시간(초)과 사이클 목록을 반환.

    반환: (평균초 or None, cycles)
    """
    cycles = find_cycles(rows)
    done = [c for c in cycles if c["seconds"] is not None]
    avg = sum(c["seconds"] for c in done) / len(done) if done else None
    return avg, cycles
