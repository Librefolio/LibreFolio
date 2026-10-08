# 📈 Interactive Chart

The chart is the heart of the asset page: the price history, or how much the price moved over a rolling window. Scroll to zoom, drag to pan, and hover a point for its values.

_Last updated: 2026-10-08_

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Asset Price Chart" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Prices or Rolling Return {: #primary-modes }

The two buttons above the chart choose what it draws:

- **Prices** — the price history, with the asset's [events](events.md) as markers.
- **Rolling Return** — for every date, the price change over a window you choose ([below](#rolling-return)).

The page always opens on **Prices**.

### 🗓️ Rolling Return Window {: #rolling-return }

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart-rolling-return" alt="Asset chart in Rolling Return mode with the 1Y window and one comparison asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

This view answers *how much has the price moved over the window, at every date?* Each point compares that day's close with the close exactly $N$ calendar days earlier:

$$
R(d) = \frac{P(d)}{P(d-N)} - 1
$$

where $P$ is the last close known on that day, in the chart's currency → [Rolling return over calendar days](../../../financial-theory/fundamentals/returns.md#rolling-return-calendar).

Pick $N$ with the **Window** control next to the two buttons:

- **1W**, **1M**, **3M**, **1Y** — 7, 30, 90 and 365 days.
- **Custom** — a whole number with **W**, **M** or **Y**, counted as 7, 30 and 365 days: `3M` is 90 days.
- **?** opens this section of the manual.

The window may be longer than the dates on screen: LibreFolio reads the older prices it needs. It is remembered for this asset, in this browser.

How to read it:

- **Above zero**, the price is higher than $N$ days before; **below zero**, lower.
- **Hover a point**: ↩ gives the date it is compared with; 📅 and 💱 give the dates of the price and of the exchange rates actually used, when one of them is older.
- **[Asset comparisons](signals.md#data-comparison)** turn into rolling returns too, with the same window and currency.
- **Price only**: dividends, interest and your transactions are not included.

??? note "🧩 Gaps and short lines — when the history is incomplete"

    A point stays empty, never estimated, when either of its two prices is missing or not positive. Each line starts on the first date it can be computed, so a recent asset or a missing exchange rate shortens only its own line, and a later missing price leaves a gap. When only part of the range can be computed, a note under the chart says so; when nothing can, a message replaces the chart.

---

## 🎛️ Choose what the chart shows

### 📅 Date range

The date range in the page toolbar sets the dates on screen: **1W**, **1M**, **3M**, **6M**, **1Y**, **2Y**, **YTD**, **MAX**, or **Custom** with a calendar. With spare room on the bar, more presets appear (3Y, 5Y, 10Y, WTD, MTD, QTD). The range you pick follows you to the Dashboard, broker, asset and FX pages of the same browser tab.

On a long range the chart may group the days into weeks or months to stay readable: a **Weekly** or **Monthly** badge at its top left says so.

### 💱 Convert to another currency

**Convert to**, next to the price, shows the chart in another currency, with a dashed 💱 line for the price in the asset's own currency. The menu lists the currencies your FX pairs can reach; **Create forex…** at its bottom adds a missing pair. Rolling returns are computed in the chosen currency too.

??? note "💱 When an exchange rate is missing"

    A banner above the chart names the pair, with a shortcut to create it or to open it. The page's **Sync** downloads the rates of the pairs that exist; it never creates one.

### 📊 Line or candles, Abs or %

In **Prices** mode, the buttons at the top left of the chart switch:

- between a **line** and **candlesticks**, which need the open, high and low prices;
- between **Abs**, the prices, and **%**, the change since the first day of the range.

---

## 🧰 Tools on the chart

The three buttons at the top right of the chart:

- **📏 Add measurement** — compare two points: see [Measures](measures.md). **Prices** and **Rolling Return** keep separate measures.
- **✏️ Edit Prices & Events** — opens the [Data Editor](data-editor.md), in **Prices** mode only.
- **⚙️ Aesthetics** — **Area Fill**, **Baseline Colors** (green above the starting value, or above zero in %, red below), **Grid Lines**, **Stale Gradient** (fades the points whose price or exchange rate is carried over from an earlier day) and **Y-Axis Scale** (**Auto**, **Include 0** or **Custom** limits). Candlesticks turn off Area Fill, Baseline Colors and Stale Gradient.

These settings and your signals are remembered for this asset, in this browser. To change them for every asset at once, use **Settings** on the [Assets page](../index.md): see [Chart Settings](../../fx/chart-settings.md).

---

## 🔗 Related

- 📊 **[Signals](signals.md)** — Overlay technical indicators
- 📐 **[Measures](measures.md)** — Measure price differences
- 📅 **[Events](events.md)** — Understand event markers
- 📚 **[Returns & Growth Rates](../../../financial-theory/fundamentals/returns.md)** — How simple, annualized and rolling returns are calculated
- 🛠️ **[Chart internals](../../../developer/frontend/components/charts.md)** — For developers: the two modes, where the chart state lives, and how the page syncs
