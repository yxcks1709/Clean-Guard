// Copy this file to secrets.h (same folder) and fill in your values.
// secrets.h is git-ignored so real Wi-Fi passwords are never committed.
#pragma once

#define WIFI_SSID "your-wifi-name"
#define WIFI_PASSWORD "your-wifi-password"

// backend/upload.php on the PC running XAMPP (use that PC's IPv4 address)
#define SERVER_URL "http://192.168.0.10/clean-guard/backend/upload.php"

// Must match devices.id in the database (Device Management in the dashboard)
#define DEVICE_ID "D1-001"
