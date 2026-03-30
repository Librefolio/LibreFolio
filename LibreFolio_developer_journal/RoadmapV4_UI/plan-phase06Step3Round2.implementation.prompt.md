# Phase 6 Step 3 — Round 2: Implementation Prompt (Clean Context)

> **Data creazione**: 30 Marzo 2026
> **Obiettivo**: Implementare le modifiche del Round 2 di AssetModal
> **Stima**: ~12h (~2.5 giorni lavorativi)

---

## 0. Contesto Progetto

**LibreFolio** è un portfolio tracker self-hosted. Stack:
- **Backend**: Python 3.13 + FastAPI + SQLModel (SQLite async) + Alembic
- **Frontend**: SvelteKit + Svelte 5 (runes) + Tailwind CSS 4 + ECharts + lucide-svelte
- **i18n**: svelte-i18n, 4 lingue (EN, IT, FR, ES), CLI `./dev.py i18n add|audit`
- **API client**: Zodios (auto-generato da OpenAPI). Sync con `./dev.py api sync`
- **DB migration**: In fase embrionale, si modifica `001_initial.py` e si ricrea con `./dev.py db create-clean`
- **Test**: `./dev.py test <category> <action>` (external, db, services, utils, schemas, api, e2e, front)

### Struttura chiave

```
backend/
├── app/
│   ├── api/v1/assets.py               # REST endpoints
│   ├── db/models.py                    # SQLModel ORM (AssetType enum riga ~149)
│   ├── schemas/assets.py              # Pydantic: FAAssetPatchItem, FAClassificationParams, etc.
│   ├── schemas/provider.py            # Pydantic: FAProviderProbeResponse, ProbeMetadataResult
│   ├── services/asset_source.py       # Core: AssetSearchService, probe logic
│   ├── services/asset_source_providers/yahoo_finance.py   # yfinance plugin
│   ├── services/asset_source_providers/justetf.py         # justetf plugin
│   └── services/transaction_service.py                    # TransactionService.create_bulk
├── alembic/versions/001_initial.py
└── data/populate_mock_data.py

frontend/src/
├── lib/
│   ├── components/
│   │   ├── assets/
│   │   │   ├── AssetModal.svelte              # 843 righe — target principale
│   │   │   ├── AssetSearchAutocomplete.svelte  # Search con dropdown risultati
│   │   │   ├── ProviderAssignmentSection.svelte # 519 righe — provider config + test
│   │   │   ├── AssetIcon.svelte
│   │   │   └── AssetTable.svelte
│   │   ├── ui/
│   │   │   ├── ModalBase.svelte
│   │   │   ├── ConfirmModal.svelte
│   │   │   ├── Tooltip.svelte                 # Da migrare a Svelte 5
│   │   │   ├── select/ (SimpleSelect, SearchSelect, CurrencySearchSelect)
│   │   │   ├── media/ImagePickerWrapper.svelte # Da migrare a Svelte 5
│   │   │   └── input/ (target per DistributionEditor)
│   │   └── table/DataTable.svelte
│   ├── stores/
│   │   └── countryStore.ts   # DA CREARE — pattern come currencyStore.ts
│   ├── utils/
│   │   ├── assetTypes.ts     # DA CREARE — utility centralizzata
│   │   └── imageCrop.ts      # Aggiungere preset "asset-icon"
│   └── i18n/{en,it,fr,es}.json
└── static/icons/asset-types/  # PNG per tipo asset (stock.png, etf.png, etc.)
```

---

## 1. Schema dati — Cosa restituisce il backend

### Probe metadata (POST /assets/provider/probe con operations=["metadata"])

`FAProviderProbeResponse.metadata.patch_data` è un `FAAssetPatchItem` serializzato come dict:

```json
{
  "asset_id": 0,
  "asset_type": "STOCK",
  "currency": "USD",
  "classification_params": {
    "short_description": "Apple Inc. — American multinational technology company...",
    "sector_area": {
      "distribution": {"Technology": "1.0000"}
    },
    "geographic_area": null
  },
  "identifier_ticker": "AAPL",
  "identifier_isin": "US0378331005",
  "identifier_cusip": null,
  "identifier_sedol": null,
  "identifier_figi": null,
  "identifier_uuid": null,
  "identifier_other": null,
  "display_name": null,
  "icon_url": null,
  "active": null
}
```

### FAClassificationParams (DB: `classification_params` JSON column)

```python
class FAClassificationParams(BaseModel):
    short_description: Optional[str] = None
    geographic_area: Optional[FAGeographicArea] = None   # distribution: Dict[ISO3, Decimal]
    sector_area: Optional[FASectorArea] = None            # distribution: Dict[SectorName, Decimal]
```

Distribuzioni: chiavi stringa, valori 0–1 (Decimal con 4 decimali). Somma deve essere 1.0.

