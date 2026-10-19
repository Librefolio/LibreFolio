---
applyTo: "frontend/**"
---

# Frontend Reference

## Structure

```text
frontend/
├── src/
│   ├── routes/(app)/          # Auth-protected pages
│   │   ├── dashboard/         # Dashboard (placeholder)
│   │   ├── brokers/           # List + [id] detail
│   │   ├── fx/                # Dual-view list + [pair] detail
│   │   ├── assets/            # Dual-view list + [id] detail
│   │   ├── transactions/      # Placeholder (Phase 7)
│   │   ├── files/             # File management
│   │   └── settings/          # User & global settings
│   ├── lib/
│   │   ├── charts/signals/    # Signal Library (10 signals)
│   │   ├── components/        # Reusable components
│   │   │   ├── ui/            # Base (select/, input/, media/, modals, banners, data-editor/)
│   │   │   ├── charts/        # ECharts (LineChart, Candlestick, ChartSettings, etc.)
│   │   │   ├── assets/        # Asset-specific (12 components)
│   │   │   ├── fx/            # FX-specific
│   │   │   ├── layout/        # Header, Sidebar, Footer, LanguageSelector
│   │   │   └── table/         # Generic DataTable
│   │   ├── stores/            # Svelte stores (14+)
│   │   ├── api/               # Zodios client + OpenAPI types
│   │   ├── utils/             # Shared utilities
│   │   └── i18n/              # Translations (EN, IT, FR, ES) — 840+ keys
│   └── app.css                # Design system (Tailwind v4 via @theme)
├── e2e/                       # Playwright E2E tests (181+)
└── build/                     # Static build (served by FastAPI)
```

## Detailed Instructions (auto-loaded by path)

| Scope | Instruction file |
|-------|-----------------|
| Signal Library | `frontend-signals.instructions.md` — all signals, base class, registry, adding new signals |
| E2E Testing | `frontend-testing.instructions.md` — Playwright patterns, fixtures, conventions |
| Lint & Format | skill `lint-format-frontend` — Prettier + svelte-check, config, workflow |
| Dead code | skill `lint-format-frontend` — `./dev.py lint --dead-code` (knip), unused files/exports/deps |

## Financial numbers

The frontend computes no financial quantity — cost, P&L, capital, NAV, returns, FX value, yields: it shows the fields the backend computes in `backend/app/services/financial_math/`; interactive measures (the measuring tool, what-if, the aggregates of the lots the user chooses — D-MF6(b)) are the only exceptions, and each must be declared where it lives.

## Design System

- **The design system — read it before building or changing any UI**: the two themes («Stone and Sage» in light, «Slate and Sage» in dark), every colour role with its value in both themes and when to use it, the shared colour folder `lib/theme/` (components take colours from it, never define them) and all the colour rules: skill `design-system` (`.github/skills/design-tools/design-system/SKILL.md`)
- **Tailwind CSS 4**: config via `@theme {}` in `app.css` (no TS config file); the colour roles live in `lib/theme/tokens.css`, which `app.css` imports
- **Colours are roles** (colour programme, workstream T): new and migrated code writes only the role utilities, never a palette class (`bg-white`, `text-gray-500`, `dark:bg-slate-800`) or a hand-written colour (`#1a4031`, `rgba(…)`, `white`)
  - surfaces `bg-lf-app` (behind the shell), `bg-lf-page` (standalone pages), `bg-lf-header` (the app header, D-T23), `bg-lf-card`, `bg-lf-panel`, `bg-lf-field`, `hover:bg-lf-hover`, `bg-lf-neutral`, `bg-lf-inverse`, `bg-lf-overlay`, `bg-lf-logo`; floating card, modal or dropdown `border-lf-raised shadow-lf-shadow`
  - the green sidebar, one family in both themes: `bg-lf-bar`, `text-lf-bar-text`, `hover:bg-lf-bar-hover`, active `bg-lf-bar-active text-lf-on-bar-active`, focus `outline-lf-bar-focus`, states `text-lf-bar-<state>` (D-T17)
  - text `text-lf-primary`, `text-lf-secondary`, `text-lf-muted`, `placeholder:text-lf-placeholder`, `text-lf-link`; borders `border-lf-subtle`, `border-lf-input` (`hover:border-lf-input-hover`); focus `ring-lf-focus`
  - brand `bg-lf-brand` + `text-lf-on-brand` (the login card header), primary button `bg-lf-action hover:bg-lf-action-hover text-lf-on-action`, `bg-lf-selected`, selected control `bg-lf-checked` + `text-lf-on-checked` (D-T16)
  - states `success`, `warning`, `danger`, `info`: `text-lf-<state>`, `bg-lf-<state>-soft`, `border-lf-<state>-line`, `text-lf-<state>-on-soft`, `bg-lf-<state> text-lf-on-status`; solid red button `bg-lf-danger-solid text-lf-on-danger-solid`; `text-lf-gain`, `text-lf-loss`, `text-lf-donate`
  - special: switch `bg-lf-switch-*`, terminal `bg-lf-terminal`, `<mark>` `bg-lf-mark`, AI `text-lf-ai`; the full palette, with both themes' values and when to use each role, is in the skill `design-system`
