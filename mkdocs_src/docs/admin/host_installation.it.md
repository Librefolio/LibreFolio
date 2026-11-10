# 📦 Installazione su Host (Pipenv)

Installa LibreFolio sulla tua macchina senza Docker, con Python, Node.js e Pipenv: comodo con poche risorse, e primo passo verso un ambiente di sviluppo.

Per Docker, vedi la [Installazione nel Manuale Utente](../user/installation.md) o la [Guida Avanzata a Docker](docker_advanced.md).

---

## ✅ Prerequisiti

Installa prima questi tre strumenti.

??? info "🐍 Python 3.13"

    La versione impostata nel `Pipfile` del progetto.

    * **macOS**, con Homebrew:
      ```bash
      brew install python@3.13
      ```
    * **Windows**: scarica il programma di installazione da [python.org](https://www.python.org/downloads/) e seleziona "Add Python to PATH".
    * **Linux (Ubuntu/Debian)**:
      ```bash
      sudo apt update
      sudo apt install python3.13 python3.13-venv python3.13-dev
      ```

??? info "📦 Node.js 24+"

    Genera l'interfaccia web.

    * **macOS**, con Homebrew:
      ```bash
      brew install node@24
      ```
    * **Windows/Linux**: con [nvm](https://github.com/nvm-sh/nvm) (Linux/macOS) o [nvm-windows](https://github.com/coreybutler/nvm-windows) (Windows), oppure scarica da [nodejs.org](https://nodejs.org/).

??? info "📋 Pipenv"

    Gestisce l'ambiente virtuale Python e i suoi pacchetti.

    * **Tutte le piattaforme**:
      ```bash
      pip install --user pipenv
      ```
      Aggiungi al `PATH` della shell la cartella dei binari utente (`~/.local/bin` su Linux/macOS, `%APPDATA%\Python` su Windows).

---

## 📋 Istruzioni di Configurazione

!!! tip "I comandi vengono eseguiti nell'ambiente Pipenv"

    I comandi `dev.py` iniziano con `pipenv run`, che li esegue nell'ambiente virtuale del progetto.
    In alternativa entra una volta con `pipenv shell`, poi digita `./dev.py …` senza prefisso.

### 📥 1. Scarica il Progetto

**Dove:** terminale, nella cartella in cui vuoi il progetto.

```bash
git clone https://github.com/Librefolio/LibreFolio.git
cd LibreFolio
```

Risultato: la cartella `LibreFolio/`. In alternativa scarica e decomprimi l'ultima release da [GitHub Releases](https://github.com/Librefolio/LibreFolio/releases).

### 🐍 2. Crea l'Ambiente Python

**Dove:** terminale, cartella `LibreFolio/`.

```bash
pipenv install --dev
```

Risultato: l'ambiente virtuale con i pacchetti Python. Fallo prima di qualsiasi comando `dev.py`: senza, si interrompe con `ModuleNotFoundError`.

### 📦 3. Installa le Altre Dipendenze

**Dove:** terminale, cartella `LibreFolio/`.

```bash
pipenv run ./dev.py install
```

Risultato, nell'ordine:

1. di nuovo i pacchetti Python (`pipenv install --dev`);
2. gli strumenti del progetto (`npm ci`);
3. le dipendenze dell'interfaccia web (`npm ci` in `frontend/`);
4. il browser Chromium di Playwright, per i test end-to-end e gli screenshot della documentazione. Se fallisce solo questo download, l'installazione si completa comunque.

### ⚙️ 4. Configura l'Ambiente

**Dove:** terminale, cartella `LibreFolio/`; poi il file `.env` appena creato.

```bash
cp .env.example .env
```

Risultato: il file `.env` con valori predefiniti che funzionano così come sono. Le variabili principali:

| Variabile | Predefinito | Descrizione |
| --- | --- | --- |
| `PORT` | `6040` | Porta di bind del server. |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Directory di database, file caricati e log (vedi [Struttura del Filesystem](filesystem.md)). |
| `LOG_LEVEL` | `INFO` | Verbosità del logging. |

Le altre variabili: [Guida alle Variabili d'Ambiente](configuration.md).

### 🚀 5. Avvia il Server

**Dove:** terminale, cartella `LibreFolio/`.

```bash
pipenv run ./dev.py server
```

Risultato: LibreFolio risponde su `http://localhost:6040`. Il primo avvio genera interfaccia web e documentazione: qualche minuto. Worker, altra porta, altre opzioni: [Strumenti da Riga di Comando](cli_tools.md#start-the-server).

### 👤 6. Crea il Tuo Account

**Dove:** browser, `http://localhost:6040`, link **Registrati qui** sotto il modulo di accesso.

Risultato: il primo account registrato diventa l'amministratore. Per gestire gli utenti dal terminale, vedi [Strumenti da Riga di Comando](cli_tools.md). Per far creare l'amministratore a LibreFolio al primo avvio, vedi [L'Amministratore Iniziale](configuration_accounts.md#initial-admin).

---

## 🗃️ Inizializzazione e Reset del Database {: #database-reset }

Non c'è nulla da inizializzare: a ogni avvio il server crea il database se manca e applica le migrazioni in sospeso.

Per ricominciare da un **database vuoto**, usa uno dei due modi seguenti.

!!! warning "Tutti i dati vengono persi"

    Entrambi i modi eliminano definitivamente il database: utenti, broker, transazioni e impostazioni. Esegui prima un backup (vedi [Backup](filesystem.md#backup)).

### 🧹 Con `dev.py`

**Dove:** terminale, cartella `LibreFolio/`, con il server fermo (il comando rifiuta di essere eseguito mentre il server è in esecuzione).

```bash
pipenv run ./dev.py db create-clean
```

Risultato: un database nuovo e vuoto.

### 🗑️ Manualmente

**Dove:** la directory dei dati, per impostazione predefinita `backend/data/prod/`.

1. Ferma il server se è in esecuzione.
2. Elimina il file del database SQLite, per impostazione predefinita `backend/data/prod/sqlite/app.db`.
3. Avvia il server: ne crea uno nuovo.

Entrambi i modi sostituiscono solo il database: file caricati, report dei broker e log restano nella directory dei dati. Per un avvio completamente pulito, ferma il server ed elimina l'intera directory dei dati: il prossimo avvio la ricrea.
