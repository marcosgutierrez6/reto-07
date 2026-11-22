"""7. Árbol de decisión EXPLÍCITO (sin entrenar). Todos los umbrales están en config.yaml."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _cumple(r, h, s, v):
    """Una regla de color se cumple si se cumplen TODAS sus condiciones (v_max, v_min, s_max, s_min, h).
    Vale para escalares y para matrices (máscaras)."""
    ok = np.ones(np.shape(h), bool)
    if "v_max" in r: ok &= v < r["v_max"]
    if "v_min" in r: ok &= v >= r["v_min"]
    if "s_max" in r: ok &= s <= r["s_max"]
    if "s_min" in r: ok &= s >= r["s_min"]
    if "h" in r: ok &= np.any([(h >= lo) & (h <= hi) for lo, hi in r["h"]], axis=0)
    return ok


def regla_mascara(hsv, r):
    """Máscara (0/255) de los píxeles HSV que cumplen una regla de color (para el ajuste con sliders)."""
    return (_cumple(r, hsv[..., 0].astype(int), hsv[..., 1].astype(int), hsv[..., 2].astype(int)) * 255).astype(np.uint8)


def color_de(f, cfg):
    """Rama de COLOR: reglas en el orden de config.yaml. Devuelve (color | None, motivo | None)."""
    h, sat, v = f["H_med"], f["S_med"], f["V_med"]
    for nombre, r in cfg["color"].items():
        if _cumple(r, h, sat, v):
            if nombre not in {c.split()[1] for c in cfg["clases"]}:
                return nombre, f"color {nombre} fuera de la lista"
            return nombre, None
    return None, f"color no reconocido (H={h:.0f} S={sat:.0f} V={v:.0f})"      # ninguna regla con margen: no forzamos


def tipo_de(f, cfg):
    """Rama de TIPO: ancho y largo en tetones casi enteros -> 'menor x mayor'. Devuelve (tipo | None, motivo | None).
    Si el tipo es entero pero no está en `tipos` se devuelve igualmente (para el inventario) con su motivo."""
    t, a, l = cfg["tipo"], f["ancho_tet"], f["largo_tet"]
    if f["rectangularidad"] < t["rect_min"]:
        return None, f"forma no rectangular (rect. {f['rectangularidad']:.2f} < {t['rect_min']}): ¿piezas pegadas o sombra?"
    if round(a) < 1 or abs(a - round(a)) > t["tol_tetones"] or abs(l - round(l)) > t["tol_tetones"]:
        return None, f"medidas {a:.2f}×{l:.2f} tetones: no son enteros (±{t['tol_tetones']})"
    tipo = f"{round(a)}x{round(l)}"
    return tipo, (None if tipo in cfg["tipos"] else f"tipo {tipo} no permitido")


def classify(f, cfg):
    """Devuelve (tipo, color, etiqueta, motivo). Etiqueta = clase de config.yaml; si no, DESCONOCIDO y el motivo."""
    (tipo, m1), (color, m2) = tipo_de(f, cfg), color_de(f, cfg)
    clase = f"{tipo} {color}"
    if tipo and not m1 and color and not m2 and clase in cfg["clases"]:
        return tipo, color, clase, ""
    motivos = [m for m in (m1, m2) if m] or [f"la combinación {clase} no existe en la colección"]
    return tipo or "?", color or "?", "DESCONOCIDO", "; ".join(motivos)


def _texto_regla(r):
    t = []
    if "v_max" in r: t.append(f"V < {r['v_max']}")
    if "s_max" in r: t.append(f"S ≤ {r['s_max']}")
    if "v_min" in r: t.append(f"V ≥ {r['v_min']}")
    if "h" in r: t.append("H ∈ " + " ∪ ".join(f"[{a},{b}]" for a, b in r["h"]))
    if "s_min" in r: t.append(f"S ≥ {r['s_min']}")
    txt = " y ".join(t)
    return txt if len(txt) <= 30 else " y\n".join(t)      # condiciones en varias líneas si es largo


def _cadena(items, final):
    """Árbol en cadena: cada pregunta lleva a una hoja por una rama y a la siguiente pregunta por la otra."""
    paso = min(0.2, 0.95 / (len(items) + 1))
    nodos, aristas = {}, []
    for i, (q, hoja, rama) in enumerate(items):
        nodos[f"q{i}"], nodos[f"h{i}"] = (.3, .95 - i * paso, q), (.8, .95 - i * paso, hoja)
        aristas += [(f"q{i}", f"h{i}", rama), (f"q{i}", f"q{i+1}" if i + 1 < len(items) else "fin", "no" if rama == "sí" else "sí")]
    nodos["fin"] = (.3, .95 - len(items) * paso, final)
    return nodos, aristas


def _dibuja(ax, nodes, edges, titulo):
    hojas = set(nodes) - {a for a, _, _ in edges}
    cajas = {k: ax.text(x, y, txt, ha="center", va="center", fontsize=9,
                        bbox=dict(boxstyle="round", fc="lightgreen" if k in hojas else "lightyellow"))
             for k, (x, y, txt) in nodes.items()}
    for a, b, l in edges:                    # la flecha se recorta en el borde real de cada recuadro
        (xa, ya), (xb, yb) = nodes[a][:2], nodes[b][:2]
        ax.annotate("", xy=(xb, yb), xytext=(xa, ya), arrowprops=dict(
            arrowstyle="->", shrinkA=0, shrinkB=0, patchA=cajas[a].get_bbox_patch(), patchB=cajas[b].get_bbox_patch()))
        ax.text((xa + xb) / 2, (ya + yb) / 2, l, fontsize=9, color="red", ha="center", va="center",
                bbox=dict(fc="white", ec="none", pad=1))
    ax.set_title(titulo); ax.axis("off"); ax.set_xlim(-0.1, 1.1); ax.set_ylim(-0.05, 1.05)


def draw_tree(cfg, path):
    """Dibuja el árbol (característica + umbral de cada nodo) leyendo config.yaml."""
    t = cfg["tipo"]
    color = _cadena([(_texto_regla(r), n, "sí") for n, r in cfg["color"].items()], "DESCONOCIDO (color)")
    tipo = _cadena([(f"ángulo (a,b) al tapete ≥ {t['d_tapete_min']}°\no forma y tamaño de pieza válidos", "sombra: se ignora", "no"),
                    (f"rectangularidad ≥ {t['rect_min']}", "DESCONOCIDO (forma)", "no"),
                    (f"ANCHO en tetones ({t['teton_cm']} cm)\na ±{t['tol_tetones']} de un entero", "DESCONOCIDO (medida)", "no"),
                    (f"LARGO en tetones\na ±{t['tol_tetones']} de un entero", "DESCONOCIDO (medida)", "no"),
                    ("tipo (menor×mayor) ∈\n{" + ", ".join(cfg["tipos"]) + "}", "DESCONOCIDO (tipo)", "no"),
                    (f"tipo + color ∈ las {len(cfg['clases'])} clases", "DESCONOCIDO (combinación)", "no")], "CLASE (p. ej. 2x6 rojo)")
    fig, ax = plt.subplots(1, 2, figsize=(16, 8))
    _dibuja(ax[0], *color, "1) V/S: negro · blanco · gris   2) tono: amarillo · azul · rojo-marrón   3) rojo vs marrón\n(H circular; evaluado en orden)")
    _dibuja(ax[1], *tipo, "4) ancho → largo → tipo permitido → clase")
    fig.tight_layout(); fig.savefig(path, dpi=120); plt.close(fig)
