"""Diff de parámetros de política entre dos campañas, por segmento.

Decisiones de matcheo (importan para no producir un diff que engañe):

- Los segmentos se matchean por la TUPLA DE CONDICIONES normalizada, nunca por
  `attribute_index` ni por ids. El índice es solo orden de carga en la UI y los
  `parameter_id` / `attribute_definition_id` son distintos en cada política.
- Los nombres de columna se normalizan a mayúsculas: la misma columna aparece como
  `withdraw_limit` en una política y `WITHDRAW_LIMIT` en otra, y sin normalizar el
  diff inventa un "eliminado" y un "agregado".
- Los valores de condición se toman como string literal. Pueden ser expresiones
  (`=in(A,B)`), así que no se parsean.
- Lo que no matchea NO se fuerza: va a los baldes `solo_a` / `solo_b`.
- En exceptions se compara nombre, contenido Y posición: insertar una exception en el
  medio cambia el resultado aunque ninguna otra se toque, porque la pipeline es ordenada.
"""
import json, sys

DIR = "/tmp/sim/policies"

POLICIES = {
    "BAU": (2721, 2159), "JOURNEY 1A": (2678, 2168), "VIP MP": (2722, 2161),
    "PISOS": (2679, 2165), "OPF": (2717, 2160), "RIESGO MED. SOW": (2723, 2163),
    "REACTIVACION": (2712, 2166), "ACTIVACION": (2719, 2167),
    "ADECUACION DE RENTA": (2720, 2164),
}


def col(c):
    """Nombre de columna sin prefijo de tabla y en mayúsculas."""
    return c.split(".")[-1].strip().upper()


def clave_segmento(s):
    """Clave estable de un segmento: sus condiciones ordenadas por columna."""
    partes = sorted((col(c["column"]), c["comparator"], str(c["value"]).strip())
                    for c in s.get("conditions", []))
    return " & ".join(f"{c}{cmp}{v}" for c, cmp, v in partes)


def etiqueta_segmento(s):
    """Etiqueta legible: rating upsell | rating bhv | rango de días."""
    ups = bhv = None
    lo = hi = None
    for c in s.get("conditions", []):
        n, v = col(c["column"]), str(c["value"]).strip()
        if "UPSELL" in n:
            ups = v
        elif "BEHAVIOR" in n:
            bhv = v
        elif "DAYS" in n:
            if c["comparator"].startswith(">"):
                lo = v
            else:
                hi = v
    dias = f"{lo}-{hi}" if lo and hi else (lo or hi or "")
    return "|".join(x for x in [ups, bhv, dias] if x) or "(sin etiqueta)"


def valores(s):
    """Valores de un setting o de una exception.

    Ojo: los settings los traen en `parameter_values` y las exceptions en
    `parameter_modify`. Leer sólo uno de los dos hace que el diff devuelva
    "sin cambios" en silencio, que es el peor modo de fallar.
    """
    items = s.get("parameter_values") or s.get("parameter_modify") or []
    return {col(p["column"]): str(p["value"]).strip() for p in items}


def cargar(pid):
    d = json.load(open(f"{DIR}/{pid}.json"))
    seg, fijo = {}, {}
    etiquetas = {}
    for s in d["settings"]:
        if s.get("is_fixed"):
            fijo.update(valores(s))
        else:
            k = clave_segmento(s)
            seg[k] = valores(s)
            etiquetas[k] = etiqueta_segmento(s)
    exc = [{"nombre": e["conditional_name"],
            "tipo": e.get("exception_type"),
            "mods": valores(e),
            "cond": clave_segmento(e)} for e in d["exceptions"]]
    return {"seg": seg, "fijo": fijo, "exc": exc, "etq": etiquetas,
            "nombre": d["policy"].get("name") or d["policy"].get("policy_name")}


def diff_dicts(a, b):
    """Devuelve (cambiados, solo_en_a, solo_en_b) comparando dos dicts planos."""
    ch = {k: (b[k], a[k]) for k in a if k in b and a[k] != b[k]}
    return ch, sorted(set(a) - set(b)), sorted(set(b) - set(a))


