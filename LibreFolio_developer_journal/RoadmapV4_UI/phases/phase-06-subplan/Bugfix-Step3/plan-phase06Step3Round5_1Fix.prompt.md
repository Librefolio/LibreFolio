# Plan: Phase 6 Step 3 — Round 5.1 Fix (post-testing + audit)

Aggiornamento post-testing manuale (Round 5) + audit completo di tutti i piani Step 3.
Include: 9 fix originali, 8 aree di codice sporco/duplicato, 1 feature mancante (fetch_interval UI).

---

## Stato reale dei 9 punti dopo testing utente

| # | Problema | Stato Round 5 | Stato Reale (post-test) | Azione Round 5.1 |
|---|----------|---------------|------------------------|-------------------|
| 1 | Search compila solo campi base | `autoFetchMetadata()` silenzioso | ⚠️ **Parziale** — `autoFetchMetadata()` è una funzione separata silenziosa che NON mostra toast quando i dati mancano. Non chiama il path globale. | Fix: rimuovere `autoFetchMetadata()`, chiamare `handleAskProvider()` dopo search selection |
| 2 | Impossibile rimuovere l'icona | Bottone ✕ + "Remove Image" rosso | ⚠️ **Parziale** — La ✕ nell'URL funziona, ma compare un bottone strano al centro e la modale non si chiude. | Fix: semplificare, assicurare URL vuoto → `null` → fallback icon. Rimuovere bottone "Remove Image". |
| 3 | Nessun feedback se distribuzioni assenti | Toast per "Ask Provider" globale | ⚠️ **Parziale** — Toast doppio (info + success) quando i dati non ci sono. | Fix: sopprimere toast success quando si mostrano toast info per dati mancanti. |
| 4 | 100.05% segnato come ✅ | Tolleranza da 0.05 a 0.01 | ⚠️ **Quasi** — 100.01% ancora accettato. | Fix: tolleranza `0.005`, display 2 decimali, validazione `Math.abs(total - 100) < 0.005` |
| 5 | Ribilanciamento | ✅ Già funzionante | ✅ **Confermato** | — |
| 6 | Nessuna paginazione | ✅ Già funzionante | ✅ **Confermato** | — |
| 7 | Z-index tendine | ✅ Già funzionante | ✅ **Confermato** | — |
| 8 | "Other" non ammesso in geographic | Frontend OK. Backend `normalize_country_keys` OK. | ⚠️ **Provider NO** — JustETF `_country_name_to_iso3()` ritorna `None` per "other" → riga 354 lo scarta. | Fix: ritornare `"Other"` (truthy) anziché `None` |
| 9 | Tooltip history senza valori | Tabella HTML per current price | ⚠️ **Parziale** — History mostra solo `points_count` + `date_range`. Current price ha ~10 decimali. `sample_prices` MAI aggiunto al backend. | Fix: aggiungere `sample_prices` allo schema + service, arrotondare current price a 2 decimali |

---

## Codice sporco / duplicato (audit)

