# 🔬 Análisis de Lotes FIFO

El análisis de lotes FIFO es el complemento **por lote** del [Precio Medio de Compra (PMC)](../weighted-average-cost.md).

PMC responde: _"¿Cuál es mi coste medio combinado para esta posición?"_ El análisis de lotes FIFO responde a una pregunta distinta: _"¿Cómo se está comportando cada lote de compra individual a lo largo del tiempo?"_

En lugar de fusionar todas las adquisiciones en un único conjunto, LibreFolio rastrea cada lote a través de su propio ciclo de vida — **abierto**, **parcialmente cerrado**, **totalmente cerrado** — y empareja las ventas en orden **FIFO** (primero en entrar, primero en salir).

!!! info "Complemento, no sustituto"

    PMC es agregado y a nivel de posición. El análisis de lotes FIFO es granular y a nivel de lote. Ambas vistas son útiles: una para el coste base combinado, otra para la atribución económica lote a lote.

---

## 💡 ¿Qué es el Análisis de Lotes FIFO?

Un **lote** es una tanda de adquisición: por ejemplo, una única compra de 100 acciones, o una transferencia entrante que conserva el coste base histórico.

Cuando se produce una venta, se cierran primero los lotes más antiguos que siguen abiertos. Esto crea un historial lote a lote:

- cuánto de cada lote sigue abierto
- cuánto se ha vendido ya
- cuánto importe de venta ha generado ese lote
- cuántos ingresos se obtuvieron mientras se mantenía ese lote
- cuánto retorno provino del cambio de precio frente a los ingresos en efectivo

Esto hace que el análisis de lotes FIFO sea especialmente útil cuando dos posiciones del mismo activo se compraron a precios o fechas muy diferentes.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-gantt-chart" alt="Línea de tiempo Vida y custodia del lote: cada barra es un lote, coloreada según el bróker custodio, con grosor proporcional a la cantidad mantenida">
</div>

La línea de tiempo **Vida y custodia del lote** anterior hace visual el ciclo de vida: cada barra es un lote, coloreada según el bróker que lo mantiene actualmente, con un grosor proporcional a la cantidad aún mantenida en ese segmento. Una barra que termina a mitad del gráfico es un lote totalmente cerrado; una barra que llega hasta «hoy» sigue abierta.

---

## 🧮 Retorno Abierto por Lote

El **Retorno Abierto** aísla el movimiento **solo de precio** de un lote respecto a su precio de referencia de apertura.

$$
\text{RelativeReturn} = \frac{\text{MarketPrice}}{\text{ReferenceUnitPrice}} - 1
$$

$\text{MarketPrice}$ es el precio de valoración del activo procedente del [resolutor unificado](../portfolio-engine/price-resolution.md): en la fecha final para el resumen del lote, en cada día para el historial de retorno. La referencia depende de qué abrió el lote:

