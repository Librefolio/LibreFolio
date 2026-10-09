# Piano — fase 00, 35: `dev.py` dentro l'immagine Docker

> **Stato**: ✅ chiuso e integrato nel treno 19 (merge `cdde3bc4d`): `5dca6e2cf`, `793aab393`, `5fe027f8f` (verifica del 2026-10-09 su `3cceb4f90`, §7.4).
> - Al checkpoint: ✅ pronto per il checkpoint (2026-10-08, §7.3). L'approccio l'ha deciso il developer; il coordinatore ha preso le quattro decisioni di §4 (§0.1).
>
> - Workstream L. Base `108a2adf5` (`dev_release2`, treno 17).
> - Corsia 6156/6166, `/tmp/librefolio-r2-l`.

## 0. Il mandato

- **Il difetto**, trovato da Q e verificato dal coordinatore, c'è già nella 1.1.0: dentro il container nessun comando `dev.py` parte.
  - `dev.py` registra sempre il test runner, e prima di `parse_args` importa `normalize_coverage_argv`.
  - `scripts/test_runner/_common.py:21` importa `backend.test_scripts`, che `.dockerignore:30` esclude dal 01/09 (`f32e460ca`).
  - Così gestione utenti, `db *` e `user init-settings` sono inutilizzabili, e `ForgotPasswordCard.svelte:42` suggerisce `./dev.sh user:reset`, che nell'immagine non funziona.
- **Il developer** (testuale): «La fix dovrebbe essere che, mentre costruisce i comandi, prima verifica che le varie directory di script esistono, altrimenti va avanti». Va bene anche un import vero dopo il controllo: così in sviluppo un import rotto resta visibile, invece di sparire come farebbe un `try/except ImportError`.
- **Il coordinatore**:
  - coprire anche `normalize_coverage_argv`;
  - incrociare `.dockerignore` con i gruppi di `dev.py`;
  - proporre un messaggio esplicito per un comando saltato (facoltativo);
  - `ForgotPasswordCard` deve mostrare il comando che funziona nell'immagine dopo la cura, verificato, oltre a quello di sviluppo. Le chiavi i18n sono di O: se servono, si coordina;
  - un test di regressione via test-author, rosso prima: aiuto e comandi utente senza `backend/test_scripts`;
  - **solo una proposta** per l'`HEALTHCHECK` (`Dockerfile:153-154`);
  - da evitare: `_frontend_utility.py` e `_frontend_portfolio.py` sono di N. Per il resto del runner si chiede prima.
