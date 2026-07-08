# Portfolio Engine — Status Report vs High-Level Design v2

**Data:** 2026-06-19  
**Design di riferimento:** `gpt5.5_high_level_design_v2.md`  
**Piano implementativo:** `code_agent_low_level_implementation_plan.md`

---

## 1. Sommario esecutivo

Il design v2 descrive 43 sezioni e 10 step implementativi. Di questi, **il nucleo del motore è implementato e funzionante** (classificatore, builder, views, orchestrator), ma **diversi elementi previsti non sono ancora stati realizzati o sono stati realizzati in modo parziale**. Il motore è wired solo su `get_history()`; `get_summary()` usa ancora la logica vecchia.

### Stato complessivo

| Area | Stato | Note |
|------|-------|------|
| Architettura engine | ✅ Completa | 4 classi come da design |
| ScopeAwareTransactionClassifier | ✅ Completo | 19 test |
| DailyStateBuilder | ✅ Completo | 16 test |
| DerivedViewsBuilder | ⚠️ Parziale | Manca `build_summary()`, manca `build_data_quality_report()` aggregato |
| PortfolioCalculationEngine | ✅ Completo | Orchestrator async funzionante |
| `get_history()` wiring | ✅ Completo | Usa il nuovo engine |
| `get_summary()` wiring | ❌ Non fatto | Usa ancora la logica vecchia |
| DTO / Schema | ✅ Completo | Tutti i nuovi DTO definiti |
| POST /allocation-history | ✅ Endpoint creato | Funzionante |
| GrowthChart ABS stacked | ❌ Non fatto | Solo rename serie, no stacked area |
| AllocationPanel History | ❌ Non fatto | Nessun componente frontend per allocation storica |
| DataQualityBanner | ⚠️ Parziale | MissingPriceAsset ricco funziona, ma non usa DataQualityReport |
| Performance scope-aware | ✅ Funzionante in history | Solo per `get_history()`, `get_summary()` ha ancora il bug NAV flat |

---

## 2. Analisi sezione per sezione

### §1–5: Obiettivo, cache, architettura, input, principio base

| Punto | Stato |
|-------|-------|
| PortfolioCalculationEngine unico | ✅ `portfolio_engine.py` — 1134 righe |
| No cache iniziale | ✅ Rispettato |
| DailyPortfolioState[] come cuore | ✅ Implementato |
| Summary/history/allocation come viste derivate | ⚠️ Solo history è derivata dal vettore. Summary usa ancora logica indipendente |

### §6: DailyPortfolioState

| Campo design | Implementato? | Note |
|--------------|---------------|------|
| date | ✅ | |
| cash_value | ✅ | |
| market_value | ✅ | |
| broker_nav_value | ✅ | |
| in_transit_cash_value | ✅ | |
| in_transit_asset_market_value | ✅ | |
| in_transit_market_value | ✅ | |
| nav_value | ✅ | |
| open_cost_basis | ✅ | |
| in_transit_asset_cost_basis | ✅ | |
| in_transit_book_value | ✅ | |
| book_value | ✅ | |
| unrealized_gain_loss | ✅ | |
| external_cash_flow | ✅ | |
| **internal_transfer_flow** | ❌ | **Previsto nel design, non implementato** |
| **scope_transfer_flow** | ❌ | **Previsto nel design, non implementato** |
| by_type_components | ✅ | `by_type: dict[str, Decimal]` |
| by_sector_components | ✅ | `by_sector: dict[str, Decimal]` |
| by_geography_components | ✅ | `by_geography: dict[str, Decimal]` |
| missing_price_assets | ✅ | `missing_price_asset_ids: set[int]` |
| missing_fx_pairs | ✅ | `missing_fx_pairs: set[str]` |
| stale_prices | ✅ | `stale_price_asset_ids: set[int]` |
| incomplete_nav | ✅ | `nav_complete: bool` |

**Campi mancanti:** `internal_transfer_flow` e `scope_transfer_flow` — questi campi servirebbero per debug/analytics dettagliato dei flussi. Non bloccano il funzionamento ma sono dati utili per la diagnostica.

