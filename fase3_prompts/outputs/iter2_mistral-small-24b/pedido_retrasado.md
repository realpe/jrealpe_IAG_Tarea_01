# Escenario: pedido_retrasado

- **Modelo**: `mistral-small:24b` (temperatura 0.2)
- **Version de prompts**: `v2`
- **Ejecutado**: 2026-09-18 12:49:08
- **Objetivo de la prueba**: Debe disculparse, dar el motivo real y ofrecer las opciones, SIN regalar cupones.
- **Pedido**: 12346
- **Consulta del cliente**: Ya paso la fecha y no me ha llegado nada, esto es muy demorado.

---

## A. Prompt basico (sin encuadre ni datos)

### Prompt enviado
```
Dame el estado del pedido 12346.
```

### Respuesta (3.6 s)
```
Lo siento, pero no tengo acceso a información en tiempo real o a bases de datos específicas para verificar el estado de pedidos. Te recomendaría que contactes directamente con el servicio de atención al cliente de la empresa donde realizaste el pedido para obtener la información más actualizada sobre el estado del pedido 12346.
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

### Respuesta (11.9 s)
```
Hola Carlos Andres Rojas,

Lamentamos informarle que su pedido 12346 se ha retrasado. El motivo registrado es un cierre vial en la vía Buga-Buenaventura. Su número de guía es CO-119002841 y puede rastrear su pedido en https://ecomarket.co/rastreo/CO-119002841. La fecha estimada de entrega es el 14 de septiembre de 2026, pero recuerde que esta es una estimación.

Ofrecemos dos opciones: esperar a que el pedido llegue a su destino o cancelar con reembolso total si el pedido aún no ha sido entregado. Por favor, infórmenos cuál opción prefiere.

Estamos para ayudarle con cualquier otra consulta que tenga.
```

### Verificacion de grounding
Sin hallazgos: todos los identificadores citados existen en el contexto.

---

## C. Analisis

Esta corrida se analiza en [`../../ANALISIS.md`](../../ANALISIS.md), sección 8.6: es la prueba de
control con un modelo mayor, y el caso `devolucion_fuera_de_plazo` contiene el fallo de negocio más
grave documentado en el trabajo.
