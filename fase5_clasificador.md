# Fase 5 — Clasificador de intención: dos aproximaciones medidas con la misma vara

**Caso**: EcoMarket — optimización de la atención al cliente
**Autor**: José Luis Realpe M.
**Curso**: Inteligencia Artificial Generativa — Maestría en IA Aplicada, Universidad Icesi

> La Fase 1 dibujó una caja llamada *clasificador de intención* y describió lo que debía hacer. Esta
> fase la implementa y la mide.
>
> **La primera aproximación da un resultado negativo y está documentado como tal.** Un clasificador
> por centroides de embeddings no alcanza a sostener el carril automático —46,5 % de exactitud— y la
> causa está cuantificada: el dataset público con el que se entrenó no representa el dominio en el que
> se mide, y la similitud semántica codifica el *tema* del mensaje cuando el carril depende del *acto*.
>
> **Ese diagnóstico produjo una predicción falsable, y la §9 la pone a prueba.** Si el problema es el
> método, un clasificador por prompt sobre el mismo conjunto debería resolver lo que los centroides no
> pueden. Sube a **83,7 %**, mantiene en **cero** los casos críticos enviados al carril automático y
> resuelve **7 de los 9** que se habían declarado estructuralmente inalcanzables. La restricción de
> fondo —no hay datos reales de EcoMarket— sigue en pie.
>
> Un experimento negativo con la causa identificada dice más sobre el problema que un número de
> exactitud sin diagnóstico. Y una causa bien identificada se puede atacar.

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
| `politica_v2.py` | Las tres políticas de decisión, su comparación y la curva de costo |
| `evaluar_clasificador.py` | Matriz de confusión y métrica de enrutamiento inseguro |
| `guardarrail_plazos.py` | Tercer guardarraíl: verifica número **y unidad** de los plazos citados |
| `clasificador_llm.py` | Segunda aproximación: clasifica por prompt en vez de por similitud (§9) |
| `comparar_clasificadores.py` | Mide centroides y prompt sobre los mismos 43 casos y las mismas métricas |
| `simular_hibrido.py` | Simula la cascada híbrida sin volver a llamar al modelo (§9.8) |

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
| **v3** — el margen se mide entre carriles | **46,5 %** | 9 | **0** | 33/37 |

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

La **v3 es la política vigente** y nació de probar la consola en vivo; §5.4 la desarrolla.

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

### 5.4 La v3: el margen se mide entre carriles, no entre intenciones

Esta política salió de escribir un caso cualquiera en la consola de la Fase 5 y mirar el detalle:

```
"hola, cuanto tiempo tengo para hacer una devolucion"

  delivery_period       0,790  automatico   <- elegida, y es la intención EQUIVOCADA
  check_refund_policy   0,759  automatico   <- la correcta
  track_refund          0,758  automatico
  get_refund            0,744  copiloto     <- primera candidata de otro carril

  v2: margen 0,790 − 0,759 = 0,031  ->  degrada a copiloto
```

La pregunta es por el plazo de *devolución* y ganó `delivery_period`, que es el plazo de *entrega*.
El embedding vio «plazo» y se quedó con el tema equivocado: el hallazgo de §7.2 con nombre y número.

Pero **las tres primeras candidatas coinciden en el carril**. El clasificador se equivocó de intención
y aun así el carril estaba bien. La v2 lo degradó igual, y ahí estaba el defecto:

> **La v2 mide la duda entre intenciones cuando la decisión es sobre carriles.** Si las dos candidatas
> más cercanas van al mismo sitio, la distancia entre ellas no dice nada sobre el riesgo de enrutar
> mal: solo dice que el modelo duda entre dos formas de nombrar lo mismo, y esa duda es inofensiva.

La formulación correcta compara contra la mejor candidata de un carril **distinto**:

```
margen_carril = similitud(mejor) − max{ similitud(i) : carril(i) ≠ carril(mejor) }
```

En el caso de arriba: 0,790 − 0,744 = **0,046** contra `get_refund`. El caso concreto sigue yendo a
copiloto, pero por la razón correcta: la duda real es *¿consulta la política o pide el reembolso?*, y
esa sí compromete dinero.

