# 📊 Weighted Average Cost (WAC)

## 💡 What is WAC?

The **Weighted Average Cost** (WAC) is the average unit cost of an asset in a portfolio, weighted by the quantity acquired at each price.

It answers the question: _"On average, how much did I pay per unit for this asset?"_

!!! info "Other names"

    - **PMC** — Prezzo Medio di Carico (Italy)
    - **ACB** — Average Cost Basis (Canada, US)
    - **CMP** — Coût Moyen Pondéré (France)

## 🧮 Formula

The WAC is computed **iteratively** as each transaction is processed chronologically:

$$
WAC_{new} = \frac{WAC_{current} \times Q_{pool} + Cost_{unit} \times Q_{tx}}{Q_{pool} + Q_{tx}}
$$

Where:

- $WAC_{current}$ = current weighted average cost before this transaction
- $Q_{pool}$ = total quantity held in the pool before this transaction
- $Cost_{unit}$ = per-unit acquisition cost of the new transaction — what was actually paid, in the currency the WAC is kept in, converted at the rate of the transaction's own date (see [Multi-Currency Handling](#multi-currency-handling))
- $Q_{tx}$ = quantity added by the new transaction

Equivalently, LibreFolio keeps the pool's total cost $C_{pool}$ next to its quantity, with $WAC = C_{pool} / Q_{pool}$: an acquisition adds its cost, a reduction of $q$ units removes $C_{pool} \cdot q / Q_{pool}$.

## ⚙️ How LibreFolio Computes WAC

LibreFolio uses an **inventory-aware iterative algorithm** that processes all qualifying transactions for a given (broker, asset) pair in chronological order. The same algorithm serves every screen that shows an average cost: the Dashboard, the Positions table, the lots analysis and the transaction preview.

### 🏷️ Transaction Effects

Each transaction contributes to the WAC computation in one of these ways:

| Effect | Condition | Impact on WAC |
|--------|-----------|---------------|
| **Weighted** | `qty > 0` with a known cost above zero | WAC moves toward the new acquisition cost |
| **Quantity reduced** | `qty < 0` | Exits at current WAC — WAC unchanged, pool shrinks |
| **Dilution** | `qty > 0` at zero cost | Pool grows, numerator unchanged → WAC **decreases** |
| **Split** | Adjustment linked to a split event | Quantity rescaled, total cost unchanged → WAC divided by the split ratio |
| **Unknown cost** | `qty > 0` with no known cost: a transfer or adjustment without cost basis override | Pool grows without cost — the WAC is **incomplete** (see [Cost Basis Override](#cost-basis-override)) |

### 📅 Same-Day Ordering

When multiple transactions occur on the same date:

1. **Additions first** (qty > 0) — processed before reductions
2. **Reductions second** (qty < 0) — ensures the pool doesn't go transiently negative

### 🔻 Pool Depletion

- When the quantity reaches 0, the last reduction takes the **whole** remaining cost, so total cost is conserved exactly; the pool restarts from zero, and a later purchase opens a new, complete pool
- A reduction larger than the pool is clamped to the quantity available

## 📝 Practical Examples

??? example "Example 1: Two Buys — WAC rises"

    | Date | Type | Qty | Unit Cost | Pool Qty | WAC |
    |------|------|-----|-----------|----------|-----|
    | Apr 1 | BUY | 10 | $150 | 10 | $150.00 |
    | Apr 15 | BUY | 5 | $180 | 15 | $160.00 |

    $$
    WAC = \frac{150 \times 10 + 180 \times 5}{10 + 5} = \frac{2400}{15} = 160.00
    $$

    The second buy at a higher price **pulls the WAC up**.

??? example "Example 2: Buy then Sell — WAC unchanged"

    | Date | Type | Qty | Unit Cost | Pool Qty | WAC |
    |------|------|-----|-----------|----------|-----|
    | Apr 1 | BUY | 10 | $150 | 10 | $150.00 |
    | Apr 15 | SELL | -5 | (at WAC) | 5 | $150.00 |

    The SELL removes units at the current WAC ($150). The WAC stays **unchanged** — only the pool shrinks.

??? example "Example 3: Zero-Cost Acquisition — Dilution"

    | Date | Type | Qty | Unit Cost | Pool Qty | WAC |
    |------|------|-----|-----------|----------|-----|
    | Apr 1 | BUY | 10 | $150 | 10 | $150.00 |
    | May 1 | ADJUSTMENT | +5 | $0 | 15 | $100.00 |

    $$
    WAC = \frac{150 \times 10 + 0 \times 5}{10 + 5} = \frac{1500}{15} = 100.00
    $$

    The WAC is **diluted** because 5 units entered at zero cost — an adjustment whose cost basis override is zero, such as an airdrop. A 3-for-2 split linked to its split event reaches the same $100.00 without any acquisition: the pool keeps its $1,500 and spreads it over 15 units.

## 🔄 Cost Basis Override {: #cost-basis-override }

For transfers and adjustments, LibreFolio supports a **cost basis override**: a unit cost, in a currency of your choice, that represents the historical cost of the units coming in. A transfer or adjustment that adds quantity needs one: the transaction form requires it.

**When set (manual mode):**

- The transaction enters the WAC computation as a normal weighted acquisition costing $\text{override} \times Q_{tx}$, converted at the transaction date like any purchase
- This preserves cost continuity across brokers (e.g., when transferring from broker A to broker B)
- An override of **zero** is a free acquisition: the dilution of Example 3

**When missing:**

- The cost of those units is **unknown**, not zero: they enter the pool without any cost, and the WAC stays incomplete until the position is closed
- The Dashboard shows that position's average cost and unrealized P&L as unavailable and warns about the missing cost basis; the transaction preview counts the units at zero (dilution)

**When auto mode (`cost_basis_mode = "auto"`):**

- LibreFolio computes the WAC of the source position at the transaction date — the sending broker's position for a transfer, the position itself (without this transaction) for an adjustment — and stores it as the override
- From then on the transaction is an ordinary weighted acquisition at that unit cost. For an adjustment on the same position, the WAC therefore stays algebraically unchanged, in the currency it was computed in:

$$
WAC_{new} = \frac{WAC \times Q_{pool} + WAC \times Q_{tx}}{Q_{pool} + Q_{tx}} = WAC
$$

!!! tip "Auto mode in the UI"

    In the transaction form, the **Auto** toggle computes the value when you validate: the preview shows the suggested WAC and the transactions it comes from, each with its effect.

??? example "Example 4: Transfer in Auto Mode — the cost follows the units"

    Broker A holds the pool of Example 1 and sends 3 units to broker B, which held none:

    | Broker | Date | Type | Qty | Unit Cost | Pool Qty | WAC |
    |--------|------|------|-----|-----------|----------|-----|
    | A | Apr 1 | BUY | 10 | $150 | 10 | $150.00 |
    | A | Apr 15 | BUY | 5 | $180 | 15 | $160.00 |
    | A | May 1 | TRANSFER out | −3 | (at WAC) | 12 | $160.00 |
    | B | May 1 | TRANSFER in (auto) | +3 | $160 (A's WAC) | 3 | $160.00 |

    In **auto mode** the receiving side takes the sender's WAC as its cost basis override: broker B starts at broker A's average, and the $480 of cost moves with the 3 units.

## 🌍 Multi-Currency Handling {: #multi-currency-handling }

The WAC is kept in a single currency, the **target currency** $T$, and every acquisition enters it at its **historical cost**: the amount actually paid, converted at the rate of the acquisition's own date $d_i$:

$$
c_i^{T} = P_i \cdot \mathrm{fx}\bigl(\mathrm{ccy}(P_i),\, T,\, d_i\bigr), \qquad \mathrm{fx}(T, T, d) = 1
$$

Here $P_i$ is the cash paid for a BUY, in its cash currency, or $\text{override} \times Q_{tx}$ in the override's currency for a transfer or adjustment. An amount already in $T$ needs no rate at all; otherwise, when the exact date has no rate, the latest rate before it is used.

The cost basis of a position is then

$$
\mathrm{CB}(a,b,t) = q(a,b,t) \times \mathrm{WAC}^{T}(a,b,t)
$$

with **no exchange rate at $t$**: it is what was paid, and it does not move when exchange rates move. For an asset priced in another currency, the exchange-rate effect therefore sits in the unrealized gain/loss — market value at the day's rate minus historical cost — where the Dashboard splits it out (see [Period P&L](portfolio-engine/period-pnl.md#unrealized-change-by-currency)).

The target currency depends on where the WAC is shown:

| Where | Target currency $T$ |
|-------|---------------------|
| Dashboard, Positions table, realized sales, Yield on Cost | The display (report) currency |
| Lots analysis WAC lines | The currency of the analysis |
| Transaction preview, automatic cost basis, WAC series (`POST /portfolio/wac`) | The currency picked in the preview, otherwise the currency of the **latest acquisition** |
| PAC planner | The planner's currency |

The latest acquisition's currency is the currency paid by the most recent transaction that added quantity — a deterministic rule; on a tie, the first one recorded wins. A split, or an acquisition of unknown cost, falls back to the asset's own currency.

??? example "Example 5: A dollar asset bought with euro, display currency EUR"

    | Date | Type | Qty | Paid | Rate USD→EUR | Cost in EUR |
    |------|------|-----|------|--------------|-------------|
    | Apr 1 | BUY | 10 | €400 | — (paid in EUR) | €400.00 |
    | May 1 | BUY | 5 | 300 USD | 0.90 | €270.00 |

    $$
    WAC^{EUR} = \frac{400 + 270}{10 + 5} = \frac{670}{15} \approx 44.67 \text{ EUR}
    $$

    The first purchase needs no rate: its cost is exactly the €400 paid. The position's cost basis stays €670 whatever the dollar does afterwards; a weaker dollar lowers the market value in euro and shows up as an unrealized loss.

!!! warning "FX Rate Availability"

    When no rate exists on or before an acquisition date, LibreFolio never counts that cost as zero. The units enter the pool without their cost and the WAC is marked incomplete: the transaction preview shows no WAC and lists the missing pair with its dates, the Dashboard shows the position's average cost and unrealized P&L as unavailable, and the lots analysis leaves those days out of its WAC lines. The UI warns about the missing FX pairs and provides quick-actions to add or sync them.

## 🎯 Where WAC is Used in LibreFolio

- **Cost basis**: $\text{CB}(a,b,t) = q(a,b,t) \times \text{WAC}^{T}(a,b,t)$, historical, with no conversion at $t$
- **Realized P&L on SELL**: $\text{realized} = P_{\text{sell}} - q_{\text{sold}} \times \text{WAC}^{T}_{\text{pre-sell}}$, with the proceeds $P_{\text{sell}}$ converted at the sale date and the units sold leaving at their historical cost
- **Cash pool decomposition**: SELL returns $C = q_{\text{sold}} \times \text{WAC}^{T}_{\text{pre-sell}}$ to Capital Pool
- **Yield on Cost**: the average purchase price of the [Yield on Cost](portfolio-engine/yield-on-cost.md) denominator
- **Transfer form**: auto-suggests the receiving side's cost_basis_override from the sending position's WAC

!!! warning "WAC is never used for asset valuation"

    WAC is an accounting construct for cost basis. Market value uses the unified resolver tiers: `MARKET → TRADE_AVG → CARRIED → MISSING`, exposed to portfolio rows as `MARKET_PRICE`, `LAST_TRADE_PRICE`, or `MISSING`. See [Price Resolution](portfolio-engine/price-resolution.md).

## ⚙️ Implementation: Position-Level Scope

WAC is maintained **per position** $(a, b)$ — i.e., per (asset, broker) pair. The same asset held on two brokers has two independent WAC pools.

$$
\text{WAC}(a, b_1, t) \neq \text{WAC}(a, b_2, t) \quad \text{in general}
$$

The average cost of every position in a report is computed **once, before the daily replay**, with all the conversions it needs batched into a single request to the FX service; the daily replay then follows each position's pool step by step instead of recomputing it, and never converts a cost itself.

### 📅 Same-day transaction ordering

Within the same date, **additions are processed before reductions**:

$$
\text{BUY}_1, \text{BUY}_2, \ldots \quad \text{then} \quad \text{SELL}_1, \text{SELL}_2, \ldots
$$

This prevents transient negative quantities and ensures SELL always reads the correct WAC that includes same-day BUYs.

## 🔗 Related

- 🔬 **[FIFO Lot Analysis](fifo-engine/fifo-lot-analysis.md)** — Per-lot complement: tracks each acquisition batch individually instead of blending them into one average
- 🔁 **[Buy & Sell](../../instruments/transaction-types/buy-sell.md)** — Transactions that feed the WAC pool
- 📈 **[NAV / Net Worth](portfolio-engine/nav.md)** — How WAC-based book value differs from market-price NAV
- 📖 **[Book Value](portfolio-engine/book-value.md)** — Open cost basis: the sum of historical costs
- ⚖️ **[WAC & Cost Basis (Developer Manual)](../../../developer/backend/transactions/wac.md)** — The single average-cost implementation and its callers
