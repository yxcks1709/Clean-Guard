"""Genera la grabación que reproduce la pestaña Test del dashboard (sin backend ni base de datos).

Pasa 5 baños simulados (mundo sintético del repositorio del modelo) por la IA real
(CleanGuardJudge = modelo restroom_unified + reglas de CleanGuard) y guarda, cada 15 s,
la lectura de los sensores y la decisión de la IA en frontend/src/data/test_replay.json.

    python build_test_replay.py            # vuelve a generar el archivo (≈ 1-2 min)

El dashboard reproduce esa grabación en bucle; cada vez que se recarga la página empieza
desde el principio, así que los eventos ocurren delante del público.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from cleanguard_ai import CleanGuardJudge                  # noqa: E402
from restroom_unified import world as W                     # noqa: E402
from restroom_unified.model import UnifiedModel             # noqa: E402

OUT = HERE.parent / "frontend" / "src" / "data" / "test_replay.json"
ADC_SCALE = 4095 / 1023
HISTORY_ROWS = 720            # 3 h de historial antes de empezar (la IA necesita 2 h)
LIVE_ROWS = 180               # 45 min de grabación (se repite en bucle)

# id, nombre, ubicación, dispositivo del mundo sintético, evento, minutos antes del evento, lux
DEVICES = [
    ("TEST-ODOR", "AI 테스트 악취", "AI테스트동 1층 화장실 101호 (악취)", 8, "occupancy_odor", 1, 250),
    ("TEST-WINDOW", "AI 테스트 창문", "AI테스트동 1층 화장실 102호 (창문)", 2, "window_open", 2, 250),
    ("TEST-LEAK", "AI 테스트 누수", "AI테스트동 1층 화장실 103호 (누수)", 8, "leak_active", 1, 250),
    ("TEST-FREEZE", "AI 테스트 동파", "AI테스트동 1층 화장실 104호 (동파)", 5, "cold", 3, 250),
    ("TEST-NORMAL", "AI 테스트 정상", "AI테스트동 1층 화장실 105호 (정상·소등)", 0, None, 0, 3),
]


def live_start(world, dev: int, event: str | None, lead_min: float) -> int:
    lead = int(lead_min * 4)
    first = max(HISTORY_ROWS, 1000) + lead
    if event is None:
        return first
    on = (world.temperature[dev] <= 0) if event == "cold" else world.labels[event][dev].astype(bool)
    starts = np.flatnonzero(on & ~np.r_[False, on[:-1]])
    return int(starts[starts >= first][0]) - lead


def decision_view(d: dict) -> dict:
    """Mismos campos que devuelve backend/getAIStatus.php."""
    s = d["status"]
    return {
        "ready": d["ready"], "level": d["level"], "headline": d["headline"], "items": d["items"],
        "odor": s["odor"]["active"], "odor_minutes": s["odor"]["minutes"],
        "door_open": s["door"]["open"], "door_source": s["door"]["source"],
        "window_open": s["window"]["open"], "window_source": s["window"]["source"],
        "light_on": s["light"]["on"], "lux": s["light"]["lux"],
        "leak": s["leak"]["active"], "leak_probability": s["leak"]["probability"],
        "pipe_frozen": s["freeze"]["pipe_frozen"],
        "freeze_risk_1h": s["freeze"]["risk_1h"], "freeze_risk_3h": s["freeze"]["risk_3h"],
    }


def main() -> None:
    print("generando mundo sintético y cargando el modelo...")
    world = W.generate(4, 12, 2, "shift")
    model = UnifiedModel.load()
    t0 = datetime(2026, 10, 14, 9, 0)          # hora ficticia; el dashboard la sustituye por la real
    devices = []
    for device_id, name, location, dev, event, lead, lux in DEVICES:
        live = live_start(world, dev, event, lead)
        judge = CleanGuardJudge(device_id, model)
        history, steps = [], []
        for n, k in enumerate(range(live - HISTORY_ROWS, live + LIVE_ROWS)):
            at = t0 + timedelta(seconds=15 * (n - HISTORY_ROWS))
            t = round(float(world.temperature[dev, k]), 1) + 0.0
            h = round(float(world.humidity[dev, k]), 1)
            air = int(round(float(world.mq135_adc[dev, k]) / ADC_SCALE))
            door, window = bool(world.labels["door_open"][dev, k]), bool(world.labels["window_open"][dev, k])
            if k < live - 240:                       # historial antiguo: solo llenar el historial (rápido)
                judge.prime(at, t, h, air)
            else:
                # la luz se "enciende" al empezar la grabación, para que el aviso de luz sin uso
                # aparezca a los 30 min de demo y no desde el primer segundo
                d = judge.add(at, t, h, air, float(lux) if k >= live else None, door, window)
                if k >= live:
                    steps.append({"t": t, "h": h, "a": air, "ai": decision_view(d)})
            if k < live:
                history.append((t, h, air))
        # historial para el gráfico: medias de 5 minutos (20 lecturas)
        buckets = [[round(float(np.mean([r[c] for r in history[i:i + 20]])), 2) for c in range(3)]
                   for i in range(0, len(history), 20)]
        devices.append({"id": device_id, "NAME": name, "location": location, "history": buckets, "steps": steps})
        heads = sorted({s["ai"]["headline"] for s in steps})
        print(f"  {device_id:12s} {len(steps)} pasos; titulares: {', '.join(heads[:6])}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"step_seconds": 15, "devices": devices}, ensure_ascii=False,
                              separators=(",", ":")), encoding="utf-8")
    print(f"guardado {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
