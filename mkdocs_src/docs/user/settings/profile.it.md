# 👤 Profilo

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="profile" alt="Profilo">
</div>

La scheda **Profilo** gestisce la tua **identità** in LibreFolio — chi sei e come accedi. Le scelte di visualizzazione (lingua, valuta, tema) si trovano invece in **[Preferenze](preferences.md)**; le opzioni a livello di istanza si trovano in **[Impostazioni › Amministrazione › Impostazioni globali](../../admin/settings.md)**.

## 🔒 Blocco modifiche

La scheda si apre **bloccata**: i campi sono di sola lettura finché non fai clic sul ✏️ **pulsante matita** nell'intestazione. Questo impedisce modifiche accidentali. Se blocchi di nuovo la scheda mentre ci sono modifiche non salvate, una finestra di conferma chiede se scartarle.

Mentre la scheda è sbloccata, ogni campo modificato mostra i propri pulsanti **salva** / **annulla**, e l'intestazione offre **salva tutto** e **annulla tutto** per le azioni in blocco.

## 🖼️ Avatar

Passa il mouse sul tuo avatar (mentre la scheda è sbloccata) e fai clic sull'icona a forma di fotocamera 📷 sovrapposta per aprire il selettore di immagini: scegli un'immagine esistente dalla [libreria dei file](../files/index.md), una condivisa o una delle tue, oppure caricane una nuova. I caricamenti passano attraverso lo **[strumento di ritaglio immagini](../misc/image-crop.md)** con il preset *avatar* (ritaglio quadrato, anteprima circolare).

