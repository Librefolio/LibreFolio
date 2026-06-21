# 📦 Installazione su Host (Pipenv)

Questa guida descrive come configurare LibreFolio direttamente su una macchina host usando Python, Node.js e Pipenv. Questo metodo di installazione manuale è adatto per gli utenti che desiderano eseguire LibreFolio senza Docker (ad es. su macchine con poche risorse) ed è anche il primo passo per gli sviluppatori che preparano un ambiente di sviluppo locale.

Per il deployment containerizzato, consulta la [Guida all'Installazione del Manuale Utente](../user/installation.md) o la [Guida a Docker Avanzato](docker_advanced.md).

---

## ✅ Prerequisiti

Prima di procedere, assicurati di avere i seguenti requisiti installati sul tuo sistema:

??? info "🐍 Python 3.13+"

    Python 3.13 è richiesto per il backend FastAPI.
    
    * **macOS**: Installa tramite Homebrew:
      ```bash
      brew install python@3.13
      ```
    * **Windows**: Scarica l'installer da [python.org](https://www.python.org/downloads/) (assicurati di spuntare "Add Python to PATH").
    * **Linux (Ubuntu/Debian)**:
      ```bash
      sudo apt update
      sudo apt install python3.13 python3.13-venv python3.13-dev
      ```

??? info "📦 Node.js 24+"

    Node.js è richiesto per compilare il frontend SvelteKit.
    
    * **macOS**: Installa tramite Homebrew:
      ```bash
      brew install node@24
      ```
    * **Windows/Linux**: Installa usando [nvm](https://github.com/nvm-sh/nvm) (Linux/macOS) o [nvm-windows](https://github.com/coreybutler/nvm-windows) (Windows), oppure scarica direttamente da [nodejs.org](https://nodejs.org/).

??? info "📋 Pipenv"

    Pipenv gestisce gli ambienti virtuali e le dipendenze per Python.
    
    * **Tutte le piattaforme**:
      ```bash
      pip install --user pipenv
      ```
      *Nota: Assicurati che i percorsi dei binari dell'utente (ad es. `~/.local/bin` su Linux/macOS o `%APPDATA%\Python` su Windows) siano aggiunti alla variabile `PATH` della tua shell.*

---

## 📋 Istruzioni di Configurazione

LibreFolio include uno script di orchestrazione principale, `dev.py`, per automatizzare le attività di gestione comuni.

!!! important "Prerequisito per l'Ambiente Python"

    Poiché `dev.py` importa moduli dal codice dell'applicazione backend, eseguirlo direttamente prima di installare le dipendenze risulterà in eccezioni di tipo `ImportError`. 
    
    Pertanto, la primissima volta che configuri il progetto sul tuo host, devi inizializzare l'ambiente virtuale eseguendo:
    ```bash
    pipenv install --dev
    ```
    Una volta configurato questo ambiente iniziale, puoi utilizzare in sicurezza `dev.py` per tutti i passaggi successivi.

!!! tip "Esecuzione di `dev.py` (Contesto Pipenv)"

    Poiché tutte le dipendenze del backend sono installate all'interno dell'ambiente virtuale gestito da `pipenv`, qualsiasi esecuzione di comandi sull'host deve essere eseguita in quel contesto:
    
    * **Comandi singoli**: Prefissa il tuo comando con `pipenv run` (ad es. `pipenv run ./dev.py server`).
    * **Shell interattiva**: Esegui prima `pipenv shell` per entrare nell'ambiente virtuale, dopodiché potrai eseguire direttamente `./dev.py` senza prefissi.
    
    *Nota: Se stai eseguendo comandi all'interno di un container Docker in esecuzione (ad es. tramite `docker exec`), **non** è necessario utilizzare `pipenv run` o `pipenv shell`. L'immagine Docker di produzione pre-installa tutte le dipendenze Python globalmente nell'ambiente di sistema del container.*

### 📥 1. Scarica il Progetto

Clona il repository:

```bash
git clone https://github.com/Librefolio/LibreFolio.git
cd LibreFolio
```

Oppure scarica l'ultimo pacchetto di rilascio da [GitHub Releases](https://github.com/Librefolio/LibreFolio/releases) ed estrailo.

### 📦 2. Installa le Dipendenze

Una volta inizializzato l'ambiente virtuale, installa tutte le rimanenti dipendenze Python, Node.js e del browser:

```bash
pipenv run ./dev.py install
```

Sotto il cofano, questo comando:

1. Inizializzerà l'ambiente virtuale Python e installerà i pacchetti tramite `pipenv`.
2. Installerà le dipendenze frontend SvelteKit tramite `npm`.
3. Installerà i binari del browser Playwright (utilizzati per la generazione di report PDF e i test E2E).

### ⚙️ 3. Configura l'Ambiente

Copia il file dell'ambiente di esempio per creare la tua configurazione `.env` attiva:

```bash
cp .env.example .env
```

Le impostazioni predefinite funzionano immediatamente. Di seguito sono riportate le variabili chiave:

* **`PORT`**: Porta di bind del server (predefinita: `6040`).
* **`LIBREFOLIO_DATA_DIR`**: Percorso della directory in cui sono memorizzati il database, i caricamenti e i log (predefinito: `./backend/data/prod`).
* **`LOG_LEVEL`**: Livello di dettaglio dei log (predefinito: `INFO`).

Per una descrizione completa di tutte le variabili d'ambiente supportate, consulta la [Guida alle Variabili d'Ambiente](configuration.md).

### 🚀 4. Avvia il Server

Per avviare il server FastAPI sull'host:

```bash
pipenv run ./dev.py server
```

Il server sarà disponibile all'indirizzo `http://localhost:6040`.

#### Opzioni del Comando Server

| Flag | Descrizione |
|------|-------------|
| `--host HOST` | Indirizzo di bind (predefinito: var d'ambiente `HOST` o `0.0.0.0`) |
| `--port PORT` / `-p PORT` | Porta di bind (predefinita: var d'ambiente `PORT` o `6040`) |
| `--workers N` / `-w N` | Numero di worker uvicorn (predefinito: 1, disabilita il ricaricamento automatico) |
| `--no-scheduler` | Disabilita le attività in background per la sincronizzazione dei dati di mercato |

### 👤 5. Accesso all'App & Creazione Utenti

La prima volta che accedi a LibreFolio nel tuo browser, vedrai una **pagina di registrazione** in cui potrai creare il tuo primo account. Il primo utente registrato diventa automaticamente l'amministratore del sistema.

Per gestire gli utenti o promuoverli ad amministratore tramite la riga di comando, consulta la [Guida agli Strumenti CLI per Utenti](cli_tools.md).

---

## 🗃️ Inizializzazione & Reset del Database

Quando si esegue l'applicazione per la prima volta, il database viene inizializzato automaticamente. Se hai bisogno di resettare il database per ripartire da zero, puoi farlo in due modi:

### 1. Comando da Terminale
Puoi eseguire il comando di pulizia dalla CLI del database:
```bash
pipenv run ./dev.py db create-clean
```
> [!WARNING]
> Questo comando eliminerà completamente il database SQLite esistente e ricreerà lo schema da zero. **Tutti i dati andranno persi in modo permanente.**

### 2. Reset Manuale
1. Ferma il server se è in esecuzione.
2. Elimina il file del database SQLite (situato di default in `backend/data/prod/sqlite/app.db`).
3. Riavvia il server; inizializzerà automaticamente un nuovo file di database SQLite.
