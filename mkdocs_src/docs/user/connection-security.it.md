# 🔐 Sicurezza della connessione

L'indicatore di sicurezza della connessione nella barra laterale di LibreFolio ti dice se ciò che
digiti — la tua password, i tuoi importi — viaggia cifrato tra il tuo dispositivo e il tuo server.
Mostra uno di tre livelli, **sicura**, **rete locale** o **non sicura**, a seconda dell'indirizzo
che hai aperto e della rete in cui ti trovi.

Per la massima sicurezza, assegna a LibreFolio un indirizzo HTTPS e usalo ovunque, anche sulla tua
rete domestica.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="security" data-name="connection-indicator" alt="L'indicatore di sicurezza della connessione in fondo alla barra laterale, aperto su Connessione: rete locale: il suo motivo, che chiunque sulla stessa rete può leggere il traffico, e il link Come connettersi in sicurezza" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🚦 I tre livelli

### 🟢 Connessione: sicura {: #connection-secure }

Ciò che digiti è cifrato, oppure non lascia mai il server.

<div class="lf-pros-cons" markdown>

| ✅ Pro | ⚠️ Contro |
|:--|:--|
| Nessuno lungo il percorso può leggerlo o modificarlo, nemmeno su un Wi-Fi pubblico. | Nessuno, sul piano del rischio. |

</div>

!!! warning "📱 Tailscale in HTTP in chiaro e l'app"

    Attraverso Tailscale con un indirizzo `http://` in chiaro, come `http://100.110.x.x:6040`, il
    tuo browser non [installerà LibreFolio come app](pwa.md). Per questo un indirizzo HTTPS resta
    migliore: come rischio i due sono uguali, perché anche Tailscale cifra il traffico.

