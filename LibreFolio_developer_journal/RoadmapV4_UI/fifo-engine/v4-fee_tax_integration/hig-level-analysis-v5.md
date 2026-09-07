FIFO Engine v5 — Piano di alto livello per l’integrazione di proventi, FEE e TAX
1. Obiettivo

Estendere il sottosistema FIFO affinché ogni lotto rappresenti in modo coerente:

quantità e custodia;
incassi da vendite;
dividendi e interessi;
commissioni;
imposte;
P&L lordo e netto;
rendimento lordo e netto;
regola usata per ogni allocazione economica.

Il risultato deve essere:

deterministico;
conservativo;
matematicamente feed-forward;
broker-aware;
compatibile con transfer, split e crossing LONG/SHORT;
auditabile;
calcolato nella target_currency scelta dall’utente;
prodotto da un solo motore FIFO pubblico e autoconsistente.

Il sistema non intende ricostruire con precisione fiscale certificata la causalità di ogni costo. Quando il ledger non fornisce un legame esplicito, applica policy proporzionali definite e documentate.

2. Assunti consolidati
2.1 Ledger immutato

Le transazioni originali non vengono modificate né arricchite con legami sintetici persistenti.

Transaction
├─ date
├─ type
├─ asset_id
├─ broker_id
├─ quantity
├─ amount
├─ currency
└─ description


Le allocazioni FIFO sono strutture runtime derivate.

Non sono necessarie migrazioni DB per memorizzare:

associazioni tra FEE/TAX e trade;
pesi di allocazione;
risultati netti;
audit economico.
2.2 Motore assoluto

Il FIFO lavora sui valori assoluti del broker:

AmountFIFO=AmountabsoluteAmount^{FIFO}=Amount^{absolute}

Non applica:

share_percentageshare\_percentage

La proiezione sulla quota dell’utente resta responsabilità del Portfolio Engine:

Amountuser=Amountabsolute⋅Shareuser,brokerAmount^{user} = Amount^{absolute}\cdot Share_{user,broker}
2.3 Calcolo nella target currency

La target_currency è un parametro noto dell’analisi.

Il LotsAnalysisService prepara ogni evento con:

native_amount
native_currency
target_amount
target_currency


Il motore:

conserva i valori nativi per audit;
usa i valori target per confronti, pooling e metriche;
non accede direttamente al sistema FX;
non effettua query o conversioni asincrone.

Quindi il motore è:

target-value aware
FX-mechanism agnostic

2.4 Modello feed-forward

Gli eventi alimentano direttamente accumulatori indipendenti:

original_cost
sale_proceeds
gross_income
allocated_fees
allocated_taxes
open_value


Non si modifica original_cost per incorporare costi e non si effettuano compensazioni inverse.

3. Stato attuale
3.1 Motore quantitativo

Il FifoLotEngine elabora attualmente:

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
FifoDataQualityIssue
FifoEngineResult


L’ordine quantitativo corrente è:

TRANSFER_DEPART
→ TRANSFER_ARRIVE
→ SPLIT
→ BUY / SELL / ADJUSTMENT


Tale ordinamento resta invariato.

3.2 Eventi economici

Le transazioni:

DIVIDEND
INTEREST
FEE
TAX


non entrano oggi nel replay quantitativo.

Attualmente:

DIVIDEND e INTEREST sono allocati dal LotsAnalysisService;
FEE e TAX sono contabilizzati dal Portfolio Engine;
FEE e TAX non vengono attribuiti ai lotti;
non esistono metriche FIFO nette.
3.3 Integrità del segno

La situazione verificata è:

CREATE API
→ FEE/TAX positive rifiutate da TXCreateItem.

IMPORT BRIM
→ usa TXCreateItem;
→ FEE/TAX positive rifiutate.

UPDATE API
→ TXUpdateItem non riapplica le business rule;
→ una FEE/TAX positiva può essere salvata.

ORM/DB diretto
→ nessun CHECK sul segno;
→ inserimenti incoerenti tecnicamente possibili.


Il problema applicativo reale da correggere è l’UPDATE.

L’inserimento ORM diretto è un caso limite esterno al funzionamento ordinario, ma deve essere almeno verificato sui dati esistenti prima di assumere globalmente:

CostTotal=−AmountCostTotal=-Amount
4. Architettura a tendere

Deve esistere un solo motore pubblico:

FifoLotEngine.run(...)


e un solo risultato completo:

FifoEngineResult


Pipeline:

┌────────────────────────────────────────────────────────────┐
│ LotsAnalysisService                                        │
│                                                            │
│ DB · autorizzazioni · FX · prezzi · qbq                    │
│ costruzione eventi nativi e target                         │
└───────────────────────────┬────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ FifoLotEngine.run()                                        │
│                                                            │
│  1. Quantitative Replay                                    │
│     TRANSFER → SPLIT → BUY / SELL / ADJUSTMENT             │
│              │                                             │
│              ▼                                             │
│     lotti · frammenti · closure                            │
│              │                                             │
│  2. Economic Pooling and Allocation                        │
│     DIVIDEND · INTEREST · FEE · TAX                        │
│              │                                             │
│              ▼                                             │
│     pool · target · allocazioni · orphan                   │
│              │                                             │
│  3. Combined Validation                                    │
│     quantità · conservazione · scope · validità            │
│              │                                             │
│              ▼                                             │
│     FifoEngineResult                                       │
└───────────────────────────┬────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ LotsAnalysisService                                        │
│                                                            │
│ history · DTO · API                                        │
└───────────────────────────┬────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ Frontend                                                   │
│                                                            │
│ lordo · costi · netto · audit · Data Quality               │
└────────────────────────────────────────────────────────────┘


Gli stage possono essere componenti privati, ma nessuno deve poter essere eseguito come motore pubblico alternativo.

5. Migrazione

Lo sviluppo può procedere per fasi sul branch dedicato, ma il merge finale è atomico.

Al termine non devono coesistere:

vecchia e nuova firma del motore;
vecchio e nuovo FifoEngineResult;
income allocato sia nel service sia nel motore;
due percorsi per il calcolo lordo;
due percorsi per l’allocazione economica.


Backend, API generata e frontend vengono aggiornati insieme.

6. Fase 0 — Integrità preliminare
6.1 Correzione dell’UPDATE

TXUpdateItem deve validare il record finale risultante dal merge:

transazione corrente
+
patch richiesta
=
stato finale candidato


Lo stato finale deve rispettare le stesse business rule del CREATE:

tipo;
cash obbligatorio;
quantità;
segno dell’importo;
asset opzionale/obbligatorio;
currency.


Non basta validare i singoli campi contenuti nella patch.

Per FEE e TAX:

Amount<0Amount<0

deve valere anche dopo un UPDATE.

6.2 Verifica dei dati esistenti

Prima dell’implementazione economica va eseguita una verifica diagnostica su:

FEE con amount >= 0
TAX con amount >= 0
BUY con segno incoerente
SELL con segno incoerente
DIVIDEND/INTEREST con segno incoerente


Se non emergono dati anomali, la nuova matematica può assumere:

CostTotal=−AmountCostTotal=-Amount

senza abs() difensivo.

Se emergono dati anomali, devono essere riportati e corretti prima della migrazione.

6.3 Vincolo DB

Un CHECK DB sul segno è un hardening consigliato, ma non costituisce un prerequisito architetturale del FIFO.

Se introdotto, deve essere preceduto dall’audit dei dati legacy.

La protezione applicativa obbligatoria resta:

CREATE
IMPORT
UPDATE

6.4 Hardening quote_base_quantity

Rimuovere dal motore:

value_for_lot
aggregate_value
relative_return_for_lot


poiché:

non sono qbq-aware;
non hanno consumer produttivi;
costituiscono un rischio di riuso errato.

La valutazione di mercato continua a usare:

OpenValue=QuantityQuoteBaseQuantity⋅MarketQuoteOpenValue= \frac{Quantity}{QuoteBaseQuantity}\cdot MarketQuote

Test permanente:

Quantity=1000,QBQ=100,MarketQuote=98,50Quantity=1000,\quad QBQ=100,\quad MarketQuote=98{,}50 OpenValue=985OpenValue=985

FEE e TAX non sono quotazioni e non subiscono scaling qbq.