### §7: Naming definitivo

| Rename | Stato |
|--------|-------|
| `invested_value` → `market_value` | ✅ Fatto in schema, service, frontend, test |
| Rimozione `invested_capital` | ✅ Il label i18n `investedCapital` è ancora nel file ma non più usato dalla serie |

### §8: Cash ledger

✅ **Completo.** Cumulative sum di tutti gli amount signati, senza filtro per tipo, con share_percentage. Testato.

### §9: Quantity ledger

✅ **Completo.** Include BUY, SELL, TRANSFER, ADJUSTMENT — tutto ciò con `quantity != 0`. Corregge il bug `_HOLDING_TYPES = {BUY, SELL}`.

### §10: Market value

✅ **Completo.** Formula: `(qty / quote_base_quantity) × price × FX`. Usa `compute_holding_value()` + backward-fill price + FX conversion.

### §11–12: Open cost basis + WAC forward-fill

✅ **Completo.** WAC calcolato una volta con `compute_wac_iterative(as_of_date=date_to)`, poi forward-fill via bisect. Conversione singola `wac_currency → target_currency`.

### §13: Book value

✅ **Completo.** `book_value = open_cost_basis + cash_value + in_transit_book_value`.

### §14: NAV

✅ **Completo.** `nav_value = broker_nav_value + in_transit_market_value`.

### §15: Unrealized gain/loss

✅ **Completo.** `unrealized_gain_loss = nav_value - book_value`.

### §16–17: Scope-aware linked tx + External cash flow

✅ **Completo.** ScopeAwareTransactionClassifier implementa tutte le regole: internal/external, in-transit detection, share_percentage, warnings.

### §18–23: In-transit

✅ **Completo.** Finestra `[departure_date+1, arrival_date-1]`, cash e asset in-transit, cost_basis_override con fallback WAC, share_percentage della departure leg.

### §24–27: Missing prices, stale prices, missing FX, MissingPriceAsset

| Feature | Stato |
|---------|-------|
| Missing price detection | ✅ `missing_price_asset_ids` per giorno |
| MissingPriceAsset DTO ricco | ✅ Definito e usato in `get_summary()` |
| **first_position_date nel MissingPriceAsset** | ❌ **Non implementato** — il campo non esiste nel DTO creato |
| Stale price detection (7gg) | ✅ Implementato + testato |
| Missing FX exclusion + reporting | ✅ Implementato |

### §28: DataQualityReport

| Sotto-campo | Schema DTO | Popolato dall'engine? |
|-------------|------------|----------------------|
| missing_price_assets | ✅ | ❌ Non aggregato dal DerivedViewsBuilder |
| missing_fx_pairs | ✅ | ❌ Idem |
| stale_prices | ✅ | ❌ Idem |
| incomplete_nav_dates | ✅ | ❌ |
| incomplete_book_value_dates | ✅ | ❌ |
| incomplete_allocation_dates | ✅ | ❌ |
| in_transit_cost_basis_warnings | ✅ | ❌ |
| share_mismatch_warnings | ✅ | ❌ |
| warnings | ✅ | ❌ |

**Stato:** Lo schema è definito, ma nessun codice costruisce un `DataQualityReport` aggregato dai DailyPortfolioState. I dati grezzi ci sono (per-day), ma l'aggregazione in DTO non è implementata. Il campo `data_quality` in `PortfolioSummary` e `AllocationHistoryResponse` è sempre `None`.

### §29–30: Performance metrics (TWRR/MWRR/ROI)

| Feature | Stato |
|---------|-------|
| Performance su NAV giornaliero reale | ✅ In `get_history()` |
| Performance su NAV giornaliero reale in `get_summary()` | ❌ **`get_summary()` ha ancora il bug NAV flat** |
| External cash flow scope-aware | ✅ In `get_history()` |
| Sign convention (`-external_cash_flow` per roi_utils) | ✅ Implementato |
| Period re-basing | ✅ Mantenuto da get_history() originale |

### §31: Allocation current

