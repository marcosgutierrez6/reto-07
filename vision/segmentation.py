"""4. Segmentación y 5. Detección."""
import cv2, numpy as np


def fondo_v(v):
    """Luminosidad (V) local del tapete: mediana a baja resolución. Las piezas son pocas y pequeñas, no la contaminan.
    Sirve para detectar lo que es MUCHO más oscuro que su entorno (piezas negras)."""
    h, w = v.shape
    chica = cv2.resize(v, (400, max(1, int(400 * h / w))), interpolation=cv2.INTER_AREA)
    return cv2.resize(cv2.medianBlur(chica, 51), (w, h), interpolation=cv2.INTER_LINEAR)


def segment(hsv, cfg):
    """Pieza = todo lo que NO es tapete verde. Devuelve (máscara_tapete, máscara_piezas_limpia).
    Una pieza negra tiene el mismo tono y saturación que el tapete oscuro (H≈72, S≈175), pero es mucho más oscura
    que su entorno: lo que baja de `oscuro_ratio` del fondo local no es tapete."""
    tapete = cv2.inRange(hsv, np.array(cfg["tapete_hsv"]["lo"]), np.array(cfg["tapete_hsv"]["hi"]))
    oscuro = hsv[..., 2] < cfg["oscuro_ratio"] * fondo_v(hsv[..., 2])
    tapete[oscuro] = 0
    k = np.ones((cfg["morfologia"],) * 2, np.uint8)
    mask = cv2.bitwise_not(tapete)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)    # quita puntos de ruido
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((cfg["cierre"],) * 2, np.uint8))   # une tetones y brillos
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask = np.zeros_like(mask)
    cv2.drawContours(mask, cnts, -1, 255, -1)           # rellena los huecos interiores: pieza completa
    marc = cv2.inRange(hsv, np.array(cfg["marcador_hsv"]["lo"]), np.array(cfg["marcador_hsv"]["hi"]))
    mask[cv2.dilate(marc, k, iterations=2) > 0] = 0     # fuera marcadores de calibración
    return tapete, mask


def detect(mask, px_cm, cfg):
    """Contornos externos con área (cm²) entre mínimo (ruido) y máximo. Devuelve también los que superan el máximo."""
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    a = lambda c: cv2.contourArea(c) / px_cm ** 2
    return ([c for c in cnts if cfg["area_min_cm2"] <= a(c) <= cfg["area_max_cm2"]],
            [c for c in cnts if a(c) > cfg["area_max_cm2"]])      # (piezas, demasiado grandes)
