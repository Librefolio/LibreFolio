# Plan: C2 Merged — Bugfix + Pair Desc/Tags Validation + Test Coverage

**Origine**: 5 bug trovati nel test manuale del Piano C (txStore refactor) + problema di description/tags divergenti nelle coppie linkate di mock data. Fix mirati + regola di validazione backend + copertura E2E da ~68 a ~82 test.

---

## 🐛 Bug

| # | Titolo | Root Cause | File |
|---|--------|-----------|------|
| B1 | `deriveStatus()` false positive "edited" su Edit paired senza modifiche | **Due cause**: (a) mock data con description diverse tra i due lati della coppia → `collectDualCreates()` copia la description del "from" su entrambi → `diffDualItem` rileva cambio nel "to" rispetto al suo original; (b) per dati legacy/sporchi il FormModal deve rendere esplicita la situazione (concatenazione + nota). La causa (a) è risolta dalla bonifica mock data. | `populate_mock_data.py`, `TransactionFormModal.svelte` |
| B2 | Clone paired TX clona solo la metà cliccata | `resolveInitialRows()` riga 235: `intent.action !== 'clone'` esclude il partner dalla risoluzione automatica | `TransactionBulkModal.svelte` |
| B3 | Picker: context menu + action buttons attivi | `TransactionsTable` definisce sempre `rowActions` e `enableActions=true`. Nessun meccanismo per disabilitarli in contesto picker. | `TransactionsTable.svelte`, `TransactionPickerModal.svelte` |
| B4 | Nessun toast dopo bulk commit | `handleBulkCommitted()` in `+page.svelte` fa solo reload. Non riceve resp dal server e non mostra toast. | `+page.svelte` |
| B5 | Reset toglie label ma sfondo resta | Conseguenza di B1 — si risolve automaticamente fixando B1 | — |
| B6 | Mock data: description divergenti nelle coppie linkate | Tutte le 8 coppie linkate in `populate_mock_data.py` hanno description diverse tra out/in (es. "Transfer AAPL to DEGIRO" vs "Transfer AAPL from IB"). Causa root del B1 e incoerenza con l'invariante "una coppia = una operazione logica". | `populate_mock_data.py` |

---

## Steps

### Step 1 — Fix B6: Bonifica mock data (tutte le coppie linkate) ✅

**File**: `backend/test_scripts/test_db/populate_mock_data.py`

Allineare description su **tutte le 8 coppie linkate**, dare la stessa stringa ad entrambi i lati:

| Coppia | Righe | Description OUT attuale | Description IN attuale | Description nuova (identica su entrambi) |
|--------|-------|------------------------|------------------------|------------------------------------------|
| 1 AAPL transfer | 1136–1163 | `"Transfer AAPL to DEGIRO"` | `"Transfer AAPL from IB"` | `"Transfer AAPL IB ↔ DEGIRO"` |
| 2 BTC transfer | 1167–1194 | `"Transfer BTC to IB"` | `"Transfer BTC from Coinbase"` | `"Transfer BTC Coinbase ↔ IB"` |
| 3 FX EUR→USD | 1198–1223 | `"FX conversion EUR→USD"` | `"FX conversion EUR→USD"` | ✅ già identiche — nessuna modifica |
| 4 Cash transfer | 1227–1254 | `"Cash transfer to IB"` | `"Cash transfer from DEGIRO"` | `"Cash transfer DEGIRO ↔ IB"` |
| Asym-a | 1269–1288 | `"[Asym-a] AAPL IB→Directa (...)"` | `"[Asym-a] AAPL Directa←IB (...)"` | `"[Asym-a] AAPL IB ↔ Directa (OWNER↔EDITOR=full)"` |
| Asym-b | 1292–1311 | analogo | analogo | `"[Asym-b] BTC IB ↔ Coinbase (OWNER↔EDITOR=full)"` |
| Asym-c | 1315–1334 | analogo | analogo | `"[Asym-c] MSFT IB ↔ DEGIRO (OWNER↔VIEWER=view-only)"` |
| Delete-safe | 1341–1360 | `"[delete-safe] ETH Coinbase→IB..."` | `"[delete-safe] ETH IB←Coinbase..."` | `"[delete-safe] ETH Coinbase ↔ IB"` |
| Asym-d | 1687–1706 | analogo | analogo | `"[Asym-d] AAPL IB ↔ HiddenBroker (OWNER↔none=locked)"` |

