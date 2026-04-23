# Plan — Phase 7 Part 3 · Closure (Blocco E + I-bis pending)

> **Parent plan**: [`plan-phase07-transaction-Part3.md`](./plan-phase07-transaction-Part3.md)
> **Phase doc**: [`phases/phase-07-transactions.md`](./phases/phase-07-transactions.md)
> **Status**: ⏳ In progress — 2026-04-22 sera tardi
> **Scope**: chiusura del Blocco E con decisioni terminali, coda I-bis pending, deliverable residui prima di passare a Part 4.

---

## 🎯 Obiettivo

Questo plan raggruppa:
1. **Decisioni terminali sul Blocco E** — stato di cose "fatte e da modificare", "non da fare", "da fare ora".
2. **Tasks I-bis pendenti** — coda di follow-up UX/Backend emersa dai test manuali 2026-04-22.
3. **Validazione finale di Part 3** — formato + lint + test + aggiornamento phase doc.

Obiettivo di chiusura: poter dichiarare Part 3 **completato** e procedere a Part 4 (pagina `/transactions`) con la roadmap pulita.

---

## 📜 Decisioni terminali sul Blocco E (post-Blocco I, dopo Q&A 2026-04-22)

Tabella autoritativa. Sostituisce la sezione Blocco E del parent plan (che resta solo
per traccia storica del design originale).

