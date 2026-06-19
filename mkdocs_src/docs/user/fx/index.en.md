# 💱 FX Rates (Currency Exchange)

LibreFolio includes a full-featured **Foreign Exchange (FX)** management system. It lets you track exchange rates between any pair of currencies, with automatic synchronization from official central bank sources.

---

## 📋 The FX List Page

Navigate to **FX Rates** from the sidebar to see all your configured currency pairs:

<div class="lf-screenshot-carousel" data-carousel="carousel-fx-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="fx" data-name="list" data-title="🔲 Card Grid View" alt="FX List Page (Grid)">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="list-table" data-title="📋 Data Table View" alt="FX List Page (Table)">
</div>

Each currency pair is displayed with details including:

- 🔀 **Grid / Table Layouts**: Toggle between a visual card grid and a compact data table. The selection is saved in your browser's `localStorage` for future sessions.
- 🏷️ The **currency pair** with flags (e.g., 🇪🇺 EUR → 🇺🇸 USD)
- 📈 The **latest exchange rate** and price trend
- 🏛️ The **active data provider** (ECB, FED, BOE, SNB, or MANUAL)
- 📊 A **sparkline chart** showing the rate trend over the past 30 days
- 🖱️ **Context Menu**: Right-click any row in the table layout for quick actions (Edit, Sync, Delete)

You can **filter** by currency to quickly find a specific pair:

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="list-filtered" alt="FX List Filtered" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔮 What's Next?

- ➕ **[Adding a Pair](add-pair.md)** — How to create a new currency pair with direct or chain routes
- 🔄 **[Synchronization](sync.md)** — Automatic and manual sync from providers
- 📊 **[Pair Detail Page](detail/index.md)** — Interactive chart, signal measurements, data editor, provider configuration
- ⚙️ **[Chart Settings](chart-settings.md)** — Customize chart appearance and signal overlays
- 🔌 **[Providers](providers/index.md)** — Supported central bank sources for FX rates (ECB, FED, BOE, SNB)
