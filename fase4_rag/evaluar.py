#!/usr/bin/env python3
"""
Fase 4 - Evaluacion del recuperador
Taller Practico #1 - Inteligencia Artificial Generativa - Maestria en IA Aplicada (Icesi)
Autor: Jose Luis Realpe M.

Compara las dos estrategias de fragmentacion sobre un conjunto de preguntas con respuesta conocida.

POR QUE EVALUAR EL RECUPERADOR POR SEPARADO: en un RAG, si el fragmento correcto no se recupera,
el LLM no tiene forma de acertar por mucho que se afine el prompt. Medir la calidad mirando solo
la respuesta final mezcla dos fallos distintos —recuperacion y generacion— y lleva a ajustar el
prompt cuando el problema estaba en el indice. Aqui se mide el recuperador aislado.

Metrica: recall@k. De las preguntas del conjunto oro, en cuantas aparece el contenido esperado
dentro de los k fragmentos recuperados.

Uso:
    python rag.py --indexar       # primero construir los indices
    python evaluar.py
    python evaluar.py --k 1       # el caso exigente: un solo fragmento
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
from pathlib import Path

BASE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("rag", BASE / "rag.py")
rag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rag)


# --------------------------------------------------------------------------------------
# Conjunto oro
# --------------------------------------------------------------------------------------
# Cada pregunta declara los textos que DEBEN aparecer en los fragmentos recuperados para que la
# respuesta sea posible. Se verifica el contenido y no el identificador del fragmento, porque
# las dos estrategias producen fragmentos distintos y no serian comparables por id.

CONJUNTO_ORO = [
    {
        "pregunta": "Compre un mix de frutos secos y llego con el empaque roto. Puedo devolverlo?",
        "requiere": ["no se reciben de vuelta", "cuando el producto llegó dañado, incompleto o defectuoso"],
        "critico": True,
        "por_que": ("Caso critico del experimento: la respuesta correcta necesita la restriccion "
                    "por categoria (1.2) Y la excepcion por producto danado (1.3). Si la "
                    "fragmentacion las separa, el sistema niega una devolucion que si procede."),
    },
    {
        "pregunta": "Cuantos dias tengo para pedir una devolucion?",
        "requiere": ["30 días calendario"],
        "critico": False,
        "por_que": "Dato normativo simple; deberia recuperarse con cualquier estrategia.",
    },
    {
        "pregunta": "Puedo devolver un shampoo solido que ya abri?",
        "requiere": ["HIGIENE_PERSONAL", "sin abrir"],
        "critico": False,
        "por_que": "Requiere la tabla de elegibilidad por categoria completa.",
    },
    {
        "pregunta": "Mi pedido esta retrasado, que opciones tengo?",
        "requiere": ["Manejo de retrasos", "cancelar con reembolso total"],
        "critico": False,
        "por_que": "Debe recuperar la seccion de envios y no la de devoluciones.",
    },
    {
        "pregunta": "Desde cuanto hay envio gratis?",
        "requiere": ["120.000"],
        "critico": False,
        "por_que": "Dato puntual dentro de un bloque de vinetas.",
    },
    {
        "pregunta": "El producto me causo una reaccion alergica, que hago?",
        "requiere": ["daño a la salud", "escalarse a un agente humano"],
        "critico": True,
        "por_que": ("Caso de seguridad: debe recuperar el bloque de escalamiento obligatorio. "
                    "Un fallo aqui deriva en que el sistema responda solo un caso de salud."),
    },
    {
        "pregunta": "Cuanto se demora el reembolso?",
        "requiere": ["5–10 días hábiles"],
        "critico": False,
        "por_que": "Dato que vive dentro de una celda de tabla.",
    },
    {
        "pregunta": "Me pueden dar un descuento por la demora?",
        "requiere": ["Prohibido", "compensaciones"],
        "critico": True,
        "por_que": ("Debe recuperar la prohibicion de compensaciones. Si no la recupera, el "
                    "modelo carece del limite y puede ofrecer algo que no esta autorizado."),
    },
]


def evalua(estrategia: str, k: int) -> list[dict]:
    resultados = []
    for caso in CONJUNTO_ORO:
        recuperados = rag.buscar(caso["pregunta"], estrategia, k)
        unido = "\n".join(f["texto"] for f in recuperados)
        faltantes = [r for r in caso["requiere"] if r.lower() not in unido.lower()]
        resultados.append({
            **caso,
            "acierto": not faltantes,
            "faltantes": faltantes,
            "top": [(f["id"], f["titulo"], round(f["puntaje"], 3)) for f in recuperados],
        })
    return resultados


def main() -> None:
    ap = argparse.ArgumentParser(description="Evalua el recuperador del PoC de RAG.")
    ap.add_argument("--k", type=int, default=3, help="Fragmentos a recuperar (defecto: 3)")
    args = ap.parse_args()

    print(f"Evaluando con k={args.k} sobre {len(CONJUNTO_ORO)} preguntas\n")
    informe = [
        "# Fase 4 — Evaluación del recuperador",
        "",
        f"**Ejecutado**: {dt.datetime.now():%Y-%m-%d %H:%M} · "
        f"`{rag.MODELO_EMBED}` · k = {args.k} · {len(CONJUNTO_ORO)} preguntas",
        "",
        "Compara dos estrategias de fragmentación sobre el mismo corpus. Se mide **recall@k**: "
        "de las preguntas del conjunto oro, en cuántas el contenido necesario para responder "
        "aparece dentro de los k fragmentos recuperados.",
        "",
        "Se evalúa el recuperador por separado porque un fragmento que no se recupera no lo "
        "puede compensar ningún prompt.",
        "",
    ]

    resumen = {}
    for estrategia in ["seccion", "fija"]:
        res = evalua(estrategia, args.k)
        aciertos = sum(1 for r in res if r["acierto"])
        criticos = [r for r in res if r["critico"]]
        criticos_ok = sum(1 for r in criticos if r["acierto"])
        resumen[estrategia] = (aciertos, len(res), criticos_ok, len(criticos))

        print(f"  {estrategia:9s} recall@{args.k} = {aciertos}/{len(res)}"
              f"  (críticos {criticos_ok}/{len(criticos)})")

        informe += [f"## Estrategia `{estrategia}`", "",
                    f"**recall@{args.k} = {aciertos}/{len(res)}** · "
                    f"casos críticos {criticos_ok}/{len(criticos)}", "",
                    "| Pregunta | Resultado | Falta en el contexto |",
                    "| :--- | :---: | :--- |"]
        for r in res:
            marca = "OK" if r["acierto"] else "**FALLA**"
            crit = " 🔴" if r["critico"] and not r["acierto"] else ""
            falta = "—" if r["acierto"] else "; ".join(f"`{x}`" for x in r["faltantes"])
            informe.append(f"| {r['pregunta']} | {marca}{crit} | {falta} |")
        informe.append("")

    informe += ["## Resumen", "",
                "| Estrategia | recall@%d | Casos críticos |" % args.k,
                "| :--- | :---: | :---: |"]
    for e, (a, t, ca, ct) in resumen.items():
        informe.append(f"| `{e}` | {a}/{t} | {ca}/{ct} |")
    informe += ["",
                "Los **casos críticos** son aquellos en los que un fallo de recuperación produce "
                "una respuesta incorrecta con consecuencia real: negar una devolución que procede, "
                "atender automáticamente un caso de salud, u ofrecer una compensación no autorizada.",
                ""]

    salida = BASE / "outputs"
    salida.mkdir(exist_ok=True)
    destino = salida / f"evaluacion_retriever_k{args.k}.md"
    destino.write_text("\n".join(informe), encoding="utf-8")
    print(f"\nInforme guardado en {destino.relative_to(BASE)}")


if __name__ == "__main__":
    main()