Tags: già identici su entrambi i lati in tutte le coppie — nessuna modifica necessaria.

---

### Step 2 — Backend: regola di validazione pair desc/tags consistency ✅

**File**: `backend/app/services/transaction_service.py`

**Nuovo metodo statico** nella classe `TransactionService`:

```python
@staticmethod
def _validate_pair_description_tags(a: Transaction, b: Transaction) -> Optional[tuple[str, str, dict]]:
    """Validate that linked pair has identical description and tags.
    Returns None if OK, otherwise (error_msg, code, params)."""
```

Logica:
- Se `a.description != b.description` → return error tuple `("Linked pair must have identical description", "pairDescriptionMismatch", {})`
- Se `a.tags != b.tags` (confronto stringhe CSV) → return error tuple `("Linked pair must have identical tags", "pairTagsMismatch", {})`
- Altrimenti → `None`

**Hook in step 6 (link resolution), righe 1127–1135**: dopo aver assegnato `related_transaction_id` e dopo `_validate_linked_pair()`, chiamare `_validate_pair_description_tags()`. Se ritorna errore → aggiungere `TXValidationIssue` con code corrispondente.

```python
# EXISTING: semantic validation
pair_result = self._validate_linked_pair(pairs[0][1], pairs[1][1])
if pair_result is not None:
    ...
    continue
# NEW: description/tags consistency
desc_result = self._validate_pair_description_tags(pairs[0][1], pairs[1][1])
if desc_result is not None:
    desc_error, desc_code, desc_params = desc_result
    issues.append(TXValidationIssue(operation="create", index=pairs[0][0], ...))
    continue
# EXISTING: set related_transaction_id
pairs[0][1].related_transaction_id = pairs[1][1].id
pairs[1][1].related_transaction_id = pairs[0][1].id
```

**Hook in step 4 (updates)**: dopo il loop degli update (dopo riga 1088), aggiungere un secondo pass per verificare la consistency finale delle coppie toccate:

```python
# 4b. Validate pair desc/tags consistency for all updated linked TXs
updated_linked_ids = set()
for orig_idx, item in parsed_updates:
    tx = existing_by_id.get(item.id)
    if tx and tx.related_transaction_id and (item.tags is not None or item.description is not None):
        updated_linked_ids.add(tx.id)

for tx_id in updated_linked_ids:
    tx = existing_by_id.get(tx_id)
    if not tx or not tx.related_transaction_id:
        continue
    partner = existing_by_id.get(tx.related_transaction_id)
    if partner is None:
        partner = await self.session.get(Transaction, tx.related_transaction_id)
    if partner is not None:
        result = self._validate_pair_description_tags(tx, partner)
        if result is not None:
            err_msg, err_code, err_params = result
            orig_idx = next((i for i, item in parsed_updates if item.id == tx_id), -1)
            issues.append(TXValidationIssue(
                operation="update", index=orig_idx, ref_id=tx_id,
                error=err_msg, code=err_code, params=err_params,
            ))
```

---

### Step 3 — Fix B1: Gestione dati sporchi nel FormModal paired ✅

**Causa B1**: se una coppia ha description diverse (dati legacy/sporchi), il FormModal mostra solo la description del "from". Quando l'utente salva senza modifiche, `collectDualCreates()` copia quella description su entrambi → `diffDualItem` rileva giustamente un cambio sul "to" → status "edited" è **corretto** perché il dato cambia davvero.

**Fix**: rendere esplicita la situazione all'utente. Quando il FormModal apre un paired edit e rileva description diverse tra `initialRow` e `partnerRow`:

**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`, nella `$effect` che inizializza il draft (dove fa `buildDraft(initialRow)` per riempire `draft.description`)

```typescript
// After building the draft from initialRow and fetching partnerRow:
if (partnerRow && initialRow.description !== partnerRow.description) {
    // Concatenate mismatched descriptions with explanatory note
    const fromDesc = initialRow.description ?? '';
    const partnerDesc = partnerRow.description ?? '';
    const parts: string[] = [];
    if (fromDesc) parts.push(fromDesc);
    if (partnerDesc) parts.push(partnerDesc);
    draft.description = parts.join(' | ') + 
        ' [auto-merged: pair had mismatched descriptions]';
}
```

Stessa logica per tags: se diversi, fare union (dedup) senza nota (i tags sono atomici, l'union è autoesplicativa).

**Risultato**:
- L'utente vede la concatenazione + nota → capisce cosa è successo
- Status "edited" → **corretto**, la description sta genuinamente cambiando
- Al save il backend valida che entrambi i lati abbiano stessa description → ✅ passa
- Nessuna logica di soppressione diff, nessun caso speciale in `collectDualUpdates()`

**B5** si risolve comunque: se i dati di partenza sono puliti (Step 1 bonifica), la concatenazione non scatta mai e status resta "original".

---

### Step 4 — Fix B2: Clone paired TX ✅

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`, `resolveInitialRows()` riga 246

