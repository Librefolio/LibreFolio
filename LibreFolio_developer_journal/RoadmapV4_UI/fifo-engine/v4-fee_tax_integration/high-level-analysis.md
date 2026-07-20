Risposte ai dubbi
1. I punti 1.2 e 1.3 sono conflitti con le nuove regole?

Sì, esattamente.

Punto 1.2 — data di attribuzione dei proventi

Il sistema attuale attribuisce DIVIDEND/INTEREST ai lotti aperti alla data della transazione. La nuova regola è invece:

EligibleQtyi(D)=OpenQtyi(D−1)EligibleQty_i(D)=OpenQty_i(D-1)

Quindi:

BUY nel giorno D
→ non riceve il provento di D

SELL nel giorno D
→ riceve ancora il provento di D


Il sistema corrente va adeguato alla nuova convenzione:

DIVIDEND/INTEREST = inizio giornata
BUY/SELL           = fine giornata

Punto 1.3 — perimetro broker

Anche questo è un conflitto potenziale col comportamento corrente.

La nuova regola deve essere:

stesso asset
+
stesso broker della transazione di provento
+
lotti LONG eleggibili


con l’eccezione esplicita delle quantità in transito:

provento sul broker From → include quantità ancora sul broker e quantità in transito provenienti dal broker;
provento sul broker To → include i frammenti già creati sul broker destinatario.

Questi due punti sono correzioni del comportamento attuale dei proventi, indipendenti dalle FEE/TAX.

2. Chiarimento sul rischio quote_base_quantity

Non vedo un bug attivo negli attuali percorsi di produzione dopo le correzioni fatte. Il rischio è latente e architetturale.

Oggi coesistono due scale:

opening_unit_price
→ prezzo per singola unità nominale

market_price
→ prezzo per quote_base_quantity


Per un’azione:

quote_base_quantity = 1


e le due scale coincidono.

Per un’obbligazione:

quote_base_quantity = 100


e non coincidono.

Esempio:

Quantità nominale      1.000
Prezzo di mercato      98,50 per 100 nominali
Costo per unità         0,985


Valutazione corretta:

OpenValue=1000100⋅98,50=985OpenValue= \frac{1000}{100}\cdot98{,}50 =985

Confronto dei prezzi corretto:

OpeningQuotePrice=OpeningUnitPrice⋅quoteBaseQuantityOpeningQuotePrice= OpeningUnitPrice\cdot quoteBaseQuantity

Il problema è che il motore contiene ancora metodi come:

value_for_lot()
aggregate_value()


che calcolano in modo grezzo:

quantity⋅marketPricequantity\cdot marketPrice

senza conoscere quote_base_quantity.

Il percorso di produzione evita il problema perché il LotsAnalysisService rivaluta con:

compute_holding_value(qty, price, qbq)


Ma un futuro consumer potrebbe chiamare direttamente il metodo grezzo del motore e ottenere valori cento volte errati su un bond.

Correzione post-release consigliata

Non è urgente prima della pubblicazione, ma va irrobustito.

Le alternative, in ordine di preferenza:

rendere obbligatorio quote_base_quantity nei metodi di valutazione del motore;
rinominare chiaramente i metodi:
value_for_lot_qbq_unaware()

marcandoli interni;
rimuoverli se non hanno più consumer reali;
introdurre tipi nominalmente distinti:
UnitPrice
QuotePrice


Aggiungerei comunque un test permanente con qbq=100.

3. L’engine attuale presenta problemi indipendenti dalle FEE/TAX?

Nel complesso, no: non vedo un difetto strutturale che impedisca la release.

Il sottosistema attuale è coerente per:

BUY e SELL FIFO;
LONG e SHORT nei casi supportati;
transfer;
split;
frammenti di custodia;
proventi;
valore stimato al costo;
continuità dopo chiusura;
quote_base_quantity nei percorsi produttivi;
FX e target currency.

Vedo però tre consolidamenti post-release già identificati:

applicare ai proventi la nuova regola D−1D-1;
rendere broker-aware l’allocazione, inclusi i transfer in corso;
proteggere esplicitamente il confine unit price / quote price con qbq.

Quindi la risposta precisa è:

L’attuale motore è sufficientemente solido per la release. Le FEE/TAX introdurranno nuova complessità, ma due modifiche sui proventi e un hardening su qbq sono già desiderabili indipendentemente da esse.

4. Formule minime e feed-forward

Concordo con la tua preferenza: evitare di aggiungere un costo al cost basis per poi sottrarlo nuovamente nel P&L.

