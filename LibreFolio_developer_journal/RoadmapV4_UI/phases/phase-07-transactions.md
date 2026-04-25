# Phase 7: Transactions System — Macro Plan

**Status**: 🔄 In corso (Part 1 ✅, Part 2 ✅ Revisione 2, **Part 3 ✅ DONE 2026-04-25** — feature work + Blocco G test coverage backend 87.06% — Part 4/4b/5 TODO)
**Sub-plans archiviati**: [`phase-07-subplan/README.md`](./phase-07-subplan/README.md)
**Durata stimata**: ~11 giorni (multi-sprint, Parti 1+2+3+4+4b+5 = 1+2+2+2+1+3)
**Priorità**: P0 (MVP)
**Dipendenze**:
- Phase 4 (Brokers + `BrokerUserAccess` OWNER/EDITOR/VIEWER)
- Phase 5 (FX)
- Phase 6 (Assets + `AssetMatchingWizard` + `AssetModal`)
- Phase 6 Step 3 Round 12 ✅ (`AssetEvent` + `FAAssetEventPoint` cross-provider)

**Complessità**: ⚠️ ALTA

> **📌 Riferimenti precedenti**:
> - [`plan-phase05-to-08-upgrade.md` §6](../plan-phase05-to-08-upgrade.md) — **obsoleto**: idea originale con regimi fiscali / cash split (posticipati a Phase 8+)
> - [`plan-phase7b-filePreview.md`](../plan-phase7b-filePreview.md) — **assorbito in Parte 4b** di questo piano (File Preview System)
>
> Questo documento **sostituisce** la vecchia stesura di Phase 7 con un design unificato
> che tiene conto dell'infrastruttura completata dopo Round 12 (AssetEvent) e del
> sottosistema BRIM già operativo con upload/parse file. Incorpora inoltre il piano
> autonomo di File Preview come Parte 4b (utile per ispezionare i file BRIM prima del parsing).

---

## 🎯 Obiettivo

Completare il sotto-sistema transazioni end-to-end:

1. **Riallineare** il modello DB/schema con il nuovo design "eventi-first" collegando
   `Transaction → AssetEvent` e uniformando il controllo accessi per-utente.
2. **Estendere** i plugin BRIM per produrre anche eventi asset + metadata UI, così che
   il frontend possa renderizzare preview coerenti.
3. **Consolidare** le API in modalità **full-bulk** (no endpoint singoli), con endpoint
   dry-run per validazione e endpoint di event-suggestion.
4. **Costruire** la pagina `/transactions` in stile DataTable-with-header-filters,
   coerente con `AssetTable` / `FxTable` / `BrokerImportFilesModal`.
5. **Unificare** l'inserimento manuale, l'output BRIM e il clone di righe esistenti in
   **una sola Staging Modal** con asset-grouping colorato, SearchSelect per bulk-assign,
   event-matching automatico via tolerance slider, e commit atomico broker-aware.
6. **Aggiungere un sistema di File Preview** (assorbito dal vecchio piano `plan-phase7b-filePreview.md`)
   che permetta di ispezionare inline file image / text / table / markdown / code sia nella Files page
   sia nel `BrokerImportFilesModal` prima del parsing BRIM.

**Escluso da questa fase** (rinviato a Phase 8+ / futuro):
regimi fiscali (FIFO/LIFO/PMC), Cash Split, Over-Sell Protection, Smart Assistant per
auto-linking massivo degli eventi retroattivi.

---

## 📊 Analisi Situazione Attuale

### Backend — già solido ✅
- `Transaction` (tabella unificata, bidirectional link via `related_transaction_id`, balance validation)
- `AssetEvent` (DIVIDEND / INTEREST / PRICE_ADJUSTMENT / SPLIT / MATURITY_SETTLEMENT)
- `TransactionService.create_bulk` con access control `EDITOR` per broker
- `BRIMProvider` base + 11 plugin broker
- Flusso BRIM: upload → parse → review → commit funzionante

### Gap identificati

| # | Gap | Impatto |
|---|-----|---------|
| 1 | Link `Transaction ↔ AssetEvent` assente | Una `DIVIDEND` tx non sa da quale `AssetEvent` globale deriva. Blocca smart assistant. |
| 2 | Access control incoerente | `GET/PATCH/DELETE /transactions` non filtrano per `BrokerUserAccess` dell'utente corrente. Solo `POST` verifica `EDITOR`. |
| 3 | BRIM non espone `plugin_version` per cache invalidation | Un aggiornamento del parser non re-triggera un re-parse dei file già elaborati |
| 4 | Frontend `/transactions` è un placeholder | Nessuna lista, nessun filtro, nessun import UI. |
| 5 | Nessuna "Staging Area" | BRIM popola stato locale del componente e invia a `POST /transactions`. Manca modale unificata con validazione bulk + preview bilanci + asset resolver. |
| 6 | `BRIMProvider` non espone metadata UI per preview dinamica | No `docs_url`, no `preview_columns`. Il frontend non può renderizzare colonne broker-specifiche. |
| 7 | Bulk TX oggi è multi-broker + best-effort | Un import inconsistente lascia il portafoglio in uno stato intermedio. Serve semantica atomic per-broker (Parte 3) |

### Endpoint già esistenti da **riusare** (nessuna duplicazione)

| Necessità | Endpoint | Note |
|-----------|----------|------|
| Broker visibili all'utente | `GET /api/v1/brokers` | Già filtrato per `BrokerUserAccess` |
| Upload file BRIM | `POST /api/v1/brokers/import/upload` | |
| Parsing BRIM | `POST /api/v1/brokers/import/files/{file_id}/parse` | Trigger esplicito, non auto |
| Cached last parse | `GET /api/v1/brokers/import/files/{file_id}/last-parse` | Per riapertura Staging |
| Plugin list | `GET /api/v1/brokers/import/plugins` | |
| Asset search | `GET /api/v1/assets/query` + `GET /api/v1/assets/provider/search` | Per resolver |
| Eventi asset | `POST /api/v1/assets/events/query` | Per matching su date |

### Verifiche di dipendenza
- ✅ **Round 12 completato**: `FAAssetEventPoint` integrato in `yahoo_finance.py`,
  `justetf.py`, `scheduled_investment.py`, `asset_source.py`. Gli eventi sono già
  persistiti correttamente in `asset_events`.
- ⏳ **Step 5 Phase 6** (`AssetMatchingWizard`) — necessario per la Staging Modal.
  Se non completato prima di Part 5, il "+ Create new asset" userà direttamente
  `AssetModal` in create mode.

---

## 🗂️ Suddivisione in 6 Parti (Sprint)

| # | Parte | Area | Target | Effort | Dettaglio |
|---|-------|------|--------|--------|-----------|
| **1** | Backend DB & Schema Realignment | models, schemas, migration | Link `Transaction ↔ AssetEvent`, access control uniforme | 1g | ✅ Completato |
| **2** | BRIM come parser puro (Revisione 2) | `BRIMProvider` base + refactor 11 plugin | Plugin emettono solo TX + preview metadata; `plugin_version` per cache | 2g v1 + 0.5g revisione | ✅ Completato |
| **3** | API Consolidation — bulk atomic per-broker | endpoints, service, pytest | `POST/PATCH/DELETE /brokers/{id}/transactions/bulk` atomic, `validate` dry-run, `events/suggest`, test ≥85% | 2g | **Dettagliato** |
| **4** | Frontend — Pagina `/transactions` | route, DataTable, filtri colonna | Lista utente con filtri header, GoTo linked pair, bulk actions | 2g | **Alto livello** |
| **4b** | Frontend — File Preview System | backend service + modale multi-tipo | Preview inline (image/text/table/markdown/code) su Files page + BRIM files | 1g | **Alto livello** |
| **5** | Frontend — Staging Modal | modale unificata, asset resolver | Manual + BRIM + Clone, grouping colorato, tolerance slider 0-7, commit via /brokers/{id}/tx/bulk atomic | 3g | **Alto livello** |

Le Parti 1–3 sono **dettagliate** (alta confidenza, basso rischio di cambio).
Le Parti 4 / 4b / 5 restano **alto livello** (ASCII art + principi UX) — target e situazione
di partenza ben definiti, attività da raffinare in piano di dettaglio dedicato al
momento dell'esecuzione.

**Ordine consigliato**: 1 → 2 → 3 → 4 → 4b → 5.
La 4b può essere anticipata o posticipata rispetto alla 5 senza impatti: è **autonoma**
rispetto al modello dati transazioni.

---

## 🔷 Parte 1 — Backend: DB & Schema Realignment

### Situazione di partenza
- `models.py`: `Transaction` e `AssetEvent` esistono ma **senza FK** tra loro
- `TransactionType.DIVIDEND/INTEREST` sono "orfani" rispetto agli `AssetEventType` omonimi
- `BrokerUserAccess` presente, check solo in `create_bulk`

