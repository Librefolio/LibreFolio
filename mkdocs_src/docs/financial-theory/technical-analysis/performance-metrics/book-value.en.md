# 📖 Book Value

*[⬅️ Back to Performance Metrics Overview](index.md)*

## 💡 What is Book Value?

**Book Value** represents the historical accounting cost of your portfolio — how much capital you deployed at cost, plus cash reserves. It does not fluctuate with market prices.

---

## 🧮 Formula

$$
\boxed{\mathrm{Book}(t) = \mathrm{OCB}(t) + \mathrm{Cash}(t) + \mathrm{InTransitBook}(t)}
$$

Where Open Cost Basis:

$$
\mathrm{OCB}(t) = \sum_{\substack{(a,b) \in S \\ q > 0}} q(a,b,t) \cdot w(a,b,t) \cdot \mathrm{fx}(\mathrm{ccy}_w, C^*, t)
$$

🔗 See **[Portfolio Engine — §3 Position State](portfolio-engine.md#3-position-state)** for full derivation.

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

- 📊 [WAC](weighted-average-cost.md) — unit cost method for OCB
- 💼 [NAV](nav.md) — market-value counterpart
- 📈 [Period PnL](period-pnl.md) — realized + unrealized combined
