# 🔬 Análisis de Lotes FIFO

El análisis de lotes FIFO es el complemento **por lote** del [precio medio ponderado (PMP)](../weighted-average-cost.md).

El PMP responde: _"¿Cuál es mi precio medio ponderado para esta posición?"_ El análisis de lotes FIFO responde una pregunta diferente: _"¿Cómo se está desempeñando cada lote de compra individual a lo largo del tiempo?"_

En lugar de fusionar todas las adquisiciones en un solo fondo común, LibreFolio rastrea cada lote a través de su propio ciclo de vida — **abierto**, **parcialmente cerrado**, **totalmente cerrado** — y empareja las ventas en orden **FIFO** (primero en entrar, primero en salir).

!!! info "Complemento, no reemplazo"

    El PMP es agregado y a nivel de posición. El análisis de lotes FIFO es granular y a nivel de lote. Ambas vistas son útiles: una para la base de costo combinada, otra para la atribución económica lote por lote.

---

## 💡 ¿Qué es el Análisis de Lotes FIFO?

Un **lote** es un lote de adquisición: por ejemplo, una COMPRA de 100 acciones, o una transferencia de entrada que conserva la base de costo histórica.

Cuando ocurre una VENTA, los lotes aún abiertos más antiguos se cierran primero. Esto crea un historial lote por lote:

- cuánto de cada lote sigue abierto
- cuánto ya se ha vendido
- cuánto producto de venta ha generado ese lote
- cuántos ingresos se obtuvieron mientras se mantuvo ese lote
- cuánto retorno provino del cambio de precio frente a los ingresos en efectivo

Esto hace que el análisis de lotes FIFO sea especialmente útil cuando dos posiciones del mismo activo se compraron a precios o fechas muy diferentes.

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-gantt-chart" alt="Cronología de Vida del Lote y Custodia — cada barra es un lote, coloreada por el bróker custodio, con grosor proporcional a la cantidad mantenida">
</div>

La cronología **Vida del Lote y Custodia** de arriba hace visible el ciclo de vida: cada barra es un lote, coloreada según el bróker que lo custodia actualmente, con un grosor proporcional a la cantidad aún mantenida en ese segmento. Una barra que termina a mitad del gráfico es un lote totalmente cerrado; una barra que llega a "hoy" sigue abierta.

---

## 🧮 Retorno Abierto por Lote

El **Retorno Abierto** aísla el movimiento **solo de precio** de un lote en relación con su precio de referencia de apertura.

$$
\text{RelativeReturn} = \frac{\text{MarketPrice}}{\text{ReferenceUnitPrice}} - 1
$$

En la práctica:

- si existe una cotización de mercado en la fecha de apertura del lote, esa cotización de apertura se convierte en `reference_unit_price`
- si el lote se abrió antes de la primera cotización de mercado disponible, el sistema recurre al costo de apertura del propio lote, escalado a las unidades de la cotización de mercado
- `reference_price_source` registra si la referencia fue `exact`, `fallback`, o `unavailable`

Esta métrica excluye dividendos, intereses y producto de venta realizado. Responde: _"¿Cuánto se ha movido el precio de mercado desde que se abrió este lote?"_

!!! tip "Fallback del precio de referencia"

    Cuando no existe una cotización de mercado para el día de apertura, LibreFolio utiliza el precio de adquisición del lote como base de referencia, escalado a la convención de cotización del activo. Esto evita retornos porcentuales engañosos en instrumentos cotizados por cada 100 unidades nominales.

    El fallback es $\text{OpeningUnitPrice}\times qbq$. Para `qbq = 100`, un bono comprado a `0.992` se compara con el eje de cotización de mercado como `99.20`, no como `0.992`.

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-wac-chart" alt="Gráfico PMP / Precio de Mercado — una burbuja por lote, coloreada por el bróker de apertura, dimensionada por el valor de apertura, trazada contra la línea de precio de mercado">
</div>

El gráfico **PMP / Precio de Mercado** traza cada lote como una burbuja contra la línea de precio de mercado: el color de la burbuja marca el bróker donde se abrió el lote, el tamaño de la burbuja escala con el valor de apertura del lote. Un lote valorado solo al costo (sin precio de mercado en tiempo real) se dibuja con un contorno discontinuo.

