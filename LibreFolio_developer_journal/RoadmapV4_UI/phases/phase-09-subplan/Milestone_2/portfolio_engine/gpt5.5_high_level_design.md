Di seguito il **recap finale del piano di miglioramento** per il nuovo sistema Portfolio di LibreFolio.

Obiettivo principale:

```text
Avere un Portfolio Calculation Engine unico, corretto, runtime, senza cache iniziale,
che calcoli tutti i valori giornalieri e da lì derivi summary, history, allocation e performance.
```

***

# 1. Principio architetturale principale

Il problema attuale nasce da logiche sparse:

```text
get_summary()
get_history()
allocation
performance
cash
market value
missing prices
```

ognuna con pezzi di calcolo propri.

La nuova architettura deve invece essere:

```text
Raw data dai sottosistemi
        ↓
Portfolio Calculation Engine unico
        ↓
DailyPortfolioState[] completo
        ↓
Viste derivate per frontend/API
```

Quindi:

```text
summary = ultimo DailyPortfolioState + aggregati
history = DailyPortfolioState[] filtrato
allocation = derivata dai DailyPortfolioState
performance = derivata da NAV + cash flow scope-aware
```

***

# 2. Decisione su cache

Per ora:

```text
NO cache portfolio.
```

Motivo:

* il portfolio engine è nuovo;
* prima serve correttezza;
* una cache invalidata male darebbe dati sbagliati;
* transazioni/prezzi/forex/WAC hanno già sottosistemi propri;
* ricalcolare runtime è più sicuro in questa fase.

La cache si rivaluterà dopo, eventualmente con versioni/revisioni dei sottosistemi.

***

# 3. Architettura generale

```text
┌──────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                │
│                            SvelteKit UI                               │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Dashboard                                                           │
│  ├─ Date range                                                       │
│  ├─ Broker filter                                                    │
│  ├─ Target currency                                                  │
│  ├─ GrowthChart                                                      │
│  │  ├─ ABS                                                           │
│  │  │  ├─ stacked: open_cost_basis + cash + in_transit_book          │
│  │  │  └─ overlay: NAV                                               │
│  │  └─ %                                                             │
│  │     ├─ ROI                                                        │
│  │     ├─ TWRR                                                       │
│  │     └─ MWRR                                                       │
│  │                                                                  │
│  ├─ AllocationPanel                                                  │
│  │  ├─ Now: pie/map                                                  │
│  │  └─ History: 100% stacked area                                    │
│  │                                                                  │
│  └─ DataQualityBanner                                                │
│     ├─ missing prices                                                │
│     ├─ missing FX                                                    │
│     ├─ incomplete NAV                                                │
│     └─ stale prices                                                  │
│                                                                      │
│  Nessun calcolo finanziario vero nel frontend.                       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ HTTP API
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                               BACKEND                                │
│                            FastAPI / Python                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Portfolio API                                                       │
│  ├─ POST /portfolio/summary                                          │
│  ├─ POST /portfolio/history                                          │
│  └─ futuro: allocation-history se serve endpoint separato             │
│                                                                      │
│  Responsabilità API:                                                 │
│  ├─ valida request                                                   │
│  ├─ legge current user                                               │
│  ├─ passa user_id, broker_ids, date range, target currency           │
│  └─ serializza DTO                                                   │
│                                                                      │
│                     ┌─────────────────────────────┐                  │
│                     │ Portfolio Calculation Engine│                  │
│                     │ Runtime, no cache           │                  │
│                     └─────────────────────────────┘                  │
│                                  │                                   │
│                                  ▼                                   │
│      ┌────────────────────────────────────────────────────────┐      │
│      │ Scope & Transaction Classification Layer                │      │
│      │                                                        │      │
│      │ - broker inclusi nello scope                            │      │
│      │ - share percentage                                      │      │
│      │ - linked tx interne/esterne                             │      │
│      │ - external cash flow                                    │      │
│      │ - internal transfer                                     │      │
│      │ - in-transit cash/assets                                │      │
│      └────────────────────────────────────────────────────────┘      │
│                                  │                                   │
│                                  ▼                                   │
│      ┌────────────────────────────────────────────────────────┐      │
│      │ Daily State Builder                                    │      │
│      │                                                        │      │
│      │ Calcola tutto per ogni giorno della finestra:           │      │
│      │ - cash_value                                           │      │
│      │ - market_value                                         │      │
│      │ - in_transit values                                    │      │
│      │ - nav_value                                            │      │
│      │ - open_cost_basis                                      │      │
│      │ - book_value                                           │      │
│      │ - unrealized_gain_loss                                 │      │
│      │ - allocation components                                │      │
│      │ - data quality flags                                   │      │
│      └────────────────────────────────────────────────────────┘      │
│                                  │                                   │
│                                  ▼                                   │
│      ┌────────────────────────────────────────────────────────┐      │
│      │ Derived Views Builders                                 │      │
│      │                                                        │      │
│      │ Da DailyPortfolioState[] produce:                      │      │
│      │ - Summary                                              │      │
│      │ - History                                              │      │
│      │ - Performance series                                   │      │
│      │ - Allocation current                                   │      │
│      │ - Allocation history                                   │      │
│      │ - DataQualityReport                                    │      │
│      └────────────────────────────────────────────────────────┘      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ usa
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         BACKEND SUBSYSTEMS                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Access Subsystem                                                    │
│  ├─ BrokerUserAccess                                                 │
│  ├─ Viewer / Editor / Owner                                          │
│  └─ share_percentage                                                 │
│                                                                      │
│  Transaction Subsystem                                               │
│  ├─ Transaction DB                                                   │
│  ├─ amount già signato                                               │
│  ├─ quantity già signata                                             │
│  ├─ related_transaction_id                                           │
│  ├─ cost_basis_override                                              │
│  └─ cost_basis_currency                                              │
│                                                                      │
│  Price Subsystem                                                     │
│  ├─ PriceHistory                                                     │
│  ├─ latest price <= date                                             │
│  └─ missing/stale prices                                             │
│                                                                      │
│  Forex Subsystem                                                     │
│  ├─ convert_bulk                                                     │
│  ├─ target currency conversion                                       │
│  └─ missing FX reporting                                             │
│                                                                      │
│  WAC / Cost Basis Subsystem                                          │
│  ├─ WAC per asset/broker/date                                        │
│  ├─ WAC aggiornato sulle transazioni rilevanti                       │
│  ├─ cost_basis_override su transfer-in                               │
│  └─ merge con posizioni esistenti                                    │
│                                                                      │
│  Performance Utilities                                               │
│  ├─ ROI                                                             │
│  ├─ TWRR                                                            │
│  └─ MWRR / XIRR                                                      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

***

# 4. Concetti finanziari da separare bene

## Cash

```text
cash_value(d) =
    somma cumulativa degli amount signati delle transazioni nello scope fino al giorno d
