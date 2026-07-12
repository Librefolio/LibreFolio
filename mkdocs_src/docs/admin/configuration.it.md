# 📝 Configurazione

LibreFolio utilizza un file `.env` per la configurazione, basato su `BaseSettings` di Pydantic. Ciò consente una facile gestione delle variabili d'ambiente sia per lo sviluppo locale che per le distribuzioni Docker.

## 🔧 Guida Rapida: Inizializzare la Configurazione

Il file `.env` si trova nella root del progetto. Viene fornito un file di esempio, `.env.example`. Per iniziare, è sufficiente copiarlo:

```bash
cp .env.example .env
```

## ✏️ Opzioni di Configurazione (File `.env`)

Queste variabili consentono di personalizzare il comportamento di LibreFolio all'interno del file `.env`. Sono le stesse variabili caricate per impostazione predefinita dal Docker Compose.

- **`PORT`** (Default: `6040`): La porta su cui verrà eseguito il server FastAPI in produzione.
- **`TEST_PORT`** (Default: `6041`): La porta su cui verrà eseguito il server di test quando è abilitata la modalità test.
- **`LIBREFOLIO_DATA_DIR`** (Default: `./backend/data/prod`): Il percorso della directory radice in cui sono memorizzati i dati persistenti (database SQLite, caricamenti, log, ecc.). I percorsi relativi vengono risolti in assoluti rispetto alla root del progetto, mentre in Docker viene sovrascritto a `/app/backend/data/prod-docker` in base ai volumi di Compose.
- **`LOG_LEVEL`** (Default: `INFO`, Opzioni: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`): Il livello di logging principale dell'applicazione.
- **`PORTFOLIO_BASE_CURRENCY`** (Default: `EUR`): La valuta di base predefinita per i calcoli dei portafogli (codice ISO 4217).
- **`PREVIEW_CACHE_MAX_MB`** (Default: `50`): Dimensione massima (in MB) per la cache in-memory delle anteprime delle immagini. Le miniature in cache vengono espulse con algoritmo LRU al superamento del limite.

## 💻 Parametri di Sistema (Variabili d'Ambiente)

Queste variabili gestiscono l'integrazione di basso livello tra i moduli dell'applicazione, l'isolamento dei test e gli script della CLI di sviluppo. Di norma, l'utente non ha bisogno di modificarle direttamente, poiché il sistema (Docker Compose o lo script `dev.py`) le auto-assegna o le gestisce automaticamente.

- **`HOST`** (Default: `0.0.0.0`): L'indirizzo di binding di rete per il server web FastAPI, iniettato automaticamente in Docker e nei comandi CLI.
- **`JWT_SECRET`**: La chiave segreta per la firma e decrittografia delle sessioni utente (JSON Web Tokens). Questa variabile **non** fa parte della validazione Pydantic `Settings` e viene letta a runtime direttamente a livello di sistema operativo. Se lasciata vuota, l'applicazione auto-assegna una chiave casuale sicura a ogni avvio (`secrets.token_urlsafe(64)`). Quando si avvia il server in locale via `./dev.py server`, lo script genera e inietta automaticamente un segreto condiviso per garantire la persistenza della sessione tra i vari worker.
- **`LIBREFOLIO_TEST_MODE`**: Flag per indicare se l'applicazione è in modalità test. Quando impostato a `1` o `true`, forza l'applicazione a isolarsi completamente reindirizzando la directory dei dati su `backend/data/test/`. Viene gestito automaticamente dai runner di test.
- **`LIBREFOLIO_LOG_LEVEL`**: Override di priorità per il livello dei log. Se impostato, ha la precedenza assoluta e sovrascrive a runtime la proprietà `LOG_LEVEL` caricata da Pydantic (utilizzato da `./dev.py server --debug`).

## 🔝 Priorità di Risoluzione

Nella risoluzione delle variabili di configurazione, LibreFolio rispetta un ordine di precedenza dal più basso (valori predefiniti nel codice) al più alto (override di Docker Compose). Per una mappa dettagliata delle priorità e un diagramma, consultare la [Sezione Priorità di Risoluzione Docker](docker_advanced.md#resolution-priority).

## 📂 Separazione dei Dati

LibreFolio utilizza directory di dati separate per la produzione e per i test:

- **Produzione**: `backend/data/prod/` (sqlite, custom-uploads, broker_reports, logs)
- **Test**: `backend/data/test/` (stessa struttura, completamente isolata)

La funzione `get_data_dir()` in `config.py` seleziona automaticamente il percorso corretto in base a `LIBREFOLIO_TEST_MODE`.

## ⚙️ Come Funziona

Le impostazioni vengono caricate in una classe Pydantic `Settings` situata in `backend/app/config.py`. Questa classe legge automaticamente le variabili dal file `.env` e ne convalida i tipi.

Questo approccio garantisce:

- **Sicurezza dei Tipi**: Le impostazioni vengono validate all'avvio dell'applicazione.
- **Configurazione Centralizzata**: Tutte le impostazioni sono definite in un unico punto.
- **Flessibilità**: Le impostazioni possono essere fornite tramite un file `.env` o come effettive variabili d'ambiente, facilitando la configurazione in diversi ambienti (locale, Docker, ecc.).