---

## 💰 Retorno Total por Lote

El **Retorno Total** es más amplio que el Retorno Abierto. Incluye el valor de mercado restante del lote, cualquier producto de venta ya realizado de ese lote, y cualquier ingreso asignado recibido mientras se mantuvo el lote.

El cálculo de lotes de LibreFolio utiliza estos componentes exactos:

$$
\text{OpeningValue} = \text{OriginalCost}
$$

$$
\text{Proceeds}(t) = \sum \text{Closure Proceeds} \text{ up to } t
$$

$$
\text{TotalValue}(t) = \text{OpenValue}(t) + \text{Proceeds}(t)
$$

$$
\text{PnL}(t) = \text{TotalValue}(t) - \text{OriginalCost}
$$

$$
\text{MarketPnL} = \text{PnL} - \text{RealizedPnL}
$$

$$
\text{RealizedPnL} = \sum \text{Closure Realized PnL}
$$

$$
\text{AssetIncome} = \sum_t \text{Income}_i(t)
$$

$$
\text{TotalPnL} = \text{MarketPnL} + \text{RealizedPnL} + \text{AssetIncome}
$$

Para el resumen escalar del lote, el porcentaje de retorno es:

$$
\text{TotalReturn} = \frac{\text{TotalPnL}}{\text{OpeningValue}}
$$

Para el historial de retorno a lo largo del tiempo, LibreFolio utiliza:

$$
\text{TotalReturn}(t) = \frac{\text{TotalValue}(t) + \text{Income}(t)}{\text{OriginalCost}} - 1
$$

Esto responde: _"¿Cuál es el retorno económico completo de este lote, incluyendo tanto el movimiento de precio como el rendimiento en efectivo?"_

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" alt="Gráfico comparativo Valor / Retorno en modo Retorno — porcentaje de retorno por lote desde la fecha de apertura de cada lote">
</div>

El gráfico comparativo **Valor / Retorno**, cambiado al modo **Retorno**, traza exactamente este porcentaje — una línea por lote, cada una medida desde su propia fecha de apertura, sobre el conjunto de lotes seleccionado actualmente.

---

## ⚙️ Escalado qbq

Algunos instrumentos se cotizan **por cantidad base**, no por unidad individual. LibreFolio llama a esta cantidad base `qbq` (`quote_base_quantity`).

- Para la mayoría de las acciones, `qbq = 1`
- Para muchos bonos, `qbq = 100`

La regla exacta de valoración es:

$$
\text{HoldingValue}(qty, price, qbq) = \left(\frac{qty}{qbq}\right)\cdot price
$$

$$
\text{OpenValue}(t) = \left(\frac{\text{OpenQuantity}(t)}{qbq}\right)\cdot \text{MarketPrice}(t)
$$

!!! warning "El escalado qbq importa"

    Supongamos que un bono tiene una cantidad nominal de 1.000 y se cotiza a **101,50 por cada 100 nominales**.

    - `qbq = 100`
    - cantidad del lote = `1.000`
    - valor de mercado = `(1.000 / 100) × 101,50 = 1.015,00`

    Si se compara `101,50` directamente con una base de costo por unidad individual como `0,992`, se obtiene un resultado absurdo porque los dos números viven en escalas diferentes.

    La comparación correcta reescala el costo del lote al eje de cotización de mercado:

    $$
    0,992 \times 100 = 99,20
    $$

    Por lo tanto, la comparación de precios significativa es **101,50 vs 99,20**, no **101,50 vs 0,992**.

Sin este escalado, los retornos y valoraciones de bonos pueden desviarse por órdenes de magnitud.

---

## 🛟 Estimado al Costo {: #estimated-at-cost }

Si no hay un precio de mercado en tiempo real disponible para un activo, LibreFolio **no** interrumpe el análisis. En su lugar, valora temporalmente la porción aún abierta del lote al costo:

$$
\text{OpenValue} = \text{OpeningValue}\cdot \frac{\text{OpenQuantity}}{\text{OriginalQuantity}}
$$

$$
\text{MarketPnL} = 0
$$

