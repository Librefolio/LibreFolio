# Portfolio Engine — Code Agent Coherence Review

**Data:** 2026-06-19
**Piano analizzato:** `gpt5.5_high_level_design.md`
**Codice di riferimento:** backend commit corrente (main)
**Agente:** Claude Opus 4.6

---

## 1. Sintesi del piano

Il piano propone un **PortfolioCalculationEngine** unico che:

1. Sostituisce le logiche sparse in `get_summary()` / `get_history()` con un singolo motore runtime
2. Calcola un `DailyPortfolioState[]` completo per ogni giorno della finestra
3. Deriva summary/history/allocation/performance come viste su quel vettore
4. Introduce classificazione scope-aware delle linked transactions (internal vs external)
5. Introduce valori `in_transit` per cash e asset tra broker quando linked tx hanno date diverse
6. Definisce naming pulito: `nav_value`, `book_value`, `open_cost_basis`, `market_value`
7. Usa WAC × quantity per `open_cost_basis` (no FIFO per ora)
8. Calcola `external_cash_flow` solo per flussi che entrano/escono dallo scope
9. Produce `DataQualityReport` esplicito con missing prices/FX
10. Rimanda cache a dopo la stabilizzazione
11. Propone allocation history (100% stacked) con Liquidity per cash
12. Propone grafico ABS con stacked book_value + overlay NAV

L'architettura è layered: **Scope Classifier → Daily State Builder → Derived Views**.

---

## 2. Verifica rispetto al codice reale

### File analizzati

| File | Esiste | Note |
|------|--------|------|
| `backend/app/db/models.py` | ✅ | Transaction, BrokerUserAccess, Asset, PriceHistory, FxRate |
| `backend/app/services/portfolio_service.py` | ✅ | PortfolioService con get_summary(), get_history(), get_lots() |
| `backend/app/services/fx.py` | ✅ | convert_bulk(), FXRateProvider ABC |
| `backend/app/utils/financial/roi_utils.py` | ✅ | TWRR, MWRR (XIRR via scipy), Simple ROI — pure math |
| `backend/app/utils/financial/wac_utils.py` | ✅ | compute_wac_from_txlist() — pure math |
| `backend/app/utils/financial/fifo_utils.py` | ✅ | calculate_fifo_lots() — pure math |
| `backend/app/utils/financial/valuation_utils.py` | ✅ | compute_holding_value() con quote_base_quantity |
| `backend/app/schemas/portfolio.py` | ✅ | PortfolioSummary, PortfolioHistoryPoint, AllocationItem |
| `backend/app/schemas/wac.py` | ✅ | WACMissingPairInfo, WACPreviewResultItem |
| `backend/app/api/v1/portfolio_api.py` | ✅ | Router POST /summary, /history, /wac, GET /lots |
| `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts` | ✅ | Client cache + fetch |
| `frontend/src/routes/(app)/dashboard/+page.svelte` | ✅ | GrowthChart, AllocationPieChart, KpiCard |

---

## 3. Coerenza modello dati

| Concetto nel piano | Stato nel codice | Giudizio |
|--------------------|------------------|----------|
| Transaction model unificato (quantity/amount signati) | `models.py:557-688` — esattamente come descritto | ✅ coerente |
| TransactionType enum (BUY/SELL/TRANSFER/ADJUSTMENT/FX_CONVERSION/CASH_TRANSFER/...) | `models.py:199-280` — match perfetto | ✅ coerente |
| `related_transaction_id` bidirezionale | `models.py:619-637` — bidirectional, DEFERRABLE FK | ✅ coerente |
| `cost_basis_override` + `cost_basis_currency` | `models.py:654-662` — presenti e documentati | ✅ coerente |
| `BrokerUserAccess` con `share_percentage` | `models.py:410-448` — 0.000000-1.000000, constraint | ✅ coerente |
| Asset con `classification_params` JSON | `models.py:455-549` — FAClassificationParams per sector/geo | ✅ coerente |
| Asset con `quote_base_quantity` | `models.py:497` — per BTP/bond valuation | ✅ coerente |
| PriceHistory (daily-point, close, currency) | `models.py:695-733` — UniqueConstraint per (asset_id, date) | ✅ coerente |
| WAC subsystem (iterativo, FX-aware) | `wac_utils.py:64-157`, `portfolio_service.py:73-280` | ✅ coerente |
| WAC con `cost_basis_override` su transfer-in | `portfolio_service.py:161-165` — cbo_amt usato per qty>0 non-BUY | ✅ coerente |
| WAC con `cost_basis_mode: "auto"` | `wac_utils.py:108-111` — add_at_wac effect | ✅ coerente |
| FIFO subsystem | `fifo_utils.py` — solo BUY/SELL, no TRANSFER | ⚠️ parzialmente coerente |
| FxConversionRoute model | non verificato ma presente in `fx.py` imports | ✅ coerente |

