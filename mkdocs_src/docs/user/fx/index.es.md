# 💱 Tasas FX (Cambio de Divisas)

LibreFolio incluye un sistema de gestión de **Foreign Exchange (FX)** completo. Permite realizar el seguimiento de los tipos de cambio entre cualquier par de divisas, con sincronización automática desde fuentes oficiales de bancos centrales.

---

## 📋 La Página de Lista de FX

Navegue a **Tasas FX** desde la barra lateral para ver todos sus pares de divisas configurados:

<div class="lf-screenshot-carousel" data-carousel="carousel-fx-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="fx" data-name="list" data-title="🔲 Vista de Cuadrícula de Tarjetas" alt="Página de Lista FX (Cuadrícula)">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="list-table" data-title="📋 Vista de Tabla de Datos" alt="Página de Lista FX (Tabla)">
</div>

Cada par de divisas se muestra con detalles que incluyen:

- 🔀 **Diseños de Cuadrícula / Tabla**: Alterne entre una cuadrícula visual de tarjetas y una tabla de datos compacta. La selección se guarda en el `localStorage` de su navegador para sesiones futuras.
- 🏷️ El **par de divisas** con banderas (ej., 🇪🇺 EUR → 🇺🇸 USD)
- 📈 El **tipo de cambio más reciente** y la tendencia del precio
- 🏛️ El **proveedor de datos activo** (ECB, FED, BOE, SNB o MANUAL)
- 📊 Un **gráfico de líneas simplificado (sparkline)** que muestra la tendencia del tipo de cambio en los últimos 30 días
- 🖱️ **Menú Contextual**: Haga clic derecho en cualquier fila del diseño de tabla para acciones rápidas (Editar, Sincronizar, Eliminar)

Puede **filtrar** por divisa para encontrar rápidamente un par específico:

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="list-filtered" alt="Lista FX Filtrada" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔮 ¿Qué sigue?

- ➕ **[Agregar un Par](add-pair.md)** — Cómo crear un nuevo par de divisas con rutas directas o en cadena
- 🔄 **[Sincronización](sync.md)** — Sincronización automática y manual desde proveedores
- 📊 **[Página de Detalle del Par](detail/index.md)** — Gráfico interactivo, medidas de señales, editor de datos, configuración del proveedor
- ⚙️ **[Configuración del Gráfico](chart-settings.md)** — Personalice la apariencia del gráfico y las superposiciones de señales
- 🔌 **[Proveedores](providers/index.md)** — Fuentes de bancos centrales compatibles para tasas FX (ECB, FED, BOE, SNB)
