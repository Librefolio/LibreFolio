# 🐳 Installazione (Utente)

Questa guida spiega come distribuire LibreFolio per l'uso regolare utilizzando Docker. Questo è il metodo consigliato per gli utenti che non intendono modificare il codice sorgente.

## ✅ Prerequisiti

- 🐍 **Python 3.13+**: [Installa Python](https://www.python.org/downloads/)
- 📦 **Node.js 20.19+**: [Installa Node.js](https://nodejs.org/) (include npm)
- 📋 **Pipenv**: `pip install pipenv`
- 🐋 **Docker**: [Installa Docker](https://docs.docker.com/get-docker/) (include Docker Compose)

!!! warning "Gruppo Docker (Linux)"

    Su Linux, l'utente deve appartenere al gruppo `docker` per eseguire i comandi Docker senza `sudo`:

    ```bash
    sudo usermod -aG docker $USER
    ```

    Successivamente, **effettua il logout e accedi di nuovo**, oppure esegui `newgrp docker` per attivare il gruppo nella sessione corrente.

!!! note "Perché Python e Node.js?"

    LibreFolio utilizza un'**immagine Docker solo per il runtime** — il frontend e la documentazione vengono compilati sull'host prima di essere impacchettati nell'immagine Docker. Immagini pre-compilate su un registro di container sono previste per rilasci futuri.

## 📥 1. Scaricare il Progetto

Clona il repository:

```bash
git clone https://github.com/Alfystar/LibreFolio.git
cd LibreFolio
```

Oppure scarica l'ultima release da [GitHub Releases](https://github.com/Alfystar/LibreFolio/releases) e scompattala.

## ⚙️ 2. Configurare l'Ambiente

1. **Copia il file di esempio** (obbligatorio — la build si interromperà se manca il file `.env`):

 ```bash
 cp .env.example .env
 ```

2. **Modifica `.env`** per personalizzare:

 - 🔌 `PORT`: Cambia la porta se la `8000` è già in uso.
 - 💰 `PORTFOLIO_BASE_CURRENCY`: La tua valuta di base (default: `EUR`).
 - 📊 `LOG_LEVEL`: Verbosità dei log (default: `INFO`).

## 📦 3. Installare le Dipendenze

```bash
./dev.py install
```

Questo installa le dipendenze Python (backend) e Node.js (frontend).

## 🏗️ 4. Build dell'Immagine Docker

```bash
./dev.py docker build
```

Questo comando esegue automaticamente:

1. La build del frontend (build di produzione SvelteKit)
2. La build del sito di documentazione (MkDocs)
3. Impacchetta tutti i componenti in un'unica immagine Docker taggata come `librefolio:latest`

## 🚀 5. Avviare con Docker Compose

```bash
docker compose up -d
```

- 🔄 `-d` avvia l'applicazione in modalità detached (in background).

## 🌐 6. Accedere a LibreFolio

Apri il browser e vai su:

**`http://localhost:8000`**

(Oppure usa la porta configurata in `.env`).

La prima volta che accedi a LibreFolio, ti verrà presentata una **pagina di registrazione** — crea il tuo account direttamente dal browser. Il primo utente registrato diventa automaticamente l'amministratore.

Endpoint disponibili:

- 🏠 **Frontend**: `http://localhost:8000/`
- 📚 **Documentazione Utente**: `http://localhost:8000/mkdocs/`

!!! tip "Gestione utenti via CLI"

    È possibile gestire gli utenti anche dalla riga di comando. Consulta il [Manuale Amministratore — CLI Tools](../admin/cli_tools.md) per i comandi relativi alla creazione, promozione e listatura degli utenti.

## 🔄 Aggiornare LibreFolio

Per aggiornare a una nuova versione:

1. **Recupera l'ultima versione del codice**:

 ```bash
 git pull
 ```

2. **Ricompila l'immagine Docker** (ricompila automaticamente frontend e docs se modificati):

 ```bash
 ./dev.py docker rebuild
 ```

 Questo comando crea una nuova immagine, ferma i container in esecuzione e li riavvia con la nuova versione.

3. Le **migrazioni del database** vengono applicate automaticamente all'avvio.

## 🧪 Provare con Dati di Test (Opzionale)

Puoi avviare un server di test con dati mock pre-popolati per esplorare l'applicazione prima di inserire dati reali:

```bash
./dev.py docker exec test db populate --force --with-static
./dev.py docker exec server --test
```

Accedi a **`http://localhost:8001`** con l'utente `e2e_test_user` / `E2eTestPass123!`.

Il server di test gira parallelamente a quello di produzione, utilizzando un database separato. Consulta la [Guida Avanzata Docker](../admin/docker_advanced.md#test-mode) per i dettagli.

---

!!! tip "Argomenti avanzati"

    Per la configurazione del reverse proxy, i backup del database, i percorsi dati personalizzati e le considerazioni per la produzione, consulta la [🐳 Guida Avanzata Docker](../admin/docker_advanced.md).
