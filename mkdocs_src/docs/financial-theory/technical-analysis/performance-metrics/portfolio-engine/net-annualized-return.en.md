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
\mathrm{CostBasis}_{end} + \sum_a \left(V_a - C_a\right), & \text{otherwise}
\end{cases}
$$

The sum is over the transfers from another broker of the scope the position received in the period, each counted as in
[Positions Closed in the Period](#closed-in-period): what their units gained before they arrived, value on arrival less
the historical cost moved (MF-A9). The position's result counts those units from their value on arrival, its end cost at
their historical cost, so the base adds the same amount. It applies only while the position still holds every unit it
received: once units left it in the period, a transfer carries no quantity to tell which part of the sum left with
them, and the sum is dropped — the end cost alone is the base, as for any position opened mid-period that sold part of
what it bought.

Window start is clamped to the oldest FIFO lot still open at period end:

$$
t_{\mathrm{start}}=\max(t_{\mathrm{from}},\ t_{\mathrm{oldest\ open\ lot}})
$$

Lots are counted at each broker: a transfer opens a lot dated at its arrival at the receiving broker. A stock split rescales the open lots and keeps their dates, so it never shortens the window.

Then:

$$
r_{\mathrm{ann}} =
\operatorname{annualize}\left(\frac{\mathrm{PnL}_{period}}{\mathrm{ann\_base}},\ t_{\mathrm{end}}-t_{\mathrm{start}}\right)
$$

### 🔚 Positions Closed in the Period {: #closed-in-period }

A position is closed when its quantity at $t_{\mathrm{end}}$ is at or below the dust threshold of $10^{-5}$ units, so a residual left by redemptions in tranches counts as closed. It has no end cost, and a start value says nothing about a holding sold a few weeks in. Its annualized return uses the capital it deployed and the time it was held inside the period:

$$
\mathrm{CostOut} = \sum_{s\,\in\,(t_{\mathrm{from}},\ t_{\mathrm{end}}]} C_s \;+\; \sum_{m\,\in\,(t_{\mathrm{from}},\ t_{\mathrm{end}}]} C_m \;+\; \sum_{a\,\in\,(t_{\mathrm{from}},\ t_{\mathrm{end}}]} \left(V_a - C_a\right)
$$

$$
t_{\mathrm{start}} = \max(t_{\mathrm{from}},\ t_{\mathrm{first\ opening}}), \qquad t_{\mathrm{close}} = \text{last day its quantity fell to the dust threshold or below}
$$

$$
r_{\mathrm{ann}} =
\operatorname{annualize}\left(\frac{\mathrm{PnL}_{period}}{\mathrm{CostOut}},\ t_{\mathrm{close}}-t_{\mathrm{start}}\right)
$$

- $C_s$ is the historical cost, in $C^*$, of each disposal the period's Realized counts — a SELL, or an outgoing ADJUSTMENT with a cost basis ([Portfolio Engine — §8](index.md#8-realized-gain-loss)). A disposal left out of Realized adds no cost.
- $C_m$ is the historical cost each transfer to another broker of the scope moved out, when the row counts that transfer's tract: it left after $t_{\mathrm{from}}$, arrived by $t_{\mathrm{end}}$, and both its value on arrival and the cost moved are known ([Period P&L](period-pnl.md), developer decision P22). The row's result carries what those units did until they arrived (the tract adjustment), so their cost belongs in the base.
- $V_a - C_a$ is, for each such transfer the position **received**, what its units gained before they arrived: their value on arrival less the historical cost moved with them. The row's result starts those units at $V_a$ (the tract adjustment takes back $V_a - C_a$), while $C_s$ and $C_m$ carry their historical cost, so the base adds the same amount and counts them at their value on arrival too (MF-A8). So $\mathrm{CostOut}$ is not only historical cost: for the units the position received, the base holds their value on arrival.
- $t_{\mathrm{first\ opening}}$ is the position's first acquisition at that broker: a transfer opens it on its arrival there, a split never does. It is the first one ever, not the last lot's, so days at zero between two closes inside the period stay in the window.
- The numerator is the row's whole $\mathrm{PnL}_{period}$: for a position held at $t_{\mathrm{from}}$, its $\Delta\mathrm{UGL}$ gives back the unrealized gain/loss it started with.
- The displayed period percentage keeps $|\mathrm{StartValue}|$ as base: only the annualized value changes base and window.

When this gives no value, the row keeps the rule above. That happens when units left the position in any other way — a transfer outside the scope, or still in transit at $t_{\mathrm{end}}$, a transfer or a disposal whose value or cost is unknown, an outgoing ADJUSTMENT without a cost basis — since the row's result would then hold more than its base covers; and with fewer than 30 days held, or a return of $-100\%$ or worse. The rule above is: $|\mathrm{StartValue}|$ over $t_{\mathrm{from}} \to t_{\mathrm{end}}$, and no value for a position opened in the period.

??? example "Example: a position sold 90 days into a one-year period"

    At $t_{\mathrm{from}}$ the position is worth 1,100 for a cost of 1,000. All of it is sold 90 days later for 1,250:

    $$
    \mathrm{PnL}_{period} = (0 - 100) + (1{,}250 - 1{,}000) = +150
    $$

    $$
    r_{\mathrm{ann}} = \operatorname{annualize}\left(\frac{150}{1{,}000},\ 90\right) = 1.15^{365/90} - 1 \approx +76.3\%
    $$

    The unrealized +100 it started with comes back out of $\Delta\mathrm{UGL}$, Realized adds +250. The period percentage stays $150 / 1{,}100 = 13.64\%$; annualized over the whole year on the start value, as an open position would be, the same +150 would read 13.64% as well.

??? example "Example: half sold, half moved to another broker"

    At $t_{\mathrm{from}}$ the position holds 10 units, worth 1,100 for a cost of 1,000. Five are sold for 625; five move to another broker of the scope and are worth 600 when they arrive:

    $$
    \mathrm{PnL}_{period} = \underbrace{(0 - 100)}_{\Delta\mathrm{UGL}} + \underbrace{(625 - 500)}_{\text{Realized}} + \underbrace{(600 - 500)}_{\text{tract}} = +125
    $$

    $$
    \mathrm{CostOut} = 500 + 500 = 1{,}000, \qquad \frac{125}{1{,}000} = 12.5\%
    $$

    The cost of the sold units alone would read $125 / 500 = 25\%$: the moved units' result in the numerator, without their cost in the base (MF-A5).

    The broker that received the five units and later sold them for 660 reads the mirror: its result is $(660 - 500) - (600 - 500) = +60$, and its base $500 + (600 - 500) = 600$, so $60 / 600 = 10\%$ — the units count from their value on arrival, in the result and in the base alike (MF-A8).

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
