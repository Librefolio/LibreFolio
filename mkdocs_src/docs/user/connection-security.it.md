# 🔐 Sicurezza della connessione

L'indicatore di sicurezza della connessione nella barra laterale di LibreFolio ti dice se ciò che
digiti — la tua password, i tuoi importi — viaggia crittografato tra il tuo dispositivo e il tuo
server. Mostra uno di tre livelli, a seconda dell'indirizzo che hai aperto e della rete in cui ti
trovi. Fai clic sulla sua riga per aprire o chiudere i dettagli: il motivo del livello e il link
**Come connettersi in sicurezza**, che apre questa pagina.
Con la barra laterale compressa, lo scudo mostra il livello quando ci passi sopra con il mouse, e un
clic apre la barra laterale con i dettagli.

Per la massima sicurezza, assegna a LibreFolio un indirizzo HTTPS e usalo ovunque, anche sulla tua
rete domestica.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="security" data-name="connection-indicator" alt="L'indicatore di sicurezza della connessione in fondo alla barra laterale, aperto su Connessione: rete locale: il suo motivo, che chiunque sulla stessa rete può leggere il traffico, e il link Come connettersi in sicurezza" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🚦 I tre livelli

### 🟢 Connessione: sicura {: #connection-secure }

Verde: ciò che digiti è crittografato, o non lascia mai il server. I dettagli indicano il motivo:

- HTTPS: la connessione è crittografata e il tuo browser la considera sicura.
- Sul server stesso (`localhost`): il traffico non lascia quel computer.
- VPN (Tailscale): Tailscale crittografa il traffico tra il tuo dispositivo e il server, anche se
  l'indirizzo inizia con `http://`, per esempio `http://100.110.x.x:6040`.

Quando il motivo è VPN, l'indirizzo è ancora `http://` in chiaro, quindi il tuo browser non
[installerà LibreFolio come app](pwa.md) da quell'indirizzo: il [passaggio 1](#https-address)
aggiunge HTTPS.

### 🏠 Connessione: rete locale {: #connection-local-network }

Verde chiaro: hai aperto LibreFolio tramite `http://` in chiaro all'interno della tua rete domestica
o aziendale, per esempio `http://192.168.1.100:6040`, l'indirizzo che altri dispositivi usano dopo
un'[installazione](installation.md) standard. Il traffico non è crittografato: chiunque sulla
stessa rete, come un ospite sul tuo Wi-Fi, potrebbe leggerlo, password inclusa. Per la massima
sicurezza, usa l'indirizzo HTTPS anche a casa.

**Connessione: rete locale** compare anche, con un motivo che inizia con *Non chiaro* nei dettagli,
quando l'indirizzo che hai aperto e la sorgente che il server vede non concordano: un indirizzo
dall'aspetto pubblico che il server vede arrivare dalla tua rete locale (split DNS, o un proxy
locale), oppure un indirizzo locale o Tailscale che il server vede arrivare da internet. Il traffico
non è crittografato e LibreFolio non può dire dove ti trovi davvero: usa l'indirizzo HTTPS.

### 🔴 Connessione: non sicura {: #connection-not-secure }

Rosso: hai raggiunto LibreFolio tramite `http://` in chiaro da internet, per esempio attraverso una
porta aperta sul tuo router. Password e dati viaggiano in chiaro su reti che non controlli: chiunque
lungo il percorso potrebbe leggerli, o persino modificarli. Su un telefono, un punto rosso sul
pulsante del menu ti avvisa anche mentre la barra laterale è chiusa.

