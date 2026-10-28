# 📉 Simple ROI (Return on Investment)

## 💡 What is it?

Simple ROI measures value generated relative to invested capital. In the current portfolio engine, the invested-capital denominator is the **capital baseline** from `cumulative_external_cash_flow`, not cash-only deposits.

## 🧮 Formula

$$
\mathrm{ROI}(t)=
\frac{\mathrm{NAV}(t)-\mathrm{CapitalBaseline}(t)}
{\mathrm{CapitalBaseline}(t)}
$$

The same baseline drives headline `total_gain_loss`:

$$
\mathrm{TotalGainLoss}(t)=\mathrm{NAV}(t)-\mathrm{CapitalBaseline}(t)
$$

`CapitalBaseline` includes ordinary external cash flows and priced in-kind ADJUSTMENT/TRANSFER capital. That prevents inherited or seeded portfolios from showing absurd ROI because an asset entered without a cash deposit.

## 🪟 The ROI of a Period {: #dashboard-period-roi }

The ROI on the Dashboard's Returns card and its line on the `%` chart measure the selected period, not the whole history. Their capital is the value the period opens with, plus the deposits and minus the withdrawals made after it:

$$
\mathrm{ROI}_{\mathrm{period}}(t)=
\frac{\mathrm{NAV}(t)-\mathrm{NetInvested}(t)}{\mathrm{NetInvested}(t)},
\qquad
\mathrm{NetInvested}(t)=\max\!\left(0,\ \mathrm{NAV}(t_0)+\sum_{t_0<s\le t}\mathrm{CF}_s\right)
$$

where $t_0$ is the last day of the history on or before the period's start, and $\mathrm{CF}_s$ counts the external flows — deposits positive, withdrawals negative, in-kind capital included as for the capital baseline above. The card is the line's last point; where $\mathrm{NetInvested}(t)$ is zero the ROI is $0$, never a missing value.

When the period starts **before the portfolio's first day**, there is no value to open with, and the flows of that first day — the first deposit — would fall outside the sum. The period then holds the whole history, so its capital is every flow, the first deposit included: the ROI is the same as with no start date at all, on the card and at every point of the line.

## 🎯 When to use it

- To read headline portfolio gain/loss against contributed economic capital.
- To compare current NAV against the current capital baseline.
- To sanity-check cash-flow-adjusted performance before looking at TWRR/MWRR.

## 📈 Position Net Annualized Return

Open holdings also expose a net CAGR:

$$
r_{\mathrm{net}}=
\frac{\mathrm{MarketComponent}+\mathrm{Income}-\mathrm{FeesTaxes}}
{\mathrm{CostBasis}}
$$

Annualization uses:

$$
r_{\mathrm{ann}}=(1+r_{\mathrm{net}})^{365/d}-1
$$

The window starts at the first lot-affecting transaction: BUY, SELL, ADJUSTMENT, or TRANSFER. Values shorter than 30 days are suppressed. Full definitions are in [Net Annualized Return](net-annualized-return.md).

## ⚠️ The Flaw: Cash Flow Dilution

Simple ROI is still sensitive to the amount and timing of capital added. If you add a large contribution after gains have already occurred, the ratio can fall even though market value did not. Use [Period P&L](period-pnl.md), [TWRR](twrr.md), and [MWRR](mwrr.md) to separate absolute profit, strategy return, and money-weighted investor return.
