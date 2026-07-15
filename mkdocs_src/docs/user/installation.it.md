# 🐳 Installazione con Docker (Utente)

Questa guida spiega come installare ed eseguire LibreFolio per l'uso regolare utilizzando l'immagine Docker ufficiale precompilata. Questo è il metodo più semplice e raccomandato per gli utenti finali.

Non è necessario installare strumenti di sviluppo o compilare il codice sulla propria macchina host (nessun requisito di Python, Node.js o Pipenv).

---

## ✅ Prerequisiti

Prima di iniziare, assicurati di aver installato **Docker** (che include Docker Compose) sulla tua macchina host. A seconda del tuo sistema operativo, puoi seguire questi passaggi:

=== "Linux"

    La maggior parte delle distribuzioni Linux consente l'installazione tramite i repository ufficiali.
    
    Per distribuzioni basate su Debian/Ubuntu:
    ```bash
    sudo apt-get update
    sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    ```
    
    !!! warning "Permessi del gruppo Docker (Linux)"
        Su Linux, il tuo utente di sistema deve appartenere al gruppo `docker` per poter eseguire i comandi senza `sudo`:
        ```bash
        sudo usermod -aG docker $USER
        ```
        Quindi **effettua il logout e accedi nuovamente** (oppure esegui `newgrp docker`) per applicare le modifiche alla sessione corrente del terminale.