7. Eventi normalizzati
7.1 Evento quantitativo
QuantitativeEvent=(id,date,type,asset,broker,quantity,amount,data)QuantitativeEvent= (id,date,type,asset,broker,quantity,amount,data)

con:

BUY
SELL
ADJUSTMENT_IN
ADJUSTMENT_OUT
TRANSFER_DEPART
TRANSFER_ARRIVE
SPLIT

7.2 Evento economico
EconomicEvent=(id,date,type,asset,broker,nativeAmount,nativeCurrency,targetAmount,targetCurrency,description)EconomicEvent= ( id, date, type, asset, broker, nativeAmount, nativeCurrency, targetAmount, targetCurrency, description )

con:

DIVIDEND
INTEREST
FEE
TAX


Il LotsAnalysisService risolve gli FX prima di invocare il motore.

8. Semantica temporale dei proventi

Per un DIVIDEND o INTEREST registrato nel giorno DD:

EligibleQuantityi(D)=OpenQuantityi(D−1)EligibleQuantity_i(D) = OpenQuantity_i(D-1)

Quindi:

BUY in D
→ non eleggibile

SELL in D
→ eleggibile

BUY e SELL in D su una posizione nata in D
→ non eleggibile

lotto completamente venduto in D
→ ancora eleggibile per il provento di D


L’Asset Event non modifica questa regola.

8.1 Split nello stesso giorno

Lo split applica lo stesso rapporto a tutti i lotti interessati:

qi′=rqiq_i'=rq_i

Pertanto:

rqi∑jrqj=qi∑jqj\frac{rq_i}{\sum_jrq_j} = \frac{q_i}{\sum_jq_j}

I pesi pre-split e post-split coincidono. L’eleggibilità può quindi usare coerentemente lo stato di D−1D-1.

9. Scope broker e transfer

Per asset aa, broker accreditante bb e giorno DD:

La,b,D={Li:directioni=LONG, EligibleQuantityi(D)>0, CustodyCompatiblei(b,D)}\mathcal L_{a,b,D} = \left\{ L_i: direction_i=LONG,\, EligibleQuantity_i(D)>0,\, CustodyCompatible_i(b,D) \right\}
9.1 Accredito sul From

Sono eleggibili:

frammenti BROKER sul From
+
frammenti IN_TRANSIT con source_broker_id = From.

9.2 Accredito sul To

Sono eleggibili soltanto quantità già presenti sul broker To a D−1D-1.

9.3 Giorno di arrivo

Se un provento viene accreditato sul To nel giorno di arrivo, ma a D−1D-1 la quantità era ancora in transito:

nessun lotto eleggibile;
asset_orphan_income;
ASSET_INCOME_NO_ELIGIBLE_LOTS.


Non vengono introdotte eccezioni end-of-day.

10. Pool economici
10.1 Chiave

Gli eventi economici sono raggruppati per:

asset_id
broker_id
date
economic_type
native_currency
target_currency


Più eventi omogenei della stessa chiave formano un unico pool.

Esempio:

FEE -2 EUR
FEE -3 EUR

NativeFeePool=5 EURNativeFeePool=5\ EUR

Le transazioni originali restano identificabili tramite:

source_transaction_ids[]

10.2 Conversione del pool

Poiché gli eventi di un pool condividono data e valuta nativa, il service converte una sola volta il totale:

TargetPool=FXConvert(NativePool,NativeCurrency,TargetCurrency,Date)TargetPool= FXConvert \left( NativePool, NativeCurrency, TargetCurrency, Date \right)

Non è necessario convertire singolarmente ogni riga del pool per calcolarne il totale.

11. Pool income

DIVIDEND e INTEREST condividono la stessa funzione di eleggibilità:

EligibleLots=f(asset,broker,D−1)EligibleLots= f(asset,broker,D-1)

Il tipo specifico non modifica i lotti eleggibili.

Pertanto, per la stessa chiave:

asset
broker
data
valuta


gli income sono:

tutti allocabili
oppure
tutti orphan.


Non è possibile che nello stesso pool TAX un income risulti allocabile e un altro orphan.

Questa proprietà resta valida finché l’eleggibilità non dipende:

dal tipo DIVIDEND/INTEREST;
dall’Asset Event;
da una ex-date specifica per transazione;
da regole income-specifiche.
12. Income senza lotti eleggibili

