# 🏦 Brókeres

Un **bróker** es una de tus cuentas —en una correduría, un banco o una bolsa—: el lugar donde viven tus inversiones y tu efectivo. Cada transacción y cada informe subido pertenece a un bróker, así que necesitas al menos uno antes de empezar.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="list" alt="Lista de brókeres" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La página **Brókeres** muestra una tarjeta por bróker, con su valor (**NAV**) en la divisa elegida en **Divisa** en la parte superior de la página. Haz clic en una tarjeta para abrir el bróker.

**Ganancia/Pérdida** es el NAV menos el capital aportado al bróker: tus depósitos menos los retiros, más el coste de los valores que aportaste sin efectivo, más lo que trasladaste desde tus otros brókeres menos lo que trasladaste fuera, con cada movimiento valorado el día en que llegó. Así, mover dinero o valores entre dos de tus brókeres no es una ganancia en una tarjeta y una pérdida en la otra, y mientras una transferencia está en tránsito, su valor permanece en la tarjeta del bróker emisor. El efectivo mantenido en otra divisa se valora al último tipo de cambio, por lo que el efecto del tipo de cambio sobre él cuenta en Ganancia/Pérdida, no en el capital. El porcentaje entre paréntesis es la ganancia sobre ese capital: muestra 0,00 % cuando ese capital es cero o negativo, por ejemplo cuando el bróker ha enviado más de lo que recibió. → [Transferencias internas](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#internal-transfers-broker-lines)

!!! note "Los brókeres compartidos muestran tu parte en la tarjeta"

    En un bróker del que eres copropietario, los valores de su tarjeta **se ajustan proporcionalmente a tu porcentaje de propiedad**: un Propietario al 50 % ve la mitad de la cuenta. Los Editores y los Lectores ven los importes completos. La página propia del bróker muestra la cuenta completa a todos; consulta [La página del bróker es el panel de un solo bróker](#broker-page-is-dashboard). Consulta [Uso compartido de brókeres](sharing.md).

---

## ➕ Crear un bróker

1. Abre **Brókeres** en la barra lateral y haz clic en **Añadir bróker**.
2. Escribe un **Nombre** —el único campo obligatorio— y configura las opciones que necesites.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Formulario de edición del bróker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

3. Haz clic en **Crear**: el bróker aparece en tu lista, listo para transacciones e informes.

??? info "⚙️ Los campos opcionales — qué hace cada uno"

    - **Descripción** — tus propias notas.
    - **Plugin de importación predeterminado** — el importador que el [Asistente de importación](../transactions/import/index.md) propone para los archivos de este bróker.
    - **URL del portal** — el sitio web del bróker, que se abre desde la página del bróker. El icono del bróker es, en este orden: tu **URL de icono personalizado**; el icono del **Plugin de importación predeterminado**, cuando ese importador está hecho para este bróker; el icono del sitio web; el icono de un importador genérico como el CSV genérico; de lo contrario, un maletín.
    - **Cuenta abierta** y **Cuenta activa** — cuándo se abrió la cuenta y si sigue abierta. Un bróker cerrado se muestra atenuado en la lista.
    - **Opciones de trading** — **Permitir compra apalancada** y **Permitir ventas en corto**, explicadas en [Opciones de trading](info.md#trading-options).
    - **Saldos iniciales** (solo al crear) — tu efectivo inicial. LibreFolio registra un **Depósito** por divisa, **con fecha de hoy**: si el dinero ya estaba allí antes, cambia la fecha de esos depósitos en la página [Transacciones](../transactions/index.md).

??? warning "🏷️ «Ya existe un bróker llamado …» — cuándo aparece"

    Los nombres de bróker son únicos en todo el servidor, entre todos sus usuarios. Elige un nombre diferente o cambia el nombre del bróker existente si es tuyo.

    Los brókeres de otros usuarios que no puedes abrir aparecen en **Otros brókeres existentes**. Su botón de compartir muestra quién tiene acceso, para que sepas a quién preguntar: todos los usuarios que hayan iniciado sesión en este LibreFolio pueden verlo, para cualquier bróker.

---

## ✏️ Editar o eliminar un bróker

- **Editar** — el lápiz de la tarjeta del bróker o **Editar** en la barra de herramientas del bróker. Los Propietarios y los Editores pueden editar un bróker.
- **Eliminar** — el icono de papelera de la tarjeta del bróker. Solo un Propietario puede eliminar un bróker. Si todavía contiene transacciones, LibreFolio indica cuántas y ofrece **Ir a transacciones** o **Eliminar bróker y transacciones**, lo que también las elimina. Los activos que transfirió a otro bróker, incluido uno compartido, permanecen allí como posición de apertura a su coste de transferencia, a partir de la fecha de transferencia: la ganancia de ese bróker también cuenta entonces lo que ganaron antes de la transferencia. Los activos que otro bróker le transfirió salen de ese otro bróker como un ajuste que extrae las unidades: no tiene valor, por lo que las unidades solo salen de la cantidad y su coste cuenta como pérdida realizada allí ([Ajustes salientes](../../financial-theory/instruments/transaction-types/adjustment.md#outgoing-adjustments)). Las transferencias de fondos con otro bróker se convierten en un depósito o un retiro allí.

---

## 🗂️ Dentro de un bróker

La tarjeta de un bróker abre su página en la pestaña **Resumen**:

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="detail" alt="Detalle del bróker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

En la parte superior, el encabezado muestra el nombre del bróker, su icono y, como insignia, tu rol y tu porcentaje de propiedad. La barra de herramientas inferior se aplica a todas las pestañas:

- el **rango de fechas** y la **Divisa** de las cifras, con la misma lista que en el panel, incluida **Crear forex**;
- **Editar** (Propietarios y Editores) y **Compartir bróker**, que abre la pestaña **Información**;
- **Exportación IA**, que copia al portapapeles un prompt ya preparado sobre este bróker; consulta [Exportación IA del bróker](../ai-export/broker.md);
- **Actualizar**, que recalcula la página a petición.

Debajo, cinco pestañas:

1. **Resumen** — cómo va la cuenta (más abajo).
2. **Posiciones** — lo que tienes en este bróker (más abajo).
3. **Riesgo** — el análisis de riesgos del panel, limitado a este bróker (consulta [Pestaña Riesgo del panel](../dashboard/index.md#risk-tab)).
4. **Transacciones** — el libro mayor del bróker, las entradas manuales, las importaciones y los informes subidos (consulta [Transacciones del bróker](import.md)).
5. **Información** — detalles de la cuenta, opciones de trading y uso compartido (consulta [Configuración e información](info.md)).

---

## 🧭 La página del bróker es el panel de un solo bróker {: #broker-page-is-dashboard }

La página de un bróker es el [panel](../dashboard/index.md) con ese bróker ya seleccionado, más la pestaña **Información** propia del bróker. Los controles, las pestañas y sus paneles funcionan como se describe en las páginas del panel; no hay filtro de bróker, porque la página corresponde a un solo bróker.

Lo que es igual que en el panel:

- **Periodo, divisa y botones.** El rango de fechas, el menú **Divisa**, **Exportación IA** y **Actualizar** son los del panel. Cuando no has usado la página durante dos minutos, el botón **Actualizar** muestra el icono de pausa y un tono más apagado, y su información emergente dice que las actualizaciones están en pausa: haz clic en él para actualizar los precios de nuevo (consulta **Precios en vivo** en la página [Activos](../assets/index.md)).
- **Los saldos de efectivo siguen el periodo.** Muestran el efectivo al final del periodo que elegiste.
- **Lotes.** **Analizar lotes** abre el detalle de lotes debajo de la lista; el botón **Atrás** del navegador lo cierra. **Ver todo →** abre la página de Activos en el mismo periodo.
- **Banner de calidad de datos.** Los precios obsoletos y los tipos de cambio ausentes u obsoletos también se notifican aquí, con los mismos botones **Sincronizar precios** y **Sincronizar tipos** ([Banner de calidad de datos](../dashboard/index.md#data-quality-banner)). Todos los roles los ven, incluido un Lector: actualizan precios y tipos de cambio compartidos, no el bróker.

Lo que es diferente:

- **El bróker completo.** Cada importe de la página, incluido Riesgo, es el importe **completo** del bróker (100 %), también cuando posees menos del 100 % de él. La insignia del encabezado muestra tu rol y tu porcentaje. El panel filtrado por el mismo bróker muestra tu parte de él.
- **Las transacciones siguen el periodo.** La pestaña Transacciones enumera las transacciones del rango de fechas elegido en la barra de herramientas, y **Ver en Transacciones** abre la página [Transacciones](../transactions/index.md) con el mismo periodo. **Importar**, **Añadir transacción**, **Editar**, **Clonar**, **Eliminar** y la barra de selección son para Propietarios y Editores; un Lector ve la tabla, el historial de importaciones y **Ver en Transacciones**.

---

## 📈 Pestaña Resumen

El **Resumen** responde a «¿cómo va esta cuenta?» con los mismos bloques que el [Resumen del panel](../dashboard/index.md), limitados a este bróker:

- **Tarjetas KPI** — **P&L período**, **Rentabilidades** y **Patrimonio neto** ([Tarjetas KPI](../dashboard/kpi-cards.md)).
- **Saldos de efectivo** — el efectivo mantenido aquí al final del periodo, por divisa.
- **Gráfico de crecimiento** — las vistas **Abs**, **%** y **P&L**, con el P&L como **Línea**, **Velas** o **Ingresos** ([Gráfico de crecimiento de la cartera](../dashboard/charts.md#portfolio-growth-chart), [Modo P&L](../dashboard/charts.md#pnl-mode)). La vista que elijas se comparte con el panel.
- **Asignación** — por tipo, sector y geografía ([Panel de asignación](../dashboard/charts.md#allocation-panel)).

Volver a un bróker que ya abriste muestra sus últimas cifras de inmediato, actualizadas en segundo plano si algo cambió ([Volver y actualizar](../dashboard/index.md#coming-back-and-refreshing)). **Actualizar** recalcula a petición, lo que incluye la pestaña **Riesgo** y el panel de lotes.

---

## 🔍 Pestaña Posiciones

La pestaña **Posiciones** enumera lo que tienes en este bróker, en el mismo panel que las [Posiciones del panel](../dashboard/positions.md):

<div class="lf-screenshot-carousel" data-carousel="carousel-broker-positions" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="positions-holdings-table" data-title="📋 Cartera (tabla)" alt="Vista de tabla de la cartera del bróker">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-holdings-map" data-title="🗺️ Cartera (mapa / treemap)" alt="Vista de mapa de la cartera del bróker">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-table" data-title="📈 Periodo (tabla)" alt="Vista de tabla del periodo del bróker">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-map" data-title="📊 Periodo (mapa / gráfico)" alt="Vista de mapa del periodo del bróker">
</div>

- **Cartera** muestra tus posiciones (cantidad, valor, peso); **Periodo** muestra las ganancias y pérdidas de cada posición durante las fechas seleccionadas. Ambos se presentan como **Tabla** o **Mapa**.
- La columna **YOC** es el [rendimiento sobre coste](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/yield-on-cost.md) de cada posición en este bróker.
- **Analizar lotes** abre el panel de [Análisis de lotes FIFO](../dashboard/positions.md#fifo-lots-analysis) debajo de la lista: encuéntralo en el menú **⋮** de una fila o haz clic con el botón derecho en el activo de la tabla o del mapa.

---

## 📑 En esta sección

- 📥 **[Transacciones del bróker](import.md)** — añade transacciones a este bróker, importa extractos y gestiona sus informes subidos.
- ⚙️ **[Configuración e información](info.md)** — detalles de la cuenta, opciones de trading y el panel de uso compartido.
- 🧠 **[Exportación IA del bróker](../ai-export/broker.md)** — qué contiene la exportación de un bróker y los análisis que puedes pedir a una IA.
- 🤝 **[Uso compartido de brókeres](sharing.md)** — roles (Propietario, Editor, Lector) y porcentajes de propiedad.

La página Brókeres, el formulario **Añadir bróker** y la página del bróker tienen cada uno una breve guía contextual: puedes repetirlas desde [Configuración → Preferencias → Introducción y guías](../settings/preferences.md#onboarding-and-guides).