Modificare il blocco `intent.action === 'clone'` (righe 246–255):

1. Aggiungere auto-inclusione partner: prima del `map`, per ogni TX cliccata che ha `related_transaction_id`, fare `txStoreGet(tx.related_transaction_id)` e aggiungerla al `resolved` (come nel blocco edit/delete riga 235)
2. Generare un `link_uuid` condiviso per la coppia clonata
3. Su entrambe: `id: 0`, `date: today`, `related_transaction_id: null`
4. Applicare `quantityRule: 'zero'` se il tipo lo richiede

```typescript
if (intent.action === 'clone') {
    // Auto-include partner for paired clone
    for (const id of txIds) {
        const tx = txStoreGet(id);
        if (tx?.related_transaction_id && !seen.has(tx.related_transaction_id)) {
            const partner = txStoreGet(tx.related_transaction_id);
            if (partner) { resolved.push(partner); seen.add(partner.id); }
        }
    }
    const today = todayIso();
    const cloned = resolved.map((r) => {
        const c = {...r, id: 0, date: today, related_transaction_id: null} as TXReadItem;
        const rule = getTypeRule(r.type);
        if (rule.quantityRule === 'zero') c.quantity = '0';
        return c;
    });
    // Generate shared link_uuid for paired clones
    if (cloned.length === 2 && cloned[0].type === cloned[1].type) {
        const uuid = generateUUID();
        (cloned[0] as any).link_uuid = uuid;
        (cloned[1] as any).link_uuid = uuid;
    }
    return {rows: cloned, autoForm: cloned.length === 1 ? 'create' : null};
}
```

**Verifica**: Clone paired → BulkModal con 2 righe `new`, Da:/A: con link_uuid condiviso.

---

### Step 5 — Fix B3: Picker context menu ✅

**File**: `frontend/src/lib/components/transactions/TransactionsTable.svelte`, `TransactionPickerModal.svelte`

1. Aggiungere prop `hideActions?: boolean` a `TransactionsTable` (default `false`)
2. Quando `hideActions=true`: settare `enableActions=false`, `enableContextMenu=false`, `rowActions=[]`
3. In `TransactionPickerModal`: passare `hideActions={true}`

---

### Step 6 — Fix B4: Toast dopo bulk commit ✅

**File**: `frontend/src/routes/(app)/transactions/+page.svelte`

1. `handleBulkCommitted(resp)` accetta il response body `TXBatchResponse` con `results[]`
2. Conta per tipo di operazione (`create`/`update`/`delete`) i `status:'success'`
3. Singola operazione → toast dettagliato (stile delete: tipo, asset, broker, data)
4. Multiple operazioni → toast sommario: "✅ N creazioni, M modifiche, D eliminazioni salvate"
5. Chiavi i18n: `transactions.toast.bulkSummary`, `transactions.toast.created`, `transactions.toast.updated`, `transactions.toast.deleted`

---

### Step 7 — Test backend: pair desc/tags validation ✅

**File**: `backend/test_scripts/test_api/test_transactions_api.py`

Nuova classe `TestPairDescriptionTagsValidation` con 4 test:

1. **`test_create_pair_same_description_ok`** — crea coppia TRANSFER via `/transactions/commit` con description identica su entrambi → commit OK, `committed=True`

2. **`test_create_pair_different_description_rejected`** — crea coppia con description diverse → `committed=False`, issue con `code="pairDescriptionMismatch"`

3. **`test_create_pair_different_tags_rejected`** — crea coppia con tags diverse → `committed=False`, issue con `code="pairTagsMismatch"`

4. **`test_update_description_pair_consistency`** — crea coppia con description identica → update description solo su un lato senza aggiornare il partner → `committed=False`, issue `pairDescriptionMismatch`. Poi update entrambi nella stessa batch → OK

