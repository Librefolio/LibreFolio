# 🧩 Frontend Components

This section documents the reusable UI components in LibreFolio, organized by functional area.

## 📚 Component Categories

The library is split into two architectural layers: **Core UI** (generic atoms and molecules) and **Features** (domain-specific components).

### Core UI
| Component | Details |
|-----------|---------|
| **[Core UI overview](core-ui/index.md)** | Modals (`ModalBase`, `ConfirmModal`, sync modals), feedback (`ToastContainer`, `Tooltip`, `InfoBanner`), pickers (`DateRangePicker`), `PageToolbar`, `DataEditor`, atoms and inputs (`PrivacyToggle`, `ExactDecimalInput`, `ExactQuantityInput`, `CompactDurationBadge`), display blocks (`KpiMetricBar`, `KpiDivergingFlowBar`, `RiskMetricCard`, `RiskCardGrid`). Generic building blocks. |
| **[DataTable](core-ui/data-table.md)** | Advanced data grid with sorting, filtering, pagination, sticky columns and column management. |
| **[File Upload & Media](core-ui/file-upload.md)** | `FileUploader`, `ImageCropper`, `ImageEditModal`, `AssetPickerModal`, `LazyImage`. |
| **[Select & Dropdowns](core-ui/select.md)** | `SimpleSelect`, `SearchSelect` and `TreeSelect` with keyboard navigation, specialized wrappers (`AssetTypeSelect`, `CurrencySearchSelect`, …) and `AssetPickerPanel` on `SelectPopover` + `CheckMenu`. A typed search ranks matches in the option's name or value above matches found only in its description — see [Ranking the matches](core-ui/select.md#ranking-the-matches). |

### Features (Domain)
| Component | Details |
|-----------|---------|
| **[Transaction Form](features/transaction-form.md)** | Complex modal for creating/editing transactions with reactive auto-calculation and live WAC preview. |
| **[Import Wizard](features/import-wizard.md)** | Multi-file staged broker import: duplicate detection (vs DB and in-batch), the file-priority batch resolver, and the N-way compare modal. |
| **[Brokers](features/brokers/index.md)** | `BrokerCard`, `BrokerForm`, `BrokerModal`, `DeleteBrokerDialog`, and Broker Sharing. |
| **[Settings](features/settings.md)** | `SettingsLayout`, `PreferencesTab`, `GlobalSettingsTab`. |
| **[Authentication](features/auth.md)** | `LoginCard`, `RegisterCard`, `ForgotPasswordCard`, the password-manager contract. |
| **[Live Prices](features/live-ticker.md)** | How the Assets list and the asset detail page poll `POST /assets/prices/current` every 30 s (60 s for the asset-detail chart head), and how a price change is shown. |
| **[Lots Analysis](features/lots-analysis.md)** | `LotsAnalysisPanel` and its chart/table/modal group: per-lot WAC vs market price, custody Gantt, unified lots table, value/return comparison, custody drill-down modal. |

## 🧭 App Header {: #app-header }

`lib/components/layout/Header.svelte` is the bar above every authenticated page (mobile menu,
privacy and theme toggles, language and help menus). It is `sticky` on every viewport and gives the
page its height back while the user reads:

- **Scrolling down** at least 8 px in a row hides it (it slides up by its own height); **scrolling
  up** at least 4 px brings it back. Within the first header-height of the page it is always shown.
- It stays **pinned** — never hides — while keyboard focus is inside it, while the Help or Language
  menu is open, while the mobile sidebar is open, while any modal is open (it watches the
  `ModalBase` scroll-lock counter on `document.body`), while an onboarding guide runs, or when the
  `keepVisible` prop is set.
- A route change, a window resize or a change of its own height shows it again.

The scroll position is sampled once per animation frame; the slide is a 200 ms transform, disabled
under `prefers-reduced-motion`. The state is published as `data-scroll-state` (`visible`, `hidden`,
`pinned`) next to `data-menu-open`, `data-modal-open`, `data-sidebar-open` and `data-guide-active`:
`Header.test.ts` tests the state machine, `e2e/layout/header-scroll.spec.ts` the real geometry.

## 📏 Component Guidelines

- **ModalBase**: ALL modals are built on `ModalBase.svelte` (directly, or through `ConfirmModal` / `SyncModalBase`) with configurable z-index
- **Svelte 5 Runes**: Use `$state`, `$derived`, `$effect`, `$props`
- **Event handling**: Use `onclick` instead of `on:click` (Svelte 5 syntax)
- **Styling**: Tailwind CSS utilities + dark mode with `dark:` prefix — see [Styling](../styling.md)
- **HTML strings**: escape user- and provider-supplied text with `escapeHtml` before it reaches `{@html}`; toasts and tooltips also sanitise what they render
- **Amounts**: format money through the shared currency formatters, so the privacy toggle masks it — see [Privacy masking](../state/app-state.md#privacy-masking)
- **Accessibility**: Keyboard navigation, ARIA labels, focus management
- **i18n**: All user-facing text via `$t('key')` translation function
