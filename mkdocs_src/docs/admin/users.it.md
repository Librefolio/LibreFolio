# 👥 Utenti e inviti

Un amministratore gestisce gli account dell'istanza — chi può accedere, chi è amministratore, chi è invitato — in una sola scheda.

**Dove:** **Impostazioni › Amministrazione › Utenti**. Uguale in ogni installazione.

---

## 🧭 Apri la scheda {: #open-the-tab }

1. Apri **Impostazioni** (icona a forma di ingranaggio nella barra laterale), poi **Amministrazione**, poi la scheda **Utenti**, accanto a **Impostazioni globali**.

    Solo gli amministratori vedono questa scheda.

La scheda ha tre parti: i **posti** occupati, in alto; gli **Account**; i **Link degli account**. Dopo ogni modifica ricarica i suoi elenchi: mostra sempre ciò che il server contiene.

!!! tip "💻 Su un server senza browser"

    La [riga di comando](cli_tools.md) fa la maggior parte di queste cose, sul server, nella cartella di LibreFolio:

    ```bash
    pipenv run ./dev.py user invite
    pipenv run ./dev.py user reset-link <username>
    pipenv run ./dev.py user deactivate <username>
    pipenv run ./dev.py user activate <username>
    pipenv run ./dev.py user promote <username>
    pipenv run ./dev.py user demote <username>
    pipenv run ./dev.py user reset-onboarding <username>
    ```

    Con Docker, il comando va nel container: «Dove eseguire i comandi» in [Strumenti da riga di comando](cli_tools.md).
    La riga di comando supera anche il limite utenti. Non può eliminare un account né revocare un invito.

---

## 📏 Posti {: #places }

L'intestazione conta i posti occupati: **3 / 10 account** con un limite utenti, **3 account** senza.

