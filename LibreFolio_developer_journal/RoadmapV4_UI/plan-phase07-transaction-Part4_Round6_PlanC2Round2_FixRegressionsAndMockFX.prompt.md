# Plan: C2 Round 2 — Fix regressions + MockFX + Rimozione auto-populate + Test

**Origine**: Piano C2 Round 2 — consenso raggiunto in chat. Rimuovere l'auto-populate implicito da `bulk_assign_providers()`, creare MockFX providers per test deterministici, applicare 4 fix frontend/backend puntuali, aggiungere test backend FX fallback e E2E asset classification. Il flusso metadata diventa esclusivamente frontend-driven: probe → diff modal → PATCH esplicito.

**Link back**: `plan-phase07-transaction-Part4_Round6_PlanC2_BugfixAndPairValidation.prompt.md` (parent plan)

---

## Steps

### Step 1 — Creare Mock FX Providers ✅

**File**: `backend/app/services/fx_providers/mockfx.py` (nuovo)

Due classi, entrambe `@register_provider(FXProviderRegistry)`:

- `MockFXProvider` (code=`"MOCKFX"`): `base_currency="EUR"`, `get_supported_currencies() → ["USD","GBP","CHF","JPY"]`, `fetch_rates()` ritorna rate deterministiche con `hash(pair+date)` normalizzato a 0.5–2.0.
- `MockFXFailProvider` (code=`"MOCKFX_FAIL"`): stessa interfaccia, `fetch_rates()` sempre `raise FXServiceError("Mock failure for testing")`.

**File**: `backend/app/api/v1/fx.py` riga 105

Filtro da:
```python
providers_list = [p for p in providers_list if p["code"] != "MANUAL"]
```
A:
```python
providers_list = [p for p in providers_list if p["code"] not in ("MANUAL", "MOCKFX", "MOCKFX_FAIL")]
```

---

### Step 2 — Rimuovere auto-populate ✅ da `bulk_assign_providers()`

**File**: `backend/app/services/asset_source.py` righe 980–1062

Eliminare l'intero blocco `# Try to auto-populate metadata from provider` e i due `except Exception` annidati. Il loop diventa:

```python
# Build results
for assignment in assignments:
    result = FAProviderAssignmentResult(
        asset_id=assignment.asset_id,
        success=True,
        message=f"Provider {assignment.provider_code} assigned",
        fields_detail=None,
    )
    results.append(result)
```

Commento riga 971 → `# Build results` (rimuovere "and auto-populate metadata").

---

### Step 3 — Fix DistributionEditor ✅ cap 100

**File**: `frontend/src/lib/components/ui/input/DistributionEditor.svelte`

- Riga 158: `Math.max(0, Math.min(100, newVal))` → `Math.max(0, newVal)`
- Riga 210 (funzione `balanceSelected()`): `Math.max(0, Math.min(100, ...))` → `Math.max(0, ...)`

Motivazione: i pesi percentuali possono superare 100 durante l'editing (il vincolo è solo al save, non in real-time).

---

### Step 4 — Fix FX auto-sync ✅ dopo save provider

**File**: `frontend/src/routes/(app)/fx/[pair]/+page.svelte`

Righe 640–641: rimuovere il commento `// Auto-sync to fetch rates from the newly added provider` e la riga `await handleSync()`. Funzione risultante:

```typescript
async function handleProviderModalCreated(_detail: {base: string; quote: string; hasRealProvider: boolean}) {
    await loadProviders();
    showProviderModal = false;
}
```

---

### Step 5 — Fix Pydantic ✅ `errors=None`

**File**: `backend/app/services/fx.py`

- Riga 1088: `errors=fallback_errors if fallback_errors else None` → `errors=fallback_errors or []`
- Riga 1193: `errors=chain_errors if chain_errors else None` → `errors=chain_errors or []`

Lo schema `FXSyncPairResult.errors` è `List[str]` con `default_factory=list`, NON `Optional[List[str]]`. Passare `None` è un type mismatch.

---

### Step 6 — Fix ordine build ✅: font PRIMA del frontend

