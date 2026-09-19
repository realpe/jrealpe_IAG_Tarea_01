# Fase 5 — Clasificador de intención: el experimento que falló, y qué demuestra

**Caso**: EcoMarket — optimización de la atención al cliente
**Autor**: José Luis Realpe M.
**Curso**: Inteligencia Artificial Generativa — Maestría en IA Aplicada, Universidad Icesi

> La Fase 1 dibujó una caja llamada *clasificador de intención* y describió lo que debía hacer. Esta
> fase la implementa y la mide.
>
> **El resultado es negativo y está documentado como tal.** El clasificador no alcanza a sostener el
> carril automático, y la causa está cuantificada: el dataset público con el que se entrenó no
> representa el dominio en el que se mide. Un experimento negativo con la causa identificada dice más
> sobre el problema que un número de exactitud sin diagnóstico.

---

## 1. Qué se construyó

Dos capas en cascada, y el orden importa.

```
mensaje
  │
  ├─ CAPA 0  reglas léxicas deterministas        ── escala ──▶  humano_exclusivo
  │          salud · amenaza legal · monto · reincidencia
  │
  └─ CAPA 1  centroides de intención (embeddings) ──────────▶  automatico
             27 centroides · similitud coseno                  copiloto
             umbral por intención + margen                     derivacion
```

La capa 0 corre primero y decide sola. Un filtro léxico no alucina y se audita línea por línea, de
modo que la garantía del carril crítico se pone ahí y no en un modelo probabilístico. Es la misma
conclusión a la que llegó la Fase 4 por otro camino: una prohibición no se parece semánticamente a la
petición que debe bloquear, así que lo crítico no puede depender de la similitud.

La capa 1 solo ve lo que la capa 0 dejó pasar. Si se corrieran las dos en paralelo y se combinaran
después, la medición no correspondería a lo que el sistema hace en producción.

| Archivo | Qué hace |
| :--- | :--- |
| `capa0_reglas.py` | 27 raíces de salud, 14 legales, 8 de tensión; umbral de monto y reincidencia |
| `construir_mapeo.py` | Traduce las 27 intenciones del dataset a los carriles de EcoMarket |
| `capa1_semantica.py` | Construye los centroides y clasifica |
| `canales.py` | Lista blanca de canales oficiales: derivación y validación de salida |
| `sonda_confianza.py` | Pone a prueba si la confianza del clasificador mide algo |
| `brecha_dominio.py` | Compara la distribución de entrenamiento con la de los casos reales |
| `politica_v2.py` | Política de decisión corregida y comparación contra la primera |
| `evaluar_clasificador.py` | Matriz de confusión y métrica de enrutamiento inseguro |

---

## 2. Los datos, y de dónde salió cada cosa

El problema de fondo de esta fase es que **el taller plantea un caso hipotético y un clasificador
necesita ejemplos etiquetados reales**. La solución fue combinar tres fuentes, y conviene decir cuál
es cuál antes de presentar cualquier cifra.

| Fuente | Cantidad | Origen | Para qué |
| :--- | ---: | :--- | :--- |
| Bitext Customer Support (es) | 24.184 | Corpus público, licencia CDLA-Sharing-1.0 | Entrenar los centroides |
| Núcleo duro sintético | 24 | Generado para este trabajo | Entrenamiento de la clase crítica |
| Conjunto de prueba | 43 | Generado para este trabajo | Medición |

**Por qué el núcleo duro es sintético.** Ningún corpus público de atención al cliente publica casos de
reacción alérgica o amenaza judicial: son raros y sensibles. En una empresa real se tomarían de
tickets históricos anonimizados y etiquetados por el equipo de soporte. Esa sustitución es una
limitación declarada del trabajo, no un atajo silencioso.

**Calidad medida del dataset, no supuesta.** La primera lectura de cinco ejemplos sugirió mala calidad
y la medición dijo otra cosa: 0,69 % de residuos en inglés, 0,37 % de nombres propios filtrados,
19,7 % de instrucciones duplicadas, 19.424 ejemplos limpios y únicos. El primer detector de inglés que
escribí contaba los marcadores de plantilla (`{{Order Number}}` contiene *Order*) y reportaba 21,8 %.
Corregir la medición cambió la conclusión.

---

## 3. El mapeo intención → carril

El dataset trae **intención** —qué quiere el cliente—; el carril depende de la política de EcoMarket.
La traducción es una decisión por intención y no por ejemplo: **27 decisiones en lugar de 24.000**, y
esa proporción es lo que hace el ejercicio viable para una persona.

