# Escenario: pedido_retrasado

- **Modelo**: `qwen2.5:7b` (temperatura 0.2)
- **Ejecutado**: 2026-09-18 10:32:06
- **Objetivo de la prueba**: Debe disculparse, dar el motivo real y ofrecer las opciones, SIN regalar cupones.
- **Pedido**: 12346
- **Consulta del cliente**: Ya paso la fecha y no me ha llegado nada, esto es muy demorado.

---

## A. Prompt basico (sin encuadre ni datos)

### Prompt enviado
```
Dame el estado del pedido 12346.
```

### Respuesta (1.7 s)
```
Para poder ayudarte a verificar el estado del pedido número 12346, necesitaría que proporcionaras más información. Por favor, proporciona el nombre del servicio o empresa de entrega con la que realizaste el pedido, ya que cada empresa tiene su propio sistema de seguimiento. Si es un pedido en línea, también podrías proporcionar el nombre del vendedor o la plataforma de comercio electrónico donde realizaste la compra.
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
  "id_pedido": "12346",
  "cliente": "Carlos Andres Rojas",
  "fecha_compra": "2026-08-28",
  "estado": "RETRASADO",
  "transportadora": "Coordinadora",
  "numero_guia": "CO-119002841",
  "url_rastreo": "https://ecomarket.co/rastreo/CO-119002841",
  "fecha_estimada_entrega": "2026-09-14",
  "retrasado": true,
  "motivo_retraso": "Cierre vial en la via Buga-Buenaventura",
  "items": [
    {
      "sku": "ECO-DET-1L",
      "nombre": "Detergente biodegradable 1L",
      "categoria": "DURADERO",
      "cantidad": 3,
      "precio_unitario": 32000
    }
  ],
  "total": 96000
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

<consulta_cliente id_pedido="12346">
Ya paso la fecha y no me ha llegado nada, esto es muy demorado.
</consulta_cliente>

## Instrucciones de la tarea
1. Busca el pedido 12346 en <datos>. Si no existe, dilo con claridad y ofrece verificar el numero; NO inventes un pedido.
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

### Respuesta (4.3 s)
```
Buen día, señor Carlos Andrés Rojas.

Le informo que su pedido 12346 se encuentra **RETRASADO**. Según nuestros registros, la transportadora es Coordinadora y el número de guía es CO-119002841. Puede rastrear su pedido [aquí](https://ecomarket.co/rastreo/CO-119002841).

El motivo del retraso es un cierre vial en la vía Buga-Buenaventura. La fecha estimada de entrega es el 14 de septiembre de 2026. Le ofrecemos la opción de esperar la entrega o, si aún no ha sido realizada, cancelar el pedido con reembolso total.

Le pedimos disculpas por el inconveniente y esperamos su pronta respuesta.

Si necesita más ayuda, no dude en contactarnos.
```

### Verificacion de grounding
Sin hallazgos: todos los identificadores citados existen en el contexto.

---

## C. Analisis

**Qué hizo el prompt básico.** Volvió a pedir datos al cliente, esta vez el nombre de la transportadora
y de la plataforma de compra. Ante un cliente que escribe "esto es muy demorado", responder con un
cuestionario es el peor resultado posible en términos de experiencia.

**Qué corrigió el mejorado.** Reconoció el retraso, informó el motivo real registrado en los datos —el
cierre vial en la vía Buga-Buenaventura—, entregó guía y enlace, dio la nueva fecha estimada y presentó
las dos opciones vigentes: esperar o cancelar con reembolso.

**Qué elemento del prompt produjo la mejora.** La instrucción 5, condicionada a `retrasado == true`, que
enumera exactamente los cuatro movimientos que exige la política 2.1. El modelo los siguió en orden.

**El acierto que más importa.** Cumplió la prohibición de ofrecer compensaciones. Un asistente sin esa
restricción tiende a regalar un cupón para calmar al cliente, que es justamente el compromiso no
autorizado descrito en la Fase 2, sección 3.1. La instrucción negativa explícita funcionó.

**Defecto detectado.** Escribió "su pedido se encuentra **RETRASADO**", dejando el código interno del
estado en la respuesta al cliente, contra la instrucción 2. El modelo aplicó la traducción a lenguaje
natural solo en el ejemplo que el prompt mencionaba (`EN_TRANSITO`) y no generalizó la regla.
