"""Pestaña 3 · Evaluar: ground truth exacto por pieza (etiquetado con clic) y métricas."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import matplotlib.pyplot as plt
from evaluate import TEST, evaluar, exportar
from vision.pipeline import ROOT
from .etiquetado import Etiquetador
from .tema import banner, pintar_banner
from .utils import ImageView, en_hilo, fig_a_bgr, llenar


class TabEvaluar(ttk.Frame):
    def __init__(self, nb, app):
        super().__init__(nb, padding=6); self.app, self.res = app, None
        sub = ttk.Notebook(self); sub.pack(fill="both", expand=True)
        self.etq = Etiquetador(sub, app, TEST)           # fotos de test, separadas de las de calibración
        r = ttk.Frame(sub, padding=6)
        sub.add(self.etq, text="  1 · Anotar fotos de test  "); sub.add(r, text="  2 · Resultados  ")
        b = ttk.Frame(r); b.pack(fill="x")
        ttk.Button(b, text="Evaluar", style="Grande.TButton", command=self.evaluar).pack(side="left", padx=(0, 8))
        ttk.Button(b, text="Exportar para el informe…", style="Sec.TButton", command=self.exportar).pack(side="left")
        self.resumen = banner(r, "neutro", "Pulsa «Evaluar» para medir el sistema con las fotos de test etiquetadas.", wraplength=1100, font=None)
        self.resumen.pack(fill="x", pady=8)
        cuerpo = ttk.Frame(r); cuerpo.pack(fill="both", expand=True)
        self.vconf = ImageView(cuerpo, hint="Aquí aparecerá la matriz de confusión."); self.vconf.pack(side="left", fill="both", expand=True)
        der = ttk.Frame(cuerpo, width=430); der.pack(side="left", fill="y", padx=(8, 0)); der.pack_propagate(False)
        ttk.Label(der, text="Precisión y recall por clase").pack(anchor="w")
        self.tmet = ttk.Treeview(der, height=10); self.tmet.pack(fill="x")
        ttk.Label(der, text="Imagen por imagen").pack(anchor="w", pady=(8, 0))
        self.timg = ttk.Treeview(der, height=8); self.timg.pack(fill="x")

    def refrescar_cfg(self):
        self.etq.refrescar_cfg()

    def evaluar(self):
        def trabajo(prog):
            r = evaluar(self.app.cfg, prog)
            r["img"] = fig_a_bgr(r["fig"]); plt.close(r["fig"])
            return r
        def listo(r):
            self.res = r
            pintar_banner(self.resumen, "ok" if r["accuracy"] >= .95 and not r["falsas"] else "aviso",
                          f"Accuracy {r['accuracy']:.1%}   ·   Piezas perdidas: {r['perdidas']}   ·   Falsas: {r['falsas']}")
            self.vconf.mostrar(r["img"]); llenar(self.tmet, r["met"], "clase"); llenar(self.timg, r["imagenes"])
        en_hilo(self.app, trabajo, listo)

    def exportar(self):
        if not self.res: return messagebox.showinfo("Nada que exportar", "Pulsa «Evaluar» primero.")
        d = filedialog.askdirectory(title="Carpeta de destino", initialdir=f"{ROOT}/results")
        if d:
            exportar(self.res, d); messagebox.showinfo("Exportado", f"CSV y PNG guardados en:\n{d}")
