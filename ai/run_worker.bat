@echo off
REM Inicia el servicio de IA de CleanGuard (dejar esta ventana abierta)
cd /d "%~dp0"
if not exist .venv (
  py -3.13 -m venv .venv
  .venv\Scripts\pip install -r requirements.txt
)
.venv\Scripts\python worker.py
pause
