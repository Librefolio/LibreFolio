# 🛡️ Manuale per amministratori

Questo manuale è destinato agli amministratori di sistema e agli utenti avanzati che devono eseguire attività di manutenzione, gestire gli utenti o interagire con il sistema tramite la riga di comando.

## 📖 Panoramica

La maggior parte delle attività amministrative e di manutenzione viene gestita tramite l'interfaccia a riga di comando principale o configurata tramite variabili d'ambiente.

---

## 📚 Guide

La documentazione è organizzata in tre aree principali:

### 🐳 Distribuzione ed esposizione
- 📦 **[Installazione su host](host_installation.md)**: Installazione manuale utilizzando Python, Node.js e Pipenv direttamente sulla macchina host.
- 🐳 **[Docker avanzato](docker_advanced.md)**: Distribuzione containerizzata tramite Docker Compose, bind dei volumi e configurazione della proprietà utente tramite GID/UID.
- 🌐 **[Esporre in modo sicuro](service_exposure.md)**: Esposizione sicura della tua istanza privata di LibreFolio su internet.

### ⚙️ Configurazione del sistema
- 📝 **[Variabili d'ambiente](configuration.md)**: Elenco completo delle variabili `.env` supportate (`PORT`, `JWT_SECRET`, `LIBREFOLIO_DATA_DIR`, ecc.) e precedenza di risoluzione delle variabili.
- ⚙️ **[Impostazioni globali](settings.md)**: Configurazione delle impostazioni di runtime a livello di sistema (TTL delle sessioni, limiti di upload, intervalli di sincronizzazione dei dati di mercato).

### 🧹 Manutenzione e operazioni
- 🛠️ **[Strumenti CLI di amministrazione](cli_tools.md)**: Come usare lo script `dev.py` per le attività amministrative (gestione utenti, aggiornamenti del database).
- 📂 **[Struttura del filesystem](filesystem.md)**: Dettagli su dove vengono archiviati database, log, upload e cartelle temporanee, e su come eseguire i backup.

---

## 🔔 Notifiche di aggiornamento {: #update-notifications }

Dopo ogni accesso, il browser di un **amministratore** interroga l'API GitHub Releases per verificare la presenza di una versione **stabile** più recente di LibreFolio (bozze e pre-release non vengono mai prese in considerazione). Per non essere invadente:

- Il controllo viene eseguito **al massimo una volta ogni 24 ore** — l'ultimo risultato viene salvato nella memoria locale del browser.
- Nelle installazioni self-hosted senza accesso a Internet il recupero fallisce semplicemente in silenzio: **nessun errore, nessun banner**.

Quando esiste una versione stabile più recente, appare una **modale di aggiornamento disponibile** che mostra la versione corrente e l'ultima versione affiancate, con collegamenti alla **[guida all'aggiornamento](../user/installation.md#updating)** e alla pagina delle release di GitHub. Due modi per chiuderla:

- **"Più tardi"** — la modale si chiude e verrà riproposta al prossimo accesso.
- **"Salta questa versione"** — la modale non segnalerà mai più quella specifica versione (una versione futura più recente verrà comunque annunciata).

Gli utenti non amministratori non vengono mai interrogati al momento dell'accesso. Se un non amministratore controlla manualmente gli aggiornamenti dalla [modale del changelog](../user/settings/about.md#changelog-modal) e una versione più recente è disponibile, vede invece una finestra di dialogo che elenca gli amministratori dell'istanza (con gli indirizzi e-mail quando disponibili), così sa a chi chiedere l'aggiornamento.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="update-available-modal" alt="Update available modal with current and latest version">
</div>

---

## 🔐 Autenticazione e persistenza delle sessioni

LibreFolio utilizza **JWT (JSON Web Tokens)** per l'autenticazione degli utenti. Per impostazione predefinita:
- Se la variabile d'ambiente **`JWT_SECRET`** viene lasciata vuota nel tuo file `.env`, all'avvio il server genera una chiave di firma casuale. Questo offre la massima sicurezza, ma le sessioni utente andranno perse se il server viene riavviato.
- Per rendere persistenti le sessioni tra i riavvii del server (o quando si eseguono più istanze server indipendenti dietro un load balancer), definisci una chiave **`JWT_SECRET`** stabile. Nota che più worker uvicorn generati sullo stesso host condividono automaticamente il segreto generato dal processo padre, il che significa che la persistenza delle sessioni è mantenuta tra i worker anche quando `JWT_SECRET` viene lasciato vuoto.

Per i dettagli tecnici, consulta la pagina [Architettura di Sicurezza](../developer/architecture/security.md) dedicata agli sviluppatori.