**File**: `dev.py`

1. `_docker_ensure_assets_built()` (riga 1091): spostare `update_js_cache()` (attualmente step 3, riga 1141) **prima** del frontend build (attualmente step 1, riga 1099). Rinumerare commenti:
   - 1 → JS library cache
   - 2 → Frontend
   - 3 → MkDocs
   - 4 → requirements.txt

2. `cmd_fe_build()` (riga 436): aggiungere `update_js_cache()` come primissimo step, prima di `cmd_api_sync()`. SvelteKit prerender valida i file referenziati in `app.html`, quindi i font devono esistere prima del build.

---

### Step 7 — Aggiungere ✅ `data-testid` per E2E classification

**File**: `frontend/src/lib/components/ui/input/DistributionEditor.svelte`

- Riga 357, wrapper `<div class="space-y-1">`: aggiungere `data-testid="distribution-editor-{kind}"`
- Riga 448, `<span>` del totale percentuale: aggiungere `data-testid="distribution-total-{kind}"`
- Riga 389, bottone `+Add`: aggiungere `data-testid="distribution-add-{kind}"`

**File**: `frontend/src/lib/components/assets/AssetModal.svelte`

- Riga 1248, collapsible "More Info" header `<div>`: aggiungere `data-testid="asset-modal-more-info"`
- Riga 1233, `<textarea>` short description: aggiungere `data-testid="asset-modal-description"`

---

### Step 8 — Migrare test ✅ `test_metadata_auto_populate`

**File**: `backend/test_scripts/test_services/test_asset_source.py`

Sostituire `test_metadata_auto_populate` (righe 244–295) con 6 nuovi test:

| Test | Verifica |
|------|----------|
| `test_assign_does_not_modify_metadata` | Assign mockprov → `classification_params` resta `None` (no auto-populate) |
| `test_assign_preserves_existing_metadata` | Asset con geo+sector pre-impostati → assign provider → geo+sector invariati |
| `test_refresh_returns_metadata_fields` | Dopo assign, `refresh_assets_from_provider()` → risultato contiene `refreshed_fields` con sector, geo, short_desc |
| `test_refresh_populates_empty_asset` | Asset vuoto → refresh → metadata scritti nel DB (sector=Technology, geo=USA+ITA come da mockprov) |
| `test_refresh_field_detail_completeness` | Verifica `missing_data_fields`, `ignored_fields` nel response |
| `test_patch_preserves_user_set_fields` | PATCH con `geographic_area` → refresh da mockprov (che ha geo diverso) → GET → verify che il refresh ha sovrascritto (comportamento refresh: "prende dal provider"). Distinto dal probe/diff che è frontend-driven |

---

### Step 9 — Test backend FX ✅ fallback con MOCKFX

**File**: `backend/test_scripts/test_api/test_fx_sync.py`

Nuova classe `TestFXFallbackWithMockProviders` (auto-discovered da pytest):

| Test | Verifica |
|------|----------|
| `test_fx_fallback_primary_fails` | Crea coppia con route MOCKFX_FAIL priority=1 + MOCKFX priority=2 → sync → `status=OK`, `provider_used` contiene "MOCKFX" (non FAIL), `errors` non-vuoto (contiene errore route 1) |
| `test_fx_fallback_all_fail` | Entrambe le route MOCKFX_FAIL → `status=FAILED`, `errors` contiene 2 errori |
| `test_fx_direct_mockfx` | Solo MOCKFX priority=1 → `status=OK`, `errors=[]` |

I test creano `FxConversionRoute` via API (`POST /fx/currencies/routes`), sync via `POST /fx/currencies/sync`, poi cleanup.

---

### Step 10 — Test E2E asset ✅ classification round-trip

**File**: `frontend/e2e/assets/asset-classification.spec.ts` (nuovo)

| Test | Descrizione |
|------|-------------|
| `set geo distribution → save → reopen → present` | Create asset → open edit modal → expand "More Info" (`data-testid="asset-modal-more-info"`) → click +Add geographic → set country+weight → save → reopen → verify entry presente |
| `set sector distribution → save → reopen → present` | Analogo per sector |
| `clear distribution → save → reopen → empty` | Add geo entry → save → reopen → remove entry → save → reopen → verify empty |

