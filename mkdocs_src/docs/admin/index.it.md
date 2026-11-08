# 🛡️ Manuale per amministratori

Per chi installa e gestisce LibreFolio. Quasi tutto si fa in uno di tre posti: da **riga di comando**, nel file **`.env`** (variabili d'ambiente) o nelle schede **Impostazioni › Amministrazione** dell'app.

---

## 📚 Guide

### 🐳 Distribuzione ed esposizione
- 📦 **[Installazione sull'host](host_installation.md)**: Python, Node.js e Pipenv direttamente sulla macchina host.
- 🐳 **[Docker avanzato](docker_advanced.md)**: Docker Compose, volumi e proprietà dei file tramite GID/UID.
- 🌐 **[Esposizione sicura](service_exposure.md)**: la tua istanza privata con Tailscale, senza aprire porte sul router: VPN per i tuoi dispositivi o router di sottorete per l'intera rete domestica.
    - 🌍 **[Esposizione sicura: accesso pubblico con Funnel](service_exposure_funnel.md)**: un indirizzo HTTPS pubblico con Tailscale Funnel, uno per LibreFolio o uno per ciascun servizio con Docker.
- 🔍 **[Verifica della sicurezza della connessione](connection_checks.md)**: la lista di controllo, l'indicatore, la vista del server e il cookie di sessione; cosa fare quando un controllo fallisce.
    - 🧰 **[Verifica della sicurezza della connessione: dietro un proxy inverso](connection_proxy.md)**: Nginx, Caddy, Traefik o Tailscale: le intestazioni da inviare, il proxy di fiducia e l'indirizzo del visitatore.

### ⚙️ Configurazione di sistema
- 📝 **[Variabili d'ambiente](configuration.md)**: il file `.env` e le variabili principali (`PORT`, `JWT_SECRET`, `LIBREFOLIO_DATA_DIR`, ecc.), con la precedenza tra i valori.
    - 🔐 **[Configurazione: segreti e impostazioni dei plugin](configuration_secrets.md)**: segreti letti da file (come i segreti Docker), chiave dell'istanza, impostazioni e chiavi API dei plugin.
    - 🛡️ **[Configurazione: controlli e protezioni](configuration_security.md)**: i controlli all'avvio, la Content-Security-Policy, la protezione dai frame e l'arresto del server.
    - 👥 **[Configurazione: account e ricerca degli asset](configuration_accounts.md)**: chi può registrarsi, limiti su account e accessi non riusciti, amministratore iniziale, ordine dei provider di prezzi.
- 📧 **[Email](email.md)**: SMTP opzionale: le variabili, esempi per i server più comuni, la scheda **Email** di Impostazioni › Amministrazione e l'email di prova.
    - 📬 **[Email: link e messaggi](email_flows.md)**: inviti e reimpostazioni della password, password dimenticate e relativi limiti, verifica dell'email, avviso di modifica dell'email.
    - 🛠️ **[Email: quando non funziona](email_troubleshooting.md)**: gli errori, cosa dice il log, note di sicurezza SMTP.
- ⚙️ **[Impostazioni globali](settings.md)**: le impostazioni di runtime (TTL della sessione, limiti di caricamento, intervalli di sincronizzazione dei dati di mercato), le schede **Amministrazione** e i controlli **Sicurezza** dell'istanza.
- 👥 **[Utenti e inviti](users.md)**: la scheda **Utenti** dell'app: inviti, link di reimpostazione della password, diritti di amministratore, disattivazione ed eliminazione.

### 🧹 Manutenzione e operazioni
- 🛠️ **[Strumenti di amministrazione CLI](cli_tools.md)**: lo script `dev.py` per gestione utenti, aggiornamenti del database e backup dell'istanza.
- 💾 **[Backup, ripristino e trasferimento](backup_restore.md)**: un unico archivio con l'intera istanza, da Impostazioni › Amministrazione › Backup o da riga di comando: crealo, verificalo, ripristinalo, sposta LibreFolio tra due installazioni.
- 📂 **[Struttura del filesystem](filesystem.md)**: dove stanno database, log, caricamenti e cartelle temporanee, e come eseguire i backup.

---

## 🔔 Notifiche di aggiornamento {: #update-notifications }

Quando un amministratore accede, LibreFolio controlla su GitHub se esiste una versione **stabile** più recente. Se esiste, la finestra **Nuova versione disponibile** mostra la tua versione e la più recente affiancate, con i link **Come aggiornare** ([guida all'aggiornamento](../user/installation.md#updating)) e **Note di rilascio su GitHub**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="update-available-modal" alt="Finestra modale di aggiornamento disponibile con la versione corrente e la più recente">
</div>

| Pulsante | Effetto |
| --- | --- |
| **Ricordamelo più tardi** | Chiude la finestra fino a un accesso successivo. |
| **Salta questa versione** | Nessun avviso automatico per quella versione; una ancora più recente verrà annunciata. |

- Un rilascio è annunciato solo quando la sua immagine Docker può essere scaricata; la finestra attende che non ci siano altre finestre o guide aperte.
- Senza accesso a Internet il controllo fallisce in silenzio: nessun errore, nessun banner.
- Per controllare subito: **Verifica aggiornamenti** nella [cronologia delle modifiche](../user/settings/about.md#changelog-modal). Segnala gli errori e anche le versioni saltate.

??? note "👥 Altri utenti — quando il controllo viene eseguito da chi non è amministratore"

    Per chi non è amministratore, all'accesso non viene eseguito alcun controllo. Se uno di loro esegue **Verifica aggiornamenti** ed esiste un rilascio più recente, la finestra **Aggiornamento disponibile — contatta un amministratore** elenca gli amministratori, con i relativi indirizzi email quando disponibili.

---

## 🔐 Mantieni gli utenti connessi dopo un riavvio {: #session-persistence }

`JWT_SECRET` è la chiave che firma ogni sessione di accesso.

- **Non impostata** (predefinito): nuova chiave casuale a ogni avvio, quindi tutti accedono di nuovo dopo un riavvio o un aggiornamento.
- **Impostata**: le sessioni sopravvivono ai riavvii. Impostala anche quando più server LibreFolio condividono gli stessi utenti dietro un bilanciatore di carico.

Per impostarla:

1. Genera una chiave. **Da terminale**, sull'host:

    ```bash
    python3 -c "import secrets; print(secrets.token_urlsafe(64))"
    ```

    Ottieni una stringa casuale da copiare. Senza Python sull'host, esegui il comando **nel container**:

    ```bash
    docker exec librefolio python -c "import secrets; print(secrets.token_urlsafe(64))"
    ```

2. Aggiungila **nel file `.env` di LibreFolio**:

    ```bash
    JWT_SECRET=paste-the-generated-value-here
    ```

3. Riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`.

    Da qui in avanti, un riavvio non disconnette nessuno.

!!! warning "🔒 Mantieni segreta la chiave"

    Chiunque la conosca può falsificare una sessione.

??? tip "🐳 Tieni la chiave fuori da `.env` — `JWT_SECRET_FILE`"

    Salva la chiave in un file, ad esempio un segreto Docker, e imposta `JWT_SECRET_FILE` sul suo percorso invece di `JWT_SECRET`: per esempio `JWT_SECRET_FILE=/run/secrets/jwt_secret`. Le regole e un esempio di Docker Compose sono in [Segreti](configuration_secrets.md#secrets).

- I worker di un singolo `./dev.py server --workers …` condividono da soli un'unica chiave.
- La durata di una sessione è la **Durata della sessione** in [Impostazioni globali](settings.md).
- Dettagli per sviluppatori: [Architettura della sicurezza](../developer/architecture/security.md).