```

Tutti i tipi con `amount != 0` impattano cash.

Quindi:

```text
BUY        → cash scende
SELL       → cash sale
DEPOSIT    → cash sale
WITHDRAWAL → cash scende
DIVIDEND   → cash sale
INTEREST   → cash sale
FEE/TAX    → cash scende
FX/CASH transfer → leg signate
```

Nessun filtro per tipo, salvo amount = 0.

***

## Market value

```text
market_value(d) =
    valore di mercato delle posizioni presenti nei broker dello scope
```

Formula concettuale:

```text
market_value(d) =
    Σ quantity(asset, broker, d)
      × price_on_or_before(asset, d)
      × FX(price_currency → target_currency, d)
```

Importante:

```text
market_value usa prezzi di mercato, non WAC.
```

***

## Open cost basis

```text
open_cost_basis(d) =
    costo contabile delle posizioni ancora aperte
```

Formula iniziale con WAC:

```text
open_cost_basis(asset, broker, d) =
    WAC(asset, broker, d) × quantity_held(asset, broker, d)
```

Poi convertito in target currency.

Nota importante:

```text
WAC non è necessariamente in target currency.
Bisogna usare sempre wac_result.wac.code come valuta sorgente.
```

***

## NAV

```text
nav_value(d) =
    market_value(d)
    + cash_value(d)
    + in_transit_market_value(d)
```

Il NAV rappresenta:

```text
valore economico dello scope selezionato
```

non solo quello fisicamente presente nei broker.

***

## Book value

```text
book_value(d) =
    open_cost_basis(d)
    + cash_value(d)
    + in_transit_book_value(d)
```

Il book value rappresenta:

```text
valore contabile dello scope selezionato
```

***

## Unrealized gain/loss

```text
unrealized_gain_loss(d) =
    nav_value(d) - book_value(d)
```

Equivalentemente:

```text
unrealized_gain_loss(d) =
    asset_market_value(d) - asset_cost_basis(d)