- **Dark theme**: a role changes value under `html.dark` — never write `dark:` on a role utility. A component not migrated yet keeps its look from the frozen legacy remap of `app.css` (P1); migrate an element whole, never mixing roles and palette classes on it
- **Gates**: `src/themeRoles.gate.test.ts` (a ratchet: legacy classes and colour literals per file only go down; role grammar) and `src/themeTokens.gate.test.ts` (both themes, contrast pairs). A file split is declared in the same commit: `node frontend/scripts/theme/theme-roles.mjs --split OLD:NEW1,NEW2`. How to migrate, the class → role table and the merge rule of the baseline: skill `theme-roles` (`.github/skills/design-tools/theme-roles/SKILL.md`)
- **Font**: `'LF Flags', Inter, system-ui, sans-serif` (`html`, `@theme --font-sans`; `--font-mono` also starts with `'LF Flags'`)
- **Flags**: `'LF Flags'` (`static/lf-flags.css`, linked by `app.html` and `offline.html`) draws only the flags (`unicode-range: U+1F1E6-1F1FF`) — Apple flags on Apple devices, the self-hosted Noto flags subset elsewhere. Never name an emoji font in a `font-family`: emoji fonts also draw digits, `#` and `*`. A component with its own stack starts it with `'LF Flags'` or wraps the flag in `.emoji-flag`. Gate: `src/flagFont.gate.test.ts`; ECharts text is not covered yet
- **Icons**: lucide-svelte

## Stores (`lib/stores/`)

| Store | File | Pattern | Role |
|-------|------|---------|------|
| `TimeSeriesStore<T>` | `.ts` | Generic class | Client-side time-series cache with `Map<string,T>`, gap-detection for delta-fetching, idempotent merge |
| `fxStoreRegistry` | `.ts` | Registry | `pairKey → TimeSeriesStore<FxDataPoint>` map |
| `EditBuffer<T>` | `.ts` | Generic class | Bidirectional edit buffer (click ↔ CSV ↔ form), bulk save |
| `chartSettingsStore` | `.svelte.ts` | Svelte 5 runes | 2-level: global + per-pair overrides. Session-lifetime only |
| `themeStore` | `.ts` | Functions + localStorage | Dark/light/auto. Key: `librefolio-theme` |
| `countryStore`, `sectorStore`, `currencyStore` | `.ts` | Writable | Backend data caches |
| `currencyGraphStore` | `.ts` | Writable | Currency conversion graph for triangulation |
| `toastStore` | `.svelte.ts` | Svelte 5 runes | Toast notifications with auto-dismiss |
| `notify` | `.svelte.ts` | Svelte 5 runes | One notification, two halves: event ring buffer (machine) + optional toast (human) |
| `auth`, `settings`, `language`, `globalSettings` | `.ts` | Writable | Global app state |

