# Plan: Phase 06 — Asset Management (Grafico & Analisi Tecnica)

**Data creazione**: 23 Marzo 2026  
**Ultimo aggiornamento**: 16 Aprile 2026  
**Status**: ✅ COMPLETATA (Step 1–4 ✅, Part C ✅, Step 6 ✅)  
**Durata stimata**: ~8 giorni  
**Dipendenze**: Phase 5 (PriceChartFull, Signal Library, DataEditor), Phase 4 (DataTable, ModalBase, component library), Phase 4.8 (user_role)

**Piani collegati:**
- [plan-phase06Step4AssetDetailPage.prompt.md](plan-phase06Step4AssetDetailPage.prompt.md) — Step 4 detail page
- [plan-phase06Step6-Polish-Test-Docs.prompt.md](phases/phase-06-subplan/Bugfix-Step6/plan-phase06Step6-Polish-Test-Docs.prompt.md) — Step 6: i18n, test, docs, coverage (✅ completato)
- [plan-partCCurrencyConversion.prompt.md](phases/phase-06-subplan/Bugfix-Step4/PlanC/plan-partCCurrencyConversion.prompt.md) — Part C: Currency conversion (✅ completata)
- [plan-partC_1_PostValidation.prompt.md](phases/phase-06-subplan/Bugfix-Step4/PlanC/plan-partC_1_PostValidation.prompt.md) — Part C.1: Post-validation fixes (✅ completata)
- [plan-partC_2–7](phases/phase-06-subplan/Bugfix-Step4/PlanC/) — Part C.2–C.7: Review, UX polish, test fixes, provider core cache (✅ completate)

---

## 1. Obiettivo

Implementare il sistema grafico per gli asset finanziari: lista con doppia visualizzazione (card grid + tabella), CRUD con smart search multi-provider e auto-fill, pagina dettaglio con `PriceChartFull` + segnali tecnici (EMA, MACD, RSI, Bollinger), import CSV prezzi OHLCV, e `AssetMatchingWizard` condiviso con Phase 7.

**Escluso da questa fase**: gain/loss, transazioni, regimi fiscali — arriveranno in Phase 7/8.

---

## 2. Contesto Tecnico

### 2.1 Backend — Stato Attuale (quasi completo)

Le API per gli asset sono già implementate e testate:

| Endpoint | Metodo | Stato | Descrizione |
|----------|--------|-------|-------------|
| `POST /api/v1/assets` | POST | ✅ | Bulk create assets |
| `PATCH /api/v1/assets` | PATCH | ✅ | Bulk update assets |
| `GET /api/v1/assets` | GET | ✅ | Bulk read by IDs (con metadata) |
| `GET /api/v1/assets/all` | GET | ✅ | All active assets |
| `GET /api/v1/assets/query` | GET | ✅ | Lista con filtri (search, type, currency, active, identifier_contains) |
| `DELETE /api/v1/assets` | DELETE | ✅ | Bulk delete (cascade provider+prices, blocca se ha transactions) |
| `GET /api/v1/assets/provider` | GET | ⚠️ | Lista providers — **DA ESTENDERE** (params_schema + filtro + fix perf) |
| `GET /api/v1/assets/provider/search` | GET | ✅ | Smart search multi-provider in parallelo |
| `POST /api/v1/assets/provider` | POST | ✅ | Bulk assign providers |
| `DELETE /api/v1/assets/provider` | DELETE | ✅ | Bulk remove providers |
| `GET /api/v1/assets/provider/assignments` | GET | ✅ | Read provider assignments |
| ~~`GET /api/v1/assets/prices/{id}`~~ | ~~GET~~ | ❌ | ~~Price history con backward-fill~~ — **ELIMINATO in Step 2b** (delegava ai provider ad ogni lettura, disallineato con FX) |
| `POST /api/v1/assets/prices/query` | POST | ✅ | **NUOVO in Step 2b** — Bulk price query (DB-only, singola query SQL, backward-fill) — analogo a `POST /fx/currencies/convert` |
| `POST /api/v1/assets/prices` | POST | ✅ | Bulk upsert prices |
| `DELETE /api/v1/assets/prices` | DELETE | ✅ | Bulk delete price ranges |
| `POST /api/v1/assets/prices/sync` | POST | ✅ | Bulk refresh prices da provider |
| `POST /api/v1/assets/provider/refresh` | POST | ✅ | Refresh metadata da provider |

**Test E2E di riferimento**: `backend/test_scripts/test_e2e/test_search_to_prices.py` — dimostra il flusso
completo Search → Create → Assign Provider → Refresh Metadata → Refresh Prices, sia per JustETF (ISIN)
che per YFinance (TICKER).

### 2.2 Provider — Struttura `provider_params`

| Provider | `identifier` | `identifier_type` | `provider_params` | `supports_search` |
|----------|-------------|-------------------|-------------------|-------------------|
| `yfinance` | ticker (es. "AAPL") | TICKER | `None` (nessun param) | ✅ |
| `justetf` | ISIN (es. "IE00B4L5Y983") | ISIN | `None` (nessun param) | ✅ |
| `cssscraper` | URL pagina web | OTHER | `{current_css_selector, currency, decimal_format?}` | ❌ |
| `scheduled_investment` | asset_id | custom | `FAScheduledInvestmentSchedule` (complesso) | ❌ |
| `mockprov` | qualsiasi | UUID | `None` | ✅ (test only) |

**Problema**: il frontend non sa quali campi servono per `provider_params` di ciascun provider.
**Soluzione**: aggiungere `params_schema` al plugin base (Step 1a).

### 2.3 Frontend — Stato Attuale

- `src/routes/(app)/assets/+page.svelte` → **placeholder 29 righe** (titolo + "Coming Soon")
- `src/routes/(app)/assets/[id]/` → **non esiste**
- `src/lib/components/assets/` → **non esiste**
- Nessun store, nessun componente asset

### 2.4 Componenti Riutilizzabili (già esistenti)

