<?php

header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json");

include "config.php";
include "ai_config.php";

/*
    Raw readings for the AI service (ai/worker.py). Requires X-API-Key.

      getAIInput.php?after_id=123&limit=2000
            Readings with id > 123, oldest first (normal polling).

      getAIInput.php?since_minutes=600&limit=2000
            Readings from the last N minutes, oldest first (warm-up after
            the worker starts, so the model has history right away).

      &table=test   reads sensor_data_test (the dashboard's Test tab)
                    instead of sensor_data.
*/

cleanguard_require_ai_key($AI_API_KEY);

$limit = max(1, min(5000, intval($_GET["limit"] ?? 2000)));
$sensorTable = (($_GET["table"] ?? "live") === "test") ? "sensor_data_test" : "sensor_data";

// Highest id right now, so the worker can skip old rows when the last
// `since_minutes` window is empty.
$maxId = intval($conn->query("SELECT COALESCE(MAX(id), 0) AS m FROM $sensorTable")->fetch_assoc()["m"]);

$columns = "id, device_id, temperature, humidity, air_quality, lux, door_open, window_open, created_at";

if (isset($_GET["since_minutes"])) {
    $minutes = max(1, intval($_GET["since_minutes"]));
    $stmt = $conn->prepare(
        "SELECT $columns FROM $sensorTable
         WHERE created_at >= NOW() - INTERVAL ? MINUTE
         ORDER BY id ASC LIMIT ?"
    );
    $stmt->bind_param("ii", $minutes, $limit);
} else {
    $afterId = max(0, intval($_GET["after_id"] ?? 0));
    $stmt = $conn->prepare(
        "SELECT $columns FROM $sensorTable
         WHERE id > ?
         ORDER BY id ASC LIMIT ?"
    );
    $stmt->bind_param("ii", $afterId, $limit);
}

$stmt->execute();
$result = $stmt->get_result();

$rows = [];
while ($row = $result->fetch_assoc()) {
    $rows[] = $row;
}

echo json_encode(["success" => true, "rows" => $rows, "max_id" => $maxId]);

$stmt->close();
$conn->close();
