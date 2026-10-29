/*
 * 샤워 후 화장실 환기 알림 — STM32 MCU 측 (Arduino UNO Q)
 *
 * 역할: 2초마다 DHT11(습도·온도)과 포토센서(조도)를 읽어 Bridge.notify로 리눅스(파이썬)에 전달.
 *       파이썬이 환기 완료라고 판단하면 set_buzzer를 호출해 부저를 울린다.
 *
 * 핀: DHT11 → D6, 포토센서(CDS+10kΩ 전압분배 가운데) → A2, 부저 모듈 → D8
 * 로직 전압: 3.3V (UNO Q / STM32)
 *
 * 필요 라이브러리: "DHT sensor library" (Adafruit). UNO Q(STM32 코어)에서 컴파일되는지 확인 필요.
 */

#include "Arduino_RouterBridge.h"
#include "DHT.h"

#define DHT_PIN    6
#define DHT_TYPE   DHT11
#define LIGHT_PIN  A2
#define BUZZER_PIN 8

#define SAMPLE_INTERVAL_MS 2000   // 2초마다 측정 (experiment.md 참고)

DHT dht(DHT_PIN, DHT_TYPE);
unsigned long lastSample = 0;

// 파이썬이 notify로 호출하는 함수 — 부저 켜기(1)/끄기(0)
void set_buzzer(int on) {
  digitalWrite(BUZZER_PIN, on ? HIGH : LOW);
}

void setup() {
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  dht.begin();

  Bridge.begin();
  // provide_safe: loop() 사이에 안전하게 실행 (Arduino API 호출 가능)
  Bridge.provide_safe("set_buzzer", set_buzzer);
}

void loop() {
  unsigned long now = millis();
  if (now - lastSample >= SAMPLE_INTERVAL_MS) {
    lastSample = now;

    float humidity = dht.readHumidity();
    float temp     = dht.readTemperature();
    int   light    = analogRead(LIGHT_PIN);

    // DHT11 읽기 실패(NaN) 시 이번 샘플은 건너뜀
    if (!isnan(humidity) && !isnan(temp)) {
      // 세 값을 한 메시지로 전달 → 파이썬 on_sensor(humidity, temp, light)
      Bridge.notify("sensor", humidity, temp, light);
    }
  }

  // Bridge가 provide_safe 콜백을 처리할 수 있도록 loop를 막지 않는다
}
