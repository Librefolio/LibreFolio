````markdown
# LibreFolio — Portfolio Calculation Engine High-Level Design

> **Area:** Phase 09 / Milestone 2 / Portfolio Engine  
> **Purpose:** nuovo design architetturale per calcoli portfolio coerenti, scope-aware, runtime, senza cache iniziale  
> **Status:** high-level design aggiornato dopo code coherence review  
> **Date:** 2026-06-19

---

## 1. Obiettivo

L’obiettivo è sostituire le logiche sparse oggi presenti in `get_summary()`, `get_history()`, allocation e performance con un unico motore:

```text
PortfolioCalculationEngine
````

Il motore deve:

1. Calcolare tutti i valori per ogni giorno della finestra richiesta.
2. Usare i sottosistemi esistenti, senza duplicarne la logica:
   * Transaction subsystem
   * Price subsystem
   * Forex subsystem
   * WAC / Cost Basis subsystem
   * Access subsystem
   * Performance math utilities
3. Produrre un vettore completo:

```text
DailyPortfolioState[]
```

4. Derivare da quel vettore:
   * summary
   * history
   * performance metrics
   * allocation current
   * allocation history
   * data quality report

***

## 2. Decisione su cache

Per la prima implementazione:

```text
NO portfolio cache.
```

Il motore ricalcola runtime.

Motivi:

* priorità alla correttezza;
* rischio alto di cache stale se transazioni, prezzi, FX o WAC cambiano;
* il portfolio engine è nuovo;
* i sottosistemi base hanno già logiche proprie;
* eventuale cache può essere aggiunta dopo, con invalidazione basata su revision/version dei dati.

***

## 3. Architettura generale

```text
┌──────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                │
│                            SvelteKit UI                               │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Dashboard                                                           │
│  ├─ DateRangePicker                                                  │
│  ├─ BrokerFilter                                                     │
│  ├─ TargetCurrencySelector                                           │
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
│  Frontend responsibility:                                            │
│  - rendering                                                         │
│  - user interaction                                                  │
│  - API calls                                                         │
│  - no financial calculation logic                                    │
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
│  └─ POST /portfolio/allocation-history                               │
│                                                                      │
│  API responsibilities:                                               │
│  ├─ validate request                                                 │
│  ├─ resolve current user                                             │
│  ├─ pass user_id, broker_ids, date range, target_currency to engine  │
│  └─ serialize DTOs                                                   │
│                                                                      │
│                     ┌─────────────────────────────┐                  │
│                     │ PortfolioCalculationEngine  │                  │
│                     │ Runtime, no cache initially │                  │
│                     └─────────────────────────────┘                  │
│                                  │                                   │
│                                  ▼                                   │
│      ┌────────────────────────────────────────────────────────┐      │
│      │ ScopeAwareTransactionClassifier                        │      │
│      │                                                        │      │
│      │ - resolves broker scope                                │      │
│      │ - applies share_percentage                             │      │
│      │ - classifies linked tx as internal/external             │      │
│      │ - identifies in-transit cash/assets                     │      │
│      │ - builds scope-aware external cash flows                │      │
│      └────────────────────────────────────────────────────────┘      │
│                                  │                                   │
│                                  ▼                                   │
│      ┌────────────────────────────────────────────────────────┐      │
│      │ DailyStateBuilder                                      │      │
│      │                                                        │      │
│      │ Calculates all values for each day in the window:       │      │
│      │ - cash_value                                           │      │
│      │ - market_value                                         │      │
│      │ - in_transit values                                    │      │
│      │ - nav_value                                            │      │
│      │ - open_cost_basis                                      │      │
│      │ - book_value                                           │      │
│      │ - unrealized_gain_loss                                 │      │
│      │ - external_cash_flow                                   │      │
│      │ - allocation components                                │      │
│      │ - data quality flags                                   │      │
│      └────────────────────────────────────────────────────────┘      │
│                                  │                                   │
│                                  ▼                                   │
│      ┌────────────────────────────────────────────────────────┐      │
│      │ DerivedViewsBuilder                                    │      │
│      │                                                        │      │
│      │ From DailyPortfolioState[] derives:                    │      │
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
                                  │ uses
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
│  ├─ transactions                                                     │
│  ├─ amount already signed                                            │
│  ├─ quantity already signed                                          │
│  ├─ related_transaction_id                                           │
│  ├─ cost_basis_override                                              │
│  └─ cost_basis_currency                                              │
│                                                                      │
│  Price Subsystem                                                     │
│  ├─ PriceHistory                                                     │
│  ├─ latest price <= date                                             │
│  ├─ quote_base_quantity support                                      │
│  └─ missing/stale price detection                                    │
│                                                                      │
│  Forex Subsystem                                                     │
│  ├─ convert_bulk                                                     │
│  ├─ target currency conversion                                       │
│  └─ missing FX reporting                                             │
│                                                                      │
│  WAC / Cost Basis Subsystem                                          │
│  ├─ WAC per asset/broker/as-of-date                                  │
│  ├─ WAC updated at relevant transactions                             │
│  ├─ cost_basis_override for transfer-in                              │
│  └─ merge with existing positions                                    │
│                                                                      │
│  Performance Math Utilities                                          │
│  ├─ ROI                                                             │
│  ├─ TWRR                                                            │
│  └─ MWRR / XIRR                                                      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