- **Una operación** —una compra, o una venta que abre un lote corto—: el precio unitario del propio lote, incluso cuando el activo tiene una cotización de mercado ese día. Una operación es un precio.
- **Un ajuste** —una posición de apertura, una sucesión, una transferencia desde un bróker no rastreado—: su coste base es un coste, no un precio, por lo que la referencia es el precio de valoración del activo en el día de apertura. Esto es, el precio del último día igual o anterior a ese que tenga uno —su cotización de mercado o, sin cotización, el precio medio de sus operaciones de compra y venta, nunca un ajuste— arrastrado. Para un activo que aún no tiene nada más, el coste de una transferencia entrante es también un precio de ese tipo, como [estimación](../portfolio-engine/price-resolution.md#transfer-cost-estimate): una transferencia desde un bróker fuera del alcance, sobre un activo sin cotización y sin otra operación en esa fecha o antes, obtiene su propio coste como referencia, marcado como fallback (`REFERENCE_PRICE_FALLBACK`).
- **Un ajuste antes de cualquier precio** —sin cotización, compra, venta ni estimación de coste de transferencia en la fecha de apertura o antes—: el precio unitario del propio lote, su coste base por unidad. Sin coste base, ese precio es cero, y el lote no tiene Retorno Abierto.

`reference_price_source` es `exact` para una cotización de mercado del propio día de apertura y para el precio del propio lote, y `fallback` para una cotización arrastrada desde un día anterior o un precio derivado de operaciones. El banner de calidad de datos informa de tal fallback (`REFERENCE_PRICE_FALLBACK`), y de un ajuste sin precio en la fecha de apertura o antes (`REFERENCE_PRICE_UNAVAILABLE`).

Cada precio se convierte a la divisa objetivo al tipo de cambio de su propio día: $\text{MarketPrice}$ al tipo del día que valora, la referencia al tipo de la fecha de apertura, incluso cuando se arrastró desde una cotización u operación anterior. Por tanto, para un precio en una divisa distinta de la objetivo, el Retorno Abierto incluye el movimiento del tipo de cambio desde la apertura.

Esta métrica excluye dividendos, intereses e importes de venta realizados. Responde: _"¿Cuánto se ha movido el precio de mercado desde que se abrió este lote?"_

!!! example "Un lote recibido por sucesión"

    Un activo cotiza a 50 el 7 de marzo y se compra a 52 el 9 de marzo, sin cotización desde entonces. Un lote recibido por sucesión el 10 de marzo tiene una referencia de **52**: la compra es el precio más reciente del activo en esa fecha o antes, arrastrado. Su `reference_price_source` es `fallback`, ya que 52 no es una cotización del 10 de marzo; una cotización del propio 10 de marzo sería la referencia, con `exact`.

!!! tip "El precio del propio lote, en el eje de cotización"

    Cuando la referencia es el precio del propio lote, LibreFolio lo escala a la convención de cotización del activo. Esto evita retornos porcentuales engañosos en instrumentos cotizados por 100 unidades nominales. Un precio de valoración procedente del resolutor ya está en ese eje.

    La referencia es entonces $\text{OpeningUnitPrice}\times qbq$. Para `qbq = 100`, un bono comprado a `0,992` se compara contra el eje de cotización de mercado como `99,20`, no como `0,992`.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-wac-chart" alt="Gráfico PMC / Precio de mercado: una burbuja por lote, coloreada según el bróker de apertura, dimensionada por el valor de apertura, trazada frente a la línea de precio de mercado">
</div>

El gráfico **PMC / Precio de mercado** traza cada lote como una burbuja frente a la línea de precio de mercado: el color de la burbuja marca el bróker donde se abrió el lote, el tamaño de la burbuja se escala con el valor de apertura del lote. Un lote cuyo valor actual se estima a coste —su activo no tiene ningún precio en la fecha final, véase [Estimado a coste](#estimated-at-cost)— se dibuja con un contorno discontinuo.

---

## 💰 Retorno Total por Lote

El **Retorno Total** es más amplio que el Retorno Abierto. Incluye el valor de mercado restante del lote, cualquier importe de venta ya realizado de ese lote —un ajuste saliente no añade ninguno, al no tener valor— y cualquier ingreso asignado recibido mientras se mantenía el lote.

Los cálculos de lotes de LibreFolio usan exactamente estos componentes:

$$
\text{OpeningValue} = \text{OriginalCost}
$$

$$
\text{Proceeds}(t) = \sum \text{Closure Proceeds} \text{ hasta } t
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

Cada importe está en la divisa objetivo del análisis. Para un lote comprado o vendido en otra divisa, cada cierre convierte sus dos tramos en sus propias fechas; véase [Lotes en Otra Divisa](#lots-in-another-currency).

Para el resumen escalar del lote, el porcentaje de retorno es:

$$
\text{TotalReturn} = \frac{\text{TotalPnL}}{\text{OpeningValue}}
$$

Para el historial de retorno a lo largo del tiempo, LibreFolio usa:

$$
\text{TotalReturn}(t) = \frac{\text{TotalValue}(t) + \text{Income}(t)}{\text{OriginalCost}} - 1
$$

Esto responde: _"¿Cuál es el retorno económico completo de este lote, incluyendo tanto el movimiento del precio como el rendimiento en efectivo?"_

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" alt="Gráfico de comparación Valor / Retorno en modo Retorno: retorno porcentual por lote desde la fecha de apertura de cada lote">
</div>

El gráfico de comparación **Valor / Retorno**, cambiado al modo **Retorno**, traza exactamente este porcentaje: una línea por lote, cada una medida desde su propia fecha de apertura, sobre el conjunto de lotes seleccionado actualmente.

### 💱 Lotes en Otra Divisa {: #lots-in-another-currency }

Los dos tramos de un cierre se convierten a la divisa objetivo **cada uno en su propia divisa, en su propia fecha**: el coste de las unidades en la divisa del lote en la fecha de apertura del lote —el tipo de compra— y el precio de cierre en la divisa de la transacción de cierre en la fecha de cierre —el tipo de venta—. Con $\text{Convert}(x, ccy, D)$ el importe $x$ en la divisa $ccy$ convertido a la divisa objetivo al tipo de la fecha $D$, un cierre de $q$ unidades de un lote largo abierto en $D_{\text{open}}$ a $\text{LotUnitCost}$ en $ccy_{\text{lot}}$, y cerrado en $D_{\text{close}}$ a $\text{ClosePrice}$ en $ccy_{\text{close}}$, da:

$$
\text{Closure Proceeds} = \text{Convert}\left(q \cdot \text{ClosePrice},\ ccy_{\text{close}},\ D_{\text{close}}\right)
$$

$$
\text{Closure Cost} = \text{Convert}\left(q \cdot \text{LotUnitCost},\ ccy_{\text{lot}},\ D_{\text{open}}\right)
$$

$$
\text{Closure Realized PnL} = \text{Closure Proceeds} - \text{Closure Cost}
$$

$\text{ClosePrice}$ es el precio unitario de una venta, en la divisa de la venta, o cero, en la divisa del lote, para un ajuste saliente, que no tiene valor (véase [Ajustes Salientes](../../../instruments/transaction-types/adjustment.md#outgoing-adjustments)). $ccy_{\text{close}}$ no tiene por qué ser $ccy_{\text{lot}}$: un lote trasladado a un bróker de otra divisa y vendido allí convierte la venta desde esa divisa. Un lote corto refleja la regla: realiza el importe de su venta de apertura, $\text{Convert}(q \cdot \text{LotUnitCost}, ccy_{\text{lot}}, D_{\text{open}})$, menos el coste de la compra que lo cierra, $\text{Convert}(q \cdot \text{ClosePrice}, ccy_{\text{close}}, D_{\text{close}})$.

Cuando un lote se compra y se vende en una sola divisa, con tipos $r_{\text{open}}$ y $r_{\text{close}}$ en las dos fechas, su resultado realizado se divide en la ganancia de precio al tipo de venta y el movimiento del tipo de cambio sobre el coste de las unidades vendidas:

$$
\text{Closure Realized PnL} = q\,(\text{ClosePrice} - \text{LotUnitCost})\,r_{\text{close}} + q\,\text{LotUnitCost}\,(r_{\text{close}} - r_{\text{open}})
$$

El movimiento del tipo de cambio entre compra y venta se realiza, por tanto, con las unidades, como en el panel, donde el importe de una venta se convierte en su fecha y las unidades salen a su coste histórico (véase [PMC](../weighted-average-cost.md)). Un tipo de cambio ausente deja el P&L realizado del cierre como desconocido, y con él el $\text{RealizedPnL}$ del lote: nunca se calcula a partir de los importes nativos.

El coste de cada cierre se convierte en la fecha de apertura, igual que $\text{OriginalCost}$, de modo que el P&L de mercado de un lote largo es el valor de sus unidades abiertas menos su coste al tipo de compra:

$$
\text{MarketPnL} = \text{PnL} - \text{RealizedPnL} = \text{OpenValue} - \left(\text{OriginalCost} - \sum \text{Closure Cost}\right)
$$

Un lote largo totalmente cerrado no tiene P&L de mercado: los costes de sus cierres suman su $\text{OriginalCost}$, y todo su P&L está realizado.

!!! example "Un lote en dólares, divisa objetivo EUR"

    Comprar 1 unidad a 100 USD cuando 1 USD = 1,00 EUR; venderla a 110 USD cuando 1 USD = 0,90 EUR.

    $$
    \text{Closure Proceeds} = 110 \times 0{,}90 = 99 \text{ EUR}
    \qquad
    \text{Closure Cost} = 100 \times 1{,}00 = 100 \text{ EUR}
    $$

    $$
    \text{RealizedPnL} = 99 - 100 = -1 \text{ EUR}
    \qquad
    \text{MarketPnL} = \text{PnL} - \text{RealizedPnL} = (99 - 100) - (-1) = 0
    $$

    La ganancia de precio, $10 \times 0{,}90 = +9$ EUR, queda superada por la caída del dólar sobre el coste, $100 \times (0{,}90 - 1{,}00) = -10$ EUR. Convertir el P&L realizado nativo, 10 USD, al tipo de venta reportaría en cambio $+9$ EUR realizados y $-10$ EUR de P&L de mercado sobre un lote que ya no se mantiene; el total, $-1$ EUR, es el mismo de una u otra forma.

---

## ⚙️ Escalado qbq

Algunos instrumentos se cotizan **por cantidad base**, no por unidad individual. LibreFolio llama a esta cantidad base `qbq` (`quote_base_quantity`).

- Para la mayoría de acciones, `qbq = 1`
- Para muchos bonos, `qbq = 100`

La regla exacta de valoración es:

$$
\text{HoldingValue}(qty, price, qbq) = \left(\frac{qty}{qbq}\right)\cdot price
$$

$$
\text{OpenValue}(t) = \left(\frac{\text{OpenQuantity}(t)}{qbq}\right)\cdot \text{MarketPrice}(t)
$$

!!! warning "El escalado qbq importa"

    Supongamos que un bono tiene una cantidad nominal de 1.000 y se cotiza a **101,50 por 100 nominales**.

    - `qbq = 100`
    - cantidad del lote = `1.000`
    - valor de mercado = `(1.000 / 100) × 101,50 = 1.015,00`

    Si comparas `101,50` directamente con un coste base por unidad individual como `0,992`, obtienes un sinsentido porque los dos números viven en escalas diferentes.

    La comparación correcta reescala el coste del lote al eje de cotización de mercado:

    $$
    0{,}992 \times 100 = 99{,}20
    $$

    Así, la comparación de precios significativa es **101,50 vs 99,20**, no **101,50 vs 0,992**.

Sin este escalado, los retornos y valoraciones de los bonos pueden desviarse en órdenes de magnitud.

---

## 🛟 Estimado a coste {: #estimated-at-cost }

Cada día, un lote se valora con el precio de valoración del activo procedente del [resolutor unificado](../portfolio-engine/price-resolution.md): una cotización de mercado, o el precio medio de las operaciones de compra y venta de un día, arrastrado. Un ajuste nunca es un precio, con o sin coste base; el coste de una transferencia entrante lo es solo como [estimación](../portfolio-engine/price-resolution.md#transfer-cost-estimate), mientras el activo no tenga cotización ni otra operación en esa fecha o antes. Un día **sin ningún precio** —sin cotización de mercado, sin compra ni venta y sin tal estimación en esa fecha o antes— **no** hace fallar el análisis: LibreFolio valora ese día a coste la porción aún abierta de un lote largo, la regla día a día que aplica el panel a una posición sin precio:

$$
\text{OpenValue}(t) = \text{OpeningValue}\cdot \frac{\text{OpenQuantity}(t)}{\text{OriginalQuantity}}
$$

$$
\text{MarketPnL}(t) = 0
$$

siendo $\text{OpeningValue}$ el coste original del lote convertido en su fecha de apertura. La elección se hace día a día, sin mirar hacia adelante. Un precio, una vez observado, se arrastra, por lo que estos días son todos anteriores a la primera cotización, compra, venta o estimación de coste de transferencia del activo: van desde la primera transacción del análisis hasta el día anterior a ese primer precio, o hasta la fecha final cuando el activo no tiene ninguno —y no hay ninguno cuando el activo ya tiene un precio el día de la primera transacción.

- **Antes del primer precio.** Un lote abierto antes del primer precio del activo —por un ajuste, por ejemplo— se valora a coste desde su apertura hasta el día anterior a ese precio, incluso cuando el activo cotiza después: su línea de valor se mantiene plana a coste, sin ganancia ni pérdida de mercado, y luego sigue el precio.
- **Ningún precio en absoluto.** Un activo sin cotización, compra, venta ni estimación de coste de transferencia hasta la fecha final —uno mantenido solo mediante ajustes, o mediante transferencias sin coste base— se valora a coste todos los días, y el resumen del lote informa `value_source = ESTIMATED_AT_COST`. Con un precio en la fecha final o antes, el resumen valora el lote a ese precio: `value_source = MARKET_PRICE`, la etiqueta de cualquier precio de valoración, cotización, operación o estimación de coste de transferencia. Un activo que llegó solo mediante transferencias con coste base no tiene, por tanto, ningún día a coste: desde su primera transferencia se valora a ese coste, convertido al tipo de cambio de cada día, y las series de precios tienen un punto para él, marcado como estimado.
- **Un precio sin tipo de cambio.** Un día cuya valoración no tiene tipo de cambio a la divisa objetivo no se valora a coste: un lote aún abierto no tiene valor ese día, y en la fecha final el resumen del lote no tiene valor ni `value_source`.
- **Un ajuste sin coste base.** Un ajuste sin coste, como una donación o una escisión, abre un lote de coste cero, y ese lote vale 0 en los días valorados a coste hasta que llegue un precio. Cuenta como cero en esos días, mientras que el coste medio del panel trata ese coste como desconocido y deja la posición sin valorar. Tal fila es rara: un [ajuste](../../../instruments/transaction-types/adjustment.md) positivo puede guardarse sin coste base solo mientras está vinculado a un desdoblamiento, y entonces no abre ningún lote, por lo que procede de una versión anterior, o de una cuyo evento de desdoblamiento se cambió después a un ajuste de precio.

Implicación práctica, en los días valorados a coste:

- el lote sigue mostrando valor residual
- los importes de venta ya realizados siguen siendo visibles
- los dividendos o intereses asignados siguen siendo visibles
- **la volatilidad no realizada se subestima temporalmente**
- `market_pnl = 0`, y sin Retorno Abierto: no hay precio de mercado con el que comparar la referencia
- sin ROI ni TWRR en el historial de rendimiento de lotes, que solo lee los días con precio

!!! info "Interpretación"

    La estimación a coste es un mecanismo fallback operativo conservador. Significa: _"Sabemos lo que pagaste, pero actualmente no sabemos lo que pagaría el mercado."_

La advertencia de calidad de datos `CURRENT_PRICE_ASSUMED_AT_COST` —*«No hay precio de mercado disponible entre {date_from} y {date_to} — valor abierto estimado a coste, P&L de mercado excluido»*— nombra exactamente esos días: desde la primera transacción hasta el día anterior al primer precio del activo, o hasta la fecha final cuando el activo no tiene ninguno. Se emite siempre que existan tales días y se solicite el resumen del lote o el historial de valor, retorno, precio o rendimiento.

---

## 💸 Asignación de Ingresos entre Lotes {: #income-allocation-across-lots }

Los dividendos e intereses vinculados a un activo se asignan **a prorrata entre los lotes largos elegibles con fecha del día anterior a la fecha del ingreso (D-1)**, y solo entre los lotes mantenidos **en el bróker pagador**.

Regla exacta de asignación:

$$
w_i(D) = \frac{\text{EligibleQty}_i(D)}{\sum_j \text{EligibleQty}_j(D)}, \qquad
\text{EligibleQty}_i(D) = \text{OpenQty}_i(D-1)
$$

$$
\text{Income}_i = \text{Convert}(I, ccy, D)\cdot w_i(D)
$$

Donde:

- $I$ = importe del ingreso recibido en la fecha $D$
- $\text{Convert}(I, ccy, D)$ = ingreso convertido a la divisa objetivo en la fecha $D$
- $\text{EligibleQty}_i(D)$ = cantidad del lote $i$ abierta en el **bróker pagador** en $D-1$ (la cantidad que salió de ese bróker en tránsito sigue contando como originada allí)
- solo los lotes largos participan en el denominador

La regla **D-1** mantiene limpio el día de registro: una compra realizada *en* la fecha del ingreso no genera esa distribución, y un lote vendido el día anterior tampoco. Los lotes elegibles más grandes reciben una mayor proporción; los lotes mantenidos en otros brókeres, o que aún no son (o ya no son) elegibles, no reciben nada.

Los ingresos conservan su signo: una corrección negativa de un pago de dividendo o interés reduce los ingresos del lote, igual que en el panel.

!!! warning "Cambiado en FIFO v5"

    Las versiones anteriores usaban la propia fecha del ingreso con **todos** los brókeres ($\text{OpenQty}_i(t)$ sobre cada lote). El motor actual usa la elegibilidad D-1 acotada al bróker pagador. Si ningún lote es elegible, los ingresos se conservan como **ingresos huérfanos a nivel de activo** (nunca se descartan, nunca se asignan al lote equivocado).

!!! tip "Regla de conservación"

    Los importes asignados a los lotes suman exactamente el total convertido del evento de ingreso. Los ingresos se distribuyen, no se crean.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-custody-modal" alt="Modal de detalle del lote: la fila Ingresos del activo muestra el dividendo/interés a prorrata asignado a este lote específico, junto a la insignia Estimado a coste cuando el valor actual del lote se estima a coste">
</div>

La fila **Ingresos del activo** del modal de detalle del lote es exactamente $\text{Income}_i$ de la fórmula anterior: la porción a prorrata que recibió este lote específico. Cuando el valor actual del lote se estima a coste —su activo no tiene ningún precio en la fecha final—, el mismo modal muestra también la insignia **Estimado a coste** de la sección anterior.

---

## 💸 Costes y Métricas Netas {: #costs-and-net-metrics }

Los `FEE` y `TAX` vinculados a activos se asignan a los lotes con una **escalera determinista de emparejamiento de operaciones**, y luego se restan para producir cifras **netas** junto a las brutas.

### 🧭 Asignación determinista de costes

Un grupo de costes (mismo bróker, mismo día, mismo tipo) se empareja con el primer objetivo no vacío en este orden:

| Coste | Orden de emparejamiento |
|------|----------------|
| `FEE` | operaciones del mismo día → operaciones del día anterior → posiciones abiertas → huérfano del activo |
| `TAX` | ingresos del mismo día → operaciones del mismo día → ingresos del día anterior → operaciones del día anterior → posiciones abiertas → huérfano del activo |

Dentro de una operación emparejada, el coste **pasa a los mismos lotes que tocó esa operación** —el coste de una compra recae sobre el lote que abrió, el coste de una venta recae sobre los lotes consumidos por FIFO—, de modo que la atribución de costes nunca contradice el emparejamiento FIFO en sí. Los importes se convierten a la divisa objetivo y se almacenan como magnitudes positivas.

!!! tip "Conservación"

    Por grupo, $\sum_i \text{Cost}_i + \text{Orphan} = \text{Convert}(\text{pool}, ccy, D)$. Un coste que no encuentra ningún lote elegible (p. ej., una comisión registrada después de que la posición esté totalmente cerrada) se convierte en **coste huérfano a nivel de activo** en lugar de descartarse o forzarse sobre un lote no relacionado.

### ⚖️ Bruto vs neto

Con los costes atribuidos por lote, LibreFolio informa tanto del rendimiento bruto como del neto:

$$
\text{NetTotalPnL}_i = \text{TotalPnL}_i - \text{Fees}_i - \text{Taxes}_i
$$

$$
\text{NetTotalReturn}_i = \frac{\text{NetTotalPnL}_i}{\text{OpeningValue}_i}
$$

donde $\text{TotalPnL}_i$ ya **incluye** los ingresos (P&L de mercado + P&L realizado + ingresos del activo). La serie de historial de valor por lote informa en cambio un P&L neto *solo de capital*, $\text{pnl}_i - \text{Fees}_i - \text{Taxes}_i$, que **excluye** los ingresos: cada línea neta refleja su propia contraparte bruta menos los costes.

El retorno anualizado del lote usa el retorno **neto**, no el bruto:

$$
\mathrm{AnnualizedReturn}_i =
\left(1+\mathrm{NetTotalReturn}_i\right)^{365/d_i}-1
$$

con $d_i$ desde la fecha de apertura hasta la fecha de cierre para lotes cerrados, o hasta la fecha final del análisis para lotes abiertos. Las ventanas inferiores a 30 días no devuelven valor anualizado; véase [Retorno Anualizado Neto](../portfolio-engine/net-annualized-return.md).

!!! example "Cifras canónicas"

    COMPRA 10×100, VENTA 4×120, precio actual 110, dividendo 50, comisiones 8, impuestos 5:
    P&L Total Bruto $= 60 + 80 + 50 = 190$; P&L Total Neto $= 190 - 13 = 177$; sobre un valor de apertura de 1.000 eso es un
    **19 %** de retorno total bruto frente a un **17,7 %** neto.

Los costes con `asset_id = null` **no** forman parte de esta vista a nivel de lote —son a nivel de cartera y los gestiona el [Motor de cartera](../portfolio-engine/roi.md). Véase [Comisión e Impuesto](../../../instruments/transaction-types/fee.md) para la teoría a nivel de instrumento.

---

## 📝 Ejemplo Resuelto

??? example "Ejemplo: dos lotes, un dividendo, un precio de mercado"

    Supongamos la misma acción, la misma divisa, `qbq = 1`.

    | Fecha | Evento | Cantidad abierta lote A | Cantidad abierta lote B | Notas |
    |------|-------|----------------|----------------|-------|
    | 2 ene | COMPRA 100 @ 10 $ | 100 | 0 | El lote A abre con coste original 1.000 $ |
    | 10 feb | COMPRA 50 @ 14 $ | 100 | 50 | El lote B abre con coste original 700 $ |
    | 15 mar | DIVIDENDO 30 $ | 100 | 50 | Ambos lotes siguen abiertos |
    | 1 abr | Precio de mercado = 16 $ | 100 | 50 | Evaluar ambos lotes |

    **Paso 1 — Asignar el dividendo a prorrata**

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

    **Paso 2 — Retorno Abierto para cada lote**

    $$
    \text{RelativeReturn}_A = \frac{16}{10} - 1 = 60{,}00\,\%
    $$

    $$
    \text{RelativeReturn}_B = \frac{16}{14} - 1 \approx 14{,}29\,\%
    $$

    **Paso 3 — Valor de mercado y Retorno Total**

    $$
    \text{OpenValue}_A = 100 \times 16 = 1.600
    \qquad
    \text{OpenValue}_B = 50 \times 16 = 800
    $$

    Como aún no se vendió ninguna acción, el importe de venta y el P&L realizado son ambos cero.

    $$
    \text{TotalPnL}_A = (1.600 - 1.000) + 20 = 620
    $$

    $$
    \text{TotalReturn}_A = \frac{620}{1.000} = 62{,}00\,\%
    $$

    $$
    \text{TotalPnL}_B = (800 - 700) + 10 = 110
    $$

    $$
    \text{TotalReturn}_B = \frac{110}{700} \approx 15{,}71\,\%
    $$

    **Paso 4 — Retorno agregado entre los lotes mostrados**

    $$
    \text{AggregateReturn} = \frac{620 + 110}{1.000 + 700} = \frac{730}{1.700} \approx 42{,}94\,\%
    $$

    Aunque ambos lotes pertenecen al mismo activo, sus retornos difieren porque se abrieron a precios diferentes.

---

## 📚 De los Lotes a las Métricas Agregadas

Los retornos a nivel de lote pueden acumularse en una serie de retorno agregada, pero **los porcentajes no deben sumarse directamente**.

LibreFolio usa esta regla agregada exacta entre los lotes mostrados:

$$
\text{AggregatePnL}(t) = \sum_i \left(\text{PnL}_i(t) + \text{Income}_i(t)\right)
$$

$$
\text{AggregateOpeningValue}(t) = \sum_i \text{OriginalCost}_i
$$

$$
\text{AggregateReturn}(t) = \frac{\text{AggregatePnL}(t)}{\text{AggregateOpeningValue}(t)}
$$

Esta vista a nivel de lote ayuda a explicar **de dónde** vino el retorno. Métricas de nivel superior como [ROI](../portfolio-engine/roi.md) y [TWRR](../portfolio-engine/twrr.md) responden a preguntas de cartera más amplias:

- **ROI** se centra en la ganancia relativa al capital invertido
- **TWRR** neutraliza el momento de los flujos de efectivo externos
- el análisis de lotes FIFO explica la contribución y la trayectoria **dentro** de una posición

La búsqueda de precios queda deliberadamente fuera del propio motor FIFO. El motor produce lotes y cierres, y solicita un precio solo para dar a un lote abierto por un ajuste su referencia; `LotsAnalysisService` responde desde el resolutor unificado ([Resolución de precios](../portfolio-engine/price-resolution.md)), y luego aplica el mismo resolutor y el fallback de estimación a coste al derivar las métricas de valoración.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-table" alt="Tabla unificada de lotes: una fila por lote con fecha de apertura, retorno total, valor actual, custodia y estado, exactamente las filas por lote sobre las que suman las fórmulas agregadas anteriores">
</div>

La **Tabla unificada de lotes** lista exactamente las filas por lote $i$ sobre las que suman las fórmulas agregadas anteriores: fecha de apertura, retorno total, valor actual, custodia y estado, todo filtrable al mismo conjunto visible de lotes que usan los gráficos.

---

## 🔗 Relacionado

- 📊 **[Precio Medio de Compra (PMC)](../weighted-average-cost.md)** — vista combinada del coste base
- 🔁 **[Compra y Venta](../../../instruments/transaction-types/buy-sell.md#fifo-matching)** — breve resumen del emparejamiento FIFO
- 💸 **[Dividendo e Interés](../../../instruments/transaction-types/dividend-interest.md)** — origen de los eventos de ingresos vinculados a activos
- 💰 **[Fiscalidad](../../../fundamentals/taxation.md)** — contexto de plusvalías y emparejamiento de lotes
- ⚙️ **[Servicio de análisis de lotes](../../../../developer/backend/transactions/lots_analysis_service.md)** — análisis profundo de la implementación para desarrolladores
