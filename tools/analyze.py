"""
CSV 분석 헬퍼 — 단일 vent_log CSV에서 '고습 시간'을 계산한다.

실행: python3 tools/analyze.py [CSV경로]
기본 입력: data/sample_vent_log.csv
matplotlib이 설치돼 있으면 그래프 PNG도 저장한다(선택).

기준선 vs 설치후 비교는 tools/compare.py 참고.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from vent_logic import SAMPLE_SECONDS
from vent_metrics import HIGH_HUM, load_rows, find_cycles


def sparkline(values):
    blocks = "▁▂▃▄▅▆▇█"
    lo, hi = min(values), max(values)
    if hi == lo:
        return blocks[0] * len(values)
    out = []
    for v in values:
        idx = int((v - lo) / (hi - lo) * (len(blocks) - 1))
        out.append(blocks[idx])
    return "".join(out)


def maybe_plot(rows, csv_path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("(matplotlib 없음 → 그래프 PNG는 건너뜀. ASCII 그래프만 출력)")
        return None

    hums = [float(r["humidity"]) for r in rows]
    lights = [int(r["light"]) for r in rows]
    xs = [i * SAMPLE_SECONDS for i in range(len(rows))]

    fig, ax1 = plt.subplots(figsize=(10, 4))
    ax1.plot(xs, hums, color="tab:blue", label="humidity(%)")
    ax1.set_xlabel("time (s)")
    ax1.set_ylabel("humidity (%)", color="tab:blue")
    ax1.axhline(HIGH_HUM, color="tab:red", linestyle="--", linewidth=1, label="high-hum 70%")
    ax2 = ax1.twinx()
    ax2.plot(xs, lights, color="tab:orange", alpha=0.5, label="light")
    ax2.set_ylabel("light", color="tab:orange")
    fig.tight_layout()

    png = os.path.splitext(csv_path)[0] + ".png"
    fig.savefig(png, dpi=100)
    plt.close(fig)
    return png


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "data", "sample_vent_log.csv"
    )
    if not os.path.exists(path):
        print(f"CSV를 찾을 수 없음: {path}")
        print("먼저 'python3 tools/simulate.py'로 샘플을 만들거나 수집한 CSV 경로를 주세요.")
        return 1

    rows = load_rows(path)
    print(f"분석 대상: {os.path.normpath(path)}  (행 {len(rows)}개, 샘플주기 {SAMPLE_SECONDS}s)")

    hums = [float(r["humidity"]) for r in rows]
    print(f"습도 범위: {min(hums):.1f} ~ {max(hums):.1f} %RH")
    print(f"습도 추이: {sparkline(hums)}")

    cycles = find_cycles(rows)
    print(f"\n감지된 환기 사이클: {len(cycles)}개  (고습 기준 {HIGH_HUM:.0f}%RH 이상)")
    done = [c for c in cycles if c["seconds"] is not None]
    for k, c in enumerate(cycles, 1):
        if c["seconds"] is None:
            print(f"  #{k}: {c['start']} ~ (데이터 내 미하강)")
        else:
            print(f"  #{k}: {c['start']} ~ {c['drop']}  고습 시간 {c['seconds']}초 "
                  f"({c['seconds'] / 60:.1f}분)")

    if done:
        avg = sum(c["seconds"] for c in done) / len(done)
        print(f"\n평균 고습 시간: {avg:.0f}초 ({avg / 60:.1f}분)  — 성공 기준 비교용 지표")

    png = maybe_plot(rows, path)
    if png:
        print(f"그래프 저장: {os.path.normpath(png)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
