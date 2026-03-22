# 🛠️ Strumenti da Riga di Comando

LibreFolio fornisce lo script `dev.py` per le attività di amministrazione. Questa pagina illustra i comandi più rilevanti per gli **amministratori di sistema**.

!!! info "👩‍💻 Per Sviluppatori"
    Per i comandi specifici per lo sviluppo (build frontend, test runner, sincronizzazione API, audit i18n), consultare la [Guida all'Installazione per Sviluppatori](../developer/dev-installation.md).

---

## 🚀 Installazione

Installa tutte le dipendenze del progetto (Python e Node.js):

```bash
./dev.py install
```

---

## 🖥️ Server (Produzione)

### ▶️ Avvio del Server

```bash
# Avvio standard
./dev.py server

# Con numero di worker calcolato automaticamente (2 × (CPU-1))
./dev.py server --workers N

# Termina il processo esistente sulla porta prima di avviare
./dev.py server --force
```

!!! tip "Multi-worker"
    In produzione, utilizza `--workers` per eseguire più worker Uvicorn. Questo migliora la produttività ed è raccomandato per qualsiasi distribuzione con più di un core CPU.

---

## 👤 Gestione Utenti

La gestione degli utenti si effettua tramite i sottocomandi `./dev.py user`:

```bash
# Crea un utente (il primo utente diventa automaticamente amministratore)
./dev.py user create <username> <email> <password>

# Elenca tutti gli utenti
./dev.py user list

# Reimposta la password di un utente
./dev.py user reset <username> <new_password>

# Promuovi un utente ad amministratore
./dev.py user promote <username>

# Declassa un amministratore a utente normale
./dev.py user demote <username>
```

---

## ⚙️ Gestione del Sistema

### 🔧 Inizializza le Impostazioni Globali

```bash
./dev.py user init-settings
```

Popola il database con le [Impostazioni Globali](settings.md) predefinite, se non esistono già.

### 🗄️ Migrazioni del Database

```bash
# Applica le migrazioni in sospeso
./dev.py db upgrade
```

!!! warning "🗄️ Reset del Database"
    `./dev.py db create-clean` ricrea il database da zero — **TUTTI i dati andranno persi**. Utilizzare solo se è necessario ricominciare da zero.

---

## 📚 Documentazione

```bash
# Build e deploy della documentazione MkDocs su GitHub Pages
./dev.py mkdocs deploy

# Genera screenshot per la galleria (richiede server in esecuzione + dati di test)
./dev.py mkdocs gallery
```

---

## 📋 Albero Completo dei Comandi

Per un elenco completo di tutti i comandi disponibili:

```bash
./dev.py --help
```

!!! info "👩‍💻 Comandi per Sviluppatori"
    Comandi aggiuntivi per i flussi di lavoro di sviluppo:

    - **Frontend**: `./dev.py front build`, `front dev`, `front check` — consultare [Sviluppo Frontend](../developer/frontend/index.md)
    - **Test**: `./dev.py test all` — consultare [Guida ai Test](../developer/test-walkthrough/index.md)
    - **Client API**: `./dev.py api sync` — consultare [Panoramica API](../developer/api/overview.md)
    - **i18n audit**: consultare [Internazionalizzazione](../developer/frontend/i18n.md)
