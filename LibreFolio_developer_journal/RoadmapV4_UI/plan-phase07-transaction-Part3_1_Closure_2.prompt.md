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
2. **Coda I-bis pendente** — 14 ticket tracciati come follow-up.
3. **Retest findings — Batch 2 part4b (#R4-1..#R4-5)** — 5 rifiniture
   emerse dal giro di smoke test 2026-04-23 pomeriggio.

**Priorità di esecuzione suggerita** (ordine consigliato):
1. ~~Batch 2 **part5b** = #R4-1 + #R4-2 + #R4-4 + #R4-5 (quick wins ~70 min)
   + diagnosi #R4-3~~ → ✅ **COMPLETO** (commit `8391aac0` + `1bff6ad1` +
   `09dba1c3`, 2026-04-23).
2. ~~**Batch 3** = R3-3 Policy D + R3-3b backup endpoints~~ → ✅
   **COMPLETO** (2026-04-23 sera, commit pending): nuovo `backup_router`
   con snapshot per-series (prezzi/eventi/FX), endpoint
   `POST /assets/{id}/market-data/wipe` per Policy D (wipe simmetrico +
   disconnect tx), hard-400 su event currency mismatch, nuovo token
   blocker `CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA`, FE modal riscritta
   con summary eventi/tx + 4 bottoni export, helper
   `backupDownload.ts` via axiosInstance (cookie auth + 401 interceptor),
   i18n × 4. **Retest 2026-04-24**: 28/29 test verdi, 3 rifiniture
   UX/cleanup emerse → Batch 3 **part5b** (vedi §Retest findings sotto).
3. ~~**Batch 3 part5b** = polish post-retest (`#R5-1..#R5-3`, ~45 min)~~
   → ✅ **COMPLETO** (2026-04-24, commit pending).
