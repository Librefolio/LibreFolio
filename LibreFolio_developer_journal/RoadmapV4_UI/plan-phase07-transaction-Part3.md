# Plan: Phase 7 — Part 3: API Consolidation (atomic per-broker) + events/suggest + deferred from Part 1

**Data**: 20 Aprile 2026 · **Ultimo update**: 22 Aprile 2026 (notte — batch 7: closure plan creato, decisioni terminali Blocco E consolidate)
**Status**: 🏗️ IN CORSO (A+B, C, D ✅ · H ✅ · I.1–I.8 ✅ · F.3 validato · I-bis #8/#9/#10/#11/#13/#14/#15/#16/#17/#18/#20/#21 ✅ · Pending tasks → vedi Closure plan)
**Priorità**: P0 (sblocca Part 4 transactions page e Part 5 Staging Modal)
**Effort stimato**: ~3–4 giorni (grosso; include gli spin-off Part 1 §8 e §9)
**Phase**: [Phase 7 — Transactions System](./phases/phase-07-transactions.md)
**Predecessori**:
- [plan-phase07-transaction-Part1.md](./plan-phase07-transaction-Part1.md) ✅
- [plan-phase07-transaction-Part2.prompt.md](./plan-phase07-transaction-Part2.prompt.md) ✅ (Revisione 2)

**Successore (chiusura Part 3)**:
- [plan-phase07-transaction-Part3_1_Closure.md](./plan-phase07-transaction-Part3_1_Closure.md) ⏳ — raccoglie **tutti** i task pendenti con decisioni terminali post Q&A 2026-04-22:
  - **Blocco E** residuo (E.3 cleanup, E.8 implementazione) + cancellazione E.1/E.2/E.4/E.5/E.6/E.7.
  - **Blocco G** intero (test coverage: 6 nuovi file + estensioni G.1/G.2 + runner + coverage target).
  - **I.9/I.10** test adaptations post Blocco I (hard-400 currency mismatch).
  - **Blocco F** verifica finale (codice ✅, test demandati a G.6).
  - **Coda I-bis**: #1/#2/#3/#4/#5/#6/#7/#12/#19/#22/#23.

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

### Dev-2026-04-21 — Blocco H inserito dopo D (transfer semantics + promotion)

In review dei commit A+B/C/D sono emerse 4 domande di design non coperte dal
piano originale, che portano al nuovo **Blocco H** (vedi sotto, prima di E):

1. **Validazione pairing su broker/tipo coerenti** — oggi nessun vincolo impedisce
   un TRANSFER con due item sullo stesso broker (no-op semantico), né un mix di
   tipi nello stesso `link_uuid`. Regole nuove: TRANSFER richiede broker distinti,
   la coppia deve condividere lo stesso `type`. FX_CONVERSION resta intra-broker
   OK (use-case reale: conversione multi-valuta su conto unico).
2. **Pairing soft per DEPOSIT/WITHDRAWAL** — la coppia "bonifico cash tra i miei
   broker" (es. 5k EUR da Fineco a IBKR) oggi esiste come due tx sciolte. Estendo
   il meccanismo `link_uuid`: diventa facoltativo per DEPOSIT/WITHDRAWAL e produce
   un `related_transaction_id` bidirezionale anche su questi tipi. Nessun tipo
   nuovo (no `CASH_TRANSFER`), nessun effetto su balance o PMC — solo marker di
   intenzione che aiuta refinement BRIM e UX.
3. **Suggeritore di trasferimenti** — ho valutato `POST /transactions/transfers/suggest`
   dedicato e l'ho **scartato**: il match è una combinazione di filtri (segno
   opposto, tolleranza temporale/importo, escludi già linkate/stesso broker) che
   si risolve estendendo `GET /transactions` con 3 filtri nuovi
   (`amount_abs_min`, `amount_abs_max`, `only_unlinked`) + `exclude_ids`. Il
   client calcola i parametri dalla tx "seed" e ottiene la lista candidata.
   Meno superficie API, più composabilità.
4. **Promozione coppia DEPOSIT/WITHDRAWAL → TRANSFER/FX_CONVERSION** — richiesta
   dal flusso "refinement BRIM". Cambiare `type` via `PATCH /bulk` è vietato
   dalla policy (immutable-type). Serve un endpoint atomico
   `POST /transactions/transfers/promote` che: validate → delete pair →
   create pair con nuovo type + link, tutto in un batch atomico riciclando la
   stessa logica di `create_bulk`.

Tipo `TRANSFER` **resta valido** per gli asset (azioni/ETF tra broker): l'alternativa
SELL/BUY o DEPOSIT/WITHDRAWAL rompe il cost-basis FIFO (`cost_basis_override` va
propagato). Per il cash intra-utente basta la coppia linkata senza nuovo tipo.

---

### Dev-2026-04-21 — Revisione Blocchi E/F in fase di checklist → Blocco I (currency simplification)

In fase di redazione della **checklist funzionale** di verifica post-implementazione dei
Blocchi A–H abbiamo individuato **vicoli ciechi logici** sui Blocchi E (price currency
coherence) ed F (OHLC sentinel), in particolare:

1. **Ridondanza banner FX**: i sotto-punti E.5, E.6 introducono banner inline nel
   `AssetPriceSummary` che **duplicano** semanticamente i banner full-width già presenti
   in `+page.svelte` via `requiredFxPairs` (stati `missing`/`no-data`/`partial-gap`).
   L'utente con un asset USD visualizzato in EUR senza pair registrata vede **tre**
   avvisi per lo stesso problema (icona inline + banner full-width + bottone 🪙 in due
   posti). Design debt.
2. **E.5 banner intra-serie non raggiungibile via UI**: con E.3 attivo (validation
   per-item al save) il DB non può mai contenere serie multi-currency per lo stesso
   asset — quindi `currency_breakdown.length > 1` è una condizione che via path normale
   non si verifica. Il banner è dead code per la UI, vivo solo per dati corrotti / SQL
   manipulation. Consumo cognitivo sproporzionato.
3. **E.7 warning pre-save in editor**: nato per segnalare mismatch *prima* che E.3
   skippi la riga → ma se il vincolo diventa "hard" al write, questa informazione
   arriva dal backend come errore reale, rendendo superfluo il pre-check frontend.
4. **Asset currency immutable o destructive change?** L'attuale PATCH asset permette
   di cambiare `asset.currency` senza toccare `price_history.currency` → incoerenza
   latente. Decisione: ogni cambio di valuta deve **cancellare** tutti i prezzi
   esistenti (l'utente li rifà via provider sync o import CSV), no bulk-convert (evita
   drift, evita dipendenza da FX history).
5. **Denormalizzazione `price_history.currency`**: la colonna resta nel DB come canary
   forensic (3 bytes/riga, serve per debugging `p.currency != asset.currency` in caso
   di corruption), ma **viene rimossa dall'API response** (`FAPricePoint.currency`):
   il frontend usa `asset.currency` come unica fonte di verità lato client. Il
   backend già carica `asset.currency` per la validation al write → nessun lookup
   extra introdotto.
6. **BRIM esente dal vincolo**: i plugin BRIM scrivono **transazioni** (che hanno
   currency propria, libera), non `price_history`. Zero impatto sugli importer.
7. **Eventi esenti dal vincolo**: `asset_events.currency` resta libera per supportare
   ADR (stock USD che paga dividendi in yen/euro a seconda del domicilio del payer).
   Asimmetria intenzionale documentata.

La checklist funzionale **non è ancora stata eseguita** — i Blocchi A–H hanno solo
passato i test unitari/API; lo scoperto di cui sopra è emerso *leggendo* la checklist
prima di eseguirla. Di conseguenza:

- Alcuni Blocchi (in particolare **E.2, E.3, E.5, E.7, E.8** e la parte banner-related
  di E.6) vanno **reinterpretati o rimossi** alla luce del nuovo design.
- La colonna `price_history.currency` **resta** (come scritto, non veniva mai
  rimossa); cambia solo il fatto che il frontend non la legge più.
- Il vincolo al write diventa **hard reject (HTTP 400)** invece di per-item skip.
- Viene introdotto un nuovo **Blocco I** (currency simplification + banner cleanup +
  wipe-on-change + export prezzi) da eseguire PRIMA del Blocco G (test coverage), così
  che i test di G riflettano il design finale e non lo stato intermedio.
- I Blocchi A–H **non hanno ancora avuto test manuale funzionale** dall'utente: verrà
  eseguito DOPO il Blocco I su design consolidato, per evitare doppio giro di verifica
  su feature poi modificate.

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
| 21 | `backend/test_scripts/test_api/test_transfer_promotion.py` | **Nuovo** | H |

---

## 🔧 Blocchi di esecuzione

> Dopo ogni blocco: `./dev.py format && ./dev.py lint && ./dev.py test <scope>`.
> Dopo A–C (backend core): `./dev.py api sync && ./dev.py front check`.
> I blocchi con modifiche UI (D, E-frontend, F-frontend) richiedono **test manuale
> estetico dell'utente** prima di chiudere il blocco. L'agent deve fermarsi e chiedere conferma.

### Blocco A — Service refactor: atomic + broker-scoped  ✅ DONE (2026-04-20, commit `df6cdde0`)

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

### Blocco B — Router refactor: broker-scoped endpoints  ✅ DONE (2026-04-20, commit `df6cdde0`, fuso con A)

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

### Blocco C — `/validate` dry-run misto + `/events/suggest`  ✅ DONE (2026-04-20, commit `c3faae19`)

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

### Blocco D — i18n delete-events + mock data (deferred Part 1)  ✅ DONE (2026-04-20, commit `a7551fa3`)

> Nota: lo step 3 "🎨 Test manuale utente" nei 4 linguaggi resta aperto per la review UX
> finale; le chiavi e i toast sono in place.

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

### Blocco H — Transfer semantics + query extensions + promotion  🆕 (Dev-2026-04-21)

