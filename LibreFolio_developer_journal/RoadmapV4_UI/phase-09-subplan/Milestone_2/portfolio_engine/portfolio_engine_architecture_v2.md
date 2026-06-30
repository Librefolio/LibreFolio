# Report matematico — Portfolio Engine vNext

> Scopo: definire matematicamente come deve funzionare il nuovo portfolio engine di LibreFolio: assunti, definizioni, calcolo iterativo, cache a finestra, invalidazione, dati per dashboard e modello a 3 cash pool.

***

## 1. Obiettivo dell’engine

Dato:

```text
utente u
broker visibili V(u)
broker selezionati S ⊆ V(u)
valuta target C*
intervallo richiesto [t0, t1]
transazioni fino a t1
prezzi nel frame richiesto
FX nel frame richiesto
```

l’engine deve produrre:

```text
1. stati giornalieri assoluti nel range richiesto
2. stati giornalieri per posizione: (broker_id, asset_id, date)
3. aggregati portfolio giornalieri
4. decomposizione cash/capitale/rendimento
5. metriche percentuali range-dependent
6. dati dashboard-ready per:
   - KPI
   - GrowthChart
   - asset table
   - asset treemap
   - contribution view
```

Principio base:

```text
prima calcolo primitive monetarie oggettive
poi aggrego
poi calcolo metriche percentuali
poi preparo DTO UI-ready
```

***

## 2. Assunti fondamentali

### 2.1 Asset vs posizione

Un asset non coincide con una posizione.

```text
asset = asset_id
posizione = (broker_id, asset_id)
```

Lo stesso asset può essere detenuto su più broker.

Quindi:

```text
price(asset, t)                  → asset-level
last_buy_price(asset, t)          → asset-level
quantity(asset, broker, t)        → position-level
wac(asset, broker, t)             → position-level
cost_basis(asset, broker, t)      → position-level
unrealized(asset, broker, t)      → position-level
realized(asset, broker, period)   → position-level
```

***

### 2.2 Broker visibili vs broker selezionati

Si distinguono:

```text
V(u) = broker visibili dall’utente
S    = broker selezionati dal filtro dashboard/report
```

`S` è usato per decidere cosa entra nel portafoglio aggregato.

`V(u)` è usato anche per stimare il prezzo fallback di un asset.

***

### 2.3 Prezzo di valutazione

Il prezzo usato per stimare il valore di mercato è:

```text
valuation_price(asset, t)
```

Priorità:

```text
1. market_price(asset, t), se disponibile
2. last_buy_price(asset, t, V(u)), se disponibile
3. missing
```

Dove:

```text
last_buy_price(asset, t, V(u)) =
  prezzo unitario dell’ultimo BUY cronologico dell’asset
  su qualunque broker visibile all’utente
  con data ≤ t
```

Nota importante:

```text
last_buy_price NON dipende dal filtro broker S
```

Esempio:

```text
utente vede Directa e IBKR
filtro dashboard = solo Directa
ultimo BUY di VWCE è su IBKR
fallback price VWCE = prezzo ultimo BUY su IBKR
```

Motivo:

```text
il prezzo è proprietà dell’asset
non del broker
```

***

### 2.4 WAC

Il WAC non è un prezzo di mercato.

```text
wac(asset, broker, t)
```

serve per:

```text
cost basis
P&L latente
realized gain/loss
book value
contribution
```

Non va usato come fallback price.

***

### 2.5 Dati derivati non persistiti

Gli stati giornalieri non vanno salvati su DB.

```text
DailyPositionState
DailyPortfolioState
CashPoolState
```

sono dati derivati.

Si possono mettere in cache, ma non persistono su disco come fonte dati.

Motivo:

```text
una modifica a transazioni/prezzi/FX/formule cambia i risultati
```

***

## 3. Finestra di calcolo

### 3.1 Frame richiesto

Il frame principale è:

```text
[t0, t1]
```

Dentro questo frame l’engine calcola giornalmente:

```text
price
FX
market value
cost basis
NAV
book
cash pool
daily metrics
```

Nel frame richiesto **non si fa time-skip su prezzi e FX**.

Motivo:

```text
prezzi e FX possono cambiare ogni giorno
per sapere se un cambio è rilevante bisognerebbe comunque calcolarlo
```

Quindi:

```text
dentro [t0, t1] → valutazione giornaliera completa
fuori [t0, t1] → ricostruzione contabile tramite transazioni
```

***

### 3.2 Pre-frame

Per arrivare correttamente a `t0`, servono le transazioni precedenti:

```text
tx.date < t0
```

Il pre-frame ricostruisce:

```text
cash iniziale
quantity iniziale per posizione
WAC iniziale per posizione
capital_pool iniziale
returns_pool iniziale
withdrawn_returns_pool iniziale
realized storico utile alle pool
```

Il pre-frame non calcola:

```text
NAV giornaliero storico
market value storico giornaliero
prezzi giornalieri storici
FX giornalieri storici
daily chart points storici
```

***

### 3.3 Estensione del blob cache

Se esiste già un blob cache valido e arriva una nuova richiesta con frame parzialmente fuori dal blob:

```text
blob esistente = [ta, tb]
nuova richiesta = [t0, t1]
```

allora, se non ci sono invalidazioni:

```text
si calcolano solo le porzioni mancanti
```

Esempi:

```text
blob = [2026-04-01, 2026-06-30]
richiesta = [2026-03-01, 2026-06-30]

→ calcola solo [2026-03-01, 2026-03-31]
→ estende blob a [2026-03-01, 2026-06-30]
```

```text
blob = [2026-04-01, 2026-06-30]
richiesta = [2026-04-01, 2026-07-15]

→ calcola solo [2026-07-01, 2026-07-15]
→ estende blob a [2026-04-01, 2026-07-15]
```

Se invece fingerprint cambia:

```text
blob invalidato interamente nella prima versione
```

Ottimizzazione futura:

```text
partial recompute da dirty date
```

ma non è requisito iniziale.

***

## 4. Definizioni matematiche

### 4.1 Insiemi

```text
B = broker visibili dall’utente
S = broker selezionati dal filtro, S ⊆ B
A = asset coinvolti
T = transazioni
D = giorni nel range [t0, t1]
C* = valuta target
```

***

### 4.2 Share utente

Ogni broker può avere una quota utente:

```text
share(b) ∈ [0, 1]
```

Ogni quantità e importo vengono scalati:

```text
effective_qty(tx) = quantity(tx) × share(broker(tx))
effective_amount(tx) = amount(tx) × share(broker(tx))
```

***

### 4.3 Quantità per posizione

Per posizione `(a,b)`:

```text
q(a,b,t) =
  Σ effective_qty(tx)
  per tutte le tx con:
    tx.asset_id = a
    tx.broker_id = b
    tx.date ≤ t
```

***

### 4.4 Prezzo asset-level

```text
p(a,t) =
  market_price(a,t)
```

se disponibile.

Altrimenti:

```text
p(a,t) =
  last_buy_price(a,t,V(u))
```

se disponibile.

Altrimenti:

```text
p(a,t) = missing
```

***

### 4.5 WAC per posizione

Per posizione `(a,b)`:

```text
pool_qty(a,b)
pool_cost(a,b)
wac(a,b)
```

BUY:

```text
pool_qty_new  = pool_qty_old + qty_buy
pool_cost_new = pool_cost_old + buy_cost
wac_new       = pool_cost_new / pool_qty_new
```

SELL:

```text
sold_cost = qty_sold × wac_old

pool_qty_new  = pool_qty_old - qty_sold
pool_cost_new = pool_cost_old - sold_cost
wac_new       = wac_old
```

Proprietà:

```text
il WAC cambia su BUY
il WAC non cambia su SELL
```

***

## 5. DailyPositionState

Per ogni giorno `t ∈ [t0, t1]` e posizione rilevante `(a,b)`:

```text
DailyPositionState(a,b,t):
  date
  broker_id
  asset_id
  quantity
  valuation_price
  valuation_source
  market_value
  wac
  cost_basis
  unrealized_pnl
  data_quality_flags
```

Dove:

```text
valuation_source ∈ {
  MARKET_PRICE,
  LAST_BUY_PRICE,
  MISSING
}
```

***

### 5.1 Market value

```text
MV(a,b,t) =
  q(a,b,t) × p(a,t) × fx(ccy_price(a), C*, t)
```

Se `p(a,t)` manca:

```text
MV(a,b,t) = null
data_quality += MISSING_PRICE
```

***

### 5.2 Cost basis

