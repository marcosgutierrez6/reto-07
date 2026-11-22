"""Imágenes sintéticas de prueba: las 14 clases (15 piezas) + la intrusa 1x3 blanca, con sombras y brillos.
Uso: python tools/make_synthetic.py dataset   (crea dataset/calibration/cal_*.jpg y dataset/test/test_*.jpg)"""
import os, sys, cv2, numpy as np
D = sys.argv[1] if len(sys.argv) > 1 else "dataset"; PX = 55; W, H = 2000, 1500
COL = {"rojo": (30, 30, 200), "azul": (200, 80, 30), "amarillo": (30, 210, 230), "blanco": (235, 235, 235),
       "gris": (170, 165, 160), "negro": (25, 25, 25), "marron": (30, 60, 110)}
CL = ["2x2 amarillo", "2x2 marron", "2x2 negro", "2x2 gris", "2x3 rojo", "2x3 gris", "2x4 azul", "2x4 azul", "2x4 gris",
      "2x6 rojo", "2x6 marron", "2x6 gris", "1x6 rojo", "1x6 gris", "2x8 negro"]
def escena(piezas, rng, sombras=True):
    img = np.full((H, W, 3), (60, 140, 60), np.uint8); puestas = []
    dims = lambda cl: [((int(cl.split()[0].split('x')[i]) * .8 - .02) * PX) for i in (0, 1)]
    for cl in sorted(piezas, key=lambda c: -np.hypot(*dims(c))):
        w, h = dims(cl); r = np.hypot(w, h) / 2
        for _ in range(5000):
            x, y = rng.uniform(r + 25, W - r - 25), rng.uniform(r + 25, H - r - 25)
            if all(np.hypot(x - a, y - b) > r + rr + 14 for a, b, rr in puestas): break
        else: raise RuntimeError("no cabe")
        puestas.append((x, y, r)); ang = rng.uniform(0, 180)
        box = cv2.boxPoints(((x, y), (w, h), ang)).astype(np.int32)
        if sombras:
            cv2.fillPoly(img, [box + np.array([14, 14])], (20, 45, 20) if rng.random() < .5 else (35, 85, 35))   # sombra profunda o suave
        cv2.fillPoly(img, [box], COL[cl.split()[1]])
        if cl.split()[1] != "negro":  # brillos de tetones
            for t in range(int(cl.split()[0].split('x')[1])):
                c = np.array([x, y]) + np.array([np.cos(np.radians(ang)), np.sin(np.radians(ang))]) * ((t - (int(cl.split()[0].split('x')[1]) - 1) / 2) * .8 * PX)
                cv2.circle(img, tuple(c.astype(int)), 5, (245, 245, 245), -1)
    img = img * np.linspace(.93, 1, W)[None, :, None] + rng.normal(0, 3, img.shape)
    return img.clip(0, 255).astype(np.uint8)
rng = np.random.default_rng(11)
os.makedirs(f"{D}/calibration", exist_ok=True); os.makedirs(f"{D}/test", exist_ok=True)
for i in range(11):
    cv2.imwrite(f"{D}/calibration/cal_{i:02d}.jpg", escena(CL + ["1x3 blanco"], rng))
for i in range(4):   # test: subconjuntos de 1 a 16 piezas
    sel = list(rng.permutation(CL)[: [1, 6, 15, 15][i]]) + (["1x3 blanco"] if i >= 1 else [])
    cv2.imwrite(f"{D}/test/test_{i}.jpg", escena(sel, rng))
