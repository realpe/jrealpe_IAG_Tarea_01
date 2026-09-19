#!/usr/bin/env python3
"""
Clasificador de carril por PROMPT, como alternativa a los centroides.

LA HIPOTESIS QUE PONE A PRUEBA
------------------------------
La Fase 5 midio que el clasificador por embeddings falla, y diagnostico la causa:
un embedding captura el TEMA y el carril depende del ACTO. "Consultar la politica
de devoluciones" y "pedir el reembolso" hablan de lo mismo —devoluciones, dinero,
plazos— y sus vectores quedan pegados, pero una se responde con una plantilla y la
otra compromete dinero de la empresa.

Un LLM no comprime la frase en 768 numeros: la lee. La distincion entre consultar
y solicitar es justo lo que un modelo de lenguaje sabe hacer.

    ¿Detecta un clasificador por prompt lo que la similitud no ve?

Se mide sobre los MISMOS 43 casos y con las MISMAS metricas, en
`comparar_clasificadores.py`. Si no mejora, el hallazgo de la fase se refuerza.

LA DIFERENCIA ESTRUCTURAL QUE HACE INTERESANTE EL EXPERIMENTO
-------------------------------------------------------------
La capa semantica NO PUEDE predecir `humano_exclusivo`: ninguna de las 27
intenciones del dataset mapea a ese carril, asi que el 0/9 en los casos
parafraseados era una limitacion de diseno, no un mal resultado.

Un clasificador por prompt SI puede emitirlo. Esa es la pregunta abierta mas
importante de la fase.

POR QUE ESTO ES PARTE DEL TALLER Y NO UN ANEXO
----------------------------------------------
Es ingenieria de prompt aplicada a una tarea de DECISION en lugar de redaccion, y
el prompt se ancla en el corpus de politicas igual que el generador. Los dos temas
del taller —prompt y RAG— aplicados a un tercer problema.

CUATRO DECISIONES DE DISENO, DECLARADAS
---------------------------------------
1. TEMPERATURA 0.0, no 0.2 como en la generacion. Clasificar no es redactar: aqui
   la reproducibilidad vale mas que la naturalidad. El mismo mensaje debe dar
   siempre el mismo carril.

2. LOS EJEMPLOS DEL PROMPT SALEN SOLO DEL CONJUNTO DE ENTRENAMIENTO. Meter casos
   de `prueba.jsonl` en el few-shot seria medir contra ejemplos ya ensenados.

3. ANTE CUALQUIER FALLO, COPILOTO. Respuesta no parseable, carril inexistente,
   ollama caido: el resultado es copiloto, nunca automatico. Misma asimetria de
   consecuencias de la Fase 2 (3.6).

4. LA POLITICA ENTRA POR EXTRACCION DIRECTA, NO POR BUSQUEDA. Las dos secciones
   que definen el escalamiento se necesitan SIEMPRE, asi que recuperarlas por
   similitud seria usar RAG donde no hace falta. RAG resuelve "no se cual
   fragmento necesito"; aqui si se cual. Es un matiz de la Fase 4 que conviene
   tener claro: no todo contexto se recupera, parte se inyecta.

USO
    python clasificador_llm.py                      # prueba con casos de ejemplo
    python clasificador_llm.py "texto del cliente"
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import requests

AQUI = Path(__file__).parent
POLITICAS = AQUI.parent / "fase3_prompts" / "data" / "politicas.md"

OLLAMA = "http://localhost:11434"
MODELO_DEFECTO = "qwen3:14b"
TEMPERATURA = 0.0          # ver decision 1 del encabezado

CARRILES = ("automatico", "copiloto", "derivacion", "humano_exclusivo")
CARRIL_SEGURO = "copiloto"  # ver decision 3

# Secciones de la politica que definen el escalamiento. Se extraen por titulo
# exacto porque se necesitan en TODAS las clasificaciones (ver decision 4).
SECCIONES = ("### 1.4", "## 4.")


def _extraer_secciones(texto: str) -> str:
    """Devuelve las secciones cuyo titulo empieza por alguno de SECCIONES."""
    fuera, tomando = [], False
    for linea in texto.splitlines():
        if linea.startswith("#"):
            tomando = any(linea.startswith(s) for s in SECCIONES)
        if tomando:
            fuera.append(linea)
    return "\n".join(fuera).strip()


def contexto_politica() -> str:
    if not POLITICAS.exists():
        return "(no se encontro politicas.md)"
    return _extraer_secciones(POLITICAS.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------------------
# El prompt
# --------------------------------------------------------------------------------------

# EJEMPLOS DEL PROMPT (few-shot). Origen declarado caso por caso, porque de aqui
# depende que la medicion valga: NINGUNO sale de datos/prueba.jsonl.
#
#   [nucleo]  copiado de datos/nucleo_duro_entrenamiento.jsonl
#   [mapeo]   redactado a partir de una intencion del mapeo, lado entrenamiento
EJEMPLOS = [
    # [nucleo] salud explicita
    ("Mi hija tuvo una reacción alérgica fuerte después de comer los frutos secos "
     "que les compré", "humano_exclusivo",
     "reporta daño a la salud de una persona; ninguna otra consideración aplica"),
    # [nucleo] legal explicito
    ("Si no me resuelven hoy mismo esto lo pasa a ver mi abogado", "humano_exclusivo",
     "amenaza de acción legal"),
    # [mapeo] track_order
    ("Quisiera saber en qué estado va mi compra", "automatico",
     "consulta de estado: dato transaccional, la política responde"),
    # [mapeo] check_refund_policy
    ("Qué condiciones piden ustedes para aceptar una devolución", "automatico",
     "consulta normativa pura; nadie decide nada"),
    # [mapeo] get_refund
    ("Necesito que me regresen el dinero de esa compra", "copiloto",
     "solicita el reembolso: compromete dinero de la empresa"),
    # [mapeo] cancel_order + excepcion
    ("Ya se venció el plazo pero igual necesito devolverlo", "copiloto",
     "pide una excepción a la política vigente"),
    # [mapeo] recover_password
    ("Olvidé mis datos de acceso y no puedo entrar", "derivacion",
     "gestión de cuentas: lo atiende otra área"),
    # [mapeo] place_order
    ("Quiero cotizar una compra grande para mi negocio", "derivacion",
     "venta, no atención post-venta"),
]

PLANTILLA = """Eres el enrutador de la mesa de servicio al cliente de EcoMarket.
Tu unica tarea es decidir QUIEN debe atender un mensaje. No lo respondas.

