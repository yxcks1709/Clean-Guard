<?php

header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json");

include "config.php";
include "ai_config.php";

/*
    Stores AI decisions written by ai/worker.py into `ai_predictions`.
    Requires X-API-Key. Body: {"predictions": [ <decision>, ... ]}

    `source` is "live" (sensor_data) or "test" (sensor_data_test).
    One row per (source, device_id, reading_id); re-sending the same decision
    overwrites it, so the worker can safely retry.
*/

cleanguard_require_ai_key($AI_API_KEY);

$body = json_decode(file_get_contents("php://input"), true);
$predictions = $body["predictions"] ?? null;

if (!is_array($predictions)) {
    echo json_encode(["success" => false, "error" => "predictions[] is required"]);
    exit;
}

function flag($value)
{
    return $value === null ? null : ($value ? 1 : 0);
}

$stmt = $conn->prepare("
    INSERT INTO ai_predictions (
        source, device_id, reading_id, created_at, ready, level, headline,
        odor, odor_minutes, door_open, door_source, window_open, window_source,
        light_on, lux, leak, leak_probability, pipe_frozen, freeze_risk_1h, freeze_risk_3h,
        items_json, probabilities_json
    ) VALUES (?,?,?,?,?,?,?, ?,?,?,?,?,?, ?,?,?,?,?,?,?, ?,?)
    ON DUPLICATE KEY UPDATE
        created_at = VALUES(created_at), ready = VALUES(ready), level = VALUES(level),
        headline = VALUES(headline), odor = VALUES(odor), odor_minutes = VALUES(odor_minutes),
        door_open = VALUES(door_open), door_source = VALUES(door_source),
        window_open = VALUES(window_open), window_source = VALUES(window_source),
        light_on = VALUES(light_on), lux = VALUES(lux), leak = VALUES(leak),
        leak_probability = VALUES(leak_probability), pipe_frozen = VALUES(pipe_frozen),
        freeze_risk_1h = VALUES(freeze_risk_1h), freeze_risk_3h = VALUES(freeze_risk_3h),
        items_json = VALUES(items_json), probabilities_json = VALUES(probabilities_json),
        processed_at = CURRENT_TIMESTAMP
");

$saved = 0;
foreach ($predictions as $p) {
    $s = $p["status"] ?? [];
    $source = (($p["source"] ?? "live") === "test") ? "test" : "live";
    $deviceId = (string)($p["device_id"] ?? "");
    $readingId = intval($p["reading_id"] ?? 0);
    if ($deviceId === "" || $readingId <= 0) {
        continue;
    }
    $createdAt = (string)($p["at"] ?? date("Y-m-d H:i:s"));
    $ready = flag($p["ready"] ?? false);
    $level = (string)($p["level"] ?? "");
    $headline = mb_substr((string)($p["headline"] ?? ""), 0, 200);
    $odor = flag($s["odor"]["active"] ?? false);
    $odorMinutes = floatval($s["odor"]["minutes"] ?? 0);
    $doorOpen = flag($s["door"]["open"] ?? null);
    $doorSource = (string)($s["door"]["source"] ?? "ai");
    $windowOpen = flag($s["window"]["open"] ?? null);
    $windowSource = (string)($s["window"]["source"] ?? "ai");
    $lightOn = flag($s["light"]["on"] ?? null);
    $lux = isset($s["light"]["lux"]) ? floatval($s["light"]["lux"]) : null;
    $leak = flag($s["leak"]["active"] ?? false);
    $leakProbability = isset($s["leak"]["probability"]) ? floatval($s["leak"]["probability"]) : null;
    $pipeFrozen = flag($s["freeze"]["pipe_frozen"] ?? false);
    $risk1h = (string)($s["freeze"]["risk_1h"] ?? "없음");
    $risk3h = (string)($s["freeze"]["risk_3h"] ?? "없음");
    $items = json_encode($p["items"] ?? [], JSON_UNESCAPED_UNICODE);
    $probabilities = json_encode($p["probabilities"] ?? new stdClass(), JSON_UNESCAPED_UNICODE);

    $stmt->bind_param(
        "ssisiss" . "idisis" . "ididiss" . "ss",
        $source, $deviceId, $readingId, $createdAt, $ready, $level, $headline,
        $odor, $odorMinutes, $doorOpen, $doorSource, $windowOpen, $windowSource,
        $lightOn, $lux, $leak, $leakProbability, $pipeFrozen, $risk1h, $risk3h,
        $items, $probabilities
    );
    $stmt->execute();
    $saved++;
}

echo json_encode(["success" => true, "saved" => $saved]);

$stmt->close();
$conn->close();