### Asset DB columns (tutte editabili nella modale)

| Campo | Tipo | Note |
|-------|------|------|
| `display_name` | str | Required |
| `currency` | str (ISO 4217) | Required |
| `asset_type` | AssetType enum | Required |
| `icon_url` | str | Nullable |
| `active` | bool | Default true, toggle solo in edit mode |
| `classification_params` | JSON | FAClassificationParams |
| `identifier_isin` | str(12) | Nullable |
| `identifier_ticker` | str(20) | Nullable |
| `identifier_cusip` | str(9) | Nullable |
| `identifier_sedol` | str(7) | Nullable |
| `identifier_figi` | str(12) | Nullable |
| `identifier_uuid` | str(36) | Nullable |
| `identifier_other` | str(100) | Nullable |

### Asset Provider Assignment DB columns

| Campo | Tipo | Note |
|-------|------|------|
| `provider_code` | str | Required |
| `identifier` | str | Required |
| `identifier_type` | IdentifierType enum | Required |
| `provider_params` | JSON | Nullable, schema da provider |
| `fetch_interval` | int | Default 1440 (minutes) |
| `user_url` | str | Nullable |
| `last_fetch_at` | datetime | Readonly, solo edit mode |
| `provider_url` | str | Readonly, calcolato dal backend (dalla probe) |

---

## 2. DESIGN CHANGE — Layout modale ridisegnato

### Pannello "More Info" (unione Classification + Identifiers)

**Decisione utente**: Classification e Identifiers devono essere **uniti** in un unico pannello collapsible chiamato **"More Info"**. Il pulsante **"Ask Provider"** si trova nell'header di questo pannello.

### Layout ASCII art aggiornato

