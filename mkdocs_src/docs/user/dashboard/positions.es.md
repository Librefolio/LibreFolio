# 🔍 Posiciones y análisis

La pestaña **Posiciones** muestra lo que posees, lo que ganó cada posición en el periodo y, a un clic de distancia, los lotes FIFO que hay detrás de cualquier posición. La página de cada bróker tiene la misma pestaña para ese bróker únicamente, con la misma configuración de tabla.

- 📋 **[Posiciones](#holdings)** — lo que posees en la fecha de fin
- 📈 **[Periodo](#performance)** — lo que ganó cada posición en el periodo
- 🔬 **[Análisis de lotes FIFO](#fifo-lots-analysis)** — los lotes que hay detrás de una posición

<div class="lf-screenshot-carousel" data-carousel="carousel-positions-views" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="positions-holdings-table" data-title="📋 Cartera (Tabla)" alt="Vista de tabla de cartera">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-holdings-map" data-title="🗺️ Cartera (Mapa / Mapa de árbol)" alt="Vista de mapa de cartera">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-table" data-title="📈 Periodo (Tabla)" alt="Vista de tabla de periodo">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-map" data-title="📊 Periodo (Mapa / Gráfico)" alt="Vista de mapa de periodo">
</div>

---

## 🎛️ Elegir una vista

- **[Cartera](#holdings) / [Periodo](#performance)** alterna entre lo que posees y lo que ganó cada posición; **Tabla / Mapa** (los dos iconos), entre una tabla y un gráfico.
- **El icono del ojo** (en Tabla) muestra, oculta o reordena las columnas; **Restablecer diseño** las restaura. **Ver todo →** abre la página de Activos.
- **Para profundizar en una posición**, abre su menú **⋮** en una tabla, o haz clic derecho sobre ella en cualquier vista: **Analizar lotes** abre el [Análisis de lotes FIFO](#fifo-lots-analysis) debajo de las posiciones (en el Panel como en la página de un bróker), **Ver activo**, la página del activo.

LibreFolio recuerda tus elecciones.

---

## 📋 Posiciones — lo que posees {: #holdings }

¿Qué posees en la fecha de fin y cómo va cada posición? **Cartera** muestra una fila por activo y bróker, empezando por el mayor valor. Al final, en cursiva, aparecen las posiciones que **vendiste por completo dentro del periodo**: no tienen valor, peso ni rendimiento, pero puedes marcarlas para dibujar su línea en el [gráfico](#return-of-the-positions), y tienen las acciones de fila habituales.

**Columnas mostradas**

| Columna | Qué muestra |
|:---|:---|
| **Activo** | El activo, con el icono de su tipo |
| **Δ1** / **Δ1%** | La variación de hoy del P&L no realizado con la cantidad de hoy, en dinero y en % del valor de ayer |
| **P&L no realizado** / **P&L %** | El valor actual menos lo que costó la posición abierta, en dinero y en % de ese coste → [Valor contable](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md) |
| **Anualizado** | El rendimiento compuesto anual desde la primera transacción, ingresos y comisiones incluidos → [Rendimiento anualizado neto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/net-annualized-return.md) |
| **YOC** | Los dividendos e intereses por unidad del último año, frente a su precio medio → [Rendimiento sobre coste](#yield-on-cost-yoc) |
| **Valor** / **Peso** | Cuánto vale la posición y su proporción en tu patrimonio neto, efectivo incluido |
| **Cant.** | Acciones, unidades o monedas en posesión |
| **Precio** *(oculto)* | El precio unitario utilizado: el precio de mercado, o el precio de tu última compra o venta cuando no hay cotización; `—` para un activo valorado a lo que te costó, que no tiene precio alguno → [Resolución de precios](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/price-resolution.md) |
| **Precio medio de compra** *(oculto)* | Precio medio de compra por unidad, cada compra al tipo de cambio de su propia fecha → [Precio medio de compra (PMC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md) |
| **Lote abierto más antiguo** *(oculto)* | Fecha de apertura del lote más antiguo aún abierto en este bróker; un desdoblamiento de acciones conserva las fechas |
| **Brókeres** | El bróker que mantiene la posición |

**Cómo interpretarla**

- **El peso incluye el efectivo**, así que las filas suman menos del 100 % cuando tienes efectivo.
- **El peso muestra `—` cuando tu patrimonio neto es cero o negativo**, por ejemplo cuando has pedido prestado más efectivo de lo que valen tus posiciones: una proporción no significaría nada.
- **El precio medio de compra conserva el tipo de cambio de cada compra**, mientras que el valor usa el de la fecha de fin: el P&L no realizado incluye lo que hizo el tipo desde entonces.
- **Δ1 compara dos precios con dos tipos de cambio**: el precio de hoy, con el que se valora la posición, al tipo de hoy, frente al último precio de mercado hasta ayer al tipo de ayer. Para un activo cotizado en otra divisa cuyo precio no se movió, Δ1 es solo lo que hizo el tipo de cambio en un día, y `0` cuando el tipo tampoco se movió.
- **En el Mapa**, los mosaicos se agrupan por bróker y tipo de activo; el tamaño es el valor y el color, el P&L %. Desplázate para hacer zoom, arrastra para moverte, y **Restablecer zoom** (↺) vuelve a mostrar todo.

??? info "➖ Celdas vacías — cuando falta un valor"

    - **`—` en P&L no realizado, P&L % o precio medio de compra**: parte de lo que pagaste es desconocida —un tipo de cambio que falta en una fecha de compra, o una transferencia o ajuste sin coste base—, o, solo para P&L no realizado y P&L %, el precio no se puede convertir porque falta el tipo de cambio de la fecha de fin. El [banner de calidad de datos](index.md#data-quality-banner) indica qué corregir.
    - **`—` en Precio, con un P&L no realizado de `0`**: el activo no tiene precio alguno —ni precio de mercado ni compra o venta, como cuando lo recibiste mediante un ajuste o una transferencia—, así que su valor es lo que te costó.
    - **Δ1** y **Δ1%** necesitan un precio de mercado hoy y otro de ayer o anterior; en el primer día de tu cartera no hay día anterior, así que quedan vacíos. **Anualizado** necesita una posición con la antigüedad suficiente para que una tasa anual signifique algo.

### 📉 Rendimiento de las posiciones {: #return-of-the-positions }

¿Qué posiciones tuyas lo hicieron mejor que la cartera y cuáles peor? En el Panel, la vista **Tabla** tanto de **Cartera** como de **Periodo** pone una casilla de verificación en cada fila y, debajo de la tabla, un gráfico de **Rendimiento de las posiciones**. Se sitúa junto a la asignación por activo —el gráfico circular de hoy y el área histórica, con dos botones— a aproximadamente 3/5 y 2/5 de la fila, como el gráfico de Crecimiento y la Asignación del Resumen. La vista **Mapa** no tiene gráfico.

- **Nada marcado**: el gráfico muestra solo la línea de la cartera. **Marca una fila**, en cualquiera de las tablas, para añadir una línea de esa posición, y marca más para compararlas.
- **La leyenda** bajo el título tiene un botón por línea, con el nombre del activo (un nombre demasiado largo para su botón se desplaza solo): haz clic en él para activar o desactivar la línea. Una **bandera** marca una posición que se cerró, y una **señal de advertencia**, una con un precio o tipo de cambio faltante, cuya línea omite esos días.
- **Abs / % / Móvil** cambian la vista; los botones están en el gráfico, arriba a la derecha, dibujados como en la lista de Activos: el icono del **gráfico de línea** para **Abs**, **%** para el porcentaje, el icono del **calendario con flechas** para **Móvil** (pasa el ratón por un botón para leer su nombre). **Abs** es la ganancia o pérdida de la posición en dinero, desde el inicio del periodo. **%** es su rendimiento en *base 100*: cada línea empieza en 100 el primer día del periodo, así que 112 significa +12 %. **Móvil** se describe más abajo. LibreFolio recuerda la vista.
- **Los colores** son los del activo: una línea lleva el color que su activo tiene en el gráfico circular y el historial de la asignación de al lado, sin importar qué marques ni en qué orden. Cuando dos brókeres tienen el mismo activo, sus líneas comparten color y se distinguen por el trazo: la primera es continua, la otra discontinua (luego de puntos, luego de punto y raya).
- **El recuadro que sigue al cursor** enumera cada línea dibujada ese día; un nombre demasiado largo para el recuadro se desplaza solo.
- **La línea de una posición cerrada termina el día en que se cerró**; pasa el cursor sobre el botón de la leyenda para ver la fecha.
- Se pueden dibujar **hasta 50 posiciones** a la vez.

**Móvil — comparar activos entre sí.** Para cada posición marcada, la línea muestra el porcentaje que se movió el **precio** del activo en una ventana móvil que avanza a lo largo del periodo, de modo que los activos comprados en días distintos se pueden comparar en igualdad de condiciones. La ventana es la mayor entre 1 semana, 1 mes, 3 meses y 1 año que encaje en el periodo, hasta que elijas otra: la fila **Ventana** sobre el gráfico ofrece esas cuatro y **Personalizado**, una duración tuya en semanas, meses o años. Tu elección se mantiene mientras cambias el periodo y vuelve a la ventana automática al salir de la página. Es **por activo**: dos brókeres que tienen el mismo activo comparten una línea. En esta vista **no hay línea de cartera**, ya que la cartera no tiene precio.

??? info "📐 Por qué la línea de la cartera puede diferir de las posiciones"

    La línea de la cartera es el rendimiento que mide el Panel, el [rendimiento ponderado por tiempo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md), no la ganancia de tus posiciones sobre el capital que emplearon. Por eso los dos pueden diferir, incluso cuando todas las posiciones están marcadas; una frase bajo el gráfico lo indica. En los días en que tu cartera vale cero o menos no hay rendimiento ponderado por tiempo, así que la línea de la cartera tiene un hueco en **%** ([Cuando no se muestra el TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md#when-no-twrr)).

### 💸 Rendimiento sobre coste (YOC) {: #yield-on-cost-yoc }

¿Cuántos ingresos te paga cada unidad en comparación con lo que costó? **YOC** compara los dividendos e intereses que recibió cada unidad durante los **últimos 365 días** con su precio medio de compra.

**Cómo interpretarlo**

- **Un valor por activo y bróker**, durante el año que termina en la fecha de fin: mover la fecha de inicio no lo cambia.
- **Bruto, no después de impuestos**: las transacciones separadas de impuestos y comisiones no se restan.
- **Pasa el cursor sobre un valor** para ver el ingreso por unidad, el periodo y los tipos de cambio utilizados —cada pago al tipo de su propia fecha—.
- **`0.00%`** significa ingresos registrados a cero, o correcciones que los anulan exactamente; un **`-`** simple significa que no hubo ingresos en el último año.

🔗 **Teoría**: [Rendimiento sobre coste](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/yield-on-cost.md) — las reglas exactas y en qué se diferencia el YOC del rendimiento por dividendo o del CAGR

??? info "🚦 Un guion con un icono ⓘ — cuando el YOC no está disponible"

    LibreFolio no muestra un YOC parcial. Cuando falla una entrada, pasa el cursor sobre el icono ⓘ ámbar para ver el motivo: menos de un año de historial en este bróker y aún sin ingresos, un pago sin unidades en posesión el día anterior, un historial de compras, ventas, transferencias o desdoblamientos que no cuadra, un tipo de cambio faltante o un precio medio desconocido. Una vez corregido, el YOC se vuelve a calcular. También aparece un guion cuando las correcciones registradas en el último año —filas antiguas de dividendos o intereses negativos— suman más que los propios ingresos: entonces el ⓘ dice *Las correcciones superan los ingresos del último año.*

---

## 📈 Periodo — lo que ganó cada posición {: #performance }

¿Qué posiciones ganaron o perdieron dinero en el periodo y cómo? **Periodo** enumera todas las posiciones del periodo, abiertas o cerradas desde entonces, empezando por las de mayor variación. LibreFolio lo calcula la primera vez que lo abres, así que puede tardar un momento.

**Métricas mostradas**

- **P&L período**, desglosado como en la [tarjeta P&L período](kpi-cards.md#card-1-period-pl) en **Variación no realizada**, **Ventas**, **Dividendos e intereses** y **Costes** → [P&L período](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)
- **Anualizado** — el resultado del periodo como tasa anual, durante el tiempo que se mantuvo la posición en el periodo; `—` para una posición cerrada en el periodo tras menos de 30 días mantenida en él, demasiado poco para que una tasa anual signifique algo → [Rendimiento anualizado neto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/net-annualized-return.md)
- **Δ1** / **Δ1%** para posiciones abiertas y, ocultos de forma predeterminada, **Valor inicial**, **Valor final**, **Lote abierto más antiguo** y **Estado**
- **Otros efectos del periodo** — lo que no pertenece a ninguna posición: **Ingresos no asignados** y **Costes no asignados**, registrados sin un activo; **Efecto del tipo de cambio sobre el efectivo**, lo que hicieron los tipos de cambio en el periodo sobre el efectivo que tienes en otra divisa, con una fila solo para un bróker cuyo efectivo se movió; **Transferencias a valor de mercado**, cuando miras solo algunos de tus brókeres, la ganancia que generaron los valores transferidos hacia o desde un bróker fuera de tu selección antes de cruzar el límite, una fila por bróker ([Transferencias a valor de mercado](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md#transfers-at-market-value)); y el **Otro / residual de conciliación**, lo que queda —una divisa cambiada con un coste, el movimiento del tipo de cambio del efectivo en tránsito entre dos de tus brókeres, valores en tránsito entre ellos el primer o último día del periodo, una venta excluida de **Ventas** porque falta un tipo o un coste de compra, o el coste de compra de un pequeño remanente —0,00001 unidades o menos, que puede dejar una venta de casi todas las unidades y que no cuenta como posición— → [Efecto del tipo de cambio sobre el efectivo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md#fx-on-cash)

**Cómo interpretarlo**

- **Las posiciones cerradas** aparecen en cursiva o llevan una insignia **Cerrada** en el gráfico; para listar solo un tipo, muestra **Estado** y fíltralo.
- **En el Mapa**, las ganancias se apilan a la derecha del cero y las pérdidas a la izquierda, y el resultado neto cierra la fila; cada porcentaje se compara con el valor inicial de la posición.
- **El P&L período de una posición** puede diferir de su ganancia total: solo cuenta el periodo.
- **El valor inicial** y **el valor final** se calculan como el **Valor** en **Cartera** —mismos precios, un activo sin precio a lo que te costó, el tipo de cambio de cada día—, así que las filas más los **Otros efectos del periodo** suman la [tarjeta P&L período](kpi-cards.md#card-1-period-pl). Un **`—`** en **Variación no realizada** significa que no se pudo calcular un valor, como un tipo de cambio o un coste de compra faltante: no es un cero.
- **Los valores transferidos entre dos de tus brókeres** durante el periodo dividen su resultado: la fila del bróker emisor conserva lo que hicieron hasta que llegaron, y la del bróker receptor, lo que hicieron después; el total no cambia.

??? tip "🙈 Ocultar importes — lo que el gráfico sigue mostrando"

    Con **Ocultar importes** activado (el botón del ojo en la barra superior), los importes y el eje del gráfico se convierten en `•••`, como en `+€•••`. Los signos, las divisas, los porcentajes, las longitudes de las barras y los colores se mantienen, así que sigues viendo quién ganó o perdió, y cuánto en comparación con los demás. Consulta [Modo privacidad](../settings/preferences.md#privacy-mode).

---

## 🔬 Análisis de lotes FIFO {: #fifo-lots-analysis }

¿Qué compras componen una posición, dónde están custodiadas y cómo ha ido cada una? El **Análisis de lotes FIFO** responde lote a lote: cada compra abre un *lote*, y cada venta cierra primero los lotes abiertos **más antiguos**: primero en entrar, primero en salir.

Elige **Analizar lotes** en una posición y se abre el panel, para los brókeres de la página: tu filtro de brókeres en el Panel, el propio bróker en su página. En el Panel, igual que en la página de un bróker, se abre **debajo de las posiciones**: la tabla de posiciones y el gráfico de rendimiento permanecen en pantalla. **Ver activo** (↗) abre el activo; **✕** cierra el panel, y también lo hace el botón Atrás del navegador.

<div class="lf-screenshot-carousel" data-carousel="carousel-fifo-lots-analysis" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="fifo-lots-panel" data-title="🔍 Resumen" alt="Resumen del análisis de lotes FIFO">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-wac-chart" data-title="📈 PMC / Precio de mercado" alt="Gráfico de PMC y precio de mercado">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-gantt-chart" data-title="🕒 Vida y custodia del lote" alt="Gráfico de Gantt de vida y custodia del lote">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-table" data-title="📋 Tabla unificada de lotes" alt="Tabla unificada de lotes">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart" data-title="💰 Comparación de valores" alt="Gráfico de comparación de valores">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" data-title="📊 Comparación de rendimientos" alt="Gráfico de comparación de rendimientos">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-custody-modal" data-title="🧾 Modal de detalle del lote" alt="Modal de detalle del lote">
</div>

**Cómo funcionan juntos los bloques**

- **Una sola selección**: haz clic en burbujas, barras o filas de la tabla para elegir lotes; si no hay ninguno elegido, cuentan todos los lotes visibles. **Abiertos / Cerrados**, en la línea de tiempo, filtra todos los bloques.
- **Doble clic para saltar**: de un marcador del gráfico a los lotes de esa transacción, de una barra de la línea de tiempo a su fila de la tabla, y viceversa.
- **Importes completos del bróker**: en un bróker del que eres copropietario, aquí no se aplica tu parte, a diferencia de las tarjetas KPI y Posiciones.

🔗 **Teoría**: [Motor FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md) · [Análisis de lotes FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md) · [Emparejamiento FIFO](../../financial-theory/instruments/transaction-types/buy-sell.md#fifo-matching) · [Fiscalidad](../../financial-theory/fundamentals/taxation.md)

### 💹 1. Precio medio de compra / Precio de mercado

¿Cómo se compara el precio con lo que pagaste y en qué situación está cada lote?

**Métricas mostradas**

- **Precio de mercado** — discontinuo donde LibreFolio lo estima a partir de tu última operación → [Cadena de precios de valoración](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md#valuation-price-chain)
- **Precio medio de compra** — una línea por bróker, y una línea discontinua **Combinada** cuando el activo está en varios → [Precio medio de compra (PMC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)
- **Burbujas** — una por lote largo, en su rendimiento total, entre los marcadores de tus transacciones y pagos → [Análisis de lotes FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)

**Cómo interpretarlo**

- **Abs / %** muestra los precios o su variación desde el primer punto; **Auto / Desde 0** establece dónde empieza el eje.
- **El color de la burbuja** es el bróker de apertura; su **tamaño**, la cantidad del lote (**Abs**) o su valor de apertura (**%**). Un **borde discontinuo** significa valorado a coste.
- **Un hueco en una línea de precio medio de compra** es un día cuyo precio medio de compra se desconoce: no se dibuja un promedio incorrecto.
- **La línea de precio de mercado** cubre todo el periodo, incluidos los días sin ningún lote abierto: después de venderlo todo, continúa hasta la fecha de fin.

### 🕒 2. Vida y custodia del lote

¿Cuándo estuvo abierto cada lote y qué bróker lo mantenía?

**Métricas mostradas**

- **Barras** — una por lote, coloreada según el bróker que lo mantiene y con un grosor proporcional a la cantidad mantenida; violeta discontinua mientras está en tránsito, con un carril por bróker tras una transferencia → [Motor FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md)

**Cómo interpretarlo**

- **Abiertos / Cerrados** mantiene solo los lotes abiertos, solo los cerrados, o ambos.
- **Una barra más fina** perdió parte de su cantidad, por ejemplo por una venta parcial.
- **Haz clic** en una barra para seleccionar su lote; **haz doble clic** para encontrar su fila en la tabla.
- **Los marcadores de una barra** son los eventos del lote: ▲ compra, ▼ venta, ◆ transferencia, **+** ajuste de entrada, **×** ajuste de salida y │ desdoblamiento. Pasa el cursor sobre un marcador, tócalo o llega a él con el teclado para ver qué ocurrió, la fecha, la cantidad (oculta como ••• en el modo privacidad) y el bróker: una transferencia entre tus brókeres muestra **Desde** y **Hacia**, una con un bróker fuera del panel nombra solo el bróker que estás viendo, y un punto donde varios eventos caen el mismo día los enumera todos. Haz clic o doble clic en un marcador igual que en su barra.

### 📋 3. Tabla de lotes

Todos los lotes con sus cifras, siguiendo el filtro y la selección del panel.

**Métricas mostradas**

- **Fecha de apertura**, **P&L total**, **Rendimiento total**, **Anualizado**, **Valor actual**, **Cantidad abierta** y **Custodia**, con una fila de **Totales** → [Análisis de lotes FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Ingresos** cuando un lote recibió alguno, y **Comisiones**, **Impuestos**, **P&L neto** y **Rendimiento neto** cuando un lote soporta costes → [Costes y métricas netas](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md#costs-and-net-metrics)

**Cómo interpretarla**

- **Haz clic** en una fila para seleccionarla, **haz doble clic** para encontrarla en la línea de tiempo; el color de la fila es el bróker de apertura.
- **El menú ⋮** ofrece **Ver detalle del lote**, **Ir al lote en Gantt**, **Ir a la transacción de apertura** y **Copiar identificador del lote** —una referencia estable, útil para soporte—.
- **Más columnas**, como **Valor de apertura**, esperan detrás del icono del ojo.

### 💰 4. Comparación de valor / rendimiento

¿Cuánto valen los lotes seleccionados y cuánto han ganado desde su apertura? Si no hay ninguno seleccionado, el gráfico cubre todos los lotes visibles.

**Métricas mostradas**

- **Valor** — **Valor residual**, **Ingresos por venta** y **Ingresos acumulados** apilados hasta el **Valor integral**, frente al **Valor de apertura** → [Análisis de lotes FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Rendimiento** — el resultado desde la apertura, en dinero (**Abs**) o en porcentaje (**%**): un **Rendimiento agregado**, más una línea por lote cuando comparas varios

**Cómo interpretarlo**

- **Valor integral por encima del valor de apertura**: los lotes ganaron, incluidas ventas e ingresos.
- **Una línea discontinua** en **Valor** significa que el valor actual de un lote se estima a coste: su activo no tiene precio alguno —ni precio de mercado, ni compra o venta, ni una transferencia cuyo coste cuente como su precio hasta la fecha de fin—.
- **Un inicio plano**: hasta el primer precio del activo —precio de mercado, compra o venta, o el coste de una transferencia que lo introdujo antes que cualquier otra cosa—, un lote, por ejemplo uno que recibiste mediante un ajuste, se valora a lo que te costó, sin ganancia ni pérdida. En cambio, un día cuyo precio no tiene tipo de cambio se omite.

### 🧾 5. Detalle del lote

Toda la historia de un lote. Ábrelo con **Ver detalle del lote** (⋮) o haciendo clic en su celda **Custodia**.

**Métricas mostradas**

- **Resumen** — valor de apertura y actual, ingresos por venta, **P&L FIFO**, **P&L total**, **Rendimiento total** y **Rendimiento en efectivo** cuando el lote recibió ingresos → [Análisis de lotes FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Desglose neto** — el P&L total menos las comisiones e impuestos asignados al lote → [Costes y métricas netas](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md#costs-and-net-metrics)
- **Custodia actual** e **Historial** — dónde está ahora el lote y cada evento desde su apertura. Una transferencia entre dos de tus brókeres aparece como dos filas, *A → En tránsito* y *En tránsito → B*, incluso cuando las unidades salen y llegan el mismo día

**Cómo interpretarlo**

- **Las cantidades son las posiciones completas del bróker**, como indica el ⓘ que hay junto a ellas.
- **Una transferencia con un bróker fuera del panel** cuenta como unidades que entran o salen. Las unidades recibidas abren un nuevo lote el día en que llegan, al coste que arrastra la transferencia. Las unidades enviadas cierran sus lotes el día en que salen, al precio de mercado de ese día, así que la ganancia que obtuvieron en este bróker se cuenta como realizada aquí. El Historial del lote etiqueta estos movimientos como **TRANSFER+** y **TRANSFER-**, y los gráficos los marcan como transferencias —◆ en Vida y custodia del lote, **Transferencia entrante** y **Transferencia saliente** en los marcadores de Precio medio de compra / Precio de mercado— sin nombrar el otro bróker. Para seguir los lotes originales a través del movimiento, abre el panel con ambos brókeres (sin filtro de brókeres en el Panel). Una transferencia que aún está en camino el último día del panel muestra sus unidades como en tránsito.
- **Ir a la transacción** abre la transacción de la fila del Historial que elegiste; de forma predeterminada, la de apertura.

??? warning "⚠️ Cuando el panel te advierte"

    - **Un banner plegado** enumera lo que falta —un tipo de cambio, un precio, un coste de compra—, con una etiqueta por lote afectado que encuentra su burbuja. Corrígelo como en el [banner de calidad de datos](index.md#data-quality-banner). El banner plegado también enumera ingresos y costes que ningún lote pudo asumir —un dividendo pagado después de vender todos los lotes, por ejemplo—, cada uno con su propio importe y fecha.
    - **Un mensaje rojo** significa que las cantidades o transferencias de algunas de las transacciones del activo no cuadran, así que sus lotes no se pueden reconstruir. Enumera cada transacción a corregir con su día, su bróker, qué está mal y un botón **Ir a la transacción**. Mientras tanto, el panel oculta los lotes, su línea de tiempo y la comparación, y el primer gráfico conserva solo sus líneas de **Precio medio de compra** y el **Precio de mercado**. Corrige esas transacciones y los lotes vuelven.
    - **Valorado a coste**: en los días anteriores al primer precio del activo —sin precio de mercado, sin compra o venta, sin una transferencia cuyo coste cuente como su precio—, sus lotes se valoran a lo que costaron, sin ganancia ni pérdida de mercado, y el banner nombra esos días. Si no hay ningún precio hasta la fecha de fin, la burbuja del lote tiene un borde discontinuo.

---

## 🔗 Enlaces relacionados

- 💰 **[Tarjetas KPI](kpi-cards.md)** — los mismos resultados para toda la cartera
- 💸 **[Transacciones](../transactions/index.md)** — la pestaña **Transacciones** del Panel enumera las operaciones del rango y los brókeres seleccionados
- 🛠️ **[Detalles técnicos](../../developer/frontend/pages/index.md#dashboard)** — para desarrolladores: cómo funcionan por dentro la pestaña Posiciones y el panel de lotes

---

*[⬅️ Volver al resumen del Panel](index.md)*
