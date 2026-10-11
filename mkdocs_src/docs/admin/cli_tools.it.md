# 🛠️ Strumenti da riga di comando

`dev.py`, alla radice del progetto, esegue le attività amministrative: avviare il server, gestire gli utenti e mantenere il database. Ogni sezione indica quando un comando richiede che il server sia arrestato.

!!! tip "Dove eseguire i comandi"

    - **Installazione host**: nell'ambiente Pipenv, con il prefisso `pipenv run` usato in questa pagina, oppure dopo `pipenv shell`.
    - **Docker**: nel container in esecuzione, con `docker compose exec librefolio python dev.py <command>` (da un checkout del sorgente, `./dev.py docker exec <command>`). Lì non serve `pipenv run`: l'immagine installa le dipendenze a livello globale. I comandi utente, `db current` e `db check` funzionano lì; `db upgrade` e `db downgrade` no, perché richiedono che il server sia arrestato ([Applicare le migrazioni](#apply-migrations)). I comandi di sviluppo come `test` non fanno parte dell'immagine ([dettagli](docker_advanced.md#docker-exec)).

---

## 🖥️ Avviare il server {: #start-the-server }

```bash
# Standard start, one worker
pipenv run ./dev.py server

# Size the workers to the CPUs (`auto` and `0` do the same)
pipenv run ./dev.py server --workers auto

# Or set the number of workers
pipenv run ./dev.py server --workers 4

# Listen on another port (default: PORT from .env, else 6040)
pipenv run ./dev.py server --port 8080

# Kill whatever already holds the port, then start
pipenv run ./dev.py server --force
```

- 🧮 Più worker gestiscono più richieste contemporaneamente: usali su qualsiasi macchina con più di una CPU. `auto` avvia $\max(1,\ 2\,(n-1))$ worker su $n$ CPU.
- ⏳ Il server compila prima l'interfaccia web e questa documentazione quando mancano o sono obsolete, quindi il primo avvio richiede qualche minuto. Se l'interfaccia non viene compilata, il server non si avvia.
- 🔑 Un riavvio disconnette tutti, a meno che `JWT_SECRET` sia impostato in `.env` (vedi [Configurazione](configuration.md)).

??? note "⚙️ Altre opzioni del server — raramente necessarie"

    | Opzione | Cosa fa |
    | --- | --- |
    | `--host HOST` | Indirizzo su cui ascoltare (predefinito: `HOST` dall'ambiente o `.env`, altrimenti `0.0.0.0`) |
    | `--data-dir PATH` | Usa un'altra directory dati per questa esecuzione, invece di `LIBREFOLIO_DATA_DIR` |
    | `--no-scheduler` | Avvia senza le sincronizzazioni programmate di prezzi e FX |
    | `--rebuild`, `-r` | Ricompila l'interfaccia web anche quando sembra aggiornata |
    | `--debug`, `-d` | Log `DEBUG` e una build di debug dell'interfaccia web |

    Forme brevi: `-w` per `--workers`, `-p` per `--port`, `-f` per `--force`. `--test`, `--coverage` e `--no-reload` sono opzioni di sviluppo: `pipenv run ./dev.py server --help` le elenca tutte.

---

## 👤 Gestire gli utenti

Questi comandi scrivono direttamente nel database, quindi funzionano anche mentre il server è in esecuzione.

### ➕ Creare ed elencare gli utenti

```bash
# Create an administrator account
pipenv run ./dev.py user create <username> <email> <password>

# List all users: ID, username, email, active, administrator
pipenv run ./dev.py user list
```

- 👑 Gli account creati qui sono sempre **amministratori**. Per un account normale, lascia che la persona si registri con **Registrati qui** nella pagina di login (quando la registrazione è aperta nelle [Impostazioni globali](settings.md)), oppure `demote` il nuovo account.
- 🔒 La password deve avere almeno 8 caratteri, con una lettera maiuscola, una lettera minuscola, una cifra e un simbolo.

### 🔑 Reimpostare una password o bloccare un account {: #reset-a-password-or-lock-an-account }

```bash
# Set a new password (same rules as above)
pipenv run ./dev.py user reset <username> <new_password>

# Lock an account out, then let it back in
pipenv run ./dev.py user deactivate <username>
pipenv run ./dev.py user activate <username>
```

- ⏱️ Una reimpostazione non termina le sessioni già aperte: restano valide fino alla scadenza. Per bloccare subito qualcuno, disattiva l'account: gli viene negato l'accesso dalla richiesta successiva.
- 💬 La schermata **Password dimenticata?** dell'app mostra questo comando per entrambe le installazioni: `docker compose exec librefolio python dev.py user reset …` per Docker, e `./dev.py user reset …` per un'installazione host, da eseguire dopo `pipenv shell` o con `pipenv run` davanti.

### 👑 Concedere o rimuovere i diritti di amministratore

```bash
pipenv run ./dev.py user promote <username>
pipenv run ./dev.py user demote <username>
```

`demote` non verifica che rimanga un altro amministratore: se non ne resta nessuno, promuovi di nuovo qualcuno.

---

## 🗄️ Mantenere il database

### ⬆️ Applicare le migrazioni {: #apply-migrations }

Ogni avvio del server applica da solo le migrazioni in sospeso, quindi raramente ti serve farlo. Per farlo manualmente, **arresta il server** prima: `db upgrade` rifiuta di essere eseguito mentre il server risponde sulla porta configurata.

```bash
# Apply pending migrations
pipenv run ./dev.py db upgrade

# Show the migration the database is at
pipenv run ./dev.py db current

# Look for missing CHECK constraints: changes nothing, exits with 1 if any
pipenv run ./dev.py db check

# Upgrade and check another database file, such as a copy
pipenv run ./dev.py db upgrade /path/to/copy/app.db
pipenv run ./dev.py db check /path/to/copy/app.db
```

- 📄 Senza un percorso, i comandi usano il database configurato. Un percorso indica un altro file SQLite: uno relativo parte dalla radice del progetto, da qualunque punto tu esegua il comando. Il file deve esistere, tranne per `db upgrade`, che lo crea (cartella inclusa) e lo aggiorna.
- 🐳 In Docker, il percorso è dentro il container, dove `LibreFolio-data/` è `/app/backend/data/prod-docker` (il database è `sqlite/app.db` al suo interno). `db current` e `db check` funzionano nel container in esecuzione: `docker compose exec librefolio python dev.py db current <path>`. `db upgrade` e `db downgrade` richiedono che il server sia arrestato (`docker compose stop librefolio`), poi un container temporaneo: `docker compose run --rm librefolio python dev.py db upgrade <path>` ([dettagli](docker_advanced.md#docker-exec)).

### 🩹 Correzioni post-migrazione {: #post-migration-fixes }

Subito dopo le migrazioni, ogni avvio esegue anche le **correzioni post-migrazione**: riparazioni che una migrazione non può fare. Di solito non c'è nulla da fare. Il log (l'output del server, salvato anche in `logs/`) può mostrare:

- ✅ `Post-migration fixes applied and verified`: è stata eseguita una riparazione. Su un database grande quell'avvio è più lento, una volta sola.
- ⚠️ `Post-migration fix failed`: il database è stato lasciato com'era e il server è partito normalmente. L'avviso fornisce l'errore e la copia del database conservata accanto al database finché non la elimini, come `app.db.pre-autoincrement-20261008T101500Z.bak`. La correzione viene ritentata al prossimo avvio.
- 🩺 `Post-migration fixes skipped`: non è stato possibile creare la copia, oppure il database non supera il controllo di integrità di SQLite. Non è stato modificato nulla.

Il file vuoto `app.db.post-migration.lock`, accanto al database, fa sì che le esecuzioni si alternino quando più worker partono insieme: lascialo al suo posto.

La prima correzione, **`autoincrement`**, assicura che l'id di un utente, broker, asset, transazione, percorso di conversione FX o evento asset eliminati non venga mai assegnato a uno nuovo. Durante la conversione di un database, elimina le cartelle dei report dei broker che non esistono più, così che un nuovo broker non possa ereditarle.

??? tip "⌨️ Eseguire le correzioni manualmente — per visualizzarle in anteprima o ritentare una fallita"

    **Arresta il server** prima (lo script non lo verifica), poi esegui dalla radice del progetto:

    ```bash
    # Preview: report what would be fixed, change nothing
    pipenv run python -m backend.app.db.post_migration --dry-run

    # Apply the fixes
    pipenv run python -m backend.app.db.post_migration
    ```

    Lo script stampa ogni correzione come `clean` (nulla da fare), `would_apply` (prova a vuoto), `applied` o `failed`, con le cartelle dei broker orfani, una copia conservata e qualsiasi errore, ed esce con `1` quando qualcosa è fallito. `--db PATH` e `--data-dir PATH` lo puntano a un altro database o a un'altra directory dati.

🔗 Come funzionano internamente le correzioni: [Schema del database — Correzioni post-migrazione](../developer/architecture/database/index.md#post-migration-fixes).

### 🔧 Aggiungere le impostazioni globali mancanti

```bash
pipenv run ./dev.py user init-settings
```

Ogni avvio aggiunge le [Impostazioni globali](settings.md) mancanti con i loro valori predefiniti; questo comando fa lo stesso senza avviare il server e non modifica mai un valore già impostato.

### 🧹 Reimpostare il database

```bash
pipenv run ./dev.py db create-clean
```

!!! warning "Tutti i dati andranno persi"

    `db create-clean` elimina il database e ne crea uno vuoto. Come `db upgrade`, rifiuta di essere eseguito mentre il server è attivo. I file caricati e i report dei broker restano sul disco: vedi [Inizializzazione e reset del database](host_installation.md#database-reset).

---

## 📋 Albero completo dei comandi

```bash
# Every command, by category
pipenv run ./dev.py --help

# The options of one command
pipenv run ./dev.py server --help
```

??? info "👩‍💻 Comandi per sviluppatori e documentazione"

    - **Frontend**: `pipenv run ./dev.py front build`, `front dev`, `front check` — vedi [Sviluppo frontend](../developer/frontend/index.md)
    - **Testing**: `pipenv run ./dev.py test all` — vedi [Procedura dettagliata dei test](../developer/test-walkthrough/index.md)
    - **API Client**: `pipenv run ./dev.py api sync` — vedi [Panoramica API](../developer/api/overview.md)
    - **i18n**: `pipenv run ./dev.py i18n audit` — vedi [Internazionalizzazione](../developer/frontend/i18n.md)
    - **Documentazione**: `pipenv run ./dev.py mkdocs deploy` pubblica questa documentazione su GitHub Pages; `pipenv run ./dev.py mkdocs gallery` rigenera i suoi screenshot con Playwright su un server di prova (`--no-populate` mantiene i dati di test attuali).

    Il toolkit completo per sviluppatori è nella [Guida al flusso di lavoro dello sviluppatore](../developer/dev_workflow.md).
