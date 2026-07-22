# 🔬 FIFO Lot Analysis

FIFO lot analysis is the **per-lot** complement to [Weighted Average Cost (WAC)](../weighted-average-cost.md).

WAC answers: _"What is my blended average cost for this position?"_ FIFO lot analysis answers a different question: _"How is each individual purchase batch performing through time?"_

Instead of merging all acquisitions into one pool, LibreFolio tracks each lot through its own lifecycle — **open**, **partially closed**, **fully closed** — and matches sells in **FIFO** order (first in, first out).

!!! info "Complement, not replacement"

    WAC is aggregate and position-level. FIFO lot analysis is granular and lot-level. Both views are useful: one for blended cost basis, one for economic attribution lot by lot.

---

## 💡 What is FIFO Lot Analysis?

A **lot** is one acquisition batch: for example, one BUY of 100 shares, or one transfer-in that preserves historical cost basis.

When a SELL occurs, the oldest still-open lots are closed first. This creates a lot-by-lot history:

- how much of each lot is still open
- how much has already been sold
- how much sale proceeds that lot has generated
- how much income was earned while that lot was held
- how much return came from price change versus cash income

This makes FIFO lot analysis especially useful when two positions in the same asset were bought at very different prices or dates.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-gantt-chart" alt="Lot Life & Custody timeline — each bar is one lot, colored by custodian broker, thickness proportional to held quantity">
</div>

The **Lot Life & Custody** timeline above makes the lifecycle visual: each bar is one lot, colored by the broker currently holding it, with thickness proportional to the quantity still held in that segment. A bar that ends mid-chart is a fully closed lot; a bar reaching "today" is still open.

---

## 🧮 Open Return per Lot

**Open Return** isolates the **price-only** move of a lot relative to its opening reference price.

$$
\text{RelativeReturn} = \frac{\text{MarketPrice}}{\text{ReferenceUnitPrice}} - 1
$$

In practice:

- if a market quote exists at the lot's opening date, that opening quote becomes `reference_unit_price`
- if the lot opened before the first available market quote, the system falls back to the lot's own opening cost, scaled to market quote units

This metric excludes dividends, interest, and realized sale proceeds. It answers: _"How much has market price moved since this lot was opened?"_

!!! tip "Reference price fallback"

    When no opening-day market quote exists, LibreFolio uses the lot's acquisition price as the reference base, scaled to the asset's quote convention. This avoids misleading percentage returns on instruments quoted per 100 nominal units.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-wac-chart" alt="WAC / Market Price chart — one bubble per lot, colored by opening broker, sized by opening value, plotted against the market price line">
</div>

The **WAC / Market Price** chart plots each lot as a bubble against the market price line: bubble color marks the broker where the lot was opened, bubble size scales with the lot's opening value. A lot valued only at cost (no live market price) is drawn with a dashed outline.

---

## 💰 Total Return per Lot

**Total Return** is broader than Open Return. It includes the lot's remaining market value, any sale proceeds already realized from that lot, and any allocated income received while the lot was held.

LibreFolio's lot math uses these exact building blocks:

$$
\text{OpeningValue} = \text{OriginalCost}
$$

$$
\text{Proceeds}(t) = \sum \text{Closure Proceeds} \text{ up to } t
$$

$$
\text{TotalValue}(t) = \text{OpenValue}(t) + \text{Proceeds}(t)
$$

$$
\text{PnL}(t) = \text{TotalValue}(t) - \text{OriginalCost}
$$

$$
\text{MarketPnL} = \text{PnL} - \text{RealizedPnL}
$$

$$
\text{RealizedPnL} = \sum \text{Closure Realized PnL}
$$

$$
\text{AssetIncome} = \sum_t \text{Income}_i(t)
$$

$$
\text{TotalPnL} = \text{MarketPnL} + \text{RealizedPnL} + \text{AssetIncome}
$$

For the scalar lot summary, the return percentage is:

$$
\text{TotalReturn} = \frac{\text{TotalPnL}}{\text{OpeningValue}}
$$

For return history through time, LibreFolio uses:

$$
\text{TotalReturn}(t) = \frac{\text{TotalValue}(t) + \text{Income}(t)}{\text{OriginalCost}} - 1
$$

This answers: _"What is full economic return of this lot, including both price movement and cash yield?"_

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" alt="Value / Return comparison chart in Return mode — percentage return per lot from each lot's own opening date">
</div>

The **Value / Return** comparison chart, switched to **Return** mode, plots exactly this percentage — one line per lot, each measured from its own opening date, over the currently selected lot set.

---

## ⚙️ qbq Scaling

Some instruments are quoted **per base quantity**, not per single unit. LibreFolio calls this base quantity `qbq` (`quote_base_quantity`).

- For most stocks, `qbq = 1`
- For many bonds, `qbq = 100`

The exact valuation rule is:

$$
\text{HoldingValue}(qty, price, qbq) = \left(\frac{qty}{qbq}\right)\cdot price
$$

$$
\text{OpenValue}(t) = \left(\frac{\text{OpenQuantity}(t)}{qbq}\right)\cdot \text{MarketPrice}(t)
$$

