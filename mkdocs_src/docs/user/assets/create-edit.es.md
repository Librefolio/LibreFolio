# ➕ Crear y Editar Activos

## Crear un Nuevo Activo

1. Haga clic en **+ Nuevo Activo** en la página de activos
2. Complete la información básica:
 - **Nombre** (requerido)
 - **Categoría** (requerido): Stock, ETF, Bond, Crypto, Commodity, P2P, Index, etc.
 - **Moneda** (requerido): la moneda en la que está denominado el activo
 - **Identificadores**: ISIN, ticker, CUSIP, SEDOL, etc.
3. Opcionalmente, configure un **[Proveedor](providers/index.md)** para la obtención automática de precios
4. Opcionalmente, añada distribuciones **sectoriales** y **geográficas**
5. Haga clic en **Guardar**

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="create-modal" alt="Modal de Creación de Activo" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

## 🧪 Probar la Configuración del Proveedor

Después de configurar un proveedor, haga clic en **Probar Configuración** para verificar que los datos de precios se pueden obtener. La prueba verifica:

- **Precio Actual**: obtiene el precio más reciente
- **Historial**: obtiene datos de precios históricos (si es compatible)

Los resultados se muestran en línea con los tiempos de ejecución. Una advertencia ⚠️ significa que la operación no es compatible con este proveedor (por ejemplo, CSS Scraper no es compatible con el historial).

## 🔌 Asignación de Proveedores

Cada activo puede tener asignado un proveedor de precios. Consulte [Proveedores](providers/index.md) para obtener detalles sobre los proveedores disponibles y su configuración.

## ⏱️ Intervalo de Obtención

El intervalo de obtención controla con qué frecuencia LibreFolio actualiza automáticamente los datos de precio del activo. El valor predeterminado es 24 horas (`24:00`). Formato: `HH:MM`.

## 🛠️ Editar un Activo

Haga clic en el botón **Editar** (✏️) en la [página de detalles](detail/index.md) para abrir el modal del activo con todos los campos precargados. Todos los campos son editables, incluida la configuración del proveedor y las distribuciones.

## 🔗 Relacionado

- 📊 **[Página de Detalles del Activo](detail/index.md)** — Ver y analizar los datos del activo
- 🔌 **[Proveedores](providers/index.md)** — Proveedores de precios disponibles
