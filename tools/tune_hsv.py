"""python tune_hsv.py imagen.jpg  -> ajusta trackbars; Q imprime los rangos para config.yaml."""
import os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from vision.pipeline import load_config
img = cv2.imread(sys.argv[1]); img = cv2.resize(img, (700, int(img.shape[0] * 700 / img.shape[1])))
hsv = cv2.cvtColor(cv2.GaussianBlur(img, (5, 5), 0), cv2.COLOR_BGR2HSV)
ini = load_config()["tapete_hsv"]["lo"] + load_config()["tapete_hsv"]["hi"]
nombres = ["Hlo", "Slo", "Vlo", "Hhi", "Shi", "Vhi"]
cv2.namedWindow("hsv")
for n, v, mx in zip(nombres, ini, [179, 255, 255] * 2): cv2.createTrackbar(n, "hsv", v, mx, lambda x: None)
while True:
    p = [cv2.getTrackbarPos(n, "hsv") for n in nombres]
    m = cv2.inRange(hsv, np.array(p[:3]), np.array(p[3:]))
    cv2.imshow("hsv", np.hstack([img, cv2.bitwise_and(img, img, mask=m)]))
    if cv2.waitKey(30) & 0xFF == ord("q"): break
print(f"lo: {p[:3]}  hi: {p[3:]}")