Implicaciones prácticas:

- el lote aún muestra valor residual
- el producto de venta ya realizado sigue siendo visible
- los dividendos o intereses asignados siguen siendo visibles
- **la volatilidad no realizada se subestima temporalmente**
- `value_source = ESTIMATED_AT_COST`
- `market_pnl = 0`
- código de problema de calidad de datos: `CURRENT_PRICE_ASSUMED_AT_COST`

!!! info "Interpretación"

    El estimado al costo es un fallback operativo conservador. Significa: _"Sabemos lo que pagó, pero actualmente no sabemos lo que el mercado pagaría."_

La advertencia de calidad de datos correspondiente es una declaración **a la fecha de valoración**. No es una unión histórica de todos los días en que un activo fue valorado al costo.

---

## 💸 Asignación de Ingresos entre Lotes {: #income-allocation-across-lots }

Los dividendos e intereses vinculados a un activo se asignan **de forma prorrateada entre los lotes LONG que son elegibles al cierre del día anterior a la fecha del ingreso (D-1)**, y solo entre los lotes mantenidos **en el bróker pagador**.

Regla exacta de asignación:

$$
w_i(D) = \frac{\text{EligibleQty}_i(D)}{\sum_j \text{EligibleQty}_j(D)}, \qquad
\text{EligibleQty}_i(D) = \text{OpenQty}_i(D-1)
$$

$$
\text{Income}_i = \text{Convert}(I, ccy, D)\cdot w_i(D)
$$

Donde:

- $I$ = monto del ingreso recibido en la fecha $D$
- $\text{Convert}(I, ccy, D)$ = ingreso convertido a la moneda objetivo en la fecha $D$
- $\text{EligibleQty}_i(D)$ = cantidad del lote $i$ abierta en el **bróker pagador** en $D-1$ (la cantidad que salió de ese bróker en tránsito aún cuenta como originada allí)
- solo los lotes LONG participan en el denominador

La regla D-1 mantiene intacto el día de registro: una compra realizada *en* la fecha del ingreso no devenga esa distribución, y un lote vendido el día anterior tampoco. Los lotes elegibles más grandes reciben una porción mayor; los lotes mantenidos en otros brókers, o que aún no son (o ya no son) elegibles, no reciben nada.

!!! warning "Cambiado en FIFO v5"

    Las versiones anteriores utilizaban la fecha del ingreso en sí misma con todos los brókers ($\text{OpenQty}_i(t)$ sobre cada lote). El motor actual utiliza la elegibilidad D-1 limitada al bróker pagador. Si ningún lote es elegible, el ingreso se mantiene como **ingreso huérfano a nivel de activo** (nunca se descarta, nunca se asigna al lote equivocado).

!!! tip "Regla de conservación"

    Los montos asignados a los lotes suman exactamente el total del evento de ingreso convertido. El ingreso se distribuye, no se crea.

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-custody-modal" alt="Modal de detalle del lote — la fila de Ingresos del Activo muestra el dividendo/interés prorrateado asignado a este lote específico, junto con la insignia Estimado al Costo cuando no hay precio de mercado en tiempo real disponible">
</div>

La fila **Ingresos del Activo** del modal de detalle del lote es exactamente $\text{Income}_i$ de la fórmula anterior — la porción prorrateada que recibió este lote específico. Cuando el lote no tiene precio de mercado en tiempo real, el mismo modal también muestra la insignia **Estimado al Costo** de la sección anterior.

---

## 💸 Costos y Métricas Netas {: #costs-and-net-metrics }

Los `FEE` y `TAX` vinculados al activo se asignan a los lotes con una **secuencia determinista de emparejamiento de operaciones**, y luego se restan para producir cifras **netas** junto con las brutas.

### 🧭 Asignación determinista de costos

Un **conjunto de costos** (mismo bróker, mismo día, mismo tipo) se empareja con el primer objetivo no vacío en este orden:

| Costo | Orden de emparejamiento |
|------|----------------|
| `FEE` | operaciones del mismo día → operaciones del día anterior → posiciones abiertas → huérfano del activo |
| `TAX` | ingresos del mismo día → operaciones del mismo día → ingresos del día anterior → operaciones del día anterior → posiciones abiertas → huérfano del activo |