**Medido sobre los 43 casos, la v3 gana en las dos condiciones** fijadas antes de medir: mejor
exactitud de las tres y cero errores de dos niveles. Dos casos vuelven a su carril correcto —*«cuánto
se demora el reembolso»* a automático y *«cómo cambio el correo de mi perfil»* a derivación— y ninguno
se rompe.

El argumento de fondo vale más que los dos puntos de exactitud: que el clasificador no distinga
`delivery_period` de `check_refund_policy` es un error de etiqueta que no le cuesta nada a EcoMarket,
porque las dos se responden igual. Que no distinga `check_refund_policy` de `get_refund` sí, porque una
consulta la política y la otra compromete dinero. **La v2 penalizaba las dos por igual.**

### 5.3 El costo de la seguridad, medido

| Margen exigido al carril automático | Aciertos | Brecha 2 | Casos automáticos correctos |
| :---: | :---: | :---: | :---: |
| 0,00 | 14/37 | 1 | **3/12** |
| 0,03 | 14/37 | 1 | **3/12** |
| 0,04 | 15/37 | 1 | 3/12 |
| **0,05** | **14/37** | **0** | **2/12** |
| 0,07 | 12/37 | 0 | 0/12 |

En 0,04 hay un acierto más y la brecha 2 sube a 1. **0,05 es el margen más bajo que mantiene los
incidentes en cero**, así que el valor deja de ser una elección a ojo y pasa a ser el resultado de
aplicar el criterio de aceptación a la curva.

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

## 8. Lo que apareció al usar el sistema

Las secciones anteriores miden. Esta recoge lo que salió de **procesar casos nuevos uno por uno** en
la consola del banco de pruebas, que resultó ser una fuente de hallazgos distinta de la medición
agregada: tres defectos que ninguna métrica sobre 43 casos habría mostrado, porque no son cuestión de
frecuencia sino de qué ocurre exactamente en un caso concreto.

### 8.1 Arreglar la fabricación de canales habilitó la evasión

Primer caso procesado, sin número de pedido:

> *Cliente:* «hola, aún no tengo mi paquete»
>
> *Asistente:* «Para consultar el estado de su paquete, puede contactarnos por correo a
> pedidos@ecomarket.co o llamar al +57 602 555 0110.»

Los canales son auténticos y el guardarraíl los aprobó. Pero el cliente no preguntó por un canal:
**el asistente tenía un solo dato faltante —el número de pedido— y en lugar de pedirlo, derivó.**

La causa es directa. La lista blanca de §4 resolvió que el modelo inventara canales, y al hacerlo le
entregó una lista de salidas de emergencia. **Una corrección creó un modo de fallo nuevo**, y ninguno
de los dos guardarraíles lo ve, porque los datos son correctos y lo que falla es la decisión.

La corrección va en el prompt, y el orden de las instrucciones importa: primero *pide el dato que te
falta*, y solo después, como último recurso, *ofrece un canal*.

### 8.2 El guardarraíl marcó la palabra inocente y dejó pasar el error real

Segundo caso:

> *Cliente:* «el paquete está abierto»
>
> *Asistente:* «…las devoluciones deben realizarse dentro de los **30 días hábiles** desde la
> recepción del producto.»

El guardarraíl reportó un hallazgo: *«posible condición de política fabricada: 'abierto' no aparece en
el contexto»*. Falso positivo — esa palabra la escribió **el cliente**, y el verificador solo recibía
el pedido, las políticas y los canales. Un modelo que repite lo que dijo el cliente no fabrica nada.

Y no reportó lo que sí importaba. La política dice **30 días calendario**; el modelo escribió **30 días
hábiles**. Treinta días hábiles son casi seis semanas. Es una condición de política fabricada con
consecuencia económica directa, y pasó desapercibida porque no hay ningún identificador inventado: el
número es correcto y **cambió una sola palabra**.

Dos correcciones:

| Defecto | Corrección |
| :--- | :--- |
| El mensaje del cliente no contaba como contexto | Se incluye en la referencia del verificador |
| Ningún control miraba las unidades de plazo | Nuevo módulo [`guardarrail_plazos.py`](fase5_clasificador/guardarrail_plazos.py) |

