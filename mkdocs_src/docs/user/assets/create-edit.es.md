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

Después de configurar un proveedor, haz clic en **Prueba de configuración** para verificar que los datos de precios se puedan obtener. La prueba verifica:

- **Precio actual**: obtiene el precio más reciente
- **Historial**: obtiene datos de precios históricos (si es compatible)

Los resultados se muestran en línea con los tiempos de ejecución. Una advertencia ⚠️ significa que la operación no es compatible con este proveedor (por ejemplo, el CSS Scraper no admite el historial).

## 🔎 Detalles de Búsqueda Inteligente

La búsqueda inteligente consulta primero la propia búsqueda de cada proveedor. Si un proveedor
compatible no encuentra nada, LibreFolio puede intentar una búsqueda de enlaces web para resolver las páginas
de los proveedores en candidatos a activos. Para Borsa Italiana, esto significa que una URL de fondo/detalle puede
convertirse en un activo listo para guardar con los `provider_params` necesarios para fijar el precio del fondo.

Para los fondos de Borsa Italiana, el ISIN visible identifica el fondo cuando está disponible, pero el precio
utiliza el código de fondo interno de Borsa guardado en la configuración del proveedor. El NAV actual se
utiliza solo cuando tiene fecha de hoy; el historial contiene un punto NAV en su fecha real.

## 🔌 Asignación de Proveedores

Cada activo puede tener un proveedor de precios asignado. Consulta [Proveedores](providers/index.md) para obtener detalles sobre los proveedores disponibles y su configuración.

## 🛠️ Editar un Activo

Haz clic en el botón **Editar** (✏️) en la [página de detalles](detail/index.md) para abrir el modal del activo con todos los campos pre-completados. Todos los campos son editables, incluida la configuración del proveedor y las distribuciones.

El campo **Otros identificadores** es una lista editable de identificadores alternativos. Las importaciones
y los proveedores pueden agregar etiquetas de bróker, códigos técnicos o identificadores de respaldo
allí; cada valor sigue siendo un elemento de lista independiente.

## 🏷️ Un instrumento, varios códigos

El mismo valor puede conocerse con más de un código. Cuando ocurre, LibreFolio mantiene **un solo
activo** y guarda los códigos adicionales en **Otros identificadores**, donde se pueden buscar y
sirven para reconocer el instrumento en importaciones posteriores.

Qué código ocupa el campo **ISIN** principal no es cuestión de gusto:

!!! tip "Deja como principal el código cotizado"

    El precio es el valor de la última compraventa, así que solo un código realmente negociable
    tiene precio. Pon el código negociable en **ISIN** y todo lo demás en **Otros
    identificadores**; de lo contrario ningún proveedor podrá valorar el activo.

### Bonos del Estado italianos para minoristas (BTP Valore, BTP Più, BTP Italia)

Estos bonos se emiten con un ISIN y se negocian con otro:

| Fase | Código | Para qué sirve |
|---|---|---|
| Suscripción en la emisión | el ISIN «CUM» | Da derecho al **premio de fidelidad** si mantienes el bono hasta el vencimiento. **No negociable**, por lo que ningún proveedor lo cotiza |
| Mercado secundario | un ISIN distinto | Libremente negociable y **cotizado**: es el que tiene precio |

Para vender antes del vencimiento el bono se convierte al código de mercado. En LibreFolio ambos
son el mismo instrumento, así que:

1. Pon el **ISIN de mercado** en el campo **ISIN**.
2. Pon el **ISIN CUM** en **Otros identificadores**.
3. Registra el **premio de fidelidad**, cuando se pague, como una transacción de tipo **Interés**
   sobre ese activo, con la fecha en que lo recibes.

El paso 3 funciona incluso con el bono ya vencido y el activo desactivado: un activo desactivado
sigue siendo seleccionable precisamente para poder registrar el último cupón, la amortización y el
premio.

!!! note "Durante la importación se te pregunta, no se decide por ti"

    Si un archivo del bróker trae el código CUM y el activo ya tiene el de mercado, la importación
    pregunta cuál de los dos debe ser el principal. El que no elijas pasa a **Otros
    identificadores**: no se pierde nada, y la siguiente importación reconoce el bono por
    cualquiera de los dos códigos.

    Cuando el mismo bono aparece en dos archivos con códigos distintos, el paso **Unificar
    activos** del asistente de importación los agrupa en un único instrumento antes de cualquier
    otra decisión.

## 🔗 Relacionado

- 📊 **[Página de Detalles del Activo](detail/index.md)** — Ver y analizar datos del activo
- 🔌 **[Proveedores](providers/index.md)** — Proveedores de precios disponibles