✅ **Implementato** in `DerivedViewsBuilder.build_allocation_current()`:
- Type: asset type + Liquidity (cash + in-transit cash)
- Sector: asset sector + Liquidity
- Geography: solo asset, cash non è paese

**Ma:** Usato solo dall'endpoint `/allocation-history`. `get_summary()` usa ancora la vecchia logica allocation.

### §32: Allocation history

| Elemento | Stato |
|----------|-------|
| Endpoint `POST /portfolio/allocation-history` | ✅ Creato |
| Query body (broker_ids, date_range, target_currency, dimension) | ✅ |
| Dimension type/sector/geography | ✅ |
| Sampling (weekly/monthly per range lunghi) | ❌ Non implementato |
| **Frontend 100% stacked area chart** | ❌ **Non implementato** |
| **Frontend toggle Now/History nell'AllocationPanel** | ❌ **Non implementato** |

### §33: Allocation con NAV incompleto

⚠️ **Parziale.** L'allocation viene calcolata sul valore disponibile, ma `incomplete_allocation_dates` non viene popolato nel `DataQualityReport`.

### §34–35: Grafico ABS

| Elemento | Design v2 | Implementato |
|----------|-----------|--------------|
| **Stacked area**: open_cost_basis + cash + in_transit_book_value | Previsto | ❌ **Non fatto** |
| **Overlay line**: nav_value | Previsto | ❌ **Non fatto** |
| Tooltip ricco (NAV, book, UGL, breakdown) | Previsto | ❌ **Non fatto** |
| Attuale implementazione | — | 3 linee: NAV (solid), Book Value (dashed), Cash (dotted) |

**Nota:** La serie "Invested Capital" → "Book Value" è stata rinominata e ora usa `book_value` dal nuovo engine. Ma la visualizzazione non è stacked area come richiesto. Resta un grafico a 3 linee con stile identico al precedente.

### §36: PortfolioHistoryPoint target

| Campo target | Implementato in schema? | Popolato dall'engine? |
|--------------|------------------------|----------------------|
| date | ✅ | ✅ |
| cash_value | ✅ | ✅ |
| market_value | ✅ | ✅ |
| broker_nav_value | ✅ | ✅ |
| in_transit_cash_value | ✅ | ✅ |
| in_transit_asset_market_value | ✅ | ✅ |
| in_transit_market_value | ✅ | ✅ |
| nav_value | ✅ | ✅ |
| open_cost_basis | ✅ | ✅ |
| in_transit_asset_cost_basis | ✅ | ✅ |
| in_transit_book_value | ✅ | ✅ |
| book_value | ✅ | ✅ |
| unrealized_gain_loss | ✅ | ✅ |
| twrr | ✅ | ✅ |
| mwrr | ✅ | ✅ |
| roi | ✅ | ✅ |

### §37: PortfolioSummary target

| Campo target | Nello schema? | Popolato? |
|--------------|---------------|-----------|
| nav_value | ❌ (usa `net_worth`) | ✅ (come `net_worth`) |
| net_worth | ✅ | ✅ |
| cash_total | ✅ | ✅ |
| market_value | ✅ (Optional) | ❌ Sempre None |
| broker_nav_value | ✅ (Optional) | ❌ Sempre None |
| in_transit_market_value | ✅ (Optional) | ❌ Sempre None |
| open_cost_basis | ✅ (Optional) | ❌ Sempre None |
| in_transit_book_value | ✅ (Optional) | ❌ Sempre None |
| book_value | ✅ (Optional) | ❌ Sempre None |
| unrealized_gain_loss | ✅ (Optional) | ❌ Sempre None |
| total_invested | ✅ | ✅ |
| total_gain_loss | ✅ | ✅ |
| simple_roi_percent | ✅ | ✅ |
| twrr_percent | ✅ | ✅ (bug NAV flat) |
| mwrr_percent | ✅ | ✅ (bug NAV flat) |
| allocation_by_type | ✅ | ✅ (vecchia logica) |
| allocation_by_sector | ✅ | ✅ (vecchia logica) |
| allocation_by_geography | ✅ | ✅ (vecchia logica) |
| missing_price_assets | ✅ (List[MissingPriceAsset]) | ✅ |
| missing_fx_pairs | ✅ | ✅ |
| data_quality | ✅ (Optional) | ❌ Sempre None |

