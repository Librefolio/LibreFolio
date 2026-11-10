# 📥 <img src="https://danskebank.fi/favicon.ico" alt=""> Danske Bank

!!! info "Alfa"

    Este importador está en fase **Alfa**: se creó a partir de las exportaciones de una única cuenta, compartidas en la [incidencia #26](https://github.com/Librefolio/LibreFolio/issues/26). Si tus archivos son distintos o una fila se importa de una forma que parece incorrecta, abre una nueva incidencia y menciona la #26.

LibreFolio importa la **cuenta de ahorro para acciones** (*osakesäästötili*) de **Danske Bank Finlandia**. El banco la divide en **dos exportaciones**, y ninguna basta por sí sola:

- los **movimientos de valores** (XLSX): operaciones, dividendos y escisiones, con cantidades y precios, pero sin depósitos, retiros ni saldo;
- el **extracto de la cuenta de efectivo** (CSV): todos los movimientos de efectivo y el saldo, pero sin cantidades.

Por eso los subes **juntos**: LibreFolio los lee como un único **conjunto de informes**, empareja cada operación con su pago y comprueba sus saldos con los del banco.

---

## 📤 Qué exportar {: #what-to-export }

| Exportación (nombre en LibreFolio) | Dónde encontrarlo en eBanking | Formato | Hasta dónde se remonta |
|:--|:--|:--|:--|
| **Movimientos de valores** (`Transactions.xlsx`) | **Sijoitukset → Tapahtumat** | XLSX | como máximo **un año** por exportación |
| **Extracto de la cuenta de efectivo** | las transacciones de la cuenta de efectivo de tu cuenta de ahorro para acciones | CSV | hasta **cinco años** |

- Movimientos de valores: **todo el año** que permite el banco.
- Extracto de la cuenta de efectivo: el mismo período, desde el día anterior a este y, idealmente, **unos días después** de su final; las operaciones se pagan unos días hábiles después de realizarse.
- Importa los archivos **tal como se descargaron**, sin volver a guardarlos en Excel.

---

## 🧺 Sube ambos archivos juntos

1. Abre el **[Asistente de importación](how-to.md)**, arrastra **ambos** archivos a **Subir**, asígnalos a tu bróker Danske Bank y haz clic en **Siguiente: Seleccionar archivos**.
2. En **Seleccionar archivos**, los dos archivos forman **una tarjeta**, ya marcada: comprueba que diga **Completo**. Una nota en la tarjeta te indica qué hará esta importación.
3. Haz clic en **Analizar**: LibreFolio combina los dos archivos en un **archivo combinado** y lo analiza como una sola fila. Su detalle, **Emparejamiento de valores ↔ efectivo**, muestra cómo se emparejaron las operaciones con sus pagos y por qué se dejó fuera alguna fila.
4. Continúa como de costumbre hasta **Importar N transacciones**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-card" alt="Tarjeta del conjunto de informes de Danske Bank en Seleccionar archivos: una tabla por tipo de exportación, la cronología de los archivos y Leer como en su encabezado" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-pairing" alt="Detalle de Analizar del conjunto: Emparejamiento de valores ↔ efectivo, con las etiquetas de resultado y los motivos con su número de filas" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Los archivos subidos juntos desde la página [Archivos](../../files/index.md#broker-reports) o desde el formulario **Informes subidos** de un bróker también forman un conjunto.

Las exportaciones subidas con una versión de LibreFolio anterior a la 1.2 no pertenecen a ningún conjunto y no se pueden leer por sí solas: el asistente mantiene **Analizar** deshabilitado mientras uno de esos archivos esté seleccionado. Sube de nuevo todas las exportaciones del conjunto juntas, de una vez, y luego selecciona ese conjunto; las copias antiguas se pueden eliminar.

### 🧩 Si falta un archivo

- ¿Solo has arrastrado un archivo? **Siguiente: Seleccionar archivos** te mantiene en **Subir**, indicando la exportación que falta y su período: arrástralo allí —se une al **mismo conjunto**— y vuelve a hacer clic en **Siguiente: Seleccionar archivos**.
- ¿Quieres continuar sin él? La tarjeta muestra **Falta un archivo** y ofrece **Subir el archivo que falta**. Mientras tanto, el conjunto marcado bloquea **Analizar**: desmárcalo para importar primero tus otros archivos.
- Los archivos subidos en momentos distintos **nunca se unen**: vuelve a subir el que falta con **Subir el archivo que falta** en la tarjeta correcta y luego elimina la copia anterior y solitaria.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-missing" alt="Tarjeta del conjunto en Seleccionar archivos que muestra Falta un archivo: el extracto de la cuenta de efectivo que falta, el período que debe cubrir y Subir el archivo que falta" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🔀 Cómo se lee el conjunto {: #how-the-set-is-read }

Normalmente no hay nada que cambiar: **Leer como**, en el encabezado de la tarjeta, muestra **Danske Bank (detectado)**. Si un archivo no pertenece al conjunto —por ejemplo, un extracto de otra cuenta subido por error—, elige **Quitar del conjunto** en su menú **⋮**: el archivo pasa, sin un plugin, a **Otros archivos de este bróker**, donde lo desmarcas. Para volver a ponerlo, elige *Danske Bank* en su columna **Plugin** de allí (la opción aparece una vez que el archivo está marcado).

**Leer los archivos uno a uno** no sirve aquí, ya que ningún otro importador lee estas exportaciones: si lo elegiste, vuelve a poner cada archivo de la misma forma. Un conjunto marcado solo en parte —su casilla muestra un guion— bloquea **Analizar**: haz clic una vez en la casilla para desmarcar el conjunto y dos veces para marcarlo entero.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-read-as" alt="Tarjeta del conjunto con la lista Leer como abierta: Danske Bank (detectado), seleccionado, y Leer los archivos uno a uno" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-file-menu" alt="Tarjeta del conjunto de Danske Bank en Seleccionar archivos con el menú ⋮ del extracto de la cuenta de efectivo abierto: Vista previa, Quitar del conjunto y Eliminar" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🗓️ Importa al menos una vez al año

La exportación de valores solo se remonta un año, así que importa **al menos una vez al año**, y que cada nueva exportación de valores llegue hasta donde terminó la anterior. Los solapamientos no son problema: lo que LibreFolio ya tiene se oculta en la **Revisión** (*N ya en LibreFolio (ocultos)*) o llega desmarcado como [duplicado](index.md#duplicate-detection). ¿Te has saltado más de un año? Consulta [Huecos](#gaps).

!!! warning "Conjuntos importados con LibreFolio 1.2"

    LibreFolio 1.2 registraba cada operación el día en que se movía el dinero; ahora la registra el día en que la hiciste, unos días antes. Si se importaran de nuevo, esas operaciones no se reconocerían como duplicadas y contarían dos veces. Así que, una vez: elimina todas las transacciones de Danske Bank que crearon esas importaciones —también las correcciones etiquetadas `gap_fix`— y vuelve a importar todo el conjunto, o importa solo desde el día siguiente al último día que ya importaste: inicia la exportación de valores en esa fecha y el extracto de la cuenta de efectivo el día anterior, como dice [Qué exportar](#what-to-export). A partir de entonces, los solapamientos vuelven a estar bien.

---

## 📝 Qué se importa

| En tus archivos | Se importa como |
|:--|:--|
| Una compra (`Määrä` positivo) y su pago `Osto …` | **Compra** |
| Una venta (`Määrä` negativo) y su pago `Myynti …` | **Venta** |
| `Tuotto` y su abono | **Dividendo** |
| `Nosto osakesäästötililtä` | **Retiro** |
| `Vero osakesäästötililtä` | **Impuesto** |
| `Palvelumaksu…` (comisiones de servicio) | **Comisión** |
| `Korko…` (intereses) | **Interés** |
| Cualquier otro abono (solo se puede depositar tu propio dinero) | **Depósito** — un aviso los enumera |
| `Jakautuminen, vanha` / `uusi` (una escisión) | **Ajustes** sin efectivo — consulta [Escisiones](#demergers) |

- Cada operación se registra el **día en que la hiciste** (`Kauppapäivä`, la fecha de la operación): una compra hecha el día 27 es una compra del día 27, aunque el banco mueva el dinero unos días hábiles después. Los dividendos y las escisiones también toman su día de la exportación de valores; los depósitos, retiros, impuestos, comisiones e intereses conservan su fecha en el extracto de la cuenta de efectivo. Los importes están en **euros**, tal como los escribió el banco.
- Los archivos no indican ISIN ni ticker: confirma cada valor en la [asignación de activos](index.md#asset-mapping) del asistente.
- **Todas las filas están contabilizadas**: una fila omitida —un pago que falta, una operación pagada después de que termine el extracto de la cuenta de efectivo…— sigue contando en el detalle del conjunto, con su motivo, y aparece en los avisos del importador, en **finés**, igual que los archivos. Hay dos casos que se tratan de forma distinta:
    - **Reservas** (`Varaus` en el extracto de la cuenta de efectivo) son retenciones que el banco sustituye por el movimiento contabilizado, y ese movimiento es el que se importa. Se cuentan en el detalle del conjunto como *reservado, no contabilizado*, pero no se enumeran en los avisos: no hay nada que comprobar.
    - **Un estado que LibreFolio no conoce**: una fila cuyo `Tila` sea distinto de ejecutada (`Toteutettu`) o contabilizada (`Toteutunut`) —por ejemplo, una orden no ejecutada— se omite con una **advertencia** y un enlace para **abrir una incidencia en GitHub**. Abre una, indicando el `Tila` que ves, para que el importador aprenda a gestionarlo. Mientras tanto, si una de esas filas es un movimiento real, añádela a mano.
- Revisa las operaciones emparejadas que un aviso señale porque sus nombres difieren.

### 💶 Las comisiones están incluidas en los importes de las operaciones

Los archivos dan **un total por operación**, comisión incluida, así que el paso **Correcciones** pregunta, para cada compra y cada venta:

- **¿Separar el precio de los cargos?**, y luego **Aplicar corrección** —para un valor cotizado en euros, LibreFolio sugiere la comisión probable; la cifra exacta está en la confirmación de la operación en eBanking;
- o **Mantener tal como se registró**: la operación conserva su importe completo (tu efectivo queda bien de cualquiera de las dos formas).

Cada operación necesita una elección; **Mantener las N filas restantes tal como se leyeron** resuelve el resto con un clic.

### ✂️ Escisiones {: #demergers }

Una escisión (`Jakautuminen`) llega como **ajustes sin efectivo**: la línea antigua (`vanha`) elimina tus acciones antiguas y cada línea nueva (`uusi`) añade otras nuevas. En el editor, cada línea nueva necesita su **coste por acción** (**Guardar todo** espera a que lo introduzcas): el coste de tus acciones antiguas × el porcentaje de la línea publicado por la Administración Tributaria finlandesa ([vero.fi](https://www.vero.fi/)), dividido entre su número de acciones.

---

## 🏁 Primera importación: alinear con el banco {: #first-import-align-with-the-bank }

En la primera importación, todo lo anterior al primer día de tu exportación de valores se resume en un **punto de partida** al final del día anterior; a partir de ahí, cada movimiento se importa uno a uno. La tarjeta del conjunto te indica la fecha.

Tras la **Revisión**, **Importar N transacciones** puede abrir **Alinear con el banco**: compara lo que tendrá LibreFolio con lo que declara el banco y propone lo que cierra la diferencia: un **Depósito** o un **Retiro** que lleva el efectivo al saldo del extracto de la cuenta de efectivo, y un **Ajuste** por cada posición que demuestren tus archivos.

LibreFolio registra una operación el día en que la hiciste, mientras que el saldo del banco cambia solo cuando la operación se paga, unos días hábiles después. Por eso, cada comparación cuenta las operaciones importadas ya realizadas pero aún no pagadas en ese día, y ambos lados hablan de lo mismo.

1. Las tarjetas de la parte superior muestran cada punto: el **Punto de partida**, un punto **Después del hueco** por cada [hueco](#gaps), la [Comprobación de fin de período](#end-of-period-check). Haz clic en una para ver su comparación y solo sus correcciones; vuelve a hacer clic para verlas todas.
2. Las correcciones, etiquetadas `gap_fix`, están **seleccionadas por defecto**: desmarca las que no quieras (o usa **Seleccionar todo**, **Seleccionar visibles**, **Deseleccionar todo**) y luego haz clic en **Continuar**.
3. En el editor, introduce el **coste por acción** de cada posición marcada como *coste a introducir*: la web del banco muestra el precio medio de compra de cada posición. **Guardar todo** espera a que lo hagas.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-gapfix-step" alt="Alinear con el banco: las tarjetas Punto de partida, Después del hueco y Comprobación de fin de período encima de las correcciones propuestas etiquetadas gap_fix" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

El paso se abre **solo cuando hay algo que mostrar**; normalmente no ocurre tras una importación anual que se solapa con la anterior. El historial que introdujiste a mano cuenta: solo se propone la diferencia. Si la comparación con el banco falla, puedes **Continuar** sin correcciones.

### 📅 Si tu extracto de la cuenta de efectivo empieza más tarde {: #cash-statement-starts-later }

Si tu extracto de la cuenta de efectivo empieza **después** del primer día de tu exportación de valores, el punto de partida sigue cayendo en el día anterior a la exportación de valores y toma el saldo con el que empieza tu extracto de la cuenta de efectivo.

- Una operación que hiciste antes de que empiece el extracto de la cuenta de efectivo y que se pagó dentro de él se importa como de costumbre, el día en que la hiciste.
- Una operación ya pagada antes de que empiece el extracto de la cuenta de efectivo no está en el extracto de la cuenta de efectivo, así que no se puede importar una a una: un aviso la enumera y el detalle del conjunto la cuenta como *liquidada antes de que empiece el extracto de la cuenta de efectivo*. Su dinero ya está en el saldo con el que empieza el extracto de la cuenta de efectivo, por lo que acaba en el punto de partida, unos días antes del día en que la hiciste. Sus acciones también, cuando tus archivos demuestren la posición —un dividendo, por ejemplo—; de lo contrario, comprueba ese valor en la web del banco (consulta [Límites](#limits)).

Para que cada operación se importe en su propio día, exporta el extracto de la cuenta de efectivo desde el día anterior a la exportación de valores, como dice [Qué exportar](#what-to-export).

### ✅ Comprobación de fin de período {: #end-of-period-check }

La última tarjeta compara tu efectivo con el saldo del extracto de la cuenta de efectivo al final del último período de valores, contando, como los demás puntos, las operaciones importadas realizadas pero aún no pagadas ese día: **Coincide** o **No coincide**. **Nunca se corrige**: tu siguiente importación trae las operaciones de los últimos días, que faltan en tu efectivo hasta entonces. Si no coincide, añade a mano el movimiento que la importación omitió (consulta el detalle del conjunto en **Analizar**).

---

## 🕳️ Huecos entre exportaciones de valores {: #gaps }

Un **hueco** es un período que ninguna exportación de valores cubre mientras el extracto de la cuenta de efectivo muestra operaciones en él: te saltaste más de un año o dejaste un hueco entre dos exportaciones de valores. Sin cantidades, esas operaciones no se pueden reconstruir:

- los depósitos, retiros, impuestos, comisiones e intereses del hueco se importan con su propia fecha;
- sus operaciones se resumen en las correcciones **Después del hueco**;
- los valores comprados o vendidos en el hueco deben comprobarse en la web del banco y corregirse a mano.

La tarjeta del conjunto te advierte de ese hueco: si el banco todavía tiene ese período, expórtalo y súbelo con los demás.

---

## ⚠️ Límites {: #limits }

- **Valores que nunca aparecen**: las posiciones solo se demuestran con un dividendo, la línea antigua de una escisión o una venta de más acciones de las que compraste (*al menos N*). Un valor que no se movió y no pagó dividendos no se puede ver: comprueba tus posiciones en la web del banco y añade a mano las que falten.
- **Capital invertido**: una corrección de posición negativa, o la línea antigua de una escisión, elimina acciones sin reducir tu capital invertido.
- **No se puede retroceder en el tiempo**: una exportación de valores anterior al historial que LibreFolio tiene del bróker no se importa; la tarjeta del conjunto lo indica.
- **Correcciones anteriores**: si un nuevo conjunto cubre la fecha de una corrección `gap_fix` importada antes, elimina esa corrección después de la importación, como pide la tarjeta; de lo contrario, el efectivo se cuenta dos veces.

## 🔗 Referencia para desarrolladores

→ [Importador de Danske Bank (referencia para desarrolladores)](../../../developer/backend/brim/danske_bank.md)
