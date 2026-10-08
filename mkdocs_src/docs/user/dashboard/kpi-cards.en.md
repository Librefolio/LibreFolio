# 💰 KPI Cards

The three KPI cards at the top of the dashboard give you a quick diagnostic of your portfolio. All values respect the **time range and broker scope** selected at the top of the page.

!!! note "Sharing affects these numbers"

    All amounts are aggregated over the brokers you have access to, and each broker you co-own contributes in proportion to your **ownership share** (e.g. a 50% Owner sees half of that broker's value and P&L). Editors and Viewers, whose share is always 0% by rule, see the broker's full amounts. See [Broker Sharing](../brokers/sharing.md).

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="KPI Cards Overview">
</div>

---

## 📉 Card 1 — Period P&L {: #card-1-period-pl }

<div class="kpi-card-crop-container card-period-pnl">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Period P&L Card">
</div>

The **Period P&L** card shows how much money your portfolio actually *earned* in the selected window — after removing the effect of your own deposits and withdrawals.

The hero number is calculated using the following formula:

\[\text{Period P&L} = \text{NAV}_{\text{end}} - \text{NAV}_{\text{start}} - \text{Net Flows}_{\text{period}}\]

A positive number means you earned money from investment activity. A negative number means you lost money net of capital movements.

### The number below the hero

Right under the Period P&L value, a smaller line shows something like `+91.31 € (+16.36%)`.

- The amount is the **day-over-day** (today vs. yesterday) change in your **Total P&L** — your all-time accumulated gain/loss, not just the selected period.
- The percentage compares that change with **yesterday's** Total P&L, taken without its sign — it tells you how much today's move "weighed" relative to your accumulated all-time result.

\[\text{Daily change} = \text{Total P&L}_{\text{today}} - \text{Total P&L}_{\text{yesterday}}\]

\[\text{%Daily change} = \frac{\text{Daily change}}{\left|\text{Total P&L}_{\text{yesterday}}\right|} \times 100\]

The sign and the colour follow the direction of the change: `+` and green when your Total P&L went up, `-` and red when it went down — even while your Total P&L is a loss. For example, if it was `-558.10 €` yesterday and is `-466.79 €` today, the line reads `+91.31 € (+16.36%)`: your accumulated loss shrank by 16.36%.

This line only appears once the history has at least two daily points. The percentage is left out only when yesterday's Total P&L is exactly zero, since there is nothing to compare against; a day without any change shows `0.00%`.

### The breakdown rows

| Row | What it measures |
|-----|-----------------|
| **Unrealized change** | How much your open positions' [unrealized gain/loss](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md) changed during the period. For assets priced in another currency it includes the effect of the exchange rate — hover the label to see it split by currency (below) |
| **Sales** | Realized gain or loss of the sales made during the period: what each sale brought in, minus what you paid for the units sold (their average cost) |
| **Dividends & interest** | Cash income from dividends, bond coupons, and P2P interest |
| **Fees & taxes** | Commissions and taxes recorded as transactions |

!!! tip "Identity check"

    The four rows explain your Period P&L: realized results (**Sales**), unrealized results with their exchange-rate effect (**Unrealized change**), **Dividends & interest**, and **Fees & taxes**. Whatever they cannot see belongs to the period's *other effects* — for example assets travelling between two of your brokers on the first or last day, or a sale whose amount could not be converted. You find it in the **Other / reconciliation residual** row of the **Other Period Effects** table, in the Performance view of [Positions](positions.md).

#### Unrealized change by currency {: #unrealized-change-by-currency }

Hover **Unrealized change** to see where it comes from. The tooltip splits it by the currency your assets are priced in — here with euro as display currency:

| Row | What it shows |
|-----|---------------|
| 📈 **Assets in USD** | What your dollar assets did *in dollars* — their own price change — counted at the exchange rate of the day |
| 💱 **USD → EUR rate** | What the exchange rate did to what you paid for them |
| **USD, not split** | Only when, on the first or last day of the period, some of those assets had no price, no exchange rate, or an incomplete purchase cost: their change is shown in one piece |

There is a 📈 row for every currency your assets are priced in, euro included, and a 💱 row for every currency other than your display currency: assets already in euro have no exchange-rate effect. For the assets priced in dollars, on a given day:

\[\text{Assets in USD} = (\text{Value in USD} - \text{Paid, in USD}) \times \text{Day's rate}\]

\[\text{USD → EUR rate} = \text{Paid, in USD} \times \text{Day's rate} - \text{Paid, in EUR}\]

Each row shows how its figure changed between the first and the last day of the period, and together the rows add up **exactly** to the Unrealized change. *Paid, in EUR* is what you really paid, each purchase at its own date's rate; *Paid, in USD* is the same amount expressed in dollars at those dates.

!!! example "A US ETF on a euro dashboard"

    During the period you bought 10 units for €400, when they were worth 500 USD. At the end of the period they are worth 550 USD, and 1 USD = €0.75. The tooltip shows:

    - 📈 **Assets in USD**: (550 − 500) × 0.75 = **+€37.50** — your ETF gained 10% in dollars;
    - 💱 **USD → EUR rate**: 500 × 0.75 − 400 = **−€25.00** — the dollar lost value against the euro;
    - together, the **Unrealized change**: 550 × 0.75 − 400 = **+€12.50**.

🔗 **Theory**: [Period P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md) · [Book Value / WAC](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)

---

## 📈 Card 2 — Returns {: #card-2-returns }

<div class="kpi-card-crop-container card-returns">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Returns Card">
</div>

The **Returns** card shows *rate-of-return* metrics — percentages that let you compare performance independently of portfolio size.

### Timing Effect

The **Timing Effect** at the top of the card measures whether your deposit/withdrawal decisions *added* or *subtracted* value compared to a passive buy-and-hold strategy:

\[\text{Timing Effect} = \text{MWRR}_{\text{cumulative}} - \text{TWRR}_{\text{cumulative}}\]

- **Favorable (positive)** ✅: you tended to deposit when prices were low, boosting your personal return above what the assets alone earned.
- **Unfavorable (negative)** ❌: you tended to deposit at peaks or missed dips, dragging your return below pure asset performance.

### The number below the Timing Effect

Below the Timing Effect you'll see a small percentage (e.g. `+0.35%`) — it's the change in your **Total P&L** from **yesterday to today**, compared with yesterday's net worth taken without its sign:

\[\text{%Daily change} = \frac{\text{Total P&L}_{\text{today}} - \text{Total P&L}_{\text{yesterday}}}{\left|\text{Net Worth}_{\text{yesterday}}\right|} \times 100\]

Its sign and colour follow the same rule as the line under the [Period P&L](#card-1-period-pl): `+` and green when your Total P&L went up, `-` and red when it went down, even in the rare case of a negative net worth. It is hidden only when yesterday's net worth was exactly zero; a day without any change shows `0.00%`.

It's a rough estimate of **today's** return — a quick pulse check. It is not the ROI, TWRR, or MWRR shown in the rows below, which stay anchored to the full selected period.

### The four return metrics

| Metric | Question it answers |
|--------|---------------------|
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md)** | How much did I gain relative to my net invested capital? |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** | How did my asset choices perform, independent of when I deposited? |
| **[MWRR cumulative](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** | What is the cumulative money-weighted return for my actual cash flows? |
| **[MWRR annualized](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** | At what yearly compound rate did my capital actually grow? |

!!! note "TWRR vs. MWRR"

    - **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** measures the **asset strategy** — same as how a fund manager is evaluated.
    - **[MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** measures **your personal result** — including the timing of your deposits.
    - The gap between them is the [Timing Effect](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md).

---

## 💰 Card 3 — Net Worth {: #card-3-net-worth }

<div class="kpi-card-crop-container card-net-worth">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Net Worth Card">
</div>

The **Net Worth** card shows the absolute value of your portfolio at the end of the selected period.

!!! note "Net Worth includes cash"

    The figure is **securities at market value + cash balance** (+ any value in transit between brokers). Because it includes liquidity, it is **not comparable** with the "securities value" (controvalore titoli) shown by a bank statement, which excludes cash — a bank's cash balance is reported separately.

### The number below Net Worth

Below the Net Worth value you'll find your **Total P&L**, with your absolute return in parentheses — e.g. `+12,450.30 (+24.85%)`.

- The amount is your **Total P&L** — the gain or loss accumulated since the beginning, across this scope's whole history (not just the current period).
- The percentage in parentheses is the **absolute (since-inception) ROI**: Total P&L ÷ net capital invested since inception. It is *not* a day-over-day change — for that daily pulse check, see the small lines on [Card 1](#card-1-period-pl) and [Card 2](#card-2-returns).

\[\text{Total P&L} = \text{Net Worth} - \text{Net Capital Invested Since Inception}\]

Note: "Net Capital Invested Since Inception" here is the sum of **all** deposits minus **all** withdrawals since you started using this scope — a different, larger figure than the "Deposited Capital" row below, which only counts movements within the selected period.

🔗 **Theory**: [Deposited Capital, Total PnL and Cash Pools](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)

### What the rows mean

| Row | Definition |
|-----|-----------|
| **[Market Value](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)** | Current market price × quantity for all held assets |
| **[Purchase Cost](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)** | What you paid for your open positions (average cost × qty), in your display currency: each purchase counts at the exchange rate of its own date, so this figure does not move with today's rates |
| **Cash** | Liquid balance held in broker accounts |
| **[Deposited Capital](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)** | Net external capital contributed to this scope |

### The Deposited Capital bar

The horizontal bar below the rows visualizes:

- 🟢 **Total deposited** — all deposits in the period
- 🔴 **Total withdrawn** — all withdrawals in the period

The hero number shows the net balance (deposited − withdrawn).

!!! info "Point-in-time vs. period"

    Market Value, Purchase Cost, and Cash are **snapshots** at the end date — they are independent of the start date.
    Deposited Capital is **period-scoped** — it counts deposits and withdrawals between the start and end of the selected range.

---

## 🔗 Related

- 💼 **[NAV / Net Worth](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- 📚 **[Book Value](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)**
- 📊 **[Period P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)**
- 💸 **[Deposited Capital & Total P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)**
- 📈 **[MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)**
- ⏱️ **[Timing Effect](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)**

---

*[⬅️ Back to Dashboard Overview](index.md)*
