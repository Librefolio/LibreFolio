# ⚙️ Chart Settings

The **Chart Settings** window changes how charts look and which overlays they draw. It serves both
the [FX list](index.md) and the [Assets list](../assets/index.md), and each list keeps its own
settings: changing the FX charts never touches the asset charts.

---

## 🔓 Open chart settings

- 🌐 **For all charts** — click **Settings** (⚙️) in the list toolbar. The window is titled
  **Chart Settings**. Applying it replaces the custom settings of every chart in the list, detail
  pages included, and the window warns you about it.
- 🎯 **For one chart** — click ⚙️ on a card. The window is titled **Chart Settings (Local)**, and
  its settings apply to that chart only.

!!! note "Detail pages use inline panels"

    On a [pair detail page](detail/index.md) (and on an asset detail page), ⚙️ on the chart opens
    the same appearance settings in a panel, and the **Signals** panel above the chart holds the
    overlays. They are the same settings as the card's local ones.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="chart-settings" alt="Chart Settings Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 👀 Preview before you apply

The window shows a preview chart with its own **Abs** / **%** switch. Your charts change only when
you click **Apply**; **Cancel** asks before discarding your changes.

<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="chart-settings" alt="Chart settings modal with the live preview">
</div>

- 🌐 **For all charts**, the preview draws a demo curve. The server computes the indicators on it,
  so they look exactly as they will on your real charts.
- 🎯 **For one chart**, the preview uses that chart's real data. Indicators show the last applied
  settings until you click **Apply**, and a banner reminds you of it.

---

## 🎨 Appearance

| Setting | What it does |
|---------|--------------|
| **Baseline Colors** | Green above, red below the start of the period |
| **Area Fill** | Gradient under the line |
| **Grid Lines** | Horizontal dashed grid |
| **Stale Gradient** | Fades the days without a new value, which repeat an earlier one |

### 📏 Axis ranges

**Y-Axis Scale** has one row for each axis on the chart: the main axis (the rate, or the percentage
in % view) and one for each indicator scale, such as the **RSI axis**. Indicators that share a
scale share a row.

- **Auto** fits the data on that axis.
- **Include 0** fits the data and also shows zero.
- **Custom** uses the **Min** and **Max** you type.

The **Abs** and **%** views keep separate ranges: switch the preview to **%** to set the
percentage one.

---

## 📈 Overlay signals

Add overlays from three dropdowns, the same as in the detail page's [Signals panel](detail/signals.md):

- 🧮 **Technical Indicators** — 9 indicators work on FX rates (asset charts offer more), grouped by
  family with a search box. The math is in
  [Technical Indicators — Financial Theory](../../financial-theory/technical-analysis/indicators/index.md).
- ↔️ **Data Comparison** — another FX pair or an asset on the same chart.
- 📐 **Synthetic Benchmarks** — reference curves built from parameters alone, not market data:
  [Linear](../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md),
  [Compound](../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) and
  [Sine Wave](../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md).

Each signal becomes a card with its parameters, a 📖 link to its theory page and, once computed, a
diagnostics icon.

---

## 💾 Where settings are saved

- Chart settings are saved in **this browser**, for your user, separately for the FX and asset
  lists. A chart's own settings sit on top of its list's settings.
- They are not stored on the server: another browser or device starts from the defaults, and
  clearing this site's browser data resets them.
- The selected period is not a chart setting: the pages of the same browser tab share it.
