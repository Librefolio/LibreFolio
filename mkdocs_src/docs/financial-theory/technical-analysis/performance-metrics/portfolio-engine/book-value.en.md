# 📖 Book Value

## 💡 What is Book Value?

**Book Value** represents the historical accounting cost of your portfolio — open cost basis plus cash reserves and in-transit book value. It does not fluctuate with market prices — only cash held in another currency follows its exchange rate, in Book as in NAV — and it is distinct from [Price Resolution](price-resolution.md).

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

Cash, instead, is each broker's cash kept in the currencies it was recorded in and valued at the rate of $t$:

$$
\mathrm{Cash}(t) = \sum_{b \in S} \sum_{c} N_{b,c}(t) \cdot \mathrm{fx}(c, C^*, t)
$$

Here $N_{b,c}(t)$ is the balance broker $b$ holds in currency $c$ on $t$ — its movements in $c$ dated on or before $t$, scaled by the broker's [ownership share](../../../../user/brokers/sharing.md) — and $\mathrm{fx}(c, C^*, t)$ is the latest rate on or before $t$, with $\mathrm{fx}(C^*, C^*, t) = 1$. Unlike OCB, Cash moves with exchange rates: 1,000 USD are worth €900 at 0.90 EUR per USD and €950 at 0.95. Each movement was still booked at the rate of its own date, and the capital flows among them entered the [capital baseline](deposited-capital.md) at that rate; only the balance held afterwards follows the rate.

In the in-transit term, cash in transit is converted at $t$ too, like the cash at rest, while assets in transit carry their frozen cost converted at their arrival date.

!!! note "Incomplete cost"

    When part of a position's cost is unknown — no exchange rate on or before an acquisition date, or a transfer or adjustment without cost basis — OCB includes only the known part, and the position itself is flagged: its average cost and unrealized gain/loss are not shown.

🔗 See **[Portfolio Engine — §3 Position State](index.md#3-position-state)** for full derivation.

---

## ⚖️ Unrealized Gain/Loss

$$
\mathrm{Unrealized}(t) = \mathrm{NAV}(t) - \mathrm{Book}(t)
$$

Because NAV values the assets at the day's market price **and** exchange rate while Book keeps historical costs, the unrealized gain/loss of an asset priced in another currency includes the effect of the exchange rate. For example, 10 units bought for €400 when they were worth 500 USD keep an OCB of €400; if they are worth 550 USD on a day when 1 USD = €0.75, their market value is €412.50 and the unrealized gain is €12.50 — the units' own gain (+€37.50) less the dollar's fall (−€25.00). [Period P&L](period-pnl.md#unrealized-change-by-currency) shows how the Dashboard splits the two.

Cash held in another currency is different: $\mathrm{Cash}(t)$ is the same term in NAV and in Book, valued at the rate of $t$ on both sides, so its exchange-rate effect cancels in the difference and Unrealized excludes it. It is a result all the same: the engine books it as the [exchange result on cash](index.md#exchange-result-on-foreign-cash), it is part of the [Total P&L](deposited-capital.md), and over a period it is the [FX on cash](period-pnl.md#fx-on-cash) part of Other. For example, 1,000 USD deposited at 0.90 EUR per USD and held while the rate rises to 0.95 count €950 in both NAV and Book: Unrealized does not move, while the Total P&L gains €50 over the €900 of capital.

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