***

## 4. Input del PortfolioCalculationEngine

Il motore riceve:

```text
user_id
broker_ids opzionali
date_from
date_to
target_currency
```

Regola broker scope:

```text
se broker_ids è valorizzato:
    scope = broker selezionati tra quelli accessibili all’utente

se broker_ids è vuoto/null:
    scope = tutti i broker accessibili all’utente
```

Il ruolo `Viewer`, `Editor`, `Owner` non cambia il calcolo.

```text
Viewer / Editor / Owner con accesso allo stesso broker vedono gli stessi report.
```

Il ruolo impatta solo le operazioni di scrittura.

***

## 5. Principio base: calcolo giornaliero completo

Il motore deve calcolare tutti i valori per ogni giorno della finestra richiesta.

Non deve esistere:

```text
summary calcolato con una logica
history calcolata con un’altra logica
allocation calcolata con un’altra logica
```

Deve esistere:

```text
DailyPortfolioState[] completo
        ↓
summary/history/allocation/performance come viste derivate
```

***

## 6. DailyPortfolioState

Oggetto logico centrale.

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

## 7. Naming definitivo

Il sistema è recente: meglio rompere ora, evitando alias ambigui.

### Nomi da usare

```text
cash_value
market_value
broker_nav_value
in_transit_cash_value
in_transit_asset_market_value
in_transit_market_value
nav_value
open_cost_basis
in_transit_asset_cost_basis
in_transit_book_value
book_value
unrealized_gain_loss
```

### Nomi da evitare/rimuovere

```text
invested_value
invested_capital
```

Motivo:

```text
invested_value nel codice attuale significa market_value.
total_invested invece significa capitale versato.
Il naming è ambiguo.
```

### Breaking change consigliato

Rinominare:

```text
PortfolioHistoryPoint.invested_value
```

in:

```text
PortfolioHistoryPoint.market_value
```

Aggiornare backend, frontend e API client generato nello stesso cambio.

***

## 8. Cash ledger

`amount` nel DB è già algebricamente signato dal punto di vista del broker/portfolio.

Formula:

```text
cash_value(d) =
    somma cumulativa di tutti gli amount signati
    delle transazioni accessibili nello scope
    fino al giorno d
    convertiti in target_currency
    applicando share_percentage
```

Non servono filtri per tipo per la cash.

Esempi:

```text
BUY        → amount < 0 → cash scende
SELL       → amount > 0 → cash sale
DEPOSIT    → amount > 0 → cash sale
WITHDRAWAL → amount < 0 → cash scende
DIVIDEND   → amount > 0 → cash sale
INTEREST   → amount > 0 → cash sale
FEE/TAX    → amount < 0 → cash scende
FX/CASH transfer → ogni leg ha amount signato
ADJUSTMENT/TRANSFER titoli → amount = 0
```

