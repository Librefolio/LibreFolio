# 🧙 Cómo importar transacciones

El **Asistente de importación** convierte los informes que descargas de tu bróker en transacciones. Revisas lo que ha leído y resuelves sus dudas; no se guarda nada hasta que pulses **Guardar todo**.

---

## 🚀 Guía paso a paso

1. Exporta un informe de transacciones de tu bróker: su página en **[Brókers compatibles](index.md)** indica qué archivo usar.
2. En la página **[Transacciones](../index.md)**, haz clic en **Importar** (:material-file-upload:).
3. Arrastra el informe al asistente, asígnalo a su bróker y sigue los pasos que se indican a continuación.
4. Haz clic en **Importar N transacciones**: las filas se abren en el espacio de trabajo masivo, todavía sin guardar.
5. Échales un último vistazo y haz clic en **Guardar todo**.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Modal de importación rápida" alt="Modal de importación rápida">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Paso 1: Subir archivo de informe" alt="Paso 1 del asistente">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Paso 2: Seleccionar archivos y analizador" alt="Paso 2 del asistente">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Paso 3: Análisis y procesamiento" alt="Paso 3 del asistente">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🗂️ Resolución de activos" alt="Resolución de activos">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Detección de duplicados" alt="Detección de duplicados">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Paso 4: Revisar e importar" alt="Revisar e importar">
</div>

---

## 🧙 Los pasos del asistente de importación

Cuatro pasos están siempre presentes; los demás aparecen solo cuando tus archivos los necesitan, y la barra de progreso muestra únicamente los pasos de la importación actual.

| Paso | Cuándo lo ves |
| :--- | :--- |
| 1 · **Subir** | Siempre |
| 2 · **Seleccionar archivos** | Siempre |
| 3 · **Procesar** | Siempre |
| 🧬 **Unificar activos** | El mismo valor aparece con más de un nombre o código |
| 🔧 **Correcciones** | El importador registró filas que no pudo entender por completo |
| 🧹 **Duplicados** | El mismo movimiento está en dos de los archivos que importas juntos |
| 4 · **Revisar** | Siempre |
| ⚖️ **Alinear con el banco** | Solo conjuntos de informes, cuando las cifras del banco difieren de las de LibreFolio |

### 📤 Paso 1: Subir

Arrastra tus informes al asistente, o haz clic para elegirlos (CSV o XLSX), y asigna cada uno a su bróker — o todos a la vez con **Asignar bróker para las cargas**. Un bróker que falte se puede crear desde la misma lista (**Crear nuevo**).

- Todos los informes que subes se conservan: para reutilizar uno, omite este paso con **Siguiente: Seleccionar archivos**.
- Cuando una cuenta llega en varias exportaciones (p. ej., [Danske Bank](danske-bank.md)), súbelas juntas: si falta una, el asistente se queda aquí y la nombra.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Paso 1 del asistente: Subir" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### 🧭 Un archivo en el bróker equivocado {: #wrong-broker }

Cuando haces clic en **Siguiente: Seleccionar archivos**, el asistente comprueba cada archivo que acabas de subir con el **Plugin de importación predeterminado** de su bróker. Si ese plugin no puede leer un archivo, probablemente el archivo pertenezca a otro bróker, y el asistente te pregunta al respecto antes de continuar (*Este archivo puede pertenecer a otro bróker*). De arriba abajo, muestra:

- **Asignado a** — el bróker en el que está el archivo, con su icono, y su plugin predeterminado, marcado como *no puede leerlo*;
- **Notas del plugin** — por qué ese plugin no puede leer el archivo, cuando lo indica: en tu idioma si existe una traducción;
- **Moverlo a** — el bróker cuyo plugin predeterminado *puede leerlo*. Cuando los plugins predeterminados de varios brókers lo leen, el aviso muestra esos brókers en su lugar: elige uno; el primero ya está seleccionado.

