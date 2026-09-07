# 🧙 Cómo importar transacciones

<style>
/* Corrections plugin table: plugin column keeps icon+name on one line */
.md-typeset details.warning table th:first-child,
.md-typeset details.warning table td:first-child { min-width: 9rem; white-space: nowrap; }
.md-typeset details.warning .md-typeset__table table td { vertical-align: middle; }
</style>

Aprende a usar el Módulo de Importación de Informes de Bróker (BRIM) para importar tus transacciones paso a paso.

---

## 🚀 Guía paso a paso

1. Exporta un informe de transacciones de tu bróker (normalmente un archivo CSV — consulta el centro de ayuda de tu bróker).
2. En LibreFolio, navega a la página de **[Transacciones](../index.md)**.
3. Haz clic en el botón **Importar** (:material-file-upload:) de la cabecera de la página.
4. Se abre el **Asistente de importación** — puedes arrastrar y soltar tu archivo de extracto en su paso de carga.
5. Revisa la vista previa — comprueba que las fechas, los importes y los nombres de los activos se vean correctos.
6. Haz clic en **Importar N transacciones** — las filas seleccionadas van al **editor masivo** como nuevas filas, donde puedes darles un último vistazo (o seguir editándolas) antes de que **Guardar todo** las confirme en tu cartera.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Quick Import Modal" alt="Quick Import Modal">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Step 1: Upload Report File" alt="Wizard Step 1">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Step 2: Select Files &amp; Parser" alt="Wizard Step 2">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Step 3: Analysis &amp; Parsing" alt="Wizard Step 3">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🗂️ Asset Resolution" alt="Asset Resolution">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Duplicate Detection" alt="Duplicate Detection">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Step 4: Review &amp; Import" alt="Review and Import">
</div>

!!! tip "Creación de bróker y activos sobre la marcha"

       Si el informe importado contiene una cuenta de bróker o activos que aún no están creados en LibreFolio, ¡no necesitas salir del flujo de importación! El asistente te guiará para crear los **[Brókers](../../brokers/index.md)** y **[Activos](../../assets/index.md)** que falten sobre la marcha, con los detalles ya rellenados a partir del extracto.

!!! tip "También puedes usar la sección Archivos"

       La sección **[Archivos](../../files/index.md)** (pestaña BRIM) te permite gestionar de forma centralizada los informes de bróker subidos, reimportarlos o eliminarlos.

---

## 🧙 Pasos del asistente de importación

El asistente tiene **cuatro pasos que ves siempre** y **tres que aparecen solo cuando tus archivos realmente los necesitan**. La barra de progreso muestra únicamente los pasos que corresponden a tu importación, de modo que un informe limpio de un solo archivo se mantiene como un flujo breve, mientras que uno desordenado de varios archivos recibe exactamente las preguntas adicionales que merece — y ninguna más.

| Paso | ¿Se muestra siempre? | Aparece cuando |
| :--- | :--- | :--- |
| 1 · Subir archivo de informe | ✅ Siempre | — |
| 2 · Seleccionar archivos y analizador | ✅ Siempre | — |
| 3 · Análisis y procesamiento | ✅ Siempre | — |
| 🧬 Unificar activos | ⚪ Opcional | El mismo valor se encuentra bajo más de un nombre o código |
| 🔧 Correcciones | ⚪ Opcional | El analizador registró filas que no pudo entender por completo |
| 🧹 Duplicados | ⚪ Opcional | El mismo movimiento aparece en dos de los archivos que importas juntos |
| 4 · Revisión e importación | ✅ Siempre | — |

!!! info "Los pasos opcionales se ejecutan en este orden por una razón"

       Cada uno se basa en las respuestas del anterior. Los valores se unifican **primero**, para
       que cuando más tarde asignes un instrumento a una fila corregida elijas de una lista limpia
       en lugar de entre tres copias del mismo bono. Las correcciones van **antes** de la
       comprobación de duplicados, porque una compra que el analizador solo pudo leer como retiro
       de efectivo se compararía de otro modo contra retiros de efectivo — pasando por alto un
       duplicado real, o inventando uno que no existe.

### 🧙 Paso 1: Subir archivo de informe

