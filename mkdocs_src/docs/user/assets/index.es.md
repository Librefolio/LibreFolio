# 💼 Activos

Los activos son los instrumentos que posees o sigues: acciones, ETF, bonos, criptomonedas o una cuenta de ahorro con intereses programados. La página **Activos** los enumera todos, cada uno con un pequeño gráfico de precios, y abre la página de detalle de cualquiera de ellos.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="list" data-title="🔲 Vista de cuadrícula de tarjetas" alt="Página de lista de activos (Cuadrícula)">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="list-table" data-title="📋 Vista de tabla de datos" alt="Página de lista de activos (Tabla)">
</div>

## 📌 ¿Qué es un activo?

Cada activo tiene:

- **un nombre e identificadores** — ISIN, ticker u otros códigos;
- **un tipo** — acción, ETF, bono, criptomoneda, materia prima… ([tipos de activos](../../financial-theory/instruments/asset-types/index.md));
- **una moneda** — aquella en la que se cotizan sus precios;
- **un proveedor de precios**, opcional — descarga el precio actual y el historial por ti ([Proveedores](providers/index.md));
- **un desglose por sector y país**, opcional;
- **eventos** — dividendos, desdoblamientos, intereses… ([Eventos de activos](detail/events.md)).

Los activos son compartidos por todos en este LibreFolio: tus transacciones deciden cuáles son tuyos.

## 📋 Explorar la lista

Abre **Activos** en la barra lateral, luego:

- **Elige un diseño** — los dos botones junto a **Añadir activo** alternan entre tarjetas con un pequeño gráfico (**Vista de cuadrícula**) y una tabla ordenable (**Vista de tabla**). Tu elección se recuerda en este navegador.
- **Elige el período** — el rango de fechas establece el período de los gráficos de las tarjetas y del cambio que muestran. En la tabla, las columnas **Δ** dan el cambio en un día y en cada período, de 1S a 5A, que quepa dentro del rango.
- **Filtrar** — escribe en **Buscar activos...** para filtrar por nombre, y elige una o más monedas y tipos en los dos menús; la ✕ borra la búsqueda y ambos menús.
- **Mostrar activos archivados** — la lista comienza mostrando solo los **Activos**: activa **Inactivos** para añadir los archivados, o desactiva **Activos** para ver solo esos.

Haz clic en una tarjeta o en una fila para abrir la **[página de detalle](detail/index.md)** del activo. Allí, las flechas **‹ ›** recorren los activos en el orden en que los muestra esta lista, incluidos filtros y orden.

??? note "📉 Abs o % en las tarjetas — solo vista de cuadrícula"

    **Abs / %** en la barra de herramientas cambia cada tarjeta, su gráfico y su cambio, entre precios y porcentajes; el botón **%** en una tarjeta cambia solo esa tarjeta, hasta que vuelvas a cambiar la barra de herramientas. La página siempre se abre en **%**.

??? note "⚙️ El aspecto de los gráficos de las tarjetas"

    **Configuración** en la barra de herramientas establece el aspecto y las superposiciones de todos los gráficos de activos a la vez, y aplicarla reemplaza la configuración propia de cada activo, incluidas las páginas de detalle. El ⚙️ en una tarjeta cambia solo esa tarjeta. Consulta [Ajustes del gráfico](../fx/chart-settings.md).

### 🗂️ Tus activos, activos de otros usuarios, seguidos

Ambos diseños dividen la lista en hasta tres paneles, cada uno con su recuento; un panel vacío no se muestra.

| Panel | Qué contiene |
|---|---|
| **Tus activos** | Activos mantenidos ahora en un bróker que posees |
| **Activos de otros usuarios** | Activos mantenidos ahora solo por otros usuarios — en brókers que no posees |
| **Seguidos** | Activos que ahora no mantiene nadie — nunca comprados o ya vendidos, mantenidos en el radar |

