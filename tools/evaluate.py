"""Evaluación sobre dataset/test usando dataset/test/labels.csv (ground truth por pieza, creado con clics en la app)."""
import os, sys
from collections import Counter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from vision.acquisition import leer_imagen
from vision.etiquetas import cargar, emparejar, real_a_pred
from vision.pipeline import process, load_config, ROOT

TEST = f"{ROOT}/dataset/test"


def evaluar(cfg, progreso=None):
    """Empareja cada pieza real con la detectada más cercana. Devuelve dict: mat, met, accuracy, perdidas, falsas,
    imagenes (DataFrame), fig."""
    lab = cargar(f"{TEST}/labels.csv")
    lab = lab[lab.clase != "ignorar"]
    nombres = [n for n in lab.imagen.unique() if os.path.exists(f"{TEST}/{n}")]
    if not nombres:
        raise ValueError("No hay fotos de test etiquetadas. Añade fotos en «Anotar» y etiqueta sus piezas.")
    conf, filas_img = Counter(), []
    for i, n in enumerate(nombres):
        r = process(leer_imagen(f"{TEST}/{n}"), cfg)
        reales = lab[lab.imagen == n]
        pares, sin_real, sin_pred = emparejar(list(zip(reales.cx_px, reales.cy_px)), [(p["cx"], p["cy"]) for p in r["pieces"]],
                                              cfg["tol_emparejar_cm"] * r["px_cm"])
        c = Counter()
        for a, b in pares: c[(real_a_pred(reales.iloc[a].clase), r["pieces"][b]["label"])] += 1
        for a in sin_real: c[(real_a_pred(reales.iloc[a].clase), "PERDIDA")] += 1
        for b in sin_pred: c[("FALSA", r["pieces"][b]["label"])] += 1
        conf.update(c)
        filas_img.append({"imagen": n, "reales": len(reales), "detectadas": len(r["pieces"]),
                          "aciertos": sum(v for (a, b), v in c.items() if a == b), "perdidas": len(sin_real), "falsas": len(sin_pred)})
        if progreso: progreso(i + 1, len(nombres))
    filas = sorted({a for a, _ in conf} - {"FALSA"}); cols = sorted({b for _, b in conf} - {"PERDIDA"})
    mat = pd.DataFrame([[conf[(a, b)] for b in cols + ["PERDIDA"]] for a in filas + ["FALSA"]],
                       index=filas + ["FALSA"], columns=cols + ["PERDIDA"])
    tp = {k: conf[(k, k)] for k in filas}
    met = pd.DataFrame({"precision": {k: tp[k] / max(mat[k].sum(), 1) if k in mat else 0 for k in filas},
                        "recall": {k: tp[k] / max(mat.loc[k].sum(), 1) for k in filas}}).round(3)
    fig, ax = plt.subplots(figsize=(10, 8)); ax.imshow(mat.values, cmap="Blues")
    ax.set_xticks(range(len(mat.columns)), mat.columns, rotation=60, ha="right"); ax.set_yticks(range(len(mat)), mat.index)
    for (i, j), v in pd.DataFrame(mat.values).stack().items(): ax.text(j, i, v, ha="center", va="center")
    ax.set_xlabel("predicha"); ax.set_ylabel("real"); ax.set_title("Matriz de confusión (exacta, emparejada por posición)")
    fig.tight_layout()
    total = mat.loc[filas].values.sum()
    return {"mat": mat, "met": met, "accuracy": sum(tp.values()) / max(total, 1), "perdidas": int(mat["PERDIDA"].sum()),
            "falsas": int(mat.loc["FALSA"].sum()), "imagenes": pd.DataFrame(filas_img), "fig": fig}


def exportar(res, carpeta):
    """CSV + PNG para el informe."""
    os.makedirs(carpeta, exist_ok=True)
    res["mat"].to_csv(f"{carpeta}/confusion.csv"); res["met"].to_csv(f"{carpeta}/metricas.csv")
    res["imagenes"].to_csv(f"{carpeta}/por_imagen.csv", index=False)
    res["fig"].savefig(f"{carpeta}/confusion.png", dpi=120)
    open(f"{carpeta}/resumen.txt", "w", encoding="utf-8").write(
        f"Accuracy: {res['accuracy']:.3f}\nPiezas perdidas: {res['perdidas']}\nFalsas: {res['falsas']}\n")


if __name__ == "__main__":
    r = evaluar(load_config())
    print(r["met"].to_string(), f"\nAccuracy: {r['accuracy']:.3f} | perdidas: {r['perdidas']} | falsas: {r['falsas']}")
    exportar(r, f"{ROOT}/results")
