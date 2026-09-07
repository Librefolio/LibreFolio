# AI Export — contenuti selezionabili e composizione

**Data**: 30 luglio 2026
**Fonte**: cataloghi runtime v1 (`18` dataset, `17` analisi, `45` componenti).

## Struttura comune dell'output

### Export Data

Un export dati non contiene istruzioni di analisi. Il testo copiato è composto da:

1. `Snapshot Metadata and Dataset Manifest`: selezione, dettaglio, target, periodo, manifest e statistiche;
2. `Snapshot Data`: sezioni YAML prodotte dai componenti del dataset selezionato.

### Request Analysis

Ogni prompt di analisi è composto, nell'ordine, da:

1. `Analysis Objective`: obiettivo e passaggi specifici dell'analisi;
2. `Shared Verification Instructions`: verifica di calcoli, segni, unità, periodi e separazione tra fatti e istruzioni;
3. `Response Contract`: sezioni obbligatorie della risposta;
4. `Snapshot Metadata and Dataset Manifest`;
5. `Snapshot Data`: dataset richiesti e, quando disponibili/applicabili, opzionali;
6. `Additional LibreFolio Data`: dataset separati che l'utente può esportare in seguito;
7. `Domain Notes`;
8. `User Notes`, solo se compilate;
9. `Response Language`.

Tutte le selezioni supportano `Compact`, `Standard` e `Full`, oltre ai periodi `3M`, `6M`, `1Y` e `Custom`.

## Dashboard — `/dashboard`

### Export Data (5)

#### Panoramica portafoglio

- **ID**: `portfolio.overview`
- **Contenuto**: Riepilogo, tutte le posizioni, allocazioni, liquidità, semantica e provenienza.
- **Periodo**: fotografia alla data finale
- **Componenti richiesti**: `portfolio.summary` (Portfolio summary), `portfolio.positions` (All portfolio positions), `portfolio.allocations_cash` (Allocations and cash), `portfolio.provenance` (Semantics and provenance)
- **Componenti opzionali**: nessuno

#### Performance e flussi portafoglio

- **ID**: `portfolio.performance_flows`
- **Contenuto**: Performance, contributori, flussi, redditi, commissioni, tasse e riconciliazione.
- **Periodo**: intervallo selezionato
- **Componenti richiesti**: `portfolio.performance` (Portfolio performance and contributors), `portfolio.flows_income` (Flows and income), `portfolio.fees_taxes` (Fees and taxes), `portfolio.reconciliation` (Reconciliation)
- **Componenti opzionali**: nessuno

#### Dati tecnici portafoglio

- **ID**: `portfolio.technical`
- **Contenuto**: Prezzi, rendimenti, indicatori, ampiezza, stati ed eventi per tutte le posizioni idonee.
- **Periodo**: intervallo selezionato con bucket adattivi
- **Componenti richiesti**: `portfolio.technical_prices` (Prices and returns), `portfolio.technical_indicators` (Indicators and states), `portfolio.technical_events` (Technical state-change events), `portfolio.technical_breadth` (Breadth metrics)
- **Componenti opzionali**: nessuno

#### Lotti FIFO portafoglio

- **ID**: `portfolio.fifo`
- **Contenuto**: Riepilogo FIFO, tutti i lotti aperti/parziali e quelli chiusi nel periodo AI.
- **Periodo**: intervallo selezionato
- **Componenti richiesti**: `portfolio.fifo_summary` (FIFO summary), `portfolio.fifo_lots` (FIFO open/partial/closed lots)
- **Componenti opzionali**: nessuno

#### Tutti i dati portafoglio

- **ID**: `portfolio.all_data`
- **Contenuto**: Unione deduplicata di tutti i dataset applicabili al portafoglio.
- **Periodo**: intervallo selezionato con bucket adattivi
- **Componenti richiesti**: `portfolio.summary` (Portfolio summary), `portfolio.positions` (All portfolio positions), `portfolio.allocations_cash` (Allocations and cash), `portfolio.provenance` (Semantics and provenance), `portfolio.performance` (Portfolio performance and contributors), `portfolio.flows_income` (Flows and income), `portfolio.fees_taxes` (Fees and taxes), `portfolio.reconciliation` (Reconciliation), `portfolio.technical_prices` (Prices and returns), `portfolio.technical_indicators` (Indicators and states), `portfolio.technical_breadth` (Breadth metrics), `portfolio.technical_events` (Technical state-change events), `portfolio.fifo_summary` (FIFO summary), `portfolio.fifo_lots` (FIFO open/partial/closed lots)
- **Componenti opzionali**: nessuno

