#!/usr/bin/env python3
"""
Tercer guardarrail de salida: verifica los PLAZOS citados en la respuesta.

DE DONDE SALIO
--------------
No de un analisis previo, sino de usar el sistema. Procesando un caso en la
consola de la Fase 5 aparecio esto:

    politica recuperada : "30 dias calendario desde la entrega"
    respuesta del modelo: "dentro de los 30 dias habiles desde la recepcion"

Treinta dias habiles son casi seis semanas. Es una condicion de politica
fabricada, con consecuencia economica directa, y los dos guardarrailes
existentes la dejaron pasar:

  - `verificar_grounding()` (Fase 3) busca identificadores y fechas inventados.
    Aqui no hay ninguno: el numero es correcto y la fecha no se cita.
  - `validar_salida()` (canales.py) mira datos de contacto. No aplica.

El modelo cambio UNA palabra y con eso duplico el plazo.

POR QUE ESTE CONTROL SI PUEDE ATRAPARLO
---------------------------------------
Es el hallazgo II de la Fase 3 —una decision incorrecta puede estar escrita con
datos correctos— pero con una diferencia que lo hace barato de detectar: aqui el
error SI es lexico. "Calendario" y "habiles" son dos palabras distintas, y la
correcta esta escrita en el contexto que se le entrego al modelo.

La regla es literal: todo plazo citado debe aparecer en el contexto con el mismo
numero Y la misma unidad. Si el contexto usa otra unidad para ese mismo numero,
la alerta lo dice, porque contradecir la politica es peor que inventar un plazo
que no existe en ninguna parte.

LO QUE NO CUBRE, DECLARADO
--------------------------
Solo plazos expresados en dias. Un porcentaje de reembolso, un umbral en pesos,
una condicion reformulada con otras palabras o un plazo en semanas siguen fuera
de su alcance. Cada capa de control tiene un limite; el valor esta en saber
cual es.

USO
    from guardarrail_plazos import verificar_plazos
    alertas = verificar_plazos(respuesta, contexto)
"""

from __future__ import annotations

import re
import unicodedata

# Captura "30 dias", "30 dias habiles", "5 dias calendario". La unidad es
# opcional a proposito: un plazo sin unidad tambien debe existir en el contexto.
_RE_PLAZO = re.compile(
    r"(\d{1,3})\s*d[ií]as?(?:\s+(h[áa]biles|calendario|corridos|corrido))?",
    re.IGNORECASE)

UNIDADES = ("habiles", "calendario", "corridos")


def _sin_tildes(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def verificar_plazos(respuesta: str, contexto: str) -> list[str]:
    """Devuelve una alerta por cada plazo que no se pueda verificar en el contexto.

    Lista vacia significa que todo plazo citado aparece en el contexto con su
    misma unidad. No dice nada sobre el resto de la respuesta.
    """
    ctx = _sin_tildes(contexto)
    alertas: list[str] = []

    for numero, unidad in _RE_PLAZO.findall(respuesta):
        u = _sin_tildes(unidad) if unidad else ""

        if u:
            if f"{numero} dias {u}" in ctx or f"{numero} dia {u}" in ctx:
                continue
            # El caso grave: el contexto usa OTRA unidad para el mismo numero.
            # No es una invencion, es una contradiccion de la politica vigente.
            otras = [o for o in UNIDADES if o != u and f"{numero} dias {o}" in ctx]
            if otras:
                alertas.append(
                    f"plazo alterado: la respuesta dice '{numero} días {unidad}' y "
                    f"la política dice '{numero} días {otras[0]}'")
            else:
                alertas.append(
                    f"plazo no verificable en el contexto: '{numero} días {unidad}'")
        elif f"{numero} dias" not in ctx and f"{numero} dia" not in ctx:
            alertas.append(f"plazo no verificable en el contexto: '{numero} días'")

    return alertas


if __name__ == "__main__":
    CTX = ("El plazo general de devolución es de 30 días calendario desde la entrega. "
           "El reporte por producto dañado debe hacerse dentro de las 72 horas.")
    pruebas = [
        ("Las devoluciones deben realizarse dentro de los 30 días hábiles.", 1),
        ("Tienes 30 días calendario desde la entrega.", 0),
        ("El plazo es de 60 días para devolver.", 1),
        ("El paquete está abierto y puedes devolverlo.", 0),
        ("Tienes 30 dias, sin tilde ni unidad.", 0),
    ]
    print(f"Contexto: {CTX}\n")
    for texto, esperado in pruebas:
        a = verificar_plazos(texto, CTX)
        marca = "ok " if len(a) == esperado else "REV"
        print(f"[{marca}] {len(a)}  {texto[:56]:58s} {a or ''}")
