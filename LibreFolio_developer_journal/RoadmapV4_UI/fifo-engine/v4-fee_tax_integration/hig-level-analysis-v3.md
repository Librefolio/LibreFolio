FIFO Engine v4 — Analisi di alto livello v3 “Omni”
Integrazione unificata di proventi, commissioni, imposte e metriche nette

Stato: proposta architetturale consolidata
 Ambito: evoluzione post-release del sottosistema FIFO
 Obiettivo: estendere il motore FIFO quantitativo con una dimensione economica lorda e netta, mantenendo un solo motore pubblico, un solo risultato e transazioni originarie inalterate.

1. Obiettivo

Il sottosistema FIFO attuale ricostruisce correttamente:

apertura e chiusura dei lotti;
matching FIFO;
posizioni LONG e SHORT;
vendite parziali e complete;
crossing LONG/SHORT;
transfer e frammenti di custodia;
split e reverse split;
proventi lordi;
valore di mercato o stimato al costo;
P&L e rendimento lordo.

L’evoluzione proposta deve includere nel dominio FIFO anche:

DIVIDEND
INTEREST
FEE
TAX


così da determinare, per ogni lotto:

P&Ligross(t)P\&L_i^{gross}(t) P&Linet(t)P\&L_i^{net}(t) Returnigross(t)Return_i^{gross}(t) Returninet(t)Return_i^{net}(t)

senza:

modificare il modello DB delle transazioni;
richiedere collegamenti causali non presenti negli estratti conto;
modificare retroattivamente il prezzo di esecuzione;
alterare il PMC;
incorporare share_percentage nel FIFO;
introdurre somme e sottrazioni compensative dello stesso importo.
2. Principi fondamentali
2.1 Un solo motore pubblico

A sviluppo terminato deve esistere un solo motore autoconsistente:

FifoLotEngine


con:

una sola operazione pubblica;
un solo risultato finale;
una sola validazione complessiva.


Interfaccia concettuale:

result = fifo_engine.run(
    quantitative_events=quantitative_events,
    economic_events=economic_events,
)


Non deve essere richiesto al chiamante di eseguire manualmente due sottosistemi separati.

2.2 Due passate interne obbligatorie

L’unicità del motore non implica un singolo ciclo di elaborazione.

Il risultato economico dipende dal risultato quantitativo:

Q=ReplayQuantitative(EQ)Q=ReplayQuantitative(E_Q) A=AllocateEconomic(EE,Q)A=AllocateEconomic(E_E,Q) R=ValidateAndCompose(Q,A)R=ValidateAndCompose(Q,A)

dove:

EQE_Q: eventi quantitativi;
EEE_E: eventi economici;
QQ: lotti, frammenti e closure;
AA: allocazioni economiche;
RR: risultato FIFO completo.

La pipeline interna è:

FifoLotEngine.run()
        │
        ├─ QuantitativeReplayStage
        │  BUY · SELL · ADJUSTMENT · TRANSFER · SPLIT
        │
        ├─ EconomicAllocationStage
        │  DIVIDEND · INTEREST · FEE · TAX
        │
        ├─ CombinedInvariantValidation
        │
        └─ FifoEngineResult


L’eventuale componente dedicato alla seconda passata deve essere un dettaglio privato:

_FifoEconomicAllocationStage


e non un motore pubblico autonomo.

2.3 Motore assoluto

Il FifoLotEngine continua a operare su quantità e importi assoluti.

Non applica:

share_percentage


La comproprietà resta una proiezione del Portfolio Engine.

Pertanto:

FIFOabsolute≠PortfoliouserFIFO^{absolute}\neq Portfolio^{user}

quando:

shareuser,broker≠1share_{user,broker}\neq1
2.4 Modello feed-forward

Gli eventi incrementano accumulatori indipendenti:

original_cost
sale_proceeds
gross_income
allocated_fees
allocated_taxes
open_value


Le metriche finali vengono derivate una sola volta.

Non si deve:

aumentare original_cost con una fee;
ridurre nuovamente il P&L della stessa fee;
rettificare gli incassi e sottrarre di nuovo il costo;
riscrivere il prezzo di apertura.
3. Stato attuale
3.1 Replay quantitativo

Il motore elabora attualmente:

BUY
SELL
ADJUSTMENT_IN
ADJUSTMENT_OUT
TRANSFER_DEPART
TRANSFER_ARRIVE
SPLIT


