# 📈 Linear Growth

A linear growth benchmark represents **simple interest** — the value increases by a fixed absolute amount each period.

---

## 💡 Financial Meaning

This models the scenario where you **do not reinvest** earnings (dividends, interest, coupons): cash payouts are received but kept aside, so only the original principal generates returns.

If instead you **reinvest** those earnings — either manually or automatically through accumulating instruments (e.g., accumulating ETFs, which reinvest dividends internally and benefit from [tax deferral](../../fundamentals/taxation.md#tax-deferral-advantage)) — you should expect **[compound growth](compound.md)**, where returns generate further returns.

In practice, the difference between linear and compound growth widens dramatically over long horizons. This is why the Linear benchmark appears as a straight line while the Compound benchmark curves upward exponentially.

!!! abstract "Capital gains & losses"

    When selling an asset above its purchase price, the difference is a **capital gain**;
    below, a **capital loss**. Each jurisdiction has its own rules regarding tax rates,
    holding period thresholds, loss carry-forward duration, and matching methods
    (FIFO, LIFO, specific identification). For a theoretical overview, see
    [Taxation & Tax Efficiency](../../fundamentals/taxation.md).

---

## 🔢 Mathematical Formula

$$
y(t) = y_0 \cdot (1 + r \cdot t)
$$

where:

- $y_0$ is the starting value (first data point of the chart),
- $r$ is the annual growth rate (expressed as a decimal, e.g. 0.07 for 7%),
- $t$ is time in years from the start.

This is equivalent to the **simple interest** formula $A = P(1 + rt)$, where $t$ is expressed in years using the applicable [Day Count Convention](../../fundamentals/day-count.md).

---

## ⚙️ Parameters

| Parameter | Key | Default | Description |
|---|---|---|---|
| Annual Rate | `annualRate` | 5 | Growth rate in percent per year. |
| Offset | `offset` | 0 | Vertical shift as % of base value. |

---

## 🔍 Interpretation

The line is perfectly straight on a linear scale. Any point where the actual price is *above* the line means the asset has outperformed the target; any point *below* means underperformance. Because the growth is additive, the line curves downward on a logarithmic scale — making it easy to visually distinguish from compound growth.

:material-link: [Simple Interest on Wikipedia](https://en.wikipedia.org/wiki/Interest#Simple_interest){ target="_blank" }


