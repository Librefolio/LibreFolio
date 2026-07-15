# 🛡️ Manuale Amministratore

Questo manuale è rivolto agli amministratori di sistema e agli utenti avanzati che devono eseguire la manutenzione, gestire gli utenti o interagire con il sistema tramite la riga di comando.

## 📖 Panoramica

La maggior parte delle attività amministrative e di manutenzione viene gestita tramite l'interfaccia a riga di comando principale o configurata tramite variabili d'ambiente.

---

## 📚 Guide

La documentazione è organizzata in tre aree principali:

### 🐳 Deployment & Esposizione
- 📦 **[Installazione su Host](host_installation.md)**: Configurazione manuale utilizzando Python, Node.js e Pipenv direttamente sulla macchina host.
- 🐳 **[Docker Avanzato](docker_advanced.md)**: Deployment containerizzato tramite Docker Compose, collegamenti dei volumi e configurazione della proprietà GID/UID dell'utente.
- 🌐 **[Esporre in Sicurezza](service_exposure.md)**: Esporre in modo sicuro la tua istanza privata di LibreFolio su Internet.

### ⚙️ Configurazione di Sistema
- 📝 **[Variabili d'Ambiente](configuration.md)**: Elenco completo delle variabili `.env` supportate (`PORT`, `JWT_SECRET`, `LIBREFOLIO_DATA_DIR`, ecc.) e ordine di priorità di risoluzione.
- ⚙️ **[Impostazioni Globali](settings.md)**: Configura le impostazioni di runtime a livello di sistema (TTL della sessione, limiti di caricamento, intervalli di sincronizzazione dei dati di mercato).

### 🧹 Manutenzione & Operazioni
- 🛠️ **[Strumenti CLI Admin](cli_tools.md)**: Come utilizzare lo script `dev.py` per attività amministrative (gestione utenti, aggiornamenti del database).
- 📂 **[Struttura Filesystem](filesystem.md)**: Dettagli su dove sono memorizzati i database, i log, i caricamenti e le cartelle temporanee, e come eseguire i backup.

---

## 🔐 Autenticazione & Persistenza delle Sessioni

LibreFolio utilizza **JWT (JSON Web Tokens)** per l'autenticazione degli utenti. Di default:
- Se la variabile d'ambiente **`JWT_SECRET`** viene lasciata vuota nel file `.env`, il server genera una chiave segreta di firma casuale all'avvio. Questo garantisce la massima sicurezza, ma le sessioni degli utenti andranno perse se il server viene riavviato.
- Per mantenere le sessioni persistenti tra i riavvii del server (o quando si eseguono più istanze indipendenti del server dietro un load balancer), definisci una chiave **`JWT_SECRET`** stabile. Nota che i molteplici worker uvicorn avviati sullo stesso host condivideranno automaticamente il segreto generato dal processo padre, il che significa che la persistenza della sessione tra i worker è mantenuta anche quando `JWT_SECRET` viene lasciata vuota.

Per dettagli tecnici, consulta la pagina dedicata alla [Sicurezza e Autenticazione](../developer/architecture/security.md) nel manuale dello sviluppatore.