Lo que cuenta es la posición **hoy**: cuando vendes toda tu posición, el activo pasa a *Activos de otros usuarios* si alguien más aún lo mantiene, y a *Seguidos* en caso contrario. Los brókers compartidos contigo como **Editor** o **Lector** cuentan como brókers de otros usuarios, y una posición reducida a un remanente insignificante cuenta como no mantenida.

En la vista de tabla, cada panel es una tabla con sus propias páginas; cambiar el tamaño, mover u ocultar una columna se aplica a las tres.

## 🔄 Mantener los precios actualizados

- **Sincronizar todo** abre una ventana donde **Iniciar sincronización** descarga los últimos precios de cada activo que tenga un proveedor; **Recargar todo** recarga la lista desde lo que LibreFolio ha almacenado. En la pestaña **[Correlación](correlation.md)**, se convierten en **Sincronizar selección**, que también descarga los tipos de cambio que convierten los activos seleccionados, y **Recargar todo**, que recalcula todos los análisis.
- **Precios en vivo** — mientras esta página o la página de un activo esté abierta y el rango de fechas termine hoy, los precios se actualizan solos de vez en cuando. Un precio se vuelve verde cuando ha subido desde la actualización anterior, rojo cuando ha bajado; cuando el mercado está cerrado, ves el último cierre, sin color.
- **En segundo plano**, el servidor actualiza los precios según una programación que establece tu administrador ([Planificador de datos de mercado](../../admin/settings.md#market-data-scheduler)). El Panel muestra los precios almacenados.

## 🖱️ Actuar sobre un activo

Cada tarjeta tiene sus propios botones; en la tabla, el **⋮** al final de una fila, o un clic derecho, abre las mismas acciones:

- **Sincronizar** — descarga los precios del activo para el período seleccionado. Necesita un proveedor, y la tabla también lo bloquea para un activo archivado.
- **Recargar** — recarga sus precios desde lo que LibreFolio ha almacenado.
- **Fusionar con…** — fusiona un duplicado en otro activo, que conserva todo ([Crear y editar](create-edit.md)).
- **Eliminar** — elimina un activo que ninguna transacción utiliza.

En la tabla, marca varias filas para **Sincronizar**, **Recargar** o **Eliminar** juntas.

??? warning "🗑️ Cuando un activo no se puede eliminar"

    Un activo no se elimina mientras **cualquier** transacción lo utilice, incluso una en un bróker que no puedes ver. El resultado muestra cuántas transacciones lo utilizan, con un enlace **Transacciones** filtrado por ese activo. Esa página muestra solo los brókers a los que puedes acceder, por lo que puede listar menos transacciones que el recuento.

## 🧭 Funcionalidades

### ➕ [Crear y editar](create-edit.md)

Crea un activo, conéctalo a un proveedor de precios y mantén sus detalles correctos.

### 🧪 [Pestaña Correlación](correlation.md)

Compara una selección de activos en paralelo — matriz de correlación, pérdidas, riesgo frente a rentabilidad y repetición histórica, solo en porcentajes.

### 📊 [Página de detalle del activo](detail/index.md)

El gráfico de precios con sus señales, medidas y eventos, el editor de datos y la clasificación.

### 🔌 [Proveedores](providers/index.md)

Precios automáticos de Yahoo Finance, justETF, Borsa Italiana, el CSS Scraper o el motor de inversión programada.

---

## 🔗 Relacionado

- 📚 **[Teoría financiera — Tipos de activos](../../financial-theory/instruments/asset-types/index.md)** — Acción, ETF, Bono, Criptomoneda, etc.
- 💱 **[Tipos de cambio](../fx/index.md)** — Tipos de cambio de divisas usados para la conversión entre divisas
- 🛠️ **[Precios en vivo](../../developer/frontend/components/features/live-ticker.md)** — Para desarrolladores: cómo las páginas consultan los precios en vivo
