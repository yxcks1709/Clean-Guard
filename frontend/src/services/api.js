// Centralized access point for the CleanGuard PHP backend.
//
// Every network call in the app goes through this module, so the base URL
// and each endpoint's request/response shape only need to live in one
// place. This also keeps components free of fetch() plumbing -- they call
// a named function and get back parsed data (or a { success, error }
// result for write operations).

// Reads from VITE_API_URL (see .env.example) so the backend origin isn't
// hardcoded in source; falls back to the project's current deployment so
// behavior is unchanged for anyone who hasn't set up a .env file.
import { getTestSensors, getTestAIStatus, getTestHistory, isTestDevice } from "./testReplay";

const API_BASE = import.meta.env.VITE_API_URL || "https://kbu1.dothome.co.kr";

// Both helpers swallow network/parse failures and return null instead of
// throwing. Every exported function below already has a safe fallback for
// a missing/malformed response (empty array, zeroed pagination, etc.), so
// a dropped connection degrades to "no data yet" in the UI instead of an
// unhandled promise rejection -- this is what lets the mobile screens show
// a proper empty/error state instead of a blank crash.
async function getJSON(path) {
  try {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

async function postJSON(path, body) {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) return { success: false, error: "네트워크 오류가 발생했습니다." };
    return await res.json();
  } catch {
    return { success: false, error: "네트워크 오류가 발생했습니다." };
  }
}

// ---------------------------------------------------------------------
// Sensor readings
// ---------------------------------------------------------------------

// Latest reading per device -- exactly one row per device. Used by Live
// ("live") and Test ("test") mode only. History mode intentionally does
// NOT read through here: it must never be collapsed to one row per
// device (see getSensorLog below).
//
// Test mode does not call the backend: it plays back a recording of the real
// AI on simulated restrooms (see services/testReplay.js).
export async function getSensors(mode = "live") {
  if (mode === "test") return getTestSensors();
  const data = await getJSON(`/getSensors.php?table=live`);
  return Array.isArray(data) ? data : [];
}

// Per-device historical trend, grouped into 5-minute buckets by the
// backend (getHistory.php reads directly from `sensor_data` -- there is
// no separate history table). Powers the HistoryChart component.
export async function getHistory(deviceId) {
  if (!deviceId) return [];
  if (isTestDevice(deviceId)) return getTestHistory(deviceId);
  const data = await getJSON(`/getHistory.php?device_id=${encodeURIComponent(deviceId)}`);
  return Array.isArray(data) ? data : [];
}

// The full History mode log: every individual measurement in
// `sensor_data`, newest first, paginated. Never grouped/collapsed.
export async function getSensorLog({ page = 1, pageSize = 50 } = {}) {
  const data = await getJSON(`/getSensorLog.php?page=${page}&pageSize=${pageSize}`);
  return {
    records: Array.isArray(data?.records) ? data.records : [],
    page: data?.page ?? page,
    pageSize: data?.pageSize ?? pageSize,
    total: data?.total ?? 0,
    totalPages: data?.totalPages ?? 0,
  };
}

// Latest AI decision for one device (odor, door/window, lights, leak,
// frozen pipes), written by the ai/worker.py service. Returns
// { available: false } when the service hasn't judged this device yet.
export async function getAIStatus(deviceId, table = "live") {
  if (!deviceId) return { available: false };
  if (table === "test" || isTestDevice(deviceId)) return getTestAIStatus(deviceId);
  const source = table === "test" ? "test" : "live";
  const data = await getJSON(
    `/getAIStatus.php?device_id=${encodeURIComponent(deviceId)}&table=${source}`
  );
  return data && typeof data === "object" ? data : { available: false };
}

// ---------------------------------------------------------------------
// Device registry (Device Management / CRUD)
// ---------------------------------------------------------------------

export async function getDevices() {
  const data = await getJSON("/getDevices.php");
  return Array.isArray(data) ? data : [];
}

export function addDevice(device) {
  return postJSON("/addDevice.php", device);
}

export function updateDevice(device) {
  return postJSON("/updateDevice.php", device);
}

export function deleteDevice(id) {
  return postJSON("/deleteDevice.php", { id });
}
