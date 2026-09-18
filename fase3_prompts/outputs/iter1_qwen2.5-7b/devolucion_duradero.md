# Escenario: devolucion_duradero

- **Modelo**: `qwen2.5:7b` (temperatura 0.2)
- **Ejecutado**: 2026-09-18 10:32:31
- **Objetivo de la prueba**: Caso elegible dentro de plazo: debe dar los pasos concretos.
- **Pedido**: 12352
- **Consulta del cliente**: Los panos de cocina no eran lo que esperaba, quiero devolverlos. Estan sin usar y con su empaque original.

---

## A. Prompt basico (sin encuadre ni datos)

### Prompt enviado
```
Un cliente quiere devolver el pedido 12352. Dile como hacerlo.
```

### Respuesta (9.4 s)
```
Claro, aquí tienes un ejemplo de cómo puedes instruir al cliente para que devuelva el pedido 12352:

---

Estimado cliente,

Gracias por contactarnos sobre la devolución del pedido 12352. Estamos aquí para ayudarte. Para poder procesar tu devolución de manera efectiva, necesitamos que sigas estos pasos:

1. **Verifica el pedido**: Asegúrate de que el pedido 12352 sea el que deseas devolver. Si hay algún error, no dudes en ponerte en contacto con nosotros.

2. **Prepara el paquete**: 
   - **Etiquetar el paquete**: Escribe "DEVOLUCIÓN" en grandes letras en la cara exterior del paquete. Incluye la referencia del pedido (12352) en la etiqueta.
   - **Empaquetar bien**: Usa burbujas de plástico, papel de burbuja o cualquier otro material de empaquetado para proteger el contenido. Asegúrate de que los productos estén en perfectas condiciones.

3. **Envía el paquete**: 
   - **Método de envío**: Podemos sugerirte que uses un servicio de envío que te dé un número de seguimiento, ya que esto facilitará el seguimiento de tu devolución.
   - **Dirección de devolución**: Envía el paquete a la siguiente dirección:
     ```
     [Nombre de la empresa]
     [Dirección de la empresa]
     [Código postal]
     [País]
     ```

4. **Envía la confirmación**: Una vez que hayas enviado el paquete, envíanos un correo electrónico a [dirección de correo electrónico] con la información del envío (número de seguimiento, método de envío, etc.). Esto nos ayudará a procesar tu devolución de manera más rápida.

5. **Espera la aprobación de la devolución**: Una vez que recibamos el paquete, revisaremos el estado de los productos y te contactaremos para informarte sobre el estado de tu devolución.

Si tienes alguna pregunta o necesitas más ayuda, no dudes en ponerte en contacto con nosotros. Estamos aquí para ayudarte.

¡Gracias por tu comprensión y paciencia!

Atentamente,
[Tu nombre]
[Nombre de la empresa]
[Contacto de la empresa]

---

Espero que esta guía sea útil. Si necesitas más detalles o ajustes, no dudes en decírmelo.
```

### Verificacion de grounding
Sin hallazgos: todos los identificadores citados existen en el contexto.

---

## B. Prompt mejorado (rol + datos + politicas + reglas + formato)