!!! warning "qbq scaling matters"

    Suppose a bond has face quantity 1,000 and is quoted at **101.50 per 100 nominal**.

    - `qbq = 100`
    - lot quantity = `1,000`
    - market value = `(1,000 / 100) × 101.50 = 1,015.00`

    If you compare `101.50` directly with a per-single-unit cost basis such as `0.992`, you get nonsense because the two numbers live on different scales.

    The correct comparison rescales the lot cost onto the market quote axis:

    $$
    0.992 \times 100 = 99.20
    $$

    So the meaningful price comparison is **101.50 vs 99.20**, not **101.50 vs 0.992**.

Without this scaling, bond returns and valuations can be off by orders of magnitude.

---

## 🛟 Estimated-at-Cost

If no live market price is available for an asset, LibreFolio does **not** fail the analysis. Instead, it temporarily values the still-open portion of the lot at cost:

$$
\text{OpenValue} = \text{OpeningValue}\cdot \frac{\text{OpenQuantity}}{\text{OriginalQuantity}}
$$

$$
\text{MarketPnL} = 0
$$

Practical implication:

- the lot still shows residual value
- already realized proceeds still remain visible
- allocated dividends or interest still remain visible
- **unrealized volatility is temporarily understated**

!!! info "Interpretation"

    Estimated-at-cost is conservative operational fallback. It means: _"We know what you paid, but we do not currently know what market would pay."_

---

## 💸 Income Allocation Across Lots {: #income-allocation-across-lots }

Dividends and interest linked to an asset are allocated **pro-rata across the LONG lots that are eligible as
of the day before the income date (D-1)**, and only across lots held **at the paying broker**.

Exact allocation rule:

$$
w_i(D) = \frac{\text{EligibleQty}_i(D)}{\sum_j \text{EligibleQty}_j(D)}, \qquad
\text{EligibleQty}_i(D) = \text{OpenQty}_i(D-1)
$$

$$
\text{Income}_i = \text{Convert}(I, ccy, D)\cdot w_i(D)
$$

Where:

- $I$ = income amount received on date $D$
- $\text{Convert}(I, ccy, D)$ = income converted into target currency on date $D$
- $\text{EligibleQty}_i(D)$ = quantity of lot $i$ open at the **paying broker** on $D-1$ (quantity that left
  that broker in transit still counts as originating there)
- only LONG lots participate in the denominator

The **D-1** rule keeps the day of record clean: a purchase made *on* the income date does not earn that
distribution, and a lot sold the day before does not either. Larger eligible lots receive a larger share;
lots held at other brokers, or not yet (or no longer) eligible, receive nothing.

!!! warning "Changed in FIFO v5"

    Earlier versions used the income date itself with **all** brokers ($\text{OpenQty}_i(t)$ over every lot).
    The current engine uses D-1 eligibility scoped to the paying broker. If no lot is eligible, the income is
    kept as **asset-level orphan income** (never dropped, never assigned to the wrong lot).

!!! tip "Conservation rule"

    The allocated lot amounts add back exactly to the converted income event total. Income is distributed, not created.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-custody-modal" alt="Lot detail modal — Asset Income row shows the pro-rata dividend/interest allocated to this specific lot, alongside the Estimated-at-Cost badge when no live market price is available">
</div>

The lot detail modal's **Asset Income** row is exactly $\text{Income}_i$ from the formula above — the pro-rata slice this specific lot received. When the lot has no live market price, the same modal also shows the **Estimated-at-Cost** badge from the previous section.

---

## 💸 Costs & Net Metrics {: #costs-and-net-metrics }

Asset-linked `FEE` and `TAX` are allocated to lots with a **deterministic operation-matching ladder**, then
subtracted to produce **net** figures alongside the gross ones.

### Deterministic cost allocation

A cost pool (same broker, same day, same type) is matched to the first non-empty target in this order:

| Cost | Matching order |
|------|----------------|
| `FEE` | same-day trades → previous-day trades → open holdings → asset orphan |
| `TAX` | same-day income → same-day trades → previous-day income → previous-day trades → open holdings → asset orphan |

Within a matched trade the cost **crosses to the very lots that trade touched** — a BUY's cost lands on the
lot it opened, a SELL's cost lands on the FIFO-consumed lots — so cost attribution never contradicts the FIFO
matching itself. Amounts are converted to the target currency and stored as positive magnitudes.

!!! tip "Conservation"

    Per pool, $\sum_i \text{Cost}_i + \text{Orphan} = \text{Convert}(\text{pool}, ccy, D)$. A cost that finds
    no eligible lot (e.g. a fee booked after the position is fully closed) becomes **asset-level orphan cost**
    rather than being dropped or forced onto an unrelated lot.

### Gross vs net

With costs attributed per lot, LibreFolio reports both gross and net performance:

$$
\text{NetTotalPnL}_i = \text{TotalPnL}_i - \text{Fees}_i - \text{Taxes}_i
$$

$$
\text{NetTotalReturn}_i = \frac{\text{NetTotalPnL}_i}{\text{OpeningValue}_i}
$$

