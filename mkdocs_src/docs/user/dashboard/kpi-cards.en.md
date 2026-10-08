# 💰 KPI Cards

The three cards at the top of the Dashboard answer three questions at a glance: **what did I earn in this period**, **how well did my money work**, and **what is my portfolio worth**. They follow the time range and the broker filter at the top of the page, and a broker's page shows the same cards for that broker alone. The **?** icon in a card's corner opens its section below.

- 📉 **[Card 1 — Period P&L](#card-1-period-pl)** — the money your investments made in the period
- 📈 **[Card 2 — Returns](#card-2-returns)** — your returns in percent, and what your timing did to them
- 💰 **[Card 3 — Net Worth](#card-3-net-worth)** — what you own, and your gain since the start

!!! note "Shared brokers count for your share"

    The Dashboard adds up the brokers you **own** with a share above 0%, each in proportion to that share: a 50% owner sees half of the broker's value and P&L. Brokers where you are an Editor or a Viewer are not counted here; their own page shows them, with their full amounts. See [Broker Sharing](../brokers/sharing.md).

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="KPI Cards Overview">
</div>

---

## 📉 Card 1 — Period P&L {: #card-1-period-pl }

How much money did your investments make in the selected period? The **Period P&L** card answers, leaving out the money you moved in or out yourself.

<div class="kpi-card-crop-container card-period-pnl">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Period P&L Card">
</div>

**Metrics shown**

- **Period P&L** — the big number: $\text{NAV}_{\text{end}} - \text{NAV}_{\text{start}} - \text{Net flows}$, the net flows being the capital you moved in or out → [Period P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)
- **The line under it** — for example `+91.31 € (+16.36%)`: how much your Total P&L moved since yesterday (panel below)
- **Unrealized change** — how the unrealized gain or loss of your holdings moved over the period, exchange-rate effect included → [Book Value](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)
- **Sales** — the realized gain or loss of the period's sales, against the average cost of the units sold → [Weighted Average Cost](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)
- **Dividends & interest** — dividends, coupons and P2P interest received → [Dividend & Interest](../../financial-theory/instruments/transaction-types/dividend-interest.md)
- **Fees & taxes** — commissions and taxes recorded as transactions; hover the row for the split → [Fee & Tax](../../financial-theory/instruments/transaction-types/fee.md)

**How to read it**

- **Green is a gain, red a loss** — and a deposit or a withdrawal is neither.
- **The four rows explain the big number.** What they cannot see, such as assets moving between two of your brokers on the first or last day, goes to the **Other / reconciliation residual** of the [Performance view](positions.md#performance).
- **The longest bar** is the row that moved your result the most.

??? info "📏 The line under the big number — how it is computed"

    It is the change of your Total P&L — your gain or loss since the start — from yesterday to today, *today* being the end date of the period. The percentage compares it with yesterday's Total P&L, taken without its sign:

    $$
    \Delta = \text{Total P}\&\text{L}_{\text{today}} - \text{Total P}\&\text{L}_{\text{yesterday}} \qquad \text{percentage} = \frac{\Delta}{\left|\text{Total P}\&\text{L}_{\text{yesterday}}\right|} \times 100
    $$

    - **Sign and colour follow the change**, even while the Total P&L is a loss: from `-558.10 €` to `-466.79 €`, the line reads `+91.31 € (+16.36%)` — your loss shrank by 16.36%.
    - **It needs two days of history**; the percentage is left out when yesterday's Total P&L is exactly zero, and a day without change shows `0.00%`.

### 💱 Unrealized change by currency {: #unrealized-change-by-currency }

Hover **Unrealized change** to split it by the currency your assets are priced in — here with euro as display currency:

| Row | What it shows |
|-----|---------------|
| 📈 **Assets in USD** | What your dollar assets did *in dollars* — their own price change — counted at the day's exchange rate |
| 💱 **USD → EUR rate** | What the exchange rate did to what you paid for them |
| ❔ **USD, not split** | Only when, on the first or last day, some of those assets had no price, no rate or an incomplete purchase cost: their change, in one piece |

There is a 📈 row for every currency, euro included, and a 💱 row for every currency other than your display currency; together the rows add up **exactly** to the Unrealized change.

??? example "A US ETF on a euro dashboard"

    During the period you bought 10 units for €400, when they were worth 500 USD. At the end of the period they are worth 550 USD, and 1 USD = €0.75. The tooltip shows:

    - 📈 **Assets in USD**: (550 − 500) × 0.75 = **+€37.50** — your ETF gained 10% in dollars;
    - 💱 **USD → EUR rate**: 500 × 0.75 − 400 = **−€25.00** — the dollar lost value against the euro;
    - together, the **Unrealized change**: 550 × 0.75 − 400 = **+€12.50**.

🔗 **Theory**: [Unrealized change by currency](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md#unrealized-change-by-currency) — the formulas behind each row

---

## 📈 Card 2 — Returns {: #card-2-returns }

How well did your money work, whatever the size of your portfolio? The **Returns** card answers in percentages, and its big number tells you whether your timing helped.

<div class="kpi-card-crop-container card-returns">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Returns Card">
</div>

**Metrics shown**

- **Timing effect** — the big number, in percentage points (pp): $\text{MWRR}_{\text{cumulative}} - \text{TWRR}$ → [Timing Effect](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)
- **The percentage under it** — for example `+0.35%`: today's change in your Total P&L, against yesterday's net worth (panel below)
- **ROI** — the period's gain against the capital invested → [Simple ROI](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md)
- **TWRR** — how your asset choices performed, whatever the timing of your deposits → [TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)
- **MWRR cumulative** and **MWRR annualized** — your personal return, deposit timing included, over the period and as a yearly rate → [MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)

**How to read it**

- **Favorable timing** (green): you tended to deposit before prices rose. **Unfavorable timing** (red): you tended to deposit at the peaks. Close to zero it reads **Neutral timing**, and the stronger the colour, the larger the effect.
- **TWRR judges the strategy, MWRR your personal result** — as for a fund manager and an investor.
- **The four rows cover the whole period**; the small percentage covers today only.

??? info "📏 The percentage under the timing effect — how it is computed"

    The same change of your Total P&L as on [Card 1](#card-1-period-pl), divided by yesterday's net worth taken without its sign:

    $$
    \text{percentage} = \frac{\text{Total P}\&\text{L}_{\text{today}} - \text{Total P}\&\text{L}_{\text{yesterday}}}{\left|\text{Net Worth}_{\text{yesterday}}\right|} \times 100
    $$

    Its sign and colour follow the change, as on Card 1. It needs two days of history and is hidden when yesterday's net worth was exactly zero.

---

## 💰 Card 3 — Net Worth {: #card-3-net-worth }

What is your portfolio worth at the end of the period, and what has it gained since you started? The **Net Worth** card answers, cash included.

<div class="kpi-card-crop-container card-net-worth">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Net Worth Card">
</div>

**Metrics shown**

- **Net Worth** — the big number: securities at market value, plus cash, plus anything in transit between your brokers → [NAV / Net Worth](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)
- **The line under it** — for example `+12,450.30 (+24.85%)`: your **Total P&L** since the start and, in brackets, your **ROI since the start** → [Deposited Capital & Total P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)
- **Market Value** — what the assets you hold are worth at market prices → [NAV / Net Worth](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)
- **Purchase Cost** — what the positions you still hold cost you, each purchase at its own date's exchange rate → [Book Value](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)
- **Cash** — the cash at your brokers; hover it to split the capital you deposited from the returns you made → [Cash pools](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#three-pool-cash-model)
- **Deposited Capital (Period)** — deposits minus withdrawals in the period, green to the right and red to the left; hover it for the totals → [Deposited Capital](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)

$$
\text{Total P}\&\text{L} = \text{Net Worth} - \text{Capital put in since the start}
$$

That capital is every deposit minus every withdrawal, plus the purchase cost of securities you brought in without cash, such as an opening position; the ROI in brackets divides the Total P&L by it.

**How to read it**

- **End date or period?** The big number and the first three rows are values on the end date; Deposited Capital (Period) counts only the movements between start and end.
- **The small caret** on a bar marks its value at the start of the period (hover it); Market Value turns red when it ends below it.
- **Net Worth includes cash**, unlike the "securities value" of a bank statement.
- **The Total P&L is not a daily change**: for today's pulse, see the small lines on Card 1 and Card 2.

---

## 🔗 Related

- 🔍 **[Positions & Analysis](positions.md)** — the same results, position by position
- 📊 **[Charts](charts.md)** — the Growth chart's **P&L** view follows your Total P&L over time
- 📐 **[Performance Metrics overview](../../financial-theory/technical-analysis/performance-metrics/index.md)** — every metric on these cards, with its formula
- 🛠️ **[Technical details](../../developer/frontend/pages/index.md#dashboard)** — for developers: where the cards' figures come from

---

*[⬅️ Back to Dashboard Overview](index.md)*