**Note tecniche:**
- Il FIFO attuale ignora TRANSFER/ADJUSTMENT — il piano dice "rimandare FIFO" il che è coerente
- Il modello dati è **completamente compatibile** con il piano senza nuovi campi DB

---

## 4. Scope-aware linked transactions

### 4.1 `related_transaction_id` — è sufficiente?

**Sì, con riserve.**

Il campo è bidirezionale (A→B e B→A). Dato un broker_id scope, l'engine può:
1. Caricare tutte le tx dello scope
2. Per ogni tx con `related_transaction_id != NULL`, fare lookup della paired tx
3. Verificare se `paired_tx.broker_id` è nello scope o fuori

Questo basta per classificare internal/external.

### 4.2 Casi ambigui

| Caso | Ambiguità | Soluzione |
|------|-----------|-----------|
| FX_CONVERSION intra-broker | Entrambe le leg sono nello stesso broker → sempre internal | Nessuna — non genera in_transit |
| ADJUSTMENT linked (asset transfer) | Il piano lo tratta come security transfer | OK, `cost_basis_override` sulla leg + dà il costo |
| ADJUSTMENT non linked (split) | `related_transaction_id = NULL` → non è un transfer | Classificare come evento interno, non external cash flow |
| Date NULL impossibili | La colonna `date` è `NOT NULL` per design | Nessuna ambiguità |

### 4.3 Linked transactions non simmetriche

**Esiste un edge case critico**: una TRANSFER ha `quantity != 0, amount = 0` su entrambe le leg. Ma un CASH_TRANSFER ha `amount != 0` su entrambe. E un FX_CONVERSION ha amounts diversi su leg diverse (perché cambi valuta).

Per FX_CONVERSION: `leg_A.amount = -1000 EUR, leg_B.amount = +1090 USD`. Queste sono **non simmetriche** per valore nominale ma simmetriche per senso economico.

**Rischio**: se l'engine somma naively gli amount delle due leg in valute diverse, il cash ledger è corretto ma in-transit deve usare la conversione FX per rappresentare un unico valore in target_currency.

### 4.4 `in_transit` senza nuovi campi DB

**Sì, implementabile.** L'in-transit è un concetto puramente runtime:

```python
# Pseudocodice
for tx in scope_transactions:
    if tx.related_transaction_id:
        paired = load(tx.related_transaction_id)
        if paired.broker_id in scope_broker_ids:
            # Internal transfer
            if tx.date != paired.date:
                # In-transit tra min_date e max_date
                departure_date = min(tx.date, paired.date)
                arrival_date = max(tx.date, paired.date)
                # → in_transit_cash_value o in_transit_asset tra le due date
```

Nessun nuovo campo DB necessario. Serve solo logica nel classificatore.

### 4.5 Nuove convenzioni necessarie

1. **Convention**: per CASH_TRANSFER/FX_CONVERSION, la leg negativa è la "partenza" e la positiva è l'"arrivo"
2. **Convention**: per TRANSFER asset, la leg con `quantity < 0` è la partenza
3. **Validazione consigliata**: verificare che linked tx abbiano broker_id diversi (già fatto in `transaction_service.py:264-272`) per TRANSFER e CASH_TRANSFER. FX_CONVERSION può essere intra-broker.

---

## 5. In-transit design review

### 5.1 Calcolo dai dati attuali

| Campo in-transit | Calcolabile? | Come |
|------------------|-------------|------|
| `in_transit_cash_value` | ✅ | `abs(departure_leg.amount)` convertito in target_currency al giorno d |
| `in_transit_asset_market_value` | ✅ | `qty_in_transit × price_on_or_before(d) × FX` |
| `in_transit_asset_cost_basis` | ✅ | `qty_in_transit × cost_basis_override` (o WAC del broker sorgente) convertito |
| `in_transit_market_value` | ✅ | Somma dei due sopra |
| `in_transit_book_value` | ✅ | `in_transit_cash_value + in_transit_asset_cost_basis` |

