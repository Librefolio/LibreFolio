# `dev.py db … [path]`: l'argomento `path` è ignorato. Facciamolo funzionare davvero

> Lotto di N, 09/10, per la 1.2. Coordinator: c8328a01. Base `9b2acdd5d` (treno 21), worktree pulito. Corsia
> 6159/6169, `/tmp/librefolio-r2-n`.
> Decisione del developer: «facciamolo funzionare davvero!».
> **Stato: analisi (sola lettura).** La scrittura parte dopo il via del coordinator e dopo il checkpoint
> committato di L su `dev.py` (riga `JWT_SECRET`).

## 1. Causa vera (verificata sul codice e con una sonda che non apre nessun DB)

- **`dev.py`.** `cmd_db_current`, `cmd_db_migrate`, `cmd_db_upgrade` e `cmd_db_downgrade` (`:442-498`) calcolano
  `db_path = args.path or get_database_path()` e passano ad Alembic solo la variabile d'ambiente
  `DATABASE_URL=sqlite:///{PROJECT_ROOT / db_path}`.
  - `run_command_live` la consegna davvero al processo figlio (`cli_base.py:411-434`, `full_env.update(env)`).
- **`backend/alembic/env.py:19-36`.** Senza `-x sqlalchemy.url=…` usa `get_settings().DATABASE_URL`.
- **`backend/app/config.py:319-333`.** `get_settings()` fa `settings.DATABASE_URL = get_database_url()`, cioè la URL
  calcolata dalla cartella dati (`get_data_dir()`: modalità test, `LIBREFOLIO_TEST_DATA_DIR`,
  `LIBREFOLIO_DATA_DIR`, poi il default). Così **sovrascrive** il valore che pydantic aveva letto dall'ambiente; il
  docstring della classe lo dice apertamente: «DATABASE_URL is computed dynamically … NOT read from .env»
  (`:95-100`).
- **Sonda** (sola lettura, nessun DB aperto né creato), con `DATABASE_URL=sqlite:////tmp/…probe.db`:
  - `Settings().DATABASE_URL` → la URL della sonda (pydantic la legge);
  - `get_settings().DATABASE_URL` → `…/backend/data/prod/sqlite/app.db`, cioè il DB configurato.