---

### Step 8 — Nuovi E2E test ✅

**Nuovo `tx-clone.spec.ts`** (5 test):
- Clone standalone → 1 riga new, `date=today`
- Clone paired → 2 righe new (Da:/A:), `date=today`, `link_uuid` condiviso
- Clone con `quantityRule='zero'` → `qty=0`
- Clone paired commit → coppia creata nel DB
- Clone da broker view-only → no edit/delete actions on row

**Nuovo `tx-bulk-operations.spec.ts`** (7 test):
- Bulk edit 2+ → griglia senza FormModal auto-open
- Edit senza modifiche + Apply → status `original` (B1 regression test)
- Mark delete + unmark → torna `original`
- Reset singola riga + Reset tutte → valori originali
- Mixed commit (create+update+delete) → toast con conteggio
- Picker: no context menu, no action buttons
- Create coppia con description diverse → errore validazione banner (B6/Step 2 regression test)

**Bugfix collaterale**: `fromTx()` in BulkModal non preservava `link_uuid` già impostato da `resolveInitialRows()` per clone paired → fix: `(tx as any).link_uuid ?? ...` fallback.

**Bugfix collaterale 2**: `TestPairDescriptionTagsValidation._setup()` asseriva `status_code == 200` per asset creation ma endpoint ritorna 201 → fix: `assert in (200, 201)`.

---

### Step 9 — Registrazione test runner ✅

**File**: `scripts/test_runner/_frontend_transaction.py`

- `front_tx_clone()` → `_run_playwright("transactions/tx-clone.spec.ts")`
- `front_tx_bulk_operations()` → `_run_playwright("transactions/tx-bulk-operations.spec.ts")`
- Entrambi aggiunti a `front_transaction_all()` tests list
- Registrati in `populate_registry()` con `add_test()`

---

### Step 10 — Nota in `phase-07-transactions.md` ✅