La rappresentazione più lineare è conservare accumulatori indipendenti derivati direttamente dalle transazioni:

opening_cost
sale_proceeds
gross_income
fees
taxes
open_value


Da questi derivano una sola volta:

GrossPnL=OpenValue+SaleProceeds+GrossIncome−OpeningCostGrossPnL= OpenValue+ SaleProceeds+ GrossIncome- OpeningCost NetPnL=GrossPnL−Fees−TaxesNetPnL= GrossPnL- Fees- Taxes

Equivalentemente, in forma diretta:

NetPnL=OpenValue+SaleProceeds+GrossIncome−OpeningCost−Fees−TaxesNetPnL= OpenValue+ SaleProceeds+ GrossIncome- OpeningCost- Fees- Taxes

Non serve:

aumentare original_cost;
ricalcolare il prezzo di apertura;
ridurre gli incassi;
sottrarre nuovamente lo stesso costo.

original_cost rimane il costo della transazione di apertura. FEE e TAX rimangono accumulatori separati e auditabili.

Questo è il modello più feed-forward:

transazioni
→ delta sugli accumulatori
→ formule finali
→ DTO
→ barra/grafici

Disegno aggiornato del sottosistema FIFO con FEE/TAX
5. Flusso complessivo
┌──────────────────────────────────────────────────────────────────────┐
│ TRANSAZIONI DB                                                       │
│                                                                      │
│ BUY · SELL · ADJUSTMENT · TRANSFER · SPLIT                          │
│ DIVIDEND · INTEREST · FEE · TAX                                     │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│ LOTS ANALYSIS SERVICE — PREPARAZIONE                                │
│                                                                      │
│ - carica transazioni asset-linked                                   │
│ - carica transfer pair e Asset Event SPLIT                          │
│ - carica prezzi, FX e quote_base_quantity                           │
│ - converte gli importi nella valuta di calcolo                      │
│ - normalizza le transazioni in FifoEvent                            │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│ FIFO LOT ENGINE — REPLAY EVENT-SOURCED                              │
│                                                                      │
│ 1. costruisce lotti e frammenti                                     │
│ 2. produce closure FIFO                                             │
│ 3. assegna proventi                                                 │
│ 4. assegna FEE/TAX                                                  │
│ 5. aggiorna accumulatori economici lordi/netti                      │
│ 6. produce issue sui dati incoerenti                                │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│ LOTS ANALYSIS SERVICE — PRESENTAZIONE                               │
│                                                                      │
│ - valutazione prezzi e qbq                                          │
│ - valore stimato al costo                                           │
│ - history temporali                                                 │
│ - conversione target currency                                       │
│ - Data Quality                                                      │
│ - DTO bulk                                                          │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│ FRONTEND                                                             │
│                                                                      │
│ Timeline · Tabella · Dettaglio lotto                                │
│ Valore lordo/netto · Rendimento lordo/netto                         │
└──────────────────────────────────────────────────────────────────────┘

6. Eventi normalizzati

Il FifoLotEngine deve ricevere anche gli eventi economici:

OPEN_LONG
CLOSE_LONG
OPEN_SHORT
CLOSE_SHORT

ADJUSTMENT_IN
ADJUSTMENT_OUT
TRANSFER_DEPART
TRANSFER_ARRIVE
SPLIT

DIVIDEND
INTEREST
FEE
TAX


Ogni evento economico contiene almeno:

transaction_id
date
type
asset_id
broker_id
amount
currency/calculation_amount
description
related_transaction_id, se presente


Il motore non interpreta fiscalmente la descrizione. La conserva per audit e tooltip.

7. Fasi logiche della giornata

Per non dipendere casualmente dall’ordine degli ID, la giornata viene modellata in fasi.

GIORNO D

FASE 0
Stato risultante dalla chiusura di D-1

FASE 1
DIVIDEND / INTEREST
Titolarità calcolata sulle quantità di inizio giornata

FASE 2
SPLIT / reverse split

FASE 3
BUY / SELL / ADJUSTMENT / TRANSFER

FASE 4
FEE / TAX
Attribuzione ai target economici più plausibili

FASE 5
Snapshot di fine giornata


Lo split resta all’inizio della giornata rispetto alle operazioni quantitative, come già stabilito.

8. Allocazione dei proventi
8.1 Regola ordinaria

Per un provento nel giorno DD, sono eleggibili i lotti LONG risultanti alla fine di D−1D-1:

EligibleQtyi(D)=OpenQtyi(D−1)EligibleQty_i(D)=OpenQty_i(D-1)