### Request Analysis (7)

#### Pianificazione PAC

- **ID**: `portfolio.pac_planning`
- **Descrizione UI**: Elabora scenari neutrali di contribuzione da fatti e vincoli del portafoglio.
- **Obiettivo canonico del prompt**: Develop neutral accumulation-plan scenarios grounded in the supplied portfolio facts.
- **Passaggi richiesti**:
  1. Summarize allocation, concentration, cash, flows, and constraints relevant to recurring contributions.
  2. Identify missing budget, horizon, target, and risk-preference inputs.
  3. Present two or three conditional PAC scenarios with rationale and trade-offs.
- **Sezioni della risposta**: `LibreFolio Facts` → `PAC Scenarios` → `Evidence and Interpretation` → `External Context` → `Assumptions, Limits, and Questions`
- **Dataset richiesti**: `portfolio.overview`, `portfolio.performance_flows`
- **Dataset opzionali**: nessuno
- **Componenti richiesti espansi**: `portfolio.summary` (Portfolio summary), `portfolio.positions` (All portfolio positions), `portfolio.allocations_cash` (Allocations and cash), `portfolio.provenance` (Semantics and provenance), `portfolio.performance` (Portfolio performance and contributors), `portfolio.flows_income` (Flows and income), `portfolio.fees_taxes` (Fees and taxes), `portfolio.reconciliation` (Reconciliation)
- **Componenti opzionali espansi**: nessuno

#### Ribilanciamento portafoglio

- **ID**: `portfolio.rebalancing`
- **Descrizione UI**: Confronta la composizione corrente con gli obiettivi forniti dall’utente.
- **Obiettivo canonico del prompt**: Compare current composition with user-supplied targets and frame neutral rebalancing pathways.
- **Passaggi richiesti**:
  1. Quantify gaps only where a target or tolerance was supplied.
  2. Compare cash-flow-only, one-time, and mixed pathways.
  3. Separate measured costs from tax, timing, and execution assumptions.
- **Sezioni della risposta**: `LibreFolio Facts` → `Measured Allocation Gaps` → `Rebalancing Pathways` → `External Context` → `Assumptions, Limits, and Questions`
- **Dataset richiesti**: `portfolio.overview`
- **Dataset opzionali**: `portfolio.performance_flows`, `portfolio.technical`
- **Componenti richiesti espansi**: `portfolio.summary` (Portfolio summary), `portfolio.positions` (All portfolio positions), `portfolio.allocations_cash` (Allocations and cash), `portfolio.provenance` (Semantics and provenance)
- **Componenti opzionali espansi**: `portfolio.performance` (Portfolio performance and contributors), `portfolio.flows_income` (Flows and income), `portfolio.fees_taxes` (Fees and taxes), `portfolio.reconciliation` (Reconciliation), `portfolio.technical_prices` (Prices and returns), `portfolio.technical_indicators` (Indicators and states), `portfolio.technical_events` (Technical state-change events), `portfolio.technical_breadth` (Breadth metrics)

#### Attribuzione della performance

- **ID**: `portfolio.performance_attribution`
- **Descrizione UI**: Spiega risultati e contributori del portafoglio nel periodo AI.
- **Obiettivo canonico del prompt**: Explain the selected-period portfolio result and its contributors.
- **Passaggi richiesti**:
  1. Separate realized, unrealized, income, fees, taxes, external flows, and residual effects.
  2. Identify positive and negative contributors without truncating the supplied universe.
  3. Interpret TWRR, MWRR, and ROI only when present and with their declared semantics.
- **Sezioni della risposta**: `LibreFolio Facts` → `Positive and Negative Contributors` → `Result Reconciliation` → `Assumptions, Limits, and Questions`
- **Dataset richiesti**: `portfolio.overview`, `portfolio.performance_flows`
- **Dataset opzionali**: nessuno
- **Componenti richiesti espansi**: `portfolio.summary` (Portfolio summary), `portfolio.positions` (All portfolio positions), `portfolio.allocations_cash` (Allocations and cash), `portfolio.provenance` (Semantics and provenance), `portfolio.performance` (Portfolio performance and contributors), `portfolio.flows_income` (Flows and income), `portfolio.fees_taxes` (Fees and taxes), `portfolio.reconciliation` (Reconciliation)
- **Componenti opzionali espansi**: nessuno

