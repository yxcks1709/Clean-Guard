# CleanGuard AI — detección de olores, puertas/ventanas, luces, fugas y tuberías congeladas

Este servicio aplica el modelo de [bangak684/restroom_sensor_ai](https://github.com/bangak684/restroom_sensor_ai)
(16 clasificadores `HistGradientBoosting`, 56 características, una decisión cada 15 s) a las lecturas reales de CleanGuard
y le añade reglas para lo que el modelo no cubre con nuestros sensores.

```
ESP8266 ──POST cada 15 s──> upload.php ──> sensor_data
                                              │
          ai/worker.py <──getAIInput.php──────┘
               │  (modelo + reglas, un juez por dispositivo)
               └──saveAIStatus.php──> ai_predictions ──getAIStatus.php──> dashboard (AIStatusCard)
```

## Qué detecta y cómo

| Qué | Sensor | Cómo | Calidad esperada* |
|---|---|---|---|
| **Mal olor** | MQ-135 | Modelo: `occupancy_odor`, `smoke_residual`, `smoking`. Si dura ≥ 10 min → 주의 "악취 N분째 지속" | buena (F1 ≈ 0.82) |
| **Puerta abierta/cerrada** | Reed switch en D7 (recomendado) | Con sensor: valor directo. Sin sensor: modelo (`door_open`) | sensor: exacta · modelo: débil (F1 ≈ 0.40) |
| **Ventana abierta/cerrada** | Reed switch en D1 (recomendado) | Igual que la puerta. En invierno (dic–feb) sube a 주의 | sensor: exacta · modelo: débil (F1 ≈ 0.36) |
| **Luces encendidas** | BH1750 (lux) | ≥ 40 lx encendida, < 20 lx apagada (histéresis). Encendida ≥ 30 min sin señales de uso → 정보 | exacta (umbral a calibrar) |
| **Fuga de agua** | DHT11 | Modelo `leak_active` + reglas: sin limpieza/lavado o ≥ 30 min → 긴급 | buena (F1 ≈ 0.86) |
| **Tubería congelada / riesgo** | DHT11 | Modelo `freeze_risk_1h/3h` + regla directa: 0 °C durante ≥ 10 min → 긴급 "배관 동결 의심" | buena (F1 ≈ 0.85 a 1 h) |

\* Cifras del propio repositorio del modelo, medidas **solo con datos sintéticos**. Con datos reales hay que recalibrar
umbrales (ver abajo). El modelo no "ve" las luces: eso lo hace el BH1750 con reglas simples.

El modelo necesita **2 horas de historial** antes de su primera decisión. Durante ese tiempo el nivel aparece como
`준비 중`, pero luces, contactos de puerta/ventana y la regla de tubería congelada ya funcionan. Al arrancar, el servicio
relee las últimas 10 h de la base de datos, así que si el ESP8266 ya estaba enviando datos no hay que esperar.
Si un dispositivo deja de enviar más de 10 minutos, su historial se reinicia (otras 2 h de calentamiento).

## Puesta en marcha (con el backend de kbu1.dothome)

1. **Base de datos** — en el phpMyAdmin de dothome, pestaña SQL: ejecutar
   [`database/migrations/001_ai_detection.sql`](../database/migrations/001_ai_detection.sql) (una sola vez).
2. **Clave** — `backend/ai_config.php` y `ai/config.json` deben tener la misma `api_key`
   (por defecto `cleanguard-ai-change-me`; cámbiala en los dos si el servidor es público).
3. **Python 3.13** — instalar desde python.org. Las versiones de `requirements.txt` son las mismas con las que se guardó
   el modelo; con otra versión de scikit-learn el archivo `.joblib` puede no cargar.
4. **Configurar** `ai/config.json`: `api_base` = URL del backend (por defecto `https://kbu1.dothome.co.kr`).
5. **Arrancar** — doble clic en `ai/run_worker.bat` (la primera vez crea el entorno e instala paquetes).
   O a mano:
   ```
   cd ai
   py -3.13 -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   .venv\Scripts\python worker.py
   ```
6. **Firmware** — ver [`esp8266/README.md`](../esp8266/README.md) para el cableado y la configuración.

El servicio usa ~45 ms por decisión (un PC normal soporta decenas de dispositivos a 15 s).

## Pestaña Test (demo sin backend)

La pestaña **Test** del dashboard no necesita backend, base de datos ni Python: reproduce en tiempo real
(un paso cada 15 s) una grabación de la IA real sobre 5 baños simulados — mal olor, ventana, fuga,
congelamiento y uno normal con la luz apagada. Cada recarga de la página empieza desde el principio
(la fuga se confirma a los ~6 min, el riesgo de congelamiento a los ~4 min). La grabación está en
`frontend/src/data/test_replay.json` y se regenera con `python build_test_replay.py`.

## Ajustes (`config.json` → `settings`)

| Clave | Por defecto | Significado |
|---|---|---|
| `adc_scale` | 4.0029 | El ESP8266 lee 0–1023 (10 bits); el modelo se entrenó con 0–4095. Se multiplica por 4095/1023 |
| `light_on_lux` / `light_off_lux` | 40 / 20 | Umbrales de luz. Mide el baño con la luz encendida y apagada (de día y de noche) y ajusta |
| `light_idle_minutes` | 30 | Minutos con luz encendida y sin señales de uso antes del aviso |
| `odor_persist_minutes` | 10 | Minutos de mal olor continuo antes de subir a 주의 |
| `frozen_c` / `frozen_minutes` | 0.0 / 10 | El DHT11 no mide bajo 0 °C: una lectura de 0 °C sostenida se trata como posible congelamiento |

## Calibrar con datos reales

El modelo se entrenó con datos simulados. Cuando haya algunos días de datos reales, anota cuándo ocurrieron cosas
(abrir la ventana, limpieza, una fuga provocada con un trapo húmedo cerca del sensor, etc.) y compara con
`ai_predictions`. Los umbrales del modelo están en el propio `.joblib` y se pueden volver a elegir con
`python -m restroom_unified.retune` del repositorio original (ver su `docs/ALGORITHMS.md`, sección 7.8).

## Archivos

| Archivo | Qué es |
|---|---|
| `worker.py` | Servicio: lee lecturas, decide, guarda |
| `build_test_replay.py` | Genera la grabación de la pestaña Test (`frontend/src/data/test_replay.json`): la IA real sobre 5 baños simulados |
| `cleanguard_ai/judge.py` | `CleanGuardJudge`: modelo + reglas de luz, contactos, olor persistente y tubería congelada |
| `restroom_unified/` | Copia sin cambios de `features.py`, `model.py`, `rules.py`, `world.py` del repositorio del modelo (commit `e66ee4e`) |
| `models/unified/unified_model.joblib` | Modelo entrenado (15 MB) |
| `config.example.json` | Plantilla de configuración |
| `run_worker.bat` | Arranque en Windows |
