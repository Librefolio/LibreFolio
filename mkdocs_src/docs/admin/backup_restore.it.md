# 💾 Backup, ripristino e spostamento della tua istanza

Un backup è un unico archivio che contiene tutto il tuo LibreFolio: il database e i file di ogni utente, in un semplice zip o, per un [backup sicuro](#secure), cifrato con una password scelta da te. Questa pagina racconta tutta la storia: cosa contiene l'archivio, come crearne e controllarne uno, come proteggerlo con una password, come ripristinarlo e come spostare LibreFolio da un'istanza che qualcuno ospita per te al tuo server, o viceversa. Ogni opzione e messaggio dei comandi si trova in «Eseguire il backup dell'istanza», in [Strumenti di amministrazione CLI](cli_tools.md).

!!! tip "🗓️ Creane uno prima di ogni aggiornamento"

    LibreFolio non riporta mai un database a una versione precedente. Un backup creato prima di un aggiornamento è la tua via di ritorno alla versione che avevi: vedi [Aggiornare LibreFolio](../user/installation.md#updating).

!!! info "📚 Questa guida è su più pagine"

    Oltre a questa pagina: [Backup: backup sigillati](backup_sealed.md), [Backup: spostamento e risoluzione dei problemi](backup_moving.md).

---

## 📦 Cosa contiene un backup {: #contents }

L'archivio è uno zip con la struttura della [directory dei dati](filesystem.md): decompresso in una directory dei dati vuota, è di nuovo la tua istanza. Un [backup sicuro](#secure) è lo stesso zip, cifrato con una password in un file `.lfbk`, e un [backup sigillato](backup_sealed.md#sealed) è un backup sicuro la cui password può essere aperta solo da una tua chiave privata, in un `.tar`.

| Nell'archivio | Di cosa si tratta |
| --- | --- |
| `sqlite/app.db` | Il database: utenti, broker, transazioni, asset, prezzi, tassi di cambio e impostazioni. Una copia coerente, creata mentre LibreFolio continua a funzionare |
| `custom-uploads/` | I file caricati nell'app |
| `broker_reports/` | I report dei broker |
| `scenario_catalog/` | I tuoi scenari di stress, se ne hai aggiunti |
| `secrets/instance.key` | Solo in un [backup sicuro](#secure), e solo quando LibreFolio ha generato la chiave dell'istanza: la chiave che ha cifrato le chiavi salvate dei provider di dati, così che viaggino con i dati. Un ripristino la legge soltanto: l'installazione che riceve il backup conserva la propria chiave |
| `manifest.json` | La descrizione dell'archivio: la versione di LibreFolio che lo ha creato e quando, la revisione di migrazione del database, le sue righe per tabella, i totali di controllo del libro mastro (la liquidità di ogni broker in ciascuna valuta e la quantità di ogni posizione), la dimensione e il checksum SHA-256 di ogni file, e se l'archivio porta la chiave dell'istanza |

Mai nell'archivio:

- 🔑 `secrets/`, che contiene la chiave dell'istanza: un [backup sicuro](#secure) porta solo la chiave generata da LibreFolio, `secrets/instance.key`, mai una chiave impostata da te con `LIBREFOLIO_INSTANCE_KEY` o `LIBREFOLIO_INSTANCE_KEY_FILE`. Vedi «La chiave dell'istanza» in [Variabili d'ambiente](configuration.md);
- 📝 `logs/`, e `scheduler_state.json`, l'ultima esecuzione delle sincronizzazioni pianificate;
- 💾 `backups/`, dove LibreFolio [conserva i backup che crea](#kept-backups), e `.restore/`, la cartella di lavoro di un ripristino;
- ⚙️ la configurazione: `.env` e le variabili d'ambiente, comprese le impostazioni [email](email.md), che LibreFolio conserva solo nell'ambiente.

### 🧭 Cosa segue {: #what-follows }

- 🔒 **Tienilo privato.** Un archivio in chiaro contiene i dati di ogni utente e non è cifrato: conservalo, insieme a ogni copia, con la stessa riservatezza del server stesso. Uno [sicuro](#secure) si apre solo con la sua password: tieni la password separata dall'archivio.
- 🗝️ **Segreti salvati e chiave dell'istanza.** Ciò che LibreFolio ha cifrato con la chiave dell'istanza, come la chiave API di un'origine dati salvata nell'app, può essere letto solo con quella chiave.
    - Un [backup sicuro](#secure) porta la chiave generata da LibreFolio: il suo ripristino ricifra quei segreti con la chiave dell'installazione che lo riceve, e non c'è nulla da fare.
    - Un backup in chiaro lascia fuori la chiave; lo stesso fa sempre un backup [sigillato](backup_sealed.md#sealed), e così pure un backup sicuro la cui chiave proviene dall'ambiente (`LIBREFOLIO_INSTANCE_KEY`, `LIBREFOLIO_INSTANCE_KEY_FILE`) o non è stata utilizzabile. Su un'installazione con un'altra chiave, LibreFolio conserva quei segreti, li segnala come non leggibili e non usa mai un valore errato: **Impostazioni › Plugin** indica sotto ciascuno *Salvato, ma la chiave di questa istanza non può leggerlo: inseriscilo di nuovo.* Se hai ancora la vecchia chiave, rimettila per prima cosa, prima che qualcuno inserisca di nuovo un segreto: ferma LibreFolio, metti la tua copia di `secrets/instance.key` al posto di quella generata, oppure imposta il vecchio valore della variabile, e avvialo di nuovo («La chiave dell'istanza» in [Variabili d'ambiente](configuration.md)). Un'installazione che conserva la propria chiave, o una in cui i segreti sono già cifrati con la sua chiave, accetta invece la vecchia chiave al ripristino: ripristina dalla riga di comando con `--instance-key-file` e la tua copia della vecchia chiave, e il controllo ricifra quei segreti con la chiave di questa installazione («La chiave dell'istanza di un'altra installazione» in [Strumenti di amministrazione CLI](cli_tools.md)). Inserisci di nuovo i segreti solo se la vecchia chiave è perduta: un segreto inserito con la nuova chiave diventerebbe illeggibile una volta ripristinata quella vecchia.
    - Per le impostazioni dell'intera istanza, ogni avvio registra anche l'errore *Segreti dei plugin memorizzati che la chiave dell'istanza non può leggere: …* con il loro numero, finché non vengono inseriti di nuovo o non torna la vecchia chiave. Nessun plugin distribuito con LibreFolio ne conserva uno oggi.
- ⚙️ **Porta con te la configurazione.** Conserva una copia del tuo `.env` insieme agli archivi: su un'altra installazione, imposta di nuovo le opzioni che ti servono, comprese quelle email ([Dove risiede la configurazione](email.md#where-it-lives)).
- 🏠 **Qualsiasi installazione può accettarlo**, se esegue la stessa versione di LibreFolio o una più recente, chiunque abbia creato l'archivio: Impostazioni o la riga di comando.

---

## ⬇️ Creare un backup {: #create }

Tre modi producono lo stesso archivio:

- **Impostazioni › Amministrazione › Backup**, nell'app: l'archivio viene scaricato sul tuo computer. Per gli amministratori.
- **La riga di comando**, sul server: `backup create`.

Da Impostazioni e dalla riga di comando, il backup può anche essere [sicuro](#secure): lo stesso zip, cifrato con una password scelta da te. Dalla riga di comando può anche essere [sigillato](backup_sealed.md#sealed): cifrato con una password casuale che solo una tua chiave privata apre, per i backup creati senza nessuno alla tastiera.

In ogni caso LibreFolio continua a funzionare durante il backup, e viene eseguito un backup alla volta, chiunque lo abbia avviato.

### 🖱️ Da Impostazioni › Amministrazione › Backup {: #settings-backup }

1. Apri **Impostazioni › Amministrazione › Backup**: solo gli amministratori hanno questa scheda.
2. In **Esegui il backup dell'istanza**, scegli il tipo di backup:
    - **In chiaro**, la scelta con cui parte la scheda: *Un semplice .zip: chiunque abbia il file vede tutti i dati e, su un'altra istanza, le chiavi dei provider di dati devono essere inserite di nuovo.*
    - **Sicuro**: *Un .lfbk cifrato con una password scelta da te: solo quella password lo apre, e una password perduta non può essere recuperata. Porta anche le chiavi dei provider di dati.* Vedi [Backup sicuri](#secure).
3. Per un backup sicuro, digita la sua password in **Password del backup**, poi di nuovo in **La stessa password**. La password segue le regole fornite dal server, quelle di una password di account con almeno 12 caratteri: l'indicatore sotto il primo campo le elenca mentre digiti (*Almeno 12 caratteri*, *Una lettera maiuscola*, *Una lettera minuscola*, *Un numero*, *Un carattere speciale*) e mostra quanto è robusta. Finché i due campi differiscono, sotto il secondo compare *Le due password differiscono.* e **Crea backup** resta disabilitato finché entrambe non sono corrette.
4. Fai clic su **Crea backup**. I campi della password si svuotano subito. La scheda segue il backup sul server, fase per fase; un backup sicuro termina con *Cifratura con la tua password*.
5. Quando la scheda mostra **Backup pronto**, fai clic su **Scarica**. Il browser salva l'archivio, denominato in base al momento in cui è iniziato il backup, in UTC, ad esempio `librefolio-backup-20261015-121500.zip`, oppure `librefolio-backup-20261015-121500.lfbk` per un backup sicuro, che la scheda contrassegna *Cifrato con la tua password: conservalo al sicuro, LibreFolio non può recuperarlo.* Una copia resta sul server, nell'elenco dei [Backup conservati sul server](#kept-backups): scaricala da lì anche più tardi.

Utile sapere:

- 🔑 **Conserva la password di un backup sicuro.** LibreFolio non ne conserva copia e, senza di essa, nessuno apre l'archivio, te compreso: conservala in un gestore di password, separata dall'archivio.
- 💾 L'archivio resta sul server finché non lo elimini, o finché non lo rimuove la [pulizia automatica](#backup-cleanup) che hai impostato. Una copia sullo stesso disco dei tuoi dati non è un vero backup: scaricala e conservala altrove ([Tenere copie fuori dal server](#keep-copies)). **Elimina dal server** lo rimuove subito, e **Crea un nuovo backup** ne avvia un altro.
- ⚠️ **Il backup è completo, con avvisi** significa che il database non ha superato il controllo di integrità o ha riferimenti interrotti ed è stato archiviato così com'è, oppure che alcuni file sono stati esclusi, oppure, per un backup sicuro, che non è stato possibile usare la chiave dell'istanza e che è stata esclusa ([Creare un backup sicuro](backup_moving.md#secure-problems)). L'archivio viene comunque scritto: leggi gli avvisi prima di farvi affidamento.
- 🚦 Mentre è in esecuzione un altro backup, avviato dall'app o dalla riga di comando, la scheda lo indica: riprova quando termina. Un backup avviato da questa scheda, o da un'altra scheda dell'app, la cui risposta non è mai arrivata (la connessione è caduta durante l'avvio) non è perduto: il successivo **Crea backup** lo trova in esecuzione, e la scheda lo segue, quindi ne offre il download, come se lo avesse appena avviato. Questo vale solo per un backup in chiaro: uno sicuro non viene mai seguito in questo modo, perché solo la sua password apre il suo archivio, e un backup seguito che risulta essere sicuro non viene offerto, a meno che la scheda non lo abbia avviato essa stessa; in entrambi i casi la scheda dice che è in esecuzione un altro backup. Una scheda che offre già un archivio continua a offrirlo e dice solo che è in esecuzione un altro backup. Un backup avviato dalla riga di comando non viene seguito: il suo archivio va altrove. La scheda non dice mai quale backup è in esecuzione; lo fa la console del browser (il suo id e da dove è stato avviato), se ti serve trovarlo.

### ⌨️ Dalla riga di comando {: #command-line }

```bash
# Docker: the archive appears in its own folder of ./LibreFolio-data/backups/ on the host
docker compose exec librefolio python dev.py backup create

# Host installation: the archive goes into its own folder of backups/ in the data directory
pipenv run ./dev.py backup create

# A secure backup (.lfbk): the password is asked twice
docker compose exec librefolio python dev.py backup create --encrypt
```

- 🗃️ Senza `--output`, l'archivio resta sul server, in una cartella propria dentro `backups/` ([Backup conservati sul server](#kept-backups)), e il comando ne stampa il percorso e il suo `SHA-256:`.
- 📁 `--output` (`-o`) copia l'archivio in un'altra cartella che esiste già, o con un nome scelto da te, e ne stampa anch'esso lo `SHA-256:`; in `backups/` non viene conservato nulla. Con Docker, il percorso è all'interno del container: usa una cartella montata dall'host.
- 🔒 Solo il proprietario dell'archivio può leggerlo (`0600`): con Docker, si tratta dell'utente del container.
- 🔐 `--encrypt` crea un [backup sicuro](#secure), `librefolio-backup-<date>-<time>.lfbk`, e chiede la sua password due volte al terminale. Invece di digitarla, forniscila con `--password-file FILE`, un file che contiene solo la password (i ritorni a capo alla fine non contano), come un segreto Docker, oppure con `--password-stdin`, una riga dello standard input, da una pipe: al terminale, il comando la chiede invece, senza mostrarla, come senza l'opzione. Ognuna delle due rende sicuro il backup da sola, con o senza `--encrypt`; le due non possono essere usate insieme.
- 🙈 Una password non è mai un argomento del comando: ogni utente del server può leggere i comandi in esecuzione (`ps`), e la shell li conserva nella cronologia. Non esiste un'opzione `--password`.
- 📏 La password segue le regole di Impostazioni › Amministrazione › Backup: almeno 12 caratteri, con una lettera maiuscola e una minuscola, una cifra e un simbolo. Una password che ne omette alcune ferma il comando prima che venga scritto qualsiasi cosa, con le regole mancanti: `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: min_length, digit)`.
- 🤖 Senza un terminale, da cron o da uno script, `--encrypt` da solo si ferma con `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)`.
- 📖 Ogni opzione, avviso ed errore: «Eseguire il backup dell'istanza» e «Eseguire il backup con Docker» in [Strumenti di amministrazione CLI](cli_tools.md).

??? example "🐳 La password dei backup come segreto Docker"

    1. Scrivi la password da sola in un file accanto a `docker-compose.yml`, come `backup_password.txt`, mai in `LibreFolio-data/`: chiunque avesse i dati avrebbe anche la sua password. Mantieni il file privato, `chmod 600 backup_password.txt`, e conserva una copia della password altrove: una password perduta non può essere recuperata.
    2. Aggiungi le righe contrassegnate a `docker-compose.yml` e lascia il resto del servizio com'è:

        ```yaml
        services:
          librefolio:
            secrets:                              # added
              - backup_password                   # added
        secrets:                                  # added
          backup_password:                        # added
            file: ./backup_password.txt           # added
        ```

        Se il file ha già elenchi `secrets:`, come per `JWT_SECRET_FILE` («Segreti in file» in [Variabili d'ambiente](configuration.md)), aggiungi le righe a quelli. Poi esegui `docker compose up -d`, che ricrea il container con il segreto.

    3. Crea il backup con il percorso in cui Docker mette il segreto nel container:

        ```bash
        docker compose exec librefolio python dev.py backup create --password-file /run/secrets/backup_password
        ```

### 🗃️ Backup conservati sul server {: #kept-backups }

Un backup creato dall'app o dalla riga di comando non viene più eliminato dopo un'ora: resta sul server finché non lo elimini, o finché non lo rimuove la [pulizia automatica](#backup-cleanup). Ognuno ha una cartella propria nella cartella `backups/` della directory dei dati, denominata in base al momento in cui è stato creato (in UTC), alla provenienza (`ui` per l'app, `cli` per la riga di comando) e a un breve codice che distingue due backup dello stesso secondo:

```text
backups/librefolio-backup-20261015-121500-ui-1a2b3c4d/librefolio-backup-20261015-121500.zip
```

L'archivio all'interno mantiene il suo nome abituale, `.zip`, `.lfbk` o `.tar`. `backups/.jobs/` contiene solo un backup in corso o uno non riuscito, che viene rimosso dopo un'ora.

**Aggiorna**, in cima all'elenco dei backup, lo rilegge: un backup fatto dalla riga di comando compare solo allora.

**Impostazioni › Amministrazione › Backup**, sotto *Backup su questo server*, elenca ogni backup conservato. **File**, nella sua scheda **Backup**, mostra lo stesso elenco; solo gli amministratori vedono l'uno o l'altro. Per ogni backup fornisce:

- 📅 la data e l'ora in cui è stato creato, e la provenienza: l'app o la riga di comando;
- 🔐 il suo tipo: in chiaro, con password ([sicuro](#secure)) o [sigillato](backup_sealed.md#sealed);
- 📏 la sua dimensione e il suo SHA-256: fai clic per copiare l'intero checksum e confrontalo con quello del file che scarichi;
- ⬇️ **Scarica** e 🗑️ **Elimina**, che rimuove subito il backup dal server.

!!! warning "💽 Scaricalo e conservalo altrove"

    Un backup che resta sullo stesso disco dei tuoi dati non è un vero backup: quando il disco viene perso, i dati e i loro backup se ne vanno insieme. Scarica l'archivio e conservalo su un altro disco, un NAS o fuori sede ([Tenere copie fuori dal server](#keep-copies)).

L'elenco mostra solo i backup creati da questa versione di LibreFolio. I file sparsi `librefolio-backup-*.zip` lasciati dalle versioni precedenti in `backups/` non sono elencati e non vengono mai rimossi da LibreFolio: eliminali tu stesso quando non ti servono più.

### 🧹 Pulizia automatica {: #backup-cleanup }

I backup conservati si accumulano e risiedono sul disco dei tuoi dati. Nel pannello chiuso **Pulizia automatica** della stessa sezione **Backup su questo server**, in **Impostazioni › Amministrazione › Backup** e in **File › Backup**, imposti due limiti, entrambi facoltativi:

| Limite | Cosa fa | Disattivato |
| --- | --- | --- |
| Dimensione totale, in MB | Quando i backup conservati pesano di più, i più vecchi vengono eliminati finché il resto non rientra | `0` |
| Età massima, in giorni | Un backup più vecchio di questo viene eliminato | `0` |

- 🛡️ **L'ultimo backup viene sempre conservato**, qualunque cosa dicano i limiti: un'istanza non rimane mai senza alcun backup.
- ⏰ La pulizia viene eseguita dopo ogni backup e all'avvio di LibreFolio, al massimo una volta l'ora: una modifica salvata si applica entro un'ora.
- 🏠 **Self-hosted:** entrambi i limiti sono disattivati finché non li imposti.
- 🔍 Vengono puliti solo i backup dell'elenco. Gli archivi sparsi più vecchi in `backups/`, un backup in corso e uno non riuscito non vengono mai toccati.
- ⌨️ La riga di comando lascia i suoi backup nello stesso posto e si applicano gli stessi limiti: vedi [Dove restano i backup](cli_backup.md#backup-kept).

### 📊 La barra dello spazio {: #space-used }

**File** mostra agli amministratori una barra, **Spazio utilizzato**, sopra le sue schede, qualunque scheda sia aperta: quanto spazio occupa la tua istanza. Si aggiorna quando fai clic su **Aggiorna** e ogni volta che cambia l'elenco dei backup conservati, così un backup creato o eliminato appare subito. La sua legenda indica la dimensione di ciascuna parte:

| Parte | Cosa conteggia |
| --- | --- |
| **Database** | Il database e i file che conserva accanto ad esso |
| **File caricati** | I file caricati nell'app, come quelli della pagina **File** |
| **Report dei broker** | Gli estratti conto caricati per importare le transazioni |
| **Backup** | Tutto ciò che è in `backups/`: i [backup conservati sul server](#kept-backups), un backup in corso e uno non riuscito |
| **Ripristino in attesa** | Un [ripristino](#restore) non ancora finito o scartato: l'archivio caricato e la sua versione aperta |
| **Altri file di LibreFolio** | Il resto della directory dei dati: log, stato e simili |

La barra ha tre aspetti, a seconda che sia impostato un limite e che il disco sia noto:

- 💽 **Nessun limite** (l'impostazione predefinita su un'installazione self-hosted): la barra è l'intero disco dei tuoi dati. Le parti di LibreFolio sono colorate, **Altro sul disco** è grigio e lo spazio **Libero** è lasciato vuoto. La riga sotto la barra indica quanto spazio usa LibreFolio rispetto alla dimensione totale del disco.
- 📏 **Con un limite**: la barra è il limite, e le parti di LibreFolio la riempiono fino a dove arrivano i dati. La riga sotto la barra mostra *usato rispetto al limite*.
- 📁 **Nessun limite e disco sconosciuto**: LibreFolio non può interrogare il disco, quindi la barra è la cartella di LibreFolio stessa, suddivisa nelle sue parti, senza spazio libero.

**Imposta il limite** nel pannello chiuso **Avanzate** sotto la stessa barra, nel campo **Spazio totale di LibreFolio (MB)**: un numero intero di megabyte, `0` per nessun limite, poi **Salva**; un avviso verde lo conferma. È lo spazio massimo che LibreFolio può occupare in tutto. È anche l'[impostazione globale](settings.md) *Limite di spazio*, che non viene mostrata nella scheda Amministrazione: questo campo è il punto in cui modificarla.

- 🚧 **Oltre il limite**, LibreFolio rifiuta ciò che aggiungerebbe dati: un file caricato, un report del broker, un backup avviato a mano (dopo aver provato la [pulizia automatica](#backup-cleanup)) e un [ripristino](#restore) il cui risultato lo supererebbe. Il messaggio dice di portare lo spazio totale ad almeno una certa dimensione e, se manca spazio sul disco, quanto altro ne serve libero. Non si fermano mai: transazioni, prezzi e database, i backup di un pannello di hosting e della riga di comando (la pulizia li segue) e un ripristino già confermato. Il limite non elimina nulla da solo.
- ⚠️ **Oltre il limite**, la barra avvisa che il limite è superato e suggerisce di eliminare backup o file, o di aumentare il limite. La barra diventa allora i tuoi dati, così nessuna parte resta fuori: una tacca chiamata *Limite 20 MB* mostra dove cade il limite, e le righe rosse dopo di essa mostrano di quanto lo superi.
- 💬 **Un rifiuto è detto dove sei**: nella finestra di caricamento o di importazione, o nella scheda del backup. Un amministratore trova **Apri le impostazioni**, che apre **File** con il pannello **Avanzate** aperto; un utente legge quanto spazio liberare, oppure di chiedere a un amministratore. Con un limite impostato da chi ospita l'istanza, il messaggio dice di chiederlo a loro.
- 🔒 **Impostato nella configurazione del server**: quando `LIBREFOLIO_STORAGE_LIMIT_MB` è impostato, il suo valore è il limite, il campo è disattivato e una nota dice che è impostato da chi ospita l'istanza. Vedi [Variabili d'ambiente](configuration.md). Un valore che LibreFolio non può usare, cioè non un numero intero, viene ignorato, e il campo funziona come sopra.
- 🧹 **La pulizia e la barra lavorano insieme.** Di solito i backup sono la parte che cresce: la [pulizia automatica](#backup-cleanup) li tiene sotto controllo, e ogni backup che elimini in **Impostazioni › Amministrazione › Backup** o in **File › Backup** accorcia **Backup** nella barra. Quando sei vicino al limite, inizia da lì.

### 🗄️ Tenere copie fuori dal server {: #keep-copies }

`backups/` si trova nella directory dei dati, sullo stesso disco dei dati: un backup conservato lì non sopravvive alla perdita di quel disco. Un archivio scaricato da Impostazioni è già fuori dal server. Dalla riga di comando, scrivi gli archivi su un altro disco, un NAS o fuori sede con `--output`, secondo una pianificazione.

Una riga `cron` per un'installazione host, ogni notte alle 03:30 (`crontab -e`, come l'utente che esegue LibreFolio):

```text
30 3 * * * cd /path/to/LibreFolio && pipenv run ./dev.py backup create --output /mnt/nas/librefolio/
```

Con Docker, aggiungi `-T`, poiché cron non fornisce un terminale al comando. L'archivio finisce in una cartella propria di `LibreFolio-data/backups/`, dove la [pulizia automatica](#backup-cleanup), una volta impostata, impedisce che il disco si riempia: copialo altrove con il tuo strumento abituale.

```text
30 3 * * * cd /path/to/librefolio && docker compose exec -T librefolio python dev.py backup create
```

Per gli archivi [sicuri](#secure), aggiungi `--password-file` con il percorso di un file che contiene la password, poiché cron non ha un terminale su cui chiederla; con Docker, il segreto dell'esempio sopra:

```text
30 3 * * * cd /path/to/librefolio && docker compose exec -T librefolio python dev.py backup create --password-file /run/secrets/backup_password
```

- 📁 La cartella passata a `--output` deve esistere quando il comando viene eseguito, quindi monta prima il NAS: un percorso che non è una cartella esistente diventa il nome dell'archivio stesso.
- 🔢 Il comando stampa ciò che ha fatto ed esce con `1` quando l'archivio non è dove hai chiesto: conserva quell'output, o fatti inviare da cron un'email.
- 🧭 cron esegue i comandi con un `PATH` ridotto: se non trova `pipenv` o `docker`, scrivi il percorso completo, che `command -v pipenv` stampa.
- 🗑️ LibreFolio non elimina nessuno di questi archivi: rimuovi tu quelli vecchi. Conservane diversi, e l'ultimo creato prima di ogni aggiornamento.
- 🔑 Conserva anche una copia di `.env`, riservata quanto gli archivi: nessun archivio la contiene. Conserva anche una copia di `secrets/`, a meno che i tuoi archivi non siano sicuri: un archivio in chiaro o [sigillato](backup_sealed.md#sealed) lascia fuori la chiave dell'istanza, uno sicuro porta la chiave generata da LibreFolio.
- 🔏 Per archivi notturni che il server stesso non può aprire, senza un file di password sul suo disco, vedi [Ogni notte con cron](backup_sealed.md#sealed-cron), in Backup sigillati.

### 🧰 Backup con restic o Backrest {: #restic }

LibreFolio scrive l'archivio; uno strumento di backup può poi inviarlo fuori sede e conservarne una cronologia. [restic](https://restic.net/) invia una cartella a un bucket S3, a Backblaze B2, a un server via SFTP e in altri luoghi, in forma cifrata, e dimentica le copie vecchie secondo una regola che gli fornisci. [Backrest](https://github.com/garethgeorge/backrest) è un'interfaccia web per restic, con il proprio scheduler. LibreFolio non ha bisogno di nessuno dei due: leggono solo la cartella in cui vengono scritti i suoi archivi.

Una ricetta notturna per un'installazione host, con le variabili di restic in un file privato (`chmod 600`):

```bash
# /etc/librefolio-restic.env: where the copies go, and the file with restic's password
RESTIC_REPOSITORY=sftp:backup@nas.example:/srv/restic/librefolio
RESTIC_PASSWORD_FILE=/root/.restic-librefolio-password
```

```text
30 3 * * * cd /path/to/LibreFolio && pipenv run ./dev.py backup create --output /var/backups/librefolio/ && . /etc/librefolio-restic.env && restic backup /var/backups/librefolio/ && restic forget --keep-daily 7 --keep-weekly 4 --prune && find /var/backups/librefolio/ -name 'librefolio-backup-*' -mtime +2 -delete
```

La riga crea l'archivio, invia la cartella, conserva sette copie giornaliere e quattro settimanali nel repository e rimuove gli archivi locali più vecchi di due giorni. Con Docker, crea l'archivio con il comando di [Tenere copie fuori dal server](#keep-copies) e fornisci a restic la cartella dell'host `LibreFolio-data/backups/`. Con Backrest, aggiungi un piano su quella stessa cartella, con la sua pianificazione e la sua conservazione, e lascia `backup create` in cron.

- 🔐 **La password di restic è una chiave per tutti i tuoi dati.** restic cifra il repository con essa, ma chiunque la possieda legge ogni copia al suo interno: conservala riservata quanto la password di un [backup sicuro](#secure), e conservane una copia altrove. Se viene perduta, il repository non può essere letto.
- 🔑 **Nessuna chiave pubblica.** restic ha bisogno della sua password sia per scrivere sia per leggere, quindi il server che invia le copie può anche leggerle. Se questo è un problema per te, invia [backup sigillati](backup_sealed.md#sealed-cron) (`--sealed`): restic conserva allora file che solo la tua chiave privata può aprire, e né il server né la password di restic li leggono. Anche i [backup sicuri](#secure) (`--password-file`) funzionano, ma la loro password risiede allora in un file sullo stesso server.
- 📦 **Poco da deduplicare.** Ogni archivio è compresso, e uno sicuro è cifrato: due notti appaiono diverse a restic, che conserva ogni archivio quasi per intero. Pianifica lo spazio del repository per le copie che conservi.
- 🧪 **Prova un ripristino prima di averne bisogno.** `restic restore latest --target /tmp/librefolio-check`, poi controlla l'archivio con [`backup restore --dry-run`](#check).

---

## 🔐 Backup sicuri {: #secure }

Un backup sicuro è l'archivio di un backup in chiaro, cifrato con una password scelta da te, in un file proprietario di LibreFolio: `.lfbk`. Creane uno da [Impostazioni › Amministrazione › Backup](#settings-backup) o con `backup create --encrypt` sulla [riga di comando](#command-line); ogni controllo e ripristino di questa pagina lo accetta, una volta fornita la sua password.

- 🛡️ **Cosa protegge: il file a riposo.** Un disco perso, un portatile rubato, una copia su un'unità cloud o un NAS: senza la password, nulla al suo interno può essere letto, né i dati né i nomi dei file. Un file modificato o troncato viene rilevato all'apertura e rifiutato.
- 👁️ **Cosa non protegge.** Chi conosce la password legge tutto: i dati di ogni utente e le chiavi dei provider di dati. Forniscila solo a chi può ripristinare il backup e non conservarla mai insieme al file.
- 🗝️ **Cosa porta con sé.** Oltre ai dati, la chiave dell'istanza, quando è stata generata da LibreFolio (`secrets/instance.key`): le chiavi salvate dei provider di dati viaggiano con il backup, e il suo ripristino le ricifra con la chiave dell'installazione che lo riceve, che conserva la propria. Una chiave impostata da te, con `LIBREFOLIO_INSTANCE_KEY` o `LIBREFOLIO_INSTANCE_KEY_FILE`, non esce mai: chi l'ha impostata la conserva.
- 🆘 **Una password perduta non può essere recuperata.** LibreFolio non ne conserva copia, e nient'altro apre il file.
- ⏳ **Lento da indovinare.** La chiave del file deriva dalla password tramite scrypt, che richiede 32 MiB di memoria e circa un decimo di secondo per ogni tentativo: nulla per un backup, abbastanza leggero per un piccolo server, ma lento per chi prova password una dopo l'altra. Da qui le regole: almeno 12 caratteri, con una lettera maiuscola e una minuscola, una cifra e un simbolo.
- 💽 **Sul server, durante la creazione,** l'archivio in chiaro viene scritto prima, nella cartella di lavoro del backup dentro `backups/`, che solo l'utente del server può aprire; viene rimosso non appena viene scritto il `.lfbk`, e quando il backup fallisce. Un controllo decifra il backup allo stesso modo, in una cartella privata della directory dei dati, e rimuove l'archivio decifrato una volta usato. Un'esecuzione interrotta bruscamente, da un'interruzione di corrente o `kill -9`, non può fare pulizia: il successivo avvio di LibreFolio rimuove ciò che ha lasciato in chiaro, e un backup interrotto in quel modo deve essere creato di nuovo. La cartella di un `backup inspect` interrotto in quel modo scompare dopo un'ora.

Il design, per gli sviluppatori: [Backup sicuri (`.lfbk`)](../developer/architecture/security.md#secure-backups).

---

## 🔎 Controllare un backup {: #check }

Due comandi controllano un archivio e non cambiano nulla. Con Docker, fornisci il percorso all'interno del container: un archivio in `LibreFolio-data/backups/` si trova lì in `/app/backend/data/prod-docker/backups/`. Un backup che LibreFolio [conserva](#kept-backups) si trova in una cartella propria, come `/app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/`.

```bash
# Is the archive whole, and what does it hold?
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# Can this installation restore it? A restore tried on a copy
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip --dry-run

# A secure backup: the same commands ask its password first
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.lfbk
```

Su un'installazione host, esegui `pipenv run ./dev.py backup …` con il percorso dell'archivio sull'host.

| | `backup inspect` | `backup restore --dry-run` |
| --- | --- | --- |
| Risponde | Se l'archivio è integro: la dimensione e il checksum SHA-256 di ogni voce, confrontati con il manifest | Se questa installazione può ripristinarlo: l'archivio decompresso in una copia, aggiornato e controllato |
| Mostra | Chi ha creato l'archivio e quando, la revisione del suo database, le sue righe e tabelle, i suoi file e se la chiave dell'istanza è inclusa | Lo stesso, più le migrazioni che un ripristino applicherebbe, i totali di controllo del libro mastro della copia confrontati con quelli registrati dall'archivio, le chiavi salvate dei provider di dati ricifrate con la chiave di questa installazione o da inserire di nuovo, e gli amministratori con cui accederesti |
| Richiede | Qualsiasi LibreFolio, con il server in esecuzione o fermo: nessuna directory dei dati, tranne per un backup sicuro, che decifra lì | L'installazione che riceverebbe l'archivio, il cui server può restare in esecuzione, e spazio libero nella sua directory dei dati: l'archivio decompresso, più il doppio del suo database, più 64 MB |
| Termina con | `✅ Every entry matches the manifest` | `✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.` |

- 🔐 **Un backup sicuro** (`.lfbk`): entrambi i comandi chiedono prima la sua password, digitata al terminale o fornita con `--password-file FILE` o `--password-stdin`, come per `backup create`. Lo decifrano in una cartella privata della directory dei dati, che solo l'utente del server può aprire, e la rimuovono alla fine: il disco deve avere spazio anche per l'archivio decifrato, all'incirca della stessa dimensione del `.lfbk`. Ciò che un comando interrotto bruscamente, da un'interruzione di corrente o `kill -9`, lascia in chiaro viene rimosso al successivo avvio di LibreFolio: l'archivio decifrato di `--dry-run` subito, la cartella di `inspect` dopo un'ora, che anche il successivo `inspect` rimuove. Il loro report aggiunge `Secure backup: decrypted with its password`. Una password errata li ferma con `❌ The password does not open this backup (wrong_password)`. Un `.zip` ignora le due opzioni della password.
- 🗝️ `--dry-run` dice anche cosa succede delle chiavi salvate dei provider di dati, per qualsiasi archivio: `Saved provider keys: 2 re-encrypted with this instance's key` quando il backup porta la chiave che le ha cifrate, `⚠️ 1 saved provider key cannot be read with this instance's key: enter it again after the restore` per quelle che non può leggere ([Cosa segue](#what-follows)).
- 🔁 Esegui `inspect` ogni tanto sulle copie che conservi, e `--dry-run` prima di uno spostamento, sull'installazione che riceverà l'archivio.
- 🖱️ **Ripristina un archivio**, in Impostazioni › Amministrazione › Backup, esegue lo stesso controllo di `--dry-run` su un archivio dal tuo computer: leggi il suo report, poi **Scarta questo archivio**, e nulla cambia ([Ripristinare da Impostazioni › Amministrazione › Backup](#restore-settings)).
- ❌ Un rifiuto termina con un codice tra parentesi: vedi [Quando qualcosa va storto](backup_moving.md#troubleshooting). Gli elenchi completi sono in «Controllare un archivio» e «Provare un ripristino su una copia», in [Strumenti di amministrazione CLI](cli_tools.md).

---

## ♻️ Ripristinare su questa installazione {: #restore }

Un ripristino sostituisce i dati dell'installazione con quelli dell'archivio: il database e i file, per ogni utente. Ci si arriva in due modi: **Impostazioni › Amministrazione › Backup**, nell'app, per gli amministratori, e `backup restore`, sulla riga di comando del server. Entrambe controllano prima l'archivio su una copia e non cambiano nulla finché non confermi: il successivo avvio di LibreFolio lo applica allora. Da Impostazioni › Amministrazione › Backup, LibreFolio si ferma non appena confermi, per quell'avvio; sulla riga di comando, lo riavvii quando preferisci. Su un'istanza che qualcuno ospita per te, la riga di comando è sul loro server: come uno dei suoi amministratori, usa Impostazioni › Amministrazione › Backup, o chiedi a loro.

### 🖱️ Ripristinare da Impostazioni › Amministrazione › Backup {: #restore-settings }

1. **Scegli l'archivio.** In **Impostazioni › Amministrazione › Backup**, sotto **Esegui il backup dell'istanza**, la scheda **Ripristina un archivio** ti ricorda che un ripristino sostituisce i dati di ogni utente: se potresti voler recuperare i dati attuali, [crea prima un backup](#settings-backup). Fai clic su **Scegli un archivio…** e seleziona un archivio di backup creato da LibreFolio qui o su un'altra installazione: un `.zip`, o un `.lfbk` sicuro. Un `.zip` viene inviato subito al server, con una barra di avanzamento: **Interrompi invio** lo ferma, e nulla viene conservato.
    Oppure prendi un backup che il server conserva: **Ripristina** sulla sua riga nell'elenco dei [backup conservati sul server](#kept-backups), qui o in **File › Backup**, chiede prima conferma, poi il server prende quel backup come archivio, senza download né caricamento, e la scheda prosegue dal passo successivo. Un backup sigillato di un pannello di hosting si apre solo con la chiave privata dei suoi destinatari: qui non si ripristina.
2. **Digita la sua password**, per un backup sicuro. La scheda la chiede prima che venga inviato qualcosa: *Un backup sicuro: digita la password con cui è stato creato.* Digitala in **Password del backup** e fai clic su **Controlla il backup**: l'archivio viene inviato, con la stessa barra di avanzamento, e la password va con la richiesta che avvia il controllo, che la prova subito. Una password errata riporta il modulo, con *Password errata, o il file è stato modificato: digita di nuovo la password.* L'archivio resta sul server, e il tentativo successivo non lo invia di nuovo. **Annulla** dimentica il file.
3. **Lascia che venga controllato.** Il server controlla l'archivio su una copia, come fa `backup restore --dry-run` ([Controllare un backup](#check)): *Decifratura del backup*, solo per un backup sicuro, *Controllo dell'archivio*, *Decompressione su una copia*, *Aggiornamento del database della copia*, *Verifica della copia*. Nulla cambia finché non confermi. **Interrompi il controllo** lo scarta: un controllo ancora in esecuzione viene scartato non appena termina.
4. **Leggi il report.** Si apre in una finestra, **Cosa farebbe questo ripristino**; una volta chiusa, **Leggi il report** la riapre. Fornisce:
    - chi ha creato l'archivio, con quale versione di LibreFolio e quando;
    - il suo database: alla versione di questo LibreFolio, o portato a essa sulla copia, con le migrazioni elencate e le correzioni applicate alla copia;
    - i file e la loro dimensione, la dimensione del database e le tabelle le cui righe sono state modificate dall'aggiornamento; e una barra di cosa contiene il backup: il database, i file caricati, i report del broker e gli altri file;
    - se il backup porta la chiave dell'istanza da cui proviene: in ogni caso, questo LibreFolio conserva la propria;
    - le chiavi salvate dei provider di dati: quante vengono ricifrate con la chiave di questo LibreFolio, come *2 chiavi salvate di provider di dati sono ricifrate con la chiave di questa istanza.*, e quante non può leggere, da inserire di nuovo dopo il ripristino, come *1 chiave salvata di un provider di dati non può essere letta con la chiave di questa istanza: inseriscila di nuovo dopo il ripristino.* ([Cosa segue](#what-follows));
    - i totali del libro mastro: gli stessi di quando è stato creato il backup, diversi sulle righe elencate ([come leggerli](backup_moving.md#check-refused)), non registrati, registrati da un'altra versione del metodo o illeggibili;
    - gli amministratori del backup, con *Dopo il ripristino accedi con uno di loro, con la password di allora; ogni sessione aperta ora termina.*
    - ogni amministratore con l'immagine del suo account nel backup, e **Verifica una password prima di ripristinare**: scegline uno, digita la sua password e fai clic su **Verifica**: *Con questa password accederai dopo il ripristino.*, oppure *Non è la sua password.* La password viene confrontata solo con il backup, e non viene mai conservata, scritta nel log o rimandata indietro;
    - *Gli inviti e i link inviati prima del ripristino saranno scaduti: inviali di nuovo se necessario.*
    - gli avvisi, che lasciano proseguire il ripristino, e i blocchi, che lo vietano: un backup senza un amministratore attivo, e un ripristino che supererebbe il [limite di spazio](#space-used), con la dimensione a cui portarlo; un controllo così restituisce subito il suo spazio, e il suo report resta a schermo finché non lo chiudi;
    - fino a quando viene conservato l'archivio caricato: 24 ore dopo il controllo.

    **Scarta questo archivio** scarta il controllo e la sua copia: nulla viene ripristinato. **Ci penso dopo** chiude la finestra e tiene il controllo: la scheda mostra allora *Un ripristino attende la tua decisione fino al …*, con **Riprendi**, che riapre lo stesso report, e **Scarta**, da qualsiasi scheda o dispositivo di un amministratore.

5. **Digita la parola.** La finestra mostra una parola scelta a caso, una parola reale da 6 a 10 lettere nella lingua dell'interfaccia. Digitala a mano nel campo sottostante: il campo rifiuta testo incollato e trascinato. La parola protegge da un clic affrettato, non da un amministratore: l'API e la riga di comando ne fanno a meno. Per un archivio che non può essere ripristinato, non si mostrano né la parola né **Ripristina e riavvia**: solo il pulsante che lo scarta.
6. **Ripristina e riavvia.** Una volta digitata la parola, **Ripristina e riavvia** conferma il ripristino e ferma subito LibreFolio, per tutti. Una finestra copre la pagina, **LibreFolio si sta riavviando**: *Il suo avvio applica il ripristino. Questa pagina attende che torni.* LibreFolio non si riavvia da solo: lo fa chi lo supervisiona ([Chi riavvia LibreFolio](#supervisors)), e quell'avvio applica il ripristino ([Cosa fa il prossimo avvio](#next-start)).

Quando LibreFolio risponde di nuovo, la pagina mostra com'è andata:

- ✅ **Ha funzionato**: la pagina va alla pagina di accesso, senza messaggi, poiché ogni sessione è terminata. Accedi con un amministratore del backup, con la password che l'account aveva quando è stato creato il backup: la solita prima pagina mostra i dati ripristinati. Un ripristino riuscito non lascia alcuna riga sulla scheda.
- ↩️ **Non è andato a buon fine**: la finestra mostra **Il ripristino non è andato a buon fine**, con il motivo, e **Torna a Backup** riporta alla scheda, dopo la pagina di accesso se il riavvio ha terminato la tua sessione, o alla pagina di blocco su un'istanza bloccata nel frattempo. *I dati sono come prima: …* significa che è stato eseguito il rollback del ripristino: la scheda dice allora quando e perché. *LibreFolio si è riavviato, ma il ripristino non è stato applicato.* significa che un avvio lo ha lasciato in attesa, per il motivo che segue. Cosa fare: [Cosa dice Impostazioni › Amministrazione › Backup](backup_moving.md#restore-settings-problems).
- ⏳ **Ci vuole molto**: dopo un minuto senza il server, la finestra aggiunge *LibreFolio non è ancora tornato. Se nulla lo riavvia da solo, avvialo tu: il ripristino viene applicato a quell'avvio.* Se LibreFolio non si ferma affatto, dopo un minuto la finestra dice *LibreFolio non si è fermato. Se non si riavvia da solo, riavvialo tu: il ripristino viene applicato a quell'avvio.*, e offre **Torna a Backup**: vedi [Cosa dice Impostazioni › Amministrazione › Backup](backup_moving.md#restore-settings-problems).

La pagina ricava l'esito con un ticket monouso che la sua richiesta di riavvio ha ricevuto, valido un'ora e conservato solo nella memoria della scheda: non richiede una sessione, quindi la finestra comunica l'esito qualunque sia la tua configurazione. Senza quel ticket, dopo un ricaricamento della pagina, più di un'ora di attesa, o un riavvio di LibreFolio dalla riga di comando invece che da questa pagina, la pagina si basa sulla sua sessione: senza `JWT_SECRET`, che disconnette tutti a ogni avvio ([Mantenere gli utenti connessi dopo un riavvio](index.md#session-persistence)), va poi alla pagina di accesso qualunque sia l'esito, e **Impostazioni › Amministrazione › Backup** dice, una volta effettuato l'accesso, se il ripristino è andato a buon fine.

Un ripristino confermato e non ancora applicato viene mostrato sulla scheda al posto di **Scegli un archivio…**: uno confermato dalla riga di comando, o qui quando LibreFolio non si è fermato o un avvio lo ha lasciato in attesa. La scheda riporta **Un ripristino attende il prossimo avvio di LibreFolio**, con il backup, chi lo ha confermato (`cli` dalla riga di comando) e quando e, se un avvio lo ha lasciato in attesa, il motivo, e *Il riavvio ferma LibreFolio per tutti; il suo prossimo avvio applica il ripristino e termina ogni sessione.*

- **Riavvia ora e ripristina** ferma LibreFolio, come fa **Ripristina e riavvia**, e la pagina lo attende allo stesso modo.
- **Annulla il ripristino** lo scarta con la sua copia controllata, come fa `backup pending --cancel`: i dati restano come sono.

Mentre un avvio applica il ripristino, la scheda riporta *Un avvio di LibreFolio sta applicando il ripristino.*

Utile sapere:

- 👑 Solo gli amministratori hanno la scheda, e viene eseguito un ripristino alla volta: un archivio viene controllato alla volta, ovunque sia iniziato il controllo, qui, in un'altra scheda o sulla riga di comando (*Un altro archivio è in fase di controllo: riprova quando termina.*), e un ripristino in attesa prende il posto di **Scegli un archivio…**.
- 📏 Quando l'installazione limita la dimensione degli archivi, la scheda lo dice, ad esempio *Archivi fino a 500 MB.*, e rifiuta un file più grande prima di inviare qualsiasi cosa. Il limite è `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`, in megabyte da 1024 × 1024 byte: nessuno per impostazione predefinita sulla tua installazione ([Il limite di caricamento di un ripristino](#restore-upload-limit)).
- 💽 Il disco della directory dei dati deve avere spazio per l'archivio e, durante il controllo, per la sua copia; per un backup sicuro, serve spazio anche per il suo archivio decifrato: [Controllare un backup](#check) dice quanto.
- 🔑 La password di un backup sicuro va al server solo con la richiesta che avvia il controllo, che la prova subito: non viene mai memorizzata, scritta nel log o restituita. Il campo si svuota non appena lo invii.
- 📦 Durante il controllo, l'archivio occupa la sua dimensione sul server, che la scheda dice mentre viene caricato, più la sua versione aperta; entrambi contano nel limite di spazio finché il ripristino non finisce o viene scartato.
- 🔄 Un ricaricamento della pagina continua a seguire il controllo e il suo report, e qualsiasi altra scheda o dispositivo di un amministratore lo riprende dalla scheda Backup. L'archivio caricato viene conservato 24 ore: dopo, la conferma risponde *Il controllo è troppo vecchio: controlla di nuovo l'archivio.*
- 🚪 Il ripristino termina ogni sessione, tutti accedono di nuovo con un account del backup, e i link inviati prima smettono di funzionare: vedi [Cosa fa il prossimo avvio](#next-start).
- ❌ Un caricamento, un controllo o una conferma rifiutati, o un server che non risponde, vengono mostrati sulla scheda con il motivo. **Riprova** rilegge lo stato del ripristino; per inviare di nuovo un archivio, sceglilo di nuovo con **Scegli un archivio…**. Il controllo rifiuta gli stessi archivi della riga di comando: vedi [Il controllo rifiuta l'archivio](backup_moving.md#check-refused).
- 🖥️ Se nulla riavvia LibreFolio, come un'installazione host avviata a mano, [avvia il server](cli_tools.md#start-the-server) tu stesso una volta che si è fermato: la pagina lo attende.

### 📤 Il limite di caricamento di un ripristino {: #restore-upload-limit }

Per controllare un archivio per un ripristino, un amministratore lo carica sull'istanza da
Impostazioni › Amministrazione › Backup
([Ripristinare da Impostazioni › Amministrazione › Backup](backup_restore.md#restore-settings)), tramite
`PUT /api/v1/backup/restore/upload`; l'istanza lo controlla poi su una copia, come
fa `backup restore --dry-run` sulla [riga di comando](cli_tools.md). `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` limita la dimensione degli
archivi che un amministratore può caricare.

| `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` | Archivio più grande accettato |
| --- | --- |
| Non impostato, o vuoto | Nessun limite |
| `0` | Nessun limite |
| Un numero intero, come `2048` | Quel numero di megabyte, da 1024 × 1024 byte ciascuno |

```bash
LIBREFOLIO_BACKUP_MAX_UPLOAD_MB=2048
```

- Impostalo nell'ambiente del container o in `.env`, poi riavvia LibreFolio.
- Un archivio oltre il limite risponde `413`, con il codice `backup_too_large` e il limite in
  `limit_mb`: prima che venga scritto qualcosa quando la richiesta annuncia la sua dimensione, altrimenti non appena
  il caricamento supera il limite. Non ne viene conservato nulla.
- Un proxy davanti a LibreFolio deve lasciar passare almeno altrettanto: Nginx con
  `client_max_body_size`, il cui valore predefinito è solo 1 MB (`client_max_body_size 2048m;` corrisponde
  all'esempio sopra), e la tua CDN, se limita la dimensione di una richiesta. Un `413` senza il
  codice `backup_too_large` proviene dal proxy, non da LibreFolio.
- Un valore diverso da un numero intero, come `500MB` o `-1`, non ferma il server: il log di avvio
  contiene già un errore, `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB cannot be used: …` (`check` è
  `backup.upload_limit`), poi ogni caricamento risponde `503` con il codice `backup_upload_unavailable`, e
  il log contiene un errore che nomina la variabile: `The upload limit of a restore cannot be read`.
- Il disco della directory dei dati richiede spazio per l'archivio e, durante il controllo, anche per la sua copia
  decompressa (quanto: «Provare un ripristino su una copia» in [Strumenti di amministrazione CLI](cli_tools.md)): in mancanza di
  spazio, il caricamento risponde `507` con il codice `backup_no_space`, anche quando il disco si dichiara
  pieno solo alla fine del file, come può fare un file system di rete o una quota. Il controllo risponde con
  un proprio codice, `no_space`: un `507` quando non può nemmeno iniziare, un rifiuto dell'archivio una volta avviato.
  Un caricamento che non può essere scritto per un altro motivo risponde `500` con il codice
  `backup_upload_failed`, e il log contiene la causa.
- Un amministratore legge il limite in vigore in `upload_limit_mb` di
  `GET /api/v1/backup/restore/status`: `0` per nessun limite, `null` quando il valore non può essere letto.
  Impostazioni › Amministrazione › Backup lo mostra sulla sua scheda di ripristino, ad esempio *Archivi fino a 500 MB.*,
  e rifiuta un file più grande prima di inviarlo.

Il limite di caricamento vincola l'archivio così com'è inviato, compresso: uno zip può decomprimersi in molto più della
sua dimensione, e il controllo lo decomprime sul disco della directory dei dati.
`LIBREFOLIO_BACKUP_MAX_RESTORE_MB` limita la dimensione decompressa di un archivio, in base alle dimensioni dichiarate dal suo manifest,
prima che il controllo decomprima qualsiasi cosa.

| `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` | Dimensione massima decompressa di un archivio |
| --- | --- |
| Non impostato, o vuoto | Nessun limite |
| `0` | Nessun limite |
| Un numero intero, come `16384` | Quel numero di megabyte, da 1024 × 1024 byte ciascuno |

- Un archivio oltre il limite viene rifiutato prima che venga decompresso qualcosa: il controllo fallisce con il codice
  `unpacked_too_large`, e nulla della sua copia viene lasciato. Un archivio sicuro viene prima decifrato, il che
  richiede circa la sua dimensione, poi misurato allo stesso modo.
- Un valore che imposti vince sempre, `0` incluso. `backup restore` sulla riga di comando segue lo stesso
  limite; chi esegue il server lo solleva per un singolo comando con `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0`
  davanti a esso («Provare un ripristino su una copia» in [Strumenti di amministrazione CLI](cli_tools.md)).
- Un valore diverso da un numero intero non ferma il server: il log di avvio contiene già un errore,
  `LIBREFOLIO_BACKUP_MAX_RESTORE_MB cannot be used: …` (`check` è `backup.restore_limit`), poi ogni
  controllo, `POST /api/v1/backup/restore/stage`, risponde `503` con il codice
  `backup_restore_unavailable`, l'archivio viene conservato, e il log contiene un errore.

### ⌨️ Ripristinare dalla riga di comando {: #restore-command }

Eseguilo dove gira il server, nel container con Docker:

```bash
# 1. Check the archive on a copy, read the report, then type "restore" to confirm
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# 2. Restart LibreFolio: its next start applies the restore
docker compose restart librefolio

# 3. See how it went
docker compose exec librefolio python dev.py backup pending
```

- 🧪 Il passo 1 esegue lo stesso controllo di `--dry-run` e mostra lo stesso report, poi ti chiede di digitare `restore`. Nulla cambia ancora: LibreFolio continua a funzionare sui suoi dati, e il ripristino attende il prossimo avvio.
- 🖥️ Su un'installazione host, esegui `pipenv run ./dev.py backup restore <archive>`, poi ferma l'intero server e [avvialo](cli_tools.md#start-the-server) di nuovo: non riavviare mai un solo worker.
- ⏳ Una volta che LibreFolio è di nuovo attivo, `backup pending` dice `✅ The last restore was applied on …`. Prima del riavvio, `backup pending --cancel` scarta il ripristino in attesa, con la sua copia controllata.
- 🤖 In uno script, `--yes` conferma senza chiedere.
- 🔐 Per un backup sicuro (`.lfbk`), `backup restore` chiede la sua password prima del controllo, o la legge con `--password-file` o `--password-stdin`, come fa `inspect` ([Controllare un backup](#check)): in uno script, fornisci una di queste opzioni insieme a `--yes`.
- 📖 Altro: «Ripristinare un archivio» e «Seguire o annullare un ripristino» in [Strumenti di amministrazione CLI](cli_tools.md).

### 🔄 Cosa fa il prossimo avvio {: #next-start }

- 🔀 **Lo scambio.** Il database e le tre cartelle dei file cambiano posto con la copia controllata: una rinomina per cartella, istantanea qualunque sia la sua dimensione. `secrets/`, `logs/`, `scheduler_state.json` e `backups/` restano come sono, così l'installazione conserva la propria chiave dell'istanza. La chiave che un backup sicuro porta non viene mai messa al suo posto: il controllo ha già ricifrato le chiavi salvate dei provider di dati sulla copia, con la chiave di questa installazione.
- 🚪 **Ogni sessione termina.** Tutti accedono di nuovo, su ogni dispositivo, con un account del backup e la password che aveva allora.
- 🔗 **I link monouso vengono revocati.** Nessun link di invito, reimpostazione password o verifica email inviato prima funziona più, nemmeno quelli contenuti nel backup: inviane di nuovi. Un account ancora in attesa della verifica email smette di attendere: quando il suo proprietario chiede alla pagina di accesso un nuovo link, la pagina risponde che l'account è disabilitato. Un amministratore lo riattiva con **Riattiva** ([Cosa fa ogni azione](users.md#actions)), o lo elimina ([Eliminare un account](users.md#delete)) così che il proprietario si registri di nuovo.
- ✅ **Il primo avvio deve completarsi.** Solo allora il ripristino viene conservato e i dati precedenti rimossi. Se quell'avvio fallisce, per una migrazione non riuscita o un file danneggiato, l'avvio successivo rimette da solo i dati precedenti, e `backup pending`, come la scheda in Impostazioni › Amministrazione › Backup, dice che è stato eseguito il rollback del ripristino, con il motivo.

### 🔌 Chi riavvia LibreFolio {: #supervisors }

Sei tu ad avviare il ripristino: con il riavvio della riga di comando, o con **Ripristina e riavvia** in Impostazioni › Amministrazione › Backup, che ferma LibreFolio. Nulla in LibreFolio riavvia il server: lo fa chi lo supervisiona, dopo quella fermata, e dopo un primo avvio che fallisce, così che l'avvio successivo riporti indietro i dati.

| Supervisore | Riavvia LibreFolio da solo |
| --- | --- |
| Docker Compose | Con `restart: unless-stopped`, in entrambi i file compose forniti da LibreFolio |
| systemd | Con `Restart=always` |
| Nessuno | No: avvia LibreFolio tu stesso, e il ripristino, o il ritorno indietro, avviene a quell'avvio |

**Ripristina e riavvia** ferma LibreFolio in modo pulito: una policy che lo riavvia solo dopo un errore, come `on-failure`, non lo avvia dopo quella fermata.

---

## 🔗 Correlati

- 📄 **[Backup: backup sigillati](backup_sealed.md)** — Backup sigillati: una chiave invece di una password
- 📄 **[Backup: spostamento e risoluzione dei problemi](backup_moving.md)** — Porta LibreFolio a casa, quando qualcosa va storto
- 🛠️ **[Strumenti di amministrazione CLI](cli_tools.md)** — «Eseguire il backup dell'istanza»: ogni opzione e messaggio di `backup create`, `inspect`, `restore`, `decrypt` e `pending`, e «Eseguire il backup con Docker»
- 📂 **[Struttura del file system](filesystem.md)** — La directory dei dati, `secrets/` e una copia fatta a mano
- 🐳 **[Installazione con Docker](../user/installation.md)** — Installare LibreFolio e aggiornarlo
- 👥 **[Utenti e inviti](users.md)** — Riattivare o eliminare account e inviare nuovi link
- 📧 **[Email](email.md)** — Le variabili email, che nessun archivio contiene
- 📝 **[Variabili d'ambiente](configuration.md)** — «La chiave dell'istanza» e ogni opzione di `.env`
- 🧑‍💻 Per gli sviluppatori: **[Ripristinare un backup](../developer/architecture/security.md#backup-restore)** — Lo scambio, il journal, il rollback e il riavvio
- 🧑‍💻 Per gli sviluppatori: **[Backup sicuri (`.lfbk`)](../developer/architecture/security.md#secure-backups)** — L'envelope, la password e la chiave dell'istanza che un backup sicuro porta
- 🧑‍💻 Per gli sviluppatori: **[Backup sigillati (`.tar`)](../developer/architecture/security.md#sealed-backups)** — I tre membri, age tramite `pyrage` e il lettore rigoroso
