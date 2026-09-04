# 🔽 Select & Dropdown Components

This section documents the reusable dropdown and select components in `lib/components/ui/select/`.

There is **no shared base component**: `SimpleSelect` and `SearchSelect` each self-contain their
open/close state, click-outside dismissal, keyboard navigation, and dropdown positioning
(`position: fixed`, so the dropdown is never clipped by `overflow` parents). The shared logic
that exists lives in plain TypeScript — `optionFilter.ts` (searchable-step/filter helpers) and
`types.ts` (`SelectOption`). Every specialized select composes one of the two generic ones.

## 🏗️ Component Hierarchy

```mermaid
graph TD
    SS["<b>SimpleSelect</b><br/><small>Fixed option list · Checkmark active<br/>Custom rendering via snippets</small>"]

    SrS["<b>SearchSelect</b><br/><small>+ Fuzzy search · Max visible items<br/>+ Inline search mode · Loading state</small>"]

    SrS --> CSS["<b>CurrencySearchSelect</b><br/><small>+ Flag emoji · ISO code + name<br/>📡 <code>/utilities/currencies</code></small>"]

    SrS --> FPS["<b>FxProviderSelect</b><br/><small>+ Provider icon · Info bar + docs link<br/>📡 <code>/fx/providers</code></small>"]

    SrS --> IPS["<b>ImportPluginSelect</b><br/><small>+ Plugin icon · Format badges<br/>📡 <code>/brim/plugins</code></small>"]

    SrS --> BSS["<b>BrokerSearchSelect</b><br/><small>+ BrokerIcon · Inline search<br/>📡 <code>/brokers</code></small>"]

    SrS --> MORE["<b>More specialized selects</b><br/><small>Asset · Country · Sector · User<br/>(same <code>SearchSelect</code> composition)</small>"]

    style SS fill:#e8f5e9,stroke:#2e7d32
    style SrS fill:#e8f5e9,stroke:#2e7d32
    style CSS fill:#fff3e0,stroke:#e65100
    style FPS fill:#fff3e0,stroke:#e65100
    style IPS fill:#fff3e0,stroke:#e65100
    style BSS fill:#fff3e0,stroke:#e65100
    style MORE fill:#fff3e0,stroke:#e65100
```

Two generic layers, then domain-specific wrappers:

- 🟢 **SimpleSelect / SearchSelect** — generic, self-contained selects with rendering
- 🟠 **Specialized selects** — domain-specific with API data loading

!!! note "BaseDropdown is gone"

    `BaseDropdown.svelte` was deleted (03/09) as an orphaned abstraction — the two generic
    selects now own their open/close and positioning logic directly. Docs or code that present
    BaseDropdown as the foundation of this hierarchy are stale.

---

## 📋 SimpleSelect

A basic dropdown for selecting from a fixed list of options, similar to a native `<select>`.

- Renders a button trigger showing the selected value
- Displays options in a dropdown with checkmark on the active item
- Supports disabled state and custom item rendering via snippets
- Keyboard navigable

**Used in**: Filter dropdowns, form fields with small option sets (e.g., theme selector, page size).

---

## 🔎 SearchSelect

A dropdown with integrated **fuzzy search**. The user can type to filter options.

- Fuzzy matching on option labels
- Configurable `maxVisibleItems` (default: 8) with scrollable dropdown
- `inlineSearch` mode — search input in the trigger itself (used by BrokerSearchSelect)
- Loading state with spinner
- Supports custom item rendering via `option` snippet

**Used in**: User search in sharing modal, any select with many options.

---

## 💰 CurrencySearchSelect

A specialized `SearchSelect` for currency selection.

- Shows **flag emoji** + currency code + name for each option
- Loads options from the `/utilities/currencies` API
- Filters by code or name
- Auto-selects the first match

**Used in**: Add Pair modal (base/quote currency), Broker form (base currency).
**Data source**: `GET /api/v1/utilities/currencies` — ISO 4217 reference list.

---

## 🔌 FxProviderSelect

A specialized select for FX data providers.

- Shows provider name with icon
- **Info bar** below the dropdown with provider details and a link to the docs page
- Reads `docs_url` from provider metadata to generate the documentation link

**Used in**: `FxProviderConfig` component on the FX detail page.
**Data source**: `GET /api/v1/fx/providers` — registered FX provider plugins.

---

## 📥 ImportPluginSelect

A select for BRIM import plugins.

- Shows plugin name with provider icon (loaded from API)
- Groups plugins by broker type
- Displays supported file formats (CSV, Excel)

**Used in**: `BrokerImportFilesModal` — selecting which parser to use for a broker report.
**Data source**: `GET /api/v1/brim/plugins` — registered BRIM provider plugins.

---

## 🏦 BrokerSearchSelect

A `SearchSelect` specialized for broker selection.

- Shows `BrokerIcon` + broker name for each option
- `inlineSearch` mode — type directly in the trigger to filter
- Loads brokers from the API with user access filtering

**Used in**: Transaction filters, transfer/FX conversion forms (selecting source/destination broker).
**Data source**: `GET /api/v1/brokers` — user's accessible brokers (filtered by RBAC).
