# 🔍 Posiciones y análisis

La pestaña **Posiciones** muestra lo que tienes, lo que ganó cada posición en el período y, a un clic de distancia, los lotes FIFO detrás de cualquier posición. La página de cada bróker tiene la misma pestaña solo para ese bróker, con la misma configuración de tabla.

- 📋 **[Posiciones](#holdings)** — lo que posees en la fecha de fin
- 📈 **[Rendimiento](#performance)** — lo que ganó cada posición en el período
- 🔬 **[Análisis de lotes FIFO](#fifo-lots-analysis)** — los lotes detrás de una posición

<div class="lf-screenshot-carousel" data-carousel="carousel-positions-views" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="positions-holdings-table" data-title="📋 Posiciones (Tabla)" alt="Vista de tabla de posiciones">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-holdings-map" data-title="🗺️ Posiciones (Mapa / Treemap)" alt="Vista de mapa de posiciones">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-table" data-title="📈 Rendimiento (Tabla)" alt="Vista de tabla de rendimiento">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-map" data-title="📊 Rendimiento (Mapa / Gráfico)" alt="Vista de mapa de rendimiento">
</div>

---

## 🎛️ Elegir una vista

- **Cartera / Período** alterna entre [Posiciones](#holdings) y [Rendimiento](#performance); **Tabla / Mapa** (los dos iconos) entre una tabla y un gráfico.
- **El icono del ojo** (en Tabla) muestra, oculta o reordena las columnas; **Restablecer diseño** las restaura. **Ver todo →** abre la página de Activos.
- **Para profundizar en una posición**, abre su menú **⋮** en una tabla, o haz clic derecho en cualquier vista: **Analizar lotes** abre el [Análisis de lotes FIFO](#fifo-lots-analysis) a continuación, **Ver activo** la página del activo.

LibreFolio recuerda tus elecciones.

---

## 📋 Posiciones — lo que posees {: #holdings }

¿Qué posees en la fecha de fin y cómo va cada posición? **Cartera** enumera una fila por activo y bróker, el mayor valor primero.

**Columnas mostradas**

| Columna | Qué muestra |
|:---|:---|
| **Activo** | El activo, con su icono de tipo |
| **Δ1** / **Δ1%** | Movimiento de hoy del P&L no realizado a la cantidad de hoy, en dinero y en % del valor de ayer |
| **P&L no realizado** / **P&L %** | Valor actual menos lo que costó la posición abierta, en dinero y en % de ese coste → [Valor contable](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md) |
| **Anualizada** | Rentabilidad compuesta anual desde la primera transacción, ingresos y comisiones incluidos → [Rentabilidad anualizada neta](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/net-annualized-return.md) |
| **YOC** | Los dividendos e intereses del último año por unidad, frente a su precio medio → [Rendimiento sobre coste](#yield-on-cost-yoc) |
| **Valor** / **Peso** | Lo que vale la posición y su parte de tu patrimonio neto, efectivo incluido |
| **Cantidad** | Acciones, unidades o monedas en posesión |
| **Precio** *(oculto)* | El precio unitario utilizado: el precio de mercado, o el precio de la última operación cuando no hay cotización → [Resolución de precios](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/price-resolution.md) |
| **Precio medio de compra (PMC)** *(oculto)* | Precio medio de compra por unidad, cada compra al tipo de cambio de su propia fecha → [Precio medio de compra (PMC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md) |
| **Lote abierto más antiguo** *(oculto)* | Fecha de apertura del lote más antiguo que sigue abierto |
| **Brókeres** | El bróker que mantiene la posición |

**Cómo leerlo**

- **El peso cuenta el efectivo**, por lo que las filas suman menos del 100 % cuando tienes efectivo.
- **El precio medio de compra (PMC) conserva el tipo de cambio de cada compra**, mientras que Valor usa el de la fecha de fin: el P&L no realizado incluye lo que hizo el tipo desde entonces.
- **En el Mapa**, los mosaicos se agrupan por bróker y tipo de activo; el tamaño es el valor, el color el P&L %. Desplázate para hacer zoom, arrastra para mover y **Restablecer zoom** (↺) lo muestra todo de nuevo.

??? info "➖ Celdas vacías — cuando falta un valor"

    - **`—` en P&L no realizado, P&L % o Precio medio de compra (PMC)**: el activo no tiene ningún precio, o parte de lo que pagaste es desconocida — un tipo de cambio faltante en una fecha de compra, o una transferencia o ajuste sin coste base. El [banner de calidad de datos](index.md#data-quality-banner) indica qué corregir.
    - **Δ1** y **Δ1%** necesitan un precio de mercado; **Anualizada** necesita una posición lo bastante antigua para que una tasa anual signifique algo.

### 💸 Rendimiento sobre coste (YOC) {: #yield-on-cost-yoc }

¿Cuántos ingresos te paga cada unidad en comparación con lo que costó? **YOC** compara los dividendos e intereses que recibió cada unidad durante los **últimos 365 días** con su precio medio de compra.

**Cómo leerlo**

- **Un valor por activo y bróker**, durante el año que termina en la fecha de fin: mover la fecha de inicio no lo cambia.
- **Bruto, no después de impuestos**: las transacciones separadas de impuestos y comisiones no se restan.
- **Pasa el cursor sobre un valor** para ver los ingresos por unidad, el período y los tipos de cambio utilizados — cada pago al tipo de su propia fecha.
- **`0.00%`** significa ingresos registrados a cero; un **`-`** simple significa que no hay ingresos en el último año.

🔗 **Teoría**: [Rendimiento sobre coste](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/yield-on-cost.md) — las reglas exactas y en qué se diferencia YOC del rendimiento por dividendo o del CAGR

??? info "🚦 Un guion con un icono ⓘ — cuando YOC no está disponible"

    LibreFolio no muestra un YOC parcial. Cuando falla una entrada, pasa el cursor sobre el ⓘ ámbar para ver el motivo: menos de un año de historial en este bróker y aún sin ingresos, un pago sin unidades en posesión el día anterior, un historial de compras, ventas, transferencias o desdoblamientos que no cuadra, un tipo de cambio faltante o un precio medio desconocido. Una vez corregido, YOC se calcula de nuevo.

---

## 📈 Rendimiento — lo que ganó cada posición {: #performance }

¿Qué posiciones ganaron o perdieron dinero en el período y cómo? **Período** enumera cada posición del período, abierta o cerrada desde entonces, los mayores movimientos primero. LibreFolio lo calcula la primera vez que lo abres, por lo que puede tardar un momento.

**Métricas mostradas**

- **P&L período**, dividido como en la [Tarjeta P&L período](kpi-cards.md#card-1-period-pl) en **Cambio no realizado**, **Ventas**, **Dividendos e intereses** y **Costes** → [P&L período](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)
- **Anualizada** — el resultado del período como tasa anual, durante el tiempo que la posición se mantuvo en el período → [Rentabilidad anualizada neta](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/net-annualized-return.md)
- **Δ1** / **Δ1%** para posiciones abiertas y, ocultos por defecto, **Valor inicial**, **Valor final**, **Lote abierto más antiguo** y **Estado**
- **Otros efectos del período** — lo que no pertenece a ninguna posición: **Ingresos no asignados** y **Costes no asignados**, registrados sin un activo, y el **Residual de otros / conciliación**

**Cómo leerlo**

- **Las posiciones cerradas** aparecen en cursiva, o llevan una insignia **Cerrado** en el gráfico; para listar solo un tipo, muestra **Estado** y fíltralo.
- **En el Mapa**, las ganancias se apilan a la derecha del cero y las pérdidas a la izquierda, el resultado neto cierra la fila; cada porcentaje se compara con el valor inicial de la posición.
- **El P&L período de una posición** puede diferir de su ganancia total: solo cuenta el período.

??? tip "🙈 Ocultar importes — lo que el gráfico aún muestra"

    Con **Ocultar importes** activado (el botón del ojo en la barra superior), los importes y el eje del gráfico se convierten en `•••`, como en `+€•••`. Los signos, monedas, porcentajes, longitudes de barras y colores permanecen, así que sigues viendo quién ganó o perdió, y cuánto en comparación con los demás. Consulta [Modo privacidad](../settings/preferences.md#privacy-mode).

---

## 🔬 Análisis de lotes FIFO {: #fifo-lots-analysis }

¿Qué compras componen una posición, dónde se mantienen y cómo ha ido cada una? El **Análisis de lotes FIFO** responde lote a lote: cada compra abre un *lote*, y cada venta cierra los lotes abiertos **más antiguos** primero — Primero en entrar, primero en salir.

Elige **Analizar lotes** en una posición y el panel se abre debajo, para los brókeres de la página: tu filtro de bróker en el Panel, el propio bróker en su página. **Ver activo** (↗) abre el activo, **✕** cierra el panel.

<div class="lf-screenshot-carousel" data-carousel="carousel-fifo-lots-analysis" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="fifo-lots-panel" data-title="🔍 Resumen" alt="Resumen del análisis de lotes FIFO">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-wac-chart" data-title="📈 PMC / Precio de mercado" alt="Gráfico de PMC y precio de mercado">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-gantt-chart" data-title="🕒 Vida y custodia del lote" alt="Gráfico de Gantt de vida y custodia del lote">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-table" data-title="📋 Tabla unificada de lotes" alt="Tabla unificada de lotes">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart" data-title="💰 Comparación de valor" alt="Gráfico de comparación de valor">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" data-title="📊 Comparación de rentabilidad" alt="Gráfico de comparación de rentabilidad">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-custody-modal" data-title="🧾 Modal de detalle del lote" alt="Modal de detalle del lote">
</div>

**Cómo funcionan los bloques juntos**

- **Una selección**: haz clic en burbujas, barras o filas de la tabla para elegir lotes; si no hay ninguno elegido, cuenta cada lote visible. **Abiertos / Cerrados**, en la línea de tiempo, filtra todos los bloques.
- **Doble clic para saltar**: desde un marcador del gráfico a los lotes de esa transacción, desde una barra de la línea de tiempo a su fila de la tabla, y viceversa.
- **Importes completos del bróker**: en un bróker que compartes, tu parte no se aplica aquí, a diferencia de las tarjetas KPI y Posiciones.

🔗 **Teoría**: [Motor FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md) · [Análisis de lotes FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md) · [Emparejamiento FIFO](../../financial-theory/instruments/transaction-types/buy-sell.md#fifo-matching) · [Fiscalidad](../../financial-theory/fundamentals/taxation.md)

### 💹 1. PMC / Precio de mercado

¿Cómo se compara el precio con lo que pagaste, y dónde se sitúa cada lote?

**Métricas mostradas**

- **Precio de mercado** — discontinuo donde LibreFolio lo estima a partir de tu última operación → [Cadena de precios de valoración](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md#valuation-price-chain)
- **Precio medio de compra (PMC)** — una línea por bróker, y una línea **Combinada** discontinua cuando el activo está en varios → [Precio medio de compra (PMC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)
- **Burbujas** — una por lote largo, en su rentabilidad total, entre los marcadores de tus transacciones y pagos → [Análisis de lotes FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)

**Cómo leerlo**

- **Abs / %** muestra los precios o su cambio desde el primer punto; **Auto / Desde 0** establece dónde comienza el eje.
- **El color de la burbuja** es el bróker de apertura, su **tamaño** la cantidad del lote (**Abs**) o su valor de apertura (**%**); un **borde discontinuo** significa valorado a coste.
- **Un hueco en una línea de PMC** es un día cuyo PMC se desconoce: no se dibuja un promedio incorrecto.

### 🕒 2. Vida y custodia del lote

¿Cuándo estuvo abierto cada lote y qué bróker lo mantuvo?

**Métricas mostradas**

- **Barras** — una por lote, coloreada por el bróker que lo mantiene y tan gruesa como la cantidad mantenida; violeta discontinua mientras está en tránsito, con un carril por bróker tras una transferencia → [Motor FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md)

**Cómo leerlo**

- **Abiertos / Cerrados** conserva solo los lotes abiertos, solo los cerrados, o ambos.
- **Una barra más fina** perdió parte de su cantidad, por ejemplo por una venta parcial.
- **Haz clic** en una barra para seleccionar su lote, **haz doble clic** para encontrar su fila en la tabla.

### 📋 3. Tabla de lotes

Cada lote con sus cifras, siguiendo el filtro y la selección del panel.

**Métricas mostradas**

- **Fecha de apertura**, **P&L total**, **Rentabilidad total**, **Anualizada**, **Valor actual**, **Cantidad abierta** y **Custodia**, con una fila de **Totales** → [Análisis de lotes FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Ingresos** cuando un lote recibió alguno, y **Comisiones**, **Impuestos**, **P&L neto** y **Rentabilidad neta** cuando un lote soporta costes → [Costes y métricas netas](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md#costs-and-net-metrics)

**Cómo leerlo**

- **Haz clic** en una fila para seleccionarla, **haz doble clic** para encontrarla en la línea de tiempo; el color de la fila es el bróker de apertura.
- **El menú ⋮** ofrece **Ver detalle del lote**, **Ir al lote en Gantt**, **Ir a la transacción de apertura** y **Copiar identificador del lote** — una referencia estable, útil para soporte.
- **Más columnas**, como **Valor de apertura**, esperan detrás del icono del ojo.

### 💰 4. Comparación de valor / rentabilidad

¿Cuánto valen los lotes seleccionados y cuánto han ganado desde su apertura? Si no hay ninguno seleccionado, el gráfico cubre todos los lotes visibles.

**Métricas mostradas**

- **Valor** — **Valor residual**, **Ingresos por venta** e **Ingresos acumulados** apilados hasta el **Valor integral**, frente al **Valor de apertura** → [Análisis de lotes FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Rentabilidad** — el resultado desde la apertura, en dinero (**Abs**) o porcentaje (**%**): una **Rentabilidad agregada**, más una línea por lote cuando comparas varios

**Cómo leerlo**

- **Valor integral por encima del Valor de apertura**: los lotes ganaron, ventas e ingresos incluidos.
- **Una línea discontinua** en **Valor** es un valor estimado a coste, sin precio de mercado.

### 🧾 5. Detalle del lote

Toda la historia de un lote. Ábrelo con **Ver detalle del lote** (⋮) o haciendo clic en su celda **Custodia**.

**Métricas mostradas**

- **Resumen** — valor de apertura y actual, ingresos por venta, **P&L FIFO**, **P&L total**, **Rentabilidad total**, y **Rentabilidad en efectivo** cuando el lote recibió ingresos → [Análisis de lotes FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Desglose neto** — el P&L total menos las comisiones e impuestos asignados al lote → [Costes y métricas netas](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md#costs-and-net-metrics)
- **Custodia actual** e **Historial** — dónde está el lote ahora, y cada evento desde su apertura

**Cómo leerlo**

- **Las cantidades son las posiciones completas del bróker**, como dice el ⓘ junto a ellas.
- **Ir a la transacción** abre la transacción de la fila del Historial que elegiste — por defecto, la de apertura.

??? warning "⚠️ Cuando el panel te avisa"

    - **Un banner plegado** enumera lo que falta — un tipo de cambio, un precio, un coste de compra — con un chip por lote afectado que encuentra su burbuja. Corrígelo como en el [banner de calidad de datos](index.md#data-quality-banner).
    - **Un mensaje rojo** significa que las cantidades o transferencias no cuadran: las cifras pueden estar incompletas, así que revisa las transacciones del activo.
    - **Un lote valorado a coste** no tiene precio de mercado: borde de burbuja discontinuo, sin ganancia o pérdida de mercado.

---

## 🔗 Relacionado

- 💰 **[Tarjetas KPI](kpi-cards.md)** — los mismos resultados para toda la cartera
- 💸 **[Transacciones](../transactions/index.md)** — la pestaña **Transacciones** del Panel enumera las operaciones del rango y brókeres seleccionados
- 🛠️ **[Detalles técnicos](../../developer/frontend/pages/index.md#dashboard)** — para desarrolladores: cómo funcionan por dentro la pestaña Posiciones y el panel de lotes

---

*[⬅️ Volver al resumen del panel](index.md)*