Raccoglie 4 osservazioni emerse in review post-commit D. Backend-only, nessun UI
cambia (lo sfrutteranno Part 4 e Part 5).

#### H.1 Validazione pairing: broker distinti + type coincidente

In `create_bulk` fase 2 (e analogamente in `validate_batch`), quando risolvo un
`link_uuid` con `len(pair) == 2`, aggiungo due check **prima** di settare
`related_transaction_id`:

```python
if pair[0].type != pair[1].type:
    error "linked pair must share the same type "
          f"(got {pair[0].type.value} + {pair[1].type.value})"
elif pair[0].type == TransactionType.TRANSFER and pair[0].broker_id == pair[1].broker_id:
    error "TRANSFER requires distinct brokers (both on broker X)"
# FX_CONVERSION intra-broker: consentito (multi-currency account)
# DEPOSIT/WITHDRAWAL intra-broker: consentito (serve per ADJUSTMENT di cassa)
else:
    pair[0].related_transaction_id = pair[1].id
    pair[1].related_transaction_id = pair[0].id
```

#### H.2 `link_uuid` facoltativo per DEPOSIT/WITHDRAWAL (soft relax)

Oggi `schemas/transactions.py` Rule 1 richiede `link_uuid` solo per TRANSFER e
FX_CONVERSION. Per DEPOSIT/WITHDRAWAL il campo esiste come opzionale ma è stato
silenziosamente ignorato dal pairing (se coppia DEPOSIT↔WITHDRAWAL arrivava con
stesso link_uuid, il service non linkava). Cambi:

- Validator: nessuna modifica richiesta (il campo era già `Optional[str]` con
  `max_length=36`; per TRANSFER/FX_CONVERSION resta obbligatorio via Rule 1).
- Service `create_bulk` fase 2: rimuovo il filtro implicito per tipo quando
  processo `link_uuid_map` — **ogni** coppia con 2 tx riceve il
  `related_transaction_id` bidirezionale, purché H.1 passi.
- Semantica: DEPOSIT + WITHDRAWAL linkate sono un *marker di intenzione*
  (bonifico tra i miei broker). Zero effetto su balance/PMC — è solo storytelling.

#### H.3 Estensione filtri `GET /transactions` (per match trasferimenti)

Tre nuovi filtri opzionali in `TXQueryParams` + handler router:

| Param | Tipo | Semantica |
|---|---|---|
| `amount_abs_min` | `Optional[Decimal]` | `ABS(Transaction.amount) >= N` |
| `amount_abs_max` | `Optional[Decimal]` | `ABS(Transaction.amount) <= N` |
| `only_unlinked` | `bool = False` | `Transaction.related_transaction_id IS NULL` |
| `exclude_ids` | `Optional[List[int]]` | `Transaction.id NOT IN (…)` |

`exclude_ids` va mantenuto disgiunto da `ids` (che è mutex con gli altri filtri):
se il client chiede `ids=…` ignoriamo `exclude_ids`. Gli altri tre convivono con
qualsiasi filtro esistente (broker_id, types, date_range, currency, tags…).

Uso tipico (pseudocode client-side):
```ts
// seed = DEPOSIT +500 EUR on broker A, 2026-03-15
const candidates = await api.query_transactions({
  types: ['WITHDRAWAL'],                // segno opposto = tipo opposto
  currency: 'EUR',
  amount_abs_min: 495, amount_abs_max: 505, // 1% tolerance
  date_start: '2026-03-12', date_end: '2026-03-18',
  only_unlinked: true,
  exclude_ids: [seed.id],
});
```

L'ordinamento rimane `date DESC, id DESC` (default di `query`). Il client ordina
ulteriormente per `abs(date - seed.date)` lato UI.

#### H.4 `POST /transactions/transfers/promote`

Endpoint dedicato per promuovere una coppia DEPOSIT/WITHDRAWAL a
TRANSFER (con asset) o FX_CONVERSION (cross-currency stesso broker).
Non si può fare via PATCH: `type` è immutable.

**Schemi nuovi** (`schemas/transactions.py`):

```python
class TXTransferPromoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_tx_id: int = Field(..., gt=0)
    to_tx_id:   int = Field(..., gt=0)
    new_type:   Literal[TransactionType.TRANSFER, TransactionType.FX_CONVERSION]
    # Richiesto se new_type == TRANSFER (cash -> asset transfer)
    asset_id:   Optional[int] = Field(None, gt=0)
    quantity:   Optional[Decimal] = None
    # Opzionale: override nuovi amount (per FX_CONVERSION i cash restano)
    # Se None, riusa from/to esistenti.

class TXTransferPromoteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rolled_back: bool
    new_from_tx_id: Optional[int] = None
    new_to_tx_id:   Optional[int] = None
    errors: List[str] = Field(default_factory=list)
```

**Service `promote_transfer(req, user_id)` — algoritmo**:

1. Load `from_tx = session.get(Transaction, req.from_tx_id)` + idem `to_tx`.
   None → errore, rolled_back=True.
2. Access check EDITOR su `{from_tx.broker_id, to_tx.broker_id}`.
3. Pre-check coerenza:
   - Tipi attuali: `from_tx.type` e `to_tx.type` devono essere
     `{DEPOSIT, WITHDRAWAL}` (due tipi cash sciolti) o `{BUY, SELL}` (già
     promoted equivalente? out-of-scope per ora).
   - Se `new_type == TRANSFER`: `req.asset_id` e `req.quantity` obbligatori,
     i due broker devono essere distinti (H.1).
   - Se `new_type == FX_CONVERSION`: `from_tx.currency != to_tx.currency`
     obbligato, stesso broker ammesso.
4. **Delete pair** via `delete_bulk([from_tx_id, to_tx_id])` — la pre-check
   linked-pair dell'attuale delete_bulk verifica già che eliminare entrambe
   non lascia dangling (se erano già linkate).
5. **Create pair** via `create_bulk([create_A, create_B])` con `link_uuid`
   generato, i nuovi campi `type`, eventuale `asset_id`/`quantity`, e
   `cost_basis_override` propagato per TRANSFER (se il from era su un asset
   con holding).
6. Atomicità: entrambi i passi condividono la stessa `session`, qualsiasi
   fallimento in step 5 → rollback e lo step 4 viene anch'esso annullato.
   → `rolled_back=True`, nuovi id `None`.
7. Commit nel router solo se entrambi gli step riescono.

Router:
```python
@tx_router.post("/transfers/promote", response_model=TXTransferPromoteResponse)
async def promote_transfer(
    req: TXTransferPromoteRequest,
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> TXTransferPromoteResponse:
    user_id = current_user.id
    service = TransactionService(session)
    response = await service.promote_transfer(req, user_id=user_id)
    if not response.rolled_back:
        await session.commit()
    else:
        await session.rollback()
    return response
```

#### H.5 Test (appendice a G)

Nuovi casi da aggiungere a `test_transaction_service.py`:
- `test_pairing_rejects_mixed_types_in_link_uuid`.
- `test_pairing_rejects_transfer_same_broker`.
- `test_pairing_allows_fx_conversion_same_broker`.
- `test_pairing_allows_deposit_withdrawal_linked`.

Nuovo file `test_transactions_api.py` (appendice):
- `test_query_filters_amount_abs_range`.
- `test_query_filters_only_unlinked`.
- `test_query_filters_exclude_ids`.
- `test_query_ids_overrides_exclude_ids`.

Nuovo file `test_transfer_promotion.py`:
- `test_promote_deposit_withdrawal_to_transfer_cross_broker`.
- `test_promote_deposit_withdrawal_to_fx_conversion_intra_broker`.
- `test_promote_rejects_transfer_same_broker`.
- `test_promote_rejects_fx_conversion_same_currency`.
- `test_promote_requires_editor_on_both_brokers`.
- `test_promote_atomicity_on_create_failure`.
- `test_promote_preserves_cost_basis_for_transfer`.

---

### Blocco E — Price currency coherence (deferred Part 1 §8)

> **📦 DETTAGLIATO IN**: [`plan-phase07-transaction-Part3_1_Closure.md`](./plan-phase07-transaction-Part3_1_Closure.md) §Decisioni terminali sul Blocco E.
>
> **Decisioni terminali** (post Q&A 2026-04-22, consolidate nel Closure plan):
> - **E.1** `original_currency` ✅ già implementato; `fx_error` ❌ cancellato dal design (scenari coperti da `requiredFxPairs` senza discriminator nel response).
> - **E.2** `currency_breakdown` ❌ cancellato (superseded da I.1).
> - **E.3** soft-skip upsert 🟡 **sostituito** da I.2 hard-400 reject — resta solo cleanup docstring/commenti residui.
> - **E.4** auto-registrazione FX pairs ❌ **cancellato** (design era sbagliato: viola principio self-hosted, UX già coperta da `requiredFxPairs` + `FxPairAddModal`).
> - **E.5/E.6/E.7** banner mismatch + FX-missing + data-editor warning ❌ cancellati (superseded da I.5/I.8).
> - **E.8** `query_events_bulk target_currency` + infobox FX-converted ⏳ **da fare ora** — dettaglio completo in Closure plan §Task E.8.
>
> Il testo originale sottostante viene conservato per **traccia storica del design originale**; fare riferimento al Closure plan per l'implementazione effettiva.

<details>
<summary>📜 Design originale E.1–E.8 (storico, superseded)</summary>

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

</details>

> **Stato comparativo & azioni follow-up** → migrati in [`plan-phase07-transaction-Part3_1_Closure.md`](./plan-phase07-transaction-Part3_1_Closure.md).

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

### Blocco I — Currency simplification + banner cleanup + wipe-on-change (Dev-2026-04-21)  🔨 IN PROGRESS (I.1–I.8 done, I.9–I.11 pending — 2026-04-21)

