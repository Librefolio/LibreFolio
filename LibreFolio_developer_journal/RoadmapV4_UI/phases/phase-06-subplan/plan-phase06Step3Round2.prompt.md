# Phase 6 Step 3 — Round 2: AssetModal Completion & Streaming Search

> **Data creazione**: 30 Marzo 2026
> **Ultimo aggiornamento**: 30 Marzo 2026
> **Status**: 📋 PIANIFICATO
> **Durata stimata**: ~4 giorni
> **Dipendenze**: Phase 6 Step 3 Round 1 (AssetModal v1 ✅), bugfix-phase06Step3.md (Round 1 bugs ✅)

---

## 0. Panoramica

Completamento AssetModal con: INDEX type + vincolo no-transazioni, streaming search SSE via `ReadableStream`, modale con tutti i campi DB, `DistributionEditor` basato su DataTable, tooltip info su test connection, fix BUG-11/12/13/14, migrazione `ImagePickerWrapper` + `Tooltip` a Svelte 5. La cache resta nei provider (non nel core). Il core orchestra solo lo stream con `as_completed`.

### Decisioni prese dall'utente

| # | Decisione | Risposta |
|---|-----------|----------|
| 1 | Nuovi AssetType? | Sì: `INDEX` (benchmark virtuale, no transazioni). NO per FUTURE/COMMODITY/OPTION. |
| 2 | Mapping asset_type: dove? | Nei **plugin** (`search()`), NON nel core. Il core fa solo fallback `OTHER` per tipi non riconosciuti. |
| 3 | Streaming search | Sì, ora. Backend SSE con `StreamingResponse`, frontend con `ReadableStream` + `fetch()` (no `EventSource`, per sicurezza auth header). |
| 4 | `classification_params` | Progettare ora. `DistributionEditor` riusabile basato su DataTable, con sort, add row con auto-focus. |
| 5 | Proposta A (Compact Profile Card) | Confermata. Icona 64×64 a sinistra, campi a destra. |
| 6 | "No Provider" nell'header | Confermato. Checkbox nell'header collapsible, panel chiuso fisso se checked. |
| 7 | Vincolo INDEX no-transazioni | Service layer (`TransactionService.create_bulk`). Niente vincolo DB (SQLite non supporta CHECK cross-table). |
| 8 | `DistributionEditor` stile | Barre percentuali lineari (no pie chart). Basato su DataTable per sort/edit. Eccesso/mancanza evidenziati. |
| 9 | SSE auth | `ReadableStream` con `fetch()` + header `Authorization`. No token in URL. |
| 10 | ImagePickerWrapper + Tooltip | Migrare a Svelte 5 runes (non adapter). Aggiornare tutti i consumer. |
| 11 | Settori i18n | Creare chiavi traduzione con `./dev.py`. |
| 12 | Paesi | Fetch da `GET /utilities/countries?language=` con flag emoji, tradotti. Creare `countryStore.ts`. |

---

## 1. Backend: `INDEX` AssetType + mapping nei plugin + vincolo no-transazioni

### 1a. Enum `AssetType`

**File**: `backend/app/db/models.py` (riga 149)

Aggiungere `INDEX = "INDEX"` all'enum `AssetType`. Aggiornare docstring:

```
INDEX: Market indices used as benchmarks (S&P 500, MSCI World).
       Cannot have transactions — virtual signal only.
       Restriction enforced at service layer (TransactionService.create_bulk).
```

### 1b. Mapping nei plugin (non nel core)

Ogni plugin `search()` deve restituire `type` già normalizzato ai nostri `AssetType` standard.

**File**: `backend/app/services/asset_source_providers/yahoo_finance.py`

Nella funzione `search()` (riga 355), il campo `"type"` oggi restituisce `quote.get("quoteType")` raw (es. `"EQUITY"`). Applicare lo stesso `asset_type_map` già presente in `fetch_asset_metadata()` (riga 430–439) per normalizzare **prima** di restituire:

```python
# Inside search(), before appending to results:
asset_type_map = {
    "equity": "STOCK", "etf": "ETF", "mutualfund": "FUND",
    "cryptocurrency": "CRYPTO", "currency": "OTHER",
    "future": "OTHER", "option": "OTHER", "index": "INDEX",
}
raw_type = quote.get("quoteType", "OTHER").lower()
normalized_type = asset_type_map.get(raw_type, "OTHER")

results.append({
    ...
    "type": normalized_type,  # ← was: quote.get("quoteType", "Unknown")
})
```

**File**: `backend/app/services/asset_source_providers/justetf.py` — già restituisce `"type": "ETF"` → OK, nessuna modifica.

**File**: `backend/app/services/asset_source.py` — aggiornare docstring del metodo `search()` nella base class `AssetSourceProvider` (riga 397):

