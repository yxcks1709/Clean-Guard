import { useState, useEffect, useMemo } from 'react';
import Header from "../components/Header";
import SummaryBar from '../components/SummaryBar';
import BuildingSelector from "../components/BuildingSelector";
import BathroomGrid from "../components/BathroomGrid";
import SidePanel from "../components/SidePanel";
import HistoryPanel from "../components/HistoryPanel";
import { getRowStatus } from "../utils/status";
import { parseLocation, groupByBuilding } from "../utils/location";
import { useSensorData } from "../hooks/useSensorData";

export default function CleanGuardDashboard() {
    const [selectedRow, setSelectedRow] = useState(null);
    const [selectedBuilding, setSelectedBuilding] = useState(null);
    const [currentTime, setCurrentTime] = useState(new Date().toLocaleTimeString());
    const [table, setTable] = useState("live");

    const isHistory = table === "history";

    const { data: sensorData } = useSensorData(table);

    useEffect(() => {
        const timer = setInterval(() => {
            setCurrentTime(new Date().toLocaleTimeString());
        }, 1000);
        return () => clearInterval(timer);
    }, []);

    // Buildings are derived dynamically from whatever `location` values the
    // API currently returns, so any number of buildings/bathrooms is
    // supported without code changes. Not used in History mode (see below).
    const buildings = useMemo(
        () =>
            groupByBuilding(sensorData, (row) =>
                getRowStatus(row).level
            ),
        [sensorData]
    );

    // Selecting a building filters the bathroom grid below it.
    const filteredData = useMemo(() => {
        if (!selectedBuilding) return sensorData;
        return sensorData.filter(
            (row) => parseLocation(row.location).building === selectedBuilding
        );
    }, [sensorData, selectedBuilding]);

    // Calculate summary counts dynamically, scoped to the current building
    // filter (or the whole facility when no building is selected).
    const summary = filteredData.reduce(
        (acc, item) => {

            const { level } = getRowStatus(item);

            acc[level]++;

            return acc;

        },
        {
            total: filteredData.length,
            normal: 0,
            warning: 0,
            danger: 0
        }
    );

    function handleSelectBuilding(name) {
        setSelectedBuilding((prev) => (prev === name ? null : name));
        setSelectedRow(null);
    }

    // Switching modes (live / test / history) immediately swaps the
    // dashboard's content -- no page refresh. Any previously selected
    // bathroom/reading is cleared since it belongs to the mode being left.
    function handleTableChange(nextTable) {
        setTable(nextTable);
        setSelectedRow(null);
    }

    return (
        <div className="min-h-screen bg-slate-100 text-slate-900 font-mono antialiased flex flex-col select-none">
            {/* HEADER */}
            <Header
                currentTime={currentTime}
                table={table}
                setTable={handleTableChange}
            />

            {isHistory ? (
                // HISTORY MODE -- a chronological log of every measurement in
                // sensor_data (paginated, newest first, no auto-refresh),
                // not a "latest reading" view. See HistoryPanel/useHistoryLog.
                <HistoryPanel
                    selectedRow={selectedRow}
                    setSelectedRow={setSelectedRow}
                />
            ) : (
                <>
                    {/* TOP SUMMARY BAR */}
                    <SummaryBar summary={summary} />
                    {/* BUILDING SELECTION */}
                    <BuildingSelector
                        buildings={buildings}
                        selectedBuilding={selectedBuilding}
                        onSelect={handleSelectBuilding}
                        totalCount={sensorData.length}
                    />
                    {/* MAIN CONTENT AREA */}
                    <main className="flex-1 flex overflow-hidden relative">
                        {/* BATHROOM GRID SECTION */}
                        <section className="flex-1 p-4 overflow-auto">
                            <BathroomGrid
                                bathrooms={filteredData}
                                selectedRow={selectedRow}
                                setSelectedRow={setSelectedRow}
                            />
                        </section>
                        {/* SIDE DETAIL PANEL */}
                        {
                            selectedRow &&
                            <SidePanel
                                selectedRow={selectedRow}
                                setSelectedRow={setSelectedRow}
                            />
                        }
                    </main>
                </>
            )}
        </div>
    );
}
