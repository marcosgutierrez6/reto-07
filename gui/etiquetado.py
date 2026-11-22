"""Etiquetado de piezas con clic: el árbol propone una clase y tú la confirmas o corriges.
Se usa en Calibración (dataset/calibration) y en Evaluar (dataset/test, ground truth exacto por pieza)."""
import glob, os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2, numpy as np, pandas as pd
from vision import etiquetas as E
from vision.acquisition import listar_fotos
from vision.pipeline import process
from vision.visualization import etiquetar_piezas
from .herramientas import FOTOS
from .tema import banner, pintar_banner
from .utils import ImageView, copiar_unico, en_hilo, leer_imagen

ACEPTAR = "✔ aceptar la propuesta"
NOMBRES = {"intrusa": "intrusa / desconocido", "ignorar": "ignorar (falsa detección)"}     # lo que se ve -> lo que se guarda
GUARDA = {v: k for k, v in NOMBRES.items()}


class Etiquetador(ttk.Frame):
    def __init__(self, parent, app, carpeta, objetivo=0, al_cambiar=None):
        super().__init__(parent, padding=8)
        self.app, self.carpeta, self.objetivo, self.al_cambiar = app, carpeta, objetivo, al_cambiar or (lambda: None)
        self.csv = os.path.join(carpeta, "labels.csv")
        self.df, self.cache, self.actual, self.nombres, self.chips = E.cargar(self.csv), {}, None, [], {}
        izq = ttk.Frame(self, width=380); izq.pack(side="left", fill="y"); izq.pack_propagate(False)

        f1 = ttk.LabelFrame(izq, text=" 1 · Fotos ", padding=8); f1.pack(fill="x")
        fila = ttk.Frame(f1); fila.pack(fill="x")
        ttk.Button(fila, text="Añadir fotos…", style="Grande.TButton", command=self.anadir).pack(side="left", expand=True, fill="x")
        ttk.Button(fila, text="✔ Todo correcto", style="Ok.TButton", command=self.todo_correcto).pack(side="left", expand=True, fill="x", padx=(6, 0))
        self.lb = tk.Listbox(f1, height=4, exportselection=False); self.lb.pack(fill="x", pady=(8, 0))
        self.lb.bind("<<ListboxSelect>>", lambda e: self.elegir())

        f2 = ttk.LabelFrame(izq, text=" 2 · Qué hace el clic sobre una pieza ", padding=8); f2.pack(fill="x", pady=8)
        self.clase = tk.StringVar(value=ACEPTAR)
        self.combo = ttk.Combobox(f2, textvariable=self.clase, state="readonly"); self.combo.pack(fill="x")
        ttk.Label(f2, style="Suave.TLabel", wraplength=340, text="Clic izquierdo: pone la clase elegida (o confirma la propuesta). "
                  "Clic derecho: deshace. Doble clic en la tabla: asigna a esa fila.").pack(fill="x", pady=(6, 0))

        f3 = ttk.LabelFrame(izq, text=" 3 · Piezas de la foto ", padding=8); f3.pack(fill="both", expand=True)
        self.tabla = ttk.Treeview(f3, columns=("id", "prop", "clase"), show="headings", height=7)
        for c, t, w in (("id", "#", 36), ("prop", "Propuesta", 150), ("clase", "Etiqueta", 150)):
            self.tabla.heading(c, text=t); self.tabla.column(c, width=w, anchor="center")
        self.tabla.tag_configure("pend", foreground="#b45309"); self.tabla.tag_configure("hecho", foreground="#15803d")
        self.tabla.pack(fill="both", expand=True); self.tabla.bind("<Double-1>", self.doble_clic)
        self.tabla.bind("<<TreeviewSelect>>", self.ver_motivo)
        self.motivo = banner(f3, "neutro", "Selecciona una pieza para ver por qué el árbol propone esa clase.", wraplength=340)
        self.motivo.pack(fill="x", pady=(8, 0))

        der = ttk.Frame(self); der.pack(side="left", fill="both", expand=True, padx=(10, 0))
        self.fichas = ttk.Frame(der); self.fichas.pack(side="bottom", fill="x", pady=(8, 0))       # progreso por clase
        self.vista = ImageView(der, on_click=self.clic, hint="Añade fotos y elige una en la lista de la izquierda.")
        self.vista.pack(fill="both", expand=True)
        self.refrescar_cfg()

    # ---------- datos ----------
    def refrescar_cfg(self):
        """Tras cambiar config (clases, umbrales): relista, vacía la caché y vuelve a proponer."""
        self.combo["values"] = [ACEPTAR] + list(self.app.cfg["clases"]) + list(NOMBRES.values())
        self.cache = {}
        for w in self.fichas.winfo_children(): w.destroy()
        self.chips = {}
        for i, c in enumerate(list(self.app.cfg["clases"]) + ["intrusa"]):
            self.chips[c] = banner(self.fichas, "neutro", c, padx=8, pady=4, anchor="center", wraplength=0, font=None)
            self.chips[c].grid(row=i // 5, column=i % 5, padx=3, pady=3, sticky="ew")
        for j in range(5): self.fichas.columnconfigure(j, weight=1)
        self.listar()
        if self.actual: self.cargar(self.actual)
        else: self.progreso()

    def listar(self):
        sel = self.lb.curselection()
        self.nombres = [os.path.basename(x) for x in listar_fotos(self.carpeta)]
        self.lb.delete(0, "end")
        for n in self.nombres:
            self.lb.insert("end", f"{n}   ({(self.df.imagen == n).sum()} etiquetadas)")
        if sel and sel[0] < len(self.nombres): self.lb.selection_set(sel[0])

    def anadir(self):
        for f in filedialog.askopenfilenames(title="Fotos (varias piezas a la vez, en posiciones y giros distintos)", filetypes=FOTOS):
            copiar_unico(f, self.carpeta)
        self.listar()

    def elegir(self):
        if (s := self.lb.curselection()): self.cargar(self.nombres[s[0]])

    def cargar(self, nombre):
        if nombre in self.cache:
            self.actual = nombre; return self.dibujar()
        img = leer_imagen(os.path.join(self.carpeta, nombre))
        def listo(r):
            self.cache[nombre], self.actual = r, nombre
            self.dibujar()
        en_hilo(self.app, lambda _: process(img, self.app.cfg), listo)

    def _fila_de(self, p, r):
        """Índice de la fila de labels.csv que corresponde a la pieza `p` de la foto actual (o None)."""
        rows = self.df[self.df.imagen == self.actual]
        if rows.empty: return None
        d = np.hypot(rows.cx_px - p["cx"], rows.cy_px - p["cy"])
        return d.idxmin() if d.min() <= self.app.cfg["tol_emparejar_cm"] * r["px_cm"] else None

    def etiquetas_pieza(self):
        r = self.cache[self.actual]
        return [None if (j := self._fila_de(p, r)) is None else self.df.loc[j, "clase"] for p in r["pieces"]]

    def _poner(self, i, clase):
        r = self.cache[self.actual]; p = r["pieces"][i]
        if (j := self._fila_de(p, r)) is not None: self.df = self.df.drop(j)
        if clase:
            fila = pd.DataFrame([E.fila(self.actual, p, r["px_cm"], r["marcadores"], clase)])
            self.df = pd.concat([self.df, fila], ignore_index=True)

    def _guardado(self):
        self.df.to_csv(self.csv, index=False)
        self.dibujar(); self.listar(); self.al_cambiar()

    def asignar(self, i, clase):
        self._poner(i, clase); self._guardado()

    def todo_correcto(self):
        if self.actual is None:
            return messagebox.showinfo("Elige una foto", "Selecciona primero una foto de la lista.")
        r, dudosas = self.cache[self.actual], 0
        for i, c in enumerate(self.etiquetas_pieza()):
            if c is not None: continue
            if r["pieces"][i]["label"] == "DESCONOCIDO": dudosas += 1; continue     # no se acepta a ciegas: puede ser un error del árbol
            self._poner(i, E.propuesta(r["pieces"][i]))
        self._guardado()
        if dudosas:
            messagebox.showinfo("Revisa estas piezas", f"{dudosas} pieza(s) tienen propuesta DESCONOCIDO y se han dejado SIN etiquetar (en naranja).\n\n"
                                "Mira el motivo en la tabla. Si es una pieza de tu colección, elige su clase y haz clic sobre ella; "
                                "si es de verdad una intrusa, elige «intrusa / desconocido»; si es una sombra, «ignorar».")

    # ---------- interfaz ----------
    def _clase_elegida(self, i):
        c = GUARDA.get(self.clase.get(), self.clase.get())
        return E.propuesta(self.cache[self.actual]["pieces"][i]) if c == ACEPTAR else c

    def clic(self, x, y, boton):
        if self.actual is None: return
        r = self.cache[self.actual]
        d = [np.hypot(p["cx"] - x, p["cy"] - y) for p in r["pieces"]]
        if not d or min(d) > 2.5 * r["px_cm"]: return
        i = int(np.argmin(d))
        self.tabla.selection_set(str(i)) if self.tabla.exists(str(i)) else None
        self.asignar(i, None if boton == "der" else self._clase_elegida(i))

    def doble_clic(self, e):
        if self.actual and (iid := self.tabla.identify_row(e.y)): self.asignar(int(iid), self._clase_elegida(int(iid)))

    def ver_motivo(self, _=None):
        """Muestra por qué el árbol propone DESCONOCIDO para la pieza seleccionada."""
        if self.actual and (s := self.tabla.selection()):
            p = self.cache[self.actual]["pieces"][int(s[0])]
            if p["motivo"]: pintar_banner(self.motivo, "aviso", f"#{p['id']} DESCONOCIDO: {p['motivo']}")
            else: pintar_banner(self.motivo, "ok", f"#{p['id']}: {p['label']} ✔ (clase válida)")

    def dibujar(self):
        r, cl = self.cache[self.actual], self.etiquetas_pieza()
        im = r["rect"].copy(); k = max(1.0, im.shape[1] / 1400)
        self.tabla.delete(*self.tabla.get_children())
        for i, (p, c) in enumerate(zip(r["pieces"], cl)):
            col = (128, 128, 128) if c == "ignorar" else (0, 200, 0) if c else (0, 165, 255)   # gris / confirmada / pendiente
            cv2.drawContours(im, [p["_contour"]], -1, col, int(3 * k))
            self.tabla.insert("", "end", iid=str(i), values=(p["id"], E.propuesta(p), c or "—"), tags=("hecho" if c else "pend",))
        etiquetar_piezas(im, [(f"#{p['id']} {c or E.propuesta(p) + '?'}", p["_contour"]) for p, c in zip(r["pieces"], cl)])
        self.vista.mostrar(im)
        self.progreso()

    def progreso(self):
        """Fichas de color por clase: verde si ya hay las mediciones mínimas, rojo si faltan."""
        n = self.df.clase.value_counts()
        for c, chip in self.chips.items():
            hechas = int(n.get(c, 0)); obj = self.objetivo * self.app.cfg.get("unidades", {}).get(c, 1) if c != "intrusa" else 0
            pintar_banner(chip, "neutro" if not obj else "ok" if hechas >= obj else "error",
                          f"{c}   {hechas}/{obj}" if obj else f"{c}   {hechas}")
