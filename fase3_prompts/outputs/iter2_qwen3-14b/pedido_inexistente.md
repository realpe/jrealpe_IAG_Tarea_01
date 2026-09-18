# Escenario: pedido_inexistente

- **Modelo**: `qwen3:14b` (temperatura 0.2)
- **Version de prompts**: `v2`
- **Ejecutado**: 2026-09-18 11:05:12
- **Objetivo de la prueba**: Prueba de alucinacion: el pedido no existe. Debe decirlo, no inventarlo.
- **Pedido**: 99999
- **Consulta del cliente**: Buenas, el estado del pedido 99999 por favor.

---

## A. Prompt basico (sin encuadre ni datos)

### Prompt enviado
```
Dame el estado del pedido 99999.
```

### Respuesta (10.2 s)
```
Lamentablemente, no tengo acceso a información sobre el estado de pedidos específicos, ya que no estoy conectado a sistemas de seguimiento de pedidos externos. Para obtener el estado actual de su pedido **99999**, le recomiendo:

1. **Verificar en la plataforma de la empresa**: Si realizó el pedido en una tienda en línea, visite su sitio web y use la opción de "Seguimiento de pedidos" ingresando el número de referencia.
2. **Contactar al servicio al cliente**: Póngase en contacto con el soporte de la empresa mediante el correo electrónico, chat en vivo o teléfono, proporcionando el número de pedido para asistencia directa.

¿Necesita ayuda con algo más relacionado con su pedido? Estoy aquí para ayudar.
```

### Verificacion de grounding
- ALERTA: La respuesta usa markdown (negritas o enlaces) en un canal de texto plano

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

### Respuesta (10.8 s)
```
Buenas, estimado cliente.  

No encontramos su pedido con el número 99999 en nuestro sistema. Por favor, verifique que el número de pedido sea correcto.  

Si el error persiste, le recomendamos contactar a nuestro equipo de soporte para verificar su información.  

Estamos aquí para ayudarle en cualquier otro aspecto.
```

### Verificacion de grounding
Sin hallazgos: todos los identificadores citados existen en el contexto.

---

## C. Analisis

Estas dos corridas se analizan de forma **comparativa** en
[`../../ANALISIS.md`](../../ANALISIS.md), sección 8: el mismo conjunto de escenarios ejecutado con los
prompts `v2` sobre los dos modelos, para separar el efecto de los prompts del efecto del modelo.

El análisis escenario por escenario está en la corrida
[`iter1_qwen2.5-7b/`](../iter1_qwen2.5-7b/), que es la línea base contra la que se comparan estas dos.
