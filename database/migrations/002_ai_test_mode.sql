-- Only if you already ran 001_ai_detection.sql BEFORE 2026-10-13 01:30
-- (its ai_predictions table had no `source` column). Adds AI decisions for the Test tab.

SET NAMES utf8mb4;

ALTER TABLE ai_predictions
    ADD COLUMN source VARCHAR(10) NOT NULL DEFAULT 'live' AFTER id,
    DROP INDEX uq_device_reading,
    DROP INDEX idx_device_time,
    ADD UNIQUE KEY uq_source_device_reading (source, device_id, reading_id),
    ADD KEY idx_source_device_time (source, device_id, created_at);