e produce:

FifoLot
FragmentInterval
LotClosure
FifoDataQualityIssue
FifoEngineResult


L’ordinamento quantitativo stabilizzato è:

TRANSFER_DEPART
TRANSFER_ARRIVE
SPLIT
BUY / SELL / ADJUSTMENT


Questo ordinamento deve essere preservato.

3.2 Eventi economici attuali

Le transazioni:

DIVIDEND
INTEREST
FEE
TAX


hanno quantità nulla e non entrano nel replay quantitativo.

Attualmente:

dividendi e interessi asset-linked vengono allocati dal LotsAnalysisService;
FEE e TAX vengono contabilizzate dal Portfolio Engine;
FEE e TAX non vengono attribuite ai singoli lotti;
non esistono metriche FIFO nette.
3.3 Matematica lorda attuale

Per lotto LiL_i:

Vi(t)=OpenValuei(t)V_i(t)=OpenValue_i(t) Si(t)=SaleProceedsi(t)S_i(t)=SaleProceeds_i(t) Ii(t)=GrossIncomei(t)I_i(t)=GrossIncome_i(t) Ci=OriginalCostiC_i=OriginalCost_i

Il valore economico lordo è:

GrossEconomicValuei(t)=Vi(t)+Si(t)+Ii(t)GrossEconomicValue_i(t) = V_i(t)+S_i(t)+I_i(t)

Il P&L lordo è:

GrossPnLi(t)=GrossEconomicValuei(t)−CiGrossPnL_i(t) = GrossEconomicValue_i(t)-C_i

Il rendimento lordo è:

GrossReturni(t)=GrossPnLi(t)CiGrossReturn_i(t) = \frac{GrossPnL_i(t)}{C_i}

per:

Ci>0C_i>0

Questa matematica è già implementata correttamente e non conta due volte i proventi.

4. Architettura a tendere
┌───────────────────────────────────────────────────────────────┐
│ LOTS ANALYSIS SERVICE                                         │
│                                                               │
│ DB · autorizzazioni · prezzi · FX · qbq · DTO                 │
│ Normalizzazione eventi quantitativi ed economici              │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│ FIFO LOT ENGINE                                               │
│                                                               │
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ 1. Quantitative Replay                                    │ │
│ │ TRANSFER → SPLIT → BUY / SELL / ADJUSTMENT               │ │
│ │ → lotti · frammenti · closure                            │ │
│ └───────────────────────────────┬───────────────────────────┘ │
│                                 │                             │
│ ┌───────────────────────────────▼───────────────────────────┐ │
│ │ 2. Economic Allocation                                   │ │
│ │ DIVIDEND · INTEREST · FEE · TAX                          │ │
│ │ → entitlement · matching · pesi · allocazioni           │ │
│ └───────────────────────────────┬───────────────────────────┘ │
│                                 │                             │
│ ┌───────────────────────────────▼───────────────────────────┐ │
│ │ 3. Combined Validation                                   │ │
│ │ quantità · conservazione · lordo/netto · issue          │ │
│ └───────────────────────────────┬───────────────────────────┘ │
│                                 │                             │
│                         FifoEngineResult                      │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│ LOTS ANALYSIS SERVICE                                         │
│                                                               │
│ conversione FX · valutazione qbq-aware · history · DTO       │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│ FRONTEND                                                      │
│                                                               │
│ metriche lorde/nette · breakdown · audit · Data Quality      │
└───────────────────────────────────────────────────────────────┘

5. Eventi normalizzati
5.1 Eventi quantitativi
QuantitativeEvent=(id,date,type,asset,broker,quantity,amount,relatedData)QuantitativeEvent= \left( id,date,type,asset,broker, quantity,amount,relatedData \right)

con:

BUY
SELL
ADJUSTMENT_IN
ADJUSTMENT_OUT
TRANSFER_DEPART
TRANSFER_ARRIVE
SPLIT

5.2 Eventi economici

Si introduce un tipo distinto:

EconomicEvent=(id,date,type,asset,broker,amount,currency,description)EconomicEvent= \left( id,date,type,asset,broker, amount,currency,description \right)

con:

DIVIDEND
INTEREST
FEE
TAX


Il motore non interpreta fiscalmente la descrizione.

La descrizione resta disponibile per:

audit;
tooltip;
diagnostica;
eventuali euristiche future.
6. Hardening di quote_base_quantity
6.1 Problema

Il percorso produttivo applica correttamente:

OpenValue=QuantityQuoteBaseQuantity⋅MarketQuoteOpenValue= \frac{Quantity}{QuoteBaseQuantity} \cdot MarketQuote

Alcuni metodi del motore risultano invece non qbq-aware:

value_for_lot
aggregate_value
relative_return_for_lot


Non hanno consumer produttivi, ma rappresentano un rischio di riuso.

6.2 Decisione

Rimuovere tali metodi dal motore.

Gli invarianti utili dei relativi test devono essere trasferiti a:

LotsAnalysisService
compute_holding_value
helper qbq-aware di test

6.3 Test permanente

Per:

Quantity=1000Quantity=1000 QBQ=100QBQ=100 MarketQuote=98,50MarketQuote=98{,}50

deve risultare:

OpenValue=1000100⋅98,50=985OpenValue= \frac{1000}{100}\cdot98{,}50 =985

Il test deve coprire:

valore aperto;
P&L lordo;
P&L netto;
rendimento relativo;
FEE/TAX, che non devono essere scalate da qbq.
7. Semantica temporale dei proventi
7.1 Titolarità D-1

Un dividendo o interesse registrato nel giorno DD viene attribuito alle quantità possedute all’inizio del giorno:

EligibleQuantityi(D)=OpenQuantityi(D−1)EligibleQuantity_i(D) = OpenQuantity_i(D-1)

Ne deriva:

BUY in D
→ non eleggibile

SELL in D
→ eleggibile

BUY in D-1
→ eleggibile

SELL in D-1
→ non eleggibile


La data dell’Asset Event non viene usata per l’allocazione.

7.2 Split nello stesso giorno

L’eleggibilità usa la quantità pre-split risultante da D−1D-1.

Poiché l’importo del provento è un totale monetario da distribuire, l’utilizzo di quantità pre-split preserva comunque:

∑iIncomeAllocationi=IncomeTotal\sum_i IncomeAllocation_i=IncomeTotal

Il caso deve essere documentato e coperto da test.

8. Scope broker dei proventi

Per un evento economico relativo ad asset aa, broker bb e giorno DD, i lotti eleggibili sono:

La,b,D={Li:directioni=LONG, EligibleQuantityi(D)>0, CustodyCompatiblei(b,D)}\mathcal L_{a,b,D} = \left\{ L_i: direction_i=LONG,\, EligibleQuantity_i(D)>0,\, CustodyCompatible_i(b,D) \right\}

Il peso è:

wi(D)=EligibleQuantityi(D)∑j∈La,b,DEligibleQuantityj(D)w_i(D)= \frac{EligibleQuantity_i(D)} {\sum_{j\in\mathcal L_{a,b,D}} EligibleQuantity_j(D)}

L’importo allocato è:

IncomeAllocationi,D=IncomeD⋅wi(D)IncomeAllocation_{i,D} = Income_D\cdot w_i(D)

Un provento accreditato su un broker non deve essere attribuito ai lotti custoditi su broker incompatibili.

9. Proventi durante i transfer
9.1 Accredito sul broker From

Sono eleggibili:

frammenti BROKER sul From
+
frammenti IN_TRANSIT con source_broker_id = From

EligibleQtyFrom=QtyBrokerFrom+QtyTransitFromEligibleQty_{From} = Qty_{BrokerFrom} + Qty_{TransitFrom}
9.2 Accredito sul broker To

Sono eleggibili soltanto i frammenti già arrivati e custoditi sul To:

EligibleQtyTo=QtyBrokerToEligibleQty_{To} = Qty_{BrokerTo}

Il frammento in transito non viene attribuito al To.

9.3 Giorno di arrivo

Nel giorno di arrivo, la regola D−1D-1 resta vincolante.

Pertanto:

provento sul From
→ quantità in transito ancora eleggibile sul From;

provento sul To
→ nessuna quantità eleggibile se a D-1 non era ancora arrivata.


In quest’ultimo caso viene generata una issue, senza introdurre eccezioni end-of-day.

9.4 Transfer nello stesso giorno

Se partenza e arrivo coincidono:

non esiste un intervallo effettivo di transito;
per il provento del giorno vale comunque lo stato D−1D-1;
pertanto la quantità resta economicamente associata al From.
9.5 Catene di transfer

