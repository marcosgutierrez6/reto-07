"""3. Preprocesamiento: desenfoque gaussiano, HSV y (opcional) CLAHE en V."""
import cv2


def preprocess(img, cfg):
    """Gaussiano (quita ruido) -> HSV (separa color de brillo). Devuelve (bgr_suave, hsv)."""
    blur = cv2.GaussianBlur(img, (cfg["blur"],) * 2, 0)
    hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
    if cfg["clahe"]:  # compensa iluminación no uniforme sin tocar H ni S
        h, s, v = cv2.split(hsv)
        hsv = cv2.merge([h, s, cv2.createCLAHE(2.0, (8, 8)).apply(v)])
    return blur, hsv
