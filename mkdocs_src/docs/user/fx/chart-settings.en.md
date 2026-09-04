# ⚙️ Chart Settings

The **Chart Settings** modal customizes chart appearance and overlay signals. The same modal serves both the [FX List](index.md) and the [Assets](../assets/index.md) pages, with **independent settings per scope** — changing the FX defaults never touches asset charts, and vice versa.

---

## 🔓 Accessing Chart Settings

The modal opens from the list pages, in two flavors:

- 🌐 **Global** — the settings button (⚙️) in the list-page toolbar. These settings become the default for every chart in the scope; applying them replaces all per-card customizations (the modal warns you about this).
- 🎯 **Local** — the settings button (⚙️) on any pair or asset card. These settings override the global ones for that card only.

!!! note "Detail pages use inline panels instead"

    On the [Pair Detail page](detail/index.md) (and on asset detail pages) the ⚙️
    button toggles an inline **aesthetics panel** and the 📈 button toggles the
    inline **signals panel** — same settings, same per-item storage, no modal.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="chart-settings" alt="Chart Settings Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 👀 Live Preview

The modal always shows a **preview chart** with an Abs/% toggle, so you see the effect of every change before applying it:

- 🌐 **Global mode** — the preview draws a synthetic demo curve. Backend indicators cannot run in the browser, so the modal asks the server to compute them live on that curve: what you see matches what real charts will render.
- 🎯 **Local mode** — the preview uses the card's **real price data**. Backend indicators show the last applied configuration; a banner reminds you to Apply to refresh them.

---

## 🎛️ Available Settings

### 🎨 Appearance

| Setting | Description |
|---------|-------------|
| **Baseline Colors** | Color the line green above / red below the baseline |
| **Area Fill** | Gradient fill under the line |
| **Grid Lines** | Horizontal dashed grid |
| **Stale Gradient** | Fade older data towards the background |
| **Y-Axis Scale** | Auto, Include 0, or a Custom min/max range |

### 📈 Overlay Signals

The modal manages the same overlay signals as the detail-page [Signals panel](detail/signals.md), added from three category dropdowns:

- 🧮 **Technical Indicators** — the backend plugin catalog for the current scope: **9 FX-compatible indicators** here, 22 on the Assets scope. The dropdown is a searchable tree grouped by family (trend, momentum, volatility, …). The math behind each indicator lives in [Technical Indicators — Financial Theory](../../financial-theory/technical-analysis/indicators/index.md).
- ↔️ **Data Comparison** — overlay another configured FX pair or an asset on the same chart.
- 📐 **Synthetic Benchmarks** — parameter-generated reference curves ([Linear](../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md), [Compound](../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md), [Sine Wave](../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md)). They are pure mathematics — not custom baskets and not market data.

Each configured signal becomes a card with inline parameters, a 📖 link to its theory page, and per-signal diagnostics once it has been computed.

---

## 💾 Persistence

Chart settings are stored locally in your browser's `localStorage`, separately for the FX and Assets scopes, with per-card overrides on top of the scope defaults. They survive across sessions — even after closing and reopening the browser — and will only be lost if you clear your browser cache/storage or if the storage expires (browser-dependent, typically months to years).
