# Escenario: devolucion_fuera_de_plazo

- **Modelo**: `qwen2.5:7b` (temperatura 0.2)
- **Ejecutado**: 2026-09-18 10:33:06
- **Objetivo de la prueba**: Entregado hace mas de 30 dias: debe escalar a humano, no decidir solo.
- **Pedido**: 12355
- **Consulta del cliente**: Compre una botella hace unos meses y ya no la quiero, puedo devolverla?

---

## A. Prompt basico (sin encuadre ni datos)

### Prompt enviado
```
Un cliente quiere devolver el pedido 12355. Dile como hacerlo.
```

### Respuesta (5.6 s)
```
Claro, aquí tienes un ejemplo de cómo puedes comunicarte con el cliente para ayudarlo a devolver el pedido 12355:

---

Estimado cliente,

Gracias por contactarnos. Lamento que no estés satisfecho con tu pedido 12355. Estamos aquí para ayudarte a resolver cualquier problema que puedas tener.

Para poder proceder con la devolución, necesitamos que nos proporciones algunos detalles:

1. **Número de pedido**: 12355
2. **Producto(s) a devolver**: Por favor, indica los productos que deseas devolver.
3. **Motivo de la devolución**: ¿Es por mala calidad, error en el pedido, o por cualquier otro motivo?
4. **Dirección de envío**: Si cambió, proporciona la nueva dirección de envío para la devolución.

Una vez que nos proporciones esta información, podremos darte instrucciones detalladas sobre cómo proceder con la devolución. También te informaremos sobre el estado de tu devolución y cuándo podrás esperar recibir un reembolso.

Si tienes alguna pregunta o necesitas ayuda adicional, no dudes en contactarnos. Estamos aquí para asistirte.

Atentamente,
[Tu nombre]
[Nombre de la empresa]

---

Este mensaje es amable, claro y proporciona todas las instrucciones necesarias para que el cliente pueda proceder con la devolución de manera eficiente.
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

### Respuesta (4.8 s)
```
Estimada Paula Andrea Bermudez,

Gracias por su mensaje. Le informamos que su pedido con el número de pedido 12355 fue entregado el 18 de junio de 2026. Según nuestra política de devoluciones, el plazo para solicitar una devolución es de 30 días calendario contados desde la fecha de entrega efectiva, es decir, hasta el 17 de julio de 2026.

Como la fecha actual es 18 de septiembre de 2026, su solicitud se encuentra fuera del plazo establecido. En este caso, la solicitud requiere aprobación de un asesor humano.

Le sugerimos que contacte a uno de nuestros asesores para discutir su situación. Estarán encantados de ayudarle con su solicitud.

Atentamente,
EcoMarket
```

### Verificacion de grounding
Sin hallazgos: todos los identificadores citados existen en el contexto.

---

## C. Analisis

**Qué hizo el prompt básico.** Rompió el rol otra vez —"aquí tienes un ejemplo de cómo puedes comunicarte
con el cliente"— y pidió datos que ya estaban disponibles, incluido el número de pedido que la propia
consulta traía.

**Qué corrigió el mejorado.** Hizo la aritmética completa: tomó la fecha de entrega (18 de junio de 2026),
sumó los 30 días calendario de la política, concluyó que el plazo venció el 17 de julio, lo comparó con la
fecha de hoy y determinó que la solicitud está fuera de término. Entonces **escaló a un asesor humano en
lugar de decidir por su cuenta**.

**Qué elemento del prompt produjo la mejora.** El marcador `{{fecha_hoy}}`, que inyecta la fecha del
sistema en tiempo de ejecución, junto con el Paso 3 que ordena contar los días y detenerse si el plazo
está vencido.

Sin `{{fecha_hoy}}` el modelo habría tenido que adivinar la fecha actual, que es un dato que no posee. Es
otra instancia del mismo principio: el dato volátil se inyecta, nunca se le pide al modelo que lo sepa.

**Lo más valioso del caso.** La política define este supuesto como uno que "requiere aprobación
discrecional". El modelo reconoció el límite de su autoridad y derivó. Es el comportamiento que la Fase 1
describe como frontera entre capacidad y autoridad, funcionando en la práctica.

**Observación menor.** La aritmética de fechas salió correcta en esta ejecución. En un modelo de 7B ese
cálculo no está garantizado, así que en producción convendría precalcularlo en el código y entregarlo ya
resuelto en el contexto, en lugar de confiar en que el modelo lo haga bien cada vez.
