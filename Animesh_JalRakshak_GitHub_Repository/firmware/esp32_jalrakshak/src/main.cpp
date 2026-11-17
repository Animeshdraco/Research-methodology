/*
 * JalRakshak ESP32 telemetry firmware - hardware integration template.
 *
 * IMPORTANT: this source is provided for bench integration, not as evidence
 * that sensors were physically connected or calibrated. Set sensor
 * coefficients from calibration records and install the correct server CA
 * before enabling transmission. Do not connect pumps or UV lamps to GPIOs.
 */
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h>
#include <math.h>
#include <time.h>
#include "secrets.h"

#ifndef DEVICE_ID
#define DEVICE_ID "JW-01"
#endif

// Two ADS1115 modules: address 0x48 and 0x49. Each carries one water line.
Adafruit_ADS1115 adcRaw;
Adafruit_ADS1115 adcPure;
constexpr uint8_t ONEWIRE_PIN = 4;
OneWire oneWire(ONEWIRE_PIN);
DallasTemperature temperatures(&oneWire);

// Analog channels: pH=AIN0, turbidity=AIN1, TDS=AIN2 for both ADS1115 devices.
// Sensor outputs MUST be conditioned to the ADS1115 input range before wiring.
enum Channel : uint8_t { PH_CH = 0, TURB_CH = 1, TDS_CH = 2 };
constexpr float ADC_LSB_VOLTS = 0.000125f; // ADS1115 GAIN_ONE: 125 uV/bit
constexpr float TDS_TEMP_COEFF = 0.02f;     // typical compensation coefficient; verify per probe
constexpr float TDS_K_VALUE = 1.0f;         // calibrate with reference solution

// Calibrate pH and turbidity with reference buffers/standards; do not leave 0.
// pH = slope * measured_voltage + intercept
constexpr float PH_SLOPE = 0.0f;
constexpr float PH_INTERCEPT = 0.0f;
// NTU = slope * measured_voltage + intercept; valid only for the calibrated probe/range.
constexpr float TURB_SLOPE = 0.0f;
constexpr float TURB_INTERCEPT = 0.0f;

static float readVoltage(Adafruit_ADS1115 &adc, Channel ch) {
  int16_t raw = adc.readADC_SingleEnded(static_cast<uint8_t>(ch));
  return static_cast<float>(raw) * ADC_LSB_VOLTS;
}

static float phFromVoltage(float v) {
  if (PH_SLOPE == 0.0f || PH_INTERCEPT == 0.0f) return NAN;
  return PH_SLOPE * v + PH_INTERCEPT;
}

static float turbidityFromVoltage(float v) {
  if (TURB_SLOPE == 0.0f) return NAN;
  return max(0.0f, TURB_SLOPE * v + TURB_INTERCEPT);
}

static float tdsFromVoltage(float v, float temperatureC) {
  // DFRobot-style polynomial, with a module-specific calibration multiplier.
  const float compensation = 1.0f + TDS_TEMP_COEFF * (temperatureC - 25.0f);
  const float compensatedV = v / max(0.1f, compensation);
  const float ppm = (133.42f * powf(compensatedV, 3) -
                     255.86f * powf(compensatedV, 2) +
                     857.39f * compensatedV) * 0.5f;
  return max(0.0f, ppm * TDS_K_VALUE);
}

static bool validReading(float v, float lo, float hi) {
  return isfinite(v) && v >= lo && v <= hi;
}

static void addNullable(JsonObject obj, const char *key, float value, float lo, float hi) {
  if (validReading(value, lo, hi)) obj[key] = value;
  else obj[key] = nullptr;
}

