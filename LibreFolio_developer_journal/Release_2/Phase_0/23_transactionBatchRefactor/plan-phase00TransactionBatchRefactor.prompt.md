# Piano SP16 — scomposizione del batch transazioni

**Creato**: 2026-09-11
**Stato**: ✅ completato 2026-09-11
**Workstream**: L
**Coordinatore**: sessione `c8328a01-f208-4ade-a352-0486d1f14de2`
**Baseline approvata**: `dev_release2` @ `4949b2f4c04050e46f643de848894b6706349f34`
**Branch worktree**: `e-alfy-l-transaction-batch`
**Lane runtime**: porta `6160`, data dir `/tmp/librefolio-r2-l-batch`
**Ambito backlog**: P4-2 / SP16 / alias S6 6.8

## Autorizzazione developer

> `Sì: codice + test di caratterizzazione + docs tecniche (Consigliato)`

L'autorizzazione comprende:

1. scomposizione interna di `TransactionService.execute_batch`;
2. test di caratterizzazione prima dell'estrazione;
3. riallineamento delle docs tecniche inglesi direttamente stale.

Non autorizza cambi di contratto, policy, API, schema, frontend o modello DB.

## Obiettivo

Ridurre `backend/app/services/transaction_service.py::TransactionService.execute_batch`
da hotspot monolitico di 637 righe/C901 storico 115 a orchestratore esplicito di stage
ordinati con contesto tipizzato, senza cambiare:

- firma pubblica;
- parsing leniente e indici originali;
- ordine delle issue e dei result;
- accesso EDITOR e atomicità multi-broker;
- delete/split/update/create/promote/link;
- UUID e simmetria delle coppie;
- WAC, cost basis e replay saldi;
- `committed`, `success`/`simulated` e `success_count`;
- proprietà della transazione DB, che resta al chiamante.

## Ownership

### Produzione — writer L

- `backend/app/services/transaction_service.py`
- `backend/app/services/transaction_batch_context.py` (nuovo)
- `backend/app/services/transaction_batch_stages.py` (nuovo)

### Test — writer obbligatorio `test-author`

Solo file già registrati, per non toccare il runner condiviso:

- `backend/test_scripts/test_services/test_transaction_service.py`
- `backend/test_scripts/test_api/test_transactions_validate.py`
- `backend/test_scripts/test_api/test_transactions_api.py`
- `backend/test_scripts/test_api/test_transactions_batch_split_promote.py`
- `backend/test_scripts/test_api/test_broker_multiuser_api.py`

Gli altri test transazioni/WAC/broker restano gate read-only salvo blocker concreto.

### Docs — writer obbligatorio `docs-writer`

- `mkdocs_src/docs/developer/backend/transactions/service.md`
- `mkdocs_src/docs/developer/backend/transactions/split_promote.md`
- `mkdocs_src/docs/developer/backend/transactions/balance_validation.md`
- `mkdocs_src/docs/developer/backend/transactions/wac.md`
- `mkdocs_src/docs/developer/architecture/database/brokers_transactions.md`
- `mkdocs_src/docs/developer/lint_gates.md`

Il writer modificherà solo pagine inglesi. Nessuna traduzione automatica senza richiesta.

### Fuori scope / writer condivisi vietati

- schema/API/modelli DB;
- `broker_service.py`;
- frontend transazioni/import/onboarding;
- `asset_source.py`, Yahoo e moduli K;
- `CHANGELOG.md`, i18n, client generato;
- catalogo test, nav MkDocs, backlog/master plan.

Un blocker su queste superfici va riportato al coordinatore prima di qualunque modifica.

## Contratto corrente da congelare

Ordine reale:

1. parse leniente create → update → split → promote;
2. preload degli ID e autorizzazione;
3. delete;
4. split prima degli update dipendenti;
5. update;
6. coerenza description/tags delle coppie aggiornate;
7. create con flush per ID;
8. promote, inclusi riferimenti same-batch via UUID;
9. link resolution degli UUID non consumati;
10. WAC e issue FX;
11. cost-basis required;
12. flush e replay saldi dalla prima data toccata;
13. decisione response.

Invarianti di esito:

- access denied termina prima delle mutazioni;
- le righe parse valide continuano anche se altre righe hanno issue;
- preview pulita o sporca mantiene result `success`, poi il router esegue rollback;
- commit con issue converte i result applicati da `success` a `simulated`;
- `success_count` è calcolato prima della conversione e conta operation-result, non righe
  persistite né numero di ID;
