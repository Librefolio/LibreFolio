# 🐳 Installazione con Docker (Utente)

Questa guida installa LibreFolio con l'immagine Docker ufficiale precostruita: il modo più semplice e consigliato per eseguirlo a casa.

Ti serve solo Docker: niente Python, Node.js o Pipenv, e nulla da compilare.

---

## ✅ Prerequisiti

Installa **Docker**, che include Docker Compose, sul computer che eseguirà LibreFolio:

=== "Linux"

    Segui la guida ufficiale di Docker per la tua distribuzione: [Install Docker Engine](https://docs.docker.com/engine/install/). Su Debian e Ubuntu, la guida aggiunge prima il repository dei pacchetti di Docker, poi installa:

    ```bash
    sudo apt-get update
    sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    ```

    !!! warning "Permessi del gruppo Docker (Linux)"

        Su Linux, il tuo utente di sistema deve appartenere al gruppo `docker` per eseguire i comandi senza `sudo`:

        ```bash
        sudo usermod -aG docker $USER
        ```

        Poi **esci e riaccedi** (oppure esegui `newgrp docker`) per applicare le modifiche alla sessione corrente del terminale.

=== "macOS"

    Installa **Docker Desktop**:

    - [Scarica Docker Desktop per Mac](https://docs.docker.com/desktop/install/mac-install/) (Apple Silicon o Intel).
    - Oppure, con Homebrew:

      ```bash
      brew install --cask docker-desktop
      ```

=== "Windows"

    Installa **Docker Desktop**:

    - Scarica e installa [Docker Desktop per Windows](https://docs.docker.com/desktop/install/windows-install/).
    - Abilita il backend **WSL 2** durante l'installazione per ottenere le prestazioni migliori.

---

## 🚀 Installazione passo dopo passo

### 📁 1. Crea una cartella di progetto

Apri un terminale, vai nella cartella dove vuoi conservare LibreFolio (per esempio la cartella Documenti), poi crea una cartella `librefolio` ed entraci:

```bash
# 🏠 Go to the main folder where you want to place the project (e.g. Documents)
cd /path/to/your/folder

# 📁 Create and enter the LibreFolio folder
mkdir librefolio
cd librefolio
```

### 📥 2. Ottieni i file di configurazione di base

LibreFolio richiede due file: `docker-compose.yml`, che descrive il container, e `.env`, che contiene le tue impostazioni. Scaricali entrambi dal repository ufficiale con uno di questi comandi:

=== "wget"

    ```bash
    # 📥 Download the official docker-compose.yml file
    wget https://raw.githubusercontent.com/Librefolio/LibreFolio/main/docker-compose.prod.yml -O docker-compose.yml

    # 🔑 Download the .env.example file and save it as .env
    wget https://raw.githubusercontent.com/Librefolio/LibreFolio/main/.env.example -O .env
    ```

=== "curl"

    ```bash
    # 📥 Download the official docker-compose.yml file
    curl -L https://raw.githubusercontent.com/Librefolio/LibreFolio/main/docker-compose.prod.yml -o docker-compose.yml

    # 🔑 Download the .env.example file and save it as .env
    curl -L https://raw.githubusercontent.com/Librefolio/LibreFolio/main/.env.example -o .env
    ```

Lo stack utilizza l'immagine ufficiale dal GitHub Container Registry (GHCR) e conserva tutti i tuoi dati in una cartella `LibreFolio-data` accanto a `docker-compose.yml`.

??? example "✍️ Preferisci scrivere `docker-compose.yml` a mano?"

    Crea un file chiamato `docker-compose.yml` e incolla questo contenuto, lo stesso servizio del file ufficiale:

    ```yaml
    services:
      librefolio:
        image: ${LIBREFOLIO_IMAGE:-ghcr.io/librefolio/librefolio:latest}
        container_name: librefolio
        restart: unless-stopped
        ports:
          - "${PORT:-6040}:6040"
        volumes:
          - ./LibreFolio-data:/app/backend/data/prod-docker
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

    La riga `env_file: .env` richiede un file `.env` nella stessa cartella: scaricalo come mostrato sopra, oppure creane uno vuoto, altrimenti Docker si arresta con un errore.

### ▶️ 3. Avvia l'applicazione

Avvia LibreFolio in background:

```bash
docker compose up -d
```

Docker scarica l'immagine ufficiale da GHCR e avvia LibreFolio. Il tag `latest` è la [variante light](#image-variants-full-and-light) dell'immagine, l'impostazione predefinita consigliata.

### 🌐 4. Accedi a LibreFolio

Apri il browser su **`http://localhost:6040`**.

Alla prima visita, LibreFolio mostra la pagina di registrazione: il primo account che crei diventa automaticamente l'**amministratore**.

??? tip "🖥️ Controlla lo stato e i log (facoltativo)"

    Dal terminale, `docker compose logs -f` segue i log di LibreFolio (`Ctrl+C` interrompe la visualizzazione). Per una vista grafica dei tuoi container e dei loro log in tempo reale, prova **[Portainer](https://github.com/portainer/portainer)**, uno strumento di gestione Docker leggero e molto diffuso.

### 📶 5. Accesso dalla rete locale e da remoto

Una volta avviato, LibreFolio è raggiungibile:

- 💻 dal **computer host**, su `http://localhost:6040`;
- 📱 da **altri dispositivi sulla stessa rete locale** (smartphone, tablet, altri PC), all'indirizzo IP locale del computer host, per esempio `http://192.168.1.100:6040`.

??? note "🛡️ Firewall — solo se gli altri dispositivi non riescono a connettersi"

    Apri la porta `6040` nel firewall del computer host:

    === "Debian / Ubuntu (UFW)"

        ```bash
        sudo ufw allow 6040/tcp
        ```

    === "RHEL / Rocky Linux / Fedora (Firewalld)"

        ```bash
        sudo firewall-cmd --add-port=6040/tcp --permanent
        sudo firewall-cmd --reload
        ```

🌍 **Fuori casa**, usa la soluzione che preferisci, come un reverse proxy con un certificato SSL. Per la configurazione più semplice e sicura, senza aprire porte sul router, **consigliamo Tailscale**: vedi [Esposizione con Tailscale](../admin/service_exposure.md).

---

## 🏷️ Varianti dell'immagine: Full e Light {: #image-variants-full-and-light }

L'immagine ufficiale è disponibile in due varianti. Entrambe contengono l'intera applicazione e tutte le pagine di testo della documentazione, in tutte e quattro le lingue; differiscono solo per gli screenshot della documentazione:

- 🪶 **Light** (l'impostazione predefinita consigliata): **senza gli screenshot della documentazione**, che vengono caricati su richiesta dal sito della documentazione online. Circa 450 MB da scaricare.
- 🗂️ **Full**: include anche gli screenshot della documentazione (desktop e mobile, in tutte e quattro le lingue, in tema chiaro e scuro), così la documentazione integrata funziona completamente offline. Un download più grande.

Ogni release è pubblicata con questi tag:

| Tag | Variante | Usalo per |
|-----|---------|-----------|
| `latest` | 🪶 Light | Seguire la release più recente (il tag usato dal `docker-compose.yml` qui sopra) |
| `X.Y.Z` (es. `1.1.0`) | 🗂️ Full | Fissare una versione, con la documentazione completamente offline |
| `X.Y.Z-light` (es. `1.1.0-light`) | 🪶 Light | Fissare una versione e restare sulla variante light |

- I tag di versione non hanno la `v`: `1.1.0`, non `v1.1.0` come sulla pagina delle release di GitHub.
- Non esiste un tag `latest-light`: `latest` è già la variante light.
- La variante full esiste solo sotto un numero di versione. Usarla significa fissare una versione, e un'immagine fissata non si aggiorna automaticamente alle release più recenti (vedi [Aggiornare LibreFolio](#updating)).

!!! warning "La variante light richiede internet per gli screenshot della documentazione"

    Con la variante light (il tag `latest` o qualsiasi tag `-light`), visualizzare gli screenshot all'interno della documentazione integrata (menu Aiuto) richiede una **connessione internet**, perché vengono recuperati dal sito della documentazione online. Tutto il resto — l'intera applicazione e tutto il testo della documentazione — è fornito dall'immagine stessa.

??? example "🗂️ Passare alla variante full"

    Aggiungi questa riga al tuo file `.env`, con la versione che desideri:

    ```bash
    LIBREFOLIO_IMAGE=ghcr.io/librefolio/librefolio:1.1.0
    ```

    Poi esegui `docker compose up -d`: Docker scarica quell'immagine e riavvia LibreFolio su di essa. Se il tuo `docker-compose.yml` ha una riga `image:` fissa, senza `LIBREFOLIO_IMAGE`, metti il tag su quella riga.

---

## ⚙️ Opzioni di configurazione

Tutte le impostazioni di LibreFolio, come la porta e la chiave di sicurezza della sessione, risiedono nel file `.env` come variabili d'ambiente.

Per ogni opzione e per come viene risolto il suo valore, vedi la [Guida alla configurazione nel Manuale di amministrazione](../admin/configuration.md).

---

## 💾 Backup dei dati {#data-backup}

Tutti i tuoi dati (il database SQLite, i file caricati, i report dei broker e i log) risiedono nella cartella `./LibreFolio-data` accanto a `docker-compose.yml`. Esegui il backup di quella cartella, fermando prima il container per ottenere una copia coerente.

Per cosa salvare e come, vedi la [sezione Backup del Manuale di amministrazione](../admin/filesystem.md#backup).

---

## 🔄 Aggiornare LibreFolio {#updating}

Le migrazioni del database vengono eseguite automaticamente all'avvio del container e sono progettate per conservare i dati esistenti, mentre alcune funzionalità, come la simulazione di rischio **What if…?**, sono [ancora in beta](../financial-theory/technical-analysis/risk-metrics/simulation-modes.md#why-beta) e possono cambiare tra una versione e l'altra. Fai un [backup](#data-backup) prima di aggiornare: è il modo per tornare indietro se qualcosa va storto.

- Con il tag `latest` ottieni sempre la release più recente, insieme a qualsiasi cambiamento che essa comporta.
- Per aggiornare solo quando decidi tu, fissa una versione invece di `latest`: `ghcr.io/librefolio/librefolio:1.1.0` (variante full) o `ghcr.io/librefolio/librefolio:1.1.0-light` (variante light). Vedi [Varianti dell'immagine](#image-variants-full-and-light).

### 🛠️ 1. Aggiornamento manuale {: #manual-update }

Per aggiornare LibreFolio all'immagine più recente:

```bash
# 🛑 Stop the running container
docker compose down

# 📥 Download the newest version of the image from the registry
docker compose pull

# 🚀 Restart LibreFolio using the new image
docker compose up -d
```

Le migrazioni del database vengono eseguite da sole all'avvio del container.

??? warning "🧯 LibreFolio non riparte dopo un aggiornamento"

    Se una migrazione del database fallisce, LibreFolio si ferma e il suo log (`docker compose logs librefolio`) mostra `Failed to apply database migrations` con l'errore; Docker continua poi a riavviare il container. Fermalo con `docker compose down`, ripristina il tuo [backup](#data-backup) di `LibreFolio-data`, e fissa la versione che stavi usando finché il problema non è risolto.

### 🤖 2. Aggiornamento automatico (Watchtower)

**Watchtower** aggiorna i container non appena viene pubblicata una nuova immagine. Consigliamo il suo fork attivo e aggiornato, [nicholas-fedor/watchtower](https://github.com/nicholas-fedor/watchtower). Per impostazione predefinita controlla **ogni** container in esecuzione sul sistema: questo comando lo limita a LibreFolio e verifica una volta a settimana, la domenica alle 04:00:

```bash
docker run -d \
  --name watchtower \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e TZ=Europe/Rome \
  nickfedor/watchtower \
  --cleanup \
  --schedule "0 0 4 * * 0" \
  librefolio
```

- `--schedule` accetta un'espressione cron con sei campi, con i secondi per primi; imposta `TZ` sul tuo fuso orario.
- `--cleanup` elimina le vecchie immagini per risparmiare spazio.
- Per ogni altra opzione, vedi il [repository del progetto](https://github.com/nicholas-fedor/watchtower).

### 🔌 3. Altre alternative di gestione

Per un maggiore controllo sulle notifiche e su quando aggiornare:

- **[WUD (What's Up Docker)](https://github.com/getwud/wud)**: uno strumento per homelab con una comoda **interfaccia web** e notifiche via Telegram, Discord, Gotify e altro. Può avvisarti delle nuove release senza aggiornare, lasciando a te la scelta di quando farlo.
- **[Diun (Docker Image Update Notifier)](https://github.com/crazy-max/diun)**: un notificatore leggero che non necessita di accesso in scrittura al socket Docker. Monitora i registry delle immagini in sola lettura e ti avvisa quando viene pubblicata una nuova versione di LibreFolio.
