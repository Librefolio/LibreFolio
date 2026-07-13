# 🌐 Esposizione Sicura

Esporre in modo sicuro servizi self-hosted su internet è una delle sfide più comuni. Questa guida spiega come rendere LibreFolio (o qualsiasi altro servizio nella tua rete locale) accessibile sfruttando [Tailscale](https://tailscale.com/), una soluzione mesh VPN sicura, ad alte prestazioni e gratuita per l'uso domestico.

!!! tip "La nostra raccomandazione di configurazione"

    Tra i diversi approcci presentati, crediamo che il **Livello 4 (Multi-Funnel via Docker)** sia la soluzione assolutamente migliore: richiede pochissima configurazione aggiuntiva rispetto agli altri metodi, offre i massimi vantaggi in termini di isolamento e modularità, e risolve le limitazioni strutturali degli altri metodi. Gli altri livelli sono presentati sia come alternative che per comprendere il percorso tecnico per arrivarci.

---

## 🔒 Sicurezza e rischi del Port Forwarding tradizionale

Il metodo tradizionale per rendere un servizio accessibile dall'esterno prevede l'apertura di porte sul router di casa (port forwarding) associate a un IP pubblico (spesso dinamico) e a un servizio DDNS (come DuckDNS). 

Questo approccio presenta rischi significativi:

1. **Esposizione all'intero web**: chiunque può scansionare il tuo IP pubblico e tentare di attaccare la porta aperta.
2. **Complessità di gestione**: è necessario configurare e rinnovare manualmente i certificati SSL (HTTPS) tramite un reverse proxy (Nginx, Caddy, ecc.).
3. **Rischi del protocollo HTTP**: senza una crittografia HTTPS correttamente configurata, le tue credenziali e i tuoi dati finanziari viaggiano in chiaro sulla rete locale e pubblica, rendendoli intercettabili da attori malintenzionati (packet sniffing).

Il seguente diagramma mostra il problema iniziale dell'esposizione remota:

```mermaid
graph LR
 User["👤 Utente Esterno<br>(Fuori Casa)"] --- Cloud["☁️ Internet / Router (IP Pubblico / DDNS?)"]
 Cloud --- Server["🖥️ Server Locale<br>(Porta 6040)"]
```

---

## 🚀 Cos'è Tailscale?

[Tailscale](https://tailscale.com/) è un servizio mesh VPN a configurazione zero basato sul moderno protocollo di crittografia **WireGuard**. 

* **Piano Gratuito (Personal)**: consente di connettere fino a **100 dispositivi** gratuitamente.
* **Rete Mesh**: tutti i dispositivi configurati si connettono direttamente tra loro in modalità peer-to-peer crittografata, senza che il traffico passi attraverso server intermedi.
* **Compatibilità**: funziona su tutti i principali sistemi operativi (Linux, macOS, Windows, iOS, Android) e può essere installato su un NAS o all'interno di container Docker.

---

## 🏁 Step 0: Installazione di Tailscale sui tuoi dispositivi

Per far funzionare qualsiasi VPN, sono necessari **almeno 2 dispositivi connessi**: il *client* (ad esempio, il tuo smartphone o laptop) e il *server* (il nodo su cui è in esecuzione LibreFolio). Prima di procedere con i livelli, installa ed effettua l'accesso a Tailscale sui tuoi dispositivi:

=== "Linux"

 Esegui il comando di installazione ufficiale sul server:

 ```bash
 curl -fsSL https://tailscale.com/install.sh | sh
 sudo tailscale up
 ```

 Per maggiori dettagli, consulta la [Guida all'installazione generica](https://tailscale.com/docs/install).

=== "macOS"

 Installa l'app ufficiale dal **Mac App Store** o usa Homebrew:

 ```bash
 brew install --cask tailscale
 sudo tailscale up
 ```

 Per maggiori dettagli, consulta la [Guida all'installazione generica](https://tailscale.com/docs/install).

=== "Windows"

 Scarica l'installer ufficiale dal portale Tailscale e segui la procedura guidata di accesso.

 Per i dettagli, consulta la [Guida all'installazione per Windows](https://tailscale.com/docs/install/windows).

=== "Android"

 Installa l'applicazione ufficiale dal [Google Play Store](https://play.google.com/store/apps/details?id=com.tailscale.ipn).

=== "iOS (iPhone/iPad)"

 Installa l'applicazione ufficiale dall' [Apple App Store](https://apps.apple.com/us/app/tailscale/id1470499037).

---

## 🛠️ I 4 livelli di configurazione ed esposizione

---

## 🏃 Livello 1: Connessione VPN privata point-to-point (Inizio)

Questo consiste nel connettere il server e il client alla stessa rete privata Tailscale. Sul server, la porta del servizio viene esposta utilizzando il comando `serve`.

```mermaid
graph LR
 Client["👤 Client (VPN attiva)<br>(100.x.y.z)"] -->|Connessione VPN Diretta| Server["🖥️ Server (VPN attiva)<br>(100.a.b.c:6040)"]
 subgraph LAN ["Rete LAN Locale"]
 Server -->|Accesso locale| LibreFolio["📊 LibreFolio (Locale)"]
 end
 style LibreFolio fill:#d4edda,stroke:#28a745,stroke-width:2px;
```

Sul server, usa il comando per esporre la porta locale di LibreFolio (porta predefinita `6040`):

```bash
tailscale serve tcp:6040 /
```

A questo punto, con la VPN attiva sullo smartphone o sul PC, basta inserire l'IP Tailscale del server (o il suo MagicDNS) seguito dalla porta nel browser per accedere a LibreFolio da remoto.

<table style="width: 100%; border-collapse: collapse; margin-top: 1rem; margin-bottom: 1rem;">
 <thead>
 <tr style="background-color: #f3f4f6;">
 <th style="width: 50%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">🟢 Vantaggi (Pro)</th>
 <th style="width: 50%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">🔴 Svantaggi (Contro)</th>
 </tr>
 </thead>
 <tbody>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(76, 175, 80, 0.08); vertical-align: top;">
 <ul>
 <li>Configurazione istantanea e minima.</li>
 <li>Massima sicurezza: i tuoi dati non passano per internet pubblico, la porta è chiusa all'esterno della VPN.</li>
 </ul>
 </td>
 <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(244, 67, 54, 0.08); vertical-align: top;">
 <ul>
 <li><strong>Richiede che la VPN Tailscale sia attiva e connessa</strong> su ogni client (es. sul telefono) per raggiungere il servizio.</li>
 <li><strong>Espone un singolo servizio</strong> per host.</li>
 </ul>
 </td>
 </tr>
 </tbody>
</table>

---

## 🥉 Livello 2: Configurazione Subnet Router (LAN Tunneling)

Questo livello trasforma il tuo server in un "sub-router". Quando sei fuori casa con la VPN attiva sul client, puoi raggiungere non solo il server ma **qualsiasi dispositivo o servizio sulla tua LAN domestica** inserendo semplicemente il suo IP locale.

```mermaid
graph LR
 Client["👤 Client (VPN attiva)<br>(100.x.y.z)"] -->|WireGuard Tunneling| Server["🖥️ Server (Subnet Router)<br>(100.a.b.c)"]
 subgraph LAN ["Rete LAN Locale (192.168.1.0/24)"]
 Server -->|Inoltro locale| LibreFolio["📊 LibreFolio<br>(es. 192.168.1.2:6040)"]
 Server -->|Inoltro locale| OtherDevice["🖨️ Altri Dispositivi/Servizi<br>(es. 192.168.1.100)"]
 end
 style LibreFolio fill:#d4edda,stroke:#28a745,stroke-width:2px;
```

### 1. Abilitare il Subnet Routing sul SO del Server

=== "Linux"

 Abilita l'IP forwarding a livello di kernel:

 ```bash
 echo 'net.ipv4.ip_forward = 1' | sudo tee -a /etc/sysctl.d/99-tailscale.conf
 echo 'net.ipv6.conf.all.forwarding = 1' | sudo tee -a /etc/sysctl.d/99-tailscale.conf
 sudo sysctl -p /etc/sysctl.d/99-tailscale.conf
 ```

 Inizia ad annunciare la subnet (sostituisci l'intervallo IP con la tua rete locale, es. `192.168.1.0/24`):

 ```bash
 sudo tailscale up --advertise-routes=192.168.1.0/24
 ```

=== "macOS"

 Usa il percorso dell'eseguibile Tailscale per annunciare la subnet locale:

 ```bash
 /Applications/Tailscale.app/Contents/MacOS/Tailscale up --advertise-routes=192.168.1.0/24
 ```

=== "Windows"

 Esegui il Prompt dei Comandi (`cmd.exe`) o PowerShell come **Amministratore** e annuncia la subnet locale:

 ```cmd
 tailscale up --advertise-routes=192.168.1.0/24
 ```

### 2. Approvare la Rotta nella Console di Amministrazione

1. Vai alla [Tailscale Admin Console](https://login.tailscale.com/admin/machines).
2. Clicca sui tre puntini accanto al tuo server -> **Edit route settings**.
3. Abilita la subnet annunciata.

!!! tip "Disabilita la scadenza della chiave per il Server"

    Poiché il server funge da infrastruttura di rete (subnet router), si raccomanda di disabilitare la scadenza automatica della chiave per questo nodo per evitare che si disconnetta e richieda una riautenticazione interattiva periodica (ogni 180 giorni per impostazione predefinita):
    1. Nella pagina **Machines** della console di amministrazione, individua il tuo server.
    2. Clicca sull'**icona dei tre puntini (...)** a destra della riga del dispositivo.
    3. Seleziona l'opzione **Disable Key Expiry**.

<table style="width: 100%; border-collapse: collapse; margin-top: 1rem; margin-bottom: 1rem;">
 <thead>
 <tr style="background-color: #f3f4f6;">
 <th style="width: 50%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">🟢 Vantaggi (Pro)</th>
 <th style="width: 50%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">🔴 Svantaggi (Contro)</th>
 </tr>
 </thead>
 <tbody>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(76, 175, 80, 0.08); vertical-align: top;">
 <ul>
 <li>Accesso a tutti i dispositivi in casa (stampanti, telecamere, LibreFolio, domotica) con un solo nodo attivo.</li>
 <li>Nessuna necessità di configurare porte o reverse proxy per ogni servizio.</li>
 </ul>
 </td>
 <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(244, 67, 54, 0.08); vertical-align: top;">
 <ul>
 <li><strong>La VPN sul client deve essere attiva</strong> per consentire la comunicazione.</li>
 <li><strong>Devi conoscere gli IP locali</strong> dei dispositivi per raggiungerli.</li>
 <li>Una volta all'interno della casa, i <strong>pacchetti viaggiano in chiaro (HTTP)</strong> sulla LAN privata.</li>
 </ul>
 </td>
 </tr>
 </tbody>
</table>

---

## 🔑 Abilitazione di Funnel e ACL nella Console

*Configurazione una tantum richiesta per il Livello 3 e il Livello 4*

Prima di poter utilizzare Tailscale Funnel (sia sul server locale nel Livello 3 che all'interno dei container Docker nel Livello 4), devi abilitare Funnel e definire le regole globali di controllo dell'accesso (ACL) per l'intera tua Tailnet. Questa è una configurazione da eseguire una sola volta direttamente nella console di amministrazione di Tailscale.

### 1. Abilitare HTTPS e Funnel nel Pannello di Controllo

1. Visita la pagina [Access Controls](https://login.tailscale.com/admin/acls) nella console di amministrazione di Tailscale.
2. Clicca sul pulsante **Add node attribute** per creare l'autorizzazione richiesta.

![Add Node Attribute](../static/tailscale-guide/TailscaleNodeAttribute.png)

3. Configura le seguenti opzioni nel modulo:
 * **Targets**: Inserisci il tag o il gruppo che desideri autorizzare per l'attivazione di Funnel. Un *Target* definisce a quali nodi si applica la regola. **Suggeriamo di usare `tag:external_access`** (per associarlo selettivamente ai container Docker) o `autogroup:member` (se desideri consentire l'esposizione per tutti i dispositivi registrati sotto il tuo account personale).
 * **Attributes**: Inserisci `funnel`.
 * **Note**: Inserisci del testo per registrare il motivo di questa regola.
 * **IP Pools, App, Capability, ecc.**: questi campi extra non sono necessari per questa configurazione di esposizione, quindi lasciali vuoti o ai loro valori predefiniti.

*Importante: la configurazione delle ACL definisce le policy di sicurezza globali necessarie per abilitare Funnel. È indipendente dalle chiavi di autenticazione (Auth Keys), che vengono utilizzate solo per registrare un nuovo dispositivo o container nella rete per la prima volta.*

In alternativa, se preferisci modificare direttamente la configurazione JSON delle ACL, puoi utilizzare il seguente esempio funzionante (aggiornato per supportare sia i tuoi dispositivi che i container contrassegnati con `tag:external_access`):

??? example "Visualizza la configurazione JSON completa delle ACL per abilitare Funnel"

 ```json
 {
 // Declaration of authorized tags
 "tagOwners": {
 "tag:external_access": ["autogroup:admin"]
 },

 // Standard access rules
 "acls": [
 // Allows all nodes in your private network to communicate
 {"action": "accept", "src": ["*"], "dst": ["*:*"]}
 ],

 "ssh": [
 {
 "action": "check",
 "src": ["autogroup:member"],
 "dst": ["autogroup:self"],
 "users": ["autogroup:nonroot", "root"]
 }
 ],

 // Enabling Funnel on specific nodes or tags
 "nodeAttrs": [
 {
 "target": ["autogroup:member"],
 "attr": ["funnel"]
 },
 {
 "target": ["tag:external_access"],
 "attr": ["funnel"]
 }
 ]
 }
 ```

---

## 🥈 Livello 3: Esposizione Pubblica tramite Tailscale Funnel (Senza VPN sul Client)

!!! warning "Prerequisito Fondamentale"

    Prima di procedere, assicurati di aver completato la [configurazione una tantum di Funnel e ACL nella console](#abilitazione-di-funnel-e-acl-nella-console).

**Tailscale Funnel** ti consente di esporre un servizio pubblicamente su internet. Chiunque può accedere alla tua istanza di LibreFolio tramite un URL HTTPS sicuro fornito da MagicDNS, **senza dover installare o attivare Tailscale** sul proprio smartphone o PC. Questo è essenziale se desideri installare LibreFolio come PWA sui dispositivi mobili e ricevere l'invito all'installazione automatica (per maggiori dettagli, consulta la guida [📱 Install as App (PWA)](../user/pwa.md)).

```mermaid
graph LR
 User["👤 Utente (Senza VPN)"] -->|Richiesta HTTPS| Funnel["☁️ Tailscale Funnel Ingress<br>(Server Pubblico Tailscale)"]
 Funnel -->|WireGuard Tunneling| Server["🖥️ Server Locale (tailscaled)<br>(100.a.b.c)"]
 subgraph LAN ["Rete LAN Locale"]
 Server -->|Inoltro locale| LibreFolio["📊 LibreFolio (Porta 6040)"]
 Server -.->|"<font color='red'><b>Impossibile esporre</b></font>"| Other["🔌 Altri Servizi Locali (Porte diverse)"]
 end
 style LibreFolio fill:#d4edda,stroke:#28a745,stroke-width:2px;
 style Other fill:#f8d7da,stroke:#dc3545,stroke-width:2px;
 linkStyle 3 stroke:#dc3545,stroke-width:2px;
```

### 1. Avviare il Funnel sul Server

Associa il funnel alla porta locale di LibreFolio:

```bash
tailscale funnel 6040 on
```

*Nota: per questo livello, non è richiesta alcuna chiave di autenticazione (Auth Key) poiché la macchina server è già stata collegata e registrata interattivamente nella tua Tailnet durante lo **Step 0**.*

### 2. Approvare e attendere la propagazione

Una volta lanciato il comando, apparirà un avviso nel terminale indicando che il Funnel è abilitato ma non ancora autorizzato per il tuo nodo, mostrando un link simile al seguente:

```text
Funnel is enabled, but the list of allowed nodes in the tailnet policy file does not include the one you are using.
To give access to this node you can edit the tailnet policy file, or visit:

 https://login.tailscale.com/f/funnel?node=xxxxxx
```

* Visita il link mostrato nel browser, accedi a Tailscale e approva l'attivazione del Funnel per questo nodo.
* Una volta approvato, il terminale visualizzerà l'URL pubblico generato.
* Attendi qualche minuto affinché i record MagicDNS si propaghino globalmente per raggiungere il servizio da qualsiasi rete esterna.

<table style="width: 100%; border-collapse: collapse; margin-top: 1rem; margin-bottom: 1rem;">
 <thead>
 <tr style="background-color: #f3f4f6;">
 <th style="width: 50%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">🟢 Vantaggi (Pro)</th>
 <th style="width: 50%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">🔴 Svantaggi (Contro)</th>
 </tr>
 </thead>
 <tbody>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(76, 175, 80, 0.08); vertical-align: top;">
 <ul>
 <li>Accesso pubblico universale tramite HTTPS gratuito gestito da Tailscale.</li>
 <li>Nessun certificato SSL o reverse proxy da configurare sul server.</li>
 <li>Permette l'installazione nativa di PWA sugli smartphone senza attivare la VPN.</li>
 </ul>
 </td>
 <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(244, 67, 54, 0.08); vertical-align: top;">
 <ul>
 <li><strong>Puoi esporre al massimo 1 singolo servizio</strong> Funnel per macchina host.</li>
 </ul>
 </td>
 </tr>
 </tbody>
</table>

---

## 🥇 Livello 4: Esposizione Multi-Funnel Avanzata via Docker (Sidecars)

!!! warning "Prerequisito Fondamentale"

    Prima di procedere con la configurazione del container, assicurati di aver completato la [configurazione una tantum di Funnel e ACL nella console](#abilitazione-di-funnel-e-acl-nella-console).

Per superare il limite di un solo Funnel per nodo host, possiamo eseguire più nodi Tailscale paralleli all'interno di container Docker. Ogni container si registrerà come un nodo indipendente nella tua Tailnet, ottenendo il proprio URL MagicDNS dedicato.

La nostra soluzione utilizza un piccolo script di avvio personalizzato che installa **socat** nel container e reindirizza il traffico HTTPS in entrata all'IP LAN statico del servizio di destinazione.

??? info "Cos'è socat?"

 **socat** (SOcket CAT) è un'utility a riga di comando estremamente flessibile che stabilisce due flussi di byte bidirezionali e trasferisce i dati tra di essi. Nel nostro caso, lo usiamo come un **mini proxy-forwarder**: ascolta sulla porta locale del container Tailscale e inoltra tutti i pacchetti ricevuti alla porta reale del servizio sul server locale.

Il diagramma di rete illustra lo scenario multi-nodo esposto in parallelo, dove i container Tailscale 1 e 2 girano sul primo host (Server 1) e i container Tailscale 3 e 4 girano sul secondo host (Server 2):

```mermaid
graph LR
 User["👤 Utente Esterno"] -->|HTTPS| Funnel1["☁️ Funnel 1<br>(service2.yourtailnet.ts.net)"]
 User -->|HTTPS| Funnel2["☁️ Funnel 2<br>(service3.yourtailnet.ts.net)"]
 User -->|HTTPS| Funnel3["☁️ Funnel 3<br>(librefolio.yourtailnet.ts.net)"]
 User -->|HTTPS| Funnel4["☁️ Funnel 4<br>(service1.yourtailnet.ts.net)"]
 
 Funnel1 -->|WireGuard| TSC1["🐳 Tailscale Container 1<br>(100.1.1.1)"]
 Funnel2 -->|WireGuard| TSC2["🐳 Tailscale Container 2<br>(100.4.4.4)"]
 Funnel3 -->|WireGuard| TSC3["🐳 Tailscale Container 3<br>(100.3.3.3)"]
 Funnel4 -->|WireGuard| TSC4["🐳 Tailscale Container 4<br>(100.2.2.2)"]
 
 subgraph LAN ["Rete LAN Locale (192.168.1.0/24)"]
 subgraph Host2 ["Server 2 (es. Mini PC - 192.168.1.10)"]
 TSC3 -->|socat: TCP/8080| Service3["🔌 Servizio 3<br>(192.168.1.10:80)"]
 TSC4 -->|socat: TCP/9000| Service4["🔌 Servizio 4<br>(192.168.1.10:80)"]
 end
 subgraph Host1 ["Server 1 (es. NAS - 192.168.1.20)"]
 TSC1 -->|socat: TCP/6040| LibreFolio["📊 LibreFolio<br>(192.168.1.20:6040)"]
 TSC2 -->|socat: TCP/80| Service1["🔌 Servizio 1<br>(192.168.1.20:80)"]
 end
 end
 style LibreFolio fill:#d4edda,stroke:#28a745,stroke-width:2px;
```

!!! note "Nodi e Servizi Multipli"

    Con questa architettura, puoi aggiungere ed esporre tutti i servizi desiderati semplicemente avviando nuovi container Tailscale associati allo script pertinente. L'unico limite è dettato dai termini del tuo piano di abbonamento Tailscale (che copre fino a 100 dispositivi nella versione gratuita).

### 1. Preparazione di Cartella e Script

Crea una cartella sul server (ad esempio, all'interno del percorso dove conservi i tuoi volumi persistenti Docker):

```bash
# Create a folder for the Tailscale nodes and enter it
mkdir -p <path_chosen>/tailscale-nodes
cd <path_chosen>/tailscale-nodes
```

Scarica lo script di avvio personalizzato <a href="https://raw.githubusercontent.com/Librefolio/LibreFolio/main/docs/static/tailscale-guide/custom_startup.sh" target="_blank" rel="noopener noreferrer">custom_startup.sh</a> all'interno di questa cartella:

```bash
# Download the script from the official repository
wget https://raw.githubusercontent.com/Librefolio/LibreFolio/main/docs/static/tailscale-guide/custom_startup.sh
# Make the script executable
chmod +x custom_startup.sh
```

### 2. Configurazione Docker Compose

Suggeriamo di definire e dichiarare il servizio Tailscale **all'interno dello stesso file `docker-compose.yml` del servizio** che desideri esporre (ad esempio, LibreFolio) per mantenerli vicini e logicamente accoppiati. Aggiungi il blocco del servizio come mostrato di seguito:

```yaml
services:
 tailscale-librefolio:
 image: tailscale/tailscale:latest
 container_name: tailscale-librefolio
 hostname: tailscale-librefolio
 restart: unless-stopped
 privileged: false
 network_mode: bridge
 cap_add:
 - NET_ADMIN
 - NET_RAW
 devices:
 - /dev/net/tun:/dev/net/tun
 command:
 - /custom_startup.sh
 environment:
 - HOST_IP=192.168.1.10 # Local IP of the service to expose (e.g. Server 1)
 - HOST_PORT=6040 # Real port of the service to expose
 - TAILSCALE_FUNNEL_PORT=6040 # Internal Funnel port
 - TS_HOSTNAME=librefolio # Custom public hostname (e.g. librefolio)
 - TS_AUTHKEY=tskey-auth-... # Authentication key generated by Tailscale
 - TS_ACCEPT_DNS=true
 - TS_STATE_DIR=/var/lib/tailscale
 - TS_USERSPACE=false
 volumes:
 - <path_chosen>/tailscale-nodes/tailscale-librefolio/state:/var/lib/tailscale
 - <path_chosen>/tailscale-nodes/custom_startup.sh:/custom_startup.sh
 - /etc/localtime:/etc/localtime:ro
 - /etc/timezone:/etc/timezone:ro
```

#### Descrizione dei Parametri di Configurazione

<table style="width: 100%; border-collapse: collapse; margin-top: 1rem; margin-bottom: 1rem;">
 <thead>
 <tr style="background-color: #f3f4f6;">
 <th style="width: 35%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold; white-space: nowrap;">Parametro</th>
 <th style="width: 65%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">Descrizione</th>
 </tr>
 </thead>
 <tbody>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; font-family: monospace; white-space: nowrap;">&lt;path_chosen&gt;</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">Il percorso assoluto (full-path) sul server locale dove vengono salvati lo script e i dati di stato (es. <code>/home/user/docker</code>).</td>
 </tr>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; font-family: monospace; white-space: nowrap;">HOST_IP</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">L'IP LAN statico della macchina che ospita il servizio.</td>
 </tr>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; font-family: monospace; white-space: nowrap;">HOST_PORT</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">La porta reale sul server LAN a cui connettersi (es. <code>6040</code> per LibreFolio).</td>
 </tr>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; font-family: monospace; white-space: nowrap;">TAILSCALE_FUNNEL_PORT</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">La porta su cui il container Tailscale ascolterà e attiverà il Funnel. In linea di principio, l'approccio migliore è impostare questo parametro sullo stesso valore della porta del servizio interno (<code>HOST_PORT</code>) per coerenza; è lasciato come parametro separato per supportare potenziali casi speciali futuri.</td>
 </tr>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; font-family: monospace; white-space: nowrap;">TS_HOSTNAME</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">L'hostname personalizzato per il nodo. L'indirizzo pubblico generato sarà <code>https://TS_HOSTNAME.your-tailnet.ts.net</code>.</td>
 </tr>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; font-family: monospace; white-space: nowrap;">TS_AUTHKEY</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">
 La chiave di autenticazione (Auth Key) generata da Tailscale. Per ottenerla:<br>
 1. Vai a <a href="https://login.tailscale.com/admin/settings/keys" target="_blank" rel="noopener noreferrer">Tailscale Admin Settings Keys</a>.<br>
 2. Sotto la sezione <strong>Auth keys</strong> (<em>non</em> sotto la sezione API access tokens), clicca sul pulsante <strong>Generate auth key...</strong>.<br>
 3. Devi <strong>abilitare l'interruttore Tags</strong> per selezionare il tag desiderato (es. <code>tag:external_access</code>). Nella descrizione della chiave, inserisci una nota descrittiva per renderla facilmente riconoscibile (es. <code>docker-librefolio-funnel</code>).<br>
 4. Clicca su <strong>Generate</strong> e copia la chiave generata (es. <code>tskey-auth-...</code>).<br>
 <br>
 <em>Nota: una volta che il container è partito correttamente, la chiave usa-e-getta viene consumata e scompare automaticamente dalla lista "Keys" nella console di amministrazione, mentre il nuovo dispositivo registrato apparirà in "Machines".</em>
 </td>
 </tr>
 </tbody>
</table>

??? example "Visualizza il file Docker Compose di produzione completo (LibreFolio + Tailscale)"

 Di seguito è riportato un esempio reale e completo di un file `docker-compose.yml` di produzione che esegue l'immagine di produzione ufficiale di LibreFolio insieme al sidecar Tailscale per l'esposizione automatica:

 ```yaml
 # =============================================================================
 # LibreFolio — Production Docker Compose
 # =============================================================================
 # Optimized for end-users running the official pre-built image from GHCR.
 # =============================================================================

 services:
 librefolio:
 image: ghcr.io/librefolio/librefolio:nightly
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

 tailscale-librefolio:
 image: tailscale/tailscale:latest
 container_name: tailscale-librefolio
 hostname: tailscale-librefolio
 restart: unless-stopped
 privileged: false
 network_mode: bridge
 cap_add:
 - NET_ADMIN
 - NET_RAW
 devices:
 - /dev/net/tun:/dev/net/tun
 command:
 - /custom_startup.sh
 environment:
 - HOST_IP=192.168.1.10 # Local IP of the service to expose (e.g. Server 1)
 - HOST_PORT=6040 # Real port of the service to expose
 - TAILSCALE_FUNNEL_PORT=6040 # Internal Funnel port
 - TS_HOSTNAME=librefolio # Custom public hostname (e.g. librefolio)
 - TS_AUTHKEY=tskey-auth-... # Replace with your generated key
 - TS_ACCEPT_DNS=true
 - TS_STATE_DIR=/var/lib/tailscale
 - TS_USERSPACE=false
 volumes:
 - /DATA/AppData/tailscale-nodes/tailscale-librefolio/state:/var/lib/tailscale
 - /DATA/AppData/tailscale-nodes/custom_startup.sh:/custom_startup.sh
 - /etc/localtime:/etc/localtime:ro
 - /etc/timezone:/etc/timezone:ro
 ```

### 3. Avvio e Approvazione

Avvia i container tramite compose del tuo servizio (incluso il sidecar Tailscale):

```bash
docker compose up -d
```

Visualizza i log del container Tailscale per estrarre il link di approvazione del Funnel (richiesto al primo avvio):

```bash
docker logs -f tailscale-librefolio
```

Nei log del container apparirà una riga di avviso con il link di autorizzazione specifico per il tuo nodo:

```text
Funnel is enabled, but the list of allowed nodes in the tailnet policy file does not include the one you are using.
To give access to this node you can edit the tailnet policy file, or visit:

 https://login.tailscale.com/f/funnel?node=nsKGo6k9ZF11CNTRL
```

* Apri il link mostrato nel browser, accedi a Tailscale e approva l'attivazione del Funnel.
* Immediatamente dopo l'approvazione, vedrai la conferma dell'esposizione riuscita nei log del container con l'URL pubblico e il proxy locale:

```text
Available on the internet:

https://librefolio.yourtailnet.ts.net/
|-- proxy http://127.0.0.1:6040

Press Ctrl+C to exit.
```

* **Nota**: a questo punto il servizio è online, ma devi attendere qualche minuto affinché la propagazione del record MagicDNS sia completata globalmente.

!!! tip "Disabilita la scadenza della chiave per il Container"

    Per evitare che il container sidecar scada e si disconnetta dalla tua Tailnet dopo il periodo predefinito (180 giorni):
    1. Vai alla pagina **Machines** della Tailscale Admin Console.
    2. Trova il nodo del container (es. `librefolio` o `tailscale-librefolio`) nell'elenco.
    3. Clicca sull'**icona dei tre puntini (...)** a destra della riga del dispositivo.
    4. Seleziona l'opzione **Disable Key Expiry**.

<table style="width: 100%; border-collapse: collapse; margin-top: 1rem; margin-bottom: 1rem;">
 <thead>
 <tr style="background-color: #f3f4f6;">
 <th style="width: 50%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">🟢 Vantaggi (Pro)</th>
 <th style="width: 50%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">🔴 Svantaggi (Contro)</th>
 </tr>
 </thead>
 <tbody>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(76, 175, 80, 0.08); vertical-align: top;">
 <ul>
 <li>Possibilità di creare <strong>infiniti Funnel pubblici indipendenti</strong> su una singola macchina fisica.</li>
 <li>URL separati e dedicati per ogni servizio domestico.</li>
 <li>I pacchetti della rete locale viaggiano in modo sicuro e diretto tra il container e il servizio di destinazione.</li>
 </ul>
 </td>
 <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(244, 67, 54, 0.08); vertical-align: top;">
 <ul>
 <li><strong>Richiede l'uso del terminale</strong> e la configurazione manuale dei file Docker Compose.</li>
 </ul>
 </td>
 </tr>
 </tbody>
</table>

---

## 🔮 MagicDNS e Domini Personalizzati

### Cos'è MagicDNS?

**MagicDNS** assegna automaticamente un nome di dominio DNS locale e pubblico a ciascuno dei tuoi dispositivi registrati nella Tailnet. Invece di dover ricordare indirizzi IP come `100.110.222.112`, puoi digitare `http://tuo-server` nel browser. 
I domini pubblici assegnati da MagicDNS terminano con il suffisso `*.ts.net` (per esempio, `https://librefolio.your-tailnet.ts.net`).

### Come usare un dominio personalizzato con Tailscale

Se possiedi un tuo dominio personale (es. `miodominio.it`) e desideri usarlo per raggiungere i tuoi nodi Tailscale privati invece di usare l'URL standard `*.ts.net`, puoi procedere con due tecniche principali:

#### Metodo 1: DNS Pubblico mappato sull'IP Tailscale (Raccomandato per Rete Privata)

Questa è la soluzione più semplice per accedere ai tuoi dispositivi privatamente utilizzando il tuo dominio.

1. Accedi alla console del tuo registrar di domini (es. Cloudflare, GoDaddy, Namecheap).
2. Crea un record DNS di tipo **A** (o **AAAA** per IPv6) per il sottodominio scelto (es. `librefolio.miodominio.it`).
3. Punta il record direttamente all'**IP privato Tailscale** del tuo server (es. `100.77.72.90`).
4. **Come funziona**: poiché gli indirizzi IP nella rete `100.64.0.0/10` non sono routabili pubblicamente a livello globale, il dominio risolverà e funzionerà **solo** quando sei connesso alla tua VPN Tailscale, garantendo che nessun utente esterno possa accedere o scansionare il servizio. Per i dettagli, consulta la [Documentazione ufficiale sulle impostazioni DNS](https://tailscale.com/kb/1054/dns#public-dns).

#### Metodo 2: Split DNS (Con Server DNS Interno)

Se desideri gestire dinamicamente i record interni e non pubblicarli su internet:

1. Configura un server DNS privato nella tua LAN (come Pi-hole, AdGuard Home o CoreDNS).
2. Aggiungi record locali del tuo dominio puntandoli ai tuoi IP Tailscale.
3. Nella console di amministrazione di Tailscale, vai su *DNS -> Nameservers -> Add Nameserver* e aggiungi l'IP Tailscale del tuo DNS privato come nameserver globale o limitato al tuo dominio. Per i dettagli, consulta la [Documentazione ufficiale sullo Split DNS](https://tailscale.com/kb/1054/dns#split-dns).

!!! warning "Attenzione sull'esposizione via Funnel Pubblico"

    Poiché i Funnel pubblici di Tailscale sono esposti su internet solo tramite il dominio sicuro `*.ts.net` (grazie ai certificati SSL firmati da Tailscale), una mappatura CNAME diretta dal tuo dominio personalizzato a un indirizzo Funnel causerà errori di sicurezza SSL/TLS nei browser, a meno che non venga utilizzato un reverse proxy separato (come Caddy o Nginx) per gestire i certificati della tua zona. L'indirizzo pubblico della tua istanza sarà `librefolio.your-tailnet.ts.net`, dove la parte iniziale `librefolio` è definita automaticamente dal valore assegnato alla variabile `TS_HOSTNAME`.

---

## 🔗 Link Utili e Risorse

* 🖥️ [Tailscale Administration Console (Machines)](https://login.tailscale.com/admin/machines)
* 🔐 [Access Controls Management (ACLs)](https://login.tailscale.com/admin/acls)
* 📖 [Official Guide to Tailscale Funnel (English Documentation)](https://tailscale.com/kb/1223/tailscale-funnel)
* 🐳 [Running Tailscale in Docker](https://tailscale.com/kb/1282/docker)
