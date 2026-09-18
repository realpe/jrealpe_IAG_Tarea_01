# Escenario: pedido_en_transito

- **Modelo**: `qwen2.5:7b` (temperatura 0.2)
- **Ejecutado**: 2026-09-18 10:32:00
- **Objetivo de la prueba**: Caso feliz: el modelo debe usar la guia y el enlace exactos del contexto.
- **Pedido**: 12345
- **Consulta del cliente**: Buenas tardes, quiero saber donde va mi pedido por favor.

---

## A. Prompt basico (sin encuadre ni datos)

### Prompt enviado
```
Dame el estado del pedido 12345.
```

### Respuesta (4.2 s)
```
Para poder ayudarte a verificar el estado del pedido número 12345, necesitaría que proporcionaras más información. Por ejemplo, ¿de quién es el pedido? ¿De qué empresa o tienda en línea es? Si tienes acceso a una cuenta de compras en línea, generalmente puedes verificar el estado del pedido desde allí.

Si no tienes acceso a tu cuenta de compras, podrías intentar contactar al servicio al cliente de la empresa que realizó la venta. Ellos podrían proporcionarte la información que necesitas sobre el estado del pedido.
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
  "id_pedido": "12345",
  "cliente": "Ana Lucia Moreno",
  "fecha_compra": "2026-09-01",
  "estado": "EN_TRANSITO",
  "transportadora": "Servientrega",
  "numero_guia": "SE-884213770",
  "url_rastreo": "https://ecomarket.co/rastreo/SE-884213770",
  "fecha_estimada_entrega": "2026-09-12",
  "retrasado": false,
  "items": [
    {
      "sku": "ECO-BOT-500",
      "nombre": "Botella termica de acero 500ml",
      "categoria": "DURADERO",
      "cantidad": 1,
      "precio_unitario": 89000
    }
  ],
  "total": 89000
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

<consulta_cliente id_pedido="12345">
Buenas tardes, quiero saber donde va mi pedido por favor.
</consulta_cliente>

## Instrucciones de la tarea
1. Busca el pedido 12345 en <datos>. Si no existe, dilo con claridad y ofrece verificar el numero; NO inventes un pedido.
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

### Respuesta (3.3 s)
```
Buenas tardes, Ana Lucia.

Su pedido 12345 está **va en camino** con la transportadora Servientrega, con el número de guía SE-884213770. Puede rastrearlo [aquí](https://ecomarket.co/rastreo/SE-884213770). La fecha estimada de entrega es el 12 de septiembre, pero recuerde que esto es una estimación.

Si tiene alguna otra consulta o necesita ayuda adicional, no dude en decírmelo.
```

### Verificacion de grounding
Sin hallazgos: todos los identificadores citados existen en el contexto.

---

## C. Analisis

**Qué hizo el prompt básico.** No identificó a EcoMarket como remitente y devolvió el trabajo al
cliente: le pidió indicar "de qué empresa o tienda en línea" es el pedido y le sugirió consultar su
cuenta de compras. Sin contexto, el modelo tiene el número del pedido y nada más, de modo que la
respuesta es cortés e inservible.

**Qué corrigió el mejorado.** Saludó a Ana Lucía por su nombre, citó la guía `SE-884213770` y el enlace
de rastreo exactamente como aparecen en `<datos>`, informó la fecha estimada y advirtió que es una
estimación.

**Qué elemento del prompt produjo la mejora.** El bloque `<datos>` con el JSON del pedido. Es el caso más
claro del principio de la Fase 1: la mejora no vino de un modelo mejor sino de entregarle el dato. La
instrucción 3 ("incluye el número de guía EXACTAMENTE como aparece") es la que evitó que lo parafraseara.

**Defectos detectados.**

- Escribió "está **va en camino**", con la concordancia rota. La instrucción 2 da la traducción literal
  `EN_TRANSITO` → "va en camino" y el modelo la insertó tal cual en la frase. Conviene pedir lenguaje
  natural en vez de dictar la cadena exacta.
- Usó markdown (negritas y enlace `[aquí](...)`) en un canal que sería texto plano. El prompt no
  especificó el formato de salida.
