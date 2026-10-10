# 📈 Gráfico interactivo

El gráfico es el corazón de la página del activo: el historial de precios, o cuánto se movió el precio en una ventana móvil. Desplázate para hacer zoom, arrastra para desplazarte y pasa el cursor sobre un punto para ver sus valores.

_Última actualización: 2026-10-08_

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Gráfico de precios del activo" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Precios o rentabilidad móvil {: #primary-modes }

Los dos botones situados encima del gráfico eligen lo que este dibuja:

- **Precios** — el historial de precios, con los [eventos](events.md) del activo como marcadores.
- **Rentabilidad móvil** — para cada fecha, la variación del precio en una ventana que tú eliges ([más abajo](#rolling-return)).

La página siempre se abre en **Precios**.

### 🗓️ Ventana de rentabilidad móvil {: #rolling-return }

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart-rolling-return" alt="Gráfico del activo en modo Rentabilidad móvil, con la ventana 1Y y un activo de comparación" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Esta vista responde a *¿cuánto se ha movido el precio en la ventana, en cada fecha?* Cada punto compara el cierre de ese día con el cierre exactamente $N$ días naturales antes:

$$
R(d) = \frac{P(d)}{P(d-N)} - 1
$$

donde $P$ es el último cierre conocido ese día, en la divisa del gráfico → [Rentabilidad móvil en días naturales](../../../financial-theory/fundamentals/returns.md#rolling-return-calendar).

Elige $N$ con el control **Ventana** situado junto a los dos botones:

- **1S**, **1M**, **3M**, **1A** — 7, 30, 90 y 365 días.
- **Personalizado** — un número entero con **S**, **M** o **A**, contados como 7, 30 y 365 días: `3M` son 90 días.
- **?** abre esta sección del manual.

La ventana puede ser más larga que las fechas que hay en pantalla: LibreFolio lee los precios más antiguos que necesita. Se recuerda para este activo, en este navegador.

Cómo interpretarla:

- **Por encima de cero**, el precio es más alto que $N$ días antes; **por debajo de cero**, más bajo.
- **Pasa el cursor sobre un punto**: ↩ indica la fecha con la que se compara; 📅 y 💱 indican las fechas del precio y de los tipos de cambio realmente utilizados, cuando alguno de ellos es más antiguo.
- Las **[comparaciones de activos](signals.md#data-comparison)** también se convierten en rentabilidades móviles, con la misma ventana y divisa.
- **Solo precio**: los dividendos, los intereses y tus transacciones no se incluyen.

??? note "🧩 Huecos y líneas cortas — cuando el historial está incompleto"

    Un punto permanece vacío, nunca estimado, cuando falta alguno de sus dos precios o alguno de ellos no es positivo. Cada línea empieza en la primera fecha en que puede calcularse, así que un activo reciente o un tipo de cambio ausente acorta solo su propia línea, y un precio ausente posterior deja un hueco. Cuando solo puede calcularse una parte del rango, una nota bajo el gráfico lo indica; cuando no puede calcularse nada, un mensaje sustituye al gráfico.

---

## 🎛️ Elegir lo que muestra el gráfico

### 📅 Rango de fechas

El rango de fechas de la barra de herramientas de la página establece las fechas en pantalla: **1S**, **1M**, **3M**, **6M**, **1A**, **2A**, **YTD**, **MAX** o **Personalizado** con un calendario. Cuando hay espacio libre en la barra, aparecen más preajustes (3A, 5A, 10A, WTD, MTD, QTD). El rango que elijas se mantiene en las páginas de Panel, bróker, activo y FX de la misma pestaña del navegador.

En un rango largo, el gráfico puede agrupar los días en semanas o meses para seguir siendo legible: una insignia **Semanal** o **Mensual** en su esquina superior izquierda lo indica.

### 💱 Convertir a otra divisa

**Convertir a**, junto al precio, muestra el gráfico en otra divisa, con una línea 💱 discontinua para el precio en la divisa propia del activo. El menú enumera las divisas a las que pueden llegar tus pares FX; **Crear par FX…** en su parte inferior añade un par que falte. Las rentabilidades móviles también se calculan en la divisa elegida.

??? note "💱 Cuando falta un tipo de cambio"

    Un banner sobre el gráfico indica el par, con un atajo para crearlo o abrirlo. La opción **Sincronizar** de la página descarga los tipos de los pares que existen; nunca crea uno.

### 📊 Línea o velas, Abs o %

En modo **Precios**, los botones de la esquina superior izquierda del gráfico alternan:

- entre una **línea** y **velas japonesas**, que necesitan los precios de apertura, máximo y mínimo;
- entre **Abs**, los precios, y **%**, la variación desde el primer día del rango.

---

## 🧰 Herramientas del gráfico

Los tres botones de la esquina superior derecha del gráfico:

- **📏 Añadir medida** — compara dos puntos: consulta [Medidas](measures.md). **Precios** y **Rentabilidad móvil** mantienen medidas independientes.
- **✏️ Editar precios y eventos** — abre el [Editor de datos](data-editor.md), solo en modo **Precios**.
- **⚙️ Estética** — **Relleno de área**, **Colores de línea base** (verde por encima del valor inicial, o por encima de cero en %, rojo por debajo), **Líneas de cuadrícula**, **Degradado de datos obsoletos** (atenúa los puntos cuyo precio o tipo de cambio se arrastra desde un día anterior) y **Escala del eje Y** (**Automática**, **Incluir 0** o límites **personalizados**). Las velas japonesas desactivan el relleno de área, los colores de línea base y el degradado de datos obsoletos.

Estos ajustes y tus señales se recuerdan para este activo, en este navegador. Para cambiarlos de una vez para todos los activos, usa **Configuración** en la [página de Activos](../index.md): consulta [Ajustes del gráfico](../../fx/chart-settings.md).

---

## 🔗 Relacionado

- 📊 **[Señales](signals.md)** — Superpón indicadores técnicos
- 📐 **[Medidas](measures.md)** — Mide diferencias de precio
- 📅 **[Eventos](events.md)** — Comprende los marcadores de eventos
- 📚 **[Rentabilidades y tasas de crecimiento](../../../financial-theory/fundamentals/returns.md)** — Cómo se calculan las rentabilidades simples, anualizadas y móviles
- 🛠️ **[Funcionamiento interno del gráfico](../../../developer/frontend/components/charts.md)** — Para desarrolladores: los dos modos, dónde reside el estado del gráfico y cómo se sincroniza la página
