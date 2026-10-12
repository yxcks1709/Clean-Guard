"""Servicio de IA de CleanGuard.

Lee las lecturas nuevas del backend PHP (getAIInput.php), pasa cada una por el CleanGuardJudge
de su dispositivo y guarda la decisión (saveAIStatus.php). El dashboard la lee con getAIStatus.php.

    python worker.py                      # usa config.json junto a este archivo
    python worker.py --config otra.json
    python worker.py --once               # procesa lo pendiente y termina (útil para probar)

Al arrancar vuelve a leer las últimas `warmup_hours` horas para que el modelo no tenga que
esperar 2 h desde cero.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from cleanguard_ai import CleanGuardJudge, Settings          # noqa: E402
from restroom_unified.model import UnifiedModel               # noqa: E402

log = logging.getLogger("cleanguard-ai")

DEFAULTS = {
    "api_base": "http://localhost/clean-guard/backend",
    "api_key": "",
    "poll_seconds": 5,
    "warmup_hours": 10,
    "warmup_full_rows": 240,
    "tables": ["live", "test"],        # live = sensor_data, test = sensor_data_test (pestaña Test)           # última hora (240 x 15 s) evaluada completa al arrancar
    "batch_limit": 2000,
    "post_chunk": 200,
    "settings": {},
}


class Api:
    def __init__(self, base: str, key: str):
        self.base = base.rstrip("/")
        self.key = key

    def _request(self, path: str, body: dict | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(f"{self.base}/{path}", data=data, method="POST" if data else "GET",
                                     headers={"X-API-Key": self.key, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as res:
            payload = json.loads(res.read().decode("utf-8"))
        if isinstance(payload, dict) and payload.get("success") is False:
            raise RuntimeError(payload.get("error", "error del backend"))
        return payload

    def readings(self, **params) -> list[dict]:
        return self.readings_page(**params)["rows"]

    def readings_page(self, **params) -> dict:
        return self._request("getAIInput.php?" + urllib.parse.urlencode(params))

    def save(self, predictions: list[dict]) -> int:
        return int(self._request("saveAIStatus.php", {"predictions": predictions}).get("saved", 0))


def _flag(value) -> bool | None:
    if value is None or value == "":
        return None
    return bool(int(value))


def _num(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


class Worker:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.api = Api(cfg["api_base"], cfg["api_key"])
        self.settings = Settings.from_dict(cfg.get("settings"))
        log.info("cargando modelo...")
        self.model = UnifiedModel.load()
        self.judges: dict[tuple[str, str], CleanGuardJudge] = {}
        self.last_id = {table: 0 for table in cfg["tables"]}

    def judge(self, table: str, device_id: str) -> CleanGuardJudge:
        key = (table, device_id)
        if key not in self.judges:
            self.judges[key] = CleanGuardJudge(device_id, self.model, self.settings)
            log.info("nuevo dispositivo: %s (%s)", device_id, table)
        return self.judges[key]

    def process(self, table: str, rows: list[dict], prime_ids: set[int] = frozenset()) -> list[dict]:
        """Evalúa las lecturas; las de `prime_ids` solo entran al historial (sin decisión)."""
        out = []
        for row in rows:
            row_id = int(row["id"])
            self.last_id[table] = max(self.last_id[table], row_id)
            temperature, humidity, air = _num(row["temperature"]), _num(row["humidity"]), _num(row["air_quality"])
            if temperature is None or humidity is None or air is None:
                continue                                       # lectura incompleta (p. ej. air_quality antiguo "나쁨")
            at = datetime.fromisoformat(str(row["created_at"]))
            judge = self.judge(table, row["device_id"])
            if row_id in prime_ids:
                judge.prime(at, temperature, humidity, air)
                continue
            decision = judge.add(at, temperature, humidity, air, _num(row.get("lux")),
                                 _flag(row.get("door_open")), _flag(row.get("window_open")))
            if decision is not None:
                decision["reading_id"] = row_id
                decision["source"] = table
                out.append(decision)
        return out

    def process_batch(self, table: str, rows: list[dict]) -> list[dict]:
        """Como process(), pero si un dispositivo trae muchas lecturas de golpe (arranque, historial cargado
        por el simulador) solo las últimas `warmup_full_rows` pasan por el modelo completo; el resto solo
        llena el historial, que es mucho más rápido y da las mismas características."""
        per_device: dict[str, list[int]] = {}
        for row in rows:
            per_device.setdefault(row["device_id"], []).append(int(row["id"]))
        keep = self.cfg["warmup_full_rows"]
        prime_ids = {i for ids in per_device.values() for i in ids[:-keep]}
        return self.process(table, rows, prime_ids)

    def save(self, decisions: list[dict]) -> None:
        chunk = self.cfg["post_chunk"]
        for i in range(0, len(decisions), chunk):
            self.api.save(decisions[i:i + chunk])

    def warmup(self) -> None:
        for table in self.cfg["tables"]:
            self.warmup_table(table)
        log.info("listo: %d dispositivos", len(self.judges))

    def warmup_table(self, table: str) -> None:
        minutes = int(self.cfg["warmup_hours"] * 60)
        log.info("[%s] releyendo las últimas %d h para calentar el modelo...", table, self.cfg["warmup_hours"])
        rows, after = [], None
        while True:
            params = {"since_minutes": minutes, "limit": self.cfg["batch_limit"], "table": table}
            if after is not None:
                params = {"after_id": after, "limit": self.cfg["batch_limit"], "table": table}
            page = self.api.readings_page(**params)
            batch = page["rows"]
            rows += batch
            self.last_id[table] = max(self.last_id[table], int(page.get("max_id", 0)))
            if len(batch) < self.cfg["batch_limit"]:
                break
            after = int(batch[-1]["id"])
        decisions = self.process_batch(table, rows)
        latest = {}
        for d in decisions:
            latest[d["device_id"]] = d
        self.save(list(latest.values()))                   # solo la última por dispositivo

    def step(self) -> int:
        total = 0
        for table in self.cfg["tables"]:
            rows: list[dict] = []
            while True:                                    # traer todo lo pendiente antes de decidir
                after = int(rows[-1]["id"]) if rows else self.last_id[table]
                batch = self.api.readings(after_id=after, limit=self.cfg["batch_limit"], table=table)
                rows += batch
                if len(batch) < self.cfg["batch_limit"]:
                    break
            decisions = self.process_batch(table, rows)
            self.save(decisions)
            latest = {d["device_id"]: d for d in decisions}
            for d in latest.values():
                log.info("[%s] %s %s | %s", table, d["device_id"], d["level"], d["headline"])
            total = max(total, len(rows))
        return total

    def run(self, once: bool = False) -> None:
        self.warmup()
        while True:
            try:
                n = self.step()
            except Exception as exc:                          # red caída, XAMPP apagado...: reintentar
                log.warning("error: %s", exc)
                n = 0
            if once:
                return
            if n < self.cfg["batch_limit"]:
                time.sleep(self.cfg["poll_seconds"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(HERE / "config.json"))
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    cfg = dict(DEFAULTS)
    path = Path(args.config)
    if path.exists():
        cfg.update(json.loads(path.read_text(encoding="utf-8")))
    else:
        log.warning("no existe %s; usando valores por defecto", path)
    Worker(cfg).run(once=args.once)


if __name__ == "__main__":
    main()
