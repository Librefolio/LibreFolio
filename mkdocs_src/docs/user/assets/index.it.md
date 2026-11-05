# 💼 Asset

Gli asset sono gli strumenti che possiedi o segui: azioni, ETF, obbligazioni, criptovalute o un conto di risparmio con interessi programmati. La pagina **Asset** li elenca tutti, ciascuno con un piccolo grafico dei prezzi, e apre la pagina di dettaglio di ognuno di essi.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="list" data-title="🔲 Vista a griglia di schede" alt="Pagina elenco asset (griglia)">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="list-table" data-title="📋 Vista tabella dati" alt="Pagina elenco asset (tabella)">
</div>

## 📌 Che cos'è un asset?

Ogni asset ha:

- **un nome e identificatori** — ISIN, ticker o altri codici;
- **un tipo** — azione, ETF, obbligazione, criptovaluta, materia prima… ([tipi di asset](../../financial-theory/instruments/asset-types/index.md));
- **una valuta** — quella in cui sono quotati i suoi prezzi;
- **un provider di prezzi**, facoltativo — scarica per te il prezzo corrente e lo storico ([Provider](providers/index.md));
- **una distribuzione settoriale e geografica**, facoltativa;
- **eventi** — dividendi, split, interessi… ([Eventi dell'asset](detail/events.md)).

Gli asset sono condivisi da tutti su questo LibreFolio: sono le tue transazioni a decidere quali sono i tuoi.

## 📋 Sfogliare l'elenco

Apri **Asset** nella barra laterale, poi:

- **Scegli un layout** — i due pulsanti accanto a **Aggiungi asset** alternano tra schede con un piccolo grafico (**Vista a griglia**) e una tabella ordinabile (**Vista tabella**). La tua scelta viene ricordata in questo browser.
- **Scegli il periodo** — l'intervallo di date imposta il periodo dei grafici delle schede e della variazione che mostrano. Quando il grafico di una scheda raggruppa i giorni in settimane o mesi perché il tracciato è troppo stretto per così tanti giorni, un piccolo badge **Settimanale** o **Mensile** in alto a sinistra lo segnala, come sul [grafico della pagina di dettaglio](detail/chart.md). Nella tabella, le colonne **Δ** danno la variazione su un giorno e su ciascun periodo, da 1W a 5Y, che rientra nell'intervallo.
- **Filtra** — digita in **Cerca asset...** per filtrare per nome, e scegli una o più valute e tipi nei due menu; la ✕ cancella la ricerca ed entrambi i menu.
- **Mostra asset archiviati** — inizialmente l'elenco mostra solo gli asset **Attivi**: attiva **Inattivi** per aggiungere quelli archiviati, oppure disattiva **Attivi** per vedere solo questi ultimi.

Clicca una scheda o una riga per aprire la **[pagina di dettaglio](detail/index.md)** dell'asset. Lì, le frecce **‹ ›** scorrono gli asset nell'ordine in cui li mostra questo elenco, filtri e ordinamento inclusi.

??? note "📉 Assoluto, % o Rolling Return sulle schede — solo nella vista a griglia"

    L'interruttore nella barra degli strumenti ha tre opzioni: l'icona della linea del grafico, la stessa presente sulle schede, per i prezzi assoluti (il suo tooltip dice **Mostra assoluto**), **%** (la variazione sul periodo) e l'icona del calendario per **Rolling Return**. La scelta si applica a ogni scheda, al suo grafico e alla sua variazione, ed è ricordata in questo browser, per il tuo utente, con le impostazioni grafico.

    Il pulsante di visualizzazione su una scheda passa alla vista successiva, **%** → **Rolling Return** → **Assoluto** → **%**, e mostra la vista verso cui passerà. Una scheda mantiene la propria scelta, anche dopo un ricaricamento, finché non cambi di nuovo l'opzione nella barra degli strumenti: questo riporta ogni scheda alla vista selezionata nella barra degli strumenti.

    In **Rolling Return**, una scheda disegna il rendimento rolling dell'asset, lo stesso rendimento a finestra di calendario della modalità **Rolling Return** della [pagina di dettaglio dell'asset](detail/index.md), e sopra di esso i rendimenti rolling dei confronti di asset salvati su quella scheda. Gli altri indicatori restano salvati, solo nascosti in questa vista. Il prezzo e la variazione in cima alla scheda non cambiano. Se l'asset ha uno storico inferiore alla finestra, la scheda mostra un breve messaggio al posto del grafico.

    La finestra si sceglie in [Impostazioni grafico](../fx/chart-settings.md): 1W, 1M, 3M, 1Y o una personalizzata. Finché non ne scegli una, è automatica: il preset più ampio che rientra nel periodo mostrato nell'elenco, quindi un intervallo di 3 mesi usa 3M e un intervallo di un anno o più usa 1Y.

    La [pagina di dettaglio](detail/index.md) dell'asset si apre nella vista della sua scheda, e con la finestra Rolling Return della scheda. Una vista scelta lì diventa quella della scheda.

??? note "⚙️ L'aspetto dei grafici delle schede"

    **Impostazioni** nella barra degli strumenti imposta l'aspetto e le sovrapposizioni di ogni grafico degli asset in una sola volta, e applicare queste impostazioni sostituisce le impostazioni proprie di ciascun asset, pagine di dettaglio incluse. Il ⚙️ su una scheda cambia solo quella scheda. Vedi [Impostazioni grafico](../fx/chart-settings.md).

### 🗂️ I tuoi asset, gli asset di altri utenti, osservati

Entrambi i layout dividono l'elenco in un massimo di tre pannelli, ciascuno con il suo conteggio; un pannello vuoto non viene mostrato.

| Pannello | Cosa contiene |
|---|---|
| **I tuoi asset** | Asset posseduti oggi in un broker che possiedi |
| **Asset di altri utenti** | Asset posseduti oggi solo da altri utenti — in broker che non possiedi |
| **Osservati** | Asset che oggi nessuno possiede — mai acquistati o già venduti, tenuti sotto osservazione |

Ciò che conta è la posizione **oggi**: quando vendi l'intera posizione, l'asset passa a *Asset di altri utenti* se qualcun altro lo possiede ancora, e a *Osservati* altrimenti. I broker condivisi con te come **Editor** o **Visualizzatore** contano come broker di altri utenti, e una posizione ridotta a un residuo trascurabile conta come non posseduta.

Nella vista tabella ogni pannello è una tabella con le proprie pagine; ridimensionare, spostare o nascondere una colonna si applica a tutte e tre.

## 🔄 Mantenere i prezzi aggiornati

- **Sincronizza tutto** apre una finestra in cui **Avvia sincronizzazione** scarica gli ultimi prezzi di ogni asset che ha un provider; **Ricarica tutto** ricarica l'elenco da ciò che LibreFolio ha memorizzato. Passa il mouse su **Impostazioni**, **Sincronizza tutto** o **Ricarica tutto** per mezzo secondo per leggere cosa fa il pulsante. Quando il periodo contiene già prezzi memorizzati per alcuni degli asset, la finestra lo dice prima che tu inizi: la sincronizzazione li sostituisce con i valori del provider, comprese le tue modifiche manuali. Nella scheda **[Correlazione](correlation.md)** diventano **Sincronizza selezione**, che scarica anche i tassi di cambio che convertono gli asset selezionati, e **Ricarica tutto**, che ricalcola ogni analisi.
- **Prezzi live** — finché l'intervallo di date termina oggi, i prezzi si aggiornano da soli: ogni minuto su questa pagina, ogni 30 secondi sulla pagina di un asset. Un prezzo diventa verde quando è salito rispetto all'aggiornamento precedente, rosso quando è sceso; quando il mercato è chiuso vedi l'ultima chiusura, senza colore. Per risparmiare risorse al server e ai provider di prezzi, l'aggiornamento si mette in pausa mentre la scheda del browser è in background, e dopo due minuti senza usare la pagina: allora una piccola etichetta **Aggiornamenti in pausa** compare in cima alla pagina. Non c'è nulla su cui cliccare: non appena torni sulla scheda, muovi il mouse o premi un tasto: i prezzi si aggiornano di nuovo da soli.
- **In background**, il server aggiorna i prezzi secondo una pianificazione impostata dal tuo amministratore ([Scheduler dei dati di mercato](../../admin/settings.md#market-data-scheduler)). La dashboard mostra i prezzi memorizzati.

## 🖱️ Agire su un singolo asset

Ogni scheda ha i propri pulsanti; nella tabella, il **⋮** alla fine di una riga, o un clic con il tasto destro, apre le stesse azioni:

- **Sincronizza** — scarica i prezzi dell'asset per il periodo selezionato. Richiede un provider; nella tabella l'azione è bloccata anche per un asset archiviato.
- **Ricarica** — ricarica i suoi prezzi da ciò che LibreFolio ha memorizzato.
- **Unisci con…** — fonde un duplicato in un altro asset, che conserva tutto ([Crea e modifica](create-edit.md)).
- **Elimina** — rimuove un asset che nessuna transazione usa, con il suo provider, i prezzi e gli eventi (dividendi, split…).

Nella tabella, spunta diverse righe per **Sincronizza**, **Ricarica** o **Elimina** insieme.

??? warning "🗑️ Quando un asset non può essere eliminato"

    Un asset non viene eliminato finché lo utilizza **anche una sola** transazione, compresa una in un broker che non puoi vedere. Il risultato mostra quante transazioni lo utilizzano, con un link **Transazioni** filtrato per quell'asset. Quella pagina mostra solo i broker a cui puoi accedere, quindi potrebbe elencare meno transazioni del conteggio.

    Quando l'elenco conta già delle transazioni per l'asset, la conferma di eliminazione si apre direttamente su quel risultato, senza il pulsante **Elimina**: non c'è nulla da confermare. Altrimenti il risultato compare dopo la conferma, e LibreFolio effettua comunque un controllo prima di eliminare.

## 🧭 Funzionalità

### ➕ [Crea e modifica](create-edit.md)

Crea un asset, collegalo a un provider di prezzi e mantieni corretti i suoi dettagli.

### 🧪 [Scheda Correlazione](correlation.md)

Confronta una selezione di asset affiancati — matrice di correlazione, perdite, rischio rispetto al rendimento e replay storico, solo in percentuale.

### 📊 [Pagina di dettaglio asset](detail/index.md)

Il grafico dei prezzi con i suoi segnali, misure ed eventi, l'editor dati e la classificazione.

### 🔌 [Provider](providers/index.md)

Prezzi automatici da Yahoo Finance, justETF, Borsa Italiana, lo scraper CSS o il motore di investimento programmato.

---

## 🔗 Correlati

- 📚 **[Teoria finanziaria — Tipi di asset](../../financial-theory/instruments/asset-types/index.md)** — Azioni, ETF, obbligazioni, criptovalute, ecc.
- 💱 **[Tassi FX](../fx/index.md)** — Tassi di cambio usati per la conversione tra valute
- 🛠️ **[Prezzi live](../../developer/frontend/components/features/live-ticker.md)** — Per gli sviluppatori: come le pagine interrogano i prezzi live
