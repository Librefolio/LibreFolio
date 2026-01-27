# Migration Plan: Data Directory Separation (prod/test)

**Data creazione**: 2026-01-26  
**Priorità**: Media (da fare dopo completamento BRIM multiuser)  
**Stima**: 2-4 ore

---

## 📋 Problema

Attualmente il progetto usa:
- `backend/data/sqlite/app.db` per produzione
- `backend/data/sqlite/test_app.db` per test

Tuttavia, con la crescita del progetto, altri dati persistenti si accumulano nella stessa cartella `backend/data/`:
- `uploads/` - File caricati dagli utenti
- `brim/` - File BRIM (uploaded, parsed, failed)
- Potenziali futuri: `cache/`, `logs/`, `exports/`, etc.

**Problemi**:
1. I test possono inquinare i dati di produzione (file nella stessa cartella)
2. Non c'è isolamento completo tra ambienti
3. I broker con ID alti dei test sono invisibili in prod solo per fortuna (non per design)
4. Difficile fare cleanup dei dati test senza rischiare dati prod

---

## 🎯 Obiettivo

Separare completamente le cartelle dati:

```
backend/data/
├── prod/                    # Dati di produzione
│   ├── sqlite/
│   │   └── app.db
│   ├── uploads/
│   │   ├── files/
│   │   │   └── .gitkeep
│   │   └── metadata/
│   │       └── .gitkeep
│   └── brim/
│       ├── uploaded/
│       │   └── .gitkeep
│       ├── parsed/
│       │   └── .gitkeep
│       └── failed/
│           └── .gitkeep
│
└── test/                    # Dati di test (contenuto gitignored, struttura no)
    ├── sqlite/
    │   └── .gitkeep
    ├── uploads/
    │   ├── files/
    │   │   └── .gitkeep
    │   └── metadata/
    │       └── .gitkeep
    └── brim/
        ├── uploaded/
        │   └── .gitkeep
        ├── parsed/
        │   └── .gitkeep
        └── failed/
            └── .gitkeep
```

---

## 🔧 Configurazione Flessibile

### File `.env`

```env
# Default data directories
LIBREFOLIO_DATA_DIR=./backend/data/prod
LIBREFOLIO_TEST_DATA_DIR=./backend/data/test

# Default ports
LIBREFOLIO_PORT=8000
LIBREFOLIO_TEST_PORT=8001
```

### Flags CLI in dev.py

```bash
# Standard: usa .env defaults
./dev.py server                     # prod: data/prod, porta 8000
./dev.py server --test              # test: data/test, porta 8001

# Custom data directory (prod mode)
./dev.py server --data ./backend/data/staging

# Custom port
./dev.py server --port 9000

# Combinazione
./dev.py server --data ./my-data --port 9000
./dev.py server --test --port 8002  # test con porta custom

# Nota: --data non è compatibile con --test (test usa sempre TEST_DATA_DIR)
```

### Logica di risoluzione

1. **Test mode** (`--test`):
   - Data dir: `LIBREFOLIO_TEST_DATA_DIR` (non sovrascrivibile da CLI)
   - Port: `--port` se specificato, altrimenti `LIBREFOLIO_TEST_PORT`

2. **Prod mode** (default):
   - Data dir: `--data` se specificato, altrimenti `LIBREFOLIO_DATA_DIR`
   - Port: `--port` se specificato, altrimenti `LIBREFOLIO_PORT`

---

## 🔍 Analisi Codice Necessaria

### 1. Configuration (`backend/app/core/config.py`)

Verificare come viene costruito il path del database:
```python
# Cercare:
DATABASE_URL
SQLITE_PATH
data/sqlite
```

**Modifica necessaria**: 
```python
DATA_DIR: str = Field(default="./backend/data/prod")

@property
def sqlite_path(self) -> Path:
    return Path(self.DATA_DIR) / "sqlite" / "app.db"

@property  
def uploads_dir(self) -> Path:
    return Path(self.DATA_DIR) / "uploads"

@property
def brim_dir(self) -> Path:
    return Path(self.DATA_DIR) / "brim"
```

