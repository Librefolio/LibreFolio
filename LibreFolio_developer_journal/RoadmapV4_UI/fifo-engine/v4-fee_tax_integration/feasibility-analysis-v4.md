FIFO Engine v4 — Analisi di alto livello v4
Motore FIFO unificato con flussi economici, pooling deterministico e metriche lorde/nette

Stato: proposta consolidata da sottoporre a review tecnica finale
 Ambito: evoluzione post-release del sottosistema FIFO
 Obiettivo: integrare proventi, commissioni e imposte in un unico motore FIFO autoconsistente, mantenendo il ledger originale immutato e producendo risultati lordi, netti e auditabili.

1. Obiettivo

Il motore FIFO corrente ricostruisce correttamente:

lotti LONG e SHORT;
aperture e chiusure FIFO;
vendite parziali e complete;
crossing LONG/SHORT;
adjustment;
transfer e frammenti di custodia;
split e reverse split;
P&L lordo;
rendimento lordo;
valore di mercato o stimato al costo.

L’evoluzione deve includere nel dominio FIFO anche:

DIVIDEND
INTEREST
FEE
TAX


per ottenere, per ogni lotto LiL_i:

GrossPnLi(t)GrossPnL_i(t) NetPnLi(t)NetPnL_i(t) GrossReturni(t)GrossReturn_i(t) NetReturni(t)NetReturn_i(t)

L’integrazione non deve:

modificare il modello DB delle transazioni;
alterare le transazioni importate dai broker;
richiedere collegamenti causali non presenti negli estratti conto;
modificare il prezzo di esecuzione;
alterare original_cost;
incorporare i costi nel PMC;
applicare share_percentage nel FIFO;
aggiungere e poi sottrarre lo stesso importo attraverso formule differenti.
2. Assunti
2.1 Natura del risultato

Il risultato FIFO costituisce una ricostruzione:

deterministica;
intuitiva;
conservativa;
auditabile;
coerente con il ledger disponibile.

Non costituisce una ricostruzione fiscale certificata.

Quando una FEE o TAX non può essere collegata con certezza a una singola operazione, viene applicata una policy proporzionale documentata.

2.2 Ledger immutabile

Le transazioni originarie restano la fonte primaria:

Transaction
- date
- type
- asset_id
- broker_id
- quantity
- amount
- currency
- description


Il motore produce strutture derivate runtime.

Non vengono introdotti:

link artificiali persistenti;
modifiche alle descrizioni;
transazioni sintetiche;
migrazioni DB per memorizzare le allocazioni.
2.3 Motore assoluto

Il FIFO considera importi e quantità assoluti del broker:

AmountFIFO=AmountabsoluteAmount^{FIFO}=Amount^{absolute}

Non applica:

share_percentageshare\_percentage

La comproprietà viene applicata successivamente dal Portfolio Engine:

Amountuser=Amountabsolute⋅Shareuser,brokerAmount^{user} = Amount^{absolute}\cdot Share_{user,broker}
3. Un solo motore pubblico

Deve esistere una sola API canonica:

FifoLotEngine.run(...)


e un solo risultato completo:

FifoEngineResult


Il chiamante non deve eseguire separatamente:

motore quantitativo;
allocatore economico;
composizione finale.

Schema:

FifoLotEngine.run()
        │
        ├─ Quantitative Replay
        ├─ Economic Allocation
        ├─ Combined Validation
        └─ FifoEngineResult


L’implementazione può utilizzare componenti privati interni, ma non deve esporre un secondo motore pubblico.

4. Pipeline interna
4.1 Passata quantitativa

La prima passata elabora:

TRANSFER_DEPART
TRANSFER_ARRIVE
SPLIT
BUY
SELL
ADJUSTMENT_IN
ADJUSTMENT_OUT


e produce:

FifoLot
FragmentInterval
LotClosure
classified quantitative events
quantitative issues


L’ordine quantitativo corrente resta invariato:

TRANSFER_DEPART
→ TRANSFER_ARRIVE
→ SPLIT
→ BUY / SELL / ADJUSTMENT

4.2 Passata economica

La seconda passata elabora:

DIVIDEND
INTEREST
FEE
TAX


utilizzando i risultati quantitativi già ricostruiti.

Produce:

income allocations
fee allocations
tax allocations
economic accumulators by lot
asset-orphan amounts
economic issues

4.3 Validazione congiunta

Prima della restituzione vengono verificati:

