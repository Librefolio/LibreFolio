# 📉 Technical Indicators

LibreFolio provides four technical indicators as chart overlays. Each indicator is explained from two complementary perspectives: the **financial** interpretation that traders use daily, and the **signal processing** equivalent that engineers will recognise instantly.

!!! info "Why two perspectives?"

    Financial markets are **not** stationary LTI (Linear Time-Invariant) systems — they
    are noisy, chaotic, and their spectral content shifts over time. Yet the mathematical
    tools we apply to extract trend, momentum, or volatility are *exactly* the same
    discrete-time filters taught in any signal processing course.

---

## 📋 Indicator Overview

| Indicator | What It Measures | Key Use | Details |
|-----------|-----------------|---------|---------|
| **EMA** | Trend direction | Golden/death cross detection | [📖](ema.md) |
| **MACD** | Momentum / trend acceleration | Bullish/bearish crossovers | [📖](macd.md) |
| **RSI** | Overbought / oversold | Mean-reversion setups | [📖](rsi.md) |
| **Bollinger Bands** | Volatility envelope | Squeeze → breakout detection | [📖](bollinger-bands.md) |

---

## 🔗 Related

- 🎯 **[Synthetic Benchmarks](../synthetic-benchmarks/index.md)** — Mathematical reference curves
- 📈 **[Interactive Chart](../../../user/assets/detail/chart.md)** — Where indicators are displayed
- 📊 **[Signals](../../../user/assets/detail/signals.md)** — How to configure overlays in LibreFolio


