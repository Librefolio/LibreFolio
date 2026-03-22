# 🔌 Configuración de Proveedores

Cada par de divisas en LibreFolio cuenta con el respaldo de uno o más **proveedores de datos** —bancos centrales que suministran los datos de tipo de cambio—. La Configuración de Proveedores le permite ver y modificar qué proveedores se utilizan para un par específico.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="provider-config" alt="Configuración de Proveedores" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔓 Cómo acceder

Haga clic en el botón **Proveedor** (⚙️) en la barra de herramientas del gráfico, en la página de detalle del par. Esto abre el modal de configuración de proveedores que muestra la configuración de rutas actual.

---

## 📋 Lo que verá

El modal muestra:

- 🛤️ **Ruta(s) actual(es)** — La(s) fuente(s) de datos activa(s) para este par, en orden de prioridad
- 🔀 **Tipo de ruta** — Si es una **ruta directa** (proveedor único) o una **ruta en cadena** (que implica múltiples conversiones intermediarias a través de una moneda intermediaria)
- 🏛️ **Detalles de cada proveedor** — Nombre, icono y moneda base de cada proveedor en la ruta

---

## 🔧 Cambiar proveedores

Puedes configurar **uno o más** proveedores de datos para cada par. Varios proveedores actúan como una **cadena de respaldo** — si la fuente principal falla, el sistema prueba automáticamente el siguiente.

Para cambiar o añadir proveedores:

1. Abre el modal de Configuración de Proveedores
2. **Elimina** la ruta actual si es necesario
3. **Añade una nueva ruta** — el sistema descubrirá las rutas disponibles (igual que al [añadir un nuevo par](../add-pair.md))
4. **Reordena** las rutas para establecer prioridades (arrastrar y soltar o botones de flecha)
5. Haz clic en **Guardar** — la siguiente sincronización obtendrá datos del proveedor disponible con mayor prioridad

---

## 🔢 Prioridad y Respaldo

Cuando se configuran múltiples rutas para un par:

- Las rutas se prueban **en orden de prioridad** (superior = mayor prioridad)
- Si el proveedor principal falla (timeout, error de API), el sistema automáticamente recurre a la siguiente ruta
- Puede **reordenar** las rutas para cambiar las prioridades

!!! example "Ejemplo de Respaldo"
    EUR/USD configurado con:

    1. **BCE** (principal) — Banco Central Europeo
    2. **FED** (respaldo) — Reserva Federal

    Si la API del BCE no está disponible durante la sincronización, el sistema utilizará automáticamente la FED.

---

## 📚 Relacionado

- ➕ **[Añadir un par](../add-pair.md)** — Descubrimiento completo de rutas (directas + en cadena)
- 🔄 **[Sincronización](../sync.md)** — Cómo la sincronización utiliza los proveedores configurados
- 📋 **[Lista de Proveedores de FX](../../../developer/backend/fx/providers_list.md)** — Detalles técnicos de cada proveedor (BCE, FED, BOE, SNB)

!!! tip "🔗 Cómo se calculan las rutas en cadena"
    Para ver el algoritmo matemático detrás de las cadenas de conversión multi-salto, consulte [Algoritmo de Cadena FX](../../../developer/frontend/fx-chain-algorithm.md).

