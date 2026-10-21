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

$\text{MarketPrice}$ is the asset's mark from the [unified resolver](../portfolio-engine/price-resolution.md): on the end date for the lot summary, on each day for the return history. The reference depends on what opened the lot:

- **A trade** — a BUY, or a SELL that opens a short lot: the lot's own unit price, even when the asset has a market quote that day. A trade is a price.
- **An adjustment** — an opening position, a succession, a transfer from an untracked broker: its cost basis is a cost, not a price, so the reference is the asset's mark on the opening day. That is the price of the last day on or before it that has one — its market quote or, without a quote, the average price of its BUY and SELL trades, never an adjustment — carried forward.
- **An adjustment before any price** — no quote, BUY or SELL on or before its opening day: the lot's own unit price, its per-unit cost basis. Without a cost basis that price is zero, and the lot has no Open Return.

`reference_price_source` is `exact` for a market quote of the opening day itself and for the lot's own price, and `fallback` for a quote carried from an earlier day or a price derived from trades. The data-quality banner reports such a fallback (`REFERENCE_PRICE_FALLBACK`), and an adjustment with no price on or before its opening day (`REFERENCE_PRICE_UNAVAILABLE`).

Each price converts into the target currency at the rate of its own day: $\text{MarketPrice}$ at the rate of the day it values, the reference at the rate of the opening date, even when it was carried from an earlier quote or trade. For a price in another currency than the target, Open Return therefore includes the exchange-rate move since the opening.

This metric excludes dividends, interest, and realized sale proceeds. It answers: _"How much has market price moved since this lot was opened?"_

!!! example "A lot received by succession"

    An asset is quoted at 50 on 7 March and bought at 52 on 9 March, with no quote since. A lot received by succession on 10 March has a reference of **52**: the BUY is the asset's most recent price on or before that day, carried forward. Its `reference_price_source` is `fallback`, since 52 is not a quote of 10 March; a quote on 10 March itself would be the reference, with `exact`.

!!! tip "The lot's own price, on the quote axis"

    When the reference is the lot's own price, LibreFolio scales it to the asset's quote convention. This avoids misleading percentage returns on instruments quoted per 100 nominal units. A mark from the resolver is already on that axis.

    The reference is then $\text{OpeningUnitPrice}\times qbq$. For `qbq = 100`, a bond bought at `0.992` compares against the market quote axis as `99.20`, not `0.992`.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-wac-chart" alt="WAC / Market Price chart — one bubble per lot, colored by opening broker, sized by opening value, plotted against the market price line">
</div>

The **WAC / Market Price** chart plots each lot as a bubble against the market price line: bubble color marks the broker where the lot was opened, bubble size scales with the lot's opening value. A lot whose current value is estimated at cost — its asset has no price at all on the end date, see [Estimated-at-Cost](#estimated-at-cost) — is drawn with a dashed outline.

---

## 💰 Total Return per Lot

**Total Return** is broader than Open Return. It includes the lot's remaining market value, any sale proceeds already realized from that lot — an outgoing adjustment adds none, having no value — and any allocated income received while the lot was held.

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

Every amount is in the analysis's target currency. For a lot bought or sold in another currency, each closure converts its two legs at their own dates — see [Lots in Another Currency](#lots-in-another-currency).

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

### 💱 Lots in Another Currency {: #lots-in-another-currency }

A closure's two legs convert into the target currency **each in its own currency, at its own date**: the cost of the units in the lot's currency at the lot's opening date — the purchase rate — and the closing price in the closing transaction's currency at the closing date — the sale rate. With $\text{Convert}(x, ccy, D)$ the amount $x$ in currency $ccy$ converted into the target currency at the rate of date $D$, a closure of $q$ units of a LONG lot opened on $D_{\text{open}}$ at $\text{LotUnitCost}$ in $ccy_{\text{lot}}$, and closed on $D_{\text{close}}$ at $\text{ClosePrice}$ in $ccy_{\text{close}}$, gives:

$$
\text{Closure Proceeds} = \text{Convert}\left(q \cdot \text{ClosePrice},\ ccy_{\text{close}},\ D_{\text{close}}\right)
$$

$$
\text{Closure Cost} = \text{Convert}\left(q \cdot \text{LotUnitCost},\ ccy_{\text{lot}},\ D_{\text{open}}\right)
$$

