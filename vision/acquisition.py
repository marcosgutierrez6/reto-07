"""1. Adquisición: archivo, carpeta, webcam o cámara IP -> (nombre, imagen BGR)."""
import cv2, glob, os
import numpy as np


def es_heic(path):
    return path.lower().endswith((".heic", ".heif"))


def leer_imagen(path):
    """Lee una imagen BGR (JPG/PNG/HEIC, también con rutas con acentos en Windows). Error claro si no se puede abrir.
    Las fotos HEIC del iPhone se decodifican con pillow-heif y se les aplica la rotación EXIF."""
    if es_heic(path):
        try:
            from PIL import Image, ImageOps
            from pillow_heif import register_heif_opener
            register_heif_opener()
            return cv2.cvtColor(np.asarray(ImageOps.exif_transpose(Image.open(path)).convert("RGB")), cv2.COLOR_RGB2BGR)
        except ImportError:
            raise ValueError("Para abrir fotos HEIC falta una librería. Ejecuta:  pip install pillow-heif")
        except Exception:
            raise ValueError(f"No se pudo abrir la foto HEIC «{os.path.basename(path)}».")
    img = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"No se pudo abrir la imagen «{os.path.basename(path)}».")
    return img


def listar_fotos(carpeta):
    """Rutas de las fotos de una carpeta (jpg, jpeg, png, heic, heif), sin distinguir mayúsculas (IMG_1.JPG, IMG_2.HEIC)."""
    return sorted(os.path.join(carpeta, f) for f in os.listdir(carpeta)
                  if f.lower().endswith((".jpg", ".jpeg", ".png", ".heic", ".heif")))


def images(path):
    """Genera (nombre, imagen) desde un archivo o desde todas las imágenes de una carpeta."""
    if os.path.isfile(path):
        files = [path]
    else:
        files = listar_fotos(path)
    for f in files:
        yield os.path.basename(f), leer_imagen(f)


def live(source):
    """Vídeo en vivo (índice de webcam o URL tipo http://IP:PUERTO/video).
    ESPACIO = analizar el frame actual, Q = salir."""
    cap, n = cv2.VideoCapture(source), 0
    while cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            break
        cv2.imshow("ESPACIO=analizar  Q=salir", frame)
        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
        if k == 32:
            n += 1
            yield f"frame_{n}", frame
    cap.release()