Después, elige:

- **Mover**, con el icono del bróker elegido en **Moverlo a** — el archivo se sube a ese bróker, en la misma sesión, y se elimina del incorrecto. Si el movimiento falla, un error lo indica y el archivo permanece donde estaba;
- **Mantenerlo aquí** — el archivo se queda, y el asistente lo lee con otro plugin que sí pueda, como antes: lo ves en la columna **Plugin** de **Seleccionar archivos**;
- **Eliminar** — el archivo se elimina.

Un aviso por archivo, por turno (*Archivo 1 de 3*); cerrarlo mantiene el archivo. Si eliminas todos los archivos que acabas de subir, el asistente se queda en **Subir**, listo para otros. Cuando ninguno de tus brókers tiene un plugin predeterminado que lea el archivo, el aviso nombra los plugins que sí lo leen — o indica que ninguno puede — y solo ofrece mantenerlo o eliminarlo.

Nunca se pregunta por los brókers sin un plugin de importación predeterminado, ni por los informes que reutilizas sin volver a subirlos.

### 🗂️ Paso 2: Seleccionar archivos

El panel de cada bróker enumera sus informes almacenados, con los archivos que acabas de subir ya marcados. Marca los archivos que quieras leer y haz clic en **Procesar (N)**.

El importador de cada archivo se detecta automáticamente: cámbialo en la columna **Plugin** si es incorrecto, y para un CSV que hayas creado tú mismo elige **[CSV genérico](generic-csv.md)**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Paso 2 del asistente: Configuración del analizador" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Los **conjuntos de informes** son una tarjeta, marcada en conjunto. **Leer como**, en su encabezado, cambia cómo se lee el conjunto, y el menú **⋮** de cada archivo puede sacarlo del conjunto (**Leer por separado con ‹plugin›**, **Quitar del conjunto**) — [detalles](danske-bank.md#how-the-set-is-read).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-read-as" alt="Tarjeta de conjunto de informes en Seleccionar archivos con la lista Leer como abierta: Danske Bank (detectado) y Leer los archivos uno por uno" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-file-menu" alt="Menú ⋮ de un archivo de efectivo en un conjunto de informes: Vista previa, Quitar del conjunto y Eliminar" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**¿Procesar está deshabilitado?** Un archivo marcado no tiene plugin, o un conjunto marcado está incompleto o solo parcialmente marcado (un guion en su casilla): elige el plugin, usa **Subir el archivo que falta**, o marca o desmarca el conjunto entero.

### 🧠 Paso 3: Procesar

LibreFolio lee cada archivo, lo comprueba y lo resume en una tabla:

| Columna | Qué cuenta |
| :--- | :--- |
| 📊 | Transacciones leídas |
| 🏦 | Valores encontrados |
| ✗ | Valores aún no emparejados con tus activos — los emparejas en **Revisar** |
| 🔴 | Problemas de validación: filas que no pudieron convertirse en transacciones |
| 🔧 | Campos que rellenar antes de guardar (en rojo cuando uno bloquea el guardado) |
| ⚠️ ℹ️ | Dos números: las advertencias (en ámbar) requieren revisión, como las filas omitidas; las notas (en azul) explican una elección del importador, sin nada que corregir |

Los recuadros debajo de la tabla cuentan lo que se importará realmente; **Ver todo**, o **Ver detalle** en el menú **⋮** de una fila, abre los detalles, con las advertencias y las notas listadas por separado.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Paso 3 del asistente: Análisis" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- **Advertencias y notas**: **Continuar** lista primero las advertencias y luego las notas; léelas y después haz clic en **Continuar de todos modos**. Una advertencia sobre filas que el importador dejó fuera, porque no las conoce o no puede leerlas, incluye un enlace para abrir una incidencia en GitHub.
- **Un archivo ha fallado**: un aviso indica por qué. Corrige su plugin en **Seleccionar archivos** y vuelve a procesar. **Volver a procesar todo** aparece en el análisis solo una vez que se ha leído al menos un archivo; si no se ha leído ninguno, vuelve a **Seleccionar archivos** y haz clic en **Procesar (N)**.