- split/promote valgono un successo pur restituendo due ID;
- nessun nuovo stage chiama `commit`, `rollback`, `begin`, `begin_nested` o crea sessioni.

## Disegno proposto

### `transaction_batch_context.py`

Dataclass `TransactionBatchContext` con:

- raw inputs, `user_id`, `commit_requested`;
- quattro liste parse con indici originali;
- `issues`, `results`;
- broker toccati e `existing_by_id`;
- `earliest_date_by_broker`;
- `link_uuid_map`, `consumed_link_uuids`;
- `wac_results`.

I set temporanei usati da un solo stage restano locali.

### `transaction_batch_stages.py`

Funzioni focalizzate, tutte sulla stessa `TransactionService.session`:

1. `parse_inputs`
2. `preload_and_authorize`
3. `apply_deletes`
4. `apply_splits`
5. `apply_updates`
6. `validate_updated_pairs`
7. `apply_creates`
8. `apply_promotes`
9. `resolve_create_links`
10. `compute_wac_and_fx_issues`
11. `validate_cost_basis`
12. `validate_balances`
13. `finalize_response`

Il modulo usa `TYPE_CHECKING` per annotare `TransactionService` e non crea un import
runtime circolare. Gli helper privati già testati restano disponibili dal vecchio modulo.

### `TransactionService.execute_batch`

Resta orchestratore pubblico, con chiamate esplicite nell'ordine sopra. Nessun dispatch
generico per verbo e nessun catch globale che trasformi errori infrastrutturali in issue.

## Strategia test

Prima dell'estrazione, `test-author` aggiunge caratterizzazione per:

- matrice preview/commit × clean/issue;
- assenza di commit/rollback interni;
- commit fallito con result `simulated`, `success_count` invariato e zero write parziali;
- parsing realmente leniente di create raw con indici originali;
- batch misto delete + split + update + create + promote;
- split-before-update;
- permutazione `id_a`/`id_b` per split/promote;
- cardinalità e consumo UUID same-batch;
- accesso multi-broker atomico.

I test devono creare/identificare i propri dati, non usare posizioni globali, conteggi
globali o attese temporali.

## Comandi lane approvati

Ogni comando è sequenziale e usa:

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6160 --data-dir /tmp/librefolio-r2-l-batch …
```

Gate mirati:

- `services transaction`
- `services broker`
- `services edge-cases`
- `api transactions-validate`
- `api transactions`
- `api batch-split-promote`
- `api tx-balance-walk`
- `api transactions-wac`
- `api transfer-promotion`
- `api broker-multiuser`
- `api brokers`

Gate finale: `all-backend`.

Nessun `--force`, populate/reset DB, porta `6040/6041`, install o suite concorrente.

## Passi e avanzamento

### Step 0 — analisi e baseline

**Stato**: ✅ completato 2026-09-11

> **Note implementazione**: verificati HEAD esatto, tree pulito, lane libera, file e
> istruzioni tracked. Letti backlog P4-2/SP16, report archiviati, decisioni devWiki,
> servizio, chiamanti, schemi, session lifecycle, test e docs. Confermati 1.739 LOC,
> `execute_batch` 937–1573 e ordine reale a 13 sub-stage. Inviata analisi dettagliata
> al coordinatore e ricevuta autorizzazione developer verbatim.

> **⚠️ Fuori pista**: primo bootstrap del worktree era su SHA errato
> `b5ed1a623c5a6bfbd7e9563fc2327e38d470ba7c`; lavoro congelato fino al ripristino
> coordinatoriale della baseline approvata. Nessun file era stato modificato.

### Step 1 — test di caratterizzazione baseline

**Stato**: ✅ completato 2026-09-11

- invocare `test-author`;
- aggiungere test nei file registrati assegnati;
- eseguire i selettori minimi pertinenti;
- registrare risultati e detour.

> **Note implementazione**: avviato il writer specializzato obbligatorio con ownership
> limitata ai test transazioni già registrati e lane isolata 6160.

> **Note implementazione (caratterizzazione)**: `test-author` ha aggiunto test in
> `test_transaction_service.py`, `test_transactions_validate.py`,
> `test_transactions_batch_split_promote.py` e `test_broker_multiuser_api.py`.
> Sono congelati matrice commit/preview × clean/issue, ownership della transazione,
> parsing leniente e indici, rollback del commit misto, split-before-update,
> orientamento split/promote e accesso atomico multi-broker. Formattazione e ruff
> mirati verdi. Comando lane
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
> --test-port 6160 --data-dir /tmp/librefolio-r2-l-batch services transaction`:
> **68 passed**. Il runner ha creato il DB lane dalle migration; nessun reset/populate
> manuale.

