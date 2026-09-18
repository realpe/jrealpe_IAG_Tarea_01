# Escenario: pedido_en_transito

- **Modelo**: `mistral-small:24b` (temperatura 0.2)
- **Version de prompts**: `v2`
- **Ejecutado**: 2026-09-18 12:48:52
- **Objetivo de la prueba**: Caso feliz: el modelo debe usar la guia y el enlace exactos del contexto.
- **Pedido**: 12345
- **Consulta del cliente**: Buenas tardes, quiero saber donde va mi pedido por favor.

---

## A. Prompt basico (sin encuadre ni datos)

### Prompt enviado
```
Dame el estado del pedido 12345.
```

### Respuesta (9.8 s)
```
No tengo acceso a información en tiempo real o a bases de datos específicas, por lo que no puedo proporcionar el estado de un pedido en particular. Te recomiendo que te pongas en contacto con el servicio de atención al cliente de la tienda o plataforma donde realizaste tu pedido para obtener información actualizada sobre el estado del pedido 12345.
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

### Respuesta (10.9 s)
```
Buenas tardes, Ana Lucia.

Su pedido 12345 está en camino. El número de guía es SE-884213770 y puede rastrearlo en https://ecomarket.co/rastreo/SE-884213770. La fecha estimada de entrega es el 12 de septiembre de 2026, pero recuerde que esta es una estimación y no una fecha comprometida contractualmente.

Si necesita más información o ayuda adicional, no dude en decírmelo.
```

### Verificacion de grounding
Sin hallazgos: todos los identificadores citados existen en el contexto.

---

## C. Analisis

Esta corrida se analiza en [`../../ANALISIS.md`](../../ANALISIS.md), sección 8.6: es la prueba de
control con un modelo mayor, y el caso `devolucion_fuera_de_plazo` contiene el fallo de negocio más
grave documentado en el trabajo.