Dentro de una operación emparejada, el costo **se imputa exactamente a los lotes que la operación tocó** — el costo de una COMPRA recae en el lote que abrió, el costo de una VENTA recae en los lotes consumidos por FIFO — por lo que la atribución de costos nunca contradice el propio emparejamiento FIFO. Los montos se convierten a la moneda objetivo y se almacenan como magnitudes positivas.

!!! tip "Conservación"

    Por **conjunto de costos**, $\sum_i \text{Cost}_i + \text{Orphan} = \text{Convert}(\text{pool}, ccy, D)$. Un costo que no encuentra ningún lote elegible (por ejemplo, una comisión contabilizada después de que la posición se haya cerrado por completo) se convierte en **costo huérfano a nivel de activo** en lugar de descartarse o forzarse sobre un lote no relacionado.

### ⚖️ Bruto vs neto

Con los costos atribuidos por lote, LibreFolio reporta tanto el rendimiento bruto como el neto:

$$
\text{NetTotalPnL}_i = \text{TotalPnL}_i - \text{Fees}_i - \text{Taxes}_i
$$

$$
\text{NetTotalReturn}_i = \frac{\text{NetTotalPnL}_i}{\text{OpeningValue}_i}
$$

donde $\text{TotalPnL}_i$ ya **incluye** ingresos (P&L de mercado + P&L realizado + ingresos del activo). La serie de historial de valor por lote, en cambio, reporta un P&L neto *solo de capital*, $\text{pnl}_i - \text{Fees}_i - \text{Taxes}_i$, que **excluye** ingresos — cada línea neta refleja su equivalente bruto menos los costos.

El retorno anualizado del lote utiliza el retorno **neto**, no el bruto:

$$
\mathrm{AnnualizedReturn}_i =
\left(1+\mathrm{NetTotalReturn}_i\right)^{365/d_i}-1
$$

con $d_i$ desde la fecha de apertura hasta la fecha de cierre para lotes cerrados, o hasta la fecha final del análisis para lotes abiertos. Los periodos inferiores a 30 días no devuelven ningún valor anualizado; consulte [Retorno Anualizado Neto](../portfolio-engine/net-annualized-return.md).

!!! example "Números canónicos"

    COMPRA 10×100, VENTA 4×120, precio actual 110, dividendo 50, comisiones 8, impuestos 5:
    P&L Total Bruto $= 60 + 80 + 50 = 190$; P&L Total Neto $= 190 - 13 = 177$; sobre un valor de apertura de 1000, eso es un
    **19 %** bruto frente a un **17,7 %** neto de retorno total.

Los costos con `asset_id = null` **no** forman parte de esta vista a nivel de lote — son a nivel de cartera y los gestiona el [Motor de Cartera](../portfolio-engine/roi.md). Consulte [Comisión e Impuesto](../../../instruments/transaction-types/fee.md) para la teoría a nivel de instrumento.

---

## 📝 Ejemplo Resuelto

