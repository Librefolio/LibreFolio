# ➕ Agregar un Par de Divisas

Para agregar un nuevo par de divisas a su panel de control de FX:

1. Haga clic en **"Agregar par"** en la página de la lista de FX
2. Seleccione las **dos divisas** utilizando el menú desplegable de búsqueda
3. El sistema descubre automáticamente las **rutas de datos** disponibles, tanto rutas directas como en cadena
4. Seleccione la ruta de su preferencia y haga clic en **Confirmar** — el par se crea y la sincronización de datos comienza automáticamente

---

## 🛤️ Rutas de Conversión (Directas y en Cadena)

Cuando selecciona una divisa base y una divisa de cotización, LibreFolio consulta a todos los proveedores instalados para descubrir las mejores rutas de tipos de cambio disponibles.

<div class="lf-screenshot-carousel" data-carousel="carousel-fx-routes" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="fx" data-name="add-pair-routes" data-title="🔗 Rutas Directas" alt="Add Pair — Direct Routes">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="add-pair-chain" data-title="🔀 Rutas en Cadena (Multi-hop)" alt="Add Pair — Chain Routes">
</div>

### 🔗 Rutas Directas
Si un proveedor soporta directamente los tipos de cambio entre ambas divisas (por ejemplo, el BCE cotizando tipos de cambio para EUR 🇪🇺 / USD 🇺🇸), el sistema lo muestra como una opción de ruta directa.

### 🔀 Rutas en Cadena
Para pares exóticos (por ejemplo, RON 🇷🇴 / JPY 🇯🇵) donde ningún banco central publica tipos de cambio directamente, el sistema construye automáticamente **cadenas de conversión**: rutas de múltiples pasos a través de divisas intermedias (normalmente EUR 🇪🇺 o USD 🇺🇸).

!!! example "Ejemplo de Cadena"

    **RON 🇷🇴 → JPY 🇯🇵** vía BCE:

    1. RON 🇷🇴 → EUR 🇪🇺 (El BCE proporciona RON 🇷🇴 / EUR 🇪🇺)
    2. EUR 🇪🇺 → JPY 🇯🇵 (El BCE proporciona EUR 🇪🇺 / JPY 🇯🇵)

    El tipo de cambio final se calcula multiplicando los tipos de cambio intermedios.

---

## 🧭 Cómo funciona el descubrimiento de rutas

Cuando selecciona dos divisas, LibreFolio consulta a todos los proveedores instalados para encontrar:

- 🔗 **Rutas directas**: un único proveedor que cubre ambas divisas
- 🔀 **Rutas en cadena**: dos o más proveedores que juntos pueden conectar las divisas a través de una divisa intermedia (por ejemplo, EUR 🇪🇺)

Cada ruta muestra:

- 🏛️ El nombre y el icono del **proveedor**
- ➡️ La **dirección** (base → cotización)
- 🔢 Para las cadenas: la **divisa intermedia** y el **número de saltos**

Puede elegir cualquier ruta disponible basándose en su preferencia de fuente de datos, periodo de cobertura o frecuencia de actualización.

!!! info "Para los Curiosos: Detrás de escena"

    Si está interesado en los detalles matemáticos de cómo se calculan y enrutan las cadenas de conversión de múltiples saltos, puede leer la documentación para desarrolladores: [FX Configuration & Routing](../../developer/backend/fx/configuration.md) y [FX Chain Algorithm](../../developer/frontend/fx-chain-algorithm.md). 
 
    *Nota: Esta documentación técnica es solo para desarrolladores y no es necesaria para utilizar esta función.*
