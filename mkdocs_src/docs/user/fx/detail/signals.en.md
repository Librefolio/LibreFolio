# 📈 Signals

The Signals panel lets you overlay **technical indicators** on the FX chart. These are computed in real-time from the exchange rate data and help you identify trends, momentum shifts, and volatility patterns.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-signals" alt="FX Signals Panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📊 Available Indicators

### 📉 [EMA — Exponential Moving Average](../../../financial-theory/technical-indicators.md#ema)

Tracks the **trend** by smoothing daily price noise, giving more weight to recent values. When a short-period EMA crosses above a long-period EMA ("golden cross"), it signals upward momentum.

- ⚡ **Fast EMA**: Short period (e.g., 12 days) — reacts quickly to price changes
- 🐢 **Slow EMA**: Long period (e.g., 26 days) — smoother, shows the underlying trend

### 📊 [MACD — Moving Average Convergence Divergence](../../../financial-theory/technical-indicators.md#macd)

Measures the **momentum** by computing the difference between two EMAs. A positive MACD means the fast EMA is above the slow EMA (bullish), negative means the opposite (bearish).

- 📈 **MACD Line**: Difference between fast and slow EMA
- 〰️ **Signal Line**: EMA of the MACD line itself (smoothed momentum)
- 📊 **Histogram**: Visual difference between MACD and Signal lines

### 💪 [RSI — Relative Strength Index](../../../financial-theory/technical-indicators.md#rsi)

An **oscillator** (0–100) that measures the speed and magnitude of price changes. Values above 70 suggest overbought conditions, below 30 suggest oversold.

### 📏 [Bollinger Bands](../../../financial-theory/technical-indicators.md#bollinger-bands)

A **volatility envelope** around the price. The bands widen during volatile periods and contract during calm periods.

- 〰️ **Middle Band**: Simple Moving Average (SMA)
- 🔺 **Upper Band**: SMA + 2 standard deviations
- 🔻 **Lower Band**: SMA − 2 standard deviations

---

## 🛠️ How to Use

1. Click the **Signals** toggle button (📈) in the chart toolbar
2. The signals panel opens below the chart
3. Toggle each indicator **on/off** independently
4. Signals are rendered as overlays directly on the chart
5. Each indicator's parameters can be adjusted in [Chart Settings](../chart-settings.md)

---

## 📚 Deep Dive: Financial Theory

For a comprehensive mathematical treatment of each indicator — including formulas, signal processing equivalents, and practical interpretation:

:material-book-open-variant: **[Technical Indicators — Financial Theory](../../../financial-theory/technical-indicators.md)**

This reference page covers:

- 🔢 The **mathematical formulas** behind each indicator
- 🎛️ **Signal processing** equivalents (EMA = IIR filter, SMA = FIR filter, etc.)
- ⚡ The **"fast vs slow"** intuition in terms of filter cut-off frequencies
- 📈 **Practical examples** of crossover detection and trend identification