Este paso acepta informes CSV o XLSX exportados desde tu bróker. Puedes seleccionar archivos manualmente o arrastrarlos y soltarlos directamente en el asistente. Asigna un bróker a cada archivo, bien archivo por archivo o con el selector global — y si el bróker aún no existe, puedes crearlo sobre la marcha desde aquí.

El paso es **opcional**: los informes subidos en sesiones anteriores ya están guardados y puedes elegirlos en el siguiente paso sin volver a subirlos.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Wizard Step 1: Upload" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### ⚙️ Paso 2: Seleccionar archivos y analizador

Este paso lista los informes guardados para cada bróker, agrupados en paneles plegables por bróker, para que puedas elegir exactamente cuáles procesar — incluidos los archivos subidos en una sesión anterior (los archivos que acabas de subir están preseleccionados). Desde este paso se pueden previsualizar o eliminar informes. Cada archivo recibe su propio analizador: el sistema detecta automáticamente el formato del bróker (p. ej. Degiro, Directa, Interactive Brokers, Intesa Sanpaolo, Crédit Agricole), y puedes cambiar la elección por archivo. Si subes una hoja de cálculo genérica, usa el analizador **CSV genérico** para asignar manualmente tus columnas (fecha, tipo, cantidad, activo, efectivo neto) a los campos de LibreFolio.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Wizard Step 2: Parser Configuration" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🧠 Paso 3: Análisis y procesamiento

El sistema procesa los archivos, validando fechas, números y monedas. Verás una barra de progreso que indica la velocidad y el estado del procesamiento. Una vez completado el análisis, cualquier aviso o error del procesamiento se resumirá antes de continuar.

Los paneles de resumen de la parte superior están **consolidados**: una vez completado el procesamiento, describen lo que realmente se importará — las transacciones seleccionadas y los valores distintos tras la unificación —, no las filas brutas de cada archivo; **Ver todo** abre el detalle agregado. Si vuelves atrás y cambias la elección del analizador, usa **Reprocesar todo** para volver a calcular los resultados.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Wizard Step 3: Analysis" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Al final del procesamiento, la tabla muestra un resumen del procesamiento de cada archivo con las siguientes columnas estadísticas marcadas con emojis:

| Emoji / Columna | Nombre de la métrica | Significado y reglas de cómputo |
| :--- | :--- | :--- |
| `📊` | **Transacciones** | El número total de transacciones financieras leídas e identificadas dentro del archivo. |
| `🏦` | **Activos identificados** | El número de instrumentos financieros (acciones, ETF, etc.) encontrados en las transacciones procesadas. |
| `✗` | **Activos sin resolver** | El número de instrumentos del archivo que no se encontraron en la base de datos de LibreFolio (marcado en rojo si es > 0, lo que requiere asignación en el Paso 4). |
| `🔴` | **Problemas de validación** | Errores formales detectados en los datos (p. ej., formatos no válidos, fechas incorrectas, datos obligatorios ausentes). |
| `🔧` | **Acción requerida (TODOs)** | Campos o atributos que requieren atención (en rojo si bloquean; en naranja para acciones de nivel de aviso/información). No son necesariamente errores: simplemente indican datos que faltan y que no se pueden extraer automáticamente solo del extracto, y que puedes rellenar fácilmente de forma manual en el formulario de edición masiva de transacciones al final del asistente. |
| `⚠️` | **Avisos** | Notificaciones generales o mensajes de advertencia generados por el analizador durante el procesamiento. |

