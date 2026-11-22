"""Genera dist/LEGOVision/ (carpeta con .exe) con PyInstaller. config.yaml, dataset/ y results/ quedan
junto al ejecutable (fuera del exe) para poder editarlos. Ejecutar en el sistema destino: python build_exe.py"""
import os, shutil, subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
subprocess.check_call([sys.executable, "-m", "PyInstaller", "--noconfirm", "--onedir", "--windowed", "--name", "LEGOVision",
                       "--paths", "tools", "--collect-all", "ruamel.yaml", "--collect-all", "pillow_heif", "app.py"])
destino = os.path.join("dist", "LEGOVision")
shutil.copy("config.yaml", destino)
for d in ("dataset", "results"):
    shutil.copytree(d, os.path.join(destino, d), dirs_exist_ok=True)
print("Listo:", destino)