### Attività
1. Aggiungere `asset_event_id: Optional[int]` a `Transaction` (FK `asset_events.id`, `ondelete="SET NULL"`, nullable, indicizzato). Semantica: quando presente, la transazione è **la realizzazione personale** di un evento asset globale.
2. Aggiornare `TXCreateItem` / `TXReadItem` / `TXUpdateItem` con `asset_event_id` (optional).
3. Aggiungere flag `event_compatible: bool` a `TX_TYPE_METADATA` (true per DIVIDEND, INTEREST, ADJUSTMENT/split).
4. Validatore in `TXCreateItem.model_validator`: se `asset_event_id` presente, `asset_id` deve matchare `asset_event.asset_id` e il `type` deve essere `event_compatible`.
5. Estendere `alembic/versions/001_initial.py` con nuova colonna + indice. Rigenerare DB con `./dev.py db create-clean`.
6. Aggiornare test `test_identifier_columns_match_enum` e suite `transaction_service`.

### Deliverable
Migrazione applicata, schema coerente, test pre-esistenti verdi, nuovo campo propagato in tutte le API.

### 📌 Deferred from Part 1 (implementato con `ondelete=RESTRICT`, non SET NULL)

Punti **rinviati** durante l'esecuzione di Part 1 (vedi [`plan-phase07-transaction-Part1.md`](../plan-phase07-transaction-Part1.md)). Riportarli a galla nelle parti indicate:

- **→ Parte 3 (API Consolidation)** — aggiungere chiavi i18n dedicate per il nuovo flow di delete eventi. In Part 1 i toast del frontend (`AssetDataEditorSection.svelte`) usano stringhe letterali coerenti con il pattern `Asset data: ...`. Da centralizzare:
    - `events.deleteBlocked` (+ varianti EN/IT/FR/ES) con placeholder `{count}`, `{accessible}`, `{hidden}`.
    - `events.deleteNotFound`, `events.deletePartial`.
    - Eseguire `./dev.py i18n add` e sostituire i letterali nel componente.
- **→ Parte 4 / 5 (Frontend Transactions + Staging Modal)** — aggiungere lo spec E2E `frontend/e2e/asset-event-delete.spec.ts` che copre:
    1. delete di un evento **non** referenziato → riga scompare, toast success.
    2. delete di un evento referenziato da transazione accessibile → toast warning con `accessible_transactions` elencate, riga **resta**.
    3. delete di un evento referenziato solo da transazioni di altri utenti → toast warning con `hidden_transactions_count`, riga resta.
    4. delete bulk misto (deleted + in_use + not_found nello stesso batch) → rimosse dalla tabella solo le `deleted`.
    Lo spec è naturale da introdurre insieme al flow `●evt` (badge evento nella TransactionsTable) e alla Staging Modal che mostra il link evento→transazione.
- **→ Parte 3 / Parte 5** — popolare `backend/test_scripts/test_db/populate_mock_data.py` con almeno 1–2 transazioni (DIVIDEND / INTEREST) che abbiano `asset_event_id` valorizzato, così da coprire rendering ●evt, validate dry-run e Staging "events/suggest" senza dover creare dati ad-hoc nei test E2E.

> ⚠️ **Divergenza dal design originale**: in Part 1 la FK è stata implementata con `ondelete="RESTRICT"` (non `SET NULL` come scritto sopra al punto 1). Motivo: preservare integrità storica — non vogliamo che cancellare un `AssetEvent` lasci transazioni orfane con event-id silenziosamente azzerato. Il RESTRICT è gestito dal service con risposta per-item (`deleted` / `not_found` / `in_use` con breakdown `accessible_transactions` + `hidden_transactions_count`). Aggiornare il punto 1 della sezione "Attività" quando si archivia il piano.

---

## 🔷 Parte 2 — BRIM come parser puro (Revisione 2)