$$
\text{Closure Realized PnL} = \text{Closure Proceeds} - \text{Closure Cost}
$$

$\text{ClosePrice}$ is a sale's unit price, in the sale's currency, or zero, in the lot's currency, for an outgoing adjustment, which has no value (see [Outgoing Adjustments](../../../instruments/transaction-types/adjustment.md#outgoing-adjustments)). $ccy_{\text{close}}$ need not be $ccy_{\text{lot}}$: a lot moved to a broker of another currency and sold there converts the sale from that currency. A SHORT lot mirrors the rule: it realizes the proceeds of its opening sale, $\text{Convert}(q \cdot \text{LotUnitCost}, ccy_{\text{lot}}, D_{\text{open}})$, minus the cost of the purchase that closes it, $\text{Convert}(q \cdot \text{ClosePrice}, ccy_{\text{close}}, D_{\text{close}})$.

When a lot is bought and sold in one currency, with rates $r_{\text{open}}$ and $r_{\text{close}}$ on the two dates, its realized result splits into the price gain at the sale rate and the exchange-rate move on the cost of the units sold:

$$
\text{Closure Realized PnL} = q\,(\text{ClosePrice} - \text{LotUnitCost})\,r_{\text{close}} + q\,\text{LotUnitCost}\,(r_{\text{close}} - r_{\text{open}})
$$

The exchange-rate move between purchase and sale is therefore realized with the units, as on the Dashboard, where a sale's proceeds convert at its date and the units leave at their historical cost (see [WAC](../weighted-average-cost.md)). A missing rate leaves the closure's realized P&L unknown, and with it the lot's $\text{RealizedPnL}$: it is never computed from the native amounts.

Every closure's cost converts at the opening date, like $\text{OriginalCost}$, so a LONG lot's market P&L is the value of its open units minus their cost at the purchase rate:

$$
\text{MarketPnL} = \text{PnL} - \text{RealizedPnL} = \text{OpenValue} - \left(\text{OriginalCost} - \sum \text{Closure Cost}\right)
$$

A fully closed LONG lot has no market P&L: its closures' costs add up to its $\text{OriginalCost}$, and its whole P&L is realized.

!!! example "A dollar lot, target currency EUR"

    Buy 1 unit at 100 USD when 1 USD = 1.00 EUR; sell it at 110 USD when 1 USD = 0.90 EUR.

    $$
    \text{Closure Proceeds} = 110 \times 0.90 = 99 \text{ EUR}
    \qquad
    \text{Closure Cost} = 100 \times 1.00 = 100 \text{ EUR}
    $$

    $$
    \text{RealizedPnL} = 99 - 100 = -1 \text{ EUR}
    \qquad
    \text{MarketPnL} = \text{PnL} - \text{RealizedPnL} = (99 - 100) - (-1) = 0
    $$

    The price gain, $10 \times 0.90 = +9$ EUR, is outweighed by the dollar's fall on the cost, $100 \times (0.90 - 1.00) = -10$ EUR. Converting the native realized P&L, 10 USD, at the sale rate would instead report $+9$ EUR realized and $-10$ EUR of market P&L on a lot no longer held; the total, $-1$ EUR, is the same either way.

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

## 🛟 Estimated-at-Cost {: #estimated-at-cost }

Each day, a lot is valued at the asset's mark from the [unified resolver](../portfolio-engine/price-resolution.md): a market quote, or the average price of a day's BUY and SELL trades, carried forward. An adjustment is never a price, with or without a cost basis. A day with **no price at all** — no market quote and no BUY or SELL on or before it — does **not** fail the analysis: LibreFolio values the still-open portion of a LONG lot at cost that day, the day-by-day rule the Dashboard applies to a holding with no price:

$$
\text{OpenValue}(t) = \text{OpeningValue}\cdot \frac{\text{OpenQuantity}(t)}{\text{OriginalQuantity}}
$$

$$
\text{MarketPnL}(t) = 0
$$

with $\text{OpeningValue}$ the lot's original cost converted at its opening date. The choice is made day by day, with no look-ahead. A price, once observed, is carried forward, so these days all come before the asset's first quote, BUY or SELL: they run from the first transaction of the analysis to the day before that first price, or to the end date when the asset has none — and there are none when the asset already has a price on the day of the first transaction.