> **⚠️ Fuori pista (environment, 2026-09-11)**: comando
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
> --test-port 6160 --data-dir /tmp/librefolio-r2-l-batch api
> transactions-validate` fallito durante startup backend condiviso, **prima di pytest**:
> `Shared backend exited during startup (code 1)` /
> `shared test backend failed to start`. Nessun test API raccolto; nessun source
> modificato dal comando. Creati soltanto normali artefatti ignored/log/DB lane;
> log applicativo vuoto. Nessun retry, reset, install o workaround; porta 6160 libera.
> Verdetto triage: **environment**, non test/prodotto e non “flaky”. Step 1 resta in
> corso finché il coordinatore autorizza diagnosi/retry.

> **⚠️ Fuori pista (triage autorizzato, 2026-09-11)**: ispezionati prima del retry
> `.testLog`, archivio log, run-status, DB lane e porta. Nessuna run cache attiva;
> l'archivio conserva setup Alembic verde e `services transaction` 68/68. Il DB
> `/tmp/librefolio-r2-l-batch/sqlite/app.db` supera `PRAGMA quick_check`, è alla
> migration head `5b1333fa6b07` e contiene 13 tabelle. Porta 6160 libera.
> `sqlite3 -readonly` non ha aperto il file; la lettura successiva con URI
> `mode=ro&immutable=1` è riuscita senza mutazioni.

> **⚠️ Fuori pista (unico probe startup autorizzato, 2026-09-11)**: eseguito
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py server
> --test --port 6160 --data-dir /tmp/librefolio-r2-l-batch --no-scheduler
> --no-reload`, con output completo in
> `/tmp/libreFolio_sp16_startup_probe.log`. Primo errore, prima del listener e di
> qualunque health check:
> `Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'typescript' imported from
> frontend/scripts/tools-codec-ast.mjs`. `frontend/node_modules/typescript` è assente.
> Il server ha quindi stampato `API sync failed - aborting build` /
> `Frontend build failed. Server not started.` Nessun PID in ascolto da terminare;
> porta 6160 provata libera. Il probe ha rigenerato i file API prima di fallire, ma
> `git status` conferma **zero delta tracked generated**: restano soltanto piano e
> quattro file test autorizzati. DB lane non resettato né popolato. Nessun retry del
> selettore API. Correzione proposta: bootstrap frontend con `npm ci` soltanto dopo
> autorizzazione coordinatoriale esplicita, poi nuovo startup/API gate; nessun
> `npm install/update/audit fix`.

> **Note implementazione (bootstrap autorizzato)**: ricevuta autorizzazione esplicita
> a `npm --prefix frontend ci`. Hash pre/post invariati:
> `package.json=8746adb596b239d8bbd53d7c8a8d41c34a0fa3d3c62b19934640ccdbc8686944`,
> `package-lock.json=0dbeb7bd7f3ecb0510e26a5a3ad1042aa1d46fb41248f05b1d99fa3360d67c6a`.
> Installate 433 dipendenze dal lock; `typescript` ora presente. Nessun edit a package
> o lock, nessun delta tracked oltre piano/test. L'audit informativo di `npm ci` ha
> segnalato vulnerabilità dipendenze; nessun `audit fix` eseguito perché fuori scope.