| Componente | Path | Usato per |
|-----------|------|-----------|
| `DataTable` | `$lib/components/table/DataTable.svelte` | Tabella con sorting, filtri, paginazione |
| `ModalBase` | `$lib/components/ui/ModalBase.svelte` | Wrapper modale universale |
| `ConfirmModal` | `$lib/components/ui/ConfirmModal.svelte` | Conferma azioni distruttive |
| `SearchSelect` | `$lib/components/ui/select/SearchSelect.svelte` | Dropdown ricercabile |
| `SimpleSelect` | `$lib/components/ui/select/SimpleSelect.svelte` | Dropdown semplice |
| `CurrencySearchSelect` | `$lib/components/ui/select/CurrencySearchSelect.svelte` | Selezione valuta con flag |
| `ImagePickerWrapper` | `$lib/components/ui/media/ImagePickerWrapper.svelte` | Selezione icona |
| `LazyImage` | `$lib/components/ui/media/LazyImage.svelte` | Immagine con lazy loading |
| `DateRangePicker` | `$lib/components/ui/DateRangePicker.svelte` | Selettore range date con preset |
| `PriceChartFull` | `$lib/components/charts/PriceChartFull.svelte` | Chart completo ECharts (line, signals, edit, measure) |
| `PriceChartCompact` | `$lib/components/charts/PriceChartCompact.svelte` | Mini chart per card |
| `ChartAestheticsSection` | `$lib/components/charts/ChartAestheticsSection.svelte` | Pannello estetica chart |
| `ChartSignalsSection` | `$lib/components/charts/ChartSignalsSection.svelte` | Pannello segnali tecnici |
| `MeasurePanel` | `$lib/components/charts/MeasurePanel.svelte` | Pannello misura abs+% |
| `DataEditor` | `$lib/components/ui/data-editor/DataEditor.svelte` | Editor tabellare con status tracking |
| `DataImportModal` | `$lib/components/ui/data-editor/DataImportModal.svelte` | Import CSV |
| `FxCard` | `$lib/components/fx/FxCard.svelte` | Card con mini chart (pattern di riferimento) |
| `FxDataEditorSection` | `$lib/components/fx/FxDataEditorSection.svelte` | Wrapper DataEditor per FX (pattern) |
| `urlFilters.ts` | `$lib/utils/urlFilters.ts` | Sync filtri ↔ URL query params |

### 2.5 Pagine di Riferimento

| Pagina | File | Pattern da riusare |
|--------|------|--------------------|
| FX List | `src/routes/(app)/fx/+page.svelte` (733 righe) | Card grid, filtri, DateRangePicker, modali |
| FX Detail | `src/routes/(app)/fx/[pair]/+page.svelte` (936 righe) | PriceChartFull, signals, DataEditor, provider config |
| Files | `src/routes/(app)/files/+page.svelte` (1425 righe) | Grid/List toggle, `LayoutGrid`/`List` icons, localStorage persist |

---

## 3. Step di Implementazione

### Step 1 — Backend: `GET /assets/provider` evoluto + fix performance (~0.5 giorni)

#### 1a) `params_schema` nel plugin base

**File**: `backend/app/services/asset_source.py`

Aggiungere una proprietà `params_schema` alla classe base `AssetSourceProvider` con default lista vuota:

```python
@property
def params_schema(self) -> list[dict]:
    """
    Schema dei campi richiesti da provider_params per questo provider.
    Il frontend usa questo per generare form dinamici.
    Default: lista vuota (nessun parametro richiesto).
    
    Returns:
        Lista di dict con chiavi: key, type, required, description, options, default
    """
    return []
```

Override nei provider che necessitano parametri:

**File**: `backend/app/services/asset_source_providers/css_scraper.py`
```python
@property
def params_schema(self) -> list[dict]:
    return [
        {"key": "current_css_selector", "type": "string", "required": True,
         "description": "CSS selector for the price element on the web page"},
        {"key": "currency", "type": "string", "required": True,
         "description": "Currency code (ISO 4217, e.g. EUR, USD)"},
        {"key": "decimal_format", "type": "select", "required": False,
         "options": ["us", "eu"], "default": "us",
         "description": "Number format: 'us' = 1,234.56 / 'eu' = 1.234,56"},
        {"key": "timeout", "type": "number", "required": False, "default": 30,
         "description": "HTTP request timeout in seconds"},
        {"key": "user_agent", "type": "string", "required": False,
         "default": "LibreFolio/1.0", "description": "Custom User-Agent header"},
    ]
```

**File**: `backend/app/services/asset_source_providers/scheduled_investment.py`
Override con lo schema del `FAScheduledInvestmentSchedule`.

`yfinance`, `justetf`, `mockprov`: ereditano il default (lista vuota).

#### 1b) Schema Pydantic + endpoint evoluto

**File**: `backend/app/schemas/provider.py`

Nuovo schema:
```python
class FAProviderParamField(BaseModel):
    """Single field definition for provider_params form."""
    model_config = ConfigDict(extra="forbid")
    key: str = Field(..., description="Parameter key name")
    type: str = Field(..., description="Field type: 'string', 'number', 'select'")
    required: bool = Field(..., description="Whether this field is required")
    description: str = Field("", description="Human-readable description")
    options: Optional[List[str]] = Field(None, description="Options for 'select' type")
    default: Optional[Any] = Field(None, description="Default value")
```

Estendere `FAProviderInfo`:
```python
class FAProviderInfo(BaseModel):
    # ...existing fields...
    params_schema: List[FAProviderParamField] = Field(
        default_factory=list,
        description="Form field definitions for provider_params"
    )
```

**File**: `backend/app/api/v1/assets.py`

Aggiungere parametro di filtro (come FX list_providers):
```python
@provider_router.get("", response_model=List[FAProviderInfo])
async def list_providers(
    providers: Optional[List[str]] = Query(
        None, description="Optional list of provider codes to filter"
    ),
    _current_user: User = Depends(get_current_user),
):
```

#### 1c) Fix performance `supports_search`

**File**: `backend/app/api/v1/assets.py` (righe 318-336)

**Problema**: `await instance.search("")` esegue HTTP reali a justetf.com e inizializza le cache.

**Soluzione**: sostituire con check locale:
```python
# PRIMA (lento — HTTP call reale):
supports_search = True
try:
    await instance.search("")
except Exception as e:
    if "NOT_SUPPORTED" in str(e):
        supports_search = False

# DOPO (istantaneo — property check locale):
supports_search = instance.test_search_query is not None
```

`test_search_query` è già implementato in ogni provider:
- `yfinance` → `"Apple"` (search supportata)
- `justetf` → `"MSCI World"` (search supportata)
- `cssscraper` → `None` (search non supportata)
- `scheduled_investment` → ha `supports_search = False` (property dedicata)
- `mockprov` → `"TEST"` (search supportata)

#### 1d) Pre-warm asincrono delle cache

**File**: `backend/app/main.py`

Nella funzione `lifespan`, dopo `_initialize_global_settings()`, lanciare un task asincrono:

```python
# Pre-warm provider caches in background (non-blocking)
import asyncio
asyncio.create_task(_prewarm_provider_caches())
```

```python
async def _prewarm_provider_caches():
    """Pre-warm provider instances and their caches in background."""
    try:
        from backend.app.services.provider_registry import AssetProviderRegistry
        for provider_info in AssetProviderRegistry.list_providers():
            code = provider_info["code"]
            AssetProviderRegistry.get_provider_instance(code)
        logger.info("Provider caches pre-warmed successfully")
    except Exception as e:
        logger.warning(f"Provider cache pre-warm failed (non-blocking): {e}")
```

#### 1e) Rigenerazione client

```bash
./dev.py api sync
```

#### Tasks

- [ ] Aggiungere `params_schema` property a `AssetSourceProvider` (default: `[]`)
- [ ] Override `params_schema` in `CSSScraperProvider`
- [ ] Override `params_schema` in `ScheduledInvestmentProvider`
- [ ] Aggiungere `FAProviderParamField` a `provider.py`
- [ ] Estendere `FAProviderInfo` con `params_schema`
- [ ] Aggiungere `providers` query param a `list_providers`
- [ ] Sostituire `await instance.search("")` con `instance.test_search_query is not None`
- [ ] Aggiungere `_prewarm_provider_caches()` asincrono in `main.py` lifespan
- [ ] `./dev.py api sync` per rigenerare client Zodios
- [ ] Verificare test API esistenti passano

