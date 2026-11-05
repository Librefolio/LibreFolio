# 💾 Strumenti di amministrazione CLI: Backup

Questa pagina fa parte della guida agli strumenti da riga di comando. Copre i comandi di **backup**: creazione, verifica e ripristino di un archivio, come seguire un ripristino e come eseguire il backup con Docker.

Il resto della guida inizia da [Strumenti da riga di comando](cli_tools.md).

---

## 💾 Eseguire il backup dell'istanza {: #backup }

`backup create` inserisce l'intera istanza in un unico archivio zip, mentre il server continua a funzionare: il database, i file caricati, i report dei broker e i tuoi scenari di stress. Con `--encrypt`, crea un [archivio sicuro](#backup-secure), cifrato con una password scelta da te, che `backup decrypt` riporta al suo zip. Con `--sealed` o `--recipient`, crea un [archivio sigillato](#backup-sealed), la cui password può essere aperta solo da una tua chiave privata, per backup eseguiti in autonomia. `backup inspect` verifica un archivio e mostra cosa contiene, `backup restore --dry-run` prova a ripristinarlo su una copia, lasciando l'istanza com'è, e `backup restore` lo ripristina al successivo avvio del server. Per copiare invece manualmente la directory dei dati, vedi [Backup](filesystem.md#backup).

### 📦 Creare un archivio

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

