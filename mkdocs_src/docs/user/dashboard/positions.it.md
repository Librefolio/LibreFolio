# 🔍 Posizioni & Analisi

La scheda **Posizioni** mostra ciò che possiedi, quanto ha guadagnato ciascuna posizione nel periodo e, a un clic di distanza, i lotti FIFO dietro qualsiasi posizione. La pagina di ciascun broker ha la stessa scheda per quel singolo broker, con le stesse impostazioni della tabella.

- 📋 **[Posizioni](#holdings)** — ciò che possiedi alla data finale
- 📈 **[Performance](#performance)** — quanto ha guadagnato ciascuna posizione nel periodo
- 🔬 **[Analisi Lotti FIFO](#fifo-lots-analysis)** — i lotti dietro una posizione

<div class="lf-screenshot-carousel" data-carousel="carousel-positions-views" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="positions-holdings-table" data-title="📋 Posizioni (Tabella)" alt="Vista Tabella Posizioni">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-holdings-map" data-title="🗺️ Posizioni (Mappa / Treemap)" alt="Vista Mappa Posizioni">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-table" data-title="📈 Performance (Tabella)" alt="Vista Tabella Performance">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-map" data-title="📊 Performance (Mappa / Grafico)" alt="Vista Mappa Performance">
</div>

---

## 🎛️ Scegliere una vista

- **Portafoglio / Periodo** alterna tra [Posizioni](#holdings) e [Performance](#performance); **Tabella / Mappa** (le due icone) tra una tabella e un grafico.
- **L'icona a forma di occhio** (in Tabella) mostra, nasconde o riordina le colonne; **Ripristina layout** le ripristina. **Vedi tutto →** apre la pagina Asset.
- **Per approfondire una posizione**, apri il suo menu **⋮** in una tabella, oppure fai clic con il tasto destro su di essa in qualsiasi vista: **Analizza Lotti** apre l'[Analisi Lotti FIFO](#fifo-lots-analysis) qui sotto, **Vedi Asset** la pagina dell'asset.

LibreFolio ricorda le tue scelte.

---

## 📋 Posizioni — ciò che possiedi {: #holdings }

Cosa possiedi alla data finale, e come sta andando ciascuna posizione? **Portafoglio** elenca una riga per asset e broker, dal valore più grande in poi.

**Colonne mostrate**

| Colonna | Cosa mostra |
|:---|:---|
| **Asset** | L'asset, con l'icona del suo tipo |
| **Δ1** / **Δ1%** | La variazione odierna del P&L latente alla quantità odierna, in denaro e in % del valore di ieri |
| **P&L latente** / **P&L %** | Il valore attuale meno quanto è costata la posizione aperta, in denaro e in % di quel costo → [Valore contabile](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md) |
| **Annualizzato** | Il rendimento composto annuo dalla prima transazione, reddito e commissioni inclusi → [Rendimento annualizzato netto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/net-annualized-return.md) |
| **YOC** | I dividendi e gli interessi dell'ultimo anno per unità, rispetto al suo prezzo medio → [Rendimento sul Costo](#yield-on-cost-yoc) |
| **Valore** / **Peso** | Quanto vale la posizione, e la sua quota del tuo Patrimonio Netto, liquidità inclusa |
| **Qtà** | Azioni, unità o monete possedute |
| **Prezzo** *(nascosta)* | Il prezzo unitario utilizzato: il prezzo di mercato, oppure il prezzo dell'ultimo scambio quando non c'è una quotazione → [Risoluzione del prezzo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/price-resolution.md) |
| **PMC (Prezzo Medio di Carico)** *(nascosta)* | Il prezzo medio di acquisto per unità, ogni acquisto al tasso di cambio della propria data → [Prezzo Medio di Carico (PMC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md) |
| **Lotto aperto più vecchio** *(nascosta)* | La data di apertura del lotto più vecchio ancora aperto |
| **Broker** | Il broker che detiene la posizione |

**Come leggerla**

- **Il Peso conta la liquidità**, quindi le righe sommano a meno del 100% quando detieni liquidità.
- **Il PMC mantiene il tasso di cambio di ogni acquisto**, mentre il Valore usa quello della data finale: il P&L latente include ciò che il tasso ha fatto da allora.
- **Nella Mappa**, i riquadri sono raggruppati per broker e tipo di asset; la dimensione è il valore, il colore il P&L %. Scorri per fare zoom, trascina per spostarti, e **Reset zoom** (↺) mostra di nuovo tutto.

??? info "➖ Celle vuote — quando manca un valore"

    - **`—` in P&L latente, P&L % o PMC**: l'asset non ha alcun prezzo, oppure parte di quanto hai pagato è sconosciuta — un tasso di cambio mancante a una data di acquisto, oppure un trasferimento o una rettifica senza costo di carico. Il [banner di qualità dei dati](index.md#data-quality-banner) indica cosa correggere.
    - **Δ1** e **Δ1%** richiedono un prezzo di mercato; **Annualizzato** richiede una posizione abbastanza vecchia perché un tasso annuo abbia un senso.

### 💸 Rendimento sul Costo (YOC) {: #yield-on-cost-yoc }

Quanto reddito ti paga ciascuna unità, rispetto a quanto è costata? **YOC** confronta i dividendi e gli interessi ricevuti da ciascuna unità negli **ultimi 365 giorni** con il suo prezzo medio di acquisto.

**Come leggerlo**

- **Un valore per asset e broker**, sull'anno che termina alla data finale: spostare la data iniziale non lo cambia.
- **Lordo, non al netto delle imposte**: le transazioni separate di imposte e commissioni non vengono sottratte.
- **Passa il mouse su un valore** per il reddito per unità, il periodo e i tassi di cambio usati — ogni pagamento al tasso della propria data.
- **`0.00%`** significa reddito registrato a zero; un semplice **`-`** significa nessun reddito nell'ultimo anno.

🔗 **Teoria**: [Rendimento sul Costo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/yield-on-cost.md) — le regole esatte, e come YOC differisce dal rendimento da dividendi o dal CAGR

??? info "🚦 Un trattino con un'icona ⓘ — quando YOC non è disponibile"

    LibreFolio non mostra uno YOC parziale. Quando un input non è valido, passa il mouse sull'ⓘ ambra per il motivo: meno di un anno di storico presso questo broker e ancora nessun reddito, un pagamento senza unità possedute il giorno prima, uno storico di acquisti, vendite, trasferimenti o split che non quadra, un tasso di cambio mancante, oppure un prezzo medio sconosciuto. Una volta corretto, YOC viene ricalcolato.

---

## 📈 Performance — quanto ha guadagnato ciascuna posizione {: #performance }

Quali posizioni hanno guadagnato o perso denaro nel periodo, e come? **Periodo** elenca ogni posizione del periodo, aperta o chiusa da allora, dalle variazioni maggiori in poi. LibreFolio la calcola la prima volta che la apri, quindi può richiedere un momento.

**Metriche mostrate**

- **P&L periodo**, suddiviso come nella [scheda P&L periodo](kpi-cards.md#card-1-period-pl) in **Variazione latente**, **Vendite**, **Dividendi & interessi** e **Costi** → [P&L periodo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)
- **Annualizzato** — il risultato del periodo come tasso annuo, sul tempo in cui la posizione è stata detenuta nel periodo → [Rendimento annualizzato netto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/net-annualized-return.md)
- **Δ1** / **Δ1%** per le posizioni aperte e, nascosti per impostazione predefinita, **Valore Iniziale**, **Valore Finale**, **Lotto aperto più vecchio** e **Stato**
- **Altri Effetti di Periodo** — ciò che non appartiene a nessuna posizione: **Reddito non allocato** e **Costi non allocati**, registrati senza un asset, e il **Residuo Altro / riconciliazione**

**Come leggerla**

- **Le posizioni chiuse** sono in corsivo, oppure portano un badge **Chiuso** nel grafico; per elencarne un solo tipo, mostra **Stato** e filtralo.
- **Nella Mappa**, i guadagni si impilano a destra dello zero e le perdite a sinistra, con il risultato netto che chiude la riga; ciascuna percentuale si confronta con il valore iniziale della posizione.
- **Il P&L periodo di una posizione** può differire dal suo guadagno complessivo: conta solo il periodo.

??? tip "🙈 Nascondi importi — cosa mostra ancora il grafico"

    Con **Nascondi importi** attivo (il pulsante a forma di occhio nella barra superiore), gli importi e l'asse del grafico diventano `•••`, come in `+€•••`. Segni, valute, percentuali, lunghezze e colori delle barre restano, quindi vedi comunque chi ha guadagnato o perso, e quanto rispetto agli altri. Vedi [Modalità privacy](../settings/preferences.md#privacy-mode).

---

## 🔬 Analisi Lotti FIFO {: #fifo-lots-analysis }

Da quali acquisti è composta una posizione, dove sono detenuti, e come è andato ciascuno? L'**Analisi Lotti FIFO** risponde lotto per lotto: ogni acquisto apre un *lotto*, e ogni vendita chiude prima i lotti aperti **più vecchi** — First-In, First-Out.

Scegli **Analizza Lotti** su una posizione e il pannello si apre sotto, per i broker della pagina: il tuo filtro broker nella dashboard, il broker stesso nella sua pagina. **Vedi Asset** (↗) apre l'asset, **✕** chiude il pannello.

<div class="lf-screenshot-carousel" data-carousel="carousel-fifo-lots-analysis" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="fifo-lots-panel" data-title="🔍 Panoramica" alt="Panoramica Analisi Lotti FIFO">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-wac-chart" data-title="📈 PMC / Prezzo di Mercato" alt="Grafico PMC e Prezzo di Mercato">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-gantt-chart" data-title="🕒 Vita del Lotto & Custodia" alt="Grafico Gantt Vita del Lotto e Custodia">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-table" data-title="📋 Tabella Unificata dei Lotti" alt="Tabella Unificata dei Lotti">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart" data-title="💰 Confronto Valori" alt="Grafico Confronto Valori">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" data-title="📊 Confronto Rendimenti" alt="Grafico Confronto Rendimenti">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-custody-modal" data-title="🧾 Modale Dettaglio Lotto" alt="Modale Dettaglio Lotto">
</div>

**Come i blocchi lavorano insieme**

- **Una sola selezione**: fai clic sulle bolle, sulle barre o sulle righe della tabella per scegliere i lotti; senza alcuna selezione, conta ogni lotto visibile. **Aperti / Chiusi**, sulla timeline, filtra ogni blocco.
- **Doppio clic per saltare**: da un marcatore di un grafico ai lotti di quella transazione, da una barra della timeline alla sua riga in tabella, e viceversa.
- **Importi completi del broker**: su un broker di cui sei co-proprietario, la tua quota non viene applicata qui, a differenza delle schede KPI e delle Posizioni.

🔗 **Teoria**: [Motore FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md) · [Analisi Lotto FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md) · [Abbinamento FIFO](../../financial-theory/instruments/transaction-types/buy-sell.md#fifo-matching) · [Tassazione](../../financial-theory/fundamentals/taxation.md)

### 💹 1. PMC / Prezzo di Mercato

Come si confronta il prezzo con quanto hai pagato, e dove si colloca ciascun lotto?

**Metriche mostrate**

- **Prezzo di Mercato** — tratteggiato dove LibreFolio lo stima dal tuo ultimo scambio → [Catena di valutazione del prezzo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md#valuation-price-chain)
- **PMC** — una linea per broker, e una linea **Combinata** tratteggiata quando l'asset è presso diversi → [Prezzo Medio di Carico (PMC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)
- **Bolle** — una per lotto long, al suo rendimento totale, tra i marcatori delle tue transazioni e dei tuoi pagamenti → [Analisi Lotto FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)

**Come leggerlo**

- **Abs / %** mostra i prezzi o la loro variazione dal primo punto; **Auto / Da 0** imposta da dove inizia l'asse.
- **Il colore della bolla** indica il broker di apertura, la sua **dimensione** la quantità del lotto (**Abs**) o il suo valore di apertura (**%**); un **bordo tratteggiato** significa valutato al costo.
- **Un vuoto in una linea PMC** è un giorno di cui il prezzo medio di carico è sconosciuto: non viene tracciata alcuna media errata.

### 🕒 2. Vita del Lotto & Custodia

Quando era aperto ciascun lotto, e quale broker lo deteneva?

**Metriche mostrate**

- **Barre** — una per lotto, colorata dal broker che lo detiene e con spessore proporzionale alla quantità detenuta; viola tratteggiata mentre è in transito, con una corsia per broker dopo un trasferimento → [Motore FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md)

**Come leggerlo**

- **Aperti / Chiusi** mantiene solo i lotti aperti, solo quelli chiusi, oppure entrambi.
- **Una barra più sottile** ha perso parte della sua quantità, per esempio per una vendita parziale.
- **Fai clic** su una barra per selezionare il suo lotto, **fai doppio clic** per trovare la sua riga in tabella.

### 📋 3. Tabella dei Lotti

Ogni lotto con le sue cifre, seguendo il filtro e la selezione del pannello.

**Metriche mostrate**

- **Data di Apertura**, **P&L Totale**, **Rendimento totale**, **Annualizzato**, **Valore Attuale**, **Quantità Aperta** e **Custodia**, con una riga **Totali** → [Analisi Lotto FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Reddito** quando un lotto ha ricevuto del reddito, e **Commissioni**, **Imposte**, **P&L Netto** e **Rendimento netto** quando un lotto sopporta dei costi → [Costi e metriche nette](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md#costs-and-net-metrics)

**Come leggerla**

- **Fai clic** su una riga per selezionarla, **fai doppio clic** per trovarla nella timeline; il colore della riga è il broker di apertura.
- **Il menu ⋮** offre **Vedi dettaglio lotto**, **Vai al lotto nel Gantt**, **Vai alla transazione di apertura** e **Copia identificatore del lotto** — un riferimento stabile, comodo per l'assistenza.
- **Altre colonne**, come **Valore di Apertura**, attendono dietro l'icona a forma di occhio.

### 💰 4. Confronto Valore / Rendimento

Quanto valgono i lotti selezionati, e quanto hanno guadagnato dall'apertura? Senza alcuna selezione, il grafico copre ogni lotto visibile.

**Metriche mostrate**

- **Valore** — **Valore residuo**, **Ricavato dalle vendite** e **Reddito cumulato** impilati fino al **Valore complessivo**, rispetto al **Valore di apertura** → [Analisi Lotto FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Rendimento** — il risultato dall'apertura, in denaro (**Abs**) o in percentuale (**%**): un **Rendimento aggregato**, più una linea per lotto quando ne confronti diversi

**Come leggerlo**

- **Valore complessivo sopra il Valore di apertura**: i lotti hanno guadagnato, vendite e reddito inclusi.
- **Una linea tratteggiata** in **Valore** è un valore stimato al costo, senza un prezzo di mercato.

### 🧾 5. Dettaglio Lotto

L'intera storia di un lotto. Aprilo con **Vedi dettaglio lotto** (⋮) oppure facendo clic sulla sua cella **Custodia**.

**Metriche mostrate**

- **Riepilogo** — valore di apertura e attuale, ricavato, **P&L FIFO**, **P&L Totale**, **Rendimento totale**, e **Cash yield** quando il lotto ha ricevuto reddito → [Analisi Lotto FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Ripartizione netta** — il P&L totale meno le commissioni e le imposte allocate al lotto → [Costi e metriche nette](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md#costs-and-net-metrics)
- **Custodia Attuale** e **Storico** — dove si trova ora il lotto, e ogni evento dalla sua apertura

**Come leggerlo**

- **Le quantità sono le disponibilità complete del broker**, come dice l'ⓘ accanto ad esse.
- **Vai alla transazione** apre la transazione della riga dello Storico che hai scelto — per impostazione predefinita, quella di apertura.

??? warning "⚠️ Quando il pannello ti avverte"

    - **Un banner ripiegato** elenca ciò che manca — un tasso, un prezzo, un valore di acquisto — con un chip per ogni lotto interessato che trova la sua bolla. Correggilo come per il [banner di qualità dei dati](index.md#data-quality-banner).
    - **Un messaggio rosso** significa che le quantità o i trasferimenti non quadrano: le cifre possono essere incomplete, quindi controlla le transazioni dell'asset.
    - **Un lotto valutato al costo** non ha un prezzo di mercato: bordo della bolla tratteggiato, nessun guadagno o perdita di mercato.

---

## 🔗 Correlati

- 💰 **[Schede KPI](kpi-cards.md)** — gli stessi risultati per l'intero portafoglio
- 💸 **[Transazioni](../transactions/index.md)** — la scheda **Transazioni** della dashboard elenca le operazioni dell'intervallo e dei broker selezionati
- 🛠️ **[Dettagli tecnici](../../developer/frontend/pages/index.md#dashboard)** — per gli sviluppatori: come funzionano dall'interno la scheda Posizioni e il pannello dei lotti

---

*[⬅️ Torna a Panoramica dashboard](index.md)*