### 5.2 Date diverse tra leg

Il meccanismo proposto è sano:
- **Finestra in-transit** = `[departure_date + 1, arrival_date - 1]` (il giorno di partenza la leg negativa riduce il broker, il giorno di arrivo la leg positiva incrementa il broker destinatario)
- ⚠️ **Scelta di design da esplicitare**: la leg di partenza agisce sul giorno `departure_date` (cash scende quel giorno) e la leg di arrivo agisce su `arrival_date` (cash sale quel giorno). L'in-transit esiste nei giorni intermedi.

### 5.3 FX conversion in transito

Criticità: se la leg è `CASH_TRANSFER EUR → USD` con date diverse, in quale valuta rappresentare l'in_transit?

**Proposta**: usare il valore della leg di partenza convertito in target_currency. Il rationale è che i soldi sono partiti in EUR, non sono ancora arrivati in USD.

Per FX_CONVERSION (e.g., EUR→USD stesso broker con date diverse — raro ma possibile): analogo, usare la leg negativa come riferimento.

### 5.4 Security transfer in transito

- La quantità "in volo" deve essere valorizzata a market price quotidiano
- Il cost basis deve usare `cost_basis_override` della leg ricevente (se presente) o il WAC del broker sorgente
- ⚠️ **Rischio**: se `cost_basis_override` non è compilato sulla leg ricevente, servono i dati del broker sorgente. Il piano assume che `cost_basis_override` sia sempre presente per TRANSFER. La validazione attuale **non lo impone** — è opzionale in DB.

### 5.5 Missing price/FX su asset in transito

- Asset in transito con missing price → `in_transit_asset_market_value = 0` + segnalato in DataQualityReport
- Asset in transito con missing FX → stessa strategia
- Impatto su NAV: sottostimato (come per qualsiasi asset senza prezzo)

### 5.6 Impatto complessivo

L'in-transit è una **feature small-scope** (tipicamente poche ore/giorni). Implementarla correttamente è fattibile ma aggiunge complessità al Daily State Builder. Il piano è onesto nel considerarla, ma servirà un **flag di opt-in** per testing incrementale.

---

## 6. NAV / Book Value / Naming

### 6.1 Naming proposto vs codice attuale

| Nome proposto | Nome attuale nel codice | File | Breaking? |
|---------------|------------------------|------|-----------|
| `nav_value` | `nav_value` | portfolio.py:168, portfolio_service.py:325 | ❌ |
| `cash_value` | `cash_value` | portfolio.py:165, portfolio_service.py:323 | ❌ |
| `market_value` | `invested_value` | portfolio.py:166, portfolio_service.py:324 | ⚠️ **sì** |
| `open_cost_basis` | Non esiste nel DTO history | — | Nuovo campo |
| `book_value` | Non esiste nel DTO | — | Nuovo campo |
| `broker_nav_value` | Non esiste | — | Nuovo campo |
| `in_transit_*` (5 campi) | Non esistono | — | Nuovi campi |
| `unrealized_gain_loss` | calcolato in holdings ma non in history | — | Nuovo campo |

### 6.2 Campi ambigui nel codice attuale

| Campo | File | Significato attuale | Ambiguità |
|-------|------|---------------------|-----------|
| `invested_value` | `portfolio.py:166` (PortfolioHistoryPoint) | **market_value** degli asset | Nome misleading — sembra "quanto investito" |
| `total_invested` | `portfolio.py:138` (PortfolioSummary) | Somma DEPOSIT - WITHDRAWAL in base_currency | Diverso da invested_value! |
| `net_worth` | `portfolio.py:137` (PortfolioSummary) | = nav_value | Alias accettabile per UI |
| `invested_value` interno | `portfolio_service.py:324` (`_HistoryCalcPoint`) | Placeholder per market_value | Confusione con total_invested |

### 6.3 Strategia di breaking change

Data la giovinezza del progetto, la strategia consigliata è:

1. **Rinominare `invested_value` → `market_value`** in PortfolioHistoryPoint
2. Aggiungere i nuovi campi come **Optional** nel DTO (nullable) per transizione
3. Il frontend GrowthChart usa i campi dal DTO generato Zodios → dopo `./dev.py api sync` il tipo cambierà automaticamente
4. **Non mantenere retrocompatibilità** — breaking change netto dato che non ci sono consumer esterni

---

## 7. WAC e open_cost_basis

### 7.1 Formula verificata

```
open_cost_basis(asset, broker, date) = WAC(asset, broker, date) × quantity_held(asset, broker, date)
```

### 7.2 Verifica punti critici

| Punto | Stato | Note |
|-------|-------|------|
| WAC è storico o solo as-of? | **As-of** (`compute_wac_iterative` prende `as_of_date`) | Corretto per il piano — serve WAC per ogni giorno rilevante |
| WAC ha currency propria? | ✅ `wac_result.wac.code` restituisce la valuta | Piano dice "usare wac.code come sorgente" — corretto |
| Rischio doppia conversione FX | ⚠️ **Sì** — WAC è già in target_currency del WAC, poi l'engine deve convertire in target_currency della query | Serve chiarezza su chi converte |
| WAC include fee? | **No** — le fee sono tx separate con `quantity=0` | Non entrano nel WAC per design |
| WAC gestisce transfer-in con `cost_basis_override` | ✅ `portfolio_service.py:161-165` — usa `cbo_amt` per qty>0 non-BUY | Corretto |
| WAC gestisce adjustment/split | ⚠️ Parziale — `cost_basis_mode="auto"` aggiunge a WAC corrente | Ok per split (add_at_wac) |
| WAC e quantity possono divergere | ✅ `compute_wac_from_txlist` traccia `pool_qty` internamente | Consistente |
| Serve CostBasisProvider? | **No per ora** — WAC è sufficiente; FIFO è alternativa futura | Piano coerente |

### 7.3 Criticità WAC nel nuovo engine

Il piano dice "non chiamare WAC per ogni giorno" e propone forward-fill:

```
WAC aggiornato solo a transazioni rilevanti
forward-fill tra una transazione e la successiva
```

Attualmente `compute_wac_iterative` fa una query DB completa ogni chiamata. Per il Daily State Builder servono:

1. **Calcolare WAC una volta** all'inizio (as_of = last day della finestra)
2. **Estrarre i punti intermedi** dalla lista `qualifying_txs` (ogni punto ha `running_wac`)
3. Forward-fill tra un punto e il successivo

Questo è **implementabile** con la struttura attuale di `WACCalcResult.qualifying`.

### 7.4 Rischio doppia conversione

- WAC viene calcolato in una `target_currency` determinata da `determine_target_currency()` (ultima acquisizione)
- La query portfolio ha un proprio `target_currency` (es. EUR)
- Se WAC è in USD e la query è in EUR → serve conversione **una sola volta**: `open_cost_basis_EUR = WAC_USD × qty × FX(USD/EUR, date)`
- Il piano è corretto nel dire "usare `wac_result.wac.code` come valuta sorgente"

---

## 8. Market value e price handling

### 8.1 Formula verificata

```python
# Codice attuale (portfolio_service.py:955-959)
raw_market_value = compute_holding_value(qty, price, quote_base_map.get(asset_id))
# dove: compute_holding_value = (qty / quote_base_quantity) * raw_price
```

Il piano dice: `market_value = quantity × price × FX`. Il codice reale include `quote_base_quantity` (per BTP/bond). **Il piano non lo menziona esplicitamente** → va aggiunto.

### 8.2 Comportamento senza prezzo

- **Attuale**: asset escluso da market_value, aggiunto a `missing_prices_assets` (set di nomi)
- **Piano**: stessa logica ma con DTO ricco `MissingPriceAsset` con broker, quantity, cost_basis
- **Coerente** ma richiede enrichment del dato

### 8.3 Prezzo stale

- **Attuale**: `_price_on_date()` usa backward-fill — nessun flag di staleness
- **Piano**: introduce `stale_prices` in DataQualityReport
- **Da implementare**: definire threshold (es. prezzo > 7 giorni → stale)

### 8.4 Asset in transito

