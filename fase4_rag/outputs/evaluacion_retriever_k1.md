# Fase 4 — Evaluación del recuperador

**Ejecutado**: 2026-09-18 11:40 · `nomic-embed-text` · k = 1 · 8 preguntas

Compara dos estrategias de fragmentación sobre el mismo corpus. Se mide **recall@k**: de las preguntas del conjunto oro, en cuántas el contenido necesario para responder aparece dentro de los k fragmentos recuperados.

Se evalúa el recuperador por separado porque un fragmento que no se recupera no lo puede compensar ningún prompt.

## Estrategia `seccion`

**recall@1 = 4/8** · casos críticos 1/3

| Pregunta | Resultado | Falta en el contexto |
| :--- | :---: | :--- |
| Compre un mix de frutos secos y llego con el empaque roto. Puedo devolverlo? | OK | — |
| Cuantos dias tengo para pedir una devolucion? | OK | — |
| Puedo devolver un shampoo solido que ya abri? | **FALLA** | `HIGIENE_PERSONAL`; `sin abrir` |
| Mi pedido esta retrasado, que opciones tengo? | OK | — |
| Desde cuanto hay envio gratis? | OK | — |
| El producto me causo una reaccion alergica, que hago? | **FALLA** 🔴 | `daño a la salud`; `escalarse a un agente humano` |
| Cuanto se demora el reembolso? | **FALLA** | `5–10 días hábiles` |
| Me pueden dar un descuento por la demora? | **FALLA** 🔴 | `Prohibido`; `compensaciones` |

## Estrategia `fija`

**recall@1 = 3/8** · casos críticos 0/3

| Pregunta | Resultado | Falta en el contexto |
| :--- | :---: | :--- |
| Compre un mix de frutos secos y llego con el empaque roto. Puedo devolverlo? | **FALLA** 🔴 | `cuando el producto llegó dañado, incompleto o defectuoso` |
| Cuantos dias tengo para pedir una devolucion? | OK | — |
| Puedo devolver un shampoo solido que ya abri? | OK | — |
| Mi pedido esta retrasado, que opciones tengo? | **FALLA** | `Manejo de retrasos` |
| Desde cuanto hay envio gratis? | OK | — |
| El producto me causo una reaccion alergica, que hago? | **FALLA** 🔴 | `daño a la salud`; `escalarse a un agente humano` |
| Cuanto se demora el reembolso? | **FALLA** | `5–10 días hábiles` |
| Me pueden dar un descuento por la demora? | **FALLA** 🔴 | `Prohibido`; `compensaciones` |

## Resumen

| Estrategia | recall@1 | Casos críticos |
| :--- | :---: | :---: |
| `seccion` | 4/8 | 1/3 |
| `fija` | 3/8 | 0/3 |

Los **casos críticos** son aquellos en los que un fallo de recuperación produce una respuesta incorrecta con consecuencia real: negar una devolución que procede, atender automáticamente un caso de salud, u ofrecer una compensación no autorizada.
