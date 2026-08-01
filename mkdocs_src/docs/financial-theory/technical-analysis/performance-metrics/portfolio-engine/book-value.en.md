# 📖 Book Value

*[⬅️ Back to Performance Metrics Overview](../index.md)*

## 💡 What is Book Value?

**Book Value** represents the historical accounting cost of your portfolio — open cost basis plus cash reserves and in-transit book value. It does not fluctuate with market prices, and it is distinct from [Price Resolution](price-resolution.md).

---

## 🧮 Formula

$$
\boxed{\mathrm{Book}(t) = \mathrm{OCB}(t) + \mathrm{Cash}(t) + \mathrm{InTransitBook}(t)}
$$

Where Open Cost Basis:

$$
\mathrm{OCB}(t) = \sum_{\substack{(a,b) \in S \\ q > 0}} q(a,b,t) \cdot w(a,b,t) \cdot \mathrm{fx}(\mathrm{ccy}_w, C^*, t)
$$

Here $w(a,b,t)$ is WAC in its cost currency. The acquisition cost itself is pinned to transaction-date FX inside WAC; the open book value is then reported in the requested currency for the valuation date.

🔗 See **[Portfolio Engine — §3 Position State](index.md#3-position-state)** for full derivation.

---

## ⚖️ Unrealized Gain/Loss

$$
\mathrm{Unrealized}(t) = \mathrm{NAV}(t) - \mathrm{Book}(t)
$$

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
