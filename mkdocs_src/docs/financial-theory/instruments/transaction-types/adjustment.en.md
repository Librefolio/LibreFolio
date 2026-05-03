# ![](../../../static/icons/transactions/adjustment.png){: width="32" style="vertical-align: middle;" } Adjustment

**Adjustments** are a catch-all transaction type for manual corrections to either cash or asset balances. Unlike the paired types (Transfer, Cash Transfer, FX Conversion), adjustments are **standalone** — each adjustment is a single, independent row.

---

## 🔑 Key Properties

| Property | Value |
|----------|-------|
| **Code** | `ADJUSTMENT` |
| **Cash effect** | Optional (± any amount) |
| **Asset effect** | Required (± any quantity) |
| **Paired** | ❌ No (standalone) |
| **Tax event** | No |

---

## 📊 Use Cases

Adjustments are used when no other transaction type fits:

- **Correcting import errors** — e.g., a broker import missed a corporate action
- **Stock splits / reverse splits** — adjust quantity without cash movement
- **Gifts** — receiving or giving shares
- **Initial balance setup** — bootstrapping a portfolio from a snapshot
- **Corporate actions** not covered by other types (spinoffs, mergers, etc.)

!!! note "Promote to Transfer"

    Two `ADJUSTMENT` rows with **opposite quantities**, **same asset**, and **different brokers** can be **promoted** to an Asset Transfer pair. This is useful when you initially recorded separate adjustments and later want to link them as a transfer.

---

## 📐 Impact on Cost Basis

Adjustments with positive quantity **increase** the lot count (FIFO). The cost basis for adjustment-created lots depends on whether a `cost_basis_override` is provided:

- **With override**: the specified amount is used as the lot cost
- **Without override**: the lot is created with zero cost (free acquisition)

---

## 🔗 Related

- 🔄 **[Asset Transfer](transfer.md)** — Two linked adjustments can be promoted to a transfer
- 🛒 **[Buy & Sell](buy-sell.md)** — Standard asset transactions with cash
- 💰 **[Fee & Tax](fee.md)** — Cash-only corrections (use Fee/Tax instead of Adjustment)

