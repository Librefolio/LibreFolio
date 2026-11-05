# 👥 Utenti e inviti

La scheda **Utenti** di **Impostazioni › Amministrazione** è dove un amministratore gestisce gli account dell'istanza: chi può accedere, chi è amministratore e chi è invitato a unirsi. Funziona allo stesso modo in ogni installazione.

---

## 🧭 Apri la scheda {: #open-the-tab }

Apri **Impostazioni** (icona a forma di ingranaggio nella barra laterale), poi **Amministrazione** e la sua scheda **Utenti**, accanto a **Impostazioni globali**. Solo gli amministratori hanno questa scheda: tutti gli altri non la vedono.

La scheda ha tre parti: i posti occupati, in alto; gli **Account**; gli **Inviti aperti**. Dopo ogni modifica, la scheda ricarica i suoi elenchi, così mostra sempre ciò che il server contiene.

!!! tip "💻 Su un server senza browser"

    La [riga di comando](cli_tools.md) fa anche la maggior parte di questo: `user invite`, `user reset-link`,
    `user deactivate` e `user activate`, `user promote` e `user demote`, `user reset-onboarding`.
    Può anche superare il limite utenti. Non può eliminare un account né revocare un invito.

---

## 📏 Posti {: #places }

L'intestazione conta i posti occupati: **3 / 10 account** quando l'istanza ha un limite utenti,
**3 account** quando non ne ha. Gli account attivi e gli inviti aperti occupano un posto; lo occupa anche un
account [in attesa della propria email](#waiting) finché il suo link è valido, e anche un
amministratore iniziale ancora [in attesa del proprio link di configurazione](#pending-setup); gli account disattivati
no. Il limite si imposta sul server con `LIBREFOLIO_MAX_USERS`: vedi «Quando l'istanza è piena» in
[Variabili d'ambiente](configuration_accounts.md#user-limit).

- 🚫 Quando l'istanza è piena, un banner dice *L'istanza è piena: nessun nuovo invito finché non
  disattivi o elimini un account, oppure revochi un invito.* **Invita** è disattivato, e un account disattivato non può essere riattivato finché
  non si libera un posto, a meno che non sia [in attesa della propria email](#waiting) con un link valido.
- 🔒 **Invita** è disattivato anche quando la registrazione è chiusa. Se l'impostazione globale **Registrazione** è
  **Chiusa**, la scheda ti dice di cambiarla lì ([Impostazioni globali](settings.md), «Chi può registrarsi»). Se è il server a chiuderla con `LIBREFOLIO_REGISTRATION`, la scheda indica il nome della variabile: solo la
  configurazione del server può riaprirla.

### 🚪 Chi può registrarsi {: #registration }

**Chi può registrarsi**, accanto a **Invita**, è l'impostazione globale **Registrazione**, qui come in
[Impostazioni globali](settings.md) («Chi può registrarsi»): **Aperta**, **Su invito** o **Chiusa**. Una scelta viene
salvata subito, senza pulsante **Salva**, e la scheda rilegge l'impostazione. Solo **Aperta** ti chiede prima una
conferma, perché lascia entrare chiunque raggiunga la pagina di accesso; se annulli, la modalità resta com'era.
Se è il server a impostare la modalità con `LIBREFOLIO_REGISTRATION`, il selettore è disattivato e la scheda indica il nome della
variabile.

---

## 👤 Account {: #accounts }

Una riga per account, dal più vecchio al più recente: l'avatar dell'account, il nome utente con i relativi badge, poi
l'email e la data di creazione. L'avatar è l'immagine scelta per l'account dal suo utente (vedi
[Profilo](../user/settings/profile.md)); un account senza avatar mostra la prima lettera del suo
nome utente in un cerchio semplice.

| Badge | Significato |
|---|---|
| **Tu** | Il tuo account |
| **Admin** | Un amministratore: gestisce l'istanza, le sue impostazioni, i suoi utenti e i suoi inviti |
| **Disattivato** | L'account non può accedere e non occupa alcun posto. Un account [in attesa della propria email](#waiting) ha un badge proprio, sotto |
| **In attesa di configurazione** | L'[amministratore iniziale](configuration_accounts.md#initial-admin), non ancora attivo: nessuno ha usato il suo link di configurazione, né ha configurato l'account in altro modo. Mostrato al posto di **Disattivato**: vedi [In attesa del proprio link di configurazione](#pending-setup) |
| **In attesa di verifica** | Un account che non ha ancora aperto il link di verifica che LibreFolio ha inviato al suo indirizzo, anche dopo la scadenza di quel link. Non può accedere e occupa un posto finché il suo link è valido. Mostrato al posto di **Disattivato**: vedi [Account in attesa della propria email](#waiting) |

Fai clic su una riga per aprire le sue azioni, e di nuovo per chiuderle. La tua riga non ne ha: dice *Questo è
il tuo account. Gestiscilo da:* con un link a **Profilo**, la scheda in cui modifichi i tuoi dati o
[elimini il tuo account](../user/settings/profile.md).

### ⚙️ Cosa fa ciascuna azione {: #actions }

| Azione | Cosa fa | Chiede conferma |
|---|---|---|
| **Disattiva** | L'account non può più accedere ed è disconnesso da ogni dispositivo. I suoi broker e le sue transazioni restano, e il suo posto viene liberato. Mostrato per un account attivo | ✅ |
| **Riattiva** | L'account può accedere di nuovo, con i suoi dati com'erano; le sue vecchie sessioni non tornano. Occupa di nuovo un posto, quindi ne serve uno libero, a meno che l'account non sia [in attesa della propria email](#waiting) con un link valido: il suo posto è già conteggiato. Mostrato per un account disattivato, compreso uno in attesa della propria email, ma non per l'amministratore iniziale [in attesa del proprio link di configurazione](#pending-setup) | — |
| **Annulla link di configurazione** | Il link di configurazione dell'amministratore iniziale [in attesa della propria configurazione](#pending-setup) smette di funzionare, compreso quello già consegnato; l'account continua ad attendere un nuovo link. Mostrato solo per quell'account, al posto di **Riattiva**: vedi [Annulla il suo link di configurazione](#cancel-setup) | ✅ |
| **Rendi amministratore** | L'account gestisce anch'esso l'istanza: impostazioni, utenti e inviti | ✅ |
| **Rimuovi amministratore** | L'account resta, come utente normale, ed è disconnesso da ogni dispositivo | ✅ |
| **Link di reimpostazione password** | Un link per scegliere una nuova password: vedi [Link di reimpostazione password](#reset-links) | La sua finestra di dialogo |
| **Disconnetti ovunque** | L'account è disconnesso da ogni dispositivo: il suo utente accede di nuovo su ciascuno. L'account resta attivo | ✅ |
| **Riavvia le guide** | La prossima volta che il suo utente apre LibreFolio, la [Configurazione iniziale](../user/getting-started.md#welcome-setup) e ogni guida ricominciano, come per un nuovo account. I suoi dati e le sue preferenze restano | ✅ |
| **Elimina** | Rimuove definitivamente l'account: vedi [Elimina un account](#delete) | La sua finestra di dialogo |

### 🔒 Quando un'azione è disattivata {: #action-off }

LibreFolio disattiva le azioni che sa che il server rifiuterebbe, e spiega perché sotto i pulsanti:

| Il pannello dice | Disattivato | Cosa puoi fare |
|---|---|---|
| *È l'unico amministratore attivo: non può essere disattivato né retrocesso.* | **Disattiva**, **Rimuovi amministratore** | Rendi prima amministratore un altro account |
| *L'istanza è piena: libera un posto per riattivarlo.* | **Riattiva** | Disattiva o elimina un altro account, oppure revoca un invito; `user activate` della riga di comando supera il limite |
| *Un amministratore deve essere retrocesso prima di poter essere eliminato.* | **Elimina** | Prima **Rimuovi amministratore**, poi **Elimina** |
| *È in attesa della propria configurazione: mantiene il suo ruolo fino ad allora.* | **Rimuovi amministratore**, per l'amministratore iniziale [in attesa del proprio link di configurazione](#pending-setup) | [Annulla il suo link di configurazione](#cancel-setup), oppure **Elimina** l'account: non richiede prima **Rimuovi amministratore** |
| *Questo account amministratore si attiva tramite il suo link di configurazione. Se il link va perso, esegui `dev.py user setup-link` sul server.* | Nessun **Riattiva**: al suo posto **Annulla link di configurazione** | Fai usare il suo link di configurazione, oppure forniscine uno nuovo: vedi [In attesa del proprio link di configurazione](#pending-setup) |

- 👑 L'istanza mantiene sempre un amministratore attivo. La tua riga non ha azioni, quindi per lasciare
  il ruolo: rendi amministratore un altro account, poi chiedi di rimuoverti i privilegi.

### ⏳ Account in attesa della propria email {: #waiting }

Con **Richiedi verifica email** attivo ([Impostazioni globali](settings.md)), un nuovo account resta in attesa finché
il suo proprietario non conferma l'indirizzo con il link che LibreFolio gli invia via email. Fino ad allora:

- la sua riga mostra **In attesa di verifica** invece di **Disattivato**, anche dopo la scadenza del suo link. Passa
  il mouse sul badge per il suggerimento, oppure apri la riga, dove sotto i pulsanti si legge: *Il suo
  proprietario non ha ancora aperto il link di verifica: l'accesso propone di inviarne uno nuovo. Riattiva
  fa entrare subito l'account, senza l'email.* Un account disattivato mentre è in attesa (vedi
  l'ultimo punto) smette di attendere, e la sua riga mostra di nuovo **Disattivato**;
- occupa un posto finché il suo link è valido, cioè per 24 ore dopo l'invio dell'ultimo link;
- **Riattiva** lo fa entrare subito: può accedere e i link già inviati smettono di funzionare. Finché
  il suo link è valido, questo non occupa un posto aggiuntivo, poiché il suo posto è già conteggiato: **Riattiva**
  funziona anche su un'istanza piena, e così `user activate` sulla
  [riga di comando](cli_tools.md), senza un avviso di limite. Una volta scaduto il link, riattivarlo
  richiede un posto libero, come per qualsiasi account disattivato;
- **Elimina** lo rimuove, come qualsiasi account. Questa scheda non offre **Disattiva** per un account che
  non è attivo; `user deactivate` sulla riga di comando, o l'API amministratore
  (`PATCH /api/v1/users/{id}` con `is_active: false`), lo mantiene ma termina l'attesa: i suoi link smettono
  di funzionare, il suo posto è libero e può accedere solo dopo la riattivazione.

Come funziona la verifica e quali sono i suoi limiti: [Verifica email](email_flows.md#verification).

### 👑 In attesa del proprio link di configurazione {: #pending-setup }

Quando LibreFolio crea l'amministratore di `LIBREFOLIO_ADMIN_EMAIL` al primo avvio, l'account resta in attesa,
non ancora attivo, finché qualcuno non apre il suo link di configurazione e sceglie la password, oppure lo configura
in altro modo (sotto): vedi
[L'amministratore iniziale](configuration_accounts.md#initial-admin). Fino ad allora:

- la sua riga mostra **In attesa di configurazione** invece di **Disattivato**, anche dopo la scadenza del suo link o
  dopo che è stato [annullato](#cancel-setup);
- occupa un posto, come un account attivo;
- il suo pannello non ha **Riattiva**: nessuno conosce la sua password, e attivarlo farebbe smettere di funzionare anche il suo link di configurazione. Al suo posto c'è **Annulla link di configurazione** ([sotto](#cancel-setup)). Sotto
  i pulsanti, il pannello dice: *Questo account amministratore si attiva tramite il suo link di configurazione. Se
  il link va perso, esegui `dev.py user setup-link` sul server.*;
- **Rimuovi amministratore** è disattivato, con la motivazione *È in attesa della propria configurazione: mantiene il suo ruolo fino
  ad allora.* Per bloccare il link già consegnato, annullalo; per bloccare del tutto l'account, eliminalo;
- **Elimina** non richiede prima **Rimuovi amministratore**, a differenza di qualsiasi altro amministratore;
- le altre azioni sono quelle di qualsiasi account disattivato.

Il server rifiuta di attivarlo, o di rimuovergli i diritti di amministratore: `PATCH /api/v1/users/{id}`
con `is_active: true`, o con `is_superuser: false`, risponde `409`, con il codice `PENDING_SETUP`,
e non cambia nulla. Se una tale modifica arriva comunque al server, per esempio da un elenco caricato
prima, la scheda spiega il motivo invece di un errore generico: *Questo amministratore è in attesa della propria configurazione: qui non può
essere né riattivato né retrocesso.* `GET /api/v1/users` contrassegna l'account con
`pending_setup: true`.

Questa versione non ha un pulsante per un nuovo link di configurazione: sul server, `user setup-link` ne stampa uno (vedi
«Un nuovo link di configurazione per l'amministratore iniziale» in [Strumenti da riga di comando](cli_tools.md)). Una volta usato il link, l'account è
attivo, come qualsiasi altro.

L'account smette di attendere anche quando viene configurato in altro modo, senza il suo link:

- **attivato sul server** con `user activate`: la riga di comando non lo rifiuta, a differenza di
  questa scheda, e non stampa alcun avviso di limite, poiché l'account occupa già il suo posto. La sua password
  è ancora quella che nessuno conosce, finché `user reset` o un link di reimpostazione non gliene assegna una;
- **con una password assegnata**, con `user reset` sul server, o con un
  [link di reimpostazione password](#reset-links) una volta usato: uno che crei con
  **Link di reimpostazione password** nel suo pannello, o uno che stampa `user reset-link`. L'account resta inattivo
  finché non viene attivato.

Da quel momento, ogni link di configurazione che aveva smette di funzionare: la pagina di configurazione dice *Questo link è stato
ritirato.*, e `user setup-link` non trova alcun amministratore in attesa. La scheda lo mostra come qualsiasi altro
account: **Disattivato** finché non è attivo, con **Riattiva**, e `GET /api/v1/users` lo contrassegna
con `pending_setup: false`. Come qualsiasi account disattivato, allora non occupa alcun posto, quindi **Riattiva**
ne richiede uno libero. Un link di reimpostazione che nessuno usa lo lascia in attesa, e così anche
[annullare il suo link di configurazione](#cancel-setup).

### 🚫 Annulla il suo link di configurazione {: #cancel-setup }

Annulla il link di configurazione dell'amministratore iniziale quando è finito alla persona sbagliata, o quando qualcun
altro potrebbe averlo visto, per esempio in un'email inoltrata o nel log del server:

1. Apri la riga dell'account **In attesa di configurazione** e fai clic su **Annulla link di configurazione**.
2. La finestra di dialogo chiede *Annullare il link di configurazione di {username}?* e spiega: *Il link già consegnato
   smette di funzionare. L'account continua ad attendere la propria configurazione: un nuovo link arriva da «dev.py user
   setup-link» sul server.*
3. Fai clic su **Annulla il link**. Un messaggio conferma: *Il link di configurazione di {username} non funziona più.*

Cosa succede:

- 🔗 ogni link di configurazione dell'account smette di funzionare, compreso quello consegnato: chi lo apre
  riceve *Questo link è stato ritirato.* e non può configurare l'account;
- ⏳ l'account resta in attesa: la sua riga mostra ancora **In attesa di configurazione**, mantiene il suo posto e
  qui non può ancora essere riattivato;
- 🔁 per far entrare l'amministratore, fornisci un nuovo link: sul server, `user setup-link` ne stampa uno (vedi
  «Un nuovo link di configurazione per l'amministratore iniziale» in [Strumenti da riga di comando](cli_tools.md))). Riavviare il server con lo stesso
  `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` non produce un nuovo link, poiché l'istanza ha già visto quel
  token: ogni avvio registra un avviso che il link di configurazione è stato ritirato, e chiede di eseguire
  `dev.py user setup-link`, oppure di impostare un nuovo token.

Sul server, `user deactivate` su questo account annulla il suo link allo stesso modo.

Se l'amministratore ha completato la propria configurazione dopo il caricamento del tuo elenco, non c'è più nulla da
annullare: LibreFolio non cambia nulla e dice *Questo amministratore ha completato la propria configurazione nel
frattempo: nulla è stato modificato.* La scheda si ricarica, e la riga ora mostra un amministratore attivo,
con **Disattiva** al posto di **Annulla link di configurazione**. L'account resta attivo e il suo proprietario
ha effettuato l'accesso.

Per rimuovere invece l'account, fai clic su **Elimina** ([Elimina un account](#delete)), senza prima
**Rimuovi amministratore**. L'account viene eliminato insieme ai suoi link di configurazione, il suo posto viene liberato e
nessuno attende più una configurazione: `user setup-link` non trova nessuno, e le variabili `LIBREFOLIO_ADMIN_*`
non creano nulla agli avvii successivi, poiché l'istanza ha degli account. Se anche in questo caso la configurazione è stata
completata nel frattempo, non viene eliminato nulla: la finestra di dialogo dice *Un amministratore deve essere
retrocesso prima di poter essere eliminato.*, poiché l'account ora è un amministratore attivo.

### 🔤 Nomi utente con una @ {: #usernames-with-at }

Dalla versione 1.3, un nuovo nome utente non può contenere `@`: all'accesso, LibreFolio interpreta qualsiasi cosa con un
`@` come indirizzo email. La registrazione, un cambio di nome utente nel Profilo e `user create` sulla
[riga di comando](cli_tools.md) lo rifiutano, e un `LIBREFOLIO_ADMIN_USERNAME` con un `@` blocca il
server all'avvio («L'amministratore iniziale» in [Variabili d'ambiente](configuration_accounts.md#initial-admin)).
Spazi, lettere accentate e segni come `.`, `_`, `-` o `+` vanno ancora bene.

Un account creato prima della versione 1.3 può averne uno, per esempio `anna@example.com` come nome utente:

- 🏷️ il nome utente resta com'è: nulla lo rinomina. Il suo utente può cambiarlo nel proprio
  [Profilo](../user/settings/profile.md), con un nome senza `@`;
- 🔑 l'account accede con il proprio indirizzo email, poiché ogni account ne ha uno. Il nome utente in sé
  funziona solo finché nessun account lo ha come indirizzo email: digitato all'accesso, un indirizzo individua l'account che lo possiede;
- 📧 nessun altro account può prendere quel nome utente come proprio indirizzo email, in qualsiasi combinazione di maiuscole: la registrazione,
  il Profilo, `user create` e `user set-email` lo rifiutano con *Email già registrata*. L'account
  stesso può prenderlo come proprio indirizzo.

---

## ✉️ Inviti {: #invitations }

Per invitare qualcuno:

1. Fai clic su **Invita**.
2. Facoltativamente, scrivi il suo indirizzo in **Email (facoltativa)**. È solo una nota su a chi è
   destinato l'invito: il link funziona per chiunque lo apra. L'elenco degli inviti lo mostra, e
   il modulo di registrazione parte da quello, dove la persona può cambiarlo.
3. Seleziona **Amministratore** se il nuovo account deve gestire l'istanza.
4. Fai clic su **Crea il link**: *Condividi questo link: funziona una sola volta, per 7 giorni.* Controlla
   l'[indirizzo del server](#server-address), fai clic su **Copia** e invia tu stesso il link, tramite messaggio o
   email, oppure lascia che sia LibreFolio a inviarlo via email: [Invia via email](#send-by-email).
5. Fai clic su **Fatto**: l'invito si aggiunge agli **Inviti aperti**.

La persona apre il link e crea il proprio account con il nome utente, l'email e la password che
sceglie: [Per iniziare](../user/getting-started.md) mostra ciò che vede.

- 🔗 Il link viene mostrato una sola volta, quando lo crei. Se va perso, revoca l'invito e
  creane uno nuovo.
- 📏 Un invito occupa un posto dal momento in cui lo crei finché non viene usato, revocato o non
  scade; l'account che crea occupa poi quel posto.
- 🔤 Un indirizzo email appartiene a un solo account, indipendentemente dalle maiuscole (`Anna@example.com` è
  `anna@example.com`), ma solo le lettere dalla A alla Z vengono confrontate in questo modo: `Émile@example.com` e
  `émile@example.com` sono due indirizzi diversi.

### 📋 Inviti aperti {: #open-invitations }

Gli inviti che nessuno ha ancora usato, dal più vecchio al più recente: l'email (oppure *Nessuna email*), un badge **Admin**
quando l'invito crea un amministratore, e quando è stato creato e quando scade. Un invito
esce dall'elenco una volta usato, revocato o scaduto.

**Revoca** ritira un invito in qualsiasi momento, dopo una conferma: il link smette subito di funzionare
e il suo posto viene liberato.

---

## 🔑 Link di reimpostazione password {: #reset-links }

Quando qualcuno ha dimenticato la password, inviagli un link per sceglierne una nuova da solo. Con l'email,
può anche richiederne uno dalla pagina di accesso: vedi [Password dimenticate](email_flows.md#forgot-password).

1. Apri la sua riga e fai clic su **Link di reimpostazione password**.
2. La finestra di dialogo spiega: *Un link monouso per impostare una nuova password, valido 30 minuti. I link
   creati prima per questo account smettono di funzionare.* Fai clic su **Crea il link**.
3. Controlla l'[indirizzo del server](#server-address), fai clic su **Copia** e invia il link, oppure fai clic
   su **Invia via email** ([Invia via email](#send-by-email)); poi fai clic su **Fatto**.

- ⏱️ Il link funziona una sola volta, per 30 minuti, e funziona solo il link più recente di un account.
- 🔒 Smette inoltre di funzionare non appena la persona cambia la propria password o il proprio indirizzo email, oppure esegui
  `user reset` o `user set-email` sulla [riga di comando](cli_tools.md).
- 🚪 Creare il link non disconnette nessuno. Una volta che la persona imposta la nuova password, il suo account viene
  disconnesso da ogni dispositivo.
- 🔗 Il link viene mostrato una sola volta: se va perso, creane uno nuovo.

Ciò che vede la persona è in [Per iniziare](../user/getting-started.md).

---

## 🌐 L'indirizzo del server di un link {: #server-address }

I link di invito e di reimpostazione password vengono mostrati nello stesso pannello:

- **Indirizzo del server**: da dove inizia il link. Viene compilato con `LIBREFOLIO_PUBLIC_URL` quando è
  il server a impostarlo, altrimenti con l'indirizzo che il tuo browser sta usando ora. *Cambialo se i tuoi utenti
  raggiungono LibreFolio a un altro indirizzo*: per esempio, sei su `http://192.168.1.10:6040` a
  casa, mentre i tuoi utenti passano da `https://librefolio.example.com`.
- **Link**: l'indirizzo del server seguito dal percorso proprio del link. **Copia** lo mette negli appunti;
  se il browser rifiuta, il link viene selezionato così puoi copiarlo a mano. *Valido fino a …*
  ne indica la scadenza.

Quando cambi l'indirizzo, il tuo browser verifica, mezzo secondo dopo che smetti di digitare, che
**questa** istanza risponda lì, e non un server qualsiasi: carica una piccola immagine da
`<address>/api/v1/auth/address-probe.png?nonce=…`, che è 1×1 quando risponde questa istanza e 2×1
quando ne risponde un'altra. L'indirizzo compilato in sé non viene
verificato.

| Messaggio | Cosa significa |
|---|---|
| *Verifica in corso che questo LibreFolio risponda a questo indirizzo…* | La verifica è in corso |
| *Questa istanza risponde a questo indirizzo.* | Il link raggiunge questo LibreFolio |
| *Qualcosa risponde a questo indirizzo, ma non questa istanza: controllalo prima di condividere.* | Lì risponde un altro LibreFolio: probabilmente non è l'indirizzo che intendevi |
| *Non è stato possibile verificare questo indirizzo da questo browser: puoi comunque condividere il link.* | Il browser non è riuscito a caricare l'immagine. Lì non risponde nulla (un indirizzo errato o chiuso, oppure nessuna risposta entro 8 secondi); una pagina aperta con `https://` verifica un indirizzo `http://`, che il browser blocca; una pagina su un indirizzo pubblico verifica un indirizzo locale, che alcuni browser bloccano o consentono solo dopo aver chiesto il tuo permesso; un'istanza bloccata non serve l'immagine; oppure risponde un LibreFolio più vecchio, che non può essere verificato |
| *Inserisci un indirizzo che inizi con http:// o https://, senza ? o #.* | Non è un indirizzo: **Copia** resta disattivato finché non lo correggi |

Qualunque sia il risultato, tranne un indirizzo che non è tale, puoi copiare il link: la verifica è solo un
consiglio. Tornando all'indirizzo compilato, il messaggio scompare. Come funziona la verifica:
[Sonda dell'indirizzo](../developer/architecture/security.md#address-probe), per gli sviluppatori.

!!! tip "🌐 Imposta l'indirizzo una volta sola"

    Imposta `LIBREFOLIO_PUBLIC_URL` sull'indirizzo che i tuoi utenti aprono, e il pannello parte da lì: vedi
    «Account e registrazioni» in [Variabili d'ambiente](configuration_accounts.md#accounts). Anche la
    [riga di comando](cli_tools.md) lo antepone ai link che stampa.

---

## 📧 Invia via email {: #send-by-email }

Finché l'istanza può inviare email con un link — email **Pronta** e `LIBREFOLIO_PUBLIC_URL` impostato su
un indirizzo che LibreFolio può usare ([Email con un link](email_flows.md#public-url)) — entrambe le finestre di dialogo dei link hanno
**Invia via email** sotto il link:

- **Un invito**: **Invia a** parte dall'indirizzo scritto nell'invito, e puoi
  cambiarlo. Se lo lasci vuoto, l'email va all'indirizzo scritto nell'invito; se non ce n'è uno, la
  finestra di dialogo chiede un indirizzo.
- **Un link di reimpostazione password** non ha campi: l'email va all'indirizzo dell'account, e solo
  finché l'account è attivo.
- **Il link nell'email inizia con `LIBREFOLIO_PUBLIC_URL`**, qualunque cosa mostri l'**Indirizzo del server**
  sopra: la finestra di dialogo lo dice.
- **La lingua**: un invito va nella lingua scelta in **Lingua dell'email**, la
  **Lingua predefinita** dell'istanza a meno che tu non ne scelga un'altra; un link di reimpostazione va nella lingua dell'account.
- **Il risultato** viene mostrato nella finestra di dialogo: *Inviato a …* con l'indirizzo e la lingua in cui è stata scritta
  l'email, oppure il motivo per cui l'email non è stata inviata ([Errori di invio](email_troubleshooting.md#sending-errors)).

Senza email, il pulsante non c'è: copia il link come prima. Le regole e i limiti:
[Link inviati da un amministratore](email_flows.md#admin-links).

---

## 🗑️ Elimina un account {: #delete }

Apri la riga dell'account e fai clic su **Elimina**; per un amministratore, fai prima clic su **Rimuovi amministratore**,
a meno che non sia l'amministratore iniziale [in attesa del proprio link di configurazione](#cancel-setup), che elimini
direttamente. L'eliminazione segue la stessa regola dell'eliminazione del proprio account
([Profilo](../user/settings/profile.md)):

1. Per un account attivo, la finestra di dialogo offre prima **Disattiva** come alternativa: conserva ogni broker e
   transazione e può essere annullata; l'account semplicemente non può più accedere.
2. Poi mostra cosa comporterebbe l'eliminazione:
    - **Eliminati, con tutte le loro transazioni e i loro file**: i broker di cui l'account è l'unico proprietario,
      ciascuno con il suo numero di transazioni. Vengono eliminati anche per gli utenti con cui li condivideva.
      Se non ce ne sono, la finestra di dialogo dice *Nessun broker viene eliminato*;
    - **Broker condivisi che restano (se ne va solo l'accesso)**: gli altri broker che l'account può aprire,
      con il suo ruolo su ciascuno;
    - un avviso quando transazioni su altri broker sono metà di trasferimenti con i broker che
      vengono eliminati: restano, senza la loro altra metà. Un trasferimento ricevuto diventa una rettifica al suo
      costo, e un trasferimento inviato a uno di quei broker una rettifica che toglie gli asset dal
      broker che li ha inviati, senza un valore: il loro costo conta come una minusvalenza realizzata su quel broker (vedi
      [Modificare o eliminare un broker](../user/brokers/index.md)).
3. Digita il nome utente dell'account, poi fai clic su **Elimina definitivamente**.

!!! danger "L'eliminazione di un account non può essere annullata"

    L'account, le sue impostazioni e i broker elencati come eliminati vengono rimossi subito, e chiunque vi sia connesso viene disconnesso alla richiesta successiva. Se l'eliminazione non riesce per un motivo tecnico,
    non viene eliminato nulla. Se la finestra di dialogo non riesce a caricare cosa comporterebbe l'eliminazione, non ti consente di
    eliminare: chiudila e riprova.

Come funziona la regola: [Eliminazione di un account](../developer/architecture/access_control.md#admin-account-deletion),
per gli sviluppatori.

---

## 🔗 Correlati

- 📝 **[Variabili d'ambiente](configuration_accounts.md#accounts)** — «Account e registrazioni»: `LIBREFOLIO_MAX_USERS`,
  `LIBREFOLIO_REGISTRATION` e `LIBREFOLIO_PUBLIC_URL`
- ⚙️ **[Impostazioni globali](settings.md)** — «Chi può registrarsi»: l'impostazione **Registrazione**
- 🛠️ **[Strumenti da riga di comando](cli_tools.md)** — «Gestire gli utenti»: la maggior parte di queste attività, senza browser
- 👤 **[Profilo](../user/settings/profile.md)** — Il tuo account e come eliminarlo
- 🧑‍💻 Per gli sviluppatori: **[API amministratore](../developer/architecture/access_control.md#admin-user-api)**
  e **[Componenti delle impostazioni](../developer/frontend/components/features/settings.md#userstab)**