El criterio es el mismo de la Fase 1: *¿existe una respuesta correcta según la política vigente, o hay
que decidir una excepción?*

| Carril | Intenciones | Ejemplos | Criterio |
| :--- | ---: | ---: | :--- |
| `automatico` | 10 | 8.934 | La política responde; nadie decide nada |
| `copiloto` | 8 | 7.168 | Hay una decisión con efecto económico o una excepción |
| `derivacion` | 9 | 8.082 | Otra área de EcoMarket lo atiende; se entrega el canal |
| `humano_exclusivo` | **0** | — | **Lo asigna la capa 0, no la intención declarada** |

La tabla vive en [`fase5_clasificador/datos/mapeo_intencion_carril.csv`](fase5_clasificador/datos/mapeo_intencion_carril.csv)
con una columna `carril_final` editable y una `justificacion` por fila, de modo que la decisión queda
trazable y se puede corregir sin tocar el código.

**Ninguna intención mapea a `humano_exclusivo`, y es deliberado.** Un cliente puede preguntar por su
pedido y mencionar una reacción alérgica en la misma frase: la intención es `track_order` y el carril
debe ser `humano_exclusivo`. La consecuencia de diseño es dura y hay que mirarla de frente: **si la
capa 0 no atrapa un caso crítico, nada más lo atrapa.**

**`derivacion` empezó siendo `fuera_de_alcance`.** Las nueve intenciones de gestión de cuentas, venta y
marketing iban a descartarse. Se replantearon al implementar la lista blanca de canales: si el sistema
sabe a qué área pertenece el caso, entregar el canal correcto en un turno es mejor servicio que mandarlo
a una cola. Reconocer *esto no es mío* pasó a ser una capacidad medible.

---

## 4. La lista blanca de canales: cerrar el hallazgo 8.3a

La Fase 3 registró que los modelos fabricaban correos y teléfonos de soporte. Al implementar el control
apareció la causa raíz, y no era el modelo: **`politicas.md` no contiene ni un solo canal de contacto**.
El prompt pedía orientar al cliente y el contexto no tenía con qué. El modelo completó el vacío.

`canales.py` cubre el hueco por los dos lados. En la entrada inyecta un directorio de áreas con sus
canales y horarios. En la salida extrae todo correo, teléfono y URL del texto generado y lo contrasta
contra ese directorio. El segundo control es el que da la garantía: instruir al modelo baja la
frecuencia del fallo, verificarlo lo convierte en un error detectable antes de que la respuesta salga.

La referencia legítima no es solo el directorio. Es **el directorio unido a lo que el contexto de ese
turno contenía**: la URL de rastreo de un pedido llega por *function calling*, es distinta en cada
pedido y ninguna lista estática puede enumerarla. La primera versión del validador la marcaba como
fabricada. Es el mismo criterio de `verificar_grounding()` en la Fase 3.

### Medición sobre las salidas reales de la Fase 3

| Corrida | Fabricado | Marcador sin llenar | Total |
| :--- | ---: | ---: | ---: |
| iter1 · `qwen2.5:7b` | 0 | 3 | 3 |
| iter2 · `qwen2.5:7b` | 1 | 4 | 5 |
| iter2 · `mistral-small:24b` | 2 | 0 | 2 |
| **iter2 · `qwen3:14b`** | **10** | 2 | **12** |

**El modelo de referencia es el que más fabrica**, cinco veces más que el de 7B. Y los dos fallan de
forma distinta: `qwen2.5` escribe `[dirección de correo electrónico]` —declara que no tiene el dato y
entrega una plantilla rota—, mientras `qwen3` escribe `atencion@ecomarket.co` y `310 123 4567` con
aplomo. El fallo de `qwen2.5` lo detecta cualquiera que lea la respuesta. El de `qwen3` solo se detecta
si alguien intenta escribir a ese correo.

Junto con el hallazgo 8.6 —`mistral-small:24b` obtuvo cero alertas del guardarraíl y cometió el peor
error de negocio— son **dos casos independientes donde el modelo más grande se ve mejor y es peor**.

El directorio también separa dos áreas, `calidad` y `legal`, que el asistente conoce y nunca ofrece.
Un correo de calidad en una respuesta automática no es un dato falso; es una derivación que no debía
ocurrir, y el validador la reporta como un fallo distinto. Un cliente que reporta una reacción alérgica
no necesita una dirección de correo, necesita que alguien lo llame.