- **Conseguenza: con `path`, si migra sempre il DB configurato.** Intanto il comando stampa «Upgrading database:
  <path>».
  - L'unico indizio è la riga `[Alembic env.py] Using DATABASE_URL from config: …`, facile da non vedere.
  - **Il caso più grave è `db downgrade <copia>`**: fa il rollback del DB **configurato** (quello di produzione, su
    un'installazione host), mentre l'utente crede di lavorare su una copia.
- **Il progetto conosce già la cura.** I test di migrazione passano sempre `-x sqlalchemy.url=`, e lo spiegano:
  «without it ``env.py`` migrates the configured database» (`test_post_migration.py:49`, `:368-372`;
  `test_autoincrement_schema.py:20`, `:55`; `db_schema_validate.py:463-478`; `test_dev_cli_image.py:501`).

## 2. Comando per comando

| Comando | Oggi con `path` | Note |
|---|---|---|
| `db current [path]` | mostra la revisione del DB configurato | nessun controllo del server |
| `db upgrade [path]` | migra il DB configurato | controllo del server sulla porta derivata dal path |
| `db downgrade [path]` | **fa il rollback del DB configurato** | come sopra |
| `db migrate msg [path]` | fa l'autogenerate contro il DB configurato | come sopra. Scrive un file in `backend/alembic/versions/`: nei test, solo il caso del rifiuto |
| `db check [path]` | **è rotto con o senza path**: chiama `backend/test_scripts/verify_db_check_constraints.py`, che **non esiste** e non è mai stato in git | il successore funzionante è `python -m backend.alembic.check_constraints_hook`, che già legge `ALEMBIC_DATABASE_URL` (`check_constraints_hook.py:68-95`). La discrepanza è già annotata in `RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/implementation-plan-v5.md:136`, come «fuori scope» |
| `db create-clean [--test]` | **funziona**: calcola lo stesso percorso delle impostazioni (e per `--test` imposta `LIBREFOLIO_TEST_MODE=1`) | fuori perimetro, non lo tocco |

- **Un uso interno da non rompere.** Il runner dei test cancella il DB di test e lo ricrea con
  `python dev.py db upgrade <test_db_path>` (`scripts/test_runner/_backend_db.py:106`, asserito da
  `test_runtime_isolation.py:852`).
  - Oggi funziona per coincidenza: l'ambiente ha `LIBREFOLIO_TEST_MODE=1` e `LIBREFOLIO_TEST_DATA_DIR`, quindi le
    impostazioni calcolano lo stesso file.
  - Con la cura il file è lo stesso, ma esplicito.
  - Ne segue un vincolo: **`upgrade` deve continuare a creare un DB che non esiste.**
- **Il controllo del server con la porta derivata dal path** (`get_server_port_for_db`, `cli_base.py:302-313`):
  - porta di test se il path risolto coincide col DB di test configurato, altrimenti porta di produzione;
  - per un path qualsiasi (per esempio una copia) controlla la porta di produzione: **prudente**, un falso positivo
    ma mai un falso negativo verso il server di produzione;
  - limite: il DB di una corsia con la sua porta (6159) viene riconosciuto solo se `LIBREFOLIO_TEST_DATA_DIR` è
    nell'ambiente. Va bene così.

## 3. Percorsi, caratteri, Docker

- **Percorsi relativi.** `dev.py:45` fa `os.chdir(PROJECT_ROOT)` all'import, quindi un path relativo è già oggi
  risolto contro la radice del progetto, da qualunque cartella si lanci. Lo stesso vale per `--data-dir` e
  `LIBREFOLIO_DATA_DIR` (`resolve_data_dir`, `cli_base.py:152-165`: «relative to the project root»).
- **Percorsi assoluti.** `PROJECT_ROOT / assoluto` dà l'assoluto, e `sqlite:///` + `/abs` dà `sqlite:////abs`:
  corretto. Va aggiunto `~` (`expanduser`).
- **Caratteri.**
  - `?` e `#` spezzano la URL (`resolve_data_dir` li rifiuta già).
  - `%` spezza `config.set_main_option` di Alembic, che passa per l'interpolazione di ConfigParser e vuole `%%`
    (`alembic/config.py:339-351`).
  - Spazi e parentesi vanno bene (argv senza shell).
- **Docker.**
  - Nel container `pipenv_prefix()` è vuoto, `PROJECT_ROOT=/app` e la cartella dati è
    `/app/backend/data/prod-docker`. Il path è **lato container**.
  - Il server è il processo principale sulla 6040, quindi `docker compose exec … dev.py db upgrade|downgrade|migrate`
    rifiuta sempre: lo dice già `docker_advanced.en.md:207`.
  - Per quei tre serve un container usa-e-getta, `docker compose run --rm librefolio python dev.py db upgrade
    <path nel container>`, lo stesso schema di `:218-223`.
  - `current` e `check` funzionano anche con `exec`.

## 4. Cura minima (solo `dev.py`), con le decisioni e la mia raccomandazione

1. **Un helper** `_db_target(args, *, create_ok: bool)`. Senza `path` restituisce `None`. Con `path`:
   - `expanduser`;
   - se è relativo, lo risolve contro `PROJECT_ROOT`, poi `.resolve()`;
   - rifiuta `%`, `?` e `#` con un messaggio chiaro (exit 1);
   - se il file **non esiste**: errore (exit 1, «Database not found: <abs>»), **tranne** per `upgrade`, che lo crea
     (serve al runner).
   - Restituisce il path assoluto.
2. **`current`, `migrate`, `upgrade`, `downgrade`**: con un `path`, `alembic -c backend/alembic.ini -x
   sqlalchemy.url=sqlite:///<abs> <sottocomando>`; `-x` è un'opzione globale e va prima del sottocomando.
   - **Senza `path`, niente `-x`**: comportamento invariato, decidono le impostazioni.
   - Tolgo la `DATABASE_URL` morta, che inganna chi legge.
   - Il messaggio stampa il path **assoluto** risolto.
3. **`check`**: `python -m backend.alembic.check_constraints_hook` (sola verifica, senza `--fix`); con un `path`,
   `ALEMBIC_DATABASE_URL=sqlite:///<abs>`.
4. **Controllo del server**: invariato (prudente), calcolato sul path assoluto.
5. **Help di argparse**: «Database file (default: the configured one; relative paths start at the project root)».

**Decisioni** (la raccomandazione è sempre la prima opzione):
- **D1, base dei percorsi relativi.** La radice del progetto, come oggi e come `--data-dir`. L'alternativa è la
  cartella da cui si lancia, che richiederebbe di catturare `os.getcwd()` prima di `dev.py:45`.
- **D2, file inesistente.** Errore per `current`, `downgrade`, `migrate` e `check`; creazione per `upgrade`.
  L'alternativa è rifiutare anche `upgrade`, ma romperebbe il runner.
- **D3, senza `path`.** Nessun `-x`. L'alternativa è passare sempre `-x` col path configurato: più esplicito, ma
  `get_data_dir` di `cli_base` e quello del backend leggono `.env` in modi diversi.
- **D4, porta.** Invariata. L'alternativa è saltare il controllo per i path che non sono di nessun server: rischio
  con `dev.py server --data-dir`.
- **D5, `%`.** Rifiutarlo in `dev.py`. L'alternativa è l'escape `%%` in `env.py` (un file di `backend/alembic`).
- **D6, `db check`.** Puntarlo all'hook esistente.
  - In più, due righe condivise descrivono `db check` come «Check migration status», che è falso:
    `.github/instructions/backend-db.instructions.md:138` e `.github/skills/devpy-tools/devpy-server/SKILL.md:62`.
  - Da correggere solo con la tua concessione.

## 5. Test (test-author, rossi prima)

Un file nuovo, `backend/test_scripts/test_utilities/test_dev_cli_db_path.py`, registrato con un'azione
`utils dev-cli-db-path` in `_backend_utils.py` (solo righe aggiunte; da concedere).

**Isolamento.** Ogni sottoprocesso `python dev.py db …` riceve:
- `LIBREFOLIO_DATA_DIR=<tmp>/configured`, con un DB sentinella dentro;
- `LIBREFOLIO_TEST_DATA_DIR=<tmp>/test-lane`;
- `LIBREFOLIO_TEST_MODE=0` e `PIPENV_DONT_LOAD_ENV=1`;
- `PORT` e `TEST_PORT` su porte libere, così nessun server reale fa rifiutare il comando.

Mai la corsia, mai la produzione. I DB si costruiscono con `alembic -x sqlalchemy.url=…` come in
`test_post_migration.py`: `upgrade head`, poi `downgrade -1` dove serve **head-1**.

**Casi:**
- **(a) `upgrade <path>`**: il bersaglio passa da head-1 a head; la sentinella resta a head-1, con i byte invariati.
  Rosso oggi: si migra la sentinella.
- **(b) `current <path>`**: con il bersaglio a head-1 e la sentinella a head, stampa la revisione del bersaglio.
  Rosso oggi: stampa quella della sentinella.
- **(c) `downgrade <path>`**: il bersaglio passa da head a head-1; la sentinella resta a head. Rosso oggi.
- **(d) `check <path>`**: con il bersaglio a head e la sentinella **assente**, exit 0 e la sentinella non viene
  creata. Rosso oggi: lo script non esiste.
- **(e) path relativo**, lanciato da un'altra cartella (`cwd` = una cartella temporanea), con
  `relpath(bersaglio, PROJECT_ROOT)`: `current` legge il bersaglio. Rosso oggi.
- **(f) file inesistente**: per `current`, `downgrade`, `check` e `migrate`, exit diverso da 0, il messaggio nomina il
  file e il file non viene creato. Rosso oggi: exit 0 sul DB configurato.
- **(g) `upgrade` su un file inesistente**: lo crea a head, cioè il flusso del runner. Rosso oggi: non lo crea.
- **(h) `%` nel path**: rifiutato, niente creato. Rosso oggi.

## 6. Gate (corsia 6159, un comando alla volta)

- il test nuovo;
- il test che asserisce il comando del runner (`test_runtime_isolation.py`) e `utils test-runner-cli`;
- **`test db create`** sulla mia corsia: ricrea il DB di test attraverso `dev.py db upgrade <path>`, cioè il flusso
  vero del runner. Da approvare: distrugge e ricrea solo `/tmp/librefolio-r2-n`, con dati sintetici;
- `check-orphans`;
- ruff e black (confronto con HEAD);
- per la doc: `mkdocs build` in modalità strict e `check-links`.

## 7. Doc (docs-writer, solo inglese, senza stamp)

In `mkdocs_src/docs/admin/cli_tools.en.md`, la sezione «Maintain the Database»: il `path` torna, documentato.
- un file SQLite, con i relativi che partono dalla radice del progetto;
- deve esistere, tranne per `upgrade`, che lo crea;
- il controllo del server resta sulla porta configurata;
- Docker: path nel container, `exec` per `current` e `check`, `docker compose run --rm` per gli altri.

Non tocco `service_exposure` (è di Q) né `docker_advanced`.

## 8. Conflitti, complessità, rischi

- **Conflitti.**
  - `dev.py`: L è sulla riga `JWT_SECRET`; si aspetta il suo commit. Le mie righe sono `:435-498` e il parser
    `:2351-2370`.
  - `_backend_utils.py`: solo righe aggiunte.
  - `cli_tools.en.md`: ha traduzioni it/fr/es, che restano indietro fino alla traduzione.
- **Complessità**: bassa, circa 40 righe in `dev.py`.
- **Rischi.**
  - Il flusso `db create` del runner: lo coprono (g) e il gate `test db create`.
  - `migrate`, che scrive file nel repo: nei test solo il rifiuto.
  - Il tempo: ogni caso lancia `pipenv run alembic`, circa 3-4 s.

## 9. Passi e definizione di fatto

1. ✅ (09/10) Analisi, sola lettura: questo documento.
2. ✅ (09/10 11:46) **Via del developer**: «Sì, tutte le raccomandazioni di N», quindi D1-D6 come proposti.
   - Base avanzata al treno 22, `da8d7a10b`, col lotto di L dentro. Da L ci sono `config.py` (`SESSION_COOKIE_SECURE`)
     e `dev.py` (`_ensure_shared_jwt_secret`): nessuna riga mia toccata, i comandi `db` si sono solo spostati di 11
     righe (`:446-510`, parser `:2362-2385`). `dev.py` ora è mio.
   - Concessi:
     - la riga del runner `utils dev-cli-db-path` (solo aggiunte);
     - il gate `test db create` sulla corsia;
     - le due righe `.github` su `db check`;
     - `cli_tools.en.md` col docs-writer.
   - **CHANGELOG**: il difetto c'era in `v1.1.0`. Al tag, `dev.py:460` ha la `DATABASE_URL` nell'env, `config.py:181`
     la sovrascrive, `env.py:37` la usa, e `dev.py:420` chiama lo script che nel tag non c'è. Quindi **🐛 Fixed**.
3. ✅ (09/10) Rossi (test-author): `backend/test_scripts/test_utilities/test_dev_cli_db_path.py`, 15 casi su DB
   temporanei.
   - **Isolamento**: una sonda di sicurezza prima di ogni `dev.py db`, che verifica che pipenv sia lo stesso venv e
     che il DB configurato sia la sentinella nel sandbox; porte libere; `LIBREFOLIO_TEST_MODE=0`.
   - Registrazione `utils dev-cli-db-path` in `_backend_utils.py` (+20, solo aggiunte).
   - **Rosso in corsia: 13 falliti, 2 passati** (le due guardie senza path; `/tmp/libreFolio_n_dbpath_red2.log`).
   > **⚠️ Fuori pista**: al primo rosso (12/3) `missing_file_is_refused[check]` era verde per errore. pytest dà a
   > `tmp_path` il nome del test, quindi il path conteneva «missing» e l'eco del path bastava. Corretto dal
   > test-author: le parole si cercano sulla riga **senza** il path; la correzione copre anche `migrate`.
4. ✅ (09/10) Cura in `dev.py` (+78 −38).
   - Gli helper `_named_db_file` (assoluto, `~`, relativi dalla radice, rifiuto di `%?#` e delle cartelle) ed
     `_existing_db_file` (file mancante = «Database not found: <abs>»).
   - `_alembic`: `-x sqlalchemy.url` solo con un path.
   - `check` → `python -m backend.alembic.check_constraints_hook` con `ALEMBIC_DATABASE_URL`.
   - `upgrade` crea la cartella **dopo** il controllo del server.
   - Help del parser aggiornato.
   - ruff e black: nessuna segnalazione nuova rispetto a HEAD.
5. ✅ (09/10) Verde e gate (corsia 6159, un comando alla volta):
   - `utils dev-cli-db-path` **15/15**;
   - `utils test-runner-cli` 36/36;
   - `utils runtime-isolation` 153/153, compreso l'asserto sul comando `db upgrade <path>` del runner;
   - **`test db create`**: il DB della corsia è ricreato passando per `dev.py db upgrade <path>`, e il log dice
     «Using DATABASE_URL from -x parameter: …/librefolio-r2-n/sqlite/app.db»; revisione
     `004_release_1_2_0_schema`;
   - `check-orphans` ✅.
   - **Prova a mano** su un DB usa-e-getta in `/tmp`, poi cancellato: `upgrade` crea e migra via `-x`, `check`
     esce con 0, «Database not found», il rifiuto di `%`; la cartella configurata non viene mai creata.
   - Le due righe `.github` su `db check` sono corrette: «Verify the model CHECK constraints exist in the DB».
6. ✅ (09/10) Doc (docs-writer), `mkdocs_src/docs/admin/cli_tools.en.md` +10, solo inglese, senza stamp.
   - In «⬆️ Apply Migrations»: `db check`, un esempio con un path (una copia), un punto su cosa vuol dire il path, e
     una nota Docker. `exec` va bene per `current` e `check`; per `upgrade` e `downgrade` servono
     `docker compose stop librefolio` e poi `run --rm`; link a `docker_advanced.md#docker-exec`.
   - `mkdocs build` in modalità strict: exit 0, nessun avviso.
   - `check-links`: exit 1 per **un link già rotto prima**, `user/assets/detail/chart/#rolling-return`, usato da
     `assets/[id]/+page.svelte:3012`: l'ancora manca nelle pagine it/fr/es. Viene dal commit `1c2f88d67`; nessun
     file di questo lotto.
   > **Fuori perimetro, per il backlog** (segnalati dal docs-writer, letti nel codice e non provati):
   > - la nota in cima a `cli_tools.en.md:7` dice che i comandi del database funzionano con `exec`, ma `upgrade` e
   >   `downgrade` no;
   > - in Docker, un `PORT` in `.env` diverso da 6040 (passato da `env_file`) farebbe controllare a `db upgrade` via
   >   `exec` la porta sbagliata. È precedente a questo lotto.
7. ✅ (09/10) Checkpoint: 4 commit proposti in `/tmp/libreFolio_commits/libreFolio_commit_n_dbpath_C1..C4.txt`.
   Liste in `n_dbpath_paths_C1..C4.txt`, blob in `n_dbpath_blobs.txt`, albero in `n_dbpath_final_tree.txt`. Stato:
   FROZEN.

**Fatto quando**:
- i 5 comandi rispettano `path`, assoluto o relativo;
- `db check` funziona;
- nessun DB viene creato per errore;
- `upgrade` crea ancora il DB del runner;
- i gate sono verdi e la doc è allineata.
