# 🛡️ Manuale per amministratori

Questo manuale è destinato a chi installa e gestisce LibreFolio. La maggior parte delle operazioni di amministrazione avviene dalla riga di comando, tramite variabili d'ambiente o nelle schede **Impostazioni › Amministrazione** dell'app.

---

## 📚 Guide

### 🐳 Distribuzione ed esposizione
- 📦 **[Installazione sull'host](host_installation.md)**: Configurazione manuale con Python, Node.js e Pipenv direttamente sulla macchina host.
- 🐳 **[Docker avanzato](docker_advanced.md)**: Distribuzione containerizzata con Docker Compose, associazione dei volumi e configurazione della proprietà dell'utente tramite GID/UID.
- 🌐 **[Esposizione sicura](service_exposure.md)**: Esponi in sicurezza la tua istanza privata di LibreFolio con Tailscale, senza aprire porte sul router: perché è meglio dell'inoltro delle porte e i livelli privati, ossia una VPN per i tuoi dispositivi o un router di sottorete per l'intera rete domestica.
    - 🌍 **[Esposizione sicura: accesso pubblico con Funnel](service_exposure_funnel.md)**: Un indirizzo HTTPS pubblico con Tailscale Funnel: abilitazione di Funnel e delle ACL, un indirizzo per LibreFolio oppure uno per ciascun servizio con Docker.
- 🔍 **[Verifica della sicurezza della connessione](connection_checks.md)**: Verifica che i tuoi utenti si connettano in modo sicuro: la lista di controllo, l'indicatore, la vista del server e il cookie di sessione, e cosa fare quando un controllo fallisce.
    - 🧰 **[Verifica della sicurezza della connessione: dietro un proxy inverso](connection_proxy.md)**: Esegui LibreFolio dietro Nginx, Caddy, Traefik o Tailscale: le intestazioni da inviare, il proxy di cui LibreFolio si fida e l'indirizzo del visitatore.

### ⚙️ Configurazione di sistema
- 📝 **[Variabili d'ambiente](configuration.md)**: Crea il file `.env` e leggi le principali variabili supportate (`PORT`, `JWT_SECRET`, `LIBREFOLIO_DATA_DIR`, ecc.), con la precedenza che stabilisce quale valore prevale.
    - 🔐 **[Configurazione: segreti e impostazioni dei plugin](configuration_secrets.md)**: I segreti e come leggerli da file come i segreti Docker, la chiave dell'istanza e le impostazioni e le chiavi API dei plugin.
    - 🛡️ **[Configurazione: controlli e protezioni](configuration_security.md)**: Cosa controlla LibreFolio all'avvio, la Content-Security-Policy e la protezione dai frame, e come si arresta il server.
    - 👥 **[Configurazione: account e ricerca degli asset](configuration_accounts.md)**: Chi può registrarsi, i limiti sugli account e sugli accessi non riusciti, l'amministratore iniziale e l'ordine dei provider di prezzi nella ricerca degli asset.
- 📧 **[Email](email.md)**: Email SMTP opzionale: le variabili, esempi per i server più comuni e la scheda **Email** di Impostazioni › Amministrazione con la relativa email di prova.
    - 📬 **[Email: link e messaggi](email_flows.md)**: Le email con un link, inviti e reimpostazioni della password, password dimenticate e i relativi limiti, verifica dell'email e l'avviso di modifica dell'email.
    - 🛠️ **[Email: quando non funziona](email_troubleshooting.md)**: Gli errori, cosa dice il log e le note di sicurezza della configurazione SMTP.
- ⚙️ **[Impostazioni globali](settings.md)**: Configura le impostazioni di runtime a livello di sistema (TTL della sessione, limiti di caricamento, intervalli di sincronizzazione dei dati di mercato), scopri come muoverti nelle schede **Amministrazione** di Impostazioni e consulta i controlli **Sicurezza** dell'istanza.
- 👥 **[Utenti e inviti](users.md)**: Gestisci gli account dell'istanza dalla scheda **Utenti** dell'app: inviti, link per la reimpostazione della password, diritti di amministratore, disattivazione ed eliminazione.

### 🧹 Manutenzione e operazioni
- 🛠️ **[Strumenti di amministrazione CLI](cli_tools.md)**: Come usare lo script `dev.py` per attività amministrative (gestione utenti, aggiornamenti del database, backup dell'istanza).
- 💾 **[Backup, ripristino e trasferimento](backup_restore.md)**: Un unico archivio con l'intera istanza: crealo da Impostazioni › Amministrazione › Backup o dalla riga di comando, verificalo, ripristinalo e sposta LibreFolio tra due installazioni.
- 📂 **[Struttura del filesystem](filesystem.md)**: Dettagli su dove vengono archiviati database, log, caricamenti e cartelle temporanee, e su come eseguire i backup.

---

## 🔔 Notifiche di aggiornamento {: #update-notifications }

Quando un amministratore accede, LibreFolio controlla su GitHub se è disponibile una versione **stabile** più recente. Se esiste, la finestra **Nuova versione disponibile** mostra la tua versione e quella più recente affiancate, con un link **Come aggiornare** alla [guida all'aggiornamento](../user/installation.md#updating) e un link **Note di rilascio su GitHub**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="update-available-modal" alt="Finestra modale di aggiornamento disponibile con la versione corrente e la più recente">
</div>

- **Ricordamelo più tardi** chiude la finestra fino a un accesso successivo.
- **Salta questa versione** interrompe l'avviso automatico per quella versione; una versione ancora più recente verrà annunciata.
- Un rilascio viene annunciato solo quando la sua immagine Docker può essere scaricata, e la finestra attende che non ci siano altre finestre o guide aperte.
- Senza accesso a Internet, il controllo automatico fallisce in silenzio: nessun errore, nessun banner.
- Per controllare subito, usa **Verifica aggiornamenti** nella [cronologia delle modifiche](../user/settings/about.md#changelog-modal): segnala gli errori e anche le versioni saltate.

??? note "👥 Altri utenti — quando il controllo viene eseguito da chi non è amministratore"

    Per gli utenti che non sono amministratori, all'accesso non viene eseguito alcun controllo. Se uno di loro esegue **Verifica aggiornamenti** ed esiste un rilascio più recente, la finestra di dialogo **Aggiornamento disponibile — contatta un amministratore** elenca gli amministratori, con i relativi indirizzi e-mail quando disponibili, così sanno a chi rivolgersi.

---

## 🔐 Mantieni gli utenti connessi dopo un riavvio {: #session-persistence }

LibreFolio firma ogni sessione di accesso con una chiave segreta, `JWT_SECRET`.

- **Non impostata** (predefinito): a ogni avvio viene generata una nuova chiave casuale, quindi tutti devono accedere di nuovo dopo un riavvio o un aggiornamento.
- **Impostata**: le sessioni sopravvivono ai riavvii. Impostala anche se più server LibreFolio separati condividono gli stessi utenti dietro un bilanciatore di carico.

### 🔑 1. Genera una chiave

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Python non è disponibile sull'host? Esegui invece il comando all'interno del container:

```bash
docker exec librefolio python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 📝 2. Aggiungila al file `.env` e riavvia

```bash
JWT_SECRET=paste-the-generated-value-here
```

Riavvia LibreFolio (con Docker Compose: `docker compose up -d`). Mantieni segreta la chiave: chiunque la conosca può falsificare una sessione.

??? tip "🐳 Tieni la chiave fuori da `.env` — `JWT_SECRET_FILE`"

    Salva la chiave in un file, ad esempio un segreto Docker, e imposta `JWT_SECRET_FILE` sul suo percorso invece di `JWT_SECRET`, per esempio `JWT_SECRET_FILE=/run/secrets/jwt_secret`. Le regole e un esempio di Docker Compose sono in [Segreti](configuration_secrets.md#secrets).

I worker di un singolo `./dev.py server --workers …` condividono autonomamente un'unica chiave. La durata di una sessione è impostata dalla **Durata della sessione** in [Impostazioni globali](settings.md). Per i dettagli, consulta la pagina per sviluppatori [Architettura della sicurezza](../developer/architecture/security.md).
