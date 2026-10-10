# 💰 Tarjetas KPI

Las tres tarjetas en la parte superior del panel responden tres preguntas de un vistazo: **cuánto gané en este periodo**, **qué tan bien trabajó mi dinero**, y **cuánto vale mi cartera**. Siguen el rango temporal y el filtro de bróker en la parte superior de la página, y la página de un bróker muestra las mismas tarjetas solo para ese bróker. El icono **?** en la esquina de una tarjeta abre su sección a continuación.

- 📉 **[Tarjeta 1 — P&L período](#card-1-period-pl)** — el dinero que generaron tus inversiones en el periodo
- 📈 **[Tarjeta 2 — Rentabilidades](#card-2-returns)** — tus rentabilidades en porcentaje, y lo que tu timing hizo con ellas
- 💰 **[Tarjeta 3 — Patrimonio neto](#card-3-net-worth)** — lo que posees, y tu ganancia desde el inicio

!!! note "Los brókeres compartidos cuentan según tu participación"

    El panel suma los brókeres que **posees** con una participación superior al 0%, cada uno en proporción a esa participación: un propietario del 50% ve la mitad del valor y del P&L del bróker. Los brókeres en los que eres Editor o Lector no se cuentan aquí; su propia página los muestra, con sus importes completos. Consulta [Compartir brókeres](../brokers/sharing.md).

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Resumen de las tarjetas KPI">
</div>

---

## 📉 Tarjeta 1 — P&L período {: #card-1-period-pl }

¿Cuánto dinero generaron tus inversiones en el periodo seleccionado? La tarjeta **P&L período** responde, dejando fuera el dinero que moviste tú mismo hacia dentro o hacia fuera.

<div class="kpi-card-crop-container card-period-pnl">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Tarjeta P&L Período">
</div>

**Métricas mostradas**

- **P&L período** — el número grande: $\text{NAV}_{\text{end}} - \text{NAV}_{\text{start}} - \text{Net flows}$, siendo los flujos netos el capital que moviste hacia dentro o hacia fuera → [P&L período](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)
- **La línea debajo** — por ejemplo `+91.31 € (+16.36%)`: cuánto se movió tu P&L Total desde ayer (panel a continuación)
- **Variación no realizada** — cómo se movió la ganancia o pérdida no realizada de tus posiciones durante el periodo, incluido el efecto del tipo de cambio → [Valor contable](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)
- **Ventas** — la ganancia o pérdida realizada de las ventas del periodo, frente al coste medio de las unidades vendidas → [Precio medio de compra (PMC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)
- **Dividendos e intereses** — dividendos, cupones e intereses P2P recibidos → [Dividendo e interés](../../financial-theory/instruments/transaction-types/dividend-interest.md)
- **Comisiones e impuestos** — comisiones e impuestos registrados como transacciones; pasa el cursor sobre la fila para ver el desglose → [Comisión e impuesto](../../financial-theory/instruments/transaction-types/fee.md)

**Cómo interpretarlo**

- **Verde es ganancia, rojo es pérdida** — y un depósito o un retiro no es ninguna de las dos.
- **Las cuatro filas explican el número grande.** Lo que no pueden ver, como activos que se mueven entre dos de tus brókeres el primer o el último día, va al **Otros / residual de conciliación** de la [vista Rendimiento](positions.md#performance).
- **La barra más larga** es la fila que más movió tu resultado.

??? info "📏 La línea bajo el número grande — cómo se calcula"

    Es el cambio de tu P&L Total —tu ganancia o pérdida desde el inicio— desde ayer hasta hoy, siendo *hoy* la fecha final del periodo. El porcentaje lo compara con el P&L Total de ayer, tomado sin su signo:

    $$
    \Delta = \text{Total P}\&\text{L}_{\text{today}} - \text{Total P}\&\text{L}_{\text{yesterday}} \qquad \text{percentage} = \frac{\Delta}{\left|\text{Total P}\&\text{L}_{\text{yesterday}}\right|} \times 100
    $$

    - **El signo y el color siguen el cambio**, incluso mientras el P&L Total es una pérdida: de `-558.10 €` a `-466.79 €`, la línea muestra `+91.31 € (+16.36%)` — tu pérdida se redujo en un 16.36%.
    - **Necesita dos días de historial**; el porcentaje se omite cuando el P&L Total de ayer es exactamente cero, y un día sin cambios muestra `0.00%`.

### 💱 Variación no realizada por divisa {: #unrealized-change-by-currency }

Pasa el cursor sobre **Variación no realizada** para desglosarla por la divisa en la que están valorados tus activos —aquí con el euro como divisa de visualización:

| Fila | Qué muestra |
|-----|---------------|
| 📈 **Activos en USD** | Qué hicieron tus activos en dólares *en dólares* —su propio cambio de precio— contabilizados al tipo de cambio del día |
| 💱 **Tipo USD → EUR** | Qué hizo el tipo de cambio con lo que pagaste por ellos |
| ❔ **USD, sin desglosar** | Solo cuando, en el primer o el último día, algunos de esos activos no tenían precio, ni tipo de cambio, o tenían un coste de compra incompleto: su variación, en una sola pieza |

Hay una fila 📈 para cada divisa, incluido el euro, y una fila 💱 para cada divisa distinta de tu divisa de visualización; en conjunto, las filas suman **exactamente** la Variación no realizada.

??? example "Un ETF estadounidense en un panel en euros"

    Durante el periodo compraste 10 unidades por €400, cuando valían 500 USD. Al final del periodo valen 550 USD, y 1 USD = €0.75. La información emergente muestra:

    - 📈 **Activos en USD**: (550 − 500) × 0.75 = **+€37.50** — tu ETF ganó un 10% en dólares;
    - 💱 **Tipo USD → EUR**: 500 × 0.75 − 400 = **−€25.00** — el dólar perdió valor frente al euro;
    - en conjunto, la **Variación no realizada**: 550 × 0.75 − 400 = **+€12.50**.

🔗 **Teoría**: [Variación no realizada por divisa](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md#unrealized-change-by-currency) — las fórmulas detrás de cada fila

---

## 📈 Tarjeta 2 — Rentabilidades {: #card-2-returns }

¿Qué tan bien trabajó tu dinero, independientemente del tamaño de tu cartera? La tarjeta **Rentabilidades** responde en porcentajes, y su número grande te dice si tu timing ayudó.

<div class="kpi-card-crop-container card-returns">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Tarjeta Rendimientos">
</div>

**Métricas mostradas**

- **Efecto timing** — el número grande, en puntos porcentuales (pp): $\text{MWRR}_{\text{cumulative}} - \text{TWRR}$ → [Efecto timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)
- **El porcentaje debajo** — por ejemplo `+0.35%`: el cambio de hoy en tu P&L Total, frente al patrimonio neto de ayer (panel a continuación)
- **ROI** — la ganancia del periodo frente al capital invertido → [ROI simple](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md)
- **TWRR** — cómo rindieron tus elecciones de activos, independientemente del timing de tus depósitos → [TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)
- **MWRR acumulado** y **MWRR anualizado** — tu rentabilidad personal, incluido el timing de los depósitos, durante el periodo y como tasa anual → [MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)

**Cómo interpretarlo**

- **Timing favorable** (verde): tendiste a depositar antes de que subieran los precios. **Timing desfavorable** (rojo): tendiste a depositar en los picos. Cerca de cero se lee **Timing neutral**, y cuanto más fuerte es el color, mayor es el efecto.
- **El TWRR juzga la estrategia, el MWRR tu resultado personal** — como para un gestor de fondos y un inversor.
- **Las cuatro filas cubren todo el periodo**; el porcentaje pequeño cubre solo hoy.
- **`—` significa sin valor**: una rentabilidad que LibreFolio no puede calcular para el periodo muestra `—` en lugar de un número. El efecto timing necesita tanto el TWRR como el MWRR: cuando falta uno, muestra un `—` gris, sin etiqueta de timing.

??? info "📏 El porcentaje bajo el efecto timing — cómo se calcula"

    El mismo cambio de tu P&L Total que en la [Tarjeta 1](#card-1-period-pl), dividido por el patrimonio neto de ayer tomado sin su signo:

    $$
    \text{percentage} = \frac{\text{Total P}\&\text{L}_{\text{today}} - \text{Total P}\&\text{L}_{\text{yesterday}}}{\left|\text{Net Worth}_{\text{yesterday}}\right|} \times 100
    $$

    Su signo y color siguen el cambio, como en la Tarjeta 1. Necesita dos días de historial y se oculta cuando el patrimonio neto de ayer era exactamente cero.

---

## 💰 Tarjeta 3 — Patrimonio neto {: #card-3-net-worth }

¿Cuánto vale tu cartera al final del periodo, y cuánto ha ganado desde que empezaste? La tarjeta **Patrimonio neto** responde, incluyendo el efectivo.

<div class="kpi-card-crop-container card-net-worth">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Tarjeta Patrimonio Neto">
</div>

**Métricas mostradas**

- **Patrimonio neto** — el número grande: valores a precio de mercado, más efectivo, más cualquier importe en tránsito entre tus brókeres → [NAV / Patrimonio neto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)
- **La línea debajo** — por ejemplo `+12,450.30 (+24.85%)`: tu **P&L Total** desde el inicio y, entre paréntesis, tu **ROI desde el inicio** → [Capital depositado y P&L Total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)
- **Valor de mercado** — cuánto valen los activos que posees a precios de mercado → [NAV / Patrimonio neto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)
- **Coste de compra** — cuánto te costaron las posiciones que aún mantienes, cada compra al tipo de cambio de su propia fecha → [Valor contable](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)
- **Efectivo** — el efectivo en tus brókeres; pasa el cursor para desglosar el capital que depositaste y las rentabilidades que obtuviste → [Grupos de efectivo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#three-pool-cash-model)
- **Capital depositado (Periodo)** — depósitos menos retiros en el periodo, verde a la derecha y rojo a la izquierda; pasa el cursor para ver los totales → [Capital depositado](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)

$$
\text{Total P}\&\text{L} = \text{Net Worth} - \text{Capital put in since the start}
$$

Ese capital es cada depósito menos cada retiro, más el coste de compra de los valores que aportaste sin efectivo, como una posición inicial; el ROI entre paréntesis divide el P&L Total entre él.

**Cómo interpretarlo**

- **¿Fecha final o periodo?** El número grande y las tres primeras filas son valores en la fecha final; Capital depositado (Periodo) cuenta solo los movimientos entre el inicio y el final.
- **El pequeño caret** en una barra marca su valor al inicio del periodo (pasa el cursor sobre ella); el Valor de mercado se vuelve rojo cuando termina por debajo de él.
- **El Patrimonio neto incluye el efectivo**, a diferencia del "valor de los títulos" de un extracto bancario.
- **El P&L Total no es un cambio diario**: para el pulso de hoy, consulta las líneas pequeñas de la Tarjeta 1 y la Tarjeta 2.

---

## 🔗 Relacionado

- 🔍 **[Posiciones y análisis](positions.md)** — los mismos resultados, posición por posición
- 📊 **[Gráficos](charts.md)** — la vista **P&L** del gráfico Growth sigue tu P&L Total a lo largo del tiempo
- 📐 **[Resumen de métricas de rendimiento](../../financial-theory/technical-analysis/performance-metrics/index.md)** — cada métrica de estas tarjetas, con su fórmula
- 🛠️ **[Detalles técnicos](../../developer/frontend/pages/index.md#dashboard)** — para desarrolladores: de dónde vienen las cifras de las tarjetas

---

*[⬅️ Volver al resumen del panel](index.md)*
