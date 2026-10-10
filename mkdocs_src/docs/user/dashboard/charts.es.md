# 📊 Gráficos

Debajo de las tarjetas KPI, el gráfico de **Crecimiento de la Cartera** y el panel de **Asignación de Activos** muestran dónde ha estado tu cartera y de qué está compuesta. Ambos siguen el rango temporal y el filtro de brókeres del Panel, y la página de un bróker los muestra solo para ese bróker.

---

## 📈 Gráfico de Crecimiento de la Cartera {: #portfolio-growth-chart }

El gráfico de crecimiento muestra cómo evolucionó tu cartera durante el período seleccionado: el interruptor **Abs / % / P&L** en su esquina superior derecha alterna entre valores absolutos, tasas de rentabilidad y el dinero realmente ganado.

El gráfico recuerda tu última vista, incluida la subvista de P&L, en este navegador y para cada usuario, y la comparte con las páginas de brókeres. Comienza en **Abs**. Sin datos de tasa de rentabilidad, **%** aparece en gris y el gráfico muestra **Abs**; tu elección vuelve la próxima vez que abras el gráfico con datos que dibujar.

<div class="lf-screenshot-carousel" data-carousel="carousel-growth" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" data-title="📈 Modo absoluto" alt="Gráfico de crecimiento — Modo absoluto">
     <img class="gallery-img" data-category="dashboard" data-name="main" alt="Gráfico de crecimiento — Modo absoluto">
  </div>
  <div class="lf-screenshot-carousel-item chart-crop-container" data-title="📈 Modo porcentual" alt="Gráfico de crecimiento — Modo porcentual">
     <img class="gallery-img" data-category="dashboard" data-name="main-pct" alt="Gráfico de crecimiento — Modo porcentual">
  </div>
</div>