| # | Design originale (Part 1 §8) | Decisione terminale | Rationale |
|---|------------------------------|---------------------|-----------|
| **E.1** | `FAPricePoint.original_currency` sempre + `AssetBackwardFillInfo.fx_error` discriminator (`pair_missing`/`no_rate_at_date`) | ✅ `original_currency` **tenuto** (già implementato).<br>❌ `fx_error` **cancellato dal design**. | Gli scenari `pair_missing` e `no_rate_at_date` sono **ancora possibili** (conversione display-currency con pair non registrata o history FX incompleta). Ma il surface UI alternativo `requiredFxPairs` (in `routes/(app)/assets/[id]/+page.svelte` L267–337, L1081–1153) li gestisce **a monte** con 4 stati (`ok`/`missing`/`no-data`/`partial-gap`), banner inline e CTA one-click (`Add FX Pair` / `Sync`). Aggiungere `fx_error` al response sarebbe duplicazione. Verifica: `grep fx_error` → 0 risultati sia in backend sia frontend → non c'era mai stato da rimuovere. |
| **E.2** | `FAPriceQueryResult.currency_breakdown` | ❌ **Cancellato** | Superseded da I.1 (Blocco I): tutti i punti di un asset hanno per definizione la stessa currency (I.2 hard-reject). Breakdown ridondante. |
| **E.3** | `upsert_prices_bulk`: mismatch → `errors.append` + skip soft | 🟡 **Rimpiazzato** da I.2 (hard 400 reject). Design originale da cancellare; codice già allineato. | Con la column `currency` rimossa dal DataEditor (I.8), i mismatch possono arrivare solo da caller "scorretti" (import CSV malformato, chiamate API manuali). Failare rumoroso > silenziare. |
| **E.4** | `fx_provider_manager.ensure_pair_registered` — auto-registrazione FX pairs | ❌ **Cancellato (design era sbagliato)** | Auto-magic viola la filosofia self-hosted (controllo esplicito dell'utente su provider/quota/sync). La UX `requiredFxPairs` già mette l'utente in condizione di capire e agire (banner + CTA "Add FX Pair" con slug pre-compilato). |
| **E.5** | `PriceCurrencyMismatchBanner` + endpoint `POST /prices/normalize` + azioni Normalize/Ignore | ❌ **Cancellato** | Superseded da I.5. Post-I.2 non possono più esistere punti dissonanti → banner + endpoint non necessari. |
| **E.6** | Banner FX-missing differenziato (`pair_missing`/`no_rate_at_date`) | ❌ **Cancellato** | Superseded da I.5 + `requiredFxPairs` (granularità superiore: 4 stati vs 2). |
| **E.7** | DataEditor: pre-fill colonna currency + warning | ❌ **Cancellato** | Superseded da I.5/I.8: colonna rimossa. |
| **E.8** | `query_events_bulk` param `target_currency` + conversione event.value | ⏳ **Da fare ora** — vedi §E.8 sotto | Sblocca visualizzazione corretta di dividendi/cash events nella display-currency scelta dall'utente, pre-requisito funzionale per Phase 9 Dashboard. |

---

## 🛠️ Task E.3 — Source cleanup + doc update  ✅ DONE (2026-04-22 sera)

### Lavoro eseguito
- Verificato: il codice `bulk_upsert_prices` in `backend/app/services/asset_source.py` L1160–1175 **era già allineato** a I.2 (hard `ValueError` → 400 nel router API).
- Verificato: endpoint `upsert_prices_bulk` in `backend/app/api/v1/assets.py` L620–624 già gestisce `ValueError` → `HTTPException(400, detail=str(e))`.
- Verificato: **nessun residuo** di pattern "soft-skip con `errors.append` per currency mismatch" (grep confermato).
- **Aggiunto**: docstring esplicita in `bulk_upsert_prices` che documenta la semantica I.2 hard-400 + rinvio a questo closure plan.

### Validazione
- `./dev.py format` → ✅ 0 changes.
- `./dev.py lint` → ✅ all checks passed.

### Lavoro
- **Grep** residui di linguaggio "soft-skip + errors[]" in:
  - `backend/app/services/asset_source.py` (docstring di `upsert_prices_bulk`, commenti inline).
  - `backend/app/api/v1/assets.py` (endpoint prezzi).
  - `backend/app/schemas/assets.py` (response schemas per upsert).
  - Test `backend/test_scripts/api/test_assets_price.py` (search per `errors: [` in assert che aspettano 200).
- **Sostituire** con la nuova semantica: HTTP 400 su qualsiasi mismatch currency, body `{detail, asset_currency, offending_dates[]}`.
- **Parent plan**: nella sezione Blocco E §E.3, aggiungere nota `> **SUPERSEDED** by I.2 (2026-04-21) — hard 400 reject. See Closure plan §E.3.` senza cancellare il testo originale (traccia storica).

### Validazione
```bash
./dev.py format && ./dev.py lint
./dev.py test api assets-price
```

---

## 🛠️ Task E.8 — `query_events_bulk` target_currency + infobox FX-converted

### Design rules (specchio del pattern prezzi)

Il sistema prezzi ha già consolidato un design per i valori convertiti FX.
**Riusare le stesse funzioni e gli stessi token** per evitare divergenze.

#### Funzioni/utility già esistenti da riusare tali e quali

| Utility | File | Uso |
|---------|------|-----|
| `getCurrencyInfo(code)` → `{flag_emoji, ...}` | `$lib/stores/currencyStore` | Lookup bandiera da ISO3. |
| `ensureCurrenciesLoaded()` | idem | Prefetch registry currency prima del render. |
| `signalLabelToHtml(sigInfo, maxLen=15)` | `$lib/components/charts/...` (cercato in `PriceChartFull.svelte` L904+) | Rendering label con icona + troncamento 15 char. |
| Lookup map pattern `Map<date, value>` | `PriceChartFull.svelte` L729–738 | Pre-compute lookup O(1) per tooltip. |

#### Token di design (estratti da `PriceChartFull.svelte` L849–955 + `MeasurePanel.svelte` L408–416)

| Token | Valore | Esempio |
|-------|--------|---------|
| **Currency badge (no conversione)** | `(${flag} ${ISO3})` fontsize 10px opacità 0.7 | `(🇺🇸 USD)` |
| **Currency badge (con conversione)** | `(${flag_display} ${ISO3_display}) 💱` fontsize 10px | `(🇪🇺 EUR) 💱` |
| **Valore originale (MeasurePanel suffix)** | `<span style="font-size:10px;opacity:0.7">(${origFlag} ${origISO3})</span>` | `(🇺🇸 USD)` in coda al valore |
| **Troncamento nome serie** | `> 15 char → slice(0,15) + '…'` | `AAPL — Tech…` |
| **Format valore numerico** | `>= 1 → toFixed(2)`, altrimenti `toFixed(4).replace(/\.?0+$/,'')` | `89.52`, `0.0425` |
| **Converted indicator** | `💱` sempre **alla fine** del pattern `(flag ISO3)` | vedi riga sopra |

### E.8.1 — Backend: `query_events_bulk`  ✅ DONE (2026-04-22 sera)

**Stato**: endpoint + conversion pass **già implementati** in precedenza.
Mancavano solo i campi `original_*` / `fx_*` sul response schema.

**Fatto**:
- Esteso `FAAssetEventPointOut` (`backend/app/schemas/prices.py` L295+) con:
  - `original_value: Optional[Currency]` (cattura amount + code originali in un unico oggetto Currency, coerente con il pattern del resto dello schema).
  - `fx_rate_date: Optional[date]`.
  - `fx_days_back: Optional[int]`.
- Service `query_events_bulk` (`backend/app/services/asset_source.py` L2637+): popola i 3 campi su conversione riuscita; skip su identity conversion (from==to) per distinguere "converted" da "passthrough" lato FE.
- **Bonus cleanup (E.1 closure discovery)**: rimosso `fx_error` discriminator (era implementato nel backend per i prezzi ma non consumato dal FE). Coerente con la decisione E.1. 6 riferimenti puliti in `asset_source.py` + 1 field in `FAPricePoint.backward_fill_info`.
- `./dev.py api sync` → client TS rigenerato con nuovi campi visibili.
- `./dev.py format && lint && front check && test api assets-events/assets-price` → ✅ tutti verdi.

### E.8.2 — Frontend: event infobox nel chart  ✅ DONE (2026-04-22 sera)

**Fatto**:
- Esteso `EventMarker` interface in `PriceChartFull.svelte` L24+ con: `originalValue`, `originalCurrency`, `originalCurrencyFlag`, `currencyFlag`, `fxRateDate`, `fxDaysBack`.
- Tooltip formatter (L673+) riscritto per pattern design-consistente:
  - `💰 {value} (flag ISO3) 💱` — emoji currency indicator **alla fine** (token standard).
  - `orig. {originalValue} (origFlag origISO3)` — font-size 10px opacity 0.7, pattern mirror di `MeasurePanel.svelte`.
  - `fx @ {date} ({days}d back)` — font-size 10px opacity 0.6.
- Hide rule: eventi con conversione fallita **non vengono renderizzati** (filtro in `chartEventMarkers` $derived del +page.svelte).

### E.8.3 — Frontend: estendere `requiredFxPairs` a include event currencies  ✅ DONE (2026-04-22 sera)

**Fatto**:
- Esteso `$derived requiredFxPairs` in `routes/(app)/assets/[id]/+page.svelte` L336+ per aggiungere le pair derivate dalle event currencies (own + comparison) ≠ `displayCurrency`.
- Logica `missing` / `no-data` (failed conversion detection su `!ev.original_value`).
- `forAsset` etichettato via nuova chiave i18n `events.fxBannerContext` ("for dividend/cash events" / "per eventi dividendi/cassa" / "pour les événements dividendes/cash" / "para eventos dividendo/efectivo") → propagata nelle 4 lingue.
- Banner esistente (L1081–1153) riusato as-is: stesso markup, CTA "Add FX Pair" + "Sync" già pronti.

### E.8.4 — Bonus backend cleanup  ✅ DONE (2026-04-22 sera)

Durante il lavoro E.8 ho scoperto che la conversione FX dei prezzi `get_prices_bulk` (con `include_events=True`) **non includeva** gli eventi nel conversion pass. Aggiunto mirror di 27 righe dopo il loop prezzi che applica la stessa logica a `result.events`, popolando `original_value` + `fx_rate_date` + `fx_days_back` e surfacing degli errori FX come stringhe non-fatali in `result.errors`. Così la conversione eventi funziona sia dall'endpoint `/assets/events/query` sia da `/assets/prices/query?include_events=true` (path usato in produzione dal +page.svelte).

### Validazione E.8
- `./dev.py format && lint` → ✅ 0 errori.
- `./dev.py api sync` → ✅ client TS rigenerato con i 3 campi aggiunti.
- `./dev.py front check` → ✅ 0 errors, 0 warnings.
- `./dev.py test api assets-events / assets-price` → ✅ entrambi PASSED.
- Test backend dedicato E.8 (`test_events_target_currency.py`) → **demandato al Blocco G** qui sotto.

### E.8.4 — Test

**Backend** (`backend/test_scripts/api/test_events_target_currency.py`):
- `test_no_target_currency_returns_raw_values`.
- `test_same_currency_passthrough` (event USD, target USD → no-op, original_* = None).
- `test_conversion_same_day_fx` (original_* popolati, fx_days_back=0).
- `test_conversion_backward_fill_fx` (fx_days_back > 0).
- `test_missing_fx_appends_to_errors_not_hard_fail`.
- `test_mixed_events_some_converted_some_not`.
- `test_original_value_always_populated_on_success`.

**Frontend**:
- Unit/component test (se esiste infrastruttura) su rendering infobox converted vs non-converted.
- Playwright E2E: caricare asset con dividend events in currency diversa, switchare displayCurrency → verifica che il tooltip contenga entrambi i valori, verifica che banner `requiredFxPairs` sia visibile se pair manca.
- Test manuale estetico esplicito (🎨).

### E.8.5 — Validazione
```bash
./dev.py format && ./dev.py lint
./dev.py api sync && ./dev.py front check
./dev.py test api events-target-currency
./dev.py test all-backend
# Test manuale: asset con dividend USD, displayCurrency=EUR, verifica infobox
```

---

## 🔍 Blocco F — Verifica finale (codice presente, test da consolidare)

Il Blocco F (OHLC partial upsert + sentinel `-1` + current-price auto-extend) **è implementato nel codice**:

- **F.3 `_extend_ohlc_bounds`** ✅ validato in produzione (conferma log 2026-04-22 sera, plan Part3 §I-bis).
- **F.4 sentinel `-1` → NULL** ✅ presente in `backend/app/services/asset_source.py` L1191–1193 (helper merge).
- **F.1/F.2** (provider > utente, bootstrap OHLC) ✅ inferibili dalla presenza di F.4.
- **F.5** eraser 🧽 + placeholder `notSet` ✅ validato via I-bis #9 fix su `ErasableNumberCell`.

### Task pendente F: test di copertura

→ Copertura di F demandata al **Blocco G.6** (`test_ohlc_sentinel.py`, vedi sotto). Nessun lavoro di codice residuo.

---

## 🧪 I.9 — Backend test adaptations (Blocco I)  ✅ DONE (2026-04-22 sera)

**Fatto** in `backend/test_scripts/test_api/test_assets_prices.py`:
- `test_upsert_mismatch_single_row_rejects_400` → single EUR row on USD asset → 400 "Currency mismatch".
- `test_upsert_mismatch_partial_rejects_entire_batch_400` → 1/3 mismatch rejects atomicamente (verificato query post-400 → 0 rows).
- `test_upsert_same_currency_succeeds_200` → regression test che il happy path non è rotto.

**Validazione**: `./dev.py test api assets-price` → ✅ tutti 17 tests PASSED (14 preesistenti + 3 I.9).

---

## ✅ I.10 — Validazione finale Blocco I

```bash
./dev.py format && ./dev.py lint
./dev.py api sync && ./dev.py front check
./dev.py test api assets-price
./dev.py test api assets-currency-change   # da G.10
./dev.py test api assets-prices-export     # da G.11
```

Da eseguire **dopo** G.10 e G.11 (che i test file li creano).

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

## 🗺️ Ordine di esecuzione suggerito

1. **E.3 source cleanup** (30 min) — quick, chiude la narrativa Blocco E.
2. **E.8 backend + test** (2h) — foundation per infobox FE.
3. **E.8 frontend infobox + `requiredFxPairs` estensione** (1.5h) — chiude E.
4. **I-bis #1 + #23** (combinati, 2h) — unico handler per "sync 0 rows" + `status=partial`.
5. **I-bis #12** (1h) — toast reduction (quick win).
6. **I-bis #3 + #4 + #6** (1h combinati) — micro-UX.
7. **I-bis #5** (1.5h) — CSV import resilience.
8. **I-bis #2** (1h) — provider dirty gating.
9. **I-bis #22** (3–4h) — save error handling generalizzato. **Prerequisito Part 4/5**.
10. **I-bis #7** (30 min) — backend 409 semantics, non urgente.
11. **I.9 test adaptations** (1h) — hard-400 currency mismatch tests.
12. **G.1 + G.2** extend existing (2h) — rollback, matrix access control.
13. **G.3 transactions/validate** (1.5h).
14. **G.4 events/suggest** (1h).
15. **G.5 prices-currency-coherence** (1h — versione ridotta post-I.11).
16. **G.6 ohlc-sentinel** (1.5h) — copertura Blocco F.
17. **G.10 asset-currency-change** (1h).
18. **G.11 asset-prices-export** (1.5h).
19. **G.7 test_runner.py** (15 min).
20. **G.8 coverage verification** (30 min) + eventuale top-up.
21. **I.10 + G.9 validazione finale** (30 min).

**Totale stimato**: ~13–14h lavoro UX/feature + ~12h test coverage + validazione = **~25–26 ore** totali per la chiusura completa.

> Se si vuole accelerare, i blocchi G.1/G.2/G.3/G.4 (matrix transazioni + validate + suggest) possono essere parallelizzati da un secondo agent/dev perché toccano area isolata.

---

## ✅ Deliverable di chiusura

### Backend
- `query_events_bulk` con `target_currency` param (E.8).
- Schema `FAEventOut` esteso con `original_value`, `original_currency`, `fx_rate_date`, `fx_days_back`.
- Source cleanup docstring/commenti E.3.
- (Opzionale I-bis #7) HTTP 409 per batch patch all-failed.

### Frontend
- Event infobox con valore converted + originale (pattern prezzi mirror).
- `requiredFxPairs` esteso a event currencies.
- Event markers/rows nascosti se conversione FX fallisce.
- Handler unificato `PriceSyncResponse` con 4 stati toast (I-bis #1+#23).
- 3 toast currency change → 1 (I-bis #12).
- Tab label currency+flag (I-bis #3).
- CSV import banner + resilience (I-bis #4 + #5).
- Empty-state "Add manually" (I-bis #6).
- Provider dirty gating per "Save Without Testing?" (I-bis #2).
- `saveWithRetry` helper + adozione in 8 modal (I-bis #22).

### i18n (nuove chiavi × 4 lingue)
- `events.fxBannerContext`, `events.hiddenDueToMissingFx` (E.8).
- `sync.postWipeZeroRows`, `prices.sync.{success,noChanges,partial,failed}` (I-bis #1+#23).
- `dataEditor.pricesInCurrency`, `dataEditor.eventsInCurrency` (I-bis #3).
- `import.csv.currencyReminder`, `import.csv.extraColumnsIgnored` (I-bis #4).
- `assetDetail.addPricesManually` (I-bis #6).
- Messaggi errore generici `save.failed.*` (I-bis #22).

### Test
- `test_events_target_currency.py` (E.8, 7 test case).
- `test_transactions_validate.py` (G.3, 6 casi).
- `test_events_suggest.py` (G.4, 5 casi + parametrizzati).
- `test_prices_currency_coherence.py` (G.5, 3 casi post-I.11).
- `test_ohlc_sentinel.py` (G.6, 8 casi).
- `test_asset_currency_change.py` (G.10, 5 casi).
- `test_asset_prices_export.py` (G.11, 7 casi).
- `test_transaction_service.py` estensione (G.1, 10 nuovi casi).
- `test_transactions_api.py` matrix estesa (G.2).
- `test_assets_prices.py` hard-400 cases (I.9).
- `scripts/test_runner.py` entries (G.7, 7 nuove).
- Coverage `transaction_service ≥ 90%`, `asset_source (funzioni toccate) ≥ 85%` (G.8).
- Unit FE su infobox converted (se infrastruttura disponibile).
- Playwright E2E scenario: asset con dividend USD, display EUR, hide-on-missing-FX, banner scatter.

### Documentazione
- Parent plan `plan-phase07-transaction-Part3.md` con nota di rinvio a questo closure.
- Phase doc `phases/phase-07-transactions.md` aggiornata al termine.

---

## 🔗 Cross-link

- **Parent**: [`plan-phase07-transaction-Part3.md`](./plan-phase07-transaction-Part3.md).
- **Predecessori**: [`plan-phase07-transaction-Part1.md`](./plan-phase07-transaction-Part1.md) ✅, [`plan-phase07-transaction-Part2.prompt.md`](./plan-phase07-transaction-Part2.prompt.md) ✅.
- **Successori**: Part 4 (pagina `/transactions`), Part 4b (File Preview), Part 5 (Staging Modal). **Gated da I-bis #22**.
- **Phase 8 follow-up**: [`phases/phase-08-scheduler.md`](./phases/phase-08-scheduler.md) — consumer `Asset.active` + scheduler demone.
- **Phase 9 follow-up**: Dashboard — consumer `Asset.active` hide su breakdown + estensione `requiredFxPairs` a viste multi-asset.

---

## 🚧 Rischi & Mitigazioni

| Rischio | Mitigazione |
|---------|-------------|
| E.8 backward-fill FX policy divergente dai prezzi | Riusare la stessa funzione `fx_service.get_rate_at_date(..., backward_fill_days=14)` |
| Event currencies miste → banner rumoroso | Dedup `toSlug` + `seenSlugs` già gestito in `requiredFxPairs` |
| I-bis #22 refactor rompe modal esistenti | Rollout progressivo: adotta `saveWithRetry` un modal alla volta + test manual regressivo |
| Ordine E → I-bis rotto da nuovi feedback utente | Accettabile: questo plan è "closure" non "frozen" — eventuali nuovi I-bis si accodano |

---

## ✅ Come validare esternamente

```bash
# 1) Format + lint + sync
./dev.py format && ./dev.py lint
./dev.py api sync && ./dev.py front check

# 2) Test mirati Blocco E residuo
./dev.py test api assets-price          # E.3 cleanup
./dev.py test api events-target-currency # E.8

# 3) Test regressione
./dev.py test all-backend

# 4) Smoke E2E
./dev.py test e2e asset-currency-change
./dev.py test e2e events-fx-conversion   # nuovo

# 5) Test manuale estetico
#    - Asset USD, displayCurrency=EUR, verifica infobox converted + banner requiredFxPairs
#    - Currency change flow: 1 solo toast finale
#    - CSV re-import dal CSV export
#    - Edit modal asset senza toccare provider → no "Save without testing?" modal
```

---

## 🧭 Giornale di viaggio (per reset conversazione)

> **Scopo**: in caso di reset del contesto, questa sezione è il backup delle intenzioni, dello stato e dei prossimi step. Aggiornata a ogni fine-sessione.

### 📍 Dove sono arrivato (2026-04-22 sera tardi, batch 1 + refactor FxBackwardFillInfo + batch 2 part1)

**Commit batch 1** (già fatto dall'utente, hash `66ad026a` + un commit successivo): Closure plan batch 1 completo.

**Sessione post-commit (questa)** — refactor schema:
- Creata nuova classe `FxBackwardFillInfo` in `backend/app/schemas/common.py` (accanto a `BackwardFillInfo`). Contiene `fx_rate_date` + `fx_days_back`.
- `AssetBackwardFillInfo` (in `prices.py`) ora eredita da **entrambi** (`BackwardFillInfo, FxBackwardFillInfo`) via mixin Pydantic → wire format prezzi identico, **zero breaking change** lato client per i prezzi.
- `FAAssetEventPointOut`: sostituiti i 2 campi piatti `fx_rate_date`+`fx_days_back` con un unico `fx_info: Optional[FxBackwardFillInfo]`. `original_value` resta standalone (non è backward-fill metadata).
- Motivazione: gli eventi **non hanno semantica di price backward-fill** (ex-date, cedola etc. sono date reali non-interpolabili). Solo la FX staleness è rilevante → raggrupparla in un oggetto dedicato, riusabile per futuri consumer (dashboard aggregati Phase 9).
- Backend (`asset_source.py`): 2 siti di costruzione `FAAssetEventPointOut` aggiornati per usare `fx_info=FxBackwardFillInfo(...)`. Import top-level esteso con `FxBackwardFillInfo`.
- Frontend (`+page.svelte`): accessi `ev.fx_rate_date`/`ev.fx_days_back` → `ev.fx_info?.fx_rate_date`/`ev.fx_info?.fx_days_back`.
- Test (`test_events_target_currency.py`): accessi aggiornati a `ev["fx_info"]["fx_rate_date"]`/`["fx_days_back"]` (sia doppi che singoli apici).
- Client TS rigenerato: `FxBackwardFillInfo` ora è un tipo Zod esportato, `fx_info` esposto come campo opzionale su `FAAssetEventPointOut`.
- Validazione post-refactor:
  - `./dev.py format && lint` → ✅ all checks passed.
  - `./dev.py front check` → ✅ 0 errors, 0 warnings.
  - `./dev.py test api events-target-currency` → ✅ 7/7 PASSED.
  - `./dev.py test api assets-price` → ✅ PASSED (regression OK).
  - `./dev.py test api assets-events` → ✅ PASSED.

**File toccati post-commit batch 1**:
- `backend/app/schemas/common.py` (+~45 righe: nuova classe `FxBackwardFillInfo`).
- `backend/app/schemas/prices.py` (AssetBackwardFillInfo rifattorizzato a inheritance, FAAssetEventPointOut con `fx_info`).
- `backend/app/services/asset_source.py` (import + 2 siti di costruzione).
- `frontend/src/routes/(app)/assets/[id]/+page.svelte` (2 blocchi event markers).
- `backend/test_scripts/test_api/test_events_target_currency.py` (assert nested).

**Sessione batch 2 part1** (questa, continuazione post-reset "actual_rate_date_str") — I-bis UX quick wins:
- **Fix pregresso**: `common.py` aveva il metodo `actual_rate_date_str()` erroneamente spostato dentro `FxBackwardFillInfo` (bug introdotto nel refactor precedente). Ripristinato dentro `BackwardFillInfo` (campo corretto: `actual_rate_date`). Verificato con one-liner runtime ✅.
- **I-bis #3** ✅ Tab label "Prices in {currency} 🇺🇸" / "Events in {currency} 🇺🇸" in `AssetDataEditorSection.svelte`:
  - Aggiunta prop `currency?: string`.
  - Derived `currencyFlag` via `getCurrencyInfo(currency).flag_emoji`.
  - Label `ml-auto` nella tab bar (switcha tra pricesInCurrency/eventsInCurrency in base ad `activeTab`).
  - `+page.svelte` passa `currency={assetInfo?.currency}`.
  - i18n keys nuove: `assetDetail.pricesInCurrency` + `assetDetail.eventsInCurrency` (4 lingue).
- **I-bis #4** ✅ Import CSV banner reminder in `PriceDataImportModal.svelte`:
  - Aggiunta prop `currency?: string`.
  - Nuovo `InfoBanner variant="warning"` nell'header slot con "Currency must match asset currency ({currency} 🇺🇸)." + "Extra columns (like currency, source_plugin_key, fetched_at from Export) are ignored."
  - `AssetDataEditorSection.svelte` propaga `currency` al modal.
  - i18n keys nuove: `import.csv.currencyReminder` + `import.csv.extraColumnsIgnored` (4 lingue).
- **I-bis #6** ✅ Empty-state "Add manually" button in `+page.svelte`:
  - Nel ramo `{:else}` (zero prezzi, provider-backed asset) aggiunto secondo bottone "Add manually" accanto a "Sync from provider". Apre il data editor salvando lo stato dei panel (pattern identico al ramo `isManualOnly`).
  - i18n key nuova: `assetDetail.addPricesManually` (4 lingue).
- **Gotcha #1 confermato**: shell strippa accenti (É, é, à, ñ). Per ogni `./dev.py i18n add` con chars non-ASCII ho creato script `/tmp/libreFolio_fix_*.py` con escape unicode (`\u00f1`) per fixare il file JSON post-add.
- Validazione batch 2 part1:
  - `./dev.py front check` → ✅ 0 errors, 0 warnings (eseguito 3 volte, dopo ogni task).
  - `./dev.py front format` → ✅ tutti i file unchanged (già formattati).

**File toccati in batch 2 part1**:
- `backend/app/schemas/common.py` (spostato `actual_rate_date_str` dal posto sbagliato).
- `frontend/src/lib/components/assets/AssetDataEditorSection.svelte` (prop currency + tab label).
- `frontend/src/lib/components/assets/PriceDataImportModal.svelte` (prop currency + warning banner).
- `frontend/src/routes/(app)/assets/[id]/+page.svelte` (passa currency al data editor + bottone "Add manually" nell'empty state).
- `frontend/src/lib/i18n/{en,it,fr,es}.json` (5 nuove chiavi × 4 lingue = 20 entries).

### 📍 Retest batch 2 part1b (2026-04-22 sera tardi, post-utente-feedback)

Dopo retest manuale dell'utente:
- **I-bis #3** ✅ confermato + traduzioni OK.
- **I-bis #6** ✅ confermato + regressione manual-only verificata. Emerso nuovo task I-bis #24 (vedi sotto).
- **I-bis #4** 🔧 2 issue da fixare:
  1. **Banner design**: non un 2° banner warning, ma **un unico InfoBanner info** con ordine: currency reminder → struttura (min/extended) → hint separatore → nota extra-columns.
  2. **Banner i18n**: le 3 righe esistenti (Minimum/Extended/separator hint) erano hardcoded in inglese → tradotte con 3 nuove chiavi i18n.
  3. **Tooltip CSV errors**: in `CsvEditor.svelte` gli errori di parsing erano comunicati via `title=` HTML nativo. Migrato al componente custom `Tooltip.svelte` (mostra istantaneo su hover della X rossa + del numero riga con error). Posizionamento `right` per non coprire la textarea. Tooltip applicato condizionalmente solo se `v.error` non vuoto (evita wrapper spurio sulle righe valide).

**i18n nuove (batch 2 part1b)** in `import.csv.*`:
- `labelMinimum` ("Minimum" / "Minimo" / "Minimum" / "Mínimo").
- `labelExtended` ("Extended" / "Esteso" / "Étendu" / "Extendido").
- `separatorHint` con placeholder `{sep}` iniettato via `@html` (il codice `<code>;</code>` non si interpola con `{values}` di svelte-i18n, quindi passo HTML escapato). 4 lingue.

**File toccati in batch 2 part1b**:
- `frontend/src/lib/components/assets/PriceDataImportModal.svelte` (collassato i 2 banner in 1, traduzioni).
- `frontend/src/lib/components/ui/data-editor/CsvEditor.svelte` (import Tooltip, 2 siti `title=""` → `<Tooltip text={v.error}>…</Tooltip>`).
- `frontend/src/lib/i18n/{en,it,fr,es}.json` (+3 chiavi).

**Validazione batch 2 part1b**:
- `./dev.py front check` → ✅ 0 errors, 0 warnings.
- `./dev.py front format` → ✅ all unchanged.

**Nuovo task tracciato** (non ancora implementato): `I-bis #24 — Auto-refresh mirato post-sync` (aggiornato solo il last-point dopo sync, no full reload; transizione fluida empty→chart se finestra include oggi). Vedi sezione dedicata sopra nel plan.

**Issue emersa ma NON fixata in questa sessione** (perché scope = #5): il CSV esportato da `/prices/export?format=csv` oggi ha colonne extra (`currency, source_plugin_key, fetched_at`) che `CsvEditor` rifiuta con "too many fields". Il round-trip export→import richiede l'header-tolerance di I-bis #5. Per ora il banner informa l'utente che le extra columns sarebbero ignorate; il parser va reso effettivamente tollerante in batch successivo.

### 📍 Retest batch 2 part1c (2026-04-22 sera tardi, 3° giro feedback utente)

Dopo il 3° retest manuale emersi 3 nuovi issue:

**Issue A — Missing FX quick-link icon**:
- Nella filterBar del detail asset (`AssetPriceSummary.svelte`), **dopo** il dropdown "Converti in", non c'era più un link rapido alla detail page della coppia FX.
- Fix: aggiunta prop `fxPairUrl?: string`. Quando valorizzata (solo se pair **healthy**) mostra un bottone `<a>` con icona `ExternalLink` e `Tooltip` "Open FX pair detail". Click → naviga a `/fx/{slug}?start=...&end=...`.
- Parent `+page.svelte`: nuovo derived `mainFxPairUrl` che cerca la main pair in `requiredFxPairs` e ritorna URL solo se `status === 'ok'`. Se missing/no-data/partial-gap → `undefined` (niente bottone). Il banner full-width gestisce già quegli stati con le CTA specifiche → evitiamo doppioni/ambiguità.
- `data-testid="asset-detail-fx-pair-link"` per E2E futuri.
- i18n: `assetDetail.openFxPair` (4 lingue, "Ouvrir le détail de la paire FX" per FR).

**Issue B — Modal import title hardcoded + Events CSV banner hardcoded**:
- `PriceDataImportModal.svelte`: `title="📥 Import Prices CSV"` → `title={$t('import.csv.titlePrices')}`.
- `EventDataImportModal.svelte`:
  - Stesso fix sul titolo.
  - Tradotte le 2 righe del banner esistente: "Format:" → `{$t('import.csv.eventsFormatLabel')}`, "Types:" → `{$t('import.csv.eventsTypesLabel')}` (elevato a `<strong>` per coerenza col pattern prezzi).
  - **Aggiunta** la nota "Extra columns ignored" (`import.csv.extraColumnsIgnored`, riutilizzo della chiave di I-bis #4) → anche events CSV ora avverte che colonne in più sono ignorate.
- i18n nuove: `import.csv.{titlePrices, titleEvents, eventsFormatLabel, eventsTypesLabel}` (4 chiavi × 4 lingue).

**Issue C — fr.json accidentally zeroed**:
- Durante un tentativo di fix accent via Python inline con surrogate escape (`\ud83d\udce5`), `write_text(..., encoding='utf-8')` ha failato ma DOPO aver aperto il file in `w` → `fr.json` → 0 byte. Ripristinato via `git checkout HEAD` + script `/tmp/libreFolio_restore_fr_keys.py` che riapplica TUTTE le 13 chiavi FR aggiunte in questa sessione (pricesInCurrency, eventsInCurrency, addPricesManually, openFxPair, currencyReminder, extraColumnsIgnored, labelMinimum, labelExtended, separatorHint, titlePrices, titleEvents, eventsFormatLabel, eventsTypesLabel) con escape unicode `\u00e9` / `\u00c9` / `\u00e0` e emoji 📥 pescato da `en.json`.
- **Lezione/gotcha nuovo**: MAI usare surrogate pair escape per l'emoji 📥 in python — usare `\N{INBOX TRAY}` o copiarla da un altro file.

**File toccati in batch 2 part1c**:
- `frontend/src/lib/components/assets/AssetPriceSummary.svelte` (+prop fxPairUrl + link).
- `frontend/src/routes/(app)/assets/[id]/+page.svelte` (+derived mainFxPairUrl, passa al summary).
- `frontend/src/lib/components/assets/PriceDataImportModal.svelte` (title i18n).
- `frontend/src/lib/components/assets/EventDataImportModal.svelte` (title i18n + banner tradotto + extra-columns note).
- `frontend/src/lib/i18n/{en,it,fr,es}.json` (+5 chiavi × 4 lingue = 20 entries; fr.json integralmente ripristinato).

**Validazione batch 2 part1c**:
- `./dev.py front check` → ✅ 0 errors, 0 warnings.
- `./dev.py front format` → ✅ all unchanged.

**i18n finale cumulativo batch 2 part1+1b+1c** (da committare insieme):
- `assetDetail.{pricesInCurrency, eventsInCurrency, addPricesManually, openFxPair}` — 4 chiavi.
- `import.csv.{currencyReminder, extraColumnsIgnored, labelMinimum, labelExtended, separatorHint, titlePrices, titleEvents, eventsFormatLabel, eventsTypesLabel}` — 9 chiavi.
- **Totale: 13 chiavi × 4 lingue = 52 entries**.

### 📍 Batch 2 part2 (2026-04-22 sera tardi, 4° giro) — I-bis #12 + #1+#23 + bugfix

**Bug A fixati in apertura** (da retest utente post-commit batch 2 part1c):
- **FX icon**: il link FX quick-access nel filterBar usava `ExternalLink`, ma l'icona standard del progetto per le coppie FX è `ArrowLeftRight` (usata in `FxTable/FxCard/FxSyncModal/FxPairAddModal/FxProviderConfig`). Sostituita in `AssetPriceSummary.svelte`.
- **DataEditor buttons hardcoded**: i bottoni "Import CSV" e "Add Row" nel toolbar di `DataEditor.svelte` erano in inglese fisso (sia nel tab Prices sia nel tab Events). Tradotti con nuove i18n:
  - `dataEditor.importCsv` ("Import CSV" / "Importa CSV" / "Importer CSV" / "Importar CSV")
  - `dataEditor.addRow` ("Add Row" / "Aggiungi riga" / "Ajouter une ligne" / "Agregar fila")
  - `dataEditor.emptyMessage` (messaggio empty-state quando non ci sono righe, "No data. Use 'Add Row'..." tradotto).

**I-bis #12 — Toast reduction currency change (5 → 1)**:
- `AssetCurrencyChangeModal.svelte`: rimossi i 3 `toasts.info` di progress (`progressDelete`, `progressPatch`, `progressSync`). Sostituiti con uno stato `progressStep: null | 'delete' | 'patch' | 'sync'` che renderizza inline nel footer del modal (sinistra dei bottoni) uno spinner CSS + la label i18n corrispondente. Le 3 chiavi i18n esistenti sono state **riutilizzate** — non rimosse dai JSON perché ora compongono il messaggio inline.
- `AssetModal.svelte` `onconfirmed` callback: rimosso il `toasts.success($t('assets.modal.saveSuccess'))` duplicato (il `currencyChange.done` che emette il modal figlio è sufficiente). Commento inline I-bis #12.
- **Risultato UX**: flusso provider-backed = **1 toast finale** `done` (era 5). Flusso no-provider = **1 toast finale** `done` (era 3). Toast di errore/warning (syncFailedManualRetry, failed) intatti.

**I-bis #1 + #23 — Unified PriceSyncResponse handler**:
- `lib/utils/syncToastHelpers.ts`: refactor `buildAssetSyncToast` con firma estesa `(result, label, tr)`. Ora gestisce **5 stati** coerenti:
  1. `ok` + `points_changed>0` → `success` (messaggio esistente).
  2. **`ok` + `points_changed===0 && events_changed===0` → `warning`** con suffix `prices.sync.noChanges` ("No new data (already up to date)"). **Questo è il fix per I-bis #1**: post-wipe scenario dove il provider restituisce 0 righe valide (es. currency mismatch silently dropped) non viene più silenziosamente colorato di verde.
  3. `partial` → `warning` con **`result.message` appended** quando presente (I-bis #23: surface del messaggio scheduled_investment tipo "Current value only, history unavailable").
  4. `skipped` → `info`.
  5. altro/errore → `error` con fallback `result.message || prices.sync.failedDefault`.
- `buildFxSyncToast`: stesso refactor per i suffissi hardcoded (`Partial`, `Skipped`, `Failed`, `manual only`) → `tr('prices.sync.{partialSuffix, skippedSuffix, failedDefault, manualOnly}')`.
- 2 callsite aggiornati: `+page.svelte` di `assets/[id]` e `fx/[pair]` — passano `tr` come 3° arg.
- i18n nuove: `prices.sync.{noResponse, partialSuffix, skippedSuffix, failedDefault, noChanges, manualOnly}` — **6 chiavi × 4 lingue = 24 entries**. Accenti ripristinati via script Python (FR: "réponse", "ignoré", "échec", "donnée déjà à"; IT: "già").

**Bug C — tracked, non fixato** (regressione goBack da asset detail → fx detail → back):
- **I-bis #25 — goBack regression `/fx/{pair}` → `/fx` instead of `/assets/{id}`** ⏳ PENDING
- **Sintomo**: dall'asset detail cliccando il nuovo link FX quick-access si naviga a `/fx/{slug}`. Cliccando il bottone back sulla pagina FX detail si torna a `/fx` (lista) invece che tornare all'asset detail di partenza.
- **Ipotesi**: `navigationStore.depth` potrebbe non essere incrementato correttamente per navigazioni via `<a href>` (anche se SvelteKit dovrebbe gestirle come SPA navigation e triggerare `afterNavigate` con `nav.type='link'`). Oppure `history.back()` è corretto ma FX detail fa `goto(..., {replaceState: true})` in qualche path che rompe lo stack.
- **Possibili fix**:
  - (a) Sostituire `<a href>` con `onclick={() => goto(fxPairUrl)}` → forzare esplicitamente il routing SPA.
  - (b) Investigare `fx/[pair]/+page.svelte` linea 662 `goto(..., {replaceState: true})` — potrebbe sovrascrivere l'entry della history che doveva contenere l'asset detail.
  - (c) Salvare un `referrer` in sessionStorage al momento del click sul link, e al back del FX detail usare quel referrer invece del fallback `/fx`.
- **Priorità**: P2 — la navigazione funziona (back del browser dovrebbe funzionare comunque), solo il bottone custom "back" del FX detail ha comportamento imprevisto. Rimandato a batch 3 o successivo.

**File toccati in batch 2 part2**:
- `frontend/src/lib/components/assets/AssetPriceSummary.svelte` (icona ExternalLink → ArrowLeftRight).
- `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` (3 stringhe tradotte).
- `frontend/src/lib/components/assets/AssetCurrencyChangeModal.svelte` (#12 refactor: progress toasts → inline spinner).
- `frontend/src/lib/components/assets/AssetModal.svelte` (rimosso toast duplicato saveSuccess nel callback currency change).
- `frontend/src/lib/utils/syncToastHelpers.ts` (#1+#23 refactor: 5 stati + i18n suffixes).
- `frontend/src/routes/(app)/assets/[id]/+page.svelte` (passa tr a buildAssetSyncToast).
- `frontend/src/routes/(app)/fx/[pair]/+page.svelte` (idem).
- `frontend/src/lib/i18n/{en,it,fr,es}.json` (+9 chiavi: 3 dataEditor + 6 prices.sync).

**Validazione batch 2 part2**:
- `./dev.py front check` → ✅ 0 errors, 0 warnings.
- `./dev.py front format` → ✅ all unchanged.

**i18n cumulativo batch 2 part1+1b+1c+2** (da committare separatamente da part1/1b/1c già commitati):
- Part2: 9 nuove chiavi × 4 lingue = **36 entries**.

### 📍 Batch 2 part3 (2026-04-23 mattina, 5° giro feedback utente)

**Feedback utente che ha scatenato part3**:
1. Link FX nel filterBar c'è ma icona era generica (`Coins` → l'utente l'ha corretta in commit precedente — **nessun'azione** qui).
2. `goBack` su FX detail torna sempre a `/fx` invece che all'asset di origine. L'utente ricorda che esisteva un sistema di "stack di pagine" con reset sui click sidebar — va verificato perché non funziona più.
3. Toast currency change: con valuta non fornita dal provider, il toast dice **sia** "currency changed" **sia** "refreshed with success", ma la refresh è fallita. L'utente vuole 2 toast distinti: "delete success" + "sync result" (via `buildAssetSyncToast`, come fa `/assets` global che dà toast perfetti tipo `"Sincronizzazione fallita per Apple Inc.: DB upsert failed: Currency mismatch ..."`).
4. BTP Italia 2028: configurato DAILY + no-cedola, primi mesi grafico cresce (retta), poi si resetta a 10000 e resta piatto. Cambiando frequenza non cambia nulla → sospetto hashing cache broken.

**Fix I — goBack regression (refactor `navigationStore.ts` stack-based)**:
- Root cause identificato: il sistema `depth` con `history.back()` era fragile perché altre pagine fanno `history.replaceState` / `goto({replaceState:true})` che corrompono la browser history. **Fix**: rifatto `navigationStore.ts` con **stack esplicito di pathnames** (`string[]`).
  - `trackNavigation(type, pathname)`: push su link/goto/form, pop su popstate, reset su enter. Dedup su push consecutivo stesso pathname (per gestire replaceState con stesso path ma diversa query).
  - `goBack(fallback)`: se stack ha ≥2 entry → pop + `goto(stack[top])`. Altrimenti `goto(fallback)`.
  - `resetNavDepth()`: svuota lo stack (chiamato dalla Sidebar sui click top-level, pattern già esistente).
  - Aggiunto helper `_debugStack()` per diagnostics.
- `+layout.svelte`: `trackNavigation(nav.type, nav.to?.url.pathname)` (path passato esplicitamente).
- Nota: usa `goto` invece di `history.back()` per determinismo — costo: una nuova entry in history, ma risoluzione pulita.
- **Sidebar era già OK** (`resetNavDepth()` chiamato sui 3 link principali): grep confermato. Il bug era solo nella logica di `goBack`.

**Fix II — Toast currency change v2 (2 toast distinti)**:
- `AssetCurrencyChangeModal.svelte` refactor di `handleConfirm`:
  - Inline spinner (delete/patch/sync) resta per UX feedback (I-bis #12).
  - **Toast #1** — `deleteSuccess`: "Deleted N prices" — sparato appena la DELETE risolve.
  - **Toast #2** — `changedTo`: "Currency changed from X to Y" — sparato appena la PATCH risolve (sempre, quando delete+patch OK).
  - **Toast #3** — sync outcome via `buildAssetSyncToast(r, tr('common.sync'), tr)`: 5 stati (ok / noChanges / partial+msg / skipped / error). In caso di exception, surface del `response.data.detail` del backend (es. "DB upsert failed: Currency mismatch for asset 1: expected EUR ...") via `toasts.error`.
  - Rimosso il vecchio `toasts.success(currencyChange.done)` e il `warning(syncFailedManualRetry)` (entrambi sostituiti dalla logica sopra).
- i18n nuove: `assetDetail.currencyChange.{deleteSuccess, changedTo}` (4 lingue, accenti FR fix via script).
- **Differenza rispetto al flow `/assets` global**: la global usa il costrutto `toasts.success($t('assets.sync.toastOk'))` / `toasts.error($t('assets.sync.toastFailed') + ': ' + r.errors[0])`. Ora il currency change flow usa `buildAssetSyncToast` che è **strettamente più espressivo** (gestisce partial, skipped, noChanges, aggiunge icons SVG inline per prezzi/eventi). Volendo in futuro si può migrare anche `/assets` global al helper, per uniformità totale.

**Fix III — Icona FX corretta dall'utente** (verificata in AssetPriceSummary.svelte): ora usa `Coins` (icona monete, più evocativa di valuta rispetto a ArrowLeftRight che è per le coppie FX directional). **No action needed**.

**Fix IV — DataEditor i18n completato** (dal feedback part2): bottoni "Import CSV" / "Add Row" + empty-state message tradotti. i18n: `dataEditor.{importCsv, addRow, emptyMessage}` (già in part2).

**Indagine V — BTP Italia 2028 (tracked come I-bis #26)**:
- `db_populate`: passato BTP Italia 2028 da `SEMIANNUAL` + `generate_interest=True` a **`DAILY` + `generate_interest=False`** (request utente). Prossimo `db create-clean` produrrà la retta lineare pulita.
- Aggiunto logging debug in `_generate_schedule_values`: `cache HIT/MISS key=... periods=... first_freq=... first_gen_int=...`. Dal prossimo retest l'utente può vedere se il cache key cambia realmente quando modifica la config.
- Bug reset **non** fixato in questa sessione (scope troppo grande, richiede riordino Step 2/4 + regression test + verifica frontend editor). Documentato come I-bis #26 con 2 bug candidati + 3 ipotesi hashing + action items.

**Elenco flussi toast asset — prima/dopo (per decisione collettiva)**:

| Scenario | Prima (pre-batch2) | Dopo part2 | Dopo part3 (ora) |
|---|---|---|---|
| Sync normale OK (/assets global) | ✓ 1 success "N fetched, M changed" | identico (non toccato) | identico |
| Sync KO (/assets global) | ✓ 1 error "Sync failed per {name}: detail" | identico | identico |
| Sync dal detail (handleSyncAsset signal) | ✓ 1 toast via buildAssetSyncToast (hardcoded EN suffixes) | ✓ 1 toast via buildAssetSyncToast (5 stati i18n) | identico part2 |
| Currency change (provider assigned, sync OK) | 5 toast: 3 progress info + 1 success done + 1 success saveSuccess | 1 toast success done | **3 toast**: deleteSuccess + changedTo + syncOk |
| Currency change (provider assigned, sync PARTIAL) | 5 toast (come sopra) | 1 toast success done ❌ fuorviante | **3 toast**: deleteSuccess + changedTo + syncWarning con result.message |
| Currency change (provider assigned, sync FAIL es. Currency mismatch) | 5 toast + 1 warning syncFailedManualRetry | 1 success done + 1 warning generic ❌ | **3 toast**: deleteSuccess + changedTo + **error con detail backend** |
| Currency change (NO provider) | 3 toast (progress + done + saveSuccess) | 1 toast done | **2 toast**: deleteSuccess + changedTo |
| Currency change (delete KO) | error | error failed | identico part3 (error, toast #1 non parte) |
| Currency change (patch KO) | error | error failed | identico part3 (toast #1 parte, #2 no) |

**Raziocinio**:
- Part2 puntava alla minimizzazione (1 solo toast) ma perdeva informazioni importanti (l'errore sync post-wipe veniva nascosto).
- Part3 trova il giusto equilibrio: **1 toast per ogni step significativo**. Delete è un'operazione distruttiva — meritocraticamente degna di conferma. Patch è rapida ma produce la notifica chiave "currency changed" che l'utente si aspetta. Sync ha tutti i suoi stati compressi nel unified helper.

**File toccati in batch 2 part3**:
- `frontend/src/lib/stores/navigationStore.ts` (refactor stack-based + debug helper).
- `frontend/src/routes/(app)/+layout.svelte` (pass pathname to trackNavigation).
- `frontend/src/lib/components/assets/AssetCurrencyChangeModal.svelte` (3-toast refactor + buildAssetSyncToast integration).
- `frontend/src/lib/i18n/{en,it,fr,es}.json` (+2 chiavi: `currencyChange.{deleteSuccess, changedTo}`).
- `backend/test_scripts/test_db/populate_mock_data.py` (BTP Italia 2028 → DAILY + no interest).
- `backend/app/services/asset_source_providers/scheduled_investment.py` (+logging debug cache HIT/MISS).

**Validazione batch 2 part3**:
- `./dev.py front check` → ✅ 0 errors, 0 warnings.
- Backend format/lint → da rifare (ho modificato 2 file Python).

**Da testare con utente prima del commit**:
1. goBack FX → asset detail: deve tornare al detail corretto, non alla lista FX.
2. Toast currency change: 3 toast distinti (delete + changedTo + sync esito reale).
3. BTP Italia 2028: dopo `./dev.py db create-clean`, grafico deve essere retta pulita (no reset).
4. Log debug: `./dev.py server start` + sync BTP, cercare "scheduled_investment cache" nei log.

### 🎯 Cosa devo fare dopo (priorità in ordine)

**Prossimo commit suggerito**: batch refactor `FxBackwardFillInfo` da solo (piccolo e coeso). Messaggio:
```
Refactor: extract FxBackwardFillInfo as standalone building block

- Create FxBackwardFillInfo in common.py (fx_rate_date + fx_days_back).
- AssetBackwardFillInfo now inherits from BackwardFillInfo + FxBackwardFillInfo.
- FAAssetEventPointOut replaces flat fx_rate_date/fx_days_back with a single
  fx_info: Optional[FxBackwardFillInfo]. Events have no price-backward-fill
  semantics (discrete real dates) — only FX staleness is meaningful.
- Frontend +page.svelte reads ev.fx_info?.fx_rate_date / .fx_days_back.
- Tests updated to nested access.
- Wire format for prices is unchanged (mixin preserves field order).
```

**Poi batch 2** (~4-5h): I-bis UX quick wins
- **#3** Tab label "Prices in {currency} 🇺🇸" → 20 min (`AssetDataEditorSection.svelte`) ✅ DONE (batch 2 part1)
- **#4** Import CSV banner reminder → 20 min (`PriceDataImportModal.svelte`) ✅ DONE (batch 2 part1)
- **#6** Empty-state "Add manually" → 40 min (panel con 0 prezzi) ✅ DONE (batch 2 part1)
- **#12** Ridurre 5 toast currency-change → 1 (refactor `AssetCurrencyChangeModal.svelte`) ✅ DONE (batch 2 part2)
- **#1 + #23** combinati: handler unificato `PriceSyncResponse` con 5 stati toast i18n (ok/noChanges/partial+msg/skipped/failed) ✅ DONE (batch 2 part2)

**Prossimo batch 2.5** (~1h): retest + possibile fix I-bis #25 (goBack regression)
- Retest manuale I-bis #12 (flow currency change con e senza provider) + I-bis #1+#23 (sync che restituisce 0 changes, status partial, etc.).
- Se I-bis #25 è bloccante, fix (opzione a/b/c proposte nel journal).

**Batch 3** (~3-4h): Test coverage Blocco G (ordine per valore decrescente)
- **G.6** `test_ohlc_sentinel.py` — 8 casi (copre Blocco F dichiarato done ma non testato).
- **G.10** `test_asset_currency_change.py` — 5 casi (copre I.3 + I.6, flusso wipe+PATCH+re-sync).
- **G.11** `test_asset_prices_export.py` — 7 casi (copre I.4, endpoint `/prices/export`).
- **G.5** `test_prices_currency_coherence.py` — 3 casi post-I.11 (versione ridotta dopo i drop).

**Batch 4** (~4h): Test Blocco G coda + I-bis #22 prerequisito Part 4/5
- **G.3** `test_transactions_validate.py` — 6 casi.
- **G.4** `test_events_suggest.py` — 5+ casi parametrizzati.
- **G.1/G.2** estensioni `test_transaction_service.py` + matrix `test_transactions_api.py` (10+casi combinati).
- **G.7** entries nel `scripts/test_runner.py` (mancano ancora: transactions-validate, events-suggest, prices-currency, ohlc-sentinel, assets-currency-change, assets-prices-export).
- **G.8** coverage verification: `./dev.py test coverage services transaction` (target ≥90%) e `asset-source` (target ≥85%).

**Batch 5** (~3-4h): I-bis #22 refactor error handling
- Helper `$lib/utils/saveWithRetry.ts` o store `createSaveAction<T>`.
- Censimento dei modal impattati (AssetModal, AssetProviderAssignmentModal, AssetCurrencyChangeModal, BrokerModal, PriceDataImportModal, DataEditor save, futuro TransactionModal).
- Rollout progressivo + i18n `save.failed.*`.

**Batch 6** (~1h): code tails
- **#2** Provider dirty gating per "Save Without Testing?"
- **#5** CSV import resilience (auto-detect separator + header tolerance).
- **#7** `patch_assets_bulk` HTTP 409 semantics (non urgente).
- **I.10** validazione finale Blocco I (run completo test suite).
- Aggiornamento `phases/phase-07-transactions.md` con stato "Part 3 completed".
- Archiviazione plan chain in `phases/phase-07-transactions-subplan/` (skill `plan-archive`).

### ⚠️ Gotcha / note operative da ricordare

1. **Pipeline UTF-8 in shell**: `echo "é"` dal prompt zsh strippa accenti. Per aggiornare file `i18n/*.json` con caratteri non-ASCII → scrivere uno script `.py` a file (`/tmp/libreFolio_*.py`) + lanciarlo. Esempio già presente: `/tmp/libreFolio_restore_fr_indent.py`. **Non usare** `json.dump(..., indent=4)` su `fr.json`: il file usa indent=2 (come en/it/es) e `indent=4` fa un mega-diff di 2000 righe.
2. **Test FX pair pollution**: nel test DB alcune coppie (EUR/USD, GBP/USD) possono avere rate già seedati da altri test → le assertion su valore esatto falliscono. Per nuovi test: usare coppie esotiche (NZD/SGD, ILS/PHP, CAD/ZAR) + `_ensure_fx_rate` helper già presente in `test_events_target_currency.py`.
3. **`./dev.py lint --fix`**: dopo una cleanup (es. rimozione fx_error), può capitare di lasciare import orfani. Sempre girare `lint --fix` se `lint` segnala 1 errore auto-fixabile.
4. **Sintassi `./dev.py i18n add`**: richiede flag `--en --it --fr --es` (non posizionali). Esempio: `./dev.py i18n add foo.bar --en "Foo" --it "Bar" --fr "Baz" --es "Qux"`. Gli accenti **vanno comunque sistemati a mano dopo** (lo script strippa i chars non-ASCII in un pass intermedio).
5. **Non eseguire mai `git commit`** — solo proporre messaggi (regola copilot-instructions). Oggi sto scrivendo i messaggi in `/tmp/libreFolio_commit_*.txt` e l'utente committa.
6. **`requiredFxPairs` derived in `+page.svelte` L267–337**: non esiste un componente `FxPairBanner` separato — il banner è inline nel `{#each pairs}` a L1081–1153. Se si vuole riusare altrove (Phase 9 Dashboard), estrarlo prima in componente.
7. **FxBackwardFillInfo wire format**: `{fx_rate_date: "YYYY-MM-DD" | null, fx_days_back: number | null}`. Lato FE è `Partial<{...}>` (Zod) quindi entrambi i campi sono tecnicamente opzionali anche quando l'oggetto è presente — usare sempre optional chaining `obj?.fx_rate_date`.
8. **Emoji in Python scripts per i18n**: MAI usare escape surrogate pair (`\ud83d\udce5`) perché `write_text(encoding='utf-8')` fallisce con `UnicodeEncodeError: surrogates not allowed` DOPO aver truncato il file → file i18n azzerato. Alternative sicure: `\N{INBOX TRAY}` (Python named-char escape) oppure leggere l'emoji da un file già presente (es. `en.json`) e riusarla. Recovery: `git checkout HEAD -- frontend/src/lib/i18n/fr.json` + script che riapplica tutte le chiavi della sessione.

### ✅ Check-list di "sessione riaperta correttamente"

Quando la conversazione riparte, verificare:
- [ ] `git log --oneline | head -5` → identificare ultimo commit Closure (cercare "Part 3 Closure" o "FxBackwardFillInfo").
- [ ] `git status` → capire se ci sono file pendenti del refactor FxBackwardFillInfo (se sì, vedi sopra batch).
- [ ] Leggere questa sezione **Giornale di viaggio** per localizzare il cursore.
- [ ] Scorrere il Closure plan dall'alto cercando sezioni ancora **senza** ✅ DONE nel titolo → ordine di attacco.
- [ ] Verificare che i test API sopracitati passino (`./dev.py test api assets-price && assets-events && events-target-currency`). Se rossi → NON procedere: qualcosa nella sessione precedente è rimasto monco.
