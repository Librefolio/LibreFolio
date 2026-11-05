# 💸 Transacciones

Las transacciones son cada movimiento de tu cartera: compras, ventas, dividendos, comisiones, transferencias y entradas o salidas de efectivo. LibreFolio calcula tus posiciones, tu rendimiento y tus costes a partir de ellas, así que un registro completo mantiene correctas todas las cifras.

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="list" alt="Lista de transacciones">
</div>

La página **Transacciones** enumera las transacciones de todos los brókeres a los que tienes acceso, de la más reciente a la más antigua. Cada bróker también muestra las suyas en su [pestaña Transacciones](../brokers/import.md).

---

## 🔎 Buscar y abrir una transacción

- **Ordenar** — haz clic en la cabecera de una columna.
- **Filtrar** — abre el filtro de una columna (fecha, tipo, activo, bróker, etiquetas, descripción…). En el filtro de fecha, escribe una fecha solo en **Desde** para ver las transacciones desde ese día en adelante, o solo en **Hasta** para las anteriores hasta ese día; los dos extremos de un rango deben ser días distintos. Tus filtros se guardan en la dirección de la página, así que un marcador reabre la misma vista.
- **Abrir** — haz doble clic en una fila para verla en modo de solo lectura; el lápiz cambia al modo de edición.
- **Precio unitario** — una columna junto al importe muestra el precio por unidad que implica una operación (el importe dividido entre la cantidad, según la base de cotización del activo); es de solo lectura y está vacía en una fila sin cantidad ni importe, y en las partes de un par vinculado. Ocúltala desde el menú de columnas si no la necesitas. El editor masivo tiene la misma columna.

Sin filtros ni ordenación, las dos filas de un par vinculado (una transferencia o un cambio de divisas) permanecen juntas, y el icono de enlace salta a la fila asociada.

---

## ➕ Añadir o importar transacciones

