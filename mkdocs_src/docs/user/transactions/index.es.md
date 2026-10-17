# 💸 Transacciones

Las transacciones son cada movimiento en tu cartera: compras, ventas, dividendos, comisiones, transferencias y entradas o salidas de efectivo. LibreFolio calcula tus posiciones, rendimiento y costes a partir de ellas, por lo que un registro completo mantiene correctas todas las cifras.

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="list" alt="Lista de transacciones">
</div>

La página **Transacciones** enumera las transacciones de todos los brókeres a los que puedes acceder, de la más reciente a la más antigua. Cada bróker también muestra las suyas en su [pestaña Transacciones](../brokers/import.md).

---

## 🔎 Buscar y abrir una transacción

- **Ordenar** — haz clic en el encabezado de una columna.
- **Filtrar** — abre el filtro de una columna (fecha, tipo, activo, bróker, etiquetas, descripción…). Tus filtros se conservan en la dirección de la página, así que un marcador reabre la misma vista.
- **Abrir** — haz doble clic en una fila para verla en modo de solo lectura; el lápiz cambia a edición.

Sin filtros ni ordenación, las dos filas de un par vinculado (una transferencia o un cambio de divisas) permanecen juntas, y el icono de enlace salta a la fila asociada.

---

## ➕ Añadir o importar transacciones

