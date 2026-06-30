# 📊 Dashboard

El Panel Principal (Dashboard) es el **centro de comando de su cartera** — una sola pantalla que le indica cuánto vale su cartera, cómo está rindiendo y cómo está distribuido su dinero.

<div class="lf-screenshot-carousel" data-carousel="carousel-dashboard-main" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Vista Principal (Absoluto)" alt="Dashboard — Modo Absoluto">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Vista Principal (Porcentaje)" alt="Dashboard — Modo Porcentaje">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-now" data-title="📊 Asignación" alt="Dashboard — Asignación">
</div>

---

## 🗂️ Estructura (Layout)

| Sección | Ubicación | Contenido |
|---------|-----------|-----------|
| **[Tarjetas KPI](kpi-cards.md)** | Fila superior | [Patrimonio Neto](kpi-cards.md#card-1--net-worth) · [P&L del Periodo](kpi-cards.md#card-2--period-pl) · [Rendimientos](kpi-cards.md#card-3--returns) |
| **[Gráfico de Crecimiento](charts.md#portfolio-growth-chart)** | Centro izquierda | Área apilada absoluta + serie de rendimiento porcentual |
| **[Panel de Asignación](charts.md#allocation-panel)** | Centro derecha + inferior | Tipo / Sector / Geografía — actual e histórico |

---

## 🎛️ Rango de Fechas & Filtro de Bróker

En la parte superior del panel principal puede seleccionar:

- **Rango de tiempo** — preajustes desde 1 semana hasta Siempre (All-Time), o un rango personalizado mediante el selector de fechas
- **Filtro de bróker** — muestra todos los brókers o se enfoca en uno o más
- **Moneda objetivo** — convierte todos los valores a una única moneda de su elección

!!! tip "El alcance importa"

    Cuando filtra por un solo bróker, las transferencias de efectivo *a otros brókers* se convierten en flujos externos para ese alcance. Esto afecta los cálculos de [Capital Depositado](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md) y [P&L del Periodo](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md).

---

## 🌡️ Banner de Calidad de Datos

Si faltan precios o tipos de cambio (FX) en la fecha de finalización, aparece un banner en la parte superior detallando qué activos no pudieron ser valorados. Los activos sin proveedor de precios (introducidos manualmente, como los proyectos de crowdfunding inmobiliario) se valoran permanentemente al coste de compra — esto es intencionado y no genera ninguna advertencia.

---

## 🔗 En esta sección

- 💰 **[Tarjetas KPI](kpi-cards.md)** — Explicación de Patrimonio Neto, P&L del Periodo y Rendimientos
- 📊 **[Gráficos](charts.md)** — Explicación del Gráfico de Crecimiento y el Panel de Asignación

## 🔗 Teoría relacionada

- **[NAV / Patrimonio Neto](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- **[Valor Contable](../../financial-theory/technical-analysis/performance-metrics/book-value.md)**
- **[P&L del Periodo](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md)**
- **[Capital Depositado & P&L Total](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- **[Resumen de Metricas de Rendimiento](../../financial-theory/technical-analysis/performance-metrics/index.md)**
