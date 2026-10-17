# 📅 Asset Events

Asset events are things that happen to the asset itself, for everyone who holds it: a dividend, a split, an interest payment. They are not your [transactions](../../../financial-theory/instruments/transaction-types/index.md), which record what happens in your portfolio.

---

## 📊 Event types

Each type, with what it does to the price and its theory page:

- 💰 **Dividend** (`DIVIDEND`) — cash paid out by a stock or an ETF; the price drops by about that amount on the ex-date → [📖](../../../financial-theory/instruments/asset-events/dividend.md)
- 📈 **Interest** (`INTEREST`) — interest paid by a bond, a loan or a deposit; the value drops by the amount paid → [📖](../../../financial-theory/instruments/asset-events/interest.md)
- ✂️ **Split** (`SPLIT`) — the units are split; their number changes, not the total value → [📖](../../../financial-theory/instruments/asset-events/split.md)
- 📊 **Price Adjustment** (`PRICE_ADJUSTMENT`) — a value change without cash, up or down: a write-down, a haircut, a re-rating → [📖](../../../financial-theory/instruments/asset-events/price-adjustment.md)
- 🏁 **Maturity Settlement** (`MATURITY_SETTLEMENT`) — the asset reaches maturity and pays back its capital; its value stops changing → [📖](../../../financial-theory/instruments/asset-events/maturity-settlement.md)

The codes in brackets are the ones a [CSV import](data-editor.md#import-from-csv) expects.

---

## 📈 Events on the chart

In **Prices** mode, events appear as markers on the [price chart](chart.md), each type with its own shape: a triangle for a dividend, a diamond for interest, a square for a price adjustment, a rounded square for maturity, an arrow for a split. Hover a marker for its date, type, amount and notes.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-events" alt="Asset chart with an event marker hovered">
</div>

- **In another currency**, the amount is converted, with the original amount below it; an event that cannot be converted is hidden.
- **Compared assets** show their events too, in the colour of their line.

---

## ⚙️ Where events come from

- **From a provider**, at each sync: dividends and splits from [Yahoo Finance](../providers/yahoo-finance.md), dividends from [justETF](../providers/justetf.md), and from [Scheduled Investment](../providers/scheduled-investment.md) the interest payouts and final maturity settlement of **Generate Coupon**, plus the events listed in its schedule (**Add Event** in the asset form).
- **From you**: in the **Events** tab of the [Data Editor](data-editor.md), one by one or from a CSV file, or with **+ New event** in the **Linked Event** field of a transaction ([below](#new-event)).

A sync refreshes the provider's events and never touches yours. A provider's event is read-only in the editor, and deleting it lasts only until the provider sends it again: to change a Scheduled Investment's events, edit its schedule. Removing the provider (**No Provider** in the [asset form](../create-edit.md#editing-an-asset)) deletes its events, and is refused while a transaction is linked to one of them.

### ✨ New event from a transaction {: #new-event }

**+ New event**, in the **Linked Event** field of a dividend, an interest or an adjustment, creates an event for the transaction's asset and links it to the transaction. It never overwrites an event: if the asset already has one of that type on that date, entered by hand or from a data provider, nothing is saved and the window shows what is there under *This event already exists*. For each event: its type, date, amount and notes, where it comes from and how many transactions are linked to it. Then choose:

- **Use this** — links that event to the transaction, and changes nothing else.
- **Edit this** — only for an event entered by hand: the window becomes *Edit event for …*, filled with that event's values. Change what you need and click **Save**: that same event is updated, for the transactions already linked to it too, and this transaction is linked to it.
- **Cancel** — back to the form, with what you typed (the **Cancel** at the bottom closes the window).

An event from a data provider offers only **Use this**, with a note: the provider updates its own events. There is no way to add a second event of the same type on the same date from here. In the [Data Editor](data-editor.md), instead, a new row or a CSV line on the date and type of one of your events updates that event.

After **Edit this**, the **Linked Event** field shows the event with its new values.

---

## 🧮 Events in a Scheduled Investment

For a [Scheduled Investment](../providers/scheduled-investment.md#how-value-is-calculated), events are part of the price itself:

$$
P(d) = V_0 + I(d) - \sum \text{Interest} + \sum \text{Price adjustments}
$$

with $V_0$ the initial value and $I(d)$ the interest accrued so far. For a market-priced asset, events only explain moves in the price, such as the drop on an ex-dividend date; they do not change the prices the provider sends.

---

## 🔗 Related

- 📈 **[Interactive Chart](chart.md)** — Event markers on the chart
- ✏️ **[Data Editor](data-editor.md)** — Manual event management with CSV import
- 🧮 **[Scheduled Investment](../providers/scheduled-investment.md)** — Provider that generates events from interest schedules
- 📚 **[Asset Events (Financial Theory)](../../../financial-theory/instruments/asset-events/index.md)** — Detailed analysis of each event type
- 💸 **[Transaction Types (Financial Theory)](../../../financial-theory/instruments/transaction-types/index.md)** — Transactions vs events
- 🛠️ **[Asset Events (developer)](../../../developer/backend/assets/events.md)** — For developers: how events are stored and refreshed
