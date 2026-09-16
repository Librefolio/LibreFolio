# Step 1 Round 1 — capacità generica della piattaforma Tool

**Stato:** FROZEN — backend handoff pronto.
**Data:** 2026-09-16.
**Baseline iniziale:** `941834237696f32bbabfde62a08e070e4b23758e`.
**Baseline corrente autorizzata:** `22cb18d1d60c8b1197627e6e8eff9cb55f001d3e`
(parent `941834237696f32bbabfde62a08e070e4b23758e`; commit exact-core
disgiunto).
**Branch:** `e-alfy-allocatore-pac`.
**Lane riservata:** porta `6153`, data dir `/tmp/librefolio-r2-d`, venv
`LibreFolio-SAUMUTtc`.
**Coordinator:** `c8328a01-f208-4ade-a352-0486d1f14de2`.

← Master:
[PAC & Rebalancer — piano implementativo](plan-phase00PacRebalancerImplementation.prompt.md)
← Parent:
[Step 1 — contratti pubblici, dipendenza SCIP e capacità](plan-phase00Step1PacRebalancerContractsCapacity.prompt.md)

## 1. Scopo

Estendere in modo additivo la piattaforma Tool per operazioni lunghe senza
modificare il comportamento delle operazioni ordinarie. La piattaforma deve
fornire:

- policy effettive per operazione;
- budget engine e riserva post-engine generici;
- deadline request/client derivate dal massimo della policy effettiva del batch;
- limite memoria per l'intero albero di processo;
- enforcement hard solo tramite cgroup v2 realmente delegato e scrivibile;
- fallback osservato su macOS/Linux non delegato, mai descritto come hard;
- metriche risorsa tipizzate e diagnostics sanitizzati;
- rilascio lane/credito soltanto dopo la prova di albero e containment vuoti.

Non appartengono a questo round plugin/schema/numerica/UI PAC, test, runner,
generated client, documentazione, i18n o changelog.

## 2. Contratto congelato

| Budget | Default operazione ordinaria | Ceiling piattaforma |
|---|---:|---:|
| queue | 5 000 ms | 5 000 ms |
| engine | 4 000 ms | 30 000 ms |
| soft wall | 4 000 ms | 44 000 ms |
| hard wall | 5 000 ms | 45 000 ms |
| cleanup | 2 000 ms | 5 000 ms |
| request | 20 000 ms | 59 000 ms |
| client | 25 000 ms | 65 000 ms |
| output reserve | — | 1 000 ms |
| memoria per job | 1 GiB | 1 GiB |

Due lane attive riservano al massimo 2 GiB. Il batch usa il massimo dei budget
request/client effettivi, non la somma. Ogni item conserva queue, hard, soft,
cleanup e memoria propri. Quattro item lunghi su due lane conservano il timeout
di coda comune a 5 secondi: la seconda wave può fallire `queue_timeout`.

## 3. Ownership

Writer esclusivo:

- `backend/app/schemas/tools.py`;
- `backend/app/services/tools/base.py`;
- `backend/app/services/tools/catalog.py`;
- `backend/app/services/tools/worker.py`;
- `backend/app/services/tools/process_tree.py`;
- `backend/app/services/tools/executor.py`;
- `backend/app/api/v1/tools.py`;
- eventuale nuovo `backend/app/services/tools/resources.py`.

Questo round non modifica superfici condivise/generate possedute da D-main.

## 4. Sequenza

- [x] Slice 1 — DTO policy/risorse strict e clamp effettivo. ✅ 2026-09-16
  > **Note implementazione**: aggiunti ceiling piattaforma, override
  > per-operazione con default ordinari invariati, `memory_limit`, metriche
  > risorsa nested, capability memoria e reservation pool tipizzate.
  > `effective_operation()` applica tutti i clamp e rifiuta un envelope
  > request incapace di contenere ingress, queue, hard wall, cleanup e response.
  > **Evidenza**:
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -c
  > "import ast,pathlib; ..."` → `AST OK: slice 1`;
  > `git diff --check -- backend/app/schemas/tools.py
  > backend/app/services/tools/catalog.py` → exit `0`.
- [x] Slice 2 — finestra engine generica e propagazione deadline per operazione. ✅ 2026-09-16
  > **Note implementazione**: `ToolExecutionContext` espone
  > `remaining_soft_ms()` e `claim_engine_window(post_engine_reserve_ms=...)`;
  > l'engine non parte se soft wall residua non contiene budget engine e
  > riserva chiamante. `ToolWorkerJob` trasporta il budget. Executor deriva
  > request outer dal massimo degli item validi e usa cleanup per-operazione
  > per queue cap, hard cap, await e shutdown.
  > **Evidenza**:
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -c
  > "import ast,pathlib; ..."` → `AST OK: slice 2`;
  > `git diff --check -- backend/app/services/tools/base.py
  > backend/app/services/tools/worker.py
  > backend/app/services/tools/executor.py` → exit `0`.
