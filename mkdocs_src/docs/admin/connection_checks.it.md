# 🔍 Verificare la sicurezza della connessione

Ogni utente vede, in fondo alla barra laterale di LibreFolio, quanto è sicuro il dialogo tra il suo
browser e il server: **Connessione: sicura**, **Connessione: rete locale** o
**Connessione: non sicura**. La guida per l'utente, [Sicurezza della connessione](../user/connection-security.md),
gli spiega i tre livelli. Questa pagina è per chi gestisce il server: come verificare che la tua
installazione dia ai suoi utenti **Connessione: sicura**, e come correggerla quando non lo fa.

L'obiettivo è un indirizzo HTTPS, da Tailscale Serve o Funnel
([Esposizione sicura](service_exposure.md)) o da un reverse proxy con un certificato
([Dietro un reverse proxy](#reverse-proxy)), e un cookie di sessione marcato `Secure`.

---

## ✅ Lista di controllo {: #checklist }

Percorrila una volta che il tuo indirizzo HTTPS funziona, e di nuovo dopo ogni modifica al proxy o a
`.env`. Ti servono un account amministratore e, per gli ultimi due controlli, un telefono con i dati
mobili.

1. **Apri l'indirizzo HTTPS e accedi.** L'indicatore mostra 🟢 **Connessione: sicura**, e i suoi
   dettagli dicono che la connessione è cifrata con HTTPS.
2. **Cerca la riga del cookie.** Con l'accesso da amministratore, i dettagli mostrano solo quel
   motivo e il link **Come connettersi in sicurezza**. Una riga in più, sul cookie di sessione,
   significa che LibreFolio non sa dell'HTTPS: vedi [Dietro un reverse proxy](#reverse-proxy).
3. **Chiedi al server.** In una nuova scheda, apri `https://<your address>/api/v1/system/connection`:
   la risposta contiene `"cookie_secure":true` ([Il punto di vista del server](#server-view)).
4. **Guarda il cookie.** Negli strumenti per sviluppatori del browser, il cookie `session`
   è marcato `Secure` ([Il cookie di sessione](#session-cookie)).
5. **Da fuori, apri l'indirizzo HTTPS.** Sul telefono, con il Wi-Fi spento, la pagina si carica e,
   una volta fatto l'accesso, l'indicatore mostra 🟢 **Connessione: sicura**. Tieni Tailscale
   spento sul telefono per un indirizzo Funnel o di reverse proxy; accendilo per un indirizzo
   Tailscale Serve, che solo la tua tailnet può aprire.
6. **Da fuori, prova l'HTTP in chiaro.** Sullo stesso telefono, `http://<your public IP or name>:6040`,
   o la tua `PORT`, non si carica. Se compare la pagina di accesso, l'HTTP in chiaro è aperto a
   internet: non accedere lì, perché la password viaggerebbe in chiaro, e chiudi la porta
   ([Quando un controllo fallisce](#when-a-check-fails)). Chi accede da quell'indirizzo vede
   🔴 **Connessione: non sicura**, o 🏠 **Connessione: rete locale** con un motivo *Incerta*
   quando il server non vede da dove arrivano i visitatori ([Limiti](#limits)).

Tutti i controlli superati? Chiedi ai tuoi utenti di usare l'indirizzo HTTPS su ogni dispositivo e
di aggiornare i loro vecchi preferiti ([Come connettersi in sicurezza](../user/connection-security.md#https-address)).

!!! note "📶 Ancora nessun indirizzo HTTPS?"

    Con il Livello 1 o 2 di [Esposizione sicura](service_exposure.md), gli utenti raggiungono
    LibreFolio con l'HTTP in chiaro. Controlla il livello che ottiene ogni indirizzo
    ([Cosa mostra l'indicatore](#indicator)) e che l'HTTP in chiaro non si carichi da fuori
    (controllo 6). I controlli sul cookie non si applicano: con l'HTTP in chiaro il cookie di
    sessione non è `Secure`, e `"cookie_secure":false` è atteso.

---

## 🚦 Cosa mostra l'indicatore {: #indicator }

Il browser giudica l'indirizzo che ha aperto; il server riferisce poi da dove vede arrivare la
richiesta, e può confermare quel verdetto o renderlo incerto, ma mai renderlo sicuro. Ecco cosa
vedono i tuoi utenti, secondo il modo in cui raggiungono LibreFolio:

| Come gli utenti raggiungono LibreFolio | Esempio | Livello |
| --- | --- | --- |
| Tailscale Serve o Funnel, o un reverse proxy con un certificato | `https://librefolio.your-tailnet.ts.net` | 🟢 **sicura**: HTTPS |
| Sul server stesso | `http://localhost:6040` | 🟢 **sicura**: `localhost` |
| IP Tailscale o nome MagicDNS completo, HTTP in chiaro (Livello 1) | `http://100.a.b.c:6040` | 🟢 **sicura**: VPN (Tailscale) |
| Nome MagicDNS breve, HTTP in chiaro: un nome senza punto conta come locale | `http://your-server:6040` | 🏠 **rete locale** |
| Indirizzo locale, anche attraverso un subnet router (Livello 2) | `http://192.168.1.100:6040` | 🏠 **rete locale** |
| Una porta aperta sul router, HTTP in chiaro | `http://myhome.duckdns.org:6040` | 🔴 **non sicura** |

Quando il server non vede gli indirizzi dei tuoi visitatori, l'ultima riga mostra invece
🏠 **rete locale** con un motivo *Incerta* ([Limiti](#limits)). La guida per l'utente dà le regole
esatte sotto ogni livello: intervalli di indirizzi, nomi e casi *Incerta*
([Sicurezza della connessione](../user/connection-security.md#connection-secure)).

---

## 🔎 Il punto di vista del server {: #server-view }

L'indicatore chiede al server come vede la connessione, una volta per ogni caricamento della
pagina: `GET /api/v1/system/connection`. Puoi leggere la stessa risposta: con l'accesso fatto, apri
questo indirizzo in una nuova scheda dello stesso browser, con il tuo indirizzo LibreFolio al posto
di quello dell'esempio:

```text
https://librefolio.your-tailnet.ts.net/api/v1/system/connection
```

Il browser mostra una risposta di una riga, per esempio:

```json
{"client_class":"public","cookie_secure":true}
```

Va bene qualsiasi account, non solo un amministratore. Una risposta come `{"detail":"Not authenticated"}`
significa che a quell'indirizzo non c'è una sessione: le sessioni appartengono a un indirizzo,
quindi accedere su `http://192.168.1.100:6040` non ti fa accedere all'indirizzo HTTPS. E siccome
l'indicatore chiede una sola volta per caricamento della pagina, ricarica LibreFolio dopo una
modifica per vedere il suo nuovo verdetto.

**`cookie_secure`** dice se un cookie di sessione impostato su questa richiesta sarebbe `Secure`,
secondo [`SESSION_COOKIE_SECURE`](#session-cookie). Sull'indirizzo HTTPS deve essere `true`: `false`
è ciò che mostra la riga per l'amministratore sul cookie ([Dietro un reverse proxy](#reverse-proxy)).
Con l'HTTP in chiaro, `false` è atteso.

**`client_class`** è da dove il server vede arrivare la richiesta. Legge l'ultimo valore di
`X-Forwarded-For`, quello aggiunto dal proxy più vicino, quando è un indirizzo IP, e altrimenti
l'indirizzo della connessione stessa. Dal server esce solo la classe: l'indirizzo non viene mai
restituito né registrato nei log.

| `client_class` | La richiesta arriva da |
| --- | --- |
| `loopback` | Il server stesso: `127.0.0.0/8` o `::1` |
| `vpn` | Tailscale o Headscale: `100.64.0.0/10` o `fd7a:115c:a1e0::/48` |
| `lan` | Una rete locale: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `fe80::/10` o `fc00::/7` |
| `public` | Qualsiasi altro indirizzo: internet |
| `unknown` | Nessun indirizzo, o uno che non si riesce a leggere |

La classe conta solo con l'HTTP in chiaro, e non sul server stesso (`localhost`):

- con un indirizzo pubblico nel browser, `public` o `unknown` conferma **Connessione: non sicura**,
  mentre `loopback`, `vpn` o `lan` la trasformano in **Connessione: rete locale**, come incerta;
- con un indirizzo locale o di Tailscale nel browser, `public` rende il verdetto incerto, e
  qualsiasi altra classe lo lascia com'è.

Sull'indirizzo HTTPS la classe non cambia niente, ma ti dice se il server riesce a vedere gli
indirizzi dei tuoi visitatori: dal telefono con i dati mobili, con Tailscale spento, `public`
significa che ci riesce, e `lan` o `loopback` che non ci riesce ([Limiti](#limits)).

---

## 🍪 Il cookie di sessione {: #session-cookie }

Il cookie che tiene un utente connesso si chiama `session`. LibreFolio lo imposta all'accesso,
sempre `HttpOnly`, così gli script della pagina non possono leggerlo, e `SameSite=Lax`. Se è anche
`Secure`, cioè inviato solo con HTTPS, dipende da `SESSION_COOKIE_SECURE` in `.env`:

- **`auto`**, il predefinito: `Secure` quando la richiesta è HTTPS, vista direttamente o perché il
  primo valore di `X-Forwarded-Proto` inviato da un reverse proxy è `https`;
- **`always`**: sempre `Secure`;
- **`never`**: mai `Secure`.

Maiuscole e spazi intorno al valore non contano; qualsiasi altro valore ferma LibreFolio all'avvio.
Quando `always` o `never` sono la scelta giusta: [Configurazione](configuration.md#session-cookie-secure).

L'attributo si decide all'accesso: il cookie che un browser ha già tiene l'attributo che ha avuto
allora. Dopo aver corretto il proxy o l'opzione, esci e accedi di nuovo.

Per vedere l'attributo nel browser:

1. Accedi all'indirizzo HTTPS.
2. Apri gli strumenti per sviluppatori: `F12`, oppure clic destro sulla pagina e **Ispeziona**.
   Safari li mostra solo dopo aver attivato le sue funzioni per sviluppatori nelle impostazioni.
3. Apri i cookie del tuo indirizzo LibreFolio: **Application** → **Cookies** in Chrome ed Edge,
   **Storage** → **Cookies** in Firefox e Safari (i nomi seguono la lingua del browser).
4. Nella riga `session`, **Secure** è spuntato (`true` in Firefox), e così **HttpOnly**;
   **SameSite** indica `Lax`.

La console non può mostrarlo: `document.cookie` esclude i cookie `HttpOnly`.

---

## 🧰 Dietro un reverse proxy {: #reverse-proxy }

Un reverse proxy riceve la connessione HTTPS e la passa a LibreFolio in HTTP in chiaro, quindi
LibreFolio sa dell'HTTPS, e del visitatore, solo dalle intestazioni del proxy:

- `X-Forwarded-Proto: https` dice che il browser usa HTTPS: con `SESSION_COOKIE_SECURE=auto`, il
  predefinito, LibreFolio marca allora il cookie di sessione `Secure`;
- `X-Forwarded-For` porta l'indirizzo del visitatore, che permette all'indicatore di vedere da dove
  si connettono gli utenti.

Tailscale Serve e Funnel, Caddy e Traefik le inviano entrambe da soli. Nginx ha bisogno di entrambe
le righe nel blocco `location` che passa le richieste a LibreFolio:

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

Se il browser usa HTTPS ma il cookie di sessione non è marcato `Secure`, perché il proxy non invia
`X-Forwarded-Proto` o perché `SESSION_COOKIE_SECURE` è `never`, gli amministratori vedono una riga
in più nei dettagli dell'indicatore. Il livello resta **Connessione: sicura**, perché la connessione
è cifrata; solo al cookie manca `Secure`:

> Il browser usa HTTPS, ma il cookie di sessione non è marcato Secure. Fai mandare X-Forwarded-Proto
> al reverse proxy (Nginx: `proxy_set_header X-Forwarded-Proto $scheme;`), oppure riporta
> SESSION_COOKIE_SECURE ad auto se è never.

Una volta corretto il proxy, ricarica LibreFolio: la riga scompare. Poi esci e accedi di nuovo,
così che il browser riceva un cookie `Secure`.

??? tip "⚙️ Imposta invece `SESSION_COOKIE_SECURE`"

    Inviare l'intestazione è la correzione migliore. Se raggiungi LibreFolio sempre e solo in HTTPS,
    puoi invece aggiungere questa riga a `.env`:

    ```bash
    SESSION_COOKIE_SECURE=always
    ```

    Poi riavvia LibreFolio: con Docker, esegui `docker compose up -d` (un semplice
    `docker compose restart` mantiene il vecchio ambiente); con un'installazione sull'host, riavvia
    `./dev.py server`, che legge anch'esso `.env`. Poi esci e accedi di nuovo.

    Usa `never` solo per il raro proxy che dichiara HTTPS mentre il browser è in HTTP in chiaro. Vedi
    [Configurazione](configuration.md#session-cookie-secure) per ogni opzione.

---

## 🛠️ Quando un controllo fallisce {: #when-a-check-fails }

| Cosa vedi | Perché | Cosa fare |
| --- | --- | --- |
| L'indirizzo HTTPS non mostra **Connessione: sicura** | La pagina non è in HTTPS: la barra degli indirizzi mostra `http://` | Apri l'indirizzo `https://`, e fai reindirizzare `http://` lì dal proxy |
| La riga sul cookie di sessione, o `"cookie_secure":false` sull'indirizzo HTTPS | Il proxy non invia `X-Forwarded-Proto: https`, o `SESSION_COOKIE_SECURE` è `never` | Correggi il proxy ([Dietro un reverse proxy](#reverse-proxy)) o riporta l'opzione ad `auto`, poi ricarica |
| `"cookie_secure":true`, ma il cookie `session` non è `Secure` | Il cookie è stato impostato prima della correzione | Esci e accedi di nuovo |
| `{"detail":"Not authenticated"}` | Nessuna sessione a questo indirizzo | Accedi a questo indirizzo, nello stesso browser |
| Ogni accesso finisce di nuovo sulla pagina di accesso | Il cookie è `Secure`, ma il browser usa l'HTTP in chiaro: `SESSION_COOKIE_SECURE=always`, o un proxy che invia `X-Forwarded-Proto: https` a un browser in HTTP in chiaro | Usa l'indirizzo HTTPS, o correggi il proxy: vedi [Configurazione](configuration.md#session-cookie-secure) |
| Da fuori, l'indirizzo HTTPS non si carica | Un indirizzo Tailscale Serve è privato; un nuovo Funnel ha bisogno di approvazione e di qualche minuto | Accendi Tailscale sul telefono, o usa Funnel; approva il Funnel e aspetta ([Esposizione sicura](service_exposure.md)) |
| Da fuori, `http://…:6040` in chiaro si carica | La porta di LibreFolio è aperta a internet: un port forward sul router, o un server con un indirizzo pubblico | Chiudila: rimuovi il port forward, o blocca la porta nel firewall del server. Tailscale non ha bisogno di porte aperte, e un reverse proxy solo della sua |
| `client_class` indica `lan` o `loopback` dai dati mobili, o l'HTTP in chiaro da internet mostra **Connessione: rete locale**, *Incerta* | Il server non vede da dove arrivano i visitatori | Vedi [Limiti](#limits); con Nginx, aggiungi la riga `X-Forwarded-For` |
| Un indirizzo Tailscale mostra **Connessione: rete locale** | Un nome MagicDNS breve non ha punti, quindi conta come locale | Usa l'IP Tailscale, il nome completo `.ts.net` o, meglio, l'indirizzo HTTPS |

---

## ⚠️ Limiti {: #limits }

L'indicatore è un consiglio, non un controllo: non blocca niente. Due limiti contano quando verifichi
un'installazione.

**Non sempre vede dove sono i visitatori.** Con Docker Desktop esposto direttamente, o dietro un
proxy che non passa l'indirizzo del visitatore in `X-Forwarded-For`, il server vede ogni visitatore
come locale: `lan`, o `loopback` per un proxy sulla stessa macchina. L'HTTP in chiaro da internet
mostra allora **Connessione: rete locale**, come incerta, invece di **Connessione: non sicura**.
Docker Engine su Linux mantiene l'indirizzo del visitatore. Gli indirizzi HTTPS non ne risentono:
mostrano **Connessione: sicura** in ogni caso.

**Non controlla i certificati.** Un certificato autofirmato che un utente ha accettato nel browser
mostra **Connessione: sicura**: il traffico è cifrato, ma nessuno garantisce che il server sia
davvero il tuo.

Non c'è nessun elenco di proxy fidati da configurare. `X-Forwarded-For` alimenta solo l'indicatore,
quindi un valore falsificato inganna solo l'indicatore di chi l'ha inviato; `X-Forwarded-Proto` può
solo attivare `Secure`, quindi un `https` falsificato rompe solo l'accesso di chi l'ha inviato.

---

## 🔗 Correlati

- 🔐 **[Sicurezza della connessione](../user/connection-security.md)** — La guida per l'utente: i
  tre livelli e cosa fare per ciascuno
- 🌐 **[Esposizione sicura](service_exposure.md)** — Tailscale, da una VPN privata a un indirizzo
  HTTPS pubblico
- 🐳 **[Docker avanzato](docker_advanced.md)** — File Compose, variabili d'ambiente, reverse proxy
- 📝 **[Configurazione](configuration.md)** — `SESSION_COOKIE_SECURE` e ogni altra opzione di `.env`
