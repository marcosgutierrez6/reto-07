"""CLI: python check_resolution.py foto.jpg LONGITUD_MM  (clic en 2 puntos de la regla/referencia)."""
import sys
import numpy as np


def evaluar(dist_px, real_mm, min_px):
    """Devuelve (mm_por_px, líneas de texto, cumple) para un segmento de `real_mm` que mide `dist_px`."""
    mm_px = real_mm / dist_px
    lineas, ok = [f"{mm_px:.3f} mm/px  ({10 / mm_px:.1f} px/cm)"], True
    for nombre, mm in (("tetón (5 mm)", 5), ("pieza 1x1 (8 mm)", 8)):
        px = mm / mm_px
        ok &= px >= min_px
        lineas.append(f"{nombre}: {px:.1f} px → {'OK' if px >= min_px else 'INSUFICIENTE'} (mínimo {min_px})")
    return mm_px, lineas, bool(ok)


if __name__ == "__main__":
    import cv2
    img, real_mm, pts = cv2.imread(sys.argv[1]), float(sys.argv[2]), []
    def clic(e, x, y, *_):
        if e == cv2.EVENT_LBUTTONDOWN and len(pts) < 2:
            pts.append((x, y)); cv2.circle(img, (x, y), 4, (0, 0, 255), -1); cv2.imshow("regla", img)
    cv2.imshow("regla", img); cv2.setMouseCallback("regla", clic)
    while len(pts) < 2 and cv2.waitKey(50) != ord("q"): pass
    if len(pts) == 2:
        print("\n".join(evaluar(np.hypot(pts[0][0] - pts[1][0], pts[0][1] - pts[1][1]), real_mm, 10)[1]))
