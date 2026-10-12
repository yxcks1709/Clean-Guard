import { useEffect, useState } from "react";
import { getAIStatus } from "../services/api";

const POLL_INTERVAL_MS = 5000;

// Polls the latest AI decision for one device. The AI service judges every
// 15 seconds, so polling faster than a few seconds would gain nothing.
// Returns null until the first response for *this* device arrives.
export function useAIStatus(deviceId, table = "live") {
  const key = `${table}:${deviceId}`;
  const [state, setState] = useState({ key: null, data: null });

  useEffect(() => {
    if (!deviceId) return;

    let cancelled = false;
    const fetchOne = () => {
      getAIStatus(deviceId, table).then((data) => {
        if (!cancelled) setState({ key, data });
      });
    };

    fetchOne();
    // The Test tab is a fast local playback, so refresh it more often.
    const interval = setInterval(fetchOne, table === "test" ? 1000 : POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [deviceId, table, key]);

  return state.key === key ? state.data : null;
}