- Il prezzo usato deve essere `price_on_or_before(date)` per l'asset in transito — **stesso meccanismo** di un asset detenuto
- L'asset in transito deve essere valorizzato a mercato anche se non è fisicamente in nessun broker

### 8.5 BTP/bond con quote_base_quantity

- `compute_holding_value()` in `valuation_utils.py:19-26` gestisce correttamente `(qty / base) × raw_price`
- Es: BTP con 10000 EUR nominali, prezzo 98.5 su base 100 → value = (10000/100) × 98.5 = 9850
- **Il piano deve menzionare esplicitamente** `quote_base_quantity` nella formula di market_value

### 8.6 Rischio NAV sottostimato

Due cause:
1. Missing price → asset escluso dal NAV
2. Stale price → valore calcolato ma potenzialmente inaccurato

Il piano gestisce entrambi ma solo il primo impedisce il calcolo. Il secondo va segnalato senza bloccare.

---

## 9. Performance metrics

### 9.1 Situazione attuale

| Metrica | Implementata | Cash flow usati | Bug? |
|---------|-------------|-----------------|------|
| Simple ROI | ✅ `roi_utils.py:77-81` | `total_invested` (= DEPOSIT - WITHDRAWAL) | ⚠️ Non scope-aware |
| TWRR series | ✅ `roi_utils.py:183-200` | Solo DEPOSIT/WITHDRAWAL come CF | ⚠️ Bug: internal transfers count as external |
| MWRR | ✅ `roi_utils.py` via scipy | Stessi CF di TWRR | ⚠️ Stesso bug |

### 9.2 Bug attuali probabili

1. **Cash flow non scope-aware**: `portfolio_service.py:620-622`:
   ```python
   if tx.type in _CASH_FLOW_TYPES:  # solo DEPOSIT/WITHDRAWAL
       cash_flows.append(...)
   ```
   → Un CASH_TRANSFER tra due broker entrambi nello scope NON dovrebbe essere un external cash flow, ma il DEPOSIT generato dalla promozione potrebbe apparire come tale se il tipo originale resta DEPOSIT/WITHDRAWAL.

   **Mitigazione attuale accidentale**: dopo la promozione a CASH_TRANSFER, il tipo cambia e non è più in `_CASH_FLOW_TYPES`. Quindi se tutte le tx sono promoted, il bug non si manifesta. Ma DEPOSIT/WITHDRAWAL standalone (senza promozione) sono correttamente external.

2. **NAV snapshot sbagliato in get_summary**: `portfolio_service.py:806`:
   ```python
   nav_snapshots = [NAVSnapshot(d, total_nav) for d in cf_dates] + [NAVSnapshot(today, total_nav)]
   ```
   → **Bug critico**: usa `total_nav` odierno per TUTTE le date storiche! TWRR è calcolato con un NAV piatto (sbagliato). `get_history()` non ha questo bug — usa NAV giornaliero reale.

3. **Quantity tracking incompleta**: `_HOLDING_TYPES = {BUY, SELL}` — le TRANSFER e ADJUSTMENT con quantity != 0 sono ignorate. Se un asset viene trasferito OUT via TRANSFER, la quantity non scala → market_value sopravvalutato.

### 9.3 Formule da mantenere

- `calculate_twrr()` — la formula geometrica è corretta
- `calculate_twrr_series()` — iterativa O(N), corretta
- `calculate_mwrr()` — Newton-Raphson via scipy, corretta
- `calculate_simple_roi()` — formula base corretta

### 9.4 Correzioni necessarie

1. External cash flow deve escludere linked tx interne allo scope
2. NAV giornaliero (non flat) per TWRR/MWRR in get_summary()
3. Quantity tracking deve includere TRANSFER e ADJUSTMENT

### 9.5 Casi test necessari

- Internal CASH_TRANSFER tra 2 broker nello scope → external_cf = 0
- DEPOSIT standalone → external_cf = amount
- Internal TRANSFER (asset) → quantity resta nel NAV dello scope
- ROI con linked tx interno → deve essere 0% se nient'altro cambia

---

## 10. Allocation current/history

### 10.1 Allocation current

- **Attuale** (`portfolio_service.py:707-727`): usa `classification_params` (FAClassificationParams) per sector/geo/type
- **Piano**: uguale + aggiunta cash come "Liquidity" in type/sector
- **Implementabilità**: ✅ — basta aggiungere `total_cash` con label "Liquidity" a `allocation_by_type` e `allocation_by_sector`