---

## 5. Resultados

43 casos de prueba: 22 comunes, 6 de núcleo duro explícito, 9 de núcleo duro parafraseado, 6 de
derivación. Los centroides se construyeron con 200 ejemplos por intención —5.400 embeddings de 768
dimensiones en 48 segundos— sobre `nomic-embed-text`.

### 5.1 La línea base de la capa 0

| Grupo | Resultado |
| :--- | :---: |
| Núcleo duro **explícito** | **6/6** |
| Núcleo duro **parafraseado** | **0/9** |

Los parafraseados expresan el mismo riesgo evitando deliberadamente los términos de la lista: *"mi bebé
se llevó el producto a la boca y lleva toda la tarde llorando y devolviendo"* en lugar de
*"intoxicación"*. El filtro léxico no ve nada. La pregunta falsable de toda la fase es si la capa
semántica recupera alguno.

### 5.2 Las dos políticas de decisión

| | Exactitud | Brecha 1 | Brecha 2 | A copiloto |
| :--- | :---: | :---: | :---: | :---: |
| **v1** — umbrales globales (confianza 0,60 · margen 0,03) | 44,2 % | 9 | **1** | 31/37 |
| **v2** — umbral por intención + coincidencia positiva | 41,9 % | 9 | **0** | 35/37 |

La matriz de confusión de la v1 muestra dónde está el problema:

| real \ predicho | automático | derivación | copiloto | humano excl. | recall |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **automático** | 3 | 0 | 9 | 0 | **25 %** |
| **derivación** | 0 | 1 | 5 | 0 | **17 %** |
| **copiloto** | 1 | 0 | 9 | 0 | 90 % |
| **humano exclusivo** | 1 | 0 | 8 | 6 | 40 % |

El único carril con buen recall es `copiloto`, y lo tiene porque es donde cae todo lo dudoso.

**Brecha 2** significa que un caso que exigía un humano terminó en el carril sin supervisión. Es el
único error que produce un incidente en vez de una demora, y la métrica binaria de *enrutamiento
inseguro* lo escondía: contaba igual mandar un caso de salud a automático que mandarlo a copiloto. Con
el conteo corregido, la v2 logra **lo único que podía lograr: ningún caso de salud llega al carril
automático**, a costa de 2,3 puntos de exactitud.

La v2 también corrige un caso que el margen no veía: *"es la segunda vez que me pasa lo mismo con
ustedes, espero una solución real"* iba al carril **automático** con la v1 —un cliente reincidente
atendido con plantilla— y baja a copiloto porque queda por debajo del piso de `track_refund` (0,742 <
0,753). Es el tipo de caso para el que se diseñó el umbral por intención.

Los tres cambios de la v2, y la evidencia de cada uno:

**Fuera el umbral global de confianza.** Las similitudes dentro de distribución tienen p5 = 0,733 y los
textos absurdos llegan a 0,727. Un solo número para 27 intenciones no separa nada cuando el piso propio
de cada centroide va de 0,688 (`delivery_options`) a 0,844 (`payment_issue`).

**Entra un umbral por intención**, el percentil 5 de la similitud de sus propios ejemplos con su
centroide. Un mensaje que no alcanza ese piso no se parece a esa intención ni al nivel de sus casos más
atípicos. El número sale de los datos.

**El carril automático exige coincidencia positiva.** En la v1 `automatico` era el destino por descarte
de cualquier mensaje que cayera cerca de un centroide automático. Es el único carril sin supervisión
humana, así que llegar ahí debería costar más que llegar a copiloto.

### 5.3 El costo de la seguridad, medido

| Margen exigido al carril automático | Aciertos | Brecha 2 | Casos automáticos correctos |
| :---: | :---: | :---: | :---: |
| 0,00 | 14/37 | 1 | **3/12** |
| 0,03 | 14/37 | 1 | **3/12** |
| 0,04 | 12/37 | 1 | 1/12 |
| 0,05 | 12/37 | 0 | 1/12 |
| 0,07 | 11/37 | 0 | 0/12 |

Esta tabla es la que cambia la conclusión de la fase. **Aun sin exigir ningún margen, el carril
automático solo acierta 3 de 12.** El umbral no es lo que está rompiendo la automatización. El
clasificador no identifica el carril automático.

Con 35 de 37 casos yendo a copiloto, el sistema es *todo lo revisa un humano*, que es exactamente lo
contrario de la premisa del taller.