**File**: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-transactions.md`

Aggiungere dopo riga 537 (nel blocco "Features deferred from Part 4 → Part 5"):

> - **Description/Tags merge su Promote**: quando la Staging Modal propone il promote di due TX standalone in coppia, le description possono differire. Il backend rifiuterà il commit se description/tags non sono identici (`pairDescriptionMismatch`). La UX per la Parte 5 dovrà offrire una **modale di diff a 3 vie** (description lato A, description lato B, risultato merged editabile) dove l'utente sceglie o compone il testo finale. Per i tags: proporre l'**union** dei due set con checkbox per deselezionare quelli indesiderati. Solo dopo l'allineamento l'utente può committare il promote. Vedi `TransactionService._validate_pair_description_tags()`.

---

## Riepilogo file modificati

| File | Tipo | Step |
|------|------|------|
| `backend/test_scripts/test_db/populate_mock_data.py` | Edit: 8 coppie description allineate | 1 |
| `backend/app/services/transaction_service.py` | Edit: nuovo `_validate_pair_description_tags()`, hook in step 4b e step 6 | 2 |
| `frontend/src/lib/components/transactions/TransactionFormModal.svelte` | Edit: concatenazione dati sporchi + nota in paired edit | 3 |
| `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` | Edit: clone paired auto-include partner | 4 |
| `frontend/src/lib/components/transactions/TransactionsTable.svelte` | Edit: prop `hideActions` | 5 |
| `frontend/src/lib/components/transactions/TransactionPickerModal.svelte` | Edit: passare `hideActions={true}` | 5 |
| `frontend/src/routes/(app)/transactions/+page.svelte` | Edit: toast dopo bulk commit | 6 |
| `backend/test_scripts/test_api/test_transactions_api.py` | Edit: nuova classe 4 test pair validation | 7 |
| `frontend/e2e/transactions/tx-clone.spec.ts` | Nuovo: ~5 test | 8 |
| `frontend/e2e/transactions/tx-bulk-operations.spec.ts` | Nuovo: ~7 test | 8 |
| `frontend/e2e/transactions/tx-paired-edit.spec.ts` | Edit: +2 test | 8 |
| `scripts/test_runner/_frontend_transaction.py` | Edit: registrazione 2 nuovi spec | 9 |
| `LibreFolio_developer_journal/.../phase-07-transactions.md` | Edit: nota diff 3-vie per Parte 5 | 10 |

## Post-modifiche

1. `./dev.py db create-clean --test` (mock data cambiati)
2. `./dev.py test api all` (test pair validation + nessuna regressione)
3. `./dev.py test front-transaction all` (E2E nuovi + regressione)

## Gap UC coverage (prima → dopo)

| Metrica | Prima | Dopo |
|---------|-------|------|
| UC coperti | 15/26 (58%) | 24/26 (92%) |
| Test E2E | 68 | 80 |
| Spec file | 7 | 9 |
| UC non coperti | UC27-UC28 (future: Split/Promote) | Solo UC27-UC28 |

## Further Considerations

- **Mock data**: verificare che `populate_mock_data.py` abbia TX paired cross-broker con ruoli diversi per i test cross-access
- **Toast singola op**: riutilizzare `typeHtml()` e `brokerHtml()` da `+page.svelte` (stesso layout del delete toast)
- **B1 dati legacy**: la concatenazione nel FormModal è un fallback per vecchie coppie; con la regola di validazione backend (Step 2), le nuove coppie non potranno mai divergere

---

## Addendum: Fix infrastrutturali (fuori scope Phase 07, stesso commit batch)

### A1 — Docker: container non più root

**Problema**: il container Docker girava come `root` → `LibreFolio-data/` creata con `root:root` sull'host, causando problemi di permessi.

**Fix applicati**:

| File | Modifica |
|------|----------|
| `Dockerfile` | Aggiunto `ARG UID=1000`/`ARG GID=1000`, creato utente `librefolio` con UID/GID dell'host, `chown -R /app`, `USER librefolio` |
| `docker-compose.yml` | `build.args` con `UID`/`GID` dall'env, `user: "${UID:-1000}:${GID:-1000}"` per runtime |
| `dev.py` (docker build/rebuild) | `--build-arg UID=$(id -u) GID=$(id -g)` passati automaticamente via `os.getuid()`/`os.getgid()` |
| `.env.example` | Documentate variabili `UID`/`GID` |

### A2 — Font Noto Color Emoji self-hosted

**Problema**: `@import url('https://fonts.googleapis.com/...')` in `app.css` → chiamata esterna bloccante, 23s di attesa quando il CDN Google è lento/irraggiungibile. Incompatibile con deploy self-hosted offline.

**Fix applicati**:

| File | Modifica |
|------|----------|
| `scripts/update_js_cache.py` | Esteso da "JS Library Cache" a "Static Resource Cache Manager": nuovo tipo `"font"` → scarica CSS da Google Fonts, parsa URL woff2, scarica tutti i subset, genera CSS locale con path relativi. Supporto `vendor_dir_key` per directory target diverse |
| `frontend/src/app.css` | Rimosso `@import url(...)` da Google Fonts |
| `frontend/src/app.html` | Aggiunto `<link>` al CSS font locale nel `<head>` |
| `.gitignore` | `frontend/static/fonts/` ignorato (auto-scaricato dal cache system) |
| `.gitattributes` | `*.woff2` marcati come binari per git |

**Flusso**: `./dev.py server` / `./dev.py docker build` → `update_js_cache()` → MathJax + Noto Color Emoji controllati/aggiornati. Se Google Fonts irraggiungibile → mantiene versione cached. Con `--force` → ri-scarica tutto.

### A3 — FX multi-route fallback in `sync_pairs_bulk`

**Problema**: `sync_pairs_bulk` in `fx.py` usava solo la route primaria (`routes[0]`, priority=1). Se BOE falliva (bot protection → HTML instead of CSV), la coppia falliva completamente, ignorando le route di fallback (ECB, FED, SNB) configurate con priorità più bassa.

**Root cause**: Phase 1 raccoglieva legs solo dalla route primaria. Phase 3 faceva `raise FXServiceError` al primo leg fallito senza tentare route alternative.

**Fix applicati** in `backend/app/services/fx.py`:

| Fase | Prima | Dopo |
|------|-------|------|
| Phase 1 (collect legs) | Solo `routes[0]` → `pair_route_map[slug] = route` | Tutte le routes → `pair_routes_map[slug] = [route1, route2, ...]`. Legs raccolti da TUTTE le routes per pre-fetch parallelo |
| Phase 2 (fetch) | Invariato | Invariato (ora fetcha dati per tutti i provider referenziati da tutte le routes) |
| Phase 3 (process) | `_process_route()` monolitica, un solo tentativo | Loop su routes in ordine di priorità. Se legs di una route falliscono → `continue` alla prossima. Log di fallback per diagnostica |
| Compute helpers | Inline in `_process_route()` | Estratti in `_compute_single_step()` e `_compute_multi_step()` per riuso nel loop |

**Comportamento nuovo**: BOE fallisce → log warning "Route 1 failed, trying next route" → ECB/FED tentati automaticamente → sync OK con provider alternativo. L'errore originale della route primaria viene preservato nel campo `errors[]` della risposta per diagnostica.

### A4 — classification_params sovrascritto dall'auto-populate

**Problema**: dopo il salvataggio di un asset con `geographic_area` (distribuzione), l'auto-populate dal provider (justetf) sovrascriveva `classification_params` eliminando `geographic_area`.

**Root cause**: race condition in `bulk_assign_providers()` — l'auto-populate leggeva l'asset dalla sessione aperta PRIMA del commit del PATCH. Il provider restituiva solo `short_description` (senza `geographic_area`), e `apply_partial_update()` applicava il merge sulla versione stale → `geographic_area` perduto.

**Fix applicati** in `backend/app/services/asset_source.py`, funzione auto-populate metadata (riga ~998):

1. **`await session.refresh(asset)`** prima dell'auto-populate → forza re-read dal DB con i dati più recenti (incluso `geographic_area` appena salvato dal PATCH)
2. **Confronto `new_json != asset.classification_params`** prima di scrivere → evita scritture inutili e falsi positivi in `changes_count`

---

## Test mancanti per prevenire regressioni

### Backend (pytest)

| Test | File suggerito | Descrizione |
|------|---------------|-------------|
| **FX fallback sync** | `test_scripts/test_services/test_fx_fallback.py` | Mockare un provider che fallisce (raise `FXServiceError`), verificare che `sync_pairs_bulk` provi la route successiva e ritorni `SyncStatus.OK` con il provider di fallback. Verificare che `errors[]` contenga l'errore della route primaria |
| **FX all routes fail** | stesso file | Mockare tutti i provider per una coppia come falliti → verificare `SyncStatus.FAILED` e che tutti gli errori siano elencati |
| **FX MANUAL-only skip** | stesso file | Coppia con sole routes MANUAL → `SyncStatus.SKIPPED` |
| **classification_params race condition** | `test_scripts/test_api/test_assets_classification.py` | Creare asset → assegnare provider → PATCH con `geographic_area` → GET → verificare che `geographic_area` sia presente. Simulare il timing del race condition: PATCH + provider assignment in rapida successione |
| **classification_params idempotent auto-populate** | stesso file | Asset con `geographic_area` → trigger auto-populate da provider che restituisce solo `short_description` → verificare che `geographic_area` sia preservato |
| **classification_params clear** | stesso file | PATCH con `geographic_area: null` → verificare che viene rimosso |

### Frontend E2E (Playwright)

| Test | File suggerito | Descrizione |
|------|---------------|-------------|
| **Asset geographic distribution save/reload** | `e2e/assets/asset-classification.spec.ts` | Aprire asset modal → impostare distribuzione geografica → salva → riaprire → verificare che la distribuzione sia ancora presente (`data-testid` sui chip/valori della mappa) |
| **Asset geographic distribution clear** | stesso file | Impostare distribuzione → salva → riaprire → rimuovere distribuzione → salva → riaprire → verificare che sia vuota |
| **FX sync con provider in errore** | `e2e/fx/fx-sync-fallback.spec.ts` | Difficile da testare E2E senza mock del provider. Alternativa: verificare che dopo un sync fallito, la UI mostri il messaggio di errore con dettaglio per-route nella response. Intercettare la risposta API e verificare il campo `errors[]` |

### Nota sulla copertura Docker

I fix Docker (A1) non sono testabili con unit/E2E. Verificare manualmente:
```bash
./dev.py docker build && docker compose up -d
ls -la LibreFolio-data/  # owner deve essere $(id -u):$(id -g), non root
docker exec librefolio whoami  # deve essere "librefolio", non "root"
```

---

## Link forward

→ **Round 2**: `plan-phase07-transaction-Part4_Round6_PlanC2Round2_FixRegressionsAndMockFX.prompt.md` — Fix regressions + MockFX + Rimozione auto-populate + Test
