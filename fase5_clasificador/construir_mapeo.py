#!/usr/bin/env python3
"""
Construye la tabla de mapeo intencion -> carril a partir del dataset Bitext.

POR QUE ESTA TABLA ES EL CORAZON DEL ETIQUETADO
-----------------------------------------------
El dataset trae INTENCION (que quiere el cliente), no CARRIL (quien debe
responder y con que grado de supervision). El carril depende de la politica de
EcoMarket, no del dataset.

La buena noticia es que el mapeo se hace una sola vez por intencion y no por
ejemplo: 27 decisiones en lugar de 24.000. Esa es la diferencia entre viable y
no viable para un trabajo individual.

EL CRITERIO, el mismo de la Fase 1
----------------------------------
    ¿Existe una respuesta correcta segun la politica vigente,
    o hay que decidir una excepcion?

    automatico        -> la politica responde; nadie decide nada
    copiloto          -> hay una decision con efecto economico o una excepcion
    humano_exclusivo  -> lo asigna la CAPA 0, no el clasificador semantico
    derivacion  -> el asistente de EcoMarket no cubre esto

SOBRE 'derivacion'
------------------
El dataset es de atencion al cliente generica e incluye gestion de cuentas,
suscripciones y colocacion de pedidos. El asistente de EcoMarket, tal como se
diseno en la Fase 1, atiende estado de pedidos y devoluciones.

La primera version descartaba esas intenciones. Se cambio al implementar la
lista blanca de canales (canales.py): si el asistente sabe a que area pertenece
el caso, entregar el canal correcto en un turno es mejor servicio que mandarlo
a una cola. Reconocer 'esto no es mio' pasa a ser una capacidad del clasificador
y no un descarte, asi que se entrena como una clase mas.

Sin esta clase, un mensaje sobre recuperar la contrasena caeria en el centroide
mas cercano de los otros carriles y se respondería mal con seguridad.

Ninguna intencion se mapea a 'humano_exclusivo': ese carril lo decide la capa 0
por reglas deterministas sobre el texto y sobre datos de la BD (monto,
reincidencia), no por la intencion declarada. Un cliente puede pedir el estado
de su pedido y mencionar una reaccion alergica en la misma frase.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).parent

# (intencion, carril propuesto, justificacion)
MAPEO = [
    # --- Consultas que la politica responde ------------------------------------
    ("track_order", "automatico",
     "Estado del pedido: dato transaccional que se resuelve con function calling"),
    ("delivery_period", "automatico",
     "Plazo de entrega: la politica de envios lo establece"),
    ("delivery_options", "automatico",
     "Opciones de envio: informacion publica de la politica"),
    ("check_refund_policy", "automatico",
     "Consulta normativa pura: la seccion 1 de la politica la responde"),
    ("track_refund", "automatico",
     "Estado de un reembolso ya aprobado: dato transaccional"),
    ("check_cancellation_fee", "automatico",
     "Consulta de una condicion escrita en la politica"),
    ("check_payment_methods", "automatico",
     "Informacion publica, sin decision asociada"),
    ("check_invoice", "automatico",
     "Consulta del estado de una factura existente"),
    ("get_invoice", "automatico",
     "Entrega de un documento ya emitido, sin criterio de por medio"),
    ("contact_customer_service", "automatico",
     "Informacion de canales. OJO: es la intencion donde los modelos fabricaron "
     "correos y telefonos (Fase 3, 8.3a); exige lista blanca de canales oficiales"),

    # --- Decisiones con efecto: el humano aprueba ------------------------------
    ("get_refund", "copiloto",
     "Solicitud de reembolso: compromete dinero de la empresa"),
    ("cancel_order", "copiloto",
     "Cancelar tiene efecto economico y depende del estado del pedido"),
    ("change_order", "copiloto",
     "Modificar un pedido en curso altera un compromiso ya adquirido"),
    ("change_shipping_address", "copiloto",
     "Cambiar destino de un envio en curso: riesgo operativo y de fraude"),
    ("set_up_shipping_address", "copiloto",
     "Afecta a donde se entrega la mercancia; se trata igual que el cambio"),
    ("payment_issue", "copiloto",
     "Problema con dinero del cliente: requiere verificacion humana"),
    ("complaint", "copiloto",
     "Queja formal. Si la politica la cubre puede bajar a automatico; ante la "
     "duda se degrada al carril mas humano"),
    ("contact_human_agent", "copiloto",
     "El cliente pide explicitamente una persona. La Fase 2 (3.5) establece que "
     "ese pedido se respeta sin obligarlo a insistir"),

    # --- Otra area de EcoMarket lo atiende: se entrega el canal ----------------
    ("create_account", "derivacion", "Gestion de cuentas: la atiende el area de cuentas"),
    ("delete_account", "derivacion", "Gestion de cuentas: la atiende el area de cuentas"),
    ("edit_account", "derivacion", "Gestion de cuentas: la atiende el area de cuentas"),
    ("switch_account", "derivacion", "Gestion de cuentas: la atiende el area de cuentas"),
    ("recover_password", "derivacion", "Autenticacion: flujo propio del area de cuentas"),
    ("registration_problems", "derivacion", "Soporte tecnico de registro: area de cuentas"),
    ("place_order", "derivacion", "Venta: la atiende el area comercial"),
    ("newsletter_subscription", "derivacion", "Marketing: la atiende el area comercial"),
    ("review", "derivacion", "Dejar resena: la recibe el area comercial"),
]


def main() -> None:
    df = pd.read_parquet(AQUI / "datos" / "bitext_es.parquet")
    conteos = df["intent"].value_counts().to_dict()
    categorias = df.groupby("intent")["category"].first().to_dict()

    mapeadas = {i for i, _, _ in MAPEO}
    faltan = set(conteos) - mapeadas
    sobran = mapeadas - set(conteos)
    if faltan:
        print(f"AVISO: intenciones del dataset sin mapear -> {sorted(faltan)}")
    if sobran:
        print(f"AVISO: intenciones mapeadas que no existen -> {sorted(sobran)}")

    filas = []
    for intencion, carril, just in MAPEO:
        filas.append({
            "intencion": intencion,
            "categoria": categorias.get(intencion, "?"),
            "ejemplos": conteos.get(intencion, 0),
            "carril_propuesto": carril,
            "carril_final": carril,      # <- Jose Luis edita ESTA columna
            "justificacion": just,
            "revisado": "no",
        })

    destino = AQUI / "datos" / "mapeo_intencion_carril.csv"
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)

    print(f"\n{len(filas)} intenciones mapeadas -> {destino.name}\n")
    resumen = {}
    for r in filas:
        c = r["carril_propuesto"]
        resumen.setdefault(c, [0, 0])
        resumen[c][0] += 1
        resumen[c][1] += r["ejemplos"]
    print(f"{'carril':20s} {'intenciones':>12s} {'ejemplos':>10s}")
    for c, (n, e) in sorted(resumen.items(), key=lambda x: -x[1][1]):
        print(f"{c:20s} {n:12d} {e:10,d}")
    print(f"\nejemplos utilizables para entrenar: {sum(e for _, e in resumen.values()):,}")


if __name__ == "__main__":
    main()
