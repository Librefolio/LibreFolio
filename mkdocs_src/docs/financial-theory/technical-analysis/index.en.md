# 📊 Technical Analysis

Technical analysis studies **price patterns and market dynamics** to identify trends, momentum, and volatility. Unlike fundamental analysis (which evaluates a company's intrinsic value), technical analysis focuses purely on historical price and volume data.

---

## 📖 What's Inside

### 📉 [Indicators](indicators/index.md)

Chart overlays that extract trend, momentum, volatility, or volume information from market data. LibreFolio implements **17 backend indicators**, each explained from both a **financial** and **signal processing** perspective:

- 📈 **[Trend](indicators/trend.md)** — EMA, SMA, KAMA, ADX, Aroon
- ⚡ **[Momentum](indicators/momentum.md)** — RSI, MACD, ROC, Stochastic RSI, PPO, CCI
- 🌊 **[Volatility](indicators/volatility.md)** — Bollinger Bands, ATR, NATR, Donchian Channels
- 📊 **[Volume](indicators/volume.md)** — OBV, MFI

### 🎯 [Synthetic Benchmarks](synthetic-benchmarks/index.md)

Mathematical reference curves overlaid on charts for comparison. Unlike indicators (computed *from* market data), benchmarks are generated purely from parameters:

- **[Linear Growth](synthetic-benchmarks/linear.md)** — Simple interest model
- **[Compound Growth](synthetic-benchmarks/compound.md)** — Compound interest model
- **[Sine Wave](synthetic-benchmarks/sine-wave.md)** — Cyclic reference for seasonality

---

## ⚡ The "Fast" vs "Slow" Intuition

In finance, *fast* and *slow* refer to the **time constant** ($\tau$) of the underlying filter.

| Property | Fast (small $N$) | Slow (large $N$) |
|---|---|---|
| Cut-off frequency $f_c$ | Higher | Lower |
| Noise rejection | Poor — lets HF through | Good — strong smoothing |
| Phase lag | Small — reacts quickly | Large — significant delay |
| Typical $N$ | 9, 12, 14 | 26, 50, 200 |

---

## 🔗 Related Sections

- 🏦 **[Instruments](../instruments/index.md)** — The assets these indicators analyze
- 📐 **[Fundamentals](../fundamentals/index.md)** — Returns, day count conventions
- 📈 **[Portfolio Theory](../portfolio-theory/index.md)** — Risk metrics and allocation

