# 📂 Struttura del Filesystem

LibreFolio memorizza tutti i dati persistenti in una directory strutturata sotto `backend/data/`. Comprendere questa struttura è importante per il backup, il debug e la manutenzione.

---

## 🗂️ Schema delle Directory

```
backend/data/
├── 📂 prod/ # Dati di produzione (predefiniti)
│ ├── 🗃️ sqlite/
│ │ └── 📄 app.db # Database SQLite principale (modalità WAL)
│ ├── 🖼️ custom-uploads/ # File caricati dagli utenti
│ │ ├── 📄 {uuid}.{ext} # File binario (immagine, documento, ecc.)
│ │ └── 📋 {uuid}.json # Metadati sidecar (caricatore, data, tipo MIME)
│ ├── 📊 broker_reports/
│ │ ├── 📥 uploaded/ # Report originali caricati dagli utenti (CSV, Excel)
│ │ ├── ✅ parsed/ # Report elaborati con successo
│ │ └── ❌ failed/ # Report per cui l'elaborazione è fallita
│ └── 📝 logs/ # File di log dell'applicazione
│
└── 🧪 test/ # Dati di test (completamente isolati)
 ├── 🗃️ sqlite/app.db
 ├── 🖼️ custom-uploads/
 ├── 📊 broker_reports/
 └── 📝 logs/
```

---

## 📖 Cosa Contiene Ogni Directory

### 🗃️ `sqlite/app.db`

Il database SQLite principale. Contiene tutti i dati dell'applicazione: utenti, broker, transazioni, tassi di cambio, impostazioni, ecc.

- 📝 Utilizza la modalità journal **WAL (Write-Ahead Logging)** per un migliore accesso concorrente.
- 📎 I file `.db-wal` e `.db-shm` sono file temporanei WAL — sono attesi e gestiti da SQLite.

:material-arrow-right: **Approfondimento per sviluppatori**: [Schema del Database](../developer/architecture/database/index.md)

### 🖼️ `custom-uploads/`

File caricati dagli utenti tramite la pagina File. Ogni caricamento crea due file:

- 📄 `{uuid}.{ext}` — Il file binario effettivo (es. `a1b2c3d4.png`)
- 📋 `{uuid}.json` — Metadati sidecar che includono: filename originale, tipo MIME, dimensione del file, data di caricamento, ID utente del caricatore

:material-arrow-right: **Approfondimento per sviluppatori**: [Componente di Caricamento File](../developer/frontend/components/file-upload.md)

### 📊 `broker_reports/`

File di report broker per il sistema BRIM (Broker Report Import Manager):

- **📥 `uploaded/`** — File originali caricati dagli utenti (CSV, Excel)
- **✅ `parsed/`** — File che sono stati elaborati con successo (transazioni estratte)
- **❌ `failed/`** — File per cui l'elaborazione è fallita (mantenuti per il debug — controllare i log per i dettagli)

:material-arrow-right: **Approfondimento per sviluppatori**: [Architettura BRIM](../developer/backend/brim/architecture.md)

### 📝 `logs/`

Log dell'applicazione in formato JSON strutturato (tramite `structlog`).

---

## 🌍 Variabili d'Ambiente

| Variabile | Default | Descrizione |
|----------|---------|-------------|
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Sovrascrive il percorso della directory dei dati di produzione |
| `LIBREFOLIO_TEST_MODE` | `0` | Impostare a `1` per utilizzare `backend/data/test/` invece di `prod/` |
| `PORT` | `8000` | Porta del server di produzione |
| `TEST_PORT` | `8001` | Porta del server di test (usata quando `LIBREFOLIO_TEST_MODE=1`) |

---

## 💾 Backup

### 📦 Backup Semplice

Il modo più semplice per fare il backup di LibreFolio è copiare l'intera directory dei dati:

```bash
# Fermare prima il server (per garantire la consistenza del database)
cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
```

### 🐳 Backup con Docker

Se si esegue tramite Docker, la directory dei dati è tipicamente montata come volume:

```bash
# Trovare il volume
docker volume inspect librefolio_data

# Copiare i dati fuori
docker cp librefolio-container:/app/backend/data/prod/ ./backup/
```

### ✅ Cosa Backuppare

Come minimo, fare il backup di:

1. **`sqlite/app.db`** — Tutti i tuoi dati (utenti, transazioni, impostazioni, tassi di cambio)
2. **`custom-uploads/`** — File caricati dagli utenti (avatar, documenti)
3. **`broker_reports/uploaded/`** — Report broker originali (nel caso sia necessario rielaborarli)

!!! consiglio "Backup solo del database"
    Se lo spazio di archiviazione è limitato, fare il backup solo di `sqlite/app.db` preserva tutti i dati strutturati. I file possono sempre essere ricaricati.

---

## 🔧 Manutenzione da Terminale Host

### 🐳 Docker exec

```bash
# Accedere alla shell del container
docker exec -it librefolio-container /bin/bash

# Eseguire comandi dev.py all'interno del container
./dev.py user list
./dev.py user reset admin newpassword
./dev.py db upgrade
```

### 💻 Accesso diretto (non Docker)

```bash
# Dalla root del progetto
./dev.py user list # Elencare tutti gli utenti
./dev.py user reset <user> <pw> # Reimpostare la password di un utente
./dev.py user promote <user> # Concedere privilegi di superuser
./dev.py user demote <user> # Rimuovere i privilegi di superuser
./dev.py db upgrade # Applicare le migrazioni in sospeso
./dev.py db create-clean # Reinizializzare il database (ATTENZIONE: cancella tutti i dati)
```

Per un elenco completo dei comandi CLI, vedere [CLI Tools](cli_tools.md).
