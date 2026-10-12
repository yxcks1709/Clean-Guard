"""Simulador de sensores CleanGuard para probar y demostrar la IA sin hardware.

Usa el mundo sintético del repositorio del modelo (restroom_unified/world.py). Para cada baño
simulado elige un tramo donde ocurre un evento, mete unas horas de historial directamente en
MySQL (así la IA decide desde el primer minuto) y luego envía una lectura cada 15 s a
upload.php, igual que el firmware del ESP8266. Los eventos empiezan pocos minutos después.

    python simulate.py --demo                     # pestaña Test: 5 baños, uno por evento
    python simulate.py --scenario fuga            # un solo baño en la tabla live (sensor_data)
    python simulate.py --scenario ventana --no-contacts --table test

Escenarios: olor, ventana, fuga, congelamiento, normal.
Arranca el simulador antes que worker.py (o reinícialo después) para que lea el historial.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from restroom_unified import world as W        # noqa: E402

ADC_SCALE = 4095 / 1023
HISTORY_MIN_ROWS = 1000          # los eventos se buscan después de esta fila del mundo sintético


@dataclass
class Scenario:
    world_device: int            # dispositivo del mundo sintético (seed 4, 12 dispositivos, perfil "shift")
    event: str | None            # etiqueta cuyo inicio buscamos ("cold" = temperatura <= 0 °C)
    lead_minutes: float          # minutos en vivo antes de que empiece el evento
    lux: float                   # luz simulada (BH1750)


SCENARIOS = {
    "olor": Scenario(8, "occupancy_odor", 1, 250),
    "ventana": Scenario(2, "window_open", 2, 250),
    "fuga": Scenario(8, "leak_active", 1, 250),            # la IA la confirma ~5 min después
    "congelamiento": Scenario(5, "cold", 3, 250),
    "normal": Scenario(0, None, 0, 3),                      # luz apagada
}

# Baños de la pestaña Test (--demo): id, nombre, ubicación, escenario
DEMO_DEVICES = [
    ("TEST-ODOR", "AI 테스트 악취", "AI테스트동 1층 화장실 101호 (악취)", "olor"),
    ("TEST-WINDOW", "AI 테스트 창문", "AI테스트동 1층 화장실 102호 (창문)", "ventana"),
    ("TEST-LEAK", "AI 테스트 누수", "AI테스트동 1층 화장실 103호 (누수)", "fuga"),
    ("TEST-FREEZE", "AI 테스트 동파", "AI테스트동 1층 화장실 104호 (동파)", "congelamiento"),
    ("TEST-NORMAL", "AI 테스트 정상", "AI테스트동 1층 화장실 105호 (정상·소등)", "normal"),
]


def event_start(world, s: Scenario, history: int) -> int:
    """Primera fila en vivo: `lead` minutos antes de que empiece el evento."""
    lead = int(s.lead_minutes * 4)
    first = max(history, HISTORY_MIN_ROWS) + lead
    if s.event is None:
        return first
    on = (world.temperature[s.world_device] <= 0) if s.event == "cold" else \
        world.labels[s.event][s.world_device].astype(bool)
    starts = np.flatnonzero(on & ~np.r_[False, on[:-1]])
    starts = starts[starts >= first]
    if not len(starts):
        raise SystemExit(f"no hay evento {s.event} en el dispositivo {s.world_device}")
    return int(starts[0]) - lead


class SimDevice:
    def __init__(self, world, device_id: str, scenario: str, history: int, args):
        self.world, self.device_id, self.name = world, device_id, scenario
        self.s = SCENARIOS[scenario]
        self.i = self.s.world_device
        self.contacts = not args.no_contacts
        self.lux = None if args.no_light else self.s.lux
        self.live = event_start(world, self.s, history)
        self.k = self.live

    def reading(self, k: int) -> dict:
        w, i = self.world, self.i
        out = {"temperature": round(float(w.temperature[i, k]), 1) + 0.0,     # + 0.0: sin "-0.0"
               "humidity": round(float(w.humidity[i, k]), 1),
               "airQuality": int(round(float(w.mq135_adc[i, k]) / ADC_SCALE))}
        if self.lux is not None:
            out["lux"] = self.lux
        if self.contacts:
            out["door"] = int(w.labels["door_open"][i, k])
            out["window"] = int(w.labels["window_open"][i, k])
        return out

    def truth(self, k: int) -> str:
        names = [n for n in W.LABELS if self.world.labels[n][self.i, k]]
        return ", ".join(names) or "-"


def connect(args):
    import pymysql
    return pymysql.connect(host=args.db_host, user=args.db_user, password=args.db_password,
                           database=args.db_name, charset="utf8mb4", autocommit=True)


def register(conn, devices: list[tuple[str, str, str]]) -> None:
    with conn.cursor() as cur:
        cur.executemany("INSERT INTO devices (id, NAME, location, STATUS) VALUES (%s,%s,%s,'정상') "
                        "ON DUPLICATE KEY UPDATE NAME = VALUES(NAME), location = VALUES(location)", devices)


def backfill(conn, table: str, dev: SimDevice, history: int) -> None:
    now = datetime.now().replace(microsecond=0)
    rows = []
    for j, k in enumerate(range(dev.live - history, dev.live)):
        r = dev.reading(k)
        rows.append((dev.device_id, r["temperature"], r["humidity"], str(r["airQuality"]), r.get("lux"),
                     r.get("door"), r.get("window"), now - timedelta(seconds=15 * (history - j))))
    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM {table} WHERE device_id = %s", (dev.device_id,))
        cur.execute("DELETE FROM ai_predictions WHERE source = %s AND device_id = %s",
                    ("test" if table == "sensor_data_test" else "live", dev.device_id))
        cur.executemany(f"INSERT INTO {table} (device_id, temperature, humidity, air_quality, lux, door_open, "
                        "window_open, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", rows)
    print(f"  {dev.device_id:12s} {dev.name:14s} historial {history * 15 / 3600:.1f} h, "
          f"evento en ~{dev.s.lead_minutes:.0f} min")


def post(api: str, body: dict) -> str:
    req = urllib.request.Request(f"{api.rstrip('/')}/upload.php", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as res:
        return res.read().decode().strip()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", action="store_true", help="5 baños de prueba en la pestaña Test")
    ap.add_argument("--scenario", choices=SCENARIOS, default="fuga", help="sin --demo: un solo baño")
    ap.add_argument("--device-id", default="D1 Mini 302", help="sin --demo: debe existir en devices")
    ap.add_argument("--table", choices=("live", "test"), default=None,
                    help="tabla destino (por defecto: test con --demo, live sin --demo)")
    ap.add_argument("--api", default="http://localhost:8080", help="URL de la carpeta backend")
    ap.add_argument("--history-hours", type=float, default=3)
    ap.add_argument("--no-light", action="store_true", help="simular que no hay BH1750")
    ap.add_argument("--no-contacts", action="store_true", help="simular que no hay sensores de puerta/ventana")
    ap.add_argument("--db-host", default="localhost")
    ap.add_argument("--db-user", default="root")
    ap.add_argument("--db-password", default="")
    ap.add_argument("--db-name", default="cleanguard")
    args = ap.parse_args()

    table = args.table or ("test" if args.demo else "live")
    db_table = "sensor_data_test" if table == "test" else "sensor_data"
    print("generando datos sintéticos...")
    world = W.generate(4, 12, 2, "shift")
    history = int(args.history_hours * 240)
    if args.demo:
        devices = [SimDevice(world, did, sc, history, args) for did, _, _, sc in DEMO_DEVICES]
    else:
        devices = [SimDevice(world, args.device_id, args.scenario, history, args)]

    conn = connect(args)
    if args.demo:
        register(conn, [(did, name, loc) for did, name, loc, _ in DEMO_DEVICES])
    print(f"cargando historial en {db_table}:")
    for dev in devices:
        backfill(conn, db_table, dev, history)
    conn.close()
    print("enviando una lectura cada 15 s por baño (Ctrl+C para parar)\n")

    while True:
        started = time.time()
        for dev in devices:
            if dev.k >= world.steps:          # se acabó el tramo sintético: volver a empezar
                dev.k = dev.live
            body = {"id": dev.device_id, **dev.reading(dev.k), "table": table}
            try:
                answer = post(args.api, body)
            except Exception as exc:          # backend apagado: avisar y seguir
                answer = f"ERROR {exc}"
            ok = "ok" if '"success":true' in answer else answer
            print(f"{datetime.now():%H:%M:%S} {dev.device_id:12s} T={body['temperature']:5.1f} "
                  f"H={body['humidity']:5.1f} MQ135={body['airQuality']:4d} {ok:3s} | real: {dev.truth(dev.k)}")
            dev.k += 1
        time.sleep(max(0.0, 15 - (time.time() - started)))


if __name__ == "__main__":
    main()
