# 🏦 Brókers

Un **bróker** en LibreFolio representa una cuenta de corretaje — el lugar donde residen tus inversiones (por ejemplo, Interactive Brokers, Degiro, una cuenta bancaria).

Todas las transacciones, informes y datos de importación están vinculados a un bróker. Necesitas al menos un bróker para comenzar a rastrear tu cartera.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="list" alt="Lista de brókers" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## ➕ Creando un bróker

1. Navega a la página **Brókers** desde la barra lateral
2. Haz clic en **"Nuevo bróker"**
3. Completa los detalles: nombre, moneda base y opcionalmente un icono
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Formulario de edición de bróker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

4. El bróker aparece en tu lista, listo para recibir transacciones e informes
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="detail" alt="Formulario de edición de bróker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>
---

## 🗂️ Diseño de detalle del bróker

Una vez que seleccionas un bróker de la lista, la interfaz se divide en cuatro pestañas principales:

1. **Descripción general**: Visualización del patrimonio neto, métricas de rendimiento, historial de crecimiento y gráficos de asignación limitados exclusivamente a esta cuenta de bróker (consulta **[Descripción general del panel de control](../dashboard/index.md)**).
2. **Posiciones**: Lista de posiciones abiertas, ponderaciones de activos y métricas de rendimiento dentro de este bróker, con acceso al panel deslizante de Lotes FIFO (consulta **[Posiciones del panel de control](../dashboard/positions.md)**).
3. **Transacciones**: El registro de todas las actividades financieras, incluyendo entradas manuales, importaciones de extractos e historiales (consulta **[Importando transacciones](import.md)**).
4. **Información**: Metadatos del bróker, configuraciones de sobregiro en efectivo/ventas en corto, Exportación con IA y controles de uso compartido en línea (consulta **[Configuración e información](info.md)**).

---

## 📈 Pestaña de Descripción general

La pestaña **Descripción general** actúa como un panel de control local para el bróker seleccionado. Contiene los mismos elementos que la **[Descripción general del panel de control](../dashboard/index.md)** principal, pero limitados exclusivamente a esta cuenta de bróker:

- **Tarjetas KPI Locales**: Patrimonio Neto, PyG del Período y Rendimientos específicos de este bróker. (Consulta **[Tarjetas KPI del panel de control](../dashboard/kpi-cards.md)** para detalles de cálculo).
- **Panel de Saldos en Efectivo**: Efectivo líquido mantenido en esta cuenta de bróker, desglosado por moneda.
- **Gráfico de Crecimiento**: Crecimiento histórico del valor de esta cuenta (consulta **[Gráfico de crecimiento de la cartera](../dashboard/charts.md#portfolio-growth-chart)**).
- **Panel de Asignación**: Composición de la cartera (por Tipo, Sector y Geografía) para las posiciones mantenidas en este bróker específico (consulta **[Panel de Asignación](../dashboard/charts.md#allocation-panel)**).

---

## 🔍 Pestaña de Posiciones

La pestaña **Posiciones** lista todos los activos activos actualmente mantenidos bajo este bróker. Es idéntica en funcionalidad a la vista principal **[Posiciones del panel de control](../dashboard/positions.md)**, pero limitada solo a este bróker:

<div class="lf-screenshot-carousel" data-carousel="carousel-broker-positions" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="positions-holdings-table" data-title="📋 Posiciones (Tabla)" alt="Vista de tabla de posiciones del bróker">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-holdings-map" data-title="🗺️ Posiciones (Mapa / Treemap)" alt="Vista de mapa de posiciones del bróker">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-table" data-title="📈 Rendimiento (Tabla)" alt="Vista de tabla de rendimiento del bróker">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-map" data-title="📊 Rendimiento (Mapa / Gráfico)" alt="Vista de mapa de rendimiento del bróker">
</div>

- **Alternancias y Diseños**: Puedes alternar entre métricas de **Posiciones** (cantidades, valores, ponderaciones) y **Rendimiento** (PyG no realizada, % ROI), y elegir entre un diseño de **Tabla** o **Mapa** (treemap).
- **Análisis FIFO**: Haz clic en cualquier fila o tarjeta de activo para abrir el panel deslizante de **Análisis de Lotes FIFO**. (Consulta **[Análisis de Lotes FIFO](../dashboard/positions.md#fifo-lots-analysis)** para reglas de emparejamiento detalladas).

---

## 📑 En Esta Sección

- 📥 **[Importando transacciones (BRIM)](import.md)** — Cómo registrar transacciones manualmente, ejecutar el asistente de importación CSV/Excel de BRIM y ver registros de importación.
- ⚙️ **[Configuración e información](info.md)** — Configuraciones de metadatos (sobregiros, ventas en corto), generador de indicaciones de Exportación con IA limitado y panel de uso compartido del bróker en línea.
- 🤝 **[Uso compartido del bróker](sharing.md)** — Guía detallada sobre permisos de roles (Propietario, Editor, Visor) y configuraciones de porcentaje de activos.