```

includendo anche asset in transito.

***

# 5. DailyPortfolioState

Il cuore del nuovo sistema è questo oggetto logico.

```text
DailyPortfolioState
├─ date
│
├─ Valuation
│  ├─ cash_value
│  ├─ market_value
│  ├─ broker_nav_value
│  ├─ in_transit_cash_value
│  ├─ in_transit_asset_market_value
│  ├─ in_transit_market_value
│  └─ nav_value
│
├─ Accounting
│  ├─ open_cost_basis
│  ├─ in_transit_asset_cost_basis
│  ├─ in_transit_book_value
│  ├─ book_value
│  └─ unrealized_gain_loss
│
├─ Performance Inputs
│  ├─ external_cash_flow
│  ├─ internal_transfer_flow
│  └─ scope_transfer_flow
│
├─ Allocation Inputs
│  ├─ by_type_components
│  ├─ by_sector_components
│  └─ by_geography_components
│
└─ Data Quality
   ├─ missing_price_assets
   ├─ missing_fx_pairs
   ├─ stale_prices
   └─ incomplete_nav
```

***

# 6. In-transit: concetto finale

`in_transit` non è solo cash.

È:

```text
valore temporaneamente fuori dai broker dello scope,
ma ancora interno al portafoglio analizzato.
```

Esiste solo se:

```text
linked transaction interna allo scope
e
le due leg hanno date diverse
```

Se le date sono uguali:

```text
nessun in_transit.
```

***

## Tipi di in-transit

```text
in_transit_cash_value
```

Per:

* bonifici interni tra broker;
* conversioni valuta con date diverse.

```text
in_transit_asset_market_value
```

Per:

* trasferimenti titoli tra broker con date diverse.

```text
in_transit_asset_cost_basis
```

Per:

* book value dei titoli in transito.

***

## Formule

```text
in_transit_market_value(d) =
    in_transit_cash_value(d)
    + in_transit_asset_market_value(d)
```

```text
in_transit_book_value(d) =
    in_transit_cash_value(d)
    + in_transit_asset_cost_basis(d)
```

```text
nav_value(d) =
    cash_value(d)
    + market_value(d)
    + in_transit_market_value(d)
```

```text
book_value(d) =
    cash_value(d)
    + open_cost_basis(d)
    + in_transit_book_value(d)
```

***

# 7. Scope-aware classification

Punto fondamentale:

```text
interno/esterno dipende dai broker selezionati nella query.
```

Input query:

```text
target_currency
date_from
date_to
broker_ids opzionali
```

Se `broker_ids` manca:

```text
scope = tutti i broker accessibili all’utente
```

***

## Regola linked transactions

```text
se entrambe le linked transactions sono nello scope:
    movimento interno

se solo una linked transaction è nello scope:
    movimento esterno allo scope

se nessuna linked transaction è nello scope:
    ignorare

se la transazione non è linked:
    classificare secondo tipo economico
```

***

## Esempio bonifico

```text
Broker A -500
Broker B +500
related_transaction_id
```

Se A e B sono nello scope:

```text
internal transfer
non external cash flow
se date diverse → in_transit_cash_value
```

Se solo A è nello scope:

```text
external outflow dello scope
```

Se solo B è nello scope:

```text
external inflow dello scope
```

***

## Esempio trasferimento titoli

```text
Broker A adjustment -qty
Broker B adjustment +qty
related_transaction_id
```

Se A e B sono nello scope:

```text
internal security transfer
non external flow
se date diverse → in_transit_asset_market_value
```

Il receiver ha:

```text
cost_basis_override
cost_basis_currency
```

Da usare per il costo contabile del transfer-in e del transito.

***

## Esempio cambio valuta

```text
- EUR
+ USD
related_transaction_id
```

Se entrambe le leg sono nello scope:

```text
internal FX conversion
non external cash flow
se date diverse → in_transit_cash_value
```

***

# 8. Performance: ROI, TWRR, MWRR

Per ora niente nuove metriche. Prima correttezza.

## Principio

Le performance devono usare:

```text
NAV giornaliero corretto
external cash flow scope-aware
```

Non basta più:

```text
DEPOSIT/WITHDRAWAL = external cash flow
```

perché bonifici/cambi/trasferimenti collegati possono essere interni allo scope.

***

## Regola

```text
external_cash_flow(d)
```

deve contenere solo flussi che entrano/escono dallo scope selezionato.

Quindi:

```text
movimento interno allo scope → non external
movimento parziale fuori scope → external per lo scope selezionato
```

***

# 9. Missing prices

Scelta confermata.

Se un asset detenuto non ha prezzo:

```text
non si valorizza nel market_value
NAV incompleto
asset segnalato al frontend
```

Ma:

```text
open_cost_basis può essere disponibile via WAC
book_value può essere più completo del NAV
```

***

## DTO ricco

Non basta più:

```text
missing_prices_assets: List[str]
```

Serve:

```text
MissingPriceAsset
├─ asset_id
├─ symbol
├─ name
├─ broker_id
├─ broker_name
├─ first_position_date
├─ quantity
├─ open_cost_basis
└─ currency
```

Frontend:

```text
Banner amber:
Alcuni asset detenuti non hanno prezzi storici. Il NAV potrebbe essere sottostimato.
Aggiungi almeno un prezzo iniziale per valorizzarli.
```

***

# 10. Naming nuovo

Dato che il sistema è recente, conviene rompere ora.

## Da evitare

```text
invested_value
invested_capital
```

Sono ambigui.

## Nuovi nomi

```text
cash_value
market_value
broker_nav_value
in_transit_market_value
nav_value
open_cost_basis
book_value
unrealized_gain_loss
```

***

# 11. Grafico ABS finale

Il grafico ABS deve mostrare:

```text
valore contabile vs valore economico
```

## Stacked area

```text
open_cost_basis
cash_value
in_transit_book_value
```

Il top dello stacked è:

```text
book_value
```

## Linea overlay

```text
nav_value
```

Dove:

```text
nav_value =
    market_value
    + cash_value
    + in_transit_market_value
