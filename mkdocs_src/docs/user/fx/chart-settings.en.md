# ⚙️ Chart Settings

LibreFolio provides a **Chart Settings** modal to customize the appearance and behavior of FX charts. These settings apply to both the mini-charts on the [FX List page](index.md) and the full chart on the [Pair Detail page](detail/index.md).

---

## 🔓 Accessing Chart Settings

You can open the Chart Settings modal from:

- 📋 The **FX List page** — via the settings button (⚙️) in the toolbar
- 📊 The **Pair Detail page** — via the chart settings button

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="chart-settings" alt="Chart Settings Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🎛️ Available Settings

### 🎨 Appearance

| Setting | Description |
|---------|-------------|
| **Line Color** | Primary color for the chart line |
| **Line Width** | Thickness of the chart line (px) |
| **Area Fill** | Enable/disable the gradient fill under the line |
| **Grid Lines** | Show/hide horizontal and vertical grid lines |

### 🖱️ Tooltip & Interaction

| Setting | Description |
|---------|-------------|
| **Tooltip Format** | Number of decimal places shown in tooltips |
| **Crosshair** | Enable/disable the crosshair on hover |
| **Zoom** | Mouse wheel and pinch zoom settings |

### 📈 Signals Overlay

When using the detail page chart, you can configure which **technical indicators** are displayed as overlays:

#### 🧮 Calculated Signals

These are computed from the pair's own data:

- 📉 **EMA** (Exponential Moving Average)
- 📊 **MACD** (Moving Average Convergence Divergence)
- 💪 **RSI** (Relative Strength Index)
- 📏 **Bollinger Bands**

Each signal can be toggled on/off independently from the [Signals panel](detail/signals.md).

#### 🔍 Comparative Signals & Benchmarks

You can also overlay **benchmark comparisons** to see how a pair performs relative to a reference:

- 📐 **Synthetic Benchmarks** — Custom baskets or computed reference rates
- ↔️ **Cross-pair overlays** — Compare EUR/USD against GBP/USD on the same chart

For the mathematical foundations, see [Technical Indicators](../../financial-theory/technical-indicators.md) and [Synthetic Benchmarks](../../financial-theory/synthetic-benchmarks.md).

---

## 💾 Persistence

Chart settings are stored locally in your browser and apply across all currency pairs. They persist between sessions.
