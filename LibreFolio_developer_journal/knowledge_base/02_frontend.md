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

| Store | Uso |
|-------|-----|
| `TimeSeriesStore<T>` | Cache client-side generica con gap-detection e merge |
| `fxStoreRegistry` | Registry cache per coppie FX |
| `EditBuffer` | Buffer edit con dirty tracking |
| `chartSettingsStore` | Configurazione estetica chart (`.svelte.ts` per runes) |
| `countryStore` | Cache paesi dal backend |
| `sectorStore` | Cache settori dal backend |
| `currencyStore` | Cache valute |
| `currencyGraphStore` | Grafo conversioni valuta |
| `fxCardInversionStore` | Inversione visuale coppie FX |
| `navigationStore` | Navigazione con history back |
| `toastStore` | Notifiche toast (`.svelte.ts` per runes) |
| `auth`, `settings`, `language`, `globalSettings` | Stato globale app |

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