**File**: `scripts/test_runner/_frontend_asset.py`

- Aggiungere `front_asset_classification()` → `_run_playwright("assets/asset-classification.spec.ts")`
- Aggiungere a `front_asset_all()` tests list
- Registrare in `populate_registry()` con `add_test(cat, "asset-classification", ...)`

---

## Riepilogo file modificati

| File | Tipo | Step |
|------|------|------|
| `backend/app/services/fx_providers/mockfx.py` | Nuovo: 2 mock FX providers | 1 |
| `backend/app/api/v1/fx.py` | Edit: filtro API nasconde MOCKFX* | 1 |
| `backend/app/services/asset_source.py` | Edit: rimuovere auto-populate (righe 980–1062) | 2 |
| `frontend/src/lib/components/ui/input/DistributionEditor.svelte` | Edit: rimuovere cap 100 + data-testid | 3, 7 |
| `frontend/src/routes/(app)/fx/[pair]/+page.svelte` | Edit: rimuovere auto-sync | 4 |
| `backend/app/services/fx.py` | Edit: errors=[] instead of None | 5 |
| `dev.py` | Edit: build order font→frontend | 6 |
| `frontend/src/lib/components/assets/AssetModal.svelte` | Edit: data-testid per More Info e description | 7 |
| `backend/test_scripts/test_services/test_asset_source.py` | Edit: sostituire test_metadata_auto_populate con 6 test | 8 |
| `backend/test_scripts/test_api/test_fx_sync.py` | Edit: 3 test FX fallback | 9 |
| `frontend/e2e/assets/asset-classification.spec.ts` | Nuovo: 3 test E2E | 10 |
| `scripts/test_runner/_frontend_asset.py` | Edit: registrazione asset-classification | 10 |

## Post-implementazione

```bash
./dev.py db create-clean --test       # DB pulito
./dev.py test services all            # test_asset_source migrato + test_asset_source_refresh
./dev.py test api test_fx_sync        # FX fallback tests
./dev.py test front-asset all         # E2E asset classification + modal + list + detail
```

---

## Execution Log

### Session 1 (pre-context-break)

Tutti i 10 step implementati. Review utente ha evidenziato:
- `pair_routes_map` tipo → corretto a `dict[str, list[FxConversionRoute]]`
- MockFX reworked: `MOCKFX_FIXED_RATE = Decimal("1.234500")`, `MOCKFX_FAIL.FAIL_MESSAGE` con stringa distintiva
- Import `AssetProviderRegistry` spostato a top-level in `test_asset_source.py`
- DistributionEditor: rimosso `max: 100` anche dalla column definition (riga 322)
- `reloadMetadata()` in `assets/[id]/+page.svelte`: rimosso gate `has_metadata` → always reload after save
- Bug persistence `classification_params.geographic_area`: indagine iniziata, sospetto server con codice vecchio

### Session 2 (2026-05-11)

#### Fix extra trovati durante test run

| # | Bug | File | Fix |
|---|-----|------|-----|
| A | Auto-populate **non rimosso** nella sessione 1 (blocco righe 980-1066 ancora presente) | `asset_source.py` | Rimosso intero blocco — loop ora solo `results.append(result)` |
| B | `errors=None` terza occorrenza in `_compute_single_step` (riga 1088) | `fx.py` | `errors=fallback_errors or []` (il fix della sessione 1 aveva patchato solo 2 su 3 occorrenze) |
| C | `RotateCcw` con `animate-spin` nella `FxPairAddModal` → rotazione visiva antioraria | `FxPairAddModal.svelte` | `RotateCcw` → `RotateCw` sia nell'import che nel template |
| D | FX detail: auto-sync dopo edit provider (sync dentro il modale non distingue create vs edit) | `FxPairAddModal.svelte` | `if (!editMode)` attorno al blocco auto-sync (righe 252-273) |
| E | FX global: toast mancante dopo auto-sync alla creazione coppia | `FxPairAddModal.svelte` | Aggiunto `toasts.success()` con count punti dopo sync OK |

