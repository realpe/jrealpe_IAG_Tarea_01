# Escenario: devolucion_duradero

- **Modelo**: `qwen3:14b` (temperatura 0.2)
- **Version de prompts**: `v2`
- **Ejecutado**: 2026-09-18 11:05:53
- **Objetivo de la prueba**: Caso elegible dentro de plazo: debe dar los pasos concretos.
- **Pedido**: 12352
- **Consulta del cliente**: Los panos de cocina no eran lo que esperaba, quiero devolverlos. Estan sin usar y con su empaque original.

---

## A. Prompt basico (sin encuadre ni datos)

### Prompt enviado
```
Un cliente quiere devolver el pedido 12352. Dile como hacerlo.
```

### Respuesta (23.1 s)
```
Para devolver el pedido 12352, sigue estos pasos:  

1. **Contacta al servicio al cliente**:  
   - Llama al número de atención al cliente o envía un mensaje a través del chat en línea (si está disponible en el sitio web o app del proveedor).  
   - Proporciona el **número de pedido (12352)** y explica la razón de la devolución (ej.: producto defectuoso, error en el envío, cambio de talla, etc.).  

2. **Verifica la política de devoluciones**:  
   - Pregunta si el producto está dentro del plazo de devolución (ej.: 30 días desde la fecha de entrega).  
   - Confirma si se requiere el **embalaje original** o si se acepta el producto en buen estado.  

3. **Sigue las instrucciones para el envío**:  
   - Si es necesario, el proveedor te enviará un **etiqueta de devolución prepagada** (en algunos casos).  
   - Empaca el producto cuidadosamente y envíalo al domicilio indicado por el proveedor.  

4. **Guarda el comprobante de envío**:  
   - Mantén el número de seguimiento del paquete para verificar que se recibió correctamente.  

5. **Espera la confirmación**:  
   - Una vez procesada la devolución, el proveedor te notificará por correo electrónico o mensaje (según su política) sobre el reembolso o cambio.  

**Nota**: Si no tienes acceso al servicio al cliente, revisa la sección "Devoluciones" en el sitio web del proveedor, donde podrás encontrar instrucciones detalladas.  

¿Necesitas ayuda para encontrar el contacto del proveedor?
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

### Respuesta (17.3 s)
```
Entendemos que los paños reutilizables no cumplieron sus expectativas. Según nuestra política, los productos de categoría **DURADERO** sí admiten devolución si están sin uso, con empaque original y etiquetas.  

Para proceder:  
1. Contacte a nuestro equipo de atención al cliente en [atencion@ecomarket.co](atencion@ecomarket.co) o al teléfono 310 123 4567.  
2. Indique su número de pedido **12352** y adjunte fotos del empaque original.  
3. El reembolso se procesará en **5–10 días hábiles** al medio de pago original.  

Si prefiere, puede escalar su caso a un asesor humano para alternativas adicionales. Estamos aquí para ayudarle.
```

### Verificacion de grounding
- ALERTA: Codigo interno visible para el cliente: DURADERO
- ALERTA: La respuesta usa markdown (negritas o enlaces) en un canal de texto plano

---

## C. Analisis

Estas dos corridas se analizan de forma **comparativa** en
[`../../ANALISIS.md`](../../ANALISIS.md), sección 8: el mismo conjunto de escenarios ejecutado con los
prompts `v2` sobre los dos modelos, para separar el efecto de los prompts del efecto del modelo.

El análisis escenario por escenario está en la corrida
[`iter1_qwen2.5-7b/`](../iter1_qwen2.5-7b/), que es la línea base contra la que se comparan estas dos.
