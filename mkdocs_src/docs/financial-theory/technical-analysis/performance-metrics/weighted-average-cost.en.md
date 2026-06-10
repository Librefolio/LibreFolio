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
- $Cost_{unit}$ = per-unit acquisition cost of the new transaction
- $Q_{tx}$ = quantity added by the new transaction

## ⚙️ How LibreFolio Computes WAC

LibreFolio uses an **inventory-aware iterative algorithm** that processes all qualifying transactions for a given (broker, asset) pair in chronological order.

### 🏷️ Transaction Effects

Each transaction contributes to the WAC computation in one of these ways:

| Effect | Condition | Impact on WAC |
|--------|-----------|---------------|
| **Weighted** | `qty > 0` and `unit_cost > 0` | WAC moves toward the new acquisition cost |
| **Quantity reduced** | `qty < 0` | Exits at current WAC — WAC unchanged, pool shrinks |
| **Dilution** | `qty > 0` but `unit_cost = 0` | Pool grows, numerator unchanged → WAC **decreases** |
| **Auto WAC** | `qty > 0`, `cost_basis_mode = "auto"` | Pool unchanged — units enter at current WAC |

### 📅 Same-Day Ordering

When multiple transactions occur on the same date:

1. **Additions first** (qty > 0) — processed before reductions
2. **Reductions second** (qty < 0) — ensures the pool doesn't go transiently negative

### 🔻 Pool Depletion

- When `new_qty = 0`: WAC resets to 0 (position closed)
- When `new_qty < 0` (rounding edge case): clamped to 0

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

    The WAC is **diluted** because 5 units entered at zero cost (e.g. stock split, airdrop, gift).

## 🔄 Cost Basis Override

For transfers and adjustments, LibreFolio supports a **cost basis override**: a user-specified unit cost that represents the historical cost of the transferred units.

**When set (manual mode):**

- The transaction enters the WAC computation as a normal weighted acquisition
- This preserves cost continuity across brokers (e.g., when transferring from broker A to broker B)

**When not set (no mode specified):**

- The transaction enters with `unit_cost = 0` (dilution effect)
- This is appropriate for stock splits, gifts, or airdrops where no purchase price exists

**When auto mode (`cost_basis_mode = "auto"`):**

- The transaction enters at the **current pool WAC** — the WAC remains algebraically unchanged
- This is appropriate for transfers or adjustments where the cost basis should be inherited from the source broker's pool

$$
WAC_{new} = \frac{WAC \times Q_{pool} + WAC \times Q_{tx}}{Q_{pool} + Q_{tx}} = WAC
$$

!!! tip "Auto WAC in the UI"

    In the transaction form, the "Auto" toggle uses this mode. The qualifying table shows the **Auto WAC** (or **Auto PMC** in Italian) effect badge, indicating that the units entered at the current pool cost without altering the WAC.

??? example "Example 4: Transfer in Auto Mode — WAC unchanged"

    | Date | Type | Qty | Unit Cost | Pool Qty | WAC |
    |------|------|-----|-----------|----------|-----|
    | Apr 1 | BUY | 10 | $150 | 10 | $150.00 |
    | Apr 15 | BUY | 5 | $180 | 15 | $160.00 |
    | May 1 | TRANSFER (auto) | +3 | $160 (=WAC) | 18 | $160.00 |

    $$
    WAC = \frac{160 \times 15 + 160 \times 3}{15 + 3} = \frac{2880}{18} = 160.00
    $$

    The transfer receiver in **auto mode** inherits the current WAC as its unit cost. The pool grows but the WAC stays **unchanged**.

## 🌍 Multi-Currency Handling

When a portfolio contains acquisitions in different currencies, LibreFolio:

1. Determines the **target currency** (most frequent among acquisitions)
2. Converts all unit costs to the target currency using historical FX rates
3. Computes WAC in the unified target currency

!!! warning "FX Rate Availability"

    If a required FX rate is missing, the WAC computation may be incomplete. The UI warns about missing FX pairs and provides quick-actions to add or sync them.

## 🎯 Where WAC is Used in LibreFolio

- **Transfer form**: auto-suggests cost_basis_override for outgoing transfers
- **P&L computation**: realized gains = sell_price − WAC (FIFO at runtime, WAC for cost basis)
- **Portfolio view**: average entry price per holding