**Pattern**: `.svelte.ts` = Svelte 5 runes; `.ts` = Svelte 4 writable or plain class.

## Privacy masking

Privacy hides the **number**, never the currency or the sign (`€•••`, `-••• CHF`); an absent `—`
stays `—`. Render money only through `lib/utils/currency/currencyFormat.ts` with an explicit
`sensitivity` (`personal` = wealth; `public` = prices, WAC, rates, percentages) or the primitives
in `lib/utils/privacy/maskable.ts`; mask held quantities with `maskableQuantity()` **at the call
site** (positions and lots masked, transactions visible).

- A **legacy** (non-runes) component that calls a formatter inside its template freezes that
  output at mount: the call compiles into `$.untrack`, so the privacy flag is never tracked.
  Render through `ui/display/CurrencyAmount.svelte` instead.
- ECharts formatters run outside effect tracking: the render `$effect` must read
  `isPrivacyEnabled()`, or the chart keeps the state it was drawn with.
- The gate `utils/privacy/moneyRenderSites.test.ts` sees only source lines with a currency
  token: axes without one, a `public` marking and legacy freezing need their own tests (a
  component test that toggles privacy in place, both ways).

## Telling the user (and the machine) that something happened

Use `notify()` from `$lib/stores/app/notify.svelte.ts`. It always records a
structured event; it raises a toast only when one is owed.

```ts
notify({
    name: 'tx.import.committed',          // stable, NEVER translated
    detail: {imported: 47, skipped: 3},   // structured
    toast: {variant: 'success', message: $t('tx.import.done', {n: 47})},  // optional
});
```

The toast and the event are **not alternative channels** — they are the human
half and the machine half of one notification. `toast` is a *field*, not another
call. The message stays free-form HTML (AI Export puts the prompt size in it);
the structured payload lives in `detail`, which is what tests read, because the
toast text is translated into four languages.

### When a toast is owed

A toast is owed when the outcome is **not already visible**, or is
**irreversible**, or is **partial**. Everything else is a silent event.

| # | case | toast | example |
|---|------|-------|---------|
| 1 | outcome already visible in the current view | ✗ | inline cell save — the value changes under the user's eyes; a deleted row disappears |
| 2 | outcome invisible | ✓ | copy to clipboard, file download, background sync started, a save that does not change the current view |
| 3 | irreversible or costly | ✓ with the count | bulk delete, asset merge, committed import — "47 imported, 3 skipped" |
| 4 | partial / degraded | ✓ always | 10 assets synced, 2 failed. Silence here would be a lie |
| 5 | error | ✓ always | already the practice: 45 of the 98 existing call sites |
| 6 | internal transition | ✗ | cache invalidated, store reloaded, wizard step, debounce fired |

### Publish state, do not print it

Every container that reloads publishes `data-busy` (`'true'`/`'false'`) plus
`aria-busy` on its root. It is the one signal for "all load waves are in" — the
assets and fx pages load rows first and prices second, and only `data-busy`
knows about both. A console line cannot do this job: it is an edge, so a reader
that arrives late has already missed it, and `debug` is compiled out of the
production build the E2E suite runs against.

Naming: `area.thing.past-tense` — `asset.saved`, `fx.rates.synced`,
`tx.import.committed`.

### API errors in the console

The API client writes every unexpected API failure to the browser console, in production too (lot H-60):
`lib/api/apiErrorConsole.ts`, called by the Axios response interceptor and by the `zod-validation` plugin of
`lib/api/zodios-client.ts`. One line: `console.error('[API]', '<status> <METHOD> <path>', {code, reason_code,
component_id, request_id, error_type})`, `network` for a call nothing answered, `schema` for an answer that breaks its
schema (with the issues' paths). How much follows the instance, `client_log_level` of `/system/instance` (the backend's
`LOG_LEVEL`): `error` writes server errors, network failures and schema mismatches; `debug` writes every 4xx too. A
canceled request is not a failure.

