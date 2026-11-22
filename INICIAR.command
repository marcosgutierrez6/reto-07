#!/bin/bash
# Doble clic en Mac: activa el entorno virtual (lo crea si falta), instala dependencias y abre la app.
cd "$(dirname "$0")"
if [ -d .venv ]; then V=.venv; elif [ -d ../.venv ]; then V=../.venv; else python3 -m venv .venv && V=.venv; fi
source "$V/bin/activate"
python -c "import tkinter" 2>/dev/null || { echo "Falta Tkinter. Instálalo con:  brew install python-tk"; read -p "Pulsa Enter para cerrar"; exit 1; }
python -c "import cv2, numpy, yaml, matplotlib, pandas, ruamel.yaml, pillow_heif" 2>/dev/null || pip install -r requirements.txt
python app.py || read -p "Ha ocurrido un error. Pulsa Enter para cerrar"
