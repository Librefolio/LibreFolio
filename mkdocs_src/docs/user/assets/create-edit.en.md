# ➕ Create & Edit Assets

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-create" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="create-modal" data-title="➕ Manual Creation Form" alt="Manual Create Modal">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="create-wizard-modal" data-title="🧙 Import Wizard Auto-Creation Form" alt="Create Asset from Wizard">
</div>

## 🚀 Asset Creation Flows

In LibreFolio, you can create new assets in two different ways:

=== "Manual Creation (with Smart Search)"

    ```mermaid
    flowchart LR
        A[Start: Click '+ New Asset'] --> B[Type Name, ISIN, or Ticker in Smart Search]
        B --> C{Match Found?}
        C -->|Yes| D[Auto-fill details from external providers]
        C -->|No| E[Manually enter name, category, & currency]
        D --> F[Adjust config / Assign pricing provider]
        E --> F
        F --> G[Click Save]
        G --> H[Asset added to library]
    ```

=== "Broker Import Auto-Creation"

    ```mermaid
    flowchart LR
        A[Start: Upload CSV report in Import Wizard] --> B[Parse report rows]
        B --> C{Asset ID recognized?}
        C -->|Yes| D[Auto-match with existing asset]
        C -->|No| E[Flag warning ⚠️ and show 'Create' button]
        E --> F[Click 'Create' to open pre-filled modal]
        F --> G[Save asset to resolve mapping]
        G --> D
        D --> H[Commit all transactions]
    ```

## 🧪 Testing Provider Configuration

After configuring a provider, click **Test Configuration** to verify that pricing data can be fetched. The test checks:

- **Current Price**: fetches the latest price
- **History**: fetches historical price data (if supported)

Results are displayed inline with execution times. A ⚠️ warning means the operation is not supported by this provider (e.g., CSS Scraper doesn't support history).

## 🔎 Smart Search Details

Smart Search first asks each provider's own search. If a supported provider cannot find anything,
LibreFolio may try a best-effort web link search and resolve provider pages back into asset
candidates. For Borsa Italiana, this means a fund/detail URL can become a ready-to-save asset with
the `provider_params` needed to price the fund by its internal code.

For Borsa Italiana funds, the visible ISIN identifies the fund when available, but pricing uses the
internal Borsa fund code saved in provider configuration. Current NAV is used only when dated today;
history contains one NAV point at its real date.

## 🔌 Provider Assignment

Each asset can have one pricing provider assigned. See [Providers](providers/index.md) for details on available providers and their configuration.

## 🛠️ Editing an Asset

Click the **Edit** (✏️) button on the [detail page](detail/index.md) to open the asset modal with all fields pre-populated. All fields are editable, including provider configuration and distributions.

The **Other identifiers** field is an editable list of alternative identifiers. Imports and
providers can add broker labels, technical codes, or fallback identifiers there; each value remains a
separate list item.

## 🔗 Related

- 📊 **[Asset Detail Page](detail/index.md)** — View and analyze asset data
- 🔌 **[Providers](providers/index.md)** — Available pricing providers

