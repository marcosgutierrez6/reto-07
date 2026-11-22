"""Gráficas y umbrales sugeridos a partir de piezas etiquetadas (df de vision.etiquetas.medir_etiquetadas)."""
import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np, pandas as pd
from matplotlib.patches import Rectangle
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from vision.config_io import a_plano
from vision.decision_tree import _cumple

PAL = {"rojo": "red", "azul": "royalblue", "amarillo": "gold", "blanco": "lightgray", "gris": "gray",
       "negro": "black", "beige": "tan", "marron": "saddlebrown"}


def circ(h):
    """Media y desviación CIRCULARES del tono (OpenCV 0-179)."""
    a = np.asarray(h, float) * np.pi / 90
    c, s = np.cos(a).mean(), np.sin(a).mean()
    R = min(np.hypot(c, s), 1.0)
    return (np.arctan2(s, c) * 90 / np.pi) % 180, np.sqrt(max(0.0, -2 * np.log(max(R, 1e-9)))) * 90 / np.pi


def por_color(df):
    """{color: {H|S|V: (media, desviación)}} con H circular. Desviación mínima 0.5 (evita dividir por 0)."""
    out = {}
    for c, g in df.groupby("color"):
        mh, sh = circ(g.H_med)
        out[c] = {"H": (mh, max(sh, .5)), "S": (g.S_med.mean(), max(g.S_med.std(ddof=0), .5)),
                  "V": (g.V_med.mean(), max(g.V_med.std(ddof=0), .5))}
    return out


def preparar(df, cfg):
    """Separa las filas etiquetadas: (válidas con 'color', intrusas, ignoradas/sombras, filas extra para estadística de color).
    Las intrusas NEUTRAS (S baja, p. ej. la 1x3 blanca) son la referencia del color «blanco» frente al gris."""
    v = df[df.clase.isin(cfg["clases"])].assign(color=lambda d: d.clase.str.split().str[1])
    intr, ign = df[df.clase == "intrusa"], df[df.clase == "ignorar"]
    smax = a_plano(cfg).get("gris_s_max", 45)
    extra = intr[intr.S_med <= smax].assign(color="blanco") if "blanco" in cfg["color"] else intr.iloc[:0].assign(color="")
    return v, intr, ign, extra


