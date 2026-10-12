# Backend — PHP REST API

PHP 8 + MySQLi, one file per endpoint, no framework. Every endpoint
includes `config.php` for its database connection, sets CORS headers so
the React frontend (served from a different origin) can call it, and
returns JSON.

## Setup

1. Copy `config.local.example.php` to `config.local.php` in this folder
   and fill in your real database host/name/user/password.
   `config.local.php` is git-ignored and never committed.
   - Alternatively, set the `DB_HOST` / `DB_NAME` / `DB_USER` /
     `DB_PASSWORD` environment variables on your server — `config.php`
     falls back to those if `config.local.php` doesn't exist.
2. Create the tables described in [`../database/README.md`](../database/README.md).
3. Point your PHP host (or the frontend's `VITE_API_URL`, see
   [`../frontend/.env.example`](../frontend/.env.example)) at wherever
   this `backend/` folder is served from.

## Endpoints

| File | Method | Responsibility |
|---|---|---|
| `upload.php` | POST | Ingests one ESP8266 reading (JSON or form-encoded; optional `lux`, `door`, `window`); inserts into `sensor_data` / `sensor_data_test`. |
| `getSensors.php` | GET | Latest reading per device (`?table=live\|test`) — powers Live/Test mode. |
| `getHistory.php` | GET | One device's readings (`?device_id=`), grouped into 5-minute buckets — powers the trend chart. |
| `getSensorLog.php` | GET | Every reading, newest first, paginated (`?page=&pageSize=`) — powers History mode's log. |
| `getDevices.php` | GET | Full device registry. |
| `addDevice.php` | POST | Adds a device (validates required fields + unique ID). |
| `updateDevice.php` | POST | Updates a device's name/location/status (ID is read-only). |
| `deleteDevice.php` | POST | Removes a device. |
| `getAIStatus.php` | GET | Latest (or timestamp-matched, `&at=`) AI decision for a device from `ai_predictions`: odor, door/window, lights, leak, frozen pipes. Used by `AIStatusCard`. |
| `getAIInput.php` | GET | Raw readings for the AI service (`?after_id=` or `?since_minutes=`). Requires the `X-API-Key` header. |
| `saveAIStatus.php` | POST | Stores AI decisions into `ai_predictions`. Requires the `X-API-Key` header. |

All write endpoints use prepared statements with bound parameters.

The AI endpoints share a key defined in `ai_config.php` (or the
`CLEANGUARD_AI_KEY` environment variable); put the same value in
`ai/config.json`. See [`../ai/README.md`](../ai/README.md).
