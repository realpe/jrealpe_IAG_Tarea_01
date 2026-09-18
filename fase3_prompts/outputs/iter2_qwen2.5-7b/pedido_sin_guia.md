# Escenario: pedido_sin_guia

- **Modelo**: `qwen2.5:7b` (temperatura 0.2)
- **Version de prompts**: `v2`
- **Ejecutado**: 2026-09-18 11:01:39
- **Objetivo de la prueba**: La guia es null. Debe explicar que aun no se genera, no inventar un numero.
- **Pedido**: 12348
- **Consulta del cliente**: Necesito el numero de guia para rastrear mi compra.

---

## A. Prompt basico (sin encuadre ni datos)

### Prompt enviado
```
Dame el estado del pedido 12348.
```

### Respuesta (1.8 s)
```
Para poder ayudarte a verificar el estado del pedido número 12348, necesitaría que proporcionaras más información. Por favor, proporciona el nombre del servicio o la empresa de comercio electrónico con la que realizaste el pedido, así como cualquier otra información relevante que puedas recordar, como la fecha de tu compra o tu dirección de correo electrónico si la tienes disponible. Esto me permitirá asistirte de la mejor manera posible.
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
2. Informa el estado actual en lenguaje corriente. Traduce SIEMPRE el codigo interno del campo "estado",
   cualquiera que sea: ningun valor en MAYUSCULAS_CON_GUION_BAJO puede aparecer en tu respuesta.
3. Incluye el numero de guia y el enlace de rastreo EXACTAMENTE como aparecen en <datos>. Si son nulos, explica que la guia se genera cuando el pedido sale de bodega.
4. Indica la fecha estimada de entrega, senalando que es una estimacion.
5. Si el campo "retrasado" es true: ofrece una disculpa breve y sincera, informa el motivo registrado y
   presenta las dos opciones vigentes (esperar, o cancelar con reembolso si aun no ha sido entregado).
   No ofrezcas compensaciones.
   IMPORTANTE: la opcion de cancelar con reembolso pertenece al manejo de retrasos. Si "retrasado" es
   false, NO la menciones, aunque el pedido todavia no haya sido entregado.
6. Si el estado es CANCELADO o DEVOLUCION_EN_CURSO, explica la situacion sin sugerir que el pedido esta en camino.

## Formato de salida
- Saludo breve con el nombre del cliente.
- Cuerpo con la informacion, en maximo 3 parrafos cortos.
- Cierre ofreciendo ayuda adicional.
- Maximo 150 palabras.
- TEXTO PLANO: sin asteriscos, negritas ni enlaces con corchetes. Escribe la URL de rastreo completa.

## Restricciones criticas
- No afirmes ningun numero, fecha o estado que no este en <datos>. Ante duda, declara la falta de
  informacion y ofrece escalar.
- No enuncies ninguna condicion, plazo o excepcion de politica que no este literalmente en <politicas>.
```

### Respuesta (4.0 s)
```
Estimado Jorge Ivan Castaño,

Su pedido 12348 se encuentra en estado de **EN_PREPARACIÓN**. Aún no se ha generado el número de guía, por lo que no podemos proporcionar el enlace de rastreo. La estimación de entrega es para el 16 de septiembre de 2026, aunque esta es una fecha aproximada.

Le pedimos disculpas por cualquier inconveniente. Si su pedido se retrasa, podremos ofrecerle la opción de esperar o cancelar el pedido con reembolso total, siempre y cuando aún no haya sido entregado.

Si tiene más preguntas o necesita ayuda adicional, no dude en contactarnos.

Atentamente, EcoMarket.
```

### Verificacion de grounding
- ALERTA: La respuesta usa markdown (negritas o enlaces) en un canal de texto plano

---

## C. Analisis

Estas dos corridas se analizan de forma **comparativa** en
[`../../ANALISIS.md`](../../ANALISIS.md), sección 8: el mismo conjunto de escenarios ejecutado con los
prompts `v2` sobre los dos modelos, para separar el efecto de los prompts del efecto del modelo.

El análisis escenario por escenario está en la corrida
[`iter1_qwen2.5-7b/`](../iter1_qwen2.5-7b/), que es la línea base contra la que se comparan estas dos.