Per catene:

A → B → C


l’allocazione deve usare esclusivamente lo stato reale dei frammenti a D−1D-1:

BROKER su B
→ eleggibile su B

IN_TRANSIT con source=B
→ eleggibile su B

mai arrivato su B
→ non eleggibile su B


Non vengono inferite custodie intermedie non materializzate nel replay.

10. Provento senza lotto eleggibile

Se:

La,b,D=∅\mathcal L_{a,b,D}=\varnothing

l’importo non viene allocato ai lotti.

Si produce:

ASSET_INCOME_NO_ELIGIBLE_LOTS
severity = WARNING
calculation_status = DEGRADED


L’issue contiene:

transaction_id
asset_id
broker_id
date
native amount
currency


Il messaggio deve indicare una possibile incoerenza di:

data;
broker;
asset;
BUY;
SELL;
transfer.
11. Buckets non allocati

Devono essere distinti due concetti.

11.1 Effetto senza asset
asset_id = null


Bucket:

broker_unallocated_income
broker_unallocated_fees
broker_unallocated_taxes


Non entra nel FIFO.

11.2 Effetto asset-linked senza lotto
asset_id presente
nessun lotto eleggibile


Bucket:

asset_orphan_income
asset_orphan_fees
asset_orphan_taxes


Resta associato all’asset e al broker, ma non viene attribuito a un lotto.

La riconciliazione assoluta diventa:

AllocatedToLots+AssetOrphan=AbsoluteAssetTotalAllocatedToLots+ AssetOrphan= AbsoluteAssetTotal
12. FEE e TAX
12.1 Segno

Nel modello transazionale FEE e TAX hanno importo negativo.

L’allocatore usa:

CostTotal=∣TransactionAmount∣CostTotal=|TransactionAmount|

Gli accumulatori:

allocated_fees
allocated_taxes


contengono valori positivi da sottrarre alle metriche lorde.

12.2 Principio

Il motore non deve determinare la natura fiscale precisa della transazione.

Distingue solamente:

FEE
TAX


e individua il target economicamente più plausibile mediante regole deterministiche.

13. Gerarchia di matching dei costi

Le priorità sono diverse per FEE e TAX.

13.1 Priorità FEE
1. SAME_DAY_SELL
2. SAME_DAY_BUY
3. SAME_DAY_INCOME
4. ADJACENT_DAY_SELL
5. ADJACENT_DAY_BUY
6. ADJACENT_DAY_INCOME
7. OPEN_LOTS_FALLBACK
8. NO_ELIGIBLE_LOTS

13.2 Priorità TAX
1. SAME_DAY_INCOME
2. SAME_DAY_SELL
3. SAME_DAY_BUY
4. ADJACENT_DAY_INCOME
5. ADJACENT_DAY_SELL
6. ADJACENT_DAY_BUY
7. OPEN_LOTS_FALLBACK
8. NO_ELIGIBLE_LOTS


La priorità differenziata riduce il rischio che una ritenuta su un provento venga attribuita a una SELL avvenuta nello stesso giorno.

13.3 Finestra adiacente

La finestra iniziale è:

D−1,  D+1D-1,\;D+1

Vincoli:

stesso asset;
stesso broker;
tier compatibile;
distanza minima.


La ricerca same-day ha sempre priorità sulla ricerca adjacent-day.

13.4 Più candidati nello stesso tier

Se esistono più candidati compatibili:

il costo viene distribuito sull’intero tier;
non viene scelta silenziosamente una sola transazione;
viene generata:
FEE_TAX_ALLOCATION_AMBIGUOUS
severity = WARNING
calculation_status = DEGRADED


La issue riporta:

candidate_count
candidate transaction ids
allocation rule

14. Allocazione su SELL

Siano le closure compatibili:

C={c1,…,cn}C=\{c_1,\ldots,c_n\}

Il peso del lotto ii è:

wi=ClosedQuantityi∑jClosedQuantityjw_i= \frac{ClosedQuantity_i} {\sum_j ClosedQuantity_j}

Il costo allocato è:

AllocatedCosti=CostTotal⋅wiAllocatedCost_i= CostTotal\cdot w_i

La regola copre:

SELL parziale;
SELL completa;
SELL multi-lotto;
più SELL nello stesso tier.