---

### Step 2 — Asset List Page: doppia visualizzazione Card + Tabella (~1 giorno)

Riscrivere `src/routes/(app)/assets/+page.svelte` (placeholder → pagina completa).
Creare `src/routes/(app)/assets/+page.ts` per load function.

**Ordine**: prima si costruiscono tutti i componenti per Assets (AssetCard, AssetTable, dual view),
poi si replica lo stesso pattern su FX (FxTable + toggle). Così il lavoro su Assets fa da "prototipo"
e il refactoring FX è una semplice applicazione dello stesso pattern.

La pagina offre **due modalità di visualizzazione** (come Files page), persistite in localStorage:

#### Card View (Grid)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Assets                                [⊞ Grid][☰ Table] [+ Add]  │
│  Manage your financial assets                                      │
├─────────────────────────────────────────────────────────────────────┤
│  🔍 Search...    │ Type [All ▾]  │ Currency [All ▾]  │ ☑ Active    │
│  📅 [3M ▾] date range picker                        │ abs/% toggle│
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ 🍎 Apple Inc.    │  │ 🌍 iShares MSCI  │  │ 📄 BTP 2030     │  │
│  │ STOCK · USD      │  │ ETF · EUR        │  │ BOND · EUR      │  │
│  │                  │  │                  │  │                  │  │
│  │ 198.42           │  │ 85.23            │  │ 100.39           │  │
│  │ ▲ +2.3%          │  │ ▼ -0.8%          │  │ ▲ +0.1%          │  │
│  │ ╱──╲_╱──         │  │ ──╲_╱──╲         │  │ ──────────       │  │
│  │                  │  │                  │  │                  │  │
│  │ ⚙ ⟳ ↻ │ ✏ 🗑   │  │ ⚙ ⟳ ↻ │ ✏ 🗑   │  │ ⚙ ⟳ ↻ │ ✏ 🗑   │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐                        │
│  │ 🪙 Bitcoin       │  │ 💰 Crowdfund X   │     (empty state      │
│  │ CRYPTO · USD     │  │ LOAN · EUR       │      se 0 asset)      │
│  │ ...              │  │ ...              │                        │
│  └──────────────────┘  └──────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
```

Ogni card (`AssetCard.svelte`) segue il pattern di `FxCard.svelte`:
- Header: icona + nome + tipo badge
- Info: ultimo prezzo + variazione abs/% + currency
- Mini chart (`PriceChartCompact`) con segnali opzionali
- Footer: azioni (settings, sync, refresh | edit, delete)
- Click sulla card → naviga a `/assets/[id]`

#### Table View (List)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  Assets                                         [⊞ Grid][☰ Table] [+ Add]      │
│  Manage your financial assets                                                    │
├──────────────────────────────────────────────────────────────────────────────────┤
│  🔍 Search...    │ Type [All ▾]  │ Currency [All ▾]  │ ☑ Active                 │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │ Icon │ Name          │ Type │ Ccy │ Last    │ Δ Abs   │ Δ %    │ Prov│Act │  │
│  ├──────┼───────────────┼──────┼─────┼─────────┼─────────┼────────┼─────┼────┤  │
│  │ 🍎   │ Apple Inc.    │ STK  │ USD │ 198.42  │ +21.75  │ +12.3% │ ✅  │ ✅ │  │
│  │ 🌍   │ iShares MSCI  │ ETF  │ EUR │  85.23  │  -0.69  │  -0.8% │ ✅  │ ✅ │  │
│  │ 📄   │ BTP 2030      │ BOND │ EUR │ 100.39  │  +0.10  │  +0.1% │ ✅  │ ✅ │  │
│  │ 🪙   │ Bitcoin       │ CRY  │ USD │ 67420   │ +3200   │  +5.0% │ ✅  │ ✅ │  │
│  │ 💰   │ Crowdfund X   │ LOAN │ EUR │ 10150   │ +150    │  +1.5% │ ✅  │ ✅ │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│  ← 1 2 3 →                                                                      │
└──────────────────────────────────────────────────────────────────────────────────┘
```

`DataTable` con sorting su tutte le colonne, paginazione, filtri colonna.

**Colonne andamento (Δ multi-periodo)**:
- Il frontend scarica **sempre l'intera serie** nel range selezionato via `POST /assets/prices/query`
  (singola query DB per tutti gli asset), poi calcola i Δ% multi-periodo lato client.
- Se il range selezionato è sufficientemente ampio, appaiono colonne aggiuntive:
  1W, 1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y — ciascuna calcolata come `(Pₙ - P_{n-periodo}) / P_{n-periodo} × 100`
  dove Pₙ è l'ultimo giorno del range (non necessariamente oggi).
- Colonne appaiono/scompaiono dinamicamente al cambiare del range nel DateRangePicker.
- Colorazione: verde (▲) se positivo, rosso (▼) se negativo, — se dato non disponibile.
- Dettagli implementativi nel piano di rientro Step 2b §7c.

**Configurazioni chart preservate**: quando si passa da grid a table, le ChartSettings (signals,
aesthetics) restano memorizzate nel `chartSettingsStore` — non vengono perse. Semplicemente non
vengono visualizzate nella modalità tabella. Tornando in grid, le card mostrano le stesse
impostazioni di prima.

#### Differenze Asset vs FX nelle card/tabella

| Feature | Assets | FX |
|---------|--------|----|
| **Swap button** (⇄ inversione) | ❌ Non presente (né grid né table) | ✅ Presente (sia grid che table) |
| **Icona** | `icon_url` custom → icona preset per `asset_type` → fallback generico | Flag emoji da currency codes |
| **Nome** | `display_name` | `BASE → QUOTE` (con flag) |
| **Andamento** | `Δ abs` + `Δ %` su close price | `Δ abs` + `Δ %` su rate |

#### View mode indipendente e persistenza per-utente

La selezione grid/table è **indipendente** tra Assets e FX:
- `localStorage` key: `lf_{userId}_assetsViewMode` e `lf_{userId}_fxViewMode`
- Default: `'grid'` per entrambe
- Persistenza: fino a clear della cache del browser
- **Scoped per utente**: la chiave include lo `userId` così utenti diversi sullo stesso
  browser hanno preferenze separate

**⚠️ VERIFICA/MIGRAZIONE localStorage per-utente**:
Tutti i localStorage usati attualmente **NON** sono scoped per utente:
- `filesPage_viewMode`, `filesPage_activeTab`, `filesPage_brokerFilter`
- `sidebar-collapsed`
- `librefolio-locale`, `librefolio-theme`
- `user_settings`, `global_settings`
- `DataTable` column visibility

**Task**: verificare quali di questi devono essere user-scoped (quelli che sono preferenze
personali, non del browser). Se servono migrazioni, creare una utility `getUserStorageKey(key)`
che prepone `lf_{userId}_` e migrare i valori esistenti al primo login.

