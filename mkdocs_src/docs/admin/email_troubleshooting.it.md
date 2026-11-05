# 🛠️ Email: quando non funziona

Questa pagina riguarda i casi in cui le email non partono: gli errori mostrati dall'email di test e dalle finestre di dialogo,
cosa dice il log e le note di sicurezza della configurazione SMTP.

Come configurare l'email, con la scheda **Email** delle Impostazioni e la sua email di test, è descritto in
[Email](email.md); i messaggi inviati da LibreFolio sono in [Email: link e messaggi](email_flows.md).

---

## 🛠️ Quando non funziona {: #troubleshooting }

I problemi sono di due tipi:

- una variabile che LibreFolio non può usare: lo stato è **Non funzionante** non appena si apre la scheda
  ([Problemi di configurazione](#configuration-problems));
- un server che rifiuta l'email o non risponde: compare solo quando si invia un'email
  ([Errori di invio](#sending-errors)).

Una configurazione che non può essere usata disattiva l'email, nient'altro: il server si avvia come al solito e
tutto il resto funziona. Il log di avvio nomina già la variabile problematica, subito dopo
`Starting LibreFolio`, e lo fa anche la scheda ([Cosa dice il log](#logs)).

### ⚙️ Problemi di configurazione {: #configuration-problems }

La scheda nomina la variabile problematica; il codice è nel log.

| La scheda dice | Codice | Cosa controllare |
| --- | --- | --- |
| `LIBREFOLIO_SMTP_HOST` non è un nome server valido… | `SMTP_HOST_INVALID` | Solo il nome o l'indirizzo IP: `smtp.example.com`, non `smtp://smtp.example.com`, `smtp.example.com:587` o `user@smtp.example.com`. La porta va in `LIBREFOLIO_SMTP_PORT`; un indirizzo IPv6 va senza parentesi quadre. |
| `LIBREFOLIO_SMTP_TLS` deve essere starttls, tls o none. | `SMTP_TLS_INVALID` | Una delle tre parole. Per la crittografia dal primo byte, sulla porta 465, la parola è `tls`. |
| `LIBREFOLIO_SMTP_PORT` deve essere un numero intero da 1 a 65535. | `SMTP_PORT_INVALID` | Solo cifre, oppure nessuna riga per usare la porta della modalità. |
| Il file della password indicato da `LIBREFOLIO_SMTP_PASSWORD_FILE` non può essere letto. | `SMTP_PASSWORD_UNREADABLE` | Il log dice perché: il file non esiste a quel percorso (con Docker, il percorso dentro il container), l'utente che esegue LibreFolio non può leggerlo, oppure è vuoto o contiene solo spazi, non è testo UTF-8 o è più grande di 64 KiB. |
| `LIBREFOLIO_SMTP_USER` è impostata da sola… (oppure `LIBREFOLIO_SMTP_PASSWORD`) | `SMTP_CREDENTIALS_INCOMPLETE` | Impostare sia l'utente sia la password, oppure nessuno dei due. Una password fornita da `LIBREFOLIO_SMTP_PASSWORD_FILE` viene indicata come `LIBREFOLIO_SMTP_PASSWORD`. |
| `LIBREFOLIO_SMTP_FROM` manca… | `SMTP_FROM_MISSING` | Aggiungere il mittente: è obbligatorio non appena viene impostato un server. |
| `LIBREFOLIO_SMTP_FROM` deve essere un solo indirizzo… | `SMTP_FROM_INVALID` | Un solo indirizzo, con o senza nome, come `LibreFolio <noreply@example.com>`: nessun elenco, nessuna interruzione di riga. |
| `LIBREFOLIO_SMTP_REPLY_TO` deve essere un solo indirizzo. | `SMTP_REPLY_TO_INVALID` | La stessa regola del mittente, oppure rimuovere la riga. |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` deve essere un numero intero almeno pari a 1. | `SMTP_MAX_PER_HOUR_INVALID` | Solo cifre, almeno `1`. Per fermare l'invio, rimuovere invece `LIBREFOLIO_SMTP_HOST`. |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` deve essere un numero intero almeno pari a 1. | `SIGNUP_EMAILS_PER_ADDRESS_INVALID` | Solo cifre, almeno `1`, oppure nessuna riga per il valore predefinito di `20`. Come le altre, disattiva l'email finché non viene corretta; il server si avvia comunque. |

### 📤 Errori di invio {: #sending-errors }

L'email di test dice perché non è partita. Per la risposta del server stesso, guardare il log.

| La scheda dice | Codice | Cosa controllare |
| --- | --- | --- |
| LibreFolio non riesce a raggiungere il server SMTP… | `CONNECTION_FAILED` | Il nome del server, come viene visto da dove gira LibreFolio (in un container, `localhost` è il container stesso), la porta e un firewall che rifiuta la connessione. |
| La connessione sicura non è riuscita… | `TLS_FAILED` | La modalità e la porta vanno insieme: `starttls` con 587, `tls` con 465. Con `starttls`, il server deve offrire la crittografia. Il suo certificato deve essere valido e rilasciato per il nome in `LIBREFOLIO_SMTP_HOST`: un certificato autofirmato, o un indirizzo IP al posto del nome, non supera il controllo. |
| Il server SMTP ha rifiutato il login… | `AUTH_FAILED` | L'utente e la password: con un provider, una password per l'app. Un server che accetta posta senza login rifiuta il login: rimuovere l'utente e la password. |
| Il server SMTP ha rifiutato l'indirizzo del mittente… | `SENDER_REFUSED` | Il server accetta solo gli indirizzi con cui il tuo account può inviare: usarne uno in `LIBREFOLIO_SMTP_FROM`. Senza un utente, il server potrebbe richiedere comunque un login. |
| Il server SMTP ha rifiutato il tuo indirizzo. | `RECIPIENT_REFUSED` | L'email del tuo account, in [Profilo](../user/settings/profile.md). Senza login, un server potrebbe rifiutarsi di inoltrare la posta ad altri domini: la sua risposta nel log lo dice. |
| Il server SMTP non ha risposto in tempo. | `TIMEOUT` | LibreFolio attende fino a 20 secondi per ogni passaggio. Un firewall che scarta la connessione senza rifiutarla porta a questo errore, e lo stesso può accadere con `starttls` sulla porta 465. |
| Il server SMTP non ha accettato il messaggio. | `SEND_FAILED` | Il server ha rifiutato il messaggio stesso: la sua risposta nel log dice perché. Un indirizzo con lettere non ASCII prima della `@`, come `zoë@example.com`, richiede un server che supporti SMTPUTF8: senza, l'email non lascia mai LibreFolio e il log riporta `SMTPNotSupportedError`. |
| Il limite orario di … email è raggiunto… (stato), oppure Il limite orario delle email è raggiunto: riprova tra … min. (test) | `EMAIL_RATE_LIMITED` | Attendere i minuti indicati. Per consentirne di più, aumentare `LIBREFOLIO_SMTP_MAX_PER_HOUR` e riavviare. |
| L'email è disattivata o non funzionante su questa istanza. | `EMAIL_UNAVAILABLE` | La configurazione è cambiata da quando è stata caricata la scheda, per esempio dopo un riavvio: ora la scheda mostra lo stato e il suo problema. |
| L'indirizzo del tuo account non è un indirizzo email valido. | `EMAIL_RECIPIENT_INVALID` | Correggere l'email del tuo account in [Profilo](../user/settings/profile.md). |
| Non è stato possibile inviare l'email di test. | — | Non è arrivata alcuna risposta nota, per esempio dopo un errore di rete: ricaricare la pagina e guardare il log. |
| Email di test inviata al tuo indirizzo…, ma non arriva nulla | — | Il server ha accettato il messaggio: da lì in poi, la consegna è compito suo. Controllare la cartella spam, poi i log del server o del tuo provider. Un mittente su un dominio che non consente a quel server di inviare per suo conto può essere rifiutato, o classificato come spam, lungo il percorso. |

**Non è stato possibile leggere lo stato dell'email.** significa che la scheda non è riuscita a raggiungere il server: ricaricare
la pagina e, se il problema persiste, guardare il log.

**Invia per email**, nelle finestre di dialogo di invito e reimpostazione, dice perché un link non è partito:

| La finestra di dialogo dice | Codice | Cosa fare |
| --- | --- | --- |
| L'email è disattivata o non funzionante su questa istanza. | `EMAIL_UNAVAILABLE` | La configurazione è cambiata da quando è stata aperta la finestra di dialogo, per esempio dopo un riavvio: vedere [Impostazioni › Amministrazione › Email](email.md#email-tab). |
| Le email non possono contenere link: LIBREFOLIO_PUBLIC_URL non è impostata, oppure non può essere l'inizio di un link. | `EMAIL_LINKS_UNAVAILABLE` | Impostarla, quindi riavviare: vedere [Email con un link](email_flows.md#public-url). |
| Questo link non funziona più: crearne uno nuovo. | `EMAIL_LINK_INVALID` | Il link è scaduto, è stato usato o è stato revocato: creare un nuovo link e inviare quello. |
| L'account non è attivo: attivarlo prima di inviargli un link di reimpostazione. | `EMAIL_ACCOUNT_INACTIVE` | **Riattivare** l'account in [Utenti e inviti](users.md#actions), oppure eseguire `user activate` sulla [riga di comando](cli_tools.md), quindi inviare di nuovo il link. |
| Inserire l'indirizzo a cui inviare l'invito. | `EMAIL_RECIPIENT_REQUIRED` | L'invito non contiene alcun indirizzo: digitarne uno in **Invia a**. |
| Non è un singolo indirizzo email valido. | `EMAIL_RECIPIENT_INVALID` | Correggere l'indirizzo in **Invia a**. Per un link di reimpostazione, l'indirizzo dell'account stesso non è valido: copiare invece il link. |
| Il limite orario delle email è raggiunto: riprova tra … min. | `EMAIL_RATE_LIMITED` | Attendere i minuti indicati. Per consentirne di più, aumentare `LIBREFOLIO_SMTP_MAX_PER_HOUR` e riavviare. |
| Il server SMTP ha rifiutato l'indirizzo del destinatario. | `RECIPIENT_REFUSED` | L'indirizzo a cui è andato il link: quello in **Invia a** per un invito, l'email dell'account per un link di reimpostazione. Senza login, un server potrebbe rifiutarsi di inoltrare la posta ad altri domini: la sua risposta nel log lo dice. |
| Gli altri messaggi dell'email di test | `CONNECTION_FAILED`, `TLS_FAILED`, `AUTH_FAILED`, … | Come nella tabella sopra. |
| Non è stato possibile inviare l'email. | — | Non è arrivata alcuna risposta nota, per esempio dopo un errore di rete: ricaricare la pagina e guardare il log. |

`EMAIL_RECIPIENT_NOT_ALLOWED`, un altro indirizzo per un link di reimpostazione, proviene solo dall'API: la
finestra di dialogo non restituisce mai questo codice.

### 📜 Cosa dice il log {: #logs }

Il log è `logs/librefolio.log` nella cartella dei dati, e il server lo stampa anche sulla console:
`docker compose logs librefolio` con Docker ([Struttura del filesystem](filesystem.md)).

A ogni avvio, subito dopo `Starting LibreFolio`, il server controlla la sua configurazione, email
inclusa ([Controlli all'avvio](configuration_security.md#startup-checks)). Una configurazione che non può essere
usata compare lì in due righe, le prime due qui sotto; `none` verso un server esterno alla tua rete
locale, e un `LIBREFOLIO_PUBLIC_URL` mancante o non valido, in una riga ciascuno. Nessuna di esse ferma
l'avvio. Gli stessi tre controlli sono nella scheda **Sicurezza** di **Impostazioni › Amministrazione**,
riletti quando lo richiedi, dove un risultato rimanda alla [scheda Email](email.md#email-tab) (vedere «Sicurezza» in
[Impostazioni globali](settings.md)).

| Il log dice | Livello | Quando |
| --- | --- | --- |
| `Email configuration cannot be used: email stays off` | `error` | Una variabile non può essere usata. Ogni processo server la registra una volta, all'avvio, con `variable`, `problem` (il codice) e `reason`: la regola che viola, oppure perché il file della password non può essere letto. |
| `LIBREFOLIO_SMTP_… cannot be used (SMTP_…): email stays off until it is fixed` | `error` | All'avvio, dopo la riga sopra, con `check` impostato a `email.smtp`: i controlli all'avvio segnalano lo stesso problema. |
| `LIBREFOLIO_SMTP_TLS=none with …: emails, their links and the SMTP password travel unencrypted; use starttls or tls` | `warning` | All'avvio, con `check` impostato a `email.smtp_encryption`: `none` verso un server esterno alla tua rete locale, che la riga nomina ([Note di sicurezza](#security)). |
| `LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out` | `info` | All'avvio, con `check` impostato a `email.links`: l'email funziona, ma `LIBREFOLIO_PUBLIC_URL` non è impostata ([Email con un link](email_flows.md#public-url)). |
| `LIBREFOLIO_PUBLIC_URL cannot start a link (it needs http:// or https:// and a host, with no user name, password, ? or #): no email with a link (forgotten password, invitation, reset) can go out` | `warning` | All'avvio, con `check` impostato a `email.links`: l'email funziona, ma la variabile non può essere l'inizio di un link ([Email con un link](email_flows.md#public-url)). |
| `Email sent` | `info` | Il server ha accettato un'email; `kind` dice quale: `test`, `invite`, `password_reset`, `email_verification`, `email_changed` o `email_change_confirmation`. |
| `Email not sent` | `warning` | Il server ha rifiutato l'email o non ha risposto: `code`, come in [Errori di invio](#sending-errors), e `detail`, la risposta del server stesso, l'indizio più preciso. |
| `Email not sent: the hourly limit of the instance is reached` | `warning` | Il limite orario ha fermato un'email; `retry_after` è in secondi. |
| `Test email sent by an administrator` | `info` | Un'email di test è partita, con `admin_id` e `language`. |
| `Link emailed by an administrator` | `info` | Un amministratore ha inviato un link via email: `admin_id`, `purpose` (`invite` o `password_reset`), `token_id`, lo `user_id` dell'account per un link di reimpostazione, e `language`. |
| `Forgotten password: reset link emailed` | `info` | Un link di reimpostazione è partito per una password dimenticata: `user_id`, `token_id` e `language`. |
| `Forgotten password: no active account matches, nothing sent` | `info` | Nessun account attivo ha quel nome utente o indirizzo email. Ciò che è stato digitato non viene mai registrato. |
| `Forgotten password: the account had a reset link moments ago, nothing sent` | `info` | I limiti dell'account stesso: un link di reimpostazione meno di 5 minuti fa, oppure 3 nell'ultima ora; con `user_id`. |
| `Forgotten password: an administrator's reset link is still live, nothing sent` | `info` | Una richiesta non annulla mai un link che un amministratore ha dato all'account; con `user_id`. |
| `Forgotten password: the hourly limit of the instance is reached, nothing sent` | `warning` | Il limite orario è stato raggiunto dopo la risposta; con `user_id`. |
| `Forgotten password: the mailbox had reset emails moments ago, nothing sent` | `info` | Quella casella di posta aveva già 3 email di reimpostazione nell'ultima ora, comprese quelle che non sono partite; con `user_id`. |
| `Forgotten password: another request won the race, nothing sent` | `info` | Due richieste per l'account nello stesso momento: l'altra invia l'email; con `user_id`. |
| `Forgotten password: no email sent` | `warning` | L'email o `LIBREFOLIO_PUBLIC_URL` hanno smesso di funzionare dopo la risposta, oppure l'email è stata rifiutata: `reason` e `code` dicono quale. Un link creato per essa viene revocato. |
| `Forgotten password: the request failed` | `error` | Un errore imprevisto, con il suo tipo in `error` e nulla di più: nessun dettaglio della richiesta raggiunge il log. |
| `Registration waits for email verification` | `info` | Un nuovo account attende il suo link; con `user_id`. La riga `User registered` della stessa registrazione ha `waits_for_email` impostato a true. |
| `Verification email held: address limit or instance budget reached` | `info` | L'indirizzo della registrazione aveva già ricevuto le sue `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` email (20 per impostazione predefinita) nell'ora, oppure il limite orario dell'istanza è esaurito: l'account attende senza la sua email, e la pagina di login lo comunica al suo proprietario; con `user_id`. |
| `Verification link emailed` | `info` | Un link di verifica è partito: `user_id`, `token_id` e `language`. |
| `Verification email: not sent` | `warning` | L'email di una registrazione non è partita: `reason` e `code` dicono perché. La pagina aveva detto che l'email era in arrivo, quindi solo questa riga dice che non è partita. L'account attende ancora, e il suo proprietario può richiedere di nuovo il link. |
| `Verification email: the account no longer waits, nothing sent` | `info` | Un amministratore ha attivato, disattivato o eliminato l'account prima che la sua email partisse; con `user_id`. |
| `Verification email: the request failed` | `error` | Un errore imprevisto, con il suo tipo in `error` e lo `user_id`, nulla di più. |
| `Login refused: email not verified` | `info` | Un account in attesa ha effettuato l'accesso con la password corretta; con `user_id`. |
| `Verification resend refused: wrong credentials` | `warning` | Qualcuno ha chiesto un nuovo link di verifica con una password errata, o per un account che non esiste. Né ciò che è stato digitato né l'indirizzo vengono registrati. |
| `Email verified` | `info` | Il proprietario ha confermato nella pagina del link: l'account è attivo; `user_id` e `token_id`. |
| `Email verification refused: the link's email did not go out` | `info` | Qualcuno ha confermato con un link la cui email LibreFolio ha considerato non inviata: l'account attende ancora, e **Invia di nuovo il link** funziona. |
| `Email verification refused: the link was sent to another address` | `info` | L'indirizzo dell'account è cambiato dopo l'invio del link: quel link smette di funzionare. |
| `Email change notice sent to the previous address` | `info` | L'avviso è andato al vecchio indirizzo. La riga ha `user_id` e `language`, e nessuno dei due indirizzi. |
| `Email change notice: email is off, nothing sent` | `info` | L'email è disattivata: niente da inviare, e nulla di sbagliato. |
| `Email change notice: past its limits, nothing sent` | `info` | L'account, o la vecchia casella di posta, aveva già 3 avvisi nell'ora: il cambio è andato a buon fine, l'avviso no. Con `user_id`. |
| `Email change notice: the account no longer exists, nothing sent` | `info` | L'account è stato eliminato prima che l'email partisse. |
| `Email change notice: not sent` | `warning` | L'email è configurata ma non può essere usata ora, il limite orario è raggiunto, il vecchio indirizzo non è un singolo indirizzo semplice, oppure l'invio è fallito: `reason` e `code` dicono quale. |
| `Email change notice: the request failed` | `error` | Un errore imprevisto, con il suo tipo in `error` e lo `user_id`, nulla di più. |

Ogni link di reimpostazione lascia anche una riga `Password reset link created`, con `user_id`, `token_id` e,
quando lo ha creato un amministratore, `created_by_user_id`.

Nessuna di queste righe contiene la password SMTP, il contenuto di un'email, un link o la sua parte segreta,
ciò che qualcuno ha digitato per chiedere un link di reimpostazione o un nuovo link di verifica, o l'indirizzo completo del destinatario:
solo il suo dominio, in `recipient_domain`. Spesso i server citano l'indirizzo che rifiutano, quindi
anche la loro risposta viene mascherata, come `550 5.1.1 <***@example.com>: Recipient address rejected`. L'avviso
di un cambio di email non nomina né il vecchio indirizzo né quello nuovo.

---

## 🔒 Note di sicurezza {: #security }

- **`starttls` non fa mai fallback sul testo in chiaro.** Un server che non offre la crittografia non riceve
  né la password né il messaggio: l'email di test fallisce con `TLS_FAILED`.
- **Il certificato viene sempre controllato**, con `starttls` e con `tls`: non c'è alcuna opzione per saltare
  il controllo.
- **`none` invia tutto in chiaro**: i messaggi, i loro link e la password SMTP. Usarlo per
  un relay sulla propria macchina o rete. Verso qualsiasi altro server,
  Impostazioni › Amministrazione › Email mostra un avviso: *Le email, i loro link e la password SMTP
  viaggiano senza crittografia verso un server esterno alla rete locale*; anche il log di avvio ne contiene uno
  ([Cosa dice il log](#logs)).
- **Tenere la password in un file segreto** (`LIBREFOLIO_SMTP_PASSWORD_FILE`) che solo l'utente
  che esegue LibreFolio può leggere, fuori da `.env` e fuori dalla cartella dei dati. Usare una password per l'app, o un
  account dedicato solo a LibreFolio, che si possa revocare autonomamente.
- **I link provengono solo da `LIBREFOLIO_PUBLIC_URL`**, mai da una richiesta: nessuno può far sì che
  LibreFolio invii per email a uno dei tuoi utenti un link a un sito controllato da terzi ([Email con un link](email_flows.md#public-url)).
- **Un link di verifica va solo all'indirizzo dell'account stesso**, e nessuno lo vede, amministratore
  compreso. **Invia di nuovo il link** chiede la password dell'account, come fa il login,
  e un nuovo link disattiva quelli precedenti.
- **I nomi restano su una riga.** Un nome utente, il nome di chi invita o il nome dell'istanza
  vengono scritti in un'email su una riga: i caratteri di controllo e le interruzioni di riga diventano spazi, e i
  caratteri che riordinano il testo (controlli bidirezionali) vengono rimossi. Un nome utente creato ad arte non può né
  aggiungere righe proprie a un'email né camuffarne il testo.
- **Nessuna parola di estranei in un'email.** Una reimpostazione della password, una verifica email e l'avviso di un
  cambio di email possono essere inviati, da qualcuno che non è un amministratore, a un indirizzo di sua scelta.
  Queste email iniziano con un semplice «Ciao,», senza il nome utente, e l'avviso non mostra alcuna parte del
  nuovo indirizzo: LibreFolio non risolve i domini, quindi anche la parte finale di un indirizzo è scelta liberamente. Un link
  di reimpostazione che invii per email è scritto allo stesso modo. Il nome utente appare comunque una volta aperto il link.
  Solo l'email di test e il link di configurazione dell'amministratore iniziale salutano per nome: li invii tu, o
  chi gestisce il server.
- **Le password dimenticate non dicono a nessuno quali account esistono**: la stessa risposta per tutti, la
  ricerca dopo la risposta, e limiti per indirizzo, per nome utente o indirizzo email, per casella di posta e
  per account ([Password dimenticate](email_flows.md#forgot-password)).
- **Cambiare l'indirizzo email di un account richiede la sua password attuale.** Senza di essa, basterebbe un momento
  dentro la sessione di qualcuno (un cookie di sessione rubato, un computer lasciato sbloccato) per
  mettere il proprio indirizzo sull'account, poi reimpostarne la password da lì: la reimpostazione via email è stata resa disponibile
  solo insieme a questa regola. Quando l'email funziona, anche il vecchio indirizzo riceve un avviso
  ([Cambi di indirizzo email](email_flows.md#email-change-notice)).
- **Il limite orario** limita ciò che l'istanza può inviare, qualunque cosa accada: aumentarlo solo quanto
  necessario.

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