- **Do not add a `console.*` of your own for an API error**, and never print an error object whole: an Axios error
  holds the request's body and configuration, a `ZodiosError` message embeds the whole answer it refused.
- **Never print** a request body, a header (the `X-Request-Id` aside), a token, a password, a query string, the text of
  a `detail`, the `input` a 422 can repeat.
- **To show the id to the user**, in a generic error message: `requestIdOf(error)`.
- A console line is for the human who investigates; it is never the signal a test or a component reads («Publish
  state, do not print it»).

## Chart Components (`lib/components/charts/`)

14 files, ~5100 lines. Key components:

| Component | Lines | Role |
|-----------|-------|------|
| `PriceChartFull` | 967 | Full chart for detail pages (single ECharts instance, signals, measure, edit) |
| `ChartSignalsSection` | 734 | Signal overlay management (3 categorized dropdowns + style popovers) |
| `LineChart` | 714 | Core line chart (multi Y-axis, visualMap, stale gradient) |
| `MeasurePanel` | 569 | 2-click measurement overlay (Δabs, Δ%, days) |
| `lineChartHelpers` | 515 | Extracted rendering helpers |
| `ChartSettingsModal` | 354 | Aesthetics + signals modal |
| `SemiDonutChart` | 310 | Half-donut for ownership distribution |
| `GeographyMap` | 238 | Choropleth world map |
| `SectorPieChart` | 190 | Sector pie chart |
| `PriceChartCompact` | 58 | Mini-chart for cards |

## Asset Components (`lib/components/assets/`)

15 files, ~6300 lines. Key components:

| Component | Lines | Role |
|-----------|-------|------|
| `ScheduledInvestmentEditor` | 1412 | Complex multi-step scheduled investment plan editor |
| `AssetModal` | 1328 | Create/Edit modal with SearchAutocomplete + provider auto-assign |
| `ProviderAssignmentSection` | 724 | Dynamic form from backend `params_schema` |
| `AssetDataEditorSection` | 493 | Price/event inline editor (integrates EditBuffer) |
| `AssetSearchAutocomplete` | 399 | Multi-provider parallel search with auto-fill |
| `ProviderComparisonModal` | 323 | Provider vs DB data diff |
| `AssetCard` | 287 | Card with mini-chart, type badge, price, Δ% |
| `AssetTable` | 265 | DataTable with multi-period Δ columns |

## i18n

- **Library**: svelte-i18n
- **Languages**: EN, IT, FR, ES (read the live key count from `./dev.py i18n audit`)
- **Generated catalogue**: `lib/i18n/{en,it,fr,es}.json`, built by `scripts/i18n_catalog.py`, ignored by git and
  read-only — never edit it (a hand edit stops the build). The npm pre-hooks, Vitest and `./dev.py front build` write it
- **Sources** (edit these, or better use the CLI): `lib/i18n/base/` (the generic vocabulary), one folder per subsystem
  `lib/i18n/<subsystem>/` with its `prefixes.txt`, and each plugin's `backend/app/services/<family>/<plugin>/i18n/`
- **CLI**: `./dev.py i18n where|add|update|remove|search|tree|audit|check|build|move|split|absorb` — `add` writes to the
  source that owns the key (see skill `devpy-i18n`)

## Where to Find Things

| What | Where |
|------|-------|
| Frontend pages | `frontend/src/routes/(app)/` |
| Base UI components | `frontend/src/lib/components/ui/` |
| Chart components | `frontend/src/lib/components/charts/` |
| Signal Library | `frontend/src/lib/charts/signals/` |
| Asset components | `frontend/src/lib/components/assets/` |
| Stores | `frontend/src/lib/stores/` |
| API Client (Zodios) | `frontend/src/lib/api/` |
| Translations (sources) | `frontend/src/lib/i18n/base/`, `frontend/src/lib/i18n/<subsystem>/`, plugins' `i18n/` |
| E2E Tests | `frontend/e2e/` |
