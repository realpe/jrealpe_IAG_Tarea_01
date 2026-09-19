#!/usr/bin/env python3
"""
Mide la brecha de dominio entre el corpus de entrenamiento y los casos reales.

QUE PREGUNTA RESPONDE
---------------------
Los centroides se construyeron con Bitext, un corpus generico de comercio
electronico traducido del ingles. Los casos de prueba son espanol colombiano
escrito para EcoMarket. Si los dos dominios no coinciden, el clasificador esta
midiendo su capacidad de reconocer un idioma que no es el que va a recibir.

La medicion es directa: para cada texto se calcula su similitud con el centroide
mas cercano. Si la distribucion de los casos de prueba queda sistematicamente
por debajo de la de los ejemplos del propio dataset, la transferencia fallo.

POR QUE ESTE ARCHIVO EXISTE
---------------------------
La cifra aparecia antes armada a mano con datos de dos corridas distintas —el
p25 salia de la sonda y el maximo del comparador de politicas—, y al reescribir
el conjunto de prueba dejo de ser exacta. Una afirmacion que sostiene la
conclusion de una fase tiene que salir de un solo comando reproducible.

USO
    python brecha_dominio.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from capa1_semantica import RUTA_CACHE, Clasificador, embed_lote
from evaluar_clasificador import cargar_prueba

AQUI = Path(__file__).parent


def cuantiles(v: np.ndarray) -> str:
    return (f"min {v.min():.3f}  p5 {np.percentile(v, 5):.3f}  "
            f"p25 {np.percentile(v, 25):.3f}  mediana {np.median(v):.3f}  "
            f"p75 {np.percentile(v, 75):.3f}  max {v.max():.3f}")


def main() -> None:
    clf = Clasificador()
    if not RUTA_CACHE.exists():
        raise SystemExit("Falta el cache. Ejecuta:  python capa1_semantica.py construir")

    # Entrenamiento: similitud de cada ejemplo con SU PROPIO centroide. Es la
    # referencia de "asi se ve un mensaje que el sistema reconoce".
    z = np.load(RUTA_CACHE, allow_pickle=True)
    V, etq = z["vectores"], z["etiquetas"]
    indice = {n: i for i, n in enumerate(clf.intenciones)}
    entren = np.array([float(v @ clf.C[indice[e]]) for v, e in zip(V, etq)])

    casos = cargar_prueba()
    P = embed_lote([c["texto"] for c in casos])
    with np.errstate(all="ignore"):
        prueba = (P @ clf.C.T).max(axis=1)

    print("=" * 74)
    print("BRECHA DE DOMINIO: similitud con el centroide mas cercano")
    print("=" * 74)
    print(f"  entrenamiento (Bitext)  n={len(entren):5d}  {cuantiles(entren)}")
    print(f"  prueba (EcoMarket)      n={len(prueba):5d}  {cuantiles(prueba)}")

    p25 = float(np.percentile(entren, 25))
    p05 = float(np.percentile(entren, 5))
    sobre25 = int((prueba >= p25).sum())
    sobre05 = int((prueba >= p05).sum())

    print("\n" + "-" * 74)
    print(f"  casos de prueba que alcanzan el p25 del entrenamiento ({p25:.3f}): "
          f"{sobre25}/{len(prueba)}  ({sobre25 / len(prueba):.0%})")
    print(f"  casos de prueba que alcanzan el p5  del entrenamiento ({p05:.3f}): "
          f"{sobre05}/{len(prueba)}  ({sobre05 / len(prueba):.0%})")
    print(f"  desplazamiento de la mediana: "
          f"{np.median(entren):.3f} -> {np.median(prueba):.3f}  "
          f"({np.median(prueba) - np.median(entren):+.3f})")

    # Desglose por grupo: sirve para ver si la brecha afecta por igual a los
    # casos comunes y a los del nucleo duro, que son preguntas distintas.
    print("\n  Por grupo del conjunto de prueba:")
    grupos = sorted({c.get("grupo", "sin_grupo") for c in casos})
    for g in grupos:
        sel = np.array([c.get("grupo") == g for c in casos])
        v = prueba[sel]
        print(f"    {g:26s} n={len(v):2d}  mediana {np.median(v):.3f}  "
              f"max {v.max():.3f}  sobre p25: {int((v >= p25).sum())}/{len(v)}")

    destino = AQUI / "modelo" / "brecha_dominio.json"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps({
        "entrenamiento": {"n": len(entren), "p5": p05, "p25": p25,
                          "mediana": float(np.median(entren))},
        "prueba": {"n": len(prueba), "mediana": float(np.median(prueba)),
                   "max": float(prueba.max()), "min": float(prueba.min())},
        "sobre_p25": sobre25, "sobre_p5": sobre05,
    }, indent=1), encoding="utf-8")
    print(f"\n-> {destino.name}")


if __name__ == "__main__":
    main()