Se:

La,b,D=∅\mathcal L_{a,b,D}=\varnothing

l’intero pool income diventa:

asset_orphan_income


e produce:

ASSET_INCOME_NO_ELIGIBLE_LOTS
severity = WARNING
analysis_status = DEGRADED


Non viene distribuito artificialmente ad altri broker o lotti.

13. Pool FEE
13.1 Target same-day

Se esistono BUY o SELL compatibili nello stesso giorno, partecipano tutti allo stesso pool target.

Gli ADJUSTMENT_IN/OUT non partecipano al pool trade.

Per ogni trade kk:

NativeTradeValuek=∣TransactionAmountk∣NativeTradeValue_k= |TransactionAmount_k|

Il service converte nella target currency:

TargetTradeValuek=∣FXConvert(TransactionAmountk,TransactionCurrencyk,TargetCurrency,Datek)∣TargetTradeValue_k= \left| FXConvert \left( TransactionAmount_k, TransactionCurrency_k, TargetCurrency, Date_k \right) \right|

Il peso è:

βk=TargetTradeValuek∑jTargetTradeValuej\beta_k= \frac{TargetTradeValue_k} {\sum_jTargetTradeValue_j}

La quota di FEE sul trade è:

TargetFeek=TargetFeePool⋅βkTargetFee_k= TargetFeePool\cdot\beta_k

Non si applica quote_base_quantity.

13.2 Pool misto BUY/SELL

Quando convivono BUY e SELL:

rule = SAME_DAY_MIXED_TRADES


La FEE viene distribuita per controvalore target.

Questa è una policy ufficiale e non genera un warning di ambiguità.

L’audit deve rendere esplicita la regola applicata.

13.3 Previous-day

Se non esistono trade same-day, vengono cercati BUY e SELL compatibili esclusivamente in D−1D-1:

rule = PREVIOUS_DAY_TRADES


Non vengono cercati trade in D+1D+1.

13.4 Allocazione sui lotti
BUY

La quota del trade BUY viene attribuita ai lotti aperti dall’operazione.

SELL

La quota del trade SELL viene attribuita ai lotti ridotti o chiusi, in proporzione alla quantità chiusa:

wi=ClosedQuantityi∑jClosedQuantityjw_i= \frac{ClosedQuantity_i} {\sum_jClosedQuantity_j}
14. Pool TAX
14.1 Target same-day

Il target primario della TAX è l’unione:

DIVIDEND ∪ INTEREST


per lo stesso:

asset
broker
giorno
valuta compatibile.


Per ogni income kk:

αk=∣TargetIncomek∣∑j∣TargetIncomej∣\alpha_k= \frac{|TargetIncome_k|} {\sum_j|TargetIncome_j|}

Se wi,kw_{i,k} è il peso del lotto nell’income kk:

Wi=∑kαkwi,kW_i= \sum_k\alpha_kw_{i,k} TargetTaxAllocationi=TargetTaxPool⋅WiTargetTaxAllocation_i= TargetTaxPool\cdot W_i
14.2 Pool interamente orphan

Poiché tutti gli income con la stessa chiave condividono il medesimo insieme di lotti eleggibili, il pool TAX è:

interamente allocabile sugli income; oppure
interamente orphan.

Se gli income target sono orphan:

asset_orphan_taxes = TargetTaxPool
ASSET_COST_NO_ELIGIBLE_LOTS


Non esistono ripartizioni miste allocated/orphan dentro lo stesso pool TAX.

14.3 Trade same-day

Se non esistono income same-day, la TAX viene attribuita al pool BUY/SELL same-day usando i pesi dei trade.

14.4 Previous-day

Se non esistono candidati same-day:

income compatibili in D−1D-1;
trade compatibili in D−1D-1.

Non vengono considerati eventi in D+1D+1.

15. Fallback

Se non esistono target same-day o previous-day, FEE/TAX vengono ripartite sui lotti LONG aperti a D−1D-1, sullo stesso asset e broker:

wi=OpenQuantityi(D−1)∑jOpenQuantityj(D−1)w_i= \frac{OpenQuantity_i(D-1)} {\sum_jOpenQuantity_j(D-1)}

Regola:

OPEN_LOTS_FALLBACK