#### Revisione redditi portafoglio

- **ID**: `portfolio.income_review`
- **Descrizione UI**: Esamina redditi, concentrazione, commissioni, tasse e contesto dei flussi.
- **Obiettivo canonico del prompt**: Review portfolio income, concentration, costs, and cash-flow context.
- **Passaggi richiesti**:
  1. Summarize income and material contributors.
  2. Keep gross income, fees, taxes, and net cash-flow context separate.
  3. Frame reinvestment or spending considerations conditionally on user goals.
- **Sezioni della risposta**: `LibreFolio Facts` → `Income Contributors and Concentration` → `Costs and Net Context` → `Assumptions, Limits, and Questions`
- **Dataset richiesti**: `portfolio.overview`, `portfolio.performance_flows`
- **Dataset opzionali**: nessuno
- **Componenti richiesti espansi**: `portfolio.summary` (Portfolio summary), `portfolio.positions` (All portfolio positions), `portfolio.allocations_cash` (Allocations and cash), `portfolio.provenance` (Semantics and provenance), `portfolio.performance` (Portfolio performance and contributors), `portfolio.flows_income` (Flows and income), `portfolio.fees_taxes` (Fees and taxes), `portfolio.reconciliation` (Reconciliation)
- **Componenti opzionali espansi**: nessuno

#### Revisione FIFO portafoglio

- **ID**: `portfolio.fifo_review`
- **Descrizione UI**: Esamina lotti FIFO aperti, parziali e chiusi nel periodo.
- **Obiettivo canonico del prompt**: Review portfolio FIFO lot composition over the exported period.
- **Passaggi richiesti**:
  1. Separate open/partial lots from lots closed inside the period.
  2. Keep residual cost, current value, realized, unrealized, income, fees, and taxes distinct.
  3. Describe concentration, age, valuation sources, shorts, and in-transit limits.
- **Sezioni della risposta**: `LibreFolio Facts` → `Open and Partial Lots` → `Period Closures` → `FIFO Results and Concentration` → `Assumptions, Limits, and Questions`
- **Dataset richiesti**: `portfolio.overview`, `portfolio.fifo`
- **Dataset opzionali**: nessuno
- **Componenti richiesti espansi**: `portfolio.summary` (Portfolio summary), `portfolio.positions` (All portfolio positions), `portfolio.allocations_cash` (Allocations and cash), `portfolio.provenance` (Semantics and provenance), `portfolio.fifo_summary` (FIFO summary), `portfolio.fifo_lots` (FIFO open/partial/closed lots)
- **Componenti opzionali espansi**: nessuno

#### Ampiezza tecnica

- **ID**: `portfolio.technical_breadth`
- **Descrizione UI**: Descrive l’ampiezza tecnica di tutte le posizioni idonee.
- **Obiettivo canonico del prompt**: Describe technical breadth across the complete eligible portfolio universe.
- **Passaggi richiesti**:
  1. Start with analyzed counts and weights.
  2. Separate trend, momentum, volatility, risk, and event evidence.
  3. Retain bucket dates and distinguish current states from historical transitions.
- **Sezioni della risposta**: `LibreFolio Facts` → `Breadth by Signal Family` → `Evidence and Interpretation` → `Assumptions, Limits, and Questions`
- **Dataset richiesti**: `portfolio.overview`, `portfolio.technical`
- **Dataset opzionali**: nessuno
- **Componenti richiesti espansi**: `portfolio.summary` (Portfolio summary), `portfolio.positions` (All portfolio positions), `portfolio.allocations_cash` (Allocations and cash), `portfolio.provenance` (Semantics and provenance), `portfolio.technical_prices` (Prices and returns), `portfolio.technical_indicators` (Indicators and states), `portfolio.technical_events` (Technical state-change events), `portfolio.technical_breadth` (Breadth metrics)
- **Componenti opzionali espansi**: nessuno

#### Descrizione portafoglio