#### Test Results

| Suite | Risultato | Note |
|-------|-----------|------|
| API (35 test groups) | ✅ 35/35 | Include 3 nuovi FX fallback MOCKFX tests |
| Services (543 tests) | ✅ 543/543 | Include 6 nuovi assign/refresh metadata tests |
| Schemas (231 tests) | ✅ 231/231 | Invariati |
| Frontend Utility (5) | ✅ 5/5 | auth, settings, files, select-components, image-crop |
| Frontend User (2) | ✅ 2/2 | multi-user, broker-sharing |
| Frontend FX (8) | ✅ 8/8 | chart-settings, fx-list, fx-detail, ecc. |
| Frontend Asset (5) | ✅ 5/5 | **Include nuovo `asset-classification` E2E** |
| Frontend Transaction (9) | ✅ 9/9 | modals, table, broker-access, paired-edit, tooltips, bulk-ops, ecc. |
| **ALL FRONTEND** | ✅ 6/6 categories | 🎉 ALL FRONTEND TESTS PASSED |

#### File aggiuntivi modificati (non nel piano originale)

| File | Modifica | Motivo |
|------|----------|--------|
| `frontend/src/lib/components/fx/FxPairAddModal.svelte` | `RotateCcw` → `RotateCw` | Icona sync ruotava in direzione sbagliata |
| `frontend/src/routes/(app)/assets/[id]/+page.svelte` | `reloadMetadata()` always reload | Gate su `has_metadata` stale impediva caricamento classification post-save |
| `frontend/src/lib/components/ui/input/DistributionEditor.svelte` | Rimosso `max: 100` da column config | HTML `<input max="100">` bloccava input >100 nonostante il fix JS |

### User Testing Feedback (Session 2)

| Area | Risultato | Note |
|------|-----------|------|
| FX Global — creazione coppia | ✅ | Sync OK, icona corretta, freccia clockwise |
| FX Global — toast post-sync | ❌→✅ | Mancava toast → aggiunto in FxPairAddModal (fix E) |
| FX Detail — edit provider | ❌→✅ | Auto-sync non voluto → `if (!editMode)` (fix D) |
| Asset — classification persistence | ✅ | geo+sector ora persistono dopo PATCH+reload |
| Asset — network flow | ✅ | PATCH assets → GET all → GET assignments → GET query → GET current |

---

## Edge Case: Form Validate vs Bulk Validate (Same-Day Intra-Batch Dependencies)

### Scenario osservato

Bulk con DEPOSIT + BUY nello stesso giorno:
```json
{"creates":[
  {"broker_id":1,"type":"DEPOSIT","date":"2026-05-11","quantity":"0","cash":{"code":"EUR","amount":"1000"}},
  {"broker_id":1,"type":"BUY","date":"2026-05-11","quantity":"11","asset_id":1,"cash":{"code":"EUR","amount":"-10"}}
]}
```

- **Bulk `/validate`** → ✅ `issues: []` (processa entrambe le righe insieme, DEPOSIT porta il bilancio a +1000, BUY spende -10 = resta +990)
- **FormModal** validate (singola riga BUY) → ❌ `balanceCashNegative` (vede solo il BUY senza il DEPOSIT che lo precede nella stessa bulk)

### Analisi: FormModal valida in isolamento

`TransactionFormModal.svelte` riga 695:
```typescript
const payload = mode === 'edit' ? {updates: [collectUpdate()]} : {creates: [collectCreate()]};
```

Invia **solo la riga corrente** a `/validate`. Non include le altre righe presenti nella BulkModal. Ciò causa falsi negativi quando una riga dipende da un'altra nella stessa batch (e.g. DEPOSIT → BUY same day).

### Domanda: la Form esiste ancora come entità standalone?

