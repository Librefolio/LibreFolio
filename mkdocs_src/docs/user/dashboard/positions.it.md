# 🔍 Posizioni e Analisi

La scheda **Posizioni** della dashboard ti consente di ispezionare le posizioni aperte, analizzare le performance e approfondire i lotti fiscali corrispondenti.

<div class="lf-screenshot-carousel" data-carousel="carousel-positions-views" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="positions-holdings-table" data-title="📋 Posizioni (Tabella)" alt="Holdings Table View">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-holdings-map" data-title="🗺️ Posizioni (Mappa / Treemap)" alt="Holdings Map View">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-table" data-title="📈 Performance (Tabella)" alt="Performance Table View">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-map" data-title="📊 Performance (Mappa / Grafico)" alt="Performance Map View">
</div>

---

## 🔍 Scheda Posizioni

La scheda **Posizioni** ha due modalità semantiche: **Posizioni** e **Performance**.

Usa l'interruttore di visualizzazione per passare dall'una all'altra, e quello tabella/mappa per cambiare il layout visivo.

#### 📋 Vista Posizioni

La vista **Posizioni** mostra l'istantanea delle posizioni aperte. La tabella ha 13 colonne:

| Colonna | Descrizione |
|:---|:---|
| **Asset** | Nome dell'asset con icona del tipo — clicca per aprire la pagina di dettaglio dell'asset. |
| **Δ1** | Variazione del P&L latente rispetto a ieri, a quantità odierna costante. |
| **Δ1%** | La stessa variazione giornaliera in percentuale del valore di mercato della posizione di ieri. |
| **P&L latente** | Guadagno/perdita aperta: valore attuale meno il costo residuo. |
| **P&L %** | P&L latente in percentuale del costo residuo. |
| **Annualizzato** | Rendimento netto annualizzato (CAGR) dei lotti ancora aperti, dalla prima transazione a oggi — per confrontare posizioni detenute per durate diverse. |
| **Valore** | Valore totale ai prezzi di mercato correnti (\(\text{Prezzo} \times \text{Quantità}\)). |
| **Peso** | Quota proporzionale di questa posizione rispetto al valore totale del portafoglio. |
| **Qtà** | Azioni, unità o monete attualmente detenute. |
| **Broker** | Account broker che detengono la posizione. |
| **Prezzo** *(nascosta di default)* | Prezzo attuale dell'asset dal provider collegato. |
| **Costo Medio** *(nascosta di default)* | Costo medio per unità della posizione attualmente aperta (Prezzo Medio di Carico). |
| **Lotto aperto più vecchio** *(nascosta di default)* | Data di apertura del lotto FIFO più vecchio ancora aperto per questa posizione. |

Usa l'**icona a occhio** nella barra degli strumenti della tabella per mostrare o nascondere le colonne — le tue scelte sono ricordate tra le sessioni.

#### 📈 Vista Performance

La vista **Performance** si carica su richiesta e mostra insieme posizioni aperte e chiuse. Nella tabella/mappa, lo **Stato** è filtrabile dentro il componente, non come interruttore di primo livello.

#### 🗺️ Stile Visivo: Tabella vs. Mappa

| Modalità Visiva | Caratteristiche Principali | Caso d'Uso Ottimale |
|:---|:---|:---|
| **📋 Vista Tabella** | • Griglia ordinabile<br>• Valori numerici precisi<br>• Ordinamento rapido delle colonne | Contabilità standard, ricerca di quantità specifiche di asset o confronto dei valori PMC. |
| **🗺️ Vista Mappa** | • Visualizzazione Treemap<br>• La dimensione indica il peso dell'asset<br>• L'intensità del colore indica la performance (verde = guadagno, rosso = perdita) | Diagnostica visiva rapida, individuazione di sovra-allocazioni o identificazione di asset con performance inferiori. |

---

## 🔬 Analisi dei Lotti FIFO {: #fifo-lots-analysis }

