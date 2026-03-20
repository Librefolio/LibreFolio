# ➕ Adding a Currency Pair

To add a new currency pair to your FX dashboard:

1. Click **"Add Pair"** on the FX list page
2. Select the **two currencies** using the search dropdown
3. The system automatically discovers available **data routes** — both direct and chain routes
4. Select the route you prefer and click **Confirm** — the pair is created and data synchronization begins automatically

---

## Direct Routes

If a provider supports both currencies directly (e.g., ECB for EUR→USD), you'll see a **Direct Routes** section:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="add-pair-routes" alt="Add Pair — Direct Routes" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## Chain Routes

For exotic pairs (e.g., RON→JPY) where no single provider covers both currencies, the system builds **conversion chains** — multi-step paths through intermediate currencies:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="add-pair-chain" alt="Add Pair — Chain Routes" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! example "Chain Example"
    **RON → JPY** via ECB:

    1. RON → EUR (ECB provides RON/EUR)
    2. EUR → JPY (ECB provides EUR/JPY)

    The final rate is computed by multiplying the intermediate rates.

---

## How Route Discovery Works

When you select two currencies, LibreFolio queries all installed providers to find:

- **Direct routes**: a single provider that covers both currencies
- **Chain routes**: two or more providers that together can connect the currencies through an intermediate currency (e.g., EUR)

Each route shows:

- The **provider** name and icon
- The **direction** (base → quote)
- For chains: the **intermediate currency** and the **number of hops**

You can choose any available route based on your preference for data source, coverage period, or update frequency.

For technical details on the routing algorithm, see the developer documentation: [FX Configuration & Routing](../../developer/backend/fx/configuration.md).

