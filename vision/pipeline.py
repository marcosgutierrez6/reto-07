"""Une todas las etapas: imagen -> piezas clasificadas + imágenes intermedias."""
import os, sys, cv2, numpy as np, yaml
from .calibration import calibrate
from .preprocessing import preprocess
from .segmentation import segment, detect
from .features import extract
from .decision_tree import classify, tipo_de
from .visualization import annotate

# Con el .exe (PyInstaller) config.yaml, dataset/ y results/ viven junto al ejecutable, fuera de él
ROOT = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
        else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_config(path=None):
    return yaml.safe_load(open(path or os.path.join(ROOT, "config.yaml")))


def row(p):
    """Pieza sin objetos de OpenCV (para CSV)."""
    return {k: v for k, v in p.items() if not k.startswith("_")}


def avisos(img, quad, px_cm, pieces, grandes, rect_shape, cfg, sombras=0):
    """Lista de avisos en español: piezas cortadas por el borde, objetos fuera del cuadrado,
    objetos demasiado grandes (piezas pegadas) y piezas DESCONOCIDO."""
    av, (H, W) = [], rect_shape[:2]
    for p in pieces:        # pieza cuyo rectángulo toca el borde de la imagen rectificada
        x, y, w, h = cv2.boundingRect(p["_contour"])
        p["_borde"] = x <= 2 or y <= 2 or x + w >= W - 2 or y + h >= H - 2
    if (b := [p["id"] for p in pieces if p["_borde"]]):
        av.append(f"Pieza(s) {b} tocan el borde del cuadrado de marcadores: pueden estar cortadas.")
    if quad is not None:    # objetos en la franja exterior al cuadrado (la homografía los recorta)
        hsv_o = preprocess(img, cfg)[1]
        mask = segment(hsv_o, cfg)[1]
        poly = np.zeros(mask.shape, np.uint8)
        cv2.fillConvexPoly(poly, quad.astype(np.int32), 255)
        r = int(cfg["margen_fuera_cm"] * px_cm)
        anillo = cv2.dilate(poly, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1,) * 2)) & ~poly
        fuera, _ = cv2.findContours(mask & anillo, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        n = sum(cv2.contourArea(c) / px_cm ** 2 >= cfg["area_min_cm2"] for c in fuera)
        if n:
            av.append(f"{n} objeto(s) fuera del cuadrado de marcadores: no se analizan.")
    def toca_borde(c):
        x, y, w, h = cv2.boundingRect(c)
        return x <= 2 or y <= 2 or x + w >= W - 2 or y + h >= H - 2
    if (g := [c for c in grandes if not toca_borde(c)]):      # los que tocan el borde son el cartón/mesa de alrededor
        av.append(f"{len(g)} objeto(s) demasiado grande(s): ¿piezas pegadas? Sepáralas.")
    if (b := [p["id"] for p in pieces if p["motivo"].startswith("forma")]):
        av.append(f"Pieza(s) {b}: forma no rectangular, posibles piezas que se TOCAN. Sepáralas.")
    if sombras:
        av.append(f"{sombras} sombra(s) o mancha(s) del tapete ignoradas (no son piezas).")
    for p in pieces:
        if p["label"] == "DESCONOCIDO":
            av.append(f"#{p['id']} DESCONOCIDO: {p['motivo']}.")
    return av


def process(img, cfg):
    rect, px_cm, quad = calibrate(img, cfg)
    blur, hsv = preprocess(rect, cfg)
    lab = cv2.cvtColor(blur, cv2.COLOR_BGR2LAB)
    tapete, mask = segment(hsv, cfg)
    cnts, grandes = detect(mask, px_cm, cfg)
    # color medio del tapete (a, b de Lab): para distinguir sombras del tapete de piezas oscuras
    verde = lab[tapete > 0]
    mat_ab = np.median(verde[::25, 1:], axis=0) if len(verde) > 1000 else None
    pieces, sombras = [], 0
    for c in cnts:
        f = extract(c, hsv, lab, px_cm, cfg, mat_ab)
        if f["dist_tapete"] < cfg["tipo"]["d_tapete_min"] and tipo_de(f, cfg)[0] not in cfg["tipos"]:
            sombras += 1                    # color de tapete y sin forma/tamaño de pieza válida: sombra
            continue
        f["id"] = len(pieces) + 1
        f["tipo"], f["color"], f["label"], f["motivo"] = classify(f, cfg)
        pieces.append(f)
    av = avisos(img, quad, px_cm, pieces, grandes, rect.shape, cfg, sombras)
    contornos = rect.copy()
    cv2.drawContours(contornos, cnts, -1, (0, 255, 0), 2)
    result = annotate(rect, pieces)
    stages = {"1 original": img, "2 rectificada": rect, "3 HSV": hsv, "4 mascara tapete": tapete,
              "5 mascara limpia": mask, "6 contornos": contornos, "7 resultado": result}
    return {"pieces": pieces, "result": result, "stages": stages, "px_cm": px_cm, "avisos": av, "rect": rect, "marcadores": quad is not None}