- **ID**: `portfolio.description`
- **Descrizione UI**: Crea una descrizione neutrale e concisa dai fatti del portafoglio.
- **Obiettivo canonico del prompt**: Produce a concise neutral portfolio description from supplied facts.
- **Passaggi richiesti**:
  1. Summarize composition, cash, capital, performance, and concentration.
  2. Keep measured facts, notes, technical context, and assumptions separate.
  3. State coverage, stale values, and unresolved questions.
- **Sezioni della risposta**: `LibreFolio Facts` → `Composition and Concentration` → `Performance and Technical Context` → `Assumptions, Limits, and Questions`
- **Dataset richiesti**: `portfolio.overview`
- **Dataset opzionali**: `portfolio.performance_flows`, `portfolio.technical`
- **Componenti richiesti espansi**: `portfolio.summary` (Portfolio summary), `portfolio.positions` (All portfolio positions), `portfolio.allocations_cash` (Allocations and cash), `portfolio.provenance` (Semantics and provenance)
- **Componenti opzionali espansi**: `portfolio.performance` (Portfolio performance and contributors), `portfolio.flows_income` (Flows and income), `portfolio.fees_taxes` (Fees and taxes), `portfolio.reconciliation` (Reconciliation), `portfolio.technical_prices` (Prices and returns), `portfolio.technical_indicators` (Indicators and states), `portfolio.technical_events` (Technical state-change events), `portfolio.technical_breadth` (Breadth metrics)

## Dettaglio broker — `/brokers/{id}`

### Export Data (5)

#### Panoramica broker

- **ID**: `broker.overview`
- **Contenuto**: Riepilogo broker, tutte le posizioni, allocazione, concentrazione e provenienza.
- **Periodo**: fotografia alla data finale
- **Componenti richiesti**: `broker.summary` (Broker summary), `broker.positions` (All broker positions), `broker.allocation_concentration` (Allocation and concentration), `broker.provenance` (Semantics and provenance)
- **Componenti opzionali**: nessuno

#### Performance e flussi broker

- **ID**: `broker.performance_flows`
- **Contenuto**: Performance, contributori, flussi, redditi, costi e riconciliazione.
- **Periodo**: intervallo selezionato
- **Componenti richiesti**: `broker.performance` (Broker performance and contributors), `broker.flows_income_costs` (Flows, income and costs), `broker.reconciliation` (Reconciliation)
- **Componenti opzionali**: nessuno

#### Dati tecnici broker

- **ID**: `broker.technical`
- **Contenuto**: Indicatori, ampiezza, stati ed eventi limitati al broker.
- **Periodo**: intervallo selezionato con bucket adattivi
- **Componenti richiesti**: `broker.technical_indicators` (Indicators and states), `broker.technical_events` (Technical state-change events), `broker.technical_breadth` (Breadth metrics)
- **Componenti opzionali**: nessuno

#### Lotti FIFO broker

- **ID**: `broker.fifo`
- **Contenuto**: Tutti i lotti FIFO applicabili nel broker selezionato.
- **Periodo**: intervallo selezionato
- **Componenti richiesti**: `broker.fifo_lots` (All applicable FIFO lots)
- **Componenti opzionali**: nessuno

#### Tutti i dati broker

- **ID**: `broker.all_data`
- **Contenuto**: Unione deduplicata di tutti i dataset applicabili al broker.
- **Periodo**: intervallo selezionato con bucket adattivi
- **Componenti richiesti**: `broker.summary` (Broker summary), `broker.positions` (All broker positions), `broker.allocation_concentration` (Allocation and concentration), `broker.provenance` (Semantics and provenance), `broker.performance` (Broker performance and contributors), `broker.flows_income_costs` (Flows, income and costs), `broker.reconciliation` (Reconciliation), `broker.technical_indicators` (Indicators and states), `broker.technical_breadth` (Breadth metrics), `broker.technical_events` (Technical state-change events), `broker.fifo_lots` (All applicable FIFO lots)
- **Componenti opzionali**: nessuno

### Request Analysis (4)

#### Revisione broker

- **ID**: `broker.review`
- **Descrizione UI**: Esamina posizioni, liquidità, performance, costi, FIFO e concentrazione.
- **Obiettivo canonico del prompt**: Provide a neutral review of the selected broker scope.
- **Passaggi richiesti**:
  1. Summarize holdings, cash, performance, flows, income, costs, FIFO, and concentration.
  2. Use technical breadth only as secondary evidence.
  3. State access, scope, and data-quality limits.