where $\text{TotalPnL}_i$ already **includes** income (market P&L + realized P&L + asset income). The per-lot
value-history series instead reports a *capital-only* net P&L, $\text{pnl}_i - \text{Fees}_i - \text{Taxes}_i$,
which **excludes** income — each net line mirrors its own gross counterpart minus costs.

!!! example "Canonical numbers"

    BUY 10×100, SELL 4×120, current price 110, dividend 50, fees 8, taxes 5:
    Gross Total P&L $= 60 + 80 + 50 = 190$; Net Total P&L $= 190 - 13 = 177$; on opening value 1000 that is a
    **19%** gross vs **17.7%** net total return.

Costs with `asset_id = null` are **not** part of this lot-level view — they are portfolio-level and handled
by the [Portfolio Engine](../portfolio-engine/roi.md). See
[Fee & Tax](../../../instruments/transaction-types/fee.md) for the instrument-level theory.

---

## 📝 Worked Example

??? example "Example: two lots, one dividend, one market price"

    Assume same stock, same currency, `qbq = 1`.

    | Date | Event | Lot A Open Qty | Lot B Open Qty | Notes |
    |------|-------|----------------|----------------|-------|
    | Jan 2 | BUY 100 @ $10 | 100 | 0 | Lot A opens with original cost $1,000 |
    | Feb 10 | BUY 50 @ $14 | 100 | 50 | Lot B opens with original cost $700 |
    | Mar 15 | DIVIDEND $30 | 100 | 50 | Both lots are still open |
    | Apr 1 | Market price = $16 | 100 | 50 | Evaluate both lots |

    **Step 1 — Allocate dividend pro-rata**

    $$
    w_A = \frac{100}{100 + 50} = \frac{2}{3}
    \qquad
    w_B = \frac{50}{100 + 50} = \frac{1}{3}
    $$

    $$
    \text{Income}_A = 30 \times \frac{2}{3} = 20
    \qquad
    \text{Income}_B = 30 \times \frac{1}{3} = 10
    $$

    **Step 2 — Open Return for each lot**

    $$
    \text{RelativeReturn}_A = \frac{16}{10} - 1 = 60.00\%
    $$

    $$
    \text{RelativeReturn}_B = \frac{16}{14} - 1 \approx 14.29\%
    $$

    **Step 3 — Market value and Total Return**

    $$
    \text{OpenValue}_A = 100 \times 16 = 1,600
    \qquad
    \text{OpenValue}_B = 50 \times 16 = 800
    $$

    Since no shares were sold yet, proceeds and realized P&L are both zero.

    $$
    \text{TotalPnL}_A = (1,600 - 1,000) + 20 = 620
    $$

    $$
    \text{TotalReturn}_A = \frac{620}{1,000} = 62.00\%
    $$

    $$
    \text{TotalPnL}_B = (800 - 700) + 10 = 110
    $$

    $$
    \text{TotalReturn}_B = \frac{110}{700} \approx 15.71\%
    $$

    **Step 4 — Aggregate return across displayed lots**

    $$
    \text{AggregateReturn} = \frac{620 + 110}{1,000 + 700} = \frac{730}{1,700} \approx 42.94\%
    $$

    Even though both lots belong to same asset, their returns differ because they were opened at different prices.

---

## 📚 From Lots to Aggregate Metrics

Lot-level returns can be rolled up into an aggregate return series, but **percentages must not be added directly**.

LibreFolio uses this exact aggregate rule across displayed lots:

$$
\text{AggregatePnL}(t) = \sum_i \left(\text{PnL}_i(t) + \text{Income}_i(t)\right)
$$

$$
\text{AggregateOpeningValue}(t) = \sum_i \text{OriginalCost}_i
$$

$$
\text{AggregateReturn}(t) = \frac{\text{AggregatePnL}(t)}{\text{AggregateOpeningValue}(t)}
$$

This lot-level view helps explain **where** return came from. Higher-level metrics such as [ROI](../portfolio-engine/roi.md) and [TWRR](../portfolio-engine/twrr.md) answer broader portfolio questions:

- **ROI** focuses on gain relative to invested capital
- **TWRR** neutralizes external cash-flow timing
- FIFO lot analysis explains contribution and path **inside** a position

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-table" alt="Unified Lots Table — one row per lot with opening date, total return, current value, custody and status, the exact per-lot rows the aggregate formulas above sum over">
</div>

The **Unified Lots Table** lists exactly the per-lot rows $i$ that the aggregate formulas above sum over — opening date, total return, current value, custody, and status, all filterable to the same visible lot set used by the charts.

---

## 🔗 Related

- 📊 **[Weighted Average Cost (WAC)](../weighted-average-cost.md)** — blended cost basis view
- 🔁 **[Buy & Sell](../../../instruments/transaction-types/buy-sell.md#fifo-matching)** — brief FIFO matching overview
- 💸 **[Dividend & Interest](../../../instruments/transaction-types/dividend-interest.md)** — source of asset-linked income events
- 💰 **[Taxation](../../../fundamentals/taxation.md)** — capital gains and lot matching context
- ⚙️ **[Lots Analysis Service](../../../../developer/backend/transactions/lots_analysis_service.md)** — developer implementation deep-dive
