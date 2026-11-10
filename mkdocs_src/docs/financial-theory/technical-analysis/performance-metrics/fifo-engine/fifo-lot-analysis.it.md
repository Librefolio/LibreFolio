# 🔬 Analisi dei Lotti FIFO

L'analisi dei lotti FIFO è il complemento **per singolo lotto** del [Prezzo medio di carico (PMC)](../weighted-average-cost.md).

Il PMC risponde a: _"Qual è il mio costo medio ponderato per questa posizione?"_ L'analisi dei lotti FIFO risponde a una domanda diversa: _"Come si comporta nel tempo ciascun singolo lotto di acquisto?"_

Invece di fondere tutti gli acquisti in un unico pool, LibreFolio traccia ogni lotto attraverso il proprio ciclo di vita — **aperto**, **parzialmente chiuso**, **completamente chiuso** — e abbina le vendite in ordine **FIFO** (first in, first out).

!!! info "Complemento, non sostituto"

    Il PMC è aggregato e a livello di posizione. L'analisi dei lotti FIFO è granulare e a livello di lotto. Entrambe le viste sono utili: una per il costo di carico ponderato, l'altra per l'attribuzione economica lotto per lotto.

---

## 💡 Che cos'è l'Analisi dei Lotti FIFO?

Un **lotto** è un singolo blocco di acquisizione: per esempio un acquisto di 100 azioni, oppure un trasferimento in entrata che conserva il costo di carico storico.

Quando avviene una vendita, i lotti ancora aperti più vecchi vengono chiusi per primi. Questo crea una storia lotto per lotto:

- quanto di ciascun lotto è ancora aperto
- quanto è già stato venduto
- quanti proventi di vendita quel lotto ha generato
- quanto reddito è stato guadagnato mentre quel lotto era detenuto
- quanta parte del rendimento deriva dalla variazione di prezzo rispetto al reddito monetario

Questo rende l'analisi dei lotti FIFO particolarmente utile quando due posizioni nello stesso asset sono state acquistate a prezzi o date molto diversi.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-gantt-chart" alt="Cronologia Lot Life & Custody — ogni barra è un lotto, colorata in base al broker depositario, spessore proporzionale alla quantità detenuta">
</div>

La cronologia **Lot Life & Custody** qui sopra rende visivo il ciclo di vita: ogni barra è un lotto, colorata in base al broker che lo detiene attualmente, con spessore proporzionale alla quantità ancora detenuta in quel segmento. Una barra che termina a metà grafico è un lotto completamente chiuso; una barra che arriva a "oggi" è ancora aperta.

---

## 🧮 Open Return per Lotto

**Open Return** isola la variazione **solo di prezzo** di un lotto rispetto al suo prezzo di riferimento di apertura.

$$
\text{RelativeReturn} = \frac{\text{MarketPrice}}{\text{ReferenceUnitPrice}} - 1
$$

$\text{MarketPrice}$ è la quotazione dell'asset fornita dal [resolver unificato](../portfolio-engine/price-resolution.md): alla data finale per il riepilogo del lotto, in ogni giorno per la storia dei rendimenti. Il riferimento dipende da ciò che ha aperto il lotto:

- **Una compravendita** — un acquisto, o una vendita che apre un lotto short: il prezzo unitario del lotto stesso, anche quando l'asset ha una quotazione di mercato quel giorno. Una compravendita è un prezzo.
- **Una rettifica** — una posizione di apertura, una successione, un trasferimento da un broker non tracciato: il suo costo di carico è un costo, non un prezzo, quindi il riferimento è la quotazione dell'asset nel giorno di apertura. Ovvero il prezzo dell'ultimo giorno pari o precedente che ne abbia uno — la sua quotazione di mercato o, in assenza di quotazione, il prezzo medio delle sue compravendite di acquisto e vendita, mai una rettifica — mantenuto. Per un asset che non ha ancora nient'altro, anche il costo di un trasferimento in entrata è un prezzo di questo tipo, come [stima](../portfolio-engine/price-resolution.md#transfer-cost-estimate): un trasferimento da un broker fuori dall'ambito, su un asset privo di quotazione e senza altre operazioni in quel giorno o in un giorno precedente, ottiene il proprio costo come riferimento, contrassegnato come fallback (`REFERENCE_PRICE_FALLBACK`).
- **Una rettifica prima di qualsiasi prezzo** — nessuna quotazione, acquisto, vendita o stima del costo di trasferimento nel giorno di apertura o in un giorno precedente: il prezzo unitario del lotto stesso, il suo costo di carico per unità. Senza un costo di carico quel prezzo è zero, e il lotto non ha Open Return.