```
Returns:
    List of dicts, each containing:
    - type: str | None - Asset type, must be a valid AssetType enum value
      (STOCK, ETF, BOND, CRYPTO, FUND, HOLD, CROWDFUND_LOAN, INDEX, OTHER).
      Do NOT return raw provider types (EQUITY, MUTUALFUND, etc.).
      The core will replace any unrecognized type with OTHER as safety net.
```

### 1c. Fallback OTHER nel core

**File**: `backend/app/services/asset_source.py` — `AssetSearchService.search()` (riga 2624)

Dopo `item.get("type")`, aggiungere validazione:

```python
from backend.app.db.models import AssetType

raw_asset_type = item.get("type")
# Safety net: if plugin returns unrecognized type, fallback to OTHER
if raw_asset_type and raw_asset_type not in AssetType.__members__:
    logger.warning(
        f"Provider '{code}' returned unrecognized asset type '{raw_asset_type}', "
        f"falling back to OTHER"
    )
    raw_asset_type = "OTHER"

results.append(
    FAProviderSearchResultItem(
        ...
        asset_type=raw_asset_type,
        ...
    )
)
```

### 1d. Vincolo no-transazioni (service layer)

**File**: `backend/app/services/transaction_service.py` — `create_bulk()` (riga 150, nel loop Phase 1)

Aggiungere import `Asset, AssetType` e check prima di creare la transazione:

```python
# After broker access check, before creating Transaction:
if item.asset_id:
    asset_stmt = select(Asset.asset_type).where(Asset.id == item.asset_id)
    asset_result = await self.session.execute(asset_stmt)
    asset_type = asset_result.scalar_one_or_none()
    if asset_type == AssetType.INDEX:
        results.append(TXCreateResultItem(
            success=False,
            error=f"Cannot create transactions for INDEX assets "
                  f"(asset_id={item.asset_id}). INDEX assets are virtual "
                  f"benchmarks and cannot be purchased or sold."
        ))
        continue
```

**Vincolo DB**: SQLite non supporta `CHECK` con subquery cross-table, quindi il vincolo rimane solo nel service layer. Annotare nel docstring di `Transaction` model: "Note: INDEX assets cannot have transactions. Enforced in TransactionService.create_bulk()."

### 1e. Test

**File**: `backend/test_scripts/test_api/test_assets_crud.py`
- Nuovo test: `test_create_index_asset_success` — crea un asset con `asset_type=INDEX`, verifica 201.

**File**: `backend/test_scripts/test_services/test_transaction_edge_cases.py`
- Nuovo test: `test_create_transaction_index_asset_rejected` — crea un asset INDEX, poi tenta una transazione BUY → verifica che `success=False` con messaggio "Cannot create transactions for INDEX assets".

**File**: `backend/test_scripts/test_services/test_asset_source.py`
- Nuovo test: `test_yfinance_search_returns_normalized_types` — verifica che yfinance `search()` non restituisce mai `"EQUITY"` o `"MUTUALFUND"`, solo `"STOCK"`, `"FUND"`, etc.
- Nuovo test: `test_core_search_fallback_unknown_type_to_other` — mock un provider che restituisce `type="BANANA"` → verifica che il core lo normalizza a `"OTHER"`.

### 1f. Migration + mock data + icona

- `backend/alembic/versions/001_initial.py`: aggiungere `INDEX` nei valori enum (se necessario per SQLite).
- `backend/data/populate_mock_data.py`: aggiungere 1-2 indici benchmark (es. "S&P 500" ticker `^GSPC`, "MSCI World" ticker `URTH`).
- Creare `frontend/static/icons/asset-types/index.png` (icona per indici — stile coerente con le altre PNG, ~64×64px, sfondo trasparente).

---

## 2. Backend + Frontend: Streaming Search via SSE

### Architettura

La cache resta **nei provider** (yfinance ha `_search_cache` TTLCache 10min via `get_ttl_cache("yfinance_search", ttl=600)`, justetf ha la sua cache). Il core NON ha una cache propria per la search — fa solo da orchestratore. I provider rispondono istantaneamente se il dato è in cache, o lanciano la query esterna se no. Lato frontend non c'è distinzione tra risposta cached o live — si fa append in coda senza riordinamento.

### 2a. Backend — `search_stream()` nel core

**File**: `backend/app/services/asset_source.py` — classe `AssetSearchService`

Aggiungere metodo:

```python
@staticmethod
async def search_stream(
    query: str, provider_codes: Optional[list[str]] = None
) -> AsyncGenerator[str, None]:
    """
    Stream search results as SSE events, one per provider.

    Each provider responds at its own pace (instant if cached, slower if live).
    Results are emitted as they arrive via asyncio.Queue.

    SSE format:
        data: {"event": "provider_results", "provider_code": "yfinance", "results": [...]}

        data: {"event": "done", "total_results": 15, "providers_queried": [...], "providers_with_errors": [...]}

    See also: search() for single-response REST alternative.
    """
```