def sugerir(df, cfg, extra=None):
    """{umbral: (valor, margen_σ_abajo, margen_σ_arriba)}. S y V: punto medio entre la clase de color propia y su vecina
    (entre las que la regla debe separar). H: punto medio hacia la vecina cromática más próxima (±5 a ±15)."""
    df = df.assign(color=df.clase.str.split().str[1])
    st, sug, reglas = por_color(df if extra is None else pd.concat([df, extra])), {}, list(cfg["color"].items())
    en = lambda r, d: bool(_cumple(r, st[d]["H"][0], st[d]["S"][0], st[d]["V"][0]))     # ¿la media de la clase d cumple r?

    def candidatas(c, omite):
        """Clases con las que `c` se puede confundir en este umbral: pasan el resto de la regla de c, no las captura
        antes una regla anterior del orden y, si c es cromático, tienen un tono parecido (±30) o son neutras."""
        i = [n for n, _ in reglas].index(c)
        resto = {k: v for k, v in reglas[i][1].items() if k not in (omite, "h")}
        cand = [d for d in st if d != c and en(resto, d) and not any(en(r, d) for _, r in reglas[:i])]
        if "h" in cfg["color"][c] and omite != "h":
            dh = lambda d: abs(((st[d]["H"][0] - st[c]["H"][0] + 90) % 180) - 90)
            cand = [d for d in cand if "h" not in cfg["color"].get(d, {}) or dh(d) <= 30]
        return cand

    for c, regla in reglas:
        if c not in st or len(st) < 2: continue
        for k in ("v_max", "v_min", "s_max", "s_min"):
            if k not in regla: continue
            f = k[0].upper()
            cand = candidatas(c, k)
            mc, sc = st[c][f]
            if k.endswith("max"):                                          # c queda abajo, el vecino arriba
                v = [d for d in cand if st[d][f][0] > mc]
                if v:
                    md, sd = st[min(v, key=lambda d: st[d][f][0])][f]; mid = (mc + md) / 2
                    sug[f"{c}_{k}"] = (mid, (mid - mc) / sc, (md - mid) / sd)
            else:                                                          # c queda arriba, el vecino abajo
                v = [d for d in cand if st[d][f][0] < mc]
                if v:
                    md, sd = st[max(v, key=lambda d: st[d][f][0])][f]; mid = (mc + md) / 2
                    sug[f"{c}_{k}"] = (mid, (mid - md) / sd, (mc - mid) / sc)
    for c in [c for c, r in reglas if "h" in r and c in st]:
        mu, sd = st[c]["H"]
        d = {o: ((st[o]["H"][0] - mu + 90) % 180) - 90 for o in candidatas(c, "h")}   # distancia con signo en la rueda
        for lado, vec, signo in (("hi", {o: x for o, x in d.items() if x > 3}, 1), ("lo", {o: x for o, x in d.items() if x < -3}, -1)):
            if vec:
                o = min(vec, key=lambda o: abs(vec[o])); dist = abs(vec[o])
                mitad = min(max(dist / 2, 5), 15); m_own, m_ot = mitad / sd, (dist - mitad) / st[o]["H"][1]
            else:
                mitad, m_own, m_ot = 15, 15 / sd, None
            sug[f"{c}_h_{lado}"] = ((mu + signo * mitad) % 180, *((m_own, m_ot) if lado == "hi" else (m_ot, m_own)))
    dev = np.maximum((df.ancho_tet - df.ancho_tet.round()).abs(), (df.largo_tet - df.largo_tet.round()).abs())
    mid = (dev.max() + .5) / 2
    sug["tol_tetones"] = (mid, (mid - dev.mean()) / max(dev.std(ddof=0), .01), None)
    sug["rect_min"] = (df.rectangularidad.min() * .95, None, None)
    sug["d_tapete_min"] = (df.dist_tapete.quantile(.05) * .5, None, None)       # la mitad de lo que se separan las piezas del tapete
    sin = df[~df.marcadores.astype(bool)].dropna(subset=["ancho_tet_bruto", "g_ancho"])   # sin marcadores: escala y perspectiva por mínimos cuadrados
    if len(sin):
        dim = sin.clase.str.split().str[0].str.split("x", expand=True).astype(int)
        n = np.r_[dim[1].values, dim[0].values].astype(float)                         # tetones reales: largo, ancho
        bruto = np.r_[sin.largo_tet_bruto.values, sin.ancho_tet_bruto.values]          # lo medido sin corregir
        g = np.r_[sin.g_largo.values, sin.g_ancho.values]
        # modelo: medido = real * s + k * g  (s = error de escala, k = paredes vistas de lado)
        if g.max() > .05:
            s, k = np.linalg.lstsq(np.c_[n, g], bruto, rcond=None)[0]
            sug["k_perspectiva"] = (float(np.clip(k / s, 0, 1.5)), None, None)         # k en unidades de la escala nueva
        else:
            s = float((bruto * n).sum() / (n * n).sum())
        sug["ancho_imagen_cm"] = (a_plano(cfg)["ancho_imagen_cm"] / s, None, None)    # medidas s veces grandes -> la foto abarca s veces menos cm
    return {k: (round(float(v[0]), 2), *(None if m is None else round(float(m), 1) for m in v[1:])) for k, v in sug.items()}


def _lineas(ax, eje, claves, act, sug):
    f = ax.axvline if eje == "x" else ax.axhline
    for k in claves:
        if k in act: f(act[k], color="k", ls="--", lw=1)          # actual: negro discontinuo
        if k in sug: f(sug[k][0], color="r", ls=":", lw=1.6)      # sugerido: rojo punteado


def _puntos(ax, x, y, v, intr, ign):
    """Piezas válidas (color de su clase), intrusas (rombo) y falsas detecciones/sombras (cruz gris)."""
    for cl, g in v.groupby("clase"):
        ax.scatter(g[x], g[y], s=28, label=cl, color=PAL.get(cl.split()[1]), edgecolor="k", lw=.4)
    if len(intr): ax.scatter(intr[x], intr[y], s=60, marker="D", facecolor="white", edgecolor="m", lw=1.5, label="intrusa")
    if len(ign): ax.scatter(ign[x], ign[y], s=40, marker="x", color="dimgray", label="falsa/sombra")


