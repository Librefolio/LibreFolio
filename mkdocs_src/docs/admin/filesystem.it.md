# 📂 Struttura del Filesystem

LibreFolio memorizza tutti i dati persistenti in una directory strutturata sotto `backend/data/`. Comprendere questa struttura è importante per il backup, il debugging e la manutenzione.

---

## 🗂️ Layout delle Directory

```
backend/data/
├── 📂 prod/ # Production data (default)
│ ├── 🗃️ sqlite/
│ │ └── 📄 app.db # Main SQLite database (WAL mode)
│ ├── 🖼️ custom-uploads/ # User-uploaded files
│ │ ├── 📄 {uuid}.{ext} # Binary file (image, document, etc.)
│ │ └── 📋 {uuid}.json # Metadata sidecar (uploader, date, MIME type)
│ ├── 📊 broker_reports/
│ │ ├── 📥 uploaded/ # Reports waiting to be parsed
│ │ ├── ✅ parsed/ # Successfully parsed reports
│ │ └── ❌ failed/ # Reports that failed parsing
│ └── 📝 logs/ # Application log files
│
└── 🧪 test/ # Test data (completely isolated)
    ├── 🗃️ sqlite/app.db
    ├── 🖼️ custom-uploads/
    ├── 📊 broker_reports/
    └── 📝 logs/
```

---

## 📖 Cosa contiene ogni Directory

### 🗃️ `sqlite/app.db`

Il database SQLite principale. Contiene tutti i dati dell'applicazione: utenti, broker, transazioni, tassi di cambio, impostazioni, ecc.

- 📝 Utilizza la modalità di journaling **WAL (Write-Ahead Logging)** per un migliore accesso concorrente
- 📎 I file `.db-wal` e `.db-shm` sono file WAL temporanei — sono previsti e gestiti da SQLite

:material-arrow-right: **Approfondimento per sviluppatori**: [Database Schema](../developer/architecture/database/index.md)

### 🖼️ `custom-uploads/`

File caricati dagli utenti tramite la pagina Files. Ogni caricamento crea due file:

- 📄 `{uuid}.{ext}` — Il file binario effettivo (es. `a1b2c3d4.png`)
- 📋 `{uuid}.json` — Metadata inclusi: nome file originale, tipo MIME, dimensione file, data di caricamento, ID dell'utente che ha effettuato il caricamento

:material-arrow-right: **Approfondimento per sviluppatori**: [File Upload Component](../developer/frontend/components/file-upload.md)

### 📊 `broker_reports/`

File dei report dei broker per il sistema BRIM (Broker Report Import Manager):

- **📥 `uploaded/`** — File grezzi così come caricati dagli utenti (CSV, Excel)
- **✅ `parsed/`** — File che sono stati elaborati con successo (transazioni estratte)
- **❌ `failed/`** — File per i quali l'analisi è fallita (conservati per il debugging — controllare i log per i dettagli)

:material-arrow-right: **Approfondimento per sviluppatori**: [BRIM Architecture](../developer/backend/brim/architecture.md)

### 📝 `logs/`

Log dell'applicazione in formato JSON strutturato (via `structlog`). I file di log ruotano settimanalmente e vengono conservati per 1 anno (compressi con gzip).

La verbosità è controllata dalla variabile d'ambiente `LOG_LEVEL`.

**Cosa cattura ogni livello** — ogni riga mostra quali livelli di log sono visibili:

| LOG_LEVEL | 🔬 TRACE (5) | 🐛 DEBUG (10) | ℹ️ INFO (20) | ⚠️ WARNING (30) | ❌ ERROR (40) | 💀 CRITICAL (50) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 🔬`TRACE` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 🐛`DEBUG` | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ℹ️ **`INFO`** *(default)* | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| ⚠️ `WARNING` | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| ❌`ERROR` | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| 💀`CRITICAL` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

**Significato di ogni livello:**

| Livello | Cosa cattura |
|-------|-----------------|
| 🔬`TRACE` | Dati granulari ad alta frequenza: singoli tassi di cambio analizzati, punti di prezzo per asset |
| 🐛`DEBUG` | Internali operativi: quale provider è stato utilizzato, risultati intermedi, decisioni algoritmiche |
| ℹ️`INFO` | Operazioni utente significative: sincronizzazione completata, importazione, login, creazione/eliminazione di risorse |
| ⚠️`WARNING` | Anomalie recuperabili: fallback attivato, dati opzionali mancanti, modalità degradata |
| ❌`ERROR` | Errori gestiti: operazioni fallite, corruzione dei dati, provider irraggiungibile |
| 💀`CRITICAL` | Errori fatali che interrompono il processo |

!!! tip "Impostazioni consigliate"

    - **Produzione**: `LOG_LEVEL=INFO` — segnale pulito, senza rumore
    - **Risoluzione problemi**: `LOG_LEVEL=DEBUG` — per vedere cosa sta decidendo il sistema
    - **Debugging profondo tassi di cambio/prezzi**: `LOG_LEVEL=TRACE` — per vedere ogni singolo punto dato

---

## 🌍 Variabili d'Ambiente

| Variabile | Default | Descrizione |
|----------|---------|-------------|
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Sovrascrive il percorso della directory dei dati di produzione |
| `LIBREFOLIO_TEST_MODE` | `0` | Impostare a `1` per usare `backend/data/test/` invece di `prod/` |
| `PORT` | `6040` | Porta del server di produzione |
| `TEST_PORT` | `6041` | Porta del server di test (usata quando `LIBREFOLIO_TEST_MODE=1`) |

---

## 💾 Backup

### 📦 Backup Semplice

Il modo più semplice per eseguire il backup di LibreFolio è copiare l'intera directory dei dati:

```bash
# Stop the server first (to ensure database consistency)
cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
```

### 🐳 Backup Docker

Se eseguito tramite Docker, la directory dei dati è tipicamente montata come volume:

```bash
# Find the volume
docker volume inspect librefolio_data

# Copy data out
docker cp librefolio-container:/app/backend/data/prod/ ./backup/
```

### ✅ Cosa salvare nel backup

Al minimo, eseguire il backup di:

1. **`sqlite/app.db`** — Tutti i tuoi dati (utenti, transazioni, impostazioni, tassi di cambio)
2. **`custom-uploads/`** — File caricati dagli utenti (avatar, documenti)
3. **`broker_reports/uploaded/`** — Report originali dei broker (nel caso fosse necessario ri-analizzarli)

!!! tip "Backup solo del database"

    Se lo spazio di archiviazione è limitato, il backup di solo `sqlite/app.db` preserva tutti i dati strutturati. I file possono essere sempre ricaricati.

---

## 🔧 Manutenzione dal Terminale Host

### 🐳 Docker exec

```bash
# Access the container shell
docker exec -it librefolio-container /bin/bash

# Run dev.py commands inside the container
./dev.py user list
./dev.py user reset admin newpassword
./dev.py db upgrade
```

### 💻 Accesso Diretto (non-Docker)

```bash
# From the project root
./dev.py user list # List all users
./dev.py user reset <user> <pw> # Reset a user's password
./dev.py user promote <user> # Grant superuser privileges
./dev.py user demote <user> # Remove superuser privileges
./dev.py db upgrade # Apply pending migrations
./dev.py db create-clean # Reset database (WARNING: deletes all data)
```

Per l'elenco completo dei comandi CLI, vedi [CLI Tools](cli_tools.md).