Implementazione:
1. Risolvere `valid_providers` (stessa logica di `search()`).
2. Creare `asyncio.Queue()`.
3. Per ogni provider, lanciare un `asyncio.create_task()` che:
   - Chiama `provider.search(query)` (colpisce la cache del provider se presente).
   - Normalizza i risultati in `FAProviderSearchResultItem` (stessa logica di `search()`).
   - Applica fallback `OTHER` per tipi non riconosciuti.
   - Fa `queue.put((code, results, error))`.
4. Il generatore fa `queue.get()` in un loop fino a che tutti i task hanno completato.
5. Per ogni risultato, `yield f"data: {json_payload}\n\n"`.
6. Alla fine, yield evento `done`.

### 2b. Backend — endpoint SSE

**File**: `backend/app/api/v1/assets.py`

Aggiungere sotto l'endpoint `/search` esistente:

```python
@provider_router.get("/search/stream")
async def search_assets_stream(
    q: str = Query(..., min_length=1, description="Search query"),
    providers: Optional[str] = Query(None, description="Comma-separated provider codes"),
    _current_user: User = Depends(get_current_user),
):
    """
    Stream search results via Server-Sent Events (SSE).

    Same as GET /search but returns results incrementally as each provider responds.
    Useful for progressive UI updates. Use fetch() with ReadableStream on the client.

    See also: GET /assets/provider/search for single-response REST alternative
    (suitable for external integrations without SSE support).

    Events:
    - provider_results: { provider_code, results[] }  — one per provider
    - done: { total_results, providers_queried, providers_with_errors }
    """
    provider_codes = [p.strip() for p in providers.split(",") if p.strip()] if providers else None

    return StreamingResponse(
        AssetSearchService.search_stream(q, provider_codes),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

Aggiornare la docstring dell'endpoint REST `/search` esistente aggiungendo:

```
See also: GET /assets/provider/search/stream for SSE streaming alternative
(returns results incrementally as each provider responds).
```

### 2c. Frontend — `ReadableStream` con `fetch()`

**File**: `frontend/src/lib/components/assets/AssetSearchAutocomplete.svelte`

Sostituire `executeSearch()`:

```typescript
async function executeSearch(q: string) {
    if (q.trim().length === 0 || selectedProviders.size === 0) return;
    const mySearchId = ++searchId;
    loading = true;
    error = null;
    showResults = true;
    results = [];  // Clear previous results

    const providerCodes = [...selectedProviders].join(',');
    let providersResponded = 0;
    const totalProviders = selectedProviders.size;

    try {
        const response = await fetch(
            `/api/v1/assets/provider/search/stream?q=${encodeURIComponent(q)}&providers=${providerCodes}`,
            { headers: { 'Authorization': `Bearer ${getToken()}` } }
        );

        if (!response.ok || !response.body) {
            // Fallback to REST endpoint
            await executeSearchRest(q, mySearchId);
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            if (mySearchId !== searchId) { reader.cancel(); return; }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() ?? '';  // Keep incomplete line in buffer

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const payload = JSON.parse(line.slice(6));

                if (payload.event === 'provider_results') {
                    providersResponded++;
                    const newResults = payload.results.map(mapToSearchResult);
                    results = [...results, ...newResults];  // Append in order of arrival
                } else if (payload.event === 'done') {
                    // Search complete
                }
            }
        }
    } catch (e: any) {
        if (mySearchId !== searchId) return;
        // Fallback to REST
        await executeSearchRest(q, mySearchId);
        return;
    } finally {
        if (mySearchId === searchId) loading = false;
    }
}
```

Stato UI durante la ricerca: mostrare "Searching... ({providersResponded}/{totalProviders} providers)" nel dropdown loading state.

---

## 3. Frontend: Refactoring `assetTypes.ts` + rimozione duplicati

### 3a. Creare utility centralizzata

**File**: `frontend/src/lib/utils/assetTypes.ts` (NUOVO)

```typescript
import type {SelectOption} from '$lib/components/ui/select';

export const ASSET_TYPES = [
    'STOCK', 'ETF', 'BOND', 'CRYPTO', 'FUND',
    'HOLD', 'CROWDFUND_LOAN', 'INDEX', 'OTHER',
] as const;

export type AssetTypeCode = typeof ASSET_TYPES[number];

export const ASSET_TYPE_PNG_MAP: Record<string, string> = {
    STOCK: 'stock', ETF: 'etf', BOND: 'bond', CRYPTO: 'crypto',
    FUND: 'fund', HOLD: 'hold', CROWDFUND_LOAN: 'crowdfunding',
    INDEX: 'index', OTHER: 'other',
};

export function getAssetTypeIconUrl(type: string | null | undefined): string {
    const filename = ASSET_TYPE_PNG_MAP[(type ?? '').toUpperCase()] ?? 'other';
    return `/icons/asset-types/${filename}.png`;
}

