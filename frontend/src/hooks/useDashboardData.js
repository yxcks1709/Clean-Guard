import { useMemo } from "react";
import { useSensorData } from "./useSensorData";
import { getRowStatus } from "../utils/status";
import { parseLocation, groupByBuilding } from "../utils/location";

function levelOf(row) {
  return getRowStatus(row).level;
}

// Shared "main dashboard" data shape: poll sensor readings for the given
// table (live/test), group them by building, filter to the selected
// building (if any), and total up Normal/Warning/Danger counts.
//
// Extracted from what used to be duplicated inline in MobileDashboard.jsx;
// the new landscape/tablet dashboard needs the exact same shape, so both
// screens share one implementation instead of two copies of the same
// grouping/filtering/counting logic. Admin.jsx (desktop) keeps its own
// existing inline version untouched, since the desktop dashboard itself is
// explicitly not being modified this round.
export function useDashboardData(table, selectedBuilding) {
  const { data: sensorData, loading } = useSensorData(table);

  const buildings = useMemo(() => groupByBuilding(sensorData, levelOf), [sensorData]);

  const filteredData = useMemo(() => {
    if (!selectedBuilding) return sensorData;
    return sensorData.filter((row) => parseLocation(row.location).building === selectedBuilding);
  }, [sensorData, selectedBuilding]);

  const summary = useMemo(
    () =>
      filteredData.reduce(
        (acc, item) => {
          acc[levelOf(item)] += 1;
          return acc;
        },
        { total: filteredData.length, normal: 0, warning: 0, danger: 0 }
      ),
    [filteredData]
  );

  return { sensorData, buildings, filteredData, summary, loading };
}
