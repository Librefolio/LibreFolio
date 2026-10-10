# ✏️ Editor Dati

L'editor dati ti permette di correggere e completare manualmente i dati di un asset: i suoi prezzi giornalieri e i suoi eventi, come i dividendi. Usalo per correggere un prezzo errato fornito da un provider, aggiungere lo storico di un asset che ne è privo, colmare una lacuna o registrare un evento che il provider ha omesso.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-editor" alt="Editor dei dati dell'asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Modificare prezzi ed eventi

1. In modalità **Prezzi**, clicca su **✏️ Modifica Prezzi ed Eventi** in alto a destra del grafico. L'editor si apre sotto il grafico, con una scheda **Prezzi** e una **Eventi**.
2. Modifica ciò che ti serve:
    - **Aggiungi Riga** aggiunge una riga in una data libera: cambia la data se necessario, poi inserisci i valori.
    - Clicca su una cella per modificarla.
    - **Elimina**, nel menu **⋮** di una riga, contrassegna la riga per l'eliminazione, e **Ripristina** la fa tornare. Spunta più righe per eliminarle insieme.
    - **Importa CSV** carica molte righe in una volta ([sotto](#import-from-csv)).
3. Clicca su **Salva (n)**, dove *n* è il numero delle modifiche apportate, oppure **Annulla** per scartarle. Sia l'uno che l'altro chiudono l'editor e riportano gli altri pannelli; lo stesso fa ✕, senza salvare.

Finché non salvi, i prezzi nuovi e modificati vengono mostrati sul grafico come una linea viola. Un prezzo salvato al di fuori delle date visualizzate le amplia per includerlo.

---

## 💰 Scheda Prezzi

- **Close** è obbligatorio e deve essere un numero positivo; **Open**, **High**, **Low** e **Volume** sono opzionali, e la gomma in una cella cancella il suo valore.
- I prezzi sono nella valuta dell'asset, mostrata accanto alle schede (*Prezzi in USD*).
- Le **righe obsolete** sono giorni privi di un prezzo proprio, riempiti con l'ultimo conosciuto. Quando ce ne sono alcune, compaiono un conteggio ⚠️ e un interruttore: attivalo per nasconderle.

---

## 📅 Scheda Eventi

Ogni riga ha un **Tipo** (Dividendo, Interesse, Split, Rettifica Prezzo o Scadenza), un **Importo** nella valuta dell'asset (per azione per un dividendo, il rapporto per uno split) e **Note** opzionali. Vedi [Eventi dell'Asset](events.md) per sapere cosa fa ciascun tipo.

- **Gli eventi provenienti da un provider sono di sola lettura**: una modifica verrebbe sovrascritta alla sua prossima sincronizzazione. Puoi eliminarne uno, ma il provider lo riaggiunge alla sua prossima sincronizzazione; per rimuoverlo definitivamente, modifica le impostazioni del provider dell'asset.
- **Modificare uno dei tuoi eventi cambia quell'evento**, incluso il suo **Tipo**: non viene aggiunto un secondo evento. Una transazione ad esso collegata resta collegata e viene letta in base al nuovo tipo: una **Rettifica** collegata a uno split, per esempio, non conta più come split una volta che l'evento è una Rettifica Prezzo.
- **Cambiare il Tipo di un evento in quello che un altro dei tuoi eventi ha in quella data** viene rifiutato al momento del salvataggio; scambiare i tipi di due eventi in un solo salvataggio funziona. Se stai eliminando quell'altro evento, salva prima l'eliminazione. Un salvataggio rifiutato mantiene le tue modifiche nell'editor perché tu le corregga, mentre le modifiche ai prezzi dello stesso salvataggio sono già memorizzate.
- **Un evento a cui è collegata una transazione** non può essere eliminato: ma il salvataggio ti avvisa.

---

## 📥 Importare da CSV {: #import-from-csv }

**Importa CSV** apre una finestra in cui trascini un file o ne incolli il testo, e ogni riga viene verificata prima che tu la importi. La prima riga deve nominare le colonne, in qualsiasi ordine.

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

    `date`, `type` e `amount` sono obbligatori. `type` è uno tra `DIVIDEND`, `INTEREST`, `SPLIT`, `PRICE_ADJUSTMENT` e `MATURITY_SETTLEMENT`.

    `value` è accettato al posto di `amount`, così un file di eventi esportato da LibreFolio (il backup offerto quando [cambi la valuta di un asset](../create-edit.md#editing-an-asset)) si reimporta, con le sue altre colonne ignorate. Tieni presente due limiti:

    - **Un evento per data**: le righe che condividono una data vengono tutte escluse come duplicati, perciò importa tali eventi da file separati.
    - **Ogni riga diventa un tuo evento**, inclusi quelli di un provider: ometti le righe il cui `source` è `PROVIDER` se il provider le invierà di nuovo, altrimenti compariranno due volte.

- Le date sono nel formato `YYYY-MM-DD`, e i decimali possono usare `.` o `,`.
- Le colonne sono separate da `;` o `,`; con `,`, scrivi i decimali con `.`.
- Le altre colonne sono ignorate, così un file di prezzi esportato da LibreFolio si importa così com'è.
- La colonna `currency` non viene né verificata né convertita: gli importi sono memorizzati nella valuta dell'asset così come sono, quindi converti prima quelli di un backup effettuato prima di un cambio di valuta.
- Una riga di prezzo aggiorna il prezzo della sua data; una riga di evento aggiorna il tuo evento con la stessa data e tipo. Una riga che corrisponde solo a un evento di un provider viene esclusa, poiché un'importazione non modifica mai quelli; le altre vengono aggiunte. Nulla viene memorizzato finché non clicchi su **Salva**.

---

## 🖱️ Vai dal grafico

Con l'editor aperto, fai doppio clic su un punto del grafico (o tieni premuto su di esso sul telefono) per passare a quella data: alla scheda **Eventi** quando la data ha un evento, a **Prezzi** altrimenti.

---

## 🔗 Correlati

- 📈 **[Grafico Interattivo](chart.md)** — Visualizzazione del grafico con indicatori di evento
- 📅 **[Eventi dell'Asset](events.md)** — Tipi di evento e relative fonti
- 📚 **[Eventi dell'Asset (Teoria Finanziaria)](../../../financial-theory/instruments/asset-events/index.md)** — Analisi dettagliata dell'impatto per ogni tipo di evento
- 🔌 **[Provider](../providers/index.md)** — Recupero automatico dei prezzi
- 🛠️ **[Componenti dell'Editor Dati](../../../developer/frontend/components/core-ui/data-editor.md)** — Per gli sviluppatori: come l'editor verifica, unisce e salva le righe