export function buildAssetTypeOptions(t: (key: string) => string): SelectOption[] {
    return ASSET_TYPES.map(at => ({
        value: at,
        label: t(`assets.types.${at}`) || at,
        icon: getAssetTypeIconUrl(at),
    }));
}

/** Identifier types — centralized from backend IdentifierType enum */
export const IDENTIFIER_TYPES = [
    'TICKER', 'ISIN', 'CUSIP', 'SEDOL', 'FIGI', 'UUID', 'OTHER',
] as const;

export type IdentifierTypeCode = typeof IDENTIFIER_TYPES[number];
```

### 3b. Rimuovere duplicazioni

| File | Cosa rimuovere | Sostituire con |
|------|----------------|----------------|
| `AssetIcon.svelte` (riga 33) | `ASSET_TYPE_PNG_MAP` locale | `import { getAssetTypeIconUrl } from '$lib/utils/assetTypes'` |
| `AssetModal.svelte` (righe 81–101) | `ASSET_TYPES`, `ASSET_TYPE_PNG_MAP`, `PROVIDER_TYPE_MAP`, `mapProviderAssetType()` | `import { buildAssetTypeOptions } from '$lib/utils/assetTypes'` |
| `AssetTable.svelte` | `ASSET_TYPE_PNG_MAP` locale | `import { getAssetTypeIconUrl } from '$lib/utils/assetTypes'` |
| `ProviderAssignmentSection.svelte` (riga 99) | `ID_TYPES` locale | `import { IDENTIFIER_TYPES } from '$lib/utils/assetTypes'` |
| `icons.ts` | `ASSET_TYPE_ICONS` | Aggiungere `INDEX: '/icons/asset-types/index.png'` |

**`PROVIDER_TYPE_MAP`** e **`mapProviderAssetType()`** vengono eliminati completamente — il backend ora normalizza i tipi nei plugin.

---

## 4. Frontend: Modale completa con tutte le sezioni e campi DB

### Layout ASCII art completo

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
│  ─── ASSET DETAILS ──────────────────────── [🔘 Active] (edit)  │
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
│  ▶ CLASSIFICATION ──────────────────────────────────────────    │
│  │                                                               │
│  │  Sector Distribution                                          │
│  │  ┌──────────────────────────────────────────────────────┐    │
│  │  │ Name ▲          │ Bar              │ Weight% │       │    │
│  │  ├─────────────────┼──────────────────┼─────────┼───────┤    │
│  │  │ Technology      │ ████████████░░░░ │ [90.00] │  [✕]  │    │
│  │  │ Other           │ ██░░░░░░░░░░░░░░ │ [10.00] │  [✕]  │    │
│  │  │                 │                  │         │       │    │
│  │  │ * new row *     │ [select sector▾] │ [ 0.00] │  [↩]  │    │
│  │  ├─────────────────┴──────────────────┴─────────┴───────┤    │
│  │  │ [+ Add sector]              Total: 100.00% ✅        │    │
│  │  └──────────────────────────────────────────────────────┘    │
│  │                                                               │
│  │  Geographic Distribution                                      │
│  │  ┌──────────────────────────────────────────────────────┐    │
│  │  │ Country ▲       │ Bar              │ Weight% │       │    │
│  │  ├─────────────────┼──────────────────┼─────────┼───────┤    │
│  │  │ 🇺🇸 USA          │ ██████████░░░░░░ │ [60.00] │  [✕]  │    │
│  │  │ 🇨🇳 CHN          │ ██████░░░░░░░░░░ │ [30.00] │  [✕]  │    │
│  │  │ 🇩🇪 DEU          │ ██░░░░░░░░░░░░░░ │ [10.00] │  [✕]  │    │
│  │  │                 │                  │         │       │    │
│  │  │ * new row *     │ [search country▾]│ [ 0.00] │  [↩]  │    │
│  │  ├─────────────────┴──────────────────┴─────────┴───────┤    │
│  │  │ [+ Add country]             Total: 100.00% ✅        │    │
│  │  └──────────────────────────────────────────────────────┘    │
│  │                                                               │
│  ▶ IDENTIFIERS ─────────────────────────── [🔄 Ask Provider]   │
│  │  ┌──────────────┐ ┌───────────────┐                          │
│  │  │ ISIN         │ │ Ticker        │                          │
│  │  │ [US03783✔]   │ │ [AAPL   ✔]    │                          │
│  │  ├──────────────┤ ├───────────────┤                          │
│  │  │ CUSIP        │ │ SEDOL         │                          │
│  │  │ [          ] │ │ [           ] │                          │
│  │  ├──────────────┤ ├───────────────┤                          │
│  │  │ FIGI         │ │ UUID          │                          │
│  │  │ [          ] │ │ [           ] │                          │
│  │  └──────────────┘ └───────────────┘                          │
│  │  Other                                                        │
│  │  [                                                        ]  │
│  │                                                               │
│  ▶ PROVIDER ASSIGNMENT ── [☐ No Provider] ──── [✅ passed] ─── │
│  │                                                               │
│  │  Provider *      [🔶 Yahoo Finance              ▾]          │
│  │  Id. Type *      [TICKER                        ▾]          │
│  │  Identifier *    [AAPL                               ]      │
│  │                                                               │
│  │  ┄┄ provider_params (dynamic, from params_schema) ┄┄         │
│  │  │ selector:  [.price                  ]                      │
│  │  │ currency:  [EUR                     ]                      │
│  │                                                               │
│  │  Fetch Interval  [1440          ] min  (= 24h)               │
│  │                                                               │
│  │  User URL        [https://my-notes.com/aapl  ] [↗]          │
│  │  Provider URL    [https://finance.yahoo.c… ] [↗] (readonly) │
│  │  Last Fetch      3 hours ago                    (readonly)   │
│  │                  ↳ Tooltip: "2026-03-29 14:30:00 UTC"        │
│  │                                                               │
│  │  [▶ Test Configuration]                                       │
│  │  ├ ✅ Current Price: 178.50 USD (1.23s) [ⓘ]                 │
│  │  │    ↳ Tooltip: "Price data may be up to 15 minutes         │
│  │  │      delayed (Yahoo Finance real-time delay).              │
│  │  │      Use 'Sync' on the asset list for a fresh fetch."     │
│  │  └ ✅ History: 1250 points, 2020-01-02 → 2026-03-29 (2.45s) │
│  │    Total: 3.68s                                               │
│  │                                                               │
│  ⓘ Provider will be auto-assigned after creation                │
│                                                                  │
│  ┌─error──────────────────────────────────────────────────────┐  │
│  │ ⚠ Asset name already exists                                │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                              [Cancel]  [🟢 Create Asset]         │
└──────────────────────────────────────────────────────────────────┘
```