- **Before the first price.** A lot opened before the asset's first price — by an adjustment, for example — is valued at cost from its opening to the day before that price, even when the asset is priced later: its value line stays flat at cost, with no market gain or loss, then follows the price.
- **No price at all.** An asset with no quote, BUY or SELL up to the end date — one held only through adjustments or transfers — is valued at cost on every day, and the lot summary reports `value_source = ESTIMATED_AT_COST`. With a price on or before the end date, the summary values the lot at that price instead: `value_source = MARKET_PRICE`, the label of any mark, quote or trade.
- **A price without a rate.** A day whose mark has no exchange rate into the target currency is not valued at cost: a still-open lot has no value that day, and on the end date the lot summary has no value and no `value_source`.
- **An adjustment without a cost basis.** Its lot opens at zero cost, so it counts at zero on those days, while the Dashboard's average cost treats that cost as unknown and leaves the holding unvalued. Such a row is rare: a positive [adjustment](../../../instruments/transaction-types/adjustment.md) can be saved without a cost basis only while it is linked to a split, and then opens no lot, so it comes from an older version, or from one whose split event was later changed to a price adjustment.

Practical implication, on the days valued at cost:

- the lot still shows residual value
- already realized proceeds still remain visible
- allocated dividends or interest still remain visible
- **unrealized volatility is temporarily understated**
- `market_pnl = 0`, and no Open Return: there is no market price to compare with the reference
- no ROI or TWRR in the lots performance history, which reads only days with a price

!!! info "Interpretation"

    Estimated-at-cost is conservative operational fallback. It means: _"We know what you paid, but we do not currently know what market would pay."_

The data-quality warning `CURRENT_PRICE_ASSUMED_AT_COST` — *"No market price available between {date_from} and {date_to} — open value estimated at cost, market P&L excluded"* — names exactly those days: from the first transaction to the day before the asset's first price, or to the end date when the asset has none. It is raised whenever such days exist and the lot summary or the value, return, price or performance history is requested.

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

Income keeps its sign: a negative correction of a dividend or interest payment lowers the lot's income, as it
does on the Dashboard.

!!! warning "Changed in FIFO v5"

    Earlier versions used the income date itself with **all** brokers ($\text{OpenQty}_i(t)$ over every lot).
    The current engine uses D-1 eligibility scoped to the paying broker. If no lot is eligible, the income is
    kept as **asset-level orphan income** (never dropped, never assigned to the wrong lot).

!!! tip "Conservation rule"

    The allocated lot amounts add back exactly to the converted income event total. Income is distributed, not created.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-custody-modal" alt="Lot detail modal — Asset Income row shows the pro-rata dividend/interest allocated to this specific lot, alongside the Estimated-at-Cost badge when the lot's current value is estimated at cost">
</div>

The lot detail modal's **Asset Income** row is exactly $\text{Income}_i$ from the formula above — the pro-rata slice this specific lot received. When the lot's current value is estimated at cost — its asset has no price at all on the end date —, the same modal also shows the **Estimated-at-Cost** badge from the previous section.

---

## 💸 Costs & Net Metrics {: #costs-and-net-metrics }

Asset-linked `FEE` and `TAX` are allocated to lots with a **deterministic operation-matching ladder**, then
subtracted to produce **net** figures alongside the gross ones.

### 🧭 Deterministic cost allocation

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

### ⚖️ Gross vs net

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

Annualized lot return uses the **net** return, not the gross one:

$$
\mathrm{AnnualizedReturn}_i =
\left(1+\mathrm{NetTotalReturn}_i\right)^{365/d_i}-1
$$

with $d_i$ from opening date to closing date for closed lots, or to the analysis end date for open lots. Windows below 30 days return no annualized value; see [Net Annualized Return](../portfolio-engine/net-annualized-return.md).

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

Price lookup is deliberately outside the FIFO engine itself. The engine produces lots and closures, and asks for a price only to give a lot opened by an adjustment its reference; `LotsAnalysisService` answers from the unified resolver ([Price Resolution](../portfolio-engine/price-resolution.md)), then applies the same resolver and the estimated-at-cost fallback when deriving valuation metrics.

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
