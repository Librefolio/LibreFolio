# 🐳 Guida Avanzata a Docker

Questa guida fornisce un approfondimento sulla configurazione Docker per LibreFolio, destinata agli utenti che desiderano personalizzare la propria installazione.

## ⚠️ Prerequisiti

!!! warning "Gruppo Docker (Linux)"

    Su Linux, l'utente deve appartenere al gruppo `docker` per eseguire i comandi Docker senza `sudo`:

    ```bash
    sudo usermod -aG docker $USER
    ```

    Successivamente, **disconnettiti e riconnettiti**, oppure esegui `newgrp docker` per attivare il gruppo nella sessione corrente. Senza questo passaggio, tutti i comandi `docker` e `docker compose` falliranno con un errore di permessi.

!!! warning "File `.env` richiesto"

    LibreFolio richiede un file `.env` nella root del progetto. Se è assente, `./dev.py docker build` rifiuterà di procedere.

    ```bash
    cp .env.example .env
    $EDITOR .env # rivedere e personalizzare i parametri
    ```

## 🏗️ Architettura

LibreFolio utilizza un'**immagine Docker solo per il runtime**. Il frontend (SvelteKit) e la documentazione (MkDocs) vengono compilati sull'host e poi copiati nell'immagine. Il comando `./dev.py docker build` gestisce questo processo automaticamente.

```text
Host (build) Docker Image (runtime)
┌──────────────┐ ┌──────────────────────┐
│ frontend/src │──npm build──▶ │ frontend/build/ │
│ mkdocs_src/ │──mkdocs ───▶ │ mkdocs_src/site/ │
│ backend/ │──copy──────▶ │ backend/ │
│ Pipfile* │──pipenv ───▶ │ Python packages │
└──────────────┘ └──────────────────────┘
```

## 📄 `docker-compose.yml`

Il file `docker-compose.yml` definisce il servizio e la directory dei dati persistenti.

### 🔧 Servizio: `librefolio`

- 🏗️ **`build: .`**: Costruisce l'immagine a partire dal `Dockerfile` nella root del progetto.
- 🔌 **`ports`**: Mappa la porta dell'host (`${PORT:-8000}`) alla porta `8000` del container, e `${TEST_PORT:-8001}` alla porta `8001` per la modalità test.
- 📂 **`volumes`**: Un bind mount `./LibreFolio-data` → `/app/backend/data/prod-docker` persiste il database, gli upload, i report dei broker e i log **nella stessa directory di `docker-compose.yml`**.
- 📝 **`env_file: .env`**: Carica tutta la configurazione dal file `.env` (copiato da `.env.example`).
- 🌍 **`environment`**: Sovrascrive solo i valori specifici di Docker: `LIBREFOLIO_DATA_DIR` (percorso nel container) e `HOST=0.0.0.0`.
- 🩺 **`healthcheck`**: Interroga `GET /api/v1/system/health` ogni 30 secondi.

### 💾 Directory Dati: `LibreFolio-data/`

Una directory in **bind mount** creata accanto a `docker-compose.yml`. Contiene il database SQLite, gli upload personalizzati, i report dei broker e i file di log. I dati sopravvivono all'arresto, al riavvio o alla rimozione del container. È possibile eseguire il backup direttamente dal filesystem dell'host.

## 🛠️ Comandi CLI

Tutte le operazioni Docker sono disponibili tramite `dev.py`:

```bash
./dev.py docker build # Costruisce l'immagine (compila automaticamente frontend + docs)
./dev.py docker build --no-cache # Ricostruzione completa senza cache Docker
./dev.py docker rebuild # Costruzione → arresto → riavvio (deploy in un unico passaggio)
./dev.py docker up # Avvia i container
./dev.py docker down # Ferma i container
./dev.py docker logs -f # Segue i log del container
./dev.py docker status # Mostra lo stato del container
./dev.py docker exec <cmd> # Esegue un comando dev.py all'interno del container
```

!!! tip "Documentazione con screenshot"

    Se stai compilando la documentazione e desideri screenshot completi nella galleria, esegui:

    ```bash
    ./dev.py mkdocs --gallery
    ```

    Questo richiede un ambiente completamente installato (con `pipenv`) e un server in esecuzione con dati di test popolati. Sii paziente: la generazione della galleria richiede alcuni minuti.

### 📡 `docker exec` — Esecuzione di Comandi all'interno del Container

Il sottocomando `docker exec` inoltra qualsiasi comando `dev.py` all'interno del container in esecuzione:

```bash
./dev.py docker exec user create admin admin@example.com Pass123!
./dev.py docker exec user list
./dev.py docker exec db upgrade
./dev.py docker exec server --test
```

Questo equivale a eseguire `docker compose exec librefolio python dev.py <cmd>`.

## 🧪 Modalità Test

La configurazione di Docker Compose espone **due porte**:

| Porta | Scopo | Database |
|------|---------|----------|
| `8000` | Server di produzione (avviato dal CMD del container) | `prod-docker/sqlite/app.db` (volume persistente) |
| `8001` | Server di test (avviato manualmente via `docker exec`) | `test/sqlite/app.db` (effimero) |

