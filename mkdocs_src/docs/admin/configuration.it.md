# 📝 Configurazione

LibreFolio utilizza un file `.env` per la configurazione, basato su `BaseSettings` di Pydantic. Ciò consente una facile gestione delle variabili d'ambiente sia per lo sviluppo locale che per le distribuzioni Docker.

## 📄 File `.env`

Il file `.env` si trova nella root del progetto. Viene fornito un file di esempio, `.env.example`. Per iniziare, è sufficiente copiarlo:

```bash
cp .env.example .env
```

### 🔑 Variabili d'Ambiente Principali

- **`PORT`**: La porta su cui verrà eseguito il server FastAPI.
 - Default: `6040`

- **`TEST_PORT`**: La porta su cui verrà eseguito il server di test quando la modalità test è abilitata.
 - Default: `6041`

- **`LIBREFOLIO_DATA_DIR`**: Il percorso della directory dove sono memorizzati i dati di produzione (database SQLite, log, upload).
 - Default: `./backend/data/prod`

- **`JWT_SECRET`**: La chiave segreta utilizzata per la firma dei JWT (JSON Web Tokens) per le sessioni utente.
 - **Importante**: Questa deve essere impostata su un valore stabile se si desidera evitare che i client perdano le sessioni al riavvio del server (o se si utilizzano più worker uvicorn). Tuttavia, per la massima sicurezza, la scelta consigliata è lasciarla vuota e permettere che venga ricalcolata dinamicamente a runtime.

- **`LOG_LEVEL`**: Il livello di logging per l'applicazione.
 - Opzioni: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
 - Default: `INFO`

- **`PORTFOLIO_BASE_CURRENCY`**: La valuta di base predefinita per i calcoli del portafoglio.
 - Default: `EUR`

- **`PREVIEW_CACHE_MAX_MB`**: Dimensione massima (in MB) per la cache in-memory delle anteprime delle immagini.
 - Default: `50`
 - Le miniature in cache vengono espulse utilizzando l'algoritmo LRU quando viene raggiunto il limite.

- **`BACKEND_CORS_ORIGINS`**: Una lista JSON delle origini CORS consentite per lo sviluppo.
 - Default: `["http://localhost:3000", "http://localhost:5173"]`

- **`LIBREFOLIO_TEST_MODE`**: Un flag per indicare se l'applicazione è in modalità test (forzando l'isolamento tramite il database di test).
 - Impostare a `1` per abilitare la modalità test.

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