#### Icone Asset — Fallback Chain

Analogo a `BrokerIcon.svelte` (che ha fallback: icon_url → portal favicon → plugin icon → Briefcase):

1. **`icon_url` custom** — URL inserito dall'utente o scelto via `ImagePickerWrapper`
2. **Icona preset per `asset_type`** — icone statiche già presenti tra gli static resources
   (documentate in MkDocs). Mapping: STOCK→📈, ETF→🌍, BOND→📄, CRYPTO→🪙, FUND→💰, ecc.
   Usare immagini SVG/PNG reali, non emoji (le emoji sono solo placeholder nel piano).
3. **Fallback generico** — icona Lucide `BarChart3` o simile

Componente: `AssetIcon.svelte` (pattern identico a `BrokerIcon.svelte`).
Il flusso di selezione icona in `AssetModal` usa `ImagePickerWrapper` con `preset="asset-icon"`,
identico a come `BrokerForm` usa `preset="broker-icon"`.

#### Aggiornamento FX List Page (stesso pattern)

Applicare lo **stesso toggle grid/table** anche alla pagina FX `/fx/+page.svelte`:
- **Grid**: mantiene le `FxCard` attuali (invariate)
- **Table**: nuova `FxTable.svelte` con `DataTable` — colonne: Flag Base→Quote, Rate, Variazione %, Provider(s), Status (Manual Only badge), Actions

Componenti condivisi:
- `ViewModeToggle.svelte` — micro-componente con 2 bottoni (LayoutGrid + List), persistenza localStorage, riusabile da Assets e FX

**Nota su `urlFilters.ts`**: esiste già in `$lib/utils/urlFilters.ts` (usato dalla pagina Files).
Sincronizza i filtri DataTable con i query params dell'URL del browser (deep-linking: bookmark/refresh
preserva i filtri). Per ora i filtri di Assets e FX usano `$state` locale (si perdono al refresh).
L'integrazione con `urlFilters.ts` è opzionale e può essere aggiunta in futuro come miglioramento.

#### Componenti da creare (Step 2)

| Componente | Path | Descrizione |
|-----------|------|-------------|
| `AssetIcon.svelte` | `$lib/components/assets/` | Icon con fallback chain (pattern BrokerIcon) |
| `AssetCard.svelte` | `$lib/components/assets/` | Card con mini chart (pattern FxCard, no swap) |
| `AssetTable.svelte` | `$lib/components/assets/` | DataTable wrapper per assets (con Δ Abs/%) |
| `ViewModeToggle.svelte` | `$lib/components/ui/` | Toggle grid/table riusabile |

#### Componenti da creare (replica su FX — dopo Assets)

| Componente | Path | Descrizione |
|-----------|------|-------------|
| `FxTable.svelte` | `$lib/components/fx/` | DataTable wrapper per FX pairs |

#### Tasks (Assets — fare per primi)

- [ ] Creare `ViewModeToggle.svelte` (riusabile, accetta storageKey prop)
- [ ] Creare `AssetIcon.svelte` (fallback chain: icon_url → preset per asset_type → fallback generico, pattern BrokerIcon)
- [ ] Creare `AssetCard.svelte` (pattern FxCard: header con AssetIcon, price+Δ, mini chart, footer actions, **NO swap button**)
- [ ] Creare `AssetTable.svelte` (DataTable: AssetIcon, name, type, currency, last price, Δ Abs, Δ %, provider, status, actions)
  - Colonne Δ Abs / Δ %: fetch smart (solo first+last price point dal backend), colorazione verde/rosso
- [ ] Riscrivere `assets/+page.svelte` con dual view + filtri + DateRangePicker per intervallo Δ
- [ ] Creare `assets/+page.ts` (load function)
- [ ] View mode Assets: `lf_{userId}_assetsViewMode`, default `'grid'`
- [ ] Empty state
- [ ] `user_role`: VIEWER non vede pulsanti edit/delete/add
- [ ] Verifica/migrazione localStorage per-utente (tutte le chiavi esistenti)
- [ ] i18n keys per nuovi label

#### Tasks (Replica su FX — dopo aver completato Assets)

- [ ] Creare `FxTable.svelte` (DataTable per FX pairs)
  - Colonne: Swap ⇄, Pair (flag+code BASE→QUOTE), Rate, Δ Abs, Δ %, Provider(s), Manual-Only badge, Actions
  - Swap button inline per riga (inversione pair come in FxCard)
  - Δ Abs / Δ % calcolati da primo e ultimo rate nell'intervallo date (come Assets)
- [ ] Aggiornare `fx/+page.svelte` con toggle grid/table usando `ViewModeToggle`
- [ ] View mode FX indipendente da Assets: `lf_{userId}_fxViewMode`, default `'grid'`

---

### Step 2b — Bugfix, Migrazione e UX Refinement (Piano di Rientro)

> **⚠️ Piano di rientro obbligatorio** — da completare **prima** di procedere con Step 3.
>
> Dopo il completamento degli Step 1+2, la review ha evidenziato bug bloccanti, debiti tecnici
> e miglioramenti UX. Il piano di rientro è documentato in:
>
> **[`plan-phase06BugfixMigration.prompt.md`](plan-phase06BugfixMigration.prompt.md)**
>
> Contiene 9 sotto-step: fix crash `.toFixed()`, migrazione BrokerIcon Svelte 5, migrazione
> localStorage user-scoped, fix FX delete 422, fix FX detail manual-only UX, ViewModeToggle
> nell'header, endpoint bulk asset prices + colonne Δ multi-periodo + migrazione test,
> fix test upload 401, pulizia i18n.
>
> **Durata stimata**: ~0.5 giorni

---

### Step 2c — Modali Sync-All e Multi-Delete per Asset (~0.5 giorni)

> **Miglioramento UX** — allinea l'esperienza asset a quella già implementata in FX.

#### Modale Sync-All Asset (pattern FxSyncModal)

Come la modale FX "Sync All", creare `AssetSyncModal.svelte`:
- Mostra lista degli asset con provider assegnato
- Progress bar per ogni asset durante il sync
- Risultato per riga: fetched↓ / changed Δ / errore
- Summary finale: totale sincronizzati, errori, tempo
- Bottone "Sync All" nella 2×2 grid apre la modale invece di eseguire direttamente

#### Modale Multi-Delete Asset (pattern ConfirmModal con lista)

Migliorare `handleBulkDeleteAssets`:
- Mostrare `ConfirmModal` con lista nomi asset da eliminare
- Warning se alcuni asset hanno transazioni (blocco backend)
- Risultato: conteggio eliminati / falliti con dettaglio errori

#### Tasks

- [ ] Creare `AssetSyncModal.svelte` (riusa pattern `FxSyncModal`)
- [ ] Creare `AssetBulkDeleteModal.svelte` (o usare `ConfirmModal` con lista items)
- [ ] Collegare "Sync All" (2×2) alla modale invece di `handleSyncAllAssets()`
- [ ] Collegare bulk delete (DataTableToolbar) alla modale di conferma con lista
- [ ] i18n keys per modale sync e delete

---

