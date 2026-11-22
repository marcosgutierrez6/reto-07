"""CLI: python main.py --image f.jpg | --folder d/ | --camera 0 | --ipcam URL  [--debug]"""
import argparse, os, sys
import cv2, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vision import acquisition
from vision.pipeline import process, load_config, row, ROOT
from vision.inventory import inventory
from vision.visualization import mosaic
from vision.decision_tree import draw_tree

ap = argparse.ArgumentParser()
ap.add_argument("--image"); ap.add_argument("--folder"); ap.add_argument("--camera", type=int)
ap.add_argument("--ipcam"); ap.add_argument("--debug", action="store_true")
a = ap.parse_args()

cfg, out = load_config(), os.path.join(ROOT, "results")
draw_tree(cfg, os.path.join(out, "arbol_decision.png"))
if a.image or a.folder:
    fuente = acquisition.images(a.image or a.folder)
elif a.camera is not None or a.ipcam:
    fuente = acquisition.live(a.ipcam or a.camera)
else:
    sys.exit("Indica --image, --folder, --camera o --ipcam")

for nombre, img in fuente:
    r = process(img, cfg)
    base = os.path.join(out, os.path.splitext(nombre)[0])
    cv2.imwrite(base + "_resultado.png", r["result"])
    pd.DataFrame([row(p) for p in r["pieces"]]).to_csv(base + "_piezas.csv", index=False)
    print(f"\n== {nombre}  ({r['px_cm']:.1f} px/cm)")
    inventory(r["pieces"], cfg, base + "_inventario.csv")
    for av in r["avisos"]:
        print("AVISO:", av)
    if a.debug:
        mosaic(r["stages"], base + "_debug.png")
    if a.camera is not None or a.ipcam:
        cv2.imshow("resultado", r["result"])
