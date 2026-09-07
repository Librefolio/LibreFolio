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

🔗 See **[Portfolio Engine — §5 Aggregation](index.md#5-portfolio-aggregation)** for full derivation.

---

## 🔗 Unified Price Resolver {: #valuation-price-chain }

The mark $\operatorname{mark}(a,t)$ comes from the unified resolver:

1. **MARKET** — same-day asset-system quote.
2. **TRADE_AVG** — average same-day BUY/SELL/priced ADJUSTMENT observation.
3. **CARRIED** — last observation before $t$, carried forward (LOCF).
4. **MISSING** — no observation on or before $t$.

Marks remain in native currency until valuation; FX conversion happens at $t$. WAC is **never** used for valuation. See [Price Resolution](price-resolution.md).

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
| `MISSING` | None — excluded from NAV |

`estimated=True` only applies to TRADE-origin marks. A stale carried MARKET quote is stale but not estimated.

Trade-origin valuations older than the 14-day grace period drive the “assets valued at cost / no market price for more than two weeks” warning as of the valuation date.