??? example "Ejemplo: dos lotes, un dividendo, un precio de mercado"

     Supongamos la misma acción, la misma moneda, `qbq = 1`.

     | Fecha | Evento | Lote A Cant. Abierta | Lote B Cant. Abierta | Notas |
     |------|-------|----------------|----------------|-------|
     | Ene 2 | COMPRA 100 @ $10 | 100 | 0 | El lote A se abre con un costo original de $1.000 |
     | Feb 10 | COMPRA 50 @ $14 | 100 | 50 | El lote B se abre con un costo original de $700 |
     | Mar 15 | DIVIDENDO $30 | 100 | 50 | Ambos lotes siguen abiertos |
     | Abr 1 | Precio de mercado = $16 | 100 | 50 | Evaluar ambos lotes |

     **Paso 1 — Asignar el dividendo prorrateado**

     $$
     w_A = \frac{100}{100 + 50} = \frac{2}{3}
     \qquad
     w_B = \frac{50}{100 + 50} = \frac{1}{3}
     $$

     $$
     \text{Income}_A = 30 \times \frac{2}{3} = 20
     \qquad
     \text{Income}_B = 30 \times \frac{1}{3} = 10
     $$

     **Paso 2 — Retorno abierto para cada lote**

     $$
     \text{RelativeReturn}_A = \frac{16}{10} - 1 = 60,00\%
     $$

     $$
     \text{RelativeReturn}_B = \frac{16}{14} - 1 \approx 14,29\%
     $$

     **Paso 3 — Valor de mercado y retorno total**

     $$
     \text{OpenValue}_A = 100 \times 16 = 1.600
     \qquad
     \text{OpenValue}_B = 50 \times 16 = 800
     $$

     Como aún no se han vendido acciones, el producto de venta y el P&L realizado son ambos cero.

     $$
     \text{TotalPnL}_A = (1.600 - 1.000) + 20 = 620
     $$

     $$
     \text{TotalReturn}_A = \frac{620}{1.000} = 62,00\%
     $$

     $$
     \text{TotalPnL}_B = (800 - 700) + 10 = 110
     $$

     $$
     \text{TotalReturn}_B = \frac{110}{700} \approx 15,71\%
     $$

     **Paso 4 — Retorno agregado entre los lotes mostrados**

     $$
     \text{AggregateReturn} = \frac{620 + 110}{1.000 + 700} = \frac{730}{1.700} \approx 42,94\%
     $$

     Aunque ambos lotes pertenecen al mismo activo, sus retornos difieren porque se abrieron a precios diferentes.

---

## 📚 De Lotes a Métricas Agregadas

Los retornos a nivel de lote se pueden agrupar en una serie de retorno agregado, pero **los porcentajes no deben sumarse directamente**.

LibreFolio utiliza esta regla agregada exacta entre los lotes mostrados:

$$
\text{AggregatePnL}(t) = \sum_i \left(\text{PnL}_i(t) + \text{Income}_i(t)\right)
$$

$$
\text{AggregateOpeningValue}(t) = \sum_i \text{OriginalCost}_i
$$

$$
\text{AggregateReturn}(t) = \frac{\text{AggregatePnL}(t)}{\text{AggregateOpeningValue}(t)}
$$

Esta vista a nivel de lote ayuda a explicar **de dónde** provino el retorno. Las métricas de nivel superior como [ROI](../portfolio-engine/roi.md) y [TWRR](../portfolio-engine/twrr.md) responden preguntas más amplias de la cartera:

- **ROI** se centra en la ganancia relativa al capital invertido
- **TWRR** neutraliza el momento de los flujos de efectivo externos
- El análisis de lotes FIFO explica la contribución y la trayectoria **dentro** de una posición

La búsqueda de precios está deliberadamente fuera del motor FIFO en sí. El motor produce lotes y cierres; `LotsAnalysisService` aplica el resolvedor unificado ([Resolución de Precios](../portfolio-engine/price-resolution.md)) y el fallback de estimado al costo al derivar las métricas de valoración.

<div class="screenshot-container">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-table" alt="Tabla Unificada de Lotes — una fila por lote con fecha de apertura, retorno total, valor actual, custodia y estado, las filas exactas por lote que las fórmulas agregadas anteriores suman">
</div>

La **Tabla Unificada de Lotes** enumera exactamente las filas por lote $i$ sobre las que suman las fórmulas agregadas anteriores — fecha de apertura, retorno total, valor actual, custodia y estado, todo filtrable al mismo conjunto de lotes visible utilizado por los gráficos.

---

## 🔗 Relacionados

- 📊 **[Precio Medio Ponderado (PMP)](../weighted-average-cost.md)** — vista de base de costo combinada
- 🔁 **[Compra y Venta](../../../instruments/transaction-types/buy-sell.md#fifo-matching)** — breve descripción general del emparejamiento FIFO
- 💸 **[Dividendo e Interés](../../../instruments/transaction-types/dividend-interest.md)** — fuente de los eventos de ingresos vinculados al activo
- 💰 **[Tributación](../../../fundamentals/taxation.md)** — contexto de plusvalías y emparejamiento de lotes
- ⚙️ **[Servicio de Análisis de Lotes](../../../../developer/backend/transactions/lots_analysis_service.md)** — inmersión profunda en la implementación para desarrolladores
