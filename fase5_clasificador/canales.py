#!/usr/bin/env python3
"""
Lista blanca de canales oficiales: derivacion directa + validacion de salida.

QUE PROBLEMA RESUELVE
---------------------
En la Fase 3 (hallazgo 8.3a) qwen2.5:7b y mistral-small:24b inventaron correos y
telefonos de soporte. La causa raiz no fue el modelo: `politicas.md` no contiene
ningun canal de contacto, de modo que el prompt pedia orientar al cliente sin
darle con que. El modelo completo el vacio, que es lo que hacen los modelos de
lenguaje.

Este modulo cubre el hueco por los dos lados:

  1. ENTRADA  -> `contexto_canales()` inyecta el directorio en el prompt, para que
                 el modelo tenga datos reales que citar.
  2. SALIDA   -> `validar_salida()` extrae TODO correo, telefono y URL del texto
                 generado y rechaza cualquiera que no este en el directorio.

El segundo control es el que da la garantia. El primero solo reduce la
probabilidad de que el modelo invente; el segundo convierte la invencion en un
error detectable antes de que la respuesta salga al cliente. Es la misma
leccion de la Fase 3: instruir al modelo baja la frecuencia del fallo y no lo
elimina, asi que la garantia se pone en una verificacion determinista.

POR QUE LA DERIVACION DIRECTA
-----------------------------
Decision de Jose Luis: cuando el caso no es del alcance del asistente, darle al
cliente el canal del area correspondiente resuelve en un turno lo que por el
flujo normal costaria una cola y un agente. El asistente no soluciona el caso;
lo entrega en la puerta correcta.

DOS AREAS ESTAN EXCLUIDAS DE LA DERIVACION AUTOMATICA: `calidad` y `legal`.
Llevan `carril_obligatorio: humano_exclusivo` en el JSON y `derivar()` se niega a
devolverlas. Un cliente que reporta una reaccion alergica no necesita un correo,
necesita que alguien lo llame. Entregarle una direccion de correo seria una
forma elegante de no atenderlo.

ALTERNATIVA DESCARTADA
----------------------
Se podia validar la salida pidiendole al propio modelo que revisara si invento
datos. Se descarto por lo mismo que en la Fase 4: un verificador probabilistico
sobre una salida probabilistica no agrega garantia, y ademas cuesta una llamada
de inferencia por respuesta. Una expresion regular contra una lista cerrada es
exacta, instantanea y auditable linea por linea.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

AQUI = Path(__file__).parent
RUTA_CANALES = AQUI / "datos" / "canales_oficiales.json"

with open(RUTA_CANALES, encoding="utf-8") as f:
    _DIRECTORIO = json.load(f)

AREAS = {a["id"]: a for a in _DIRECTORIO["areas"]}

# Areas que el asistente conoce pero nunca ofrece por si mismo.
AREAS_RESERVADAS = {i for i, a in AREAS.items()
                    if a.get("carril_obligatorio") == "humano_exclusivo"}

# intencion -> id de area, derivado del JSON para que el mapeo viva en un solo sitio.
INTENCION_A_AREA = {
    intencion: area["id"]
    for area in _DIRECTORIO["areas"]
    for intencion in area.get("intenciones", [])
}


# --------------------------------------------------------------------------------------
# Normalizacion de valores de contacto
# --------------------------------------------------------------------------------------

def _normalizar_telefono(valor: str) -> str:
    """Deja solo digitos y descarta el indicativo de pais.

    El modelo puede escribir el mismo numero como '+57 602 555 0110',
    '6025550110' o '(602) 555-0110'. Comparar cadenas literales daria falsos
    positivos: los tres son el mismo canal legitimo. Se comparan los ultimos 10
    digitos, que es el numero nacional colombiano.
    """
    digitos = re.sub(r"\D", "", valor)
    return digitos[-10:] if len(digitos) >= 10 else digitos


def _normalizar_url(valor: str) -> str:
    v = valor.lower().strip().rstrip("/.,;)")
    v = re.sub(r"^https?://", "", v)
    return re.sub(r"^www\.", "", v)


def _normalizar_correo(valor: str) -> str:
    v = valor.lower().strip().rstrip(".,;)")
    # Sin tildes: un modelo puede escribir 'devolucións@...' por contaminacion.
    v = unicodedata.normalize("NFD", v)
    return "".join(c for c in v if unicodedata.category(c) != "Mn")


# Conjuntos permitidos, construidos una sola vez al importar.
def _construir_permitidos() -> dict[str, set[str]]:
    correos, telefonos, urls = set(), set(), set()
    for area in _DIRECTORIO["areas"]:
        for canal in area["canales"]:
            v, t = canal["valor"], canal["tipo"]
            if t == "correo":
                correos.add(_normalizar_correo(v))
            elif t in ("telefono", "whatsapp"):
                telefonos.add(_normalizar_telefono(v))
            elif t == "formulario":
                urls.add(_normalizar_url(v))
    return {"correos": correos, "telefonos": telefonos, "urls": urls}


PERMITIDOS = _construir_permitidos()


def _construir_reservados() -> dict[str, set[str]]:
    """Canales que existen y son legitimos, pero que el asistente no debe ofrecer.

    Son los de `calidad` y `legal`. Un correo de calidad en una respuesta
    automatica no es un dato falso; es una derivacion que no debia ocurrir. El
    validador los trata como una alerta distinta porque el problema es distinto.
    """
    correos, telefonos = set(), set()
    for i in AREAS_RESERVADAS:
        for canal in AREAS[i]["canales"]:
            if canal["tipo"] == "correo":
                correos.add(_normalizar_correo(canal["valor"]))
            elif canal["tipo"] in ("telefono", "whatsapp"):
                telefonos.add(_normalizar_telefono(canal["valor"]))
    return {"correos": correos, "telefonos": telefonos}


RESERVADOS = _construir_reservados()

# Dominio corporativo: una URL de ecomarket que no este en la lista se marca
# igual, porque una ruta inventada dentro del dominio real es tan falsa como un
# dominio inventado, y ademas mas creible para el cliente.
DOMINIO = "ecomarket.co"


# --------------------------------------------------------------------------------------
# 1. Entrada: contexto para el prompt
# --------------------------------------------------------------------------------------

def contexto_canales(ids: list[str] | None = None, incluir_reservadas: bool = False) -> str:
    """Bloque de texto con los canales, para inyectar en el prompt del modelo.

    Por defecto excluye `calidad` y `legal`: son areas internas y el modelo no
    debe siquiera tener la tentacion de ofrecerlas. Minimizar el contexto tambien
    reduce la superficie de invencion, el mismo criterio de `contexto_pedido()`
    en la Fase 3.
    """
    seleccion = ids or [i for i in AREAS if i not in AREAS_RESERVADAS]
    if not incluir_reservadas:
        seleccion = [i for i in seleccion if i not in AREAS_RESERVADAS]

    lineas = ["CANALES OFICIALES DE ECOMARKET",
              "Usa UNICAMENTE estos datos. Si el canal que necesitas no aparece "
              "aqui, di que no lo tienes disponible.", ""]
    for i in seleccion:
        a = AREAS[i]
        lineas.append(f"- {a['nombre']} ({', '.join(a['asuntos'][:3])}):")
        for c in a["canales"]:
            lineas.append(f"    {c['tipo']}: {c['valor']}  [{c['horario']}]")
    return "\n".join(lineas)


# --------------------------------------------------------------------------------------
# 2. Derivacion: a que area va este caso
# --------------------------------------------------------------------------------------

def derivar(intencion: str | None = None, area_id: str | None = None) -> dict | None:
    """Devuelve el area a la que se deriva el caso, o None si no corresponde.

    Devuelve None cuando el area es reservada: esos casos los toma un humano y
    la derivacion por canal seria una forma de no atenderlos.
    """
    destino = area_id or INTENCION_A_AREA.get(intencion or "")
    if destino is None or destino in AREAS_RESERVADAS:
        return None
    a = AREAS[destino]
    return {
        "area": a["id"],
        "nombre": a["nombre"],
        "canales": a["canales"],
        "mensaje": (f"Este caso lo atiende {a['nombre']}. "
                    f"Puedes comunicarte por {a['canales'][0]['tipo']}: "
                    f"{a['canales'][0]['valor']} ({a['canales'][0]['horario']})."),
    }


# --------------------------------------------------------------------------------------
# 3. Salida: validacion contra la lista blanca
# --------------------------------------------------------------------------------------

RE_CORREO = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
RE_URL = re.compile(r"(?:https?://|www\.)[^\s<>\"'\)\]]+")
# Telefono: 7 o mas digitos con separadores tipicos. Se exige un minimo de 7
# para no marcar montos, cantidades ni identificadores de pedido de 5 digitos.
RE_TELEFONO = re.compile(r"(?:\+?\d[\d \-().]{6,}\d)")

# Tercer modo de fallo, descubierto al revisar las salidas reales de la Fase 3:
# qwen2.5:7b no inventa el correo, escribe '[direccion de correo electronico]'.
# Es el fallo honesto —el modelo declara que no tiene el dato— y aun asi llega al
# cliente como una plantilla sin llenar. No lo atrapa ninguna de las reglas
# anteriores porque no hay arroba ni digitos. Se busca un marcador de relleno
# entre corchetes o llaves que mencione un tipo de dato de contacto.
RE_PLACEHOLDER = re.compile(
    r"[\[\{]{1,2}\s*[^\]\}\n]{0,60}"
    r"(?:correo|email|e-mail|telefono|teléfono|contacto|direccion|dirección|"
    r"numero|número|linea|línea|whatsapp)"
    r"[^\]\}\n]{0,60}\s*[\]\}]{1,2}",
    re.IGNORECASE)


def _parece_telefono(fragmento: str, digitos: str) -> bool:
    """Filtra montos e identificadores que la expresion regular atrapa de mas.

    Se exige una forma reconocible de numero telefonico colombiano:
      +           indicativo internacional explicito
      3xx         celular
      60x         fijo en el plan de numeracion vigente
      018000      linea gratuita nacional; es ademas el formato que un modelo
                  inventa con mas facilidad, porque suena institucional
    Sin este filtro, un monto escrito '1.250.000' se reportaria como telefono.
    """
    return (fragmento.strip().startswith("+")
            or digitos.startswith(("018000", "01800"))
            or digitos[:1] in ("3", "6"))


def validar_salida(texto: str, contexto: str = "",
                   permitir_reservadas: bool = False) -> list[str]:
    """Devuelve la lista de alertas por datos de contacto indebidos.

    Detecta dos fallos distintos:
      - FABRICADO: el dato no existe en el directorio. Es el error de la Fase 3.
      - RESERVADO: el dato existe pero pertenece a `calidad` o `legal`, areas que
        el asistente no ofrece. Con `permitir_reservadas=True` no se reporta,
        para el caso de un agente humano que si puede citarlas.

    `contexto` es el texto que se le paso al modelo (datos del pedido, politicas).
    Un dato de contacto que aparece literalmente ahi NO es fabricacion: llego por
    function calling y es especifico del caso, como la URL de rastreo de un
    pedido. Un directorio estatico no puede enumerar esos valores porque cambian
    con cada pedido, asi que la referencia legitima es la union de dos cosas: la
    lista blanca de canales fijos y lo que el contexto de ese turno contenia. Es
    el mismo criterio de `verificar_grounding()` en la Fase 3.

    Lista vacia significa que todo dato de contacto presente en la respuesta es
    autentico y apropiado para el carril. No dice nada sobre si el resto de la
    respuesta es correcto: es un control sobre un tipo de error concreto.
    """
    alertas: list[str] = []
    ctx = contexto.lower()

    def en_contexto(valor: str) -> bool:
        return bool(ctx) and valor.lower().rstrip(".,;)") in ctx

    for m in RE_CORREO.findall(texto):
        n = _normalizar_correo(m)
        if en_contexto(m):
            continue
        if n in PERMITIDOS["correos"]:
            if n in RESERVADOS["correos"] and not permitir_reservadas:
                alertas.append(f"canal reservado ofrecido al cliente: {m}")
            continue
        alertas.append(f"correo no autorizado: {m}")

    for m in RE_URL.findall(texto):
        n = _normalizar_url(m)
        if n in PERMITIDOS["urls"] or en_contexto(m):
            continue
        if n.startswith(DOMINIO) or f".{DOMINIO}" in n:
            alertas.append(f"ruta inventada en el dominio oficial: {m}")
        else:
            alertas.append(f"URL no autorizada: {m}")

    for m in RE_TELEFONO.findall(texto):
        n = _normalizar_telefono(m)
        crudo = re.sub(r"\D", "", m)
        if len(n) < 7 or not _parece_telefono(m, crudo) or en_contexto(m.strip()):
            continue
        if n in PERMITIDOS["telefonos"]:
            if n in RESERVADOS["telefonos"] and not permitir_reservadas:
                alertas.append(f"canal reservado ofrecido al cliente: {m.strip()}")
            continue
        alertas.append(f"telefono no autorizado: {m.strip()}")

    for m in RE_PLACEHOLDER.findall(texto):
        alertas.append(f"marcador de relleno sin completar: {m.strip()}")

    return alertas


# --------------------------------------------------------------------------------------

if __name__ == "__main__":
    print(contexto_canales())
    print("\n" + "=" * 70)

    pruebas = [
        ("Escribenos a devoluciones@ecomarket.co y te ayudamos.", 0),
        ("Comunicate al +57 602 555 0120 en horario habil.", 0),
        ("Puedes escribir a soporte@ecomarket.com para mas ayuda.", 1),      # inventado
        ("Llama al 01 8000 123 456, nuestra linea gratuita.", 1),            # inventado
        ("Radica tu caso en https://ecomarket.co/soporte/pqrs", 1),      # ruta falsa
        ("Radica tu caso en https://ecomarket.co/devoluciones", 0),
        ("Tu pedido 12345 por $149.000 llega el 22/09/2026.", 0),            # sin falsos +
        ("El reembolso de 1.250.000 pesos se procesa en 5 dias.", 0),        # monto largo
        ("Escribe a calidad@ecomarket.co y te responden.", 1),           # reservado
        ("Te comunico con calidad: +57 602 555 0160", 1),                    # reservado
    ]
    print("\nVALIDACION DE SALIDA")
    for texto, esperado in pruebas:
        a = validar_salida(texto)
        marca = "ok " if len(a) == esperado else "REV"
        print(f"[{marca}] {len(a)} alerta(s)  {texto[:58]:60s} {a or ''}")

    print("\nDERIVACION")
    for i in ["create_account", "place_order", "track_order", "get_refund"]:
        d = derivar(i)
        print(f"  {i:24s} -> {d['area'] if d else 'NO DERIVA (humano)'}")
    print(f"  {'(area calidad)':24s} -> "
          f"{derivar(area_id='calidad') or 'NO DERIVA (humano)'}")
