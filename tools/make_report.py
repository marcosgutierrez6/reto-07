"""Genera results/informe.pdf (figuras, tablas y resultados) a partir del código y de las fotos de dataset/.
Uso: python tools/make_report.py"""
import os, sys, glob, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from vision import pipeline as P, etiquetas as E
from vision.acquisition import leer_imagen
from vision.decision_tree import draw_tree
from vision.visualization import mosaic, annotate
from tools import analyze_thresholds as A

R = P.ROOT; OUT = f"{R}/results/informe"; os.makedirs(OUT, exist_ok=True)
cfg = P.load_config(); ss = getSampleStyleSheet()
H1, H2, T = ss["Heading1"], ss["Heading2"], ss["BodyText"]
story = []
def txt(s): story.append(Paragraph(s, T)); story.append(Spacer(1, 6))
def img(path, w=16):
    h, ww = cv2.imread(path).shape[:2]; story.append(Image(path, w * cm, w * cm * h / ww)); story.append(Spacer(1, 6))
def tabla(filas, anchos=None):
    t = Table([[Paragraph(str(c), ss["BodyText"]) for c in f] for f in filas], colWidths=anchos, repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .4, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")])); story.append(t); story.append(Spacer(1, 8))

fotos = {c: sorted(glob.glob(f"{R}/dataset/{c}/*.png")) for c in ("calibration", "test")}
todas = fotos["calibration"] + fotos["test"]
proc = {os.path.basename(f): (leer_imagen(f), None) for f in todas[:0]}

# ---- portada
story += [Spacer(1, 4 * cm), Paragraph("Inventario automatico de piezas LEGO mediante vision artificial clasica", H1),
          Paragraph("Reto 07 - Examen parcial de Vision Artificial Clasica", T), Spacer(1, 12),
          Paragraph("Autor: Marcos Guti\u00e9rrez &nbsp;&nbsp; Fecha: " + datetime.date.today().strftime("%d/%m/%Y"), T),
          Paragraph("Video de la demo (YouTube): <link href='https://youtu.be/yHbt5aCICo8' color='blue'>https://youtu.be/yHbt5aCICo8</link>", T),
          Paragraph("Repositorio (codigo): <link href='https://github.com/marcosgutierrez6/reto-07' color='blue'>https://github.com/marcosgutierrez6/reto-07</link>", T),
          Paragraph("Carpeta de Drive (fotos y material): <link href='https://drive.google.com/drive/u/2/folders/1R35zVPEsOiFWRcb7Qbb1JnXILw5mMd_8' color='blue'>enlace a la carpeta de Drive</link>", T), PageBreak()]

# ---- 1 contexto
story.append(Paragraph("1. Contexto y requisitos", H1))
txt("Se analiza una escena cenital de piezas LEGO sobre un tapete de fieltro verde. El sistema detecta cada pieza (nivel 1), "
    "la clasifica por <b>tipo</b> (huella en tetones) y <b>color</b> con un arbol de decision explicito (nivel 2) y elabora un "
    "<b>inventario</b> frente a la coleccion esperada, indicando que piezas faltan y cuales son intrusas (nivel 3). "
    "No se usa ningun clasificador aprendido: todos los umbrales estan en <i>config.yaml</i> y se justifican con mediciones.")
tabla([["Elemento", "Valor"],
       ["Tipos geometricos (6)", ", ".join(cfg["tipos"])],
       ["Clases (tipo + color)", f"{len(cfg['clases'])}: " + ", ".join(cfg["clases"])],
       ["Unidades por clase", "2x4 azul: 2 unidades; resto: 1 (15 piezas fisicas)"],
       ["Intrusa de prueba", "1x3 blanca (tipo no permitido): se informa DESCONOCIDO con motivo"],
       ["Restricciones", "Sin deep learning; clase final depende de dos atributos (tipo y color)"]], [5 * cm, 12 * cm])

# ---- 2 montaje
story.append(Paragraph("2. Montaje fisico", H1))
txt(f"Tapete verde mate de unos 50 x 50 cm; una camara de movil fija en posicion cenital (fotos HEIC de iPhone, convertidas a PNG). "
    f"La iluminacion es la de la sala. Escala sin marcadores: la foto abarca <b>{cfg['ancho_imagen_cm']} cm</b> en su lado largo "
    f"(calibrable); con 4 marcadores magenta se usa homografia. Se tomaron <b>{len(todas)}</b> fotos "
    f"({len(fotos['calibration'])} para calibrar y {len(fotos['test'])} para test) con 1 a 15 piezas, posiciones y orientaciones distintas.")
ej = leer_imagen(f"{R}/dataset/calibration/IMG_0695.png"); cv2.imwrite(f"{OUT}/montaje.png", cv2.resize(ej, None, fx=.2, fy=.2)); img(f"{OUT}/montaje.png", 10)
h, w = ej.shape[:2]; pxcm = max(h, w) / cfg["ancho_imagen_cm"]
txt(f"<b>Justificacion de resolucion:</b> imagen de {w}x{h} px, {pxcm:.1f} px/cm. El detalle mas pequeno necesario es un teton "
    f"(0,8 cm) = {pxcm * 0.8:.0f} px, muy por encima del minimo necesario (unos 8-10 px) para medir la huella con precision de fraccion de teton.")

# ---- 3 pipeline
fig, ax = plt.subplots(figsize=(8, 3.4)); ax.axis("off")
pasos = ["Adquisicion\n(JPG/PNG/HEIC)", "Calibracion\n(escala / homografia)", "Preproceso\n(Gauss, HSV, Lab)", "Segmentacion\n(tapete + oscuro_ratio)",
         "Deteccion\n(contornos)", "Caracteristicas\n(huella, color, forma)", "Arbol de decision\n(tipo + color)", "Inventario\n(faltan / intrusas)"]
for i, p in enumerate(pasos):
    x, y = i % 4, -(i // 4)
    ax.text(x, y, p, ha="center", va="center", fontsize=9, bbox=dict(boxstyle="round,pad=.5", fc="#dbeafe", ec="#1d4ed8"))
    if i and i != 4: ax.annotate("", xy=(x - .3, y), xytext=(x - .7, y), arrowprops=dict(arrowstyle="->"))
ax.annotate("", xy=(0, -.4), xytext=(3, -.4 + 0), arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0", color="grey"))
ax.set_xlim(-.6, 3.6); ax.set_ylim(-1.5, .5); fig.savefig(f"{OUT}/pipeline.png", dpi=170, bbox_inches="tight"); plt.close(fig)
story.append(Paragraph("3. Pipeline completo", H1)); img(f"{OUT}/pipeline.png", 17)

# ---- 4 segmentacion
story.append(Paragraph("4. Metodo de segmentacion", H1))
txt(f"1) El tapete se detecta por color en HSV (H 35-85, S y V minimos); lo que NO es tapete dentro del area util es candidato a pieza. "
    f"2) Las piezas negras tienen el mismo HSV que el tapete en sombra; se detectan por <b>oscuridad relativa</b>: V inferior al "
    f"{cfg['oscuro_ratio']} del fondo local. 3) Apertura ({cfg['morfologia']} px) para quitar ruido y cierre ({cfg['cierre']} px) para unir tetones y brillos. "
    f"4) Se rellenan contornos externos y se filtra por area ({cfg['area_min_cm2']}-{cfg['area_max_cm2']} cm2). "
    f"5) Las sombras se descartan si su angulo de croma (a,b de Lab) es parecido al del tapete y la forma no es valida.")
r0 = P.process(ej, cfg); mosaic(r0["stages"], f"{OUT}/etapas.png", cols=4, size=300); img(f"{OUT}/etapas.png", 17)
txt("<i>Figura: etapas intermedias del pipeline sobre IMG_0695 (15 piezas).</i>")

# ---- 5 caracteristicas
story.append(Paragraph("5. Caracteristicas extraidas", H1))
tabla([["Caracteristica", "Calculo", "Para que sirve"],
       ["largo_tet, ancho_tet", "Lados de minAreaRect / (teton_cm*px_cm), con correccion de perspectiva", "Tipo (2x4, 1x6...)"],
       ["area_cm2", "Area del contorno / px_cm^2", "Filtro de ruido y objetos grandes"],
       ["rectangularidad", "Area contorno / area rectangulo minimo", "Rechaza piezas pegadas y sombras"],
       ["aspect", "largo / ancho", "Apoya el tipo"],
       ["orientacion, centroide", "Angulo de minAreaRect y momentos", "Evaluacion, perspectiva, etiquetas"],
       ["H, S, V (mediana)", "HSV de la region erosionada, sin pixeles especulares; H con estadistica circular", "Color"],
       ["L, a, b (mediana)", "Lab de la misma region", "Angulo de croma frente al tapete"],
       ["dist_tapete", "Angulo (grados) en el plano (a,b) entre la pieza y el tapete", "Detectar sombras"],
       ["g_largo, g_ancho", "Distancia al centro de la foto proyectada sobre los ejes de la pieza", "Correccion de perspectiva (paredes vistas de lado)"]],
      [3.7 * cm, 8 * cm, 5.3 * cm])

# ---- 6 arbol
story.append(Paragraph("6. Arbol de decision", H1))
draw_tree(cfg, f"{OUT}/arbol.png"); img(f"{OUT}/arbol.png", 17)
c = cfg["color"]
tabla([["Regla de color (en orden)", "Condiciones"]] + [[n, ", ".join(f"{k}={v}" for k, v in r.items())] for n, r in c.items()], [4 * cm, 13 * cm])
txt(f"Tipo: ancho y largo en tetones deben estar a menos de {cfg['tipo']['tol_tetones']} de un entero, formar un tipo permitido y la rectangularidad "
    f"ser >= {cfg['tipo']['rect_min']}. Clase valida solo si 'tipo color' esta en la coleccion; si no, DESCONOCIDO con motivo.")

# ---- 7 justificacion umbrales
story.append(PageBreak()); story.append(Paragraph("7. Justificacion experimental de los umbrales", H1))
df, _ = E.medir_etiquetadas(cfg, f"{R}/dataset/calibration")
figs, sug, resumen = A.analizar(df, cfg)
A.exportar_figuras(figs, OUT)
for n in figs: img(f"{OUT}/{n}.png", 12 if "ancho" in n or "largo" in n else 15)
story.append(Paragraph("Estadistica por clase (fotos de calibracion)", H2))
for l in resumen.split("\n"): story.append(Paragraph(l.replace("<", "&lt;").replace("±", "+/-").replace("σ", "s"), ss["Code"]))
story.append(Spacer(1, 8))
story.append(Paragraph("Umbrales sugeridos por las mediciones (valor, margen abajo y arriba en desviaciones tipicas)", H2))
tabla([["Umbral", "Sugerido", "Actual"]] + [[k, f"{v[0]:.2f}", str(A.a_plano(cfg).get(k, "-"))] for k, v in sug.items()], [6 * cm, 3 * cm, 3 * cm])

# ---- 8 resultados
story.append(PageBreak()); story.append(Paragraph("8. Resultados sobre el conjunto de pruebas", H1))
filas = [["Foto", "Conjunto", "Piezas detectadas", "DESCONOCIDAS", "Clases distintas"]]
res = {}
for conj, fs in fotos.items():
    for f in fs:
        r = P.process(leer_imagen(f), cfg); n = os.path.basename(f); res[n] = r
        nd = sum(p["label"] == "DESCONOCIDO" for p in r["pieces"])
        filas.append([n, conj, len(r["pieces"]), nd, len({p["label"] for p in r["pieces"]})])
tabla(filas, [3.5 * cm, 3 * cm, 3.5 * cm, 3.5 * cm, 3.5 * cm])
for n in ("IMG_0695.png", "IMG_0697.png", "IMG_0726.png"):
    p = f"{OUT}/res_{n}"; cv2.imwrite(p, cv2.resize(res[n]["result"], None, fx=.25, fy=.25) if res[n]["result"].shape[1] > 1500 else res[n]["result"]); img(p, 11)
    txt(f"<i>{n}: resultado anotado.</i>")
n0 = P.process(ej, cfg)
from vision.inventory import inventory
inv = inventory(n0["pieces"], cfg, imprimir=False)
story.append(Paragraph("Inventario (nivel 3) de IMG_0695", H2))
tabla([["Clase", "Esperadas", "Encontradas", "Estado"]] + [[f.clase, f.esperadas, f.encontradas, f.estado] for f in inv["coleccion"].itertuples()],
      [6 * cm, 3 * cm, 3 * cm, 3 * cm])

# ---- 9 evaluacion cuantitativa
story.append(Paragraph("9. Medida cuantitativa de aciertos y errores", H1))
t, falt = E.medir_etiquetadas(cfg, f"{R}/dataset/test")
n_tot = sum(len(r["pieces"]) for k, r in res.items() if k in {os.path.basename(f) for f in fotos["test"]})
ok = int((t["clase"].map(E.real_a_pred) == t["pred"]).sum())
txt(f"Piezas detectadas en test: {n_tot}. Piezas con etiqueta verificada: {len(t)}; aciertos: {ok}; piezas etiquetadas no detectadas: {len(falt)}. "
    f"Piezas pendientes de verificacion manual: {n_tot - len(t)}. <b>Nota:</b> la tasa sobre las piezas etiquetadas solo es una medida real si las "
    f"etiquetas son verdad terreno revisada a mano; actualizar este informe tras revisar las pendientes (python tools/make_report.py).")
if len(t):
    cm_ = pd.crosstab(t["clase"].map(E.real_a_pred), t["pred"]); story.append(Paragraph("Matriz de confusion (filas: real, columnas: predicho)", H2))
    tabla([["real \\ pred"] + list(cm_.columns)] + [[i] + list(r) for i, r in cm_.iterrows()])

# ---- 10 limitaciones
story.append(Paragraph("10. Limitaciones observadas", H1))
txt("- <b>Brillo especular central:</b> un foco sobre el tapete quema el centro y baja la saturacion; rojos/marrones se ven rosas y azules casi blancos (DESCONOCIDO o color erroneo). "
    "Mitigacion: luz difusa y menos exposicion.<br/>- <b>Perspectiva:</b> piezas en el borde de la foto se ven mas anchas por sus paredes laterales; se corrige parcialmente con k_perspectiva.<br/>"
    "- <b>Piezas tocandose:</b> dos piezas pegadas pueden formar un unico contorno; se avisa en la interfaz.<br/>- <b>Pieza negra:</b> depende del contraste relativo con el tapete.<br/>"
    "- <b>Blanco frente a gris:</b> umbral no calibrado sin foto de la intrusa 1x3 blanca.")
story.append(Paragraph("11. Codigo", H1))
txt("Estructura: <i>vision/</i> (acquisition, calibration, segmentation, features, decision_tree, inventory, visualization), "
    "<i>tools/</i> (analyze_thresholds, evaluate, check_resolution, tune_hsv, make_synthetic, make_report), <i>gui/</i> y <i>app.py</i> (interfaz Tkinter), <i>config.yaml</i> (todos los umbrales).")

SimpleDocTemplate(f"{R}/results/informe.pdf", pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm).build(story)
print("OK", f"{R}/results/informe.pdf")
