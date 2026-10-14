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
- **From you**: in the **Events** tab of the [Data Editor](data-editor.md), one by one or from a CSV file, or with **New event** in the **Linked Event** field of a transaction.

A sync refreshes the provider's events and never touches yours. A provider's event is read-only in the editor, and deleting it lasts only until the provider sends it again: to change a Scheduled Investment's events, edit its schedule.

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
