# 📊 Signals

Signals are lines drawn over the price chart: **technical indicators** that LibreFolio computes from the stored prices, **another asset or a currency pair** to compare with, and **reference curves** such as a steady growth. Use them to read trend, momentum, volatility and risk at a glance.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals" alt="Asset Signals Panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Add a signal

1. Open the **Signals** panel above the chart.
2. Pick a signal from one of its three menus: **Technical Indicators**, **Data Comparison** or **Synthetic Benchmarks**. In the indicators menu, type to search by name, description or the data an indicator uses.
3. Set its parameters on the card that appears; the chart follows.
4. Drag a card by its handle (arrows on a phone) to change the order, or remove it with 🗑️.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals-tree" alt="Grouped indicator search on the asset signals panel">
</div>

Each line of a card, and each zone of indicators such as RSI, has its own colour and line style. Your signals are remembered for this asset, in this browser.

---

## 📉 Technical indicators {: #technical-indicators }

**22 indicators**, grouped by what they measure. Each name links to its theory page; the **?** on a card opens the same page.

### 📈 Trend

- [SMA](../../../financial-theory/technical-analysis/indicators/sma.md) — simple average of the closing prices
- [EMA](../../../financial-theory/technical-analysis/indicators/ema.md) — average that weighs recent prices more
- [KAMA](../../../financial-theory/technical-analysis/indicators/kama.md) — average that adapts to market noise
- [ADX](../../../financial-theory/technical-analysis/indicators/adx.md) — trend strength, with +DI and −DI for its direction
- [Aroon](../../../financial-theory/technical-analysis/indicators/aroon.md) — how recent the latest highs and lows are

### ⚡ Momentum

- [RSI](../../../financial-theory/technical-analysis/indicators/rsi.md) — buying and selling pressure, with overbought and oversold zones
- [MACD](../../../financial-theory/technical-analysis/indicators/macd.md) — momentum between two moving averages, with a signal line and a histogram
- [PPO](../../../financial-theory/technical-analysis/indicators/ppo.md) — the same momentum, in percent
- [ROC](../../../financial-theory/technical-analysis/indicators/roc.md) — speed of the price change
- [Stochastic RSI](../../../financial-theory/technical-analysis/indicators/stochastic-rsi.md) — where RSI sits within its recent range
- [CCI](../../../financial-theory/technical-analysis/indicators/cci.md) — distance from the average price

### 🌊 Volatility

- [Bollinger Bands](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md) — a band around a moving average that widens with volatility
- [ATR](../../../financial-theory/technical-analysis/indicators/atr.md) — volatility in price units
- [NATR](../../../financial-theory/technical-analysis/indicators/natr.md) — volatility in percent of the price
- [Donchian Channels](../../../financial-theory/technical-analysis/indicators/donchian-channels.md) — the highest high and the lowest low of the period

### 📊 Volume

- [OBV](../../../financial-theory/technical-analysis/indicators/obv.md) — pressure of the volume behind price moves
- [MFI](../../../financial-theory/technical-analysis/indicators/mfi.md) — volume-weighted momentum

### ⚠️ Risk

- [Underwater Drawdown](../../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md) — how far the price is below its running peak ([full history](#drawdown-full-history))
- [Rolling Return](../../../financial-theory/fundamentals/returns.md#rolling-return-sessions) — price-only return over a sliding window
- [Rolling Volatility](../../../financial-theory/technical-analysis/risk-metrics/volatility.md) — annualized volatility over a sliding window
- [Rolling Sharpe Ratio](../../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md) — excess return per unit of volatility over a sliding window
- [Rolling Beta](../../../financial-theory/technical-analysis/risk-metrics/beta-active-return.md) — how strongly the asset follows a comparison asset you pick

Periods count **sessions**, the days the asset was quoted: an SMA 200 covers 200 sessions, about 290 calendar days ([why](../../../financial-theory/technical-analysis/indicators/index.md)). The **Window** of the four rolling risk signals counts days with a quote too; for Rolling Beta, days on which both assets were quoted.

!!! info "Not every indicator can run on every asset"

    ADX, Aroon, ATR, NATR, CCI, Donchian Channels and MFI need **high** and **low** prices; OBV and MFI need the **volume**. Without them, the card tells you which data is missing.

### 📉 Drawdown over the full history {: #drawdown-full-history }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals-drawdown" alt="Drawdown signal card with the full-history toggle">
</div>

The **Underwater Drawdown** card has a **Full history** checkbox, on by default: the drop is measured from the highest price of the asset's whole history, even years before the dates on screen. Untick it for a quicker view, measured from the highest price within the dates on screen.

---

## 💱 Compare with an asset or a currency pair {: #data-comparison }

The **Data Comparison** menu adds:

- **Asset Comparison** — another asset on the same chart, such as a stock against its index ETF. In **%** view both lines start at 0 %.
- **FX Pair** — the rate of one of your currency pairs.

**Sync** (🔄) on an Asset Comparison card downloads that asset's prices for the chart's dates, together with the exchange rates that convert it, for pairs that exist. When the pair is missing, an amber ⚠️ on the card creates it; when its rates are missing, an amber 🔄 syncs them.

In [Rolling Return](chart.md#rolling-return) mode only Asset Comparison stays: each compared asset becomes a rolling return, with the same window and currency. The other signals are hidden, not deleted, and come back in **Prices** mode.

---

## 📐 Synthetic benchmarks

Reference curves drawn from their parameters alone, with no market data:

- [Linear Growth](../../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md) — $y(t) = y_0\,(1 + r\,t)$
- [Compound Growth](../../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) — $y(t) = y_0\,(1 + r)^t$
- [Sine Wave](../../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md) — $y(t) = A \sin(2\pi t / T) + y_0$

---

## 🩺 Read a signal card

- A **spinner** turns while the signal is computed.
- **📈 N** is the number of price points loaded.
- A grey **ℹ** — computed, with a small caveat: a short gap or a nearly complete warm-up. Hover the icon for the details.
- An amber **⚠** — computed, with a caveat worth a look: larger gaps, an incomplete warm-up, or data that starts after the first date on screen. The card turns amber too.
- A red **⚠** — not computed: a missing price field, too little history for the parameters, no data at all, or a calculation error. The card turns red.

??? note "🧩 Patchy price history — when a signal is partial"

    ADX, Aroon, ATR, NATR, CCI, Donchian Channels, MFI and OBV can run on a patchy history: they use the most recent stretch without gaps that is long enough, and the tooltip names that stretch and how many points were left out. The other indicators need a history without gaps, and explain why they cannot run rather than draw a misleading line. A weekend or a market holiday is not a gap.

---

## 🔗 Related

- 📚 **[Technical Indicators](../../../financial-theory/technical-analysis/indicators/index.md)** — Every indicator's formula and how to read it
- ⚠️ **[Risk Metrics](../../../financial-theory/technical-analysis/risk-metrics/index.md)** — The metrics behind the risk signals
- 🧠 **[Asset AI Export](../../ai-export/asset.md)** — Technical indicators computed by the same backend, exported for an AI assistant
- 🛠️ **[Signal Plugin Guide](../../../developer/architecture/patterns/signal_plugin_guide.md)** — For developers: how indicators are computed, checked and added
