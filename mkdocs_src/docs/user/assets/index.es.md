# 💼 Activos

Los activos son los instrumentos que tienes o sigues: acciones, ETF, bonos, cripto o una cuenta de ahorro con intereses programados. La página **Activos** los enumera todos, cada uno con un pequeño gráfico de precios, y abre la página de detalle de cualquiera de ellos.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="list" data-title="🔲 Vista de cuadrícula de tarjetas" alt="Página de lista de activos (cuadrícula)">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="list-table" data-title="📋 Vista de tabla de datos" alt="Página de lista de activos (tabla)">
</div>

## 📌 ¿Qué es un activo?

Cada activo tiene:

- **un nombre y identificadores** — ISIN, ticker u otros códigos;
- **un tipo** — acción, ETF, bono, cripto, materia prima… ([tipos de activos](../../financial-theory/instruments/asset-types/index.md));
- **una divisa** — aquella en la que se cotizan sus precios;
- **un proveedor de precios**, opcional — descarga por ti el precio actual y el historial ([Proveedores](providers/index.md));
- **un desglose por sector y país**, opcional;
- **eventos** — dividendos, desdoblamientos, intereses… ([Eventos de activos](detail/events.md)).

Los activos son compartidos por todos en este LibreFolio: tus transacciones deciden cuáles son tuyos.

## 📋 Explorar la lista

Abre **Activos** en la barra lateral y, a continuación:

- **Elige un diseño** — los dos botones junto a **Añadir activo** alternan entre tarjetas con un pequeño gráfico (**Vista de cuadrícula**) y una tabla ordenable (**Vista de tabla**). Tu elección se recuerda en este navegador.
- **Elige el periodo** — el rango de fechas establece el periodo de los gráficos de las tarjetas y del cambio que muestran. Cuando el gráfico de una tarjeta agrupa los días en semanas o meses porque la representación es demasiado estrecha para tantos días, una pequeña insignia **Semanal** o **Mensual** en su esquina superior izquierda lo indica, como en el [gráfico de la página de detalle](detail/chart.md). En la tabla, las columnas **Δ** dan el cambio en un día y en cada periodo, de 1W a 5Y, que encaje en el rango.
- **Filtrar** — escribe en **Buscar activos...** para filtrar por nombre, y elige una o más divisas y tipos en los dos menús; la ✕ borra la búsqueda y ambos menús.
- **Mostrar activos archivados** — la lista empieza mostrando solo los activos **Activos**: activa **Inactivos** para añadir los archivados, o desactiva **Activos** para ver solo los archivados.

Haz clic en una tarjeta o en una fila para abrir la **[página de detalle](detail/index.md)** del activo. Allí, las flechas **‹ ›** recorren los activos en el orden en que los muestra esta lista, incluidos los filtros y la ordenación.

??? note "📉 Abs, % o Rentabilidad móvil en las tarjetas — solo vista de cuadrícula"

    El conmutador de la barra de herramientas tiene tres opciones: el icono de gráfico de líneas, el mismo que en las tarjetas, para los precios absolutos (su información emergente dice **Mostrar absoluto**), **%** (el cambio durante el periodo) y el icono de calendario para **Rentabilidad móvil**. Tu elección se aplica a todas las tarjetas, a su gráfico y a su cambio, y se recuerda en este navegador, para tu usuario, junto con los ajustes del gráfico.

    El botón de vista de una tarjeta pasa a la vista siguiente, **%** → **Rentabilidad móvil** → **Abs** → **%**, y muestra la vista a la que irá. Una tarjeta conserva su propia elección, incluso después de recargar, hasta que vuelvas a cambiar la barra de herramientas: eso restablece todas las tarjetas a la vista de la barra de herramientas.

    En **Rentabilidad móvil**, una tarjeta dibuja la rentabilidad móvil del activo, la misma rentabilidad de ventana de calendario que el modo **Rentabilidad móvil** de la [página de detalle del activo](detail/index.md), y sobre ella las rentabilidades móviles de las comparaciones de activos guardadas en esa tarjeta. Los demás indicadores permanecen guardados, solo ocultos en esta vista. El precio y el cambio en la parte superior de la tarjeta no cambian. Si el activo tiene menos historial que la ventana, la tarjeta muestra un mensaje breve en lugar del gráfico.

    La ventana se elige en [Ajustes del gráfico](../fx/chart-settings.md): 1W, 1M, 3M, 1Y o una personalizada. Hasta que elijas una, es automática: el mayor preajuste que encaje en el periodo mostrado en la lista, de modo que un rango de 3 meses usa 3M y un rango de un año o más usa 1Y.

    La [página de detalle](detail/index.md) del activo se abre en la vista de su tarjeta y con la ventana de Rentabilidad móvil de la tarjeta. Una vista elegida allí pasa a ser la de la tarjeta.

??? note "⚙️ El aspecto de los gráficos de las tarjetas"

    **Configuración** en la barra de herramientas establece a la vez el aspecto y las superposiciones de todos los gráficos de activos, y al aplicarla se sustituye la configuración propia de cada activo, incluidos los ajustes de las páginas de detalle. El ⚙️ de una tarjeta cambia solo la configuración de esa tarjeta. Consulta [Ajustes del gráfico](../fx/chart-settings.md).

### 🗂️ Tus activos, activos de otros usuarios, en seguimiento

Ambos diseños dividen la lista en hasta tres paneles, cada uno con su recuento; un panel vacío no se muestra.