> El barrido se hace sobre el mismo conjunto con el que se mide. Sirve para ver la forma del compromiso
> y no para fijar el valor definitivo; con 43 casos no alcanza para separar validación de prueba.

---

## 6. El hallazgo central: la transferencia del dataset falló

La causa está medida, y el dato ya estaba disponible antes de que lo interpretara bien.

`brecha_dominio.py` compara la similitud de cada ejemplo de entrenamiento con su propio centroide
contra la de cada caso de prueba con el centroide más cercano:

| Conjunto | n | min | p5 | p25 | mediana | p75 | max |
| :--- | ---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Entrenamiento (Bitext) | 5.400 | 0,453 | 0,748 | 0,813 | **0,857** | 0,890 | 0,967 |
| Prueba (EcoMarket) | 43 | 0,668 | 0,687 | 0,722 | **0,744** | 0,760 | 0,835 |

**La mediana de los casos de prueba (0,744) queda por debajo del percentil 5 del entrenamiento
(0,748).** El caso típico que el sistema va a recibir puntúa peor que el 95 % de los ejemplos con los
que se construyeron sus centroides. La mediana se desplaza 0,114 puntos hacia abajo, y **solo 1 de 43
casos alcanza el p25** del entrenamiento.

| Grupo | n | mediana | sobre el p25 |
| :--- | ---: | :---: | :---: |
| `comun` | 22 | 0,744 | 1/22 |
| `derivacion` | 6 | 0,744 | 0/6 |
| `nucleo_duro_parafraseado` | 9 | 0,758 | 0/9 |
| `nucleo_duro_evidente` | 6 | 0,691 | 0/6 |

La brecha es pareja entre grupos, así que no es un artefacto de los casos difíciles: es el dominio
completo el que no coincide.

Los centroides están construidos sobre un corpus genérico de comercio electrónico traducido del inglés.
Los casos de prueba son español colombiano natural, con *guía*, *plata*, *me arrepentí de la compra*.
Son dominios distintos y los embeddings lo registran.

**La conclusión práctica:** *existe un dataset público* no es lo mismo que *existen datos de
entrenamiento utilizables*. Esta medición es la justificación cuantificada de por qué una empresa real
necesita etiquetar sus propios tickets, y convierte en un número lo que de otro modo sería una
recomendación genérica.

---

## 7. Dos límites que no se arreglan ajustando parámetros

### 7.1 La confianza no mide riesgo, y no puede medirlo

Los nueve parafraseados puntúan entre 0,709 y 0,788. *"Mi bebé se llevó el producto a la boca"* obtuvo
**0,788**, el valor más alto de todo el grupo y más que varios aciertos. La hipótesis inicial fue que la confianza era inservible; la sonda
la corrigió y dio algo más preciso.

La confianza **sí** discrimina lo ajeno al dominio: fotosíntesis y Beethoven puntúan 0,669 de mediana
contra 0,857 de lo conocido. El solapamiento lo produce casi todo el núcleo duro, y por una razón de
fondo: **esos mensajes son texto de atención al cliente legítimo.** Una queja sobre un producto. Están
*dentro* de distribución como texto y fuera como carril. Lo que los distingue —hubo daño a una persona—
es un detalle del contenido, no el tema del mensaje, y el tema es lo que el embedding codifica.

De ahí la separación de responsabilidades: la confianza sirve para detectar fuera de dominio, y la
seguridad se queda en la capa 0. Que la capa 0 sea léxica es el límite del diseño, y declararlo es
parte del control.

### 7.2 El embedding captura el tema; el carril depende del acto

El diagnóstico de los centroides lo anticipó antes de medir:

| Par de intenciones | Coseno | Carriles |
| :--- | :---: | :--- |
| `change_order` ~ `track_order` | **0,976** | copiloto / automatico |
| `check_refund_policy` ~ `get_refund` | 0,934 | automatico / copiloto |
| `get_refund` ~ `track_refund` | 0,927 | copiloto / automatico |

Pedido, reembolso y factura son **temas**; consultar frente a solicitar es el **acto**. Un modelo de
similitud semántica no está optimizado para esa distinción, y es justo la que separa un carril que
compromete dinero de uno que no.

---

## 8. Qué haría falta para que esto funcione

Por orden de impacto esperado, y ninguno cuesta más que los demás juntos:

**Tickets reales de EcoMarket etiquetados por el equipo de soporte.** Es la causa raíz medida en §6 y no
la sustituye ninguna mejora de método. Con unos cientos de ejemplos por carril, en el español de los
clientes reales, la mayor parte de este informe deja de aplicar.

**Un clasificador entrenado en vez de centroides.** Una regresión logística sobre los embeddings aprende
qué dimensiones separan consultar de solicitar, que es precisamente lo que el promedio de un centroide
no puede representar. El código deja los vectores en caché, de modo que probarlo no cuesta volver a
inferir.

**Un modelo de embeddings adaptado al español latinoamericano**, o `nomic-embed-text` ajustado sobre el
corpus propio.

**La capa 0 revisada por el área legal y por calidad**, con las raíces léxicas versionadas como un
cambio controlado. Sigue siendo la única garantía del carril crítico.

---

## 9. Reproducción

```bash
ollama pull nomic-embed-text

cd fase5_clasificador
python capa0_reglas.py            # línea base del filtro léxico
python construir_mapeo.py         # tabla intención -> carril
python capa1_semantica.py construir
python sonda_confianza.py         # ¿mide algo la confianza?
python brecha_dominio.py          # ¿coincide el dominio de entrenamiento con el real?
python politica_v2.py             # comparación v1/v2 y curva de costo
python evaluar_clasificador.py    # matriz de confusión
python canales.py                 # lista blanca y validación de salida
```

El dataset (`datos/bitext_es.parquet`, 6,9 MB) no se versiona en el repositorio. Se descarga de
[bitext/Bitext-customer-support-llm-chatbot-training-dataset](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset)
en su edición en español, licencia CDLA-Sharing-1.0, que exige atribución y compartir igual.

En macOS con Apple Silicon, `numpy` emite `RuntimeWarning` de *divide by zero*, *overflow* e *invalid
value* en `matmul`. `politica_v2.py` los diagnostica: no hay NaN ni infinitos y la diferencia contra una
suma manual en float64 es de 6,7 × 10⁻⁷. Es un aviso espurio del BLAS de Accelerate y no afecta los
resultados.

---

## 10. Limitaciones declaradas

**La independencia del conjunto de prueba es parcial, y el archivo lo declara por separado en dos
campos** porque son dos garantías distintas:

| Campo | Estado | Qué garantiza |
| :--- | :---: | :--- |
| `etiqueta_revisada` | **43/43** | El autor leyó cada caso y confirmó el carril. El *ground truth* es humano |
| `texto_propio` | **18/43** | El texto lo redactó el autor y no el asistente que generó el entrenamiento |

Lo primero elimina el riesgo mayor: una etiqueta equivocada corrompe la medición entera. Lo segundo
es parcial, y está concentrado donde importa: **4 de los 9 casos de núcleo duro parafraseado** —los que
sostienen el hallazgo principal— están escritos por el autor.

La reescritura dejó una lección sobre el diseño de conjuntos de prueba. Tres de esos casos se
reescribieron primero incorporando *médico* y *urgencias*, que son dos de las 27 raíces de la capa 0.
Las etiquetas seguían siendo correctas y el sistema los atrapaba, pero el grupo dejaba de medir lo que
define —expresar el riesgo **evitando** el vocabulario del filtro— y el 0/9 se habría convertido en 3/9
por una prueba más fácil. Se volvieron a redactar sin esos términos y el grupo recuperó su propósito.
**Un caso de prueba se valida contra lo que el grupo mide, no solo contra su etiqueta.**

El sesgo restante empuja hacia arriba, de modo que **los resultados reales serían iguales o peores**.
Como las conclusiones de esta fase son negativas, el sesgo juega en contra de lo que se afirma: si con
un conjunto favorable el carril automático solo acierta 3 de 12, con textos plenamente independientes
no acertaría más.

**43 casos no alcanzan para separar validación de prueba**, de modo que los umbrales se eligieron
mirando el mismo conjunto con el que se mide. Los valores concretos no son transferibles; la forma del
compromiso sí.

**La clase `humano_exclusivo` depende por completo de la capa 0.** No hay respaldo. Un caso crítico
redactado sin los términos de la lista se pierde, y eso está medido en 0/9.

**El monto y la reincidencia se leen de campos simulados.** En producción vienen de la base
transaccional y esa integración no está implementada.

**Los canales del directorio son ficticios**, porque EcoMarket lo es. En una implementación real ese
archivo lo mantiene el área de servicio al cliente y su actualización es un cambio controlado: es la
única fuente de verdad contra la que se valida la salida del modelo.