### 10.2 Allocation history (100% stacked)

- **Non esiste** nel codice attuale
- Richiede: per ogni giorno della finestra, calcolare breakdown per type/sector/geo
- **Implementabilità**: possibile dal DailyPortfolioState proposto, dato che ogni giorno ha market_value per asset → si può derivare la distribuzione
- ⚠️ **Costo computazionale**: per 3 anni × 365 giorni × N asset × 3 dimensioni = potenzialmente costoso

### 10.3 Geography

- Piano dice: "cash non è un paese" → Unknown solo per asset non classificabili
- `FAClassificationParams.geographic_area.distribution` esiste già (`models.py:540-549`)
- ✅ Implementabile senza modifiche al data model

### 10.4 Asset in transito

- Piano: "mantengono type/sector/geography" → l'asset in transito ha ancora un asset_id → si legge la classificazione dall'Asset
- Cash in transito: Liquidity per type/sector, non rappresentata in geography
- ✅ Coerente

---

## 11. DTO/API/frontend impact

### 11.1 Breaking changes necessari

| Schema | Tipo cambio | Dettaglio |
|--------|-------------|-----------|
| `PortfolioHistoryPoint` | **Rename + add** | `invested_value` → `market_value`, add `open_cost_basis`, `book_value`, `in_transit_*`, `unrealized_gain_loss` |
| `PortfolioSummary` | **Add fields** | `open_cost_basis`, `book_value`, `in_transit_market_value`, `data_quality` (structured) |
| `AllocationItem` | **Invariato** | Schema OK |
| Nuovo: `DataQualityReport` | **Add** | missing_price_assets (ricco), stale_prices, incomplete_nav_dates |
| Nuovo: `MissingPriceAsset` | **Add** | asset_id, symbol, broker_id, quantity, open_cost_basis |
| Nuovo: `AllocationHistoryPoint` | **Add** | per 100% stacked area |

### 11.2 Compatibilità temporanea

- Rendere i nuovi campi `Optional` con default `None` — il frontend non li usa finché non aggiornato
- Rinominare `invested_value` → `market_value` è un breaking change netto (non retrocompatibile)
- Consiglio: fare il rename in un singolo PR che aggiorna frontend + backend + api sync

### 11.3 File frontend impattati

| File | Motivo |
|------|--------|
| `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts` | Type inferenza da Zodios — si aggiorna automaticamente dopo `api sync` |
| `frontend/src/routes/(app)/dashboard/+page.svelte` | Usa summary/history data |
| `frontend/src/components/dashboard/GrowthChart.svelte` | Deve usare nuovi campi per stacked area |
| `frontend/src/components/charts/AllocationPieChart.svelte` | Aggiungere toggle Ora/Storia |
| API client generato (Zodios) | Rigenerato automaticamente con `./dev.py api sync` |

---

## 12. Performance/runtime

### 12.1 Analisi carichi

| Operazione | Complessità attuale | Con nuovo engine |
|------------|--------------------|--------------------|
| Query transactions | O(B) per broker | O(B) — stessa, ma una sola pass |
| WAC per asset | O(T) per asset (tutte le tx) | O(T) una volta, poi forward-fill |
| Prices bulk load | O(1 query) per all assets/range | Stessa — `_bulk_load_asset_prices` già esiste |
| FX conversion | O(N) per singola convert_bulk | Batch con un unico `convert_bulk` — già implementato |
| MWRR (scipy) | O(N × Newton iterations) per punto | Stessa — `asyncio.to_thread` esistente |
| Allocation history | Non esiste | O(D × A) per D giorni × A asset |

### 12.2 Mitigazioni raccomandate (senza cache)

1. **Single-pass transaction scan**: caricare tutte le tx dello scope UNA volta, classificarle, poi derivare cash_delta, qty_delta, fx_requests in un loop
2. **Batch FX preloading**: il codice attuale in `get_history()` già fa bulk FX per market_value. Estendere a cash amounts in valute multiple
3. **WAC forward-fill**: calcolare WAC as_of(end_date) una volta per (asset, broker), estrarre `qualifying_txs` per rebuild giornaliero senza ri-query DB
4. **Allocation history a granularità ridotta**: se la finestra è > 1 anno, campionare settimanalmente (52 punti vs 365)
5. **Endpoint separato per allocation_history**: non includerlo in `/portfolio/history` per default — solo su richiesta esplicita
6. **Pure functions**: il Daily State Builder deve essere una funzione pura che prende i dati pre-caricati → testabile, profilabile, parallelizzabile

