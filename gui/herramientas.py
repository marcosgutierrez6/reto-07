"""Ventanas auxiliares: ajuste de colores HSV con sliders y comprobación de resolución."""
import copy
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2, numpy as np
from vision.config_io import ETIQ, leer, escribir, guardar_config
from vision.decision_tree import regla_mascara
from check_resolution import evaluar     # tools/ ya está en sys.path (lo hace app.py)
from .tema import C, banner, pintar_banner
from .utils import ImageView, leer_imagen

FOTOS = [("Imágenes (incluye HEIC del iPhone)", "*.jpg *.jpeg *.png *.heic *.heif *.JPG *.JPEG *.PNG *.HEIC *.HEIF"), ("Todos", "*.*")]


def _hsv6(clave):    # sliders de un rango HSV completo de config (lo/hi de H, S, V)
    return [(f"{n} {'mín' if lh == 'lo' else 'máx'}", 179 if i == 0 else 255, (clave, lh, i))
            for i, n in enumerate("HSV") for lh in ("lo", "hi")]


def objetos(cfg):
    """Qué se puede ajustar: tapete, marcadores y una entrada por cada color de config.yaml (sus propias condiciones)."""
    o = {"Tapete verde": ("hsv", "tapete_hsv", _hsv6("tapete_hsv")), "Marcadores": ("hsv", "marcador_hsv", _hsv6("marcador_hsv"))}
    for c, r in cfg["color"].items():
        ks = (["h_lo", "h_hi"] if "h" in r else []) + [k for k in ("s_min", "s_max", "v_min", "v_max") if k in r]
        o[c.capitalize()] = ("color", c, [(ETIQ[k], 179 if k.startswith("h") else 255, f"{c}_{k}") for k in ks])
    return o


class AjusteHSV(tk.Toplevel):
    """Sliders con vista previa de la máscara. 'Guardar' escribe en config.yaml."""

    def __init__(self, app):
        super().__init__(app, bg=C["fondo"]); self.app = app; self.title("Ajustar colores (HSV)"); self.geometry("1000x720")
        self.tmp, self.cambios, self.hsv, self.img = copy.deepcopy(app.cfg), {}, None, None
        barra = ttk.Frame(self, padding=6); barra.pack(fill="x")
        ttk.Button(barra, text="Abrir foto…", style="Grande.TButton", command=self.abrir).pack(side="left")
        self.obj = tk.StringVar(value="Tapete verde")
        self.objs = objetos(app.cfg)
        c = ttk.Combobox(barra, textvariable=self.obj, values=list(self.objs), state="readonly", width=18)
        c.pack(side="left", padx=8); c.bind("<<ComboboxSelected>>", lambda e: self.sliders())
        ttk.Button(barra, text="Guardar en config.yaml", style="Ok.TButton", command=self.guardar).pack(side="right")
        self.vista = ImageView(self, hint="Abre una foto y mueve los sliders:\nlo que queda en color es lo que acepta la regla."); self.vista.pack(fill="both", expand=True)
        self.caja = ttk.Frame(self, padding=6); self.caja.pack(fill="x")
        self.sliders()

    def abrir(self):
        f = filedialog.askopenfilename(parent=self, title="Foto del tapete con piezas", filetypes=FOTOS)
        if f:
            img = leer_imagen(f)
            self.img = cv2.resize(img, (800, int(img.shape[0] * 800 / img.shape[1])))
            self.hsv = cv2.cvtColor(cv2.GaussianBlur(self.img, (5, 5), 0), cv2.COLOR_BGR2HSV)
            self.actualizar()

    def sliders(self):
        for w in self.caja.winfo_children(): w.destroy()
        for txt, mx, k in self.objs[self.obj.get()][2]:
            s = tk.Scale(self.caja, from_=0, to=mx, orient="horizontal", label=txt, length=150, command=lambda v, k=k: self.mover(k, v))
            s.set(int(leer(self.tmp, k))); s.pack(side="left", padx=4)
        self.actualizar()

    def mover(self, k, v):
        escribir(self.tmp, k, int(float(v))); self.cambios[k] = int(float(v)); self.actualizar()

    def actualizar(self):
        if self.img is None: return
        modo, clave, _ = self.objs[self.obj.get()]
        if modo == "hsv":
            d = self.tmp[clave]; m = cv2.inRange(self.hsv, np.array(d["lo"]), np.array(d["hi"]))
        else:
            m = regla_mascara(self.hsv, self.tmp["color"][clave])
        self.vista.mostrar(np.hstack([self.img, cv2.bitwise_and(self.img, self.img, mask=m)]))

    def guardar(self):
        if not self.cambios:
            return messagebox.showinfo("Sin cambios", "No has movido ningún slider.", parent=self)
        if messagebox.askyesno("Guardar", "Se escribirán los valores en config.yaml (queda copia config.yaml.bak). ¿Continuar?", parent=self):
            guardar_config(lambda d, s: [escribir(d, k, v, s) for k, v in self.cambios.items()])
            self.cambios = {}; self.app.recargar()
            messagebox.showinfo("Guardado", "config.yaml actualizado.", parent=self)