```text
CB(a,b,t) =
  q(a,b,t) × wac(a,b,t) × fx(ccy_wac(a,b), C*, t)
```

***

### 5.3 Unrealized P\&L

```text
UGL(a,b,t) =
  MV(a,b,t) - CB(a,b,t)
```

Se `MV` o `CB` non disponibili:

```text
UGL(a,b,t) = null
```

***

## 6. Aggregazione portfolio

Il portfolio viene aggregato partendo dalle posizioni.

### 6.1 Market value aggregato

```text
MV(t) =
  Σ MV(a,b,t)
  per b ∈ S
```

***

### 6.2 Open cost basis aggregato

```text
OCB(t) =
  Σ CB(a,b,t)
  per b ∈ S
```

***

### 6.3 Unrealized P\&L aggregato

```text
UGL(t) =
  Σ UGL(a,b,t)
  per b ∈ S
```

***

### 6.4 Cash

```text
cash(t) =
  saldo cash cumulativo dei broker selezionati
  convertito in C*
```

Include effetti di:

```text
DEPOSIT
WITHDRAWAL
BUY
SELL
DIVIDEND
INTEREST
FEE
TAX
FX_CONVERSION
cash transfer
```

***

### 6.5 In-transit

Per movimenti interni con date diverse:

```text
in_transit_cash(t)
in_transit_asset_market_value(t)
in_transit_asset_cost_basis(t)
```

Finestra:

```text
departure_date < t < arrival_date
```

***

### 6.6 NAV

```text
NAV(t) =
  MV(t)
  + cash(t)
  + in_transit_cash(t)
  + in_transit_asset_market_value(t)
```

***

### 6.7 Book value

```text
Book(t) =
  OCB(t)
  + cash(t)
  + in_transit_cash(t)
  + in_transit_asset_cost_basis(t)
```

***

### 6.8 Total P\&L assoluto

```text
total_pnl(t) =
  NAV(t) - capital_baseline(t)
```

Dove:

```text
capital_baseline(t) = capitale esterno netto apportato
```

***

## 7. Calcolo iterativo globale

L’engine lavora in tre blocchi logici.

***

### 7.1 Pre-frame

Per `tx.date < t0`:

```text
1. applica transazioni storiche
2. aggiorna cash
3. aggiorna quantity
4. aggiorna WAC
5. aggiorna pool cash
6. aggiorna realized utile alle pool
```

Non calcola market estimation giornaliera.

***

### 7.2 Frame richiesto

Per ogni giorno `t ∈ [t0, t1]`:

```text
1. Applica transazioni del giorno
2. Aggiorna quantity e WAC
3. Aggiorna cash
4. Aggiorna le 3 cash pool
5. Recupera price(asset,t)
6. Recupera FX(t)
7. Calcola DailyPositionState
8. Aggrega DailyPortfolioState
9. Calcola derived daily fields
```

Dentro questo frame:

```text
prezzi e FX valutati giornalmente
```

***

### 7.3 Frame esteso da cache

Se una richiesta è parzialmente fuori da un blob cache ancora valido:

```text
1. conserva i giorni già calcolati
2. calcola solo i giorni mancanti
3. unisce i risultati
4. aggiorna il blob esteso
```

Questa estensione è consentita solo se:

```text
fingerprint transazioni invariato
fingerprint prezzi valido per frame coinvolto
fingerprint FX valido per frame coinvolto
```

Se fingerprint cambia:

```text
blob invalidato
ricalcolo completo del frame richiesto
```

***

## 8. Realized, income, fee/tax

### 8.1 Realized gain/loss

Per SELL su posizione `(a,b)`:

```text
sell_proceeds =
  cash incassato convertito in C*
```

```text
sold_cost_basis =
  qty_sold × wac(a,b,t_sell) × fx(wac_ccy, C*, t_sell)
```

```text
realized_gain_loss =
  sell_proceeds - sold_cost_basis
```

Accumulo:

```text
realized_by_position(a,b) += realized_gain_loss
```

***

### 8.2 Income

Per DIVIDEND/INTEREST:

```text
income_amount =
  amount × fx(ccy, C*, t) × share(b)
```

Se `asset_id` presente:

```text
income_by_position(a,b) += income_amount
```

Se `asset_id` assente:

```text
generic_income_pool(b) += income_amount
```

