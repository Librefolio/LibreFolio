# Plan: Phase 7 — Part 3: API Consolidation (atomic per-broker) + events/suggest + deferred from Part 1

**Data**: 20 Aprile 2026
**Status**: 📋 PIANIFICATO (pronto per implementazione)
**Priorità**: P0 (sblocca Part 4 transactions page e Part 5 Staging Modal)
**Effort stimato**: ~3–4 giorni (grosso; include gli spin-off Part 1 §8 e §9)
**Phase**: [Phase 7 — Transactions System](./phases/phase-07-transactions.md)
**Predecessori**:
- [plan-phase07-transaction-Part1.md](./plan-phase07-transaction-Part1.md) ✅
- [plan-phase07-transaction-Part2.prompt.md](./plan-phase07-transaction-Part2.prompt.md) ✅ (Revisione 2)

---

## 📌 Deviazioni dal piano originale

### Dev-2026-04-20 — Multi-broker atomic (non broker-scoped)

**Contesto**: il piano originale prevedeva `POST/PATCH/DELETE /brokers/{broker_id}/transactions/bulk`
con rifiuto immediato di qualsiasi item con `broker_id ≠ path`. Conflitto scoperto con
l'agent in sessione nuova: il test esistente `test_query_linked_tx_both_have_related_id`
crea un `TRANSFER` cross-broker (`test_broker` + `test_broker_overdraft`) in un'unica
`create_bulk` — caso d'uso reale perché la risoluzione `link_uuid → related_transaction_id`
richiede DEFERRABLE FK all'interno della **stessa session DB**.

**Use-case utente**: durante il rifinimento BRIM (parse di più file contemporaneamente)
o un bonifico manuale da-a, è naturale avere un set di transazioni che tocca più broker
come unica unità logica. BRIM non dirà mai "transazione linkata", lato utente è un
insert unico.

**Decisione**: gli endpoint bulk tornano su `/transactions/*` (non broker-scoped),
accettano item su più broker, l'atomicità è a livello di batch:
- Ogni `broker_id` distinto nel batch → access check `EDITOR`.
- `_validate_broker_balances` chiamato per ogni broker toccato.
- Qualsiasi violazione (FK, balance, access, broker mismatch su update) → rollback
  totale + `rolled_back=True`.
- Per-item `status: Literal["success","simulated","failed","not_attempted"]`.

**Endpoint finali**:
- `POST /transactions/bulk` (ex `POST /transactions`).
- `PATCH /transactions/bulk` (ex `PATCH /transactions`).
- `DELETE /transactions/bulk?ids=...` (ex `DELETE /transactions?ids=...`).
- `POST /transactions/validate` (nuovo, non broker-scoped).
- `GET /transactions?ids=...` (come da piano, con filtro broker accessibili).
- `POST /transactions/events/suggest` (come da piano).
- `GET /transactions/{tx_id}` **rimosso**.

**Frontend TODO per Part 4/5**: la Staging Modal deve gestire draft multi-broker
in un singolo set atomico (es. tabs per broker, preview bilanci multi-broker,
indicazione visiva quando una coppia `link_uuid` attraversa broker).

**Decisione break-API**: utente conferma pre-beta, posso rompere senza wrapper
legacy. `TXCreateResultItem/TXUpdateResultItem/TXDeleteResult` ottengono un nuovo
campo `status` tri-state + `success` resta per retro-logica semplice.

### Dev-2026-04-20 — Commit A+B fusi

Blocchi A (service) e B (router) sono inseparabili: cambiare le firme del
service senza aggiornare il router lascia il backend non-compilante. Vengono
committati insieme come "Part 3 Block A+B — multi-broker atomic transactions".

---

> **📌 Contesto**: piano unificato che raccoglie **Parte 3 API consolidation**
> (full-bulk + atomic per-broker, come Revisione 2 del macro-plan), il sotto-piano
> **3b events/suggest** (slider tolerance 0–7gg), e tutti i **deferred da Parte 1**
> rimandati a Parte 3 (i18n delete eventi, mock data, price currency validation,
> OHLC `-1` sentinel + current-price auto-extend).
>
> Unico file, esecuzione in 7 blocchi sequenziali con lint/format+test verdi al
> termine di ciascun blocco.

