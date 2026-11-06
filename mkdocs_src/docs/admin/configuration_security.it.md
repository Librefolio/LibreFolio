# 🛡️ Configurazione: controlli e protezioni

Questa pagina illustra cosa controlla LibreFolio nella propria configurazione quando si avvia, cosa significa ogni
riscontro e cosa fare, le protezioni che richiede al browser (la **Content-Security-Policy** e
la protezione dei frame) e come si arresta.

Le opzioni esaminate da questi controlli sono spiegate in [Configurazione](configuration.md), la
prima pagina della guida, e i secret che menzionano in
[Configurazione: secret e impostazioni dei plugin](configuration_secrets.md).

---

## 🩺 Controlli all'avvio {: #startup-checks }

Subito dopo la sua riga `Starting LibreFolio`, il server controlla la sua configurazione. Non modifica nulla:
ogni riscontro è una riga del log, al livello corrispondente, con il nome del controllo in `check`, come
`platform.jwt_secret`.

Gli stessi controlli, su richiesta, sono nella scheda **Sicurezza** di **Impostazioni › Amministrazione**, per
gli amministratori: formulati nella lingua dell'app, con errori e avvisi conteggiati da un numero sulla
scheda, e vengono riletti con **Controlla di nuovo** dopo aver corretto la configurazione e riavviato il server (vedi
«Sicurezza» in [Impostazioni globali](settings.md)).