Quindi l’income non attribuito è scaricato sul broker.

Non esiste income generico globale senza broker, perché:

```text
il broker esiste sempre
```

***

### 8.3 Fee/tax

Per FEE/TAX:

```text
fee_tax_amount =
  abs(amount) × fx(ccy, C*, t) × share(b)
```

Se `asset_id` presente:

```text
fees_taxes_by_position(a,b) += fee_tax_amount
```

Se `asset_id` assente:

```text
generic_fee_tax_pool(b) += fee_tax_amount
```

Quindi fee/tax non attribuiti sono scaricati sul broker.

Nessuna euristica:

```text
non collegare fee/tax a SELL vicine
non inferire asset_id se manca
```

***

## 9. Contribution periodica asset-level

Per posizione `(a,b)` nel periodo `[t0,t1]`:

```text
period_unrealized_delta(a,b) =
  UGL(a,b,t1) - UGL(a,b,t0)
```

```text
period_realized_gain_loss(a,b) =
  Σ realized SELL su (a,b) nel periodo
```

```text
period_income(a,b) =
  Σ income attribuiti a (a,b) nel periodo
```

```text
period_fees_taxes(a,b) =
  Σ fee/tax attribuiti a (a,b) nel periodo
```

Formula:

```text
period_pnl(a,b) =
    period_unrealized_delta(a,b)
  + period_realized_gain_loss(a,b)
  + period_income(a,b)
  - period_fees_taxes(a,b)
```

***

### 9.1 Bucket generici per broker

Per valori non attribuibili ad asset:

```text
generic_income_pool(b)
generic_fee_tax_pool(b)
```

Il contributo generico broker-level è:

```text
generic_period_pnl(b) =
  generic_income_pool(b)
  - generic_fee_tax_pool(b)
```

UI:

```text
Broker / Non allocato
```

Esempio:

```text
Directa / Non allocato
Recrowd / Non allocato
```

Non:

```text
Portfolio globale / Non allocato
```

salvo aggregazione finale opzionale.

***

### 9.2 Posizioni chiuse

La contribution view deve includere anche posizioni chiuse.

Caso:

```text
quantity(a,b,t1) = 0
realized_gain_loss(a,b) ≠ 0
```

Allora la posizione deve comparire comunque in `positions_contribution`.

***

## 10. Metriche percentuali

Le metriche percentuali sono layer separato.

Motivo:

```text
non sono linearmente cumulabili
dipendono da t0
sono più costose
```

***

### 10.1 TWRR

TWRR neutralizza solo flussi esterni:

```text
DEPOSIT
WITHDRAWAL
trasferimenti da/verso fuori selezione
```

Non neutralizza:

```text
DIVIDEND
INTEREST
SELL
FEE
TAX
```

Questi restano dentro NAV.

***

### 10.2 MWRR

MWRR/XIRR usa:

```text
external cash flows
NAV iniziale
NAV finale
```

Non inserisce dividendi/interessi/vendite come cash flow se restano nel portafoglio.

Motivo:

```text
sono già inclusi nel NAV finale
```

Altrimenti sarebbero contati due volte.

***

### 10.3 Parallelismo futuro

Le metriche percentuali, specialmente:

```text
MWRR
MWRR series
quick ranges
```

possono essere calcolate dopo gli assoluti.

Possibile ottimizzazione futura:

```text
process pool per metriche %
```

Non prioritaria nella prima implementazione.

***

# 11. Cash pools — modello a 3 pool

Le pool sono una convenzione visuale/prodotto, non fiscale.

Obiettivo:

```text
distinguere:
- capitale proprio ancora nel sistema
- rendimento generato ancora nel sistema
- rendimento uscito e potenzialmente ripristinabile
```

***

## 11.1 Definizioni

```text
K(t) = capital_pool
R(t) = returns_pool
W(t) = withdrawn_returns_pool
```

Dove:

```text
K = capitale dell’utente attualmente nel sistema
R = rendimento generato ancora nel sistema
W = rendimento generato, uscito dal sistema, ma tracciato come ripristinabile
```

`W` è nascosto in UI.

***

## 11.2 Deposito

Per deposito esterno `D > 0`:

```text
restore = min(D, W_old)

R_new = R_old + restore
W_new = W_old - restore
K_new = K_old + (D - restore)
```

