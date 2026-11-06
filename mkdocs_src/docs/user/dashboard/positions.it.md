# 🔍 Posizioni e analisi

La scheda **Posizioni** mostra ciò che possiedi, quanto ha guadagnato ciascuna posizione nel periodo e, a un clic di distanza, i lotti FIFO dietro qualsiasi posizione. La pagina di ogni broker ha la stessa scheda, limitata a quel broker, con le stesse impostazioni della tabella.

- 📋 **[Posizioni detenute](#holdings)** — ciò che possiedi alla data finale
- 📈 **[Periodo](#performance)** — quanto ha guadagnato ciascuna posizione nel periodo
- 🔬 **[Analisi lotti FIFO](#fifo-lots-analysis)** — i lotti dietro una posizione

<div class="lf-screenshot-carousel" data-carousel="carousel-positions-views" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="positions-holdings-table" data-title="📋 Portafoglio (Tabella)" alt="Vista tabella del portafoglio">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-holdings-map" data-title="🗺️ Portafoglio (Mappa / Treemap)" alt="Vista mappa del portafoglio">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-table" data-title="📈 Periodo (Tabella)" alt="Vista tabella del periodo">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-map" data-title="📊 Periodo (Mappa / Grafico)" alt="Vista mappa del periodo">
</div>

---

## 🎛️ Scegliere una vista

- **[Portafoglio](#holdings) / [Periodo](#performance)** alterna tra ciò che possiedi e quanto ha guadagnato ciascuna posizione; **Tabella / Mappa** (le due icone) tra una tabella e un grafico.
- **L'icona a forma di occhio** (in Tabella) mostra, nasconde o riordina le colonne; **Reimposta layout** le ripristina. **Vedi tutto →** apre la pagina degli asset.
- **Per approfondire una posizione**, apri il suo menu **⋮** in una tabella, oppure fai clic con il pulsante destro del mouse su di essa in qualsiasi vista: **Analizza lotti** apre l'[Analisi lotti FIFO](#fifo-lots-analysis) sotto le posizioni (nella Dashboard come nella pagina di un broker), **Vedi asset** la pagina dell'asset.

LibreFolio ricorda le tue scelte.

---

## 📋 Posizioni detenute — ciò che possiedi {: #holdings }

Cosa possiedi alla data finale e come sta andando ciascuna posizione? **Portafoglio** elenca una riga per asset e broker, a partire dal valore più grande. In fondo, in corsivo, compaiono le posizioni che hai **venduto completamente nel periodo**: non hanno valore, peso né rendimento, ma puoi selezionarle per tracciare la loro linea nel [grafico](#return-of-the-positions) e dispongono delle consuete azioni di riga.

**Colonne mostrate**

| Colonna | Cosa mostra |
|:---|:---|
| **Asset** | L'asset, con l'icona del suo tipo |
| **Δ1** / **Δ1%** | La variazione odierna del P&L latente alla quantità odierna, in denaro e in % del valore di ieri |
| **P&L latente** / **P&L %** | Valore corrente meno quanto è costata la posizione aperta, in denaro e in % di quel costo → [Valore contabile](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md) |
| **Annualizzato** | Rendimento composto annuo dalla prima transazione, redditi e commissioni inclusi → [Rendimento annualizzato netto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/net-annualized-return.md) |
| **YOC** | I dividendi e gli interessi dell'ultimo anno per unità, rispetto al prezzo medio → [Rendimento sul costo](#yield-on-cost-yoc) |
| **Valore** / **Peso** | Quanto vale la posizione e la sua quota del tuo patrimonio netto, liquidità inclusa |
| **Q.tà** | Azioni, unità o monete detenute |
| **Prezzo** *(nascosto)* | Il prezzo unitario utilizzato: il prezzo di mercato, oppure il prezzo del tuo ultimo acquisto o della tua ultima vendita quando non c'è una quotazione; `—` per un asset valorizzato a quanto ti è costato, che non ha alcun prezzo → [Determinazione del prezzo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/price-resolution.md) |
| **Costo medio** *(nascosto)* | Prezzo medio di acquisto per unità, con ogni acquisto al tasso di cambio della propria data → [Prezzo medio di carico (PMC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md) |
| **Lotto aperto più vecchio** *(nascosto)* | Data di apertura del lotto più vecchio ancora aperto presso questo broker; uno split azionario mantiene le date |
| **Broker** | Il broker che detiene la posizione |

**Come leggerla**

- **Il peso include la liquidità**, quindi le righe sommano a meno del 100% quando detieni liquidità.
- **Il peso mostra `—` quando il tuo patrimonio netto è pari a zero o negativo**, ad esempio quando hai preso in prestito più liquidità di quanto valgono le tue posizioni: una sua quota non avrebbe significato.
- **Il costo medio conserva il tasso di cambio di ogni acquisto**, mentre il valore usa quello della data finale: il P&L latente include ciò che il tasso ha fatto nel frattempo.
- **Δ1 confronta due prezzi a due tassi di cambio**: il prezzo di oggi, quello a cui è valorizzata la posizione, al tasso di oggi, rispetto all'ultimo prezzo di mercato fino a ieri al tasso di ieri. Per un asset quotato in un'altra valuta il cui prezzo non si è mosso, Δ1 è solo ciò che il tasso di cambio ha fatto in un giorno, e `0` quando neanche il tasso si è mosso.
- **Nella Mappa**, i riquadri sono raggruppati per broker e tipo di asset; la dimensione è il valore, il colore il P&L %. Scorri per ingrandire, trascina per spostarti e **Reimposta zoom** (↺) mostra di nuovo tutto.

??? info "➖ Celle vuote — quando manca un valore"

    - **`—` in P&L latente, P&L % o Costo medio**: parte di quanto hai pagato è sconosciuta — un tasso di cambio mancante a una data di acquisto, oppure un trasferimento o una rettifica senza costo di carico —, oppure, solo per P&L latente e P&L %, il prezzo non può essere convertito perché manca il tasso di cambio della data finale. Il [banner di qualità dei dati](index.md#data-quality-banner) indica cosa correggere.
    - **`—` in Prezzo, con un P&L latente di `0`**: l'asset non ha alcun prezzo — nessun prezzo di mercato e nessun acquisto o vendita, come quando lo hai ricevuto tramite una rettifica o un trasferimento — quindi il suo Valore è quanto ti è costato.
    - **Δ1** e **Δ1%** richiedono un prezzo di mercato oggi e uno pari o precedente a ieri; nel primo giorno del tuo portafoglio non c'è un giorno precedente, quindi restano vuoti. **Annualizzato** richiede una posizione abbastanza vecchia perché un tasso annuo abbia significato.

### 📉 Rendimento delle posizioni {: #return-of-the-positions }

Quali delle tue posizioni sono andate meglio del portafoglio e quali peggio? Nella Dashboard, la vista **Tabella** sia di **Portafoglio** sia di **Periodo** aggiunge una casella di selezione a ogni riga e, sotto la tabella, un grafico **Rendimento delle posizioni**. Si trova accanto all'allocazione per asset — la torta di oggi e l'area storica, con due pulsanti — a circa 3/5 e 2/5 della riga, come il grafico Crescita e l'Allocazione della Panoramica. La vista **Mappa** non ha grafico.

- **Nessuna selezione**: il grafico mostra solo la linea del portafoglio. **Seleziona una riga**, in una delle due tabelle, per aggiungere una linea per quella posizione, e selezionane altre per confrontarle.
- **La legenda** sotto il titolo ha un pulsante per linea, con il nome dell'asset (un nome troppo lungo per il pulsante scorre da solo): cliccalo per disattivare e riattivare la linea. Una **bandierina** contrassegna una posizione chiusa, e un **segno di avvertimento** una con un prezzo o un tasso di cambio mancante, la cui linea omette quei giorni.
- **Ass. / % / Rolling** cambia la vista; i pulsanti sono sul grafico, in alto a destra, disegnati come nell'elenco Asset: l'icona del **grafico a linea** per **Ass.**, **%** per la percentuale, l'icona del **calendario con le frecce** per **Rolling** (passaci sopra per leggerne il nome). **Ass.** è il profitto o la perdita della posizione in denaro, dall'inizio del periodo. **%** è il suo rendimento in *base 100*: ogni linea parte da 100 il primo giorno del periodo, quindi 112 significa +12%. **Rolling** è descritto più sotto. LibreFolio ricorda la vista.
- **I colori** sono quelli dell'asset: una linea ha il colore che il suo asset ha nella torta e nello storico dell'allocazione accanto, qualunque cosa selezioni e in qualunque ordine. Se due broker detengono lo stesso asset, le loro linee hanno lo stesso colore e si distinguono per il tratto: la prima è piena, l'altra tratteggiata (poi a puntini, poi punto-trattino).
- **Il riquadro che segue il cursore** elenca ogni linea disegnata in quel giorno; un nome troppo lungo per il riquadro scorre da solo.
- **La linea di una posizione chiusa termina il giorno in cui è stata chiusa**; passa il mouse sul pulsante della legenda per vedere la data.
- Si possono disegnare **fino a 50 posizioni** contemporaneamente.

**Rolling — confrontare gli asset tra loro.** Per ogni posizione selezionata, la linea mostra la variazione percentuale del **prezzo** dell'asset su una finestra che scorre lungo il periodo, così asset acquistati in giorni diversi possono essere confrontati su base omogenea. La finestra è la più ampia tra 1 settimana, 1 mese, 3 mesi e 1 anno che rientra nel periodo, finché non ne scegli un'altra: la riga **Finestra** sopra il grafico offre quelle quattro e **Personalizzato**, una durata tua in settimane, mesi o anni. La scelta resta mentre cambi il periodo e torna alla finestra automatica quando lasci la pagina. È **per asset**: due broker che detengono lo stesso asset condividono un'unica linea. In questa vista **non c'è una linea del portafoglio**, poiché il portafoglio non ha un prezzo.

??? info "📐 Perché la linea del portafoglio può differire dalle posizioni"

    La linea del portafoglio è il rendimento misurato dalla Dashboard, il [rendimento ponderato per il tempo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md), non il profitto delle tue posizioni sul capitale impiegato. I due possono quindi differire, anche quando ogni posizione è selezionata; una frase sotto il grafico lo indica. Nei giorni in cui il tuo portafoglio vale zero o meno non esiste un rendimento ponderato per il tempo, quindi la linea del portafoglio presenta un vuoto in **%** ([Quando non viene mostrato il TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md#when-no-twrr)).

### 💸 Rendimento sul costo (YOC) {: #yield-on-cost-yoc }

Quanto reddito ti paga ogni unità rispetto a quanto è costata? **YOC** confronta i dividendi e gli interessi ricevuti da ogni unità negli **ultimi 365 giorni** con il suo prezzo medio di acquisto.

**Come leggerlo**

- **Un valore per asset e broker**, sull'anno che termina alla data finale: spostare la data iniziale non lo cambia.
- **Lordo, non al netto delle imposte**: le transazioni separate di imposte e commissioni non vengono sottratte.
- **Passa il mouse su un valore** per vedere il reddito per unità, il periodo e i tassi di cambio usati — ogni pagamento al tasso della propria data.
- **`0.00%`** significa reddito registrato a zero, oppure correzioni che lo annullano esattamente; un semplice **`-`** significa nessun reddito nell'ultimo anno.

🔗 **Teoria**: [Rendimento sul costo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/yield-on-cost.md) — le regole esatte e in che modo YOC differisce dal rendimento da dividendi o dal CAGR

??? info "🚦 Un trattino con un'icona ⓘ — quando YOC non è disponibile"

    LibreFolio non mostra un YOC parziale. Quando un input non è valido, passa il mouse sull'ⓘ ambra per il motivo: meno di un anno di storico presso questo broker e nessun reddito ancora, un pagamento senza unità detenute il giorno prima, uno storico di acquisti, vendite, trasferimenti o split che non quadra, un tasso di cambio mancante o un prezzo medio sconosciuto. Una volta corretto, YOC viene calcolato di nuovo. Un trattino compare anche quando le correzioni registrate nell'ultimo anno — righe negative più vecchie relative a dividendi o interessi — sommate superano il reddito stesso: l'ⓘ allora recita *Le correzioni superano il reddito dell'ultimo anno.*

---

## 📈 Periodo — quanto ha guadagnato ciascuna posizione {: #performance }

Quali posizioni hanno guadagnato o perso denaro nel periodo, e come? **Periodo** elenca ogni posizione del periodo, aperta o chiusa nel frattempo, a partire dalle variazioni maggiori. LibreFolio lo calcola la prima volta che lo apri, quindi può richiedere un momento.

**Metriche mostrate**

- **P&L periodo**, suddiviso come nella [scheda P&L periodo](kpi-cards.md#card-1-period-pl) in **Variazione non realizzata**, **Vendite**, **Dividendi e interessi** e **Costi** → [P&L periodo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)
- **Annualizzato** — il risultato del periodo come tasso annuo, sul tempo in cui la posizione è stata detenuta nel periodo; `—` per una posizione chiusa nel periodo dopo meno di 30 giorni di detenzione, un intervallo troppo breve perché un tasso annuo abbia significato → [Rendimento annualizzato netto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/net-annualized-return.md)
- **Δ1** / **Δ1%** per le posizioni aperte e, nascosti per impostazione predefinita, **Valore iniziale**, **Valore finale**, **Lotto aperto più vecchio** e **Stato**
- **Altri effetti del periodo** — ciò che non appartiene a nessuna posizione: **Redditi non allocati** e **Costi non allocati**, registrati senza un asset; **Effetto cambio sulla liquidità**, ciò che i tassi di cambio hanno fatto nel periodo sulla liquidità che detieni in un'altra valuta, con una riga solo per un broker la cui liquidità si è mossa; **Trasferimenti a valore di mercato**, quando consideri solo alcuni dei tuoi broker, il guadagno che i titoli trasferiti da o verso un broker esterno alla tua selezione hanno realizzato prima di superare il confine, una riga per broker ([Trasferimenti a valore di mercato](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md#transfers-at-market-value)); e l'**Altro / residuo di riconciliazione**, ciò che resta — una valuta scambiata a un costo, la variazione del tasso di cambio della liquidità in transito tra due dei tuoi broker, titoli in transito tra essi il primo o l'ultimo giorno del periodo, una vendita esclusa dalle **Vendite** perché manca un tasso o un valore di acquisto, oppure il valore di acquisto di un minuscolo residuo — 0,00001 unità o meno, che una vendita di quasi tutte le unità può lasciare e che non conta come posizione → [Effetto cambio sulla liquidità](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md#fx-on-cash)

**Come leggerlo**

- Le **posizioni chiuse** sono in corsivo, oppure riportano un badge **Chiusa** nel grafico; per elencare un solo tipo, mostra **Stato** e filtralo.
- **Nella Mappa**, i guadagni si accumulano a destra dello zero e le perdite a sinistra, con il risultato netto che chiude la riga; ogni percentuale è confrontata con il valore iniziale della posizione.
- Il **P&L periodo** di una posizione può differire dal suo guadagno complessivo: conta solo il periodo.
- **Valore iniziale** e **Valore finale** sono calcolati come il **Valore** in **Portafoglio** — stessi prezzi, un asset senza prezzo a quanto ti è costato, il tasso di cambio di ogni giorno — quindi le righe più gli **Altri effetti del periodo** sommano alla [scheda P&L periodo](kpi-cards.md#card-1-period-pl). Un **`—`** in **Variazione non realizzata** significa che un valore non è stato calcolabile, ad esempio per un tasso di cambio o un valore di acquisto mancante: non è uno zero.
- **I titoli spostati tra due dei tuoi broker** durante il periodo dividono il loro risultato: la riga del broker mittente conserva ciò che hanno fatto fino all'arrivo, quella del broker ricevente ciò che hanno fatto dopo; il totale non cambia.

??? tip "🙈 Nascondi importi — cosa mostra ancora il grafico"

    Con **Nascondi importi** attivo (il pulsante a forma di occhio nella barra superiore), gli importi e l'asse del grafico diventano `•••`, come in `+€•••`. Segni, valute, percentuali, lunghezze delle barre e colori restano, quindi vedi comunque chi ha guadagnato o perso, e quanto rispetto agli altri. Vedi [Modalità privacy](../settings/preferences.md#privacy-mode).

---

## 🔬 Analisi lotti FIFO {: #fifo-lots-analysis }

Quali acquisti compongono una posizione, dove sono detenuti e come si è comportato ciascuno? L'**Analisi lotti FIFO** risponde lotto per lotto: ogni acquisto apre un *lotto* e ogni vendita chiude prima i lotti aperti **più vecchi** — First-In, First-Out.

Scegli **Analizza lotti** su una posizione e il pannello si apre, per i broker della pagina: il tuo filtro broker nella Dashboard, il broker stesso nella sua pagina. Nella Dashboard, come nella pagina di un broker, si apre **sotto le posizioni**: la tabella delle posizioni e il grafico dei rendimenti restano sullo schermo. **Vedi asset** (↗) apre l'asset; **✕** chiude il pannello, e lo stesso fa il pulsante Indietro del browser.

<div class="lf-screenshot-carousel" data-carousel="carousel-fifo-lots-analysis" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="fifo-lots-panel" data-title="🔍 Panoramica" alt="Panoramica dell'analisi lotti FIFO">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-wac-chart" data-title="📈 PMC / Prezzo di mercato" alt="Grafico PMC e prezzo di mercato">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-gantt-chart" data-title="🕒 Vita del lotto e custodia" alt="Grafico di Gantt di vita del lotto e custodia">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-table" data-title="📋 Tabella unificata dei lotti" alt="Tabella unificata dei lotti">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart" data-title="💰 Confronto del valore" alt="Grafico di confronto del valore">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" data-title="📊 Confronto dei rendimenti" alt="Grafico di confronto dei rendimenti">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-custody-modal" data-title="🧾 Dettaglio del lotto (modale)" alt="Finestra modale di dettaglio del lotto">
</div>

**Come funzionano insieme i blocchi**

- **Una sola selezione**: fai clic su bolle, barre o righe della tabella per scegliere i lotti; se non ne è selezionato nessuno, contano tutti i lotti visibili. **Aperti / Chiusi**, sulla linea temporale, filtra ogni blocco.
- **Doppio clic per saltare**: da un indicatore del grafico ai lotti di quella transazione, da una barra della linea temporale alla sua riga nella tabella, e viceversa.
- **Importi completi del broker**: su un broker che possiedi in comproprietà, la tua quota non viene applicata qui, a differenza delle schede KPI e delle Posizioni detenute.

🔗 **Teoria**: [Motore FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md) · [Analisi lotti FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md) · [Abbinamento FIFO](../../financial-theory/instruments/transaction-types/buy-sell.md#fifo-matching) · [Tassazione](../../financial-theory/fundamentals/taxation.md)

### 💹 1. Costo medio / Prezzo di mercato

Come si confronta il prezzo con quanto hai pagato e a che punto è ciascun lotto?

**Metriche mostrate**

- **Prezzo di mercato** — tratteggiato dove LibreFolio lo stima dal tuo ultimo scambio → [Catena dei prezzi di valutazione](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md#valuation-price-chain)
- **Costo medio** — una linea per broker e una linea **Combinata** tratteggiata quando l'asset è detenuto presso più broker → [Prezzo medio di carico (PMC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)
- **Bolle** — una per ogni lotto long, al suo rendimento totale, tra gli indicatori delle tue transazioni e dei tuoi pagamenti → [Analisi lotti FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)

**Come leggerlo**

- **Ass. / %** mostra i prezzi o la loro variazione rispetto al primo punto; **Auto / Da 0** imposta dove inizia l'asse.
- Il **colore della bolla** è il broker di apertura, la sua **dimensione** è la quantità del lotto (**Ass.**) o il suo valore di apertura (**%**); un **bordo tratteggiato** indica una valorizzazione al costo.
- **Un vuoto in una linea del Costo medio** è un giorno in cui il costo medio è sconosciuto: non viene disegnata una media errata.
- **La linea del Prezzo di mercato** copre l'intero periodo, inclusi i giorni senza lotti aperti: dopo che hai venduto tutto, prosegue fino alla data finale.

### 🕒 2. Vita del lotto e custodia

Quando è stato aperto ciascun lotto e quale broker lo deteneva?

**Metriche mostrate**

- **Barre** — una per lotto, colorata in base al broker che lo detiene e spessa quanto la quantità detenuta; viola tratteggiata durante il transito, con una corsia per broker dopo un trasferimento → [Motore FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md)

**Come leggerlo**

- **Aperti / Chiusi** mantiene solo i lotti aperti, solo quelli chiusi o entrambi.
- **Una barra più sottile** ha perso parte della sua quantità, ad esempio per una vendita parziale.
- **Fai clic** su una barra per selezionare il suo lotto, **fai doppio clic** per trovarne la riga nella tabella.
- **Gli indicatori su una barra** sono gli eventi del lotto: ▲ acquisto, ▼ vendita, ◆ trasferimento, **+** rettifica in entrata, **×** rettifica in uscita e │ split. Passa il mouse su un indicatore, toccalo o raggiungilo con la tastiera per vedere cosa è successo, la data, la quantità (nascosta come ••• in modalità privacy) e il broker: un trasferimento tra i tuoi broker mostra **Da** e **A**, uno con un broker esterno al pannello nomina solo il broker che stai guardando, e un punto in cui più eventi cadono nello stesso giorno li elenca tutti. Fai clic o fai doppio clic su un indicatore come faresti sulla sua barra.

### 📋 3. Tabella dei lotti

Ogni lotto con le sue cifre, in base al filtro e alla selezione del pannello.

**Metriche mostrate**

- **Data di apertura**, **P&L totale**, **Rendimento totale**, **Annualizzato**, **Valore corrente**, **Quantità aperta** e **Custodia**, con una riga **Totali** → [Analisi lotti FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Reddito** quando un lotto ne ha ricevuto, e **Commissioni**, **Imposte**, **P&L netto** e **Rendimento netto** quando un lotto sostiene costi → [Costi e metriche nette](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md#costs-and-net-metrics)

**Come leggerla**

- **Fai clic** su una riga per selezionarla, **fai doppio clic** per trovarla nella linea temporale; il colore della riga è il broker di apertura.
- **Il menu ⋮** offre **Vedi dettaglio lotto**, **Vai al lotto nel Gantt**, **Vai alla transazione di apertura** e **Copia identificatore lotto** — un riferimento stabile, utile per l'assistenza.
- **Altre colonne**, come **Valore di apertura**, attendono dietro l'icona a forma di occhio.

### 💰 4. Confronto valore / rendimento

Quanto valgono i lotti selezionati e quanto hanno guadagnato dall'apertura? Se non ne è selezionato nessuno, il grafico copre tutti i lotti visibili.

**Metriche mostrate**

- **Valore** — **Valore residuo**, **Ricavi di vendita** e **Reddito cumulato** impilati fino al **Valore complessivo**, rispetto al **Valore di apertura** → [Analisi lotti FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Rendimento** — il risultato dall'apertura, in denaro (**Ass.**) o in percentuale (**%**): un **Rendimento aggregato**, più una linea per lotto quando ne confronti diversi

**Come leggerlo**

- **Valore complessivo sopra il Valore di apertura**: i lotti hanno guadagnato, incluse vendite e redditi.
- **Una linea tratteggiata** in **Valore** significa che il valore corrente di un lotto è stimato al costo: il suo asset non ha alcun prezzo — nessun prezzo di mercato, nessun acquisto o vendita e nessun trasferimento il cui costo valga come prezzo fino alla data finale.
- **Un inizio piatto**: fino al primo prezzo dell'asset — prezzo di mercato, acquisto o vendita, oppure il costo di un trasferimento che lo ha fatto entrare prima di qualsiasi altra cosa — un lotto, ad esempio uno ricevuto tramite una rettifica, è valorizzato a quanto ti è costato, senza guadagno o perdita. Un giorno il cui prezzo non ha un tasso di cambio viene invece omesso.

### 🧾 5. Dettaglio del lotto

L'intera storia di un lotto. Aprilo con **Vedi dettaglio lotto** (⋮) o facendo clic sulla sua cella **Custodia**.

**Metriche mostrate**

- **Riepilogo** — valore di apertura e corrente, ricavi, **P&L FIFO**, **P&L totale**, **Rendimento totale** e **Rendimento in liquidità** quando il lotto ha ricevuto reddito → [Analisi lotti FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)
- **Dettaglio netto** — il P&L totale meno le commissioni e le imposte allocate al lotto → [Costi e metriche nette](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md#costs-and-net-metrics)
- **Custodia attuale** e **Cronologia** — dove si trova ora il lotto e ogni evento dalla sua apertura. Un trasferimento tra due dei tuoi broker appare come due righe, *A → In transito* e *In transito → B*, anche quando le unità partono e arrivano nello stesso giorno

**Come leggerlo**

- **Le quantità sono le posizioni complete del broker**, come indica l'ⓘ accanto.
- **Un trasferimento con un broker esterno al pannello** conta come unità in entrata o in uscita. Le unità ricevute aprono un nuovo lotto il giorno in cui arrivano, al costo che il trasferimento porta con sé. Le unità inviate chiudono i loro lotti il giorno in cui partono, al prezzo di mercato di quel giorno, quindi il guadagno che hanno realizzato presso questo broker conta come realizzato qui. La Cronologia del lotto etichetta questi movimenti come **TRANSFER+** e **TRANSFER-**, e i grafici li contrassegnano come trasferimenti — ◆ in Vita del lotto e custodia, **Trasferimento in entrata** e **Trasferimento in uscita** sugli indicatori di Costo medio / Prezzo di mercato — senza nominare l'altro broker. Per seguire i lotti originali attraverso lo spostamento, apri il pannello con entrambi i broker (nessun filtro broker nella Dashboard). Un trasferimento ancora in corso l'ultimo giorno del pannello mostra le sue unità come in transito.
- **Vai alla transazione** apre la transazione della riga di Cronologia che hai scelto — per impostazione predefinita, quella di apertura.

??? warning "⚠️ Quando il pannello ti avverte"

    - **Un banner compresso** elenca ciò che manca — un tasso, un prezzo, un valore di acquisto — con una chip per ogni lotto interessato che ne trova la bolla. Correggilo come per il [banner di qualità dei dati](index.md#data-quality-banner). Il banner compresso elenca anche redditi e costi che nessun lotto ha potuto prendere in carico — ad esempio un dividendo pagato dopo che tutti i lotti erano stati venduti — ciascuno con il proprio importo e la propria data.
    - **Un messaggio rosso** significa che le quantità o i trasferimenti di alcune transazioni dell'asset non quadrano, quindi i suoi lotti non possono essere ricostruiti. Elenca ogni transazione da correggere con il giorno, il broker, il problema e un pulsante **Vai alla transazione**. Nel frattempo il pannello nasconde i lotti, la loro linea temporale e il confronto, e il primo grafico mantiene solo le sue linee **Costo medio** e il **Prezzo di mercato**. Correggi quelle transazioni e i lotti ricompaiono.
    - **Valorizzato al costo**: nei giorni precedenti il primo prezzo dell'asset — nessun prezzo di mercato, nessun acquisto o vendita, nessun trasferimento il cui costo valga come prezzo — i suoi lotti sono valorizzati a quanto sono costati, senza guadagno o perdita di mercato, e il banner nomina quei giorni. Se non esiste alcun prezzo fino alla data finale, la bolla del lotto ha un bordo tratteggiato.

---

## 🔗 Correlati

- 💰 **[Schede KPI](kpi-cards.md)** — gli stessi risultati per l'intero portafoglio
- 💸 **[Transazioni](../transactions/index.md)** — la scheda **Transazioni** della Dashboard elenca le operazioni dell'intervallo e dei broker selezionati
- 🛠️ **[Dettagli tecnici](../../developer/frontend/pages/index.md#dashboard)** — per gli sviluppatori: come funzionano internamente la scheda Posizioni e il pannello dei lotti

---

*[⬅️ Torna alla Panoramica della Dashboard](index.md)*