invarianti quantitativi;
conservazione dei proventi;
conservazione di FEE e TAX;
crossing LONG/SHORT;
scope broker;
riconciliazione nativa;
riconciliazione target;
disponibilità delle metriche lorde e nette.
5. Migrazione atomica

Non è richiesta retrocompatibilità interna con il vecchio percorso.

La migrazione deve aggiornare nello stesso intervento:

firma di FifoLotEngine.run;
tutti i call-site;
FifoEngineResult;
caricamento degli eventi economici;
allocazione dei proventi;
allocazione di FEE e TAX;
LotsAnalysisService;
DTO/API;
client generato;
frontend;
test.

Non devono coesistere due implementazioni dell’allocazione income.

Un risultato restituito da FifoLotEngine.run() è sempre stato processato da entrambi gli stadi, anche quando la lista degli eventi economici è vuota.

Non è necessario un flag economic_stage_completed: il completamento economico è un invariante del solo percorso pubblico.

6. Eventi normalizzati
6.1 Evento quantitativo
QuantitativeEvent=(id,date,type,asset,broker,quantity,amount,data)QuantitativeEvent= (id,date,type,asset,broker,quantity,amount,data)

con:

BUY
SELL
ADJUSTMENT_IN
ADJUSTMENT_OUT
TRANSFER_DEPART
TRANSFER_ARRIVE
SPLIT

6.2 Evento economico
EconomicEvent=(id,date,type,asset,broker,amount,currency,description)EconomicEvent= (id,date,type,asset,broker,amount,currency,description)

con:

DIVIDEND
INTEREST
FEE
TAX


La descrizione viene preservata per audit e visualizzazione, ma non è necessaria alla matematica principale.

7. Stato quantitativo utilizzato dall’economia

La passata economica utilizza:

lot_id
opening_transaction_id
opening_date
opening_broker_id
direction
original_quantity
original_cost
fragment intervals
custody type
source broker
destination broker
closures
closing transaction id
closed quantity
close reason
close date


Non sono necessarie modifiche a:

FifoLot
LotClosure
FragmentInterval


Le grandezze economiche vengono conservate in accumulatori separati, indicizzati per lot_id.

8. Hardening di quote_base_quantity

I seguenti metodi non qbq-aware devono essere rimossi:

value_for_lot
aggregate_value
relative_return_for_lot


Non hanno consumer di produzione e rappresentano un rischio di errore, soprattutto sui bond.

La valutazione rimane responsabilità del percorso qbq-aware:

OpenValue=QuantityQuoteBaseQuantity⋅MarketQuoteOpenValue= \frac{Quantity}{QuoteBaseQuantity}\cdot MarketQuote

Test permanente:

Quantity=1000Quantity=1000 QuoteBaseQuantity=100QuoteBaseQuantity=100 MarketQuote=98,50MarketQuote=98{,}50 OpenValue=985OpenValue=985

FEE e TAX sono importi monetari e non devono essere scalati tramite quote_base_quantity.

9. Semantica temporale dei proventi
9.1 Regola D-1

Un dividendo o interesse registrato nel giorno DD viene attribuito alle quantità possedute alla fine del giorno precedente:

EligibleQuantityi(D)=OpenQuantityi(D−1)EligibleQuantity_i(D) = OpenQuantity_i(D-1)

Ne consegue:

BUY in D
→ non eleggibile

SELL in D
→ eleggibile

BUY in D-1
→ eleggibile

SELL in D-1
→ non eleggibile


Non vengono introdotte eccezioni end-of-day.

9.2 Apertura e chiusura nello stesso giorno

Un lotto aperto e chiuso nel giorno DD non era presente a D−1D-1:

EligibleQuantityi(D)=0EligibleQuantity_i(D)=0

Pertanto non partecipa ai proventi di DD.

9.3 Split nello stesso giorno

L’eleggibilità usa le quantità pre-split presenti a D−1D-1.

Poiché lo split applica uniformemente il rapporto rr:

qi′=rqiq_i'=rq_i

i pesi restano invariati:

rqi∑jrqj=qi∑jqj\frac{rq_i}{\sum_j rq_j} = \frac{q_i}{\sum_j q_j}

La scelta pre-split non modifica la distribuzione proporzionale del provento.

10. Scope broker dei proventi

Per asset aa, broker accreditante bb e data DD:

La,b,D={Li:directioni=LONG, EligibleQuantityi(D)>0, CustodyCompatiblei(b,D)}\mathcal L_{a,b,D} = \{ L_i: direction_i=LONG,\, EligibleQuantity_i(D)>0,\, CustodyCompatible_i(b,D) \}

