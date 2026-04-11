# 📅 Asset Events

Asset events represent things that happen to the asset **globally** — not at the portfolio level. They are distinct from [transactions](../../../financial-theory/transaction-types.en.md), which track what happens in a user's portfolio.

For a deep dive into each event type — including market impact, formulas, and practical examples — see the **[Asset Events (Financial Theory)](../../../financial-theory/asset-events.en.md)** section.

---

## 📊 Event Types

| Type | Icon | Effect on Price | Description | Learn More |
|------|------|----------------|-------------|-----------|
| **Dividend** | 💰 | Price drops by event value (ex-date) | Cash distribution from equity or ETF | [📖](../../../financial-theory/asset-events/dividend.en.md) |
| **Interest** | 📈 | Price drops by event value | Interest payment from debt instrument or loan | [📖](../../../financial-theory/asset-events/interest.en.md) |
| **Split** | ✂️ | Changes quantity, not total value | Stock or unit split | [📖](../../../financial-theory/asset-events/split.en.md) |
| **Price Adjustment** | 📊 | Algebraic change (+/-) | Non-cash value change: write-down, haircut, re-rating | [📖](../../../financial-theory/asset-events/price-adjustment.en.md) |
| **Maturity Settlement** | 🏁 | Final capital return | Asset reaches maturity — no further price calculations | [📖](../../../financial-theory/asset-events/maturity-settlement.en.md) |

## 📈 Event Markers on the Chart

Events appear as **colored markers** on the [price chart](chart.en.md). Each event type has a distinct color and icon. Hover over a marker to see the event details (date, type, value, currency).

## ⚙️ Where Events Come From

Events can be generated in two ways:

### 1. Provider-generated (automatic)

Some providers produce events during sync:

- **[Scheduled Investment](../providers/scheduled-investment.en.md)**: generates INTEREST and PRICE_ADJUSTMENT events from the interest schedule configuration
- **[Yahoo Finance](../providers/yahoo-finance.en.md)**: may produce DIVIDEND events from historical data

Provider-generated events have a `provider_assignment_id` and are automatically updated during sync (DELETE + INSERT deduplication on `asset_id, date, type`).

### 2. User-created (manual)

Events can also be added manually via the asset edit modal. Manual events have no `provider_assignment_id` and are never auto-deleted during sync.

---

## 🧮 How Events Affect Price Calculation

For the **Scheduled Investment** provider, events are integral to the price calculation:

```
price(d) = initial_value + accrued_interest − Σ(INTEREST events) + Σ(PRICE_ADJUSTMENT events)
```

For market-priced assets (Yahoo Finance, justETF), events are informational — they explain sudden price drops (ex-dividend dates) but don't directly modify the fetched price.

---

## 🔗 Related

- 📈 **[Interactive Chart](chart.en.md)** — Event markers on the chart
- ✏️ **[Data Editor](data-editor.en.md)** — Manual event management with CSV import
- 🧮 **[Scheduled Investment](../providers/scheduled-investment.en.md)** — Provider that generates events from interest schedules
- 📚 **[Asset Events (Financial Theory)](../../../financial-theory/asset-events.en.md)** — Detailed analysis of each event type
- 💸 **[Transaction Types (Financial Theory)](../../../financial-theory/transaction-types.en.md)** — Transactions vs events
