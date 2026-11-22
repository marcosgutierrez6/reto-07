"""Tema visual único (claro, alto contraste). Fija colores explícitos en TODOS los widgets para que se vean igual
con el modo oscuro o claro del sistema (en el modo oscuro Tk pone texto blanco por defecto: blanco sobre amarillo no se lee)."""
import tkinter as tk
from tkinter import font as tkfont, ttk

C = {"fondo": "#f3f4f6", "panel": "#ffffff", "texto": "#111827", "suave": "#6b7280", "borde": "#d1d5db",
     "cabecera": "#111827", "primario": "#1d4ed8", "primario_h": "#1e40af", "ok": "#15803d", "ok_h": "#166534",
     "peligro": "#b91c1c", "gris": "#e5e7eb", "gris_h": "#d1d5db", "visor": "#1f2937"}
# (fondo, texto) de cada tipo de aviso: todos con contraste AA
BANNER = {"ok": ("#dcfce7", "#14532d"), "aviso": ("#fef3c7", "#78350f"), "error": ("#fee2e2", "#7f1d1d"),
          "info": ("#dbeafe", "#1e3a8a"), "neutro": ("#e5e7eb", "#1f2937")}


def banner(parent, tipo="neutro", texto="", **kw):
    """Etiqueta de color con texto legible (colores explícitos)."""
    bg, fg = BANNER[tipo]
    kw = {"justify": "left", "anchor": "w", "padx": 10, "pady": 8, "wraplength": 400, **kw}
    return tk.Label(parent, text=texto, bg=bg, fg=fg, font=kw.pop("font", None) or tkfont.nametofont("TkDefaultFont"), **kw)


def pintar_banner(lbl, tipo, texto=None):
    bg, fg = BANNER[tipo]
    lbl.configure(bg=bg, fg=fg, **({} if texto is None else {"text": texto}))