| ID | File | Problema | Azione |
|----|------|----------|--------|
| C1 | `AssetModal.svelte` (righe 535-725) | `handleAskProvider()` e `handleAskProviderSection()` contengono ~190 righe di logica quasi identica: stesso probe call, stessa iterazione su `IDENTIFIER_TYPES`, stessa comparazione sector/geo. Copia-incolla puro. | **Estrarre** `fetchAndCompareMetadata(scope: 'all' \| 'identifiers' \| 'sector' \| 'geographic')` — una sola funzione che probe+compara i campi filtrati per scope e ritorna `{differences, autoFilled, missingFields}`. Le 3 funzioni (`handleAskProvider`, `handleAskProviderSection`, `autoFetchMetadata`) diventano wrapper sottili o spariscono. |
| C2 | `AssetModal.svelte` (righe 451-530) | `autoFetchMetadata()` è ridondante: fa lo stesso probe + stessa logica campi di `handleAskProvider()`, ma in versione "silent". Se si unifica la logica (C1), questa funzione sparisce. | **Rimuovere** — sostituita dalla funzione unificata (C1) |
| C3 | `assetTypes.ts` (riga 96) | `export const SECTOR_KEYS = SECTOR_KEYS_FALLBACK` è marcato `@deprecated` ma nessuno lo importa. Codice morto. | **Rimuovere** l'export deprecated |
| C4 | i18n | 10 chiavi unused: 1 ora usata (`fetchInterval` — vedi Feature F1), 9 riservate per Step 4 detail page (`autoFilled`, `conflictWarning`, `cacheInfo`, `executionTime`, `failed`, `metadata`, `passed`, `lastFetch`, `neverFetched`). | **Annotare** le 9 restanti come "reserved for Step 4". `fetchInterval` viene usata in questo round. |
| C5 | `ProviderAssignmentSection.svelte` (riga 420-435) | `<select>` HTML nativo per `params_schema` campi di tipo `select` (riguarda `css_scraper` campo `decimal_format`). Inconsistente col design system che usa `SimpleSelect` ovunque. | **Sostituire** `<select>` nativo con `SimpleSelect` compatto. |
| C6 | `AssetModal.svelte` (righe 339, 349) | `initialSnapshot` è costruito con `JSON.stringify([...fields...])` in due punti separati (`resetForm()` e `populateFromEditData()`) con liste di campi leggermente diverse. Fragile — se si aggiunge un campo, bisogna ricordarsi di aggiornare entrambi. | **Estrarre** helper `buildFormSnapshot(): string` usato da entrambi. |
| C7 | `AssetModal.svelte` (riga 186) | `columnsToIdentifierRows()` itera su tutti i 7 `IDENTIFIER_TYPES` per trovare quelli non vuoti. Pattern verboso ma non rotto. | **Minor** — potrebbe usare `Object.entries(data).filter(...)` ma non critico. Lasciare. |
| C8 | `AssetModal.svelte` (righe 834, 892) | `fetch_interval: 1440` hardcodato in entrambi i payload `saveCreate()` e `saveEdit()`. Nessun campo UI per configurarlo. | **Collegato a Feature F1** — il valore deve venire da uno state `fetchInterval` bindato alla UI. |

---

## Feature mancante

### F1 — Campo `fetch_interval` nella sezione Provider

**Problema**: Il backend supporta `fetch_interval` su `FAProviderAssignmentItem` (default 1440 min = 24h), il DB lo persiste, la chiave i18n `assets.provider.fetchInterval` esiste già ma è segnalata come unused. Nella modale però il valore è hardcodato a `1440` nei payload di save (righe 834, 892) e **non esiste nessun campo UI** per modificarlo.

Il `fetch_interval` sarà usato dall'auto-sync job (implementato in step futuri) per decidere ogni quanto aggiornare i prezzi di un asset dal provider. È essenziale poterlo configurare fin da ora.

**Soluzione**:

1. **Nuovo state** in `AssetModal.svelte`:
   ```typescript
   let fetchInterval = $state(1440); // default 24h in minutes
   ```

2. **Populate in edit mode** — `populateFromEditData()`:
   ```typescript
   fetchInterval = data.fetch_interval ?? 1440;
   ```

3. **Reset** — `resetForm()`:
   ```typescript
   fetchInterval = 1440;
   ```

4. **Campo UI** — nella `ProviderAssignmentSection`, dopo Identifier e prima delle URL:
   ```
   ┌──────────────────────────────────────────────────────────┐
   │  Provider   [yfinance ▾]     ID Type [TICKER ▾]         │
   │  Identifier [AAPL                                    ]  │
   │                                                          │
   │  Fetch Interval (min) *   [1440              ]          │
   │  ⓘ How often the auto-sync job refreshes prices.        │
   │     Common: 1440 (24h), 60 (1h), 10080 (weekly)        │
   │                                                          │
   │  User URL   [https://...]     Provider URL [...]        │
   └──────────────────────────────────────────────────────────┘
   ```

5. **Prop** in `ProviderAssignmentSection`:
   ```typescript
   fetchInterval?: number;  // bindable
   ```

6. **Payload save** — `saveCreate()` e `saveEdit()` usano lo state:
   ```typescript
   fetch_interval: fetchInterval,
   ```

7. **Include nel dirty tracking** — aggiungere `fetchInterval` alla `buildFormSnapshot()` (vedi C6).

8. **Chiave i18n** — `assets.provider.fetchInterval` già esiste e non sarà più "unused".

**File coinvolti**:
- `frontend/src/lib/components/assets/AssetModal.svelte` — state, populate, reset, payload, dirty
- `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte` — nuovo campo UI con input number

---

## Dettaglio Fix Round 5.1

### Fix 1 — Search selection → auto-ask provider globale + rimozione autoFetchMetadata (collegato C1+C2)

**Problema**: `applySearchResult()` chiama `autoTriggerProbe()` + `autoFetchMetadata()` come funzioni separate. `autoFetchMetadata()` è un silent fill che non mostra toast quando i dati mancano. Il piano diceva di chiamare direttamente `handleAskProvider()` globale ma non è stato fatto.

