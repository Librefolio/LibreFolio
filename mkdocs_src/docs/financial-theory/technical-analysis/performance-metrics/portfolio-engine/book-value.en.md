# 📖 Book Value

## 💡 What is Book Value?

**Book Value** represents the historical accounting cost of your portfolio — open cost basis plus cash reserves and in-transit book value. It does not fluctuate with market prices, and it is distinct from [Price Resolution](price-resolution.md).

---

## 🧮 Formula

$$
\boxed{\mathrm{Book}(t) = \mathrm{OCB}(t) + \mathrm{Cash}(t) + \mathrm{InTransitBook}(t)}
$$

Where Open Cost Basis:

$$
\mathrm{OCB}(t) = \sum_{\substack{(a,b) \in S \\ q > 0}} q(a,b,t) \cdot w^{C^*}(a,b,t)
$$

Here $w^{C^*}(a,b,t)$ is the [WAC](../weighted-average-cost.md) kept directly in the requested currency $C^*$: each acquisition entered it at the rate of its own date $d_i$, as $P_i \cdot \mathrm{fx}(\mathrm{ccy}(P_i), C^*, d_i)$ for an amount $P_i$ actually paid. OCB therefore uses **no exchange rate at the valuation date** $t$: it is the sum of historical costs — what was paid — and it does not move when exchange rates move.

In the in-transit term, cash in transit is converted at $t$, while assets in transit carry their frozen cost converted at their arrival date.

!!! note "Incomplete cost"

    When part of a position's cost is unknown — no exchange rate on or before an acquisition date, or a transfer or adjustment without cost basis — OCB includes only the known part, and the position itself is flagged: its average cost and unrealized gain/loss are not shown.

🔗 See **[Portfolio Engine — §3 Position State](index.md#3-position-state)** for full derivation.

---

## ⚖️ Unrealized Gain/Loss

$$
\mathrm{Unrealized}(t) = \mathrm{NAV}(t) - \mathrm{Book}(t)
$$

Because NAV values the assets at the day's market price **and** exchange rate while Book keeps historical costs, the unrealized gain/loss of an asset priced in another currency includes the effect of the exchange rate. For example, 10 units bought for €400 when they were worth 500 USD keep an OCB of €400; if they are worth 550 USD on a day when 1 USD = €0.75, their market value is €412.50 and the unrealized gain is €12.50 — the units' own gain (+€37.50) less the dollar's fall (−€25.00). [Period P&L](period-pnl.md#unrealized-change-by-currency) shows how the Dashboard splits the two.

---

## 📝 Example

| Component | Amount |
|-----------|--------|
| Open Cost Basis | €27,000 |
| Cash | €600 |
| In-Transit Book | €0 |

$$
\mathrm{Book} = 27\,000 + 600 = 27\,600 \text{ EUR}
$$

With NAV = €33,000:

$$
\mathrm{Unrealized} = 33\,000 - 27\,600 = +5\,400 \text{ EUR}
$$

---

## 🔗 Related

- 📊 [WAC](../weighted-average-cost.md) — unit cost method for OCB
- 💼 [NAV](nav.md) — market-value counterpart
- 🧭 [Price Resolution](price-resolution.md) — market/trade marks used by NAV, not by book value
- 📈 [Period PnL](period-pnl.md) — realized + unrealized combined
- 📈 [Performance Metrics Overview](../index.md) — all performance metrics at a glance
