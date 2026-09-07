# 📈 Net Annualized Return

## 💡 Purpose

LibreFolio reports annualized return only when the observed window is long enough to make compounding meaningful. The shared conversion is:

$$
\boxed{r_{\mathrm{ann}} = (1+r_{\mathrm{cum}})^{365/d}-1}
$$

where $d$ is calendar days. It is the inverse of:

$$
r_{\mathrm{cum}}=(1+r_{\mathrm{ann}})^{d/365}-1
$$

The implementation returns `None` when:

- $r_{\mathrm{cum}} \leq -1$
- $d < 30$
- the computation overflows

!!! warning "Thirty-day guard"

    A one-week return annualized to 365 days can explode into meaningless percentages. LibreFolio therefore suppresses annualization below 30 days and displays an empty value instead of a mathematically correct but misleading CAGR.

## 🧾 Holdings View

For an open holding in “Your positions” / portfolio summary:

$$
r_{\mathrm{net}} =
\frac{
\mathrm{MarketComponent}
+ \mathrm{Income}
- \mathrm{FeesTaxes}
}{
\mathrm{CostBasis}
}
$$

where:

$$
\mathrm{MarketComponent} =
\begin{cases}
\mathrm{CurrentValue}-\mathrm{CostBasis}, & \text{market value exists}\\
0, & \text{price-less / valued at cost}
\end{cases}
$$

Annualization window:

$$
d = t_{\mathrm{report}} - t_{\mathrm{first\ lot\ affecting}}
$$

Lot-affecting transaction types are:

$$
\{\text{BUY},\ \text{SELL},\ \text{ADJUSTMENT},\ \text{TRANSFER}\}
$$

This includes in-kind successions, broker transfers, and adjustment-seeded positions. Old BUY/SELL-only discovery would miss those holdings.

## 🪟 Period View

For per-asset period contribution:

$$
\mathrm{PnL}_{period} =
\Delta \mathrm{UGL}
+ \mathrm{Realized}
+ \mathrm{Income}
- \mathrm{FeesTaxes}
$$

The displayed period percentage remains:

$$
r_{\mathrm{period}} = \frac{\mathrm{PnL}_{period}}{|\mathrm{StartValue}|}
$$

when `StartValue` is non-zero. Annualization can fall back to end cost basis for assets opened mid-period:

$$
\mathrm{ann\_base}=
\begin{cases}
|\mathrm{StartValue}|, & |\mathrm{StartValue}|>0\\
\mathrm{CostBasis}_{end}, & \text{otherwise}
\end{cases}
$$

Window start is clamped to the oldest FIFO lot still open at period end:

$$
t_{\mathrm{start}}=\max(t_{\mathrm{from}},\ t_{\mathrm{oldest\ open\ lot}})
$$

Then:

$$
r_{\mathrm{ann}} =
\operatorname{annualize}\left(\frac{\mathrm{PnL}_{period}}{\mathrm{ann\_base}},\ t_{\mathrm{end}}-t_{\mathrm{start}}\right)
$$

## 🧬 FIFO Lots

FIFO lot annualized return is net of allocated income, fees, and taxes:

$$
\mathrm{NetTotalPnL}_i =
\mathrm{MarketPnL}_i
+ \mathrm{RealizedPnL}_i
+ \mathrm{Income}_i
- \mathrm{Fees}_i
- \mathrm{Taxes}_i
$$

$$
\mathrm{NetTotalReturn}_i =
\frac{\mathrm{NetTotalPnL}_i}{\mathrm{OpeningValue}_i}
$$

The annualized value uses `net_total_return`, not gross `total_return`:

$$
r_{\mathrm{ann},i} =
\operatorname{annualize}
\left(
\mathrm{NetTotalReturn}_i,\ 
t_{\mathrm{lot\ end}}-t_{\mathrm{opening}}
\right)
$$

where $t_{\mathrm{lot\ end}}$ is the closing date for fully closed lots, otherwise the analysis end date.

## 🔗 Related

- 🧭 [Price Resolution](price-resolution.md) — source of market and trade-origin valuations
- 📉 [Simple ROI](roi.md) — headline and position-level return context
- 📊 [Period PnL](period-pnl.md) — period decomposition
- 🔬 [FIFO Lot Analysis](../fifo-engine/fifo-lot-analysis.md) — per-lot net metrics
- ⚙️ [Portfolio Engine](index.md) — full mathematical model
