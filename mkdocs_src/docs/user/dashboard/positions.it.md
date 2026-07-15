# 🔍 Posizioni e Analisi

*[⬅️ Torna alla Panoramica della Dashboard](index.md)*

La scheda **Posizioni** della dashboard consente di ispezionare le posizioni aperte, analizzare le performance e approfondire i lotti fiscali corrispondenti.

<div class="lf-screenshot-carousel" data-carousel="carousel-positions-views" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="positions-holdings-table" data-title="📋 Posizioni (Tabella)" alt="Vista Tabellare delle Posizioni">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-holdings-map" data-title="🗺️ Posizioni (Mappa / Treemap)" alt="Vista a Mappa delle Posizioni">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-table" data-title="📈 Performance (Tabella)" alt="Vista Tabellare delle Performance">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-map" data-title="📊 Performance (Mappa / Grafico)" alt="Vista a Mappa delle Performance">
</div>

---

## 🔍 Scheda Posizioni

La scheda **Posizioni** fornisce una ripartizione dettagliata di tutti gli strumenti finanziari attualmente detenuti nel tuo portafoglio (Azioni, ETF, Obbligazioni, Criptovalute, ecc.).

La scheda Posizioni consente di passare tra due modalità metriche principali tramite l'interruttore di vista, ciascuna focalizzata su un aspetto diverso delle posizioni:

#### 📋 Vista Posizioni (Holdings)

La vista **Posizioni** (Holdings) si concentra sulla contabilità, sulle quantità e sulla valutazione attuale degli asset. Ti aiuta a monitorare l'esposizione attuale del portafoglio e le metriche di base.

| Metrica | Descrizione |
|:---|:---|
| **Quantità** | Azioni, unità o valute digitali attualmente detenute nel portafoglio. |
| **Prezzo di Mercato** | Prezzo in tempo reale dell'asset recuperato dal provider di dati collegato. |
| **Valore di Mercato** | Valore totale ai prezzi di mercato correnti (\(\text{Prezzo} \times \text{Quantità}\)). |
| **Prezzo Medio (PMC)** | Il Prezzo Medio di Carico pagato per acquisire la posizione aperta attuale. |
| **Peso** | Quota proporzionale di questo asset rispetto al valore totale del portafoglio. |

#### 📈 Vista Performance

La vista **Performance** si concentra sui rendimenti assoluti e relativi. Ti aiuta ad analizzare la redditività delle tue posizioni aperte, tenendo conto delle transazioni storiche e dei redditi distribuiti.

| Metrica | Descrizione |
|:---|:---|
| **Valore Totale** | Valore attuale delle posizioni (corrisponde al Valore di Mercato). |
| **P&L Non Realizzato** | Guadagno o perdita latente calcolato come \(\text{Valore di Mercato} - \text{Valore Contabile}\). |
| **ROI %** | Tasso di rendimento rispetto alla base di costo della posizione. |
| **P&L Totale** | Rendimento assoluto cumulativo (include vendite passate chiuse e dividendi). |

#### 🗺️ Stile Visivo: Tabella vs. Mappa

| Modalità Visiva | Caratteristiche Principali | Caso d'Uso Ottimale |
|:---|:---|:---|
| **📋 Vista Tabellare** | • Layout a griglia ordinabile<br>• Valori numerici precisi<br>• Ordinamento rapido delle colonne | Contabilità standard, ricerca di quantità specifiche di asset o confronto dei valori PMC. |
| **🗺️ Vista a Mappa** | • Visualizzazione Treemap<br>• La dimensione indica il peso dell'asset<br>• L'intensità del colore indica la performance (verde = guadagno, rosso = perdita) | Diagnostica visiva rapida, individuazione di sovrallocazioni o identificazione di asset con performance inferiori. |

---

## 🔬 Analisi dei Lotti FIFO {: #fifo-lots-analysis }

