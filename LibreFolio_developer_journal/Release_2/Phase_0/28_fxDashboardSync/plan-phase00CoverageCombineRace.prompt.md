# Piano — N / `coverage combine` delle passate parallele (corsa sui file di coverage tardivi)

> Lotto assegnato dal coordinator l'08/10 alle 10:53, su decisione del developer («diamo a N analisi e fix»).
> Prima l'analisi, poi il codice. Base `58fc35174` (pulita).
>
> Riferimenti: il piano dello step 2
> ([`plan-phase00FxDashboardSyncStep2PageCache.prompt.md`](plan-phase00FxDashboardSyncStep2PageCache.prompt.md)).

| | |
|---|---|
| **Corsia** | `--test-port 6159 --data-dir /tmp/librefolio-r2-n`; review `127.0.0.1:6169` (non usata) |
| **Prove** | `/tmp/libreFolio_cov_combine/`, copiate dal coordinator (il checkout principale non si legge) |
| **Limiti** | al massimo una piccola passata `--coverage --workers 2` sulla corsia; niente coverage completa |

---

## 1. Il difetto osservato (coverage completa del 07/10, `d07412899`, 2 worker)

- Passata parallela da **111** unità: verde, poi `❌ coverage combine failed: Couldn't combine from non-existent path
  '…/.coverage_data/parts/.coverage.w1.MacBook Pro di Emanuele (2).pid10917.Xm9GZYYx'`.
- Passata da **54** unità: stesso errore su `….pid24531.X0pJBznx`.
- Le passate da 24 e 11 unità si sono combinate («combined 2 worker coverage file(s)»).
- Nella cartella delle parti, alla fine, c'è `….pid24531.X0pJBznx.HNQIp837rWOh`: il percorso cercato dal combine
  **più** un suffisso `.H…h`.
- Il backend risulta al 36,8%, sottostimato.

## 2. Analisi, verificata sul codice e riprodotta

### 2.1 Chi crea i nomi dei file

- **Il runner** (`scripts/test_runner/_executor.py:25-44`, `_worker_env`): ogni worker parallelo riceve
  `COVERAGE_FILE=.coverage_data/parts/.coverage.w{i}`, più `COVERAGE_PROCESS_START` e la `sitecustomize` sul
  `PYTHONPATH` (`_common.py:36-51`).
- **pytest-cov 7.1.0** (`pytest_cov/engine.py:235-276`, `Central`):
  - all'avvio di ogni worker fa `cov.erase()` (non c'è `--cov-append`), cioè `Coverage.erase()` →
    `_data.erase(parallel=True)` (`coverage/control.py:764-777`), che **cancella `.coverage.w{i}` e ogni
    `.coverage.w{i}.*`** (`coverage/sqldata.py:900-906`);
  - a fine sessione salva e combina `.coverage.w{i}.*` dentro `.coverage.w{i}` (`Coverage.combine()` usa
    `suffix=None`, `control.py:911`).
- **coverage.py 7.16.0**, dato parallelo (`parallel = true` in `.coveragerc`): il nome è
  `<base>.<host>.pid<pid>.X<rand>x` (`sqldata.py:1173-1191`; nell'host i punti diventano `_`, spazi e parentesi
  restano). Alla fine di `write()` il file viene **rinominato** con `.H<hash>h` (`sqldata.py:914-929`). Il nome
  senza `.H` è quindi transitorio: esiste solo mentre il processo sta salvando.
- **Chi scrive in parallelo**: con `COVERAGE_PROCESS_START` impostato, `a1_coverage.pth` (nel venv) e la nostra
  `sitecustomize` avviano coverage in **ogni** interprete del venv
  (`coverage.process_startup(slug="pth")`). Tra questi c'è il **resource tracker** di `multiprocessing`
  (`python -c "from multiprocessing.resource_tracker import main; …"`). Lo avvia il contesto `spawn` usato dai
  worker quantitativi (`backend/app/services/risk/quant/spawn_worker.py:342`), e **termina dopo** il pytest che
  lo ha creato, quando la sua pipe va in EOF.

### 2.2 Come il runner li combina

`_executor.py:223-272` (`combine_coverage`), chiamato da `_cli.py:970-971` appena tornano i worker:

1. `parts = sorted(PARTS_DIR.glob(".coverage.w*"))`, una fotografia della cartella;
2. `coverage combine --append <ogni file, per nome>`, lanciato con `pipenv run` (avvio di circa 1 s).