```
┌──────────────────────────────────────────────────────────────────┐
│  Create Asset                                             [✕]   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  🔍 SEARCH ONLINE                                               │
│  [🔎 Search Apple, AAPL, IE00B4L5Y983...                   ]   │
│  Providers: [●yfinance] [●justetf]   Searching… (1/2 providers) │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 🍎 Apple Inc.  AAPL · USD · STOCK [🔶yfinance badge] [↗] │  │
│  │ 📈 SWDA.MI     IE00B4L5Y983 · EUR · ETF [📗justetf]  [↗] │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ─── ASSET DETAILS ────────[🔄 Ask Provider] [🔘 Active] (edit)  │
│                                                                  │
│  ┌──────────┐   Name *       [Apple Inc.                     ]  │
│  │          │                                                    │
│  │   ICON   │   Type *       [📈 Stock                    ▾]   │
│  │  64×64   │                                                    │
│  │ (click   │   Currency *   [🇺🇸 USD                      ▾]   │
│  │ to edit) │                                                    │
│  └──────────┘   Description                                      │
│                 [Apple Inc. — American multinational         ]   │
│                 [technology company headquartered in...      ]   │
│                                                                  │
│  ▶ MORE INFO ────────────────────────────────────────────────    │
│  │                                                               │
│  │  ── Identifiers ──          [+ add] [🔄 Ask Provider]         │
│  │  ┌───────────────────────────────────┐                        │
│  │  │ codice ▲       │ valore   │ action│                        │
│  │  ├────────────────┼──────────┼───────┤                        │
│  │  │ UUID           │  asdasd  │  [✕]  │                        │
│  │  │ ISIN           │ adasdasd │  [✕]  │                        │
│  │  └────────────────┴──────────────────┘                        │
│  │                                                               │
│  │  ── Classification ──      [+ add] [🔄 Ask Provider]          │
│  │                                                               │
│  │  Sector Distribution                                          │
│  │  ┌──────────────────────────────────────────────────────┐    │
│  │  │ Name ▲          │ Bar              │ Weight% │       │    │
│  │  ├─────────────────┼──────────────────┼─────────┼───────┤    │
│  │  │ Technology      │ ████████████░░░░ │ [90.00] │  [✕]  │    │
│  │  │ Other           │ ██░░░░░░░░░░░░░░ │ [10.00] │  [✕]  │    │
│  │  ├─────────────────┴──────────────────┴─────────┴───────┤    │
│  │  │ [+ Add sector]              Total: 100.00% ✅        │    │
│  │  └──────────────────────────────────────────────────────┘    │
│  │                                                               │
│  │  Geographic Distribution           [+ add] [🔄 Ask Provider]  │
│  │  ┌──────────────────────────────────────────────────────┐    │
│  │  │ Country ▲       │ Bar              │ Weight% │       │    │
│  │  ├─────────────────┼──────────────────┼─────────┼───────┤    │
│  │  │ 🇺🇸 USA          │ ██████████░░░░░░ │ [60.00] │  [✕]  │    │
│  │  │ 🇨🇳 CHN          │ ██████░░░░░░░░░░ │ [30.00] │  [✕]  │    │
│  │  ├─────────────────┴──────────────────┴─────────┴───────┤    │
│  │  │ [+ Add country]             Total: 100.00% ✅        │    │
│  │  └──────────────────────────────────────────────────────┘    │
│  │                                                               │
│  ▶ PROVIDER ASSIGNMENT ── [☐ No Provider] ──── [✅ passed] ─── │
│  │                                                               │
│  │  Provider *      [🔶 Yahoo Finance              ▾]          │
│  │  Id. Type *      [TICKER                        ▾]          │
│  │  Identifier *    [AAPL                               ]      │
│  │  ┄┄ provider_params (dynamic) ┄┄                              │
│  │  Fetch Interval  [1440          ] min  (= 24h)               │
│  │  User URL        [https://my-notes.com/aapl  ] [↗]          │
│  │  Provider URL    [https://finance.yahoo.c… ] [↗] (readonly) │
│  │  Last Fetch      3 hours ago              (readonly, edit)   │
│  │                                                               │
│  │  [▶ Test Configuration]                                       │
│  │  ├ ✅ Current Price: 178.50 USD (1.23s) [ⓘ]                 │
│  │  └ ✅ History: 1250 points, 2020-01-02 → 2026-03-29 (2.45s) │
│  │                                                               │
├──────────────────────────────────────────────────────────────────┤
│                              [Cancel]  [🟢 Create Asset]         │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. "Ask Provider" — Logica di sovrascrittura con modale differenze

### Flusso completo quando l'utente preme "Ask Provider"

1. Chiama `POST /assets/provider/probe` con `operations: ["metadata"]`
2. Riceve `patch_data` con i campi: `asset_type`, `currency`, `classification_params` (con `short_description`, `sector_area`, `geographic_area`), `identifier_*` (7 campi)
3. Per **ogni** campo ricevuto (non solo identifiers — TUTTI i campi):

   **Caso A — Campo vuoto localmente + provider fornisce valore**: → Auto-fill silenzioso, badge ✔ verde

   **Caso B — Campo uguale al valore del provider**: → Nessuna modifica, badge ✔ verde (conferma)

   **Caso C — Campo diverso dal valore del provider**: → **NON sovrascrive automaticamente**. Accumula in una lista "differenze".

4. Se ci sono differenze (caso C):
   → Mostra una **modale di confronto** ("Provider Data Comparison") che elenca tutte le differenze.

### Design modale confronto differenze

```
┌──────────────────────────────────────────────────────────────────┐
│  Provider Data Comparison                                 [✕]   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  The provider returned values that differ from your current      │
│  data. Review each difference and choose whether to accept.     │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Field          │ Current Value     │ Provider Value        │  │
│  ├────────────────┼───────────────────┼───────────────────────┤  │
│  │ ☐ Currency     │ EUR               │ USD                   │  │
│  │ ☐ Asset Type   │ FUND              │ STOCK                 │  │
│  │ ☐ ISIN         │ IE00B4L5Y983      │ US0378331005          │  │
│  │ ☐ Description  │ (first 50 chars…) │ (first 50 chars…)     │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ── Distributions (accept/reject in block) ──                    │
│                                                                  │
│  ☐ Sector Distribution                                           │
│  ┌─ Current ──────────────────┐  ┌─ Provider ────────────────┐  │
│  │ Technology      90.00%     │  │ Technology      100.00%   │  │
│  │ Other           10.00%     │  │                           │  │
│  └────────────────────────────┘  └───────────────────────────┘  │
│                                                                  │
│  ☐ Geographic Distribution                                       │
│  ┌─ Current ──────────────────┐  ┌─ Provider ────────────────┐  │
│  │ 🇺🇸 USA          60.00%     │  │ 🇺🇸 USA          70.00%   │  │
│  │ 🇩🇪 DEU          40.00%     │  │ 🇨🇳 CHN          30.00%   │  │
│  └────────────────────────────┘  └───────────────────────────┘  │
│                                                                  │
│  [Select All] [Deselect All]                                     │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                   [Cancel]  [✅ Apply Selected (3/5)]            │
└──────────────────────────────────────────────────────────────────┘
```

### Regole per i campi stringa (identifier_*, currency, asset_type, short_description)

- Ogni riga ha una **checkbox individuale**
- L'utente può selezionare quali campi sovrascrivere
- "Apply Selected" applica solo i campi spuntati
- "Cancel" non applica nulla

### Regole per le distribuzioni (sector_area, geographic_area)

- Ogni distribuzione è un **blocco indivisibile**: o si accetta tutta o si rifiuta tutta
- Una singola checkbox per l'intera distribuzione
- Mostrare un confronto side-by-side (Current vs Provider)
- Se si accetta → sovrascrittura totale della distribuzione

### Campi da confrontare (tutti quelli nel patch_data)

| Campo patch_data | Tipo confronto | Note |
|---|---|---|
| `asset_type` | stringa | Solo se diverso |
| `currency` | stringa | Solo se diverso |
| `classification_params.short_description` | stringa (troncata in preview) | Solo se diverso |
| `classification_params.sector_area` | distribuzione (blocco) | Side-by-side |
| `classification_params.geographic_area` | distribuzione (blocco) | Side-by-side |
| `identifier_ticker` | stringa | Solo se diverso |
| `identifier_isin` | stringa | Solo se diverso |
| `identifier_cusip` | stringa | Solo se diverso |
| `identifier_sedol` | stringa | Solo se diverso |
| `identifier_figi` | stringa | Solo se diverso |
| `identifier_uuid` | stringa | Solo se diverso |
| `identifier_other` | stringa | Solo se diverso |

**NB**: `display_name`, `icon_url`, `active` sono ignorati dal provider (restituisce null per quelli).

---

## 4. Task completi da implementare

### Priorità 1 — Critici e bloccanti

#### 4.1 BUG-11: Create asset 201 ma modale non si chiude ⭐ CRITICO

**File**: `frontend/src/lib/components/assets/AssetModal.svelte` — `saveCreate()` (riga 444)

Separare create e assign in due try/catch indipendenti:

```typescript
async function saveCreate() {
    // Step 1: Create asset
    const createPayload = [{ ... }];
    const createResp = await zodiosApi.create_assets_bulk_api_v1_assets_post(createPayload);
    const result = createResp?.results?.[0];
    if (!result?.success) throw new Error(result?.message || 'Failed to create asset');
    const assetId = result.asset_id;

    // Step 2: Assign provider (separate try/catch — asset already created)
    if (hasProvider) {
        try {
            const assignPayload = [{ asset_id: assetId, ... }];
            await zodiosApi.assign_providers_bulk_api_v1_assets_provider_post(assignPayload);
        } catch (assignErr: any) {
            console.error('Provider assignment failed after asset creation:', assignErr);
            toasts.warning($t('assets.modal.createSuccessProviderFailed', { values: { name: displayName } }));
            open = false;
            oncreated?.();
            return;
        }
    }

    toasts.success($t('assets.modal.createSuccess', { values: { name: displayName } }));
    open = false;
    oncreated?.();
}
```

Aggiungere `console.error('Save failed:', e)` nel catch generico di `doSave()`.
Scrollare `formError` in vista con `setTimeout(() => { document.querySelector('[data-form-error]')?.scrollIntoView(...) }, 50)`.

#### 4.2 BUG-12: SimpleSelect dropdown troncato

**File**: `AssetModal.svelte` righe 632, 725

Rimuovere `overflow-hidden` dai container collapsible:
```svelte
<!-- PRIMA: -->
<div class="border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden">
<!-- DOPO: -->
<div class="border border-gray-200 dark:border-slate-700 rounded-lg">
```

#### 4.3 INDEX AssetType + mapping plugin + vincolo no-transazioni

**File `backend/app/db/models.py`**: Aggiungere `INDEX = "INDEX"` all'enum `AssetType`.

**File `backend/app/services/asset_source_providers/yahoo_finance.py`** (search, riga ~355): Applicare `asset_type_map` nella `search()` per normalizzare prima di restituire (stesso mapping già presente in `fetch_asset_metadata` riga 430). Aggiungere `"index": "INDEX"` alla mappa.

**File `backend/app/services/asset_source.py`** (core `search()`, riga ~2624): Dopo `item.get("type")`, validazione safety: se tipo non in `AssetType.__members__`, fallback a `"OTHER"` con warning.

**File `backend/app/services/transaction_service.py`** (`create_bulk`, riga ~150): Se `asset_type == AssetType.INDEX`, rifiutare con `success=False`, messaggio: "Cannot create transactions for INDEX assets".

**Test da creare**:
- `test_create_index_asset_success` in `test_assets_crud.py`
- `test_create_transaction_index_asset_rejected` in `test_transaction_edge_cases.py`
- `test_yfinance_search_returns_normalized_types` in `test_asset_source.py`
- `test_core_search_fallback_unknown_type_to_other` in `test_asset_source.py`

**Icona**: Creare `frontend/static/icons/asset-types/index.png` (64×64, stile coerente).
**Mock data**: Aggiungere 1-2 indici benchmark in `populate_mock_data.py`.

### Priorità 2 — Refactoring

#### 4.4 `assetTypes.ts` utility + rimozione duplicati

**File NUOVO**: `frontend/src/lib/utils/assetTypes.ts`

```typescript
export const ASSET_TYPES = [
    'STOCK', 'ETF', 'BOND', 'CRYPTO', 'FUND',
    'HOLD', 'CROWDFUND_LOAN', 'INDEX', 'OTHER',
] as const;
export type AssetTypeCode = typeof ASSET_TYPES[number];

