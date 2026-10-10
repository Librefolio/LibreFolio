# 📥 <img src="https://danskebank.fi/favicon.ico" alt=""> Danske Bank

!!! info "Alpha"

    Este importador está en **Alpha**: se creó a partir de las exportaciones de una sola cuenta, compartidas en [la incidencia #26](https://github.com/Librefolio/LibreFolio/issues/26). Si tus archivos se ven diferentes, o una fila se importa de una forma que parece incorrecta, avísanos allí.

LibreFolio importa la **cuenta de ahorro de acciones** (*osakesäästötili*) de **Danske Bank Finlandia**. El banco la divide en **dos exportaciones**, y ninguna es suficiente por sí sola:

- los **movimientos de valores** (XLSX): operaciones, dividendos y escisiones, con cantidades y precios — pero sin depósitos, retiros ni saldo;
- el **extracto de la cuenta de efectivo** (CSV): cada movimiento de efectivo y el saldo — pero sin cantidades.

Así que las subes **juntas**: LibreFolio las lee como un único **conjunto de informes**, empareja cada operación con su pago y comprueba sus saldos contra los del banco.

---

## 📤 Qué exportar

| Exportación (nombre en LibreFolio) | Dónde en eBanking | Formato | Antigüedad máxima |
|:--|:--|:--|:--|
| **Movimientos de valores** (`Transactions.xlsx`) | **Sijoitukset → Tapahtumat** | XLSX | como máximo **un año** por exportación |
| **Extracto de la cuenta de efectivo** | las transacciones de la cuenta de efectivo de tu cuenta de ahorro de acciones | CSV | hasta **cinco años** |

- Movimientos de valores: el **año completo** que permita el banco.
- Extracto de la cuenta de efectivo: el mismo periodo, desde el día anterior a este, y idealmente **unos días después** de su final — las operaciones se pagan unos días hábiles después de realizarse.
- Importa los archivos **tal como se descargan**, sin volver a guardarlos en Excel.

---

## 🧺 Sube ambos archivos juntos

1. Abre el **[Asistente de importación](how-to.md)**, arrastra **ambos** archivos a **Subir**, asígnalos a tu bróker Danske Bank y haz clic en **Siguiente: Seleccionar archivos**.
2. En **Seleccionar archivos**, los dos archivos forman **una tarjeta**, ya marcada: comprueba que diga **Completo**. Una nota en la tarjeta te indica qué hará esta importación.
3. Haz clic en **Analizar**: LibreFolio fusiona los dos archivos en un único **archivo combinado** y lo analiza como una fila. Su detalle, **Emparejamiento de valores ↔ efectivo**, muestra cómo se emparejaron las operaciones con sus pagos y por qué se omitió alguna fila.
4. Continúa como de costumbre hasta **Importar N transacciones**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-card" alt="Tarjeta de conjunto de informes de Danske Bank en Seleccionar archivos: una tabla por tipo de exportación, la línea temporal de los archivos y Leer como en su encabezado" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-pairing" alt="Detalle de análisis del conjunto: Emparejamiento de valores ↔ efectivo, con las etiquetas de resultado y los motivos con su número de filas" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Los archivos subidos juntos desde la página [Archivos](../../files/index.md#broker-reports) o desde **Informes subidos** de un bróker también forman un conjunto.

Las exportaciones subidas con una versión de LibreFolio anterior a la 1.2 no pertenecen a ningún conjunto y no se pueden leer por sí solas: el asistente mantiene **Analizar** deshabilitado mientras una de ellas esté seleccionada. Sube de nuevo todas las exportaciones del conjunto juntas, de una vez, y luego selecciona ese conjunto; las copias antiguas se pueden eliminar.

### 🧩 Si falta un archivo

- ¿Solo has arrastrado un archivo? **Siguiente: Seleccionar archivos** te mantiene en **Subir**, indicando la exportación que falta y su periodo: arrástrala allí — se une al **mismo conjunto** — y haz clic de nuevo en **Siguiente: Seleccionar archivos**.
- ¿Continúas sin él? La tarjeta muestra **Falta un archivo** y ofrece **Subir el archivo que falta**. Mientras tanto, el conjunto marcado bloquea **Analizar**: desmárcalo para importar primero tus otros archivos.
- Los archivos subidos en momentos diferentes **nunca se unen**: sube de nuevo el que falta con **Subir el archivo que falta** en la tarjeta correcta y luego elimina la copia solitaria anterior.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-missing" alt="Tarjeta de conjunto en Seleccionar archivos mostrando Falta un archivo: el extracto de la cuenta de efectivo que falta, el periodo que debe cubrir y Subir el archivo que falta" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🔀 Cómo se lee el conjunto {: #how-the-set-is-read }

Normalmente no hay nada que cambiar: **Leer como**, en el encabezado de la tarjeta, muestra **Danske Bank (detectado)**. Si un archivo no pertenece al conjunto — por ejemplo, un extracto de otra cuenta subido por error —, elige **Quitar del conjunto** en su menú **⋮**: el archivo se mueve, sin plugin, a **Otros archivos de este bróker**, donde lo desmarcas. Para volver a ponerlo, elige *Danske Bank* en su columna **Plugin** allí (la opción aparece una vez que el archivo está marcado).

**Leer los archivos uno a uno** no sirve aquí, ya que ningún otro importador lee estas exportaciones: si lo elegiste, vuelve a poner cada archivo de la misma forma. Un conjunto marcado solo en parte — su casilla muestra un guion — bloquea **Analizar**: haz clic una vez en la casilla para desmarcar el conjunto, dos veces para marcarlo entero.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-read-as" alt="Tarjeta de conjunto con la lista Leer como abierta: Danske Bank (detectado), seleccionado, y Leer los archivos uno a uno" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-file-menu" alt="Tarjeta de conjunto de Danske Bank en Seleccionar archivos con el menú ⋮ del extracto de la cuenta de efectivo abierto: Vista previa, Quitar del conjunto y Eliminar" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🗓️ Importa al menos una vez al año

La exportación de valores solo se remonta un año, así que importa **al menos una vez al año**, y cada nueva exportación de valores debe llegar hasta donde terminó la anterior. Los solapamientos no son problema: lo que LibreFolio ya tiene se oculta en la **Revisión** (*N ya en LibreFolio (oculto)*) o llega desmarcado como [duplicado](index.md#duplicate-detection). ¿Te has saltado más de un año? Consulta [Huecos](#gaps).

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
| `Korko…` (interés) | **Interés** |
| Cualquier otro abono (solo se puede ingresar tu propio dinero) | **Depósito** — un aviso los enumera |
| `Jakautuminen, vanha` / `uusi` (una escisión) | **Ajustes** sin efectivo — consulta [Escisiones](#demergers) |

- Cada transacción recibe su **fecha valor** (el día en que se movió el dinero o las acciones) y su importe en **euros**, tal como lo escribió el banco.
- Los archivos no dan ISIN ni ticker: confirma cada valor en el [mapeo de activos](index.md#asset-mapping) del asistente.
- **Nada se descarta en silencio**: las filas omitidas — un pago que falta, una orden no ejecutada, una operación pagada después de que termina el extracto… — se cuentan en el detalle del conjunto y se listan en los avisos del importador, en **finés** como los archivos. Revisa las operaciones emparejadas que señale un aviso porque sus nombres difieren.

### 💶 Las comisiones están incluidas en los importes de las operaciones

Los archivos dan **un total por operación**, con la comisión incluida, así que el paso **Correcciones** pregunta, para cada compra y venta:

- **¿Separar el precio de los gastos?**, y luego **Aplicar corrección** — para un valor cotizado en euros, LibreFolio sugiere la comisión probable; la cifra exacta está en la confirmación de la operación en eBanking;
- o **Mantener tal como se registró**: la operación conserva su importe completo (tu efectivo queda correcto de cualquier forma).

Cada operación necesita una elección; **Mantener las N filas restantes tal como se leyeron** resuelve el resto con un clic.

### ✂️ Escisiones {: #demergers }

Una escisión (`Jakautuminen`) llega como **ajustes sin efectivo**: la línea antigua (`vanha`) elimina tus acciones antiguas, cada línea nueva (`uusi`) añade nuevas. En el editor, cada línea nueva necesita su **coste por acción** (**Guardar todo** espera a ello): el coste de tus acciones antiguas × el porcentaje de la línea publicado por la Administración Tributaria Finlandesa ([vero.fi](https://www.vero.fi/)), dividido por su número de acciones.

---

## 🏁 Primera importación: alinea con el banco {: #first-import-align-with-the-bank }

En la primera importación, todo lo anterior al primer día de tu exportación de valores se resume en un **punto de partida** al final del día anterior; a partir de ahí, cada movimiento se importa uno a uno. La tarjeta del conjunto te indica la fecha.

Después de la **Revisión**, **Importar N transacciones** puede abrir **Alinear con el banco**: compara lo que LibreFolio tendrá con lo que declara el banco y propone lo que cierra la diferencia — un **Depósito** o un **Retiro** que lleva el efectivo al saldo del extracto de la cuenta de efectivo, y un **Ajuste** por cada posición que demuestren tus archivos.

1. Las tarjetas de la parte superior muestran cada punto — el **Punto de partida**, un punto **Después del hueco** por cada [hueco](#gaps), la [Comprobación de fin de periodo](#end-of-period-check). Haz clic en uno para ver su comparación y solo sus correcciones; haz clic de nuevo para verlas todas.
2. Las correcciones, etiquetadas `gap_fix`, están **seleccionadas por defecto**: desmarca las que no quieras (o usa **Seleccionar todo**, **Seleccionar visibles**, **Deseleccionar todo**) y luego haz clic en **Continuar**.
3. En el editor, introduce el **coste por acción** de cada posición marcada como *coste a introducir* — la web del banco muestra el precio medio de compra de cada posición. **Guardar todo** espera a ello.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-gapfix-step" alt="Alinear con el banco: las tarjetas Punto de partida, Después del hueco y Comprobación de fin de periodo encima de las correcciones propuestas etiquetadas gap_fix" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

El paso se abre **solo cuando hay algo que mostrar** — normalmente no después de una importación anual que se solapa con la anterior. El historial que introdujiste a mano cuenta: solo se propone la diferencia. Si la comparación con el banco falla, puedes **Continuar** sin correcciones.

### ✅ Comprobación de fin de periodo {: #end-of-period-check }

La última tarjeta compara tu efectivo con el saldo del extracto de la cuenta de efectivo al final del último periodo de valores: **Coincide** o **No coincide**. **Nunca se corrige**: tu siguiente importación trae las operaciones de los últimos días, que faltan en tu efectivo hasta entonces. Si no coincide, añade a mano el movimiento que la importación omitió (consulta el detalle del conjunto en **Analizar**).

---

## 🕳️ Huecos entre exportaciones de valores {: #gaps }

Un **hueco** es un periodo que ninguna exportación de valores cubre mientras el extracto de la cuenta de efectivo muestra operaciones en él — te saltaste más de un año o dejaste un hueco entre dos exportaciones de valores. Sin cantidades, esas operaciones no se pueden reconstruir:

- los depósitos, retiros, impuestos, comisiones e intereses del hueco se importan con su propia fecha;
- sus operaciones se resumen en las correcciones **Después del hueco**;
- los valores comprados o vendidos en el hueco deben comprobarse en la web del banco y corregirse a mano.

La tarjeta del conjunto te avisa de ese hueco: si el banco todavía tiene ese periodo, expórtalo y súbelo con los demás.

---

## ⚠️ Límites {: #limits }

- **Valores que nunca aparecen**: las posiciones solo se demuestran por un dividendo, la línea antigua de una escisión, o una venta de más acciones de las que compraste (*al menos N*). Un valor que no se movió y no pagó dividendos no se puede ver: comprueba tus posiciones en la web del banco y añade a mano las que falten.
- **Capital invertido**: una corrección de posición negativa, o la línea antigua de una escisión, elimina acciones sin reducir tu capital invertido.
- **No se puede retroceder en el tiempo**: una exportación de valores anterior al historial que LibreFolio tiene para el bróker no se importa; la tarjeta del conjunto lo indica.
- **Correcciones anteriores**: si un nuevo conjunto cubre la fecha de una corrección `gap_fix` importada antes, elimina esa corrección después de la importación, como pide la tarjeta — o el efectivo se cuenta dos veces.

## 🔗 Referencia para desarrolladores

→ [Importador de Danske Bank (referencia para desarrolladores)](../../../developer/backend/brim/danske_bank.md)
