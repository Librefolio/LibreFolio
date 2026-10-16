# 💼 Net Asset Value (NAV) / Net Worth

## 💡 What is NAV?

**Net Asset Value (NAV)** is the total market valuation of your portfolio at a point in time $t$. It answers: *"How much is the portfolio worth right now?"*

---

## 🧮 Formula

$$
\boxed{\mathrm{NAV}(t) = \mathrm{MV}(t) + \mathrm{Cash}(t) + \mathrm{InTransit}(t)}
$$

Where:

$$
\mathrm{MV}(t)=
\sum_{(a,b)\in S}
\frac{q(a,b,t)}{qbq(a)}
\cdot \operatorname{mark}(a,t)
\cdot \mathrm{fx}(\mathrm{ccy}_{mark}, C^*, t)
$$

and the cash of each broker, kept in the currencies it was recorded in and valued at the rate of $t$:

$$
\mathrm{Cash}(t) = \sum_{b \in S} \sum_{c} N_{b,c}(t) \cdot \mathrm{fx}(c, C^*, t)
$$

with $N_{b,c}(t)$ the balance broker $b$ holds in currency $c$ on $t$, scaled by the broker's [ownership share](../../../../user/brokers/sharing.md), and $\mathrm{fx}(c, C^*, t)$ the latest rate on or before $t$ ($1$ for $c = C^*$). Cash held in another currency therefore moves NAV when its exchange rate moves.

A position whose asset has no mark yet — no quote, no BUY or SELL on or before $t$ — enters $\mathrm{MV}(t)$ at its cost basis $\mathrm{CB}(a,b,t)$ instead when that cost is complete, and is left out of NAV otherwise.

🔗 See **[Portfolio Engine — §3 Position State](index.md#3-position-state)** and **[§5 Aggregation](index.md#5-portfolio-aggregation)** for full derivation.

---

## 🔗 Unified Price Resolver {: #valuation-price-chain }

The mark $\operatorname{mark}(a,t)$ comes from the unified resolver:

1. **MARKET** — same-day asset-system quote.
2. **TRADE_AVG** — average same-day BUY/SELL observation.
3. **CARRIED** — last observation before $t$, carried forward (LOCF).
4. **MISSING** — no observation on or before $t$.

An ADJUSTMENT is never an observation, with or without a cost basis: it records a cost, not a price.

Marks remain in native currency until valuation, and so do cash balances, each in the currency it was recorded in; FX conversion happens at $t$. WAC is **never** a price: only a position with no mark at all is counted at its cost basis, a declared estimate (`ESTIMATED_AT_COST`) that keeps the exchange rates of its acquisition dates. See [Price Resolution](price-resolution.md).

---

## 📝 Example

| Component | Amount |
|-----------|--------|
| Market Value of Assets | €32,759 |
| Cash Balance | €631 |
| In-Transit | €0 |

$$
\mathrm{NAV} = 32\,759 + 631 + 0 = 33\,390 \text{ EUR}
$$

---

## ⚖️ Key Distinctions

- **NAV vs [Book Value](book-value.md)**: NAV = market value; Book = acquisition cost. Difference = unrealized gains.
- **NAV vs [Period PnL](period-pnl.md)**: NAV = snapshot; Period PnL = flow-adjusted change over time.

---

## ⚠️ Data Quality

| Valuation Source | Confidence |
|-----------------|------------|
| `MARKET_PRICE` | Full — real quote, exact or carried |
| `LAST_TRADE_PRICE` | Partial — trade-origin resolver mark |
| `ESTIMATED_AT_COST` | Estimate — no price at all: the cost basis, with no unrealized gain or loss |
| `MISSING` | None — no price and an incomplete cost: excluded from NAV |

`estimated=True` only applies to TRADE-origin marks. A stale carried MARKET quote is stale but not estimated.

For an asset with a price provider, the Dashboard warns as of the valuation date: a trade-origin valuation, once the asset has had no market quote for more than the 14-day grace period, raises the “valued at their last transaction price” warning, and a valuation at cost, more than 14 days after the asset's first acquisition, raises the “valued at cost” warning. An asset without a provider raises neither: its trades, or its cost, are its intended value.
