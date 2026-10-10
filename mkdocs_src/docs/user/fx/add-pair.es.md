# ➕ Añadir un par de divisas

Un par le dice a LibreFolio de dónde proviene el tipo de cambio entre dos divisas: un proveedor de banco central,
una cadena de proveedores o tipos que introduces tú mismo.

Haz clic en **Añadir par** en la [página de FX](index.md). La misma ventana se abre desde el panel, desde una
página de activo y desde el paso Cambio del asignador PAC.

---

## 🧭 Añadir un par paso a paso

### 💱 Paso 1: Elige las dos divisas

En **Añadir nuevo par de divisas**, elige la **Divisa base** y la **Divisa cotizada**. Cada lista
oculta las divisas que ya están emparejadas con la otra, por lo que un par no se puede añadir dos veces.

### 🛤️ Paso 2: Elige una ruta

Haz clic en **Añadir ruta de conversión** para ver todas las formas en que los proveedores pueden producir este tipo de cambio:

- 🔗 **Conversión directa (1 paso)** — un proveedor publica el par;
- 🔀 **Conversión en cadena** — pasa por otras divisas, agrupada por número de pasos;
- 🚫 **No utilizable** — proveedores que no pueden alcanzar este par.

Filtra con el cuadro de búsqueda (proveedor, divisa o país) y luego haz clic en una ruta para añadirla.

<div class="lf-screenshot-carousel" data-carousel="carousel-fx-routes" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="fx" data-name="add-pair-routes" data-title="🔗 Rutas directas" alt="Añadir Par — Rutas directas">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="add-pair-chain" data-title="🔀 Rutas en cadena (varios saltos)" alt="Añadir Par — Rutas en cadena">
</div>

??? tip "🛟 Rutas de respaldo — cuando añades más de una"

    LibreFolio usa la ruta **#1** primero y prueba la **#2** si falla durante una sincronización, y así sucesivamente. Arrastra
    las rutas para reordenarlas; 🗑️ elimina una, y ⚠️ muestra una nota de su proveedor.

??? note "🔀 Crear también pares intermedios — cuando eliges una ruta en cadena"

    Marca **Crear también pares intermedios** para guardar cada paso como un par propio. Luego puedes
    sincronizar cada paso por separado y convertir también a la divisa intermedia: una cadena solo almacena
    el tipo de cambio de su propio par.

??? note "✏️ Sin ruta — solo tipos manuales"

    Puedes guardar sin una ruta y luego introducir los tipos tú mismo en el
    [Editor de datos](detail/data-editor.md) del par.

### 💾 Paso 3: Guardar

Haz clic en **Guardar configuración**; la ventana se cierra inmediatamente.

- **Con un proveedor**, LibreFolio descarga el **historial completo** del par hasta hoy, sea cual
  sea el periodo que muestre la página, incluidos los pares intermedios. Un mensaje informa del resultado, en verde solo
  si todo funcionó.
- **Sin un proveedor**, un mensaje confirma que se creó el par.

Haz clic en el nombre del par en el mensaje para abrir su página.

---

## 🛤️ Rutas directas y en cadena

Una **ruta directa** usa un proveedor que publica ambas divisas, como el ECB para
EUR 🇪🇺 / USD 🇺🇸. Cuando ningún banco central publica el par, una **ruta en cadena** multiplica los tipos de cambio de
sus pasos. RON 🇷🇴 / USD 🇺🇸, por ejemplo, va RON → EUR → USD, ambos pasos del ECB, que
publica EUR/RON y EUR/USD:

$$
r_{\text{RON}\to\text{USD}} = r_{\text{RON}\to\text{EUR}} \times r_{\text{EUR}\to\text{USD}}
$$

- Una cadena tiene un tipo de cambio solo los días en que **cada paso** tiene uno.
- Si un paso falla durante una sincronización, toda la cadena falla: las cadenas más cortas son más fiables.
- El tipo de cambio de una cadena puede diferir ligeramente de una cotización directa de mercado.

---

## 🔗 Relacionado

- 🔄 **[Sincronización](sync.md)** — Descargar tipos de cambio de nuevo más tarde
- 🔌 **[Configuración del proveedor](detail/provider.md)** — Cambiar las rutas de un par después de crearlo
- 🧑‍💻 Para desarrolladores: **[Configuración y enrutamiento de FX](../../developer/backend/fx/configuration.md)** y **[Algoritmo de cadena de FX](../../developer/frontend/fx-chain-algorithm.md)**