static bool readLine(Adafruit_ADS1115 &adc, float temperatureC, JsonObject target) {
  const float phV = readVoltage(adc, PH_CH);
  const float turbV = readVoltage(adc, TURB_CH);
  const float tdsV = readVoltage(adc, TDS_CH);
  const float ph = phFromVoltage(phV);
  const float turb = turbidityFromVoltage(turbV);
  const float tds = tdsFromVoltage(tdsV, temperatureC);
  addNullable(target, "ph", ph, 0.0f, 14.0f);
  addNullable(target, "turbidity_ntu", turb, 0.0f, 10000.0f);
  addNullable(target, "tds_mg_l", tds, 0.0f, 100000.0f);
  addNullable(target, "temperature_c", temperatureC, -10.0f, 100.0f);
  return validReading(ph, 0, 14) && validReading(turb, 0, 10000) &&
         validReading(tds, 0, 100000) && validReading(temperatureC, -10, 100);
}

static bool clockTimestamp(char *buffer, size_t length) {
  time_t now = time(nullptr);
  if (now < 1760000000) return false; // NTP not synchronised; do not emit a fake timestamp.
  struct tm utc;
  gmtime_r(&now, &utc);
  return strftime(buffer, length, "%Y-%m-%dT%H:%M:%SZ", &utc) > 0;
}

static bool postReading(JsonDocument &doc) {
  WiFiClientSecure tls;
  tls.setCACert(JALRAKSHAK_ROOT_CA); // Replace with API host's trusted CA chain.
  HTTPClient http;
  if (!http.begin(tls, JALRAKSHAK_API_URL)) return false;
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Key", JALRAKSHAK_DEVICE_KEY);
  String body;
  serializeJson(doc, body);
  int code = http.POST(body);
  String response = http.getString();
  Serial.printf("POST /api/v1/readings -> %d, response bytes=%u\n", code, response.length());
  http.end();
  return code == 201;
}

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  if (!adcRaw.begin(0x48) || !adcPure.begin(0x49)) {
    Serial.println("ADS1115 initialisation failed; check I2C wiring and addresses.");
    while (true) delay(1000);
  }
  adcRaw.setGain(GAIN_ONE);
  adcPure.setGain(GAIN_ONE);
  temperatures.begin();
  WiFi.mode(WIFI_STA);
  WiFi.begin(JALRAKSHAK_WIFI_SSID, JALRAKSHAK_WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println(" connected");
  configTime(0, 0, "pool.ntp.org", "time.google.com");
  Serial.println("Waiting for NTP time synchronisation");
  char ts[25];
  for (int attempt = 0; attempt < 30 && !clockTimestamp(ts, sizeof(ts)); ++attempt) delay(1000);
  if (!clockTimestamp(ts, sizeof(ts))) Serial.println("NTP not ready; telemetry remains disabled until time is available.");
  Serial.println("Verify pH/turbidity calibration constants before using this node.");
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    temperatures.requestTemperatures();
    float rawTemp = temperatures.getTempCByIndex(0);
    float pureTemp = temperatures.getTempCByIndex(1);
    StaticJsonDocument<1024> doc;
    doc["device_id"] = DEVICE_ID;
    char timestamp[25];
    if (!clockTimestamp(timestamp, sizeof(timestamp))) {
      Serial.println("NTP time unavailable; refusing to send an incorrectly timestamped record.");
      delay(30000);
      return;
    }
    doc["timestamp"] = timestamp;
    doc["data_source"] = "hardware";
    doc["firmware_version"] = "0.1.0-calibration-required";
    JsonObject raw = doc.createNestedObject("raw");
    JsonObject pure = doc.createNestedObject("purified");
    bool rawOk = readLine(adcRaw, rawTemp, raw);
    bool pureOk = readLine(adcPure, pureTemp, pure);
    if (rawOk && pureOk) {
      bool ok = postReading(doc);
      Serial.println(ok ? "Reading accepted" : "Reading rejected; check API, key, TLS and network");
    } else {
      Serial.println("No transmission: calibration or sensor range invalid. Check probes and coefficients.");
    }
  }
  delay(60UL * 60UL * 1000UL); // one-hour research sampling interval; tune after requirements review
}