??? abstract "🧬 Unificar activos — aparece cuando el mismo valor se encuentra bajo más de un nombre o código"

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-assets-step" alt="Import wizard — Unify Assets step with a proposed group">
    </div>

    **Cuándo lo verás.** Cuando dos o más de los instrumentos leídos de tus archivos parezcan
    el mismo valor — porque comparten un ISIN, un ticker o un nombre — o cuando tus archivos
    describan un mismo bono bajo dos códigos diferentes. Una importación de un solo archivo en
    la que cada valor sea distinto nunca muestra este paso.

    **Por qué existe.** Cada archivo se lee de forma independiente, por lo que el mismo BTP que
    aparece en un informe de posiciones *y* en un informe de movimientos llega como dos
    instrumentos no relacionados. Si se deja así, se convierte en dos activos duplicados en tu
    biblioteca — y en dos entradas de aspecto idéntico en cada lista posterior, donde la mitad
    de tus filas se adjuntaría silenciosamente a la mitad del instrumento.

    **Qué haces aquí.** El asistente propone una agrupación y tú la confirmas, ajustas o
    rechazas. Cada tarjeta es un valor, y su borde te dice quién decidió:

    | Borde | Significado |
    | :--- | :--- |
    | 🟩 verde sólido | **Unificado** — el motor está seguro (mismo ISIN, ticker o nombre), o así lo has decidido |
    | 🟨 ámbar discontinuo | **Por confirmar** — una similitud sobre la que el motor no actuará por sí solo |
    | ⬜ gris liso | **Por su cuenta** — nada que decidir |

    - **Fusiona o separa** con el menú `⋮` de cada tarjeta, o arrastrando una tarjeta sobre otra.
    - **Elige el código principal** haciendo clic en una de las insignias de color: recibe una ⭐
    y se convierte en el identificador por el que se conocerá el activo. Los códigos que
    pierden se conservan como identificadores alternativos, de modo que nada de lo que tus
    archivos conocían se descarta.
    - **Cambia el nombre** de un grupo con el lápiz. Un grupo que ya coincide con algo de tu
    biblioteca lleva una insignia **en el catálogo**, y gana el nombre de tu biblioteca.
    - **Restaurar agrupación automática**, en la parte superior, deshace todas las fusiones,
    divisiones y elecciones de código de un solo clic si quieres empezar de nuevo.

    !!! tip "Aquí es donde se resuelven los bonos de doble código"

        Los bonos minoristas italianos (BTP Valore, BTP Più, BTP Italia) se suscriben bajo un
        ISIN y se negocian bajo otro. Elige el código **negociable** como principal — es el único
        que un proveedor de precios puede cotizar — y deja el código de suscripción ("CUM") como
        alternativo. Consulta [Crear y editar activos](../../assets/create-edit.md) para conocer
        todos los detalles.

??? warning "🔧 Correcciones — aparece cuando el analizador registró filas que no pudo entender por completo"

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-fix-step" alt="Import wizard — Corrections step with flagged rows">
    </div>

    **Cuándo lo verás.** Cuando tu informe contenga líneas que el plugin registró pero no pudo
    leer por completo: una operación cuyo instrumento o cantidad el archivo simplemente no
    incluye, o una comisión o impuesto que no se pudo asociar a ningún valor. Los informes que
    se procesan sin problemas omiten este paso.

    Este paso existe solo si el plugin del bróker **marca filas para revisión** — un plugin que
    nunca emite estas marcas nunca lo abrirá. Los plugins que actualmente lo hacen:

    | Plugin | Marcas que puede emitir |
    |--------|--------------------|
    | <img src="https://www.credit-agricole.it/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> [Crédit Agricole](credit_agricole.md) | Líneas de operación+comisiones agrupadas (se ofrecen para **dividirlas**), filas de efectivo que no se pudieron vincular a un instrumento, bloqueos relacionados con duplicados |

    A medida que más plugins aprendan a marcar filas, se listarán aquí.

    **Por qué existe.** Una compra que el plugin solo pudo registrar como retiro de efectivo —
    porque el archivo no le proporcionó ni una cantidad ni un instrumento — se compararía contra
    retiros de efectivo en la comprobación de duplicados. Se pasaría por alto un duplicado
    real, o se inventaría uno imaginario. Arreglar estas filas *antes* de la comparación es el
    único momento en que funciona.

    **Qué haces aquí.** Las filas se agrupan por la naturaleza de la cuestión, de modo que
    resuelves casos similares a la vez. Para cada una puedes:

    - **Corregirla** — elige el tipo de transacción correcto y, cuando corresponda, el
    instrumento y la cantidad. Solo se ofrecen los tipos que tienen sentido para esa fila; una
    comisión o impuesto no tiene campo de cantidad y es legítimo que no tenga **ningún
    instrumento** ("cargo del bróker").
    - **Dividirla** — cuando una línea agrupa una operación junto con sus comisiones o impuestos.
    - **Mantenerla tal como se leyó** — estás de acuerdo con lo que hizo el plugin. La fila se
    atenúa y permanece en la lista, así que siempre puedes ver y revisar lo que decidiste.
    - **Restablecer** una sola fila, o todas las filas de un grupo, y empezar de nuevo.

    Un botón **muéstrame la fuente** resalta cada línea original asociada a un aviso en la vista
    previa del archivo, para que puedas comprobar el extracto antes de decidir.

    !!! danger "Filas bloqueantes"

        Las filas marcadas en **rojo** son bloqueantes: la importación no se puede guardar hasta
        que las resuelvas. Las filas ámbar son informativas — puedes dejarlas exactamente como
        están.

