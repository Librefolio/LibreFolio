# Piano Phase 00 — SP08 Asset pricing e confini del servizio

**Creato:** 2026-09-11
**Workstream:** K — SP08
**Coordinator:** sessione `c8328a01-f208-4ade-a352-0486d1f14de2`
**Worktree:** `/Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-fuzzy-fishstick`
**Branch:** `e-alfy-asset-pricing-boundaries`
**Baseline approvata:** `dev_release2` @ `4949b2f4c04050e46f643de848894b6706349f34`
**Corsia runtime:** porta `6159`, data dir assoluta `/tmp/librefolio-r2-k-pricing`
**Autorizzazione developer ricevuta verbatim:** `Sì: piano K completo raccomandato`

## Obiettivo

Chiudere SP08 senza cambiare contratti di prodotto:

1. ridurre `YahooFinanceProvider.get_history_value` separando acquisizione, mapping
   DataFrame e parsing dividendi/split;
2. scindere `backend/app/services/asset_source.py` per responsabilità;
3. estrarre le fasi PREPARE/FETCH/PERSIST di `bulk_refresh_prices`;
4. mantenere una facciata legacy sottile e permanente per Release 2;
5. preservare identità di cache/thread/errori, import pubblici, auto-discovery,
   transazioni, commit a chunk, query DB-only, write-back delle quote correnti,
   invalidazioni, ricerca e risultati parziali.

## Scope e ownership

### Produzione posseduta

- `backend/app/services/asset_source.py`
- `backend/app/services/asset_sources/**`
- `backend/app/services/asset_source_providers/yahoo_finance.py`

### Test posseduti tramite `test-author`

- `backend/test_scripts/test_services/test_yahoo_finance_errors.py`
- `backend/test_scripts/test_services/test_asset_source.py`
- `backend/test_scripts/test_services/test_asset_source_refresh.py`
- `backend/test_scripts/test_services/test_asset_source_upsert_guards.py`
- `backend/test_scripts/test_utilities/test_provider_core_cache.py`
- `backend/test_scripts/test_api/test_current_price_persistence.py`

### Documentazione posseduta tramite `docs-writer`

- `mkdocs_src/docs/developer/backend/assets/architecture.md`
- `mkdocs_src/docs/developer/architecture/patterns/asset_plugin_guide.md`
- `mkdocs_src/docs/developer/backend/assets/search_link_finder.md`
- `mkdocs_src/docs/developer/architecture/patterns/async.md`
- verifica puntuale di
  `mkdocs_src/docs/developer/backend/assets/provider_yahoo_finance.md`

### Fuori scope / vietato

- frontend, i18n, client API generato, schema/API/DB/migrazioni;
- `CHANGELOG.md`, backlog master, MkDocs nav, test runner condiviso;
- superfici D portfolio/PAC, I Asset detail/PriceChart, J onboarding;
- `transaction_service.py` e helper L;
- refactor FX, BRIM o provider asset diversi da Yahoo;
- normalizzazione delle forme cache key o dei `source_plugin_key` correnti;
- chiusura implicita del marker C901 di `get_prices_bulk`.

## Architettura destinazione

Package canonico `backend/app/services/asset_sources/`:

| Modulo | Responsabilità |
|---|---|
| `core.py` | `AssetSourceError`, tipi/sentinelle, cinque cache singleton, hash params, sanitizzazione errori, thread isolation, guardia OHLC, `AssetSourceProvider` |
| `provider_management.py` | assign/remove/get assignment, wipe parametrici, probe provider |
| `metadata.py` | refresh metadata e applicazione patch via CRUD canonico |
| `price_store.py` | upsert/delete prezzi/eventi, wipe valuta, chunk/commit, helper OHLC |
| `price_query.py` | backward fill, capability, `get_prices_bulk` DB-only, quote correnti + write-back |
| `refresh.py` | orchestrazione refresh e fasi PREPARE/FETCH/PERSIST |
| `crud.py` | `AssetCRUDService` |
| `search.py` | `AssetSearchService`, cache query, link-finder, SSE |
| `manager.py` | unica identità `AssetSourceManager`, composizione dei metodi |
| `__init__.py` | export canonici |

`backend/app/services/asset_source.py` resta facciata legacy: re-export degli stessi
oggetti, mai sottoclassi o copie. I moduli foglia non importano manager/facciata.
Tutti gli accessi runtime a cache e thread passano da `core.<nome>` per conservare
identità e monkeypatch canonico.

