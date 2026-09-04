# ➕ Crear y Editar Activos

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-create" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="create-modal" data-title="➕ Formulario de creación manual" alt="Modal de creación manual">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="create-wizard-modal" data-title="🧙 Formulario de auto-creación del asistente de importación" alt="Crear activo desde el asistente">
</div>

## 🚀 Flujos de creación de activos {: #asset-creation-flows }

En LibreFolio, puedes crear activos nuevos de dos maneras diferentes:

=== "Creación manual (con búsqueda inteligente)"

 ```mermaid
 flowchart LR
 A[Start: Click '+ New Asset'] --> B[Type Name, ISIN, or Ticker in Smart Search]
 B --> C{Match Found?}
 C -->|Yes| D[Auto-fill details from external providers]
 C -->|No| E[Manually enter name, category, & currency]
 D --> F[Adjust config / Assign pricing provider]
 E --> F
 F --> G[Click Save]
 G --> H[Asset added to library]
 ```

=== "Auto-creación mediante importación de bróker"

 ```mermaid
 flowchart LR
 A[Start: Upload CSV report in Import Wizard] --> B[Parse report rows]
 B --> C{Asset ID recognized?}
 C -->|Yes| D[Auto-match with existing asset]
 C -->|No| E[Flag warning ⚠️ and show 'Create' button]
 E --> F[Click 'Create' to open pre-filled modal]
 F --> G[Save asset to resolve mapping]
 G --> D
 D --> H[Commit all transactions]
 ```

## 🧪 Prueba de la configuración del proveedor

Tras configurar un proveedor, haz clic en **Probar configuración** para verificar que se pueden obtener los datos de precios. La prueba comprueba:

- **Precio actual**: obtiene el último precio
- **Historial**: obtiene los datos históricos de precios (si el proveedor lo admite)

Los resultados se muestran en el propio formulario, junto con los tiempos de ejecución. Una advertencia ⚠️ significa que el proveedor no admite esa operación (p. ej., CSS Scraper no admite historial).

## 🔎 Detalles de la búsqueda inteligente

La búsqueda inteligente consulta primero el buscador propio de cada proveedor. Si un proveedor compatible no encuentra nada,
LibreFolio puede intentar, sin garantías, una búsqueda por enlaces web y resolver las páginas del proveedor para convertirlas
de nuevo en candidatos a activo. Para Borsa Italiana, esto significa que una URL de fondo/detalle puede convertirse en un activo listo para guardar con
los `provider_params` necesarios para valorar el fondo mediante su código interno.

Para los fondos de Borsa Italiana, el ISIN visible identifica el fondo cuando está disponible, pero la valoración utiliza el
código interno del fondo de Borsa guardado en la configuración del proveedor. El NAV actual solo se usa si tiene fecha de hoy;
el historial contiene un punto de NAV en su fecha real.

## 🔌 Asignación de proveedor

A cada activo se le puede asignar un único proveedor de precios. Consulta [Proveedores](providers/index.md) para más detalles sobre los proveedores disponibles y su configuración.

## 🛠️ Edición de un activo {: #editing-an-asset }

Haz clic en el botón **Editar** (✏️) en la [página de detalle](detail/index.md) para abrir el modal del activo con todos los campos ya rellenados. Todos los campos son editables, incluyendo la configuración del proveedor y las distribuciones.

El campo **Otros identificadores** es una lista editable de identificadores alternativos. Las importaciones y los
proveedores pueden añadir ahí etiquetas de bróker, códigos técnicos o identificadores fallback; cada valor se mantiene como
un elemento de lista independiente.

## 🗺️ Distribuciones manuales geográficas y sectoriales

Los proveedores rellenan las distribuciones de **área geográfica** y **sector** cuando pueden — pero muchos
activos (instrumentos personalizados, bonos, inversiones programadas o, sencillamente, activos cuyo proveedor no ofrece
desglose) llegan sin ninguna. Siempre puedes definir o corregir ambas distribuciones manualmente desde el
modal del activo: alimentan los **gráficos de asignación** del panel de control (anillos geográficos y sectoriales, tanto actuales como
a lo largo del tiempo) y el contexto de concentración de AI Export.

