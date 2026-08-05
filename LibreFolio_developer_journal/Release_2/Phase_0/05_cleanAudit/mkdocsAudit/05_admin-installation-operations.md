# 05 — Admin e operazioni

> **Release 2 · Phase 0 · 05_cleanAudit · mkdocsAudit**
>
> Ambito: le **8 pagine EN** pubblicate sotto `mkdocs_src/docs/admin/*.en.md`. Sola
> verifica: nessuna modifica a codice, `.env`, docker-compose o documentazione.
> Baseline: worktree dirty corrente, commit `09cbb7e28f4e4e4bba9f9d40748b98e1876f5103`
> (manifest completo in [00_BASELINE](00_BASELINE.md), non alterato).

## Pagine in scope

| # | File | Argomento |
|---|---|---|
| 1 | `cli_tools.en.md` | Comandi `dev.py` per amministrazione |
| 2 | `configuration.en.md` | Variabili `.env` e priorità di risoluzione |
| 3 | `docker_advanced.en.md` | Docker Compose, UID/GID, produzione, backup |
| 4 | `filesystem.en.md` | Struttura `backend/data/`, log, backup |
| 5 | `host_installation.en.md` | Installazione host via Pipenv |
| 6 | `index.en.md` | Indice manuale admin, JWT/sessioni |
| 7 | `service_exposure.en.md` | Esposizione via Tailscale (4 livelli) |
| 8 | `settings.en.md` | Global Settings (DB-backed, UI admin) |

Tracciatura eseguita su: `dev.py` (2375 righe), `scripts/user_cli.py`,
`backend/app/config.py`, `backend/app/schemas/settings.py`,
`backend/app/services/global_settings_service.py`,
`backend/app/services/scheduler/settings.py`, `backend/app/api/v1/{auth,brokers,uploads}.py`,
`backend/app/logging_config.py`, `backend/app/db/session.py`, `Dockerfile`,
`entrypoint.sh`, `docker-compose.yml`, `docker-compose.prod.yml`,
`.github/workflows/release.yml`, `frontend/src/lib/components/settings/**`.
Un comando reale (`./dev.py mkdocs --gallery`) e un URL pubblico
(`raw.githubusercontent.com/.../custom_startup.sh`) sono stati eseguiti/richiesti
in sola lettura per riprodurre due reperti.

## Copertura

| Report | Pagine | Stato |
|---|---:|---|
| Questo report | 8/8 | Completato |

| Pagina | Reperti propri | Stato |
|---|---:|---|
| `cli_tools.en.md` | 3 (B1, B2, B7) | Verificata con reperti |
| `configuration.en.md` | 0 | Verificata, nessun reperto non-beta |
| `docker_advanced.en.md` | 3 (B3, B9, B11) | Verificata con reperti |
| `filesystem.en.md` | 0 | Verificata, nessun reperto |
| `host_installation.en.md` | 1 (B12) | Verificata con reperti |
| `index.en.md` | 0 diretto, 1 in comune (B9) | Verificata, un rimando condiviso |
| `service_exposure.en.md` | 1 (B4) | Verificata con reperti |
| `settings.en.md` | 5 (A1–A5) | Verificata con reperti |

Legenda gravità: 🔴 `critical` · 🟡 `major` · 🟢 `minor` · ⚪ `info` (stessa scala di
`00_INDEX.md`: critical = rischio dati/sicurezza/operatività; major = guida a un
esito sbagliato; minor = imprecisione senza esito funzionale; info = miglioramento
o incertezza da confermare).

---

## Reperti — `settings.en.md`

### 🔴 A1 — `enable_registration` non fa nulla

**Dove**: `mkdocs_src/docs/admin/settings.en.md:39,60`
**Claim**: *"Whether new user registration is allowed. Set to `false` to prevent new
sign-ups."*

**Controprova**: `backend/app/api/v1/auth.py:189-206` (`register()`) non chiama mai
`is_registration_enabled()`. La funzione esiste ed è corretta
(`backend/app/services/global_settings_service.py:95-101`, legge
`enable_registration` con default `true`), ma **nessun chiamante la invoca** in
tutto il repository (verificato con `grep` su `backend/`). L'endpoint crea sempre
l'utente, indipendentemente dal valore del setting.

**Classificazione**: Contraddizione · **Gravità**: 🔴 critical · **Confidenza**: Alta
(tracciata riga per riga, zero chiamanti).

**Impatto**: un amministratore che disattiva le registrazioni dalla UI Global
Settings **non ottiene alcuna protezione** — chiunque può ancora registrarsi via
`/api/v1/auth/register` — e non ha modo di accorgersene dall'interfaccia.