El control nuevo es literal: todo plazo citado debe aparecer en el contexto con el mismo número **y la
misma unidad**. Si el contexto usa otra unidad para ese número, la alerta lo dice, porque contradecir
la política vigente es peor que inventar un plazo inexistente.

> Es el hallazgo II con una diferencia que lo hace barato de atrapar: **aquí el error sí es léxico.**
> «Calendario» y «hábiles» son dos palabras distintas y la correcta estaba escrita en el contexto.
> Su límite queda declarado en el propio módulo: solo cubre plazos en días.

### 8.3 La taxonomía del dataset no cubre casos reales

Tercer caso:

> *Cliente:* «me llegó el pedido de otra persona»

Las cinco candidatas quedaron entre 0,680 y 0,725 —ganó `delivery_period`— y la razón es que
**ninguna de las 27 intenciones del dataset describe esta situación.** El clasificador no estaba
eligiendo, estaba repartiendo entre opciones igualmente inadecuadas.

El caso además tiene una dimensión que ninguna de esas intenciones contempla: el cliente tiene en su
poder el paquete de un tercero, con su nombre y su dirección. Eso es tratamiento de datos personales
de otra persona bajo la Ley 1581 y no debería resolverlo una plantilla. El sistema lo envió a copiloto,
que es el carril correcto, **pero por el margen bajo y no porque entendiera el problema**.

### Por qué esta sección existe

Los tres hallazgos salieron de usar el sistema, no de medirlo, y los tres apuntan en la misma
dirección que el resto de la fase: **cada control tiene un alcance, y el alcance solo se descubre
cuando algo lo cruza.** Construir la consola no era un extra de presentación; fue el instrumento que
produjo estos tres.

---

## 9. El clasificador por prompt: la segunda aproximación, medida con la misma vara

El diagnóstico de §7 dejó una predicción falsable. Si el problema es que el embedding codifica el
**tema** y el carril depende del **acto**, entonces un modelo que *lee* el mensaje en vez de medir su
distancia a un promedio debería acertar donde los centroides fallan. La afirmación más fuerte era
estructural: la capa semántica **no puede** emitir `humano_exclusivo` —no hay centroide para esa
clase—, mientras que un clasificador por prompt sí puede. Eso convertía el experimento en una pregunta
con respuesta medible.

### 9.1 Cómo se construyó, y las cuatro decisiones que lo definen

`clasificador_llm.py` clasifica el mensaje con una sola llamada a `qwen3:14b` y espera una línea
`carril|confianza|justificacion`. Cuatro decisiones de diseño, cada una con su razón:

**Temperatura 0,0**, frente a 0,2 en generación. En clasificación la naturalidad no vale nada y la
reproducibilidad lo vale todo: la misma entrada debe dar la misma salida cuando otra persona corra el
script.

**Los ejemplos *few-shot* salen únicamente del entrenamiento** —del núcleo duro y de la tabla de
mapeo—, y cada uno está rotulado en el código con su origen. Ningún caso de `prueba.jsonl` entró al
prompt. Si uno hubiera entrado, el 83,7 % de abajo no mediría nada.

**Cualquier falla cae a `copiloto`.** Si el modelo no responde, responde fuera de formato o inventa un
carril, el caso va al carril con supervisión humana, nunca al automático. Es la misma asimetría que
gobierna el resto del sistema: equivocarse hacia arriba cuesta una demora, hacia abajo cuesta un
incidente. `parsear()` se probó contra nueve entradas adversarias —bloque `<think>`, comillas,
mayúsculas, guiones, carril inventado, respuesta vacía— y las tres impargueables cayeron al carril
seguro con `parseo_ok: False`.

**La política se inyecta por extracción directa, no por recuperación semántica.** El prompt incluye
literalmente las secciones `### 1.4` y `## 4.` del documento de política, 804 caracteres. La razón está
escrita en el código: *RAG resuelve «no sé cuál fragmento necesito»; aquí sí sé cuál.* Recuperar por
similitud un fragmento cuya ubicación es fija agrega un punto de falla sin agregar información.

### 9.2 Tres configuraciones, los mismos 43 casos, las mismas métricas

`comparar_clasificadores.py` reutiliza `SUPERVISION` y `cargar_prueba` de `evaluar_clasificador.py`,
de modo que los números son directamente comparables con los publicados en §5 sin reinterpretarlos.

