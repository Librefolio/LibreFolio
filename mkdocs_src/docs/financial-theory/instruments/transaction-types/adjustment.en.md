# 🧮 ![](../../../static/icons/transactions/adjustment.png){: width="32" style="vertical-align: middle;" } Adjustment

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="form-modal-adjustment" alt="Transaction Form — Adjustment">
</div>

**Adjustments** are standalone asset-quantity corrections. They are cashless in the shipped transaction schema: quantity changes, cash does not. Unlike paired types (Transfer, Cash Transfer, FX Conversion), each adjustment is a single, independent row.

---

## 🔑 Key Properties

| Property | Value |
|----------|-------|
| **Code** | `ADJUSTMENT` |
| **Cash effect** | None — `ADJUSTMENT` is cashless |
| **Asset effect** | Required (± any quantity) |
| **Tax event** | No |

---

## 📊 Use Cases

Adjustments are used when no other transaction type fits:

- **Correcting import errors** — e.g., a broker import missed a corporate action
- **Stock splits / reverse splits** — adjust quantity without cash movement
- **Gifts** — receiving or giving shares
- **Inherited or succession holdings** — securities arrive in-kind, with no broker cash movement
- **Initial balance setup** — bootstrapping a portfolio from a snapshot
- **Corporate actions** not covered by other types (spinoffs, mergers, etc.)

Imported examples: Intesa Sanpaolo `patrimonio` snapshots use positive `ADJUSTMENT`s to seed existing holdings with a per-unit `cost_basis_override`; Crédit Agricole Italia succession rows (`GIRO ALTRO DOSSIER`, `VERS.TITOLI`) are also modeled as positive cashless `ADJUSTMENT`s, not as paired `TRANSFER`s, because the source dossier is outside LibreFolio.

!!! note "Promote to Transfer"

    Two `ADJUSTMENT` rows with **opposite quantities**, **same asset**, and **different brokers** can be **promoted** to an Asset Transfer pair. This is useful when you initially recorded separate adjustments and later want to link them as a transfer.

---

## 📐 Impact on Cost Basis

Adjustments with positive quantity **increase** the lot count (FIFO). The cost basis
for adjustment-created lots depends on whether a **Cost Basis Override** is provided:

- **With override**: the specified value is used as the **per-unit acquisition cost** (WAC — Weighted Average Cost)
- **Without override**: the lot is created with zero cost (free acquisition — e.g. gifts, airdrops)

!!! info "Per-unit value"

    The Cost Basis Override is the average cost **per single unit** of the asset.
    To get the total cost of the transferred block, multiply by the quantity:

    $$\text{Total cost} = \text{WAC} \times \text{quantity}$$

### 🏦 Automatic Cost Basis on Transfers and Seeds

When transferring assets between brokers, LibreFolio **automatically computes** the Cost Basis Override on the receiving side using the **Weighted Average Cost (WAC)** of the source broker's position. Broker-import seeds may set it directly from the source report instead. The value is always **per unit**, not the total position value; for a snapshot with total fiscal value \(C\) and quantity \(q\), plugins store:

$$\text{Cost Basis Override} = \frac{C}{q}$$

This records in-kind capital, not P&L: the adjustment creates/changes lots but does not create a cash contribution or realised gain.

!!! tip "Learn more"

    For the full formula, examples, and edge cases, see the dedicated page:
    **[📊 Weighted Average Cost (WAC)](../../technical-analysis/performance-metrics/weighted-average-cost.md)**

??? note "✏️ When to Override Manually"

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

- 📊 **[Weighted Average Cost (WAC)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — How automatic cost basis is computed
- 🔄 **[Asset Transfer](transfer.md)** — Two linked adjustments can be promoted to a transfer
- 🛒 **[Buy & Sell](buy-sell.md)** — Standard asset transactions with cash
- 💰 **[Fee & Tax](fee.md)** — Cash-only corrections (use Fee/Tax instead of Adjustment)