| Occupa un posto | |
|---|---|
| Account attivo | ✅ |
| Invito aperto | ✅ |
| Account [in attesa della propria email](#waiting) | ✅ finché il suo link è valido |
| Amministratore iniziale [in attesa del proprio link di configurazione](#pending-setup) | ✅ |
| Account disattivato | ❌ |

**Dove si imposta il limite:** nel `.env` di LibreFolio, con `LIBREFOLIO_MAX_USERS`: «Quando l'istanza è piena» in [Variabili d'ambiente](configuration_accounts.md#user-limit).

Quando **Invita** è disattivato:

| Perché | Cosa dice la scheda | Cosa puoi fare |
|---|---|---|
| 🚫 L'istanza è piena | Un banner: *L'istanza è piena: nessun nuovo invito finché non disattivi o elimini un account, oppure revochi un invito.* Neanche un account disattivato può essere riattivato, a meno che non sia [in attesa della propria email](#waiting) con un link valido | Disattiva o elimina un account, oppure revoca un invito |
| 🔒 L'impostazione globale **Registrazione** è **Chiusa** | Ti dice di cambiarla in [Impostazioni globali](settings.md), «Chi può registrarsi» | Cambiala lì, oppure in [Chi può registrarsi](#registration) qui sotto |
| 🔒 Il server chiude la registrazione con `LIBREFOLIO_REGISTRATION` | Indica il nome della variabile | Solo la configurazione del server può riaprirla |

### 🚪 Chi può registrarsi {: #registration }

**Dove:** il selettore **Chi può registrarsi**, accanto a **Invita**. È l'impostazione globale **Registrazione**, la stessa di [Impostazioni globali](settings.md) («Chi può registrarsi»).

1. Scegli **Aperta**, **Su invito** o **Chiusa**.

    La scelta viene salvata subito, senza pulsante **Salva**, e la scheda rilegge l'impostazione.

- ⚠️ Solo **Aperta** chiede prima una conferma: lascia entrare chiunque raggiunga la pagina di accesso. Se annulli, la modalità resta com'era.
- 🔒 Se è il server a impostare la modalità con `LIBREFOLIO_REGISTRATION`, il selettore è disattivato e la scheda indica il nome della variabile.

---

## 👤 Account {: #accounts }

Una riga per account, dal più vecchio al più recente: avatar, nome utente con i suoi badge, email, data di creazione. L'avatar è l'immagine scelta dall'utente nel suo [Profilo](../user/settings/profile.md); senza avatar, la prima lettera del nome utente in un cerchio.

| Badge | Significato |
|---|---|
| **Tu** | Il tuo account |
| **Admin** | Un amministratore: gestisce l'istanza, le sue impostazioni, i suoi utenti e i suoi inviti |
| **Disattivato** | L'account non può accedere e non occupa alcun posto |
| **In attesa di configurazione** | L'[amministratore iniziale](configuration_accounts.md#initial-admin), non ancora attivo: nessuno ha usato il suo link di configurazione, né lo ha configurato in altro modo. Al posto di **Disattivato**: vedi [In attesa del proprio link di configurazione](#pending-setup) |
| **In attesa di verifica** | Un account che non ha ancora aperto il link di verifica inviato al suo indirizzo, anche dopo la scadenza del link. Non può accedere e occupa un posto finché il link è valido. Al posto di **Disattivato**: vedi [Account in attesa della propria email](#waiting) |

**Dove sono le azioni:** fai clic su una riga per aprirle, di nuovo per chiuderle. La tua riga non ne ha: dice *Questo è il tuo account. Gestiscilo da:* con un link a **Profilo**, dove modifichi i tuoi dati o [elimini il tuo account](../user/settings/profile.md).

### ⚙️ Cosa fa ciascuna azione {: #actions }

| Azione | Cosa fa | Chiede conferma |
|---|---|---|
| **Disattiva** | L'account non può più accedere ed è disconnesso da ogni dispositivo. Broker e transazioni restano; il suo posto si libera. Solo per un account attivo | ✅ |
| **Riattiva** | L'account accede di nuovo, con i suoi dati; le vecchie sessioni non tornano. Occupa di nuovo un posto, quindi ne serve uno libero, a meno che non sia [in attesa della propria email](#waiting) con un link valido (il posto è già conteggiato). Per un account disattivato, anche in attesa della propria email, ma non per l'amministratore iniziale [in attesa del proprio link di configurazione](#pending-setup) | — |
| **Annulla link di configurazione** | Il link di configurazione dell'amministratore iniziale [in attesa della propria configurazione](#pending-setup) smette di funzionare, compreso quello già consegnato; l'account continua ad attendere un nuovo link. Solo per quell'account, al posto di **Riattiva**: vedi [Annulla il suo link di configurazione](#cancel-setup) | ✅ |
| **Rendi amministratore** | L'account gestisce anch'esso l'istanza: impostazioni, utenti e inviti | ✅ |
| **Rimuovi amministratore** | L'account resta, come utente normale, ed è disconnesso da ogni dispositivo | ✅ |
| **Link di reimpostazione password** | Un link per scegliere una nuova password: vedi [Link di reimpostazione password](#reset-links) | La sua finestra di dialogo |
| **Disconnetti ovunque** | L'account è disconnesso da ogni dispositivo e vi accede di nuovo. Resta attivo | ✅ |
| **Riavvia le guide** | Alla prossima apertura di LibreFolio, la [Configurazione iniziale](../user/getting-started.md#welcome-setup) e ogni guida ricominciano, come per un nuovo account. Dati e preferenze restano | ✅ |
| **Elimina** | Rimuove definitivamente l'account: vedi [Elimina un account](#delete) | La sua finestra di dialogo |

### 🔒 Quando un'azione è disattivata {: #action-off }

LibreFolio disattiva le azioni che il server rifiuterebbe e spiega perché sotto i pulsanti:

| Il pannello dice | Disattivato | Cosa puoi fare |
|---|---|---|
| *È l'unico amministratore attivo: non può essere disattivato né retrocesso.* | **Disattiva**, **Rimuovi amministratore** | Rendi prima amministratore un altro account |
| *L'istanza è piena: libera un posto per riattivarlo.* | **Riattiva** | Disattiva o elimina un altro account, oppure revoca un invito; `user activate` della riga di comando supera il limite |
| *Un amministratore deve essere retrocesso prima di poter essere eliminato.* | **Elimina** | Prima **Rimuovi amministratore**, poi **Elimina** |
| *È in attesa della propria configurazione: mantiene il suo ruolo fino ad allora.* | **Rimuovi amministratore**, per l'amministratore iniziale [in attesa del proprio link di configurazione](#pending-setup) | [Annulla il suo link di configurazione](#cancel-setup), oppure **Elimina** l'account, senza prima **Rimuovi amministratore** |
| *Questo account amministratore si attiva tramite il suo link di configurazione. Se il link va perso, esegui `dev.py user setup-link` sul server.* | Nessun **Riattiva**: al suo posto **Annulla link di configurazione** | Fai usare il suo link di configurazione, oppure forniscine uno nuovo: vedi [In attesa del proprio link di configurazione](#pending-setup) |

- 👑 L'istanza mantiene sempre un amministratore attivo. La tua riga non ha azioni: per lasciare il ruolo, rendi amministratore un altro account, poi chiedigli di rimuoverti i privilegi.

### ⏳ Account in attesa della propria email {: #waiting }

Con **Richiedi verifica email** attivo ([Impostazioni globali](settings.md)), un nuovo account resta in attesa finché il suo proprietario non conferma l'indirizzo con il link che LibreFolio gli invia via email. Fino ad allora:

- 🏷️ la riga mostra **In attesa di verifica** invece di **Disattivato**, anche dopo la scadenza del link. Passa il mouse sul badge per il suggerimento, oppure apri la riga: sotto i pulsanti si legge *Il suo proprietario non ha ancora aperto il link di verifica: l'accesso propone di inviarne uno nuovo. Riattiva fa entrare subito l'account, senza l'email.*;
- 📏 occupa un posto finché il suo link è valido: 24 ore dopo l'invio dell'ultimo link;
- ✅ **Riattiva** lo fa entrare subito: può accedere e i link già inviati smettono di funzionare. Con il link ancora valido non serve un posto libero (il suo è già conteggiato): funziona anche su un'istanza piena, come `user activate` sulla [riga di comando](cli_tools.md), senza avviso di limite. Con il link scaduto, serve un posto libero come per qualsiasi account disattivato;
- 🗑️ **Elimina** lo rimuove, come qualsiasi account;
- ⛔ la scheda non offre **Disattiva** per un account non attivo. Sul server, `user deactivate`, o l'API amministratore (`PATCH /api/v1/users/{id}` con `is_active: false`), lo mantiene ma termina l'attesa: i suoi link smettono di funzionare, il suo posto è libero, la riga mostra di nuovo **Disattivato** e può accedere solo dopo la riattivazione.

Come funziona la verifica e i suoi limiti: [Verifica email](email_flows.md#verification).

### 👑 In attesa del proprio link di configurazione {: #pending-setup }

Quando LibreFolio crea l'amministratore di `LIBREFOLIO_ADMIN_EMAIL` al primo avvio, l'account resta in attesa, non attivo, finché qualcuno non apre il suo link di configurazione e sceglie la password, oppure lo configura in altro modo (sotto): [L'amministratore iniziale](configuration_accounts.md#initial-admin). Fino ad allora:

- 🏷️ la riga mostra **In attesa di configurazione** invece di **Disattivato**, anche dopo la scadenza del link o dopo che è stato [annullato](#cancel-setup);
- 📏 occupa un posto, come un account attivo;
- ⛔ il pannello non ha **Riattiva**: nessuno conosce la sua password, e attivarlo farebbe smettere di funzionare anche il link di configurazione. Al suo posto c'è **Annulla link di configurazione** ([sotto](#cancel-setup)), con la motivazione della [tabella sopra](#action-off);
- 🔒 **Rimuovi amministratore** è disattivato, con la sua motivazione ([tabella sopra](#action-off)). Per bloccare il link già consegnato, annullalo; per bloccare del tutto l'account, eliminalo;
- 🗑️ **Elimina** non richiede prima **Rimuovi amministratore**, a differenza di ogni altro amministratore;
- le altre azioni sono quelle di qualsiasi account disattivato.

Il server rifiuta di attivarlo o di retrocederlo: `PATCH /api/v1/users/{id}` con `is_active: true`, o con `is_superuser: false`, risponde `409`, codice `PENDING_SETUP`, senza cambiare nulla. Se una tale modifica arriva comunque al server, per esempio da un elenco caricato prima, la scheda dice *Questo amministratore è in attesa della propria configurazione: qui non può essere né riattivato né retrocesso.* `GET /api/v1/users` lo contrassegna con `pending_setup: true`.

**Un nuovo link di configurazione.** Questa versione non ha un pulsante per crearlo.

**Dove:** sul server, nella cartella di LibreFolio:

```bash
pipenv run ./dev.py user setup-link
```

Il comando stampa il link: «Un nuovo link di configurazione per l'amministratore iniziale» in [Strumenti da riga di comando](cli_tools.md). Una volta usato, l'account è attivo come qualsiasi altro.

**Configurato in altro modo, senza il suo link.** L'account smette di attendere anche così:

| Dove | Come | Risultato |
|---|---|---|
| Sul server | `user activate` | La riga di comando non lo rifiuta, a differenza della scheda, e non stampa alcun avviso di limite: l'account occupa già il suo posto. La sua password resta quella che nessuno conosce, finché `user reset` o un link di reimpostazione non gliene assegna una |
| Sul server | `user reset` | Una password assegnata. L'account resta inattivo finché non viene attivato |
| Nel suo pannello, o sul server | Un [link di reimpostazione password](#reset-links) usato: da **Link di reimpostazione password**, o stampato da `user reset-link` | Come sopra: inattivo finché non viene attivato |

Da quel momento ogni link di configurazione smette di funzionare: la pagina di configurazione dice *Questo link è stato ritirato.*, e `user setup-link` non trova alcun amministratore in attesa. La scheda lo mostra come qualsiasi altro account: **Disattivato** finché non è attivo, con **Riattiva**, e `GET /api/v1/users` lo contrassegna con `pending_setup: false`. Non occupa più alcun posto, quindi **Riattiva** ne richiede uno libero. Un link di reimpostazione che nessuno usa lo lascia in attesa, come [annullare il suo link di configurazione](#cancel-setup).

### 🚫 Annulla il suo link di configurazione {: #cancel-setup }

Quando il link è finito alla persona sbagliata, o qualcun altro potrebbe averlo visto (un'email inoltrata, il log del server).

**Dove:** la riga dell'account **In attesa di configurazione**, pulsante **Annulla link di configurazione**. Sul server, `user deactivate` su questo account annulla il link allo stesso modo.

1. Apri la riga e fai clic su **Annulla link di configurazione**.

    La finestra chiede *Annullare il link di configurazione di {username}?* e spiega: *Il link già consegnato smette di funzionare. L'account continua ad attendere la propria configurazione: un nuovo link arriva da «dev.py user setup-link» sul server.*

2. Fai clic su **Annulla il link**.

    Un messaggio conferma: *Il link di configurazione di {username} non funziona più.*

Cosa succede:

- 🔗 ogni link di configurazione dell'account smette di funzionare, compreso quello consegnato: chi lo apre legge *Questo link è stato ritirato.* e non può configurare l'account;
- ⏳ l'account resta in attesa: la riga mostra ancora **In attesa di configurazione**, mantiene il suo posto e qui non può essere riattivato;
- 🔁 per far entrare l'amministratore, fornisci un nuovo link con `user setup-link` sul server (sopra). Riavviare il server con lo stesso `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` non produce un nuovo link: l'istanza ha già visto quel token. Ogni avvio registra un avviso che il link di configurazione è stato ritirato, e chiede di eseguire `dev.py user setup-link` oppure di impostare un nuovo token.

Casi particolari:

| Caso | Cosa succede |
|---|---|
| L'amministratore ha completato la configurazione dopo il caricamento del tuo elenco | Nulla da annullare: LibreFolio non cambia nulla e dice *Questo amministratore ha completato la propria configurazione nel frattempo: nulla è stato modificato.* La scheda si ricarica: la riga mostra un amministratore attivo, con **Disattiva** al posto di **Annulla link di configurazione**; il suo proprietario ha effettuato l'accesso |
| Vuoi rimuovere l'account | **Elimina** ([Elimina un account](#delete)), senza prima **Rimuovi amministratore**. L'account è eliminato con i suoi link di configurazione, il posto si libera e nessuno attende più una configurazione: `user setup-link` non trova nessuno, e le variabili `LIBREFOLIO_ADMIN_*` non creano nulla agli avvii successivi, poiché l'istanza ha degli account |
| Vuoi rimuoverlo, ma la configurazione è stata completata nel frattempo | Non viene eliminato nulla: la finestra dice *Un amministratore deve essere retrocesso prima di poter essere eliminato.*, poiché ora è un amministratore attivo |

### 🔤 Nomi utente con una @ {: #usernames-with-at }

Dalla versione 1.3 un nuovo nome utente non può contenere `@`: all'accesso, LibreFolio interpreta qualsiasi cosa con una `@` come indirizzo email. Lo rifiutano la registrazione, un cambio di nome utente nel Profilo e `user create` sulla [riga di comando](cli_tools.md); un `LIBREFOLIO_ADMIN_USERNAME` con una `@` blocca il server all'avvio («L'amministratore iniziale» in [Variabili d'ambiente](configuration_accounts.md#initial-admin)). Spazi, lettere accentate e segni come `.`, `_`, `-` o `+` vanno bene.

Un account creato prima della versione 1.3 può averne uno, per esempio `anna@example.com`:

- 🏷️ il nome utente resta com'è: nulla lo rinomina. L'utente può cambiarlo nel proprio [Profilo](../user/settings/profile.md), con un nome senza `@`;
- 🔑 l'account accede con il proprio indirizzo email. Il nome utente funziona all'accesso solo finché nessun account lo ha come indirizzo email: un indirizzo digitato individua l'account che lo possiede;
- 📧 nessun altro account può prendere quel nome utente come indirizzo email, con qualsiasi maiuscole: registrazione, Profilo, `user create` e `user set-email` lo rifiutano con *Email già registrata*. L'account stesso può prenderlo come proprio indirizzo.

---

## ✉️ Inviti {: #invitations }

**Dove:** **Utenti**, pulsante **Invita**. Sul server: `pipenv run ./dev.py user invite` ([riga di comando](cli_tools.md)).

1. Fai clic su **Invita**.

2. Facoltativo: scrivi il suo indirizzo in **Email (facoltativa)**.

    È solo una nota su a chi è destinato l'invito: il link funziona per chiunque lo apra. L'elenco degli inviti lo mostra, e il modulo di registrazione parte da quello, modificabile.

3. Seleziona **Amministratore** se il nuovo account deve gestire l'istanza.

4. Fai clic su **Crea il link**.

    *Condividi questo link: funziona una sola volta, per 7 giorni.* Controlla l'[indirizzo del server](#server-address), fai clic su **Copia** e invia il link tu stesso (messaggio o email), oppure lascia che lo invii LibreFolio: [Invia via email](#send-by-email).

5. Fai clic su **Fatto**.

    L'invito compare nei [Link degli account](#account-links). La persona apre il link e crea l'account con nome utente, email e password che sceglie: [Per iniziare](../user/getting-started.md) mostra ciò che vede.

- 🔗 Il link viene mostrato una sola volta, quando lo crei. Se va perso, revoca l'invito e creane uno nuovo.
- 📏 Un invito occupa un posto da quando lo crei finché non viene usato, revocato o scade; l'account che crea occupa poi quel posto.
- 🔤 Un indirizzo email appartiene a un solo account, indipendentemente dalle maiuscole (`Anna@example.com` è `anna@example.com`), ma solo le lettere dalla A alla Z sono confrontate così: `Émile@example.com` e `émile@example.com` sono due indirizzi diversi.

---

## 🔑 Link di reimpostazione password {: #reset-links }

Quando qualcuno ha dimenticato la password, inviagli un link per sceglierne una nuova da solo. Con l'email, può anche richiederne uno dalla pagina di accesso: [Password dimenticate](email_flows.md#forgot-password).

**Dove:** la riga dell'account, pulsante **Link di reimpostazione password**. Sul server: `pipenv run ./dev.py user reset-link <username>` ([riga di comando](cli_tools.md)).

1. Apri la riga e fai clic su **Link di reimpostazione password**.

    La finestra spiega: *Un link monouso per impostare una nuova password, valido 30 minuti. I link creati prima per questo account smettono di funzionare.*

2. Fai clic su **Crea il link**.

3. Controlla l'[indirizzo del server](#server-address), fai clic su **Copia** e invia il link, oppure fai clic su **Invia via email** ([Invia via email](#send-by-email)). Poi **Fatto**.

    La persona apre il link e sceglie la password: [Per iniziare](../user/getting-started.md).

- ⏱️ Il link funziona una sola volta, per 30 minuti; vale solo il link più recente di un account.
- 🔒 Smette di funzionare anche appena la persona cambia password o indirizzo email, o quando esegui `user reset` o `user set-email` sulla [riga di comando](cli_tools.md).
- 🚪 Creare il link non disconnette nessuno. Quando la persona imposta la nuova password, l'account è disconnesso da ogni dispositivo.
- 🔗 Il link viene mostrato una sola volta: se va perso, creane uno nuovo.

---

## 📋 Link degli account {: #account-links }

Ogni link monouso dell'istanza, e a che punto è: inviti, link di reimpostazione della password, verifiche dell'email, il link di configurazione del primo amministratore, il cambio email del titolare di un'istanza gestita. Il link stesso qui non compare mai: si vede una volta sola, quando viene creato.

**Dove:** **Utenti**, la sezione **Link degli account**, sotto gli account.

| Colonna | Cosa mostra |
|---|---|
| **Tipo** | *Invito*, *Reimpostazione password*, *Verifica email*, *Configurazione amministratore* o *Cambio email* |
| **Per** | L'account su cui agisce il link; per un invito, l'indirizzo scritto nell'invito, oppure *Chiunque abbia il link*; un badge **Admin** quando l'invito crea un amministratore |
| **Creato da** | L'amministratore che l'ha creato; *—* quando l'ha chiesto LibreFolio o la persona stessa (una verifica, una reimpostazione dalla pagina di accesso) |
| **Creato**, **Scade** | Data e ora |
| **Stato** | *Aperto*; *Usato*, con quando e da chi; *Scaduto*; *Revocato*, con quando |

I link aperti sono nella prima tabella. Quelli chiusi — usati, scaduti o revocati — sono in **Link chiusi**, ripiegato: cliccalo per aprirlo. Ogni tabella ordina per colonna (clic sull'intestazione), filtra per colonna (l'imbuto nell'intestazione), nasconde o mostra colonne (l'occhio) e divide in pagine gli elenchi lunghi.

**Revoca**, nel menu (⋮) di un link aperto, lo ritira dopo una conferma: il link smette subito di funzionare, e un invito libera il suo posto. Qui si revocano inviti, link di reimpostazione della password e verifiche dell'email. Il link di configurazione dell'amministratore in attesa si annulla dal suo account ([Annulla il suo link di configurazione](#cancel-setup)); il cambio email del titolare segue l'indirizzo impostato da chi ospita l'istanza, e qui non si revoca.

---

## 🌐 L'indirizzo del server di un link {: #server-address }

Link di invito e di reimpostazione password si mostrano nello stesso pannello:

- **Indirizzo del server**: da dove inizia il link. Compilato con `LIBREFOLIO_PUBLIC_URL` quando il server la imposta, altrimenti con l'indirizzo che il tuo browser usa ora. *Cambialo se i tuoi utenti raggiungono LibreFolio a un altro indirizzo*: per esempio tu sei su `http://192.168.1.10:6040` a casa, i tuoi utenti passano da `https://librefolio.example.com`.
- **Link**: l'indirizzo del server seguito dal percorso del link. **Copia** lo mette negli appunti; se il browser rifiuta, il link viene selezionato per copiarlo a mano. *Valido fino a …* ne indica la scadenza.

Quando cambi l'indirizzo, mezzo secondo dopo che smetti di digitare il browser verifica che **questa** istanza risponda lì, e non un server qualsiasi: carica `<address>/api/v1/auth/address-probe.png?nonce=…`. L'indirizzo compilato in sé non viene verificato.

| Messaggio | Cosa significa |
|---|---|
| *Verifica in corso che questo LibreFolio risponda a questo indirizzo…* | La verifica è in corso |
| *Questa istanza risponde a questo indirizzo.* | Il link raggiunge questo LibreFolio |
| *Qualcosa risponde a questo indirizzo, ma non questa istanza: controllalo prima di condividere.* | Lì risponde un altro LibreFolio: probabilmente non è l'indirizzo che intendevi |
| *Non è stato possibile verificare questo indirizzo da questo browser: puoi comunque condividere il link.* | Il browser non ha caricato l'immagine. Lì non risponde nulla (indirizzo errato o chiuso, o nessuna risposta entro 8 secondi); una pagina `https://` verifica un indirizzo `http://`, che il browser blocca; una pagina su un indirizzo pubblico verifica un indirizzo locale, che alcuni browser bloccano o consentono solo dopo aver chiesto il tuo permesso; un'istanza bloccata non serve l'immagine; oppure risponde un LibreFolio più vecchio, che non può essere verificato |
| *Inserisci un indirizzo che inizi con http:// o https://, senza ? o #.* | Non è un indirizzo: **Copia** resta disattivato finché non lo correggi |

Qualunque sia il risultato, tranne un indirizzo che non è tale, puoi copiare il link: la verifica è solo un consiglio. Tornando all'indirizzo compilato, il messaggio scompare. Come funziona: [Sonda dell'indirizzo](../developer/architecture/security.md#address-probe), per gli sviluppatori.

!!! tip "🌐 Imposta l'indirizzo una volta sola"

    **Dove:** nel `.env` di LibreFolio, l'indirizzo che i tuoi utenti aprono:

    ```bash
    LIBREFOLIO_PUBLIC_URL=https://librefolio.example.com
    ```

    Il pannello parte da lì: «Account e registrazioni» in [Variabili d'ambiente](configuration_accounts.md#accounts). Anche la [riga di comando](cli_tools.md) lo antepone ai link che stampa.

---

## 📧 Invia via email {: #send-by-email }

Condizione: email **Pronta** e `LIBREFOLIO_PUBLIC_URL` impostato su un indirizzo che LibreFolio può usare ([Email con un link](email_flows.md#public-url)). Allora entrambe le finestre dei link hanno **Invia via email** sotto il link. Senza email il pulsante non c'è: copia il link come prima.

| | Invito | Link di reimpostazione password |
|---|---|---|
| **Destinatario** | **Invia a** parte dall'indirizzo scritto nell'invito; puoi cambiarlo. Vuoto, l'email va all'indirizzo dell'invito; se non ce n'è uno, la finestra chiede un indirizzo | Nessun campo: va all'indirizzo dell'account, e solo finché l'account è attivo |
| **Lingua** | **Lingua dell'email**: la **Lingua predefinita** dell'istanza, a meno che tu non ne scelga un'altra | La lingua dell'account |

- 🌐 **Il link nell'email inizia con `LIBREFOLIO_PUBLIC_URL`**, qualunque cosa mostri l'**Indirizzo del server** sopra: la finestra lo dice.
- 📨 **Il risultato** è nella finestra: *Inviato a …* con indirizzo e lingua dell'email, oppure il motivo per cui l'email non è partita ([Errori di invio](email_troubleshooting.md#sending-errors)).

Regole e limiti: [Link inviati da un amministratore](email_flows.md#admin-links).

---

## 🗑️ Elimina un account {: #delete }

**Dove:** la riga dell'account, pulsante **Elimina**. Per un amministratore, prima **Rimuovi amministratore**; non per l'amministratore iniziale [in attesa del proprio link di configurazione](#cancel-setup), che elimini direttamente. La riga di comando non elimina account.

L'eliminazione segue la stessa regola dell'eliminazione del proprio account ([Profilo](../user/settings/profile.md)):

1. Per un account attivo, la finestra offre prima **Disattiva** come alternativa.

    Conserva ogni broker e transazione e può essere annullata; l'account semplicemente non accede più.

2. La finestra mostra cosa comporterebbe l'eliminazione:

    - **Eliminati, con tutte le loro transazioni e i loro file**: i broker di cui l'account è l'unico proprietario, ciascuno con il suo numero di transazioni. Sono eliminati anche per gli utenti con cui li condivideva. Se non ce ne sono: *Nessun broker viene eliminato*;
    - **Broker condivisi che restano (se ne va solo l'accesso)**: gli altri broker che l'account può aprire, con il suo ruolo su ciascuno;
    - un avviso quando transazioni su altri broker sono metà di trasferimenti con i broker eliminati: restano, senza l'altra metà. Un trasferimento ricevuto diventa una rettifica al suo costo; un trasferimento inviato a uno di quei broker una rettifica che toglie gli asset dal broker che li ha inviati, senza un valore: il loro costo conta come minusvalenza realizzata su quel broker ([Modificare o eliminare un broker](../user/brokers/index.md)).

3. Digita il nome utente dell'account, poi fai clic su **Elimina definitivamente**.

    L'account, le sue impostazioni e i broker elencati sono rimossi subito.

!!! danger "L'eliminazione di un account non può essere annullata"

    Chiunque sia connesso con quell'account viene disconnesso alla richiesta successiva. Se l'eliminazione non riesce per un motivo tecnico, non viene eliminato nulla. Se la finestra non riesce a caricare cosa comporterebbe l'eliminazione, non ti consente di eliminare: chiudila e riprova.

Come funziona la regola: [Eliminazione di un account](../developer/architecture/access_control.md#admin-account-deletion), per gli sviluppatori.

---

## 🔗 Correlati

- 📝 **[Variabili d'ambiente](configuration_accounts.md#accounts)** — «Account e registrazioni»: `LIBREFOLIO_MAX_USERS`, `LIBREFOLIO_REGISTRATION` e `LIBREFOLIO_PUBLIC_URL`
- ⚙️ **[Impostazioni globali](settings.md)** — «Chi può registrarsi»: l'impostazione **Registrazione**
- 🛠️ **[Strumenti da riga di comando](cli_tools.md)** — «Gestire gli utenti»: la maggior parte di queste attività, senza browser
- 👤 **[Profilo](../user/settings/profile.md)** — Il tuo account e come eliminarlo
- 🧑‍💻 Per gli sviluppatori: **[API amministratore](../developer/architecture/access_control.md#admin-user-api)** e **[Componenti delle impostazioni](../developer/frontend/components/features/settings.md#userstab)**
