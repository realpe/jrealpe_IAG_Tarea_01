# Escenario: devolucion_higiene_defectuoso

- **Modelo**: `mistral-small:24b` (temperatura 0.2)
- **Version de prompts**: `v2`
- **Ejecutado**: 2026-09-18 12:51:13
- **Objetivo de la prueba**: Caso dificil: categoria restringida PERO producto danado -> aplica la excepcion.
- **Pedido**: 12347
- **Consulta del cliente**: Los cepillos me llegaron con el empaque roto y uno partido. Quiero devolverlos.

---

## A. Prompt basico (sin encuadre ni datos)

### Prompt enviado
```
Un cliente quiere devolver el pedido 12347. Dile como hacerlo.
```

### Respuesta (19.0 s)
```
Para devolver el pedido 12347, el cliente puede seguir estos pasos:

1. **Contactar al Servicio de Atención al Cliente**: El cliente debe comunicarse con el servicio de atención al cliente a través del número de teléfono proporcionado en la confirmación del pedido o en la página web de la empresa. Es importante tener a mano el número de pedido (12347) y cualquier otra información relevante.

2. **Enviar un Correo Electrónico**: Si prefiere, el cliente puede enviar un correo electrónico a la dirección de soporte indicada en la página web de la empresa. En el correo, debe incluir el número de pedido (12347) y una breve explicación del motivo de la devolución.

3. **Acceder a la Cuenta en Línea**: Si el cliente tiene una cuenta en línea, puede iniciar sesión y buscar la opción de "Devoluciones" o "Rastreo de Pedidos". Desde allí, puede iniciar el proceso de devolución siguiendo las instrucciones proporcionadas en la plataforma.

4. **Seguir las Instrucciones de Devolución**: Una vez que el cliente haya iniciado el proceso de devolución, recibirá instrucciones específicas sobre cómo empaquetar y enviar el producto. Es importante seguir estas instrucciones para asegurar que la devolución se procese correctamente.

5. **Enviar el Producto**: El cliente debe enviar el producto a la dirección indicada por la empresa. Asegúrese de incluir cualquier documentación requerida, como el formulario de devolución o la confirmación de devolución.

Si tienes más detalles específicos sobre la política de devoluciones de la empresa o cualquier otra información relevante, por favor házmelo saber para poder proporcionar una guía más precisa.
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

### Respuesta (17.0 s)
```
Hola Maria Fernanda, lamento mucho que los cepillos dentales de bambú hayan llegado en mal estado. Entiendo que el empaque estaba roto y uno de los productos partido. En este caso, la política de devoluciones de EcoMarket permite la devolución de productos defectuosos o dañados en transporte, independientemente de la categoría del producto.

Para proceder con la devolución, debe reportar el incidente dentro de las 72 horas siguientes a la entrega y adjuntar evidencia fotográfica del daño. Aquí están los pasos a seguir:

1. Tome fotos claras del empaque roto y del producto partido.
2. Envíe las fotos a nuestro equipo de atención al cliente a través del canal de comunicación que prefiera.
3. Nuestro equipo revisará la evidencia y le indicará cómo proceder con la devolución.

El costo del transporte de retorno lo asumiremos nosotros. Una vez recibamos el producto, se le repondrá o reembolsará el monto total en 5-10 días hábiles al medio de pago original.

Si necesita ayuda adicional o tiene alguna otra consulta, no dude en contactarnos. Estamos aquí para ayudarle.
```

### Verificacion de grounding
Sin hallazgos: todos los identificadores citados existen en el contexto.

---

## C. Analisis

Esta corrida se analiza en [`../../ANALISIS.md`](../../ANALISIS.md), sección 8.6: es la prueba de
control con un modelo mayor, y el caso `devolucion_fuera_de_plazo` contiene el fallo de negocio más
grave documentado en el trabajo.