- [x] Slice 3 — cgroup v2 hard e monitor osservato process-tree. ✅ 2026-09-16
  > **Note implementazione**: aggiunto controller risorsa isolato. La modalità
  > `cgroup_v2_hard` viene esposta solo dopo prova di cgroup v2, controller
  > memoria abilitato, parent delegato/scrivibile, creazione gruppo job e
  > readback esatto di `memory.max`. Il PID root viene collegato prima
  > dell'ACK che abilita il plugin; `memory.events` rileva OOM. In assenza di
  > delegation, il supervisor campiona RSS dell'albero/process group ogni
  > massimo 50 ms e dichiara `process_tree_observed`. Cleanup e lane release
  > richiedono processo, process group e cgroup vuoti.
  > **Evidenza**:
  > AST dei quattro file Slice 3 → `AST OK: slice 3`;
  > `git diff --check` scoped → exit `0`;
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run ruff check
  > backend/app/services/tools/resources.py
  > backend/app/services/tools/process_tree.py
  > backend/app/services/tools/worker.py
  > backend/app/services/tools/executor.py` → `All checks passed!`.
  > **Fuori pista — 2026-09-16**:
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run ruff check
  > backend/app/services/tools/resources.py
  > backend/app/services/tools/process_tree.py
  > backend/app/services/tools/worker.py
  > backend/app/services/tools/executor.py` → exit `1` durante lint statico:
  > ordine import in `executor.py`, `B904` e `C901` in `process_tree.py`.
  > Nessuna collection/setup/test; nessun DB, file runtime o server toccato.
  > Correzione confinata ai file già in lease.
- [x] Slice 4 — lifecycle/reservation/metriche/API diagnostics e request budget. ✅ 2026-09-16
  > **Note implementazione**: executor riserva memoria per job attivo,
  > propaga limiti engine/memoria, campiona durante I/O, conserva metriche
  > risorsa dopo cleanup e mette in quarantena lane/subtree non svuotati.
  > `memory_limit` prevale su result/crash quando osservato; cleanup fallito
  > resta `cleanup_failed`. Snapshot espone capacità e reservation in byte.
  > API rischedula compute sul massimo `request_timeout_ms` effettivo del
  > batch, mantiene 20 s per catalog/diagnostics e pubblica capability
  > sanitizzata ottenuta off event loop. Budget queue/hard restano per item.
  > **Evidenza**: inclusa nel gate statico complessivo sotto.
  > **Fuori pista — 2026-09-16**: dopo l'integrazione API, verifica
  > obbligatoria baseline:
  > `git rev-parse HEAD && git branch --show-current` →
  > `22cb18d1d60c8b1197627e6e8eff9cb55f001d3e`,
  > `e-alfy-allocatore-pac`; baseline autorizzata
  > `941834237696f32bbabfde62a08e070e4b23758e`.
  > Stop condition attivata prima di Black/gate finale. Nessun test/runtime,
  > DB o server avviato; nessuno staging/history mutation eseguito dal writer.
  >
  > **Risoluzione — 2026-09-16**: coordinatore ha attestato che `22cb18d`
  > contiene soltanto exact-core numerico, relativi test/selector e piano Step
  > 2, senza overlap con il lease Tool. Verifica locale:
  > `git rev-parse HEAD`, `git branch --show-current`,
  > `git diff --cached --name-only`, `git show --stat --oneline --summary
  > HEAD` → SHA/branch attesi, staged `0`, quattro path disgiunti. Continuazione
  > autorizzata senza reset/rebase/staging.
- [x] Static gate — Black, Ruff, parse/import review e `git diff --check`. ✅ 2026-09-16
  > **Note implementazione**:
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run black
  > <8 file Python in lease>` → `8 files left unchanged`;
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run ruff check
  > <8 file Python in lease>` → `All checks passed!`;
  > parse AST → `AST OK: 8 leased Python files`;
  > `git diff --check` scoped e globale → exit `0`;
  > controllo whitespace dei due nuovi file → `Untracked whitespace OK`.
- [x] Handoff — matrice test-author, rischi, file e stato `FROZEN`. ✅ 2026-09-16
  > **Evidenza finale**:
  > `git diff --check` → exit `0`; `git diff --cached --name-only` → vuoto;
  > `git rev-parse HEAD` →
  > `22cb18d1d60c8b1197627e6e8eff9cb55f001d3e`;
  > `lsof -nP -iTCP:6153 -sTCP:LISTEN` → nessun output, exit `1`
  > atteso: nessun listener sulla lane.

Ogni slice completata riceve immediatamente data, nota implementazione, comando
di evidenza e ogni deviazione `Fuori pista`.

## 5. Stop conditions

- drift del baseline o modifica concorrente di un file in lease;
- necessità di modificare config, `main.py`, plugin/schema PAC, frontend, test,
  runner o generated artifacts;
- impossibilità di distinguere hard cgroup da monitor osservato;
- rilascio lane senza prova di subtree vuoto;
- drift dei default ordinari o del fingerprint di dominio;
- necessità di installare dipendenze o avviare runtime/test.

## 6. Gate futuri test-author

