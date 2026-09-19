#!/usr/bin/env python3
"""
Centroides contra prompt: la misma medicion para las dos aproximaciones.

QUE COMPARA
-----------
    A. capa 0 + centroides (politica v3)   el sistema medido en la Fase 5
    B. capa 0 + clasificador por prompt    la alternativa
    C. clasificador por prompt SOLO        sin la capa 0 delante

La C existe por una razon concreta. La capa semantica no puede emitir
`humano_exclusivo`, asi que en A la capa 0 es la unica defensa del nucleo duro.
El clasificador por prompt SI puede emitirlo, y conviene saber cuanto detecta
por su cuenta: si C acierta en los casos parafraseados, el filtro lexico deja de
ser la unica red.

MISMAS METRICAS QUE LA FASE 5
-----------------------------
Se reutilizan `SUPERVISION` y `cargar_prueba` de `evaluar_clasificador.py`, de
modo que los numeros son comparables con los ya publicados sin reinterpretarlos.

    brecha 1   necesitaba un humano y fue a copiloto     -> una demora
    brecha 2   necesitaba un humano y fue a automatico   -> un incidente

La exactitud global no es el criterio de aceptacion; la brecha 2 si.

ADVERTENCIA SOBRE EL COSTO
--------------------------
El clasificador por prompt tarda segundos por caso en lugar de milisegundos. La
corrida completa son 43 llamadas al modelo: entre 2 y 5 minutos con qwen3:14b.
El tiempo medido se reporta, porque es parte de la comparacion.

USO
    python comparar_clasificadores.py
    python comparar_clasificadores.py --modelo qwen2.5:7b
    python comparar_clasificadores.py --limite 10      # prueba rapida
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np

import capa0_reglas
import clasificador_llm
import politica_v2
from capa1_semantica import Clasificador, embed_lote
from evaluar_clasificador import CARRILES, SUPERVISION, cargar_prueba

AQUI = Path(__file__).parent
RUTA_UMBRALES = AQUI / "modelo" / "umbrales_por_intencion.json"


# --------------------------------------------------------------------------------------

def metricas(casos: list[dict], predichos: list[str]) -> dict:
    ok = cop = 0
    brecha = {1: 0, 2: 0}
    matriz = {r: {p: 0 for p in CARRILES} for r in CARRILES}
    grupos: dict[str, list[int]] = {}

    for c, pred in zip(casos, predichos):
        real = c["carril"]
        matriz[real][pred] += 1
        g = grupos.setdefault(c.get("grupo", "sin_grupo"), [0, 0])
        g[1] += 1
        if pred == real:
            ok += 1
            g[0] += 1
        else:
            d = SUPERVISION[real] - SUPERVISION[pred]
            if d > 0:
                brecha[d] += 1
        cop += int(pred == "copiloto")

    return {"aciertos": ok, "total": len(casos), "brecha1": brecha[1],
            "brecha2": brecha[2], "copiloto": cop, "matriz": matriz,
            "grupos": grupos}


def tabla(nombre: str, m: dict, segundos: float | None = None) -> str:
    t = (f"  {nombre:34s} {m['aciertos']:>2d}/{m['total']} = "
         f"{m['aciertos'] / m['total']:5.1%}  "
         f"brecha1 {m['brecha1']:>2d}   brecha2 {m['brecha2']:>2d}   "
         f"copiloto {m['copiloto']:>2d}")
    if segundos is not None:
        t += f"   {segundos:5.1f}s/caso"
    return t


# --------------------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default=clasificador_llm.MODELO_DEFECTO)
    ap.add_argument("--limite", type=int, default=0,
                    help="usar solo los primeros N casos (prueba rapida)")
    args = ap.parse_args()

    casos = cargar_prueba()
    if args.limite:
        casos = casos[:args.limite]
    print(f"{len(casos)} casos · modelo {args.modelo} · "
          f"temperatura {clasificador_llm.TEMPERATURA}\n")

    # ---------- capa 0, una sola vez para todos ----------
    r0 = [capa0_reglas.evaluar(c["texto"], pedido=c.get("pedido"),
                               devoluciones_60d=c.get("devoluciones_60d", 0))
          for c in casos]
    escala = [r["escala"] for r in r0]
    print(f"Capa 0 escala {sum(escala)} de {len(casos)}\n")

    # ---------- A: capa 0 + centroides (v3) ----------
    clf = Clasificador()
    umbrales = json.loads(RUTA_UMBRALES.read_text(encoding="utf-8"))
    idx = [i for i, e in enumerate(escala) if not e]
    V = embed_lote([casos[i]["texto"] for i in idx])
    with np.errstate(all="ignore"):
        S = V @ clf.C.T
    pred_a = ["humano_exclusivo"] * len(casos)
    for fila, i in zip(S, idx):
        orden = np.argsort(-fila)
        pred_a[i] = politica_v2.decidir_v3(clf, umbrales, fila, orden)[0]

    # ---------- B y C: clasificador por prompt ----------
    # Se llama UNA vez por caso y el resultado se usa para las dos variantes: B
    # respeta la cascada (la capa 0 decide primero) y C usa el veredicto del
    # modelo siempre. Asi la comparacion no depende de dos corridas distintas.
    print("Clasificando con el modelo…")
    llm, total_s = [], 0.0
    for n, c in enumerate(casos, 1):
        r = clasificador_llm.clasificar(c["texto"], modelo=args.modelo)
        llm.append(r)
        total_s += r["segundos"]
        print(f"\r  {n}/{len(casos)}  {total_s:5.1f}s", end="", flush=True)
    print()

    fallos = sum(1 for r in llm if not r["parseo_ok"])
    if fallos:
        print(f"  AVISO: {fallos} respuesta(s) no se pudieron parsear "
              f"-> se contaron como copiloto")

    pred_b = ["humano_exclusivo" if e else r["carril"]
              for e, r in zip(escala, llm)]
    pred_c = [r["carril"] for r in llm]

    ma, mb, mc = (metricas(casos, p) for p in (pred_a, pred_b, pred_c))
    seg = total_s / len(casos)

    print("\n" + "=" * 92)
    print("COMPARACION")
    print("=" * 92)
    print(tabla("A · capa 0 + centroides (v3)", ma, 0.03))
    print(tabla("B · capa 0 + prompt", mb, seg))
    print(tabla("C · prompt solo, sin capa 0", mc, seg))
    print("\n  brecha2 = enviado al carril automatico algo que exigia un humano.")

    # ---------- el grupo que decide ----------
    print("\n" + "=" * 92)
    print("NUCLEO DURO PARAFRASEADO — el grupo donde la capa semantica da 0/9")
    print("=" * 92)
    n_par = aciertos_b = aciertos_c = 0
    for c, e, r, pa in zip(casos, escala, llm, pred_a):
        if c.get("grupo") != "nucleo_duro_parafraseado":
            continue
        n_par += 1
        cb = "humano_exclusivo" if e else r["carril"]
        aciertos_b += cb == "humano_exclusivo"
        aciertos_c += r["carril"] == "humano_exclusivo"
        marca = "SI " if r["carril"] == "humano_exclusivo" else "NO "
        print(f"  [{marca}] prompt -> {r['carril']:17s} (centroides: {pa:16s}) "
              f"{c['texto'][:42]}")
        if r["justificacion"]:
            print(f"         {r['justificacion'][:82]}")
    if n_par:
        print(f"\n  centroides {0}/{n_par}   ·   prompt solo {aciertos_c}/{n_par}"
              f"   ·   capa 0 + prompt {aciertos_b}/{n_par}")

    # ---------- diferencias caso a caso ----------
    print("\n" + "=" * 92)
    print("CASOS DONDE A Y B DIFIEREN")
    print("=" * 92)
    hay = False
    for c, a, b, r in zip(casos, pred_a, pred_b, llm):
        if a == b:
            continue
        hay = True
        real = c["carril"]
        gana = "prompt" if b == real else ("centroides" if a == real else "ninguno")
        print(f"  real={real:17s} centroides={a:17s} prompt={b:17s} "
              f"[{gana}]  {c['texto'][:40]}")
    if not hay:
        print("  ninguno")

    # ---------- volcado ----------
    destino = AQUI / "modelo" / "resultados_comparacion.json"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps({
        "generado": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "modelo": args.modelo, "temperatura": clasificador_llm.TEMPERATURA,
        "n_casos": len(casos), "segundos_por_caso": round(seg, 2),
        "fallos_de_parseo": fallos,
        "A_centroides": ma, "B_capa0_mas_prompt": mb, "C_prompt_solo": mc,
        "detalle": [{"texto": c["texto"], "real": c["carril"],
                     "grupo": c.get("grupo"), "capa0_escala": e,
                     "centroides": a, "prompt": r["carril"],
                     "confianza_prompt": r["confianza"],
                     "justificacion": r["justificacion"],
                     "segundos": r["segundos"], "parseo_ok": r["parseo_ok"]}
                    for c, e, a, r in zip(casos, escala, pred_a, llm)],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {destino.name}")


if __name__ == "__main__":
    main()
