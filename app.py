"""Interfaz gráfica del sistema de visión LEGO. Uso: python app.py"""
import os, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [AQUI, os.path.join(AQUI, "tools")]       # vision/, gui/ y tools/ importables
import tkinter as tk
from tkinter import ttk
from vision.pipeline import load_config
from gui import tema
from gui.utils import mostrar_error
from gui.tab_calibracion import TabCalibracion
from gui.tab_analizar import TabAnalizar
from gui.tab_evaluar import TabEvaluar
from gui.tab_arbol import TabArbol


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LEGO · Visión artificial clásica"); self.geometry("1440x900"); self.minsize(1180, 720)
        self.report_callback_exception = lambda t, e, tb: mostrar_error(e, self)   # nada de tracebacks en pantalla
        tema.aplicar(self)
        self.cfg = load_config()
        tema.cabecera(self, "LEGO · Visión artificial clásica", "calibrar · analizar · evaluar")
        pie = tk.Frame(self, bg=tema.C["gris"]); pie.pack(side="bottom", fill="x")        # barra de estado
        self.estado = tk.StringVar(value="Listo")
        tk.Label(pie, textvariable=self.estado, bg=tema.C["gris"], fg=tema.C["texto"], anchor="w").pack(side="left", padx=14, pady=6)
        self.barra = ttk.Progressbar(pie, length=260); self.barra.pack(side="right", padx=14, pady=6)
        self.nb = ttk.Notebook(self); self.nb.pack(fill="both", expand=True, padx=6, pady=(0, 4))
        self.tabs = [TabCalibracion(self.nb, self), TabAnalizar(self.nb, self), TabEvaluar(self.nb, self), TabArbol(self.nb, self)]
        for t, n in zip(self.tabs, ("1 · Calibración", "2 · Analizar", "3 · Evaluar", "4 · Árbol de decisión")):
            self.nb.add(t, text=n)
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.nb.nametowidget(self.nb.select()).__dict__.get("refrescar", lambda: None)())

    def recargar(self):
        """Tras guardar config.yaml: relee los umbrales y actualiza las pestañas."""
        self.cfg = load_config()
        for t in self.tabs:
            if hasattr(t, "refrescar_cfg"): t.refrescar_cfg()


if __name__ == "__main__":
    App().mainloop()
