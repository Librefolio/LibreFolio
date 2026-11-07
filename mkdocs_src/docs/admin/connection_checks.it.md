# 🔍 Verifica della sicurezza della connessione

In fondo alla barra laterale, ogni utente vede quanto è sicura la comunicazione tra il browser e il server:
**Connessione: sicura**, **Connessione: rete locale** oppure **Connessione: non sicura**.
I tre livelli, spiegati agli utenti: [Sicurezza della connessione](../user/connection-security.md).

Questa pagina è per chi gestisce il server: come verificare che il tuo deployment mostri **Connessione: sicura**, e come correggerlo quando non accade.

L'obiettivo:

- un indirizzo HTTPS, da Tailscale Serve o Funnel ([Esposizione sicura](service_exposure.md)) oppure da un reverse proxy con un certificato ([Dietro un reverse proxy](connection_proxy.md#reverse-proxy));
- un cookie di sessione contrassegnato `Secure`.

!!! info "📚 Questa guida è suddivisa in più pagine"

    Questa pagina è la lista di controllo: cosa mostra l'indicatore, come esaminare la vista del server e il cookie di sessione, cosa fare quando un controllo fallisce.
    Se esegui LibreFolio dietro un reverse proxy, [Verifica della sicurezza della connessione: dietro un reverse proxy](connection_proxy.md) spiega gli header che deve inviare e come LibreFolio apprende l'indirizzo del visitatore.

---

## ✅ Lista di controllo {: #checklist }

Percorrila una volta che il tuo indirizzo HTTPS funziona, e di nuovo dopo ogni modifica al proxy o a `.env`.
Ti servono un account amministratore e, per gli ultimi due controlli, un telefono con i dati mobili attivi.

1. **Apri l'indirizzo HTTPS e accedi.**

    L'indicatore mostra 🟢 **Connessione: sicura**; i dettagli dicono che la connessione è cifrata con HTTPS.

2. **Cerca la riga del cookie.** Da amministratore, i dettagli mostrano:

    - quel motivo e il link **Come connettersi in sicurezza**;
    - un link ai [controlli di sicurezza](settings.md#security-tab) quando elencano errori o avvisi, ad esempio **2 avvisi di sicurezza**.

    Una riga in più sul cookie di sessione significa che LibreFolio non sa dell'HTTPS: vedi [Dietro un reverse proxy](connection_proxy.md#reverse-proxy).

3. **Chiedi al server.** In una nuova scheda, apri:

    ```text
    https://<your address>/api/v1/system/connection
    ```

    La risposta contiene `"cookie_secure":true` ([La vista del server](#server-view)).

4. **Guarda il cookie.** Apri gli strumenti per sviluppatori del browser.

    Il cookie `session` è contrassegnato `Secure` ([Il cookie di sessione](#session-cookie)).

5. **Dall'esterno, apri l'indirizzo HTTPS.** Sul telefono, con il Wi-Fi disattivato.

    La pagina si carica e, dopo l'accesso, l'indicatore mostra 🟢 **Connessione: sicura**.

    | Indirizzo | Tailscale sul telefono |
    | --- | --- |
    | Funnel o reverse proxy | Disattivato |
    | Tailscale Serve (lo apre solo il tuo tailnet) | Attivato |

6. **Dall'esterno, prova HTTP semplice.** Sullo stesso telefono, apri:

    ```text
    http://<your public IP or name>:6040
    ```

    Oppure il tuo `PORT`. La pagina **non** si carica.

    Se compare la pagina di login, HTTP semplice è aperto a Internet:

    - non accedere da lì: la password viaggerebbe in chiaro;
    - chiudi la porta ([Quando un controllo fallisce](#when-a-check-fails)).

    Chi accede da quell'indirizzo vede 🔴 **Connessione: non sicura**, oppure 🏠 **Connessione: rete locale** con motivo *Non chiaro* quando il server non vede da dove arrivano i visitatori ([Limiti](#limits)).

Tutti i controlli superati? Chiedi ai tuoi utenti di usare l'indirizzo HTTPS su ogni dispositivo e di aggiornare i vecchi segnalibri ([Come connettersi in sicurezza](../user/connection-security.md#https-address)).

!!! note "📶 Non hai ancora un indirizzo HTTPS?"

    Con il Livello 1 o 2 di [Esposizione sicura](service_exposure.md), gli utenti raggiungono LibreFolio tramite HTTP semplice.
    Controlla il livello che riceve ciascun indirizzo ([Cosa mostra l'indicatore](#indicator)) e che HTTP semplice non si carichi dall'esterno (controllo 6).
    I controlli sui cookie non si applicano: su HTTP semplice il cookie di sessione non è `Secure`, e `"cookie_secure":false` è previsto.

---

## 🚦 Cosa mostra l'indicatore {: #indicator }

Il browser valuta l'indirizzo che ha aperto.
Il server poi segnala da dove vede arrivare la richiesta: può confermare il verdetto o renderlo incerto, mai renderlo sicuro.

| Come gli utenti raggiungono LibreFolio | Esempio | Livello |
| --- | --- | --- |
| Tailscale Serve o Funnel, o un reverse proxy con un certificato | `https://librefolio.your-tailnet.ts.net` | 🟢 **sicura**: HTTPS |
| Sul server stesso | `http://localhost:6040` | 🟢 **sicura**: `localhost` |
| IP Tailscale o nome MagicDNS completo, HTTP semplice (Livello 1) | `http://100.a.b.c:6040` | 🟢 **sicura**: VPN (Tailscale) |
| Nome MagicDNS breve, HTTP semplice: un nome senza punti viene considerato locale | `http://your-server:6040` | 🏠 **rete locale** |
| Indirizzo locale, anche tramite un subnet router (Livello 2) | `http://192.168.1.100:6040` | 🏠 **rete locale** |
| Una porta aperta sul router, HTTP semplice | `http://myhome.duckdns.org:6040` | 🔴 **non sicura** |

Quando il server non vede gli indirizzi dei visitatori, l'ultima riga mostra invece 🏠 **rete locale** con motivo *Non chiaro* ([Limiti](#limits)).
Le regole esatte di ogni livello (intervalli di indirizzi, nomi, casi *Non chiaro*): [Sicurezza della connessione](../user/connection-security.md#connection-secure).

---

## 🔎 La vista del server {: #server-view }

A ogni caricamento della pagina, l'indicatore chiede al server come vede la connessione: `GET /api/v1/system/connection`.

Per leggere la stessa risposta:

1. **Accedi a LibreFolio.**

2. **Apri questo indirizzo in una nuova scheda dello stesso browser**, con il tuo indirizzo LibreFolio al posto dell'esempio:

    ```text
    https://librefolio.your-tailnet.ts.net/api/v1/system/connection
    ```

    Il browser mostra una risposta su una riga:

    ```json
    {"client_class":"public","cookie_secure":true}
    ```

Da sapere:

- va bene qualsiasi account, non solo un amministratore;
- `{"detail":"Not authenticated"}` significa che non c'è alcuna sessione su quell'indirizzo: le sessioni appartengono a un indirizzo, quindi accedere a `http://192.168.1.100:6040` non ti fa accedere all'indirizzo HTTPS;
- l'indicatore chiede una sola volta per caricamento: ricarica LibreFolio dopo una modifica per vedere il nuovo verdetto.

**`cookie_secure`**: se un cookie di sessione impostato su questa richiesta sarebbe `Secure`, in base a [`SESSION_COOKIE_SECURE`](#session-cookie).

| Indirizzo | Valore atteso |
| --- | --- |
| HTTPS | `true`. `false` fa comparire la riga per l'amministratore sul cookie ([Dietro un reverse proxy](connection_proxy.md#reverse-proxy)) |
| HTTP semplice | `false` |

**`client_class`**: da dove il server vede arrivare la richiesta.
Legge l'ultimo valore `X-Forwarded-For`, quello aggiunto dal proxy più vicino, se è un indirizzo IP; altrimenti l'indirizzo della connessione stessa.
Dal server esce solo la classe: l'indirizzo non viene mai restituito né registrato nei log.

| `client_class` | La richiesta proviene da |
| --- | --- |
| `loopback` | Il server stesso: `127.0.0.0/8` o `::1` |
| `vpn` | Tailscale o Headscale: `100.64.0.0/10` o `fd7a:115c:a1e0::/48` |
| `lan` | Una rete locale: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `fe80::/10` o `fc00::/7` |
| `public` | Qualsiasi altro indirizzo: Internet |
| `unknown` | Nessun indirizzo, o uno non leggibile |

La classe conta solo su HTTP semplice, e non sul server stesso (`localhost`):

| Indirizzo nel browser | `client_class` | Effetto sul verdetto |
| --- | --- | --- |
| Pubblico | `public` o `unknown` | Conferma **Connessione: non sicura** |
| Pubblico | `loopback`, `vpn` o `lan` | Diventa **Connessione: rete locale**: verdetto incerto |
| Locale o Tailscale | `public` | Verdetto incerto |
| Locale o Tailscale | Qualsiasi altra | Nessuno |

Sull'indirizzo HTTPS la classe non cambia nulla, ma ti dice se il server vede gli indirizzi dei visitatori.
Dal telefono in rete mobile, con Tailscale disattivato:

- `public`: il server li vede;
- `lan` o `loopback`: non li vede ([Limiti](#limits)).

---

## 🍪 Il cookie di sessione {: #session-cookie }

Il cookie che mantiene l'accesso si chiama `session`.
LibreFolio lo imposta all'accesso, sempre con `HttpOnly` (gli script nella pagina non possono leggerlo) e `SameSite=Lax`.

Se sia anche `Secure`, cioè inviato solo su HTTPS, dipende da `SESSION_COOKIE_SECURE` in `.env`:

| Valore | `Secure` |
| --- | --- |
| `auto` (predefinito) | Quando la richiesta è HTTPS: rilevato direttamente, o perché il primo valore `X-Forwarded-Proto` inviato da un reverse proxy è `https` |
| `always` | Sempre |
| `never` | Mai |

Maiuscole/minuscole e spazi attorno al valore non contano.
Qualsiasi altro valore blocca LibreFolio all'avvio.
Quando `always` o `never` è la scelta giusta: [Configurazione](configuration.md#session-cookie-secure).

Il flag viene deciso all'accesso: un cookie già nel browser mantiene il flag ricevuto allora.
Dopo aver corretto il proxy o l'opzione, esci e accedi di nuovo.

Per vedere il flag nel browser:

1. **Accedi all'indirizzo HTTPS.**

2. **Apri gli strumenti per sviluppatori**: `F12`, oppure tasto destro sulla pagina → **Ispeziona**.

    Safari li mostra solo dopo aver attivato le funzioni per sviluppatori nelle sue impostazioni.

3. **Apri i cookie del tuo indirizzo LibreFolio.**

    | Browser | Percorso |
    | --- | --- |
    | Chrome, Edge | **Applicazione** → **Cookie** |
    | Firefox, Safari | **Archiviazione** → **Cookie** |

4. **Leggi la riga `session`.**

    **Secure** è spuntato (`true` in Firefox), come **HttpOnly**; **SameSite** riporta `Lax`.

La console non può mostrarlo: `document.cookie` omette i cookie `HttpOnly`.

---

## 🛠️ Quando un controllo fallisce {: #when-a-check-fails }

| Cosa vedi | Perché | Cosa fare |
| --- | --- | --- |
| L'indirizzo HTTPS non mostra **Connessione: sicura** | La pagina non è su HTTPS: la barra degli indirizzi mostra `http://` | Apri l'indirizzo `https://` e fai reindirizzare dal proxy `http://` verso di esso |
| La riga sul cookie di sessione, oppure `"cookie_secure":false` sull'indirizzo HTTPS | Il proxy non invia `X-Forwarded-Proto: https`, oppure `SESSION_COOKIE_SECURE` è `never` | Correggi il proxy ([Dietro un reverse proxy](connection_proxy.md#reverse-proxy)) o riporta l'opzione a `auto`, poi ricarica |
| `"cookie_secure":true`, ma il cookie `session` non è `Secure` | Il cookie è stato impostato prima della correzione | Esci e accedi di nuovo |
| `{"detail":"Not authenticated"}` | Nessuna sessione su questo indirizzo | Accedi su questo indirizzo, nello stesso browser |
| Ogni accesso termina di nuovo sulla pagina di login | Il cookie è `Secure`, ma il browser usa HTTP semplice: `SESSION_COOKIE_SECURE=always`, oppure un proxy che invia `X-Forwarded-Proto: https` a un browser su HTTP semplice | Usa l'indirizzo HTTPS o correggi il proxy: [Configurazione](configuration.md#session-cookie-secure) |
| Dall'esterno, l'indirizzo HTTPS non si carica | Un indirizzo Tailscale Serve è privato; un nuovo Funnel richiede approvazione e qualche minuto | Attiva Tailscale sul telefono, oppure usa Funnel; approva il Funnel e attendi ([Esposizione sicura: accesso pubblico con Funnel](service_exposure_funnel.md#step-2-approve-and-wait-for-propagation)) |
| Dall'esterno, `http://…:6040` in HTTP semplice si carica | La porta di LibreFolio è aperta a Internet: un port forwarding sul router, o un server con un indirizzo pubblico | Chiudila: rimuovi il port forwarding o blocca la porta nel firewall del server. Tailscale non richiede porte aperte, un reverse proxy solo la propria |
| `client_class` mostra `lan` o `loopback` da una rete mobile, oppure HTTP semplice da Internet mostra **Connessione: rete locale**, *Non chiaro* | Il server non vede da dove provengono i visitatori | Vedi [Limiti](#limits); con Nginx, aggiungi la riga `X-Forwarded-For` |
| Un indirizzo Tailscale mostra **Connessione: rete locale** | Un nome MagicDNS breve non contiene punti, quindi viene considerato locale | Usa l'IP Tailscale, il nome completo `.ts.net` o, meglio, l'indirizzo HTTPS |

---

## ⚠️ Limiti {: #limits }

L'indicatore è un consiglio, non un controllo: non blocca nulla.
Due limiti contano quando verifichi un deployment.

**Non vede sempre da dove provengono i visitatori.**

- Con Docker Desktop esposto direttamente, o dietro un proxy che non passa l'indirizzo del visitatore in `X-Forwarded-For`, il server vede ogni visitatore come locale: `lan`, oppure `loopback` per un proxy sulla stessa macchina.
- HTTP semplice da Internet mostra quindi **Connessione: rete locale**, con verdetto incerto, invece di **Connessione: non sicura**.
- Gli indirizzi HTTPS non sono interessati: mostrano **Connessione: sicura** in entrambi i casi.
- Docker Engine su Linux conserva l'indirizzo del visitatore su IPv4.
- Su IPv6, a meno che il container abbia un proprio indirizzo IPv6, i visitatori IPv6 arrivano tramite il proxy di Docker, dal gateway della rete del container: condividono tutti quell'unico indirizzo locale, sia per l'indicatore sia per i limiti per indirizzo del visitatore, che pertanto li contano insieme.
- Il proxy di Docker non aggiunge alcun header di inoltro, quindi LibreFolio non può accorgersene: il suo avviso su un proxy di cui non si fida richiede un header di questo tipo.
- Lo evita un reverse proxy posto davanti che vede l'indirizzo di ogni visitatore, configurato come spiega [L'indirizzo del visitatore](connection_proxy.md#client-address).

**Non controlla i certificati.**

- Un certificato autofirmato che un utente ha accettato nel browser mostra **Connessione: sicura**: il traffico è cifrato, ma nessuno garantisce che il server sia davvero il tuo.

Né l'indicatore né il cookie di sessione richiedono un elenco di proxy attendibili:

- un `X-Forwarded-For` falsificato inganna solo l'indicatore di chi lo ha inviato;
- `X-Forwarded-Proto` può solo attivare `Secure`, quindi un `https` falsificato rompe solo l'accesso del mittente stesso.

I limiti per indirizzo del visitatore sono un'altra questione: [L'indirizzo del visitatore](connection_proxy.md#client-address).

---

## 🔗 Correlati

- 📄 **[Verifica della sicurezza della connessione: dietro un reverse proxy](connection_proxy.md)** — Quali proxy LibreFolio considera attendibili, l'indirizzo del visitatore, Tailscale con Docker
- 🔐 **[Sicurezza della connessione](../user/connection-security.md)** — La guida utente: i tre livelli e cosa fare in ciascuno
- 🌐 **[Esposizione sicura](service_exposure.md)** — Tailscale, da una VPN privata a un indirizzo HTTPS pubblico
- 🐳 **[Docker avanzato](docker_advanced.md)** — File Compose, variabili d'ambiente, reverse proxy
- 📝 **[Configurazione](configuration.md)** — `SESSION_COOKIE_SECURE` e ogni altra opzione di `.env`
