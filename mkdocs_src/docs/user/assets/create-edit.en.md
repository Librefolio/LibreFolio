# ➕ Create & Edit Assets

Add an instrument you hold or follow, connect it to a price provider and keep its details right.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-create" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="create-modal" data-title="➕ Manual Creation Form" alt="Manual Create Modal">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="create-wizard-modal" data-title="🧙 Import Wizard Auto-Creation Form" alt="Create Asset from Wizard">
</div>

## 🚀 Create an asset {: #asset-creation-flows }

=== "From the Assets page"

    1. On the **Assets** page, click **+ Add Asset**.
    2. In **Search Online**, type a name, ticker or ISIN and pick a result: LibreFolio fills in the
       form, connects that provider and [checks its data](#provider-data-comparison). No result?
       Fill in the form yourself.
    3. Check the fields below, then click **Create Asset**.

=== "From a broker import"

    1. In the import wizard's **Resolve Assets** section, choose **Create new asset** in the
       security's selector.
    2. The form opens with the report's codes and names. If the report has no name, **Name**
       starts with the ISIN (or the ticker).
    3. Click one of the **Suggestions** under **Search Online** to look the security up, or fill in
       the form yourself. Then click **Create Asset**.

    If the result you pick has the same name as one of your assets, LibreFolio offers to use that
    asset instead; **Use it and add the key** also saves the report's codes on it.

Check these fields before saving:

- **Name**: required and unique; a warning appears if another asset already uses it.
- **Type**: see [Choose the asset type](#choosing-the-asset-type).
- **Units per single price**: how many units one price refers to, usually 1. Bonds are quoted per
  100: LibreFolio proposes it when you choose **Bond**.
- **Currency**: the currency the prices are quoted in. For a fund listed in euros that is EUR,
  even when the fund is denominated in another currency.

After saving from the **Assets** page, the confirmation links to the new asset. If the asset has a
provider, its price history starts downloading right away.

## 🗂️ Choose the asset type {: #choosing-the-asset-type }

The **Type** field opens a searchable menu of
[asset types](../../financial-theory/instruments/asset-types/index.md). **ETF** and
**Crowdfunding** are families: open one to see its generic member first (**ETF**, **Crowdfund**),
then specific ones such as **Equity ETF** or **Real estate crowdfunding**. Type a few letters to
search both levels, by name or code (for example `etf_bond`).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="type-picker-open" alt="Type menu with the ETF family expanded, each specific ETF type showing its composite icon">
</div>

**Search Online** usually sets a general type such as **ETF**. If you know what the fund holds,
refine it, for example to **Equity ETF**: its badge and icon then show what it holds. A later
[check against the provider's data](#provider-data-comparison) keeps your choice.

## 🔌 Connect a price provider

Picking a **Search Online** result connects its provider for you. To set one up by hand, expand
**Provider Assignment** (untick **No Provider** first if it is ticked):

1. Choose the **Provider**, then enter the **Identifier**, its **Identifier Type** and any settings
   the provider asks for.
2. Click **Test Configuration**: LibreFolio fetches a **Current Price** and a few days of
   **History**. ⚠️ means the provider does not offer that data or has none right now (CSS Scraper
   has no history, for example); the test still passes. ❌ is an error: check the identifier and
   the settings.

An asset has at most one provider; tick **No Provider** if you will enter its prices yourself. See
[Providers](providers/index.md) for what each one offers.

## ⚖️ Check the provider's data {: #provider-data-comparison }

LibreFolio compares the provider's details with your form after you pick a **Search Online**
result, and when you click **Ask Provider**: at the top of **Asset Details** for everything, next
to **Identifiers** or in a distribution editor for that part only. It needs a provider and an
identifier.

- Empty fields are filled in, and the provider's extra codes join **Other identifiers**.
- *Provider has no data for: …* names a missing sector or geographic breakdown; *All data matches
  provider* means there is nothing to review.
- Anything that differs opens the **Provider Data Comparison** dialog.

<!-- [Screenshot Placeholder: assets/create-provider-compare — the Provider Data Comparison dialog with an identifier row and its main-code chooser, a Type row shown as icon badges, and a distribution row] -->

Each row of the dialog shows your **Current Value** next to the **Provider Value**, and starts
ticked:

1. Untick the rows where you want to keep your value (**Select All** and **Deselect All** help).
2. On an identifier row, choose the main code; the other is kept under **Other identifiers** (see
   [Edit identifiers](#one-instrument-several-codes)). The provider's code is proposed, as it is
   normally the quoted one.
3. Click **Apply Selected**, which counts the rows you take (for example *Apply Selected (2/3)*),
   or **Cancel** to change nothing.

The accepted values only fill in the form: they are stored when you save the asset.

- **Your refined type is kept.** Borsa Italiana, for example, reports every ETFplus instrument as
  plain **ETF**: if you chose **Equity ETF**, that counts as agreeing and no row appears (the same
  goes for **Crowdfunding**). A type *more specific* than yours is still offered.
- **Each question is asked once.** When a search result brings a different ISIN (or other code)
  from the one in the form, LibreFolio first asks which is the main one, and the comparison does
  not ask again.

## 🛠️ Edit an asset {: #editing-an-asset }

On the asset's [detail page](detail/index.md), click **Edit** (✏️), change what you need in the
**Edit Asset** form, and click **Save Changes**.

A new **Currency** for an asset that already has prices means deleting its stored prices and
events: on saving, a dialog lists what goes (transactions stay) and offers a backup. After
**Delete & Change Currency**, prices are downloaded again from the provider, if there is one.

## 🏷️ Edit identifiers {: #one-instrument-several-codes }

One security can have several codes. LibreFolio keeps **one asset** with all of them, under
**More Info** in the asset form:

- **Identifiers**: the main codes, one per type (ISIN, ticker…). **Add identifier** adds a row and
  **Ask Provider** fetches them.
- **Other identifiers**: any extra code or broker label. Type one and press Enter, comma, semicolon
  or Tab. These codes are searchable and help recognise the asset on later imports.

!!! tip "Keep the quoted code as the main ISIN"

    A price is the value of the last trade, so only a tradeable code has a price. Put that code in
    **ISIN** and everything else in **Other identifiers**, or no provider can price the asset.

### 🏛️ Italian retail government bonds (BTP Valore, BTP Più, BTP Italia)

These bonds are subscribed under one ISIN and traded under another:

| Phase | Code | What it does |
|---|---|---|
| Subscription at issue | the "CUM" ISIN | Entitles you to the **loyalty premium** if you hold to maturity. **Not tradeable**, so no provider quotes it |
| Secondary market | a different ISIN | Freely traded and **quoted**: this is the one with a price |

To sell before maturity, the bond is converted to the market code. Keep both codes on one asset:

1. Put the **market ISIN** in **ISIN**.
2. Put the **CUM ISIN** in **Other identifiers**.
3. Record the **loyalty premium**, when it is paid, as an **Interest** transaction on that asset.
   This works after maturity too: a deactivated asset stays selectable.

When an import brings the CUM code for an asset that holds the market one, LibreFolio asks which
code should lead and keeps the other under **Other identifiers**.

## 🗺️ Set sector and country distributions

Providers fill in the sector and geographic breakdowns when they can; for other assets, set them
yourself. They feed the dashboard's allocation charts and the AI Export.

In the asset form, expand **More Info**: under **Classification**, **Sector Distribution** and
**Geographic Distribution** list one row per sector or country, with its weight in percent.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-distribution-editors" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="distribution-editor-sector" data-title="🏭 Sector Distribution" alt="Sector distribution editor in the asset modal">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="distribution-editor-geographic" data-title="🌍 Geographic Distribution" alt="Geographic distribution editor in the asset modal">
</div>

- **Add sector** / **Add country** adds a row: pick the entry, then type its weight.
- The **Total** turns green at 100%, amber when something is missing, red when you go over.
- **Balance to 100%**, a row action, moves the whole gap into that row. **Balance selected rows**
  shares it among the selected rows, in proportion to their weights.
- **Remove** deletes a row, **Ask Provider** fetches the provider's breakdown, and **Import CSV**
  loads one from a file.

### 📥 Import a distribution from CSV {: #importing-a-distribution-csv }

**Import CSV** expects a `name,weight` header, then one row per country or sector, with weights in
percent:

```csv
name,weight
USA,60
Italy,40
```

- **Names** must match exactly, ignoring letter case and surrounding spaces. Countries: an ISO code
  (`IT`, `ITA`) or the name in your language. Sectors: the sector key (such as `Government Bonds`)
  or the name in your language.
- **Weights** go from `0` to `100` and must total 100 (within 0.005 points); each name appears
  once.
- The import is **all-or-nothing**: one bad row blocks it. When it succeeds, it **replaces** the
  whole distribution.

!!! warning "Decimal commas"

    The separator, `,` or `;`, is read from the header. With `,`, the row `Italy,12,5` is silently
    read as `12`. Use `;` throughout (`name;weight`, then `Italy;12,5`), quote the value
    (`Italy,"12,5"`), or write `Italy,12.5`.

## 🧲 Merge duplicate assets

If the same instrument ended up as two assets, each holds part of its history. To fold one into
the other:

1. On the **Assets** page, use **Merge with…** on the asset that should disappear: the button on
   its card, or the right-click menu in the table.
2. Choose the asset to keep (inactive ones too) and click **Continue**. On a day both have a price,
   the kept asset's price wins; so does its price provider, if it has one.
3. Read **What moves**: the exact counts of transactions, prices and events. Where both assets
   have a different code of the same type, choose the one that leads.
4. Click **Merge and delete**. The first asset is deleted; this cannot be undone.

No identifier is lost: each code of the deleted asset fills an empty field of the kept one or joins
its **Other identifiers**. Identical events are merged.

During an import, when two of your assets carry a security's ISIN, its **Resolve Assets** card
says *Two stored assets match this security* and offers **Merge**. Matching names alone never
trigger it.

## 🔗 Related

- 📊 **[Asset Detail Page](detail/index.md)** — View and analyze asset data
- 🔌 **[Providers](providers/index.md)** — Available pricing providers
- 🧬 **[Asset Identity](../../developer/frontend/components/features/asset-identity.md)** — For developers: how identifiers, provider comparisons and merges work
