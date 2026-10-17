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

Imported examples: Intesa Sanpaolo `patrimonio` snapshots use positive `ADJUSTMENT`s to seed existing holdings with a per-unit `cost_basis_override`; Crédit Agricole succession rows (`GIRO ALTRO DOSSIER`, `VERS.TITOLI`) are also modeled as positive cashless `ADJUSTMENT`s, not as paired `TRANSFER`s, because the source dossier is outside LibreFolio.

!!! note "Promote to Transfer"

    Two `ADJUSTMENT` rows with **opposite quantities**, **same asset**, and **different brokers** can be **promoted** to an Asset Transfer pair. This is useful when you initially recorded separate adjustments and later want to link them as a transfer. Neither row may be linked to an asset event, a split for instance: a transfer cannot carry that link, so LibreFolio neither suggests nor accepts such a promote.

---

## 📐 Impact on Cost Basis

Adjustments with positive quantity **increase** the lot count (FIFO). The cost basis
for adjustment-created lots depends on whether a **Cost Basis Override** is provided:

- **With override**: the specified value is used as the **per-unit acquisition cost** (WAC — Weighted Average Cost), in the cost basis's own currency, which is also the currency of the FIFO lot the adjustment opens (not the row's own currency, often empty since an adjustment moves no cash); an override of **zero** records a free acquisition, such as an airdrop
- **Without override**: the FIFO lot opens at zero cost, but the average cost (WAC) treats the cost as **unknown**, not free: the units join the position without a cost, its WAC stays incomplete until the position is closed, the Dashboard shows its average cost and unrealized P&L as unavailable, and a data-quality warning names the asset (see [Cost Basis Override](../../technical-analysis/performance-metrics/weighted-average-cost.md#cost-basis-override))

A positive adjustment cannot be saved without a cost basis: enter one, or choose **Auto**, which stores the average cost of the position the units join (zero if it holds none yet). Two kinds of rows can still lack one: an adjustment linked to a **split**, which Auto saves without one because the split keeps the cost already held and spreads it over the new quantity, and rows saved before the cost basis became mandatory.

!!! info "Per-unit value"

    The Cost Basis Override is the average cost **per single unit** of the asset.
    To get the total cost of the transferred block, multiply by the quantity:

    $$\text{Total cost} = \text{WAC} \times \text{quantity}$$

### 📤 Outgoing Adjustments {: #outgoing-adjustments }

Adjustments with negative quantity **decrease** the position. In the FIFO lots they consume the broker's open lots oldest first, as a sale does. What the units leave with depends, again, on the **Cost Basis Override**:

- **With override**: the units are **handed over at that per-unit cost** — the principle of an incoming adjustment, in the opposite direction. The Dashboard takes the value handed over, $q \times \text{CostBasis}$ converted at the adjustment's date, out of its [capital baseline](../../technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#outgoing-adjustments): capital that leaves, not a loss. The position gives up the average cost of those units, and the difference is realized, as for a sale: in a single currency, $q \times (\text{CostBasis} - \text{AverageCost})$. The FIFO lots do the same: each lot the adjustment consumes closes at the row's per-unit cost — **not** that lot's own FIFO cost — so $q$ units taken from a lot realize $q \times (\text{CostBasis} - \text{LotUnitCost})$, and the value handed over, $q \times \text{CostBasis}$, counts among that lot's proceeds
- **Without override**: the units leave at **zero** — a write-off: each consumed lot realizes minus the cost of those units, with no proceeds. The Dashboard moves no capital and realizes nothing: the units leave the NAV, and their value comes off the Total P&L

!!! example "Two lots, one outgoing adjustment"

    Every amount is in the report currency. Buy 10 units at 10, then 10 units at 20: the average cost is 15. An adjustment of −10 units with a cost basis of 15 consumes the first lot (FIFO) and closes it at 15: the lot realizes $10 \times (15 - 10) = +50$ and hands over $10 \times 15 = 150$. The second lot stays open at 20, so at a price $p$ the lots total $50 + 10 \times (p - 20) = 10 \times (p - 15)$ — the Dashboard's P&L on 10 units with an average cost of 15, where the handover realizes $150 - 150 = 0$.

    With a single lot, buy 10 units at 20 and adjust −4 at 20: nothing is realized, and at a price of 30 the 6 remaining units gain $6 \times (30 - 20) = 60$, on the Dashboard and in the lots alike. Adjust −4 at 30 instead, the market price: the 4 units realize $4 \times (30 - 20) = +40$ on both sides, and the Dashboard's capital drops by the $4 \times 30 = 120$ handed over.

!!! note "Currency of an outgoing cost basis"

    The cost basis applies to every lot the adjustment consumes, whatever its currency: a cost basis without a currency counts in the lot's, a lot without a currency in the report currency. In the report currency the two sides convert each at its own date — the value handed over, $q \times \text{CostBasis}$, from the cost basis's currency at the adjustment's date, the lot's cost from the lot's currency at its opening date — and the lot realizes their difference, the exchange-rate move between the two dates included (see [Lots in Another Currency](../../technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md#lots-in-another-currency)). The Dashboard converts the value handed over the same way, at the adjustment's date — a cost basis without a currency counts in the asset's — and realizes it against the average cost, whose purchases keep the rates of their own dates (see the example in [Deposited Capital](../../technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#outgoing-adjustments)).

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

