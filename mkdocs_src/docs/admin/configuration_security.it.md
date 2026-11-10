# 🛡️ Configurazione: controlli e protezioni

Questa pagina riguarda:

- i **controlli all'avvio**: cosa dice ogni riscontro, dove si risolve e con quale valore;
- le **protezioni del browser**: la Content-Security-Policy e la protezione dei frame;
- l'**arresto del server**.

Le opzioni che questi controlli esaminano sono spiegate in [Configurazione](configuration.md); i secret in
[Configurazione: secret e impostazioni dei plugin](configuration_secrets.md).

---

## 🩺 Controlli all'avvio {: #startup-checks }

Subito dopo la riga `Starting LibreFolio`, il server controlla la propria configurazione senza modificare nulla.

**Dove li leggi:**

| Dove | Come |
| --- | --- |
| Il log del server | Una riga per riscontro, al livello corrispondente, con il nome del controllo in `check` (es. `platform.jwt_secret`). |
| **Impostazioni › Amministrazione › Sicurezza** (solo amministratori) | Gli stessi controlli, nella lingua dell'app; un numero sulla scheda conta errori e avvisi. Dopo aver corretto e riavviato, fai clic su **Controlla di nuovo** ([Sicurezza](settings.md#security-tab)). |

**Dove li risolvi:** salvo dove la tabella dice altro, nel **file `.env`** di LibreFolio.
Poi riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`.

| Livello | Il log dice (`check`) | Dove | Cosa fare |
| --- | --- | --- | --- |
| ℹ️ `info` | `The session key is random: every restart signs everyone out. To stay signed in, set JWT_SECRET.` | `.env` | Nulla, se disconnettere tutti a ogni riavvio va bene. Altrimenti imposta `JWT_SECRET`: [Mantieni gli utenti connessi](index.md#session-persistence). |
| ⚠️ `warning` | `The session signing key from JWT_SECRET is … characters long: use at least 32 random characters` (o `from JWT_SECRET_FILE (<path>)`) | `.env`, o il file che la riga nomina | Genera una chiave di almeno 32 caratteri casuali, come in [Mantieni gli utenti connessi](index.md#session-persistence), e mettila dove indica la riga. |
| ⚠️ `warning` | `Set both directly and through a *_FILE variable: …` | `.env` | Per ogni secret elencato, tieni solo una delle due: la variabile stessa ha la precedenza, il file viene ignorato. |
| ❌ `error` | `The instance key cannot be used: …`, che termina con `cannot be reached (Permission denied)` o `cannot be read (…)` | Riga di comando, sul server: la cartella `secrets/` e `instance.key` | Appartengono a un altro utente, o i permessi impediscono a LibreFolio di accedervi. Restituisci la proprietà di entrambi all'utente che esegue LibreFolio (`chown`), poi `chmod 700` sulla cartella e `chmod 600` sul file. Non sostituire mai la chiave con una nuova. Il server si avvia comunque. |
| ❌ `error` | `The instance key cannot be used: …`, con un altro motivo, come `is empty or blank` | Il file `secrets/instance.key` | È danneggiata: ripristinala da un backup, non sostituirla mai con una chiave nuova. Il server si avvia comunque. |
| ⚠️ `warning` | `… is open to other users (…): the folder should be 0700 and the file 0600` | Riga di comando, sul server | `chmod 700` sulla cartella `secrets/`, `chmod 600` su `instance.key`. |
| ⚠️ `warning` | `SESSION_COOKIE_SECURE=never: the session cookie is sent over plain HTTP too; prefer auto` | `.env` | Torna a `auto`, a meno che tu non abbia davvero bisogno di `never`: [`SESSION_COOKIE_SECURE`](configuration.md#session-cookie-secure). |
| ℹ️ `info` | `The log level is DEBUG: the log records operational detail; …` (o `TRACE`) | `.env` | Torna a `INFO` quando hai finito di risolvere i problemi. |
| ❌ `error` | `LIBREFOLIO_TEST_MODE is on outside a test lane: test-only providers are served, the data are kept in the test data directory <path> and .env is not read; unset it on a production instance` (`platform.test_mode`) | L'ambiente del server, non `.env`: cerca da dove proviene, per esempio da un'unità di servizio | Rimuovi `LIBREFOLIO_TEST_MODE`, oppure impostala a `0`, poi riavvia. La modalità test serve ai test di LibreFolio stesso (`./dev.py test`, `./dev.py server --test`), che la attivano e disattivano da soli. Fino ad allora il server lavora sulla cartella che la riga nomina, non sulla tua [cartella dei dati](filesystem.md): ciò che inserisci nel frattempo viene salvato lì. |
| ❌ `error` | `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB cannot be used: expected a whole number of megabytes, 0 for no limit; restore uploads answer 503 until it is fixed` (`backup.upload_limit`) | `.env` | Un numero intero di megabyte, `0` per nessun limite, oppure rimuovi la variabile ([Il limite di upload di un ripristino](backup_restore.md#restore-upload-limit)). Fino ad allora Impostazioni › Amministrazione › Backup non può caricare un archivio da ripristinare; la riga di comando ne ripristina comunque uno. Il server si avvia comunque. |
| ❌ `error` | `LIBREFOLIO_BACKUP_MAX_RESTORE_MB cannot be used: expected a whole number of megabytes, 0 for no limit; restore checks answer 503 until it is fixed` (`backup.restore_limit`) | `.env` | Come sopra, nella variabile che la riga nomina. Fino ad allora ogni controllo di un ripristino è rifiutato con `backup_restore_unavailable`, da Impostazioni › Amministrazione › Backup e dalla riga di comando, dove `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` davanti a `backup restore` rimuove il limite per quel comando. Il server si avvia comunque. |
| ❌ `error` | `LIBREFOLIO_BACKUP_RECIPIENTS: item 2 is not an age recipient: …; the hosting panel's backups answer 503 until it is fixed` (o `expected at most 2 recipients`, `repeats an earlier recipient`) (`backup.recipients`) | `.env` | Una o due chiavi pubbliche `age1…`, separate da virgole, come le fornisce `backup keygen` ([Backup sigillati](backup_sealed.md#sealed)). Il server si avvia comunque. |
| ⚠️ `warning` | `LIBREFOLIO_LOGIN_LIMIT=off: failed sign-ins are not limited; turn it back on unless this is a test instance` (`accounts.login_limit`) | `.env` | Nulla, su un'istanza destinata ai test. Altrimenti rimuovi la variabile, oppure impostala a `on`: [Accessi falliti](configuration_accounts.md#login-limit). |
| ❌ `error` | `LIBREFOLIO_SMTP_… cannot be used (SMTP_…): email stays off until it is fixed` (`email.smtp`) | `.env`, la variabile che la riga nomina | È disattivata solo l'email, nient'altro. Cosa significa ogni codice: [Problemi di configurazione](email_troubleshooting.md#configuration-problems). Il server si avvia comunque. |
| ⚠️ `warning` | `LIBREFOLIO_SMTP_TLS=none with …: emails, their links and the SMTP password travel unencrypted; use starttls or tls` | `.env` | `LIBREFOLIO_SMTP_TLS=starttls` o `tls`, oppure invia tramite un relay sulla tua rete: [Note di sicurezza](email_troubleshooting.md#security). |
| ℹ️ `info` | `LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out` (`email.links`) | `.env` | Nulla, se nessun link deve uscire via email. Altrimenti imposta `LIBREFOLIO_PUBLIC_URL` sull'indirizzo a cui i tuoi utenti aprono LibreFolio ([Account e registrazioni](configuration_accounts.md#accounts), [Email](email.md)). |
| ⚠️ `warning` | `LIBREFOLIO_PUBLIC_URL cannot start a link (it needs http:// or https:// and a host, with no user name, password, ? or #): no email with a link (forgotten password, invitation, reset) can go out` (`email.links`) | `.env` | Scrivi l'indirizzo con `http://` o `https://` e un nome host, senza nome utente, password, `?` o `#`, come `https://librefolio.example.com` ([Email](email.md)). |
| ❌ `error` | `Stored plugin secrets that the instance key cannot read: <N>. Enter them again in the plugin settings, or restore the instance key they were saved with` (`platform.plugin_secrets`; compare più avanti, dopo che il database è pronto) | `secrets/instance.key` o `LIBREFOLIO_INSTANCE_KEY`; solo in ultima istanza **Impostazioni › Plugin** | La chiave dell'istanza è cambiata dopo il salvataggio di questi [secret dei plugin](configuration_secrets.md#plugin-secrets): procedura sotto. Il server si avvia comunque. |

??? note "🔑 Secret dei plugin illeggibili: rimettere la vecchia chiave"

    Cause: una `secrets/instance.key` persa che LibreFolio ha sostituito con una nuova, dati ripristinati senza la
    relativa `secrets/`, o un'altra `LIBREFOLIO_INSTANCE_KEY`.

    Se il log dice anche `The instance key cannot be used: …`, correggi prima quello (tabella sopra).

    1. **Hai ancora la vecchia chiave?** La tua copia di `secrets/instance.key`, salvata insieme alla cartella dei
       dati come dice [La chiave dell'istanza](configuration_secrets.md#instance-key), oppure il vecchio valore della
       variabile. Un archivio in chiaro creato con **Esegui il backup dell'istanza** lascia fuori la chiave; uno
       [sicuro](backup_restore.md#secure) porta con sé la chiave generata da LibreFolio e il suo ripristino ricifra
       questi secret.
    2. **Ferma LibreFolio**, metti la vecchia chiave al posto della nuova, avvia di nuovo.
       I secret tornano leggibili.

    !!! warning "⚠️ Prima che qualcuno inserisca di nuovo un secret"

        Un secret inserito di nuovo viene salvato sotto la nuova chiave e diventa illeggibile quando la vecchia
        torna in uso.

    Solo se la vecchia chiave è andata persa: inserisci di nuovo i secret in **Impostazioni › Plugin**. Da quel
    momento, la chiave da salvare è quella nuova.

    I secret personali non sono conteggiati: ogni utente vede i propri nella propria scheda.

**Errori che bloccano l'avvio.** Il server non parte, e l'errore è nell'output della console (con Docker,
`docker compose logs librefolio`): nomina la variabile e, quando esiste, il file, mai il secret. Correggi, poi avvia
di nuovo.

| Causa | Dove |
| --- | --- |
| Un `JWT_SECRET_FILE` o un `LIBREFOLIO_INSTANCE_KEY_FILE` che non riesce a fornire il proprio secret | Il file che la variabile indica ([Secret nei file](configuration_secrets.md#secret-files)) |
| Una chiave dell'istanza fornita da te più corta di 32 caratteri | `.env`, `LIBREFOLIO_INSTANCE_KEY` |
| Un `LIBREFOLIO_LOGIN_LIMIT` diverso da `on` o `off` | `.env` ([Accessi falliti](configuration_accounts.md#login-limit)) |

---

## 🛡️ Protezioni del browser {: #browser-protections }

Ogni risposta di LibreFolio porta header che dicono al browser come proteggere le sue pagine.

| Header | Da impostare? | Cosa fa |
| --- | --- | --- |
| `X-Content-Type-Options: nosniff` | No, sempre presente | Il browser usa il tipo che LibreFolio invia: un file caricato non viene mai eseguito come script né mostrato come pagina. |
| `Referrer-Policy: strict-origin-when-cross-origin` | No, sempre presente | Un altro sito apprende al massimo l'indirizzo di LibreFolio (`https://librefolio.example.com`), mai la pagina di partenza. |
| `Content-Security-Policy` | No, su ogni pagina in ogni profilo, senza interruttore | [La Content-Security-Policy](#csp). |
| `X-Frame-Options` + `frame-ancestors` | `LIBREFOLIO_FRAME_PROTECTION` in `.env`, spento su un'installazione tua | [Protezione dei frame](#frame-protection). |
| `Content-Security-Policy-Report-Only` | `LIBREFOLIO_CSP_REPORT_ONLY` in `.env`, spento su un'installazione tua | [La policy di sola segnalazione](#csp-report-only). |

I due interruttori sono letti all'avvio: dopo una modifica riavvia LibreFolio. Con Docker Compose, esegui
`docker compose up -d`. Per gli sviluppatori: [Header delle risposte](../developer/architecture/security.md#response-headers).

### 🛡️ La Content-Security-Policy {: #csp }

Dice al browser cosa può eseguire una pagina e a cosa può connettersi. LibreFolio ne **applica sempre** una, in ogni
profilo, senza impostazione per disattivarla. Nel caso usuale non ti chiede nulla: conta solo quando qualcosa tra
LibreFolio e il browser aggiunge uno script alla pagina ([Uno script che non hai inviato](#csp-blocked-script)).

| Cosa | Policy | Effetto |
|---|---|---|
| Ogni pagina di LibreFolio: la web app, la documentazione (`/mkdocs`) e, dove sono attive, le pagine proprie dell'API a `/api/v1/docs` e `/api/v1/redoc` | `object-src 'none'; base-uri 'self'; form-action 'self'` | Nessun contenuto plugin (`<object>`, `<embed>`), nessun `<base>` e nessun form verso un altro sito: LibreFolio non ne usa nessuno. Un PDF non è una pagina: non ne contiene nessuna. |
| Le pagine della web app | `script-src`: solo gli script di LibreFolio stesso; i suoi script inline sono consentiti dal loro hash, calcolato dai file della web app | Uno script scritto nella pagina da chiunque altro non viene eseguito. |
| Le pagine della web app | `worker-src 'self' blob:` | I worker del visualizzatore PDF. |
| Le pagine proprie dell'API a `/api/v1/docs` e `/api/v1/redoc`, solo dove `LIBREFOLIO_API_DOCS` è attivo | `script-src 'self' https://cdn.jsdelivr.net`, `worker-src 'self' blob:`, `connect-src 'self'` | Pagine proprie di LibreFolio, non di FastAPI: Swagger UI e ReDoc da `cdn.jsdelivr.net` a una versione fissa, con checksum verificato dal browser (Subresource Integrity). Script di avvio dalla tua istanza: nessuno script inline, nessun Google Fonts. Il worker è la ricerca di ReDoc. Con le pagine disattivate, nulla di tutto questo esiste. |
| Gli script della build della web app, i file sotto `/_app/` | `script-src 'self'`, lo stesso `connect-src` delle pagine, `worker-src 'self' blob:`, `object-src 'none'`, `base-uri 'self'` | Vale solo se un browser esegue uno di questi file come **worker**: carica gli script di LibreFolio e nient'altro, si connette solo dove possono le pagine. Oggi l'unico worker avviato da un file è quello che elabora i prezzi; quello del visualizzatore PDF parte da un `blob:` e mantiene la policy della pagina. |
| Le pagine della web app | `connect-src 'self'`, l'origine di [`LIBREFOLIO_PUBLIC_URL`](configuration_accounts.md#accounts) quando è impostata, e `https://api.github.com` solo su un'installazione self-hosted | Dove la pagina può inviare richieste. GitHub serve alla verifica di una nuova release, che il tuo browser effettua quando un amministratore accede (mai nel profilo `managed`). |
| Ogni risposta, con la [Protezione dei frame](#frame-protection) attiva | `frame-ancestors 'self'` | Solo le pagine di LibreFolio stesso possono mostrarla in un frame. |

**Non** applica `default-src`, `style-src`, `img-src`, `font-src` e `frame-src`: immagini (le icone di asset e broker
sono un link a qualsiasi indirizzo), stili, font e frame restano liberi. Se un'altra pagina può mostrare LibreFolio in
un frame lo decide solo [`LIBREFOLIO_FRAME_PROTECTION`](#frame-protection).

Quando ricostruisci la web app dai sorgenti mentre LibreFolio è in esecuzione, gli hash seguono la nuova build: non
devi riavviarlo.

??? note "📄 L'anteprima PDF non chiede nulla a terze parti"

    Il motore del visualizzatore è una copia propria di LibreFolio, e `connect-src` resta limitato all'indirizzo di
    LibreFolio stesso. Se quella copia non è raggiungibile, l'anteprima mostra il visualizzatore PDF del tuo browser.

    L'unica cosa che il visualizzatore scarica è il testo cinese, giapponese e coreano, e la chiede alla tua istanza
    (`/api/v1/files/pdf-fonts/…`, solo per utenti autenticati). La prima volta, **il server** scarica il font da
    `cdn.jsdelivr.net` (indirizzo e versione fissi), lo conserva solo se il suo checksum (sha256) corrisponde all'elenco
    fornito con LibreFolio, e lo memorizza in `cache/pdf-fonts/` nella [cartella dei dati](filesystem.md).

    - Puoi eliminare quella cartella: i font vengono scaricati di nuovo quando un PDF ne ha bisogno. Non fa parte di
      un backup.
    - Un'istanza che non raggiunge `cdn.jsdelivr.net` mostra quel PDF senza quei caratteri.
    - Un file che non corrisponde all'elenco viene scartato, e il log ha un avviso che lo nomina.

#### 🕵️ Uno script che non hai inviato {: #csp-blocked-script }

Un proxy, un CDN o un'estensione del browser che **aggiunge uno script** alle pagine di LibreFolio viene bloccato,
come qualsiasi altra cosa che LibreFolio non ha inviato.

**Cosa vedi:**

- la pagina funziona, ma può perdere il pezzo che quello script forniva: un contatore, un indirizzo offuscato, un
  widget dell'estensione;
- la console del browser mostra, una volta per caricamento della pagina:

    ```text
    LibreFolio blocked a script it did not send (<source>): a proxy, a CDN or a browser extension adds it. Guide: https://<your address>/mkdocs/admin/configuration_security/#csp
    ```

    `<source>` è l'indirizzo da cui è venuto lo script, o `inline` per uno script scritto nella pagina;

- in **Impostazioni › Amministrazione › Sicurezza** ([Sicurezza](settings.md#security-tab)), il browser che l'ha
  incontrato mostra l'avviso *uno script è stato bloccato*, con le sorgenti. L'avviso appartiene a quella scheda del
  browser e sparisce quando la chiudi.

Non viene inviato nulla al tuo server: nessun report, nessuna richiesta. Console e scheda sono gli unici posti in cui
il browser lo segnala.

**Cosa fare:** disattiva l'aggiunta per l'indirizzo di LibreFolio. Nessuna impostazione amplia la policy.

| Chi aggiunge lo script | Dove si risolve | Cosa fare |
| --- | --- | --- |
| **Cloudflare**: Rocket Loader, Email Address Obfuscation, configurazione automatica di Web Analytics | La dashboard di Cloudflare, per il nome host di LibreFolio | Disattiva Rocket Loader (*Speed › Optimization*), Email Address Obfuscation (*Scrape Shield*) e la configurazione automatica di Web Analytics (*Analytics & Logs › Web Analytics*). Una *Configuration Rule* lo fa solo per quel host e lascia gli altri tuoi siti come sono. I nomi dei menu cambiano di tanto in tanto. |
| **Nginx**: un `sub_filter` che scrive uno `<script>` nelle pagine | La configurazione di Nginx, nel `server` o nel `location` che fa da proxy a LibreFolio | Rimuovi quel `sub_filter`. |
| **Un'estensione del browser** che aggiunge uno script proprio a ogni pagina | Il browser | Disattivala per l'indirizzo di LibreFolio, oppure prova la pagina in una finestra privata, che di solito funziona senza estensioni. |

Poi ricarica la pagina: la riga sparisce dalla console. L'avviso nella scheda Sicurezza resta finché non chiudi quella
scheda del browser.

#### 🔗 Un indirizzo pubblico che non può essere usato {: #csp-public-url }

`LIBREFOLIO_PUBLIC_URL` aggiunge la sua origine (`scheme://host`, con la porta solo quando non è quella predefinita) a
`connect-src`. Un valore che non può essere usato (senza `http://` o `https://`, o con nome utente o password) non
aggiunge nulla: il server si avvia e serve come al solito, e il log ha l'avviso *LIBREFOLIO_PUBLIC_URL cannot be used*.

Correggi il valore in **`.env`** ([Account e registrazioni](configuration_accounts.md#accounts)).
Riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`.

#### 📡 Il controllo dell'indirizzo di un link di condivisione {: #csp-address-check }

Il campo **Indirizzo del server** nei dialoghi di invito e reimpostazione della password della scheda
[Utenti](users.md#server-address) non chiede dati all'indirizzo: la policy lo impedirebbe. Carica una piccola immagine
trasparente dall'indirizzo digitato, `/api/v1/auth/address-probe.png`, consentita dalla policy, e ne legge la
dimensione: una dimensione dice che **questa** istanza risponde lì, un'altra che risponde qualcos'altro. I messaggi
dicono le stesse cose di prima.

### 🖼️ Protezione dei frame {: #frame-protection }

Decide se una pagina a **un altro indirizzo** può mostrare LibreFolio in un frame. Un altro indirizzo è un altro nome
host, o lo stesso su un'altra porta: una dashboard di Home Assistant su `http://homeassistant.local:8123` che mostra
LibreFolio da `http://homeassistant.local:6040`.

| `LIBREFOLIO_FRAME_PROTECTION` | Effetto |
| --- | --- |
| `false`, il predefinito su un'installazione tua | Qualsiasi pagina può mostrare LibreFolio in un frame. |
| `true` | Solo le pagine di LibreFolio stesso possono mostrarlo in un frame; ovunque altro, il browser rifiuta di visualizzarlo. |

**Quando attivarla:** su un'installazione tua, lascia spento se una tua pagina mostra LibreFolio in un frame, come una
dashboard di Home Assistant: con l'interruttore attivo, il browser rifiuterebbe di mostrarlo lì. Se nessuna delle tue
pagine lo fa, attivala: nessun altro sito potrà mostrare LibreFolio dentro le proprie pagine.

1. **Nel file `.env`**, aggiungi:

    ```env
    LIBREFOLIO_FRAME_PROTECTION=true
    ```

2. Riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`.
   Ogni risposta porta ora `X-Frame-Options: SAMEORIGIN` e `Content-Security-Policy: frame-ancestors 'self'`, la
   stessa regola nell'header più vecchio e in quello più nuovo.

Con l'interruttore attivo:

- lo stesso `Content-Security-Policy` porta anche le tre regole che [LibreFolio applica alle sue pagine](#csp) in
  ogni profilo (`object-src 'none'`, `base-uri 'self'`, `form-action 'self'`): non dipendono da questo interruttore.
  Un PDF conserva solo `frame-ancestors 'self'`, così che il browser possa ancora mostrarlo;
- una risposta `304 Not Modified` riceve solo `X-Frame-Options`, così che il browser mantenga la policy della copia
  che già ha.

È il controllo `platform.frame_protection` dei [controlli all'avvio](#startup-checks). Passa sempre, e il log non ne
dice nulla; **Impostazioni › Amministrazione › Sicurezza** lo elenca tra i
[controlli superati](settings.md#security-passed):

| Interruttore | La scheda dice |
| --- | --- |
| Attivo | *Solo le pagine di LibreFolio stesso possono mostrarlo in un frame.* |
| Spento, su un'installazione propria | *Pagine a un altro indirizzo, come le tue dashboard, possono mostrare LibreFolio in un frame: il valore predefinito di un'installazione propria.* |

### 📋 La policy di sola segnalazione {: #csp-report-only }

`LIBREFOLIO_CSP_REPORT_ONLY` aggiunge alle pagine della web app una seconda policy, **più ampia** della
[Content-Security-Policy](#csp) applicata: dice anche da dove una pagina può caricare immagini, stili, font e frame.
È di sola segnalazione: il browser non blocca nulla ed elenca ciò che ne resta fuori nella sua console per
sviluppatori, e da nessun'altra parte. La policy applicata resta attiva qualunque sia il valore.

| `LIBREFOLIO_CSP_REPORT_ONLY` | Effetto |
| --- | --- |
| `false`, il predefinito su un'installazione tua | Nessuna policy di sola segnalazione. |
| `true` | Le pagine della web app portano `Content-Security-Policy-Report-Only`. |

**Quando attivarla:** su un'installazione tua non serve: i tuoi utenti non vedono alcuna differenza. Attivala per
vedere, nella console per sviluppatori del browser, cosa bloccherebbe una policy di questo tipo sulla tua istanza.

1. **Nel file `.env`**, aggiungi:

    ```env
    LIBREFOLIO_CSP_REPORT_ONLY=true
    ```

2. Riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`.
   Le pagine della web app portano ora l'header `Content-Security-Policy-Report-Only`.

Con l'interruttore attivo:

- non lo portano la documentazione (`/mkdocs`), tutto sotto `/api/` comprese le pagine di documentazione dell'API, i
  file caricati dalle pagine, né una risposta `304 Not Modified`;
- la policy consente ciò che proviene dall'indirizzo di LibreFolio stesso e alcune eccezioni di cui l'app ha bisogno:
  immagini da qualsiasi indirizzo `https://` (le icone di asset e broker sono un link), stili inline e il WebAssembly
  del visualizzatore PDF. Per gli sviluppatori, direttiva per direttiva:
  [La Content-Security-Policy e la protezione dei frame](../developer/architecture/security.md#managed-headers);
- gli script inline della web app sono consentiti dai loro hash, come nella policy applicata: dopo aver ricostruito la
  web app dai sorgenti, non devi riavviare LibreFolio;
- ogni riga che questa policy aggiunge alla console dice cosa **avrebbe** bloccato: nulla è stato bloccato. Uno script
  che la policy applicata blocca ha una sua riga: [Uno script che non hai inviato](#csp-blocked-script).

È il controllo `platform.csp_report_only` dei [controlli all'avvio](#startup-checks). Passa sempre, e il log non ne
dice nulla; **Impostazioni › Amministrazione › Sicurezza** lo elenca tra i
[controlli superati](settings.md#security-passed):

| Interruttore | La scheda dice |
| --- | --- |
| Attivo | Una riga che dice che le pagine della web app portano una policy di sola segnalazione. |
| Spento, su un'installazione propria | *Nessuna Content-Security-Policy di sola segnalazione: il valore predefinito di un'installazione propria.* |

---

## ⏹️ Arresto del server {: #shutdown }

Quando gli viene chiesto di fermarsi, il server deve farlo entro il **budget di arresto**: 8 secondi se non lo cambi,
contati dal segnale (SIGTERM da `docker stop`, `docker compose down` o un riavvio; SIGINT da Ctrl+C).

**Dove:** nel **file `.env`**.

| Variabile | Predefinito | Cosa fa |
| --- | --- | --- |
| `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS` | `8` | Il budget di arresto, in secondi: un intero da `2` a `600`, oppure `0` per nessun limite, come prima della release 1.3. Un valore che non può essere usato non ferma il server, a differenza delle [opzioni principali](configuration.md#main-options): il log dice `Shutdown budget setting cannot be used: the default applies`, e il budget resta a 8 secondi. |
| `UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN` | 3/8 del budget | Quanti secondi uvicorn, il web server, attende le richieste in corso: `3` con il budget predefinito. L'immagine Docker e `./dev.py server` lo calcolano dal budget. Un valore tuo ha la precedenza: tienilo sotto il budget, che conta comunque per l'intero arresto. |

Il budget viene speso in questo ordine:

1. **Richieste in corso**: il web server non ne accetta di nuove e concede a quelle in esecuzione 3/8 del budget, 3
   secondi per impostazione predefinita. Poi interrompe quelle ancora in corso, come un lungo import da un broker: ciò
   che non avevano ancora salvato torna allo stato precedente (rollback), e si ripetono quando LibreFolio è di nuovo
   attivo.
2. **Il lavoro del server stesso**: sincronizzazioni pianificate, processi worker, cache… si fermano uno dopo l'altro,
   ciascuno entro il tempo rimasto. L'ultimo passo termina i processi figli ancora in esecuzione (import da broker,
   simulazioni di rischio, Strumenti): nessuno sopravvive al server.
3. **Budget esaurito**: se qualcosa trattiene ancora il server, termina comunque con stato di uscita 1, e il log dice
   cosa era ancora in esecuzione: `Shutdown budget exhausted: ending the process`.

!!! warning "🐳 Dai al container più tempo del budget"

    Docker dà a un container 10 secondi per fermarsi, poi lo uccide: il budget predefinito di 8 secondi va bene.
    Se alzi `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS`, dai al container almeno 2 secondi in più, altrimenti Docker uccide
    il server dopo 10 secondi, qualunque sia il suo budget.

    **In `docker-compose.yml`**, sul servizio `librefolio`, lascia il resto com'è e aggiungi:

    ```yaml
    services:
      librefolio:
        stop_grace_period: 32s  # for LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS=30
    ```

    Poi esegui `docker compose up -d`.

`./dev.py server` mantiene quel margine da solo: dopo un Ctrl+C attende fino al budget più 2 secondi, poi termina il
server ([Avvia il server](cli_tools.md#start-the-server)).

---

## 🔗 Correlati

- 📄 **[Configurazione](configuration.md)** — Crea il file `.env`, Opzioni principali, Parametri impostati dagli strumenti, …
- 📄 **[Configurazione: secret e impostazioni dei plugin](configuration_secrets.md)** — Secret, Impostazioni dei plugin
- 📄 **[Configurazione: account e ricerca di asset](configuration_accounts.md)** — Account e registrazioni, L'ordine dei provider dei prezzi nella ricerca, Opzionale: ricerca web per nuovi asset
- 📄 **[Impostazioni globali](settings.md#security-tab)** — La scheda Sicurezza
