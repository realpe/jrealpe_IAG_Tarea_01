#!/usr/bin/env python3
"""
Sonda: ¿la 'confianza' del clasificador mide algo?

LA HIPOTESIS QUE SE PONE A PRUEBA
---------------------------------
En la evaluacion, mensajes que no se parecen a nada del dataset —"mi bebe se
llevo el producto a la boca"— obtuvieron confianza 0.77 y se enrutaron al carril
automatico. Si la similitud coseno con el centroide mas cercano midiera de
verdad "esto se parece a algo que conozco", esos mensajes deberian puntuar bajo.

Hipotesis: nomic-embed-text tiene un PISO DE SIMILITUD alto. Dos textos en
espanol cualesquiera ya comparten bastante estructura como para dar coseno ~0.6
o mas, asi que el valor absoluto no distingue dentro de fuera de distribucion.

Como se falsa: se embeben tres grupos y se compara la distribucion de la
similitud maxima contra los 27 centroides.

  A. DENTRO   ejemplos del dataset que NO se usaron para el centroide
  B. NUCLEO   los parafraseados de salud y legal, que el sistema debe rechazar
  C. ABSURDO  frases sin ninguna relacion con atencion al cliente

Si A, B y C se solapan, el umbral de confianza es inservible y hay que quitarlo
en lugar de seguir ajustandolo. Si A queda claramente por encima, el umbral
sirve y estaba mal calibrado.

SEGUNDA PARTE: UMBRALES POR INTENCION
-------------------------------------
Un umbral global asume que todas las intenciones tienen centroides igual de
compactos, y no es cierto: una intencion redactada de muchas formas produce un
centroide flojo, con similitudes bajas incluso para sus propios ejemplos.

Por eso se calcula, para cada intencion y usando los vectores de entrenamiento
que quedaron en cache, el percentil 5 de la similitud de sus ejemplos con su
propio centroide. Un mensaje nuevo que no alcanza ese piso no se parece a esa
intencion ni siquiera al nivel de sus casos mas atipicos. Es un umbral con
significado empirico y no un numero elegido a ojo.

USO
    python sonda_confianza.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from capa1_semantica import (MUESTRAS_POR_INTENCION, RUTA_CACHE, RUTA_CENTROIDES,
                             Clasificador, embed_lote)

AQUI = Path(__file__).parent
DATOS = AQUI / "datos"

# Grupo C: deliberadamente ajenos al dominio, en el mismo idioma y registro.
# El idioma se mantiene para que la diferencia medida sea el TEMA y no el
# idioma, que es una variable distinta.
ABSURDO = [
    "La fotosintesis convierte la luz solar en energia quimica",
    "El teorema de Pitagoras relaciona los lados de un triangulo rectangulo",
    "Ayer llovio toda la tarde en el Valle del Cauca",
    "Mi perro aprendio a dar la pata la semana pasada",
    "La segunda guerra mundial termino en 1945",
    "Prefiero el cafe sin azucar por las mananas",
    "El motor de la moto necesita cambio de aceite cada 5000 kilometros",
    "Beethoven compuso nueve sinfonias completas",
]


def maximos(V: np.ndarray, C: np.ndarray) -> np.ndarray:
    return (V @ C.T).max(axis=1)


def resumen(nombre: str, v: np.ndarray) -> None:
    print(f"  {nombre:10s} n={len(v):3d}  "
          f"min {v.min():.3f}  p25 {np.percentile(v, 25):.3f}  "
          f"mediana {np.median(v):.3f}  p75 {np.percentile(v, 75):.3f}  "
          f"max {v.max():.3f}")


def main() -> None:
    clf = Clasificador()
    C = clf.C

    # --- A. Dentro de distribucion, ejemplos no vistos --------------------------
    df = pd.read_parquet(DATOS / "bitext_es.parquet").drop_duplicates(subset="instruction")
    dentro = []
    for intencion in clf.intenciones:
        sub = df[df["intent"] == intencion]
        # Se reproduce la misma muestra del entrenamiento para poder excluirla:
        # medir sobre los ejemplos que formaron el centroide daria un resultado
        # optimista por construccion.
        usados = set(sub.sample(min(MUESTRAS_POR_INTENCION, len(sub)),
                                random_state=42)["instruction"])
        libres = sub[~sub["instruction"].isin(usados)]
        if len(libres):
            dentro.extend(libres.sample(min(4, len(libres)),
                                        random_state=7)["instruction"].tolist())

    # --- B. Nucleo duro parafraseado -------------------------------------------
    nucleo = [json.loads(l)["texto"]
              for l in (DATOS / "prueba.jsonl").read_text(encoding="utf-8").splitlines()
              if l.strip() and json.loads(l).get("grupo") == "nucleo_duro_parafraseado"]

    print(f"Embebiendo {len(dentro)} + {len(nucleo)} + {len(ABSURDO)} textos")
    vA = maximos(embed_lote(dentro), C)
    vB = maximos(embed_lote(nucleo), C)
    vC = maximos(embed_lote(ABSURDO), C)

    print("\n" + "=" * 74)
    print("SIMILITUD MAXIMA CONTRA LOS 27 CENTROIDES")
    print("=" * 74)
    resumen("A DENTRO", vA)
    resumen("B NUCLEO", vB)
    resumen("C ABSURDO", vC)

    # El veredicto se hace explicito para que no dependa de leer la tabla: se
    # compara el piso de lo que el sistema DEBE aceptar con el techo de lo que
    # DEBE rechazar. Si se cruzan, ningun umbral separa los dos grupos.
    piso_dentro = np.percentile(vA, 5)
    techo_fuera = max(vB.max(), vC.max())
    print("\n" + "-" * 74)
    print(f"  piso de A (p5)              {piso_dentro:.3f}")
    print(f"  techo de B y C (maximo)     {techo_fuera:.3f}")
    if techo_fuera >= piso_dentro:
        print("\n  VEREDICTO: se solapan. NINGUN umbral global de confianza separa")
        print("  lo conocido de lo desconocido. El umbral debe quitarse, no ajustarse.")
    else:
        print(f"\n  VEREDICTO: hay separacion. Un umbral entre {techo_fuera:.3f} y "
              f"{piso_dentro:.3f} es defendible.")

    # --- Umbrales por intencion -------------------------------------------------
    if not RUTA_CACHE.exists():
        print("\n(sin cache de entrenamiento: no se calculan umbrales por intencion)")
        return

    z = np.load(RUTA_CACHE, allow_pickle=True)
    V, etq = z["vectores"], z["etiquetas"]
    print("\n" + "=" * 74)
    print("COMPACIDAD DE CADA CENTROIDE (similitud de sus propios ejemplos)")
    print("=" * 74)
    print(f"{'intencion':28s} {'p5':>7s} {'mediana':>9s}   (p5 = umbral propuesto)")
    umbrales = {}
    filas = []
    for i, intencion in enumerate(clf.intenciones):
        s = V[etq == intencion] @ C[i]
        umbrales[intencion] = float(np.percentile(s, 5))
        filas.append((umbrales[intencion], np.median(s), intencion))
    for p5, med, intencion in sorted(filas):
        print(f"{intencion:28s} {p5:7.3f} {med:9.3f}")

    destino = AQUI / "modelo" / "umbrales_por_intencion.json"
    destino.write_text(json.dumps(umbrales, indent=1), encoding="utf-8")
    print(f"\n-> {destino.name}")
    print("  Las intenciones de arriba son las de centroide mas flojo: sus propios")
    print("  ejemplos se le parecen poco, asi que son las menos confiables.")


if __name__ == "__main__":
    main()
