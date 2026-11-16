"""
공용 분석 로직 — CSV에서 '고습 시간'을 계산한다.

analyze.py(단일 CSV)와 compare.py(기준선 vs 설치후)가 공유한다.

고습 시간 정의: state가 VENT로 바뀐 행부터 DONE(환기 완료)이 되는 행까지 걸린 시간
= (행 수) × 2초. 샤워 사이클마다 구해 평균을 낸다.

※ 환기 완료(DONE)는 상태머신이 '습도 ≤ 기준선+5%p(COMPLETION_HUM)'로 판정한다.
   따라서 고습 시간 계산과 완료 판정이 '같은 기준'을 쓴다 (교수 피드백 반영).
"""

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "python"))

from vent_logic import SAMPLE_SECONDS, VENT, DONE, COMPLETION_HUM  # noqa: F401 (COMPLETION_HUM 재노출)


def load_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def find_cycles(rows):
    """VENT 진입 ~ DONE(환기 완료) 구간을 찾아 각 사이클의 고습 시간(초)을 반환.

    반환: [{"start": VENT시작시각, "done": 완료시각 or None, "seconds": 초 or None}, ...]
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
            while j < n and rows[j]["state"] != DONE:
                j += 1
            if j < n:
                cycles.append({
                    "start": rows[i]["time"],
                    "done": rows[j]["time"],
                    "seconds": (j - i) * SAMPLE_SECONDS,
                })
                prev_state = rows[j]["state"]
                i = j + 1
                continue
            else:
                cycles.append({
                    "start": rows[i]["time"],
                    "done": None,          # 데이터 내에서 완료되지 않음
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