### 2. Static Uploads (`backend/app/services/static_uploads.py`)

Cercare:
```python
# Path delle cartelle uploads
UPLOAD_DIR
data/uploads
```

**Modifica necessaria**: Usare `settings.uploads_dir`.

### 3. BRIM Provider (`backend/app/services/brim_provider.py`)

Cercare:
```python
# Path delle cartelle BRIM
data/brim
uploaded/
parsed/
failed/
```

**Modifica necessaria**: Usare `settings.brim_dir`.

### 4. Alembic (`backend/alembic/env.py` e `alembic.ini`)

Cercare:
```python
# Database URL per migrations
sqlalchemy.url
```

### 5. Test Server Helper (`backend/test_scripts/test_server_helper.py`)

Cercare come viene configurato il test mode e verificare che usi `LIBREFOLIO_TEST_DATA_DIR`.

### 6. dev.py

Aggiungere argomenti:
```python
parser.add_argument('--data', help='Custom data directory (prod mode only)')
parser.add_argument('--port', type=int, help='Custom port')
```

E logica:
```python
if args.test:
    data_dir = os.getenv('LIBREFOLIO_TEST_DATA_DIR', './backend/data/test')
    port = args.port or get_test_server_port()
else:
    data_dir = args.data or os.getenv('LIBREFOLIO_DATA_DIR', './backend/data/prod')
    port = args.port or get_server_port()

env["LIBREFOLIO_DATA_DIR"] = data_dir
```

---

## 📝 Piano di Implementazione

### Fase 1: Creare Struttura Directory

```bash
# Script per creare struttura con .gitkeep
mkdir -p backend/data/prod/sqlite
mkdir -p backend/data/prod/uploads/{files,metadata}
mkdir -p backend/data/prod/brim/{uploaded,parsed,failed}

mkdir -p backend/data/test/sqlite  
mkdir -p backend/data/test/uploads/{files,metadata}
mkdir -p backend/data/test/brim/{uploaded,parsed,failed}

# Creare .gitkeep in tutte le cartelle foglia
find backend/data -type d -empty -exec touch {}/.gitkeep \;
```

### Fase 2: Backend Configuration

1. **Modificare `config.py`**:
   - Aggiungere `DATA_DIR` setting
   - Creare properties per paths derivati
   - Gestire creazione automatica directories

2. **Creare helper centralizzato** in `backend/app/core/paths.py`:
   ```python
   from backend.app.core.config import settings
   from pathlib import Path
   
   def ensure_data_dirs():
       """Ensure all data directories exist."""
       dirs = [
           settings.sqlite_path.parent,
           settings.uploads_dir / "files",
           settings.uploads_dir / "metadata", 
           settings.brim_dir / "uploaded",
           settings.brim_dir / "parsed",
           settings.brim_dir / "failed",
       ]
       for d in dirs:
           d.mkdir(parents=True, exist_ok=True)
   ```

### Fase 3: Aggiornare Services

1. **static_uploads.py**: Usare `settings.uploads_dir`
2. **brim_provider.py**: Usare `settings.brim_dir`
3. **Database**: Usare `settings.sqlite_path`

### Fase 4: Aggiornare dev.py

1. Aggiungere args `--data` e `--port`
2. Passare `LIBREFOLIO_DATA_DIR` come env var
3. Validare che `--data` e `--test` non siano usati insieme

### Fase 5: Aggiornare Test Infrastructure

1. **test_server_helper.py**: Usare `LIBREFOLIO_TEST_DATA_DIR`
2. **conftest.py**: Verificare fixtures

### Fase 6: Migration Dati Esistenti