coverage.py tratta ogni argomento esplicito così (`coverage/data.py:68-96`, `combinable_files`): se è un file lo
prende, se è una cartella la scorre, **altrimenti solleva `NoDataError("Couldn't combine from non-existent
path")`**. Basta un nome sparito per far fallire **tutto il combine**: nessun file combinato, exit 1.

### 2.3 La corsa, riprodotta sulla 6159

Sonda `/tmp/libreFolio_n_covprobe.py`, log `/tmp/libreFolio_n_covprobe_spawn.log`. Un worker con lo stesso
ambiente di `_worker_env(1)` lancia `test_risk_spawn_worker.py` (11 passati). Dopo il suo ritorno, la cartella
viene letta ogni 10 ms:

| t dopo il ritorno | Cartella |
|---|---|
| 0,000 s | `.coverage.w1` (la base, già combinata da pytest-cov) |
| 0,011 s | compare `.coverage.w1.MacBook Pro di Emanuele (2).pid78459.XzLJ9g3x` (nome transitorio) |
| 0,034 s | rinominato `….XzLJ9g3x.HNQIp837rWOh` |

- `meta.sys_argv` del file tardivo: `['-c']`, cioè il resource tracker.
- L'hash `HNQIp837rWOh` è **identico** a quello del file rimasto nella coverage del 07/10: stesso processo, stessi
  dati.