**Soluzione**: Dopo la ristrutturazione C1+C2:
1. `applySearchResult()` chiama `autoTriggerProbe()` + `handleAskProvider()` (il globale)
2. `autoFetchMetadata()` viene **eliminata** — la logica è incorporata nella funzione unificata
3. `handleAskProvider()` gestisce sia il caso "prima compilazione" (auto-fill per campi vuoti) che il caso "confronto" (comparison modal per conflitti)

**Flusso post-fix**:
```
Search Select → applySearchResult()
  ├── Compila: name, type, currency, identifier, provider fields
  ├── autoTriggerProbe() → test current_price + history
  └── handleAskProvider() → probe metadata
       ├── Campi vuoti → auto-fill silenzioso
       ├── Campi diversi → comparison modal
       ├── Sector/geo assenti → toast info (blu)
       └── Tutto OK → toast success (verde)
```

**File coinvolti**: `frontend/src/lib/components/assets/AssetModal.svelte`

---

### Fix 2 — Rimozione icona: semplificare + fallback in AssetIcon

**Problema**: Il flusso "Remove Image" ha un bottone strano al centro e la modale non si chiude.

**Soluzione**:
1. La ✕ nel campo URL dell'AssetPickerModal è sufficiente — svuota il campo
2. Rimuovere il bottone "Remove Image" rosso aggiunto in Round 5 (confonde)
3. In `AssetPickerModal.svelte`, quando l'utente clicca "Confirm/Select" con URL vuoto, dispatchare `select` con `url: ''`
4. In `AssetModal.handleImagePickerChange(url)`: se `url === ''` → settare `iconUrl = null`
5. Verificare che `AssetIcon` con `iconUrl=null` mostri correttamente il fallback (chain: iconUrl → PNG per assetType → BarChart3 Lucide)

**File coinvolti**:
- `frontend/src/lib/components/ui/media/AssetPickerModal.svelte` — rimuovere bottone "Remove Image"
- `frontend/src/lib/components/assets/AssetModal.svelte` — handler URL vuoto → null

---

### Fix 3 — Toast coerenti: no doppio toast quando dati assenti

**Problema**: Quando si clicca "Ask Provider" e il provider non ha dati, compaiono 2 toast: info (blu) + success (verde). Confusionario.

**Soluzione**:
1. Se il provider NON ha dati per i campi richiesti → mostrare SOLO toast info (blu)
2. Se il provider HA dati → mostrare SOLO toast success (verde) o aprire comparison modal
3. Mai entrambi contemporaneamente per la stessa operazione
4. Nella funzione unificata (C1): la variabile `missingFields` diventa il discriminante — se non vuota, toast info solo; se vuota + nessun diff, toast success.

**File coinvolti**: `frontend/src/lib/components/assets/AssetModal.svelte` — logica toast nella funzione unificata

---

### Fix 4 — Tolleranza distribuzione: esattamente 100.00%

**Problema**: 100.01% è ancora accettato.

**Soluzione**:
1. **Tolleranza validazione**: `Math.abs(total - 100) < 0.005` (±0.005% — copre errori floating point senza ammettere 100.01%)
2. **Display pesi**: 2 decimali (`XX.XX%`) — coerente con backend (4 decimali raw 0.xxxx → 2 decimali percentuale)
3. **`emitChange()`**: arrotonda a 4 decimali raw → `Number((weight / 100).toFixed(4))` (già presente)
4. **Celle editable**: `step={0.01}`, max 2 decimali visualizzati

**File coinvolti**: `frontend/src/lib/components/ui/input/DistributionEditor.svelte`

---

### Fix 5 — Ribilanciamento ✅ CONFERMATO

Nessuna azione.

---

### Fix 6 — Paginazione ✅ CONFERMATO

Nessuna azione.

---

### Fix 7 — Z-index ✅ CONFERMATO

Nessuna azione.

---

### Fix 8 — JustETF provider: preservare "Other" nella distribuzione geografica

**Problema**: `_country_name_to_iso3()` ritorna `None` per "other" → riga 354 `if iso3:` lo scarta.

**Soluzione**:

```python
# justetf.py — _country_name_to_iso3():
def _country_name_to_iso3(country_name: str) -> Optional[str]:
    if country_name.lower() == "other":
        return "Other"  # Preserve "Other" as-is (normalize_country_keys handles it)
    try:
        from backend.app.utils.geo_utils import normalize_country_to_iso3
        return normalize_country_to_iso3(country_name)
    except (ValueError, ImportError) as e:
        logger.debug(f"Could not normalize country '{country_name}': {e}")
        return None
```

La riga 354 (`if iso3:`) continua a funzionare perché `"Other"` è truthy.

**Verifica**: testare con `IE00B0M63177` che ha "Other" nei paesi.

**File coinvolti**: `backend/app/services/asset_source_providers/justetf.py`

---

### Fix 9 — Probe history: aggiungere `sample_prices` + arrotondare prezzo

**Problema**:
- History mostra solo `points_count` + `date_range`, nessun valore reale
- Current price nel tooltip ha ~10 decimali
- Il campo `sample_prices` non esiste nello schema backend

**Soluzione Backend**:

**a) Schema** — `backend/app/schemas/provider.py`:
```python
class ProbeHistoryResult(BaseProbeOperationResult):
    """Result of history probe operation."""
    points_count: Optional[int] = Field(None, description="Number of price points found")
    date_range: Optional[str] = Field(None, description="Date range of found data (start → end)")
    sample_prices: Optional[list[dict]] = Field(
        None,
        description="Sample price points [{date: str, close: float}], max 10"
    )
```

**b) Service** — `backend/app/services/asset_source.py` in `_probe_history()`:
```python
# Dopo aver ottenuto `points`:
sample = None
if points:
    sample = [
        {"date": str(p.date), "close": round(float(p.close), 2)}
        for p in points[:10]
    ]
return ProbeHistoryResult(
    success=True, points_count=len(points), date_range=date_range_str,
    sample_prices=sample,
    execution_time_ms=...,
)
```

**c) Rigenerare client zodios** (`./dev.py api sync`)

**Soluzione Frontend**:

**d) Tooltip history** — usare `sample_prices` dalla response per costruire la tabella HTML
**e) Tooltip current price** — arrotondare a 2 decimali: `Number(value).toFixed(2)`

**File coinvolti**:
- `backend/app/schemas/provider.py` — aggiungere `sample_prices`
- `backend/app/services/asset_source.py` — popolare `sample_prices` in `_probe_history()`
- `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte` — tooltip
- Rigenerazione `generated.ts`

---

## Refactoring C1+C2 — Dettaglio funzione unificata

### Nuova funzione: `fetchAndCompareMetadata()`

