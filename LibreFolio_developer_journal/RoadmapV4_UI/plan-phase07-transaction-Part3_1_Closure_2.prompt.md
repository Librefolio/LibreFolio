# Phase 7 Part 3 Closure — Pending Batches (file _2)

> 📄 **File companion di** [`plan-phase07-transaction-Part3_1_Closure.md`](./plan-phase07-transaction-Part3_1_Closure.md).
>
> Qui risiedono **solo i batch ancora da eseguire**. Per il lavoro già
> completato, le decisioni di design (#R3-1..#R3-4, Policy D R3-3, backup
> endpoint R3-3b), le gotcha e il giornale di viaggio → consultare il file
> principale (parent plan).

**Data di scorporo**: 2026-04-23 pomeriggio (plan parent a ~1700 righe,
spostate sezioni pending per mantenere leggibilità).

**Indice**:
1. **Blocco G** — Test coverage (G.1..G.11) + validazione finale.
2. **Coda I-bis pendente** — 7 ticket tracciati come follow-up (era 14,
   ridotta dopo audit 2026-04-24: 7 erano già DONE — 6 in Batch 2
   + #25 risolto in un commit intermedio).
3. **Retest findings — Batch 2 part4b (#R4-1..#R4-5)** — 5 rifiniture
   chiuse 2026-04-23.
4. **Retest findings — Batch 3 (#R5-1..#R5-3)** — 3 rifiniture chiuse
   2026-04-24.

**Priorità di esecuzione suggerita** (aggiornata 2026-04-24 — decisione
utente):

> **Decisione 2026-04-24**: risolvere **tutti i pendenti I-bis** prima
> di entrare nel Blocco G. Motivazione: il Blocco G scrive test di
> coverage; farlo prima dei fix #2/#5/#7/#22/#24/#26 significherebbe
> testare codice che cambia a breve, con conseguente rewrite dei test.
> Meglio congelare il comportamento, poi coprirlo.

1. ~~Batch 2 **part5b**~~ → ✅ **COMPLETO** (2026-04-23).
2. ~~**Batch 3** = R3-3 Policy D + R3-3b backup endpoints~~ → ✅
   **COMPLETO** (2026-04-23 sera).
3. ~~**Batch 3 part5b** = polish post-retest (`#R5-1..#R5-3`)~~
   → ✅ **COMPLETO** (2026-04-24).
4. **Batch 4** = chiusura I-bis pendenti (~7-8h spalmati in 6 sub-batch
   tematici). **← IN CORSO**
   - **4.a** — #2 Save Without Testing gating (~45 min, FE, P1.5). ✅ DONE
   - **4.b** — #7 HTTP 409 semantics (~30 min, BE, P2). ✅ DONE
   - **4.c** — #26 scheduled_investment Step 2/4 reorder + cache key
     test (~1h + test, P1). ✅ DONE
   - **4.d** — #22 `saveWithRetry` helper + adozione 8 modal (~3-4h, P1,
     prerequisito Part 4/5). 🟡 PARTIAL (helper creato + 2/8 modal
     adottati — vedi sub-batch 4.d-part2 per i restanti)
   - **4.e** — #5 CSV autodetect separator + header tolerance (~1.5h, P2). ⏳ PENDING
   - **4.f** — #24 Backend `changed_points` + FE merge incrementale
     (~1h, P2). ⏳ PENDING
5. **Blocco G** test coverage (8-10h stimati) — dopo Batch 4.
6. **I-bis #19** rinviato formalmente a Phase 8/9 (nessun lavoro qui).

---

## 🧪 Blocco G — Test coverage + API sync (INTERAMENTE PENDENTE)

> **Stato rilevato 2026-04-22**: solo 2 test file base esistono (`test_transaction_service.py`, `test_transactions_api.py`). **6 nuovi file da creare**, 2 estensioni, test_runner da aggiornare, coverage target da verificare.

### G.1 — `test_transaction_service.py` (ESTENDI)

Fixture: OWNER / EDITOR / VIEWER / FOREIGN.

Casi da aggiungere:
- `test_create_bulk_atomic_rollback_on_overdraft`.
- `test_create_bulk_atomic_rollback_on_shorting`.
- `test_create_bulk_atomic_rollback_on_asset_event_mismatch`.
- `test_create_bulk_rejects_broker_mismatch_immediately`.
- `test_update_bulk_requires_editor`.
- `test_update_bulk_rejects_foreign_tx`.
- `test_delete_bulk_requires_editor`.
- `test_delete_bulk_rejects_linked_without_pair` (verificare atomicità).
- `test_query_filters_accessible_brokers_only`.
- `test_query_by_ids_preserves_order`.

### G.2 — `test_transactions_api.py` (ESTENDI)

Matrix **OWNER × EDITOR × VIEWER** × **POST/PATCH/DELETE** × **owned/foreign broker**.

Casi dedicati:
- `test_get_single_by_ids` (sostituto di `GET /transactions/{id}` rimosso).
- `test_get_tx_id_route_is_removed` → 404 (non 405).
- Matrix completa di access control.

### G.3 — `test_transactions_validate.py` (NUOVO)

Path: `backend/test_scripts/test_api/test_transactions_validate.py`.

Casi:
- `test_validate_empty_batch`.
- `test_validate_mixed_creates_updates_deletes` (ordine delete → update → create).
- `test_validate_reports_all_issues_not_just_first`.
- `test_validate_no_side_effect` (DB non modificato).
- `test_validate_would_rollback_true_on_balance_violation`.
- `test_validate_rejects_broker_mismatch`.

### G.4 — `test_events_suggest.py` (NUOVO)

Path: `backend/test_scripts/test_api/test_events_suggest.py`.

Fixture AAPL con eventi `DIVIDEND` a `-5, -3, -1, 0, +1, +3, +5`:
- Parametrizzato `tolerance_days ∈ {0, 3, 7}` → 1, 7, 15 eventi.
- `test_suggest_ordering_by_distance_asc`.
- `test_suggest_type_not_event_compatible` (BUY → skipped).
- `test_suggest_type_mapping_adjustment_to_split_and_price`.
- `test_suggest_preserves_request_order`.
- `test_suggest_max_batch_size` (501 → 422).

### G.5 — `test_prices_currency_coherence.py` (NUOVO, versione post-I.11)

Path: `backend/test_scripts/test_services/test_prices_currency_coherence.py`.

Versione **aggiornata da I.11** (drop dei test su breakdown/normalize, mismatch ora hard-400):

- `test_original_currency_always_populated`.
- `test_backward_fill_info_none_when_all_ok`.
- `test_upsert_rejects_currency_mismatch_hard_400` (sostituisce la versione `via_errors`).
- ~~`test_fx_error_pair_missing`~~ → **DROP** (fx_error cancellato, vedi E.1 closure).
- ~~`test_fx_error_no_rate_at_date`~~ → **DROP**.
- ~~`test_currency_breakdown_single_currency`~~ → **DROP** (I.11).
- ~~`test_currency_breakdown_multi_currency`~~ → **DROP** (I.11).
- ~~`test_sync_all_auto_registers_missing_fx_pairs`~~ → **DROP** (E.4 cancellato).
- ~~`test_normalize_endpoint_converts_dissonant_points`~~ → **DROP** (I.11, endpoint non implementato).

Totale: **3 test case** (ridotti da 9 originali dopo superseding).

### G.6 — `test_ohlc_sentinel.py` (NUOVO)

Path: `backend/test_scripts/test_services/test_ohlc_sentinel.py`.

Copertura Blocco F (F.1–F.4):
- `test_sentinel_minus_one_sets_null_on_close`.
- `test_null_field_is_noop` (merge parziale).
- `test_provider_overrides_user_cleared_field` (F.1: provider > utente).
- `test_current_price_bootstrap_populates_ohlc` (F.2).
- `test_current_price_extends_intraday_low_high` (F.3).
- `test_current_price_preserves_open_if_set` (F.3).
- `test_current_price_volume_not_modified` (F.3).
- `test_volume_minus_one_from_provider_mapped_to_none` (F.4 caveat volume).

### G.7 — `scripts/test_runner.py` (ESTENDI)

Aggiungere entry runner:
- `api/transactions-validate` (→ G.3).
- `api/events-suggest` (→ G.4).
- `services/prices-currency` (→ G.5).
- `services/ohlc-sentinel` (→ G.6).
- `api/assets-currency-change` (→ G.10, da I.11).
- `api/assets-prices-export` (→ G.11, da I.11).
- `api/events-target-currency` (→ E.8, nuovo).

### G.8 — Coverage target

- `transaction_service.py` ≥ **90%**.
- `asset_source.py` (funzioni toccate da Part 3: `upsert_prices_bulk`, `_extend_ohlc_bounds`, sentinel merge) ≥ **85%**.

Comando:
```bash
./dev.py test coverage services transaction
./dev.py test coverage services asset-source
```

### G.9 — Validazione finale Blocco G
```bash
./dev.py format && ./dev.py lint
./dev.py api sync && ./dev.py front check
./dev.py test services transaction
./dev.py test api transactions
./dev.py test api transactions-validate
./dev.py test api events-suggest
./dev.py test services prices-currency
./dev.py test services ohlc-sentinel
./dev.py test api assets-currency-change      # G.10
./dev.py test api assets-prices-export        # G.11
./dev.py test api events-target-currency      # E.8
./dev.py test all-backend
```

### G.10 — `test_asset_currency_change.py` (NUOVO, da I.11)

Path: `backend/test_scripts/test_api/test_asset_currency_change.py`.

Copertura flusso wipe + PATCH + re-sync (I.3 + I.6):
- `test_patch_currency_same_value_noop` (200, no side effect).
- `test_patch_currency_without_prices_succeeds` (200, asset.currency aggiornata).
- `test_patch_currency_with_prices_rejects_409` (409 con `existing_count`, `oldest_date`, `newest_date`).
- `test_patch_currency_after_delete_prices_succeeds` (flow completo: DELETE → PATCH → verify).
- `test_patch_currency_invalid_code_400`.

### G.11 — `test_asset_prices_export.py` (NUOVO, da I.11)

Path: `backend/test_scripts/test_api/test_asset_prices_export.py`.

Copertura endpoint `/prices/export` (I.4):
- `test_export_csv_format_default`.
- `test_export_csv_contains_all_columns` (`date, open, high, low, close, volume, currency, source_plugin_key, fetched_at`).
- `test_export_json_format`.
- `test_export_invalid_format_400`.
- `test_export_empty_prices_returns_header_only`.
- `test_export_requires_asset_access`.
- `test_export_large_dataset_streaming` (>10k righe, StreamingResponse).

---

## 📋 Coda I-bis pendente (dal parent plan)

> **Audit 2026-04-24**: verificata la coda I-bis #1..#26 contro i commit
> reali (`Closure.md` §"Batch 2 part1/part2/part2b") **e contro i
> sorgenti attuali**. Sette ticket che erano listati qui come ⏳ PENDING
> sono in realtà ✅ DONE — spostati in fondo in una sotto-sezione
> "Già risolti".
>
> **Pendenti reali (verificati nei sorgenti)**: 7 ticket — #2, #5, #7,
> #19, #22, #24, #26.

### I-bis #2 — "Save Without Testing?" modal gating  ✅ DONE (2026-04-24, Batch 4.a, commit pending)

**Dove**: `AssetModal.svelte` (sezione provider).
**Cosa**: il modal "Save Without Testing?" compariva ad **ogni** save asset; ora compare solo se `providerCode`, `providerIdentifier`, `providerIdentifierType` o `providerParams` sono diversi dallo stato caricato.

**Implementazione** (Batch 4.a):
- Snapshot iniziale dei 4 campi provider in `loadAssetData()` (`initialProviderCode`, `initialProviderIdentifier`, `initialProviderIdentifierType`, già presente `initialProviderParamsJson`).
- `$derived providerDirty` confronta i valori correnti con lo snapshot; in create mode (`!editMode`) = `hasProvider`.
- `handleSave()` gate: `if (hasProvider && providerDirty && providerTestStatus !== 'passed') → modal`. Edit di soli `name`/`description`/classification → skip modal.

**Retest manuale richiesto**: modificare solo `name` → no modal; modificare `providerCode` → modal compare; cancel → dismiss; confirm → save procede.

### I-bis #5 — CSV Import resilience  ⏳ PENDING

**Dove**: `CsvEditor.svelte`.
**Cosa**:
- (a) Auto-detect separator `;` o `,` dalla prima riga non vuota.
- (b) Header match **tolerante** alle extra-column: ignora colonne non mappate, richiede `date` + `close` presenti.
- (c) Banner inline (I-bis #4, già implementato) documenta il comportamento.

**Target**: rendere re-importabile il CSV generato da `/backup/asset/{id}/prices?format=csv` (ora il round-trip export → import fallisce con "too many fields").

### I-bis #7 — Backend `patch_assets_bulk` HTTP 409 semantics  ✅ DONE (2026-04-24, Batch 4.b, commit pending)

**Cosa**: l'endpoint `PATCH /api/v1/assets` ora ritorna **HTTP 409** quando **tutti** gli item del batch falliscono e almeno uno dei fallimenti riporta il token `CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA`. Nel caso di partial-success (almeno 1 item OK) resta il 200 con payload `success_count + results[]`, preservando la multi-asset semantic.

**Implementazione** (Batch 4.b):
- `backend/app/api/v1/assets.py::patch_assets_bulk`: dopo la chiamata al service, se `response.success_count == 0 and len(results) > 0 and all(not r.success)` e almeno un `r.message` contiene `CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA` → `raise HTTPException(409, detail={error_code, message, results: [...]})`.
- `frontend/src/lib/components/assets/AssetModal.svelte::performSave`: try/catch attorno a `patch_assets_bulk_api_v1_assets_patch`; se `err.response.status === 409` e il detail ha `Array.isArray(detail.results)` → ricostruisce `patchResp = {results: detail.results, success_count: 0}` e prosegue il flusso esistente (destructive currency-change modal). Stessa UX, HTTP semantica corretta.

**Priorità**: P2, non bloccante — chiusa nello stesso commit per simmetria con gli altri sub-batch.

### I-bis #19 — Semantica estesa `Asset.active` (follow-up Phase 8/9)  ✅ DONE (doc-only, 2026-04-24, Batch 4.d-part3)

**Spin-off** da I-bis #17. Regole definitive già consolidate in [`phases/phase-08-scheduler.md`](./phases/phase-08-scheduler.md) §Interazione con Asset.active:

- **Scheduler auto (Phase 8)**: skip inattivi (filtro `asset.active == True` nel daemon loop).
- **Sync manuale frontend**: consentito su inattivi (azione esplicita utente).
- **Dashboard / Portfolio breakdown (Phase 9)**: nasconde inattivi nelle aggregazioni.
- **Badge "📦 Archived"** su card/table/detail page: desiderabile, non bloccante.

**Nessun codice in Phase 7**: l'implementazione operativa è per costruzione deferita alle phase successive (8 = scheduler, 9 = dashboard). Chiusura formale del ticket per non lasciarlo aperto nella coda I-bis.

**Lavoro in questo plan**: **nulla** — si tratta solo del rinvio formale a Phase 8/9. Traccio qui il cross-link per chiudere il cerchio.

### I-bis #22 — Generalizzare error handling "Save failed → keep modal open + toast"  🟡 PARTIAL (2026-04-24, Batch 4.d, commit pending)

**Requisito funzionale**:
Se il save fallisce (HTTP !2xx / network error), la modale:
1. **NON si chiude** (o si riapre con draft ripristinato).
2. Mostra **toast errore** con messaggio da `response.detail` (FastAPI) o fallback i18n.
3. Mantiene dirty state per permettere correzione + retry.

**Stato Batch 4.d (2026-04-24)** — **helper creato + 2 modal adottati**:

Helper nuovo: `frontend/src/lib/utils/saveWithRetry.ts`
- `saveWithRetry<T>(call, options)` — wrappa una Promise, ritorna
  discriminated union `{status: 'success', data} | {status: 'error', message, error, status_code}`. Non solleva mai.
- `extractErrorMessage(err, fallback)` — estrae il detail da errori
  Axios/FastAPI: string, object, Pydantic array `[{msg}]`, statusText,
  `err.message`.
- `extractStatusCode(err)` — helper per route custom (es. 409).
- Opzioni: `fallback` (msg i18n-aware passato dal chiamante), `toast`
  (bool, default `true`), `prefix` (es. nome asset), `onError`
  (pre-hook per custom handling — es. 409 destructive modal).

**Modal adottati**:
1. `BrokerModal.svelte` — create + update ora passano per `saveWithRetry`
   con fallback i18n `brokers.createFailed` / `brokers.updateFailed`.
   La modale resta aperta on error (early `return` dopo `error = result.message`).
2. `AssetCurrencyChangeModal.svelte` — `extractErrorMessage` sostituisce
   3 siti di estrazione manuale `err?.response?.data?.detail || err?.message`.
   Il flusso 3-step (wipe → patch → sync) mantiene le sue `try/catch`
   strutturate ma ora sfrutta l'extractor unificato per coerenza.

**Modal ancora da adottare** (sub-batch **4.d-part2**):
- `AssetModal.svelte` — grosso, ha già custom 409 handling dal 4.b.
  Rischio di regressione: fare una pass dedicata.
- `AssetProviderAssignmentModal.svelte` — TBD.
- `BrokerSharingModal.svelte` — TBD.
- `CashTransactionModal.svelte` — TBD.
- `FxPairAddModal.svelte` — TBD.
- `PriceDataImportModal.svelte` + `EventDataImportModal.svelte` — usano
  il `DataImportModal` generic wrapper, valutare se adottare a livello di
  wrapper (più efficiente).
- `TransactionModal.svelte` — Part 4 (non ancora esistente).
- Save flows di `DataEditor` — censimento necessario.

**Prossimo commit**: `feat(phase07): Batch 4.d-part1 — saveWithRetry helper + adopt Broker/CurrencyChange modals`

**Priorità**: P1 — prerequisito per Part 5 Staging Modal. Il helper è
stabile e retro-compatibile; l'adozione nei restanti modal può
procedere in modo incrementale senza bloccare altri lavori.

### I-bis #24 — Auto-refresh mirato post-sync (last-point-only)  ⏳ PENDING

**Contesto UX**: dopo aver cliccato "Sync" con provider current-price, se l'utente aspetta il debounce del backend e fa refresh manuale della pagina, il nuovo punto compare. Senza refresh non compare → UX incoerente.

**Design proposto**:
1. Backend: `POST /assets/prices/sync` ritorna anche `changed_points: FAPricePoint[]` (delta) oltre ai counter esistenti.
2. Frontend: `mergeChartDataIncremental(newPoints)` — merge puntuale invece di full reload.
3. Empty-state → chart transition in-place quando il primo punto arriva e rientra nella finestra.

**Priorità**: P2 — nice-to-have, sinergia con il payload già strutturato dopo I-bis #1+#23 (DONE).

### I-bis #25 — goBack regression `/fx/{pair}` → `/fx` invece di `/assets/{id}`  ✅ DONE

**Sintomo**: dall'asset detail, click su link FX quick-access → `/fx/{slug}`. Bottone back (`goBack('/fx')`) riporta alla lista `/fx` invece che all'asset detail di origine.

**Risoluzione verificata nei sorgenti 2026-04-24** (`AssetPriceSummary.svelte:96-114`): il link FX è già implementato come `<button onclick={() => goto(fxPairUrl)}>` invece di `<a href>`. Il commento esplicativo inline (righe 99-103) chiarisce:

> _"we intentionally use a `<button onclick={goto(...)}>` instead of an `<a href>` here, because this element is wrapped inside `<Tooltip>` whose internal handlers call stopPropagation/preventDefault on click; a native `<a>` ends up triggering a full-page reload (breaking SPA navigation and resetting the navigationStore stack, which in turn breaks goBack() on the destination page)."_

Il fix (a) è stato applicato probabilmente durante un giro di bugfix del Tooltip; retest utente conferma SPA routing funzionante.

### I-bis #26 — scheduled_investment: reset a initial_value + cache hashing dubbio  ✅ DONE (2026-04-24, Batch 4.c, commit pending)

**Sintomo originale** (BTP Italia 2028):
- Config db_populate originale: `maturation_frequency=SEMIANNUAL`, `generate_interest=True`.
- Utente l'ha modificata a DAILY + `generate_interest=False` dal frontend.
- Dopo sync: primi mesi retta crescente (corretto), poi valori resettati a `initial_value=10000` e piatti.

**Causa radice confermata** (`_generate_schedule_values` in `scheduled_investment.py`):
L'ordine storico era Step 2 (auto-coupon reset) → Step 3 (manual events) → Step 4 (emit value). Per ogni `current_date in all_maturation_dates` con `generate_interest=True`, il reset di `principal` + azzeramento di `total_interest` avveniva **prima** dell'emissione → il punto emesso era sempre il post-reset (piatto su `initial_value`). Con DAILY la maturation era ogni giorno → retta piatta.

Sul sospetto `_cache_key`: **non era la causa**. L'hash MD5 su `model_dump(mode='json')` copre correttamente `maturation_frequency` e `generate_interest` (sono campi `BaseModel` normali, non `exclude_unset`). La ri-sync non mostrava cambi perché il wipe+regen avveniva correttamente ma la serie generata era identica post-reset (retta piatta) indipendentemente dalla frequency. Nessun test `test_cache_key_differs_on_frequency_change` necessario dopo questa verifica.

**Fix applicato** (Batch 4.c):
- `scheduled_investment.py::_generate_schedule_values`: riordinati i passi:
  1. **Step 2** (nuovo) = manual events (era Step 3).
  2. **Step 3** (nuovo) = emit pre-reset value — `values[current_date] = principal + total_interest + event_adjustment` su `current_date in all_maturation_dates`.
  3. **Step 4** (nuovo) = auto-coupon reset (`generate_interest=True`) — era Step 2.
- Commenti inline aggiornati con reference a I-bis #26.

**Test aggiunti** (`test_synthetic_yield_integration.py`):
- `test_generate_interest_daily_emits_pre_reset_value` — assert `values[Jan 2] > 10000` (retta piatta = regression).
- `test_generate_interest_weekly_shows_sawtooth_peaks` — assert ≥5 picchi > `initial_value` (sawtooth WEEKLY).

**Validazione**: `./dev.py test services synthetic-yield-integration` → PASSED (tutti i test preesistenti + 2 nuovi).

**Priorità originale**: P1 — BTP Italia 2028 è asset dimostrativo nel populate, grafico errato visibile durante smoke test. **Risolto.**

---

### 📦 Già risolti (tracciamento storico, 2026-04-22/24)

| # | Ticket | Risolto in |
|---|--------|------------|
| #1 | Post-wipe sync 0 rows — unified handler | ✅ Batch 2 part2 (unified `PriceSyncResponse` 4-stati, commit pre-`8391aac0`) |
| #3 | Tab label "Prices/Events in {currency} {flag}" | ✅ Batch 2 part1 (`AssetDataEditorSection.svelte` + i18n × 4) |
| #4 | Import CSV banner reminder | ✅ Batch 2 part1 (`PriceDataImportModal.svelte` + `EventDataImportModal.svelte`) |
| #6 | Empty-state "Add manually" button | ✅ Batch 2 part1 (`+page.svelte` asset detail) |
| #12 | Toast reduction currency change (5 → 1) | ✅ Batch 2 part2 (3 toast progress → spinner inline + 1 toast finale) |
| #23 | scheduled_investment `status=partial` surface | ✅ Batch 2 part2 (insieme a #1, stesso handler `buildAssetSyncToast`) |
| #25 | goBack FX quick-access link | ✅ Commit intermedio (probabilmente durante refactor Tooltip): `AssetPriceSummary.svelte:108` ora usa `<button onclick={goto}>` con commento esplicativo inline |

**Verifica**: vedere `plan-phase07-transaction-Part3_1_Closure.md` §"Batch 2 part1" e §"Batch 2 part2" per i dettagli implementativi di #1, #3, #4, #6, #12, #23. Per #25 ispezione diretta del sorgente conferma il fix.

---


## Retest findings — Batch 2 part4b (#R4-1..#R4-5)

_Registrato il 2026-04-23 dopo commit di batch 2 part4+5 + part4b. L'utente ha
ripetuto il giro di smoke test manuale: R3-1 ok, R3-2 ok nella sostanza ma con
messaggio migliorabile, R3-4 funziona in backend ma ha 3 rifiniture aperte +
una feature request trasversale. Questi 5 punti diventano il Batch 2 **part5b**
(rifinitura) da eseguire prima di aprire il Batch 3 (R3-3 Policy D)._

### #R4-1 — R3-2: messaggio errore currency-mismatch troppo tecnico  ✅ DONE (2026-04-23, commit `1bff6ad1`)

**Sintomo osservato dall'utente** (asset cambiato da USD a EUR, provider ritorna
solo punti USD):

```
Sync: 1 validation error for FAUpsert
prices
  List should have at least 1 item after validation, not 0 [type=too_short,
  input_value=[], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/too_short
```

**Causa radice**: il filtro pre-count introdotto in part4 scarta correttamente
tutti i punti mismatched e popola `errors = ["N points discarded: currency
mismatch (…)"]`, ma poi il flusso continua a costruire `FAUpsert(prices=[])`
che ha un validator `min_length=1` → l'eccezione Pydantic viene sollevata
**prima** che il ramo "if errors: message = errors[0]" abbia occasione di
scrivere il messaggio custom nel `ProviderSyncResult`.

**Fix proposto** (BE, `services/asset_source._persist_single`):
1. Dopo il filtro pre-count, se `len(accepted_prices) == 0 and mismatch_buckets`:
   - short-circuit → ritorna subito un `ProviderSyncResult(status=FAILED,
     fetched_count=0, stored_count=0, message=errors[0])` **senza**
     istanziare `FAUpsert`.
2. Se `len(accepted_prices) == 0` ma `not mismatch_buckets` (cioè il provider
   ha ritornato zero punti) mantenere il comportamento attuale (OK con
   `fetched_count=0`).
3. Unit test: aggiungere un caso in `test_assets_prices.py` (o
   `test_asset_source.py`) che mocka un provider con payload 100% mismatched
   e verifica:
   - `result.status == "FAILED"`
   - `result.fetched_count == 0`
   - `"currency mismatch" in result.message`
   - nessun `ValidationError` sollevato.

**Estensione FE** (coerenza): lo store/toaster di sync deve continuare a
mostrare `result.message` (già fa così), ma verificare che non ci sia un ramo
che mostra la raw exception prima.

### #R4-2 — R3-4: ConfirmModal deve essere ROSSO, non giallo  ✅ DONE (2026-04-23, commit `1bff6ad1`)

**Sintomo**: il modal "Regenerate Prices?" oggi usa `warning={true}` →
variante gialla. L'utente vuole la variante rossa (distruttiva) perché
l'azione wipa lo storico dei prezzi.

**Fix proposto** (FE, `AssetModal.svelte`):
- Ispezionare `ConfirmModal` (`frontend/src/lib/components/ui/ConfirmModal.svelte`
  o path equivalente) per verificare quale prop gestisce la variante
  "danger/destructive" (tipicamente `danger={true}` o `variant="danger"`).
- Se esiste → sostituire `warning={true}` con `danger={true}` nell'istanza
  `#R3-4` di `AssetModal.svelte`.
- Se non esiste → estendere `ConfirmModal` con un nuovo prop `danger` che
  applica classi Tailwind rosse (`bg-red-600`, `hover:bg-red-700`,
  `text-red-50`) all'icona e al bottone di conferma, mantenendo `warning`
  come default giallo. Allineare `dark:` classes.
- Nessuna modifica i18n richiesta (le 3 chiavi
  `assets.modal.scheduledRegen{Title,Message,Confirm}` restano valide).

**Validazione**: `./dev.py front check` + smoke manuale (screenshot o
ispezione visiva del modal).

### #R4-3 — R3-4: grafico resta retta lineare dopo regen WEEKLY  ✅ DONE (2026-04-23, risolto indirettamente dal commit `8391aac0` — parametric provider refactor)

**Sintomo**: dopo confermato il modal e completato il save, il backend log
dimostra che il wipe+regen è avvenuto correttamente:

```
parametric provider 'scheduled_investment' params changed for asset 12
  — wiped prices and invalidated cache
scheduled_investment cache MISS key=ee4aa952 periods=1 first_freq=WEEKLY
Fetched 120 historical prices for asset 12
scheduled_investment cache HIT key=ee4aa952 periods=1 first_freq=WEEKLY
```

Ma il grafico su `/assets/12` continua a mostrare una retta lineare DAILY,
non i gradini WEEKLY attesi.

**Ipotesi di causa** (da verificare, in ordine di probabilità):
1. **I-bis #26 (pre-esistente)**: bug noto dove `scheduled_investment` resetta
   al valore iniziale / ignora cambi di frequenza → il regen genera punti ma
   tutti con lo stesso valore di `initial_value`, quindi la serie appare come
   retta. Verificare con SQL:
   ```sql
   SELECT date, close FROM price_history
   WHERE asset_id=12 AND source_plugin_key='scheduled_investment'
   ORDER BY date LIMIT 20;
   ```
   Se i `close` sono tutti uguali → è I-bis #26, fixare lì.
2. **Chart reactivity**: `+page.svelte` potrebbe non re-fetchare
   `price_history` dopo che `AssetModal` emette `saved`. Verificare il
   callback `onSaved` → deve invalidare `assetPricesQuery` / ri-invocare
   `loadChartData()`.
3. **Cache frontend**: Zodios/React-Query-like store che serve il vecchio
   payload da cache → controllare che al `saved` venga fatto
   `queryClient.invalidate()` o equivalente.

**Piano di debug**:
1. Aprire DevTools → Network, cambiare params, confermare regen.
2. Verificare che dopo il save parta una `POST /api/v1/assets/prices/query`
   con il `timeRange` corrente.
3. Se la query NON parte → problema 2 (reactivity) → aggiungere invalidazione.
4. Se la query parte ma ritorna i vecchi valori → problema 1 (I-bis #26).
5. Se la query parte e ritorna nuovi valori ma il grafico non si aggiorna →
   problema chart-component reactivity (probabile `$state` vs prop passing).

**Azione**: prima di iniziare il fix, l'utente esegue i passi 1-2 sopra e
riporta quale dei 3 rami è. Il fix vero e proprio è condizionato a questa
diagnosi.

### #R4-4 — BE warning: `FAProviderAssignmentResult` object has no field `metadata_updated`  ✅ DONE (2026-04-23, commit `1bff6ad1`)

**Sintomo** (nel log di save con regen):

```
{"asset_id": 12, "provider": "scheduled_investment",
 "error": "\"FAProviderAssignmentResult\" object has no field \"metadata_updated\"",
 "event": "Failed to fetch metadata from provider",
 "logger": "backend.app.services.asset_source", "level": "WARNING"}
```

**Causa probabile**: in `bulk_assign_providers` (o nel ramo post-assign che
tenta il metadata fetch automatico) qualcuno fa `result.metadata_updated =
True` o `.model_copy(update={"metadata_updated": ...})` ma
`FAProviderAssignmentResult` non dichiara quel campo nello schema Pydantic
(probabile refactor leftover). Il warning è **cosmetico** (non blocca il
flusso), ma sporca i log e indica uno stato incoerente.

**Fix proposto**:
1. `grep -rn "metadata_updated" backend/app/` per localizzare il setter.
2. O aggiungere il campo al modello `FAProviderAssignmentResult` (se
   semanticamente utile per il FE), o rimuovere il setter (se dead code).
3. Valutare: è utile esporre al FE se il metadata è stato aggiornato in-place
   dopo assign? Se sì → aggiungere campo; se no → rimuovere il write.
4. Unit test: verificare che `bulk_assign_providers` per un provider
   parametrico (scheduled_investment) non emetta più quel warning.

### #R4-5 — Feature: toasts in modalità DEV devono loggare anche su console  ✅ DONE (2026-04-23, commit `1bff6ad1` base + `09dba1c3` HTML strip refinement)

**Richiesta**: per tracciamento durante lo sviluppo, ogni toast (success /
error / warning / info) mostrato all'utente deve essere replicato su
`console.log` / `console.warn` / `console.error` quando il build FE è in
modalità debug. In produzione il comportamento resta invariato (nessun
log console).

**Implementazione effettiva** (FE, `frontend/src/lib/stores/toastStore.svelte.ts`):

- Ogni chiamata a `show(variant, message, duration?)` ora specchia il toast
  sulla console via il helper centralizzato `$lib/debug` (`debug.log` /
  `debug.info` / `debug.warn` / `debug.error`), mappando la variante al
  livello console corrispondente (`success→log`, `info→info`, `warning→warn`,
  `error→error`).
- Gate: il helper `debug` è attivo quando `VITE_DEBUG=true` OPPURE
  `import.meta.env.DEV === true`. In build di produzione il blocco è
  tree-shaken → zero overhead, zero leak.
- Prefisso: `[Toast] [<variant>] <message>` (il primo `[Toast]` è iniettato
  dal logger con `console.<level>('[Toast]', ...)`, il secondo è esplicito
  per facilitare il grep a livello di variante).
- **Extra**: aggiunta utility `stripHtmlForLog(message)` che rimuove
  `<svg>…</svg>`, `<img …>`, tutti i tag HTML residui e decodifica le entità
  più comuni, così le icone lucide inline e i badge colorati (che sono
  essenziali nell'UI) non sporcano il log console. La versione UI del toast
  non è toccata.

**Verificato** su flusso `/fx/{pair}` e `/assets/{id}` sync:
- Success → `[Toast] [success] Synced: 🇦🇺 AUD 🇪🇺 EUR 62↓ 0Δ`
- Error → `[Toast] [error] Sync failed for Apple Inc.: 62 points discarded: currency mismatch (got 62 USD, expected EUR)`

**Note collaterali**:
- L'errore di console `"A listener indicated an asynchronous response by
  returning true, but the message channel closed before a response was
  received"` osservato durante lo stesso retest è rumore di un'estensione
  Chrome (origine `fx:1` = documento HTML, non il bundle app) → non
  azionabile lato codice, ignorato.

**Coda** (futuri): pannello debug in-app che raccoglie gli ultimi N toast
per bug report utenti. Non in questo batch.

---

### Priorità suggerita per Batch 2 part5b

| # | Ticket | Area | Sforzo stimato | Priorità | Stato |
|---|--------|------|---------------:|:--------:|:-----:|
| 1 | #R4-1 | BE (short-circuit empty accepted_prices) | 15 min | alta | ✅ DONE |
| 2 | #R4-2 | FE (ConfirmModal variant rosso) | 20 min | alta | ✅ DONE |
| 3 | #R4-4 | BE (rimuovere/aggiungere metadata_updated) | 20 min | media | ✅ DONE |
| 4 | #R4-5 | FE (toast console log in DEV) + HTML strip | 15+10 min | bassa | ✅ DONE |
| 5 | #R4-3 | FE/BE (chart non aggiorna) | 1-3h (dipende da diagnosi) | alta ma bloccante su diagnosi utente | ✅ DONE |

**Stato Batch 2 part5b**: **5/5 completi**. Risoluzioni:

- `8391aac0` (2026-04-23 mattina) — parametric provider refactor + `isParametric`
  rename + dynamic wipe SQL → sblocca rigenerazione corretta (#R4-3).
- `1bff6ad1` (2026-04-23 pomeriggio) — R4-1 + R4-2 + R4-4 + R4-5 base.
- `09dba1c3` (2026-04-23 sera) — R4-5 extension: HTML/SVG strip su console log.

Batch 2 part5b chiuso. Prossimo step: **Batch 3** (R3-3 Policy D + R3-3b backup
endpoints) — design già fissato nel parent plan.

**Nota su #R4-3 resa retrospettiva**: la diagnosi era in 3 rami (I-bis #26,
chart reactivity, FE cache). Il refactor `8391aac0` ha toccato sia backend
(wipe SQL dinamico, `provider_kind`) sia FE (`isParametric` derived in
`+page.svelte`, `AssetModal.svelte` branches). Il retest utente ha
confermato che il grafico ora aggiorna correttamente dopo regen WEEKLY →
chiuso senza bisogno di debug ramo-per-ramo. Se in futuro il sintomo
riemerge su un altro asset parametrico, riaprire con diagnosi network/SQL
come originariamente pianificato.

**Nota su I-bis #2** (warning "Save Without Testing?" su param-only change):
confermato dall'utente — resta tracciato nel TODO futuri, non in questo
batch.

---


## Retest findings — Batch 3 (#R5-1..#R5-3)

_Registrato il 2026-04-24 dopo l'implementazione di Batch 3 (R3-3 Policy D +
R3-3b backup endpoints, commit pending). L'utente ha eseguito la test list
frontend completa (7 sezioni, 29 casi): 28 verdi, 1 bug UX cosmetico, 2
proposte di polish._

### Stato test list 2026-04-24

| Sez | Scope | Esito |
|-----|-------|:-----:|
| 1.x | Backup endpoints standalone (1.1–1.6) | ✅ 6/6 |
| 2.x | Download helper via axiosInstance (2.1–2.3) | ✅ 2/2 + 1 skip |
| 3.x | Flow currency change end-to-end (3.1–3.8) | ✅ 8/8 |
| 4.x | Hard-400 event currency mismatch | ⚠️ API OK, UI inconsistente (vedi #R5-3) |
| 5.x | Regressioni legacy + no-break | ✅ 2/2 |
| 6.  | i18n × 4 | ✅ |
| 7.  | Console pulita | ✅ |

**Verifica DB post-wipe** (asset Apple id=1, dati iniziali):
```
prices | events_manual | events_provider | linked_tx
   253 |             3 |               4 |         2
```
Dopo il flow "Delete & Change Currency" EUR→USD:
```
prices | events_manual | events_provider | linked_tx
     0 |             0 |               0 |         0
```
(post-wipe pre-resync: prezzi e eventi azzerati, transazioni preservate ma
scollegate; resync era 0 perché provider non restituiva dati per il range
richiesto — comportamento atteso).

### #R5-1 — Modal currency change: copy del title/banner da semplificare

**Contesto**: la modal attuale ha title "Change currency — destructive
action" + un paragrafo `body` che ripete in prosa gli stessi dati della
lista bullet sottostante. Risultato: informazione duplicata, cognitive
load alto, e la consequenza importante "le transazioni scollegate sono
responsabilità utente riconnetterle" non è enfatizzata.

**Richiesta utente**: semplificare il title / body per comunicare in
modo asciutto:
1. Cosa: cambio valuta.
2. Conseguenze → vedi lista rossa sotto.
3. Dopo il wipe: il sistema **prova** a risincronizzare prezzi ed
   eventi dal provider.
4. **Caveat**: le transazioni scollegate restano disconnesse —
   l'utente è responsabile di ricollegarle ai nuovi eventi (o
   lasciarle orfane).

**Fix proposto** (FE, `AssetCurrencyChangeModal.svelte` + i18n × 4):

- **Title** (più descrittivo, tono neutro):
  "Change asset currency ({from} → {to})".
- **Body** (1 paragrafo corto, non ripete la lista):
  "Changing the currency requires wiping all stored market data (see
  below). After the wipe, LibreFolio will attempt to re-sync prices
  and events from the provider in the new currency. **Transactions
  that were linked to the deleted events will be disconnected — you
  are responsible for reattaching them to the newly-synced events if
  needed.**"
- **Copy del bullet "linked_tx"**: già in bold red, lasciare invariato.
- **Copy del titolo backup section**: rinominare da
  "Backup current prices before deletion" a
  "Download backup before proceeding" (ora copre anche eventi).

**i18n keys da toccare** (en/it/fr/es):
- `assetDetail.currencyChange.title` — nuovo formato con placeholders
  `{from} {to}`.
- `assetDetail.currencyChange.body` — riscritto, 1 paragrafo asciutto,
  **senza** i contatori (stanno nei bullet).
- `assetDetail.currencyChange.backupTitle` — "Download backup before
  proceeding".
- Rimuovere placeholders obsoleti da `body`: `{prices, events, oldest,
  today}` non più usati lì (i contatori stanno nei `summary*`).

**Effort**: ~20 min (FE + 4 file i18n).

### #R5-2 — Modal backup section: title fuorviante quando ci sono solo eventi

**Contesto**: durante il primo retest (asset con 3 eventi manuali, 0
prezzi), l'utente ha percepito un bug "non compaiono i bottoni export
prezzi". In realtà i bottoni prezzi sono **correttamente nascosti**
(`{#if blocker.prices > 0}`) perché non ci sono prezzi da esportare;
compaiono solo i 2 bottoni eventi. **MA** il titolo della sezione
("Backup current prices before deletion") menziona solo i prezzi → la
dissonanza cognitiva suggerisce "manca qualcosa".

**Fix**: coperto da #R5-1 punto 4 (rinomina `backupTitle` →
"Download backup before proceeding"). Zero codice logic da cambiare,
solo copy.

**Verifica retest atteso**: con la nuova copy, il fatto che compaia solo
"Export events CSV/JSON" quando `prices=0` sarà auto-esplicativo.

### #R5-3 — Event editor FE: colonna `currency` da rimuovere

**Contesto**: l'editor di eventi manuali (accessibile da "Edit Prices &
Events" su asset detail → tab Events) espone una colonna `currency` che
l'utente può liberamente modificare. **Ma** Policy D impone ora:
`event.currency == asset.currency` (hard-400 backend, vedi
`EVENT_CURRENCY_MISMATCH` in `bulk_upsert_events`). Se l'utente inserisce
una currency diversa:
- FE invia il POST.
- BE respinge 400.
- Toast di errore genera confusione ("perché il form mi lascia scegliere?").

**Principio di design**: il frontend deve **impedire** l'input invalido,
non lasciare il backend a rifiutarlo a posteriori. La colonna `currency`
in questo editor è semanticamente redundant — ogni evento eredita la
currency dell'asset.

**Fix proposto** (FE):
1. **Rimuovere la colonna `currency`** dalla tabella di
   `AssetDataEditorSection.svelte` (o dove risiede l'editor eventi).
2. **Nel payload POST**: non inviare più `value.code` per-evento, solo
   `value.amount`. Il backend inserisce `asset.currency` automaticamente
   (già fa così: `currency = evt.value.code or default_currency`).
3. **UI**: aggiungere una nota in cima al tab Events:
   "All events are denominated in the asset's currency ({currency} {flag})".
4. **i18n**: nuova chiave `dataEditor.eventsInAssetCurrency` × 4 (già
   simile a I-bis #3 tab label per prezzi).

**Test backend** (Blocco G.10+): `test_assets_events_hard_400_on_currency_mismatch`
in `backend/test_scripts/test_api/test_assets_events.py` (NUOVO file o
estensione se esiste) — verifica che POST `/assets/events` con un evento
`{value: {code: "USD", amount: "1"}}` su asset EUR ritorni 400 con
`detail` contenente `EVENT_CURRENCY_MISMATCH`.

**Effort**: FE ~20 min, BE test ~15 min.

**Priorità**: media — UI consistency + prevenzione input invalido. Non
blocca Batch 3 commit (il BE ha già il guard hard-400), può essere
nello stesso batch polish.

---

### Priorità suggerita per Batch 3 part5b

| # | Ticket | Area | Sforzo stimato | Priorità | Stato |
|---|--------|------|---------------:|:--------:|:-----:|
| 1 | #R5-1 | FE + i18n (modal copy: title/body split/backupTitle) | 20 min | alta | ✅ DONE |
| 2 | #R5-2 | FE + i18n (subset di #R5-1) | — | — | ✅ DONE (via #R5-1) |
| 3 | #R5-3 | FE (rimuovi colonna currency editor eventi) | 20 min | media | ✅ DONE |

**Stato Batch 3 part5b**: **3/3 completi** (2026-04-24, commit pending).

**Risoluzioni**:
* `AssetCurrencyChangeModal.svelte` — title ora `"Change asset currency
  ({from} → {to})"`; body splittato in `bodyIntro` (tono neutro,
  rimanda alla lista) + `bodyCaveat` (paragrafo rosso bold, enfatizza
  responsabilità utente sulle tx scollegate); `backupTitle` rinominato
  "Download a backup before proceeding".
* `AssetDataEditorSection.svelte` — rimossa colonna `currency` da
  `eventColumns`, da `eventsToEventRows` (sia `values` che
  `_originalValues`), e il payload POST ora fissa
  `value.code = asset.currency` invece di leggere `r.values.currency`.
* i18n × 4 — rimossa chiave obsoleta `body`, aggiunte `bodyIntro` +
  `bodyCaveat`, aggiornate `title` e `backupTitle`.

**Test `test_assets_events_hard_400_on_currency_mismatch`** — rinviato a
Blocco G.10+ come pianificato (BE guard già attivo e verificato via
retest 2026-04-24).

**Nota test list retest**: la sez. 1.3/1.4/3.3 diventa auto-passante —
con la nuova copy del `backupTitle` non c'è più dissonanza cognitiva
quando compaiono solo i bottoni "Export events" senza i corrispondenti
"Export prices".

---

## Proposta Batch 4 — UX quick wins pre-Blocco G (opzionale)

_Registrato il 2026-04-24 dopo audit coda I-bis: l'utente ha chiesto
esplicitamente se proseguire con Blocco G o se restano rifiniture UX
non notate. Questa sezione propone un batch opzionale di quick-win
tra Batch 3 e Blocco G._

**Motivazione**: il Blocco G è ~8-10h di test coverage puri (zero
valore UX percepibile, puro hardening). Prima di entrarci conviene
eliminare 2-3 irritazioni persistenti che l'utente incontra ogni
giorno e che rischiano di accumulare altri retest findings.

### Candidati

| # | Ticket | Tempo | Beneficio | Rischio |
|---|--------|------:|-----------|---------|
| #2 | "Save Without Testing?" gating (dirty-bit provider) | ~45 min | Alto (ogni save asset) | Basso |
| #26 | scheduled_investment reset bug — **solo diagnosi** (log attivati + SQL dump) | ~30 min | Alto se confermato | Zero (no fix) |

**Totale**: ~1h15min per #2 + diagnosi #26. Il fix reale di #26
(inversione Step 2/4 + test cache key) resta per Batch 5 dopo conferma
diagnostica.

### Ordine suggerito

1. **#2** (più impatto, più bassa complessità):
   - Aggiungere `$state provider_dirty: boolean` in `AssetModal.svelte`.
   - `$effect` che traccia `providerCode, providerIdentifier,
     providerIdentifierType, providerParams` contro snapshot iniziale.
   - Nel gate del "Save Without Testing?" modal: `if (!provider_dirty)
     → skip modal, go straight to save`.
   - Retest manuale: modificare solo `name`/`description` → no modal;
     modificare `providerCode` → modal compare; cancel → modal
     dismissed; confirm → save procede.
   - Nessun i18n change.

2. **#26 diagnosi** (no fix, solo dati):
   - Attivare `LIBREFOLIO_LOG_LEVEL=DEBUG` sul server.
   - Ripetere lo scenario BTP Italia 2028: DAILY + generate_interest=True.
   - Catturare log `scheduled_investment cache HIT/MISS` + query SQL
     `SELECT date, close FROM price_history WHERE asset_id=N ORDER BY
     date LIMIT 30`.
   - Aggiungere output al plan sotto §I-bis #26 come "Diagnosi
     2026-04-XX" così Batch 5 può partire dal log reale.

### Commit strategy

**Un commit per ticket** (#2 separato), più 1 commit di solo journal
per la diagnosi #26.

### Decisione utente richiesta

- **Opzione A** — Batch 4 ora (~1h15), poi Blocco G.
- **Opzione B** — Blocco G subito (~8-10h), poi Batch 4 + altri I-bis.
- **Opzione C** — Solo #2 ora (45 min, il tuo annoyance principale),
  poi Blocco G, poi il resto.

Raccomandazione mia: **Opzione C**. #2 è l'unico ticket che l'utente
ha menzionato esplicitamente come persistente, #26 può aspettare il
giro diagnostico dopo Blocco G.


---

## Retest Batch 4 — esiti sezione per sezione (2026-04-24)

_Registrato dopo giro di smoke test manuale della [checklist
4.a/4.b/4.c/4.d-part1](./checklist-phase07-batch4-pretest.md)._

### Esiti sintetici

| Sezione | Ticket | Esito | Note |
|---------|--------|:-----:|------|
| 1.1 | #2 edit nome → no modal | ✅ | |
| 1.2 | #2 edit identifier → modal | ✅ | |
| **1.3** | **#2 edit providerCode → modal** | ❌ → ✅ | **bug trovato, fix applicato (vedi #R6-1)** |
| 1.4 | #2 edit providerParams | ✅ | + banner regenerate prezzi (corretto) |
| 1.5 | #2 Test Provider → no modal | ✅ | |
| 1.6 | #2 create con provider | ✅ | |
| 1.7 | #2 create senza provider | ✅ | |
| Bonus | Search + Save → no modal | ✅ | testStatus='passed' via autoTriggerProbe |
| 2.1 | #7 currency change con prezzi | ✅ | HTTP 409 in Network tab, UX invariata |
| 2.2 | #7 currency change senza prezzi | ✅ | 200, no 409 |
| 2.3 | #7 bulk multi-asset misto | ⏭️ | skippato — richiede curl raw |
| 3.x | #26 sawtooth + DAILY/WEEKLY | ✅ con caveat | → vedi #R6-2 e #R6-3 |
| 4.1 | #22 Broker create happy | ✅ | |
| 4.2 | #22 Broker duplicato | ✅ | banner inline, no toast (utente conferma OK) |
| 4.3 | #22 Broker update happy | ✅ | |
| 4.4 | #22 Broker update offline | ✅ | banner inline + toast, modal resta aperta |
| 4.5 | #22 Backup export offline | ✅ | toast `Download a backup before proceeding: Network Error` |
| 4.6 | #22 wipe fallisce | ⏭️ | skippato — invasivo |
| 4.7 | #22 post-wipe sync fallisce | ⏭️ | skippato |
| 4.8 | #22 uniformità console toast | ✅ | `[Toast] [error] <prefix>: <detail>` coerente |
| R.1..R.4 | regressione | ✅ | login, asset detail, i18n, console pulita |

### #R6-1 — I-bis #2 bug: cambio `providerCode` droppa silenziosamente il save  ✅ FIXED (2026-04-24, Batch 4 post-retest)

**Sintomo** (test 1.3): dall'edit asset, cambio del dropdown provider
(Yahoo → JustETF) senza cliccare Test. Atteso: modal "Save Without
Testing?". Osservato: **nessun modal, nessuna chiamata `/provider`, il
nuovo provider non viene persistito** (alla riapertura dell'edit il
provider è ancora Yahoo).

**Causa radice**: `ProviderAssignmentSection.handleProviderChange` azzera
l'`identifier` on purpose (formati ID diversi tra provider). Con
identifier vuoto e `identifierType='TICKER'`, `hasProvider` diventa
`false`. Questo produce una doppia regressione:
1. Il gate `handleSave` (`hasProvider && providerDirty && !passed`)
   non triggera il modal perché `hasProvider=false`.
2. In `saveEdit` lo Step 2 ha due rami:
   - `if (providerNoProvider) → remove` — skip, l'utente non ha spuntato "No provider".
   - `else if (hasProvider) → assign` — skip, `hasProvider=false`.
   Risultato: il PATCH asset parte (aggiorna solo metadata), ma il
   provider change viene droppato silenziosamente. Nessun feedback.

**Fix applicato** (`AssetModal.svelte::handleSave`):
Aggiunta pre-guard prima del gate modal:
```ts
if (editMode && providerDirty && !providerNoProvider && providerCode !== '' && !hasProvider) {
    formError = $t('assets.modal.providerIncomplete');
    // scroll error into view
    return;
}
```
Se l'utente ha cambiato provider ma non completato l'identifier, viene
mostrato un errore esplicito "You changed the provider but left the
identifier empty. Please fill the identifier (or tick 'No provider')
before saving."

**i18n × 4**: nuova chiave `assets.modal.providerIncomplete` in
`en.json`, `it.json`, `fr.json`, `es.json`.

**Validazione**: `./dev.py front check` → 0/0. Retest manuale 1.3 da
ripetere.

### #R6-2 — scheduled_investment: `current_price` non considera eventi sottrattivi  ✅ FIXED (2026-04-24, Batch 4 post-retest)

**Sintomo osservato dall'utente** (retest sezione 3): il
`current_price` del provider `scheduled_investment` ritorna il valore
giornaliero calcolato **dall'inizio dello schedule** senza considerare
gli eventi sottrattivi (coupon già pagati, PRICE_ADJUSTMENT negativi)
che ci sono stati nel mezzo. Risultato: con `generate_interest=True`,
il valore corrente mostrato è il **picco pre-reset** dell'ultima
maturation date invece del valore accruato intra-ciclo.

**Causa radice** (`scheduled_investment.py::get_current_value`):
quando `target_date` non è in `cached` (cioè in mezzo a due maturation
dates, caso tipico per SEMIANNUAL/WEEKLY), il ramo di fallback faceva
un backward-fill:
```python
earlier_dates = [d for d in cached.keys() if d <= target_date]
value = cached[max(earlier_dates)]  # = picco pre-reset del coupon precedente!
```
Post fix 4.c i valori cached sono pre-reset (corretto per il grafico),
ma il backward-fill così fatto ritorna un valore stantio: oggi (Oct 15)
dopo il coupon del 1 luglio dovrebbe essere ~principal + 3.5 mesi di
accrual, non il picco di luglio.

**Fix applicato**: nuovo helper `_compute_value_at(schedule, target_date)`
che **ri-walka** lo schedule giorno per giorno fino a `target_date`
applicando gli stessi Step 1-4 di `_generate_schedule_values`:
- Step 1 — accrual giornaliero.
- Step 2 — applicazione eventi manuali (INTEREST sottrattivo,
  PRICE_ADJUSTMENT additivo).
- Step 3 — se siamo al `target_date` → emetti il valore corrente e
  interrompi.
- Step 4 — altrimenti, se è una maturation date con
  `generate_interest=True`, applica il reset e continua.

Il ramo "between maturation" di `get_current_value` ora chiama
`_compute_value_at` invece del backward-fill. Gli altri rami
(post-maturity, before-schedule, exact cached date) restano invariati.

**Costo**: O(days-since-start). Per schedule di 10 anni = 3650 iterazioni
in Python puro, ~50-100ms wall. Accettabile perché chiamato solo al sync
del current price (non nel hot path). Nessun caching aggiunto — la
semantica "giorno specifico" non beneficia del cache tuple esistente.

**Test regression aggiunti** (`test_synthetic_yield_integration.py`):
- `test_compute_value_at_semiannual_after_first_coupon_is_close_to_principal`:
  dopo coupon SEMIANNUAL + 1 giorno, valore ~principal (non ~peak).
- `test_compute_value_at_semiannual_mid_cycle_grows_monotonically`:
  serie Aug<Sep<Oct nel mid-cycle post-coupon.
- `test_compute_value_at_respects_manual_interest_subtractive_event`:
  un evento INTEREST manuale riduce il valore sulla sua data.
- `test_compute_value_at_returns_none_outside_schedule`: edge case.

Tutti verdi: `./dev.py test services synthetic-yield-integration` → PASSED.

### #R6-3 — Scheduled Investment: frequenze prezzi/cedola disaccoppiate + anchor date  📋 TRACCIATO IN TODO_FUTURI

**Richiesta utente**: "se attiviamo il flag della cedola, ogni volta
che si genera l'evento, si resetta anche il valore, potrebbe servire
estendere sia il json di scheduling che la tabella sul frontend per
permettere di scegliere la frequenza di calcolo dei prezzi e se la
cedola è attiva la frequenza di calcolo della cedola, ed eventualmente
il giorno del mese/settimana/anno in cui cade."

**Stato**: design proposto ma **non implementato in questo batch** —
richiede estensione schema Pydantic + nuovo enum `CouponAnchor` + 3
campi FE + retrocompatibilità + test parametrici. Costo stimato 7-10h.

Tracciato come TODO futuro in
[`TODO_FUTURI.md`](../../TODO_FUTURI.md) §"Scheduled Investment —
Frequenze disaccoppiate (prezzi vs cedola) + anchor day".

---

### Priorità Batch 4 post-retest

| # | Ticket | Area | Stato |
|---|--------|------|:-----:|
| 1 | #R6-1 | FE (AssetModal pre-guard) + i18n × 4 | ✅ FIXED |
| 2 | #R6-2 | BE (scheduled_investment current_price) + 4 test regression | ✅ FIXED |
| 3 | #R6-3 | Scheduling flexibility | 📋 TODO_FUTURI |
| 4 | #R6-4 | BE (asset_source param-change event wipe + tx disconnect) | ✅ FIXED |
| 5 | #R6-5 | FE (AssetModal auto-sync also on non-parametric provider change) | ✅ FIXED |
| 6 | #R6-6 | UX (BrokerImportFilesModal: adottare toast per upload) | ⏳ PENDING |
| 7 | #R6-7 | UX (BrokerImportFilesModal: ConfirmModal prima di bulk delete) | ⏳ PENDING |
| 8 | #R6-8 | UX (BrokerSharingModal: success → toast + chiude, non banner) | ⏳ PENDING |

**Stato Batch 4 aggiornato**:
- 4.a #2 Save Without Testing gating → ✅ DONE + post-retest fix #R6-1.
- 4.b #7 HTTP 409 semantics → ✅ DONE.
- 4.c #26 scheduled_investment pre-reset value → ✅ DONE + retest bonus #R6-2 (current_price intra-cycle accrual) + #R6-4 (event wipe on params change).
- 4.d-part1 #22 saveWithRetry helper + 2 modal → ✅ DONE.
- 4.d-part2 #22 saveWithRetry adozione 5 modali residui (PasswordChange, FxPairAdd, BrokerImportFiles, BrokerSharing, AssetModal) → ✅ DONE + bonus #R6-5 (auto-sync su provider change) + 3 design-drift findings #R6-6/#R6-7/#R6-8 emersi in retest (sub-batch 4.d-part3 da pianificare).
- 4.e #5 CSV resilience → ⏳ TBD.
- 4.f #24 changed_points delta → ⏳ TBD.

**Batch 4 commit ready**: tutto il lavoro pendente (parts 4.a/4.b/4.c/4.d
+ findings #R6-1..#R6-5) è in blocco nel working tree, pronto per il
commit unico. Validazione finale 2026-04-24: `./dev.py lint` → passed,
`./dev.py front check` → 0 errors / 0 warnings, `./dev.py i18n audit` →
897 keys all complete.

I findings #R6-6/#R6-7/#R6-8 **non bloccano** il commit Batch 4 (sono
drift di design emersi solo durante il retest, non regressioni
introdotte da 4.d-part2 — il comportamento oggetto delle modifiche è
conforme a quanto pianificato). Verranno affrontati in un follow-up
dedicato **Batch 4.d-part3** post-commit.

---

### Retest Batch 4.d-part2 — esiti happy/bad-flow (2026-04-24)

Checklist completa eseguita: vedi `/tmp/libreFolio_batch4dPart2_retest_checklist.md` (5 modali, 28 check).

**Esiti sintetici**

| Modal | Happy | Bad (network/validation) | Semantica speciale | Finding |
|-------|:-----:|:------------------------:|:------------------:|:-------:|
| 1. PasswordChangeModal | ✅ | ✅ | ✅ (onError + InfoBanner preservato) | — |
| 2. FxPairAddModal | ✅ | ✅ | ✅ (auto-sync isolation) | — |
| 3. BrokerImportFilesModal | ✅ (senza toast) | ✅ | 🟡 design obsoleto | **#R6-6**, **#R6-7** |
| 4. BrokerSharingModal | ✅ (ma banner post-success invece di toast+close) | ✅ | 🟡 design obsoleto | **#R6-8** |
| 5. AssetModal (5a/5b/5c/5d) | ✅ | ✅ | ✅ (409 dup + 409 currency + #R6-5 auto-sync) | — |
| 5e. #R6-1 pre-guard | ⏭️ SKIP (già testato in 4.a retest) | ⏭️ SKIP | — | — |
| 3c-2 bulk delete partial | ⏭️ SKIP (richiede mock backend) | — | — | — |

**Conclusione**: `saveWithRetry` è adottato correttamente in tutte le 5
modali — modale-resta-aperta, errori non consumati, semantiche
preservate. Tre drift di design rispetto all'app evoluta sono emersi
come sotto-findings indipendenti dall'adozione del helper.

---

### #R6-6 — BrokerImportFilesModal: adottare toast per upload  ⏳ PENDING

**Origine**: retest 4.d-part2 sezione 3a (2026-04-24).

**Problema**: l'upload files attualmente **non emette toast** né di success
né di errore (affida il feedback a `error` inline della modale e al refresh
della lista). Questo era coerente con il design originale della modale
(gestionale, resta aperta) ma **non è più coerente** con il resto dell'app
evoluto, dove ogni save produce toast conferma.

**Fix proposto**:
- In `BrokerImportFilesModal.svelte`, loop upload: per ogni file
  caricato con successo emettere `toast.success($t('uploads.uploadSucceeded', {values: {file: file.name}}))`.
- Al termine del loop, se almeno 1 success → toast riepilogo
  (`$t('uploads.uploadBatchSucceeded', {values: {count}})`), se tutti
  fail → toast error già gestito da `saveWithRetry` (di per sé ok).
- Errore singolo file: passare a `toast: true` in `saveWithRetry` per
  avere toast dedicato con `prefix: file.name`.

**i18n nuove × 4**: `uploads.uploadSucceeded`, `uploads.uploadBatchSucceeded`
(verificare se già esistenti — alcune chiavi `uploads.*` ci sono già).

**File**:
- `frontend/src/lib/components/brokers/BrokerImportFilesModal.svelte`
  → handler upload (funzione loop già migrata in 4.d-part2).
- `frontend/src/lib/i18n/{en,it,fr,es}.json`.

**Effort**: ~30 min. **Rischio**: basso.

---

### #R6-7 — BrokerImportFilesModal: ConfirmModal prima di bulk delete  ⏳ PENDING

**Origine**: retest 4.d-part2 sezione 3c-1 (2026-04-24).

**Problema**: l'azione "Delete selected" su N file si esegue **senza
conferma**. È una distruzione bulk irreversibile — il design attuale
dell'app usa `ConfirmModal` (rosso, destructive) per tutte le azioni
analoghe (delete asset, delete transaction, revoke access, ecc.).

**Fix proposto**:
- Aggiungere `ConfirmModal` destructive con:
  - title `$t('uploads.confirmBulkDelete.title')`
  - message `$t('uploads.confirmBulkDelete.message', {values: {count}})`
  - variant `destructive`
  - confirm label `$t('common.delete')`.
- Il PUT/DELETE bulk parte solo dopo `onconfirm`.

**i18n nuove × 4**: `uploads.confirmBulkDelete.title`, `uploads.confirmBulkDelete.message`.

**File**:
- `frontend/src/lib/components/brokers/BrokerImportFilesModal.svelte`
  → gating del bulk delete tramite stato `confirmBulkDeleteOpen`.
- `frontend/src/lib/i18n/{en,it,fr,es}.json`.

**Effort**: ~20 min. **Rischio**: basso. **Priorità**: medio-alta
(gap UX evidente).

---

### #R6-8 — BrokerSharingModal: success → toast + close (non banner)  ⏳ PENDING

**Origine**: retest 4.d-part2 sezione 4 (2026-04-24).

**Problema**: il save sharing termina **success** mostrando un **banner
inline** e **lasciando la modale aperta**. Il pattern corretto (e
uniforme con il resto dell'app dopo l'evoluzione del design) è:
- success → `toast.success(...)` + `onclose()` della modale.
- error → banner inline persistente (attuale comportamento del ramo error
  è ok, da mantenere).

**Fix proposto** in `BrokerSharingModal.svelte::handleSave`:
```ts
const result = await saveWithRetry(/* ... */);
if (result.status === 'ok') {
    toast.success($t('brokers.sharing.saveSucceeded'));
    onclose();
    return;
}
// ramo error invariato: banner inline via `error = result.message`
```

Rimuovere `successMessage` / banner di success dal markup se presente.

**i18n nuova × 4**: `brokers.sharing.saveSucceeded` (verificare se già
esistente).

**File**:
- `frontend/src/lib/components/brokers/BrokerSharingModal.svelte`.
- `frontend/src/lib/i18n/{en,it,fr,es}.json`.

**Effort**: ~15 min. **Rischio**: basso.

---

### Sub-batch 4.d-part3 (follow-up pianificato)

Raccogliere #R6-6 + #R6-7 + #R6-8 in un sub-plan dedicato
`plan-phase07-transaction-Part3_1_Closure_2-Batch4dPart3.prompt.md`
**dopo** il commit Batch 4. Effort totale stimato: ~1h15 + i18n audit.
Ordine consigliato: #R6-7 (ConfirmModal, maggiore impatto UX) → #R6-8
(simmetria pattern) → #R6-6 (cosmetico, toasts).