| Configuración | Exactitud | IC 95 % | brecha 1 | **brecha 2** | copiloto | Costo |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **A** · capa 0 + centroides (v3) | 20/43 = 46,5 % | [32,5 – 61,1] | 9 | **0** | 33 | 0,03 s |
| **B** · capa 0 + prompt | **36/43 = 83,7 %** | [70,0 – 91,9] | **2** | **0** | 16 | 14,6 s |
| **C** · prompt solo, sin capa 0 | **36/43 = 83,7 %** | [70,0 – 91,9] | **2** | **0** | 16 | 14,6 s |

*43 casos, `qwen3:14b`, temperatura 0,0, 629,7 s de inferencia total. Cero fallos de parseo.*

**La condición de aceptación se cumple: brecha 2 sigue en cero.** Ese era el criterio declarado de
antemano —si el clasificador por prompt hubiera mandado al carril automático un solo caso que exigía
un humano, la idea se descartaba sin mirar la exactitud—. No lo hizo.

Los intervalos de A y B no se solapan. Con 43 casos casi nada es concluyente, y esta diferencia
alcanza a serlo.

### 9.3 El grupo que decidía el experimento

| | Núcleo duro parafraseado |
| :--- | :---: |
| Centroides | **0/9** — estructural: no hay centroide de `humano_exclusivo` |
| Prompt solo, sin capa 0 | **7/9** |

Siete de los nueve casos que el sistema medido en §5 no puede atrapar salvo por coincidencia léxica,
el prompt los clasifica correctamente **sin la capa 0 delante**. Las justificaciones que devuelve
nombran exactamente el criterio que define el grupo: *«reporta posible daño a la salud de un menor por
ingestión de producto»*, *«amenaza de acción legal»*. El modelo no está reconociendo palabras, está
leyendo el hecho.

Los dos que falla son ambos del eje legal y ambos caen a `copiloto`, que es **brecha 1: una demora,
no un incidente**:

> *«Voy a tener que buscar asesoría de alguien…»* → `copiloto`
> *«Ya hablé con alguien que me está asesorando…»* → `copiloto`

Las justificaciones son reveladoras: *«solicita asesoría legal: compromete decisión externa»*,
*«puede requerir intervención»*. El modelo **detectó** el elemento legal y aun así lo pesó por debajo
del umbral. La regla del prompt trata la amenaza explícita de acción legal como categórica y deja la
mención de pasada en zona gris. Es un problema de redacción de la regla, y la §9.6 explica por qué no
se corrigió.

### 9.4 El hallazgo que no se buscaba: la capa 0 quedó redundante

**B y C dan exactamente el mismo resultado en las tres métricas.** La capa 0 escaló 6 de los 43 casos,
y el prompt clasificó esos mismos 6 igual por su cuenta. El filtro léxico no aportó un solo caso.

La conclusión operativa no es quitarlo. **Se conserva, y por una razón que no aparece en la tabla**:
la capa 0 es determinista, cuesta microsegundos y no depende de que un servicio de inferencia responda.
Es la única parte del sistema que sigue clasificando si Ollama está caído, si el modelo cambia de
versión o si una actualización altera su comportamiento. Deja de ser la única red del carril crítico
y pasa a ser el piso garantizado debajo de una red mejor. Esa es la forma que toma la defensa en
profundidad cuando la capa de arriba es probabilística.

### 9.5 Un caso que ninguna configuración acierta, y lo que revela de la métrica

> *«Ya no quiero recibir los correos de ustedes»* — real: `derivacion` · prompt: `automatico`

No cuenta como brecha, porque la escala de supervisión asigna 0 tanto a `derivacion` como a
`automatico`. Y sin embargo es una **solicitud de supresión de datos personales**, un derecho del
titular bajo el artículo 8 de la Ley 1581 de 2012, con término legal para responder y área
responsable definida. El sistema la resolvería sola y en silencio.

**La escala de supervisión mide riesgo de autonomía, no riesgo regulatorio.** Son dos ejes distintos y
el informe venía midiendo uno solo. Un caso puede ser inofensivo para el cliente y aun así ser un
incumplimiento de habeas data. Corregirlo exige una segunda dimensión en la métrica, y esa dimensión
no está construida.

