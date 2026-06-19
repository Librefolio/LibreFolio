# ➕ Adding a Currency Pair

To add a new currency pair to your FX dashboard:

1. Click **"Add Pair"** on the FX list page
2. Select the **two currencies** using the search dropdown
3. The system automatically discovers available **data routes** — both direct and chain routes
4. Select the route you prefer and click **Confirm** — the pair is created and data synchronization begins automatically

---

## 🛤️ Conversion Routes (Direct & Chain)

When you select a base and quote currency, LibreFolio queries all installed providers to discover the best available exchange rate routes.

<div class="lf-screenshot-carousel" data-carousel="carousel-fx-routes" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="fx" data-name="add-pair-routes" data-title="🔗 Direct Routes" alt="Add Pair — Direct Routes">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="add-pair-chain" data-title="🔀 Chain Routes (Multi-hop)" alt="Add Pair — Chain Routes">
</div>

### 🔗 Direct Routes
If a provider directly supports exchange rates between both currencies (e.g. ECB quoting rates for EUR 🇪🇺 / USD 🇺🇸), the system displays it as a direct route option.

### 🔀 Chain Routes
For exotic pairs (e.g., RON 🇷🇴 / JPY 🇯🇵) where no single central bank publishes rates directly, the system automatically builds **conversion chains** — multi-step paths through intermediate currencies (typically EUR 🇪🇺 or USD 🇺🇸).

!!! example "Chain Example"

    **RON 🇷🇴 → JPY 🇯🇵** via ECB:

    1. RON 🇷🇴 → EUR 🇪🇺 (ECB provides RON 🇷🇴 / EUR 🇪🇺)
    2. EUR 🇪🇺 → JPY 🇯🇵 (ECB provides EUR 🇪🇺 / JPY 🇯🇵)

    The final rate is computed by multiplying the intermediate rates.

---

## 🧭 How Route Discovery Works

When you select two currencies, LibreFolio queries all installed providers to find:

- 🔗 **Direct routes**: a single provider that covers both currencies
- 🔀 **Chain routes**: two or more providers that together can connect the currencies through an intermediate currency (e.g., EUR 🇪🇺)

Each route shows:

- 🏛️ The **provider** name and icon
- ➡️ The **direction** (base → quote)
- 🔢 For chains: the **intermediate currency** and the **number of hops**

You can choose any available route based on your preference for data source, coverage period, or update frequency.

!!! info "For the Curious: Behind the Scenes"

    If you are interested in the mathematical details of how multi-hop conversion chains are computed and routed, you can read the developer documentation: [FX Configuration & Routing](../../developer/backend/fx/configuration.md) and [FX Chain Algorithm](../../developer/frontend/fx-chain-algorithm.md). 
    
    *Note: This technical documentation is only for developers and is not required to use this feature.*