L'avatar viene salvato immediatamente ed è usato in tutta l'app ovunque venga mostrata la tua identità — barra laterale, condivisione dei broker ed elenchi dei collaboratori. Gli amministratori lo vedono anche in **[Impostazioni › Amministrazione › Utenti](../../admin/users.md#accounts)**, accanto al tuo nome utente.

Poiché gli altri utenti vedono il tuo avatar, la sua immagine è **condivisa**: un'immagine che carichi qui viene salvata come condivisa, e una delle tue immagini personali diventa condivisa quando la selezioni, con un avviso (vedi [Condivisa o personale](../files/index.md#visibility)).

!!! note "Impostabile anche dalla pagina di benvenuto"

    Gli account appena creati possono scegliere la stessa immagine una volta, durante la **[configurazione iniziale al primo accesso](../getting-started.md#welcome-setup)** — è lo stesso selettore, raggiunto semplicemente da una schermata diversa. Saltare quel passaggio lascia le tue iniziali come avatar; puoi sempre aggiungere o cambiare un'immagine in seguito da qui.

## ✏️ Nome utente, email, account creato

- **Nome utente** ed **Email** sono modificabili (è richiesta una scheda sbloccata). Le modifiche si applicano immediatamente alle tue credenziali di accesso. Cambiare l'email richiede anche la tua password attuale: vedi [Cambiare la propria email](#email-change) qui sotto.
- **Account creato** è un campo di sola lettura che mostra la data di registrazione.

### 📧 Cambiare la propria email {: #email-change }

Non appena l'email nel campo è un indirizzo diverso da quello attuale, subito sotto il campo dell'email compare un campo **Password attuale**, con un promemoria: *Per cambiare la tua email, inserisci la password attuale. Gli altri tuoi dispositivi verranno disconnessi.* Il pulsante di salvataggio dell'email, e **salva tutto**, restano disabilitati finché non la digiti.

- **Password errata**: la scheda dice *La password attuale non è corretta*. La nuova email resta nel suo campo e viene svuotata solo la password: digita di nuovo, poi salva.
- **Password errata, ancora e ancora**: le password errate inserite qui e gli accessi falliti con il tuo nome utente vengono conteggiati insieme. Dopo 10 errori in 15 minuti, la modifica viene rifiutata anche con la password corretta, e lo stesso vale per l'accesso con il tuo nome utente, per un massimo di 15 minuti. La scheda mostra quindi *Troppe password errate: attendi qualche minuto e riprova.*, e conserva sia la tua nuova email sia la password che hai digitato: salva di nuovo quando l'attesa è terminata.
- **Email rifiutata per un altro motivo**, ad esempio perché un altro account la usa già, come sua email o come suo nome utente, anche con maiuscole diverse: la scheda mostra il motivo e la tua email attuale viene ripristinata.
- **Email salvata**: resti connesso su questo dispositivo. Ogni altro dispositivo connesso al tuo account viene disconnesso e deve accedere di nuovo. Qualsiasi link per reimpostare la password ricevuto prima della modifica smette di funzionare, anche uno ancora in attesa nella tua vecchia casella di posta.
- **Un'email a ciascun indirizzo**: quando la tua istanza può inviare email, LibreFolio scrive all'indirizzo che avevi prima, per informarti della modifica, e al tuo nuovo indirizzo, per confermare che ora è quello del tuo account. La prima non mostra nulla del nuovo indirizzo e dice cosa fare se non hai effettuato tu la modifica; la seconda non mostra nulla del vecchio. Se una delle due non arriva, controlla anche la cartella spam.
- **Sono cambiate solo le maiuscole**, ad esempio `Anna@example.com` al posto di `anna@example.com`: è sempre il tuo indirizzo, quindi la scheda non chiede la password, salvi subito, nessun dispositivo viene disconnesso e l'indirizzo resta verificato. Solo per le lettere dalla A alla Z il confronto ignora maiuscole e minuscole; per le lettere accentate non è così: `Émile@example.com` e `émile@example.com` sono due indirizzi diversi.

Cambiare solo il nome utente non richiede la password e non disconnette alcun dispositivo. Il nuovo nome utente non può contenere `@`, perché all'accesso LibreFolio interpreta qualsiasi cosa contenga una `@` come indirizzo email: la scheda dice *Il nome utente non può contenere @: per accedere puoi sempre usare il tuo indirizzo email.*, e il nome utente attuale viene ripristinato. Spazi, lettere accentate e segni come `.`, `_`, `-` o `+` sono consentiti.

!!! info "Perché la tua password"

    Il tuo indirizzo email è il modo in cui il tuo account può essere recuperato: un link per reimpostare la password inviato a quell'indirizzo consente a chiunque lo legga di scegliere una nuova password. Senza questo controllo, qualcuno che ha accesso anche solo per un momento alla tua sessione aperta (un computer lasciato sbloccato, un cookie di sessione rubato) potrebbe inserire il proprio indirizzo nel tuo account e tenersi l'account per sempre. Senza la tua password, non può cambiare l'indirizzo.

## 🔐 Sicurezza

### 🔑 Cambia password

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="password-modal" alt="Cambia password">
</div>

Il pulsante **Cambia password** (sempre disponibile, non serve sbloccare la scheda) apre una modale che richiede:

1. La tua **password attuale** (per verifica)
2. Una **nuova password** che rispetti ogni regola della checklist sotto il campo: almeno 8 caratteri, una lettera maiuscola, una lettera minuscola, un numero e un carattere speciale — e deve essere diversa da quella attuale
3. **Conferma** della nuova password

La checklist segue ciò che digiti e il server applica esattamente le stesse regole. Contano le lettere e le cifre di qualsiasi alfabeto: `É` è una lettera maiuscola, `é` una minuscola. Un carattere speciale è qualsiasi carattere che non sia una lettera, un numero o uno spazio, come `!`, `_` o `€`. Se il server rifiuta comunque la nuova password, la modale dice *La password non soddisfa i requisiti di sicurezza*, e la checklist mostra quali regole mancano.

Le password attuali errate e gli accessi falliti con il tuo nome utente vengono conteggiati insieme, come per [l'email](#email-change): dopo 10 errori in 15 minuti, la modifica viene rifiutata anche con la password attuale corretta, e lo stesso vale per l'accesso con il tuo nome utente, per un massimo di 15 minuti. La modale mostra quindi *Troppe password errate: attendi qualche minuto e riprova.*, e conserva quanto hai digitato nei suoi tre campi: riprova quando l'attesa è terminata.

Dopo la conferma, la tua sessione resta attiva — non devi accedere di nuovo. Ogni altro dispositivo connesso al tuo account viene disconnesso. Qualsiasi link per reimpostare la password ricevuto prima della modifica smette di funzionare.

### 🗑️ Elimina account

Il pulsante **Elimina account** rimuove definitivamente il tuo account e le sue impostazioni. La sua finestra di dialogo mostra prima cosa verrebbe eliminato insieme al tuo account, poi ti chiede di digitare il tuo **nome utente**. **Elimina definitivamente** agisce subito: vieni disconnesso e riportato alla pagina di accesso.

Per i tuoi broker vale la stessa regola di [lasciare un broker condiviso](../brokers/sharing.md), e la finestra di dialogo li elenca prima che tu confermi:

- **Eliminati, con tutte le loro transazioni e i loro file**: i broker di cui sei l'**unico proprietario**, ciascuno con il suo numero di transazioni. Vengono eliminati anche i loro file di report importati, e scompaiono anche per gli utenti con cui li avevi condivisi. Se non ce ne sono, la finestra di dialogo dice *Nessun broker viene eliminato*;
- **Broker condivisi che restano (viene rimosso solo l'accesso)**: ogni altro broker che puoi aprire, con il tuo ruolo al suo interno. Resta per gli altri suoi utenti: viene rimosso solo il tuo accesso;
- un avviso quando le transazioni su altri broker sono metà di trasferimenti con i broker che vengono eliminati: restano, senza la loro altra metà. Un trasferimento ricevuto diventa una rettifica al suo costo, e un trasferimento inviato a uno di quei broker diventa una rettifica che preleva gli asset dal broker che li ha inviati, senza un valore: il loro costo viene conteggiato come perdita realizzata in quel broker (vedi [Modificare o eliminare un broker](../brokers/index.md)).

Se la finestra di dialogo non riesce a caricare quell'elenco, non ti consente di eliminare: chiudila e riprova. Se l'eliminazione fallisce per un motivo tecnico, non viene eliminato nulla.

!!! warning "Irreversibile"

    L'eliminazione del tuo account non può essere annullata. Se sei l'**unico amministratore attivo** dell'istanza, l'eliminazione viene rifiutata: rendi prima amministratore un altro account, dalla scheda [Utenti](../../admin/users.md).

---

## 🔗 Correlati

- 🎛️ **[Preferenze utente](preferences.md)** — Lingua, valuta di base e tema
- ⚙️ **[Panoramica impostazioni](index.md)** — Riepilogo delle impostazioni generali
- ℹ️ **[Informazioni](about.md)** — Informazioni sulla versione, plugin e changelog
- 🛡️ **[Impostazioni globali](../../admin/settings.md)** — Opzioni a livello di istanza (amministratore)