**Nota critica:** `get_summary()` non è stato wired al nuovo engine. Tutti i nuovi Optional fields sono sempre `None`. Il bug NAV flat per TWRR/MWRR persiste in summary.

### §38: Endpoint

| Endpoint | Stato |
|----------|-------|
| POST /portfolio/summary | ✅ Esiste (ma non usa engine) |
| POST /portfolio/history | ✅ Esiste e usa engine |
| POST /portfolio/allocation-history | ✅ Creato e funzionante |

### §39: Performance runtime

| Mitigazione | Stato |
|-------------|-------|
| Single-pass transaction loading | ✅ |
| Batch FX conversion | ✅ `_preload_fx_rates()` |
| Bulk price loading | ✅ |
| WAC forward-fill | ✅ |
| Pure functions testabili | ✅ |
| Allocation history endpoint separato | ✅ |
| Sampling su range lunghi | ❌ Non implementato |

### §40: Roadmap implementativa

| Step | Stato |
|------|-------|
| Step 1 — ScopeAwareTransactionClassifier | ✅ |
| Step 2 — CashLedger + QuantityLedger | ✅ |
| Step 3 — Price / FX preload | ✅ |
| Step 4 — WAC forward-fill | ✅ |
| Step 5 — DailyPortfolioStateBuilder | ✅ |
| Step 6 — Derived views | ⚠️ Parziale (manca build_summary, build_data_quality_report) |
| Step 7 — DTO/API breaking change | ✅ |
| Step 8 — GrowthChart ABS | ❌ Non fatto (stacked area) |
| Step 9 — Allocation history endpoint | ⚠️ Backend fatto, frontend non fatto |
| Step 10 — Refinement performance | ⚠️ Fatto in history, non in summary |

### §41: Test minimi

| Test richiesto | Presente? | File |
|----------------|-----------|------|
| Cash ledger (tutti i tipi) | ✅ | `test_daily_state_builder.py` |
| Quantity ledger (TRANSFER/ADJUSTMENT) | ✅ | `test_daily_state_builder.py` |
| NAV formula | ✅ | `test_daily_state_builder.py` |
| Market value BTP/bond (quote_base) | ✅ | `test_daily_state_builder.py` |
| Book value formula | ✅ | `test_daily_state_builder.py` |
| Unrealized gain/loss | ✅ (implicito nel book value test) | |
| Missing price detection | ✅ | `test_daily_state_builder.py` |
| Missing FX exclusion | ✅ | `test_daily_state_builder.py` |
| Internal linked tx stesso giorno | ✅ | `test_scope_classifier.py` |
| Internal linked tx date diverse + in-transit | ✅ | `test_scope_classifier.py` |
| Linked tx parziale nello scope | ✅ | `test_scope_classifier.py` |
| FX conversion linked | ✅ | `test_scope_classifier.py` |
| Security transfer | ✅ | `test_scope_classifier.py` |
| Transfer cost basis (cbo + fallback) | ✅ (solo cbo testato) | `test_scope_classifier.py` |
| Allocation geography (cash non è paese) | ✅ | `test_daily_state_builder.py` |
| share_percentage dimezza tutto | ✅ | `test_daily_state_builder.py`, `test_scope_classifier.py` |
| Performance: internal transfer non altera ROI | ✅ | `test_scope_classifier.py` (no ECF) |
| **Stale price detection 7 giorni** | ✅ | `test_daily_state_builder.py` |
| **In-transit cash window** | ✅ | `test_daily_state_builder.py` |
| **Multi-currency FX** | ✅ | `test_daily_state_builder.py` |

### §42: Bug attuali da risolvere

