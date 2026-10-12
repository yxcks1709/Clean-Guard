-- CleanGuard: full local database (XAMPP) for testing before deploying.
-- Creates everything from scratch, already including the AI migration
-- (so do NOT also run migrations/001_ai_detection.sql on this database).
-- phpMyAdmin -> SQL tab -> paste and run, or:
--   C:\xampp\mysql\bin\mysql.exe -u root < database\setup_local.sql

SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS cleanguard CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE cleanguard;

CREATE TABLE IF NOT EXISTS devices (
    id       VARCHAR(50)  NOT NULL PRIMARY KEY,
    NAME     VARCHAR(100) NOT NULL,
    location VARCHAR(150) NOT NULL,
    STATUS   VARCHAR(20)  NOT NULL DEFAULT '정상'
) DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS sensor_data (
    id          INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    device_id   VARCHAR(50)  NOT NULL,
    temperature DECIMAL(5,2) NOT NULL,
    humidity    DECIMAL(5,2) NOT NULL,
    air_quality VARCHAR(20)  NOT NULL,
    lux         FLOAT        NULL,
    door_open   TINYINT(1)   NULL,
    window_open TINYINT(1)   NULL,
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX (device_id),
    INDEX (created_at)
) DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS sensor_data_test LIKE sensor_data;

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

-- The board in esp8266/include/secrets.h (DEVICE_ID) and the simulator use this ID.
INSERT IGNORE INTO devices (id, NAME, location, STATUS)
VALUES ('D1 Mini 302', 'D1 Mini 302', '본관 3층 화장실 302호', '정상');
