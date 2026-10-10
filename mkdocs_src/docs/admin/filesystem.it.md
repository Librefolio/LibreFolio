# 📂 Struttura del filesystem

LibreFolio conserva tutto ciò che memorizza in un'unica **directory dati**: il database, i file caricati, i report del broker e i log. La sua struttura è tutto ciò che devi conoscere per backup e manutenzione.

| Installazione | Directory dati |
| --- | --- |
| Host (Pipenv) | `backend/data/prod/` nella cartella del progetto, o il percorso in `LIBREFOLIO_DATA_DIR` |
| Docker Compose | `LibreFolio-data/` accanto a `docker-compose.yml` (`/app/backend/data/prod-docker` all'interno del container) |

---

## 🗂️ Struttura delle directory

```text
backend/data/
├── 📂 prod/                          # Dati di produzione (predefinito)
│   ├── 🗃️ sqlite/
│   │   └── 📄 app.db                 # Database SQLite principale (modalità WAL)
│   ├── 🖼️ custom-uploads/            # File caricati nell'app
│   ├── 📊 broker_reports/
│   │   ├── 📥 uploaded/              # Report in attesa di essere letti
│   │   ├── ✅ parsed/                # Report letti con successo
│   │   └── ❌ failed/                # Report che non è stato possibile leggere
│   ├── 📝 logs/                      # File di log dell'applicazione
│   ├── 🎭 scenario_catalog/          # Opzionale: i tuoi scenari di stress
│   └── 📋 scheduler_state.json       # Ultima esecuzione delle sincronizzazioni programmate
│
└── 🧪 test/                          # Dati di test (completamente isolati)
    ├── 🗃️ sqlite/app.db
    ├── 🖼️ custom-uploads/
    ├── 📊 broker_reports/
    └── 📝 logs/
```

---

## 📖 Cosa contiene ciascuna directory

### 🗃️ `sqlite/`

- 📄 `app.db` contiene tutti i dati strutturati: utenti, broker, transazioni, asset, prezzi, tassi di cambio e impostazioni.
- 📎 `app.db-wal` e `app.db-shm` sono i file di lavoro di SQLite (modalità WAL), previsti mentre il server è in esecuzione: non copiare mai `app.db` da solo mentre il server è attivo.
- 🔒 `app.db.post-migration.lock` è un file vuoto usato all'avvio: lascialo al suo posto. Un file chiamato `app.db.pre-<fix>-<UTC time>.bak` è una copia conservata dopo una [correzione post-migrazione](cli_tools.md#post-migration-fixes) non riuscita: eliminalo una volta che non ti serve più.

### 🖼️ `custom-uploads/`

File caricati nell'app, come quelli della pagina **Files**, e gli avatar predefiniti. Ogni file ha un nome casuale e un file `.json` accanto che lo descrive: mantieni le coppie insieme.

### 📊 `broker_reports/`

I report del broker caricati per l'importazione, in una cartella `broker_<id>/` per broker:

- **📥 `uploaded/`** — in attesa di essere letti
- **✅ `parsed/`** — letti con successo
- **❌ `failed/`** — non è stato possibile leggerli, conservati per poter controllare il motivo

Un report si sposta da `uploaded/` a `parsed/` o `failed/`, quindi il suo file originale è sempre in una delle tre cartelle.

### 📝 `logs/`

- 📄 `librefolio.log` contiene un record JSON per riga; il server stampa il log anche sulla sua console.
- 🗓️ Ogni lunedì (UTC) il file viene archiviato e compresso (`.gz`); vengono conservati gli ultimi 52 archivi, un anno.
- 🎚️ `LOG_LEVEL` in `.env` imposta quanto viene scritto (predefinito `INFO`).

??? info "📶 Livelli di log — cosa registra ciascuno"

    Ogni livello registra anche tutti quelli più gravi.

    | Livello | Cosa registra |
    |-------|-----------------|
    | 🔬 `TRACE` | Dati granulari ad alta frequenza: singoli tassi di cambio analizzati, punti di prezzo per asset |
    | 🐛 `DEBUG` | Dettagli operativi interni: quale provider è stato usato, risultati intermedi, decisioni algoritmiche |
    | ℹ️ `INFO` *(predefinito)* | Operazioni significative dell'utente: sincronizzazione completata, importazione, login, risorsa creata/eliminata |
    | ⚠️ `WARNING` | Anomalie recuperabili: fallback attivato, dati opzionali mancanti, modalità degradata |
    | ❌ `ERROR` | Errori gestiti: operazioni fallite, corruzione dei dati, provider non raggiungibile |
    | 💀 `CRITICAL` | Errori fatali che arrestano il processo |

    - **Produzione**: `LOG_LEVEL=INFO` — segnale pulito, senza rumore
    - **Risoluzione dei problemi**: `LOG_LEVEL=DEBUG` — vedi cosa sta decidendo il sistema
    - **Debug approfondito FX/prezzi**: `LOG_LEVEL=TRACE` — vedi ogni singolo punto dati

🔗 Per gli sviluppatori: [Directory dati su disco](../developer/architecture/database/index.md#data-directory) — ogni file, il suo formato e il codice che lo scrive, incluso `scenario_catalog/`.

---

## 🌍 Variabili d'ambiente

- `LIBREFOLIO_DATA_DIR` sposta la directory dati di produzione, e `LIBREFOLIO_TEST_DATA_DIR` quella di test. Un percorso relativo parte dalla cartella del progetto.
- Con Docker Compose il percorso all'interno del container è fisso: per conservare i dati altrove sull'host, modifica il lato sinistro del volume `./LibreFolio-data:/app/backend/data/prod-docker` in `docker-compose.yml`.

Le altre variabili, e il file `.env`, sono descritte in [Configurazione](configuration.md).

---

## 💾 Backup

### 📦 Backup semplice

Il modo più semplice per eseguire il backup di LibreFolio è copiare l'intera directory dati:

```bash
# Arresta prima il server (per garantire la coerenza del database)
cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
```

### 🐳 Backup Docker

Con Docker Compose, la directory dati è la cartella `LibreFolio-data/` sull'host, quindi non serve alcun comando di copia Docker. Arresta il container per una copia coerente:

```bash
docker compose stop librefolio
cp -r ./LibreFolio-data/ /path/to/backup/librefolio-$(date +%Y%m%d)/
docker compose start librefolio
```

??? tip "🔄 Esegui il backup del database senza arrestare il server"

    Il backup online di SQLite crea una copia coerente mentre il server è in esecuzione. Richiede lo strumento `sqlite3`:

    ```bash
    sqlite3 backend/data/prod/sqlite/app.db ".backup '/path/to/backup/app.db'"
    ```

    Con Docker, il database è `./LibreFolio-data/sqlite/app.db`. Questo comando copia solo il database: copia le cartelle sottostanti come al solito.

### ✅ Cosa includere nel backup

Come minimo, esegui il backup di:

1. **`sqlite/app.db`** — Tutti i tuoi dati (utenti, transazioni, impostazioni, tassi di cambio)
2. **`custom-uploads/`** — File caricati dall'utente (avatar, documenti)
3. **`broker_reports/`** — I report originali del broker, nel caso in cui tu debba importarli di nuovo
4. **`scenario_catalog/`** — I tuoi scenari di stress, se ne hai aggiunti

Se lo spazio è limitato, `sqlite/app.db` da solo conserva tutti i dati strutturati: i file e i report possono essere caricati di nuovo se li hai ancora.
