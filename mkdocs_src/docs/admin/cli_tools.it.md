# 🛠️ Strumenti da riga di comando

`dev.py` esegue le attività amministrative: avviare il server, gestire utenti e inviti, mantenere il database, eseguire il backup dell'istanza. Ogni sezione dice **dove** si lancia il comando e quando richiede il server fermo.

!!! tip "Dove eseguire i comandi"

    | Installazione | Dove | Forma del comando |
    | --- | --- | --- |
    | **Su host** | Terminale sul server, nella cartella di LibreFolio (la radice del progetto), ambiente Pipenv | `pipenv run ./dev.py <command>` — oppure `./dev.py <command>` dopo `pipenv shell` |
    | **Docker, server in esecuzione** | Terminale sull'host, nella cartella del `docker-compose.yml` | `docker compose exec librefolio python dev.py <command>` |
    | **Docker, server fermo** | Stesso terminale | `docker compose stop librefolio`, poi `docker compose run --rm librefolio python dev.py <command>` (container monouso), poi `docker compose start librefolio` |

    - Nel container non c'è `pipenv run`: l'immagine installa le dipendenze globalmente.
    - `docker compose exec` esegue il comando come root. Da un checkout dei sorgenti, `./dev.py docker exec <command>` lo esegue invece come utente del server ([dettagli](docker_advanced.md#docker-exec)).
    - Nell'immagine funzionano i comandi `user`, `db current`, `db check`, `db currencies`, `backup create`, `backup inspect`, `backup restore`, `backup decrypt` e `backup pending` ([Backup con Docker](cli_backup.md#backup-docker)). `db upgrade` e `db downgrade` richiedono il server fermo, quindi la terza forma ([Applicare le migrazioni](#apply-migrations)). I comandi di sviluppo come `test` non fanno parte dell'immagine.

!!! info "📚 Questa guida è su più pagine"

    Oltre a questa pagina: [Strumenti di amministrazione CLI: backup](cli_backup.md).

---

## 🖥️ Avviare il server {: #start-the-server }

**Su host**, nel terminale del server, cartella di LibreFolio. In Docker il server è il processo principale del container: lo avvia `docker compose up -d`.

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

Il server risponde sulla porta scelta (`PORT` da `.env`, altrimenti 6040).

- 🧮 Più worker gestiscono più richieste insieme: usali su ogni macchina con più di una CPU. `auto` avvia $\max(1,\ 2\,(n-1))$ worker su $n$ CPU.
- ⏳ Al primo avvio, o quando sono obsoleti, il server compila l'interfaccia web e questa documentazione: servono alcuni minuti. Se l'interfaccia non compila, il server non parte.
- 🔑 Un riavvio disconnette tutti, a meno che `JWT_SECRET` sia impostato in `.env` ([Configurazione](configuration.md)).
- ⏹️ Ctrl+C arresta il server in modo pulito: `dev.py` gli concede il [budget di spegnimento](configuration_security.md#shutdown) più 2 secondi (10 secondi per impostazione predefinita), poi lo termina; un secondo Ctrl+C lo termina subito. Un SIGTERM al solo `dev.py`, per esempio da un supervisore di processi, riceve la stessa attesa: `dev.py` lo inoltra al server.

??? note "⚙️ Altre opzioni del server — raramente necessarie"

    | Opzione | Cosa fa |
    | --- | --- |
    | `--host HOST` | Indirizzo su cui restare in ascolto (predefinito: `HOST` dall'ambiente o da `.env`, altrimenti `0.0.0.0`) |
    | `--data-dir PATH` | Un'altra directory dei dati per questa esecuzione, invece di `LIBREFOLIO_DATA_DIR` |
    | `--no-scheduler` | Avvia senza le sincronizzazioni pianificate dei prezzi e dei tassi FX |
    | `--rebuild`, `-r` | Ricompila l'interfaccia web anche quando sembra aggiornata |
    | `--debug`, `-d` | Log `DEBUG`, build di debug dell'interfaccia web e pagine di documentazione dell'API (`/api/v1/docs`, `/api/v1/redoc`), altrimenti disattivate |

    Forme brevi: `-w` per `--workers`, `-p` per `--port`, `-f` per `--force`. `--test`, `--coverage` e `--no-reload` sono opzioni di sviluppo: `pipenv run ./dev.py server --help` le elenca tutte.

---

## 👤 Gestire gli utenti

**Su host** o **in Docker con il server in esecuzione** (prima o seconda forma della tabella sopra): questi comandi scrivono direttamente nel database, quindi funzionano anche mentre il server gira.

Nell'app, gli amministratori gestiscono account e inviti in **Impostazioni › Amministrazione › Utenti** ([Utenti e inviti](users.md)). La riga di comando serve su un server senza browser o per superare il [limite utenti](configuration_accounts.md#user-limit).

### ➕ Creare ed elencare utenti

```bash
# Create an administrator account
pipenv run ./dev.py user create <username> <email> <password>

# Create a regular account
pipenv run ./dev.py user create <username> <email> <password> --role user

# List all users: ID, username, email, active, administrator
pipenv run ./dev.py user list
```

`user list` stampa, per ogni account: ID, nome utente, email, attivo, amministratore.

- 👑 `user create` crea un **amministratore**; con `--role user`, un account normale. Le persone possono anche registrarsi da sole: **Registrati qui** nella pagina di accesso mentre **Registrazione** è **Aperta** (su una nuova istanza, anche finché non esiste il primo account), oppure con un [link d'invito](#invite) ([Chi può registrarsi](settings.md#registration)).
- 🔒 Password: stesse regole dell'app e dell'API. Almeno 8 caratteri, con una maiuscola, una minuscola, una cifra e un simbolo. Contano lettere e cifre di qualsiasi alfabeto (`É`, `é`); un simbolo è qualsiasi carattere che non sia lettera, numero o spazio (`!`, `_`, `€`). Una password non valida non cambia nulla: il comando stampa `Password does not meet security requirements:` e una riga per regola violata, che inizia con il codice della regola (`digit: the password must contain a digit`), poi esce con `1`.
- 🔤 Nome utente: da 3 a 50 caratteri, senza `@` (all'accesso, tutto ciò che contiene `@` è letto come email). Spazi, lettere accentate, `.`, `_`, `-`, `+` vanno bene. Errori, ciascuno con uscita `1` e senza cambiare nulla: `A username cannot contain @: the sign-in reads it as an email address`; `A username must be 3 to 50 characters long`; `Username already taken`; `Email already registered` se un altro account ha quell'indirizzo, o l'indirizzo è il nome utente di un altro account ([`user set-email`](#set-email)), a prescindere dalle maiuscole.
- 📏 Al [limite utenti](configuration_accounts.md#user-limit), `user create` avvisa `The instance is at its limit (LIBREFOLIO_MAX_USERS: 5 of 5 places taken): the command line creates the account anyway`, poi crea l'account: la riga di comando è il modo per superare il limite.

### ✉️ Invitare qualcuno {: #invite }

```bash
# An invitation link for a regular account
pipenv run ./dev.py user invite

# An invitation for an administrator, with a note of whom it is for
pipenv run ./dev.py user invite --admin --email anna@example.com
```

Il comando stampa un link valido una sola volta, per 7 giorni: invialo alla persona, che lo apre e crea il proprio account con nome utente, email e password a sua scelta ([cosa vede](../user/getting-started.md#invitation-link)).

- 👑 `--admin`: il nuovo account è amministratore; senza, è normale.
- ✉️ `--email`: solo una nota su chi è il destinatario; la persona può registrarsi con un altro indirizzo.
- 🌐 Con [`LIBREFOLIO_PUBLIC_URL`](configuration_accounts.md#accounts) impostata, il link è completo (`https://librefolio.example.com/invite#token=…`). Senza, il comando stampa solo il percorso, `/invite#token=…`, e ti ricorda di anteporre l'indirizzo del server (`http://192.168.1.10:6040`). Se la variabile è impostata ma non è un indirizzo `http://` o `https://`, il promemoria dice `LIBREFOLIO_PUBLIC_URL is not valid (…)`, con il motivo. Vale per tutti i link di questa pagina.
- 🔒 La parte segreta viene dopo `#`: i browser non la inviano mai al server, quindi non finisce nei log del server o del proxy. Invia il link per intero.
- 🚪 Gli inviti funzionano con **Registrazione** **Aperta** o **Su invito**. Con **Chiusa**, il comando si arresta con `Registration is disabled: invitations cannot be created` ed esce con `1`; anche i link già inviati non funzionano.
- 📏 Un invito occupa un posto del [limite utenti](configuration_accounts.md#user-limit) finché non è usato, revocato o scaduto. Al limite, il comando avvisa, poi crea comunque l'invito.
- ⏳ Nessun comando annulla un invito: un link non usato scade dopo 7 giorni. Prima, **Revoca** nella scheda [Utenti](users.md#open-invitations), oppure via API: `GET /api/v1/users/invites` elenca gli inviti in attesa, `DELETE /api/v1/users/invites/<id>` ne revoca uno.

### 🔑 Reimpostare una password o bloccare un account {: #reset-a-password-or-lock-an-account }

```bash
# Set a new password (same rules as above)
pipenv run ./dev.py user reset <username> <new_password>

# Lock an account out, then let it back in
pipenv run ./dev.py user deactivate <username>
pipenv run ./dev.py user activate <username>
```

`reset` cambia subito la password; `deactivate` rifiuta l'account dalla sua richiesta successiva.

- ⏱️ `reset` termina le sessioni aperte: ogni dispositivo viene disconnesso alla richiesta successiva. Per bloccare qualcuno definitivamente, `deactivate`: riattivarlo non ripristina le vecchie sessioni.
- 🔗 `reset` annulla anche ogni [link di reimpostazione](#reset-link) ancora aperto per l'account, chiunque lo abbia creato.
- 👑 `deactivate` rifiuta l'ultimo amministratore attivo: `User '<username>' is the last active administrator: promote or activate another administrator first`, uscita `1`.
- 📏 Al [limite utenti](configuration_accounts.md#user-limit), `activate` di un account disattivato avvisa `… the command line reactivates the account anyway`, poi lo riattiva. Nessun avviso per un account che occupa già il suo posto: uno in attesa dell'email con un link attivo, o l'amministratore iniziale in attesa del link di configurazione.
- 📬 Con la verifica email attiva, `activate` fa entrare subito un account in attesa della sua email e `deactivate` termina l'attesa: in entrambi i casi i suoi link di verifica smettono di funzionare (*Verifica email* in [Email](email.md)).
- 🏁 Sull'[amministratore iniziale](configuration_accounts.md#initial-admin) ancora in attesa del link di configurazione, `reset` e `activate` lo configurano senza il link e terminano l'attesa definitivamente: i suoi link di configurazione sono invalidati, incluso quello di `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`, e né [`user setup-link`](#setup-link) né un nuovo `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` gliene danno un altro. `activate` da solo lascia un account attivo di cui nessuno conosce la password, finché `reset` o un [link di reimpostazione](#reset-link) gliene dà una; `reset` da solo lo lascia inattivo, finché non intervieni con `activate`.
- 🚫 Su quello stesso amministratore in attesa, `deactivate` non configura nulla: annulla il link di configurazione, come **Annulla link di configurazione** in [Utenti e inviti](users.md#cancel-setup). Stampa `✅ User '<username>' deactivated`; ogni suo link di configurazione è invalidato, incluso quello di `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`, e l'account continua ad attendere: [`user setup-link`](#setup-link) gliene dà uno nuovo, e lo stesso fa un **nuovo** `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` al prossimo avvio. Lo stesso token, a un riavvio, no: l'istanza lo ha già visto.
- 💬 La schermata **Password dimenticata?** dell'app mostra questo comando per entrambe le installazioni: per Docker la riga `docker compose exec librefolio sh -c 'exec gosu …' sh user reset …` (quella di [`docker exec`](docker_advanced.md#docker-exec), eseguita come utente del server, non come root); per l'host `./dev.py user reset …`, dopo `pipenv shell` o con `pipenv run` davanti. Quando l'istanza può inviare via email un link di reimpostazione, la schermata mostra prima il modulo email e tiene i comandi in un pannello chiuso ([Password dimenticate](email_flows.md#forgot-password)).

### 🔗 Inviare un link di reimpostazione della password {: #reset-link }

```bash
pipenv run ./dev.py user reset-link <username>
```

Il comando stampa un link: la persona lo apre e sceglie da sé la nuova password, invece di ricevere quella scelta da te con `user reset` ([cosa vede](../user/getting-started.md#password-reset-link)).

- ⏱️ Il link vale una sola volta, per 30 minuti. Un nuovo link per lo stesso account annulla i precedenti; una modifica della password o dell'email dell'account — nel Profilo dell'utente, o con `user reset` o `user set-email` — li annulla tutti.
- 🚪 Impostata la nuova password, ogni dispositivo connesso viene disconnesso, come con `user reset`. Creare il link non disconnette nessuno.
- 🌐 Link completo con `LIBREFOLIO_PUBLIC_URL`, solo il percorso (`/reset-password#token=…`) senza ([come per gli inviti](#invite)).

### 🔁 Un nuovo link di configurazione per l'amministratore iniziale {: #setup-link }

```bash
pipenv run ./dev.py user setup-link
```

Il comando stampa un nuovo link di configurazione per l'amministratore creato da `LIBREFOLIO_ADMIN_EMAIL` al primo avvio ([L'amministratore iniziale](configuration_accounts.md#initial-admin)), finché nessuno ha usato il suo: lui lo apre, sceglie la password ed è autenticato. Usalo quando il link è scaduto, perso o annullato.

- ⏱️ Il link vale una sola volta, per 72 ore. I link di configurazione precedenti sono invalidati, incluso quello di `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`.
- 🚫 Dopo un annullamento — **Annulla link di configurazione** in [Utenti e inviti](users.md#cancel-setup), o `user deactivate` sull'amministratore in attesa — l'amministratore attende ancora: questo comando gli dà un nuovo link.
- 📮 Dopo un nuovo indirizzo per l'amministratore in attesa — `LIBREFOLIO_ADMIN_EMAIL` modificata prima di un riavvio, o [`user set-email`](#set-email) — i suoi link, diretti al vecchio indirizzo, sono invalidati: questo comando gli dà un link per il nuovo. Lo stesso indirizzo con altre maiuscole/minuscole delle lettere A-Z non è una modifica: il link continua a funzionare.
- 🔚 Configurato in un altro modo — `user activate`, oppure una password da `user reset` o da un [link di reimpostazione](#reset-link) — l'amministratore non attende più: i suoi link sono invalidati definitivamente e il comando si arresta con l'errore qui sotto.
- 🌐 Link completo con `LIBREFOLIO_PUBLIC_URL`, solo il percorso (`/setup#token=…`) senza ([come per gli inviti](#invite)).
- 📧 Il comando stampa solo il link: non invia alcuna email.
- ❌ Senza un amministratore in attesa, il comando si arresta con `No administrator account is waiting for its setup link` ed esce con `1`. Lo stesso se l'amministratore completa la configurazione mentre il comando gira: il comando ricontrolla subito prima di emettere il link e non ne dà alcuno a un account già configurato.

### 📧 Cambiare l'indirizzo email di un account {: #set-email }

```bash
pipenv run ./dev.py user set-email <username> <new_email>
```

La stessa modifica di una nuova email nel [Profilo](../user/settings/profile.md#email-change) dell'utente, senza la sua password: per chi non può cambiare indirizzo da solo, o per separare due account che ne condividono uno ([sotto](#email-case-conflict)).

- 🔤 Un indirizzo appartiene a un solo account, a prescindere dalle maiuscole/minuscole: `Anna@example.com` e `anna@example.com` sono lo stesso indirizzo. Solo le lettere A-Z sono confrontate così, non quelle accentate: `Émile@example.com` e `émile@example.com` sono due indirizzi diversi.
- 🚪 Un nuovo indirizzo disconnette l'account da ogni dispositivo, annulla ogni link di reimpostazione della password e ogni link di cambio email in attesa, e viene registrato come non verificato; l'account può comunque accedere. Non tocca la password. Lo stesso indirizzo con altre maiuscole/minuscole cambia solo come è scritto: nessuno è disconnesso e resta verificato.
- 👑 Sull'amministratore iniziale ancora in attesa del link di configurazione, il nuovo indirizzo invalida anche quel link: l'account attende ancora, e [`user setup-link`](#setup-link) gliene dà uno nuovo. Finché `LIBREFOLIO_ADMIN_EMAIL` è impostata, ogni avvio del server riassegna quell'indirizzo all'account in attesa: modifica anche la variabile, altrimenti il prossimo avvio riporta il vecchio indirizzo e invalida anche il nuovo link.
- ❌ Rifiutati, con uscita `1` e senza cambiare nulla: un indirizzo che un altro account ha già, a prescindere dalle maiuscole/minuscole (`Email already registered`); un indirizzo che è il nome utente di un altro account, a prescindere dalle maiuscole/minuscole (stesso errore: un account creato prima della versione 1.3 può avere una `@` nel nome utente, [Nomi utente con una @](users.md#usernames-with-at), e se quel nome diventa l'indirizzo di qualcuno, l'accesso, che legge prima un indirizzo, non troverebbe più quell'account); un indirizzo non valido (`Not an email address`); un nome utente sconosciuto (`User '<username>' not found`). Il nome utente dell'account stesso non è un ostacolo: può diventare il suo indirizzo.

### 👑 Concedere o rimuovere i diritti di amministratore

```bash
pipenv run ./dev.py user promote <username>
pipenv run ./dev.py user demote <username>
```

Una retrocessione disconnette l'account da ogni dispositivo.

- 👑 `demote` rifiuta l'ultimo amministratore attivo: `User '<username>' is the last active administrator: promote another user first`, uscita `1`.
- 🏁 `demote` rifiuta anche l'[amministratore iniziale](configuration_accounts.md#initial-admin) ancora in attesa del link di configurazione, che fino ad allora mantiene il ruolo: `User '<username>' is the initial administrator waiting for its setup: it keeps its role until then; deactivate it to cancel its setup link, or delete it from Settings › Administration › Users`, uscita `1`, senza cambiare nulla. Per annullare il suo link: `user deactivate` ([sopra](#reset-a-password-or-lock-an-account)). Per rimuovere l'account: eliminalo in [Utenti e inviti](users.md#delete), senza retrocederlo prima. La riga di comando non elimina alcun account.

### 🧭 Riavviare le guide di un utente {: #reset-onboarding }

```bash
# Every guide, the Welcome setup included
pipenv run ./dev.py user reset-onboarding <username>

# One guide only
pipenv run ./dev.py user reset-onboarding <username> --flow intro_tour
```

Alla prossima apertura di LibreFolio, la configurazione iniziale e le guide ricominciano come alla prima visita; dati e preferenze dell'utente restano. `--flow` riavvia una sola guida: `pipenv run ./dev.py user reset-onboarding --help` elenca i nomi (`welcome`, `intro_tour`, `import_guide`…).

---

## 🗄️ Mantenere il database

### ⬆️ Applicare le migrazioni {: #apply-migrations }

Ogni avvio del server applica da solo le migrazioni in attesa: raramente ti serve farlo a mano.

**Su host**, nel terminale del server, cartella di LibreFolio, **con il server fermo**: `db upgrade` rifiuta di partire mentre il server risponde sulla porta configurata. `db current`, `db check` e `db currencies` non modificano nulla e girano anche con il server attivo.

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

`db upgrade` porta il database all'ultima migrazione; `db current` stampa quella a cui si trova.

- 📄 Senza percorso, i comandi usano il database configurato. Un percorso indica un altro file SQLite: uno relativo parte dalla radice del progetto, da qualunque cartella tu lanci il comando. Il file deve esistere, tranne per `db upgrade`, che lo crea (cartella inclusa) e lo aggiorna.
- 🐳 **In Docker**, il percorso è interno al container: `LibreFolio-data/` è `/app/backend/data/prod-docker`, il database è `sqlite/app.db` al suo interno. `db current`, `db check` e `db currencies`: server in esecuzione, `docker compose exec librefolio python dev.py db current <path>`. `db upgrade` e `db downgrade`: server fermo (`docker compose stop librefolio`), poi container monouso, `docker compose run --rm librefolio python dev.py db upgrade <path>` ([dettagli](docker_advanced.md#docker-exec)).

### 🔤 Due account con lo stesso indirizzo email {: #email-case-conflict }

Dalla versione 1.3 un indirizzo email appartiene a un solo account, a prescindere dalle maiuscole/minuscole. Se un database precedente ha due account con indirizzi diversi solo per le maiuscole (`Anna@example.com` e `anna@example.com`), l'aggiornamento si arresta alla migrazione che lo controlla e il server non parte. Le migrazioni precedenti restano applicate, nessun account è modificato, il prossimo avvio riprende da lì. Il log (o l'output di `db upgrade`) nomina gli account per id e nome utente, mai per indirizzo; un `;` separa un gruppo dal successivo:

```text
Email addresses must be unique regardless of case (release 1.3), and these accounts share one apart from upper and lower case: #3 'anna', #8 'anna_work'. Give all but one account of each group another address with …
```

LibreFolio non unisce mai due account: dai un altro indirizzo a tutti gli account tranne uno di ciascun gruppo, poi avvia di nuovo LibreFolio.

=== "Su host"

    Nel terminale del server, cartella di LibreFolio:

    ```bash
    pipenv run ./dev.py user set-email <username> <new_email>
    ```

=== "Docker"

    Nella cartella del `docker-compose.yml`. Il server è il processo principale del container, che quindi non resta in esecuzione e `docker compose exec` non serve: usa un container monouso.

    ```bash
    docker compose stop librefolio
    docker compose run --rm librefolio python dev.py user set-email <username> <new_email>
    docker compose start librefolio
    ```

### 🩹 Correzioni post-migrazione {: #post-migration-fixes }

Subito dopo le migrazioni, ogni avvio esegue le **correzioni post-migrazione**: riparazioni che una migrazione non può fare. Di solito non c'è nulla da fare. Nel log (l'output del server, salvato anche in `logs/`) puoi leggere:

| Riga di log | Significato |
| --- | --- |
| ✅ `Post-migration fixes applied and verified` | Una riparazione è stata fatta. Su un database grande quell'avvio è più lento, una volta sola. |
| ⚠️ `Post-migration fix failed` | Database lasciato com'era, server avviato normalmente. L'avviso riporta l'errore e la copia del database conservata accanto all'originale finché non la elimini (`app.db.pre-autoincrement-20261008T101500Z.bak`). La correzione viene ritentata al prossimo avvio. |
| 🩺 `Post-migration fixes skipped` | Impossibile creare la copia, oppure il database non supera il controllo di integrità di SQLite. Nulla modificato. |
| 🔗 `Foreign key violations already in the database, left as they are` | Il database contiene riferimenti a righe che non esistono più, elencati nell'avviso. Le correzioni li lasciano invariati e girano comunque: una correzione fallisce solo per un riferimento interrotto che aggiungerebbe lei stessa. |

Il file vuoto `app.db.post-migration.lock`, accanto al database, fa alternare le esecuzioni quando più worker partono insieme: lascialo al suo posto.

Le correzioni:

- **`autoincrement`**: l'id di un utente, broker, asset, transazione, percorso di conversione FX o evento di asset eliminato non viene mai riassegnato. Durante la conversione elimina le cartelle dei report dei broker che non esistono più, così un nuovo broker non le eredita.
- **`orphan_pair_halves`**, una volta sola: ripara i trasferimenti che l'eliminazione di un broker ha lasciato senza l'altra metà sui broker rimanenti.
    - 📈 Titoli ricevuti dal broker eliminato → posizione di apertura al costo di trasferimento, dalla data del trasferimento. Il capitale di quel broker li conta a quel costo, non al valore di mercato all'arrivo, quindi la sua plusvalenza include anche quella maturata prima del trasferimento. Senza un costo registrato restano senza costo e l'app segnala un'acquisizione senza valore di acquisto: inserisci il costo nella transazione.
    - 💶 Giroconti con il broker eliminato → depositi o prelievi: capitale e plusvalenza non cambiano.
    - 📤 Titoli inviati **al** broker eliminato: subito dopo le correzioni, nello stesso avvio, ogni trasferimento diventa una rettifica che toglie i titoli dal broker mittente, senza valore: scende solo la quantità, e il costo è conteggiato come minusvalenza realizzata su quel broker. Una riga di log ciascuno (`Lone transfer leg converted to an ADJUSTMENT-out without a value`). Se il database non supera il controllo rapido di SQLite, restano com'erano (`Lone transfer legs left as they are: the database failed its quick check`). Se l'intero passaggio fallisce (`Lone transfer legs could not be converted; starting normally`), nulla è modificato e il server parte comunque.
- **`event_types`**, una volta sola: ripara gli eventi di asset con un tipo che LibreFolio non conosce, come `dividend` o `dividendo` scritti a mano in un CSV. Finora un tale evento faceva fallire il caricamento dell'intero elenco degli eventi dell'asset, quindi nessuno era mostrato.
    - ✅ Un tipo diverso solo per maiuscole/minuscole o spazi (`dividend`, ` Split `) viene corretto.
    - 🗑️ Un evento dal tipo ancora sconosciuto viene eliminato. Una transazione collegata resta, senza il suo evento: ricollegala all'evento giusto se ti serve.

??? tip "⌨️ Eseguire le correzioni manualmente — per visualizzarle in anteprima o ritentare una correzione fallita"

    **Su host**, nel terminale del server, cartella di LibreFolio, **con il server fermo** (lo script non lo controlla). In Docker: [Correzioni post-migrazione con il server fermo](docker_advanced.md#post-migration-fixes).

    ```bash
    # Preview: report what would be fixed, change nothing
    pipenv run python -m backend.app.db.post_migration --dry-run

    # Apply the fixes
    pipenv run python -m backend.app.db.post_migration
    ```

    Lo script stampa ogni correzione come `clean` (nulla da fare), `would_apply` (prova a vuoto), `applied` o `failed`, con le cartelle orfane dei broker, una copia conservata e ogni errore, poi una riga per ogni trasferimento di titoli inviati a un broker eliminato (`Lone transfer leg …`); esce con `1` quando qualcosa è fallito. `--db PATH` e `--data-dir PATH` lo indirizzano a un altro database o a un'altra directory dei dati.

    Per vedere cosa farà `orphan_pair_halves` sul tuo database, lancia `--dry-run` prima del primo avvio della nuova versione: stampa `Fix orphan_pair_halves: would_apply` quando c'è qualcosa da riparare, e un avviso elenca le transazioni per id, raggruppate per conversione (`TRANSFER->ADJUSTMENT`), con quelle che resteranno senza costo e i trasferimenti di titoli inviati a un broker eliminato; questi ricevono una riga ciascuno dopo le correzioni (`would become an ADJUSTMENT-out without a value`). Lo script stampa sulla console ciò che il server scriverebbe nel log: l'avviso e, in un'esecuzione reale, una riga per ogni transazione modificata (con `LOG_LEVEL` a `INFO`, il predefinito). Non scrive alcun file di log: conserva il suo output se vuoi una traccia della riparazione.

🔗 Come funzionano le correzioni all'interno: [Schema del database — Correzioni post-migrazione](../developer/architecture/database/index.md#post-migration-fixes).

### 💱 Codici valuta che non sono codici ISO {: #currency-codes }

Dalla versione 1.3 LibreFolio salva una valuta solo come codice alfabetico ISO 4217 (`EUR`, `USD`). Le versioni precedenti accettavano anche il nome o il codice numerico e lo salvavano com'era scritto: `Euro`, `978`. Un tale valore viene ancora letto, ma una modifica che risalva la sua riga è rifiutata finché il codice non è corretto, e i suoi importi non si sommano a quelli del codice ISO: `978` e `EUR` fanno due saldi. Un backup ripristinato può riportare tali valori.

Poco dopo ogni avvio, il log avvisa quando il database ne contiene; LibreFolio non li modifica da solo:

```text
Stored currency codes that are not ISO 4217 codes: an edit of their rows is refused until they are corrected (./dev.py db currencies lists them)
```

**Su host** o **in Docker con il server in esecuzione** (`docker compose exec librefolio python dev.py db currencies`):

```bash
# Where each value is stored, how many rows hold it, and the ISO code it stands for
pipenv run ./dev.py db currencies

# Another database file, such as a copy
pipenv run ./dev.py db currencies /path/to/copy/app.db
```

Il comando elenca i valori senza modificare nulla.

- 🔎 Ogni riga indica il posto (`transactions.currency`, `assets.currency`, i passaggi di un percorso FX, le impostazioni di un provider, la valuta di base di un utente…), il valore, quante righe lo contengono e il codice ISO che rappresenta: `978` è `EUR`, `US DOLLAR` è `USD`.
- ➖ Un trattino: nessun codice unico. Un nome condiviso da due valute (`Bolívar Soberano`: `VED` o `VES`), un valore che non è una valuta, oppure un codice che conta centesimi anziché unità (`GBX`, `ZAC`, `ILA`), da non rinominare mai semplicemente.
- 🔤 Anche un codice in minuscolo o con spazi (`eur`) è elencato: la valuta giusta, in una forma che i confronti esatti non rilevano.
- 🧱 Un valore salvato come byte grezzi o testo non valido in UTF-8, che solo un database danneggiato o creato a mano contiene, appare nella notazione di SQLite (`X'455552'`) con un trattino: non è mai un codice.
- 🚦 Uscita `0` quando ogni codice è ISO, `1` quando ne elenca alcuni, `2` quando non riesce a leggere il database.

### 🔧 Aggiungere le impostazioni globali mancanti

**Su host** o **in Docker con il server in esecuzione**:

```bash
pipenv run ./dev.py user init-settings
```

Aggiunge le [Impostazioni globali](settings.md) mancanti con i valori predefiniti, come fa ogni avvio, ma senza avviare il server; non modifica mai un valore già impostato.

### 🧹 Reimpostare il database

**Su host**, nel terminale del server, cartella di LibreFolio, **con il server fermo**:

```bash
pipenv run ./dev.py db create-clean
```

!!! warning "Tutti i dati andranno persi"

    `db create-clean` elimina il database e ne crea uno vuoto. Come `db upgrade`, rifiuta di partire mentre il server è attivo. I file caricati e i report dei broker restano su disco: [Inizializzazione e reimpostazione del database](host_installation.md#database-reset).

---

## 📋 Albero completo dei comandi

```bash
# Every command, by category
pipenv run ./dev.py --help

# The options of one command
pipenv run ./dev.py server --help
```

??? info "👩‍💻 Comandi per sviluppatori e documentazione"

    - **Frontend**: `pipenv run ./dev.py front build`, `front dev`, `front check` — [Sviluppo frontend](../developer/frontend/index.md)
    - **Test**: `pipenv run ./dev.py test all` — [Procedura guidata dei test](../developer/test-walkthrough/index.md)
    - **Client API**: `pipenv run ./dev.py api sync` — [Panoramica dell'API](../developer/api/overview.md)
    - **i18n**: `pipenv run ./dev.py i18n audit` — [Internazionalizzazione](../developer/frontend/i18n.md)
    - **Documentazione**: `pipenv run ./dev.py mkdocs deploy` pubblica questa documentazione su GitHub Pages; `pipenv run ./dev.py mkdocs gallery` rigenera le schermate con Playwright su un server di test (`--no-populate` mantiene i dati di test attuali).

    Il toolkit completo per sviluppatori: [Guida al flusso di lavoro per sviluppatori](../developer/dev_workflow.md).

---

## 🔗 Correlati

- 📄 **[Strumenti di amministrazione CLI: backup](cli_backup.md)** — Eseguire il backup dell'istanza