En el modal del activo ([crear](#asset-creation-flows) o [editar](#editing-an-asset)) abre
el área **Clasificación**:

1. **Distribución geográfica** — una fila por país o área, con su peso en porcentaje.
2. **Distribución sectorial** — una fila por sector, con su peso en porcentaje.

Para cada distribución puedes:

- **Añadir una fila** — elige el área o el sector en el menú desplegable y escribe el peso.
- **Editar los pesos en línea** — el **total** acumulado se muestra en la parte inferior del editor y se pone
 **verde al llegar exactamente al 100 %** — ámbar cuando falta algo, rojo cuando se supera.
- **Eliminar** una fila con su botón de borrar.

!!! tip "La regla del 100 %"

    El panel de control normaliza las distribuciones parciales, pero un 100 % exacto ofrece los anillos
    de asignación más significativos. Si el instrumento es 100 % de un único país o sector,
    una única fila al 100 % es a la vez válida y la opción más clara.

*(Capturas de pantalla de los dos editores de distribución — `assets/detail-classification` ya existe y muestra el área; está previsto añadir primeros planos específicos de los editores en la próxima actualización de la galería.)*

## 🏷️ Un instrumento, varios códigos

El mismo valor puede ser conocido por más de un código. Cuando eso ocurre, LibreFolio mantiene **un único
activo** y guarda los códigos adicionales en **Otros identificadores**, donde se pueden buscar y se usan
para reconocer el instrumento en importaciones posteriores.

Qué código va en el campo **ISIN** principal no es una cuestión de gustos:

!!! tip "Mantén el código cotizado como ISIN principal"

    Un precio es el valor de la última operación, así que solo un código que pueda negociarse de verdad tiene
    precio. Pon el código negociable en **ISIN** y todo lo demás en **Otros identificadores** —
    de lo contrario, ningún proveedor podrá valorar el activo.

### Bonos del Estado italianos para minoristas (BTP Valore, BTP Più, BTP Italia)

Estos bonos se emiten con un ISIN y se negocian con otro:

| Fase | Código | Qué hace |
|---|---|---|
| Suscripción en la emisión | el ISIN "CUM" | Da derecho a la **prima de fidelidad** si lo mantienes hasta el vencimiento. **No negociable**, por lo que ningún proveedor lo cotiza |
| Mercado secundario | un ISIN distinto | Se negocia libremente y está **cotizado** — este es el que tiene precio |

Para vender antes del vencimiento, el bono se convierte al código de mercado. En LibreFolio ambos son el
mismo instrumento, por lo que:

1. Pon el **ISIN de mercado** en el campo **ISIN**.
2. Pon el **ISIN CUM** en **Otros identificadores**.
3. Registra la **prima de fidelidad**, cuando se pague, como una transacción de **Interés** en ese activo,
 con la fecha del día en que la recibas.

El paso 3 funciona incluso después de que el bono haya vencido y el activo se haya desactivado: un activo
desactivado sigue siendo seleccionable precisamente para que puedan registrarse el último cupón, el reembolso y la prima.

!!! note "Durante una importación se te pregunta, no se te impone"

    Si un archivo de bróker lleva el código CUM y el activo ya tiene el de mercado, la importación
    pregunta cuál de los dos debe prevalecer. El que no elijas se añade a **Otros identificadores** —
    no se descarta nada, y la siguiente importación reconoce el bono por cualquiera de los dos códigos.

    Cuando el mismo bono aparece en dos archivos con códigos distintos, el paso **Unificar activos** del
    asistente de importación los agrupa en un único instrumento antes de que se decida nada más.

## 🧲 Fusión de activos duplicados

Si el mismo instrumento ha terminado dos veces en tu biblioteca — algo habitual cuando se importa un bono
una vez con su código de suscripción y otra con su código de mercado —, puedes integrar uno en el
otro desde la acción **Fusionar**, disponible en la lista de activos y en la página de detalle del activo.

La operación es **destructiva**, por lo que se realiza en dos pasos deliberados:

1. **Elige el activo que se conserva.** El activo desde el que has empezado es el que desaparecerá; tú
 eliges a su superviviente de todo el catálogo, incluidos los activos desactivados — un bono vencido es
 exactamente el tipo de elemento que se fusiona.
2. **Comprueba qué se traslada y define la identidad.** LibreFolio realiza primero una simulación y muestra las
 cifras reales: cuántas transacciones, precios y eventos se reasignarán, y qué ocurre con
 el proveedor de precios. Cuando ambos activos tienen un valor para el mismo identificador, pregunta cuál
 debe prevalecer; el otro se conserva en **Otros identificadores**.

| Qué se traslada | Qué ocurre |
|---|---|
| Transacciones | Se reasignan al activo superviviente |
| Historial de precios | Se reasigna; si ambos activos tienen un precio el mismo día, prevalece el del superviviente |
| Eventos corporativos (dividendos, cupones) | Se reasignan; los eventos idénticos se consolidan, y las transacciones que apuntaban a ellos se reasignan también |
| Asignación de proveedor | Se traslada solo si el superviviente no tiene ninguno — de lo contrario, el superviviente conserva el suyo |
| Identificadores | Se **fusionan**, nunca se descartan: todo lo que conocía el activo eliminado sobrevive como identificador alternativo |

!!! warning "El activo de origen se elimina"

    La fusión no se puede deshacer desde la interfaz. Lee la vista previa antes de confirmar — es un
    recuento exacto, no una estimación.

!!! tip "Puede que se te ofrezca una fusión durante una importación"

    Cuando una importación encuentra **dos** activos que responden al mismo código — la señal clásica de un
    duplicado creado por una importación anterior —, el asistente muestra un aviso discreto con un botón **Fusionar**,
    justo donde puedes verlos a ambos uno al lado del otro. Nunca se ofrecen coincidencias basadas únicamente en el nombre:
    es normal que dos fondos del mismo emisor se parezcan.

## 🔗 Relacionados

- 📊 **[Página de detalle del activo](detail/index.md)** — Consulta y analiza los datos del activo
- 🔌 **[Proveedores](providers/index.md)** — Proveedores de precios disponibles