LOS CUATRO CARRILES

  humano_exclusivo  Un agente lo atiende, sin intervencion del modelo.
  automatico        El sistema responde solo. La politica ya tiene la respuesta.
  copiloto          El modelo redacta un borrador y una persona lo aprueba.
  derivacion        Lo atiende otra area de EcoMarket: cuentas, ventas, facturacion.

LA REGLA QUE MANDA SOBRE TODAS LAS DEMAS

  Si el mensaje menciona dano a la salud de una persona —malestar, sintomas,
  atencion medica, un producto que causo algo— o una amenaza legal, el carril es
  humano_exclusivo, SIN IMPORTAR de que mas hable el mensaje. Un cliente puede
  preguntar por su pedido y mencionar una reaccion alergica en la misma frase:
  manda la reaccion alergica.

  Ante la duda en esta regla, escala. Un caso facil enviado a un humano cuesta
  minutos; un caso de salud atendido con una plantilla es un incidente.

EL CRITERIO PARA LOS DEMAS CARRILES

  La pregunta es: ¿existe una respuesta correcta en la politica vigente, o hay
  que DECIDIR una excepcion?

  - La politica responde y nadie decide nada          -> automatico
  - Hay una decision con efecto economico, un gesto
    comercial, o una excepcion a la politica          -> copiloto
  - El asunto es de otra area                         -> derivacion

  Distingue CONSULTAR de SOLICITAR. "¿Cuanto tiempo tengo para devolver?" es una
  consulta y la responde la politica. "Quiero devolver esto" es una solicitud que
  compromete dinero. Hablan del mismo tema y van a carriles distintos.

  Si no reconoces de que trata el mensaje, responde copiloto.

EXTRACTO DE LA POLITICA VIGENTE DE ECOMARKET

{politica}

EJEMPLOS

{ejemplos}

FORMATO DE RESPUESTA

Una sola linea, sin markdown, exactamente asi:

  carril|confianza|justificacion

donde confianza es un numero entre 0 y 1, y la justificacion es una frase corta.

MENSAJE A CLASIFICAR

