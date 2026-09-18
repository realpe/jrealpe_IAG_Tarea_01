# Escenario: devolucion_higiene_defectuoso

- **Modelo**: `qwen2.5:7b` (temperatura 0.2)
- **Version de prompts**: `v2`
- **Ejecutado**: 2026-09-18 11:02:26
- **Objetivo de la prueba**: Caso dificil: categoria restringida PERO producto danado -> aplica la excepcion.
- **Pedido**: 12347
- **Consulta del cliente**: Los cepillos me llegaron con el empaque roto y uno partido. Quiero devolverlos.

---

## A. Prompt basico (sin encuadre ni datos)

### Prompt enviado
```
Un cliente quiere devolver el pedido 12347. Dile como hacerlo.
```

### Respuesta (10.2 s)
```
Claro, aquí tienes un ejemplo de cómo puedes instruir al cliente para que devuelva el pedido 12347:

---

Estimado cliente,

Gracias por contactarnos para realizar la devolución del pedido 12347. Le agradecemos su confianza en nuestro servicio.

Para proceder con la devolución, por favor siga estos pasos:

1. **Preparación del Producto:**
   - Verifique que el producto esté en perfectas condiciones.
   - Retire cualquier embalaje original y asegúrese de que el producto esté limpio y sin signos de uso.
   - Retire cualquier etiqueta de seguimiento o etiquetas de envío que puedan estar en el producto.

2. **Preparación del Envío:**
   - Si aún no lo ha hecho, por favor rellene el formulario de devolución en nuestro sitio web o envíe un correo electrónico a nuestro servicio al cliente para solicitar un número de seguimiento de devolución.
   - Si ya ha recibido el número de seguimiento, utilícelo para preparar su envío.

3. **Empaquetado del Producto:**
   - Empaque el producto con cuidado en su embalaje original o en un nuevo embalaje adecuado.
   - Asegúrese de que el producto esté bien protegido para evitar daños durante el transporte.

4. **Etiquetado del Envío:**
   - Añada claramente el número de seguimiento de devolución en la etiqueta del paquete.
   - Incluya una copia del recibo de compra o del formulario de devolución con el paquete.

5. **Envío del Producto:**
   - Envíe el paquete a la dirección que se le proporcionó en el formulario de devolución o en el correo electrónico que recibió.
   - Asegúrese de que el envío sea con un servicio que le proporcionará un seguimiento.

6. **Notificación de Envío:**
   - Una vez que haya enviado el paquete, envíenos un correo electrónico con la información del seguimiento para que podamos actualizar su estado.

Una vez recibamos el producto, revisaremos su estado y procederemos con el reembolso en el plazo estipulado en nuestras políticas de devolución.

Si tiene alguna pregunta o necesita ayuda adicional, no dude en contactarnos. Estamos aquí para ayudarle.

Atentamente,
[Nombre de la Empresa]
[Correo Electrónico de Soporte al Cliente]
[Teléfono de Soporte al Cliente]

---

Espero que esta guía sea útil. Si necesitas más detalles o ajustes, no dudes en decírmelo.
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

### Respuesta (4.7 s)
```
Estimada María Fernanda,

Lamentamos que los cepillos llegaran dañados. Según nuestra política, cuando un producto llega dañado, incompleto o defectuoso, procede la devolución para cualquier categoría, incluidos los de higiene personal, siempre que se reporte dentro de las 72 horas siguientes a la entrega.

Para proceder, por favor envíe una foto del daño y siga estos pasos:
1. Envíe el producto a la dirección que encontrará en el correo de confirmación de devolución.
2. Una vez recibido, le enviaremos el reembolso al medio de pago original en 5-10 días hábiles.

Si tiene alguna duda, no dude en escalar su caso a un asesor humano.

Atentamente,
Equipo de EcoMarket
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