4. Blocco G test coverage (8-10h stimati). **← PROSSIMO**
5. Coda I-bis in priorità decrescente (#22 prerequisito Part 4/5 prima,
   poi #25, #26, #24, #1, #2, ecc.).

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

Tutti i punti ⏳ dalla lista priorità al §I-bis Part3. Mantengo la numerazione originale.

### I-bis #3 — Tab label "Prices in {currency} {flag}"  ⏳ PENDING

**Dove**: `AssetDataEditorSection.svelte`, riga tab Prices/Events.
**Cosa**: label a destra "Prices in USD 🇺🇸" / "Events in USD 🇺🇸".
**i18n**: `dataEditor.pricesInCurrency`, `dataEditor.eventsInCurrency` × 4.
**Utility**: `getCurrencyInfo(asset.currency).flag_emoji`.

### I-bis #4 — Import CSV banner reminder  ⏳ PENDING

**Dove**: `PriceDataImportModal.svelte`, sopra la textarea.
**Cosa**: `InfoBanner` "Currency must match asset currency ({currency} {flag}). Extra columns in the CSV (like `currency`, `source_plugin_key`, `fetched_at` from Export) are ignored on import."
**i18n**: `import.csv.currencyReminder`, `import.csv.extraColumnsIgnored` × 4.

### I-bis #5 — CSV Import resilience  ⏳ PENDING

**Dove**: `CsvEditor.svelte`.
**Cosa**:
- (a) Auto-detect separator `;` o `,` dalla prima riga non vuota.
- (b) Header match **tolerante** alle extra-column: ignora colonne non mappate, richiede `date` + `close` presenti.
- (c) Banner inline (I-bis #4) documenta il comportamento.

**Target**: rendere re-importabile il CSV generato da `/prices/export?format=csv`.

### I-bis #6 — Empty-state "Add manually" button  ⏳ PENDING

**Dove**: panel asset con zero prezzi.
**Cosa**: aggiungere secondo bottone "Add manually" accanto a "Sync from provider", che apre l'edit panel pre-filtrato su tab Prices con riga vuota.
**i18n**: `assetDetail.addPricesManually` × 4.

### I-bis #1 — Surface errori sync post-wipe (currency change flow)  ⏳ PENDING

**Contesto**: se provider post-wipe restituisce currency diversa da quella nuova dell'asset, `bulk_upsert_prices` respinge hard-400 ma l'errore non arriva al frontend in modo leggibile.

**Da fare**:
- (a) Toast di errore esplicito invece di "Prices refreshed" quando `success_count>0` ma `inserted_count==0`.
  - i18n: `sync.postWipeZeroRows` × 4.
- (b) Banner inline full-width sul detail page con lo stesso messaggio finché l'utente non risolve.
- (c) Backend: `POST /prices/sync` surface per-asset `{inserted, errors[]}` in risposta (probabilmente già presente, verificare).

### I-bis #2 — "Save Without Testing?" modal gating  ⏳ PENDING

**Dove**: `AssetModal.svelte` (sezione provider).
**Cosa**: il modal "Save Without Testing?" compare oggi ad **ogni** save asset. Deve comparire solo se `providerCode`, `providerIdentifier`, `providerIdentifierType` o `providerParams` sono diversi dallo stato caricato.

**Implementazione**: traccia dirty-bit separato sul blocco provider + gate su quello.

### I-bis #7 — Backend `patch_assets_bulk` HTTP 409 semantics  ⏳ PENDING non urgente

**Cosa**: alzare HTTP status a 409 quando **tutti** gli item del batch falliscono per `CURRENCY_CHANGE_BLOCKED_BY_PRICES`. Senza rompere la multi-asset semantic (200 se alcuni passano).

**Priorità**: P2, non bloccante.

### I-bis #12 — Ridurre i 5 toast del currency change a 1  ⏳ PENDING refactor medio

**Contesto**: flusso currency change emette 5 toast in sequenza (3 progress + 1 finale + 1 generico "updated").

**Design**:
- Sostituire i 3 toast progress con **un unico toast loading** (o spinner inline nel modal).
- Mostrare solo il toast finale "Currency changed from X to Y. Prices refreshed."
- Sopprimere il toast generico "`{name}` updated successfully" quando PATCH arriva via currency-change flow (flag interno al chiamante).

### I-bis #19 — Semantica estesa `Asset.active` (follow-up Phase 8/9)  ⏳ PENDING

**Spin-off** da I-bis #17. Regole definitive già consolidate in [`phases/phase-08-scheduler.md`](./phases/phase-08-scheduler.md) §Interazione con Asset.active:

- **Scheduler auto (Phase 8)**: skip inattivi (filtro `asset.active == True` nel daemon loop).
- **Sync manuale frontend**: consentito su inattivi (azione esplicita utente).
- **Dashboard / Portfolio breakdown (Phase 9)**: nasconde inattivi nelle aggregazioni.
- **Badge "📦 Archived"** su card/table/detail page: desiderabile, non bloccante.

**Lavoro in questo plan**: **nulla** — si tratta solo del rinvio formale a Phase 8/9. Traccio qui il cross-link per chiudere il cerchio.

### I-bis #22 — Generalizzare error handling "Save failed → keep modal open + toast"  ⏳ PENDING prerequisito Part 4/5

**Requisito funzionale**:
Se il save fallisce (HTTP !2xx / network error), la modale:
1. **NON si chiude** (o si riapre con draft ripristinato).
2. Mostra **toast errore** con messaggio da `response.detail` (FastAPI) o fallback i18n.
3. Mantiene dirty state per permettere correzione + retry.

**Step preliminare (censimento)**: mappare tutti i modal × endpoint × comportamento attuale on-error. Candidati:
- `AssetModal.svelte`, `AssetProviderAssignmentModal.svelte`, `AssetCurrencyChangeModal.svelte`, `BrokerModal.svelte`, `TransactionModal.svelte` (Part 4), `PriceDataImportModal.svelte`, `EventsModal.svelte`, flussi Save di `DataEditor`.

**Design proposto**: helper `$lib/utils/saveWithRetry.ts` o pattern store `createSaveAction<T>({call, onSuccess, onError})`:
- Intercetta HTTP errors + parse `detail`.
- Mostra toast via `toast.error(...)`.
- Ritorna union `{status: 'success', data} | {status: 'error', message}`.

**Priorità**: P1 — prerequisito per Part 5 Staging Modal.

### I-bis #25 — goBack regression `/fx/{pair}` → `/fx` invece di `/assets/{id}`  ⏳ PENDING (nuovo, 2026-04-22 batch 2 part2 retest)

**Sintomo**: dall'asset detail, dopo aver cliccato il nuovo link FX quick-access (I-bis #4 part1c), si arriva a `/fx/{slug}`. Cliccando il bottone back in testa alla pagina FX detail (`data-testid="fx-detail-back-btn"`, handler `goBack('/fx')`), si viene riportati alla lista `/fx` invece che all'asset detail di partenza.

**Analisi**:
- `navigationStore.goBack(fallbackPath)` usa `history.back()` se `depth > 1`, altrimenti `goto(fallbackPath)`.
- `afterNavigate` in `(app)/+layout.svelte` chiama `trackNavigation(nav.type)` che incrementa `depth` per navigazioni non-popstate.
- Normalmente: asset detail (depth=1 entering) → click `<a href>` → depth=2 → FX detail → goBack → depth>1 → history.back() → torna asset detail. **Dovrebbe funzionare**.
- Possibili cause del glitch:
  1. `fx/[pair]/+page.svelte:662` fa `goto(..., {replaceState: true})` quando rileva inversione pair → sovrascrive l'entry history dell'asset detail.
  2. Il mio `<a href="/fx/...">` navigazione potrebbe essere intercettata prima che `afterNavigate` scatti (edge case SvelteKit).
  3. Depth potrebbe essere **reset** o sbagliato a causa di preload/prefetch dei dati.

**Fix proposti (da provare in ordine)**:
- (a) **Quick win**: sostituire `<a href={fxPairUrl}>` con `<button onclick={() => goto(fxPairUrl)}>` in `AssetPriceSummary.svelte` — forza esplicitamente SPA routing.
- (b) Investigare `fx/[pair]/+page.svelte:662` `replaceState:true` — valutare se limitarlo ai soli casi dove l'URL era già `/fx/{pair}`.
- (c) **Fallback robusto**: salvare `document.referrer` (o URL corrente prima del click) in `sessionStorage['fxDetail.returnTo']`. FX detail `goBack` legge questa key e se valida (URL interno) fa `goto(returnTo)` invece di usare solo `depth`.

**Priorità**: P2 — la navigazione browser (Alt+Left) funziona, solo il bottone custom ha comportamento incoerente.

### I-bis #26 — scheduled_investment: reset a initial_value + cache hashing dubbio  ⏳ PENDING (nuovo, 2026-04-23 batch 2 part3)

**Sintomo** (BTP Italia 2028):
- Config db_populate originale: `maturation_frequency=SEMIANNUAL`, `generate_interest=True`.
- Utente l'ha modificata a DAILY + `generate_interest=False` dal frontend.
- Dopo sync: **primi mesi** retta crescente (corretto), poi i valori si **resettano a `initial_value=10000`** e restano piatti.
- Modificando di nuovo (DAILY → WEEKLY) + risync: **nulla cambia** → sospetto hashing `_cache_key` non rileva la variazione.

**Analisi del codice** (`backend/app/services/asset_source_providers/scheduled_investment.py:326+`):

```python
# Step 2: reset on maturation + generate_interest=True
if current_date in all_maturation_dates and period and period.generate_interest:
    if interest_amount > 0:
        auto_events.append(INTEREST event)
        total_interest = Decimal("0")   # RESET
        event_adjustment = Decimal("0")

# Step 4: emit value AT maturation dates (AFTER reset!)
if current_date in all_maturation_dates:
    values[current_date] = principal + total_interest + event_adjustment
```

**Bug candidati**:
1. **Ordine Step 2 prima di Step 4**: il value emesso a una maturation_date con `generate_interest=True` è **sempre `principal`** (post-reset). Con DAILY + gen_interest=True → ogni giorno reset → serie piatta a 10000. Se lo schedule ha un primo periodo senza reset seguito da uno con reset, si vedrebbe proprio il pattern "retta poi piatto".
2. **Hashing opacità**: `_cache_key` = `md5(sort_keys(model_dump(mode='json')))`. Dovrebbe rilevare ogni cambio. Se non lo fa:
   - (a) Il frontend NON invia davvero i nuovi `provider_params` nel PATCH (verificare devtools network).
   - (b) Il backend rifiuta silenziosamente l'update (verificare `assign_providers_bulk` endpoint).
   - (c) Edge case Pydantic: un campo con `default_factory` o `exclude_unset` non serializzato.

**Azioni fatte in questa sessione (batch 2 part3)**:
- `db_populate`: BTP Italia 2028 → `DAILY` + `generate_interest=False` (come richiesto). Dopo `./dev.py db create-clean` deve dare una retta pulita per 4 anni — ottimo regression test visuale.
- Logging debug in `_generate_schedule_values`: `cache HIT/MISS key=... periods=N first_freq=... first_gen_int=...`. Prossimo retest con log DEBUG attivi permette di vedere se il cache key cambia realmente tra edits.
- Attivare log: `LIBREFOLIO_LOG_LEVEL=DEBUG ./dev.py server start` oppure filtro grep sul server log per `scheduled_investment cache`.

**Fix proposti (batch 3+)**:
- **Bug reset**: invertire l'ordine degli step — emettere value PRE-reset (crescita reale visibile in grafico), poi reset per ciclo successivo. Mantiene gli INTEREST events come payout ma mostra la crescita giornaliera/settimanale che l'utente si aspetta.
- **Hashing**: aggiungere test `test_cache_key_differs_on_frequency_change` + `test_cache_key_differs_on_generate_interest_toggle` + `test_cache_key_identical_on_event_only_change`.
- **Frontend**: verificare che `ScheduledInvestmentEditor` invii `provider_params` aggiornato via `assign_providers_bulk` (non solo PATCH asset).

**Priorità**: P1 — BTP Italia 2028 è asset dimostrativo nel populate, grafico errato visibile durante smoke test.

### I-bis #24 — Auto-refresh mirato post-sync (last-point-only)  ⏳ PENDING (nuovo, 2026-04-22 batch 2 part1 retest)

**Contesto UX**: dopo aver cliccato "Sync" con provider current-price, se l'utente aspetta il debounce del backend e fa refresh manuale della pagina, il nuovo punto compare. Senza refresh non compare → UX incoerente. In più, anche il bottone "Add manually" dell'empty state (I-bis #6) sarebbe molto più fluido se, dopo il primo save, il pannello empty transitasse direttamente al grafico senza full-reload.

**Design proposto**:
1. **Caso "chart popolato, sync current-price"**: invece di ricaricare tutto `chartData` (causa flash "chart vuoto → chart pieno" + ricalcolo signals + ricalcolo FX conversion), invocare un merge targettato:
   - Backend già risponde con `inserted_count`, `updated_count` e idealmente con i punti effettivamente toccati. Se non lo fa, va esteso → tornare `points: FAPricePoint[]` (delta) al posto di solo counters.
   - Frontend: fare un `Map<date, point>` dei punti attuali e applicare le modifiche incrementalmente. Solo il punto odierno (o i punti toccati) viene re-renderizzato.
   - Ricompute dei signals / FX conversion avviene sullo stesso subset.
2. **Caso "empty state → primo punto"** (integrazione I-bis #6): quando `chartData.length === 0` e la finestra temporale include oggi, se il sync (o il save manuale) restituisce un punto con `date >= dateStart && date <= dateEnd`, il componente deve transizionare **in-place** dall'empty state al grafico senza ricaricare la pagina:
   - Già oggi il `{#if chartData.length > 0}` switcha automaticamente se la reattività viene triggerata: basta assicurarsi che `chartData` venga aggiornato.
3. **Performance**: evitare il re-render completo del chart ECharts. Usare `setOption(..., { replaceMerge: ['series'] })` o `appendData` se disponibile.

**File candidati**:
- Backend: `backend/app/api/v1/assets.py` endpoint `POST /assets/prices/sync` — aggiungere `changed_points: FAPricePoint[]` nel response model (o esporre via query flag `?return_points=true` per non rompere il wire format esistente).
- Frontend: `frontend/src/routes/(app)/assets/[id]/+page.svelte` — nuova funzione `mergeChartDataIncremental(newPoints)` invocata da `handleSync`, oltre al flusso attuale "full reload".
- Frontend: stesso pattern da riusare nel `handleSave` di `AssetDataEditorSection.svelte` (dopo I-bis #24 l'empty → chart flow diventa automatico).

**i18n**: nessuna chiave nuova (il toast di sync esistente resta).

**Priorità**: **P2** — nice-to-have UX, non blocca Part 4. Rimandabile a batch tail dopo I-bis #1+#23 (che forniscono il payload giusto sul response `/prices/sync`).

**Note**: ha una forte sinergia con I-bis #1+#23 (handler unificato `PriceSyncResponse`): se quel refactor espone già i `changed_points`, il work di I-bis #24 si riduce a soli ~30 min di merge logic frontend.

### I-bis #23 — Sync `scheduled_investment`: `status="partial"` non surfacciato al frontend  ⏳ PENDING

**Contesto**: sync manuale BTP Italia 2028 restituisce 200 OK con `results[0].status="partial"`, `points_changed=0`, `message="Current value only, history unavailable"`. Frontend tratta come errore generico senza esporre il `message`.

**Da fare**:
- **(a) Backend audit**: `scheduled_investment.sync_asset_history` deve ricalcolare tutti i punti da `start_date` a oggi per un piano periodico. Verificare se il return `partial / Current value only` è corretto o è un path di fallback errato.
- **(b) Frontend**: handler `PriceSyncResponse` con switch su 4 stati + toast i18n:
  - `success_count>0 && total_points_changed>0` → verde "N prezzi aggiornati".
  - `success_count>0 && total_points_changed==0` → giallo "Nessun nuovo prezzo (già aggiornato fino a oggi)".
  - `errors.length>0 || results[].status=='failed'` → rosso con detail.
  - `status=='partial'` → giallo con `message` del provider.
  - i18n: `prices.sync.{success,noChanges,partial,failed}` × 4.
- **(c) Unificare con I-bis #1**: stessa radice (frontend non distingue "0 rows = OK" vs "0 rows = problema"). Un unico handler condiviso.

**Priorità**: P1 — sblocca retest completo scheduled_investment.

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
| 5 | #R4-3 | FE/BE (chart non aggiorna) | 1-3h (dipende da diagnosi) | alta ma bloccata su diagnosi utente | ✅ DONE |

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


