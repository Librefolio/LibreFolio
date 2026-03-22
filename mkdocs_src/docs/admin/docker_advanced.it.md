# 🐳 Guida Avanzata a Docker

Questa guida offre uno sguardo più approfondito alla configurazione Docker per LibreFolio, rivolta a utenti che desiderano personalizzare la propria distribuzione.

## 📄 `docker-compose.yml`

Il file `docker-compose.yml` definisce i servizi, le reti e i volumi per l'applicazione.

### 🔧 Servizi

- **`backend`**: L'applicazione FastAPI principale.
 - 🏗️ **`build`**: Specifica il Dockerfile nella root del progetto.
 - 🔌 **`ports`**: Mappa la porta dell'host (definita da `${PORT}` in `.env`) alla porta 8000 del container.
 - 📂 **`volumes`**:
 - `./backend:/app/backend`: Monta il codice sorgente del backend per lo sviluppo (consente l'hot reload).
 - `./frontend/build:/app/frontend/build`: Monta la build di produzione del frontend.
 - `./mkdocs_src/site:/app/mkdocs_src/site`: Monta il sito della documentazione.
 - `./logs:/app/logs`: Conserva i file di log.
 - 🌍 **`env_file`**: Carica le variabili d'ambiente dal file `.env`.

### 💾 Volumi

- **`libre-folio-data`**: Un volume nominato usato per conservare i file del database SQLite. Questo garantisce che i tuoi dati non vadano persi quando fermi o rimuovi i container.

### 🌐 Reti

- **`libre-folio-net`**: Una rete bridge personalizzata per consentire ai servizi di comunicare tra loro.

## 🏭 Considerazioni per la Produzione

Per una distribuzione in produzione, potresti considerare le seguenti modifiche:

### 🔒 1. Reverse Proxy

È altamente consigliato eseguire LibreFolio dietro un reverse proxy come **Nginx** o **Traefik**. Questo ti permette di:

- 🔐 Gestire facilmente certificati SSL/TLS per HTTPS.
- 🖥️ Servire più applicazioni sullo stesso server.
- 🛡️ Aggiungere header di sicurezza e rate limiting.

### 💾 2. Backup del Database

Poiché il database è archiviato in un volume Docker, dovresti avere una strategia per effettuare il backup. Puoi usare un semplice cron job per copiare il file del database dal volume in una posizione sicura.

Esempio di script di backup:

```bash
#!/bin/bash
docker cp librefolio_backend_1:/app/backend/data/sqlite/app.db /path/to/backups/app.db-$(date +%F)
```

### 🚫 3. Disabilitare i Mount di Sviluppo

In un ambiente di produzione, potresti non voler montare direttamente il codice sorgente. Puoi creare un file separato `docker-compose.prod.yml` che ometta i volumi del codice sorgente e si avvalga esclusivamente dell'immagine Docker costruita.
