#!/usr/bin/env python3
"""
Simula la cascada hibrida SIN volver a llamar al modelo.

LA IDEA
-------
Los centroides cuestan milisegundos y aciertan 46,5 %. El clasificador por
prompt cuesta ~15 segundos y acierta 83,7 %. El hibrido busca pagar los
segundos solo donde hacen falta:

    capa 0 dispara            -> humano_exclusivo        (0 ms,  determinista)
    la v3 decide con holgura  -> se queda el centroide   (~30 ms)
    la v3 DEGRADA a copiloto  -> se consulta al modelo   (~15 s)

POR QUE NO HAY UN UMBRAL NUEVO
------------------------------
`decidir_v3` ya devuelve una razon cada vez que degrada: piso de confianza no
alcanzado, o margen entre carriles insuficiente. Esa razon ES la senal de duda,
y ya fue elegida y documentada al fijar la v3. Reutilizarla mantiene el numero
de parametros ajustados igual que antes.

Esto no es cosmetico. Con 43 casos no se puede separar validacion de prueba
(ver §12 del informe), asi que cada umbral que se barra mirando esos 43 casos
es un grado de libertad mas ajustado al conjunto. El hibrido, formulado asi, no
agrega ninguno. El barrido del final existe solo como diagnostico y esta
rotulado como tal: sus numeros NO son el resultado que se reporta.

POR QUE SE PUEDE SIMULAR SIN INFERENCIA
---------------------------------------
`comparar_clasificadores.py` ya guardo la respuesta del modelo para cada uno de
los 43 casos en `modelo/resultados_comparacion.json`. El hibrido nunca produce
una respuesta que no este en ese archivo: para cada caso elige entre la del
centroide y la del modelo, y las dos ya estan calculadas. Cero llamadas.

La consecuencia practica: se puede saber si vale la pena implementarlo ANTES de
implementarlo.

USO
    python simular_hibrido.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import capa0_reglas
import politica_v2
from capa1_semantica import Clasificador, embed_lote
from evaluar_clasificador import CARRILES, SUPERVISION, cargar_prueba

AQUI = Path(__file__).parent
RUTA_UMBRALES = AQUI / "modelo" / "umbrales_por_intencion.json"
RUTA_COMPARACION = AQUI / "modelo" / "resultados_comparacion.json"

# Costos medidos, no estimados. El de los centroides sale de la corrida de
# comparar_clasificadores.py; el del prompt es el promedio real de 43 llamadas.
SEG_CENTROIDES = 0.03
SEG_CAPA0 = 0.0


# --------------------------------------------------------------------------------------

def metricas(casos: list[dict], predichos: list[str]) -> dict:
    """Identica a la de comparar_clasificadores.py, para que los numeros sean
    comparables sin reinterpretarlos."""
    ok = 0
    brecha = {1: 0, 2: 0}
    for c, pred in zip(casos, predichos):
        real = c["carril"]
        if pred == real:
            ok += 1
        else:
            d = SUPERVISION[real] - SUPERVISION[pred]
            if d > 0:
                brecha[d] += 1
    return {"aciertos": ok, "total": len(casos),
            "brecha1": brecha[1], "brecha2": brecha[2],
            "copiloto": sum(1 for p in predichos if p == "copiloto")}


def linea(nombre: str, m: dict, seg: float, escalados: str = "—") -> str:
    return (f"  {nombre:32s} {m['aciertos']:>2d}/{m['total']} = "
            f"{m['aciertos'] / m['total']:5.1%}   "
            f"brecha1 {m['brecha1']:>2d}   brecha2 {m['brecha2']:>2d}   "
            f"{seg:6.2f} s/caso   escala al LLM {escalados}")


# --------------------------------------------------------------------------------------

def main() -> None:
    if not RUTA_COMPARACION.exists():
        raise SystemExit(
            f"Falta {RUTA_COMPARACION.name}. Corre antes:\n"
            f"    python comparar_clasificadores.py")

    comp = json.loads(RUTA_COMPARACION.read_text(encoding="utf-8"))
    # Se indexa por texto y no por posicion: si el conjunto de prueba cambia de
    # orden o de tamano, un desfase silencioso mezclaria las respuestas.
    del_llm = {d["texto"]: d for d in comp["detalle"]}

    casos = cargar_prueba()
    faltan = [c["texto"] for c in casos if c["texto"] not in del_llm]
    if faltan:
        raise SystemExit(
            f"{len(faltan)} caso(s) de prueba.jsonl no estan en "
            f"{RUTA_COMPARACION.name}. El conjunto cambio desde la ultima "
            f"comparacion; vuelve a correr comparar_clasificadores.py.")

    print(f"{len(casos)} casos · respuestas del modelo reproducidas de "
          f"{RUTA_COMPARACION.name}")
    print(f"modelo {comp['modelo']} · {comp['segundos_por_caso']} s/caso medidos\n")

    # ---------- capa 0 ----------
    r0 = [capa0_reglas.evaluar(c["texto"], pedido=c.get("pedido"),
                               devoluciones_60d=c.get("devoluciones_60d", 0))
          for c in casos]
    escala0 = [r["escala"] for r in r0]

    # ---------- capa 1 con la v3, guardando la RAZON ----------
    clf = Clasificador()
    umbrales = json.loads(RUTA_UMBRALES.read_text(encoding="utf-8"))
    idx = [i for i, e in enumerate(escala0) if not e]
    V = embed_lote([casos[i]["texto"] for i in idx])
    with np.errstate(all="ignore"):
        S = V @ clf.C.T

    pred_v3: list[str] = ["humano_exclusivo"] * len(casos)
    dudoso: list[bool] = [False] * len(casos)   # ¿la v3 degrado por duda?
    razon: list[str | None] = [None] * len(casos)
    conf: list[float] = [1.0] * len(casos)      # 1.0 para los que resolvio la capa 0

    for fila, i in zip(S, idx):
        orden = np.argsort(-fila)
        conf[i] = float(fila[orden[0]])
        carril, motivo = politica_v2.decidir_v3(clf, umbrales, fila, orden)
        pred_v3[i] = carril
        # `motivo` no es None exactamente cuando la v3 degrado a copiloto por
        # falta de confianza o de margen. Ese es el criterio de escalamiento:
        # no se inventa uno nuevo, se reutiliza el que ya define la politica.
        dudoso[i] = motivo is not None
        razon[i] = motivo

    pred_llm = [del_llm[c["texto"]]["prompt"] for c in casos]

    # ---------- las tres configuraciones ----------
    pred_a = pred_v3
    pred_b = ["humano_exclusivo" if e else p for e, p in zip(escala0, pred_llm)]
    pred_h = [
        "humano_exclusivo" if e else (llm if d else v3)
        for e, d, v3, llm in zip(escala0, dudoso, pred_v3, pred_llm)
    ]

    n_esc = sum(1 for e, d in zip(escala0, dudoso) if not e and d)
    frac = n_esc / len(casos)
    seg_h = (frac * comp["segundos_por_caso"]
             + (1 - frac) * SEG_CENTROIDES)

    ma, mb, mh = (metricas(casos, p) for p in (pred_a, pred_b, pred_h))

    print("=" * 100)
    print("SIMULACION DE LA CASCADA HIBRIDA — sin llamadas nuevas al modelo")
    print("=" * 100)
    print(linea("A · centroides (v3)", ma, SEG_CENTROIDES, "0 %"))
    print(linea("B · prompt (con capa 0)", mb, comp["segundos_por_caso"], "100 %"))
    print(linea("H · hibrido por duda de la v3", mh, seg_h,
                f"{n_esc}/{len(casos)} = {frac:.0%}"))

    ahorro = 1 - seg_h / comp["segundos_por_caso"]
    perdida = mb["aciertos"] - mh["aciertos"]
    print(f"\n  El hibrido ahorra {ahorro:.0%} del tiempo del prompt y "
          f"{'pierde' if perdida > 0 else 'gana'} {abs(perdida)} acierto(s) "
          f"frente a B.")
    if mh["brecha2"] > 0:
        print(f"  *** ATENCION: brecha2 = {mh['brecha2']}. El hibrido manda al "
              f"carril automatico un caso que exige un humano. Se descarta. ***")

    # ---------- de donde sale cada acierto ----------
    print("\n" + "=" * 100)
    print("DESCOMPOSICION: quien decide cada caso y con que resultado")
    print("=" * 100)
    cubos = {"capa 0": [0, 0], "centroide (sin duda)": [0, 0], "LLM (por duda)": [0, 0]}
    for c, e, d, ph in zip(casos, escala0, dudoso, pred_h):
        k = "capa 0" if e else ("LLM (por duda)" if d else "centroide (sin duda)")
        cubos[k][1] += 1
        cubos[k][0] += ph == c["carril"]
    for k, (ok, n) in cubos.items():
        pct = f"{ok / n:5.1%}" if n else "    —"
        print(f"  {k:24s} {ok:>2d}/{n:<2d} = {pct}")

    print("\n  La fila del medio es la que justifica el hibrido: son los casos que")
    print("  el centroide resuelve sin pagar segundos. Si su exactitud es baja, la")
    print("  cascada esta dejando pasar errores para ahorrar tiempo.")

    # ---------- casos donde el hibrido pierde contra B ----------
    peores = [(c, v3, llm) for c, e, d, v3, llm in
              zip(casos, escala0, dudoso, pred_v3, pred_llm)
              if not e and not d and v3 != c["carril"] and llm == c["carril"]]
    if peores:
        print("\n" + "=" * 100)
        print("EL COSTO DEL HIBRIDO: el centroide decidio sin dudar y se equivoco")
        print("=" * 100)
        print("  Casos que B acierta y H falla, porque la v3 no los marco como dudosos.")
        print("  Son el precio exacto de no consultar al modelo.\n")
        for c, v3, llm in peores:
            print(f"  real={c['carril']:17s} centroide={v3:17s} (LLM acertaba) "
                  f"{c['texto'][:44]}")

    # ---------- el piso de confianza como medidor de calidad de datos ----------
    # Segundo disparador, distinto del margen. El margen dice «no se entre que
    # dos carriles elegir»; el piso dice «esto no se parece a nada que conozca».
    # Un mensaje de nucleo duro en espanol natural queda lejos de todo centroide,
    # asi que su confianza es baja POR LA MISMA CAUSA por la que es riesgoso: la
    # brecha de dominio de la §6. El piso convierte en regla explicita lo que
    # hoy es una correlacion observada (§9.8).
    #
    # La tabla no sirve para elegir el valor mirando la exactitud —eso seria
    # ajustar contra el conjunto de prueba—. Sirve para lo contrario: el valor
    # se fija por politica y la tabla dice CUANTO LLM cuesta sostenerlo con los
    # datos actuales. Referencias de la §6: entrenamiento p5 0,748 y mediana
    # 0,857; prueba mediana 0,744.
    print("\n" + "=" * 100)
    print("PISO DE CONFIANZA — cuanto LLM cuesta cada nivel de exigencia")
    print("=" * 100)
    print("  Escala al modelo si la v3 dudo O si la confianza queda por debajo del piso.")
    print("  A medida que el entrenamiento se acerque al dominio real, la confianza sube,")
    print("  menos casos cruzan el piso y el uso del LLM baja sin tocar el umbral.\n")
    print(f"  {'piso':>6s}  {'escala':>7s}  {'exactitud':>9s}  {'brecha2':>7s}  {'s/caso':>7s}")
    for piso in (0.00, 0.75, 0.80, 0.85, 0.88, 0.92):
        pred, n = [], 0
        for c, e, d, cf, v3, llm in zip(casos, escala0, dudoso, conf, pred_v3, pred_llm):
            if e:
                pred.append("humano_exclusivo")
                continue
            if d or cf < piso:
                pred.append(llm)
                n += 1
            else:
                pred.append(v3)
        mm = metricas(casos, pred)
        f = n / len(casos)
        s = f * comp["segundos_por_caso"] + (1 - f) * SEG_CENTROIDES
        marca = "  <- propuesto" if abs(piso - 0.88) < 1e-9 else ""
        print(f"  {piso:6.2f}  {f:6.0%}   {mm['aciertos'] / mm['total']:8.1%}  "
              f"{mm['brecha2']:>7d}  {s:7.2f}{marca}")

    sin_duda_conf = [cf for e, d, cf in zip(escala0, dudoso, conf) if not e and not d]
    if sin_duda_conf:
        print(f"\n  Confianza de los {len(sin_duda_conf)} casos que el centroide resolvio "
              f"sin dudar: {min(sin_duda_conf):.3f} – {max(sin_duda_conf):.3f}")
        print("  Son los unicos que un piso puede llegar a rescatar para el camino barato.")

    # ---------- diagnostico, NO resultado ----------
    print("\n" + "=" * 100)
    print("DIAGNOSTICO — barrido de margen (NO es el resultado reportado)")
    print("=" * 100)
    print("  Estas filas existen para ver la FORMA del compromiso, no para elegir un")
    print("  valor. Elegir el mejor de esta tabla seria ajustar un parametro contra el")
    print("  conjunto de prueba, que es justo lo que la §12 declara como limite.\n")
    print(f"  {'margen':>7s}  {'escala':>7s}  {'exactitud':>9s}  {'brecha2':>7s}  {'s/caso':>7s}")
    # El tope es 1.01 y no 1.00 a proposito: `margen_entre_carriles` devuelve
    # 1.0 cuando ninguna otra intencion cae en otro carril, y con un umbral de
    # 1.00 esos casos no escalarian. La ultima fila debe ser «escala todo».
    for umbral in (0.00, 0.02, 0.03, 0.05, 0.08, 0.12, 1.01):
        pred, n = [], 0
        for k, (c, e) in enumerate(zip(casos, escala0)):
            if e:
                pred.append("humano_exclusivo")
                continue
            j = idx.index(k)
            fila = S[j]
            orden = np.argsort(-fila)
            m, _ = politica_v2.margen_entre_carriles(clf, fila, orden)
            if m < umbral:
                pred.append(pred_llm[k])
                n += 1
            else:
                pred.append(pred_v3[k])
        mm = metricas(casos, pred)
        f = n / len(casos)
        s = f * comp["segundos_por_caso"] + (1 - f) * SEG_CENTROIDES
        print(f"  {umbral:7.2f}  {f:6.0%}   {mm['aciertos'] / mm['total']:8.1%}  "
              f"{mm['brecha2']:>7d}  {s:7.2f}")

    # ---------- volcado ----------
    destino = AQUI / "modelo" / "resultados_hibrido.json"
    destino.write_text(json.dumps({
        "criterio": "escala al LLM cuando decidir_v3 degrada por piso o por margen",
        "modelo": comp["modelo"],
        "A_centroides": ma, "B_prompt": mb, "H_hibrido": mh,
        "escalados": n_esc, "fraccion_escalada": round(frac, 3),
        "segundos_por_caso": round(seg_h, 2),
        "por_decisor": {k: {"aciertos": v[0], "total": v[1]} for k, v in cubos.items()},
        "detalle": [{"texto": c["texto"], "real": c["carril"], "grupo": c.get("grupo"),
                     "capa0": e, "dudoso": d, "razon_v3": rz,
                     "centroide": v3, "llm": llm, "hibrido": ph}
                    for c, e, d, rz, v3, llm, ph in
                    zip(casos, escala0, dudoso, razon, pred_v3, pred_llm, pred_h)],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {destino.name}")


if __name__ == "__main__":
    main()
