# 🔐 Sicurezza della connessione

L'indicatore di sicurezza della connessione nella barra laterale di LibreFolio ti dice se ciò che
digiti — la tua password, i tuoi importi — viaggia cifrato tra il tuo dispositivo e il tuo server.
Mostra uno dei tre livelli, **sicura**, **rete locale** o **non sicura**, a seconda dell'indirizzo
con cui hai aperto l'applicazione e della rete in cui ti trovi. Gli amministratori vedono inoltre
qui quando i controlli di sicurezza dell'istanza richiedono la loro attenzione: vedi
[Avvisi di sicurezza per gli amministratori](#security-warnings).

Per la massima sicurezza, assegna a LibreFolio un indirizzo HTTPS e usalo ovunque, anche sulla tua
rete domestica.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="security" data-name="connection-indicator" alt="L'indicatore di sicurezza della connessione in fondo alla barra laterale, aperto su Connessione: rete locale: il suo motivo, ovvero che chiunque sulla stessa rete può leggere il traffico, e il link Come connettersi in sicurezza" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🚦 I tre livelli

### 🟢 Connessione: sicura {: #connection-secure }

Ciò che digiti è cifrato, oppure non lascia mai il server.

<div class="lf-pros-cons" markdown>

| ✅ Pro | ⚠️ Contro |
|:--|:--|
| Nessuno lungo il percorso può leggerlo o modificarlo, nemmeno su un Wi-Fi pubblico. | Nulla, dal punto di vista del rischio. |

</div>

!!! warning "📱 Tailscale su HTTP semplice e l'app"

    Tramite Tailscale con un indirizzo `http://` semplice, come `http://100.110.x.x:6040`, il tuo
    browser non [installerà LibreFolio come app](pwa.md). Per questo un indirizzo HTTPS è comunque
    migliore: quanto a rischio i due sono identici, dato che anche Tailscale cifra il traffico.

👉 **Cosa fare:** nulla, continua a usare questo indirizzo. Per l'app, passa a un
[indirizzo HTTPS](#https-address).

??? info "🔍 Quando una connessione è considerata sicura"

    I dettagli riportano uno dei tre motivi:

    - **HTTPS**: qualsiasi indirizzo `https://`. Decide il tuo browser da solo, qualunque cosa veda il server.
    - **Sul server stesso**: `localhost`, nomi che terminano in `.localhost` e indirizzi di loopback
      come `127.0.0.1` e `::1`. Decide il tuo browser da solo: il traffico non lascia quel
      computer.
    - **VPN (Tailscale)**: un indirizzo `http://` semplice negli intervalli di Tailscale, `100.64.0.0/10` e
      `fd7a:115c:a1e0::/48`, o un nome che termina in `.ts.net`. Tailscale cifra il traffico tra
      il tuo dispositivo e il server. Se invece il server vede la richiesta provenire da internet,
      il livello è [rete locale](#connection-local-network), con motivo «Incerto».

### 🏠 Connessione: rete locale {: #connection-local-network }

Hai aperto LibreFolio tramite `http://` semplice all'interno della tua rete domestica o aziendale,
per esempio su `http://192.168.1.100:6040`, l'indirizzo che gli altri dispositivi usano dopo un'[installazione](installation.md) standard.

<div class="lf-pros-cons" markdown>

| 🤷 Ti accontenti di | ⚠️ Contro |
|:--|:--|
| Una connessione che non richiede configurazione e il cui traffico resta dentro la tua rete. | Nulla è cifrato: chiunque sulla stessa rete, come un ospite sul tuo Wi-Fi, potrebbe leggere il traffico, password inclusa. |

</div>

👉 **Cosa fare:** usa l'[indirizzo HTTPS](#https-address) anche a casa.

Lo stesso livello compare con un motivo che inizia con *Incerto* quando LibreFolio non riesce a
determinare dove ti trovi davvero: il consiglio non cambia.

??? info "🔍 Quando una connessione è considerata rete locale"

    **Un indirizzo locale tramite `http://` semplice**: un indirizzo in `10.x`, da `172.16.x` a `172.31.x`,
    `192.168.x` o `169.254.x`, un indirizzo IPv6 link-local o unique local, oppure un nome che termina in
    `.local`, `.lan`, `.home.arpa` o `.internal`, o senza alcun punto, come
    `http://nas:6040`. Un nome breve MagicDNS di Tailscale, come `http://my-server:6040`, non contiene nemmeno un punto, quindi rientra qui: l'IP di Tailscale o il nome completo che termina in
    `.ts.net` è considerato [sicuro](#connection-secure).

    **Incerto**: il tuo browser valuta l'indirizzo con cui hai aperto l'applicazione, e poi il server
    segnala da dove vede arrivare la richiesta, solo il tipo di indirizzo e mai il tuo indirizzo IP. Il
    server può confermare il verdetto del browser o renderlo incerto, ma mai far considerare sicura
    una connessione; finché non risponde, vale il verdetto del browser. Quando i due non concordano, il
    livello è rete locale e il motivo inizia con *Incerto*:

    - un indirizzo che sembra pubblico ma che il server vede arrivare dalla tua rete locale, da Tailscale
      o dal server stesso, per esempio tramite split DNS o un proxy locale;
    - un indirizzo locale o di Tailscale che il server vede arrivare da internet.

    Il traffico non è cifrato e LibreFolio non riesce a determinare dove ti trovi davvero.

### 🔴 Connessione: non sicura {: #connection-not-secure }

Hai raggiunto LibreFolio tramite `http://` semplice da internet, per esempio attraverso una porta
aperta sul tuo router. Su un telefono, un punto rosso sul pulsante del menu ti avvisa anche mentre
la barra laterale è chiusa.

<div class="lf-pros-cons" markdown>

| ✅ Pro | ⚠️ Contro |
|:--|:--|
| Nessuno. | Password e dati viaggiano in chiaro su reti che non controlli: chiunque lungo il percorso potrebbe leggerli, o persino modificarli. |

</div>

👉 **Cosa fare:** evita questo indirizzo. Se gestisci il server, assegna a LibreFolio un
[indirizzo HTTPS](#https-address) e smetti di esporre HTTP semplice. Poi cambia la password:
**Impostazioni** → [**Profilo**](settings/profile.md) → **Cambia password**. Questo disconnette anche ogni altro dispositivo
collegato al tuo account.

??? info "🔍 Quando una connessione è considerata non sicura"

    **Un indirizzo pubblico tramite `http://` semplice**: un indirizzo o un nome che non è locale, non è
    Tailscale e non è il server stesso, come un IP pubblico o un nome di dominio tipo
    `http://myhome.duckdns.org:6040`. Il livello vale quando anche il server vede la richiesta arrivare
    da internet, o non riesce a determinarlo. Se vede la richiesta arrivare dalla tua rete locale, da
    Tailscale o dal server stesso, il livello è [rete locale](#connection-local-network), con motivo «Incerto».

---

## 🔒 Come connettersi in sicurezza {: #https-address }

Assegna a LibreFolio un indirizzo HTTPS, poi usa solo quello. Chi gestisce il server lo configura, in
uno dei due modi:

- **Tailscale**, senza aprire alcuna porta sul router: Tailscale Serve assegna un indirizzo HTTPS ai
  dispositivi della tua tailnet, e Funnel uno pubblico che non richiede Tailscale sui tuoi dispositivi. Vedi
  [Esporre in modo sicuro](../admin/service_exposure.md).
- **Un reverse proxy** con un certificato TLS, come Caddy, Traefik o Nginx: vedi
  [Docker avanzato](../admin/docker_advanced.md).

Poi segui qualche buona abitudine:

- usa l'indirizzo `https://` su ogni dispositivo, anche a casa;
- aggiungilo ai segnalibri e aggiorna i vecchi segnalibri e le scorciatoie sulla schermata home che
  puntano ancora a `http://`;
- se non gestisci il server, chiedi l'indirizzo a chi lo gestisce;
- controlla l'indicatore: dovrebbe mostrare **Connessione: sicura**.

Se gestisci il server, [Verificare la sicurezza della connessione](../admin/connection_checks.md) spiega come
verificare il risultato.

---

## 🛡️ Avvisi di sicurezza per gli amministratori {: #security-warnings }

Se sei un amministratore, la stessa riga ti segnala anche, su ogni pagina, quando i controlli di
sicurezza della tua istanza richiedono la tua attenzione: gli errori e gli avvisi che **Impostazioni** →
**Amministrazione** → **Sicurezza** elenca, e conta nella sua scheda.

- **Un punto sull'icona.** Un piccolo punto si trova nell'angolo dello scudo della riga, con la barra
  laterale espansa o compressa: rosso quando almeno un controllo è un errore, ambrato quando ci sono solo
  avvisi.
- **Un link nei dettagli.** Clicca la riga: dopo il motivo, un link riporta il conteggio, come
  **2 avvisi di sicurezza**, errori inclusi. Apre la scheda **Sicurezza**, dove ogni rilevamento indica
  cosa non va, e chiude i dettagli.
- **Il conteggio in parole.** Con la barra laterale compressa, passando il puntatore sullo scudo vengono mostrati il livello e il
  conteggio, come *Connessione: sicura — 2 avvisi di sicurezza*. Uno screen reader legge lo stesso, con la
  barra laterale espansa o compressa.
- **Su un telefono**, la barra laterale si nasconde dietro il pulsante del menu, quindi anche il pulsante porta il punto: rosso
  in presenza di un errore, o quando la connessione è [non sicura](#connection-not-secure), ambrato con solo
  avvisi. Apri il menu per vedere la riga.

Il punto segue la scheda **Sicurezza**: le informazioni non vengono mai conteggiate, quindi con solo informazioni, o
nulla, non c'è alcun punto. LibreFolio legge i controlli una volta sola, quando si apre nel tuo browser:
dopo aver corretto qualcosa sul server e averlo riavviato, ricarica la pagina, oppure clicca **Controlla di nuovo** sulla
scheda. Gli altri utenti non vedono mai il punto né il link, e il loro browser non richiede mai i controlli.
Cosa significa ogni controllo e come risolverlo: «Sicurezza» in
[Impostazioni globali](../admin/settings.md#security-tab).

---

## 🧭 Cosa non fa l'indicatore

L'indicatore descrive la connessione che stai usando in questo momento e fornisce consigli. Tre cose sono
al di fuori della sua portata.

**Non blocca nulla.** È un consiglio, non un controllo. E poiché descrive la connessione del
dispositivo su cui ti trovi, lo stesso LibreFolio può mostrare **Connessione: sicura** sul tuo portatile e
**Connessione: non sicura** sul tuo telefono.

**Non verifica i certificati.** Un certificato autofirmato che hai accettato nel browser
mostra **Connessione: sicura**. Il traffico è cifrato, ma nessuno garantisce che il server sia
davvero il tuo.

**Non riesce sempre a vedere dove ti trovi.** Quando LibreFolio gira in Docker Desktop ed è esposto
direttamente, o si trova dietro un proxy che non trasmette il tuo indirizzo in `X-Forwarded-For`, il server
vede ogni visitatore come locale. L'HTTP semplice da internet mostra allora
**Connessione: rete locale**, con motivo «Incerto», invece di **Connessione: non sicura**. Docker Engine su
Linux conserva il tuo indirizzo.

Qualunque cosa mostri l'indicatore, il consiglio resta lo stesso: usa l'indirizzo HTTPS.

---

## 🔗 Correlati

- 🌐 **[Esporre in modo sicuro](../admin/service_exposure.md)** — Tailscale, da una VPN privata a un
  indirizzo HTTPS pubblico
- 🔍 **[Verificare la sicurezza della connessione](../admin/connection_checks.md)** — Per gli amministratori: l'indirizzo
  HTTPS, il cookie di sessione e il reverse proxy
- 🐳 **[Docker avanzato](../admin/docker_advanced.md)** — File Compose, variabili d'ambiente,
  reverse proxy
- 📝 **[Configurazione](../admin/configuration.md)** — Ogni opzione del file `.env`
- 📦 **[Installazione con Docker](installation.md)** — Accesso locale e remoto dopo l'installazione
- 📱 **[Installazione come app (PWA)](pwa.md)** — Richiede un indirizzo HTTPS
