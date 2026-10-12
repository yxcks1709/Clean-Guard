-- CleanGuard: AI detection (odor, door/window, lights, leaks, frozen pipes)
-- Run once in phpMyAdmin (SQL tab) or: mysql -u root cleanguard < 001_ai_detection.sql

SET NAMES utf8mb4;

-- 1) New optional sensor columns. NULL = that sensor isn't installed on the device.
ALTER TABLE sensor_data
    ADD COLUMN lux         FLOAT      NULL AFTER air_quality,
    ADD COLUMN door_open   TINYINT(1) NULL AFTER lux,
    ADD COLUMN window_open TINYINT(1) NULL AFTER door_open;

ALTER TABLE sensor_data_test
    ADD COLUMN lux         FLOAT      NULL AFTER air_quality,
    ADD COLUMN door_open   TINYINT(1) NULL AFTER lux,
    ADD COLUMN window_open TINYINT(1) NULL AFTER door_open;

-- 2) One AI decision per reading (live and test tables), written by ai/worker.py (saveAIStatus.php),
--    read by the dashboard (getAIStatus.php).
CREATE TABLE IF NOT EXISTS ai_predictions (
    id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    source             VARCHAR(10)  NOT NULL DEFAULT 'live', -- live = sensor_data, test = sensor_data_test
    device_id          VARCHAR(50)  NOT NULL,
    reading_id         INT UNSIGNED NOT NULL,          -- sensor_data.id this decision was made on
    created_at         DATETIME     NOT NULL,          -- time of that reading
    processed_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ready              TINYINT(1)   NOT NULL,          -- 0 during the model's 2 h warm-up
    level              VARCHAR(10)  NOT NULL,          -- 평상시 / 정보 / 주의 / 긴급 / 준비 중
    headline           VARCHAR(200) NOT NULL,
    odor               TINYINT(1)   NOT NULL DEFAULT 0,
    odor_minutes       FLOAT        NULL,
    door_open          TINYINT(1)   NULL,
    door_source        VARCHAR(10)  NULL,              -- sensor | ai
    window_open        TINYINT(1)   NULL,
    window_source      VARCHAR(10)  NULL,
    light_on           TINYINT(1)   NULL,              -- NULL = no light sensor
    lux                FLOAT        NULL,
    leak               TINYINT(1)   NOT NULL DEFAULT 0,
    leak_probability   FLOAT        NULL,
    pipe_frozen        TINYINT(1)   NOT NULL DEFAULT 0,
    freeze_risk_1h     VARCHAR(10)  NOT NULL DEFAULT '없음',  -- 없음 / 주의 / 경보
    freeze_risk_3h     VARCHAR(10)  NOT NULL DEFAULT '없음',
    items_json         TEXT         NULL,              -- [{level, code, message}, ...]
    probabilities_json TEXT         NULL,              -- {label: probability} for all 16 model labels
    UNIQUE KEY uq_source_device_reading (source, device_id, reading_id),
    KEY idx_source_device_time (source, device_id, created_at)
) DEFAULT CHARSET = utf8mb4;
