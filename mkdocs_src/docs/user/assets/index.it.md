# 💼 Asset

Gli asset sono gli strumenti che detieni o segui: azioni, ETF, obbligazioni, criptovalute o un conto di risparmio con interessi programmati. La pagina **Asset** li elenca tutti, ciascuno con un piccolo grafico dei prezzi, e apre la pagina di dettaglio di ognuno di essi.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="list" data-title="🔲 Vista griglia" alt="Pagina dell'elenco asset (griglia)">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="list-table" data-title="📋 Vista tabella" alt="Pagina dell'elenco asset (tabella)">
</div>

## 📌 Che cos'è un asset?

Ogni asset ha:

- **un nome e degli identificatori** — ISIN, ticker o altri codici;
- **un tipo** — azione, ETF, obbligazione, criptovaluta, commodity… ([tipi di asset](../../financial-theory/instruments/asset-types/index.md));
- **una valuta** — quella in cui sono quotati i suoi prezzi;
- **un provider di prezzi**, opzionale — scarica per te il prezzo corrente e lo storico ([Provider](providers/index.md));
- **una distribuzione settoriale e geografica**, opzionale;
- **eventi** — dividendi, split, interessi… ([Eventi degli asset](detail/events.md)).

Gli asset sono condivisi da tutti su questo LibreFolio: sono le tue transazioni a decidere quali sono tuoi.

## 📋 Sfogliare l'elenco

Apri **Asset** nella barra laterale, poi:

- **Scegli un layout** — i due pulsanti accanto a **Aggiungi asset** consentono di alternare tra schede con un piccolo grafico (**Vista griglia**) e una tabella ordinabile (**Vista tabella**). La tua scelta viene ricordata in questo browser.
- **Scegli il periodo** — l'intervallo di date imposta il periodo dei grafici delle schede e della variazione che mostrano. Nella tabella, le colonne **Δ** indicano la variazione su un giorno e su ciascun periodo, da 1W a 5Y, che rientra nell'intervallo.
- **Filtra** — digita in **Cerca asset...** per filtrare per nome e scegli una o più valute e tipi nei due menu; la ✕ cancella la ricerca ed entrambi i menu.
- **Mostra asset archiviati** — l'elenco parte con i soli asset **Attivi**: attiva **Inattivi** per aggiungere quelli archiviati, oppure disattiva **Attivi** per vedere solo quelli.

Clicca una scheda o una riga per aprire la **[pagina di dettaglio](detail/index.md)** dell'asset. Lì, le frecce **‹ ›** permettono di scorrere gli asset nell'ordine in cui li mostra questo elenco, filtri e ordinamento inclusi.

??? note "📉 Abs o % sulle schede — solo nella vista griglia"

    **Abs / %** nella barra degli strumenti alterna ogni scheda, il suo grafico e la sua variazione, tra prezzi e percentuali; il pulsante **%** su una scheda alterna solo quella scheda, finché non modifichi di nuovo la barra degli strumenti. La pagina si apre sempre su **%**.

??? note "⚙️ L'aspetto dei grafici delle schede"

    **Impostazioni** nella barra degli strumenti imposta l'aspetto e le sovrapposizioni di tutti i grafici degli asset in una volta, e applicarle sostituisce le impostazioni proprie di ogni asset, pagine di dettaglio incluse. Il ⚙️ su una scheda modifica solo quella scheda. Vedi [Impostazioni grafico](../fx/chart-settings.md).

### 🗂️ I tuoi asset, gli asset di altri utenti, osservati

Entrambi i layout dividono l'elenco in un massimo di tre pannelli, ciascuno con il suo conteggio; un pannello vuoto non viene mostrato.

| Pannello | Che cosa contiene |
|---|---|
| **I tuoi asset** | Asset detenuti attualmente in un broker di tua proprietà |
| **Asset di altri utenti** | Asset detenuti attualmente solo da altri utenti — in broker che non possiedi |
| **Osservati** | Asset che attualmente non sono detenuti da nessuno — mai acquistati o già venduti, tenuti sotto osservazione |

