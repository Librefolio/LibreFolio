# 🔌 Provider Configuration

Each currency pair gets its rates from one or more **routes**: a central bank that quotes the pair
directly, or a chain of conversions. Here you see and change the routes of the pair you are
viewing.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="provider-config" alt="Provider Configuration" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔓 How to Access

On the pair's detail page, click **Providers** (🔧) in the toolbar, next to **Sync**. The
**Edit Pair Providers** window opens.

---

## 📋 What You See

Under **Conversion Routes**, each row is a route, in priority order:

- the currencies, with the provider of each step between them — hover a provider's icon for its
  name and description;
- the priority badge: **#1** is used first;
- ⚠️ when a provider has a data warning, such as the SNB's monthly rates;
- 🗑️ to remove the route.

---

## 🔧 Changing Providers

1. Click **Add conversion route** and pick a route under **Direct conversion (1 step)** or
   **Chain conversion**. Type in the search box to filter by provider, currency or country.
2. Drag the rows to set their priority (on a phone, use the up and down arrows).
3. Click **Save Configuration**: the next sync uses the new routes.

??? note "🔗 Also create intermediate pairs — when you pick a chain route"

    Tick it to save each step of the chain as a pair of its own, with its provider, so that you can
    sync and view it on its own.

??? note "✍️ No route left — when you remove them all"

    The pair becomes manual: **Sync** is disabled, and you enter the rates yourself in the
    [Data Editor](data-editor.md).

---

## 🔢 Priority & Fallback

A sync tries the routes from the top. If one fails — for example, its central bank does not
answer — it moves on to the next; the pair fails only when every route does. With EUR/USD set to
**#1** ECB and **#2** FED, a sync that cannot reach the ECB uses the FED rate instead.

---

## 📚 Related

- ➕ **[Adding a Pair](../add-pair.md)** — Full route discovery (direct + chain routes)
- 🔄 **[Synchronization](../sync.md)** — How sync uses the configured providers
- 🔌 **[FX Providers](../providers/index.md)** — User guide and details on each provider (ECB, FED, BOE, SNB)
- 🧮 **For developers: [FX Chain Algorithm](../../../developer/frontend/fx-chain-algorithm.md)** — How chain routes are found and calculated
