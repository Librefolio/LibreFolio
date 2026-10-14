# 🔍 Pair Detail Page

Click a pair in the [FX list](../index.md) to open its page: a large chart of its rates, with tools
to analyse, edit and configure the pair.

---

## 🗺️ The page at a glance

- **Header** — ⇄ swaps the pair's direction and the list card follows (with unsaved changes in the
  rate editor, LibreFolio asks first); ← goes back to the list.
- **Toolbar** — the period, the latest rate with its change, and the **AI Export**, **Providers**,
  **Sync** and **Reload** buttons. **Reload** reads the stored rates again; **Sync** downloads new
  ones, see [Synchronization](../sync.md).
- **Below** — the folded **Signals** panel, the chart, then the folded **Measures** panel.

---

## 🧭 Features

### 📈 [Interactive Chart](chart.md)

The rate history, with zoom, pan, an **Abs** / **%** view and period presets.

### 📊 [Signals](signals.md)

Indicators, comparisons and benchmark curves drawn on the chart; nine indicators work on FX rates.

### 📐 [Measures](measures.md)

The change, the change in % and the yearly rate between two points of the chart.

### ✏️ [Data Editor](data-editor.md)

Add, edit or delete single rates, or import many at once from a CSV file.

### ⚙️ [Provider Config](provider.md)

**Providers** changes where the rates come from: the provider, backup routes and chains.

### 🧠 AI Export

**AI Export** prepares a snapshot of the pair, or an **FX Pair Analysis** or **FX Exposure Impact**
request, to paste into an AI assistant. FX Exposure Impact counts only the cash and the positions
held directly in the pair's currencies: it does not look inside funds. See
[FX AI Export](../../ai-export/fx.md).

---

## 🔗 Related

- ⚙️ **[Chart Settings](../chart-settings.md)** — Chart look and overlay signals
- 📋 **[FX Overview](../index.md)** — Back to the FX list page