```

***

## Interpretazione visiva

```text
NAV sopra book_value
→ plusvalenza latente

NAV sotto book_value
→ minusvalenza latente
```

Eventuale frontend:

```text
area differenza verde se NAV > book_value
area differenza rossa se NAV < book_value
```

***

## Tooltip consigliato

```text
NAV: 12.450 €
Book value: 12.100 €
Unrealized gain/loss: +350 €

Market value: 10.000 €
Open cost basis: 9.650 €
Cash: 2.000 €

In transit:
  Cash: 300 €
  Securities market value: 150 €
  Securities cost basis: 120 €
```

***

# 12. Allocation

## Allocation “oggi”

### Type

```text
cash → Liquidity
```

### Sector

```text
cash → Liquidity
```

### Geography

La UI attuale con mappa resta valida.

La parte geografica deve rappresentare gli asset classificabili geograficamente.

Sotto la mappa:

```text
X% degli asset non ha classificazione geografica disponibile.
```

Non dire:

```text
cash = Unknown country
```

***

## Allocation history

Nuovo toggle:

```text
Ora | Storia
```

In modalità storia:

```text
100% stacked area
```

### Type history

```text
asset type + Liquidity
```

### Sector history

```text
sector + Liquidity
```

### Geography history

```text
nazioni + Unknown
```

Dove `Unknown` significa:

```text
asset non geolocalizzabili
```

Non deve essere una nazione fittizia per la cash.

Asset in transito:

```text
continuano a contribuire alla loro type/sector/geography
```

Cash in transito:

```text
Liquidity per type/sector
non rappresentata come paese per geography
```

***

# 13. Data quality

Il nuovo engine deve produrre un oggetto esplicito.

```text
DataQualityReport
├─ missing_price_assets
├─ missing_fx_pairs
├─ stale_prices
├─ incomplete_nav_dates
├─ incomplete_book_value_dates
└─ warnings
```

## Esempi

```text
missing price
→ NAV sottostimato o incompleto

missing FX
→ valore escluso o non convertibile

stale price
→ valore calcolato, ma con prezzo vecchio

