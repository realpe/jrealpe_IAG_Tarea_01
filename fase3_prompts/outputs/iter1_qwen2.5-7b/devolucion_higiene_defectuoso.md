# Escenario: devolucion_higiene_defectuoso

- **Modelo**: `qwen2.5:7b` (temperatura 0.2)
- **Ejecutado**: 2026-09-18 10:32:56
- **Objetivo de la prueba**: Caso dificil: categoria restringida PERO producto danado -> aplica la excepcion.
- **Pedido**: 12347
- **Consulta del cliente**: Los cepillos me llegaron con el empaque roto y uno partido. Quiero devolverlos.

---

## A. Prompt basico (sin encuadre ni datos)

### Prompt enviado
```
Un cliente quiere devolver el pedido 12347. Dile como hacerlo.
```

### Respuesta (7.7 s)
```
Para devolver el pedido 12347, puedes seguir estos pasos:

1. **Verifica la Política de Devoluciones**: Antes de proceder, revisa la política de devoluciones del vendedor o la plataforma en la que realizaste la compra. Esto te ayudará a entender los plazos, los costos y los requisitos específicos.

2. **Contacta al Servicio al Cliente**: Puedes llamar al número de atención al cliente proporcionado en la confirmación de compra o en el sitio web del vendedor. También puedes enviar un correo electrónico o usar el chat en línea si está disponible.

3. **Explica la Situación**: Cuando contactes al servicio al cliente, explica que deseas devolver el pedido 12347. Proporciona detalles como la razón de la devolución y cualquier problema que hayas tenido con el producto.

4. **Recibe las Instrucciones**: El servicio al cliente te proporcionará instrucciones sobre cómo proceder con la devolución. Esto podría incluir:
   - El envío del producto a una dirección específica.
   - La obtención de un número de seguimiento para el paquete de devolución.
   - El reembolso del costo del envío, si es necesario.

5. **Envía el Producto**: Envía el producto de vuelta siguiendo las instrucciones proporcionadas. Asegúrate de que el producto esté en perfectas condiciones y que incluyas cualquier documentación adicional que se te solicite.

6. **Confirma la Devolución**: Una vez que hayas enviado el producto, confirma con el servicio al cliente que la devolución ha sido recibida y que el proceso de reembolso está en curso.

7. **Revisa el Reembolso**: Finalmente, verifica que el reembolso se haya realizado en tu cuenta bancaria o tarjeta de crédito según lo acordado.

Si tienes alguna pregunta o necesitas más ayuda, no dudes en preguntar. ¡Espero que esta información te sea útil!
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
  "id_pedido": "12347",
  "cliente": "Maria Fernanda Ospina",
  "fecha_compra": "2026-09-05",
  "estado": "ENTREGADO",
  "transportadora": "Servientrega",
  "numero_guia": "SE-884219903",
  "url_rastreo": "https://ecomarket.co/rastreo/SE-884219903",
  "fecha_estimada_entrega": "2026-09-08",
  "fecha_entrega_real": "2026-09-08",
  "retrasado": false,
  "items": [
    {
      "sku": "ECO-CEP-BAM",
      "nombre": "Cepillo dental de bambu x4",
      "categoria": "HIGIENE_PERSONAL",
      "cantidad": 2,
      "precio_unitario": 24000
    }
  ],
  "total": 48000
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

<consulta_cliente id_pedido="12347">
Los cepillos me llegaron con el empaque roto y uno partido. Quiero devolverlos.
</consulta_cliente>

## Procedimiento de decision (siguelo en este orden)
Paso 1 — Localiza el pedido 12347 en <datos>. Si no existe, dilo y detente.

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
Estimada María Fernanda,

Lamentamos que los cepillos llegaran dañados. Entiendo que uno de ellos llegó con el empaque roto y otro se partió. Según nuestra política de devoluciones, cuando un producto llega dañado, incompleto o defectuoso, procede la devolución para cualquier categoría, incluidos productos de higiene personal.

Para proceder, por favor envíe una foto del daño y un detalle del producto afectado. Una vez recibida la evidencia, le haremos la reposición o reembolso total en un plazo de 5 a 10 días hábiles.

Si tiene alguna duda o necesita asesoría adicional, no dude en escalar su caso a un asesor humano.

Atentamente,
EcoMarket
```

### Verificacion de grounding
Sin hallazgos: todos los identificadores citados existen en el contexto.

---

## C. Analisis

**El caso difícil del conjunto.** Un producto de categoría `HIGIENE_PERSONAL`, que la política restringe,
pero que llegó dañado, lo cual activa la excepción de la sección 1.3. Requiere resolver una jerarquía:
la excepción por defecto prevalece sobre la restricción por categoría.

**Qué hizo el prompt básico.** El procedimiento genérico de siempre, sin distinguir categorías ni detectar
que había un producto dañado de por medio.

**Qué corrigió el mejorado.** Reconoció el daño, aplicó la excepción de forma explícita —"cuando un
producto llega dañado procede la devolución para cualquier categoría, incluidos productos de higiene
personal"—, pidió evidencia fotográfica y ofreció reposición o reembolso total.

**Qué elemento del prompt produjo la mejora.** El **orden** del procedimiento de decisión. El Paso 2
pregunta por producto dañado y, si la respuesta es sí, salta directamente al Paso 5, sin pasar por la
verificación de categoría del Paso 4. La jerarquía de reglas quedó codificada en el orden de los pasos en
lugar de dejarse al criterio del modelo.

Es el mejor resultado de la iteración: un modelo de 7B resolvió correctamente una excepción que colisiona
con una regla general, porque el prompt le dio el camino en el orden correcto.

**Defecto detectado.** Omitió el plazo de 72 horas que la sección 1.3 exige para reportar el daño. El dato
estaba en el contexto y no llegó a la respuesta. Es una omisión, más leve que una fabricación, y aun así
deja al cliente sin una condición que después puede invocarse en su contra.
