# LibreFolio — Frontend Reference

## 📁 Struttura

```text
frontend/
├── src/
│   ├── routes/(app)/          # Pagine protette da auth
│   │   ├── dashboard/         # Dashboard (placeholder)
│   │   ├── brokers/           # Lista + [id] dettaglio
│   │   ├── fx/                # Lista dual-view + [pair] dettaglio (Phase 5)
│   │   ├── assets/            # Lista dual-view (1116 righe) + [id] dettaglio (1185 righe) (Phase 6)
│   │   ├── transactions/      # Placeholder (Phase 7)
│   │   ├── files/             # File management
│   │   └── settings/          # User & global settings
│   ├── lib/
│   │   ├── charts/signals/    # Signal Library (10 segnali)
│   │   ├── components/        # Componenti riutilizzabili
│   │   │   ├── ui/            # Base (select/, input/, media/, modals, banners, ViewModeToggle, data-editor/)
│   │   │   ├── charts/        # ECharts (LineChart, Candlestick, ChartSettings, etc.)
│   │   │   ├── assets/        # Asset-specific (12 componenti, 5587 righe)
│   │   │   ├── fx/            # FX-specific (FxCard, FxTable, FxPairAddModal, FxSyncModal, etc.)
│   │   │   ├── layout/        # Header, Sidebar, Footer, LanguageSelector
│   │   │   ├── settings/      # Settings tabs
│   │   │   ├── brokers/       # Broker-specific
│   │   │   ├── auth/          # Login, Register, ForgotPassword
│   │   │   ├── files/         # FilesTable
│   │   │   └── table/         # DataTable generico
│   │   ├── stores/            # Svelte stores (14+)
│   │   ├── api/               # Zodios client + OpenAPI types
│   │   ├── utils/             # Utility condivise (14 file)
│   │   └── i18n/              # Traduzioni (EN, IT, FR, ES) — 840+ chiavi
│   └── app.css                # Design system (Tailwind v4 via @theme)
├── e2e/                       # Playwright E2E tests (181+)
└── build/                     # Build statica (servita da FastAPI)
```

---

## 🎨 Design System

- **Tailwind CSS 4**: config via `@theme {}` in `app.css` (no file config TS)
- **Colori brand**: `#1a4031` (libre-green), `#f5f4ef` (libre-beige)
- **Dark mode completo**: variabili CSS in `html.dark`
- **Font**: Inter, system-ui, sans-serif + `Noto Color Emoji` per bandiere
- **Icone**: lucide-svelte

---

## 📊 Componenti Chart (ECharts)

Libreria modulare in `lib/components/charts/`:

| Componente | Uso |
|-----------|-----|
| `LineChart` | Multi-asse Y, visualMap (rosso/verde), stale gradient |
| `CandlestickChart` | Candele forex (apertura = chiusura giorno precedente) |
| `DataZoomBar` | Zoom temporale bidirezionale |
| `MeasureOverlay` | Click-to-click con Δabs, Δ%, giorni |
| `ChartSettingsModal` | Estetica + segnali overlay, preview sinusoide live |
| `PriceChartFull` | Chart completo (detail page FX e Assets) |
| `PriceChartCompact` | Mini-chart (card) |
| `SemiDonutChart` | Semicerchio (broker sharing) |

---

## 💼 Componenti Asset (`lib/components/assets/`)

12 componenti specifici per asset management (5587 righe totali):

| Componente | Uso |
|-----------|-----|
| `AssetCard` | Card con mini-chart, badge tipo, prezzo, Δ% |
| `AssetIcon` | Icona asset con fallback chain (pattern BrokerIcon) |
| `AssetModal` | Create/Edit modale con SearchAutocomplete e provider auto-assign (1325 righe) |
| `AssetSearchAutocomplete` | Ricerca multi-provider in parallelo con auto-fill |
| `AssetTable` | DataTable wrapper con colonne Δ multi-periodo |
| `AssetPriceSummary` | Riepilogo prezzo + variazioni |
| `AssetSyncModal` | Modale sync/refresh prezzi (pattern SyncModalBase) |
| `ProviderAssignmentSection` | Gestione provider assignments con form dinamico da `params_schema` |
| `ProviderComparisonModal` | Confronto dati provider vs DB |
| `ScheduledInvestmentEditor` | Editor complesso per piano investimento schedulato (1412 righe) |
| `BoundaryDateModal` | Modale per selezione date start/end |
| `CellDateRange` | Cella tabella con range date colorato |

---

## 📈 Signal Library (`lib/charts/signals/`)

Segnali calcolati iterativamente in O(N) nel frontend:

| Segnale | Tipo | Asse |
|---------|------|------|
| `EmaSignal` | Tecnico (IIR 1° ordine) | Primario |
| `RsiSignal` | Tecnico | Secondario (0-100) |
| `MacdSignal` | Tecnico (3 sotto-segnali) | Terziario |
| `BollingerSignal` | Tecnico (confidence band) | Primario |
| `FxPairSignal` | Data Comparison | Primario |
| `AssetComparisonSignal` | Data Comparison (sovrappone altro asset) | Primario |
| `MeasureSignal` | Misura punto-punto (Δabs, Δ%, giorni) | Primario |
| `LinearSignal` | Benchmark sintetico | Primario |
| `CompoundSignal` | Benchmark sintetico | Primario |
| `SineSignal` | Test/Demo | Primario |

Base class: `ChartSignal.ts` con `render()`, `getDefaultStyle()`, `getAxisId()`.
Registry: `registry.ts` con registrazione automatica dei segnali disponibili.

---

## 🌐 i18n

- **Libreria**: svelte-i18n
- **Lingue**: EN, IT, FR, ES (840+ chiavi per lingua)
- **File**: `lib/i18n/{en,it,fr,es}.json`
- **CLI**: `./dev.py i18n audit|add|remove|update|search|tree`
- **Bandiere**: emoji con web font `Noto Color Emoji` (per compatibilità Windows)

---

## 🏪 Stores

| Store | File | Pattern | Uso |
|-------|------|---------|-----|
| `TimeSeriesStore<T>` | `TimeSeriesStore.ts` | Class (generic) | Cache client-side per time-series con `Map<string,T>`, gap-detection per delta-fetching, merge idempotente, invalidation per-range o totale. Usato da FX e Asset charts. |
| `fxStoreRegistry` | `fxStoreRegistry.ts` | Registry | Mappa `pairKey → TimeSeriesStore<FxDataPoint>`. Una cache per coppia FX. |
| `EditBuffer<T>` | `EditBuffer.ts` | Class (generic) | Buffer bidirezionale per edit pendenti (click → CSV ↔ form). Bulk save al backend. Usato da FX e Asset edit mode. |
| `chartSettingsStore` | `chartSettingsStore.svelte.ts` | Svelte 5 runes (`$state`) | 2 livelli: global settings + per-pair overrides. Session-lifetime only (non persiste su refresh). |
| `themeStore` | `themeStore.ts` | Functions + localStorage | Single source of truth per dark/light/auto. Key: `librefolio-theme`. Exports: `applyTheme`, `getCurrentResolvedTheme`, `initThemeListener`. |
| `countryStore` | `countryStore.ts` | Writable store | Cache paesi dal backend |
| `sectorStore` | `sectorStore.ts` | Writable store | Cache settori dal backend |
| `currencyStore` | `currencyStore.ts` | Writable store | Cache valute |
| `currencyGraphStore` | `currencyGraphStore.ts` | Writable store | Grafo conversioni valuta per triangolazione |
| `fxCardInversionStore` | `fxCardInversionStore.ts` | Writable store | Inversione visuale coppie FX nelle card |
| `navigationStore` | `navigationStore.ts` | Writable store | Navigazione con history back (breadcrumb) |
| `toastStore` | `toastStore.svelte.ts` | Svelte 5 runes (`$state`) | Notifiche toast con auto-dismiss |
| `auth` | `auth.ts` | Writable store | JWT token + user info |
| `settings` | `settings.ts` | Writable store | User settings |
| `language` | `language.ts` | Writable store | Lingua selezionata |
| `globalSettings` | `globalSettings.ts` | Writable store | Impostazioni globali admin |

**Pattern key**:
- `.svelte.ts` → Svelte 5 runes (`$state`, `$derived`)
- `.ts` → Svelte 4 writable stores or plain TS classes
- Stores generici (`TimeSeriesStore`, `EditBuffer`) sono classi istanziabili, non singleton

---

## 📊 Componenti Chart (ECharts) — Dettaglio

Libreria modulare in `lib/components/charts/` (14 file, ~5100 righe):