```typescript
/**
 * Unified metadata fetch + comparison logic.
 * Used by: handleAskProvider() [global], handleAskProviderSection() [per-section],
 *          and applySearchResult() [auto after search].
 *
 * @param scope Which fields to compare. 'all' = everything, others = section-specific.
 * @returns void — side effects: sets state, shows toast or opens comparison modal.
 */
async function fetchAndCompareMetadata(
    scope: 'all' | 'identifiers' | 'sector' | 'geographic'
) {
    if (!providerCode || !providerIdentifier) return;
    askingProvider = true;
    autoFilledFields = new Set();

    try {
        const response = await zodiosApi.probe_provider_config_api_v1_assets_provider_probe_post({
            provider_code: providerCode,
            identifier: providerIdentifier,
            identifier_type: providerIdentifierType as any,
            provider_params: providerParams,
            operations: ['metadata'],
        }) as any;

        const meta = response.metadata;
        if (!meta?.success || !meta.patch_data) {
            toasts.info($t('assets.identifiers.askProviderHint') + ' — no data from provider');
            return;
        }
        const pd = meta.patch_data;
        const differences: DiffItem[] = [];
        const missingFields: string[] = [];

        // --- IDENTIFIERS (scope 'all' or 'identifiers') ---
        if (scope === 'all' || scope === 'identifiers') {
            for (const idType of IDENTIFIER_TYPES) {
                const dbKey = `identifier_${idType.toLowerCase()}`;
                const provVal = pd[dbKey];
                if (provVal) {
                    const currentVal = getIdentifierByType(idType);
                    if (!currentVal) {
                        setFieldValue(dbKey, provVal);
                        autoFilledFields = new Set([...autoFilledFields, dbKey]);
                    } else if (currentVal !== provVal) {
                        differences.push({field: dbKey, label: idType, type: 'string',
                            currentValue: currentVal, providerValue: provVal, selected: true});
                    }
                }
            }
        }

        // --- ASSET DETAILS (scope 'all' only) ---
        if (scope === 'all') {
            compareStringField(differences, 'display_name', $t('common.name'), displayName, pd.display_name);
            compareStringField(differences, 'asset_type', $t('assets.type'), assetType, pd.asset_type);
            compareStringField(differences, 'currency', $t('common.currency'), currency, pd.currency);
        }

        // --- CLASSIFICATION: description, sector, geographic ---
        const cpData = pd.classification_params;

        if (scope === 'all') {
            if (cpData?.short_description)
                compareStringField(differences, 'short_description', 'Description',
                    shortDescription, cpData.short_description);
        }

        if (scope === 'all' || scope === 'sector') {
            if (cpData?.sector_area) {
                const provDist = cpData.sector_area.distribution ?? cpData.sector_area;
                compareDistribution(differences, 'sector_area',
                    $t('assets.modal.sectorDistribution'), sectorDistribution, provDist);
            } else {
                missingFields.push($t('assets.modal.sectorDistribution'));
            }
        }

        if (scope === 'all' || scope === 'geographic') {
            if (cpData?.geographic_area) {
                const provDist = cpData.geographic_area.distribution ?? cpData.geographic_area;
                compareDistribution(differences, 'geographic_area',
                    $t('assets.modal.geographicDistribution'), geographicDistribution, provDist);
            } else {
                missingFields.push($t('assets.modal.geographicDistribution'));
            }
        }

        // --- RESULTS ---
        if (missingFields.length > 0) {
            toasts.info($t('assets.comparison.noDistributionData',
                {values: {fields: missingFields.join(', ')}}));
        }

        if (differences.length > 0) {
            comparisonDifferences = differences;
            showComparisonModal = true;
        } else if (missingFields.length === 0) {
            // Only show success if nothing was missing
            toasts.success($t('assets.comparison.allMatch'));
        }
        // If missingFields > 0 and no differences → only info toast shown (no success)

    } catch (e: any) {
        console.error(`Ask Provider (${scope}) failed:`, e);
    } finally {
        askingProvider = false;
    }
}

/** Compare a string field — auto-fill if empty, diff if different, skip if same */
function compareStringField(
    diffs: DiffItem[], field: string, label: string,
    currentVal: string, providerVal: string | null | undefined
) {
    if (!providerVal) return;
    if (!currentVal) {
        setFieldValue(field, providerVal);
        autoFilledFields = new Set([...autoFilledFields, field]);
    } else if (currentVal === providerVal) {
        autoFilledFields = new Set([...autoFilledFields, field]);
    } else {
        diffs.push({field, label, type: 'string',
            currentValue: currentVal, providerValue: providerVal, selected: true});
    }
}

/** Compare a distribution — auto-fill if empty, diff if different, skip if same */
function compareDistribution(
    diffs: DiffItem[], field: string, label: string,
    currentDist: Record<string, number>, providerDist: Record<string, number>
) {
    const hasCurrent = Object.keys(currentDist).length > 0;
    if (!hasCurrent) {
        if (field === 'sector_area') sectorDistribution = providerDist;
        else geographicDistribution = providerDist;
        autoFilledFields = new Set([...autoFilledFields, field]);
    } else if (JSON.stringify(currentDist) !== JSON.stringify(providerDist)) {
        diffs.push({field, label, type: 'distribution',
            currentValue: currentDist, providerValue: providerDist, selected: true});
    } else {
        autoFilledFields = new Set([...autoFilledFields, field]);
    }
}
```

Poi i wrapper diventano:
```typescript
function handleAskProvider() { fetchAndCompareMetadata('all'); }
function handleAskProviderSection(s) { fetchAndCompareMetadata(s); }
// autoFetchMetadata() → ELIMINATA, applySearchResult() chiama handleAskProvider()
```

**Riduzione stimata**: da ~280 righe a ~100 righe.

---

## Refactoring C6 — Helper `buildFormSnapshot()`

```typescript
function buildFormSnapshot(): string {
    return JSON.stringify([
        displayName, currency, assetType, iconUrl,
        JSON.stringify(identifierRows.map(r => [r.type, r.value])),
        shortDescription,
        JSON.stringify(sectorDistribution),
        JSON.stringify(geographicDistribution),
        providerCode, providerIdentifier, providerIdentifierType,
        providerNoProvider, fetchInterval,
    ]);
}
```

Usato in `resetForm()`, `populateFromEditData()`, e nel `$derived` di `currentSnapshot`.

---

## Refactoring C5 — SimpleSelect per params_schema select fields

**File**: `ProviderAssignmentSection.svelte` (riga 420-435)

