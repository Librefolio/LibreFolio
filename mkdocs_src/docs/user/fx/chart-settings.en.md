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


<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="chart-settings" alt="Chart settings modal with the live preview">
</div>

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
| **Y-Axis Scale** | Auto, Include 0, or a Custom min/max range for the active axis row |

### 📏 Axis Profiles

Asset and FX charts use the same client-side axis-settings model, while their saved scopes remain independent:

- The primary **absolute** and **percentage** axes have separate profiles. Changing one does not overwrite the other, and the chart selects the matching profile when its mode changes.
- The aesthetics panel shows one additional row for each active **semantic secondary axis**. Signal outputs that share that axis share its row instead of creating duplicate controls.
- Across the shared Asset and FX detail views and the global and per-card **Chart Settings** preview surfaces, every configurable row has a localized semantic name rather than a bare unit: **Price axis** with its currency (or **Preview** context), **Percentage axis**, **Exchange-rate axis** with its pair (or **Preview** context), **Volume axis**, or an **RSI**, **MACD**, or other named signal axis as applicable.
- Each row independently supports **Auto**, **Include 0**, and **Custom** minimum/maximum settings.
- On a secondary axis, **Auto** fits the actual visible extent across all series sharing that axis. For example, visible RSI values from 20 to 80 produce a 20–80 range.
- **Include 0** uses the same actual visible combined extent and adds zero. With the same RSI values, the range is 0–80.
- **Custom** uses the minimum and maximum entered explicitly.
- Custom **Min** and **Max** fields use compact tabular-number typography and can wrap with their row on narrow layouts. At mobile widths they switch to a 16 px input size with a matching 20 px line height to avoid focus zoom; touch manipulation prevents double-tap zoom, and keyboard-arrow stepping remains consistent.
- Plugin-declared bounds do not clamp **Auto** or **Include 0**.

### 📅 Responsive Date Axis

Asset and FX price charts, Dashboard **Growth** and **Allocation History**, and the broker-lot **WAC/Price**, **Gantt**, and **Comparison** charts share one responsive date-axis policy.

The policy derives a tick budget from usable chart width after horizontal padding and also considers the number of plotted dates. On a narrow or crowded axis it uses compact locale-aware date labels, preserves the first and last labels, thins interior category labels or reduces the time-axis split count, and hides any remaining overlap. Labels always stay horizontal at 0° rotation. On a spacious, lower-density desktop chart it keeps the normal dense date formatting without forced compact thinning.

Dashboard **Performance** is intentionally exempt: it is a horizontal categorical contribution chart with a numeric value X-axis, not a date X-axis.

### 📈 Overlay Signals

The modal manages the same overlay signals as the detail-page [Signals panel](detail/signals.md), added from three category dropdowns:

- 🧮 **Technical Indicators** — the backend plugin catalog for the current scope: **9 FX-compatible indicators** here, 22 on the Assets scope. The dropdown is a searchable tree grouped by family (trend, momentum, volatility, …). The math behind each indicator lives in [Technical Indicators — Financial Theory](../../financial-theory/technical-analysis/indicators/index.md).
- ↔️ **Data Comparison** — overlay another configured FX pair or an asset on the same chart.
- 📐 **Synthetic Benchmarks** — parameter-generated reference curves ([Linear](../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md), [Compound](../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md), [Sine Wave](../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md)). They are pure mathematics — not custom baskets and not market data.

Each configured signal becomes a card with inline parameters, a 📖 link to its theory page, and per-signal diagnostics once it has been computed.

---

## 💾 Persistence

Chart settings—including aesthetics, absolute/percentage axis profiles, semantic secondary-axis profiles, and signal configurations—are stored locally in your browser's `localStorage`. They are user-scoped, separated between the FX and Assets scopes, and can have per-card overrides on top of the scope defaults. They survive across sessions and are lost if that browser storage is cleared.

These settings are not stored in the backend database. The backend persists source data such as asset prices, asset events, and FX-rate history; signal results, including Asset Rolling Return, are computed for a request and are not persisted as new history.

The shared visible start/end range is separate from chart settings and is kept in `sessionStorage` for the current tab. Computed Rolling Return and comparison series remain in the current page runtime rather than either browser store.
