# 💰 Tarjetas KPI

Las tres tarjetas en la parte superior del panel responden tres preguntas de un vistazo: **cuánto gané en este período**, **qué tan bien trabajó mi dinero** y **cuánto vale mi cartera**. Siguen el rango temporal y el filtro de bróker de la parte superior de la página, y la página de un bróker muestra las mismas tarjetas solo para ese bróker. El icono **?** en la esquina de una tarjeta abre su sección correspondiente más abajo.

- 📉 **[Tarjeta 1 — P&L período](#card-1-period-pl)** — el dinero que generaron tus inversiones en el período
- 📈 **[Tarjeta 2 — Rentabilidades](#card-2-returns)** — tus rentabilidades en porcentaje y lo que hizo tu timing con ellas
- 💰 **[Tarjeta 3 — Patrimonio neto](#card-3-net-worth)** — lo que posees y tu ganancia desde el inicio

!!! note "Los brókeres compartidos cuentan según tu participación"

    El panel suma los brókeres que **posees** con una participación superior al 0 %, cada uno en proporción a esa participación: un propietario del 50 % ve la mitad del valor y del P&L del bróker. Los brókeres en los que eres Editor o Lector no se cuentan aquí; su propia página los muestra, con sus importes completos. Consulta [Compartir brókeres](../brokers/sharing.md).

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Resumen de las tarjetas KPI">
</div>

---

## 📉 Tarjeta 1 — P&L período {: #card-1-period-pl }

¿Cuánto dinero generaron tus inversiones en el período seleccionado? La tarjeta **P&L período** responde, dejando fuera el dinero que aportaste o retiraste tú mismo.

<div class="kpi-card-crop-container card-period-pnl">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Tarjeta de P&L período">
</div>

**Métricas mostradas**

- **P&L período** — la cifra grande: $\text{NAV}_{\text{end}} - \text{NAV}_{\text{start}} - \text{Net flows}$, siendo los flujos netos el capital que moviste hacia dentro o hacia fuera → [P&L período](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)
- **La línea debajo** — por ejemplo `+91.31 € (+16.36%)`: cuánto se movió tu P&L total desde ayer (panel inferior)
- **Variación no realizada** — cómo se movió durante el período la ganancia o pérdida no realizada de tus posiciones, incluido el efecto del tipo de cambio → [P&L período](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)
- **Ventas** — la ganancia o pérdida realizada de las ventas del período, frente al coste medio de las unidades vendidas. Un ajuste que elimina unidades no tiene valor: aquí cuenta como una venta a precio cero, una pérdida de lo que costaron esas unidades (consulta [Ajustes de salida](../../financial-theory/instruments/transaction-types/adjustment.md#outgoing-adjustments)) → [Precio medio de compra (PMC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)
- **Dividendos e intereses** — dividendos, cupones e intereses de P2P recibidos → [Dividendos e intereses](../../financial-theory/instruments/transaction-types/dividend-interest.md)
- **Comisiones e impuestos** — comisiones e impuestos registrados como transacciones; pasa el cursor sobre la fila para ver el desglose → [Comisión e impuesto](../../financial-theory/instruments/transaction-types/fee.md)

**Cómo leerla**

- **Verde es ganancia, rojo es pérdida** — y un depósito o un retiro no son ninguna de las dos.
- **Las cuatro filas explican la cifra grande.** Lo que no pueden captar pasa a la [Vista del período](positions.md#performance): lo que los tipos de cambio hicieron con el efectivo que tienes en otra divisa aparece allí como **Efecto del tipo de cambio sobre el efectivo**, una fila por cada bróker cuyo efectivo se vio afectado por los tipos de cambio. Cuando consultas solo algunos de tus brókeres, los valores transferidos hacia o desde un bróker fuera de tu selección se contabilizan a su valor de mercado del día: la ganancia que obtuvieron en el otro bróker aparece como **Transferencias a valor de mercado**, una fila por cada bróker implicado ([cómo funciona](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md#transfers-at-market-value)). El resto —como activos que se mueven entre dos de tus brókeres el primer o el último día— es el **Otros / residual de conciliación**.
- **La barra más larga** es la fila que más movió tu resultado.

??? info "📏 La línea bajo la cifra grande — cómo se calcula"

    Es el cambio de tu P&L total —tu ganancia o pérdida desde el inicio— de ayer a hoy, siendo *hoy* la fecha final del período. El porcentaje lo compara con el P&L total de ayer, tomado sin su signo:

    $$
    \Delta = \text{Total P}\&\text{L}_{\text{today}} - \text{Total P}\&\text{L}_{\text{yesterday}} \qquad \text{percentage} = \frac{\Delta}{\left|\text{Total P}\&\text{L}_{\text{yesterday}}\right|} \times 100
    $$

    - **El signo y el color siguen el cambio**, incluso cuando el P&L total es una pérdida: de `-558.10 €` a `-466.79 €`, la línea muestra `+91.31 € (+16.36%)` — tu pérdida se redujo un 16,36 %.
    - **Solo falta cuando el período termina en el primer día de tu cartera**, ya que no hay un día anterior con el que comparar; el porcentaje se omite cuando el P&L total de ayer es exactamente cero, y un día sin cambios muestra `0.00%`. Un lunes, la línea abarca todo el fin de semana, ya que un día sin mercado conserva los precios del último día de negociación.

### 💱 Variación no realizada por divisa {: #unrealized-change-by-currency }

Pasa el cursor sobre **Variación no realizada** para desglosarla por la divisa en la que están valorados tus activos —aquí con el euro como moneda de visualización:

| Fila | Qué muestra |
|-----|---------------|
| 📈 **Activos en USD** | Qué hicieron tus activos en dólares *en dólares* —su propia variación de precio—, contabilizados al tipo de cambio del día |
| 💱 **Tipo de cambio USD → EUR** | Qué hizo el tipo de cambio con lo que pagaste por ellos |
| ❔ **USD, sin desglosar** | Solo cuando, el primer o el último día, algunos de esos activos no tenían tipo de cambio o tenían un coste de compra incompleto: su variación, en un solo bloque |

Hay una fila 📈 por cada divisa, incluido el euro, y una fila 💱 por cada divisa distinta de tu moneda de visualización; en conjunto, las filas suman **exactamente** la Variación no realizada. En un día en que un activo se valora por lo que te costó, porque no tiene ningún precio, no tiene ganancia ni pérdida no realizada y no suma nada a ninguna fila.

??? example "Un ETF estadounidense en un panel en euros"

    Durante el período compraste 10 unidades por 400 €, cuando valían 500 USD. Al final del período valen 550 USD, y 1 USD = 0,75 €. La información emergente muestra:

    - 📈 **Activos en USD**: (550 − 500) × 0,75 = **+37,50 €** — tu ETF ganó un 10 % en dólares;
    - 💱 **Tipo de cambio USD → EUR**: 500 × 0,75 − 400 = **−25,00 €** — el dólar perdió valor frente al euro;
    - en conjunto, la **Variación no realizada**: 550 × 0,75 − 400 = **+12,50 €**.

🔗 **Teoría**: [Variación no realizada por divisa](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md#unrealized-change-by-currency) — las fórmulas detrás de cada fila

---

## 📈 Tarjeta 2 — Rentabilidades {: #card-2-returns }

¿Qué tan bien trabajó tu dinero, sea cual sea el tamaño de tu cartera? La tarjeta **Rentabilidades** responde en porcentajes, y su cifra grande te dice si tu timing ayudó.

<div class="kpi-card-crop-container card-returns">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Tarjeta de rentabilidades">
</div>

**Métricas mostradas**

- **Efecto timing** — la cifra grande, en puntos porcentuales (pp): $\text{MWRR}_{\text{cumulative}} - \text{TWRR}$ → [Efecto timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)
- **El porcentaje debajo** — por ejemplo `+0.35%`: el cambio de hoy en tu P&L total, frente al patrimonio neto de ayer (panel inferior)
- **ROI** — la ganancia del período frente al capital invertido: lo que valía la cartera cuando comenzó el período, más los depósitos y menos los retiros realizados desde entonces. Cuando el rango empieza antes de tu primera transacción, tu primer depósito también cuenta como capital, así que el ROI es el mismo que en todo tu historial → [ROI simple](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md#dashboard-period-roi)
- **TWRR** — cómo se comportaron tus elecciones de activos, sea cual sea el momento de tus depósitos → [TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)
- **MWRR acumulado** y **MWRR anualizado** — tu rentabilidad personal, incluido el timing de los depósitos, durante el período y como tasa anual → [MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)

**Cómo leerla**

- **Timing favorable** (verde): tendías a depositar antes de que subieran los precios. **Timing desfavorable** (rojo): tendías a depositar en los máximos. Cerca de cero se muestra como **Timing neutro**, ni verde ni rojo.
- **TWRR juzga la estrategia; MWRR, tu resultado personal** — como en el caso de un gestor de fondos y un inversor.
- **Las cuatro filas cubren todo el período**; el porcentaje pequeño cubre solo hoy.
- **`—` significa que no hay valor**: una rentabilidad que LibreFolio no puede calcular para el período muestra `—` en lugar de un número. TWRR y MWRR muestran `—` cuando tu cartera vale cero o menos al final del período, por ejemplo después de venderlo todo y retirar el efectivo ([Cuándo no se muestra TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md#when-no-twrr), [MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)). El efecto timing necesita tanto TWRR como MWRR: cuando falta uno, muestra un `—` gris, sin etiqueta de timing. El ROI nunca es `—`: sin capital invertido en el período, muestra `0.00%`.

??? info "📏 El porcentaje bajo el efecto timing — cómo se calcula"

    El mismo cambio de tu P&L total que en la [Tarjeta 1](#card-1-period-pl), dividido por el patrimonio neto de ayer tomado sin su signo:

    $$
    \text{percentage} = \frac{\text{Total P}\&\text{L}_{\text{today}} - \text{Total P}\&\text{L}_{\text{yesterday}}}{\left|\text{Net Worth}_{\text{yesterday}}\right|} \times 100
    $$

    Su signo y color siguen el cambio, como en la Tarjeta 1. Falta cuando el período termina en el primer día de tu cartera y se oculta cuando el patrimonio neto de ayer era exactamente cero.

---

## 💰 Tarjeta 3 — Patrimonio neto {: #card-3-net-worth }

¿Cuánto vale tu cartera al final del período y cuánto ha ganado desde que empezaste? La tarjeta **Patrimonio neto** responde, incluido el efectivo.

<div class="kpi-card-crop-container card-net-worth">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Tarjeta de patrimonio neto">
</div>

**Métricas mostradas**

- **Patrimonio neto** — la cifra grande: valores a valor de mercado, más efectivo, más cualquier cosa en tránsito entre tus brókeres → [NAV / Patrimonio neto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)
- **La línea debajo** — por ejemplo `+12,450.30 (+24.85%)`: tu **P&L total** desde el inicio y, entre paréntesis, tu **ROI desde el inicio** → [Capital depositado y P&L total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)
- **Valor de mercado** — cuánto valen a precios de mercado los activos que tienes → [NAV / Patrimonio neto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)
- **Coste de compra** — lo que te costaron las posiciones que aún mantienes, cada compra al tipo de cambio de su propia fecha → [Valor contable](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)
- **Efectivo** — el efectivo en tus brókeres; pasa el cursor para separar el capital que depositaste de las rentabilidades que obtuviste → [Grupos de efectivo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#three-pool-cash-model)
- **Capital depositado (período)** — depósitos menos retiros en el período, en verde a la derecha y en rojo a la izquierda; pasa el cursor para ver los totales → [Capital depositado](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)

$$
\text{Total P}\&\text{L} = \text{Net Worth} - \text{Capital put in since the start}
$$

Ese capital es cada depósito menos cada retiro, más el coste de compra de los valores que aportaste sin efectivo, como una posición de apertura; el ROI entre paréntesis divide el P&L total entre ese capital.

**Cómo leerla**

- **¿Fecha final o período?** La cifra grande y las tres primeras filas son valores en la fecha final; Capital depositado (período) cuenta solo los movimientos entre el inicio y el final.
- **El pequeño indicador** en una barra marca su valor al inicio del período (pasa el cursor sobre él); Valor de mercado se vuelve rojo cuando termina por debajo de ese valor.
- **El patrimonio neto incluye efectivo**, a diferencia del "valor de los títulos" de un extracto bancario.
- **El P&L total no es un cambio diario**: para ver el pulso de hoy, consulta las líneas pequeñas de la Tarjeta 1 y la Tarjeta 2.

---

## 🔗 Relacionado

- 🔍 **[Posiciones y análisis](positions.md)** — los mismos resultados, posición por posición
- 📊 **[Gráficos](charts.md)** — la vista **P&L** del gráfico de crecimiento sigue tu P&L total a lo largo del tiempo
- 📐 **[Resumen de métricas de rendimiento](../../financial-theory/technical-analysis/performance-metrics/index.md)** — cada métrica de estas tarjetas, con su fórmula
- 🛠️ **[Detalles técnicos](../../developer/frontend/pages/index.md#dashboard)** — para desarrolladores: de dónde vienen las cifras de las tarjetas

---

*[⬅️ Volver al resumen del panel](index.md)*
