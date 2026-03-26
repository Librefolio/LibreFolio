# Plan: Phase 06 — Asset Management (Grafico & Analisi Tecnica)

**Data creazione**: 23 Marzo 2026  
**Ultimo aggiornamento**: 23 Marzo 2026  
**Status**: 📋 PIANIFICATO  
**Durata stimata**: ~7 giorni  
**Dipendenze**: Phase 5 (PriceChartFull, Signal Library, DataEditor), Phase 4 (DataTable, ModalBase, component library), Phase 4.8 (user_role)

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
| `POST /api/v1/assets/prices/refresh` | POST | ✅ | Bulk refresh prices da provider |
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

### Step 3 — `AssetModal.svelte` + `AssetSearchAutocomplete.svelte` (~1.5 giorni)

Creare `src/lib/components/assets/AssetModal.svelte` con `ModalBase`.
Creare `src/lib/components/assets/AssetSearchAutocomplete.svelte`.

#### Layout AssetModal

```
┌──────────────────────────────────────────────────────────┐
│  ✕                    Add Asset                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ── Search Online ──────────────────────────────────     │
│  🔍 Search by name, ticker, ISIN...                      │
│  Providers: ☑ Yahoo Finance  ☑ JustETF  ☐ CSS Scraper   │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 🍎 Apple Inc.           AAPL · USD · STOCK        │← │
│  │    via Yahoo Finance                               │  │
│  │ 🍎 Apple Inc.           AAPL · USD · STOCK        │  │
│  │    via JustETF                                     │  │
│  └────────────────────────────────────────────────────┘  │
│           ↓ (seleziona → auto-fill form sotto)           │
│                                                          │
│  ── Asset Details ──────────────────────────────────     │
│  Display Name *  [ Apple Inc.              ]             │
│  Asset Type *    [ STOCK           ▾]                    │
│  Currency *      [ 🇺🇸 USD          ▾]                   │
│  Icon            [📎 Choose image...       ]             │
│                                                          │
│  ▸ Identifiers (click to expand)                         │
│  ┌────────────────────────────────────────────────────┐  │
│  │ ISIN   [                ] Ticker [AAPL           ] │  │
│  │ CUSIP  [                ] SEDOL  [               ] │  │
│  │ FIGI   [                ]                          │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ⓘ Provider "yfinance" will be auto-assigned on create   │
│                                                          │
│                          [Cancel]  [Create Asset]        │
└──────────────────────────────────────────────────────────┘
```

#### Flussi

**Search → Create** (flusso primario, come `test_search_to_prices.py` steps 1→2→3):
1. Utente digita query (debounced 300ms)
2. `GET /assets/provider/search?q=...&providers=...` in parallelo su provider selezionati
3. Risultati in dropdown con `identifier`, `identifier_type`, `display_name`, `currency`, `asset_type`, `provider_code`
4. Selezione → auto-fill form + memorizza internamente `{identifier, identifier_type, provider_code}`
5. Submit → `POST /assets` (crea asset) → se search result: `POST /assets/provider` (assegna provider)
6. Banner info: "Provider X will be auto-assigned on create"

**Create Manuale** (flusso secondario):
1. Utente compila form direttamente (senza search)
2. Submit → solo `POST /assets`, nessun provider
3. Provider assegnabile poi dalla pagina dettaglio

**Edit Mode**:
1. Pre-popola con dati asset esistente
2. Sezione search nascosta
3. Submit → `PATCH /assets`

#### Tasks

- [ ] Creare `AssetSearchAutocomplete.svelte` (debounced search, provider checkboxes, dropdown risultati)
- [ ] Creare `AssetModal.svelte` con `ModalBase` (create + edit mode)
- [ ] Auto-fill form da search result
- [ ] Auto-assign provider on create (2-step: POST /assets → POST /assets/provider)
- [ ] `ImagePickerWrapper` per icon_url
- [ ] `CurrencySearchSelect` per currency
- [ ] `SimpleSelect` per asset_type (STOCK, ETF, BOND, CRYPTO, FUND, HOLD, CROWDFUND_LOAN, OTHER)
- [ ] Collapsible identifiers section (ISIN, Ticker, CUSIP, SEDOL, FIGI)
- [ ] Validazione: display_name obbligatorio, unicità (feedback da backend)
- [ ] user_role: VIEWER non può aprire il modal in create/edit mode

---

