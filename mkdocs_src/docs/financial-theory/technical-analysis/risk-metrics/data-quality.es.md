# 🧪 Calidad de datos

Una cifra de riesgo es tan fiable como las observaciones que la sustentan, por lo que la cantidad y la frescura de los datos subyacentes forman parte de la lectura del resultado. LibreFolio no mantiene esa capa oculta: cada resultado de riesgo viaja con un informe de datos de origen, un estado derivado de él y —cuando faltaba algo— la lista de lo que faltaba.

---

## 🚦 Estado de los datos de origen {: #source-data-status }

Los datos de origen se clasifican en tres niveles:

| Estado | Qué significa |
|---|---|
| `ok` | Nada falta y nada se ha arrastrado durante más tiempo que el [umbral de antigüedad](#staleness-threshold). La serie es lo que dice ser. |
| `carried_forward` | Nada falta por completo, pero algunos precios o tipos de cambio se arrastraron desde una fecha anterior durante más tiempo que el umbral de antigüedad: cotizaciones obsoletas, puntos de precio arrastrados, puntos de FX arrastrados. |
| `partial` | Algo falta por completo: precios, pares FX, fechas dentro de la ventana analizada en las que no todas las posiciones pudieron valorarse, pares de divisas no resueltos o activos que no pudieron participar en absoluto. |

Dos propiedades de esta escala importan más que las etiquetas.

**Se deriva, no se declara.** El estado es una propiedad calculada del propio contenido del informe: un productor no puede declarar `ok` mientras informa de precios faltantes, porque el estado se recalcula a partir de lo que contiene el informe. Cualquier falta absoluta da `partial`; si nada falta pero algo se arrastró más allá del umbral de antigüedad, `carried_forward`; en caso contrario, `ok`. `partial` tiene precedencia sobre `carried_forward`.

**Es categórico, no numérico.** El estado responde a *qué tipo de imperfección está presente*, nunca a *cuánta es tolerable*. No hay un nivel de completitud por debajo del cual el sistema declare una cifra no fiable; ese juicio se deja al lector, de forma deliberada y explícita.

### ⏳ El umbral de antigüedad {: #staleness-threshold }

Un precio o un tipo de cambio arrastrado desde una fecha anterior es normal en sí mismo: los fines de semana, los días festivos y los instrumentos cotizados según sus propios calendarios de mercado dejan huecos todo el tiempo — y un precio almacenado un fin de semana o un día festivo de mercado que solo repite el cierre anterior también se arrastra, no se cotiza (véase [Arrastres almacenados](#stored-carries)). Un valor arrastrado se vuelve **obsoleto** solo cuando es más de **siete días naturales** más antiguo que la fecha a la que sustituye, y solo uno obsoleto cuenta en la serie por activo de un análisis: se registra como un punto de precio o de FX arrastrado, y uno solo basta para `carried_forward`. Uno más joven no degrada nada, pero no es invisible: un precio arrastrado sigue dando una rentabilidad del período de cero, y esa rentabilidad entra en la muestra (véase [Limitaciones](#limitations)). El umbral decide qué cuenta como imperfección, no cuántas imperfecciones son tolerables.

Siete días naturales es el único umbral de antigüedad del proyecto, no una convención de esta página: el [laboratorio de correlación](../../../user/assets/correlation.md) de la página de Activos y la repetición histórica juzgan la antigüedad de un precio por esos mismos siete días, y las advertencias que informan de precios o tipos de cambio obsoletos lo citan.

### 🔁 Arrastres almacenados {: #stored-carries }

No todos los precios arrastrados llegan como un hueco. Algunas fuentes entregan una fila para cada día natural, repitiendo el último cierre en los días en que su mercado está cerrado: justETF, por ejemplo, repite el cierre del viernes el sábado y el domingo. Leídas como cotizaciones, esas filas introducirían en cada serie construida a partir de ellas una rentabilidad de cero, en la moneda del propio activo, que ningún mercado produjo. Por tanto, un precio almacenado es un **arrastre**, no una cotización, cuando se cumplen ambas condiciones:

- está fechado en sábado o domingo, o en un día laborable que es festivo en al menos uno de los principales mercados — la unión de los calendarios que QuantLib proporciona para TARGET, Borsa Italiana, Xetra, Euronext Paris, la London Stock Exchange, Switzerland y la NYSE;
- su cierre, en la moneda del propio activo, es **exactamente** el cierre de la fila anterior, sin tolerancia.

Tres tipos de fila siguen siendo cotizaciones: el primer precio de una serie, que no tiene fila anterior; un precio sin cambios en un día laborable ordinario, porque un día plano de un bono o un fondo del mercado monetario es real; y un precio que se movió un fin de semana o un festivo, como hace el de un criptoactivo. La unión de los mercados es segura porque la regla también exige la repetición exacta: un instrumento que cotizó mientras otro mercado estaba cerrado casi siempre se ha movido, y un precio que se movió sigue siendo una cotización — en el peor caso, un día genuinamente plano en tal fecha se lee como un arrastre. La tabla de festivos se construye cuando arranca el servidor; si no pudo construirse, solo se aplican los fines de semana hasta que un intento posterior tenga éxito.

Un arrastre es la última cotización genuina arrastrada, y se fecha a partir de esa cotización, así que durante un fin de semana ordinario tiene uno o dos días de antigüedad — muy dentro del umbral de antigüedad. Su fecha no es una fecha de cotización del activo. No añade ningún candidato al [calendario compartido](#alignment-what-missing-data-actually-costs), ningún día de observación a la serie de rentabilidad de una cartera (véase [Cobertura](#coverage)), y nada a las cotizaciones que deciden si un activo puede participar en un análisis de un conjunto de activos — al menos 20 en el período, el mínimo que aceptan las analíticas estadísticas — o en una [repetición histórica](historical-replay.md), que necesita el activo valorado en ambos extremos de su ventana. Cuando la cotización de otro activo sitúa la fecha en un calendario compartido de todos modos, el activo se valora allí en su última cotización genuina, y ese punto cuenta como arrastrado en la medida de frescura de [Cobertura](#coverage).

---

## 📋 Qué registra el informe {: #what-the-report-records }

El informe es un inventario, no una puntuación:

| Señal | Qué captura |
|---|---|
| Activos sin precio | Posiciones para las que no se pudo obtener ningún precio utilizable |
| Pares FX faltantes / no resueltos | Conversiones de divisa que no pudieron resolverse |
| Precios obsoletos | Posiciones cuyo último precio es más antiguo que el [umbral de antigüedad](#staleness-threshold) |
| Puntos de precio arrastrados | Cuántos puntos de precio se arrastraron más allá del umbral de antigüedad, y para qué activos |
| Puntos de FX arrastrados | Cuántos puntos de conversión se arrastraron más allá del umbral de antigüedad, y para qué pares |
| Fechas incompletas | Fechas en las que la valoración, el NAV, el valor contable o la asignación no pudieron completarse para todas las posiciones |
| Activos no utilizables | Activos excluidos antes de intentar cualquier métrica, cada uno con un motivo |
| Advertencias | Notas de formato libre adjuntadas por la etapa productora |

Cada entrada nombra el objeto al que se refiere — el activo, el par de divisas, la fecha. Un lector puede preguntar *qué* activo, par de divisas o fecha degradó la cifra, no solo *si* algo lo hizo.

---

## 🧮 Alineación: qué cuesta realmente que falten datos {: #alignment-what-missing-data-actually-costs }

Cuando un análisis abarca varias posiciones — una matriz de correlación, un desglose de contribución al riesgo — se calcula sobre un **único calendario compartido**, y construir ese calendario es donde los datos faltantes se convierten en un coste visible.

1. Una fecha es candidata si al menos una posición tuvo una cotización fresca en ella, sin que un [arrastre almacenado](#stored-carries) cuente como tal: los candidatos son la unión de los calendarios de cotización de las posiciones durante la ventana solicitada.
2. Una fecha candidata entra en el análisis solo si **todas** las posiciones pudieron valorarse en ella. Aquí *valorado* incluye un precio o un tipo de cambio arrastrado desde una fecha anterior, sin límite de antigüedad, así que en la práctica la prueba falla solo antes del primer precio utilizable de una posición, o donde su conversión a la moneda objetivo no pudo resolverse. Las fechas que fallan esta prueba se descartan para todas las posiciones, pero se registran como fechas de valoración incompletas solo una vez que el calendario ha comenzado — es decir, después de la línea base.
3. La línea base es la última fecha anterior al inicio solicitado en la que todas las posiciones eran valorables; si no hay ninguna, el análisis comienza dentro de la ventana solicitada, en la primera fecha en la que todas las posiciones pueden valorarse, y se nombran las posiciones responsables del inicio tardío.

La consecuencia merece decirse claramente: **una posición que empieza tarde acorta la ventana para todos**. Un hueco dentro de un historial no acorta nada, porque el precio o el tipo de cambio faltante se arrastra. Nada se interpola: un precio o un tipo arrastrado es el último conocido. Una vez que se ha arrastrado más allá del [umbral de antigüedad](#staleness-threshold) se cuenta como un punto arrastrado — un asunto del estado `carried_forward`, no de la longitud de la ventana. Uno más joven no degrada el estado, aunque un precio arrastrado, sea cual sea su antigüedad, sigue contando en la medida de frescura descrita en [Cobertura](#coverage). Una posición nunca se incluye parcialmente en un cálculo conjunto — o la fecha sirve para todas o no es una observación. Un inicio tardío por sí solo no hace que el resultado sea `partial`: las fechas que cuesta no se listan como incompletas, el informe nombra las posiciones responsables en sus entradas `short_history`, y la pérdida se muestra en el recuento de observaciones y en la cobertura del calendario compartido más abajo. Una fecha perdida después de que el calendario haya comenzado es diferente: se lista como incompleta y hace que el resultado sea `partial`.

---

## 📏 Cobertura {: #coverage }

La cobertura es normalmente el compañero de densidad del estado: responde a *cuánto de lo que podría haberse observado se observó realmente*. Varios ratios diferentes reciben ese nombre. No comparten denominador, y no todos miden el mismo tipo de cosa: dos de ellos cuentan observaciones, un tercero cuenta posiciones y no contiene ninguna observación.

**¿Cuánto costó el calendario compartido?** De las fechas en las que al menos una posición tuvo una cotización fresca, esta es la proporción que sobrevivió al requisito de que todas las posiciones fueran valorables. Una cifra muy por debajo de 1 significa que en muchas de las fechas en las que alguna posición cotizó, otra no pudo valorarse — y como los huecos se arrastran, eso normalmente apunta a una posición cuyo historial comienza mucho después del inicio solicitado, o a conversiones que no pudieron resolverse, más que a huecos.

**¿Cuánto de los datos es genuinamente fresco?** En la cuadrícula de posiciones × observaciones, esta es la proporción de puntos cuyo precio se cotizó en esa fecha en lugar de arrastrarse desde una anterior. Mide el mismo tipo de imperfección que el estado `carried_forward`, pero solo sobre las observaciones y con un criterio más estricto: todo precio arrastrado cuenta en su contra, por joven que sea, mientras que el estado solo cuenta los arrastrados más allá del umbral de antigüedad. También cuenta solo precios: una cotización fresca pero que tuvo que convertirse con un tipo de cambio arrastrado sigue contando como fresca, porque las conversiones arrastradas se registran como su propia señal separada. Así que una proporción por debajo del 100% no implica por sí misma `carried_forward`, y una proporción del 100% no lo descarta por sí misma — ni, por tanto, un resultado `partial`.

**¿Cuánto de la cartera pudo clasificarse?** De las posiciones en alcance, esta es la proporción cuyos metadatos de sector o geografía estaban disponibles, en lugar de faltar y enviar la posición al cajón de sastre `Other` al 100%. Esta es una afirmación sobre metadatos: no entra ningún precio, ninguna fecha ni ninguna observación. Un [choque hipotético](hypothetical-shock.md) informa de este ratio.

!!! warning "Un nombre compartido, dos tipos de cantidad"

    Cuando la cifra es una medida de densidad, su denominador depende de la ruta. Para un análisis construido a partir de cotizaciones de instrumentos, son las fechas de cotización candidatas. Para una serie de cartera, son los **días de observación** de la cartera: el análisis lee la propia serie de rentabilidad de la cartera, su [rentabilidad ponderada por tiempo](../performance-metrics/portfolio-engine/twrr.md), solo en los días en los que al menos una posición del alcance tuvo una cotización propia, y encadena la rentabilidad de todos los demás días en el siguiente; el denominador cuenta esos días a lo largo del período — o cada día natural abarcado, si ninguna posición tuvo una cotización propia en la ventana. En una serie de cartera esa cifra es alta por construcción — el historial de la cartera tiene un punto para cada día natural, arrastrando el último valor conocido allí donde no se cotizó nada, así que cada día de observación tiene uno — y por tanto no certifica nada sobre los precios que hay detrás. En una cuadrícula de instrumentos una cifra más baja apunta a fechas que el calendario compartido realmente perdió — un inicio tardío o una conversión que no pudo resolverse — nunca a un mercado cerrado: una fecha en la que no se cotizó nada, o en la que los únicos precios almacenados fueron arrastres, no es candidata, y en una fecha en la que solo algunas posiciones cotizaron, las otras se arrastran y siguen valoradas, así que el cierre se muestra en la medida de frescura.

    La pregunta *¿estos precios se cotizaron o se arrastraron?* sí tiene respuesta en el sistema, pero es la medida de frescura anterior, no la que un resultado lleva bajo el nombre de *cobertura*. Qué medida llega a cada pantalla concreta queda fuera de lo que describe esta página.

    Un discriminador lo resuelve sin ningún conocimiento del funcionamiento interno. **Cuando un resultado informa de `n_observations = 0` y `calendar_days = 0` junto a una cobertura distinta de cero, esa cobertura no es una afirmación sobre la densidad de datos.** No puede serlo: no se observó nada. Está informando de cuánto de la cartera se clasificó.

    La distinción cambia qué debería hacerse con el número. Una cobertura del 80%, leída con los dos primeros significados en mente, dice *falta una quinta parte de los precios*. En un ratio de clasificación dice que falta una quinta parte de las etiquetas de sector o geografía. Una es un hueco en los datos de mercado, la otra un hueco en los metadatos de activos, y las dos exigen acciones completamente distintas. Véase [Anualización observada](observed-annualization.md) para saber cómo el período y el recuento de observaciones también producen el factor de anualización.

---

## 🚫 Exclusiones {: #exclusions }

Un activo puede salir del análisis en dos momentos distintos, y la distinción se registra.

**Antes de intentar cualquier métrica**, cuando sus datos de origen no pueden sustentar ninguna: ningún precio utilizable, ninguna conversión de divisa utilizable, una divisa inválida. Estos se informan como activos no utilizables, cada uno con su motivo.

**Cuando se resuelve el alcance**, si el activo no tiene ninguna serie de rentabilidad preparada utilizable en absoluto. El alcance solicitado se reduce entonces a los activos que sobreviven, cada exclusión conserva su motivo, y una advertencia por cada motivo nombra exactamente qué activos se descartaron.

En ninguno de los dos casos el análisis se niega a ejecutarse: se ejecuta sobre lo que queda y lo dice. Un activo excluido es un cambio en *qué se midió*, por lo que fuerza a salir del estado limpio a todo resultado cuya medición cambió — y solo a esos.

### 🎯 Qué resultados conllevan una exclusión {: #which-results-carry-an-exclusion }

Una exclusión es un agujero en la serie por activo del alcance: la serie de rentabilidad de cada posición, alineada en el [calendario compartido](#alignment-what-missing-data-actually-costs). Todo resultado construido a partir de esas series la hereda — el activo se lista como excluido, la advertencia que lo nombra viaja con el resultado, y el resultado es `partial`. Eso cubre correlación, contribución al riesgo, riesgo/rentabilidad y la simulación; los KPI, el valor en riesgo y la comparación reproducidos sobre la composición actual, que son los pesos de hoy ejecutados sobre esas series; los análisis de un conjunto de activos elegidos directamente; y los análisis de una *rebanada* de una cartera, una selección de sus posiciones. Una rebanada no puede recortarse del propio historial de la cartera, así que incluso en el modo histórico se reproduce a partir de las series de las posiciones seleccionadas.

La excepción es el modo histórico de una cartera en su conjunto — todos sus brókers o una selección de ellos, pero no una rebanada de sus posiciones. Allí, cuatro analíticas leen el propio historial de rentabilidad de la cartera, su [rentabilidad ponderada por tiempo](../performance-metrics/portfolio-engine/twrr.md) (TWRR), en sus [días de observación](#coverage), en lugar de las series por activo: los KPI (volatilidad, Sharpe, Sortino, …), el [valor en riesgo](value-at-risk.md) histórico y el [VaR condicional](conditional-value-at-risk.md), la caída máxima, y la comparación contra un índice de referencia, que solo añade la propia serie del índice de referencia. Ese historial ya valora cada posición — una sin cotizaciones de mercado al precio de su última transacción — así que un activo ausente de las series por activo no cuesta nada en valor a estas cuatro: como mucho, los días en los que solo se cotizó ese activo dejan de ser días de observación, y sus rentabilidades se encadenan en el siguiente. No heredan ni la exclusión ni la advertencia que la nombra, ni la advertencia de que la parte de la composición actual contada a rentabilidad cero incluye valor en tránsito, una afirmación sobre una composición que nunca usan. La misma solicitud sigue informando de la exclusión en todo resultado que lea las series por activo. Lo que aún puede hacer que estas cuatro sean `partial` son los datos que hay detrás del propio historial de la cartera, y para la comparación la preparación de su índice de referencia — véase [Interpretación](#interpretation).

Las pruebas de estrés aplican reglas propias. Una [repetición histórica](historical-replay.md) prepara sus propias series sobre la ventana de su episodio, y deja fuera — por motivos propios, nombrados en sus propias advertencias — los activos que no puede valorar en ambos extremos de esa ventana. Un [choque hipotético](hypothetical-shock.md) no lee ninguna serie de rentabilidad: aplica sus choques a cada posición a través de la clasificación de la posición, así que una exclusión de las series por activo no le cuesta nada, y no hereda ni la exclusión ni su advertencia.

### 🏷️ Motivos de exclusión {: #exclusion-reasons }

Cada activo excluido conlleva un motivo, y cada motivo tiene su propia frase en la advertencia:

| Motivo | Por qué se dejó fuera el activo |
|---|---|
| `no_price_source` | No tiene asignada ninguna fuente de precios y nunca se ha registrado un precio para él. No hay nada configurado para ponerle precio, así que es un estado permanente y no un hueco en los datos — típicamente una inversión privada, como un préstamo de crowdfunding, que ningún mercado cotiza. |
| `missing_price` | Tiene una fuente de precios, o precios registrados, pero ningún precio utilizable para el período: la fuente no devolvió nada para él, o todos los precios registrados caen después del período. |
| `missing_fx` | Sus precios no pudieron convertirse a la moneda objetivo. |
| `invalid_currency` | Sus precios no llevan una divisa válida. |
| `insufficient_history` | No hay suficiente historial en el período para darle una serie de rentabilidad utilizable. |

Los precios registrados solo *antes* del período nunca causan una exclusión: el último de ellos se arrastra al período, como se describe en [Alineación](#alignment-what-missing-data-actually-costs). Solo el resultado distingue los dos primeros motivos: en su informe de datos de origen, un activo al que nada pone precio sigue listado entre los activos no utilizables como `missing_price`.

### ⚖️ El peso excluido {: #excluded-weight }

Los análisis de la composición actual que declaran pesos — contribución al riesgo y riesgo/rentabilidad — mantienen una posición excluida en su peso y la cuentan a rentabilidad cero: las cifras que calculan son exactamente las que daría el mismo dinero mantenido en efectivo. El resultado nombra esa parte por separado. `excluded_weight` es la suma de los pesos de las posiciones del alcance que quedaron sin serie, y se declara junto a `cash_weight`, el residual de rentabilidad cero: la parte del valor del alcance mantenida fuera de las posiciones que tienen serie — efectivo, cualquier valor en tránsito y las posiciones excluidas. En todo resultado que producen estos dos análisis, el peso excluido forma parte de ese residual. Los dos podrían no anidarse solo si las posiciones valieran más que el patrimonio neto — un saldo de efectivo negativo no compensado por valor en tránsito — y en ese caso ninguno de los dos análisis produce un resultado: vuelve `unavailable`. Las selecciones sin pesos, como un conjunto de activos elegidos directamente, no conllevan ninguno.

---

## 💡 Interpretación {: #interpretation }

Todo resultado analítico conlleva un estado propio, distinto del de los datos de origen:

| Estado del resultado | Significado |
|---|---|
| `ok` | Calculado sin nada faltante u obsoleto en sus datos de origen, nada excluido de lo que lee y ninguna advertencia degradante |
| `partial` | Calculado, pero con datos de origen faltantes u obsoletos, algo excluido de lo que lee, o una advertencia degradante |
| `unavailable` | No calculado; un código de motivo estable explica por qué (historial insuficiente, datos no disponibles, parámetros inválidos, un cálculo demasiado grande para ejecutarse, alcance o modo incompatibles, …) |
| `failed` | El cálculo se interrumpió por un error que la analítica no declara — un fallo del cálculo, nunca un veredicto sobre los datos. Conlleva el código `execution_failed` (*El cálculo del backend falló.*), el servidor lo registra, y la pantalla muestra **Cálculo fallido** |

Un fallo no es un valor indefinido. Una métrica que genuinamente no tiene valor para datos bien formados — la correlación de una serie que nunca se movió, un ratio de Sharpe sobre volatilidad cero — no falla: ese valor vuelve vacío, marcado como `undefined` en una celda de correlación o explicado por una advertencia como `sharpe_undefined`, y el resto del resultado sigue siendo utilizable. A la inversa, un error que la analítica no anticipó nunca se informa como una métrica indefinida: eso convertiría un fallo del cálculo en una afirmación sobre tus datos.

Un resultado es `partial` cuando se cumple **cualquiera** de estas condiciones: está presente una advertencia que degrada el resultado; un activo del alcance que el resultado lee fue [excluido](#which-results-carry-an-exclusion); la propia analítica excluyó algo; o el estado del informe de datos de origen sobre el que se juzga el resultado es distinto de `ok`. En el último caso también se adjunta una advertencia explícita, para que la degradación nunca se infiera solo del estado.

Ese informe es el de la serie que consumió el resultado:

- un resultado construido a partir de las series por activo del alcance — incluidos los KPI, las cifras de valor en riesgo, la caída máxima y la comparación cuando se reproducen desde esas series, sobre la composición actual o sobre una rebanada — se juzga con el informe de su preparación, fusionado, cuando el alcance es una cartera, con el propio informe de la cartera;
- sobre el TWRR de una cartera, los KPI, las cifras de valor en riesgo y la caída máxima se juzgan con el propio informe de datos de origen de la cartera: si el propio historial de la cartera está incompleto — una posición que no pudo valorarse, un tipo de cambio faltante, un día en el que el patrimonio neto no pudo valorarse por completo — siguen siendo `partial`, con la advertencia. Ese informe registra lo que no pudo valorarse, no cuán antigua es una valoración, así que un precio arrastrado más allá del umbral de antigüedad dentro del historial de la cartera no los degrada;
- la comparación contra un índice de referencia sobre el TWRR se juzga con el informe de la cartera más la preparación de su índice de referencia, que se alinea en el calendario compartido del alcance: un precio o un tipo de cambio en ese calendario arrastrado más allá del [umbral de antigüedad](#staleness-threshold) — del índice de referencia o de una posición — o una fecha perdida de él, todavía lo hace `partial`; las posiciones excluidas del alcance nunca entraron en ese calendario, así que su exclusión no lo hace.

!!! info "Cómo leer un resultado parcial"

    `partial` no significa *incorrecto*. Significa que la cifra conlleva una imperfección conocida: puede apoyarse en precios o tipos de cambio arrastrados más allá del umbral de antigüedad — misma ventana, mismas posiciones — o responder a una pregunta ligeramente distinta de la formulada, sobre un calendario con fechas incompletas o sobre menos posiciones. La cifra y el motivo viajan juntos en la misma carga útil, y están pensados para leerse juntos: una contribución al riesgo calculada con dos posiciones excluidas describe una cartera en la que esas dos se mantuvieron inmóviles, como efectivo — no la cartera tal como es.

Las analíticas también se niegan a responder en lugar de responder mal. Cada una declara el número mínimo de observaciones que necesita, y por debajo de ese mínimo no se calcula en absoluto: el resultado vuelve `unavailable` con un motivo `insufficient_history` que conlleva tanto las observaciones disponibles como el número requerido. La contribución al riesgo y la comparación contra un índice de referencia, por ejemplo, necesitan al menos 20. Las cifras de valor en riesgo cuentan sus ventanas compuestas por el horizonte en lugar de sus rentabilidades, así que un horizonte más largo necesita una ventana más larga — véase [valor en riesgo](value-at-risk.md#the-observation-count-is-not-the-history-length). [Correlación](correlation.md#how-each-cell-is-computed) es una excepción: nunca se rechaza por historial corto. Su mínimo — un parámetro ajustable del análisis, 20 observaciones por defecto — se aplica a la matriz en su conjunto: cada serie comparte un calendario, así que cada par tiene el mismo número de observaciones, y por debajo del mínimo cada celda vuelve `insufficient` sin coeficiente, en un resultado marcado como `partial` en lugar de `unavailable`.

---

## ⚠️ Limitaciones {: #limitations }

!!! warning "Un estado describe las entradas, no el modelo"

    `ok` dice que la serie estaba completa, no que la métrica sea apropiada, que la ventana sea lo bastante larga o que el pasado se parezca al futuro. Toda advertencia de las páginas de métricas sigue aplicándose a una cifra construida sobre datos impecables.

!!! warning "Los datos arrastrados favorecen una cifra de riesgo"

    Un precio arrastrado desde una fecha anterior produce una rentabilidad del período de exactamente cero en la moneda del propio instrumento; tras la conversión a la moneda objetivo, solo el tipo de cambio lo mueve. Todo precio arrastrado hace esto, por joven que sea, y esas rentabilidades entran en la muestra como cualquier otra observación. Dentro del [umbral de antigüedad](#staleness-threshold) eso es normal: durante un fin de semana, un festivo o un día en el que solo cotizó otro mercado, el instrumento no tuvo una nueva cotización, y su siguiente cotización se pone al día. Un precio arrastrado durante más tiempo sustituye a días en los que el instrumento bien podría haberse movido, así que una serie rica en tales puntos informa de **menos** movimiento del que realmente tuvo el instrumento. Esos son los puntos que cuenta el estado `carried_forward`, y el estado es la advertencia de que una cifra aparentemente tranquila puede estar tranquila por el motivo equivocado.

!!! warning "Una posición valorada a partir de sus operaciones permanece inmóvil"

    En el TWRR de una cartera, una posición a la que ningún mercado pone precio se valora a [el precio de su última transacción](../performance-metrics/portfolio-engine/price-resolution.md), así que en su propia moneda permanece inmóvil de una transacción a la siguiente. Para un préstamo mantenido a su valor nominal — una inversión típica de crowdfunding — eso es la verdad. Para una posición cuyo valor realmente se mueve, aplana todas las cifras leídas en el TWRR, igual que hace un precio arrastrado. Ningún estado lo señala: el informe de la cartera no cuenta una valoración a partir de operaciones en contra de su estado, y para una posición sin fuente de precios trata esa valoración como el estado previsto y permanente.

!!! warning "Ningún umbral de calidad descarta una cifra"

    Aparte de los recuentos mínimos de observaciones descritos arriba, por debajo de los cuales una analítica no se calcula en absoluto o cada celda de correlación vuelve `insufficient`, nada en el sistema declara una cobertura o una proporción de arrastrados más allá de la cual una cifra deba descartarse. Esa ausencia es deliberada — el número honesto es el que viene con su propia procedencia — pero significa que el juicio final es tuyo, y no puede delegarse en la etiqueta de estado.

---

## 🔗 Relacionado {: #related }

- 📅 **[Anualización observada](observed-annualization.md)** — el factor de anualización contado a partir de las mismas observaciones, y por qué una serie dispersa no es necesariamente una serie rota
- 🔗 **[Correlación](correlation.md)** — informa del recuento de observaciones detrás de cada celda
- 📊 **[Volatilidad](volatility.md)** — la cifra más directamente aplanada por los precios arrastrados