Il peso è:

wi=EligibleQuantityi(D)∑j∈La,b,DEligibleQuantityj(D)w_i= \frac{EligibleQuantity_i(D)} {\sum_{j\in\mathcal L_{a,b,D}}EligibleQuantity_j(D)}

L’importo allocato è:

IncomeAllocationi=IncomeTotal⋅wiIncomeAllocation_i= IncomeTotal\cdot w_i

Un accredito su un broker non modifica economicamente lotti incompatibili con quel broker.

11. Proventi durante i transfer
11.1 Accredito sul broker From

Sono eleggibili:

frammenti BROKER sul From
+
frammenti IN_TRANSIT con source_broker_id = From

EligibleQtyFrom=QtyBrokerFrom+QtyTransitFromEligibleQty_{From} = Qty_{BrokerFrom} + Qty_{TransitFrom}
11.2 Accredito sul broker To

Sono eleggibili soltanto i frammenti già arrivati prima del giorno DD:

EligibleQtyTo=QtyBrokerTo(D−1)EligibleQty_{To} = Qty_{BrokerTo}(D-1)

Le quantità ancora in transito non sono attribuite al broker To.

11.3 Provento sul To nel giorno di arrivo

Non viene introdotta alcuna eccezione.

Se:

arrival_date = D
income broker = To


ma la quantità era ancora in transito a D−1D-1, il provento diventa asset-orphan.

Viene emessa:

ASSET_INCOME_NO_ELIGIBLE_LOTS


Il messaggio suggerisce di verificare:

data del provento;
data del transfer;
broker dell’accredito;
correttezza delle transazioni.
11.4 Transfer nello stesso giorno

Se partenza e arrivo avvengono nello stesso giorno, per il provento di DD vale comunque lo stato di D−1D-1.

La quantità resta economicamente associata al From.

11.5 Catene di transfer

Per catene:

A → B → C


si utilizza esclusivamente lo stato materializzato nei frammenti a D−1D-1.

Non vengono inferite custodie intermedie non presenti nel replay.

12. Provento senza lotto eleggibile

Se:

La,b,D=∅\mathcal L_{a,b,D}=\varnothing

il provento non viene allocato a un lotto.

Viene accumulato in:

asset_orphan_income


e viene emessa:

ASSET_INCOME_NO_ELIGIBLE_LOTS
severity = WARNING


L’elaborazione prosegue in stato DEGRADED.

13. Bucket non allocati
13.1 Eventi senza asset
asset_id = null


restano fuori dal FIFO:

broker_unallocated_income
broker_unallocated_fees
broker_unallocated_taxes


Sono gestiti dal Portfolio Engine.

13.2 Eventi asset-linked senza lotto
asset_id presente
nessun lotto eleggibile


producono:

asset_orphan_income
asset_orphan_fees
asset_orphan_taxes


Sono inclusi nella riconciliazione assoluta dell’asset, ma non nel risultato di uno specifico lotto.

14. Segno di FEE e TAX

Nel ledger:

FEE.amount < 0
TAX.amount < 0


L’allocatore definisce:

CostTotal=∣TransactionAmount∣CostTotal= |TransactionAmount|

Gli accumulatori:

allocated_fees
allocated_taxes


contengono importi positivi, successivamente sottratti dal risultato lordo.

Una FEE/TAX con segno inatteso produce:

ECONOMIC_EVENT_UNEXPECTED_SIGN
severity = WARNING


L’evento deve essere diagnosticato prima di applicare abs() silenziosamente.

15. Pooling degli eventi economici
15.1 Chiave del pool

Gli eventi vengono raggruppati per:

asset_id
broker_id
date
economic_type


Quindi:

EconomicPool=(a,b,D,type)EconomicPool= (a,b,D,type)

Esempio:

FEE -2
FEE -3
stesso asset, broker e giorno


produce:

FeePool=5FeePool=5

Le transazioni sorgente restano identificabili mediante:

source_transaction_ids[]

15.2 Obiettivo

Il pooling:

riduce i casi combinatori;
evita matching arbitrari tra singole righe;
tratta uniformemente fee o imposte aggregate dal broker;
conserva il totale economico;
evita di pretendere una causalità fiscale non presente nel ledger.
16. Matching temporale

Per ogni pool:

1. candidati nello stesso giorno D;
2. candidati nel giorno precedente D-1;
3. fallback sui lotti aperti;
4. orphan se nessun target esiste.


