# 💼 Assets

Assets are the instruments you hold or follow: stocks, ETFs, bonds, crypto, or a savings account with scheduled interest. The **Assets** page lists them all, each with a small price chart, and opens the detail page of any of them.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="list" data-title="🔲 Card Grid View" alt="Asset List Page (Grid)">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="list-table" data-title="📋 Data Table View" alt="Asset List Page (Table)">
</div>

## 📌 What is an asset?

Each asset has:

- **a name and identifiers** — ISIN, ticker or other codes;
- **a type** — stock, ETF, bond, crypto, commodity… ([asset types](../../financial-theory/instruments/asset-types/index.md));
- **a currency** — the one its prices are quoted in;
- **a price provider**, optional — it downloads the current price and the history for you ([Providers](providers/index.md));
- **a sector and country breakdown**, optional;
- **events** — dividends, splits, interest… ([Asset events](detail/events.md)).

Assets are shared by everyone on this LibreFolio: your transactions decide which ones are yours.

## 📋 Browse the list

Open **Assets** in the sidebar, then:

- **Pick a layout** — the two buttons next to **Add Asset** switch between cards with a small chart (**Grid view**) and a sortable table (**Table view**). Your choice is remembered in this browser.
- **Pick the period** — the date range sets the period of the card charts and of the change they show. When a card's chart groups the days into weeks or months because the plot is too narrow for so many days, a small **Weekly** or **Monthly** badge at its top left says so, like on the [detail page's chart](detail/chart.md). In the table, the **Δ** columns give the change over one day and over each period, from 1W to 5Y, that fits in the range.
- **Filter** — type in **Search assets...** to filter by name, and pick one or more currencies and types in the two menus; the ✕ clears the search and both menus.
- **Show archived assets** — the list starts with **Active** assets only: switch on **Inactive** to add the archived ones, or switch off **Active** to see only those.

Click a card or a row to open the asset's **[detail page](detail/index.md)**. There, the **‹ ›** arrows step through the assets in the order this list shows them, filters and sort included.

??? note "📉 Abs, % or Rolling Return on the cards — grid view only"

    The switch in the toolbar has three options: the chart-line icon, the same as on the cards, for the absolute prices (its tooltip says **Show absolute**), **%** (the change over the period) and the calendar icon for **Rolling Return**. Your choice applies to every card, its chart and its change, and it is remembered in this browser, for your user, with the chart settings.

    The view button on a card goes to the next view, **%** → **Rolling Return** → **Abs** → **%**, and shows the view it will go to. A card keeps its own choice, even after you reload, until you change the toolbar again: that resets every card to the toolbar's view.

    In **Rolling Return**, a card draws the asset's rolling return, the same calendar-window return as the **Rolling Return** mode of the [asset detail page](detail/index.md), and over it the rolling returns of the asset comparisons saved on that card. The other indicators stay saved, only hidden in this view. The price and the change at the top of the card do not change. If the asset has less history than the window, the card shows a short message instead of the chart.

    The window is chosen in [Chart Settings](../fx/chart-settings.md): 1W, 1M, 3M, 1Y or a custom one. Until you choose one, it is automatic: the largest preset that fits the period shown in the list, so a 3-month range uses 3M and a range of one year or more uses 1Y.

    The asset's [detail page](detail/index.md) opens in the view of its card, and with the card's Rolling Return window. A view chosen there becomes the card's.

??? note "⚙️ The look of the card charts"

    **Settings** in the toolbar sets the look and the overlays of every asset chart at once, and applying it replaces each asset's own settings, detail pages included. The ⚙️ on a card changes that card only. See [Chart Settings](../fx/chart-settings.md).

### 🗂️ Your assets, other users' assets, watched

Both layouts split the list into up to three panels, each with its count; an empty panel is not shown.

| Panel | What it holds |
|---|---|
| **Your assets** | Assets held now in a broker you own |
| **Other users' assets** | Assets held now only by other users — in brokers you do not own |
| **Watched** | Assets held by no one now — never bought or already sold, kept on the radar |

What counts is the position **today**: when you sell your whole position, the asset moves to *Other users' assets* if someone else still holds it, and to *Watched* otherwise. Brokers shared with you as **Editor** or **Viewer** count as other users' brokers, and a position closed down to a negligible leftover counts as not held.

In the table view each panel is a table with its own pages; resizing, moving or hiding a column applies to all three.

## 🔄 Keep prices up to date

- **Sync All** opens a window where **Start Sync** downloads the latest prices of every asset that has a provider; **Reload All** reloads the list from what LibreFolio has stored. Hover over **Settings**, **Sync All** or **Reload All** for half a second to read what the button does. When the period already holds stored prices for some of the assets, the window says so before you start: the sync replaces them with the provider's values, your manual edits included. On the **[Correlation](correlation.md)** tab they become **Sync selection**, which also downloads the exchange rates that convert the selected assets, and **Reload All**, which recomputes every analysis.
- **Live prices** — while the date range ends today, prices refresh by themselves: every minute on this page, every 30 seconds on an asset's page. A price turns green when it went up since the previous refresh, red when it went down; when the market is closed you see the last close, uncoloured. To spare the server and the price providers, refreshing pauses while the browser tab is in the background, and after two minutes without using the page: then a small **Updates paused** label shows at the top of the page. There is nothing to click: as soon as you come back to the tab, move the mouse or press a key, prices refresh again on their own.
- **In the background**, the server refreshes prices on a schedule your administrator sets ([Market Data Scheduler](../../admin/settings.md#market-data-scheduler)). The Dashboard shows the stored prices.

## 🖱️ Act on one asset

Each card has its own buttons; in the table, the **⋮** at the end of a row, or a right-click, opens the same actions:

- **Sync** — downloads the asset's prices for the selected period. It needs a provider, and the table also blocks it for an archived asset.
- **Reload** — reloads its prices from what LibreFolio has stored.
- **Merge with…** — folds a duplicate into another asset, which keeps everything ([Create & Edit](create-edit.md)).
- **Delete** — removes an asset that no transaction uses, with its provider, prices and events (dividends, splits…).

In the table, tick several rows to **Sync**, **Reload** or **Delete** them together.

??? warning "🗑️ When an asset cannot be deleted"

    An asset is not deleted while **any** transaction uses it, even one in a broker you cannot see. The result shows how many transactions use it, with a **Transactions** link filtered to that asset. That page shows only the brokers you can access, so it may list fewer transactions than the count.

    When the list already counts transactions for the asset, its confirmation opens straight on that result, with no **Delete** button: there is nothing to confirm. Otherwise the result appears after you confirm, and LibreFolio still checks before deleting.

## 🧭 Features

### ➕ [Create & Edit](create-edit.md)

Create an asset, connect it to a price provider and keep its details right.

### 🧪 [Correlation Tab](correlation.md)

Compare a selection of assets side by side — correlation matrix, losses, risk against return, and historical replay, in percentages only.

### 📊 [Asset Detail Page](detail/index.md)

The price chart with its signals, measures and events, the data editor, and the classification.

### 🔌 [Providers](providers/index.md)

Automatic prices from Yahoo Finance, justETF, Borsa Italiana, the CSS Scraper, or the Scheduled Investment engine.

---

## 🔗 Related

- 📚 **[Financial Theory — Asset Types](../../financial-theory/instruments/asset-types/index.md)** — Stock, ETF, Bond, Crypto, etc.
- 💱 **[FX Rates](../fx/index.md)** — Currency exchange rates used for cross-currency conversion
- 🛠️ **[Live Prices](../../developer/frontend/components/features/live-ticker.md)** — For developers: how the pages poll live prices
