<?php

header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json");

include "config.php";

/*
    Latest AI decision for a device, from `ai_predictions` (written by
    ai/worker.py through saveAIStatus.php).

      getAIStatus.php?device_id=D1-001
            Newest decision (Live/Test mode).

      getAIStatus.php?device_id=D1-001&at=2026-07-13 15:30:00
            Decision closest to `at` within 5 minutes (History mode).

      &table=test   decisions made on sensor_data_test (Test tab).
*/

$deviceId = $_GET["device_id"] ?? null;
$at = $_GET["at"] ?? null;
$source = (($_GET["table"] ?? "live") === "test") ? "test" : "live";

if (!$deviceId) {
    echo json_encode(["available" => false, "error" => "device_id is required"]);
    exit;
}

$columns = "
    source, device_id, reading_id, created_at, processed_at, ready, level, headline,
    odor, odor_minutes, door_open, door_source, window_open, window_source,
    light_on, lux, leak, leak_probability, pipe_frozen, freeze_risk_1h, freeze_risk_3h,
    items_json, probabilities_json
";

$TOLERANCE_SECONDS = 300;

if ($at) {
    $stmt = $conn->prepare("
        SELECT $columns
        FROM ai_predictions
        WHERE source = ? AND device_id = ?
          AND created_at BETWEEN (? - INTERVAL $TOLERANCE_SECONDS SECOND) AND (? + INTERVAL $TOLERANCE_SECONDS SECOND)
        ORDER BY ABS(TIMESTAMPDIFF(SECOND, created_at, ?)) ASC
        LIMIT 1
    ");
    $stmt->bind_param("sssss", $source, $deviceId, $at, $at, $at);
} else {
    $stmt = $conn->prepare("
        SELECT $columns
        FROM ai_predictions
        WHERE source = ? AND device_id = ?
        ORDER BY created_at DESC, reading_id DESC
        LIMIT 1
    ");
    $stmt->bind_param("ss", $source, $deviceId);
}

$stmt->execute();
$row = $stmt->get_result()->fetch_assoc();

if (!$row) {
    echo json_encode(["available" => false]);
} else {
    foreach (["ready", "odor", "door_open", "window_open", "light_on", "leak", "pipe_frozen"] as $flag) {
        $row[$flag] = $row[$flag] === null ? null : (bool)$row[$flag];
    }
    foreach (["odor_minutes", "lux", "leak_probability"] as $number) {
        $row[$number] = $row[$number] === null ? null : floatval($row[$number]);
    }
    $row["items"] = json_decode($row["items_json"] ?? "[]", true) ?: [];
    $row["probabilities"] = json_decode($row["probabilities_json"] ?? "{}", true) ?: new stdClass();
    unset($row["items_json"], $row["probabilities_json"]);
    $row["available"] = true;
    echo json_encode($row, JSON_UNESCAPED_UNICODE);
}

$stmt->close();
$conn->close();
