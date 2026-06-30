# 💼 Net Asset Value (NAV) / Net Worth

*[⬅️ Back to Performance Metrics Overview](index.md)*

## 💡 What is NAV?

**Net Asset Value (NAV)** is the total market valuation of your portfolio at a point in time $t$. It answers: *"How much is the portfolio worth right now?"*

---

## 🧮 Formula

$$
\boxed{\mathrm{NAV}(t) = \mathrm{MV}(t) + \mathrm{Cash}(t) + \mathrm{InTransit}(t)}
$$

Where $\mathrm{MV}(t) = \sum_{(a,b) \in S} q(a,b,t) \cdot p(a,t) \cdot \mathrm{fx}(\mathrm{ccy}_p, C^*, t)$

🔗 See **[Portfolio Engine — §5 Aggregation](portfolio-engine.md#5-portfolio-aggregation)** for full derivation.

---

## 🔗 Valuation Price Chain

The price $p(a,t)$ follows a strict priority:

1. **Market price** — PriceHistory backward-fill (latest $\leq t$)
2. **Last buy price** — most recent BUY unit price from $V(u)$ (all visible brokers)
3. **Missing** — position excluded from NAV

WAC is **never** used for valuation. See **[Portfolio Engine — §2](portfolio-engine.md#2-valuation-price)**.

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
| `MARKET_PRICE` | Full — PriceHistory available |
| `LAST_BUY_PRICE` | Partial — using transaction price |
| `MISSING` | None — excluded from NAV |