### 🧩 Pasos que aparecen solo cuando se necesitan {: #only-when-needed }

Según lo que encuentre **Procesar**, pueden aparecer hasta tres pasos antes de **Revisar**, en este orden. Abre el que te muestre el asistente:

??? abstract "🧬 Unificar activos — cuando el mismo valor aparece con más de un nombre o código"

    Tus archivos describen el mismo valor más de una vez — con dos nombres o códigos, o en dos archivos. Unifícalo aquí, o se convertirá en dos activos con sus transacciones repartidas entre ellos.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-assets-step" alt="Asistente de importación — Paso Unificar activos con un grupo propuesto">
    </div>

    Cada tarjeta es un valor: un borde **verde sólido** significa unificado, **ámbar discontinuo** significa pendiente de confirmar, **gris** significa que no hay nada que decidir.

    - **Confirmar** o **Dividir** una propuesta; combina o separa tarjetas con **⋮** (**Combinar con…**, **Quitar del grupo**) o arrastrando y soltando.
    - **Haz clic en una insignia de código** para convertirla en el código principal (⭐) — elige el que se usa para cotizar los precios; los demás permanecen como alternativas.
    - **Renombrar** con el lápiz; un valor que ya está en tu biblioteca (**en el archivo**) conserva su nombre.
    - **Continuar** espera hasta que no quede ninguna propuesta abierta: **Confirmar todo (N)** las resuelve a la vez, y **Restaurar agrupación automática** empieza de nuevo.

??? warning "🔧 Correcciones — cuando el importador registró filas que no pudo entender por completo"

    El importador registró filas que no pudo entender por completo — actualmente, filas de informes de [Crédit Agricole](credit_agricole.md) y [Danske Bank](danske-bank.md).

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-fix-step" alt="Asistente de importación — Paso Correcciones con filas marcadas">
    </div>

    Las filas se agrupan por pregunta. Da una respuesta a cada una:

    - **Corregirla**: elige el tipo y, cuando corresponda, el valor y la cantidad, y luego **Aplicar corrección**. Una comisión o impuesto puede pertenecer a **Sin instrumento (cargo del bróker)**.
    - **Dividirla**: separa el precio de las comisiones, impuestos o intereses acumulados que aparecen en tu nota de contrato.
    - **Mantener tal como se registró**: acepta lo que leyó el importador.

    **Fila N en el archivo** muestra la línea original, y **Restaurar** deshace una respuesta. **Continuar** espera todas las respuestas; **Mantener las N filas restantes tal como se leyeron** responde a todas las que siguen abiertas.

??? note "🧹 Duplicados — cuando el mismo movimiento está en dos de los archivos que importas juntos"

    El mismo movimiento está en dos de los archivos que importas juntos, como un extracto anual y uno trimestral. Las coincidencias con transacciones ya guardadas no abren este paso: **Revisar** las señala.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicates-step" alt="Asistente de importación — Paso Duplicados con un par entre archivos">
    </div>

    - **Prioridad de archivos**: arrastra los archivos al orden en que confías y haz clic en **Recalcular por prioridad**. Cada grupo conserva la copia del archivo con mayor prioridad — nunca una ya guardada o pendiente en el espacio de trabajo masivo.
    - **Mantener**: marca las copias que quieres importar, fila por fila; **Restablecer valores predeterminados** restaura la elección automática.
    - **Comparar** muestra las copias una al lado de la otra, con las diferencias resaltadas.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-nway-compare" alt="Modal de comparación de N vías con las diferencias por campo resaltadas">
    </div>

    Los grupos se enumeran en **Solapamiento total** (copias idénticas) y **Solapamiento parcial** (algo difiere).

