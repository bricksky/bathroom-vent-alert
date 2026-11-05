"""
상태머신 로직 테스트 — 하드웨어 없이 vent_logic.VentStateMachine을 검증한다.

실행: python3 tests/test_vent_logic.py   (pytest 없이도 동작)
      pytest tests/                        (pytest 있으면 그대로 인식)
"""

import os
import sys

# app/python 을 import 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "python"))

from vent_logic import VentStateMachine, IDLE, SHOWER, VENT, DONE


def run_sequence(sm, samples):
    """(humidity, light) 목록을 순서대로 넣고 (state, buzzed) 기록을 반환."""
    out = []
    for humidity, light in samples:
        state, buzzed, _cmd = sm.update(humidity, 25.0, light)
        out.append((state, buzzed))
    return out


def test_full_cycle_rings_once():
    """평소 → 샤워(습도↑) → 환기(불 꺼짐, 습도↓) → 완료(부저 1회)."""
    sm = VentStateMachine()  # 기준선 55, 샤워 +15(=70), 환기복귀 +5(=60), 조도 500
    seq = [
        (50, 100),   # IDLE: 불 꺼짐·습도 낮음
        (75, 800),   # 불 켜짐 + 습도>70 → SHOWER
        (85, 800),   # 샤워 지속 → SHOWER
        (82, 100),   # 불 꺼짐(환기 시작) → VENT
        (68, 100),   # 환기 중(>60) → VENT
        (60, 100),   # 습도<=60 → DONE (부저 울림)
        (57, 100),   # DONE → IDLE (부저 끔)
    ]
    states = [s for s, _ in run_sequence(sm, seq)]
    buzzes = [b for _, b in run_sequence(VentStateMachine(), seq)]

    assert states == [IDLE, SHOWER, SHOWER, VENT, VENT, DONE, IDLE], states
    assert sum(buzzes) == 1, f"부저는 정확히 1회 울려야 함, 실제 {sum(buzzes)}회"
    assert buzzes[5] == 1, "부저는 DONE 진입 샘플에서 울려야 함"


def test_baseline_mode_no_buzzer():
    """기준선 모드: 같은 사이클이라도 부저가 울리지 않아야 한다."""
    sm = VentStateMachine(baseline_mode=True)
    seq = [(50, 100), (75, 800), (85, 800), (82, 100), (60, 100)]
    result = run_sequence(sm, seq)
    states = [s for s, _ in result]
    buzzes = [b for _, b in result]
    assert states[-1] == DONE, states
    assert sum(buzzes) == 0, "기준선 모드에선 부저가 울리면 안 됨"


def test_no_false_trigger_when_light_off():
    """불이 꺼진 채 습도만 흔들리면 샤워로 오판하지 않아야 한다."""
    sm = VentStateMachine()
    seq = [(50, 100), (72, 100), (90, 100), (60, 100)]  # 불 꺼짐 → 전부 IDLE
    states = [s for s, _ in run_sequence(sm, seq)]
    assert all(s == IDLE for s in states), states


def test_buzzer_off_follows_on():
    """부저를 켠 다음 샘플에서 반드시 끄기 명령이 나가야 한다."""
    sm = VentStateMachine()
    for humidity, light in [(50, 100), (75, 800), (82, 100), (60, 100)]:
        _s, _b, cmd = sm.update(humidity, 25.0, light)
    assert cmd is True, "DONE 진입 시 부저 켜기(True)"
    _s, _b, cmd = sm.update(57, 25.0, 100)
    assert cmd is False, "다음 샘플에서 부저 끄기(False)"


def _main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {t.__name__}: {e!r}")
    print(f"\n{passed}/{len(tests)} 통과")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(_main())
