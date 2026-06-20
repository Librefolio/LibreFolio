# 💼 Activos

Los activos son el núcleo de LibreFolio. Representan cualquier instrumento financiero que poseas o sigas: acciones, ETF, bonos, criptomonedas o instrumentos personalizados como cuentas de ahorro con intereses programados.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="list" data-title="🔲 Vista de Cuadrícula de Tarjetas" alt="Página de Lista de Activos (Cuadrícula)">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="list-table" data-title="📋 Vista de Tabla de Datos" alt="Página de Lista de Activos (Tabla)">
</div>

## 📌 ¿Qué es un Activo?

Un activo en LibreFolio es un instrumento financiero con:

- **Identidad**: nombre, ISIN, ticker u otros identificadores
- **Categoría**: acción, ETF, bono, crypto, materia prima, etc.
- **Moneda**: la moneda en la que está denominado el activo
- **Proveedor**: un proveedor de precios opcional que obtiene automáticamente los precios actuales y el historial
- **Clasificación**: sector y distribución geográfica (gráficos de sectores + mapa mundial)
- **Transacciones**: operaciones de compra, venta, dividendos e intereses vinculadas a una cartera

## 📋 Lista de Activos

Navega a **Activos** en la barra lateral para ver todos tus activos. La página de la lista ofrece:

- 🔀 **Diseños de Cuadrícula / Tabla**: Elige entre una cuadrícula visual basada en tarjetas o una tabla de datos densa y ordenable. Tu preferencia de diseño se guarda automáticamente en el `localStorage` de tu navegador y se cargará en sesiones futuras.
- 🔎 **Búsqueda Inteligente**: Filtra activos en tiempo real introduciendo un nombre, ISIN, ticker o el nombre del bróker.
- 🏷️ **Filtros por tipo**: Filtra la lista para mostrar solo clases específicas (ej. ETF, Acciones, Bonos, Crypto).
- 🗃️ **Activos Archivados**: Alterna entre posiciones activas y activos archivados para mantener tu lista limpia.
- ⏱️ **Selector de Delta de Tiempo**: Cambia el marco temporal utilizado para calcular los cambios de precio (ej. `1D`, `1W`, `1M`, `YTD`, `ALL`).
- 🔄 **Sincronización y Actualización**: Sincroniza los datos de precios en tiempo real para todos los proveedores configurados o actualiza la lista manualmente.
- 🖱️ **Menú Contextual**: Haz clic derecho en cualquier fila del diseño de tabla de datos para acceder a acciones rápidas (Editar, Eliminar, Sincronizar).

Haz clic en cualquier tarjeta de activo para navegar a su **[página de detalles](detail/index.md)**.

## 🧭 Funcionalidades

### ➕ [Crear y Editar](create-edit.md)

Guía paso a paso para crear nuevos activos, configurar proveedores y editar activos existentes.

### 📊 [Página de Detalles del Activo](detail/index.md)

El corazón del análisis de activos: gráfico interactivo, señales técnicas, medidas, clasificación y editor de datos.

### 🔌 [Proveedores](providers/index.md)

Obtención automática de precios desde Yahoo Finance, justETF, CSS Scraper o el motor de Inversión Programada.

---

## 📡 Precios en Tiempo Real y Ticker en Tiempo Real

Para mantenerte actualizado sobre los movimientos del mercado sin obligarte a actualizar la página constantemente, LibreFolio muestra insignias de precios compactas y en vivo en las páginas del **panel de control** y de **Detalles del Activo**.

### ⏱️ Sondeo Automático (Polling)

Al visualizar estas páginas, tu navegador consulta al backend cada **30 segundos** los precios actuales de los activos. Este proceso se ejecuta silenciosamente en segundo plano y no es bloqueante (la interfaz de usuario está lista instantáneamente y los precios se cargan a medida que llegan).

### 🎨 Indicadores Visuales

Las insignias cambian de color dinámicamente para indicar los movimientos recientes de los precios en relación con el sondeo anterior:

* 🟢 **Verde (Sube)**: El precio del activo ha aumentado.
* 🔴 **Rojo (Baja)**: El precio del activo ha disminuido.
* ⚪ **Gris (Neutral)**: El precio no ha cambiado, se está cargando o el mercado está cerrado actualmente.

!!! note "Cierre de Mercado y fallbacks"

    Durante los fines de semana o cierres de mercado, el ticker en tiempo real mostrará el último precio de cierre disponible en una insignia gris neutral.

### 🔌 Caché y Programador en Segundo Plano

Para garantizar tiempos de carga rápidos y evitar que tu instancia sea limitada o bloqueada por proveedores externos (como Yahoo Finance), LibreFolio utiliza una estrategia de doble capa:

1. **Programador en Segundo Plano**: Un demonio de fondo en el servidor actualiza todos los precios de activos activos a intervalos regulares (predeterminado: cada 10 minutos, configurable por administradores en Global Settings). Esto mantiene actualizada la base de datos y la caché local de precios.
2. **Caché de Sondeo bajo Demanda**: Cuando el frontend consulta al backend, este lee desde esta caché local ya actualizada. Si la caché está vacía, el proveedor obtiene el precio y lo almacena con un TTL (Time-To-Live) de 120 segundos. Las actualizaciones de página posteriores o las vistas del panel de control de otros usuarios acceden directamente a la caché local.

---

## 🔗 Relacionados

- 📚 **[Teoría Financiera — Tipos de Activos](../../financial-theory/instruments/asset-types/index.md)** — Acciones, ETF, Bonos, Crypto, etc.
- 💱 **[Tipos de cambio FX](../fx/index.md)** — Tipos de cambio de moneda utilizados para la conversión entre diferentes divisas
