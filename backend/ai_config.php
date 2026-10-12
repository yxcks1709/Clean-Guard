<?php
/**
 * Shared secret for the AI service (ai/worker.py).
 *
 * getAIInput.php and saveAIStatus.php only answer requests that send this
 * key in the X-API-Key header, so random visitors can't read raw readings
 * or write fake predictions. Put the same value in ai/config.json.
 *
 * Override it without editing this file by setting the CLEANGUARD_AI_KEY
 * environment variable on the server.
 */

$AI_API_KEY = getenv("CLEANGUARD_AI_KEY") ?: "cleanguard-ai-change-me";

function cleanguard_require_ai_key(string $expected): void
{
    $sent = $_SERVER["HTTP_X_API_KEY"] ?? ($_GET["key"] ?? "");
    if ($expected === "" || !hash_equals($expected, (string)$sent)) {
        http_response_code(401);
        echo json_encode(["success" => false, "error" => "invalid API key"]);
        exit;
    }
}
