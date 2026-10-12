/*
 * CleanGuard sensor node (Wemos D1 mini / ESP8266)
 *
 * Every 15 s it reads the sensors and POSTs one JSON reading to backend/upload.php.
 * The AI service (ai/worker.py) turns those readings into: bad odor, door/window
 * open, lights on, water leak and frozen-pipe alerts.
 *
 * Wiring (see esp8266/README.md for the full table):
 *   DHT11  DATA -> D2 (GPIO4)  (same as before)    temperature / humidity
 *   MQ-135 AO   -> 180k resistor -> A0             odor / air quality (A0 max 3.2 V on the D1 mini)
 *   BH1750 SDA  -> D6 (GPIO12), SCL -> D5 (GPIO14) light level (lux)          [optional]
 *   Door reed switch   -> D7 (GPIO13) and GND      closed = magnet near       [optional]
 *   Window reed switch -> D1 (GPIO5)  and GND                                 [optional]
 *
 * Wi-Fi, server URL and device ID live in include/secrets.h (git-ignored).
 * Copy include/secrets.example.h to include/secrets.h and edit it.
 */

#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <Wire.h>
#include <DHT.h>
#include <BH1750.h>

#include "secrets.h"

// ---- Which optional sensors are installed (1 = yes, 0 = no) ----
#ifndef USE_LIGHT_SENSOR
#define USE_LIGHT_SENSOR 1
#endif
#ifndef USE_DOOR_SWITCH
#define USE_DOOR_SWITCH 1
#endif
#ifndef USE_WINDOW_SWITCH
#define USE_WINDOW_SWITCH 1
#endif

// ---- Pins ----
#define DHT_PIN D2
#define DHT_TYPE DHT11
#define MQ135_PIN A0
#define DOOR_PIN D7
#define WINDOW_PIN D1
#define I2C_SDA D6
#define I2C_SCL D5

// The AI model works on one reading every 15 seconds.
const unsigned long SEND_INTERVAL_MS = 15000;
// MQ-135: average several ADC samples to remove noise.
const int MQ135_SAMPLES = 16;

DHT dht(DHT_PIN, DHT_TYPE);
#if USE_LIGHT_SENSOR
BH1750 lightMeter;
bool lightOk = false;
#endif

unsigned long lastSend = 0;

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Wi-Fi 연결 중");
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(WiFi.status() == WL_CONNECTED ? "\nWi-Fi 연결 성공!" : "\nWi-Fi 연결 실패 (다음 주기에 재시도)");
}

int readMq135() {
  long sum = 0;
  for (int i = 0; i < MQ135_SAMPLES; i++) {
    sum += analogRead(MQ135_PIN);
    delay(5);
  }
  return (int)(sum / MQ135_SAMPLES);
}

// Reed switch wired between the pin and GND with INPUT_PULLUP:
// magnet near (door/window closed) -> contact closed -> LOW.
bool isOpen(uint8_t pin) {
  return digitalRead(pin) == HIGH;
}

void setup() {
  Serial.begin(115200);
  dht.begin();
#if USE_DOOR_SWITCH
  pinMode(DOOR_PIN, INPUT_PULLUP);
#endif
#if USE_WINDOW_SWITCH
  pinMode(WINDOW_PIN, INPUT_PULLUP);
#endif
#if USE_LIGHT_SENSOR
  Wire.begin(I2C_SDA, I2C_SCL);
  lightOk = lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE);
  Serial.println(lightOk ? "BH1750 OK" : "BH1750 없음 (조도 값 없이 전송)");
#endif
  connectWiFi();
}

void loop() {
  if (lastSend != 0 && millis() - lastSend < SEND_INTERVAL_MS) {
    delay(50);
    return;
  }

  float temp = dht.readTemperature();
  float hum = dht.readHumidity();
  if (isnan(temp) || isnan(hum)) {
    Serial.println("DHT 센서 읽기 실패! 2초 후 재시도");
    delay(2000);
    return;
  }
  lastSend = millis();

  int air = readMq135();

  String body = "{\"id\":\"" + String(DEVICE_ID) + "\"";
  body += ",\"temperature\":" + String(temp, 1);
  body += ",\"humidity\":" + String(hum, 1);
  body += ",\"airQuality\":" + String(air);
#if USE_LIGHT_SENSOR
  if (lightOk) {
    float lux = lightMeter.readLightLevel();
    if (lux >= 0) body += ",\"lux\":" + String(lux, 1);
  }
#endif
#if USE_DOOR_SWITCH
  body += ",\"door\":" + String(isOpen(DOOR_PIN) ? 1 : 0);
#endif
#if USE_WINDOW_SWITCH
  body += ",\"window\":" + String(isOpen(WINDOW_PIN) ? 1 : 0);
#endif
  body += ",\"table\":\"live\"}";

  Serial.println(body);

  connectWiFi();
  if (WiFi.status() != WL_CONNECTED) return;

  WiFiClient client;
  HTTPClient http;
  http.begin(client, SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  int code = http.POST(body);
  Serial.print("HTTP Response code: ");
  Serial.println(code);
  http.end();
}