| Livello | Il log dice | Cosa fare |
| --- | --- | --- |
| ℹ️ `info` | `The session key is random: every restart signs everyone out. To stay signed in, set JWT_SECRET.` | Nessuna azione, se disconnettere tutti a ogni riavvio va bene. Altrimenti vedi [Mantieni gli utenti connessi](index.md#session-persistence). |
| ⚠️ `warning` | `The session signing key from JWT_SECRET is … characters long: use at least 32 random characters` (o `from JWT_SECRET_FILE (<path>)`) | Genera una chiave più lunga, come in [Mantieni gli utenti connessi](index.md#session-persistence), e mettila dove indica la riga. |
| ⚠️ `warning` | `Set both directly and through a *_FILE variable: …` | Per ogni secret elencato, tieni solo una delle due: la variabile stessa ha la precedenza, il file viene ignorato. |
| ❌ `error` | `The instance key cannot be used: …`, che termina con `cannot be reached (Permission denied)` o `cannot be read (…)` | La cartella `secrets/` o `instance.key` appartiene a un altro utente, oppure i suoi permessi impediscono a LibreFolio di accedervi. Restituisci la proprietà di entrambi all'utente che esegue LibreFolio (`chown`), poi `chmod 700` sulla cartella e `chmod 600` sul file. Non sostituire mai la chiave con una nuova. Il server si avvia comunque. |
| ❌ `error` | `The instance key cannot be used: …`, che termina con un altro motivo, come `is empty or blank` | `instance.key` è danneggiata: ripristinala da un backup, non sostituirla mai con una chiave nuova. Il server si avvia comunque. |
| ⚠️ `warning` | `… is open to other users (…): the folder should be 0700 and the file 0600` | Limita i permessi: `chmod 700` sulla cartella `secrets/`, `chmod 600` su `instance.key`. |
| ⚠️ `warning` | `SESSION_COOKIE_SECURE=never: the session cookie is sent over plain HTTP too; prefer auto` | Torna a `auto` a meno che tu non abbia davvero bisogno di `never`: vedi [HTTPS e reverse proxy](configuration.md). |
| ℹ️ `info` | `The log level is DEBUG: the log records operational detail; …` (o `TRACE`) | Torna a `INFO` quando hai finito di risolvere i problemi. |
| ❌ `error` | `LIBREFOLIO_TEST_MODE is on outside a test lane: test-only providers are served, the data are kept in the test data directory <path> and .env is not read; unset it on a production instance` (`check` è `platform.test_mode`) | La modalità test serve alle esecuzioni di test di LibreFolio stesso (`./dev.py test`, `./dev.py server --test`), che la attivano e disattivano da sole: rimuovi `LIBREFOLIO_TEST_MODE` dall'ambiente del server, oppure impostalo a `0`, poi riavvia: cerca da dove proviene l'ambiente del server, per esempio da un'unità di servizio. Fino ad allora il server lavora sulla cartella che la riga nomina invece che sulla tua [cartella dei dati](filesystem.md): ciò che viene inserito nel frattempo viene salvato lì, non insieme ai tuoi dati. |
| ❌ `error` | `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB cannot be used: expected a whole number of megabytes, 0 for no limit; restore uploads answer 503 until it is fixed` (`check` è `backup.upload_limit`) | Scrivi un numero intero di megabyte, `0` per nessun limite, oppure rimuovi la variabile, poi riavvia ([Il limite di upload di un ripristino](backup_restore.md#restore-upload-limit)). Fino ad allora Impostazioni › Amministrazione › Backup non può caricare un archivio da ripristinare; la riga di comando ne ripristina comunque uno. Il server si avvia comunque. |
| ❌ `error` | `LIBREFOLIO_BACKUP_MAX_RESTORE_MB cannot be used: expected a whole number of megabytes, 0 for no limit; restore checks answer 503 until it is fixed` (`check` è `backup.restore_limit`) | Scrivi un numero intero di megabyte, `0` per nessun limite, nella variabile che la riga nomina, oppure rimuovila, poi riavvia ([Il limite di upload di un ripristino](backup_restore.md#restore-upload-limit)). Fino ad allora ogni controllo di un ripristino viene rifiutato con `backup_restore_unavailable`, da Impostazioni › Amministrazione › Backup e dalla riga di comando, dove `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` davanti a `backup restore` rimuove il limite per quel comando. Il server si avvia comunque. |
| ❌ `error` | `LIBREFOLIO_BACKUP_RECIPIENTS: item 2 is not an age recipient: …; the hosting panel's backups answer 503 until it is fixed` (o `expected at most 2 recipients`, `repeats an earlier recipient`) (`check` è `backup.recipients`) | Scrivi una o due chiavi pubbliche `age1…`, separate da virgole, come le fornisce `backup keygen`, poi riavvia ([Backup sigillati](backup_sealed.md#sealed)). Il server si avvia comunque. |
| ⚠️ `warning` | `LIBREFOLIO_LOGIN_LIMIT=off: failed sign-ins are not limited; turn it back on unless this is a test instance` (`check` è `accounts.login_limit`) | Nessuna azione, su un'istanza destinata ai test. Altrimenti rimuovi la variabile, oppure impostala a `on`, poi riavvia: vedi [Accessi falliti](configuration_accounts.md#login-limit). |
| ❌ `error` | `LIBREFOLIO_SMTP_… cannot be used (SMTP_…): email stays off until it is fixed` (`check` è `email.smtp`) | È disattivata solo l'email, nient'altro: correggi la variabile che la riga nomina, poi riavvia. Cosa significa ogni codice: [Problemi di configurazione](email_troubleshooting.md#configuration-problems). Il server si avvia comunque. |
| ⚠️ `warning` | `LIBREFOLIO_SMTP_TLS=none with …: emails, their links and the SMTP password travel unencrypted; use starttls or tls` | Imposta `LIBREFOLIO_SMTP_TLS` su `starttls` o `tls`, oppure invia tramite un relay sulla tua rete: vedi [Note di sicurezza](email_troubleshooting.md#security). |
| ℹ️ `info` | `LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out` (`check` è `email.links`) | Nessuna azione, se nessun link deve uscire via email. Altrimenti imposta `LIBREFOLIO_PUBLIC_URL` sull'indirizzo a cui i tuoi utenti aprono LibreFolio ([Account e registrazioni](configuration_accounts.md#accounts)), poi riavvia: vedi [Email](email.md). |
| ⚠️ `warning` | `LIBREFOLIO_PUBLIC_URL cannot start a link (it needs http:// or https:// and a host, with no user name, password, ? or #): no email with a link (forgotten password, invitation, reset) can go out` (`check` è `email.links`) | Scrivi l'indirizzo con `http://` o `https://` e un nome host, senza nome utente, password, `?` o `#`, come `https://librefolio.example.com`, poi riavvia: vedi [Email](email.md). |
| ❌ `error` | `Stored plugin secrets that the instance key cannot read: <N>. Enter them again in the plugin settings, or restore the instance key they were saved with` (`check` è `platform.plugin_secrets`; questo compare più avanti nell'avvio, dopo che il database è pronto) | La chiave dell'istanza è cambiata dopo che questi [secret dei plugin](configuration_secrets.md#plugin-secrets) a livello di istanza sono stati salvati: una `secrets/instance.key` persa che LibreFolio ha sostituito con una nuova, dati ripristinati senza la relativa `secrets/`, o un'altra `LIBREFOLIO_INSTANCE_KEY`. Se hai ancora la vecchia chiave (la tua copia di `secrets/instance.key`, salvata insieme alla cartella dei dati come dice [La chiave dell'istanza](configuration_secrets.md#instance-key), dato che un archivio in chiaro creato con **Esegui il backup dell'istanza** lascia fuori la chiave, mentre uno [sicuro](backup_restore.md#secure) porta con sé la chiave generata da LibreFolio e il suo ripristino ricifra questi secret; oppure il vecchio valore della variabile), ferma LibreFolio, mettila al posto della nuova e avvia di nuovo. Fallo prima che qualcuno inserisca di nuovo un secret: un secret inserito di nuovo viene salvato sotto la nuova chiave e diventa illeggibile una volta che la vecchia chiave è tornata in uso. Solo se la vecchia chiave è andata persa, inserisci di nuovo i secret in **Impostazioni › Plugin**: da quel momento, la chiave da salvare è quella nuova. Se il log dice anche `The instance key cannot be used: …`, correggi prima quello: vedi sopra. I secret personali non sono conteggiati: ogni utente vede i propri nella propria scheda. Il server si avvia comunque. |

Alcuni secret che hai configurato bloccano invece l'avvio quando non possono essere usati: un
`JWT_SECRET_FILE` o un `LIBREFOLIO_INSTANCE_KEY_FILE` che non riesce a fornire il proprio secret (vedi
[Secret nei file](configuration_secrets.md#secret-files)),
oppure una chiave dell'istanza fornita da te più corta di 32 caratteri. L'errore è nell'output della console
del server (`docker compose logs librefolio` con Docker): nomina la variabile e, quando esiste, il file, mai il secret. Correggi il problema, poi avvia
di nuovo.

Lo stesso vale per un `LIBREFOLIO_LOGIN_LIMIT` diverso da `on` o `off`
([Accessi falliti](configuration_accounts.md#login-limit)).

---

## 🛡️ Protezioni del browser {: #browser-protections }

Ogni risposta di LibreFolio porta header che dicono al browser come proteggere le sue pagine. Tre
ci sono sempre, senza nulla da impostare:

- `X-Content-Type-Options: nosniff`: il browser usa il tipo che LibreFolio invia e non ne indovina mai
  un altro, così un file caricato non viene mai eseguito come script né mostrato come pagina.
- `Referrer-Policy: strict-origin-when-cross-origin`: un altro sito apprende al massimo l'indirizzo di
  LibreFolio, come `https://librefolio.example.com`, mai la pagina da cui è venuta una richiesta.
- Una `Content-Security-Policy` su ogni pagina, in ogni profilo, senza alcun interruttore per disattivarla: vedi
  [La Content-Security-Policy](#csp).

Altre due sono interruttori, ciascuno impostato per conto proprio, spenti su un'installazione tua:
[Protezione dei frame](#frame-protection) e
[La policy di sola segnalazione](#csp-report-only). LibreFolio legge entrambi all'avvio: riavvialo dopo una modifica. Per
gli sviluppatori: [Header delle risposte](../developer/architecture/security.md#response-headers).

### 🛡️ La Content-Security-Policy {: #csp }

Una Content-Security-Policy dice al browser cosa può eseguire una pagina e a cosa può connettersi.
LibreFolio ne **applica sempre** una, in ogni profilo: non c'è alcuna impostazione per disattivarla. È tenuta
quanto più stretta possibile mentre LibreFolio funziona come ha sempre fatto, e ampliata solo dove LibreFolio
ne ha davvero bisogno. Nel caso usuale non ti chiede nulla: diventa rilevante solo quando qualcosa tra
LibreFolio e il browser aggiunge uno script alla pagina ([Uno script che non hai inviato](#csp-blocked-script)).

| Cosa | Policy | Perché |
|---|---|---|
| Ogni pagina di LibreFolio: la web app, la documentazione (`/mkdocs`) e, dove sono attive, le pagine proprie dell'API a `/api/v1/docs` e `/api/v1/redoc` | `object-src 'none'; base-uri 'self'; form-action 'self'` | Nessun contenuto plugin (`<object>`, `<embed>`); nessun elemento `<base>` che invii i link della pagina a un altro sito; nessun form che invii i suoi dati a un altro sito. LibreFolio non ne usa nessuno. Un PDF non è una pagina: non ne contiene nessuna |
| Le pagine della web app | `script-src`: solo gli script di LibreFolio stesso. I suoi script inline sono consentiti dal loro hash, che LibreFolio calcola dai file della web app, così uno script scritto nella pagina da chiunque altro non viene eseguito | Uno script che LibreFolio non ha inviato è il modo in cui una pagina viene dirottata |
| Le pagine della web app | `worker-src 'self' blob:` | I worker del visualizzatore PDF |
| Le pagine proprie dell'API a `/api/v1/docs` e `/api/v1/redoc`, solo dove `LIBREFOLIO_API_DOCS` è attivo | `script-src 'self' https://cdn.jsdelivr.net`, `worker-src 'self' blob:`, `connect-src 'self'` | Le due pagine sono proprie di LibreFolio, non di FastAPI: caricano Swagger UI e ReDoc da `cdn.jsdelivr.net` a una versione specifica, e il browser rifiuta un file il cui checksum (Subresource Integrity) non è quello che LibreFolio si aspetta. I loro script di avvio provengono dalla tua istanza, quindi le pagine non contengono script inline, e non usano Google Fonts. Il worker è la ricerca di ReDoc. Dove le pagine sono disattivate, nulla di tutto questo esiste |
| Gli script della build della web app, i file sotto `/_app/` | `script-src 'self'`, lo stesso `connect-src` delle pagine, `worker-src 'self' blob:`, `object-src 'none'`, `base-uri 'self'` | Una policy per il caso in cui un browser esegua uno di questi file come **worker**: può caricare gli script di LibreFolio e nient'altro, e connettersi solo dove possono le pagine. Un browser la ignora su qualsiasi script che non sia un worker. Oggi l'unico worker avviato da un file è quello che elabora i prezzi; il worker del visualizzatore PDF parte da un `blob:` e mantiene la policy della pagina |
| Le pagine della web app | `connect-src 'self'`, l'origine di [`LIBREFOLIO_PUBLIC_URL`](configuration_accounts.md#accounts) quando è impostata, e `https://api.github.com` solo su un'installazione self-hosted | Dove la pagina può inviare richieste. L'indirizzo pubblico è quello che indichi agli utenti di LibreFolio come indirizzo di accesso; GitHub serve a verificare se è disponibile una nuova release, verifica che il tuo browser effettua quando un amministratore accede (il profilo `managed` non la effettua mai) |
| Ogni risposta, con la [Protezione dei frame](#frame-protection) attiva | `frame-ancestors 'self'` | Solo le pagine di LibreFolio stesso possono mostrarla in un frame |

**L'anteprima PDF non chiede nulla a terze parti.** Il motore del visualizzatore è una copia propria di LibreFolio, e `connect-src` resta limitato all'indirizzo di LibreFolio stesso. Se quella copia non è raggiungibile, l'anteprima mostra invece il visualizzatore PDF del tuo browser. Il testo cinese, giapponese e coreano è l'unica cosa che il visualizzatore scarica, e la scarica dalla tua istanza, non da terze parti: quando un PDF richiede un font di questo tipo, la pagina lo chiede a LibreFolio (`/api/v1/files/pdf-fonts/…`, solo per utenti autenticati). La prima volta, **il server** scarica il file da `cdn.jsdelivr.net` (un indirizzo fisso, a una versione fissa), lo conserva solo se il suo checksum (sha256) corrisponde all'elenco fornito con LibreFolio, e lo memorizza in `cache/pdf-fonts/` dentro la [cartella dei dati](filesystem.md). È sicuro eliminare quella cartella: i font vengono scaricati di nuovo quando un PDF ne ha bisogno, e non fa parte di un backup. Un'istanza che non riesce a raggiungere `cdn.jsdelivr.net` mostra un PDF di questo tipo senza quei caratteri; un file che non corrisponde all'elenco viene scartato, e il log ha un avviso che lo nomina.

Ciò che la policy **non** applica: `default-src`, `style-src`, `img-src`, `font-src` e
`frame-src`. Immagini (le icone di asset e broker sono impostate tramite un link a qualsiasi indirizzo), stili,
font e frame restano liberi; se un'altra pagina può mostrare LibreFolio in un frame lo decide
solo `LIBREFOLIO_FRAME_PROTECTION`, dato che mostrare LibreFolio dentro una dashboard è un uso legittimo
di un'installazione propria.

Nulla cambia per ciò che LibreFolio fa da sé. Quando ricostruisci la web app dai sorgenti
mentre LibreFolio è in esecuzione, gli hash seguono la nuova build: non devi riavviarlo.

#### 🕵️ Uno script che non hai inviato {: #csp-blocked-script }

Un proxy, un CDN o un'estensione del browser che **aggiunge uno script** alle pagine di LibreFolio viene
bloccato, come qualsiasi altra cosa che LibreFolio non ha inviato. Casi tipici:

- Il **Rocket Loader** di Cloudflare, la sua **Email Address Obfuscation** e la configurazione automatica del suo
  **Web Analytics**, che riscrivono la pagina o vi aggiungono uno script mentre passa;
- un `sub_filter` di Nginx che scrive uno `<script>` nelle pagine;
- un'estensione del browser che aggiunge uno script proprio a ogni pagina.

Cosa vedi:

- la pagina funziona, ma può perdere il pezzo che quello script forniva: un contatore, un indirizzo offuscato, un
  widget dell'estensione;
- la console del browser mostra, una volta per caricamento della pagina, `LibreFolio blocked a script it did not send
  (<source>): a proxy, a CDN or a browser extension adds it. Guide:
  https://<your address>/mkdocs/admin/configuration_security/#csp`, dove `<source>` è l'indirizzo da cui è venuto lo script,
  o `inline` per uno script scritto nella pagina;
- nella scheda [Sicurezza](settings.md) di **Impostazioni › Amministrazione**, il browser
  che l'ha incontrato mostra un avviso, *uno script è stato bloccato*, che nomina le sorgenti. L'avviso appartiene a quella
  scheda del browser, e sparisce quando la scheda si chiude.

Non viene inviato nulla al tuo server: nessun report, nessuna richiesta. La console e la scheda sono gli unici
posti in cui il browser lo segnala.

Cosa fare: **disattiva l'aggiunta per l'indirizzo di LibreFolio**. La policy non viene ampliata tramite
un'impostazione, perché uno script aggiunto in transito è esattamente ciò che questa policy serve a fermare.

- **Cloudflare**: per il nome host di LibreFolio, disattiva Rocket Loader (*Speed › Optimization*), Email
  Address Obfuscation (*Scrape Shield*) e la configurazione automatica di Web Analytics (*Analytics & Logs ›
  Web Analytics*). Una *Configuration Rule* può farlo solo per quel host e lasciare gli altri tuoi siti come
  sono. I nomi dei menu cambiano di tanto in tanto.
- **Nginx**: rimuovi il `sub_filter` che aggiunge lo script dal `server` o dal `location` che
  fa da proxy a LibreFolio.
- **Un'estensione del browser**: disattivala per l'indirizzo di LibreFolio, oppure prova la pagina in una finestra privata,
  che di solito funziona senza estensioni.

Poi ricarica la pagina: la riga sparisce dalla console. L'avviso nella scheda Sicurezza resta finché
non chiudi quella scheda del browser.

#### 🔗 Un indirizzo pubblico che non può essere usato {: #csp-public-url }

`LIBREFOLIO_PUBLIC_URL` aggiunge la sua origine (`scheme://host`, con la porta solo quando non è quella
predefinita) a `connect-src`. Un valore che non può essere usato, come uno senza `http://` o
`https://`, o con un nome utente o una password, non aggiunge nulla: il server si avvia e serve come al solito,
e il log ha un avviso, *LIBREFOLIO_PUBLIC_URL cannot be used*. Correggi il valore, poi riavvia: vedi
[Account e registrazioni](configuration_accounts.md#accounts).

#### 📡 Il controllo dell'indirizzo di un link di condivisione {: #csp-address-check }

Il controllo del campo **Indirizzo del server** nei dialoghi di invito e reimpostazione della password della
scheda [Utenti](users.md#server-address) non chiede più dati all'indirizzo: la policy impedirebbe alla pagina di farlo.
Carica invece una piccola immagine trasparente dall'indirizzo che hai digitato,
`/api/v1/auth/address-probe.png`, che la policy consente, e ne legge la dimensione: una dimensione dice che
**questa** istanza risponde lì, un'altra che a rispondere è qualcos'altro. I messaggi dicono le stesse cose di prima.

### 🖼️ Protezione dei frame {: #frame-protection }

`LIBREFOLIO_FRAME_PROTECTION` decide se una pagina a un altro indirizzo può mostrare LibreFolio in un
frame. Un altro indirizzo è un altro nome host, o lo stesso su un'altra porta: una dashboard di Home Assistant
su `http://homeassistant.local:8123` che mostra LibreFolio da
`http://homeassistant.local:6040` è una pagina a un altro indirizzo.

- **Off** (`false`), il valore predefinito su un'installazione tua: qualsiasi pagina può mostrare LibreFolio in un frame.
- **On** (`true`): solo le pagine di LibreFolio stesso possono mostrarlo in
  un frame. Ovunque altro, il browser rifiuta di visualizzarlo.

Con l'interruttore attivo:

- ogni risposta porta `X-Frame-Options: SAMEORIGIN` e
  `Content-Security-Policy: frame-ancestors 'self'`, la stessa regola nell'header più vecchio e in quello
  più nuovo;
- lo stesso campo `Content-Security-Policy` porta anche le tre regole che
  [LibreFolio applica alle sue pagine](#csp) in ogni profilo: `object-src 'none'`,
  `base-uri 'self'` e `form-action 'self'`. Non dipendono da questo interruttore. Un PDF conserva
  solo `frame-ancestors 'self'`, così che il browser possa ancora mostrarlo;
- una risposta `304 Not Modified` riceve solo `X-Frame-Options`, così che il browser mantenga la policy della
  copia che già ha.

Quando cambiarlo:

- **Su un'installazione tua**, lascialo spento se una tua pagina mostra LibreFolio in un frame, come
  una dashboard di Home Assistant: con l'interruttore attivo, il browser rifiuterebbe di mostrare LibreFolio
  lì. Se nessuna delle tue pagine lo fa, puoi attivarlo, così che nessun altro sito possa mostrare LibreFolio
  dentro le proprie pagine.

È il controllo `platform.frame_protection` dei [controlli all'avvio](#startup-checks), presente anche nella
scheda [Sicurezza](settings.md) di **Impostazioni › Amministrazione**:

- Il controllo passa, e il log non ne dice nulla. La scheda lo elenca tra i
  [controlli superati](settings.md): *Solo le pagine di LibreFolio stesso possono mostrarlo in un
  frame.* con l'interruttore attivo, *Pagine a un altro indirizzo, come le tue dashboard, possono mostrare
  LibreFolio in un frame: il valore predefinito di un'installazione propria.* con l'interruttore spento su un'installazione
  propria.

### 📋 La policy di sola segnalazione {: #csp-report-only }

La [Content-Security-Policy](#csp) che LibreFolio applica è stretta di proposito: lascia liberi immagini,
stili, font e frame. `LIBREFOLIO_CSP_REPORT_ONLY` aggiunge una seconda policy, **più ampia**, alle
pagine della web app: l'intera policy a cui LibreFolio mira, che dice anche da dove una pagina può caricare
le sue immagini, stili, font e frame. È di sola segnalazione: il browser la controlla e non blocca
nulla. Elenca ciò che ne resta fuori nella sua console per sviluppatori, e da nessun'altra parte, dato che la policy
non nomina alcun indirizzo a cui inviare un report. La policy applicata resta attiva qualunque sia il valore di questo interruttore.

- **Off** (`false`), il valore predefinito su un'installazione tua.
- **On** (`true`).

Con l'interruttore attivo:

- le pagine della web app portano un header `Content-Security-Policy-Report-Only`. La documentazione
  (`/mkdocs`), tutto sotto `/api/`, comprese le pagine di documentazione dell'API, e i file caricati dalle
  pagine non lo portano, né lo porta una risposta `304 Not Modified`;
- la policy consente ciò che proviene dall'indirizzo di LibreFolio stesso, e alcune eccezioni di cui l'app ha bisogno,
  come immagini da qualsiasi indirizzo `https://` (le icone di asset e broker sono impostate tramite un link),
  stili inline e il WebAssembly del visualizzatore PDF. Per gli sviluppatori, l'intera policy, direttiva
  per direttiva:
  [La Content-Security-Policy e la protezione dei frame](../developer/architecture/security.md#managed-headers);
- gli script inline della web app sono consentiti dai loro hash, come nella policy applicata,
  che seguono i file della web app: dopo aver ricostruito la web app dai sorgenti, non devi
  riavviare LibreFolio;
- ogni riga che questa policy aggiunge alla console dice cosa avrebbe bloccato: nulla è stato bloccato. Uno script
  che la policy applicata blocca è un'altra cosa, e ha una sua riga: vedi
  [Uno script che non hai inviato](#csp-blocked-script).

Quando cambiarlo:

- **Su un'installazione tua**, non c'è bisogno di attivarla: i tuoi utenti non vedono alcuna differenza
  in un caso o nell'altro. Attivala se vuoi vedere, nella console per sviluppatori del browser, cosa bloccherebbe
  una policy di questo tipo sulla tua istanza.

È il controllo `platform.csp_report_only` dei [controlli all'avvio](#startup-checks), presente anche nella
scheda [Sicurezza](settings.md) di **Impostazioni › Amministrazione**:

- Il controllo passa, e il log non ne dice nulla. La scheda lo elenca tra i
  [controlli superati](settings.md): una riga che dice che le pagine della web app portano una
  policy di sola segnalazione, con l'interruttore attivo, *Nessuna Content-Security-Policy di sola segnalazione: il valore predefinito
  di un'installazione propria.* con l'interruttore spento su un'installazione propria.

---

## ⏹️ Arresto del server {: #shutdown }

Quando al server viene chiesto di fermarsi, deve farlo entro un limite di tempo, il **budget di arresto**:
8 secondi se non lo cambi, contati dal segnale (SIGTERM da `docker stop`,
`docker compose down` o un riavvio; SIGINT da Ctrl+C). Il più delle volte gli utenti non notano nulla,
tranne riavvii più rapidi e più puliti.

| Variabile | Predefinito | Cosa fa |
| --- | --- | --- |
| `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS` | `8` | Il budget di arresto, in secondi: un numero intero da `2` a `600`, oppure `0` per nessun limite, come prima della release 1.3. Un valore che non può essere usato non ferma il server, a differenza delle [opzioni principali](configuration.md): il log dice `Shutdown budget setting cannot be used: the default applies`, e il budget resta a 8 secondi. |
| `UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN` | 3/8 del budget | Quanti secondi uvicorn, il web server, attende le richieste in corso: `3` con il budget predefinito. L'immagine Docker e `./dev.py server` lo calcolano dal budget. Un valore impostato da te ha la precedenza: tienilo sotto il budget, che conta comunque per l'intero arresto. |

Il budget viene speso in questo ordine:

1. **Richieste in corso**: il web server non ne accetta di nuove e concede a quelle già in esecuzione 3/8 del
   budget, 3 secondi per impostazione predefinita. Poi interrompe quelle ancora in corso, come un lungo import
   da un broker: ciò che non avevano ancora salvato viene riportato allo stato precedente (rollback), così possono semplicemente essere ripetute una volta
   che LibreFolio è di nuovo attivo.
2. **Il lavoro del server stesso**: le sincronizzazioni pianificate, i processi worker, le cache… si fermano uno dopo
   l'altro, ciascuno entro il tempo rimasto. L'ultimo passo termina i processi figli ancora in esecuzione
   (import da broker, simulazioni di rischio, Strumenti), così nessuno sopravvive al server.
3. **Quando il budget si esaurisce**: se qualcosa trattiene ancora il server, termina comunque, con stato di uscita
   1, e il suo log dice cosa era ancora in esecuzione: `Shutdown budget exhausted: ending the process`.

!!! warning "🐳 Dai al container più tempo del budget"

    Docker dà a un container 10 secondi per fermarsi per impostazione predefinita, poi lo uccide: il budget predefinito di
    8 secondi va bene. Se alzi `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS`, dai al container almeno
    2 secondi in più: imposta `stop_grace_period` sul servizio `librefolio` di `docker-compose.yml`, lascia
    il resto del servizio com'è, poi esegui `docker compose up -d`.

    ```yaml
    services:
      librefolio:
        stop_grace_period: 32s  # for LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS=30
    ```

    Altrimenti Docker uccide il server dopo 10 secondi, qualunque sia il suo budget.

`./dev.py server` mantiene quel margine da solo: dopo un Ctrl+C attende fino al budget più 2 secondi
per questo arresto, poi termina il server ([Avvia il server](cli_tools.md#start-the-server)).

---

## 🔗 Correlati

- 📄 **[Configurazione](configuration.md)** — Crea il file `.env`, Opzioni principali, Parametri impostati dagli strumenti, …
- 📄 **[Configurazione: secret e impostazioni dei plugin](configuration_secrets.md)** — Secret, Impostazioni dei plugin
- 📄 **[Configurazione: account e ricerca di asset](configuration_accounts.md)** — Account e registrazioni, L'ordine dei provider dei prezzi nella ricerca, Opzionale: ricerca web per nuovi asset