def aplicar(root):
    """Configura fuentes, estilos ttk (tema clam) y opciones por defecto de los widgets clásicos de Tk."""
    for n in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont"):
        tkfont.nametofont(n).configure(size=12)
    base = tkfont.nametofont("TkDefaultFont")
    negrita = tkfont.Font(root, family=base.actual("family"), size=12, weight="bold")    # explícita: .copy() no heredaba el tamaño
    root._fuentes = [negrita]            # ¡guardar la referencia!: si Python borra el objeto Font, Tk vuelve a la fuente pequeña
    root.configure(bg=C["fondo"])
    s = ttk.Style(root); s.theme_use("clam")
    s.configure(".", background=C["fondo"], foreground=C["texto"], font=base, bordercolor=C["borde"],
                lightcolor=C["fondo"], darkcolor=C["fondo"], troughcolor=C["gris"], focuscolor=C["primario"], selectbackground=C["primario"])
    s.configure("TFrame", background=C["fondo"]); s.configure("Panel.TFrame", background=C["panel"])
    s.configure("TLabel", background=C["fondo"], foreground=C["texto"])
    s.configure("Suave.TLabel", foreground=C["suave"]); s.configure("Titulo.TLabel", font=(base.actual("family"), 16, "bold"))
    s.configure("Error.TLabel", foreground="#b91c1c")
    s.configure("TLabelframe", background=C["fondo"], bordercolor=C["borde"], borderwidth=1, relief="solid")
    s.configure("TLabelframe.Label", background=C["fondo"], foreground=C["texto"], font=negrita)
    def boton(nombre, bg, hover, fg="white", pad=(14, 9), font=negrita, borde=0):
        s.configure(nombre, background=bg, foreground=fg, padding=pad, font=font, borderwidth=borde, bordercolor=C["borde"],
                    focusthickness=0, relief="flat", anchor="center")
        s.map(nombre, background=[("disabled", "#cbd5e1"), ("pressed", hover), ("active", hover)],
              foreground=[("disabled", "#64748b")], bordercolor=[("active", C["suave"])])
    boton("Grande.TButton", C["primario"], C["primario_h"])                       # acción principal
    boton("Ok.TButton", C["ok"], C["ok_h"])                                       # confirmar / guardar
    boton("Sec.TButton", "white", C["gris"], fg=C["texto"], borde=1)             # acción secundaria
    boton("TButton", "white", C["gris"], fg=C["texto"], pad=(10, 6), font=base, borde=1)
    s.configure("TNotebook", background=C["fondo"], borderwidth=0, tabmargins=(8, 8, 8, 0))
    s.configure("Sub.TNotebook", background=C["fondo"], borderwidth=0, tabmargins=(0, 6, 0, 0))
    s.configure("Sub.TNotebook.Tab", padding=(12, 8), font=negrita, background=C["gris"], foreground=C["suave"], borderwidth=0)
    s.map("Sub.TNotebook.Tab", background=[("selected", "white")], foreground=[("selected", C["primario"])],
          padding=[("selected", (12, 8))], expand=[("selected", (0, 0, 0, 0))])
    s.configure("TNotebook.Tab", padding=(22, 10), font=negrita, background=C["gris"], foreground=C["suave"], borderwidth=0)
    s.map("TNotebook.Tab", background=[("selected", "white")], foreground=[("selected", C["primario"])],
          padding=[("selected", (22, 10))], expand=[("selected", (0, 0, 0, 0))])
    s.configure("Treeview", background="white", fieldbackground="white", foreground=C["texto"], rowheight=28, borderwidth=1)
    s.configure("Treeview.Heading", background=C["gris"], foreground=C["texto"], font=negrita, padding=6, relief="flat")
    s.configure("Compacto.Treeview", rowheight=24)
    s.map("Treeview", background=[("selected", C["primario"])], foreground=[("selected", "white")])
    s.map("Treeview.Heading", background=[("active", C["gris_h"])])
    for e in ("TCombobox", "TEntry", "TSpinbox"):
        s.configure(e, fieldbackground="white", background="white", foreground=C["texto"], arrowcolor=C["texto"], padding=6)
    s.map("TCombobox", fieldbackground=[("readonly", "white")], foreground=[("readonly", C["texto"])],
          selectbackground=[("readonly", "white")], selectforeground=[("readonly", C["texto"])])
    s.configure("Horizontal.TProgressbar", troughcolor=C["gris"], background=C["primario"], thickness=12, borderwidth=0)
    for w in ("TRadiobutton", "TCheckbutton"):
        s.configure(w, background=C["fondo"], foreground=C["texto"])
    # widgets clásicos de Tk: colores explícitos
    for k, v in {"*Listbox.background": "white", "*Listbox.foreground": C["texto"], "*Listbox.selectBackground": C["primario"],
                 "*Listbox.selectForeground": "white", "*Listbox.highlightThickness": 1, "*Listbox.highlightColor": C["primario"],
                 "*Listbox.highlightBackground": C["borde"], "*Listbox.relief": "flat", "*Listbox.activeStyle": "none",
                 "*Text.background": "white", "*Text.foreground": C["texto"], "*Text.relief": "flat", "*Text.highlightThickness": 1,
                 "*Text.highlightBackground": C["borde"], "*Text.padX": 8, "*Text.padY": 6,
                 "*Scale.background": C["fondo"], "*Scale.foreground": C["texto"], "*Scale.troughColor": "#cbd5e1",
                 "*Scale.highlightThickness": 0, "*Scale.activeBackground": C["primario"],
                 "*TCombobox*Listbox.background": "white", "*TCombobox*Listbox.foreground": C["texto"],
                 "*TCombobox*Listbox.selectBackground": C["primario"], "*TCombobox*Listbox.selectForeground": "white"}.items():
        root.option_add(k, v)
    return negrita


def cabecera(root, titulo, subtitulo):
    """Barra superior oscura con el título de la app."""
    f = tk.Frame(root, bg=C["cabecera"]); f.pack(side="top", fill="x")
    root._fuentes.append(tkfont.Font(root, size=17, weight="bold"))
    tk.Label(f, text=titulo, bg=C["cabecera"], fg="white", font=root._fuentes[-1]).pack(side="left", padx=(18, 10), pady=10)
    tk.Label(f, text=subtitulo, bg=C["cabecera"], fg="#9ca3af").pack(side="left")
    return f
