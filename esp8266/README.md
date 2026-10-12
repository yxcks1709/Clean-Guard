# ESP8266 Sensor Node (Wemos D1 mini)

Firmware: [`src/main.cpp`](src/main.cpp) (PlatformIO, `platformio.ini`).
Every **15 seconds** the node reads its sensors and POSTs one JSON reading to
`backend/upload.php`. The AI service ([`../ai/`](../ai/README.md)) turns those
readings into odor, door/window, light, leak and frozen-pipe alerts.

## Wiring

| Sensor | Sensor pin | D1 mini pin | Notes |
|---|---|---|---|
| DHT11 | VCC / GND / DATA | 3V3 / G / **D2** | Same pin as before. 10 kΩ pull-up DATA→3V3 if your module has none |
| MQ-135 module | VCC / GND | **5V** / G | The heater needs 5 V (~150 mA) |
| MQ-135 module | AO | **A0 through a 180 kΩ resistor** | AO can reach 5 V; the D1 mini's A0 accepts 3.2 V max. 180 kΩ in series + the board's internal 220k/100k divider keeps the chip at ≤ 1.0 V |
| BH1750 (optional) | VCC / GND / SDA / SCL | 3V3 / G / **D6** / **D5** | Light level in lux. ADDR pin unconnected |
| Door reed switch (optional) | two wires | **D7** and G | Magnet on the door, switch on the frame: closed door = contact closed |
| Window reed switch (optional) | two wires | **D1** and G | Same as the door |

Reed switches use the internal pull-up, so no resistor is needed: contact
closed (magnet near) = `LOW` = closed; contact open = `HIGH` = open.

Sensors you don't install: set them to `0` in `platformio.ini`
(`USE_LIGHT_SENSOR`, `USE_DOOR_SWITCH`, `USE_WINDOW_SWITCH`). The backend then
stores `NULL` and the AI uses its model estimate for door/window instead.

New MQ-135 sensors should run powered for 24–48 h before their readings are
stable (burn-in). The AI also needs 2 h of history before its first decision.

## Configuration

Wi-Fi, server URL and device ID are in `include/secrets.h` (git-ignored).
Copy [`include/secrets.example.h`](include/secrets.example.h) to
`include/secrets.h` and edit:

```c
#define WIFI_SSID "..."
#define WIFI_PASSWORD "..."
#define SERVER_URL "http://<PC IPv4>/clean-guard/backend/upload.php"
#define DEVICE_ID "D1-001"   // must match devices.id (Device Management)
```

## Payload

```
POST /upload.php
Content-Type: application/json

{"id":"D1-001","temperature":21.0,"humidity":45.0,"airQuality":512,
 "lux":120.5,"door":0,"window":1,"table":"live"}
```

`airQuality` is the raw MQ-135 ADC value (0–1023, average of 16 samples).
`lux`, `door` and `window` are only sent when that sensor is enabled.
`upload.php` still accepts the old form-encoded format, so older boards keep working.
