# Escenario: devolucion_fuera_de_plazo

- **Modelo**: `mistral-small:24b` (temperatura 0.2)
- **Version de prompts**: `v2`
- **Ejecutado**: 2026-09-18 12:51:52
- **Objetivo de la prueba**: Entregado hace mas de 30 dias: debe escalar a humano, no decidir solo.
- **Pedido**: 12355
- **Consulta del cliente**: Compre una botella hace unos meses y ya no la quiero, puedo devolverla?

---

## A. Prompt basico (sin encuadre ni datos)

### Prompt enviado
```
Un cliente quiere devolver el pedido 12355. Dile como hacerlo.
```

### Respuesta (19.6 s)
```
Para devolver el pedido 12355, el cliente debe seguir estos pasos:

1. **Contactar al Servicio de Atención al Cliente**: El cliente debe comunicarse con el servicio de atención al cliente a través del número de teléfono proporcionado en la confirmación del pedido o en la página web de la empresa. Es importante tener a mano el número de pedido (12355) y cualquier otra información relevante.

2. **Solicitar la Devolución**: Informar al representante del servicio de atención al cliente que desea devolver el pedido 12355. El representante le proporcionará las instrucciones específicas para la devolución.

3. **Empaquetar el Producto**: Seguir las instrucciones proporcionadas para empaquetar el producto de manera segura y adecuada. Asegúrese de incluir todos los accesorios y documentos que vinieron con el producto.

4. **Generar una Etiqueta de Devolución**: Si es necesario, el servicio de atención al cliente puede generar una etiqueta de devolución que el cliente debe imprimir y pegar en el paquete. Esta etiqueta generalmente cubre los costos de envío de la devolución.

5. **Enviar el Paquete**: Llevar el paquete a la oficina de correos o al centro de envíos indicado. Asegúrese de que el paquete esté correctamente etiquetado y listo para ser enviado.

6. **Confirmar la Devolución**: Una vez que el paquete haya sido enviado, el cliente debe confirmar la devolución con el servicio de atención al cliente, proporcionando el número de seguimiento del envío si es posible.

Si tienes alguna otra pregunta o necesitas más detalles, por favor házmelo saber.
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

### Respuesta (19.7 s)
```
Hola Paula Andrea, gracias por contactarnos. Entendemos que ya no desea la botella térmica de acero que compró el 15 de junio de 2026.

La fecha de entrega fue el 18 de junio de 2026, por lo que tiene hasta el 17 de julio de 2026 para solicitar la devolución. La botella térmica de acero 750ml es un producto duradero, por lo que puede devolverla sin uso, con empaque original y etiquetas. El reembolso se hará al medio de pago original en 5–10 días hábiles.

Para proceder con la devolución, por favor siga estos pasos:
1. Envíe un correo a soporte@ecomarket.co con el asunto "Devolución pedido 12355".
2. En el correo, indique que desea devolver la botella térmica de acero 750ml y adjunte una foto del producto en su empaque original.
3. Una vez que recibamos su solicitud, le enviaremos las instrucciones para el envío del producto.

Recuerde que el producto debe estar en las mismas condiciones en las que lo recibió, sin uso y con su empaque original. Si tiene alguna otra pregunta o necesita ayuda adicional, estamos aquí para ayudarla.
```

### Verificacion de grounding
Sin hallazgos: todos los identificadores citados existen en el contexto.

---

## C. Analisis

Esta corrida se analiza en [`../../ANALISIS.md`](../../ANALISIS.md), sección 8.6: es la prueba de
control con un modelo mayor, y el caso `devolucion_fuera_de_plazo` contiene el fallo de negocio más
grave documentado en el trabajo.