### Prompt enviado
```
Actua como agente de servicio al cliente de EcoMarket y atiende una solicitud de devolucion.

<datos>
{
  "id_pedido": "12352",
  "cliente": "Ricardo Alberto Nieto",
  "fecha_compra": "2026-09-07",
  "estado": "ENTREGADO",
  "transportadora": "Servientrega",
  "numero_guia": "SE-884225514",
  "url_rastreo": "https://ecomarket.co/rastreo/SE-884225514",
  "fecha_estimada_entrega": "2026-09-10",
  "fecha_entrega_real": "2026-09-09",
  "retrasado": false,
  "items": [
    {
      "sku": "ECO-PAN-REU",
      "nombre": "Paños reutilizables de cocina x6",
      "categoria": "DURADERO",
      "cantidad": 1,
      "precio_unitario": 55000
    }
  ],
  "total": 55000
}
</datos>

<politicas>
## 1. Política de devoluciones

### 1.1 Plazo general
El cliente tiene **30 días calendario** contados desde la **fecha de entrega efectiva** para solicitar
una devolución, siempre que el producto sea elegible según la sección 1.2.

### 1.2 Elegibilidad por categoría de producto

| Categoría | ¿Admite devolución? | Condiciones |
|---|---|---|
| `DURADERO` | **Sí** | Producto sin uso, con empaque original y etiquetas. Reembolso al medio de pago original en 5–10 días hábiles. |
| `HIGIENE_PERSONAL` | **Solo si el empaque está sin abrir** | Por normativa sanitaria, un producto de higiene con el sello roto no puede reingresar al inventario. |
| `PERECEDERO` | **No** | Alimentos y productos con fecha de vencimiento no se reciben de vuelta. |

### 1.3 Excepción por producto defectuoso o dañado en transporte
La restricción de la sección 1.2 **no aplica** cuando el producto llegó dañado, incompleto o defectuoso.
En ese caso, **cualquier categoría** —incluidos perecederos y productos de higiene— da derecho a
**reposición o reembolso total**, sin importar el estado del empaque.

Requisito: el cliente debe reportarlo dentro de las **72 horas** siguientes a la entrega y adjuntar
evidencia fotográfica. El costo del transporte de retorno lo asume EcoMarket.

### 1.4 Casos que NO puede resolver el asistente automático
Deben escalarse a un agente humano:

- Solicitudes fuera del plazo de 30 días (requieren aprobación discrecional).
- Reclamos por más de **$500.000 COP**.
- Cualquier mención de daño a la salud, reacción alérgica o intoxicación.
- Amenaza de acción legal, queja ante la Superintendencia de Industria y Comercio, o exposición en redes.
- Segunda devolución del mismo cliente en un período de 60 días.

---
</politicas>

<consulta_cliente id_pedido="12352">
Los panos de cocina no eran lo que esperaba, quiero devolverlos. Estan sin usar y con su empaque original.
</consulta_cliente>

## Procedimiento de decision (siguelo en este orden)
Paso 1 — Localiza el pedido 12352 en <datos>. Si no existe, dilo y detente.

Paso 2 — ¿El cliente reporta un producto danado, defectuoso o incompleto?
   - SI  -> aplica la excepcion por producto defectuoso de <politicas>. En ese caso la devolucion procede
            para CUALQUIER categoria, incluidos PERECEDERO e HIGIENE_PERSONAL. Ve al Paso 5.
   - NO  -> continua al Paso 3.

Paso 3 — Verifica el plazo: cuenta los dias entre "fecha_entrega_real" y la fecha de hoy (2026-09-18).
   - Si superan el plazo de <politicas>, la solicitud requiere aprobacion de un asesor humano. Escala y detente.
   - Si el pedido aun no ha sido entregado, indica que la devolucion se tramita despues de recibirlo, o que
     puede solicitar la cancelacion si aun no ha salido. Detente.

Paso 4 — Verifica la categoria de CADA item del pedido en <datos> y aplica la tabla de elegibilidad:
   - DURADERO          -> procede con las condiciones de la politica.
   - HIGIENE_PERSONAL  -> procede SOLO si el empaque esta sin abrir. Si no lo sabes, preguntalo.
   - PERECEDERO        -> NO procede. Explica la razon sanitaria, no solo la negativa.
   Si el pedido mezcla categorias, resuelve item por item: unos pueden proceder y otros no.

Paso 5 — Redacta la respuesta.

## Como redactar
- Empieza reconociendo la situacion del cliente antes de dar la respuesta administrativa.
- Si la devolucion NO procede: explica el porque de forma clara y humana, indica que es una condicion de la
  politica y no una decision personal, y ofrece una alternativa real (asesoria de uso, escalar a un asesor).
  Nunca cierres con una negativa seca.
- Si procede: entrega los pasos concretos, numerados, y los tiempos indicados en <politicas>.
- Si el caso cae en los supuestos de escalamiento de <politicas> (monto alto, tema de salud, accion legal,
  fuera de plazo), escala a un asesor humano y no decidas por tu cuenta.

## Restricciones criticas
- No autorices el reembolso: explica el procedimiento. La autorizacion la da un asesor.
- No inventes plazos, montos ni condiciones que no esten en <politicas>.
- Maximo 180 palabras.
```

### Respuesta (4.6 s)
```
Estimado señor Nieto,

Gracias por contactarse con EcoMarket. Lamentamos que los paños reutilizables de cocina no cumplieran con sus expectativas. Según nuestras políticas, los productos de la categoría `DURADERO` son elegibles para devolución siempre que estén sin uso y con su empaque original, lo cual parece ser el caso.

Para proceder con la devolución, por favor siga estos pasos:

1. Envíe los paños reutilizables de cocina junto con el empaque original a la dirección que nos proporcionará Servientrega.
2. Una vez recibidos, le haremos el reembolso al medio de pago original en un plazo de 5 a 10 días hábiles.

Si tiene alguna duda o necesita ayuda adicional, no dude en escalar su caso a un asesor humano.

Atentamente,
EcoMarket
```

### Verificacion de grounding
Sin hallazgos: todos los identificadores citados existen en el contexto.

---

## C. Analisis

**Qué hizo el prompt básico, y aquí aparece un fallo nuevo.** Respondió *"Claro, aquí tienes un ejemplo
de cómo puedes instruir al cliente para que devuelva el pedido"*. **Rompió el rol**: le habló al operador
en lugar de al cliente. Después inventó un procedimiento genérico de comercio electrónico —rotular el
paquete con la palabra DEVOLUCIÓN, usar papel burbuja— que no tiene relación con la política de EcoMarket.

Este fallo de rol no estaba previsto al diseñar el escenario y es un buen argumento a favor del encuadre:
sin un rol asignado, el modelo elige uno y puede elegir mal.

**Qué corrigió el mejorado.** Identificó la categoría `DURADERO`, verificó las condiciones de la política
—sin uso, con empaque original—, confirmó la elegibilidad y dio el plazo correcto de 5 a 10 días hábiles
para el reembolso.

**Qué elemento del prompt produjo la mejora.** El system prompt fijó el rol, y el Paso 4 del procedimiento
de decisión obligó a consultar la categoría de cada ítem en `<datos>` antes de responder.

**Defecto detectado.** Escribió "envíe los paños a la dirección que nos proporcionará Servientrega". La
política no dice quién recoge una devolución. El modelo tomó la transportadora del envío original, que
estaba en el contexto, y la trasladó a un procedimiento distinto. Es contaminación de contexto: un dato
correcto usado en el lugar equivocado.