=== "macOS"

    Su macOS, il modo consigliato è installare **Docker Desktop**:
    
    - [Scarica Docker Desktop per Mac](https://docs.docker.com/desktop/install/mac-install/) (disponibile per Apple Silicon o Intel).
    - In alternativa, se utilizzi Homebrew, puoi installarlo da terminale:
      ```bash
      brew install --cask docker
      ```

=== "Windows"

    Su Windows, installa **Docker Desktop**:
    
    - Scarica e installa [Docker Desktop per Windows](https://docs.docker.com/desktop/install/windows-install/).
    - Assicurati di abilitare il backend basato su **WSL 2** durante l'installazione per ottenere le migliori prestazioni.

---

## 🚀 Installazione Passo-Passo

### 📁 1. Crea una cartella per il progetto

📂 Naviga nella cartella in cui desideri salvare il progetto (ad esempio la tua cartella utente o dei documenti), crea una nuova directory per LibreFolio e accedi ad essa:

```bash
# 🏠 Vai alla cartella principale dove vuoi posizionare il progetto (es. Documenti)
cd /percorso/della/tua/cartella

# 📁 Crea e accedi alla cartella di LibreFolio
mkdir librefolio
cd librefolio
```

### 📥 2. Ottieni i file di configurazione base

⚙️ Per avviare LibreFolio, avrai bisogno del file `docker-compose.yml` (che descrive lo stack dei container) e del file `.env` (che contiene le impostazioni personalizzate del tuo ambiente).

⬇️ Puoi scaricarli direttamente dal repository GitHub ufficiale utilizzando uno dei seguenti comandi:

=== "wget"

    ```bash
    # 📥 Scarica il file docker-compose.yml ufficiale
    wget https://raw.githubusercontent.com/Librefolio/LibreFolio/main/docker-compose.prod.yml -O docker-compose.yml

    # 🔑 Scarica il file .env.example e salvalo come .env
    wget https://raw.githubusercontent.com/Librefolio/LibreFolio/main/.env.example -O .env
    ```

=== "curl"

    ```bash
    # 📥 Scarica il file docker-compose.yml ufficiale
    curl -L https://raw.githubusercontent.com/Librefolio/LibreFolio/main/docker-compose.prod.yml -o docker-compose.yml

    # 🔑 Scarica il file .env.example e salvalo come .env
    curl -L https://raw.githubusercontent.com/Librefolio/LibreFolio/main/.env.example -o .env
    ```

✍️ In alternativa, puoi creare manualmente un file chiamato `docker-compose.yml` e incollarvi all'interno il seguente codice:

```yaml
services:
  librefolio:
    image: ghcr.io/librefolio/librefolio:latest
    container_name: librefolio
    restart: unless-stopped
    ports:
      - "6040:6040"
    volumes:
      - ./librefolio-data:/app/backend/data/prod-docker
    env_file: .env
    environment:
      - LIBREFOLIO_DATA_DIR=/app/backend/data/prod-docker
      - HOST=0.0.0.0
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:6040/api/v1/system/health')"]
      interval: 30s
      timeout: 10s
      start_period: 15s
      retries: 3
```

💡 *(Se non hai scaricato il file `.env.example`, rimuovi la riga `env_file: .env` dal codice sopra, o crea un file `.env` vuoto, per evitare errori all'avvio).*

### ▶️ 3. Avvia l'applicazione

🚀 Avvia il container in background (in modalità *detached*) eseguendo:

```bash
docker compose up -d
```

📦 Docker scaricherà l'immagine ufficiale dal registro GitHub Container Registry (GHCR) e avvierà LibreFolio.

### 🌐 4. Accedi a LibreFolio

🖥️ Una volta avviato il container, apri il browser e vai su:

**`http://localhost:6040`**

👤 Al primo accesso, ti verrà presentata la pagina di registrazione per creare l'account amministratore di LibreFolio. Il primo utente che si registra riceverà automaticamente i privilegi di amministratore.

!!! tip "Visualizzazione dello Stato e dei Log con Portainer"

    Se preferisci una comoda interfaccia grafica per monitorare lo stato del tuo container LibreFolio e leggerne i log in tempo reale, ti consigliamo l'uso di **[Portainer](https://github.com/portainer/portainer)**, uno strumento di gestione Docker leggero ed estremamente diffuso.

### 📶 5. Accesso in Rete Locale e Remoto

Una volta avviato, LibreFolio sarà raggiungibile:

- 💻 Direttamente dal **computer host** visitando `http://localhost:6040`.
- 📱 Da **altri dispositivi sulla stessa rete locale (LAN)** (es. smartphone, tablet, altri PC) inserendo nel browser l'indirizzo IP locale del computer host (es. `http://192.168.1.100:6040`).

#### 🛡️ Configurazione del Firewall (facoltativo)
Se non riesci ad accedere a LibreFolio da altri dispositivi della rete locale, potrebbe essere necessario aprire la porta `6040` nel firewall del computer host:

=== "Debian / Ubuntu (UFW)"

    ```bash
    sudo ufw allow 6040/tcp
    ```

=== "RHEL / Rocky Linux / Fedora (Firewalld)"

    ```bash
    sudo firewall-cmd --add-port=6040/tcp --permanent
    sudo firewall-cmd --reload
    ```

#### 🌐 Accesso Remoto
Per accedere a LibreFolio in sicurezza quando sei fuori casa (fuori dalla rete locale), sei libero di configurare la soluzione che preferisci (come un reverse proxy con certificato SSL).

Tuttavia, per la massima semplicità e sicurezza senza dover aprire porte sul tuo router, **consigliamo l'uso di Tailscale**. Trovi tutti i dettagli e la guida passo-passo nella pagina [Esposizione con Tailscale](../admin/service_exposure.md).

---

## ⚙️ Opzioni di Configurazione

Tutte le impostazioni di LibreFolio (come porte, valuta di base e chiavi di sicurezza delle sessioni) sono gestite tramite variabili d'ambiente nel file `.env`.

Per i dettagli completi su ciascuna opzione e sulle modalità di risoluzione delle variabili, consulta la [Guida alla Configurazione nel Manuale Amministratore](../admin/configuration.md).

---

## 💾 Backup dei Dati

Tutti i dati di LibreFolio (database SQLite, file caricati dagli utenti, report caricati e log) sono salvati localmente all'interno della cartella `./librefolio-data` creata a fianco del file `docker-compose.yml`.

Per le istruzioni dettagliate su cosa salvare e su come eseguire backup consistenti, consulta la [Sezione Backup del Manuale Amministratore](../admin/filesystem.md#backup).

---

## 🔄 Aggiornamento di LibreFolio

### ⚠️ Attenzione: Stato di Alpha
LibreFolio è attualmente in fase di sviluppo **Alpha**. Questo significa che tra una versione e l'altra potrebbero esserci modifiche strutturali o migrazioni del database che potrebbero impedire l'avvio della nuova versione, richiedendo un intervento manuale o il ripristino di una versione precedente.

- Usando il tag `:latest` nel file `docker-compose.yml`, riceverai subito le ultime funzionalità ma ti esporrai a potenziali incompatibilità durante gli aggiornamenti automatici.
- Se preferisci stabilità e controllo assoluto, ti consigliamo di bloccare l'immagine sostituendo `:latest` con un tag di versione specifico (ad esempio, `ghcr.io/librefolio/librefolio:v0.10.0`).

### 🛠️ 1. Aggiornamento Manuale

Per aggiornare LibreFolio manualmente all'ultima versione disponibile:

```bash
# 🛑 Arresta il container in esecuzione
docker compose down

# 📥 Scarica la versione più recente dell'immagine dal registro
docker compose pull

# 🚀 Riavvia LibreFolio applicando la nuova immagine
docker compose up -d
```

Le migrazioni del database verranno eseguite automaticamente all'avvio del container.

### 🤖 2. Aggiornamento Automatico (Watchtower)

Se desideri automatizzare l'aggiornamento del container non appena viene rilasciata una nuova immagine sul registro, puoi utilizzare **Watchtower** (ti consigliamo il fork attivo e aggiornato di [nicholas-fedor/watchtower](https://github.com/nicholas-fedor/watchtower)).

!!! note "Comportamento di default"

    Di default, Watchtower monitora e aggiorna tutti i container attivi sul sistema. Per maggiori dettagli e opzioni avanzate, consulta il [repository ufficiale del progetto](https://github.com/nicholas-fedor/watchtower).

Per comodità, se desideri limitare il controllo del software solo a LibreFolio ed eseguire la verifica a cadenza settimanale (ad esempio, ogni domenica alle 4:00 del mattino tramite espressione Cron), puoi avviare Watchtower con questo comando:

```bash
docker run -d \
  --name watchtower \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e TZ=Europe/Rome \
  nicholas-fedor/watchtower \
  --cleanup \
  --schedule "0 0 4 * * 0" \
  librefolio
```
💡 *(Questo comando avvia Watchtower in background con accesso al socket di Docker. Verificherà la presenza di nuove immagini sul registro solo per il container `librefolio` ogni domenica alle 04:00:00, eliminando le vecchie immagini per risparmiare spazio. Modifica `TZ` impostando il tuo fuso orario di riferimento).*

### 🔌 3. Altre Alternative di Gestione

Se desideri un approccio diverso o più controllo sulle notifiche e sull'applicazione delle release, esistono valide alternative:

- **[WUD (What's Up Docker)](https://github.com/fmartinou/whats-up-docker)**  
  Tool moderno per homelab dotato di una comoda **interfaccia web**.  
  È estremamente modulare e supporta notifiche su Telegram, Discord e Gotify.  
  Permette di inviare avvisi sulle nuove release senza aggiornare automaticamente, lasciandoti la scelta di quando farlo.  
  
- **[Diun (Docker Image Update Notifier)](https://github.com/crazy-max/diun)**  
  Un notificatore puro, leggero e sicuro.  
  Non richiede i permessi di scrittura sul socket di Docker.  
  Monitora i registri delle immagini in sola lettura e ti avvisa quando viene pubblicata una nuova versione di LibreFolio.