- **Sezioni della risposta**: `LibreFolio Facts` → `Holdings, Cash, and Concentration` → `Performance, Costs, Income, and FIFO` → `Evidence and Interpretation` → `Assumptions, Limits, and Questions`
- **Dataset richiesti**: `broker.overview`, `broker.performance_flows`
- **Dataset opzionali**: `broker.technical`, `broker.fifo`
- **Componenti richiesti espansi**: `broker.summary` (Broker summary), `broker.positions` (All broker positions), `broker.allocation_concentration` (Allocation and concentration), `broker.provenance` (Semantics and provenance), `broker.performance` (Broker performance and contributors), `broker.flows_income_costs` (Flows, income and costs), `broker.reconciliation` (Reconciliation)
- **Componenti opzionali espansi**: `broker.technical_indicators` (Indicators and states), `broker.technical_events` (Technical state-change events), `broker.technical_breadth` (Breadth metrics), `broker.fifo_lots` (All applicable FIFO lots)

#### Efficienza costi broker

- **ID**: `broker.cost_efficiency`
- **Descrizione UI**: Esamina commissioni e tasse rispetto al contesto di attività disponibile.
- **Obiettivo canonico del prompt**: Review fees and taxes within the selected broker scope.
- **Passaggi richiesti**:
  1. Summarize total costs and contributors.
  2. Use ratios only when the relevant activity or asset denominator is supplied.
  3. Present neutral efficiency considerations and missing context.
- **Sezioni della risposta**: `LibreFolio Facts` → `Cost Contributors and Ratios` → `Neutral Efficiency Considerations` → `Assumptions, Limits, and Questions`
- **Dataset richiesti**: `broker.overview`, `broker.performance_flows`
- **Dataset opzionali**: nessuno
- **Componenti richiesti espansi**: `broker.summary` (Broker summary), `broker.positions` (All broker positions), `broker.allocation_concentration` (Allocation and concentration), `broker.provenance` (Semantics and provenance), `broker.performance` (Broker performance and contributors), `broker.flows_income_costs` (Flows, income and costs), `broker.reconciliation` (Reconciliation)
- **Componenti opzionali espansi**: nessuno

#### Concentrazione broker

- **ID**: `broker.concentration_context`
- **Descrizione UI**: Descrive diversificazione e concentrazione nell’ambito del broker.
- **Obiettivo canonico del prompt**: Describe concentration and diversification within the selected broker scope.
- **Passaggi richiesti**:
  1. Separate position, asset-type, sector, geography, currency, and cash dimensions.
  2. Distinguish broker concentration from whole-portfolio concentration.
  3. Frame diversification choices as questions, not instructions.
- **Sezioni della risposta**: `LibreFolio Facts` → `Concentration Dimensions` → `Evidence and Interpretation` → `Assumptions, Limits, and Questions`
- **Dataset richiesti**: `broker.overview`
- **Dataset opzionali**: `broker.technical`
- **Componenti richiesti espansi**: `broker.summary` (Broker summary), `broker.positions` (All broker positions), `broker.allocation_concentration` (Allocation and concentration), `broker.provenance` (Semantics and provenance)
- **Componenti opzionali espansi**: `broker.technical_indicators` (Indicators and states), `broker.technical_events` (Technical state-change events), `broker.technical_breadth` (Breadth metrics)

#### Revisione FIFO broker

- **ID**: `broker.fifo_review`
- **Descrizione UI**: Esamina i lotti FIFO nel broker selezionato.
- **Obiettivo canonico del prompt**: Review FIFO lots within the selected broker.
- **Passaggi richiesti**:
  1. Separate open/partial lots from period closures.
  2. Keep value and result components distinct.
  3. Describe age, concentration, valuation, short, and transfer limits.
- **Sezioni della risposta**: `LibreFolio Facts` → `Open and Partial Lots` → `Period Closures` → `Lot Results, Age, and Concentration` → `Assumptions, Limits, and Questions`
- **Dataset richiesti**: `broker.overview`, `broker.fifo`
- **Dataset opzionali**: nessuno
- **Componenti richiesti espansi**: `broker.summary` (Broker summary), `broker.positions` (All broker positions), `broker.allocation_concentration` (Allocation and concentration), `broker.provenance` (Semantics and provenance), `broker.fifo_lots` (All applicable FIFO lots)
- **Componenti opzionali espansi**: nessuno

