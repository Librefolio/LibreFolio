# 📊 Panel

El Panel es el **centro de control de tu cartera** — una única pantalla que te dice cuánto vale tu cartera, cómo se está comportando y dónde está asignado tu dinero.

<div class="lf-screenshot-carousel" data-carousel="carousel-dashboard-main" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Vista principal (absoluta)" alt="Panel — Modo absoluto">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Vista principal (porcentaje)" alt="Panel — Modo porcentaje">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-now" data-title="📊 Asignación" alt="Panel — Asignación">
</div>

## 🗂️ Diseño por pestañas

La interfaz del Panel está organizada en cuatro pestañas principales, que te permiten cambiar entre distintos niveles de detalle:

1. **Resumen** (predeterminada): métricas clave, saldos de efectivo y gráficos visuales de tu cartera.
2. **[Posiciones y análisis](positions.md)**: posiciones abiertas, ponderaciones y análisis detallado de lotes fiscales (FIFO).
3. **[Riesgo](#risk-tab)**: el panel de **Riesgo de la cartera**, que responde a cuatro preguntas sobre el riesgo de tu cartera.
4. **Transacciones**: las operaciones del rango de fechas y del ámbito de brókeres seleccionados, como una lista paginada de solo lectura — haz doble clic en una fila para abrir su visor de detalle. Consulta [Transacciones](../transactions/index.md) para la guía completa.

---

## 📈 Pestaña Resumen

La pestaña Resumen es la página de inicio predeterminada. Está estructurada en las siguientes secciones:

| Sección | Descripción |
|---------|-------------|
| **[Tarjetas KPI](kpi-cards.md)** | Resumen del Patrimonio neto, el P&L período y las métricas de tasa de retorno. |
| **Saldos de efectivo** | Saldos líquidos agrupados por divisa en el ámbito de brókeres activo. |
| **[Gráfico de crecimiento](charts.md#portfolio-growth-chart)** | Valor de la cartera a lo largo del tiempo en tres vistas: valores absolutos (Abs), tasas de retorno (%) y el dinero realmente ganado (P&L). |
| **[Panel de asignación](charts.md#allocation-panel)** | Gráficos de donut e histórico apilado agrupados por Tipo, Sector y Geografía. |

### 🪙 Saldos de efectivo

Justo debajo de las tarjetas KPI, el panel **Saldos de efectivo** muestra tu efectivo líquido total agregado por divisa. Por ejemplo, si tienes USD en el bróker A y EUR en el bróker B, ambos saldos se mostrarán uno al lado del otro.

Cuando aplicas un filtro de bróker, los saldos de efectivo se actualizan automáticamente para reflejar solo el efectivo mantenido dentro de los brókeres seleccionados.

---

## 🛡️ Pestaña Riesgo {: #risk-tab }

La pestaña Riesgo contiene el panel **Riesgo de la cartera**, que responde a cuatro preguntas sobre el riesgo de tu cartera: **¿Cuánto puede doler?**, **¿Estoy tan diversificado como creo?**, **¿Me están pagando por este riesgo?** y **¿Y si…?** Siempre cubre toda tu cartera — todos los brókeres que posees con una participación superior al 0% — y sigue el rango de fechas y la divisa objetivo del panel, pero no el filtro de brókeres: cuando hay un filtro activo, un subtítulo lo indica. Consulta [Pestaña Riesgo](risk.md) para los bloques y las herramientas que muestran.

---

## 🎛️ Rango de fechas, filtros y exportación IA

En la parte superior derecha del panel, tienes varios controles para personalizar tu vista:

- **Rango temporal** — preajustes desde 1 semana hasta Todo el tiempo (MAX), o un rango personalizado mediante el selector de fechas.
- **Filtro de brókeres** — filtra las métricas a uno o varios brókeres específicos; la pestaña Riesgo siempre cubre todos los brókeres que posees, y un subtítulo lo indica cuando hay un filtro activo.
- **Divisa objetivo** — convierte todos los activos y saldos de efectivo dinámicamente a una única divisa seleccionada para una visualización agregada. La lista ofrece tu divisa predeterminada y las divisas de tus pares FX configurados — ambos extremos de cada par. Una divisa por la que una [ruta en cadena](../fx/add-pair.md) solo pasa no se ofrece: al sincronizar una cadena se almacena únicamente el tipo de cambio de su propio par, por lo que LibreFolio no tiene tipos con los que convertir a esa divisa. Para que una divisa esté disponible, dale un par propio: elige **Crear forex…** al final de la lista, o marca **Crear también pares intermedios** cuando añadas un par mediante una ruta en cadena.
- **exportación IA** (:material-brain:) — abre una exportación al portapapeles. Elige **Instantánea de datos** para solo datos fácticos, o una **tarea de análisis** que incluye automáticamente sus instrucciones y contrato de respuesta, y luego selecciona el **nivel de detalle** (Compacto, Estándar o Completo). La instantánea del backend sigue el filtro de brókeres activo, el rango de fechas y la divisa objetivo; LibreFolio no contacta con ningún servicio de IA. Consulta [exportación IA de la cartera](../ai-export/portfolio.md) o el [resumen de la exportación IA](../ai-export/index.md).

El rango temporal, el filtro de brókeres y la divisa objetivo se mantienen tal como los configures durante el resto de tu sesión en esta pestaña del navegador — recargar la página también los conserva — y se restablecen cuando cierras sesión. El rango temporal se comparte con las demás páginas que tienen uno (las páginas de Activos y FX, sus páginas de detalle y la página de cada bróker), por lo que un cambio hecho allí también aparece aquí. Junto a **exportación IA**, el botón **Actualizar** (:material-refresh:) recalcula todo a petición: consulta [Volver y actualizar](#coming-back-and-refreshing).

!!! tip "El ámbito importa"

    Cuando filtras a un único bróker, las transferencias de fondos *a otros brókeres* se convierten en flujos externos para ese ámbito. Esto afecta a los cálculos de [Capital depositado](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) y [P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md).

!!! note "La compartición afecta a estas cifras"

    El panel solo cuenta los brókeres que **posees** con una participación superior al 0%, y cada importe procedente de ellos se **escala según tu porcentaje de propiedad**: un Propietario con una participación del 50% ve la mitad del valor, los ingresos y el P&L de ese bróker contabilizados en los totales. Los brókeres en los que eres **Editor** o **Lector** — que por norma siempre llevan una participación del 0% — quedan excluidos, al igual que aquellos que posees con una participación del 0%: faltan de los totales, del filtro de brókeres, de la pestaña Posiciones (incluidas la vista Rendimiento y el panel de lotes), de la pestaña Riesgo y de la pestaña Transacciones. Los ves en su propia página de bróker, donde los Editores y Lectores obtienen los importes **completos** del bróker. Consulta [Compartición de brókeres](../brokers/sharing.md) para más detalles.

---

## 🔄 Volver y actualizar {: #coming-back-and-refreshing }

Vuelve al Panel — desde la barra lateral, o con el botón **←** de retroceso de una página de activo — y muestra al instante lo que mostraba cuando lo dejaste: las tarjetas KPI, los gráficos, la pestaña Posiciones con su vista Rendimiento y el panel de [Análisis de lotes FIFO](positions.md#fifo-lots-analysis), y la pestaña Riesgo. No hay marcadores de carga, y las cifras de los KPI aparecen directamente en su valor en lugar de contar desde cero. Si mientras tanto cambiaste el rango temporal en otra página, el Panel se abre en ese rango.

- **Si nada cambió mientras tanto**, eso es todo: LibreFolio no recalcula nada.
- **Si algo cambió** — por ejemplo una transacción; precios, tipos o eventos introducidos a mano o incorporados por una sincronización; un activo editado o fusionado; un cambio en uno de tus brókeres o en tu acceso a él; o el precio en vivo que una página de activo consulta mientras está abierta — las cifras antiguas permanecen en pantalla mientras LibreFolio recalcula en segundo plano, y luego los números pasan a los nuevos valores. Una sincronización de precios o tipos que no aportó nada nuevo no es un cambio.

El botón **Actualizar** recalcula todo, incluso cuando nada cambió: las cifras, la vista Rendimiento, el panel de lotes y la pestaña Riesgo. Lo que ves permanece en pantalla mientras tanto.

Si un recálculo falla, las cifras que ya están en pantalla se mantienen y un mensaje te lo indica. En la pestaña Riesgo, esto solo se cumple para las cifras del período y la divisa que estás viendo: si cambias a un período o una divisa para los que la pestaña aún no tiene cifras y el cálculo falla, muestra *No se pudieron cargar los datos de riesgo.* en lugar de sus niveles, en vez de las cifras de tu elección anterior.

---

## 🌡️ Banner de calidad de datos {: #data-quality-banner }

Si faltan precios o tipos de cambio FX en la fecha de fin, aparece un banner en la parte superior que explica qué activos no pudieron valorarse.
<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="data-quality-banner" alt="Banner de calidad de datos del panel con enlaces por activo">
</div>
 Los activos sin proveedor de precios (introducidos manualmente, como los proyectos de financiación colectiva inmobiliaria) se valoran al precio de su última transacción, a menos que introduzcas tú mismo un precio más reciente — esto es intencionado y no genera ninguna advertencia. Un activo que sí tiene proveedor de precios pero que sigue sin precio de mercado en la fecha de fin, más de dos semanas después de comprarlo por primera vez, también se valora mientras tanto al precio de su última transacción, y el banner lo lista: un bono comprado en la emisión, antes de su primera cotización, por ejemplo.

El banner también te advierte cuando un activo que posees tiene proveedor de precios pero su último precio tiene **más de una semana** en la fecha de fin: haz clic en **Sincronizar precios** para obtener los precios que faltan, y la advertencia desaparece una vez que están al día. Los activos manuales nunca se señalan de este modo, ya que no hay nada que sincronizar.

También lista los activos con un **coste de compra faltante**: una transferencia o un ajuste que incorporó unidades sin un coste base. LibreFolio no puede saber cuánto costaron esas unidades, así que las cuenta a cero en tu coste de compra y muestra el coste medio y el P&L no realizado de esa posición como no disponibles (`—`). Para corregirlo, busca esa transferencia o ajuste entre tus [transacciones](../transactions/index.md) y asígnale su coste base.

Los tipos de cambio se comprueban para cada transacción hasta la fecha de fin — cada compra, venta y movimiento de efectivo se convierte al tipo de su propia fecha — y, para valorar lo que posees, en cada día del período en pantalla. Cuando un par FX configurado con proveedor **no tiene tipo** para algunas de esas fechas, el banner lo lista con el intervalo de las fechas faltantes. LibreFolio convierte un importe con el tipo más reciente en su fecha o anterior, por antiguo que sea, así que estas fechas son *anteriores* al primer tipo almacenado del par — a menudo bastante antes del período en pantalla, porque cada transacción pasada cuenta para los totales como tu P&L total y tu coste de compra. Haz clic en **Sincronizar tipos** para rellenarlas:

- LibreFolio descarga ese intervalo de fechas con **una semana extra a cada lado** (nunca más allá de hoy), sea cual sea el período que esté mostrando el panel. La semana extra cubre los fines de semana y los días festivos, cuando los proveedores no publican nada: un día así en el borde del intervalo toma entonces el tipo del día laborable anterior.
- Una vez finalizada la descarga, el panel se actualiza y un mensaje informa del resultado para cada par.
- Si la descarga se realiza pero los mismos pares siguen señalados, el proveedor no tiene tipos para las fechas que aún faltan — normalmente porque son anteriores al inicio de su historial. El mensaje se convierte entonces en una advertencia que lo indica: introduce esos tipos a mano en el [Editor de datos](../fx/detail/data-editor.md) del par.

Los pares con solo tipos manuales (sin proveedor) reciben una advertencia propia: su botón **Ver FX** abre la página del primer par que liste, donde añades los tipos tú mismo.

!!! tip "Rellena todo el historial de un par de una vez"

    Abre la [página FX](../fx/index.md), elige el rango **Todo** (MAX) y haz clic en [Sincronizar todo](../fx/sync.md): LibreFolio descarga todo lo que publican los proveedores para tus pares, hasta hoy. Un par que añadas con proveedor lo hace por sí solo — consulta [Añadir un par de divisas](../fx/add-pair.md).

---

## 🔗 En esta sección

- 💰 **[Tarjetas KPI](kpi-cards.md)** — Patrimonio neto, P&L período y retornos explicados
- 📊 **[Gráficos](charts.md)** — Gráfico de crecimiento y panel de asignación explicados
- 🔍 **[Posiciones y análisis](positions.md)** — Posiciones abiertas, vistas de tabla vs. mapa y análisis detallado de lotes fiscales FIFO.

## 🔗 Teoría relacionada

- **[NAV / Patrimonio neto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- **[Valor contable](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)**
- **[P&L período](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)**
- **[Capital depositado y P&L total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- **[Resumen de métricas de rendimiento](../../financial-theory/technical-analysis/performance-metrics/index.md)**