`reference_price_source` è `exact` per una quotazione di mercato del giorno di apertura stesso e per il prezzo del lotto stesso, e `fallback` per una quotazione mantenuta da un giorno precedente o per un prezzo derivato dalle compravendite. Il banner di qualità dei dati segnala tale fallback (`REFERENCE_PRICE_FALLBACK`), e una rettifica senza prezzo nel giorno di apertura o in un giorno precedente (`REFERENCE_PRICE_UNAVAILABLE`).

Ogni prezzo viene convertito nella valuta di destinazione al tasso di cambio del proprio giorno: $\text{MarketPrice}$ al tasso di cambio del giorno che valorizza, il riferimento al tasso di cambio della data di apertura, anche quando è stato mantenuto da una quotazione o compravendita precedente. Per un prezzo in una valuta diversa da quella di destinazione, l'Open Return include quindi anche la variazione del tasso di cambio dall'apertura.

Questa metrica esclude dividendi, interessi e proventi di vendita realizzati. Risponde a: _"Quanto si è mosso il prezzo di mercato da quando questo lotto è stato aperto?"_

!!! example "Un lotto ricevuto per successione"

    Un asset è quotato a 50 il 7 marzo e acquistato a 52 il 9 marzo, senza quotazioni successive. Un lotto ricevuto per successione il 10 marzo ha un riferimento di **52**: l'acquisto è il prezzo più recente dell'asset in quel giorno o in un giorno precedente, mantenuto. Il suo `reference_price_source` è `fallback`, poiché 52 non è una quotazione del 10 marzo; una quotazione del 10 marzo stesso sarebbe invece il riferimento, con `exact`.

!!! tip "Il prezzo del lotto stesso, sull'asse delle quotazioni"

    Quando il riferimento è il prezzo del lotto stesso, LibreFolio lo scala alla convenzione di quotazione dell'asset. Questo evita rendimenti percentuali fuorvianti su strumenti quotati per 100 unità nominali. Una quotazione proveniente dal resolver è già su quell'asse.

    Il riferimento diventa quindi $\text{OpeningUnitPrice}\times qbq$. Con `qbq = 100`, un'obbligazione acquistata a `0.992` viene confrontata con l'asse della quotazione di mercato come `99.20`, non `0.992`.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-wac-chart" alt="Grafico PMC / Market Price — una bolla per lotto, colorata in base al broker di apertura, dimensionata in base al valore di apertura, tracciata rispetto alla linea del prezzo di mercato">
</div>

