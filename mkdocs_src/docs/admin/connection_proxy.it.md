# 🧰 Verifica della sicurezza della connessione: dietro un proxy inverso

Questa pagina riguarda l'esecuzione di LibreFolio **dietro un proxy inverso** come Nginx, Caddy, Traefik o
Tailscale Serve: gli header che il proxy deve inviare perché la connessione sia considerata sicura, di quale proxy
LibreFolio si fida e come apprende l'indirizzo di ogni visitatore.

Per vedere ciò che ottengono i tuoi utenti, con l'indicatore, la vista del server e il cookie di sessione, parti da
[Verifica della sicurezza della connessione](connection_checks.md).

---

## 🧰 Dietro un proxy inverso {: #reverse-proxy }

Un proxy inverso riceve la connessione HTTPS e la passa a LibreFolio su HTTP in chiaro, quindi
LibreFolio viene a sapere dell'HTTPS, e del visitatore, solo dagli header del proxy:

- `X-Forwarded-Proto: https` indica che il browser usa HTTPS: con `SESSION_COOKIE_SECURE=auto`,
  l'impostazione predefinita, LibreFolio contrassegna quindi il cookie di sessione come `Secure`;
- `X-Forwarded-For` trasporta l'indirizzo del visitatore, il che consente all'indicatore di vedere da dove si connettono
  gli utenti.

Tailscale Serve e Funnel, Caddy e Traefik li inviano entrambi automaticamente. Nginx ha bisogno di entrambe le righe nel
blocco `location` che passa le richieste a LibreFolio:

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

Se il browser usa HTTPS ma il cookie di sessione non è contrassegnato come `Secure`, perché il proxy non
invia `X-Forwarded-Proto` o perché `SESSION_COOKIE_SECURE` è `never`, gli amministratori vedono una riga in più
nei dettagli dell'indicatore. Il livello resta **Connessione: sicura**, perché la connessione è
cifrata; solo il cookie è privo di `Secure`:

> Il tuo browser usa HTTPS, ma il cookie di sessione non è contrassegnato come Secure. Fai in modo che il proxy inverso invii
> X-Forwarded-Proto (Nginx: `proxy_set_header X-Forwarded-Proto $scheme;`), oppure riporta
> SESSION_COOKIE_SECURE su auto se è impostato su never.

Una volta corretto il proxy, ricarica LibreFolio: la riga scompare. Poi esci e accedi di nuovo,
così che il browser riceva un cookie `Secure`.