**No** — la FormModal è oggi esclusivamente invocata **dall'interno della BulkModal** per editare/creare una singola riga. Non esiste più un flusso "crea transazione singola fuori dalla bulk". Ogni transazione nasce dentro la bulk table.

### Proposta: validate contestuale

La FormModal dovrebbe mandare a `/validate` il payload completo della bulk (compresa la riga corrente modificata), non solo la singola riga. Così il balance walk vede tutte le transazioni in-flight:

```typescript
// Invece di:
{creates: [collectCreate()]}
// Dovrebbe essere:
{creates: [...otherBulkCreates, collectCreate()], updates: [...otherBulkUpdates]}
```

Oppure — soluzione più leggera — la FormModal **non valida affatto** (non chiama `/validate`), e la validazione rimane solo nella BulkModal al "Validate All" / auto-debounce. La FormModal si limita al check strutturale locale (campi obbligatori presenti).

**Decisione da prendere**: disabilitare la validate nella FormModal (solo structural check locale) oppure passarle il contesto della bulk.

### Same-Day Ordering: come funziona

`_validate_broker_balances()` ordina le transazioni con:
```python
ORDER BY Transaction.date, Transaction.id
```

Le transazioni **dello stesso giorno** vengono processate in ordine di `id` (auto-increment). Nella bulk, l'ordine di inserimento determina l'ordine degli ID:
- index 0 → ID più basso → processato per primo
- index 1 → ID più alto → processato dopo

**Implicazione**: l'ordine delle righe nella bulk array matters! Un BUY prima di un DEPOSIT nello stesso giorno fallirà la validazione, anche se la somma finale è positiva.

**Coerenza**: questo è il design corretto per un sistema daily-point. Il vincolo "mai negativo" deve essere vero in ogni istante, e l'ordine di inserimento (ID) è l'unico modo deterministico di risolvere l'ambiguità intra-giorno.

### Test coverage attuale

**Non esistono test backend** per i seguenti scenari:
- Same-day DEPOSIT+BUY (ordine corretto → pass)
- Same-day BUY+DEPOSIT (ordine invertito → fail)
- Same-day multiple operations che si compensano
- Validate della singola riga vs batch completa

**Raccomandazione**: creare `backend/test_scripts/test_api/test_tx_balance_walk.py` con test specifici per:
1. Same-day deposit-then-buy (pass)
2. Same-day buy-then-deposit (fail — saldo negativo intra-day)
3. Multi-day cumulative balance
4. Edit che sposta la data di un deposit → cascata di violazioni
5. Delete di un deposit a metà timeline → downstream BUY diventa invalido

---

## Pending: Missing i18n Keys for Transaction Toasts ✅

### Piano originale (PlanC2 Step 6)

Riferimento: `plan-phase07-transaction-Part4_Round6_PlanC2_BugfixAndPairValidation.prompt.md`, Step 6 — Fix B4.

Il piano prevedeva:
1. `handleBulkCommitted(resp)` conta per tipo di operazione i `status:'success'`
2. **Singola operazione** → toast **dettagliato** (stile delete: tipo, asset, broker, data) — riutilizzare `typeHtml()` e `brokerHtml()` da `+page.svelte`
3. **Multiple operazioni** → toast **sommario**: "✅ N creazioni, M modifiche, D eliminazioni salvate"
4. Chiavi previste: `transactions.toast.bulkSummary`, `transactions.toast.created`, `transactions.toast.updated`, `transactions.toast.deleted`

### Stato attuale

L'implementazione (riga 481-496 di `+page.svelte`) fa **solo il sommario numerico** per tutti i casi:
```typescript
if (created) parts.push(`${created} ${$_('transactions.toast.created') || 'created'}`);
```
- Il toast dettagliato per singola operazione **non è stato implementato**
- La chiave `transactions.toast.bulkSummary` **non è definita né usata**
- Le 3 chiavi `.created/.updated/.deleted` sono usate ma **non definite** nei file i18n (fallback hardcoded)

### Azioni da fare

