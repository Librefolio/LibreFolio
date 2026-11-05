# ✏️ Editor dati

L'editor dati ti permette di correggere e completare a mano i dati di un asset: i suoi prezzi giornalieri e i suoi eventi, come i dividendi. Usalo per correggere un prezzo sbagliato proveniente da un provider, aggiungere lo storico di un asset che ne è privo, colmare una lacuna o registrare un evento che il provider ha omesso.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-editor" alt="Editor dati dell'asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Modificare prezzi ed eventi

1. Nella modalità **Prezzi**, clicca **✏️ Modifica prezzi ed eventi** in alto a destra nel grafico. L'editor si apre sotto il grafico, con le schede **Prezzi** e **Eventi**.
2. Modifica ciò che ti serve:
    - **Aggiungi riga** aggiunge una riga in una data libera: cambia la data se necessario, poi inserisci i valori.
    - Clicca su una cella per modificarla.
    - **Elimina**, nel menu **⋮** di una riga, contrassegna la riga per l'eliminazione, e **Ripristina** la riporta indietro. Spunta più righe per eliminarle insieme.
    - **Importa CSV** carica molte righe in una volta ([sotto](#import-from-csv)).
3. Clicca **Salva (n)**, dove *n* conta le tue modifiche, oppure **Annulla** per scartarle. Entrambi chiudono l'editor e riportano gli altri pannelli; lo fa anche ✕, senza salvare.

Finché non salvi, i prezzi nuovi e modificati compaiono sul grafico come una linea viola. Un prezzo salvato fuori dalle date visualizzate le amplia per includerlo.

---

## 💰 Scheda Prezzi

- **Chiusura** è obbligatoria e deve essere maggiore di 0; **Apertura**, **Massimo**, **Minimo** e **Volume** sono facoltativi, 0 o più, e la gomma in una cella ne cancella il valore. LibreFolio non conserva prezzi negativi: una riga che ne contiene uno, cosa che solo un file importato può portare, non viene salvata e conta come saltata.
- I prezzi sono nella valuta dell'asset, indicata accanto alle schede (*Prezzi in USD*).
- Le **righe obsolete** sono giorni privi di un prezzo proprio, riempiti con l'ultimo conosciuto. Quando ce ne sono, compaiono un conteggio ⚠️ e un interruttore: attivalo per nasconderle.
- **Un prezzo rifiutato dal server viene indicato nell'avviso.** Se il server ne rifiuta alcuni, ad esempio una chiusura superiore al **Massimo** della riga o inferiore al suo **Minimo**, salva gli altri. Un avviso elenca quindi fino a cinque date rifiutate, ciascuna con il suo motivo, e indica quante sono le altre; resta visibile per 20 secondi, così puoi annotarle e reinserirle. Se rifiuta l'intero salvataggio, per esempio perché una data è successiva a domani, non viene salvato nulla: il messaggio ne spiega il motivo e l'editor resta aperto con le tue modifiche.

---

## 📅 Scheda Eventi

Ogni riga ha un **Tipo** (Dividendo, Interesse, Split, Rettifica prezzo o Scadenza), un **Importo** nella valuta dell'asset (per azione per un dividendo, il rapporto per uno split) e **Note** facoltative. Vedi [Eventi dell'asset](events.md) per sapere cosa fa ciascun tipo.

- **Gli eventi provenienti da un provider sono di sola lettura**: una modifica verrebbe sovrascritta alla sincronizzazione successiva. Puoi eliminarne uno, ma il provider lo riaggiunge alla sincronizzazione successiva; per rimuoverlo definitivamente, modifica le impostazioni del provider dell'asset.
- **Modificare uno dei tuoi eventi modifica quell'evento**, incluso il suo **Tipo**: non viene aggiunto un secondo evento. Una transazione collegata resta collegata e viene letta in base al nuovo tipo: una **Rettifica** collegata a uno split, per esempio, non conta più come split una volta che l'evento è una Rettifica prezzo.
- **Le modifiche ai tuoi eventi vengono salvate tutte insieme, o per niente.** Eliminazioni, modifiche e nuove righe vanno in un unico passaggio, prima le eliminazioni. Se qualcosa viene rifiutato, non viene memorizzata nessuna modifica agli eventi, eliminazioni comprese: *Salvataggio non riuscito: …* ti dice il perché, nella tua lingua, e le tue modifiche restano nell'editor così puoi correggerle. Le modifiche ai prezzi dello stesso salvataggio vengono comunque memorizzate, poiché i prezzi si salvano per primi.

Un salvataggio viene rifiutato, con un messaggio che indica l'evento responsabile, quando:

- **un evento è in una valuta diversa da quella dell'asset**: questo proviene da una riga CSV, che conserva la valuta in cui è stata scritta ([sotto](#import-from-csv));
- **il nuovo Tipo di un evento è quello che un altro dei tuoi eventi ha in quella data**: scambiare i tipi di due eventi in un unico salvataggio funziona, e funziona anche eliminare quell'altro evento nello stesso salvataggio;
- **elimini un evento a cui è collegata una transazione**: il messaggio indica l'evento e quante transazioni lo utilizzano. Rimuovi prima il collegamento da quelle transazioni. Prima di LibreFolio 1.3, il resto del salvataggio andava a buon fine e quell'eliminazione veniva saltata con un avviso;
- **modifichi il Tipo di uno split le cui rettifiche collegate non hanno un valore di acquisto**: senza lo split, quelle unità risulterebbero acquistate a un prezzo sconosciuto. Il messaggio conta tali rettifiche, comprese quelle presso un broker che non puoi vedere; assegna loro prima un valore di acquisto, poi cambia il Tipo;
- **un Tipo non è uno dei cinque**: anche questo proviene da una riga CSV.

---

## 📥 Importa da CSV {: #import-from-csv }

**Importa CSV** apre una finestra in cui puoi rilasciare un file o incollarne il testo, e ogni riga viene verificata prima dell'importazione. La prima riga deve indicare i nomi delle colonne, in qualsiasi ordine.

=== "Prezzi"

    ```text
    date;currency;close;open;high;low;volume
    2024-01-15;USD;145.50;144.00;146.20;143.80;1500000
    2024-01-16;USD;146.10;;;;
    ```

    `date`, `currency` e `close` sono obbligatori: scrivi la valuta dell'asset.

=== "Eventi"

    ```text
    date;currency;type;amount;notes
    2024-03-15;USD;DIVIDEND;1.25;Q1 payout
    2024-06-01;;SPLIT;2;2:1 split
    ```

    `date`, `type` e `amount` sono obbligatori. `type` è uno tra `DIVIDEND`, `INTEREST`, `SPLIT`, `PRICE_ADJUSTMENT` e `MATURITY_SETTLEMENT`: qualsiasi altro valore viene rifiutato al salvataggio.

    `value` è accettato al posto di `amount`, così un file di eventi esportato da LibreFolio (il backup offerto quando [si cambia la valuta di un asset](../create-edit.md#editing-an-asset)) si reimporta, con le sue altre colonne ignorate. Tieni presente due limiti:

    - **Un evento per data e tipo**: le righe che condividono sia la data sia il tipo vengono tutte scartate come duplicati; un dividendo e uno split nello stesso giorno si importano insieme.
    - **Righe contrassegnate `PROVIDER`**: quando l'asset ha un provider, vengono scartate e l'editor ti dice quante; sincronizza l'asset per caricarle. Quando l'asset non ha un provider, vengono aggiunte come eventi tuoi.

    In quel file, una nota che inizia con `=`, `+`, `-` o `@` ha un apostrofo davanti, così che un foglio di calcolo la mostri come testo invece di eseguirla come formula: l'importazione rimuove quell'apostrofo e la nota torna com'era.

- Le date sono nel formato `YYYY-MM-DD` e i decimali possono usare `.` o `,`.
- Le colonne sono separate da `;` o `,`; con `,`, scrivi i decimali con `.`.
- Le altre colonne vengono ignorate, così un file di prezzi esportato da LibreFolio si importa così com'è.
- La colonna `currency` non viene mai convertita. Su una riga di prezzo non viene nemmeno controllata: il prezzo viene memorizzato nella valuta dell'asset così com'è. Una riga di evento conserva la sua valuta, e una in una valuta diversa da quella dell'asset viene rifiutata al salvataggio; una vuota prende quella dell'asset. Quindi, prima di importare un backup effettuato prima di un cambio di valuta, converti i suoi importi e scrivi la nuova valuta dell'asset.
- Una riga di prezzo aggiorna il prezzo della sua data; una riga di evento aggiorna il tuo evento con la stessa data e lo stesso tipo. Una riga che corrisponde solo a un evento di un provider viene scartata, poiché un'importazione non li modifica mai; le altre vengono aggiunte. Nulla viene memorizzato finché non clicchi **Salva**.

---

## 🖱️ Saltare dal grafico

Con l'editor aperto, fai doppio clic su un punto del grafico (o tieni premuto su quel punto da telefono) per saltare a quella data: alla scheda **Eventi** se la data ha un evento, altrimenti a **Prezzi**.

---

## 🔗 Correlati

- 📈 **[Grafico interattivo](chart.md)** — Visualizzazione del grafico con indicatori di eventi
- 📅 **[Eventi dell'asset](events.md)** — Tipi di evento e loro origini
- 📚 **[Eventi dell'asset (Teoria finanziaria)](../../../financial-theory/instruments/asset-events/index.md)** — Analisi dettagliata dell'impatto per ciascun tipo di evento
- 🔌 **[Provider](../providers/index.md)** — Recupero automatico dei prezzi
- 🛠️ **[Componenti dell'editor Datapoint](../../../developer/frontend/components/core-ui/data-editor.md)** — Per gli sviluppatori: come l'editor verifica, unisce e salva le righe
