import { useAIStatus } from "../hooks/useAIStatus";

// AI Analysis card: the latest decision of the AI service (ai/worker.py)
// for one device -- odor, door, window, lights, leak and frozen pipes --
// read through getAIStatus.php. The dashboard never runs the model itself.

const LEVEL_STYLE = {
  긴급: "bg-red-50 border-red-300 text-red-700",
  주의: "bg-amber-50 border-amber-300 text-amber-700",
  정보: "bg-sky-50 border-sky-300 text-sky-700",
  평상시: "bg-emerald-50 border-emerald-300 text-emerald-700",
};
const DEFAULT_STYLE = "bg-slate-50 border-slate-300 text-slate-600";

const TONE = {
  bad: "text-red-700",
  warn: "text-amber-700",
  ok: "text-emerald-700",
  none: "text-slate-400",
};

function sourceTag(source) {
  return source === "sensor" ? "센서" : "AI";
}

function rows(s) {
  const freezeLevel = s.pipe_frozen ? "동결 의심" : s.freeze_risk_1h !== "없음" ? `1시간 내 ${s.freeze_risk_1h}`
    : s.freeze_risk_3h !== "없음" ? `3시간 내 ${s.freeze_risk_3h}` : "없음";
  const freezeTone = s.pipe_frozen || s.freeze_risk_1h === "경보" ? "bad"
    : freezeLevel !== "없음" ? "warn" : "ok";

  return [
    {
      label: "악취",
      value: !s.ready ? "준비 중" : s.odor ? `감지 (${Math.round(s.odor_minutes ?? 0)}분)` : "없음",
      tone: !s.ready ? "none" : s.odor ? "warn" : "ok",
    },
    {
      label: "문",
      value: s.door_open === null ? "알 수 없음" : `${s.door_open ? "열림" : "닫힘"} · ${sourceTag(s.door_source)}`,
      tone: s.door_open === null ? "none" : s.door_open ? "warn" : "ok",
    },
    {
      label: "창문",
      value: s.window_open === null ? "알 수 없음" : `${s.window_open ? "열림" : "닫힘"} · ${sourceTag(s.window_source)}`,
      tone: s.window_open === null ? "none" : s.window_open ? "warn" : "ok",
    },
    {
      label: "조명",
      value: s.light_on === null ? "센서 없음" : `${s.light_on ? "켜짐" : "꺼짐"} · ${Math.round(s.lux ?? 0)} lx`,
      tone: s.light_on === null ? "none" : s.light_on ? "warn" : "ok",
    },
    {
      label: "누수",
      value: !s.ready ? "준비 중" : s.leak ? "의심" : "없음",
      tone: !s.ready ? "none" : s.leak ? "bad" : "ok",
    },
    {
      label: "배관 동파",
      value: freezeLevel,
      tone: freezeTone,
    },
  ];
}

export default function AIStatusCard({ deviceId, table = "live" }) {
  const status = useAIStatus(deviceId, table);

  return (
    <div className="bg-white border rounded p-3">
      <div className="text-[10px] text-slate-500 font-bold uppercase mb-2">
        AI Analysis{table === "test" ? " · TEST" : ""}
      </div>

      {!status ? (
        <div className="text-[11px] text-slate-400 font-bold text-center py-3">불러오는 중...</div>
      ) : status.available && status.level === undefined ? (
        <div className="text-[11px] text-amber-700 font-bold text-center py-3 border border-dashed border-amber-300 rounded bg-amber-50">
          서버의 getAIStatus.php가 이전 버전입니다. 새 backend 파일을 업로드하세요.
        </div>
      ) : !status.available ? (
        <div className="text-[11px] text-slate-400 font-bold text-center py-3 border border-dashed border-slate-300 rounded bg-slate-50">
          AI 판정 기록이 없습니다. AI 서비스(ai/worker.py)가 실행 중인지 확인하세요.
        </div>
      ) : (
        <>
          <div className={`border rounded px-2 py-1.5 mb-2 text-xs font-black ${LEVEL_STYLE[status.level] ?? DEFAULT_STYLE}`}>
            {status.level} · {status.headline}
          </div>

          <div className="grid grid-cols-2 gap-1.5 mb-2">
            {rows(status).map((r) => (
              <div key={r.label} className="border border-slate-200 rounded px-2 py-1">
                <div className="text-[9px] text-slate-500 font-bold">{r.label}</div>
                <div className={`text-[11px] font-black ${TONE[r.tone]}`}>{r.value}</div>
              </div>
            ))}
          </div>

          {status.items?.length > 1 && (
            <ul className="space-y-0.5 mb-2">
              {status.items.slice(1).map((item) => (
                <li key={item.code} className="text-[10px] text-slate-600">
                  <span className="font-bold">[{item.level}]</span> {item.message}
                </li>
              ))}
            </ul>
          )}

          <div className="text-[9px] text-slate-400">판정 시각: {status.created_at}</div>
        </>
      )}
    </div>
  );
}