Il costo:

non modifica l’incasso lordo;
non modifica il P&L lordo;
riduce il P&L netto.
15. Allocazione su BUY

Per una o più BUY candidate:

wi=OpeningValuei∑jOpeningValuejw_i= \frac{OpeningValue_i} {\sum_j OpeningValue_j} AllocatedCosti=CostTotal⋅wiAllocatedCost_i= CostTotal\cdot w_i

Con una sola BUY:

AllocatedCosti=CostTotalAllocatedCost_i=CostTotal

Il costo:

non modifica opening_unit_price;
non modifica original_cost;
riduce il risultato netto.
16. Crossing LONG/SHORT
16.1 BUY: chiusura SHORT e apertura LONG

Siano:

qc=QuantitycloseShortq_c=Quantity_{closeShort} qo=QuantityopenLongq_o=Quantity_{openLong} q=qc+qoq=q_c+q_o

Il costo viene diviso:

CostcloseShort=CostTotal⋅qcqCost_{closeShort} = CostTotal\cdot\frac{q_c}{q} CostopenLong=CostTotal⋅qoqCost_{openLong} = CostTotal\cdot\frac{q_o}{q}

La quota closeShort viene ripartita sulle closure SHORT.

La quota openLong viene assegnata al nuovo lotto LONG.

16.2 SELL: chiusura LONG e apertura SHORT

Analogamente:

CostcloseLong=CostTotal⋅qcqCost_{closeLong} = CostTotal\cdot\frac{q_c}{q} CostopenShort=CostTotal⋅qoqCost_{openShort} = CostTotal\cdot\frac{q_o}{q}
16.3 Invariante
Costclose+Costopen=CostTotalCost_{close}+Cost_{open}=CostTotal

Per i lotti SHORT il denominatore del rendimento netto resta il nozionale di apertura già utilizzato dal modello lordo.

17. Allocazione su DIVIDEND e INTEREST

Se FEE/TAX viene associata a un provento, riutilizza gli stessi pesi:

CostAllocationi=CostTotal⋅IncomeWeightiCostAllocation_i= CostTotal\cdot IncomeWeight_i

Non viene effettuata una nuova ricostruzione dei lotti eleggibili.

Questo garantisce coerenza tra:

gross income allocation
income fee/tax allocation
net income


Per lotto:

NetIncomei=GrossIncomei−IncomeFeei−IncomeTaxiNetIncome_i= GrossIncome_i- IncomeFee_i- IncomeTax_i

Il NetIncome è una vista derivata; gli accumulatori FEE/TAX restano separati.

18. Fallback sui lotti aperti

Se non esistono candidati BUY, SELL o income:

Lfallback={Li:asseti=a, brokeri=b, directioni=LONG, OpenQuantityi(D−1)>0}\mathcal L_{fallback} = \left\{ L_i: asset_i=a,\, broker_i=b,\, direction_i=LONG,\, OpenQuantity_i(D-1)>0 \right\}

Il peso è:

wi=OpenQuantityi(D−1)∑jOpenQuantityj(D−1)w_i= \frac{OpenQuantity_i(D-1)} {\sum_jOpenQuantity_j(D-1)}

Questo rappresenta costi generici asset-linked, quali:

custodia;
gestione;
costo periodico.
18.1 Nessun target

Se:

Lfallback=∅\mathcal L_{fallback}=\varnothing

il costo entra in:

asset_orphan_fees


oppure:

asset_orphan_taxes


e viene generata:

ASSET_COST_NO_ELIGIBLE_LOTS
severity = WARNING
calculation_status = DEGRADED

19. Modello feed-forward
19.1 Accumulatori per lotto

Per il lotto ii:

original_cost
sale_proceeds
gross_income
allocated_fees
allocated_taxes
open_value


Gli accumulatori economici appartengono al risultato dell’allocation stage, non mutano le strutture quantitative originarie.

19.2 Valore economico lordo
GrossEconomicValuei(t)=OpenValuei(t)+SaleProceedsi(t)+GrossIncomei(t)GrossEconomicValue_i(t) = OpenValue_i(t)+ SaleProceeds_i(t)+ GrossIncome_i(t)
19.3 P&L lordo
GrossPnLi(t)=GrossEconomicValuei(t)−OriginalCostiGrossPnL_i(t) = GrossEconomicValue_i(t)- OriginalCost_i
19.4 Costi
AllocatedCostsi(t)=AllocatedFeesi(t)+AllocatedTaxesi(t)AllocatedCosts_i(t) = AllocatedFees_i(t)+ AllocatedTaxes_i(t)
19.5 P&L netto
NetPnLi(t)=GrossPnLi(t)−AllocatedCostsi(t)NetPnL_i(t) = GrossPnL_i(t)- AllocatedCosts_i(t)

