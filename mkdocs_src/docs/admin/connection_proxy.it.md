# 🧰 Verifica della sicurezza della connessione: dietro un proxy inverso

Questa pagina riguarda LibreFolio **dietro un proxy inverso** come Nginx, Caddy, Traefik o Tailscale Serve:

- gli header che il proxy deve inviare perché la connessione sia considerata sicura;
- di quale proxy LibreFolio si fida;
- come apprende l'indirizzo di ogni visitatore.

Per vedere ciò che ottengono i tuoi utenti (indicatore, vista del server, cookie di sessione), parti da
[Verifica della sicurezza della connessione](connection_checks.md).

---

## 🧰 Dietro un proxy inverso {: #reverse-proxy }

Il proxy riceve la connessione HTTPS e la passa a LibreFolio su HTTP in chiaro.
LibreFolio viene a sapere dell'HTTPS, e del visitatore, solo dagli header del proxy:

| Header | Cosa dice a LibreFolio |
| --- | --- |
| `X-Forwarded-Proto: https` | Il browser usa HTTPS. Con `SESSION_COOKIE_SECURE=auto` (predefinito) il cookie di sessione è contrassegnato `Secure`. |
| `X-Forwarded-For` | L'indirizzo del visitatore. L'indicatore vede da dove si connettono gli utenti. |

Tailscale Serve e Funnel, Caddy e Traefik li inviano entrambi automaticamente.
Nginx ha bisogno di entrambe le righe nel blocco `location` che passa le richieste a LibreFolio:

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

**Browser su HTTPS, ma cookie di sessione senza `Secure`?**
Succede se il proxy non invia `X-Forwarded-Proto`, o se `SESSION_COOKIE_SECURE` è `never`.
Gli amministratori vedono una riga in più nei dettagli dell'indicatore.
Il livello resta **Connessione: sicura**: la connessione è cifrata, solo il cookie è privo di `Secure`:

> Il tuo browser usa HTTPS, ma il cookie di sessione non è contrassegnato come Secure. Fai in modo che il proxy inverso invii
> X-Forwarded-Proto (Nginx: `proxy_set_header X-Forwarded-Proto $scheme;`), oppure riporta
> SESSION_COOKIE_SECURE su auto se è impostato su never.

Per risolvere:

1. Correggi il proxy: deve inviare `X-Forwarded-Proto` (Nginx: la prima riga sopra).
2. Ricarica LibreFolio: la riga scompare.
3. Esci e accedi di nuovo: il browser riceve un cookie `Secure`.

