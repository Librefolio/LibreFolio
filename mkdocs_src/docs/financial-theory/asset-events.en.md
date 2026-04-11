# 📅 Asset Events

Asset events represent **corporate actions or scheduled financial occurrences** that affect an asset globally — independent of any individual investor's portfolio. They are distinct from [transactions](transaction-types.md), which track what happens at the portfolio level (e.g., a user buying or selling shares).

Understanding asset events is essential for accurate price analysis, total return calculations, and historical chart interpretation.

---

## 📊 Event Types Overview

| Type | Emoji | Impact on Price | Typical Assets |
|------|-------|----------------|----------------|
| **[Dividend](asset-events/dividend.md)** | 💰 | Price drops by dividend amount (ex-date) | Stocks, ETFs |
| **[Interest](asset-events/interest.md)** | 📈 | Accrual reduces remaining yield | Bonds, Loans, Fixed-income |
| **[Split](asset-events/split.md)** | ✂️ | Price divides, quantity multiplies | Stocks, ETFs |
| **[Price Adjustment](asset-events/price-adjustment.md)** | 📊 | Algebraic change (+/−) to fair value | Bonds, Illiquid assets |
| **[Maturity Settlement](asset-events/maturity-settlement.md)** | 🏁 | Final capital return, no further pricing | Bonds, Term deposits |

---

## 🔄 Events vs Transactions

| Concept | Events | Transactions |
|---------|--------|-------------|
| **Scope** | Global — affects the asset itself | Personal — affects a user's portfolio |
| **Example** | "Apple declared a $0.25 dividend on 2024-05-10" | "I received $12.50 from my 50 AAPL shares" |
| **Effect on chart** | Marker on the price chart | Not visible on price chart |
| **Who creates them** | Provider (automatic) or user (manual) | Import from broker reports (BRIM) |

---

## ⚙️ Sources of Events

### Provider-generated (automatic)

Some providers produce events during data synchronization:

- **Scheduled Investment**: generates `INTEREST` and `PRICE_ADJUSTMENT` events from the configured interest schedule
- **Yahoo Finance**: may produce `DIVIDEND` events from historical data

Provider-generated events have a `provider_assignment_id` and are automatically refreshed during sync (deduplication on `asset_id + date + type`).

### User-created (manual)

Events can be added manually via the **Data Editor** or **CSV Import**. Manual events have no `provider_assignment_id` and are never auto-deleted during sync.

---

## 📈 Event Markers on the Chart

Events appear as **colored diamond markers** (◆) on the interactive price chart. Each event type has a distinct color. Hover over a marker to see full details (date, type, value, currency, notes).

Double-clicking an event marker while the Data Editor is open will **scroll directly to that event's row** in the Events tab.

---

## 🔗 Related

- 📈 **[Interactive Chart](../user/assets/detail/chart.md)** — Event markers on the chart
- ✏️ **[Data Editor](../user/assets/detail/data-editor.md)** — Manual event management
- 💸 **[Transaction Types](transaction-types.md)** — Portfolio-level operations


