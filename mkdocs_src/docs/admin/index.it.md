# 🛡️ Manuale di amministrazione

Questo manuale è destinato a chi installa ed esegue LibreFolio. La maggior parte delle operazioni di amministrazione avviene dalla riga di comando, tramite variabili d'ambiente o nella scheda **Admin** delle impostazioni dell'app.

---

## 📚 Guide

### 🐳 Distribuzione ed esposizione
- 📦 **[Installazione sull'host](host_installation.md)**: Configurazione manuale usando Python, Node.js e Pipenv direttamente sulla macchina host.
- 🐳 **[Docker avanzato](docker_advanced.md)**: Distribuzione containerizzata tramite Docker Compose, binding dei volumi e configurazione della proprietà GID/UID dell'utente.
- 🌐 **[Esposizione sicura](service_exposure.md)**: Esponi in modo sicuro la tua istanza privata di LibreFolio su Internet.

### ⚙️ Configurazione del sistema
- 📝 **[Variabili d'ambiente](configuration.md)**: Elenco completo delle variabili `.env` supportate (`PORT`, `JWT_SECRET`, `LIBREFOLIO_DATA_DIR`, ecc.) e precedenza di risoluzione delle variabili.
- ⚙️ **[Impostazioni globali](settings.md)**: Configura le impostazioni di runtime a livello di sistema (TTL sessione, limiti di caricamento, intervalli di sincronizzazione dei dati di mercato).

### 🧹 Manutenzione e operazioni
- 🛠️ **[Strumenti di amministrazione CLI](cli_tools.md)**: Come usare lo script `dev.py` per attività amministrative (gestione utenti, aggiornamenti del database).
- 📂 **[Struttura del filesystem](filesystem.md)**: Dettagli su dove vengono archiviati database, log, caricamenti e cartelle temporanee, e su come eseguire backup.

---

## 🔔 Notifiche di aggiornamento {: #update-notifications }

Quando un amministratore accede, LibreFolio controlla su GitHub se è disponibile una versione **stabile** più recente. Se esiste, la finestra **Nuova versione disponibile** mostra la tua versione e quella più recente affiancate, con un link **Come aggiornare** alla [guida all'aggiornamento](../user/installation.md#updating) e un link **Note di rilascio su GitHub**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="update-available-modal" alt="Modale di aggiornamento disponibile con versione corrente e più recente">
</div>

- **Ricordamelo più tardi** chiude la finestra fino a un accesso successivo.
- **Salta questa versione** interrompe la richiesta automatica per quella versione; una più recente viene annunciata
  di nuovo.
- Una versione viene annunciata solo quando la sua immagine Docker può essere scaricata, e la finestra attende che
  nessun'altra finestra o guida sia aperta.
- Senza accesso a Internet, il controllo automatico fallisce silenziosamente: nessun errore, nessun banner.
- Per controllare subito, usa **Controlla aggiornamenti** nel
  [changelog](../user/settings/about.md#changelog-modal): segnala gli errori e anche le versioni che
  hai saltato.

??? note "👥 Altri utenti — quando qualcuno che non è un amministratore esegue il controllo"

    Per gli utenti che non sono amministratori, non viene eseguito alcun controllo all'accesso. Se uno di loro esegue
    **Controlla aggiornamenti** ed esiste una versione più recente, la
    finestra di dialogo **Aggiornamento disponibile — contatta un amministratore** elenca gli amministratori, con i loro
    indirizzi e-mail quando disponibili, così sanno a chi rivolgersi.

---

## 🔐 Mantieni gli utenti connessi dopo un riavvio {: #session-persistence }

LibreFolio firma ogni sessione di login con una chiave segreta, `JWT_SECRET`.

- **Non impostata** (impostazione predefinita): viene creata una nuova chiave casuale a ogni avvio, quindi tutti devono accedere
  di nuovo dopo un riavvio o un aggiornamento.
- **Impostata**: le sessioni sopravvivono ai riavvii. Impostala anche se diversi server LibreFolio separati condividono
  gli stessi utenti dietro un load balancer.

### 🔑 1. Genera una chiave

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Non c'è Python sull'host? Esegui invece il comando all'interno del container:

```bash
docker exec librefolio python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 📝 2. Aggiungila al file `.env` e riavvia

```bash
JWT_SECRET=paste-the-generated-value-here
```

Riavvia LibreFolio (con Docker Compose: `docker compose up -d`). Mantieni la chiave privata: chiunque la conosca può falsificare una sessione.

I worker di un singolo `./dev.py server --workers …` condividono una chiave tra loro. La durata di una sessione è la **Durata sessione** in [Impostazioni globali](settings.md). Per i dettagli, consulta la pagina per sviluppatori [Architettura di sicurezza](../developer/architecture/security.md).
