"""
고습 시간 계산·비교 로직 테스트 — 하드웨어 없이 vent_metrics를 검증한다.

실행: python3 tests/test_vent_metrics.py   (pytest 없이도 동작)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from vent_metrics import find_cycles, average_high_humidity
from vent_logic import IDLE, SHOWER, VENT, DONE, SAMPLE_SECONDS


def make_rows(samples):
    """(humidity, state) 목록을 CSV DictReader와 같은 형태의 행으로 바꾼다."""
    rows = []
    for i, (hum, state) in enumerate(samples):
        rows.append({
            "time": f"t{i}", "humidity": str(hum), "temp": "25.0",
            "light": "100", "state": state, "buzzer": "0",
        })
    return rows


def test_single_cycle_seconds():
    """VENT 시작(습도 85)부터 70 미만(65)까지 2칸 → 2*2=4초."""
    rows = make_rows([
        (50, IDLE), (80, SHOWER), (85, VENT), (75, VENT), (65, VENT),
    ])
    cycles = find_cycles(rows)
    assert len(cycles) == 1, cycles
    # VENT 시작 index2(85) → index4(65<70), (4-2)*SAMPLE_SECONDS
    assert cycles[0]["seconds"] == 2 * SAMPLE_SECONDS, cycles[0]


def test_two_cycles_average():
    """두 사이클의 고습 시간 평균이 맞는지."""
    rows = make_rows([
        # 사이클1: VENT 85 → 65 (2칸=4초)
        (50, IDLE), (85, VENT), (75, VENT), (65, VENT), (50, IDLE),
        # 사이클2: VENT 90 → 60 (3칸=6초)
        (88, VENT), (80, VENT), (72, VENT), (60, VENT), (50, IDLE),
    ])
    avg, cycles = average_high_humidity(rows)
    done = [c for c in cycles if c["seconds"] is not None]
    assert len(done) == 2, done
    assert done[0]["seconds"] == 2 * SAMPLE_SECONDS
    assert done[1]["seconds"] == 3 * SAMPLE_SECONDS
    assert avg == (2 * SAMPLE_SECONDS + 3 * SAMPLE_SECONDS) / 2


def test_incomplete_cycle_excluded():
    """습도가 끝까지 70 밑으로 안 떨어지면 평균에서 제외된다."""
    rows = make_rows([
        (50, IDLE), (85, VENT), (80, VENT), (75, VENT),   # 끝까지 >=70
    ])
    avg, cycles = average_high_humidity(rows)
    assert cycles[0]["seconds"] is None, cycles
    assert avg is None


def test_reduction_percentage():
    """감소율 계산이 상식과 맞는지 (기준선 100초 → 설치후 60초 = 40%)."""
    base, after = 100.0, 60.0
    reduction = (base - after) / base * 100
    assert abs(reduction - 40.0) < 1e-9


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