### Step 3 — `AssetModal` + `AssetSearchAutocomplete` + Provider Probe (~2.5 giorni)

> **📋 Piano dettagliato**: [`plan-phase06Step3AssetModal.prompt.md`](phases/phase-06-subplan/plan-phase06Step3AssetModal.prompt.md)
>
> Il piano dettagliato contiene 10 sotto-step con ASCII art complete, schema code, dependency graph,
> e note implementative. Questo file riporta solo la sintesi.

#### Obiettivi

1. **AssetModal.svelte** — modale Create/Edit con search online, form asset, identifiers, provider assignment
2. **AssetSearchAutocomplete.svelte** — ricerca debounced multi-provider con dropdown risultati e `provider_url`
3. **ProviderAssignmentSection.svelte** — sezione provider riusabile (modal + futuro detail page) con form dinamico da `params_schema`, test configuration, user/provider URL
4. **`POST /assets/provider/probe`** — endpoint bulk modulare (operazioni selezionabili: `current_price`, `history`, `metadata`) con `execution_time_ms` per operazione, nessuna persistenza DB
5. **Schema inheritance** — `FAProviderConfigBase` come base minimale, esteso da `FAProviderAssignmentItem` (+ `asset_id`, `fetch_interval`, `user_url`) e `FAProviderProbeRequest` (+ `operations`). Le funzioni service accettano il base, i figli passano senza travasi
6. **`user_url`** — nuovo campo persistito su `AssetProviderAssignment` (modifica `001_initial.py`, no migrazione Alembic)
7. **`provider_url`** — calcolato dal backend via `get_asset_url()` nei provider (yfinance, justetf, cssscraper). Esposto sia in `FAProviderSearchResultItem` che in `FAProviderAssignmentReadItem`
8. **`fetch_asset_metadata` potenziato** — yfinance estrae `identifier_ticker` + `identifier_isin`. JustETF best-effort con ISIN + ticker dal DataFrame
9. **Workflow auto-test** — dopo selezione search result → auto-trigger probe `["current_price", "history"]` con feedback ⏳→✅/❌ + timing
10. **Pulsante "Ask Provider"** — nella sezione identifiers, chiama probe `["metadata"]`, compila campi vuoti (✔️), segnala conflitti con pre-esistenti (⚠️)
11. **Confirmation modals** — save without test (ConfirmModal warning), change identifier in edit mode (ConfirmModal warning)
12. **E3**: Toggle Abs/% per AssetCard con suffisso valuta in Abs mode

#### Componenti Backend (nuovi/modificati)

| File | Modifica |
|------|----------|
| `schemas/provider.py` | `FAProviderConfigBase`, `FAProviderProbeRequest`, `ProbeOperation`, response schemas |
| `db/models.py` | `AssetProviderAssignment.user_url` |
| `alembic/001_initial.py` | colonna `user_url` |
| `services/asset_source.py` | `get_asset_url()`, `probe_provider_config()` |
| `asset_source_providers/yahoo_finance.py` | `get_asset_url()`, `fetch_asset_metadata` con identifiers |
| `asset_source_providers/justetf.py` | `get_asset_url()`, `fetch_asset_metadata` (nuovo) |
| `asset_source_providers/css_scraper.py` | `get_asset_url()` |
| `api/v1/assets.py` | `POST /assets/provider/probe`, `provider_url` nelle risposte |

#### Componenti Frontend (nuovi)

| Componente | Descrizione |
|-----------|-------------|
| `AssetSearchAutocomplete.svelte` | Ricerca debounced, provider checkboxes, dropdown con `provider_url` |
| `ProviderAssignmentSection.svelte` | Form dinamico provider, test config con timing, user/provider URL |
| `AssetModal.svelte` | Modale completa Create/Edit con auto-fill, auto-test, ask-provider, confirm modals |

#### Task riassuntivi

- [ ] Backend: schema inheritance `FAProviderConfigBase` → figli
- [ ] Backend: `user_url` su model + DB + schemi + populate
- [ ] Backend: `get_asset_url()` in 3 provider + `provider_url` in search/read
- [ ] Backend: `fetch_asset_metadata` potenziato (yfinance identifiers, justetf best-effort)
- [ ] Backend: `POST /assets/provider/probe` con 3 operazioni + `execution_time_ms`
- [ ] Backend: test probe + user_url + API sync
- [ ] Frontend: `AssetSearchAutocomplete.svelte`
- [ ] Frontend: `ProviderAssignmentSection.svelte` (riusabile)
- [ ] Frontend: `AssetModal.svelte` (create + edit + auto-test + ask-provider + confirm modals)
- [ ] Frontend: E3 toggle Abs/% su AssetCard
- [ ] Frontend: i18n ~40 chiavi (EN/IT/FR/ES)
- [ ] Frontend: integrazione modale nella pagina lista

---

### Step 4 — Asset Detail Page con PriceChartFull + Analisi Tecnica + Currency Conversion (~2.5 giorni)

Creare `src/routes/(app)/assets/[id]/+page.svelte` e `+page.ts`.
Creare `src/lib/components/assets/AssetDataEditorSection.svelte`.

Architettura identica a `/fx/[pair]/+page.svelte` (936 righe).

#### Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  ← Back to Assets                                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ── HEADER ─────────────────────────────────────────────────────    │
│  🍎 Apple Inc.                                      [✏ Edit]       │
│  STOCK · 🇺🇸 USD · AAPL                     [↻ Refresh] [⟳ Sync]  │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ── FILTER BAR ─────────────────────────────────────────────────   │
│  📅 [2025-09-23] → [2026-03-23]    │  Last: 198.42 USD             │
│  [1W] [1M] [3M] [6M] [1Y] [ALL]   │  ▲ +12.3% (+21.75)            │
│                                     │  abs/% toggle                 │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ── CHART ──────────────────────────────────────────────────────    │
│  [Line ▾] [Abs/% ▾]                      [✏ Edit] [📐 Measure]    │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 200 ┤                                          ╱──╲          │  │
│  │     │                               ╱─────────╱    ╲─── EMA  │  │
│  │ 180 ┤                     ╱────────╱                         │  │
│  │     │           ╱────────╱                                   │  │
│  │ 160 ┤ ─────────╱                                             │  │
│  │     │╱                                                       │  │
│  │ 140 ┤                                                        │  │
│  │     ├────────┬────────┬────────┬────────┬────────┬───────────│  │
│  │       Sep      Oct      Nov      Dec      Jan      Feb       │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ▸ Chart Aesthetics (foldable)                                      │
│  ▸ Technical Signals (EMA, MACD, RSI, Bollinger) (foldable)         │
│  ▸ Measure Panel (abs+% come FX) (foldable)                        │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ── DATA EDITOR (toggle visibility) ────────────────────────────   │
│  [+ Add Row]  [📥 Import CSV]  [🗑 Delete Selected]  [💾 Save]     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ Status │ Date       │ Open   │ High   │ Low    │ Close │ Vol │  │
│  ├────────┼────────────┼────────┼────────┼────────┼───────┼─────┤  │
│  │   ●    │ 2026-03-21 │ 197.50 │ 199.10 │ 196.80 │198.42 │ 12M│  │
│  │   ✎    │ 2026-03-20 │ 195.00 │ 198.00 │ 194.50 │197.50 │ 15M│  │
│  │   +    │ 2026-03-19 │        │        │        │196.00 │     │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ── PROVIDER ASSIGNMENT ────────────────────────────────────────   │
│  Provider: Yahoo Finance (yfinance)        [Change] [Remove]        │
│  Identifier: AAPL (TICKER)                                          │
│  Last fetch: 2026-03-23 10:30                                       │
│  Fetch interval: 1440 min (24h)                                     │
│                                                                     │
│  ── oppure se nessun provider ──                                    │
│  No provider assigned.  [+ Assign Provider]                         │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Provider:  [Yahoo Finance  ▾]                                  │ │
│  │ Identifier: [AAPL                           ]                  │ │
│  │ Type:       [TICKER ▾]                                         │ │
│  │ (campi dinamici da params_schema, es. per cssscraper:)         │ │
│  │ CSS Selector *: [.summary-value strong      ]                  │ │
│  │ Currency *:     [EUR ▾]                                        │ │
│  │ Decimal Format: [US ▾]                                         │ │
│  │                                    [Cancel] [Assign]           │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ── METADATA (readonly, refreshable) ───────────────────────────   │
│  Identifiers:  ISIN: —  Ticker: AAPL  CUSIP: —  SEDOL: —           │
│  Sector: Technology                                                 │
│  Description: Consumer electronics and software company...          │
│  Geographic: 🇺🇸 USA 100%                                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### `AssetDataEditorSection.svelte`