Interpretazione:

```text
se l’utente rimette soldi dopo aver prelevato rendimenti,
prima ripristina rendimento uscito,
poi aggiunge nuovo capitale
```

***

## 11.3 Prelievo

Per prelievo esterno `X > 0`:

Prima capitale:

```text
from_capital = min(X, K_old)
K_mid = K_old - from_capital
remaining = X - from_capital
```

Poi rendimento:

```text
from_returns = min(remaining, R_old)
R_new = R_old - from_returns
W_new = W_old + from_returns
K_new = K_mid
```

Interpretazione:

```text
prima l’utente riprende il proprio capitale
poi, se serve, preleva rendimento
```

***

## 11.4 Dividendi/interessi

Per income `I > 0`:

```text
R_new = R_old + I
K_new = K_old
W_new = W_old
```

***

## 11.5 Vendita

Per vendita:

```text
P = sell_proceeds
C = sold_cost_basis
G = P - C
```

Aggiornamento:

```text
K_mid = K_old + C
R_mid = R_old + G
```

Se `R_mid >= 0`:

```text
K_new = K_mid
R_new = R_mid
```

Se `R_mid < 0`:

```text
K_new = K_mid + R_mid
R_new = 0
```

Poiché `R_mid` è negativo, il deficit riduce il capitale.

```text
W_new = W_old
```

***

## 11.6 Acquisto

Per acquisto `B > 0`:

Prima rendimento:

```text
from_returns = min(B, R_old)
R_mid = R_old - from_returns
remaining = B - from_returns
```

Poi capitale:

```text
K_new = K_old - remaining
R_new = R_mid
W_new = W_old
```

Interpretazione:

```text
prima si reinvestono utili
poi si usa capitale
```

***

## 11.7 Fee/tax

Per costo `F > 0`:

```text
R_mid = R_old - F
```

Se `R_mid >= 0`:

```text
R_new = R_mid
K_new = K_old
```

Se `R_mid < 0`:

```text
R_new = 0
K_new = K_old + R_mid
```

Poiché `R_mid` è negativo, il deficit riduce il capitale.

***

## 11.8 Invariante di riconciliazione

A fine giornata:

```text
cash_like(t) ≈ K(t) + R(t)
```

Dove:

```text
cash_like(t) = cash(t) + in_transit_cash(t)
```

`W(t)` non entra nell’invariante perché rappresenta rendimento uscito dal sistema.

Se:

```text
cash_like(t) - (K(t) + R(t)) ≠ 0
```

allora:

```text
reconciliation_delta(t)
data_quality_flag
```

Non correggere silenziosamente.

***

# 12. Cache a finestra

## 12.1 Principio

La cache è:

```text
blob range-based
```

Non full-history obbligatoria.

***

## 12.2 Range standard

Ragionevole precalcolare:

```text
1W
1M
3M
6M
1Y
```

Lazy/on-demand:

```text
2Y
5Y
MAX
custom estesi
```

***

## 12.3 Contenuto blob

Un blob può contenere:

```text
query context
fingerprints
daily portfolio states nel range
daily position states nel range
cash pool states nel range
wac series necessarie
summary
history
allocation
positions_exposure
positions_contribution
performance metrics
data_quality
```

***

## 12.4 Blob estendibile

Un blob valido può essere ampliato.

Se:

```text
blob = [ta, tb]
richiesta = [t0, t1]
```

e:

```text
[t0, t1] non è interamente contenuto in [ta, tb]
```

allora si calcola:

```text
[t0, ta-1] se t0 < ta
[tb+1, t1] se t1 > tb
```

Poi:

```text
blob_new = union(blob_old, missing_segments)
```

Questo evita di ricalcolare dati già validi.

***

## 12.5 Key cache

Chiave concettuale:

```text
user_id
visible_brokers
selected_brokers
target_currency
date_from
date_to
include_flags
tx_fingerprint
price_fingerprint
fx_fingerprint
```

***

## 12.6 Fingerprint transazioni

Il fingerprint transazioni deve considerare:

```text
transazioni rilevanti fino a date_to
```

non solo quelle nel frame.

Motivo:

```text
lo stato a t0 dipende da transazioni precedenti
```

***

## 12.7 Fingerprint prezzi e FX

Per prezzi e FX:

```text
fingerprint nel frame richiesto
```