**Ocultar importes** (el botón del ojo en la barra superior) convierte cada importe del eje y de la información emergente en `•••`; los signos, las divisas, las líneas y los colores se mantienen. Consulta [Modo privacidad](../settings/preferences.md#privacy-mode).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="privacy-masked" alt="El Panel con Ocultar importes activado: el botón del ojo tachado en la cabecera, los importes de las tarjetas KPI y de Saldos de Efectivo mostrados como ••• con su signo y su divisa, los porcentajes todavía legibles y el eje de Crecimiento de la Cartera oculto" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 💶 Abs — valores absolutos

| Elemento | Color | Significado |
|---------|-------|---------|
| Área — **Coste de Compra** | Azul | Lo que te costaron las posiciones que mantienes (coste medio × cantidad) |
| Área — **Rentabilidades** | Esmeralda | Rentabilidades mantenidas como efectivo (dividendos, intereses, ganancias realizadas aún no reinvertidas) |
| Área — **Capital** | Verde grisáceo | Depósitos aún no invertidos, mantenidos como efectivo |
| Línea — **[Valor neto (NAV)](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)** | Verde oscuro continua | Valor total de la cartera a los precios de mercado actuales |
| Línea — **[Capital Depositado](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)** | Gris discontinua | Capital externo neto aportado a lo largo del tiempo |

**La brecha entre las dos líneas es tu P&L Total**: cada ganancia obtenida alguna vez (no realizada, realizada, intereses y dividendos) menos comisiones e impuestos. La información emergente muestra ambas líneas, el P&L Total en verde o rojo, y el desglose: **Activos a Coste** (el área azul, incluidos los activos que se mueven entre tus brókeres), **Rentabilidades** y **Capital**.

**Los activos valorados a su precio de compra**, como los préstamos P2P sin precio de mercado en vivo, mantienen el NAV cerca del Coste de Compra, por lo que la brecha puede ser estrecha: lee el **P&L Total** en la información emergente.

🔗 **Teoría**: [Capital Depositado y P&L Total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) · [Descomposición del Efectivo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#three-pool-cash-model)

### 📉 % — tasa de rentabilidad

Cada línea es la rentabilidad acumulada desde el inicio del período seleccionado:

| Serie | Qué muestra |
|--------|--------------|
| **[MWRR acumulada](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** | Tu rentabilidad personal ponderada por el dinero, incluido el momento de los depósitos |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** | Rentabilidad pura de la estrategia de activos, ignorando cuándo depositaste |
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md)** | Rentabilidad bruta sobre el capital neto invertido |

La brecha entre la MWRR y la TWRR es el [efecto timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md). Si el [banner de calidad de datos](index.md#data-quality-banner) indica **MWRR no disponible**, la línea de MWRR se oculta; la TWRR y el ROI permanecen.

### 💰 P&L — el dinero que ganaste {: #pnl-mode }

**P&L** representa tu **P&L Total** (NAV menos capital depositado): cuánto dinero ha ganado realmente la cartera desde su inicio. Ampliar la vista no reinicia el cómputo en cero.

Un segundo interruptor, en la parte superior izquierda del área de trazado, elige cómo dibujarlo (solo iconos en un gráfico estrecho):

| Vista | Qué dibuja | La pregunta que responde |
|------|---------------|------------------------|
| **Línea** | P&L acumulado como una única línea | ¿Cómo ha evolucionado mi resultado a lo largo del tiempo? |
| **Velas** | Una vela por período, desde un día hasta un año | ¿Qué amplitud tuvo la oscilación dentro de cada período? |
| **Ingresos** | Barras del efectivo que realmente se movió | ¿De dónde vino el dinero y cuánto me costó? |

#### Línea — P&L acumulado {: #pnl-line }

- La línea es **verde por encima de cero y roja por debajo**.
- Una **línea gris discontinua** marca el P&L del primer día a la vista: la brecha hasta ella es lo que ganaste o perdiste desde el borde izquierdo.

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="El gráfico Crecimiento de la Cartera en modo P&L, vista Línea: la línea P&L Total en verde, la línea gris discontinua en el P&L del primer día visible y una línea discontinua por bróker">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-line" alt="El gráfico Crecimiento de la Cartera en modo P&L, vista Línea: la línea P&L Total en verde, la línea gris discontinua en el P&L del primer día visible y una línea discontinua por bróker">
  </div>
</div>

**Líneas de bróker.** Con dos o más brókeres en el ámbito, cada bróker recibe una línea discontinua y una fila en la información emergente con su parte del total; las partes suman el total cada día. Una parte no es el rendimiento propio del bróker: el dinero en tránsito cuenta para el bróker del que salió, por lo que la línea de un bróker puede dar un salto en la fecha de una transferencia. Con un solo bróker, o en la página de un bróker, solo se dibuja el total.

#### Velas — la oscilación dentro del período {: #pnl-candles }

Cada período de la [anchura que elijas](#pnl-width) se convierte en una **vela** formada por valores de P&L, no por precios. Su **cierre** es exactamente el P&L Total que muestra **Línea** para ese día.

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="El gráfico Crecimiento de la Cartera en modo P&L, vista Velas a 3D: las velas sintéticas de P&L, los botones de anchura de 3D a 6M en la esquina superior derecha del gráfico, las etiquetas de período en el eje y el pie Sintético bajo el gráfico">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-candles" alt="El gráfico Crecimiento de la Cartera en modo P&L, vista Velas a 3D: las velas sintéticas de P&L, los botones de anchura de 3D a 6M en la esquina superior derecha del gráfico, las etiquetas de período en el eje y el pie Sintético bajo el gráfico">
  </div>
</div>

!!! warning "Los máximos y los mínimos son hipotéticos"

    La parte superior e inferior de una vela suman el máximo y el mínimo diarios propios de cada activo, que no se alcanzaron en el mismo momento: ese estado de la cartera puede que nunca haya existido, como dice el pie del gráfico (*Sintético — máximos/mínimos entre activos son hipotéticos y no simultáneos*). Léelos como hasta dónde la cartera *podría* haberse movido.

Además, ten en cuenta:

- **Sin volumen** — el P&L de una cartera no tiene volumen negociado.
- **Cuerpos finos, mechas largas** — la apertura y el cierre suelen estar cerca mientras que el rango sumado es amplio.
- **Huecos** — un día en el que un activo en cartera no pudo valorarse no tiene vela en lugar de una estimada.

La información emergente da el período, **Apertura**, **Cierre**, **Máximo** y **Mínimo**, además de una fila por bróker cuando hay dos o más en el ámbito.

#### Ingresos — el efectivo que realmente se movió {: #pnl-income }

**Ingresos** deja a un lado las valoraciones y representa tus flujos de efectivo reales. Cada barra es la **suma** de los flujos de su período, en hasta tres columnas:

| Columna | Barras | Qué representa |
|--------|------|--------------------|
| Ingresos y costes | **Dividendo** · **Interés** por encima de cero, **Comisiones e impuestos** por debajo | Lo que la cartera te pagó, y lo que te costó la actividad |
| Depósitos | **Depósito** | Dinero nuevo que aportaste (los retiros no se dibujan) |
| Compras | **Coste de Compra**, en dos zonas: **Capital nuevo** abajo, **Reinvertido** arriba | Lo que gastaste en compras, dividido según de dónde vino el dinero |

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="El gráfico Crecimiento de la Cartera en modo P&L, vista Ingresos a 1M: grupos mensuales de barras para Interés, Costes e impuestos por debajo de cero, Depósito y Coste de compra">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-income" alt="El gráfico Crecimiento de la Cartera en modo P&L, vista Ingresos a 1M: grupos mensuales de barras para Interés, Costes e impuestos por debajo de cero, Depósito y Coste de compra">
  </div>
</div>

Cómo leerlo:

- **Capital nuevo o reinvertido.** Una compra gasta primero las rentabilidades ya mantenidas como efectivo en ese bróker (**Reinvertido**, verde como en **Abs**); el resto es **Capital nuevo** (azul). Las ventas nunca se dibujan.
- **Los signos se conservan.** Una corrección negativa sobre un dividendo pasado reduce la barra del dividendo; las comisiones e impuestos permanecen por debajo de cero.
- **Coincide con los KPI.** Para las mismas fechas y brókeres, **Dividendo** e **Interés** suman exactamente la fila **Dividendos e intereses** de la [tarjeta de P&L período](kpi-cards.md#card-1-period-pl).
- **Una entrada de leyenda.** Ambas zonas de compra se llaman **Coste de Compra**: un clic oculta las dos, y también el área de **Abs** del mismo nombre.
- **Faltan tipos de cambio.** Un importe que no puede convertirse en su fecha se omite, no se cuenta como cero; el [banner de calidad de datos](index.md#data-quality-banner) lo informa.

!!! warning "Las barras de compra no son el KPI de Coste de Compra"

    Las barras son un **flujo**: lo que gastaste en compras en cada período. La fila **Coste de Compra** de la [tarjeta de Patrimonio Neto](kpi-cards.md#card-3-net-worth) es un **nivel**: lo que te costaron las posiciones que aún mantienes en la fecha final. Las ventas y las compras anteriores cuentan en el KPI pero no tienen barra.

#### Anchura de vela — de 1D a 1A {: #pnl-width }

En **Velas** e **Ingresos**, los botones de la esquina superior derecha del área de trazado, de **1D** a **1A**, establecen cuánto tiempo cubre una vela, o un grupo de barras. El gráfico sigue mostrando todo el rango, y ampliar la vista nunca cambia la anchura.

- **Períodos de calendario.** **1S** va de lunes a domingo, **1M** es un mes natural, **3M** un trimestre, **6M** un semestre, **1A** un año; **3D** y **2S** son bloques fijos de días.
- **Etiquetas del eje.** Cada etiqueta nombra el inicio de su período, incluso uno que el rango solo cubre en parte; los meses y los años aparecen solo donde cambian, y las etiquetas amontonadas se inclinan o se reducen.
- **Solo se ofrecen las anchuras que caben** en el gráfico y en el rango; **Ingresos** empieza en **1S**.
- **Dónde comienza.** **Velas** toma la anchura más fina disponible; **Ingresos** se abre en **1M**, o en la anchura más cercana disponible, cada vez que entras en él. Recargar la página restablece la anchura.
- **Los períodos parciales aparecen atenuados.** Un período en el que el rango comienza a mitad, o uno último cortado por un rango que termina en el pasado, se dibuja atenuado, y su información emergente dice *Parcial: N de M días*. En caso contrario, el período en curso se dibuja entero, con *En curso: N de M días*.

---

## 🥧 Panel de Asignación {: #allocation-panel }

El panel de **Asignación de Activos** muestra cómo se reparte tu cartera, hoy y a lo largo del tiempo. Elige una dimensión con las pestañas **Por Tipo**, **Por Sector** y **Geográfica**, y una vista con los dos botones de la esquina superior derecha: el gráfico circular para **Ahora**, el gráfico de áreas para **Historial**.

<div class="lf-screenshot-carousel" data-carousel="carousel-alloc" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active alloc-crop-container" data-title="Por tipo (actual)" alt="Asignación por tipo — Actual">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-type-now" alt="Asignación por tipo — Actual">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Por sector (actual)" alt="Asignación por sector — Actual">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-now" alt="Asignación por sector — Actual">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Por geografía (actual)" alt="Asignación por geografía — Actual">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-now" alt="Asignación por geografía — Actual">
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
| **Por Tipo** | Qué es cada posición — su [tipo de activo](../../financial-theory/instruments/asset-types/index.md), como Acción, ETF, Bono, Fondo o Cripto — además de **Liquidez** para tu efectivo. Los subtipos cuentan con su [familia](../../financial-theory/instruments/asset-types/index.md#families-and-subtypes), como un **ETF de Renta Variable** con tus otros ETF. |
| **Por Sector** | Sector industrial: 💻 Tecnología, 🏦 Financiero, 💊 Salud, etc. |
| **Geográfica** | Dónde están invertidos tus activos, país por país, según la distribución geográfica de cada activo |

### 🕰️ Ahora e Historial

- **Ahora** — la asignación en el último día del rango seleccionado: un gráfico de anillo para **Por Tipo** y **Por Sector**, un mapa mundial para **Geográfica**. Pasa el cursor sobre una porción o un país para ver su porcentaje e importe. Por tipo, el anillo puede tener [dos anillos](#allocation-type-rings).
- **Historial** — un gráfico de áreas apiladas al 100% de cómo cambió la asignación a lo largo del tiempo, práctico para ver el rebalanceo. Por tipo, cada familia es un área; al pasar el cursor sobre una fecha se listan sus subtipos, como *ETF genérico* y *ETF de Renta Variable*.

El panel recuerda la vista y la pestaña en este navegador, para cada usuario, y las comparte con las páginas de brókeres.

### 🍩 Dos anillos por tipo {: #allocation-type-rings }

En cuanto mantienes un activo con un subtipo, como un **ETF de Renta Variable** o **Crowdfunding inmobiliario**, el anillo de **Ahora** de **Por Tipo** dibuja dos anillos:

- **Anillo interior** — una porción por familia, con su icono donde cabe: todos tus ETF (el **ETF** genérico y todos los subtipos) juntos, **Crowdfunding** con **Crowdfunding inmobiliario**, y todos los demás tipos, **Liquidez** incluida, por separado. Estas son las familias que agrupa el [menú de Tipo](../assets/create-edit.md#choosing-the-asset-type) del activo.
- **Anillo exterior** — más fino y separado, divide cada familia que contiene un subtipo en sus miembros, en tonalidades del color de la familia, con rótulo donde hay espacio. El miembro genérico se lee *ETF genérico* o *Crowdfunding genérico*.
- **Pasa el cursor** sobre una porción para ver su parte e importe; en el anillo exterior, una última línea que empieza por **↳** da la parte de toda la familia.
- **La leyenda** solo lista familias: al hacer clic en una se ocultan sus porciones en ambos anillos.

Sin ningún subtipo, el anillo se mantiene como un único anillo.

### 💵 El efectivo como Liquidez

Tu efectivo es la porción **Liquidez** de **Por Tipo** y **Por Sector**; el mapa **Geográfica** lo deja fuera, ya que el efectivo no pertenece a ningún país. Con el filtro de brókeres activado, el panel muestra solo los activos y el efectivo de los brókeres seleccionados.

---

## 🔗 Relacionado

- 💰 **[Tarjetas KPI](kpi-cards.md)** — Patrimonio Neto, P&L período, Rentabilidades
- 💼 **[NAV / Patrimonio Neto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- 💸 **[Capital Depositado y P&L Total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** · **[MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** · **[Efecto timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)**
- 🛠️ **[Interioridades de los gráficos](../../developer/frontend/components/charts.md)** — para desarrolladores: cómo se construyen estos gráficos

---

*[⬅️ Volver al Resumen del Panel](index.md)*
