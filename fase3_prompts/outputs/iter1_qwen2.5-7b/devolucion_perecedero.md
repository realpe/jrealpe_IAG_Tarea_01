# Escenario: devolucion_perecedero

- **Modelo**: `qwen2.5:7b` (temperatura 0.2)
- **Ejecutado**: 2026-09-18 10:32:43
- **Objetivo de la prueba**: NO procede por categoria. Debe negar con explicacion sanitaria y tono empatico.
- **Pedido**: 12357
- **Consulta del cliente**: Los frutos secos no me gustaron, quiero que me devuelvan la plata.

---

## A. Prompt basico (sin encuadre ni datos)

### Prompt enviado
```
Un cliente quiere devolver el pedido 12357. Dile como hacerlo.
```

### Respuesta (7.6 s)
```
Para devolver el pedido 12357, puedes seguir estos pasos:

1. **Verifica la Política de Devoluciones**: Primero, revisa la política de devoluciones de la empresa que realizó el envío. Esta información generalmente se encuentra en el sitio web de la empresa o en el correo electrónico que recibiste con la confirmación del pedido.

2. **Contáctate con el Servicio al Cliente**: Puedes llamar al número de atención al cliente proporcionado en el correo electrónico o en el sitio web. También puedes enviar un correo electrónico a su servicio de soporte.

3. **Información Necesaria**: Cuando contactes a la empresa, ten a mano la siguiente información:
   - Número de pedido: 12357
   - Fecha de entrega
   - Detalles del producto que deseas devolver
   - Razón de la devolución

4. **Rellenar el Formulario de Devolución**: La empresa probablemente te proporcionará un formulario de devolución que necesitarás completar. Este formulario puede estar disponible en línea o puede que te lo envíen por correo electrónico.

5. **Envío del Producto**: Una vez que hayas completado el formulario, recibirás instrucciones sobre cómo enviar el producto. Esto puede ser a través de un servicio de envío que la empresa te proporcionará o a través de un servicio de envío que elijas tú.

6. **Seguimiento del Envío**: Mantente en contacto con el servicio al cliente para seguir el estado de tu devolución. También puedes solicitar un número de seguimiento para rastrear el paquete.

7. **Reembolso**: Una vez que la empresa reciba el producto, revisará su estado y procederá al reembolso según sus políticas. Este proceso puede tardar entre 5 a 10 días hábiles.

Si tienes alguna pregunta o necesitas ayuda adicional, no dudes en preguntar. ¡Espero que la devolución sea lo más sencilla posible!
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
  "id_pedido": "12357",
  "cliente": "Oscar Mauricio Lopez",
  "fecha_compra": "2026-09-01",
  "estado": "ENTREGADO",
  "transportadora": "Interrapidisimo",
  "numero_guia": "IR-552998410",
  "url_rastreo": "https://ecomarket.co/rastreo/IR-552998410",
  "fecha_estimada_entrega": "2026-09-06",
  "fecha_entrega_real": "2026-09-06",
  "retrasado": false,
  "items": [
    {
      "sku": "ECO-FRU-MIX",
      "nombre": "Mix de frutos secos organicos 1kg",
      "categoria": "PERECEDERO",
      "cantidad": 1,
      "precio_unitario": 78000
    }
  ],
  "total": 78000
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

<consulta_cliente id_pedido="12357">
Los frutos secos no me gustaron, quiero que me devuelvan la plata.
</consulta_cliente>

## Procedimiento de decision (siguelo en este orden)
Paso 1 — Localiza el pedido 12357 en <datos>. Si no existe, dilo y detente.

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
Estimado señor Oscar Mauricio López,

Lamento que los frutos secos no hayan cumplido con sus expectativas. Según nuestra política de devoluciones, los productos perecederos como el mix de frutos secos no se pueden devolver una vez que han sido abiertos por cuestiones de seguridad alimentaria. 

Le sugerimos que pruebe el producto en caso de que aún no lo haya hecho. Si el sabor o la calidad no es lo que esperaba, le recomendamos que nos lo comunique a un asesor humano para explorar otras opciones como asesoramiento de uso o intercambio por otro producto.

Si tiene alguna otra consulta, no dude en contactarnos. Estamos aquí para ayudarlo.

Atentamente,
EcoMarket
```

### Verificacion de grounding
Sin hallazgos: todos los identificadores citados existen en el contexto.

---

## C. Analisis

**Qué hizo el prompt básico.** El mismo procedimiento genérico de devolución del escenario anterior, con
la misma ruptura de rol. Sin la categoría del producto en el contexto, **no tenía forma de saber que esta
devolución no procede**, así que le explicó al cliente cómo tramitar algo que la política prohíbe.

**Qué corrigió el mejorado.** Negó la devolución con la razón sanitaria y en tono empático, que es
exactamente lo que pedía el escenario: reconocer la situación del cliente antes de dar la respuesta
administrativa, en lugar de cerrar con una negativa seca.

**Qué elemento del prompt produjo la mejora.** El Paso 4 del procedimiento de decisión, que obliga a
verificar la categoría de cada ítem, sumado a la instrucción de redacción que pide explicar el porqué y
ofrecer una alternativa.

### El defecto más importante de toda la iteración

El modelo escribió que los perecederos no se devuelven **"una vez que han sido abiertos"**. La política
(sección 1.2) dice que los perecederos no admiten devolución, sin ninguna condición de apertura. **El
modelo agregó una condición que no existe.** También ofreció un "intercambio por otro producto" que la
política no contempla, y sugirió "pruebe el producto en caso de que aún no lo haya hecho", un consejo que
nadie le pidió.

Las tres cosas tienen consecuencias reales. Un cliente que lea esa respuesta puede concluir que si no
abrió el paquete sí puede devolverlo, y reclamar apoyándose en lo que el canal oficial de EcoMarket le
dijo.

**Por qué el guardarraíl no lo detectó.** `verificar_grounding()` valida números de guía y fechas contra
el contexto. Una condición de política inventada pasa invisible porque no contiene ningún identificador.
El validador funciona para lo que valida y es ciego a todo lo demás.

Este hallazgo refuerza el argumento de la Fase 2: la seguridad viene de capas, y esta capa tiene un
alcance definido que conviene declarar en lugar de suponerla completa.

**Nota sobre variabilidad.** En el escenario `prompt_injection`, con el mismo pedido y la misma política,
el modelo respondió "no se pueden devolver una vez entregados", que sí es correcto. La misma
configuración produjo una versión correcta y otra fabricada. Con temperatura 0.2 la variación persiste,
y esto justifica evaluar sobre un conjunto de casos en vez de sobre una sola ejecución.
