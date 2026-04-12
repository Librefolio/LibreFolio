# 📈 Signals

The Signals panel lets you overlay **technical indicators** on the FX chart. These are computed in real-time from the exchange rate data and help you identify trends, momentum shifts, and volatility patterns.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-signals" alt="FX Signals Panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📊 Available Indicators

### 📉 [EMA — Exponential Moving Average](../../../financial-theory/technical-analysis/indicators/ema.md)

Smooths daily rate noise to reveal the **underlying trend**. In FX, an EMA crossing above the rate line often suggests a weakening base currency (or strengthening quote currency). Configurable period: shorter = more reactive, longer = smoother.

### 📊 [MACD — Moving Average Convergence Divergence](../../../financial-theory/technical-analysis/indicators/macd.md)

Measures the **momentum** by computing the difference between a fast and a slow EMA. A positive MACD means the fast EMA is above the slow EMA (bullish), negative means the opposite (bearish). Useful in FX for detecting trend reversals and momentum shifts.

- 📈 **MACD Line**: Difference between fast and slow EMA
- 〰️ **Signal Line**: EMA of the MACD line itself (smoothed momentum)
- 📊 **Histogram**: Visual difference between MACD and Signal lines

### 💪 [RSI — Relative Strength Index](../../../financial-theory/technical-analysis/indicators/rsi.md)

An **oscillator** (0–100) that measures the speed and magnitude of price changes. In FX, values above 70 may suggest the currency pair is overbought, below 30 suggests oversold. Useful for spotting potential reversals.

### 📏 [Bollinger Bands](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md)

A **volatility envelope** around the price. The bands widen during volatile periods and contract during calm periods. In FX, a rate touching the upper band may signal overbought conditions, while touching the lower band may signal oversold.

- 〰️ **Middle Band**: Simple Moving Average (SMA)
- 🔺 **Upper Band**: SMA + 2 standard deviations
- 🔻 **Lower Band**: SMA − 2 standard deviations

---

## 🛠️ How to Use

1. Click the **Signals** toggle button (📈) in the chart toolbar
2. The signals panel opens below the chart
3. Add indicators from the categorized dropdowns (Technical Indicators, Data Comparison, Synthetic Benchmarks)
4. Each indicator's parameters can be adjusted inline
5. Signals are rendered as overlays directly on the chart

---

## 📚 Deep Dive: Financial Theory

For a comprehensive mathematical treatment of each indicator — including formulas, signal processing equivalents, and practical interpretation:

:material-book-open-variant: **[Technical Indicators — Financial Theory](../../../financial-theory/technical-analysis/indicators/index.md)**

This reference page covers:

- 🔢 The **mathematical formulas** behind each indicator
- 🎛️ **Signal processing** equivalents (EMA = IIR filter, SMA = FIR filter, etc.)
- ⚡ The **"fast vs slow"** intuition in terms of filter cut-off frequencies
- 📈 **Practical examples** of crossover detection and trend identification