Quando clicchi su una posizione nella vista Tabella o Mappa, un pannello di **Analisi dei Lotti FIFO** scorre dal lato destro dello schermo. Questo pannello fornisce un'analisi approfondita della fiscalità e della cronologia di abbinamento dei lotti per quell'asset specifico.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-panel" alt="Pannello di Analisi dei Lotti FIFO">
</div>

### 1. Timeline a Bolle

Il grafico della **Timeline a Bolle** visualizza tutti gli acquisti e le vendite nel periodo selezionato:

- 🟢 **Bolle Verdi**: Rappresentano le transazioni di acquisto. La dimensione della bolla rappresenta la quantità acquistata.
- 🔴 **Bolle Rosse**: Rappresentano le transazioni di vendita. La dimensione rappresenta la quantità venduta.
- 🔵 **Linea Blu**: Traccia la progressione storica del tuo Prezzo Medio di Carico (PMC/Valore contabile per azione).
- 🔍 **Suggerimento**: Passando il mouse su qualsiasi bolla vengono rivelati data, tipo di transazione, quantità e prezzo di transazione.

### 2. Grafico del Prezzo PMC

Questo grafico sovrappone la linea del **Prezzo Medio di Carico (PMC)** alla linea storica del **Prezzo di Mercato**. Questo ti aiuta a visualizzare quando hai acquistato rispetto ai movimenti di mercato e se le tue posizioni correnti sono in profitto o in perdita.

🔗 **Teoria**: Fai riferimento a **[Prezzo Medio di Carico (PMC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)** per come viene calcolata la base di costo, e alla **[Catena del Prezzo di Valutazione](../../financial-theory/technical-analysis/performance-metrics/nav.md#valuation-price-chain)** per come i prezzi di mercato vengono risolti dai provider di dati.

### 3. Tabella dei Lotti Aperti

Mostra i **Lotti Fiscali** attivi che sono attualmente aperti (non ancora abbinati a una vendita). Mostra:

- 📅 **Data di Acquisizione**: La data esatta in cui le azioni sono state acquistate.
- 💰 **Prezzo di Acquisizione**: Il prezzo di acquisto originale.
- 📦 **Quantità residua**: Le azioni di questo lotto ancora detenute.
- 📊 **Valore del Lotto**: Valore di mercato corrente di questo lotto specifico.
- 📈 **P&L Non Realizzato**: Guadagno o perdita specifici per questo acquisto.

### 4. Tabella dei Lotti Chiusi

Mostra la cronologia delle **vendite realizzate** in cui un lotto di acquisto è stato abbinato a un lotto di vendita. Aiuta a tracciare:

- 🤝 **Data di Abbinamento**: La data di vendita.
- 📦 **Quantità abbinata**: Le azioni chiuse.
- 💸 **P&L Realizzato**: Il guadagno o la perdita finale riconosciuti dall'abbinamento di questo acquisto con la vendita.

!!! info "Logica di abbinamento FIFO"

    LibreFolio risolve i lotti fiscali seguendo rigorosamente la metodologia contabile **First-In, First-Out (FIFO)**. Le azioni acquisite per prime vengono abbinate per prime a qualsiasi operazione di vendita in entrata.

    Per una panoramica teorica dettagliata su come l'abbinamento FIFO si mappa sul calcolo delle plusvalenze e sulla tassazione, consulta **[Teoria della Tassazione](../../financial-theory/fundamentals/taxation.md)** e il **[Modello di Transazione Acquisto/Vendita](../../financial-theory/instruments/transaction-types/buy-sell.md#fifo-matching)**.

---

## 💸 Scheda Transazioni

La scheda **Transazioni** sulla Dashboard mostra un elenco completo e paginato di tutte le operazioni registrate nell'ambito del portafoglio attivo (ordini di acquisto/vendita, pagamenti di dividendi, depositi di contante, trasferimenti, ecc.).

Per una spiegazione dettagliata dell'elenco delle transazioni, dei filtri e di come leggere i dettagli delle transazioni in sola lettura, consulta la pagina dedicata **[Panoramica delle Transazioni](../transactions/index.md)**.
