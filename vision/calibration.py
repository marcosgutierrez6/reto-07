"""2. Calibración de escala (px/cm) + corrección de perspectiva con 4 marcadores."""
import cv2, numpy as np


def calibrate(img, cfg):
    """Busca 4 marcadores magenta en las esquinas de un área de `area_cm` cm.
    Devuelve (imagen rectificada, px/cm, cuadrilátero de marcadores o None).
    Con los 4 marcadores: homografía -> vista cenital exacta y px/cm medido en ESTA imagen.
    Si no: imagen sin tocar y px/cm fijo de la configuración."""
    hsv = cv2.cvtColor(cv2.GaussianBlur(img, (5, 5), 0), cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, np.array(cfg["marcador_hsv"]["lo"]), np.array(cfg["marcador_hsv"]["hi"]))
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:4]
    if len(cnts) < 4 or cv2.contourArea(cnts[3]) < 20:
        return img, max(img.shape[:2]) / cfg["ancho_imagen_cm"], None   # px/cm independiente de la resolución
    pts = np.array([c[:, 0].mean(axis=0) for c in cnts], np.float32)   # centros
    s, d = pts.sum(1), pts[:, 0] - pts[:, 1]
    src = np.array([pts[s.argmin()], pts[d.argmax()], pts[s.argmax()], pts[d.argmin()]], np.float32)  # TL TR BR BL
    lado = np.mean([np.linalg.norm(src[i] - src[(i + 1) % 4]) for i in range(4)])
    n = int(round(lado))
    dst = np.float32([[0, 0], [n, 0], [n, n], [0, n]])
    rect = cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst), (n + 1, n + 1))
    return rect, lado / cfg["area_cm"], src