### 📦 Paso 4: Revisar {: #review }

Todas las filas por importar en una cuadrícula — estado, fecha, tipo, valor, bróker, cantidad, efectivo y etiquetas, además del archivo cuando importas varios.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Cuadrícula de Revisar e importar" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### 🗂️ Empareja cada valor

El panel **Resolver activos** encima de la cuadrícula enumera los valores de tus archivos. Empareja cada uno:

- Busca **En esta importación** y **En el archivo** (tu biblioteca) desde un solo campo. Las coincidencias probables aparecen primero, con una insignia de confianza (**Exacta** a **Baja**); una única coincidencia ya está seleccionada.
- **Crear “…”** abre el formulario de nuevo activo, rellenado con el nombre y los códigos del informe.
- ✏️ **Inspeccionar / editar** abre el activo elegido; **Combinar** aparece cuando dos de tus activos coinciden.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Panel de resolución de activos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Si el código del informe difiere del código del activo o del proveedor de precios, LibreFolio pregunta cuál es el principal. El código del proveedor, el que tiene precios, está preseleccionado; los demás permanecen como alternativas. Una nota ámbar en un activo nuevo, como un posible vencimiento, es solo un aviso.

#### 🚦 Lee las insignias de estado

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Insignias de detección de duplicados" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Insignia | Significado | ¿Marcada al principio? |
| :--- | :--- | :--- |
| **✓ Única** | No hay nada similar guardado | ✅ |
| **ℹ Posible duplicado** | Una transacción guardada tiene el mismo tipo, fecha, cantidad e importe, pero otra descripción | ✅ — compruébalo |
| **⚠ Probable duplicado** | Una transacción guardada coincide, incluida la descripción | ⬜ |
| **⧉ Duplicado en el lote** | Copia exacta de otra fila de esta importación, o del espacio de trabajo masivo | ⬜ |
| **≈ Posible duplicado en el lote** | Lo mismo, con otra descripción | ✅ — compruébalo |
| **✗ Sin resolver** | Su valor aún no está emparejado | ✅ — emparéjalo o desmárcalo |
| **⛔ Antes de la apertura** | Con fecha anterior a la fecha de apertura del bróker | No se puede importar |
| **⏮ Ya en LibreFolio** | Conjuntos de informes: anterior al historial que conserva LibreFolio; oculto tras un contador | No se puede importar |

Haz clic en una insignia de duplicado para comparar la fila con su gemela; un aviso indica por qué hay filas desmarcadas. Una conversión de divisa es una sola fila, que se importa entera.

#### ⛔ Filas anteriores a la fecha de apertura del bróker {: #opening-date }

Las filas con fecha anterior a la fecha de apertura del bróker no se pueden importar (el día de apertura sí vale). Si la fecha es incorrecta, el aviso ofrece **Establecer apertura en ‹fecha›** — la fecha de la fila más antigua — y **Editar fecha del bróker**; después, las filas se comprueban de nuevo.

#### 📥 Importar las filas

**Importar N transacciones** se habilita cuando al menos una fila está marcada y todas las filas marcadas tienen su valor. Antes se ejecuta una última comprobación de duplicados: los duplicados modificados entre archivos te devuelven a **Duplicados**, y una selección modificada te mantiene aquí con un mensaje — comprueba las marcas y haz clic de nuevo.