| Panel | Qué contiene |
|---|---|
| **Tus activos** | Activos mantenidos ahora en un bróker que tienes |
| **Activos de otros usuarios** | Activos mantenidos ahora solo por otros usuarios — en brókeres que no tienes |
| **En seguimiento** | Activos que ahora no tiene nadie — nunca comprados o ya vendidos, mantenidos en el radar |

Lo que cuenta es la posición **hoy**: cuando vendes toda tu posición, el activo pasa a *Activos de otros usuarios* si alguien más aún lo tiene, y a *En seguimiento* en caso contrario. Los brókeres compartidos contigo como **Editor** o **Lector** cuentan como brókeres de otros usuarios, y una posición reducida a un remanente insignificante cuenta como no mantenida.

En la vista de tabla, cada panel es una tabla con sus propias páginas; cambiar el tamaño, mover u ocultar una columna se aplica a los tres.

## 🔄 Mantener los precios actualizados

- **Sincronizar todo** abre una ventana en la que **Iniciar sincronización** descarga los últimos precios de cada activo que tenga un proveedor; **Recargar todo** vuelve a cargar la lista desde lo que LibreFolio ha almacenado. Pasa el cursor sobre **Configuración**, **Sincronizar todo** o **Recargar todo** durante medio segundo para leer qué hace el botón. Cuando el periodo ya contiene precios almacenados para algunos de los activos, la ventana lo indica antes de que empieces: la sincronización los sustituye por los valores del proveedor, incluidas tus ediciones manuales. En la pestaña **[Correlación](correlation.md)** se convierten en **Sincronizar selección**, que también descarga los tipos de cambio para convertir los activos seleccionados, y **Recargar todo**, que recalcula todos los análisis.
- **Precios en vivo** — mientras el rango de fechas termina hoy, los precios se actualizan solos: cada minuto en esta página, cada 30 segundos en la página de un activo. Un precio se vuelve verde cuando ha subido desde la actualización anterior, y rojo cuando ha bajado; cuando el mercado está cerrado ves el último cierre, sin color. Para ahorrar recursos al servidor y a los proveedores de precios, la actualización se pausa mientras la pestaña del navegador está en segundo plano y tras dos minutos sin usar la página: entonces aparece una pequeña etiqueta **Actualizaciones pausadas** en la parte superior de la página. No hay nada que pulsar: en cuanto vuelves a la pestaña, mueves el ratón o pulsas una tecla, los precios se actualizan de nuevo por sí solos.
- **En segundo plano**, el servidor actualiza los precios según una programación que establece tu administrador ([Planificador de datos de mercado](../../admin/settings.md#market-data-scheduler)). El Panel muestra los precios almacenados.

## 🖱️ Actuar sobre un activo

Cada tarjeta tiene sus propios botones; en la tabla, el **⋮** al final de una fila, o un clic derecho, abre las mismas acciones:

- **Sincronizar** — descarga los precios del activo para el periodo seleccionado. Necesita un proveedor, y la tabla también lo bloquea para un activo archivado.
- **Recargar** — vuelve a cargar sus precios desde lo que LibreFolio ha almacenado.
- **Fusionar con…** — fusiona un duplicado en otro activo, que conserva todo ([Crear y editar](create-edit.md)).
- **Eliminar** — elimina un activo que ninguna transacción utiliza, junto con su proveedor, sus precios y sus eventos (dividendos, desdoblamientos…).

En la tabla, marca varias filas para ejecutar **Sincronizar**, **Recargar** o **Eliminar** en todas ellas a la vez.

??? warning "🗑️ Cuando un activo no se puede eliminar"

    Un activo no se elimina mientras **cualquier** transacción lo utilice, incluso una en un bróker que no puedes ver. El resultado muestra cuántas transacciones lo utilizan, con un enlace **Transacciones** filtrado a ese activo. Esa página muestra solo los brókeres a los que puedes acceder, por lo que puede listar menos transacciones que el recuento.

    Cuando la lista ya cuenta transacciones para el activo, su confirmación se abre directamente en ese resultado, sin botón **Eliminar**: no hay nada que confirmar. De lo contrario, el resultado aparece después de que confirmes, y LibreFolio sigue comprobando antes de eliminar.

## 🧭 Funciones

### ➕ [Crear y editar](create-edit.md)

Crea un activo, conéctalo a un proveedor de precios y mantén sus datos correctos.

### 🧪 [Pestaña Correlación](correlation.md)

Compara una selección de activos en paralelo — matriz de correlación, pérdidas, riesgo frente a rentabilidad y repetición histórica, solo en porcentajes.

### 📊 [Página de detalle del activo](detail/index.md)

El gráfico de precios con sus señales, medidas y eventos, el editor de datos y la clasificación.

### 🔌 [Proveedores](providers/index.md)

Precios automáticos de Yahoo Finance, justETF, Borsa Italiana, el CSS Scraper o el motor de Inversión programada.

---

## 🔗 Relacionado

- 📚 **[Teoría financiera — Tipos de activos](../../financial-theory/instruments/asset-types/index.md)** — Acciones, ETF, bonos, cripto, etc.
- 💱 **[Tipos de cambio](../fx/index.md)** — Tipos de cambio de divisas usados para la conversión entre divisas
- 🛠️ **[Precios en vivo](../../developer/frontend/components/features/live-ticker.md)** — Para desarrolladores: cómo las páginas consultan los precios en vivo