Sostituire:
```svelte
<select id="param-{field.key}" ...>
    {#each field.options as opt}
        <option value={opt}>{opt}</option>
    {/each}
</select>
```

Con:
```svelte
<SimpleSelect
    value={paramsValues[field.key] ?? field.default ?? ''}
    options={field.options.map(o => ({value: o, label: o}))}
    disabled={disabled || readonly}
    dropdownPosition="auto"
    onchange={(v) => handleParamChange(field.key, v)}
/>
```

---

## Ordine di esecuzione consigliato

| # | Fix | Tipo | Effort |
|---|-----|------|--------|
| 1 | **C1+C2** — Funzione unificata `fetchAndCompareMetadata()` | Refactoring | 45 min |
| 2 | **Fix 1** — Search → handleAskProvider (dipende da C1+C2) | Bug fix | 10 min |
| 3 | **Fix 3** — Toast coerenti (incorporato in C1+C2) | Bug fix | 0 min (già nel refactoring) |
| 4 | **C6** — Helper `buildFormSnapshot()` | Refactoring | 10 min |
| 5 | **F1 + C8** — Campo `fetchInterval` nella UI + rimozione hardcode | Feature | 20 min |
| 6 | **Fix 8** — JustETF "Other" nei paesi | Bug fix backend | 5 min |
| 7 | **Fix 9a-c** — `sample_prices` backend + regen client | Feature backend | 20 min |
| 8 | **Fix 4** — Tolleranza distribuzione 0.005 | Bug fix | 5 min |
| 9 | **Fix 2** — Rimozione icona semplificata | Bug fix | 10 min |
| 10 | **Fix 9d-e** — Tooltip con sample_prices (dipende da 9a-c) | Frontend | 10 min |
| 11 | **C3** — Rimuovere `SECTOR_KEYS` deprecated | Cleanup | 2 min |
| 12 | **C5** — SimpleSelect per params_schema select | Cleanup | 10 min |

**Tempo totale stimato**: ~2.5 ore

---

## Note su chiavi i18n

| Chiave | Stato | Destinazione |
|--------|-------|-------------|
| `assets.provider.fetchInterval` | ✅ Usata in F1 | `ProviderAssignmentSection.svelte` |
| `assets.identifiers.autoFilled` | Reserved Step 4 | Detail page — badge "auto-filled by provider" |
| `assets.identifiers.conflictWarning` | Reserved Step 4 | Detail page — warning conflitto |
| `assets.probe.cacheInfo` | Reserved Step 4 | Detail page — info cache provider |
| `assets.probe.executionTime` | Reserved Step 4 | Detail page — tempo esecuzione |
| `assets.probe.failed` | Reserved Step 4 | Detail page — stato failed |
| `assets.probe.metadata` | Reserved Step 4 | Detail page — tab metadata |
| `assets.probe.passed` | Reserved Step 4 | Detail page — stato passed |
| `assets.provider.lastFetch` | Reserved Step 4 | Detail page — ultimo fetch |
| `assets.provider.neverFetched` | Reserved Step 4 | Detail page — mai fetched |

---

## Validation Checklist

- [ ] `npx svelte-check --threshold error` → 0 errors
- [ ] `pytest` backend tests pass
- [ ] `./dev.py i18n audit` → chiave `fetchInterval` non più unused (9 unused restanti: reserved Step 4)
- [ ] `./dev.py api sync` completato (per sample_prices)
- [ ] Manuale: search selection → auto-popola identifiers + distributions + toast info se mancanti
- [ ] Manuale: ✕ su URL icona → salva → fallback icon visibile (no bottone strano)
- [ ] Manuale: Ask Provider senza dati → solo toast info (blu), NO toast success (verde)
- [ ] Manuale: 100.01% → ⚠️ non valido, 100.00% → ✅ valido
- [ ] Manuale: IE00B0M63177 → distribuzione geografica include "Other"
- [ ] Manuale: tooltip history → tabella con date e prezzi reali
- [ ] Manuale: tooltip current price → prezzo con 2 decimali
- [ ] Manuale: fetch_interval editabile nella sezione Provider (default 1440)
- [ ] Manuale: modifica fetch_interval → dirty tracking funziona
- [ ] Code review: nessuna logica duplicata tra handleAskProvider / handleAskProviderSection
- [ ] Code review: `autoFetchMetadata()` rimossa
- [ ] Code review: `SECTOR_KEYS` deprecated export rimosso
- [ ] Code review: `params_schema` select usa SimpleSelect
