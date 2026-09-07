# ➕ Create & Edit Assets

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-create" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="create-modal" data-title="➕ Manual Creation Form" alt="Manual Create Modal">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="create-wizard-modal" data-title="🧙 Import Wizard Auto-Creation Form" alt="Create Asset from Wizard">
</div>

## 🚀 Asset Creation Flows {: #asset-creation-flows }

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

## 🛠️ Editing an Asset {: #editing-an-asset }

Click the **Edit** (✏️) button on the [detail page](detail/index.md) to open the asset modal with all fields pre-populated. All fields are editable, including provider configuration and distributions.

The **Other identifiers** field is an editable list of alternative identifiers. Imports and
providers can add broker labels, technical codes, or fallback identifiers there; each value remains a
separate list item.

## 🗺️ Manual Geographic & Sector Distributions

Providers fill in the **geographic area** and **sector** distributions when they can — but many
assets (custom instruments, bonds, scheduled investments, or simply assets whose provider has no
breakdown) arrive with none. You can always set or correct both distributions by hand from the
asset modal: they feed the dashboard's **allocation charts** (geography and sector rings, now and
over time) and the AI Export concentration context.

In the asset modal ([create](#asset-creation-flows) or [edit](#editing-an-asset)) open
the **Classification** area:

1. **Geographic distribution** — one row per country/area, with its weight in percent.
2. **Sector distribution** — one row per sector, with its weight in percent.

For each distribution you can:

- **Add a row** and pick the area/sector from the dropdown, then type the weight.
- **Edit weights inline**; the running **total** sits at the bottom of the editor and turns
  **green at exactly 100%** — amber when something is missing, red when you overshoot.
- **Remove** a row with its delete button.

!!! tip "The 100% rule"

    The dashboard normalizes partial distributions, but a clean 100% gives the most meaningful
    allocation rings. If the instrument is 100% one country or sector, a single row at 100 is
    both valid and the clearest choice.

*(Screenshots of the two distribution editors — `assets/detail-classification` already exists and shows the area; dedicated close-ups of the editors are planned for the next gallery run.)*

## 🏷️ One instrument, several codes

The same security can be known by more than one code. When that happens, LibreFolio keeps **one
asset** and stores the extra codes under **Other identifiers**, where they are searchable and are
used to recognise the instrument on later imports.

Which code goes in the main **ISIN** field is not a matter of taste:

!!! tip "Keep the quoted code as the main ISIN"

    A price is the value of the last trade, so only a code that can actually be traded has a
    price. Put the tradeable code in **ISIN** and everything else in **Other identifiers** —
    otherwise the asset cannot be priced by any provider.

### Italian retail government bonds (BTP Valore, BTP Più, BTP Italia)

These bonds are issued under one ISIN and traded under another:

| Phase | Code | What it does |
|---|---|---|
| Subscription at issue | the "CUM" ISIN | Entitles you to the **loyalty premium** if you hold to maturity. **Not tradeable**, so no provider quotes it |
| Secondary market | a different ISIN | Freely traded and **quoted** — this is the one with a price |

To sell before maturity the bond is converted to the market code. In LibreFolio the two are the
same instrument, so:

1. Put the **market ISIN** in the **ISIN** field.
2. Put the **CUM ISIN** in **Other identifiers**.
3. Record the **loyalty premium**, when it is paid, as an **Interest** transaction on that asset,
   dated the day you receive it.

Step 3 works even after the bond has matured and the asset has been deactivated: a deactivated
asset stays selectable precisely so the last coupon, the redemption and the premium can be
entered.

!!! note "During an import you are asked, not overruled"

    If a broker file carries the CUM code and the asset already holds the market one, the import
    asks which of the two should lead. The one you do not pick is added to **Other identifiers** —
    nothing is discarded, and the next import recognises the bond from either code.

    When the same bond appears in two files under different codes, the **Unify assets** step of the
    import wizard groups them into a single instrument before anything else is decided.

## 🧲 Merging duplicate assets

If the same instrument ended up in your library twice — a common outcome of importing a bond
under its subscription code once and its market code another time — you can fold one into the
other from the **Merge** action, available on the asset list and on the asset detail page.

The operation is **destructive**, so it happens in two deliberate steps:

1. **Choose the asset to keep.** The one you started from is the one that will disappear; you
   pick its survivor from the whole catalogue, deactivated assets included — a matured bond is
   exactly the sort of thing being merged.
2. **See what moves, then settle the identity.** LibreFolio runs a dry run first and shows the
   real counts: how many transactions, prices and events will be reassigned, and what happens to
   the price provider. Where both assets carry a value for the same identifier, it asks which one
   should lead; the other is kept under **Other identifiers**.

| What moves | What happens |
|---|---|
| Transactions | Reassigned to the surviving asset |
| Price history | Reassigned; if both assets have a price on the same day, the survivor's wins |
| Corporate events (dividends, coupons) | Reassigned; identical events are collapsed, and the transactions pointing at them follow |
| Provider assignment | Moved only if the survivor has none — otherwise the survivor keeps its own |
| Identifiers | **Merged**, never dropped: everything the deleted asset knew survives as an alternative identifier |

!!! warning "The source asset is deleted"

    Merging cannot be undone from the interface. Read the preview before confirming — it is an
    exact count, not an estimate.

!!! tip "You may be offered a merge during an import"

    When an import finds **two** assets answering to the same code — the classic signature of a
    duplicate created by an earlier import — the wizard shows a discreet notice with a **Merge**
    button, right where you can see both of them side by side. Name-only resemblances are never
    offered: two funds from the same issuer are supposed to look alike.

## 🔗 Related

- 📊 **[Asset Detail Page](detail/index.md)** — View and analyze asset data
- 🔌 **[Providers](providers/index.md)** — Available pricing providers