| Componente | Righe | Ruolo | Note |
|-----------|-------|-------|------|
| `PriceChartFull` | 967 | Chart completo per detail page (FX e Assets) | Single ECharts instance, 1 grid + inside dataZoom, signal overlays, measure, edit mode |
| `ChartSignalsSection` | 734 | Gestione segnali overlay | 3 dropdown categorizzati (Indicators/Comparison/Benchmarks), OrderableList, style popovers |
| `LineChart` | 714 | Line chart core multi-asse Y | visualMap (rosso/verde), stale gradient, area fill, segment coloring |
| `MeasurePanel` | 569 | Overlay misurazione punto-punto | 2-click placement, Δabs/Δ%/giorni, tabella riassuntiva |
| `lineChartHelpers` | 515 | Helper functions per LineChart | Logica rendering estratta per tenere il componente pulito |
| `ChartSettingsModal` | 354 | Modal estetica + segnali | Wrapper di ChartAestheticsSection + ChartSignalsSection |
| `SemiDonutChart` | 310 | Half-donut per ownership | Distribuzione broker in semicerchio con avatar labels |
| `GeographyMap` | 238 | Choropleth world map | Paesi colorati per peso, ISO Alpha-3 codes |
| `SectorPieChart` | 190 | Pie chart settori | i18n labels, dark mode, responsive |
| `ChartAestheticsSection` | 185 | Controlli estetica estratti | 4 toggle + Y-axis mode selector |
| `SignalStyleEditor` | 172 | Editor stile linea segnale | Color picker, line width, dash style |
| `ChartToolbar` | 77 | Toolbar tipo chart + view mode | |
| `PriceChartCompact` | 58 | Mini-chart per card | No toolbar/zoom/edit, mini Y-axis |
| `index.ts` | 26 | Barrel export | |

---

## 💼 Componenti Asset (`lib/components/assets/`) — Dettaglio

15 componenti per asset management (~6317 righe totali):

| Componente | Righe | Ruolo | Note |
|-----------|-------|-------|------|
| `ScheduledInvestmentEditor` | 1412 | Editor piano investimento schedulato | Componente più complesso, form multi-step |
| `AssetModal` | 1328 | Create/Edit modale | SearchAutocomplete + provider auto-assign |
| `ProviderAssignmentSection` | 724 | Gestione provider assignments | Form dinamico generato da `params_schema` del backend |
| `AssetDataEditorSection` | 493 | Editor dati prezzo/eventi | Integra EditBuffer per inline editing |
| `AssetSearchAutocomplete` | 399 | Ricerca multi-provider parallela | Auto-fill campi da risultati provider |
| `ProviderComparisonModal` | 323 | Confronto dati provider vs DB | Diff visuale con highlight differenze |
| `AssetCard` | 287 | Card con mini-chart | Badge tipo, prezzo, Δ% multi-periodo |
| `AssetTable` | 265 | DataTable wrapper | Colonne Δ multi-periodo, sorting, filtering |
| `BoundaryDateModal` | 261 | Selezione date start/end | |
| `CellDateRange` | 236 | Cella tabella con range date | Colorazione per stato (attivo/scaduto/futuro) |
| `AssetSyncModal` | 162 | Sync/refresh prezzi | Pattern SyncModalBase |
| `AssetPriceSummary` | 152 | Riepilogo prezzo + variazioni | |
| `EventDataImportModal` | 98 | Import eventi da CSV | |
| `PriceDataImportModal` | 98 | Import prezzi da CSV | |
| `AssetIcon` | 79 | Icona asset | Fallback chain (pattern BrokerIcon) |

---

## 📍 Dove Trovare Cosa

| Cosa cerchi? | Dove guardare |
|--------------|---------------|
| Pagine frontend | `frontend/src/routes/(app)/` |
| Componenti UI base | `frontend/src/lib/components/ui/` |
| Componenti Select | `frontend/src/lib/components/ui/select/` (9 componenti: SearchSelect, SimpleSelect, CurrencySearchSelect, FxProviderSelect, BrokerSearchSelect, CountrySearchSelect, SectorSearchSelect, ImportPluginSelect, BaseDropdown) |
| Data Editor | `frontend/src/lib/components/ui/data-editor/` (DataEditor, DataImportModal) |
| Componenti Chart | `frontend/src/lib/components/charts/` |
| Signal Library | `frontend/src/lib/charts/signals/` (10 segnali + registry) |
| Componenti Asset | `frontend/src/lib/components/assets/` (12 componenti) |
| Componenti FX | `frontend/src/lib/components/fx/` (7 componenti) |
| Stores | `frontend/src/lib/stores/` (14+ store) |
| Utilities | `frontend/src/lib/utils/` (assetTypes, providerHelpers, syncHelpers, responsiveLayout, icons, colors, …) |
| E2E Tests | `frontend/e2e/` (181+ test) |
| API Client (Zodios) | `frontend/src/lib/api/` |
| Traduzioni | `frontend/src/lib/i18n/{en,it,fr,es}.json` (840+ chiavi) |