### 9.6 Lo que no se hizo, a propósito

**No se ajustó el prompt para recuperar los dos fallos legales.** La corrección es evidente —basta
endurecer la regla para que cualquier mención de asesoría o acción legal sea categórica—, y por eso
mismo es peligrosa: mirar los errores del conjunto de prueba y reescribir el prompt contra ellos
convierte el 83,7 % en un número ajustado a esos 43 casos y ya no en una estimación. El ajuste queda
declarado como trabajo pendiente, con su conjunto de validación aparte.

**Una vía de contaminación sí queda declarada.** Los ejemplos del prompt salen del entrenamiento, pero
la «regla que manda sobre todas las demás» —salud o legal ⇒ `humano_exclusivo`— se redactó con el
diagnóstico de §5 y §7 ya conocido, y ese diagnóstico salió de mirar este conjunto de prueba. La
influencia es indirecta y no anula el resultado; declararla es parte de la medición.

**No se midió la arquitectura híbrida evidente**: centroides primero y el modelo solo cuando el margen
entre carriles es bajo, que recuperaría buena parte de la exactitud a una fracción del costo. Es la
continuación natural y no está implementada, de modo que no se afirma nada sobre ella.

### 9.7 El costo, que es parte del resultado

**14,6 segundos por caso frente a 0,03: un factor de ~490.** El número importa según el carril. Para
decidir si un reporte de daño a la salud llega a un humano, quince segundos son irrelevantes. Para
responder *«¿dónde está mi pedido?»*, son la diferencia entre una respuesta y un abandono. Eso vuelve
a apuntar a la arquitectura híbrida de §9.6, y refuerza por qué la capa 0 se queda: resuelve gratis
los casos que no admiten espera.

### 9.8 El disparador mide incertidumbre, no riesgo — y por qué eso importa

Probar la consola con un caso nuevo dejó a la vista un límite que ninguna de las
tablas anteriores muestra. El mensaje fue *«llevo toda la tarde con malestar luego de consumir
su producto»*, escrito en el momento y sin ninguna de las 27 raíces de la capa 0:

```
capa 0     ninguna regla dispara
capa 1     delivery_period   confianza 0,790   piso de la intencion 0,692   -> pasa el piso
v3         margen entre carriles 0,029 contra review; el automatico exige 0,05
           -> copiloto, con razon
cascada    humano_exclusivo (0,95) — «reporta dano a la salud de una persona»
corte      cola de atencion humana; no se genera respuesta
```

El sistema acertó. **Pero escaló por la razón equivocada.** Lo que disparó la cascada fue una
duda de enrutamiento entre `delivery_period` y `review`, dos intenciones que no tienen relación
con la salud. Si ese margen hubiera sido 0,06 en lugar de 0,029, la v3 no habría dudado, la
cascada no se habría disparado y un cliente con malestar estomacal habría recibido una respuesta
automática sobre plazos de entrega.

De ahí la formulación general: **la cascada solo ve los casos que el centroide no entiende, no
los casos peligrosos.** Un centroide seguro y equivocado nunca llega al clasificador por prompt.

La pregunta que sigue es si eso ocurre en la práctica, y se puede medir:

| | Núcleo duro parafraseado |
| :--- | :---: |
| Casos en los que la v3 dudó y la cascada se disparó | **9/9** |

Los nueve escalaron. Y los únicos cuatro casos que el centroide resolvió sin dudar en todo el
conjunto son estos:

> *«¿Cuándo llega mi pedido?»* · *«Cuánto se demora el reembolso»* ·
> *«Quiero que borren mi cuenta y todos mis datos»* · *«Cómo hago para cambiar el correo de mi perfil»*

Cortos, canónicos, de una sola intención, redactados casi como los ejemplos del corpus. **El
centroide deja de dudar exactamente cuando el mensaje se parece a lo que vio en el
entrenamiento.** Un mensaje de núcleo duro es, por construcción, lo contrario: español
colombiano natural, narrativo, alguien contando algo que le pasó. La duda y el riesgo salen de
la misma causa, que es la brecha de dominio medida en la §6.

**La consecuencia es incómoda y conviene decirla completa: la protección que da la cascada
depende de que el clasificador semántico sea malo.**