Wrapper analogo a `FxDataEditorSection.svelte`, ma con colonne OHLCV:

| Colonna | Key | Tipo | Obbligatoria |
|---------|-----|------|-------------|
| Date | `date` | date | ✅ |
| Open | `open` | number | ❌ |
| High | `high` | number | ❌ |
| Low | `low` | number | ❌ |
| Close | `close` | number | ✅ |
| Volume | `volume` | number | ❌ |

Il `DataImportModal` CSV va adattato: attualmente gestisce 2 colonne (date, rate) per FX.
Per gli asset serve supporto a 6 colonne con mapping flessibile. Close è l'unico obbligatorio
oltre a Date.

Salvataggio via `POST /assets/prices` (bulk upsert).

#### Provider Assignment — Form Dinamico

Quando l'utente seleziona un provider dal dropdown, il form genera i campi secondo `params_schema`:
- `yfinance`/`justetf`: solo `identifier` + `identifier_type`
- `cssscraper`: + `current_css_selector`, `currency`, `decimal_format`
- `scheduled_investment`: schema complesso dedicato

#### Tasks

- [ ] Creare `assets/[id]/+page.ts` (load: fetch asset metadata + provider assignment)
- [ ] Creare `assets/[id]/+page.svelte` (header, filter bar, chart, data editor, provider, metadata)
- [ ] Integrare `PriceChartFull` con `POST /assets/prices/query` (DB-only, come FX convert)
- [ ] Integrare `ChartAestheticsSection` + `ChartSignalsSection` + `MeasurePanel` (foldable)
- [ ] Creare `AssetDataEditorSection.svelte` (wrapper DataEditor con colonne OHLCV)
- [ ] Adattare `DataImportModal` per supporto 6 colonne (o creare variante asset-specific)
- [ ] Provider assignment section con form dinamico da `params_schema`
- [ ] Pulsante Refresh Prices: attivo solo se provider assegnato, chiama `POST /assets/prices/sync`. Se no provider → **disabilitato** (opacity-50, tooltip "Assegna un provider o inserisci prezzi manualmente")
- [ ] Chart empty state: se no provider → messaggio "Nessun dato — inserire prezzi manualmente" + bottone apre editor (pattern identico a FX detail manual-only, Step 2b §5)
- [ ] Sezione Metadata readonly (identifiers, classification_params)
- [ ] Adaptive layout (wide/tablet/mobile) con ResizeObserver
- [ ] Chart settings store per-asset (come `chartSettingsStore.svelte.ts` per FX)
- [ ] Dark mode coerente
- [ ] **E4**: Segnali tecnici su AssetCard — estendere `PriceChartCompact` per accettare `settings?: ChartSettings` e renderizzare overlay segnali (SMA, Bollinger, ecc.). Spostato da Step 3: dipende dal chart settings store per-asset creato in questo step.

#### Currency Conversion on Query (sotto-task backend + frontend)

**Razionale**: ogni `PriceHistory` row ha la propria `currency` (può differire da `asset.currency`
se il provider restituisce in una valuta diversa, es. ETF cross-listed). Il frontend deve poter
visualizzare i prezzi nella valuta scelta dall'utente.

**Approccio**: Opzione B — il backend converte in `POST /assets/prices/query` tramite un campo
opzionale `target_currency`. Riusa `convert_bulk()` FX già esistente e ottimizzato.

**Prerequisito**: le coppie FX necessarie (es. USD→EUR) devono essere configurate e sincronizzate.
Se mancanti, il backend restituisce il prezzo originale non convertito con un warning in `errors`.

##### BackwardFillInfo Split — `AssetBackwardFillInfo`

Quando si converte un price point, ci sono **due fonti indipendenti di staleness**:
il prezzo (backward-filled N giorni) e il rate FX usato per la conversione (backward-filled M giorni).
Mescolarli in un unico `days_back` perde l'informazione su *quale* dato è vecchio.

**Schema**:
```python
# common.py — invariato (usato da FX e come base)
class BackwardFillInfo(BaseModel):
    actual_rate_date: date      # Data del dato reale
    days_back: int              # Giorni stale

# prices.py — NUOVO, estende per asset con info FX conversion
class AssetBackwardFillInfo(BackwardFillInfo):
    fx_rate_date: Optional[date] = None   # Data del rate FX usato per convertire
    fx_days_back: Optional[int] = None    # Giorni stale del rate FX
```

- **FX** (`FXConversionResult`): continua a usare `BackwardFillInfo` — zero modifiche
- **Asset** (`FAPricePoint`): tipo cambia da `BackwardFillInfo` a `AssetBackwardFillInfo`
- `AssetBackwardFillInfo` è un `BackwardFillInfo` (ereditarietà) → backward-compatible al 100%
- Senza conversione: `fx_rate_date` e `fx_days_back` restano `None` (comportamento attuale invariato)

**Comportamento per scenario**:

| Scenario | `days_back` | `fx_days_back` |
|----------|-------------|----------------|
| Prezzo fresco, no conversione | `None` (= no backward_fill_info) | — |
| Prezzo stale 3gg, no conversione | `3` | `None` |
| Prezzo fresco, FX fresco | `None` | — |
| Prezzo stale 3gg, FX fresco | `3` | `0` o `None` |
| Prezzo fresco, FX stale 2gg | `0` | `2` |
| Prezzo stale 3gg, FX stale 5gg | `3` | `5` |

**Gradiente opacità**: usa `days_back` dell'asset (il prezzo è il dato più impattante; le valute
oscillano poco). Il FX stale non influenza il gradiente del chart.

