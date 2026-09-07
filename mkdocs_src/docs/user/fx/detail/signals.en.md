# 📈 Signals

The Signals panel lets you overlay **technical indicators**, **comparison series**, and **benchmark curves** on the FX chart. Indicators are computed server-side by LibreFolio's backend **signal plugin platform** from the pair's stored rate history — the browser only renders the results.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-signals" alt="FX Signals Panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🧮 Available Signals

Signals are organized into **three categories**, each with its own dropdown at the top of the panel: **Technical Indicators**, **Data Comparison**, and **Synthetic Benchmarks**.

### 📉 Technical Indicators — 9 FX-Compatible Plugins

Of the 22 backend indicator plugins, **9 run on FX close rates**. The mathematics of each indicator lives in the Financial Theory section — follow the links below, or click the 📖 icon on any signal card to jump straight to its theory page.

| Family | Indicators |
|---|---|
| 📈 **Trend** (3) | [EMA](../../../financial-theory/technical-analysis/indicators/ema.md) · [SMA](../../../financial-theory/technical-analysis/indicators/sma.md) · [KAMA](../../../financial-theory/technical-analysis/indicators/kama.md) |
| ⚡ **Momentum** (5) | [RSI](../../../financial-theory/technical-analysis/indicators/rsi.md) · [MACD](../../../financial-theory/technical-analysis/indicators/macd.md) · [ROC](../../../financial-theory/technical-analysis/indicators/roc.md) · [Stochastic RSI](../../../financial-theory/technical-analysis/indicators/stochastic-rsi.md) · [PPO](../../../financial-theory/technical-analysis/indicators/ppo.md) |
| 🌊 **Volatility** (1) | [Bollinger Bands](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md) |

!!! info "Why only 9?"

    FX rates have a single value per day — there is no high, low, or volume. The
    remaining 13 plugins need those extra fields (or compute portfolio-style risk
    metrics) and are available on [asset charts](../../assets/detail/signals.md)
    instead. The full inventory lives in
    [Technical Indicators — Financial Theory](../../../financial-theory/technical-analysis/indicators/index.md).

### 💱 Data Comparison

Browser-computed overlays that normalize another series onto the same chart:

- 💱 **FX Pair** — overlay another configured pair (e.g. compare EUR/USD against GBP/USD); pairs already picked by another signal are marked 📌, and the current page's pair wears a 👑
- ↔️ **Asset Comparison** — overlay an asset's performance next to the exchange rate

### 📐 Synthetic Benchmarks

Browser-computed **mathematical reference curves** generated purely from parameters — no market data needed: [Linear Growth](../../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md), [Compound Growth](../../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md), and [Sine Wave](../../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md).

---

## 🔍 Finding an Indicator

The indicator dropdown is a **collapsible tree grouped by family** (trend, momentum, volatility), with a search box on top — type to filter across all families at once; arrows, `→`/`←`, and `Enter` navigate the tree.

*Screenshot coming: the grouped indicator tree open on the FX Signals panel.*

---

## 🎛️ Signal Cards

Every added signal becomes a card showing:

- 📖 A **docs icon** linking to the indicator's Financial Theory page
- 🎚️ **Parameters inline** (period, signal period, …) — some tooltips contain LaTeX formulas rendered with KaTeX
- 🏷️ A **data badge** with the number of rate points (📈) loaded
- 🗑️ Remove button; drag cards to reorder the overlays

A small **spinner** appears on each card while the backend request is in flight. After loading, a colored icon reports per-signal **diagnostics** — hover it for details: ℹ️ notice (gray) and ⚠️ warning (amber) when the signal computed with caveats (data gaps, incomplete warm-up, data starting after the chart range), 🔴 error (red) when it could not compute at all (not enough history, missing fields). If a card reports missing data, syncing the pair usually fills the gap.

---

## 🛠️ How to Use

1. Click the **Signals** toggle button (📈) in the chart toolbar
2. The signals panel opens below the chart
3. Add signals from the three category dropdowns (Technical Indicators, Data Comparison, Synthetic Benchmarks)
4. Adjust each signal's parameters inline on its card
5. Signals are rendered as overlays directly on the chart

---

## 🧠 AI Export

The **AI Export** (:material-brain:) button in the page toolbar offers two FX
tasks:

- **FX Pair Analysis**
- **FX Exposure Impact**

The backend snapshot uses the page's canonical currency pair, selected range,
target currency, rate history, and shared technical-signal results. For FX
Exposure Impact, exposure is limited to cash currencies and position trading or
valuation currencies directly linkable to the pair; it does **not** look through
funds or issuers to infer hidden currency exposure. See
[FX AI Export](../../ai-export/fx.md) or the
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
