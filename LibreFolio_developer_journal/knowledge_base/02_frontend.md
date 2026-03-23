# LibreFolio — Frontend Reference

## 📁 Struttura

```text
frontend/
├── src/
│   ├── routes/(app)/          # Pagine protette da auth
│   │   ├── dashboard/         # Dashboard (placeholder)
│   │   ├── brokers/           # Lista + [id] dettaglio
│   │   ├── fx/                # Lista + [pair] dettaglio (Phase 5)
│   │   ├── assets/            # Placeholder (Phase 6)
│   │   ├── transactions/      # Placeholder (Phase 7)
│   │   ├── files/             # File management
│   │   └── settings/          # User & global settings
│   ├── lib/
│   │   ├── charts/signals/    # Signal Library (EMA, MACD, RSI, Bollinger, etc.)
│   │   ├── components/        # Componenti riutilizzabili
│   │   │   ├── ui/            # Base (select/, input/, media/, modals, banners)
│   │   │   ├── charts/        # ECharts (LineChart, Candlestick, ChartSettings, etc.)
│   │   │   ├── fx/            # FX-specific (FxCard, FxPairAddModal, etc.)
│   │   │   ├── layout/        # Header, Sidebar, Footer, LanguageSelector
│   │   │   ├── settings/      # Settings tabs
│   │   │   ├── brokers/       # Broker-specific
│   │   │   ├── auth/          # Login, Register, ForgotPassword
│   │   │   ├── files/         # FilesTable
│   │   │   └── table/         # DataTable generico
│   │   ├── stores/            # Svelte stores (TimeSeriesStore, EditBuffer, auth, etc.)
│   │   ├── api/               # Zodios client + OpenAPI types
│   │   └── i18n/              # Traduzioni (EN, IT, FR, ES) — 620+ chiavi
│   └── app.css                # Design system (Tailwind v4 via @theme)
├── e2e/                       # Playwright E2E tests (67+)
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
| `PriceChartFull` | Chart completo (detail page) |
| `PriceChartCompact` | Mini-chart (card) |
| `SemiDonutChart` | Semicerchio (broker sharing) |

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
| `LinearSignal` | Benchmark sintetico | Primario |
| `CompoundSignal` | Benchmark sintetico | Primario |
| `SineSignal` | Test/Demo | Primario |

Base class: `ChartSignal.ts` con `render()`, `getDefaultStyle()`, `getAxisId()`.

---

## 🌐 i18n

- **Libreria**: svelte-i18n
- **Lingue**: EN, IT, FR, ES (620+ chiavi per lingua)
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
| `auth`, `settings`, `language`, `globalSettings` | Stato globale app |

---

## 📍 Dove Trovare Cosa

| Cosa cerchi? | Dove guardare |
|--------------|---------------|
| Pagine frontend | `frontend/src/routes/(app)/` |
| Componenti UI base | `frontend/src/lib/components/ui/` |
| Componenti Select | `frontend/src/lib/components/ui/select/` |
| Componenti Chart | `frontend/src/lib/components/charts/` |
| Signal Library | `frontend/src/lib/charts/signals/` |
| Componenti FX | `frontend/src/lib/components/fx/` |
| Stores | `frontend/src/lib/stores/` |
| E2E Tests | `frontend/e2e/` |
| API Client (Zodios) | `frontend/src/lib/api/` |
| Traduzioni | `frontend/src/lib/i18n/{en,it,fr,es}.json` |