Ciò che conta è la posizione **oggi**: quando vendi tutta la tua posizione, l'asset passa a *Asset di altri utenti* se qualcun altro lo detiene ancora, e a *Osservati* altrimenti. I broker condivisi con te come **Editor** o **Visualizzatore** contano come broker di altri utenti, e una posizione ridotta a un residuo trascurabile conta come non detenuta.

Nella vista tabella ogni pannello è una tabella con le proprie pagine; ridimensionare, spostare o nascondere una colonna vale per tutte e tre.

## 🔄 Mantenere i prezzi aggiornati

- **Sincronizza tutto** apre una finestra in cui **Avvia sincronizzazione** scarica gli ultimi prezzi di ogni asset che ha un provider; **Ricarica tutto** ricarica l'elenco da ciò che LibreFolio ha memorizzato. Nella scheda **[Correlazione](correlation.md)** diventano **Sincronizza selezione**, che scarica anche i tassi di cambio che convertono gli asset selezionati, e **Ricarica tutto**, che ricalcola ogni analisi.
- **Prezzi live** — mentre questa pagina o la pagina di un asset è aperta e l'intervallo di date termina oggi, i prezzi si aggiornano da soli ogni tanto. Un prezzo diventa verde quando è salito rispetto all'aggiornamento precedente, rosso quando è sceso; quando il mercato è chiuso vedi l'ultima chiusura, senza colore.
- **In background**, il server aggiorna i prezzi secondo una pianificazione impostata dal tuo amministratore ([Scheduler dei dati di mercato](../../admin/settings.md#market-data-scheduler)). La dashboard mostra i prezzi memorizzati.

## 🖱️ Agire su un singolo asset

Ogni scheda ha i propri pulsanti; nella tabella, il **⋮** alla fine di una riga, o un clic destro, apre le stesse azioni:

- **Sincronizza** — scarica i prezzi dell'asset per il periodo selezionato. Richiede un provider, e nella tabella blocca questa azione anche per un asset archiviato.
- **Ricarica** — ricarica i suoi prezzi da ciò che LibreFolio ha memorizzato.
- **Unisci con…** — fonde un duplicato in un altro asset, che mantiene tutto ([Crea e modifica](create-edit.md)).
- **Elimina** — rimuove un asset che nessuna transazione utilizza.

Nella tabella, spunta più righe per **Sincronizza**, **Ricarica** o **Elimina** insieme.

??? warning "🗑️ Quando un asset non può essere eliminato"

    Un asset non viene eliminato finché **una qualsiasi** transazione lo utilizza, anche una in un broker che non puoi vedere. Il risultato mostra quante transazioni lo utilizzano, con un link **Transazioni** filtrato su quell'asset. Quella pagina mostra solo i broker a cui puoi accedere, quindi potrebbe elencare meno transazioni rispetto al conteggio.

## 🧭 Funzionalità

### ➕ [Crea e modifica](create-edit.md)

Crea un asset, collegalo a un provider di prezzi e mantieni corretti i suoi dettagli.

### 🧪 [Scheda Correlazione](correlation.md)

Confronta una selezione di asset fianco a fianco — matrice di correlazione, perdite, rischio rispetto al rendimento e replay storico, solo in percentuale.

### 📊 [Pagina di dettaglio asset](detail/index.md)

Il grafico dei prezzi con i suoi segnali, misure ed eventi, l'editor dati e la classificazione.

### 🔌 [Provider](providers/index.md)

Prezzi automatici da Yahoo Finance, justETF, Borsa Italiana, il CSS Scraper o il motore di investimento programmato.

---

## 🔗 Correlati

- 📚 **[Teoria finanziaria — Tipi di asset](../../financial-theory/instruments/asset-types/index.md)** — Azioni, ETF, Obbligazioni, Criptovalute, ecc.
- 💱 **[Tassi di cambio](../fx/index.md)** — Tassi di cambio usati per la conversione tra valute
- 🛠️ **[Prezzi live](../../developer/frontend/components/features/live-ticker.md)** — Per gli sviluppatori: come le pagine effettuano il polling dei prezzi live