Se non esistono lotti eleggibili:

asset_orphan_fees
asset_orphan_taxes
ASSET_COST_NO_ELIGIBLE_LOTS

16. Crossing LONG/SHORT

Per un trade che chiude una direzione e apre quella opposta:

q=qclose+qopenq=q_{close}+q_{open} Costclose=CostTrade⋅qcloseqCost_{close} = CostTrade\cdot\frac{q_{close}}{q} Costopen=CostTrade⋅qopenqCost_{open} = CostTrade\cdot\frac{q_{open}}{q}

e:

Costclose+Costopen=CostTradeCost_{close}+Cost_{open}=CostTrade

La quota close viene distribuita sui lotti chiusi.

La quota open viene assegnata al nuovo lotto nella direzione opposta.

Le LotClosure restano immutabili. I costi vengono registrati negli accumulatori economici associati ai lotti.

17. Accumulatori

Per il lotto LiL_i:

original_cost
sale_proceeds
gross_income
allocated_fees
allocated_taxes
open_value


Gli accumulatori economici non modificano le strutture quantitative.

18. Formule
18.1 Valore lordo
GrossEconomicValuei(t)=OpenValuei(t)+SaleProceedsi(t)+GrossIncomei(t)GrossEconomicValue_i(t) = OpenValue_i(t)+ SaleProceeds_i(t)+ GrossIncome_i(t)
18.2 P&L lordo
GrossPnLi(t)=GrossEconomicValuei(t)−OriginalCostiGrossPnL_i(t) = GrossEconomicValue_i(t)- OriginalCost_i
18.3 P&L netto
NetPnLi(t)=GrossPnLi(t)−AllocatedFeesi(t)−AllocatedTaxesi(t)NetPnL_i(t) = GrossPnL_i(t)- AllocatedFees_i(t)- AllocatedTaxes_i(t)

Equivalentemente:

NetPnLi(t)=OpenValuei(t)+SaleProceedsi(t)+GrossIncomei(t)−OriginalCosti−AllocatedFeesi(t)−AllocatedTaxesi(t)NetPnL_i(t)= OpenValue_i(t)+ SaleProceeds_i(t)+ GrossIncome_i(t)- OriginalCost_i- AllocatedFees_i(t)- AllocatedTaxes_i(t)
18.4 Rendimenti

Per:

OriginalCosti>0OriginalCost_i>0 GrossReturni(t)=GrossPnLi(t)OriginalCostiGrossReturn_i(t) = \frac{GrossPnL_i(t)} {OriginalCost_i} NetReturni(t)=NetPnLi(t)OriginalCostiNetReturn_i(t) = \frac{NetPnL_i(t)} {OriginalCost_i}

Per gli SHORT il denominatore resta il nozionale di apertura già usato dal modello lordo.

19. Persistenza dopo chiusura

Dopo la chiusura completa:

OpenValuei(t)=0OpenValue_i(t)=0

Restano cristallizzati:

sale_proceeds
gross_income
allocated_fees
allocated_taxes
gross P&L
net P&L
gross return
net return


Un costo registrato dopo la chiusura e attribuito tramite PREVIOUS_DAY_TRADES modifica il risultato netto dalla propria data.

Il lordo resta invariato.

20. Audit a tre livelli

L’audit è sempre incluso nella risposta FIFO.

20.1 Gruppo sorgente
EconomicAllocationGroup
- asset_id
- broker_id
- date
- economic_type
- rule
- source_transaction_ids[]
- native_currency
- native_total
- target_currency
- target_total
- fx_rate
- native_orphan
- target_orphan
- targets[]

20.2 Target operativo
TargetOperationAllocation
- target_transaction_ids[]
- context
- operation_weight
- native_amount
- target_amount
- lots[]


context può essere:

OPENING
CLOSURE
INCOME
HOLDING

20.3 Allocazione al lotto
EconomicLotAllocation
- lot_id
- weight
- native_amount
- target_amount


Lo stesso lotto può comparire sotto target o contesti diversi senza perdere il breakdown.

21. Conservazione
21.1 Nativa
∑iNativeAllocationi+NativeOrphan=NativePool\sum_iNativeAllocation_i+ NativeOrphan = NativePool
21.2 Target
∑iTargetAllocationi+TargetOrphan=TargetPool\sum_iTargetAllocation_i+ TargetOrphan = TargetPool