e appartenenti al broker dell’accredito.

wi=EligibleQtyi(D)∑jEligibleQtyj(D)w_i= \frac{EligibleQty_i(D)} {\sum_j EligibleQty_j(D)} GrossIncomei=IncomeTotal⋅wiGrossIncome_i= IncomeTotal\cdot w_i
8.2 Transfer in corso
Broker From
├─ frammenti ancora custoditi sul From
└─ frammenti IN_TRANSIT originati dal From

Broker To
└─ frammenti già creati sul To


Provento sul broker From:

EligibleQty=QtyFrom+QtyTransitFromEligibleQty= Qty_{From}+ Qty_{TransitFrom}

Provento sul broker To:

EligibleQty=QtyBrokerToEligibleQty= Qty_{BrokerTo}

Esempio:

Lotto originario       100
Custodia From           40
In transito From→To     60
Custodia To              0


Dividendo su From:

quantità eleggibile = 100


Dopo l’arrivo, dividendo su To:

quantità eleggibile = 60

8.3 Nessun lotto eleggibile
ASSET_INCOME_NO_ELIGIBLE_LOTS


Il motore:

non perde la transazione;
non la attribuisce altrove;
restituisce stato DEGRADED;
genera banner con riferimenti alla transazione.
9. Attribuzione FEE/TAX: scelta del target

Non serve capire se una TAX sia fiscalmente una ritenuta o un’imposta sulla plusvalenza. Serve scegliere l’insieme di lotti interessato.

Regola 1 — collegamento disponibile

Se related_transaction_id identifica un evento:

BUY       → lotto aperto dalla BUY
SELL      → closure/lotti consumati
DIVIDEND  → lotti che hanno ricevuto il provento
INTEREST  → lotti che hanno ricevuto il provento

Regola 2 — stesso giorno

Se non esiste collegamento:

FEE/TAX nello stesso asset, broker e giorno di BUY
→ lotti aperti da quelle BUY

FEE/TAX nello stesso asset, broker e giorno di SELL
→ lotti ridotti/chiusi da quelle SELL

FEE/TAX nello stesso giorno di DIVIDEND/INTEREST
→ lotti destinatari del provento


Se esistono più candidati, l’engine utilizza una priorità deterministica documentata.

Una possibile priorità iniziale:

evento esplicitamente collegato
→ operazione immediatamente vicina nell’ordine
→ SELL closure
→ BUY opening
→ income allocation
→ lotti aperti generici


La priorità effettiva va testata sui dati BRIM prima di essere congelata.

Regola 3 — finestra temporale breve

Se non esiste candidato nel giorno della FEE/TAX:

cerca eventi compatibili in D-1 e D+1


con vincoli:

stesso asset;
stesso broker;
distanza minima;
tipo di evento economicamente utilizzabile.

Regola 4 — fallback

Se non esiste un evento candidato:

FEE/TAX asset-linked
→ lotti LONG aperti a inizio giornata
   sullo stesso asset e broker.


Se non esistono:

ASSET_COST_NO_ELIGIBLE_LOTS

10. Ripartizione del costo sul target
10.1 Target BUY

Se una FEE/TAX è attribuita a una o più BUY:

wi=OpeningValuei∑jOpeningValuejw_i= \frac{OpeningValue_i} {\sum_j OpeningValue_j} AllocatedCosti=CostTotal⋅wiAllocatedCost_i= CostTotal\cdot w_i

Con una sola BUY:

100% al lotto creato.

10.2 Target SELL

Se una SELL consuma più lotti:

wi=ClosedQuantityi∑jClosedQuantityjw_i= \frac{ClosedQuantity_i} {\sum_j ClosedQuantity_j} AllocatedCosti=CostTotal⋅wiAllocatedCost_i= CostTotal\cdot w_i

Questo evita di dover determinare se il costo sia fee o tax.

10.3 Target income

Se la FEE/TAX viene associata a DIVIDEND/INTEREST, riutilizza gli stessi pesi del provento:

AllocatedCosti=CostTotal⋅IncomeWeightiAllocatedCost_i= CostTotal\cdot IncomeWeight_i
10.4 Target lotti aperti

Nel fallback generico:

wi=OpenQtyi∑jOpenQtyjw_i= \frac{OpenQty_i} {\sum_j OpenQty_j} AllocatedCosti=CostTotal⋅wiAllocatedCost_i= CostTotal\cdot w_i

In tutti i casi:

∑iAllocatedCosti=CostTotal\sum_i AllocatedCost_i=CostTotal

