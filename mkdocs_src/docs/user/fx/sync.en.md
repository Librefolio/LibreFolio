# 🔄 FX Synchronization

Pairs with a provider get their rates from official central bank sources. LibreFolio downloads
them when you add a pair, whenever you ask, and — if your administrator turned it on — on a
schedule.

---

## 🔄 Sync all pairs

1. On the [FX page](index.md), choose the period in the date picker. Pick **All** for the whole
   history.
2. Click **Sync All**. The **Sync FX Rates** window lists every pair with a provider: pairs with
   manual rates only have nothing to download.
3. Click **Start Sync**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="sync-progress" alt="Sync Progress" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📊 Reading the results

- Each row shows a pair, the provider that answered, **↓** the rates downloaded and **Δ** the rates
  that were new or changed.
- An amber row means the provider sent no rates for the period; a red row means the sync failed.
  Hover the message to read it in full, and click the row's ↻ button to try that pair again.
- The summary at the bottom shows how many pairs synced and the totals. **Retry N failed** runs
  every failed pair again.

---

## 🎯 Sync one pair

- On the FX page, the **Sync** button of a pair's card, or of a table row, downloads that pair's
  rates for the selected period. A message reports the result.
- On the pair's [detail page](detail/index.md), **Sync** opens the sync window for the pair and for
  any pair or asset you compare it with on the chart.

**Sync** is greyed out for pairs with manual rates only.

---

## ⚠️ What a sync changes

- Dates of the period that are already stored take the provider's value; missing dates are added.
- Dates outside the period are left untouched.
- If a pair's first route fails, LibreFolio tries the next one: see
  [Provider Config](detail/provider.md).

!!! warning "The provider has the last word"

    A sync overwrites the rates you edited by hand within its period. To keep your own rates, use a
    pair without a provider (manual rates only).

??? tip "🕰️ Older history missing — when a pair's chart starts later than expected"

    A pair you add with a provider downloads its whole history by itself. If an older pair's chart
    starts later than the provider's history, set the period on the FX page to **All** and click
    **Sync All** once: LibreFolio downloads everything the providers publish, up to today.

---

## 🕐 Automatic sync

When your administrator turns on the background scheduler, LibreFolio refreshes the recent rates of
every pair with a provider on its own, at the times they choose: see
[Market Data Scheduler](../../admin/settings.md#market-data-scheduler).

---

## 🔗 Related

- ➕ **[Adding a Pair](add-pair.md)** — Direct and chain routes
- 🔌 **[FX Providers](providers/index.md)** — The central banks LibreFolio reads rates from
- ⚙️ **[Provider Config](detail/provider.md)** — Routes, priorities and fallbacks of a pair
- 🧑‍💻 For developers: **[FX Configuration & Routing](../../developer/backend/fx/configuration.md)**
