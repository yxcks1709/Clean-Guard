import { useParams, useLocation, useNavigate } from "react-router-dom";
import { parseLocation } from "../utils/location";
import { getRowStatus, getOnlineStatus } from "../utils/status";
import { useBathroomDetail } from "../hooks/useBathroomDetail";
import HistoryChart from "../components/HistoryChart";
import AIStatusCard from "../components/AIStatusCard";

function DetailHeader({ onBack, title, subtitle }) {
  return (
    <div className="sticky top-0 z-40 bg-slate-900 text-white px-4 py-3 shadow-sm flex items-center gap-3">
      <button
        type="button"
        onClick={onBack}
        aria-label="뒤로 가기"
        className="p-2 -ml-2 rounded-lg bg-slate-800 border border-slate-700 text-lg leading-none active:scale-95 transition-transform shrink-0"
      >
        ←
      </button>
      <div className="min-w-0 flex-1">
        <div className="font-black text-base text-emerald-400 truncate">{title}</div>
        {subtitle && <div className="text-[11px] text-slate-400 truncate">{subtitle}</div>}
      </div>
    </div>
  );
}

// Full-screen mobile detail page, reached from MobileDashboard by tapping
// a bathroom card. This deliberately does NOT reuse SidePanel.jsx -- the
// brief calls for full-screen mobile pages, not a desktop side panel --
// but it does reuse HistoryChart directly, the same status/location
// utilities every other screen uses, and the same shared AIStatusCard the
// desktop SidePanel uses (latest AI decision from the ai/worker.py service).
export default function MobileBathroomDetail() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const searchParams = new URLSearchParams(location.search);
  const mode = searchParams.get("mode") || "live";

  const { row, loading } = useBathroomDetail({
    id,
    mode,
    initialRow: location.state?.row,
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center">
        <div className="text-sm font-bold text-slate-400">불러오는 중...</div>
      </div>
    );
  }

  if (!row) {
    return (
      <div className="min-h-screen bg-slate-100 flex flex-col">
        <DetailHeader onBack={() => navigate(-1)} title="화장실을 찾을 수 없습니다" />
        <div className="flex-1 flex items-center justify-center p-6 text-center text-sm text-slate-400 font-bold">
          이 장치의 데이터를 더 이상 사용할 수 없습니다.
        </div>
      </div>
    );
  }

  const status = getRowStatus(row);
  const online = getOnlineStatus(row.created_at);
  const { building, floor, room, label } = parseLocation(row.location);

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col font-mono">
      <DetailHeader
        onBack={() => navigate(-1)}
        title={room ? `${room}호` : label}
        subtitle={row.location}
      />

      <main
        className="flex-1 overflow-y-auto p-4 space-y-4"
        style={{ paddingBottom: "max(2rem, env(safe-area-inset-bottom))" }}
      >
        <div className={`rounded-2xl border ${status.border} bg-white shadow-sm p-4 flex items-center justify-between`}>
          <span className={`${status.text} font-black text-sm`}>{status.label}</span>
          <span className={`${online.color} text-xs font-bold`}>{online.label}</span>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-3">
            <div className="text-[10px] text-slate-500 font-bold">Device ID</div>
            <div className="font-black text-sm truncate">{row.id}</div>
          </div>
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-3">
            <div className="text-[10px] text-slate-500 font-bold">건물 / 층</div>
            <div className="font-black text-sm truncate">
              {building} {floor ? `${floor}층` : ""}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4">
            <div className="text-[10px] text-slate-500 font-bold">현재 온도</div>
            <div className="font-black text-2xl mt-1">{row.temperature}°C</div>
          </div>
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4">
            <div className="text-[10px] text-slate-500 font-bold">현재 습도</div>
            <div className="font-black text-2xl mt-1">{row.humidity}%</div>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4">
          <div className="text-[10px] text-slate-500 font-bold">공기질</div>
          <div className="font-black text-lg mt-1">{row.air_quality}</div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4">
          <div className="text-[10px] text-slate-500 font-bold mb-2">기록 추이</div>
          <HistoryChart deviceId={row.id} />
        </div>

        <AIStatusCard deviceId={row.id} table={mode === "test" ? "test" : "live"} />

        <div className="text-[10px] text-slate-400 text-center pb-2">
          마지막 업데이트: {row.created_at}
        </div>
      </main>
    </div>
  );
}