- 🟢 Il server continua a funzionare, e a scrivere, durante il backup: il database viene copiato con `VACUUM INTO` di SQLite, un'istantanea coerente, poi sulla copia vengono eseguiti il controllo di integrità e quello delle chiavi esterne di SQLite.
- 🗃️ **Senza `--output`, l'archivio resta sul server**, in una cartella dedicata dentro `backups/`, come `backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip`: la cartella prende il nome dal momento, da dove proviene il backup (`cli`) e da un codice breve. Nulla viene copiato o spostato, e il comando stampa quel percorso, poi una riga `SHA-256: <64 hexadecimal digits>`, il checksum dell'archivio. Il backup compare quindi nell'elenco di **Impostazioni › Amministrazione › Backup**, e nella pulizia automatica: [Backup conservati sul server](backup_restore.md#kept-backups).
- 📋 **Con `--output`, l'archivio viene copiato lì** e nulla resta in `backups/`: la stessa riga `SHA-256:` segue il percorso della copia. Confrontala con il checksum del file una volta che è su un altro disco.
- 🏷️ L'archivio prende il nome dal momento in cui inizia il backup, in UTC: `librefolio-backup-20261015-121500.zip`, oppure `.lfbk` per un [archivio sicuro](#backup-secure). In una cartella indicata con `--output` che contiene già un file con quel nome, ad esempio dopo due backup nello stesso secondo, diventa `librefolio-backup-20261015-121500-2.zip`, poi `-3`, e così via: un archivio non sostituisce mai un file.
- 📁 `--output` (`-o`) viene controllato prima che il backup inizi, e il comando deve poter scrivere lì. Una cartella esistente riceve l'archivio con il suo nome predefinito. Qualsiasi altro percorso è il file dell'archivio, anche uno che termina con `/`: una cartella che non esiste ancora diventa il nome dell'archivio. Quel file non deve esistere ancora, e il suo nome non viene mai cambiato. Le sue cartelle mancanti vengono create solo quando l'archivio viene spostato lì, così un backup fallito non lascia dietro di sé una cartella vuota. Preferisci percorsi assoluti: uno relativo parte dalla radice del progetto, da qualunque punto tu esegua il comando.
- 💽 Prima di scrivere qualsiasi cosa, il comando controlla lo spazio libero dove costruisce l'archivio, nella cartella `backups/` della directory dei dati, anche con `-o`: circa il doppio della dimensione del database, più i file, più un piccolo margine. Quando è insufficiente, o quando il disco o una quota si riempiono comunque durante il backup, il comando si ferma con `❌ Backup failed (backup_no_space): not enough free space`. Quando `-o` è su un altro disco, lo spazio lì viene controllato una volta che l'archivio è costruito e la sua dimensione è nota.
- 🛟 Se l'archivio finito non può andare in `-o` (nel frattempo è comparso un file con quel nome, non è possibile creare le sue cartelle, l'altro disco è a corto di spazio, un errore di scrittura), viene messo invece in `backups/`, come file sciolto: non compare nell'elenco dei backup conservati e la pulizia automatica non lo rimuove mai. Il comando termina con `1`. Uno spostamento che fallisce a metà non lascia file parziali.
- 🚦 Un backup alla volta: mentre ne è in corso un altro, il comando si ferma e ti chiede di riprovare quando l'altro backup è terminato.
- ✅ Termina con `✅ Backup written: <path>`, la dimensione e il tempo impiegato, `SHA-256: <checksum>`, eventuali avvisi e un promemoria: `🔒 The archive holds every user's data: keep it private.`, oppure, per un archivio sicuro, `🔐 Encrypted with your password: only that password opens it, and LibreFolio cannot recover a lost one.` Esce con `0` quando l'archivio è dove hai chiesto, anche in presenza di avvisi, e con `1` altrimenti.
- 🔒 Senza una password, l'archivio non è cifrato: LibreFolio lo scrive, come un archivio sicuro, in modo che solo il proprietario possa leggerlo e scriverlo (`0600`). Conservalo, insieme a ogni copia, con la stessa riservatezza della directory dei dati.
- 🗑️ I backup conservati in `backups/` restano lì finché non li elimini da **Impostazioni › Amministrazione › Backup** o dalla cartella, oppure finché la [pulizia automatica](backup_restore.md#backup-cleanup) che hai impostato non li rimuove, tranne l'ultimo. LibreFolio non tocca mai i file `librefolio-backup-*.zip` sciolti che le versioni precedenti hanno lasciato in `backups/`. Quella cartella è sullo stesso disco dei dati, quindi copia gli archivi su un altro disco, un NAS o fuori sede, oppure scrivili lì direttamente con `-o`.
- 🔗 Mantieni `backups/` come cartella reale, mai come collegamento a un NAS o a un altro disco: ogni archivio viene prima costruito al suo interno, anche con `-o`. Un collegamento, o un file, al suo posto ferma il comando con `❌ <data dir>/backups is not a plain folder (a link, or a file): …`.
- 🧪 `backup --test-db create` esegue invece il backup della directory dei dati di test: un'opzione di sviluppo.

??? note "⚠️ Avvisi ed errori — cosa significano i messaggi"

    **Avvisi**: l'archivio viene comunque scritto.

    - `The database failed its integrity check` o `The database has foreign-key violations`: l'archivio conserva il database così com'è, e `backup inspect` mostra il risultato del controllo di integrità.
    - `Left out (<n>): links, special files, files or folders that could not be read, or files removed during the backup`, seguiti dalle voci, al massimo 50: non sono nell'archivio. I collegamenti non vengono mai seguiti, anche quando un'intera cartella come `custom-uploads/` è un collegamento a un altro disco.
    - `The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore`: un [archivio sicuro](#backup-secure) senza la chiave.

    **Non dove hai chiesto**: l'archivio viene scritto, e il comando esce con `1`.

    - `⚠️ <reason>: the archive was written to <path> instead`, seguito dalle righe usuali: `-o` non ha potuto ricevere l'archivio finito, quindi è in `backups/`, come file sciolto fuori dall'elenco dei backup conservati. Spostalo dove vuoi.
    - `❌ <reason>: the archive stays in <path>. Move it within the hour: the next backup after that removes it.`: neanche `backups/` ha potuto riceverlo. È ancora nella cartella di lavoro del backup, dentro `backups/.jobs/`, che il primo backup avviato dopo quell'ora, o il primo avvio di LibreFolio dopo quell'ora, rimuove: sposta l'archivio fuori prima di allora.

    **Errori**: nessun archivio viene scritto, e il comando esce con `1`.

    - `❌ No data directory at <path>` o `❌ No database at <path>: nothing to back up`: il comando esegue il backup della [directory dei dati](filesystem.md) con cui è configurato LibreFolio; controlla `LIBREFOLIO_DATA_DIR`.
    - `❌ <path> already exists: choose another name or folder`, `❌ <path> is not a folder: choose another path` (un file occupa il posto dove il percorso richiede una cartella) o `❌ cannot write into <folder>: choose another folder, or run the command as a user who can`: `-o` non può ricevere l'archivio. Il backup non è iniziato e non è stato creato nulla.
    - `❌ <data dir>/backups is not a plain folder (a link, or a file): …`: rendi di nuovo `backups/` una cartella reale. `❌ The backup could not run in <data dir>/backups: <reason>`: il comando non ha potuto preparare lì la sua cartella di lavoro, ad esempio perché non può scrivere nella directory dei dati.
    - `❌ Backup failed (backup_no_space): not enough free space`: lo spazio libero era insufficiente all'inizio, oppure il disco o una quota si sono riempiti durante il backup, anche a metà di un file. Libera spazio sul disco della directory dei dati.
    - `❌ Backup failed (backup_failed): the cause is in the log above`: qualsiasi altro errore. Uno di questi è un file che fallisce mentre viene copiato nell'archivio, come un errore di lettura a metà del file: una parte di un file non può essere rimossa da uno zip, quindi l'intero backup si ferma. Un file che fallisce prima che la sua copia inizi viene invece escluso con l'avviso sopra.

### 🗃️ Dove restano i backup {: #backup-kept }

Il comando e l'app lasciano entrambi i backup finiti in `backups/`, una cartella ciascuno, con nome `librefolio-backup-<date>-<time>-<origin>-<id>`, dove l'origine è `cli` qui e `ui` per l'app. `backups/.jobs/` contiene solo un backup in corso o uno fallito. Cosa farne:

- 📋 Elencali, scaricali ed eliminali in **Impostazioni › Amministrazione › Backup**, oppure in **File › Backup** (solo amministratori): [Backup conservati sul server](backup_restore.md#kept-backups).
- 🧹 Imposta una dimensione totale e un'età massima, entrambe opzionali, in modo che i più vecchi vengano eliminati da soli, mai l'ultimo: [Pulizia automatica](backup_restore.md#backup-cleanup). Il comando le applica dopo ogni backup, come fa l'app.
- 💽 Una copia sul disco dei tuoi dati non è un vero backup: copia l'archivio su un altro disco, oppure usa `--output`.
- 🔎 Per verificare o ripristinare un archivio conservato dalla riga di comando, passa a `backup inspect` o `backup restore` il percorso stampato da `backup create`.

### 🔐 Un archivio sicuro {: #backup-secure }

```bash
# The password is asked twice at the terminal
pipenv run ./dev.py backup create --encrypt

# The password read from a file that holds it alone (with Docker, a secret: /run/secrets/…)
pipenv run ./dev.py backup create --password-file ~/.librefolio-backup-password

# The password read from the standard input, such as from a password manager
pass show librefolio/backup | pipenv run ./dev.py backup create --password-stdin
```

Un archivio sicuro, `librefolio-backup-20261015-121500.lfbk`, è lo zip che `backup create` scrive senza password, cifrato con una password scelta da te: solo quella password lo apre, e LibreFolio non può recuperarne una perduta. Cosa protegge e cosa no: [Backup sicuri](backup_restore.md#secure).

- 🔑 **Da dove proviene la password**, mai dalla riga di comando, che ogni utente del server può leggere (`ps`) e che la shell conserva nella cronologia: non esiste un'opzione `--password`, e i comandi che accettano una password non accettano opzioni abbreviate.
    - `--encrypt` da solo: digitata al terminale, due volte.
    - `--password-file FILE`: il testo del file, senza il byte order mark iniziale e senza i caratteri di fine riga finali, come per [Segreti nei file](configuration_secrets.md#secret-files): un file che contiene solo la password, come un secret Docker. Un percorso relativo parte dalla radice del progetto.
    - `--password-stdin`: una riga dello standard input, senza il suo fine riga, ad esempio da una pipe. Al terminale, la password viene chiesta come senza l'opzione, senza essere mostrata, due volte per `create`: digitata lì come riga, sarebbe visibile.

    `--password-file` e `--password-stdin` si escludono a vicenda, e ciascuna rende l'archivio sicuro senza `--encrypt`.

- 📄 **Un file di cui il comando può fidarsi.** Il file di `--password-file`, come quello di `--instance-key-file` ([La chiave dell'istanza di un'altra installazione](#backup-restore-instance-key)), deve essere un file regolare: un FIFO, una cartella o un dispositivo viene rifiutato subito, senza mai attenderlo né leggerlo, con `❌ password file: <path> is not a regular file (password_unreadable)`. Avviato come root, ad esempio con `docker compose exec`, il comando rifiuta anche un percorso che passa attraverso un collegamento dentro la directory dei dati, dove l'utente di LibreFolio potrebbe averne piazzato uno verso un file che solo root può leggere: `❌ password file: <path> goes through a link inside the data directory: give the file itself, from outside it (password_unreadable)`. Un collegamento altrove viene seguito, come Kubernetes monta i suoi secret; i secret Docker e Compose sono file normali. Per `--instance-key-file`, le stesse righe iniziano con `instance key file:` e terminano con `(instance_key_unreadable)`.

- 📏 **Le regole** sono quelle di una password di account con almeno 12 caratteri: una lettera maiuscola e una minuscola, una cifra e un simbolo, ogni classe conteggiata in Unicode come per gli account; al massimo 1024 caratteri. Vengono controllate prima che il backup inizi: una password che ne viola una non scrive nulla.
- 🗝️ **La chiave dell'istanza.** L'archivio contiene `secrets/instance.key` quando LibreFolio ha generato la chiave e può usarla; mai una chiave impostata con `LIBREFOLIO_INSTANCE_KEY` o `LIBREFOLIO_INSTANCE_KEY_FILE`. Una chiave generata che non può essere usata, danneggiata, irraggiungibile o più lunga di 4096 byte, più di quanto un ripristino rilegga, viene esclusa, con l'avviso `⚠️ The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore`, e l'archivio viene comunque scritto.
- 🔐 **La cifratura** avviene dopo le fasi usuali, come `… encrypting`. Scrive il `.lfbk` accanto allo zip in `backups/`, quindi lì serve di nuovo la dimensione dello zip, più 64 MB: quando è insufficiente, `❌ Backup failed (backup_no_space): not enough free space`. Lo zip viene rimosso una volta cifrato, o quando il backup fallisce. Un backup interrotto bruscamente, da un'interruzione di corrente o da `kill -9`, non può rimuoverlo: il successivo avvio di LibreFolio termina quel backup come interrotto e rimuove ciò che ha lasciato in `backups/.jobs/`, zip e copia del database inclusi.
- ✅ Termina come sopra, con il promemoria `🔐 Encrypted with your password: only that password opens it, and LibreFolio cannot recover a lost one.`

??? note "❌ Errori della password — cosa significano i messaggi"

    Non viene scritto nulla, e il comando esce con `1`.

    - `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)`: `--encrypt` senza un terminale su cui chiedere, ad esempio in cron. Una password vuota digitata al terminale termina con `❌ No password was typed (password_required)`, una riga vuota ricevuta tramite pipe con `--password-stdin` termina con `❌ The standard input carried no password (password_required)`.
    - `❌ The two passwords differ (password_mismatch)`.
    - `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: <rules>)`: i codici delle regole non rispettate, in quest'ordine: `min_length`, `uppercase`, `lowercase`, `digit`, `special`.
    - `❌ The password is longer than 1024 characters (password_too_long)`.
    - `❌ password file: <path> does not exist (password_unreadable)`, oppure `cannot be read (…)`, `is empty or blank`, `is not UTF-8 text`, `is larger than 65536 bytes, too large for a secret`, `is not a regular file`, `goes through a link inside the data directory: give the file itself, from outside it` (vedi «Un file di cui il comando può fidarsi» sopra).

    Entrambe le opzioni della password insieme, o un'opzione che non esiste, come `--password`, fermano il comando prima che inizi, con la sua riga d'uso e il codice di uscita `2`.

### 🗂️ Cosa contiene l'archivio

L'archivio ha la struttura della directory dei dati e contiene solo:

| Voce | Cos'è |
| --- | --- |
| `manifest.json` | La descrizione dell'archivio, vedi sotto |
| `sqlite/app.db` | La copia del database |
| `custom-uploads/` | I file caricati nell'app |
| `broker_reports/` | I report dei broker |
| `scenario_catalog/` | I tuoi scenari di stress, se ne hai aggiunti |
| `secrets/instance.key` | Solo in un [archivio sicuro](#backup-secure), quando LibreFolio ha generato la chiave dell'istanza: il suo testo, fuori dall'elenco dei file del manifest. Un ripristino la legge per cifrare di nuovo i segreti salvati, e non la estrae mai |

Tutto il resto resta fuori: `secrets/` (ma `secrets/instance.key` in un archivio sicuro), `logs/`, `scheduler_state.json`, la cartella `backups/` stessa, il marcatore `.librefolio-production-data` e i file di lavoro di SQLite accanto al database: `app.db-wal`, `app.db-shm`, `app.db.post-migration.lock` e le copie `.bak` delle [correzioni post-migrazione](cli_tools.md#post-migration-fixes). La copia del database contiene già ciò che era in attesa in `app.db-wal`. I collegamenti simbolici e i file speciali non vengono mai seguiti né archiviati.

!!! warning "🔑 La chiave dell'istanza è solo in un archivio sicuro"

    Un archivio in chiaro esclude `secrets/`, che contiene la [chiave dell'istanza](configuration_secrets.md#instance-key). Eseguine il backup separatamente, come spiega [Struttura del file system → Cosa sottoporre a backup](filesystem.md#what-to-back-up), e conserva la copia con la stessa riservatezza degli archivi. Prima di avviare LibreFolio sui dati di un archivio in chiaro, rimetti `secrets/` insieme ad essi: senza la sua chiave, ciò che LibreFolio ha cifrato non può più essere letto. Un [archivio sicuro](#backup-secure) contiene la chiave generata da LibreFolio, mai una impostata con `LIBREFOLIO_INSTANCE_KEY` o `LIBREFOLIO_INSTANCE_KEY_FILE`: conserva quella dove l'hai impostata. Con una copia della chiave, un ripristino su un'altra installazione può comunque leggere i segreti salvati di un archivio in chiaro: [La chiave dell'istanza di un'altra installazione](#backup-restore-instance-key).

??? info "📋 `manifest.json` — cosa registra"

    - il formato, `librefolio-backup`, e la sua versione;
    - la versione di LibreFolio che ha creato l'archivio, come (`cli` per questo comando, `ui` per l'interfaccia web) e quando, in UTC;
    - il database: la sua revisione di migrazione (Alembic), il risultato del controllo di integrità di SQLite, il numero di violazioni di chiavi esterne, le righe di ogni tabella e i totali di controllo del libro contabile, la liquidità di ogni broker in ogni valuta e la quantità di ogni posizione (un archivio creato prima di questi non ne ha);
    - ogni voce, il database per primo, con il suo percorso, la sua dimensione e il suo SHA-256;
    - se l'archivio contiene la chiave dell'istanza, e lo SHA-256 di quella voce: solo un archivio sicuro la contiene.

### 🔍 Verificare un archivio

```bash
# Check every entry against the manifest, and show what the archive holds
pipenv run ./dev.py backup inspect /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip

# Faster: compare the entry names with the manifest, without reading the entries
pipenv run ./dev.py backup inspect /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --no-verify
```

- 🟢 Funziona su qualsiasi archivio, con il server in esecuzione o fermo, e non richiede una directory dei dati, tranne che per un archivio sicuro (sotto). Come con `-o`, un percorso relativo parte dalla radice del progetto.
- 📋 Mostra chi ha creato l'archivio e quando (`Made by LibreFolio <version> (cli) on <date> UTC`), la revisione di migrazione del database, la dimensione e il controllo di integrità, le sue righe e tabelle, il numero e la dimensione dei file, e se la chiave dell'istanza è inclusa.
- 🔎 Confronta la dimensione e lo SHA-256 di ogni voce con il manifest, e termina con `✅ Every entry matches the manifest`. `--no-verify` confronta solo i nomi delle voci, senza leggere le voci, e termina con `ℹ️ The entry names match the manifest; their contents were not read (--no-verify)`.
- 🔐 Un archivio sicuro, riconosciuto dai suoi primi byte qualunque sia il suo nome, chiede prima la sua password, una volta, dalle stesse fonti di `create` ([Un archivio sicuro](#backup-secure)). Viene quindi decifrato (`🔓 Decrypting <path>`) in una cartella privata `.decrypt-…` dentro `backups/` della directory dei dati, rimossa alla fine, anche quando il comando fallisce: il comando richiede quella directory dei dati e spazio al suo interno per l'archivio decifrato, circa la dimensione del `.lfbk`. Una cartella lasciata da un `inspect` interrotto bruscamente (un'interruzione di corrente, `kill -9`) viene rimossa dal successivo `inspect`, o dal successivo avvio di LibreFolio, una volta che ha un'ora: una più giovane potrebbe appartenere a un altro `inspect` ancora in esecuzione. Il suo report aggiunge `Secure backup: decrypted with its password`. Una password errata termina con `❌ The password does not open this backup (wrong_password)`; vedi anche `password_required`, `envelope_damaged` e `envelope_unsupported` tra i rifiuti di [Provare un ripristino su una copia](#backup-restore-dry-run). Un `.zip` ignora le opzioni della password.
- ❌ Esce con `1` quando mancano voci, differiscono dal manifest o non sono in esso (ne indica le prime cinque di ciascun tipo), e quando il file non è un archivio che riesce a leggere: il messaggio termina quindi con un codice, come `archive_unreadable` (non è un file zip, o è troncato), `manifest_missing`, `manifest_unknown_format` (non è un backup LibreFolio) o `manifest_newer_format` (creato da un LibreFolio più recente: verificalo con quella versione o una più recente).

### 🔏 Un archivio sigillato {: #backup-sealed }

Un archivio sigillato è un `.tar` la cui password è generata da LibreFolio stesso e cifrata per una o due chiavi pubbliche age: solo la chiave privata corrispondente lo apre, e il server che lo ha creato non può aprirlo. È pensato per backup eseguiti in autonomia, ad esempio ogni notte da cron. Cosa contiene, come conservare la chiave e come cambiarla: [Backup sigillati](backup_sealed.md#sealed).

```bash
# A key pair: the private key into a file of its own (0600, never over a file), the public key printed
pipenv run ./dev.py backup keygen --identity-file ~/librefolio-backup-key.txt

# A sealed archive for that public key (twice --recipient while a key is being changed)
pipenv run ./dev.py backup create --recipient age1…

# The same, for the keys of LIBREFOLIO_BACKUP_RECIPIENTS
pipenv run ./dev.py backup create --sealed

# Check, restore or decrypt it where the private key is
pipenv run ./dev.py backup inspect librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt
pipenv run ./dev.py backup restore librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt --dry-run
pipenv run ./dev.py backup decrypt librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt -o backup.zip
```

- 🗝️ **`keygen`** scrive la chiave privata nel formato di `age-keygen` (`# created:`, `# public key: age1…`, poi `AGE-SECRET-KEY-1…`), leggibile solo dal proprietario, e mai sopra un file esistente (`❌ <path> already exists: a key file is never written over`). Stampa quindi `🔑 Public key, for --recipient or LIBREFOLIO_BACKUP_RECIPIENTS:` e la riga `age1…`. Eseguilo su un tuo computer, non sul server: la chiave privata non deve stare sul server.
- 🔏 **`create --recipient age1…`** sigilla per la chiave indicata, `--recipient` due volte per due chiavi; **`create --sealed`** sigilla per le chiavi di `LIBREFOLIO_BACKUP_RECIPIENTS` ([Variabili d'ambiente](configuration.md)). L'archivio è `librefolio-backup-20261015-121500.tar`, con le solite regole di `-o` e dei nomi. Dopo le fasi di un archivio sicuro, il backup mostra `… sealing` e termina con `🔏 Sealed for 1 key: only the matching private key opens its password, and this server cannot.`
- 🔑 **Nessuna password da fornire.** `--sealed` e `--recipient` vanno senza `--encrypt`, `--password-file` e `--password-stdin`, e `--sealed` senza `--recipient`: il comando si ferma prima che venga scritto qualcosa. Non richiede un terminale, quindi funziona da cron così com'è; con Docker, `docker compose exec -T librefolio python dev.py backup create --sealed`.
- 🗝️ **Mai la chiave dell'istanza**, nemmeno una generata da LibreFolio: a differenza di un [archivio sicuro](#backup-secure), uno sigillato esclude `secrets/instance.key`.
- 💽 **Spazio.** La sigillatura scrive il `.tar` accanto al `.lfbk`, quindi la cartella di lavoro in `backups/` necessita di nuovo della dimensione del `.lfbk`, più 64 MB, altrimenti il backup si ferma con `backup_no_space`.
- 🔓 **`--identity-file`** apre un archivio sigillato per `inspect`, `restore` e `decrypt`. Legge un file di chiave come lo scrive `age-keygen`, prima di qualsiasi cambio di utente, come fa `--password-file`: funziona un secret Docker. Il comando controlla il `.tar` e il suo manifest, apre la password con la chiave, la verifica rispetto a `backup.lfbk`, stampa `🔏 Sealed backup <path>: its password opened with <key file>`, poi copia `backup.lfbk` in una cartella privata della cartella temporanea di sistema, rimossa alla fine, e prosegue come per un archivio sicuro con la sua password.
- ❌ Un `.tar` senza `--identity-file` si ferma con `sealed_backup_needs_key`; `--identity-file` con qualsiasi altro archivio si ferma con `❌ --identity-file opens a sealed backup (.tar) only: <path> is not one`.
- 🧾 **I rifiuti**, ciascuno alla fine del suo messaggio: `sealed_identity_invalid` (il file di chiave non contiene una chiave age, o non può essere letto), `sealed_no_identity` (nessuna chiave del file apre la password), `sealed_tar_invalid` (non contiene i tre file di un archivio sigillato, in ordine, come file ustar normali), `sealed_manifest_invalid` (il suo `manifest.json` non lo descrive), `sealed_password_invalid` (ciò che la chiave ha aperto non è una password che LibreFolio scrive), poi quelli di un archivio sicuro: `wrong_password` (quella password non apre `backup.lfbk`) e `envelope_damaged`. Ogni messaggio, con cosa fare: [Creare o aprire un backup sigillato](backup_moving.md#sealed-problems).

### 🧪 Provare un ripristino su una copia {: #backup-restore-dry-run }

```bash
# Check an archive for a restore, on a copy: the instance stays as it is
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --dry-run
```

`backup restore --dry-run` estrae l'archivio in una copia, la aggiorna e la verifica, poi ti dice cosa farebbe un ripristino. La copia viene creata nella directory dei dati, in `.restore/stage/<id>/`, e rimossa alla fine: il database e i file dell'istanza non vengono mai toccati, quindi il server può continuare a funzionare. Senza `--dry-run`, lo stesso controllo è la prima metà di un ripristino: vedi [Ripristinare un archivio](#backup-restore).

Un [archivio sicuro](#backup-secure) chiede prima la sua password, come fa `inspect`, e viene decifrato nella cartella della copia, come `.restore/stage/<id>/archive.zip`, che viene rimosso una volta estratto. Un controllo interrotto bruscamente lascia quell'archivio decifrato, o la sua parte `archive.zip.part`: il successivo avvio di LibreFolio lo rimuove. Il controllo passa quindi attraverso sei passaggi, e si ferma al primo che rifiuta l'archivio:

1. **Un archivio LibreFolio.** È accettato solo un archivio scritto da LibreFolio, con il suo `manifest.json`: una directory dei dati zippata a mano non lo è. Ogni voce viene controllata prima che venga scritto un byte: il manifest la elenca (o la annuncia, per la chiave dell'istanza di un archivio sicuro), è un file normale (non una cartella, un collegamento o una voce cifrata), il suo nome compare una sola volta, anche ignorando maiuscole e minuscole, la sua dimensione è quella nel manifest, e il tutto entra nello spazio libero.
2. **Estratto.** Ogni voce viene scritta in un nuovo file della copia, mai attraverso un collegamento né sopra un altro file, e il suo SHA-256 viene confrontato con quello del manifest. Poi, prima che qualsiasi altra cosa apra la copia, viene letto lo schema del suo database e nulla di esso viene eseguito: un trigger, una vista o una tabella virtuale, che LibreFolio non crea mai e il cui SQL verrebbe eseguito durante il controllo e nel server dopo un ripristino, rifiuta l'archivio (`database_foreign_objects`).
3. **La revisione decide.** La revisione di migrazione (Alembic) del database, indicata dal manifest e confermata dal database stesso:
    - la stessa revisione di questo LibreFolio: il database viene ripristinato così com'è;
    - una più vecchia: la copia viene aggiornata alla revisione di questo LibreFolio, in un processo separato, che viene fermato se dura più di un'ora;
    - una che questo LibreFolio non conosce, molto probabilmente di una versione più recente: rifiutata con `revision_unknown`. Aggiorna prima LibreFolio: un database non viene mai retrocesso.

    Poi le [correzioni post-migrazione](cli_tools.md#post-migration-fixes) vengono eseguite sulla copia, come a ogni avvio.

4. **Controllata prima e dopo.** Prima dell'aggiornamento, la copia supera il controllo di integrità di SQLite, contiene esattamente le righe contate dal manifest e non contiene testo che non sia UTF-8: LibreFolio non scrive mai tale testo, e il server non potrebbe leggere le sue righe dopo un ripristino. Dopo l'aggiornamento, la copia supera di nuovo il controllo di integrità, alla revisione di questo LibreFolio. Una migrazione può cambiare i dati, quindi le righe modificate sono un avviso, non un rifiuto, e lo stesso vale per i riferimenti interrotti (chiavi esterne), mantenuti così come sono.
5. **Amministratori.** Il report indica gli amministratori attivi del backup. Senza alcuno, il ripristino è bloccato: nessuno potrebbe gestire l'istanza dopo.
6. **Segreti salvati.** L'istanza mantiene la propria [chiave dell'istanza](configuration_secrets.md#instance-key). Quando l'archivio contiene la chiave che ha cifrato i suoi segreti dei plugin salvati, come la chiave API di un'origine dati, o quando fornisci quella chiave con `--instance-key-file` ([La chiave dell'istanza di un'altra installazione](#backup-restore-instance-key)), essi vengono cifrati di nuovo sulla copia con la chiave di questa istanza; gli altri vengono contati, per essere inseriti di nuovo dopo il ripristino. Una copia senza segreti non legge nemmeno la chiave di questa istanza.

Mostra i passaggi man mano (`… decrypting` per un archivio sicuro, `… checking`, `… unpacking`, `… upgrading`, `… verifying`), poi il suo report:

- 📦 Chi ha creato l'archivio e quando (`Made by LibreFolio <version> (<how>) on <date> UTC`), e cosa fa un ripristino con il database: `this LibreFolio's own: restored as it is`, oppure `upgraded on the copy to <revision> (<n> migrations)`, seguiti da ogni migrazione con la prima riga della sua descrizione.
- 🩹 Le correzioni post-migrazione che hanno cambiato qualcosa sulla copia, se presenti.
- 🔢 Le righe, le tabelle e la dimensione del database, poi le tabelle le cui righe sono state cambiate dall'aggiornamento, come `<table> (<before> → <after>)`, con `—` per una tabella che non esisteva.
- 📁 Il numero e la dimensione dei file; `Secure backup: decrypted with its password` per un archivio sicuro; `Instance key: included` o `Instance key: not included`, oppure `Instance key: not included; given with --instance-key-file` con quell'opzione; e le chiavi salvate dei provider di dati: `Saved provider keys: <n> re-encrypted with this instance's key`, e `⚠️ <n> saved provider keys cannot be read with this instance's key: enter them again after the restore` per quelle che la chiave dell'archivio, o la chiave fornita, non ha letto, o quando non c'è una chiave.
- ⚖️ I totali di controllo del libro contabile: la liquidità di ogni broker in ogni valuta e la quantità di ogni posizione, calcolate dalle sole transazioni, senza prezzo, tasso di cambio, costo o data. Il backup li ha registrati nel suo manifest, e il controllo li rilegge sulla copia una volta aggiornata. Una differenza è un avviso, mai un rifiuto: una migrazione può correggere i dati. Il report dice una delle seguenti cose:
    - `Ledger totals: the same as when the backup was made`;
    - `⚠️ Ledger totals differ from the backup's (<n> lines):`, poi le righe che differiscono, prima la liquidità, al massimo 20: `broker <id>, <currency> cash: <before> → <after>` o `broker <id>, asset <id> quantity: <before> → <after>`, l'importo del backup prima della freccia e quello della copia dopo, con `—` per zero. `… and <n> more` conta le righe escluse;
    - `Ledger totals: not recorded in this archive`: un archivio creato da un LibreFolio precedente, da prima dei totali, non ne registra alcuno, e nemmeno uno i cui totali non potevano essere letti quando è stato creato;
    - `Ledger totals: recorded by another version of the method, not compared`;
    - `⚠️ Ledger totals: could not be read on the copy`.
- 👑 Gli amministratori, e cosa significherà un ripristino per tutti: `After a restore you sign in with one of them, with the password of then; every session open now ends.` e `Invitations and links sent before the restore will have expired: send them again if needed.`
- ⚠️ Gli avvisi, che consentono al ripristino di proseguire: `The upgrade changed the rows of some tables (listed above)`, `The backup's database has broken references: they are kept as they are`, `The upgrade added broken references to the copy`, `The ledger's totals differ from those the backup recorded (listed above)`, `The ledger's totals could not be read on the copy` o `Some currency codes in the backup are not ISO 4217 codes, names or numbers an earlier version saved: an edit of their rows is refused until they are corrected (./dev.py db currencies lists them after the restore)`, come spiega [Codici valuta che non sono codici ISO](cli_tools.md).
- 👥 Un backup con più account attivi di quanti ne consenta `LIBREFOLIO_MAX_USERS` aggiunge una riga, stampata una volta, che non nomina alcun account né indirizzo: `⚠️ The backup holds <n> active accounts; this instance accepts <m> (LIBREFOLIO_MAX_USERS): at the first sign-in the administrator chooses who keeps access, the others are deactivated (not deleted)`. È solo informativa: `backup restore --yes` conferma e `--dry-run` esce con `0`, come per qualsiasi backup.
- ⛔ Il blocco, che lo vieta: `❌ The backup has no active administrator: after a restore nobody could manage the instance`.

Termina con `✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.` ed esce con `0`. Esce con `1` quando l'archivio viene rifiutato o il ripristino bloccato. Un rifiuto è una riga, il motivo seguito da un codice tra parentesi, come `❌ The file is not a LibreFolio backup (not_a_backup)`, e non resta nulla della copia.

- 💽 La copia richiede spazio libero sul disco della directory dei dati: tutto ciò che l'archivio contiene una volta estratto, più il doppio della dimensione del suo database per l'aggiornamento, più 64 MB. `backup inspect` mostra quelle dimensioni; l'archivio stesso viene letto dove si trova, mai copiato. Un archivio sicuro richiede anche spazio per il suo archivio decifrato, circa la sua dimensione, finché non viene estratto. Quando lo spazio è insufficiente, il controllo si ferma prima di estrarre qualsiasi cosa, con il numero di byte necessari (`no_space`); anche un disco che si riempie durante il controllo lo ferma.
- 📦 La dimensione estratta dell'archivio ha un limite quando `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` ne imposta uno («Opzioni principali» in [Variabili d'ambiente](configuration.md)). Le dimensioni dichiarate dal manifest vengono sommate prima di controllare lo spazio libero, e un archivio oltre il limite viene rifiutato con `unpacked_too_large`, prima che qualsiasi cosa venga estratta. `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` davanti al comando lo rimuove per quel comando: `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0 pipenv run ./dev.py backup restore <archive>`, oppure `docker compose exec -e LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0 librefolio python dev.py backup restore <archive>` con Docker. Un limite che non può essere letto ferma il comando prima di `🔎 Checking … on a copy`, con codice di uscita `1`: `❌ LIBREFOLIO_BACKUP_MAX_RESTORE_MB: expected a whole number of megabytes, 0 for no limit (backup_restore_unavailable)`.
- 🚦 Un archivio alla volta viene controllato: mentre è in corso un altro controllo, il comando si ferma con `❌ Another archive is being checked (from the web interface or another command): try again when it ends`.
- 🆕 Non usa mai il database dell'istanza: qualsiasi installazione può controllare un archivio, anche una nuova, purché esista la sua directory dei dati (altrimenti `❌ No data directory at <path>`). Come con `-o`, un percorso relativo parte dalla radice del progetto.
- 🔗 Mantieni `.restore/` e `.restore/stage/` come cartelle reali: un collegamento, o un file, al loro posto ferma il comando con `❌ <path> is not a plain folder (a link, or a file): the copy is made in a folder of the data directory`.

??? note "❌ Rifiuti — cosa significano i codici"

    | Codice | Perché l'archivio viene rifiutato |
    | --- | --- |
    | `not_a_backup` | Non è uno zip, o è uno zip senza il manifest che LibreFolio scrive, come una directory dei dati zippata a mano |
    | `password_required` | Un archivio sicuro, e nessuna password: nessun terminale su cui chiedere, e nessuna delle opzioni `--password-file` e `--password-stdin` |
    | `wrong_password` | La password non apre l'archivio sicuro: non è quella con cui è stato creato, oppure l'inizio del file è stato modificato |
    | `envelope_damaged` | L'archivio sicuro è danneggiato, troncato, o è stato modificato dopo la creazione |
    | `envelope_unsupported` | L'archivio sicuro proviene da un LibreFolio più recente, o richiede impostazioni che questo non accetta: aggiorna prima LibreFolio |
    | `instance_key_unreadable`, `instance_key_invalid` | Il file indicato con `--instance-key-file` non può fornire la chiave, oppure la chiave è più corta di 32 caratteri: vedi [La chiave dell'istanza di un'altra installazione](#backup-restore-instance-key) |
    | `archive_unreadable`, `archive_damaged` | Il file non può essere letto, oppure lo zip è danneggiato |
    | `manifest_newer_format` | Il formato dell'archivio è più recente di quanto questo LibreFolio legga: aggiorna prima LibreFolio |
    | `manifest_invalid`, `manifest_unreadable`, `manifest_too_large` | Il manifest è danneggiato o non valido |
    | `unexpected_entry`, `missing_entry` | L'archivio contiene una voce che il suo manifest non elenca, oppure mancano voci elencate dal manifest; per la chiave dell'istanza, una voce che il manifest non annuncia, o una che annuncia e che l'archivio non ha |
    | `duplicate_entry` | Una voce compare due volte, anche quando cambia solo la distinzione tra maiuscole e minuscole del suo nome, o si trova dove deve stare la cartella di un'altra voce |
    | `not_a_file`, `encrypted_entry`, `unsupported_entry` | Una voce è una cartella o un collegamento, è cifrata, o usa una compressione che LibreFolio non scrive |
    | `too_many_entries` | L'archivio contiene più di 500.000 voci |
    | `checksum_mismatch` | La dimensione o lo SHA-256 di una voce differisce dal manifest: l'archivio è danneggiato o è stato modificato |
    | `unpacked_too_large` | Una volta estratto, l'archivio sarebbe più grande di quanto questa installazione accetti per un ripristino, secondo le dimensioni dichiarate dal suo manifest: `LIBREFOLIO_BACKUP_MAX_RESTORE_MB`. Nulla viene estratto |
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

```bash
# Check the archive on a copy, then restore it at the next start of the server
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip
```

Senza `--dry-run`, `backup restore` esegue lo stesso controllo su una copia e mostra lo stesso report ([Provare un ripristino su una copia](#backup-restore-dry-run)). Quando l'archivio può essere ripristinato, ti chiede conferma:

```text
   Type "restore" to restore this archive at the next start of the server:
```

- ⌨️ Digita `restore`, in minuscolo; gli spazi attorno non contano. Qualsiasi altra cosa, `Restore` o una riga vuota inclusi, termina con `Nothing restored: the copy was removed.` e codice di uscita `1`.
- 🤖 `--yes` (`-y`) conferma senza chiedere. Senza un terminale su cui chiedere, ad esempio in uno script, è obbligatorio: altrimenti il comando si ferma con `❌ No terminal to ask on: add --yes to confirm the restore. Nothing restored: the copy was removed.` ed esce con `1`. Un [archivio sicuro](#backup-secure) richiede lì anche la sua password: aggiungi `--password-file` o `--password-stdin`.

Una volta confermato, il comando esce con `0` e dice:

```text
✅ The restore waits for the next start of the server: restart LibreFolio to apply it.
   That start replaces the database and the files, and ends every session: sign in with an administrator of the backup.
   ./dev.py backup pending shows it; ./dev.py backup pending --cancel drops it.
```

Non è ancora cambiato nulla: il server continua a funzionare sui suoi dati, e la copia verificata attende in `.restore/stage/<id>/`, per tutto il tempo necessario. Riavvia LibreFolio quando ti è comodo: ferma l'intero server, poi [avvialo di nuovo](cli_tools.md#start-the-server); con Docker, `docker compose restart librefolio` ([Eseguire il backup con Docker](#backup-docker)). Se il server è fermo, il suo successivo avvio applica il ripristino.

Quell'avvio lo applica prima di leggere qualsiasi dato:

1. 🛑 **Solo un avvio dell'intero server.** Ogni processo server di LibreFolio mantiene un lock sulla directory dei dati fin dalle prime fasi del suo avvio, prima di leggere qualsiasi dato, finché non termina. Un avvio che lo trova tenuto da un altro processo, come un worker che uvicorn riavvia accanto ai suoi fratelli in esecuzione con `--workers`, o un secondo server sulla stessa directory dei dati, lascia il ripristino in attesa (`server_running`). Riavvia l'intero server, mai un solo worker. Un avvio che trova il ripristino applicato da un altro server ancora in esecuzione, o da un altro avvio, si ferma invece di servire dati il cui ripristino non è completato.
2. 🔀 **Lo scambio.** `sqlite/`, `custom-uploads/`, `broker_reports/` e `scenario_catalog/` dell'istanza si scambiano di posto con quelli della copia. Ogni spostamento è una rinomina dentro la directory dei dati: istantanea, qualunque sia la dimensione. Le cartelle proprie dell'istanza vengono messe da parte in `.restore/previous/`.
3. 🔒 **Cosa resta.** `secrets/`, `logs/`, `scheduler_state.json` e `backups/` non vengono toccati: l'istanza mantiene la sua [chiave dell'istanza](configuration_secrets.md#instance-key), i suoi log e i suoi archivi.
4. ✅ **Il primo avvio deve completarsi.** L'avvio prosegue sui dati ripristinati, che il controllo ha già portato alla revisione di questo LibreFolio. Una volta superato, prima di rispondere a chiunque, termina ogni sessione, revoca i link monouso del backup e rimuove i precedenti dati dell'istanza e la copia: il ripristino è completato.
5. ↩️ **Altrimenti, si torna a com'era prima.** Se quel primo avvio fallisce, per una migrazione che fallisce o un file danneggiato, l'avvio successivo riporta da solo i dati a com'erano prima e registra il rollback del ripristino, con il motivo ([Seguire o annullare un ripristino](#backup-pending)). Con Docker, il container si riavvia da solo dopo un avvio fallito, quindi i dati tornano senza il tuo intervento; se non c'è nulla che riavvii il server, avvialo tu.

Dopo il ripristino:

- 🔑 Tutti devono accedere di nuovo, su ogni dispositivo, con un account del backup e la password che aveva allora. Il report del controllo indica gli amministratori del backup.
- 🔗 Nessun link inviato prima del ripristino funziona più (inviti, reimpostazioni della password, verifiche email), nemmeno quelli ancora contenuti nel backup: inviane di nuovi.
- 📧 Un account che il backup conteneva ancora in attesa della verifica email perde anch'esso il suo link e smette di attendere: la pagina di accesso non può più inviargliene un altro e risponde che l'account è disabilitato. Un amministratore lo attiva in [Utenti e inviti](users.md#actions), e il suo indirizzo resta non verificato; oppure lo elimina ([Eliminare un account](users.md#delete)), così che il suo proprietario si registri di nuovo e riceva un nuovo link. Un tale account non ha mai effettuato l'accesso, quindi non contiene dati.
- 🆘 Se nessuno ricorda la password di allora di un amministratore, chi gestisce il server crea un link di reimpostazione con [`user reset-link`](cli_tools.md), oppure imposta una nuova password con `user reset`. Una volta effettuato l'accesso, un amministratore invia link di reimpostazione agli altri da [Utenti e inviti](users.md#reset-links).

Da sapere:

- 🚦 Un ripristino alla volta: mentre uno attende o viene applicato, `backup restore` si ferma prima del controllo con `❌ A restore already waits for the next start: ./dev.py backup pending --cancel drops it (restore_already_pending)` ed esce con `1`. Si ferma anche lì quando non riesce a leggere lo stato del ripristino, poiché non può sapere se uno è in attesa: `❌ The state of the restore cannot be read: <reason> (restore_state_unreadable)`, codice di uscita `1`, nulla controllato. `--dry-run` funziona comunque.
- ❌ Se la conferma stessa viene rifiutata, il comando stampa una riga che termina con un codice, rimuove la copia ed esce con `1`: `restore_stage_outdated` quando LibreFolio è stato aggiornato tra il controllo e la conferma, `restore_stage_expired` quando la domanda è rimasta in attesa più di 24 ore, `restore_already_pending` quando nel frattempo è stato confermato un altro ripristino. Esegui di nuovo il comando; dopo `restore_stage_outdated`, controlla di nuovo l'archivio.
- 📍 Eseguilo dove gira il server, nel container con Docker: il ripristino viene registrato per il percorso della directory dei dati, e un server che trova la propria directory dei dati sotto un altro percorso non lo applica.
- 🔗 Mantieni le quattro cartelle come cartelle reali della directory dei dati: una che è un collegamento, o che è montata a parte, non può essere scambiata. L'avvio lascia quindi i dati come sono e registra il rollback del ripristino con `swap_failed`.
- 💽 Lo scambio non richiede spazio proprio: la copia creata dal controllo diventa i dati dell'istanza, e i dati precedenti vengono rimossi una volta completato il primo avvio.
- 🗝️ Il ripristino mantiene la chiave dell'istanza di questa installazione. Quando l'archivio contiene la chiave dell'installazione che lo ha creato (un [archivio sicuro](#backup-secure), quando LibreFolio ha generato quella chiave), il controllo ha già cifrato di nuovo i suoi segreti salvati con la chiave di questa installazione. Da qualsiasi altro archivio di un'altra installazione, fornisci la chiave di quell'installazione con `--instance-key-file`, e il controllo li cifra di nuovo anch'esso ([La chiave dell'istanza di un'altra installazione](#backup-restore-instance-key)). Altrimenti non possono essere letti qui: il report li conta, per inserirli di nuovo dopo il ripristino, a meno che tu non rimetta prima la chiave di quell'installazione ([Segreti salvati e chiave dell'istanza](configuration_secrets.md#plugin-secrets)). Vedi «La chiave dell'istanza è solo in un archivio sicuro» sopra.

### 🗝️ La chiave dell'istanza di un'altra installazione {: #backup-restore-instance-key }

```bash
# A clear archive of another installation, with the instance key of that installation
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --instance-key-file ~/old-instance.key
```

Un archivio in chiaro esclude la chiave dell'istanza, e così anche un archivio sicuro la cui chiave proveniva dall'ambiente: i segreti dei plugin salvati che contiene, come la chiave API di un'origine dati, si aprono solo con la chiave dell'installazione che lo ha creato. `--instance-key-file FILE` fornisce quella chiave a `backup restore`, con o senza `--dry-run`: il controllo cifra di nuovo quei segreti sulla copia con la chiave di questa istanza, che resta com'è.

- 📄 Il file contiene la chiave dell'istanza della vecchia installazione: una copia del suo `secrets/instance.key`, il file del suo `LIBREFOLIO_INSTANCE_KEY_FILE` così com'è, oppure il valore del suo `LIBREFOLIO_INSTANCE_KEY` scritto in un file come era scritto nella variabile, spazi inclusi. Vengono eliminati solo un byte order mark iniziale e i caratteri di fine riga finali, come per `--password-file`: una chiave che funzionava come variabile funziona allo stesso modo nel file.
- 🔑 Il comando lo legge per primo, come l'utente che lo ha avviato, prima di passare all'utente proprietario della directory dei dati, come legge `--password-file`: con `docker compose exec`, funziona un secret Docker che solo root può leggere. Il file segue la stessa regola di `--password-file`, «Un file di cui il comando può fidarsi» in [Un archivio sicuro](#backup-secure): tienilo fuori dalla directory dei dati.
- 🙈 La chiave non viene mai stampata. Solo la riga di comando la accetta: l'interfaccia web non accetta mai una chiave, e un ripristino da Impostazioni › Amministrazione › Backup conta quei segreti come non leggibili.
- 📁 Il report dice `Instance key: not included; given with --instance-key-file`, poi `Saved provider keys: <n> re-encrypted with this instance's key`.
- ℹ️ Un archivio che contiene la propria chiave viene ripristinato con essa, qualunque cosa contenga il file: il report aggiunge `ℹ️ The archive carries its own instance key: --instance-key-file is not used`.
- ⚠️ Una chiave che non legge nessuno dei segreti salvati non è la chiave dell'installazione che ha creato il backup: il report aggiunge `⚠️ The key given with --instance-key-file reads none of the saved provider keys: it is not the key of the instance this backup came from`, prima della riga che li conta, per inserirli di nuovo dopo il ripristino. Quando la chiave propria di questa istanza non può essere usata, o quando non ha ancora una chiave e il controllo non riesce a crearne una, ad esempio quando non si può scrivere in `secrets/`, nulla viene cifrato di nuovo, qualunque sia la chiave fornita, e la riga è invece `⚠️ This instance's own key cannot be used, so nothing was re-encrypted with the key given: <problem>`: il problema del log di avvio `The instance key cannot be used: …` («Controlli di avvio» in [Variabili d'ambiente](configuration.md)), oppure, senza una chiave, `<path>: there is no instance key yet, and it could not be created`. I segreti già sotto la chiave di questa istanza, come in un archivio di questa stessa istanza, vengono lasciati come sono, qualunque sia la chiave fornita.
- ❌ Esce con `1`, prima che qualsiasi cosa venga controllata, quando il file non può fornire la chiave: `❌ instance key file: <path> does not exist (instance_key_unreadable)`, oppure `cannot be read (…)`, `is empty or blank`, `is not UTF-8 text`, `is larger than 65536 bytes, too large for a secret`, `is not a regular file`, `goes through a link inside the data directory: give the file itself, from outside it`. Una chiave più corta di 32 caratteri lo ferma prima che la copia venga creata: `❌ The instance key given is too short: an instance key has at least 32 characters (instance_key_invalid)`.

### ⏳ Seguire o annullare un ripristino {: #backup-pending }

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

`backup pending` non cambia nulla ed esce con `0`, tranne quando non riesce a leggere lo stato del ripristino: vedi [Uno stato del ripristino illeggibile](#backup-pending-unreadable) sotto. `--json` e `--recover` sono pensati per gli script: vedi [Per gli script](#backup-pending-json). Altrimenti mostra una di queste cose:

| Stampa | Cosa significa |
| --- | --- |
| `ℹ️ No restore waits for the next start` | Nessun ripristino è stato confermato, o l'ultimo è stato annullato |
| `⏳ A restore waits for the next start of the server`, poi `backup made by LibreFolio <version> on <date> UTC; confirmed by <who> on <date> UTC` | Confermato, non ancora applicato. `<who>` è `cli` per questo comando, altrimenti il nome utente dell'amministratore che lo ha confermato |
| `⏳ A restore is being applied by the server` | Un avvio lo ha applicato e non è ancora completato. Se quel processo di avvio è terminato in modo anomalo, il successivo rimette i dati a posto |
| `✅ The last restore was applied on <date> UTC: backup made by LibreFolio <version> on <date> UTC` | Il ripristino è completato |
| `⚠️ The last restore was rolled back on <date> UTC, the data is as it was before: <reason> (<code>)` | Il ripristino è stato annullato, per il motivo indicato sotto |

Quando un avvio ha trovato un ripristino in attesa e non lo ha applicato, una riga in più ne dice il motivo, e il ripristino resta in attesa:

- `⚠️ At the last start a backup was running: the next start applies it (backup_running)`: un backup era in corso quando il server è stato avviato, ad esempio un `backup create` dalla riga di comando.
- `⚠️ It was confirmed for another data directory (<path>): this one does not apply it (other_data_directory)`: il server ha trovato la propria directory dei dati sotto un percorso diverso da quello in cui è stato confermato il ripristino, ad esempio una copia della directory dei dati. Annullalo con `--cancel`, poi esegui `backup restore` dove gira il server.
- `⚠️ At the last start another server process was serving the data directory: restart the whole server to apply it (server_running)`: un worker è stato riavviato mentre gli altri continuavano a servire (`--workers`), oppure un altro server usa la stessa directory dei dati. Riavvia l'intero server.

| Codice | `<reason>` | Cosa fare |
| --- | --- | --- |
| `first_start_failed` | `the first start after it did not complete` | Il log di quell'avvio ne indica la causa |
| `swap_interrupted` | `the start that applied it was interrupted` | Nulla: un avvio si è fermato durante lo scambio, e il successivo lo ha annullato |
| `swap_failed` | `its folders could not be moved into place` | Rendi le quattro cartelle cartelle reali della directory dei dati, né collegamenti né mount separati |
| `stage_missing` | `its checked copy was gone` | La copia in `.restore/stage/` è stata rimossa o modificata: controlla di nuovo l'archivio |

Un rollback rimuove anche i dati ripristinati e la copia: per riprovare, esegui di nuovo `backup restore`. Se anche il ripristino dei dati precedenti fallisce, ad esempio per un errore del disco o di permessi, LibreFolio non si avvia: il suo log contiene `The data directory is half restored: the restore could not be undone, and LibreFolio does not start on it`, e ogni avvio riprova.

#### 🧩 Uno stato del ripristino illeggibile {: #backup-pending-unreadable }

Lo stato del ripristino, `.restore/restore.json`, può diventare illeggibile: proprietario o permessi cambiati, un errore del disco, un collegamento o una cartella al suo posto, o contenuto che LibreFolio non ha scritto. Un ripristino potrebbe quindi essersi fermato a metà, e LibreFolio non può dire quali dati contenga. `backup pending` lo dice ed esce con `1`:

```text
❌ The state of the restore cannot be read: <why>: a restore may have stopped half way. LibreFolio serves no data until you choose (restore_state_unreadable: <reason>)
   The data of before is kept in .restore/previous/: sqlite, user_files
   Checked copies kept: 1 (none is removed while the state cannot be read)
👉 Stop LibreFolio, then run ./dev.py backup pending --recover previous: it puts the data of before back.
```

`<reason>` è `io` (il file system lo rifiuta: restituisci `.restore/` e i suoi file all'utente che esegue LibreFolio, poi esegui di nuovo `backup pending`, il che potrebbe bastare), `not_a_file` o `invalid`. Finché lo stato non può essere letto, nessuna copia verificata viene rimossa, né dalla pulizia del server né da Impostazioni › Amministrazione › Backup, e nessun ripristino può essere confermato.

`backup pending --recover previous`, con LibreFolio fermo, riporta i dati di prima a partire da ciò che dicono le cartelle: ogni cartella conservata in `.restore/previous/` torna al suo posto, e quella che sostituisce va in `.restore/failed/`. Un ripristino completato non conservava dati precedenti, quindi i suoi dati restano. Lo stato illeggibile viene conservato come `.restore/restore.json.unreadable-<date>` per un'occhiata, e mai più letto. Poi avvia LibreFolio sui dati di prima, oppure ripristina di nuovo un backup con `backup restore`. Mentre LibreFolio è in esecuzione, si ferma con `(restore_in_use)` ed esce con `5`; con uno stato che riesce a leggere, o nessuno, si ferma con `(restore_nothing_to_recover)` ed esce con `3`: i codici di uscita sono nella tabella di [Per gli script](#backup-pending-json). Eseguito due volte, la seconda esecuzione non cambia nulla.

`--cancel`, uguale a `--recover cancel` ma con i codici di uscita sotto, annulla il ripristino in attesa, con la sua copia verificata, chiunque lo abbia confermato: `✅ The restore waiting for the next start was dropped, with its copy: the data stays as it is`, codice di uscita `0`. Se la copia non può essere rimossa, ad esempio per un errore di permessi o del disco, il ripristino viene comunque annullato, codice di uscita `0`, con invece due righe: `✅ The restore waiting for the next start was dropped: the data stays as it is` e `⚠️ Its checked copy could not be removed: it goes when its check expires`. Quando la rimozione è fallita con un errore, il log sopra di esse contiene l'avviso `The copy of a cancelled restore could not be removed: it goes when its check expires`; una copia lasciata senza un errore, come una che contiene una cartella di sola lettura, non ne ha. LibreFolio riprova al suo primo avvio quando il controllo ha 24 ore. Se il ripristino stesso non può essere annullato, per un errore del file system prima che ciò avvenga (il suo lock, o la rimozione del suo stato): `❌ The restore could not be cancelled: <reason>. It still waits for the next start (restore_cancel_failed)`, codice di uscita `1`. Quando lo stato del ripristino non può essere letto: la riga `restore_state_unreadable` di `backup pending`, codice di uscita `1`. Quando nessun ripristino è in attesa, o uno è già in fase di applicazione: `❌ No restore waits for the next start: nothing to cancel (restore_not_pending)`, codice di uscita `1`.

#### 🤖 Per gli script: --json e --recover {: #backup-pending-json }

Uno script, o una macchina che raggiunge il server via `ssh`, legge lo stato con `--json` e agisce con `--recover CHOICE`. Entrambi sono pensati per essere eseguiti senza una persona: non viene mai chiesto nulla al terminale, e i codici di uscita sono fissi.

**La riga JSON.** Con `--json`, `backup pending` scrive esattamente una riga su stdout: un oggetto JSON, poi un fine riga, senza colori. Tutto ciò che direbbe altrimenti, e le righe di log di LibreFolio, vanno su stderr. Esce con `0` ogni volta che la riga è stata stampata: uno stato illeggibile è uno stato, non un errore.

| Chiave | Valore |
| --- | --- |
| `state` | `none`, `pending`, `in_progress`, `committed`, `rolled_back` o `unreadable` |
| `reason` | Perché: il motivo del rollback di uno stato `rolled_back` (`first_start_failed`, `swap_interrupted`, `swap_failed`, `stage_missing`), oppure `io`, `not_a_file`, `invalid` per uno `unreadable`; `null` altrimenti |
| `waiting` | Perché un avvio non ha applicato un ripristino in attesa: `backup_running`, `other_data_directory`, `server_running`, oppure `null` |
| `backup_created_at` | Quando è stato creato il backup del ripristino, come `2026-10-23T03:00:12Z` (UTC); `null` senza stato, o con uno illeggibile |
| `safety_copy` | `{"present": true, "at": "<date>Z"}` quando i dati precedenti a uno scambio sono conservati in `.restore/previous/`, altrimenti `{"present": false, "at": null}` |
| `choices` | Le parole che `--recover` accetta ora, nella tabella sotto |

Dopo un `--recover`, la riga descrive lo stato **dopo** di esso e aggiunge `recover`, `{"choice": "<word>", "done": true}` o `false`, e, quando il codice di uscita non è `0`, `error`, la parola della tabella dei codici di uscita.

| `state` | Significa | `choices` |
| --- | --- | --- |
| `none` | Nessun ripristino è stato confermato, o l'ultimo è stato annullato | nessuna |
| `pending` | Un ripristino attende il prossimo avvio | `cancel` |
| `in_progress` | Un avvio lo sta applicando, o lo ha applicato e non è ancora completato | nessuna |
| `committed` | L'ultimo ripristino è completato | nessuna |
| `rolled_back` | L'ultimo ripristino è stato annullato, con il suo `reason` | nessuna |
| `unreadable` | Lo stato del ripristino non può essere letto: [Uno stato del ripristino illeggibile](#backup-pending-unreadable) | `previous` |

```json
{"state":"unreadable","reason":"invalid","waiting":null,"backup_created_at":null,"safety_copy":{"present":true,"at":"2026-10-23T03:00:12Z"},"choices":["previous"]}
{"state":"pending","reason":null,"waiting":"server_running","backup_created_at":"2026-10-22T21:30:05Z","safety_copy":{"present":false,"at":null},"choices":["cancel"]}
```

La riga non contiene mai un nome utente, un'email, un percorso o un identificatore: chi ha confermato il ripristino, la directory dei dati e la copia verificata non sono al suo interno. `safety_copy.at` è il momento in cui il ripristino è stato applicato, oppure, con uno stato illeggibile, quando `.restore/previous/` è cambiata l'ultima volta.

**I codici di uscita.** `--recover previous` riporta i dati di prima quando lo stato non può essere letto, con LibreFolio fermo; `--recover cancel` annulla il ripristino in attesa, con la sua copia verificata. I codici di uscita sono gli stessi con o senza `--json`:

| Uscita | Quando | `error` nella riga |
| --- | --- | --- |
| `0` | Fatto: i dati di prima sono tornati, o il ripristino in attesa è stato annullato | nessuno |
| `2` | Un errore d'uso: `--recover` senza una scelta, `--recover` con `--cancel`, o `--json` con `--cancel` (usa `--recover cancel`) | nessuno: la riga non viene scritta |
| `3` | Nulla da recuperare: nessuno stato del ripristino, o la scelta era già stata eseguita. | `nothing_to_recover` |
| `4` | La scelta non è valida in questo stato, come `previous` mentre lo stato può essere letto, `cancel` mentre non può, o una parola che non è una scelta: nulla cambia | `choice_not_valid` |
| `5` | È fallito: LibreFolio è in esecuzione su questa directory dei dati (`restore_in_use`), una cartella non può essere riportata indietro (`restore_apply_failed`), il ripristino non può essere annullato (`failed`): nulla viene dichiarato fatto. Con una directory dei dati mancante, anche `5`, ma nessuna riga viene scritta: stdout resta vuoto e stderr ne dice il motivo | `restore_in_use`, `restore_apply_failed` o `failed` |

Eseguita di nuovo, una scelta non cambia nulla: il secondo `--recover previous` non trova uno stato illeggibile, non sposta cartelle, non aggiunge nulla a `.restore/failed/` ed esce con `3`; lo stesso vale per un secondo `--recover cancel`. Uno script può quindi ripetere `previous` o `cancel` finché non legge `0` o `3`.

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

```bash
# The zip inside a secure archive, to use it by hand
pipenv run ./dev.py backup decrypt /mnt/nas/librefolio/librefolio-backup-20261015-121500.lfbk -o /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip
```

`backup decrypt` scrive lo zip contenuto in un [archivio sicuro](#backup-secure): l'archivio che `backup create` scrive senza password, con `secrets/instance.key` quando l'archivio sicuro contiene la chiave. `inspect` e `restore` accettano quello zip come qualsiasi altro, e la sua chiave cifra comunque di nuovo i segreti salvati. Per ripristinare un archivio sicuro non ne hai bisogno: `backup restore` accetta il `.lfbk` così com'è.

- 🔑 Chiede la password una volta, oppure la legge con `--password-file` o `--password-stdin` ([Un archivio sicuro](#backup-secure)).
- 🆕 `-o` (`--output`) è obbligatorio, ed è il file dello zip: non deve esistere ancora. Uno esistente viene rifiutato prima che venga chiesta la password, `❌ <path> already exists: choose another name`, e non viene scritto nulla. Come con `create`, un percorso relativo parte dalla radice del progetto.
- 🔒 Lo zip contiene in chiaro i dati di ogni utente, e solo il proprietario può leggerlo (`0600`): l'utente che ha eseguito il comando, o l'utente del server quando il comando è passato a quello. Termina con `✅ Decrypted: <path> (<size>)` e `🔒 It holds every user's data in clear: keep it private, and remove it once used.` Quando l'archivio sicuro contiene la chiave dell'istanza, un'ultima riga aggiunge `🔑 It also holds the instance key: with it, every saved provider key can be read.`
- 🟢 Non richiede una directory dei dati, e funziona con il server in esecuzione o fermo. Dove ce n'è una e lo esegui come root, ad esempio con `docker compose exec`, legge prima un `--password-file` come root (funziona un secret Docker di proprietà di root), poi passa all'utente proprietario della directory dei dati, come fanno gli altri comandi: lo zip appartiene quindi all'utente del server, e `-o` deve essere un luogo in cui quell'utente può scrivere ([Eseguire il backup con Docker](#backup-docker)). Se non riesce a passare, si ferma prima di leggere l'archivio o chiedere la password, con il messaggio degli altri comandi: `❌ cannot switch to the owner of <path> (<uid>:<gid>): <reason>. Run the command as that user.`
- ❌ Esce con `1` quando non riesce a leggere il file, come un file che solo root può leggere una volta che il comando gira come l'utente del server (`❌ Cannot read <path>: <reason> (archive_unreadable)`, prima che venga chiesta la password), quando il file non è un archivio sicuro (`❌ <path> is not a secure backup: a plain .zip needs no decrypting (not_an_envelope)`), quando la password non lo apre (`wrong_password`), quando è danneggiato (`envelope_damaged`: nulla resta in `-o`) o proviene da un LibreFolio più recente (`envelope_unsupported`), e quando non può scrivere in `-o` (`❌ Cannot write <path>: <reason>`, una volta fornita la password: nulla resta lì).

### 🚚 Usare un archivio su un'altra installazione

[`backup restore`](#backup-restore) ripristina un archivio sull'installazione in cui lo esegui e mantiene i `secrets/` di quell'installazione. Per avviare invece manualmente un'altra installazione sui dati di un archivio, con i `secrets/` dell'installazione che lo ha creato, ad esempio quando sposti LibreFolio:

1. **Ferma LibreFolio** sull'installazione che riceve i dati.
2. **Decomprimi l'archivio in una [directory dei dati](filesystem.md) vuota** (`LibreFolio-data/` con Docker Compose): se contiene qualcosa, spostalo prima da parte. Nulla dei vecchi dati deve mescolarsi con quelli dell'archivio, nemmeno `app.db-wal` e `app.db-shm` di SQLite. Un archivio sicuro viene prima decifrato nel suo zip ([Decifrare un archivio sicuro](#backup-decrypt)).
3. **Rimetti `secrets/`** nella directory dei dati, dalla copia che hai salvato separatamente. Lo zip di un archivio sicuro che contiene la chiave porta già `secrets/instance.key`: assegna alla cartella il modo `0700` e al file `0600` (`chmod`), altrimenti il log di avvio mostra un avviso.
4. **Avvia LibreFolio**, la versione che ha creato l'archivio o una più recente: le migrazioni in attesa vengono eseguite da sole all'avvio.

Da sapere:

- 🧪 Prima del passaggio 1, controlla l'archivio sull'installazione che lo riceve, con `backup restore <archive> --dry-run` ([Provare un ripristino su una copia](#backup-restore-dry-run)): senza cambiare nulla, ti dice se quel LibreFolio può accettare l'archivio, quali migrazioni applicherà il suo avvio e con quali amministratori effettuerai l'accesso.
- ⛔ LibreFolio non esegue mai il downgrade di un database: un archivio creato da una versione più recente richiede quella versione o una più recente, e una versione più vecchia non si avvia su di esso. `backup inspect` mostra quale versione ha creato l'archivio, e `backup restore --dry-run` rifiuta un tale archivio con `revision_unknown`.
- 🧹 Il `manifest.json` lasciato nella radice della directory dei dati è innocuo: puoi eliminarlo.
- 👤 Con Docker, il container assegna la directory dei dati al suo utente a ogni avvio, quindi il proprietario dei file decompressi non importa. Su un'installazione host, decomprimi come l'utente che esegue LibreFolio, così che i file gli appartengano.
- 🗝️ La chiave di un archivio sicuro funziona solo dove non sono impostate né `LIBREFOLIO_INSTANCE_KEY` né `LIBREFOLIO_INSTANCE_KEY_FILE`: una chiave impostata lì prevale su `secrets/instance.key`. Non metterla mai al posto di una chiave già in uso: ciò che è stato salvato con quella chiave diventerebbe illeggibile. Un'installazione con una propria chiave accetta l'archivio con [`backup restore`](#backup-restore), che cifra di nuovo i segreti salvati.

### 🐳 Eseguire il backup con Docker {: #backup-docker }

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

- 👤 `docker compose exec` viene eseguito come root: il comando passa all'utente proprietario della directory dei dati, `backup decrypt` incluso, quindi tutto ciò che scrive appartiene all'utente del server. Se non riesce a passare, si ferma e ti chiede di eseguirlo come quell'utente: `docker compose exec --user <uid>:<gid> librefolio python dev.py backup create`, con i numeri del messaggio.
- 📂 `-o` e gli archivi di `inspect` e `restore` sono percorsi all'interno del container, dove la directory dei dati è `/app/backend/data/prod-docker`. L'archivio stampato da `backup create` è in una cartella dedicata lì, come `/app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/`. Per controllare un archivio che si trova sull'host, copialo prima in `LibreFolio-data/`, ad esempio in `LibreFolio-data/backups/`. Per scrivere l'archivio altrove rispetto a `LibreFolio-data/backups/`, usa una cartella montata dall'host in cui l'utente del server possa scrivere: in qualsiasi altro posto, resta dentro il container e va perso quando il container viene ricreato.
- 🔑 `restore` e `decrypt` leggono l'archivio anche come utente del server: un archivio scritto da `backup create` va bene, ma uno che hai copiato tu deve essere leggibile da quell'utente, altrimenti si fermano con `archive_unreadable`. Con l'immagine ufficiale, `sudo chown 1000:1000 <archive>` sull'host lo assegna a quell'utente.
- ⌨️ `docker compose exec` fornisce al comando un terminale su cui chiedere. Senza, ad esempio con `docker compose exec -T` in uno script, aggiungi `--yes`.
- 🔐 Per un [archivio sicuro](#backup-secure), `--encrypt` chiede la password su quel terminale. Con `-T`, ad esempio da cron, forniscila con `--password-file` e un secret Docker, come `/run/secrets/backup_password`: [l'esempio](backup_restore.md#command-line) in Backup, ripristino e spostamento dell'istanza mostra le righe da aggiungere a `docker-compose.yml`. Anche `backup decrypt` passa all'utente del server, quindi il suo zip appartiene a quell'utente: dagli un `-o` in cui quell'utente possa scrivere, in `LibreFolio-data/backups/` o in una cartella montata dall'host, come `docker compose exec librefolio python dev.py backup decrypt /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.lfbk -o /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip`.
- 🔏 Un [archivio sigillato](#backup-sealed) non richiede un terminale: `docker compose exec -T librefolio python dev.py backup create --sealed` legge `LIBREFOLIO_BACKUP_RECIPIENTS` dall'ambiente del container, che `env_file: .env` popola; dopo una modifica di `.env`, `docker compose up -d` ricrea il container con esso. Per aprirne uno nel container, fornisci a `--identity-file` un percorso al suo interno; meglio, aprilo sul tuo computer, dove si trova la chiave privata ([Aprire un backup sigillato](backup_sealed.md#sealed-open)).
- 🔁 Dopo un primo avvio che fallisce sui dati ripristinati, il container si riavvia da solo (`restart: unless-stopped`, in entrambi i file compose forniti da LibreFolio), e quell'avvio riporta i dati a com'erano prima.
- 🔒 Sull'host, gli archivi appartengono all'utente del container, e solo quell'utente può leggerli: se il tuo utente host è un altro, copiali con `sudo cp -a`.
- 💻 Da un checkout del codice sorgente, `./dev.py docker exec backup create` fa lo stesso.

---

## 🔗 Correlati

- 📄 **[Strumenti da riga di comando](cli_tools.md)** — Avviare il server, gestire gli utenti, mantenere il database, …
