# 📊 Gráficos

Debajo de las tarjetas KPI, el gráfico **Crecimiento de la cartera** y el panel **Asignación de activos** muestran dónde ha estado tu cartera y de qué está compuesta. Ambos siguen el rango temporal y el filtro de bróker del panel, y la página de un bróker los muestra solo para ese bróker.

---

## 📈 Gráfico de crecimiento de la cartera {: #portfolio-growth-chart }

El gráfico de crecimiento muestra cómo evolucionó tu cartera durante el periodo seleccionado: el interruptor **Abs / % / P&L** de su esquina superior derecha alterna entre valores absolutos, tasas de rendimiento y el dinero realmente ganado.

En un periodo largo, el gráfico agrupa los días para mantener la legibilidad: en semanas, luego meses y, para un historial de muchas décadas, años. Una insignia **Semanal**, **Mensual** o **Anual** en la esquina superior izquierda del gráfico indica cuál. Cuando no se agrupa nada, no hay insignia.

### 〰️ Cómo se dibujan las líneas {: #line-shape }

Todos los gráficos unen sus puntos con una de tres formas: **Segmentos** (la predeterminada, una línea recta entre dos puntos), **Escalones** (cada valor se mantiene hasta el siguiente) o **Curva suave** (una línea suave que nunca pasa por encima ni por debajo de los dos puntos vecinos, de modo que no dibuja ningún valor que nunca existió). Eliges la forma en la primera página del recorrido de bienvenida y, más adelante, en **Configuración → Preferencias**; se aplica a todos los gráficos de este navegador. En las páginas de detalle de activos y de FX, los ajustes del gráfico también tienen una fila **Forma de línea**, para dar a ese gráfico concreto su propia forma. La forma solo cambia cómo se unen los puntos: el valor de un día en la información emergente es siempre el que el informe guarda para ese día. Cuando un gráfico muestra semanas o meses, los puntos no son escalones, así que **Escalones** dibuja segmentos en esos casos.

El gráfico recuerda tu última vista, incluida la subvista de P&L, en este navegador y para cada usuario, y la comparte con las páginas de brókeres. Empieza en **Abs**. Sin datos de tasa de rendimiento, **%** aparece atenuado y el gráfico muestra **Abs**, pero conserva tu elección: **%** vuelve en cuanto haya datos que dibujar — después de cambiar el periodo o el bróker, o la próxima vez que abras el gráfico —, a menos que mientras tanto elijas otra vista.

<div class="lf-screenshot-carousel" data-carousel="carousel-growth" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" data-title="📈 Modo absoluto" alt="Gráfico de crecimiento — Modo absoluto">
     <img class="gallery-img" data-category="dashboard" data-name="main" alt="Gráfico de crecimiento — Modo absoluto">
  </div>
  <div class="lf-screenshot-carousel-item chart-crop-container" data-title="📈 Modo porcentual" alt="Gráfico de crecimiento — Modo porcentual">
     <img class="gallery-img" data-category="dashboard" data-name="main-pct" alt="Gráfico de crecimiento — Modo porcentual">
  </div>
</div>