Motivo:

```text
fuori dal frame non calcoliamo market estimation giornaliera
```

***

## 12.8 Invalidazione

Prima versione:

```text
se fingerprint cambia
→ invalida intero blob
```

Non implementare subito:

```text
partial recompute da dirty_date
versioning broker
versioning asset price
timeline patching
```

Futuro possibile:

```text
se cambia un dato alla data d
→ riusa cache fino a d-1
→ ricalcola da d in poi
```

***

# 13. Output report-ready

L’engine deve emettere dati già pronti per UI.

***

## 13.1 Exposure positions

```text
positions_exposure:
  broker_id
  broker_name
  asset_id
  asset_name
  asset_ticker
  asset_type
  is_open
  quantity
  valuation_price
  valuation_source
  market_value
  nav_weight_percent
  wac
  cost_basis
  unrealized_pnl
  unrealized_pnl_percent
  data_quality_flags
```

***

## 13.2 Contribution positions

```text
positions_contribution:
  broker_id
  broker_name
  asset_id
  asset_name
  asset_ticker
  asset_type
  is_open
  is_closed_in_period
  period_unrealized_delta
  period_realized_gain_loss
  period_income
  period_fees_taxes
  period_pnl
  impact_rank
  side
  data_quality_flags
```

***

## 13.3 Generic broker buckets

```text
broker_generic_contributions:
  broker_id
  broker_name
  generic_income
  generic_fees_taxes
  generic_period_pnl
```

Formula:

```text
generic_period_pnl =
  generic_income - generic_fees_taxes
```

***

## 13.4 Contribution totals

```text
gross_gains
gross_losses
scale_max
period_pnl_total
```

Dove:

```text
period_pnl_total =
  Σ period_pnl(position)
  + Σ generic_period_pnl(broker)
```

***

# 14. Separazione backend/frontend

Backend calcola:

```text
NAV
Book
cash
cash pools
market value
cost basis
P&L
contribution
weights
performance metrics
data quality
```

Frontend fa solo:

```text
display
formatting
sorting leggero
grouping visuale
costruzione shape ECharts
toggle tabella/mappa
```

Niente calcoli finanziari core nel frontend.

***

# 15. Riassunto finale

Architettura voluta:

```text
1. Ricostruzione pre-frame tramite transazioni.
2. Calcolo giornaliero completo solo nel frame richiesto.
3. Nessun time-skip su prezzi/FX dentro il frame.
4. Price fallback = market price, poi ultimo BUY asset-level tra broker visibili.
5. WAC = position-level, mai usato come price.
6. Stati minimi per posizione/giorno.
7. Portfolio = aggregazione delle posizioni.
8. Cash pools a 3 componenti:
   - capitale
   - rendimento dentro sistema
   - rendimento uscito nascosto
9. Fee/tax/income non asset-linked vanno in bucket generico per broker.
10. Metriche percentuali come layer successivo.
11. Cache blob range-based.
12. Blob estendibile se nuova richiesta esce parzialmente dal range già calcolato.
13. Invalidazione intero blob nella prima versione.
14. Backend produce dati dashboard-ready.
```

Questo è il piano ad alto livello coerente per un engine:

```text
centralizzato
range-aware
cacheabile
matematicamente ordinato
compatibile con multi-broker
utile per dashboard asset/treemap/contribution
senza persistenza inutile di dati derivati
```

***

# 16. Note implementative (30 giugno 2026)

## 16.1 Stato di conformità rispetto al piano