Non vengono cercati candidati nel giorno successivo D+1D+1.

Le regole adjacent-day diventano quindi:

PREVIOUS_DAY_TRADES
PREVIOUS_DAY_INCOME

17. Pool FEE
17.1 Trade same-day

Se esistono BUY e/o SELL compatibili nello stesso giorno, vengono trattati come un unico pool di trade.

Per operazione kk:

TradeValuek=∣Quantityk⋅ExecutionPricek∣TradeValue_k= |Quantity_k\cdot ExecutionPrice_k|

Il peso dell’operazione è:

βk=TradeValuek∑jTradeValuej\beta_k= \frac{TradeValue_k} {\sum_j TradeValue_j}

La quota di FEE attribuita all’operazione è:

Feek=FeePool⋅βkFee_k= FeePool\cdot\beta_k
17.2 BUY

La quota assegnata a una BUY viene attribuita ai lotti aperti dalla BUY.

Se la BUY produce più lotti:

wiBUY=OpeningValuei∑jOpeningValuejw_i^{BUY} = \frac{OpeningValue_i} {\sum_jOpeningValue_j} Feei=FeeBUY⋅wiBUYFee_i= Fee_{BUY}\cdot w_i^{BUY}
17.3 SELL

La quota assegnata a una SELL viene attribuita ai lotti ridotti o chiusi dalla SELL.

Per le closure:

wiSELL=ClosedQuantityi∑jClosedQuantityjw_i^{SELL} = \frac{ClosedQuantity_i} {\sum_jClosedQuantity_j} Feei=FeeSELL⋅wiSELLFee_i= Fee_{SELL}\cdot w_i^{SELL}
17.4 Round-trip same-day

Quando nello stesso giorno esistono BUY e SELL:

non si sceglie silenziosamente una sola operazione;
entrambe partecipano al pool;
la FEE viene ripartita per controvalore lordo.

Regola di audit:

SAME_DAY_MIXED_TRADES


Trattandosi della policy ufficiale, non viene emesso automaticamente un warning di ambiguità.

17.5 Previous-day trade

Se non esistono trade same-day, vengono cercati BUY e SELL compatibili nel giorno D−1D-1.

Le operazioni vengono riunite in un pool e trattate con le stesse formule del trade same-day.

Regola:

PREVIOUS_DAY_TRADES

18. Pool TAX
18.1 Income same-day

Se esistono DIVIDEND o INTEREST compatibili nello stesso giorno, costituiscono il target primario.

Siano gli income:

I1,…,InI_1,\ldots,I_n

Il peso economico dell’income kk è:

αk=∣Ik∣∑j∣Ij∣\alpha_k= \frac{|I_k|} {\sum_j|I_j|}

Ogni income possiede già pesi interni sui lotti:

wi,kw_{i,k}

Il peso finale del lotto è:

Wi=∑kαkwi,kW_i= \sum_k \alpha_k w_{i,k}

La TAX allocata è:

TaxAllocationi=TaxPool⋅WiTaxAllocation_i= TaxPool\cdot W_i

Poiché:

∑kαk=1\sum_k\alpha_k=1

e:

∑iwi,k=1\sum_iw_{i,k}=1

vale:

∑iWi=1\sum_iW_i=1

e quindi:

∑iTaxAllocationi=TaxPool\sum_iTaxAllocation_i=TaxPool
18.2 Trade same-day senza income

Se non esistono income compatibili nello stesso giorno, la TAX viene attribuita al pool di trade same-day, usando la stessa struttura del Pool FEE.

18.3 Income previous-day

Se non esistono candidati same-day, vengono cercati income compatibili in D−1D-1.

Regola:

PREVIOUS_DAY_INCOME


La ripartizione usa ancora l’importo lordo degli income e i relativi pesi sui lotti.

18.4 Trade previous-day

Se non esistono income in D−1D-1, vengono cercati trade compatibili in D−1D-1.

Regola:

PREVIOUS_DAY_TRADES

19. Fallback sui lotti aperti

Se nessun pool target è disponibile:

Lfallback={Li:asseti=a, brokeri=b, directioni=LONG, OpenQuantityi(D−1)>0}\mathcal L_{fallback} = \{ L_i: asset_i=a,\, broker_i=b,\, direction_i=LONG,\, OpenQuantity_i(D-1)>0 \}

Il peso è:

wi=OpenQuantityi(D−1)∑jOpenQuantityj(D−1)w_i= \frac{OpenQuantity_i(D-1)} {\sum_jOpenQuantity_j(D-1)}

