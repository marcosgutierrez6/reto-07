"""8b. Salida visual: imagen anotada y mosaico de depuración."""
import cv2, numpy as np


def escala(img):
    """Factor de tamaño de dibujo proporcional a la foto (en una de 4000 px los trazos finos no se ven)."""
    return max(img.shape[:2]) / 1500


def etiquetar_piezas(img, items):
    """items: [(texto, contorno)]. Dibuja cada etiqueta (texto blanco en negrita sobre negro semitransparente) junto a su pieza,
    probando 8 posiciones y eligiendo la que menos pisa a otras etiquetas y a otras piezas. Tamaño proporcional a la imagen."""
    k, (H, W) = escala(img), img.shape[:2]
    fuente, esc, gro, pad, m = cv2.FONT_HERSHEY_DUPLEX, 0.8 * k, max(2, int(2.2 * k)), int(7 * k), int(4 * k)
    cajas = [cv2.boundingRect(c) for _, c in items]
    inter = lambda r, q: max(0, min(r[0] + r[2], q[0] + q[2]) - max(r[0], q[0])) * max(0, min(r[1] + r[3], q[1] + q[3]) - max(r[1], q[1]))
    puestas = []
    for (txt, _), (x, y, bw, bh) in zip(items, cajas):
        (tw, th), base = cv2.getTextSize(txt, fuente, esc, gro)
        w, h = tw + 2 * pad, th + base + 2 * pad
        cx, cy = x + bw / 2 - w / 2, y + bh / 2 - h / 2
        mejor = None
        for px, py in ((cx, y - h - m), (cx, y + bh + m), (x + bw + m, cy), (x - w - m, cy),
                       (x + bw + m, y - h - m), (x - w - m, y - h - m), (x + bw + m, y + bh + m), (x - w - m, y + bh + m)):
            r = (int(np.clip(px, 0, max(W - w, 0))), int(np.clip(py, 0, max(H - h, 0))), w, h)
            costo = 3 * sum(inter(r, q) for q in puestas) + sum(inter(r, c) for c in cajas)   # pisar otra etiqueta cuesta más
            if mejor is None or costo < mejor[0]: mejor = (costo, r)
            if costo == 0: break
        r = mejor[1]; puestas.append(r)
        roi = img[r[1]:r[1] + h, r[0]:r[0] + w]
        img[r[1]:r[1] + h, r[0]:r[0] + w] = cv2.addWeighted(roi, 0.35, np.zeros_like(roi), 0.65, 0)   # negro al 65 %
        cv2.putText(img, txt, (r[0] + pad, r[1] + pad + th), fuente, esc, (255, 255, 255), gro, cv2.LINE_AA)


def annotate(img, pieces):
    """Contorno (verde), rectángulo rotado (magenta) y etiqueta con ID. Trazos proporcionales al tamaño de la foto."""
    out, k = img.copy(), escala(img)
    for p in pieces:
        cv2.drawContours(out, [p["_contour"]], -1, (0, 255, 0), max(1, int(2 * k)))
        cv2.polylines(out, [cv2.boxPoints(p["_rect"]).astype(np.int32)], True, (255, 0, 255), max(1, int(k)))
    etiquetar_piezas(out, [(f"#{p['id']} {p['label']}", p["_contour"]) for p in pieces])     # al final: nada las tapa
    return out


def mosaic(stages, path=None, cols=4, size=400):
    """Une las etapas {titulo: imagen} en una sola imagen (para vídeo/informe)."""
    tiles = []
    for name, im in stages.items():
        im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR) if im.ndim == 2 else im
        im = cv2.resize(im, (size, size))
        cv2.putText(im, name, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        tiles.append(im)
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    m = np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)])
    if path:
        cv2.imwrite(path, m)
    return m
