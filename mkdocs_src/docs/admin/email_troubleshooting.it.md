# 🛠️ Email: quando non funziona

Pagina di diagnosi: le email non partono.
Per ogni errore trovi **cosa vedi**, **perché** e **cosa fare**, con il punto in cui intervieni.

Come configurare l'email e la sua email di test: [Email](email.md).
I messaggi che LibreFolio invia: [Email: link e messaggi](email_flows.md).

---

## 🛠️ Quando non funziona {: #troubleshooting }

Due tipi di problema:

| Cosa vedi | Perché | Dove guardare |
| --- | --- | --- |
| Stato **Non funzionante** appena apri la scheda **Email** | Una variabile che LibreFolio non può usare | [Problemi di configurazione](#configuration-problems) |
| L'errore compare solo quando invii un'email | Il server SMTP rifiuta l'email o non risponde | [Errori di invio](#sending-errors) |

Una configurazione inutilizzabile disattiva solo l'email: il server si avvia come al solito e tutto il resto funziona.

Dove intervieni, nelle tabelle di questa pagina:

| Dove | Cosa | Dopo |
| --- | --- | --- |
| **`.env`** — il file `.env` di LibreFolio ([dove si trova](email.md#where-it-lives)) | Le variabili `LIBREFOLIO_SMTP_…` e `LIBREFOLIO_PUBLIC_URL` | Riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`. |
| **Server SMTP** — il server o il provider | Login, mittenti ammessi, certificato, relay | Riprova l'email di test. |
| **Interfaccia** — **Impostazioni › Amministrazione › Email**, [Profilo](../user/settings/profile.md), [Utenti e inviti](users.md#actions) | Stato, email di test, il tuo indirizzo, gli account | Nessun riavvio. |
| **Log** | La risposta esatta del server e il codice | [Cosa dice il log](#logs): dove si legge. |

### ⚙️ Problemi di configurazione {: #configuration-problems }

**Dove: il file `.env` di LibreFolio.** La scheda **Email** nomina la variabile; il codice è nel log, subito dopo `Starting LibreFolio`.
Dopo ogni correzione: riavvia LibreFolio. Con Docker Compose, esegui `docker compose up -d`.

| Cosa vedi (scheda) | Codice | Perché | Cosa fare |
| --- | --- | --- | --- |
| `LIBREFOLIO_SMTP_HOST` non è un nome server valido… | `SMTP_HOST_INVALID` | Non è solo un nome o un indirizzo IP | `smtp.example.com`, non `smtp://smtp.example.com`, `smtp.example.com:587` o `user@smtp.example.com`. La porta va in `LIBREFOLIO_SMTP_PORT`; un IPv6 senza parentesi quadre. |
| `LIBREFOLIO_SMTP_TLS` deve essere starttls, tls o none. | `SMTP_TLS_INVALID` | Parola non ammessa | Una delle tre. Crittografia dal primo byte, porta 465: `tls`. |
| `LIBREFOLIO_SMTP_PORT` deve essere un numero intero da 1 a 65535. | `SMTP_PORT_INVALID` | Fuori intervallo o non numerico | Solo cifre, oppure togli la riga: vale la porta della modalità. |
| Il file della password indicato da `LIBREFOLIO_SMTP_PASSWORD_FILE` non può essere letto. | `SMTP_PASSWORD_UNREADABLE` | Il file non esiste a quel percorso (con Docker, il percorso dentro il container), l'utente che esegue LibreFolio non può leggerlo, è vuoto o solo spazi, non è UTF-8, o supera 64 KiB | Il log dice quale: sistema file o percorso. |
| `LIBREFOLIO_SMTP_USER` è impostata da sola… (oppure `LIBREFOLIO_SMTP_PASSWORD`) | `SMTP_CREDENTIALS_INCOMPLETE` | Utente senza password o viceversa. Una password da `LIBREFOLIO_SMTP_PASSWORD_FILE` conta come `LIBREFOLIO_SMTP_PASSWORD` | Entrambi, oppure nessuno dei due. |
| `LIBREFOLIO_SMTP_FROM` manca… | `SMTP_FROM_MISSING` | Obbligatorio appena imposti un server | Aggiungi il mittente. |
| `LIBREFOLIO_SMTP_FROM` deve essere un solo indirizzo… | `SMTP_FROM_INVALID` | Elenco o interruzione di riga | Un solo indirizzo, con o senza nome: `LibreFolio <noreply@example.com>`. |
| `LIBREFOLIO_SMTP_REPLY_TO` deve essere un solo indirizzo. | `SMTP_REPLY_TO_INVALID` | Stessa regola del mittente | Un solo indirizzo, oppure togli la riga. |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` deve essere un numero intero almeno pari a 1. | `SMTP_MAX_PER_HOUR_INVALID` | Non è un intero ≥ 1 | Solo cifre, almeno `1`. Per fermare l'invio togli invece `LIBREFOLIO_SMTP_HOST`. |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` deve essere un numero intero almeno pari a 1. | `SIGNUP_EMAILS_PER_ADDRESS_INVALID` | Non è un intero ≥ 1. Come le altre disattiva l'email finché non la correggi; il server si avvia comunque | Solo cifre, almeno `1`, oppure togli la riga: predefinito `20`. |

### 📤 Errori di invio {: #sending-errors }

L'email di test, in **Impostazioni › Amministrazione › Email**, dice perché non è partita.
La risposta esatta del server è nel log ([Cosa dice il log](#logs)).

| Cosa vedi (email di test) | Codice | Perché | Cosa fare — dove |
| --- | --- | --- | --- |
| LibreFolio non riesce a raggiungere il server SMTP… | `CONNECTION_FAILED` | Nome del server, porta o firewall. Il nome vale da dove gira LibreFolio: in un container, `localhost` è il container stesso | **`.env`**: `LIBREFOLIO_SMTP_HOST`, `LIBREFOLIO_SMTP_PORT`. **Rete**: un firewall che rifiuta la connessione. |
| La connessione sicura non è riuscita… | `TLS_FAILED` | Modalità e porta non vanno insieme; con `starttls` il server non offre la crittografia; certificato non valido o non rilasciato per il nome in `LIBREFOLIO_SMTP_HOST` (autofirmato, o un IP al posto del nome, non passa) | **`.env`**: `starttls` con 587, `tls` con 465; in `LIBREFOLIO_SMTP_HOST` il nome del certificato. **Server SMTP**: un certificato valido. |
| Il server SMTP ha rifiutato il login… | `AUTH_FAILED` | Utente o password errati. Un server senza login rifiuta il login | **`.env`**: utente e password; con un provider, una password per l'app. Server senza login: togli entrambi. |
| Il server SMTP ha rifiutato l'indirizzo del mittente… | `SENDER_REFUSED` | Il server accetta solo gli indirizzi con cui il tuo account può inviare. Senza utente, potrebbe richiedere comunque un login | **`.env`**: in `LIBREFOLIO_SMTP_FROM` uno di quegli indirizzi, o aggiungi il login. |
| Il server SMTP ha rifiutato il tuo indirizzo. | `RECIPIENT_REFUSED` | L'email del tuo account. Senza login, un server può rifiutare il relay verso altri domini: la risposta nel log lo dice | **Interfaccia**: il tuo indirizzo in [Profilo](../user/settings/profile.md). **Server SMTP**: il relay. |
| Il server SMTP non ha risposto in tempo. | `TIMEOUT` | Oltre i 20 secondi che LibreFolio attende per ogni passaggio: un firewall che scarta la connessione senza rifiutarla, oppure `starttls` sulla porta 465 | **`.env`**: la coppia modalità/porta. **Rete**: il firewall. |
| Il server SMTP non ha accettato il messaggio. | `SEND_FAILED` | Il server ha rifiutato il messaggio stesso. Lettere non ASCII prima della `@`, come `zoë@example.com`, richiedono SMTPUTF8: senza, l'email non lascia mai LibreFolio e il log riporta `SMTPNotSupportedError` | **Log**: la risposta del server dice perché. **Server SMTP**: SMTPUTF8, oppure un indirizzo ASCII. |
| Il limite orario di … email è raggiunto… (stato), oppure Il limite orario delle email è raggiunto: riprova tra … min. (test) | `EMAIL_RATE_LIMITED` | Massimo dell'ora raggiunto | Attendi i minuti indicati. Per di più, **`.env`**: aumenta `LIBREFOLIO_SMTP_MAX_PER_HOUR` e riavvia. |
| L'email è disattivata o non funzionante su questa istanza. | `EMAIL_UNAVAILABLE` | Configurazione cambiata da quando hai caricato la scheda, per esempio dopo un riavvio | **Interfaccia**: la scheda mostra ora lo stato e il suo problema. |
| L'indirizzo del tuo account non è un indirizzo email valido. | `EMAIL_RECIPIENT_INVALID` | L'email del tuo account | **Interfaccia**: correggila in [Profilo](../user/settings/profile.md). |
| Non è stato possibile inviare l'email di test. | — | Nessuna risposta nota, per esempio un errore di rete | Ricarica la pagina e guarda il **log**. |
| Email di test inviata al tuo indirizzo…, ma non arriva nulla | — | Il server ha accettato: da lì la consegna è compito suo. Un mittente su un dominio che non autorizza quel server può essere rifiutato o finire in spam lungo il percorso | Cartella spam, poi i **log del server o del provider**. |

**Non è stato possibile leggere lo stato dell'email.**: la scheda non ha raggiunto il server. Ricarica; se persiste, guarda il log.

**Invia per email**, nelle finestre di dialogo di invito e reimpostazione, dice perché un link non è partito:

| Cosa vedi (finestra di dialogo) | Codice | Perché | Cosa fare — dove |
| --- | --- | --- | --- |
| L'email è disattivata o non funzionante su questa istanza. | `EMAIL_UNAVAILABLE` | Configurazione cambiata da quando hai aperto la finestra, per esempio dopo un riavvio | **Interfaccia**: [Impostazioni › Amministrazione › Email](email.md#email-tab). |
| Le email non possono contenere link: LIBREFOLIO_PUBLIC_URL non è impostata, oppure non può essere l'inizio di un link. | `EMAIL_LINKS_UNAVAILABLE` | Manca l'inizio dei link | **`.env`**: imposta `LIBREFOLIO_PUBLIC_URL`, poi riavvia ([Email con un link](email_flows.md#public-url)). |
| Questo link non funziona più: crearne uno nuovo. | `EMAIL_LINK_INVALID` | Link scaduto, usato o revocato | **Interfaccia**: crea un nuovo link e invia quello. |
| L'account non è attivo: attivarlo prima di inviargli un link di reimpostazione. | `EMAIL_ACCOUNT_INACTIVE` | Account disattivato | **Interfaccia**: **Riattiva** in [Utenti e inviti](users.md#actions); oppure **riga di comando**: `user activate` ([CLI](cli_tools.md)). Poi invia di nuovo il link. |
| Inserire l'indirizzo a cui inviare l'invito. | `EMAIL_RECIPIENT_REQUIRED` | L'invito non contiene alcun indirizzo | **Interfaccia**: digitane uno in **Invia a**. |
| Non è un singolo indirizzo email valido. | `EMAIL_RECIPIENT_INVALID` | Indirizzo non valido. Per una reimpostazione, è quello dell'account stesso | **Interfaccia**: correggi **Invia a**. Per la reimpostazione, copia invece il link. |
| Il limite orario delle email è raggiunto: riprova tra … min. | `EMAIL_RATE_LIMITED` | Massimo dell'ora raggiunto | Attendi i minuti indicati. Per di più, **`.env`**: aumenta `LIBREFOLIO_SMTP_MAX_PER_HOUR` e riavvia. |
| Il server SMTP ha rifiutato l'indirizzo del destinatario. | `RECIPIENT_REFUSED` | L'indirizzo del link: **Invia a** per un invito, l'email dell'account per una reimpostazione. Senza login, un server può rifiutare il relay verso altri domini | **Interfaccia**: l'indirizzo. **Log**: la risposta del server. **Server SMTP**: il relay. |
| Gli altri messaggi dell'email di test | `CONNECTION_FAILED`, `TLS_FAILED`, `AUTH_FAILED`, … | Come nella tabella sopra | Come nella tabella sopra. |
| Non è stato possibile inviare l'email. | — | Nessuna risposta nota, per esempio un errore di rete | Ricarica la pagina e guarda il **log**. |

`EMAIL_RECIPIENT_NOT_ALLOWED` (un altro indirizzo per un link di reimpostazione) proviene solo dall'API: la finestra di dialogo non lo restituisce mai.

### 📜 Cosa dice il log {: #logs }

**Dove si legge:**

| Installazione | Comando o file |
| --- | --- |
| Docker | `docker compose logs librefolio` |
| Sull'host | `logs/librefolio.log` nella cartella dei dati ([Struttura del filesystem](filesystem.md)); il server lo stampa anche sulla console |

A ogni avvio, subito dopo `Starting LibreFolio`, il server controlla la configurazione, email inclusa ([Controlli all'avvio](configuration_security.md#startup-checks)): configurazione inutilizzabile (le prime due righe sotto), `none` verso un server esterno alla tua rete locale (una riga), `LIBREFOLIO_PUBLIC_URL` mancante o non valido (una riga).
Nessuna ferma l'avvio.
Gli stessi tre controlli sono in **Impostazioni › Amministrazione › Sicurezza**, riletti quando lo richiedi; un risultato rimanda alla [scheda Email](email.md#email-tab) (vedi «Sicurezza» in [Impostazioni globali](settings.md)).

**Avvio e invio**

| Il log dice | Livello | Quando |
| --- | --- | --- |
| `Email configuration cannot be used: email stays off` | `error` | Una variabile non può essere usata. Una volta per processo server, all'avvio, con `variable`, `problem` (il codice) e `reason`: la regola violata, oppure perché il file della password non può essere letto. |
| `LIBREFOLIO_SMTP_… cannot be used (SMTP_…): email stays off until it is fixed` | `error` | All'avvio, dopo la riga sopra, con `check` impostato a `email.smtp`: i controlli all'avvio segnalano lo stesso problema. |
| `LIBREFOLIO_SMTP_TLS=none with …: emails, their links and the SMTP password travel unencrypted; use starttls or tls` | `warning` | All'avvio, con `check` impostato a `email.smtp_encryption`: `none` verso un server esterno alla tua rete locale, che la riga nomina ([Note di sicurezza](#security)). |
| `LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out` | `info` | All'avvio, con `check` impostato a `email.links`: l'email funziona, ma `LIBREFOLIO_PUBLIC_URL` non è impostata ([Email con un link](email_flows.md#public-url)). |
| `LIBREFOLIO_PUBLIC_URL cannot start a link (it needs http:// or https:// and a host, with no user name, password, ? or #): no email with a link (forgotten password, invitation, reset) can go out` | `warning` | All'avvio, con `check` impostato a `email.links`: l'email funziona, ma la variabile non può essere l'inizio di un link ([Email con un link](email_flows.md#public-url)). |
| `Email sent` | `info` | Il server ha accettato un'email; `kind` dice quale: `test`, `invite`, `password_reset`, `email_verification`, `email_changed` o `email_change_confirmation`. |
| `Email not sent` | `warning` | Il server ha rifiutato l'email o non ha risposto: `code`, come in [Errori di invio](#sending-errors), e `detail`, la risposta del server stesso, l'indizio più preciso. |
| `Email not sent: the hourly limit of the instance is reached` | `warning` | Il limite orario ha fermato un'email; `retry_after` è in secondi. |
| `Test email sent by an administrator` | `info` | Un'email di test è partita, con `admin_id` e `language`. |
| `Link emailed by an administrator` | `info` | Un amministratore ha inviato un link via email: `admin_id`, `purpose` (`invite` o `password_reset`), `token_id`, lo `user_id` dell'account per un link di reimpostazione, e `language`. |

**Password dimenticate**

| Il log dice | Livello | Quando |
| --- | --- | --- |
| `Forgotten password: reset link emailed` | `info` | Un link di reimpostazione è partito: `user_id`, `token_id` e `language`. |
| `Forgotten password: no active account matches, nothing sent` | `info` | Nessun account attivo ha quel nome utente o indirizzo email. Ciò che è stato digitato non viene mai registrato. |
| `Forgotten password: the account had a reset link moments ago, nothing sent` | `info` | I limiti dell'account: un link di reimpostazione meno di 5 minuti fa, oppure 3 nell'ultima ora; con `user_id`. |
| `Forgotten password: an administrator's reset link is still live, nothing sent` | `info` | Una richiesta non annulla mai un link dato da un amministratore; con `user_id`. |
| `Forgotten password: the hourly limit of the instance is reached, nothing sent` | `warning` | Il limite orario è stato raggiunto dopo la risposta; con `user_id`. |
| `Forgotten password: the mailbox had reset emails moments ago, nothing sent` | `info` | Quella casella aveva già 3 email di reimpostazione nell'ultima ora, comprese quelle non partite; con `user_id`. |
| `Forgotten password: another request won the race, nothing sent` | `info` | Due richieste per l'account nello stesso momento: l'altra invia l'email; con `user_id`. |
| `Forgotten password: no email sent` | `warning` | L'email o `LIBREFOLIO_PUBLIC_URL` hanno smesso di funzionare dopo la risposta, oppure l'email è stata rifiutata: `reason` e `code` dicono quale. Il link creato viene revocato. |
| `Forgotten password: the request failed` | `error` | Un errore imprevisto, con il suo tipo in `error` e nulla di più: nessun dettaglio della richiesta raggiunge il log. |

Ogni link di reimpostazione lascia anche una riga `Password reset link created`, con `user_id`, `token_id` e, se lo ha creato un amministratore, `created_by_user_id`.

**Verifica email**

| Il log dice | Livello | Quando |
| --- | --- | --- |
| `Registration waits for email verification` | `info` | Un nuovo account attende il suo link; con `user_id`. La riga `User registered` della stessa registrazione ha `waits_for_email` impostato a true. |
| `Verification email held: address limit or instance budget reached` | `info` | L'indirizzo aveva già ricevuto le sue `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` email (20 per impostazione predefinita) nell'ora, oppure il limite orario dell'istanza è esaurito: l'account attende senza la sua email, e la pagina di login lo dice al suo proprietario; con `user_id`. |
| `Verification link emailed` | `info` | Un link di verifica è partito: `user_id`, `token_id` e `language`. |
| `Verification email: not sent` | `warning` | L'email di una registrazione non è partita: `reason` e `code` dicono perché. La pagina aveva detto che l'email era in arrivo: solo questa riga dice che non è partita. L'account attende ancora; il proprietario può richiedere di nuovo il link. |
| `Verification email: the account no longer waits, nothing sent` | `info` | Un amministratore ha attivato, disattivato o eliminato l'account prima che l'email partisse; con `user_id`. |
| `Verification email: the request failed` | `error` | Un errore imprevisto, con il suo tipo in `error` e lo `user_id`, nulla di più. |
| `Login refused: email not verified` | `info` | Un account in attesa ha fatto login con la password corretta; con `user_id`. |
| `Verification resend refused: wrong credentials` | `warning` | Richiesta di un nuovo link di verifica con password errata, o per un account che non esiste. Né ciò che è stato digitato né l'indirizzo vengono registrati. |
| `Email verified` | `info` | Il proprietario ha confermato nella pagina del link: l'account è attivo; `user_id` e `token_id`. |
| `Email verification refused: the link's email did not go out` | `info` | Conferma con un link la cui email LibreFolio ha considerato non inviata: l'account attende ancora, e **Invia di nuovo il link** funziona. |
| `Email verification refused: the link was sent to another address` | `info` | L'indirizzo dell'account è cambiato dopo l'invio del link: quel link smette di funzionare. |

**Cambio di indirizzo email**

| Il log dice | Livello | Quando |
| --- | --- | --- |
| `Email change notice sent to the previous address` | `info` | L'avviso è andato al vecchio indirizzo. La riga ha `user_id` e `language`, nessuno dei due indirizzi. |
| `Email change notice: email is off, nothing sent` | `info` | L'email è disattivata: niente da inviare, nulla di sbagliato. |
| `Email change notice: past its limits, nothing sent` | `info` | L'account, o la vecchia casella, aveva già 3 avvisi nell'ora: il cambio è riuscito, l'avviso no. Con `user_id`. |
| `Email change notice: the account no longer exists, nothing sent` | `info` | L'account è stato eliminato prima che l'email partisse. |
| `Email change notice: not sent` | `warning` | L'email è configurata ma non usabile ora, il limite orario è raggiunto, il vecchio indirizzo non è un singolo indirizzo semplice, oppure l'invio è fallito: `reason` e `code` dicono quale. |
| `Email change notice: the request failed` | `error` | Un errore imprevisto, con il suo tipo in `error` e lo `user_id`, nulla di più. |

Nessuna di queste righe contiene la password SMTP, il contenuto di un'email, un link o la sua parte segreta, ciò che qualcuno ha digitato per chiedere un link di reimpostazione o di verifica, o l'indirizzo completo del destinatario: solo il suo dominio, in `recipient_domain`.
Anche la risposta del server viene mascherata, perché spesso cita l'indirizzo rifiutato: `550 5.1.1 <***@example.com>: Recipient address rejected`.
L'avviso di un cambio di email non nomina né il vecchio indirizzo né quello nuovo.

---

## 🔒 Note di sicurezza {: #security }

- **`starttls` non fa mai fallback sul testo in chiaro.** Un server che non offre la crittografia non riceve né la password né il messaggio: l'email di test fallisce con `TLS_FAILED`.
- **Il certificato viene sempre controllato**, con `starttls` e con `tls`: nessuna opzione lo salta.
- **`none` invia tutto in chiaro**: messaggi, link e password SMTP. Usalo solo per un relay sulla tua macchina o rete. Verso qualsiasi altro server, Impostazioni › Amministrazione › Email mostra un avviso: *Le email, i loro link e la password SMTP viaggiano senza crittografia verso un server esterno alla rete locale*; anche il log di avvio ne contiene uno ([Cosa dice il log](#logs)).
- **Tieni la password in un file segreto** (`LIBREFOLIO_SMTP_PASSWORD_FILE`) che solo l'utente che esegue LibreFolio può leggere, fuori da `.env` e fuori dalla cartella dei dati. Usa una password per l'app, o un account dedicato solo a LibreFolio, che puoi revocare da solo.
- **I link provengono solo da `LIBREFOLIO_PUBLIC_URL`**, mai da una richiesta: nessuno può far inviare da LibreFolio a un tuo utente un link a un sito di terzi ([Email con un link](email_flows.md#public-url)).
- **Un link di verifica va solo all'indirizzo dell'account stesso**, e nessuno lo vede, amministratore compreso. **Invia di nuovo il link** chiede la password dell'account, come il login, e un nuovo link disattiva i precedenti.
- **I nomi restano su una riga.** Nome utente, nome di chi invita e nome dell'istanza vanno in un'email su una riga: caratteri di controllo e interruzioni di riga diventano spazi, i controlli bidirezionali vengono rimossi. Un nome utente creato ad arte non può aggiungere righe a un'email né camuffarne il testo.
- **Nessuna parola di estranei in un'email.** Reimpostazione della password, verifica email e avviso di cambio indirizzo possono essere inviati, da chi non è amministratore, a un indirizzo di sua scelta. Queste email iniziano con un semplice «Ciao,», senza nome utente, e l'avviso non mostra alcuna parte del nuovo indirizzo: LibreFolio non risolve i domini, quindi anche la parte finale di un indirizzo è scelta liberamente. Un link di reimpostazione che invii per email è scritto allo stesso modo; il nome utente appare una volta aperto il link. Solo l'email di test e il link di configurazione dell'amministratore iniziale salutano per nome: li invii tu, o chi gestisce il server.
- **Le password dimenticate non dicono a nessuno quali account esistono**: la stessa risposta per tutti, la ricerca dopo la risposta, e limiti per indirizzo, per nome utente o indirizzo email, per casella di posta e per account ([Password dimenticate](email_flows.md#forgot-password)).
- **Cambiare l'indirizzo email di un account richiede la sua password attuale.** Senza, basterebbe un momento dentro la sessione di qualcuno (un cookie di sessione rubato, un computer lasciato sbloccato) per mettere il proprio indirizzo sull'account e poi reimpostarne la password: la reimpostazione via email esiste solo insieme a questa regola. Quando l'email funziona, anche il vecchio indirizzo riceve un avviso ([Cambi di indirizzo email](email_flows.md#email-change-notice)).
- **Il limite orario** limita ciò che l'istanza può inviare, qualunque cosa accada: aumentalo solo quanto serve.

??? info "🏠 Cosa conta come la tua rete locale — quando compare l'avviso"

    LibreFolio giudica `LIBREFOLIO_SMTP_HOST` così com'è scritto, senza risolvere il nome. Locale significa:

    - `localhost`, oppure un nome senza punto, come un servizio Docker Compose (`smtp-relay`) o una
      macchina della tua LAN;
    - un nome che termina in `.local`, `.lan`, `.home.arpa`, `.internal` o `.localhost`;
    - un indirizzo di loopback, privato o link-local, come `127.0.0.1`, `192.168.1.10` o
      `fd00::25`, oppure un indirizzo Tailscale (`100.64.0.0/10`, `fd7a:115c:a1e0::/48`).

    Qualsiasi altro server riceve l'avviso, anche uno sulla tua rete conosciuto con un nome completo come
    `relay.example.com`. Anche un nome Tailscale come `relay.tailnet.ts.net` lo riceve, mentre il suo
    indirizzo `100.x` no.

---

## 🔗 Correlati

- 📄 **[Email](email.md)** — Dove si trova la configurazione, Le variabili, Esempi, …
- 📄 **[Email: link e messaggi](email_flows.md)** — Email con un link, Link inviati da un amministratore, Password dimenticate, …