??? tip "⚙️ Imposta invece `SESSION_COOKIE_SECURE`"

    Inviare l'header è la soluzione migliore. Se raggiungi LibreFolio sempre e solo tramite HTTPS, puoi
    invece aggiungere questa riga a `.env`:

    ```bash
    SESSION_COOKIE_SECURE=always
    ```

    Poi riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`; su un'installazione sull'host, riavvia
    `./dev.py server`, che legge anch'esso `.env`. Poi esci e accedi di nuovo.

    Usa `never` solo per il raro proxy che dichiara HTTPS mentre il browser è su HTTP in chiaro. Vedi
    [Configurazione](configuration.md#session-cookie-secure) per tutte le opzioni.

### 🧭 L'indirizzo del visitatore {: #client-address }

LibreFolio limita alcune richieste per indirizzo del visitatore: gli accessi falliti
([Accessi falliti](configuration_accounts.md#login-limit)), le email di registrazione, **Invia di nuovo il link**
e le password dimenticate ([Email](email.md)). Dietro un proxy inverso, le connessioni provengono dal
proxy: a meno che LibreFolio non apprenda l'indirizzo di ogni visitatore, tutte condividono quello del proxy e
un unico conteggio. Per gli accessi è particolarmente importante: 50 accessi falliti attraverso il proxy, da chiunque,
rifiuterebbero ogni tentativo di accesso attraverso di esso, anche quelli con le password corrette, fino a 15 minuti. Questo
resta vero dietro un proxy su un indirizzo pubblico. Dietro uno su un indirizzo locale, come un container proxy
davanti all'immagine Docker, LibreFolio esclude invece gli accessi attraverso di esso dal conteggio
per indirizzo, e solo il limite per nome utente o indirizzo email li conta: vedi
[Quando LibreFolio non si fida del tuo proxy](#untrusted-proxy), sotto. In ogni caso, la soluzione è
far sì che LibreFolio apprenda l'indirizzo di ogni visitatore, in uno dei due modi che seguono.

Di default, l'indirizzo che conta è quello della connessione, così come lo fornisce uvicorn, il server web di
LibreFolio. uvicorn prende l'indirizzo del visitatore da `X-Forwarded-For` solo quando la connessione proviene
da un indirizzo elencato in `FORWARDED_ALLOW_IPS`, `127.0.0.1` quando quella variabile non è impostata:
[Password dimenticate](email_flows.md#forgot-password), nella guida email, spiega come elencare lì il tuo proxy.

Se invece il tuo proxy scrive l'indirizzo del visitatore in un header tutto suo, indica quel header in
`LIBREFOLIO_CLIENT_IP_HEADER`, in `.env` o nell'ambiente del container:

```bash
LIBREFOLIO_CLIENT_IP_HEADER=Fly-Client-IP
```

| Il tuo proxy | L'header | Cosa configurare |
| --- | --- | --- |
| Fly.io | `Fly-Client-IP` | Niente: lo imposta il proxy di Fly. |
| Nginx | `X-Real-IP` | Aggiungi `proxy_set_header X-Real-IP $remote_addr;` al blocco `location` che passa le richieste a LibreFolio. |

!!! warning "🚧 Solo quando ogni richiesta passa attraverso il proxy"

    LibreFolio crede all'header, chiunque lo invii. Imposta la variabile solo se i tuoi visitatori possono
    raggiungere LibreFolio esclusivamente attraverso quel proxy: un visitatore che lo raggiunge direttamente, sulla sua
    porta (`PORT`, 6040 per impostazione predefinita) o per qualsiasi altro percorso, può inviare l'header e scegliere qualsiasi indirizzo, per
    aggirare i limiti o per esaurire quelli di qualcun altro.

- **Riavvia dopo una modifica**: LibreFolio legge la variabile una volta per processo del server. Con Docker,
  esegui `docker compose up -d`; su un'installazione
  sull'host, riavvia `./dev.py server`.
- **L'header deve contenere un solo indirizzo, scritto dal proxy stesso**: mai un valore che il proxy
  inoltra dal visitatore. `X-Forwarded-For` e `Forwarded` sono rifiutati: contengono un elenco il cui primo
  indirizzo è scelto dal visitatore. Per `X-Forwarded-For`, elenca invece il tuo proxy in `FORWARDED_ALLOW_IPS`.
- **Un valore errato impedisce l'avvio del server**, con un errore che nomina la variabile: uno di
  quei due header, oppure un valore che non è il nome di un header, come un nome con uno spazio o
  con un `:`. Maiuscole/minuscole e spazi attorno al nome non hanno importanza; un valore vuoto equivale a non
  impostarla.
- **Una richiesta senza l'header** viene conteggiata con l'indirizzo della connessione.
- **Un header che LibreFolio non può usare**, perché la richiesta lo trasporta due volte oppure perché l'header contiene un elenco, un
  indirizzo con una porta o qualsiasi cosa diversa da un singolo indirizzo IP, viene anch'esso conteggiato con l'indirizzo della connessione.
  Il log presenta quindi un avviso per ogni processo del server,
  `Client address header unusable: using the connection's address`, con il nome dell'header in
  `header`, quante volte la richiesta lo trasportava in `lines` e la lunghezza totale di tali righe in `length`,
  mai il valore stesso: controlla come il tuo proxy imposta l'header.
- **Un altro proxy davanti a Fly.io**, come Cloudflare: `Fly-Client-IP` contiene allora l'indirizzo di quel proxy,
  non quello del visitatore.