**Tooltip**: quando `fx_days_back` > 0, aggiungere riga dedicata sotto lo stale del prezzo:
`⚠ FX rate: N days old` — solo nel tooltip, non nel gradiente visivo.

**Marker puntuale opzionale**: per i punti dove il prezzo è fresco ma il FX è stale (caso raro),
valutare un piccolo marker ambra (⊙ 4px) sulla linea — da decidere in review durante l'implementazione.
Se troppo invasivo, solo tooltip.

##### Task Currency Conversion

- [ ] Backend: creare `AssetBackwardFillInfo(BackwardFillInfo)` in `prices.py` con `fx_rate_date` e `fx_days_back`
- [ ] Backend: aggiornare `FAPricePoint.backward_fill_info` tipo → `Optional[AssetBackwardFillInfo]`
- [ ] Backend: aggiungere `target_currency: Optional[str]` a `FAPriceQueryItem`
- [ ] Backend: aggiungere `original_currency: Optional[str]` a `FAPricePoint` (populated solo se convertito)
- [ ] Backend: in `get_prices_bulk()`, se `target_currency` presente e diversa da `point.currency`:
  - raggruppare punti per coppia `(from_currency, target_currency)`
  - chiamare `convert_bulk()` in batch (una query SQL per coppia)
  - sostituire OHLC con valori convertiti, impostare `original_currency`
  - popolare `fx_rate_date` e `fx_days_back` dal risultato `convert_bulk()`
- [ ] Backend: `./dev.py api sync` per rigenerare client Zodios
- [ ] Frontend: dropdown "Display currency" nella filter bar della detail page (default = `asset.currency`)
- [ ] Frontend: passare `target_currency` a `POST /assets/prices/query` quando selezionata
- [ ] Frontend: gradiente opacità chart → usa `days_back` (prezzo), ignora `fx_days_back`
- [ ] Frontend: tooltip chart → riga aggiuntiva `⚠ FX rate: N days old` quando `fx_days_back > 0`
- [ ] Frontend: etichetta valuta nel chart e indicatore "converted from USD" quando `original_currency` presente
- [ ] Documentazione MkDocs: `developer/backend/assets/price-conversion.md` — razionale currency per-row, flow conversione, BackwardFillInfo split, gestione stale composta, prerequisiti FX

---

### Step 5 — `AssetMatchingWizard.svelte` (condiviso Phase 7) (~1 giorno)

Spostato alla phase 7 perchè ora sarebbe non testabile o usabile.

---

### Step 6 — i18n, E2E Test, Documentazione (~1 giorno)

#### i18n Keys (~30 chiavi)

```
assets.title, assets.subtitle, assets.addAsset, assets.editAsset, assets.deleteConfirm,
assets.search.placeholder, assets.search.providers, assets.search.noResults,
assets.search.autoAssign, assets.search.searching,
assets.detail.header, assets.detail.provider, assets.detail.prices,
assets.detail.metadata, assets.detail.identifiers, assets.detail.noProvider,
assets.detail.assignProvider, assets.detail.removeProvider,
assets.detail.refreshMetadata, assets.detail.refreshPrices,
assets.detail.backToList,
assets.card.lastPrice, assets.card.noData,
assets.editor.importCsv, assets.editor.addRow,
assets.matching.title, assets.matching.searchDb, assets.matching.searchProviders,
assets.matching.createNew, assets.matching.select, assets.matching.notFound,
assets.viewMode.grid, assets.viewMode.table,
assets.provider.paramsTitle, assets.provider.identifier, assets.provider.identifierType
```

Aggiungere via `./dev.py i18n add` in EN/IT/FR/ES.

---

### 📝 Note per Step Documentazione — Verifiche Approfondite Post-Bugfixstep3Round 12

> **ATTENZIONE**: Le seguenti aree sono state modificate significativamente nel Round 12/12-Finale e
> richiedono **verifica approfondita** durante lo step di documentazione/QA.

#### Backend: `financial_math.py` — ✅ ELIMINATO (Round 12 Finale, Blocco 1)
- Funzioni spostate in `scheduled_investment.py` come sezione `# Financial Math`
- `_calculate_act_365` + `_calculate_act_360` fattorizzate in `_calculate_act_fixed(start, end, denominator)`
- `find_active_period()` eliminata (dead code)
- `test_financial_math.py` eliminato (13 test orfani di `find_active_period`)

#### Backend: `scheduled_investment.py` — Aggiornato Round 12 Finale
- **`_generate_schedule_values()` ora ritorna `tuple[dict, list[FAAssetEventPoint]]`** — cache salva la tupla intera (D5)
- **Emissione selettiva**: price points emessi solo alle maturation dates, non ogni giorno
- **`generate_interest=True`**: auto-genera eventi INTEREST ad ogni maturation date (D1/D8)
  - Cedola = `current_value - initial_value` (solo positiva)
  - Dopo coupon: `total_interest = 0`, `event_adjustment = 0` → value torna a `initial_value`
- **`MATURITY_SETTLEMENT`**: generato alla fine dello schedule (o del late interest) quando generate_interest=True (D6)
  - Dopo settlement il motore è "spento" — `get_current_value` ritorna settlement value
- **Late interest maturation frequency**: emissione selettiva anche post-maturity
- **Skip formula (D9)**: SIMPLE late interest usa closed-form, COMPOUND day-by-day solo nel sotto-periodo

#### Backend: `_upsert_asset_events()` — Aggiornato Round 12 Finale
- DELETE filtra anche per `provider_assignment_id` → eventi manuali sopravvivono al refresh (D7)

#### Backend: Schemi aggiornati
- `FAInterestRatePeriod.generate_interest: bool = False` — flag auto-generazione eventi
- `FALateInterestConfig.maturation_frequency: MaturationFrequency = DAILY` — emissione selettiva late
- `FALateInterestConfig.generate_interest: bool = False` — auto-generazione + MATURITY_SETTLEMENT
- `AssetEventType.MATURITY_SETTLEMENT` — nuovo valore enum (D6)
- `AssetEvent`: rimossa UniqueConstraint su (asset_id, date, type) → auto + manuali coesistono (D7)

#### Frontend: `ScheduledInvestmentEditor.svelte`
- **`generate_interest` toggle**: nuova colonna DataTable con checkbox inline
- **Maturation frequency filtering**: opzioni filtrate per durata periodo, auto-fallback a DAILY
- **Serialize/deserialize**: `generate_interest` + `maturation_frequency` su late_interest
- **Emoji icons** sulle opzioni maturation frequency

#### Frontend: Fix critici (Round 12 Finale, Blocco 4 §4.1/§4.3)
- `hasProvider` in `AssetModal.svelte`: accetta `AUTO_GENERATED` senza identifier
- Test button in `ProviderAssignmentSection.svelte`: abilitato per AUTO_GENERATED
- `computedParams`: passa `providerParams` direttamente per `scheduled_investment`

