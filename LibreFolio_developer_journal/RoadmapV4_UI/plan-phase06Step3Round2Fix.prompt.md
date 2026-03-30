# Phase 6 Step 3 — Round 2 Fix & Refinement

> **Data creazione**: 30 Marzo 2026
> **Obiettivo**: Correggere i bug emersi dal Round 2, allineare la UI dei risultati di ricerca alla convenzione interna, ristrutturare le sezioni modale con `DataTable`, aggiungere selettori per settori/paesi, e bottoni "Ask Provider" per sezione.
> **Pre-requisiti**: Tutti i task del Round 2 completati e tutti i test backend+frontend passano.

---

## 0. Stato attuale (post Round 2)

### ✅ Completati e funzionanti
- BUG-11 (saveCreate try/catch separati), BUG-12 (overflow-hidden)
- `assetTypes.ts` centralizzato, duplicati rimossi
- BUG-13 (No Provider checkbox nell'header collapsible)
- BUG-14 (Provider badge nei risultati ricerca — parziale, vedi fix)
- Backend INDEX (enum, yahoo_finance mapping, core fallback, transaction rejection)
- Streaming search SSE (backend `search_stream` + endpoint + frontend `ReadableStream`)
- Ristrutturazione modale (More Info = Identifiers + Classification)
- ProviderComparisonModal, DistributionEditor (HTML custom)
- countryStore.ts, Svelte 5 migration (Tooltip, ImagePickerWrapper), consumer updates
- Preset `asset-icon` in imageCrop.ts
- i18n keys (718 chiavi, 100% coverage 4 lingue)
- Mock data INDEX (S&P 500, MSCI World)

### 🐛 Bug da correggere
1. **`IdentifierType.TICKER` serializzato come stringa enum** — L'endpoint SSE `search_stream()` usa `str(IdentifierType.TICKER)` che in Python 3.11+ produce `"IdentifierType.TICKER"` anziché `"TICKER"`. Il frontend lo passa tal quale ad "Ask Provider" → il backend rifiuta con `Input should be 'ISIN', 'TICKER', ...`.
2. **Ask Provider nascosto anziché disabilitato** — Quando non c'è provider, il bottone "Ask Provider" è completamente nascosto (`{#if hasProvider}`). L'utente preferisce che resti visibile ma disabilitato (greyed out).
3. **Checkbox "No Provider" duplicato** — Presente sia nell'header del collapsible (AssetModal) che internamente (ProviderAssignmentSection). Rimuovere quello interno.
4. **`import asyncio as _asyncio` dentro la funzione** — In `search_stream()`, `asyncio` è già importato al top del file.
5. **Starlette non nel Pipfile** — Usato e presente nel lock file, ma non dichiarato esplicitamente.

### 📐 Miglioramenti richiesti dall'utente
1. **Risultati ricerca**: il badge provider deve stare vicino al nome; il tipo asset deve mostrare la label i18n + icona nostra, non il raw type del provider.
2. **Tabelle con DataTable**: identifiers e distribuzioni devono usare il nostro `DataTable.svelte`, non HTML custom.
3. **"Add row" vicino al titolo**: il bottone per aggiungere riga va accanto al nome della sezione, non in fondo alla tabella.
4. **Ask Provider per sezione**: oltre al globale, servono bottoni specifici per Identifiers, Sector, Geographic.
5. **Selettori per settori e paesi**: DistributionEditor deve usare `SimpleSelect` (settori) e un nuovo `CountrySearchSelect` (paesi), non input di testo libero.
6. **i18n 11 chiavi non usate**: tenere per ora (saranno usate negli step successivi).

---

## 1. Contesto tecnico

### File principali coinvolti

| File | Righe | Ruolo |
|------|-------|-------|
| `backend/app/services/asset_source.py` | 2753 | Core search, `search_stream()` (riga 2647) |
| `backend/app/api/v1/assets.py` | 878 | Endpoint SSE `/search/stream` (riga 425) |
| `frontend/src/lib/components/assets/AssetModal.svelte` | 1022 | Target principale |
| `frontend/src/lib/components/assets/AssetSearchAutocomplete.svelte` | 396 | Risultati ricerca |
| `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte` | 519 | Config provider + test |
| `frontend/src/lib/components/ui/input/DistributionEditor.svelte` | 255 | Editor distribuzioni (da riscrivere) |
| `frontend/src/lib/components/table/DataTable.svelte` | 1837 | Tabella generica riutilizzabile |
| `frontend/src/lib/components/table/types.ts` | 462 | Tipi celle DataTable |
| `frontend/src/lib/utils/assetTypes.ts` | 69 | Tipi asset centralizzati |
| `frontend/src/lib/stores/countryStore.ts` | 121 | Cache paesi |
| `Pipfile` | 60 | Dipendenze Python |

### DataTable — Capacità rilevanti

Il `DataTable.svelte` supporta:
- **Cell types**: `string`, `number`, `icon-text`, `badge`, `date`, `size`, `link`, `custom`, `image`, `editable-number`, `html`
- **Row actions**: Array di `RowAction<T>` con icona, label, onClick, variant (default/danger), confirm
- **Custom cells**: `{ type: 'custom', component: MyComponent, props: {...} }` — renderizza qualsiasi Svelte component inline
- **Editable number**: `{ type: 'editable-number', value, step, min, max, onchange }` — input numerico inline
- **Disabilitabili**: selection, pagination, filters, sorting, column resize, column visibility

### Pattern DataEditor (riferimento)

`DataEditor.svelte` wrappa `DataTable` con:
- `enableSelection=true`, `enablePagination=true`, `enableSorting=true`
- Colonne costruite via `$derived.by()` che mappano i dati a cell content
- `CustomCell` per il `SingleDatePicker` inline
- `EditableNumberCell` per i valori editabili
- Row actions: delete (soft-delete), revert

---

## 2. Task da implementare

### Priorità 1 — Bug critici

#### 2.1 Fix serializzazione `IdentifierType` in SSE stream

**File**: `backend/app/services/asset_source.py`

**Problema**: Riga 2735 — `"identifier_type": str(item.get("identifier_type", ""))` produce `"IdentifierType.TICKER"` perché `str()` su un `str, Enum` in Python 3.11+ restituisce la rappresentazione completa.

**Soluzione**: Usare `.value` per estrarre il valore stringa:

```python
# PRIMA (riga 2735):
"identifier_type": str(item.get("identifier_type", "")),

# DOPO:
"identifier_type": getattr(item.get("identifier_type", ""), "value", str(item.get("identifier_type", ""))),
```

**Verifica**: L'endpoint REST non ha questo bug perché usa Pydantic (`FAProviderSearchResultItem.identifier_type: IdentifierType`) che serializza `.value` automaticamente.

#### 2.2 Rimuovere `import asyncio as _asyncio` dalla funzione

**File**: `backend/app/services/asset_source.py`

**Problema**: Riga 2667 — `import asyncio as _asyncio` dentro `search_stream()`. `asyncio` è già importato al top del file (riga 26).

**Soluzione**: Rimuovere riga 2667 e rinominare tutti i riferimenti `_asyncio.` → `asyncio.` (righe 2684, 2700, 2751).

#### 2.3 Aggiungere `starlette` al Pipfile

**File**: `Pipfile`

**Problema**: `starlette` è usato (`from starlette.responses import StreamingResponse` in `assets.py` riga 12) ed è nel lock file, ma non dichiarato nel Pipfile.

**Soluzione**: Aggiungere `starlette = "*"` nella sezione `[packages]`.

---

### Priorità 2 — UX: Risultati ricerca allineati alla convenzione

#### 2.4 Provider badge vicino al nome + asset_type localizzato

**File**: `frontend/src/lib/components/assets/AssetSearchAutocomplete.svelte`

**Stato attuale** (righe 348-372): Il badge provider è in fondo alla riga inferiore, dopo `currency · type · provider`. Il tipo è mostrato raw come `<span class="uppercase">{result.asset_type}</span>`.

**Modifiche richieste**:

**(a) Spostare badge provider sulla riga del nome:**
```svelte
<!-- Riga nome — PRIMA: -->
<div class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
    {result.display_name}
</div>

<!-- Riga nome — DOPO: -->
<div class="flex items-center gap-1.5 text-sm font-medium text-gray-900 dark:text-gray-100 min-w-0">
    <span class="truncate">{result.display_name}</span>
    {#if getAssetProviderIconUrl(result.provider_code)}
        <img src={getAssetProviderIconUrl(result.provider_code)} 
             alt={result.provider_code}
             class="w-3.5 h-3.5 rounded-sm object-contain shrink-0"
             title={result.provider_code}/>
    {/if}
</div>
```

**(b) Sostituire raw asset_type con label i18n + icona:**
```svelte
<!-- PRIMA: -->
{#if result.asset_type}
    <span class="mx-1">·</span>
    <span class="uppercase">{result.asset_type}</span>
{/if}

<!-- DOPO: -->
{#if result.asset_type}
    <span class="mx-1">·</span>
    <span class="inline-flex items-center gap-0.5">
        <img src={getAssetTypeIconUrl(result.asset_type)} alt="" class="w-3 h-3 object-contain"/>
        <span>{$t('assets.types.' + (result.asset_type ?? 'OTHER').toUpperCase())}</span>
    </span>
{/if}
```

**(c) Rimuovere il provider_code dalla riga inferiore** — resta solo l'icona badge sulla riga del nome.

**Import aggiuntivo necessario**: `getAssetTypeIconUrl` è già importato (riga 17 — `providerHelpers`); aggiungere anche `getAssetTypeIconUrl` da `$lib/utils/assetTypes`.

---

### Priorità 3 — Ask Provider: disabilitato + per-sezione + No Provider deduplica

#### 2.5 Bottone Ask Provider: sempre visibile, disabilitato se no provider

**File**: `frontend/src/lib/components/assets/AssetModal.svelte`

**Stato attuale** (riga 761): `{#if hasProvider}` nasconde completamente il bottone.

**Modifica**: Rendere sempre visibile ma con `disabled`:

```svelte
<!-- PRIMA: -->
{#if hasProvider}
    <button ... onclick={(e) => { e.stopPropagation(); handleAskProvider(); }} disabled={askingProvider} ...>
        ...
    </button>
{/if}

<!-- DOPO: -->
<button
    type="button"
    onclick={(e) => { e.stopPropagation(); handleAskProvider(); }}
    disabled={!hasProvider || askingProvider}
    class="... disabled:opacity-30 disabled:cursor-not-allowed ..."
    title={!hasProvider ? $t('assets.identifiers.askProviderHint') : ''}
>
    ...
</button>
```

> **Nota**: La chiave i18n `assets.identifiers.askProviderHint` esiste già (era tra le 11 "non usate").

#### 2.6 Rimuovere checkbox "No Provider" duplicato

**File**: `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte`

**Stato attuale** (righe 272-282): C'è un checkbox "No Provider" con `<Minus>` icon all'interno della sezione. Questo è duplicato perché `AssetModal.svelte` ha già lo stesso checkbox nell'header del collapsible (righe 896-914).

**Modifica**: Rimuovere l'intero blocco `<label>` con checkbox e icona Minus (righe 271-282). Rimuovere anche `handleNoProviderToggle()` (righe 192-199) e l'import di `Minus` (riga 24). Il `{#if !noProvider}` (riga 284) rimane per wrappare il contenuto.

#### 2.7 Ask Provider per sezione (bottoni specifici)

**File**: `frontend/src/lib/components/assets/AssetModal.svelte`

**Concetto**: Oltre al bottone globale nell'header "More Info", aggiungere un piccolo bottone "Ask Provider" per ogni sub-sezione (Identifiers, Sector Distribution, Geographic Distribution).

**Nota sulle operations**: Ogni bottone per-sezione chiama la probe con `operations: ['metadata']` (l'unica operazione che restituisce identifiers/classification). Il bottone globale usa anch'esso `['metadata']`. I bottoni "Test Configuration" nel ProviderAssignmentSection usano `['current_price', 'history']`. Le operations ammesse sono definite dall'enum `ProbeOperation` nel backend. I bottoni per-sezione differiscono non nella richiesta ma nel **filtraggio dei risultati**: ognuno applica solo i campi della propria sezione.

**Aggiornamento docstring backend**: La docstring dell'endpoint `POST /probe` e la description del campo `operations` in `FAProviderProbeRequest` devono generare dinamicamente la lista delle operazioni ammesse dall'enum `ProbeOperation`, così da restare sempre allineate.

**Implementazione**:


Nuove funzioni:
```typescript
/** Ask Provider for a specific section — calls same probe, applies only relevant fields */
async function handleAskProviderSection(section: 'identifiers' | 'sector' | 'geographic') {
    if (!providerCode || !providerIdentifier) return;
    askingProvider = true;
    
    try {
        const response = await zodiosApi.probe_provider_config_api_v1_assets_provider_probe_post({
            provider_code: providerCode,
            identifier: providerIdentifier,
            identifier_type: providerIdentifierType as any,
            provider_params: providerParams,
            operations: ['metadata'],
        }) as any;

        const meta = response.metadata;
        if (!meta?.success || !meta.patch_data) return;
        const pd = meta.patch_data;

        if (section === 'identifiers') {
            // Auto-fill only identifier_* fields, show toast for conflicts
            applyIdentifierFields(pd);
        } else if (section === 'sector') {
            applySectorFields(pd.classification_params);
        } else if (section === 'geographic') {
            applyGeographicFields(pd.classification_params);
        }
    } catch (e: any) {
        console.error('Ask Provider (section) failed:', e);
    } finally {
        askingProvider = false;
    }
}
```

Le funzioni helper `applyIdentifierFields()`, `applySectorFields()`, `applyGeographicFields()` usano la stessa logica di `handleAskProvider()` (vuoto → auto-fill, uguale → badge ✔, diverso → sovrascrive con toast warning) ma senza aprire la modale completa. La modale differenze (`ProviderComparisonModal`) resta esclusiva del bottone globale.

**Layout nel template** — Ogni sub-sezione header:
```svelte
<div class="flex items-center justify-between">
    <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
        {$t('assets.modal.identifiers')}
    </div>
    <div class="flex items-center gap-1.5">
        <button type="button" onclick={addIdentifierRow} 
                class="..." title="Add identifier">
            <Plus size={12}/>
        </button>
        <button type="button" onclick={() => handleAskProviderSection('identifiers')}
                disabled={!hasProvider || askingProvider}
                class="..." title="Ask Provider">
            {#if askingProvider}<Loader2 size={12} class="animate-spin"/>{:else}<RefreshCw size={12}/>{/if}
        </button>
    </div>
</div>
```

---

### Priorità 4 — Identifiers con DataTable

#### 2.8 Nuovo cell type `EditableTextCell`

**File**: `frontend/src/lib/components/table/types.ts`

Aggiungere un nuovo tipo cella per input testo inline, seguendo il pattern di `EditableNumberCell`:

```typescript
/**
 * Editable text cell — renders an inline <input type="text">.
 * Used for identifier values, names, etc.
 */
export interface EditableTextCell {
    type: 'editable-text';
    /** Current value */
    value: string;
    /** Placeholder text */
    placeholder?: string;
    /** Max length */
    maxLength?: number;
    /** Callback when value changes (blur or Enter) */
    onchange: (newValue: string) => void;
}
```

Aggiungere `EditableTextCell` all'union type `CellContent`.

**File**: `frontend/src/lib/components/table/DataTable.svelte`

Aggiungere il rendering dopo il blocco `editable-number` (~riga 1059):

```svelte
{:else if cellContent.type === 'editable-text'}
    <input
        type="text"
        class="cell-editable-text"
        value={cellContent.value}
        placeholder={cellContent.placeholder ?? ''}
        maxlength={cellContent.maxLength}
        onblur={(e) => cellContent.onchange(e.currentTarget.value)}
        onkeydown={(e) => { if (e.key === 'Enter') e.currentTarget.blur(); }}
        onclick={(e) => e.stopPropagation()}
    />
```

Stile CSS: copiare da `.cell-editable-number` ma senza `font-family: monospace` e senza `max-width: 120px` (usa `width: 100%`).

#### 2.9 Riscrivere Identifiers come DataTable

**File**: `frontend/src/lib/components/assets/AssetModal.svelte`

**Stato attuale**: 7 campi fissi in griglia 2 colonne (righe 788-841), con variabili separate `identifierIsin`, `identifierTicker`, etc.

**Nuovo design**: Una `DataTable` con righe dinamiche:

**Tipo riga**:
```typescript
interface IdentifierRow {
    id: string;           // Unique row ID (nanoid or uuid)
    type: string;         // IdentifierTypeCode ('ISIN', 'TICKER', etc.)
    value: string;        // The actual identifier value
    autoFilled?: boolean; // Badge ✔ da Ask Provider
}
```

**State**:
```typescript
let identifierRows = $state<IdentifierRow[]>([]);
```

**Colonne DataTable**:
```typescript
let identifierColumns = $derived<ColumnDef<IdentifierRow>[]>([
    {
        id: 'type',
        header: () => $t('assets.provider.identifierType'),
        type: 'custom',
        cell: (row) => ({
            type: 'custom',
            component: InlineIdentifierTypeSelect,  // wrapper attorno a SimpleSelect
            props: {
                value: row.type,
                onchange: (newType: string) => updateIdentifierRow(row.id, 'type', newType),
            },
        }),
        width: 120,
        sortable: false,
        filterable: false,
    },
    {
        id: 'value',
        header: () => $t('assets.provider.identifier'),
        type: 'custom',
        cell: (row) => ({
            type: 'editable-text',
            value: row.value,
            placeholder: 'US0378331005, AAPL, ...',
            onchange: (newVal: string) => updateIdentifierRow(row.id, 'value', newVal),
        }),
        width: 250,
        sortable: false,
        filterable: false,
    },
]);
```

**Props DataTable**:
```svelte
<DataTable
    data={identifierRows}
    columns={identifierColumns}
    getRowId={(r) => r.id}
    storageKey="asset-modal-identifiers"
    enableSelection={false}
    enablePagination={false}
    enableColumnFilters={false}
    enableSorting={false}
    enableColumnResize={false}
    enableColumnVisibility={false}
    enableActions={true}
    rowActions={identifierRowActions}
    tableLayout="auto"
/>
```

**Row actions**: Solo delete (`X` icon, variant danger).

**Componente `InlineIdentifierTypeSelect`**: Piccolo componente wrapper che renderizza un `SimpleSelect` compatto con le opzioni `IDENTIFIER_TYPES`. Può essere un semplice file o un componente inline via `CustomCell`.

**Helper di conversione backend↔frontend**:

```typescript
/** Convert DB columns (identifier_isin, identifier_ticker, ...) to table rows */
function columnsToIdentifierRows(data: AssetData): IdentifierRow[] {
    const rows: IdentifierRow[] = [];
    const mapping: [string, string][] = [
        ['ISIN', data.identifier_isin ?? ''],
        ['TICKER', data.identifier_ticker ?? ''],
        ['CUSIP', data.identifier_cusip ?? ''],
        ['SEDOL', data.identifier_sedol ?? ''],
        ['FIGI', data.identifier_figi ?? ''],
        ['UUID', data.identifier_uuid ?? ''],
        ['OTHER', data.identifier_other ?? ''],
    ];
    for (const [type, value] of mapping) {
        if (value) rows.push({ id: crypto.randomUUID(), type, value });
    }
    return rows;
}

/** Convert table rows back to DB columns for create/edit payload */
function identifierRowsToColumns(rows: IdentifierRow[]): Record<string, string | undefined> {
    const result: Record<string, string | undefined> = {};
    for (const row of rows) {
        if (!row.value.trim()) continue;
        const key = `identifier_${row.type.toLowerCase()}`;
        result[key] = row.value.trim();
    }
    return result;
}
```

**Impatto su `saveCreate()` e `saveEdit()`**: Sostituire i singoli campi `identifierIsin || undefined` con lo spread dell'helper `identifierRowsToColumns(identifierRows)`.

**Impatto su `populateFromEditData()`**: Sostituire il setting dei 7 campi singoli con `identifierRows = columnsToIdentifierRows(data)`.

**Impatto su `handleAskProvider()`**: Il loop `compareField('identifier_*', ...)` deve iterare sulle righe della tabella anziché sui singoli state variables. Adattare `setFieldValue()` per aggiornare le righe.

---

### Priorità 5 — DistributionEditor con DataTable + selettori

#### 2.10 Nuovo componente `CountrySearchSelect.svelte`

**File NUOVO**: `frontend/src/lib/components/ui/select/CountrySearchSelect.svelte`

Modellato su `CurrencySearchSelect.svelte` (~187 righe). Usa `countryStore.ts` per i dati.

**Props**:
```typescript
interface Props {
    value?: string;                    // ISO3 code (bindable)
    excludedCountries?: Set<string>;   // Hide these (already in distribution)
    placeholder?: string;
    disabled?: boolean;
    maxVisibleItems?: number;
    dropdownPosition?: 'top' | 'bottom' | 'auto';
    onchange?: (value: string) => void;
}
```

**Opzioni SearchSelect**:
```typescript
// Per ogni country da countryStore:
{
    value: country.iso3,                        // "ITA"
    label: `${country.iso3} — ${country.name}`, // "ITA — Italia"
    icon: country.flag_emoji,                    // "🇮🇹"
    searchText: `${country.iso3} ${country.iso2} ${country.name}`,
}
```

**Paesi individuali**: Ogni paese è un'opzione singola (Italia, Francia, Germania — non "Europa"). Non serve raggruppamento.

**Reload su cambio lingua**: Stessa logica di `CurrencySearchSelect` — `$effect` che osserva `$currentLanguage` e richiama `ensureCountriesLoaded(lang)`.

#### 2.11 Riscrivere DistributionEditor con DataTable

**File**: `frontend/src/lib/components/ui/input/DistributionEditor.svelte`

**Stato attuale**: 255 righe di HTML custom con grid layout, input text per add, barra visuale inline.

**Nuovo design**: Wrapper attorno a `DataTable` (come `DataEditor.svelte`).

**Tipo riga**:
```typescript
interface DistEntry {
    id: string;       // Unique row ID
    key: string;      // Sector name or ISO3 country code
    weight: number;   // 0-100 (display range)
}
```

**Colonne DataTable**:

| Column ID | Header | Cell type | Sortable |
|-----------|--------|-----------|----------|
| `key` | Sector / Country | `custom` → `SimpleSelect` (sector) o `CountrySearchSelect` (geographic) | ❌ |
| `bar` | — | `html` → `<div>` con barra gradiente proporzionale | ❌ |
| `weight` | Weight % | `editable-number` (min 0, max 100, step 0.01) | ❌ |

**Row actions**: Delete (X icon, danger variant).

**Props DataTable**: minimal — no pagination, no filters, no selection, no sorting, no column resize. `tableLayout="auto"`.

**Footer** (fuori dal DataTable, sotto):
```svelte
<div class="flex items-center justify-end gap-1.5 px-3 py-1.5 text-xs font-medium">
    <span class="text-gray-500 dark:text-gray-400">{$t('assets.distribution.total')}:</span>
    <span class="{isValid ? 'text-green-600' : isExcess ? 'text-red-500' : 'text-amber-500'} font-mono">
        {totalPercent.toFixed(2)}%
    </span>
    {#if isValid}
        <span class="text-green-500">✅</span>
    {:else if isExcess}
        <span class="text-red-500">⚠ (+{(totalPercent - 100).toFixed(2)}% {$t('assets.distribution.excess')})</span>
    {:else if isMissing}
        <span class="text-amber-500">⚠ ({(100 - totalPercent).toFixed(2)}% {$t('assets.distribution.missing')})</span>
    {/if}
</div>
```

**Barra visuale** (cella `html`):
```typescript
cell: (row) => ({
    type: 'html',
    html: `<div class="h-3 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
        <div class="h-full rounded-full transition-all ${validClass}" 
             style="width: ${Math.min(100, (row.weight / maxWeight) * 100)}%"></div>
    </div>`,
}),
```

> **Nota**: `validClass` viene calcolato come `isValid ? 'bg-libre-green' : isExcess ? 'bg-red-400' : 'bg-amber-400'`.

**Selettore per sector** (cella `custom` quando `kind='sector'`):
```typescript
// SimpleSelect con le 12 opzioni settori
cell: (row) => ({
    type: 'custom',
    component: InlineSectorSelect,
    props: {
        value: row.key,
        excludeKeys: entries.filter(e => e.id !== row.id).map(e => e.key),
        onchange: (newKey: string) => updateEntryKey(row.id, newKey),
    },
}),
```

`InlineSectorSelect`: SimpleSelect con opzioni derivate da `SECTOR_KEYS.map(k => ({ value: k, label: $t('sectors.' + k) }))`. Esclude le chiavi già usate nelle altre righe.

**Selettore per geographic** (cella `custom` quando `kind='geographic'`):
```typescript
cell: (row) => ({
    type: 'custom',
    component: CountrySearchSelect,
    props: {
        value: row.key,
        excludedCountries: new Set(entries.filter(e => e.id !== row.id).map(e => e.key)),
        onchange: (newKey: string) => updateEntryKey(row.id, newKey),
        maxVisibleItems: 4,
        dropdownPosition: 'auto',
    },
}),
```

**Conversione 0-1 ↔ 0-100**: Rimane invariata — riceve da prop `value` in 0-1, converte a 0-100 per le righe interne, emette `onchange()` in 0-1.

#### 2.12 Layout sezione con titolo + azioni inline

**File**: `frontend/src/lib/components/assets/AssetModal.svelte`

Pattern per ogni sub-sezione dentro "More Info":

```
┌─────────────────────────────────────────────────────────┐
│ IDENTIFIERS                         [+ Add] [🔄 Ask]   │
│ ┌───────────────────────────────────────────────────┐   │
│ │ Type      │ Identifier     │ Actions              │   │
│ ├───────────┼────────────────┼──────────────────────│   │
│ │ [ISIN ▾]  │ [US0378331005] │ [✕]                  │   │
│ │ [TICKER▾] │ [AAPL       ✔] │ [✕]                  │   │
│ └───────────────────────────────────────────────────┘   │
│                                                          │
│ SECTOR DISTRIBUTION                 [+ Add] [🔄 Ask]   │
│ ┌───────────────────────────────────────────────────┐   │
│ │ Sector        │ Bar          │ Weight% │ Actions   │   │
│ ├───────────────┼──────────────┼─────────┼──────────│   │
│ │ [Technology▾] │ ████████████ │ [90.00] │ [✕]      │   │
│ │ [Other     ▾] │ ██           │ [10.00] │ [✕]      │   │
│ └───────────────────────────────────────────────────┘   │
│                              Total: 100.00% ✅          │
│                                                          │
│ GEOGRAPHIC DISTRIBUTION             [+ Add] [🔄 Ask]   │
│ ┌───────────────────────────────────────────────────┐   │
│ │ Country       │ Bar          │ Weight% │ Actions   │   │
│ ├───────────────┼──────────────┼─────────┼──────────│   │
│ │ [🇺🇸 USA    ▾] │ ██████████   │ [60.00] │ [✕]      │   │
│ │ [🇨🇳 CHN    ▾] │ ██████       │ [30.00] │ [✕]      │   │
│ └───────────────────────────────────────────────────┘   │
│                              Total: 90.00% ⚠(10% miss) │
└─────────────────────────────────────────────────────────┘
```

Il bottone globale "Ask Provider" nell'header del collapsible "More Info" rimane per il flusso completo con modale differenze.

---

### Priorità 6 — Infrastruttura e pulizia

#### 2.13 i18n: chiavi non usate

Le 11 chiavi segnalate dall'audit:

| Chiave | Decisione | Motivo |
|--------|-----------|--------|
| `assets.identifiers.askProviderHint` | **Tenere** | Usata nel tooltip del bottone disabilitato (step 2.5) |
| `assets.identifiers.autoFilled` | **Tenere** | Prevista per tooltip badge ✔ |
| `assets.identifiers.conflictWarning` | **Tenere** | Prevista per toast dei bottoni per-sezione |
| `assets.probe.cacheInfo` | **Tenere** | Prevista per tooltip info nei test results |
| `assets.probe.executionTime` | **Tenere** | Prevista per dettaglio test |
| `assets.probe.failed` | **Tenere** | Prevista per badge stato |
| `assets.probe.metadata` | **Tenere** | Prevista per label operazione metadata |
| `assets.probe.passed` | **Tenere** | Prevista per badge stato |
| `assets.provider.fetchInterval` | **Tenere** | Prevista per campo fetch interval nel modale |
| `assets.provider.lastFetch` | **Tenere** | Prevista per label data ultimo fetch |
| `assets.provider.neverFetched` | **Tenere** | Prevista per stato "mai eseguito" |

→ **Nessuna rimozione.** Tutte le chiavi saranno usate entro i prossimi 2 step.

#### 2.14 Nuove chiavi i18n necessarie

| Chiave | EN | IT |
|--------|----|----|
| `assets.identifiers.askProviderSection` | Ask Provider | Chiedi al Provider |
| `assets.identifiers.addIdentifier` | Add identifier | Aggiungi identificativo |
| `assets.distribution.addEntry` | Add | Aggiungi |

(Aggiungere FR e ES per tutte)

---

## 3. Componenti nuovi da creare

| Componente | Path | Righe stimate | Descrizione |
|------------|------|---------------|-------------|
| `CountrySearchSelect.svelte` | `frontend/src/lib/components/ui/select/` | ~150 | Selettore paese con search, flag emoji, da countryStore |
| `InlineIdentifierTypeSelect.svelte` | `frontend/src/lib/components/assets/` | ~40 | Wrapper compatto di SimpleSelect per identifier type |
| `InlineSectorSelect.svelte` | `frontend/src/lib/components/assets/` | ~50 | Wrapper compatto di SimpleSelect per settori i18n |

---

## 4. File da modificare

| File | Tipo modifica | Task |
|------|---------------|------|
| `backend/app/services/asset_source.py` | Fix bug | 2.1, 2.2 |
| `Pipfile` | Aggiunta dipendenza | 2.3 |
| `AssetSearchAutocomplete.svelte` | UX improvement | 2.4 |
| `AssetModal.svelte` | Ristrutturazione major | 2.5, 2.7, 2.9, 2.12 |
| `ProviderAssignmentSection.svelte` | Rimozione duplicato | 2.6 |
| `table/types.ts` | Nuovo cell type | 2.8 |
| `table/DataTable.svelte` | Rendering nuovo tipo | 2.8 |
| `DistributionEditor.svelte` | Riscrittura completa | 2.11 |
| i18n JSON (4 file) | Nuove chiavi | 2.14 |

---

## 5. Ordine di implementazione consigliato

1. **2.1 + 2.2 + 2.3** — Fix backend (15 min) → Sblocca Ask Provider
2. **2.4** — Risultati ricerca allineati (20 min) → UX immediata
3. **2.5 + 2.6** — Ask Provider disabilitato + deduplica checkbox (15 min)
4. **2.8** — `EditableTextCell` in DataTable (15 min) → Pre-requisito per tabelle
5. **2.10** — `CountrySearchSelect` (45 min) → Pre-requisito per DistributionEditor
6. **2.11** — DistributionEditor con DataTable (1h 30min) → Riscrittura completa
7. **2.9** — Identifiers con DataTable (1h 30min) → Riscrittura + helper conversione
8. **2.7** — Ask Provider per sezione (45 min) → Logica sezione-specifica
9. **2.12** — Layout sezioni con titolo + azioni (30 min) → Polish finale
10. **2.14** — i18n nuove chiavi (10 min)

**Stima totale**: ~6h

---

## 6. Verifiche post-implementazione

### Backend
```bash
./dev.py test -v api run          # Endpoint SSE funziona
./dev.py test -v services run     # search_stream serializza correttamente
./dev.py test -v db populate      # Mock data popola senza errori
```

### Frontend
```bash
./dev.py front check              # 0 errori svelte-check
./dev.py test front run           # Test frontend passano
./dev.py i18n audit               # 0 chiavi non usate (o solo quelle deliberatamente tenute)
```

### Manuale
- [ ] Cercare "Apple" → risultati mostrano icona tipo + label tradotta + badge provider vicino al nome
- [ ] Cercare "MSCI" → tipo INDEX mostrato correttamente con icona index.png
- [ ] Selezionare un risultato → Ask Provider (disabilitato inizialmente, abilitato dopo selezione)
- [ ] Click "Ask Provider" globale → modale differenze se conflitti
- [ ] Click "Ask Provider" sezione Identifiers → auto-filla solo identificatori
- [ ] Click "Ask Provider" sezione Sector → auto-filla solo distribuzione settoriale
- [ ] Tabella Identifiers: add/remove righe, select tipo, edit valore
- [ ] Tabella Distribuzione: add settore/paese con selettore, edit peso, barra visuale, badge totale
- [ ] No Provider checkbox nell'header → sezione collassa, bottone Ask Provider grigio
- [ ] Save create → payload contiene `identifier_isin`, `identifier_ticker` (da conversione righe)

---

## 7. Decisioni architetturali

### DataTable per tabelle piccole (3-10 righe) — perché?
- **Consistenza**: Stesso look&feel di tutte le tabelle dell'app
- **Riutilizzabilità**: Cell types (`editable-number`, `editable-text`, `custom`) disponibili ovunque
- **Row actions**: Delete con conferma già pronto
- **Dark mode**: Gestito centralmente nel CSS di DataTable

Disabilitando pagination, filters, selection, sorting, resize → il DataTable si riduce a una tabella pulita con solo rendering celle + actions.

### Backend: colonne fisse vs array identifier
Il backend mantiene le colonne fisse (`identifier_isin`, `identifier_ticker`, …). La conversione righe↔colonne avviene solo nel frontend. Questo evita:
- Migrazione schema DB
- Modifica di tutti gli endpoint CRUD
- Impatto su Zodios types

Se in futuro servisse un modello più flessibile (N identifier arbitrari), si valuta un campo JSON `identifiers: [{type, value}]`.

### Ask Provider: globale vs per-sezione
- **Globale** (nell'header "More Info"): chiama probe, confronta TUTTI i campi, apre modale differenze per conflitti
- **Per-sezione** (accanto al titolo): chiama la stessa probe, ma applica solo i campi della sezione corrente. Conflitti → sovrascrive con toast warning (no modale). Utile per "aggiorna veloce solo gli identifier".

### Cache streaming search
Rimandato a un ticket dedicato (Round 3). Richiede:
- Cache centralizzata in `AssetSearchService` con chiave query
- Fuzzy matching frontend sui risultati precedenti
- Invalidazione TTL
Non è un quick fix e non è bloccante per i task di questo round.

