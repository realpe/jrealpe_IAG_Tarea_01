#!/usr/bin/env python3
"""
Fase 4 - Prueba de concepto de RAG sobre las politicas de EcoMarket
Taller Practico #1 - Inteligencia Artificial Generativa - Maestria en IA Aplicada (Icesi)
Autor: Jose Luis Realpe M.

Implementa el ciclo completo de RAG: fragmentar el corpus, generar embeddings, recuperar los
fragmentos relevantes para una consulta y responder con el LLM usando SOLO lo recuperado.

DECISION DE DISENO: no se usa ChromaDB ni FAISS. El corpus son ~20 fragmentos, y a ese volumen
un motor vectorial es sobreingenieria: agrega una dependencia y no aporta nada frente a calcular
la similitud coseno en Python puro. El documento fase4_viabilidad_rag.md explica en que punto si
conviene migrar a un motor real (Oracle 23ai con tipo VECTOR, o pgvector).

Uso:
    ollama pull nomic-embed-text
    python rag.py --indexar                        # construye los dos indices
    python rag.py --preguntar "puedo devolver un cafe que llego danado?"
    python rag.py --preguntar "..." --estrategia fija --k 3
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Falta 'requests'. Instala con: pip install -r ../requirements.txt")

BASE = Path(__file__).parent
CORPUS = BASE.parent / "fase3_prompts" / "data" / "politicas.md"
INDICES = BASE / "indices"

OLLAMA = "http://localhost:11434"
MODELO_EMBED = "nomic-embed-text"
MODELO_LLM = "qwen3:14b"

# Tamano de fragmento para la estrategia "fija", en caracteres. Se eligio deliberadamente pequeno
# para que parta secciones por la mitad: el objetivo del experimento es provocar el fallo, no
# evitarlo. Una implementacion real ajustaria este valor por tokens y no por caracteres.
TAM_FIJO = 450
SOLAPE_FIJO = 80


# --------------------------------------------------------------------------------------
# Fragmentacion: las dos estrategias que se comparan
# --------------------------------------------------------------------------------------

def fragmentar_fijo(texto: str) -> list[dict]:
    """
    Ventana deslizante de tamano fijo con solape.

    Es la estrategia ingenua y la mas comun en tutoriales. Ignora por completo la estructura del
    documento: puede partir una tabla, separar un encabezado de su contenido, o —el caso que
    interesa a este experimento— dejar una regla en un fragmento y su excepcion en otro.
    """
    fragmentos = []
    i = 0
    n = 0
    while i < len(texto):
        trozo = texto[i:i + TAM_FIJO]
        fragmentos.append({
            "id": f"fijo-{n:02d}",
            "titulo": f"(fragmento {n} sin contexto de seccion)",
            "texto": trozo.strip(),
        })
        i += TAM_FIJO - SOLAPE_FIJO
        n += 1
    return [f for f in fragmentos if f["texto"]]


def fragmentar_por_seccion(texto: str) -> list[dict]:
    """
    Fragmenta respetando la estructura del documento, con dos reglas:

    1. Cada fragmento arrastra su encabezado padre. Sin eso, el fragmento que dice "30 dias
       calendario" no indica de que politica habla, y el recuperador lo confunde con los plazos
       de envio.
    2. Las secciones que forman una unidad de decision NO se separan. En este corpus, la 1.2
       (restriccion por categoria) y la 1.3 (excepcion por producto danado) se indexan juntas:
       aplicar la primera sin la segunda produce una negativa incorrecta al cliente.

    La regla 2 es especifica de este documento y esa es justamente su leccion: la fragmentacion
    no es un parametro tecnico universal, depende de como esta escrita la norma.
    """
    # Unidades de decision que deben permanecer juntas, por prefijo de encabezado
    INSEPARABLES = [("### 1.2", "### 1.3")]

    bloques = re.split(r"\n(?=## )", texto)
    fragmentos = []
    n = 0

    for bloque in bloques:
        m = re.match(r"## (.+)", bloque)
        titulo_padre = m.group(1).strip() if m else "Documento"

        subbloques = re.split(r"\n(?=### )", bloque)
        # Unir las subsecciones declaradas inseparables
        unidos = []
        saltar = False
        for i, sub in enumerate(subbloques):
            if saltar:
                saltar = False
                continue
            fusionar = False
            for ini, fin in INSEPARABLES:
                if sub.startswith(ini) and i + 1 < len(subbloques) and subbloques[i + 1].startswith(fin):
                    fusionar = True
            if fusionar:
                unidos.append(sub + "\n" + subbloques[i + 1])
                saltar = True
            else:
                unidos.append(sub)

        for sub in unidos:
            limpio = sub.strip()
            if len(limpio) < 40:
                continue
            ms = re.match(r"#{2,3} (.+)", limpio)
            titulo = ms.group(1).strip() if ms else titulo_padre
            # El encabezado padre se antepone para que el fragmento sea autocontenido
            contexto = f"[{titulo_padre}]\n" if titulo != titulo_padre else ""
            fragmentos.append({
                "id": f"sec-{n:02d}",
                "titulo": titulo,
                "texto": contexto + limpio,
            })
            n += 1

    return fragmentos


ESTRATEGIAS = {
    "seccion": fragmentar_por_seccion,
    "fija": fragmentar_fijo,
}


# --------------------------------------------------------------------------------------
# Embeddings
# --------------------------------------------------------------------------------------

def embed(textos: list[str]) -> list[list[float]]:
    """
    Genera embeddings con Ollama.

    Se intenta primero /api/embed (API nueva, admite lotes) y se cae a /api/embeddings (API
    antigua, uno por llamada) segun la version de Ollama instalada.
    """
    try:
        r = requests.post(f"{OLLAMA}/api/embed",
                          json={"model": MODELO_EMBED, "input": textos}, timeout=300)
        if r.ok and "embeddings" in r.json():
            return r.json()["embeddings"]
    except requests.exceptions.RequestException:
        pass

    vectores = []
    for t in textos:
        try:
            r = requests.post(f"{OLLAMA}/api/embeddings",
                              json={"model": MODELO_EMBED, "prompt": t}, timeout=300)
            r.raise_for_status()
        except requests.exceptions.ConnectionError:
            sys.exit(f"No hay conexion con Ollama en {OLLAMA}. Ejecuta 'ollama serve'.")
        except requests.exceptions.HTTPError as e:
            sys.exit(f"Error de Ollama: {e}\nVerifica que '{MODELO_EMBED}' este descargado.")
        vectores.append(r.json()["embedding"])
    return vectores


def coseno(a: list[float], b: list[float]) -> float:
    """Similitud coseno en Python puro: suficiente y exacta para este volumen."""
    num = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return num / (na * nb) if na and nb else 0.0


# --------------------------------------------------------------------------------------
# Indice
# --------------------------------------------------------------------------------------

def indexar(estrategia: str) -> Path:
    texto = CORPUS.read_text(encoding="utf-8")
    fragmentos = ESTRATEGIAS[estrategia](texto)
    print(f"  {estrategia}: {len(fragmentos)} fragmentos, "
          f"{sum(len(f['texto']) for f in fragmentos) // len(fragmentos)} caracteres de media")

    vectores = embed([f["texto"] for f in fragmentos])
    for f, v in zip(fragmentos, vectores):
        f["vector"] = v

    INDICES.mkdir(exist_ok=True)
    destino = INDICES / f"indice_{estrategia}.json"
    destino.write_text(json.dumps(fragmentos, ensure_ascii=False), encoding="utf-8")
    return destino


def cargar_indice(estrategia: str) -> list[dict]:
    ruta = INDICES / f"indice_{estrategia}.json"
    if not ruta.exists():
        sys.exit(f"No existe {ruta.name}. Ejecuta primero: python rag.py --indexar")
    return json.loads(ruta.read_text(encoding="utf-8"))


def buscar(pregunta: str, estrategia: str, k: int = 3) -> list[dict]:
    """Devuelve los k fragmentos mas similares a la pregunta, con su puntaje."""
    indice = cargar_indice(estrategia)
    v_pregunta = embed([pregunta])[0]
    puntuados = [
        {"id": f["id"], "titulo": f["titulo"], "texto": f["texto"],
         "puntaje": coseno(v_pregunta, f["vector"])}
        for f in indice
    ]
    puntuados.sort(key=lambda x: x["puntaje"], reverse=True)
    return puntuados[:k]


# --------------------------------------------------------------------------------------
# Generacion
# --------------------------------------------------------------------------------------

SYSTEM = """Eres el asistente de servicio al cliente de EcoMarket.
Responde UNICAMENTE con lo que aparece en los fragmentos de politica entregados.
Si los fragmentos no contienen la respuesta, dilo con claridad y ofrece escalar a un asesor humano.
No agregues condiciones, plazos ni excepciones que no esten escritas en los fragmentos.
Cita al final la seccion de la que tomaste la respuesta.
Responde en texto plano, maximo 120 palabras, tratando al cliente de usted."""


def responder(pregunta: str, estrategia: str, k: int = 3) -> tuple[str, list[dict]]:
    recuperados = buscar(pregunta, estrategia, k)
    contexto = "\n\n---\n\n".join(f"[{f['titulo']}]\n{f['texto']}" for f in recuperados)
    prompt = f"<politicas_recuperadas>\n{contexto}\n</politicas_recuperadas>\n\nConsulta del cliente: {pregunta}"

    r = requests.post(f"{OLLAMA}/api/chat", json={
        "model": MODELO_LLM,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.2, "num_ctx": 8192},
    }, timeout=600)
    r.raise_for_status()
    texto = re.sub(r"<think>.*?</think>", "", r.json()["message"]["content"], flags=re.DOTALL)
    return texto.strip(), recuperados


# --------------------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="PoC de RAG sobre las politicas de EcoMarket.")
    ap.add_argument("--indexar", action="store_true", help="Construye los indices de ambas estrategias")
    ap.add_argument("--preguntar", help="Consulta a responder")
    ap.add_argument("--estrategia", default="seccion", choices=list(ESTRATEGIAS))
    ap.add_argument("--k", type=int, default=3, help="Fragmentos a recuperar (defecto: 3)")
    ap.add_argument("--solo-recuperar", action="store_true", help="Muestra los fragmentos sin llamar al LLM")
    args = ap.parse_args()

    if args.indexar:
        print("Construyendo indices...")
        for e in ESTRATEGIAS:
            destino = indexar(e)
            print(f"  -> {destino.name}\n")
        print("Listo. Ahora puedes preguntar con --preguntar")
        return

    if not args.preguntar:
        ap.error("Indica --indexar o --preguntar")

    recuperados = buscar(args.preguntar, args.estrategia, args.k)
    print(f"\nEstrategia: {args.estrategia} | k={args.k}\n")
    print("Fragmentos recuperados:")
    for f in recuperados:
        print(f"  [{f['puntaje']:.3f}] {f['id']} - {f['titulo']}")

    if args.solo_recuperar:
        for f in recuperados:
            print(f"\n--- {f['id']} ---\n{f['texto'][:400]}")
        return

    print("\nGenerando respuesta...\n")
    texto, _ = responder(args.preguntar, args.estrategia, args.k)
    print(texto)


if __name__ == "__main__":
    main()
