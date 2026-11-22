"""Pestaña 4 · Árbol de decisión."""
import os
from tkinter import ttk
import cv2
from vision.decision_tree import draw_tree
from vision.pipeline import ROOT
from .utils import ImageView


class TabArbol(ttk.Frame):
    def __init__(self, nb, app):
        super().__init__(nb, padding=8); self.app = app
        ttk.Button(self, text="Regenerar con los umbrales actuales", style="Grande.TButton", command=self.refrescar).pack(anchor="w")
        self.vista = ImageView(self, hint="Pulsa «Regenerar» para dibujar el árbol."); self.vista.pack(fill="both", expand=True, pady=6)

    def refrescar(self):
        ruta = os.path.join(ROOT, "results", "arbol_decision.png")
        draw_tree(self.app.cfg, ruta)
        self.vista.mostrar(cv2.imread(ruta))