Script per migrare:
```bash
#!/bin/bash
# migrate-data.sh

# Backup
cp -r backend/data backend/data.backup.$(date +%Y%m%d)

# Move prod data
mv backend/data/sqlite/app.db backend/data/prod/sqlite/ 2>/dev/null || true
mv backend/data/uploads/* backend/data/prod/uploads/ 2>/dev/null || true  
mv backend/data/brim/* backend/data/prod/brim/ 2>/dev/null || true

# Move test data
mv backend/data/sqlite/test_app.db backend/data/test/sqlite/app.db 2>/dev/null || true

# Cleanup old structure
rmdir backend/data/sqlite 2>/dev/null || true

echo "Migration complete. Old data backed up to backend/data.backup.*"
```

### Fase 7: Aggiornare .gitignore

```gitignore
# Data directories - ignore content but keep structure
backend/data/prod/sqlite/*.db
backend/data/prod/uploads/files/*
backend/data/prod/uploads/metadata/*
backend/data/prod/brim/**/*

backend/data/test/sqlite/*.db
backend/data/test/uploads/files/*
backend/data/test/uploads/metadata/*
backend/data/test/brim/**/*

# Keep .gitkeep files
!backend/data/**/.gitkeep
```

---

## ✅ Checklist

### Setup Struttura
- [ ] Creare struttura directory prod/test
- [ ] Aggiungere .gitkeep in tutte le cartelle
- [ ] Aggiornare .gitignore

### Backend
- [ ] Modificare config.py con DATA_DIR
- [ ] Creare helper paths.py
- [ ] Aggiornare static_uploads.py
- [ ] Aggiornare brim_provider.py
- [ ] Aggiornare database URL construction
- [ ] Aggiornare alembic.ini/env.py
- [ ] Chiamare ensure_data_dirs() all'avvio

### Test Infrastructure  
- [ ] Aggiornare test_server_helper.py
- [ ] Aggiornare conftest.py se necessario
- [ ] Verificare tutti i test passano

### Scripts & Dev
- [ ] Aggiungere `--data` e `--port` a dev.py
- [ ] Aggiornare .env.example
- [ ] Creare script migration dati
- [ ] Testare combinazioni di flags

### Documentation
- [ ] Aggiornare README
- [ ] Documentare nuova struttura
- [ ] Documentare flags CLI

---

## 🧪 Test di Verifica

1. **Test Mode**:
   ```bash
   ./dev.py server --test
   # Verifica: usa backend/data/test/, porta 8001
   # Carica file, verifica vadano in test/uploads
   ```

2. **Prod Mode default**:
   ```bash
   ./dev.py server
   # Verifica: usa backend/data/prod/, porta 8000
   ```

3. **Custom data dir**:
   ```bash
   mkdir -p /tmp/librefolio-staging
   ./dev.py server --data /tmp/librefolio-staging
   # Verifica: crea struttura e usa quella directory
   ```

4. **Custom port**:
   ```bash
   ./dev.py server --port 9000
   # Verifica: avvia su porta 9000
   ```

5. **Isolamento**:
   ```bash
   # Crea dati in test
   ./dev.py server --test
   # (carica file)
   
   # Avvia prod
   ./dev.py server
   # Verifica: dati test non visibili
   ```

6. **Error handling**:
   ```bash
   ./dev.py server --test --data /tmp/custom
   # Verifica: errore "Cannot use --data with --test"
   ```

---

## ⚠️ Note Importanti

1. **Backup prima di migrare**: Fare backup completo di `backend/data/` prima di iniziare

2. **Docker**: Se si usa Docker, aggiornare volumi per puntare a `backend/data/prod/`

3. **CI/CD**: Aggiornare pipeline per usare nuova struttura

4. **Alembic migrations**: Potrebbero richiedere path specifico - verificare che `DATABASE_URL` venga costruito correttamente

5. **Compatibilità**: Durante la transizione, supportare temporaneamente entrambe le strutture
