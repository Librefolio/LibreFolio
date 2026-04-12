# ➕ Agregar un Par de Divisas

Para agregar un nuevo par de divisas a su panel de control de FX:

1. Haga clic en **"Add Pair"** en la página de la lista de FX
2. Seleccione las **dos divisas** utilizando el menú desplegable de búsqueda
3. El sistema descubre automáticamente las **rutas de datos** disponibles, tanto rutas directas como en cadena
4. Seleccione la ruta de su preferencia y haga clic en **Confirmar** — el par se crea y la sincronización de datos comienza automáticamente

---

## 🔗 Rutas Directas

Si un proveedor admite ambas divisas directamente (por ejemplo, ECB para EUR→USD), verá una sección de **Rutas Directas**:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="add-pair-routes" alt="Add Pair — Direct Routes" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Rutas en Cadena

Para pares exóticos (por ejemplo, RON→JPY) donde ningún proveedor único cubre ambas divisas, el sistema construye **cadenas de conversión**: rutas de múltiples pasos a través de divisas intermedias:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="add-pair-chain" alt="Add Pair — Chain Routes" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! example "Chain Example"

    **RON → JPY** vía ECB:

    1. RON → EUR (ECB proporciona RON/EUR)
    2. EUR → JPY (ECB proporciona EUR/JPY)

    El tipo de cambio final se calcula multiplicando los tipos de cambio intermedios.

---

## 🧭 Cómo funciona el Descubrimiento de Rutas

Cuando selecciona dos divisas, LibreFolio consulta todos los proveedores instalados para encontrar:

- 🔗 **Rutas directas**: un único proveedor que cubre ambas divisas
- 🔀 **Rutas en cadena**: dos o más proveedores que juntos pueden conectar las divisas a través de una divisa intermedia (por ejemplo, EUR)

Cada ruta muestra:

- 🏛️ El nombre y el icono del **proveedor**
- ➡️ La **dirección** (base → cotización)
- 🔢 Para cadenas: la **divisa intermedia** y el **número de saltos**

Puede elegir cualquier ruta disponible basándose en su preferencia de fuente de datos, periodo de cobertura o frecuencia de actualización.

Para obtener detalles técnicos sobre el algoritmo de enrutamiento, consulte la documentación para desarrolladores: [FX Configuration & Routing](../../developer/backend/fx/configuration.md).
