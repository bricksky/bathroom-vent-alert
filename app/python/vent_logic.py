"""
샤워 후 화장실 환기 알림 — 순수 판단 로직 (하드웨어/Bridge 의존 없음)

main.py(실물), 테스트, 시뮬레이터가 공유한다. 여기에는 아두이노/Bridge 관련
import이 없어서, 보드 없이도 import하고 돌려볼 수 있다.
"""

import csv
import os

# ── 판단 기준값 (experiment.md 참고. 모두 '가짜 값' — 실측으로 확정) ──
HUM_BASELINE = 55.0   # 평소 습도 기준선 (%RH)
SHOWER_RISE  = 15.0   # 기준선 + 이 값 초과 → 샤워 중으로 판단
VENT_RETURN  = 5.0    # 기준선 + 이 값 이내로 복귀 → 환기 완료로 판단
LIGHT_ON     = 500    # 조도 이 값 초과 → 화장실 불 켜짐

SAMPLE_SECONDS = 2    # 샘플링 주기(초)

# ── 상태 ──
IDLE, SHOWER, VENT, DONE = "IDLE", "SHOWER", "VENT", "DONE"

CSV_HEADER = ["time", "humidity", "temp", "light", "state", "buzzer"]


class VentStateMachine:
    """센서 샘플을 받아 상태(IDLE→SHOWER→VENT→DONE→IDLE)를 판단한다."""

    def __init__(self, hum_baseline=HUM_BASELINE, shower_rise=SHOWER_RISE,
                 vent_return=VENT_RETURN, light_on=LIGHT_ON, baseline_mode=False):
        self.hum_baseline = hum_baseline
        self.shower_rise = shower_rise
        self.vent_return = vent_return
        self.light_on = light_on
        self.baseline_mode = baseline_mode   # True면 부저를 울리지 않음(기준선 측정)
        self.state = IDLE
        self._buzzer_off_pending = False

    def update(self, humidity, temp, light):
        """센서 한 샘플 처리.

        반환: (state, buzzed, buzzer_cmd)
          - state:      처리 후 현재 상태
          - buzzed:     이번 샘플에 알림이 울렸으면 1, 아니면 0 (CSV 기록용)
          - buzzer_cmd: 하드웨어에 보낼 부저 명령. True=켜기, False=끄기, None=변화 없음
        """
        buzzed = 0
        buzzer_cmd = None

        # 직전 사이클에 켠 부저 끄기 (약 2초 비프)
        if self._buzzer_off_pending:
            buzzer_cmd = False
            self._buzzer_off_pending = False

        light_is_on = light > self.light_on

        if self.state == IDLE:
            # 불 켜짐 + 습도 급상승 → 샤워 시작
            if light_is_on and humidity > self.hum_baseline + self.shower_rise:
                self.state = SHOWER

        elif self.state == SHOWER:
            # 불 꺼짐(샤워 끝, 사용자가 환기 시작) → 환기 감시 모드
            if not light_is_on:
                self.state = VENT

        elif self.state == VENT:
            # 습도가 기준선 근처로 복귀 → 환기 완료 → 알림
            if humidity <= self.hum_baseline + self.vent_return:
                self.state = DONE
                if not self.baseline_mode:
                    buzzer_cmd = True
                    self._buzzer_off_pending = True
                    buzzed = 1

        elif self.state == DONE:
            # 알림 한 번 울렸으면 대기로 복귀 (재알림 방지)
            self.state = IDLE

        return self.state, buzzed, buzzer_cmd


# ── CSV 헬퍼 (실물·시뮬레이터 공용) ──

def ensure_csv(path):
    """헤더가 없으면 생성."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", newline="") as f:
            csv.writer(f).writerow(CSV_HEADER)


def append_row(path, time_str, humidity, temp, light, state, buzzer):
    """측정 한 줄 기록."""
    with open(path, "a", newline="") as f:
        csv.writer(f).writerow(
            [time_str, f"{humidity:.1f}", f"{temp:.1f}", light, state, buzzer]
        )