- **Nessun profilo lo imposta**: l'header dipende dal proxy davanti a ciascuna istanza.
- **L'indicatore non lo usa**: continua a leggere `X-Forwarded-For`, come
  spiega [La vista del server](connection_checks.md#server-view).

#### 🕵️ Quando LibreFolio non si fida del tuo proxy {: #untrusted-proxy }

LibreFolio non si fida del tuo proxy quando non apprende l'indirizzo del visitatore né tramite
`FORWARDED_ALLOW_IPS` né tramite `LIBREFOLIO_CLIENT_IP_HEADER`: non riesce a distinguere i visitatori
dietro il proxy, e nemmeno i suoi limiti per indirizzo del visitatore possono farlo. Riconosce un tale
proxy dalle sue richieste: provengono da un indirizzo locale (`loopback`, `lan` o `vpn` in
[La vista del server](connection_checks.md#server-view), come `172.18.0.2` su una rete Docker) e trasportano un header
di inoltro (`X-Forwarded-For`, `Forwarded` o `X-Real-IP`) che non ha fornito a LibreFolio alcun indirizzo del visitatore.
Allora:

- **I limiti per indirizzo del visitatore escludono quelle richieste**, così che un solo visitatore non possa
  bloccare tutti. I limiti per account o per indirizzo email continuano a conteggiarle.
- **Il log presenta un avviso per ogni processo del server**, la prima volta che una richiesta del genere incontra un limite per
  indirizzo del visitatore:
  `Requests come through a reverse proxy that LibreFolio does not trust: the limits per client address skip them. List the proxy in FORWARDED_ALLOW_IPS, or name the header it sets in LIBREFOLIO_CLIENT_IP_HEADER`,
  con i nomi degli header in `headers`, come `X-Forwarded-For, X-Real-IP`, mai un
  indirizzo.
- **I controlli di sicurezza** lo segnalano anch'essi, come avviso di `platform.client_address`. Questo controllo
  indica ciò che il server ha incontrato dal suo ultimo avvio: dopo un riavvio legge `ok` finché non si presenta di nuovo una
  richiesta del genere, quindi non compare mai tra i [controlli all'avvio](configuration_security.md#startup-checks).
- **Per risolvere**, elenca il tuo proxy in `FORWARDED_ALLOW_IPS`, come spiega [Password dimenticate](email_flows.md#forgot-password)
  nella guida email, oppure indica in `LIBREFOLIO_CLIENT_IP_HEADER` l'header che il proxy stesso imposta, come sopra, se ogni
  richiesta lo attraversa. Dietro Tailscale Serve o Funnel con l'immagine Docker, segui [Tailscale Serve e Funnel con Docker](#tailscale).
  In `FORWARDED_ALLOW_IPS`, indica l'indirizzo del proxy così come lo vede LibreFolio: con Docker, l'indirizzo del container
  del proxy, o la sua rete Docker, come `FORWARDED_ALLOW_IPS=172.18.0.0/16` (`docker network inspect`, con il nome della
  rete, mostra entrambi), anche se un'intera rete include il suo gateway, che è anche l'indirizzo delle connessioni effettuate
  sul server stesso ([vedi sotto](#tailscale)). Fidati solo di indirizzi usati esclusivamente dal tuo proxy. Imposta l'una o
  l'altra variabile in `.env` o nell'ambiente del container, poi riavvia, come sopra: con Docker,
  `docker compose up -d`. Nessun tuo proxy davanti a LibreFolio? Allora l'header è stato inviato da un visitatore sulla tua
  rete o VPN, oppure, con Docker Desktop esposto direttamente, da qualsiasi visitatore, o da qualsiasi
  visitatore IPv6 che il proxy di Docker trasmette ([Limiti](connection_checks.md#limits)): non elencare nulla.

**Gli header di inoltro da un indirizzo pubblico** ottengono solo un `info`, nel log una volta per processo del server,
`Forwarding headers from a public address were ignored: if a proxy on a public address forwards the requests, list it in FORWARDED_ALLOW_IPS`,
anche con `headers`, e nei controlli di sicurezza, dove `platform.client_address` resta un avviso se
è stato incontrato anche un proxy come sopra. Quelle richieste continuano a essere conteggiate con l'indirizzo della connessione. Sono
innocue quando nessun tuo proxy ha un indirizzo pubblico: un visitatore, o un proxy proprio, può aggiungere
tali header.

#### 🐳 Tailscale Serve e Funnel con Docker {: #tailscale }

Tailscale Serve e Funnel passano l'indirizzo del visitatore in `X-Forwarded-For`: l'indirizzo Tailscale
del dispositivo, `100.x.y.z`, oppure, tramite Funnel, l'indirizzo del visitatore su Internet. Scrivono
l'header da soli, al posto di qualsiasi header inviato dal visitatore. Su HTTPS, l'impostazione predefinita di Serve e
l'unica modalità di Funnel, inviano anche `X-Forwarded-Proto: https`; con `tailscale serve --http=…`
non ne inviano nessuno, giustamente, dato che anche il browser usa HTTP in chiaro.

Con l'immagine Docker, LibreFolio non può usare quell'indirizzo senza configurazione. Entrambe le configurazioni Tailscale di
[Esporre in modo sicuro](service_exposure.md), sul server e nei
[container sidecar](service_exposure_funnel.md#level-4-multi-funnel-with-docker-sidecars), raggiungono il suo container attraverso Docker, quindi le loro richieste provengono
dal gateway della rete Docker del container, come `172.28.0.1`, di cui uvicorn non si fida:

- **Sul server**, `tailscale serve --bg 6040` (l'indirizzo HTTPS del Livello 1) o
  `tailscale funnel --bg 6040` (Livello 3) passa le richieste a `http://127.0.0.1:6040`, e
  il proxy di Docker le consegna al container;
- **Nei container sidecar** (Livello 4), socat le passa all'indirizzo LAN del server e
  alla porta pubblicata di LibreFolio.

Quindi LibreFolio avvisa di un proxy di cui non si fida, [come sopra](#untrusted-proxy), e i suoi limiti
per indirizzo del visitatore escludono tutte quelle richieste. Installato invece sull'host, senza Docker,
LibreFolio non ha bisogno di nulla per `tailscale serve` o `tailscale funnel` sullo stesso server: vede
le loro richieste provenire da `127.0.0.1`, di cui uvicorn si fida per impostazione predefinita.

Per permettere a LibreFolio di vedere ogni visitatore, lavora sul server, nella cartella che contiene
`docker-compose.yml` e `.env`:

1. **Trova il gateway** della rete Docker di LibreFolio:

    ```bash
    docker inspect --format '{{range .NetworkSettings.Networks}}{{.Gateway}}{{end}}' librefolio
    ```

    Stampa un indirizzo come `172.28.0.1`; `librefolio` è il nome che `docker-compose.yml` assegna
    al container (`container_name`). `docker network inspect <network>` mostra lo stesso gateway
    sotto `IPAM` → `Config` → `Gateway`, accanto alla `Subnet` della rete: `docker network ls` elenca
    le reti, e quella propria di un progetto Compose è `<project>_default`.

    Per assicurarti che le richieste di Tailscale provengano da esso, apri LibreFolio al suo indirizzo Tailscale,
    poi leggi le ultime righe del suo log:

    ```bash
    docker compose logs --tail 20 librefolio
    ```

    uvicorn registra ogni richiesta su una riga che riporta l'indirizzo che vede, poi la richiesta. Attraverso
    Tailscale, quell'indirizzo è quello del gateway:

    ```text
    172.28.0.1:<port> - "GET … HTTP/1.1" 200 OK
    ```

    Le righe per `/api/v1/system/health` sono l'health check di Docker, eseguito all'interno del container:
    lasciale da parte.

2. **Elenca il gateway in `FORWARDED_ALLOW_IPS`.** Aggiungi questa riga a `.env`, con il tuo gateway:

    ```bash
    FORWARDED_ALLOW_IPS=172.28.0.1
    ```

    Se `.env` imposta già la variabile, per un altro proxy, aggiungi il gateway alla fine del suo elenco,
    dopo una virgola.

3. **Riavvia LibreFolio**, così che il suo container riceva il nuovo ambiente:

    ```bash
    docker compose up -d
    ```

4. **Controlla.** Apri di nuovo LibreFolio al suo indirizzo Tailscale, poi leggi il log come al punto 1. Le
   righe delle tue richieste ora mostrano l'indirizzo del dispositivo al posto di quello del gateway (tramite
   Funnel, l'indirizzo pubblico del visitatore), seguito dalla porta `0`:

    ```text
    100.x.y.z:0 - "GET … HTTP/1.1" 200 OK
    ```

    L'avviso di `platform.client_address` smette di ripresentarsi. Tuttavia quel controllo indica ciò che il server
    ha incontrato dal suo ultimo avvio, quindi dopo il riavvio legge `ok` in ogni caso: la riga del log
    è la prova reale.

Tre cose da tenere a mente sul fidarsi del gateway:

- **Il gateway esatto è la scelta più restrittiva**, ma Compose può assegnare alla rete un'altra subnet
  quando la ricrea (`docker compose down`, poi `docker compose up -d`): controlla di nuovo il gateway dopo un cambiamento del genere.
- **`FORWARDED_ALLOW_IPS=172.16.0.0/12` sopravvive a questo**, poiché copre ogni rete Docker da
  `172.16` a `172.31`. Ma si fida di ogni rete Docker sul server e non copre le
  reti `192.168.x.x` che Docker assegna una volta esaurite quelle.
- **Il gateway non è solo Tailscale.** È anche l'indirizzo di ogni connessione effettuata sul
  server stesso attraverso la porta pubblicata, e dei visitatori IPv6 che il proxy di Docker trasmette
  ([Limiti](connection_checks.md#limits)): fidarsi di esso consente loro di scegliere l'indirizzo conteggiato ai fini dei limiti.
    - Se raggiungi LibreFolio **solo** tramite `tailscale serve` o `tailscale funnel` sul
      server, pubblica la porta solo sul loopback, così che nulla al di fuori del server possa raggiungerla:
      in `docker-compose.yml`, sotto `ports:`, cambia `"${PORT:-6040}:6040"` in
      `"127.0.0.1:${PORT:-6040}:6040"`, poi esegui `docker compose up -d`.
    - Non con il Livello 4, né con gli indirizzi HTTP in chiaro dei Livelli 1 e 2: raggiungono la porta
      tramite l'indirizzo LAN o Tailscale del server.

---

## 🔗 Correlati

- 📄 **[Verifica della sicurezza della connessione](connection_checks.md)** — Checklist, Cosa mostra l'indicatore, La vista del server, …