## Dettaglio asset — `/assets/{id}`

### Export Data (4)

#### Panoramica asset

- **ID**: `asset.overview`
- **Contenuto**: Identità, snapshot di mercato corrente, ambito posizione e provenienza.
- **Periodo**: fotografia alla data finale
- **Componenti richiesti**: `asset.identity` (Asset identity), `asset.market_snapshot` (Current market snapshot), `asset.position_scope` (Position scope across brokers), `asset.provenance` (Semantics and provenance)
- **Componenti opzionali**: nessuno

#### Performance posizione asset

- **ID**: `asset.position_performance`
- **Contenuto**: Posizioni per broker, costo, valore, P&L, performance e dettagli lotti applicabili.
- **Periodo**: intervallo selezionato
- **Componenti richiesti**: `asset.positions_by_broker` (Positions per broker), `asset.cost_value_pl` (Cost, value and P&L), `asset.performance` (Position performance)
- **Componenti opzionali**: `asset.lot_detail` (Applicable lot detail)

#### Dati di mercato e tecnici asset

- **ID**: `asset.market_technical`
- **Contenuto**: Bucket OHLC/rendimento, indicatori, stati ed eventi.
- **Periodo**: intervallo selezionato con bucket adattivi
- **Componenti richiesti**: `asset.ohlc_returns` (OHLC buckets and returns), `asset.indicators` (Technical indicators), `asset.states_events` (Technical states and events)
- **Componenti opzionali**: nessuno

#### Tutti i dati asset

- **ID**: `asset.all_data`
- **Contenuto**: Unione deduplicata di tutti i dataset applicabili all’asset.
- **Periodo**: intervallo selezionato con bucket adattivi
- **Componenti richiesti**: `asset.identity` (Asset identity), `asset.market_snapshot` (Current market snapshot), `asset.position_scope` (Position scope across brokers), `asset.provenance` (Semantics and provenance), `asset.positions_by_broker` (Positions per broker), `asset.cost_value_pl` (Cost, value and P&L), `asset.performance` (Position performance), `asset.ohlc_returns` (OHLC buckets and returns), `asset.indicators` (Technical indicators), `asset.states_events` (Technical states and events)
- **Componenti opzionali**: `asset.lot_detail` (Applicable lot detail)

### Request Analysis (3)

#### Analisi trend asset

- **ID**: `asset.trend_analysis`
- **Descrizione UI**: Spiega trend, momentum, volatilità, drawdown ed eventi.
- **Obiettivo canonico del prompt**: Explain the selected asset trend using market and technical evidence.
- **Passaggi richiesti**:
  1. Separate long-, medium-, and short-horizon trend, momentum, volatility, and drawdown.
  2. Use bucket extrema and their real dates where material.
  3. Treat technical states as descriptive rather than predictive.
- **Sezioni della risposta**: `LibreFolio Facts` → `Trend, Momentum, Volatility, and Drawdown` → `Technical Events` → `External Context` → `Assumptions, Limits, and Questions`
- **Dataset richiesti**: `asset.overview`, `asset.market_technical`
- **Dataset opzionali**: nessuno
- **Componenti richiesti espansi**: `asset.identity` (Asset identity), `asset.market_snapshot` (Current market snapshot), `asset.position_scope` (Position scope across brokers), `asset.provenance` (Semantics and provenance), `asset.ohlc_returns` (OHLC buckets and returns), `asset.indicators` (Technical indicators), `asset.states_events` (Technical states and events)
- **Componenti opzionali espansi**: nessuno

#### Revisione posizione

- **ID**: `asset.position_review`
- **Descrizione UI**: Esamina valore, costo, P&L, ambito broker e contesto FIFO della posizione.
- **Obiettivo canonico del prompt**: Review the current position in the selected asset.
- **Passaggi richiesti**:
  1. Summarize quantity, value, cost, P&L, broker scope, and valuation source.
  2. Separate aggregate performance from FIFO lot facts.
  3. State missing prices, estimated values, and concentration limits.