---

## 🎯 Obiettivo

1. **Consolidare l'API transazioni** in stile full-bulk + **atomic per-broker**:
   sposta le 3 rotte mutanti sotto `POST/PATCH/DELETE /brokers/{broker_id}/transactions/bulk`
   con rollback totale su qualsiasi violazione. Rimuovi `GET /transactions/{id}`,
   aggiungi `GET /transactions?ids=1,2,3` ordinato.
2. **Uniformare l'access control** derivandolo da `BrokerUserAccess` (1 check
   per-batch, non per-item): `EDITOR` per create/update/delete, filtro
   automatico dei broker accessibili su `GET /transactions`.
3. **Introdurre `POST /brokers/{broker_id}/transactions/validate`** — dry-run
   **misto** (create + update + delete nella stessa richiesta) consumato dalla
   Staging Modal in live (debounced).
4. **Introdurre `POST /transactions/events/suggest`** — ricerca eventi candidati
   entro ±tolerance_days ∈ [0,7], input e risposta parallela per batch.
5. **Chiudere i deferred di Parte 1**:
   - (D) i18n delete-event toasts + mock data estesi.
   - (E) Price currency coherence: `FAPricePoint.original_currency` sempre,
     `fx_error` discriminato, `currency_breakdown`, validazione upsert,
     auto-registrazione FX mancanti, banner frontend distinti.
   - (F) OHLC partial upsert + sentinel `-1` + current-price auto-extend
     intra-day + icona "gomma" 🧽 con placeholder i18n `dataEditor.cell.notSet`.

---

## 📊 Situazione di partenza

### Backend — `transaction_service.py` (699 righe, post-Part1)
- `create_bulk(items, user_id)` — access check **per-item** con cache (da semplificare).
- `update_bulk(items)` e `delete_bulk(items)` — **nessun access check** (gap da chiudere).
- Tutti i `*_bulk` sono **best-effort per-row**: raccolgono `results[]` misti e il router decide
  commit/rollback leggendo `len(errors)`. Semantica da sostituire con "atomic: tutto o niente".
- `_validate_asset_event_link` già presente (Part 1).
- `query(params: TXQueryParams)` — non filtra per broker accessibili all'utente. Gap da chiudere.

### Backend — `api/v1/transactions.py` (287 righe)
- `POST /transactions` — multi-broker, best-effort.
- `GET /transactions` — senza filtro per accesso utente.
- `GET /transactions/{id}` — **da rimuovere**.
- `GET /transactions/types` — OK, resta.
- `PATCH /transactions` — passa `user_id` ma il service lo ignora.
- `DELETE /transactions?ids=…` — idem.

### Backend — `api/v1/brokers.py`
- Dopo Revisione 2 di Parte 2: nessun endpoint `/import/commit`. Il commit della Staging
  andrà obbligatoriamente sul nuovo `POST /brokers/{broker_id}/transactions/bulk`.
- Pattern già usato per `/{broker_id}/summary` e `/import/upload?broker_id=…`.

### Backend — prezzi / eventi (Blocchi E+F)
- `asset_source.upsert_prices_bulk` accetta `currency` qualsiasi, anche ≠ `Asset.currency`.
- `FAPricePoint.backward_fill_info` mostra solo il caso price-backward-fill; nessuna
  discriminazione `pair_missing` vs `no_rate_at_date`.
- `current_price_service` → se il provider fornisce solo `close`, non popola OHLC e
  non estende min/max intra-day.
- Nessun sentinel `-1` per `SET NULL`; oggi `None` nel payload = no-op.

