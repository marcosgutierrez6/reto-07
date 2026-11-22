"""8a. Interpretación (nivel 3): inventario, comparación con la colección completa y total de tetones."""
from collections import Counter
import pandas as pd


def inventory(pieces, cfg, csv=None, imprimir=True):
    """Devuelve un dict con: tabla (tipo x color con totales), coleccion (por clase: encontradas/esperadas/estado),
    faltan, desconocidas [(id, motivo)], por_tipo, por_color, tetones (total de la escena) y n.
    Si se da `csv` guarda <csv> (tipo x color) y <csv sin _inventario>_coleccion.csv."""
    ok = [p for p in pieces if p["label"] != "DESCONOCIDO"]
    cuenta, uni = Counter(p["label"] for p in ok), cfg.get("unidades", {})
    filas = []
    for c in cfg["clases"]:                          # la colección completa de config.yaml
        esp, n = uni.get(c, 1), cuenta.get(c, 0)
        filas.append({"clase": c, "encontradas": n, "esperadas": esp, "estado": "ok" if n == esp else "FALTA" if n < esp else "SOBRA"})
    col = pd.DataFrame(filas)
    faltan = [f"{r.clase}" + (f" (faltan {r.esperadas - r.encontradas})" if r.esperadas > 1 else "") for r in col.itertuples() if r.encontradas < r.esperadas]
    tab = (pd.crosstab(pd.Series([p["tipo"] for p in ok], name="tipo"), pd.Series([p["color"] for p in ok], name="color"),
                       margins=True, margins_name="TOTAL") if ok else pd.DataFrame())
    # tetones de todas las piezas con huella medible (incluidas las desconocidas de tipo no permitido)
    tetones = sum(int(a) * int(b) for p in pieces if p["tipo"] != "?" for a, b in [p["tipo"].split("x")])
    r = {"tabla": tab, "coleccion": col, "faltan": faltan, "n": len(pieces), "tetones": tetones,
         "desconocidas": [(p["id"], p["motivo"]) for p in pieces if p["label"] == "DESCONOCIDO"],
         "por_tipo": dict(Counter(p["tipo"] for p in ok)), "por_color": dict(Counter(p["color"] for p in ok))}
    if imprimir:
        print(f"\nINVENTARIO: {r['n']} piezas · {tetones} tetones · {len(r['desconocidas'])} DESCONOCIDAS")
        print(tab.to_string() if ok else "(sin piezas reconocidas)")
        print("Por tipo:", r["por_tipo"], "· Por color:", r["por_color"])
        print("FALTAN de la colección:", ", ".join(faltan) if faltan else "ninguna")
        for i, m in r["desconocidas"]: print(f"  DESCONOCIDO #{i}: {m}")
    if csv:
        tab.to_csv(csv); col.to_csv(csv.replace("_inventario", "_coleccion"), index=False)
    return r