con residuo assegnato deterministicamente.

11. Accumulatori del lotto

Ogni lotto mantiene grandezze derivate runtime:

original_cost
sale_proceeds
gross_income

allocated_fees
allocated_taxes

open_value


Breakdown opzionale per origine:

opening_fees
closing_fees
income_fees
holding_fees

opening_taxes
closing_taxes
income_taxes
holding_taxes


Il breakdown non cambia la formula; serve soltanto per audit e tooltip.

12. Formule feed-forward
12.1 P&L lordo
GrossPnLi(t)=OpenValuei(t)+SaleProceedsi(t)+GrossIncomei(t)−OriginalCostiGrossPnL_i(t)= OpenValue_i(t)+ SaleProceeds_i(t)+ GrossIncome_i(t)- OriginalCost_i
12.2 Costi totali
Costsi(t)=Feesi(t)+Taxesi(t)Costs_i(t)= Fees_i(t)+Taxes_i(t)
12.3 P&L netto
NetPnLi(t)=GrossPnLi(t)−Costsi(t)NetPnL_i(t)= GrossPnL_i(t)-Costs_i(t)

oppure direttamente:

NetPnLi(t)=OpenValuei(t)+SaleProceedsi(t)+GrossIncomei(t)−OriginalCosti−Feesi(t)−Taxesi(t)NetPnL_i(t)= OpenValue_i(t)+ SaleProceeds_i(t)+ GrossIncome_i(t)- OriginalCost_i- Fees_i(t)- Taxes_i(t)
12.4 Rendimento lordo
GrossReturni(t)=GrossPnLi(t)OriginalCostiGrossReturn_i(t)= \frac{GrossPnL_i(t)} {OriginalCost_i}
12.5 Rendimento netto
NetReturni(t)=NetPnLi(t)OriginalCostiNetReturn_i(t)= \frac{NetPnL_i(t)} {OriginalCost_i}

Nella prima implementazione original_cost resta invariato. Non viene aumentato con la fee BUY e la stessa fee non viene quindi aggiunta e sottratta in passaggi diversi.

13. Aggiornamento temporale feed-forward

Ogni evento produce soltanto delta sugli accumulatori.

BUY
→ original_cost += buy amount
→ open_quantity += quantity

SELL
→ sale_proceeds += proceeds allocati
→ open_quantity -= quantity
→ realized quantity aggiornata

DIVIDEND / INTEREST
→ gross_income += allocazione

FEE
→ allocated_fees += allocazione

TAX
→ allocated_taxes += allocazione

PRICE
→ open_value = quantità aperta × prezzo

TRANSFER
→ cambia custodia
→ nessun delta economico

SPLIT
→ cambia quantità/prezzo unitario
→ nessun delta di costo


Il risultato visualizzato è sempre derivato dagli accumulatori correnti, senza compensazioni inverse.

14. Output del motore

Il FifoEngineResult deve esporre per lotto almeno:

gross_income
allocated_fees
allocated_taxes
gross_pnl
net_pnl
gross_return
net_return


e possibilmente una lista di allocazioni auditabili:

CostAllocation
- transaction_id
- lot_id
- event_date
- cost_type: FEE | TAX
- allocation_context: OPENING | CLOSURE | INCOME | HOLDING
- amount
- allocation_rule


allocation_rule può contenere:

EXPLICIT_LINK
SAME_DAY_BUY
SAME_DAY_SELL
SAME_DAY_INCOME
ADJACENT_DAY
OPEN_LOTS_FALLBACK


Questo permette di documentare le assunzioni senza modificare le transazioni originali.

15. Ruolo finale dei componenti
LotsAnalysisService
│
├─ carica DB
├─ risolve FX
├─ prepara eventi normalizzati
└─ chiama il motore
        │
        ▼
FifoLotEngine
│
├─ lotti e closure
├─ transfer e split
├─ income entitlement
├─ FEE/TAX target matching
├─ ripartizione costi
├─ accumulatori lordi/netti
└─ issue e allocation audit
        │
        ▼
LotsAnalysisService
│
├─ prezzi e qbq
├─ history temporali
├─ estimated-at-cost
├─ target currency
└─ DTO
        │
        ▼
Frontend
│
├─ Lordo / Netto
├─ P&L
├─ Return
├─ Proventi
├─ FEE
└─ TAX


Questa struttura mantiene il FifoLotEngine titolare della semantica dei lotti, mentre il service resta responsabile dell’I/O e della preparazione monetaria.