### Mappa campi DB → Sezione modale

**Tabella `assets`:**

| Campo DB | Sezione | Widget | Note |
|---|---|---|---|
| `display_name` | Asset Details | text input | Required |
| `asset_type` | Asset Details | SimpleSelect + icone PNG | Include `INDEX` |
| `currency` | Asset Details | CurrencySearchSelect | Required |
| `icon_url` | Asset Details | ImagePickerWrapper (Proposta A 64×64) | Placeholder dal tipo corrente |
| `active` | Asset Details header | toggle switch | Solo edit mode |
| `classification_params.short_description` | Asset Details | textarea 2-3 righe | Auto da "Ask Provider" |
| `classification_params.sector_area` | Classification (collapsible) | `DistributionEditor kind="sector"` | Auto da metadata |
| `classification_params.geographic_area` | Classification (collapsible) | `DistributionEditor kind="geographic"` | Auto da metadata |
| `identifier_isin` | Identifiers (collapsible) | text + badge ✔/⚠ | Da "Ask Provider" |
| `identifier_ticker` | Identifiers | text + badge ✔/⚠ | Da "Ask Provider" |
| `identifier_cusip` | Identifiers | text | — |
| `identifier_sedol` | Identifiers | text | — |
| `identifier_figi` | Identifiers | text | — |
| `identifier_uuid` | Identifiers | text | **Era nascosto** — ora esposto |
| `identifier_other` | Identifiers | text (full width) | **Era nascosto** — ora esposto |
| `created_at` / `updated_at` | — | Non editabili, non mostrati | — |

**Tabella `asset_provider_assignments`:**

| Campo DB | Sezione | Widget | Note |
|---|---|---|---|
| `provider_code` | Provider Assignment (collapsible) | SimpleSelect con icone | — |
| `identifier` | Provider Assignment | text input | — |
| `identifier_type` | Provider Assignment | SimpleSelect | — |
| `provider_params` | Provider Assignment | Form dinamico da `params_schema` | — |
| `fetch_interval` | Provider Assignment | number input + hint calcolato | **NUOVO** — default 1440, hint "(= 24h)" |
| `user_url` | Provider Assignment | text + link icon | — |
| `provider_url` | Provider Assignment (readonly) | text + link icon | Calcolato dal backend |
| `last_fetch_at` | Provider Assignment (readonly) | data relativa + tooltip esatta | **NUOVO** — solo edit mode |
| `created_at` / `updated_at` | — | Non editabili, non mostrati | — |

### Dettagli implementativi aggiuntivi

**Tooltip [ⓘ] su Current Price nel test connection**: Accanto al valore del test, un'icona ⓘ info con `Tooltip.svelte`. Testo i18n key `assets.probe.cacheInfo`:

> "Price data may be up to 15 minutes delayed (Yahoo Finance real-time delay). Use 'Sync' on the asset list for a fresh fetch."

Il TTL è per-provider. yfinance: `_search_cache` 10min; il `get_current_value()` usa `fast_info` che ha ~15min delay da Yahoo. Il tooltip comunica questo al utente.

