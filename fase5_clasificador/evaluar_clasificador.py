#!/usr/bin/env python3
"""
Evaluacion del clasificador completo: capa 0 (reglas) + capa 1 (semantica).

QUE PREGUNTA RESPONDE
---------------------
La pregunta central del experimento ya esta planteada por la linea base: la capa
0 acierta 6/6 en los casos de nucleo duro escritos de forma explicita y 0/9 en
los parafraseados. La capa semantica existe para responder si recupera alguno.

Si la respuesta es "ninguno", el hallazgo no es un fracaso: es evidencia de que
el riesgo de salud o legal no se detecta por texto de forma confiable, y respalda
la decision de diseno de que ese carril no se automatiza. Un resultado negativo
medido vale mas que uno positivo supuesto.

LA METRICA QUE MANDA
--------------------
`enrutamiento inseguro`: un caso enviado a un carril con MENOS supervision de la
que necesitaba. Se define sobre una escala de supervision:

    automatico = 0     derivacion = 0     copiloto = 1     humano_exclusivo = 2

Inseguro es predicho < real. El objetivo declarado en la Fase 1 (4.4) es cero.
La exactitud global no sirve como criterio de aceptacion: un clasificador que
manda todo a copiloto tendria pesima exactitud y cero enrutamientos inseguros, y
uno con 95 % de exactitud que falla justo en los casos de salud es inaceptable.

`derivacion` comparte el nivel 0 con `automatico` porque ninguno de los dos
involucra juicio humano. Confundirlos es un error de entrega —el cliente recibe
el canal equivocado— y se reporta aparte.

USO
    python evaluar_clasificador.py
    python evaluar_clasificador.py --calibrar     # barre umbrales de la capa 1
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

import capa0_reglas
import capa1_semantica
from capa1_semantica import Clasificador, embed_lote

AQUI = Path(__file__).parent
RUTA_PRUEBA = AQUI / "datos" / "prueba.jsonl"

SUPERVISION = {"automatico": 0, "derivacion": 0, "copiloto": 1, "humano_exclusivo": 2}
CARRILES = ["automatico", "derivacion", "copiloto", "humano_exclusivo"]


def cargar_prueba() -> list[dict]:
    casos = []
    for linea in RUTA_PRUEBA.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea:
            continue
        d = json.loads(linea)
        if "texto" in d:            # las demas lineas son comentarios del archivo
            casos.append(d)
    return casos


def clasificar_completo(casos: list[dict], clf: Clasificador) -> list[dict]:
    """Ejecuta el pipeline real: capa 0 primero, capa 1 solo para lo que pasa.

    Importa respetar este orden. Si se corrieran las dos capas en paralelo y se
    combinaran despues, se estaria midiendo algo que el sistema en produccion no
    hace.
    """
    r0 = [capa0_reglas.evaluar(c["texto"],
                               pedido=c.get("pedido"),
                               devoluciones_60d=c.get("devoluciones_60d", 0))
          for c in casos]

    pendientes = [i for i, r in enumerate(r0) if not r["escala"]]
    resultados: list[dict] = [dict(x) for x in r0]

    if pendientes:
        V = embed_lote([casos[i]["texto"] for i in pendientes])
        for i, r1 in zip(pendientes, clf.clasificar_vectores(V)):
            resultados[i] = r1
    return resultados


# --------------------------------------------------------------------------------------

def informe(casos: list[dict], preds: list[dict]) -> dict:
    matriz = defaultdict(Counter)
    inseguros, entregas_malas = [], []
    por_grupo = defaultdict(lambda: [0, 0])
    por_capa = Counter()

    for c, p in zip(casos, preds):
        real, pred = c["carril"], p["carril"]
        matriz[real][pred] += 1
        por_capa[p["capa"]] += 1

        g = c.get("grupo", "sin_grupo")
        por_grupo[g][1] += 1
        if real == pred:
            por_grupo[g][0] += 1
        elif SUPERVISION[pred] < SUPERVISION[real]:
            inseguros.append((c, p))
        elif {real, pred} == {"automatico", "derivacion"}:
            entregas_malas.append((c, p))

    aciertos = sum(matriz[r][r] for r in matriz)
    total = len(casos)

    print("=" * 78)
    print(f"MATRIZ DE CONFUSION   ({total} casos)")
    print("=" * 78)
    ancho = max(len(c) for c in CARRILES) + 2
    # El encabezado se arma fuera del f-string: una barra invertida dentro de la
    # parte expresion de un f-string es error de sintaxis hasta Python 3.11.
    encabezado = "real / predicho"
    print(f"{encabezado:>{ancho}} " + " ".join(f"{c[:10]:>11s}" for c in CARRILES)
          + f" {'recall':>8s}")
    for real in CARRILES:
        fila = matriz.get(real)
        if not fila:
            continue
        n = sum(fila.values())
        print(f"{real:>{ancho}} " + " ".join(f"{fila.get(p, 0):>11d}" for p in CARRILES)
              + f" {fila.get(real, 0) / n:>7.0%}")

    print(f"\nExactitud global        {aciertos}/{total} = {aciertos / total:.1%}")
    print(f"Resueltos por capa 0    {por_capa[0]}   |   por capa 1: {por_capa[1]}")

    print("\nPor grupo del conjunto de prueba:")
    for g, (ok, n) in sorted(por_grupo.items()):
        print(f"  {g:28s} {ok}/{n}  {ok / n:>6.0%}")

    print("\n" + "-" * 78)
    print(f"ENRUTAMIENTO INSEGURO: {len(inseguros)}   (objetivo 0)")
    print("-" * 78)
    for c, p in inseguros:
        print(f"  {c['carril']:17s} -> {p['carril']:12s} "
              f"conf={p.get('confianza', '—')}  {c['texto'][:60]}")

    if entregas_malas:
        print(f"\nEntregas al area equivocada (automatico <-> derivacion): "
              f"{len(entregas_malas)}")
        for c, p in entregas_malas:
            print(f"  {c['carril']:12s} -> {p['carril']:12s}  {c['texto'][:58]}")

    return {"total": total, "aciertos": aciertos, "inseguros": len(inseguros),
            "por_grupo": {g: v for g, v in por_grupo.items()}}


def detalle_nucleo_duro(casos: list[dict], preds: list[dict]) -> None:
    """El experimento concreto: que pasa con los parafraseados."""
    print("\n" + "=" * 78)
    print("NUCLEO DURO PARAFRASEADO — ¿aporta algo la capa semantica?")
    print("=" * 78)
    for c, p in zip(casos, preds):
        if c.get("grupo") != "nucleo_duro_parafraseado":
            continue
        ok = "SI " if p["carril"] == "humano_exclusivo" else "NO "
        via = "capa 0" if p["capa"] == 0 else f"capa 1 -> {p.get('intencion', '')}"
        print(f"  [{ok}] {via:34s} {c['texto'][:56]}")
    print("\n  Recordatorio: la capa 1 NO puede predecir humano_exclusivo, porque")
    print("  ninguna intencion del dataset mapea a ese carril. Un 'NO' aqui")
    print("  significa que la capa 0 no lo atrapo y nada mas lo va a atrapar.")


# --------------------------------------------------------------------------------------

def calibrar(casos: list[dict]) -> None:
    """Barre los dos umbrales de la capa 1 sobre el conjunto de prueba.

    ADVERTENCIA METODOLOGICA: calibrar y medir sobre el mismo conjunto infla el
    resultado. Se hace aqui por el tamano del conjunto (37 casos) y se deja
    declarado. Con mas datos el umbral se elige en un conjunto de validacion
    aparte del de prueba.
    """
    clf = Clasificador()
    no_escalan = [c for c in casos if not capa0_reglas.evaluar(c["texto"])["escala"]]
    V = embed_lote([c["texto"] for c in no_escalan])
    S = V @ clf.C.T
    orden = np.argsort(-S, axis=1)
    conf = np.array([S[i, orden[i, 0]] for i in range(len(S))])
    marg = np.array([S[i, orden[i, 0]] - S[i, orden[i, 1]] for i in range(len(S))])
    base = [clf.carriles[orden[i, 0]] for i in range(len(S))]

    print("\nCALIBRACION (solo casos que pasan la capa 0)")
    print(f"{'u_conf':>7s} {'u_marg':>7s} {'aciertos':>9s} {'inseguros':>10s} "
          f"{'degradados':>11s}")
    for uc in (0.0, 0.50, 0.55, 0.60, 0.65, 0.70):
        for um in (0.0, 0.02, 0.03, 0.05):
            ok = ins = deg = 0
            for c, cb, cf, mg in zip(no_escalan, base, conf, marg):
                pred = "copiloto" if (cf < uc or mg < um) else cb
                if pred != cb:
                    deg += 1
                if pred == c["carril"]:
                    ok += 1
                elif SUPERVISION[pred] < SUPERVISION[c["carril"]]:
                    ins += 1
            print(f"{uc:7.2f} {um:7.2f} {ok:>6d}/{len(no_escalan)} {ins:>10d} {deg:>11d}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrar", action="store_true")
    args = ap.parse_args()

    casos = cargar_prueba()
    # Dos garantias distintas, dos avisos distintos. Una etiqueta sin revisar
    # corrompe la medicion; un texto no reescrito la infla. No son lo mismo y el
    # informe no debe presentarlos como si lo fueran.
    sin_etiqueta = sum(1 for c in casos if not c.get("etiqueta_revisada"))
    sin_texto = sum(1 for c in casos if not c.get("texto_propio"))
    if sin_etiqueta:
        print(f"AVISO: {sin_etiqueta}/{len(casos)} etiquetas sin revisar por una persona.")
    if sin_texto:
        print(f"AVISO: {sin_texto}/{len(casos)} textos redactados por el asistente de IA.")
        print("  La independencia de fuente es parcial y las cifras estan infladas en esa medida.")
    if sin_etiqueta or sin_texto:
        print()

    if args.calibrar:
        calibrar(casos)
        return

    clf = Clasificador()
    print(f"Umbrales: confianza {capa1_semantica.UMBRAL_CONFIANZA} · "
          f"margen {capa1_semantica.UMBRAL_MARGEN}\n")
    preds = clasificar_completo(casos, clf)
    informe(casos, preds)
    detalle_nucleo_duro(casos, preds)


if __name__ == "__main__":
    main()
