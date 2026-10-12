<?php

header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");

include "config.php";

/*
    Live and History both read the latest reading from `sensor_data` --
    there is no separate history table. History mode gets its full
    historical detail from getHistory.php instead, so any table value
    other than "test" simply falls back to `sensor_data` here.

    live
    test
*/

$table = $_GET["table"] ?? "live";

switch($table){

    case "test":
        $sensorTable = "sensor_data_test";
        break;

    default:
        $sensorTable = "sensor_data";
        break;

}

$source = $sensorTable === "sensor_data_test" ? "test" : "live";

$baseSql = "
SELECT
    d.id,
    d.NAME,
    d.location,
    d.STATUS,
    s.temperature,
    s.humidity,
    s.air_quality,
    s.created_at,
    '$source' AS source
    %s
FROM devices d
LEFT JOIN $sensorTable s
ON d.id = s.device_id
%s
WHERE s.id = (
    SELECT MAX(id)
    FROM $sensorTable
    WHERE device_id = d.id
)
ORDER BY d.location, d.id
";

// Latest AI decision per device (ai/worker.py), so cards can show it.
$aiColumns = ", a.level AS ai_level, a.headline AS ai_headline, a.created_at AS ai_at";
$aiJoin = "
LEFT JOIN ai_predictions a
ON a.id = (
    SELECT p.id FROM ai_predictions p
    WHERE p.source = '$source' AND p.device_id = d.id
    ORDER BY p.created_at DESC, p.reading_id DESC
    LIMIT 1
)";

try {
    $result = $conn->query(sprintf($baseSql, $aiColumns, $aiJoin));
} catch (mysqli_sql_exception $e) {
    // ai_predictions not created yet: readings only, as before.
    $result = $conn->query(sprintf($baseSql, "", ""));
}

$data = [];

while($row = $result->fetch_assoc()){

    $data[] = $row;

}

echo json_encode($data);

$conn->close();

?>
