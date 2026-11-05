# 📬 Email: Link e messaggi

Questa pagina descrive i messaggi che LibreFolio invia una volta che l'email funziona: i **link** per inviti e reimpostazioni della password, le **password dimenticate**, i **limiti** su queste email, la **verifica** dei nuovi indirizzi e l'avviso di un **cambio di indirizzo**.

Prima deve funzionare l'email: le variabili SMTP, la scheda **Email** e l'email di prova sono in [Email](email.md), mentre cosa controllare quando un messaggio non parte è in [Email: quando non funziona](email_troubleshooting.md).

---

## 🌐 Email con un link {: #public-url }

Un link di invito o di reimpostazione della password inviato per email viene costruito solo da `LIBREFOLIO_PUBLIC_URL`: quell'indirizzo, poi la pagina che riceve il link, ad esempio `https://librefolio.example.com/reset-password#token=…`. Mai dall'indirizzo usato dal browser, né da qualsiasi altra cosa presente in una richiesta.

- **Perché.** Chiunque può inviare a LibreFolio una richiesta che indica un altro indirizzo. Se un link venisse costruito dalla richiesta, un estraneo potrebbe far sì che LibreFolio invii per email a uno dei tuoi utenti un link reale verso un sito suo, e catturarne la parte segreta quando l'utente lo apre.
- **Cosa impostare.** L'indirizzo con cui i tuoi utenti aprono LibreFolio, con `http://` o `https://` e un nome host, ad esempio `https://librefolio.example.com`: senza nome utente o password, senza `?` o `#`, senza spazi. È la stessa variabile che la riga di comando antepone ai link che stampa: vedi [Account e registrazioni](configuration_accounts.md#accounts).
- **Senza di essa**, o con un indirizzo che viola queste regole, nessuna email con un link viene inviata: tale email viene rifiutata con `EMAIL_LINKS_UNAVAILABLE`, mentre l'email di prova funziona ancora, e **Richiedi la verifica dell'email** non può essere attivata ([Verifica email](#verification)). I link che copi, ad esempio dalla [riga di comando](cli_tools.md), restano come sono.
- **Cosa dice l'email**: nomina la tua istanza tramite l'host di `LIBREFOLIO_PUBLIC_URL` e indica per quanto tempo il link è ancora valido: 7 giorni per un nuovo invito, 30 minuti per un link di reimpostazione della password, 24 ore per un link di verifica, 72 ore per il link di configurazione dell'amministratore iniziale. Un link funziona una sola volta.
- **La parte segreta** del link viene dopo `#`: i browser non la inviano mai al server, quindi resta fuori dai log del server e del proxy.
- **Per verificarlo**: con l'email **Pronta**, Impostazioni › Amministrazione › Email mostra un avviso quando `LIBREFOLIO_PUBLIC_URL` non è impostata o non può essere usata, e il log di avvio contiene una riga ([Cosa dice il log](email_troubleshooting.md#logs)). Una volta che può essere usata, la scheda mostra l'indirizzo e controlla, dal tuo browser, che questa istanza risponda lì: vedi [L'indirizzo nelle email con link](email.md#links-check). Da qualsiasi punto, `/api/v1/system/instance` mostra `"links": true` una volta che sia l'email sia l'indirizzo sono a posto.

---

## 📨 Link inviati da un amministratore {: #admin-links }

Un link di invito o di reimpostazione della password creato da un amministratore può essere inviato per email, invece di essere copiato a mano. Finché l'email è **Pronta** e `LIBREFOLIO_PUBLIC_URL` può essere usata ([Email con un link](#public-url)), le finestre di dialogo di invito e di reimpostazione della password di [Utenti e inviti](users.md#send-by-email) mostrano **Invia per email** sotto il link:

1. Crea il link come al solito: **Invita**, oppure **Link di reimpostazione password** nella riga della persona.
2. Per un invito, controlla l'indirizzo in **Invia a**: parte da quello scritto nell'invito e puoi modificarlo. Un link di reimpostazione della password non ha un campo: va all'indirizzo del suo account.
3. Per un invito, scegli la **Lingua dell'email**: **La lingua dell'istanza** la scrive nella **Lingua predefinita** dell'istanza ([Impostazioni globali](settings.md)); scegli English, Italiano, Français o Español per qualcuno che ne legge un'altra. Un link di reimpostazione della password va nella lingua del suo account. Per impostare la **Lingua predefinita** prima che un amministratore l'abbia salvata, inserisci `LIBREFOLIO_DEFAULT_LANGUAGE` nel file `.env` (`en`, `it`, `fr` o `es`): vedi [Variabili d'ambiente](configuration_accounts.md#accounts).
4. Fai clic su **Invia per email**. La finestra dice *Inviata a …* con l'indirizzo e la lingua in cui è stata scritta l'email, oppure perché l'email non è partita ([Errori di invio](email_troubleshooting.md#sending-errors)).

Le regole:

- **Il link nell'email inizia con `LIBREFOLIO_PUBLIC_URL`**, qualunque sia l'**Indirizzo del server** mostrato nella finestra: solo la parte segreta del link viaggia dalla finestra. La finestra lo dice sopra il pulsante.
- **Un invito** va all'indirizzo in **Invia a**, oppure a quello scritto nell'invito, nella lingua scelta in **Lingua dell'email**, la **Lingua predefinita** dell'istanza se non ne hai scelta un'altra. È solo la lingua dell'email: non diventa la lingua dell'account creato dall'invito. Indica te come persona che invita e precisa che il nuovo account sarà un amministratore.
- **Un link di reimpostazione della password** va solo all'indirizzo del suo account, nella lingua dell'account, e solo finché l'account è attivo.
- **Viene inviato solo un link valido**: uno scaduto, usato o revocato viene rifiutato, e se ne deve creare uno nuovo.
- Ogni email conta ai fini del limite orario.

---

## 🗝️ Password dimenticate {: #forgot-password }

Chi ha dimenticato la password può richiedere un link di reimpostazione della password via email, con il proprio nome utente o indirizzo email, senza accedere. Nella pagina di accesso, **Password dimenticata?** apre un modulo per farlo quando le email con un link possono partire: email **Pronta** e una `LIBREFOLIO_PUBLIC_URL` utilizzabile. Sotto il modulo, un pannello chiuso finché non viene cliccato conserva il comando che un amministratore può eseguire sul server. Altrimenti la pagina mostra quel comando, aperto, sotto l'avviso *Il recupero via email non è disponibile su questa istanza. Reimposta la password dal terminale del server oppure chiedi all'amministratore un link di reimpostazione della password.* Quando la pagina non riesce a leggere la configurazione dell'istanza dal server, mostra solo il suggerimento *Chiedi all'amministratore un link di reimpostazione della password: può crearne uno per il tuo account.* Un amministratore crea quel link in **Impostazioni › Amministrazione › Utenti**, anche senza email ([Link di reimpostazione password](users.md#reset-links)).

È sicuro perché cambiare l'indirizzo email di un account richiede la password attuale ([Profilo](../user/settings/profile.md)): vedi [Note di sicurezza](email_troubleshooting.md#security).

Funziona così:

- **La stessa risposta per tutti**: *Se un account attivo corrisponde, il suo proprietario riceve un'email con un link per scegliere una nuova password*, indipendentemente dal fatto che un account corrisponda o no. La ricerca dell'account e l'invio dell'email avvengono dopo la risposta, così nessuno può usarla per scoprire quali account esistono.
- **L'account** viene trovato come lo trova l'accesso, tramite nome utente o indirizzo email. Solo un account attivo riceve l'email, al proprio indirizzo e nella propria lingua.
- **Il link** funziona una sola volta, per 30 minuti, e sostituisce i link di reimpostazione della password inviati all'account dalle richieste precedenti. Finché un link di reimpostazione della password creato da un amministratore è ancora valido, non viene inviato nulla: una richiesta non lo annulla mai.
- **Quando l'email o `LIBREFOLIO_PUBLIC_URL` non sono pronti**, la richiesta viene rifiutata con un breve messaggio, uguale per tutti.

I limiti:

| Limite | Se superato |
| --- | --- |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` richieste all'ora (20 per impostazione predefinita) dallo stesso indirizzo, un conteggio condiviso con le registrazioni e con **Invia di nuovo il link** ([Limiti sulle email di attivazione e di reimpostazione della password](#activation-limits)); un indirizzo IPv6 conta per il suo /64, il blocco che di solito ha un abbonato | La richiesta viene rifiutata finché non si libera un posto in quel conteggio, o nel limite orario dell'istanza se quello fa attendere più a lungo; la risposta indica per quanto tempo. |
| 3 richieste all'ora per lo stesso nome utente o indirizzo email, che un account corrisponda o meno | La richiesta viene rifiutata finché la più vecchia di esse non ha un'ora. |
| Il limite orario dell'istanza, `LIBREFOLIO_SMTP_MAX_PER_HOUR` | La richiesta viene rifiutata finché non rientra di nuovo un'email. |
| 3 email all'ora alla stessa casella di posta, per qualunque account siano e comunque sia scritto il suo indirizzo | Non viene inviato nulla e la risposta resta la stessa. |
| 1 email ogni 5 minuti, e 3 all'ora, per lo stesso account, compresi i link di reimpostazione della password creati da un amministratore | Non viene inviato nulla e la risposta resta la stessa. Due richieste nello stesso momento non possono essere inviate entrambe. |

Il limite per account conta i link di reimpostazione della password dell'account nel database. Gli altri sono conservati nella memoria di ciascun processo del server: con più processi, ognuno mantiene il proprio conteggio, e un riavvio li dimentica. Un'email di reimpostazione della password che non è partita conta comunque, per l'account e per la casella di posta.

**Una casella di posta, comunque sia scritto il suo indirizzo.** Il limite per casella di posta conta gli alias di un indirizzo come un'unica casella: le maiuscole non contano, né un `+tag` su qualsiasi dominio (`name+news@example.com` è `name@example.com`), né i punti di un indirizzo Gmail, dove `googlemail.com` è `gmail.com` (`first.last@googlemail.com` è `firstlast@gmail.com`). I limiti delle [email di verifica](#verification-limits) e degli [avvisi di cambio email](#email-change-notice) contano allo stesso modo. Ogni email va comunque all'indirizzo esattamente come lo ha l'account. Una casella che accetta posta sotto qualsiasi nome, come un dominio catch-all o `anything@user.fastmail.com` di Fastmail, conta ogni nome a parte: solo il limite orario dell'istanza trattiene quelli.

**Dietro un reverse proxy**, l'indirizzo che conta è quello del visitatore, come lo legge LibreFolio (vedi [L'indirizzo del visitatore](connection_proxy.md#client-address)):

- Quando `LIBREFOLIO_CLIENT_IP_HEADER` indica l'header che il tuo proxy imposta con l'indirizzo del visitatore (`Fly-Client-IP` su Fly.io, `X-Real-IP` da Nginx), LibreFolio lo legge lì. Impostalo solo se ogni richiesta passa attraverso quel proxy: un visitatore che raggiunge LibreFolio direttamente potrebbe scrivere l'header.
- Altrimenti è l'indirizzo che vede il server (uvicorn), il quale prende l'indirizzo del visitatore dall'header `X-Forwarded-For` del proxy solo quando l'indirizzo del proxy è elencato in `FORWARDED_ALLOW_IPS` (`127.0.0.1` se non impostato). Elenca lì gli indirizzi o le reti del tuo proxy, ad esempio `172.18.0.0/16`, mai `*`: con `*`, uvicorn prende il primo indirizzo dell'header, che il visitatore può scrivere.
- **Un proxy di cui LibreFolio non si fida, su un indirizzo locale** (una rete Docker, la tua rete o la tua VPN), ad esempio un container proxy davanti all'immagine Docker, la configurazione abituale: questi limiti per indirizzo escludono le richieste che passano da lì, così le richieste di un visitatore non possono esaurire il conteggio di **Password dimenticata?**, **Invia di nuovo il link** e delle registrazioni per tutti. I limiti per nome utente o indirizzo email, per account e per casella di posta, e il limite orario dell'istanza, continuano a contarle. Il log avvisa una volta per processo del server, e i controlli di sicurezza lo segnalano come avviso di `platform.client_address` (vedi [L'indirizzo del visitatore](connection_proxy.md#client-address)).
- **Un proxy di cui LibreFolio non si fida, su un indirizzo pubblico**, come una CDN: ogni visitatore condivide l'indirizzo del proxy e il suo conteggio, quindi le prime `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` richieste di chiunque esauriscono il conteggio di quelle richieste attraverso il proxy per tutti, per un massimo di un'ora. Comunica il proxy a LibreFolio.

---

## 🚦 Limiti sulle email di attivazione e di reimpostazione della password {: #activation-limits }

Le email che attivano un account e quelle che reimpostano una password sono trattenute da **due contatori**, gli stessi per ogni modo di richiederle. Ognuno conta negli ultimi 60 minuti, nella memoria di ciascun processo del server.

| Contatore | Variabile | Predefinito | Cosa conta |
| --- | --- | --- | --- |
| **Per indirizzo** | `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` | 20 all'ora | Le email che partono per un indirizzo client (un indirizzo IPv6 per il suo /64), in un unico conteggio: le registrazioni, ogni **Invia di nuovo il link** con la password corretta e ogni **Password dimenticata?** per un account esistente. I tentativi non vengono contati: una password errata, una richiesta per un nome che nessun account ha, o una rifiutata da un altro limite non gli costa nulla |
| **Per istanza** | `LIBREFOLIO_SMTP_MAX_PER_HOUR` | 50 all'ora | Ogni email inviata dall'istanza: attivazioni, reimpostazioni, inviti, avvisi |

Altri tre limiti restano come sono. Non sono contatori di email di attivazione, e raramente contano per un account la cui email è stata trattenuta, dato che nulla ha ancora raggiunto la sua casella di posta:

- il limite dell'accesso sulle **password errate** ([Accessi non riusciti](configuration_accounts.md#login-limit)), che **Invia di nuovo il link** condivide con la pagina di accesso;
- **3 email all'ora alla stessa casella di posta**, così che LibreFolio non possa essere usato per inondare l'indirizzo di qualcun altro;
- **1 email ogni 5 minuti, e 3 all'ora, per lo stesso account**, per **Invia di nuovo il link**.

Il contatore per indirizzo conta le **email che partono**, non i tentativi. Viene consultato per primo, quindi una richiesta viene rifiutata subito, prima che la password sia verificata, quando il conteggio è pieno; viene consumato all'ultimo momento, quando l'email sta per partire, e non da nient'altro: le password errate hanno il proprio limite, una richiesta per un nome che nessun account ha non costa nulla (e, per **Password dimenticata?**, la risposta è la stessa indipendentemente dal fatto che un account corrisponda o no), e un **Invia di nuovo il link** rifiutato dal limite per account o per casella di posta non consuma nulla. Un'email che il server SMTP rifiuta poi resta contata: è stata tentata.

Quando un contatore trattiene una richiesta, la risposta indica quanti secondi attendere, e quel tempo è esatto: è il **più lungo** dei tempi di attesa dei contatori che l'hanno trattenuta, quindi la stessa richiesta fatta in quel momento passa, a meno che altri dalla stessa rete abbiano usato il posto nel frattempo (la risposta indica allora il nuovo tempo).

**Un esempio.** Un ufficio con un solo indirizzo internet e un limite di 20. Tra le 9:00 e le 9:40 si registrano venti colleghi, e partono le loro venti email. Alle 9:45 si registra il ventunesimo, Mario: il suo account viene creato, ma la sua email è trattenuta, e la pagina gli dice di riprovare tra circa 15 minuti, il tempo che manca perché l'email delle 9:00 esca dal conteggio alle 10:00. Alle 9:46 accede e chiede di nuovo il link: lo stesso contatore lo rifiuta, per 14 minuti. Alle 10:00 chiede di nuovo con nome utente e password, e il link parte.

Il contatore per indirizzo è condiviso di proposito, con una conseguenza da conoscere: quando una rete ha esaurito il proprio conteggio con le registrazioni, anche **Password dimenticata?** da quella rete attende, finché non si libera un posto. Aumenta `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` per una rete in cui molte persone si registrano insieme, come una scuola o un ufficio, e riavvia.

---

## ✅ Verifica email {: #verification }

Con **Richiedi la verifica dell'email** attivo, un nuovo account non può accedere finché il suo proprietario non conferma l'indirizzo con un link che LibreFolio invia per email all'account. L'interruttore si trova in **Impostazioni › Amministrazione › Impostazioni globali**, nella categoria **Sicurezza** ([Impostazioni globali](settings.md)), ed è disattivato per impostazione predefinita.

- **Chi attende**: ogni account creato dalla pagina di registrazione mentre l'interruttore è attivo, compresi quelli aperti con un invito. Il primo account di una nuova istanza, il suo amministratore, non attende mai, né lo fa l'amministratore che LibreFolio crea da `LIBREFOLIO_ADMIN_EMAIL`, che viene attivato dal suo link di configurazione; nemmeno gli account creati con `user create` sulla [riga di comando](cli_tools.md), né gli account già esistenti.
- **Subito dopo la registrazione**, la pagina di accesso dice: *Account creato. Ti stiamo inviando un'email con un link per attivarlo: aprilo entro 24 ore, poi accedi. Nessuna email dopo qualche minuto? Controlla la cartella spam, poi accedi con nome utente e password: ti verrà offerto un nuovo link.* Quando l'indirizzo client ha già ricevuto le email di `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` registrazioni (20 per impostazione predefinita) nell'ultima ora, o il limite orario dell'istanza è esaurito, nessuna email parte, e la pagina lo dice invece, con quanto tempo attendere: *Account creato, ma non è stato possibile inviare ora l'email di attivazione. Riprova tra circa N minuti: accedi con nome utente e password, e ti verrà offerto un nuovo link.* N è esatto: è il tempo necessario perché entrambi i contatori ammettano una nuova email ([Limiti sulle email di attivazione e di reimpostazione della password](#activation-limits)). Dietro un reverse proxy di cui LibreFolio non si fida, su un indirizzo locale (la configurazione Docker abituale), non viene contato nulla per indirizzo, quindi questo secondo testo non compare mai ([Password dimenticate](#forgot-password)). In ogni caso l'account viene creato e resta in attesa.
- **L'email**, *Conferma il tuo indirizzo email*, parte subito dopo quella risposta, a meno che un limite la trattenga ([Limiti delle email di verifica](#verification-limits)), nella **Lingua predefinita** dell'istanza: un nuovo account non ha ancora una lingua propria. Il suo pulsante, **Conferma il mio indirizzo email**, apre un link che inizia con `LIBREFOLIO_PUBLIC_URL` ([Email con un link](#public-url)) e funziona una sola volta, per 24 ore.
- **Finché l'indirizzo non è confermato**, l'account non può accedere. Accedendo con la password corretta viene detto che l'indirizzo non è ancora verificato, e viene offerto **Invia di nuovo il link**: un nuovo link, che invalida quelli precedenti. Con una password errata, l'accesso dà il suo solito rifiuto, così nessuno apprende più di quanto non apprenderebbe da qualsiasi altro tentativo.
- **Una volta che il proprietario conferma**, l'account è attivo e il proprietario torna alla pagina di accesso con una conferma. Cosa vede la persona, passo dopo passo: *Se LibreFolio ti chiede di confermare la tua email* in [Per iniziare](../user/getting-started.md).
- **Aprire il link non conferma nulla**: mostra una pagina di LibreFolio con un pulsante, **Conferma il mio indirizzo email**, e solo il clic su di esso consuma il link. Il motivo sono i filtri della posta che analizzano i link, come Microsoft Defender Safe Links: aprono i link di un messaggio in un browser che esegue script, e se bastasse aprirli, il filtro attiverebbe l'account al posto del proprietario. Una tale apertura non consuma nulla; il link resta valido per il suo proprietario. Chi apre un link senza essersi registrato deve solo chiudere la pagina.

### 🔀 Attivarlo e disattivarlo {: #verification-switch }

- **Si attiva solo finché le email con un link possono partire**: email **Pronta** ([Impostazioni › Amministrazione › Email](email.md#email-tab)) e una `LIBREFOLIO_PUBLIC_URL` utilizzabile ([Email con un link](#public-url)). Fino ad allora, mentre è disattivato, l'interruttore è in grigio, con il suggerimento *Richiede un'email con un link da inviare: configura prima SMTP e LIBREFOLIO_PUBLIC_URL (Impostazioni › Amministrazione › Email).* Se ciò cambia tra il momento in cui apri la scheda e il salvataggio, il salvataggio viene rifiutato — *La verifica email richiede un'email con un link da inviare, e ora nessuna può partire: controlla Impostazioni › Amministrazione › Email.* — e non se ne memorizza nulla.
- **Disattivarlo funziona sempre.** Gli account già in attesa continuano ad attendere: i loro link funzionano ancora, e anche **Invia di nuovo il link**. Per farne entrare uno subito, attivalo ([Account in attesa](#verification-waiting)).
- **Mentre è attivo, salvare le altre impostazioni funziona sempre**, anche quando da allora l'email ha smesso di funzionare.
- **Se l'email smette di funzionare mentre è attivo** — il server o una variabile si guastano — nessuno può più registrarsi, nemmeno con un invito, che resta valido: la pagina di registrazione dice *Al momento non è possibile registrarsi: questa istanza non può inviare l'email di verifica. Riprova più tardi oppure chiedi al suo amministratore.*, e nessun account viene creato. Solo il primo account di una nuova istanza viene lasciato passare. **Invia di nuovo il link** fallisce allo stesso modo. Sistema l'email ([Quando non funziona](email_troubleshooting.md#troubleshooting)) oppure disattiva l'interruttore.

### ⏳ Account in attesa {: #verification-waiting }

In **Impostazioni › Amministrazione › Utenti**, un account in attesa mostra il badge **In attesa di verifica**, non **Disattivato**, anche una volta scaduto il suo link. Passa il mouse sul badge, o apri la riga, per il suggerimento: il suo proprietario non ha ancora aperto il link, accedendo ne viene offerto uno nuovo, e **Riattiva** fa entrare l'account subito.

- **Occupa un posto** del limite utenti (`LIBREFOLIO_MAX_USERS`) finché il suo link è valido, come un invito aperto. Quando l'ultimo link inviato scade, 24 ore dopo, il posto torna libero, e **Invia di nuovo il link** richiede allora un posto libero: su un'istanza piena, al proprietario viene detto di chiedere a te.
- **Per farlo entrare senza l'email**, fai clic su **Riattiva** nella sua riga ([Account in attesa della loro email](users.md#waiting)), oppure esegui `user activate` sulla [riga di comando](cli_tools.md): può accedere subito, e i link già inviati smettono di funzionare. Finché il suo link è valido, questo non occupa un posto extra, dato che il suo posto è già contato: **Riattiva** funziona anche su un'istanza piena, e `user activate` non stampa alcun avviso di limite. Una volta scaduto il link, riattivarlo richiede un posto libero, come per qualsiasi account disattivato.
- **Per rifiutarlo**, eliminalo ([Elimina un account](users.md#delete)) o disattivalo: con `user deactivate` sulla riga di comando, oppure con l'API amministratore (`PATCH /api/v1/users/{id}` con `is_active: false`). Disattivato, smette di attendere: i suoi link smettono di funzionare, il suo posto è libero, la sua riga da quel momento indica **Disattivato**, e accedendo viene detto al proprietario che l'account è disabilitato. La scheda Utenti stessa non offre **Disattiva** per un account non attivo: lì, **Elimina** è la via.

### 📏 Limiti delle email di verifica {: #verification-limits }

| Limite | Se superato |
| --- | --- |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` email all'ora (20 per impostazione predefinita) dallo stesso indirizzo, contando le email che partono: le registrazioni, **Invia di nuovo il link** con la password corretta e **Password dimenticata?** per un account esistente; un indirizzo IPv6 conta per il suo /64 | I successivi nuovi account vengono comunque creati e attendono, ma le loro email non partono: la pagina di accesso lo dice subito dopo la registrazione, con quanto tempo attendere, e i loro proprietari chiedono di nuovo il link dalla pagina di accesso una volta trascorso quel tempo. **Invia di nuovo il link** viene rifiutato per lo stesso tempo. |
| Il limite proprio dell'accesso sulle password errate, condiviso con la pagina di accesso: 10 ogni 15 minuti per lo stesso nome utente o indirizzo email, 50 dallo stesso indirizzo (vedi [Accessi non riusciti](configuration_accounts.md#login-limit)) | La richiesta viene rifiutata prima che la password sia verificata: la pagina dice tra quanti minuti riprovare. La password corretta azzera i fallimenti di ciò che era stato digitato. |
| 1 email ogni 5 minuti, e 3 all'ora, per lo stesso account, compresa l'email della registrazione | La richiesta viene rifiutata: la pagina dice tra quanti minuti riprovare. |
| 3 email all'ora alla stessa casella di posta, per qualunque account siano e comunque sia scritto il suo indirizzo ([Password dimenticate](#forgot-password)): sia l'email di una registrazione sia i link inviati di nuovo, e solo le email che sono partite | **Invia di nuovo il link** viene rifiutato: la pagina dice tra quanti minuti riprovare. Dopo una registrazione, l'account viene creato e attende, ma nessuna email parte, e nulla lo dice al proprietario: la pagina mostra il suo testo abituale, che già indica cosa fare (controlla la cartella spam, poi accedi per ricevere un nuovo link). |
| Il limite orario dell'istanza, `LIBREFOLIO_SMTP_MAX_PER_HOUR` | La richiesta viene rifiutata finché non rientra di nuovo un'email. Una registrazione effettuata mentre è esaurito viene trattenuta come una oltre il limite del suo indirizzo. |
| Un posto libero, una volta scaduto il link dell'account | La richiesta viene rifiutata: al proprietario viene detto di chiedere a te. |

**Cosa resta invisibile.** Dopo una registrazione, *Ti stiamo inviando un'email* significa che l'email è in coda, non che è stata consegnata: parte dopo la risposta, e può comunque non partire. Il limite della casella di 3 email di verifica all'ora, il limite orario dell'istanza, un errore SMTP, l'email o `LIBREFOLIO_PUBLIC_URL` che hanno smesso di funzionare nel frattempo, un riavvio: nessuno di questi raggiunge la pagina. Solo il log lo dice, con `Verification email: not sent` o `Verification email: the request failed` ([Cosa dice il log](email_troubleshooting.md#logs)), e un riavvio prima che l'email parta non lascia alcuna riga. L'account resta in attesa con l'email trattenuta, e **Invia di nuovo il link** rimedia alla situazione; per questo il testo della pagina dice alla persona cosa fare quando non arriva nulla. Il limite della casella non viene deliberatamente controllato prima della risposta: una registrazione che rispondesse diversamente quando la casella avesse appena ricevuto email direbbe a chiunque si registri con l'indirizzo di qualcun altro se quella casella le sta ricevendo.

Un link la cui email non è partita non conta né per l'account né per la casella di posta. Se nel frattempo l'account smette di attendere — il suo indirizzo è confermato, oppure un amministratore lo ha attivato o disattivato — non viene inviato alcun nuovo link. I limiti per indirizzo e per casella di posta sono conservati nella memoria di ciascun processo del server: con più processi, ognuno mantiene il proprio conteggio, e un riavvio li dimentica. Dietro un reverse proxy, l'indirizzo che conta segue le regole indicate in [Password dimenticate](#forgot-password).

---

## 🔔 Cambi di indirizzo email {: #email-change-notice }

Quando qualcuno cambia l'indirizzo email del proprio account, in [Profilo](../user/settings/profile.md), LibreFolio scrive all'indirizzo che l'account aveva **prima**:

- **Solo al vecchio indirizzo**: il nuovo non riceve nulla.
- **Nulla del nuovo indirizzo e nessun nome utente**: l'email dice solo che l'indirizzo è cambiato, senza alcuna parte di quello nuovo, nemmeno il suo dominio, e si apre con un semplice «Ciao,» ([Note di sicurezza](email_troubleshooting.md#security)).
- **Nessun link.** Dice al proprietario che, se non è stato lui a fare il cambio, qualcuno potrebbe stare usando il suo account: deve cambiare subito la password se può ancora e segnalartelo.
- **Nella lingua dell'account.** Nomina la tua istanza tramite l'host di `LIBREFOLIO_PUBLIC_URL`, con la sua porta se ne ha una, oppure «LibreFolio» quando la variabile non è impostata o non può essere usata: non contenendo link, l'avviso non ne ha bisogno.
- **Dopo il cambio**: l'email parte dopo la risposta, e il cambio non la attende mai. Con l'email disattivata, non viene inviato nulla, e il log lo dice in una riga informativa, non in un avviso. L'avviso conta ai fini del limite orario come qualsiasi email.
- **Al massimo 3 all'ora per un account, e 3 all'ora alla stessa casella di posta**, comunque sia scritto il suo indirizzo ([Password dimenticate](#forgot-password)). Superato l'uno o l'altro, il cambio va comunque a buon fine e l'avviso viene saltato. Senza questi limiti, un account potrebbe puntare la propria email a un indirizzo qualsiasi e cambiarlo di nuovo, per far scrivere la tua istanza lì.
- **Non per le sole maiuscole.** Cambiare solo le maiuscole delle lettere dalla A alla Z, ad esempio `Anna@example.com` per `anna@example.com`, non è un cambio di indirizzo, quindi nessun avviso parte. Le lettere accentate contano come diverse: `Émile@example.com` per `émile@example.com` è un cambio, con il suo avviso.

---

## 🔗 Correlati

- 📄 **[Email](email.md)** — Dove si trova la configurazione, Le variabili, Esempi, …
- 📄 **[Email: quando non funziona](email_troubleshooting.md)** — Quando non funziona, Note di sicurezza