## Invarianti obbligatorie

- Provider sync I/O diretto dentro Yahoo; nessun `asyncio.to_thread` nel provider.
- `_run_provider_in_thread` è l'unico confine thread del manager.
- Guardia OHLC applicata una sola volta via `AssetSourceProvider.__init_subclass__`.
- `start_date="min"` Yahoo usa `history(period="max")`.
- Range finiti Yahoo: start incluso, end incluso tramite end remoto + 1 giorno.
- NaN Close scartato; NaN OHLC/volume opzionale → `None`; valuta fallback USD.
- Errori Yahoo tipizzati; dividendi e split best-effort indipendenti.
- `get_prices_bulk` non chiama provider e conserva warm-up/FX/eventi/segnali/slicing.
- `/prices/current` conserva fallback DB e persistenza OHLC odierna.
- PREPARE usa sessione condivisa read-only; FETCH non usa DB; PERSIST usa una
  `AsyncSession` distinta per asset.
- Chunk `PRICE_UPSERT_CHUNK_SIZE=1000`, commit intermedi e verità dei risultati
  parziali invariati.
- Nessuna falsa atomicità: prezzi, eventi e `last_fetch_at` restano commit separati.
- Auto-discovery continua a scansionare `asset_source_providers/`.
- CRUD/merge/delete, ricerca, link-finder, SSE e invalidazioni restano equivalenti.

## Passi e checkpoint

### Passo 0 — baseline, istruzioni, analisi e autorizzazione

- [x] Completato il 2026-09-11.

> **Note implementazione**: letti contratto coordinated-workstream, istruzioni backend,
> provider asset e test; caricati `asset-plugin` e `wiki-search`; verificati backlog,
> report archiviati e codice corrente. Baseline ripristinata e ricontrollata:
> HEAD esatto `4949b2f4c04050e46f643de848894b6706349f34`, worktree pulito,
> porta 6159 libera. Ricevuta autorizzazione developer verbatim. Branch rinominata
> tramite tool app-native prima di qualsiasi file.

### Passo 1 — caratterizzazione offline con `test-author`

- [x] Aggiungere copertura Yahoo per kwargs finiti/min, retry history, mapping NaN,
  date/UTC, errori tipizzati, indipendenza dividendi/split.
- [x] Sostituire introspezione fragile del probe con prova comportamentale.
- [x] Definire test identità legacy/canonico e punti monkeypatch privati;
  implementarli al Passo 3, quando il package canonico esiste.
- [x] Eseguire solo i selettori minimi autorizzati nella corsia K.

> **Note implementazione**: `test-author` ha esteso
> `test_yahoo_finance_errors.py` con caratterizzazione offline dei kwargs remoti,
> retry senza attesa reale, mapping NaN, range UTC/inclusivo, fallback valuta e
> indipendenza dividendi/split. In `test_provider_core_cache.py` l'asserzione
> `inspect.getsource` è stata sostituita da una prova comportamentale del bypass
> cache e del passaggio nel confine thread. Il selettore
> `services provider-errors yahoo` ha chiuso con **40 passed, 84 deselected**.
>
> **⚠️ Fuori pista**: il comando autorizzato
> `... test --test-port 6159 --data-dir /tmp/librefolio-r2-k-pricing utilities provider-core-cache`
> è fallito in parsing CLI, prima della collection, con
> `invalid choice: 'utilities'`. Nessun server avviato e nessun test/DB setup
> raggiunto da quell'invocazione. La categoria registrata reale è `utils`; il
> piano e i comandi successivi sono corretti a `utils provider-core-cache`.
> Il primo comando ha creato il DB di corsia sotto il path macOS canonico
> `/private/tmp/librefolio-r2-k-pricing/sqlite/app.db`, equivalente al path
> assegnato `/tmp/librefolio-r2-k-pricing`.
>
> **Note implementazione**: rieseguito il selettore corretto
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
> --test-port 6159 --data-dir /tmp/librefolio-r2-k-pricing utils
> provider-core-cache`: **20 passed**. Nessun server avviato. La futura
> migrazione dei patch target privati e le asserzioni d'identità restano
> intenzionalmente nel Passo 3, perché prima del package canonico non sono
> esprimibili senza rendere rossa la baseline.

### Passo 2 — refactor Yahoo locale

- [x] Estrarre acquisizione history/currency/event series.
- [x] Estrarre mapping puro DataFrame → punti.
- [x] Estrarre parser dividendi e split indipendenti.
- [x] Correggere commenti `_sync_fetch_history` obsoleti.
- [x] Verificare parità offline.

**Checkpoint A:** Yahoo + caratterizzazione verdi, nessuna modifica manager.

> **Note implementazione**: in `yahoo_finance.py` aggiunti
> `_YahooHistoryAcquisition`, `_acquire_history_data`,
> `_map_history_prices`, `_parse_dividend_events`,
> `_parse_split_events` e normalizzazione data condivisa. Il metodo pubblico
> conserva validazione, confine errori e costruzione `FAHistoricalData`; nessun
> `to_thread` o cache prezzo nel provider. Le acquisizioni e i parser evento
> falliscono indipendentemente in best-effort.
>
> **Evidenza**:
> `black` sui tre file del checkpoint + `ruff check` → verde;
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
> --test-port 6159 --data-dir /tmp/librefolio-r2-k-pricing services
> provider-errors yahoo` → **40 passed, 84 deselected**. Checkpoint A chiuso.