Evita questo indirizzo. Se gestisci il server, assegna a LibreFolio un indirizzo HTTPS
([passaggio 1](#https-address)) e smetti di esporre HTTP in chiaro. Poi cambia la password:
**Impostazioni** → [**Profilo**](settings/profile.md) → **Cambia password**.

??? info "🔍 Come viene scelto il livello"

    Il tuo browser classifica l'indirizzo che hai digitato in uno di quattro tipi:

    - questo computer: `localhost` e indirizzi di loopback;
    - Tailscale: `100.64.0.0/10`, `fd7a:115c:a1e0::/48` e nomi che terminano con `.ts.net`;
    - rete locale: indirizzi `10.x`, da `172.16.x` a `172.31.x`, `192.168.x` e `169.254.x`, IPv6
      link-local e unique local, e nomi che terminano con `.local`, `.lan`, `.home.arpa` o
      `.internal`, oppure senza alcun punto;
    - internet: tutto il resto.

    HTTPS è sempre sicuro. HTTP in chiaro è considerato sicuro per `localhost`, e per un indirizzo
    Tailscale a meno che il server non veda la richiesta arrivare da internet.

    Il server classifica l'indirizzo da cui proviene ogni richiesta negli stessi tipi e riporta solo
    il tipo, mai il tuo indirizzo IP. Può confermare il verdetto del browser o renderlo incerto, ma
    non può mai far considerare sicura una connessione. Finché non risponde, vale il verdetto del
    browser.

---

## 🔒 Come connettersi in sicurezza

### 🌐 1. Assegna a LibreFolio un indirizzo HTTPS {: #https-address }

Questo è compito di chi gestisce il server: se non sei tu, chiedi a chi lo gestisce l'indirizzo
HTTPS. Due modi:

- Tailscale: segui [Esposizione sicura](../admin/service_exposure.md). Con il suo Livello 1 (VPN
  privata) attivo, esegui `tailscale serve --bg 6040` sul server (o il tuo `PORT`), poi apri
  `https://<server-name>.your-tailnet.ts.net`. Per un indirizzo HTTPS pubblico che non richiede
  Tailscale sui tuoi dispositivi, usa Funnel (Livelli 3 e 4).
- Un reverse proxy con un certificato TLS, come Caddy, Traefik o Nginx: vedi
  [Docker avanzato](../admin/docker_advanced.md).

Tailscale, Caddy e Traefik comunicano a LibreFolio l'uso di HTTPS autonomamente; Nginx richiede due
righe: vedi [Dietro un reverse proxy](#reverse-proxy).

### 🔖 2. Usa l'indirizzo HTTPS ovunque

Usalo su ogni dispositivo, anche a casa:

- Salva nei preferiti `https://…`, non `http://192.168.x.x:6040`.
- Aggiorna i vecchi preferiti e le scorciatoie sulla schermata Home che puntano ancora a `http://`.
- Apri LibreFolio dal nuovo indirizzo: l'indicatore mostra **Connessione: sicura**.

---

## 🧰 Dietro un reverse proxy {: #reverse-proxy }

*Per gli amministratori.* Un reverse proxy riceve la connessione HTTPS e la passa a LibreFolio
tramite HTTP in chiaro. Ciò che conta qui è il cookie di sessione che ti mantiene connesso: con
`SESSION_COOKIE_SECURE=auto`, il valore predefinito, LibreFolio lo contrassegna come `Secure`
(inviato solo su HTTPS) quando la richiesta è HTTPS, direttamente o perché il proxy invia
`X-Forwarded-Proto: https`.

Tailscale Serve e Funnel, Caddy e Traefik inviano quell'header autonomamente. Caddy e Traefik passano
anche il tuo indirizzo in `X-Forwarded-For`, il che consente all'indicatore di vedere da dove ti
connetti. Nginx richiede entrambe le righe nel blocco `location` che passa le richieste a
LibreFolio:

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

Se il tuo browser usa HTTPS ma il cookie di sessione non è contrassegnato come `Secure`, perché il
proxy non invia `X-Forwarded-Proto` o perché `SESSION_COOKIE_SECURE` è `never`, gli amministratori
vedono una riga in più nei dettagli dell'indicatore. Il livello resta **Connessione: sicura**, perché
la connessione è crittografata; solo il cookie è privo di `Secure`:

> Il tuo browser usa HTTPS, ma il cookie di sessione non è contrassegnato come Secure. Fai in modo che il reverse proxy invii
> X-Forwarded-Proto (Nginx: `proxy_set_header X-Forwarded-Proto $scheme;`), oppure riporta
> SESSION_COOKIE_SECURE su auto se è never.

??? tip "⚙️ Imposta invece `SESSION_COOKIE_SECURE`"

    Inviare l'header è la soluzione migliore. Se raggiungi LibreFolio solo tramite HTTPS, puoi
    invece aggiungere questa riga a `.env`:

    ```bash
    SESSION_COOKIE_SECURE=always
    ```

    Poi riavvia LibreFolio: con Docker, esegui `docker compose up -d` (un semplice
    `docker compose restart` mantiene il vecchio ambiente); in un'installazione host, riavvia
    `./dev.py server`, che legge anch'esso `.env`.

    L'opzione accetta `auto` (il valore predefinito), `always` o `never`; maiuscole/minuscole e spazi
    non contano, e qualsiasi altro valore arresta LibreFolio all'avvio. Usa `never` solo per il raro
    proxy che dichiara HTTPS mentre il browser è su HTTP in chiaro. Vedi
    [Configurazione](../admin/configuration.md) per tutte le opzioni.

---

## 🧭 Cosa non fa l'indicatore

- Non blocca nulla: è un consiglio, non un controllo.
- Descrive la connessione che stai usando in questo momento: lo stesso LibreFolio può mostrare
  **Connessione: sicura** sul tuo laptop e **Connessione: non sicura** sul tuo telefono.
- Non controlla i certificati: un certificato autofirmato che hai accettato nel browser mostra
  **Connessione: sicura**. Il traffico è crittografato, ma nessuno garantisce che il server sia
  davvero tuo.
- Non può sempre vedere dove ti trovi. Con Docker Desktop esposto direttamente, o dietro un proxy
  che non passa il tuo indirizzo in `X-Forwarded-For`, il server vede ogni visitatore come locale:
  HTTP in chiaro da internet mostra quindi **Connessione: rete locale**, come non chiaro, invece di
  **Connessione: non sicura**. Docker Engine su Linux conserva il tuo indirizzo. Il consiglio non
  cambia: usa l'indirizzo HTTPS.

---

## 🔗 Correlati

- 🌐 **[Esposizione sicura](../admin/service_exposure.md)** — Tailscale, da una VPN privata a un
  indirizzo HTTPS pubblico
- 🐳 **[Docker avanzato](../admin/docker_advanced.md)** — File Compose, variabili d'ambiente,
  reverse proxy
- 📝 **[Configurazione](../admin/configuration.md)** — Ogni opzione del file `.env`
- 📦 **[Installazione con Docker](installation.md)** — Accesso locale e remoto dopo l'installazione
- 📱 **[Installa come app (PWA)](pwa.md)** — Richiede un indirizzo HTTPS