Equivalentemente:

NetPnLi(t)=OpenValuei(t)+SaleProceedsi(t)+GrossIncomei(t)−OriginalCosti−AllocatedFeesi(t)−AllocatedTaxesi(t)NetPnL_i(t)= OpenValue_i(t)+ SaleProceeds_i(t)+ GrossIncome_i(t)- OriginalCost_i- AllocatedFees_i(t)- AllocatedTaxes_i(t)
19.6 Rendimenti

Per:

OriginalCosti>0OriginalCost_i>0

si definiscono:

GrossReturni(t)=GrossPnLi(t)OriginalCostiGrossReturn_i(t) = \frac{GrossPnL_i(t)} {OriginalCost_i} NetReturni(t)=NetPnLi(t)OriginalCostiNetReturn_i(t) = \frac{NetPnL_i(t)} {OriginalCost_i}

Quando:

OriginalCosti≤0OriginalCost_i\le0

il rendimento percentuale non viene inventato e resta non disponibile.

20. Persistenza temporale

Gli accumulatori economici non vengono azzerati alla chiusura del lotto.

Dopo la chiusura completa:

OpenValuei(t)=0OpenValue_i(t)=0

ma restano cristallizzati:

SaleProceedsi(t)SaleProceeds_i(t) GrossIncomei(t)GrossIncome_i(t) AllocatedFeesi(t)AllocatedFees_i(t) AllocatedTaxesi(t)AllocatedTaxes_i(t) GrossPnLi(t)GrossPnL_i(t) NetPnLi(t)NetPnL_i(t) GrossReturni(t)GrossReturn_i(t) NetReturni(t)NetReturn_i(t)

fino a date_to.

21. Allocazione nativa e FX
21.1 Allocazione nativa

Per evento EE:

NativeAllocationi,E=NativeAmountE⋅wiNativeAllocation_{i,E} = NativeAmount_E\cdot w_i

con:

∑iNativeAllocationi,E=NativeAmountE\sum_i NativeAllocation_{i,E} = NativeAmount_E

Il residuo viene assegnato deterministicamente all’ultimo lotto secondo un ordinamento stabile.

21.2 Conversione target

Il service converte il totale una sola volta:

TargetTotalE=FXConvert(NativeAmountE,NativeCurrencyE,TargetCurrency,DateE)TargetTotal_E= FXConvert \left( NativeAmount_E, NativeCurrency_E, TargetCurrency, Date_E \right)

Poi ripartisce:

TargetAllocationi,E=TargetTotalE⋅wiTargetAllocation_{i,E} = TargetTotal_E\cdot w_i

con:

∑iTargetAllocationi,E=TargetTotalE\sum_i TargetAllocation_{i,E} = TargetTotal_E

Anche il residuo target viene assegnato deterministicamente.

Questa policy garantisce conservazione sia in valuta nativa sia in target currency.

22. Audit trail

Ogni allocazione deve produrre:

EconomicAllocation=(sourceTx, targetTx, lot, broker, date, type, context, rule, weight, candidateCount, nativeAmount, nativeCurrency, targetAmount, targetCurrency)EconomicAllocation= \left( sourceTx,\, targetTx,\, lot,\, broker,\, date,\, type,\, context,\, rule,\, weight,\, candidateCount,\, nativeAmount,\, nativeCurrency,\, targetAmount,\, targetCurrency \right)

Campi:

source_transaction_id
target_transaction_id
lot_id
broker_id
date
type
context
rule
weight
candidate_count
native_amount
native_currency
target_amount
target_currency

Type
DIVIDEND
INTEREST
FEE
TAX

Context
OPENING
CLOSURE
INCOME
HOLDING

Rule
SAME_DAY_SELL
SAME_DAY_BUY
SAME_DAY_INCOME
ADJACENT_DAY_SELL
ADJACENT_DAY_BUY
ADJACENT_DAY_INCOME
OPEN_LOTS_FALLBACK


