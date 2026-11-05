# 🚀 Per iniziare

Ti diamo il benvenuto in LibreFolio! In pochi passaggi crei il tuo account, fai un rapido tour e importi il tuo
primo estratto conto del broker — e la tua dashboard si popola da sola.

---

## 📝 1. Registra il tuo account

Apri l'indirizzo di LibreFolio (ad esempio `http://localhost:6040`): compare la pagina di accesso. Fai clic su
**Registrati qui** per creare un account.

Se la pagina di accesso non mostra **Registrati qui**, il tuo amministratore consente l'accesso solo con un
link di invito, oppure ha chiuso le registrazioni: chiedi all'amministratore un invito o un account. Con un
invito, segui [Se hai ricevuto un link di invito](#invitation-link).

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Modulo di registrazione" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Compila i tuoi dati:

- 👤 **Nome utente** — univoco, da 3 a 50 caratteri, senza `@`: accedi con esso. Spazi, lettere accentate
  e segni come `.`, `_`, `-` o `+` sono ammessi. Quando accedi, LibreFolio interpreta
  qualsiasi cosa contenga una `@` come indirizzo email, quindi il modulo rifiuta un nome utente che la contenga: *Il nome utente non può contenere @:
  per accedere, puoi sempre usare il tuo indirizzo email.*
- 📧 **Email** — un indirizzo valido; funziona anche per l'accesso.
- 🔑 **Password** e **Conferma password** — l'indicatore di robustezza ti dice quando la password è
  abbastanza sicura.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registrazione con indicatore di robustezza della password" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "Primo utente = Amministratore"

    Il primissimo account a registrarsi diventa l'**amministratore**: gestisce le
    **[Impostazioni globali](../admin/settings.md)** dell'istanza e ogni funzione di amministrazione.

### ✉️ Se hai ricevuto un link di invito {: #invitation-link }

Un amministratore può invitarti con un link personale, via messaggio o email: l'oggetto dell'email è
*Hai ricevuto un invito a LibreFolio* e il pulsante **Crea il tuo account** apre il link.

1. Apri il link. LibreFolio lo verifica, poi mostra il modulo di registrazione con una nota che hai
   ricevuto un invito; una seconda nota ti dice se l'invito ti rende amministratore.
2. Se l'amministratore ha indicato il tuo indirizzo email nell'invito, è già compilato: puoi
   modificarlo.
3. Scegli il nome utente e la password, poi fai clic su **Registrati**.
4. Torni alla pagina di accesso, con una conferma: accedi con il tuo nuovo account.

- ⏱️ Un link di invito funziona una sola volta, per 7 giorni. Se la pagina dice che il link è scaduto, è già
  stato usato, è stato revocato o non è valido, chiedi un nuovo link all'amministratore.
- 📬 Se l'istanza ti chiede di confermare il tuo indirizzo email, apri il link che ti invia via email prima di
  accedere: vedi [Se LibreFolio ti chiede di confermare la tua email](#verify-email).
- 🔒 Non appena la pagina si apre, la barra degli indirizzi perde la parte segreta del link: conserva il messaggio
  che hai ricevuto nel caso ti serva riaprire il link. Se la pagina dice che il link è incompleto,
  riaprilo da quel messaggio.
- 🚪 Se la pagina dice che la registrazione è disabilitata, l'amministratore ha chiuso le iscrizioni per ora:
  chiedi all'amministratore.

### 📬 Se LibreFolio ti chiede di confermare la tua email {: #verify-email }

Alcune istanze chiedono a ogni nuovo account di confermare il proprio indirizzo email prima del primo accesso. In tal caso,
dopo **Registrati**:

1. La pagina di accesso dice: *Account creato. Ti stiamo inviando un'email con un link per attivarlo:
   aprila entro 24 ore, poi accedi. Non hai ricevuto l'email dopo qualche minuto? Controlla la cartella spam, poi
   accedi con il tuo nome utente e la tua password: ti verrà offerto un nuovo link.* Non puoi ancora accedere.
2. Apri l'email *Conferma il tuo indirizzo email* e fai clic su **Conferma il mio indirizzo email**. Se il
   pulsante non funziona, copia nel browser l'indirizzo scritto sotto.
3. Il pulsante apre una pagina di LibreFolio che ti chiede di confermare. Fai clic su **Conferma il mio indirizzo email**
   lì: LibreFolio quindi conferma il tuo indirizzo e ti riporta alla pagina di accesso, con una
   conferma: accedi con il tuo nome utente e la tua password.

- 🖱️ Perché un altro clic? Alcuni servizi email aprono da soli i link di un messaggio, per verificarli:
  il clic assicura che sia tu a confermare.
- 🙋 Se non hai creato un account su questa istanza, chiudi semplicemente la pagina: non succede nulla.
- ⏱️ Il link funziona una sola volta, per 24 ore.
- 📭 Non hai ricevuto l'email? Controlla nella cartella spam. Poi, nella pagina di accesso, accedi con il tuo nome utente e
  la tua password: LibreFolio dice che il tuo indirizzo non è ancora verificato e offre **Invia di nuovo il link**
  sotto. Un nuovo link sostituisce quelli precedenti. Se chiedi troppo spesso, o dopo troppe password errate,
  la pagina ti dice tra quanti minuti puoi chiedere di nuovo.
- 🚦 Se invece la pagina di accesso dice che al momento non è stato possibile inviare l'email di attivazione, perché ci sono
  state troppe registrazioni dalla tua rete nell'ultima ora (o l'istanza ha inviato troppe
  email), nessuna email è in arrivo. Il tuo account è comunque creato: attendi i minuti indicati dalla pagina,
  poi accedi con il tuo nome utente e la tua password, e ti verrà offerto **Invia di nuovo il link**.
- ⌛ Se la pagina dice che il link è scaduto, accedi allo stesso modo: ti viene offerto un nuovo link.
  Se nel frattempo l'istanza non ha più posti liberi, chiedi al tuo amministratore.
- ✅ Se la pagina dice che il link è già stato usato, il tuo account è probabilmente già attivo:
  accedi.
- 🔒 Come con un invito, la barra degli indirizzi perde la parte segreta del link non appena la pagina
  si apre: conserva l'email finché il tuo account non è attivo.

---

## 🔐 2. Accedi

Dopo la registrazione, torni alla pagina di accesso. Accedi con il tuo nome utente (o email) e la tua
password. Digita il nome utente esattamente come l'hai scelto, maiuscole comprese. Se il tuo nome utente contiene
una `@`, cosa che possono avere gli account creati prima della versione 1.3, accedi invece con il tuo indirizzo email.
Se LibreFolio ti ha chiesto di confermare il tuo indirizzo email, apri prima il link che ti ha inviato via email:
vedi [Se LibreFolio ti chiede di confermare la tua email](#verify-email).

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="01-login" alt="Pagina di accesso" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Sotto la scheda, come in ogni pagina di accesso, una riga contiene le [note legali](settings/about.md#legal-notice)
della tua istanza.

!!! note "Troppi tentativi di accesso"

    Dopo 10 password errate in 15 minuti per lo stesso nome utente o indirizzo email, o 50 dallo
    stesso indirizzo IP, la pagina di accesso dice *Troppi tentativi di accesso: attendi qualche minuto e riprova.*
    Finché l'attesa non è terminata, anche la password corretta viene rifiutata: attendi fino a 15 minuti, poi
    accedi. Il tuo amministratore può anche farti entrare subito, riavviando LibreFolio.

### 📧 Se hai dimenticato la password {: #forgot-password }

Nella pagina di accesso, fai clic su **Password dimenticata?**. Quando la tua istanza può inviare email, la pagina ha un
modulo in alto:

1. Digita il tuo nome utente o il tuo indirizzo email, poi fai clic su **Inviami un link per reimpostare la password**.
2. La pagina risponde allo stesso modo indipendentemente dal fatto che un account corrisponda o meno: controlla la posta in arrivo e la
   cartella spam.
3. Apri l'email *Reimposta la password di LibreFolio* e fai clic su **Scegli una nuova password**. La pagina
   che si apre è quella di un link inviato da un amministratore: segui
   [Se un amministratore ti ha inviato un link per reimpostare la password](#password-reset-link) dal passaggio 2.

- ⏱️ Il link funziona una sola volta, per 30 minuti.
- 📭 Non hai ricevuto l'email dopo qualche minuto? L'account potrebbe essere disattivato o registrato con un altro
  indirizzo, oppure le richieste sono arrivate troppo ravvicinate: riprova più tardi o chiedi al tuo amministratore.
- 💻 Sotto il modulo, un pannello chiuso contiene il comando che il tuo amministratore esegue sul server per reimpostare
  una password; quando la tua istanza non può inviare email, la pagina lo mostra aperto. In ogni caso: chiedi al tuo amministratore.

### 🔑 Se un amministratore ti ha inviato un link per reimpostare la password {: #password-reset-link }

Il tuo amministratore può anche inviarti un link per scegliere tu stesso una nuova password, via messaggio o
email.

1. Apri il link: la pagina mostra l'account a cui appartiene.
2. Digita due volte la nuova password: deve rispettare le regole mostrate sotto il campo.
3. Fai clic su **Imposta la nuova password**. Torni alla pagina di accesso, con una conferma: accedi con
   la nuova password.

- ⏱️ Il link funziona una sola volta, per 30 minuti. Se la pagina dice che è scaduto, è già stato usato o
  è stato revocato, chiedine uno nuovo: ogni nuovo link revoca quelli inviati prima.
- 🚪 Impostare la nuova password disconnette il tuo account da ogni dispositivo: accedi di nuovo con la nuova
  password su ciascuno di essi.

---

## 🎉 3. Configurazione iniziale e tour rapido {: #welcome-setup }

La prima volta che accedi, LibreFolio apre una pagina **Benvenuto** prima della dashboard:

- 🌍 Controlla **Lingua** e **Valuta predefinita**: partono dai valori predefiniti del tuo amministratore.
- 🖼️ Aggiungi un'**immagine del profilo** se vuoi — altrimenti vengono mostrate le tue iniziali.
- ✅ Fai clic su **Continua** per salvare, o su **Salta definitivamente la configurazione** per mantenere le impostazioni attuali.
- 🚪 Devi uscire? **Esci** è in alto a destra.
- ⚖️ Sotto la scheda: le [note legali](settings/about.md#legal-notice) della tua istanza.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="welcome-setup" alt="La pagina di benvenuto del primo avvio: il blocco dell'immagine del profilo con l'avatar con le iniziali e Scegli immagine, Lingua e Valuta predefinita precompilate, la nota che la preferenza del tema viene mantenuta invariata, e Salta definitivamente la configurazione e Continua" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Segue una breve animazione di benvenuto, poi il **Tour rapido** parte da solo — fai clic su **Avvia tour**
per iniziare subito, oppure su **✕** per saltarlo. Il tour mostra dove si trovano le cose: il pulsante del menu, poi
**Dashboard**, **Transazioni**, **Broker**, **FX**, **Asset**, **Strumenti** e **Impostazioni**. Si
limita a indicare: non apre mai un modulo e non crea dati.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="core-tour-step" alt="Il Tour rapido sulla Dashboard al passaggio 5 di 8, tassi di cambio: una cornice e un cursore sulla voce Tassi di cambio della barra laterale, e il pannello dei messaggi con Indietro e Avanti" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

??? note "👋 Usi già LibreFolio? — account precedenti alle guide"

    Se il tuo account esisteva prima dell'aggiunta delle guide, LibreFolio non te le fa seguire:
    la configurazione iniziale risulta **Completata**, il tour e le guide risultano **Saltati**. Puoi comunque
    ripetere ciascuno di essi da
    **[Impostazioni → Preferenze → Primo utilizzo e guide](settings/preferences.md#onboarding-and-guides)**.

??? warning "⚠️ La configurazione non si carica — cosa fare"

    Se le tue impostazioni o i progressi delle guide non possono essere caricati, una pagina **Impossibile caricare il primo utilizzo**
    offre **Riprova** e **Esci**. Se la tua configurazione iniziale è già completata, potresti vedere la
    Dashboard invece, con un banner **Riprova** in alto.

### 🧭 Guide contestuali

Successivamente, brevi guide si avviano la prima volta che raggiungi un punto in cui sono utili:

| Area | Guide contestuali |
|---|---|
| **Transazioni** | Panoramica della pagina, modulo Aggiungi transazione, workspace bulk e Procedura guidata di importazione |
| **Broker** | Pagina Broker, modulo Aggiungi broker e dettagli del broker |
| **FX** | Pagina FX, modulo Aggiungi coppia e dettagli della coppia |
| **Asset** | Pagina Asset, modulo Aggiungi asset e dettagli dell'asset |

- Indicano controlli reali e non fanno mai clic, non caricano, non modificano e non salvano al posto tuo.
- Una cornice pulsante contrassegna l'area di cui parla un passaggio; un piccolo cursore contrassegna un pulsante che puoi provare.
  Facendoci clic, svolge la sua normale funzione e fa avanzare la guida.
- Il pannello dei messaggi sbiadisce un po' dopo un momento, così puoi vedere la pagina dietro; passaci sopra il mouse per
  farlo tornare.
- Esci da una pagina a metà guida e la sua guida riprende dallo stesso passaggio quando torni; chiudere un modulo
  riavvia la guida di quel modulo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="contextual-guide" alt="La guida della pagina FX al passaggio 2 di 4, sul filtraggio di date, valute e viste: una cornice attorno ai filtri delle valute, e il pannello dei messaggi con Indietro e Avanti" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Puoi ripetere qualsiasi guida da
**[Impostazioni → Preferenze → Primo utilizzo e guide](settings/preferences.md#onboarding-and-guides)**.

---

## 🏦 4. Importa il tuo primo estratto conto (crea broker e asset al volo)

La tua dashboard è ancora vuota — che tu ci arrivi direttamente o dopo le schermate di benvenuto qui sopra.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="empty-state" alt="Dashboard vuota" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Il modo più rapido per popolarla è importare la cronologia delle transazioni. Non devi configurare broker
o asset prima: la Procedura guidata di importazione li crea man mano.

### 📋 Passaggi

1. **Apri la Procedura guidata di importazione**: nella pagina **[Transazioni](transactions/index.md)**, fai clic su **Importa** (:material-file-upload:). La pagina di dettaglio di un broker ha lo stesso pulsante, con quel broker già selezionato.

2. **Carica il tuo estratto conto**: trascina il report del tuo broker (`.csv`, `.xlsx` o `.xls`) nella procedura guidata e assegnalo al suo broker — scegli **Crea nuovo** se il broker non esiste ancora. Ogni report che carichi viene conservato (lo trovi in **[File e caricamenti](files/index.md#broker-reports)**): la prossima volta, salta questo passaggio e seleziona il report nel passaggio successivo.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Passaggio di caricamento della procedura guidata" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

3. **Seleziona i file e analizza**: seleziona i report da importare. Ognuno riceve il parser del proprio broker — cambialo per file se necessario, **CSV generico** per un formato sconosciuto. LibreFolio legge quindi ogni riga e riepiloga ciò che ha trovato: transazioni, titoli, problemi e probabili duplicati. Alcuni file richiedono poi uno o due passaggi extra (vedi il pannello sotto).
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Passaggio di analisi della procedura guidata" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

4. **Rivedi e importa**: abbina ogni titolo alla tua libreria di asset, oppure crealo **al volo** con i dettagli letti dall'estratto conto. I probabili duplicati arrivano non selezionati, e le righe con data precedente alla data di apertura del broker vengono escluse. Maggiori dettagli in **[Mappatura degli asset](transactions/import/index.md#asset-mapping)**.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Passaggio di revisione della procedura guidata: risoluzione degli asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

5. **Salva dall'editor bulk**: **Importa N transazioni** sposta le righe selezionate nell'editor bulk — non è ancora stato salvato nulla. Dagli un'ultima occhiata, poi fai clic su **Salva tutto**.

??? note "🧩 Passaggi extra — solo quando i tuoi file li richiedono"

    La procedura guidata aggiunge un passaggio solo quando i tuoi file lo richiedono; un report pulito da un solo file li salta
    tutti:

    - **Unifica asset** — lo stesso titolo compare con nomi o codici diversi.
    - **Correzioni** — alcune righe non sono state lette completamente.
    - **Duplicati** — lo stesso movimento è in due file che importi insieme.
    - **Allinea con la banca** — dopo **Rivedi**, per un set di report come Danske Bank, quando le
      cifre della banca differiscono da quelle di LibreFolio.

    Vedi **[Passaggi che compaiono solo quando necessario](transactions/import/how-to.md#only-when-needed)**.

La prima volta che apri la procedura guidata, una guida ti accompagna attraverso i passaggi necessari per i tuoi file; non
fa mai clic né salva al posto tuo (vedi **[Prima importazione guidata](transactions/import/how-to.md#guided-first-import)**).
Per la procedura completa vedi **[Come importare le transazioni](transactions/import/how-to.md)**; per i
broker e i formati di file supportati vedi **[Importa da broker](transactions/import/index.md)**.

---

## 📈 5. Torna alla dashboard

Torna alla **Dashboard**: il valore del tuo portafoglio, la tua allocazione (per tipo, settore e area geografica)
e la cronologia delle tue performance ora sono compilati.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="main" alt="Vista principale della dashboard" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔮 6. Cosa c'è dopo?

Ora che il tuo portafoglio è popolato, puoi:

- 🤝 **[Condividi il tuo broker](brokers/sharing.md)** — Dai accesso a familiari o consulenti.
- 💱 **[Configura i tassi di cambio](fx/index.md)** — Configura la conversione di valuta per portafogli multivaluta.
- ⚙️ **[Personalizza le tue preferenze](settings/preferences.md)** — Regola lingua, valuta predefinita e tema. Gli amministratori gestiscono anche le **[Impostazioni globali](../admin/settings.md)** a livello di sistema.
- 🧭 **[Ripeti la configurazione iniziale o i tour guidati](settings/preferences.md#onboarding-and-guides)** — Rivedi la schermata di benvenuto, il tour rapido o la guida all'importazione in qualsiasi momento da Impostazioni → Preferenze.
- 📱 **[Installa LibreFolio come app](pwa.md)** — Mettilo nella schermata Home del telefono o in una finestra desktop dedicata.
