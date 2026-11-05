# 🛠️ Strumenti da riga di comando

`dev.py`, nella radice del progetto, esegue le attività amministrative: avviare il server, gestire gli utenti, mantenere il database ed eseguire il backup dell'istanza. Ogni sezione indica quando un comando richiede l'arresto del server.

!!! tip "Dove eseguire i comandi"

    - **Installazione su host**: nell'ambiente Pipenv, con il prefisso `pipenv run` usato in questa pagina, oppure dopo `pipenv shell`.
    - **Docker**: nel container in esecuzione, con `docker compose exec librefolio python dev.py <command>` (da un checkout dei sorgenti, `./dev.py docker exec <command>`, che lo esegue come utente del server invece che come root). Lì non c'è `pipenv run`: l'immagine installa le dipendenze globalmente. I comandi utente, `db current`, `db check`, `backup create`, `backup inspect`, `backup restore`, `backup decrypt` e `backup pending` funzionano lì ([Backup con Docker](cli_backup.md#backup-docker)); `db upgrade` e `db downgrade` no, perché richiedono il server arrestato ([Applicare le migrazioni](#apply-migrations)). I comandi di sviluppo come `test` non fanno parte dell'immagine ([dettagli](docker_advanced.md#docker-exec)).

!!! info "📚 Questa guida è su più pagine"

    Oltre a questa pagina: [Strumenti di amministrazione CLI: backup](cli_backup.md).

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
- ⏳ Il server compila prima l'interfaccia web e questa documentazione quando mancano o sono obsolete, quindi il primo avvio richiede alcuni minuti. Se l'interfaccia non viene compilata, il server non si avvia.
- 🔑 Un riavvio disconnette tutti, a meno che `JWT_SECRET` sia impostato in `.env` (vedi [Configurazione](configuration.md)).
- ⏹️ Ctrl+C arresta il server in modo pulito: `dev.py` gli concede fino al [budget di spegnimento](configuration_security.md#shutdown) più 2 secondi per fermarsi (10 secondi per impostazione predefinita), poi lo termina; un secondo Ctrl+C lo termina subito. Un SIGTERM inviato al solo `dev.py`, per esempio da un supervisore di processi, riceve la stessa attesa: `dev.py` lo inoltra al server.

??? note "⚙️ Altre opzioni del server — raramente necessarie"

    | Opzione | Cosa fa |
    | --- | --- |
    | `--host HOST` | Indirizzo su cui restare in ascolto (predefinito: `HOST` dall'ambiente o da `.env`, altrimenti `0.0.0.0`) |
    | `--data-dir PATH` | Usa un'altra directory dei dati per questa esecuzione, invece di `LIBREFOLIO_DATA_DIR` |
    | `--no-scheduler` | Avvia senza le sincronizzazioni pianificate dei prezzi e dei tassi FX |
    | `--rebuild`, `-r` | Ricompila l'interfaccia web anche quando sembra aggiornata |
    | `--debug`, `-d` | Log `DEBUG`, build di debug dell'interfaccia web e pagine di documentazione dell'API (`/api/v1/docs`, `/api/v1/redoc`), che altrimenti sono disattivate |

    Forme brevi: `-w` per `--workers`, `-p` per `--port`, `-f` per `--force`. `--test`, `--coverage` e `--no-reload` sono opzioni di sviluppo: `pipenv run ./dev.py server --help` le elenca tutte.

---

## 👤 Gestire gli utenti

Questi comandi scrivono direttamente nel database, quindi funzionano anche mentre il server è in esecuzione.

Nell'app, gli amministratori gestiscono gli altri account e gli inviti dalla scheda **Utenti** di **Impostazioni › Amministrazione**: vedi [Utenti e inviti](users.md). I comandi seguenti non richiedono un browser: usali su un server senza interfaccia grafica o per superare il [limite utenti](configuration_accounts.md#user-limit).

### ➕ Creare ed elencare utenti

```bash
# Create an administrator account
pipenv run ./dev.py user create <username> <email> <password>

# Create a regular account
pipenv run ./dev.py user create <username> <email> <password> --role user

# List all users: ID, username, email, active, administrator
pipenv run ./dev.py user list
```

- 👑 `user create` crea un **amministratore** a meno che tu non aggiunga `--role user`, che crea un account normale. Le persone possono anche creare il proprio account: con **Registrati qui** nella pagina di accesso mentre **Registrazione** è **Aperta** (su una nuova istanza, anche finché non esiste il suo primo account), oppure con un [link d'invito](#invite) (vedi [Chi può registrarsi](settings.md#registration)).
- 🔒 La password segue le stesse regole dell'app e dell'API: almeno 8 caratteri, con una lettera maiuscola, una lettera minuscola, una cifra e un simbolo. Contano le lettere e le cifre di qualsiasi alfabeto, come `É` o `é`; un simbolo è qualsiasi carattere che non sia una lettera, un numero o uno spazio, come `!`, `_` o `€`. Una password che non rispetta una regola non cambia nulla: il comando stampa `Password does not meet security requirements:` e una riga per ogni regola non rispettata, ciascuna delle quali inizia con il codice della regola, come `digit: the password must contain a digit`, quindi esce con `1`.
- 🔤 Un nome utente non può contenere `@`: all'accesso, LibreFolio interpreta qualsiasi cosa contenga una `@` come indirizzo email. Un nome utente così non cambia nulla: il comando si arresta con l'errore `A username cannot contain @: the sign-in reads it as an email address` ed esce con `1`. Spazi, lettere accentate e segni come `.`, `_`, `-` o `+` vanno bene. Un nome utente deve anche avere da 3 a 50 caratteri, come alla registrazione: uno più corto o più lungo non cambia comunque nulla, il comando si arresta con l'errore `A username must be 3 to 50 characters long` ed esce con `1`. Il comando si arresta anche, con `Username already taken`, se un altro account ha quel nome utente, e, con `Email already registered`, se un altro account ha quell'indirizzo, o se l'indirizzo è il nome utente di un altro account (vedi [`user set-email`](#set-email)), a prescindere dalle maiuscole.
- 📏 Quando l'istanza ha raggiunto il suo [limite utenti](configuration_accounts.md#user-limit), `user create` avvisa `The instance is at its limit (LIBREFOLIO_MAX_USERS: 5 of 5 places taken): the command line creates the account anyway`, poi lo crea: la riga di comando è il modo per superare il limite.

### ✉️ Invitare qualcuno {: #invite }

```bash
# An invitation link for a regular account
pipenv run ./dev.py user invite

# An invitation for an administrator, with a note of whom it is for
pipenv run ./dev.py user invite --admin --email anna@example.com
```

Il comando stampa un link che funziona una sola volta, per 7 giorni. Invialo alla persona: lo aprirà e creerà il proprio account, con il nome utente, l'email e la password che sceglie ([cosa vede](../user/getting-started.md#invitation-link)).

- 👑 `--admin` rende il nuovo account un amministratore; senza di esso, l'account è normale.
- ✉️ `--email` è solo una nota su a chi è destinato l'invito: la persona può registrarsi con un altro indirizzo.
- 🌐 Con [`LIBREFOLIO_PUBLIC_URL`](configuration_accounts.md#accounts) impostata, il link è completo, ad esempio `https://librefolio.example.com/invite#token=…`. Senza, il comando stampa solo il percorso, `/invite#token=…`, e ti ricorda di anteporvi l'indirizzo del tuo server, ad esempio `http://192.168.1.10:6040`. Se la variabile è impostata ma non è un indirizzo `http://` o `https://`, il promemoria dice invece `LIBREFOLIO_PUBLIC_URL is not valid (…)`, con il motivo.
- 🔒 La parte segreta del link viene dopo `#`: i browser non inviano mai quella parte al server, quindi non finisce nei log del server o del proxy. Invia il link per intero.
- 🚪 Gli inviti funzionano mentre **Registrazione** è **Aperta** o **Su invito**. Mentre è **Chiusa**, il comando si arresta con l'errore `Registration is disabled: invitations cannot be created` ed esce con `1`, e anche i link già inviati non funzionano.
- 📏 Un invito occupa un posto del [limite utenti](configuration_accounts.md#user-limit) finché non viene usato o revocato, oppure scade. Al limite, il comando avvisa, poi crea comunque l'invito.
- ⏳ Non c'è un comando per annullare un invito: un link che nessuno ha usato smette di funzionare dopo 7 giorni. Un amministratore può revocarlo prima con **Revoca** nella scheda [Utenti](users.md#open-invitations), oppure tramite l'API: `GET /api/v1/users/invites` elenca gli inviti in attesa, `DELETE /api/v1/users/invites/<id>` ne revoca uno.

### 🔑 Reimpostare una password o bloccare un account {: #reset-a-password-or-lock-an-account }

```bash
# Set a new password (same rules as above)
pipenv run ./dev.py user reset <username> <new_password>

# Lock an account out, then let it back in
pipenv run ./dev.py user deactivate <username>
pipenv run ./dev.py user activate <username>
```

- ⏱️ Una reimpostazione termina le sessioni già aperte: ogni dispositivo connesso all'account viene disconnesso alla sua richiesta successiva. Per bloccare qualcuno definitivamente, disattiva l'account: viene rifiutato dalla sua richiesta successiva, e riattivarlo non ripristina le sue vecchie sessioni.
- 🔗 Una reimpostazione annulla anche qualsiasi link di reimpostazione della password ancora aperto per l'account, chiunque lo abbia creato.
- 👑 `deactivate` rifiuta l'ultimo amministratore attivo: si arresta con l'errore `User '<username>' is the last active administrator: promote or activate another administrator first` ed esce con `1`.
- 📏 Quando l'istanza ha raggiunto il suo [limite utenti](configuration_accounts.md#user-limit), `activate` di un account disattivato avvisa `… the command line reactivates the account anyway`, poi lo riattiva. Non stampa alcun avviso per un account che occupa già il suo posto: uno in attesa dell'email con un link attivo (sotto), o l'amministratore iniziale in attesa del suo link di configurazione.
- 📬 Con la verifica email attiva, `activate` fa entrare subito un account in attesa della sua email — senza avviso sul limite finché il suo link è attivo, poiché il suo posto è già conteggiato — e `deactivate` termina la sua attesa: in entrambi i casi, i link di verifica che gli sono stati inviati smettono di funzionare. Vedi *Verifica email* in [Email](email.md).
- 🏁 Sull'[amministratore iniziale](configuration_accounts.md#initial-admin) ancora in attesa del suo link di configurazione, `reset` e `activate` funzionano come su qualsiasi account: lo configurano senza il suo link, e `activate` non stampa alcun avviso sul limite, poiché l'account occupa già il suo posto. Ciascuno dei due termina definitivamente l'attesa: i suoi link di configurazione vengono invalidati, incluso quello di `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`, e né [`user setup-link`](#setup-link) né un nuovo `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` gliene forniscono un altro. `activate` da solo lascia un account attivo la cui password nessuno conosce, finché `reset` o un [link di reimpostazione](#reset-link) gliene fornisce una; `reset` da solo lo lascia inattivo, finché non interviene `activate`.
- 🚫 Su quell'amministratore ancora in attesa, `deactivate` non configura nulla: annulla il link di configurazione, come fa **Annulla link di configurazione** in [Utenti e inviti](users.md#cancel-setup). Il comando stampa `✅ User '<username>' deactivated`; ogni link di configurazione dell'account viene invalidato, incluso quello di `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`, e l'account continua ad attendere un nuovo link: [`user setup-link`](#setup-link) gliene fornisce uno, e lo stesso fa un nuovo `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` al successivo avvio. Lo stesso token, a un riavvio, non ne fornisce alcuno, poiché l'istanza lo ha già visto.
- 💬 La schermata **Password dimenticata?** dell'app mostra questo comando per entrambe le installazioni: la riga `docker compose exec librefolio sh -c 'exec gosu …' sh user reset …` per Docker (quella in [`docker exec`](docker_advanced.md#docker-exec), che viene eseguita come utente del server, non come root), e `./dev.py user reset …` per un'installazione su host, da eseguire dopo `pipenv shell` o con `pipenv run` davanti. Quando la tua istanza può inviare via email un link di reimpostazione, la schermata mostra prima il modulo email e tiene i comandi in un pannello chiuso per impostazione predefinita ([Password dimenticate](email_flows.md#forgot-password)).

### 🔗 Inviare un link di reimpostazione della password {: #reset-link }

```bash
pipenv run ./dev.py user reset-link <username>
```

Invece di scegliere una nuova password per qualcuno con `user reset`, inviagli questo link: lo apre e sceglie lui stesso la nuova password ([cosa vede](../user/getting-started.md#password-reset-link)).

- ⏱️ Il link funziona una sola volta, per 30 minuti. Un nuovo link per lo stesso account annulla quelli precedenti; una modifica della password o dell'indirizzo email dell'account — nel Profilo dell'utente, oppure con `user reset` o `user set-email` — li annulla tutti.
- 🚪 Una volta impostata la nuova password, ogni dispositivo connesso all'account viene disconnesso, come con `user reset`. Creare il link non disconnette nessuno.
- 🌐 Come per gli [inviti](#invite), il link è completo quando `LIBREFOLIO_PUBLIC_URL` è impostata, e solo il percorso (`/reset-password#token=…`) quando non lo è.

### 🔁 Un nuovo link di configurazione per l'amministratore iniziale {: #setup-link }

```bash
pipenv run ./dev.py user setup-link
```

Quando LibreFolio ha creato l'amministratore da `LIBREFOLIO_ADMIN_EMAIL` al suo primo avvio ([L'amministratore iniziale](configuration_accounts.md#initial-admin)) e nessuno ha ancora usato il suo link di configurazione, questo comando ne stampa uno nuovo: l'amministratore lo apre, sceglie la password e viene autenticato. Usalo quando il link è scaduto, è andato perso o è stato annullato.

- ⏱️ Il link funziona una sola volta, per 72 ore. I link di configurazione emessi prima vengono invalidati, incluso quello di `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`.
- 🚫 Un link annullato — **Annulla link di configurazione** in [Utenti e inviti](users.md#cancel-setup), oppure `user deactivate` sull'amministratore in attesa — lascia l'amministratore in attesa: questo comando gli fornisce un nuovo link.
- 📮 Un nuovo indirizzo per l'amministratore in attesa — `LIBREFOLIO_ADMIN_EMAIL` modificata prima di un riavvio, oppure [`user set-email`](#set-email) — invalida i suoi link di configurazione, che erano diretti al vecchio indirizzo. L'amministratore è ancora in attesa: questo comando gli fornisce un link per il nuovo indirizzo. Lo stesso indirizzo con diverse maiuscole/minuscole delle lettere A-Z non è una modifica, e il link continua a funzionare.
- 🔚 Configurato in un altro modo — attivato con `user activate`, oppure con una password fornita tramite `user reset` o un [link di reimpostazione](#reset-link) — l'amministratore non attende più: i suoi link di configurazione vengono invalidati definitivamente, e questo comando si arresta con l'errore seguente.
- 🌐 Come per gli [inviti](#invite), il link è completo quando `LIBREFOLIO_PUBLIC_URL` è impostata, e solo il percorso (`/setup#token=…`) quando non lo è.
- 📧 Il comando stampa solo il link: non invia alcuna email.
- ❌ Quando nessun amministratore è in attesa della sua configurazione, il comando si arresta con l'errore `No administrator account is waiting for its setup link` ed esce con `1`. Fa lo stesso quando l'amministratore completa la sua configurazione mentre il comando è in esecuzione: il comando controlla di nuovo subito prima di emettere il link e non ne fornisce alcuno a un account già configurato.

### 📧 Cambiare l'indirizzo email di un account {: #set-email }

```bash
pipenv run ./dev.py user set-email <username> <new_email>
```

La stessa modifica di una nuova email nel [Profilo](../user/settings/profile.md#email-change) dell'utente, senza la sua password: usala quando qualcuno non può cambiare il proprio indirizzo da solo, oppure per separare due account che ne condividono uno ([sotto](#email-case-conflict)).

- 🔤 Un indirizzo appartiene a un solo account, a prescindere dalle maiuscole/minuscole: `Anna@example.com` e `anna@example.com` sono lo stesso indirizzo. Solo le lettere A-Z vengono confrontate in questo modo, le lettere accentate no: `Émile@example.com` e `émile@example.com` sono due indirizzi diversi.
- 🚪 Un nuovo indirizzo disconnette l'account da ogni dispositivo, annulla qualsiasi link di reimpostazione della password ancora aperto e viene registrato come non verificato; l'account può comunque accedere. L'indirizzo dell'account stesso con altre maiuscole/minuscole è lo stesso indirizzo: cambia solo il modo in cui è scritto, nessuno viene disconnesso e resta verificato.
- 👑 Sull'amministratore iniziale ancora in attesa del suo link di configurazione, un nuovo indirizzo invalida anche quel link, che era diretto al vecchio indirizzo: l'account è ancora in attesa, e [`user setup-link`](#setup-link) gliene fornisce uno nuovo. Finché `LIBREFOLIO_ADMIN_EMAIL` è impostata, ogni avvio del server assegna di nuovo quell'indirizzo all'account in attesa: modifica anche la variabile, altrimenti il prossimo avvio riporta il vecchio indirizzo e invalida anche il nuovo link.
- ❌ Un indirizzo che un altro account ha già, a prescindere dalle maiuscole/minuscole, viene rifiutato: il comando si arresta con l'errore `Email already registered` ed esce con `1`, senza cambiare nulla. Lo stesso vale per un indirizzo che è il nome utente di un altro account, a prescindere dalle maiuscole/minuscole: un account creato prima della versione 1.3 può avere una `@` nel proprio nome utente ([Nomi utente con una @](users.md#usernames-with-at)), e una volta che quel nome è l'indirizzo di qualcuno, l'accesso, che interpreta prima un indirizzo, non troverebbe più quell'account con il suo nome. Il nome utente dell'account stesso non è un ostacolo: può diventare il suo indirizzo. Anche un indirizzo non valido (`Not an email address`) o un nome utente sconosciuto (`User '<username>' not found`) arresta il comando.
- 📮 Un nuovo indirizzo annulla anche qualsiasi link di cambio email ancora in attesa per l'account. Non tocca la password.

### 👑 Concedere o rimuovere i diritti di amministratore

```bash
pipenv run ./dev.py user promote <username>
pipenv run ./dev.py user demote <username>
```

`demote` rifiuta l'ultimo amministratore attivo: si arresta con l'errore `User '<username>' is the last active administrator: promote another user first` ed esce con `1`. Una retrocessione disconnette l'account da ogni dispositivo.

### 🧭 Riavviare le guide di un utente {: #reset-onboarding }

```bash
# Every guide, the Welcome setup included
pipenv run ./dev.py user reset-onboarding <username>

# One guide only
pipenv run ./dev.py user reset-onboarding <username> --flow intro_tour
```

La prossima volta che l'utente apre LibreFolio, la configurazione iniziale e le guide ricominciano, come alla sua prima visita; i suoi dati e le sue preferenze restano come sono. `--flow` riavvia una sola guida: `pipenv run ./dev.py user reset-onboarding --help` elenca i nomi, come `welcome`, `intro_tour` o `import_guide`.
`demote` rifiuta anche l'[amministratore iniziale](configuration_accounts.md#initial-admin) ancora in attesa del suo link di configurazione, che fino ad allora mantiene il suo ruolo: si arresta con l'errore `User '<username>' is the initial administrator waiting for its setup: it keeps its role until then; deactivate it to cancel its setup link, or delete it from Settings › Administration › Users` ed esce con `1`, senza cambiare nulla. Per annullare il suo link, esegui `user deactivate` (vedi «Reimpostare una password o bloccare un account» sopra); per rimuovere l'account, eliminalo in [Utenti e inviti](users.md#delete), senza prima retrocederlo: la riga di comando non elimina alcun account.

---

## 🗄️ Mantenere il database

### ⬆️ Applicare le migrazioni {: #apply-migrations }

Ogni avvio del server applica da solo le migrazioni in attesa, quindi raramente ti serve questo. Per farlo manualmente, **arresta prima il server**: `db upgrade` rifiuta di essere eseguito mentre il server risponde sulla porta configurata.

```bash
# Apply pending migrations
pipenv run ./dev.py db upgrade

# Show the migration the database is at
pipenv run ./dev.py db current

# Look for missing CHECK constraints: changes nothing, exits with 1 if any
pipenv run ./dev.py db check

# List the currency codes that are not ISO codes: changes nothing, exits with 1 if any
pipenv run ./dev.py db currencies

# Upgrade and check another database file, such as a copy
pipenv run ./dev.py db upgrade /path/to/copy/app.db
pipenv run ./dev.py db check /path/to/copy/app.db
```

- 📄 Senza un percorso, i comandi usano il database configurato. Un percorso indica un altro file SQLite: uno relativo parte dalla radice del progetto, da qualunque posizione tu esegua il comando. Il file deve esistere, tranne per `db upgrade`, che lo crea (cartella inclusa) e lo aggiorna.
- 🐳 In Docker, il percorso è all'interno del container, dove `LibreFolio-data/` è `/app/backend/data/prod-docker` (il database è `sqlite/app.db` al suo interno). `db current`, `db check` e `db currencies` funzionano nel container in esecuzione: `docker compose exec librefolio python dev.py db current <path>`. `db upgrade` e `db downgrade` richiedono il server arrestato (`docker compose stop librefolio`), poi un container monouso: `docker compose run --rm librefolio python dev.py db upgrade <path>` ([dettagli](docker_advanced.md#docker-exec)).

### 🔤 Due account con lo stesso indirizzo email {: #email-case-conflict }

Dalla versione 1.3, un indirizzo email appartiene a un solo account, a prescindere dalle maiuscole/minuscole. Un database di una versione precedente può contenere due account i cui indirizzi differiscono solo per le maiuscole/minuscole, come `Anna@example.com` e `anna@example.com`: l'aggiornamento quindi si arresta alla migrazione che lo controlla, e il server non si avvia. Le migrazioni precedenti restano applicate, nessun account viene modificato, e il successivo avvio riprende da quella migrazione. Il log (o l'output di `db upgrade`) nomina gli account per id e nome utente, mai per indirizzo; un `;` separa un gruppo di account dal successivo:

```text
Email addresses must be unique regardless of case (release 1.3), and these accounts share one apart from upper and lower case: #3 'anna', #8 'anna_work'. Give all but one account of each group another address with …
```

LibreFolio non unisce mai due account: assegna un altro indirizzo a tutti gli account tranne uno di ciascun gruppo con [`user set-email`](#set-email), poi avvia di nuovo LibreFolio:

```bash
pipenv run ./dev.py user set-email <username> <new_email>
```

In Docker, il server è il processo principale del container, quindi il container non resta in esecuzione e non ci si può affidare a `docker compose exec`: esegui invece il comando in un container monouso.

```bash
docker compose stop librefolio
docker compose run --rm librefolio python dev.py user set-email <username> <new_email>
docker compose start librefolio
```

### 🩹 Correzioni post-migrazione {: #post-migration-fixes }

Subito dopo le migrazioni, ogni avvio esegue anche le **correzioni post-migrazione**: riparazioni che una migrazione non può fare. Di solito non c'è nulla da fare. Il log (l'output del server, salvato anche in `logs/`) può mostrare:

- ✅ `Post-migration fixes applied and verified`: è stata effettuata una riparazione. Su un database di grandi dimensioni quell'avvio è più lento, una volta sola.
- ⚠️ `Post-migration fix failed`: il database è stato lasciato com'era e il server si è avviato normalmente. L'avviso riporta l'errore e la copia del database conservata accanto al file originale finché non la elimini, come `app.db.pre-autoincrement-20261008T101500Z.bak`. La correzione viene ritentata al successivo avvio.
- 🩺 `Post-migration fixes skipped`: non è stato possibile creare la copia, oppure il database non supera il controllo di integrità di SQLite. Nulla è stato modificato.
- 🔗 `Foreign key violations already in the database, left as they are`: il database contiene riferimenti a righe che non esistono più, elencati nell'avviso. Le correzioni li lasciano invariati e vengono comunque eseguite: una correzione fallisce solo per un riferimento interrotto che aggiungerebbe essa stessa.

Il file vuoto `app.db.post-migration.lock`, accanto al database, fa alternare le esecuzioni quando più worker si avviano insieme: lascialo al suo posto.

La prima correzione, **`autoincrement`**, assicura che l'id di un utente, broker, asset, transazione, percorso di conversione FX o evento di asset eliminato non venga mai riassegnato. Durante la conversione di un database, elimina le cartelle dei report dei broker che non esistono più, così che un nuovo broker non possa ereditarle.

La seconda correzione, **`orphan_pair_halves`**, ripara, una volta sola, i trasferimenti che un'eliminazione precedente di un broker ha lasciato senza la loro altra metà sui broker rimanenti:

- 📈 I titoli ricevuti dal broker eliminato diventano una posizione di apertura al loro costo di trasferimento, a partire dalla data del trasferimento. Il capitale di quel broker li conta quindi a quel costo invece che al loro valore di mercato all'arrivo, così la sua plusvalenza include anche quella maturata prima del trasferimento. Quando non è stato registrato alcun costo, restano senza costo e l'app segnala un'acquisizione senza valore di acquisto: inserisci il costo nella transazione.
- 💶 I giroconti con il broker eliminato diventano depositi o prelievi: capitale e plusvalenza non cambiano.
- 📤 Titoli inviati **al** broker eliminato: subito dopo le correzioni, nello stesso avvio, ciascuno di questi trasferimenti diventa una rettifica che toglie i titoli dal broker mittente. Tale rettifica non ha valore: i titoli diminuiscono solo nella quantità, e il loro costo è conteggiato come una minusvalenza realizzata su quel broker. Il log ha una riga per ciascuno (`Lone transfer leg converted to an ADJUSTMENT-out without a value`). Su un database che non supera il controllo rapido di SQLite, ognuno di essi viene lasciato com'è (`Lone transfer legs left as they are: the database failed its quick check`). Se l'intero passaggio fallisce (`Lone transfer legs could not be converted; starting normally`), nulla viene modificato e il server si avvia comunque.

La correzione **`event_types`** ripara, una volta sola, gli eventi di asset memorizzati con un tipo che LibreFolio non conosce, come `dividend` o `dividendo` scritti a mano in un file CSV. Finora un tale evento faceva fallire il caricamento dell'intero elenco degli eventi di quell'asset, quindi nessuno di essi veniva mostrato:

- ✅ Un tipo che differisce solo per maiuscole/minuscole o spazi (`dividend`, ` Split `) viene corretto.
- 🗑️ Un evento il cui tipo è ancora sconosciuto viene eliminato. Una transazione collegata ad esso resta, senza il suo evento collegato: ricollegala all'evento giusto se ti serve.

??? tip "⌨️ Eseguire le correzioni manualmente — per visualizzarle in anteprima o ritentare una correzione fallita"

    **Arresta prima il server** (lo script non lo controlla), poi esegui dalla radice del progetto:

    ```bash
    # Preview: report what would be fixed, change nothing
    pipenv run python -m backend.app.db.post_migration --dry-run

    # Apply the fixes
    pipenv run python -m backend.app.db.post_migration
    ```

    Lo script stampa ogni correzione come `clean` (nulla da fare), `would_apply` (prova a vuoto), `applied` o `failed`, con le cartelle orfane dei broker, una copia conservata e qualsiasi errore, poi una riga per ogni trasferimento di titoli inviati a un broker eliminato (`Lone transfer leg …`), ed esce con `1` quando qualcosa è fallito. `--db PATH` e `--data-dir PATH` lo indirizzano verso un altro database o un'altra directory dei dati.

    Per vedere cosa modificherà `orphan_pair_halves` sul tuo database, esegui lo script in anteprima con `--dry-run` prima del primo avvio della nuova versione: stampa `Fix orphan_pair_halves: would_apply` quando c'è qualcosa da riparare, e un avviso elenca le transazioni per id, raggruppate per conversione (come `TRANSFER->ADJUSTMENT`), con quelle che resteranno senza un costo e i trasferimenti di titoli inviati a un broker eliminato. Quei trasferimenti ricevono una riga ciascuno dopo le correzioni (`would become an ADJUSTMENT-out without a value`). Lo script stampa anche, sulla console, ciò che il server registrerebbe nel log: l'avviso e, in un'esecuzione reale, una riga per ogni transazione modificata (con `LOG_LEVEL` impostato a `INFO`, il valore predefinito). Non scrive alcun file di log: conserva il suo output se vuoi una traccia di una riparazione eseguita manualmente.

🔗 Come funzionano le correzioni all'interno: [Schema del database — Correzioni post-migrazione](../developer/architecture/database/index.md#post-migration-fixes).

### 💱 Codici valuta che non sono codici ISO {: #currency-codes }

Dalla versione 1.3, LibreFolio salva una valuta solo come codice alfabetico ISO 4217, come `EUR` o `USD`. Le versioni precedenti accettavano anche il nome di una valuta o il suo codice numerico, e lo salvavano così com'era scritto: `Euro`, `978`. Un tale valore viene ancora letto, ma una modifica che salva di nuovo la sua riga viene rifiutata finché il suo codice non viene corretto, e i suoi importi non coincidono mai con quelli del codice ISO: `978` e `EUR` creano due saldi. Un backup ripristinato può riportare tali valori.

Poco dopo ogni avvio, il log avvisa quando il database ne contiene alcuni, e LibreFolio non li modifica da solo:

```text
Stored currency codes that are not ISO 4217 codes: an edit of their rows is refused until they are corrected (./dev.py db currencies lists them)
```

`db currencies` li elenca, senza modificare nulla:

```bash
# Where each value is stored, how many rows hold it, and the ISO code it stands for
pipenv run ./dev.py db currencies

# Another database file, such as a copy
pipenv run ./dev.py db currencies /path/to/copy/app.db
```

- 🔎 Ogni riga indica il posto (`transactions.currency`, `assets.currency`, i passaggi di un percorso FX, le impostazioni di un provider, la valuta di base di un utente…), il valore, quante righe lo contengono e il codice ISO che rappresenta: `978` è `EUR`, `US DOLLAR` è `USD`.
- ➖ Un trattino significa che non c'è un unico codice: un nome condiviso da due valute (`Bolívar Soberano`: `VED` o `VES`), un valore che non è una valuta, oppure un codice che conta centesimi anziché unità (`GBX`, `ZAC`, `ILA`), che non deve mai essere semplicemente rinominato.
- 🔤 Viene elencato anche un codice in minuscolo o con spazi, come `eur`: la valuta giusta, in una forma che i confronti esatti non rilevano.
- 🧱 Un valore salvato come byte grezzi anziché come testo, o come testo non valido in UTF-8, che solo un database danneggiato o creato a mano contiene, viene elencato nella notazione di SQLite, come `X'455552'`, con un trattino: non è mai un codice.
- 🚦 Il comando esce con `0` quando ogni codice è un codice ISO, `1` quando ne elenca alcuni e `2` quando non riesce a leggere il database.
- 🐳 In Docker: `docker compose exec librefolio python dev.py db currencies`.

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

    `db create-clean` elimina il database e ne crea uno vuoto. Come `db upgrade`, rifiuta di essere eseguito mentre il server è attivo. I file caricati e i report dei broker restano su disco: vedi [Inizializzazione e reimpostazione del database](host_installation.md#database-reset).

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
    - **Test**: `pipenv run ./dev.py test all` — vedi [Procedura guidata dei test](../developer/test-walkthrough/index.md)
    - **Client API**: `pipenv run ./dev.py api sync` — vedi [Panoramica dell'API](../developer/api/overview.md)
    - **i18n**: `pipenv run ./dev.py i18n audit` — vedi [Internazionalizzazione](../developer/frontend/i18n.md)
    - **Documentazione**: `pipenv run ./dev.py mkdocs deploy` pubblica questa documentazione su GitHub Pages; `pipenv run ./dev.py mkdocs gallery` rigenera le sue schermate con Playwright su un server di test (`--no-populate` mantiene i dati di test attuali).

    Il toolkit completo per sviluppatori è nella [Guida al flusso di lavoro per sviluppatori](../developer/dev_workflow.md).

---

## 🔗 Correlati

- 📄 **[Strumenti di amministrazione CLI: backup](cli_backup.md)** — Eseguire il backup dell'istanza