> **Nota storica**: in una prima iterazione ("v1 — BRIM Plugin v2: Events & UI
> Metadata") si era introdotto un endpoint `POST /brokers/import/commit`
> atomico, il dispatcher `BRIMCapabilities`, e l'emissione di `asset_events`
> dai plugin. Una rilettura critica ha portato al smantellamento di queste
> astrazioni (vedi [plan-phase07-transaction-Part2.prompt.md §Revisione 2](../plan-phase07-transaction-Part2.prompt.md)).
> Il blocco che segue descrive lo **stato finale post-Revisione 2**.

### Situazione di partenza (dopo v1 smantellata)
- `BRIMProvider.parse()` ritorna `BRIMParseOutput` con `transactions`, `warnings`, `extracted_assets` (NO `asset_events`).
- `BRIMPreviewColumn` + `preview_columns()` abstract già in piedi.
- `docs_url` property già in piedi.
- `search_asset_candidates()` + `BRIMAssetMapping` + `detect_tx_duplicates()` già in piedi.
- Nessun `BRIMCapabilities`, nessun `commit_import()`, nessun `/import/commit`.

### Principio
**BRIM è un parser.** Legge il file broker-specifico, produce TX con fake
asset id + elenco asset estratti + warnings. Non committa nulla, non
crea eventi, non dichiara capability UI. La risoluzione fake→real e il
commit sono responsabilità della Staging Modal frontend (Parte 5) che
usa l'endpoint standard TX (Parte 3, semantica atomica per-broker).

### Attività
1. **Aggiungere `plugin_version` al `BRIMProvider` base class**:
   - `@property plugin_version: str` con default `"1.0.0"`.
   - Docstring: "bump quando l'output del parser cambierebbe per lo stesso file".
   - Propagato in `BRIMPluginInfo.plugin_version` via `to_plugin_info()`.
2. **Persistere `plugin_version` nel metadata sidecar (via registry)**:
   - `save_parse_result(file_id, parse_result, plugin_code)` riceve solo `plugin_code` e deriva la versione dal registry (single source of truth, niente parametro `plugin_version` esposto).
   - `BRIMFileInfo` espone `parsed_plugin_code`, `parsed_plugin_version`, `parse_is_stale: bool` (computed lazy in `get_file_info`/`list_files`: `True` sse `status==PARSED && parsed_plugin_version != registry.get(plugin_code).plugin_version`).
3. **Rinominare `AssetSourceManager.bulk_upsert_events_manual` → `bulk_upsert_events`** e aggiornare callsite in `api/v1/assets.py` (unico callsite pubblico). Cancellare `bulk_upsert_events_strict` (dead code dopo smantellamento v1).
4. **Refactor tecnico `brim_provider.py`** (pulizia rilevata post-v1):
   - Estrarre helper module-level `_build_file_info_from_metadata(meta_path)` per eliminare la duplicazione tra gli inner `_parse_metadata` (in `list_files`) e `_try_parse_metadata` (in `get_file_info`).
   - Estrarre helper `_find_metadata_path(file_id)` per eliminare la tripla scansione `status → root + broker_*/` in `list_files`, `get_file_info`, `save_parse_result`.
5. **Test aggiornati**:
   - Rimossi: `test_capabilities_shape`, `test_schwab_dividend_populates_asset_events`.
   - Confermati: `test_plugin_version_is_non_empty_string`, `test_to_plugin_info_propagates_fields` (contratto per ogni plugin).
   - **Standardizzazione parametrization**: fondere le due classi parametrizzate (`TestPluginInterface` su `provider_code` e `TestBRIMPluginsContract` su `(code, plugin)`) in **un'unica** `TestBRIMPlugin` con pattern `@pytest.mark.parametrize(("code", "plugin"), _PLUGIN_PARAMS, ids=_PLUGIN_IDS)` — fail-fast a collection time, coerente con `test_asset_providers.py`/`test_fx_providers.py`.
   - **Nuovi** (contratto, parametrizzato `(code, plugin)` su tutti i plugin registrati):
     - `test_parse_is_idempotent` — stesso input → stesso output (determinismo richiesto dal caching via `plugin_version`).
     - `test_parse_produces_negative_fake_ids` — fake id nel range `< FAKE_ASSET_ID_BASE` / `is_fake_asset_id(id) == True`.
     - `test_parse_broker_id_propagated_on_all_tx` — estendere il check `broker_id` a tutti i sample e a tutte le TX.
     - `test_parse_warnings_for_malformed_row` — richiede nuovo sample `sample_reports/generic_malformed_row.csv`.
   - **Nuovo** (end-to-end API, in `test_brim_versioning.py`):
     - `test_parse_is_stale_detection` — upload + parse con v`1.0.0`, monkeypatch a v`2.0.0`, verifica `parse_is_stale` passi da `False` a `True` in `GET /files/{id}`; re-parse riallinea a `False`.
   - **Fuori scope** (Parte 5 o non pianificati): `test_detect_method_per_plugin` (coperto indirettamente da `TestAutoDetection`), `test_fake_id_collision_across_plugins` (gestione multi-parse è responsabilità Staging Modal).

### Deliverable
BRIM è un parser puro; ogni plugin espone `plugin_version`; la UI può
rilevare parse cached stantii; nessun endpoint `/commit`, nessuna
capability, nessun `asset_events` nel BRIM.

### 📋 Piani di dettaglio ancora da scrivere (status Phase 7)

Tracciamento dei sub-plan che servono ma non sono ancora stati redatti:

| Parte | Plan file | Status | Dipendenze |
|---|---|---|---|
| Parte 1 | `plan-phase07-transaction-Part1.md` | ✅ scritto ed eseguito | — |
| Parte 2 | `plan-phase07-transaction-Part2.prompt.md` (Revisione 2) | ✅ completato | Parte 1 |
| Parte 3 (include 3b) | `plan-phase07-transaction-Part3.md` (API consolidation atomic per-broker + events/suggest + deferred da Part 1 §8/§9) | 📋 **scritto, pronto per esecuzione** | Parte 1, Parte 2 |
| Parte 4 | (TBD — eventuale UX transactions page) | ⏳ da decidere | Parte 3 |
| Parte 5 | `plan-phase07-transaction-Part5-staging-modal.md` (Staging Modal frontend: resolve fake_id, event matching, `parse_is_stale` banner, commit via endpoint standard) | ⏳ **da scrivere** | Parte 2, Parte 3 |

---

## 🔷 Parte 3 — API Consolidation (full-bulk, atomic per-broker)

### Principi
- **Niente endpoint singoli**: no `GET /transactions/{id}`, no `DELETE /transactions/{id}`. Tutto via liste di ID.
- **Niente endpoint duplicati**: `GET /api/v1/brokers` già ritorna i broker accessibili.
- **Access control uniforme** su ogni verbo, derivato da `BrokerUserAccess`.
- **Bulk TX atomico per-broker** (🆕 Revisione 2): ogni bulk-create/update/delete è **broker-scoped**. Se UNA riga viola access o regole di coerenza del broker (overdraft, shorting, FK asset_event), tutto il batch viene **rigettato** (rollback). Niente più best-effort per-row.

### 🆕 Nuova semantica atomic per-broker (Revisione 2)

**Motivazione**: un utente che carica una serie di transazioni su un broker
specifico si aspetta che "tutte quelle transazioni assieme" siano coerenti
con le regole del broker. Se il set è inconsistente (cash overdraft, short,
asset_event mismatch, access denied), vuole un **unico verdetto** e la
possibilità di correggere il blocco, non un import parziale che lascia il
portafoglio in uno stato intermedio difficile da ripulire.

**Endpoint**: spostare il bulk TX da `POST /transactions` (multi-broker,
best-effort) a `POST /brokers/{broker_id}/transactions/bulk` (single-broker,
atomic). Stesso pattern già usato da `/brokers/import/upload?broker_id=...`
e `/brokers/{id}/summary`.

**Contratto**:
- Request: `List[TXCreateItem]` (il `broker_id` interno all'item deve **matchare** `{broker_id}` di path; mismatch → 400 immediato, nessun insert).
- Validazione pre-commit (in memoria) con lo stesso motore usato da `POST .../validate` (dry-run): access check, INDEX reject, asset_event FK check, balance simulation.
- Se tutte le righe passano → `create_bulk` inserisce tutto, `_validate_broker_balances` conferma post-insert, la dependency FastAPI committa.
- Se anche **una sola** riga fallisce → `session.rollback()` esplicito, response con `rolled_back=True`, `results[]` per debug (quale riga ha rotto cosa), `errors[]`, **nessun** record creato.
- Stessa semantica per `PATCH /brokers/{broker_id}/transactions/bulk` e `DELETE /brokers/{broker_id}/transactions/bulk?ids=...`.

**Impatto su `TransactionService`**:
- `create_bulk`, `update_bulk`, `delete_bulk` continuano a vivere ma diventano **broker-scoped** (nuovo parametro `broker_id`); internamente validano e, su qualsiasi errore, fanno `rollback`+ritornano `rolled_back=True`.
- L'attuale semantica multi-broker best-effort non serve a nessuno (BRIM è mono-broker, la manual entry è mono-broker). La rimuoviamo senza wrapper legacy.

**Impatto su frontend**:
- Staging Modal commit usa `POST /brokers/{broker_id}/transactions/bulk`.
- Banner rosso se `rolled_back=True` con elenco `results` per-riga (riusa pattern già visto nei toast di delete eventi Part 1).

### Attività
1. **Rimuovere** `GET /api/v1/transactions/{tx_id}`.
   Sostituito da `GET /api/v1/transactions?ids=1,2,3` (query list param), che ordina la risposta nello **stesso ordine** degli ID richiesti (pattern già adottato in `/api/v1/assets`).
2. **Uniformare access control**:
   - `GET /transactions` → filtra automaticamente per broker accessibili dall'utente (JOIN con `BrokerUserAccess`).
   - `POST /brokers/{broker_id}/transactions/bulk` → check `EDITOR` su `{broker_id}` (1 sola volta, non per-item).
   - `PATCH /brokers/{broker_id}/transactions/bulk` → idem.
   - `DELETE /brokers/{broker_id}/transactions/bulk?ids=...` → idem + verifica che ogni `id` appartenga al broker.
   - Tutto gestito in `TransactionService` (generalizzare helper `_check_broker_access`).
3. **Refactor `create_bulk/update_bulk/delete_bulk`**: broker-scoped + atomic. Ogni eccezione o balance violation → `session.rollback()` + response con `rolled_back=True`. Rimuovere la semantica multi-broker / best-effort.
4. **Nuovo endpoint** `POST /brokers/{broker_id}/transactions/validate` (body: `List[TXCreateItem]`):
   dry-run atomico **senza commit**. Usa lo stesso motore del bulk-create ma ritorna senza insert. Risposta: `validation_errors` per item + `balance_preview` per il broker. Consumato in live dalla Staging Modal (debounced 500ms).
5. **Nuovo endpoint** `POST /api/v1/transactions/events/suggest`
   (body: `[{asset_id, date, type, tolerance_days}]`):
   ricerca eventi candidati entro ±tolerance. Risposta per-item: lista `AssetEvent` ordinata per distanza temporale dalla data richiesta. Usato in Staging/Edit quando l'utente cambia asset su righe DIVIDEND/INTEREST/ADJUSTMENT. **Range `tolerance_days` consigliato: 0-7** (slider UI).
6. **Ampliamento schemi**: `asset_event_id` (da Parte 1) propagato in `create_bulk` / `update_bulk`.
7. **[deferred da Part 1] i18n del flow delete eventi**: attualmente i toast in `AssetDataEditorSection.svelte` usano stringhe letterali EN. Centralizzare con `./dev.py i18n add`:
   - `events.deleteBlocked` (placeholder `{count}`, `{accessible}`, `{hidden}`),
   - `events.deleteNotFound`,
   - `events.deletePartial`.
   Sostituire i letterali nel componente. Vedi [plan-phase07-transaction-Part1.md](../plan-phase07-transaction-Part1.md) §Deferred.
8. **[deferred da Part 1] populate_mock_data**: aggiungere 1–2 transazioni (DIVIDEND / INTEREST) con `asset_event_id` valorizzato in `backend/test_scripts/test_db/populate_mock_data.py`, così da coprire `validate` dry-run, `events/suggest` e il rendering ●evt (Part 4) senza fixture ad-hoc. ✅ **Fatto in Part 1 testing** — funzione `link_transactions_to_events()` linka la tx DIVIDEND di Apple al primo `AssetEvent` manuale Apple e stampa testing tip. Da espandere qui con almeno una INTEREST e (se serve in Part 4 per testare il caso "hidden") una tx su un broker non accessibile dall'utente di test.
9. **[deferred da Part 1] Validazione coerenza valuta nei prezzi**: oggi `upsert_prices_bulk` accetta righe con `currency` qualsiasi, anche diversa da `Asset.currency`. Una serie storica con valute miste produce un grafico semanticamente sbagliato e **non triggera** alcun banner FX (il sistema non sa che è un errore). Aggiungere in Parte 3 (è il punto in cui consolidiamo le validazioni server-side):
   - **Backend — esposizione raw currency per-point (sempre)**: `FAPricePoint.original_currency` deve essere **sempre** popolato (anche quando non c'è conversione, nel qual caso = `currency`). `FAPricePoint.backward_fill_info` resta **Optional**: è `None` nel caso "tutto ok" (95%+ dei data-point, niente stale, niente FX, niente errori), popolato solo quando c'è qualcosa da comunicare — la sola presenza dell'oggetto è il segnale "attenzione" per il frontend.
   - **Backend — discriminazione cause FX-missing (`fx_error`)**: aggiungere a `AssetBackwardFillInfo` un campo `fx_error: Optional[Literal["pair_missing", "no_rate_at_date"]] = None`. `backward_fill_info` è popolato se e solo se **almeno uno** dei seguenti è vero: (a) `days_back > 0` (price backward-filled), (b) `fx_rate_date` valorizzato (FX conversion applicata), (c) `fx_error` valorizzato (FX mancante). Semantica a 5 casi del campo:
     - (A) no-conversion + no-stale: `backward_fill_info = None` (non serializzato)
     - (B) conversion same-day: `fx_rate_date=date_point`, `fx_days_back=0`, `fx_error=None`
     - (C) conversion backward-filled: `fx_rate_date=prev_date`, `fx_days_back=N>0`, `fx_error=None`
     - (D) FX pair non in registry: both `fx_*` None, `fx_error="pair_missing"`
     - (E) FX pair esiste ma nessuna rate ≤ `date_point` (date_point pre-history): both `fx_*` None, `fx_error="no_rate_at_date"`
     Consente al frontend di discriminare il messaggio nel banner ("registra la coppia FX" vs "sincronizza FX più indietro nel tempo"). Oggi entrambi i casi D/E probabilmente finiscono in `errors[]` generici.
   - **Backend — summary aggregato**: aggiungere a `FAPriceQueryResult` un campo `currency_breakdown: list[{currency, count, first_date, last_date}]` calcolato server-side. Se `len(breakdown) > 1` l'asset ha dati cross-currency e il frontend può fare UX mirata.
   - **Backend — validazione upsert**: nel service `upsert_prices_bulk`, rifiutare item con `currency != asset.currency` (errore 400 con messaggio chiaro), oppure accettare + restituire `errors[]` per-item (coerente con la politica "nessun hard-fail" del resto di Phase 7).
   - **Backend — sync-all FX auto-detect**: quando `sync-all` prezzi parte, raccogliere tutte le `(price.currency, asset.currency)` con mismatch e iscriverle automaticamente alla FX provider registry per il successivo `sync-all` FX. Stesso pattern per `event.currency → display_currency` su eventi. Inoltre: scan di tutte le response recenti con `fx_error="pair_missing"` → auto-registration della coppia mancante.
   - **Frontend — banner mismatch intra-serie**: distinto dal banner "FX missing per target_currency" esistente. Usa `currency_breakdown`: *"Alcuni prezzi sono in EUR invece che nella valuta dichiarata USD — probabile import errato. [Normalize] [Ignore]"*. Il click su *Normalize* converte i punti dissonanti usando FX rate alla loro data e li riscrive in DB.
   - **Frontend — banner FX-missing differenziato**: leggere `fx_error` per-point, aggregare, e mostrare due banner distinti: *"Coppia FX X/Y non configurata — [Aggiungi al registry →]"* (pair_missing) vs *"FX X/Y configurata ma mancano rate prima di YYYY-MM-DD — [Sync storico →]"* (no_rate_at_date).
   - **Frontend — data-editor prezzi**: pre-fillare la colonna `currency` con `asset.currency` sui nuovi append e mostrare ⚠️ se l'utente cambia il valore (quasi sempre un errore).
   - **Eventi**: la currency diversa è **legittima** (ETF EUR con dividendi USD). Niente vincolo hard, ma aggiungere al path `query_events_bulk` un parametro opzionale `target_currency` parallelo a quello dei prezzi per convertire `event.value` a display-currency alla data dell'evento. Se la FX rate manca → entry in `result.errors[]` con "Missing FX rate for event on <date>".
9. **[deferred da Part 1] Upsert parziale OHLC + sentinel `-1` + current-price auto-extend** (affine a sync/import, quindi in Parte 3):
   - **Principio chiave**: sui prezzi **provider > utente**. Nessun `manual_override_fields`: se il provider in futuro fornisce un valore per un campo, è autorevole e sovrascrive liberamente (anche campi precedentemente cancellati dall'utente via `-1`). L'utente può ri-cancellare se serve, ma è raro e accettabile.
   - **Feature "current-price bootstrap OHLC"** (row nuova): quando il current-price inserisce un datapoint che **non esiste ancora** con solo `close`, popolare `open=high=low=close`, `volume=None`. Facilita il rendering del grafico per il giorno in corso.
   - **Feature "current-price auto-extend min/max"** (row esistente) — **nuovo, richiesto**:
     - Quando il current-price aggiorna un datapoint **già presente** in DB (tipicamente la riga di oggi), il service legge i valori correnti di `(low, high)` **prima** dell'upsert e calcola:
       - `new_low = min(existing_low, current_close)` se `existing_low is not None`, altrimenti `current_close`.
       - `new_high = max(existing_high, current_close)` se `existing_high is not None`, altrimenti `current_close`.
     - Se `existing_open is None`, set `open = current_close` (prima osservazione del giorno).
     - `volume`: lasciato intatto (il current-price provider non lo fornisce).
     - Effetto: anche con provider "poveri" (JustETF) che mandano solo close, la finestra intra-day min/max si accumula da sola tra i refresh successivi. Al prossimo sync-all (daily provider), OHLC veri sovrascrivono la stima (coerente con "provider > utente"). Nessun flag manual necessario.
     - Implementazione: nuovo helper `_extend_ohlc_bounds(existing: PriceHistory, new_close: Decimal) -> dict` invocato solo dal path current-price (non dal bulk historical). Log: `DEBUG "Extended intra-day range for {asset}@{date}: low {old}→{new}"`.
   - **Sentinel `-1` per clear esplicito** (convenzione scelta al posto del tri-state): nel payload upsert, `-1` su un campo OHLC/volume significa "SET NULL esplicito" per quel campo (la riga resta). Regole:
     - `null` / campo omesso → **no-op** (merge parziale preserva il DB).
     - valore ≥ 0 → scrivi il valore.
     - `-1` → `UPDATE ... SET campo = NULL`. **Nessun** flag manual: il prossimo sync provider potrà ripopolare il campo liberamente (provider > utente).
     - **Effetto a query-time**:
       - `close=NULL` → il punto è "vuoto": il renderer fa backward-fill dal close precedente (stessa logica già applicata per i gap giornalieri), con `backward_fill_info.days_back` popolato.
       - `open/high/low=NULL` → il candela chart può derivare i valori da `(close_{t-1}, close_t)` come proxy oppure ignorare il punto (line chart puro).
       - `volume=NULL` → display `—`.
     - **UX Frontend — icona "gomma" 🧽 per-cella**: ogni cella OHLC/volume editabile mostra, in hover, un'icona gomma discreta. Click → conferma rapida → popola il payload con `-1` per quel campo. Keyboard shortcut: `Delete` su cella selezionata = stesso effetto.
     - **UX Frontend — presentazione del NULL (mai mostrare `-1`)**: il sentinel `-1` è un dettaglio di trasporto, **non deve mai comparire nella UI**. Sia dopo una cancellazione (click gomma) sia al caricamento di dati nativamente NULL dal DB, la cella mostra un placeholder testuale i18n-zato (key candidate: `dataEditor.cell.notSet` → EN "Not set", IT "Non impostato", FR "Non défini", ES "No establecido") in italic grigio chiaro. Stesso placeholder per close/open/high/low/volume. Il parser dell'input in edit-mode tratta stringa vuota **e** il placeholder come "no-op" (no payload field); solo il click-gomma genera `-1` nel payload.
     - Documentare il sentinel nei docstring dello schema (`FAPricePoint`) e in mkdocs_src.
     - Caveat `volume`: improbabile che provider leciti segnalino `-1` come misura reale; ma documentare per sicurezza. Se un provider lo fa, mappa a `None` pre-upsert.
10. **Test matrix**:
   - OWNER / EDITOR / VIEWER × GET / POST / PATCH / DELETE × owned / foreign broker
   - `validate` senza side-effect (DB invariato)
   - `events/suggest` con tolleranza 0 / 3 / 7 giorni
   - Link `asset_event_id` rifiutato se `asset_id` mismatch
   - **Atomic per-broker**: una sola riga che viola (overdraft / shorting / asset_event mismatch) → rollback totale del batch, DB invariato, `rolled_back=True` in response
   - **Broker mismatch nel body**: `broker_id` dell'item ≠ `{broker_id}` del path → 400 immediato, nessun insert
   - Copertura ≥85% su `transaction_service` e `brim_provider`

### Deliverable
API bulk coerenti, niente endpoint singolari, suite test green, endpoint di supporto per la Staging Modal pronti.

---

## 🔷 Parte 4 — Frontend: Pagina `/transactions` (Alto Livello)

### Principi UX
- **Filtri tutti nelle column header** tramite `DataTableColumnFilter` già esistente (date range, enum multiselect, text search, number range, asset autocomplete, tag multiselect).
- **Toolbar minima**: solo azioni globali (`↻ Refresh`, `Cols▾ ColumnVisibilityToggle`, `📥 Import ▾`, `+ New`).
- **Paginatore server-side** via `DataTablePagination` esistente.
- **`SelectionBar`** per bulk actions (pattern `BrokerImportFilesModal`).
- **GoTo linked pair**: click 🔗 naviga alla pagina contenente la riga pair, evidenziandola (stesso pattern dei data-editor asset/forex dopo doppio-click). Implementazione: `?highlight_id=N` in query string + scroll + pulse.
- **Indicatore ●evt**: badge viola quando `asset_event_id != null`, tooltip con dettagli evento.
- **Badge tipo** via `TransactionTypeBadge.svelte`, guidato da `TXTypeMetadata` cached post-boot (coerente con `broker_detail` — BUY verde, SELL rosso, DIVIDEND viola…).

### Wireframe ASCII

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│  Transactions                        [↻] [Cols▾] [📥 Import ▾] [+ New]           │
│  All transactions across your accessible brokers                                  │
├───────────────────────────────────────────────────────────────────────────────────┤
│ ☐ │Date▲▼🔽 │Type🔽  │Asset 🔍🔽      │Qty 🔽    │Cash 🔽     │Broker🔽 │Tags🔽 │⋯│
├───┼─────────┼────────┼────────────────┼──────────┼────────────┼─────────┼───────┼─┤
│ ☐ │04-15-26 │🛒 BUY  │VWCE            │+10.00    │-€1,050.00  │Degiro   │—      │✎│
│ ☐ │04-10-26 │💵 DIV  │AAPL            │ 0        │+€12.40     │IBKR     │div    │✎│←●evt
│ ☐ │04-08-26 │💱 FX   │—               │ 0        │-$1,000.00  │IBKR     │—      │✎│🔗
│ ☐ │04-08-26 │💱 FX   │—               │ 0        │+€921.50    │IBKR     │—      │✎│🔗
│ ☐ │04-05-26 │🔄 XFER │BTC             │-0.5      │—           │Coinbase │—      │✎│🔗
│ ☐ │04-05-26 │🔄 XFER │BTC             │+0.5      │—           │Ledger   │—      │✎│🔗
│ ☐ │04-01-26 │💰 DEP  │—               │ 0        │+€2,000.00  │Degiro   │—      │✎│
├───────────────────────────────────────────────────────────────────────────────────┤
│ ▾ 3 selected: [✎ Edit bulk] [📋 Clone to staging] [🗑 Delete]  ← SelectionBar    │
│                                                                                   │
│  Rows per page: [50 ▾]      ◀ Prev   Page 1 of 12   Next ▶   Total 582 tx       │
└───────────────────────────────────────────────────────────────────────────────────┘

🔽 = column filter popover    🔗 = GoTo linked pair    ●evt = linked AssetEvent
```

### Attività (alto livello)
- Route `src/routes/(app)/transactions/+page.svelte` + `+page.ts` carica `GET /transactions` + `GET /brokers` + `GET /transactions/types`.
- Componente `TransactionsTable.svelte` wrapper di `DataTable` con colonne: select, date, type, asset, qty, cash, broker, tags, `linked_icon`, `event_icon`, actions.
- Filtri sincronizzati con **query string** per linkabilità (`/transactions?broker_id=3&type=DIVIDEND`).
- Icona 🔗 (lucide `Link2`) visibile se `related_transaction_id != null`. Click → filtra pagina su `?ids=<this>,<related>&highlight=<related>` → scroll + pulse.
- Icona ● (badge viola) se `asset_event_id != null`, tooltip con evento.
- **Bulk actions** in `SelectionBar`:
  - `✎ Edit bulk` → apre Staging Modal (Parte 5) in modalità **edit** con N righe pre-caricate come `TXUpdateItem`.
  - `📋 Clone to staging` → apre Staging Modal in modalità **create** con N righe clonate (id stripped, data=oggi default).
  - `🗑 Delete` → `ConfirmModal` + `DELETE /transactions?ids=...`.
- **Single-row actions** (icona ✎ in colonna azioni): stesso flow dei bulk ma con N=1.
- **Import menu**:
  - "From broker file…" → apre `BrokerImportFilesModal` esistente. Dopo parse successful → auto-apre Staging in modalità BRIM.
  - "Manual entry…" → apre Staging vuota.
- **[deferred da Part 1] Spec E2E `frontend/e2e/asset-event-delete.spec.ts`**: naturale da introdurre qui insieme al badge ●evt (evidenzia collegamento transazione↔evento). Copre 4 scenari: (1) delete evento non referenziato → riga scompare + toast success; (2) delete evento referenziato da tx accessibile → toast warning con `accessible_transactions`, riga resta; (3) delete evento referenziato solo da tx di altri utenti → toast warning con `hidden_transactions_count`, riga resta; (4) delete bulk misto (deleted + in_use + not_found) → sparisce solo la riga `deleted`. Vedi [plan-phase07-transaction-Part1.md](../plan-phase07-transaction-Part1.md) §Deferred.

### Deliverable
Pagina funzionante con visualizzazione + filtri + delete/edit/clone via Staging Modal.

---

## 🔷 Parte 4b — Frontend: File Preview System (Alto Livello)

### Motivazione
Prima di cliccare "Parse" su un file BRIM uploadato, l'utente vuole poter **ispezionare il
contenuto grezzo** per verificare encoding, separatore, intestazioni, righe di spazzatura.
Lo stesso meccanismo serve nella pagina Files per i file statici. Questo piano era stato
disegnato autonomamente in [`plan-phase7b-filePreview.md`](../plan-phase7b-filePreview.md)
e viene ora **assorbito** qui con i necessari aggiornamenti di stack.

### Situazione di partenza
- Nessun endpoint di preview file (solo download diretto)
- `BrokerImportFilesModal` mostra solo metadata (nome, dimensione, stato)
- Files page mostra solo lista, senza preview

### Principi UX
- **Bottone 👁 preview** visibile solo per file con `canPreview(filename) === true`.
- **Modale unificata** `FilePreviewModal` (basata su `ModalBase` esistente) che auto-detecta il tipo dal backend e renderizza il sub-componente appropriato.
- **Integrazione in 3 posizioni**:
  - Pagina `/files` tab Static
  - Pagina `/files` tab BRIM
  - `BrokerImportFilesModal` (nuovo accesso via Import ▾ dalla pagina `/transactions`)
- **Binari/archivi**: NO preview, solo download (nessun bottone visualizzato).

### Tipi supportati

| Categoria | Estensioni | Componente | Controlli |
|-----------|------------|------------|-----------|
| Image | jpg, jpeg, png, gif, webp, svg | `ImagePreview.svelte` | Slider qualità 25/50/75/100%, dimensioni originali |
| Text | txt, log, json, xml, yaml, yml | `TextPreview.svelte` | Line-range picker, line numbers, total lines |
| Markdown | md, markdown | `MarkdownPreview.svelte` | Toggle raw/rendered (via `marked` + `dompurify`) |
| Table | csv, xlsx, xls | `TablePreview.svelte` | Wrapper `DataTable`, row-range picker, total rows |
| Code | py, js, ts, html, css, sql | `CodePreview.svelte` | Syntax highlighting (`highlight.js`), line-range picker |
| Unsupported | zip, tar, pdf, … | — | Solo download, nessun bottone preview |

### Wireframe ASCII (caso CSV BRIM)

```
╔════════════════════════════════════════════════════════════════════════╗
║ 👁 Preview — degiro_2026-04.csv · 12.3 KB · 847 rows               [✕]║
╠════════════════════════════════════════════════════════════════════════╣
║ Type: CSV      From row: [1▾]    To row: [50▾]    Total: 847          ║
║ Separator: [auto ▾]   Encoding: [utf-8 ▾]                             ║
╠════════════════════════════════════════════════════════════════════════╣
║ # │Date       │Product             │ISIN         │Qty     │Price      ║
║ 1 │04-15-2026 │VANGUARD FTSE ALLW  │IE00BK5BQT80 │+10     │€105.00    ║
║ 2 │04-15-2026 │VANGUARD FTSE ALLW  │IE00BK5BQT80 │ 0      │-€0.50 fee ║
║ 3 │04-10-2026 │APPLE INC           │US0378331005 │ 0      │+€12.40 div║
║ ...                                                                    ║
╠════════════════════════════════════════════════════════════════════════╣
║                       [Download full file]  [Close]                    ║
╚════════════════════════════════════════════════════════════════════════╝
```

### Backend

| File | Azione | Descrizione |
|------|--------|-------------|
| `backend/app/services/file_preview.py` | **Nuovo** | `PreviewType` enum, `detect_preview_type()`, `get_text_preview()`, `get_table_preview()`, `get_markdown_preview()`, `get_image_preview()` |
| `backend/app/schemas/uploads.py` | Modifica | `FilePreviewResponse` + `FilePreviewMetadata` |
| `backend/app/api/v1/uploads.py` | Modifica | `GET /files/{file_id}/preview` (param: `start_line`, `end_line`, `render_md`, `img_quality`) |
| `backend/app/api/v1/brokers.py` | Modifica | `GET /brokers/import/files/{file_id}/preview` (stessa shape) |
| `backend/app/config.py` | Modifica | `PREVIEW_MAX_LINES`, `PREVIEW_MAX_FILE_SIZE_MB` |

### Frontend

| File | Azione | Descrizione |
|------|--------|-------------|
| `src/lib/types/preview.ts` | **Nuovo** | `PreviewType`, `FilePreviewResponse`, `FilePreviewMetadata` |
| `src/lib/utils/filePreview.ts` | **Nuovo** | `canPreview(filename)` |
| `src/lib/components/ui/media/FilePreviewModal.svelte` | **Nuovo** | Modale principale (wraps `ModalBase`, Svelte 5 runes) |
| `src/lib/components/ui/media/ImagePreview.svelte` | **Nuovo** | Slider qualità |
| `src/lib/components/ui/media/TextPreview.svelte` | **Nuovo** | Line-range, line numbers |
| `src/lib/components/ui/media/MarkdownPreview.svelte` | **Nuovo** | `marked` + `dompurify`, toggle raw/rendered |
| `src/lib/components/ui/media/TablePreview.svelte` | **Nuovo** | Wrapper `DataTable` esistente |
| `src/lib/components/ui/media/CodePreview.svelte` | **Nuovo** | `highlight.js` |
| `src/lib/components/files/FilesTable.svelte` | Modifica | Bottone 👁 in colonna azioni |
| `src/lib/components/brokers/BrokerImportFilesModal.svelte` | Modifica | Bottone 👁 prima di "Parse" |

### Dipendenze nuove

**Backend** (`pipenv install`): `python-magic`, `openpyxl` (se non già), `markdown`.
**Frontend** (`npm install`): `marked`, `dompurify`, `highlight.js`.

### Attività (alto livello)
1. Backend: `PreviewService` con dispatch per tipo (30m setup + 2h API + schema).
2. Schema response unificato `FilePreviewResponse` propagato nei due endpoint.
3. Frontend: utility `canPreview()` + `FilePreviewModal` master (15m setup + 3h componenti).
4. Integrazione Files page (tab Static + BRIM) e `BrokerImportFilesModal` (~1h).
5. i18n (~15m): chiavi `files.preview`, `files.quality`, `files.fromLine`, `files.toLine`, `files.totalLines`, `files.totalRows`, `files.showRaw`, `files.showRendered`, `files.previewUnsupported` × 4 lingue.
6. Test E2E Playwright: image+quality, text+range, csv→DataTable, markdown toggle, binary no-preview, brim file preview (~1h).

### Deliverable
Sistema preview funzionante in 3 punti di accesso (Files Static, Files BRIM, BrokerImportFilesModal), con 5 sub-componenti tipo-specifici e copertura E2E.

### Note di sicurezza/perf
- **Streaming** per file testuali grandi (evitare caricamento totale in RAM).
- **DOMPurify** obbligatorio sul markdown renderizzato per evitare XSS.
- **Cache** opzionale (LRU in-memory) per preview frequenti.
- **Size limit** via `PREVIEW_MAX_FILE_SIZE_MB` — oltre, ritorna errore strutturato con indicazione "file troppo grande, solo download".

---

## 🔷 Parte 5 — Frontend: Staging Modal (Alto Livello)

### Flusso BRIM completo (post-Revisione 2)

```
1. User apre Import ▾ → "From broker file…"
2. BrokerImportFilesModal (esistente) → seleziona broker + file già uploadato
   (oppure upload nuovo file via POST /brokers/import/upload)
3. User clicca "Parse" sulla riga file → POST /brokers/import/files/{id}/parse
   con { plugin_code, broker_id }
4. Backend ritorna BRIMParseResponse (transactions + asset_mappings + duplicates
   + warnings). Il file viene auto-marcato PARSED (o FAILED su errore) e il
   risultato cachato nel metadata sidecar con la `plugin_version` corrente.
5. Frontend auto-apre Staging Modal pre-popolata
6. In Staging: user risolve asset (fake_id → real_id), rivede duplicati,
   fa match TX ↔ AssetEvent (slider ±0..7gg via POST /transactions/events/suggest),
   commit via POST /brokers/{broker_id}/transactions/bulk (endpoint standard,
   atomic per-broker — vedi Parte 3)
7. Se `rolled_back=True` → banner rosso con `results[]`, Staging resta aperta
   con stato invariato. Se ok → Staging si chiude, toast "N transactions imported".
```

### Principi UX aggiuntivi
- **Tutte le colonne hanno filtri header** (stesso pattern della lista).
- **Asset grouping per colore**: ogni `asset_id` unico in staging riceve un colore distintivo (pastello, ~8 colori ciclici). Le righe con stesso asset condividono il colore. Modificare l'asset di una riga la sposta nel gruppo-colore corrispondente.
- **SearchSelect globale per colore**: sopra la tabella, un `SearchSelect` per ogni colore attivo che modifica **in bulk** tutte le righe di quel gruppo.
- **Split asset**: bottone 🎨 in row-actions per "slegare" una riga da un gruppo e metterla in un gruppo nuovo (utile quando BRIM raggruppa male).
- **SearchSelect manuale**: oltre al resolver automatico (da `extracted_symbol`/`isin`/`name`), l'utente può aprire `SearchSelect.svelte` (riuso da `AssetCompare`) per selezionare esplicitamente tra gli asset del DB, OPPURE cliccare "+ Create new" → apre `AssetModal` esistente (o `AssetMatchingWizard` quando completato). Il frontend **auto-assegna** `selected_asset_id` se `BRIMAssetMapping.candidates` contiene esattamente 1 elemento (suggerimento del backend, overridable).
- **Event matching parametrico** (post-asset-resolve):
  - Per ogni riga DIVIDEND / INTEREST / ADJUSTMENT con asset risolto, il frontend chiama `POST /transactions/events/suggest` con `tolerance_days` (default 7, slider 0..7).
  - 1 match → auto-link. N>1 → popover con scelta. 0 → nessun link.
  - L'utente può sempre: (a) accettare il match, (b) aprire ricerca manuale, (c) cliccare "+ Create new event" per crearlo al volo, (d) lasciare la TX "orfana" (nessun `asset_event_id`).
  - Slider tolerance visibile in un settings popover ⚙ della modale.
- **Auto-pair TRANSFER/FX_CONVERSION** (strutturalmente identici: entrambi usano `related_transaction_id` + `link_uuid`): quando user sceglie `type=TRANSFER` o `type=FX_CONVERSION` → auto-genera riga-coppia con `link_uuid` condiviso e segni invertiti. Le due righe sono editate insieme.
- **Duplicate banner** (da `BRIMDuplicateReport`): chip `⚠ 2 possible duplicates` → click espande pannello con checklist ignora/importa.
- **Validazione live**: debounced 500ms → `POST /brokers/{broker_id}/transactions/validate` → banner errori per-riga + balance preview aggiornato.
- **Rollback banner**: se il commit ritorna `rolled_back=True`, banner rosso persistente con elenco `results[]` (quale riga ha rotto cosa). Nessuna modifica al DB, Staging resta aperta con stato invariato.
- **Parse stantio**: se `BRIMFileInfo.parse_is_stale=true`, la UI mostra "Plugin updated — re-parse available" con pulsante per ri-triggerare `POST /files/{id}/parse`.
- **Preview columns dinamiche**: la tabella legge `BRIMPluginInfo.preview_columns` del plugin usato e costruisce le colonne a runtime (key/label/type/width/align).
- **Modalità-solo** (no route dedicata, sempre modale larga ~95vw × 90vh).

### Wireframe ASCII

```
╔══════════════════════════════════════════════════════════════════════════════════════╗
║ 📥 Staging — 8 tx ready · 2 unresolved · 2 possible duplicates            ⚙  [✕]  ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║ Source: BRIM "Degiro CSV" · File: report_apr.csv · Broker: Degiro                   ║
║                                                                                      ║
║ 🎨 Asset groups: [🟦 VWCE▾] [🟨 BTC ▾] [🟥 AAPL▾] [🟩 unresolved 🔍"TSLA"▾] [+]   ║
║    ↑ ogni SearchSelect modifica tutte le righe di quel colore                       ║
║                                                                                      ║
║ Event matching tolerance: [──●────] 7 days    Auto-link on asset change: [✓]        ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║ ☐│Date 🔽│Type🔽 │Asset (group) 🔍🔽│Qty 🔽 │Cash 🔽    │Link🔽│Evt🔽│✓│⋯ │         ║
║ ─┼───────┼───────┼───────────────────┼───────┼───────────┼──────┼─────┼─┼──┤         ║
║🟦│04-15  │🛒 BUY │VWCE               │+10.00 │-€1,050    │—     │—    │✓│⚙│         ║
║🟦│04-15  │🛒 BUY │VWCE               │+5.00  │-€525      │—     │—    │✓│⚙│         ║
║🟥│04-10  │💵 DIV │AAPL               │ 0     │+€12.40    │—     │🔗evt│✓│⚙│ ←auto   ║
║🟨│04-08  │🔄 XFER│BTC                │-0.5   │—          │pair A│—    │✓│⚙│         ║
║🟨│04-08  │🔄 XFER│BTC                │+0.5   │—          │pair A│—    │✓│⚙│         ║
║🟩│04-05  │🛒 BUY │🔍 "TSLA" unres.   │+3.00  │-$750      │—     │—    │✕│⚙│ ⚠       ║
║🟩│04-02  │💵 DIV │🔍 "MSFT" unres.   │ 0     │+$22       │—     │—    │✕│⚙│ ⚠       ║
║  │04-01  │💰 DEP │—                  │ 0     │+€2,000    │—     │—    │✓│⚙│         ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║ ⚠ Row 3: AAPL dividend in DB il 2026-04-11 (1d off) → [Auto-link] [Ignore]          ║
║                                                                                      ║
║ Balance preview (Degiro): Cash EUR −€1,575 · Holdings VWCE +15                      ║
║                                                                                      ║
║      [Cancel]  [Validate (live)]  [Commit 6/8 tx ▸]  (2 unresolved blocked)         ║
╚══════════════════════════════════════════════════════════════════════════════════════╝

Icone: ⚙ row-actions (split asset, remove, duplicate, open event matcher)
       🔗evt = asset_event_id assegnato (click = popover evento)
```

### Sub-componenti pianificati

| Componente | Ruolo |
|------------|-------|
| `TransactionStagingModal.svelte` | Modale larga, stato locale `$state` con draft list |
| `StagingTable.svelte` | `DataTable` con celle editabili + color-band sinistra per gruppo asset |
| `AssetGroupSelector.svelte` | Riga di `SearchSelect` colorati sopra la tabella |
| `RowActions.svelte` | Menu ⚙ per riga (split-asset / remove / duplicate / event-matcher) |
| `EventSuggestionPopover.svelte` | Mostra risultato `events/suggest` |
| `BalancePreviewPanel.svelte` | Usa risposta `POST /transactions/validate` |
| `DuplicateBanner.svelte` | Da `BRIMDuplicateReport`, checklist ignora/importa |

### Modalità di apertura

| Modalità | Origine | Commit endpoint |
|----------|---------|-----------------|
| `create-manual` | Start vuoto, `+ Add row` | `POST /brokers/{broker_id}/transactions/bulk` (atomic) |
| `create-brim` | Pre-popolato da `BRIMParseResponse` | `POST /brokers/{broker_id}/transactions/bulk` (atomic) |
| `edit-bulk` | Pre-popolato da N `TXReadItem` → `TXUpdateItem` draft | `PATCH /brokers/{broker_id}/transactions/bulk` (atomic) |
| `clone-bulk` | Clone di N righe (id stripped) | `POST /brokers/{broker_id}/transactions/bulk` (atomic) |

Tutte e 4 le modalità usano lo **stesso** endpoint broker-scoped (Parte 3):
un commit = un broker = all-or-nothing. Niente più endpoint BRIM-specifico.

### Deliverable
Modale unificata che copre i 4 ingressi, riusa `AssetModal` / `AssetMatchingWizard`, con validazione server live e commit atomico broker-aware.

### 📌 Deferred from Part 1 — ricadute in Parte 5

- **Event link/unlink nella Staging Modal**: la Staging deve esporre un controllo per impostare `asset_event_id` (tramite `POST /transactions/events/suggest`, già schedulato in Parte 3) **e** per rimuovere il link usando la sentinel `asset_event_id = 0` di `TXUpdateItem` (implementata in Part 1). Da coprire nello spec E2E `asset-event-delete.spec.ts` (allocato in Parte 4) esteso con il caso "unlink via Staging edit-bulk".
- **Blocco delete evento in-use**: se l'utente apre il popover evento da una tx e tenta di cancellare l'evento globale, il backend può rispondere `status=in_use`. La Staging / popover deve mostrare il breakdown `accessible_transactions` + `hidden_transactions_count` (stesso UX pattern del data-editor eventi Part 1).

### 📌 Deferred from Part 2 — ricadute in Parte 5 (Revisione 2)

- **Rendering dinamico `preview_columns`**: la Staging Modal deve leggere `BRIMPluginInfo.preview_columns` dal plugin usato per il parse e costruire le colonne della `DataTable` a runtime (invece di un set hard-coded). Ogni colonna porta `key`, `label` (passata a i18n), `type`, `width`, `align`.
- **`plugin_version` + `parse_is_stale`**: se `BRIMFileInfo.parse_is_stale=true`, mostrare banner "Plugin updated since last parse — [Re-parse]" che ri-triggera `POST /brokers/import/files/{id}/parse`. Altrimenti la Staging può usare direttamente `GET /brokers/import/files/{id}/last-parse` cachato senza re-parsare.
- **Commit via `POST /brokers/{broker_id}/transactions/bulk`** (non più via un endpoint BRIM-specifico): il client invia il payload TX **dopo** aver sostituito i fake id con i real id. Risposta con `rolled_back: bool`, `results[]`, `created_tx_ids`, `errors[]`. Vedi Parte 3 per la semantica atomica per-broker.
- **Gestione `rolled_back=true`**: banner rosso persistente con il dettaglio dei `results` falliti. Nessuna modifica al DB, quindi la Staging Modal resta aperta con lo stato invariato e l'utente può correggere.
- **E2E `brim-atomic-commit.spec.ts`**: nuovo spec Playwright che verifica rollback atomico simulando un'overdraft violation → nessuna TX creata in DB, banner mostrato, stato Staging preservato.

---

## 🗂️ File da Creare / Modificare (riepilogo)

### Backend (modifiche)

| File | Modifica | Parte |
|------|----------|-------|
| `backend/app/db/models.py` | `Transaction.asset_event_id` FK + index | 1 |
| `backend/app/schemas/transactions.py` | `asset_event_id` in TXCreate/Update/Read, validator, `event_compatible` in `TX_TYPE_METADATA` | 1 |
| `backend/alembic/versions/001_initial.py` | Aggiungere colonna + indice | 1 |
| `backend/app/services/brim_provider.py` | Base class: `plugin_version`, `docs_url`, `preview_columns` abstract, `BRIMParseOutput` (senza asset_events). **NO** `capabilities`, **NO** `commit_import` | 2 |
| `backend/app/services/brim_providers/*.py` (×11) | Refactor parse() alla nuova firma; Schwab NON emette più asset_events | 2 |
| `backend/app/schemas/brim.py` | `BRIMPreviewColumn`, `plugin_version`/`parsed_plugin_version`/`parse_is_stale` in `BRIMFileInfo`. **Rimossi**: `BRIMCapabilities`, `BRIMCommitRequest/Response/ResultItem`, `asset_events` da `BRIMParseOutput/Response` | 2 |
| `backend/app/services/asset_source.py` | Rinomina `bulk_upsert_events_manual` → `bulk_upsert_events`; rimuovi `bulk_upsert_events_strict` | 2 |
| `backend/app/api/v1/brokers.py` | **Rimuovi** `POST /brokers/import/commit`. Verifica auto-transition `move_to_parsed/failed` post-parse | 2 |
| `backend/app/api/v1/transactions.py` | Rimuovere `GET /{tx_id}`. Spostare bulk a `POST/PATCH/DELETE /brokers/{broker_id}/transactions/bulk` atomic. Aggiungere `POST /brokers/{broker_id}/transactions/validate` + `POST /transactions/events/suggest` | 3 |
| `backend/app/services/transaction_service.py` | `create_bulk/update_bulk/delete_bulk` → broker-scoped + atomic (rollback su qualsiasi errore) | 3 |
| `backend/app/services/file_preview.py` | **Nuovo**: dispatch preview per tipo (image/text/table/markdown/code) | 4b |
| `backend/app/schemas/uploads.py` | `FilePreviewResponse` + `FilePreviewMetadata` | 4b |
| `backend/app/api/v1/uploads.py` | `GET /files/{file_id}/preview` | 4b |
| `backend/app/api/v1/brokers.py` (import) | `GET /brokers/import/files/{file_id}/preview` | 4b |
| `backend/app/config.py` | `PREVIEW_MAX_LINES`, `PREVIEW_MAX_FILE_SIZE_MB` | 4b |

### Frontend (nuovi)

| File | Descrizione | Parte |
|------|-------------|-------|
| `src/routes/(app)/transactions/+page.svelte` | Lista con filtri header | 4 |
| `src/routes/(app)/transactions/+page.ts` | Load function | 4 |
| `src/lib/components/transactions/TransactionsTable.svelte` | Wrapper `DataTable` | 4 |
| `src/lib/components/transactions/TransactionTypeBadge.svelte` | Badge tipo da `TXTypeMetadata` | 4 |
| `src/lib/components/transactions/TransactionStagingModal.svelte` | Modale unificata | 5 |
| `src/lib/components/transactions/StagingTable.svelte` | Editable DataTable con color-band | 5 |
| `src/lib/components/transactions/AssetGroupSelector.svelte` | `SearchSelect` per colore | 5 |
| `src/lib/components/transactions/RowActions.svelte` | Menu ⚙ per riga | 5 |
| `src/lib/components/transactions/EventSuggestionPopover.svelte` | Popover eventi candidati | 5 |
| `src/lib/components/transactions/BalancePreviewPanel.svelte` | Preview bilanci dal validate | 5 |
| `src/lib/components/transactions/DuplicateBanner.svelte` | Banner duplicati BRIM | 5 |
| `src/lib/types/preview.ts` | Tipi TS `PreviewType`, `FilePreviewResponse` | 4b |
| `src/lib/utils/filePreview.ts` | `canPreview(filename)` | 4b |
| `src/lib/components/ui/media/FilePreviewModal.svelte` | Modale unificata preview | 4b |
| `src/lib/components/ui/media/ImagePreview.svelte` | Preview immagini con quality slider | 4b |
| `src/lib/components/ui/media/TextPreview.svelte` | Preview testo con line-range | 4b |
| `src/lib/components/ui/media/MarkdownPreview.svelte` | Preview markdown raw/rendered | 4b |
| `src/lib/components/ui/media/TablePreview.svelte` | Preview CSV/Excel via `DataTable` | 4b |
| `src/lib/components/ui/media/CodePreview.svelte` | Syntax highlighting | 4b |

### Frontend (modifiche)

| File | Modifica | Parte |
|------|----------|-------|
| `src/lib/components/brokers/BrokerImportFilesModal.svelte` | Dopo parse ok → emit event → Staging auto-open. Bottone 👁 Preview per riga (Parte 4b) | 4/4b/5 |
| `src/lib/components/files/FilesTable.svelte` | Bottone 👁 in colonna azioni (Static + BRIM tab) | 4b |
| `src/lib/api/*` | Rigenerare tipi dopo `./dev.py api sync` | tutte |

---

## 🔎 Considerazioni finali & Decisioni

| # | Decisione | Note |
|---|-----------|------|
| 1 | **Event-linking**: opt-in con auto-suggest slider 0–14gg alla selezione asset (create + edit) | Grouping per colore + SearchSelect per bulk-assign di tutte le righe dello stesso gruppo |
| 2 | **No legacy BRIM**: rompo firma `parse()` in tutti gli 11 plugin, niente wrapper | La v1 non è mai andata in produzione |
| 3 | **Solo modale, niente route dedicata** | Modale larga ~95vw × 90vh sufficiente per tutti i flussi |
| 4 | **FX_CONVERSION ≡ TRANSFER** strutturalmente | Entrambi usano `related_transaction_id` + `link_uuid`, auto-pair in Staging |
| 5 | **Round 12 completato** ✅ | AssetEvent infrastructure operativa, Parte 1 può procedere |
| 6 | **Full-bulk API** | Niente `GET/DELETE /transactions/{id}`, tutto via liste di ID |
| 7 | **Riuso endpoint esistenti** | `GET /brokers` è già filtrato per access → niente `accessible-brokers` nuovo |
| 8 | **Smart assistant retroattivo** (matching eventi ↔ transazioni storiche) | Posticipato a Phase 8+ |
| 9 | **Regimi fiscali / Cash Split / Over-Sell Protection** | Posticipati a Phase 8+ (erano nel piano originale `plan-phase05-to-08-upgrade.md §6` ma fuori scope MVP) |
| 10 | **File Preview System** incorporato come Parte 4b | Assorbe il vecchio `plan-phase7b-filePreview.md`. Allineato a Svelte 5 runes + `ModalBase` + `DataTable` esistenti. Autonomo rispetto al modello transazioni: può essere implementato in parallelo a Parti 1–3 se ci sono risorse |
| 11 | **🆕 BRIM = parser puro** (Revisione 2) | Smantellata l'implementazione v1 con `BRIMCapabilities` + `asset_events` + `/import/commit` atomico. Il BRIM produce solo transazioni con fake id + asset estratti. Il commit è responsabilità del frontend via endpoint standard TX. `plugin_version` introdotta per invalidare parse cached |
| 12 | **🆕 Bulk TX atomic per-broker** (Revisione 2) | `POST/PATCH/DELETE /brokers/{broker_id}/transactions/bulk` sostituisce il precedente `POST /transactions` multi-broker best-effort. Un commit = un broker = all-or-nothing. Risposta con `rolled_back: bool`. Coerente con il principio "un import è un'unità coerente" |
| 13 | **🆕 `bulk_upsert_events_manual` → `bulk_upsert_events`** (Revisione 2) | Rimosso suffisso `_manual` ridondante (lo scope "user events" è già implicito nell'endpoint `PUT /assets/events/bulk`) |

---

## ✅ Verifica Completamento

### Test manuali end-to-end
- [ ] Lista transazioni visibile con filtri colonna funzionanti
- [ ] GoTo linked pair: click 🔗 → scroll + pulse su riga related
- [ ] Badge ●evt visibile su transazioni con `asset_event_id`
- [ ] `+ New` apre Staging vuota → add rows → validate → commit OK
- [ ] Clone bulk: 3 righe selezionate → `📋 Clone to staging` → Staging pre-popolata
- [ ] Edit bulk: 3 righe selezionate → `✎ Edit bulk` → Staging in mode edit → PATCH OK
- [ ] Delete bulk con conferma
- [ ] Import → upload file → parse → Staging auto-apre con BRIM data + eventi
- [ ] Asset grouping: cambio asset via `SearchSelect` globale → tutte le righe del colore aggiornate
- [ ] Split asset: 🎨 su una riga → nuovo gruppo-colore creato
- [ ] Event tolerance slider 0/7/14 → comportamento corretto
- [ ] Auto-pair TRANSFER: selezione `type=TRANSFER` su una riga → auto-crea riga coppia
- [ ] VIEWER su broker → no bottoni edit/delete/create
- [ ] Duplicati BRIM: banner + checklist funziona
- [ ] **Parte 4b**: Bottone 👁 visibile solo su file supportati
- [ ] **Parte 4b**: Preview CSV BRIM mostra `DataTable` con row-range
- [ ] **Parte 4b**: Preview immagine con quality slider funzionante
- [ ] **Parte 4b**: Preview markdown toggle raw/rendered
- [ ] **Parte 4b**: File binario → nessun bottone preview
- [ ] **Parte 4b**: Preview accessibile da Files page + `BrokerImportFilesModal`

### Test backend
- [ ] Access matrix OWNER/EDITOR/VIEWER × verb × owned/foreign broker
- [ ] `POST /brokers/{broker_id}/transactions/validate` senza side-effect
- [ ] `POST /transactions/events/suggest` tolleranze varie (0, 3, 7 giorni)
- [ ] `asset_event_id` validator rifiuta mismatch
- [ ] **Bulk TX atomic per-broker**: una riga violata → rollback totale, DB invariato, `rolled_back=True`
- [ ] **Broker mismatch**: `broker_id` item ≠ path → 400, nessun insert
- [ ] **`plugin_version`**: ogni plugin espone la property; parse cached con versione obsoleta → `parse_is_stale=true`
- [ ] Copertura ≥85% su `transaction_service` e `brim_provider`

---

## 📎 Dipendenze & Sblocca

- **Richiede**:
  - Phase 4 (Brokers + BrokerUserAccess) ✅
  - Phase 5 (FX) ✅
  - Phase 6 (Assets + AssetModal) ✅
  - Phase 6 Step 3 Round 12 (AssetEvent) ✅
  - Phase 6 Step 5 (AssetMatchingWizard) — se non pronto, fallback a `AssetModal`
- **Sblocca**: Phase 8 (Dashboard consuma transazioni + eventi per P&L e distribuzioni)

---

## 📁 Archivio previsto (post-completamento)

```
phases/phase-07-subplan/
├── README.md
├── plan-phase07-transaction-Part1.md                       (Parte 1 — ✅ completata)
├── plan-phase07-transaction-Part2.prompt.md                (Parte 2 — ✅ completata, Revisione 2)
├── plan-phase07-transaction-Part3.md                       (Parte 3 — 📋 pianificata, include 3b + deferred §8/§9)
├── plan-phase07-transaction-Part4.md                       (Parte 4 — ⏳ da scrivere)
├── plan-phase07-transaction-Part4b-filePreview.md          (Parte 4b — ⏳ da scrivere)
└── plan-phase07-transaction-Part5-staging-modal.md         (Parte 5 — ⏳ da scrivere)
```

---

**Prossimo passo**: eseguire la **Parte 3** — API Consolidation atomic per-broker + `events/suggest` + deferred da Parte 1 (vedi
[`plan-phase07-transaction-Part3.md`](../plan-phase07-transaction-Part3.md)).
Parte 1 (DB schema realignment) e Parte 2 (BRIM parser puro, Revisione 2) sono completate.
Parte 3 è pianificata in un unico file (assorbe 3b events/suggest + deferred §8 price currency + §9 OHLC sentinel) e pronta per l'implementazione.
