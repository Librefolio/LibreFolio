# 📝 Transaction Form

The Transaction Form opens whenever you **create** or **edit** a transaction. It adapts dynamically to the selected transaction type, showing only the fields relevant to that operation.

---

## 🏷️ Transaction Types

| Type | Icon | Description |
|------|------|-------------|
| **BUY** | 🟢 | Purchase of an asset |
| **SELL** | 🔴 | Sale of an asset |
| **DIVIDEND** | 💰 | Cash dividend received |
| **INTEREST** | 📈 | Interest income (bonds, P2P) |
| **FEE** | 💸 | Broker fee or platform charge |
| **DEPOSIT** | ⬇️ | Cash deposited into the broker account |
| **WITHDRAWAL** | ⬆️ | Cash withdrawn from the broker account |
| **ADJUSTMENT** | 🔧 | Manual correction to quantity or price |
| **TRANSFER** | 🔄 | Asset moved between two of your brokers (composite) |
| **FX_CONVERSION** | 💱 | Currency exchange within a broker (composite) |

See [Financial Theory → Transaction Types](../../financial-theory/instruments/transaction-types/index.md) for the conceptual definition of each type.

---

## 📋 Common Fields

These fields appear for **all** transaction types:

| Field | Required | Description |
|-------|:--------:|-------------|
| **Type** | ✅ | Transaction type selector |
| **Date** | ✅ | Execution date (YYYY-MM-DD) |
| **Currency** | ✅ | Currency of the transaction |
| **Amount** | ✅ | Total gross amount |
| **Fee** | ❌ | Brokerage commission or tax withheld |
| **Notes** | ❌ | Free-text memo |

---

## 🏦 Asset Operations (BUY / SELL / TRANSFER)

When an asset is involved, additional fields appear:

| Field | Required | Description |
|-------|:--------:|-------------|
| **Asset** | ✅ | The asset being traded (searchable) |
| **Quantity** | ✅ | Number of units |
| **Unit Price** | ✅ | Price per unit |

!!! tip "Auto-calculation"

    If you fill in **Quantity** and **Unit Price**, the **Amount** is computed automatically, and vice versa.

---

## 💰 WAC Preview

For **BUY** and **SELL** transactions, a **WAC (Weighted Average Cost) preview** panel appears below the main fields. It shows in real-time:

- The **current cost basis** before this transaction
- The **projected new cost basis** after saving
- The **realized gain/loss** (SELL only)

This preview is computed live — no need to save first.

!!! note "Manual WAC Override"

    You can switch the WAC mode from **Auto** (computed by LibreFolio) to **Manual** (enter your own cost basis). This is useful when migrating historical data from another system.

---

## 🔄 Composite Transactions

**TRANSFER** and **FX_CONVERSION** are *composite* — they link two legs:

- **TRANSFER**: specifies a **source broker** and a **destination broker**, plus the asset and quantity. LibreFolio records both legs atomically.
- **FX_CONVERSION**: specifies the **source currency amount** and the **destination currency amount** within the same broker.

To split a composite back into two independent transactions, use the [Split](index.md#split) operation on the transaction table.

---

## ✅ Validation

The form validates on save:

- Dates must be in valid range (not in the future by default).
- Quantity and price must be positive.
- For SELL: quantity cannot exceed the current holding (warning, not a hard block).
- Amount must match quantity × price within a small tolerance.

---

## 🔗 Related

- 📋 **[Transaction Table](index.md)** — List view, filtering, bulk operations
- 📥 **[Import from Broker](import/index.md)** — Skip manual entry with BRIM import