Non sono necessari:

confidence
description duplicata
closure_id


poiché sono ricavabili da regola, candidati e transazioni.

23. Data Quality
23.1 Nessun lotto per provento
ASSET_INCOME_NO_ELIGIBLE_LOTS
severity = WARNING
status = DEGRADED


Il provento resta asset-linked ma non attribuito.

23.2 Nessun lotto per costo
ASSET_COST_NO_ELIGIBLE_LOTS
severity = WARNING
status = DEGRADED


Il costo resta asset-linked ma non attribuito.

23.3 Allocazione ambigua
FEE_TAX_ALLOCATION_AMBIGUOUS
severity = WARNING
status = DEGRADED


L’allocazione viene eseguita sul tier compatibile, ma viene segnalata come euristica.

23.4 Cambio FX mancante
FX_RATE_MISSING_FOR_ALLOCATION
severity = WARNING
status = DEGRADED


L’allocazione nativa resta disponibile; le metriche target coinvolte risultano incomplete.

23.5 Conservazione fallita
ALLOCATION_CONSERVATION_FAILED
severity = ERROR


Se il delta supera la tolleranza:

le metriche nette coinvolte non vengono restituite come precise;
net_total_pnl e net_total_return risultano non disponibili nel perimetro affetto;
il resto del risultato può continuare in modalità DEGRADED se isolabile.
24. Risultato unico del motore

L’output pubblico resta unico:

FifoEngineResult
├─ lots
├─ fragments
├─ closures
├─ economic_allocations
├─ economic_accumulators_by_lot
├─ asset_orphan_income
├─ asset_orphan_fees
├─ asset_orphan_taxes
├─ issues
└─ calculation_status


Per lotto:

EconomicAccumulator
├─ gross_income
├─ allocated_fees
├─ allocated_taxes
├─ gross_pnl
├─ net_pnl
├─ gross_return
└─ net_return


Il chiamante non può ottenere accidentalmente un risultato “definitivo” privo della passata economica quando questa è richiesta.

25. Contratto DTO

I campi esistenti mantengono la semantica lorda:

total_pnl
total_return


La documentazione deve esplicitare:

total_pnl    = gross total P&L
total_return = gross total return


Si aggiungono:

allocated_fees
allocated_taxes
net_total_pnl
net_total_return


Alle history:

allocated_fees
allocated_taxes
net_pnl
net_total_return


L’audit completo viene richiesto mediante analysis opzionale:

COST_ALLOCATIONS


in modo da non aumentare inutilmente la response standard.

26. Riconciliazione
26.1 Riconciliazione assoluta FIFO

Per asset aa, broker bb, periodo TT:

∑iGrossIncomei,a,b,T+AssetOrphanIncomea,b,T=AbsoluteAssetIncomea,b,T\sum_i GrossIncome_{i,a,b,T} + AssetOrphanIncome_{a,b,T} = AbsoluteAssetIncome_{a,b,T} ∑iAllocatedFeesi,a,b,T+AssetOrphanFeesa,b,T=AbsoluteAssetFeesa,b,T\sum_i AllocatedFees_{i,a,b,T} + AssetOrphanFees_{a,b,T} = AbsoluteAssetFees_{a,b,T} ∑iAllocatedTaxesi,a,b,T+AssetOrphanTaxesa,b,T=AbsoluteAssetTaxesa,b,T\sum_i AllocatedTaxes_{i,a,b,T} + AssetOrphanTaxes_{a,b,T} = AbsoluteAssetTaxes_{a,b,T}

Questa è la riconciliazione vincolante del FIFO.

26.2 Proiezione Portfolio Engine

Il Portfolio Engine applica successivamente:

Amounta,b,Tuser=Amounta,b,Tabsolute⋅Shareuser,bAmount^{user}_{a,b,T} = Amount^{absolute}_{a,b,T} \cdot Share_{user,b}

Il FIFO non deve caricare o applicare share_percentage.

La riconciliazione col Portfolio Engine deve quindi usare accumulatori pre-share oppure una proiezione esplicita del risultato assoluto.

