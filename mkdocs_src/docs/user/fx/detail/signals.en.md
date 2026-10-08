# 📈 Signals

The **Signals** panel draws technical indicators, comparison series and benchmark curves on the FX
chart. LibreFolio computes the indicators from the pair's stored rates.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-signals" alt="FX Signals Panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Add a signal

1. Click the **Signals** bar above the chart to unfold the panel.
2. Pick a signal from one of the three dropdowns: **Technical Indicators**, **Data Comparison** or
   **Synthetic Benchmarks**.
3. Adjust its parameters on its card: the chart follows.
4. Drag the cards to reorder them; 🗑️ removes one.

The signals you add are kept with this pair's [chart settings](../chart-settings.md).

---

## 🧮 Technical indicators — 9 for FX

Nine indicators work on FX rates. Follow the links below, or click 📖 on a card, for the math
behind each one.

| Family | Indicators |
|---|---|
| 📈 **Trend** (3) | [EMA](../../../financial-theory/technical-analysis/indicators/ema.md) · [SMA](../../../financial-theory/technical-analysis/indicators/sma.md) · [KAMA](../../../financial-theory/technical-analysis/indicators/kama.md) |
| ⚡ **Momentum** (5) | [RSI](../../../financial-theory/technical-analysis/indicators/rsi.md) · [MACD](../../../financial-theory/technical-analysis/indicators/macd.md) · [ROC](../../../financial-theory/technical-analysis/indicators/roc.md) · [Stochastic RSI](../../../financial-theory/technical-analysis/indicators/stochastic-rsi.md) · [PPO](../../../financial-theory/technical-analysis/indicators/ppo.md) |
| 🌊 **Volatility** (1) | [Bollinger Bands](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md) |

??? info "🤔 Why only 9? — the other indicators need more than a daily rate"

    FX rates have one value per day, with no high, low or volume. The other indicators need those
    fields, or measure portfolio-style risk, so they are available on
    [asset charts](../../assets/detail/signals.md) only. The full list is in
    [Technical Indicators — Financial Theory](../../../financial-theory/technical-analysis/indicators/index.md).

### 🔍 Finding an indicator

The **Technical Indicators** dropdown is a tree grouped by family (trend, momentum, volatility), with
a search box on top: type to filter every family at once. The arrow keys and `Enter` work too.

*Screenshot coming: the grouped indicator tree open on the FX Signals panel.*

---

## 💱 Data comparison

- 💱 **FX Pair** — another of your pairs, e.g. GBP/USD next to EUR/USD. In the list, 👑 marks this
  page's pair and 📌 a pair already used by another signal.
- ↔️ **Asset Comparison** — an asset's price next to the rate.

A comparison card has buttons to sync the compared pair or asset and to open its page. In % view
both curves start at 0 %, so their moves compare directly.

## 📐 Synthetic benchmarks

Reference curves built from parameters alone, with no market data:
[Linear Growth](../../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md),
[Compound Growth](../../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) and
[Sine Wave](../../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md).

---

## 🎛️ Read a signal card

- 📖 opens the indicator's theory page; hover a parameter for help.
- A badge counts the data points loaded for the signal.
- A spinner turns while the signal is computed. Then an icon may report a problem — hover it for
  the details:
    - grey ℹ️ — a small caveat;
    - amber ⚠️ — computed with caveats, such as gaps, a short warm-up or data that starts after the
      period;
    - red ⚠️ — not computed, for example because the history is too short.

If a card reports missing data, syncing the pair usually fills the gap.

---

## 📚 Deep dive: financial theory

Each indicator's formula, its signal-processing view (EMA as an IIR filter, SMA as an FIR filter)
and how to read its crossovers:

:material-book-open-variant: **[Technical Indicators — Financial Theory](../../../financial-theory/technical-analysis/indicators/index.md)**
