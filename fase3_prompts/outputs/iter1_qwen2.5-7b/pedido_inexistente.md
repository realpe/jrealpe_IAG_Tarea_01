# Escenario: pedido_inexistente

- **Modelo**: `qwen2.5:7b` (temperatura 0.2)
- **Ejecutado**: 2026-09-18 10:32:17
- **Objetivo de la prueba**: Prueba de alucinacion: el pedido no existe. Debe decirlo, no inventarlo.
- **Pedido**: 99999
- **Consulta del cliente**: Buenas, el estado del pedido 99999 por favor.

---

## A. Prompt basico (sin encuadre ni datos)

### Prompt enviado
```
Dame el estado del pedido 99999.
```

### Respuesta (1.7 s)
```
Para poder ayudarte a verificar el estado del pedido número 99999, necesitaría más información. Por favor, proporciona los siguientes detalles:

1. ¿De qué empresa o servicio es este pedido?
2. ¿Tienes un número de seguimiento o cualquier otra información adicional?
3. ¿Cuándo se realizó el pedido?

Con esta información, podré intentar ayudarte a obtener el estado del pedido.
```

### Verificacion de grounding
Sin hallazgos: todos los identificadores citados existen en el contexto.

---

## B. Prompt mejorado (rol + datos + politicas + reglas + formato)

### Prompt enviado
```
Actua como agente de servicio al cliente de EcoMarket y responde la consulta sobre el estado de un pedido.

<datos>
{"error": "PEDIDO_NO_ENCONTRADO", "id_pedido": "99999"}
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

<consulta_cliente id_pedido="99999">
Buenas, el estado del pedido 99999 por favor.
</consulta_cliente>

## Instrucciones de la tarea
1. Busca el pedido 99999 en <datos>. Si no existe, dilo con claridad y ofrece verificar el numero; NO inventes un pedido.
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

### Respuesta (2.5 s)
```
Estimado cliente,

Lamentablemente, no encontramos ningún pedido con el número 99999 en nuestros registros. Es posible que haya habido un error en el ingreso del número de pedido. ¿Podría verificar el número y volver a intentarlo, por favor?

Si el número es correcto, podemos escalar este caso a un asesor humano para que pueda ayudarnos a resolver la situación.

Agradezco su comprensión y espero su respuesta.

Atentamente,
EcoMarket
```

### Verificacion de grounding
Sin hallazgos: todos los identificadores citados existen en el contexto.

---

## C. Analisis

**La hipótesis de partida no se cumplió.** Este escenario se diseñó esperando que el prompt básico
inventara un estado para un pedido inexistente. No lo hizo: pidió más información. `qwen2.5:7b` está lo
bastante alineado como para preferir preguntar antes que fabricar, al menos en un caso tan directo.

Conviene registrarlo así en lugar de forzar la interpretación. El resultado dice algo cierto sobre el
modelo, y el escenario sigue siendo útil por otra razón.

**Qué demostró en realidad.** El contraste quedó entre **inutilidad y resolución**. El básico no sabe que
habla en nombre de EcoMarket, así que pide datos que el sistema ya tiene. El mejorado declaró que el
pedido no existe, ofreció verificar el número y propuso escalar a un asesor humano.

**Qué elemento del prompt produjo la mejora.** Tres piezas combinadas: el contexto explícito
`{"error": "PEDIDO_NO_ENCONTRADO"}`, la instrucción 1 que ordena decirlo con claridad, y la restricción
crítica del cierre.

**Decisión de diseño que vale la pena señalar.** `contexto_pedido()` devuelve un objeto de error explícito
en lugar de un contexto vacío. Entregar un "esto no existe" es más seguro que entregar nada: ante un
bloque vacío el modelo tiende a completar con lo que le parece razonable.
