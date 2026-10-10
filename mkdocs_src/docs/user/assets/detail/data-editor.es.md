# ✏️ Editor de datos

El editor de datos te permite corregir y completar a mano los datos de un activo: sus precios diarios y sus eventos, como los dividendos. Úsalo para corregir un precio erróneo de un proveedor, añadir el historial de un activo que no lo tenga, rellenar un hueco o registrar un evento que el proveedor haya pasado por alto.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-editor" alt="Editor de datos del activo" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Editar precios y eventos

1. En el modo **Precios**, haz clic en **✏️ Editar precios y eventos** en la parte superior derecha del gráfico. El editor se abre debajo del gráfico, con una pestaña **Precios** y otra **Eventos**.
2. Cambia lo que necesites:
    - **Añadir fila** añade una fila en una fecha libre: cambia la fecha si es necesario y rellena los valores.
    - Haz clic en una celda para editarla.
    - **Eliminar**, en el menú **⋮** de una fila, marca la fila para eliminarla, y **Deshacer** la recupera. Marca varias filas para eliminarlas juntas.
    - **Importar CSV** carga muchas filas a la vez ([más abajo](#import-from-csv)).
3. Haz clic en **Guardar (n)**, donde *n* cuenta tus cambios, o en **Cancelar** para descartarlos. Ambos cierran el editor y vuelven a mostrar los otros paneles; el ✕ también lo hace, sin guardar.

Hasta que guardes, los precios nuevos y modificados se muestran en el gráfico como una línea morada. Un precio guardado fuera de las fechas mostradas amplía el rango para incluirlo.

---

## 💰 Pestaña Precios

- **Cierre** es obligatorio y debe ser un número positivo; **Apertura**, **Máximo**, **Mínimo** y **Volumen** son opcionales, y la goma de borrar en una celda limpia su valor.
- Los precios están en la moneda del activo, que se muestra junto a las pestañas (*Precios en USD*).
- Las **filas obsoletas** son días sin un precio propio, rellenados con el último conocido. Cuando las hay, aparecen un contador ⚠️ y un interruptor: actívalo para ocultarlas.

---

## 📅 Pestaña Eventos

Cada fila tiene un **Tipo** (Dividendo, Interés, Desdoblamiento, Ajuste de precio o Vencimiento), un **Importe** en la moneda del activo (por acción para un dividendo, la proporción de un desdoblamiento) y **Notas** opcionales. Consulta [Eventos de activos](events.md) para saber qué hace cada tipo.

- **Los eventos de un proveedor son de solo lectura**: una edición se sobrescribiría en su próxima sincronización. Puedes eliminar uno, pero el proveedor lo vuelve a añadir en su próxima sincronización; para eliminarlo definitivamente, cambia la configuración del proveedor del activo.
- **Editar uno de tus eventos modifica ese evento**, incluido su **Tipo**: no se añade un segundo evento. Una transacción vinculada a él permanece vinculada y se interpreta según el nuevo tipo: un **Ajuste** vinculado a un desdoblamiento, por ejemplo, deja de contar como desdoblamiento una vez que el evento es un Ajuste de precio.
- **Cambiar el Tipo de un evento al que ya tiene otro de tus eventos en esa fecha** se rechaza al guardar; intercambiar los tipos de dos eventos en un solo guardado funciona. Si vas a eliminar ese otro evento, guarda primero la eliminación. Un guardado rechazado mantiene tus cambios en el editor para que los corrijas, mientras que los cambios de precios del mismo guardado ya se han almacenado.
- **Un evento al que está vinculada una transacción** no se puede eliminar: en su lugar, el guardado te avisa.

---

## 📥 Importar desde CSV {: #import-from-csv }

**Importar CSV** abre una ventana donde puedes soltar un archivo o pegar su texto, y cada fila se comprueba antes de importarla. La primera línea debe nombrar las columnas, en cualquier orden.

=== "Precios"

    ```text
    date;currency;close;open;high;low;volume
    2024-01-15;USD;145.50;144.00;146.20;143.80;1500000
    2024-01-16;USD;146.10;;;;
    ```

    `date`, `currency` y `close` son obligatorios: escribe la moneda del activo.

=== "Eventos"

    ```text
    date;currency;type;amount;notes
    2024-03-15;USD;DIVIDEND;1.25;Q1 payout
    2024-06-01;;SPLIT;2;2:1 split
    ```

    `date`, `type` y `amount` son obligatorios. `type` es uno de `DIVIDEND`, `INTEREST`, `SPLIT`, `PRICE_ADJUSTMENT` y `MATURITY_SETTLEMENT`.

    Se acepta `value` en lugar de `amount`, por lo que un archivo de eventos exportado por LibreFolio (la copia de seguridad que se ofrece cuando [cambias la moneda de un activo](../create-edit.md#editing-an-asset)) se puede volver a importar, ignorando sus otras columnas. Ten en cuenta dos límites:

    - **Un evento por fecha**: las filas que comparten una fecha se omiten todas por ser duplicados, así que importa esos eventos desde archivos separados.
    - **Cada fila se convierte en tu propio evento**, incluidos los de un proveedor: omite las filas cuyo `source` sea `PROVIDER` si el proveedor las volverá a enviar, o aparecerán dos veces.

- Las fechas son `YYYY-MM-DD`, y los decimales pueden usar `.` o `,`.
- Las columnas se separan por `;` o `,`; con `,`, escribe los decimales con `.`.
- Las otras columnas se ignoran, por lo que un archivo de precios exportado por LibreFolio se importa tal cual.
- La columna `currency` no se comprueba ni se convierte: los importes se almacenan en la moneda del activo tal como están, así que convierte primero los de una copia de seguridad tomada antes de un cambio de moneda.
- Una línea de precios actualiza el precio de su fecha; una línea de evento actualiza tu evento con la misma fecha y tipo. Una línea que coincide solo con un evento de un proveedor se omite, ya que una importación nunca cambia esos; las demás se añaden. No se almacena nada hasta que hagas clic en **Guardar**.

---

## 🖱️ Saltar desde el gráfico

Con el editor abierto, haz doble clic en un punto del gráfico (o mantén pulsado sobre él en un teléfono) para saltar a esa fecha: a la pestaña **Eventos** cuando la fecha tenga un evento, a **Precios** en caso contrario.

---

## 🔗 Relacionado

- 📈 **[Gráfico interactivo](chart.md)** — Visualización del gráfico con marcadores de eventos
- 📅 **[Eventos de activos](events.md)** — Tipos de eventos y sus fuentes
- 📚 **[Eventos de activos (Teoría financiera)](../../../financial-theory/instruments/asset-events/index.md)** — Análisis detallado del impacto de cada tipo de evento
- 🔌 **[Proveedores](../providers/index.md)** — Obtención automática de precios
- 🛠️ **[Componentes del editor de puntos de datos](../../../developer/frontend/components/core-ui/data-editor.md)** — Para desarrolladores: cómo el editor comprueba, fusiona y guarda filas