Il fallback copre costi asset-linked generici, quali:

custodia;
gestione;
costi periodici.

Regola:

OPEN_LOTS_FALLBACK

19.1 Nessun target

Se:

Lfallback=∅\mathcal L_{fallback}=\varnothing

il costo viene registrato, secondo il tipo, in:

asset_orphan_fees
asset_orphan_taxes


e viene emessa:

ASSET_COST_NO_ELIGIBLE_LOTS
severity = WARNING

20. Crossing LONG/SHORT

Una singola operazione può:

chiudere una posizione;
aprire la direzione opposta.
20.1 BUY: SHORT → LONG

Siano:

qc=QuantitycloseShortq_c=Quantity_{closeShort} qo=QuantityopenLongq_o=Quantity_{openLong} q=qc+qoq=q_c+q_o

Il costo dell’operazione viene diviso:

CostcloseShort=CostTrade⋅qcqCost_{closeShort} = CostTrade\cdot\frac{q_c}{q} CostopenLong=CostTrade⋅qoqCost_{openLong} = CostTrade\cdot\frac{q_o}{q}

La quota di chiusura viene attribuita ai lotti SHORT chiusi.

La quota di apertura viene attribuita al nuovo lotto LONG.

20.2 SELL: LONG → SHORT

Analogamente:

CostcloseLong=CostTrade⋅qcqCost_{closeLong} = CostTrade\cdot\frac{q_c}{q} CostopenShort=CostTrade⋅qoqCost_{openShort} = CostTrade\cdot\frac{q_o}{q}
20.3 Invariante
Costclose+Costopen=CostTradeCost_{close}+Cost_{open}=CostTrade

Le LotClosure restano immutabili. Le allocazioni vengono registrate negli accumulatori economici per lotto con:

context = CLOSURE
context = OPENING

21. Accumulatori economici

Per ogni lotto LiL_i:

original_cost
sale_proceeds
gross_income
allocated_fees
allocated_taxes
open_value


Le strutture quantitative non vengono mutate dalla passata economica.

Gli accumulatori economici sono memorizzati nel risultato finale, indicizzati per lot_id.

22. Formule feed-forward
22.1 Valore economico lordo
GrossEconomicValuei(t)=OpenValuei(t)+SaleProceedsi(t)+GrossIncomei(t)GrossEconomicValue_i(t) = OpenValue_i(t)+ SaleProceeds_i(t)+ GrossIncome_i(t)
22.2 P&L lordo
GrossPnLi(t)=GrossEconomicValuei(t)−OriginalCostiGrossPnL_i(t) = GrossEconomicValue_i(t)- OriginalCost_i
22.3 Costi allocati
AllocatedCostsi(t)=AllocatedFeesi(t)+AllocatedTaxesi(t)AllocatedCosts_i(t) = AllocatedFees_i(t)+ AllocatedTaxes_i(t)
22.4 P&L netto
NetPnLi(t)=GrossPnLi(t)−AllocatedCostsi(t)NetPnL_i(t) = GrossPnL_i(t)- AllocatedCosts_i(t)

Equivalentemente:

NetPnLi(t)=OpenValuei(t)+SaleProceedsi(t)+GrossIncomei(t)−OriginalCosti−AllocatedFeesi(t)−AllocatedTaxesi(t)NetPnL_i(t)= OpenValue_i(t)+ SaleProceeds_i(t)+ GrossIncome_i(t)- OriginalCost_i- AllocatedFees_i(t)- AllocatedTaxes_i(t)
22.5 Rendimenti

Per:

OriginalCosti>0OriginalCost_i>0

si definiscono:

GrossReturni(t)=GrossPnLi(t)OriginalCostiGrossReturn_i(t) = \frac{GrossPnL_i(t)} {OriginalCost_i} NetReturni(t)=NetPnLi(t)OriginalCostiNetReturn_i(t) = \frac{NetPnL_i(t)} {OriginalCost_i}

Per i lotti SHORT il denominatore resta il nozionale di apertura già utilizzato dal modello lordo.

Per:

OriginalCosti≤0OriginalCost_i\le0

i rendimenti percentuali restano non disponibili.

23. Persistenza dopo chiusura

Alla chiusura completa:

OpenValuei(t)=0OpenValue_i(t)=0

Restano cristallizzati fino a date_to:

SaleProceedsi(t)SaleProceeds_i(t) GrossIncomei(t)GrossIncome_i(t) AllocatedFeesi(t)AllocatedFees_i(t) AllocatedTaxesi(t)AllocatedTaxes_i(t) GrossPnLi(t)GrossPnL_i(t) NetPnLi(t)NetPnL_i(t) GrossReturni(t)GrossReturn_i(t) NetReturni(t)NetReturn_i(t)

Un costo registrato dopo la chiusura può ancora essere attribuito al lotto tramite PREVIOUS_DAY_TRADES; una volta attribuito modifica il risultato netto cristallizzato dalle date successive.

24. Conservazione nativa

Per pool economico PP:

NativePoolP=∑e∈P∣Amounte∣NativePool_P= \sum_{e\in P}|Amount_e|

o, per income positivi:

NativePoolP=∑e∈PAmounteNativePool_P= \sum_{e\in P}Amount_e

L’allocazione nativa è:

NativeAllocationi,P=NativePoolP⋅wiNativeAllocation_{i,P} = NativePool_P\cdot w_i

Deve valere:

∑iNativeAllocationi,P=NativePoolP\sum_iNativeAllocation_{i,P} = NativePool_P

Il residuo viene assegnato deterministicamente all’ultimo lotto secondo un ordinamento stabile.

25. Conversione FX e conservazione target

Il LotsAnalysisService converte il totale del pool una sola volta:

TargetPoolP=FXConvert(NativePoolP,NativeCurrencyP,TargetCurrency,DateP)TargetPool_P= FXConvert ( NativePool_P, NativeCurrency_P, TargetCurrency, Date_P )

Quindi distribuisce:

TargetAllocationi,P=TargetPoolP⋅wiTargetAllocation_{i,P} = TargetPool_P\cdot w_i

Deve valere:

∑iTargetAllocationi,P=TargetPoolP\sum_iTargetAllocation_{i,P} = TargetPool_P

Il residuo target viene assegnato deterministicamente.

Il motore resta indipendente dalla valuta target.

25.1 Pool con valute differenti

Un pool può contenere soltanto eventi con:

stesso asset
stesso broker
stessa data
stesso tipo
stessa valuta


La valuta deve quindi fare parte della chiave del pool:

asset_id
broker_id
date
economic_type
currency


Eventi in valute differenti costituiscono pool distinti.

26. Audit one-shot

L’audit delle allocazioni è sempre incluso nel risultato FIFO.

Non esiste una analysis separata COST_ALLOCATIONS.

Per limitare la dimensione, l’audit usa gruppi compatti.

26.1 Gruppo di allocazione
EconomicAllocationGroup
- asset_id
- broker_id
- date
- type
- rule
- context
- candidate_count
- source_transaction_ids[]
- target_transaction_ids[]
- native_total
- native_currency
- target_total
- target_currency
- allocations[]

26.2 Allocazione per lotto
EconomicLotAllocation
- lot_id
- weight
- native_amount
- target_amount


La descrizione delle transazioni non viene duplicata.

26.3 Ordinamento

I gruppi sono ordinati per:

date
broker_id
asset_id
type
source_transaction_ids


Le allocazioni interne sono ordinate per:

lot_id

27. Data Quality e stato
27.1 Stati globali
COMPLETE
DEGRADED
FAILED

COMPLETE

Tutte le quantità e metriche richieste sono affidabili.

DEGRADED

Una parte del risultato è:

non allocata;
euristica;
non convertibile;
localmente non disponibile.

La parte indipendente resta valida.

FAILED

Il risultato generale è inaffidabile a causa di un errore quantitativo o economico non isolabile.

27.2 Validità locale delle metriche nette

Per lotto:

net_metrics_status:
AVAILABLE
UNAVAILABLE


Un errore economico isolabile non invalida:

quantità;
custodia;
closure;
P&L lordo;
rendimento lordo;
altri lotti non coinvolti.
27.3 Nessun lotto per provento
ASSET_INCOME_NO_ELIGIBLE_LOTS
severity = WARNING
status = DEGRADED


Il provento diventa asset_orphan_income.

27.4 Nessun lotto per costo
ASSET_COST_NO_ELIGIBLE_LOTS
severity = WARNING
status = DEGRADED


Il costo diventa asset_orphan_fees o asset_orphan_taxes.

27.5 Segno inatteso
ECONOMIC_EVENT_UNEXPECTED_SIGN
severity = WARNING
status = DEGRADED


L’evento non viene normalizzato silenziosamente senza diagnostica.