Quando fai clic su una posizione nella vista Tabella o Mappa, LibreFolio espande un pannello **Analisi dei Lotti FIFO** direttamente **sotto** la vista Posizioni. Utilizza una transizione a scorrimento verticale e si sposta automaticamente nella visuale — **non** è un pannello laterale destro. Se necessario, appare prima un banner sulla qualità dei dati, poi i blocchi di analisi rimangono in questo ordine: PMC / Prezzo di Mercato, Vita del Lotto e Custodia, tabella dei lotti unificata, confronto Valore/Rendimento e il modale dei dettagli del lotto. Per impostazione predefinita, nessuna selezione esplicita significa che **tutti i lotti attualmente visibili** sono inclusi nei grafici collegati.

<div class="lf-screenshot-carousel" data-carousel="carousel-fifo-lots-analysis" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="fifo-lots-panel" data-title="🔍 Panoramica" alt="FIFO Lots Analysis Overview">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-wac-chart" data-title="📈 PMC / Prezzo di Mercato" alt="WAC and Market Price Chart">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-gantt-chart" data-title="🕒 Vita del Lotto e Custodia" alt="Lot Life and Custody Gantt Chart">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-table" data-title="📋 Tabella Lotti Unificata" alt="Unified Lots Table">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart" data-title="💰 Confronto Valore" alt="Value Comparison Chart">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" data-title="📊 Confronto Rendimento" alt="Return Comparison Chart">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-custody-modal" data-title="🧾 Modale Dettaglio Lotto" alt="Lot Detail Modal">
</div>

### 1. PMC / Prezzo di Mercato

Questo primo grafico confronta il **Prezzo di Mercato** dell'asset con le linee **PMC** per singolo broker e la linea PMC combinata per la posizione selezionata.

- Attiva **ASS / %** per passare dai prezzi assoluti all'evoluzione percentuale dall'inizio dell'intervallo.
- In modalità **ASS**, attiva **Auto / Da 0** per scegliere se l'asse Y è adattato strettamente o forzato a partire da zero.
- Marcatori di eventi e bolle di performance dei lotti ti aiutano a collegare acquisti, vendite, trasferimenti, frazionamenti ed eventi di reddito alla cronologia della base di costo.
- Cliccare sulle bolle dei lotti aggiorna la selezione condivisa dei lotti utilizzata dagli altri blocchi.
- **Il colore della bolla** corrisponde al **broker di apertura** del lotto — gli stessi colori utilizzati dalle barre di custodia nel blocco 2 qui sotto.
- **La dimensione della bolla** riflette il **valore di apertura** del lotto (la sua base di costo originale): bolle più grandi rappresentano investimenti iniziali più grandi.
- Un **bordo della bolla tratteggiato** segna un lotto attualmente mostrato **al costo** perché non è ancora disponibile un prezzo di mercato live.

