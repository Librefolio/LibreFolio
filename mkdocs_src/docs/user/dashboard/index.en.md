# 📊 Dashboard

The Dashboard is your **portfolio's command center** — a single screen that tells you what your portfolio is worth, how it's performing, and where your money is allocated.

<div class="lf-screenshot-carousel" data-carousel="carousel-dashboard-main" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Main View (Absolute)" alt="Dashboard — Absolute Mode">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Main View (Percentage)" alt="Dashboard — Percentage Mode">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-now" data-title="📊 Allocation" alt="Dashboard — Allocation">
</div>

## 🗂️ Tabbed Layout

The Dashboard interface is organized into four primary tabs, allowing you to switch between different levels of detail:

1. **Overview** (default): Key metrics, cash balances, and visual charts of your portfolio.
2. **[Positions & Analysis](positions.md)**: Open holdings, weights, and detailed tax lot (FIFO) analysis.
3. **[Risk](#risk-tab)**: The **Portfolio risk** panel, which answers four questions about your portfolio's risk.
4. **Transactions**: The operations in the selected date range and broker scope, as a paginated, read-only list — double-click a row to open its detail viewer. See [Transactions](../transactions/index.md) for the full guide.

---

## 📈 Overview Tab

The Overview tab is the default landing page. It is structured into the following sections:

| Section | Description |
|---------|-------------|
| **[KPI Cards](kpi-cards.md)** | Summary of Net Worth, Period P&L, and rate-of-return metrics. |
| **Cash Balances** | Liquid balances grouped by currency across the active broker scope. |
| **[Growth Chart](charts.md#portfolio-growth-chart)** | Portfolio value over time in three views: absolute values (Abs), rates of return (%), and the money actually earned (P&L). |
| **[Allocation Panel](charts.md#allocation-panel)** | Donut and historical stacked charts grouped by Type, Sector, and Geography. |

### 🪙 Cash Balances

Directly below the KPI cards, the **Cash Balances** panel displays your total liquid cash aggregated by currency. For example, if you hold USD in broker A and EUR in broker B, both balances will be displayed side-by-side. 

When you apply a broker filter, the cash balances automatically update to reflect only the cash held within the selected brokers.

---

## 🛡️ Risk Tab {: #risk-tab }

The Risk tab holds the **Portfolio risk** panel, which answers four questions about your portfolio's risk: **How much can it hurt?**, **Am I as diversified as I think?**, **Am I being paid for this risk?** and **What if…?** It always covers your whole portfolio — every broker you own with a share above 0% — and follows the dashboard date range and target currency, but not the broker filter: when a filter is on, a subtitle says so. See [Risk Tab](risk.md) for the blocks and the tools they show.

---

## 🎛️ Date Range, Filters & AI Export

At the top right of the dashboard, you have several controls to customize your view:

- **Time range** — presets from 1 week to All-Time (MAX), or a custom range via the date picker.
- **Broker filter** — filters the metrics to one or more specific brokers; the Risk tab always covers every broker you own, and a subtitle says so when a filter is on.
- **Target currency** — converts all assets and cash balances dynamically into a single selected currency for aggregate viewing. The list offers your default currency and the currencies of your configured FX pairs — both ends of each pair. A currency that a [chain route](../fx/add-pair.md) only passes through is not offered: syncing a chain stores only the rate of its own pair, so LibreFolio has no rates to convert into that currency. To make a currency available, give it a pair of its own: pick **Create forex…** at the bottom of the list, or tick **Also create intermediate pairs** when you add a pair through a chain route.
- **AI Export** (:material-brain:) — opens a clipboard export. Choose **Data
  Snapshot** for factual data only, or an **analysis task** that automatically
  includes its instructions and response contract, then select the **detail
  level** (Compact, Standard, or Full). The backend snapshot follows the active
  broker filter, date range, and target currency; LibreFolio does not contact an
  AI service. See [Portfolio AI Export](../ai-export/portfolio.md) or the
  [AI Export overview](../ai-export/index.md).

The time range, the broker filter and the target currency stay as you set them for the rest of your session in this browser tab — a page reload keeps them too — and reset when you log out. The time range is shared with the other pages that have one (the Assets and FX pages, their detail pages, and each broker's page), so a change made there shows up here as well. Next to **AI Export**, the **Refresh** button (:material-refresh:) recalculates everything on demand: see [Coming back and refreshing](#coming-back-and-refreshing).

!!! tip "Scope matters"

    When you filter to a single broker, cash transfers *to other brokers* become external flows for that scope. This affects [Deposited Capital](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) and [P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md) calculations.

!!! note "Sharing affects these numbers"

    The dashboard counts only the brokers you **own** with a share above 0%, and every amount from them is **scaled by your ownership share**: an Owner with a 50% share sees half of that broker's value, income, and P&L counted in the totals. Brokers where you are an **Editor** or a **Viewer** — who always carry a 0% share by rule — are left out, like those you own with a 0% share: they are missing from the totals, from the broker filter, from the Positions tab (Performance view and lots panel included), from the Risk tab and from the Transactions tab. You see them on their own broker page, where Editors and Viewers get the broker's **full** amounts. See [Broker Sharing](../brokers/sharing.md) for details.

---

## 🔄 Coming back and refreshing {: #coming-back-and-refreshing }

Come back to the Dashboard — from the sidebar, or with the **←** back button of an asset page — and it shows at once what it showed when you left: the KPI cards, the charts, the Positions tab with its Performance view and [FIFO Lots Analysis](positions.md#fifo-lots-analysis) panel, and the Risk tab. There are no loading placeholders, and the KPI figures appear at their value instead of counting up from zero. If you changed the time range on another page in the meantime, the Dashboard opens on that range instead.

- **If nothing changed in the meantime**, that is all: LibreFolio recalculates nothing.
- **If something changed** — for example a transaction; prices, rates or events entered by hand or brought in by a sync; an asset edited or merged; a change to one of your brokers or to your access to it; or the live price that an asset page checks while it is open — the old figures stay on screen while LibreFolio recalculates in the background, then the numbers move to the new values. A price or rate sync that brought nothing new is not a change.

The **Refresh** button recalculates everything, even when nothing changed: the figures, the Performance view, the lots panel and the Risk tab. What you see stays on screen meanwhile.

If a recalculation fails, the figures already on screen stay and a message tells you so. On the Risk tab, this holds only for figures of the period and currency you are viewing: if you switch to a period or a currency the tab has no figures for yet and the calculation fails, it shows *Risk data could not be loaded.* in place of its levels, rather than the figures of your previous choice.

---

## 🌡️ Data Quality Banner

If any prices or FX rates are missing on the end date, a banner appears at the top explaining which assets could not be valued.
<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="data-quality-banner" alt="Dashboard data-quality banner with per-asset links">
</div>
 Assets without a price provider (entered manually, such as real-estate crowdfunding projects) are valued at the price of their latest transaction, unless you enter a more recent price yourself — this is intentional and does not generate a warning. An asset that does have a price provider but still has no market price on the end date, more than two weeks after you first bought it, is valued meanwhile at the price of its latest transaction too, and the banner lists it: a bond bought at issue, before its first quote, for example.

The banner also warns you when an asset you hold has a price provider but its latest price is **more than a week old** on the end date: click **Sync prices** to fetch the missing prices, and the warning goes away once they are up to date. Manual assets are never flagged this way, since there is nothing to sync.

It also lists the assets with a **missing purchase cost**: a transfer or an adjustment that brought units in without a cost basis. LibreFolio cannot know what those units cost, so it counts them at zero in your purchase cost and shows that position's average cost and unrealized P&L as unavailable (`—`). To fix it, find that transfer or adjustment among your [transactions](../transactions/index.md) and give it its cost basis.

Exchange rates are checked for every transaction up to the end date — each purchase, sale and cash movement is converted at the rate of its own date — and, to value what you hold, on each day of the period on screen. When a configured FX pair with a provider has **no rate** for some of those dates, the banner lists it with the span of the missing dates. LibreFolio converts an amount with the latest rate on or before its date, however old, so these dates come *before* the pair's first stored rate — often well before the period on screen, because every past transaction counts towards totals such as your Total P&L and your purchase cost. Click **Sync rates** to fill them:

- LibreFolio downloads that span of dates with **one extra week on each side** (never beyond today), whatever period the dashboard is showing. The extra week covers weekends and bank holidays, when providers publish nothing: such a day at the edge of the span then takes the rate of the previous working day.
- Once the download is over, the dashboard refreshes and a message reports the result for each pair.
- If the download goes through but the same pairs are still flagged, the provider has no rates for the dates still missing — typically because they come before the start of its history. The message then turns into a warning that says so: enter those rates by hand in the pair's [Data Editor](../fx/detail/data-editor.md).

Pairs with manual rates only (no provider) get a warning of their own: its **View FX** button opens the page of the first pair it lists, where you add the rates yourself.

!!! tip "Fill a pair's whole history at once"

    Open the [FX page](../fx/index.md), choose the **All** (MAX) range and click [Sync All](../fx/sync.md): LibreFolio downloads everything the providers publish for your pairs, up to today. A pair you add with a provider does this by itself — see [Adding a Currency Pair](../fx/add-pair.md).

---

## 🔗 In this section

- 💰 **[KPI Cards](kpi-cards.md)** — Net Worth, Period P&L, and Returns explained
- 📊 **[Charts](charts.md)** — Growth Chart and Allocation Panel explained
- 🔍 **[Positions & Analysis](positions.md)** — Open positions, table vs. map views, and detailed FIFO tax lot analysis.

## 🔗 Related theory

- **[NAV / Net Worth](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- **[Book Value](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)**
- **[Period P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)**
- **[Deposited Capital & Total P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- **[Performance Metrics overview](../../financial-theory/technical-analysis/performance-metrics/index.md)**