- **Añadir transacción** abre el [espacio de trabajo masivo](#bulk-workspace) en un formulario **Nueva transacción**: rellénalo ([Formulario de transacción](form.md)), haz clic en **Aplicar** y luego en **Guardar todo**.
- **Importar** abre el espacio de trabajo con el **Asistente de importación**, que lee los archivos exportados por tu bróker — consulta [Importar desde el bróker](import/index.md).

---

## ✏️ Editar, clonar o eliminar transacciones

- **Una fila** — haz clic derecho en ella o usa sus acciones de fila: **Ver**, **Editar**, **Clonar**, **Separar par** o **Eliminar**. Solo ves las acciones que permite tu rol en ese bróker.
- **Varias filas** — márcalas y elige **Editar**, **Clonar** o **Eliminar** en la barra de selección. **Editar** y **Eliminar** omiten las filas de los brókeres en los que solo eres lector.

Cada una de estas acciones abre el espacio de trabajo masivo, y nada cambia antes de **Guardar todo**. Editar o eliminar un lado de un par vinculado arrastra consigo a su pareja.

**Clonar** conserva la fecha original: así es como vuelves a registrar una fila histórica, por ejemplo con otro tipo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="transactions" data-name="clone-flow" alt="Espacio de trabajo masivo con una fila de transacción clonada">
</div>

---

## 🔗 Vincular o desvincular un par {: #link-pairs }

Algunas operaciones son dos transacciones vinculadas — consulta [Transacciones emparejadas](form.md#composite-transactions).

- **Vincular** — marca dos filas sueltas que vayan juntas y haz clic en **🔗 Promover par**. Dos **ajustes** se convierten en una **transferencia de activos**; un **retiro** y un **depósito** se convierten en un **cambio de divisas** (mismo bróker, dos divisas) o en una **transferencia de fondos** (dos brókeres, misma divisa e importe). Si las filas tienen descripciones distintas o etiquetas distintas, eliges qué conservar; cada fila mantiene su propia fecha. Una descripción admite como máximo 500 caracteres: el diálogo los cuenta y mantiene **Confirmar promoción** desactivado hasta que la descripción se ajuste al límite.
- **Desvincular** — **Separar par** en una fila vinculada la convierte de nuevo en dos filas sueltas. Una **transferencia de activos** se convierte en dos **ajustes**: el ajuste receptor conserva su coste y el ajuste emisor saca las unidades sin valor: en su bróker solo se descuenta la cantidad, y su coste se contabiliza como una pérdida realizada (consulta [Ajustes salientes](../../financial-theory/instruments/transaction-types/adjustment.md#outgoing-adjustments)).

Ambas piden confirmación y luego guardan al instante, sin el espacio de trabajo.

---

## 🔁 Revincular eventos {: #relink-events }

Un dividendo, un pago de intereses o un ajuste pueden vincularse al **evento** del activo (el dividendo que anunció el proveedor, un desdoblamiento…). El vínculo se pierde cuando [cambiar la divisa de un activo](../assets/create-edit.md#changing-the-currency) elimina los eventos a los que apuntaba, y un dividendo que registraste antes de descargar su evento nunca tuvo uno. **Revincular eventos**, en la barra de herramientas situada sobre la tabla, encuentra esas transacciones y propone el evento que se debe vincular.

La ventana lista tus **dividendos, intereses y ajustes** que tienen un activo pero ningún evento, en los brókeres donde eres al menos editor, de los más recientes a los más antiguos. Cada fila muestra el activo, la fecha, el tipo y lo que se encontró:

| Lo que ves | Significado | Qué puedes hacer |
|--------------|---------|-----------------|
| **Un evento ese día** | Exactamente un evento del mismo activo, el mismo día y del tipo correspondiente | **Vincular** la fila |
| **Ningún evento ese día** | El activo no tiene ese evento ese día | Nada aquí: añade el evento o vincula otro en la transacción |
| **N eventos ese día** | Más de un candidato | Nada aquí: LibreFolio nunca adivina. Elige el correcto en la transacción |

**Vincular todas las filas con un evento** vincula de una vez todas las filas del primer tipo, en un único guardado: si alguna se rechaza, no se vincula ninguna. No se vincula nada a menos que hagas clic.

!!! info "El evento debe tener la misma fecha"

    Un candidato solo se propone si es **del mismo día** que la transacción. También debe ser el mismo activo y del tipo correspondiente: un dividendo con un dividendo, un pago de intereses con un evento de intereses, un ajuste con un ajuste de precio o un desdoblamiento.

    Por ejemplo, registraste un dividendo el **12 de marzo**. Se propone un evento del mismo activo con fecha **12 de marzo**. Un evento con fecha **10 de marzo** **no** se propone, aunque sea el único cercano: la fila muestra *Ningún evento ese día*.

    Esto es lo que ocurre cuando tu bróker abonó el dividendo unos días después del evento. Abre la transacción y elige tú mismo el evento en **Evento vinculado** ([Formulario de transacción](form.md)).

---

## 🧰 El espacio de trabajo masivo {: #bulk-workspace }

El espacio de trabajo es una cuadrícula de filas en borrador — marcadas como **nueva**, **editar** o **eliminar** — donde preparas los cambios antes de escribirlos:

- **Añadir fila**, **Importar** y **Restablecer todo** están encima de la cuadrícula. Al marcar filas aparecen **Restablecer seleccionadas**, **Eliminar seleccionadas** y, para un par que coincida, **🔗 Promover par**.
- Las filas se comprueban mientras trabajas: los problemas aparecen arriba, bajo *Se encontraron errores de validación*, y un clic te lleva a la fila. Con muchas filas, la comprobación automática se pausa: pulsa **⚡ Validar ahora** antes de guardar.
- Cuando dos filas parecen las dos mitades de una misma transferencia o cambio, un banner verde ofrece **Fusionar** para fusionarlas — dos filas nuevas, dos ya guardadas o una de cada. Cuando propone más de un par, **Fusionar todos (N)** los fusiona de una vez. Si las dos filas de un par tienen descripciones distintas o etiquetas distintas, una misma elección se aplica a todos los pares: **Todo a la izquierda** conserva la descripción y las etiquetas de la primera fila, tal como las lista el banner; **Todo a la derecha**, las de la segunda fila; **Combinar**, la opción por defecto, conserva ambas descripciones y las etiquetas de las dos filas. Una descripción admite como máximo 500 caracteres, como en cualquier transacción: con **Combinar**, un par cuyas dos descripciones juntas superarían ese límite no se fusiona, y un mensaje indica cuántos pares quedaron sin fusionar — fusiónalos de uno en uno con **Fusionar**, donde puedes acortar la descripción.
- Cuando la otra mitad ya está guardada pero no está en el espacio de trabajo — por ejemplo, una transferencia cuyo primer lado importaste el mes pasado —, el botón 💡, encima de la cuadrícula y en el menú de la fila, ofrece añadirla: una vez dentro, el banner ofrece el par.
- **Guardar todo** escribe todo de una vez. Si hay sugerencias de fusión que no has revisado — el 💡 que nunca abriste, el banner verde en el que nunca hiciste clic —, pregunta primero (*Sugerencias que no has revisado*): **Mostrar las sugerencias** abre la lista del 💡 o trae el banner a la vista; **Guardar de todos modos** continúa. Una vez que has revisado, no vuelve a preguntar hasta que cierres el espacio de trabajo. **Cancelar** cierra el espacio de trabajo, preguntando antes si tienes cambios sin guardar.

??? warning "🚦 Banners tras una importación — cuándo aparecen"

    Tras una importación, los banners encima de la cuadrícula listan lo que hay que revisar antes de **Guardar todo**:

    - **rojo** — filas que el importador no entendió del todo: **Guardar todo** permanece desactivado hasta que las completes;
    - **ámbar** — campos derivados automáticamente que hay que verificar: **Guardar todo** te pide primero **Revisar** o **Guardar de todos modos**;
    - **ámbar, fechas** — filas con fecha anterior al 1 de enero de 1900, listadas una a una (haz clic en una línea para ir a la fila): **Guardar todo** pregunta una vez por todas ellas (*Sí, las fechas son correctas*). Una fecha tan antigua suele ser un error tipográfico; una vez confirmada, se guarda como cualquier otra.
    - **ámbar** — filas que pueden ser desdoblamientos de acciones (importaciones de Revolut y Trading212): vincula un evento de desdoblamiento a cada una, o créalo desde el banner; consulta [Revolut](import/revolut.md#stock-splits).

    Haz clic en un banner para desplegar su lista y luego en una entrada: la cuadrícula pasa a la página de esa fila y la resalta. Los problemas de saldo listan las filas que los causan (*Filas del espacio de trabajo: …*), y un clic abre la primera en el orden de clasificación actual. Si tus filtros de columna ocultan la fila, un mensaje te lo indica.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="transactions" data-name="bulk-todo-banner" alt="Espacio de trabajo masivo con el banner de campos a verificar desplegado y la fila de la entrada seleccionada resaltada en la cuadrícula">
</div>

Después de un guardado, de **Promover par** o de **Separar par**, la página Transacciones borra su selección, ya que esas filas pueden haber cambiado; cerrar o cancelar la mantiene. Si se rechaza **Promover par** o **Separar par**, nada cambia: un mensaje de error explica por qué y la confirmación permanece abierta.

---

## 🧭 Guías contextuales

La página Transacciones, el formulario **Añadir transacción**, el espacio de trabajo masivo y el [Asistente de importación](import/how-to.md#guided-first-import) tienen cada uno una guía breve. Una guía solo se inicia cuando su pantalla está lista y nunca edita un borrador ni pulsa un botón por ti; en el espacio de trabajo muestra un aviso a la vez, que se cierra con **Entendido**.

Puedes repetir cualquier guía desde [Configuración → Preferencias → Introducción y guías](../settings/preferences.md#onboarding-and-guides).

---

## 🔗 Relacionado

* 📝 **[Formulario de transacción](form.md)** — campos y tipos de transacción
* 📥 **[Importar desde el bróker](import/index.md)** — el flujo de importación BRIM
* 📖 **[Tipos de transacción](../../financial-theory/instruments/transaction-types/index.md)** — la teoría financiera detrás de cada tipo
