# 🔄 FX Synchronization

Once a currency pair is configured with a data provider, LibreFolio can **automatically synchronize** exchange rates from official central bank sources.

---

## 🔄 Sync All

From the FX list page, use the **Sync All** button to synchronize all configured pairs at once:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="sync-progress" alt="Sync Progress" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

The sync modal shows:

- 📊 **Progress** for each pair being synced
- ✅ **Status** indicators (success, error, skipped)
- 🆕 **New data points** count for each pair

---

## 🎯 Individual Pair Sync

You can also sync a single pair from its [detail page](detail/index.md) using the sync button. This is useful when you want to update only one specific pair.

---

## ⚙️ How Sync Works

The sync process:

1. Fetches rates from the selected provider's API (ECB, FED, BOE, SNB, etc.)
2. Stores new data points in the local database
3. Skips dates that already exist (no duplicates)
4. If the primary provider fails, the system automatically falls back to the next configured provider

!!! tip "No duplicate data"
    Re-syncing a pair is always safe — existing data points are never overwritten or duplicated.

---

## 🌐 Data Supply Chains

For advanced users: LibreFolio uses a sophisticated **routing system** for FX data. Each currency pair can have multiple providers configured with priorities and fallback chains.

This means:

- 🔄 If your primary provider (e.g., ECB) is down, the system falls back to the next provider (e.g., FED)
- 🔀 Exotic pairs use multi-step chains through intermediate currencies (e.g., RON → EUR → JPY)
- ⚙️ You can customize which provider to use for each pair

For the list of supported providers, see the [FX Providers List](../../developer/backend/fx/providers_list.md).

For technical details on the routing algorithm and configuration, see the developer documentation: [FX Configuration & Routing](../../developer/backend/fx/configuration.md).
