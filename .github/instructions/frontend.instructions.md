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

## Design System

- **Tailwind CSS 4**: config via `@theme {}` in `app.css` (no TS config file)
- **Brand colors**: `#1a4031` (libre-green), `#f5f4ef` (libre-beige)
- **Full dark mode**: CSS variables in `html.dark`
- **Font**: Inter, system-ui, sans-serif + `Noto Color Emoji` for flags
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
- **Languages**: EN, IT, FR, ES (840+ keys per language)
- **Files**: `lib/i18n/{en,it,fr,es}.json`
- **CLI**: `./dev.py i18n audit|add|remove|update|search|tree` (see skill `devpy-i18n`)

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
| Translations | `frontend/src/lib/i18n/{en,it,fr,es}.json` |
| E2E Tests | `frontend/e2e/` |