### Avvio del Server di Test

1. **Avvia il container** (il server di produzione parte automaticamente su `:8000`):

 ```bash
 docker compose up -d
 ```

2. **Popola il database di test** con dati simulati:

 ```bash
 ./dev.py docker exec test db populate --force --with-static
 ```

3. **Avvia il server di test** sulla porta 8001:

 ```bash
 ./dev.py docker exec server --test
 ```

4. **Accedi** all'indirizzo **`http://localhost:8001`**

 Credenziali di test:

 | Username | Password |
 |----------|----------|
 | `e2e_test_user` | `E2eTestPass123!` |
 | `e2e_test_admin` | `E2eAdminPass123!` |

!!! warning "I dati di test sono effimeri"

    Il database di test risiede all'interno del **layer scrivibile** del container, non su un bind mount persistente. Ciò significa che:

    - ✅ I dati sopravvivono a `docker compose stop` / `docker compose start` (il container è in pausa, non rimosso).
    - ❌ I dati vanno **persi** con `docker compose down` (il container viene rimosso e ricreato).

    Se hai bisogno di dati di test persistenti, aggiungi un bind mount dedicato in `docker-compose.yml`:

    ```yaml
    volumes:
    - ./LibreFolio-data:/app/backend/data/prod-docker
    - ./LibreFolio-test-data:/app/backend/data/test # ← aggiungi questo
    ```

## 🏭 Considerazioni per la Produzione

### 🎮 1. Personalizzazione di `docker-compose.yml`

Il repository include un file `docker-compose.yml` pronto all'uso. Ecco il file completo con annotazioni che mostrano cosa puoi personalizzare:

```yaml
services:
 librefolio:
 image: librefolio:latest # Built by ./dev.py docker build
 build: .
 container_name: librefolio
 restart: unless-stopped
 ports:
 - "${PORT:-8000}:8000" # (1) Production port — change via PORT in .env
 - "${TEST_PORT:-8001}:8001" # (2) Test server port (optional)
 volumes:
 - ./LibreFolio-data:/app/backend/data/prod-docker # (3) Persistent data (bind mount)
 env_file: .env # (4) All config from .env file
 environment:
 - LIBREFOLIO_DATA_DIR=/app/backend/data/prod-docker # Docker-specific override
 - HOST=0.0.0.0
 healthcheck:
 test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/system/health')"]
 interval: 30s
 timeout: 10s
 start_period: 15s
 retries: 3
```

**Personalizzazioni comuni:**

| # | Cosa | Come |
|---|------|-----|
| (1) | Cambiare porta di produzione | Imposta `PORT=3000` in `.env` |
| (2) | Disabilitare porta di test | Rimuovi la riga `TEST_PORT` da `ports:` |
| (3) | Percorso dati personalizzato | Cambia il bind mount: `./my-data:/app/backend/data/prod-docker` |
| (4) | Tutta la configurazione | Modifica il file `.env` (copiato da `.env.example`) |

!!! tip "Primo utente"

    La prima volta che accedi a LibreFolio tramite browser, vedrai una pagina di registrazione. Crea il tuo account direttamente: il primo utente diventa automaticamente l'amministratore. Non è necessario l'uso della CLI.

### 🔒 2. Reverse Proxy

È vivamente consigliato eseguire LibreFolio dietro un reverse proxy come **Nginx** o **Traefik**. Questo ti permette di:

- 🔐 Gestire facilmente i certificati SSL/TLS per HTTPS.
- 🖥️ Servire più applicazioni sullo stesso server.
- 🛡️ Aggiungere header di sicurezza e rate limiting.

### 💾 3. Backup del Database

Il database è memorizzato nella directory `LibreFolio-data/` accanto a `docker-compose.yml`. Effettua il backup direttamente dal filesystem dell'host:

```bash
#!/bin/bash
cp ./LibreFolio-data/sqlite/app.db /path/to/backups/app.db-$(date +%F)
```

Non è necessario `docker cp`: la directory dei dati è un bind mount accessibile dall'host.

### 🔑 4. Variabili d'Ambiente

Tutta la configurazione è gestita nel file `.env` (copiato da `.env.example`). Le sovrascritture specifiche di Docker nel blocco `environment:` non devono essere modificate:

| Variabile | Default | Descrizione | Dove |
|----------|---------|-------------|-------|
| `PORT` | `8000` | Porta host per il server di produzione | `.env` |
| `TEST_PORT` | `8001` | Porta host per il server di test | `.env` |
| `LOG_LEVEL` | `INFO` | Verbosità dei log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `.env` |
| `PORTFOLIO_BASE_CURRENCY` | `EUR` | Valuta di base per i calcoli del portafoglio | `.env` |
| `PREVIEW_CACHE_MAX_MB` | `50` | Cache massima in memoria per l'anteprima immagini (MB) | `.env` |
| `LIBREFOLIO_DATA_DIR` | `/app/backend/data/prod-docker` | Percorso dati nel container (non modificare) | `docker-compose.yml` |
| `HOST` | `0.0.0.0` | Indirizzo di bind del container (non modificare) | `docker-compose.yml` |
