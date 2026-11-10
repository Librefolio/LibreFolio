# 🏠 Backup: spostamento e risoluzione dei problemi

Questa pagina della guida ai backup copre lo **spostamento** di LibreFolio da un'installazione a un'altra (da un hosting a un server tuo, o il contrario) e cosa fare **quando qualcosa va storto** con un backup o un ripristino.

Il resto della guida inizia da [Backup, ripristino e spostamento dell'istanza](backup_restore.md).

---

## 🏠 Porta LibreFolio a casa {: #bring-home }

Un archivio sposta il tuo LibreFolio da un'installazione a un'altra. Due vie:

| Via | Quando | Dove |
| --- | --- | --- |
| **Ripristino** | Il ripristino controlla l'archivio su una copia prima che qualcosa cambi; con Docker prende un backup sicuro (`.lfbk`) così com'è, ed è la via più semplice | Impostazioni › Amministrazione › Backup, o `backup restore` ([Ripristinare su questa installazione](backup_restore.md#restore)) |
| **A mano** | La cartella dati della destinazione è vuota, o non esiste ancora: decomprimi lo zip lì prima del primo avvio | Terminale del server di destinazione, [qui sotto](#by-hand) |

In entrambi i casi la destinazione esegue la stessa versione di LibreFolio o una più recente ([Mai all'indietro](#never-backwards)).

### ✋ A mano: decomprimi prima del primo avvio {: #by-hand }

Da sapere prima di iniziare:

- 🔎 **Nulla controlla prima l'archivio.** Un archivio danneggiato, o di un LibreFolio più recente, si manifesta quando l'avvio fallisce, e alcuni danni solo più tardi, quando una pagina legge i dati che tocca. Un ripristino lo controlla su una copia prima che qualcosa cambi. Per controllare un archivio prima di decomprimerlo a mano, usa un'installazione di LibreFolio **già in esecuzione**: `backup inspect <archive>` confronta ogni file con il manifest e, per uno zip, non scrive nulla; `backup restore <archive> --dry-run` esegue l'intero controllo di un ripristino, su una copia («Controllare un archivio» e «Provare un ripristino su una copia» in [Strumenti di amministrazione CLI](cli_tools.md)). La prova a vuoto lavora nella cartella dati di quell'installazione: non puntarla mai alla cartella vuota che stai per riempire.
- 📖 I passaggi per qualsiasi installazione, inclusa quella host: «Usare un archivio su un'altra installazione» in [Strumenti di amministrazione CLI](cli_tools.md).

I passi, con Docker Compose:

1. **Server di origine — Impostazioni › Amministrazione › Backup, o terminale.** Crea un backup e portalo sul server di destinazione ([Creare un backup](backup_restore.md#create)). Se è un backup in chiaro, porta anche la cartella `secrets/` della sua cartella dati: l'archivio non la contiene.

    Risultato: l'archivio (`.zip` o `.lfbk`) è sul server di destinazione.

2. **Server di destinazione — terminale, cartella di `docker-compose.yml`.** La cartella dati `LibreFolio-data` deve essere vuota, o non esistere ancora. Se LibreFolio è già stato avviato su di essa, fermalo (`docker compose down`) e sposta prima `LibreFolio-data` da parte.

    Risultato: nessun dato estraneo si mescola con quello dell'archivio.

3. **Solo per un backup sicuro (`.lfbk`) — terminale di un'installazione in cui è disponibile la riga di comando di LibreFolio.** Un `.lfbk` non è uno zip: trasformalo nel suo zip con `backup decrypt`.

    ```bash
    # Host installation
    pipenv run ./dev.py backup decrypt librefolio-backup-20261015-121500.lfbk -o librefolio-backup-20261015-121500.zip

    # Docker, in a running LibreFolio container: the paths inside it, and the zip where the container's user can write
    docker compose exec librefolio python dev.py backup decrypt /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.lfbk -o /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip
    ```

    Risultato: lo zip da decomprimere al passo 4. Da sapere:

    - 🔓 La password è chiesta al terminale, oppure letta con `--password-file` o `--password-stdin`.
    - 🚫 Un `-o` che esiste già viene rifiutato e non viene scritto nulla: il comando non sostituisce mai un file.
    - 🔒 Solo il proprietario legge lo zip (`0600`): l'utente che ha eseguito il comando, o con Docker l'utente del container.
    - 🗑️ Lo zip contiene i dati di ogni utente in chiaro: eliminalo una volta decompresso.
    - 🔑 Se il backup contiene la chiave dell'istanza, il comando aggiunge `🔑 It also holds the instance key: with it, every saved provider key can be read.`: chiunque abbia quello zip legge anche le chiavi salvate dei provider di dati.

4. **Server di destinazione — terminale, cartella di `docker-compose.yml`.** Decomprimi lo zip nella cartella dati.

    ```bash
    # In the folder of docker-compose.yml, before the first start
    unzip librefolio-backup-20261015-121500.zip -d LibreFolio-data
    ```

    Risultato: `LibreFolio-data/` contiene i dati dell'archivio. Il `manifest.json` lasciato lì è innocuo: puoi eliminarlo.

5. **Server di destinazione — cartella `LibreFolio-data/secrets/`.** Prima del primo avvio:

    - 🗝️ **Backup in chiaro**: rimetti il `secrets/` del server di origine in `LibreFolio-data/`, e i segreti salvati restano leggibili. Senza, LibreFolio crea una nuova chiave dell'istanza la prima volta che ne ha bisogno.
    - 🔐 **Backup sicuro che porta la chiave**: lo zip contiene già `secrets/instance.key`, e le chiavi salvate dei provider di dati restano leggibili. Rendi privati la cartella e il file, altrimenti il log di avvio contiene un avviso («Controlli all'avvio» in [Variabili d'ambiente](configuration.md)):

    ```bash
    chmod 700 LibreFolio-data/secrets
    chmod 600 LibreFolio-data/secrets/instance.key
    ```

    Risultato: la chiave dell'istanza è al suo posto, e nulla nel log di avvio la riguarda.

    !!! warning "⛔ La chiave di un backup, solo su una cartella dati vuota"

        Usa la chiave di un backup solo in questo modo: su una cartella dati vuota, su un'installazione che non imposta né `LIBREFOLIO_INSTANCE_KEY` né `LIBREFOLIO_INSTANCE_KEY_FILE`. Una chiave impostata lì ha la precedenza su `secrets/instance.key`, e le chiavi salvate dei provider di dati resterebbero illeggibili.
        Non metterla mai al posto di una chiave già in uso: ciò che è stato salvato con quella chiave diventerebbe illeggibile. Per portare un backup sicuro su un'installazione che ha una propria chiave, ripristinalo: il ripristino cifra di nuovo le chiavi salvate con la chiave di quell'installazione.

6. **Server di destinazione — terminale, cartella di `docker-compose.yml`.** Primo avvio, con la stessa immagine dell'origine o una più recente.

    ```bash
    docker compose up -d
    ```

    Risultato: l'avvio applica da solo le migrazioni in sospeso.

### ⛔ Mai all'indietro {: #never-backwards }

LibreFolio non riporta mai un database a una versione precedente: usa la versione che ha creato l'archivio, o una più recente. Un LibreFolio più vecchio rifiuta un archivio il cui database contiene una migrazione che non conosce.

- 🏷️ `backup inspect` mostra quale versione ha creato l'archivio (`Made by LibreFolio <version>`); **Impostazioni › Informazioni** mostra la versione di un'istanza.
- ❌ `backup restore` rifiuta un tale archivio con `revision_unknown`, prima che qualcosa cambi.
- 🛑 A mano, un LibreFolio più vecchio non si avvia su tali dati: il log contiene `Failed to apply database migrations`, e Docker continua a riavviare il container. Fermalo con `docker compose down`.

Aggiorna prima il LibreFolio che riceve ([Aggiornare LibreFolio](../user/installation.md#updating)), poi ripristina. Con Docker, l'immagine `latest` è la release più recente.

---

## 🧯 Quando qualcosa va storto {: #troubleshooting }

### 🔐 Creare un backup sicuro {: #secure-problems }

| Cosa vedi | Perché | Cosa fare |
| --- | --- | --- |
| `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)` | `backup create --encrypt` senza un terminale su cui chiedere, come in cron | Fornisci la password con `--password-file` o `--password-stdin` ([Dalla riga di comando](backup_restore.md#command-line)) |
| `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: …)`, o in Impostazioni › Amministrazione › Backup *La password non soddisfa le regole previste per la password di un backup.* | Le regole sono elencate dopo `password_too_weak:`. In Impostazioni **Crea backup** resta disabilitato finché ogni regola non è rispettata; se le regole di un backup non sono arrivate dal server (`GET /api/v1/backup/instance/options`), l'indicatore applica quelle della password di un account (8 caratteri), e il server rifiuta comunque meno di 12 | Scegli una password più lunga che rispetti ogni regola. Non è stato scritto nulla |
| `❌ The two passwords differ (password_mismatch)` | La seconda password digitata al terminale non è la prima | Esegui di nuovo il comando |
| `❌ password file: <path> does not exist (password_unreadable)`, o `cannot be read`, `is empty or blank`, `is not UTF-8 text` | `--password-file` non riesce a fornire la password | Correggi il file: solo la password, in UTF-8. Con Docker, il percorso all'interno del container, come `/run/secrets/backup_password` |
| `⚠️ The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore`, o in Impostazioni › Amministrazione › Backup *La chiave dell'istanza non può essere usata: il backup è stato creato senza di essa, quindi le chiavi dei provider di dati devono essere inserite di nuovo dopo un ripristino.* | `secrets/instance.key` c'è, ma è danneggiata o irraggiungibile, oppure supera i 4096 byte che un ripristino riesce a rileggere (la chiave generata da LibreFolio ha 43 caratteri). Il backup è completo, senza la chiave | Se il log di avvio dice cosa non va nella chiave, correggilo («Controlli all'avvio» in [Variabili d'ambiente](configuration.md)), poi crea un nuovo backup sicuro. Se non dice nulla, la chiave è troppo lunga per essere trasportata: conserva una copia di `secrets/` insieme al backup, come per un backup in chiaro |

### 🧾 Il controllo rifiuta l'archivio {: #check-refused }

`backup restore`, con o senza `--dry-run`, termina con un rifiuto e il suo codice tra parentesi, senza cambiare nulla. Impostazioni › Amministrazione › Backup rifiuta gli stessi archivi e indica il motivo sulla scheda, senza il codice: *L'archivio è danneggiato.* per `archive_damaged`, per esempio.

| Codice | Perché | Cosa fare |
| --- | --- | --- |
| `revision_unknown` | L'archivio proviene da un LibreFolio più recente | Aggiorna questa installazione ([Mai all'indietro](#never-backwards)), poi esegui di nuovo il comando |
| `manifest_newer_format` | Il formato dell'archivio è più recente di quello che questo LibreFolio legge | Aggiorna prima LibreFolio |
| `checksum_mismatch`, `archive_damaged`, `missing_entry` | L'archivio è danneggiato, troncato o modificato | `backup inspect` indica le voci che differiscono. Copia di nuovo l'archivio da dove lo conservi, o usane un altro |
| `database_damaged` | Il database non supera il controllo di integrità di SQLite, SQLite non ne legge lo schema, oppure contiene testo non UTF-8. Impostazioni › Amministrazione › Backup: *Il database del backup è danneggiato: non può essere ripristinato.* | Copia di nuovo l'archivio da dove lo conservi, o usane un altro. Testo non UTF-8 significa che un altro programma ha scritto nel database (LibreFolio non lo scrive mai), oppure che l'archivio è stato modificato |
| `database_foreign_objects` | Il database contiene un trigger, una vista o una tabella virtuale, che LibreFolio non crea mai. Impostazioni › Amministrazione › Backup: *Il database del backup contiene trigger, viste o altri oggetti che LibreFolio non crea mai: non è stato creato da LibreFolio, o è stato modificato, e non può essere ripristinato.* | L'archivio non è stato creato da LibreFolio, o è stato modificato dopo: usa un altro backup |
| `not_a_backup` | Non è un archivio scritto da LibreFolio, come una cartella dati compressa a mano | Rimetti una tale copia [a mano](#by-hand), in una cartella dati vuota |
| `sealed_backup_needs_key` | Un backup notturno sigillato (`.tar`): la sua password è all'interno, cifrata per una chiave che il controllo non ha. Impostazioni › Amministrazione › Backup: *Questo è un backup sigillato di un pannello di hosting: la sua password è cifrata per la chiave del provider. Estrai backup.lfbk, apri password.age con age, poi ripristina backup.lfbk con quella password.* | Ripristinalo dove si trova la sua chiave privata: `backup restore <archive>.tar --identity-file <key file>` ([Backup sigillati](backup_sealed.md#sealed)) |
| `sealed_no_identity`, `sealed_identity_invalid`, `sealed_tar_invalid`, `sealed_manifest_invalid`, `sealed_password_invalid` | Un [backup sigillato](backup_sealed.md#sealed) fornito con `--identity-file` che non si apre | Vedi [Creare o aprire un backup sigillato](#sealed-problems) |
| `no_space` | La copia richiede più spazio libero di quanto ne abbia il disco della cartella dati | Libera spazio: l'archivio decompresso, più il doppio del suo database, più 64 MB, e per un backup sicuro anche la dimensione del suo `.lfbk` |
| `archive_unreadable` | L'archivio non può essere aperto, molto spesso perché l'utente del server non può leggerlo | Con Docker e l'immagine ufficiale, `sudo chown 1000:1000 <archive>` sull'host lo assegna a quell'utente |
| `restore_already_pending` | Un altro ripristino attende il prossimo avvio | Riavvia LibreFolio per applicarlo, oppure annullalo con `backup pending --cancel` o **Annulla il ripristino** in Impostazioni › Amministrazione › Backup |
| `wrong_password` | La password non apre il backup sicuro: non è quella con cui è stato creato, oppure l'inizio del file è stato modificato. Impostazioni › Amministrazione › Backup la chiede di nuovo: *Password errata, o il file è stato modificato: digita di nuovo la password.* | Digitala di nuovo così com'è stata scelta, maiuscole e minuscole incluse. Se è corretta, copia di nuovo il file da dove lo conservi |
| `password_required` | Un backup sicuro, e nessuna password: il comando non aveva un terminale su cui chiedere, né `--password-file` né `--password-stdin` | Esegui il comando in un terminale, o fornisci la password con una delle due opzioni |
| `envelope_damaged` | Il backup sicuro è danneggiato, troncato, o modificato dopo essere stato creato | Copialo di nuovo da dove lo conservi, o usane un altro: LibreFolio non legge alcuna parte di un `.lfbk` danneggiato |
| `envelope_unsupported` | Il backup sicuro proviene da un LibreFolio più recente, o richiede impostazioni che questo non accetta | Aggiorna prima questa installazione ([Mai all'indietro](#never-backwards)), poi esegui di nuovo il comando |

Altri due messaggi:

- `❌ No file at <path>`: con Docker, fornisci il percorso all'interno del container, `/app/backend/data/prod-docker/…`.
- `❌ The backup has no active administrator: after a restore nobody could manage the instance`, o lo stesso nel report di Impostazioni › Amministrazione › Backup, la cui conferma resta disabilitata: sull'installazione da cui proviene il backup, rendi amministratore un account attivo, poi crea un nuovo backup.

Ogni codice: «Rifiuti — cosa significano i codici» in [Strumenti di amministrazione CLI](cli_tools.md).

Due avvisi lasciano proseguire il ripristino, ma leggili prima di confermare:

- 🔑 *Il tuo account non è tra gli amministratori di questo backup: dopo il riavvio non puoi accedere con esso.* Solo nel report di Impostazioni › Amministrazione › Backup, in rosso. Dopo il ripristino accedi con un account del backup, con la password che aveva allora: l'account che usi ora non vi è compreso. Prima di confermare, assicurati di conoscere la password di uno degli amministratori indicati dal report; se non la conosci, usa un altro backup.
- `⚠️ Ledger totals differ from the backup's (<n> lines):`, o *I totali del libro mastro differiscono da quelli del backup su 2 righe:* nel report di Impostazioni › Amministrazione › Backup: la liquidità di un broker o la quantità di una posizione nella copia, una volta aggiornata, non è quella registrata dal backup, perché delle transazioni sono state perse, aggiunte o modificate tra i due (per esempio da una migrazione che corregge i dati). Ogni riga che segue indica un numero di broker, poi un numero di valuta o di asset, con l'importo del backup prima della freccia e quello della copia dopo: i numeri sono quelli degli indirizzi `/brokers/<id>` e `/assets/<id>` nell'app. Confronta queste righe con l'istanza da cui proviene il backup. L'avviso non blocca mai il ripristino: sta a te decidere se confermare.

### 🔏 Creare o aprire un backup sigillato {: #sealed-problems }

Per crearne uno, con `backup create --sealed` o `--recipient`: non viene scritto nulla e il comando termina con `1`.

| Cosa vedi | Perché | Cosa fare |
| --- | --- | --- |
| `❌ LIBREFOLIO_BACKUP_RECIPIENTS is not set: give the recipients there, or with --recipient age1…` | `--sealed` non ha trovato la variabile: non è in `.env`, o il container non è stato ricreato dopo che è stata aggiunta | Impostala ([Sigilla ogni backup](backup_sealed.md#sealed-recipients)), poi `docker compose up -d`, oppure esegui il comando dalla cartella del progetto con `pipenv run`, che legge `.env` |
| `❌ LIBREFOLIO_BACKUP_RECIPIENTS: item 2 is not an age recipient: expected age1… as age-keygen prints it (BACKUP_RECIPIENTS_INVALID)`, o `expected at most 2 recipients, comma-separated (BACKUP_RECIPIENTS_TOO_MANY)`, o `item 2 repeats an earlier recipient (BACKUP_RECIPIENTS_DUPLICATE)` | La variabile contiene qualcosa di diverso da una o due chiavi `age1…` distinte: una chiave privata, una chiave SSH, una virgola di troppo | Scrivi solo le chiavi pubbliche, come le stampano `keygen` o `age-keygen -y`. La scheda **Sicurezza** dice lo stesso (`backup.recipients`) |
| `❌ A --recipient is not an age recipient: expected age1…, as keygen or age-keygen prints it`, `❌ The same recipient is given twice`, `❌ At most 2 recipients: --recipient twice, while a key is being changed` | Le stesse regole, per `--recipient` | Fornisci una o due chiavi pubbliche diverse |
| `❌ A sealed backup draws a password of its own: --sealed and --recipient go without --encrypt, --password-file or --password-stdin` | Un backup sigillato non ha una password da fornire | Ometti le opzioni della password |
| `❌ --sealed reads the recipients from LIBREFOLIO_BACKUP_RECIPIENTS: give them there or with --recipient, not both` | `--sealed` e `--recipient` insieme | Tieni uno dei due |
| `❌ <path> already exists: a key file is never written over` | `backup keygen` non sostituisce mai una chiave: la vecchia potrebbe ancora aprire backup | Scegli un altro nome di file, oppure sposta prima il vecchio file se sei sicuro che nessun backup ne abbia bisogno |

Per aprirne uno, con `--identity-file`: il comando non cambia nulla e termina con `1`. Legge prima il file della chiave, poi il `.tar`.

| Cosa vedi | Perché | Cosa fare |
| --- | --- | --- |
| `(sealed_backup_needs_key)` | Un `.tar` fornito senza `--identity-file`, sulla riga di comando o in Impostazioni › Amministrazione › Backup | Fornisci il file della chiave, oppure [aprilo a mano](backup_sealed.md#sealed-by-hand) e ripristina `backup.lfbk` con la sua password |
| `❌ --identity-file opens a sealed backup (.tar) only: <path> is not one` | Un `.zip` o un `.lfbk` fornito con `--identity-file` | Ometti `--identity-file`: quegli archivi si aprono come al solito |
| `❌ The key file cannot be read (sealed_identity_invalid)`, `Line 3 of the key file is not an age key`, `The key file holds no age key` | Il file non è una chiave privata: solo la chiave pubblica, una chiave copiata con un carattere mancante, o un file che il comando non può leggere | Fornisci il file scritto da `keygen` o `age-keygen`, con la sua riga `AGE-SECRET-KEY-1…`. I commenti (`#`) e le righe vuote possono restare |
| `❌ None of the keys given opens the password of this backup (sealed_no_identity)` | Il backup è stato sigillato per un'altra chiave: una più vecchia, prima di un [cambio di chiave](backup_sealed.md#sealed-rotation) | Confronta i suoi `recipients` (`tar xOf <archive>.tar manifest.json`) con la riga `# public key:` dei tuoi file di chiave, e fornisci quella corrispondente |
| `(sealed_tar_invalid)`, come `The archive is cut short` o `The archive does not hold manifest.json, password.age and backup.lfbk, in this order` | Non è il `.tar` che LibreFolio ha scritto: troncato da una copia, ricostruito a mano con `tar cf`, o non è un backup sigillato | Copia di nuovo l'originale da dove lo conservi, o usa il backup di un'altra notte |
| `(sealed_manifest_invalid)`, come `The manifest does not describe backup.lfbk: its size or SHA-256 differs` | `manifest.json` o `backup.lfbk` è stato modificato | La copia è danneggiata: usane un'altra |
| `(sealed_password_invalid)` | La chiave ha aperto `password.age`, ma ciò che contiene non è una password scritta da LibreFolio | Non è un backup di LibreFolio, o è stato modificato: usa un'altra copia |
| `❌ The password does not open this backup (wrong_password)` | La chiave ha aperto la password, ma quella password non apre `backup.lfbk`: i due file provengono da backup diversi, o uno è stato modificato | Usa un'altra copia, conservata integra come LibreFolio l'ha scritta |
| `(envelope_damaged)`, durante il controllo o il ripristino | Un byte di `backup.lfbk` è stato modificato dopo la creazione del backup: la password era corretta | Usa un'altra copia: LibreFolio non legge alcuna parte di un `.lfbk` danneggiato |

### 🔁 Il ripristino non va a buon fine {: #restart-problems }

| Cosa vedi | Perché | Cosa fare |
| --- | --- | --- |
| `backup pending` dice `The state of the restore cannot be read`, `(restore_state_unreadable: <reason>)` | `.restore/restore.json` non può essere usato: permessi (`io`), un link o una cartella al suo posto (`not_a_file`), o contenuto non scritto da LibreFolio (`invalid`). Un ripristino potrebbe essersi fermato a metà. Nel frattempo nessuna copia controllata viene rimossa | Per `io`, restituisci `.restore/` all'utente che esegue LibreFolio e controlla di nuovo. Altrimenti ferma LibreFolio ed esegui `backup pending --recover previous`: i dati precedenti tornano da `.restore/previous/`. Poi avvialo, o ripristina di nuovo un backup («Uno stato di ripristino illeggibile» in [Strumenti di amministrazione CLI](cli_tools.md)) |
| `backup pending` termina con `(server_running)` | All'ultimo avvio, un altro processo server serviva la cartella dati: un worker riavviato da solo, o un secondo server | Riavvia l'intero server, mai un singolo worker, ed esegui un solo server per cartella dati |
| `backup pending` termina con `(other_data_directory)` | Il server ha trovato la propria cartella dati sotto un percorso diverso da quello per cui il ripristino è stato confermato, come una copia della cartella dati | `backup pending --cancel`, o **Annulla il ripristino** in Impostazioni › Amministrazione › Backup, poi ripristina di nuovo l'archivio: con `backup restore`, dove è in esecuzione il server |
| `backup pending` termina con `(backup_running)` | Un backup era in esecuzione all'ultimo avvio | Nulla: il prossimo avvio applica il ripristino |
| `backup pending` dice che il ripristino è stato riportato allo stato precedente, `(first_start_failed)` | Il primo avvio sui dati ripristinati non è stato completato | I dati sono come prima. Il log di quell'avvio contiene la causa: correggila, poi ripristina di nuovo l'archivio |
| … riportato allo stato precedente, `(swap_interrupted)` | L'avvio che aveva applicato il ripristino è stato interrotto, e quello successivo l'ha annullato | Ripristina di nuovo l'archivio |
| … riportato allo stato precedente, `(swap_failed)` | Non è stato possibile spostare le cartelle al loro posto | Rendi `sqlite/`, `custom-uploads/`, `broker_reports/` e `scenario_catalog/` cartelle reali della cartella dati, né link né mount separati, poi ripristina di nuovo l'archivio |
| … riportato allo stato precedente, `(stage_missing)` | La copia controllata era sparita o modificata | Ripristina di nuovo l'archivio |
| Un avvio si ferma e il suo log dice che un altro server ha applicato il ripristino o serve la cartella dati | Due server LibreFolio usano la stessa cartella dati | Ferma l'altro, poi avvia di nuovo LibreFolio: `backup pending` dirà se il ripristino è stato mantenuto |
| LibreFolio non si avvia e il suo log contiene `The data directory is half restored` | Anche il ripristino dei dati precedenti è fallito, per esempio per un errore del disco o dei permessi | Correggi la causa indicata dal log: ogni avvio riprova |
| `Failed to apply database migrations` dopo una decompressione a mano | Un archivio da un LibreFolio più recente, o una migrazione che fallisce: il log contiene l'errore | Per un archivio più recente, `docker compose down`, poi usa la versione che l'ha creato o una più recente ([Mai all'indietro](#never-backwards)) |

### 🖱️ Cosa dice Impostazioni › Amministrazione › Backup {: #restore-settings-problems }

La finestra del riavvio dà a parole il motivo che `backup pending` dà come codice: la tabella dice quale, e la riga di quel codice in [Il ripristino non va a buon fine](#restart-problems) dice cosa fare. Sulla scheda, **Riprova** rilegge lo stato del ripristino; per inviare di nuovo un archivio, sceglilo di nuovo.

| Cosa vedi | Perché | Cosa fare |
| --- | --- | --- |
| Dopo **Ripristina e riavvia**, la pagina di accesso, senza alcun messaggio | Il ripristino ha funzionato e ha terminato ogni sessione. Solo nel caso della riga successiva la pagina di accesso compare anche se il ripristino non è andato a buon fine | Accedi con un amministratore del backup, con la password che l'account aveva quando è stato creato il backup. Se nessuno la ricorda: [Dopo un ripristino](#after-restore) |
| La pagina di accesso è comparsa, ma dopo l'accesso i dati sono come prima | La pagina non ha letto l'esito con il proprio ticket (ricaricamento della pagina, più di un'ora di attesa, o LibreFolio riavviato dalla riga di comando invece che dalla pagina), e LibreFolio gira senza `JWT_SECRET` ([Mantenere gli utenti connessi dopo un riavvio](index.md#session-persistence)): ogni avvio disconnette tutti, anche se il ripristino non è andato a buon fine. Gli account e le password di prima consentono ancora l'accesso | Apri **Impostazioni › Amministrazione › Backup**: la scheda dice *L'ultimo ripristino è stato riportato allo stato precedente in data …*, oppure mostra il ripristino in attesa, con il motivo; poi vedi la riga di quel motivo qui sotto |
| *LibreFolio non è ancora tornato. Se nulla lo avvia di nuovo da solo, avvialo tu: il ripristino viene applicato a quell'avvio.* | LibreFolio non risponde da un minuto: nulla lo ha riavviato (nessun supervisore, o uno che lo avvia solo dopo un errore, [Chi riavvia LibreFolio](backup_restore.md#supervisors)), oppure il suo avvio è lento | Se è fermo, avvialo: `docker compose up -d` con Docker, o [avvia il server](cli_tools.md#start-the-server) su un'installazione host. La pagina prosegue da sola una volta che LibreFolio risponde |
| *LibreFolio non si è fermato. Se non si riavvia da solo, riavvialo tu: il ripristino viene applicato a quell'avvio.*, un minuto dopo **Ripristina e riavvia**, con **Torna a Backup** | La richiesta non ha fermato il server: il ripristino attende ancora il prossimo avvio, e `backup pending` lo mostra in attesa | Riavvia LibreFolio tu: `docker compose restart librefolio` con Docker, oppure ferma l'intero server e [avvialo](cli_tools.md#start-the-server) di nuovo. Il suo avvio applica il ripristino, e la pagina prosegue da sola. Oppure **Torna a Backup**: la scheda mostra il ripristino in attesa, da riavviare (**Riavvia ora e ripristina**) o annullare (**Annulla il ripristino**) |
| **Il ripristino non è andato a buon fine**, con *I dati sono come prima: …* | Il ripristino è stato riportato allo stato precedente: *il primo avvio successivo non è stato completato* (`first_start_failed`), *l'avvio che lo ha applicato è stato interrotto* (`swap_interrupted`), *non è stato possibile spostare le sue cartelle al loro posto* (`swap_failed`) o *la sua copia controllata era sparita* (`stage_missing`) | Quanto dice la riga di quel codice. **Torna a Backup** riporta alla scheda, che dice quando l'ultimo ripristino è stato riportato allo stato precedente e perché |
| **Il ripristino non è andato a buon fine**, con *LibreFolio è stato riavviato, ma il ripristino non è stato applicato.* e il motivo | Un avvio ha lasciato il ripristino in attesa: *All'ultimo avvio era in esecuzione un backup…* (`backup_running`), *È stato confermato per un'altra cartella dati…* (`other_data_directory`) o *All'ultimo avvio un altro processo LibreFolio stava servendo i dati…* (`server_running`) | Quanto dice la riga di quel codice. **Torna a Backup** mostra il ripristino in attesa, con **Riavvia ora e ripristina** e **Annulla il ripristino** |
| *L'archivio è più grande di quanto questo LibreFolio accetti (500 MB).* | L'installazione limita gli archivi caricati per un ripristino con `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` (`backup_too_large`) | Non c'è alcun limite a meno che qualcuno non ne abbia impostato uno: aumentalo, oppure impostalo a `0`, poi riavvia ([Il limite di caricamento di un ripristino](backup_restore.md#restore-upload-limit)). Oppure ripristina dalla riga di comando, che non ha limiti di caricamento |
| *Una volta decompresso, l'archivio è più grande di quanto questo LibreFolio accetti per un ripristino.* | Le dimensioni dichiarate dal manifest, sommate, superano `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` (`unpacked_too_large`). Il controllo ha rifiutato l'archivio prima di decomprimere qualsiasi cosa | Non c'è alcun limite a meno che qualcuno non ne abbia impostato uno: aumentalo, impostalo a `0` o rimuovilo, poi riavvia ([Il limite di caricamento di un ripristino](backup_restore.md#restore-upload-limit)). Oppure ripristina dalla riga di comando con `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` davanti a `backup restore` |
| *LibreFolio non riesce a leggere il proprio limite di ripristino in questo momento: riprova più tardi.* | `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` non è un numero intero di megabyte (`backup_restore_unavailable`): non parte alcun controllo, e l'archivio resta sul server. Il log contiene un errore, già dall'avvio | Scrivi un numero intero di megabyte, `0` per nessun limite, oppure rimuovi la variabile, poi riavvia; la scheda **Sicurezza** di Impostazioni › Amministrazione la nomina (`backup.restore_limit`). Poi scegli di nuovo l'archivio |
| L'invio si interrompe con *Un proxy davanti a LibreFolio ha rifiutato un archivio di queste dimensioni: chiedi a chi lo gestisce di accettare caricamenti più grandi, oppure ripristina dalla riga di comando.*, oppure con *Il server non risponde: controlla la connessione e riprova.* o *Il server ha risposto con un errore: il log del server ne contiene la causa.*, e il log di LibreFolio non ne riporta nulla | Un proxy davanti a LibreFolio ha rifiutato l'archivio: Nginx accetta solo 1 MB per impostazione predefinita. Il primo messaggio: il proxy risponde *troppo grande* (HTTP 413); gli altri: interrompe la connessione o risponde in altro modo | Consenti al proxy di accettare archivi grandi quanto i tuoi, con `client_max_body_size` in Nginx ([Il limite di caricamento di un ripristino](backup_restore.md#restore-upload-limit)), oppure ripristina dalla riga di comando |
| *Spazio libero insufficiente sul server per questo archivio.* | Il disco della cartella dati, o una quota, è pieno (`backup_no_space`): durante l'invio, e allora dell'archivio non resta nulla (un file system di rete o una quota può segnalarlo solo alla fine del file), oppure alla conferma con **Ripristina e riavvia**, e allora nulla è confermato e la copia controllata resta; il log contiene `A restore could not be confirmed: not enough free space` | Libera spazio sul disco della cartella dati, poi scegli di nuovo l'archivio. Dopo una conferma, **Riprova**: il report torna, e **Ripristina e riavvia** conferma di nuovo |
| *Spazio libero insufficiente sul server per controllare l'archivio.* | Il disco della cartella dati, o una quota, è pieno quando inizia il controllo, e allora l'archivio resta sul server, oppure mentre il controllo crea la sua copia (`no_space`) | Libera spazio, quanto dice la riga `no_space` di [Il controllo rifiuta l'archivio](#check-refused), poi scegli di nuovo l'archivio |
| *Non è stato possibile scrivere la copia: il log del server ne contiene la causa.* | Il controllo non è partito, o non ha scritto la sua copia, per un motivo diverso dallo spazio (`stage_failed`): proprietario o permessi di una cartella di `.restore/`, disco in sola lettura, errore del disco. Il log contiene `A check of a backup archive could not start`, con l'errore e il motivo di sistema | Correggi ciò che la riga del log indica, per esempio restituendo `.restore/` all'utente che esegue LibreFolio, poi scegli di nuovo l'archivio |
| *Spazio libero insufficiente sul server per il backup.*, sulla scheda **Esegui il backup dell'istanza** | Il disco della cartella dati, o una quota, è pieno (`backup_no_space`), all'avvio del backup o durante: il backup viene creato in `backups/`, su quel disco | Libera spazio su quel disco, poi **Riprova**. Quanto spazio richiede un backup: «Creare un archivio» in [Strumenti di amministrazione CLI](cli_tools.md) |
| *Non è stato possibile confermare il ripristino: il log del server ne contiene la causa. Nulla è cambiato.*, dopo **Ripristina e riavvia** | La conferma non è stata scritta, per un motivo diverso dallo spazio (`restore_confirm_failed`): proprietario o permessi di `.restore/`, disco in sola lettura, errore del disco. Il log contiene `A restore could not be confirmed`, con l'errore e il motivo di sistema. Nulla è confermato, e la copia controllata resta | Correggi ciò che la riga del log indica, per esempio restituendo `.restore/` all'utente che esegue LibreFolio, poi **Riprova**: il report torna, e **Ripristina e riavvia** conferma di nuovo |
| *Non è stato possibile annullare il ripristino: il log del server ne contiene la causa. Attende ancora il prossimo avvio.*, dopo **Annulla il ripristino**: la scheda mostra ancora il ripristino in attesa, con **Riavvia ora e ripristina** e **Annulla il ripristino** | Il suo stato in `.restore/` non si è potuto bloccare o rimuovere (`restore_cancel_failed`): proprietario o permessi, disco in sola lettura, errore del disco. Il log contiene `A pending restore could not be cancelled`, con l'errore e il motivo di sistema. Una copia che non si può rimuovere dopo l'annullamento non è un errore di questo tipo: il ripristino è annullato, e il log contiene l'avviso `The copy of a cancelled restore could not be removed: it goes when its check expires` | Correggi ciò che la riga del log indica, poi **Annulla il ripristino** di nuovo, sulla stessa scheda: finché non è annullato, il prossimo avvio di LibreFolio applica il ripristino. Una copia lasciata viene rimossa al primo avvio di LibreFolio dopo che il suo controllo ha 24 ore |
| *Non è stato possibile riavviare LibreFolio: il log del server ne contiene la causa. Il ripristino attende ancora il prossimo avvio.*, dopo **Ripristina e riavvia** o **Riavvia ora e ripristina** | LibreFolio non è stato fermato: il ticket con cui la pagina legge l'esito non è stato scritto (`restore_restart_failed`), per un disco pieno o per proprietario o permessi di `.restore/`. Il log contiene `The ticket of the restore's outcome could not be written: no restart`. Il ripristino è confermato, e attende | Correggi ciò che la riga del log indica, poi **Riavvia ora e ripristina**, che la scheda mostra con il ripristino in attesa. Oppure riavvia LibreFolio tu, `docker compose restart librefolio` con Docker: il suo avvio applica il ripristino |
| *Non è possibile leggere lo stato del ripristino: il log del server ne contiene la causa. Un ripristino potrebbe ancora attendere il prossimo avvio.* | Lo stato del ripristino in `.restore/` non si può leggere (`restore_state_unreadable`): proprietario o permessi, come file scritti da `root`, o un errore del disco. Non si sa se un ripristino sia in attesa: confermare un altro ripristino viene rifiutato, e un avvio che non legge lo stato lo lascia com'è e non applica nulla | Restituisci `.restore/` e i suoi file all'utente che esegue LibreFolio, leggibili da esso, poi **Riprova**. Con Docker, ogni avvio del container restituisce la cartella dati a quell'utente prima che LibreFolio legga lo stato, quindi un ripristino in attesa viene applicato a quell'avvio; i permessi modificati con `chmod` restano come sono. `backup pending` dice lo stesso, con il motivo di sistema |
| La scheda rifiuta l'archivio, per esempio *Questo file non è un backup di LibreFolio.*, *L'archivio è danneggiato.* o *Il backup sicuro è danneggiato o è stato modificato: non può essere aperto.* | Il controllo lo ha rifiutato, come fa `backup restore` | Vedi il suo codice in [Il controllo rifiuta l'archivio](#check-refused) |
| La scheda chiede di nuovo la password di un backup sicuro: *Password errata, o il file è stato modificato: digita di nuovo la password.* | La password non apre il backup (`wrong_password`) | Digitala di nuovo: l'archivio resta sul server e non viene inviato di nuovo. Se la password è corretta, il file è stato modificato: **Annulla**, poi scegli una buona copia con **Scegli un archivio…** |

### 🔑 Dopo un ripristino {: #after-restore }

| Cosa succede | Cosa fare |
| --- | --- |
| Nessuno ricorda la password che un amministratore aveva nel backup | Chi gestisce il server ne imposta una nuova con `user reset`, o crea un link di reimpostazione con `user reset-link` ([Reimpostare una password o bloccare un account](cli_tools.md#reset-a-password-or-lock-an-account)) |
| La pagina di accesso risponde che un account è disabilitato: era in attesa della verifica dell'email | Un amministratore fa clic su **Riattiva** sulla sua riga ([Cosa fa ogni azione](users.md#actions)), oppure lo elimina così che il suo proprietario si registri di nuovo ([Eliminare un account](users.md#delete)) |
| Un link inviato prima del ripristino non funziona più | Invia un nuovo invito o un nuovo link di reimpostazione della password ([Utenti e inviti](users.md)) |
| Un'impostazione segreta di un plugin è segnalata come impostata ma illeggibile, come annunciato dal report del controllo (*… non può essere letta con la chiave di questa istanza: inserisci di nuovo i relativi valori dopo il ripristino.*) | Il backup non aveva una chiave in grado di leggerla: un backup in chiaro, o uno sicuro la cui istanza aveva una chiave impostata nel proprio ambiente, o non riusciva a usare la propria. Se hai ancora la vecchia chiave, rimettila al suo posto prima che qualcuno inserisca di nuovo un segreto; solo in caso contrario inserisci di nuovo l'impostazione in **Impostazioni › Plugin**, dove ogni utente inserisce la propria ([Cosa segue](backup_restore.md#what-follows)). Se il log di avvio dice che la chiave di questa installazione non può essere usata, correggi prima quello («Controlli all'avvio» in [Variabili d'ambiente](configuration.md)) |
| Dopo uno spostamento, non viene inviata alcuna email | Imposta le variabili email su questa installazione, poi riavvia ([Email](email.md)) |

---

## 🔗 Correlati

- 📄 **[Backup, ripristino e spostamento dell'istanza](backup_restore.md)** — Cosa contiene un backup, Creare un backup, Backup sicuri, …
- 📄 **[Backup: backup sigillati](backup_sealed.md)** — Backup sigillati: una chiave invece di una password