1. Aggiungere le 3 chiavi i18n mancanti (sommario numerico)
2. Valutare se implementare il toast dettagliato per singola op (pianificato ma mai fatto) — bassa priorità, il sommario è sufficiente
3. Rimuovere `transactions.toast.bulkSummary` dal piano (non più necessaria, il codice costruisce la frase direttamente dalle 3 chiavi componenti)

---

## Pending: Toast Informativo per Asset Creati da Transaction ✅

### Scenario

Utente crea un asset direttamente dalla TransactionFormModal (pulsante "Crea Asset"), poi crea un BUY per quell'asset. Al commit della bulk, l'asset esiste ma non ha nessun prezzo storico.

### Decisione: solo toast informativo (no auto-sync)

Al commit della bulk, se sono stati creati asset "vergini" (senza price history), mostrare un **toast informativo** che:
- ✅ Conferma la creazione dell'asset
- ℹ️ Comunica all'utente che per i prezzi dovrà andare nella pagina asset e fare sync al termine dell'inserimento delle transazioni

**No auto-sync**: l'utente decide lui quando e come popolare i prezzi storici.

### Implementazione

Nel callback `handleBulkCommitted()` di `transactions/+page.svelte`:
1. Per ogni `result` con `operation: "create"` → raccogliere gli `asset_id` unici
2. Filtrare quelli appena creati nella sessione corrente (tracking via AssetModal)
3. Toast: `"Asset {name} created. Go to the asset page to sync price history."`

Chiave i18n: `transactions.toast.assetCreatedHint`

---

## Pending: FormModal Validate con Contesto Bulk ✅

### Decisione: mandare l'intero bulk

La FormModal deve inviare a `/validate` l'**intera bulk** (tutte le creates + updates + deletes), con la riga corrente sostituita/aggiunta. Così il balance walk vede il contesto completo.

### Implementazione

1. **BulkModal** passa alla FormModal un callback `getBulkContext()` che ritorna il payload corrente della bulk (creates, updates, deletes) **esclusa** la riga in editing
2. **FormModal** nella `validateFn`:
   ```typescript
   const bulkContext = getBulkContext(); // {creates: [...], updates: [...], deletes: [...]}
   const myPayload = mode === 'edit' ? {updates: [collectUpdate()]} : {creates: [collectCreate()]};
   // Merge: bulk context + current row
   const fullPayload = {
       creates: [...(bulkContext.creates || []), ...(myPayload.creates || [])],
       updates: [...(bulkContext.updates || []), ...(myPayload.updates || [])],
       deletes: bulkContext.deletes || [],
   };
   const res = await zodiosApi.validate_transactions_...(fullPayload);
   // Filter issues: show only those with index matching current row
   ```
3. **Issue filtering**: `/validate` ritorna issues per tutte le righe, ma la FormModal deve mostrare solo quelle relative alla riga corrente (match per `index` e `operation`)

### Banner text per errori contestuali

Quando la FormModal mostra errori derivanti dalla validazione contestuale (cioè la riga è valida da sola, ma viola i vincoli considerando le altre modifiche pianificate), usare un header distinto nel banner:

- **Chiave**: `transactions.validate.contextualIssuesHeader`
- **EN**: `"With the other pending changes, this row causes the following issues:"`
- **IT**: `"Considerando le altre modifiche in sospeso, questa riga causa i seguenti problemi:"`
- **FR**: `"Avec les autres modifications en attente, cette ligne provoque les problèmes suivants :"`
- **ES**: `"Con los demás cambios pendientes, esta fila causa los siguientes problemas:"`

Questo header sostituisce `validate.issuesHeader` / `validate.balanceIssuesHeader` solo quando l'errore proviene dal contesto (cioè la stessa riga validata da sola non avrebbe errori). In pratica, si usa sempre il header contestuale nella FormModal perché lì la validazione è sempre contestuale.

