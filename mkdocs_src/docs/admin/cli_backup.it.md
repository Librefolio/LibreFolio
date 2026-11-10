# 💾 Strumenti di amministrazione CLI: Backup

Questa pagina della guida ai comandi copre `dev.py backup`: creare, verificare e ripristinare un archivio, seguire un ripristino, lavorare con Docker.

Il resto della guida inizia da [Strumenti da riga di comando](cli_tools.md).

---

## 💾 Eseguire il backup dell'istanza {: #backup }

`backup create` mette l'intera istanza in un unico zip, con il server in funzione: database, file caricati, report dei broker, scenari di stress. Per copiare a mano la directory dei dati, vedi [Backup](filesystem.md#backup).

| Attività | Comando |
| --- | --- |
| Creare un archivio | `backup create`; con `--encrypt` un [archivio sicuro](#backup-secure), con `--sealed` o `--recipient` un [archivio sigillato](#backup-sealed) per backup eseguiti in autonomia |
| Verificare un archivio e vederne il contenuto | `backup inspect` |
| Provare un ripristino su una copia, istanza intatta | `backup restore --dry-run` |
| Ripristinare al successivo avvio del server | `backup restore` |
| Seguire o annullare un ripristino | `backup pending` |
| Riportare un archivio sicuro al suo zip | `backup decrypt` |
| Generare la chiave di un archivio sigillato | `backup keygen` |

**Dove si lanciano i comandi:**

| Installazione | Dove | Comando |
| --- | --- | --- |
| Host | Terminale del server, cartella di LibreFolio | `pipenv run ./dev.py backup …` |
| Docker | Terminale del server, cartella di `docker-compose.yml`: il comando gira dentro il container | `docker compose exec librefolio python dev.py backup …`, con i percorsi del container: [Eseguire il backup con Docker](#backup-docker) |
| Un tuo computer | `backup keygen`, e l'apertura di un archivio sigillato dove sta la chiave privata | [Un archivio sigillato](#backup-sealed) |

Un percorso relativo (`-o`, archivi, file della password) parte dalla radice del progetto, da qualunque punto tu esegua il comando: preferisci percorsi assoluti. `backup --test-db create` esegue il backup della directory dei dati di test: un'opzione di sviluppo.

### 📦 Creare un archivio

**Dove: terminale del server, cartella di LibreFolio** (Docker: [dentro il container](#backup-docker)).

```bash
# Keep an archive in its own folder of <data dir>/backups/, and print its SHA-256
pipenv run ./dev.py backup create

# Copy it into another folder instead, which must already exist
pipenv run ./dev.py backup create -o /mnt/nas/librefolio/

# Or give the archive a name of your own
pipenv run ./dev.py backup create -o /mnt/nas/librefolio/before-update.zip

# A secure archive (.lfbk): the password is asked twice
pipenv run ./dev.py backup create --encrypt -o /mnt/nas/librefolio/
```

Risultato: l'archivio zip, nel posto scelto con le opzioni sotto, e il suo checksum stampato.

| Opzione | Effetto |
| --- | --- |
| nessuna | **L'archivio resta sul server**, in una cartella dedicata di `backups/`: `backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip` (momento, origine `cli`, codice breve). Nulla è copiato o spostato. Compare in **Impostazioni › Amministrazione › Backup** e nella pulizia automatica: [Backup conservati sul server](backup_restore.md#kept-backups) |
| `-o`, `--output PATH` | **L'archivio è copiato lì**, nulla resta in `backups/`. Cartella esistente: l'archivio con il nome predefinito dentro. Ogni altro percorso, anche con `/` finale: il file dell'archivio, che non deve esistere e non è mai rinominato; le cartelle mancanti sono create solo allo spostamento, così un backup fallito non lascia una cartella vuota. Controllato prima che il backup inizi: il comando deve poter scrivere lì |
| `--encrypt` | [Archivio sicuro](#backup-secure) `.lfbk`, password chiesta due volte |
| `--password-file FILE`, `--password-stdin` | Archivio sicuro con la password da un file o dallo standard input, senza `--encrypt` |
| `--recipient age1…`, `--sealed` | [Archivio sigillato](#backup-sealed) `.tar`, senza password |

Da sapere:

- ✅ Termina con `✅ Backup written: <path>`, dimensione e tempo impiegato, `SHA-256: <checksum>`, eventuali avvisi e il promemoria `🔒 The archive holds every user's data: keep it private.` (archivio sicuro: `🔐 Encrypted with your password: only that password opens it, and LibreFolio cannot recover a lost one.`). Esce con `0` quando l'archivio è dove hai chiesto, anche con avvisi; `1` altrimenti.
- 🟢 Il server continua a funzionare, e a scrivere: il database è copiato con `VACUUM INTO` di SQLite, un'istantanea coerente, poi la copia passa il controllo di integrità e quello delle chiavi esterne.
- 🏷️ Il nome viene dal momento d'inizio, in UTC: `librefolio-backup-20261015-121500.zip`, `.lfbk` per un archivio sicuro. In una cartella `--output` che ha già quel nome, ad esempio dopo due backup nello stesso secondo: `librefolio-backup-20261015-121500-2.zip`, poi `-3`, e così via. Un archivio non sostituisce mai un file.
- 🧾 Dopo il percorso, il comando stampa `SHA-256: <64 hexadecimal digits>`, il checksum dell'archivio: confrontalo con quello del file una volta su un altro disco.
- 💽 **Spazio**: controllato prima di scrivere, in `backups/` della directory dei dati, anche con `-o`: circa il doppio del database, più i file, più un piccolo margine. Insufficiente, o disco o quota che si riempiono durante il backup → `❌ Backup failed (backup_no_space): not enough free space`. Con `-o` su un altro disco, lo spazio lì è controllato quando l'archivio è costruito e la sua dimensione è nota.
- 🛟 Se l'archivio finito non può andare in `-o` (un file con quel nome comparso nel frattempo, cartelle non creabili, altro disco pieno, errore di scrittura) → resta in `backups/` come file sciolto: fuori dall'elenco dei backup conservati, mai rimosso dalla pulizia automatica. Il comando termina con `1`. Uno spostamento fallito a metà non lascia file parziali.
- 🚦 Un backup alla volta: con un altro in corso, il comando si ferma e ti chiede di riprovare quando l'altro è terminato.
- 🔒 Senza password l'archivio non è cifrato: è scritto `0600`, leggibile e scrivibile solo dal proprietario. Conservalo, con ogni copia, con la riservatezza della directory dei dati.
- 🗑️ I backup in `backups/` restano finché non li elimini da **Impostazioni › Amministrazione › Backup** o dalla cartella, o finché la [pulizia automatica](backup_restore.md#backup-cleanup) non li rimuove, tranne l'ultimo. I file `librefolio-backup-*.zip` sciolti delle versioni precedenti non vengono mai toccati. `backups/` è sul disco dei dati: copia gli archivi su un altro disco, un NAS o fuori sede, oppure scrivili lì direttamente con `-o`.
- 🔗 Mantieni `backups/` una cartella reale, mai un collegamento a un NAS o a un altro disco: ogni archivio è costruito lì, anche con `-o`. Un collegamento, o un file, al suo posto → `❌ <data dir>/backups is not a plain folder (a link, or a file): …`.

??? note "⚠️ Avvisi ed errori — cosa significano i messaggi"

    **Avvisi**: l'archivio viene comunque scritto.

    - `The database failed its integrity check` o `The database has foreign-key violations`: il database è nell'archivio così com'è; `backup inspect` mostra il risultato del controllo.
    - `Left out (<n>): links, special files, files or folders that could not be read, or files removed during the backup`, poi le voci, al massimo 50: non sono nell'archivio. I collegamenti non vengono mai seguiti, anche quando un'intera cartella come `custom-uploads/` è un collegamento a un altro disco.
    - `The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore`: un [archivio sicuro](#backup-secure) senza la chiave.

    **Non dove hai chiesto**: l'archivio viene scritto, codice di uscita `1`.

    - `⚠️ <reason>: the archive was written to <path> instead`, poi le righe usuali: `-o` non ha potuto ricevere l'archivio, che è in `backups/` come file sciolto, fuori dall'elenco dei backup conservati. Spostalo dove vuoi.
    - `❌ <reason>: the archive stays in <path>. Move it within the hour: the next backup after that removes it.`: neanche `backups/` ha potuto riceverlo. È nella cartella di lavoro, dentro `backups/.jobs/`, che il primo backup o il primo avvio di LibreFolio dopo quell'ora rimuove: spostalo fuori prima.

    **Errori**: nessun archivio scritto, codice di uscita `1`.

    - `❌ No data directory at <path>` o `❌ No database at <path>: nothing to back up`: il comando usa la [directory dei dati](filesystem.md) con cui è configurato LibreFolio; controlla `LIBREFOLIO_DATA_DIR`.
    - `❌ <path> already exists: choose another name or folder`, `❌ <path> is not a folder: choose another path` (un file occupa il posto di una cartella del percorso) o `❌ cannot write into <folder>: choose another folder, or run the command as a user who can`: `-o` non può ricevere l'archivio. Il backup non è iniziato.
    - `❌ <data dir>/backups is not a plain folder (a link, or a file): …`: rendi `backups/` di nuovo una cartella reale. `❌ The backup could not run in <data dir>/backups: <reason>`: la cartella di lavoro non può essere preparata lì, ad esempio perché la directory dei dati non è scrivibile.
    - `❌ Backup failed (backup_no_space): not enough free space`: spazio insufficiente all'inizio, oppure disco o quota riempiti durante il backup, anche a metà di un file. Libera spazio sul disco della directory dei dati.
    - `❌ Backup failed (backup_failed): the cause is in the log above`: ogni altro errore, ad esempio un file che fallisce mentre viene copiato nell'archivio (un errore di lettura a metà): una parte di file non si toglie da uno zip, quindi l'intero backup si ferma. Un file che fallisce prima della copia è invece escluso con l'avviso sopra.

### 🗃️ Dove restano i backup {: #backup-kept }

Comando e app lasciano i backup finiti in `backups/`, una cartella ciascuno: `librefolio-backup-<date>-<time>-<origin>-<id>`, origine `cli` per il comando e `ui` per l'app. `backups/.jobs/` contiene solo un backup in corso o uno fallito.

| Cosa farne | Dove |
| --- | --- |
| Elencarli, scaricarli, eliminarli | **Impostazioni › Amministrazione › Backup**, oppure **File › Backup** (solo amministratori): [Backup conservati sul server](backup_restore.md#kept-backups) |
| Eliminare da soli i più vecchi, mai l'ultimo: dimensione totale ed età massima, entrambe opzionali | [Pulizia automatica](backup_restore.md#backup-cleanup). Il comando le applica dopo ogni backup, come l'app |
| Verificare o ripristinare un archivio conservato dalla riga di comando | `backup inspect` o `backup restore`, con il percorso stampato da `backup create` |

💽 Una copia sul disco dei tuoi dati non è un vero backup: copia l'archivio su un altro disco, oppure usa `--output`.

### 🔐 Un archivio sicuro {: #backup-secure }

**Dove: terminale del server, cartella di LibreFolio** (Docker, da cron: `-T` e un secret, [sotto](#backup-docker)).

```bash
# The password is asked twice at the terminal
pipenv run ./dev.py backup create --encrypt

# The password read from a file that holds it alone (with Docker, a secret: /run/secrets/…)
pipenv run ./dev.py backup create --password-file ~/.librefolio-backup-password

# The password read from the standard input, such as from a password manager
pass show librefolio/backup | pipenv run ./dev.py backup create --password-stdin
```

Risultato: `librefolio-backup-20261015-121500.lfbk`, lo zip che `backup create` scrive senza password, cifrato con la tua.

Solo quella password lo apre, e LibreFolio non recupera una password perduta: il comando termina come un backup normale, con il promemoria `🔐 Encrypted with your password: only that password opens it, and LibreFolio cannot recover a lost one.` Cosa protegge e cosa no: [Backup sicuri](backup_restore.md#secure).

**Da dove viene la password**: mai dalla riga di comando, che ogni utente del server legge (`ps`) e che la shell conserva nella cronologia. Non esiste `--password`, e le opzioni della password non hanno forma abbreviata.

| Opzione | La password |
| --- | --- |
| `--encrypt` da solo | Digitata al terminale, due volte |
| `--password-file FILE` | Il testo del file, senza il byte order mark iniziale e i fine riga finali, come per [Segreti nei file](configuration_secrets.md#secret-files): un file con la sola password, come un secret Docker. Un percorso relativo parte dalla radice del progetto |
| `--password-stdin` | Una riga dello standard input, senza il suo fine riga, ad esempio da una pipe. Al terminale è chiesta come senza l'opzione, nascosta, due volte per `create`: digitata lì come riga sarebbe visibile |

`--password-file` e `--password-stdin` si escludono a vicenda, e ciascuna rende l'archivio sicuro senza `--encrypt`.

- 📄 **Un file di cui il comando può fidarsi.** Il file di `--password-file`, come quello di `--instance-key-file` ([La chiave dell'istanza di un'altra installazione](#backup-restore-instance-key)), deve essere un file regolare. Un FIFO, una cartella o un dispositivo è rifiutato subito, senza leggerlo: `❌ password file: <path> is not a regular file (password_unreadable)`. Da root, ad esempio con `docker compose exec`, è rifiutato anche un percorso che passa per un collegamento dentro la directory dei dati (l'utente di LibreFolio potrebbe puntarlo a un file che solo root legge): `❌ password file: <path> goes through a link inside the data directory: give the file itself, from outside it (password_unreadable)`. Un collegamento altrove è seguito, come i secret di Kubernetes; i secret Docker e Compose sono file normali. Per `--instance-key-file`, le stesse righe iniziano con `instance key file:` e finiscono con `(instance_key_unreadable)`.
- 📏 **Le regole**: come una password di account, almeno 12 caratteri con maiuscola, minuscola, cifra e simbolo (classi contate in Unicode come per gli account), al massimo 1024. Controllate prima che il backup inizi: una password che ne viola una non scrive nulla.
- 🗝️ **La chiave dell'istanza**: `secrets/instance.key` è nell'archivio quando LibreFolio ha generato la chiave e può usarla; mai una chiave da `LIBREFOLIO_INSTANCE_KEY` o `LIBREFOLIO_INSTANCE_KEY_FILE`. Una chiave generata ma inutilizzabile (danneggiata, irraggiungibile, oltre 4096 byte, più di quanto un ripristino rilegga) è esclusa con `⚠️ The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore`; l'archivio è scritto comunque.
- 💽 **Spazio**: la cifratura (`… encrypting`, dopo le fasi usuali) scrive il `.lfbk` accanto allo zip in `backups/`: lì serve di nuovo la dimensione dello zip, più 64 MB, altrimenti `❌ Backup failed (backup_no_space): not enough free space`. Lo zip è rimosso una volta cifrato, o se il backup fallisce. Dopo un'interruzione brusca (corrente, `kill -9`), il successivo avvio di LibreFolio chiude quel backup come interrotto e rimuove ciò che resta in `backups/.jobs/`, zip e copia del database inclusi.

??? note "❌ Errori della password — cosa significano i messaggi"

    Nulla viene scritto, codice di uscita `1`.

    - `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)`: `--encrypt` senza un terminale su cui chiedere, ad esempio in cron. Password vuota digitata al terminale: `❌ No password was typed (password_required)`; riga vuota via pipe con `--password-stdin`: `❌ The standard input carried no password (password_required)`.
    - `❌ The two passwords differ (password_mismatch)`.
    - `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: <rules>)`: i codici delle regole violate, in quest'ordine: `min_length`, `uppercase`, `lowercase`, `digit`, `special`.
    - `❌ The password is longer than 1024 characters (password_too_long)`.
    - `❌ password file: <path> does not exist (password_unreadable)`, oppure `cannot be read (…)`, `is empty or blank`, `is not UTF-8 text`, `is larger than 65536 bytes, too large for a secret`, `is not a regular file`, `goes through a link inside the data directory: give the file itself, from outside it` («Un file di cui il comando può fidarsi» sopra).

    Entrambe le opzioni della password insieme, o un'opzione inesistente come `--password`, fermano il comando prima che inizi, con la riga d'uso e codice di uscita `2`.

### 🗂️ Cosa contiene l'archivio

L'archivio ha la struttura della directory dei dati e contiene solo:

| Voce | Cos'è |
| --- | --- |
| `manifest.json` | La descrizione dell'archivio, sotto |
| `sqlite/app.db` | La copia del database |
| `custom-uploads/` | I file caricati nell'app |
| `broker_reports/` | I report dei broker |
| `scenario_catalog/` | I tuoi scenari di stress, se ne hai aggiunti |
| `secrets/instance.key` | Solo in un [archivio sicuro](#backup-secure), quando LibreFolio ha generato la chiave dell'istanza: il suo testo, fuori dall'elenco dei file del manifest. Un ripristino la legge per cifrare di nuovo i segreti salvati, e non la estrae mai |

Tutto il resto resta fuori: `secrets/` (tranne `secrets/instance.key` in un archivio sicuro), `logs/`, `scheduler_state.json`, la cartella `backups/`, il marcatore `.librefolio-production-data` e i file di lavoro di SQLite accanto al database: `app.db-wal`, `app.db-shm`, `app.db.post-migration.lock` e le copie `.bak` delle [correzioni post-migrazione](cli_tools.md#post-migration-fixes). La copia del database contiene già ciò che era in attesa in `app.db-wal`. Collegamenti simbolici e file speciali non vengono mai seguiti né archiviati.

!!! warning "🔑 La chiave dell'istanza è solo in un archivio sicuro"

    Un archivio in chiaro esclude `secrets/`, con la [chiave dell'istanza](configuration_secrets.md#instance-key). Eseguine il backup a parte ([Struttura del file system → Cosa sottoporre a backup](filesystem.md#what-to-back-up)) e conserva la copia con la riservatezza degli archivi. Prima di avviare LibreFolio sui dati di un archivio in chiaro, rimetti `secrets/` insieme ad essi: senza la sua chiave, ciò che LibreFolio ha cifrato non si legge più. Un [archivio sicuro](#backup-secure) contiene la chiave generata da LibreFolio, mai una da `LIBREFOLIO_INSTANCE_KEY` o `LIBREFOLIO_INSTANCE_KEY_FILE`: conserva quella dove l'hai impostata. Con una copia della chiave, un ripristino su un'altra installazione legge comunque i segreti salvati di un archivio in chiaro: [La chiave dell'istanza di un'altra installazione](#backup-restore-instance-key).

??? info "📋 `manifest.json` — cosa registra"

    - il formato, `librefolio-backup`, e la sua versione;
    - la versione di LibreFolio che ha creato l'archivio, come (`cli` per questo comando, `ui` per l'interfaccia web) e quando, in UTC;
    - il database: la revisione di migrazione (Alembic), il risultato del controllo di integrità di SQLite, il numero di violazioni di chiavi esterne, le righe di ogni tabella e i totali di controllo del libro contabile, la liquidità di ogni broker in ogni valuta e la quantità di ogni posizione (un archivio creato prima di questi non ne ha);
    - ogni voce, il database per primo, con percorso, dimensione e SHA-256;
    - se l'archivio contiene la chiave dell'istanza, e lo SHA-256 di quella voce: solo un archivio sicuro la contiene.

### 🔍 Verificare un archivio

**Dove: qualsiasi installazione**, con il server in esecuzione o fermo; non richiede una directory dei dati, tranne per un archivio sicuro (sotto). Docker: [dentro il container](#backup-docker), con il percorso del container.

```bash
# Check every entry against the manifest, and show what the archive holds
pipenv run ./dev.py backup inspect /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip

# Faster: compare the entry names with the manifest, without reading the entries
pipenv run ./dev.py backup inspect /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --no-verify
```

Risultato: il report dell'archivio, e `✅ Every entry matches the manifest` una volta confrontati dimensione e SHA-256 di ogni voce con il manifest.

| Opzione | Effetto |
| --- | --- |
| `--no-verify` | Confronta solo i nomi delle voci, senza leggerle: `ℹ️ The entry names match the manifest; their contents were not read (--no-verify)` |
| `--password-file FILE`, `--password-stdin` | La password di un archivio sicuro, dalle stesse fonti di `create` ([Un archivio sicuro](#backup-secure)); un `.zip` le ignora |
| `--identity-file FILE` | La chiave privata di un [archivio sigillato](#backup-sealed) |

- 📋 Il report: chi ha creato l'archivio e quando (`Made by LibreFolio <version> (cli) on <date> UTC`), la revisione di migrazione del database, la sua dimensione e il controllo di integrità, righe e tabelle, numero e dimensione dei file, se la chiave dell'istanza è inclusa.
- 🔐 Un archivio sicuro, riconosciuto dai primi byte qualunque sia il nome, chiede prima la password, una volta. È decifrato (`🔓 Decrypting <path>`) in una cartella privata `.decrypt-…` dentro `backups/` della directory dei dati, rimossa alla fine anche se il comando fallisce: servono quella directory e spazio per l'archivio decifrato, circa la dimensione del `.lfbk`. Una cartella lasciata da un `inspect` interrotto bruscamente (corrente, `kill -9`) è rimossa dal successivo `inspect`, o dal successivo avvio di LibreFolio, quando ha un'ora: una più giovane può essere di un altro `inspect` in corso. Il report aggiunge `Secure backup: decrypted with its password`. Password errata: `❌ The password does not open this backup (wrong_password)`; `password_required`, `envelope_damaged` e `envelope_unsupported` sono tra i rifiuti di [Provare un ripristino su una copia](#backup-restore-dry-run).
- ❌ Esce con `1` quando mancano voci, differiscono dal manifest o non sono in esso (le prime cinque di ciascun tipo), e quando il file non è un archivio leggibile: il messaggio termina con un codice, come `archive_unreadable` (non è uno zip, o è troncato), `manifest_missing`, `manifest_unknown_format` (non è un backup LibreFolio) o `manifest_newer_format` (creato da un LibreFolio più recente: verificalo con quella versione o una più recente).

### 🔏 Un archivio sigillato {: #backup-sealed }

Un archivio sigillato è un `.tar` la cui password è generata da LibreFolio e cifrata per una o due chiavi pubbliche age: solo la chiave privata corrispondente lo apre, il server che lo ha creato no. È fatto per backup eseguiti in autonomia, ad esempio ogni notte da cron. Cosa contiene, come conservare e cambiare la chiave: [Backup sigillati](backup_sealed.md#sealed).

1. **Su un tuo computer, non sul server**: la chiave privata non deve stare sul server.

    ```bash
    # A key pair: the private key into a file of its own (0600, never over a file), the public key printed
    pipenv run ./dev.py backup keygen --identity-file ~/librefolio-backup-key.txt
    ```

    Risultato: la chiave privata nel formato di `age-keygen` (`# created:`, `# public key: age1…`, poi `AGE-SECRET-KEY-1…`), leggibile solo dal proprietario, mai sopra un file esistente (`❌ <path> already exists: a key file is never written over`); poi `🔑 Public key, for --recipient or LIBREFOLIO_BACKUP_RECIPIENTS:` e la riga `age1…`.

2. **Terminale del server, cartella di LibreFolio** (Docker: `docker compose exec -T librefolio python dev.py backup create --sealed`).

    ```bash
    # A sealed archive for that public key (twice --recipient while a key is being changed)
    pipenv run ./dev.py backup create --recipient age1…

    # The same, for the keys of LIBREFOLIO_BACKUP_RECIPIENTS
    pipenv run ./dev.py backup create --sealed
    ```

    Risultato: `librefolio-backup-20261015-121500.tar`, con le solite regole di `-o` e dei nomi; dopo le fasi di un archivio sicuro, `… sealing`, poi `🔏 Sealed for 1 key: only the matching private key opens its password, and this server cannot.`

3. **Dove sta la chiave privata**: verificalo, ripristinalo o decifralo con `--identity-file`.

    ```bash
    # Check, restore or decrypt it where the private key is
    pipenv run ./dev.py backup inspect librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt
    pipenv run ./dev.py backup restore librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt --dry-run
    pipenv run ./dev.py backup decrypt librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt -o backup.zip
    ```

    Risultato: `🔏 Sealed backup <path>: its password opened with <key file>`, poi il comando prosegue come per un archivio sicuro con la sua password.

| Opzione | Effetto |
| --- | --- |
| `--recipient age1…` | Sigilla per quella chiave; due volte per due chiavi, mentre una chiave viene cambiata |
| `--sealed` | Sigilla per le chiavi di `LIBREFOLIO_BACKUP_RECIPIENTS` ([Variabili d'ambiente](configuration.md)); senza `--recipient` |
| `--identity-file FILE` | Apre un `.tar` per `inspect`, `restore` e `decrypt`: un file di chiave come lo scrive `age-keygen`, letto prima di ogni cambio di utente, come `--password-file`: funziona un secret Docker |

Da sapere:

- 🔑 **Nessuna password da fornire**: `--sealed` e `--recipient` vanno senza `--encrypt`, `--password-file` e `--password-stdin`, altrimenti il comando si ferma prima che venga scritto qualcosa. Non richiede un terminale: funziona da cron così com'è.
- 🗝️ **Mai la chiave dell'istanza**, nemmeno una generata da LibreFolio: a differenza di un [archivio sicuro](#backup-secure), un archivio sigillato esclude `secrets/instance.key`.
- 💽 **Spazio**: la sigillatura scrive il `.tar` accanto al `.lfbk`, quindi la cartella di lavoro in `backups/` richiede di nuovo la dimensione del `.lfbk`, più 64 MB, altrimenti `backup_no_space`.
- 🔓 **Come apre**: il comando controlla il `.tar` e il suo manifest, apre la password con la chiave, la verifica rispetto a `backup.lfbk`, poi copia `backup.lfbk` in una cartella privata della cartella temporanea di sistema, rimossa alla fine.
- ❌ Un `.tar` senza `--identity-file` si ferma con `sealed_backup_needs_key`; `--identity-file` con qualsiasi altro archivio con `❌ --identity-file opens a sealed backup (.tar) only: <path> is not one`.
- 🧾 **I rifiuti**, alla fine del messaggio: `sealed_identity_invalid` (il file non contiene una chiave age, o non si legge), `sealed_no_identity` (nessuna chiave del file apre la password), `sealed_tar_invalid` (non contiene i tre file di un archivio sigillato, in ordine, come file ustar normali), `sealed_manifest_invalid` (il suo `manifest.json` non lo descrive), `sealed_password_invalid` (ciò che la chiave ha aperto non è una password scritta da LibreFolio), poi quelli di un archivio sicuro: `wrong_password` (non apre `backup.lfbk`) e `envelope_damaged`. Ogni messaggio, con cosa fare: [Creare o aprire un backup sigillato](backup_moving.md#sealed-problems).

### 🧪 Provare un ripristino su una copia {: #backup-restore-dry-run }

**Dove: terminale del server, cartella di LibreFolio** (Docker: [dentro il container](#backup-docker)). Funziona su qualsiasi installazione con una directory dei dati, anche nuova: non usa mai il database dell'istanza, e il server può continuare a funzionare.

```bash
# Check an archive for a restore, on a copy: the instance stays as it is
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --dry-run
```

Risultato: l'archivio è estratto in una copia, `.restore/stage/<id>/` nella directory dei dati, aggiornato e verificato, poi il report dice cosa farebbe un ripristino e la copia è rimossa.

- ✅ Termina con `✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.`, codice di uscita `0`; `1` quando l'archivio è rifiutato o il ripristino bloccato: una riga con un codice tra parentesi, come `❌ The file is not a LibreFolio backup (not_a_backup)`, e nulla resta della copia.
- ♻️ Senza `--dry-run`, lo stesso controllo è la prima metà di un ripristino: [Ripristinare un archivio](#backup-restore).
- 🔐 Un [archivio sicuro](#backup-secure) chiede prima la password, come `inspect`, ed è decifrato nella copia come `.restore/stage/<id>/archive.zip`, rimosso una volta estratto. Un controllo interrotto bruscamente lascia quell'archivio, o la sua parte `archive.zip.part`: il successivo avvio di LibreFolio lo rimuove.

**Cosa controlla**, in sei passaggi, fermandosi al primo che rifiuta l'archivio (`… decrypting` per un archivio sicuro, `… checking`, `… unpacking`, `… upgrading`, `… verifying`):

1. **Un archivio LibreFolio**, con il suo `manifest.json`: una directory dei dati zippata a mano non lo è. Ogni voce, prima che un byte sia scritto: elencata dal manifest (o annunciata, per la chiave dell'istanza), file normale (non cartella, collegamento o voce cifrata), nome unico anche ignorando maiuscole e minuscole, dimensione del manifest; il tutto entra nello spazio libero.
2. **Estratto**: ogni voce in un nuovo file della copia, mai attraverso un collegamento né sopra un altro file, SHA-256 confrontato al manifest. Lo schema del database è letto senza eseguirne nulla: un trigger, una vista o una tabella virtuale, che LibreFolio non crea mai, rifiuta l'archivio (`database_foreign_objects`).
3. **La revisione decide**: la revisione di migrazione (Alembic), dal manifest e confermata dal database.
    - la stessa di questo LibreFolio: ripristinato così com'è;
    - più vecchia: la copia è aggiornata alla revisione di questo LibreFolio, in un processo separato, fermato dopo un'ora;
    - sconosciuta, molto probabilmente più recente: `revision_unknown`. Aggiorna prima LibreFolio: un database non viene mai retrocesso.

    Poi le [correzioni post-migrazione](cli_tools.md#post-migration-fixes) girano sulla copia, come a ogni avvio.

4. **Controllata prima e dopo**: prima dell'aggiornamento la copia passa il controllo di integrità di SQLite, ha esattamente le righe contate dal manifest e nessun testo non UTF-8 (LibreFolio non ne scrive, e il server non potrebbe leggerlo); dopo, passa di nuovo il controllo di integrità. Righe cambiate da una migrazione e riferimenti interrotti (chiavi esterne), mantenuti come sono, sono avvisi, non rifiuti.
5. **Amministratori**: senza un amministratore attivo nel backup, il ripristino è bloccato: nessuno potrebbe gestire l'istanza dopo.
6. **Segreti salvati**: l'istanza mantiene la propria [chiave dell'istanza](configuration_secrets.md#instance-key). I segreti dei plugin salvati (come la chiave API di un'origine dati) sono cifrati di nuovo sulla copia con essa quando l'archivio contiene la chiave che li ha cifrati, o la fornisci con `--instance-key-file` ([La chiave dell'istanza di un'altra installazione](#backup-restore-instance-key)); gli altri sono contati, da inserire di nuovo dopo il ripristino. Una copia senza segreti non legge nemmeno la chiave di questa istanza.

**Il report**:

- 📦 Chi ha creato l'archivio e quando (`Made by LibreFolio <version> (<how>) on <date> UTC`), e cosa fa un ripristino con il database: `this LibreFolio's own: restored as it is`, oppure `upgraded on the copy to <revision> (<n> migrations)`, poi ogni migrazione con la prima riga della sua descrizione.
- 🩹 Le correzioni post-migrazione che hanno cambiato qualcosa sulla copia, se presenti.
- 🔢 Righe, tabelle e dimensione del database, poi le tabelle le cui righe sono cambiate con l'aggiornamento, come `<table> (<before> → <after>)`, con `—` per una tabella che non esisteva.
- 📁 Numero e dimensione dei file; `Secure backup: decrypted with its password` per un archivio sicuro; `Instance key: included` o `Instance key: not included`, oppure `Instance key: not included; given with --instance-key-file` con quell'opzione; le chiavi salvate dei provider di dati: `Saved provider keys: <n> re-encrypted with this instance's key`, e `⚠️ <n> saved provider keys cannot be read with this instance's key: enter them again after the restore` per quelle che la chiave dell'archivio, o quella fornita, non ha letto, o quando non c'è una chiave.
- ⚖️ I totali di controllo del libro contabile: la liquidità di ogni broker in ogni valuta e la quantità di ogni posizione, dalle sole transazioni, senza prezzo, cambio, costo o data. Registrati nel manifest alla creazione, riletti sulla copia una volta aggiornata. Una differenza è un avviso, mai un rifiuto: una migrazione può correggere i dati. Una di queste righe:
    - `Ledger totals: the same as when the backup was made`;
    - `⚠️ Ledger totals differ from the backup's (<n> lines):`, poi le righe che differiscono, prima la liquidità, al massimo 20: `broker <id>, <currency> cash: <before> → <after>` o `broker <id>, asset <id> quantity: <before> → <after>`, l'importo del backup prima della freccia e quello della copia dopo, `—` per zero. `… and <n> more` conta le righe escluse;
    - `Ledger totals: not recorded in this archive`: un archivio di un LibreFolio precedente ai totali, o i cui totali non si leggevano alla creazione;
    - `Ledger totals: recorded by another version of the method, not compared`;
    - `⚠️ Ledger totals: could not be read on the copy`.
- 👑 Gli amministratori, e cosa significherà un ripristino per tutti: `After a restore you sign in with one of them, with the password of then; every session open now ends.` e `Invitations and links sent before the restore will have expired: send them again if needed.`
- ⚠️ Gli avvisi, che lasciano proseguire il ripristino: `The upgrade changed the rows of some tables (listed above)`, `The backup's database has broken references: they are kept as they are`, `The upgrade added broken references to the copy`, `The ledger's totals differ from those the backup recorded (listed above)`, `The ledger's totals could not be read on the copy` o `Some currency codes in the backup are not ISO 4217 codes, names or numbers an earlier version saved: an edit of their rows is refused until they are corrected (./dev.py db currencies lists them after the restore)`, come spiega [Codici valuta che non sono codici ISO](cli_tools.md).
- 👥 Un backup con più account attivi di quanti ne consenta `LIBREFOLIO_MAX_USERS` aggiunge una riga, una volta, senza nomi né indirizzi: `⚠️ The backup holds <n> active accounts; this instance accepts <m> (LIBREFOLIO_MAX_USERS): at the first sign-in the administrator chooses who keeps access, the others are deactivated (not deleted)`. Solo informativa: `backup restore --yes` conferma e `--dry-run` esce con `0`, come per qualsiasi backup.
- ⛔ Il blocco: `❌ The backup has no active administrator: after a restore nobody could manage the instance`.

Da sapere:

- 💽 La copia richiede spazio libero sul disco della directory dei dati: il contenuto estratto dell'archivio, più il doppio del suo database per l'aggiornamento, più 64 MB (`backup inspect` mostra quelle dimensioni); l'archivio è letto dove si trova, mai copiato. Un archivio sicuro richiede anche spazio per l'archivio decifrato, circa la sua dimensione, finché non è estratto. Spazio insufficiente → il controllo si ferma prima di estrarre, con i byte necessari (`no_space`); anche un disco che si riempie durante il controllo lo ferma.
- 📦 `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` («Opzioni principali» in [Variabili d'ambiente](configuration.md)) limita la dimensione estratta: le dimensioni del manifest sono sommate prima del controllo dello spazio, e un archivio oltre il limite è rifiutato con `unpacked_too_large`, senza estrarre nulla. Per togliere il limite in un solo comando, mettigli davanti `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0`:

    ```bash
    # Host
    LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0 pipenv run ./dev.py backup restore <archive>

    # Docker
    docker compose exec -e LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0 librefolio python dev.py backup restore <archive>
    ```

    Un limite illeggibile ferma il comando prima di `🔎 Checking … on a copy`, codice di uscita `1`: `❌ LIBREFOLIO_BACKUP_MAX_RESTORE_MB: expected a whole number of megabytes, 0 for no limit (backup_restore_unavailable)`.

- 🚦 Un archivio alla volta: con un altro controllo in corso, `❌ Another archive is being checked (from the web interface or another command): try again when it ends`.
- 🆕 Serve solo la directory dei dati, altrimenti `❌ No data directory at <path>`. Come con `-o`, un percorso relativo parte dalla radice del progetto.
- 🔗 Mantieni `.restore/` e `.restore/stage/` cartelle reali: un collegamento, o un file, al loro posto → `❌ <path> is not a plain folder (a link, or a file): the copy is made in a folder of the data directory`.

??? note "❌ Rifiuti — cosa significano i codici"

    | Codice | Perché l'archivio viene rifiutato |
    | --- | --- |
    | `not_a_backup` | Non è uno zip, o è uno zip senza il manifest che LibreFolio scrive, come una directory dei dati zippata a mano |
    | `password_required` | Un archivio sicuro, e nessuna password: nessun terminale su cui chiedere, e nessuna delle opzioni `--password-file` e `--password-stdin` |
    | `wrong_password` | La password non apre l'archivio sicuro: non è quella con cui è stato creato, oppure l'inizio del file è stato modificato |
    | `envelope_damaged` | L'archivio sicuro è danneggiato, troncato, o è stato modificato dopo la creazione |
    | `envelope_unsupported` | L'archivio sicuro proviene da un LibreFolio più recente, o richiede impostazioni che questo non accetta: aggiorna prima LibreFolio |
    | `instance_key_unreadable`, `instance_key_invalid` | Il file indicato con `--instance-key-file` non può fornire la chiave, oppure la chiave è più corta di 32 caratteri: [La chiave dell'istanza di un'altra installazione](#backup-restore-instance-key) |
    | `archive_unreadable`, `archive_damaged` | Il file non può essere letto, oppure lo zip è danneggiato |
    | `manifest_newer_format` | Il formato dell'archivio è più recente di quanto questo LibreFolio legga: aggiorna prima LibreFolio |
    | `manifest_invalid`, `manifest_unreadable`, `manifest_too_large` | Il manifest è danneggiato o non valido |
    | `unexpected_entry`, `missing_entry` | L'archivio contiene una voce che il manifest non elenca, oppure mancano voci elencate; per la chiave dell'istanza, una voce che il manifest non annuncia, o una annunciata che l'archivio non ha |
    | `duplicate_entry` | Una voce compare due volte, anche quando cambia solo la distinzione tra maiuscole e minuscole del nome, o si trova dove deve stare la cartella di un'altra voce |
    | `not_a_file`, `encrypted_entry`, `unsupported_entry` | Una voce è una cartella o un collegamento, è cifrata, o usa una compressione che LibreFolio non scrive |
    | `too_many_entries` | L'archivio contiene più di 500.000 voci |
    | `checksum_mismatch` | La dimensione o lo SHA-256 di una voce differisce dal manifest: l'archivio è danneggiato o è stato modificato |
    | `unpacked_too_large` | Una volta estratto, l'archivio supererebbe quanto questa installazione accetta per un ripristino, secondo le dimensioni del manifest: `LIBREFOLIO_BACKUP_MAX_RESTORE_MB`. Nulla viene estratto |
    | `no_space` | Spazio libero insufficiente per la copia |
    | `stage_failed` | Non è stato possibile scrivere la copia: l'errore stampato appena sopra ne indica la causa |
    | `database_damaged` | Il database del backup non supera il controllo di integrità di SQLite, prima o dopo l'aggiornamento, SQLite non riesce a leggerne lo schema, oppure contiene testo che non è UTF-8 (un altro programma vi ha scritto, o è stato modificato) |
    | `database_foreign_objects` | Il database del backup contiene un trigger, una vista o una tabella virtuale, che LibreFolio non crea mai: non è stato creato da LibreFolio, o è stato modificato. Usa un altro backup |
    | `manifest_mismatch` | Il database del backup non è quello descritto dal suo manifest |
    | `revision_missing` | Il database del backup non registra alcuna revisione di migrazione |
    | `revision_unknown` | Il backup proviene da un LibreFolio più recente, o non da questo: aggiorna LibreFolio, poi controllalo di nuovo |
    | `upgrade_failed` | L'aggiornamento della copia è fallito o è durato più di un'ora (l'errore stampato appena sopra ne indica la causa), oppure non ha raggiunto la revisione di questo LibreFolio |
    | `post_migration_failed` | Una correzione post-migrazione è fallita sulla copia: l'errore stampato appena sopra ne indica la causa |
    | `head_unknown` | Questo LibreFolio non riesce a leggere i propri script di migrazione |

### ♻️ Ripristinare un archivio {: #backup-restore }

**Dove: dove gira il server** — terminale del server, cartella di LibreFolio; con Docker [dentro il container](#backup-docker). Il ripristino è registrato per il percorso della directory dei dati: un server che trova la propria directory dei dati sotto un altro percorso non lo applica.

1. **Lancia il comando.**

    ```bash
    # Check the archive on a copy, then restore it at the next start of the server
    pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip
    ```

    Risultato: lo stesso controllo su una copia e lo stesso report di [Provare un ripristino su una copia](#backup-restore-dry-run); se l'archivio può essere ripristinato, la domanda:

    ```text
       Type "restore" to restore this archive at the next start of the server:
    ```

2. **Digita `restore`**, in minuscolo; gli spazi attorno non contano. Qualsiasi altra cosa, `Restore` o una riga vuota inclusi, termina con `Nothing restored: the copy was removed.` e codice di uscita `1`.

    Risultato, codice di uscita `0`:

    ```text
    ✅ The restore waits for the next start of the server: restart LibreFolio to apply it.
       That start replaces the database and the files, and ends every session: sign in with an administrator of the backup.
       ./dev.py backup pending shows it; ./dev.py backup pending --cancel drops it.
    ```

    Non è ancora cambiato nulla: il server continua sui suoi dati, e la copia verificata attende in `.restore/stage/<id>/`, per tutto il tempo necessario.

3. **Riavvia LibreFolio** quando ti è comodo: ferma l'intero server, poi [avvialo di nuovo](cli_tools.md#start-the-server); con Docker, `docker compose restart librefolio` ([Eseguire il backup con Docker](#backup-docker)). Se il server è fermo, il suo successivo avvio applica il ripristino.

    Risultato: quell'avvio applica il ripristino prima di leggere qualsiasi dato (sotto).

| Opzione | Effetto |
| --- | --- |
| `--dry-run` | Solo il controllo: [Provare un ripristino su una copia](#backup-restore-dry-run) |
| `--yes`, `-y` | Conferma senza chiedere. Senza un terminale, ad esempio in uno script, è obbligatorio: altrimenti `❌ No terminal to ask on: add --yes to confirm the restore. Nothing restored: the copy was removed.`, codice di uscita `1` |
| `--password-file FILE`, `--password-stdin` | La password di un [archivio sicuro](#backup-secure), obbligatoria senza terminale |
| `--instance-key-file FILE` | La chiave dell'istanza di un'altra installazione: [sotto](#backup-restore-instance-key) |
| `--identity-file FILE` | La chiave privata di un [archivio sigillato](#backup-sealed) |

**Cosa fa quell'avvio:**

1. 🛑 **Solo un avvio dell'intero server.** Ogni processo server tiene un lock sulla directory dei dati dall'inizio dell'avvio fino al termine. Un avvio che lo trova tenuto da un altro processo (un worker che uvicorn riavvia accanto ai fratelli, con `--workers`; un secondo server sulla stessa directory) lascia il ripristino in attesa (`server_running`). Riavvia l'intero server, mai un solo worker. Un avvio che trova il ripristino applicato da un altro server ancora in esecuzione, o da un altro avvio, si ferma invece di servire dati il cui ripristino non è completato.
2. 🔀 **Lo scambio.** `sqlite/`, `custom-uploads/`, `broker_reports/` e `scenario_catalog/` dell'istanza si scambiano con quelli della copia: rinomine dentro la directory dei dati, istantanee qualunque sia la dimensione. Le cartelle dell'istanza vanno in `.restore/previous/`.
3. 🔒 **Cosa resta.** `secrets/`, `logs/`, `scheduler_state.json` e `backups/` non vengono toccati: l'istanza mantiene la sua [chiave dell'istanza](configuration_secrets.md#instance-key), i log e gli archivi.
4. ✅ **Il primo avvio deve completarsi.** Prosegue sui dati ripristinati, già alla revisione di questo LibreFolio. Superato, prima di rispondere a chiunque, termina ogni sessione, revoca i link monouso del backup e rimuove dati precedenti e copia: il ripristino è completato.
5. ↩️ **Altrimenti, si torna a prima.** Se quel primo avvio fallisce (una migrazione, un file danneggiato), l'avvio successivo riporta da solo i dati a com'erano e registra il rollback con il motivo ([Seguire o annullare un ripristino](#backup-pending)). Con Docker il container si riavvia da solo; se nulla riavvia il server, avvialo tu.

**Dopo il ripristino:**

- 🔑 Tutti accedono di nuovo, su ogni dispositivo, con un account del backup e la password di allora. Il report del controllo indica gli amministratori del backup.
- 🔗 Nessun link inviato prima del ripristino funziona più (inviti, reimpostazioni della password, verifiche email), nemmeno quelli ancora nel backup: inviane di nuovi.
- 📧 Un account che il backup conteneva in attesa della verifica email perde il suo link e smette di attendere: la pagina di accesso non gliene invia un altro e risponde che l'account è disabilitato. Un amministratore lo attiva in [Utenti e inviti](users.md#actions), con l'indirizzo che resta non verificato, oppure lo elimina ([Eliminare un account](users.md#delete)), così che il proprietario si registri di nuovo e riceva un nuovo link. Un tale account non ha mai effettuato l'accesso: non contiene dati.
- 🆘 Se nessuno ricorda la password di allora di un amministratore, chi gestisce il server crea un link di reimpostazione con [`user reset-link`](cli_tools.md), oppure imposta una nuova password con `user reset`. Una volta dentro, un amministratore invia link di reimpostazione agli altri da [Utenti e inviti](users.md#reset-links).

Da sapere:

- 🚦 Un ripristino alla volta: mentre uno attende o viene applicato, `backup restore` si ferma prima del controllo con `❌ A restore already waits for the next start: ./dev.py backup pending --cancel drops it (restore_already_pending)`, codice di uscita `1`. Si ferma lì anche quando non legge lo stato del ripristino, perché non sa se uno è in attesa: `❌ The state of the restore cannot be read: <reason> (restore_state_unreadable)`, codice di uscita `1`, nulla controllato. `--dry-run` funziona comunque.
- ❌ Se la conferma è rifiutata, il comando stampa una riga con un codice, rimuove la copia ed esce con `1`: `restore_stage_outdated` (LibreFolio aggiornato tra il controllo e la conferma), `restore_stage_expired` (domanda in attesa più di 24 ore), `restore_already_pending` (un altro ripristino confermato nel frattempo). Esegui di nuovo il comando; dopo `restore_stage_outdated`, controlla di nuovo l'archivio.
- 🔗 Mantieni le quattro cartelle cartelle reali della directory dei dati: una che è un collegamento, o montata a parte, non può essere scambiata. L'avvio lascia i dati come sono e registra il rollback con `swap_failed`.
- 💽 Lo scambio non richiede spazio proprio: la copia del controllo diventa i dati dell'istanza, e i dati precedenti sono rimossi una volta completato il primo avvio.
- 🗝️ Il ripristino mantiene la chiave dell'istanza di questa installazione. I segreti salvati di un archivio di un'altra installazione sono cifrati di nuovo con essa dal controllo se l'archivio contiene la chiave che li ha cifrati (un [archivio sicuro](#backup-secure), con chiave generata da LibreFolio) o se la fornisci con `--instance-key-file` ([La chiave dell'istanza di un'altra installazione](#backup-restore-instance-key)). Altrimenti qui non si leggono: il report li conta, da inserire di nuovo dopo il ripristino, a meno che tu non rimetta prima la chiave di quell'installazione ([Segreti salvati e chiave dell'istanza](configuration_secrets.md#plugin-secrets)). Vedi «La chiave dell'istanza è solo in un archivio sicuro» sopra.

### 🗝️ La chiave dell'istanza di un'altra installazione {: #backup-restore-instance-key }

**Dove: terminale del server, cartella di LibreFolio**, con il file della chiave fuori dalla directory dei dati (Docker: un secret che solo root legge, [sotto](#backup-docker)).

```bash
# A clear archive of another installation, with the instance key of that installation
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --instance-key-file ~/old-instance.key
```

Risultato: il controllo cifra di nuovo sulla copia i segreti dei plugin salvati (come la chiave API di un'origine dati) con la chiave di questa istanza, che resta com'è.

Serve perché un archivio in chiaro esclude la chiave dell'istanza, e così un archivio sicuro la cui chiave veniva dall'ambiente: i suoi segreti salvati si aprono solo con la chiave dell'installazione che lo ha creato. Funziona con o senza `--dry-run`.

- 📁 Il report dice `Instance key: not included; given with --instance-key-file`, poi `Saved provider keys: <n> re-encrypted with this instance's key`.
- 📄 **Il file**: una copia del `secrets/instance.key` della vecchia installazione, il file del suo `LIBREFOLIO_INSTANCE_KEY_FILE` così com'è, oppure il valore del suo `LIBREFOLIO_INSTANCE_KEY` scritto in un file come era nella variabile, spazi inclusi. Tolti solo un byte order mark iniziale e i fine riga finali, come per `--password-file`: una chiave che funzionava come variabile funziona uguale nel file.
- 🔑 Letto per primo, come l'utente che ha avviato il comando, prima del passaggio all'utente proprietario della directory dei dati, come `--password-file`: con `docker compose exec` funziona un secret Docker che solo root legge. Stessa regola di `--password-file`, «Un file di cui il comando può fidarsi» in [Un archivio sicuro](#backup-secure): tienilo fuori dalla directory dei dati.
- 🙈 La chiave non viene mai stampata. Solo la riga di comando la accetta: l'interfaccia web no, e un ripristino da Impostazioni › Amministrazione › Backup conta quei segreti come non leggibili.
- ℹ️ Un archivio con la propria chiave è ripristinato con quella, qualunque cosa contenga il file: `ℹ️ The archive carries its own instance key: --instance-key-file is not used`.
- ⚠️ Una chiave che non legge nessun segreto salvato non è quella dell'installazione che ha creato il backup: `⚠️ The key given with --instance-key-file reads none of the saved provider keys: it is not the key of the instance this backup came from`, prima della riga che li conta. Se la chiave di questa istanza non è usabile, o non c'è e il controllo non riesce a crearla (`secrets/` non scrivibile), nulla è cifrato di nuovo, qualunque sia la chiave fornita: `⚠️ This instance's own key cannot be used, so nothing was re-encrypted with the key given: <problem>`, con il problema del log di avvio `The instance key cannot be used: …` («Controlli di avvio» in [Variabili d'ambiente](configuration.md)) oppure, senza chiave, `<path>: there is no instance key yet, and it could not be created`. I segreti già sotto la chiave di questa istanza, come in un archivio di questa stessa istanza, restano come sono.
- ❌ Esce con `1`, prima di controllare qualsiasi cosa, quando il file non fornisce la chiave: `❌ instance key file: <path> does not exist (instance_key_unreadable)`, oppure `cannot be read (…)`, `is empty or blank`, `is not UTF-8 text`, `is larger than 65536 bytes, too large for a secret`, `is not a regular file`, `goes through a link inside the data directory: give the file itself, from outside it`. Una chiave più corta di 32 caratteri lo ferma prima che la copia sia creata: `❌ The instance key given is too short: an instance key has at least 32 characters (instance_key_invalid)`.

### ⏳ Seguire o annullare un ripristino {: #backup-pending }

**Dove: terminale del server, cartella di LibreFolio** (Docker: [dentro il container](#backup-docker)); `--recover previous` solo con LibreFolio fermo.

```bash
# The restore waiting for the next start, or the last one
pipenv run ./dev.py backup pending

# Drop the restore waiting, and its checked copy (the same as --recover cancel)
pipenv run ./dev.py backup pending --cancel

# When the state of the restore cannot be read: put the data of before back (LibreFolio stopped)
pipenv run ./dev.py backup pending --recover previous

# For a script: the state as one JSON line, and the same actions with fixed exit codes
pipenv run ./dev.py backup pending --json
pipenv run ./dev.py backup pending --recover cancel --json
```

Risultato: `backup pending` non cambia nulla ed esce con `0`, tranne quando non legge lo stato del ripristino ([Uno stato del ripristino illeggibile](#backup-pending-unreadable)). Mostra una di queste righe:

| Stampa | Cosa significa |
| --- | --- |
| `ℹ️ No restore waits for the next start` | Nessun ripristino confermato, o l'ultimo annullato |
| `⏳ A restore waits for the next start of the server`, poi `backup made by LibreFolio <version> on <date> UTC; confirmed by <who> on <date> UTC` | Confermato, non ancora applicato. `<who>` è `cli` per questo comando, altrimenti il nome utente dell'amministratore che lo ha confermato |
| `⏳ A restore is being applied by the server` | Un avvio lo ha applicato e non è ancora completato. Se quel processo è terminato in modo anomalo, il successivo rimette i dati a posto |
| `✅ The last restore was applied on <date> UTC: backup made by LibreFolio <version> on <date> UTC` | Completato |
| `⚠️ The last restore was rolled back on <date> UTC, the data is as it was before: <reason> (<code>)` | Annullato, per il motivo nella tabella sotto |

| Opzione | Effetto |
| --- | --- |
| `--cancel` | Annulla il ripristino in attesa, con la sua copia: [sotto](#backup-pending-unreadable) |
| `--json` | Lo stato come una riga JSON, per gli script: [Per gli script](#backup-pending-json) |
| `--recover CHOICE` | `previous` o `cancel`, con codici di uscita fissi: [Per gli script](#backup-pending-json) |

Quando un avvio ha trovato un ripristino in attesa senza applicarlo, una riga in più ne dice il motivo, e il ripristino resta in attesa:

- `⚠️ At the last start a backup was running: the next start applies it (backup_running)`: un backup era in corso all'avvio, ad esempio un `backup create` dalla riga di comando.
- `⚠️ It was confirmed for another data directory (<path>): this one does not apply it (other_data_directory)`: il server ha trovato la propria directory dei dati sotto un percorso diverso da quello della conferma, ad esempio una copia della directory dei dati. Annullalo con `--cancel`, poi esegui `backup restore` dove gira il server.
- `⚠️ At the last start another server process was serving the data directory: restart the whole server to apply it (server_running)`: un worker riavviato mentre gli altri servivano (`--workers`), oppure un altro server sulla stessa directory dei dati. Riavvia l'intero server.

| Codice | `<reason>` | Cosa fare |
| --- | --- | --- |
| `first_start_failed` | `the first start after it did not complete` | Il log di quell'avvio ne indica la causa |
| `swap_interrupted` | `the start that applied it was interrupted` | Nulla: un avvio si è fermato durante lo scambio, e il successivo lo ha annullato |
| `swap_failed` | `its folders could not be moved into place` | Rendi le quattro cartelle cartelle reali della directory dei dati, né collegamenti né mount separati |
| `stage_missing` | `its checked copy was gone` | La copia in `.restore/stage/` è stata rimossa o modificata: controlla di nuovo l'archivio |

Un rollback rimuove anche i dati ripristinati e la copia: per riprovare, esegui di nuovo `backup restore`. Se anche il ritorno ai dati precedenti fallisce (disco, permessi), LibreFolio non si avvia: il log contiene `The data directory is half restored: the restore could not be undone, and LibreFolio does not start on it`, e ogni avvio riprova.

#### 🧩 Uno stato del ripristino illeggibile {: #backup-pending-unreadable }

Lo stato del ripristino, `.restore/restore.json`, può diventare illeggibile: proprietario o permessi cambiati, un errore del disco, un collegamento o una cartella al suo posto, contenuto che LibreFolio non ha scritto. Un ripristino potrebbe essersi fermato a metà, e LibreFolio non sa quali dati contenga. `backup pending` lo dice ed esce con `1`:

```text
❌ The state of the restore cannot be read: <why>: a restore may have stopped half way. LibreFolio serves no data until you choose (restore_state_unreadable: <reason>)
   The data of before is kept in .restore/previous/: sqlite, user_files
   Checked copies kept: 1 (none is removed while the state cannot be read)
👉 Stop LibreFolio, then run ./dev.py backup pending --recover previous: it puts the data of before back.
```

`<reason>` è `io` (il file system lo rifiuta: restituisci `.restore/` e i suoi file all'utente che esegue LibreFolio, poi esegui di nuovo `backup pending`, che può bastare), `not_a_file` o `invalid`. Finché lo stato non si legge, nessuna copia verificata è rimossa, né dalla pulizia del server né da Impostazioni › Amministrazione › Backup, e nessun ripristino può essere confermato.

**`--recover previous`**, con LibreFolio fermo, riporta i dati di prima a partire dalle cartelle: ogni cartella conservata in `.restore/previous/` torna al suo posto, e quella che sostituisce va in `.restore/failed/`. Un ripristino completato non conservava dati precedenti: i suoi dati restano. Lo stato illeggibile è conservato come `.restore/restore.json.unreadable-<date>` per un'occhiata, e mai più letto. Poi avvia LibreFolio sui dati di prima, oppure ripristina di nuovo un backup con `backup restore`. Con LibreFolio in esecuzione si ferma con `(restore_in_use)`, codice di uscita `5`; con uno stato leggibile, o nessuno, con `(restore_nothing_to_recover)`, codice di uscita `3` ([Per gli script](#backup-pending-json)). Eseguito due volte, la seconda non cambia nulla.

**`--cancel`**, uguale a `--recover cancel` ma con i codici di uscita qui sotto, annulla il ripristino in attesa con la sua copia verificata, chiunque lo abbia confermato:

| Esito | Stampa | Uscita |
| --- | --- | --- |
| Annullato | `✅ The restore waiting for the next start was dropped, with its copy: the data stays as it is` | `0` |
| Annullato, copia non rimossa (permessi, disco) | `✅ The restore waiting for the next start was dropped: the data stays as it is` e `⚠️ Its checked copy could not be removed: it goes when its check expires`. Con un errore, il log sopra contiene `The copy of a cancelled restore could not be removed: it goes when its check expires`; una copia lasciata senza errore, come una con una cartella di sola lettura, non ne ha. LibreFolio riprova al primo avvio quando il controllo ha 24 ore | `0` |
| Non annullabile, per un errore del file system prima (il lock, o la rimozione dello stato) | `❌ The restore could not be cancelled: <reason>. It still waits for the next start (restore_cancel_failed)` | `1` |
| Stato illeggibile | La riga `restore_state_unreadable` di `backup pending` | `1` |
| Nessun ripristino in attesa, o uno già in applicazione | `❌ No restore waits for the next start: nothing to cancel (restore_not_pending)` | `1` |

#### 🤖 Per gli script: --json e --recover {: #backup-pending-json }

Uno script, o una macchina che raggiunge il server via `ssh`, legge lo stato con `--json` e agisce con `--recover CHOICE`: nulla è chiesto al terminale, e i codici di uscita sono fissi.

**La riga JSON.** Con `--json`, `backup pending` scrive esattamente una riga su stdout: un oggetto JSON, poi un fine riga, senza colori. Tutto il resto, righe di log di LibreFolio incluse, va su stderr. Esce con `0` ogni volta che la riga è stampata: uno stato illeggibile è uno stato, non un errore.

| Chiave | Valore |
| --- | --- |
| `state` | `none`, `pending`, `in_progress`, `committed`, `rolled_back` o `unreadable` |
| `reason` | Il motivo del rollback di uno stato `rolled_back` (`first_start_failed`, `swap_interrupted`, `swap_failed`, `stage_missing`), oppure `io`, `not_a_file`, `invalid` per uno `unreadable`; `null` altrimenti |
| `waiting` | Perché un avvio non ha applicato un ripristino in attesa: `backup_running`, `other_data_directory`, `server_running`, oppure `null` |
| `backup_created_at` | Quando è stato creato il backup del ripristino, come `2026-10-23T03:00:12Z` (UTC); `null` senza stato, o con uno illeggibile |
| `safety_copy` | `{"present": true, "at": "<date>Z"}` quando i dati precedenti a uno scambio sono in `.restore/previous/`, altrimenti `{"present": false, "at": null}` |
| `choices` | Le parole che `--recover` accetta ora, nella tabella sotto |

Dopo un `--recover`, la riga descrive lo stato **dopo** di esso e aggiunge `recover`, `{"choice": "<word>", "done": true}` o `false`, e, con codice di uscita diverso da `0`, `error`, la parola della tabella dei codici di uscita.

| `state` | Significa | `choices` |
| --- | --- | --- |
| `none` | Nessun ripristino confermato, o l'ultimo annullato | nessuna |
| `pending` | Un ripristino attende il prossimo avvio | `cancel` |
| `in_progress` | Un avvio lo sta applicando, o lo ha applicato e non è ancora completato | nessuna |
| `committed` | L'ultimo ripristino è completato | nessuna |
| `rolled_back` | L'ultimo ripristino è stato annullato, con il suo `reason` | nessuna |
| `unreadable` | Lo stato non può essere letto: [Uno stato del ripristino illeggibile](#backup-pending-unreadable) | `previous` |

```json
{"state":"unreadable","reason":"invalid","waiting":null,"backup_created_at":null,"safety_copy":{"present":true,"at":"2026-10-23T03:00:12Z"},"choices":["previous"]}
{"state":"pending","reason":null,"waiting":"server_running","backup_created_at":"2026-10-22T21:30:05Z","safety_copy":{"present":false,"at":null},"choices":["cancel"]}
```

La riga non contiene mai un nome utente, un'email, un percorso o un identificatore: chi ha confermato, la directory dei dati e la copia verificata non ci sono. `safety_copy.at` è il momento in cui il ripristino è stato applicato, oppure, con uno stato illeggibile, l'ultima modifica di `.restore/previous/`.

**I codici di uscita.** `--recover previous` riporta i dati di prima quando lo stato non si legge, con LibreFolio fermo; `--recover cancel` annulla il ripristino in attesa, con la sua copia verificata. Uguali con o senza `--json`:

| Uscita | Quando | `error` nella riga |
| --- | --- | --- |
| `0` | Fatto: i dati di prima sono tornati, o il ripristino in attesa è stato annullato | nessuno |
| `2` | Un errore d'uso: `--recover` senza una scelta, `--recover` con `--cancel`, o `--json` con `--cancel` (usa `--recover cancel`) | nessuno: la riga non viene scritta |
| `3` | Nulla da recuperare: nessuno stato del ripristino, o la scelta era già stata eseguita | `nothing_to_recover` |
| `4` | La scelta non è valida in questo stato, come `previous` mentre lo stato si legge, `cancel` mentre non si legge, o una parola che non è una scelta: nulla cambia | `choice_not_valid` |
| `5` | È fallito: LibreFolio è in esecuzione su questa directory dei dati (`restore_in_use`), una cartella non può tornare indietro (`restore_apply_failed`), il ripristino non può essere annullato (`failed`): nulla è dichiarato fatto. Con una directory dei dati mancante, anche `5`, ma nessuna riga: stdout vuoto, stderr ne dice il motivo | `restore_in_use`, `restore_apply_failed` o `failed` |

Eseguita di nuovo, una scelta non cambia nulla: il secondo `--recover previous` non trova uno stato illeggibile, non sposta cartelle, non aggiunge nulla a `.restore/failed/` ed esce con `3`; lo stesso per un secondo `--recover cancel`. Uno script può ripetere `previous` o `cancel` finché non legge `0` o `3`.

Uno script che legge lo stato e recupera, su un server dove LibreFolio è fermo:

```bash
state=$(pipenv run ./dev.py backup pending --json 2>/dev/null)

if [ "$(echo "$state" | jq -r '.choices | index("previous") != null')" = "true" ]; then
    pipenv run ./dev.py backup pending --recover previous --json 2>/dev/null
    case $? in
        0|3) echo "data of before is back" ;;
        5)   echo "failed: stop LibreFolio, read the log" >&2; exit 1 ;;
    esac
fi
```

### 🔓 Decifrare un archivio sicuro {: #backup-decrypt }

**Dove: qualsiasi installazione**, server in esecuzione o fermo; non richiede una directory dei dati. Docker: [dentro il container](#backup-docker), con `-o` dove l'utente del server può scrivere.

```bash
# The zip inside a secure archive, to use it by hand
pipenv run ./dev.py backup decrypt /mnt/nas/librefolio/librefolio-backup-20261015-121500.lfbk -o /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip
```

Risultato: lo zip contenuto nell'[archivio sicuro](#backup-secure), quello che `backup create` scrive senza password, con `secrets/instance.key` se l'archivio sicuro contiene la chiave.

| Opzione | Effetto |
| --- | --- |
| `-o`, `--output FILE` | Obbligatorio: il file dello zip, che non deve esistere ancora. Uno esistente è rifiutato prima della password, `❌ <path> already exists: choose another name`, nulla scritto. Percorso relativo dalla radice del progetto, come con `create` |
| `--password-file FILE`, `--password-stdin` | La password, altrimenti chiesta una volta al terminale ([Un archivio sicuro](#backup-secure)) |
| `--identity-file FILE` | La chiave privata di un [archivio sigillato](#backup-sealed) |

- ✅ Termina con `✅ Decrypted: <path> (<size>)` e `🔒 It holds every user's data in clear: keep it private, and remove it once used.`; con la chiave dell'istanza, un'ultima riga: `🔑 It also holds the instance key: with it, every saved provider key can be read.`
- ♻️ `inspect` e `restore` accettano quello zip come qualsiasi altro, e la sua chiave cifra comunque di nuovo i segreti salvati. Per ripristinare un archivio sicuro non serve: `backup restore` accetta il `.lfbk` così com'è.
- 🔒 Lo zip contiene in chiaro i dati di ogni utente, e solo il proprietario lo legge (`0600`): l'utente che ha eseguito il comando, o l'utente del server quando il comando è passato a quello.
- 👤 Dove c'è una directory dei dati e lo esegui come root, ad esempio con `docker compose exec`, legge prima `--password-file` come root (funziona un secret Docker di root), poi passa all'utente proprietario della directory dei dati, come gli altri comandi: lo zip appartiene all'utente del server, e `-o` deve essere scrivibile da quell'utente ([Eseguire il backup con Docker](#backup-docker)). Se non riesce a passare, si ferma prima di leggere l'archivio o chiedere la password: `❌ cannot switch to the owner of <path> (<uid>:<gid>): <reason>. Run the command as that user.`
- ❌ Esce con `1` quando non legge il file, come uno che solo root legge una volta passato all'utente del server (`❌ Cannot read <path>: <reason> (archive_unreadable)`, prima della password), quando il file non è un archivio sicuro (`❌ <path> is not a secure backup: a plain .zip needs no decrypting (not_an_envelope)`), quando la password non lo apre (`wrong_password`), quando è danneggiato (`envelope_damaged`: nulla resta in `-o`) o di un LibreFolio più recente (`envelope_unsupported`), e quando non scrive in `-o` (`❌ Cannot write <path>: <reason>`, una volta data la password: nulla resta lì).

### 🚚 Usare un archivio su un'altra installazione

[`backup restore`](#backup-restore) ripristina un archivio sull'installazione in cui lo esegui, con i `secrets/` di quella. Per avviare invece a mano un'altra installazione sui dati di un archivio, con i `secrets/` dell'installazione che lo ha creato, ad esempio quando sposti LibreFolio:

1. **Installazione che riceve i dati, terminale**: prima, controlla l'archivio con `backup restore <archive> --dry-run` ([Provare un ripristino su una copia](#backup-restore-dry-run)): senza cambiare nulla, dice se quel LibreFolio accetta l'archivio, quali migrazioni applicherà e con quali amministratori accederai. Poi **ferma LibreFolio**.
2. **Directory dei dati vuota** (`LibreFolio-data/` con Docker Compose): se contiene qualcosa, spostalo prima da parte: nulla dei vecchi dati deve mescolarsi con quelli dell'archivio, nemmeno `app.db-wal` e `app.db-shm` di SQLite. **Decomprimi l'archivio** lì; un archivio sicuro va prima decifrato nel suo zip ([Decifrare un archivio sicuro](#backup-decrypt)).
3. **`secrets/` nella directory dei dati**: rimettilo dalla copia salvata a parte. Lo zip di un archivio sicuro con la chiave porta già `secrets/instance.key`: dai alla cartella il modo `0700` e al file `0600` (`chmod`), altrimenti il log di avvio mostra un avviso.
4. **Avvia LibreFolio**, la versione che ha creato l'archivio o una più recente: le migrazioni in attesa girano da sole all'avvio.

Da sapere:

- ⛔ LibreFolio non retrocede mai un database: un archivio di una versione più recente richiede quella o una più recente, e una più vecchia non si avvia su di esso. `backup inspect` mostra la versione che ha creato l'archivio; `backup restore --dry-run` lo rifiuta con `revision_unknown`.
- 🧹 Il `manifest.json` lasciato nella radice della directory dei dati è innocuo: puoi eliminarlo.
- 👤 Con Docker, il container assegna la directory dei dati al suo utente a ogni avvio: il proprietario dei file decompressi non importa. Su un'installazione host, decomprimi come l'utente che esegue LibreFolio.
- 🗝️ La chiave di un archivio sicuro funziona solo dove non sono impostate né `LIBREFOLIO_INSTANCE_KEY` né `LIBREFOLIO_INSTANCE_KEY_FILE`: una chiave impostata lì prevale su `secrets/instance.key`. Non metterla mai al posto di una chiave già in uso: ciò che è stato salvato con quella chiave diventerebbe illeggibile. Un'installazione con una propria chiave accetta l'archivio con [`backup restore`](#backup-restore), che cifra di nuovo i segreti salvati.

### 🐳 Eseguire il backup con Docker {: #backup-docker }

**Dove: terminale del server, cartella di `docker-compose.yml`.** Il comando gira dentro il container, dove la directory dei dati è `/app/backend/data/prod-docker`.

```bash
# Write an archive: on the host, it appears in its own folder of ./LibreFolio-data/backups/
docker compose exec librefolio python dev.py backup create

# Check it, with its path inside the container
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# Try a restore of it on a copy: the instance stays as it is
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip --dry-run

# Restore it: the same check, then type "restore" to confirm
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# Restart the container: its start applies the restore
docker compose restart librefolio

# Then see how it went
docker compose exec librefolio python dev.py backup pending
```

Risultato: come sull'host; l'archivio di `backup create` è in una cartella dedicata, come `/app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/`, cioè `./LibreFolio-data/backups/` sull'host.

- 👤 `docker compose exec` gira come root: il comando passa all'utente proprietario della directory dei dati, `backup decrypt` incluso, e ciò che scrive appartiene all'utente del server. Se non riesce a passare, si ferma e ti chiede di eseguirlo come quell'utente: `docker compose exec --user <uid>:<gid> librefolio python dev.py backup create`, con i numeri del messaggio.
- 📂 `-o` e gli archivi di `inspect` e `restore` sono percorsi dentro il container. Un archivio che è sull'host: copialo prima in `LibreFolio-data/`, ad esempio in `LibreFolio-data/backups/`. Un archivio da scrivere fuori da `LibreFolio-data/backups/`: una cartella montata dall'host, scrivibile dall'utente del server; altrove resta dentro il container e va perso quando il container è ricreato.
- 🔑 `restore` e `decrypt` leggono l'archivio come utente del server: uno scritto da `backup create` va bene, uno copiato da te deve essere leggibile da quell'utente, altrimenti `archive_unreadable`. Con l'immagine ufficiale, `sudo chown 1000:1000 <archive>` sull'host.
- ⌨️ `docker compose exec` dà al comando un terminale su cui chiedere. Senza, ad esempio `docker compose exec -T` in uno script, aggiungi `--yes`.
- 🔐 [Archivio sicuro](#backup-secure): `--encrypt` chiede la password su quel terminale. Con `-T`, ad esempio da cron, usa `--password-file` e un secret Docker, come `/run/secrets/backup_password`: [l'esempio](backup_restore.md#command-line) in Backup, ripristino e spostamento dell'istanza mostra le righe da aggiungere a `docker-compose.yml`. Lo zip di `backup decrypt` appartiene all'utente del server: dagli un `-o` scrivibile da lui, in `LibreFolio-data/backups/` o in una cartella montata dall'host: `docker compose exec librefolio python dev.py backup decrypt /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.lfbk -o /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip`.
- 🔏 [Archivio sigillato](#backup-sealed), senza terminale: `docker compose exec -T librefolio python dev.py backup create --sealed` legge `LIBREFOLIO_BACKUP_RECIPIENTS` dall'ambiente del container, che `env_file: .env` popola; dopo una modifica di `.env`, `docker compose up -d` ricrea il container. Per aprirne uno nel container, dai a `--identity-file` un percorso al suo interno; meglio, aprilo sul tuo computer, dove sta la chiave privata ([Aprire un backup sigillato](backup_sealed.md#sealed-open)).
- 🔁 Dopo un primo avvio fallito sui dati ripristinati, il container si riavvia da solo (`restart: unless-stopped`, in entrambi i file compose forniti da LibreFolio), e quell'avvio riporta i dati a com'erano.
- 🔒 Sull'host, gli archivi appartengono all'utente del container, e solo lui li legge: con un altro utente host, copiali con `sudo cp -a`.
- 💻 Da un checkout del codice sorgente, `./dev.py docker exec backup create` fa lo stesso.

---

## 🔗 Correlati

- 📄 **[Strumenti da riga di comando](cli_tools.md)** — Avviare il server, gestire gli utenti, mantenere il database, …