??? tip "⚙️ Imposta invece `SESSION_COOKIE_SECURE`"

    Inviare l'header è la soluzione migliore.
    Se raggiungi LibreFolio sempre e solo tramite HTTPS, puoi invece aggiungere questa riga a `.env`:

    ```bash
    SESSION_COOKIE_SECURE=always
    ```

    Riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`.
    Sull'host, riavvia `./dev.py server` (legge anch'esso `.env`).
    Poi esci e accedi di nuovo.

    Usa `never` solo per il raro proxy che dichiara HTTPS mentre il browser è su HTTP in chiaro.
    Tutte le opzioni: [Configurazione](configuration.md#session-cookie-secure).

### 🧭 L'indirizzo del visitatore {: #client-address }

LibreFolio limita alcune richieste per indirizzo del visitatore:

- gli accessi falliti ([Accessi falliti](configuration_accounts.md#login-limit));
- le email di registrazione, **Invia di nuovo il link** e le password dimenticate ([Email](email.md)).

Dietro un proxy inverso, le connessioni provengono dal proxy.
Se LibreFolio non apprende l'indirizzo di ogni visitatore, tutte condividono quello del proxy e un unico conteggio.

- **Per gli accessi è particolarmente importante**: 50 accessi falliti attraverso il proxy, da chiunque, rifiuterebbero
  ogni tentativo di accesso attraverso di esso, anche con la password corretta, fino a 15 minuti.
  Questo resta vero dietro un proxy su un indirizzo pubblico.
- **Dietro un proxy su un indirizzo locale**, come un container proxy davanti all'immagine Docker, LibreFolio esclude
  invece gli accessi attraverso di esso dal conteggio per indirizzo: li conta solo il limite per nome utente o indirizzo
  email. Vedi [Quando LibreFolio non si fida del tuo proxy](#untrusted-proxy), sotto.

In ogni caso, la soluzione è far apprendere a LibreFolio l'indirizzo di ogni visitatore, in uno dei due modi che seguono.

**Modo 1 — `FORWARDED_ALLOW_IPS`.**
Di default, l'indirizzo che conta è quello della connessione, così come lo fornisce uvicorn, il server web di LibreFolio.
uvicorn prende l'indirizzo del visitatore da `X-Forwarded-For` solo quando la connessione proviene da un indirizzo
elencato in `FORWARDED_ALLOW_IPS` (`127.0.0.1` quando la variabile non è impostata).
Come elencarvi il tuo proxy: [Password dimenticate](email_flows.md#forgot-password), nella guida email.

**Modo 2 — `LIBREFOLIO_CLIENT_IP_HEADER`.**
Se il tuo proxy scrive l'indirizzo del visitatore in un header tutto suo, indica quel header in
`LIBREFOLIO_CLIENT_IP_HEADER`, in `.env` o nell'ambiente del container:

```bash
LIBREFOLIO_CLIENT_IP_HEADER=Fly-Client-IP
```

| Il tuo proxy | L'header | Cosa configurare |
| --- | --- | --- |
| Fly.io | `Fly-Client-IP` | Niente: lo imposta il proxy di Fly. |
| Nginx | `X-Real-IP` | Aggiungi `proxy_set_header X-Real-IP $remote_addr;` al blocco `location` che passa le richieste a LibreFolio. |

!!! warning "🚧 Solo quando ogni richiesta passa attraverso il proxy"

    LibreFolio crede all'header, chiunque lo invii.
    Imposta la variabile solo se i tuoi visitatori raggiungono LibreFolio esclusivamente attraverso quel proxy.
    Chi lo raggiunge direttamente, sulla sua porta (`PORT`, 6040 per impostazione predefinita) o per qualsiasi altro
    percorso, può inviare l'header e scegliere qualsiasi indirizzo: per aggirare i limiti o per esaurire quelli di
    qualcun altro.

Riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`. Sull'host, riavvia `./dev.py server`.
LibreFolio legge la variabile una volta per processo del server.

Regole dell'header:

- **Un solo indirizzo, scritto dal proxy stesso.** Mai un valore che il proxy inoltra dal visitatore.
- **`X-Forwarded-For` e `Forwarded` sono rifiutati**: contengono un elenco il cui primo indirizzo è scelto dal visitatore.
  Per `X-Forwarded-For`, elenca invece il tuo proxy in `FORWARDED_ALLOW_IPS`.
- **Un valore errato impedisce l'avvio del server**, con un errore che nomina la variabile.
  Errato: uno di quei due header, oppure un valore che non è il nome di un header (uno spazio, un `:`).
  Maiuscole/minuscole e spazi attorno al nome non hanno importanza. Un valore vuoto equivale a non impostarla.
- **Richiesta senza l'header** → conteggiata con l'indirizzo della connessione.
- **Header che LibreFolio non può usare** → conteggiata con l'indirizzo della connessione.
  Inutilizzabile: la richiesta lo trasporta due volte, oppure contiene un elenco, un indirizzo con una porta o qualsiasi
  cosa diversa da un singolo indirizzo IP.
  Il log presenta un avviso per ogni processo del server:

    ```text
    Client address header unusable: using the connection's address
    ```

    Con il nome dell'header in `header`, quante volte la richiesta lo trasportava in `lines` e la lunghezza totale di
    tali righe in `length`; mai il valore stesso. Controlla come il tuo proxy imposta l'header.

