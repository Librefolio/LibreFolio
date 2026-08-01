# 📉 Simple ROI (Return on Investment)

*[⬅️ Back to Performance Metrics Overview](../index.md)*

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
