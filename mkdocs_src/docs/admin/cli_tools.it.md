# 🛠️ Strumenti da Riga di Comando

LibreFolio fornisce lo script `dev.py` per le attività di amministrazione. Questa pagina copre i comandi più rilevanti per gli **amministratori di sistema**.

!!! info "👩‍💻 Per gli Sviluppatori"

    Per i comandi specifici per lo sviluppo (build del frontend, test runner, sincronizzazione API, audit i18n), consulta la [Guida all'Installazione per Sviluppatori](../developer/dev-installation.md).

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

# Con worker calcolati automaticamente (2 × (CPU-1))
./dev.py server --workers N

# Termina il processo esistente sulla porta prima di avviare
./dev.py server --force
```

!!! tip "Multi-worker"

    Per la produzione, usa `--workers` per eseguire più worker Uvicorn. Questo migliora il throughput ed è raccomandato per qualsiasi deployment con più di 1 core CPU.

---

## 👤 Gestione Utenti

La gestione degli utenti avviene tramite i sottocomandi di `./dev.py user`:

```bash
# Crea un utente (il primo utente diventa automaticamente admin)
./dev.py user create <username> <email> <password>

# Elenca tutti gli utenti
./dev.py user list

# Resetta la password di un utente
./dev.py user reset <username> <new_password>

# Promuovi un utente ad admin
./dev.py user promote <username>

# Rimuovi i privilegi di admin a un utente
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
# Applica le migrazioni in sospeso
./dev.py db upgrade
```

!!! warning "🗄️ Reset del Database"

    `./dev.py db create-clean` ricrea il database da zero — **tutti i dati andranno persi**. Usalo solo se hai bisogno di un nuovo inizio.

---

## 📚 Documentazione

```bash
# Crea e distribuisci la documentazione MkDocs su GitHub Pages
./dev.py mkdocs deploy

# Genera gli screenshot della galleria (richiede il server attivo + dati di test)
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