- **Agregar Transacción** abre el [espacio de trabajo masivo](#bulk-workspace) en un formulario de **Nueva transacción**: rellénalo ([Formulario de transacción](form.md)), haz clic en **Aplicar** y luego en **Guardar todo**.
- **Importar** abre el espacio de trabajo con el **Asistente de importación**, que lee los archivos exportados por tu bróker — consulta [Importar desde el bróker](import/index.md).

---

## ✏️ Editar, clonar o eliminar transacciones

- **Una fila** — haz clic derecho en ella, o usa sus acciones de fila: **Ver**, **Editar**, **Clonar**, **Separar par** o **Eliminar**. Solo ves las acciones que permite tu rol en ese bróker.
- **Varias filas** — márcalas y luego elige **Editar**, **Clonar** o **Eliminar** en la barra de selección. **Editar** y **Eliminar** omiten las filas de brókeres en los que solo eres un Lector.

Cada una de estas acciones abre el espacio de trabajo masivo, y nada cambia antes de **Guardar todo**. Editar o eliminar un lado de un par vinculado arrastra también a su contraparte.

**Clonar** conserva la fecha original: así es como vuelves a registrar una fila histórica, por ejemplo, con otro tipo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="transactions" data-name="clone-flow" alt="Espacio de trabajo masivo con una fila de transacción clonada">
</div>

---

## 🔗 Vincular o desvincular un par {: #link-pairs }

Algunas operaciones son dos transacciones vinculadas — consulta [Transacciones emparejadas](form.md#composite-transactions).

- **Vincular** — marca dos filas individuales que vayan juntas y haz clic en **🔗 Promover par**. Dos **Ajustes** se convierten en una **Transferencia de activos**; un **Retiro** y un **Depósito** se convierten en un **Cambio de divisas** (mismo bróker, dos divisas) o en una **Transferencia de fondos** (dos brókeres, misma divisa e importe). Si las filas no coinciden en fecha, descripción, etiquetas o coste base, tú eliges qué conservar.
- **Desvincular** — **Separar par** en una fila vinculada la convierte de nuevo en dos filas individuales.

Ambas piden confirmación y luego guardan de inmediato, sin el espacio de trabajo.

---

## 🧰 El espacio de trabajo masivo {: #bulk-workspace }

El espacio de trabajo es una cuadrícula de filas en borrador — marcadas como **nueva**, **editar** o **eliminar** — donde preparas los cambios antes de escribirlos:

- **Añadir fila**, **Importar** y **Restablecer todo** están encima de la cuadrícula. Al marcar filas se añaden **Restablecer seleccionados**, **Eliminar seleccionadas** y, para un par coincidente, **🔗 Promover par**.
- Las filas se comprueban mientras trabajas: los problemas aparecen en la parte superior bajo *Se han encontrado errores de validación*, y al hacer clic te lleva a la fila. Con muchas filas, la comprobación automática se pausa — pulsa **⚡ Validar ahora** antes de guardar.
- Cuando dos filas parecen las dos mitades de una transferencia o un cambio, un banner verde ofrece **Unir** las dos — dos filas nuevas, dos guardadas o una de cada. Cuando propone más de un par, **Unir todos (N)** las fusiona de una vez. Cuando las dos filas de un par tienen una descripción diferente o etiquetas diferentes, una elección se aplica a todos los pares: **Todo izquierda** conserva la descripción y las etiquetas de la primera fila, tal como las enumera el banner; **Todo derecha**, las de la segunda fila; **Combinar**, la opción predeterminada, conserva ambas descripciones y las etiquetas de ambas filas. Una descripción admite como máximo 500 caracteres, como en cualquier transacción: dos descripciones largas combinadas pueden superarlos, y entonces el guardado se rechaza.
- Cuando la otra mitad ya está guardada pero no está en el espacio de trabajo — por ejemplo, una transferencia cuyo primer lado importaste el mes pasado —, el botón 💡, encima de la cuadrícula y en el menú de la fila, ofrece añadirla: una vez dentro, el banner ofrece el par.
- **Guardar todo** escribe todo de una vez. Si hay sugerencias de fusión que no has revisado — el 💡 que nunca se abrió, el banner verde en el que nunca se hizo clic —, pregunta primero (*Sugerencias aún sin revisar*): **Mostrar las sugerencias** abre la lista del 💡 o trae el banner a la vista; **Guardar de todos modos** continúa. Una vez que has revisado, no vuelve a preguntar hasta que cierres el espacio de trabajo. **Cancelar** cierra el espacio de trabajo, preguntando primero si tienes cambios sin guardar.

??? warning "🚦 Banners después de una importación — cuándo aparecen"

    Tras una importación, los banners encima de la cuadrícula enumeran lo que hay que revisar antes de **Guardar todo**:

    - **rojo** — filas que el importador no entendió del todo: **Guardar todo** permanece deshabilitado hasta que las completes;
    - **ámbar** — campos derivados automáticamente que hay que verificar: **Guardar todo** primero te pide **Revisar** o **Guardar de todos modos**.

    Haz clic en un banner para desplegar su lista, y luego en una entrada: la cuadrícula pasa a la página de esa fila y la resalta. Los problemas de balance enumeran las filas que los causan (*Filas del espacio de trabajo: …*), y al hacer clic se abre la primera en el orden de clasificación actual. Si los filtros de tus columnas ocultan la fila, un mensaje te lo indica.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="transactions" data-name="bulk-todo-banner" alt="Espacio de trabajo masivo con el banner de campos a verificar desplegado y la fila de la entrada seleccionada resaltada en la cuadrícula">
</div>

Después de guardar, de **Promover par** o de **Separar par**, la página Transacciones borra su selección, ya que esas filas pueden haber cambiado; cerrar o cancelar la conserva. Si se rechaza un **Promover par** o un **Separar par**, no cambia nada: un mensaje de error indica el motivo y la confirmación sigue abierta.

---

## 🧭 Guías contextuales

La página Transacciones, el formulario **Agregar Transacción**, el espacio de trabajo masivo y el [Asistente de importación](import/how-to.md#guided-first-import) tienen cada uno una guía breve. Una guía solo se inicia cuando su pantalla está lista y nunca edita un borrador ni pulsa un botón por ti; en el espacio de trabajo muestra un aviso a la vez, que se cierra con **Entendido**.

Puedes repetir cualquier guía desde [Ajustes → Preferencias → Introducción y guías](../settings/preferences.md#onboarding-and-guides).

---

## 🔗 Relacionado

* 📝 **[Formulario de transacción](form.md)** — campos y tipos de transacción
* 📥 **[Importar desde el bróker](import/index.md)** — el flujo de trabajo de importación BRIM
* 📖 **[Tipos de transacción](../../financial-theory/instruments/transaction-types/index.md)** — la teoría financiera detrás de cada tipo