Il grafico **PMC / Market Price** rappresenta ogni lotto come una bolla rispetto alla linea del prezzo di mercato: il colore della bolla indica il broker presso cui il lotto è stato aperto, la dimensione della bolla è proporzionale al valore di apertura del lotto. Un lotto il cui valore corrente è stimato al costo — il suo asset non ha alcun prezzo alla data finale, vedi [Estimated-at-Cost](#estimated-at-cost) — è disegnato con un contorno tratteggiato.

---

## 💰 Total Return per Lotto

**Total Return** è più ampio dell'Open Return. Include il valore di mercato residuo del lotto, eventuali proventi di vendita già realizzati da quel lotto — una rettifica in uscita non ne aggiunge, non avendo valore — e qualsiasi reddito allocato ricevuto mentre il lotto era detenuto.

Il calcolo dei lotti di LibreFolio usa esattamente questi elementi costitutivi:

$$
\text{OpeningValue} = \text{OriginalCost}
$$

$$
\text{Proceeds}(t) = \sum \text{Closure Proceeds} \text{ up to } t
$$

$$
\text{TotalValue}(t) = \text{OpenValue}(t) + \text{Proceeds}(t)
$$

$$
\text{PnL}(t) = \text{TotalValue}(t) - \text{OriginalCost}
$$

$$
\text{MarketPnL} = \text{PnL} - \text{RealizedPnL}
$$

$$
\text{RealizedPnL} = \sum \text{Closure Realized PnL}
$$

$$
\text{AssetIncome} = \sum_t \text{Income}_i(t)
$$

$$
\text{TotalPnL} = \text{MarketPnL} + \text{RealizedPnL} + \text{AssetIncome}
$$

Ogni importo è espresso nella valuta di destinazione dell'analisi. Per un lotto acquistato o venduto in un'altra valuta, ciascuna chiusura converte le sue due componenti alle rispettive date — vedi [Lotti in un'Altra Valuta](#lots-in-another-currency).

Per il riepilogo scalare del lotto, la percentuale di rendimento è:

$$
\text{TotalReturn} = \frac{\text{TotalPnL}}{\text{OpeningValue}}
$$

Per la storia dei rendimenti nel tempo, LibreFolio usa:

$$
\text{TotalReturn}(t) = \frac{\text{TotalValue}(t) + \text{Income}(t)}{\text{OriginalCost}} - 1
$$

Questo risponde a: _"Qual è il rendimento economico completo di questo lotto, includendo sia la variazione di prezzo sia il rendimento monetario?"_

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" alt="Grafico di confronto Value / Return in modalità Return — rendimento percentuale per lotto dalla data di apertura di ciascun lotto">
</div>

Il grafico di confronto **Value / Return**, impostato in modalità **Return**, traccia esattamente questa percentuale — una linea per lotto, ciascuna misurata dalla propria data di apertura, sull'insieme di lotti attualmente selezionato.

### 💱 Lotti in un'Altra Valuta {: #lots-in-another-currency }

Le due componenti di una chiusura vengono convertite nella valuta di destinazione **ciascuna nella propria valuta, alla propria data**: il costo delle unità nella valuta del lotto alla data di apertura del lotto — il tasso di cambio di acquisto — e il prezzo di chiusura nella valuta della transazione di chiusura alla data di chiusura — il tasso di cambio di vendita. Con $\text{Convert}(x, ccy, D)$ l'importo $x$ nella valuta $ccy$ convertito nella valuta di destinazione al tasso di cambio della data $D$, una chiusura di $q$ unità di un lotto LONG aperto il $D_{\text{open}}$ a $\text{LotUnitCost}$ in $ccy_{\text{lot}}$, e chiuso il $D_{\text{close}}$ a $\text{ClosePrice}$ in $ccy_{\text{close}}$, dà:

$$
\text{Closure Proceeds} = \text{Convert}\left(q \cdot \text{ClosePrice},\ ccy_{\text{close}},\ D_{\text{close}}\right)
$$

$$
\text{Closure Cost} = \text{Convert}\left(q \cdot \text{LotUnitCost},\ ccy_{\text{lot}},\ D_{\text{open}}\right)
$$

$$
\text{Closure Realized PnL} = \text{Closure Proceeds} - \text{Closure Cost}
$$

$\text{ClosePrice}$ è il prezzo unitario di una vendita, nella valuta della vendita, oppure zero, nella valuta del lotto, per una rettifica in uscita, che non ha valore (vedi [Rettifiche in uscita](../../../instruments/transaction-types/adjustment.md#outgoing-adjustments)). $ccy_{\text{close}}$ non deve necessariamente essere uguale a $ccy_{\text{lot}}$: un lotto spostato presso un broker di un'altra valuta e venduto lì converte la vendita da quella valuta. Un lotto SHORT rispecchia la regola: realizza i proventi della sua vendita di apertura, $\text{Convert}(q \cdot \text{LotUnitCost}, ccy_{\text{lot}}, D_{\text{open}})$, meno il costo dell'acquisto che lo chiude, $\text{Convert}(q \cdot \text{ClosePrice}, ccy_{\text{close}}, D_{\text{close}})$.

Quando un lotto è acquistato e venduto in un'unica valuta, con tassi di cambio $r_{\text{open}}$ e $r_{\text{close}}$ alle due date, il suo risultato realizzato si scompone nella plusvalenza di prezzo al tasso di cambio di vendita e nella variazione del tasso di cambio sul costo delle unità vendute:

$$
\text{Closure Realized PnL} = q\,(\text{ClosePrice} - \text{LotUnitCost})\,r_{\text{close}} + q\,\text{LotUnitCost}\,(r_{\text{close}} - r_{\text{open}})
$$

La variazione del tasso di cambio tra acquisto e vendita è quindi realizzata insieme alle unità, come nella Dashboard, dove i proventi di una vendita vengono convertiti alla sua data e le unità escono al loro costo storico (vedi [PMC](../weighted-average-cost.md)). Un tasso di cambio mancante lascia sconosciuto il P&L realizzato della chiusura, e con esso il $\text{RealizedPnL}$ del lotto: non viene mai calcolato dagli importi in valuta nativa.

Il costo di ogni chiusura viene convertito alla data di apertura, come $\text{OriginalCost}$, quindi il P&L di mercato di un lotto LONG è il valore delle sue unità aperte meno il loro costo al tasso di cambio di acquisto:

$$
\text{MarketPnL} = \text{PnL} - \text{RealizedPnL} = \text{OpenValue} - \left(\text{OriginalCost} - \sum \text{Closure Cost}\right)
$$

Un lotto LONG completamente chiuso non ha P&L di mercato: i costi delle sue chiusure si sommano al suo $\text{OriginalCost}$, e tutto il suo P&L è realizzato.

!!! example "Un lotto in dollari, valuta di destinazione EUR"

    Acquisto di 1 unità a 100 USD quando 1 USD = 1,00 EUR; vendita a 110 USD quando 1 USD = 0,90 EUR.

    $$
    \text{Closure Proceeds} = 110 \times 0.90 = 99 \text{ EUR}
    \qquad
    \text{Closure Cost} = 100 \times 1.00 = 100 \text{ EUR}
    $$

    $$
    \text{RealizedPnL} = 99 - 100 = -1 \text{ EUR}
    \qquad
    \text{MarketPnL} = \text{PnL} - \text{RealizedPnL} = (99 - 100) - (-1) = 0
    $$

    La plusvalenza di prezzo, $10 \times 0.90 = +9$ EUR, è superata dal calo del dollaro sul costo, $100 \times (0.90 - 1.00) = -10$ EUR. Convertire il P&L realizzato nativo, 10 USD, al tasso di cambio di vendita riporterebbe invece $+9$ EUR di realizzato e $-10$ EUR di P&L di mercato su un lotto non più detenuto; il totale, $-1$ EUR, è lo stesso in entrambi i modi.

---

## ⚙️ Scalatura qbq

Alcuni strumenti sono quotati **per quantità base**, non per singola unità. LibreFolio chiama questa quantità base `qbq` (`quote_base_quantity`).

- Per la maggior parte delle azioni, `qbq = 1`
- Per molte obbligazioni, `qbq = 100`

La regola di valutazione esatta è:

$$
\text{HoldingValue}(qty, price, qbq) = \left(\frac{qty}{qbq}\right)\cdot price
$$

$$
\text{OpenValue}(t) = \left(\frac{\text{OpenQuantity}(t)}{qbq}\right)\cdot \text{MarketPrice}(t)
$$

!!! warning "La scalatura qbq è importante"

    Supponiamo che un'obbligazione abbia quantità nominale 1.000 e sia quotata a **101,50 per 100 nominali**.

    - `qbq = 100`
    - quantità del lotto = `1,000`
    - valore di mercato = `(1,000 / 100) × 101.50 = 1,015.00`

    Se si confronta direttamente `101.50` con un costo di carico per singola unità come `0.992`, si ottiene un risultato privo di senso, perché i due numeri vivono su scale diverse.

    Il confronto corretto riscala il costo del lotto sull'asse della quotazione di mercato:

    $$
    0.992 \times 100 = 99.20
    $$

    Quindi il confronto di prezzo significativo è **101.50 vs 99.20**, non **101.50 vs 0.992**.

Senza questa scalatura, i rendimenti e le valutazioni delle obbligazioni possono discostarsi di ordini di grandezza.

---

## 🛟 Estimated-at-Cost {: #estimated-at-cost }

Ogni giorno, un lotto viene valorizzato alla quotazione dell'asset fornita dal [resolver unificato](../portfolio-engine/price-resolution.md): una quotazione di mercato, oppure il prezzo medio delle compravendite di acquisto e vendita di un giorno, mantenuto. Una rettifica non è mai un prezzo, con o senza costo di carico; il costo di un trasferimento in entrata lo è solo come [stima](../portfolio-engine/price-resolution.md#transfer-cost-estimate), finché l'asset non ha quotazione e non ha altre operazioni in quel giorno o in un giorno precedente. Un giorno **senza alcun prezzo** — nessuna quotazione di mercato, nessun acquisto o vendita e nessuna tale stima in quel giorno o in un giorno precedente — **non** fa fallire l'analisi: LibreFolio valuta a costo la porzione ancora aperta di un lotto LONG in quel giorno, la regola giorno per giorno che la Dashboard applica a una posizione priva di prezzo:

$$
\text{OpenValue}(t) = \text{OpeningValue}\cdot \frac{\text{OpenQuantity}(t)}{\text{OriginalQuantity}}
$$

$$
\text{MarketPnL}(t) = 0
$$

dove $\text{OpeningValue}$ è il costo originale del lotto convertito alla sua data di apertura. La scelta viene fatta giorno per giorno, senza look-ahead. Un prezzo, una volta osservato, viene mantenuto, quindi questi giorni precedono tutti la prima quotazione, il primo acquisto, la prima vendita o la prima stima del costo di trasferimento dell'asset: vanno dalla prima transazione dell'analisi al giorno precedente quel primo prezzo, oppure alla data finale quando l'asset non ne ha alcuno — e non ce ne sono quando l'asset ha già un prezzo nel giorno della prima transazione.

- **Prima del primo prezzo.** Un lotto aperto prima del primo prezzo dell'asset — per esempio da una rettifica — viene valorizzato al costo dalla sua apertura fino al giorno precedente quel prezzo, anche quando l'asset viene prezzato in seguito: la sua linea di valore resta piatta al costo, senza guadagni o perdite di mercato, poi segue il prezzo.
- **Nessun prezzo.** Un asset senza quotazione, acquisto, vendita o stima del costo di trasferimento fino alla data finale — detenuto solo tramite rettifiche, o tramite trasferimenti senza costo di carico — viene valorizzato al costo in ogni giorno, e il riepilogo del lotto riporta `value_source = ESTIMATED_AT_COST`. Con un prezzo alla data finale o in un giorno precedente, il riepilogo valuta invece il lotto a quel prezzo: `value_source = MARKET_PRICE`, l'etichetta di qualsiasi quotazione, compravendita o stima del costo di trasferimento. Un asset arrivato solo tramite trasferimenti con costo di carico non ha quindi alcun giorno al costo: dal suo primo trasferimento viene valutato a quel costo, convertito al tasso di cambio di ogni giorno, e le serie di prezzo hanno un punto per esso, contrassegnato come stimato.
- **Un prezzo senza tasso di cambio.** Un giorno la cui quotazione non ha un tasso di cambio verso la valuta di destinazione non viene valorizzato al costo: un lotto ancora aperto non ha valore quel giorno, e alla data finale il riepilogo del lotto non ha valore né `value_source`.
- **Una rettifica senza costo di carico.** Una rettifica priva di costo, come una donazione o uno spin-off, apre un lotto a costo zero, e quel lotto vale 0 nei giorni valorizzati al costo finché non arriva un prezzo. Conta come zero in quei giorni, mentre il costo medio della Dashboard tratta quel costo come sconosciuto e lascia la posizione non valorizzata. Una riga del genere è rara: una [rettifica](../../../instruments/transaction-types/adjustment.md) positiva può essere salvata senza costo di carico solo finché è collegata a uno split, e in tal caso non apre alcun lotto, quindi proviene da una versione più vecchia, o da una in cui l'evento di split è stato poi modificato in una rettifica prezzo.

Implicazione pratica, nei giorni valorizzati al costo:

- il lotto mostra comunque un valore residuo
- i proventi già realizzati restano comunque visibili
- i dividendi o gli interessi allocati restano comunque visibili
- **la volatilità non realizzata è temporaneamente sottostimata**
- `market_pnl = 0`, e nessun Open Return: non c'è un prezzo di mercato da confrontare con il riferimento
- nessun ROI o TWRR nella storia delle performance dei lotti, che legge solo i giorni con un prezzo

!!! info "Interpretazione"

    Estimated-at-cost è un fallback operativo prudente. Significa: _"Sappiamo quanto hai pagato, ma al momento non sappiamo quanto pagherebbe il mercato."_

L'avviso di qualità dei dati `CURRENT_PRICE_ASSUMED_AT_COST` — *"Nessun prezzo di mercato disponibile tra {date_from} e {date_to} — valore aperto stimato al costo, P&L di mercato escluso"* — indica esattamente quei giorni: dalla prima transazione al giorno precedente il primo prezzo dell'asset, oppure alla data finale quando l'asset non ne ha alcuno. Viene emesso ogni volta che tali giorni esistono e viene richiesto il riepilogo del lotto o la storia dei valori, dei rendimenti, dei prezzi o delle performance.

---

## 💸 Allocazione del Reddito tra i Lotti {: #income-allocation-across-lots }

I dividendi e gli interessi collegati a un asset sono allocati **pro-rata tra i lotti LONG ammissibili con riferimento al giorno precedente la data del reddito (D-1)**, e solo tra i lotti detenuti **presso il broker pagante**.

Regola di allocazione esatta:

$$
w_i(D) = \frac{\text{EligibleQty}_i(D)}{\sum_j \text{EligibleQty}_j(D)}, \qquad
\text{EligibleQty}_i(D) = \text{OpenQty}_i(D-1)
$$

$$
\text{Income}_i = \text{Convert}(I, ccy, D)\cdot w_i(D)
$$

Dove:

- $I$ = importo del reddito ricevuto alla data $D$
- $\text{Convert}(I, ccy, D)$ = reddito convertito nella valuta di destinazione alla data $D$
- $\text{EligibleQty}_i(D)$ = quantità del lotto $i$ aperta presso il **broker pagante** in $D-1$ (la quantità che ha
  lasciato quel broker in transito conta comunque come originata lì)
- solo i lotti LONG partecipano al denominatore

La regola **D-1** mantiene pulito il giorno di registrazione: un acquisto effettuato *il* giorno del reddito non
guadagna quella distribuzione, e nemmeno un lotto venduto il giorno precedente. I lotti ammissibili più grandi
ricevono una quota maggiore; i lotti detenuti presso altri broker, o non ancora (o non più) ammissibili, non ricevono nulla.

Il reddito conserva il proprio segno: una correzione negativa di un dividendo o di un pagamento di interessi riduce
il reddito del lotto, come avviene nella Dashboard.

!!! warning "Modificato in FIFO v5"

    Le versioni precedenti usavano la data del reddito stessa con **tutti** i broker ($\text{OpenQty}_i(t)$ su ogni lotto).
    Il motore attuale usa l'ammissibilità a D-1 limitata al broker pagante. Se nessun lotto è ammissibile, il reddito
    viene conservato come **reddito orfano a livello di asset** (mai scartato, mai assegnato al lotto sbagliato).

!!! tip "Regola di conservazione"

    Gli importi allocati ai lotti corrispondono esattamente al totale convertito dell'evento di reddito. Il reddito viene distribuito, non creato.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-custody-modal" alt="Modale di dettaglio del lotto — la riga Asset Income mostra il dividendo/interesse pro-rata allocato a questo specifico lotto, insieme al badge Estimated-at-Cost quando il valore corrente del lotto è stimato al costo">
</div>

La riga **Asset Income** del modale di dettaglio del lotto è esattamente $\text{Income}_i$ della formula qui sopra — la quota pro-rata ricevuta da questo specifico lotto. Quando il valore corrente del lotto è stimato al costo — il suo asset non ha alcun prezzo alla data finale —, lo stesso modale mostra anche il badge **Estimated-at-Cost** della sezione precedente.

---

## 💸 Costi e Metriche Nette {: #costs-and-net-metrics }

I `FEE` e `TAX` collegati all'asset sono allocati ai lotti con una **scala deterministica di abbinamento delle operazioni**, poi
sottratti per produrre cifre **nette** accanto a quelle lorde.

### 🧭 Allocazione deterministica dei costi

Un pool di costi (stesso broker, stesso giorno, stesso tipo) viene abbinato alla prima destinazione non vuota in questo ordine:

| Costo | Ordine di abbinamento |
|------|----------------|
| `FEE` | compravendite dello stesso giorno → compravendite del giorno precedente → posizioni aperte → orfano a livello di asset |
| `TAX` | redditi dello stesso giorno → compravendite dello stesso giorno → redditi del giorno precedente → compravendite del giorno precedente → posizioni aperte → orfano a livello di asset |

All'interno di una compravendita abbinata il costo **passa esattamente ai lotti toccati da quella compravendita** — il costo di un acquisto ricade sul lotto che ha aperto, il costo di una vendita ricade sui lotti consumati in FIFO — così l'attribuzione dei costi non contraddice mai l'abbinamento FIFO stesso. Gli importi sono convertiti nella valuta di destinazione e memorizzati come grandezze positive.

!!! tip "Conservazione"

    Per ogni pool, $\sum_i \text{Cost}_i + \text{Orphan} = \text{Convert}(\text{pool}, ccy, D)$. Un costo che non trova
    alcun lotto ammissibile (ad es. una commissione registrata dopo che la posizione è completamente chiusa) diventa
    **costo orfano a livello di asset** invece di essere scartato o forzato su un lotto non correlato.

### ⚖️ Lordo vs netto

Con i costi attribuiti per lotto, LibreFolio riporta sia la performance lorda sia quella netta:

$$
\text{NetTotalPnL}_i = \text{TotalPnL}_i - \text{Fees}_i - \text{Taxes}_i
$$

$$
\text{NetTotalReturn}_i = \frac{\text{NetTotalPnL}_i}{\text{OpeningValue}_i}
$$

dove $\text{TotalPnL}_i$ **include** già il reddito (P&L di mercato + P&L realizzato + reddito dell'asset). La serie
storica del valore per lotto riporta invece un P&L netto *solo capitale*, $\text{pnl}_i - \text{Fees}_i - \text{Taxes}_i$,
che **esclude** il reddito — ogni linea netta rispecchia la propria controparte lorda meno i costi.

Il rendimento annualizzato del lotto usa il rendimento **netto**, non quello lordo:

$$
\mathrm{AnnualizedReturn}_i =
\left(1+\mathrm{NetTotalReturn}_i\right)^{365/d_i}-1
$$

con $d_i$ dalla data di apertura alla data di chiusura per i lotti chiusi, o alla data finale dell'analisi per i lotti aperti. Le finestre inferiori a 30 giorni non restituiscono alcun valore annualizzato; vedi [Rendimento annualizzato netto](../portfolio-engine/net-annualized-return.md).

!!! example "Numeri canonici"

    ACQUISTO 10×100, VENDITA 4×120, prezzo corrente 110, dividendo 50, commissioni 8, imposte 5:
    P&L Totale Lordo $= 60 + 80 + 50 = 190$; P&L Totale Netto $= 190 - 13 = 177$; su un valore di apertura di 1.000 ciò corrisponde a un rendimento totale lordo del **19%** contro uno netto del **17,7%**.

I costi con `asset_id = null` **non** fanno parte di questa vista a livello di lotto — sono a livello di portafoglio e gestiti
dal [Portfolio Engine](../portfolio-engine/roi.md). Vedi
[Commissione & Imposta](../../../instruments/transaction-types/fee.md) per la teoria a livello di strumento.

---

## 📝 Esempio Svolto

??? example "Esempio: due lotti, un dividendo, un prezzo di mercato"

    Assumiamo lo stesso titolo, la stessa valuta, `qbq = 1`.

    | Data | Evento | Quantità aperta Lotto A | Quantità aperta Lotto B | Note |
    |------|-------|----------------|----------------|-------|
    | 2 gen | ACQUISTO 100 @ $10 | 100 | 0 | Il Lotto A si apre con costo originale $1.000 |
    | 10 feb | ACQUISTO 50 @ $14 | 100 | 50 | Il Lotto B si apre con costo originale $700 |
    | 15 mar | DIVIDENDO $30 | 100 | 50 | Entrambi i lotti sono ancora aperti |
    | 1 apr | Prezzo di mercato = $16 | 100 | 50 | Valutazione di entrambi i lotti |

    **Passo 1 — Allocare il dividendo pro-rata**

    $$
    w_A = \frac{100}{100 + 50} = \frac{2}{3}
    \qquad
    w_B = \frac{50}{100 + 50} = \frac{1}{3}
    $$

    $$
    \text{Income}_A = 30 \times \frac{2}{3} = 20
    \qquad
    \text{Income}_B = 30 \times \frac{1}{3} = 10
    $$

    **Passo 2 — Open Return per ciascun lotto**

    $$
    \text{RelativeReturn}_A = \frac{16}{10} - 1 = 60.00\%
    $$

    $$
    \text{RelativeReturn}_B = \frac{16}{14} - 1 \approx 14.29\%
    $$

    **Passo 3 — Valore di mercato e Total Return**

    $$
    \text{OpenValue}_A = 100 \times 16 = 1,600
    \qquad
    \text{OpenValue}_B = 50 \times 16 = 800
    $$

    Poiché non è ancora stata venduta alcuna quota, i proventi e il P&L realizzato sono entrambi zero.

    $$
    \text{TotalPnL}_A = (1,600 - 1,000) + 20 = 620
    $$

    $$
    \text{TotalReturn}_A = \frac{620}{1,000} = 62.00\%
    $$

    $$
    \text{TotalPnL}_B = (800 - 700) + 10 = 110
    $$

    $$
    \text{TotalReturn}_B = \frac{110}{700} \approx 15.71\%
    $$

    **Passo 4 — Rendimento aggregato sui lotti visualizzati**

    $$
    \text{AggregateReturn} = \frac{620 + 110}{1,000 + 700} = \frac{730}{1,700} \approx 42.94\%
    $$

    Anche se entrambi i lotti appartengono allo stesso asset, i loro rendimenti differiscono perché sono stati aperti a prezzi diversi.

---

## 📚 Dai Lotti alle Metriche Aggregate

I rendimenti a livello di lotto possono essere aggregati in una serie di rendimenti complessiva, ma **le percentuali non devono essere sommate direttamente**.

LibreFolio usa questa esatta regola di aggregazione sui lotti visualizzati:

$$
\text{AggregatePnL}(t) = \sum_i \left(\text{PnL}_i(t) + \text{Income}_i(t)\right)
$$

$$
\text{AggregateOpeningValue}(t) = \sum_i \text{OriginalCost}_i
$$

$$
\text{AggregateReturn}(t) = \frac{\text{AggregatePnL}(t)}{\text{AggregateOpeningValue}(t)}
$$

Questa vista a livello di lotto aiuta a spiegare **da dove** proviene il rendimento. Metriche di livello superiore come [ROI](../portfolio-engine/roi.md) e [TWRR](../portfolio-engine/twrr.md) rispondono a domande più ampie sul portafoglio:

- **ROI** si concentra sul guadagno rispetto al capitale investito
- **TWRR** neutralizza la tempistica dei flussi di cassa esterni
- l'analisi dei lotti FIFO spiega il contributo e il percorso **all'interno** di una posizione

La ricerca dei prezzi è deliberatamente esterna al motore FIFO stesso. Il motore produce lotti e chiusure, e richiede un prezzo solo per dare a un lotto aperto da una rettifica il suo riferimento; `LotsAnalysisService` risponde usando il resolver unificato ([Risoluzione del prezzo](../portfolio-engine/price-resolution.md)), poi applica lo stesso resolver e il fallback estimated-at-cost quando deriva le metriche di valutazione.

<div class="screenshot-container">
    <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-table" alt="Unified Lots Table — una riga per lotto con data di apertura, rendimento totale, valore corrente, custodia e stato, esattamente le righe per lotto sommate dalle formule aggregate qui sopra">
</div>

La **Unified Lots Table** elenca esattamente le righe per lotto $i$ che le formule aggregate qui sopra sommano — data di apertura, rendimento totale, valore corrente, custodia e stato, tutte filtrabili sullo stesso insieme di lotti visibile usato dai grafici.

---

## 🔗 Correlati

- 📊 **[Prezzo medio di carico (PMC)](../weighted-average-cost.md)** — vista del costo di carico ponderato
- 🔁 **[Acquisto & Vendita](../../../instruments/transaction-types/buy-sell.md#fifo-matching)** — breve panoramica dell'abbinamento FIFO
- 💸 **[Dividendo & Interesse](../../../instruments/transaction-types/dividend-interest.md)** — origine degli eventi di reddito collegati all'asset
- 💰 **[Tassazione](../../../fundamentals/taxation.md)** — contesto su plusvalenze e abbinamento dei lotti
- ⚙️ **[Lots Analysis Service](../../../../developer/backend/transactions/lots_analysis_service.md)** — approfondimento sull'implementazione per sviluppatori
