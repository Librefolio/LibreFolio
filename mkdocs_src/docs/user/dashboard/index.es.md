# 📊 Panel de control

El Panel de control es el **centro de comando de tu cartera** — una pantalla única que te indica cuánto vale tu cartera, cómo se está desempeñando y dónde está asignado tu dinero.

<div class="lf-screenshot-carousel" data-carousel="carousel-dashboard-main" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Vista Principal (Absoluto)" alt="Panel de control — Modo Absoluto">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Vista Principal (Porcentaje)" alt="Panel de control — Modo Porcentaje">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-now" data-title="📊 Asignación" alt="Panel de control — Asignación">
</div>

## 🗂️ Diseño de Pestañas

La interfaz del Panel de control está organizada en tres pestañas principales, que te permiten cambiar entre diferentes niveles de detalle:

1. **Descripción general** (predeterminada): Métricas clave, saldos de efectivo y gráficos visuales de tu cartera.
2. **[Posiciones y Análisis](positions.md)**: Tenencias abiertas, pesos y análisis detallado de lotes fiscales (FIFO).
3. **Transacciones**: Lista de operaciones recientes con un visor detallado de solo lectura.

---

## 📈 Pestaña de Descripción general

La pestaña de Descripción general es la página de inicio predeterminada. Está estructurada en las siguientes secciones:

| Sección | Descripción |
|---------|-------------|
| **[Tarjetas KPI](kpi-cards.md)** | Resumen del Valor Neto, PyG del Período y métricas de tasa de retorno. |
| **Saldos de Efectivo** | Saldos líquidos agrupados por moneda dentro del ámbito de brókeres activos. |
| **[Gráfico de Crecimiento](charts.md#portfolio-growth-chart)** | Gráfico de áreas apiladas que muestra el costo de los activos, efectivo y rendimientos a lo largo del tiempo. |
| **[Panel de Asignación](charts.md#allocation-panel)** | Gráficos de dona y de barras apiladas históricos agrupados por Tipo, Sector y Geografía. |

### 🪙 Saldos de Efectivo

Directamente debajo de las tarjetas KPI, el panel de **Saldos de Efectivo** muestra tu efectivo líquido total agregado por moneda. Por ejemplo, si tienes USD en el bróker A y EUR en el bróker B, ambos saldos se mostrarán uno al lado del otro.

Cuando aplicas un filtro de brókeres, los saldos de efectivo se actualizan automáticamente para reflejar solo el efectivo mantenido dentro de los brókeres seleccionados.

---

## 🎛️ Rango de Fechas, Filtros y Exportación IA

En la parte superior derecha del Panel de control, tienes varios controles para personalizar tu vista:

- **Rango de tiempo** — valores predefinidos desde 1 semana hasta Todo el Tiempo (MÁX), o un rango personalizado mediante el selector de fechas.
- **Filtro de bróker** — filtra todas las métricas a uno o más brókeres específicos.
- **Moneda objetivo** — convierte dinámicamente todos los activos y saldos de efectivo en una sola moneda seleccionada para una visión agregada.
- **Exportación IA** (:material-brain:) — Haz clic en este botón para copiar al portapapeles un resumen basado en texto del estado actual de tu cartera, optimizado para pegar en LLMs (ej., Gemini). Puedes elegir entre:
 - **Exportación Completa**: Incluye todos los valores KPI, posiciones, pesos y asignaciones.
 - **Solo Datos**: Una representación compacta en JSON/texto de tus tenencias y saldos.

!!! tip "El ámbito importa"

    Cuando filtras a un solo bróker, las transferencias de efectivo *a otros brókeres* se convierten en flujos externos para ese ámbito. Esto afecta el [Capital Depositado](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md) y el [PyG](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md).

---

## 🌡️ Aviso de Calidad de Datos

Si faltan precios o tipos de cambio FX en la fecha de finalización, aparece un aviso en la parte superior explicando qué activos no pudieron ser valorados. Los activos sin un proveedor de precios (ingresados manualmente, como proyectos de crowdfunding inmobiliario) se valoran permanentemente al costo de compra — esto es intencional y no genera una advertencia.

---

## 🔗 En esta sección

- 💰 **[Tarjetas KPI](kpi-cards.md)** — Valor Neto, PyG del Período y Rendimientos explicados
- 📊 **[Gráficos](charts.md)** — Gráfico de Crecimiento y Panel de Asignación explicados
- 🔍 **[Posiciones y Análisis](positions.md)** — Posiciones abiertas, vistas de tabla vs. mapa, y análisis detallado de lotes fiscales FIFO.

## 🔗 Teoría relacionada

- **[NAV / Valor Neto](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- **[Valor Contable](../../financial-theory/technical-analysis/performance-metrics/book-value.md)**
- **[PyG del Período](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md)**
- **[Capital Depositado y PyG Total](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- **[Resumen de Métricas de Rendimiento](../../financial-theory/technical-analysis/performance-metrics/index.md)**
