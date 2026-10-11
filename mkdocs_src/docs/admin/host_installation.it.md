# 📦 Installazione su Host (Pipenv)

Questa guida installa LibreFolio direttamente sulla tua macchina con Python, Node.js e Pipenv, senza Docker: comodo su macchine con poche risorse, e il primo passo verso un ambiente di sviluppo.

Per Docker, consulta la [Installazione nel Manuale Utente](../user/installation.md) o la [Guida Avanzata a Docker](docker_advanced.md).

---

## ✅ Prerequisiti

Installa prima questi tre strumenti.

??? info "🐍 Python 3.13"

    Il backend richiede Python 3.13, la versione impostata nel `Pipfile` del progetto.

    * **macOS**: Installa usando Homebrew:
      ```bash
      brew install python@3.13
      ```
    * **Windows**: Scarica il programma di installazione da [python.org](https://www.python.org/downloads/) (assicurati di selezionare "Add Python to PATH").
    * **Linux (Ubuntu/Debian)**:
      ```bash
      sudo apt update
      sudo apt install python3.13 python3.13-venv python3.13-dev
      ```

??? info "📦 Node.js 24+"

    Node.js genera l'interfaccia web.

    * **macOS**: Installa tramite Homebrew:
      ```bash
      brew install node@24
      ```
    * **Windows/Linux**: Installa usando [nvm](https://github.com/nvm-sh/nvm) (Linux/macOS) o [nvm-windows](https://github.com/coreybutler/nvm-windows) (Windows), oppure scarica direttamente da [nodejs.org](https://nodejs.org/).

??? info "📋 Pipenv"

    Pipenv gestisce l'ambiente virtuale Python e i suoi pacchetti.

    * **Tutte le piattaforme**:
      ```bash
      pip install --user pipenv
      ```
      *Nota: Assicurati che i percorsi dei binari della tua user-base (ad esempio `~/.local/bin` su Linux/macOS o `%APPDATA%\Python` su Windows) siano aggiunti alla variabile `PATH` della tua shell.*

---

## 📋 Istruzioni di Configurazione

!!! tip "I comandi vengono eseguiti nell'ambiente Pipenv"

    I comandi `dev.py` iniziano con `pipenv run`, che li esegue nell'ambiente virtuale del progetto. Puoi anche accedervi una volta con `pipenv shell`, poi digitare `./dev.py …` senza il prefisso.

### 📥 1. Scarica il Progetto

```bash
git clone https://github.com/Librefolio/LibreFolio.git
cd LibreFolio
```

Oppure scarica il pacchetto della release più recente da [GitHub Releases](https://github.com/Librefolio/LibreFolio/releases) e decomprimilo.

### 🐍 2. Crea l'Ambiente Python

```bash
pipenv install --dev
```

Fallo prima di qualsiasi comando `dev.py`: `dev.py` necessita di questi pacchetti Python e, senza di essi, si interrompe con un `ModuleNotFoundError`.

### 📦 3. Installa le Altre Dipendenze

```bash
pipenv run ./dev.py install
```

Nell'ordine, installa:

1. nuovamente i pacchetti Python, con `pipenv install --dev`;
2. gli strumenti del progetto, con `npm install`;
3. le dipendenze dell'interfaccia web, con `npm ci` in `frontend/`;
4. il browser Chromium di Playwright, usato dai test end-to-end e dagli screenshot della documentazione. Se fallisce solo questo download, l'installazione si completa comunque.

### ⚙️ 4. Configura l'Ambiente

```bash
cp .env.example .env
```

I valori predefiniti funzionano così come sono. Le variabili principali:

| Variabile | Predefinito | Descrizione |
| --- | --- | --- |
| `PORT` | `6040` | Porta di bind del server. |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Directory in cui sono archiviati il database, i file caricati e i log (vedi [Struttura del Filesystem](filesystem.md)). |
| `LOG_LEVEL` | `INFO` | Verbosità del logging. |

Le altre variabili sono descritte nella [Guida alle Variabili d'Ambiente](configuration.md).

### 🚀 5. Avvia il Server

```bash
pipenv run ./dev.py server
```

Il primo avvio genera l'interfaccia web e la documentazione, quindi richiede qualche minuto. Poi apri `http://localhost:6040`. Per i worker, un'altra porta e le altre opzioni, vedi [Strumenti da Riga di Comando](cli_tools.md#start-the-server).

### 👤 6. Crea il Tuo Account

Apri LibreFolio nel browser e scegli **Registrati qui** sotto il modulo di accesso: il primo account registrato diventa l'amministratore. Per gestire gli utenti dal terminale, vedi [Strumenti da Riga di Comando](cli_tools.md).

---

## 🗃️ Inizializzazione e Reset del Database {: #database-reset }

Non c'è nulla da inizializzare manualmente: a ogni avvio, il server crea il database se manca e applica eventuali migrazioni in sospeso.

Per ricominciare da un **database vuoto**, usa uno dei due modi seguenti.

!!! warning "Tutti i dati vengono persi"

    Entrambi i modi eliminano definitivamente il database: utenti, broker, transazioni e impostazioni. Esegui prima un backup (vedi [Backup](filesystem.md#backup)).

### 🧹 Con `dev.py`

Ferma il server (il comando rifiuta di essere eseguito mentre il server è in esecuzione), poi:

```bash
pipenv run ./dev.py db create-clean
```

### 🗑️ Manualmente

1. Ferma il server se è in esecuzione.
2. Elimina il file del database SQLite (per impostazione predefinita `backend/data/prod/sqlite/app.db`).
3. Avvia il server: ne crea uno nuovo.

Entrambi i modi sostituiscono solo il database: i file caricati, i report dei broker e i log rimangono nella directory dei dati. Per un avvio completamente pulito, ferma invece il server ed elimina l'intera directory dei dati (per impostazione predefinita `backend/data/prod/`): il prossimo avvio la ricrea.
