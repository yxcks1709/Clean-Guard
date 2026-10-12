import { getRowStatus, getOnlineStatus } from "../utils/status";
import { parseLocation } from "../utils/location";

// Touch-optimized full-width card for a single bathroom's latest reading,
// used by the mobile main screen's scrollable list. Reuses the exact same
// status/location logic the desktop grid uses -- only the layout differs.
export default function MobileBathroomCard({ row, onTap }) {
  const status = getRowStatus(row);
  const online = getOnlineStatus(row.created_at);
  const { building, room, label } = parseLocation(row.location);

  return (
    <button
      type="button"
      onClick={() => onTap(row)}
      className={`w-full text-left bg-white rounded-2xl border ${status.border} shadow-sm active:scale-[0.98] transition-transform p-4 mb-3`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="font-black text-base text-slate-900 truncate">
            {room ? `${room}호` : label}
          </div>
          <div className="text-xs text-slate-500 font-bold mt-0.5 truncate">
            {row.id} · {building}
          </div>
        </div>
        <span className={`${online.color} text-[11px] font-bold shrink-0`}>
          {online.label}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 mt-3">
        <div className="bg-slate-50 rounded-lg p-2 text-center">
          <div className="text-[9px] text-slate-500 font-bold">온도</div>
          <div className="font-black text-sm">{row.temperature}°C</div>
        </div>
        <div className="bg-slate-50 rounded-lg p-2 text-center">
          <div className="text-[9px] text-slate-500 font-bold">습도</div>
          <div className="font-black text-sm">{row.humidity}%</div>
        </div>
        <div className="bg-slate-50 rounded-lg p-2 text-center">
          <div className="text-[9px] text-slate-500 font-bold">공기질</div>
          <div className="font-black text-sm truncate">{row.air_quality}</div>
        </div>
      </div>

      <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100">
        <span className={`${status.text} text-xs font-bold`}>{status.label}</span>
        <span className="text-[10px] text-slate-400 truncate ml-2">{row.created_at}</span>
      </div>
    </button>
  );
}
