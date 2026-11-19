"""
샤워 후 화장실 환기 알림 — 리눅스(파이썬) 측 (Arduino UNO Q)

STM32 스케치가 2초마다 Bridge.notify("sensor", humidity, temp, light)로 보내는 값을
받아 상태를 판단(vent_logic)하고 CSV로 기록한다. 환기 완료 시 스케치의 set_buzzer를
notify로 호출해 부저를 울린다.

판단 로직은 vent_logic.VentStateMachine에 분리되어 있다 (하드웨어 없이 테스트 가능).
기준선 모드(환경변수 VENT_BASELINE=1): 부저를 울리지 않고 기록만 한다.
"""

from arduino.app_utils import *
import os
from datetime import datetime

from vent_logic import VentStateMachine, ensure_csv, append_row

BASELINE_MODE = os.environ.get("VENT_BASELINE", "0") == "1"
LOG_PATH      = os.environ.get("VENT_LOG", "vent_log.csv")
SELFTEST      = os.environ.get("VENT_SELFTEST", "0") == "1"  # 1이면 시작 시 부저 1회 울려 배선 확인

sm = VentStateMachine(baseline_mode=BASELINE_MODE)
_selftest_state = 0   # 0=미실행, 1=부저ON, 2=완료
_err_count = 0


def set_buzzer(on):
    """스케치(STM32)의 set_buzzer를 notify로 호출 (fire-and-forget, 스레드 안전)."""
    Bridge.notify("set_buzzer", 1 if on else 0)


def on_sensor(humidity: float, temp: float, light: int):
    global _selftest_state
    # 브링업용: 켜고 첫 샘플에 부저 ON, 다음 샘플에 OFF (약 2초 '삑')
    if SELFTEST and _selftest_state < 2:
        if _selftest_state == 0:
            set_buzzer(True); _selftest_state = 1
            print("[SELFTEST] 부저 ON — 소리 나는지 확인 (2초)")
        else:
            set_buzzer(False); _selftest_state = 2
            print("[SELFTEST] 부저 OFF — 셀프테스트 완료")

    state, buzzed, buzzer_cmd = sm.update(humidity, temp, light)
    if buzzer_cmd is not None:
        set_buzzer(buzzer_cmd)
    append_row(LOG_PATH, datetime.now().isoformat(timespec="seconds"),
               humidity, temp, light, state, buzzed)
    print(f"[{state}] hum={humidity:.1f}% temp={temp:.1f}C light={light} buzzer={buzzed}")


def on_sensor_error(light: int):
    """스케치가 DHT11 읽기에 실패했을 때 — 배선/풀업 문제 진단용."""
    global _err_count
    _err_count += 1
    print(f"[DHT ERROR #{_err_count}] DHT11 읽기 실패 (D6 배선·전원·풀업 확인). "
          f"조도(A2)={light} → 보드/조도는 동작 중")


ensure_csv(LOG_PATH)
print(f"vent-alert 시작 | baseline_mode={BASELINE_MODE} | selftest={SELFTEST} | log={LOG_PATH}")
Bridge.provide("sensor", on_sensor)
Bridge.provide("sensor_error", on_sensor_error)
App.run()