***

## 9. Quantity ledger

Il nuovo engine non deve considerare solo BUY/SELL.

Formula:

```text
quantity(asset, broker, d) =
    somma cumulativa di tutte le transaction.quantity != 0
    fino al giorno d
    applicando share_percentage
```

Quindi include:

```text
BUY
SELL
TRANSFER
ADJUSTMENT
corporate action modellate come adjustment
```

Questo corregge il rischio attuale:

```text
TRANSFER/ADJUSTMENT ignorati nel quantity tracking.
```

***

## 10. Market value

`market_value` è il valore di mercato delle posizioni presenti nei broker dello scope.

Non usa WAC.

Formula corretta:

```text
market_value(asset, broker, d) =
    (quantity(asset, broker, d) / quote_base_quantity(asset))
    × price_on_or_before(asset, d)
    × FX(price_currency → target_currency, d)
```

Dove:

```text
quote_base_quantity = asset.quote_base_quantity
```

Se `quote_base_quantity` non è valorizzato:

```text
quote_base_quantity = 1
```

Questo è fondamentale per BTP, bond e strumenti quotati a base 100.

Esempio:

```text
quantity = 10000 nominali
price = 98.5
quote_base_quantity = 100

market_value = (10000 / 100) × 98.5 = 9850
```

***

## 11. Open cost basis

`open_cost_basis` è il costo contabile delle posizioni ancora aperte.

Formula iniziale, basata su WAC:

```text
open_cost_basis(asset, broker, d) =
    WAC(asset, broker, d)
    × quantity(asset, broker, d)
```

Poi il risultato viene convertito nella `target_currency` della query.

Attenzione:

```text
WAC ha una propria currency.
La query portfolio ha una target_currency.
```

Regola:

```text
usare sempre wac_result.wac.code come valuta sorgente.
```

Conversione corretta:

```text
open_cost_basis_target =
    Currency(wac_currency, WAC_amount × quantity)
    convertita in target_currency al giorno d
```

Non fare doppia conversione.

***

## 12. WAC storico e forward-fill

Il sistema WAC fornisce WAC as-of e una lista di transazioni rilevanti con running WAC.

Non chiamare WAC per ogni giorno.

Approccio:

```text
per ogni asset/broker:
    compute_wac_iterative(as_of_date = date_to)
    estrai wac_qualifying_txs con running_wac
    costruisci serie WAC giornaliera tramite forward-fill
```

Tra due transazioni rilevanti:

```text
WAC(d) = ultimo running_wac <= d
```

Quindi:

```text
open_cost_basis(d) = WAC(d) × quantity(d)
```

***

## 13. Book value

`book_value` è il valore contabile dello scope selezionato.

Formula:

```text
book_value(d) =
    open_cost_basis(d)
    + cash_value(d)
    + in_transit_book_value(d)
```

Dove:

```text
in_transit_book_value(d) =
    in_transit_cash_value(d)
    + in_transit_asset_cost_basis(d)
```

***

## 14. NAV

`nav_value` è il valore economico dello scope selezionato.

Formula:

```text
broker_nav_value(d) =
    market_value(d)
    + cash_value(d)
```

```text
in_transit_market_value(d) =
    in_transit_cash_value(d)
    + in_transit_asset_market_value(d)
```

```text
nav_value(d) =
    broker_nav_value(d)
    + in_transit_market_value(d)
```

Espanso:

```text
nav_value(d) =
    market_value(d)
    + cash_value(d)
    + in_transit_cash_value(d)
    + in_transit_asset_market_value(d)
```

***

## 15. Unrealized gain/loss

Formula:

```text
unrealized_gain_loss(d) =
    nav_value(d) - book_value(d)
```

Equivalentemente:

```text
unrealized_gain_loss(d) =
    (market_value(d) + in_transit_asset_market_value(d))
    -
    (open_cost_basis(d) + in_transit_asset_cost_basis(d))
```

Il cash e il cash in transito non creano plus/minusvalenza latente.

***

## 16. Scope-aware linked transactions

Il concetto interno/esterno dipende dallo scope dei broker selezionati.

### Regola base

Per una linked transaction:

```text
se entrambe le leg sono nello scope:
    movimento interno

se solo una leg è nello scope:
    movimento esterno allo scope

se nessuna leg è nello scope:
    ignorare
```

Questo vale per:

```text
CASH_TRANSFER
FX_CONVERSION
TRANSFER titoli
ADJUSTMENT linked usati come transfer titoli
```

***

## 17. External cash flow

Le performance devono usare cash flow esterni allo scope selezionato.

Non basta dire:

```text
DEPOSIT/WITHDRAWAL = external cash flow
```

perché linked transactions possono rappresentare movimenti interni.

Regola:

```text
external_cash_flow(d) =
    valore che entra o esce dallo scope selezionato
```

Esempi:

### Deposito standalone

```text
external inflow
```

### Prelievo standalone

```text
external outflow
```

### Bonifico broker A → broker B, entrambi nello scope

```text
internal transfer
external_cash_flow = 0
```

### Bonifico broker A → broker B, solo A nello scope

```text
external outflow per lo scope
```

### Bonifico broker A → broker B, solo B nello scope

```text
external inflow per lo scope
```

***

## 18. In-transit

`in_transit` è un concetto runtime.

Non richiede nuovi campi DB.

Esiste solo se:

```text
linked transaction interna allo scope
e
le due leg hanno date diverse
```

Se le date sono uguali:

```text
in_transit = 0
```

***

## 19. Finestra in-transit

Se:

```text
departure_date < arrival_date
```

allora l’in-transit è attivo nei giorni intermedi:

```text
(departure_date, arrival_date)
```

Ovvero:

```text
departure_date + 1  →  arrival_date - 1
```

Motivo:

* nel `departure_date` la leg negativa è già nel ledger del broker sorgente;
* nel `arrival_date` la leg positiva è già nel ledger del broker ricevente;
* il transito rappresenta solo il buco tra le due date.

***

## 20. In-transit cash

Per cash transfer o FX conversion con date diverse:

```text
in_transit_cash_value(d) =
    valore della leg di partenza
    convertito in target_currency al giorno d
```

La leg di partenza è:

```text
la leg con amount < 0
```

Per FX conversion:

```text
usare la valuta della leg negativa fino alla data di arrivo.
```

***

## 21. In-transit asset

Per trasferimento titoli con date diverse:

```text
in_transit_asset_market_value(asset, d) =
    (quantity_in_transit / quote_base_quantity(asset))
    × price_on_or_before(asset, d)
    × FX(price_currency → target_currency, d)
```

Quindi l’asset in transito continua a muoversi a mercato.

***

## 22. In-transit asset cost basis

Per trasferimento titoli:

Prima scelta:

```text
cost_basis_override della leg ricevente
```

convertito da:

```text
cost_basis_currency → target_currency
```

Fallback:

```text
WAC del broker sorgente alla departure_date
```

Se manca anche il fallback:

```text
in_transit_asset_cost_basis incompleto
DataQuality warning
```

Nota:

```text
cost_basis_override è opzionale nel DB.
Il piano non deve assumere che sia sempre presente.
```

***

## 23. share\_percentage e in-transit

Regola iniziale:

```text
se entrambe le leg sono nello scope:
    share in-transit = share_percentage della leg di partenza
```

Se:

```text
share_source != share_target
```

allora:

```text
calcolare comunque usando share_source
aggiungere DataQuality/debug warning
```

Motivo:

```text
durante il transito il valore è uscito dal broker sorgente e non è ancora entrato nel broker ricevente.
```

***

## 24. Missing prices

Se un asset detenuto o in transito non ha prezzo disponibile:

```text
non entra nel market_value
NAV è incompleto
asset viene segnalato in data_quality
```

Non usare automaticamente il prezzo di acquisto come fallback.

Motivo:

```text
market value deve restare distinto da cost basis.
```

***

## 25. MissingPriceAsset DTO

Sostituire il semplice `List[str]` con DTO ricco.

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

## 26. Stale prices

Il price subsystem usa backward-fill.

Questo è corretto, ma deve essere visibile.

Threshold iniziale consigliata:

```text
stale se latest price usato è più vecchio di 7 giorni calendario
```

Se stale:

```text
il valore può essere calcolato
ma data_quality deve segnalarlo
```

***

## 27. Missing FX

Tutte le conversioni devono passare dal Forex subsystem, idealmente tramite `convert_bulk()`.

Se una conversione FX manca:

```text
valore non convertibile
escluso dalla somma interessata
missing_fx_pairs valorizzato
data_quality warning
```

Non inventare tassi.

***

## 28. DataQualityReport

Nuovo oggetto strutturato.

```text
DataQualityReport
├─ missing_price_assets
├─ missing_fx_pairs
├─ stale_prices
├─ incomplete_nav_dates
├─ incomplete_book_value_dates
├─ incomplete_allocation_dates
├─ in_transit_cost_basis_warnings
├─ share_mismatch_warnings
└─ warnings
```

Semantica:

```text
missing price
→ NAV potenzialmente sottostimato

missing FX
→ valore non convertibile

stale price
→ valore calcolato, ma con prezzo vecchio

incomplete NAV date
→ almeno un asset detenuto/in transito non valorizzabile

incomplete book value
→ costo contabile non disponibile per qualche componente

share mismatch
→ linked tx interna con share diverse tra broker
```

***

## 29. Performance metrics

Per ora non introdurre nuove metriche.

Prima correggere:

```text
ROI
TWRR
MWRR
```

usando:

```text
NAV giornaliero corretto
external_cash_flow scope-aware
```

***

## 30. TWRR / MWRR / ROI inputs

Input corretti:

```text
NAV series = nav_value(d)
Cash flows = external_cash_flow(d)
```

`external_cash_flow` non deve includere movimenti interni allo scope.

Bug attuale da correggere naturalmente con il nuovo engine:

```text
get_summary usa NAV odierno su date storiche per TWRR/MWRR.
```

Nel nuovo engine:

```text
summary performance = derivata dal DailyPortfolioState[]
```

non da NAV flat.

***

## 31. Allocation current

`allocation current` deriva dall’ultimo `DailyPortfolioState`.

### Type

```text
asset type + Liquidity
```

Cash e cash in transito:

```text
Liquidity
```

Asset in transito:

```text
mantiene asset type originale
```

### Sector

```text
asset sector + Liquidity
```

Cash e cash in transito:

```text
Liquidity
```

Asset in transito:

```text
mantiene sector dell’asset
```

### Geography

La UI attuale usa una mappa.

Regola:

```text
cash non è una nazione
cash non va colorata sulla mappa
```

La mappa mostra solo asset geolocalizzabili.

Sotto la mappa:

```text
X% degli asset non ha classificazione geografica disponibile.
```

Asset in transito:

```text
mantiene classificazione geografica dell’asset
```

***

## 32. Allocation history

Non includere di default in `/portfolio/history`.

Creare endpoint dedicato:

```text
POST /portfolio/allocation-history
```

Motivo:

```text
allocation history può essere pesante su range lunghi.
```

Output:

```text
100% stacked area time series
```

### Type history

```text
asset types + Liquidity
```

### Sector history

```text
sectors + Liquidity
```

### Geography history

```text
nazioni + Unknown
```

Dove:

```text
Unknown = asset non geolocalizzabili
```

Non significa:

```text
cash
```

Cash non è un paese.

***

## 33. Allocation con NAV incompleto

Se NAV è incompleto per missing prices:

```text
calcolare allocation sul valore valorizzabile
marcare il giorno come incomplete_allocation_date
mostrare warning frontend
```

Non scartare automaticamente il giorno.

***

## 34. Grafico ABS

Il grafico ABS deve confrontare:

```text
valore contabile
vs
valore economico
```

### Stacked area

```text
open_cost_basis
cash_value
in_transit_book_value
```

Top dello stacked:

```text
book_value
```

### Overlay line

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

### Interpretazione

```text
NAV sopra book_value
→ plusvalenza latente

NAV sotto book_value
→ minusvalenza latente
```

***

## 35. Tooltip ABS consigliato

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

## 36. PortfolioHistoryPoint target

Breaking change consentito.

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

Rimuovere/rinominare:

```text
invested_value → market_value
```

***

## 37. PortfolioSummary target

```text
PortfolioSummary
├─ nav_value
├─ net_worth
├─ cash_total
├─ market_value
├─ broker_nav_value
├─ in_transit_market_value
├─ open_cost_basis
├─ in_transit_book_value
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

Nota:

```text
net_worth può restare come alias UI/API di nav_value.
Internamente usare nav_value.
```

***

## 38. Endpoint consigliati

```text
POST /portfolio/summary
POST /portfolio/history
POST /portfolio/allocation-history
```

`/summary` e `/history` devono essere adapter sopra il nuovo engine.

`/allocation-history` può essere separato per costo computazionale.

***

## 39. Performance runtime

Senza cache, mitigare con:

```text
single-pass transaction loading
batch FX conversion
bulk price loading
WAC forward-fill
pure functions testabili
allocation_history endpoint separato
eventuale sampling su range lunghi
```

Sampling consigliato per allocation history:

```text
range breve → daily
range lungo → weekly/monthly, da definire lato UI/API
```

Non introdurre cache nella prima implementazione.

***

## 40. Roadmap implementativa consigliata

### Step 1 — ScopeAwareTransactionClassifier

Responsabilità:

```text
classificare transazioni in:
- normal transaction
- linked internal
- linked external outflow
- linked external inflow
- in-transit candidate
```

Output:

```text
normalized tx
external cash flow events
in-transit intervals
data quality warnings
```

***

### Step 2 — CashLedger + QuantityLedger

Pure functions.

```text
cash_value(d)
quantity(asset, broker, d)
```

Quantity deve includere:

```text
tutte le transaction.quantity != 0
```

***

### Step 3 — Price / FX preload

Precaricare:

```text
price history per asset
FX conversions necessarie
quote_base_quantity
```

***

### Step 4 — WAC forward-fill

Per ogni asset/broker:

```text
compute WAC as-of date_to
extract running WAC points
forward-fill daily WAC
```

***

### Step 5 — DailyPortfolioStateBuilder

Costruire per ogni giorno:

```text
cash
quantity
market_value
open_cost_basis
in_transit
nav_value
book_value
unrealized_gain_loss
data quality flags
```

***

### Step 6 — Derived views

Creare adapter:

```text
summary from DailyPortfolioState[]
history from DailyPortfolioState[]
performance from NAV + external CF
```

***

### Step 7 — DTO/API breaking change

Aggiornare:

```text
PortfolioHistoryPoint
PortfolioSummary
DataQualityReport
MissingPriceAsset
```

Rinominare:

```text
invested_value → market_value
```

Eseguire API sync e aggiornare frontend.

***

### Step 8 — GrowthChart ABS

Aggiornare grafico:

```text
stacked: open_cost_basis + cash_value + in_transit_book_value
overlay: nav_value
```

***

### Step 9 — Allocation history endpoint

Implementare:

```text
POST /portfolio/allocation-history
```

con:

```text
type
sector
geography
```

***

### Step 10 — Refinement performance

Validare:

```text
ROI
TWRR
MWRR
```

su NAV giornaliero e external cash flow scope-aware.

***

## 41. Test minimi

### Cash ledger

```text
BUY riduce cash
SELL aumenta cash
DEPOSIT aumenta cash
WITHDRAWAL riduce cash
DIVIDEND aumenta cash
INTEREST aumenta cash
FEE/TAX riducono cash
```

### Quantity ledger

```text
BUY aumenta qty
SELL riduce qty
TRANSFER riduce/aumenta qty
ADJUSTMENT modifica qty
```

### NAV

```text
nav_value = market_value + cash_value + in_transit_market_value
```

### Market value BTP/bond

```text
quantity = 10000
price = 98.5
quote_base_quantity = 100

