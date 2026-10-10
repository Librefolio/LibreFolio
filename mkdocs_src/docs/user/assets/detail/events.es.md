# 📅 Eventos de Activos

Los eventos de activos son cosas que le ocurren al activo en sí, para todos los que lo poseen: un dividendo, un desdoblamiento, un pago de intereses. No son tus [transacciones](../../../financial-theory/instruments/transaction-types/index.md), que registran lo que ocurre en tu cartera.

---

## 📊 Tipos de eventos

Cada tipo, con su efecto sobre el precio y su página teórica:

- 💰 **Dividendo** (`DIVIDEND`) — efectivo pagado por una acción o un ETF; el precio baja aproximadamente esa cantidad en la fecha ex-dividendo → [📖](../../../financial-theory/instruments/asset-events/dividend.md)
- 📈 **Interés** (`INTEREST`) — interés pagado por un bono, un préstamo o un depósito; el valor baja por el importe pagado → [📖](../../../financial-theory/instruments/asset-events/interest.md)
- ✂️ **Desdoblamiento** (`SPLIT`) — las unidades se dividen; su número cambia, no el valor total → [📖](../../../financial-theory/instruments/asset-events/split.md)
- 📊 **Ajuste de Precio** (`PRICE_ADJUSTMENT`) — un cambio de valor sin efectivo, al alza o a la baja: una reducción de valor, un recorte, una revalorización → [📖](../../../financial-theory/instruments/asset-events/price-adjustment.md)
- 🏁 **Liquidación al Vencimiento** (`MATURITY_SETTLEMENT`) — el activo alcanza el vencimiento y devuelve su capital; su valor deja de cambiar → [📖](../../../financial-theory/instruments/asset-events/maturity-settlement.md)

Los códigos entre paréntesis son los que espera una [importación CSV](data-editor.md#import-from-csv).

---

## 📈 Eventos en el gráfico

En modo **Precios**, los eventos aparecen como marcadores en el [gráfico de precios](chart.md), cada tipo con su propia forma: un triángulo para un dividendo, un rombo para el interés, un cuadrado para un ajuste de precio, un cuadrado redondeado para el vencimiento, una flecha para un desdoblamiento. Pasa el cursor sobre un marcador para ver su fecha, tipo, importe y notas.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-events" alt="Gráfico de activo con un marcador de evento bajo el cursor">
</div>

- **En otra divisa**, el importe se convierte, con el importe original debajo; un evento que no se puede convertir se oculta.
- **Activos comparados** también muestran sus eventos, en el color de su línea.

---

## ⚙️ De dónde vienen los eventos

- **De un proveedor**, en cada sincronización: dividendos y desdoblamientos de [Yahoo Finance](../providers/yahoo-finance.md), dividendos de [justETF](../providers/justetf.md), y de [Inversión Programada](../providers/scheduled-investment.md) los pagos de intereses y la liquidación final al vencimiento de **Generar Cupón**, más los eventos listados en su calendario (**Añadir Evento** en el formulario del activo).
- **De ti**: en la pestaña **Eventos** del [Editor de Datos](data-editor.md), uno a uno o desde un archivo CSV, o con **Nuevo evento** en el campo **Evento Vinculado** de una transacción.

Una sincronización actualiza los eventos del proveedor y nunca toca los tuyos. Un evento de un proveedor es de solo lectura en el editor, y si lo eliminas, solo se mantiene así hasta que el proveedor lo vuelva a enviar: para cambiar los eventos de una Inversión Programada, edita su calendario.

---

## 🧮 Eventos en una Inversión Programada

Para una [Inversión Programada](../providers/scheduled-investment.md#how-value-is-calculated), los eventos son parte del propio precio:

$$
P(d) = V_0 + I(d) - \sum \text{Interés} + \sum \text{Ajustes de precio}
$$

con $V_0$ el valor inicial y $I(d)$ el interés acumulado hasta el momento. Para un activo con precio de mercado, los eventos solo explican movimientos en el precio, como la caída en una fecha ex-dividendo; no cambian los precios que envía el proveedor.

---

## 🔗 Relacionado

- 📈 **[Gráfico Interactivo](chart.md)** — Marcadores de eventos en el gráfico
- ✏️ **[Editor de Datos](data-editor.md)** — Gestión manual de eventos con importación CSV
- 🧮 **[Inversión Programada](../providers/scheduled-investment.md)** — Proveedor que genera eventos a partir de calendarios de intereses
- 📚 **[Eventos de Activos (Teoría Financiera)](../../../financial-theory/instruments/asset-events/index.md)** — Análisis detallado de cada tipo de evento
- 💸 **[Tipos de Transacción (Teoría Financiera)](../../../financial-theory/instruments/transaction-types/index.md)** — Transacciones vs eventos
- 🛠️ **[Eventos de Activos (desarrollador)](../../../developer/backend/assets/events.md)** — Para desarrolladores: cómo se almacenan y actualizan los eventos
