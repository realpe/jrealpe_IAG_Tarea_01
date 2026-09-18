# Escenario: devolucion_duradero

- **Modelo**: `qwen2.5:7b` (temperatura 0.2)
- **Version de prompts**: `v2`
- **Ejecutado**: 2026-09-18 11:02:00
- **Objetivo de la prueba**: Caso elegible dentro de plazo: debe dar los pasos concretos.
- **Pedido**: 12352
- **Consulta del cliente**: Los panos de cocina no eran lo que esperaba, quiero devolverlos. Estan sin usar y con su empaque original.

---

## A. Prompt basico (sin encuadre ni datos)

### Prompt enviado
```
Un cliente quiere devolver el pedido 12352. Dile como hacerlo.
```

### Respuesta (10.4 s)
```
Claro, aquí tienes un ejemplo de cómo puedes informar al cliente sobre el proceso de devolución del pedido 12352:

---

Estimado cliente,

Gracias por contactarnos para realizar la devolución del pedido 12352. Estamos aquí para ayudarte y asegurarnos de que todo salga bien. Aquí te proporcionamos los pasos que debes seguir:

1. **Verifica el estado del pedido**: Antes de proceder, asegúrate de que el pedido 12352 ya haya sido recibido por nosotros. Puedes hacerlo revisando tu cuenta de cliente o enviándonos un correo electrónico a [dirección de correo electrónico del servicio al cliente].

2. **Prepara el paquete para la devolución**:
   - **Etiquetar el paquete**: Escribe "DEVOLUCIÓN" en la parte superior del paquete y asegúrate de incluir el número de pedido 12352 en la etiqueta.
   - **Empaquetar correctamente**: Protege bien el producto para evitar daños durante el transporte. Si es necesario, envuelve el producto en papel de burbuja o caja de cartón.

3. **Envía el paquete**:
   - **Método de envío**: Podemos aceptar devoluciones por correo ordinario o por servicio de mensajería. Recomendamos el servicio de mensajería para un seguimiento más rápido.
   - **Dirección de devolución**: [Proporcionar la dirección de devolución, si es necesario, o indicar que el paquete se enviará a la dirección de envío original].

4. **Notifica al servicio al cliente**:
   - **Correo electrónico**: Envía un correo electrónico a [dirección de correo electrónico del servicio al cliente] con los detalles de tu devolución, incluyendo el número de pedido 12352 y el número de seguimiento del paquete si lo tienes.
   - **Número de seguimiento**: Si usas un servicio de mensajería, proporciona el número de seguimiento para que podamos rastrear tu paquete.

5. **Reembolso**: Una vez que recibamos el paquete y lo verifiquemos, procederemos con el reembolso. El tiempo de procesamiento puede variar, pero normalmente se realiza en 5-7 días hábiles.

Si tienes alguna pregunta o necesitas ayuda adicional, no dudes en contactarnos. Estamos aquí para asistirte.

Atentamente,
[Nombre del representante del servicio al cliente]
[Nombre de la empresa]

---

Espero que esta información sea útil para el cliente. Si necesitas más detalles o ajustes, no dudes en decírmelo.
```

### Verificacion de grounding
- ALERTA: La respuesta usa markdown (negritas o enlaces) en un canal de texto plano

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

### Respuesta (5.6 s)
```
Estimado Ricardo Alberto Nieto,

Entiendo que los paños reutilizables de cocina no cumplieron con tus expectativas. Según nuestra política de devoluciones, los productos de la categoría DURADERO, como los que compraste, sí pueden ser devueltos siempre que estén sin uso y con su empaque original.

Para proceder con la devolución, por favor sigue estos pasos:

1. Envíanos un correo electrónico a soporte@ecomarket.co con la referencia de tu pedido (12352) y una foto del producto.
2. Recibirás un cupón de devolución para que puedas enviar el producto.
3. Envía el producto a la dirección que te proporcionaremos y asegúrate de que el seguimiento esté registrado.
4. Una vez recibido, te haremos el reembolso en 5-10 días hábiles.

Si tienes alguna duda o necesitas más ayuda, no dudes en escalar a un asesor humano.

Atentamente,
EcoMarket
```

### Verificacion de grounding
- ALERTA: Salida comercial no contemplada en las politicas: 'cupon'
- ALERTA: Salida comercial no contemplada en las politicas: 'cupón'
- ALERTA: Codigo interno visible para el cliente: DURADERO

---

## C. Analisis

Estas dos corridas se analizan de forma **comparativa** en
[`../../ANALISIS.md`](../../ANALISIS.md), sección 8: el mismo conjunto de escenarios ejecutado con los
prompts `v2` sobre los dos modelos, para separar el efecto de los prompts del efecto del modelo.

El análisis escenario por escenario está en la corrida
[`iter1_qwen2.5-7b/`](../iter1_qwen2.5-7b/), que es la línea base contra la que se comparan estas dos.
