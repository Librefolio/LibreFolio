# 🚀 Guida introduttiva

Benvenuto in LibreFolio! In pochi passaggi crei il tuo account, fai un rapido tour e importi il tuo
primo estratto conto del broker — e la tua dashboard si popola da sola.

---

## 📝 1. Registra il tuo account

Apri l'indirizzo di LibreFolio (ad esempio `http://localhost:6040`): appare la pagina di accesso. Clicca
**Registrati qui** per creare un account.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Modulo di registrazione" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Inserisci i tuoi dati:

- 👤 **Nome utente** — univoco: accedi con questo.
- 📧 **Email** — un indirizzo valido; funziona anche per l'accesso.
- 🔑 **Password** e **Conferma password** — l'indicatore di robustezza ti dice quando la password è
  abbastanza sicura.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registrazione con robustezza password" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "Primo utente = Amministratore"

    Il primissimo account a registrarsi diventa l'**amministratore**: gestisce le
    **[Impostazioni globali](../admin/settings.md)** a livello di istanza e ogni funzionalità di amministrazione.

---

## 🔐 2. Accedi

Dopo la registrazione, torni alla pagina di accesso. Accedi con il tuo nome utente (o email) e la tua
password.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="01-login" alt="Pagina di accesso" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🎉 3. Configurazione iniziale e tour rapido {: #welcome-setup }

La prima volta che accedi, LibreFolio apre una pagina di **Benvenuto** prima della dashboard:

- 🌍 Controlla **Lingua** e **Valuta predefinita**: partono dai valori predefiniti del tuo amministratore.
- 🖼️ Aggiungi un'**immagine del profilo** se vuoi — altrimenti vengono mostrate le tue iniziali.
- ✅ Clicca **Continua** per salvare, oppure **Salta configurazione in modo permanente** per mantenere le impostazioni attuali.
- 🚪 Devi uscire? **Esci** è in alto a destra.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="welcome-setup" alt="La pagina di Benvenuto al primo avvio: il blocco dell'immagine del profilo con l'avatar delle iniziali e Scegli immagine, Lingua e Valuta predefinita precompilate, la nota che la preferenza del tema resta invariata, e Salta configurazione in modo permanente e Continua" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Segue una breve animazione di benvenuto, poi il **Tour rapido** inizia da solo — clicca **Avvia tour**
per iniziare subito, oppure **✕** per saltarlo. Il tour mostra dove si trovano le cose: il pulsante del menu, poi
**Dashboard**, **Transazioni**, **Broker**, **FX**, **Asset**, **Strumenti** e **Impostazioni**. Indica
soltanto: non apre mai un modulo né crea dati.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="core-tour-step" alt="Il Tour rapido sulla Dashboard al passaggio 5 di 8, tassi FX: una cornice e un cursore sulla voce Tassi FX della barra laterale, e il pannello dei messaggi con Indietro e Avanti" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

??? note "👋 Usi già LibreFolio? — account precedenti alle guide"

    Se il tuo account esisteva prima dell'aggiunta delle guide, LibreFolio non te le propone:
    la configurazione iniziale risulta **Completata**, il tour e ogni guida risultano **Saltati**. Puoi comunque
    ripetere qualsiasi guida da
    **[Impostazioni → Preferenze → Primo utilizzo e guide](settings/preferences.md#onboarding-and-guides)**.

??? warning "⚠️ La configurazione non si carica — cosa fare"

    Se le tue impostazioni o i progressi delle guide non possono essere caricati, una pagina **Impossibile caricare i dati del primo utilizzo**
    offre **Riprova** e **Esci**. Se la tua configurazione iniziale è già completata, potresti invece vedere la
    Dashboard, con un banner **Riprova** in alto.

### 🧭 Guide contestuali

Successivamente, brevi guide si avviano la prima volta che raggiungi un punto in cui possono aiutare:

| Area | Guide contestuali |
|---|---|
| **Transazioni** | Panoramica della pagina, modulo Aggiungi transazione, workspace bulk e Procedura guidata di importazione |
| **Broker** | Pagina Broker, modulo Aggiungi broker e dettagli del broker |
| **FX** | Pagina FX, modulo Aggiungi coppia e dettagli della coppia |
| **Asset** | Pagina Asset, modulo Aggiungi asset e dettagli dell'asset |

- Puntano a controlli reali e non cliccano, non eseguono l'upload, non modificano e non salvano mai per te.
- Una cornice pulsante contrassegna l'area di cui parla un passaggio; un piccolo cursore contrassegna un pulsante che puoi provare.
  Cliccarlo svolge la sua normale funzione e fa avanzare la guida.
- Il pannello dei messaggi si attenua leggermente dopo un momento, così puoi vedere la pagina dietro; passaci sopra il mouse per
  farlo riapparire.
- Se lasci una pagina a metà guida, la sua guida riprende dallo stesso passaggio quando torni; chiudere un modulo
  riavvia la guida di quel modulo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="contextual-guide" alt="La guida della pagina FX al passaggio 2 di 4, sul filtro di date, valute e viste: una cornice attorno ai filtri valuta, e il pannello dei messaggi con Indietro e Avanti" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Puoi ripetere qualsiasi guida da
**[Impostazioni → Preferenze → Primo utilizzo e guide](settings/preferences.md#onboarding-and-guides)**.

---

## 🏦 4. Importa il tuo primo estratto conto (Crea broker e asset al volo)

La tua dashboard è ancora vuota — che tu ci arrivi direttamente o dopo le schermate di benvenuto qui sopra.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="empty-state" alt="Dashboard vuota" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Il modo più veloce per popolarla è importare la cronologia delle tue transazioni. Non devi configurare prima broker
o asset: la Procedura guidata di importazione li crea man mano.

### 📋 Passaggi

1. **Apri la Procedura guidata di importazione**: nella pagina **[Transazioni](transactions/index.md)**, clicca **Importa** (:material-file-upload:). La pagina di dettaglio di un broker ha lo stesso pulsante, con quel broker già selezionato.

2. **Carica il tuo estratto conto**: trascina il report del tuo broker (`.csv`, `.xlsx` o `.xls`) nella procedura guidata e assegnalo al suo broker — scegli **Crea nuovo** se il broker non esiste ancora. Ogni report che carichi viene conservato (lo trovi in **[File e caricamenti](files/index.md#broker-reports)**): la prossima volta, salta questo passaggio e seleziona il report nel passaggio successivo.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Passaggio di caricamento della procedura guidata" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

3. **Seleziona i file e analizza**: seleziona i report da importare. Ognuno riceve il parser del suo broker — cambialo per file se necessario, **CSV generico** per un formato sconosciuto. LibreFolio poi legge ogni riga e riassume ciò che ha trovato: transazioni, titoli, problemi e probabili duplicati. Alcuni file richiedono poi uno o due passaggi extra (vedi il pannello sotto).
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Passaggio di analisi della procedura guidata" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

4. **Rivedi e importa**: abbina ogni titolo alla tua libreria di asset, oppure crealo **al volo** con i dettagli letti dall'estratto conto. I probabili duplicati arrivano deselezionati, e le righe datate prima della data di apertura del broker vengono escluse. Maggiori informazioni in **[Mappatura asset](transactions/import/index.md#asset-mapping)**.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Passaggio di revisione della procedura guidata: risoluzione asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

5. **Salva dall'editor bulk**: **Importa N transazioni** sposta le righe selezionate nell'editor bulk — non è ancora salvato nulla. Dagli un'ultima occhiata, poi clicca **Salva tutto**.

??? note "🧩 Passaggi extra — solo quando i tuoi file li richiedono"

    La procedura guidata aggiunge un passaggio solo quando i tuoi file lo richiedono; un report singolo e pulito li salta
    tutti:

    - **Unifica asset** — lo stesso titolo appare con nomi o codici diversi.
    - **Correzioni** — alcune righe non sono state lette completamente.
    - **Duplicati** — lo stesso movimento è in due file che importi insieme.
    - **Allinea con la banca** — dopo **Rivedi e importa**, per un set di report come Danske Bank, quando le
      cifre della banca differiscono da quelle di LibreFolio.

    Vedi **[Passaggi che compaiono solo quando necessario](transactions/import/how-to.md#only-when-needed)**.

La prima volta che apri la procedura guidata, una guida ti accompagna attraverso i passaggi richiesti dai tuoi file; non
clicca né salva mai per te (vedi **[Prima importazione guidata](transactions/import/how-to.md#guided-first-import)**).
Per la procedura completa vedi **[Come importare le transazioni](transactions/import/how-to.md)**; per i
broker supportati e i formati di file vedi **[Importazione da broker](transactions/import/index.md)**.

---

## 📈 5. Torna alla Dashboard

Torna alla **Dashboard**: il valore del tuo portafoglio, la tua allocazione (per tipo, settore e area geografica)
e la cronologia delle tue performance ora sono compilati.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="main" alt="Vista principale della Dashboard" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔮 6. E adesso?

Ora che il tuo portafoglio è popolato, puoi:

- 🤝 **[Condividi il tuo broker](brokers/sharing.md)** — Concedi l'accesso a familiari o consulenti.
- 💱 **[Configura i tassi FX](fx/index.md)** — Configura la conversione di valuta per portafogli multi-valuta.
- ⚙️ **[Personalizza le tue preferenze](settings/preferences.md)** — Regola lingua, valuta predefinita e tema. Gli amministratori gestiscono anche le **[Impostazioni globali](../admin/settings.md)** a livello di sistema.
- 🧭 **[Ripeti la configurazione iniziale o i tour guidati](settings/preferences.md#onboarding-and-guides)** — Rivedi la schermata di benvenuto, il tour rapido o la guida all'importazione in qualsiasi momento da Impostazioni → Preferenze.
- 📱 **[Installa LibreFolio come app](pwa.md)** — Mettila nella schermata Home del tuo telefono o in una finestra dedicata sul desktop.
