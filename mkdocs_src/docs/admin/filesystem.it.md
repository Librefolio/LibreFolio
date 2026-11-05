# 📂 Struttura del filesystem

LibreFolio conserva tutto ciò che memorizza in un'unica **directory dei dati**: il database, i file caricati, i report del broker, i log e la chiave dell'istanza. La sua struttura è tutto ciò che serve sapere per i backup e la manutenzione.

| Installazione | Directory dei dati |
| --- | --- |
| Host (Pipenv) | `backend/data/prod/` nella cartella del progetto, oppure il percorso in `LIBREFOLIO_DATA_DIR` |
| Docker Compose | `LibreFolio-data/` accanto a `docker-compose.yml` (`/app/backend/data/prod-docker` all'interno del container) |

---

## 🗂️ Struttura delle directory

```text
backend/data/
├── 📂 prod/                          # Production data (default)
│   ├── 🗃️ sqlite/
│   │   └── 📄 app.db                 # Main SQLite database (WAL mode)
│   ├── 🖼️ custom-uploads/            # Files uploaded in the app
│   ├── 📊 broker_reports/
│   │   ├── 📥 uploaded/              # Reports waiting to be read
│   │   ├── ✅ parsed/                # Reports read successfully
│   │   └── ❌ failed/                # Reports that could not be read
│   ├── 📝 logs/                      # Application log files
│   ├── 💾 backups/                   # Backups kept by LibreFolio, one folder each
│   ├── 🎭 scenario_catalog/          # Optional: your own stress scenarios
│   ├── 🗄️ cache/                     # Safe to delete: PDF preview fonts, fetched again
│   ├── 🔐 secrets/                   # Created when LibreFolio first needs the key
│   │   └── 🔑 instance.key           # The instance key: back it up, never change it
│   └── 📋 scheduler_state.json       # Scheduled syncs: last run, pending retry
│
└── 🧪 test/                          # Test data (completely isolated)
    ├── 🗃️ sqlite/app.db
    ├── 🖼️ custom-uploads/
    ├── 📊 broker_reports/
    └── 📝 logs/
```

---

## 📖 Cosa contiene ogni directory

### 🗃️ `sqlite/`

- 📄 `app.db` contiene tutti i dati strutturati: utenti, broker, transazioni, asset, prezzi, tassi di cambio e impostazioni.
- 📎 `app.db-wal` e `app.db-shm` sono i file di lavoro di SQLite (modalità WAL), previsti mentre il server è in esecuzione: non copiare mai `app.db` da solo mentre il server è attivo.
- 🔒 `app.db.post-migration.lock` è un file vuoto usato all'avvio: lascialo al suo posto. Un file chiamato `app.db.pre-<fix>-<UTC time>.bak` è una copia conservata dopo una [correzione post-migrazione](cli_tools.md#post-migration-fixes) fallita: eliminalo quando non ti serve più.

### 🖼️ `custom-uploads/`

File caricati nell'app, come quelli della pagina **Files**, e gli avatar predefiniti. Ogni file ha un nome casuale e un file `.json` accanto che lo descrive: mantieni le coppie insieme.

### 📊 `broker_reports/`

I report del broker caricati per l'importazione, in una cartella `broker_<id>/` per ogni broker:

- **📥 `uploaded/`** — in attesa di essere letti
- **✅ `parsed/`** — letti con successo
- **❌ `failed/`** — non è stato possibile leggerli, conservati per permetterti di verificare il motivo

Un report passa da `uploaded/` a `parsed/` o `failed/`, quindi il suo file originale si trova sempre in una delle tre cartelle.

### 📝 `logs/`

- 📄 `librefolio.log` contiene un record JSON per riga; il server stampa il log anche sulla console.
- 🗓️ Ogni lunedì (UTC) il file viene archiviato e compresso (`.gz`); vengono conservati gli ultimi 52 archivi, un anno.
- 🎚️ `LOG_LEVEL` in `.env` stabilisce quanto viene scritto (predefinito `INFO`).

??? info "📶 Livelli di log — cosa registra ciascuno"

    Ogni livello registra anche tutti quelli più gravi.

    | Livello | Cosa cattura |
    |-------|-----------------|
    | 🔬 `TRACE` | Dati dettagliati ad alta frequenza: singoli tassi di cambio elaborati, punti di prezzo per asset |
    | 🐛 `DEBUG` | Dettagli interni operativi: quale provider è stato usato, risultati intermedi, decisioni algoritmiche |
    | ℹ️ `INFO` *(predefinito)* | Operazioni significative dell'utente: sincronizzazione completata, importazione, login, risorsa creata/eliminata |
    | ⚠️ `WARNING` | Anomalie recuperabili: fallback attivato, dati opzionali mancanti, modalità degradata |
    | ❌ `ERROR` | Errori gestiti: operazioni fallite, corruzione dei dati, provider irraggiungibile |
    | 💀 `CRITICAL` | Errori fatali che arrestano il processo |

    - **Produzione**: `LOG_LEVEL=INFO` — segnale pulito, senza rumore
    - **Risoluzione dei problemi**: `LOG_LEVEL=DEBUG` — vedi cosa sta decidendo il sistema
    - **Debug approfondito di FX/prezzi**: `LOG_LEVEL=TRACE` — vedi ogni singolo punto dati

**Leggere il log.** Ogni riga scritta da LibreFolio è un oggetto JSON: il messaggio è in `event`, il livello in `level`, l'ora (UTC) in `timestamp` e il traceback di un errore in `exception`. Ogni riga scritta mentre il server risponde a una richiesta porta il `request_id` di quella richiesta. Quando qualcosa fallisce, lo stesso id arriva al browser: nell'header `X-Request-Id` della risposta, nel corpo di un errore del server e nella riga `[API]` che l'app web scrive nella console del browser (strumenti di sviluppo, **Console**). Chiedi quell'id all'utente che segnala l'errore, poi leggi le sue righe con [jq](https://jqlang.org/), dalla cartella `logs/`:

```bash
# Every line of one request
jq -cR 'fromjson? | select(.request_id == "3f2a9c0d41b7e865")' librefolio.log

# The errors, each followed by its traceback
jq -rR 'fromjson? | select(.level == "ERROR" or .level == "CRITICAL") | "\(.timestamp) \(.request_id // "-") \(.event)", (.exception // empty)' librefolio.log
```

`fromjson?` salta le poche righe che non sono JSON, come quelle delle librerie utilizzate da LibreFolio. Per una settimana archiviata, decomprimila al volo: `gzip -dc librefolio.log.2026-10-12.gz | jq -cR …`. Una riga relativa a una richiesta fallita indica il suo metodo e il suo percorso, mai la sua query string, i suoi header o il suo corpo.

### 🗄️ `cache/`

Copie che LibreFolio può scaricare di nuovo. Attualmente contiene `pdf-fonts/`, i font cinesi, giapponesi e coreani di cui l'anteprima PDF ha bisogno quando il PDF li utilizza, conservati dopo il primo download: vedi [La Content-Security-Policy](configuration_security.md#csp). Eliminarla non fa perdere nulla e non fa parte di un [backup](backup_restore.md).

### 🔐 `secrets/`

- 🔑 `instance.key` contiene la [chiave dell'istanza](configuration_secrets.md#instance-key), il segreto da cui LibreFolio deriva le proprie chiavi di crittografia. LibreFolio la crea la prima volta che ha bisogno della chiave. Dopo, un `instance.key` mancante appare come un primo utilizzo: LibreFolio crea una nuova chiave e ciò che era stato crittografato con quella vecchia non può più essere letto.
- 🔒 Solo l'utente che esegue LibreFolio può aprire la cartella e il file: la cartella è `0700`, il file `0600`. Mantienili così e mantienili di proprietà di quell'utente: altrimenti il [log di avvio](configuration_security.md#startup-checks) presenta un avviso, oppure un errore quando è LibreFolio stesso a non poterli aprire.
- ⛔ Non modificare, sostituire o eliminare mai la `instance.key` in uso: ciò che è stato crittografato con essa non potrebbe più essere letto. Se è danneggiata, o se LibreFolio ha già sostituito una chiave perduta con una nuova, arresta LibreFolio e rimetti la tua copia prima che qualcuno inserisca di nuovo un segreto di un plugin: vedi [La chiave dell'istanza](configuration_secrets.md#instance-key).
- ♻️ Quando ripristini la directory dei dati, rimetti a posto `secrets/` insieme ad essa prima di avviare di nuovo LibreFolio. Non avviare mai LibreFolio su dati ripristinati senza il suo `secrets/`.
- ⚙️ Quando la chiave proviene da `LIBREFOLIO_INSTANCE_KEY` o `LIBREFOLIO_INSTANCE_KEY_FILE`, LibreFolio non usa questa cartella.

🔗 Per gli sviluppatori: [Directory dei dati su disco](../developer/architecture/database/index.md#data-directory) — ogni file, il suo formato e il codice che lo scrive, `scenario_catalog/` incluso.

---

## 🌍 Variabili d'ambiente

- `LIBREFOLIO_DATA_DIR` sposta la directory dei dati di produzione, e `LIBREFOLIO_TEST_DATA_DIR` quella di test. Un percorso relativo parte dalla cartella del progetto.
- Con Docker Compose il percorso all'interno del container è fisso: per tenere i dati altrove sull'host, modifica il lato sinistro del volume `./LibreFolio-data:/app/backend/data/prod-docker` in `docker-compose.yml`.

Le altre variabili sono descritte, e il file `.env` è descritto, in [Configurazione](configuration.md).

---

## 💾 Backup

Il modo consigliato è un archivio di backup, creato mentre LibreFolio continua a funzionare: vedi [Backup, ripristino e spostamento dell'istanza](backup_restore.md). Dalla riga di comando, `./dev.py backup create` scrive un archivio zip del database, dei file caricati, dei report del broker e dei tuoi scenari di stress, per impostazione predefinita in una cartella dedicata all'interno della cartella `backups/` della directory dei dati: vedi [Eseguire il backup dell'istanza](cli_backup.md#backup), e [Eseguire il backup con Docker](cli_backup.md#backup-docker) per il comando nel container. Esclude `secrets/`, che salvi separatamente come spiegato in [Cosa includere nel backup](#what-to-back-up), a meno che tu non renda [sicuro](backup_restore.md#secure) l'archivio (`--encrypt`): un archivio sicuro contiene la chiave dell'istanza generata da LibreFolio. Copiare manualmente la directory dei dati, come descritto di seguito, è l'alternativa.

### 📦 Backup semplice

Il modo più semplice per eseguire il backup di LibreFolio è copiare l'intera directory dei dati:

```bash
# Stop the server first (to ensure database consistency)
cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
```

Questa copia, come quella Docker riportata di seguito, comprende anche `backups/`, con ogni backup che LibreFolio vi conserva ([Backup conservati sul server](backup_restore.md#kept-backups)): elimina prima quelli che non ti servono più, imposta la [pulizia automatica](backup_restore.md#backup-cleanup), oppure lascia fuori la cartella.

### 🐳 Backup con Docker

Con Docker Compose, la directory dei dati è la cartella `LibreFolio-data/` sull'host, quindi non serve alcun comando Docker di copia. Ferma il container per ottenere una copia coerente:

```bash
docker compose stop librefolio
cp -r ./LibreFolio-data/ /path/to/backup/librefolio-$(date +%Y%m%d)/
docker compose start librefolio
```

??? tip "🔄 Eseguire il backup del database senza fermare il server"

    Il backup online di SQLite crea una copia coerente mentre il server è in esecuzione. Richiede lo strumento `sqlite3`:

    ```bash
    sqlite3 backend/data/prod/sqlite/app.db ".backup '/path/to/backup/app.db'"
    ```

    Con Docker, il database è `./LibreFolio-data/sqlite/app.db`. Questo comando copia solo il database: copia le cartelle elencate sotto come al solito.

### ✅ Cosa includere nel backup {: #what-to-back-up }

Come minimo, esegui il backup di:

1. **`sqlite/app.db`** — Tutti i tuoi dati (utenti, transazioni, impostazioni, tassi di cambio)
2. **`custom-uploads/`** — File caricati dall'utente (avatar, documenti)
3. **`broker_reports/`** — I report originali del broker, in caso tu debba importarli di nuovo
4. **`scenario_catalog/`** — I tuoi scenari di stress, se ne hai aggiunti
5. **`secrets/`** — La chiave dell'istanza, se LibreFolio l'ha creata

!!! warning "🔑 Mantieni `secrets/` insieme ai dati e mantienila privata"

    Esegui il backup di `secrets/` insieme al database e conserva le copie private quanto il database stesso. Non modificare né eliminare mai la chiave dell'istanza una volta in uso: ciò che è stato crittografato con essa non potrebbe più essere letto. Quando ripristini, rimetti `secrets/` insieme ai dati prima di avviare LibreFolio.

    Solo l'utente che esegue LibreFolio può aprire `secrets/`. Lo stesso vale per `backups/`, creata al primo backup, e `.restore/`, creata la prima volta che un archivio viene verificato per un ripristino: LibreFolio le crea entrambe come `0700`, e gli archivi in `backups/` come `0600`. Se `cp` segnala `Permission denied` in una di esse, per esempio con Docker quando il tuo utente host non è quello del container, copia come root e mantieni i permessi: `sudo cp -a`. Anche eliminare un vecchio archivio da `backups/` fallisce allo stesso modo: usa `sudo rm`.

Se lo spazio è limitato, conserva almeno `sqlite/app.db`, che contiene tutti i dati strutturati, e la piccola cartella `secrets/`: i file e i report possono essere caricati di nuovo se li hai ancora.