const PNG_MAP: Record<string, string> = {
    STOCK: 'stock', ETF: 'etf', BOND: 'bond', CRYPTO: 'crypto',
    FUND: 'fund', HOLD: 'hold', CROWDFUND_LOAN: 'crowdfunding',
    INDEX: 'index', OTHER: 'other',
};

export function getAssetTypeIconUrl(type: string | null | undefined): string {
    const filename = PNG_MAP[(type ?? '').toUpperCase()] ?? 'other';
    return `/icons/asset-types/${filename}.png`;
}

export function buildAssetTypeOptions(t: (key: string) => string): SelectOption[] {
    return ASSET_TYPES.map(at => ({
        value: at,
        label: t(`assets.types.${at}`) || at,
        icon: getAssetTypeIconUrl(at),
    }));
}

export const IDENTIFIER_TYPES = [
    'TICKER', 'ISIN', 'CUSIP', 'SEDOL', 'FIGI', 'UUID', 'OTHER',
] as const;
export type IdentifierTypeCode = typeof IDENTIFIER_TYPES[number];
```

**Rimuovere duplicati da**: `AssetIcon.svelte`, `AssetModal.svelte`, `AssetTable.svelte`, `ProviderAssignmentSection.svelte`. Eliminare `PROVIDER_TYPE_MAP` e `mapProviderAssetType()` dal frontend (il backend ora normalizza).

#### 4.5 BUG-13: "No Provider" nell'header collapsible

**File**: `AssetModal.svelte` sezione Provider Assignment (riga 724+)

Spostare checkbox nell'header: `[▶/▼] Provider Assignment [☐ No Provider] [✅/❌ test]`

Logica:
- Checkbox checked → chevron nascosto, panel fisso chiuso, click header non fa nulla
- Checkbox unchecked → panel apribile/chiudibile normalmente
- `stopPropagation()` sulla checkbox per evitare toggle del collapsible

#### 4.6 BUG-14: Provider badge nei risultati di ricerca

**File**: `AssetSearchAutocomplete.svelte` (riga ~295)

Sostituire `<span class="text-gray-400">via {result.provider_code}</span>` con badge con icona provider. Usare `getAssetProviderIconUrl(result.provider_code)` dal provider list caricato.

### Priorità 3 — Streaming Search

#### 4.7 Backend: `search_stream()` nel core

**File**: `backend/app/services/asset_source.py` — `AssetSearchService`

Nuovo metodo `search_stream()` → `AsyncGenerator[str, None]`:
1. Risolvere providers, creare `asyncio.Queue()`
2. Per ogni provider, lanciare `asyncio.create_task()` che chiama `provider.search(query)` → `queue.put()`
3. Generatore fa `queue.get()` fino a completamento
4. Yield SSE: `data: {"event": "provider_results", "provider_code": "yfinance", "results": [...]}\n\n`
5. Evento finale: `data: {"event": "done", "total_results": N, ...}\n\n`

#### 4.8 Backend: Endpoint SSE

**File**: `backend/app/api/v1/assets.py`

```python
@provider_router.get("/search/stream")
async def search_assets_stream(q, providers, _current_user):
    return StreamingResponse(
        AssetSearchService.search_stream(q, provider_codes),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

#### 4.9 Frontend: ReadableStream con fetch()

**File**: `AssetSearchAutocomplete.svelte`

Sostituire `executeSearch()` per usare `fetch()` + `ReadableStream` verso `/api/v1/assets/provider/search/stream`. Fallback al REST endpoint se SSE fallisce. Mostrare "Searching... (1/2 providers)" con contatore incrementale.

### Priorità 4 — Modale completa con tutti i campi

#### 4.10 Ristrutturazione sezioni modale

**File**: `AssetModal.svelte`

**Sezione "Asset Details"** (sempre visibile):
- `display_name` (text, required)
- `asset_type` (SimpleSelect con icone PNG, include INDEX)
- `currency` (CurrencySearchSelect, required)
- `icon_url` (ImagePickerWrapper, layout Proposta A: 64×64 a sinistra, campi a destra)
- `classification_params.short_description` (textarea 2-3 righe)
- `active` (toggle, solo edit mode, nel header della sezione)

**Sezione "More Info"** (collapsible, NUOVA — unione Identifiers + Classification):
- Header: `[▶/▼] More Info ─────── [🔄 Ask Provider]`
- "Ask Provider" visibile solo se `hasProvider`
- Sub-sezione **Identifiers**: griglia 2 colonne con tutti i 7 campi identifier (ISIN, Ticker, CUSIP, SEDOL, FIGI, UUID, Other)
- Sub-sezione **Classification**:
  - `DistributionEditor kind="sector"` per `sector_area`
  - `DistributionEditor kind="geographic"` per `geographic_area`

**Sezione "Provider Assignment"** (collapsible, checkbox No Provider nell'header):
- Tutti i campi provider attuali +
- `fetch_interval` (number input + hint calcolato: 60→"(= 1h)", 1440→"(= 24h)")
- `last_fetch_at` (solo edit mode, data relativa + tooltip data esatta UTC)
- Tooltip [ⓘ] su Current Price nel test: "Price data may be up to 15 min delayed"
- History test: mostrare `date_range` in aggiunta a `points_count`

#### 4.11 "Ask Provider" — Nuova logica completa

**File**: `AssetModal.svelte` — riscrivere `handleAskProvider()`

La nuova logica deve:

1. Chiamare probe con `operations: ["metadata"]`
2. Dal `patch_data` ricevuto, iterare su TUTTI i campi:
   - `asset_type`, `currency`, `identifier_*` (7 campi), `classification_params.short_description`, `classification_params.sector_area`, `classification_params.geographic_area`
3. Per ogni campo:
   - **Vuoto localmente + provider ha valore** → auto-fill silenzioso, badge ✔
   - **Uguale** → badge ✔
   - **Diverso** → accumula in lista `differences[]`
4. Se `differences.length > 0` → apre `ProviderComparisonModal`
5. Se `differences.length === 0` → toast "All data matches provider" ✔

**Nuovo componente**: `ProviderComparisonModal.svelte`

Props:
```typescript
interface DiffItem {
    field: string;          // "currency", "identifier_isin", "sector_area", etc.
    label: string;          // Localized label
    type: 'string' | 'distribution';
    currentValue: any;
    providerValue: any;
    selected: boolean;      // Checkbox state
}

interface Props {
    open: boolean;
    differences: DiffItem[];
    onapply: (selectedFields: string[]) => void;
    oncancel: () => void;
}
```

- Per campi stringa: mostrare Current → Provider
- Per distribuzioni: mostrare side-by-side in blocco
- "Select All" / "Deselect All"
- "Apply Selected (N/M)" → applica solo i campi spuntati

### Priorità 5 — Classification + DistributionEditor

#### 4.12 DistributionEditor.svelte

**File NUOVO**: `frontend/src/lib/components/ui/input/DistributionEditor.svelte`

Wrappa `DataTable` (NOT `DataEditor.svelte` che è per time-series). Props:

```typescript
interface Props {
    kind: 'sector' | 'geographic';
    value?: Record<string, number>;  // bindable, 0-1 range
    readonly?: boolean;
    disabled?: boolean;
    onchange?: (value: Record<string, number>) => void;
}
```

Colonne DataTable:
| Column | Cell (existing) | Cell (new row) | Sortable |
|--------|----------------|----------------|----------|
| Key | Label (sector/🇺🇸 USA) | Select/autocomplete | ✅ |
| Bar | `<div>` gradiente verde proporzionale | Same | ❌ |
| Weight % | `editable-number` (0-100) | Same | ✅ |
| Actions | [✕] delete | [↩] revert | ❌ |

Footer: `[+ Add]   Total: {sum}%  {badge ✅/⚠}`
- sum == 100 → ✅ verde
- sum > 100 → ⚠ rosso "(+X% excess)"
- sum < 100 → ⚠ ambra "(X% missing)"

**Conversione interna**: riceve/emette 0–1, mostra 0–100.

#### 4.13 Settori: i18n + fetch

Fetch da `GET /utilities/sectors` → `{ items: ["Industrials", "Technology", ...] }`

Chiavi i18n da creare (12 settori × 4 lingue):
`sectors.Industrials`, `sectors.Technology`, `sectors.Financials`, `sectors.ConsumerDiscretionary`, `sectors.HealthCare`, `sectors.RealEstate`, `sectors.BasicMaterials`, `sectors.Energy`, `sectors.ConsumerStaples`, `sectors.Telecommunication`, `sectors.Utilities`, `sectors.Other`

Aggiungere `assets.types.INDEX` (EN: Index, IT: Indice, FR: Indice, ES: Índice).

#### 4.14 countryStore.ts

**File NUOVO**: `frontend/src/lib/stores/countryStore.ts`

Pattern analogo a `currencyStore.ts`: lazy load da `GET /utilities/countries?language={lang}`, session-level cache, reactive al cambio lingua.

Dropdown: `🇺🇸 USA — United States` (flag + iso3 + nome tradotto).

### Priorità 6 — Svelte 5 Migration

#### 4.15 Tooltip.svelte → Svelte 5 runes

- `export let` → `$props()` con `interface Props`
- `$: renderedContent` → `$derived()`
- `onMount`/`onDestroy` → `$effect` con cleanup
- `on:click` → `onclick`, `on:mouseenter` → `onmouseenter`, etc.
- `<slot/>` → `{@render children()}`

#### 4.16 ImagePickerWrapper.svelte → Svelte 5 runes

- `export let` → `$props()` con `open = $bindable()`
- `createEventDispatcher` → callback props: `onchange?: (url: string) => void`, `oncancel?: () => void`
- `<slot/>` → `{@render children?.()}`

#### 4.17 Aggiornare consumer

| File | Modifica |
|------|----------|
| `BrokerForm.svelte` | `on:change={(e) => e.detail.url}` → `onchange={(url) => ...}` |
| `ProfileTab.svelte` | `on:change` → `onchange`, `on:cancel` → `oncancel` |

#### 4.18 Preset "asset-icon"

**File**: `frontend/src/lib/utils/imageCrop.ts`

```typescript
'asset-icon': { width: 256, height: 256, aspect: 1, circular: false }
```

#### 4.19 Migration + mock data

- `001_initial.py`: aggiungere `INDEX` nei valori enum
- `populate_mock_data.py`: 1-2 indici (S&P 500 `^GSPC`, MSCI World `URTH`)
- `frontend/static/icons/asset-types/index.png`: icona 64×64

---

## 5. File da leggere prima di iniziare

I file critici da leggere interamente per avere il contesto completo:

| File | Motivo |
|------|--------|
| `frontend/src/lib/components/assets/AssetModal.svelte` | Target principale (843 righe) |
| `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte` | 519 righe, test config |
| `frontend/src/lib/components/assets/AssetSearchAutocomplete.svelte` | Search con dropdown |
| `frontend/src/lib/components/assets/AssetIcon.svelte` | Ha ASSET_TYPE_PNG_MAP duplicato |
| `frontend/src/lib/components/assets/AssetTable.svelte` | Ha ASSET_TYPE_PNG_MAP duplicato |
| `backend/app/db/models.py` (righe 100-170) | AssetType enum, IdentifierType enum |
| `backend/app/schemas/assets.py` (righe 380-600) | FAClassificationParams, distribuzioni |
| `backend/app/schemas/provider.py` (righe 270-370) | ProbeResponse, ProbeMetadataResult |
| `backend/app/services/asset_source.py` (righe 1190-1260) | _probe_metadata, probe flow |
| `backend/app/services/asset_source_providers/yahoo_finance.py` (righe 350-500) | search + fetch_metadata |
| `backend/app/services/asset_source.py` (righe 2600-2636) | core search() |
| `frontend/src/lib/components/ui/Tooltip.svelte` | Da migrare Svelte 5 |
| `frontend/src/lib/components/ui/media/ImagePickerWrapper.svelte` | Da migrare Svelte 5 |
| `frontend/src/lib/stores/currencyStore.ts` | Pattern di riferimento per countryStore |
| `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` | Pattern di riferimento per DistributionEditor |
| `frontend/src/lib/components/table/DataTable.svelte` | Base per DistributionEditor |
| `frontend/src/lib/utils/imageCrop.ts` | Aggiungere preset |

---

## 6. Chiavi i18n da creare

Usare `./dev.py i18n add <key> --en "..." --it "..." --fr "..." --es "..."` per ciascuna.

### Settori (12)
| Key | EN | IT | FR | ES |
|-----|----|----|----|----|
| `sectors.Industrials` | Industrials | Industriali | Industriels | Industriales |
| `sectors.Technology` | Technology | Tecnologia | Technologie | Tecnología |
| `sectors.Financials` | Financials | Finanziari | Financiers | Financieros |
| `sectors.ConsumerDiscretionary` | Consumer Discretionary | Beni voluttuari | Consommation discrétionnaire | Consumo discrecional |
| `sectors.HealthCare` | Health Care | Sanità | Santé | Salud |
| `sectors.RealEstate` | Real Estate | Immobiliare | Immobilier | Inmobiliario |
| `sectors.BasicMaterials` | Basic Materials | Materie prime | Matériaux de base | Materiales básicos |
| `sectors.Energy` | Energy | Energia | Énergie | Energía |
| `sectors.ConsumerStaples` | Consumer Staples | Beni di consumo | Consommation de base | Consumo básico |
| `sectors.Telecommunication` | Telecommunication | Telecomunicazioni | Télécommunication | Telecomunicaciones |
| `sectors.Utilities` | Utilities | Servizi pubblici | Services publics | Servicios públicos |
| `sectors.Other` | Other | Altro | Autre | Otro |

### Asset type INDEX
| Key | EN | IT | FR | ES |
|-----|----|----|----|----|
| `assets.types.INDEX` | Index | Indice | Indice | Índice |

### Nuove chiavi modale
| Key | EN | IT |
|-----|----|----|
| `assets.modal.moreInfo` | More Info | Ulteriori Info |
| `assets.modal.identifiers` | Identifiers | Identificatori |
| `assets.modal.classification` | Classification | Classificazione |
| `assets.modal.sectorDistribution` | Sector Distribution | Distribuzione Settoriale |
| `assets.modal.geographicDistribution` | Geographic Distribution | Distribuzione Geografica |
| `assets.modal.createSuccessProviderFailed` | Asset "{name}" created, but provider assignment failed. Assign it manually. | Asset "{name}" creato, ma assegnazione provider fallita. Assegna manualmente. |
| `assets.provider.fetchInterval` | Fetch Interval (min) | Intervallo Fetch (min) |
| `assets.provider.lastFetch` | Last Fetch | Ultimo Fetch |
| `assets.provider.neverFetched` | Never fetched | Mai eseguito |
| `assets.probe.cacheInfo` | Price data may be up to 15 minutes delayed. Use 'Sync' on the asset list for a fresh fetch. | I dati di prezzo possono avere un ritardo fino a 15 minuti. Usa 'Sync' nella lista asset per un aggiornamento. |
| `assets.comparison.title` | Provider Data Comparison | Confronto Dati Provider |
| `assets.comparison.description` | The provider returned values that differ from your current data. Review and choose which to accept. | Il provider ha restituito valori diversi dai tuoi dati attuali. Revisiona e scegli quali accettare. |
| `assets.comparison.currentValue` | Current Value | Valore Attuale |
| `assets.comparison.providerValue` | Provider Value | Valore Provider |
| `assets.comparison.selectAll` | Select All | Seleziona Tutto |
| `assets.comparison.deselectAll` | Deselect All | Deseleziona Tutto |
| `assets.comparison.applySelected` | Apply Selected ({count}/{total}) | Applica Selezionati ({count}/{total}) |
| `assets.comparison.allMatch` | All data matches provider ✔ | Tutti i dati corrispondono al provider ✔ |
| `assets.distribution.total` | Total | Totale |
| `assets.distribution.excess` | excess | eccesso |
| `assets.distribution.missing` | missing | mancante |
| `assets.distribution.addSector` | Add sector | Aggiungi settore |
| `assets.distribution.addCountry` | Add country | Aggiungi paese |

(Aggiungere FR e ES per tutte queste chiavi)

---

## 7. Ordine di implementazione consigliato

1. **BUG-11** (critico, 30 min) → Corregge il flusso create
2. **BUG-12** (10 min) → overflow-hidden
3. **4.4 assetTypes.ts** (25 min) → Centralizza, pulisce duplicati
4. **4.3 INDEX** backend (45 min) → Enum + mapping + vincolo + test
5. **4.5 BUG-13** No Provider nell'header (20 min)
6. **4.6 BUG-14** Provider badge (15 min)
7. **4.15-4.18 Svelte 5 migration** (Tooltip + ImagePickerWrapper + consumer + preset) (65 min)
8. **4.7-4.9 Streaming Search** (backend + endpoint + frontend) (1h 45min)
9. **4.10 Ristrutturazione modale** (layout + tutti i campi + fetch_interval + last_fetch) (1h 40min)
10. **4.12-4.14 DistributionEditor + stores** (countryStore + settori i18n) (3h 15min)
11. **4.11 Ask Provider + ProviderComparisonModal** (nuova logica completa) (1h 30min)
12. **4.19 Migration + mock data + icona** (20 min)
13. **i18n keys** (30 min, distribuito durante l'implementazione)

**Stima totale**: ~12h

---

## 8. Note importanti per l'implementazione

- **Svelte 5 runes**: TUTTI i nuovi componenti devono usare `$props()`, `$state()`, `$derived()`, `$effect()`. NO `export let`, NO `$:`, NO `createEventDispatcher`, NO `<slot/>`.
- **Tailwind CSS 4**: Le classi sono definite in `app.css` via `@theme {}`. Usare le variabili CSS del design system (`--color-libre-green`, etc.).
- **i18n**: Ogni stringa visibile all'utente DEVE avere una chiave i18n. Usare `$t('key')`.
- **Dark mode**: OGNI classe visiva deve avere il corrispondente `dark:` variant.
- **Test**: Dopo modifiche backend, verificare con `./dev.py test api run` e `./dev.py test services run`.
- **API sync**: Dopo modifiche agli endpoint backend, eseguire `./dev.py api sync` per rigenerare i tipi Zodios.
- **DB**: Dopo modifica a `001_initial.py`, eseguire `./dev.py db create-clean`.

