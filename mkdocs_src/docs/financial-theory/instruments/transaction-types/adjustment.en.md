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

Adjustments with positive quantity **increase** the lot count (FIFO). The cost basis
for adjustment-created lots depends on whether a **Cost Basis Override** is provided:

- **With override**: the specified value is used as the **per-unit acquisition cost** (PMC — Prezzo Medio di Carico)
- **Without override**: the lot is created with zero cost (free acquisition — e.g. gifts, airdrops)

!!! info "Per-unit value"

    The Cost Basis Override is the average cost **per single unit** of the asset.
    To get the total cost of the transferred block, multiply by the quantity:

    $$\text{Total cost} = \text{PMC} \times \text{quantity}$$

### 🏦 Automatic Cost Basis on Transfers

When transferring assets between brokers, LibreFolio **automatically computes** the
Cost Basis Override on the receiving side. The formula is the Weighted Average Cost (WAC):

$$WAC = \frac{\sum_{i} q_i \times p_i}{\sum_{i} q_i}$$

where $q_i$ is the quantity and $p_i$ is the per-unit cost of each acquisition lot
at the **source broker** (from BUY transactions and previous incoming transfers).

### ✏️ When to Override Manually

The automatic formula works for the standard case (same fiscal regime, no tax events
at transfer). In the following scenarios the user must set the value manually:

| Scenario | What to set |
|----------|------------|
| **Normal transfer** | Leave empty — auto-calculated |
| **Exit Tax** | Market value at transfer date (jurisdiction-specific) |
| **Inheritance** | Fair market value at date of death (or stepped-up basis) |
| **Gift** | Donor's original cost basis (carryover basis) |
| **Corporate action** | Adjusted basis per corporate action terms |

!!! warning "User Responsibility"

    When manually overriding the cost basis, the user is responsible for the
    correctness of the value. LibreFolio does not validate override amounts
    against tax rules — consult a tax advisor for jurisdiction-specific guidance.

---

## 🔗 Related

- 🔄 **[Asset Transfer](transfer.md)** — Two linked adjustments can be promoted to a transfer
- 🛒 **[Buy & Sell](buy-sell.md)** — Standard asset transactions with cash
- 💰 **[Fee & Tax](fee.md)** — Cash-only corrections (use Fee/Tax instead of Adjustment)

