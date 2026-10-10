# 📝 Formulario de transacción

El formulario de transacción añade o edita una transacción — o un par vinculado — en el [espacio de trabajo masivo](index.md#bulk-workspace). También muestra una transacción en solo lectura cuando haces doble clic en ella en una lista. Solo aparecen los campos que necesita el tipo elegido.

<div class="lf-screenshot-carousel" data-carousel="transactions" data-carousel-interval="3000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="transactions" data-name="form-modal" data-title='<img src="/LibreFolio/static/icons/transactions/buy.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> COMPRA' alt="Compra">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-sell" data-title='<img src="/LibreFolio/static/icons/transactions/sell.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> VENTA' alt="Venta">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-dividend" data-title='<img src="/LibreFolio/static/icons/transactions/dividend.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DIVIDENDO' alt="Dividendo">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-deposit" data-title='<img src="/LibreFolio/static/icons/transactions/deposit.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DEPÓSITO' alt="Depósito">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-adjustment" data-title='<img src="/LibreFolio/static/icons/transactions/adjustment.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> AJUSTE' alt="Ajuste">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> TRANSFERENCIA DE ACTIVOS' alt="Transferencia de activos">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-fxconversion" data-title='<img src="/LibreFolio/static/icons/transactions/fx-conversion.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> CONVERSIÓN FX' alt="Conversión FX">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-cash-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/cash-transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> TRANSFERENCIA DE FONDOS' alt="Transferencia de fondos">
</div>

---

## ✍️ Rellena el formulario

1. Elige el **Tipo**, luego el **Bróker** si aún no está establecido.
2. Rellena la sección **Obligatorio**: la **Fecha**, el **Activo** y su cantidad cuando el tipo la tiene, y el importe en efectivo.
3. Abre **Opcional** para **Etiquetas**, una **Descripción** o, en dividendos, interés y ajustes, un **Evento vinculado**.
4. Haz clic en **Aplicar** para colocar la fila en el espacio de trabajo; **Guardar todo** en el espacio de trabajo la guarda.

Algunas reglas hacen que las entradas sean rápidas:

- **Los importes son totales** — escribe el total pagado o recibido, no el precio por acción (*Importe total (no por acción)*).
- **Escribe números positivos** — el formulario añade el signo menos donde sale dinero o unidades: el pago de una compra, las unidades de una venta, un retiro, una comisión, un impuesto. Solo una cantidad de **Ajuste** lleva signo: positiva añade unidades, negativa las elimina.
- **Comprobaciones sobre la marcha** — una vez rellenados los campos obligatorios, el formulario comprueba la entrada con tu libro mayor y las demás filas del espacio de trabajo, y enumera cualquier problema en la parte superior. **⚡ Validar ahora** comprueba al instante.
- **¿Falta un bróker o un activo?** — **Crear nuevo** en la lista de brókers, o **Nuevo activo** en la lista de activos, lo crea sin salir del formulario.

??? info "💰 Coste base de las unidades entrantes — para Ajustes y Transferencias de activos"

    Cuando un **Ajuste** añade unidades, o en el lado receptor de una **Transferencia de activos**, el formulario pregunta cuánto costaron esas unidades:

    - **Auto** — LibreFolio lo calcula como un [precio medio de compra (PMC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md); pulsa **⚡ Validar ahora** para verlo.
    - **Manual** — lo escribes tú.

    En **Auto**, el PMC se toma en el bróker de origen de una transferencia, o en el bróker propio del ajuste. Si ese bróker no tiene otra transacción en el activo hasta la fecha en que entran las unidades, no hay nada que promediar, y el coste es 0 por diseño: si esas unidades sí costaron algo, vuelve a abrir la transacción después y escribe su coste en **Manual**. En **Manual**, el campo no puede quedar vacío: LibreFolio marca la fila y no guarda nada hasta que lo rellenes o cambies a **Auto**. Para unidades que no costaron nada, como un regalo, escribe 0. Si falta un tipo de cambio, el enlace **Sincronizar tipos de cambio** lo obtiene.

---

## 🏷️ Tipos de transacción

La [Guía de teoría financiera](../../financial-theory/instruments/transaction-types/index.md) explica cada tipo en profundidad.

### 🧾 Transacciones simples

| Tipo | Qué registra | Teoría |
|------|-----------------|--------|
| ![](../../static/icons/transactions/buy.png){: width="24" style="vertical-align: middle;" } **Compra** | Unidades de un activo compradas, y el total pagado | [📖 Leer](../../financial-theory/instruments/transaction-types/buy-sell.md) |
| ![](../../static/icons/transactions/sell.png){: width="24" style="vertical-align: middle;" } **Venta** | Unidades de un activo vendidas, y el total recibido | [📖 Leer](../../financial-theory/instruments/transaction-types/buy-sell.md) |
| ![](../../static/icons/transactions/dividend.png){: width="24" style="vertical-align: middle;" } **Dividendo** | Efectivo pagado por un activo que posees | [📖 Leer](../../financial-theory/instruments/transaction-types/dividend-interest.md) |
| ![](../../static/icons/transactions/interest.png){: width="24" style="vertical-align: middle;" } **Interés** | Intereses recibidos, con o sin un activo | [📖 Leer](../../financial-theory/instruments/transaction-types/dividend-interest.md) |
| ![](../../static/icons/transactions/deposit.png){: width="24" style="vertical-align: middle;" } **Depósito** | Efectivo que ingresas en el bróker | [📖 Leer](../../financial-theory/instruments/transaction-types/deposit-withdrawal.md) |
| ![](../../static/icons/transactions/withdrawal.png){: width="24" style="vertical-align: middle;" } **Retiro** | Efectivo que sacas del bróker | [📖 Leer](../../financial-theory/instruments/transaction-types/deposit-withdrawal.md) |
| ![](../../static/icons/transactions/fee.png){: width="24" style="vertical-align: middle;" } **Comisión** | Una comisión u otro coste, opcionalmente vinculado a un activo | [📖 Leer](../../financial-theory/instruments/transaction-types/fee.md) |
| ![](../../static/icons/transactions/tax.png){: width="24" style="vertical-align: middle;" } **Impuesto** | Un impuesto pagado, opcionalmente vinculado a un activo | [📖 Leer](../../financial-theory/instruments/transaction-types/fee.md) |
| ![](../../static/icons/transactions/adjustment.png){: width="24" style="vertical-align: middle;" } **Ajuste** | Unidades añadidas o eliminadas sin efectivo: un desdoblamiento, un regalo, una posición abierta en otro lugar | [📖 Leer](../../financial-theory/instruments/transaction-types/adjustment.md) |

### 🔗 Transacciones emparejadas {: #composite-transactions }

Una operación emparejada se registra como dos transacciones vinculadas, que el formulario muestra como una, con un lado **Desde** y un lado **Hasta**. Cada lado tiene su propia fecha, y la flecha **Intercambiar lados** invierte la dirección.

| Tipo | Qué registra | Teoría |
|------|-----------------|--------|
| ![](../../static/icons/transactions/transfer.png){: width="24" style="vertical-align: middle;" } **Transferencia de activos** | Unidades de un activo movidas entre dos de tus brókers | [📖 Leer](../../financial-theory/instruments/transaction-types/transfer.md) |
| ![](../../static/icons/transactions/cash-transfer.png){: width="24" style="vertical-align: middle;" } **Transferencia de fondos** | Efectivo movido entre dos de tus brókers, en una sola divisa | [📖 Leer](../../financial-theory/instruments/transaction-types/cash-transfer.md) |
| ![](../../static/icons/transactions/fx-conversion.png){: width="24" style="vertical-align: middle;" } **Cambio de divisas** | Una divisa convertida en otra, dentro de un mismo bróker | [📖 Leer](../../financial-theory/instruments/transaction-types/fx-conversion.md) |

Una transferencia necesita dos brókers diferentes; un cambio de divisas, dos divisas diferentes. También se pueden vincular dos filas simples para formar un par más adelante, y dividir un par de nuevo — consulta [Vincular o desvincular un par](index.md#link-pairs).

---

## 🔗 Relacionado

- 📋 **[Transacciones](index.md)** — la lista, los filtros y el espacio de trabajo masivo
- 📥 **[Importar desde el bróker](import/index.md)** — omite la entrada manual con una importación BRIM
