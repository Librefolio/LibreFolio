# 📊 Signals

The Signals panel lets you overlay **technical indicators** on the price chart. These are computed in real-time from the asset's price data and help identify trends, momentum shifts, and volatility patterns.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals" alt="Asset Signals Panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📊 Available Indicators

### 📉 [EMA — Exponential Moving Average](../../../financial-theory/technical-indicators.md#ema)

Smooths daily price noise to reveal the **underlying trend**. An EMA crossing above the price line often signals a downward trend. Configurable period: shorter = more reactive, longer = smoother.

### 📊 [MACD — Moving Average Convergence Divergence](../../../financial-theory/technical-indicators.md#macd)

Measures **momentum** by computing the difference between a fast and a slow EMA. Useful for detecting trend reversals and momentum shifts.

- 📈 **MACD Line**: Difference between fast and slow EMA
- 〰️ **Signal Line**: EMA of the MACD line itself (smoothed momentum)
- 📊 **Histogram**: Visual difference between MACD and Signal lines

### 💪 [RSI — Relative Strength Index](../../../financial-theory/technical-indicators.md#rsi)

An **oscillator** (0–100) that measures the speed and magnitude of price changes. Values above 70 may suggest the asset is overbought, below 30 suggests oversold.

### 📏 [Bollinger Bands](../../../financial-theory/technical-indicators.md#bollinger-bands)

A **volatility envelope** around the price. The bands widen during volatile periods and contract during calm periods.

- 〰️ **Middle Band**: Simple Moving Average (SMA)
- 🔺 **Upper Band**: SMA + 2 standard deviations
- 🔻 **Lower Band**: SMA − 2 standard deviations

### 🔀 Asset Comparison

Compare the current asset's performance against **another asset**. The comparison asset's price is overlaid on the chart, normalized to the same scale. Useful for relative performance analysis (e.g., compare a stock against its benchmark index).

---

## 🛠️ How to Use

1. Click the **Signals** toggle button (📈) in the toolbar
2. The signals panel opens below the toolbar
3. Add indicators from the categorized dropdowns
4. Each indicator's parameters can be adjusted inline
5. Signals are rendered as overlays directly on the chart

---

## 📚 Deep Dive: Financial Theory

For a comprehensive mathematical treatment of each indicator — including formulas, signal processing equivalents, and practical interpretation:

:material-book-open-variant: **[Technical Indicators — Financial Theory](../../../financial-theory/technical-indicators.md)**

This reference page covers:

- 🔢 The **mathematical formulas** behind each indicator
- 🎛️ **Signal processing** equivalents (EMA = IIR filter, SMA = FIR filter, etc.)
- ⚡ The **"fast vs slow"** intuition in terms of filter cut-off frequencies
- 📈 **Practical examples** of crossover detection and trend identification