Gli eventuali residui vengono assegnati deterministicamente all’ultimo elemento secondo un ordinamento stabile.

22. Status
22.1 Stato globale dell’analisi
COMPLETE
DEGRADED
FAILED

COMPLETE

Replay quantitativo e allocazione economica completi e affidabili.

DEGRADED

Il replay quantitativo resta affidabile, ma esiste almeno un problema economico isolabile:

orphan;
FX mancante;
conservazione fallita in un pool;
metrica netta localmente indisponibile.
FAILED

Il replay quantitativo o la topologia complessiva non sono affidabili.

Esempi:

quantità non riconciliabile;
topologia frammenti incoerente;
transfer quantitativamente non ricostruibile;
violazione di un invariante quantitativo non isolabile.
22.2 Stato locale del lotto
net_metrics_status:
AVAILABLE
UNAVAILABLE


Gli errori economici isolabili non invalidano:

quantità;
custodia;
closure;
P&L lordo;
rendimento lordo;
altri lotti non coinvolti.

ALLOCATION_CONSERVATION_FAILED è sempre associata a un pool noto e produce:

analysis_status = DEGRADED
net_metrics_status = UNAVAILABLE


solo sui lotti interessati.

23. Data Quality
23.1 Provento senza lotti
ASSET_INCOME_NO_ELIGIBLE_LOTS
severity = WARNING

23.2 Costo senza lotti
ASSET_COST_NO_ELIGIBLE_LOTS
severity = WARNING

23.3 Cambio mancante
FX_RATE_MISSING_FOR_ALLOCATION
severity = WARNING

23.4 Conservazione fallita
ALLOCATION_CONSERVATION_FAILED
severity = ERROR


Il problema resta localizzato al pool.

23.5 Segno inatteso

Dopo la correzione dell’UPDATE e la verifica dei dati esistenti, il segno coerente diventa una precondizione di integrità delle transazioni.

Se viene introdotto anche il vincolo DB, ECONOMIC_EVENT_UNEXPECTED_SIGN non è necessario nel motore FIFO.

Senza vincolo DB, può restare un’asserzione difensiva interna, non una policy economica.

24. Risultato unico
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
└─ analysis_status


Tutte le raccolte fanno parte del risultato canonico.

25. DTO/API

I campi esistenti mantengono la semantica lorda:

total_pnl
total_return


Si aggiungono:

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


La response include sempre:

economic_allocation_groups[]
asset_orphan_income
asset_orphan_fees
asset_orphan_taxes


Backend, client generato e frontend vengono migrati insieme.

26. Riconciliazione

La chiave usa il broker dell’evento economico:

asset_id
event_broker_id
periodo
native currency
target currency


Devono valere:

AllocatedIncome+AssetOrphanIncome=AbsoluteAssetIncomeAllocatedIncome+ AssetOrphanIncome = AbsoluteAssetIncome AllocatedFees+AssetOrphanFees=AbsoluteAssetFeesAllocatedFees+ AssetOrphanFees = AbsoluteAssetFees AllocatedTaxes+AssetOrphanTaxes=AbsoluteAssetTaxesAllocatedTaxes+ AssetOrphanTaxes = AbsoluteAssetTaxes

Il Portfolio Engine introduce accumulatori assoluti pre-share:

per_income_absolute
per_fees_absolute
per_taxes_absolute


Successivamente:

Amountuser=Amountabsolute⋅Shareuser,brokerAmount^{user} = Amount^{absolute}\cdot Share_{user,broker}
27. Performance

Durante ogni analisi vengono costruiti indici temporanei:

opening transaction → lot
closing transaction → closures
(date, asset, broker) → BUY/SELL
(date, asset, broker) → income
(lot, date) → eligible quantity
(broker, date) → custody-compatible fragments


Obiettivo:

quantitative replay:
O(N log N + consumo frammenti)

pooling:
O(E)

matching:
O(P · k)

history:
O(L · D)


Non vengono introdotte cache persistenti.

28. Sequenza di sviluppo
Fase 0 — Integrità e qbq
correzione UPDATE;
audit segni dati esistenti;
eventuale CHECK DB;
rimozione metodi non qbq-aware;
test qbq=100.

