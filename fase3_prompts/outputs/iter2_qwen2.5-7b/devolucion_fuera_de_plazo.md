# Escenario: devolucion_fuera_de_plazo

- **Modelo**: `qwen2.5:7b` (temperatura 0.2)
- **Version de prompts**: `v2`
- **Ejecutado**: 2026-09-18 11:02:37
- **Objetivo de la prueba**: Entregado hace mas de 30 dias: debe escalar a humano, no decidir solo.
- **Pedido**: 12355
- **Consulta del cliente**: Compre una botella hace unos meses y ya no la quiero, puedo devolverla?

---

## A. Prompt basico (sin encuadre ni datos)

### Prompt enviado
```
Un cliente quiere devolver el pedido 12355. Dile como hacerlo.
```

### Respuesta (5.4 s)
```
Claro, puedo ayudarte a guiar al cliente en el proceso de devolución. Aquí tienes un ejemplo de cómo podrías comunicarte con el cliente:

---

¡Hola! Esperamos que estés teniendo un buen día.

Nos complace que quieras devolver el pedido 12355. Para poder proceder con la devolución, necesitamos que nos proporciones algunos detalles:

1. **Número de pedido**: Ya lo has proporcionado (12355), pero es importante confirmarlo.
2. **Motivo de la devolución**: ¿Es por un problema de calidad, error en el pedido, o por cualquier otro motivo?
3. **Estado del producto**: ¿El producto está en buen estado y no ha sido usado? Si es necesario, envíanos una foto del producto.
4. **Dirección de envío**: Para poder enviar el nuevo envío, necesitamos tu dirección actualizada.

Una vez que nos proporciones esta información, podremos proceder con la devolución y asegurarnos de que todo se haga de la manera más rápida y eficiente posible.

Si tienes alguna pregunta o necesitas ayuda adicional, no dudes en contactarnos. Estamos aquí para ayudarte.

¡Gracias por tu comprensión!

Atentamente,
[Tu nombre o departamento]

---

Espero que esta guía sea útil. Si necesitas más detalles o cambios, házmelo saber.
```

### Verificacion de grounding
- ALERTA: Posible condicion de politica fabricada: 'usado' no aparece en el contexto
- ALERTA: La respuesta usa markdown (negritas o enlaces) en un canal de texto plano

---

## B. Prompt mejorado (rol + datos + politicas + reglas + formato)

### Prompt enviado
```
Actua como agente de servicio al cliente de EcoMarket y atiende una solicitud de devolucion.

<datos>
{
  "id_pedido": "12355",
  "cliente": "Paula Andrea Bermudez",
  "fecha_compra": "2026-06-15",
  "estado": "ENTREGADO",
  "transportadora": "Servientrega",
  "numero_guia": "SE-883990012",
  "url_rastreo": "https://ecomarket.co/rastreo/SE-883990012",
  "fecha_estimada_entrega": "2026-06-19",
  "fecha_entrega_real": "2026-06-18",
  "retrasado": false,
  "items": [
    {
      "sku": "ECO-BOT-750",
      "nombre": "Botella termica de acero 750ml",
      "categoria": "DURADERO",
      "cantidad": 1,
      "precio_unitario": 105000
    }
  ],
  "total": 105000
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

<consulta_cliente id_pedido="12355">
Compre una botella hace unos meses y ya no la quiero, puedo devolverla?
</consulta_cliente>

## Procedimiento de decision (siguelo en este orden)
Paso 1 — Localiza el pedido 12355 en <datos>. Si no existe, dilo y detente.

Paso 2 — ¿El cliente reporta un producto danado, defectuoso o incompleto?
   - SI  -> aplica la excepcion por producto defectuoso de <politicas>. En ese caso la devolucion procede
            para CUALQUIER categoria, incluidos PERECEDERO e HIGIENE_PERSONAL. Menciona el plazo de
            reporte y el requisito de evidencia tal como los define <politicas>. Ve al Paso 5.
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
- No inventes plazos, montos ni condiciones que no esten en <politicas>. En particular, si la politica
  niega la devolucion de una categoria sin condicionarla al estado del empaque, NO agregues que depende
  de si el producto fue abierto: enuncia la regla tal cual esta escrita.
- No ofrezcas intercambios, canjes, bonos ni reenvios: <politicas> no los contempla. Si el cliente
  necesita una salida distinta, ofrece escalar a un asesor humano.
- No afirmes quien recoge el producto ni por que transportadora, salvo que <politicas> lo indique.
- TEXTO PLANO: sin asteriscos, negritas ni enlaces con corchetes.
- Maximo 180 palabras.
```

### Respuesta (5.0 s)
```
Estimada Paula Andrea Bermudez,

Gracias por su consulta. Comprende que la botella termica que compró el 15 de junio de 2026 se encuentra fuera del plazo de 30 días para devoluciones, que vence el 18 de septiembre de 2026. Según nuestra política, las devoluciones solo se aceptan dentro de este período.

Si la botella no ha sido usada y mantiene su empaque original, podríamos considerar su caso, pero debido a que ya ha pasado el plazo, necesitamos que un asesor humano revise su situación. Le sugerimos que nos contacte para que podamos revisar su caso y brindarle la mejor asesoría posible.

Si tiene alguna duda adicional, no dude en comunicarse con nosotros. ¡Gracias por su comprensión!

Atentamente,
EcoMarket
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