??? note "🧹 Duplicados — aparece cuando el mismo movimiento está en dos de los archivos que importas juntos"

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicates-step" alt="Import wizard — Duplicates step with a cross-file pair">
    </div>

    **Cuándo lo verás.** Solo cuando dos o más archivos de esta importación se solapan en el
    tiempo y contienen el mismo movimiento. Los duplicados contra transacciones **ya existentes
    en tu base de datos** *no* abren este paso — simplemente llegan a la revisión final ya
    desmarcados.

    **Por qué existe.** Las exportaciones solapadas son normales: descargas un extracto de todo
    el año y luego uno trimestral que repite parte de él. Desmarcar los gemelos uno a uno es
    tedioso y fácil de hacer mal, así que el asistente los agrupa y te permite decidir una sola
    vez.

    **Qué haces aquí.**

    - **Ordena tus archivos por prioridad.** Arrástralos al orden en que confíes: la copia que se
    conserva para cada grupo se toma del archivo de mayor prioridad.
    - **Recalcula** después de reordenar, para volver a derivar cada elección de la nueva
    prioridad.
    - **Anula individualmente** en la tabla del grupo: cada fila lleva una casilla **Conservar**
    y muestra de qué archivo proviene y si es la copia que se conserva. **Restablecer valores
    predeterminados** restaura las elecciones automáticas.
    - **Compara en paralelo** cuando dos copias difieren y quieres ver exactamente en qué se
    diferencian antes de elegir — el modal de comparación resalta los campos que difieren.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-nway-compare" alt="N-way compare modal with per-field differences highlighted">
    </div>

    Cada grupo se etiqueta como **Total** (los archivos coinciden en todos los detalles — un
    solapamiento puro) o **Parcial** (algo difiere, por lo que merece un vistazo).

### 📦 Paso 4: Revisión e importación

La revisión final muestra cada transacción que se va a importar en una cuadrícula tipo hoja de cálculo, y es donde cada instrumento se empareja por fin con tu biblioteca.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Review and Import grid" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La tabla muestra:

- **Fecha**: La fecha de ejecución.
- **Tipo**: COMPRA, VENTA, DIVIDENDO, DEPÓSITO, etc.
- **Activo**: El activo emparejado de tu biblioteca.
- **Cantidad**: El número de unidades/acciones.
- **Precio**: El precio unitario.
- **Importe neto**: El impacto total en efectivo.
- **Comisiones/Impuestos**: Comisiones e impuestos incluidos.

#### 🗂️ Resolución de activos

Un panel plegable sobre la cuadrícula lista todos los instrumentos encontrados en tus archivos y te permite indicar qué es cada uno en tu biblioteca. Un único campo de búsqueda lo cubre todo, en dos secciones:

- **En esta importación** — los instrumentos leídos de tus archivos, ya unificados por el paso anterior. Aquel que ya está vinculado a tu biblioteca muestra una insignia **en el catálogo** y aparece aquí únicamente, nunca dos veces.
- **En el catálogo** — todo lo demás en tu biblioteca de activos.

Los candidatos con coincidencia automática se fijan en la parte superior del campo de búsqueda con una insignia de confianza (**Exacta** / **Alta** / **Media** / **Baja**), de modo que la coincidencia más probable suele estar a un solo clic.

Si ninguna de las dos secciones tiene lo que necesitas, el botón **Crear «…»** al final de la lista está siempre visible y ya incluye lo que hayas escrito — nunca tienes que ir a buscarlo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Asset resolution panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

El lápiz ✏️ junto a un instrumento emparejado abre el editor completo de activos sin salir del asistente, para que puedas corregir un identificador o un nombre y volver directamente. Cuando un instrumento coincide con **dos** activos ya existentes en tu biblioteca, el asistente detecta la ambigüedad y ofrece una acción de **fusión** para integrar uno en el otro.

