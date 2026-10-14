# 🔌 Configuración de Proveedores

Cada par de divisas obtiene sus tipos de cambio de una o más **rutas**: un banco central que cotiza el par
directamente, o una cadena de conversiones. Aquí ves y cambias las rutas del par que estás
viendo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="provider-config" alt="Configuración del proveedor" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔓 Cómo Acceder

En la página de detalle del par, haz clic en **Proveedores** (🔧) en la barra de herramientas, junto a **Sincronizar**. Se abre la ventana **Editar Proveedores del Par**.

---

## 📋 Qué Ves

Bajo **Rutas de Conversión**, cada fila es una ruta, en orden de prioridad:

- las divisas, con el proveedor de cada paso entre ellas — pasa el cursor sobre el icono de un proveedor para ver su
  nombre y descripción;
- la insignia de prioridad: **#1** se usa primero;
- ⚠️ cuando un proveedor tiene una advertencia de datos, como los tipos de cambio mensuales del SNB;
- 🗑️ para eliminar la ruta.

---

## 🔧 Cambiar Proveedores

1. Haz clic en **Añadir ruta de conversión** y elige una ruta bajo **Conversión directa (1 paso)** o
   **Conversión en cadena**. Escribe en el cuadro de búsqueda para filtrar por proveedor, divisa o país.
2. Arrastra las filas para establecer su prioridad (en un teléfono, usa las flechas arriba y abajo).
3. Haz clic en **Guardar Configuración**: la siguiente sincronización usa las nuevas rutas.

??? note "🔗 También crear pares intermedios — cuando eliges una ruta en cadena"

    Márcalo para guardar cada paso de la cadena como un par propio, con su proveedor, para que puedas
    sincronizarlo y verlo por sí solo.

??? note "✍️ Sin rutas restantes — cuando las eliminas todas"

    El par se vuelve manual: **Sincronizar** se deshabilita, e introduces los tipos de cambio tú mismo en el
    [editor de datos](data-editor.md).

---

## 🔢 Prioridad y fallback

Una sincronización prueba las rutas en orden de prioridad. Si una falla — por ejemplo, su banco central no
responde — pasa a la siguiente; el par solo falla cuando fallan todas las rutas. Con EUR/USD configurado como
**#1** ECB y **#2** FED, una sincronización que no puede acceder al ECB usa el tipo de cambio del FED en su lugar.

---

## 📚 Relacionado

- ➕ **[Añadir un Par](../add-pair.md)** — Descubrimiento completo de rutas (rutas directas + en cadena)
- 🔄 **[Sincronización](../sync.md)** — Cómo la sincronización usa los proveedores configurados
- 🔌 **[Proveedores FX](../providers/index.md)** — Guía de usuario y detalles sobre cada proveedor (ECB, FED, BOE, SNB)
- 🧮 **Para desarrolladores: [Algoritmo de Cadena FX](../../../developer/frontend/fx-chain-algorithm.md)** — Cómo se encuentran y calculan las rutas en cadena