### Frontend
- `AssetDataEditorSection.svelte` → stringhe letterali nei toast delete eventi.
- Nessuna icona gomma 🧽 per-cella OHLC, nessun placeholder `notSet`.
- Banner prezzi: solo "FX missing per target_currency" generico; manca mismatch
  intra-serie e distinzione `pair_missing` vs `no_rate_at_date`.

### Dati di test
- `populate_mock_data.py` — `link_transactions_to_events()` linka solo AAPL DIVIDEND.
  Manca INTEREST linked e tx "hidden" su broker non accessibile (fixture per E2E Parte 4).

---

## 🗂️ Scope (files)

| # | File | Tipo | Blocco |
|---|------|------|--------|
| 1 | `backend/app/services/transaction_service.py` | Modifica | A |
| 2 | `backend/app/schemas/transactions.py` | Modifica | A, C |
| 3 | `backend/app/api/v1/transactions.py` | Modifica | B, C |
| 4 | `backend/app/api/v1/brokers.py` | Modifica | B, C |
| 5 | `backend/app/services/asset_source.py` | Modifica | E, F |
| 6 | `backend/app/schemas/prices.py` | Modifica | E |
| 7 | `backend/app/services/current_price.py` (nome da verificare) | Modifica | F |
| 8 | `backend/app/services/fx_provider.py` (auto-register) | Modifica | E |
| 9 | `frontend/src/lib/components/assets/AssetDataEditorSection.svelte` | Modifica | D |
| 10 | `frontend/src/lib/components/assets/PriceEditorSection.svelte` | Modifica | E, F |
| 11 | `frontend/src/lib/components/assets/FxMissingBanner.svelte` | Nuovo/Modifica | E |
| 12 | `frontend/src/lib/i18n/locales/{en,it,fr,es}/*.json` | Modifica | D, E, F |
| 13 | `backend/test_scripts/test_db/populate_mock_data.py` | Modifica | D |
| 14 | `backend/test_scripts/test_api/test_transactions_api.py` | Modifica | G |
| 15 | `backend/test_scripts/test_services/test_transaction_service.py` | Modifica | G |
| 16 | `backend/test_scripts/test_api/test_events_suggest.py` | **Nuovo** | G |
| 17 | `backend/test_scripts/test_api/test_transactions_validate.py` | **Nuovo** | G |
| 18 | `backend/test_scripts/test_services/test_prices_currency_coherence.py` | **Nuovo** | G |
| 19 | `backend/test_scripts/test_services/test_ohlc_sentinel.py` | **Nuovo** | G |
| 20 | `scripts/test_runner.py` | Modifica | G |

---

## 🔧 Blocchi di esecuzione

> Dopo ogni blocco: `./dev.py format && ./dev.py lint && ./dev.py test <scope>`.
> Dopo A–C (backend core): `./dev.py api sync && ./dev.py front check`.
> I blocchi con modifiche UI (D, E-frontend, F-frontend) richiedono **test manuale
> estetico dell'utente** prima di chiudere il blocco. L'agent deve fermarsi e chiedere conferma.

### Blocco A — Service refactor: atomic + broker-scoped

1. Aggiungere `TransactionService._check_broker_access_or_raise(broker_id, user_id, min_role)` che lancia `HTTPException(403)` su miss. Usato una volta per batch.
2. Refactor `create_bulk(broker_id, items, user_id)`:
   - Rifiuta immediatamente se qualche `item.broker_id != broker_id` → `HTTPException(400, "broker_id mismatch on item N")`, nessun insert.
   - 1 solo `_check_broker_access_or_raise(broker_id, user_id, EDITOR)`.
   - Qualsiasi `Exception` interrompe il loop: `await session.rollback()`, popola `results[]` con `simulated / failed / not_attempted`, return `rolled_back=True`, `success_count=0`.
   - A fine loop → `_validate_broker_balances` nella stessa sessione; se lancia → rollback + `rolled_back=True` + `errors=[str(e)]`.
   - Nessun commit interno; il commit è gestito dal router (Blocco B) solo se `rolled_back=False`.
