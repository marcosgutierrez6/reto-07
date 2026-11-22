# Reto 07 - Inventario LEGO con visión artificial clásica

**Autor:** Marcos Gutiérrez

| Recurso | Enlace |
|---|---|
| Vídeo de la demo | https://youtu.be/yHbt5aCICo8 |
| Repositorio (código) | https://github.com/marcosgutierrez6/reto-07 |
| Drive (fotos y material) | https://drive.google.com/drive/u/2/folders/1R35zVPEsOiFWRcb7Qbb1JnXILw5mMd_8 |
| Informe (PDF) | [informe.pdf](informe.pdf) |

Las fotos del dataset (≈750 MB) no están en el repositorio por tamaño: están en la carpeta de Drive.

---

# LEGO vision (visión clásica, sin deep learning)

## Uso (interfaz gráfica)
Doble clic en **INICIAR.command** (Mac) o **INICIAR.bat** (Windows); o `python app.py`.
En Mac hace falta Tkinter: `brew install python-tk@3.13`.

## Colección y reglas (todo en `config.yaml`)
- **14 clases / 15 piezas**: 2x2 amarillo, marron, negro, gris · 2x3 rojo, gris · 2x4 azul (×2), gris · 2x6 rojo, marron, gris ·
  1x6 rojo, gris · 2x8 negro. (El marrón se escribe `marron`, sin tilde: OpenCV no dibuja acentos.)
- La cámara ve solo la **huella**: ladrillo y placa con la misma huella son el mismo tipo.
- **Tipo**: ancho y largo de `minAreaRect` en tetones (0,8 cm) deben ser casi enteros (`tol_tetones`); se ordena (menor×mayor) y debe estar en `tipos`
  (1x6, 2x2, 2x3, 2x4, 2x6, 2x8). 2x3 y 1x6 tienen la misma área: se separan por el ancho.
- **Color** (H circular, dentro de la máscara erosionada y sin brillos): reglas EN ORDEN — negro (V baja), blanco (intrusa), gris (S baja),
  amarillo, azul, rojo (H rojo-naranja con V y S altas) y marrón (mismo tono, V y S menores).
- **Clase** = tipo + color si está en `clases`; si no, `DESCONOCIDO` **con el motivo** (tipo no permitido, color fuera de la lista,
  medidas no enteras, forma no rectangular, combinación inexistente...). La 1x3 blanca intrusa sale así.
- **Piezas negras**: en una foto real son del mismo verde oscuro que el tapete (H≈72, S≈175), pero mucho más oscuras que su zona: lo que baja de `oscuro_ratio` (0,62) de la luminosidad local no se considera tapete.
- **Gris vs blanco**: depende de la luz. Calibra `blanco` con una foto que incluya la 1x3 blanca etiquetada como intrusa; mientras tanto la regla `blanco` es muy estricta para no confundir tus grises claros.
- **Escala sin marcadores**: `ancho_imagen_cm` = cm que abarca la foto en su lado largo (no depende de la resolución: JPG, PNG, HEIC).
- **Sombras**: un blob con la crominancia (ángulo a,b) del tapete y sin forma/tamaño de pieza válidos se ignora (y se avisa).
  Si dos piezas se tocan (forma no rectangular) se avisa. Con luz difusa y sin sombras duras todo funciona mejor.

## Flujo de calibración (pestaña *Calibración*)
1. *Clases…* edita la colección (y `unidades` en config.yaml para las piezas repetidas, p. ej. `2x4 azul: 2`).
2. *Etiquetar fotos*: «Añadir fotos…» (todas las piezas a la vez, posiciones y giros distintos; mínimo **10 mediciones por clase**, 20 la 2x4 azul).
   El árbol propone una clase; confirma con «Todo correcto» o corrige con el desplegable + clic (clic der. deshace).
   Opciones: las 14 clases, «intrusa / desconocido» y «ignorar (falsa detección)». Todo en `dataset/calibration/labels.csv`.
3. *Umbrales*: «Calcular umbrales» → gráficas ancho×largo, **S vs V** (negro/gris/blanco intrusa/sombra), **V vs H** y **L vs a** (rojo frente a marrón)
   y H vs S, con umbrales actuales y sugeridos (PNG en `results/calibracion/`); edita la tabla; «Guardar en config.yaml» (copia `.bak`);
   «Comprobar calibración» (% de aciertos y qué piezas fallan, con motivo).
Herramientas: *Ajustar colores (HSV)* y *Comprobar resolución*. **Evaluar**: etiqueta fotos de test distintas y pulsa «Evaluar».

## Inventario (nivel 3)
Pestaña *Analizar* y `main.py`: conteo por clase, tipo y color, nº de DESCONOCIDO con motivo, **qué piezas de la colección faltan**
y **total de tetones**. Se guarda `_inventario.csv` (tipo×color) y `_coleccion.csv` (por clase).

## Línea de comandos
`python main.py --image f.jpg | --folder d/ | --camera 0 | --ipcam URL [--debug]`, `python tools/evaluate.py`,
`python tools/make_synthetic.py dataset` (datos sintéticos de prueba), `python build_exe.py`.