- **Sezioni della risposta**: `LibreFolio Facts` → `Cost, Value, and P&L` → `FIFO and Portfolio Role` → `Assumptions, Limits, and Questions`
- **Dataset richiesti**: `asset.overview`, `asset.position_performance`
- **Dataset opzionali**: `asset.market_technical`
- **Componenti richiesti espansi**: `asset.identity` (Asset identity), `asset.market_snapshot` (Current market snapshot), `asset.position_scope` (Position scope across brokers), `asset.provenance` (Semantics and provenance), `asset.positions_by_broker` (Positions per broker), `asset.cost_value_pl` (Cost, value and P&L), `asset.performance` (Position performance)
- **Componenti opzionali espansi**: `asset.lot_detail` (Applicable lot detail), `asset.ohlc_returns` (OHLC buckets and returns), `asset.indicators` (Technical indicators), `asset.states_events` (Technical states and events)

#### Drawdown e recupero

- **ID**: `asset.drawdown_recovery`
- **Descrizione UI**: Descrive picco, minimo, progresso del recupero e contesto tecnico.
- **Obiettivo canonico del prompt**: Describe measured drawdown and recovery state.
- **Passaggi richiesti**:
  1. Identify peak, trough, current level, magnitude, and real observation dates.
  2. Separate price recovery from trend, momentum, and volatility interpretation.
  3. State period, bucket, and coverage limits.
- **Sezioni della risposta**: `LibreFolio Facts` → `Peak, Trough, and Recovery` → `Trend and Volatility Context` → `External Context` → `Assumptions, Limits, and Questions`
- **Dataset richiesti**: `asset.overview`, `asset.market_technical`
- **Dataset opzionali**: `asset.position_performance`
- **Componenti richiesti espansi**: `asset.identity` (Asset identity), `asset.market_snapshot` (Current market snapshot), `asset.position_scope` (Position scope across brokers), `asset.provenance` (Semantics and provenance), `asset.ohlc_returns` (OHLC buckets and returns), `asset.indicators` (Technical indicators), `asset.states_events` (Technical states and events)
- **Componenti opzionali espansi**: `asset.positions_by_broker` (Positions per broker), `asset.cost_value_pl` (Cost, value and P&L), `asset.performance` (Position performance), `asset.lot_detail` (Applicable lot detail)

## Dettaglio cambio — `/fx/{pair}`

### Export Data (4)

#### Panoramica coppia FX

- **ID**: `fx.overview`
- **Contenuto**: Identità coppia, tasso corrente, percorso di conversione e provenienza.
- **Periodo**: fotografia alla data finale
- **Componenti richiesti**: `fx.pair_identity` (FX pair identity), `fx.current_rate` (Current rate), `fx.conversion_provenance` (Conversion provenance)
- **Componenti opzionali**: nessuno

#### Dati di mercato e tecnici FX

- **ID**: `fx.market_technical`
- **Contenuto**: OHLC tasso, rendimenti, volatilità, indicatori, stati ed eventi.
- **Periodo**: intervallo selezionato con bucket adattivi
- **Componenti richiesti**: `fx.rate_ohlc` (Rate OHLC), `fx.returns_volatility` (Returns and volatility), `fx.indicators` (Technical indicators), `fx.states_events` (Technical states and events)
- **Componenti opzionali**: nessuno

#### Esposizione FX diretta

- **ID**: `fx.direct_exposure`
- **Contenuto**: Collegamenti diretti base/quote a liquidità e posizioni con provenienza conversioni.
- **Periodo**: intervallo selezionato
- **Componenti richiesti**: `fx.exposure_base_quote` (Direct base/quote exposures), `fx.exposure_provenance` (Conversion provenance for exposures)
- **Componenti opzionali**: nessuno

#### Tutti i dati FX

- **ID**: `fx.all_data`
- **Contenuto**: Unione deduplicata di tutti i dataset FX applicabili.
- **Periodo**: intervallo selezionato con bucket adattivi
- **Componenti richiesti**: `fx.pair_identity` (FX pair identity), `fx.current_rate` (Current rate), `fx.conversion_provenance` (Conversion provenance), `fx.rate_ohlc` (Rate OHLC), `fx.returns_volatility` (Returns and volatility), `fx.indicators` (Technical indicators), `fx.states_events` (Technical states and events), `fx.exposure_base_quote` (Direct base/quote exposures), `fx.exposure_provenance` (Conversion provenance for exposures)
- **Componenti opzionali**: nessuno

### Request Analysis (3)

#### Revisione trend FX

