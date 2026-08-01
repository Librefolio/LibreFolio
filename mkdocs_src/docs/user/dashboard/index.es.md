# 📊 Panel de control

El panel de control es el **centro de control de tu cartera** — una única pantalla que te muestra el valor de tu cartera, su rendimiento y dónde está asignado tu dinero.

<div class="lf-screenshot-carousel" data-carousel="carousel-dashboard-main" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Vista Principal (Absoluto)" alt="Panel de control — Modo Absoluto">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Vista Principal (Porcentaje)" alt="Panel de control — Modo Porcentaje">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-now" data-title="📊 Asignación" alt="Panel de control — Asignación">
</div>

## 🗂️ Diseño con Pestañas

La interfaz del panel de control está organizada en tres pestañas principales, permitiéndote cambiar entre diferentes niveles de detalle:

1. **Descripción general** (por defecto): Métricas clave, saldos de efectivo y gráficos visuales de tu cartera.
2. **[Posiciones y Análisis](positions.md)**: Posiciones abiertas, ponderaciones y análisis detallado de lotes fiscales (FIFO).
3. **Transacciones**: Lista de operaciones recientes con un visor de detalles de solo lectura.

---

## 📈 Pestaña de Descripción general

La pestaña de Descripción general es la página de inicio predeterminada. Está estructurada en las siguientes secciones:

| Sección | Descripción |
|---------|-------------|
| **[Tarjetas KPI](kpi-cards.md)** | Resumen del Valor Neto, Pérdidas y Ganancias (PyG) del Período y métricas de tasa de rendimiento. |
| **Saldos de Efectivo** | Saldos líquidos agrupados por moneda dentro del ámbito del bróker activo. |
| **[Gráfico de Crecimiento](charts.md#portfolio-growth-chart)** | Gráfico de áreas apiladas que muestra el costo de los activos, el efectivo y los rendimientos a lo largo del tiempo. |
| **[Panel de Asignación](charts.md#allocation-panel)** | Gráficos de dona e históricos apilados agrupados por Tipo, Sector y Geografía. |

### 🪙 Saldos de Efectivo

Directamente debajo de las tarjetas KPI, el panel de **Saldos de Efectivo** muestra tu efectivo líquido total agregado por moneda. Por ejemplo, si tienes USD en el bróker A y EUR en el bróker B, ambos saldos se mostrarán uno al lado del otro.

Cuando aplicas un filtro de bróker, los saldos de efectivo se actualizan automáticamente para reflejar solo el efectivo mantenido dentro de los brókeres seleccionados.

---

## 🎛️ Rango de Fechas, Filtros y Exportación IA

En la parte superior derecha del panel de control, tienes varios controles para personalizar tu vista:

- **Rango de tiempo**: predefinidos desde 1 semana hasta Todo el tiempo (MAX), o un rango personalizado a través del selector de fechas.
- **Filtro de bróker**: filtra todas las métricas a uno o más brókeres específicos.
- **Moneda objetivo**: convierte dinámicamente todos los activos y saldos de efectivo a una única moneda seleccionada para una vista agregada.
- **Exportación de IA** (:material-brain:) — abre una exportación al portapapeles.
  Elige **Instantánea de datos** para copiar solo datos factuales, o una **tarea
  de análisis** que incluye automáticamente sus instrucciones y su contrato de
  respuesta; después, selecciona el **nivel de detalle** (Compacto, Estándar o
  Completo). La instantánea del backend sigue el filtro de bróker activo, el
  rango de fechas y la moneda objetivo; LibreFolio no contacta con servicios de
  IA. Consulta la [guía de Exportación de IA](../ai-export/index.md).

!!! tip "El ámbito importa"

    Cuando filtras a un solo bróker, las transferencias de efectivo *a otros brókeres* se convierten en flujos externos para ese ámbito. Esto afecta los cálculos de [Capital Depositado](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) y [PyG](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md).

---

## 🌡️ Banner de Calidad de Datos

Si faltan precios o tipos de cambio en la fecha de finalización, aparece un banner en la parte superior explicando qué activos no pudieron ser valorados. Los activos sin un proveedor de precios (ingresados manualmente, como proyectos de crowdfunding inmobiliario) se valoran permanentemente al costo de compra; esto es intencional y no genera una advertencia.

---

## 🔗 En esta sección

- 💰 **[Tarjetas KPI](kpi-cards.md)** — Valor Neto, PyG del Período y Rendimientos explicados
- 📊 **[Gráficos](charts.md)** — Gráfico de Crecimiento y Panel de Asignación explicados
- 🔍 **[Posiciones y Análisis](positions.md)** — Posiciones abiertas, vistas de tabla vs. mapa y análisis detallado de lotes fiscales FIFO.

## 🔗 Teoría relacionada

- **[NAV / Valor Neto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- **[Valor Contable](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)**
- **[PyG del Período](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)**
- **[Capital Depositado y PyG Total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- **[Resumen de Métricas de Rendimiento](../../financial-theory/technical-analysis/performance-metrics/index.md)**