{mensaje}"""


def construir_prompt(mensaje: str) -> str:
    ejemplos = "\n".join(
        f'  "{t}"\n  -> {c}|0.95|{j}\n' for t, c, j in EJEMPLOS)
    return PLANTILLA.format(politica=contexto_politica(),
                            ejemplos=ejemplos, mensaje=mensaje)


# --------------------------------------------------------------------------------------
# Llamada y parseo
# --------------------------------------------------------------------------------------

def _limpiar(texto: str) -> str:
    """Quita el bloque de razonamiento de los modelos que lo emiten.

    qwen3 puede devolver <think>...</think> antes de la respuesta. Se descarta
    porque contiene texto libre que confundiria al parser.
    """
    return re.sub(r"<think>.*?</think>", "", texto, flags=re.DOTALL).strip()


def parsear(salida: str) -> dict:
    """Extrae carril, confianza y justificacion. Ante la duda, CARRIL_SEGURO.

    El parseo es defensivo a proposito: un modelo puede agregar una frase antes,
    envolver la linea en comillas o usar mayusculas. Lo que NO se hace es
    adivinar el carril a partir de texto libre — si no aparece uno de los cuatro
    nombres exactos, se devuelve copiloto y se marca el fallo.
    """
    limpio = _limpiar(salida)
    for linea in limpio.splitlines():
        linea = linea.strip().strip('"`').lstrip("- ")
        if "|" not in linea:
            continue
        partes = [p.strip() for p in linea.split("|")]
        carril = partes[0].lower().replace(" ", "_").replace("-", "_")
        if carril not in CARRILES:
            continue
        try:
            confianza = float(partes[1].replace(",", "."))
        except (IndexError, ValueError):
            confianza = None
        return {"carril": carril, "confianza": confianza,
                "justificacion": partes[2] if len(partes) > 2 else "",
                "parseo_ok": True, "crudo": limpio}
    return {"carril": CARRIL_SEGURO, "confianza": None,
            "justificacion": "no se pudo interpretar la respuesta del modelo",
            "parseo_ok": False, "crudo": limpio}


def clasificar(mensaje: str, modelo: str = MODELO_DEFECTO,
               timeout: int = 120) -> dict:
    """Clasifica un mensaje. Cualquier fallo devuelve CARRIL_SEGURO."""
    prompt = construir_prompt(mensaje)
    ini = time.time()
    try:
        r = requests.post(f"{OLLAMA}/api/chat", timeout=timeout, json={
            "model": modelo, "stream": False,
            "options": {"temperature": TEMPERATURA},
            "messages": [{"role": "user", "content": prompt}],
        })
        r.raise_for_status()
        salida = r.json()["message"]["content"]
    except Exception as e:                                   # noqa: BLE001
        return {"carril": CARRIL_SEGURO, "confianza": None,
                "justificacion": f"fallo al llamar al modelo: {type(e).__name__}",
                "parseo_ok": False, "crudo": "", "segundos": time.time() - ini,
                "modelo": modelo, "error": str(e)}

    fuera = parsear(salida)
    fuera["segundos"] = round(time.time() - ini, 2)
    fuera["modelo"] = modelo
    return fuera


# --------------------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1:
        casos = [(a, None) for a in sys.argv[1:]]
    else:
        # Casos de humo. Los tres primeros son del nucleo duro PARAFRASEADO, que
        # es donde la capa semantica da 0/9: son los que importan.
        casos = [
            ("Mi bebé se llevó el producto a la boca y duro la tarde llorando",
             "humano_exclusivo"),
            ("Tengo el cuerpo brotado y el único cambio fue ese producto",
             "humano_exclusivo"),
            ("Ya hablé con alguien que me está asesorando sobre mis derechos como comprador",
             "humano_exclusivo"),
            ("hola, cuanto tiempo tengo para hacer una devolución", "automatico"),
            ("Quiero devolver el termo, ya no lo necesito", "copiloto"),
            ("No me acuerdo de la contraseña de mi cuenta", "derivacion"),
        ]

    print(f"modelo: {MODELO_DEFECTO} · temperatura {TEMPERATURA}\n")
    aciertos = 0
    for mensaje, esperado in casos:
        r = clasificar(mensaje)
        if esperado:
            ok = r["carril"] == esperado
            aciertos += ok
            marca = "ok " if ok else "NO "
        else:
            marca = "-- "
        conf = f"{r['confianza']:.2f}" if r["confianza"] is not None else " — "
        print(f"[{marca}] {r['carril']:17s} conf={conf} {r['segundos']:5.1f}s  "
              f"{mensaje[:46]}")
        if r["justificacion"]:
            print(f"        {r['justificacion'][:88]}")
        if not r["parseo_ok"]:
            print(f"        (sin parsear) {r['crudo'][:120]}")
    if any(e for _, e in casos):
        n = sum(1 for _, e in casos if e)
        print(f"\n{aciertos}/{n} en los casos con carril esperado")
