#!/usr/bin/env python3
"""
Capa 1: clasificador semantico por centroides de intencion.

QUE HACE Y POR QUE ASI
----------------------
La capa 0 (reglas lexicas) atrapa el nucleo duro. Lo que pasa ese filtro llega
aqui, y aqui se decide entre `automatico`, `copiloto` y `derivacion`.

El metodo es el mas simple que puede funcionar: se calcula el embedding de cada
mensaje de entrenamiento, se promedia por intencion para obtener 27 CENTROIDES,
y un mensaje nuevo se asigna a la intencion cuyo centroide le queda mas cerca
por similitud coseno. La intencion se traduce a carril con la tabla revisada en
`datos/mapeo_intencion_carril.csv`.

POR QUE CENTROIDE POR INTENCION Y NO POR CARRIL
-----------------------------------------------
Un carril agrupa intenciones que no se parecen entre si. El centroide de
`automatico` promediaria "donde esta mi pedido" con "que medios de pago
aceptan": el vector resultante no se parece a ninguna de las dos y queda en una
zona del espacio donde no vive ningun mensaje real. Con 27 centroides cada uno
representa un grupo coherente, y el carril se obtiene despues por tabla.

Como efecto secundario el sistema predice la intencion, que es lo que la
arquitectura de la Fase 1 dibuja en la caja "clasificador de intencion".

POR QUE CENTROIDES Y NO UN CLASIFICADOR ENTRENADO
-------------------------------------------------
Una regresion logistica sobre los embeddings daria algo mas de exactitud. Se
eligio el centroide por tres razones:
  - Es inspeccionable: se puede preguntar a que centroide se parecio un mensaje
    y cuanto, que es lo que exige el registro de auditoria de la Fase 1.
  - Agregar una intencion nueva cuesta promediar sus ejemplos, sin reentrenar.
  - No introduce hiperparametros que habria que justificar en la sustentacion.
La alternativa queda anotada como trabajo futuro; el codigo guarda los
embeddings en cache, asi que probarla despues no cuesta volver a inferir.

DOS UMBRALES, DOS PREGUNTAS DISTINTAS
-------------------------------------
  confianza = similitud con el mejor centroide
              -> ¿esto se parece a algo que conozco?
  margen    = diferencia entre el mejor y el segundo
              -> ¿estoy seguro de CUAL de los dos es?

Baja confianza significa mensaje fuera de distribucion. Margen bajo significa
que el mensaje esta entre dos intenciones. Los dos casos van a `copiloto`: ante
la duda se degrada al carril con supervision humana, por la asimetria de
consecuencias de la Fase 2 (3.6).

REQUISITO: ollama corriendo con nomic-embed-text.
    ollama pull nomic-embed-text

USO
    python capa1_semantica.py construir          # calcula y guarda los centroides
    python capa1_semantica.py probar "texto"     # clasifica un mensaje
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

AQUI = Path(__file__).parent
DATOS = AQUI / "datos"
MODELO_DIR = AQUI / "modelo"
RUTA_CENTROIDES = MODELO_DIR / "centroides.json"
RUTA_CACHE = MODELO_DIR / "cache_embeddings.npz"

OLLAMA = "http://localhost:11434"
MODELO_EMB = "nomic-embed-text"
LOTE = 64

# Cuantos ejemplos por intencion se usan para el centroide. El dataset trae ~890
# por intencion; 200 basta porque un promedio converge rapido y el resto solo
# cuesta tiempo de inferencia. Se deja como constante para poder medir si subirlo
# cambia algo.
MUESTRAS_POR_INTENCION = 200

# Umbrales iniciales. NO son valores elegidos a ojo para siempre: se calibran en
# evaluar_clasificador.py contra el conjunto de prueba y se ajustan aqui.
UMBRAL_CONFIANZA = 0.60
UMBRAL_MARGEN = 0.03


# --------------------------------------------------------------------------------------
# Embeddings
# --------------------------------------------------------------------------------------

def embed_lote(textos: list[str]) -> np.ndarray:
    """Pide embeddings a ollama en lotes y devuelve una matriz normalizada.

    Se normaliza cada vector a norma 1 al recibirlo. Con vectores unitarios la
    similitud coseno es el producto punto, asi que toda la busqueda posterior se
    reduce a una multiplicacion de matrices.
    """
    salida = []
    for i in range(0, len(textos), LOTE):
        trozo = textos[i:i + LOTE]
        r = requests.post(f"{OLLAMA}/api/embed",
                          json={"model": MODELO_EMB, "input": trozo}, timeout=300)
        r.raise_for_status()
        salida.extend(r.json()["embeddings"])
        print(f"\r  embeddings {min(i + LOTE, len(textos)):>6d}/{len(textos)}",
              end="", flush=True)
    print()
    m = np.asarray(salida, dtype=np.float32)
    normas = np.linalg.norm(m, axis=1, keepdims=True)
    normas[normas == 0] = 1.0          # evita division por cero en un texto vacio
    return m / normas


# --------------------------------------------------------------------------------------
# Construccion de centroides
# --------------------------------------------------------------------------------------

def cargar_mapeo() -> dict[str, str]:
    """Lee `carril_final`, que es la columna que revisa una persona.

    Se usa `carril_final` y no `carril_propuesto` a proposito: si Jose Luis
    corrige una fila del CSV, el cambio entra sin tocar el codigo.
    """
    with open(DATOS / "mapeo_intencion_carril.csv", encoding="utf-8") as f:
        return {r["intencion"]: r["carril_final"] for r in csv.DictReader(f)}


def construir() -> None:
    mapeo = cargar_mapeo()
    df = pd.read_parquet(DATOS / "bitext_es.parquet")

    # El dataset tiene ~20 % de instrucciones duplicadas. Un duplicado no aporta
    # informacion al promedio y sesga el centroide hacia la frase repetida.
    antes = len(df)
    df = df.drop_duplicates(subset="instruction")
    print(f"Dataset: {antes:,} filas -> {len(df):,} tras quitar duplicados")

    textos, etiquetas = [], []
    for intencion in sorted(mapeo):
        sub = df[df["intent"] == intencion]
        if sub.empty:
            print(f"  AVISO: '{intencion}' no existe en el dataset, se omite")
            continue
        # random_state fijo: la seleccion debe ser reproducible para que el
        # experimento se pueda repetir y comparar.
        sub = sub.sample(min(MUESTRAS_POR_INTENCION, len(sub)), random_state=42)
        textos.extend(sub["instruction"].tolist())
        etiquetas.extend([intencion] * len(sub))

    print(f"Ejemplos a embeber: {len(textos):,} de {len(set(etiquetas))} intenciones")
    t0 = time.time()
    vectores = embed_lote(textos)
    print(f"  {time.time() - t0:.1f} s  ({vectores.shape[1]} dimensiones)")

    # El centroide de una intencion es el promedio de sus vectores, renormalizado
    # para que siga viviendo en la esfera unitaria y el producto punto siga siendo
    # el coseno.
    centroides, intenciones = [], []
    etq = np.asarray(etiquetas)
    for intencion in sorted(set(etiquetas)):
        c = vectores[etq == intencion].mean(axis=0)
        centroides.append(c / np.linalg.norm(c))
        intenciones.append(intencion)
    C = np.asarray(centroides, dtype=np.float32)

    MODELO_DIR.mkdir(exist_ok=True)
    with open(RUTA_CENTROIDES, "w", encoding="utf-8") as f:
        json.dump({
            "modelo_embeddings": MODELO_EMB,
            "muestras_por_intencion": MUESTRAS_POR_INTENCION,
            "construido": time.strftime("%Y-%m-%d %H:%M"),
            "intenciones": intenciones,
            "carriles": [mapeo[i] for i in intenciones],
            "centroides": C.tolist(),
        }, f)
    # Los vectores de entrenamiento se guardan para poder probar despues otro
    # clasificador sin volver a pagar la inferencia.
    np.savez_compressed(RUTA_CACHE, vectores=vectores, etiquetas=etq)

    # Diagnostico: que tan separados quedaron los centroides entre si. Dos
    # centroides con coseno alto son intenciones que el modelo va a confundir, y
    # conviene saberlo antes de medir.
    S = C @ C.T
    np.fill_diagonal(S, -1)
    print(f"\n{len(intenciones)} centroides -> {RUTA_CENTROIDES.name}")
    print("\nPares mas confundibles (coseno entre centroides):")
    pares = [(S[i, j], intenciones[i], intenciones[j])
             for i in range(len(C)) for j in range(i + 1, len(C))]
    for s, a, b in sorted(pares, reverse=True)[:8]:
        print(f"  {s:.3f}  {a}  ~  {b}   [{mapeo[a]} / {mapeo[b]}]"
              + ("   <-- CARRILES DISTINTOS" if mapeo[a] != mapeo[b] else ""))


# --------------------------------------------------------------------------------------
# Clasificacion
# --------------------------------------------------------------------------------------

class Clasificador:
    def __init__(self, ruta: Path = RUTA_CENTROIDES):
        if not ruta.exists():
            raise SystemExit(f"Faltan los centroides. Ejecuta:  python {Path(__file__).name} construir")
        d = json.loads(ruta.read_text(encoding="utf-8"))
        self.intenciones = d["intenciones"]
        self.carriles = d["carriles"]
        self.C = np.asarray(d["centroides"], dtype=np.float32)

    def clasificar_vectores(self, V: np.ndarray) -> list[dict]:
        """Clasifica una matriz de vectores ya normalizados."""
        S = V @ self.C.T                       # coseno contra los 27 centroides
        orden = np.argsort(-S, axis=1)
        salida = []
        for fila, idx in zip(S, orden):
            i1, i2 = idx[0], idx[1]
            conf, margen = float(fila[i1]), float(fila[i1] - fila[i2])
            carril = self.carriles[i1]
            razon = None
            if conf < UMBRAL_CONFIANZA:
                carril, razon = "copiloto", f"confianza baja ({conf:.3f})"
            elif margen < UMBRAL_MARGEN:
                carril, razon = "copiloto", (
                    f"margen bajo ({margen:.3f}) entre "
                    f"{self.intenciones[i1]} y {self.intenciones[i2]}")
            salida.append({
                "intencion": self.intenciones[i1],
                "carril": carril,
                "carril_sin_umbral": self.carriles[i1],
                "confianza": round(conf, 4),
                "margen": round(margen, 4),
                "degradado_por": razon,
                "segunda_opcion": self.intenciones[i2],
                "capa": 1,
            })
        return salida

    def clasificar(self, textos: list[str]) -> list[dict]:
        return self.clasificar_vectores(embed_lote(textos))


# --------------------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("construir", "probar"):
        print(__doc__.split("USO")[-1])
        raise SystemExit(1)

    if sys.argv[1] == "construir":
        construir()
    else:
        textos = sys.argv[2:] or [
            "¿Dónde está mi pedido?",
            "Quiero que me devuelvan la plata",
            "No me acuerdo de mi contraseña",
            "Necesito hablar con una persona",
            "Quiero comprar tres bolsas de café",
        ]
        c = Clasificador()
        for t, r in zip(textos, c.clasificar(textos)):
            extra = f"  ({r['degradado_por']})" if r["degradado_por"] else ""
            print(f"{r['carril']:12s} {r['intencion']:26s} "
                  f"conf={r['confianza']:.3f} marg={r['margen']:.3f}  {t}{extra}")