Quindi `combine_coverage` fotografa la cartella nella finestra di ~20 ms in cui il tracker sta salvando (gira
subito dopo l'ultimo worker), e circa 1 s dopo coverage non trova più il nome: il file è già stato rinominato.

- **Perché solo le passate grandi**: per la corsa serve un processo che usi il contesto `spawn` (i test
  `risk_*`, servizi e api); le passate da 24 e 11 unità non ne hanno.
- **Il nome del Mac non c'entra**:
  - coverage accetta spazi e parentesi (`glob.escape`, `data.py:84`; host `[^.]+`, `sqldata.py:1200`);
  - il runner passa una lista senza shell, e l'errore mostra il percorso intero;
  - il «suffisso in più» è il segno di completamento di coverage stesso.

### 2.4 Le conseguenze, peggiori del messaggio

- Il combine fallito non unisce la passata. Il messaggio dice «le parti restano in `.coverage_data/parts/`», ma
  alla passata successiva l'`erase()` di pytest-cov **cancella** `.coverage.w0*` e `.coverage.w1*`.
- Prova: dopo il fallimento della passata da 111, quella da 24 combina «2» file, non 2+7. I dati delle due passate
  grandi sono **persi**, non solo esclusi.
- `_cli.py:971` ignora il valore di ritorno: la run finisce verde con la coverage parziale.

### 2.5 Lo stesso schema altrove (`_coverage.py`)

- `_finalize_coverage` (`:173-192`): `glob(".coverage.*")` nella radice, poi `coverage combine` con i nomi
  espliciti. Sono i file del backend condiviso (anche i suoi figli spawn e il suo tracker), quindi la stessa corsa
  quando il server si ferma.
- `_coverage_combine_internal` (`:372`, comando manuale): stesso schema.

## 3. Correzione proposta

1. **Combine a cartella, non a nomi**, in un helper unico di `_coverage.py`:
   - `coverage combine [--append] <cartella>`: è coverage a scorrere la cartella, dentro il proprio processo, ~1 s
     dopo il ritorno dei worker. Un nome che sparisce durante il suo giro non lo fa fallire: verificato
     (`/tmp/libreFolio_n_covupd`), il file sparito viene saltato e gli altri combinati;
   - poi una nuova lettura della cartella. Se sono rimaste parti (arrivate dopo il giro di coverage), un altro giro,
     al massimo 3. Ogni giro cancella ciò che ha combinato, quindi ciò che resta è nuovo;
   - se dopo l'ultimo giro restano file, li nomina, e il combine risulta fallito.
   - Lo usano `_executor.combine_coverage` (parti dei worker), `_finalize_coverage` (file del backend condiviso
     nella radice, senza `--append`, come oggi) e `_coverage_combine_internal`.
2. **(Raccomandato, piccolo)** prefisso unico per passata in `_worker_env`:
   - `COVERAGE_FILE=.coverage.<passata>.w{i}` invece di `.coverage.w{i}`;
   - l'`erase()` di una passata nuova cancella solo i suoi file, mai le parti rimaste da una passata precedente;
   - il combine a cartella di quella passata, o di una successiva, le recupera. Così il messaggio «le parti restano»
     torna vero.

Nessun altro comportamento cambia: stessi file finali (`.coverage_data/backend`, `frontend`), stesse stampe di
successo.

**Fuori perimetro, per il backlog**: `_cli.py:971` ignora l'esito del combine. Una run con coverage persa dovrebbe
dirlo nel verdetto finale.

## 4. Test, rosso prima (test-author)

Nuovo file `backend/test_scripts/test_utilities/test_coverage_combine.py`. Dati di coverage veri
(`CoverageData.add_arcs`, un sorgente finto diverso per parte) in una cartella temporanea:

- `.coverage.w0` e `.coverage.w1`;
- `.coverage.w1.MacBook Pro di Emanuele (2).pid24532.XxpJi2Cx.H4iMCLM7Cjwh` (spazi, parentesi, doppio suffisso);
- un transitorio `….pid24531.X0pJBznx`.

Si chiama il vero `combine_coverage()`, con `PROJECT_ROOT` e `PARTS_DIR` puntati sulla cartella temporanea e
`pipenv_prefix` → `[sys.executable, "-m"]`, così gira il vero `coverage combine`.

1. **La corsa**: un `subprocess.run` avvolto rinomina il transitorio in `….HNQIp837rWOh` subito prima di lanciare
   coverage, cioè quello che fa il tracker. Atteso: `True`, l'archivio accumulato contiene i sorgenti di **tutte** le
   parti, nella cartella non resta niente. **Rosso oggi**: `Couldn't combine from non-existent path`, `False`.
2. **L'arrivo tardivo**: dopo il primo giro di coverage compare una parte nuova. Atteso: combinata al secondo
   giro. **Rosso oggi**: resta nella cartella, fuori dall'archivio.
3. **I file del server nella radice** (il modo di `_finalize_coverage`): `.coveragerc` resta, tutte le parti con
   spazi e parentesi vengono combinate.

Registrazione: una funzione `utils_coverage_combine` e un `add_test(...)` in `_backend_utils.py`,
`isolation="pure"` (file temporanei e un sottoprocesso coverage; niente DB, server, rete né scritture nella repo).

## 5. Verifica sulla corsia

- Il nuovo test, `utils test-runner-cli` e `check-orphans`.
- La sonda rifatta col codice nuovo.
- Una passata `--coverage --workers 2`. La più piccola che fa nascere la corsa è `services all`: contiene
  `test_risk_*` (spawn) ed è la passata da 111 del 07/10, ~10 min sotto carico. Il via lo decide il coordinator.

## 6. Perimetro richiesto

- `scripts/test_runner/_coverage.py` (helper e le due chiamate);
- **`scripts/test_runner/_executor.py`**: è lì il combine che fallisce (`combine_coverage`, `:223-272`), più la riga
  di `_worker_env` per la proposta 2;
- il nuovo test e la registrazione in `_backend_utils.py`.

Niente `_common.py`: il suo `coverage combine --keep` (`:324-333`) è già a cartella.

## 7. Passi

1. ✅ (08/10) Analisi al coordinator: questo documento. **Approvata** alle 11:04, con il perimetro concesso:
   - `_executor.py`: `combine_coverage` passa all'helper, e la riga di `_worker_env`;
   - `_coverage.py`: l'helper, usato dai tre combine;
   - il test e la registrazione in `_backend_utils.py`, solo righe aggiunte;
   - `_cli.py:971`: un combine fallito pesa sul verdetto, con il suo caso nel test.

   > **Variante approvata** (11:10): ogni run scrive nella sua cartella `parts/run-<data>-<pid>/`, con
   > `COVERAGE_FILE=.coverage.p<passata>.w{i}`. Due condizioni del coordinator, ciascuna con il suo caso nel test:
   > 1. dopo un combine riuscito la cartella della run si rimuove; se il combine fallisce resta, nominata nel
   >    messaggio;
   > 2. `--cov-clean-backend` pulisce anche `parts/`: i `.coverage*` sciolti e le cartelle `run-*`, compresi i 4
   >    resti del 07/10. **Fuori pista**: serve una riga in `_suites.py` (`_clean_coverage_dirs`), dichiarata.
2. ✅ (08/10) Test rossi (test-author), `backend/test_scripts/test_utilities/test_coverage_combine.py`, più la
   registrazione `utils coverage-combine` in `_backend_utils.py` (18 righe aggiunte, nessuna tolta).
   > **Note implementazione**: rosso provato col codice di produzione invariato, con
   > `dev.py test --test-port 6159 --data-dir /tmp/librefolio-r2-n utils coverage-combine`: **7 falliti, 1 passato**
   > (il controllo di (d)). Log in `/tmp/libreFolio_n_cov_red.log`. Ogni rosso fallisce per il motivo giusto:
   > - (a) `:253` e (c) `:304`: «Couldn't combine from non-existent path '….pid24531.X0pJBznx'», l'errore del 07/10,
   >   sul nome con spazi e parentesi;
   > - (b) `:275`: la parte tardiva resta in `parts/`;
   > - (d) `:355`: `ok=True` con il combine fallito;
   > - (e) `:385` e `:410`: la cartella della run sopravvive; un file illeggibile non fa fallire niente;
   > - (f) `:445`: i 4 resti del 07/10 restano in `parts/`.
3. ✅ (08/10) Correzione, applicata con `/tmp/libreFolio_n_covfix.py`:
   - `_coverage.py`: `_coverage_parts`, `combine_coverage_dir` (cartella, nuova lettura, al massimo 3 giri, stop
     quando un giro non cambia niente, segnala le parti arrivate tardi), `clean_coverage_parts`, `_combine_keeping`;
   - `_executor.py`: `RUN_PARTS_DIR`, nome per passata, `combine_coverage` con l'helper, `_remove_run_parts_dir`;
   - `_cli.py`: il combine pesa sul verdetto della passata;
   - `_suites.py`: la riga concessa in `_clean_coverage_dirs`.
   > **Note implementazione**: verde, **8 passati** (`/tmp/libreFolio_n_cov_green.log`). Lint, rispetto a HEAD:
   > - `_coverage.py`: da 2 segnalazioni ruff a 1 (resta l'`E741` già presente a `:305`). black non toccherebbe
   >   nessuna riga mia: il file era già fuori formato prima, 66 righe a HEAD e 56 adesso;
   > - `_suites.py`: +1 `PLC0415`, l'import locale concesso, come i tre già presenti (`:55`, `:59`, `:95`). Non c'è
   >   ciclo d'import, quindi l'import in testa sarebbe pulito; la scelta è del coordinator;
   > - gli altri file: nessuna segnalazione nuova, black pulito.
   >
   > **⚠️ Fuori pista**: il ramo parallelo di `_coverage_combine_internal` faceva salire la complessità a 12 (C901).
   > L'ho spostato nella piccola `_combine_keeping` (le istantanee per nome, le parti come cartella).
4. ✅ (08/10) Verifica sulla corsia, prima passata:
   - `utils test-runner-cli`: ✅ 36 passati;
   - `check-orphans`: ✅, il test nuovo è registrato e raggiungibile da `all`;
   - **la sonda rifatta**, `/tmp/libreFolio_n_covprobe2.py`: ✅. Percorre il codice vero (`run_groups`, poi subito
     `combine_coverage`) su `test_risk_spawn_worker.py`. La parte del resource tracker compare a 0,001 s e viene
     rinominata a 0,026 s, con lo stesso hash `HNQIp837rWOh` del 07/10. L'istantanea della sonda stessa aveva
     elencato il nome transitorio e, all'apertura, non lo ha più trovato: è la corsa che uccideva il runner.
     Adesso coverage elenca da sé: tutto combinato, 0 archi mancanti, cartella rimossa a 0,922 s. La parte del
     tracker, misurata sulla sonda vecchia, ha 308 file e **0 archi**: è l'innesco della perdita, non il dato perso;
   - **la passata vera**, `services all` con `--coverage --cov-clean-backend --workers 2`, con 3 resti seminati in
     `parts/` (`/tmp/libreFolio_n_services_cov.log`):
     - la pulizia toglie i 3 resti;
     - parallelo 111 unità, 2766 + 2878 passati; consolidamento 178 passati; `spawn_worker.py` all'86,49%;
     - **combine rosso**, per una sola parte.
   > **⚠️ Fuori pista: la parte vuota.** La parte è `….pid17336.XWmqACex.HuitnSoGmx4h`: SQLite con tutte le
   > tabelle di coverage e **0 righe** (nemmeno `coverage_schema`). coverage la rifiuta («isn't a coverage data
   > file»). Il suffisso `.H` è un hash di dati veri: quello di un hasher vuoto sarebbe `p11G0L8e12`.
   >
   > La causa: `Coverage._on_sigterm` (`control.py:756`) non è rientrante. Un SIGTERM che arriva durante il
   > salvataggio di atexit fa partire un secondo salvataggio annidato, che chiude la connessione del primo (la sua
   > transazione si perde), rinomina il file e uccide il processo. Due percorsi del prodotto lo innescano:
   > - `spawn_worker.stop()` (`:272-288`): sentinella, `join(1.0)`, poi `terminate()`. La riga `:282` risulta coperta
   >   in questa run;
   > - `ProcessTree._signal` (`tools/process_tree.py:188-209`): `killpg(SIGTERM)` e poi `terminate()` sugli stessi
   >   processi.
   >
   > Il dato del figlio è perso dentro il figlio: nessun combine può recuperarlo. Il codice vecchio cancellava quella
   > parte in silenzio, perché `unlink` toglieva tutte le parti dopo un combine terminato con 0. Il comportamento su
   > queste parti è chiesto al coordinator; nel frattempo i test non toccano niente.
   >
   > **Decisione del coordinator** (12:12): **opzione A**. Una parte finita (nome `.H…h`) la cui tabella `file` è
   > vuota si toglie, si nomina con un avviso e la passata resta verde. Ogni altra parte illeggibile resta rossa,
   > tenuta e nominata. Vale anche per `_finalize_coverage`. Le cause vanno nel backlog (C).
4b. ✅ (08/10) Regola delle parti vuote.
   > **Note implementazione**:
   > - test-author ha scritto il caso (g): (g1) le parti dei worker, (g2) la guardia sul nome transitorio, (g3) il
   >   backend condiviso. Rosso provato con `/tmp/libreFolio_n_cov_red_g.log`: **2 falliti, 9 passati**; (g1) cade
   >   a `:502` (`ok is True`), (g3) a `:544` (la parte resta nella cartella di lavoro), (g2) è verde come deve.
   > - Codice in `_coverage.py`: `_FINISHED_PART`, `_holds_no_data` (apertura in sola lettura via `as_uri()`, così
   >   un file sparito non viene ricreato e gli spazi del nome sono escapati) e `_drop_empty_parts`.
   >   `combine_coverage_dir` le toglie prima di ogni giro e alla fine, mai con `keep`.
   >   `_executor.combine_coverage` le toglie prima di contare, così il «combined N» è esatto.
   > - Verde: **11 passati** (`/tmp/libreFolio_n_cov_final.log`).
   >
   > **⚠️ Fuori pista**:
   > - lo script preparato filtrava solo alla fine. Il test-author ha fatto notare che il dettaglio dell'ultimo giro
   >   fallito sarebbe rimasto, e l'ho cambiato: filtro prima di ogni giro;
   > - il messaggio di `clean_coverage_parts` contava una cartella come «part(s)»: ora dice «item(s) — loose parts
   >   and run-* directories».
5. ✅ (08/10) Verifica finale sul codice finale:
   - `utils coverage-combine`: 11 passati;
   - `utils test-runner-cli`: 36 passati;
   - `check-orphans`: ✅;
   - `git diff --check` pulito; nessuno spazio in coda nei file nuovi; porte 6159 e 6169 libere;
   - **seconda passata vera**, `services all` con `--coverage --workers 2`, senza `--cov-clean-backend`
     (`/tmp/libreFolio_n_services_cov2.log`): **exit 0**.
     - Parallelo: 111 unità, 2747 + 2897 passati. Consolidamento: 178 passati.
     - La parte vuota è ricomparsa, stavolta dal worker 1: `….pid46233.X4wSLuNx.HuitnSoGmx4h`, **con lo stesso hash**
       della prima volta. Il contenuto è quindi deterministico. È stata tolta e nominata.
     - «combined 5 worker coverage file(s)», con le tardive comprese; la cartella della run è stata rimossa.
     - La cartella della run fallita è rimasta **intatta**: nessuna run raccoglie i resti di un'altra.
     - Coverage al 76,19%, identica alla prima passata (52169 / 10530 / 15726 / 2164).
   - `clean_coverage_parts` sul resto vero: toglie la cartella della run fallita e tiene i junit.
6. Consegna e FROZEN; le frasi del caso per la nota del runner, nessun CHANGELOG. Il devWiki è archiviato
   (`problems/coverage-combine-race-renamed-part`, la riga di `concepts/test-isolation-classes`, `index.md` e
   `log.md`, solo in aggiunta). `check_source_paths.py` dà 0 path mancanti sulla pagina nuova. graphify è rinviato:
   non è disponibile nel worktree.
   > **Checkpoint** (08/10): 4 commit proposti, scritti in `/tmp/libreFolio_commits/libreFolio_commit_n_combine_C1..C4.txt`
   > (runner e test; la doc del runner; il devWiki; questo piano). Le liste dei path sono in
   > `n_combine_paths_C1..C4.txt`, i blob in `n_combine_blobs.txt` e l'albero finale in `n_combine_final_tree.txt`.
   > Stato: FROZEN.