Con los tickets reales que pide la §10, el centroide se volvería confiado precisamente sobre ese
registro de español, dejaría de dudar de un reporte de daño a la salud redactado de forma
natural, y la cascada no se dispararía donde más hace falta. Arreglar la causa raíz degradaría
esta salvaguarda. No es una paradoja: un disparador que mide incertidumbre protege solo mientras
el sistema sea incierto.

Dos conclusiones de diseño se siguen de esto:

**`humano_exclusivo` no puede depender de la cascada.** El 9/9 es una correlación observada sobre
nueve casos, no una propiedad garantizada, y la diferencia entre esas dos cosas es justo lo que
hay que declarar.

**La capa 0 es la única pieza cuya garantía no se degrada cuando el resto mejora**, porque
dispara por riesgo y no por duda. Es el tercer argumento independiente —después del de la §9.4 y
del de la Fase 4— para conservarla, y el más fuerte de los tres.

### 9.9 El piso de confianza: un indicador de calidad de datos disfrazado de constante

El límite de la §9.8 se cierra agregando un **segundo disparador**, independiente del primero:

| Disparador | Qué pregunta | Qué detecta |
| :--- | :--- | :--- |
| Margen entre carriles (v3) | *¿Entre qué dos carriles elijo?* | Ambigüedad de enrutamiento |
| **Piso de confianza** | *¿Se parece esto a algo que conozca?* | **Distancia al dominio de entrenamiento** |

La cascada escala si se cumple **cualquiera** de los dos. El segundo es el que importa para la
seguridad: un mensaje de núcleo duro en español natural queda lejos de todo centroide, de modo que
su confianza es baja *por la misma causa* por la que es riesgoso. Con el piso, la protección deja
de depender de que el margen salga estrecho y pasa a ser una regla explícita.

**El umbral se declara, no se ajusta.** Se fijó en **0,88** por política y no barriendo la tabla
para maximizar la exactitud, que es lo que la §12 declara como límite del conjunto. Puesto contra
las cifras de la §6:

| | p5 | mediana |
| :--- | :---: | :---: |
| Entrenamiento (Bitext) | 0,748 | **0,857** |
| Prueba (EcoMarket) | 0,687 | **0,744** |

**0,88 está por encima de la mediana del entrenamiento**, así que hoy casi todo caso real cae por
debajo y la cascada se dispara casi siempre. Eso no es un umbral mal elegido. **Es la medida de
que el corpus público no representa el dominio**, expresada como una constante que el sistema
consulta en cada mensaje.

Y de ahí sale la propiedad que justifica el diseño. El valor no se toca nunca; el sistema mejora
por el otro lado:

> Entrenar la capa semántica con **tickets reales de EcoMarket** sube la confianza sobre el
> español que los clientes escriben de verdad. Menos casos cruzan el piso hacia abajo, la cascada
> se dispara menos, y **el uso del clasificador por prompt baja solo, sin modificar una línea de
> código.** La fracción de casos escalados se vuelve la métrica de cuán lejos está el
> entrenamiento del dominio.

Eso invierte el problema de la §9.8. Allí, mejorar los datos *degradaba* la salvaguarda, porque la
protección venía de que el clasificador fuera malo. Con el piso declarado, mejorar los datos
**reduce el costo** y la salvaguarda sigue en su sitio: el piso no deja de aplicarse cuando el
sistema mejora, simplemente lo cruzan menos mensajes.

El objetivo declarado, entonces, es que **el clasificador por prompt intervenga lo menos posible**.
Hoy interviene en casi todo y eso es el síntoma, no el diseño. La meta no es un umbral más
permisivo: es un entrenamiento que no lo necesite.

`simular_hibrido.py` imprime el costo de cada nivel de exigencia. La tabla está para dimensionar
el costo de una política ya fijada, no para escoger el número:

| Piso | Escala | Exactitud | Brecha 2 | s/caso |
| ---: | ---: | ---: | :---: | ---: |
| sin piso (solo margen) | 77 % | 83,7 % | 0 | 11,24 |
| 0,75 | 79 % | 83,7 % | 0 | 11,58 |
| 0,80 | 84 % | 83,7 % | 0 | 12,26 |
| **0,88** | **86 %** | **83,7 %** | **0** | **12,60** |
| 0,92 | 86 % | 83,7 % | 0 | 12,60 |