| Bug | Risolto? | Dove |
|-----|----------|------|
| 1. get_summary TWRR/MWRR con NAV flat | ❌ **Solo in get_history()** — get_summary() ha ancora il bug |
| 2. Quantity tracking solo BUY/SELL | ✅ Engine include tutti i tipi |
| 3. invested_value naming | ✅ Rinominato market_value |
| 4. Missing prices senza warning ricco | ✅ MissingPriceAsset DTO |
| 5. Linked tx non classificate per scope | ✅ ScopeAwareTransactionClassifier |
| 6. Summary/history duplicano logiche | ⚠️ **History usa engine, summary no → divergenza persiste** |

---

## 3. Elenco completo elementi mancanti

### Backend — Logica

| # | Elemento mancante | Sezione design | Impatto | Complessità |
|---|-------------------|----------------|---------|-------------|
| 1 | **`get_summary()` wiring al nuovo engine** | §5, §37, §38 | 🔴 Alto — i nuovi campi sono tutti None, bug NAV flat persiste, allocation usa vecchia logica | Alto |
| 2 | `DerivedViewsBuilder.build_summary()` | §6 (step 6) | 🔴 Bloccante per wiring summary | Medio |
| 3 | `DerivedViewsBuilder.build_data_quality_report()` aggregato | §28 | 🟡 Medio — DataQuality sempre None | Medio |
| 4 | `internal_transfer_flow` nel DailyPortfolioState | §6 | 🟢 Basso — campo diagnostico | Basso |
| 5 | `scope_transfer_flow` nel DailyPortfolioState | §6 | 🟢 Basso — campo diagnostico | Basso |
| 6 | `first_position_date` nel MissingPriceAsset DTO | §25 | 🟢 Basso | Basso |
| 7 | Sampling allocation history (weekly/monthly) | §39 | 🟢 Basso — ottimizzazione | Basso |
| 8 | WAC fallback per in-transit cost basis (quando cbo manca) | §22 | 🟡 Medio — oggi usa solo cbo dal departure/arrival leg | Medio |

### Frontend — Visualizzazione

| # | Elemento mancante | Sezione design | Impatto | Complessità |
|---|-------------------|----------------|---------|-------------|
| 9 | **GrowthChart ABS stacked area** (open_cost_basis + cash + in_transit_book_value con overlay NAV) | §34 | 🔴 Alto — è il cambio visuale principale del design | Alto |
| 10 | **GrowthChart tooltip ricco** (NAV, book_value, UGL, breakdown) | §35 | 🟡 Medio | Medio |
| 11 | **AllocationPanel toggle Now/History** nel dashboard | §32, §86–88 del design | 🔴 Alto — il backend è pronto ma non c'è UI | Alto |
| 12 | **Allocation history 100% stacked area chart** (tipo/settore/geografia) | §32 | 🔴 Alto — componente frontend mancante | Alto |
| 13 | Geografia: nota "X% degli asset non ha classificazione" sotto la mappa | §31 | 🟡 Medio | Basso |
| 14 | DataQualityBanner unificato (usa `data_quality` da summary, non solo missing_price_assets) | §28, H.3 del piano | 🟡 Medio | Medio |

### Wiring / Integrazione

| # | Elemento mancante | Note |
|---|-------------------|------|
| 15 | `data_quality` campo in PortfolioSummary sempre None | Serve DataQualityReport aggregato |
| 16 | `data_quality` campo in AllocationHistoryResponse sempre None | Idem |
| 17 | `net_worth` come alias di `nav_value` in backend | Design dice sì, oggi `net_worth` è calcolato indipendentemente |

---

## 4. Cosa è stato modificato rispetto al design

