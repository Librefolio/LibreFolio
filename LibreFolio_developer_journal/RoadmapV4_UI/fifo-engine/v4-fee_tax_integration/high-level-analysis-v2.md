FIFO Engine v4 — Integrazione dei flussi economici e metriche nette
1. Obiettivo

Estendere il sottosistema FIFO affinché attribuisca ai lotti anche:

dividendi;
interessi;
commissioni;
imposte;

producendo una rappresentazione distinta di:

P&LgrosseP&LnetP\&L^{gross} \qquad\text{e}\qquad P\&L^{net}

senza modificare le transazioni originali, il loro schema DB o la matematica quantitativa già stabilizzata.

L’estensione deve essere:

deterministica;
conservativa;
auditabile;
broker-aware;
compatibile con transfer e posizioni parzialmente chiuse;
indipendente dalla valuta target;
feed-forward, senza compensazioni inverse.
2. Stato attuale
2.1 Motore quantitativo

Il FifoLotEngine elabora esclusivamente transazioni con quantità:

BUY
SELL
ADJUSTMENT_IN
ADJUSTMENT_OUT
TRANSFER_DEPART
TRANSFER_ARRIVE
SPLIT


Produce:

FifoLot
FragmentInterval
LotClosure
FifoDataQualityIssue


Il replay è ordinato secondo:

TRANSFER_DEPART
TRANSFER_ARRIVE
SPLIT
BUY / SELL / ADJUSTMENT


con ordine deterministico interno basato sulla transazione.

Questa sequenza è già stabilizzata e non deve essere sostituita da un nuovo ordinamento globale.

2.2 Eventi economici

Le transazioni con quantità nulla:

DIVIDEND
INTEREST
FEE
TAX


non entrano attualmente nel FifoLotEngine.

Dividendi e interessi asset-linked vengono caricati e allocati dal LotsAnalysisService.

FEE e TAX vengono contabilizzate soltanto dal Portfolio Engine a livello:

asset + broker + periodo


ma non sono attribuite ai singoli lotti.

2.3 Formule lorde attuali

Per il lotto LiL_i:

Vi(t)=OpenValuei(t)V_i(t)=OpenValue_i(t) Si(t)=SaleProceedsi(t)S_i(t)=SaleProceeds_i(t) Ii(t)=GrossIncomei(t)I_i(t)=GrossIncome_i(t) Ci=OriginalCostiC_i=OriginalCost_i

Il P&L lordo corrente è:

GrossPnLi(t)=Vi(t)+Si(t)+Ii(t)−CiGrossPnL_i(t) = V_i(t)+S_i(t)+I_i(t)-C_i

Il rendimento totale lordo è:

GrossReturni(t)=GrossPnLi(t)CiGrossReturn_i(t) = \frac{GrossPnL_i(t)}{C_i}

per:

Ci>0C_i>0

Le formule attuali risultano coerenti e non contano due volte i proventi.

2.4 Limiti attuali dell’allocazione dei proventi

L’allocazione corrente:

usa la quantità attiva nel giorno DD;
opera asset-wide;
non limita l’allocazione al broker dell’accredito;
non include una policy specifica per quantità in transito;
ignora silenziosamente il provento se non esistono lotti eleggibili.

Questa semantica deve essere sostituita.

3. Invarianti da preservare
3.1 Invarianti quantitativi
OpenQuantityi(t)≥0OpenQuantity_i(t)\ge 0

per ogni lotto rappresentato con quantità positiva e direzione separata.

Positiona,b(t)=∑iσi OpenQuantityi,b(t)Position_{a,b}(t) = \sum_i \sigma_i\,OpenQuantity_{i,b}(t)

dove:

