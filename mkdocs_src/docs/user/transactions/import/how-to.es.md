# 🧙 Cómo importar transacciones

El **Asistente de importación** convierte los informes que descargas de tu bróker en transacciones.
Tú revisas lo que ha leído y resuelves sus dudas; nada se guarda hasta que pulsas **Guardar todo**.

---

## 🚀 Guía paso a paso

1. Exporta un informe de transacciones desde tu bróker: su página en **[Brókeres compatibles](index.md)**
   indica qué archivo.
2. En la página **[Transacciones](../index.md)**, haz clic en **Importar** (:material-file-upload:).
3. Suelta el informe en el asistente, asígnalo a su bróker y sigue los pasos de abajo.
4. Haz clic en **Importar N transacciones**: las filas se abren en el espacio de trabajo masivo, aún sin guardar.
5. Dales un último vistazo y haz clic en **Guardar todo**.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Modal de importación rápida" alt="Modal de importación rápida">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Paso 1: Subir el archivo del informe" alt="Paso 1 del asistente">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Paso 2: Seleccionar archivos y analizador" alt="Paso 2 del asistente">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Paso 3: Análisis y lectura" alt="Paso 3 del asistente">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🗂️ Resolución de activos" alt="Resolución de activos">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Detección de duplicados" alt="Detección de duplicados">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Paso 4: Revisar e importar" alt="Revisar e importar">
</div>

---

## 🧙 Los pasos del asistente de importación

Cuatro pasos están siempre presentes; los demás aparecen solo cuando tus archivos los necesitan, y la
barra de progreso muestra únicamente los pasos de la importación actual.

| Paso | Cuándo lo ves |
| :--- | :--- |
| 1 · **Subir** | Siempre |
| 2 · **Seleccionar** | Siempre |
| 3 · **Analizar** | Siempre |
| 🧬 **Unificar activos** | El mismo valor aparece con más de un nombre o código |
| 🔧 **Correcciones** | El importador registró filas que no pudo entender del todo |
| 🧹 **Duplicados** | El mismo movimiento está en dos de los archivos que importas juntos |
| 4 · **Revisar** | Siempre |
| ⚖️ **Alinear con el banco** | Solo en conjuntos de informes, cuando las cifras del banco difieren de las de LibreFolio |

### 📤 Paso 1: Subir

Arrastra tus informes al asistente, o haz clic para elegirlos (CSV o XLSX), y asigna cada uno a
su bróker — o todos a la vez con **Bróker para subidas**. Un bróker que falte puede crearse
desde la misma lista (**Crear nuevo**).

- Cada informe que subes se conserva: para reutilizar uno, salta este paso con **Siguiente: Seleccionar**.
- Cuando una cuenta llega en varias exportaciones (p. ej. [Danske Bank](danske-bank.md)), súbelas
  juntas: si falta una, el asistente se queda aquí y la nombra.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Paso 1 del asistente: Subir" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### 🧭 Un archivo en el bróker equivocado {: #wrong-broker }

Cuando haces clic en **Siguiente: Seleccionar**, el asistente comprueba cada archivo que acabas de subir
con el **Plugin de importación predeterminado** de su bróker. Si ese plugin no puede leer un archivo, el archivo probablemente
pertenece a otro bróker, y el asistente te pregunta al respecto antes de continuar (*Este archivo puede pertenecer
a otro bróker*). De arriba abajo, muestra:

- **Asignado a** — el bróker en el que está el archivo, con su icono y su plugin predeterminado, marcado
  *no sabe leerlo*;
- **Notas del plugin** — por qué ese plugin no puede leer el archivo, cuando lo indica: en tu
  idioma cuando existe una traducción;
- **Moverlo a** — el bróker cuyo plugin predeterminado *sabe leerlo*. Cuando los plugins predeterminados de
  varios brókeres pueden leerlo, el aviso lista esos brókeres en su lugar: elige uno, el primero ya está
  seleccionado.

Después elige:

- **Mover**, con el icono del bróker elegido en **Moverlo a** — el archivo se sube a ese bróker, en
  la misma sesión, y se elimina del equivocado. Si el movimiento falla, un error lo indica y el archivo
  permanece donde estaba;
- **Dejarlo aquí** — el archivo se queda, y el asistente lo lee con otro plugin que sí puede, como
  antes: lo ves en la columna **Plugin** de **Seleccionar**;