### Passo 3 — core canonico e facciata

- [x] Creare package e `core.py`.
- [x] Spostare provider ABC/guardia/cache/thread senza duplicare identità.
- [x] Creare facciata legacy e testare identità/import/discovery.

> **Note implementazione**: creato `backend/app/services/asset_sources/`;
> `core.py` è l'unico owner di errori, sentinelle, cinque cache, thread runner,
> guardia OHLC e ABC. `asset_source.py` è ridotto a facciata di 36 righe.
> `manager.py` compone un'unica classe da mixin di responsabilità.
> Test di identità legacy/canonico, discovery in interprete fresco e singolo
> wrapper OHLC aggiunti da `test-author`.
>
> **Evidenza**: import smoke con discovery Yahoo verde; `ruff check` verde;
> `utils provider-core-cache` → **33 passed**.

### Passo 4 — CRUD, search, provider management, metadata

- [x] Muovere `AssetCRUDService` meccanicamente.
- [x] Muovere `AssetSearchService` meccanicamente.
- [x] Muovere provider assignment/probe.
- [x] Muovere refresh metadata.
- [x] Comporre unica classe `AssetSourceManager`.
- [x] Verificare test mirati.

**Checkpoint B:** responsabilità non-pricing estratte e import compatibili.

> **Note implementazione**: corpi trasferiti senza riscrittura algoritmica in
> `crud.py`, `search.py`, `provider_management.py`, `metadata.py`. Dipendenza
> metadata → CRUD esplicita; moduli foglia non importano manager/facciata.
> Private monkeypatch migrati ai moduli canonici; import pubblici restano sulla
> facciata per testare compatibilità Release 2.
>
> **Evidenza**: `services asset-source` → **61 passed**;
> `services web-link-finder` → **24 passed**;
> `services scheduled-investment-param-change` → **3 passed**;
> `db asset-merge` → **12 passed**.

### Passo 5 — price store e query

- [x] Muovere storage prezzi/eventi/wipe con commit e chunk invariati.
- [x] Muovere query/backward fill/capability.
- [x] Muovere quote correnti preservando write-back odierno.
- [x] Lasciare esplicito e aperto il marker C901 di `get_prices_bulk`.
- [x] Migrare monkeypatch privati ai moduli canonici.
- [x] Verificare servizi/API mirati.

> **Note implementazione**: storage e query trasferiti rispettivamente in
> `price_store.py` e `price_query.py`; `PRICE_UPSERT_CHUNK_SIZE` resta 1000.
> Cache/thread sono sempre dereferenziati da `core`, quindi un solo oggetto e
> un solo patch point. `get_prices_bulk` conserva il marker P2 e il corpo
> multi-pass; quote correnti conservano cache key a tre elementi, source tag
> `provider:<code>` e write-back odierno.
>
> **Evidenza**: `services asset-source-guards` → **22 passed**;
> `services asset-signals` → **18 passed**;
> `api current-price-persistence` → **5 passed**.
>
> **⚠️ Fuori pista**: il primo tentativo API è fallito prima della collection
> perché mancavano `frontend/build` e dipendenze frontend. Il coordinator ha
> autorizzato verbatim il solo bootstrap `npm --prefix frontend ci` dal lock
> committato. Hash pre/post invariati:
> `frontend/package.json`
> `8746adb596b239d8bbd53d7c8a8d41c34a0fa3d3c62b19934640ccdbc8686944`,
> `frontend/package-lock.json`
> `0dbeb7bd7f3ecb0510e26a5a3ad1042aa1d46fb41248f05b1d99fa3360d67c6a`.
> Nessun file tracked frontend modificato; solo `node_modules/` e `.svelte-kit/`
> ignorati. Il singolo retry autorizzato è poi passato 5/5. `npm ci` ha
> segnalato 20 vulnerabilità del lock esistente; nessun audit-fix/update eseguito.

