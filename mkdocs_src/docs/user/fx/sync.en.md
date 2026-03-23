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

1. Fetches rates from the configured provider's API (ECB, FED, BOE, SNB, etc.)
2. **Overwrites** existing data points in the downloaded date range with the provider's values — the provider is treated as the authoritative source
3. Adds new data points for dates not yet in the database
4. If the primary provider fails, the system automatically falls back to the next configured provider

After sync, you'll see the number of **points downloaded** and how many were **actually new** (not previously present in the database).

!!! warning "Provider is authoritative"

    Re-syncing a pair will overwrite any manually edited values in the synced date range. If you need to preserve manual edits, consider using a pair configured with the MANUAL provider (no automatic data source).

!!! info "Chain conversion precision"

    When using chain routes (e.g., RON → EUR → JPY), each intermediate conversion introduces a minimal rounding error. While negligible for most purposes, be aware that chain-converted rates may differ slightly from direct market quotes.

---

## 🌐 Data Supply Chains

For advanced users: LibreFolio uses a sophisticated **routing system** for FX data. Each currency pair can have multiple providers configured with priorities and fallback chains.

This means:

- 🔄 If your primary provider (e.g., ECB) is down, the system falls back to the next provider (e.g., FED)
- 🔀 Exotic pairs use multi-step chains through intermediate currencies (e.g., RON → EUR → JPY)
- ⚙️ You can customize which provider to use for each pair

For the list of supported providers, see the [FX Providers List](../../developer/backend/fx/providers_list.md).

For technical details on the routing algorithm and configuration, see the developer documentation: [FX Configuration & Routing](../../developer/backend/fx/configuration.md).
