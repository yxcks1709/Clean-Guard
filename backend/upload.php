<?php

header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");
header("Content-Type: application/json");

include "config.php";

/*
    Ingests one ESP8266 reading.

    Accepts JSON (current firmware) or form-encoded fields (older firmware):
      {
        "id": "D1-001",          // or device_id=...
        "temperature": 21.0,
        "humidity": 45.0,
        "airQuality": 512,       // MQ-135 raw ADC (ESP8266 A0, 0-1023)
        "lux": 120.5,            // optional, BH1750
        "door": 0,               // optional, reed switch: 1 = open
        "window": 1,             // optional, reed switch: 1 = open
        "table": "live"          // or "test"
      }
*/

$data = json_decode(file_get_contents("php://input"), true);
if (!is_array($data)) {
    $data = $_POST;
}

$deviceId = trim((string)($data["id"] ?? $data["device_id"] ?? ""));
$temp = $data["temperature"] ?? null;
$humidity = $data["humidity"] ?? null;
$air = (string)($data["airQuality"] ?? $data["air_quality"] ?? "0");

function optional_number($value)
{
    return ($value === null || $value === "") ? null : floatval($value);
}

function optional_flag($value)
{
    return ($value === null || $value === "") ? null : (intval($value) ? 1 : 0);
}

$lux = optional_number($data["lux"] ?? null);
$door = optional_flag($data["door"] ?? null);
$window = optional_flag($data["window"] ?? null);

if ($deviceId === "" || !is_numeric($temp) || !is_numeric($humidity)) {
    http_response_code(400);
    echo json_encode(["success" => false, "error" => "id, temperature and humidity are required"]);
    exit;
}

$temp = floatval($temp);
$humidity = floatval($humidity);

$sensorTable = (($data["table"] ?? "live") === "test") ? "sensor_data_test" : "sensor_data";

mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);

try {
    $stmt = $conn->prepare(
        "INSERT INTO $sensorTable (device_id, temperature, humidity, air_quality, lux, door_open, window_open)
         VALUES (?,?,?,?,?,?,?)"
    );
    $stmt->bind_param("sddsdii", $deviceId, $temp, $humidity, $air, $lux, $door, $window);
    $stmt->execute();
} catch (mysqli_sql_exception $e) {
    // Database not migrated yet (no lux/door_open/window_open columns):
    // store the basic reading so nothing is lost.
    $stmt = $conn->prepare(
        "INSERT INTO $sensorTable (device_id, temperature, humidity, air_quality) VALUES (?,?,?,?)"
    );
    $stmt->bind_param("sdds", $deviceId, $temp, $humidity, $air);
    $stmt->execute();
}

echo json_encode(["success" => true]);

$stmt->close();
$conn->close();
