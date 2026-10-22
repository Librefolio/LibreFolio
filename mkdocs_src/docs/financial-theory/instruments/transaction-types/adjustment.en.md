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

Adjustments with negative quantity **decrease** the position: units given away, sent to an account LibreFolio does not track, or removed by a correction. Such an adjustment **has no value** — it only lowers the quantity — so it takes no **Cost Basis Override**:

- **Capital and returns**: no capital leaves, so the adjustment is no flow for the [capital baseline](../../technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#outgoing-adjustments), TWRR or MWRR: the value of the units leaves the NAV, and the returns read it as a loss.
- **Average cost**: the position gives up the average cost of those units, so the average cost (WAC) of what remains does not change.
- **Realized**: the units leave at **zero**, so the adjustment realizes minus their cost, $-q \times \text{AverageCost}$ on the Dashboard. The FIFO lots consume the broker's open lots oldest first, as a sale does, and close them at zero: $q$ units taken from a lot realize $-q \times \text{LotUnitCost}$, with no proceeds.

To record units that left for money, use a **Sell**. The API refuses a cost basis on an outgoing adjustment (`costBasisNotAllowed`); one stored on such a row by an earlier version stays in the database but is ignored. An adjustment linked to a **split** is the exception: the split only spreads the cost already held over the new quantity, and realizes nothing.

!!! example "Two shares given away"

    Every amount is in the report currency. Buy 10 shares at 50 (invested 500); the price rises to 80, so the position is worth 800 and its Total P&L is $800 - 500 = +300$. An adjustment of −2 shares gives two away:

    - 8 shares remain, worth $8 \times 80 = 640$; the invested capital stays 500 and the average cost 50;
    - realized: $0 - 2 \times 50 = -100$; unrealized: $8 \times (80 - 50) = +240$;
    - Total P&L: $640 - 500 = +140$, that is $-100 + 240$;
    - the day's TWRR: $640 / 800 - 1 = -20\%$, since no flow offsets the value that left.

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

