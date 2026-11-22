@echo off
rem Doble clic en Windows: activa el entorno virtual (lo crea si falta), instala dependencias y abre la app.
cd /d "%~dp0"
if not exist .venv\Scripts\activate.bat (
    py -3 -m venv .venv || python -m venv .venv
)
call .venv\Scripts\activate.bat
python -c "import cv2, numpy, yaml, matplotlib, pandas, ruamel.yaml, pillow_heif, tkinter" 2>nul || pip install -r requirements.txt
python app.py
if errorlevel 1 pause
