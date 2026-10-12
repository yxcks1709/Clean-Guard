import { parseLocation } from "../utils/location";
import HistoryChart from "./HistoryChart";
import AIStatusCard from "./AIStatusCard";

export default function SidePanel({
    selectedRow,
    setSelectedRow
}) {
    const { building, floor, room, label } = parseLocation(selectedRow.location);

    return (
        <aside className="fixed inset-0 z-30 w-full md:static md:inset-auto md:z-10 md:w-80 bg-slate-50 border-l border-slate-300 flex flex-col shadow-lg animate-in slide-in-from-right duration-100">
            <div className="bg-slate-200 p-3 border-b border-slate-300 flex justify-between items-center">
                <span className="font-black text-xs text-slate-700">
                    상세 정보
                </span>

                <button
                    onClick={() => setSelectedRow(null)}
                    className="text-slate-500 hover:text-slate-800 text-xs font-bold px-3 py-1.5 md:px-1.5 md:py-0.5 rounded border border-slate-300 bg-white shadow-xs"
                >
                    닫기
                </button>
            </div>

            <div className="p-4 flex-1 space-y-4 text-xs overflow-y-auto">

                <div>
                    <label className="text-[10px] text-slate-500 font-bold">
                        위치
                    </label>

                    <div className="text-sm font-black">
                        {selectedRow.location}
                    </div>
                </div>

                {/* IDENTIFICATION */}
                <div className="grid grid-cols-2 gap-2">

                    <div className="bg-white p-2 border rounded">
                        <label className="text-[10px] text-slate-500 font-bold">Device ID</label>
                        <div className="text-sm font-black truncate">{selectedRow.id}</div>
                    </div>

                    <div className="bg-white p-2 border rounded">
                        <label className="text-[10px] text-slate-500 font-bold">건물</label>
                        <div className="text-sm font-black truncate">{building}</div>
                    </div>

                    <div className="bg-white p-2 border rounded">
                        <label className="text-[10px] text-slate-500 font-bold">층</label>
                        <div className="text-sm font-black">{floor ? `${floor}층` : "-"}</div>
                    </div>

                    <div className="bg-white p-2 border rounded">
                        <label className="text-[10px] text-slate-500 font-bold">화장실 번호</label>
                        <div className="text-sm font-black truncate">{room ? `${room}호` : label}</div>
                    </div>

                </div>

                {/* IMPLEMENTED SENSOR DATA */}
                <div className="grid grid-cols-2 gap-2">

                    <div className="bg-white p-2 border rounded">
                        <label>현재 온도</label>

                        <div className="text-lg font-black">
                            {selectedRow.temperature}°C
                        </div>
                    </div>

                    <div className="bg-white p-2 border rounded">
                        <label>현재 습도</label>

                        <div className="text-lg font-black">
                            {selectedRow.humidity}%
                        </div>
                    </div>

                </div>

                <div className="bg-white p-2 border rounded">
                    <label>공기질</label>

                    <div className="font-bold">
                        {selectedRow.air_quality}
                    </div>
                </div>

                <div className="bg-white p-2 border rounded">
                    <label className="text-[10px] text-slate-500 font-bold">장치 상태</label>

                    <div className="font-bold">
                        {selectedRow.STATUS ?? "-"}
                    </div>
                </div>

                {/* AI ANALYSIS -- latest decision of the AI service
                    (odor, door/window, lights, leak, frozen pipes). */}
                <AIStatusCard deviceId={selectedRow.id} table={selectedRow.source ?? "live"} />

                {/* HISTORICAL TREND CHART */}
                <div>
                    <label className="text-[10px] text-slate-500 font-bold block mb-1.5">
                        기록 추이
                    </label>

                    <HistoryChart deviceId={selectedRow.id} />
                </div>

                <div className="bg-slate-900 text-slate-300 rounded p-3 font-mono text-[11px]">

                    <div>
                        [{selectedRow.created_at}] Sensor Data Received
                    </div>

                    <div>
                        Device : {selectedRow.id}
                    </div>

                    <div>
                        Status : {selectedRow.STATUS}
                    </div>
                </div>
            </div>
        </aside>
    );
}