**History date range**: Nella riga History dei test results, mostrare il `date_range` già restituito da `ProbeHistoryResult.date_range` (formato "2020-01-02 → 2026-03-29"). Oggi il frontend mostra solo `{h.points_count} points` — aggiungere: `{h.points_count} points, {h.date_range}`.

**`fetch_interval`**: Number input con hint calcolato dinamicamente:
- 60 → "(= 1h)", 720 → "(= 12h)", 1440 → "(= 24h)", 10080 → "(= 7d)"

**`last_fetch_at`**: Solo in edit mode. Formattato come data relativa ("3 hours ago") con tooltip che mostra la data esatta UTC.

---

## 5. Frontend: Fix BUG-11, BUG-12, BUG-13, BUG-14

### BUG-11: Create asset 201 ma modale non si chiude ⭐ CRITICO

**File**: `frontend/src/lib/components/assets/AssetModal.svelte` — `saveCreate()` (riga 444)

**Fix**: Separare create e assign in due try/catch indipendenti:

```typescript
async function saveCreate() {
    // Step 1: Create asset
    const createPayload = [{ ... }];
    const createResp = await zodiosApi.create_assets_bulk_api_v1_assets_post(createPayload);
    const result = createResp?.results?.[0];
    if (!result?.success) {
        throw new Error(result?.message || 'Failed to create asset');
    }
    const assetId = result.asset_id;

    // Step 2: Assign provider (separate try/catch — asset already created)
    if (hasProvider) {
        try {
            const assignPayload = [{ asset_id: assetId, ... }];
            await zodiosApi.assign_providers_bulk_api_v1_assets_provider_post(assignPayload);
        } catch (assignErr: any) {
            console.error('Provider assignment failed after asset creation:', assignErr);
            // Close modal but warn user
            toasts.warning($t('assets.modal.createSuccessProviderFailed', {
                values: { name: displayName }
            }));
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

Scrollare `formError` in vista:

```typescript
// After setting formError:
formError = e?.message || 'Save failed';
// Scroll error into view
setTimeout(() => {
    document.querySelector('[data-form-error]')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
}, 50);
```

### BUG-12: SimpleSelect dropdown troncato dentro panel collapsible

**File**: `frontend/src/lib/components/assets/AssetModal.svelte` (righe 632, 725)

**Fix**: Rimuovere `overflow-hidden` dalle classi dei container collapsible. Applicare border-radius separatamente:

```svelte
<!-- PRIMA: -->
<div class="border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden">

