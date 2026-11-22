"""Lectura/edición de umbrales de config.yaml (nombres planos) y guardado conservando comentarios."""
import os, shutil
from .pipeline import ROOT

RUTAS = {"tol_tetones": ("tipo", "tol_tetones"), "rect_min": ("tipo", "rect_min"), "d_tapete_min": ("tipo", "d_tapete_min"), "k_perspectiva": ("tipo", "k_perspectiva"), "ancho_imagen_cm": ("ancho_imagen_cm",)}
LIMITES = ("v_max", "v_min", "s_max", "s_min")
ETIQ = {"v_max": "V máx", "v_min": "V mín", "s_max": "S máx", "s_min": "S mín", "h_lo": "H desde", "h_hi": "H hasta"}


def _get(d, ruta):
    for k in ruta: d = d[k]
    return d


def etiqueta(k):
    """Nombre legible de un umbral plano: 'rojo_s_min' -> 'Rojo: S mín'."""
    base = {"tol_tetones": "Tolerancia (tetones)", "rect_min": "Rectangularidad mín.", "d_tapete_min": "Ángulo al tapete mín. (°)", "k_perspectiva": "Corrección de perspectiva", "ancho_imagen_cm": "Ancho de la foto (cm)"}
    if k in base: return base[k]
    c, suf = k.split("_", 1)
    return f"{c.capitalize()}: {ETIQ[suf]}"


def a_plano(cfg):
    """Umbrales editables como {nombre: valor}. Rango de tono: lo > hi = da la vuelta (rojo 170..10)."""
    p = {k: _get(cfg, r) for k, r in RUTAS.items()}
    for c, r in cfg["color"].items():
        p.update({f"{c}_{k}": r[k] for k in LIMITES if k in r})
        if "h" in r:
            h = r["h"]
            p[f"{c}_h_lo"], p[f"{c}_h_hi"] = (h[1][0], h[0][1]) if len(h) == 2 else (h[0][0], h[0][1])
    return p


def aplicar_plano(cfg, plano, seq=list):
    """Escribe {nombre: valor} en cfg (dict anidado). `seq` crea las listas (flow-style al guardar)."""
    for k, v in plano.items():
        if k in RUTAS:
            _get(cfg, RUTAS[k][:-1])[RUTAS[k][-1]] = v
    for c, r in cfg["color"].items():
        for k in LIMITES:
            if f"{c}_{k}" in plano and k in r:
                r[k] = plano[f"{c}_{k}"]
        if f"{c}_h_lo" in plano and "h" in r:
            lo, hi = int(plano[f"{c}_h_lo"]), int(plano[f"{c}_h_hi"])
            r["h"] = seq([seq([lo, hi])] if lo <= hi else [seq([0, hi]), seq([lo, 180])])


def leer(cfg, k):
    """Valor de un ajuste: nombre plano (str) o ruta anidada (tupla, índices enteros incluidos)."""
    return a_plano(cfg)[k] if isinstance(k, str) else _get(cfg, k)


def escribir(cfg, k, v, seq=list):
    if isinstance(k, str):
        p = a_plano(cfg); p[k] = v; aplicar_plano(cfg, p, seq)
    else:
        _get(cfg, k[:-1])[k[-1]] = v


def guardar_config(mutador, path=None):
    """Aplica `mutador(data, seq)` sobre config.yaml conservando comentarios (ruamel) y deja copia .bak."""
    from ruamel.yaml import YAML
    from ruamel.yaml.comments import CommentedSeq
    path = path or os.path.join(ROOT, "config.yaml")
    def seq(x):
        s = CommentedSeq(x); s.fa.set_flow_style(); return s
    y = YAML(); y.preserve_quotes = True
    with open(path, encoding="utf-8") as f: data = y.load(f)
    mutador(data, seq)
    shutil.copy(path, path + ".bak")
    with open(path, "w", encoding="utf-8") as f: y.dump(data, f)
