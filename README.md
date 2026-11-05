# 샤워 후 화장실 환기 알림 장치 (bathroom-vent-alert)

샤워 후 환기(창문/환풍기)로 **습도가 충분히 낮아지면 부저로 "이제 닫아도/꺼도 된다"고 알려주는** 아두이노 장치.

수업 팀 과제 저장소입니다. 실험 설계 전체 명세는 [`docs/experiment.md`](docs/experiment.md)를 참고하세요.

## 구성

Arduino UNO Q의 App Lab + Bricks 구조를 따른다 (한 보드 안의 STM32 MCU + 내장 리눅스).

```
bathroom-vent-alert/
├── README.md
├── docs/
│   └── experiment.md     # 실험 전체 명세 (단일 기준점)
├── app/                  # App Lab 프로젝트 (App Lab에서 이 폴더를 연다)
│   ├── app.yaml          # bricks: arduino:sketch + arduino:python
│   ├── sketch/sketch.ino # STM32 MCU: DHT11·포토센서 읽기 + 부저
│   └── python/
│       ├── main.py       # 리눅스: Bridge 수신 + CSV 기록 (실물)
│       └── vent_logic.py # 순수 상태 판단 로직 (하드웨어 의존 없음)
├── tools/
│   ├── simulate.py       # 하드웨어 없이 샘플 CSV 생성 (데모용)
│   └── analyze.py        # CSV에서 '고습 시간' 계산 + 그래프(선택)
├── tests/
│   └── test_vent_logic.py # 상태머신 로직 테스트
└── data/
    └── sample_vent_log.csv # 시뮬레이터가 만든 데모 데이터
```

## 하드웨어 요약

- **보드**: Arduino UNO Q (STM32 MCU + Qualcomm 리눅스, 로직 3.3V)
- **센서**: DHT11 온습도(D6), 포토센서 CDS+10kΩ(A2)
- **출력**: 부저 모듈(D8)

자세한 핀 배치·판단 로직은 [`docs/experiment.md`](docs/experiment.md) 참고.

## 실행 (UNO Q)

1. 보드의 Debian에 기본 설치된 **Arduino App Lab**에서 `app/` 폴더를 연다.
2. 빌드/배포 — App Lab이 스케치(STM32)와 파이썬(리눅스)을 함께 올린다.
3. 파이썬 쪽 로그와 `vent_log.csv`로 센서값·상태를 확인한다.

- 기준선 측정(부저 끔): 환경변수 `VENT_BASELINE=1`
- CSV 경로 변경: 환경변수 `VENT_LOG=/경로/vent_log.csv`

## 데모·테스트 (하드웨어 없이)

보드 없이 코드 로직만 검증·시연할 수 있다.

```bash
python3 tests/test_vent_logic.py   # 상태머신 로직 테스트 (pytest 불필요)
python3 tools/simulate.py          # 샤워→환기→완료 1사이클 샘플 CSV 생성
python3 tools/analyze.py           # 생성된 CSV에서 '고습 시간' 계산
```

`simulate.py`는 `data/sample_vent_log.csv`를 만들고, `analyze.py`는 거기서
환기 사이클별 고습 시간(VENT 시작~습도<70)과 평균을 계산한다.
matplotlib이 있으면 습도·조도 그래프 PNG도 저장한다.

> ⚠️ `sketch.ino`는 "DHT sensor library"가 필요하며, UNO Q(STM32 코어)에서 컴파일되는지 실물 확인이 필요하다.
> 판단 기준값(습도 55%, 조도 500 등)은 가짜 값으로, 9주차 모의실험·11주차 실측으로 확정한다.

## 작업 방식 (주차별 PR)

- 매주 브랜치 생성 → 작업 커밋 → PR 생성
- 브랜치: `week09-...`, PR 제목: `[9주차] ...`
- PR 본문에 **주차별 작업 현황 요약문** 포함

## 진행 현황

| 주차 | 작업물 | 상태 |
|------|--------|------|
| 8 | 회로도·결선도·비교표 | - |
| 9 | 센서→파이썬→CSV 코드 구현 | ✅ 완료 (PR #1) |
| 10 | 현재 구현 시연: 로직 테스트·시뮬레이터·분석기 | 진행 중 |