27.6 Cambio FX mancante
FX_RATE_MISSING_FOR_ALLOCATION
severity = WARNING
status = DEGRADED


L’allocazione nativa resta valida; quella target e le metriche nette target coinvolte diventano non disponibili.

27.7 Conservazione fallita
ALLOCATION_CONSERVATION_FAILED
severity = ERROR

Errore isolabile

Se l’evento e i lotti coinvolti sono identificabili:

global status = DEGRADED
net_metrics_status = UNAVAILABLE


solo per i lotti interessati.

Errore non isolabile

Se non è possibile determinare un perimetro affidabile:

global status = FAILED

28. Risultato unico
FifoEngineResult
├─ lots
├─ fragment_intervals
├─ closures
├─ classified_events
├─ economic_allocation_groups
├─ economic_accumulators_by_lot
├─ asset_orphan_income
├─ asset_orphan_fees
├─ asset_orphan_taxes
├─ issues
└─ calculation_status


Tutte le collection fanno parte del risultato canonico.

Quando non esistono eventi economici:

economic_allocation_groups = []
economic_accumulators_by_lot = zero values
asset_orphan_* = zero/empty

29. DTO/API

I campi esistenti mantengono la semantica lorda:

total_pnl
total_return


La documentazione deve indicarli esplicitamente come valori lordi.

Si aggiungono al summary:

allocated_fees
allocated_taxes
net_total_pnl
net_total_return
net_metrics_status


Alle history:

allocated_fees
allocated_taxes
net_pnl
net_total_return
net_metrics_status


La response contiene anche:

economic_allocation_groups[]
asset_orphan_income
asset_orphan_fees
asset_orphan_taxes


Backend e frontend vengono migrati insieme.

30. Riconciliazione assoluta

La chiave di riconciliazione usa il broker accreditante o addebitante dell’evento economico, non la custodia corrente del lotto.

Per:

asset a
broker evento b
periodo T
valuta c


devono valere:

AllocatedIncomea,b,T,c+AssetOrphanIncomea,b,T,c=AbsoluteAssetIncomea,b,T,cAllocatedIncome_{a,b,T,c} + AssetOrphanIncome_{a,b,T,c} = AbsoluteAssetIncome_{a,b,T,c} AllocatedFeesa,b,T,c+AssetOrphanFeesa,b,T,c=AbsoluteAssetFeesa,b,T,cAllocatedFees_{a,b,T,c} + AssetOrphanFees_{a,b,T,c} = AbsoluteAssetFees_{a,b,T,c} AllocatedTaxesa,b,T,c+AssetOrphanTaxesa,b,T,c=AbsoluteAssetTaxesa,b,T,cAllocatedTaxes_{a,b,T,c} + AssetOrphanTaxes_{a,b,T,c} = AbsoluteAssetTaxes_{a,b,T,c}

Ogni gruppo conserva:

broker_id = broker dell’evento sorgente


anche quando il lotto ha una custodia differente.

31. Portfolio Engine e share

Il Portfolio Engine deve introdurre accumulatori assoluti pre-share:

per_income_absolute
per_fees_absolute
per_taxes_absolute


Prima della proiezione utente:

Amountuser=Amountabsolute⋅Shareuser,brokerAmount^{user} = Amount^{absolute}\cdot Share_{user,broker}

La riconciliazione FIFO utilizza gli accumulatori assoluti.

Il FIFO non carica né applica share_percentage.

32. Performance

Durante la singola esecuzione devono essere costruiti indici temporanei:

opening transaction → lot
closing transaction → closures
(date, asset, broker) → BUY trades
(date, asset, broker) → SELL trades
(date, asset, broker) → income events
(lot, date) → eligible quantity
(broker, date) → custody-compatible fragments


Obiettivo:

replay quantitativo:
O(N log N + costo consumo frammenti)

pool economici:
O(E)

matching:
O(E · k)


dove kk è il numero medio di candidati nel pool.

Non vengono introdotte cache persistenti premature.