- **Un altro proxy davanti a Fly.io**, come Cloudflare: `Fly-Client-IP` contiene l'indirizzo di quel proxy, non quello
  del visitatore.
- **Nessun profilo lo imposta**: l'header dipende dal proxy davanti a ciascuna istanza.
- **L'indicatore non lo usa**: continua a leggere `X-Forwarded-For`, come spiega
  [La vista del server](connection_checks.md#server-view).

#### 🕵️ Quando LibreFolio non si fida del tuo proxy {: #untrusted-proxy }

LibreFolio non si fida del tuo proxy quando non apprende l'indirizzo del visitatore né tramite `FORWARDED_ALLOW_IPS`
né tramite `LIBREFOLIO_CLIENT_IP_HEADER`.
Non riesce a distinguere i visitatori dietro il proxy; nemmeno i suoi limiti per indirizzo del visitatore possono farlo.

Riconosce un tale proxy dalle sue richieste, quando valgono entrambe le condizioni:

- provengono da un **indirizzo locale**: `loopback`, `lan` o `vpn` in
  [La vista del server](connection_checks.md#server-view), come `172.18.0.2` su una rete Docker;
- trasportano un **header di inoltro** (`X-Forwarded-For`, `Forwarded` o `X-Real-IP`) che non ha fornito a LibreFolio
  alcun indirizzo del visitatore.

**Cosa succede**

- **I limiti per indirizzo del visitatore escludono quelle richieste**: un solo visitatore non può bloccare tutti.
  I limiti per account o per indirizzo email continuano a conteggiarle.
- **Il log presenta un avviso per ogni processo del server**, la prima volta che una richiesta del genere incontra un
  limite per indirizzo del visitatore:

    ```text
    Requests come through a reverse proxy that LibreFolio does not trust: the limits per client address skip them. List the proxy in FORWARDED_ALLOW_IPS, or name the header it sets in LIBREFOLIO_CLIENT_IP_HEADER
    ```

    Con i nomi degli header in `headers`, come `X-Forwarded-For, X-Real-IP`; mai un indirizzo.

- **I controlli di sicurezza lo segnalano**, come avviso di `platform.client_address`.
  Il controllo indica ciò che il server ha incontrato dal suo ultimo avvio: dopo un riavvio legge `ok` finché non si
  ripresenta una richiesta del genere. Perciò non compare mai tra i
  [controlli all'avvio](configuration_security.md#startup-checks).

**Come risolvere**

Scegli il caso tuo:

| Situazione | Cosa fare |
| --- | --- |
| Il proxy inoltra `X-Forwarded-For` | Elenca il proxy in `FORWARDED_ALLOW_IPS`: [Password dimenticate](email_flows.md#forgot-password), nella guida email. |
| Il proxy imposta un header tutto suo e ogni richiesta lo attraversa | Indica quell'header in `LIBREFOLIO_CLIENT_IP_HEADER`, [come sopra](#client-address). |
| Tailscale Serve o Funnel con l'immagine Docker | Segui [Tailscale Serve e Funnel con Docker](#tailscale). |
| Nessun tuo proxy davanti a LibreFolio | Non elencare nulla: vedi sotto. |

In `FORWARDED_ALLOW_IPS`, indica l'indirizzo del proxy **così come lo vede LibreFolio**.
Con Docker: l'indirizzo del container del proxy, oppure la sua rete Docker:

```bash
FORWARDED_ALLOW_IPS=172.18.0.0/16
```

`docker network inspect`, con il nome della rete, mostra entrambi.

!!! warning "⚠️ Fidati solo di indirizzi usati esclusivamente dal tuo proxy"

    Un'intera rete include il suo gateway, che è anche l'indirizzo delle connessioni effettuate sul server stesso
    ([vedi sotto](#tailscale)).

Imposta l'una o l'altra variabile in `.env` o nell'ambiente del container.
Riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`.

**Nessun tuo proxy davanti a LibreFolio?** Allora l'header è stato inviato da:

- un visitatore sulla tua rete o VPN;
- con Docker Desktop esposto direttamente, qualsiasi visitatore;
- qualsiasi visitatore IPv6 che il proxy di Docker trasmette ([Limiti](connection_checks.md#limits)).

Non elencare nulla.

**Header di inoltro da un indirizzo pubblico.** Ottengono solo un `info`:

- nel log, una volta per processo del server, anche con `headers`:

    ```text
    Forwarding headers from a public address were ignored: if a proxy on a public address forwards the requests, list it in FORWARDED_ALLOW_IPS
    ```

- nei controlli di sicurezza, dove `platform.client_address` resta un avviso se è stato incontrato anche un proxy
  come sopra.

Quelle richieste continuano a essere conteggiate con l'indirizzo della connessione.
Sono innocue quando nessun tuo proxy ha un indirizzo pubblico: un visitatore, o un proxy proprio, può aggiungere tali
header.

#### 🐳 Tailscale Serve e Funnel con Docker {: #tailscale }

Tailscale Serve e Funnel passano l'indirizzo del visitatore in `X-Forwarded-For`:

- l'indirizzo Tailscale del dispositivo, `100.x.y.z`;
- tramite Funnel, l'indirizzo del visitatore su Internet.

Scrivono l'header da soli, al posto di qualsiasi header inviato dal visitatore.
Su HTTPS (impostazione predefinita di Serve, unica modalità di Funnel) inviano anche `X-Forwarded-Proto: https`.
Con `tailscale serve --http=…` non ne inviano nessuno, giustamente: anche il browser usa HTTP in chiaro.

**Con l'immagine Docker**, LibreFolio non può usare quell'indirizzo senza configurazione.
Entrambe le configurazioni Tailscale di [Esporre in modo sicuro](service_exposure.md) raggiungono il suo container
attraverso Docker. Le loro richieste provengono quindi dal gateway della rete Docker del container, come `172.28.0.1`,
di cui uvicorn non si fida:

- **Sul server**: `tailscale serve --bg 6040` (l'indirizzo HTTPS del Livello 1) o `tailscale funnel --bg 6040`
  (Livello 3) passa le richieste a `http://127.0.0.1:6040`, e il proxy di Docker le consegna al container.
- **Nei [container sidecar](service_exposure_funnel.md#level-4-multi-funnel-with-docker-sidecars)** (Livello 4): socat
  le passa all'indirizzo LAN del server e alla porta pubblicata di LibreFolio.

Quindi LibreFolio avvisa di un proxy di cui non si fida ([come sopra](#untrusted-proxy)), e i suoi limiti per
indirizzo del visitatore escludono tutte quelle richieste.

**Installato sull'host, senza Docker**: LibreFolio non ha bisogno di nulla per `tailscale serve` o `tailscale funnel`
sullo stesso server. Le loro richieste provengono da `127.0.0.1`, di cui uvicorn si fida per impostazione predefinita.

**Procedura.** Lavora sul server, nella cartella che contiene `docker-compose.yml` e `.env`.

1. **Trova il gateway** della rete Docker di LibreFolio:

    ```bash
    docker inspect --format '{{range .NetworkSettings.Networks}}{{.Gateway}}{{end}}' librefolio
    ```

    Stampa un indirizzo come `172.28.0.1`. `librefolio` è il nome che `docker-compose.yml` assegna al container
    (`container_name`).

    ??? tip "🔎 In alternativa, con `docker network inspect`"

        `docker network ls` elenca le reti; quella propria di un progetto Compose è `<project>_default`.
        `docker network inspect <network>` mostra lo stesso gateway sotto `IPAM` → `Config` → `Gateway`, accanto alla
        `Subnet` della rete.

2. **Verifica che le richieste di Tailscale provengano dal gateway.** Apri LibreFolio al suo indirizzo Tailscale, poi
   leggi le ultime righe del suo log:

    ```bash
    docker compose logs --tail 20 librefolio
    ```

    uvicorn registra ogni richiesta su una riga: l'indirizzo che vede, poi la richiesta. Attraverso Tailscale,
    quell'indirizzo è quello del gateway:

    ```text
    172.28.0.1:<port> - "GET … HTTP/1.1" 200 OK
    ```

    Le righe per `/api/v1/system/health` sono l'health check di Docker, eseguito all'interno del container: lasciale
    da parte.

3. **Elenca il gateway in `FORWARDED_ALLOW_IPS`.** Aggiungi questa riga a `.env`, con il tuo gateway:

    ```bash
    FORWARDED_ALLOW_IPS=172.28.0.1
    ```

    Se `.env` imposta già la variabile, per un altro proxy, aggiungi il gateway alla fine del suo elenco, dopo una
    virgola.

4. **Riavvia LibreFolio**, così che il suo container riceva il nuovo ambiente:

    ```bash
    docker compose up -d
    ```

5. **Controlla.** Apri di nuovo LibreFolio al suo indirizzo Tailscale, poi leggi il log come al passo 2:

    ```bash
    docker compose logs --tail 20 librefolio
    ```

    Le righe delle tue richieste mostrano ora l'indirizzo del dispositivo (tramite Funnel, l'indirizzo pubblico del
    visitatore), seguito dalla porta `0`:

    ```text
    100.x.y.z:0 - "GET … HTTP/1.1" 200 OK
    ```

    L'avviso di `platform.client_address` smette di ripresentarsi.
    Ma quel controllo indica ciò che il server ha incontrato dal suo ultimo avvio, quindi dopo il riavvio legge `ok`
    in ogni caso: la riga del log è la prova reale.

**Tre cose da tenere a mente sul fidarsi del gateway.**

| Valore in `FORWARDED_ALLOW_IPS` | Pro | Contro |
| --- | --- | --- |
| Il gateway esatto, come `172.28.0.1` | La scelta più restrittiva. | Compose può assegnare alla rete un'altra subnet quando la ricrea (`docker compose down`, poi `docker compose up -d`): controlla di nuovo il gateway dopo un cambiamento del genere. |
| `172.16.0.0/12` | Sopravvive a quel cambiamento: copre ogni rete Docker da `172.16` a `172.31`. | Si fida di ogni rete Docker sul server. Non copre le reti `192.168.x.x` che Docker assegna una volta esaurite quelle. |

!!! warning "⚠️ Il gateway non è solo Tailscale"

    È anche l'indirizzo di ogni connessione effettuata sul server stesso attraverso la porta pubblicata, e dei
    visitatori IPv6 che il proxy di Docker trasmette ([Limiti](connection_checks.md#limits)).
    Fidarsi di esso consente loro di scegliere l'indirizzo conteggiato ai fini dei limiti.

    Raggiungi LibreFolio **solo** tramite `tailscale serve` o `tailscale funnel` sul server?
    Pubblica la porta solo sul loopback, così che nulla al di fuori del server possa raggiungerla.
    In `docker-compose.yml`, sotto `ports:`, cambia:

    ```yaml
    - "${PORT:-6040}:6040"
    ```

    in:

    ```yaml
    - "127.0.0.1:${PORT:-6040}:6040"
    ```

    Poi esegui `docker compose up -d`.

    Non con il Livello 4, né con gli indirizzi HTTP in chiaro dei Livelli 1 e 2: raggiungono la porta tramite
    l'indirizzo LAN o Tailscale del server.

---

## 🔗 Correlati

- 📄 **[Verifica della sicurezza della connessione](connection_checks.md)** — Checklist, Cosa mostra l'indicatore, La vista del server, …
