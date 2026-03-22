# ➕ Agregar un Par de Divisas

Para agregar un nuevo par de divisas a tu panel de FX:

1. Haz clic en **"Agregar Par"** en la página de la lista de FX
2. Selecciona las **dos divisas** usando el menú desplegable de búsqueda
3. El sistema identifica automáticamente las **rutas de datos** disponibles — tanto rutas directas como en cadena
4. Selecciona la ruta que prefieras y haz clic en **Confirmar** — se crea el par y la sincronización de datos comienza automáticamente

---

## 🔗 Rutas Directas

Si un proveedor admite ambas divisas directamente (por ejemplo, ECB para EUR→USD), verás una sección **Rutas Directas**:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="add-pair-routes" alt="Agregar Par — Rutas Directas" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Rutas en Cadena

Para pares exóticos (por ejemplo, RON→JPY) donde ningún proveedor cubre ambas divisas, el sistema construye **rutas en cadena** — caminos de múltiples pasos a través de divisas intermedias:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="add-pair-chain" alt="Agregar Par — Rutas en Cadena" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! example "Ejemplo de Ruta en Cadena"
 **RON → JPY** a través de ECB:

 1. RON → EUR (ECB proporciona RON/EUR)
 2. EUR → JPY (ECB proporciona EUR/JPY)

 La tasa final se calcula multiplicando las tasas intermedias.

---

## 🧭 Cómo Funciona el Descubrimiento de Rutas

Cuando seleccionas dos divisas, LibreFolio consulta a todos los proveedores instalados para encontrar:

- 🔗 **Rutas directas**: un único proveedor que cubre ambas divisas
- 🔀 **Rutas en cadena**: dos o más proveedores que juntos pueden conectar las divisas a través de una divisa intermedia (por ejemplo, EUR)

Cada ruta muestra:

- 🏛️ El **nombre** y **icono** del proveedor
- ➡️ La **dirección** (base → cotización)
- 🔢 Para rutas en cadena: la **divisa intermedia** y el **número de saltos**

Puedes elegir cualquier ruta disponible según tu preferencia en cuanto a la fuente de datos, período de datos disponibles o frecuencia de actualización.

Para detalles técnicos sobre el algoritmo de enrutamiento, consulta la documentación para desarrolladores: [Configuración y Enrutamiento FX](../../developer/backend/fx/configuration.md).