def main():
    salida = {}
    for pol, (pa, pb) in POLICIES.items():
        A, B = cargar(pa), cargar(pb)

        # --- segmentos ---
        comunes = [k for k in A["seg"] if k in B["seg"]]
        por_param = {}
        for k in comunes:
            ch, _, _ = diff_dicts(A["seg"][k], B["seg"][k])
            for p, (vb, va) in ch.items():
                por_param.setdefault(p, []).append({"seg": A["etq"][k], "de": vb, "a": va})

        # --- fijos y exceptions ---
        fch, fsa, fsb = diff_dicts(A["fijo"], B["fijo"])
        na = [e["nombre"] for e in A["exc"]]
        nb = [e["nombre"] for e in B["exc"]]
        exc_add = [n for n in na if n not in nb]
        exc_del = [n for n in nb if n not in na]
        mb = {e["nombre"]: e for e in B["exc"]}
        exc_mod = [e["nombre"] for e in A["exc"]
                   if e["nombre"] in mb and (e["mods"] != mb[e["nombre"]]["mods"]
                                             or e["cond"] != mb[e["nombre"]]["cond"])]
        # reordenamiento: comparar el orden relativo de las que están en ambas
        ca = [n for n in na if n in set(nb)]
        cb = [n for n in nb if n in set(na)]
        reordenadas = ca != cb

        salida[pol] = {
            "policy_a": {"id": pa, "name": A["nombre"]},
            "policy_b": {"id": pb, "name": B["nombre"]},
            "n_seg_a": len(A["seg"]), "n_seg_b": len(B["seg"]), "n_seg_match": len(comunes),
            "seg_solo_a": [A["etq"][k] for k in A["seg"] if k not in B["seg"]],
            "seg_solo_b": [B["etq"][k] for k in B["seg"] if k not in A["seg"]],
            "params": por_param,
            "fijos_cambiados": fch, "fijos_solo_a": fsa, "fijos_solo_b": fsb,
            "exc_agregadas": exc_add, "exc_eliminadas": exc_del,
            "exc_modificadas": exc_mod, "exc_reordenadas": reordenadas,
            "n_exc_a": len(na), "n_exc_b": len(nb),
        }

    json.dump(salida, open("/tmp/sim/policy_diff.json", "w"), ensure_ascii=False)

    # --- reporte a consola ---
    for pol, d in salida.items():
        print(f"\n{'='*70}\n{pol}   ({d['n_seg_match']}/{d['n_seg_a']} segmentos matchean"
              f" · {d['n_exc_a']} vs {d['n_exc_b']} exceptions)")
        if d["seg_solo_a"] or d["seg_solo_b"]:
            print(f"  ⚠ segmentos sin match — solo A: {d['seg_solo_a']} | solo B: {d['seg_solo_b']}")
        if not d["params"]:
            print("  parámetros segmentados: SIN CAMBIOS")
        for p, items in d["params"].items():
            deltas = set()
            for it in items:
                try:
                    deltas.add(round(float(it["a"]) - float(it["de"]), 4))
                except ValueError:
                    deltas.add(f"{it['de']}->{it['a']}")
            uniforme = f"delta uniforme {deltas.pop()}" if len(deltas) == 1 else f"{len(deltas)} deltas distintos"
            print(f"  {p:24s} {len(items):2d}/{d['n_seg_match']} segmentos · {uniforme}")
            if len(deltas) > 0:
                for it in items[:3]:
                    print(f"        {it['seg']:20s} {it['de']} -> {it['a']}")
                if len(items) > 3:
                    print(f"        ... y {len(items)-3} más")
        if d["fijos_cambiados"]:
            print("  fijos cambiados:", {k: f"{v[0]}->{v[1]}" for k, v in d["fijos_cambiados"].items()})
        if d["fijos_solo_a"]:
            print("  fijos nuevos:", d["fijos_solo_a"])
        if d["exc_agregadas"]:
            print("  exceptions agregadas:", d["exc_agregadas"])
        if d["exc_eliminadas"]:
            print("  exceptions eliminadas:", d["exc_eliminadas"])
        if d["exc_modificadas"]:
            print("  exceptions modificadas:", d["exc_modificadas"][:6],
                  f"(+{len(d['exc_modificadas'])-6})" if len(d["exc_modificadas"]) > 6 else "")
        if d["exc_reordenadas"]:
            print("  ⚠ exceptions REORDENADAS")


main()