- **ID**: `fx.trend_review`
- **Descrizione UI**: Spiega direzione, trend, momentum, volatilità ed eventi della coppia.
- **Obiettivo canonico del prompt**: Explain the selected FX pair trend in quote-per-base direction.
- **Passaggi richiesti**:
  1. State current rate, period movement, extrema, source, and direction semantics.
  2. Separate trend, momentum, volatility, drawdown, and events.
  3. Keep observed rate facts distinct from external interpretation.
- **Sezioni della risposta**: `LibreFolio Facts` → `Direction, Trend, Momentum, and Volatility` → `Technical Events` → `External Context` → `Assumptions, Limits, and Questions`
- **Dataset richiesti**: `fx.overview`, `fx.market_technical`
- **Dataset opzionali**: nessuno
- **Componenti richiesti espansi**: `fx.pair_identity` (FX pair identity), `fx.current_rate` (Current rate), `fx.conversion_provenance` (Conversion provenance), `fx.rate_ohlc` (Rate OHLC), `fx.returns_volatility` (Returns and volatility), `fx.indicators` (Technical indicators), `fx.states_events` (Technical states and events)
- **Componenti opzionali espansi**: nessuno

#### Tempistica conversione FX

- **ID**: `fx.conversion_timing`
- **Descrizione UI**: Fornisce scenari neutrali di tempistica della conversione nell’incertezza.
- **Obiettivo canonico del prompt**: Provide neutral conversion-timing context under uncertainty.
- **Passaggi richiesti**:
  1. Describe rate location, trend, momentum, volatility, drawdown, and events.
  2. Present multiple conditional timing approaches without point forecasts.
  3. State horizon, execution, provider, and exposure assumptions.
- **Sezioni della risposta**: `LibreFolio Facts` → `Rate and Technical Context` → `Neutral Timing Scenarios` → `External Context` → `Assumptions, Limits, and Questions`
- **Dataset richiesti**: `fx.overview`, `fx.market_technical`
- **Dataset opzionali**: `fx.direct_exposure`
- **Componenti richiesti espansi**: `fx.pair_identity` (FX pair identity), `fx.current_rate` (Current rate), `fx.conversion_provenance` (Conversion provenance), `fx.rate_ohlc` (Rate OHLC), `fx.returns_volatility` (Returns and volatility), `fx.indicators` (Technical indicators), `fx.states_events` (Technical states and events)
- **Componenti opzionali espansi**: `fx.exposure_base_quote` (Direct base/quote exposures), `fx.exposure_provenance` (Conversion provenance for exposures)

#### Impatto esposizione FX

- **ID**: `fx.exposure_impact`
- **Descrizione UI**: Descrive i collegamenti diretti di liquidità e posizioni alla coppia valutaria.
- **Obiettivo canonico del prompt**: Describe how the FX pair relates to direct linked exposure.
- **Passaggi richiesti**:
  1. Separate cash, trading-currency, and valuation-currency links.
  2. Describe conditional directional effects without forecasting.
  3. State concentration, conversion provenance, and non-look-through limits.
- **Sezioni della risposta**: `LibreFolio Facts` → `Direct Exposure Links` → `Conditional Directional Impact` → `External Context` → `Assumptions, Limits, and Questions`
- **Dataset richiesti**: `fx.overview`, `fx.direct_exposure`
- **Dataset opzionali**: `fx.market_technical`
- **Componenti richiesti espansi**: `fx.pair_identity` (FX pair identity), `fx.current_rate` (Current rate), `fx.conversion_provenance` (Conversion provenance), `fx.exposure_base_quote` (Direct base/quote exposures), `fx.exposure_provenance` (Conversion provenance for exposures)
- **Componenti opzionali espansi**: `fx.rate_ohlc` (Rate OHLC), `fx.returns_volatility` (Returns and volatility), `fx.indicators` (Technical indicators), `fx.states_events` (Technical states and events)

## Note di lettura

- `*.all_data` è l'unione dichiarativa dei dataset dello stesso dominio: non usa un builder monolitico separato.
- Un dataset opzionale amplia il contesto quando disponibile/applicabile; non cambia l'identità dell'analisi.
- I componenti tecnici usano bucket adattivi e profili di aggregazione dichiarati dai Signal Plugin.
- Le analisi non invocano direttamente un LLM: il backend compone i dati, il frontend compone e copia il prompt.
