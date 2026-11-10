# 💱 FX Rates (Currency Exchange)

LibreFolio converts your amounts between currencies with the rates kept here. Each currency pair
downloads its rates from a central bank (ECB, FED, BOE or SNB), or holds rates you enter yourself.

---

## 📋 The FX list page

Open **FX Rates** from the sidebar to see your currency pairs:

<div class="lf-screenshot-carousel" data-carousel="carousel-fx-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="fx" data-name="list" data-title="🔲 Card Grid View" alt="FX List Page (Grid)">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="list-table" data-title="📋 Data Table View" alt="FX List Page (Table)">
</div>

Each pair shows its flags (e.g. 🇪🇺 EUR → 🇺🇸 USD), its **latest rate**, the change over the selected
period and a mini chart. When the chart groups the rates by week or month because the plot is too
narrow for so many days, a **Weekly** or **Monthly** badge at its top left says so, like on the
[detail page](detail/chart.md). A ✏️ **Manual** badge marks pairs without a provider. Click a pair to open
its [detail page](detail/index.md).

### 🔀 Cards or table

- The view toggle next to **Add Pair** switches between cards and table; LibreFolio remembers your
  choice.
- In the table, the **Δ** columns show the change over the last day, over the period and, on long
  periods, over 1W to 5Y. **Columns** adds hidden ones, such as each pair's **Providers**.
- Select rows to act on several pairs at once, or right-click a row.

### 🔍 Filter by currency

Pick a currency in **Filter currency** to list only its pairs, and a **Second currency** to narrow
the list to one pair; ✕ clears both.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="list-filtered" alt="FX List Filtered" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🧰 Page and pair actions

- The **period** picker at the top sets the range of every chart and change; in card view,
  the chart-line icon (tooltip **Show absolute**), **%** and the calendar icon (**Rolling Return**) show all cards as rates, as % change or as rolling return. The
  list opens on **Abs**; once you choose a view, it is remembered for you in this browser.
- A card's view button cycles **%** → **Rolling Return** → **Abs** and shows the view it goes to. The
  card keeps its own choice across reloads until you change the toolbar, which resets every card.
  On **Rolling Return** a card draws the rolling return of the rate the way the card shows the pair
  (flipped with ⇄: the return of the flipped rate), and over it the rolling returns of the FX pairs
  compared on that card. The rate and its change at the top stay as they are, and with too little
  history the card shows a short message instead of the chart. The window is the one set in
  [Chart Settings](chart-settings.md).
- A card draws the comparisons saved in its [Chart Settings](chart-settings.md), with another FX pair
  or with an asset. The line of an asset is its price in the asset's own currency, so compare it in
  the **%** view; the prices load once for all the cards that compare an asset.
- **Sync All** downloads new rates ([Synchronization](sync.md)); **Reload All** reads the stored
  ones again. **Settings** sets the look of every card ([Chart Settings](chart-settings.md)). Hover
  over any of the three for half a second to read what it does.
- On a card, ⇄ flips the direction shown (USD → EUR instead of EUR → USD); the buttons at the bottom
  open its own chart settings, **Sync** or **Reload** it, or delete it.

!!! warning "Deleting a pair deletes its rates"

    Deleting a pair removes its provider settings **and all its stored rates**, once you confirm.

---

## 🔮 What's next?

- ➕ **[Adding a Pair](add-pair.md)** — Create a pair with a direct or chain route
- 🔄 **[Synchronization](sync.md)** — Download rates, by hand or on a schedule
- 📊 **[Pair Detail Page](detail/index.md)** — Chart, signals, measures, rate editor and providers
- ⚙️ **[Chart Settings](chart-settings.md)** — Chart look and overlay signals
- 🔌 **[Providers](providers/index.md)** — The central banks LibreFolio reads (ECB, FED, BOE, SNB)