33. Invarianti
Quantità
InitialQuantity+QuantityIn−QuantityOut=OpenQuantityInitialQuantity+ QuantityIn- QuantityOut= OpenQuantity
Proventi
∑iIncomeAllocationi+AssetOrphanIncome=IncomeTotal\sum_iIncomeAllocation_i+ AssetOrphanIncome = IncomeTotal
FEE
∑iFeeAllocationi+AssetOrphanFee=∣FeeTotal∣\sum_iFeeAllocation_i+ AssetOrphanFee = |FeeTotal|
TAX
∑iTaxAllocationi+AssetOrphanTax=∣TaxTotal∣\sum_iTaxAllocation_i+ AssetOrphanTax = |TaxTotal|
Pool
∑iAllocationi,P=PoolTotalP\sum_i Allocation_{i,P} = PoolTotal_P
Crossing
Costclose+Costopen=CostTradeCost_{close}+Cost_{open}=CostTrade
P&L netto
NetPnLi=GrossPnLi−AllocatedFeesi−AllocatedTaxesiNetPnL_i= GrossPnL_i- AllocatedFees_i- AllocatedTaxes_i
FX nativo
∑iNativeAllocationi,P=NativePoolP\sum_iNativeAllocation_{i,P} = NativePool_P
FX target
∑iTargetAllocationi,P=TargetPoolP\sum_iTargetAllocation_{i,P} = TargetPool_P
Broker scope

Un evento economico sul broker bb non viene attribuito a lotti incompatibili con bb, salvo la gestione esplicita dei frammenti in transito sul From.

34. Sequenza di implementazione
Fase 0 — Hardening qbq
rimozione metodi non qbq-aware;
test bond qbq=100.

Fase 1a — Semantica D-1
income basato su quantità D-1;
test BUY/SELL same-day.

Fase 1b — Broker e transfer
scope broker;
transito From;
To soltanto dopo arrivo;
orphan income;
issue.

Fase 2a — Contratto interno unico
nuova firma run;
nuovo FifoEngineResult;
aggiornamento atomico dei call-site;
nessun percorso legacy.

Fase 2b — Economic allocation stage
EconomicEvent;
pool;
income;
accumulatori;
audit groups;
validazione.

Fase 3 — FEE/TAX
pool same-day;
previous-day;
fallback;
crossing;
orphan;
Data Quality.

Fase 4 — FX e metriche nette
conversione pool;
allocazioni target;
net P&L;
net return;
history;
validità locale.

Fase 5 — DTO e frontend
campi netti;
audit one-shot;
breakdown;
lordo/netto;
banner.

Fase 6 — Portfolio Engine
accumulatori assoluti pre-share;
riconciliazione;
proiezione user-scoped.

Fase 7 — Benchmark e cleanup
benchmark;
rimozione vecchio income allocator;
cleanup DTO/helper;
documentazione assunzioni.

35. Stato attuale e stato a tendere
Motore
OGGI
replay quantitativo;
income allocato dal service;
FEE/TAX solo nel Portfolio Engine.

TARGET
un solo motore pubblico;
due stadi interni obbligatori;
risultato quantitativo ed economico unico.

Proventi
OGGI
quantità attiva in D;
asset-wide;
non broker-aware.

TARGET
quantità D-1;
broker-aware;
transito sul From;
orphan esplicito.

FEE/TAX
OGGI
nessuna attribuzione ai lotti;
nessun P&L netto FIFO.

TARGET
pool giornalieri;
ripartizione proporzionale;
fallback deterministico;
allocated_fees/taxes;
net P&L e net return.

Audit
OGGI
nessuna spiegazione per-lotto dei costi.

TARGET
allocation groups one-shot;
transazioni sorgente;
regola;
target;
peso;
importo nativo e target.

Errori
OGGI
COMPLETE / DEGRADED.

TARGET
COMPLETE / DEGRADED / FAILED;
validità locale delle metriche nette.

36. Risultato finale
TRANSAZIONI
BUY · SELL · DIVIDEND · INTEREST · FEE · TAX
                       │
                       ▼
              FIFO LOT ENGINE
                       │
        ┌──────────────┴──────────────┐
        ▼                             │
QUANTITATIVE REPLAY                   │
lotti · frammenti · closure           │
        │                             │
        ▼                             │
ECONOMIC POOLING & ALLOCATION         │
income · fee · tax · orphan           │
        │                             │
        ▼                             │
COMBINED VALIDATION                   │
quantità · conservazione · perimetri  │
        │                             │
        └──────────────┬──────────────┘
                       ▼
               FIFO ENGINE RESULT
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   LORDO           COSTI           NETTO
 Gross P&L     Fee · Tax       Net P&L
 Gross Return  Audit groups    Net Return


Il risultato a tendere è un unico motore FIFO autoconsistente, capace di trasformare il ledger esistente in una rappresentazione quantitativa ed economica completa, con politiche deterministiche e documentate, senza modificare le transazioni originali e senza simulare una precisione fiscale non supportata dai dati.