#### Documentazione da aggiornare
- `scheduled-investment.en.md`: aggiungere `generate_interest` flag, `maturation_frequency` su late, auto-eventi, MATURITY_SETTLEMENT
- Nota **auto-sync alla creazione**: frontend deve richiedere sync su tutto il range schedule
- Nota **riconfigurazione**: eliminare prezzi/eventi precedenti prima di ri-sincronizzare
- Verificare docs `day-count` con le 4 convenzioni
  Verificare coerenza con `AssetEventType` DB enum.
- **Nessun campo `day_count` su `FAInterestRatePeriod`** — è globale su `FAScheduledInvestmentSchedule`.
  Frontend e test devono rispettare questa separazione.





#### E2E Test Playwright

- [ ] Asset list: entrambe le view (grid + table) visibili
- [ ] Toggle view mode persiste in localStorage
- [ ] Filtri funzionanti (search, type, currency, active)
- [ ] Smart search trova asset da yfinance/justetf
- [ ] Auto-fill form da search result
- [ ] Create asset con auto-assign provider
- [ ] Create asset manuale (senza provider)
- [ ] Edit asset → modifiche salvate
- [ ] Delete asset → rimosso (con ConfirmModal)
- [ ] Detail page: chart con dati di prezzo
- [ ] Detail page: segnali tecnici (EMA) visibili
- [ ] Detail page: data editor OHLCV funziona
- [ ] Detail page: CSV import prezzi
- [ ] Provider assignment con form dinamico
- [ ] Provider cssscraper: campi params_schema visibili
- [ ] Matching wizard: search DB → select
- [ ] Matching wizard: search providers → create
- [ ] FX page: toggle grid/table funziona
- [ ] Dark mode coerente su tutti i componenti
- [ ] user_role VIEWER: pulsanti edit/delete/add nascosti

#### Screenshot Gallery

Light/dark × desktop/mobile per:
- Asset list (grid + table)
- Asset modal (search + form)
- Asset detail (chart + editor + provider)
- Matching wizard (3 step)
- FX list (table view — nuovo)

#### Documentazione MkDocs

Aggiornare `mkdocs_src/` con guida utente:
- Come aggiungere un asset (search vs manuale)
- Come usare il grafico e i segnali tecnici
- Come importare prezzi da CSV
- Come assegnare un provider manualmente

---

## 4. Riepilogo File

### Backend (modifiche)

```
backend/app/services/asset_source.py                               # params_schema property
backend/app/services/asset_source_providers/css_scraper.py         # override params_schema
backend/app/services/asset_source_providers/scheduled_investment.py # override params_schema
backend/app/schemas/provider.py                                     # FAProviderParamField + FAProviderInfo esteso
backend/app/api/v1/assets.py                                        # list_providers: filtro + fix supports_search
backend/app/main.py                                                 # asyncio.create_task(_prewarm_provider_caches)
```

### Frontend (nuovi)

```
src/lib/components/ui/ViewModeToggle.svelte                        # Toggle grid/table riusabile
src/lib/components/assets/AssetIcon.svelte                         # Icon con fallback chain
src/lib/components/assets/AssetCard.svelte                         # Card con mini chart
src/lib/components/assets/AssetTable.svelte                        # DataTable wrapper per assets
src/lib/components/assets/AssetModal.svelte                        # Create/Edit modale
src/lib/components/assets/AssetSearchAutocomplete.svelte           # Smart search multi-provider
src/lib/components/assets/AssetDataEditorSection.svelte            # DataEditor con colonne OHLCV
src/lib/components/assets/AssetMatchingWizard.svelte               # Wizard 3-step (condiviso Phase 7)
src/lib/components/fx/FxTable.svelte                               # DataTable wrapper per FX pairs
src/routes/(app)/assets/[id]/+page.svelte                          # Detail page
src/routes/(app)/assets/[id]/+page.ts                              # Detail load function
src/routes/(app)/assets/+page.ts                                   # List load function
```

### Frontend (riscritture)

```
src/routes/(app)/assets/+page.svelte                               # placeholder → dual view page
src/routes/(app)/fx/+page.svelte                                   # aggiunta toggle + FxTable
```

### Rigenerazione

```
./dev.py api sync                                                   # client Zodios
```

---

## 5. Stima Totale: ~8 giorni

| Step | Giorni | Contenuto |
|------|--------|-----------|
| 1 | 0.5 | Backend: params_schema, fix perf, pre-warm async |
| 2 | 1 | Asset list dual view + FX table view + ViewModeToggle |
| 2b | 0.5 | Bugfix, migrazione, UX refinement |
| 2c | 0.5 | Modali Sync-All e Multi-Delete |
| 3 | 5 | AssetModal + Search + Probe + ScheduledInvestment Engine (12 round, [dettaglio](phases/phase-06-subplan/plan-phase06Step3AssetModal.prompt.md)) |
| 4 | 2 | Asset detail page + chart + data editor + provider + currency conversion |
| 5 | 1 | AssetMatchingWizard (condiviso Phase 7) |
| 6 | 1 | i18n, E2E test, docs, gallery |

---

## 6. Dependency Graph

```
Phase 4 (DataTable, ModalBase, component library)
     │
Phase 4.8 (user_role, BrokerSharingModal)
     │
Phase 5 (PriceChartFull, Signal Library, DataEditor, FxCard)
     │
     ▼
Phase 6 — Step 1 (Backend: params_schema, fix perf) ✅
     │
     ├── Step 2 (Asset List + FX Table) ✅
     │
     ├── Step 2b (Bugfix, Migration, UX Refinement) ✅
     │
     ├── Step 2c (Sync-All + Multi-Delete modals) ✅
     │
     ├── Step 3 (AssetModal + Search + Probe + ScheduledInvestment Engine) ✅
     │      │    ← dettaglio in phases/phase-06-subplan/plan-phase06Step3AssetModal.prompt.md
     │      │    ← Round 12 Finale: phases/phase-06-subplan/plan-phase06Step3Round12Finale-MaturationEngine.prompt.md
     │      ▼
     ├── Step 4 (Asset Detail Page) ← dipende da Step 3 per edit modal + ProviderAssignmentSection
     │
     ├── Step 5 (AssetMatchingWizard) ← riusa logica Step 3
     │      │
     │      └──→ Phase 7 (riuso wizard nel MultiImportWizard)
     │
     └── Step 6 (i18n, Test, Docs)
```

---

## 7. Componenti Condivisi tra Fasi (aggiornamento)

| Componente | Built in | Used in |
|-----------|----------|---------|
| `ViewModeToggle.svelte` | Phase 6 | Phase 6 (Assets + FX), future pages |
| `AssetCard.svelte` | Phase 6 | Phase 6, Phase 8 (dashboard) |
| `AssetMatchingWizard.svelte` | Phase 6 | Phase 6, **Phase 7** (import BRIM) |
| `FxTable.svelte` | Phase 6 | Phase 6 (FX page) |
| `PriceChartFull` | Phase 5 | Phase 5, **Phase 6**, Phase 8 |
| `DataEditor` | Phase 5 | Phase 5, **Phase 6** |
| `FxCard` | Phase 5 | Phase 5, Phase 6 (pattern reference) |