incomplete NAV date
→ almeno un asset detenuto non valorizzabile in quel giorno
```

***

# 14. DTO target

## PortfolioHistoryPoint

```text
PortfolioHistoryPoint
├─ date
├─ cash_value
├─ market_value
├─ broker_nav_value
├─ in_transit_cash_value
├─ in_transit_asset_market_value
├─ in_transit_market_value
├─ nav_value
├─ open_cost_basis
├─ in_transit_asset_cost_basis
├─ in_transit_book_value
├─ book_value
├─ unrealized_gain_loss
├─ twrr
├─ mwrr
└─ roi
```

***

## PortfolioSummary

```text
PortfolioSummary
├─ net_worth / nav_value
├─ market_value
├─ cash_total
├─ in_transit_market_value
├─ open_cost_basis
├─ book_value
├─ unrealized_gain_loss
├─ total_invested
├─ total_gain_loss
├─ simple_roi_percent
├─ twrr_percent
├─ mwrr_percent
├─ allocation_by_type
├─ allocation_by_sector
├─ allocation_by_geography
├─ missing_price_assets
├─ missing_fx_pairs
└─ data_quality
```

Nota naming:

```text
net_worth può restare come alias UI/API di nav_value,
ma internamente meglio usare nav_value.
```

***

# 15. Roadmap implementativa

## Step 1 — Nuovo engine runtime

Creare:

```text
portfolio_engine.py
```

Con:

```text
PortfolioCalculationEngine
DailyPortfolioState
PortfolioCalculationResult
```

Niente cache.

***

## Step 2 — Scope e classificazione transazioni

Creare layer:

```text
ScopeAwareTransactionClassifier
```

Responsabilità:

```text
- capire scope broker
- gestire share_percentage
- classificare linked transactions
- distinguere internal/external
- generare in-transit quando serve
```

***

## Step 3 — Serie giornaliera completa

Il motore calcola tutti i valori per ogni giorno della finestra:

```text
cash
quantity
market value
in-transit
NAV
open cost basis
book value
unrealized gain/loss
```

***

## Step 4 — WAC daily

Usare WAC centralizzato.

Non chiamare WAC per ogni giorno.

Approccio:

```text
WAC aggiornato a transazioni rilevanti
forward-fill tra una transazione e la successiva
```

***

## Step 5 — Missing prices / missing FX

Aggiungere:

```text
MissingPriceAsset DTO
DataQualityReport
incomplete_nav_dates
```

***

## Step 6 — Summary/history da engine unico

`get_summary()` e `get_history()` diventano adapter.

```text
summary = vista derivata
history = vista derivata
```

Non devono più avere calcoli paralleli.

***

## Step 7 — Frontend GrowthChart

Aggiornare ABS:

```text
stacked area:
  open_cost_basis
  cash_value
  in_transit_book_value

overlay:
  nav_value
```

***

## Step 8 — Allocation Ora/Storia

Aggiungere toggle:

```text
Ora | Storia
```

E implementare:

```text
100% stacked area per type/sector/geography
```

***

## Step 9 — Performance

Solo dopo stabilizzazione daily states:

```text
ROI
TWRR
MWRR
```

basati su:

```text
NAV corretto
external cash flow scope-aware
```

***

# 16. Test essenziali

## Cash ledger

```text
BUY riduce cash
SELL aumenta cash
DEPOSIT aumenta cash
WITHDRAWAL riduce cash
DIVIDEND aumenta cash
INTEREST aumenta cash
FEE/TAX riducono cash
```

***

## NAV

```text
NAV = market_value + cash_value + in_transit_market_value
```

***

## Book value

```text
book_value = open_cost_basis + cash_value + in_transit_book_value
```

***

## Unrealized gain/loss

```text
unrealized_gain_loss = nav_value - book_value
```

***

## Missing price

```text
asset detenuto senza prezzo:
  market_value incompleto
  NAV incompleto
  missing_price_assets valorizzato
```

***

## Internal transfer stesso giorno

```text
linked tx interne stesso giorno:
  no external cash flow
  no in_transit
  NAV stabile
```

***

## Internal transfer date diverse

```text
linked tx interne con date diverse:
  no external cash flow
  in_transit valorizzato tra le due date
  NAV stabile salvo variazione prezzo asset
```

***

## Transfer fuori scope

```text
solo una leg nello scope:
  external cash flow
  no in_transit
  NAV cambia per lo scope selezionato
```

***

## Asset in transito

```text
titolo in transito:
  valorizzato giornalmente a prezzo di mercato
  incluso nel NAV
  incluso nel book value tramite cost basis
```

***

# 17. Sintesi finale

Il piano finale è:

```text
1. Un solo Portfolio Calculation Engine.
2. Nessuna cache iniziale.
3. Calcolo completo per ogni giorno della finestra.
4. Summary/history/allocation/performance sono viste derivate.
5. Cash = ledger algebrico completo.
6. Market value = quantità × prezzo di mercato.
7. Open cost basis = WAC × quantità.
8. NAV = market value + cash + in-transit market value.
9. Book value = open cost basis + cash + in-transit book value.
10. In-transit gestisce cash, FX e titoli interni allo scope con date diverse.
11. External cash flow dipende dallo scope broker selezionato.
12. Missing prices e missing FX devono essere espliciti.
13. Naming pulito subito, rompendo ora se necessario.
14. Grafico ABS mostra book value stacked e NAV overlay.
15. Allocation history usa serie time-based 100% stacked.
```

Questo impianto dovrebbe evitare il problema attuale principale:

```text
calcoli duplicati, nomi ambigui, gradini non spiegati, NAV incompleto non segnalato.
```

E crea una base pulita per aggiungere dopo:

```text
benchmark
max drawdown
volatility
Sharpe
FIFO/lotti avanzati
cash drag
analytics più evolute
```
