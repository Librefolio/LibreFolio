# 👥 Configurazione: Account e ricerca degli asset

Questa pagina spiega chi può **registrarsi** al tuo LibreFolio e quanti account può contenere, il limite
sugli accessi non riusciti e l'**amministratore iniziale**, poi due opzioni della ricerca degli asset: l'ordine
dei provider di prezzi nei suoi risultati e la ricerca web opzionale.

Il file `.env` e le sue altre opzioni sono spiegati in [Configurazione](configuration.md), la
prima pagina della guida.

---

## 👥 Account e registrazioni {: #accounts }

Chi può creare un account, quanti account l'istanza può contenere e il limite sugli accessi
non riusciti. Senza queste variabili, l'impostazione **Registrazione** delle
[Impostazioni globali](settings.md) decide chi può registrarsi, non c'è alcun limite al
numero di account, la lingua dei nuovi account è quella scelta da un amministratore
([Impostazioni globali](settings.md)) e gli accessi non riusciti sono limitati ([Accessi non riusciti](#login-limit)). Tutte e otto sono
opzionali: togli il commento da una riga della sezione **Accounts** di `.env.example` per impostarne una. Altre tre, per
installazioni tramite script e Docker Compose, creano l'[amministratore iniziale](#initial-admin) di una nuova
istanza.

| Variabile | Predefinito | Cosa fa |
| --- | --- | --- |
| `LIBREFOLIO_REGISTRATION` | _non impostato_ | Chi può creare un account: `open` (chiunque), `invite` (solo con un link di invito) o `disabled` (nessuno). Non impostata: decide l'impostazione globale **Registrazione**; su una nuova istanza è **Su invito**, a meno che un amministratore l'abbia cambiata (un'istanza aggiornata da una versione precedente mantiene la modalità che aveva). Impostata: prevale questo valore e l'impostazione globale non può essere modificata dall'app. La distinzione tra maiuscole e minuscole e gli spazi attorno al valore non hanno importanza. Qualunque sia il valore, il primo account di una nuova istanza può essere creato dalla pagina di accesso, con **Registrati qui**, e diventa l'amministratore: vedi [Chi può registrarsi](settings.md). Con `LIBREFOLIO_ADMIN_EMAIL`, LibreFolio crea invece direttamente quell'amministratore: vedi [L'amministratore iniziale](#initial-admin). Impostata su `open`, mostra inoltre agli amministratori che aprono l'app da un indirizzo esterno alla rete locale un avviso che nomina questa variabile: vedi [L'avviso sulla registrazione aperta](settings.md). |
| `LIBREFOLIO_MAX_USERS` | _non impostato_ (nessun limite) | Il numero massimo di account che l'istanza può contenere: un numero intero, almeno `1`; qualsiasi altro valore (`0`, `abc`, `-3`, `1.5`) arresta il server all'avvio. Contano gli account attivi, così come ogni invito finché non viene usato, revocato o scade, ogni account in attesa della verifica email mentre il suo link è valido, e l'[amministratore iniziale](#initial-admin) mentre attende la sua configurazione; gli account disattivati non contano. Vedi [Quando l'istanza è piena](#user-limit). |
| `LIBREFOLIO_DEFAULT_LANGUAGE` | _non impostato_ | La lingua degli account che non ne hanno scelta una e delle email inviate a chi non ha ancora un account: `en`, `it`, `fr` o `es`, senza distinzione tra maiuscole e minuscole. Vale come **Lingua predefinita** delle [Impostazioni globali](settings.md) finché un amministratore non salva quell'impostazione per la prima volta; da quel primo salvataggio prevale il valore dell'amministratore, anche quando torna a essere l'inglese. Non impostato: decide l'impostazione; su una nuova istanza è l'inglese. Qualsiasi altro valore arresta il server all'avvio. |
| `LIBREFOLIO_DEFAULT_CURRENCY` | _non impostato_ | La valuta con cui iniziano i nuovi account: un codice ISO 4217 conosciuto da LibreFolio, come `EUR`, `USD` o `CHF`, senza distinzione tra maiuscole e minuscole. Vale come **Valuta predefinita** delle [Impostazioni globali](settings.md) finché un amministratore non salva quell'impostazione per la prima volta; da quel primo salvataggio prevale il valore dell'amministratore, anche quando torna a essere `EUR`. Non impostato: decide l'impostazione; su una nuova istanza è `EUR`. Qualsiasi altro valore arresta il server all'avvio. |
| `LIBREFOLIO_DEFAULT_TIMEZONE` | _non impostato_ | Il fuso orario dell'app, quello in cui vengono letti gli orari dello [scheduler dei dati di mercato](settings.md#market-data-scheduler): un nome IANA come `Europe/Rome` o `America/New_York` (il server stesso lavora sempre in UTC). Vale come **Fuso orario** della configurazione dello scheduler finché un amministratore non salva quell'impostazione per la prima volta; da quel primo salvataggio prevale il valore dell'amministratore, anche quando torna a essere `UTC`. Non impostato: decide l'impostazione; su una nuova istanza è `UTC`. Qualsiasi altro valore arresta il server all'avvio. |
| `LIBREFOLIO_PUBLIC_URL` | _non impostato_ | L'indirizzo da cui i tuoi utenti aprono LibreFolio, con `http://` o `https://`, come `https://librefolio.example.com`. Nella scheda [Utenti](users.md) di Impostazioni › Amministrazione, le finestre di dialogo per invito e reimpostazione della password compilano il campo **Indirizzo del server** con esso; in mancanza, con l'indirizzo usato dal browser dell'amministratore. L'amministratore può cambiare quell'indirizzo, e il browser verifica quindi che questo LibreFolio risponda lì. La [riga di comando](cli_tools.md) lo antepone ai link di invito e reimpostazione della password che stampa; in mancanza, stampa solo il percorso (`/invite#token=…`) e l'indirizzo devi aggiungerlo tu. Anche le email con un link ne hanno bisogno, senza alcun fallback all'indirizzo del browser: in mancanza, non viene inviata alcuna email di invito, alcuna email con il link di reimpostazione della password né alcuna email di password dimenticata ([Email](email.md)). Un indirizzo che contiene un nome utente o una password viene rifiutato, e LibreFolio funziona allora come se non fosse impostato. |
| `LIBREFOLIO_LOGIN_LIMIT` | `on` | Il limite sugli accessi non riusciti: `on` o `off`, senza distinzione tra maiuscole e minuscole; gli spazi attorno al valore non hanno importanza. `off` è solo per un'istanza di test: chiunque può allora provare password senza sosta, e ogni avvio registra un [avviso](configuration_security.md#startup-checks). A differenza di `LIBREFOLIO_REGISTRATION` e `LIBREFOLIO_PUBLIC_URL`, qualsiasi altro valore, inclusi `true`, `1` e `yes`, arresta il server all'avvio. Vedi [Accessi non riusciti](#login-limit). |

Un valore vuoto equivale a non impostato. Un valore errato di `LIBREFOLIO_REGISTRATION` o
`LIBREFOLIO_PUBLIC_URL` non arresta il server, a differenza delle [opzioni principali](configuration.md): LibreFolio resta sul lato sicuro e scrive un errore nel log la prima volta che ciascun
processo del server ha bisogno del valore: `Invalid account configuration`, con la variabile e il suo valore in
`problem` (un indirizzo che contiene una `@` non viene mostrato: potrebbe contenere un nome utente o una password) e
in `consequence` le conseguenze finché non lo correggi. Correggi il valore, poi riavvia:

| Valore errato | Cosa fa LibreFolio | `consequence` nel log |
| --- | --- | --- |
| `LIBREFOLIO_REGISTRATION` diverso dalle tre modalità | La registrazione è chiusa e l'impostazione globale resta bloccata | `registration stays closed until it is fixed` |
| `LIBREFOLIO_PUBLIC_URL` senza `http://` o `https://`, oppure con un nome utente o una password | Ignorato, come se non fosse impostato: la [riga di comando](cli_tools.md) stampa solo il percorso e dice perché sotto ciascun link, e le finestre di dialogo della scheda [Utenti](users.md) partono dall'indirizzo del browser. Non viene inviata alcuna email con un link e, quando l'email funziona, anche il log di avvio contiene un [avviso](configuration_security.md#startup-checks) ([Email](email.md)) | `links show the bare path until it is fixed` |

`LIBREFOLIO_LOGIN_LIMIT`, `LIBREFOLIO_MAX_USERS`, `LIBREFOLIO_DEFAULT_LANGUAGE`, `LIBREFOLIO_DEFAULT_CURRENCY` e `LIBREFOLIO_DEFAULT_TIMEZONE` sono le eccezioni: un
valore che LibreFolio non può usare **arresta il server all'avvio**, come fa un valore inutilizzabile
dell'[amministratore iniziale](#initial-admin). Per `LIBREFOLIO_LOGIN_LIMIT` vale qualsiasi valore diverso da `on` o `off`; per
`LIBREFOLIO_MAX_USERS`, qualsiasi valore diverso da un numero intero almeno pari a `1` (`0`, `abc`, `-3` e `1.5` arrestano il server);
per `LIBREFOLIO_DEFAULT_LANGUAGE`, qualsiasi valore diverso da `en`, `it`, `fr` o `es`; per `LIBREFOLIO_DEFAULT_CURRENCY`, qualsiasi valore diverso da un codice valuta conosciuto da LibreFolio; per `LIBREFOLIO_DEFAULT_TIMEZONE`, qualsiasi valore diverso da un nome di fuso orario IANA. L'errore è
nell'output della console del server (`docker compose logs librefolio` con Docker) e nomina la
variabile e il valore, ad esempio `LIBREFOLIO_LOGIN_LIMIT='yes': expected on or off` o
`LIBREFOLIO_MAX_USERS='abc': expected a whole number of at least 1`. Correggilo, poi
avvia di nuovo.

### 📏 Quando l'istanza è piena {: #user-limit }

Quando gli account attivi, gli inviti in sospeso, gli account in attesa della verifica email e un
[amministratore iniziale](#initial-admin) in attesa della sua configurazione raggiungono `LIBREFOLIO_MAX_USERS`:

- nessuno può registrarsi senza un invito, qualunque sia la modalità di [Registrazione](settings.md);
- un link di invito già inviato funziona ancora: il suo posto è stato conteggiato quando è stato creato;
- gli amministratori non possono creare inviti o riattivare account, tranne dalla
  [riga di comando](cli_tools.md): `user create`, `user invite` e `user activate` stampano un avviso,
  poi procedono. `user activate` non ne stampa nessuno per un account che occupa già il suo posto: uno
  in attesa della verifica email mentre il suo link è attivo, o l'amministratore iniziale in attesa
  della sua configurazione.

Un posto si libera quando un account viene disattivato o eliminato, quando un invito viene revocato o
scade, oppure quando scade il link di un account in attesa della verifica email (vedi
*Verifica email* in [Email](email.md)). Il primo account di una nuova istanza può sempre essere
creato.

### 📉 Quando il piano si riduce {: #user-limit-over }

Se gli account **attivi** superano `LIBREFOLIO_MAX_USERS` — hai abbassato il limite e riavviato, oppure hai
ripristinato un backup che contiene più utenti di quanti il limite consenta — l'istanza è *oltre il limite*. LibreFolio
non elimina nessuno; chiede a un amministratore di scegliere.

- **Chi è interessato**: solo `active > limit`. Con esattamente tanti account attivi quanti il limite, non succede
  nulla. Gli inviti e gli account in attesa della verifica occupano posti ma non danno mai inizio a questo stato.
- **Cosa vede un amministratore**: al primo accesso, prima di qualsiasi altra pagina, l'elenco degli account
  attivi. L'amministratore che sta scegliendo è selezionato e non può essere deselezionato. Ogni riga indica quanti
  broker l'account possiede **da solo**: quei broker restano, ma nessun altro può raggiungerli finché l'account non viene
  riattivato. Un contatore mostra quanti account sono scelti rispetto a quanti ne consente il limite.
- **Prima il backup completo**: la stessa pagina lo offre, così i dati possono essere portati via prima che qualcuno venga
  disattivato.
- **Cosa succede con «Disattiva gli altri e continua»**: gli account non scelti vengono **disattivati**, non
  eliminati: vengono disconnessi, non possono accedere e conservano tutti i loro dati. Puoi riattivarne uno in seguito quando si libera
  un posto ([Quando l'istanza è piena](#user-limit)). Gli inviti in sospeso vengono annullati, dal più recente,
  solo nella misura in cui gli account scelti hanno bisogno dei loro posti; la pagina dice quanti prima che tu confermi.
- **Cosa vedono tutti gli altri** finché la scelta non viene fatta: un messaggio che un amministratore deve scegliere chi
  mantiene l'accesso. Nessuno tranne un amministratore entra, e gli amministratori non vedono altro che questa scelta.
- **Un limite che LibreFolio non riesce a leggere** (`LIBREFOLIO_MAX_USERS=abc`, `0`) non dà mai inizio a questo stato: il
  server non si avvia finché non correggi il valore, quindi un errore di battitura non può escludere tutti.

Nessun passaggio speciale è necessario dopo un ripristino: gli account ripristinati vengono conteggiati allo stesso modo.

### 🚦 Accessi non riusciti {: #login-limit }

LibreFolio smette di controllare le password per un po' quando gli accessi continuano a fallire, così che nessuno possa provare
password su password finché una non funziona. Il limite è attivo a meno che tu non lo disattivi.

| Limite | Superato il limite |
| --- | --- |
| 10 accessi non riusciti ogni 15 minuti con lo stesso nome utente o indirizzo email, indipendentemente dal fatto che un account li abbia | Ogni accesso con quel nome utente o indirizzo email viene rifiutato, compresa la password corretta, finché il fallimento più vecchio non ha 15 minuti. |
| 50 accessi non riusciti ogni 15 minuti dallo stesso indirizzo, qualunque nome utente o indirizzo email usino; un indirizzo IPv6 viene conteggiato per il suo /64, il blocco che un abbonato di solito possiede. Non vengono conteggiati per gli accessi che arrivano attraverso un proxy di cui LibreFolio non si fida, su un indirizzo locale: vedi *Dietro un reverse proxy* sotto | Ogni accesso da quell'indirizzo viene rifiutato, per qualsiasi account, finché il fallimento più vecchio non ha 15 minuti. |

- **Cosa vede l'utente**: la pagina di accesso dice *Troppi tentativi di accesso: attendi qualche minuto e riprova.*
  L'attesa è di 15 minuti al massimo. La risposta è la stessa indipendentemente dal fatto che un account esista o no,
  quindi il limite non rivela a nessuno quali account esistono.
- **Cosa conta come fallimento**: una password errata, oppure un nome utente o indirizzo email che nessun account
  possiede. All'accesso, la password corretta di un account disattivato, o di uno ancora in attesa della
  verifica email, non conta né come fallimento né come successo.
- **Riprovare non allunga l'attesa**: un accesso rifiutato dal limite non viene conteggiato e
  la sua password non viene nemmeno controllata.
- **Un accesso riuscito** azzera i fallimenti del nome utente o indirizzo email usato, non quelli
  dell'indirizzo da cui è arrivato.
- **Il nome utente e l'indirizzo email contano separatamente**, anche per un solo account: chi tenta di indovinare
  la sua password ha 10 tentativi con il nome utente e 10 con l'indirizzo email ogni 15 minuti, sempre
  entro i 50 del proprio indirizzo. Le maiuscole da A a Z non contano: `Alice` e `alice` condividono un unico
  conteggio.
- **Anche la password attuale conta.** Una password attuale errata in **Cambia password**, o quando un
  utente cambia il proprio indirizzo email nella scheda Profilo ([Profilo](../user/settings/profile.md)),
  conta come un accesso non riuscito con il nome utente dell'account, dallo stesso indirizzo. Quindi 10 password attuali
  errate bloccano anche l'accesso con quel nome utente, e gli accessi non riusciti con il nome utente
  bloccano quei due controlli: **Cambia password** e la scheda Profilo dicono allora *Troppe password
  errate: attendi qualche minuto e riprova.* L'eliminazione del proprio account non chiede alcuna password:
  non c'è nulla da limitare.
- **Anche Invia di nuovo il link conta.** Nella pagina di accesso, un account in attesa della verifica
  email riceve **Invia di nuovo il link**, che controlla il nome utente o indirizzo email e la
  password come fa un accesso ([Verifica email](email_flows.md#verification)). Una password errata lì
  conta come un accesso non riuscito con quanto digitato, dallo stesso indirizzo; oltre il limite, viene
  rifiutata prima che la password sia controllata, e la pagina indica tra quanti minuti riprovare. La
  password corretta azzera i fallimenti di quanto digitato, come fa un accesso riuscito. I suoi limiti specifici
  si applicano comunque ([Limiti delle email di verifica](email_flows.md#verification-limits)).
- **Non soggetti a limite**: i link di invito e di reimpostazione della password. I loro token sono valori casuali lunghi
  che nessuno può indovinare, e un limite per indirizzo potrebbe rifiutarli a ogni utente dietro
  lo stesso router. **Password dimenticata?** non chiede alcuna password e ha limiti propri: vedi
  [Password dimenticate](email_flows.md#forgot-password).
- **Tenuti in memoria**, da ciascun processo del server: un riavvio dimentica ogni conteggio, il che consente anche a un utente
  che non può aspettare di rientrare subito. Con più processi del server (`./dev.py server --workers N`),
  ciascuno mantiene i propri conteggi, quindi i limiti sono N volte questi; l'immagine Docker ne esegue uno.
- **Dietro un reverse proxy**, l'indirizzo che conta è quello del visitatore, come lo legge LibreFolio.
  Comunica a LibreFolio il tuo proxy, elencandolo in `FORWARDED_ALLOW_IPS` o indicando l'header che
  imposta in `LIBREFOLIO_CLIENT_IP_HEADER`, come spiega
  [L'indirizzo del visitatore](connection_proxy.md#client-address). Fino ad allora, LibreFolio vede
  ogni visitatore con l'indirizzo del proxy, e ciò che accade dipende da dove si trova il proxy.
- **Un proxy di cui LibreFolio non si fida, su un indirizzo locale** (una rete Docker, la tua rete o
  la tua VPN), come un container proxy davanti all'immagine Docker, la configurazione abituale: LibreFolio
  esclude gli accessi attraverso di esso dal limite per indirizzo, così che 50 accessi non riusciti da
  chiunque non possano rifiutare tutti gli accessi. Il limite per nome utente o indirizzo email li conta comunque. Il log
  contiene un avviso per ciascun processo del server, la prima volta che una richiesta attraverso un tale proxy incontra un limite
  per indirizzo:
  `Requests come through a reverse proxy that LibreFolio does not trust: the limits per client address skip them. List the proxy in FORWARDED_ALLOW_IPS, or name the header it sets in LIBREFOLIO_CLIENT_IP_HEADER`.
- **Un proxy di cui LibreFolio non si fida, su un indirizzo pubblico**, come una CDN: ogni visitatore condivide
  l'indirizzo del proxy e il suo conteggio, quindi 50 accessi non riusciti da chiunque rifiutano ogni accesso attraverso
  il proxy, comprese le password corrette, per un massimo di 15 minuti.

**Disattivazione.** `LIBREFOLIO_LOGIN_LIMIT=off`, senza distinzione tra maiuscole e minuscole, è pensato per un'istanza di test, i cui
test automatizzati accedono di proposito in modo errato: nulla viene conteggiato e nulla viene rifiutato. Ogni avvio
registra allora un avviso, con `accounts.login_limit` in `check`:
`LIBREFOLIO_LOGIN_LIMIT=off: failed sign-ins are not limited; turn it back on unless this is a test instance`.
Lo stesso controllo, su richiesta, si trova nella scheda **Sicurezza** di **Impostazioni › Amministrazione**: un avviso,
conteggiato nel numero sulla scheda, finché il limite non torna attivo (vedi «Sicurezza» in
[Impostazioni globali](settings.md)).
Rimuovi la variabile, oppure impostala su `on`, per riattivare il limite al prossimo avvio. Qualsiasi altro
valore arresta il server all'avvio: vedi [Account e registrazioni](#accounts).

### 👑 L'amministratore iniziale {: #initial-admin }

LibreFolio può creare da solo l'amministratore di una nuova istanza, al suo primo avvio, per l'indirizzo che gli fornisci: nessuno può registrarsi prima e prendere il suo posto. È pensato per installazioni realizzate con
uno script o Docker Compose. Senza queste variabili nulla cambia, e il primo account
registrato diventa l'amministratore ([Chi può registrarsi](settings.md)).

| Variabile | Predefinito | Cosa fa |
| --- | --- | --- |
| `LIBREFOLIO_ADMIN_EMAIL` | _non impostato_ | L'indirizzo email dell'amministratore. Impostarlo attiva l'amministratore iniziale. |
| `LIBREFOLIO_ADMIN_USERNAME` | `admin` | Il nome utente dell'amministratore: da 3 a 50 caratteri, senza `@`, come alla registrazione. |
| `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` | _non impostato_ | Opzionale: il token del link di configurazione, per uno script che consegna il link stesso. Da 32 a 200 caratteri, solo lettere, cifre e `-` `.` `_` `~`, poiché viaggia in un link: l'output di `openssl rand -hex 32`, per esempio. `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` lo legge invece da un file: vedi [Segreti](configuration_secrets.md#secrets). Non impostato: LibreFolio genera il token. |

Un valore vuoto equivale a non impostato. Gli spazi attorno all'email e al nome utente non hanno importanza; il token
viene usato esattamente come scritto, quindi uno spazio al suo interno, anche alla fine, lo rende inutilizzabile.

Al primo avvio di un'istanza **senza alcun account**, LibreFolio:

1. crea l'amministratore, non ancora attivo, con una password casuale che nessuno conosce: nessuno può ancora accedere con essa;
2. imposta l'[impostazione globale](settings.md) **Registrazione** su **Su invito**;
   `LIBREFOLIO_REGISTRATION`, quando impostata, decide comunque;
3. emette un **link di configurazione**, `/setup#token=…`, che funziona una sola volta, per 72 ore. Apre la
   pagina di configurazione dell'istanza, dove l'amministratore sceglie la password ed effettua l'accesso.

Mentre l'amministratore attende, nessuno può registrarsi come primo account, e l'amministratore
occupa un posto di `LIBREFOLIO_MAX_USERS`. Chi consegna il link dipende dal token:

- **Con `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`**, chi lo ha scelto: il link è l'indirizzo
  dell'istanza seguito da `/setup#token=` e dal token. LibreFolio non lo registra né lo invia via email.
- **Senza di esso**, LibreFolio genera il token e consegna il link da sé:
    - scrive il link **una sola volta** nel proprio log, come avviso:
      `Setup link of the initial administrator, single use: open it to choose the password`, con
      il link in `link` (con Docker: `docker compose logs librefolio`). Il link è l'indirizzo
      completo quando `LIBREFOLIO_PUBLIC_URL` è impostato; altrimenti è il percorso, e `note` ti chiede di
      anteporgli l'indirizzo del tuo server;
    - invia il link via email a `LIBREFOLIO_ADMIN_EMAIL` quando l'email funziona, cioè con un server SMTP
      configurato ([Email](email.md)) e `LIBREFOLIO_PUBLIC_URL` impostato. L'email è nella lingua
      predefinita dell'istanza e viene inviata quando il server è avviato, così un server di posta lento non ritarda mai
      l'avvio. Se non può essere inviata, il log contiene `Setup link of the initial administrator not emailed`,
      con il motivo, e il link nel log funziona comunque.

Un riavvio mentre l'amministratore attende non emette nulla di nuovo e non scrive di nuovo il link nel log. Una volta che nessun link funziona più, ogni avvio registra un avviso:
`The initial administrator's setup link has expired: run ./dev.py user setup-link…` quando il link è scaduto, oppure
`The initial administrator's setup link was withdrawn (cancelled, or its address changed): run ./dev.py user setup-link…`
quando è stato [annullato](users.md#cancel-setup) o l'indirizzo dell'amministratore è cambiato. Quel comando
stampa un nuovo link ([Un nuovo link di configurazione](cli_tools.md)). Un nuovo valore di
`LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` fornisce anch'esso un nuovo link, al prossimo avvio.

Su un'istanza che ha già account e nessun amministratore in attesa, le variabili non creano
nulla: ogni avvio registra `LIBREFOLIO_ADMIN_* ignored: this instance already has accounts`. Lo stesso
vale una volta completata la configurazione.

Un valore che LibreFolio non può usare **arresta il server all'avvio**, su qualsiasi istanza, compresa una che ha già
account:

- `LIBREFOLIO_ADMIN_USERNAME` o `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` impostati senza
  `LIBREFOLIO_ADMIN_EMAIL`;
- un'email che non è un indirizzo;
- un nome utente più corto di 3 o più lungo di 50 caratteri, o che contiene una `@`: l'accesso interpreta un
  nome con `@` come indirizzo email, e l'amministratore accede comunque con l'indirizzo di
  `LIBREFOLIO_ADMIN_EMAIL`;
- un token più corto di 32 o più lungo di 200 caratteri, o con un carattere diverso da lettere,
  cifre e `-` `.` `_` `~`, spazio incluso;
- un `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` che non riesce a fornire il token
  ([Segreti nei file](configuration_secrets.md#secret-files)).

L'errore è nell'output della console del server (`docker compose logs librefolio` con Docker): nomina
la variabile, mai il token. Correggi il valore, poi avvia di nuovo.

---

## 🥇 L'ordine dei provider di prezzi nella ricerca {: #provider-order }

Quando crei un asset, la ricerca interroga contemporaneamente ogni provider di prezzi ed elenca i risultati provider per provider. Ogni provider dichiara la sua posizione: il suo livello, **premium** per una fonte di cui
un'istanza si fa garante, come dati con licenza, o **community**, il valore predefinito; e la sua priorità all'interno
del livello. Quando è disponibile almeno un provider premium, i suoi risultati vengono per primi. Nessuno dei
provider inclusi in LibreFolio è premium, quindi senza uno la ricerca mantiene il suo ordine.

| Variabile | Predefinito | Cosa fa |
| --- | --- | --- |
| `LIBREFOLIO_ASSET_PROVIDERS_PREMIUM` | _non impostato_ | I provider da considerare premium, per codice, separati da virgole, come `yfinance,justetf`: esattamente questi, qualunque cosa dichiarino. Non impostato: ciò che dichiara ciascun provider. |
| `LIBREFOLIO_ASSET_PROVIDERS_ORDER` | _non impostato_ | I provider da elencare per primi, in questo ordine, per codice, separati da virgole; gli altri seguono nel loro ordine dichiarato. I provider premium vengono comunque prima degli altri. Non impostato: ciò che dichiara ciascun provider. |

- I codici dei provider inclusi in LibreFolio sono `yfinance`, `justetf`, `borsa_italiana`,
  `css_scraper` e `scheduled_investment`; un provider che aggiungi ha i propri. La distinzione tra maiuscole e minuscole e gli spazi attorno ai codici non hanno importanza.
- Un codice che nessun provider ha viene ignorato, e il server lo registra una volta.
- Le impostazioni si applicano alla ricerca successiva, senza riavvio: LibreFolio le legge a ogni ricerca.

---

## 🔎 Opzionale: ricerca web per nuovi asset {: #optional-web-search-for-new-assets }

Quando crei un asset, anche dalla procedura guidata di importazione del broker, e la ricerca propria di un provider non trova
nulla, LibreFolio può trovare la pagina dell'asset con una ricerca web tramite la
libreria [`ddgs`](https://pypi.org/project/ddgs/). È attiva per impostazione predefinita e non viene mai usata per gli aggiornamenti
dei prezzi. Tutte queste variabili sono opzionali: togli il commento da una riga di `.env.example` per modificarne una.

| Variabile | Predefinito | Cosa fa |
| --- | --- | --- |
| `LIBREFOLIO_WEB_LINK_FINDER_ENABLED` | `1` | `0` disattiva la ricerca web; la ricerca propria dei provider continua a funzionare. |
| `LIBREFOLIO_WEB_LINK_FINDER_ENGINE` | `ddgs` | `ddgs` non richiede configurazione. `apikey` è riservato a un servizio di ricerca a pagamento e non restituisce ancora risultati. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_REGION` | `wt-wt` | Regione di ricerca. `wt-wt` (mondiale) evita che i siti nazionali come Borsa Italiana vengano retrocessi. Esempi: `it-it`, `us-en`. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND` | `auto` | Motori che `ddgs` interroga: `auto` li alterna per la copertura più ampia; un elenco come `google,bing,duckduckgo` dà risultati più stabili. |
| `LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT` | `6` | Limite di tempo di una ricerca, in secondi: almeno `1`. Qualsiasi altro valore fa usare il valore predefinito. |
| `LIBREFOLIO_WEB_LINK_FINDER_MAX` | `5` | Numero massimo di link restituiti da una ricerca: un numero intero, almeno `1`. Qualsiasi altro valore fa usare il valore predefinito. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | _vuoto_ | Chiave per il motore `apikey`. `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` la legge invece da un file: vedi [Segreti](configuration_secrets.md#secrets). |

??? tip "🔁 I risultati cambiano tra un tentativo e l'altro — quando un asset noto a volte non viene trovato"

    Con `auto`, ogni ricerca può raggiungere motori diversi, quindi la stessa query può andare meglio o peggio
    da un tentativo all'altro. Riprova una volta, oppure imposta
    `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND=google,bing,duckduckgo`.

---

## 🔗 Correlati

- 📄 **[Configurazione](configuration.md)** — Creare il file `.env`, opzioni principali, parametri impostati dagli strumenti, …
- 📄 **[Configurazione: segreti e impostazioni dei plugin](configuration_secrets.md)** — Segreti, impostazioni dei plugin
- 📄 **[Configurazione: controlli e protezioni](configuration_security.md)** — Controlli all'avvio, protezioni del browser, arresto del server
