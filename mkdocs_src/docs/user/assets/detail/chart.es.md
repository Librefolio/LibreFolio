# 📈 Gráfico interactivo

El gráfico es el corazón de la página del activo: el historial de precios, o cuánto se ha movido el precio en una ventana móvil. Desplázate para hacer zoom, arrastra para mover la vista y pasa el cursor por un punto para ver sus valores.

_Última actualización: 2026-10-22_

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Gráfico de precios del activo" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Precios o rentabilidad móvil {: #primary-modes }

Los dos botones situados encima del gráfico eligen qué dibuja:

- **Precios** — el historial de precios, con los [eventos](events.md) del activo como marcadores.
- **Rentabilidad móvil** — para cada fecha, la variación del precio en una ventana que elijas ([más abajo](#rolling-return)).

La página se abre en la vista que tiene la tarjeta de este activo en la [página de Activos](../index.md): **Abs** o **%** abren **Precios** en esa vista, **Rentabilidad móvil** abre **Rentabilidad móvil**. Cambia el modo aquí, o **Abs** y **%** bajo **Precios**, y esa pasa a ser la vista del activo: su tarjeta y tu próxima visita se abrirán en ella. Se recuerda en este navegador, para tu usuario, junto con los ajustes del gráfico; el interruptor de la lista restablece cada tarjeta, y con ello cada página de detalle, a su vista.

### 🗓️ Ventana de rentabilidad móvil {: #rolling-return }

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart-rolling-return" alt="Gráfico del activo en modo Rentabilidad móvil con la ventana 1Y y un activo de comparación" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Esta vista responde a *¿cuánto se ha movido el precio en la ventana, en cada fecha?* Cada punto compara el cierre de ese día con el cierre exactamente $N$ días naturales antes:

$$
R(d) = \frac{P(d)}{P(d-N)} - 1
$$

donde $P$ es el último cierre conocido en ese día, en la moneda del gráfico → [Rentabilidad móvil en días naturales](../../../financial-theory/fundamentals/returns.md#rolling-return-calendar).

Elige $N$ con el control **Ventana**, junto a los dos botones:

- **1W**, **1M**, **3M**, **1Y** — 7, 30, 90 y 365 días.
- **Personalizado** — un número entero con **W**, **M** o **Y**, cuyos sufijos cuentan como 7, 30 y 365 días: `3M` son 90 días.
- **?** abre esta sección del manual.

La ventana puede ser más larga que las fechas en pantalla: LibreFolio lee los precios más antiguos que necesita. Es la misma que en la tarjeta del activo: la elegida para este activo o, hasta que elijas una, una automática, el mayor preajuste que encaje con las fechas en pantalla (para unos 3 meses se usa 3M, para un año o más se usa 1Y y para menos de una semana se usa 1W). La ventana que elijas aquí se guarda para este activo, en este navegador.

Cómo leerlo:

- **Por encima de cero**, el precio es mayor que hace $N$ días; **por debajo de cero**, menor.
- **Pasa el cursor por un punto**: ↩ da la fecha con la que se compara; 📅 y 💱 dan las fechas del precio y de los tipos de cambio realmente utilizados, cuando alguno de ellos es más antiguo.
- Las **[comparaciones de activos](signals.md#data-comparison)** también se convierten en rentabilidades móviles, con la misma ventana y moneda.
- **Solo precio**: no se incluyen dividendos, intereses ni tus transacciones.

??? note "🧩 Huecos y líneas cortas — cuando el historial está incompleto"

    Un punto permanece vacío, nunca estimado, cuando falta alguno de sus dos precios o alguno de ellos no es positivo. Cada línea comienza en la primera fecha en que puede calcularse, así que un activo reciente o un tipo de cambio ausente acorta solo su propia línea, y un precio que falte más adelante deja un hueco. Cuando solo puede calcularse parte del rango, una nota bajo el gráfico lo indica; cuando no puede calcularse nada, un mensaje sustituye al gráfico.

---

## 🎛️ Elegir qué muestra el gráfico

### 📅 Rango de fechas

El rango de fechas de la barra de herramientas de la página determina las fechas en pantalla: **1W**, **1M**, **3M**, **6M**, **1Y**, **2Y**, **YTD**, **Todo** o **Personalizado**, un número de días, semanas, meses o años hacia atrás desde hoy; haz clic en una fecha para elegir los dos extremos en un calendario. Los dos extremos deben ser días distintos: el día en el que haces clic primero no se puede volver a pulsar, y una fecha escrita igual al otro extremo se muestra en rojo. Si sobra espacio en la barra, aparecen más preajustes (3Y, 5Y, 10Y, WTD, MTD, QTD). El rango que elijas te acompaña a las páginas del panel, del bróker, del activo y de FX de la misma pestaña del navegador.

En un rango largo, el gráfico puede agrupar los días en semanas o meses para seguir siendo legible: una insignia **Semanal** o **Mensual** en su esquina superior izquierda lo indica.

### 💱 Convertir a otra moneda

**Convertir a**, junto al precio, muestra el gráfico en otra moneda, con una línea 💱 discontinua para el precio en la moneda propia del activo. El menú enumera las monedas a las que pueden llegar tus pares FX; **Crear forex…** en su parte inferior añade un par que falte. Las rentabilidades móviles también se calculan en la moneda elegida.

??? note "💱 Cuando falta un tipo de cambio"

    Un banner encima del gráfico indica el par FX, con un atajo para crearlo o abrirlo. La opción **Sincronizar** de la página descarga los tipos de cambio de los pares FX que existen; nunca crea uno.

### 📊 Línea o velas, Abs o %

En modo **Precios**, los botones de la esquina superior izquierda del gráfico permiten alternar:

- entre una **línea** y **velas japonesas**, que necesitan los precios de apertura, máximo y mínimo;
- entre **Abs**, los precios, y **%**, la variación desde el primer día del rango.

---

## 🧰 Herramientas del gráfico

Los tres botones de la esquina superior derecha del gráfico:

- **📏 Añadir medida** — compara dos puntos: consulta [Medidas](measures.md). **Precios** y **Rentabilidad móvil** mantienen medidas separadas.
- **✏️ Editar precios y eventos** — abre el [Editor de datos](data-editor.md), solo en modo **Precios**.
- **⚙️ Estética** — **Relleno de área**, **Colores de la línea base** (verde por encima del valor inicial, o por encima de cero en %, rojo por debajo), **Líneas de cuadrícula**, **Degradado de datos obsoletos** (atenúa los puntos cuyo precio o tipo de cambio se arrastra desde un día anterior) y **Escala del eje Y** (**Auto**, **Incluir 0** o límites **Personalizados**). Las velas japonesas desactivan el relleno de área, los colores de la línea base y el degradado de datos obsoletos.

Esta configuración y tus señales se recuerdan para este activo, en este navegador. Para cambiarla de una vez para todos los activos, usa **Configuración** en la [página de Activos](../index.md): consulta [Ajustes del gráfico](../../fx/chart-settings.md).

---

## 🔗 Relacionado

- 📊 **[Señales](signals.md)** — Superpón indicadores técnicos
- 📐 **[Medidas](measures.md)** — Mide diferencias de precios
- 📅 **[Eventos](events.md)** — Comprende los marcadores de eventos
- 📚 **[Rentabilidades y tasas de crecimiento](../../../financial-theory/fundamentals/returns.md)** — Cómo se calculan las rentabilidades simples, anualizadas y móviles
- 🛠️ **[Funcionamiento interno del gráfico](../../../developer/frontend/components/charts.md)** — Para desarrolladores: los dos modos, dónde vive el estado del gráfico y cómo se sincroniza la página