<!-- DOPO: -->
<div class="border border-gray-200 dark:border-slate-700 rounded-lg">
```

L'header del collapsible riceve `rounded-t-lg`, il content `rounded-b-lg` (quando è l'ultimo elemento visibile).

### BUG-13: "No Provider" checkbox nell'header collapsible

**File**: `frontend/src/lib/components/assets/AssetModal.svelte` — sezione Provider Assignment (riga 724+)

**Fix**: Spostare la checkbox nell'header:

```
[▶/▼] Provider Assignment    [☐ No Provider]    [✅/❌ test status]
```

Comportamento:
- **Checkbox checked** ("No Provider"): chevron nascosto, panel fisso chiuso, click sull'header non fa nulla.
- **Checkbox unchecked**: panel apribile/chiudibile normalmente con il chevron.
- `stopPropagation()` sul checkbox per evitare toggle del collapsible.

### BUG-14: Provider badge nei risultati di ricerca

**File**: `frontend/src/lib/components/assets/AssetSearchAutocomplete.svelte` (riga 295)

**Fix**: Sostituire:
```svelte
<span class="text-gray-400">via {result.provider_code}</span>
```

Con badge con icona:
```svelte
{#if providerIconUrl}
    <span class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] rounded bg-gray-100 dark:bg-slate-700">
        <img src={providerIconUrl} alt="" class="w-3 h-3 rounded-sm object-contain"/>
        <span class="text-gray-500 dark:text-gray-400">{result.provider_code}</span>
    </span>
{:else}
    <span class="inline-flex items-center px-1.5 py-0.5 text-[10px] rounded bg-gray-100 dark:bg-slate-700 text-gray-500">{result.provider_code}</span>
{/if}
```

Aggiungere `ensureAssetProvidersCached()` in `$effect` al mount del componente, e usare `getAssetProviderIconUrl(result.provider_code)` per il lookup.

---

## 6. Frontend: `DistributionEditor.svelte` basato su DataTable

### 6a. Componente

**File**: `frontend/src/lib/components/ui/input/DistributionEditor.svelte` (NUOVO)

Wrappa direttamente `DataTable` (NON `DataEditor.svelte` che è specifico per time-series con date). Logica di row status tracking interna, ispirata a DataEditor ma semplificata (no date, no CSV import, no stale days).

**Props**:
```typescript
interface Props {
    kind: 'sector' | 'geographic';
    value?: Record<string, number>;  // bindable, keys are sector names or ISO-3 codes
    readonly?: boolean;
    disabled?: boolean;
    onchange?: (value: Record<string, number>) => void;
}
```

**DataTable columns**:

| Column | Type | Cell (normal) | Cell (appended) | Sortable |
|--------|------|---------------|-----------------|----------|
| Key | string | Text label (sector name / 🇺🇸 USA) | Select/autocomplete dropdown | ✅ |
| Bar | custom | `<div>` con width proporzionale, gradiente verde | Same | ❌ |
| Weight % | number | `editable-number`, step 0.01, min 0, max 100 | Same | ✅ |
| Actions | — | [✕] delete | [↩] revert | ❌ |

**Footer**:
```
[+ Add {sector|country}]                Total: {sum}% {badge}
```

Badge logic:
- `sum == 100.00` → `✅` verde
- `sum > 100.00` → `⚠ (+{excess}% excess)` rosso
- `sum < 100.00` → `⚠ ({missing}% missing)` ambra

**Add row** (pattern DataEditor): Click su "Add" → append riga con key vuota, weight 0, `status: 'appended'`. Auto-focus via `navigateToRowId()`. Riga evidenziata con classe `row-appended`.

**Conversione pesi**: Il componente riceve/emette valori 0–1 (come `FAGeographicArea.distribution`), ma mostra 0–100 nell'input. La conversione è interna.

### 6b. Dati per autocomplete — Settori

Fetch da `GET /utilities/sectors` (Zodios alias: `list_sectors_api_v1_utilities_sectors_get`). Restituisce `{ items: ["Industrials", "Technology", ...], count: 12 }`. Cache nel componente (fetch una volta).

**Chiavi i18n** da creare con `./dev.py i18n`:

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

Aggiungere anche `assets.types.INDEX` per il nuovo tipo:

| Key | EN | IT | FR | ES |
|-----|----|----|----|----|
| `assets.types.INDEX` | Index | Indice | Indice | Índice |

### 6c. Dati per autocomplete — Paesi

Fetch da `GET /utilities/countries?language={currentLang}` (Zodios alias: `list_countries_api_v1_utilities_countries_get`). Restituisce:
```json
{ "items": [
    { "iso3": "USA", "iso2": "US", "name": "United States", "flag_emoji": "🇺🇸" },
    { "iso3": "ITA", "iso2": "IT", "name": "Italia", "flag_emoji": "🇮🇹" },
    ...
], "count": 249, "language": "it" }
```

**Creare `countryStore.ts`**: Pattern analogo a `currencyStore.ts` — lazy load + session-level cache + language-reactive.

**File**: `frontend/src/lib/stores/countryStore.ts` (NUOVO)

```typescript
// Session-level cache for country data.
// Pattern: same as currencyStore.ts
// - ensureCountriesLoaded(lang): lazy load, dedup concurrent calls
// - getAllCountries(): return cached list
// - getCountryInfo(iso3): lookup single country
// - Reactive: reloads when currentLanguage changes
```

Nel dropdown mostrare: `🇺🇸 USA — United States` (flag + iso3 + translated name).

---

## 7. Migrazione Svelte 5: `ImagePickerWrapper` + `Tooltip`

### 7a. `Tooltip.svelte` → Svelte 5 runes

**File**: `frontend/src/lib/components/ui/Tooltip.svelte`

Migrazione:
- `export let text/html/math/position/maxWidth` → `interface Props { ... }` + `let { ... }: Props = $props();`
- `$: renderedContent = getRenderedContent()` → `let renderedContent = $derived(getRenderedContent())`
- `onMount` / `onDestroy` → `$effect` con cleanup return
- `on:click={toggle}` → `onclick={toggle}`
- `on:keydown={handleKeydown}` → `onkeydown={handleKeydown}`
- `on:mouseenter={show}` / `on:mouseleave={hide}` → `onmouseenter={show}` / `onmouseleave={hide}`
- `<slot/>` → `{@render children()}` con `children` snippet prop
- `bind:this` rimane uguale

### 7b. `ImagePickerWrapper.svelte` → Svelte 5 runes

**File**: `frontend/src/lib/components/ui/media/ImagePickerWrapper.svelte`

Migrazione:
- `export let open/title/preset/initialUrl/circularPreview/filterImages` → `$props()` con `open = $bindable()`
- `createEventDispatcher` → callback props:
  ```typescript
  interface Props {
      open?: boolean;
      title?: string;
      preset?: PresetName;
      initialUrl?: string;
      circularPreview?: boolean;
      filterImages?: boolean;
      onchange?: (url: string) => void;
      oncancel?: () => void;
      children?: Snippet;
  }
  ```
- `dispatch('change', {url})` → `onchange?.(url)`
- `dispatch('cancel')` → `oncancel?.()`
- `<slot/>` → `{@render children?.()}`

### 7c. Aggiornare i consumer

| File | Modifica |
|------|----------|
| `BrokerForm.svelte` (riga 452) | `on:change={(e) => ... e.detail.url}` → `onchange={(url) => ...}` |
| `ProfileTab.svelte` (riga 751) | `on:change={(e) => ... e.detail.url}` → `onchange={(url) => ...}` |
| `BrokerForm.svelte` | `on:cancel` → `oncancel` |
| `ProfileTab.svelte` | `on:cancel` → `oncancel` |

Verificare anche `AssetPickerModal.svelte` e `ImageEditModal.svelte` — se usano `createEventDispatcher`, migrarli nello stesso passaggio.

### 7d. Aggiungere preset `"asset-icon"`

**File**: `frontend/src/lib/utils/imageCrop.ts`

Aggiungere preset:
```typescript
'asset-icon': {
    width: 256,
    height: 256,
    aspect: 1,
    circular: false,
}
```

---

## 8. Piano di Implementazione — Priorità e stime

### Priorità 1 — Critici e bloccanti

| # | Task | Stima | Files |
|---|------|-------|-------|
| BUG-11 | Fix create: separate try/catch, console.error, scroll formError | 30 min | AssetModal.svelte |
| BUG-12 | Fix dropdown troncato: remove overflow-hidden | 10 min | AssetModal.svelte |
| 1a-1c | INDEX AssetType + mapping plugin + core fallback | 45 min | models.py, yahoo_finance.py, asset_source.py |
| 1d | Vincolo no-transazioni INDEX | 20 min | transaction_service.py |
| 1e | Test INDEX + mapping + transaction rejection | 30 min | test_*.py |

### Priorità 2 — Refactoring

| # | Task | Stima | Files |
|---|------|-------|-------|
| 3 | `assetTypes.ts` utility + rimozione duplicati | 25 min | assetTypes.ts, AssetIcon, AssetModal, AssetTable, ProviderAssignment |
| BUG-13 | "No Provider" nell'header collapsible | 20 min | AssetModal.svelte |
| BUG-14 | Provider badge nei risultati search | 15 min | AssetSearchAutocomplete.svelte |

### Priorità 3 — Streaming Search

| # | Task | Stima | Files |
|---|------|-------|-------|
| 2a | `search_stream()` nel core | 45 min | asset_source.py |
| 2b | Endpoint SSE + docstring cross-ref | 15 min | assets.py (API) |
| 2c | Frontend ReadableStream + fallback REST | 45 min | AssetSearchAutocomplete.svelte |

### Priorità 4 — Modale completa

| # | Task | Stima | Files |
|---|------|-------|-------|
| 4 | Riorganizzare sezioni modale + tutti i campi | 1h | AssetModal.svelte, ProviderAssignmentSection.svelte |
| 4 | Tooltip su test results + history date range | 20 min | ProviderAssignmentSection.svelte |
| 4 | fetch_interval + last_fetch_at | 20 min | ProviderAssignmentSection.svelte |
| 4 | ImagePickerWrapper per asset icon (Proposta A) | 40 min | AssetModal.svelte |

### Priorità 5 — Classification + DistributionEditor

| # | Task | Stima | Files |
|---|------|-------|-------|
| 6a | DistributionEditor.svelte basato su DataTable | 2h | DistributionEditor.svelte (nuovo) |
| 6b | Settori: i18n keys (12 × 4 lingue) + fetch | 30 min | i18n files, DistributionEditor |
| 6c | countryStore.ts + integrazione geographic | 45 min | countryStore.ts (nuovo), DistributionEditor |
| 4 | Sezione Classification collapsible nella modale | 30 min | AssetModal.svelte |

### Priorità 6 — Svelte 5 Migration

| # | Task | Stima | Files |
|---|------|-------|-------|
| 7a | Tooltip.svelte → Svelte 5 runes | 20 min | Tooltip.svelte |
| 7b | ImagePickerWrapper → Svelte 5 runes | 25 min | ImagePickerWrapper.svelte |
| 7c | Aggiornare consumer (BrokerForm, ProfileTab) | 15 min | BrokerForm, ProfileTab |
| 7d | Preset "asset-icon" | 5 min | imageCrop.ts |
| 1f | index.png + migration + mock data | 20 min | icons, 001_initial.py, populate_mock_data.py |

---

**Stima totale**: ~12h (~2.5 giorni lavorativi a ritmo normale)

---

## 9. Note per il futuro (fuori scope)

- yfinance come FX provider → appuntato, non in questo step
- Nuovi AssetType (COMMODITY, FUTURE) → solo se necessaria la logica di pricing
- Benchmark overlay nei grafici per INDEX → Phase 8+
- `classification_params` auto-populated anche dal provider justetf (già restituisce sector/country da ETF overview)
- Active toggle nella tabella asset list (non solo nella modale edit)
- AssetMatchingWizard (Phase 6 Step 5)