3. `update_bulk(broker_id, items, user_id)`: stessa semantica + per ogni item verifica che la tx esista e appartenga a `broker_id`.
4. `delete_bulk(broker_id, ids, user_id)`: stessa semantica + ogni id deve appartenere a `broker_id`.
5. **Nuovo** `validate_batch(broker_id, creates, updates, deletes, user_id)` — motore comune dry-run (Blocco C).
6. `query(params, user_id)`: JOIN implicito con `BrokerUserAccess`. Nuovo param opzionale `ids: Optional[List[int]]` che ritorna nell'ordine richiesto.
7. Rimuovere `get_by_id()` (dead code post-Blocco B).

**Schemi**:
- `rolled_back: bool = False` in `TXBulkCreateResponse`, `TXBulkUpdateResponse`, `TXBulkDeleteResponse`.
- Docstring `TXCreateItem.asset_event_id`: "omit to leave unlinked".
- Docstring `TXUpdateItem.asset_event_id`: "0 = unlink (Part 1 sentinel), >0 = link".

---

### Blocco B — Router refactor: broker-scoped endpoints

1. **Rimuovere** `GET /transactions/{tx_id}`.
2. **Spostare** le 3 rotte bulk su `brokers_router`:
   - `POST   /brokers/{broker_id}/transactions/bulk` — body `List[TXCreateItem]`.
   - `PATCH  /brokers/{broker_id}/transactions/bulk` — body `List[TXUpdateItem]`.
   - `DELETE /brokers/{broker_id}/transactions/bulk?ids=1,2,3`.
   - Router: se `response.rolled_back` → return (service ha già rollato), altrimenti `await session.commit()` e return.
3. **Lasciare** su `/transactions`:
   - `GET /transactions` con nuovo `ids: Optional[List[int]] = Query(None)` (mutex con gli altri filtri).
   - `GET /transactions/types` invariato.
4. **Grep pre-deploy** sul frontend per callsite a `GET /transactions/{id}`; sostituire con `?ids=N`.
5. **Pulizia** endpoint vecchi: cancellare `POST/PATCH/DELETE /transactions`. Nessun wrapper legacy.

---

### Blocco C — `/validate` dry-run misto + `/events/suggest`

#### C.1 `POST /brokers/{broker_id}/transactions/validate`

Semantica: batch **misto** creates + updates + deletes, verdetto unico.

**Schemi nuovi**:
- `TXValidateBatch { creates: List[TXCreateItem], updates: List[TXUpdateItem], deletes: List[int] }` — `default_factory=list`, `extra="forbid"`, cap 500 per lista.
- `TXValidationIssue { operation: Literal["create","update","delete"], index: int, ref_id: Optional[int], error: str }`.
- `TXValidateResponse { would_rollback: bool, issues: List[TXValidationIssue], balance_preview: Dict[str, Decimal], holdings_preview: Dict[int, Decimal] }`.

**Motore `validate_batch`**:
1. Access-check `EDITOR`.
2. Rigetta (come issue, non eccezione) create/update.broker_id ≠ path o delete id non del broker → `would_rollback=True`, return senza flush.
3. Esegue in ordine `deletes → updates → creates` nella stessa sessione. Ogni eccezione → issue, **loop non si ferma** (vogliamo set completo).
4. `_validate_broker_balances` una volta; fallimento → issue `create` con `str(BalanceValidationError)`.
5. Calcola `balance_preview` e `holdings_preview` da sessione flushata.
6. **SEMPRE** `await session.rollback()` a fine metodo.
7. `would_rollback = len(issues) > 0 or balance_violation`.

Router: non commita mai.

#### C.2 `POST /transactions/events/suggest`

Non broker-scoped (asset events sono globali).

**Schemi nuovi**:
- `TXEventSuggestRequestItem { asset_id: int>0, date, type: TransactionType, tolerance_days: int = Field(0, ge=0, le=7) }`.
- `TXEventSuggestResultItem { asset_id, date, type, candidates: List[AssetEventReadItem], skipped_reason: Optional[Literal["type_not_event_compatible"]] }`.

