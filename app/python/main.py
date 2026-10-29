"""
샤워 후 화장실 환기 알림 — 리눅스(파이썬) 측 (Arduino UNO Q)

STM32 스케치가 2초마다 Bridge.notify("sensor", humidity, temp, light)로 보내는 값을
받아 상태를 판단하고 CSV로 기록한다. 환기 완료(DONE) 시 스케치의 set_buzzer를
notify로 호출해 부저를 울린다.

상태 머신: IDLE(대기) → SHOWER(샤워) → VENT(환기) → DONE(완료) → IDLE
CSV 헤더:  time,humidity,temp,light,state,buzzer

기준선 모드(환경변수 VENT_BASELINE=1): 부저를 울리지 않고 기록만 한다 (11주차 기준선 측정용).
"""

from arduino.app_utils import *
import csv
import os
from datetime import datetime

# ── 판단 기준값 (experiment.md 참고. 모두 '가짜 값' — 9주차 모의실험/11주차 실측으로 확정) ──
HUM_BASELINE = 55.0   # 평소 습도 기준선 (%RH)
SHOWER_RISE  = 15.0   # 기준선 + 이 값 초과 → 샤워 중으로 판단
VENT_RETURN  = 5.0    # 기준선 + 이 값 이내로 복귀 → 환기 완료로 판단
LIGHT_ON     = 500    # 조도 이 값 초과 → 화장실 불 켜짐

# ── 설정 (환경변수로 조정) ──
BASELINE_MODE = os.environ.get("VENT_BASELINE", "0") == "1"   # 1이면 부저 끔(기준선 측정)
LOG_PATH      = os.environ.get("VENT_LOG", "vent_log.csv")    # CSV 저장 경로

# ── 상태 ──
IDLE, SHOWER, VENT, DONE = "IDLE", "SHOWER", "VENT", "DONE"
state = IDLE
buzzer_off_pending = False   # 직전 사이클에 부저를 켰으면 이번에 끈다 (약 2초 비프)


def ensure_csv_header():
    if not os.path.exists(LOG_PATH) or os.path.getsize(LOG_PATH) == 0:
        with open(LOG_PATH, "w", newline="") as f:
            csv.writer(f).writerow(["time", "humidity", "temp", "light", "state", "buzzer"])


def log_row(humidity, temp, light, cur_state, buzzer):
    with open(LOG_PATH, "a", newline="") as f:
        csv.writer(f).writerow([
            datetime.now().isoformat(timespec="seconds"),
            f"{humidity:.1f}", f"{temp:.1f}", light, cur_state, buzzer,
        ])


def set_buzzer(on):
    """스케치(STM32)의 set_buzzer를 notify로 호출 (fire-and-forget, 스레드 안전)."""
    Bridge.notify("set_buzzer", 1 if on else 0)


def on_sensor(humidity: float, temp: float, light: int):
    global state, buzzer_off_pending
    buzzed = 0

    # 직전 사이클에 울린 부저 끄기
    if buzzer_off_pending:
        set_buzzer(False)
        buzzer_off_pending = False

    light_on = light > LIGHT_ON

    if state == IDLE:
        # 불 켜짐 + 습도 급상승 → 샤워 시작
        if light_on and humidity > HUM_BASELINE + SHOWER_RISE:
            state = SHOWER

    elif state == SHOWER:
        # 불 꺼짐(샤워 끝, 사용자가 환기 시작) → 환기 감시 모드
        if not light_on:
            state = VENT

    elif state == VENT:
        # 습도가 기준선 근처로 복귀 → 환기 완료 → 알림
        if humidity <= HUM_BASELINE + VENT_RETURN:
            state = DONE
            if not BASELINE_MODE:
                set_buzzer(True)
                buzzer_off_pending = True
                buzzed = 1

    elif state == DONE:
        # 알림 한 번 울렸으면 대기로 복귀 (재알림 방지)
        state = IDLE

    log_row(humidity, temp, light, state, buzzed)
    print(f"[{state}] hum={humidity:.1f}% temp={temp:.1f}C light={light} buzzer={buzzed}")


ensure_csv_header()
print(f"vent-alert 시작 | baseline_mode={BASELINE_MODE} | log={LOG_PATH}")
Bridge.provide("sensor", on_sensor)
App.run()
