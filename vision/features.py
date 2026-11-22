"""6. Características por pieza (forma + color)."""
import cv2, numpy as np


def hue_stats(h):
    """Media y mediana CIRCULARES del tono (0-179): el rojo da la vuelta en 0/180."""
    ang = h * np.pi / 90
    ref = (np.arctan2(np.sin(ang).mean(), np.cos(ang).mean()) * 90 / np.pi) % 180
    d = (h - ref + 90) % 180 - 90          # desviaciones respecto a la media, en [-90, 90)
    return ref, (ref + np.median(d)) % 180


def extract(c, hsv, lab, px_cm, cfg, mat_ab=None):
    """Devuelve un dict con todas las características de un contorno."""
    area, per = cv2.contourArea(c), cv2.arcLength(c, True)
    rect = cv2.minAreaRect(c)
    (_, _), (w, h), ang = rect
    M = cv2.moments(c)
    f = {
        "cx": M["m10"] / M["m00"], "cy": M["m01"] / M["m00"],           # centroide
        "largo_cm": max(w, h) / px_cm, "ancho_cm": min(w, h) / px_cm,   # lados de minAreaRect
        "largo_tet": max(w, h) / px_cm / cfg["tipo"]["teton_cm"],      # ...y en tetones
        "ancho_tet": min(w, h) / px_cm / cfg["tipo"]["teton_cm"],
        "area_px": area, "area_cm2": area / px_cm ** 2, "perimetro": per,
        "aspect": max(w, h) / min(w, h),                                # lado largo/corto (invariante a rotación)
        "rectangularidad": area / (w * h),                              # área / área minAreaRect
        "circularidad": 4 * np.pi * area / per ** 2,
        "solidez": area / cv2.contourArea(cv2.convexHull(c)),           # área / área envolvente convexa
        "orientacion": (ang if w >= h else ang + 90) % 180,             # ángulo del lado largo
        "_contour": c, "_rect": rect,
    }
    # Perspectiva: la cámara no mira recto hacia abajo a las piezas laterales y ve sus paredes, que se suman a la huella.
    # El exceso crece con la distancia al centro de la foto y actúa en la dirección RADIAL (se reparte entre largo y ancho
    # según el ángulo). Se resta k_perspectiva * distancia; k se calibra en la app («Calcular umbrales»).
    alto, ancho = hsv.shape[:2]
    dn = np.hypot(f["cx"] - ancho / 2, f["cy"] - alto / 2) / (max(alto, ancho) / 2)       # 0 = centro, 1 = borde largo
    rel = np.arctan2(f["cy"] - alto / 2, f["cx"] - ancho / 2) - np.radians(f["orientacion"])
    f["g_largo"], f["g_ancho"] = dn * abs(np.cos(rel)), dn * abs(np.sin(rel))
    f["largo_tet_bruto"], f["ancho_tet_bruto"] = f["largo_tet"], f["ancho_tet"]
    k = cfg["tipo"]["k_perspectiva"]
    f["largo_tet"] -= k * f["g_largo"]; f["ancho_tet"] -= k * f["g_ancho"]
    f["largo_cm"], f["ancho_cm"] = f["largo_tet"] * cfg["tipo"]["teton_cm"], f["ancho_tet"] * cfg["tipo"]["teton_cm"]
    # Color solo dentro de la pieza, erosionada (sin bordes/sombras) y sin brillos especulares
    mask = np.zeros(hsv.shape[:2], np.uint8)
    cv2.drawContours(mask, [c], -1, 255, -1)
    er = cv2.erode(mask, np.ones((cfg["erosion"],) * 2, np.uint8))
    if not er.any():
        er = mask
    p_hsv, p_lab = hsv[er > 0], lab[er > 0]
    ok = ~((p_hsv[:, 2] >= cfg["especular"]["v_min"]) & (p_hsv[:, 1] <= cfg["especular"]["s_max"]))
    if not ok.any():
        ok[:] = True
    for px, nombres in ((p_hsv[ok], "HSV"), (p_lab[ok], "Lab")):
        for i, n in enumerate(nombres):
            v = px[:, i].astype(float)
            f[n + "_mean"], f[n + "_med"] = hue_stats(v) if n == "H" else (v.mean(), np.median(v))
    # Ángulo (°) entre la crominancia (a, b) de la pieza y la del tapete. Una sombra del tapete es el mismo verde más oscuro
    # (mismo ángulo, da igual lo profunda que sea); un color distinto (marrón, rojo...) o un neutro (gris/negro) da un ángulo grande.
    v = np.array([f["a_med"] - 128, f["b_med"] - 128])           # OpenCV guarda a,b con offset 128
    if mat_ab is None or np.hypot(*v) < 4:
        f["dist_tapete"] = 180.0                                   # sin crominancia: neutro, no se parece al verde
    else:
        m = np.asarray(mat_ab, float) - 128
        f["dist_tapete"] = float(np.degrees(abs(np.arctan2(v[0] * m[1] - v[1] * m[0], v @ m))))
    return f
