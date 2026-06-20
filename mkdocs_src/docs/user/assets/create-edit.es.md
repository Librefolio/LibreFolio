# ➕ Crear y Editar Activos

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-create" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="create-modal" data-title="➕ Formulario de Creación Manual" alt="Modal de Creación Manual">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="create-wizard-modal" data-title="🧙 Formulario de Auto-Creación del Asistente de Importación" alt="Crear Activo desde el Asistente">
</div>

## 🚀 Flujos de Creación de Activos

En LibreFolio, puedes crear nuevos activos de dos maneras diferentes:

=== "Creación Manual (con Búsqueda Inteligente)"

 ```mermaid
 flowchart LR
 A[Inicio: Clic en '+ Nuevo Activo'] --> B[Escribir Nombre, ISIN o Ticker en búsqueda inteligente]
 B --> C{¿Coincidencia encontrada?}
 C -->|Sí| D[Auto-completar detalles desde proveedores externos]
 C -->|No| E[Ingresar manualmente nombre, categoría y moneda]
 D --> F[Ajustar config / Asignar proveedor de precios]
 E --> F
 F --> G[Clic en Guardar]
 G --> H[Activo añadido a la biblioteca]
 ```

=== "Auto-Creación por Importación de Bróker"

 ```mermaid
 flowchart LR
 A[Inicio: Subir reporte CSV en el Asistente de Importación] --> B[Analizar filas del reporte]
 B --> C{¿ID de activo reconocido?}
 C -->|Sí| D[Auto-emparejar con activo existente]
 C -->|No| E[Marcar advertencia ⚠️ y mostrar botón 'Crear']
 E --> F[Clic en 'Crear' para abrir modal pre-rellenado]
 F --> G[Guardar activo para resolver el mapeo]
 G --> D
 D --> H[Confirmar todas las transacciones]
 ```

## 🧪 Prueba de Configuración del Proveedor

Después de configurar un proveedor, haz clic en **Test Configuration** para verificar que los datos de precios se puedan obtener. La prueba verifica:

- **Current Price**: obtiene el precio más reciente
- **History**: obtiene datos de precios históricos (si es compatible)

Los resultados se muestran en línea con los tiempos de ejecución. Una advertencia ⚠️ significa que la operación no es compatible con este proveedor (por ejemplo, el CSS Scraper no admite el historial).

## 🔌 Asignación de Proveedores

Cada activo puede tener un proveedor de precios asignado. Consulta [Proveedores](providers/index.md) para obtener detalles sobre los proveedores disponibles y su configuración.

## 🛠️ Editar un Activo

Haz clic en el botón **Edit** (✏️) en la [página de detalles](detail/index.md) para abrir el modal del activo con todos los campos pre-completados. Todos los campos son editables, incluida la configuración del proveedor y las distribuciones.

## 🔗 Relacionado

- 📊 **[Página de Detalles del Activo](detail/index.md)** — Ver y analizar datos del activo
- 🔌 **[Proveedores](providers/index.md)** — Proveedores de precios disponibles