**Direzione di correzione**: aggiungere il controllo `is_registration_enabled()`
in testa a `register()` (decidere se il primo utente deve poter registrarsi anche a
registrazioni chiuse, per non bloccare un'installazione nuova), oppure — se si
preferisce agire solo sui report — segnalare esplicitamente nella pagina che il
controllo non è ancora applicato lato server.

> Nota di correlazione: lo stesso reperto è già stato registrato indipendentemente
> nel report `01_api_layer.md` (A1) per il layer API. Qui è confermato dal lato
> "cosa promette la documentazione admin", non duplicato: la pagina `settings.en.md`
> è quella che l'amministratore legge prima di premere l'interruttore, quindi la
> correzione minima immediata è documentale (avviso), quella strutturale è nel
> codice (A1 di `01_api_layer.md`).

**✅ Stato remediation (2026-08-05): implementato.** `register()` chiama ora
`is_registration_enabled()` e risponde `403 New user registration is disabled`
quando l'impostazione è falsa. È stata scelta l'**esenzione bootstrap**: il primo
utente in assoluto (`count_users() == 0`) può sempre registrarsi, altrimenti
un'installazione nuova con registrazioni chiuse resterebbe inaccessibile per sempre.
Evidenza: `backend/app/api/v1/auth.py:186-192`.

> **Conseguenza operativa emersa solo in fase di verifica finale, da conoscere prima
> di toccare quest'area.** Rendere l'impostazione *effettiva* ha reso la suite di test
> API dipendente dal suo valore: quasi ogni test crea il proprio utente via
> `POST /auth/register`. Finché il controllo non esisteva, un `enable_registration`
> lasciato a `false` nel database di test era del tutto innocuo; da ora in poi
> propaga un fallimento a cascata su ~50 test, con il messaggio
> `New user registration is disabled` che **non indica in alcun modo la causa reale**
> (uno stato residuo, non un difetto del test che fallisce).
>
> I test di `test_auth_api.py` che disattivano deliberatamente la registrazione la
> ripristinano già in un `finally`, ma quel ripristino salta se il processo viene
> ucciso a metà — Ctrl-C, server di test morto, un run Playwright parallelo che
> ricrea il database sotto i piedi. Lo stato sporco sopravvive quindi al run
> *successivo*. È esattamente ciò che è accaduto durante questa verifica: la prima
> esecuzione della suite API si è fermata a `0/50`.
>
> Mitigazione aggiunta: una fixture di sessione `autouse` in
> `backend/test_scripts/conftest.py` riporta `enable_registration` a `true`
> all'avvio della sessione di test. Non sostituisce la pulizia per-test — gira una
> volta sola all'inizio, quindi i test che disattivano la registrazione *durante* la
> sessione continuano a funzionare come prima — ma impedisce che uno stato residuo
> si travesta da regressione del prodotto.

---

### 🔴 A2 — `require_email_verification` non ha alcuna implementazione

**Dove**: `mkdocs_src/docs/admin/settings.en.md:40,61`
**Claim**: *"Whether new users must verify their email before accessing the
system."*

**Controprova**: `grep -rn "require_email_verification" backend/` restituisce solo
la dichiarazione dello schema (`backend/app/schemas/settings.py:93`) e la menzione
nel docstring di `backend/app/db/models.py:368`. Non esiste alcun accessor (a
differenza di `enable_registration`, che almeno ha `is_registration_enabled()`) né
alcun punto del codice che legga questo valore per bloccare l'accesso.

**Classificazione**: Contraddizione · **Gravità**: 🔴 critical · **Confidenza**: Alta.

**Impatto**: stesso schema di A1 ma un gradino più indietro — l'impostazione è
puramente decorativa, zero logica di verifica email esiste nel codebase.

**Direzione di correzione**: implementare la verifica email, oppure rimuovere
l'impostazione dalla UI/documentazione finché non è supportata. Lasciare
all'amministratore un interruttore che non fa niente è l'opzione peggiore.

---

### 🟡 A3 — `max_file_upload_mb` non si applica ai broker report

**Dove**: `mkdocs_src/docs/admin/settings.en.md:41,69`
**Claim**: *"Maximum file upload size in megabytes. **Applies to all uploads
(static resources and broker reports)**."*

**Controprova**: `get_max_upload_mb()` (`global_settings_service.py:85-91`) è usato
**solo** in `backend/app/api/v1/uploads.py:169` (upload di file statici/Files page).
L'endpoint di upload dei broker report,
`backend/app/api/v1/brokers.py:494` (`upload_file`, `/brim/upload`), usa invece una
costante hard-coded indipendente:

```python
# backend/app/api/v1/brokers.py:488
MAX_FILE_SIZE = 10 * 1024 * 1024
...
if len(content) > MAX_FILE_SIZE:   # riga 527 — non legge mai il global setting
```

**Classificazione**: Contraddizione · **Gravità**: 🟡 major · **Confidenza**: Alta
(due percorsi di codice confrontati direttamente, uno legge il setting, l'altro no).

**Impatto**: un amministratore che alza `max_file_upload_mb` a, ad esempio, 50 MB
per caricare report broker più grandi **non ottiene l'effetto promesso**: i file
statici rispetteranno il nuovo limite, i report broker resteranno bloccati a 10 MB
fissi, senza alcun messaggio che spieghi la discrepanza (l'errore 413 riporta
comunque "Maximum size: 10 MB", che rinforza la confusione).

**Direzione di correzione**: far leggere anche `brokers.py` da
`get_max_upload_mb()` (stesso pattern già corretto in `uploads.py:169`), oppure
correggere la doc per dire esplicitamente "solo Files/upload statici; i broker
report hanno un limite fisso di 10 MB non configurabile".

**✅ Stato remediation (2026-08-05): implementato.** L'endpoint di upload dei report
broker usa ora lo stesso helper `get_max_upload_mb()` già impiegato per i file
statici (`backend/app/api/v1/brokers.py:76,518`), quindi `max_file_upload_mb` vale
davvero su entrambe le superfici come la pagina prometteva. La documentazione non va
ridimensionata: era il codice ad applicare il limite solo a metà.

---

### 🟡 A4 — `default_theme` esiste ma non è documentato

**Dove**: `mkdocs_src/docs/admin/settings.en.md` (intera pagina — tabella `## 📋
Available Settings` righe 36-47 e `## 🗂️ Categories` righe 50-73)

**Controprova**: `backend/app/schemas/settings.py:141-145` definisce
`default_theme` (`type: str, default: "auto"`) in `GLOBAL_SETTINGS_DEFAULTS`, alla
pari di `default_currency`/`default_language`. È pienamente cablato:

- letto da `backend/app/services/settings_service.py:56,92` per impostare il tema
  di default dei nuovi utenti;
- esposto nella UI in `frontend/src/lib/components/settings/tabs/GlobalSettingsTab.svelte:48`
  dentro il gruppo `defaults` (`keys: ['default_currency', 'default_language',
  'default_theme']`) con un selettore dedicato a riga 657;
- coperto da test (`backend/test_scripts/test_services/test_settings_service.py`).

Non compare né nella tabella `## 📋 Available Settings` né nella sezione
`### 🌍 Defaults` di `## 🗂️ Categories`, dove ci si aspetterebbe accanto a
`default_currency` e `default_language`.

**Classificazione**: Omissione · **Gravità**: 🟡 major · **Confidenza**: Alta
(setting live, in UI, testato — non è codice morto).

**Impatto**: un amministratore che consulta la pagina Settings per capire quali
leve di default esistono per i nuovi utenti non scopre che il tema (light/dark/
auto) è configurabile a livello globale.

**Direzione di correzione**: aggiungere una riga nella tabella (`default_theme |
str | auto | Default UI theme for newly registered users (light, dark, auto)`) e
nella sezione `Defaults` delle Categorie.

---

### 🟡 A5 — `scheduler_timezone` non documentato, e "server local time" è impreciso

**Dove**: `mkdocs_src/docs/admin/settings.en.md:44,66` e sezione `## 🕐 Market Data
Scheduler` (voce *"History Sync Times"*)
**Claim**: *"Specific daily times (**server local time**, comma-separated) to
trigger the end-of-day history sync."*

**Controprova**: `backend/app/services/scheduler/settings.py` — il docstring del
modulo e di `load_scheduler_settings()` è esplicito: *"Times are stored in
UTC[...] compute defaults [...] in the configured timezone and convert to UTC"*.
Il fuso orario non è quello del sistema operativo del server, ma un **setting
globale dedicato**, `scheduler_timezone` (letto a riga 80, esposto in
`backend/app/api/v1/settings.py:172,196`), configurabile dall'utente tramite un
selettore IANA in `frontend/src/lib/components/settings/SchedulerConfigModal.svelte:5-6,50`
(commento del componente: *"Times are stored in UTC. The user selects an IANA
timezone and sees/edits times in that timezone; conversion to/from UTC happens on
open/save."*). `scheduler_timezone` **non esiste** in
`GLOBAL_SETTINGS_DEFAULTS` (`backend/app/schemas/settings.py`) né nella tabella o
nelle Categorie di `settings.en.md`.

**Classificazione**: Contraddizione (per "server local time") + Omissione (per
`scheduler_timezone`) · **Gravità**: 🟡 major · **Confidenza**: Alta (commento del
componente frontend è inequivocabile).

**Impatto**: un amministratore che imposta `06:00,23:00` aspettandosi l'ora del
sistema operativo del server ottiene invece l'ora nel fuso configurato nella UI
(default `UTC` se mai impostato) — su un server con `TZ` di sistema diverso da UTC
i due comportamenti divergono silenziosamente.

**Direzione di correzione**: sostituire "server local time" con "in the timezone
configured via the Scheduler Configuration modal (stored internally in UTC)", e
aggiungere `scheduler_timezone` sia alla tabella dei settings sia alla sezione
Sync & Uploads/Categories.

---

## Reperti — `cli_tools.en.md`

### 🟡 B1 — `--workers N` non ha alcun calcolo automatico

**Dove**: `mkdocs_src/docs/admin/cli_tools.en.md:24-25`
**Claim**:
```
# With auto-calculated workers (2 × (CPU-1))
pipenv run ./dev.py server --workers N
```

**Controprova**: il parser di `server` in `dev.py:2073` definisce
`--workers`/`-w` come `type=int, default=1` — un intero letterale, senza alcuna
parola chiave "auto" o calcolo derivato dalla CPU. L'unica formula
`cpu_count`-based nel file (`dev.py:821-824`, `worker_count = explicit_workers if
explicit_workers else max(2, cpu_count)`) appartiene a **tutt'altro comando**
(`mkdocs gallery`, worker Playwright per gli screenshot), non a `server`.

**Classificazione**: Contraddizione · **Gravità**: 🟡 major · **Confidenza**: Alta
(nessuna riga di `cmd_server`/argparse la implementa; confrontato l'unico match
`cpu_count` del file, appartenente a un comando diverso).

**Impatto**: l'amministratore legge "auto-calculated" e può pensare che digitare
letteralmente `--workers N` (o comunque un valore qualsiasi) faccia calcolare da
solo il numero ottimale — invece deve calcolare lui stesso `2 × (CPU-1)` (formula
peraltro atipica: quella classica da letteratura Gunicorn è `(2 × CPU) + 1``) e
passarlo come intero.

**Direzione di correzione**: riformulare come
`# --workers <n>: manually size to your CPU count (e.g. 2 × cores - 1)`,
rimuovendo ogni riferimento a un calcolo automatico assente.

**✅ Stato remediation (2026-08-05): implementato, ma con esito opposto alla
direzione suggerita — e la doc resta comunque da correggere.** Invece di rimuovere
la promessa dalla pagina, è stato aggiunto il calcolo automatico: `--workers`
accetta ora un intero positivo, `0` oppure `auto` — gli ultimi due attivano
entrambi il calcolo, mentre un valore negativo o non numerico viene rifiutato con
un messaggio esplicito. La formula è `max(1, 2 × (CPU − 1))`
(`dev.py:138-152`, `_resolve_server_workers`), la stessa già usata altrove in
`dev.py` (mantenuta per coerenza interna, pur non essendo la classica Gunicorn
`(2 × CPU) + 1`).

⚠️ **Lato documentale, corretto separatamente il 2026-08-05.**
`cli_tools.en.md` descriveva `--workers N` come se un valore qualsiasi attivasse il
calcolo automatico. Il testo EN è stato riallineato al comportamento reale (`auto`
o `0` per il calcolo, un intero per il valore esplicito). Le versioni IT/FR/ES della
stessa pagina restano al testo precedente e vanno riallineate nel batch multilingua,
insieme a tutte le altre correzioni EN di questo audit.

---

### 🟡 B2 — Il commento su `user create` confonde CLI e registrazione web

**Dove**: `mkdocs_src/docs/admin/cli_tools.en.md:43`
**Claim**:
```
# Create a user (first user becomes admin automatically)
pipenv run ./dev.py user create <username> <email> <password>
```

**Controprova**: `scripts/user_cli.py` — `register_subparser()` mappa
`create → create-superuser` (riga 372: `command_map = {"create":
"create-superuser", ...}`), e `cmd_create_superuser()` (riga 100-120) chiama
sempre `user_service.create_user(..., is_superuser=True)`, **senza condizioni**.
La logica "il primo utente diventa admin" esiste solo nell'endpoint web
`backend/app/api/v1/auth.py:189-206` (`is_first_user = user_count == 0`), un
percorso di codice completamente diverso.

**Classificazione**: Dettaglio obsoleto · **Gravità**: 🟡 major · **Confidenza**:
Alta (dispatcher e funzione chiamata letti direttamente).

**Impatto**: il commento lascia intendere che solo il primo utente creato da CLI
diventi admin; in realtà **ogni** utente creato con `./dev.py user create` è
sempre un superuser, primo o centesimo che sia. Non è un bug (è il comportamento
voluto per uno strumento amministrativo), ma il commento descrive un
comportamento — quello della registrazione web — che non è quello del comando
documentato.

**Direzione di correzione**: cambiare il commento in
`# Create a user (always created as superuser/admin via CLI)`, per non confonderlo
con la regola "first user becomes admin" della pagina `host_installation.en.md`
(quella sì corretta, ma per la registrazione via browser).

---

### 🟢 B7 — Prerequisito "running server" per `mkdocs gallery` sovrastimato

**Dove**: `mkdocs_src/docs/admin/cli_tools.en.md:89` e
`docker_advanced.en.md:172-178` (*"a running server with populated test data"*)

**Controprova**: `cmd_mkdocs_gallery()` (`dev.py:755-830`) popola da solo il
database di test (a meno di `--no-populate`) e lancia
`npm run test:e2e -- gallery.spec.ts`; `frontend/playwright.config.ts:73-78`
definisce un blocco `webServer` con `reuseExistingServer: !process.env.CI` — in
locale, se nessun server sulla porta di test è già attivo, Playwright **lo avvia
da solo**.

**Classificazione**: Dettaglio obsoleto · **Gravità**: 🟢 minor · **Confidenza**:
Media (comportamento dedotto dalla config Playwright, non eseguito end-to-end in
questo audit per rispettare il vincolo "non avviare servizi").

**Impatto**: minimo — l'admin che segue la doc alla lettera avvierà comunque un
server prima, superfluo ma innocuo.

**Direzione di correzione**: chiarire che il comando può avviare da solo un server
di test se nessuno è già in ascolto sulla porta configurata, rendendo il
prerequisito esplicitamente opzionale.

---

## Reperti — `docker_advanced.en.md`

### 🔴 B3 — `./dev.py mkdocs --gallery` non esiste: fallisce con errore argparse

**Dove**: `mkdocs_src/docs/admin/docker_advanced.en.md:172-176`
**Claim**:
```
!!! tip "Documentation with screenshots"
    ...
    ./dev.py mkdocs --gallery
```

**Controprova — riprodotta direttamente** (comando in sola lettura, nessun side
effect: fallisce in fase di parsing prima di qualunque azione):

```
$ python3 dev.py mkdocs --gallery
usage: dev.py [-h] command ...
dev.py: error: unrecognized arguments: --gallery
```

Il parser reale (`dev.py:2167-2186`) registra `gallery` come **sottocomando**
(`mk_sub.add_parser("gallery", ...)`), non come flag di `mkdocs`. La stessa
funzionalità è documentata correttamente altrove nello stesso set di pagine:
`cli_tools.en.md:90` scrive `./dev.py mkdocs gallery` (corretto).

**Classificazione**: Contraddizione · **Gravità**: 🔴 critical (comando copiato/
incollato da un amministratore fallisce immediatamente) · **Confidenza**: Alta —
riprodotto con esecuzione diretta, non dedotto.

**Impatto**: chiunque copi il comando dalla guida Docker riceve un errore
argparse invece di generare gli screenshot; è anche un'incoerenza interna fra due
pagine dello stesso manuale admin.

**Direzione di correzione**: correggere in `./dev.py mkdocs gallery` (senza `--`).

---

### 🟡 B9 — Percorso di distribuzione GHCR/`docker-compose.prod.yml` non documentato

**Dove**: `mkdocs_src/docs/admin/docker_advanced.en.md` (intera pagina — non
menziona mai il file) e `index.en.md:15` (voce *"Advanced Docker"* nell'elenco
Guide)

**Controprova**: il repository contiene `docker-compose.prod.yml` (immagine
`ghcr.io/librefolio/librefolio:latest`, nessun build locale, nessuna porta di
test), pubblicato e mantenuto dalla stessa pipeline di rilascio
(`.github/workflows/release.yml:168` pubblica `ghcr.io/librefolio/librefolio` con
tag `latest`/`nightly`/versione semantica). `README.md:102,106` lo referenzia
esplicitamente come percorso di installazione "senza build" (`curl -L
.../docker-compose.prod.yml -o docker-compose.yml`). **Nessuna** delle 8 pagine
admin nomina questo file o questo percorso: `docker_advanced.en.md` descrive solo
il flusso `./dev.py docker build` + `docker-compose.yml` locale.

**Classificazione**: Omissione · **Gravità**: 🟡 major · **Confidenza**: Alta (file
verificato nel repo, uso confermato in due punti: workflow di release e README).

**Impatto**: un amministratore che legge solo il manuale admin (senza incrociare
il README del progetto) non scopre mai che esiste un'immagine pre-costruita
pubblica scaricabile senza clonare il repository né installare Node/Pipenv/Docker
build — l'unico percorso descritto richiede sempre una build locale.

**Direzione di correzione**: aggiungere in `docker_advanced.en.md` una sezione (o
almeno un rimando) sul deployment "immagine pre-costruita" via
`docker-compose.prod.yml`/GHCR, distinguendolo esplicitamente dal percorso
`./dev.py docker build` documentato.

---

### 🟡 B11 — Backup Docker non menziona il rischio WAL

**Dove**: `mkdocs_src/docs/admin/docker_advanced.en.md:304-315` (*"💾 3. Database
Backup"*)
**Claim**:
```bash
cp ./LibreFolio-data/sqlite/app.db /path/to/backups/app.db-$(date +%F)
```
*"No `docker cp` needed [...] simply backing up [...] is sufficient."*

**Controprova**: `backend/app/db/session.py:26,34` configura SQLite in modalità
**WAL** (`PRAGMA journal_mode=WAL`), confermato anche nella pagina
`filesystem.en.md:31-33` (*".db-wal e .db-shm sono file WAL temporanei... gestiti
da SQLite"*). Nessun checkpoint automatico allo shutdown è stato trovato in
`backend/app/main.py` (lifespan analizzato, nessuna chiamata a
`wal_checkpoint`/simile). In WAL mode i dati scritti di recente possono risiedere
nel file `.db-wal` separato finché non avviene un checkpoint: copiare **solo**
`app.db` mentre il container è **in esecuzione**, senza fermarlo né includere
`.db-wal`/`.db-shm`, rischia un backup incompleto o incoerente. La stessa pagina
`filesystem.en.md:127-129` prescrive correttamente, per il backup da host,
*"Stop the server first (to ensure database consistency)"* — la sezione Docker
equivalente in `docker_advanced.en.md`, per lo stesso identico rischio tecnico, non
lo prescrive affatto.

**Classificazione**: Limite non documentato · **Gravità**: 🟡 major (rischio di
perdita/incoerenza dati in fase di ripristino, non immediatamente visibile) ·
**Confidenza**: Media-Alta (rischio strutturale di WAL dedotto da codice e
confermato in un'altra pagina del set; non è stato riprodotto un backup corrotto
per rispettare il vincolo "non modificare/avviare servizi").

**Impatto**: un backup automatizzato preso a container attivo (cron con lo
snippet esatto della doc) può includere una `app.db` senza le transazioni ancora
solo nel WAL, producendo un ripristino con dati mancanti — senza alcun errore
visibile al momento del backup.

**Direzione di correzione**: allineare la sezione Docker alla stessa cautela già
presente in `filesystem.en.md` — fermare il container (`docker compose stop`)
prima del backup, oppure includere sempre `*.db-wal`/`*.db-shm` insieme a
`app.db`, oppure eseguire un `PRAGMA wal_checkpoint(TRUNCATE);` prima della copia.

---

## Reperti — `service_exposure.en.md`

### 🔴 B4 — URL di download di `custom_startup.sh` restituisce 404

**Dove**: `mkdocs_src/docs/admin/service_exposure.en.md:416,420`
**Claim**:
```
wget https://raw.githubusercontent.com/Librefolio/LibreFolio/main/docs/static/tailscale-guide/custom_startup.sh
```

**Controprova — riprodotta direttamente** (richiesta HTTP di sola lettura verso
GitHub, nessuna modifica):

```
$ curl (fetch) .../main/docs/static/tailscale-guide/custom_startup.sh
→ 404

$ curl (fetch) .../main/mkdocs_src/docs/static/tailscale-guide/custom_startup.sh
→ 200 OK (contenuto dello script confermato)
```

Il file esiste nel repository al percorso reale
`mkdocs_src/docs/static/tailscale-guide/custom_startup.sh` (confermato anche in
`mkdocs_src/site/static/tailscale-guide/`, copia pubblicata). L'URL nella doc omette
il segmento `mkdocs_src/`.

**Classificazione**: Navigazione/link · **Gravità**: 🔴 critical (comando core
della procedura Livello 4 fallisce, bloccando l'intero setup multi-Funnel) ·
**Confidenza**: Alta — riprodotto con richiesta HTTP diretta, esito 404 vs 200
confrontato.

**Impatto**: chiunque segua "Level 4: Advanced Multi-Funnel Exposure" alla lettera
si blocca al primo comando `wget`, senza indicazioni su come procedere altrimenti
(il link HTML alla riga 416 ha lo stesso URL rotto, quindi anche il click sul link
in pagina fallisce, non solo l'esempio da terminale).

**Direzione di correzione**: correggere entrambe le occorrenze in
`https://raw.githubusercontent.com/Librefolio/LibreFolio/main/mkdocs_src/docs/static/tailscale-guide/custom_startup.sh`.

---

## Reperti — `configuration.en.md`

## Reperti — `host_installation.en.md`

### 🟢 B12 — `./dev.py install` ha 4 step, la doc ne descrive 3

**Dove**: `mkdocs_src/docs/admin/host_installation.en.md:89-97`
**Claim**:
```
Under the hood, this command will:
1. Initialize the Python virtual environment and install packages via pipenv.
2. Install frontend SvelteKit dependencies via npm.
3. Install Playwright browser binaries...
```

**Controprova**: `cmd_install()` (`dev.py:1770-1810`) esegue **quattro** passi
numerati esplicitamente nell'output CLI stesso:
`[1/4] pipenv install --dev`, `[2/4] npm install` (root, strumenti come Prettier/
Playwright test runner), `[3/4] npm ci` (frontend), `[4/4] playwright install
chromium`. Il passo `[2/4]` (dipendenze npm alla radice del progetto, da
`package.json` root: `prettier`, `@playwright/test`) non è menzionato nella doc.

**Classificazione**: Dettaglio obsoleto · **Gravità**: 🟢 minor · **Confidenza**:
Alta (funzione letta interamente, 4 blocchi `print(Colors.info("[N/4]..."))`
inequivocabili).

**Impatto**: basso — è un passo trasparente per l'utente (nessuna azione richiesta
da parte sua), ma la doc sotto-conta gli step reali eseguiti dal comando.

**Direzione di correzione**: aggiungere il punto mancante ("Install root-level
Node tooling via npm install") come secondo step della lista.

---

## Reperti — nota trasversale (non un reperto a sé)

### ⚪ C1 — Terminologia "LRU" imprecisa per la cache di anteprima

**Dove**: `mkdocs_src/docs/admin/configuration.en.md:25` (`PREVIEW_CACHE_MAX_MB`)
**Claim**: *"Cached thumbnails are evicted using the **LRU** algorithm when the
limit is reached."*

**Controprova**: `backend/app/api/v1/uploads.py:54-119` — la classe `PreviewCache`
evince le voci con `min(self.entries, key=lambda k: self.entries[k][2])`, dove
l'indice `[2]` è il **timestamp di scrittura** (`put`), mai aggiornato da `get()`
(righe 83-91, nessuna riscrittura della entry in lettura). Questo è eviction per
**vecchiaia di scrittura** (prossimo a un FIFO temporizzato + TTL), non "least
recently **used**" in senso stretto: una voce scritta una sola volta ma letta
molto di frequente verrebbe comunque espulsa prima di una scritta più di recente
ma mai riletta. Il termine "LRU" proviene dal commento originale nel codice stesso
(`uploads.py:54`, *"In-memory LRU cache"*), quindi la doc eredita — correttamente
— la stessa imprecisione già presente nel commento sorgente.

**Classificazione**: Dettaglio obsoleto · **Gravità**: ⚪ info (nessun impatto
operativo: la cache funziona, solo l'etichetta dell'algoritmo è imprecisa;
segnalato come miglioramento/precisazione terminologica, non come difetto da
correggere con priorità) · **Confidenza**: Media (letta la logica di eviction;
non misurato l'effetto pratico su un carico reale).

**Direzione di correzione**: correggere sia il commento sorgente sia la doc in
"evicted oldest-write-first with 1h TTL" (o implementare un vero LRU aggiornando
il timestamp su `get()`, se il comportamento LRU è quello desiderato).

---

## Campioni verificati (nessun reperto)

Claim controllate esplicitamente contro il codice e risultate **corrette**:

| Claim | Pagina | Fonte codice |
|---|---|---|
| Rotazione log settimanale, 52 settimane, gzip | `filesystem.en.md:57-69` | `backend/app/logging_config.py:10,177-187` |
| Tabella livelli log (TRACE 5 … CRITICAL 50) | `filesystem.en.md:60-77` | `backend/app/logging_config.py:14-26` |
| SQLite in modalità WAL | `filesystem.en.md:31` | `backend/app/db/session.py:26,34` |
| Sidecar `{uuid}.json` con uploader/mime/data | `filesystem.en.md:43-49` | `backend/app/services/static_uploads.py:142-175,320` |
| `global_settings`, chiave/valore stringa, `ON CONFLICT DO NOTHING` | `settings.en.md:104-108` | `backend/app/db/models.py:371`, `backend/app/services/settings_service.py:188-210` |
| `session_ttl_hours` guida davvero la scadenza JWT | `settings.en.md:38` | `backend/app/services/auth_service.py:103`, `global_settings_service.py:75-81` |
| `max_file_upload_mb` applicato ai file statici | `settings.en.md:41` | `backend/app/api/v1/uploads.py:169` |
| `docker exec` ≡ `docker compose exec librefolio python dev.py <cmd>` | `docker_advanced.en.md:126-134` | `dev.py:1534-1548` (`cmd_docker_exec`) |
| Healthcheck `GET /api/v1/system/health` ogni 30s | `docker_advanced.en.md`/`docker-compose.yml` | `backend/app/api/v1/system.py:194`, `docker-compose.yml` |
| UID/GID default 1000:1000, entrypoint root→gosu | `docker_advanced.en.md` | `Dockerfile`, `entrypoint.sh` |
| `./dev.py docker build` auto-builda frontend+docs, rifiuta senza `.env` | `docker_advanced.en.md` | `dev.py:_check_env_file`, `_docker_ensure_assets_built` |
| Test DB nel writable layer, non bind-mount | `docker_advanced.en.md` | `docker-compose.yml` (nessun volume per `backend/data/test`) |
| JWT_SECRET auto-generato se assente, condiviso fra worker via `dev.py server` | `index.en.md`, `configuration.en.md` | `backend/app/services/auth_service.py:84`, `dev.py:264` |
| `user create/list/reset/promote/demote/init-settings` (sintassi CLI) | `cli_tools.en.md:40-56` | `scripts/user_cli.py:326-356` |
| `--host`/`--port`/`-p`/`--workers`/`-w`/`--no-scheduler` (flag reali) | `host_installation.en.md` | `dev.py:2068-2079` |
| Immagine locale `librefolio:latest`, due porte (6040/6041) | `docker_advanced.en.md` | `docker-compose.yml` |
| Tag GHCR `nightly` esiste realmente (branch `dev`) | `service_exposure.en.md` (esempio) | `.github/workflows/release.yml:172` |

## Non verificabili / non riprodotti

- **Livelli 1-4 Tailscale** (`service_exposure.en.md`): comandi `tailscale up
  --advertise-routes`, `tailscale funnel`, configurazione ACL/ Funnel sulla
  console Tailscale — dipendono da un servizio SaaS esterno e da hardware fuori
  dal repository. Non riproducibili in questo audit (nessun avvio di servizi
  consentito); classificati "Non verificabile", non trattati come bug.
- **Screenshot/gallery UI** (`settings.en.md`, placeholder `<img
  class="gallery-img" data-category="settings" data-name="...">`): la presenza
  reale delle immagini generate da `./dev.py mkdocs gallery` non è stata
  verificata (richiederebbe build+server attivo, esclusi dal vincolo del task).
- **Formula `2 × (CPU-1)`** (B1): non è stato possibile determinare se questa
  fosse una formula reale rimossa in un refactoring precedente o un'invenzione
  mai implementata — la ricerca nella history del file non rientra nello scope
  "solo worktree corrente" di questo audit.

## Sintesi

| Gravità | Conteggio | ID |
|---|---:|---|
| 🔴 critical | 4 | A1, A2, B3, B4 |
| 🟡 major | 7 | A3, A4, A5, B1, B2, B9, B11 |
| 🟢 minor | 2 | B7, B12 |
| ⚪ info | 1 | C1 |
| **Totale reperti** | **14** | — |

Pagine verificate senza reperti propri: `configuration.en.md` (0),
`filesystem.en.md` (0), `index.en.md` (0 diretti — condivide B9 come rimando
incrociato dall'elenco Guide).

Reperti concentrati su due nuclei: (1) **`settings.en.md`** — tre interruttori
Global Settings che promettono un comportamento server-side più ampio o diverso
di quello reale (registrazione, verifica email, limite upload broker, fuso orario
scheduler) più un setting mancante (`default_theme`); (2) **comandi CLI/URL non
riproducibili così come scritti** (`mkdocs --gallery`, URL `custom_startup.sh`),
entrambi verificati con esecuzione/richiesta diretta e non per deduzione.

Nessuna pagina admin richiede una riscrittura strutturale: i reperti sono
correzioni puntuali (una riga di codice mancante, un URL, una sintassi di
comando, righe di tabella da aggiungere), ad eccezione del nucleo A1/A2 che è
condiviso con — e già aperto da — il report `01_api_layer.md`.

## Stato remediation — Block 3 (2026-08-05)

I conteggi sopra restano lo snapshot dell'audit. Il manuale inglese corrente e'
stato riallineato al codice per i seguenti reperti:

| Reperti | Stato | Esito |
|---|---|---|
| A4 | ✅ Aggiornato | Aggiunto `default_theme` e distinta la preferenza utente dal default globale. |
| A5 | ✅ Aggiornato | Documentati `scheduler_timezone`, UTC e il significato limitato del default scheduler. |
| B7 | ✅ Aggiornato | Gallery descrive Playwright, server/test data gestiti dal comando e `--no-populate`. |
| B9 | ✅ Aggiornato | Installation documenta stack GHCR production e bind mount `./LibreFolio-data`. |
| B11 | ✅ Aggiornato | Backup Docker richiede stop container e copia completa del bind mount. |
| B12 | ✅ Aggiornato | Host installation documenta Pipenv, root npm, frontend npm ci e Playwright. |

Le traduzioni e la validazione MkDocs completa sono rinviate al batch multi-lingua.