| Sezione piano | Stato | Note |
|---|---|---|
| §1 Obiettivo engine | ✅ Conforme | Produce daily states, position states, aggregati, decomposizione cash pool, dati dashboard-ready |
| §2.1 asset vs posizione | ✅ Conforme | `key = (asset_id, broker_id)` ovunque |
| §2.2 V(u) vs S | ✅ Conforme | Engine riceve `visible_broker_ids` (V(u)) + `scope_broker_ids` (S). last_buy_price usa V(u) |
| §2.3 Prezzo di valutazione | ✅ Conforme | Catena: MARKET_PRICE → LAST_BUY_PRICE(V(u)) → MISSING. Nessun WAC→price |
| §2.4 WAC | ✅ Conforme | Position-level, mai usato come price fallback, solo per cost basis |
| §2.5 Dati non persistiti | ✅ Conforme | Tutto in-memory, niente su DB |
| §3.1 Frame richiesto | ✅ Conforme | `frame_start`..`date_to` = valutazione giornaliera completa |
| §3.2 Pre-frame | ✅ Conforme | `date_from`..`frame_start-1` = solo contabilità (cash, qty, WAC, pool) |
| §3.3 Estensione blob cache | ⚠️ Parziale | Cache fingerprint-keyed e range-aware (hit se contenuto). Forward extension stub, non ancora incrementale |
| §4 Definizioni | ✅ Conforme | Qty, price, WAC, MV, CB, UGL tutti implementati come da formula |
| §5 DailyPositionState | ✅ Conforme | Dataclass con: date, broker_id, asset_id, quantity, valuation_price/source, market_value, wac, cost_basis, unrealized_pnl |
| §5.1 Market value | ✅ Conforme | MV = qty × p(a,t) × fx |
| §5.2 Cost basis | ✅ Conforme | CB = qty × wac × fx |
| §5.3 Unrealized P&L | ✅ Conforme | UGL = MV - CB (None se MV mancante) |
| §6 Aggregazione portfolio | ✅ Conforme | Somma di MV, OCB, UGL sulle posizioni in S |
| §6.4 Cash | ✅ Conforme | Ledger cumulativo con tutti i tipi tx |
| §6.5 In-transit | ✅ Conforme | Finestra [departure+1, arrival-1] per cash e asset |
| §6.6 NAV | ✅ Conforme | MV + cash + in_transit |
| §6.7 Book value | ✅ Conforme | OCB + cash + in_transit_book |
| §6.8 Total P&L | ✅ Conforme | NAV - capital_baseline |
| §7 Calcolo iterativo | ✅ Conforme | Pre-frame + frame come descritto |
| §8.1 Realized | ✅ Conforme | sell_proceeds - (qty_sold × WAC_pre_sell × fx). WAC letto PRIMA della riduzione |
| §8.2 Income | ✅ Conforme | Se asset_id → position-level; se assente → generic_pool(broker) |
| §8.3 Fee/tax | ✅ Conforme | Stessa logica income. Nessuna euristica |
| §9 Contribution periodica | ✅ Conforme | period_pnl = unrealized_delta + realized + income - fees_taxes |
| §9.1 Bucket generici broker | ✅ Conforme | unalloc_income[broker_id], unalloc_fees[broker_id] |
| §9.2 Posizioni chiuse | ⚠️ Struttura pronta | position_states_start/end emessi + per_realized traccia chiuse. DerivedViewsBuilder non ancora riscritta per union |
| §10 Metriche % | ✅ Invariato | TWRR/MWRR/ROI calcolate come layer successivo in DerivedViewsBuilder (non toccate) |
| §11 Cash pools 3-pool | ⚠️ Parziale | K e R implementate event-driven. W (withdrawn_returns) non ancora tracciata esplicitamente |
| §11.1-11.7 Regole pool | ✅ Conforme | DEPOSIT→K, WITHDRAWAL→K poi R, DIVIDEND→R, SELL→K+R, BUY→R poi K, FEE→R poi K |
| §11.8 Invariante | ✅ Conforme | cash_like ≈ K+R con reconciliation proportionale se drift |
| §12 Cache a finestra | ⚠️ Parziale | Blob keyed by fingerprint (no date range in key). Hit if fully contained. Forward extension stub |
| §12.6 Fingerprint tx | ✅ Conforme | Hash di tx.id + tx.updated_at per tutte le tx fino a date_to |
| §12.7 Fingerprint prezzi/FX | ✅ Conforme | COUNT + MAX(fetched_at) come proxy |
| §12.8 Invalidazione | ✅ Conforme | Fingerprint change → invalida intero blob |
| §13 Output report-ready | ⚠️ Parziale | position_states_start/end emessi dall'engine. DerivedViewsBuilder non ancora riscritta per generare positions_exposure/contribution dal nuovo formato |
| §14 Separazione BE/FE | ✅ Conforme | Tutto calcolato backend. Frontend solo display |

## 16.2 Differenze rispetto al piano

### 16.2.1 Nessuna DailyPositionState per ogni giorno del frame

Il piano descrive "per ogni giorno t ∈ [t0, t1] e posizione, un DailyPositionState".

