# 🔌 Provider Configuration

Each currency pair in LibreFolio is backed by one or more **data providers** — central banks that supply the exchange rate data. The Provider Configuration lets you view and modify which providers are used for a specific pair.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="provider-config" alt="Provider Configuration" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔓 How to Access

Click the **Provider** button (⚙️) in the chart toolbar on the Pair Detail page. This opens the provider configuration modal showing the current route setup.

---

## 📋 What You See

The modal displays:

- 🛤️ **Current Route(s)** — The active data source(s) for this pair, in priority order
- 🔀 **Route Type** — Whether it's a **Direct** route (single provider) or a **Chain** route (multi-hop through an intermediate currency)
- 🏛️ **Provider Details** — Name, icon, and base currency of each provider in the route

---

## 🔧 Changing Providers

You can configure **one or more** data providers for each pair. Multiple providers act as a **fallback chain** — if the primary source fails, the system automatically tries the next one.

To change or add providers:

1. Open the Provider Configuration modal
2. **Remove** the current route if needed
3. **Add a new route** — the system will discover available routes (same as when [adding a new pair](../add-pair.md))
4. **Reorder** routes to set priorities (drag & drop or arrow buttons)
5. Click **Save** — the next sync will fetch data from the highest-priority available provider

---

## 🔢 Priority & Fallback

When multiple routes are configured for a pair:

- Routes are tried **in priority order** (top = highest priority)
- If the primary provider fails (timeout, API error), the system automatically falls back to the next route
- You can **reorder** routes to change priorities

!!! example "Fallback Example"
    EUR/USD configured with:

    1. **ECB** (primary) — European Central Bank
    2. **FED** (fallback) — Federal Reserve

    If ECB's API is unreachable during sync, the system automatically uses FED instead.

---

## 📚 Related

- ➕ **[Adding a Pair](../add-pair.md)** — Full route discovery (direct + chain routes)
- 🔄 **[Synchronization](../sync.md)** — How sync uses the configured providers
- 📋 **[FX Providers List](../../../developer/backend/fx/providers_list.md)** — Technical details on each provider (ECB, FED, BOE, SNB)

!!! tip "🔗 How chain routes are calculated"
    For the mathematical algorithm behind multi-hop conversion chains, see [FX Chain Algorithm](../../../developer/frontend/fx-chain-algorithm.md).