**Ocultar importes** (el botón del ojo en la barra superior) convierte cada importe del eje y de las informaciones emergentes en `•••`; los signos, las divisas, las líneas y los colores se mantienen. Véase [modo privacidad](../settings/preferences.md#privacy-mode).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="privacy-masked" alt="El Panel con Ocultar importes activado: el botón del ojo tachado en la cabecera, los importes de las tarjetas KPI y de los Saldos de efectivo mostrados como ••• con su signo y divisa, los porcentajes aún legibles y el eje de Crecimiento de la cartera enmascarado" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 💶 Abs — valores absolutos

| Elemento | Color | Significado |
|---------|-------|---------|
| Área — **Coste de compra** | Azul | Lo que te costaron las posiciones que mantienes (coste medio × cantidad) |
| Área — **Rendimientos** | Esmeralda | Rendimientos mantenidos como efectivo (dividendos, intereses, ganancias realizadas aún no reinvertidas, ganancias cambiarias del efectivo que mantienes en otra divisa) |
| Área — **Capital** | Verde grisáceo | Depósitos aún no invertidos, mantenidos como efectivo |
| Línea — **[Valor neto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)** | Verde oscuro sólido | Valor total de la cartera a precios de mercado actuales |
| Línea — **[Capital depositado](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)** | Gris discontinuo | Capital externo neto aportado a lo largo del tiempo |

**La diferencia entre ambas líneas es tu P&L total**: todas las ganancias obtenidas (no realizadas, realizadas, intereses, dividendos y ganancias o pérdidas cambiarias del efectivo mantenido en otra divisa) menos comisiones e impuestos. La información emergente muestra ambas líneas, el P&L total en verde o rojo, y el desglose: **Activos a coste** (el área azul, incluidos los activos que se mueven entre tus brókeres), **Rendimientos** y **Capital**.

**Los activos valorados a su precio de compra**, como los préstamos P2P sin precio de mercado en vivo, mantienen el NAV cerca del Coste de compra, por lo que la diferencia puede ser pequeña: lee el **P&L total** en la información emergente.

**Dinero procedente de un bróker fuera de la vista.** En la página de un bróker, o con el filtro de bróker activado, el dinero recibido de un bróker fuera de la vista es **Capital**, como lo sería un depósito — o **Rendimientos** de nuevo, si devuelve rendimientos que retiraste anteriormente. El dinero enviado a un bróker fuera de la vista sale primero de **Capital** y luego de **Rendimientos**, como ocurre con un retiro. Lo mismo se aplica a la mitad de una transferencia cuya otra mitad se eliminó o desvinculó, en todas las vistas.

🔗 **Teoría**: [Capital depositado y P&L total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) · [Descomposición del efectivo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#three-pool-cash-model)

### 📉 % — tasa de rendimiento

Cada línea es el rendimiento acumulado desde el inicio del periodo seleccionado:

| Serie | Qué muestra |
|--------|--------------|
| **[MWRR acumulado](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** | Tu rendimiento personal ponderado por dinero, incluido el momento de los depósitos |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** | Rendimiento puro de la estrategia de activos, ignorando cuándo depositaste |
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md)** | Rendimiento bruto sobre el capital neto invertido |

La diferencia entre MWRR y TWRR es el [efecto timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md). La línea MWRR tiene un hueco en los días que no tienen MWRR — un valor de cero o menos, o retiros netos que no dejan capital invertido — según la misma regla que las tarjetas MWRR ([MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)). La línea TWRR tiene un hueco en los días en que tu cartera vale cero o menos, por ejemplo después de venderlo todo y retirar el efectivo, según la misma regla que la tarjeta TWRR; tras nuevos depósitos vuelve a partir de donde estaba ([Cuándo no se muestra TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md#when-no-twrr)). La línea ROI no tiene huecos. Cuando el último día del periodo no tiene MWRR, el [banner de calidad de datos](index.md#data-quality-banner) dice *No se puede calcular MWRR para este periodo*.

### 💰 P&L — el dinero que has ganado {: #pnl-mode }

**P&L** representa tu **P&L total** (NAV menos capital depositado): cuánto dinero ha ganado realmente la cartera desde su inicio. Hacer zoom no reinicia el recuento en cero.

Un segundo interruptor, en la esquina superior izquierda del gráfico, elige cómo dibujarlo (solo iconos en un gráfico estrecho):

| Vista | Qué dibuja | La pregunta que responde |
|------|---------------|------------------------|
| **Línea** | P&L acumulado como una sola línea | ¿Cómo ha evolucionado mi resultado a lo largo del tiempo? |
| **Velas** | Una vela por periodo, desde un día hasta un año | ¿Qué amplitud tuvo la oscilación dentro de cada periodo? |
| **Ingresos** | Barras del efectivo que realmente se movió | ¿De dónde vino el dinero y cuánto me costó? |

#### Línea — P&L acumulado {: #pnl-line }

- La línea es **verde por encima de cero y roja por debajo**.
- Una **línea gris discontinua** marca el P&L del primer día visible: la diferencia hasta ella es lo que has ganado o perdido desde el borde izquierdo.

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="El gráfico de Crecimiento de la cartera en modo P&L, vista Línea: la línea de P&L total en verde, la línea gris discontinua en el P&L del primer día visible y una línea discontinua por bróker">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-line" alt="El gráfico de Crecimiento de la cartera en modo P&L, vista Línea: la línea de P&L total en verde, la línea gris discontinua en el P&L del primer día visible y una línea discontinua por bróker">
  </div>
</div>

**Líneas de brókeres.** Con dos o más brókeres en el ámbito, cada bróker recibe una línea discontinua y una fila en la información emergente con su parte del total; las partes suman el total cada día. La línea de un bróker es el P&L generado mientras el valor estuvo en ese bróker: mover dinero o valores entre dos de tus brókeres no es ni una ganancia ni una pérdida, así que ninguna línea da un salto cuando llega una transferencia.

- **En tránsito** — hasta que llega la transferencia, el valor y sus variaciones de precio o de tipo de cambio permanecen con el bróker del que salió.
- **Distintas participaciones de propiedad** — cuando los dos brókeres tienen distintas [participaciones de propiedad](../brokers/sharing.md), la línea receptora mantiene un escalón el día de llegada: el mismo escalón que muestra el total.
- **Sin valor el día de llegada** — si falta un tipo de cambio, o el valor aún no tiene precio y no se registró ningún coste en su llegada, el salto se mantiene: no se adivina nada. Un valor sin precio alguno se mueve al coste que registra para él el bróker receptor, el valor que LibreFolio le asigna allí; si parte de lo que ese bróker pagó por el activo ya era desconocida, su propia línea asume la diferencia.
- **Brókeres fuera de la vista** — en la página de un bróker, o con el filtro de bróker activado, los valores enviados a un bróker fuera de la vista o recibidos de él cuentan como capital a su valor de mercado en ese día — a su coste si no tienen precio alguno —, no como una ganancia o pérdida; el dinero cuenta como un depósito o un retiro. Cuando se elimina el otro bróker de una transferencia, la mitad que queda ya no es una transferencia: los valores se convierten en un ajuste, contabilizado como capital a su coste en lugar de a su valor de mercado, y el dinero, como un depósito o un retiro (véase [Editar o eliminar un bróker](../brokers/index.md)). Solo los valores enviados cuyo coste medio requiere un tipo de cambio ausente siguen siendo una transferencia, contabilizada a valor de mercado.

Con un solo bróker, o en la página de un bróker, solo se dibuja el total.

🔗 **Teoría**: [Transferencias internas en las líneas de brókeres](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#internal-transfers-broker-lines)

#### Velas — la oscilación dentro del periodo {: #pnl-candles }

Cada periodo del [ancho que elijas](#pnl-width) se convierte en una **vela** formada por valores de P&L, no por precios. Su **cierre** es exactamente el P&L total que muestra **Línea** para ese día.

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="El gráfico de Crecimiento de la cartera en modo P&L, vista Velas en 3D: las velas sintéticas de P&L, los botones de ancho de 3D a 6M en la esquina superior derecha del gráfico, las etiquetas de periodo en el eje y el texto Sintético bajo el gráfico">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-candles" alt="El gráfico de Crecimiento de la cartera en modo P&L, vista Velas en 3D: las velas sintéticas de P&L, los botones de ancho de 3D a 6M en la esquina superior derecha del gráfico, las etiquetas de periodo en el eje y el texto Sintético bajo el gráfico">
  </div>
</div>

!!! warning "Los máximos y mínimos son hipotéticos"

    La parte superior e inferior de una vela suman los máximos y mínimos diarios propios de cada activo, que no se alcanzaron en el mismo momento: puede que ese estado de la cartera nunca haya existido, como indica el texto bajo el gráfico (*Sintético: los máximos y mínimos entre activos son hipotéticos y no simultáneos*). Léelos como hasta dónde *podría* haber oscilado la cartera.

También cabe esperar:

- **Sin volumen** — el P&L de una cartera no tiene volumen negociado.
- **Cuerpos finos, mechas largas** — la apertura y el cierre suelen estar cerca mientras el rango sumado es amplio.
- **Huecos** — un día en el que no se pudo valorar un activo en cartera no tiene vela, en lugar de una vela estimada.

La información emergente muestra el periodo, **Apertura**, **Cierre**, **Máximo** y **Mínimo**, además de una fila por bróker cuando hay dos o más en el ámbito.

#### Ingresos — el efectivo que realmente se movió {: #pnl-income }

**Ingresos** deja a un lado las valoraciones y representa tus flujos de efectivo reales. Cada barra es la **suma** de los flujos de su periodo, en hasta tres columnas:

| Columna | Barras | Qué representa |
|--------|------|--------------------|
| Ingresos y costes | **Dividendo** · **Interés** por encima de cero, **Comisiones e impuestos** por debajo | Lo que la cartera te pagó y lo que te costó la actividad |
| Depósitos | **Depósito** | Dinero nuevo que aportaste (los retiros no se dibujan) |
| Compras | **Coste de compra**, en dos zonas: **Capital nuevo** abajo, **Reinvertido** arriba | Lo que gastaste en compras, dividido según de dónde vino el dinero |

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="El gráfico de Crecimiento de la cartera en modo P&L, vista Ingresos en 1M: grupos mensuales de barras para Interés, Comisiones e impuestos por debajo de cero, Depósito y Coste de compra">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-income" alt="El gráfico de Crecimiento de la cartera en modo P&L, vista Ingresos en 1M: grupos mensuales de barras para Interés, Comisiones e impuestos por debajo de cero, Depósito y Coste de compra">
  </div>
</div>

Cómo leerlo:

- **Capital nuevo o reinvertido.** Una compra gasta primero los rendimientos ya mantenidos como efectivo en ese bróker (**Reinvertido**, en verde como en **Abs**); el resto es **Capital nuevo** (azul). El dinero movido hacia o desde un bróker fuera de la vista modifica ese efectivo como lo haría un depósito o un retiro, como en **Abs** más arriba. Las ventas nunca se dibujan.
- **Se conservan los signos.** Una corrección negativa sobre un dividendo pasado reduce la barra de dividendos; las comisiones e impuestos permanecen por debajo de cero.
- **Coincide con los KPI.** Para las mismas fechas y brókeres, **Dividendo** e **Interés** suman exactamente lo que muestra la fila **Dividendos e intereses** de la [tarjeta P&L período](kpi-cards.md#card-1-period-pl).
- **Una sola entrada de leyenda.** Ambas zonas de compra se denominan **Coste de compra**: un clic oculta ambas, y también el área **Abs** del mismo nombre.
- **Tipos de cambio ausentes.** Un importe que no se puede convertir en su fecha se omite, no se cuenta como cero; el [banner de calidad de datos](index.md#data-quality-banner) lo indica.

!!! warning "Las barras de compras no son el KPI de Coste de compra"

    Las barras son un **flujo**: lo que gastaste en compras en cada periodo. La fila **Coste de compra** de la [tarjeta de Patrimonio neto](kpi-cards.md#card-3-net-worth) es un **nivel**: lo que te costaron las posiciones que aún mantienes en la fecha final. Las ventas y las compras anteriores cuentan en el KPI pero no tienen barra.

#### Ancho de vela — de 1D a 1Y {: #pnl-width }

En **Velas** e **Ingresos**, los botones de la esquina superior derecha del gráfico, de **1D** a **1Y**, establecen cuánto tiempo cubre una vela, o un grupo de barras. El gráfico sigue mostrando todo el rango, y el zoom nunca cambia el ancho.

- **Periodos de calendario.** **1W** va de lunes a domingo, **1M** es un mes natural, **3M** un trimestre, **6M** un semestre, **1Y** un año; **3D** y **2W** son bloques fijos de días.
- **Etiquetas del eje.** Cada etiqueta nombra el inicio de su periodo, incluso si el rango solo lo cubre en parte; los meses y años aparecen solo donde cambian, y las etiquetas apiñadas se inclinan o se reducen.
- Solo se ofrecen los **anchos que caben** en el gráfico y en el rango; **Ingresos** empieza en **1W**.
- **Dónde empieza.** **Velas** toma el ancho más fino disponible; **Ingresos** se abre en **1M**, o en el ancho más cercano disponible, cada vez que entras en él. Recargar la página restablece el ancho.
- **Los periodos parciales aparecen atenuados.** Un periodo en el que el rango empieza a mitad, o un último periodo acortado por un rango que termina en el pasado, se dibuja atenuado, y su información emergente dice *Parcial: N de M días*. En caso contrario, el periodo en curso se dibuja completo, con *En curso: N de M días*.

---

## 🥧 Panel de asignación {: #allocation-panel }

El panel **Asignación de activos** muestra cómo se reparte tu cartera, hoy y a lo largo del tiempo. Elige una dimensión con las pestañas **Por tipo**, **Por sector**, **Geográfico** y **Por activo**, y una vista con los dos botones de la esquina superior derecha: el gráfico circular para **Ahora**, el gráfico de áreas para **Historial**.

<div class="lf-screenshot-carousel" data-carousel="carousel-alloc" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active alloc-crop-container" data-title="Por tipo (actual)" alt="Asignación por tipo — actual">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-type-now" alt="Asignación por tipo — actual">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Por sector (actual)" alt="Asignación por sector — actual">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-now" alt="Asignación por sector — actual">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Por geografía (actual)" alt="Asignación por geografía — actual">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-now" alt="Asignación por geografía — actual">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Por tipo (histórico)" alt="Historial de asignación por tipo">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-type-history" alt="Historial de asignación por tipo">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Por sector (histórico)" alt="Historial de asignación por sector">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-history" alt="Historial de asignación por sector">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Por geografía (histórico)" alt="Historial de asignación por geografía">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-history" alt="Historial de asignación por geografía">
  </div>
</div>

### 🗂️ Tres dimensiones

| Pestaña | Qué muestra |
|-----|--------------|
| **Por tipo** | Qué es cada posición — su [tipo de activo](../../financial-theory/instruments/asset-types/index.md), como Acción, ETF, Bono, Fondo o Cripto —, más **Liquidez** para tu efectivo. Los subtipos cuentan con su [familia](../../financial-theory/instruments/asset-types/index.md#families-and-subtypes), como un **ETF de renta variable** junto con tus demás ETF. |
| **Por sector** | Sector industrial: 💻 Tecnología, 🏦 Finanzas, 💊 Sanidad, etc. |
| **Geográfico** | Dónde están invertidos tus activos, país por país, según la distribución geográfica de cada activo |
| **Por activo** | Cuánto pesa cada activo individual: una porción por activo, con **Liquidez** para tu efectivo. Véase [Por activo](#allocation-by-asset). |

### 🕰️ Ahora e historial

- **Ahora** — la asignación en el último día del rango seleccionado: un donut para **Por tipo** y **Por sector**, un mapamundi para **Geográfico**. Pasa el cursor sobre una porción o un país para ver su porcentaje e importe. Por tipo, el donut puede tener [dos anillos](#allocation-type-rings).
- **Historial** — un gráfico de áreas apiladas al 100 % de cómo cambió la asignación a lo largo del tiempo, útil para ver el rebalanceo. Por tipo, cada familia es un área; al pasar el cursor sobre una fecha se listan sus subtipos, como *ETF genérico* y *ETF de renta variable*.

El panel recuerda la vista y la pestaña en este navegador, para cada usuario, y las comparte con las páginas de brókeres.

### 🧩 Por activo {: #allocation-by-asset }

¿Qué activos individuales pesan más? **Por activo** divide la cartera activo por activo en lugar de por categoría.

- **Ahora** — un gráfico circular con el peso de cada activo en el último día del rango seleccionado. Cada porción muestra el icono de su activo — el suyo, o el de su tipo si no tiene o no se puede cargar; el efectivo muestra el de Liquidez. No hay leyenda: pasa el ratón por una porción para leer el nombre, la parte y el importe.
- **Historial** — cómo cambió la distribución por activo a lo largo del tiempo. **Se incluyen las posiciones cerradas**, por lo que un activo que vendiste sigue apareciendo en los días en que lo mantuviste.
- **Los colores** siguen el peso de hoy: el activo más pesado recibe el primer color, luego los demás por peso, después los activos cerrados, empezando por el cerrado más recientemente. El gráfico circular y el historial usan el mismo color para el mismo activo, y también las líneas de [Rentabilidad de las posiciones](positions.md#return-of-the-positions).

### 🍩 Dos anillos por tipo {: #allocation-type-rings }

En cuanto mantienes un activo con subtipo, como un **ETF de renta variable** o **Crowdfunding inmobiliario**, el donut **Ahora** de **Por tipo** dibuja dos anillos:

- **Anillo interior** — una porción por familia, con su icono donde cabe: todos tus ETF (el **ETF** genérico y todos los subtipos) juntos, **Crowdfund** con **Crowdfunding inmobiliario**, y todos los demás tipos, **Liquidez** incluida, por separado. Son las familias que agrupa el [menú de Tipo](../assets/create-edit.md#choosing-the-asset-type) del activo.
- **Anillo exterior** — más fino y separado, divide cada familia que contiene un subtipo en sus miembros, en tonos del color de la familia, con etiqueta donde hay espacio. El miembro genérico aparece como *ETF genérico* o *Crowdfund genérico*.
- **Pasa el cursor** sobre una porción para ver su parte e importe; en el anillo exterior, una última línea que empieza por **↳** indica la parte de toda la familia.
- **La leyenda** solo lista familias: al hacer clic en una se ocultan sus porciones en ambos anillos.

Sin ningún subtipo, el donut mantiene un solo anillo.

### 💵 Efectivo como liquidez

Tu efectivo es la porción **Liquidez** de **Por tipo**, **Por sector** y **Por activo**; el mapa **Geográfico** lo deja fuera, ya que el efectivo no pertenece a ningún país. Con el filtro de bróker activado, el panel muestra solo los activos y el efectivo de los brókeres seleccionados.

### ➖ Efectivo negativo {: #allocation-negative-cash }

El porcentaje de cada porción es su importe dividido entre la suma de todas las porciones, incluido el efectivo, así que el efectivo negativo cambia las partes:

- **Efectivo por debajo de cero, activos por encima** — por ejemplo, 1.500 € en acciones con efectivo a −500 € en un descubierto: las porciones suman 1.000 €, así que **Liquidez** marca −50 % y las acciones 150 %. Los porcentajes siguen sumando 100 %.
- **No queda nada que repartir** — cuando las porciones suman cero o menos, ninguna porción tiene porcentaje: 500 € en acciones compradas con un descubierto de −500 €, o una cartera que vaciaste, cuya única porción es **Liquidez** a cero. Cada porción muestra `—` en lugar de un porcentaje y conserva su importe, y el gráfico no tiene nada que dibujar y lo indica. En **Historial**, un día en el que las porciones suman cero o menos tampoco tiene porcentajes.
- **Un resto minúsculo** de 0,00001 unidades o menos, que puede dejar una venta de casi todas las unidades, no es una posición: no tiene porción.

---

## 🔗 Relacionado

- 💰 **[Tarjetas KPI](kpi-cards.md)** — Patrimonio neto, P&L período, Rendimientos
- 💼 **[NAV / Patrimonio neto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- 💸 **[Capital depositado y P&L total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** · **[MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** · **[efecto timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)**
- 🛠️ **[Funcionamiento interno de los gráficos](../../developer/frontend/components/charts.md)** — para desarrolladores: cómo se construyen estos gráficos

---

*[⬅️ Volver al resumen del Panel](index.md)*