### Vantaggi
- Zero duplicazione di logica (il backend è l'unico validatore)
- La FormModal vede sempre il contesto corretto (same-day dependencies risolte)
- La BulkModal non perde la sua validate globale

---

## Pending: Same-Day Ordering Algorithm ✅ (confirmed end-of-day + tests)

### Problema attuale

`ORDER BY date, id` funziona solo se l'ordine di inserimento corrisponde all'ordine logico delle operazioni. Ma per l'utente, l'ordine in cui clicca "Add row" nella bulk non ha significato semantico — un DEPOSIT e un BUY nello stesso giorno sono concettuali, non sequenziali.

### Opzione A: Ordinamento per tipo (type-priority)

Definire una priorità fissa per `TransactionType` che riflette l'ordine logico:

| Priority | Type | Reasoning |
|----------|------|-----------|
| 1 | DEPOSIT | Cash enters the broker first |
| 2 | TRANSFER_IN | Assets/cash arrive |
| 3 | BUY | Requires cash already present |
| 4 | DIVIDEND | Passive income on held assets |
| 5 | INTEREST | Passive income on cash |
| 6 | FEE | Deducted from balance |
| 7 | TAX | Deducted from balance |
| 8 | SELL | Liquidates held assets |
| 9 | WITHDRAWAL | Cash leaves (alias: TRANSFER_OUT) |
| 10 | TRANSFER_OUT | Assets/cash leave |
| 11 | SPLIT | Structural change |
| 12 | OTHER | Catch-all |

`ORDER BY date, type_priority, id`

**Pro**: deterministico, semanticamente corretto (deposit prima di buy), ordine indipendente dall'inserimento.
**Contro**: regole rigide — edge cases dove l'utente vuole un ordine diverso? Rari.

### Opzione B: End-of-Day balance check (somma giornaliera)

Invece di validare istante per istante dentro la giornata, sommare tutti i delta del giorno e verificare che il saldo a fine giornata sia ≥ 0.

```python
# Attuale: per-transaction within day
for tx in txs_of_day:
    balance += tx.amount
    if balance < 0: FAIL  # ← fails mid-day

# Proposta: end-of-day
day_delta = sum(tx.amount for tx in txs_of_day)
balance += day_delta
if balance < 0: FAIL  # ← checks only EOD
```

**Pro**: ordine intra-giorno irrilevante, nessuna ambiguità.
**Contro**: permette stati "transienti negativi" dentro la giornata. Ma dato che il nostro sistema è daily-point (un prezzo per giorno, un saldo per giorno), i saldi intra-giorno non hanno significato osservabile.

### Raccomandazione

**Opzione B (end-of-day)** è più coerente con il design daily-point di LibreFolio:
- Se il sistema ragiona per giorno, non ha senso imporre un ordine intra-giorno
- Elimina la dipendenza dall'ordine di inserimento
- Elimina il problema FormModal (DEPOSIT + BUY same day sono equivalenti a BUY + DEPOSIT)
- Implementazione più semplice (3 righe di codice cambiate)

L'Opzione A (type-priority) è un buon fallback se in futuro si volesse un ordinamento deterministico per visualizzazione, ma non per la validazione.

### Impatto sul codice

`_validate_broker_balances()` in `transaction_service.py` righe 432-465:

```python
# PRIMA (per-tx within day):
while current_date <= end_date:
    for tx in txs_by_date.get(current_date, []):
        cash_balances[tx.currency] += tx.amount
        asset_balances[tx.asset_id] += tx.quantity
    # check balances AFTER processing ALL transactions of the day
    ...
```

In realtà il codice **già** processa tutte le transazioni del giorno prima di controllare i saldi! Il loop è:
1. `for tx in txs_of_day:` → accumula tutti i delta
2. **poi** `if balance < 0: FAIL`

Quindi **il codice implementa già l'Opzione B** (end-of-day check). Il "problema" osservato dall'utente nella FormModal non è un bug di ordinamento — è un bug di **contesto mancante** (la FormModal valida solo 1 riga, non l'intera bulk).

### Conclusione

- L'algoritmo di balance walk è **già corretto** (end-of-day, non per-transazione)
- Il fix è solo **passare il contesto bulk alla FormModal** (sezione precedente)
- **Test backend da creare** per confermare e documentare il comportamento end-of-day

### Test backend pianificati: `test_tx_balance_walk.py`

**File**: `backend/test_scripts/test_api/test_tx_balance_walk.py` (nuovo)

| # | Test | Scenario | Expected |
|---|------|----------|----------|
| 1 | `test_same_day_deposit_then_buy_pass` | Bulk: DEPOSIT +1000 + BUY -10, same day | ✅ committed=True |
| 2 | `test_same_day_buy_then_deposit_pass` | Bulk: BUY -10 + DEPOSIT +1000, same day (ordine invertito) | ✅ committed=True (end-of-day: +990) |
| 3 | `test_same_day_net_negative_fail` | Bulk: DEPOSIT +100 + BUY -200, same day | ❌ balanceCashNegative |
| 4 | `test_multi_day_cumulative` | Day 1: DEPOSIT +1000. Day 2: BUY -500. Day 3: BUY -600 | ❌ Day 3: balance -100 |
| 5 | `test_edit_move_deposit_date_cascade` | Committed: DEPOSIT day 1, BUY day 2. Update: move DEPOSIT to day 3 | ❌ Day 2: BUY without deposit |
| 6 | `test_delete_deposit_cascades` | Committed: DEPOSIT day 1, BUY day 2. Delete DEPOSIT | ❌ Day 2: balance negative |
| 7 | `test_same_day_multi_ops_compensating` | DEPOSIT +500, BUY -300, SELL +200, WITHDRAWAL -400, same day | ✅ net=0 |
| 8 | `test_validate_single_row_vs_batch` | Validate BUY -10 alone → ❌. Validate DEPOSIT +1000 + BUY -10 → ✅ | Confirms context matters |

### Session 3 — Execution Log (2026-05-11)

#### Implementazioni completate

| # | Item | File(s) | Risultato |
|---|------|---------|-----------|
| 1 | i18n: 3 chiavi toast mancanti | `{en,it,fr,es}.json` | ✅ `transactions.toast.{created,updated,deleted}` |
| 2 | i18n: banner contestuale | `{en,it,fr,es}.json` | ✅ `transactions.validate.contextualIssuesHeader` |
| 3 | i18n: hint asset creato | `{en,it,fr,es}.json` | ✅ `transactions.toast.assetCreatedHint` |
| 4 | Backend: 8 balance walk tests | `test_tx_balance_walk.py` (nuovo) | ✅ 8/8 passed — conferma end-of-day algorithm |
| 5 | Frontend: FormModal context-aware validate | `TransactionFormModal.svelte` | ✅ prop `getBulkContext`, merge payload, issue filtering |
| 6 | Frontend: BulkModal → FormModal context | `TransactionBulkModal.svelte` | ✅ `getBulkContextExcluding(tempId)` + prop passata |
| 7 | Frontend: banner contestuale | `TransactionFormModal.svelte` | ✅ header diverso quando `getBulkContext` presente |
| 8 | Docker: entrypoint gosu | `Dockerfile`, `entrypoint.sh`, `docker-compose.yml` | ✅ Testato su server Linux |
| 9 | Docker: docs aggiornata | `docker_advanced.en.md` | ✅ Semplificata, cheatsheet Linux |
| 10 | translate-diff: LaTeX validation | `translate_docs.py` | ✅ LATEX_COUNT con line numbers, LATEX_SYNTAX |

#### Verifiche

- `svelte-check`: 0 errors, 0 warnings ✅
- Backend balance walk: 8/8 tests pass ✅
- Docker build+up su server Linux: ✅ `LibreFolio-data/` owner corretto

#### Ancora da fare (non in questo round)

- Nessuno — tutti gli item del round completati

---

## Link forward

→ **Piano C3**: [`plan-phase07-transaction-Part4_Round6_PlanC3_PendingOpRefactor.prompt.md`](./plan-phase07-transaction-Part4_Round6_PlanC3_PendingOpRefactor.prompt.md) — Completamento refactor architetturale: `DraftRow` → `PendingOp` + `DraftFields`, eliminazione `fromTx()`, props legacy, rinomina `drafts` → `ops`.