market_value = 9850
```

### Book value

```text
book_value = open_cost_basis + cash_value + in_transit_book_value
```

### Unrealized gain/loss

```text
unrealized_gain_loss = nav_value - book_value
```

### Missing price

```text
asset detenuto senza prezzo:
    market_value incompleto
    NAV incompleto
    missing_price_assets valorizzato
```

### Missing FX

```text
conversione mancante:
    valore escluso
    missing_fx_pairs valorizzato
```

### Internal linked tx stesso giorno

```text
cash transfer A→B same day, entrambi nello scope:
    external_cash_flow = 0
    in_transit = 0
    NAV stabile
```

### Internal linked tx date diverse

```text
cash transfer A→B date diverse, entrambi nello scope:
    external_cash_flow = 0
    in_transit_cash_value nei giorni intermedi
    NAV stabile
```

### Linked tx parziale nello scope

```text
solo una leg nello scope:
    external cash flow
    no in_transit
    NAV cambia per lo scope
```

### FX conversion

```text
EUR→USD linked:
    internal se entrambe le leg nello scope
    no external cash flow
    cash cambia valuta
```

### Security transfer

```text
asset transfer A→B:
    quantity si sposta
    NAV dello scope resta stabile
    se date diverse, asset in transit valorizzato a mercato
```

### Transfer cost basis

```text
se cost_basis_override presente:
    usare quello

se assente:
    fallback WAC sorgente

se fallback assente:
    warning data_quality
```

### Allocation geography

```text
cash non è paese
asset senza geo → Unknown
asset in transit mantiene geo asset
```

### share\_percentage

```text
share=0.5:
    cash, qty, market value, book value, NAV dimezzati
```

### Performance

```text
internal transfer non altera ROI/TWRR/MWRR
external deposit/prelievo sì
```

***

## 42. Bug attuali da risolvere con il refactor

Il nuovo engine deve eliminare questi problemi:

```text
1. get_summary calcola TWRR/MWRR usando NAV odierno su date storiche.
2. get_history usa quantity tracking solo BUY/SELL.
3. invested_value significa market_value.
4. missing prices in history possono sottostimare NAV senza warning ricco.
5. linked transactions non sono pienamente classificate rispetto allo scope.
6. summary/history duplicano logiche e rischiano divergenze.
```

***

## 43. Decisione finale

Il piano aggiornato è:

```text
1. PortfolioCalculationEngine unico.
2. Nessuna cache iniziale.
3. Calcolo completo per ogni giorno della finestra.
4. Summary/history/allocation/performance come viste derivate.
5. Cash = ledger algebrico completo.
6. Quantity = ledger completo su tutte le quantity != 0.
7. Market value = quantity / quote_base_quantity × price × FX.
8. Open cost basis = WAC × quantity × FX.
9. NAV = market_value + cash + in_transit_market_value.
10. Book value = open_cost_basis + cash + in_transit_book_value.
11. In-transit gestisce cash, FX e asset interni allo scope con date diverse.
12. External cash flow dipende dallo scope broker selezionato.
13. Missing prices, stale prices e missing FX sono espliciti.
14. Breaking change naming ora: invested_value → market_value.
15. Allocation history endpoint separato.
16. FIFO/lotti avanzati rimandati.
17. Cache rimandata.
```

Questo design crea una base coerente per aggiungere dopo:

```text
benchmark
max drawdown
volatility
Sharpe
cash drag
FIFO/lotti avanzati
analytics portfolio-level più evolute
```

```
```