| Modifica | Motivazione |
|----------|-------------|
| DailyPortfolioState non ha `internal_transfer_flow` e `scope_transfer_flow` | Semplificazione — non bloccanti per MVP |
| MissingPriceAsset non ha `first_position_date` | Il campo richiede un calcolo extra (`min(tx.date)` per asset/broker); rimandato |
| GrowthChart: 3 linee anziché stacked area + overlay | Complessità ECharts per stacked area con overlay richiede refactor sostanziale del componente |
| AllocationPanel: solo "Now" (pie charts), nessun toggle "History" | Richiede componente frontend nuovo (100% stacked area per allocation) |
| `get_summary()` non wired | È il metodo più complesso (~300 righe) con holdings, broker breakdown, allocation — richiede un `build_summary()` dedicato nel DerivedViewsBuilder |
| InTransitInterval non fa WAC fallback per cost_basis | Usa solo `cost_basis_override` dalle leg della coppia, non interroga il WAC del broker sorgente |
| DataQualityReport mai aggregato | I dati per-day ci sono, ma la funzione di aggregazione non è stata scritta |

---

## 5. Ordine raccomandato per completare

### Priorità 1 — Critico (funzionalità core incompleta)

1. **`get_summary()` wiring** — Scrivere `DerivedViewsBuilder.build_summary()` e convertire `get_summary()` in adapter del nuovo engine. Questo risolve il bug NAV flat residuo, popola i campi Optional, e unifica la logica.

2. **`build_data_quality_report()`** — Aggregare missing_price_ids, stale_price_ids, missing_fx_pairs, incomplete_nav_dates dai DailyPortfolioState in un DataQualityReport. Collegarlo a summary e allocation-history response.

### Priorità 2 — Frontend alto impatto

3. **AllocationPanel History** — Creare componente 100% stacked area (ECharts) + toggle Now/History nella dashboard. Il backend (`POST /allocation-history`) è pronto con supporto dimension type/sector/geography.

4. **GrowthChart ABS stacked** — Riscrivere la vista EUR con stacked area (open_cost_basis + cash_value + in_transit_book_value) e overlay line NAV. Tooltip ricco.

### Priorità 3 — Polish

5. DataQualityBanner unificato (legge `data_quality` dal summary)
6. Nota percentuale geo-classificazione sotto la mappa
7. `first_position_date` nel MissingPriceAsset
8. WAC fallback per in-transit cost basis
9. Sampling allocation history per range lunghi

---

## 6. File creati/modificati in questa implementazione

### Nuovi file

| File | Righe | Contenuto |
|------|-------|-----------|
| `backend/app/services/portfolio_engine.py` | 1134 | Engine completo: Classifier, Builder, Views, Orchestrator |
| `backend/test_scripts/.../test_portfolio_engine/__init__.py` | 0 | Package |
| `backend/test_scripts/.../test_portfolio_engine/test_scope_classifier.py` | 370 | 19 test pure |
| `backend/test_scripts/.../test_portfolio_engine/test_daily_state_builder.py` | 427 | 16 test pure |

### File modificati

| File | Tipo modifica |
|------|---------------|
| `backend/app/schemas/portfolio.py` | +5 nuovi DTO, rename, nuovi campi Optional |
| `backend/app/services/portfolio_service.py` | Rename `invested_value`→`market_value`, `get_history()` riscritto come adapter engine, `missing_price_assets` arricchito |
| `backend/app/api/v1/portfolio_api.py` | +endpoint `POST /allocation-history` |
| `backend/test_scripts/test_api/test_portfolio_api.py` | Aggiornati per rename |
| `backend/test_scripts/.../test_portfolio_service.py` | Aggiornati per rename |
| `frontend/src/lib/components/dashboard/GrowthChart.svelte` | Serie "Invested Capital"→"Book Value" |
| `frontend/src/routes/(app)/dashboard/+page.svelte` | `missing_prices_assets`→`missing_price_assets` + `.map(a => a.name)` |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | +chiave `bookValue` |
| `frontend/src/lib/api/generated.ts` | Rigenerato (api sync ×2) |

---

## 7. Test

| Suite | Risultato |
|-------|-----------|
| Portfolio engine (35 nuovi) | ✅ 35/35 |
| Portfolio service (23 esistenti) | ✅ 23/23 |
| Portfolio API (20 + 1 pre-existing fail) | ✅ 20/20 |
| Schema tests | ✅ tutti |
| Frontend svelte-check | ✅ 0 errori |
| Ruff lint | ✅ clean |