### Step 4 — Asset Detail Page con PriceChartFull + Analisi Tecnica (~2 giorni)

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
- [ ] Pulsante Refresh Prices: attivo solo se provider assegnato, chiama `POST /assets/prices/refresh`. Se no provider → **disabilitato** (opacity-50, tooltip "Assegna un provider o inserisci prezzi manualmente")
- [ ] Chart empty state: se no provider → messaggio "Nessun dato — inserire prezzi manualmente" + bottone apre editor (pattern identico a FX detail manual-only, Step 2b §5)
- [ ] Sezione Metadata readonly (identifiers, classification_params)
- [ ] Adaptive layout (wide/tablet/mobile) con ResizeObserver
- [ ] Chart settings store per-asset (come `chartSettingsStore.svelte.ts` per FX)
- [ ] Dark mode coerente

---

### Step 5 — `AssetMatchingWizard.svelte` (condiviso Phase 7) (~1 giorno)

Creare `src/lib/components/assets/AssetMatchingWizard.svelte`.

#### Layout

```
┌──────────────────────────────────────────────────────────┐
│  ✕               Find or Create Asset                    │
├──────────────────────────────────────────────────────────┤
│  Step: [① Search DB] → [② Search Online] → [③ Create]   │
│         ━━━━━━━━━━━    ─────────────────   ───────────   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ── Step 1: Search Existing Assets ──────────────────    │
│  🔍 [Search by name, ticker, ISIN...              ]      │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Name            │ Type │ Ccy │ Identifiers        │  │
│  ├─────────────────┼──────┼─────┼────────────────────┤  │
│  │ Apple Inc.      │ STK  │ USD │ AAPL               │  │
│  │ Apple Corp.     │ STK  │ USD │ APCX               │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  [Select "Apple Inc."]     [→ Not found, search online]  │
│                                                          │
├──────────────────── (Step 2 se cliccato) ────────────────┤
│                                                          │
│  ── Step 2: Search Online Providers ─────────────────    │
│  🔍 [Apple                                        ]      │
│  (risultati da GET /assets/provider/search)              │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 🍎 Apple Inc.  AAPL · USD · STOCK  via yfinance   │  │
│  │ 🍎 Apple Inc.  AAPL · USD · STOCK  via justetf    │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  [Select & Create]         [→ Not found, create manual]  │
│                                                          │
├──────────────────── (Step 3 se cliccato) ────────────────┤
│                                                          │
│  ── Step 3: Create Manually ─────────────────────────    │
│  (stesso form di AssetModal in create mode)               │
│  Display Name * [                    ]                    │
│  Asset Type *   [         ▾]                              │
│  Currency *     [         ▾]                              │
│                          [Cancel]  [Create & Select]      │
└──────────────────────────────────────────────────────────┘
```

#### Specifiche

- **Step 1**: `DataTable` con `GET /assets/query?search=...&identifier_contains=...`
  Ricerca per nome, ticker, ISIN. Selezione → emette `onselect(asset_id)`.
- **Step 2**: `GET /assets/provider/search?q=...` su tutti i provider con search.
  Selezione → crea asset + assegna provider (stesso flusso Step 3) → emette `onselect(asset_id)`.
- **Step 3**: form manuale (stesso di `AssetModal` create) → emette `onselect(asset_id)`.
- Pulsanti "Not found" per avanzare allo step successivo.
- Progress bar visuale (step indicator).
- Embeddabile standalone (dentro `ModalBase`) E inline (senza ModalBase, per Phase 7 import wizard).

#### Tasks

- [ ] Creare `AssetMatchingWizard.svelte` con 3 step
- [ ] Step 1: DataTable search DB esistente
- [ ] Step 2: Search provider online con risultati
- [ ] Step 3: Form manuale (riuso logica AssetModal)
- [ ] Emissione `onselect(asset_id: number)` in tutti e 3 gli step
- [ ] Step indicator visuale
- [ ] Supporto standalone (ModalBase) e inline (senza)
- [ ] i18n keys (assets.matching.*)

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

## 5. Stima Totale: ~7 giorni

| Step | Giorni | Contenuto |
|------|--------|-----------|
| 1 | 0.5 | Backend: params_schema, fix perf, pre-warm async |
| 2 | 1 | Asset list dual view + FX table view + ViewModeToggle |
| 3 | 1.5 | AssetModal + AssetSearchAutocomplete |
| 4 | 2 | Asset detail page + chart + data editor + provider |
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
Phase 6 — Step 1 (Backend: params_schema, fix perf)
     │
     ├── Step 2 (Asset List + FX Table)
     │
     ├── Step 3 (AssetModal + Search)
     │      │
     │      ▼
     ├── Step 4 (Asset Detail Page) ← dipende da Step 3 per edit modal
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