### 12.3 Colli di bottiglia potenziali

1. **MWRR per ogni giorno** (`calculate_mwrr_series`): N chiamate a Newton-Raphson — già mitigato con `asyncio.to_thread`
2. **FX convert_bulk con N × D richieste**: se un utente ha 10 asset in 5 valute diverse su 3 anni → ~5000 FX lookups. Il bulk load da DB è veloce ma attenzione alla memoria
3. **WAC per tutti gli asset/broker**: se un utente ha 30 asset su 3 broker = 90 WAC calculations. Con forward-fill → OK

---

## 13. Test plan minimo

| # | Test | Cosa verifica | Fixture |
|---|------|---------------|---------|
| 1 | Cash ledger | BUY riduce cash, SELL aumenta, DEPOSIT/WITHDRAWAL/DIVIDEND/FEE corretti | Broker con 8 tx diverse |
| 2 | NAV formula | `nav = market_value + cash + in_transit_market_value` | Asset con prezzo noto |
| 3 | Book value | `book = open_cost_basis + cash + in_transit_book_value` | WAC noto + cash |
| 4 | WAC / open_cost_basis | `ocb = WAC × qty` con FX conversion | Asset in USD, target EUR |
| 5 | Missing prices | Asset detenuto senza prezzo → NAV incompleto, segnalato | Asset senza PriceHistory |
| 6 | Missing FX | Conversione fallita → valore escluso, pair segnalato | Coppia EUR/XYZ inesistente |
| 7 | Internal linked tx stesso giorno | CASH_TRANSFER A→B same day → no external_cf, no in_transit | 2 broker, tx stessa data |
| 8 | Internal linked tx date diverse | CASH_TRANSFER date diverse → in_transit_cash nei giorni intermedi | 2 broker, date ≠ |
| 9 | Linked tx parzialmente nello scope | Solo una leg nello scope → external cash flow | Scope = {Broker A} |
| 10 | FX conversion linked | EUR→USD stessa data → no external_cf, cash EUR→USD corretto | FX_CONVERSION pair |
| 11 | Security transfer | TRANSFER asset A→B → qty si sposta, market_value invariato per scope completo | 2 broker, TRANSFER linked |
| 12 | BTP/bond valuation | `qty=10000, price=98.5, quote_base=100 → value=9850` | Asset con quote_base_quantity=100 |
| 13 | Allocation geography unknown | Asset senza classification_params → "Unknown" | Asset senza geo |
| 14 | ROI scope-aware | Internal transfer non altera ROI; external deposit sì | 2 scenari comparati |
| 15 | TWRR con NAV daily | TWRR calcolata su NAV giornaliero reale | Asset con price change |
| 16 | MWRR convergenza | Caso semplice con soluzione nota | 1 deposit + crescita lineare |
| 17 | share_percentage | Broker con share=0.5 → tutti i valori dimezzati | BrokerUserAccess(share=0.5) |

---

## 14. Conclusione obiettiva

### Giudizio complessivo

# ✅ APPROVATO CON MODIFICHE

Il piano è **architetturalmente solido**, ben ragionato, e largamente coerente con il data model esistente. Non richiede modifiche al DB. Le formule sono corrette. L'approccio layered (Classifier → Builder → Views) è appropriato.

Le modifiche richieste sono chiarimenti e piccole correzioni, non revisioni strutturali.

---

### Top 5 rischi tecnici

