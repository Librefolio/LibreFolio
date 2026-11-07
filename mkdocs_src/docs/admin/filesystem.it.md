# 📂 Struttura del filesystem

Tutto ciò che LibreFolio memorizza sta in un'unica **directory dei dati**: database, file caricati, report dei broker, log e chiave dell'istanza.
Conoscerla basta per backup e manutenzione.

**Dove si trova.** Nel resto della pagina, `<data>` è questa cartella:

| Installazione | `<data>` sull'host | `<data>` dentro il container |
| --- | --- | --- |
| Host (Pipenv) | `backend/data/prod/` nella cartella del progetto, oppure il percorso in `LIBREFOLIO_DATA_DIR` | — |
| Docker Compose | `LibreFolio-data/` accanto a `docker-compose.yml` | `/app/backend/data/prod-docker` |

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

| Cartella | Cosa contiene | Chi la scrive o la legge |
| --- | --- | --- |
| 🗃️ `sqlite/` | `app.db`: utenti, broker, transazioni, asset, prezzi, tassi di cambio, impostazioni | Il server |
| 🖼️ `custom-uploads/` | File caricati nell'app (come quelli della pagina **Files**) e avatar predefiniti | L'app |
| 📊 `broker_reports/` | I report dei broker caricati, una cartella `broker_<id>/` per broker | L'importazione |
| 📝 `logs/` | `librefolio.log` e i suoi archivi settimanali | Il server scrive, tu leggi |
| 💾 `backups/` | I backup conservati sul server, una cartella ciascuno | Backup e ripristino |
| 🎭 `scenario_catalog/` | I tuoi scenari di stress, se ne hai aggiunti | Tu |
| 🗄️ `cache/` | Copie scaricabili di nuovo (`pdf-fonts/`) | L'anteprima PDF |
| 🔐 `secrets/` | `instance.key`, la chiave dell'istanza | LibreFolio, la prima volta che ha bisogno della chiave |
| 📋 `scheduler_state.json` | Ultima esecuzione e tentativo in sospeso delle sincronizzazioni pianificate | Le sincronizzazioni pianificate |

---

## 📖 Cosa contiene ogni directory

### 🗃️ `sqlite/`

