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
        A[Start: Click '+ Add Asset'] --> B[Type Name, ISIN, or Ticker in Smart Search]
        B --> C{Match Found?}
        C -->|Yes| D[Auto-fill details from external providers]
        C -->|No| E[Manually enter name, type, & currency]
        D --> F[Adjust config / Assign pricing provider]
        E --> F
        F --> G[Click 'Create Asset']
        G --> H[Asset added to library]
    ```

    **Name** is required: while it is empty, the form says *Enter an asset name to continue.* The
    ⓘ icon next to **Currency** explains what that field is for — the currency used to store this
    asset's prices. Pick the currency its prices are quoted in: for a fund listed in euros that is
    EUR, even when the fund itself is denominated in another currency.

=== "Broker Import Auto-Creation"

    ```mermaid
    flowchart LR
        A[Start: Upload CSV report in Import Wizard] --> B[Parse report rows]
        B --> C{Asset ID recognized?}
        C -->|Yes| D[Auto-match with existing asset]
        C -->|No| E[Flag warning ⚠️ and offer 'Create new asset']
        E --> F[Choose 'Create new asset' to open pre-filled modal]
        F --> G[Save asset to resolve mapping]
        G --> D
        D --> H[Commit all transactions]
    ```

    In the wizard's **Resolve Assets** section, each security found in the report has a card with
    an asset selector. When LibreFolio finds no candidate at all for a security — typically the
    first time you import it — an **Assets to create manually** note explains the choice: link it
    to an existing asset, or choose **Create new asset** in the selector. Once the asset is saved,
    later imports recognise it by its saved identifier whenever the match is unique.

    The form opens pre-filled with what the report says: the security's codes, and a description
    listing the names and codes found. If the report gives no name, the **Name** field starts with
    the ISIN — or with the ticker when there is no ISIN — instead of staying blank; rename it as you
    like.

!!! info "Success notification"

    Saving from the **Add Asset** button on the asset list closes the modal at once and
    shows a success toast whose asset name is a clickable link straight to the new asset's
    detail page. If the asset has a pricing provider, that page's own post-creation flow then
    triggers a price sync for it — when that sync succeeds, it shows its own **follow-up
    success toast**, also with a clickable name.

    Creating an asset **from inside another flow** — the broker import wizard, a
    transaction's contextual "add asset" search, or the transaction form — behaves the
    same way for saving, but the modal instead hands the new asset back to that
    selector, and its confirmation stays plain text (no link), consistent with whatever
    notifications, if any, that flow already shows.

## 🧪 Testing Provider Configuration

After configuring a provider, click **Test Configuration** to verify that pricing data can be fetched. The test checks:

- **Current Price**: fetches the latest price
- **History**: fetches historical price data (if supported)

Results are displayed inline with execution times. A ⚠️ warning means the operation is not supported by this provider (e.g., CSS Scraper doesn't support history).

## 🔎 Smart Search Details

Smart Search is the **Search Online** box at the top of the asset form: type a name, ticker or ISIN
and pick one of the results.

Smart Search first asks each provider's own search. If a supported provider cannot find anything,
LibreFolio may try a best-effort web link search and resolve provider pages back into asset
candidates. For Borsa Italiana, this means a fund/detail URL can become a ready-to-save asset with
the `provider_params` needed to price the fund by its internal code.

For Borsa Italiana funds, the visible ISIN identifies the fund when available, but pricing uses the
internal Borsa fund code saved in provider configuration. Current NAV is used only when dated today;
history contains one NAV point at its real date.

## 🗂️ Choosing the Asset Type {: #choosing-the-asset-type }

The **Type** field opens a searchable menu of
[asset types](../../financial-theory/instruments/asset-types/index.md). Most types sit at the top
level; **ETF** and **Crowdfunding** are families you open to see their members. Each family lists its
generic member first — **ETF** (*mixed or unstated content*) and **Crowdfund** (*P2P and business
lending*) — followed by the specific ones, such as **Equity ETF** or **Real estate crowdfunding**.
Type a few letters to search across both levels, by name or by code (for example `etf_bond`); if the
current type belongs to a family, that family is already open.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="type-picker-open" alt="Type menu with the ETF family expanded, each specific ETF type showing its composite icon">
</div>

When Smart Search finds the instrument, the type is filled in from the provider — usually a general
one such as **ETF**. If you know what the fund holds, refine it — for example to **Equity ETF**: the
type then records what the fund contains as well as what it is, and its badge takes the colour of
what it holds. Specific types show their family's icon with a small circle in the corner showing
what they hold — the same icon you will see in the asset list and elsewhere in the app. A later
check against the provider's data keeps your refinement — see
[Comparing with the Provider's Data](#provider-data-comparison).

## ⚖️ Comparing with the Provider's Data {: #provider-data-comparison }

Each time LibreFolio reads an asset's details from its provider, it compares them with what the
form already holds. This happens automatically right after you pick a Smart Search result, and
whenever you click **Ask Provider** — at the top of **Asset Details** to check every field, or next
to **Identifiers** and in each distribution editor to check only that part. **Ask Provider** works
once a provider and its identifier are set in **Provider Assignment**.

- An empty field is simply filled in, alternative codes from the provider are added to
  **Other identifiers**, and a field that already matches is left alone.
- When the provider has no sector or geographic breakdown, a message names what is missing
  (*Provider has no data for: …*).
- If nothing differs and nothing is missing, a message confirms *All data matches provider*.
- Everything that differs is gathered in the **Provider Data Comparison** dialog.

<!-- [Screenshot Placeholder: assets/create-provider-compare — the Provider Data Comparison dialog with an identifier row and its main-code chooser, a Type row shown as icon badges, and a distribution row] -->

The dialog groups the differences under **Identifiers**, **Asset Details** and **Classification**.
Every row has a tick box and starts ticked; most rows show your **Current Value** next to the
**Provider Value**:

- **Identifiers** are never a plain swap: you choose which code is the main one, and the other is
  kept under **Other identifiers** — see [One instrument, several codes](#one-instrument-several-codes).
  The provider's code is proposed as the main one, since it is normally the quoted one.
- **Type** is shown on both sides as the badge the asset cards use: the type's icon and its name in
  your language.
- **Sector Distribution** and **Geographic Distribution** show both breakdowns side by side,
  largest share first.

Untick the rows where you want to keep your own value (**Select All** and **Deselect All** help),
then click **Apply Selected** — the button counts the rows you are taking, for example
*Apply Selected (2/3)*. **Cancel** leaves the form as it is. Either way nothing is saved yet: the
accepted values only fill in the form, and are stored when you save the asset.

!!! tip "Your ETF subtype is kept"

    Some providers know only an instrument's family: Borsa Italiana, for example, reports every
    ETFplus instrument simply as **ETF**. If you have refined the type to a member of that family —
    say **Equity ETF** — the comparison counts the provider's **ETF** as agreeing with it: no row
    appears, and your type stays. The same goes for the **Crowdfunding** family. A provider that
    proposes a *more specific* type than yours (for example **Equity ETF** for an asset still typed
    **ETF**) is still shown, so you can take the refinement.

!!! note "Each question is asked once"

    Picking a Smart Search result can raise a question first: if the result carries an ISIN (or
    another code) different from the one already in the form — typically one read from a broker
    report — LibreFolio asks which of the two is the main code
    (*Which ISIN is the main one for «…»?*). The comparison waits until you answer, or leave
    without choosing, and then drops the rows that would ask the same thing again; if nothing else
    is left, it does not open at all. It waits in the same way while the import wizard asks whether
    to reuse an existing asset with the same name.

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

In the asset modal ([create](#asset-creation-flows) or [edit](#editing-an-asset)) expand
**More Info**: below the identifiers, its **Classification** part holds two editors.

1. **Sector Distribution** — one row per sector, with its weight in percent.
2. **Geographic Distribution** — one row per country/area, with its weight in percent.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-distribution-editors" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="distribution-editor-sector" data-title="🏭 Sector Distribution" alt="Sector distribution editor in the asset modal">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="distribution-editor-geographic" data-title="🌍 Geographic Distribution" alt="Geographic distribution editor in the asset modal">
</div>

For each distribution you can:

- **Add sector** / **Add country** to add a row: pick the sector or country from the dropdown, then
  type the weight.
- **Edit weights inline**; the running **total** sits at the bottom of the editor and turns
  **green when it is less than 0.005 percentage points away from 100%** — amber when
  something is missing, red when you overshoot.
- **Balance to 100%** in a row's actions adds the whole gap to that row (or takes the excess from
  it); select several rows and use **Balance selected rows** to share it among them in proportion
  to their weights.
- **Remove** a row from its actions.

### 📥 Importing a Distribution CSV {: #importing-a-distribution-csv }

The **Import CSV** button accepts the same two-column format for geographic and sector data — a
header row of `name,weight` (or `name;weight`, see separators below) followed by one row per
country/area or sector:

```csv
name,weight
USA,60
Italy,40
```

`weight` is a percentage from `0` through `100`. Names are matched **exactly** after trimming
surrounding whitespace and normalizing letter case — there is no fuzzy matching:

- geographic names may be an ISO 2-letter code, an ISO 3-letter code, or the country's
  currently localized name;
- sector names may be a canonical sector key (such as `Government Bonds`) or the sector's
  currently localized label.

The import is **atomic and all-or-nothing**: it validates every row before touching anything,
and on success it **replaces the whole distribution** — rows already present in the editor that
are not repeated in the file are dropped, not merged. An invalid or unmatched name, a **name
repeated on two rows**, an out-of-range weight, or a total outside the green tolerance blocks
the whole import and nothing is changed. Imported weights are not auto-balanced. On acceptance,
each percentage is converted once to its stored fraction (`60` becomes `0.6`).

!!! tip "The 100% rule"

    Aim for a clean 100%. The editor and CSV importer accept totals only when the difference
    from 100% is strictly less than 0.005 percentage points. If the instrument is 100% one
    country or sector, a single row at 100 is both valid and the clearest choice.

!!! warning "Separator and decimal comma: avoid the silent-truncation trap"

    The importer auto-detects the column separator from the header row — `;` (semicolon) or
    `,` (comma) both work, whichever the first line uses. This is convenient for round-tripping
    exports, but it creates one real trap: if you use `,` as both the **column separator** and
    the **decimal separator** (e.g. `Italy,12,5` meaning 12.5%), the row is read as **three**
    fields instead of two, and the weight column silently becomes `12` — the `,5` is discarded
    without an error.

    To write a decimal-comma weight safely, pick one of:

    - use `;` as the column separator instead (unambiguous, decimal comma passes through as-is):

      ```csv
      name;weight
      Italy;12,5
      USA;87,5
      ```

    - or keep `,` as the column separator and **quote** any value that itself contains a comma:

      ```csv
      name,weight
      Italy,"12,5"
      USA,"87,5"
      ```

    A plain `.` decimal point (`Italy,12.5`) is never ambiguous with a comma-separated file and
    needs no quoting.

## 🏷️ One instrument, several codes {: #one-instrument-several-codes }

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

If you only notice later that the same instrument was created twice — by hand once and by an
import another time, under slightly different names, or under its subscription code once and its
market code another — each copy holds part of its history and neither shows the whole position.
On the **Assets** page, the **Merge** action folds one into the other: a button on each card, or
**Merge with…** in the right-click menu of the table.

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