**Service `suggest_events_bulk(requests)`**:
- Se type non in `EVENT_COMPATIBLE_TYPES` → `candidates=[]`, `skipped_reason`.
- Altrimenti SELECT `AssetEvent WHERE asset_id=req.asset_id AND ABS(date - req.date) <= tolerance_days AND event_type_maps_to(tx_type)` ORDER BY distanza asc.
- Mapping: `DIVIDEND↔DIVIDEND`, `INTEREST↔INTEREST`, `ADJUSTMENT↔(PRICE_ADJUSTMENT|SPLIT)`.

Body `List[TXEventSuggestRequestItem]` cap 500. Response stesso ordine input. Nessun side-effect. Solo auth utente.

---

### Blocco D — i18n delete-events + mock data (deferred Part 1)

1. `./dev.py i18n add` × 4 lingue:
   - `events.deleteSuccess` = "{count} event(s) deleted"
   - `events.deleteNotFound` = "Event(s) not found: {ids}"
   - `events.deletePartial` = "{deleted} deleted, {inUse} in use, {notFound} not found"
   - `events.deleteBlocked` = "Cannot delete: {count} event(s) still in use by transactions ({accessible} visible to you, {hidden} in other users' portfolios)"
2. Sostituire letterali "Asset data: …" in `AssetDataEditorSection.svelte`.
3. **🎨 Test manuale utente** — verificare wording nei 4 linguaggi triggerando i 4 scenari.
4. `populate_mock_data.link_transactions_to_events()`:
   - +1 tx `INTEREST` su bond mock (BTP) linkata a `AssetEvent INTEREST` esistente.
   - +1 tx DIVIDEND su broker **non** accessibile a `e2e_test_user` (admin-only OWNER). Fixture per caso "hidden" spec E2E Parte 4.
   - `./dev.py db create-clean` + verifica visuale.

---

### Blocco E — Price currency coherence (deferred Part 1 §8)

#### E.1 `FAPricePoint`
- `original_currency: str` **sempre popolato** (= `currency` se no-conversion, = valuta pre-conversione altrimenti).
- `backward_fill_info: Optional[...]` popolato sse `days_back>0 OR fx_rate_date OR fx_error`.
- Nuovo campo in `AssetBackwardFillInfo`: `fx_error: Optional[Literal["pair_missing","no_rate_at_date"]]`.

5 stati:
- (A) no-conversion+no-stale → `backward_fill_info = None`.
- (B) conversion same-day → `fx_rate_date=date_point, fx_days_back=0`.
- (C) conversion backward-filled → `fx_days_back=N>0`.
- (D) pair non in registry → `fx_*=None, fx_error="pair_missing"`.
- (E) pair esiste ma pre-history → `fx_*=None, fx_error="no_rate_at_date"`.

#### E.2 `FAPriceQueryResult`
- `currency_breakdown: List[CurrencyBreakdownEntry]` con `{currency, count, first_date, last_date}` (SELECT GROUP BY currency).

#### E.3 Validazione `upsert_prices_bulk`
- Carica `asset.currency`, item con `currency != asset.currency` → `errors.append(...)` e skip item. No hard-fail.

#### E.4 Sync-all auto-registrazione FX
- Raccogli coppie `(point.currency, asset.currency)` mismatch + tutti `fx_error="pair_missing"`.
- Chiama `fx_provider_manager.ensure_pair_registered(base, quote)`:
  - Già presente → no-op.
  - Altrimenti → inserisci con provider di default + log INFO.
- Stesso per coppie event/display-currency.

#### E.5 Frontend banner mismatch intra-serie
- Componente `PriceCurrencyMismatchBanner.svelte` (o estensione FxMissing).
- Attivo se `result.currency_breakdown.length > 1`.
- Layout: lista currency dissonanti + count + range date.
- Azioni: **[Normalize]** → nuovo endpoint `POST /assets/{id}/prices/normalize` (converte punti dissonanti a `asset.currency`). **[Ignore]** → `asset.meta.ignore_currency_mismatch=true`.
- i18n: `prices.currencyMismatch.{title,body,normalize,ignore}` × 4.
- **🎨 Test manuale utente**.