27. Invarianti complete
Quantità
InitialQuantity+QuantityIn−QuantityOut=OpenQuantityInitialQuantity+ QuantityIn- QuantityOut= OpenQuantity
Income
∑iIncomeAllocationi,E+OrphanIncomeE=IncomeAmountE\sum_i IncomeAllocation_{i,E} + OrphanIncome_E = IncomeAmount_E
FEE
∑iFeeAllocationi,E+OrphanFeeE=∣FeeAmountE∣\sum_i FeeAllocation_{i,E} + OrphanFee_E = |FeeAmount_E|
TAX
∑iTaxAllocationi,E+OrphanTaxE=∣TaxAmountE∣\sum_i TaxAllocation_{i,E} + OrphanTax_E = |TaxAmount_E|
Crossing
Costclose+Costopen=CostTotalCost_{close}+Cost_{open}=CostTotal
P&L netto
NetPnLi=GrossPnLi−AllocatedFeesi−AllocatedTaxesiNetPnL_i= GrossPnL_i- AllocatedFees_i- AllocatedTaxes_i
FX nativo
∑iNativeAllocationi,E=NativeTotalE\sum_i NativeAllocation_{i,E} = NativeTotal_E
FX target
∑iTargetAllocationi,E=TargetTotalE\sum_i TargetAllocation_{i,E} = TargetTotal_E
Broker scope

Un evento sul broker bb non modifica lotti incompatibili col broker bb.

28. Sequenza di implementazione
Fase 0 — Hardening qbq
rimuovere i metodi non qbq-aware;
spostare gli invarianti utili nei test corretti;
aggiungere test qbq=100.

Fase 1 — Correzione proventi
D-1;
scope broker;
transito From/To;
giorno di arrivo;
catene;
bucket orphan;
Data Quality.

Fase 2 — Passata economica interna
EconomicEvent;
EconomicAllocationStage;
matching;
pesi;
allocazioni native;
audit;
invarianti.

Fase 3 — FEE/TAX
priorità differenziate;
same-day;
adjacent-day;
fallback;
crossing LONG/SHORT;
orphan costs;
Data Quality.

Fase 4 — FX e metriche nette
conversione totale;
allocazioni target;
accumulatori;
net P&L;
net return;
history persistenti.

Fase 5 — DTO/API
campi netti;
history nette;
COST_ALLOCATIONS opzionale;
rigenerazione client.

Fase 6 — Frontend
lordo/netto;
breakdown FEE/TAX;
audit allocazioni;
Data Quality;
tooltip e modale.

Fase 7 — Riconciliazione
accumulatori assoluti pre-share;
riconciliazione FIFO;
proiezione Portfolio;
benchmark.

29. Stato attuale e stato a tendere
Proventi
OGGI
qty attiva in D
asset-wide
non broker-aware
nessuna policy completa per il transito
nessun bucket orphan esplicito

TARGET
qty D-1
broker-aware
transito attribuito al From
To soltanto dopo arrivo
asset_orphan_income
issue esplicite

FEE/TAX
OGGI
solo Portfolio Engine
nessuna allocazione ai lotti
nessun risultato netto FIFO

TARGET
passata economica interna obbligatoria
matching deterministico
allocazioni per lotto
metriche lorde e nette
audit trail
bucket orphan

Motore
OGGI
un motore quantitativo
income esterno nel service

TARGET
un solo motore pubblico
due stadi interni obbligatori
un solo risultato autoconsistente
validazione congiunta

qbq
OGGI
percorso produttivo corretto
metodi pericolosi ma inutilizzati

TARGET
rimozione dei metodi non qbq-aware
test permanente bond qbq=100

30. Risultato finale
TRANSAZIONI
BUY · SELL · INCOME · FEE · TAX
          │
          ▼
QUANTITATIVE REPLAY
lotti · frammenti · closure
          │
          ▼
ECONOMIC ALLOCATION
entitlement · matching · pesi · allocazioni
          │
          ▼
COMBINED VALIDATION
quantità · conservazione · FX · broker scope
          │
          ▼
ACCUMULATORI
open value · proceeds · income · fees · taxes
          │
          ▼
METRICHE
Gross P&L · Net P&L · Gross Return · Net Return
          │
          ▼
AUDIT
quale evento
su quale lotto
con quale peso
secondo quale regola
in quale valuta


Il risultato a tendere è un FifoLotEngine unico e autoconsistente, con una pipeline interna quantitativa ed economica, capace di produrre una rappresentazione intuitiva, deterministica e auditabile del risultato lordo e netto dei lotti senza modificare il ledger originario.
