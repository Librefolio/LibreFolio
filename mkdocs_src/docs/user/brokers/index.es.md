# 🏦 Brókeres

Un **bróker** en LibreFolio representa una cuenta de corretaje — el lugar donde residen tus inversiones (por ejemplo, Interactive Brokers, Degiro, una cuenta bancaria).

Todas las transacciones, informes y datos de importación están vinculados a un bróker. Necesitas al menos un bróker para empezar a rastrear tu cartera.

!!! note "Los brókeres compartidos muestran tu participación"

    En un bróker que coposees, el patrimonio neto mostrado en la tarjeta del bróker (y en la pestaña Descripción general del bróker) se **escala según tu porcentaje de propiedad** — un Propietario al 50% ve la mitad del valor de la cuenta. Los Editores y Visores siempre ven los importes completos. Consulta [Uso compartido del bróker](sharing.md).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="list" alt="Lista de brókeres" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## ➕ Creando un bróker

1. Navega a la página de **Brókeres** desde la barra lateral
2. Haz clic en **"Agregar Bróker"**
3. Completa los detalles: nombre, moneda base y, opcionalmente, un ícono
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Formulario de edición del bróker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

4. El bróker aparece en tu lista, listo para recibir transacciones e informes
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="detail" alt="Formulario de edición del bróker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>
---

## 🗂️ Disposición de detalles del bróker

Una vez que seleccionas un bróker de la lista, la interfaz se divide en cuatro pestañas principales:

1. **Descripción general**: Visualización del patrimonio neto, métricas de rendimiento, historial de crecimiento y gráficos de asignación limitados exclusivamente a esta cuenta de corretaje (ver **[Descripción general del panel de control](../dashboard/index.md)**).
2. **Posiciones**: Lista de posiciones abiertas, ponderaciones de activos y métricas de rendimiento dentro de este bróker, con acceso al panel en línea de Análisis de Lotes FIFO (ver **[Posiciones del panel de control](../dashboard/positions.md)**).
3. **Transacciones**: El registro de todas las actividades financieras, incluyendo entradas manuales, importaciones de estados de cuenta e historiales (ver **[Transacciones del bróker](import.md)**).
4. **Información**: Metadatos del bróker, configuraciones de sobregiro/venta en corto, Exportación de IA y controles de uso compartido en línea (ver **[Configuración e información](info.md)** y **[Broker AI Export](../ai-export/broker.md)**).

---

## 📈 Pestaña de Descripción general

La pestaña **Descripción general** actúa como un panel de control local para el bróker seleccionado. Contiene los mismos elementos que la **[Descripción general del panel de control](../dashboard/index.md)** principal, pero limitados exclusivamente a esta cuenta de corretaje:

- **Tarjetas KPI locales**: Patrimonio Neto, Pérdidas y Ganancias del Período y Rendimientos específicos de este bróker. (Ver **[Tarjetas KPI del panel de control](../dashboard/kpi-cards.md)** para detalles de cálculo).
- **Panel de saldos en efectivo**: Efectivo líquido mantenido en esta cuenta de corretaje, desglosado por moneda.
- **Gráfico de crecimiento**: Crecimiento histórico del valor de esta cuenta (ver **[Gráfico de crecimiento de la cartera](../dashboard/charts.md#portfolio-growth-chart)**).
- **Panel de asignación**: Composición de la cartera (por Tipo, Sector y Geografía) para las posiciones mantenidas en este bróker específico (ver **[Panel de asignación](../dashboard/charts.md#allocation-panel)**).

---

## 🔍 Pestaña de Posiciones

La pestaña **Posiciones** enumera todos los activos activos actualmente mantenidos bajo este bróker. Es idéntica en funcionalidad a la vista principal de **[Posiciones del panel de control](../dashboard/positions.md)**, pero limitada solo a este bróker:

<div class="lf-screenshot-carousel" data-carousel="carousel-broker-positions" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="positions-holdings-table" data-title="📋 Posiciones (Tabla)" alt="Vista de tabla de posiciones del bróker">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-holdings-map" data-title="🗺️ Posiciones (Mapa / Treemap)" alt="Vista de mapa de posiciones del bróker">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-table" data-title="📈 Rendimiento (Tabla)" alt="Vista de tabla de rendimiento del bróker">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-map" data-title="📊 Rendimiento (Mapa / Gráfico)" alt="Vista de mapa de rendimiento del bróker">
</div>

- **Interruptores y diseños**: Puedes alternar entre métricas de **Posición** (cantidades, valores, ponderaciones) y **Rendimiento** (P&L no realizado, % ROI), y elegir entre un diseño de **Tabla** o **Mapa** (treemap).
- **Análisis FIFO**: Haz clic en cualquier fila o tarjeta de activo para expandir el panel de **Análisis de Lotes FIFO** en línea debajo de la lista. (Ver **[Análisis de Lotes FIFO](../dashboard/positions.md#fifo-lots-analysis)** para reglas de coincidencia detalladas).

---

## 📑 En Esta Sección

- 📥 **[Transacciones del bróker](import.md)** — Registra transacciones manualmente con alcance limitado a este bróker, inicia el asistente de importación masiva BRIM y gestiona los archivos de informes subidos.
- ⚙️ **[Configuración e información](info.md)** — Ajustes de metadatos (sobregiros, ventas en corto), generador de indicaciones de Exportación de IA limitadas y el panel de uso compartido de bróker en línea.
- 🤝 **[Uso compartido del bróker](sharing.md)** — Guía detallada sobre permisos de roles (Propietario, Editor, Visor) y configuraciones de porcentaje de activos.
- 🧠 **[Broker AI Export](../ai-export/broker.md)** — Tareas con alcance de broker, cobertura de datos, muestreo exacto, disponibilidad y privacidad.