> **Stato al 2026-04-21 sera**: codice I.1–I.8 implementato e verde su
> format/lint/svelte-check/test api+services (asset-source, assets-price).
> Deviazione pragmatica adottata su **I.1**: `FAPricePoint.currency` non è stato
> rimosso dal modello ma reso `Optional[str]` (frontend non lo invia più e non lo
> legge; backend lo accetta assente e lo tratta come implicit = asset.currency).
> Rimosso invece completamente `CurrencyBreakdownEntry` + `currency_breakdown`
> dal response schema. I blocchi rimanenti (I.9 tests update, I.11 G-block
> extensions) sono ancora da fare.

> **Feedback funzionale 2026-04-22** — raccolti durante la checklist utente post-I.1–I.8.
> Applicati hotfix immediati (punti marcati ✅ qui sotto), il resto confluisce in
> un nuovo **Blocco I-bis** prima di andare al Blocco G.
>
> **Hotfix applicati in giornata (2026-04-22 mattina)**:
> - ✅ `ErasableNumberCell` commit bug: i valori digitati sparivano al blur perché
>   l'ordine `editing=false → onchange(n)` faceva partire il `$effect` con `value`
>   ancora stale. Riscritto: `onchange` → poi `editing=false`. Inoltre aggiunto
>   guard `if (draft !== desired)` prima di riscrivere per evitare write spuri.
> - ✅ `ErasableNumberCell` confirm dialog rimosso: il click sull'eraser imposta
>   direttamente la sentinel `-1` senza `window.confirm`. L'azione Revert di riga
>   copre i mistake accidentali. Stesso per il tasto `Delete`.
> - ✅ `ErasableNumberCell` gomma spostata a **sinistra** (absolute, opacity-0 fino
>   a hover/focus) per non sovrapporsi alle freccie su/giù dell'input number.
> - ✅ `ErasableNumberCell` placeholder: quando la cella è vuota non mostra più un
>   numero di esempio — solo l'etichetta italica "Not set" tradotta. Quando l'utente
>   va in focus la cella diventa bianca e accetta input normalmente.
> - ✅ Currency change modal: il body dice ora *"from {oldest} to today {today}"*
>   (prima usava `{newest}`, meno parlante in quel contesto perché il re-sync copre
>   fino a oggi, non fino all'ultima data salvata).
> - ✅ Dopo una currency change riuscita, `displayCurrency` viene forzato alla nuova
>   `asset.currency` dentro `handleAssetUpdated()` del +page.svelte → la selector
>   "Display currency" non resta più puntata alla vecchia valuta.
>
> **Da fare in Blocco I-bis** (non urgente ma necessario per UX completa):
> 1. **Provider vs asset currency mismatch post-wipe**: oggi se il provider restituisce
>    una currency diversa da quella nuova dell'asset, il sync post-wipe silenziosamente
>    non scrive righe (bulk_upsert_prices ora è hard-reject 400, ma l'errore non
>    risale fino al frontend in modo leggibile). Servono:
>    (a) toast di **errore esplicito** invece che il toast "Prices refreshed" al
>        termine quando il sync non ha inserito niente, con testo i18n tipo *"Post-wipe
>        sync produced 0 rows — provider currency may not match the new asset
>        currency. Update the provider or the asset currency."*;
>    (b) banner inline full-width sul detail page con lo stesso messaggio finché
>        l'utente non risolve (provider reassignment o currency rollback);
>    (c) valutare se il `POST /prices/sync` debba surface per-asset `{inserted,
>        errors[]}` per dare al frontend materiale da mostrare.
> 2. **"Save Without Testing?" modal gating**: oggi compare ad *ogni* save dell'asset,
>    anche se il provider non è stato toccato. Modifica: aprirlo solo se `providerCode`,
>    `providerIdentifier`, `providerIdentifierType` o `providerParams` differiscono
>    dallo stato caricato. Traccia il dirty-bit sul blocco provider separatamente e
>    gate il modal su quello.
> 3. **Tab label "Prices in {currency} {flag}"**: nella riga dei tab Prices/Events di
>    `AssetDataEditorSection` aggiungere a destra una piccola label che ricorda
>    all'utente la currency dell'asset (ISO3 + bandiera). Formato uniforme con il
>    resto della UI (utilizza `CurrencyInfo.flag_emoji` dal register `getCurrencyInfo`).
>    Nuova chiave i18n `dataEditor.pricesInCurrency` + variante events.
> 4. **Import CSV banner reminder**: in `PriceDataImportModal` aggiungere un
>    `InfoBanner` sopra il textarea che dice *"Currency must match asset
>    currency ({currency} {flag}). Extra columns in the CSV (like `currency`,
>    `source_plugin_key`, `fetched_at` from Export) are ignored on import."* Due
>    chiavi i18n: `import.csv.currencyReminder`, `import.csv.extraColumnsIgnored`.
> 5. **CSV Import resilience**: oggi `CsvEditor.svelte` richiede header esatto
>    (`date;Currency;Close;Open;High;Low;Volume` o simile, match stretto). Il CSV
>    generato da `/prices/export?format=csv` ha header `date,open,high,low,close,volume,currency,source_plugin_key,fetched_at`
>    (separatore `,`, colonne extra) → **non ri-importabile**. Modifiche:
>    (a) accetta sia `;` che `,` come separator (auto-detect dal first non-empty line);
>    (b) header match deve essere **tolerante alle extra-column**: ignora colonne
>        non mappate in `columns[].key`, ma richiede la presenza di tutte le required
>        (date + close);
>    (c) documentazione inline nel banner (punto 4 sopra).
> 6. **Empty-state "Add manually" button**: quando un asset non ha prezzi e il pannello
>    mostra solo "Sync from provider", aggiungere un secondo bottone "Add manually"
>    che apre l'edit panel pre-filtrato sul tab Prices con una riga vuota pronta.
>    Chiave i18n `assetDetail.addPricesManually`.
> 7. **Backend: patch_assets_bulk semantics**: feedback #2 evidenzia che il 409-style
>    blocker marker `CURRENCY_CHANGE_BLOCKED_BY_PRICES|...` passa attraverso il
>    `FAAssetPatchResult.message` ma il bulk endpoint ritorna sempre 200 anche per
>    fallimenti per-item. Da valutare se alzare l'HTTP status a 409 quando TUTTI gli
>    item del batch falliscono per quella ragione (senza rompere la multi-asset
>    semantic quando alcuni item passano). Non urgente.
>
> Tutti questi punti verranno raggruppati sotto "Blocco I-bis" (sezione da aggiungere
> qui sotto dopo la checklist utente su questa seconda iterazione di hotfix).

> **Seconda iterazione test manuale 2026-04-22 pomeriggio** — verifica hotfix mattina.
>
> ✅ **Confermati OK**:
> 1. *ErasableNumberCell commit* — digitare valore in cella "Not set" → click fuori →
>    il valore **resta** (bug commit risolto). Piccola nota UX **positiva**: dopo il
>    commit la cella ora è evidenziata in rosso (stato "dirty"), mentre le altre
>    restano grigie → feedback visivo coerente. Riaprendo e chiudendo il focus torna
>    grigia normale.
> 2. *Eraser click senza confirm dialog* — click gomma su cella con valore →
>    cleared immediato, nessun `window.confirm`. ✅
> 3. *Eraser posizione* — l'icona compare a sinistra su hover, non sovrapposta alle
>    frecce su/giù del `<input type=number>`. ✅
> 4. *Placeholder italico* — celle "Not set" mostrano solo etichetta italic grigia,
>    nessun numero di esempio fantasma. ✅
> 5. *Currency change modal* — body mostra la data corretta "da {oldest} a oggi {today}".
>    ⚠️ **Richiesta UX di affinamento**: l'utente preferirebbe il testo **senza** le
>    due date esplicite, solo "fino a oggi" (es. *"verranno cancellati 31 record di
>    prezzo fino ad oggi"*). Le date verbose sono rumore, conta solo il totale + il
>    fatto che arriva a oggi. Azione: semplificare la stringa i18n
>    `assetDetail.currencyChange.body` rimuovendo placeholder `{oldestDate}`, e
>    valutare se `{newestDate}` ha ancora senso. Se proprio servono, spostarle in un
>    tooltip o in small-font secondario. ✅ tracciato per I-bis #8.
> 6. *Display currency auto-switch post-change* — dopo USD→EUR la selector
>    "Display currency" si riposiziona su EUR. ✅
> 7. *Toast sequence currency change* — sequenza leggibile: "Cancellazione di 31
>    record…" → "Aggiornamento valuta asset…" → "Ri-sincronizzazione prezzi da
>    2026-03-23…" → "Valuta cambiata da USD a EUR. Prezzi aggiornati." → "Bitcoin
>    aggiornato con successo". ✅ (Provider yfinance per Bitcoin ha accettato EUR,
>    quindi il caso "0 righe inserite" del punto #1 I-bis non si è riprodotto qui —
>    resta da validare con un asset in cui il provider forza una currency non
>    allineata.)
> 8. *F.3 current-price auto-extend* — confermato dai log JSON (`[F.3 extend]
>    asset=8 date=2026-04-22 new_close=78217.46 patch_fields=['close']`, e un
>    secondo evento con `patch_fields=['low', 'close']` quando il nuovo close è
>    sotto il minimo esistente). Il min/max intra-day si estende correttamente, il
>    campo `open` viene mantenuto, e il persist commit va a buon fine (1 riga
>    written/updated). Feature **VALIDATA** in produzione. ✅
>
> 🐞 **Nuove regressioni scoperte** (da aggiungere a Blocco I-bis):
> 9. **Dirty detection rotta per OHLCV non-close**: caso riprodotto su asset
>    manuale con alcune celle "Not set":
>    - L'utente imposta `close=0.07` in una cella vuota → Save abilitato → click Save → POST
>      `/assets/prices` con body `[{"asset_id":38,"prices":[{"date":"2026-04-22","close":0.07}]}]`
>      → 200 OK, `inserted_count:1`.
>    - Riapre l'edit panel: il valore 0.07 **non compare**, la cella mostra di
>      nuovo "Not set", e le altre OHLCV restano "Not set".
>    - Se ora modifica `open`/`high`/`low`/`volume` direttamente (digitando un
>      numero), **il bottone Save NON si abilita** → la dirty detection ignora
>      gli edit diretti sui campi non-close.
>    - Viceversa: asset con righe tutte piene, click gomma → value scompare →
>      click Restore → value ritorna → Save **si abilita** correttamente → POST
>      con `"open":-1` nel payload → 200 OK → al reload del pannello la cella
>      risulta "Non impostato" (sentinel `-1` → NULL a DB → placeholder a UI) ✅.
>    - Ma: sullo stesso asset, se a questo punto l'utente prova a inserire un
>      valore nuovo in una cella "Not set" (es. scrivere `0.5` in open), **Save
>      resta disabilitato**. Solo la gomma (→ sentinel `-1`) produce dirty.
>    - **Ipotesi**: l'`onchange` di `ErasableNumberCell` nel caso
>      `value===null && draft!==null` (cioè passa da "non impostato" a "impostato")
>      probabilmente non propaga il change verso `DataEditor`'s dirty tracker —
>      o il tracker confronta `null === undefined` in modo che ignori il delta.
>      Stessa ipotesi per la re-lettura post-save: il backend ritorna `open/high
>      /low/close/volume` eventualmente `null`, il diff riga originale/corrente
>      vede tutte null→null e conclude "unchanged" invece di rimontare il draft.
>    - Gravità: **bloccante** per l'editing manuale multi-campo. Priorità alta
>      nel I-bis (punto 9).
> 10. **Post-save: il valore salvato non è visibile al reload del pannello**
>     (probabile regressione collegata al punto 9): salvando `close=0.07` su una
>     cella "Not set", la response 200 è corretta, ma riaprendo l'edit panel il
>     valore non è mostrato. Serve verifica se:
>     (a) il GET prezzi post-save include la riga appena inserita (controllare
>         network log `/prices` response body);
>     (b) il mapping response→form state di `AssetDataEditorSection` droppa le
>         righe con `date == today` perché si scontrano con una logica di merge
>         della `current-price`;
>     (c) il `$effect` di rehydration del DataEditor confronta timestamp stale.
>     Azione: aggiungere `console.debug` temporanei sull'hydrate e reinvocare
>     il save per isolare il path.
>
> Questi due punti (9, 10) diventano **I-bis #8, #9, #10** nella lista sotto.
> Vanno risolti prima di dichiarare Blocco I "funzionalmente validato".

> **Ordine**: da eseguire **PRIMA del Blocco G**, così che la test coverage di G
> rifletta il design finale. Supersedes parziale di E.2, E.3, E.5, E.7, E.8 e parte
> di E.6. Rationale completo vedi deviazione Dev-2026-04-21 sopra.

#### I.1 Backend — API response cleanup
- `FAPricePoint.currency` → **rimosso** dallo schema response (restano open/high/low/close/volume/date/original_*).
- `FAPriceQueryResult.currency_breakdown` + classe `CurrencyBreakdownEntry` → **rimossi** (Supersedes E.2).
- Pass di popolamento `currency_breakdown` in `get_prices_bulk` → **rimosso**.
- `fx_error` discriminator su `AssetBackwardFillInfo` → **mantenuto** (backend log/debug), anche senza consumer frontend. Nessun cambio.

#### I.2 Backend — Hard reject su mismatch (Supersedes E.3)
- `bulk_upsert_prices`: se anche una sola riga del payload ha `currency != asset.currency` → **HTTP 400** con body `{detail: "Currency mismatch", asset_currency, offending_dates: [...]}`. No più per-item skip silenzioso.
- Il frontend, con colonna currency rimossa dal DataEditor (vedi I.5), non può più far arrivare mismatch qui → questo è defensive/forensic.

#### I.3 Backend — PATCH asset rifiuta currency change su asset con prezzi
- L'attuale endpoint `PATCH /api/v1/assets/{asset_id}` (o equivalente):
  - Se `patch.currency` è presente **e** `patch.currency != current.currency` **e** esistono righe in `price_history` per quell'asset → **HTTP 409** con body `{detail: "Asset has N price records. Delete them before changing currency.", existing_count: N, oldest_date: YYYY-MM-DD, newest_date: YYYY-MM-DD}`.
  - Altrimenti (zero prezzi o stessa currency) → procede normalmente.
- **Nessun nuovo endpoint dedicato**: l'orchestrazione "delete → patch → re-sync" vive lato frontend (vedi I.6). Backend espone solo i mattoni esistenti: `DELETE /assets/{id}/prices/bulk`, `PATCH /assets/{id}`, `POST /assets/prices/sync/bulk`.

#### I.4 Backend — Export prezzi con formato parametrico
- **Nuovo endpoint** `GET /api/v1/assets/{asset_id}/prices/export?format={json|csv}`:
  - `format=csv` (default): `Content-Type: text/csv`, filename `prices_{asset_slug}_{YYYY-MM-DD}.{format}`, colonne `date, open, high, low, close, volume, currency, source_plugin_key, fetched_at` (currency da DB come canary; include tutto per backup "completo").
  - `format=json`: `Content-Type: application/json`, body `{asset_id, currency, prices: [...]}`, stesso contenuto per riga.
  - Formati futuri (excel, parquet, ecc.) aggiungibili senza rompere l'API. Enum Pydantic su `format` per validation.
  - Streaming response se dataset > 10k righe (StreamingResponse con generator).
- **Auth**: stesse regole di query prezzi (owner asset o accesso broker).

#### I.5 Frontend — Banner cleanup
- `AssetPriceSummary.svelte`:
  - **Rimuovi** i prop `fxConversionMissing`, `fxPairSlug`, `onAddFxPair`, `onsyncfx`, `fxSyncing` (banner #5 + bottone #6 — duplicavano `requiredFxPairs`).
  - **Rimuovi** i prop `currencyBreakdown`, `onNormalizeCurrency`, `onIgnoreCurrencyMismatch` (banner #7 E.5).
  - **Mantieni** `livePriceConversionFailed` (banner #4 — caso "oggi manca FX rate", semanticamente distinto da #3).
- `+page.svelte`:
  - **Rimuovi** state `currencyBreakdown`, `currencyMismatchDismissed`.
  - **Rimuovi** prop passati a AssetPriceSummary (solo lastPrice, delta*, displayCurrency, assetCurrency, layoutMode, livePriceConversionFailed restano).
- `AssetDataEditorSection.svelte`:
  - **Rimuovi** prop `assetCurrency` e la derivazione `mismatchedPriceRows` / `mismatchedCurrenciesLabel` + banner warning sopra tabella (Supersedes E.7).
  - **Rimuovi** colonna `currency` da `priceColumns` (asset.currency inferita lato backend — il save non invia più il campo currency nel payload).
  - **Rimuovi** `defaultRowValues={{currency: assetCurrency}}` passato a `DataEditor`.
- `DataEditor.svelte`:
  - Mantieni il prop `defaultRowValues` come feature generica (utile per altri use case futuri). Nessun breaking change.
- Conseguenza del save path: `FAPricePoint` inviato non contiene più `currency`, backend la deriva da asset. Se un utente importa un CSV con una colonna `currency` diversa → backend reject con 400 (I.2).

#### I.6 Frontend — Flow cambio currency (wipe + re-sync)
Nuovo componente `AssetCurrencyChangeModal.svelte` (o estensione di `AssetDetailsModal`):

**Trigger**: utente cambia il campo currency nell'edit asset → submit PATCH.

**Step 1**: backend risponde 409 → frontend apre il modal.

**Contenuto modal**:
- **Header**: icona ⚠️ rossa + titolo `assetDetail.currencyChange.title` ("Change currency — destructive action").
- **Body**:
  - Riga 1: `assetDetail.currencyChange.body` con placeholders — "Changing currency from **{oldCurrency}** to **{newCurrency}** will permanently delete **{count}** price records (from **{oldestDate}** to **{newestDate}**)".
  - Riga 2 (info): "After wipe, prices will be auto-synced from provider starting from {oldestDate}". Se l'asset non ha provider assignment, messaggio alternativo: "No provider assigned — you will need to re-import prices manually".
- **Sezione backup**:
  - Bottone secondario "📥 Export current prices as CSV" → `GET /prices/export?format=csv` (blob download).
  - Bottone secondario "📥 Export as JSON" (minore visibilità) → `format=json`.
- **Azioni**:
  - "Cancel" (grigio, default focus) → chiude il modal, currency torna al valore precedente.
  - "Delete & Change Currency" (rosso, destructive) → esegue la sequenza Step 2.

**Step 2** (al click del bottone rosso):
1. `DELETE /assets/{id}/prices/bulk` con `date_ranges: [{start: oldestDate, end: newestDate}]` → aspetta 200.
2. `PATCH /assets/{id}` con `currency: newCurrency` → aspetta 200 (ora non trova più prezzi, accetta il cambio).
3. Se l'asset ha provider assignment: `POST /assets/prices/sync/bulk` con `{asset_id, date_range: {start: oldestDate, end: today}}`.
4. Toast di progresso tra gli step: "Deleting prices..." → "Updating currency..." → "Re-syncing from provider..." → "Done".
5. Error handling: se uno step fallisce, mostra toast error con dettaglio. La sequenza NON è transazionale tra endpoint distinti (il backend non espone una transaction multi-endpoint) → in caso di fallimento dopo il DELETE, l'asset resta in stato degradato (zero prezzi, currency vecchia o nuova a seconda di dove è fallito). Refresh manuale resuscita lo stato visibile.
6. Al termine: `invalidate()` route SvelteKit + reload pagina asset.

**Nota concurrency**: il modal non previene race condition con sync in background. Mitigazione: disabilita il pulsante "Sync" in toolbar per tutta la durata della sequenza wipe+resync.

#### I.7 Frontend — i18n
- **Rimuovi** (dead keys post I.5):
  - `prices.currencyMismatch.{title,body,normalize,ignore}` × 4 lingue = 16 righe.
  - `prices.fxMissing.{pairMissing,noRateAtDate,addPair,syncHistory}` × 4 lingue = 16 righe.
  - `dataEditor.warning.currencyMismatch` × 4 = 4 righe.
- **Aggiungi** (per I.6):
  - `assetDetail.currencyChange.title` — "Change currency" / "Cambia valuta" / "Changer de devise" / "Cambiar divisa".
  - `assetDetail.currencyChange.body` — "Changing currency from {oldCurrency} to {newCurrency} will permanently delete {count} price records (from {oldestDate} to {newestDate})" + tre traduzioni.
  - `assetDetail.currencyChange.autoSyncInfo` — "After wipe, prices will be auto-synced from provider starting from {oldestDate}".
  - `assetDetail.currencyChange.noProviderInfo` — "No provider assigned — you will need to re-import prices manually".
  - `assetDetail.currencyChange.exportCsv` — "Export current prices as CSV".
  - `assetDetail.currencyChange.exportJson` — "Export as JSON".
  - `assetDetail.currencyChange.cancel` — "Cancel".
  - `assetDetail.currencyChange.confirm` — "Delete & Change Currency".
  - `assetDetail.currencyChange.progress.{delete,patch,sync,done}` — 4 stringhe di toast progresso × 4 lingue.
  - Totale ~40 nuove traduzioni.
- Usa batch `./dev.py i18n add` per ogni chiave.

#### I.8 Frontend — DataEditor prezzi: currency column rimossa
- In `AssetDataEditorSection`, `priceColumns` non contiene più il key `currency`.
- Il save path `handleSave` non invia più `currency` nei `priceItems` (backend la deriva).
- Il CSV import modal: se CSV ha colonna `currency`, il parser la **ignora** (non la passa come value). Eventuale nota i18n "CSV currency column is ignored — asset currency is used" in PriceDataImportModal (opzionale).

#### I.9 Backend — Test adaptations
- `test_assets_price.py`:
  - Test su upsert con currency mismatch → ora aspetta **400 hard** (prima era 200 con `errors: [...]`).
  - Rimuovi test su `currency_breakdown` / `CurrencyBreakdownEntry`.
- `test_asset_currency_change.py` (nuovo, vedi G.10 sotto).
- `test_asset_prices_export.py` (nuovo, vedi G.11 sotto).

#### I.10 Validazione finale Blocco I
```bash
./dev.py format && ./dev.py lint
./dev.py api sync && ./dev.py front check
./dev.py test api assets-price
./dev.py test api assets-currency-change
./dev.py test api assets-prices-export
```

Poi procedi con **Blocco G** (test coverage allineato al design post-I) e infine la
checklist funzionale utente.

#### I.11 Estensioni a Blocco G
Aggiungere a G.5 `test_prices_currency_coherence.py` (rimpiazzando i test dead):
- **Rimuovi** `test_currency_breakdown_*` e `test_normalize_endpoint_converts_dissonant_points`.
- **Modifica** `test_upsert_rejects_currency_mismatch_via_errors` → `test_upsert_rejects_currency_mismatch_hard_400`.

Aggiungere nuovo file `test_asset_currency_change.py` (G.10):
- `test_patch_currency_same_value_noop` (200, no side effect).
- `test_patch_currency_without_prices_succeeds` (200, asset.currency aggiornata).
- `test_patch_currency_with_prices_rejects_409` (409 con `existing_count`, `oldest_date`, `newest_date`).
- `test_patch_currency_after_delete_prices_succeeds` (flow completo: DELETE → PATCH → verify).
- `test_patch_currency_invalid_code_400`.

Aggiungere nuovo file `test_asset_prices_export.py` (G.11):
- `test_export_csv_format_default`.
- `test_export_csv_contains_all_columns`.
- `test_export_json_format`.
- `test_export_invalid_format_400`.
- `test_export_empty_prices_returns_header_only`.
- `test_export_requires_asset_access`.
- `test_export_large_dataset_streaming` (>10k rows, verify streaming response).

Aggiungere a G.7 `scripts/test_runner.py`:
- `api/assets-currency-change`
- `api/assets-prices-export`

---

### Blocco I-bis — Hotfix & UX follow-up (Dev-2026-04-22)  🔨 IN PROGRESS

> Raccoglie i punti emersi nei due giri di test manuale del 2026-04-22 (mattina
> + pomeriggio) post implementazione I.1–I.8. I 7 hotfix mattutini sono già
> applicati inline (vedi callout sopra). I restanti 10 punti qui sotto sono la
> coda pendente, ordinata per priorità.

#### I-bis #9 — Dirty detection rotta per OHLCV erasable (BLOCCANTE)  ✅ FIXED (2026-04-22 sera)

**Sintomo**: digitando un numero in una cella `ErasableNumberCell` "Not set"
(open/high/low/volume), Save NON si abilita. Il bug NON si verifica per `close`
(che usa il path `editable-number`) né per la gomma (che manda sentinel `-1`).

**Root cause identificata** (2026-04-22 sera): `ErasableNumberCell.svelte` aveva
`let draft = $state('')` (stringa), ma l'input è
`<input type="number" bind:value={draft}>`. Svelte 5 **coerce automaticamente**
`bind:value` su `type=number` a `number | null`. Appena l'utente digitava,
`draft` diventava un numero → `draft.trim()` in `commit()` lanciava
`TypeError: draft.trim is not a function` silenziosamente → `onchange` mai
emesso → dirty tracker mai informato.

**Fix applicato** (commit pending):
- `draft` ridichiarato come `$state<number | null>(null)`.
- `$effect` aggiornato: `desired = value == null || value === -1 ? null : value`.
- `commit()` rimosso `.trim()`, gestisce direttamente `number | null | NaN`.
- `handleEraseClick()` / `handleKeyDown()` / click handler "cleared" allineati
  al nuovo tipo (`draft = null` invece di `''`).
- Aggiunto commento esteso sul perché della scelta, per evitare regressioni.

**Verifica**: `./dev.py front check` verde (0 errors, 0 warnings). Test manuale
utente pendente (serve retest #9 + #10 sullo stesso flusso).

#### I-bis #10 — Post-save: valore appena salvato non visibile al reload  ✅ FIXED (2026-04-22 sera, risolto con fix #9)

**Retest post-fix #9** (2026-04-22 sera): payload save
`[{asset_id:16, prices:[{date:"2026-04-22", close:89.52, open:89.52, high:89.65, low:-1}]}]`
→ response `{success_count:1, inserted_count:1}`. Riaprendo l'edit panel il
backend restituisce correttamente la riga con open=89.52, high=89.65,
low=null, close=89.52, volume=null e le celle mostrano i valori (incluse
"Not set" per le null). **Il Restore funziona**.

Il bug #10 era quindi un **sintomo** di #9: il dirty tracker cieco faceva sì
che il payload arrivasse al backend con soli campi "forzati" (es. close
tramite keydown manuale sul save button), quindi la riga risultava salvata
ma con un solo campo → l'utente leggeva come "nulla salvato". Fixando #9 la
catena save → GET → display si è riallineata.

#### I-bis #1 — Post-wipe sync produces 0 rows: surfacing errore

Oggi se il provider restituisce una currency diversa da quella nuova
dell'asset, il sync post-wipe silenziosamente non scrive righe
(`bulk_upsert_prices` ora è hard-reject 400, ma l'errore non risale fino al
frontend in modo leggibile). Servono:
- (a) toast di **errore esplicito** invece che il toast "Prices refreshed" al
  termine quando il sync non ha inserito niente, con testo i18n tipo
  *"Post-wipe sync produced 0 rows — provider currency may not match the
  new asset currency. Update the provider or the asset currency."*;
- (b) banner inline full-width sul detail page con lo stesso messaggio finché
  l'utente non risolve (provider reassignment o currency rollback);
- (c) valutare se il `POST /prices/sync` debba surface per-asset
  `{inserted, errors[]}` per dare al frontend materiale da mostrare.

#### I-bis #2 — "Save Without Testing?" modal gating

Oggi compare ad *ogni* save dell'asset, anche se il provider non è stato
toccato. Modifica: aprirlo solo se `providerCode`, `providerIdentifier`,
`providerIdentifierType` o `providerParams` differiscono dallo stato caricato.
Traccia il dirty-bit sul blocco provider separatamente e gate il modal su
quello.

#### I-bis #3 — Tab label "Prices in {currency} {flag}"

Nella riga dei tab Prices/Events di `AssetDataEditorSection` aggiungere a
destra una piccola label che ricorda all'utente la currency dell'asset (ISO3 +
bandiera). Formato uniforme con il resto della UI (utilizza
`CurrencyInfo.flag_emoji` dal register `getCurrencyInfo`). Nuova chiave i18n
`dataEditor.pricesInCurrency` + variante events.

#### I-bis #4 — Import CSV banner reminder

In `PriceDataImportModal` aggiungere un `InfoBanner` sopra il textarea che
dice *"Currency must match asset currency ({currency} {flag}). Extra columns
in the CSV (like `currency`, `source_plugin_key`, `fetched_at` from Export)
are ignored on import."* Due chiavi i18n: `import.csv.currencyReminder`,
`import.csv.extraColumnsIgnored`.

#### I-bis #5 — CSV Import resilience

Oggi `CsvEditor.svelte` richiede header esatto (separatore stretto, match
stretto). Il CSV generato da `/prices/export?format=csv` ha header
`date,open,high,low,close,volume,currency,source_plugin_key,fetched_at`
(separatore `,`, colonne extra) → **non ri-importabile**. Modifiche:
- (a) accetta sia `;` che `,` come separator (auto-detect dal first non-empty
  line);
- (b) header match deve essere **tolerante alle extra-column**: ignora
  colonne non mappate in `columns[].key`, ma richiede la presenza di tutte
  le required (date + close);
- (c) documentazione inline nel banner (punto #4 sopra).

#### I-bis #6 — Empty-state "Add manually" button

Quando un asset non ha prezzi e il pannello mostra solo "Sync from provider",
aggiungere un secondo bottone "Add manually" che apre l'edit panel
pre-filtrato sul tab Prices con una riga vuota pronta. Chiave i18n
`assetDetail.addPricesManually`.

#### I-bis #7 — Backend: `patch_assets_bulk` HTTP semantics

Il 409-style blocker marker `CURRENCY_CHANGE_BLOCKED_BY_PRICES|...` passa
attraverso il `FAAssetPatchResult.message` ma il bulk endpoint ritorna sempre
200 anche per fallimenti per-item. Da valutare se alzare l'HTTP status a 409
quando TUTTI gli item del batch falliscono per quella ragione (senza rompere
la multi-asset semantic quando alcuni item passano). Non urgente.

#### I-bis #8 — Currency change modal body semplificato  ✅ FIXED (2026-04-22 sera)

Feedback UX: le due date esplicite nel body (`from {oldest} to today {today}`)
sono rumore. L'utente preferisce solo "fino a oggi".

**Fix applicato**: rimossi i placeholder `{oldest}` e `{today}` dal body in
tutte e 4 le lingue (en/it/fr/es). Nuovo testo:
- EN: "...will permanently delete {count} price records up to today. Prices
  will be re-fetched..."
- IT: "...verranno eliminati permanentemente {count} record di prezzo fino
  ad oggi. I prezzi verranno..."
- FR: "...supprimera définitivement {count} enregistrements de prix jusqu'à
  aujourd'hui. Les prix seront..."
- ES: "...eliminará permanentemente {count} registros de precio hasta hoy.
  Los precios se volverán a..."

I placeholder non più referenziati nel template vengono ignorati silently
dalla libreria i18n → nessun impatto sul chiamante (il componente continua a
passare `values={from,to,count,oldest,today}` ma sono no-op).

#### I-bis #11 — `autoSyncInfo` dentro InfoBanner nel currency change modal  ✅ FIXED (2026-04-22 sera)

**Fix applicato** in `AssetCurrencyChangeModal.svelte`:
- Import `InfoBanner` da `$lib/components/ui/InfoBanner.svelte`.
- Le due righe `autoSyncInfo` / `noProviderInfo` wrappate rispettivamente in
  `<InfoBanner variant="info">` e `<InfoBanner variant="warning">`.
- Nessuna modifica i18n (riusate le chiavi esistenti).

Verifica: `./dev.py front check` → 0 errors.

#### I-bis #12 — Currency change: troppi toast in sequenza (UX noise)

Feedback: durante il flusso currency change compaiono 5 toast in sequenza:
1. "Deleting 2 price records…"
2. "Updating asset currency…"
3. "Re-syncing prices from 2026-04-21…"
4. "Currency changed from EUR to USD. Prices refreshed."
5. "'Amundi Prime Global UCITS ETF' updated successfully"

I primi 3 sono rumore (progress intermedio), il #4 è il messaggio finale
utile, il #5 è ridondante con il #4 (emesso dal flusso generico di edit
asset post-PATCH).

**Design proposto**:
- Sostituire i 3 toast di progress con **un unico toast "loading"** (o
  spinner inline nel modal) che si chiude alla fine.
- Mostrare solo il toast finale "Currency changed from X to Y. Prices
  refreshed.".
- Sopprimere il toast generico "`{name}` updated successfully" quando la
  PATCH asset è avvenuta via currency-change flow (flag interno al
  chiamante).

⏳ Pending (richiede refactor di 2-3 punti del flusso) — non urgente.

#### I-bis #13 — Mock data: asset configurati male in `populate_mock_data.py`  ✅ FIXED COMPLETE (2026-04-22 sera tardi)

Feedback dettagliato sui mock asset (correggere in
`backend/test_scripts/test_db/populate_mock_data.py`):

1. ✅ **"Amundi Prime Global UCITS ETF"** → rinominato a **"Amundi MSCI
   Semiconductors UCITS ETF Acc"**, aggiunto `identifier_isin=LU1900066033`
   + `identifier_ticker=CHIP`, descrizione aggiornata ("Semiconductors
   sector ETF…"). ISIN nel provider config era già corretto.

2. ✅ **"Amundi MSCI World UCITS ETF"** → rinominato a **"Amundi Core MSCI
   World UCITS ETF Acc"**, aggiunto `identifier_isin=IE000BI8OT95` +
   `identifier_ticker=MWRD`, **provider cambiato da yfinance a justetf**
   con `IdentifierType.ISIN`.

3. ✅ **"BTP Italia 2028"** (2026-04-22 sera tardi): la "malformazione" NON
   era nella config del mock — era il bug Pydantic #21 che faceva fallire
   la GET `/provider/assignments` con 500, inducendo il frontend a mostrare
   "provider disattivato" come fallback UI. L'utente ha confermato via
   `/provider/probe` che la config produce correttamente 10000 EUR flat con
   maturation semi-annuale. Aggiornato il mock:
   `initial_value.amount: 1000 → 10000` (un singolo taglio BTP realistico)
   + commento esteso che linka a #21.

4. ✅ **"BTP Italia 2034 (Borsa Italiana)"** → rinominato a **"BTP Più Sc
   Fb33 EUR"** (display_name + classification description).

5. ✅ **"Gold Spot Price"**: CSS selector aggiornato al deep selector
   fornito dall'utente (catturato da Kitco live gold page 2026-04-22).
   Commento inline che spiega il cambio (il vecchio `#sp-last` non
   esiste più sulla pagina corrente).

6. ✅ **"Vanguard FTSE All-World UCITS ETF"** e **"iShares Core S&P 500
   UCITS ETF"** **RIMOSSI** (2026-04-22 sera tardi, su richiesta utente
   "dedica il tempo necessario, non tanti punti"):
   - Definizioni asset: eliminate (sostituite da commento di trail con
     data + rationale).
   - Provider assignments: rimossi i 2 tuple `yfinance` correlati.
   - `populate_transactions`: rimossi i 4 transaction items (+ i locals
     `vwce`/`cspx`).
   - `populate_price_history`: rimossi i 2 price_configs + locals.
   - `populate_asset_events`: rimosso il blocco VWCE dividends.
   - Verifica: `python ast.parse`, `./dev.py format/lint/front check` tutti
     verdi. `grep vwce|cspx|Vanguard|iShares` → solo commenti di trail.

7. ✅ **"Real Estate Loan - Milano Centro"** → rinominato a **"RE Loan
   Milano"** + aggiunto `active: False` (fixture per testare stato
   asset inattivo). **"Real Estate Loan - Roma Parioli"** → rinominato
   a **"RE Loan Roma"**. Aggiornate anche tutte le 4 occorrenze negli
   `select()` dei populate_transactions/populate_events.

Verifica globale: `./dev.py format && lint && front check` → tutti verdi.

#### I-bis #14 — Frontend: asset type badge mostra icona sbagliata per tipo INDEX  ✅ FIXED (2026-04-22 sera)

**Root cause confermata**: `PNG_MAP` / `ASSET_TYPE_ICON_MAP` / `TYPE_ICON_MAP`
in 4 file diversi (`lib/utils/assetTypes.ts`, `lib/utils/icons.ts`,
`lib/components/assets/AssetCard.svelte`,
`lib/components/charts/ChartSignalsSection.svelte`, `routes/(app)/assets/+page.svelte`)
non avevano entry per `INDEX` → caduta sul fallback `other.png`.

**Fix applicato**:
- Aggiunta entry `INDEX: 'index'` in tutti i 5 siti + aggiunto
  `'INDEX'` a `ALL_ASSET_TYPES` nel filtro dropdown.
- Creato `frontend/static/icons/asset-types/index.png` come **placeholder
  iniziale** (copia di `stock.png`). TODO: sostituire con un'icona
  dedicata (tipo "chart-line" o "trending-up") in un followup grafico.

Verifica: `./dev.py front check` → 0 errors.

#### I-bis #15 — Metadata & Classification: aggiungere descrizione asset in cima  ✅ FIXED (2026-04-22 sera)

Campo originario identificato: **`classification_params.short_description`**
(non è un field diretto di `Asset`, ma nested nella JSON `classification_params`).
Già letto in `AssetModal` come `shortDescription`.

**Fix applicato** in `frontend/src/routes/(app)/assets/[id]/+page.svelte`:
- Nuovo `$state` `shortDescription: string | null`.
- Popolato in `loadClassificationData` (`cp.short_description ?? null`).
- Reset in tutti i punti dove si resettano gli altri field classification
  (init, loadClassification failure path, has_metadata=false path).
- Renderizzata come **prima sezione** del pannello `Metadata &
  Classification`: heading uppercase + `<p>` con `whitespace-pre-wrap
  leading-relaxed`. Nascosta se vuota (no empty state).
- Nuova chiave i18n `assetDetail.metadataDescription` in EN/IT/FR/ES
  ("Description" / "Descrizione" / "Description" / "Descripción").
  Collisione evitata: `assetDetail.metadata` era già una stringa scalare,
  non un oggetto — quindi non si poteva usare `metadata.description`.

Verifica: `./dev.py front check` → 0 errors.

#### I-bis #16 — Cleanup icone asset: rimuovere force-INDEX→SVG + elimina `icons.ts` dead code  ✅ FIXED (2026-04-22 tardi)

Il feedback utente ha evidenziato due problemi:
1. Nel `AssetIcon.svelte` c'era un force di fallback sul lucide `BarChart3` per
   `assetType === 'INDEX'` (legacy, quando non esisteva `index.png`).
2. `frontend/src/lib/utils/icons.ts` conteneva due const (`ASSET_TYPE_ICONS`,
   `TRANSACTION_ICONS`) + due funzioni (`getAssetTypeIcon`, `getTransactionIcon`)
   **completamente inutilizzate**. Il codice è stato sostituito tempo fa da
   `assetTypes.ts::getAssetTypeIconUrl` + i `*_ICON_MAP` inline nei componenti.

**Fix applicato**:
- `AssetIcon.svelte:37`: rimosso `&& assetType !== 'INDEX'` dal derived
  `pngSrc`. Ora INDEX riceve l'icona `/icons/asset-types/index.png` come
  tutti gli altri tipi.
- **Eliminato** `frontend/src/lib/utils/icons.ts` (dead code, 0 import nel
  codebase).

L'utente ha fornito un'icona `index.png` dedicata — il placeholder creato
nello step precedente (#14) non serve più, andrà sovrascritto dall'asset
dell'utente.

#### I-bis #17 — Filtro "Active Only / Show All" rotto + semantica del campo `Asset.active`  ✅ FIXED (2026-04-22 tardi)

**Sintomo**: toggle "active only" sulla pagina assets non mostra gli asset
inattivi quando switchato su "show all". RE Loan Milano (marcato `active=False`)
rimaneva invisibile indipendentemente dallo stato del toggle.

**Root cause**: l'endpoint `GET /api/v1/assets/query` aveva
`active: bool = Query(True)` come default → filtro applicato server-side a
livello di query SQL. Gli asset inattivi non arrivavano mai al frontend,
quindi il toggle client-side `filterActiveOnly && !a.active` non aveva nulla
da filtrare.

**Fix applicato** (tri-state):
- `FAAinfoFiltersRequest.active`: da `bool = Field(True)` → `Optional[bool] = Field(None)`.
  Semantica: `None` = no filter (return both), `True` = only active,
  `False` = only inactive.
- `AssetCRUDService.list_assets`: `conditions.append(Asset.active == filters.active)`
  → wrapped in `if filters.active is not None`.
- API `/query`: `active: Optional[bool] = Query(None)` con description
  aggiornata.
- L'altro endpoint `/assets/all` (usato da BRIM) continua a passare
  `active=True` esplicito → comportamento invariato per quel use-case.
- Rigenerato client TypeScript via `./dev.py api sync`.

Il frontend `list_assets_api_v1_assets_query_get({queries: {}})` ora ottiene
ENTRAMBI attivi e inattivi; il toggle in `+page.svelte` filtra client-side
(logica `filterActiveOnly && !a.active` era già corretta).

**Risposta alla domanda "a cosa serve Asset.active oggi?"**:
Il campo è al momento **quasi puramente cosmetico**. L'analisi di tutti i
callsite (`grep Asset.active | asset.active`) mostra che è usato solo in:
- Il filtro di `list_assets` (ora tri-state).
- Il mapping `FAinfoResponse.active` (round-trip del campo al frontend).

**NON è usato** per:
- Validare transazioni (si possono ancora comprare/vendere asset inattivi).
- Bloccare il sync provider.
- Nascondere l'asset dalle pagine di dettaglio / portfolio breakdown.
- Mostrare badge "inattivo" in UI (a parte l'implicito filtro lista).

Semantica futura desiderabile (da tracciare come nuovo task post-phase-07):
- Asset inattivo = "archived": non compare nel portfolio live, no auto-sync,
  transazioni passate preservate, no nuove transazioni.
- Badge UI "📦 Archived" su card/table/detail page.
- Confirm modal "Archive?" al posto di un semplice toggle.

**Per ora la distinzione rimane utile solo come filtro di lista** — sufficiente
per il retest del feature I-bis #13.7 (Milano disabled fixture).

#### I-bis #18 — Edit modal: description `short_description` vuota all'apertura  ✅ FIXED (2026-04-22 tardi)

**Sintomo** (feedback utente sul test 2): asset Apple Inc. mostra correttamente
"Technology company" nella nuova sezione Metadata del detail page, MA all'apertura
dell'edit modal la textarea "Description" è **vuota**. Il Save successivo
avrebbe quindi accidentalmente azzerato il `short_description` nel DB.

**Root cause**: in `frontend/src/routes/(app)/assets/[id]/+page.svelte::buildEditData()`
la costruzione di `classification_params` passata al modal ometteva
`short_description`. La check `hasClassification` considerava solo sector +
geographic, quindi su asset con SOLO description (no sector/geo) il
`classification_params` diventava `null` completamente → il modal apriva
vuoto.

**Fix applicato**:
- Aggiunto `short_description: shortDescription ?? null` al payload.
- Esteso il check `hasClassification` a includere `shortDescription`.
- Commento esteso sul perché della scelta.

Verifica: `./dev.py front check` → 0 errors. Test manuale pendente: aprire
edit modal su Apple Inc. dopo populate e verificare che la textarea contenga
"Technology company".

#### I-bis #19 — Semantica estesa di `Asset.active` (follow-up)  ⏳ PENDING

Spin-off dalla risposta di #I-bis #17: il flag `Asset.active` ha oggi effetto
solo sulla lista. Per dare al feature senso reale:
- Bloccare nuove transazioni su asset inattivi (validation al create).
- Skippare il sync automatico provider sugli inattivi.
- Nasconderli dal portfolio breakdown (o mostrarli con stile "archived").
- Aggiungere badge UI "📦 Archived" su card/table/detail page.
- Confirm modal "Archive asset?" al posto del toggle silenzioso.

**Aggiornamento 2026-04-22 sera tardi**: il vero consumer del flag è lo
**scheduler automatico** (Phase 8 — vedi `phase-08-scheduler.md`, nuova
sezione "Interazione con Asset.active"). Lì il demone filtra
`AssetProviderAssignment.asset.active == True` per current-price refresh e
daily history sync. Finché Phase 8 non è attiva, la distinzione rimane
puramente cosmetica (filtro di lista).

**Aggiornamento 2026-04-22 notte** (feedback utente test 4):

Regole definitive per il consumer Asset.active, decise con l'utente dopo
lettura di phase-08-scheduler.md §Interazione con Asset.active:

- **Scheduler automatico (Phase 8)**: NON chiama né current_price né history
  per asset inattivi. Filtro `asset.active == True` nel daemon loop.
- **Sync manuale (frontend → `POST /prices/sync`, `POST /events/sync`,
  "Recalculate" button)**: consentito anche su asset inattivi. Caso d'uso:
  l'utente riattiva temporaneamente un archived, fa refresh puntuale,
  eventualmente lo riarchivia. L'azione manuale è esplicita → non deve
  essere bloccata dal flag.
- **Dashboard / Portfolio breakdown**: gli asset inattivi NON devono
  comparire. Nuovo requisito dal feedback. Implementazione: il
  `/dashboard/*` filtra `asset.active == True` nelle query di aggregazione
  (allocazione, performance, positions table, charts). Transazioni storiche
  restano consultabili nella pagina /transactions (separata).
- **Badge "📦 Archived"** su card/table/detail page dell'asset rimane
  desiderabile (dà feedback visivo nella lista "Show Inactive"), ma non
  bloccante per Phase 8.

#### I-bis #20 — Tri-state UI toggle "Active | Inactive" segmented  ✅ FIXED (2026-04-22 sera tardi)

Completa la side #I-bis #17. Il backend ora è tri-state (`Optional[bool]`) ma
il frontend aveva ancora un pulsante binario `filterActiveOnly`. Cambiato in
**segmented control a due sub-button** indipendenti, come da UX richiesta:

```
[ Active ]  [ Inactive ]
   ✓           ✗          → show only active
   ✗           ✓          → show only inactive
   ✓           ✓          → show both (no filter)
   ✗           ✗          → show both (no filter)
```

**Fix applicato** in `routes/(app)/assets/+page.svelte`:
- Rimosso `filterActiveOnly: boolean`; sostituito con due stati indipendenti
  `filterShowActive` (default true, libre-green) + `filterShowInactive`
  (default false, amber).
- Nuova logica `filteredAssets`: `bothSameState = filterShowActive === filterShowInactive`
  → se true, no filter; altrimenti matcha solo lo stato selezionato.
- Nuovo markup: `<div class="inline-flex rounded-lg border overflow-hidden">`
  con due `<button aria-pressed={...}>`, colore verde/amber per feedback
  visivo distinto.
- Nuova chiave i18n `assets.showInactive` × 4 lingue.
- Semplificato testo `assets.showActive`: da "Active only" a "Active" (è
  solo la label del button, la semantica è data dallo stato premuto).

Verifica: `./dev.py front check` → 0 errors.

Riferimento cross-linked in `phase-08-scheduler.md` §Interazione con
Asset.active (l'utente ha indicato lì la destinazione naturale del filter).

#### I-bis #21 — 500 Internal Server Error su GET /provider/assignments per AUTO_GENERATED providers  ✅ FIXED (2026-04-22 sera tardi)

**Sintomo**: dopo aver salvato un `AssetProviderAssignment` con
`provider_code=scheduled_investment` e `identifier_type=AUTO_GENERATED`, la
successiva chiamata di lettura falliva con 500:

```json
{
  "detail": "1 validation error for FAProviderAssignmentReadItem\nidentifier\n  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]"
}
```

Questo bloccava la UI del detail asset: il probe funzionava, il save
scriveva correttamente in DB, ma la re-read falliva → pannello provider
mostrava "disattivato" come fallback.

**Root cause**: il DB model `AssetProviderAssignment.identifier` è
`Optional[str]` (`NULL for AUTO_GENERATED providers` — commento nel model).
Ma la schema Pydantic di lettura `FAProviderAssignmentReadItem.identifier`
era dichiarata `str = Field(...)` (required non-null). Mismatch
DB↔schema → Pydantic rifiutava il record letto dal DB.

**Fix applicato** in `backend/app/schemas/provider.py`:
- `identifier: Optional[str] = Field(None, description="...NULL for AUTO_GENERATED providers like scheduled_investment")`.
- Rigenerato Zodios client via `./dev.py api sync`.

Verifica: `./dev.py front check` → 0 errors. Test manuale pendente: ripetere
il flusso utente (aggiungi/modifica provider scheduled_investment su BTP
Italia 2028, salva, verifica che la pagina detail lo legga senza 500).

Questo bug era la vera causa di I-bis #13.3 ("BTP Italia 2028 schedule
malformato / provider disattivato") — la config del mock era corretta, solo
la re-read lato frontend falliva.

#### I-bis #22 — Generalizzare error handling "Save failed → keep modal open + toast"  ⏳ PENDING

**Contesto** (feedback utente 2026-04-22 notte, post fix #21):

Quando il backend restituiva 500 sulla GET `/provider/assignments` (bug #21),
il flusso di save del provider si chiudeva comunque correttamente — ma in
scenari analoghi (500/4xx sulla PATCH stessa, non sulla re-read) il
comportamento oggi non è uniforme: alcune modali si chiudono e perdono lo
stato editato, altre restano aperte; gli errori arrivano a volte come toast,
a volte come console error silente, a volte non arrivano affatto.

**Requisito funzionale**:

Se il salvataggio verso il backend **fallisce** (HTTP !2xx o exception
network), la modale:
1. **NON deve chiudersi** (o, se già chiusa con effetto ottimistico, deve
   **riaprirsi** ripristinando il draft che l'utente aveva editato).
2. Deve mostrare un **toast di errore** con messaggio leggibile derivato da
   `response.detail` (FastAPI) o fallback i18n generico.
3. Deve mantenere il dirty state così che l'utente possa correggere e
   riprovare, oppure annullare esplicitamente.

**Analisi necessaria** (da eseguire prima dell'implementazione):

Censire tutti i punti del frontend dove avviene un save verso il backend,
mappando: file modal + endpoint chiamato + comportamento attuale on-error.
Candidati noti:

- `AssetModal.svelte` (`POST/PATCH /assets/*`).
- `AssetProviderAssignmentModal.svelte` (provider config).
- `AssetCurrencyChangeModal.svelte` (DELETE prices + PATCH + re-sync).
- `BrokerModal.svelte` (`POST/PATCH /brokers/*`).
- `TransactionModal.svelte` (Part 4 in arrivo — da includere nel design).
- `PriceDataImportModal.svelte` (CSV import).
- `EventsModal.svelte` (create/edit asset events).
- Tutti i flussi "Save" del `DataEditor` (prices/events edit panel).

**Design proposto** (da discutere):

- Creare un helper `$lib/utils/saveWithRetry.ts` o pattern store
  `createSaveAction<T>({ call, onSuccess, onError })` che:
  - Intercetta HTTP errors e parse `detail`.
  - Mostra toast errore via `toast.error(...)` (già presente).
  - Ritorna un discriminated union `{status: 'success', data} | {status: 'error', message}`
    così il modal sa se chiudersi o restare aperto.
- Le modali adottano il pattern: su `error` restano montate con draft
  intatto, su `success` invocano `onClose()` + toast di successo.
- Per flussi a più step (es. currency change: DELETE → PATCH → sync), il
  wrapper preserva lo step che ha fallito nel messaggio.

**Priorità**: P1 — non bloccante per Phase 7 ma da fare prima di Part 4/5
(Staging Modal) perché quel flusso userà il pattern. L'analisi (censimento
modal × endpoint × comportamento) è prerequisito a un commit dedicato nel
prossimo batch.

#### I-bis #23 — Sync scheduled_investment: status="partial" non surfacciato al frontend  ⏳ PENDING

**Contesto** (feedback utente 2026-04-22 notte, test 2 post fix #21):

Dopo il fix #21 il pannello provider torna a funzionare (il BTP Italia 2028
mostra correttamente il pulsante "Ricalcola"), ma cliccando il sync manuale
il frontend riporta un errore ambiguo (*"sinc fallisce senza motivo"*)
mentre la risposta HTTP è in realtà **200 OK**:

```json
{
  "results": [{
    "asset_id": 12,
    "status": "partial",
    "provider_used": "scheduled_investment",
    "points_fetched": 1,
    "points_changed": 0,
    "inserted_count": 0,
    "updated_count": 0,
    "events_fetched": 0,
    "events_changed": 0,
    "message": "Current value only, history unavailable",
    "errors": [],
    "elapsed_ms": 4
  }],
  "success_count": 1,
  "errors": [],
  "date_range": { "start": "2026-01-22", "end": "2026-04-22" },
  "total_points_changed": 0
}
```

**Problemi identificati**:

1. **Backend**: per `scheduled_investment` (BRIM scheduler) `points_changed=0`
   con `status=partial` è normale se la data odierna coincide con un punto
   già presente — ma il messaggio `"Current value only, history unavailable"`
   è fuorviante: l'asset **dovrebbe** generare history completa dal
   `start_date` del piano. O la logica del provider è rotta, o va rivisto
   il messaggio, o va distinto tra "nulla da aggiornare" (✅ success) e
   "provider limitato a current value" (⚠️ partial).
2. **Frontend**: la UI tratta `status=partial && points_changed=0` come
   errore generico senza esporre né il `message` né il numero di punti
   fetched/changed. Servirebbe un toast diverso in base a:
   - `success_count>0 && total_points_changed>0` → verde "N prezzi
     aggiornati".
   - `success_count>0 && total_points_changed==0` → giallo "Nessun nuovo
     prezzo (già aggiornato fino a oggi)".
   - `errors.length > 0 || results[].status=='failed'` → rosso con detail.
   - `status=='partial'` → giallo con `message` del provider.

**Azioni**:

- (a) Audit del provider `scheduled_investment.sync_asset_history`:
  capire se il return `partial / Current value only` è corretto per
  un piano periodico (dovrebbe ricalcolare tutti i punti da start_date
  a oggi) o se è un path di fallback errato.
- (b) Frontend: handler `PriceSyncResponse` con switch sui tre stati
  sopra + toast i18n differenziati (nuove chiavi
  `prices.sync.success`, `prices.sync.noChanges`, `prices.sync.partial`,
  `prices.sync.failed`).
- (c) Collegamento con #I-bis #1 (post-wipe sync 0 rows): stessa radice
  (il frontend non distingue "0 rows = OK" vs "0 rows = problema").
  Unificare il pattern in un unico handler condiviso.

**Priorità**: P1 — sblocca il retest completo dello scheduled_investment
(l'utente ora lo vede come "rotto" mentre il backend sta tornando una
risposta legittima ma mal interpretata).

#### I-bis — Priorità & ordine

**✅ Completati** (2026-04-22):
#8, #9, #10, #11, #13, #14, #15, #16, #17, #18, #20, #21.

**⏳ Pendenti** → **dettagliati in** [`plan-phase07-transaction-Part3_1_Closure.md`](./plan-phase07-transaction-Part3_1_Closure.md) §Coda I-bis pendente:
#1, #2, #3, #4, #5, #6, #7, #12, #19 (→ Phase 8/9), #22 (prerequisito Part 4/5), #23.

---

## 📦 Deliverable

### API
- `POST/PATCH/DELETE /brokers/{broker_id}/transactions/bulk` atomic + `rolled_back`.
- `POST /brokers/{broker_id}/transactions/validate` dry-run misto.
- `POST /transactions/events/suggest` tolerance 0–7gg.
- `POST /transactions/transfers/promote` promozione DEPOSIT/WITHDRAWAL → TRANSFER/FX_CONVERSION (H.4).
- `POST /assets/{id}/prices/normalize` conversione punti dissonanti.
- `GET /transactions?ids=…` (sostituisce `/{id}` rimosso).
- `GET /transactions` filtrato per broker accessibili + nuovi filtri
  `amount_abs_min`, `amount_abs_max`, `only_unlinked`, `exclude_ids` (H.3).

### Service
- `TransactionService.*_bulk` atomiche + broker-scoped.
- `TransactionService.validate_batch`, `.suggest_events_bulk`.
- `TransactionService.promote_transfer` (H.4).
- Pairing `link_uuid` esteso a DEPOSIT/WITHDRAWAL + check broker distinti su TRANSFER + check type coerente (H.1, H.2).
- `asset_source.upsert_prices_bulk` validazione currency.
- `asset_source._extend_ohlc_bounds` intra-day.
- `fx_provider_manager.ensure_pair_registered`.

### Schemi
- `rolled_back` in tutti i TXBulk*Response.
- `TXValidateBatch`, `TXValidationIssue`, `TXValidateResponse`.
- `TXEventSuggestRequestItem`, `TXEventSuggestResultItem`.
- `TXTransferPromoteRequest`, `TXTransferPromoteResponse` (H.4).
- `TXQueryParams` con `amount_abs_min`, `amount_abs_max`, `only_unlinked`, `exclude_ids` (H.3).
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
| 10 | Transfer-match via filtri `GET /transactions` esteso | No endpoint dedicato — client compone i filtri (H.3) |
| 11 | DEPOSIT/WITHDRAWAL linkabili, no nuovo tipo CASH_TRANSFER | Marker di intenzione zero-cost, niente effetto su balance/PMC (H.2) |
| 12 | `type` resta immutable via PATCH | Promozione coppia via endpoint dedicato `/transfers/promote` (H.4) |
| 13 | TRANSFER richiede broker distinti, FX_CONVERSION no | TRANSFER intra-broker è no-op semantico; FX intra-broker è use-case reale (H.1) |

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
- **Chiusura Part 3** (decisioni terminali + tutti i task pendenti): [`plan-phase07-transaction-Part3_1_Closure.md`](./plan-phase07-transaction-Part3_1_Closure.md) ⏳.
- **Successori**: Part 4 (pagina /transactions), Part 4b (File Preview), Part 5 (Staging Modal).
- **Phase doc**: [phase-07-transactions.md](./phases/phase-07-transactions.md) §Parte 3.
- **Phase 8/9 follow-up**: [`phases/phase-08-scheduler.md`](./phases/phase-08-scheduler.md) (consumer `Asset.active`).

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
./dev.py test api transfer-promotion     # H
./dev.py test services prices-currency
./dev.py test services ohlc-sentinel

# 3) Regressione completa
./dev.py test all-backend

# 4) Test manuale estetico (Blocchi D, E.5, E.6, E.7, F.5)
```