- **Q**:
  - se la card linka la doc, usa `admin/cli_tools/` **senza ancora**, perché le ancore cambiano con la lingua e l'onda 3 rinomina la sezione;
  - le righe di doc con `./dev.sh user:reset` (`cli_tools.en.md:78`, l'avviso in `docker_advanced`, `dev_workflow.en.md:143-144`) le aggiorna lui dopo l'ingresso della cura: io non le tocco.
- **CHANGELOG**: lo scrive il coordinatore.

### 0.1 Le decisioni del coordinatore (2026-10-08, 18:34)

1. **Il comando saltato, reso esplicito: sì.** Al posto del gruppo `test` mancante, una voce «not available in this installation» che dice cosa manca ed esce con 2. Lo stesso per `i18n` e `translate*`, al posto dei `try/except` silenziosi. Gli altri gruppi restano come nella 1.1.
2. **Il runner: sì.** La voce `utils dev-cli-image` in `_backend_utils.py` è mia fino al checkpoint. `test_release_image_contract.py` (di M) non si tocca, ma gira fra i gate, perché il `Dockerfile` cambia.
3. **La card: sì.** Le due righe nel blocco di codice, Docker e installazione manuale, senza link e senza chiavi i18n.
4. **L'`HEALTHCHECK`: implementarlo.** `localhost:6040` fisso, coerente col `CMD`. Nel checkpoint va spiegato come l'ho verificato senza il demone Docker.
- La cartella `35_devCliImage` va bene.

## 1. Stato verificato (2026-10-08, sul codice a `108a2adf5`)

- **La catena**:
  - `dev.py:2350`: `from scripts.test_runner import register_subparser`;
  - `scripts/test_runner/__init__.py:45` → `_cli` → `_common.py:21` e `:24`: `backend.test_scripts.test_db_config` e `test_utils`;
  - `dev.py:2585`: `from scripts.test_runner._cli import normalize_coverage_argv`, prima di `parse_args`.
- **La riproduzione** (`/tmp/lf-image/app`): ho ricostruito in `/tmp` lo stesso insieme di file che il `Dockerfile` copia in `/app`.
  - Cioè: `backend/` senza `test_scripts/` né `data/`, `scripts/`, `dev.py`, `Pipfile`, `frontend/package.json`, `frontend/build/`, un `VERSION` segnaposto, e `.env.example` copiato come `.env`.
  - Il demone Docker non risponde, quindi l'immagine vera non si costruisce.
  - Con l'interprete del venv condiviso, `dev.py --help`, `user --help`, `user list` e `db current` danno tutti `ModuleNotFoundError: No module named 'backend.test_scripts'`, exit 1.
- **Con il runner saltato**, solo nella copia in `/tmp`:
  - ogni gruppo si registra e il suo `--help` funziona; `test` e `i18n` danno «invalid choice»;
  - su un DB temporaneo dentro la simulazione (`LIBREFOLIO_DATA_DIR=/tmp/lf-image/data`, schema via `alembic -x sqlalchemy.url=…`), `user create`, `user reset`, `user list` e `info version` escono con 0.
- **I gruppi incrociati con l'immagine**. L'immagine ha solo i `[packages]` del Pipfile: `argcomplete` e `mkdocs` sì; `black`, `ruff`, `pytest` e `graphify` no; nemmeno `pipenv`, `npm` e la CLI di docker.

  | Gruppo | Ha bisogno di (assente nell'immagine) | Alla registrazione | All'uso |
  |---|---|---|---|
  | `test` | `backend/test_scripts`, `frontend/e2e`, node | **crash di tutto `dev.py`** | — |
  | `i18n` | `frontend/scripts/i18n-audit.py` | sparisce in silenzio (`try/except`) | — |
  | `mkdocs translate`, `translate-validate` | `mkdocs_src/aphra-pipeline` | spariscono in silenzio (`try/except`) | — |
  | `mkdocs` (gli altri), `front`, `api client`/`sync`, `graph`, `format`, `lint`, `shell`, `install`, `docker` | sorgenti o strumenti di sviluppo | si registrano | falliscono all'uso (non verificato uno per uno) |
  | `user`, `db`, `info` | — | si registrano | funzionano. `db upgrade` col server acceso è rifiutato da `check_server_running`: è preesistente, ed è già nel backlog |

- **La card** (`ForgotPasswordCard.svelte:41-43`): una riga fissa, fuori dall'i18n, `./dev.sh user:reset <username> <new_password>`, fra «Run this command on the server:» (`auth.serverTerminalInstructions`) e «Contact your system administrator…».
  - `dev.sh` la traduce in `dev.py user reset`, e sull'host funziona con pipenv.
  - Nell'immagine non ci sono né `dev.sh` né pipenv.
  - Il servizio compose si chiama `librefolio`; `docker compose exec` gira da root, perché il `Dockerfile` non ha `USER`, come i comandi già nella doc Docker.
  - `user_cli` non usa `check_server_running`, quindi `user reset` funziona con l'app accesa.
- **L'`HEALTHCHECK`**:
  - il `Dockerfile` (`:153-154`) sonda `localhost:${PORT}`, mentre il `CMD` (`:157`) lancia uvicorn su `--port 6040`, fisso;
  - compose mappa `${PORT:-6040}:6040` e ha il suo `healthcheck` su **6040**, che sostituisce quello dell'immagine;
  - il difetto colpisce quindi chi usa l'immagine senza compose, con `-e PORT=…`: il container risulta *unhealthy* mentre l'app risponde.

## 2. Il disegno

- In `dev.py`, `_has(*paths)`: vero se ogni percorso esiste sotto `PROJECT_ROOT`.
- **`test`**: se `_has("backend/test_scripts")`, l'import vero e la registrazione; altrimenti niente import (vedi §4.1).
- **`normalize_coverage_argv`**: solo se `test` è registrato. Altrimenti `parse_args(sys.argv[1:])`.
- **`i18n` e `mkdocs translate*`**: lo stesso schema, controllo e poi import vero, al posto dei due `try/except` silenziosi. È il principio del developer: in sviluppo un import rotto torna visibile.

## 3. Il test, rosso prima (test-author)

`backend/test_scripts/test_utilities/test_dev_cli_image.py`:
- in `tmp_path`, lo stesso insieme di file che il `Dockerfile` copia in `/app`, senza `backend/test_scripts`;
- in un sottoprocesso, con l'interprete corrente e `cwd` nell'albero:
  - `dev.py --help`, `user --help` e `db --help` escono con 0, senza traceback;
  - `test` esce con un errore e senza traceback;
  - su un DB temporaneo (schema via alembic con `-x`), `user create`, `user reset` e `user list` escono con 0, e l'utente compare.
- La registrazione `utils dev-cli-image` in `_backend_utils.py` **la chiedo prima** (§4.2).

## 4. Le decisioni (✅ prese, §0.1)

1. **Il comando saltato, reso esplicito**. Al posto del gruppo, una voce `test` con «not available in this installation». Eseguita, dice cosa manca (`backend/test_scripts`, l'immagine non porta i test) ed esce con 2. Lo stesso per `i18n` e `mkdocs translate*`. Oggi questi comandi spariscono e argparse risponde «invalid choice». Consiglio: sì, per `test`, `i18n` e `translate*`.
2. **Il runner**: una voce mia, `utils dev-cli-image`, in `_backend_utils.py`.
3. **La card**: due righe nel blocco di codice, con etichette da shell non tradotte, senza chiavi i18n nuove e senza link:
   ```
   # Docker
   docker compose exec librefolio python dev.py user reset <username> <new_password>
   # Manual install
   ./dev.py user reset <username> <new_password>
   ```
   Il testo di `serverTerminalInstructions` («Run this command on the server:») resta giusto: se ne esegue uno. Se si preferisce un link alla doc, `admin/cli_tools/` senza ancora, ma serve un'etichetta, cioè una chiave di O.
4. **L'`HEALTHCHECK`**, solo una proposta: `localhost:6040` fisso, come il `CMD` e come compose. Il `PORT` dell'utente vale solo per la porta dell'host.

## 5. Superfici

| File | Cosa |
|---|---|
| `dev.py` | `_has`, la registrazione condizionata di `test`, `i18n` e `translate*`, `normalize_coverage_argv` |
| `Dockerfile` | l'`HEALTHCHECK` su `localhost:6040` (decisione 4) |
| `frontend/src/lib/components/auth/ForgotPasswordCard.svelte` | i due comandi |
| `backend/test_scripts/test_utilities/test_dev_cli_image.py` (nuovo) | il test (test-author) |
| `scripts/test_runner/_backend_utils.py` | la mia voce, se concessa |
| questo piano | — |

## 6. Gate

- Il test nuovo; `utils` della sua categoria.
- `test --help` e un test qualsiasi in sviluppo, per vedere che il runner si registra ancora.
- `check-orphans`; ruff e black; prettier; `git diff --check`; porte libere.
- La simulazione dell'immagine in `/tmp`, prima e dopo.

## 7. Avanzamento

### 7.0 ✅ L'analisi e la riproduzione (2026-10-08)

> **Note implementazione**: §1, con la riproduzione nella simulazione di `/app`.
>
> **⚠️ Fuori pista**:
> - Nel repo non ci sono `requirements.txt` né `VERSION`: li genera `dev.py docker build` (`dev.py:1525-1545`). Nella simulazione `VERSION` è un segnaposto.
> - Il demone Docker non risponde, quindi la verifica è sulla simulazione dello stesso insieme di file, con l'interprete del venv condiviso, non sull'immagine vera.

### 7.1 ✅ Il runner e i rossi (2026-10-08)

> **Note implementazione**:
> - **Runner**: `utils_dev_cli_image` e la voce `dev-cli-image` (`isolation="pure"`) in `_backend_utils.py`. `utils all` la raccoglie da solo.
> - **Test-author**: il file nuovo, con dentro le decisioni di §0.1, comprese le voci «not available» e un test statico dell'`HEALTHCHECK` (`Dockerfile`, `CMD` e compose).
> - **Il rosso** (`utils dev-cli-image`, 6156): **12 failed, 10 passed**, tutti su `AssertionError`. Log: `files/plan35/red.log`.
>   - 11 si fermano sul crash: ogni `dev.py` dell'albero immagine esce con 1, con `ModuleNotFoundError`.
>   - L'`HEALTHCHECK` fallisce con «probes localhost:${PORT}, not a literal number, while the CMD binds --port 6040».
>   - I verdi sono le premesse (l'albero non ha `backend/test_scripts`, `frontend/scripts` né `mkdocs_src/aphra-pipeline`), lo schema creato con alembic, e i 5 casi sintetici del controllo `HEALTHCHECK`.
>
> **⚠️ Fuori pista — `docker-compose.prod.yml`**: il test-author ha controllato anche il suo healthcheck, che sonda 6040. È un po' oltre la richiesta, ma corretto.

### 7.2 ✅ La cura (2026-10-08)

> **Note implementazione**:
> - **`dev.py`**:
>   - `_has(*paths)`;
>   - `_add_unavailable(subparsers, name, help, missing)`: la voce resta nella lista con «— not available in this installation», ed eseguita stampa cosa manca ed esce con 2;
>   - `test` si registra solo se c'è `backend/test_scripts`, e solo allora gira `normalize_coverage_argv`;
>   - `i18n` (`frontend/scripts/i18n-audit.py`) e `mkdocs translate`/`translate-validate` (`mkdocs_src/aphra-pipeline`) fanno controllo e poi import vero; i due `try/except ImportError` sono spariti;
>   - gli esempi di `docker exec` non propongono più `test db populate`, che nel container non c'è: ora `user list`.
> - **`Dockerfile`**: l'`HEALTHCHECK` sonda `localhost:6040`, con un commento che spiega perché `PORT` è la porta dell'host.
> - **`ForgotPasswordCard.svelte`**: due righe nel blocco di codice, `# Docker` con `docker compose exec librefolio python dev.py user reset <username> <new_password>` e `# Manual install` con `./dev.py user reset …`. Più un `data-testid="forgot-reset-commands"` sul blocco. Nessuna chiave i18n, nessun link.
> - **Verde**: `utils dev-cli-image` **22 passed**. Log: `green2.log`.
>
> **⚠️ Fuori pista — `test --help`**: al primo verde un caso restava rosso. Una voce stub con `nargs=REMAINDER` non prende un primo token che sembra un'opzione, e argparse rispondeva «unrecognized arguments: --help».
> - La cura: lo stub ha `prefix_chars="\x00"`, così ogni parola dopo il comando, `--help` o `--coverage` compresi, finisce in `rest`.
> - Poi `test --coverage api all` dà anch'esso la spiegazione, exit 2.
>
> **⚠️ Fuori pista — ruff e black su `dev.py`**: `dev.py` non era pulito già a `HEAD`. Ruff dà gli stessi rilievi di prima, 7 C901, 1 E741, 1 F401, 7 F541, 20 PLC0415, 4 S110 e 3 W293: nessuno nuovo. E black lo riformatterebbe tutto. Non l'ho riformattato. Il test nuovo e il runner sono puliti.

### 7.3 ✅ La verifica e i gate (2026-10-08)

> **Note implementazione**:
> - **La simulazione dell'immagine**, rifatta da zero dal worktree curato (`/tmp/lf-image/app`):
>   - `--help` esce con 0 e lista `test` e `i18n` come «not available in this installation»;
>   - `test`, `test --coverage api all`, `i18n audit` e `mkdocs translate` escono con 2 e dicono cosa manca;
>   - su un DB temporaneo dentro la simulazione, `user create`, `user reset` e `user list` escono con 0. Il comando della card è verificato.
> - **Il checkout completo non cambia**: `--help` non ha nessuna voce «not available», e `test --help`, `i18n --help`, `mkdocs translate --help` e `translate-validate --help` escono con 0.
> - **L'`HEALTHCHECK` senza il demone Docker**:
>   1. il test statico IMG-008: la porta della sonda è uguale a quella del `--port` del `CMD` e a quella dei due compose;
>   2. il comando esatto dell'`HEALTHCHECK`, letto dal `Dockerfile` e con 6040 sostituito dalla porta della corsia (la 6040 è di produzione), lanciato col python del venv: exit **0** su un server vero sulla 6156, exit **1** su una porta chiusa, la 6166.
>
>   **⚠️ Fuori pista**: il server si è ricostruito da solo il frontend all'avvio, perché la card era più nuova del build. È servito anche all'E2E.
>
> | Gate (6156, un comando alla volta; log `files/plan35/`) | Esito |
> |---|---|
> | `utils dev-cli-image` | 22 passed |
> | `utils all`, compreso `release-image-contract` di M | 1248 passed, exit 0 |
> | `front-utility auth "Forgot Password"`, cioè la card | 2 passed |
> | svelte-check (nel build all'avvio del server); prettier sulla card | 0/0; pulito |
> | ruff e black sul test e sul runner; ruff su `dev.py` (gli stessi rilievi di `HEAD`); `check-orphans`; `git diff --check` | puliti |
> | porte 6156 e 6166 | libere |

### 7.4 ✅ Integrazione e verifica finale (2026-10-09)

> **Note implementazione**:
> - **I commit**, integrati nel treno 19 (merge `cdde3bc4d`, 2026-10-08):
>   - `5dca6e2cf` fix(docker): dev.py and HEALTHCHECK in the image;
>   - `793aab393` fix(auth): reset command that works in Docker;
>   - `5fe027f8f` docs(journal): plan 35, dev.py in the image.
> - **Verifica** su `3cceb4f90`:
>   - `_add_unavailable` in `dev.py:2306`, con «not available in this installation»;
>   - l'`HEALTHCHECK` su `localhost:6040` (`Dockerfile:154-155`);
>   - la voce `utils dev-cli-image` (`_backend_utils.py:347`).
> - **`db upgrade` a server acceso** (tabella di §1): è voluto, e la doc lo dice (`docker_advanced.en.md:207`). Non è un residuo.
> - **Classificazione: FINITA.** Nessun residuo. Archiviata in `Release_2/phases/35_devCliImage/`.
