<?php
/**
 * Database Connection Configuration
 */

$host     = "localhost";
$dbname   = "cleanguard";
$username = "root";
$password = "";

// MySQLi DB 연결
$conn = new mysqli($host, $username, $password, $dbname);

if ($conn->connect_error) {
    die("Database Connection Failed: " . $conn->connect_error);
}

$conn->set_charset("utf8");