#### E.6 Frontend banner FX-missing differenziato
- Leggi `backward_fill_info.fx_error` aggregato.
- "Coppia FX {X}/{Y} non configurata — [Aggiungi al registry →]" (`pair_missing`).
- "FX {X}/{Y} configurata ma mancano rate prima di {date} — [Sync storico →]" (`no_rate_at_date`).
- i18n: `prices.fxMissing.{pairMissing,noRateAtDate}` × 4.
- **🎨 Test manuale utente**.

#### E.7 Frontend data-editor prezzi
- Pre-fill colonna `currency` con `asset.currency` sui nuovi append.
- Cambio valore → ⚠️ inline warning cella.
- i18n: `dataEditor.warning.currencyMismatch` × 4.

#### E.8 `query_events_bulk` param `target_currency`
- Converte `event.value` a display-currency alla data dell'evento.
- Miss FX → `result.errors[]` "Missing FX rate for event on {date}". No hard-fail.

---

### Blocco F — OHLC partial upsert + sentinel `-1` + current-price auto-extend (deferred Part 1 §9)

#### F.1 Principio
**Provider > utente**: niente `manual_override_fields`. Provider sovrascrive liberamente.

#### F.2 Current-price bootstrap OHLC (row nuova)
- First-time `(asset, today)` con solo `close` → insert con `open=high=low=close`, `volume=None`.

#### F.3 Current-price auto-extend intra-day (row esistente) — **nuovo, richiesto**
Nuovo helper `_extend_ohlc_bounds(existing, new_close) -> dict`:
- `low = min(existing.low, new_close)` o `new_close` se None.
- `high = max(existing.high, new_close)` o `new_close` se None.
- `open = new_close` se `existing.open is None`.
- `volume` intatto.
Invocato **solo** dal path current-price. Log DEBUG `"Extended intra-day range for {asset}@{date}: low {old}→{new}, high {old}→{new}"`.

#### F.4 Sentinel `-1` per SET NULL
Nel payload upsert `open/high/low/close/volume`:
- `null`/omesso → **no-op** (merge parziale).
- ≥ 0 → scrivi.
- `-1` → `SET NULL`. Niente flag manual.

Query-time:
- `close=NULL` → punto vuoto, backward-fill con `backward_fill_info.days_back`.
- `open/high/low=NULL` → candela derivata da `(close_{t-1}, close_t)` o ignorata.
- `volume=NULL` → display `—`.

Docstring in `FAPricePoint` + sezione mkdocs "Sentinel values in price upsert".

Caveat volume: pre-upsert `if incoming.volume == -1 and source == "provider": incoming.volume = None`.

#### F.5 Frontend gomma 🧽 + placeholder `notSet`
- Cella OHLC/volume hover → icona gomma (lucide `Eraser`). Click → popover conferma → `-1` in payload.
- Shortcut `Delete` su cella selezionata = stesso effetto.
- **Sentinel mai visibile**: dopo cancellazione o reload NULL → placeholder i18n `dataEditor.cell.notSet` in italic grigio chiaro:
  - EN "Not set", IT "Non impostato", FR "Non défini", ES "No establecido".
- Parser input: vuoto e placeholder = no-op (no payload field); solo 🧽 → `-1`.
- **🎨 Test manuale utente** per styling + popover + shortcut.

---

### Blocco G — Test coverage + API sync

#### G.1 `test_transaction_service.py` (estendi)
Fixture: OWNER / EDITOR / VIEWER / FOREIGN.