!!! question "«¿Cuál es el código principal?»"

       Cuando tu informe incluye un identificador y el activo — o el proveedor de precios — incluye
       otro distinto del mismo tipo, LibreFolio no sobrescribe nada. Pregunta cuál debe liderar,
       mostrando de dónde procede cada valor: **del proveedor**, **ya guardado** o **del informe**.
       El que elijas se convierte en el identificador del activo; los demás se conservan como
       identificadores alternativos, de modo que la próxima importación reconozca el valor en
       cualquier caso.

       El valor del proveedor viene preseleccionado, porque es el único que tiene un feed de precios
       detrás.

#### ⛔ Fecha de apertura del bróker

Si el bróker de destino tiene una fecha de apertura, el asistente marca las filas cuya fecha sea **estrictamente anterior** a ella con el estado `Before opening`. Esas filas se deseleccionan y no se pueden importar; una fila que esté en el día de apertura sigue siendo válida. Si la fecha es incorrecta, un banner por bróker te permite **Editar fecha del bróker** manualmente o **corregirla automáticamente** con la fecha de transacción más antigua encontrada; a continuación, vuelve a comprobar o actualiza para que el asistente reevalúe cada fila con la fecha actualizada.

#### ⚠️ Avisos de activos

Algunos plugins adjuntan avisos informativos a los activos extraídos. Por ejemplo, Intesa Sanpaolo y Crédit Agricole pueden advertir de que un valor puede haber vencido o haber sido amortizado. Estos avisos aparecen como banners ámbar cuando creas o asignas el activo; no bloquean la importación.

#### ⚠️ Duplicados contra tu base de datos

Independientemente del paso opcional **Duplicados** — que compara los archivos importados *entre sí* —, cada fila se compara también con las transacciones ya existentes en tu base de datos, por tipo, fecha, importe, cantidad y descripción. Estas no abren un paso propio: se marcan aquí mismo con una insignia de estado.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Duplicate detection badges" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Insignia de UI | Nivel de confianza | Criterios / Reglas de coincidencia |
| :--- | :--- | :--- |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ PROBABLE</span> | `LIKELY_WITH_ASSET` | Los campos básicos y la descripción coinciden, y el activo se resolvió automáticamente (duplicado con alta confianza). |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ PROBABLE</span> | `LIKELY` | Los campos básicos y la descripción coinciden, pero el activo no está resuelto. |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSIBLE</span> | `POSSIBLE_WITH_ASSET` | Los campos básicos coinciden y el activo se resolvió automáticamente (pero la descripción difiere o está vacía). |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSIBLE</span> | `POSSIBLE` | Los campos básicos (tipo, fecha, cantidad, importe) coinciden, pero el activo no está resuelto. |
| <span style="background-color: rgba(16, 185, 129, 0.15); color: #10b981; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">✅ ÚNICA</span> | — | La transacción no tiene registros coincidentes en la base de datos y se clasifica como nueva (no se ha detectado ningún duplicado). |
| <span style="background-color: rgba(239, 68, 68, 0.15); color: #ef4444; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">❌ SIN RESOLVER</span> | — | El bróker o el instrumento financiero no se emparejó con una entidad existente en la base de datos (requiere resolución en el Paso 4 antes de importar). |

Por defecto, el asistente desmarca automáticamente los duplicados "Probables" para evitar la doble contabilización, pero puedes anular esta elección. Un banner sobre la cuadrícula resume por qué se deseleccionan las filas.

Otras dos insignias provienen de comparaciones *dentro de esta importación*, no contra la base de datos:

| Insignia de UI | Significado |
| :--- | :--- |
| ⧉ **Duplicado en el lote** | Copia exacta de una fila aún pendiente en esta importación (o ya preparada en el editor masivo) — deseleccionada por defecto. |
| ≈ **Posible duplicado en el lote** | Igual, pero la descripción difiere — permanece seleccionada para que decidas. |

Haz clic en **Importar N transacciones** para pasar las filas seleccionadas al **editor masivo** como nuevas filas: todavía no se escribe nada en el libro mayor. Dales un último vistazo — o sigue editándolas — y luego pulsa **Guardar todo** para confirmarlas en tu cartera.