??? info "⚖️ Alinear con el banco — después de Revisar, solo para un conjunto de informes como Danske Bank"

    Para un conjunto de informes como [Danske Bank](danske-bank.md#first-import-align-with-the-bank), LibreFolio compara lo que tendrá con los saldos y posiciones del banco. Las tarjetas muestran cada punto — **Punto de partida**, **Después de la brecha**, **Comprobación de fin de periodo** — encima de las correcciones propuestas, todas marcadas. Desmarca las que no quieras y haz clic en **Continuar**; si la comparación ha fallado, continúa sin ellas.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-gapfix-step" alt="Alinear con el banco: las tarjetas Punto de partida, Después de la brecha y Comprobación de fin de periodo encima de las correcciones propuestas etiquetadas gap_fix" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

### 💾 Guardar en el espacio de trabajo masivo

Las filas llegan al espacio de trabajo masivo sin guardar. Compruébalas o edítalas y luego haz clic en **Guardar todo**: espera a las filas listadas en rojo y pregunta antes de guardar los valores listados en ámbar que no hayas verificado (**Guardar de todos modos**). Una fila cuya cantidad tenga más de 10 decimales, cuyo importe en efectivo tenga más de 6, o cuyo coste base por unidad tenga más de 12, se rechaza al pulsar **Guardar todo**, con el máximo en el mensaje (*Cantidad: Como máximo 10 decimales*): LibreFolio nunca redondea ese valor. Las fechas de transacción pueden remontarse hasta el año 1 y llegar hasta mañana. Las filas con fecha anterior a 1900 se marcan en ámbar en la revisión (una nota encima de la tabla las cuenta) y el espacio de trabajo masivo pide que se confirmen una vez, ya que tales fechas suelen ser un error tipográfico; una vez confirmadas, se guardan como cualquier otra. Una fila con fecha posterior a mañana se rechaza al pulsar **Guardar todo**, con el último día permitido en el mensaje (*Fecha: No posterior a 2026-10-18* cuando hoy es 17 de octubre de 2026).

Una fila que incorpora unidades — un **Ajuste** que añade unidades, o el lado receptor de una **Transferencia de activos** — conserva el coste escrito en el informe, incluso 0, en **Manual**. Si el informe no indica ninguno, empieza en **Auto** (💡 en la columna **Anulación del coste base**): **Guardar todo** la guarda con el [coste medio](../form.md#cost-basis) de las unidades que ya posees, a menos que la cambies a **Manual**. Si no hay nada que promediar, la fila se rechaza: elige **Manual** y escribe su coste, 0 para una donación.

Las filas a las que el importador señala un coste faltante son la excepción: una posición añadida por **Alinear con el banco**, una nueva línea de una [escisión](danske-bank.md#demergers) de Danske Bank, una fila `ADJUSTMENT` de un archivo [CSV genérico](generic-csv.md) que añade unidades sin coste. Se listan en rojo, y su formulario se abre en **Manual** con el coste vacío: escríbelo a mano, aunque sea 0 — elegir **Auto** no las quita de la lista.

Cuando llegan las filas, y después de **⚡ Validar ahora** o de un **Guardar todo** rechazado, la cuadrícula pasa a la página de la primera fila cuyo [coste **Auto** fue rechazado](../form.md#cost-basis), y la resalta: la más antigua por fecha, ya que corregirla puede permitir que pasen las filas posteriores del mismo activo en ese bróker. La comprobación automática que se ejecuta mientras editas no hace esto.

---

## 🧭 Primera importación guiada {: #guided-first-import }

La primera vez que abres el asistente, una burbuja de guía te acompaña:

- su **Paso N de M** cuenta solo los pasos que ves; los consejos de los pasos opcionales esperan a una importación que los necesite;
- solo señala: nunca hace clic, sube ni edita por ti;
- termina resaltando **Guardar todo**, sin pulsarlo;
- **X** omite solo el consejo actual.

Para volver a verla, elige **Repetir en el próximo desencadenante** para la **Guía de importación** en **[Configuración → Preferencias → Introducción y guías](../../settings/preferences.md#onboarding-and-guides)**: se inicia con tu próxima importación.

---

## 🔗 Relacionados

- 🏦 **[Brókers compatibles](index.md)** — qué archivo exportar
- 🛠️ **[Funcionamiento interno del asistente de importación](../../../developer/frontend/components/features/import-wizard.md)** — para desarrolladores