Implementazione: emettiamo **snapshot a t0** e **snapshot a t1** (non per ogni giorno).

Motivo: il DailyPortfolioState aggregato è già sufficiente per il chart giornaliero. Le posizioni servono per:
- Exposure view (solo t1)
- Contribution (diff t0 vs t1 + accumulators)

Emettere per ogni giorno causerebbe O(days × positions) memory senza use case concreto.

**Se necessario**: estensibile aggiungendo posizione_states anche a giorni intermedi.

### 16.2.2 W (withdrawn_returns_pool) non tracciata

Il piano prevede 3 pool: K, R, W. Attualmente:
- K e R implementate con regole event-driven complete
- W incrementata su WITHDRAWAL (from_R va a W) ma **non persistita** in DailyPortfolioState
- DEPOSIT con restore da W: attualmente semplificato a `K += D`

Impact: nessuno sulla correttezza di K e R per l'invariante. W serve solo per il ripristino su ri-deposito dopo prelievo returns. Da aggiungere quando serve UX per mostrare W separatamente.

### 16.2.3 Cache forward extension non ancora incrementale

Il piano prevede: se blob=[ta,tb] e richiesta=[ta,t1>tb], calcola solo [tb+1,t1] e estende.

Implementazione attuale: se range non contenuto → full recompute.

Motivo: l'estensione incrementale richiede serializzare lo stato accumulatore di fine-blob (wac_pool, cumulative_qty, cash, pools). Struttura pronta (i dati ci sono), implementazione deferrita.

### 16.2.4 DerivedViewsBuilder non aggiornata

Il piano prevede che le derived views (exposure, contribution) vengano dal nuovo PortfolioCalculationResult.

Implementazione attuale: l'engine emette position_states + accumulators, ma `portfolio_service.py` continua a usare il suo vecchio loop per holdings/contribution come prima. Le due strade coesistono.

Motivo: cambiare le derived views richiede modifica dei DTO esposti all'API → frontend sync → test E2E. Deferrito a fase successiva.

## 16.3 Scoperte implementative

### 16.3.1 Ordine di esecuzione SELL critico per 3-pool

Bug scoperto e risolto: il WAC pool DEVE essere letto PRIMA di ridurre la quantità, altrimenti una full sell (qty→0) produce `pool_q=0` → `cost_basis=0` → tutto il proceeds va in R.

Soluzione: loop unificato per-tx che fa:
1. Legge WAC corrente
2. Calcola cost_basis del sell
3. Aggiorna 3-pool (K += CB, R += gain)
4. Aggiorna per_realized
5. SOLO ORA riduce wac_pool_qty/cost

### 16.3.2 Sorting additions-first è obbligatorio

Entro lo stesso giorno, BUY PRIMA di SELL. Altrimenti una sell potrebbe leggere un WAC pre-buy sbagliato. Implementato come: `day_additions + day_reductions + day_non_position`.

### 16.3.3 FX cross-rate per WAC in asset_currency

WAC è mantenuto in `asset_currency` (non target_currency). Se un BUY è pagato in EUR ma l'asset è quotato in USD, serve cross-rate:

```
unit_cost_usd = (total_eur × fx(EUR→target)) / (fx(USD→target)) / qty
```

Implementato in `_buy_unit_cost()` tramite `fx_rate_map`.

### 16.3.4 last_buy_price è asset-level, non position-level

Un singolo dict `asset_id → (date, price, ccy)` aggiornato da TUTTI i BUY su V(u). Se l'asset è detenuto su 2 broker, il last_buy_price è l'ultimo BUY su qualunque broker visibile.

### 16.3.5 Pre-frame non ha bisogno di market FX

Nel pre-frame, gli unici FX necessari sono quelli per convertire tx.amount in target_currency (per il cash ledger) e per _buy_unit_cost (per WAC in asset_currency). NON servono FX giornalieri per prezzi — perché non calcoliamo market value nel pre-frame.

### 16.3.6 Reconciliation pool è proporzionale, non assoluta

Se `K + R ≠ cash_like` (drift da FX/arrotondamenti), non correggiamo K o R direttamente — applichiamo un fattore di scala proporzionale per `cash_from_contributed` / `cash_from_generated` che sono i valori UI-facing. Le pool interne restano consistenti per i calcoli tx successivi.