Con successivo grant lane:

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6153 --data-dir /tmp/librefolio-r2-d schemas tools
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6153 --data-dir /tmp/librefolio-r2-d services tools-registry
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6153 --data-dir /tmp/librefolio-r2-d services tools-lifecycle
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6153 --data-dir /tmp/librefolio-r2-d api tools
```

Nessun test viene scritto o eseguito in questo round dal writer produzione.

> **Note implementazione — evidenza runtime delegata, 2026-09-16**:
> evidenza ricevuta dal coordinatore/test-author; nessun comando runtime
> eseguito da questo writer.
>
> - `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py
>   test --test-port 6153 --data-dir /tmp/librefolio-r2-d schemas tools`
>   → `271 passed / 271`, suite completata;
> - `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py
>   test --test-port 6153 --data-dir /tmp/librefolio-r2-d services
>   tools-registry`
>   → `94 passed / 94`, suite completata;
> - `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py
>   test --test-port 6153 --data-dir /tmp/librefolio-r2-d services
>   tools-lifecycle`
>   → `84 passed, 6 failed` su 90 test. Collection e setup completati; i sei
>   failure deterministici avvengono nella fase di esecuzione test, prima
>   delle assertion di handshake.
>
> **Fuori pista — 2026-09-16**: i sei failure lifecycle hanno una sola causa:
> drift della fixture test `_SessionWitness`, che non implementa il protocollo
> corrente
> `observe_memory_limit(root_pid, root_birth, process_group)`. Verdetto:
> test-fixture drift, non regressione prodotto; riparazione assegnata al
> `test-author`. Gate API, statico e review restano sospesi fino alla
> riparazione. Stato repository al rilievo:
> HEAD `22cb18d1d60c8b1197627e6e8eff9cb55f001d3e`, staged `0`; nessun
> server/listener residuo sulla porta `6153`. Workstream resta `FROZEN`.
>
> **Note implementazione — resume gate, 2026-09-16**: dopo la riparazione
> test-only di `_SessionWitness.observe_memory_limit()`, D-main ha rieseguito
> in coda esclusiva sulla lane `6153`: `schemas tools` → `271/271`,
> `services tools-registry` → `94/94`, `services tools-lifecycle` →
> `91/91`. Il detour fixture è chiuso; gate API/statico/review restano
> pendenti e partiranno soltanto senza scritture concorrenti sul contratto
> PAC importato.
>
> **Note implementazione — API gate, 2026-09-16**: con contratto W0 fermo
> per test/review, D-main ha completato in serie `api tools` → `7/7` e
> `api pac-tool` → `5/5`. Ruff è verde su tutti i 14 path Tool; Black ha
> rilevato un solo drift nel test-owned
> `test_schemas/test_tools_schemas.py`, restituito allo stesso test-author
> senza modifiche produzione. Review read-only di deadline arithmetic,
> cgroup path/PID identity, reservation release, error precedence e default
> legacy: nessun difetto produzione ad alta confidenza; resta obbligatorio
> chiudere Black prima del checkpoint selettivo.
>
> **Note implementazione — static closure, 2026-09-16**: test-author ha
> formattato soltanto `test_tools_schemas.py`; riesecuzione D-main su tutti
> i 14 path Tool: Ruff verde, Black `14 files would be left unchanged`,
> `git diff --check` verde, porta `6153` libera. Slice backend Tool pronta
> per handoff selettivo; nessun generated/client incluso.

Matrice richiesta al successivo `test-author`:

| Area | Contratto minimo |
|---|---|
| DTO/catalogo | default ordinari, ceiling long, clamp, policy incoerenti, fingerprint dominio invariato |
| Engine window | budget+riserva sufficiente/insufficiente, deadline monotona, cancellation |
| cgroup v2 | delegation/readback, attach pre-ACK, OOM→`memory_limit`, subtree vuoto prima release |
| Fallback osservato | RSS albero, campionamento 50 ms, kill, mode mai hard, errore osservazione |
| Executor | reservation 0/1/2 GiB, quarantine, cleanup precedence, metriche nested |
| Batch/API | max request mixed batch, hard/queue per item, seconda wave queue timeout, disconnect |
| Diagnostics | capability sanitizzata, pool reservation, nessun PID/path/scenario |

Fixture privata lifecycle con timeout dichiarati a 120/119 s dovrà esplicitare i
nuovi budget coerenti oppure usare una policy piattaforma dedicata; il writer
produzione non modifica test.

## 7. Definition of Done

- default ordinari invariati;
- long envelope disponibile soltanto per opt-in esplicito;
- batch mixed con massimo outer budget e deadline item indipendenti;
- engine non parte senza budget più riserva;
- memoria 1 GiB applicata all'albero, con modalità dichiarata correttamente;
- `memory_limit` resta errore piattaforma;
- metriche byte separate dalle durate;
- diagnostics privo di dati scenario/processo sensibili;
- catalogo `2` e fingerprint dominio invariati;
- static gate verde e nessun artifact runtime;
- handoff finale `FROZEN`, senza staging o history mutation.
