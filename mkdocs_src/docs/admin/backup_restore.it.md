# 💾 Backup, ripristino e spostamento della tua istanza

Un backup è un unico archivio con tutto il tuo LibreFolio: il database e i file di ogni utente. È un semplice zip oppure, per un [backup sicuro](#secure), un `.lfbk` cifrato con una password scelta da te.

Qui trovi:

- [cosa contiene l'archivio](#contents) e [cosa comporta](#what-follows);
- come [crearne uno](#create), dall'app o dalla riga di comando, e come [tenerne copie fuori dal server](#keep-copies);
- come [controllarlo](#check) e come [ripristinarlo](#restore), dall'app o dalla riga di comando.

Ogni opzione e messaggio dei comandi: «Eseguire il backup dell'istanza», in [Strumenti di amministrazione CLI](cli_tools.md).

!!! tip "🗓️ Creane uno prima di ogni aggiornamento"

    LibreFolio non riporta mai un database a una versione precedente. Un backup creato prima di un aggiornamento è la tua via di ritorno alla versione che avevi: vedi [Aggiornare LibreFolio](../user/installation.md#updating).

!!! info "📚 Questa guida è su più pagine"

    Oltre a questa pagina: [Backup: backup sigillati](backup_sealed.md), [Backup: spostamento e risoluzione dei problemi](backup_moving.md).

---

## 📦 Cosa contiene un backup {: #contents }

L'archivio è uno zip con la struttura della [directory dei dati](filesystem.md): decompresso in una directory dei dati vuota, è di nuovo la tua istanza. Un [backup sicuro](#secure) è lo stesso zip, cifrato con una password, in un file `.lfbk`. Un [backup sigillato](backup_sealed.md#sealed) è un backup sicuro la cui password si apre solo con una tua chiave privata, in un `.tar`.

| Nell'archivio | Di cosa si tratta |
| --- | --- |
| `sqlite/app.db` | Il database: utenti, broker, transazioni, asset, prezzi, tassi di cambio e impostazioni. Una copia coerente, presa mentre LibreFolio continua a funzionare |
| `custom-uploads/` | I file caricati nell'app |
| `broker_reports/` | I report dei broker |
| `scenario_catalog/` | I tuoi scenari di stress, se ne hai aggiunti |
| `secrets/instance.key` | Solo in un [backup sicuro](#secure), e solo se LibreFolio ha generato la chiave dell'istanza: la chiave che cifra le chiavi salvate dei provider di dati. Un ripristino la legge soltanto: l'installazione che riceve il backup conserva la propria |
| `manifest.json` | La descrizione dell'archivio: versione di LibreFolio e data di creazione, revisione di migrazione del database, righe per tabella, totali di controllo del libro mastro (liquidità di ogni broker per valuta e quantità di ogni posizione), dimensione e checksum SHA-256 di ogni file, e se l'archivio porta la chiave dell'istanza |

Mai nell'archivio:

- 🔑 `secrets/`: un [backup sicuro](#secure) porta solo la chiave generata da LibreFolio, `secrets/instance.key`, mai una chiave impostata da te con `LIBREFOLIO_INSTANCE_KEY` o `LIBREFOLIO_INSTANCE_KEY_FILE` («La chiave dell'istanza» in [Variabili d'ambiente](configuration.md));
- 📝 `logs/` e `scheduler_state.json` (l'ultima esecuzione delle sincronizzazioni pianificate);
- 💾 `backups/`, dove LibreFolio [conserva i backup che crea](#kept-backups), e `.restore/`, la cartella di lavoro di un ripristino;
- ⚙️ la configurazione: `.env` e le variabili d'ambiente, comprese le impostazioni [email](email.md), che vivono solo nell'ambiente.

### 🧭 Cosa segue {: #what-follows }

- 🔒 **Tienilo privato.** Un archivio in chiaro contiene i dati di ogni utente, non cifrati: conservalo, con ogni copia, con la stessa riservatezza del server. Uno [sicuro](#secure) si apre solo con la sua password: tieni la password separata dall'archivio.
- ⚙️ **Porta con te la configurazione.** Conserva una copia del tuo `.env` insieme agli archivi: su un'altra installazione, imposta di nuovo le opzioni che ti servono, comprese quelle email ([Dove risiede la configurazione](email.md#where-it-lives)).
- 🏠 **Qualsiasi installazione può accettarlo**, da Impostazioni o dalla riga di comando, se esegue la stessa versione di LibreFolio o una più recente, chiunque abbia creato l'archivio.
- 🗝️ **Segreti salvati e chiave dell'istanza.** Ciò che LibreFolio ha cifrato con la chiave dell'istanza, come la chiave API di un'origine dati salvata nell'app, si legge solo con quella chiave:

| Backup | La chiave dell'istanza | Ripristinato su un'installazione con un'altra chiave |
| --- | --- | --- |
| [Sicuro](#secure), chiave generata da LibreFolio | Viaggia con i dati | I segreti vengono ricifrati con la chiave dell'installazione che lo riceve: nulla da fare |
| In chiaro; [sigillato](backup_sealed.md#sealed); sicuro con chiave dall'ambiente (`LIBREFOLIO_INSTANCE_KEY`, `LIBREFOLIO_INSTANCE_KEY_FILE`) o non utilizzabile | Resta fuori | I segreti restano salvati ma illeggibili; LibreFolio non usa mai un valore errato. **Impostazioni › Plugin** dice sotto ciascuno *Salvato, ma la chiave di questa istanza non può leggerlo: inseriscilo di nuovo.* |

Se hai ancora la vecchia chiave, rimettila **prima** che qualcuno inserisca di nuovo un segreto: un segreto inserito con la nuova chiave diventerebbe illeggibile una volta ripristinata quella vecchia. Inserisci di nuovo i segreti solo se la vecchia chiave è perduta.

1. Ferma LibreFolio.
2. **Sul server, in `secrets/` della directory dei dati**: metti la tua copia di `secrets/instance.key` al posto di quella generata. Oppure, **in `.env`**, rimetti il vecchio valore della variabile («La chiave dell'istanza» in [Variabili d'ambiente](configuration.md)).
3. Avvia di nuovo LibreFolio.

Se l'installazione conserva la propria chiave, o i suoi segreti sono già cifrati con la sua chiave, accetta la vecchia chiave al ripristino: **dalla riga di comando**, ripristina con `--instance-key-file` e la tua copia della vecchia chiave; il controllo ricifra quei segreti con la chiave di questa installazione («La chiave dell'istanza di un'altra installazione» in [Strumenti di amministrazione CLI](cli_tools.md)).

Per le impostazioni dell'intera istanza, ogni avvio registra nel log l'errore *Segreti dei plugin memorizzati che la chiave dell'istanza non può leggere: …*, con il loro numero, finché non vengono inseriti di nuovo o non torna la vecchia chiave. Nessun plugin distribuito con LibreFolio ne conserva uno oggi.

---

## ⬇️ Creare un backup {: #create }

Due modi producono lo stesso archivio:

| Dove | Cosa ottieni |
| --- | --- |
| **Impostazioni › Amministrazione › Backup**, nell'app (amministratori) | L'archivio scaricato sul tuo computer, e una copia [conservata sul server](#kept-backups) |
| **Terminale sul server**: `backup create` | L'archivio sul server, o dove indichi con `--output` |

Da entrambi il backup può essere [sicuro](#secure): lo stesso zip, cifrato con una password scelta da te. Solo dalla riga di comando può essere [sigillato](backup_sealed.md#sealed): cifrato con una password casuale che solo una tua chiave privata apre, per i backup creati senza nessuno alla tastiera.

LibreFolio continua a funzionare durante il backup. Viene eseguito un backup alla volta, chiunque lo abbia avviato.

### 🖱️ Da Impostazioni › Amministrazione › Backup {: #settings-backup }

1. Apri **Impostazioni › Amministrazione › Backup** (solo gli amministratori hanno la scheda), sezione **Esegui il backup dell'istanza**.
2. Scegli il tipo:
    - **In chiaro** (predefinito): *Un semplice .zip: chiunque abbia il file vede tutti i dati e, su un'altra istanza, le chiavi dei provider di dati devono essere inserite di nuovo.*
    - **Sicuro**: *Un .lfbk cifrato con una password scelta da te: solo quella password lo apre, e una password perduta non può essere recuperata. Porta anche le chiavi dei provider di dati.* Vedi [Backup sicuri](#secure).
3. Per un backup sicuro, digita la password in **Password del backup** e di nuovo in **La stessa password**. Valgono le regole di una password di account, fornite dal server: l'indicatore sotto il primo campo le elenca mentre digiti (*Almeno 12 caratteri*, *Una lettera maiuscola*, *Una lettera minuscola*, *Un numero*, *Un carattere speciale*) e mostra quanto è robusta. Finché i due campi differiscono compare *Le due password differiscono.* e **Crea backup** resta disabilitato.
4. Fai clic su **Crea backup**. I campi della password si svuotano subito; la scheda segue il backup fase per fase (un backup sicuro termina con *Cifratura con la tua password*).
5. A **Backup pronto**, fai clic su **Scarica**. Il browser salva `librefolio-backup-20261015-121500.zip` (data e ora di inizio, in UTC), o `.lfbk` per un backup sicuro, che la scheda contrassegna *Cifrato con la tua password: conservalo al sicuro, LibreFolio non può recuperarlo.*

Utile sapere:

- 🔑 **Conserva la password di un backup sicuro** in un gestore di password, separata dall'archivio: LibreFolio non ne tiene copia e senza di essa nessuno apre l'archivio, te compreso.
- 💾 Una copia resta sul server, nell'elenco dei [Backup conservati sul server](#kept-backups), finché non la elimini o non la rimuove la [pulizia automatica](#backup-cleanup): scaricala da lì anche più tardi. Una copia sullo stesso disco dei dati non è un vero backup: conservala altrove ([Tenere copie fuori dal server](#keep-copies)). **Elimina dal server** la rimuove subito; **Crea un nuovo backup** ne avvia un altro.
- ⚠️ **Il backup è completo, con avvisi**: il database non ha superato il controllo di integrità o ha riferimenti interrotti ed è stato archiviato così com'è; oppure alcuni file sono stati esclusi; oppure, per un backup sicuro, la chiave dell'istanza non era utilizzabile ed è stata esclusa ([Creare un backup sicuro](backup_moving.md#secure-problems)). L'archivio viene comunque scritto: leggi gli avvisi prima di farvi affidamento.
- 🚦 **Un altro backup è in esecuzione** (dall'app o dalla riga di comando): la scheda lo dice, riprova quando termina.

Cosa fa la scheda con un backup già in corso:

| Backup in corso | La scheda |
| --- | --- |
| In chiaro, avviato da questa o da un'altra scheda dell'app, la cui risposta non è mai arrivata (connessione caduta all'avvio) | Non è perduto: il successivo **Crea backup** lo trova, lo segue e ne offre il download |
| Sicuro, non avviato da questa scheda | Mai seguito: solo la sua password apre l'archivio. La scheda dice che è in esecuzione un altro backup |
| Qualsiasi, mentre la scheda offre già un archivio | Continua a offrire il suo e dice solo che è in esecuzione un altro backup |
| Avviato dalla riga di comando | Non seguito: il suo archivio va altrove |

La scheda non dice mai quale backup è in esecuzione: lo fa la console del browser (id e provenienza).

### ⌨️ Dalla riga di comando {: #command-line }

**Nel terminale del server**, dalla cartella con `docker-compose.yml` (Docker) o dalla cartella di LibreFolio (installazione host):

```bash
# Docker: the archive appears in its own folder of ./LibreFolio-data/backups/ on the host
docker compose exec librefolio python dev.py backup create

# Host installation: the archive goes into its own folder of backups/ in the data directory
pipenv run ./dev.py backup create

# A secure backup (.lfbk): the password is asked twice
docker compose exec librefolio python dev.py backup create --encrypt
```

Il comando stampa il percorso dell'archivio e il suo `SHA-256:`.

- 🗃️ Senza `--output`, l'archivio resta sul server, in una cartella propria dentro `backups/` ([Backup conservati sul server](#kept-backups)).
- 📁 `--output` (`-o`) copia l'archivio in un'altra cartella già esistente, o con un nome scelto da te; in `backups/` non resta nulla. Con Docker il percorso è dentro il container: usa una cartella montata dall'host.
- 🔒 Solo il proprietario dell'archivio può leggerlo (`0600`): con Docker, l'utente del container.
- 🔐 `--encrypt` crea un [backup sicuro](#secure), `librefolio-backup-<date>-<time>.lfbk`, e chiede la password due volte al terminale. In alternativa: `--password-file FILE`, un file con la sola password (i ritorni a capo finali non contano), come un segreto Docker; oppure `--password-stdin`, una riga dello standard input da una pipe (al terminale, il comando la chiede senza mostrarla). Ognuna delle due rende sicuro il backup da sola, con o senza `--encrypt`; non si usano insieme.
- 🙈 Non esiste `--password`: ogni utente del server legge i comandi in esecuzione (`ps`) e la shell li conserva nella cronologia.
- 📏 Regole della password, come in Impostazioni › Amministrazione › Backup: almeno 12 caratteri, una maiuscola, una minuscola, una cifra e un simbolo. Altrimenti il comando si ferma prima di scrivere qualsiasi cosa: `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: min_length, digit)`.
- 🤖 Senza terminale (cron, script), `--encrypt` da solo si ferma: `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)`.
- 📖 Ogni opzione, avviso ed errore: «Eseguire il backup dell'istanza» e «Eseguire il backup con Docker» in [Strumenti di amministrazione CLI](cli_tools.md).

??? example "🐳 La password dei backup come segreto Docker"

    1. **Accanto a `docker-compose.yml`**, scrivi la sola password in un file, come `backup_password.txt`, mai in `LibreFolio-data/` (chi avesse i dati avrebbe anche la password). Poi `chmod 600 backup_password.txt`, e conserva una copia della password altrove: perduta, non si recupera.
    2. **In `docker-compose.yml`**, aggiungi le righe contrassegnate e lascia il resto del servizio com'è. Se il file ha già elenchi `secrets:`, come per `JWT_SECRET_FILE` («Segreti in file» in [Variabili d'ambiente](configuration.md)), aggiungi le righe a quelli.

        ```yaml
        services:
          librefolio:
            secrets:                              # added
              - backup_password                   # added
        secrets:                                  # added
          backup_password:                        # added
            file: ./backup_password.txt           # added
        ```

        Esegui `docker compose up -d`: il container viene ricreato con il segreto.

    3. **Nel terminale del server**, crea il backup con il percorso del segreto nel container:

        ```bash
        docker compose exec librefolio python dev.py backup create --password-file /run/secrets/backup_password
        ```

### 🗃️ Backup conservati sul server {: #kept-backups }

Un backup creato dall'app o dalla riga di comando non viene più eliminato dopo un'ora: resta sul server finché non lo elimini, o finché non lo rimuove la [pulizia automatica](#backup-cleanup). Ognuno ha una cartella propria in `backups/` della directory dei dati: momento di creazione (UTC), provenienza (`ui` app, `cli` riga di comando) e un breve codice che distingue due backup dello stesso secondo. L'archivio dentro mantiene il nome abituale, `.zip`, `.lfbk` o `.tar`:

```text
backups/librefolio-backup-20261015-121500-ui-1a2b3c4d/librefolio-backup-20261015-121500.zip
```

`backups/.jobs/` contiene solo un backup in corso o uno non riuscito, rimosso dopo un'ora.

**Dove li vedi**: **Impostazioni › Amministrazione › Backup**, sotto *Backup su questo server*, oppure **File › Backup**, stesso elenco; solo gli amministratori. **Aggiorna**, in cima all'elenco, lo rilegge: un backup fatto dalla riga di comando compare solo allora. Per ogni backup:

- 📅 data e ora di creazione, e provenienza: app o riga di comando;
- 🔐 tipo: in chiaro, con password ([sicuro](#secure)) o [sigillato](backup_sealed.md#sealed);
- 📏 dimensione e SHA-256: fai clic per copiare l'intero checksum e confrontalo con quello del file scaricato;
- ⬇️ **Scarica** e 🗑️ **Elimina**, che rimuove subito il backup dal server.

!!! warning "💽 Scaricalo e conservalo altrove"

    Un backup che resta sullo stesso disco dei tuoi dati non è un vero backup: quando il disco viene perso, i dati e i loro backup se ne vanno insieme. Scarica l'archivio e conservalo su un altro disco, un NAS o fuori sede ([Tenere copie fuori dal server](#keep-copies)).

L'elenco mostra solo i backup creati da questa versione di LibreFolio. I file sparsi `librefolio-backup-*.zip` delle versioni precedenti in `backups/` non sono elencati e LibreFolio non li rimuove mai: eliminali tu quando non ti servono più.

### 🧹 Pulizia automatica {: #backup-cleanup }

**Nel pannello chiuso Pulizia automatica**, nella sezione **Backup su questo server** di **Impostazioni › Amministrazione › Backup** o di **File › Backup**, imposti due limiti, entrambi facoltativi:

| Limite | Cosa fa | Disattivato |
| --- | --- | --- |
| Dimensione totale, in MB | Quando i backup conservati pesano di più, i più vecchi vengono eliminati finché il resto non rientra | `0` |
| Età massima, in giorni | Un backup più vecchio viene eliminato | `0` |

- 🛡️ **L'ultimo backup viene sempre conservato**, qualunque cosa dicano i limiti.
- ⏰ La pulizia gira dopo ogni backup e all'avvio di LibreFolio, al massimo una volta l'ora: una modifica salvata si applica entro un'ora.
- 🏠 **Self-hosted:** entrambi i limiti sono disattivati finché non li imposti.
- 🔍 Vengono puliti solo i backup dell'elenco: mai gli archivi sparsi più vecchi in `backups/`, un backup in corso o uno non riuscito.
- ⌨️ I backup della riga di comando restano nello stesso posto e seguono gli stessi limiti: [Dove restano i backup](cli_backup.md#backup-kept).

### 📊 La barra dello spazio {: #space-used }

**In File**, sopra le schede, gli amministratori vedono la barra **Spazio utilizzato**: quanto occupa la tua istanza. Si aggiorna con **Aggiorna** e ogni volta che cambia l'elenco dei backup conservati. La legenda dà la dimensione di ogni parte:

| Parte | Cosa conteggia |
| --- | --- |
| **Database** | Il database e i file che conserva accanto ad esso |
| **File caricati** | I file caricati nell'app, come quelli della pagina **File** |
| **Report dei broker** | Gli estratti conto caricati per importare le transazioni |
| **Backup** | Tutto ciò che è in `backups/`: i [backup conservati sul server](#kept-backups), un backup in corso e uno non riuscito |
| **Ripristino in attesa** | Un [ripristino](#restore) non ancora finito o scartato: l'archivio caricato e la sua versione aperta |
| **Altri file di LibreFolio** | Il resto della directory dei dati: log, stato e simili |

Tre aspetti della barra:

| Situazione | La barra | La riga sotto |
| --- | --- | --- |
| 💽 **Nessun limite** (predefinito self-hosted) | L'intero disco dei dati: parti di LibreFolio colorate, **Altro sul disco** grigio, **Libero** vuoto | Quanto usa LibreFolio rispetto al disco |
| 📏 **Con un limite** | Il limite, riempito fino a dove arrivano i dati | *usato rispetto al limite* |
| 📁 **Nessun limite e disco sconosciuto** (LibreFolio non può interrogarlo) | La sola cartella di LibreFolio, divisa nelle sue parti, senza spazio libero | — |

**Imposta il limite** in **File › Avanzate** (pannello chiuso sotto la barra), campo **Spazio totale di LibreFolio (MB)**: un numero intero di megabyte, `0` per nessun limite, poi **Salva**; un avviso verde conferma. È lo spazio massimo che LibreFolio può occupare in tutto, cioè l'[impostazione globale](settings.md) *Limite di spazio*, che la scheda Amministrazione non mostra: si cambia qui.

- 🚧 **Oltre il limite**, LibreFolio rifiuta ciò che aggiungerebbe dati: un file caricato, un report del broker, un backup avviato a mano (dopo aver provato la [pulizia automatica](#backup-cleanup)) e un [ripristino](#restore) il cui risultato lo supererebbe. Il messaggio dice a quanto portare lo spazio totale e, se manca spazio sul disco, quanto altro ne serve libero. Non si fermano mai: transazioni, prezzi e database, i backup di un pannello di hosting e della riga di comando (la pulizia li segue) e un ripristino già confermato. Il limite non elimina nulla da solo.
- ⚠️ La barra avvisa che il limite è superato e suggerisce di eliminare backup o file, o di aumentare il limite. Diventa allora i tuoi dati, così nessuna parte resta fuori: una tacca *Limite 20 MB* mostra dove cade il limite, le righe rosse dopo di essa di quanto lo superi.
- 💬 **Un rifiuto è detto dove sei**: nella finestra di caricamento o di importazione, o nella scheda del backup. Un amministratore trova **Apri le impostazioni**, che apre **File** con il pannello **Avanzate** aperto; un utente legge quanto spazio liberare, o di chiedere a un amministratore. Con un limite impostato da chi ospita l'istanza, il messaggio dice di chiederlo a loro.
- 🔒 **Impostato nella configurazione del server**: con `LIBREFOLIO_STORAGE_LIMIT_MB` nell'ambiente, il suo valore è il limite, il campo è disattivato e una nota dice che è impostato da chi ospita l'istanza ([Variabili d'ambiente](configuration.md)). Un valore non intero viene ignorato e il campo funziona come sopra.
- 🧹 **Pulizia e barra lavorano insieme.** Di solito crescono i backup: la [pulizia automatica](#backup-cleanup) li tiene sotto controllo, e ogni backup eliminato in **Impostazioni › Amministrazione › Backup** o in **File › Backup** accorcia **Backup** nella barra. Vicino al limite, inizia da lì.

### 🗄️ Tenere copie fuori dal server {: #keep-copies }

`backups/` sta nella directory dei dati, sullo stesso disco: un backup lì non sopravvive alla perdita del disco. Un archivio scaricato da Impostazioni è già fuori dal server. Dalla riga di comando, scrivi gli archivi su un altro disco, un NAS o fuori sede con `--output`, a pianificazione.

**Nel `crontab` dell'utente che esegue LibreFolio** (`crontab -e`), installazione host, ogni notte alle 03:30:

```text
30 3 * * * cd /path/to/LibreFolio && pipenv run ./dev.py backup create --output /mnt/nas/librefolio/
```

**Con Docker**, aggiungi `-T` (cron non dà un terminale al comando). L'archivio finisce in una cartella propria di `LibreFolio-data/backups/`, dove la [pulizia automatica](#backup-cleanup), una volta impostata, impedisce che il disco si riempia: copialo altrove con il tuo strumento abituale.

```text
30 3 * * * cd /path/to/librefolio && docker compose exec -T librefolio python dev.py backup create
```

**Archivi [sicuri](#secure)**: aggiungi `--password-file` con un file che contiene la password (cron non ha un terminale su cui chiederla). Con Docker, il segreto dell'esempio sopra:

```text
30 3 * * * cd /path/to/librefolio && docker compose exec -T librefolio python dev.py backup create --password-file /run/secrets/backup_password
```

- 📁 La cartella di `--output` deve esistere quando il comando gira: monta prima il NAS. Un percorso che non è una cartella esistente diventa il nome dell'archivio.
- 🔢 Il comando stampa ciò che ha fatto ed esce con `1` quando l'archivio non è dove hai chiesto: conserva l'output, o fatti inviare un'email da cron.
- 🧭 cron ha un `PATH` ridotto: se non trova `pipenv` o `docker`, scrivi il percorso completo (`command -v pipenv` lo stampa).
- 🗑️ LibreFolio non elimina nessuno di questi archivi: rimuovi tu quelli vecchi. Conservane diversi, e l'ultimo creato prima di ogni aggiornamento.
- 🔑 Conserva anche una copia di `.env`, riservata quanto gli archivi: nessun archivio la contiene. E una copia di `secrets/`, a meno che i tuoi archivi non siano sicuri: uno in chiaro o [sigillato](backup_sealed.md#sealed) lascia fuori la chiave dell'istanza ([Cosa segue](#what-follows)).
- 🔏 Archivi notturni che il server stesso non può aprire, senza un file di password sul suo disco: [Ogni notte con cron](backup_sealed.md#sealed-cron), in Backup sigillati.

### 🧰 Backup con restic o Backrest {: #restic }

LibreFolio scrive l'archivio; uno strumento di backup lo porta fuori sede e ne tiene una cronologia. [restic](https://restic.net/) copia una cartella, cifrata, su S3, Backblaze B2, SFTP e altro, e dimentica le copie vecchie secondo una regola tua. [Backrest](https://github.com/garethgeorge/backrest) è un'interfaccia web per restic, con il proprio scheduler. Nessuno dei due serve a LibreFolio: leggono solo la cartella dei suoi archivi.

Ricetta notturna, installazione host. **In un file privato** (`chmod 600`), le variabili di restic:

```bash
# /etc/librefolio-restic.env: where the copies go, and the file with restic's password
RESTIC_REPOSITORY=sftp:backup@nas.example:/srv/restic/librefolio
RESTIC_PASSWORD_FILE=/root/.restic-librefolio-password
```

**Nel `crontab`**:

```text
30 3 * * * cd /path/to/LibreFolio && pipenv run ./dev.py backup create --output /var/backups/librefolio/ && . /etc/librefolio-restic.env && restic backup /var/backups/librefolio/ && restic forget --keep-daily 7 --keep-weekly 4 --prune && find /var/backups/librefolio/ -name 'librefolio-backup-*' -mtime +2 -delete
```

La riga crea l'archivio, invia la cartella, conserva sette copie giornaliere e quattro settimanali nel repository e rimuove gli archivi locali più vecchi di due giorni. Con Docker, crea l'archivio con il comando di [Tenere copie fuori dal server](#keep-copies) e dai a restic la cartella dell'host `LibreFolio-data/backups/`. Con Backrest, aggiungi un piano su quella cartella, con la sua pianificazione e conservazione, e lascia `backup create` in cron.

- 🔐 **La password di restic è una chiave per tutti i tuoi dati**: chiunque la possieda legge ogni copia. Riservata quanto la password di un [backup sicuro](#secure), con una copia altrove: perduta, il repository non si legge più.
- 🔑 **Nessuna chiave pubblica.** restic usa la sua password sia per scrivere sia per leggere: il server che invia le copie può anche leggerle. Se è un problema, invia [backup sigillati](backup_sealed.md#sealed-cron) (`--sealed`): solo la tua chiave privata li apre, né il server né la password di restic. Anche i [backup sicuri](#secure) (`--password-file`) funzionano, ma la loro password sta in un file sullo stesso server.
- 📦 **Poco da deduplicare.** Ogni archivio è compresso, uno sicuro è cifrato: restic conserva ogni archivio quasi per intero. Pianifica lo spazio del repository per le copie che tieni.
- 🧪 **Prova un ripristino prima di averne bisogno.** `restic restore latest --target /tmp/librefolio-check`, poi controlla l'archivio con [`backup restore --dry-run`](#check).

---

## 🔐 Backup sicuri {: #secure }

Un backup sicuro è l'archivio di un backup in chiaro, cifrato con una password scelta da te, in un file proprietario di LibreFolio: `.lfbk`. Lo crei da [Impostazioni › Amministrazione › Backup](#settings-backup) o con `backup create --encrypt` sulla [riga di comando](#command-line); ogni controllo e ripristino di questa pagina lo accetta, data la sua password.

- 🛡️ **Protegge il file a riposo.** Disco perso, portatile rubato, copia su cloud o NAS: senza la password non si legge nulla, né i dati né i nomi dei file. Un file modificato o troncato viene rilevato all'apertura e rifiutato.
- 👁️ **Non protegge da chi conosce la password**: legge tutto, dati di ogni utente e chiavi dei provider di dati. Dalla solo a chi può ripristinare il backup, mai insieme al file.
- 🗝️ **Porta la chiave dell'istanza**, se generata da LibreFolio (`secrets/instance.key`): le chiavi salvate dei provider di dati viaggiano con il backup, e il ripristino le ricifra con la chiave dell'installazione che lo riceve, che conserva la propria. Una chiave impostata da te (`LIBREFOLIO_INSTANCE_KEY`, `LIBREFOLIO_INSTANCE_KEY_FILE`) non esce mai.
- 🆘 **Una password perduta non si recupera.** LibreFolio non ne tiene copia, e nient'altro apre il file.
- ⏳ **Lento da indovinare.** La chiave del file deriva dalla password con scrypt: 32 MiB di memoria e circa un decimo di secondo per tentativo, nulla per un backup, lento per chi prova password una dopo l'altra. Da qui le regole: almeno 12 caratteri, una maiuscola, una minuscola, una cifra e un simbolo.
- 💽 **Sul server, durante la creazione,** l'archivio in chiaro viene scritto prima, nella cartella di lavoro del backup dentro `backups/`, che solo l'utente del server può aprire; viene rimosso appena scritto il `.lfbk`, e quando il backup fallisce. Dopo un'interruzione brusca (corrente, `kill -9`), il successivo avvio di LibreFolio rimuove ciò che è rimasto in chiaro, e il backup va creato di nuovo. Un controllo decifra il backup allo stesso modo: [Controllare un backup](#check).

Il design, per gli sviluppatori: [Backup sicuri (`.lfbk`)](../developer/architecture/security.md#secure-backups).

---

## 🔎 Controllare un backup {: #check }

Due comandi controllano un archivio senza cambiare nulla. **Nel terminale del server**, dentro il container con Docker: un archivio in `LibreFolio-data/backups/` è lì in `/app/backend/data/prod-docker/backups/`, e un backup [conservato](#kept-backups) sta nella sua cartella, come `/app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/`.

```bash
# Is the archive whole, and what does it hold?
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# Can this installation restore it? A restore tried on a copy
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip --dry-run

# A secure backup: the same commands ask its password first
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.lfbk
```

Installazione host: `pipenv run ./dev.py backup …` con il percorso dell'archivio sull'host.

| | `backup inspect` | `backup restore --dry-run` |
| --- | --- | --- |
| Risponde | Se l'archivio è integro: dimensione e SHA-256 di ogni voce, confrontati con il manifest | Se questa installazione può ripristinarlo: archivio decompresso in una copia, aggiornato e controllato |
| Mostra | Chi ha creato l'archivio e quando, revisione del database, righe e tabelle, file, se la chiave dell'istanza è inclusa | Lo stesso, più: le migrazioni che un ripristino applicherebbe, i totali del libro mastro della copia confrontati con quelli dell'archivio, le chiavi dei provider ricifrate con la chiave di questa installazione o da inserire di nuovo, gli amministratori con cui accederesti |
| Richiede | Qualsiasi LibreFolio, server in esecuzione o fermo; nessuna directory dei dati, tranne per un backup sicuro, che decifra lì | L'installazione che riceverebbe l'archivio (il server può restare attivo) e spazio libero nella sua directory dei dati: archivio decompresso + il doppio del suo database + 64 MB |
| Termina con | `✅ Every entry matches the manifest` | `✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.` |

- 🔐 **Backup sicuro** (`.lfbk`): entrambi chiedono prima la password, al terminale o con `--password-file FILE` / `--password-stdin`, come `backup create`. Lo decifrano in una cartella privata della directory dei dati, che solo l'utente del server può aprire, e rimuovono l'archivio decifrato alla fine: serve spazio anche per quello, circa quanto il `.lfbk`. Dopo un'interruzione brusca (corrente, `kill -9`), il successivo avvio di LibreFolio rimuove ciò che è rimasto in chiaro: subito l'archivio di `--dry-run`, dopo un'ora la cartella di `inspect`, che anche il successivo `inspect` rimuove. Il report aggiunge `Secure backup: decrypted with its password`. Password errata: `❌ The password does not open this backup (wrong_password)`. Un `.zip` ignora le due opzioni.
- 🗝️ `--dry-run` dice cosa succede alle chiavi salvate dei provider di dati, per qualsiasi archivio: `Saved provider keys: 2 re-encrypted with this instance's key` se il backup porta la chiave che le ha cifrate, `⚠️ 1 saved provider key cannot be read with this instance's key: enter it again after the restore` per quelle che non legge ([Cosa segue](#what-follows)).
- 🔁 Esegui `inspect` ogni tanto sulle copie che conservi, e `--dry-run` prima di uno spostamento, sull'installazione che riceverà l'archivio.
- 🖱️ **Ripristina un archivio**, in Impostazioni › Amministrazione › Backup, fa lo stesso controllo di `--dry-run` su un archivio dal tuo computer: leggi il report, poi **Scarta questo archivio**, e nulla cambia ([Ripristinare da Impostazioni › Amministrazione › Backup](#restore-settings)).
- ❌ Un rifiuto termina con un codice tra parentesi: [Quando qualcosa va storto](backup_moving.md#troubleshooting). Elenchi completi in «Controllare un archivio» e «Provare un ripristino su una copia», in [Strumenti di amministrazione CLI](cli_tools.md).

---

## ♻️ Ripristinare su questa installazione {: #restore }

Un ripristino sostituisce i dati dell'installazione con quelli dell'archivio: database e file, per ogni utente. Due vie, che controllano prima l'archivio su una copia e non cambiano nulla finché non confermi; il successivo avvio di LibreFolio applica il ripristino:

| Dove | Chi | Dopo la conferma |
| --- | --- | --- |
| **Impostazioni › Amministrazione › Backup**, nell'app | Amministratori | LibreFolio si ferma subito, per quell'avvio |
| **Terminale sul server**: `backup restore` | Chi ha accesso al server | Lo riavvii quando preferisci |

Su un'istanza che qualcuno ospita per te, la riga di comando è sul loro server: usa Impostazioni › Amministrazione › Backup, o chiedi a loro.

### 🖱️ Ripristinare da Impostazioni › Amministrazione › Backup {: #restore-settings }

1. **Scegli l'archivio.** In **Impostazioni › Amministrazione › Backup**, sotto **Esegui il backup dell'istanza**, la scheda **Ripristina un archivio** ricorda che un ripristino sostituisce i dati di ogni utente: se potresti volerli recuperare, [crea prima un backup](#settings-backup). **Scegli un archivio…** → un `.zip` o un `.lfbk` sicuro creato da LibreFolio, qui o altrove. Un `.zip` parte subito verso il server, con una barra di avanzamento: **Interrompi invio** lo ferma, nulla resta.

    **Oppure prendi un backup che il server conserva**: **Ripristina** sulla sua riga nell'elenco dei [backup conservati sul server](#kept-backups), qui o in **File › Backup**. Chiede prima conferma, poi il server prende quel backup come archivio, senza download né caricamento, e la scheda prosegue dal passo successivo. Un backup sigillato di un pannello di hosting si apre solo con la chiave privata dei suoi destinatari: qui non si ripristina.

2. **Digita la password**, per un backup sicuro: la scheda la chiede prima di inviare qualcosa (*Un backup sicuro: digita la password con cui è stato creato.*). Compila **Password del backup** e fai clic su **Controlla il backup**: l'archivio viene inviato, e la password va con la richiesta che avvia il controllo, che la prova subito. Password errata → *Password errata, o il file è stato modificato: digita di nuovo la password.*; l'archivio resta sul server e il tentativo seguente non lo invia di nuovo. **Annulla** dimentica il file.
3. **Lascia che venga controllato.** Il server controlla l'archivio su una copia, come `backup restore --dry-run` ([Controllare un backup](#check)): *Decifratura del backup* (solo sicuro), *Controllo dell'archivio*, *Decompressione su una copia*, *Aggiornamento del database della copia*, *Verifica della copia*. Nulla cambia finché non confermi. **Interrompi il controllo** lo scarta (un controllo ancora in esecuzione viene scartato appena termina).
4. **Leggi il report**, nella finestra **Cosa farebbe questo ripristino** (chiusa, **Leggi il report** la riapre). Cosa dice: sotto.
5. **Digita la parola.** La finestra mostra una parola reale, a caso, da 6 a 10 lettere nella lingua dell'interfaccia. Digitala a mano nel campo sotto: il campo rifiuta testo incollato e trascinato. La parola protegge da un clic affrettato, non da un amministratore: l'API e la riga di comando ne fanno a meno. Per un archivio che non può essere ripristinato, non compaiono né la parola né **Ripristina e riavvia**: solo il pulsante che lo scarta.
6. **Ripristina e riavvia.** Conferma il ripristino e ferma subito LibreFolio, per tutti. Una finestra copre la pagina, **LibreFolio si sta riavviando**: *Il suo avvio applica il ripristino. Questa pagina attende che torni.* LibreFolio non si riavvia da solo: lo fa chi lo supervisiona ([Chi riavvia LibreFolio](#supervisors)), e quell'avvio applica il ripristino ([Cosa fa il prossimo avvio](#next-start)).

#### 📋 Cosa dice il report

- chi ha creato l'archivio, con quale versione di LibreFolio e quando;
- il database: alla versione di questo LibreFolio, o portato a essa sulla copia, con le migrazioni elencate e le correzioni applicate alla copia;
- i file e la loro dimensione, la dimensione del database e le tabelle le cui righe sono cambiate con l'aggiornamento; e una barra di cosa contiene il backup: il database, i file caricati, i report del broker e gli altri file;
- se il backup porta la chiave dell'istanza da cui proviene: in ogni caso, questo LibreFolio conserva la propria;
- le chiavi salvate dei provider di dati: quante ricifrate con la chiave di questo LibreFolio (*2 chiavi salvate di provider di dati sono ricifrate con la chiave di questa istanza.*) e quante illeggibili, da inserire di nuovo dopo il ripristino (*1 chiave salvata di un provider di dati non può essere letta con la chiave di questa istanza: inseriscila di nuovo dopo il ripristino.*) ([Cosa segue](#what-follows));
- i totali del libro mastro: uguali a quando è stato creato il backup, diversi sulle righe elencate ([come leggerli](backup_moving.md#check-refused)), non registrati, registrati da un'altra versione del metodo o illeggibili;
- gli amministratori del backup, con *Dopo il ripristino accedi con uno di loro, con la password di allora; ogni sessione aperta ora termina.*
- *Gli inviti e i link inviati prima del ripristino saranno scaduti: inviali di nuovo se necessario.*
- ogni amministratore con l'immagine del suo account nel backup, e **Verifica una password prima di ripristinare**: scegline uno, digita la sua password e fai clic su **Verifica**. Risposta: *Con questa password accederai dopo il ripristino.*, oppure *Non è la sua password.* La password viene confrontata solo con il backup: mai conservata, scritta nel log o rimandata indietro;
- gli avvisi, che lasciano proseguire, e i blocchi, che vietano il ripristino: un backup senza un amministratore attivo, e un ripristino che supererebbe il [limite di spazio](#space-used), con la dimensione a cui portarlo; un controllo così restituisce subito il suo spazio, e il report resta a schermo finché non lo chiudi;
- fino a quando viene conservato l'archivio caricato: 24 ore dopo il controllo.

Sotto il report: **Scarta questo archivio** scarta il controllo e la sua copia, nulla viene ripristinato. **Ci penso dopo** chiude la finestra e tiene il controllo: la scheda mostra *Un ripristino attende la tua decisione fino al …*, con **Riprendi**, che riapre lo stesso report, e **Scarta**, da qualsiasi scheda o dispositivo di un amministratore.

#### 🏁 Com'è andata

Quando LibreFolio risponde di nuovo, la pagina mostra l'esito:

| Esito | Cosa vedi | Cosa fare |
| --- | --- | --- |
| ✅ **Ha funzionato** | La pagina di accesso, senza messaggi: ogni sessione è terminata. Un ripristino riuscito non lascia righe sulla scheda | Accedi con un amministratore del backup, con la password che aveva quando è stato creato: la prima pagina mostra i dati ripristinati |
| ↩️ **Non è andato a buon fine** | **Il ripristino non è andato a buon fine**, con il motivo. *I dati sono come prima: …* = rollback eseguito, la scheda dice quando e perché. *LibreFolio si è riavviato, ma il ripristino non è stato applicato.* = un avvio lo ha lasciato in attesa, per il motivo che segue | **Torna a Backup** riporta alla scheda (dopo la pagina di accesso se il riavvio ha chiuso la tua sessione, o alla pagina di blocco su un'istanza bloccata nel frattempo). Poi [Cosa dice Impostazioni › Amministrazione › Backup](backup_moving.md#restore-settings-problems) |
| ⏳ **Ci vuole molto** | Dopo un minuto senza server: *LibreFolio non è ancora tornato. Se nulla lo riavvia da solo, avvialo tu: il ripristino viene applicato a quell'avvio.* Se LibreFolio non si ferma affatto, dopo un minuto: *LibreFolio non si è fermato. Se non si riavvia da solo, riavvialo tu: il ripristino viene applicato a quell'avvio.*, con **Torna a Backup** | [Cosa dice Impostazioni › Amministrazione › Backup](backup_moving.md#restore-settings-problems) |

La pagina legge l'esito con un ticket monouso ricevuto dalla richiesta di riavvio, valido un'ora e tenuto solo nella memoria della scheda: non serve una sessione. Senza ticket (pagina ricaricata, più di un'ora di attesa, riavvio dalla riga di comando invece che da qui) la pagina si affida alla sessione: senza `JWT_SECRET`, che disconnette tutti a ogni avvio ([Mantenere gli utenti connessi dopo un riavvio](index.md#session-persistence)), va alla pagina di accesso qualunque sia l'esito, e **Impostazioni › Amministrazione › Backup** dice, una volta entrato, se il ripristino è andato a buon fine.

#### ⏳ Un ripristino in attesa

Un ripristino confermato e non ancora applicato prende il posto di **Scegli un archivio…**: uno confermato dalla riga di comando, o qui quando LibreFolio non si è fermato o un avvio lo ha lasciato in attesa. La scheda dice **Un ripristino attende il prossimo avvio di LibreFolio**, con il backup, chi lo ha confermato (`cli` dalla riga di comando) e quando, il motivo se un avvio lo ha lasciato in attesa, e *Il riavvio ferma LibreFolio per tutti; il suo prossimo avvio applica il ripristino e termina ogni sessione.*

| Pulsante | Cosa fa |
| --- | --- |
| **Riavvia ora e ripristina** | Ferma LibreFolio, come **Ripristina e riavvia**; la pagina lo attende allo stesso modo |
| **Annulla il ripristino** | Lo scarta con la sua copia controllata, come `backup pending --cancel`: i dati restano come sono |

Mentre un avvio applica il ripristino, la scheda dice *Un avvio di LibreFolio sta applicando il ripristino.*

Utile sapere:

- 👑 Solo gli amministratori hanno la scheda. Un ripristino alla volta: un archivio viene controllato alla volta, ovunque sia iniziato il controllo, qui, in un'altra scheda o sulla riga di comando (*Un altro archivio è in fase di controllo: riprova quando termina.*).
- 📏 Se l'installazione limita la dimensione degli archivi (`LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`, nessuno per impostazione predefinita), la scheda lo dice (*Archivi fino a 500 MB.*) e rifiuta un file più grande prima di inviare qualsiasi cosa: [Il limite di caricamento di un ripristino](#restore-upload-limit).
- 💽 Il disco della directory dei dati deve avere spazio per l'archivio, per la sua copia durante il controllo e, per un backup sicuro, per l'archivio decifrato: quanto, in [Controllare un backup](#check).
- 📦 Durante il controllo, l'archivio occupa sul server la sua dimensione, che la scheda dice mentre viene caricato, più la sua versione aperta; entrambi contano nel limite di spazio finché il ripristino non finisce o viene scartato.
- 🔑 La password di un backup sicuro va al server solo con la richiesta che avvia il controllo, che la prova subito: mai memorizzata, scritta nel log o restituita. Il campo si svuota appena la invii.
- 🔄 Un ricaricamento della pagina continua a seguire il controllo e il report, e qualsiasi altra scheda o dispositivo di un amministratore lo riprende dalla scheda Backup. L'archivio caricato è conservato 24 ore: dopo, la conferma risponde *Il controllo è troppo vecchio: controlla di nuovo l'archivio.*
- 🚪 Il ripristino termina ogni sessione, tutti accedono di nuovo con un account del backup, e i link inviati prima smettono di funzionare: [Cosa fa il prossimo avvio](#next-start).
- ❌ Un caricamento, un controllo o una conferma rifiutati, o un server che non risponde, compaiono sulla scheda con il motivo. **Riprova** rilegge lo stato del ripristino; per inviare di nuovo un archivio, **Scegli un archivio…**. Il controllo rifiuta gli stessi archivi della riga di comando: [Il controllo rifiuta l'archivio](backup_moving.md#check-refused).
- 🖥️ Se nulla riavvia LibreFolio, come un'installazione host avviata a mano, [avvia il server](cli_tools.md#start-the-server) tu stesso una volta che si è fermato: la pagina lo attende.

### 📤 Il limite di caricamento di un ripristino {: #restore-upload-limit }

Un amministratore carica l'archivio da Impostazioni › Amministrazione › Backup ([Ripristinare da Impostazioni › Amministrazione › Backup](backup_restore.md#restore-settings)), tramite `PUT /api/v1/backup/restore/upload`, e l'istanza lo controlla su una copia, come `backup restore --dry-run` sulla [riga di comando](cli_tools.md). Due variabili limitano quanto può essere grande.

**`LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`** limita l'archivio così com'è inviato, compresso:

| Valore | Archivio più grande accettato |
| --- | --- |
| Non impostato, o vuoto | Nessun limite |
| `0` | Nessun limite |
| Un numero intero, come `2048` | Quel numero di megabyte, da 1024 × 1024 byte ciascuno |

1. **In `.env`**, o nell'ambiente del container:

    ```bash
    LIBREFOLIO_BACKUP_MAX_UPLOAD_MB=2048
    ```

2. Riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`.
3. **Nella configurazione del proxy** davanti a LibreFolio, lascia passare almeno altrettanto: Nginx con `client_max_body_size`, predefinito solo 1 MB (`client_max_body_size 2048m;` corrisponde all'esempio), e la tua CDN, se limita la dimensione di una richiesta.

Il limite in vigore si legge in `upload_limit_mb` di `GET /api/v1/backup/restore/status`: `0` nessun limite, `null` valore illeggibile. Impostazioni › Amministrazione › Backup lo mostra sulla scheda di ripristino (*Archivi fino a 500 MB.*) e rifiuta un file più grande prima di inviarlo.

| Il caricamento risponde | Codice | Quando |
| --- | --- | --- |
| `413` | `backup_too_large`, con il limite in `limit_mb` | Archivio oltre il limite: prima di scrivere qualcosa se la richiesta annuncia la sua dimensione, altrimenti appena il caricamento supera il limite. Nulla viene conservato |
| `413` senza `backup_too_large` | — | Viene dal proxy, non da LibreFolio |
| `503` | `backup_upload_unavailable` | Valore non intero (`500MB`, `-1`): il server non si ferma, ma il log di avvio ha già `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB cannot be used: …` (`check` è `backup.upload_limit`) e ogni caricamento aggiunge al log un errore che nomina la variabile: `The upload limit of a restore cannot be read` |
| `507` | `backup_no_space` | Il disco della directory dei dati non ha spazio per l'archivio e, durante il controllo, per la sua copia decompressa (quanto: «Provare un ripristino su una copia» in [Strumenti di amministrazione CLI](cli_tools.md)); anche se il disco si dichiara pieno solo alla fine del file, come un file system di rete o una quota. Il controllo ha un proprio codice, `no_space`: `507` se non può nemmeno iniziare, rifiuto dell'archivio una volta avviato |
| `500` | `backup_upload_failed` | Il caricamento non può essere scritto per un altro motivo; il log ha la causa |

**`LIBREFOLIO_BACKUP_MAX_RESTORE_MB`** limita la dimensione decompressa, secondo le dimensioni dichiarate dal manifest, prima che il controllo decomprima qualsiasi cosa: uno zip può decomprimersi in molto più della sua dimensione, sul disco della directory dei dati.

| Valore | Dimensione massima decompressa di un archivio |
| --- | --- |
| Non impostato, o vuoto | Nessun limite |
| `0` | Nessun limite |
| Un numero intero, come `16384` | Quel numero di megabyte, da 1024 × 1024 byte ciascuno |

- Un archivio oltre il limite è rifiutato prima di decomprimere qualcosa: il controllo fallisce con il codice `unpacked_too_large`, nulla della copia resta. Un archivio sicuro viene prima decifrato (circa la sua dimensione), poi misurato allo stesso modo.
- Un valore che imposti vince sempre, `0` incluso. `backup restore` sulla riga di comando segue lo stesso limite; chi esegue il server lo solleva per un singolo comando con `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` davanti a esso («Provare un ripristino su una copia» in [Strumenti di amministrazione CLI](cli_tools.md)).
- Un valore non intero non ferma il server: il log di avvio ha già `LIBREFOLIO_BACKUP_MAX_RESTORE_MB cannot be used: …` (`check` è `backup.restore_limit`), poi ogni controllo, `POST /api/v1/backup/restore/stage`, risponde `503` con il codice `backup_restore_unavailable`, l'archivio viene conservato e il log ha un errore.

### ⌨️ Ripristinare dalla riga di comando {: #restore-command }

**Nel terminale del server**, dove gira LibreFolio: nel container con Docker.

```bash
# 1. Check the archive on a copy, read the report, then type "restore" to confirm
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# 2. Restart LibreFolio: its next start applies the restore
docker compose restart librefolio

# 3. See how it went
docker compose exec librefolio python dev.py backup pending
```

- 🧪 Il passo 1 fa lo stesso controllo di `--dry-run`, mostra lo stesso report, poi chiede di digitare `restore`. Nulla cambia ancora: LibreFolio continua sui suoi dati, il ripristino attende il prossimo avvio.
- 🖥️ Installazione host: `pipenv run ./dev.py backup restore <archive>`, poi ferma l'intero server e [avvialo](cli_tools.md#start-the-server) di nuovo: mai un solo worker.
- ⏳ Con LibreFolio di nuovo attivo, `backup pending` dice `✅ The last restore was applied on …`. Prima del riavvio, `backup pending --cancel` scarta il ripristino in attesa, con la sua copia controllata.
- 🤖 In uno script, `--yes` conferma senza chiedere.
- 🔐 Backup sicuro (`.lfbk`): `backup restore` chiede la password prima del controllo, o la legge con `--password-file` o `--password-stdin`, come `inspect` ([Controllare un backup](#check)): in uno script, una delle due insieme a `--yes`.
- 📖 Altro: «Ripristinare un archivio» e «Seguire o annullare un ripristino» in [Strumenti di amministrazione CLI](cli_tools.md).

### 🔄 Cosa fa il prossimo avvio {: #next-start }

- 🔀 **Lo scambio.** Il database e le tre cartelle dei file cambiano posto con la copia controllata, in un istante qualunque sia la dimensione. `secrets/`, `logs/`, `scheduler_state.json` e `backups/` restano come sono: l'installazione conserva la propria chiave dell'istanza. La chiave portata da un backup sicuro non viene mai messa al suo posto: il controllo ha già ricifrato le chiavi dei provider di dati sulla copia, con la chiave di questa installazione.
- 🚪 **Ogni sessione termina.** Tutti accedono di nuovo, su ogni dispositivo, con un account del backup e la password che aveva allora.
- 🔗 **I link monouso vengono revocati.** Nessun link di invito, reimpostazione password o verifica email inviato prima funziona più, nemmeno quelli nel backup: inviane di nuovi. Un account ancora in attesa della verifica email smette di attendere: quando il proprietario chiede alla pagina di accesso un nuovo link, la pagina risponde che l'account è disabilitato. Un amministratore lo riattiva con **Riattiva** ([Cosa fa ogni azione](users.md#actions)) o lo elimina ([Eliminare un account](users.md#delete)) perché il proprietario si registri di nuovo.
- ✅ **Il primo avvio deve completarsi.** Solo allora il ripristino viene conservato e i dati precedenti rimossi. Se fallisce (migrazione non riuscita, file danneggiato), l'avvio successivo rimette da solo i dati precedenti, e `backup pending`, come la scheda in Impostazioni › Amministrazione › Backup, dice che è stato eseguito il rollback, con il motivo.

### 🔌 Chi riavvia LibreFolio {: #supervisors }

Sei tu ad avviare il ripristino: con il riavvio della riga di comando, o con **Ripristina e riavvia** in Impostazioni › Amministrazione › Backup, che ferma LibreFolio. Nulla in LibreFolio riavvia il server: lo fa chi lo supervisiona, dopo quella fermata e dopo un primo avvio fallito, così che l'avvio successivo riporti indietro i dati.

| Supervisore | Riavvia LibreFolio da solo |
| --- | --- |
| Docker Compose | Con `restart: unless-stopped`, in entrambi i file compose forniti da LibreFolio |
| systemd | Con `Restart=always` |
| Nessuno | No: avvia LibreFolio tu stesso, e il ripristino, o il ritorno indietro, avviene a quell'avvio |

**Ripristina e riavvia** ferma LibreFolio in modo pulito: una policy che riavvia solo dopo un errore, come `on-failure`, non lo avvia dopo quella fermata.

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