Casi:
- `test_create_bulk_atomic_rollback_on_overdraft`.
- `test_create_bulk_atomic_rollback_on_shorting`.
- `test_create_bulk_atomic_rollback_on_asset_event_mismatch`.
- `test_create_bulk_rejects_broker_mismatch_immediately`.
- `test_update_bulk_requires_editor`.
- `test_update_bulk_rejects_foreign_tx`.
- `test_delete_bulk_requires_editor`.
- `test_delete_bulk_rejects_linked_without_pair` (verificare che ora sia atomic).
- `test_query_filters_accessible_brokers_only`.
- `test_query_by_ids_preserves_order`.

#### G.2 `test_transactions_api.py` (estendi)
Matrix OWNER/EDITOR/VIEWER × POST/PATCH/DELETE × owned/foreign broker.
- `test_get_single_by_ids` (sostituto `/5`).
- `test_get_tx_id_route_is_removed` → 404 (non 405).

#### G.3 `test_transactions_validate.py` (nuovo)
- `test_validate_empty_batch`.
- `test_validate_mixed_creates_updates_deletes` (ordine delete→update→create).
- `test_validate_reports_all_issues_not_just_first`.
- `test_validate_no_side_effect`.
- `test_validate_would_rollback_true_on_balance_violation`.
- `test_validate_rejects_broker_mismatch`.

#### G.4 `test_events_suggest.py` (nuovo)
Fixture AAPL con eventi DIVIDEND a `-5,-3,-1,0,+1,+3,+5`:
- Parametrizzato `tolerance_days ∈ {0,3,7}` → 1, 7, 15 eventi.
- `test_suggest_ordering_by_distance_asc`.
- `test_suggest_type_not_event_compatible` (BUY → skipped).
- `test_suggest_type_mapping_adjustment_to_split_and_price`.
- `test_suggest_preserves_request_order`.
- `test_suggest_max_batch_size` (501 → 422).

#### G.5 `test_prices_currency_coherence.py` (nuovo)
- `test_original_currency_always_populated`.
- `test_backward_fill_info_none_when_all_ok`.
- `test_fx_error_pair_missing`.
- `test_fx_error_no_rate_at_date`.
- `test_currency_breakdown_single_currency`.
- `test_currency_breakdown_multi_currency`.
- `test_upsert_rejects_currency_mismatch_via_errors`.
- `test_sync_all_auto_registers_missing_fx_pairs`.
- `test_normalize_endpoint_converts_dissonant_points`.

#### G.6 `test_ohlc_sentinel.py` (nuovo)
- `test_sentinel_minus_one_sets_null_on_close`.
- `test_null_field_is_noop`.
- `test_provider_overrides_user_cleared_field`.
- `test_current_price_bootstrap_populates_ohlc`.
- `test_current_price_extends_intraday_low_high`.
- `test_current_price_preserves_open_if_set`.
- `test_current_price_volume_not_modified`.
- `test_volume_minus_one_from_provider_mapped_to_none`.

#### G.7 `scripts/test_runner.py`
Aggiungere entry:
- `api/transactions-validate`
- `api/events-suggest`
- `services/prices-currency`
- `services/ohlc-sentinel`

#### G.8 Coverage target
- `transaction_service.py` ≥ 90%.
- `asset_source.py` (funzioni toccate) ≥ 85%.

#### G.9 Validazione finale
```bash
./dev.py format && ./dev.py lint
./dev.py api sync && ./dev.py front check
./dev.py test services transaction
./dev.py test api transactions
./dev.py test api transactions-validate
./dev.py test api events-suggest
./dev.py test services prices-currency
./dev.py test services ohlc-sentinel
./dev.py test all-backend
```

---

## 📦 Deliverable

### API
- `POST/PATCH/DELETE /brokers/{broker_id}/transactions/bulk` atomic + `rolled_back`.
- `POST /brokers/{broker_id}/transactions/validate` dry-run misto.
- `POST /transactions/events/suggest` tolerance 0–7gg.
- `POST /assets/{id}/prices/normalize` conversione punti dissonanti.
- `GET /transactions?ids=…` (sostituisce `/{id}` rimosso).
- `GET /transactions` filtrato per broker accessibili.

