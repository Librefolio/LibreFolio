# 📉 Technical Indicators

LibreFolio exposes **22 backend-calculated technical indicators**, grouped by the market property they measure. The same mathematical contracts power Asset charts, compatible FX charts, annotations, and analytical consumers such as AI Export.

!!! info "Price fields matter"

    Not every indicator can run on every series. **9 of the 22** are close-only
    indicators and work on both Assets and FX rates (EMA, SMA, KAMA, MACD, RSI,
    ROC, PPO, Stochastic RSI, Bollinger Bands). Indicators requiring high, low, or
    volume are Asset-only and report themselves as unavailable when those fields
    do not exist. The **Risk** family is also Asset-only: rolling risk readings are
    not produced for FX pairs.

---

## 📈 Trend

Trend indicators smooth price or measure whether a directional move is established.

| Indicator | Main Question | Data | Details |
|---|---|---|---|
| **EMA** | Where is the recent weighted trend? | Close | [📖](ema.md) |
| **SMA** | What is the equal-weight average price? | Close | [📖](sma.md) |
| **KAMA** | How should smoothing adapt to noise? | Close | [📖](kama.md) |
| **ADX** | How strong is the trend? | High, Low, Close | [📖](adx.md) |
| **Aroon** | How recently did new extremes occur? | High, Low | [📖](aroon.md) |

➡️ [Trend group overview](trend.md)

---

## ⚡ Momentum

Momentum indicators measure speed, directional pressure, and acceleration.

| Indicator | Main Question | Data | Details |
|---|---|---|---|
| **RSI** | Are buyers or sellers dominating? | Close | [📖](rsi.md) |
| **MACD** | Is trend momentum accelerating? | Close | [📖](macd.md) |
| **ROC** | How fast has price changed? | Close | [📖](roc.md) |
| **Stochastic RSI** | Where is RSI inside its recent range? | Close | [📖](stochastic-rsi.md) |
| **PPO** | What is moving-average momentum in percentage terms? | Close | [📖](ppo.md) |
| **CCI** | How far is price from its recent statistical mean? | High, Low, Close | [📖](cci.md) |

➡️ [Momentum group overview](momentum.md)

---

## 🌊 Volatility

Volatility indicators measure range, dispersion, and channel width rather than direction.

| Indicator | Main Question | Data | Details |
|---|---|---|---|
| **Bollinger Bands** | How wide is the statistical price envelope? | Close | [📖](bollinger-bands.md) |
| **ATR** | How large is the typical true range? | High, Low, Close | [📖](atr.md) |
| **NATR** | How large is volatility relative to price? | High, Low, Close | [📖](natr.md) |
| **Donchian Channels** | What are the period's highest high and lowest low? | High, Low | [📖](donchian-channels.md) |

➡️ [Volatility group overview](volatility.md)

---

## 📊 Volume

Volume indicators combine price direction with trading activity.

| Indicator | Main Question | Data | Details |
|---|---|---|---|
| **OBV** | Is signed volume accumulating or distributing? | Close, Volume | [📖](obv.md) |
| **MFI** | Is money flow buying or selling pressure? | High, Low, Close, Volume | [📖](mfi.md) |

➡️ [Volume group overview](volume.md)

---

## ⚠️ Risk

Risk indicators turn the price series itself into a rolling risk read-out. They are **Asset-only** — FX pairs do not produce them.

| Indicator | Main Question | Data | Details |
|---|---|---|---|
| **Underwater Drawdown** | How far below the running peak is the price? | Close | [📖](../risk-metrics/max-drawdown.md) |
| **Rolling Return** | What did the last window compound to? | Close | [📖](../../fundamentals/returns.md) |
| **Rolling Volatility** | How dispersed are recent returns? | Close | [📖](../risk-metrics/volatility.md) |
| **Rolling Sharpe Ratio** | Is excess return paying for its risk? | Close | [📖](../risk-metrics/sharpe-ratio.md) |
| **Rolling Beta** | How sensitive is the asset to a comparison asset? | Close + comparison asset | — |

➡️ [Risk metrics overview](../risk-metrics/index.md)

---

## 🔗 Related

- 🎯 **[Synthetic Benchmarks](../synthetic-benchmarks/index.md)** — Mathematical reference curves
- 📈 **[Interactive Chart](../../../user/assets/detail/chart.md)** — Where indicators are displayed
- 📊 **[Signals](../../../user/assets/detail/signals.md)** — How to configure overlays in LibreFolio
