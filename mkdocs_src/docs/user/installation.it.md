# 🐳 Installazione (Utente)

Questa guida spiega come installare e configurare LibreFolio per un uso regolare utilizzando Docker. Questo è il metodo consigliato per gli utenti che non intendono modificare il codice sorgente.

## ✅ Prerequisiti

- 🐋 **Docker**: [Installa Docker](https://docs.docker.com/get-docker/)
- 🔗 **Docker Compose**: Di solito incluso con Docker Desktop.

## 📥 1. Scarica il Progetto

Scarica l'ultima versione dalla pagina [GitHub Releases](https://github.com/ea-enel/LibreFolio/releases). Decomprimi la cartella.

In alternativa, puoi clonare il repository:

```bash
git clone https://github.com/ea-enel/LibreFolio.git
cd LibreFolio
```

## ⚙️ 2. Configura l'Ambiente

Il progetto utilizza un file `.env` per la configurazione. Un file di esempio è fornito.

1. **Copia il file di esempio**:
 ```bash
 cp .env.example .env
 ```

2. **Modifica `.env`** (Opzionale):
 - 🔌 `PORT`: Cambia la porta se `8000` è già in uso.
 - 📁 `LIBREFOLIO_DATA_DIR`: Cambia dove vengono archiviati i dati (predefinito: `./backend/data/prod`).

## 🚀 3. Esegui con Docker Compose

Questo singolo comando costruirà le immagini e avvierà l'applicazione.

```bash
docker-compose up -d
```

- 🔄 `-d` esegue l'applicazione in modalità detached (in background).
- ⏳ La prima volta che esegui questo comando, Docker scaricherà le immagini di base necessarie e costruirà l'applicazione, il che potrebbe richiedere alcuni minuti.

## 👤 4. Crea un Superuser

Per effettuare l'accesso, è necessario creare un account amministratore (superuser). Il primo utente creato diventa automaticamente il superuser.

```bash
docker-compose exec backend ./dev.py user create <username> <email> <password>
```

Sostituisci `<username>`, `<email>` e `<password>` con le tue credenziali.

## 🌐 5. Accedi a LibreFolio

L'applicazione è ora in esecuzione! Apri il browser e vai a:

**`http://localhost:8000`**

(O usa la porta configurata in `.env`).

## 🔄 Aggiornare LibreFolio

Per aggiornare a una nuova versione:

1. **Scarica l'ultimo codice**:
 ```bash
 git pull
 ```

2. **Ricostruisci e riavvia i container**:
 ```bash
 docker-compose up -d --build
 ```

3. **Applica le migrazioni del database** (se presenti):
 ```bash
 docker-compose exec backend pipenv run alembic upgrade head
 ```