### Service
- `TransactionService.*_bulk` atomiche + broker-scoped.
- `TransactionService.validate_batch`, `.suggest_events_bulk`.
- `asset_source.upsert_prices_bulk` validazione currency.
- `asset_source._extend_ohlc_bounds` intra-day.
- `fx_provider_manager.ensure_pair_registered`.

### Schemi
- `rolled_back` in tutti i TXBulk*Response.
- `TXValidateBatch`, `TXValidationIssue`, `TXValidateResponse`.
- `TXEventSuggestRequestItem`, `TXEventSuggestResultItem`.
- `FAPricePoint.original_currency` sempre.
- `AssetBackwardFillInfo.fx_error`.
- `FAPriceQueryResult.currency_breakdown`.

### Frontend
- Toast delete-eventi i18n × 4 lingue × 4 scenari.
- Banner mismatch intra-serie.
- Banner FX-missing differenziato.
- Icona 🧽 + placeholder `notSet` × 4 lingue.
- i18n keys: `events.delete*`, `prices.currencyMismatch.*`, `prices.fxMissing.*`, `dataEditor.warning.currencyMismatch`, `dataEditor.cell.notSet`.

### Dati di test
- `populate_mock_data.py` + INTEREST linked + tx su broker hidden.

### Test
- 4 nuovi file test (≥ 35 test case aggiunti).
- Matrix access control completa.
- Coverage ≥ 90% su `transaction_service`.

---

## 🔎 Decisioni & Note

| # | Decisione | Note |
|---|-----------|------|
| 1 | Unico piano Part 3 (no split 3b/3c) | Coerente con phase doc, evita fragmentazione |
| 2 | `/validate` accetta **mix** creates+updates+deletes | La Staging ha draft eterogenei |
| 3 | `/validate` ordine `deletes → updates → creates` | Creates vedono DB post-cleanup |
| 4 | `/validate` NON si ferma al primo errore | Set completo di issues per UI feedback |
| 5 | Atomic rollback → `results[]` diagnostico | `simulated / failed / not_attempted` |
| 6 | Sentinel `-1` mai visibile in UI | Placeholder `dataEditor.cell.notSet` |
| 7 | Provider > utente sui prezzi | No `manual_override_fields` |
| 8 | Auto-registrazione FX su mismatch | Riduce friction utente |
| 9 | Blocchi UI → test manuale utente | Esplicito nel flusso |

---

## 🚧 Rischi & Mitigazioni

| Rischio | Mitigazione |
|---------|-------------|
| Blocco grosso → commit monstre | Commit + test al termine di ogni blocco |
| Banner styling divergente tra browser | Test manuale estetico esplicito |
| Migration `original_currency` | Computed on-read, no migration DB |
| Breaking `GET /transactions/{id}` | Grep frontend pre-deploy, no wrapper legacy |
| `/validate` lento su batch grandi | Cap 500 items per lista (Pydantic) |
| Conflitto `-1` con volume reale | Mapping pre-upsert da provider |

---

## 🔗 Cross-link

- **Predecessori**: [Part1](./plan-phase07-transaction-Part1.md) ✅, [Part2](./plan-phase07-transaction-Part2.prompt.md) ✅.
- **Successori**: Part 4 (pagina /transactions), Part 4b (File Preview), Part 5 (Staging Modal).
- **Phase doc**: [phase-07-transactions.md](./phases/phase-07-transactions.md) §Parte 3.

---

## ✅ Come validare esternamente

```bash
# 1) Format + lint + sync
./dev.py format && ./dev.py lint
./dev.py api sync && ./dev.py front check

# 2) Test mirati
./dev.py test services transaction
./dev.py test api transactions
./dev.py test api transactions-validate
./dev.py test api events-suggest
./dev.py test services prices-currency
./dev.py test services ohlc-sentinel

# 3) Regressione completa
./dev.py test all-backend

# 4) Test manuale estetico (Blocchi D, E.5, E.6, E.7, F.5)
```