> **Note implementazione (retry unico autorizzato)**: comando identico
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
> --test-port 6160 --data-dir /tmp/librefolio-r2-l-batch api
> transactions-validate` avvia correttamente il backend condiviso e termina
> **11 passed**; inclusi parsing leniente raw e rollback del commit misto appena
> caratterizzati. Runner proprietario di startup/teardown; nessun retry ulteriore.

> **Note implementazione (chiusura Step 1)**: baseline completa sui file modificati:
> `services transaction` **68 passed**, `api transactions-validate` **11 passed**,
> `api batch-split-promote` **22 passed**, `api broker-multiuser` **14 passed**.
> `git diff --check` verde sui quattro test; runner arrestato e porta 6160 libera.
> I test di caratterizzazione precedono qualunque estrazione produzione come richiesto.

### Step 2 — contesto tipizzato

**Stato**: ✅ completato 2026-09-11

- creare `transaction_batch_context.py`;
- mantenere import e contratti privati compatibili;
- validare staticamente e con service tests.

> **Note implementazione**: creato `TransactionBatchContext` con input normalizzati e
> stato cross-stage tipizzato (parsed rows, issue/result, broker/righe esistenti, date
> replay, UUID consumati e WAC). Black e ruff sul modulo: verdi. Gate
> `services transaction`: **68 passed**.

### Step 3 — parse/preload/access

**Stato**: ✅ completato 2026-09-11

- estrarre stage read/authorization;
- preservare ordine issue ed early return access denied;
- rieseguire caratterizzazione mirata.

> **⚠️ Fuori pista (static gate)**: primo black+ruff dopo il wiring ha riformattato
> soltanto `transaction_batch_stages.py`, poi ruff ha fermato il gate con cinque import
> inutilizzati e `preload_and_authorize` C901=16. Nessun test/runtime avviato. Correzione
> scelta: rimuovere gli import, marcare esplicitamente il re-export testato di
> `_parse_lenient` e scomporre il preload in helper read/access; vietato trasferire il
> vecchio hotspot in un nuovo stage.

> **Note implementazione**: `_parse_lenient` spostato e re-esposto dal modulo storico;
> `parse_inputs` conserva ordine create/update/split/promote; preload separato in
> raccolta ID, bulk load, re-fetch difensivo split e access issue. Early return identico.
> Corretto il primo gate statico: black+ruff verdi, nessun C901 nel nuovo preload.
> Gate dopo estrazione: `services transaction` **68 passed**,
> `api transactions-validate` **11 passed**, `api broker-multiuser` **14 passed**.

### Step 4 — delete/split/update

**Stato**: ✅ completato 2026-09-11

- estrarre mutazioni su righe esistenti;
- preservare split-before-update, pair integrity, timestamp e prima data di replay;
- rieseguire service, validate, split e access gates.

> **⚠️ Fuori pista (static gate)**: dopo l'estrazione meccanica black ha formattato il
> nuovo modulo; ruff ha rilevato `apply_updates` C901=17, due import stale e un alias
> locale non più usato. Nessun runtime avviato. Nessuna soppressione aggiunta: il mapping
> update viene diviso in helper type/date, valori, event link e validazione final-state.

> **Note implementazione**: estratti `apply_deletes`, `apply_splits`, `apply_updates`
> e `validate_updated_pairs`. Update ulteriormente separato in helper focalizzati, così
> il nuovo modulo resta senza C901. Conservati delete pair check, orientamento per segno,
> split-before-update, final-state validation, event link e pair metadata. Black+ruff
> verdi. Gate: `services transaction` **68 passed**, `api transactions-validate`
> **11 passed**, `api batch-split-promote` **22 passed**, `api broker-multiuser`
> **14 passed**.

### Step 5 — create/promote/link

**Stato**: ✅ completato 2026-09-11

- preservare flush per create, ID e mappe UUID;
- preservare promote same-batch e link UUID consumati;
- verificare simmetria e result ordering.

> **Note implementazione**: estratti `apply_creates`, `apply_promotes` e
> `resolve_create_links`; promote diviso in risoluzione ref, merge campi e cost basis.
> Conservati flush per riga, ID, orientamento result, UUID consumati, regole metadata,
> link reciproci e issue count. Black+ruff verdi; nessun nuovo C901. Gate:
> `services transaction` **68 passed**, `api batch-split-promote` **22 passed**,
> `api transactions` **22 passed, 1 skipped** (skip preesistente del caso linked-delete).

### Step 6 — WAC/cost basis/balance/finalizer

**Stato**: ✅ completato 2026-09-11

- mantenere helper WAC e stessa session visibility;
- preservare issue FX, split-linked skip e cost-basis receiver;
- preservare replay EOD, attribution e first-error behavior;
- preservare matrice response/status/count.

> **Note implementazione**: spostato `BalanceValidationError` nel modulo context e
> re-esposto dal servizio storico; estratti WAC/issue FX, tre rami cost basis, replay
> saldi e finalizer response. Conservati flush, same-session visibility, skip su issue,
> first balance error, mapping ID→operation/index, `success_count` pre-conversione e
> status `simulated` solo sul commit fallito. Black+ruff verdi. Gate:
> `services transaction` **68 passed**, `api transactions-validate` **11 passed**,
> `api batch-split-promote` **22 passed**, `api tx-balance-walk` **9 passed**,
> `api transactions-wac` **14 passed**.

### Step 7 — orchestratore e qualità

**Stato**: ✅ completato 2026-09-11

- ridurre `execute_batch` a sequenza esplicita;
- rimuovere il suo marker C901/TODO senza creare un nuovo mega-stage;
- eseguire lint/format con skill di progetto e `git diff --check`;
- review semantica completa del diff.

> **Note implementazione**: `execute_batch` ora è un orchestratore esplicito di
> **50 righe AST** (prima 637), firma invariata byte-per-byte salvo rimozione del
> commento `noqa/TODO`. Docstring aggiornata all'ordine reale e alla ownership del
> chiamante. Black, ruff normale, ruff `--select C901` e `git diff --check` verdi.
> Nessuna occorrenza di `.commit()`, `.rollback()`, `.begin()` o `begin_nested()` nei
> tre file produzione owned. Review scope: solo servizio, due moduli nuovi, quattro
> test e piano. Gate caller aggiuntivi: `services broker` **33 passed**,
> `services edge-cases` **17 passed**, `api transfer-promotion` **3 passed**,
> `api brokers` **29 passed**.

### Step 8 — docs tecniche inglesi

**Stato**: ✅ completato 2026-09-11

- invocare `docs-writer`;
- riallineare ordine, transaction ownership, split/promote e WAC;
- build MkDocs strict e link check se richiesti dal writer;
- nessun edit a traduzioni/nav.

> **Note implementazione**: `docs-writer` ha riallineato le sei pagine inglesi owned:
> service architecture, split/promote, balance validation, WAC, database transactions e
> lint gates. Corretti stage/order, context, `committed` response, transaction ownership,
> promote in-place vs endpoint legacy, UUID transiente, WAC create/update e replay EOD.
> Verificati 637→50 righe, C901 suppression 202→201 e TODO refactor 25→24 rispetto a
> HEAD. `mkdocs build` strict verde; `mkdocs check-links`: **12 valid, 0 invalid**;
> `git diff --check` docs verde; 12 source path esistenti. Pagine EN-only senza
> controparti tradotte: nessuna traduzione, stamp o debito.

### Step 9 — gate finali e handoff

**Stato**: ✅ completato 2026-09-11

- eseguire tutti i gate mirati;
- eseguire `all-backend`;
- provare porta 6160 libera;
- verificare solo path approvati e nessun artefatto runtime;
- inviare handoff finale e tornare `FROZEN`.

> **Note implementazione**: full lint `dev.py lint` verde e `git diff --check` verde.
> Tutti i gate mirati approvati sono verdi: service transaction/broker/edge-cases;
> API transactions-validate, transactions, batch-split-promote, tx-balance-walk,
> transactions-wac, transfer-promotion, broker-multiuser e brokers. Gate finale
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
> --test-port 6160 --data-dir /tmp/librefolio-r2-l-batch all-backend`:
> **7/7 categorie passate — ALL BACKEND TESTS PASSED**, durata invocazione 13m28s.
> Porta 6160 libera dopo teardown. Hash finali package/lock identici alla baseline
> pre-bootstrap; nessun manifest modificato. Tree contiene esclusivamente produzione,
> test, docs e piano approvati; `node_modules`, `.testLog`, DB/log/snapshot lane restano
> ignored/runtime e non sono candidati al checkpoint.

> **Note implementazione (handoff)**: nessun file staged, nessun commit/push/rebase/reset.
> Messaggio Conventional Commit proposto:
> `refactor(transactions): split batch pipeline stages`.

## Definition of done

- `execute_batch` non è più hotspot C901/TODO ed espone ordine leggibile;
- nessun cambio a firma, schema o payload/response;
- stessa atomicità, access control, issue/result/index ordering;
- preview e commit fallito non persistono;
- nessun commit/rollback/savepoint nei nuovi stage;
- split/promote/link/WAC/cost basis/saldi equivalenti;
- test di caratterizzazione e gate esistenti verdi;
- docs inglesi coerenti col codice;
- `git diff --check` verde, porta 6160 libera;
- nessuna staging/commit/history mutation.
