"""Pestaña 2 · Analizar."""
import datetime, glob, os
import tkinter as tk
from tkinter import font as tkfont
from tkinter import filedialog, messagebox, ttk
import cv2, pandas as pd
from vision.config_io import guardar_config
from vision.inventory import inventory
from vision.pipeline import process, row, ROOT
from vision.visualization import mosaic
from .herramientas import FOTOS
from .tema import C, banner, pintar_banner
from .utils import ImageView, en_hilo, leer_imagen


class TabAnalizar(ttk.Frame):
    def __init__(self, nb, app):
        super().__init__(nb, padding=8); self.app, self.r, self.nombre = app, None, None
        b = ttk.Frame(self); b.pack(fill="x")
        ttk.Button(b, text="Abrir imagen…", style="Grande.TButton", command=self.abrir).pack(side="left")
        ttk.Button(b, text="Capturar del móvil", style="Grande.TButton", command=self.capturar).pack(side="left", padx=8)
        ttk.Label(b, text="URL cámara IP:").pack(side="left", padx=(8, 4))
        self.url = tk.StringVar(value=app.cfg.get("ipcam_url", ""))
        ttk.Entry(b, textvariable=self.url, width=34).pack(side="left")
        self.debug = tk.BooleanVar()
        ttk.Checkbutton(b, text="Ver etapas (debug)", variable=self.debug, command=self.mostrar).pack(side="left", padx=14)
        ttk.Button(b, text="Guardar resultado", style="Ok.TButton", command=self.guardar).pack(side="right")
        cuerpo = ttk.Frame(self); cuerpo.pack(fill="both", expand=True, pady=(8, 0))
        self.vista = ImageView(cuerpo, hint="Abre una foto del tapete (JPG, PNG o HEIC)\no captura una desde el móvil.")
        self.vista.pack(side="left", fill="both", expand=True)
        der = ttk.Frame(cuerpo, width=460); der.pack(side="left", fill="y", padx=(10, 0)); der.pack_propagate(False)
        kpis = ttk.Frame(der); kpis.pack(fill="x")
        self.kpi, self._fuente = {}, tkfont.Font(size=20, weight="bold")     # referencia viva: si no, Tk la pierde
        for i, t in enumerate(("Piezas", "Tetones", "Desconocidas")):          # tarjetas con las cifras clave
            f = tk.Frame(kpis, bg="white", highlightthickness=1, highlightbackground=C["borde"]); f.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0))
            kpis.columnconfigure(i, weight=1)
            self.kpi[t] = tk.Label(f, text="–", bg="white", fg=C["texto"], font=self._fuente); self.kpi[t].pack(pady=(4, 0))
            tk.Label(f, text=t, bg="white", fg=C["suave"]).pack(pady=(0, 4))
        ttk.Label(der, text="Colección completa vs escena", font=("", 12, "bold")).pack(anchor="w", pady=(8, 3))
        self.inv = ttk.Treeview(der, columns=("enc", "esp", "estado"), height=15, style="Compacto.Treeview")
        for c, t, w in (("#0", "Clase", 170), ("enc", "Hay", 55), ("esp", "Set", 55), ("estado", "Estado", 90)):
            self.inv.heading(c, text=t); self.inv.column(c, width=w, anchor="w" if c == "#0" else "center")
        for tag, fg, bg in (("ok", "#14532d", "#f0fdf4"), ("FALTA", "#7f1d1d", "#fee2e2"), ("SOBRA", "#78350f", "#fef3c7")):
            self.inv.tag_configure(tag, foreground=fg, background=bg)
        self.inv.pack(fill="x")
        self.faltan = banner(der, "neutro", "", wraplength=440, font=None); self.faltan.pack(fill="x", pady=(8, 0))
        ttk.Label(der, text="Avisos", font=("", 12, "bold")).pack(anchor="w", pady=(8, 3))
        self.avisos = tk.Text(der, height=8, wrap="word", state="disabled")
        for tag, fg, bg in (("aviso", "#78350f", "#fef3c7"), ("error", "#7f1d1d", "#fee2e2"), ("ok", "#14532d", "#dcfce7"), ("info", "#1e3a8a", "#dbeafe")):
            self.avisos.tag_configure(tag, foreground=fg, background=bg, spacing1=3, spacing3=3, lmargin1=6, lmargin2=6)
        self.avisos.pack(fill="both", expand=True)

    def abrir(self):
        f = filedialog.askopenfilename(title="Foto del tapete", filetypes=FOTOS)
        if f: self.analizar(leer_imagen(f), os.path.splitext(os.path.basename(f))[0])

    def capturar(self):
        url = self.url.get().strip()
        if not url:
            return messagebox.showinfo("URL", "Escribe la URL de la cámara IP (por ejemplo http://192.168.1.20:8080/video).")
        if url != self.app.cfg.get("ipcam_url"):
            guardar_config(lambda d, s: d.__setitem__("ipcam_url", url)); self.app.recargar()
        def trabajo(_):
            cap, fr = cv2.VideoCapture(url), None
            if not cap.isOpened():
                raise ValueError("No se pudo conectar con la cámara. Comprueba la URL y que el móvil y el ordenador estén en la misma red Wi-Fi.")
            for _ in range(5):                 # los primeros frames suelen venir en caché
                ok, f = cap.read(); fr = f if ok else fr
            cap.release()
            if fr is None: raise ValueError("La cámara conectó pero no envió imagen.")
            return fr
        en_hilo(self.app, trabajo, lambda fr: self.analizar(fr, datetime.datetime.now().strftime("captura_%Y%m%d_%H%M%S")))

    def analizar(self, img, nombre):
        def listo(r):
            self.r, self.nombre = r, nombre
            r["mosaico"] = mosaic(r["stages"])
            inv = r["inventario"] = inventory(r["pieces"], self.app.cfg, imprimir=False)
            self.inv.delete(*self.inv.get_children())
            for f in inv["coleccion"].itertuples():
                self.inv.insert("", "end", text=f.clase, values=(f.encontradas, f.esperadas, {"ok": "✔ ok"}.get(f.estado, f.estado)), tags=(f.estado,))
            nd = len(inv["desconocidas"])
            self.kpi["Piezas"].configure(text=str(inv["n"])); self.kpi["Tetones"].configure(text=str(inv["tetones"]))
            self.kpi["Desconocidas"].configure(text=str(nd), fg="#b91c1c" if nd else "#15803d")
            if inv["faltan"]: pintar_banner(self.faltan, "error", "FALTAN: " + ", ".join(inv["faltan"]))
            else: pintar_banner(self.faltan, "ok", "✔ La colección está completa: no falta ninguna pieza.")
            self.avisos.configure(state="normal"); self.avisos.delete("1.0", "end")
            for a in r["avisos"]:
                self.avisos.insert("end", ("⚠ " if not a.startswith("#") else "✘ ") + a + "\n", "aviso" if not a.startswith("#") else "error")
            if not r["avisos"]: self.avisos.insert("end", "✔ Sin avisos.", "ok")
            self.avisos.configure(state="disabled")
            self.mostrar()
        en_hilo(self.app, lambda _: process(img, self.app.cfg), listo)

    def mostrar(self):
        if self.r: self.vista.mostrar(self.r["mosaico"] if self.debug.get() else self.r["result"])

    def guardar(self):
        if not self.r:
            return messagebox.showinfo("Nada que guardar", "Analiza primero una imagen.")
        base = os.path.join(ROOT, "results", self.nombre); os.makedirs(os.path.dirname(base), exist_ok=True)
        cv2.imwrite(base + "_resultado.png", self.r["result"]); cv2.imwrite(base + "_debug.png", self.r["mosaico"])
        pd.DataFrame([row(p) for p in self.r["pieces"]]).to_csv(base + "_piezas.csv", index=False)
        inventory(self.r["pieces"], self.app.cfg, base + "_inventario.csv", imprimir=False)
        messagebox.showinfo("Guardado", f"Guardado en results/:\n{self.nombre}_resultado.png\n{self.nombre}_inventario.csv\n{self.nombre}_coleccion.csv\n{self.nombre}_piezas.csv\n{self.nombre}_debug.png")