- 📎 `app.db-wal` e `app.db-shm`: file di lavoro di SQLite (modalità WAL), presenti con il server in esecuzione. Non copiare mai `app.db` da solo con il server attivo.
- 🔒 `app.db.post-migration.lock`: file vuoto usato all'avvio, lascialo al suo posto.
- 🗑️ `app.db.pre-<fix>-<UTC time>.bak`: copia conservata dopo una [correzione post-migrazione](cli_tools.md#post-migration-fixes) fallita. Eliminala quando non ti serve più.

### 🖼️ `custom-uploads/`

Ogni file ha un nome casuale e un `.json` accanto che lo descrive: mantieni le coppie insieme.

### 📊 `broker_reports/`

Dentro `broker_<id>/`, un report passa da `uploaded/` a `parsed/` o `failed/`: l'originale è sempre in una delle tre.

- **📥 `uploaded/`** — in attesa di essere letti
- **✅ `parsed/`** — letti con successo
- **❌ `failed/`** — non leggibili, conservati perché tu possa verificare il motivo

### 📝 `logs/`

- 📄 `librefolio.log`: un record JSON per riga; il server stampa il log anche sulla console.
- 🗓️ Ogni lunedì (UTC) il file viene archiviato e compresso (`.gz`); restano gli ultimi 52 archivi, un anno.

**Quanto scrivere.** Nel **`.env`** di LibreFolio (predefinito `INFO`):

```env
LOG_LEVEL=INFO
```

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

**Leggere il log.** Ogni riga è un oggetto JSON: messaggio in `event`, livello in `level`, ora (UTC) in `timestamp`, traceback in `exception`.
Una riga scritta durante una richiesta porta il suo `request_id`; quando qualcosa fallisce, lo stesso id arriva al browser: header `X-Request-Id` della risposta, corpo dell'errore del server, riga `[API]` nella console del browser (strumenti di sviluppo, **Console**).

1. **Chiedi l'id** all'utente che segnala l'errore.
2. **Nella cartella `<data>/logs/`**, leggi le sue righe con [jq](https://jqlang.org/):

    ```bash
    # Every line of one request
    jq -cR 'fromjson? | select(.request_id == "3f2a9c0d41b7e865")' librefolio.log

    # The errors, each followed by its traceback
    jq -rR 'fromjson? | select(.level == "ERROR" or .level == "CRITICAL") | "\(.timestamp) \(.request_id // "-") \(.event)", (.exception // empty)' librefolio.log
    ```

    Una riga di richiesta fallita indica metodo e percorso, mai query string, header o corpo.

- `fromjson?` salta le righe non JSON, come quelle delle librerie usate da LibreFolio.
- Settimana archiviata: `gzip -dc librefolio.log.2026-10-12.gz | jq -cR …`.

### 🗄️ `cache/`

`pdf-fonts/`: i font cinesi, giapponesi e coreani che l'anteprima PDF scarica al primo uso quando il PDF li utilizza, vedi [La Content-Security-Policy](configuration_security.md#csp).
Eliminarla non fa perdere nulla; non fa parte di un [backup](backup_restore.md).

### 🔐 `secrets/`

- 🔑 `instance.key` è la [chiave dell'istanza](configuration_secrets.md#instance-key), da cui LibreFolio deriva le proprie chiavi di crittografia. Se manca, LibreFolio la tratta come un primo utilizzo: crea una nuova chiave e ciò che era cifrato con la vecchia non si legge più.
- 🔒 Cartella `0700`, file `0600`, di proprietà dell'utente che esegue LibreFolio. Altrimenti il [log di avvio](configuration_security.md#startup-checks) presenta un avviso, o un errore se LibreFolio stesso non può aprirli.
- ⛔ Non modificare, sostituire o eliminare mai la `instance.key` in uso. Se è danneggiata, o se LibreFolio ha già sostituito una chiave perduta con una nuova: arresta LibreFolio e rimetti la tua copia prima che qualcuno inserisca di nuovo un segreto di un plugin, vedi [La chiave dell'istanza](configuration_secrets.md#instance-key).
- ♻️ Quando ripristini la directory dei dati, rimetti `secrets/` insieme ad essa prima di avviare LibreFolio. Mai avviare LibreFolio su dati ripristinati senza il suo `secrets/`.
- ⚙️ Con la chiave in `LIBREFOLIO_INSTANCE_KEY` o `LIBREFOLIO_INSTANCE_KEY_FILE`, LibreFolio non usa questa cartella.

🔗 Per gli sviluppatori: [Directory dei dati su disco](../developer/architecture/database/index.md#data-directory) — ogni file, il suo formato e il codice che lo scrive, `scenario_catalog/` incluso.

---

## 🌍 Variabili d'ambiente

**Host, nel `.env`** di LibreFolio. Un percorso relativo parte dalla cartella del progetto:

```env
LIBREFOLIO_DATA_DIR=/path/to/data        # directory dei dati di produzione
LIBREFOLIO_TEST_DATA_DIR=/path/to/test   # directory dei dati di test
```

**Docker Compose, nel `docker-compose.yml`.** Il percorso dentro il container è fisso: per tenere i dati altrove sull'host, cambia il lato sinistro del volume.

```yaml
- ./LibreFolio-data:/app/backend/data/prod-docker
```

Le altre variabili e il file `.env`: [Configurazione](configuration.md).

---

## 💾 Backup {: #backup }

Il modo consigliato è un archivio di backup, creato mentre LibreFolio continua a funzionare: [Backup, ripristino e spostamento dell'istanza](backup_restore.md).

- **Da riga di comando**, `./dev.py backup create`: uno zip di database, file caricati, report dei broker e scenari di stress, per impostazione predefinita in una cartella dedicata dentro `<data>/backups/`. Vedi [Eseguire il backup dell'istanza](cli_backup.md#backup) e, per il comando nel container, [Eseguire il backup con Docker](cli_backup.md#backup-docker).
- L'archivio **esclude `secrets/`**, che salvi a parte ([Cosa includere nel backup](#what-to-back-up)), a meno che tu non lo renda [sicuro](backup_restore.md#secure) con `--encrypt`: un archivio sicuro contiene la chiave dell'istanza generata da LibreFolio.
- L'alternativa è copiare a mano la directory dei dati, come sotto.

### 📦 Backup semplice

1. **Ferma il server**, per la coerenza del database.
2. **Dalla cartella del progetto**, copia l'intera directory dei dati:

    ```bash
    # Stop the server first (to ensure database consistency)
    cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
    ```

    Risultato: una copia completa e datata di `<data>`.

Questa copia, come quella Docker riportata di seguito, comprende anche `backups/`, con ogni backup che LibreFolio vi conserva ([Backup conservati sul server](backup_restore.md#kept-backups)): elimina prima quelli che non ti servono più, imposta la [pulizia automatica](backup_restore.md#backup-cleanup), oppure lascia fuori la cartella.

### 🐳 Backup con Docker

La directory dei dati è la cartella `LibreFolio-data/` sull'host: nessun comando Docker di copia.

1. **Dalla cartella di `docker-compose.yml`**, ferma il container, copia, riavvia:

    ```bash
    docker compose stop librefolio
    cp -r ./LibreFolio-data/ /path/to/backup/librefolio-$(date +%Y%m%d)/
    docker compose start librefolio
    ```

    Risultato: una copia coerente; il server resta fermo solo per la durata della copia.

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

    Salva `secrets/` insieme al database e tieni le copie private quanto il database. Non modificare né eliminare mai la chiave dell'istanza in uso: ciò che è cifrato con essa non si legge più. Al ripristino, rimetti `secrets/` insieme ai dati prima di avviare LibreFolio.

    Solo l'utente che esegue LibreFolio può aprire `secrets/`. Lo stesso vale per `backups/`, creata al primo backup, e `.restore/`, creata la prima volta che un archivio viene verificato per un ripristino: LibreFolio le crea entrambe come `0700`, e gli archivi in `backups/` come `0600`. Se `cp` segnala `Permission denied` in una di esse, per esempio con Docker quando il tuo utente host non è quello del container, copia come root e mantieni i permessi: `sudo cp -a`. Anche eliminare un vecchio archivio da `backups/` fallisce allo stesso modo: usa `sudo rm`.

Se lo spazio è limitato, conserva almeno `sqlite/app.db`, che contiene tutti i dati strutturati, e la piccola cartella `secrets/`: i file e i report possono essere caricati di nuovo se li hai ancora.