**Con 0,88 escalan los 37 casos que llegan a la capa semántica** —el 86 % restante lo resuelve la
capa 0—, de modo que el híbrido pasa a ser idéntico a la configuración B. Cuesta 1,36 s más por
caso y no gana ningún acierto. Los pisos de 0,85 en adelante dan el mismo resultado por la razón
que aparece en la última línea del script.

#### El dato que reinterpreta el ahorro del 23 %

> Confianza de los 4 casos que el centroide resolvió sin dudar: **0,736 – 0,835**

La mediana del entrenamiento es **0,857**. Los cuatro casos «seguros» quedan por debajo, y el
máximo —0,835— explica por qué cualquier piso superior escala todo. La consecuencia es más amplia
que el ajuste de un umbral:

**En los 43 casos de prueba el centroide nunca estuvo realmente confiado.** Ni una vez alcanzó el
nivel que para él representa un caso típico.

Eso reinterpreta el 23 % de ahorro de la §9.7. No era un camino barato legítimo: eran cuatro casos
que el disparador de margen dejó pasar, y en los que el centroide acertó sin tener una confianza
que lo respaldara. **Hoy no existe un camino barato en este sistema**, y el piso de confianza deja
de suponer que sí.

#### Qué se puede afirmar, entonces

**La arquitectura híbrida es correcta y hoy no rinde.** Con los datos actuales equivale a la
configuración B y su único aporte es dejar la regla de seguridad explícita en lugar de apoyada en
una correlación de nueve casos. Su valor es **condicional a resolver la brecha de dominio**, que es
la misma causa raíz de la §6 apareciendo por tercera vez.

Lo que sí queda instalado es el instrumento: **la tasa de escalamiento, hoy en 86 %, es la lectura
de cuánto le falta al entrenamiento para representar el dominio.** No hay que interpretarla ni
recalcularla — baja sola cuando los datos mejoren, y el día que baje, el ahorro aparece sin tocar
una línea.

### 9.10 Qué cambia esto en las conclusiones de la fase

El resultado negativo de §5 y §6 **se mantiene intacto y con la misma causa**: el dataset público no
transfiere al dominio, y ninguna configuración de centroides sostiene el carril automático. Lo que
cambia es el alcance de la conclusión. El fracaso no era del problema, era del método aplicado a él.
Con la misma política, el mismo conjunto de prueba y la misma métrica, cambiar de similitud de
embeddings a lectura por prompt mueve la exactitud de 46,5 % a 83,7 % y resuelve el límite que se
había declarado estructural.

Sigue sin haber datos reales de EcoMarket, y esa carencia sigue siendo la restricción de fondo.

---

## 10. Qué haría falta para que esto funcione

Por orden de impacto esperado, y ninguno cuesta más que los demás juntos:

**Tickets reales de EcoMarket etiquetados por el equipo de soporte.** Es la causa raíz medida en §6 y no
la sustituye ninguna mejora de método. Con unos cientos de ejemplos por carril, en el español de los
clientes reales, la mayor parte de este informe deja de aplicar.

> **Y es la vía por la que baja el costo del clasificador.** Con el piso de confianza de la §9.9
> fijo en 0,88, cada punto que suba la confianza del centroide sobre texto real es un caso menos
> que escala al modelo. La fracción de casos escalados —hoy casi todos— es la métrica directa de
> cuánto le falta al entrenamiento para representar el dominio, y el objetivo operativo es que el
> clasificador por prompt intervenga lo menos posible.

**La arquitectura híbrida por margen.** Centroides primero y clasificador por prompt solo cuando el
margen entre carriles queda por debajo del umbral. La §9 muestra que el prompt gana 37 puntos a un
costo de ~490× por caso; el híbrido apunta a conservar la mayor parte de esa ganancia pagándola solo
en los casos dudosos. Es la continuación directa de esta fase y no está implementada.

**Un clasificador entrenado en vez de centroides.** Una regresión logística sobre los embeddings aprende
qué dimensiones separan consultar de solicitar, que es precisamente lo que el promedio de un centroide
no puede representar. El código deja los vectores en caché, de modo que probarlo no cuesta volver a
inferir. Sigue valiendo la pena como línea barata: el prompt cuesta segundos y este cuesta
microsegundos.

