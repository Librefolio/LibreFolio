# 🏦 Brókers

Un **bróker** es una de tus cuentas — en una casa de bolsa, un banco o un exchange: el lugar donde viven tus inversiones y tu efectivo. Cada transacción y cada informe subido pertenece a un bróker, así que necesitas al menos uno antes de empezar.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="list" alt="Lista de brókers" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La página **Brókers** muestra una tarjeta por cada bróker, con su valor (**NAV**) en la divisa elegida en **Divisa** en la parte superior de la página. Haz clic en una tarjeta para abrir el bróker.

!!! note "Los brókers compartidos muestran tu participación"

    En un bróker del que eres copropietario, los valores de su tarjeta y de su pestaña **Resumen** se **escalan según tu porcentaje de propiedad**: un Propietario con el 50% ve la mitad de la cuenta. Los Editores y los Lectores siempre ven los importes completos. Consulta [Compartir brókers](sharing.md).

---

## ➕ Crear un bróker

1. Abre **Brókers** desde la barra lateral y haz clic en **Añadir bróker**.
2. Escribe un **Nombre** — el único campo obligatorio — y configura las opciones que necesites.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Formulario de edición del bróker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

3. Haz clic en **Crear**: el bróker aparece en tu lista, listo para transacciones e informes.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="detail" alt="Formulario de edición del bróker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

