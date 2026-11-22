"""Utilidades comunes de la interfaz: visor de imágenes, hilos con barra de progreso, errores amigables."""
import base64, os, queue, shutil, threading, traceback
import tkinter as tk
from tkinter import messagebox
import cv2, numpy as np
from vision.pipeline import ROOT
from vision.acquisition import es_heic, leer_imagen  # noqa: F401  (leer_imagen se reexporta para la GUI)


def fig_a_bgr(fig):
    """Figura de matplotlib (backend Agg) -> imagen BGR para el visor."""
    fig.canvas.draw()
    return cv2.cvtColor(np.asarray(fig.canvas.buffer_rgba()), cv2.COLOR_RGBA2BGR)


def clases(cfg):
    """(tipos, colores) leídos de config.yaml."""
    return list(cfg["tipo"]["area_ref"]), [k for k, v in cfg["color"].items() if isinstance(v, (list, dict))]


def copiar_unico(origen, carpeta):
    """Copia un archivo a `carpeta` sin pisar otro con el mismo nombre. Las fotos HEIC (iPhone) se convierten a PNG."""
    os.makedirs(carpeta, exist_ok=True)
    nombre, ext = os.path.splitext(os.path.basename(origen))
    heic = es_heic(origen)
    if heic: ext = ".png"
    destino, n = os.path.join(carpeta, nombre + ext), 1
    while os.path.exists(destino):
        destino, n = os.path.join(carpeta, f"{nombre}_{n}{ext}"), n + 1
    if heic:
        cv2.imencode(".png", leer_imagen(origen))[1].tofile(destino)     # tofile: vale con rutas con acentos
    else:
        shutil.copy(origen, destino)
    return destino


def llenar(tree, df, indice=None):
    """Rellena un ttk.Treeview con un DataFrame (el índice sale como primera columna si se da `indice`)."""
    tree.delete(*tree.get_children())
    cols = ([indice] if indice else []) + [str(c) for c in df.columns]
    tree["columns"], tree["show"] = cols, "headings"
    for c in cols:
        tree.heading(c, text=c); tree.column(c, width=70, anchor="center")
    for i, fila in df.iterrows():
        tree.insert("", "end", values=([i] if indice else []) + [round(v, 3) if isinstance(v, float) else v for v in fila])


def error_amigable(e):
    if isinstance(e, ValueError):
        return str(e)
    if isinstance(e, FileNotFoundError):
        return f"No se encuentra el archivo o la carpeta: {e.filename}"
    if isinstance(e, PermissionError):
        return "No hay permiso para leer o escribir ese archivo. ¿Está abierto en otro programa?"
    return f"Ha ocurrido un problema inesperado ({type(e).__name__}). Los detalles están en results/error.log."


def mostrar_error(e, parent=None):
    if not isinstance(e, (ValueError, FileNotFoundError, PermissionError)):    # el traceback va a un log, no a pantalla
        os.makedirs(f"{ROOT}/results", exist_ok=True)
        with open(f"{ROOT}/results/error.log", "a", encoding="utf-8") as f:
            traceback.print_exception(e, file=f)
    messagebox.showerror("No se ha podido completar la acción", error_amigable(e), parent=parent)


def en_hilo(app, trabajo, listo, msg="Procesando…"):
    """Ejecuta trabajo(progreso) en un hilo (la ventana no se congela) y llama a listo(resultado) en el hilo
    principal. progreso(i, n) mueve la barra; sin progreso la barra es indeterminada."""
    q, barra = queue.Queue(), app.barra

    def run():
        try:
            q.put(("ok", trabajo(lambda i, n: q.put(("p", (i, n))))))
        except Exception as e:
            q.put(("err", e))

    app.estado.set(msg); barra.configure(mode="indeterminate", value=0); barra.start(12)
    threading.Thread(target=run, daemon=True).start()

    def sondear():
        try:
            while True:
                t, v = q.get_nowait()
                if t == "p":
                    barra.stop(); barra.configure(mode="determinate", maximum=v[1], value=v[0])
                    continue
                barra.stop(); barra.configure(mode="determinate", value=0)
                app.estado.set("Hubo un problema" if t == "err" else "Listo ✔")
                mostrar_error(v, app) if t == "err" else listo(v)
                return
        except queue.Empty:
            app.after(80, sondear)
    sondear()


class ImageView(tk.Canvas):
    """Muestra una imagen BGR ajustada al tamaño disponible. Con on_click(x, y, 'izq'|'der') devuelve
    las coordenadas de clic en píxeles de la imagen original."""

    def __init__(self, parent, on_click=None, hint="", **kw):
        super().__init__(parent, bg="#1f2937", highlightthickness=0, **kw)
        self.hint = hint
        self.img, self.on_click, self._foto, self.k, self.off, self._job = None, on_click, None, 1.0, (0, 0), None
        self.bind("<Configure>", self._cambio_tamano)
        if on_click:
            for b in (1, 2, 3):                 # en Mac el botón derecho es el 2
                self.bind(f"<Button-{b}>", self._clic)

    def mostrar(self, bgr):
        self.img = bgr
        self._pintar()

    def _cambio_tamano(self, _):
        if self._job: self.after_cancel(self._job)
        self._job = self.after(40, self._pintar)

    def _pintar(self):
        if self.winfo_width() < 20 or self.winfo_height() < 20:
            return
        if self.img is None:                                  # vacío: mensaje de ayuda centrado
            self.delete("all")
            self.create_text(self.winfo_width() / 2, self.winfo_height() / 2, text=self.hint, fill="#9ca3af",
                             font=("", 14), justify="center", width=max(self.winfo_width() - 60, 100))
            return
        W, H, (h, w) = self.winfo_width(), self.winfo_height(), self.img.shape[:2]
        self.k = min(W / w, H / h)
        im = cv2.resize(self.img, (max(1, int(w * self.k)), max(1, int(h * self.k))), interpolation=cv2.INTER_AREA)
        self.off = ((W - im.shape[1]) / 2, (H - im.shape[0]) / 2)
        self._foto = tk.PhotoImage(data=base64.b64encode(cv2.imencode(".png", im, [cv2.IMWRITE_PNG_COMPRESSION, 1])[1].tobytes()))
        self.delete("all")
        self.create_image(*self.off, image=self._foto, anchor="nw")

    def _clic(self, e):
        if self.img is None: return
        x, y, (h, w) = (e.x - self.off[0]) / self.k, (e.y - self.off[1]) / self.k, self.img.shape[:2]
        if 0 <= x < w and 0 <= y < h:
            self.on_click(x, y, "izq" if e.num == 1 else "der")