**Una segunda dimensión en la métrica de riesgo.** La §9.5 encontró un caso —solicitud de supresión de
datos personales— que es inofensivo en la escala de supervisión y aun así es un asunto de habeas data
con término legal. Riesgo de autonomía y riesgo regulatorio son ejes distintos y el informe mide uno.

**Un modelo de embeddings adaptado al español latinoamericano**, o `nomic-embed-text` ajustado sobre el
corpus propio.

**La capa 0 revisada por el área legal y por calidad**, con las raíces léxicas versionadas como un
cambio controlado. Sigue siendo la única garantía del carril crítico.

---

## 11. Reproducción

```bash
ollama pull nomic-embed-text

cd fase5_clasificador
python capa0_reglas.py            # línea base del filtro léxico
python construir_mapeo.py         # tabla intención -> carril
python capa1_semantica.py construir
python sonda_confianza.py         # ¿mide algo la confianza?
python brecha_dominio.py          # ¿coincide el dominio de entrenamiento con el real?
python politica_v2.py             # comparación v1/v2/v3 y curva de costo
python evaluar_clasificador.py    # matriz de confusión
python canales.py                 # lista blanca y validación de salida
python guardarrail_plazos.py      # verificación de plazos citados

# Fase 5 bis — clasificador por prompt (requiere el modelo generador)
ollama pull qwen3:14b
python clasificador_llm.py         # prueba de humo, 6 casos
python comparar_clasificadores.py  # centroides vs prompt, 43 casos (~10 min)
python simular_hibrido.py          # cascada hibrida, sin inferencia nueva
```

El dataset (`datos/bitext_es.parquet`, 6,9 MB) no se versiona en el repositorio. Se descarga de
[bitext/Bitext-customer-support-llm-chatbot-training-dataset](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset)
en su edición en español, licencia CDLA-Sharing-1.0, que exige atribución y compartir igual.

En macOS con Apple Silicon, `numpy` emite `RuntimeWarning` de *divide by zero*, *overflow* e *invalid
value* en `matmul`. `politica_v2.py` los diagnostica: no hay NaN ni infinitos y la diferencia contra una
suma manual en float64 es de 6,7 × 10⁻⁷. Es un aviso espurio del BLAS de Accelerate y no afecta los
resultados.

---

## 12. Limitaciones declaradas

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

**En la configuración por centroides, la clase `humano_exclusivo` depende por completo de la capa 0.**
No hay respaldo: un caso crítico redactado sin los términos de la lista se pierde, y eso está medido
en 0/9. El clasificador por prompt de la §9 recupera 7 de esos 9 sin ayuda de la capa 0, de modo que
el límite deja de ser estructural en esa configuración. Lo que sustituye una red determinista por una
probabilística, y por eso la capa 0 se conserva debajo.

**El 83,7 % de la §9 se mide sobre 43 casos**, con un intervalo de [70,0 – 91,9] al 95 %. Sostiene la
comparación contra el 46,5 % de los centroides, cuyo intervalo no se solapa; no sostiene ninguna
afirmación sobre el valor exacto. El prompt tampoco se ajustó contra los errores observados, de modo
que la cifra es una estimación y no un máximo alcanzado.

**Un error de método que quedó documentado en el código.** La primera versión del comparador tenía el
barrido de umbrales escrito dos veces —uno para imprimir y otro para el JSON—, y al introducir la v3
solo se actualizó uno. La tabla impresa quedó rotulada «política v3» mostrando cifras de la v2, y la
inconsistencia se detectó porque el total del barrido no cuadraba con el de la comparación. Se unificó
en una sola función `barrer()`: dos copias de un cálculo se desincronizan en el primer cambio.

**El monto y la reincidencia se leen de campos simulados.** En producción vienen de la base
transaccional y esa integración no está implementada.

**Los canales del directorio son ficticios**, porque EcoMarket lo es. En una implementación real ese
archivo lo mantiene el área de servicio al cliente y su actualización es un cambio controlado: es la
única fuente de verdad contra la que se valida la salida del modelo.