??? info "⚙️ Los campos opcionales: qué hace cada uno"

    - **Descripción** — tus propias notas.
    - **Plugin de importación predeterminado** — el importador que el [Asistente de importación](../transactions/import/index.md) propone para los archivos de este bróker.
    - **URL del portal** — el sitio web del bróker, que se abre desde la página del bróker. Su icono se usa cuando no configuras una **URL de icono personalizado**.
    - **Cuenta abierta** y **Cuenta activa** — cuándo se abrió la cuenta y si sigue abierta. Un bróker cerrado aparece atenuado en la lista.
    - **Opciones de trading** — **Permitir compra apalancada** y **Permitir venta en corto**, explicadas en [Opciones de trading](info.md#trading-options).
    - **Saldos iniciales** (solo al crear) — tu efectivo inicial. LibreFolio registra un **Depósito** por divisa, **con fecha de hoy**: si el dinero ya estaba ahí antes, cambia la fecha de esos depósitos en la página [Transacciones](../transactions/index.md).

??? warning "🏷️ “Ya existe un bróker llamado…” — cuándo aparece"

    Los nombres de bróker son únicos en todo el servidor, entre todos sus usuarios. Elige otro nombre o cambia el nombre del bróker existente si es tuyo.

    Los brókers de otros usuarios que no puedes abrir aparecen en **Otros brókers existentes**. Su botón de compartir muestra quién tiene acceso, para que sepas a quién preguntar: cualquier usuario con sesión iniciada en este LibreFolio puede verlo, para cualquier bróker.

---

## ✏️ Editar o eliminar un bróker

- **Editar** — el lápiz de la tarjeta del bróker o **Editar** en la barra de herramientas del bróker. Los Propietarios y los Editores pueden editar un bróker.
- **Eliminar** — la papelera de la tarjeta del bróker. Solo un Propietario puede eliminar un bróker. Si aún contiene transacciones, LibreFolio indica cuántas y ofrece **Ir a transacciones** o **Eliminar bróker y transacciones**, que las elimina también.

---

## 🗂️ Dentro de un bróker

La barra de herramientas de la parte superior se aplica a todas las pestañas:

- el **rango de fechas** y la **Divisa** de las cifras;
- **Editar**, **Compartir bróker** (abre la pestaña **Info**) y **Actualizar**;
- **Exportación IA**, que copia al portapapeles un prompt ya preparado sobre este bróker; consulta [Exportación IA de bróker](../ai-export/broker.md).

Debajo, cinco pestañas:

1. **Resumen** — cómo va la cuenta (más abajo).
2. **Posiciones** — lo que tienes en este bróker (más abajo).
3. **Riesgo** — el análisis de riesgos del Panel, limitado a este bróker (consulta [Pestaña Riesgo del Panel](../dashboard/index.md#risk-tab)).
4. **Transacciones** — el libro mayor de este bróker, entradas manuales, importaciones e informes subidos (consulta [Transacciones del bróker](import.md)).
5. **Info** — detalles de la cuenta, opciones de trading y uso compartido (consulta [Configuración e información](info.md)).

---

## 📈 Pestaña Resumen

La pestaña **Resumen** responde a “¿cómo va esta cuenta?” con los mismos bloques que el [Resumen del Panel](../dashboard/index.md), limitados a este bróker:

- **Tarjetas KPI** — **P&L período**, **Rentabilidades** y **Patrimonio neto** ([Tarjetas KPI](../dashboard/kpi-cards.md)).
- **Saldos de efectivo** — el efectivo que hay aquí, por divisa.
- **Gráfico de crecimiento** — las vistas **Abs**, **%** y **P&L**, con el P&L como **Línea**, **Velas** o **Ingresos** ([Gráfico de crecimiento de la cartera](../dashboard/charts.md#portfolio-growth-chart), [Modo P&L](../dashboard/charts.md#pnl-mode)). La vista que elijas se comparte con el Panel.
- **Asignación** — por tipo, sector y zona geográfica ([Panel de asignación](../dashboard/charts.md#allocation-panel)).

Volver a un bróker que ya abriste muestra sus últimas cifras al instante, actualizadas en segundo plano si algo cambió ([Volver y actualizar](../dashboard/index.md#coming-back-and-refreshing)). **Actualizar** recalcula a petición, incluida la pestaña **Riesgo** y el panel de lotes.

---

## 🔍 Pestaña Posiciones

La pestaña **Posiciones** lista lo que tienes en este bróker, en el mismo panel que las [Posiciones del Panel](../dashboard/positions.md):

<div class="lf-screenshot-carousel" data-carousel="carousel-broker-positions" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="positions-holdings-table" data-title="📋 Posiciones (Tabla)" alt="Vista de tabla de posiciones del bróker">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-holdings-map" data-title="🗺️ Posiciones (Mapa / Treemap)" alt="Vista de mapa de posiciones del bróker">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-table" data-title="📈 Rendimiento (Tabla)" alt="Vista de tabla de rendimiento del bróker">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-map" data-title="📊 Rendimiento (Mapa / Gráfico)" alt="Vista de mapa de rendimiento del bróker">
</div>

- **Cartera** muestra tus posiciones (cantidad, valor, peso); **Periodo** muestra las ganancias y pérdidas de cada posición en las fechas seleccionadas. Ambos se presentan como **Tabla** o **Mapa**.
- La columna **YOC** muestra el [Rendimiento sobre coste](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/yield-on-cost.md) de cada posición en este bróker.
- **Analizar lotes** abre el panel de [Análisis de lotes FIFO](../dashboard/positions.md#fifo-lots-analysis) debajo de la lista: lo encontrarás en el menú **⋮** de una fila, o haz clic con el botón derecho en el activo de la tabla o del mapa.

---

## 📑 En esta sección

- 📥 **[Transacciones del bróker](import.md)** — añade transacciones a este bróker, importa extractos y gestiona sus informes subidos.
- ⚙️ **[Configuración e información](info.md)** — detalles de la cuenta, opciones de trading y el panel para compartir.
- 🧠 **[Exportación IA de bróker](../ai-export/broker.md)** — qué contiene una exportación de bróker y los análisis que puedes pedirle a una IA.
- 🤝 **[Compartir brókers](sharing.md)** — roles (Propietario, Editor, Lector) y porcentajes de propiedad.

La página Brókers, el formulario **Añadir bróker** y la página del bróker tienen cada uno una breve guía contextual: puedes repetirlas desde [Configuración → Preferencias → Introducción y guías](../settings/preferences.md#onboarding-and-guides).