class Resolucion(tk.Toplevel):
    """Clic en 2 puntos de una regla/referencia de longitud conocida -> mm/px y comprobación del mínimo."""

    def __init__(self, app):
        super().__init__(app, bg=C["fondo"]); self.app, self.pts, self.base = app, [], None
        self.title("Comprobar resolución"); self.geometry("1000x720")
        barra = ttk.Frame(self, padding=6); barra.pack(fill="x")
        ttk.Button(barra, text="Abrir foto…", style="Grande.TButton", command=self.abrir).pack(side="left")
        ttk.Label(barra, text="  Longitud real entre los 2 puntos (mm):").pack(side="left")
        self.mm = tk.StringVar(value="100"); ttk.Entry(barra, textvariable=self.mm, width=7).pack(side="left", padx=4)
        ttk.Button(barra, text="Reiniciar puntos", command=self.reiniciar).pack(side="left", padx=8)
        self.res = banner(self, "info", "Abre una foto y haz clic en los dos extremos de la regla.", wraplength=950, font=None)
        self.res.pack(fill="x", padx=6, pady=6)
        self.vista = ImageView(self, on_click=self.clic); self.vista.pack(fill="both", expand=True)

    def abrir(self):
        f = filedialog.askopenfilename(parent=self, title="Foto con regla o referencia", filetypes=FOTOS)
        if f: self.base = leer_imagen(f); self.reiniciar()

    def reiniciar(self):
        self.pts = []
        if self.base is not None: self.vista.mostrar(self.base)

    def clic(self, x, y, boton):
        if len(self.pts) == 2: self.pts = []
        self.pts.append((x, y))
        im = self.base.copy(); r = max(3, im.shape[1] // 250)
        for p in self.pts: cv2.circle(im, (int(p[0]), int(p[1])), r, (0, 0, 255), -1)
        if len(self.pts) == 2:
            cv2.line(im, *[tuple(map(int, p)) for p in self.pts], (0, 0, 255), max(1, r // 2))
            try: mm = float(self.mm.get().replace(",", "."))
            except ValueError: return messagebox.showwarning("Longitud", "Escribe la longitud real en mm (un número).", parent=self)
            _, lineas, ok = evaluar(np.hypot(self.pts[0][0] - self.pts[1][0], self.pts[0][1] - self.pts[1][1]), mm, self.app.cfg["resolucion_min_px"])
            pintar_banner(self.res, "ok" if ok else "error",
                          "\n".join(lineas) + ("\n✔ La resolución es suficiente." if ok else "\n✘ Resolución insuficiente: acerca la cámara."))
        self.vista.mostrar(im)
