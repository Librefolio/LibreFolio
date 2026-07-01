# 📊 Gráficos

*[⬅️ Volver a la descripción general del panel de control](index.md)*

La sección de gráficos se encuentra debajo de las tarjetas de KPI y ofrece una **visión histórica y estructural** de su cartera durante el rango de tiempo seleccionado.

---

## 📈 Gráfico de Crecimiento de la Cartera

El gráfico de crecimiento muestra cómo ha evolucionado el valor de su cartera durante el periodo seleccionado. Utilice el interruptor **Abs / %** en la esquina superior derecha para cambiar entre dos vistas.

<div class="lf-screenshot-carousel" data-carousel="carousel-growth" data-carousel-interval="5000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Modo Absoluto" alt="Gráfico de Crecimiento — Modo Absoluto">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Modo Porcentual" alt="Gráfico de Crecimiento — Modo Porcentual">
</div>

### Modo ABS — valores absolutos

El gráfico utiliza un diseño de **áreas apiladas + líneas superpuestas**:

| Elemento | Color | Significado |
|---------|-------|---------|
| Área — **Coste de Activos** | Azul | Base de coste de todas las posiciones abiertas (coste medio × cantidad) |
| Área — **Retornos** | Esmeralda | Retornos de la cartera mantenidos como efectivo líquido (intereses, ganancias realizadas aún no reinvertidas) |
| Área — **Capital** | Gris-verde | Depósitos no desplegados mantenidos en efectivo |
| Línea — **[NAV](../../financial-theory/technical-analysis/performance-metrics/nav.md)** | Verde oscuro sólido | Valor total de la cartera a precios de mercado actuales |
| Línea — **[Capital Depositado](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)** | Gris discontinuo | Capital externo neto aportado a lo largo del tiempo |

**La brecha entre la línea de NAV y la línea de Capital Depositado = P&L Total** — todas las ganancias generadas, incluyendo ganancias no realizadas, ganancias realizadas, intereses y dividendos, menos comisiones e impuestos.

#### Desglose de la información emergente

Cuando pasa el cursor sobre el gráfico, la información emergente muestra:

- **NAV** — valor total de la cartera en esa fecha
- **Capital Depositado** — capital neto que aportó hasta esa fecha
- **Total P&L** — la diferencia (NAV − Capital Depositado)
- **Coste de Activos** / **Retornos** / **Capital** — los tres componentes de efectivo

!!! tip "Lectura de carteras impulsadas por ingresos (P2P, bonos)"

    Para carteras como el préstamo P2P donde los activos se valoran a su precio de compra (sin precio de mercado en vivo), NAV ≈ Coste de Activos. La brecha entre NAV y Capital Depositado puede no ser visible como un hueco en el gráfico, pero la información emergente **Total P&L** muestra el valor correcto.

    Cuando reinvierte todos los retornos en nuevos activos, el área de Retornos se mantiene cerca de cero y los ingresos obtenidos terminan integrados en el área de Coste de Activos. Esto es matemáticamente correcto: su base de coste creció porque reinvirtió el beneficio.

🔗 **Teoría**: [Capital Depositado y P&L Total](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md) · [Descomposición del Efectivo](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md#modelo-de-efectivo-de-tres-pools)

### Modo % — tasa de retorno

Todas las series comienzan en 0% al inicio del periodo seleccionado y muestran cómo evolucionó cada métrica de retorno:

| Serie | Qué muestra |
|--------|--------------|
| **[MWRR acumulado](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | Su retorno personal ponderado por el capital, incluyendo el momento de los depósitos |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** | Retorno puro de la estrategia de activos, ignorando cuándo depositó |
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/roi.md)** | Retorno bruto sobre el capital neto invertido |

La brecha entre MWRR y TWRR es el [Efecto de temporalidad](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md).

!!! note "MWRR no disponible"

    Si aparece un **banner de Calidad de Datos** indicando que el MWRR no es fiable, la serie MWRR se oculta del gráfico %. El problema ocurre típicamente cuando el periodo tiene flujos de efectivo muy grandes en relación con el tamaño inicial de la cartera, lo que provoca que el resolvedor matemático sea inestable. ROI y TWRR siempre se muestran.

---

## 🥧 Panel de Asignación

El panel de asignación muestra cómo está distribuida su cartera en el momento actual y cómo ha evolucionado históricamente.

<div class="lf-screenshot-carousel" data-carousel="carousel-alloc" data-carousel-interval="5000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="allocation-type-now" data-title="Por Tipo (Actual)" alt="Asignación por Tipo — Actual">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-sector-now" data-title="Por Sector (Actual)" alt="Asignación por Sector — Actual">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-geo-now" data-title="Por Geografía (Actual)" alt="Asignación por Geografía — Actual">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-history" data-title="Por Tipo (Histórico)" alt="Historial de Asignación por Tipo">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-sector-history" data-title="Por Sector (Histórico)" alt="Historial de Asignación por Sector">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-geo-history" data-title="Por Geografía (Histórico)" alt="Historial de Asignación por Geografía">
</div>

### Tres dimensiones

| Dimensión | Qué muestra |
|-----------|--------------|
| **Tipo** | ETF, Acción, Bono, Crypto, Bienes Raíces, Liquidez (efectivo) |
| **Sector** | Sector industrial: 💻 Tecnología, 🏦 Financieros, 💊 Salud, etc. |
| **Geografía** | País o región de la cotización principal de cada activo |

### Pestañas Actual vs. Histórico

- **Actual** — Gráfico de dona de la asignación actual en `date_to`. Pase el cursor sobre cualquier segmento para ver el porcentaje exacto y el valor absoluto.
- **Histórico** — Gráfico de áreas apiladas al 100% que muestra cómo cambió la asignación a lo largo del tiempo. Útil para visualizar el reequilibrio de la cartera a través de meses o años.

### El efectivo como Liquidez

El **Efectivo** (el saldo de su bróker) siempre aparece como el segmento de **Liquidez** tanto en la vista de Tipo como en la de Sector. En el mapa de Geografía, el efectivo no se asigna a ningún país y no aparece.

!!! info "Alcance del bróker"

    Cuando filtra por brókeres específicos, la asignación muestra solo los activos y el efectivo dentro de esos brókeres.

---

## 🔗 Relacionados

- 💰 **[Tarjetas de KPI](kpi-cards.md)** — Patrimonio Neto, P&L del Periodo, Retornos
- 💼 **[NAV / Patrimonio Neto](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- 💸 **[Capital Depositado y P&L Total](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** · **[MWRR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** · **[Efecto de temporalidad](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md)**
