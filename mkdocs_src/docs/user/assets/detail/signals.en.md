# 📊 Signals

The Signals panel lets you overlay **technical indicators**, **comparison series**, and **benchmark curves** on the price chart. Indicators are computed server-side by LibreFolio's backend **signal plugin platform** from the asset's stored price history — the browser only renders the results, so the chart, the diagnostics, and the AI Export snapshots all see the same numbers.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals" alt="Asset Signals Panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🧮 Available Signals

Signals are organized into **three categories**, each with its own dropdown at the top of the panel.

### 📉 Technical Indicators — 22 Backend Plugins

Asset charts can run **22 indicator plugins**, grouped by the market property they measure. The mathematics of each indicator lives in the Financial Theory section — follow the links below, or click the 📖 icon on any signal card to jump straight to its theory page.

| Family | Indicators |
|---|---|
| 📈 **Trend** (5) | [EMA](../../../financial-theory/technical-analysis/indicators/ema.md) · [SMA](../../../financial-theory/technical-analysis/indicators/sma.md) · [KAMA](../../../financial-theory/technical-analysis/indicators/kama.md) · [ADX](../../../financial-theory/technical-analysis/indicators/adx.md) · [Aroon](../../../financial-theory/technical-analysis/indicators/aroon.md) |
| ⚡ **Momentum** (6) | [RSI](../../../financial-theory/technical-analysis/indicators/rsi.md) · [MACD](../../../financial-theory/technical-analysis/indicators/macd.md) · [ROC](../../../financial-theory/technical-analysis/indicators/roc.md) · [Stochastic RSI](../../../financial-theory/technical-analysis/indicators/stochastic-rsi.md) · [PPO](../../../financial-theory/technical-analysis/indicators/ppo.md) · [CCI](../../../financial-theory/technical-analysis/indicators/cci.md) |
| 🌊 **Volatility** (4) | [Bollinger Bands](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md) · [ATR](../../../financial-theory/technical-analysis/indicators/atr.md) · [NATR](../../../financial-theory/technical-analysis/indicators/natr.md) · [Donchian Channels](../../../financial-theory/technical-analysis/indicators/donchian-channels.md) |
| 📊 **Volume** (2) | [OBV](../../../financial-theory/technical-analysis/indicators/obv.md) · [MFI](../../../financial-theory/technical-analysis/indicators/mfi.md) |
| ⚠️ **Risk** (5) | Underwater Drawdown · Rolling Return · Rolling Volatility · Rolling Sharpe Ratio · Rolling Beta |

For the risk family's concepts, see the [Risk Metrics](../../../financial-theory/technical-analysis/risk-metrics/index.md) theory pages ([Max Drawdown](../../../financial-theory/technical-analysis/risk-metrics/max-drawdown.md), [Volatility](../../../financial-theory/technical-analysis/risk-metrics/volatility.md), [Sharpe Ratio](../../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md)).

!!! info "Not every indicator can run on every asset"

    Indicators that need **high/low** prices (ADX, Aroon, ATR, NATR, CCI, Donchian
    Channels) or **volume** (OBV, MFI) become available only when your price history
    includes those fields — the signal card tells you which field is missing.
    **Rolling Beta** additionally asks you to pick a comparison asset.

### 💱 Data Comparison

Browser-computed overlays that normalize another series onto the same chart:

- ↔️ **Asset Comparison** — overlay another asset's performance, normalized to the same scale (e.g. a stock against its benchmark index)
- 💱 **FX Pair** — overlay a configured currency pair's rate

### 📐 Synthetic Benchmarks

Browser-computed **mathematical reference curves** generated purely from parameters — no market data needed: [Linear Growth](../../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md), [Compound Growth](../../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md), and [Sine Wave](../../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md).

---

## 🔍 Finding an Indicator

The indicator dropdown is a **collapsible tree grouped by family** (trend, momentum, volatility, volume, risk), with a search box on top:

- ⌨️ Type to filter across all families — the search matches names, descriptions, and even the data fields an indicator uses
- 📁 Each family shows a count badge and expands/collapses independently
- 🖱️ Full keyboard support: arrows move, `→`/`←` expand and collapse a family, `Enter` selects


<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals-tree" alt="Grouped indicator search on the asset signals panel">
</div>


---

## 🎛️ Signal Cards

Every added signal becomes a card showing:

- 📖 A **docs icon** linking to the indicator's Financial Theory page
- 🎚️ **Parameters inline** (numbers, dropdowns, checkboxes) — some tooltips contain LaTeX formulas rendered with KaTeX
- 🏷️ A **data badge** with the number of price points (📈) loaded
- 🗑️ Remove button; drag cards to reorder the overlays

### ⏳ While the Backend Computes

A small **spinner** appears on each card while the backend request is in flight. The transient state is deliberate: cards never flash a red "no data" error just because the answer has not arrived yet.

### 🩺 Per-Signal Diagnostics

After loading, a colored icon reports how the computation went — hover it for the full explanation:

- ℹ️ **Notice** (gray) / ⚠️ **Warning** (amber) — the signal was computed but with caveats: data gaps, an incomplete warm-up, or a range that starts before your data does
- 🔴 **Error** (red) — the signal could not be computed: missing OHLCV fields, not enough history for the chosen parameters, or a calculation failure

---

## 🧩 Incomplete Data: Partial Segments

Indicators that tolerate gaps (ADX, Aroon, ATR, NATR, CCI, Donchian, MFI, OBV) do not fail on a patchy price history: the backend selects the most recent **complete contiguous segment**, computes the indicator there, and reports the result as *partial* — the tooltip tells you which segment was used and how many points were excluded. All other indicators require gap-free input and explain why they cannot run instead of drawing a misleading line.

---

## 📉 Drawdown: Full-History Toggle

The **Underwater Drawdown** card carries a **Full history** checkbox (on by default): the decline is measured against the running peak of the *entire* available history, then sliced to the visible window — a peak from years ago still counts. Disable it for a faster, window-relative view. AI Export snapshots always use the full-history behavior regardless of this chart setting.


<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals-drawdown" alt="Drawdown signal card with the full-history toggle">
</div>


---

## 🛠️ How to Use

1. Click the **Signals** toggle button (📈) in the toolbar
2. The signals panel opens below the toolbar
3. Add signals from the three category dropdowns (**Technical Indicators**, **Data Comparison**, **Synthetic Benchmarks**)
4. Adjust each signal's parameters inline on its card
5. Signals are rendered as overlays directly on the chart

---

## 🧠 AI Export

The **AI Export** (:material-brain:) button in the page toolbar offers two Asset
tasks:

- **Position Review**
- **Asset Market Analysis**

The backend builds the snapshot from asset identity and valuation, normalized
price history, portfolio position context, and technical results from the shared
signal service. The browser does not recalculate indicators. Tasks appear only
when applicable to the asset and available data—for example, Position Review
requires an open position. See
[Asset AI Export](../../ai-export/asset.md) or the
[AI Export overview](../../ai-export/index.md).

---

## 📚 Deep Dive: Financial Theory

For a comprehensive mathematical treatment of each indicator — including formulas, signal processing equivalents, and practical interpretation:

:material-book-open-variant: **[Technical Indicators — Financial Theory](../../../financial-theory/technical-analysis/indicators/index.md)**

This reference page covers:

- 🔢 The **mathematical formulas** behind each indicator
- 🎛️ **Signal processing** equivalents (EMA = IIR filter, SMA = FIR filter, etc.)
- ⚡ The **"fast vs slow"** intuition in terms of filter cut-off frequencies
- 📈 **Practical examples** of crossover detection and trend identification
