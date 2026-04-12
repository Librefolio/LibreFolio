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

File caricati dagli utenti tramite la pagina File. Ogni caricamento crea due file:

- 📄 `{uuid}.{ext}` — Il file binario effettivo (es. `a1b2c3d4.png`)
- 📋 `{uuid}.json` — Metadati includenti: nome file originale, tipo MIME, dimensione del file, data di caricamento, ID dell'utente che ha caricato il file

:material-arrow-right: **Approfondimento per sviluppatori**: [File Upload Component](../developer/frontend/components/file-upload.md)

### 📊 `broker_reports/`

File di report del broker per il sistema BRIM (Broker Report Import Manager):

- **📥 `uploaded/`** — File grezzi così come caricati dagli utenti (CSV, Excel)
- **✅ `parsed/`** — File che sono stati elaborati con successo (transazioni estratte)
- **❌ `failed/`** — File la cui elaborazione è fallita (conservati per il debugging — controllare i log per i dettagli)

:material-arrow-right: **Approfondimento per sviluppatori**: [BRIM Architecture](../developer/backend/brim/architecture.md)

### 📝 `logs/`

Log dell'applicazione in formato JSON strutturato (via `structlog`).

---

## 🌍 Variabili d'Ambiente

| Variabile | Default | Descrizione |
|----------|---------|-------------|
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Sovrascrive il percorso della directory dei dati di produzione |
| `LIBREFOLIO_TEST_MODE` | `0` | Imposta a `1` per usare `backend/data/test/` invece di `prod/` |
| `PORT` | `8000` | Porta del server di produzione |
| `TEST_PORT` | `8001` | Porta del server di test (usata quando `LIBREFOLIO_TEST_MODE=1`) |

---

## 💾 Backup

### 📦 Backup Semplice

Il modo più semplice per eseguire il backup di LibreFolio è copiare l'intera directory dei dati:

```bash
# Arrestare prima il server (per garantire la coerenza del database)
cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
```

### 🐳 Backup Docker

Se eseguito via Docker, la directory dei dati è tipicamente montata come volume:

```bash
# Trova il volume
docker volume inspect librefolio_data

# Copia i dati all'esterno
docker cp librefolio-container:/app/backend/data/prod/ ./backup/
```

### ✅ Cosa includere nel backup

Al minimo, effettua il backup di:

1. **`sqlite/app.db`** — Tutti i tuoi dati (utenti, transazioni, impostazioni, tassi di cambio)
2. **`custom-uploads/`** — File caricati dagli utenti (avatar, documenti)
3. **`broker_reports/uploaded/`** — Report originali dei broker (nel caso in cui sia necessario rieseguire l'analisi)

!!! tip "Backup solo del database"

    Se lo spazio di archiviazione è limitato, il backup di solo `sqlite/app.db` preserva tutti i dati strutturati. I file possono essere sempre ricaricati.

---

## 🔧 Manutenzione dal Terminale Host

### 🐳 Docker exec

```bash
# Accedi alla shell del container
docker exec -it librefolio-container /bin/bash

# Esegui i comandi di dev.py all'interno del container
./dev.py user list
./dev.py user reset admin newpassword
./dev.py db upgrade
```

### 💻 Accesso Diretto (non Docker)

```bash
# Dalla root del progetto
./dev.py user list # Elenca tutti gli utenti
./dev.py user reset <user> <pw> # Resetta la password di un utente
./dev.py user promote <user> # Concede i privilegi di superutente
./dev.py user demote <user> # Rimuove i privilegi di superutente
./dev.py db upgrade # Applica le migrazioni in sospeso
./dev.py db create-clean # Resetta il database (ATTENZIONE: elimina tutti i dati)
```

Per un elenco completo dei comandi CLI, consulta [CLI Tools](cli_tools.md).