| # | Rischio | Severità | Mitigazione |
|---|---------|----------|-------------|
| 1 | **Quantity tracking incompleta** — il codice attuale ignora TRANSFER/ADJUSTMENT per le quantità detenute. Se il nuovo engine eredita questo bug, market_value è sbagliato. | Alta | Includere TRANSFER/ADJUSTMENT in qty tracking fin dal day 1 |
| 2 | **`cost_basis_override` opzionale su TRANSFER** — se non compilato, il costo in-transit dell'asset è sconosciuto. Serve fallback a WAC del broker sorgente. | Media | Implementare fallback + DataQuality warning |
| 3 | **Performance su range lunghi** — 3 anni × 365 × 30 asset × 3 allocation dimensions senza cache potrebbe essere lento | Media | Endpoint separato per allocation_history, sampling settimanale |
| 4 | **FX_CONVERSION in-transit** — semantica ambigua (quale valuta per il valore in transito?) | Bassa | Documentare: usare la leg di partenza convertita in target_ccy |
| 5 | **TWRR bug in get_summary** — usa NAV flat per tutti i giorni storici → TWRR attuale è sbagliata | Alta (bug esistente) | Corretto naturalmente dal nuovo engine (NAV daily) |

---

### Top 5 correzioni consigliate al piano

| # | Correzione |
|---|-----------|
| 1 | **Aggiungere `quote_base_quantity` alla formula di market_value**: `market_value = (qty / quote_base) × price × FX`. Attualmente il piano dice solo `qty × price × FX`. |
| 2 | **Esplicitare il fallback per `cost_basis_override` mancante su TRANSFER**: proporre `fallback = WAC_source_broker(asset, departure_date)` o `fallback = 0 + DataQuality warning`. |
| 3 | **Definire la finestra in-transit con precisione inclusiva/esclusiva**: `[departure_date + 1, arrival_date - 1]` o `(departure_date, arrival_date)` — il piano dice "tra le due date" senza specificare estremi. |
| 4 | **Chiarire WAC target_currency vs query target_currency**: due conversioni distinte. WAC ha una propria target_currency (determinata dall'ultima acquisizione). Il portfolio engine ha la target_currency della query. Serve una sola conversione: `WAC_ccy → query_ccy`. |
| 5 | **Aggiungere allocation_history come endpoint separato** (non inline in `/portfolio/history`): dati potenzialmente pesanti, non sempre necessari al frontend. Il piano lo accenna ("futuro: allocation-history se serve endpoint separato") ma dovrebbe essere la scelta primaria. |

---

### Ordine implementativo consigliato

```
Step 1: ScopeAwareTransactionClassifier (pura logica, testabile)
   → classifica tx in internal/external/in-transit

Step 2: CashLedger + QuantityLedger (pure functions)
   → cash_value(d), qty_held(asset, broker, d)
   → include TRANSFER/ADJUSTMENT in qty tracking

Step 3: WAC forward-fill integration
   → WAC per (asset, broker, end_date), estrae running_wac per ogni data

Step 4: DailyPortfolioState builder (pure function)
   → produce il vettore [DailyPortfolioState] da dati pre-caricati
   → usa batch price + batch FX

Step 5: Derived Views (summary, history, performance)
   → rewrite get_summary() e get_history() come adapter sul DailyPortfolioState
   → corregge TWRR/ROI con NAV daily reale

Step 6: DataQualityReport + MissingPriceAsset
   → enrichment del DTO

Step 7: Frontend GrowthChart + naming migration
   → rename invested_value → market_value
   → stacked book_value + overlay NAV

Step 8: Allocation history (endpoint separato)
   → 100% stacked area type/sector/geo

Step 9: In-transit (incrementale, opt-in)
   → attivare solo se la classificazione produce finestre in-transit
```

---

### Domande aperte residue

1. **Threshold per "stale price"**: quanti giorni senza aggiornamento prezzo = stale? Proposta: >5 giorni lavorativi (7 calendario).
2. **FX_CONVERSION intra-broker con date diverse**: è realisticamente possibile? Se sì, come trattare (in-transit o conversione istantanea con data = max)?
3. **ADJUSTMENT non linked**: split/gift senza `related_transaction_id` — il piano li classifica come "evento interno". Devono impattare il cash ledger? (Attualmente `amount=0` → no impatto cash, ok.)
4. **share_percentage su in-transit**: se il broker sorgente ha `share=0.5` e il destinatario `share=1.0`, quale share applicare alla fase in-transit? Proposta: share del broker sorgente (chi ha spedito).
5. **Allocation senza NAV completo**: se il NAV è incompleto (missing prices), la % allocation è calcolata sul subset valorizzabile? O si esclude il giorno? Piano non specifica.

---

*Fine review. Nessun codice modificato.*
