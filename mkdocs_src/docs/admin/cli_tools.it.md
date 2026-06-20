# 🛠️ Strumenti da Riga di Comando

LibreFolio fornisce lo script `dev.py` per le attività di amministrazione. Questa pagina copre i comandi più rilevanti per gli **amministratori di sistema**.

!!! info "👩‍💻 Per gli Sviluppatori"

    Per i comandi specifici per lo sviluppo (build del frontend, test runner, sincronizzazione API, audit i18n), consulta la [Guida al Workflow per Sviluppatori](../developer/dev_workflow.md).

---
## 🖥️ Server (Produzione)

### ▶️ Avvio del Server

```bash
# Standard start
./dev.py server

# With auto-calculated workers (2 × (CPU-1))
./dev.py server --workers N

# Kill existing process on port before starting
./dev.py server --force
```

!!! tip "Multi-worker"

    Per la produzione, usa `--workers` per eseguire più worker Uvicorn. Questo migliora il throughput ed è raccomandato per qualsiasi deployment con più di 1 core CPU.

---

## 👤 Gestione Utenti

La gestione degli utenti avviene tramite i sottocomandi di `./dev.py user`:

```bash
# Create a user (first user becomes admin automatically)
./dev.py user create <username> <email> <password>

# List all users
./dev.py user list

# Reset a user's password
./dev.py user reset <username> <new_password>

# Promote a user to admin
./dev.py user promote <username>

# Demote an admin to regular user
./dev.py user demote <username>
```

---

## ⚙️ Gestione di Sistema

### 🔧 Inizializza Impostazioni Globali

```bash
./dev.py user init-settings
```

Inserisce i dati predefiniti delle [Impostazioni Globali](settings.md) nel database se non esistono già.

### 🗄️ Migrazioni del Database

```bash
# Apply pending migrations
./dev.py db upgrade
```

!!! warning "🗄️ Reset del Database"

    `./dev.py db create-clean` ricrea il database da zero — **tutti i dati andranno persi**. Usalo solo se hai bisogno di un nuovo inizio.

---

## 📚 Documentazione

```bash
# Build and deploy MkDocs documentation to GitHub Pages
./dev.py mkdocs deploy

# Generate gallery screenshots (requires running server + test data)
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

    - **Frontend**: `./dev.py front build`, `front dev`, `front check` — vedi [Sviluppo Frontend](../developer/frontend/index.md)
    - **Testing**: `./dev.py test all` — vedi [Walkthrough dei Test](../developer/test-walkthrough/index.md)
    - **API Client**: `./dev.py api sync` — vedi [Panoramica API](../developer/api/overview.md)
    - **i18n**: `./dev.py i18n audit` — vedi [Internazionalizzazione](../developer/frontend/i18n.md)