🔗 **Teoria**: Fare riferimento a **[Prezzo Medio di Carico (PMC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)** per le regole della base di costo e alla **[Catena del Prezzo di Valutazione](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md#valuation-price-chain)** per come vengono risolti i prezzi di mercato.

### 2. Vita del Lotto e Custodia

Il blocco **Vita del lotto e custodia** è una timeline in stile Gantt che mostra quando ogni lotto era aperto e dove era detenuto nel tempo.

- Usa il filtro **Aperto / Chiuso** per mostrare solo i lotti aperti, solo quelli chiusi o entrambi.
- Ogni barra rappresenta la vita di un lotto; i trasferimenti creano corsie di custodia aggiuntive in modo da poter vedere i movimenti da broker a broker e i periodi in transito.
- **Il colore della barra** identifica il **broker di custodia** che attualmente detiene quel segmento del lotto — i badge dei broker corrispondenti sono elencati nella legenda sotto il grafico. Un segmento viola tratteggiato segna un periodo **in transito** tra broker (trasferimento avviato ma non ancora arrivato).
- **Lo spessore della barra** è proporzionale alla **quantità detenuta** durante quel segmento esatto — un lotto che è stato parzialmente venduto o frazionato mostra barre più sottili successivamente.
- Cliccando su una barra si seleziona quel lotto nell'analisi condivisa; un doppio clic può riportare alla riga corrispondente nella tabella.

🔗 **Teoria**: Consultare **[Motore FIFO — Ciclo di Vita del Lotto e Modello di Abbinamento](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md)** per come sono definiti gli stati dei lotti, i frazionamenti e i trasferimenti tra broker.

### 3. Tabella Lotti Unificata

v3 sostituisce le vecchie tabelle separate **Lotti Aperti** e **Lotti Chiusi** con un'unica **tabella unificata**.

- La tabella mostra il set di lotti corrente con colonne come data di apertura, rendimento totale, valore corrente, custodia e **Stato**.
- Il filtraggio condiviso significa che la tabella riflette sempre lo stesso set di lotti visibili dei grafici sopra.
- Il menu **Azioni** di ogni riga include:
 - **Visualizza dettaglio lotto**
 - **Vai al lotto nel Gantt**
 - **Vai alla transazione di apertura**
 - **Copia identificatore lotto**

### 4. Confronto Valore / Rendimento

Questo grafico di confronto si concentra sui lotti attualmente selezionati nel pannello. Se non hai selezionato lotti specifici, utilizza **tutti i lotti visibili**.

- Passa da **Valore** a **Rendimento** utilizzando l'interruttore della modalità in alto a destra.
- La modalità **Valore** confronta i lotti selezionati in termini monetari assoluti e offre anche l'interruttore dell'asse Y **Auto / Da 0**.
- La modalità **Rendimento** confronta la percentuale di rendimento di ciascun lotto dalla sua data di apertura sullo stesso set di lotti selezionato.

### 5. Modale Dettaglio Lotto

Scegli **Visualizza dettaglio lotto** dalle azioni della riga della tabella per aprire il modale **Dettaglio Lotto FIFO** per un lotto specifico.

- Il riepilogo include **P&L Totale**, **Rendimento totale**, **Reddito dell'asset**, **Rendimento in contanti**, P&L FIFO, valore di apertura/corrente e altre metriche a livello di lotto.
- **Custodia Corrente** mostra come il lotto è attualmente distribuito tra broker o in fette in transito.
- **Cronologia** elenca la cronologia completa della custodia e del ciclo di vita, inclusi trasferimenti e altri eventi del lotto, con un'azione diretta **Vai alla transazione** per la transazione pertinente.

!!! info "Logica di abbinamento FIFO"

    LibreFolio risolve la chiusura dei lotti rigorosamente con l'abbinamento **First-In, First-Out (FIFO)**: le quantità vendute consumano sempre il **lotto aperto idoneo più vecchio per primo** prima di toccare lotti più recenti.

    Per teoria e formule più approfondite, consultare:

    - **[Teoria Fiscale](../../financial-theory/fundamentals/taxation.md)**
    - **[Modello di Transazione Acquisto/Vendita](../../financial-theory/instruments/transaction-types/buy-sell.md#fifo-matching)**
    - **[Analisi dei Lotti FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)**

---

## 💸 Scheda Transazioni

La scheda **Transazioni** nella Dashboard visualizza un elenco completo e paginato di tutte le operazioni registrate nell'ambito del portafoglio attivo (ordini di acquisto/vendita, pagamenti di dividendi, depositi di denaro, trasferimenti, ecc.).

Per una spiegazione dettagliata dell'elenco delle transazioni, dei filtri e di come leggere i dettagli delle transazioni in sola lettura, fare riferimento alla pagina dedicata **[Panoramica Transazioni](../transactions/index.md)**.

---

*[⬅️ Torna alla Panoramica della Dashboard](index.md)*