def analizar(df, cfg):
    """df: piezas etiquetadas (válidas + intrusa + ignorar). Devuelve ({nombre: figura}, sugeridos, texto)."""
    v, intr, ign, extra = preparar(df, cfg)
    if v.empty:
        raise ValueError("No hay piezas etiquetadas con una de las clases. Etiqueta antes algunas fotos.")
    act, sug = a_plano(cfg), sugerir(v, cfg, extra)
    ks = lambda suf: [k for k in act if k.endswith(suf)]
    figs = {}
    fig, ax = plt.subplots(figsize=(7, 7))                         # 1) ancho vs largo (tetones)
    _puntos(ax, "ancho_tet", "largo_tet", v, intr, ign.iloc[:0])
    for cl in v.clase.unique():
        a, l = map(int, cl.split()[0].split("x"))
        for tol, kw in ((act["tol_tetones"], dict(ec="k", ls="--")), (sug["tol_tetones"][0], dict(ec="r", ls=":"))):
            ax.add_patch(Rectangle((a - tol, l - tol), 2 * tol, 2 * tol, fill=False, **kw))
    ax.set_xticks(range(0, int(v.ancho_tet.max()) + 2)); ax.set_yticks(range(0, int(v.largo_tet.max()) + 2)); ax.grid(alpha=.3)
    ax.set_xlabel("ancho (tetones)"); ax.set_ylabel("largo (tetones)"); ax.legend(fontsize=7)
    ax.set_title("Los puntos deben caer cerca de los enteros\ncuadro negro: tolerancia actual · rojo: sugerida")
    figs["ancho_vs_largo"] = fig
    PLANOS = (("H_vs_S", "H_med", "S_med", ks("_h_lo") + ks("_h_hi"), ks("_s_min") + ks("_s_max"), "H vs S"),
              ("S_vs_V", "S_med", "V_med", ks("_s_min") + ks("_s_max"), ks("_v_min") + ks("_v_max"),
               "S vs V: negro / gris / blanco (intrusa) / sombra"),
              ("V_vs_H", "H_med", "V_med", ks("_h_lo") + ks("_h_hi"), ks("_v_min") + ks("_v_max"), "V vs H: rojo frente a marrón"),
              ("L_vs_a", "a_med", "L_med", [], [], "L vs a (Lab): rojo frente a marrón"))
    for nombre, x, y, ejx, ejy, titulo in PLANOS:
        fig, ax = plt.subplots(figsize=(8, 6))
        _puntos(ax, x, y, v, intr, ign)
        _lineas(ax, "x", ejx, act, sug); _lineas(ax, "y", ejy, act, sug)
        ax.set_xlabel(x.replace("_med", "") + " (mediana)"); ax.set_ylabel(y.replace("_med", "") + " (mediana)")
        ax.legend(fontsize=7, ncol=2); ax.grid(alpha=.3)
        ax.set_title(titulo + ("\numbrales: actual (negro) · sugerido (rojo)" if ejx or ejy else ""))
        figs[nombre] = fig
    for fig in figs.values(): fig.tight_layout()
    txt = []
    for cl, g in v.groupby("clase"):
        mu, sd = circ(g.H_med)
        txt.append(f"{cl:14s} n={len(g):3d} ancho={g.ancho_tet.mean():.2f}±{g.ancho_tet.std(ddof=0):.2f} "
                   f"largo={g.largo_tet.mean():.2f}±{g.largo_tet.std(ddof=0):.2f} tet | H={mu:5.1f}±{sd:4.1f}(circ) "
                   f"S={g.S_med.mean():5.1f}±{g.S_med.std(ddof=0):4.1f} V={g.V_med.mean():5.1f}±{g.V_med.std(ddof=0):4.1f}")
    txt.append(f"\nintrusas: {len(intr)} · falsas/sombras etiquetadas: {len(ign)}")
    return figs, sug, "\n".join(txt)


def exportar_figuras(figs, carpeta):
    os.makedirs(carpeta, exist_ok=True)
    for n, f in figs.items(): f.savefig(os.path.join(carpeta, n + ".png"), dpi=130)
