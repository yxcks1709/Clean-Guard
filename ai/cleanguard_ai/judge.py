"""CleanGuardJudge: un baño (un ESP8266), una decisión cada 15 s.

Envuelve el modelo unificado de restroom_sensor_ai (UnifiedJudge) y le añade lo que
ese modelo no cubre o cubre mal con los sensores de CleanGuard:

  * malos olores   -> modelo (occupancy_odor, smoke_residual, smoking) + regla de persistencia
  * puerta/ventana -> sensor magnético (reed) si existe; si no, el modelo
  * luces          -> sensor de luz BH1750 (lux) con histéresis + "luz encendida sin nadie"
  * fugas          -> modelo (leak_active) + reglas de restroom_unified.rules
  * congelamiento  -> modelo (freeze_risk_1h / 3h) + regla directa: DHT11 en 0 °C durante N minutos

El modelo necesita 2 h de historial (WARMUP). Mientras tanto, las reglas directas
(luz, contactos, tubería congelada) ya funcionan y el nivel sale como "준비 중" si no hay nada.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np

from restroom_unified import features as F
from restroom_unified import rules as R
from restroom_unified.model import UnifiedJudge, UnifiedModel

LEVELS = R.LEVELS                      # ("평상시", "정보", "주의", "긴급")
STEP_S = F.DT                          # 15 s por fila del modelo
ODOR_LABELS = ("occupancy_odor", "smoke_residual", "smoking")
PRESENCE_LABELS = ("occupancy_odor", "handwashing_humidity", "faucet_on", "door_open", "cleaning_products",
                   "cleaning_wet_floor", "sanitizer")


@dataclass
class Settings:
    adc_scale: float = 4095 / 1023     # ESP8266 A0 = 10 bits; el modelo se entrenó con ADC de 12 bits
    max_fill_s: int = 600              # huecos <= 10 min se rellenan repitiendo la última lectura
    light_on_lux: float = 40.0         # >= esto: luz encendida
    light_off_lux: float = 20.0        # <  esto: luz apagada (histéresis)
    light_idle_minutes: float = 30.0   # luz encendida sin señales de uso -> aviso
    odor_persist_minutes: float = 10.0 # mal olor que dura más que esto -> 주의
    frozen_c: float = 0.0              # DHT11 no mide bajo 0 °C: 0 significa "0 °C o menos"
    frozen_minutes: float = 10.0       # minutos a <= frozen_c para avisar "tubería congelada"

    @classmethod
    def from_dict(cls, data: dict | None) -> "Settings":
        known = {k: v for k, v in (data or {}).items() if k in cls.__dataclass_fields__}
        return cls(**known)


class _ContactJudge(UnifiedJudge):
    """UnifiedJudge que, si hay sensor magnético, usa su valor en lugar de la probabilidad del modelo."""

    door: bool | None = None
    window: bool | None = None

    def _decide(self, at, probs, temperature):
        if self.door is not None:
            probs["door_open"] = 1.0 if self.door else 0.0
        if self.window is not None:
            probs["window_open"] = 1.0 if self.window else 0.0
        return super()._decide(at, probs, temperature)


def _bucket(at: datetime) -> int:
    return int(at.timestamp()) // STEP_S


class CleanGuardJudge:
    def __init__(self, device_id: str, model: UnifiedModel, settings: Settings | None = None):
        self.device_id = device_id
        self.model = model
        self.cfg = settings or Settings()
        self.reset()

    def reset(self) -> None:
        """Olvida todo el historial (p. ej. si el simulador vuelve a cargar datos más antiguos)."""
        self._reset_model()
        self.last_bucket: int | None = None
        self.last_row: tuple | None = None
        self.light_on: bool | None = None
        self.light_since: datetime | None = None
        self.last_presence: datetime | None = None
        self.last_door: bool | None = None
        self.odor_timer, self.cold_timer = R.Timer(), R.Timer()

    def _reset_model(self) -> None:
        self.inner = _ContactJudge(self.device_id, self.model)

    # ------------------------------------------------------------------ entrada
    def add(self, at: datetime, temperature: float, humidity: float, mq135_raw: float,
            lux: float | None = None, door: bool | None = None, window: bool | None = None) -> dict | None:
        """Una lectura del ESP8266. Devuelve la decisión, o None si cae en un intervalo de 15 s ya decidido."""
        at = at.replace(tzinfo=None)
        if not self._advance(at, temperature, humidity, mq135_raw):
            return None                                   # varias lecturas en los mismos 15 s: solo cuenta la primera
        self.inner.door = door
        self.inner.window = window
        result = self.inner.add(at, *self.last_row, None)
        return self._finish(at, result, temperature, lux, door, window)

    def prime(self, at: datetime, temperature: float, humidity: float, mq135_raw: float) -> None:
        """Mete una lectura antigua en el historial sin evaluar el modelo (calentamiento rápido al arrancar).
        El historial queda igual que con add(); solo se pierden los temporizadores de esas filas."""
        at = at.replace(tzinfo=None)
        if self._advance(at, temperature, humidity, mq135_raw):
            self._push(at)

    def _advance(self, at: datetime, temperature: float, humidity: float, mq135_raw: float) -> bool:
        bucket = _bucket(at)
        if self.last_bucket is not None and self.last_bucket - bucket > self.cfg.max_fill_s // STEP_S:
            self.reset()                                  # el tiempo fue hacia atrás (datos recargados)
        if self.last_bucket is not None and bucket <= self.last_bucket:
            return False
        if self.last_bucket is not None:
            gap = bucket - self.last_bucket - 1
            if gap * STEP_S > self.cfg.max_fill_s:
                self._reset_model()                       # hueco largo: el historial ya no sirve, vuelve a calentar
            else:
                for _ in range(gap):                      # hueco corto: repetir la última lectura
                    self.last_bucket += 1
                    self._push(datetime.fromtimestamp(self.last_bucket * STEP_S))
        self.last_bucket = bucket
        self.last_row = (float(temperature), float(humidity), float(mq135_raw) * self.cfg.adc_scale)
        return True

    def _push(self, at: datetime) -> None:
        """Añade la última fila al historial de características sin predecir (barato)."""
        stream = self.inner.stream
        stream.stamp.append(np.datetime64(at, "ns"))
        for col, value in zip(stream.cols, (*self.last_row, np.nan)):
            col.append(value)
        stream.rows += 1

    # ------------------------------------------------------------------ reglas
    def _light(self, at: datetime, lux: float | None) -> bool | None:
        if lux is None:
            self.light_on = None
            self.light_since = None
            return None
        if self.light_on:
            on = lux >= self.cfg.light_off_lux
        else:
            on = lux >= self.cfg.light_on_lux
        if on and not self.light_on:
            self.light_since = at
        if not on:
            self.light_since = None
        self.light_on = on
        return on

    def _finish(self, at: datetime, result: dict, temperature: float, lux: float | None,
                door: bool | None, window: bool | None) -> dict:
        ready = result["ready"]
        labels = set(result["labels"])
        probs = result["probabilities"]
        items = [dict(i) for i in result["items"]]

        # Presencia: cualquier señal de uso, o un cambio en el contacto de la puerta.
        if labels & set(PRESENCE_LABELS) or (door is not None and self.last_door is not None and door != self.last_door):
            self.last_presence = at
        self.last_door = door

        # Puerta / ventana: sensor si hay, si no el modelo (solo cuando está listo).
        door_open = door if door is not None else ("door_open" in labels if ready else None)
        window_open = window if window is not None else ("window_open" in labels if ready else None)
        if not ready:
            # Antes de las 2 h el modelo no da nada; los contactos sí se pueden mostrar.
            if window:
                winter = at.month in R.WINTER_MONTHS
                items.append({"level": "주의" if winter else "정보", "code": "window_open", "message": "창문 열림"})
            if door:
                items.append({"level": "정보", "code": "door_open", "message": "문 열림"})

        # Mal olor
        odor = ready and bool(labels & set(ODOR_LABELS))
        odor_minutes = self.odor_timer.minutes(odor, at)
        if odor and odor_minutes >= self.cfg.odor_persist_minutes:
            items.append({"level": "주의", "code": "odor_persistent", "message": f"악취 {odor_minutes:.0f}분째 지속"})

        # Luz
        light_on = self._light(at, lux)
        idle_minutes = None
        if light_on:
            idle_from = max(t for t in (self.light_since, self.last_presence) if t is not None)
            idle_minutes = (at - idle_from).total_seconds() / 60
            if idle_minutes >= self.cfg.light_idle_minutes:
                items.append({"level": "정보", "code": "light_idle",
                              "message": f"사용 없이 조명 {idle_minutes:.0f}분째 켜짐"})

        # Tubería congelada (regla directa: no depende del modelo)
        cold_minutes = self.cold_timer.minutes(temperature <= self.cfg.frozen_c, at)
        pipe_frozen = cold_minutes >= self.cfg.frozen_minutes
        if pipe_frozen:
            items.append({"level": "긴급", "code": "pipe_frozen",
                          "message": f"배관 동결 의심 (실내 0℃ 이하 {cold_minutes:.0f}분)"})

        items.sort(key=lambda i: -LEVELS.index(i["level"]))
        if items:
            level, headline = items[0]["level"], items[0]["message"]
        elif ready:
            level, headline = "평상시", "정상"
        else:
            level, headline = result["level"], result["headline"]

        leak = "leak_active" in labels
        return {
            "device_id": self.device_id,
            "at": at.isoformat(sep=" ", timespec="seconds"),
            "ready": ready,
            "level": level,
            "headline": headline,
            "items": items,
            "labels": sorted(labels),
            "probabilities": probs,
            "status": {
                "odor": {"active": odor, "minutes": round(odor_minutes, 1),
                         "probability": probs.get("occupancy_odor")},
                "door": {"open": door_open, "source": "sensor" if door is not None else "ai"},
                "window": {"open": window_open, "source": "sensor" if window is not None else "ai"},
                "light": {"on": light_on, "lux": lux,
                          "idle_minutes": None if idle_minutes is None else round(idle_minutes, 1)},
                "leak": {"active": leak, "probability": probs.get("leak_active")},
                "freeze": {"pipe_frozen": pipe_frozen, "risk_1h": result["freeze_levels"]["freeze_risk_1h"],
                           "risk_3h": result["freeze_levels"]["freeze_risk_3h"], "temperature": temperature},
            },
        }