### Passo 6 — refresh: trasloco meccanico

- [x] Muovere `bulk_refresh_prices` in `refresh.py` con closure e dict invariati.
- [x] Eseguire gate refresh prima di qualunque estrazione.

**Checkpoint C-meccanico:** refresh verde nella nuova sede, algoritmo ancora identico.

> **Note implementazione**: `bulk_refresh_prices` trasferito inizialmente
> verbatim in `refresh.py`; closure/dict/sessioni originali ancora intatti.
> Il checkpoint è avvenuto prima di introdurre record tipizzati o helper.
>
> **Evidenza**: `services asset-source-refresh` → **12 passed**;
> `services asset-sync-counts` → **1 passed**;
> `api prices-sync-delta` → **5 passed** (inclusi cap 500 e idempotenza).

### Passo 7 — refresh: fasi tipizzate

- [x] Introdurre record privati tipizzati con soli dati necessari.
- [x] Estrarre PREPARE.
- [x] Estrarre FETCH item/batch.
- [x] Estrarre confronto e PERSIST item/batch.
- [x] Eliminare closure annidate e marker P2 del refresh, non quello della query.
- [x] Verificare sessioni, timeout, cache, delta, errori e commit.

**Checkpoint C-finale:** S6 6.4 chiuso con parità.

> **⚠️ Fuori pista**: primo lancio del codemod locale
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python
> .copilot_extract_refresh_phases.py` terminato prima della scrittura con
> `RuntimeError: Expected one occurrence, found 0: '        session,\\n'`.
> Causa: `textwrap.dedent` aveva ridotto l'indentazione della firma estratta.
> Nessun file produzione, DB o server toccato dal lancio fallito; corretto il
> match esatto prima di riprovare.
>
> **Note implementazione**: `refresh.py` ora usa i record frozen
> `_PreparedRefreshItem` (solo ID/primitivi/provider, nessun ORM oltre PREPARE)
> e `_FetchedRefreshData`. Estratti `_prepare_refresh_items`,
> `_fetch_refresh_item(s)`, `_count_actual_price_changes` e
> `_persist_refresh_item(s)`. Il metodo pubblico è un orchestratore breve.
> PREPARE usa la sessione chiamante solo in lettura; FETCH non riceve sessioni;
> PERSIST crea una `AsyncSession` distinta per asset. Timeout/semaforo,
> cache key, resume/min, filtro valuta, `changed_points`, commit prezzi/eventi e
> commit separato `last_fetch_at` sono invariati. Rimossi i marker P2 e le
> closure refresh; `get_prices_bulk` resta esplicitamente aperto.
>
> **Evidenza**: Black + Ruff verdi (`_prepare_refresh_items` mantiene una
> soppressione C901=11 motivata dalla mappatura lineare degli esiti);
> `services asset-source-refresh` → **12 passed**;
> `services asset-sync-counts` → **1 passed**;
> `api prices-sync-delta` → **5 passed**.
> `git diff --check` verde e porta 6159 libera. Checkpoint C-finale chiuso.

### Passo 8 — documentazione tecnica con `docs-writer`

- [x] Aggiornare mappa moduli e facciata.
- [x] Correggere la guida plugin: nessun `to_thread` dentro provider.
- [x] Aggiornare path search/thread.
- [x] Verificare Yahoo senza documentare cambi comportamento inesistenti.
- [x] Nessuna nav/traduzione.

> **Note implementazione**: `docs-writer` ha riallineato le cinque pagine
> tecniche approvate: mappa package/facciata e responsabilità query/store/refresh,
> regola thread provider corretta, path search canonico e helper Yahoo con
> contratto pubblico invariato. Nessuna modifica a nav, traduzioni, user docs o
> changelog.
>
> **Evidenza**:
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py
> mkdocs build` → exit 0, build 21.03 s;
> `... dev.py mkdocs check-links` → exit 0, **12 valid links**;
> `git diff --check` verde.

### Passo 9 — gate finali e handoff

