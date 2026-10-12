import { getRowStatus, getOnlineStatus } from "../utils/status";
import { parseLocation } from "../utils/location";

export default function BathroomCard({ data, isSelected, onSelect }) {
    const status = getRowStatus(data);
    const online = getOnlineStatus(data.created_at);
    const { room, label } = parseLocation(data.location);

    return (
        <div
            onClick={() => onSelect(data)}
            className={`cursor-pointer bg-white border rounded shadow-xs p-3 text-xs transition-colors duration-75 ${status.bg} border-slate-300 ${
                isSelected ? "ring-2 ring-inset ring-slate-800 font-semibold" : ""
            }`}
        >
            <div className="flex justify-between items-start mb-1 gap-2">
                <span className="font-black text-sm truncate">
                    {room ? `${room}호` : label}
                </span>
                <span className={`${online.color} text-[10px] font-bold shrink-0`}>{online.label}</span>
            </div>

            <div className="text-[10px] text-slate-500 font-bold mb-2 truncate">{data.location}</div>

            <div className="grid grid-cols-3 gap-1 mb-2">
                <div className="bg-white/70 border border-slate-200 rounded p-1 text-center">
                    <div className="text-[9px] text-slate-500 font-bold">온도</div>
                    <div className="font-black">{data.temperature}°C</div>
                </div>
                <div className="bg-white/70 border border-slate-200 rounded p-1 text-center">
                    <div className="text-[9px] text-slate-500 font-bold">습도</div>
                    <div className="font-black">{data.humidity}%</div>
                </div>
                <div className="bg-white/70 border border-slate-200 rounded p-1 text-center">
                    <div className="text-[9px] text-slate-500 font-bold">공기질</div>
                    <div className="font-black truncate">{data.air_quality}</div>
                </div>
            </div>

            {/* Device Status (administrative: 정상/점검중/고장) alongside the
                status badge -- the AI's verdict (🤖) when the AI service has
                judged this device recently, otherwise the threshold rules.
                Full AI detail is in AIStatusCard on the detail panel. */}
            <div className="flex items-center justify-between gap-2">
                <span className="inline-flex items-center rounded border border-slate-200 bg-slate-50 text-slate-600 font-bold text-[10px] px-1.5 py-0.5">
                    {data.STATUS ?? "-"}
                </span>
                <span className={`${status.text} text-[10px] font-bold text-right`}>{status.label}</span>
            </div>

            <div className="text-[9px] text-slate-400 mt-1">{data.created_at}</div>
        </div>
    );
}
