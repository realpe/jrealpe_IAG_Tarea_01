# Escenario: pedido_sin_guia

- **Modelo**: `qwen2.5:7b` (temperatura 0.2)
- **Ejecutado**: 2026-09-18 10:32:13
- **Objetivo de la prueba**: La guia es null. Debe explicar que aun no se genera, no inventar un numero.
- **Pedido**: 12348
- **Consulta del cliente**: Necesito el numero de guia para rastrear mi compra.

---

## A. Prompt basico (sin encuadre ni datos)

### Prompt enviado
```
Dame el estado del pedido 12348.
```

### Respuesta (2.7 s)
```
Para poder ayudarte a verificar el estado del pedido número 12348, necesitaría que proporcionaras más información. Por favor, considera las siguientes opciones:

1. **Nombre del Cliente**: Aunque no es siempre necesario, puede ser útil para verificar el pedido.
2. **Plataforma de Compras**: ¿Dónde realizaste la compra? (Ej: Amazon, eBay, AliExpress, etc.)
3. **Detalles del Pedido**: Si tienes información adicional como la fecha de la compra o el nombre del vendedor.

Si no tienes acceso a tu cuenta de compras, puedes intentar contactar al servicio al cliente de la plataforma donde realizaste la compra para obtener más información sobre el estado de tu pedido.
```

### Verificacion de grounding
Sin hallazgos: todos los identificadores citados existen en el contexto.

---

## B. Prompt mejorado (rol + datos + politicas + reglas + formato)

### Prompt enviado
```
Actua como agente de servicio al cliente de EcoMarket y responde la consulta sobre el estado de un pedido.

<datos>
{
  "id_pedido": "12348",
  "cliente": "Jorge Ivan Castaño",
  "fecha_compra": "2026-09-09",
  "estado": "EN_PREPARACION",
  "transportadora": null,
  "numero_guia": null,
  "url_rastreo": null,
  "fecha_estimada_entrega": "2026-09-16",
  "retrasado": false,
  "items": [
    {
      "sku": "ECO-CAF-500",
      "nombre": "Cafe organico molido 500g",
      "categoria": "PERECEDERO",
      "cantidad": 2,
      "precio_unitario": 38000
    },
    {
      "sku": "ECO-MIE-350",
      "nombre": "Miel de abejas cruda 350g",
      "categoria": "PERECEDERO",
      "cantidad": 1,
      "precio_unitario": 45000
    }
  ],
  "total": 121000
}
</datos>

<politicas>
## 2. Política de envíos

- **Preparación**: 1–2 días hábiles desde la confirmación del pago.
- **Tiempos de tránsito estimados**: 2–3 días hábiles en ciudades principales; 4–7 días hábiles en el resto del país.
- **Envío gratis** en pedidos superiores a $120.000 COP.
- Las fechas de entrega son **estimadas**, no comprometidas contractualmente. El asistente **nunca** debe
  prometer una fecha exacta ni garantizar una entrega.

### 2.1 Manejo de retrasos
Cuando un pedido está marcado como `RETRASADO`, el asistente debe:

1. Reconocer el inconveniente y ofrecer una disculpa breve y sincera (sin excesos).
2. Informar el motivo registrado, si existe.
3. Entregar la nueva fecha estimada y el enlace de rastreo.
4. Ofrecer las opciones vigentes: esperar, o cancelar con reembolso total si el pedido aún no ha sido entregado.

**Prohibido**: ofrecer compensaciones, cupones o descuentos por iniciativa propia. Eso lo autoriza un humano.

---
</politicas>

<consulta_cliente id_pedido="12348">
Necesito el numero de guia para rastrear mi compra.
</consulta_cliente>

## Instrucciones de la tarea
1. Busca el pedido 12348 en <datos>. Si no existe, dilo con claridad y ofrece verificar el numero; NO inventes un pedido.
2. Informa el estado actual en lenguaje del cliente (no uses el codigo interno tal cual: "EN_TRANSITO" se dice "va en camino").
3. Incluye el numero de guia y el enlace de rastreo EXACTAMENTE como aparecen en <datos>. Si son nulos, explica que la guia se genera cuando el pedido sale de bodega.
4. Indica la fecha estimada de entrega, senalando que es una estimacion.
5. Si el campo "retrasado" es true: ofrece una disculpa breve y sincera, informa el motivo registrado y presenta las dos opciones vigentes (esperar, o cancelar con reembolso si aun no ha sido entregado). No ofrezcas compensaciones.
6. Si el estado es CANCELADO o DEVOLUCION_EN_CURSO, explica la situacion sin sugerir que el pedido esta en camino.

## Formato de salida
- Saludo breve con el nombre del cliente.
- Cuerpo con la informacion (maximo 3 parrafos cortos o una lista de 3 vinetas).
- Cierre ofreciendo ayuda adicional.
- Maximo 150 palabras.

## Restriccion critica
No afirmes ningun numero, fecha o estado que no este en <datos>. Ante duda, declara la falta de informacion y ofrece escalar.
```

### Respuesta (4.1 s)
```
Buen día, señor Jorge Ivan Castaño.

Su pedido 12348 se encuentra en preparación y aún no ha sido enviado. Según nuestras políticas, el envío se realizará en 1-2 días hábiles desde la confirmación del pago.

No tenemos el número de guía ni el enlace de rastreo disponibles en este momento, ya que el pedido aún no ha salido de nuestra bodega. La fecha estimada de entrega es el 16 de septiembre, pero recuerde que esto es una estimación y no una garantía.

Si tiene alguna preocupación, le sugerimos que espere a la entrega o, si aún no ha sido enviada, puede optar por cancelar el pedido y solicitar un reembolso total. Le agradecemos su comprensión. 

Estamos a su disposición para cualquier otra consulta.
```

### Verificacion de grounding
Sin hallazgos: todos los identificadores citados existen en el contexto.

---

## C. Analisis

**Qué hizo el prompt básico.** Pidió datos y, al enumerar posibles vendedores, mencionó "Amazon, eBay,
AliExpress". Es una alucinación de contexto: el modelo construye un escenario plausible e inventado
porque nada en el prompt le dice dónde está parado.

**Qué corrigió el mejorado.** Este era el escenario de riesgo —`numero_guia` es `null`— y lo resolvió
bien: explicó que el pedido está en preparación y que la guía se genera cuando sale de bodega. **No
inventó un número de guía**, que era exactamente lo que se estaba probando.

**Qué elemento del prompt produjo la mejora.** La instrucción 3 prevé el caso nulo de forma explícita.
Anticipar el valor ausente en la instrucción evita que el modelo llene el vacío por su cuenta.

**Defecto detectado, y es el más instructivo.** Ofreció "cancelar el pedido y solicitar un reembolso
total". Esa opción vive en la sección 2.1 de la política, que aplica únicamente a pedidos `RETRASADO`, y
este pedido está en `EN_PREPARACION`. El modelo tomó una regla y la aplicó fuera de su ámbito.

**La lección de diseño.** Se le inyectó la sección 2 completa de la política, y el modelo entiende todo lo
que hay en el contexto como aplicable. Cuanto más contexto irrelevante se entrega, más probable es este
error. Es un argumento directo a favor de la recuperación granular que hará el RAG: entregar el fragmento
que corresponde al caso en lugar del capítulo entero.
