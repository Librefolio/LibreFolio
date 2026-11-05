# 📅 Eventos del activo

Los eventos del activo son cosas que le suceden al propio activo, para todos los que lo poseen: un dividendo, un desdoblamiento, un pago de intereses. No son tus [transacciones](../../../financial-theory/instruments/transaction-types/index.md), que registran lo que sucede en tu cartera.

---

## 📊 Tipos de eventos

Cada tipo, con lo que hace al precio y su página de teoría:

- 💰 **Dividendo** (`DIVIDEND`) — efectivo pagado por una acción o un ETF; el precio baja aproximadamente ese importe en la fecha ex → [📖](../../../financial-theory/instruments/asset-events/dividend.md)
- 📈 **Interés** (`INTEREST`) — interés pagado por un bono, un préstamo o un depósito; el valor baja en el importe pagado → [📖](../../../financial-theory/instruments/asset-events/interest.md)
- ✂️ **Desdoblamiento** (`SPLIT`) — las unidades se desdoblan; cambia su número, no el valor total → [📖](../../../financial-theory/instruments/asset-events/split.md)
- 📊 **Ajuste de precio** (`PRICE_ADJUSTMENT`) — un cambio de valor sin efectivo, al alza o a la baja: una depreciación, un recorte, una recalificación → [📖](../../../financial-theory/instruments/asset-events/price-adjustment.md)
- 🏁 **Liquidación al vencimiento** (`MATURITY_SETTLEMENT`) — el activo alcanza el vencimiento y devuelve su capital; su valor deja de cambiar → [📖](../../../financial-theory/instruments/asset-events/maturity-settlement.md)

Los códigos entre paréntesis son los que espera una [importación de CSV](data-editor.md#import-from-csv).

---

## 📈 Eventos en el gráfico

En el modo **Precios**, los eventos aparecen como marcadores en el [gráfico de precios](chart.md), cada tipo con su propia forma: un triángulo para un dividendo, un rombo para un interés, un cuadrado para un ajuste de precio, un cuadrado redondeado para el vencimiento y una flecha para un desdoblamiento. Pasa el cursor sobre un marcador para ver su fecha, tipo, importe y notas.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-events" alt="Gráfico del activo con un marcador de evento sobre el que se pasa el cursor">
</div>

- **En otra moneda**, el importe se convierte, con el importe original debajo; un evento que no se puede convertir se oculta.
- **Los activos comparados** también muestran sus eventos, en el color de su línea.

---

## ⚙️ De dónde vienen los eventos

- **De un proveedor**, en cada sincronización: dividendos y desdoblamientos de [Yahoo Finance](../providers/yahoo-finance.md), dividendos de [justETF](../providers/justetf.md), y de la [Inversión programada](../providers/scheduled-investment.md) los pagos de intereses y la liquidación final al vencimiento de **Generar cupón**, además de los eventos enumerados en su calendario (**Añadir evento** en el formulario del activo).
- **De ti**: en la pestaña **Eventos** del [Editor de datos](data-editor.md), uno a uno o desde un archivo CSV, o con **+ Nuevo evento** en el campo **Evento vinculado** de una transacción ([más abajo](#new-event)).

Una sincronización actualiza los eventos del proveedor y nunca toca los tuyos. Un evento de un proveedor es de solo lectura en el editor, y su borrado solo se mantiene hasta que el proveedor lo vuelva a enviar: para cambiar los eventos de una Inversión programada, edita su calendario. Eliminar el proveedor (**Sin proveedor** en el [formulario del activo](../create-edit.md#editing-an-asset)) borra sus eventos, y no se permite mientras una transacción esté vinculada a uno de ellos.

### ✨ Nuevo evento desde una transacción {: #new-event }

**+ Nuevo evento**, en el campo **Evento vinculado** de un dividendo, un interés o un ajuste, crea un evento para el activo de la transacción y lo vincula a la transacción. Nunca sobrescribe un evento: si el activo ya tiene uno de ese tipo en esa fecha, introducido a mano o procedente de un proveedor de datos, no se guarda nada y la ventana muestra lo que hay en *Este evento ya existe*. Para cada evento: su tipo, fecha, importe y notas, de dónde procede y cuántas transacciones están vinculadas a él. Después, elige:

- **Usar este** — vincula ese evento a la transacción y no cambia nada más.
- **Editar este** — solo para un evento introducido a mano: la ventana pasa a ser *Editar evento para …*, rellenada con los valores de ese evento. Cambia lo que necesites y haz clic en **Guardar**: ese mismo evento se actualiza, también para las transacciones ya vinculadas a él, y esta transacción queda vinculada a él.
- **Cancelar** — vuelve al formulario, con lo que hayas escrito (el **Cancelar** de abajo cierra la ventana).

Un evento de un proveedor de datos solo ofrece **Usar este**, con una nota: el proveedor actualiza sus propios eventos. Desde aquí no hay forma de añadir un segundo evento del mismo tipo en la misma fecha. En el [Editor de datos](data-editor.md), en cambio, una fila nueva o una línea de CSV con la fecha y el tipo de uno de tus eventos actualiza ese evento.

Después de **Editar este**, el campo **Evento vinculado** muestra el evento con sus nuevos valores.

---

## 🧮 Eventos en una Inversión programada

Para una [Inversión programada](../providers/scheduled-investment.md#how-value-is-calculated), los eventos forman parte del propio precio:

$$
P(d) = V_0 + I(d) - \sum \text{Interés} + \sum \text{Ajustes de precio}
$$

donde $V_0$ es el valor inicial y $I(d)$ el interés acumulado hasta ahora. Para un activo valorado a precio de mercado, los eventos solo explican movimientos del precio, como la caída en una fecha ex-dividendo; no cambian los precios que envía el proveedor.

---

## 🔗 Relacionado

- 📈 **[Gráfico interactivo](chart.md)** — Marcadores de eventos en el gráfico
- ✏️ **[Editor de datos](data-editor.md)** — Gestión manual de eventos con importación de CSV
- 🧮 **[Inversión programada](../providers/scheduled-investment.md)** — Proveedor que genera eventos a partir de calendarios de intereses
- 📚 **[Eventos del activo (Teoría financiera)](../../../financial-theory/instruments/asset-events/index.md)** — Análisis detallado de cada tipo de evento
- 💸 **[Tipos de transacción (Teoría financiera)](../../../financial-theory/instruments/transaction-types/index.md)** — Transacciones frente a eventos
- 🛠️ **[Eventos del activo (desarrollador)](../../../developer/backend/assets/events.md)** — Para desarrolladores: cómo se almacenan y actualizan los eventos
