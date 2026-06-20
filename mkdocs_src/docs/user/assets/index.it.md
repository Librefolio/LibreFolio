# 💼 Asset

Gli asset sono il cuore di LibreFolio. Rappresentano qualsiasi strumento finanziario posseduto o monitorato: azioni, ETF, obbligazioni, criptovalute o strumenti personalizzati come conti di risparmio con interessi programmati.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="list" data-title="🔲 Vista Griglia a Schede" alt="Asset List Page (Grid)">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="list-table" data-title="📋 Vista Tabella Dati" alt="Asset List Page (Table)">
</div>

## 📌 Cos'è un Asset?

Un asset in LibreFolio è uno strumento finanziario caratterizzato da:

- **Identità**: nome, ISIN, ticker o altri identificativi
- **Categoria**: azione, ETF, obbligazione, crypto, commodity, ecc.
- **Valuta**: la valuta in cui l'asset è denominato
- **Provider**: un provider di prezzi opzionale che recupera automaticamente i prezzi attuali e lo storico
- **Classificazione**: settore e distribuzione geografica (grafici a torta + mappa del mondo)
- **Transazioni**: operazioni di acquisto, vendita, dividendo, interesse collegate a un portafoglio

## 📋 Lista Asset

Naviga verso **Assets** nella barra laterale per vedere tutti i tuoi asset. La pagina della lista offre:

- 🔀 **Layout Griglia / Tabella**: Scegli tra una griglia visiva basata su schede o una tabella dati densa e ordinabile. La tua preferenza di layout viene salvata automaticamente nel `localStorage` del browser e verrà caricata nelle sessioni future.
- 🔎 **Ricerca Intelligente**: Filtra gli asset in tempo reale inserendo un nome, ISIN, ticker o il nome del broker.
- 🏷️ **Filtri per Tipo**: Filtra la lista per visualizzare solo classi specifiche (es. ETF, Azioni, Obbligazioni, Crypto).
- 🗃️ **Asset Archiviati**: Usa l'interruttore per passare dalle posizioni attive agli asset archiviati per mantenere pulita la tua lista.
- ⏱️ **Selettore Delta Temporale**: Cambia l'intervallo di tempo utilizzato per calcolare le variazioni di prezzo (es. `1D`, `1W`, `1M`, `YTD`, `ALL`).
- 🔄 **Sincronizzazione e Aggiornamento**: Sincronizza i dati dei prezzi in tempo reale per tutti i provider configurati o aggiorna manualmente la lista.
- 🖱️ **Menu Contestuale**: Fai clic con il tasto destro su qualsiasi riga nel layout a tabella per azioni rapide (Modifica, Elimina, Sincronizza).

Clicca su qualsiasi scheda asset per navigare verso la sua **[pagina di dettaglio](detail/index.md)**.

## 🧭 Funzionalità

### ➕ [Creazione e Modifica](create-edit.md)

Guida passo-passo per creare nuovi asset, configurare i provider e modificare asset esistenti.

### 📊 [Pagina di Dettaglio Asset](detail/index.md)

Il cuore dell'analisi dell'asset: grafico interattivo, segnali tecnici, misure, classificazione ed editor dati.

### 🔌 [Provider](providers/index.md)

Recupero automatico dei prezzi da Yahoo Finance, justETF, CSS Scraper o dal motore di investimento programmato.

---

## 📡 Prezzi in Tempo Reale e Ticker in Tempo Reale

Per tenerti aggiornato sui movimenti di mercato senza costringerti a continui aggiornamenti della pagina, LibreFolio mostra badge di prezzo live e compatti nelle pagine **Dashboard** e **Dettaglio Asset**.

### ⏱️ Polling Automatico

Durante la visualizzazione di queste pagine, il browser interroga il backend ogni **30 secondi** per i prezzi correnti degli asset. Questo processo avviene silenziosamente in background ed è completamente non bloccante (l'interfaccia utente è pronta istantaneamente e i prezzi vengono caricati man mano che arrivano).

### 🎨 Indicatori Visivi

I badge cambiano colore dinamicamente per indicare i recenti movimenti di prezzo rispetto all'ultimo polling:

* 🟢 **Verde (Su)**: Il prezzo dell'asset è aumentato.
* 🔴 **Rosso (Giù)**: Il prezzo dell'asset è diminuito.
* ⚪ **Grigio (Neutro)**: Il prezzo è invariato, in fase di caricamento o il mercato è attualmente chiuso.

!!! note "Market Closure & Fallbacks"

    Durante i fine settimana o le chiusure del mercato, il ticker in tempo reale mostrerà l'ultimo prezzo di chiusura disponibile in un badge grigio neutro come fallback.

### 🔌 Caching e Scheduler in Background

Per garantire tempi di caricamento rapidi ed evitare che la tua istanza venga limitata o bloccata dai provider esterni (come Yahoo Finance), LibreFolio utilizza una strategia a due livelli:

1. **Scheduler in Background**: Un demone in background sul server aggiorna tutti i prezzi degli asset attivi a intervalli regolari (default: ogni 10 minuti, configurabile dagli amministratori nelle impostazioni Globali). Questo mantiene aggiornati il database e la cache locale dei prezzi.
2. **Cache di Polling On-Demand**: Quando il frontend interroga il backend, legge da questa cache locale aggiornata. Se la cache è fredda, il provider recupera il prezzo e lo memorizza con un TTL (Time-To-Live) di 120 secondi. I successivi aggiornamenti della pagina o le visualizzazioni della dashboard da parte di altri utenti interpellano direttamente la cache locale.

---

## 🔗 Correlati

- 📚 **[Teoria Finanziaria — Tipi di Asset](../../financial-theory/instruments/asset-types/index.md)** — Azioni, ETF, Obbligazioni, Crypto, ecc.
- 💱 **[Tassi FX](../fx/index.md)** — Tassi di cambio valutario utilizzati per la conversione valutaria
