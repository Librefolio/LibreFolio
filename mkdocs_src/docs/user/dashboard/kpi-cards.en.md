# 💰 KPI Cards

*[⬅️ Back to Dashboard Overview](index.md)*

The three KPI cards at the top of the dashboard give you a quick diagnostic of your portfolio. All values respect the **time range and broker scope** selected at the top of the page.

---

## 💰 Card 1 — Net Worth {: #card-1-net-worth }

The **Net Worth** card shows the absolute value of your portfolio at the end of the selected period.

### What the rows mean

| Row | Definition |
|-----|-----------|
| **[Market Value](../../financial-theory/technical-analysis/performance-metrics/nav.md)** | Current market price × quantity for all held assets |
| **[Book Value](../../financial-theory/technical-analysis/performance-metrics/book-value.md)** | What you paid for your open positions (average cost × qty) |
| **Cash** | Liquid balance held in broker accounts |
| **[Deposited Capital](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)** | Net external capital contributed to this scope |

### The Deposited Capital bar

The horizontal bar below the rows visualizes:

- 🟢 **Total deposited** — all deposits in the period
- 🔴 **Total withdrawn** — all withdrawals in the period

The hero number shows the net balance (deposited − withdrawn).

!!! info "Point-in-time vs. period"

    Market Value, Book Value, and Cash are **snapshots** at the end date — they are independent of the start date.
    Deposited Capital is **period-scoped** — it counts deposits and withdrawals between the start and end of the selected range.

---

## 📉 Card 2 — Period P&L {: #card-2-period-pl }

The **Period P&L** card shows how much money your portfolio actually *earned* in the selected window — after removing the effect of your own deposits and withdrawals.

The hero number uses the formula:

> **NAV end** − **NAV start** − **Net External Flows in period**

A positive number means you earned money from investment activity. A negative number means you lost money net of capital movements.

### The breakdown rows

| Row | What it measures |
|-----|-----------------|
| **Unrealized change** | How much your open positions' [unrealized gain/loss](../../financial-theory/technical-analysis/performance-metrics/book-value.md) changed during the period |
| **Sales** | Realized gain or loss from positions closed during the period (sell price − average cost) |
| **Dividends & interest** | Cash income from dividends, bond coupons, and P2P interest |
| **Fees & taxes** | Commissions and taxes recorded as transactions |

!!! tip "Identity check"

    All four rows add up to the Period P&L hero number (± small residuals from FX rounding).

🔗 **Theory**: [Period P&L](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md) · [Book Value / WAC](../../financial-theory/technical-analysis/performance-metrics/book-value.md)

---

## 📈 Card 3 — Returns {: #card-3-returns }

The **Returns** card shows *rate-of-return* metrics — percentages that let you compare performance independently of portfolio size.

### Timing Effect

The **Timing Effect** at the top of the card measures whether your deposit/withdrawal decisions *added* or *subtracted* value compared to a passive buy-and-hold strategy.

> **Timing Effect** = MWRR cumulative − TWRR cumulative

- **Favorable (positive)** ✅: you tended to deposit when prices were low, boosting your personal return above what the assets alone earned.
- **Unfavorable (negative)** ❌: you tended to deposit at peaks or missed dips, dragging your return below pure asset performance.

### The four return metrics

| Metric | Question it answers |
|--------|---------------------|
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/roi.md)** | How much did I gain relative to my net invested capital? |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** | How did my asset choices perform, independent of when I deposited? |
| **[MWRR cumulative](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | What is the cumulative money-weighted return for my actual cash flows? |
| **[MWRR annualized](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | At what yearly compound rate did my capital actually grow? |

!!! note "TWRR vs. MWRR"

    - **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** measures the **asset strategy** — same as how a fund manager is evaluated.
    - **[MWRR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** measures **your personal result** — including the timing of your deposits.
    - The gap between them is the [Timing Effect](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md).

---

## 🔗 Related

- 💼 **[NAV / Net Worth](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- 📚 **[Book Value](../../financial-theory/technical-analysis/performance-metrics/book-value.md)**
- 📊 **[Period P&L](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md)**
- 💸 **[Deposited Capital & Total P&L](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)**
- 📈 **[MWRR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)**
- ⏱️ **[Timing Effect](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md)**