- [x] Lint/format mirati secondo skill.
- [x] Test mirati completi.
- [x] Escalation `services all` e `api all` solo dopo il verde mirato.
- [x] Review manuale import/cache/session/commit.
- [x] `git diff --check`.
- [x] Arresto risorse e prova porta 6159 libera.
- [x] Handoff strutturato al coordinator; stato FROZEN.

> **Note implementazione**: review read-only dedicata sul diff SP08: nessun
> problema significativo trovato. Completata la matrice mirata restante,
> sempre sequenziale nella corsia 6159:
> `provider-registry` 7, `provider-contracts` 397,
> `current-price-bootstrap` 8, `scheduler-jobs` 20,
> `assets-price` 18, `assets-provider` 24, `assets-metadata` 13,
> `assets-events` 13, `assets-crud` 32, `market-data-wipe` 5,
> `asset-currency-change` 4, `asset-merge` API 7,
> `search-to-prices` E2E 3 — tutti passed. Log completo:
> `/tmp/libreFolio_sp08_targeted.log`.
>
> **⚠️ Fuori pista**: prima escalation `services all` terminata con
> **1 failed, 3846 passed**. Unico rosso:
> `TestImportCycleSafety::test_fresh_process_end_to_end_registry_construction_still_works`.
> Il subprocess costruiva correttamente i registry (`67 40 11`) ma cinque log DEBUG
> di creazione cache precedevano l'output. Triage: **defect**, non flakiness né
> stato condiviso. La scissione aveva rimosso dal core l'import incidentale di
> `signal_service` che, nel monolite, inizializzava `logging_config` prima di
> `get_ttl_cache`; senza bootstrap esplicito, structlog usava il PrintLogger.
> Correzione: il core deve usare direttamente il logger progetto
> `backend.app.logging_config.get_logger`, rendendo esplicito l'ordine senza
> reintrodurre dipendenze signals. Log completo:
> `/tmp/libreFolio_sp08_services_all.log`.
>
> **Note implementazione**: applicato il bootstrap logger esplicito in `core.py`;
> il probe fresh-process stampa di nuovo solo `67 40 11`. Il test rosso mirato
> è passato **1 passed, 921 deselected**. La ripresa `--resume services all`
> ha rieseguito l'unità AI Export completa: **922 passed**; combinata con
> **3846 passed** della prima esecuzione, tutti i servizi risultano verdi.
> `api all` ha chiuso con **674 passed, 3 skipped**. Black `--check` sui 18 file
> Python modificati/nuovi, Ruff mirato e `git diff --check` sono verdi.
> Review dedicata: nessun problema significativo. Build MkDocs e link check
> verdi come registrato al Passo 8. HEAD resta
> `4949b2f4c04050e46f643de848894b6706349f34`; manifest/lock frontend conservano
> gli hash pre-bootstrap; porta 6159 libera. Nessun file staged, nessun commit
> o mutazione history.

## Comandi test autorizzati

Ogni comando usa:

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py test \
  --test-port 6159 \
  --data-dir /tmp/librefolio-r2-k-pricing \
  <categoria> <azione>
```

Selettori previsti, sempre sequenziali:

- `services provider-errors yahoo`
- `utils provider-core-cache`
- `services asset-source`
- `services asset-source-refresh`
- `services asset-source-guards`
- `services asset-sync-counts`
- `services provider-registry`
- `services provider-contracts`
- `services current-price-bootstrap`
- `services scheduled-investment-param-change`
- `services web-link-finder`
- `services asset-signals`
- `services scheduler-jobs`
- `api assets-price`
- `api assets-provider`
- `api assets-metadata`
- `api assets-events`
- `api assets-crud`
- `api current-price-persistence`
- `api prices-sync-delta`
- `api market-data-wipe`
- `api asset-currency-change`
- `api asset-merge`
- `db asset-merge`
- `e2e search-to-prices`

Il test live `external asset-providers --providers yfinance` non è prova di parità e
non si esegue senza richiesta developer separata.

## Definition of Done

- facciata legacy sottile; package canonico per responsabilità;
- stessa identità per classi, errori, cache e thread;
- Yahoo equivalente, testato offline;
- refresh con fasi esplicite e sessioni corrette;
- import produzione esistenti invariati;
- nessun cambio schema/API/frontend/DB/changelog/runner;
- documentazione inglese coerente;
- gate mirati e integrati verdi;
- porta 6159 libera e workstream FROZEN al handoff.