σi={+1LONG−1SHORT\sigma_i= \begin{cases} +1 & LONG\\ -1 & SHORT \end{cases}

Transfer e split non producono P&L:

ΔP&Ltransfer=0\Delta P\&L_{transfer}=0 ΔP&Lsplit=0\Delta P\&L_{split}=0

Per uno split di rapporto rr:

qi′=rqiq_i'=rq_i pi′=pirp_i'=\frac{p_i}{r} qi′pi′=qipiq_i'p_i'=q_ip_i
3.2 Conservazione degli importi economici

Per ogni evento economico EE:

∑iAllocationE,i=AmountE\sum_i Allocation_{E,i}=Amount_E

La conservazione deve valere nella valuta originaria dell’evento, prima della conversione FX.

Gli eventuali residui decimali vengono assegnati deterministicamente all’ultimo lotto eleggibile secondo un ordinamento stabile.

3.3 Immutabilità del costo originario

Il costo originario continua a rappresentare esclusivamente l’apertura del lotto:

OriginalCosti=OpeningQuantityi⋅OpeningUnitPriceiOriginalCost_i = OpeningQuantity_i\cdot OpeningUnitPrice_i

FEE e TAX non modificano original_cost.

Questa scelta evita operazioni compensative del tipo:

aggiungere il costo alla base
e sottrarre lo stesso costo dal risultato

4. Architettura a tendere

L’estensione economica appartiene al dominio FIFO, ma deve restare separata dal replay quantitativo.

┌───────────────────────────────────────────────────────────────┐
│ LOTS ANALYSIS SERVICE                                         │
│                                                               │
│ Caricamento DB · FX · prezzi · quote_base_quantity            │
│ Normalizzazione eventi quantitativi ed economici              │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│ FIFO LOT ENGINE                                               │
│                                                               │
│ Passata 1 — Replay quantitativo                               │
│ TRANSFER → SPLIT → BUY/SELL/ADJUSTMENT                        │
│ → lotti, frammenti, closure                                   │
│                                                               │
│ Passata 2 — Allocazione economica                             │
│ DIVIDEND/INTEREST → entitlement                               │
│ FEE/TAX → target matching                                     │
│ → allocazioni, accumulatori, issue                            │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│ LOTS ANALYSIS SERVICE                                         │
│                                                               │
│ Conversione FX delle allocazioni                              │
│ Valutazione qbq-aware                                         │
│ History lorde/nette · Data Quality · DTO                      │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│ FRONTEND                                                      │
│                                                               │
│ P&L lordo/netto · rendimento lordo/netto · breakdown costi   │
└───────────────────────────────────────────────────────────────┘


La seconda passata può essere implementata come:

FifoLotEngine.replay_economic()


oppure come componente interno dedicato:

FifoEconomicAllocator


ma deve restare parte del dominio FIFO.

5. Eventi economici normalizzati

Si introduce un tipo separato dagli eventi quantitativi:

EconomicEvent=(id, date, type, asset, broker, amount, currency, description)EconomicEvent= \left( id,\, date,\, type,\, asset,\, broker,\, amount,\, currency,\, description \right)

con:

type ∈ {
    DIVIDEND,
    INTEREST,
    FEE,
    TAX
}


L’evento conserva la valuta originaria.

Il motore determina:

lotti eleggibili;
pesi di allocazione;
contesto dell’allocazione;
regola euristica utilizzata.

Il service applica invece la conversione FX.

6. Hardening di quote_base_quantity
6.1 Stato attuale

Il percorso produttivo usa correttamente:

OpenValue=QuantityQuoteBaseQuantity⋅MarketQuoteOpenValue= \frac{Quantity}{QuoteBaseQuantity}\cdot MarketQuote

Alcuni metodi del motore risultano invece non qbq-aware:

value_for_lot
aggregate_value
relative_return_for_lot


Questi metodi non hanno consumer produttivi, ma costituiscono un rischio di riuso futuro.

6.2 Stato a tendere

Prima dell’estensione economica, tali metodi devono essere:

rimossi, se inutilizzati; oppure
resi qbq-aware tramite parametro obbligatorio.

Deve esistere un test permanente con:

quote_base_quantity = 100


Esempio:

Quantity=1000Quantity=1000 MarketQuote=98,50MarketQuote=98{,}50 QBQ=100QBQ=100 OpenValue=1000100⋅98,50=985OpenValue= \frac{1000}{100}\cdot98{,}50 = 985
7. Nuova semantica dei proventi
7.1 Titolarità temporale

Un provento registrato nel giorno DD viene attribuito alle quantità possedute all’inizio del giorno:

EligibleQuantityi(D)=OpenQuantityi(D−1)EligibleQuantity_i(D) = OpenQuantity_i(D-1)

Ne deriva:

BUY in D
→ non partecipa al provento di D

SELL in D
→ partecipa al provento di D

BUY in D-1
→ partecipa

SELL in D-1
→ non partecipa


L’Asset Event collegato resta informativo. La data utilizzata è quella della transazione.

7.2 Scope broker

Per un provento relativo ad asset aa, broker bb e giorno DD:

La,b,D={Li:directioni=LONG, EligibleQuantityi(D)>0, CustodyCompatiblei(b,D)}\mathcal L_{a,b,D} = \left\{ L_i: direction_i=LONG,\, EligibleQuantity_i(D)>0,\, CustodyCompatible_i(b,D) \right\}

Il peso è:

wi(D)=EligibleQuantityi(D)∑j∈La,b,DEligibleQuantityj(D)w_i(D)= \frac{EligibleQuantity_i(D)} {\sum_{j\in\mathcal L_{a,b,D}}EligibleQuantity_j(D)}

e:

IncomeAllocationi,D=IncomeD⋅wi(D)IncomeAllocation_{i,D} = Income_D\cdot w_i(D)
7.3 Provento durante un transfer

Durante il transito, la quantità resta economicamente associabile al broker sorgente.

Accredito sul broker From

Sono eleggibili:

frammenti BROKER sul From
+
frammenti IN_TRANSIT con source_broker_id = From


Formalmente:

EligibleQtyFrom=QtyBrokerFrom+QtyTransitFromEligibleQty_{From} = Qty_{BrokerFrom} + Qty_{TransitFrom}
Accredito sul broker To

Sono eleggibili soltanto i frammenti già arrivati:

EligibleQtyTo=QtyBrokerToEligibleQty_{To} = Qty_{BrokerTo}

Il frammento in transito non viene attribuito al broker To prima dell’arrivo.

7.4 Nessun lotto eleggibile

Se:

La,b,D=∅\mathcal L_{a,b,D}=\varnothing

il provento non viene allocato.

Il risultato contiene:

ASSET_INCOME_NO_ELIGIBLE_LOTS
severity = WARNING
calculation_status = DEGRADED


L’issue deve includere:

transaction_id
asset_id
broker_id
date
amount
currency


Il messaggio deve indicare una probabile incoerenza tra:

data;
broker;
asset;
BUY;
SELL;
transfer.
8. Allocazione di FEE e TAX
8.1 Principio

Il motore non determina la natura fiscale esatta della transazione.

FEE e TAX sono trattate uniformemente come:

AllocatedCostAllocatedCost

distinguendo soltanto il tipo contabile:

FEE
TAX


La descrizione originale viene preservata per audit e visualizzazione.

8.2 Costi privi di asset

Se:

asset_id = null


l’evento viene ignorato dal dominio FIFO.

Resta contabilizzato dal Portfolio Engine come effetto broker-level.

8.3 Gerarchia deterministica dei target

L’allocatore tenta, nell’ordine:

1. SAME_DAY_SELL
2. SAME_DAY_BUY
3. SAME_DAY_INCOME
4. ADJACENT_DAY_INCOME
5. OPEN_LOTS_FALLBACK
6. NO_ELIGIBLE_LOTS


Un eventuale collegamento esplicito potrà essere supportato in futuro, ma non costituisce prerequisito.

Ogni allocazione deve registrare la regola applicata.

9. Allocazione su SELL

Se una FEE/TAX viene associata a una SELL, viene attribuita ai lotti ridotti o chiusi dalla SELL.

Siano le closure:

CS={c1,…,cn}C_S=\{c_1,\ldots,c_n\}

Il peso è:

wi=ClosedQuantityi∑jClosedQuantityjw_i= \frac{ClosedQuantity_i} {\sum_j ClosedQuantity_j}

Il costo allocato è:

AllocatedCosti=CostTotal⋅wiAllocatedCost_i= CostTotal\cdot w_i

Questo vale per:

vendita parziale;
vendita completa;
SELL multi-lotto.

Il costo riduce il risultato netto, ma non modifica:

costo originario;
prezzo di apertura;
incasso lordo;
P&L lordo.
10. Allocazione su BUY

Se una FEE/TAX viene associata a una BUY, viene attribuita ai lotti aperti dalla BUY.

Per più lotti candidati:

wi=OpeningValuei∑jOpeningValuejw_i= \frac{OpeningValue_i} {\sum_j OpeningValue_j} AllocatedCosti=CostTotal⋅wiAllocatedCost_i= CostTotal\cdot w_i

Con una sola BUY:

AllocatedCosti=CostTotalAllocatedCost_i=CostTotal

Il costo non modifica original_cost; viene accumulato separatamente e riduce il risultato netto.

11. Attraversamento LONG/SHORT

Una BUY o SELL può contemporaneamente:

chiudere una direzione;
aprire la direzione opposta.
11.1 BUY: SHORT → LONG

Siano:

qc=quantitaˋ SHORT chiusaq_c=\text{quantità SHORT chiusa} qo=quantitaˋ LONG apertaq_o=\text{quantità LONG aperta} q=qc+qoq=q_c+q_o

Il costo viene suddiviso:

CostcloseShort=Cost⋅qcqCost_{closeShort} = Cost\cdot\frac{q_c}{q} CostopenLong=Cost⋅qoqCost_{openLong} = Cost\cdot\frac{q_o}{q}
11.2 SELL: LONG → SHORT

Analogamente:

CostcloseLong=Cost⋅qcqCost_{closeLong} = Cost\cdot\frac{q_c}{q} CostopenShort=Cost⋅qoqCost_{openShort} = Cost\cdot\frac{q_o}{q}

Ogni quota viene poi ripartita internamente sui lotti o sulle closure interessate.

12. Allocazione su DIVIDEND/INTEREST

Se la FEE/TAX viene associata a un provento, riutilizza esattamente i pesi già calcolati per il provento:

CostAllocationi=CostTotal⋅IncomeWeightiCostAllocation_i= CostTotal\cdot IncomeWeight_i

Il costo non richiede una nuova determinazione dei lotti eleggibili.

La ricerca considera:

proventi nello stesso giorno;
in assenza di candidati, proventi compatibili in D−1D-1 e D+1D+1.

In presenza di più candidati alla stessa distanza si applica un ordinamento deterministico e si registra la regola euristica.

13. Fallback sui lotti aperti

Se non esistono BUY, SELL o proventi candidati:

Lfallback={Li:asseti=a, brokeri=b, directioni=LONG, OpenQuantityi(D−1)>0}\mathcal L_{fallback} = \left\{ L_i: asset_i=a,\, broker_i=b,\, direction_i=LONG,\, OpenQuantity_i(D-1)>0 \right\}

Il peso è:

wi=OpenQuantityi(D−1)∑jOpenQuantityj(D−1)w_i= \frac{OpenQuantity_i(D-1)} {\sum_j OpenQuantity_j(D-1)}

Il fallback rappresenta costi generici dell’investimento, ad esempio:

custodia;
gestione;
costi periodici asset-linked.
13.1 Nessun target

Se:

Lfallback=∅\mathcal L_{fallback}=\varnothing

il costo non viene allocato.

Viene generata:

ASSET_COST_NO_ELIGIBLE_LOTS
severity = WARNING
calculation_status = DEGRADED


con dati diagnostici della transazione.

14. Modello feed-forward
14.1 Accumulatori per lotto

Ogni lotto mantiene:

original_cost
sale_proceeds
gross_income
allocated_fees
allocated_taxes
open_value


Gli accumulatori sono derivati runtime e non modificano il DB.

14.2 Valore economico lordo
GrossEconomicValuei(t)=OpenValuei(t)+SaleProceedsi(t)+GrossIncomei(t)GrossEconomicValue_i(t) = OpenValue_i(t)+ SaleProceeds_i(t)+ GrossIncome_i(t)
14.3 P&L lordo
GrossPnLi(t)=GrossEconomicValuei(t)−OriginalCostiGrossPnL_i(t) = GrossEconomicValue_i(t)- OriginalCost_i
14.4 Costi allocati
AllocatedCostsi(t)=AllocatedFeesi(t)+AllocatedTaxesi(t)AllocatedCosts_i(t) = AllocatedFees_i(t)+ AllocatedTaxes_i(t)
14.5 P&L netto
NetPnLi(t)=GrossPnLi(t)−AllocatedCostsi(t)NetPnL_i(t) = GrossPnL_i(t)- AllocatedCosts_i(t)

Equivalentemente:

NetPnLi(t)=OpenValuei(t)+SaleProceedsi(t)+GrossIncomei(t)−OriginalCosti−AllocatedFeesi(t)−AllocatedTaxesi(t)NetPnL_i(t)= OpenValue_i(t)+ SaleProceeds_i(t)+ GrossIncome_i(t)- OriginalCost_i- AllocatedFees_i(t)- AllocatedTaxes_i(t)
14.6 Rendimenti
GrossReturni(t)=GrossPnLi(t)OriginalCostiGrossReturn_i(t) = \frac{GrossPnL_i(t)} {OriginalCost_i} NetReturni(t)=NetPnLi(t)OriginalCostiNetReturn_i(t) = \frac{NetPnL_i(t)} {OriginalCost_i}

per:

OriginalCosti>0OriginalCost_i>0
15. Feed-forward degli eventi

Ogni evento determina esclusivamente delta sugli accumulatori.

BUY
→ apre quantità e original_cost

SELL
→ riduce quantità e incrementa sale_proceeds

DIVIDEND / INTEREST
→ incrementa gross_income

FEE
→ incrementa allocated_fees

TAX
→ incrementa allocated_taxes

PRICE
→ aggiorna open_value

TRANSFER
→ modifica custodia, nessun delta economico

SPLIT
→ riscala quantità e prezzo, nessun delta economico


Non sono previste operazioni inverse o compensative.

16. Audit trail

Ogni allocazione economica deve essere rappresentata da:

CostAllocation=(transactionId, lotId, date, type, context, rule, amount, currency)CostAllocation= \left( transactionId,\, lotId,\, date,\, type,\, context,\, rule,\, amount,\, currency \right)

con:

type:
FEE | TAX

context:
OPENING | CLOSURE | INCOME | HOLDING

rule:
SAME_DAY_SELL
SAME_DAY_BUY
SAME_DAY_INCOME
ADJACENT_DAY_INCOME
OPEN_LOTS_FALLBACK


L’audit trail consente di:

spiegare il risultato all’utente;
verificare le assunzioni;
confrontare l’allocazione con i dati BRIM;
modificare in futuro le euristiche senza cambiare le transazioni.
17. Conversione FX

Il dominio FIFO determina le allocazioni nella valuta originaria dell’evento.

Per ogni allocazione:

NativeAllocationi,E=NativeAmountE⋅wiNativeAllocation_{i,E} = NativeAmount_E\cdot w_i

Il LotsAnalysisService converte successivamente:

TargetAllocationi,E=FXConvert(NativeAllocationi,E,CurrencyE,TargetCurrency,DateE)TargetAllocation_{i,E} = FXConvert \left( NativeAllocation_{i,E}, Currency_E, TargetCurrency, Date_E \right)

Gli accumulatori in target currency vengono costruiti soltanto dopo la conversione.

18. Contratto DTO a tendere

I campi esistenti mantengono la semantica lorda:

total_pnl
total_return


Si aggiungono:

allocated_fees
allocated_taxes
net_total_pnl
net_total_return


Eventualmente:

cost_allocations[]


per dettaglio e audit.

Non viene introdotta una rinomina distruttiva dei campi esistenti.

19. Riconciliazione con il Portfolio Engine

Il Portfolio Engine resta la vista aggregata. Il FIFO descrive la distribuzione sui lotti.

Devono valere:

∑iGrossIncomei+UnallocatedIncome=PortfolioIncome\sum_i GrossIncome_i + UnallocatedIncome = PortfolioIncome ∑iAllocatedFeesi+UnallocatedFees=PortfolioFees\sum_i AllocatedFees_i + UnallocatedFees = PortfolioFees ∑iAllocatedTaxesi+UnallocatedTaxes=PortfolioTaxes\sum_i AllocatedTaxes_i + UnallocatedTaxes = PortfolioTaxes

Le due implementazioni non devono condividere necessariamente lo stesso algoritmo, ma devono riconciliarsi numericamente.

20. Stato attuale e stato a tendere
20.1 Proventi
OGGI
asset-wide
quantità attiva nel giorno D
nessuna gestione broker/transito
income orfano ignorato

TARGET
stato D-1
scope broker
transito attribuito al From
arrivo attribuito al To
issue se nessun lotto eleggibile

20.2 FEE/TAX
OGGI
contabilizzate soltanto a livello Portfolio Engine
nessuna attribuzione ai lotti
nessun P&L netto FIFO

TARGET
seconda passata economica nel dominio FIFO
allocazione deterministica
accumulatori FEE/TAX
P&L e rendimento lordo/netto
audit trail

20.3 quote_base_quantity
OGGI
percorso produttivo corretto
metodi motore non-qbq-aware inutilizzati ma esposti

TARGET
rimozione o firma qbq-aware obbligatoria
test permanente qbq=100

21. Sequenza di implementazione
Fase 0 — Hardening
rimuovere o rendere qbq-aware i metodi di valutazione grezza;
aggiungere test qbq=100.

Fase 1 — Proventi
regola D-1;
scope broker;
transfer From/To;
issue senza eleggibili;
test di riconciliazione.

Fase 2 — Allocatore economico
EconomicEvent;
seconda passata;
income allocation;
FEE/TAX target matching;
CostAllocation;
issue.

Fase 3 — Metriche nette
allocated_fees;
allocated_taxes;
net_total_pnl;
net_total_return;
history nette;
DTO/API.

Fase 4 — Frontend
Lordo/Netto;
breakdown FEE/TAX;
audit dell’allocazione;
tooltip e modale;
Data Quality.

22. Invarianti di test
Conservazione
∑iIncomeAllocationi=IncomeTotal\sum_i IncomeAllocation_i=IncomeTotal ∑iFeeAllocationi=FeeTotal\sum_i FeeAllocation_i=FeeTotal ∑iTaxAllocationi=TaxTotal\sum_i TaxAllocation_i=TaxTotal
Risultato netto
NetPnLi=GrossPnLi−Feesi−TaxesiNetPnL_i= GrossPnL_i- Fees_i- Taxes_i
Scope broker

Un evento sul broker bb non modifica lotti di broker incompatibili.

Transfer

Una quantità in transito è eleggibile sul From, non sul To, fino all’arrivo.

Same-day income
BUY D     esclusa
SELL D    inclusa

Crossing

La somma dei costi sulle porzioni chiuse e aperte deve coincidere col costo totale dell’operazione.

Riconciliazione

La somma allocata ai lotti più la parte non allocata deve coincidere con il totale del Portfolio Engine.

23. Risultato a tendere
TRANSAZIONI
BUY · SELL · INCOME · FEE · TAX
          │
          ▼
REPLAY QUANTITATIVO
lotti · frammenti · closure
          │
          ▼
REPLAY ECONOMICO
entitlement · target matching · allocazioni
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
quale transazione è stata attribuita
a quale lotto
con quale regola


Il modello mantiene il cuore FIFO esistente, aggiungendo una seconda dimensione economica deterministica e auditabile, senza modificare le transazioni originarie e senza introdurre compensazioni matematiche ridondanti.
