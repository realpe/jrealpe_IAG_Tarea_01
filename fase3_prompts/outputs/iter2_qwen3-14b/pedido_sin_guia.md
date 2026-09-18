# Escenario: pedido_sin_guia

- **Modelo**: `qwen3:14b` (temperatura 0.2)
- **Version de prompts**: `v2`
- **Ejecutado**: 2026-09-18 11:04:52
- **Objetivo de la prueba**: La guia es null. Debe explicar que aun no se genera, no inventar un numero.
- **Pedido**: 12348
- **Consulta del cliente**: Necesito el numero de guia para rastrear mi compra.

---

## A. Prompt basico (sin encuadre ni datos)

### Prompt enviado
```
Dame el estado del pedido 12348.
```

### Respuesta (9.3 s)
```
Lamentablemente, no tengo acceso a información específica sobre pedidos o sistemas internos de empresas. Para obtener el estado de su pedido (12348), le recomiendo que:

1. **Consulte directamente con el vendedor o plataforma** donde realizó la compra (por ejemplo, a través de su sitio web, app o correo electrónico de confirmación).
2. **Verifique su bandeja de entrada** en caso de haber recibido un correo de seguimiento.
3. **Contacte al servicio al cliente** de la empresa si no encuentra la información.

¿Necesita ayuda para encontrar el contacto de soporte o orientación sobre cómo seguir el proceso?
```

### Verificacion de grounding
- ALERTA: La respuesta usa markdown (negritas o enlaces) en un canal de texto plano

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

### Respuesta (14.5 s)
```
Estimado Jorge Ivan Castaño, su pedido 12348 está en preparación y se encuentra en proceso de embalaje. Actualmente no disponemos del número de guía, ya que se genera una vez que el pedido salga de nuestra bodega. La fecha estimada de entrega es el 16 de septiembre de 2026, aunque este plazo es orientativo según nuestra política de envíos.  

Quedamos atentos para informarle el número de guía y el enlace de rastreo en cuanto el pedido esté listo para enviar. Si tiene preguntas adicionales, no dude en contactarnos.  

Atentamente,  
Equipo EcoMarket.
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
