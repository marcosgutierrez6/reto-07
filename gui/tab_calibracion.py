"""Pestaña 1 · Calibración: etiquetar fotos -> calcular umbrales -> comprobar."""
import copy, re
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import matplotlib.pyplot as plt, pandas as pd
from analyze_thresholds import analizar, exportar_figuras
from vision.config_io import a_plano, aplicar_plano, etiqueta, guardar_config
from vision.etiquetas import medir_etiquetadas, real_a_pred
from vision.pipeline import ROOT
from .etiquetado import Etiquetador
from .herramientas import AjusteHSV, Resolucion
from .tema import C, banner, pintar_banner
from .utils import ImageView, en_hilo, fig_a_bgr, llenar

CAL = f"{ROOT}/dataset/calibration"


class TabCalibracion(ttk.Frame):
    def __init__(self, nb, app):
        super().__init__(nb, padding=8); self.app, self.sug, self.vals = app, {}, a_plano(app.cfg)
        top = ttk.Frame(self); top.pack(fill="x")
        for t, c in (("Clases…", self.editar_clases), ("Ajustar colores (HSV)", lambda: AjusteHSV(app)),
                     ("Comprobar resolución", lambda: Resolucion(app))):
            ttk.Button(top, text=t, style="Sec.TButton", command=c).pack(side="left", padx=(0, 8))
        ttk.Label(top, style="Suave.TLabel", text="Flujo: 1) etiqueta fotos  →  2) calcula umbrales  →  3) guarda y comprueba").pack(side="right")
        sub = self.sub = ttk.Notebook(self); sub.pack(fill="both", expand=True, pady=6)
        self.etq = Etiquetador(sub, app, CAL, objetivo=10)
        u = ttk.Frame(sub, padding=10)
        sub.add(self.etq, text="  Paso 1 · Etiquetar fotos  "); sub.add(u, text="  Paso 2 · Umbrales  ")

        izq = ttk.Frame(u, width=470); izq.pack(side="left", fill="y"); izq.pack_propagate(False)
        ttk.Button(izq, text="Calcular umbrales", style="Grande.TButton", command=self.calcular).pack(side="top", fill="x")
        ttk.Button(izq, text="Comprobar calibración", style="Grande.TButton", command=self.comprobar).pack(side="bottom", fill="x", pady=(8, 0))
        fila = ttk.Frame(izq); fila.pack(side="bottom", fill="x", pady=(8, 0))
        ttk.Button(fila, text="Usar sugeridos", style="Sec.TButton", command=self.usar_sugeridos).pack(side="left", expand=True, fill="x")
        ttk.Button(fila, text="Guardar en config.yaml", style="Ok.TButton", command=self.guardar).pack(side="left", expand=True, fill="x", padx=(6, 0))
        ttk.Label(izq, style="Suave.TLabel", wraplength=450, text="Doble clic en una fila para editar el valor «Actual». "
                  "Las filas con valor sugerido se resaltan.").pack(side="top", fill="x", pady=(8, 4))
        self.tabla = ttk.Treeview(izq, columns=("actual", "sug", "mar"), height=10, style="Compacto.Treeview")
        for c, t, w in (("#0", "Umbral", 200), ("actual", "Actual", 75), ("sug", "Sugerido", 100), ("mar", "Margen σ", 105)):
            self.tabla.heading(c, text=t); self.tabla.column(c, width=w, anchor="w" if c == "#0" else "center")
        self.tabla.tag_configure("sug", background="#dbeafe"); self.tabla.tag_configure("edit", foreground="#b45309")
        sb = ttk.Scrollbar(izq, orient="vertical", command=self.tabla.yview); self.tabla.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", pady=4)
        self.tabla.pack(side="top", fill="both", expand=True, pady=4); self.tabla.bind("<Double-1>", self.editar)

        der = ttk.Notebook(u, style="Sub.TNotebook"); der.pack(side="left", fill="both", expand=True, padx=(10, 0))
        self.vistas = {}
        for k, t in (("ancho_vs_largo", "Ancho×largo"), ("S_vs_V", "S vs V"), ("V_vs_H", "V vs H"), ("L_vs_a", "L vs a"), ("H_vs_S", "H vs S")):
            self.vistas[k] = ImageView(der, hint="Pulsa «Calcular umbrales» para ver la gráfica.\nS vs V separa negro / gris / blanco / sombra;\nV vs H y L vs a separan rojo de marrón.")
            der.add(self.vistas[k], text=f" {t} ")
        c = ttk.Frame(der, padding=10); der.add(c, text=" Comprobación ")
        self.resumen = banner(c, "neutro", "Pulsa «Comprobar calibración».", wraplength=900, font=None); self.resumen.pack(fill="x")
        self.fallos = ttk.Treeview(c, height=14); self.fallos.pack(fill="both", expand=True, pady=8)
        e = ttk.Frame(der, padding=10); der.add(e, text=" Estadísticas ")
        self.texto = tk.Text(e, font=("Menlo", 11), state="disabled", wrap="none"); self.texto.pack(fill="both", expand=True)
        self.pintar()

    def refrescar_cfg(self):
        self.vals = a_plano(self.app.cfg); self.pintar(); self.etq.refrescar_cfg()

    # ---------- tabla de umbrales ----------
    def pintar(self):
        self.tabla.delete(*self.tabla.get_children())
        f = lambda v: f"{v:.2f}" if isinstance(v, float) else v
        for k, v in self.vals.items():
            s = self.sug.get(k)
            mar = "" if not s else " | ".join("—" if m is None else f"{m:.1f}" for m in s[1:])
            self.tabla.insert("", "end", iid=k, text=etiqueta(k), values=(f(v), "" if not s else f(s[0]), mar), tags=("sug",) if s else ())

    def editar(self, e):
        k = self.tabla.identify_row(e.y)
        if k and (v := simpledialog.askfloat("Editar umbral", etiqueta(k), initialvalue=self.vals[k], parent=self)) is not None:
            self.vals[k] = v; self.pintar()

    def usar_sugeridos(self):
        if not self.sug:
            return messagebox.showinfo("Sin sugerencias", "Primero pulsa «Calcular umbrales».")
        self.vals.update({k: s[0] for k, s in self.sug.items()}); self.pintar()

    def guardar(self):
        if messagebox.askyesno("Guardar", "Se sobrescribirán los umbrales de config.yaml (queda una copia en config.yaml.bak). ¿Continuar?"):
            guardar_config(lambda d, s: aplicar_plano(d, self.vals, s))
            self.app.recargar(); messagebox.showinfo("Guardado", "Umbrales guardados en config.yaml.\nCopia anterior: config.yaml.bak")

    # ---------- cálculo y comprobación ----------
    def calcular(self):
        cfg = copy.deepcopy(self.app.cfg)
        def trabajo(prog):
            df, _ = medir_etiquetadas(cfg, CAL, prog, incluir_ignoradas=True)   # intrusas y sombras salen en las gráficas
            if df.empty:
                raise ValueError("No hay piezas etiquetadas. Etiqueta antes algunas fotos en el paso 1.")
            figs, sug, txt = analizar(df, cfg)
            exportar_figuras(figs, f"{ROOT}/results/calibracion")
            imgs = {k: fig_a_bgr(f) for k, f in figs.items()}
            for f in figs.values(): plt.close(f)
            pd.DataFrame([{"umbral": k, "actual": a_plano(cfg)[k], "sugerido": s[0], "margen_abajo_sigma": s[1], "margen_arriba_sigma": s[2]}
                          for k, s in sug.items()]).to_csv(f"{ROOT}/results/calibracion/umbrales.csv", index=False)
            return imgs, sug, txt
        def listo(r):
            imgs, self.sug, txt = r
            for k, im in imgs.items(): self.vistas[k].mostrar(im)
            self.texto.configure(state="normal"); self.texto.delete("1.0", "end"); self.texto.insert("end", txt); self.texto.configure(state="disabled")
            self.pintar()
            messagebox.showinfo("Hecho", "Gráficas guardadas en results/calibracion/ (PNG) junto con umbrales.csv.")
        en_hilo(self.app, trabajo, listo)

    def comprobar(self):
        cfg = copy.deepcopy(self.app.cfg); aplicar_plano(cfg, self.vals)     # con los umbrales de la tabla (guardados o no)
        def trabajo(prog):
            df, perdidas = medir_etiquetadas(cfg, CAL, prog)
            if df.empty and perdidas.empty:
                raise ValueError("No hay piezas etiquetadas. Etiqueta antes algunas fotos en el paso 1.")
            return df, perdidas
        def listo(r):
            df, perdidas = r
            df["ok"] = df.clase.map(real_a_pred) == df.pred
            malas = df[~df.ok][["imagen", "id", "clase", "pred", "motivo", "ancho_tet", "largo_tet", "H_med", "S_med", "V_med"]].rename(
                columns={"clase": "real", "pred": "predicho"})
            malas = pd.concat([malas, perdidas.rename(columns={"clase": "real"}).assign(predicho="NO DETECTADA")], ignore_index=True)
            total = len(df) + len(perdidas)
            pintar_banner(self.resumen, "ok" if len(malas) == 0 else "aviso",
                          f"Aciertos: {(total - len(malas)) / max(total, 1):.1%}  ({total - len(malas)}/{total})   ·   Fallos: {len(malas)}")
            llenar(self.fallos, malas.fillna("").reset_index(drop=True))
        en_hilo(self.app, trabajo, listo)

    # ---------- clases ----------
    def editar_clases(self):
        w = tk.Toplevel(self, bg=C["fondo"]); w.title("Clases del sistema")
        colores = ", ".join(self.app.cfg["color"])
        ttk.Label(w, padding=8, justify="left", text=f"Una clase por línea: «ancho x largo color», con el lado menor primero (2x4 rojo).\nColores disponibles: {colores}").pack()
        t = tk.Text(w, width=28, height=12); t.pack(padx=8); t.insert("1.0", "\n".join(self.app.cfg["clases"]))
        def guardar():
            lineas = [x.strip() for x in t.get("1.0", "end").splitlines() if x.strip()]
            for x in lineas:
                m = re.fullmatch(r"(\d+)x(\d+) (\w+)", x)
                if not m or int(m[1]) > int(m[2]) or m[3] not in self.app.cfg["color"]:
                    return messagebox.showerror("Clase no válida", f"«{x}» no es válida.\nFormato: 2x4 rojo (lado menor primero; el color debe existir).", parent=w)
            guardar_config(lambda d, s: d.__setitem__("clases", lineas))
            self.app.recargar(); w.destroy()
        ttk.Button(w, text="Guardar en config.yaml", style="Ok.TButton", command=guardar).pack(pady=10)
