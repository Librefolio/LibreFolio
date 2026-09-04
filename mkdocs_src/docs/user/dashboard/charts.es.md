# 📊 Gráficos

La sección de gráficos se encuentra debajo de las tarjetas KPI y te proporciona una **vista histórica y estructural** de tu cartera durante el período de tiempo seleccionado.

---

## 📈 Gráfico de Crecimiento de la Cartera {: #portfolio-growth-chart }

El gráfico de crecimiento muestra cómo evolucionó el valor de tu cartera durante el período seleccionado. Usa el interruptor **Abs / %** en la esquina superior derecha para cambiar entre dos vistas.

<div class="lf-screenshot-carousel" data-carousel="carousel-growth" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <div class="lf-screenshot-carousel-item is-active chart-crop-container" data-title="📈 Modo Absoluto" alt="Gráfico de Crecimiento — Modo Absoluto">
 <img class="gallery-img" data-category="dashboard" data-name="main" alt="Gráfico de Crecimiento — Modo Absoluto">
 </div>
 <div class="lf-screenshot-carousel-item chart-crop-container" data-title="📈 Modo Porcentual" alt="Gráfico de Crecimiento — Modo Porcentual">
 <img class="gallery-img" data-category="dashboard" data-name="main-pct" alt="Gráfico de Crecimiento — Modo Porcentual">
 </div>
</div>

### ABS ABS — valores absolutos

El gráfico utiliza un diseño de **área apilada + líneas superpuestas**:

| Elemento | Color | Significado |
|----------|-------|-------------|
| Área — **Costo de Activos** | Azul | Base del costo de todas las posiciones abiertas (costo promedio × cantidad) |
| Área — **Rendimientos** | Esmeralda | Rendimientos de la cartera como efectivo líquido (intereses, ganancias realizadas aún no reinvertidas) |
| Área — **Capital** | Gris-verde | Depósitos no utilizados en efectivo |
| Línea — **[NAV](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)** | Verde oscuro sólido | Valor total de la cartera a precios de mercado actuales |
| Línea — **[Capital Depositado](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)** | Gris discontinua | Capital externo neto aportado a lo largo del tiempo |

**La brecha entre la línea de NAV y la línea de Capital Depositado = PyG Total** — todas las ganancias generadas, incluyendo plusvalías no realizadas, plusvalías realizadas, intereses y dividendos, menos comisiones e impuestos.

#### Tooltip de la información emergente

Al pasar el cursor sobre el gráfico, la información emergente muestra:

- **NAV** — valor total de la cartera en esa fecha
- **Capital Depositado** — capital neto que aportaste hasta esa fecha
- **PyG Total** — la diferencia (NAV − Capital Depositado)
- **Costo de Activos** / **Rendimientos** / **Capital** — los tres componentes de efectivo

!!! tip "Lectura de carteras basadas en ingresos (P2P, bonos)"

    En carteras como préstamos P2P donde los activos se valoran a su precio de compra (sin precio de mercado en vivo), NAV ≈ Costo de Activos. Es posible que la brecha entre NAV y Capital Depositado no sea visible como una brecha en el gráfico, pero el **PyG Total** en la información emergente muestra el valor correcto.

    Cuando reinviertes todos los rendimientos en nuevos activos, el área de Rendimientos se mantiene cerca de cero, y los ingresos obtenidos quedan incorporados en el área de Costo de Activos. Esto es matemáticamente correcto: tu base del costo creció porque reinvertiste las ganancias.

🔗 **Teoría**: [Capital Depositado y PyG Total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) · [Descomposición de Efectivo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#three-pool-cash-model)

### Modo % — tasa de rendimiento

Todas las series comienzan en 0% al inicio del período seleccionado y muestran cómo evolucionó cada métrica de rendimiento:

| Serie | Qué muestra |
|-------|-------------|
| **[MWRR acumulado](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** | Tu rendimiento personal ponderado por dinero, incluyendo el momento de los depósitos |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** | Rendimiento puro de la estrategia de activos, ignorando cuándo depositaste |
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md)** | Rendimiento bruto sobre el capital neto invertido |

La brecha entre MWRR y TWRR es el [Efecto del Momento de las Aportaciones](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md).

!!! note "MWRR no disponible"

    Si aparece un banner de **Calidad de Datos** indicando que MWRR no es fiable, la serie de MWRR se oculta del gráfico %. El problema generalmente ocurre cuando el período tiene flujos de efectivo muy grandes en relación con el tamaño inicial de la cartera, lo que hace que el solucionador matemático sea inestable. ROI y TWRR siempre se muestran.

---

## 🥧 Panel de Asignación {: #allocation-panel }

El panel de asignación muestra cómo está distribuida tu cartera en el momento actual y cómo ha evolucionado históricamente.

<div class="lf-screenshot-carousel" data-carousel="carousel-alloc" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <div class="lf-screenshot-carousel-item is-active alloc-crop-container" data-title="Por Tipo (Actual)" alt="Asignación por Tipo — Actual">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-type-now" alt="Asignación por Tipo — Actual">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Por Sector (Actual)" alt="Asignación por Sector — Actual">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-now" alt="Asignación por Sector — Actual">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Por Geografía (Actual)" alt="Asignación por Geografía — Actual">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-now" alt="Asignación por Geografía — Actual">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Por Tipo (Histórico)" alt="Historial de Asignación por Tipo">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-type-history" alt="Historial de Asignación por Tipo">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Por Sector (Histórico)" alt="Historial de Asignación por Sector">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-history" alt="Historial de Asignación por Sector">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Por Geografía (Histórico)" alt="Historial de Asignación por Geografía">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-history" alt="Historial de Asignación por Geografía">
 </div>
</div>

### Three dimensiones

| Dimensión | Qué muestra |
|-----------|-------------|
| **Tipo** | ETF, Acción, Bono, Cripto, Bienes Raíces, Liquidez (efectivo) |
| **Sector** | Sector industrial: 💻 Tecnología, 🏦 Financiero, 💊 Salud, etc. |
| **Geografía** | País o región de la cotización principal de cada activo |

### Now Ahora vs. Historial

- **Ahora** — Gráfico de donut de la asignación actual en `date_to`. Pasa el cursor sobre cualquier porción para ver el porcentaje exacto y el valor absoluto.
- **Historial** — Gráfico de área apilada al 100% que muestra cómo cambió la asignación con el tiempo. Útil para visualizar el reequilibrio de la cartera a lo largo de meses o años.

### Cash como Liquidez

**Efectivo** (tu saldo del bróker) siempre aparece como la porción de **Liquidez** tanto en las vistas de Tipo como de Sector. En el mapa geográfico, el efectivo no está asignado a ningún país y no aparece.

!!! info "Ámbito del bróker"

    Cuando filtras por brókeres específicos, la asignación muestra solo los activos y el efectivo dentro de esos brókeres.

---

## 🔗 Relacionado

- 💰 **[Tarjetas KPI](kpi-cards.md)** — Patrimonio Neto, PyG del Período, Rendimientos
- 💼 **[NAV / Patrimonio Neto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- 💸 **[Capital Depositado y PyG Total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** · **[MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** · **[Efecto del Momento de las Aportaciones](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)**

---

*[⬅️ Volver a la Descripción General del Panel](index.md)*
