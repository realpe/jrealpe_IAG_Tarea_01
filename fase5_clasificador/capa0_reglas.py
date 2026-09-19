#!/usr/bin/env python3
"""
Capa 0 del clasificador: reglas deterministas que corren ANTES del modelo.

POR QUE EXISTE Y POR QUE VA PRIMERO
-----------------------------------
El error de enrutamiento mas grave es mandar un caso del nucleo duro —salud,
amenaza legal, monto alto— al carril automatico. Sus consecuencias son
asimetricas: un caso facil enviado al copiloto cuesta tiempo de un agente; un
caso de salud atendido por una plantilla es un incidente.

Un filtro lexico no alucina y es auditable linea por linea. Por eso la garantia
se pone aqui y no en el clasificador semantico, que es probabilistico. El
experimento de RAG (Fase 4) llego a la misma conclusion por otro camino: una
prohibicion no se parece semanticamente a la peticion que debe bloquear, asi que
lo critico no puede depender de la similitud.

DISENO DE LOS TERMINOS
----------------------
Se buscan RAICES y no palabras completas: "alergi" cubre alergia, alergica,
alergico, alergenos. La comparacion se hace sin tildes y en minusculas, porque
el cliente escribe "alergia" tanto como "alérgia".

Se prefiere el falso positivo: si un termino dispara de mas, un agente revisa un
caso que no lo necesitaba. El costo de ese error es minutos; el del contrario es
una persona danada.
"""

from __future__ import annotations

import re
import unicodedata

UMBRAL_MONTO = 500_000  # COP. Politica de EcoMarket, seccion 1.4.


# Cada entrada: (raiz a buscar, motivo legible para el registro de auditoria)
TERMINOS_SALUD = [
    ("alergi", "posible reacción alérgica"),
    ("alergen", "mención de alérgenos"),
    ("intoxic", "posible intoxicación"),
    ("envenen", "posible envenenamiento"),
    ("roncha", "síntoma cutáneo"),
    ("sarpullid", "síntoma cutáneo"),
    ("urticaria", "síntoma cutáneo"),
    ("erupcion", "síntoma cutáneo"),
    ("irritacion", "síntoma cutáneo"),
    ("quemadur", "lesión"),
    ("ampolla", "lesión"),
    ("vomit", "síntoma digestivo"),
    ("nausea", "síntoma digestivo"),
    ("diarrea", "síntoma digestivo"),
    ("mareo", "síntoma"),
    ("desmay", "síntoma grave"),
    ("hospital", "atención médica"),
    ("urgencias", "atención médica"),
    ("clinica", "atención médica"),
    ("medico", "atención médica"),
    ("doctor", "atención médica"),
    ("pediatra", "atención médica"),
    ("ambulancia", "atención médica"),
    ("intoxicacion", "posible intoxicación"),
    ("se lo tomo", "posible ingesta accidental"),
    ("se lo comio", "posible ingesta accidental"),
    ("ingirio", "posible ingesta accidental"),
]

TERMINOS_LEGAL = [
    ("demand", "amenaza de acción judicial"),
    ("abogad", "mención de representación legal"),
    ("tutela", "acción de tutela"),
    ("superintendencia", "queja ante la SIC"),
    (" sic ", "queja ante la SIC"),
    ("fiscalia", "denuncia penal"),
    ("denunci", "denuncia"),
    ("juzgad", "proceso judicial"),
    ("judicial", "proceso judicial"),
    ("procuraduria", "entidad de control"),
    ("defensoria", "entidad de control"),
    ("consumidor", "invocación del estatuto del consumidor"),
    ("estafa", "imputación de fraude"),
    ("fraude", "imputación de fraude"),
]

# Terminos que NO escalan por si solos pero suben la prioridad de revision.
TERMINOS_TENSION = [
    ("inaceptable", "tono de escalamiento"),
    ("indignad", "tono de escalamiento"),
    ("pesima", "insatisfacción fuerte"),
    ("nunca mas", "riesgo de pérdida de cliente"),
    ("redes sociales", "amenaza de exposición pública"),
    ("twitter", "amenaza de exposición pública"),
    ("tercera vez", "reincidencia declarada"),
    ("van varias veces", "reincidencia declarada"),
]


def normalizar(texto: str) -> str:
    """Minusculas y sin tildes, para que la deteccion no dependa de la ortografia."""
    t = texto.lower()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    # Se rodea de espacios para que las raices con espacio (" sic ") coincidan
    # tambien al inicio o al final del mensaje.
    return f" {re.sub(r'[^a-z0-9ñ ]+', ' ', t)} "


def _buscar(texto_norm: str, terminos: list[tuple[str, str]]) -> list[str]:
    return [motivo for raiz, motivo in terminos if raiz in texto_norm]


def evaluar(mensaje: str, pedido: dict | None = None,
            devoluciones_60d: int = 0) -> dict:
    """
    Decide si el caso debe ir al nucleo duro SIN consultar al modelo.

    Devuelve siempre la traza completa: que reglas dispararon y por que. Ese
    detalle va al registro de auditoria, porque una decision de enrutamiento sin
    justificacion registrada no es auditable.

    `pedido` y `devoluciones_60d` vienen de la base transaccional: el monto y la
    reincidencia no se pueden leer del texto del cliente.
    """
    t = normalizar(mensaje)
    motivos: list[str] = []

    salud = _buscar(t, TERMINOS_SALUD)
    legal = _buscar(t, TERMINOS_LEGAL)
    motivos += [f"salud: {m}" for m in salud]
    motivos += [f"legal: {m}" for m in legal]

    if pedido and (pedido.get("total") or 0) > UMBRAL_MONTO:
        motivos.append(f"monto: ${pedido['total']:,} supera el umbral de ${UMBRAL_MONTO:,}")

    if devoluciones_60d >= 1:
        motivos.append(f"reincidencia: {devoluciones_60d + 1}ª devolución en 60 días")

    tension = _buscar(t, TERMINOS_TENSION)

    return {
        "escala": bool(motivos),
        "carril": "humano_exclusivo" if motivos else None,
        "motivos": motivos,
        "senales_tension": tension,   # informativas, no deciden por si solas
        "capa": 0,
    }


if __name__ == "__main__":
    ejemplos = [
        ("Mi hijo se tomó un poco del producto y está con vómito", None, 0),
        ("Esto ya lo voy a poner en manos de mi abogado", None, 0),
        ("¿Dónde está mi pedido 12345?", None, 0),
        ("Quiero devolver la mochila", {"total": 149000}, 0),
        ("Quiero devolver el equipo", {"total": 890000}, 0),
        ("Me salió una roncha después de usar el jabón", None, 0),
        ("Es la segunda vez que devuelvo algo este mes", None, 1),
    ]
    for msg, ped, dev in ejemplos:
        r = evaluar(msg, ped, dev)
        marca = "ESCALA" if r["escala"] else "sigue "
        print(f"[{marca}] {msg[:52]:54s} {r['motivos'] or ''}")