- **Quitar** — el archivo se borra.

Un aviso por archivo, por turno (*Archivo 1 de 3*); cerrarlo mantiene el archivo. Si eliminas todos los archivos
que acabas de subir, el asistente se queda en **Subir**, listo para otros. Cuando ninguno de tus brókeres
tiene un plugin predeterminado que lea el archivo, el aviso nombra los plugins que sí lo leen — o dice que
ninguno puede — y solo ofrece mantenerlo o eliminarlo.

A los brókeres sin plugin de importación predeterminado nunca se les pregunta, y tampoco a los informes que
reutilizas sin volver a subirlos.

### 🗂️ Paso 2: Seleccionar archivos

El panel de cada bróker lista sus informes almacenados, con los archivos que acabas de subir ya marcados.
Marca los archivos que quieras leer y haz clic en **Analizar (N)**.

El importador de cada archivo se detecta automáticamente: cámbialo en la columna **Plugin** si es incorrecto,
y para un CSV que hayas creado tú mismo elige **[CSV genérico](generic-csv.md)**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Paso 2 del asistente: Configuración del analizador" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Los **conjuntos de informes** son una sola tarjeta, marcada como un todo. **Leído como**, en su encabezado, cambia cómo se
lee el conjunto, y el menú **⋮** de cada archivo puede sacarlo del conjunto (**Leer por separado con ‹plugin›**,
**Quitar del conjunto**) — [detalles](danske-bank.md#how-the-set-is-read).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-read-as" alt="Tarjeta de conjunto de informes en Seleccionar archivos con la lista Leer como abierta: Danske Bank (detectado) y Leer los archivos uno por uno" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-file-menu" alt="El menú ⋮ de un archivo de efectivo en un conjunto de informes: Vista previa, Quitar del conjunto y Eliminar" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**¿Analizar está deshabilitado?** Un archivo marcado no tiene plugin, o un conjunto marcado está incompleto o solo
parcialmente marcado (un guion en su casilla): elige el plugin, usa **Subir el archivo que falta**, o marca o
desmarca todo el conjunto.

### 🧠 Paso 3: Analizar

LibreFolio lee cada archivo, lo comprueba y lo resume en una tabla:

| Columna | Qué cuenta |
| :--- | :--- |
| 📊 | Transacciones leídas |
| 🏦 | Valores encontrados |
| ✗ | Valores aún no emparejados con tus activos — los emparejas en **Revisar** |
| 🔴 | Problemas de validación: filas que no pudieron convertirse en transacciones |
| 🔧 | Campos por rellenar antes de guardar (en rojo cuando uno bloquea el guardado) |
| ⚠️ | Advertencias del importador, como filas omitidas |

Los mosaicos sobre la tabla cuentan lo que realmente se va a importar; **Ver todo** abre los detalles.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Paso 3 del asistente: Análisis" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- **Advertencias**: **Continuar** las lista primero; léelas y después haz clic en **Continuar de todos modos**.
- **Un archivo ha fallado**: un aviso indica por qué. Corrige su plugin en **Seleccionar** y luego haz clic en
  **Reanalizar todos**.

### 🧩 Pasos que aparecen solo cuando hacen falta {: #only-when-needed }

Según lo que encuentre **Analizar**, pueden aparecer hasta tres pasos antes de **Revisar**, en este orden.
Abre el que te muestre el asistente:

??? abstract "🧬 Unificar activos — cuando el mismo valor aparece con más de un nombre o código"

    Tus archivos describen el mismo valor más de una vez — con dos nombres o códigos, o en dos archivos.
    Unifícalo aquí, o se convertirá en dos activos con sus transacciones repartidas entre ellos.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-assets-step" alt="Asistente de importación — paso Unificar activos con un grupo propuesto">
    </div>

    Cada tarjeta es un valor: un borde **verde sólido** significa unificado, **ámbar discontinuo** significa por
    confirmar, **gris** significa nada que decidir.

    - **Confirmar** o **Separar** una propuesta; fusiona o separa tarjetas con **⋮** (**Fusionar con…**,
      **Sacar del grupo**) o arrastrando y soltando.
    - **Haz clic en una insignia de código** para convertirla en el código principal (⭐) — elige el que se usa para cotizar los precios; los
      demás quedan como alternativas.
    - **Renombrar** con el lápiz; un valor que ya está en tu biblioteca (**en archivo**) conserva su nombre.
    - **Continuar** espera hasta que no haya ninguna propuesta abierta: **Confirmar todo (N)** las resuelve de una vez, y
      **Restaurar agrupación automática** empieza de nuevo.

??? warning "🔧 Correcciones — cuando el importador registró filas que no pudo entender del todo"

    El importador registró filas que no pudo entender del todo — hoy, filas de los informes de
    [Crédit Agricole](credit_agricole.md) y [Danske Bank](danske-bank.md).

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-fix-step" alt="Asistente de importación — paso Correcciones con filas marcadas">
    </div>

    Las filas se agrupan por pregunta. Da una respuesta a cada una:

    - **Corregirla**: elige el tipo y, donde corresponda, el valor y la cantidad, y después
      **Aplicar corrección**. Una comisión o un impuesto pueden pertenecer a **Ningún activo (gasto del bróker)**.
    - **Dividirla**: separa el precio de las comisiones, impuestos o intereses acumulados que figuran en tu
      nota de contrato.
    - **Dejar como está**: acepta lo que leyó el importador.

    **Fila N del archivo** muestra la línea original, y **Restaurar** deshace una respuesta. **Continuar** espera
    a que respondas a todas; **Mantener las N filas restantes tal como se leyeron** responde a todas las abiertas.

??? note "🧹 Duplicados — cuando el mismo movimiento está en dos de los archivos que importas juntos"

    El mismo movimiento está en dos de los archivos que importas juntos, como un extracto anual y otro trimestral.
    Las coincidencias con transacciones ya guardadas no abren este paso: **Revisar** las marca.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicates-step" alt="Asistente de importación — paso Duplicados con un par entre archivos">
    </div>

    - **Prioridad de archivos**: arrastra los archivos al orden en que confíes y haz clic en **Recalcular por prioridad**.
      Cada grupo conserva la copia del archivo con mayor prioridad — nunca una ya guardada o esperando en el espacio de trabajo masivo.
    - **Conservar**: marca las copias que quieras importar, fila a fila; **Restablecer valores** restaura la elección automática.
    - **Comparar** muestra las copias lado a lado, con las diferencias resaltadas.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-nway-compare" alt="Modal de comparación N-way con las diferencias campo a campo resaltadas">
    </div>

    Los grupos se listan bajo **Solapamiento total** (copias idénticas) y **Solapamiento parcial** (algo
    difiere).

### 📦 Paso 4: Revisar {: #review }

Todas las filas que vayas a importar en una sola cuadrícula — estado, fecha, tipo, valor, bróker, cantidad, efectivo y etiquetas,
además del archivo cuando importas varios.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Cuadrícula de revisar e importar" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### 🗂️ Empareja cada valor

El panel **Resolver activos** sobre la cuadrícula lista los valores de tus archivos. Empareja cada uno:

- Busca **En esta importación** y **En el archivo** (tu biblioteca) desde un mismo campo. Las coincidencias probables
  aparecen primero, con una insignia de confianza (**Exacta** a **Baja**); una única coincidencia ya está seleccionada.
- **Crear “…”** abre el formulario de nuevo activo, rellenado con el nombre y los códigos del informe.
- ✏️ **Inspeccionar / editar** abre el activo elegido; **Fusionar** aparece cuando dos de tus activos coinciden.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Panel de resolución de activos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Si el código del informe difiere del del activo o del proveedor de precios, LibreFolio pregunta cuál es
el principal. El código del proveedor, el que tiene precios, está preseleccionado; los demás quedan como
alternativas. Una nota ámbar en un activo nuevo, como un posible vencimiento, es solo un consejo.

#### 🚦 Lee las insignias de estado

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Insignias de detección de duplicados" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Insignia | Significado | ¿Marcada inicialmente? |
| :--- | :--- | :--- |
| **✓ Único** | No hay nada similar guardado | ✅ |
| **ℹ Posible dup** | Una transacción guardada tiene el mismo tipo, fecha, cantidad e importe, pero otra descripción | ✅ — revísala |
| **⚠ Probable dup** | Una transacción guardada coincide, descripción incluida | ⬜ |
| **⧉ Duplicado en el lote** | Copia exacta de otra fila de esta importación, o del espacio de trabajo masivo | ⬜ |
| **≈ Posible duplicado del lote** | Lo mismo, con otra descripción | ✅ — revísala |
| **✗ Sin resolver** | Su valor aún no está emparejado | ✅ — emparéjalo o desmárcala |
| **⛔ Anterior a la apertura** | Con fecha anterior a la fecha de apertura del bróker | No se puede importar |
| **⏮ Ya en LibreFolio** | Conjuntos de informes: anterior al historial que conserva LibreFolio; ocultas tras un contador | No se puede importar |

Haz clic en una insignia de duplicado para comparar la fila con su gemela; un aviso explica por qué las filas están desmarcadas. Una
conversión de divisa es una sola fila, importada entera.

#### ⛔ Filas anteriores a la fecha de apertura del bróker {: #opening-date }

Las filas con fecha anterior a la fecha de apertura del bróker no se pueden importar (el propio día de apertura sí vale). Si
la fecha es incorrecta, el aviso ofrece **Establecer apertura en ‹fecha›** — la fecha de la fila más antigua — y
**Editar fecha del bróker**; después se vuelven a comprobar las filas.

#### 📥 Importa las filas

**Importar N transacciones** se habilita cuando al menos una fila está marcada y todas las filas marcadas tienen su
valor. Antes se ejecuta una última comprobación de duplicados: los duplicados que hayan cambiado entre archivos te devuelven a
**Duplicados**, y una selección que haya cambiado te mantiene aquí con un mensaje — revisa las marcas y haz clic
de nuevo.

??? info "⚖️ Alinear con el banco — después de Revisar, solo para un conjunto de informes como Danske Bank"

    Para un conjunto de informes como [Danske Bank](danske-bank.md#first-import-align-with-the-bank), LibreFolio
    compara lo que va a contener con los saldos y posiciones del banco. Las tarjetas muestran cada punto —
    **Punto de partida**, **Después del hueco**, **Comprobación de fin de periodo** — sobre las correcciones propuestas,
    todas marcadas. Desmarca las que no quieras y haz clic en **Continuar**; si la comparación ha fallado, continúa
    sin ellas.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-gapfix-step" alt="Alinear con el banco: las tarjetas Punto de partida, Después del hueco y Comprobación de fin de periodo sobre las correcciones propuestas etiquetadas gap_fix" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

### 💾 Guardar en el espacio de trabajo masivo

Las filas llegan al espacio de trabajo masivo sin guardar. Compruébalas o edítalas y luego haz clic en **Guardar todo**: espera
a las filas listadas en rojo, y pregunta antes de guardar los valores listados en ámbar que no hayas
verificado (**Guardar de todos modos**). Una fila cuya cantidad tiene más de 10 decimales, cuyo importe tiene
más de 6, o cuyo coste base por unidad tiene más de 12, se rechaza en **Guardar todo**, con el máximo en el
mensaje (*Cantidad: Como máximo 10 decimales*): LibreFolio nunca la redondea.
Las fechas de las transacciones van del 1 de enero de 1900 hasta mañana: una fila del informe con
una fecha fuera de ese intervalo también se rechaza en **Guardar todo**, con el intervalo en el mensaje (*Fecha:
Entre 1900-01-01 y 2026-10-18* si hoy es 17 de octubre de 2026).

---

## 🧭 Primera importación guiada {: #guided-first-import }

La primera vez que abres el asistente, un bocadillo guía te acompaña:

- su **Paso N de M** cuenta solo los pasos que ves; los consejos para pasos opcionales esperan a una importación
  que los necesite;
- solo señala: nunca hace clic, sube ni edita por ti;
- termina resaltando **Guardar todo**, sin pulsarlo;
- **X** omite solo el consejo actual.

Para volver a verlo, elige **Repetir en la próxima activación** para la **Guía de importación** en
**[Configuración → Preferencias → Introducción y guías](../../settings/preferences.md#onboarding-and-guides)**:
se inicia con tu próxima importación.

---

## 🔗 Relacionado

- 🏦 **[Brókeres compatibles](index.md)** — qué archivo exportar
- 🛠️ **[Funcionamiento interno del asistente de importación](../../../developer/frontend/components/features/import-wizard.md)** — para desarrolladores
