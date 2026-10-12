# Database

No `.sql` migration/dump files exist in this project's history, so this
document describes the tables `backend/*.php` expects, inferred directly
from the columns each query actually reads and writes. Use it as a
reference schema to stand up a compatible MySQL/MariaDB database — it is
not an exported dump of any specific server.

## `devices`

The device registry (Device Management CRUD). One row per physical sensor
node.

| Column     | Type (suggested)         | Notes                                             |
|------------|---------------------------|----------------------------------------------------|
| `id`       | `VARCHAR(50)` PRIMARY KEY | Device ID, e.g. `D1-001`. Set once, never updated. |
| `NAME`     | `VARCHAR(100)`             | Display name, e.g. `D1 Mini 2`.                    |
| `location` | `VARCHAR(150)`             | Free text: `"<건물> <층>층 화장실 <호>호"`. Parsed by `frontend/src/utils/location.js`. |
| `STATUS`   | `VARCHAR(20)`               | One of `정상` / `점검중` / `고장` (see `frontend/src/constants.js`). |

```sql
CREATE TABLE devices (
    id       VARCHAR(50)  NOT NULL PRIMARY KEY,
    NAME     VARCHAR(100) NOT NULL,
    location VARCHAR(150) NOT NULL,
    STATUS   VARCHAR(20)  NOT NULL DEFAULT '정상'
);
```

## `sensor_data` and `sensor_data_test`

Raw sensor readings. Identical structure; `sensor_data` is the Live table,
`sensor_data_test` is the Test table (selected by `?table=` on the read
endpoints, or `"table"` in `upload.php`'s request body). History mode
always reads from `sensor_data` — there is no separate history table.

| Column        | Type (suggested)     | Notes                                                     |
|---------------|------------------------|-------------------------------------------------------------|
| `id`          | `INT` PRIMARY KEY AUTO_INCREMENT | Reading ID.                                       |
| `device_id`   | `VARCHAR(50)`           | Foreign key to `devices.id`.                                |
| `temperature` | `DECIMAL(5,2)` / `FLOAT` | Degrees Celsius.                                             |
| `humidity`    | `DECIMAL(5,2)` / `FLOAT` | Relative humidity, percent.                                  |
| `air_quality` | `VARCHAR(20)` or numeric | `frontend/src/utils/status.js` compares this against the string `"나쁨"`; `backend/getHistory.php` also runs `AVG()` on it for the trend chart — confirm which convention your sensor firmware sends before choosing a type. |
| `created_at`  | `DATETIME` / `TIMESTAMP` | Not supplied by `upload.php`'s INSERT — should default to `CURRENT_TIMESTAMP`. |

```sql
CREATE TABLE sensor_data (
    id          INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    device_id   VARCHAR(50)  NOT NULL,
    temperature DECIMAL(5,2) NOT NULL,
    humidity    DECIMAL(5,2) NOT NULL,
    air_quality VARCHAR(20)  NOT NULL,
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX (device_id),
    INDEX (created_at)
);

CREATE TABLE sensor_data_test LIKE sensor_data;
```

> `backend/upload.php` also accepts a `"table": "history"` value that maps
> to `sensor_data_history` — that table does not exist in the schema
> above. This is a pre-existing inconsistency in the endpoint, left
> unmodified per this cleanup's "do not change functionality" scope; see
> `backend/README.md`.

## AI detection (migration `migrations/001_ai_detection.sql`)

Run [`migrations/001_ai_detection.sql`](migrations/001_ai_detection.sql) once.
It adds three optional columns to `sensor_data` and `sensor_data_test`
(`NULL` when that sensor isn't installed on the device):

| Column        | Type         | Notes |
|---------------|--------------|-------|
| `lux`         | `FLOAT`      | BH1750 light level. |
| `door_open`   | `TINYINT(1)` | Door reed switch, 1 = open. |
| `window_open` | `TINYINT(1)` | Window reed switch, 1 = open. |

`air_quality` now holds the raw MQ-135 ADC value (0–1023) sent by the firmware.

It also creates `ai_predictions`: one row per AI decision, written by
`ai/worker.py` through `backend/saveAIStatus.php` and read by
`backend/getAIStatus.php`. Key columns: `device_id`, `reading_id`
(→ `sensor_data.id`), `created_at`, `ready` (0 during the model's 2 h warm-up),
`level` (평상시 / 정보 / 주의 / 긴급 / 준비 중), `headline`, `odor`, `door_open` +
`door_source` (sensor | ai), `window_open` + `window_source`, `light_on`, `lux`,
`leak`, `leak_probability`, `pipe_frozen`, `freeze_risk_1h` / `freeze_risk_3h`
(없음 / 주의 / 경보), `items_json` (all alerts) and `probabilities_json` (all 16
model labels). It replaces the old `restroom_sencor_fake_data` table, which
nothing reads anymore.

## Setting up credentials

None of the above requires committing real credentials. Copy
`backend/config.local.example.php` to `backend/config.local.php` (git
ignored) and fill in your real host/database/user/password, or set the
`DB_HOST` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` environment variables.
See `.env.example` and `backend/README.md`.