Fase 1 — Proventi
D-1;
scope broker;
transfer From/To;
orphan income;
pool TAX interamente allocabile o orphan.

Fase 2 — Contratto unico
nuova firma FifoLotEngine.run;
nuovo FifoEngineResult;
aggiornamento call-site;
tipi audit a tre livelli.

Fase 3 — Pooling economico
EconomicEvent native+target;
pool FEE/TAX;
trade value da target amount;
income;
audit;
conservazione.

Fase 4 — FEE/TAX
same-day;
previous-day;
fallback;
crossing;
orphan.

Fase 5 — Netto e history
allocated fees/taxes;
net P&L;
net return;
persistenza post-chiusura;
status locale/globale.

Fase 6 — DTO e frontend
API;
client generato;
lordo/netto;
breakdown costi;
audit;
Data Quality.

Fase 7 — Portfolio Engine
accumulatori pre-share;
riconciliazione assoluta;
proiezione user-scoped.

Fase 8 — Cleanup e benchmark
rimozione vecchio income allocator;
rimozione helper morti;
benchmark payload audit;
documentazione delle policy.

29. Test obbligatori
Integrità
CREATE FEE/TAX positiva → rifiutata
IMPORT FEE/TAX positiva → rifiutata
UPDATE FEE/TAX positiva → rifiutata
audit dati legacy

Semantica temporale
BUY same-day esclusa
SELL same-day inclusa
lotto aperto/chiuso same-day escluso
split same-day

Broker e transfer
provento broker corretto
From durante transito
To durante transito
To nel giorno di arrivo → orphan

Pool FEE
più FEE
solo BUY
solo SELL
BUY+SELL
previous-day
crossing LONG/SHORT
bond qbq=100
trade multivaluta

Pool TAX
più TAX
DIVIDEND+INTEREST
pool interamente allocabile
pool interamente orphan
same-day
previous-day

FX
target EUR
target USD
FX mancante
conservazione nativa
conservazione target
residui

Metriche
gross P&L
net P&L
gross return
net return
estimated-at-cost
chiusura completa
costo post-chiusura
SHORT
original_cost nullo

Status
COMPLETE
DEGRADED con orphan
DEGRADED con FX mancante
DEGRADED con netto locale unavailable
FAILED quantitativo

Riconciliazione
FIFO assoluto
Portfolio pre-share
Portfolio share-weighted
broker multipli
asset-orphan

30. Risultato a tendere
TRANSAZIONI
BUY · SELL · DIVIDEND · INTEREST · FEE · TAX
                       │
                       ▼
       PREPARAZIONE FX IN TARGET CURRENCY
                       │
                       ▼
                 FIFO LOT ENGINE
                       │
       ┌───────────────┴────────────────┐
       ▼                                │
QUANTITATIVE REPLAY                     │
lotti · frammenti · closure             │
       │                                │
       ▼                                │
ECONOMIC POOLING                        │
income · fee · tax                      │
       │                                │
       ▼                                │
TARGET OPERATIONS                       │
opening · closure · income · holding    │
       │                                │
       ▼                                │
LOT ALLOCATION                          │
gross income · fee · tax · orphan       │
       │                                │
       ▼                                │
COMBINED VALIDATION                     │
quantità · conservazione · status       │
       │                                │
       └───────────────┬────────────────┘
                       ▼
               FIFO ENGINE RESULT
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
        LORDO        COSTI         NETTO
     Gross P&L      Fee/Tax       Net P&L
     Gross Return   Audit         Net Return

31. Conclusione

L’architettura è pronta per lo sviluppo.

Non risultano ulteriori paradossi logici o criticità architetturali aperte. Il solo bug applicativo concreto emerso nell’ultima verifica è la possibilità di salvare FEE/TAX positive tramite UPDATE, da correggere nella Fase 0.

La matematica successiva può quindi assumere, dopo il gate di integrità:

FEE.amount<0FEE.amount<0 TAX.amount<0TAX.amount<0

e:

CostTotal=−AmountCostTotal=-Amount

Il resto dell’evoluzione è incrementale, testabile per fasi e compatibile con un merge finale atomico del nuovo sottosistema FIFO economico.