👉 **Cosa fare:** niente, continua a usare questo indirizzo. Per l'app, passa a un
[indirizzo HTTPS](#https-address).

??? info "🔍 Quando una connessione è sicura"

    I dettagli danno uno di tre motivi:

    - **HTTPS**: qualsiasi indirizzo `https://`. Il tuo browser decide da solo, qualunque cosa veda
      il server.
    - **Sul server stesso**: `localhost`, i nomi che finiscono in `.localhost` e gli indirizzi di
      loopback come `127.0.0.1` e `::1`. Il tuo browser decide da solo: il traffico non esce da
      quel computer.
    - **VPN (Tailscale)**: un indirizzo `http://` in chiaro negli intervalli di Tailscale,
      `100.64.0.0/10` e `fd7a:115c:a1e0::/48`, o un nome che finisce in `.ts.net`. Tailscale cifra
      il traffico tra il tuo dispositivo e il server. Se invece il server vede arrivare la
      richiesta da internet, il livello è [rete locale](#connection-local-network), come incerto.

### 🏠 Connessione: rete locale {: #connection-local-network }

Hai aperto LibreFolio con `http://` in chiaro all'interno della tua rete domestica o d'ufficio, per
esempio su `http://192.168.1.100:6040`, l'indirizzo che usano gli altri dispositivi dopo
un'[installazione](installation.md) standard.

<div class="lf-pros-cons" markdown>

| 🤷 Ti accontenti di | ⚠️ Contro |
|:--|:--|
| Una connessione che non chiede configurazione, e il cui traffico resta nella tua rete. | Niente è cifrato: chiunque sia sulla stessa rete, come un ospite sul tuo Wi-Fi, potrebbe leggere il traffico, password compresa. |

</div>

👉 **Cosa fare:** usa l'[indirizzo HTTPS](#https-address) anche in casa.

Lo stesso livello compare con un motivo che inizia con *Incerta* quando LibreFolio non riesce a
capire dove ti trovi davvero: il consiglio non cambia.

??? info "🔍 Quando una connessione è di rete locale"

    **Un indirizzo locale con `http://` in chiaro**: un indirizzo in `10.x`, da `172.16.x` a
    `172.31.x`, in `192.168.x` o in `169.254.x`, un indirizzo IPv6 link-local o unique local,
    oppure un nome che finisce in `.local`, `.lan`, `.home.arpa` o `.internal`, o senza alcun
    punto, come `http://nas:6040`. Anche un nome MagicDNS breve di Tailscale, come
    `http://my-server:6040`, non ha punti, quindi conta qui: l'IP Tailscale o il nome completo che
    finisce in `.ts.net` conta come [sicuro](#connection-secure).

    **Incerta**: il tuo browser giudica l'indirizzo che hai aperto, e il server riferisce poi da dove
    vede arrivare la richiesta, solo il tipo di indirizzo e mai il tuo indirizzo IP. Il server può
    confermare il verdetto del browser o renderlo incerto, ma mai far contare una connessione come
    sicura; finché non risponde, vale il verdetto del browser. Quando i due non coincidono, il
    livello è rete locale e il motivo inizia con *Incerta*:

    - un indirizzo che sembra pubblico, che il server vede arrivare dalla tua rete locale, da
      Tailscale o dal server stesso, per esempio attraverso lo split DNS o un proxy locale;
    - un indirizzo locale o di Tailscale che il server vede arrivare da internet.

    Il traffico non è cifrato, e LibreFolio non riesce a capire dove ti trovi davvero.

### 🔴 Connessione: non sicura {: #connection-not-secure }

Hai raggiunto LibreFolio con `http://` in chiaro da internet, per esempio attraverso una porta
aperta sul tuo router. Su un telefono, un punto rosso sul pulsante del menu ti avvisa anche quando la
barra laterale è chiusa.

<div class="lf-pros-cons" markdown>

| ✅ Pro | ⚠️ Contro |
|:--|:--|
| Nessuno. | Password e dati viaggiano in chiaro su reti che non controlli: chiunque lungo il percorso potrebbe leggerli, o persino modificarli. |

</div>

👉 **Cosa fare:** evita questo indirizzo. Se gestisci il server, assegna a LibreFolio un
[indirizzo HTTPS](#https-address) e smetti di esporre l'HTTP in chiaro. Poi cambia la tua password:
**Impostazioni** → [**Profilo**](settings/profile.md) → **Cambia password**. Così vengono disconnessi anche tutti gli
altri dispositivi collegati al tuo account.

??? info "🔍 Quando una connessione non è sicura"

    **Un indirizzo pubblico con `http://` in chiaro**: un indirizzo o un nome che non è locale, né
    di Tailscale, né del server stesso, come un IP pubblico o un nome di dominio come
    `http://myhome.duckdns.org:6040`. Il livello resta quando anche il server vede arrivare la
    richiesta da internet, o non riesce a dirlo. Se la vede arrivare dalla tua rete locale, da
    Tailscale o dal server stesso, il livello è [rete locale](#connection-local-network), come
    incerto.

---

## 🔒 Come connettersi in sicurezza {: #https-address }

Assegna a LibreFolio un indirizzo HTTPS, poi usa solo quello. Lo configura chi gestisce il server,
in uno di questi due modi:

- **Tailscale**, senza aprire porte sul router: Tailscale Serve dà un indirizzo HTTPS ai
  dispositivi della tua tailnet, e Funnel un indirizzo pubblico che non richiede Tailscale sui tuoi
  dispositivi. Vedi [Esposizione sicura](../admin/service_exposure.md).
- **Un reverse proxy** con un certificato TLS, come Caddy, Traefik o Nginx: vedi
  [Docker avanzato](../admin/docker_advanced.md).

Poi segui qualche buona abitudine:

- usa l'indirizzo `https://` su ogni dispositivo, anche in casa;
- aggiungilo ai preferiti, e aggiorna i vecchi preferiti e le scorciatoie sulla schermata Home che
  puntano ancora a `http://`;
- se non gestisci tu il server, chiedi l'indirizzo a chi lo gestisce;
- guarda l'indicatore: deve mostrare **Connessione: sicura**.

Se gestisci il server, [Verificare la sicurezza della connessione](../admin/connection_checks.md)
mostra come controllare il risultato.

---

## 🧭 Cosa non fa l'indicatore

L'indicatore descrive la connessione che stai usando in questo momento, e ti consiglia. Ci sono tre
cose che non fa.

**Non blocca niente.** È un consiglio, non un controllo. E siccome descrive la connessione del
dispositivo che stai usando, lo stesso LibreFolio può mostrare **Connessione: sicura** sul tuo
portatile e **Connessione: non sicura** sul tuo telefono.

**Non controlla i certificati.** Un certificato autofirmato che hai accettato nel browser mostra
**Connessione: sicura**. Il traffico è cifrato, ma nessuno garantisce che il server sia davvero il
tuo.

**Non sempre vede dove ti trovi.** Quando LibreFolio gira in Docker Desktop ed è esposto
direttamente, o sta dietro un proxy che non passa il tuo indirizzo in `X-Forwarded-For`, il server
vede ogni visitatore come locale. L'HTTP in chiaro da internet mostra allora
**Connessione: rete locale**, come incerta, invece di **Connessione: non sicura**. Docker Engine su
Linux mantiene il tuo indirizzo.

Qualunque cosa mostri l'indicatore, il consiglio resta lo stesso: usa l'indirizzo HTTPS.

---

## 🔗 Correlati

- 🌐 **[Esposizione sicura](../admin/service_exposure.md)** — Tailscale, da una VPN privata a un
  indirizzo HTTPS pubblico
- 🔍 **[Verificare la sicurezza della connessione](../admin/connection_checks.md)** — Per gli
  amministratori: l'indirizzo HTTPS, il cookie di sessione e il reverse proxy
- 🐳 **[Docker avanzato](../admin/docker_advanced.md)** — File Compose, variabili d'ambiente,
  reverse proxy
- 📝 **[Configurazione](../admin/configuration.md)** — Ogni opzione del file `.env`
- 📦 **[Installazione con Docker](installation.md)** — Accesso locale e remoto dopo l'installazione
- 📱 **[Installa come app (PWA)](pwa.md)** — Richiede un indirizzo HTTPS
