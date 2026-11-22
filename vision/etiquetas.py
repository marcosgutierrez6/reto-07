"""Etiquetas de piezas (labels.csv) compartidas por Calibración y Evaluar."""
import os
import numpy as np, pandas as pd

FEATURES = ["ancho_cm", "largo_cm", "ancho_tet", "largo_tet", "area_cm2", "aspect", "rectangularidad",
            "H_med", "S_med", "V_med", "L_med", "a_med", "b_med", "dist_tapete",
            "ancho_tet_bruto", "largo_tet_bruto", "g_ancho", "g_largo"]
COLUMNAS = ["imagen", "id", "cx_px", "cy_px", "cx_cm", "cy_cm", "clase", "propuesta", "px_cm", "marcadores"] + FEATURES
ESPECIALES = ("intrusa", "ignorar")      # intrusa = pieza que NO es de ninguna clase; ignorar = falsa detección


def cargar(path):
    """labels.csv como DataFrame (vacío pero con columnas numéricas bien tipadas si aún no existe)."""
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame(columns=COLUMNAS).astype({c: float for c in ["id", "cx_px", "cy_px", "cx_cm", "cy_cm", "px_cm"] + FEATURES})


def propuesta(p):
    """Clase propuesta por el árbol para la pieza `p` (DESCONOCIDO se etiqueta como intrusa)."""
    return "intrusa" if p["label"] == "DESCONOCIDO" else p["label"]


def real_a_pred(clase):
    """Una intrusa se acierta cuando el sistema responde DESCONOCIDO."""
    return "DESCONOCIDO" if clase == "intrusa" else clase


def fila(imagen, p, px_cm, marcadores, clase):
    """Fila de labels.csv: etiqueta + centroide + todas las medidas de la pieza."""
    return {"imagen": imagen, "id": p["id"], "cx_px": p["cx"], "cy_px": p["cy"], "cx_cm": p["cx"] / px_cm,
            "cy_cm": p["cy"] / px_cm, "clase": clase, "propuesta": propuesta(p), "px_cm": px_cm,
            "marcadores": bool(marcadores), **{k: p[k] for k in FEATURES}}


def emparejar(reales, preds, tol):
    """Empareja puntos (x, y) reales con detectados, de menor a mayor distancia (< tol px).
    Devuelve (pares (i, j), reales sin pareja, detectados sin pareja)."""
    cand = sorted((np.hypot(a[0] - b[0], a[1] - b[1]), i, j) for i, a in enumerate(reales) for j, b in enumerate(preds))
    ui, uj, pares = set(), set(), []
    for d, i, j in cand:
        if d <= tol and i not in ui and j not in uj:
            ui.add(i); uj.add(j); pares.append((i, j))
    return pares, [i for i in range(len(reales)) if i not in ui], [j for j in range(len(preds)) if j not in uj]


def medir_etiquetadas(cfg, carpeta, progreso=None, incluir_ignoradas=False):
    """Vuelve a procesar las fotos de `carpeta` con el cfg dado y empareja cada pieza detectada con su etiqueta.
    Devuelve (df con clase real, predicción y medidas actuales, df de piezas etiquetadas no detectadas)."""
    from .acquisition import leer_imagen
    from .pipeline import process
    lab = cargar(os.path.join(carpeta, "labels.csv"))
    if not incluir_ignoradas:
        lab = lab[lab.clase != "ignorar"]
    filas, perdidas, nombres = [], [], list(lab.imagen.unique())
    for n, nombre in enumerate(nombres):
        ruta = os.path.join(carpeta, nombre)
        if not os.path.exists(ruta): continue
        r = process(leer_imagen(ruta), cfg)
        reales = lab[lab.imagen == nombre]
        pares, sin_real, _ = emparejar(list(zip(reales.cx_px, reales.cy_px)), [(p["cx"], p["cy"]) for p in r["pieces"]],
                                       cfg["tol_emparejar_cm"] * r["px_cm"])
        for i, j in pares:
            p = r["pieces"][j]
            filas.append({"imagen": nombre, "id": p["id"], "clase": reales.iloc[i].clase, "pred": p["label"], "motivo": p["motivo"],
                          "px_cm": r["px_cm"], "marcadores": r["marcadores"], **{k: p[k] for k in FEATURES}})
        perdidas += [{"imagen": nombre, "clase": reales.iloc[i].clase} for i in sin_real]
        if progreso: progreso(n + 1, len(nombres))
    return pd.DataFrame(filas), pd.DataFrame(perdidas, columns=["imagen", "clase"])
