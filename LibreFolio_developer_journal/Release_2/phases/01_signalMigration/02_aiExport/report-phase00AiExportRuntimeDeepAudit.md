# AI Export — runtime deep audit

**Data**: 30 luglio 2026
**Tipo**: indagine read-only; codice corrente come unica source of truth.
**Ambito**: runtime component-based pubblico `/api/v1/ai-export`; il vecchio task/profile stack è trattato come legacy non servito dall'endpoint.

## Executive summary

Il runtime dichiara correttamente `18` dataset, `17` analisi e `45` componenti, ma l'indagine ha confermato divergenze importanti tra catalogo, payload e promesse dei prompt.

Problemi più gravi osservati:

1. `portfolio.technical` fallisce con `503` quando lo stesso asset è detenuto in più broker: il loader produce risultati duplicati per `asset_id`, vietati da `PriceResultsResource` (`technical_shared.py:391-479`, `resources.py:17-31`).
2. La conversione prezzi Asset può lasciare punti iniziali in valuta nativa e punti successivi in target currency; `asset.ohlc_returns.currency` usa la prima valuta, mentre gli indicatori vengono resi unavailable e poi omessi (`asset_source.py:2330-2583`, `asset_fx_technical.py:73-92`). Probe reale: currency `USD`, latest close convertita in `EUR`, `0` indicatori.
3. `fx.current_rate` e quindi `fx.overview` dipendono dalla serie tecnica con warm-up massimo; una lacuna storica remota produce `503` anche quando rate corrente ed esposizione diretta sono disponibili (`fx_core.py:126-151`, `technical_shared.py:520-572`).
4. `asset.drawdown_recovery` non riceve `RISK_DRAWDOWN`: il bundle curato ha 20 indicatori ma non Drawdown; i bucket contengono solo close min/max senza date e l'applicability richiede soltanto due osservazioni (`technical_shared.py:163-205`, `runtime_service.py:372-379`).
5. I ritorni bucket prezzo e performance usano first/last interni: nei bucket giornalieri sono sempre `0` e perdono il delta dal bucket precedente (`technical_shared.py:646-656`, `portfolio_financial.py:308-345`, `broker_financial.py:316-353`).
6. Annotazioni con `observed_only=false`, `epsilon=0` e serie calendar-backfilled producono eventi su giorni sintetici e rumore numerico (`schemas/signals.py:643-650`, `signal_annotations.py:192-274`). Probe AAPL: `517` eventi, `52` nel weekend, un cross su differenza `7e-15`.
7. Omissioni di componenti/dataset opzionali e indicatori non calcolabili non sono esposte nel manifest o nei payload; `BuildContext.diagnostics` resta interno (`dependencies.py:208-216,333-359`, `composer.py:96-171`, `ai_export_runtime.py:320-389`).

Probe reali sul DB test:

| Selezione | Esito | Evidenza |
|---|---:|---|
| `portfolio.technical`, all broker, Full | 503 | duplicate asset IDs in `portfolio.price_results` |
| `portfolio.technical`, broker 5, Full | 200 | 3 asset, 20 indicatori/asset, 1.639 eventi, 2.665.012 caratteri ≈ 666.253 token |
| `asset.drawdown_recovery`, target EUR | 200 | 365 pseudo-osservazioni, currency mista, 0 indicatori, nessun Drawdown |
| `asset.drawdown_recovery`, target USD | 200 | 20 indicatori, nessun Drawdown, 894.788 caratteri ≈ 223.697 token |
| `fx.overview` | 503 | current rate accoppiato a warm-up tecnico non disponibile |
| `fx.direct_exposure` | 200 | 23 righe dirette, 9 campi per riga |
| `broker.cost_efficiency` | 200 | nessun operation count/traded notional/capitale medio |

## Dataset resolution e failure semantics

### Regole effettive

| Caso | Dataset required | Dataset optional | Manifest/API |
|---|---|---|---|
| Detail non supportato | `selection_not_applicable` 422 | dataset saltato | nessuna entry per l'optional saltato |
| Required component raises | intera richiesta `snapshot_source_failure` 503 | intero dataset optional omesso | solo component_id, retryable sempre false |
| Optional component raises | dataset incluso senza quel componente | dataset incluso senza quel componente | nessun warning/status |
| Builder ritorna payload vuoto | successo e sezione inclusa | successo e dataset incluso | manifest normale |
| Indicatore UNAVAILABLE/FAILED | componente tecnico continua; indicatore omesso | idem | nessuna diagnostica pubblica |
| Analisi non applicabile dopo build | 422 per `requires_position`, `requires_price_history`, `requires_direct_exposure` | n/a | nessuno snapshot |
| Asset inesistente | 404 solo se root cause è `AssetNotFoundError` | idem se required | `entity_not_found` |
| Altro errore sorgente/assembler | 503 | omissione se tutto il dataset è optional | `snapshot_source_failure` senza root cause |

Fonti: `composer.py:96-171`, `dependencies.py:333-378`, `runtime_service.py:432-531`, `api/v1/ai_export.py:95-179`.

### Optional dataset: verifica della regola proposta

- Tutti i dataset correnti supportano Compact/Standard/Full; quindi oggi nessun optional è escluso per detail.
- Ogni optional è tentato deterministicamente nell'ordine catalogo e incluso se i suoi componenti required costruiscono.
- Nessuna scelta dipende da token, caratteri, randomizzazione o ottimizzazione.
- Se un componente required dell'optional fallisce, l'intero optional sparisce; se fallisce un suo componente optional, il dataset resta ma è parziale.
- Il manifest contiene soltanto i dataset effettivamente inclusi e il ruolo `required|optional`; non registra dataset tentati/omessi, componenti omessi o cause.

Test di riferimento: `test_ai_export_composer.py:103-246`. Gap: manca un test esplicito “optional buildable viene incluso” e manca un test HTTP/DB reale delle omissioni.

### Successo parziale

La granularità di requiredness è solo catalogica:

- dataset → `required_component_ids` / `optional_component_ids` (`datasets/spec.py:63-169`);
- analysis → `required_dataset_ids` / `optional_dataset_ids` (`analyses/spec.py:50-132`);
- dipendenze interne di un componente sono sempre required per quel componente (`dependencies.py:362-378`).

Non esiste un contratto pubblico per `partial dataset`. Un componente che ritorna normalmente è successo, anche vuoto; una eccezione è failure. L'unico componente optional di catalogo è `asset.lot_detail`, ma la stessa semantica vale agli `*.all_data`. Questo diverge dalla semantica desiderata perché il client non può distinguere empty, partial, unavailable e technical failure.

## Compact/Standard/Full e completezza dell'universo

### Policy temporale confermata

| Detail | P | M | K | 90d | 180d | 365d |
|---|---:|---:|---:|---:|---:|---:|
| Compact | 2 | 30 | 30 | 20 | 23 | 29 |
| Standard | 2 | 30 | 14 | 26 | 33 | 46 |
| Full | 2 | 30 | 7 | 35 | 49 | 75 |

Formula e mapping: `temporal/policy.py:19-94`; conteggi e invarianti: `test_ai_export_temporal.py:68-217`.

- `D(x)=1` per offset `0..7`; il test Full conferma almeno 14 giorni recenti giornalieri.
- I bucket sono costruiti dal periodo finale verso il passato, poi restituiti oldest→newest.
- Il bucket più vecchio **inizia** esattamente alla data iniziale; quello più recente **termina** a `snapshot_as_of` (`temporal/plan.py:55-132`).
- Copertura completa, nessun gap/overlap.

### Differenze reali oltre la granularità

Nel runtime component-based non risultano top-N, selezione NAV, contributor limits, event caps, lot caps, bundle diversi per detail o trimming token. Tutte le collection sono mantenute; cambiano i bucket. Eccezioni/filtri semantici indipendenti dal detail:

- universo tecnico Portfolio/Broker = posizioni non fully-sold con `end_value != 0`, quindi non include asset venduti entro fine periodo (`technical_shared.py:391-418`);
- lotti = open/partial + chiusi con `closing_date >= period_start`; nessun cutoff fisso tre mesi (`portfolio_financial.py:517-631`, `broker_financial.py:498-547`, `asset_core.py:418-467`);
- indicatori failed/unavailable omessi;
- `asset.lot_detail` closed degradati senza closing date omessi e contati.

Il vecchio stack in `assemblers/`, `profiles/`, `sampling.py`, `technical.py` contiene ancora top-N, 7 daily+8 weekly, cap eventi e 7+3 FIFO Compact, ma non è servito dall'endpoint pubblico attuale. Restano importati alcuni helper FIFO puri (`payloads/portfolio_broker.py:24-67`).

### Nessun budget adattivo

`Composer` vieta esplicitamente il trimming (`composer.py:16-17`). La stima token è calcolata dopo il payload (`runtime_service.py:382-430`). I payload reali dimostrano che Full può superare ampiamente le finestre dei modelli.

## Inventario dei dataset

| Dataset | Domain | Period | Required components | Optional components |
|---|---|---|---|---|
| `portfolio.overview` | portfolio | as_of | `portfolio.summary`, `portfolio.positions`, `portfolio.allocations_cash`, `portfolio.provenance` | nessuno |
| `portfolio.performance_flows` | portfolio | windowed | `portfolio.performance`, `portfolio.flows_income`, `portfolio.fees_taxes`, `portfolio.reconciliation` | nessuno |
| `portfolio.technical` | portfolio | aggregated | `portfolio.technical_prices`, `portfolio.technical_indicators`, `portfolio.technical_events`, `portfolio.technical_breadth` | nessuno |
| `portfolio.fifo` | portfolio | windowed | `portfolio.fifo_summary`, `portfolio.fifo_lots` | nessuno |
| `portfolio.all_data` | portfolio | aggregated | `portfolio.summary`, `portfolio.positions`, `portfolio.allocations_cash`, `portfolio.provenance`, `portfolio.performance`, `portfolio.flows_income`, `portfolio.fees_taxes`, `portfolio.reconciliation`, `portfolio.technical_prices`, `portfolio.technical_indicators`, `portfolio.technical_breadth`, `portfolio.technical_events`, `portfolio.fifo_summary`, `portfolio.fifo_lots` | nessuno |
| `broker.overview` | broker | as_of | `broker.summary`, `broker.positions`, `broker.allocation_concentration`, `broker.provenance` | nessuno |
| `broker.performance_flows` | broker | windowed | `broker.performance`, `broker.flows_income_costs`, `broker.reconciliation` | nessuno |
| `broker.technical` | broker | aggregated | `broker.technical_indicators`, `broker.technical_events`, `broker.technical_breadth` | nessuno |
| `broker.fifo` | broker | windowed | `broker.fifo_lots` | nessuno |
| `broker.all_data` | broker | aggregated | `broker.summary`, `broker.positions`, `broker.allocation_concentration`, `broker.provenance`, `broker.performance`, `broker.flows_income_costs`, `broker.reconciliation`, `broker.technical_indicators`, `broker.technical_breadth`, `broker.technical_events`, `broker.fifo_lots` | nessuno |
| `asset.overview` | asset | as_of | `asset.identity`, `asset.market_snapshot`, `asset.position_scope`, `asset.provenance` | nessuno |
| `asset.position_performance` | asset | windowed | `asset.positions_by_broker`, `asset.cost_value_pl`, `asset.performance` | `asset.lot_detail` |
| `asset.market_technical` | asset | aggregated | `asset.ohlc_returns`, `asset.indicators`, `asset.states_events` | nessuno |
| `asset.all_data` | asset | aggregated | `asset.identity`, `asset.market_snapshot`, `asset.position_scope`, `asset.provenance`, `asset.positions_by_broker`, `asset.cost_value_pl`, `asset.performance`, `asset.ohlc_returns`, `asset.indicators`, `asset.states_events` | `asset.lot_detail` |
| `fx.overview` | fx | as_of | `fx.pair_identity`, `fx.current_rate`, `fx.conversion_provenance` | nessuno |
| `fx.market_technical` | fx | aggregated | `fx.rate_ohlc`, `fx.returns_volatility`, `fx.indicators`, `fx.states_events` | nessuno |
| `fx.direct_exposure` | fx | windowed | `fx.exposure_base_quote`, `fx.exposure_provenance` | nessuno |
| `fx.all_data` | fx | aggregated | `fx.pair_identity`, `fx.current_rate`, `fx.conversion_provenance`, `fx.rate_ohlc`, `fx.returns_volatility`, `fx.indicators`, `fx.states_events`, `fx.exposure_base_quote`, `fx.exposure_provenance` | nessuno |

## Inventario dei 45 componenti

Legenda: `?` indica campo non required nel modello Pydantic. I campi sono quelli realmente serializzati dal relativo `output_model`.

### `portfolio.summary`

- **Domain**: portfolio
- **Used by datasets**: portfolio.overview (required), portfolio.all_data (required)
- **Required sources/services**: PortfolioService.get_report / PortfolioCalculationEngine
- **Applicability**: `as_of`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=portfolio.summary].payload`
- **Scalar/object fields**: `as_of`: string; `broker_count`: integer; `cash_total`: Currency; `market_value?`: Currency | null; `mwrr_annualized_percent?`: number | string | null; `mwrr_cumulative_percent?`: number | string | null; `net_deposited_capital?`: Currency | null; `net_worth`: Currency; `open_cost_basis?`: Currency | null; `period_start`: string; `position_count`: integer; `simple_roi_percent`: number | string; `target_currency`: string; `total_deposited?`: Currency | null; `total_gain_loss`: Currency; `total_gain_loss_percent`: number | string; `total_invested`: Currency; `total_withdrawn?`: Currency | null; `twrr_percent?`: number | string | null; `unrealized_gain_loss?`: Currency | null
- **Collections**: `cash_balances?`: array<Currency> → {amount, code}
- **Collection semantics**: Ordine e completezza definiti dal builder/output model; nessun filtro per detail rilevato.
- **Temporal fields/policy**: `as_of`, `period_start`. Fotografia a snapshot_as_of = period_end.
- **Currency fields/semantics**: `cash_balances`, `cash_total`, `market_value`, `open_cost_basis`, `target_currency`, `total_gain_loss`, `total_gain_loss_percent`, `total_invested`, `unrealized_gain_loss`. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_portfolio_summary` in `backend/app/services/ai_export/components/portfolio_financial.py:145`; model `PortfolioSummaryPayload` in `backend/app/services/ai_export/components/portfolio_financial.py:119`.

### `portfolio.positions`

- **Domain**: portfolio
- **Used by datasets**: portfolio.overview (required), portfolio.all_data (required)
- **Required sources/services**: PortfolioService.get_report / PortfolioCalculationEngine
- **Applicability**: `as_of`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=portfolio.positions].payload`
- **Scalar/object fields**: `as_of`: string; `position_count`: integer; `target_currency`: string
- **Collections**: `positions?`: array<PositionRow> → {allocation_percent, asset_id, asset_name, asset_ticker, asset_type, broker_id, broker_name, current_price, current_value, gain_loss, gain_loss_percent, nav_weight_percent, quantity, valuation_source, wac_per_unit}
- **Collection semantics**: Chiave `(broker_id, asset_id)`; ordinamento crescente; nessun top-N.
- **Temporal fields/policy**: `as_of`. Fotografia a snapshot_as_of = period_end.
- **Currency fields/semantics**: `target_currency`. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_portfolio_positions` in `backend/app/services/ai_export/components/portfolio_financial.py:190`; model `PortfolioPositionsPayload` in `backend/app/services/ai_export/components/portfolio_financial.py:181`.

### `portfolio.allocations_cash`

- **Domain**: portfolio
- **Used by datasets**: portfolio.overview (required), portfolio.all_data (required)
- **Required sources/services**: PortfolioService.get_report / PortfolioCalculationEngine
- **Applicability**: `as_of`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=portfolio.allocations_cash].payload`
- **Scalar/object fields**: `as_of`: string; `cash_total`: Currency; `market_value?`: Currency | null; `target_currency`: string
- **Collections**: `by_geography?`: array<AllocationSlice> → {amount, emoji, name, percent}; `by_sector?`: array<AllocationSlice> → {amount, emoji, name, percent}; `by_type?`: array<AllocationSlice> → {amount, emoji, name, percent}; `cash_balances?`: array<Currency> → {amount, code}
- **Collection semantics**: Slice tipo/settore/geografia dal Portfolio Engine; nessun filtro locale.
- **Temporal fields/policy**: `as_of`. Fotografia a snapshot_as_of = period_end.
- **Currency fields/semantics**: `cash_balances`, `cash_total`, `market_value`, `target_currency`. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_portfolio_allocations_cash` in `backend/app/services/ai_export/components/portfolio_financial.py:217`; model `PortfolioAllocationsCashPayload` in `backend/app/services/ai_export/components/portfolio_financial.py:204`.

### `portfolio.provenance`

- **Domain**: portfolio
- **Used by datasets**: portfolio.overview (required), portfolio.all_data (required)
- **Required sources/services**: BuildScope + static runtime methodology
- **Applicability**: `none`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=portfolio.provenance].payload`
- **Scalar/object fields**: `domain`: string; `engine_source`: string; `fifo_methodology`: string; `period_end`: string; `period_start`: string; `target_currency`: string; `valuation_semantics`: string
- **Collections**: `broker_scope?`: array<integer>; `notes?`: array<ProvenanceNote> → {subject, text}
- **Collection semantics**: Ordine e completezza definiti dal builder/output model; nessun filtro per detail rilevato.
- **Temporal fields/policy**: `period_end`, `period_start`. Nessuna propria aggregazione temporale.
- **Currency fields/semantics**: `target_currency`. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: `engine_source`, `notes`, `valuation_semantics`
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_portfolio_provenance` in `backend/app/services/ai_export/components/portfolio_financial.py:265`; model `PortfolioProvenancePayload` in `backend/app/services/ai_export/components/portfolio_financial.py:251`.

### `portfolio.performance`

- **Domain**: portfolio
- **Used by datasets**: portfolio.performance_flows (required), portfolio.all_data (required)
- **Required sources/services**: PortfolioService.get_report / PortfolioCalculationEngine
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=portfolio.performance].payload`
- **Scalar/object fields**: `bucket_count`: integer; `contributor_count`: integer; `gross_gains`: Currency; `gross_losses`: Currency; `mwrr_annualized_percent?`: number | string | null; `mwrr_cumulative_percent?`: number | string | null; `period_end`: string; `period_pnl?`: Currency | null; `period_start`: string; `simple_roi_percent?`: number | string | null; `target_currency`: string; `twrr_percent?`: number | string | null
- **Collections**: `buckets?`: array<PerformanceBucketRow> → {end_date, end_value, has_data, index, max_value, min_value, net_external_flow, period_pnl, reconciliation_diff, return_percent, start_date, start_value}; `contributors?`: array<ContributionRow> → {asset_id, asset_name, asset_ticker, asset_type, broker_id, broker_name, end_value, is_fully_sold, period_fees_taxes, period_income, period_pnl, period_pnl_percent, period_realized_gain_loss, period_unrealized_delta, start_value}
- **Collection semantics**: Bucket in ordine temporale; contributor ordinati `(broker_id, asset_id)`; universo completo.
- **Temporal fields/policy**: `bucket_count`, `buckets`, `period_end`, `period_pnl`, `period_start`. Intervallo inclusivo [period_start, period_end].
- **Currency fields/semantics**: `gross_gains`, `gross_losses`, `period_pnl`, `target_currency`. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_portfolio_performance` in `backend/app/services/ai_export/components/portfolio_financial.py:348`; model `PortfolioPerformancePayload` in `backend/app/services/ai_export/components/portfolio_financial.py:289`.

### `portfolio.flows_income`

- **Domain**: portfolio
- **Used by datasets**: portfolio.performance_flows (required), portfolio.all_data (required)
- **Required sources/services**: PortfolioService.get_report / PortfolioCalculationEngine
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=portfolio.flows_income].payload`
- **Scalar/object fields**: `net_deposited_capital?`: Currency | null; `period_end`: string; `period_income?`: Currency | null; `period_net_flows?`: Currency | null; `period_start`: string; `target_currency`: string; `total_deposited?`: Currency | null; `total_withdrawn?`: Currency | null
- **Collections**: `income_effects?`: array<EffectRow> → {broker_id, broker_name, category, description, period_pnl}; `unallocated?`: array<UnallocatedRow> → {broker_id, broker_name, unallocated_fees_taxes, unallocated_income}
- **Collection semantics**: Unallocated ordinati per broker; effetti filtrati a categoria Income.
- **Temporal fields/policy**: `period_end`, `period_income`, `period_net_flows`, `period_start`. Intervallo inclusivo [period_start, period_end].
- **Currency fields/semantics**: `income_effects`, `period_income`, `target_currency`. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_portfolio_flows_income` in `backend/app/services/ai_export/components/portfolio_financial.py:394`; model `PortfolioFlowsIncomePayload` in `backend/app/services/ai_export/components/portfolio_financial.py:379`.

### `portfolio.fees_taxes`

- **Domain**: portfolio
- **Used by datasets**: portfolio.performance_flows (required), portfolio.all_data (required)
- **Required sources/services**: PortfolioService.get_report / PortfolioCalculationEngine
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=portfolio.fees_taxes].payload`
- **Scalar/object fields**: `period_end`: string; `period_fees?`: Currency | null; `period_fees_taxes?`: Currency | null; `period_start`: string; `period_taxes?`: Currency | null; `target_currency`: string
- **Collections**: `cost_effects?`: array<EffectRow> → {broker_id, broker_name, category, description, period_pnl}; `unallocated?`: array<UnallocatedRow> → {broker_id, broker_name, unallocated_fees_taxes, unallocated_income}
- **Collection semantics**: Unallocated ordinati per broker; effetti filtrati a categoria Cost.
- **Temporal fields/policy**: `period_end`, `period_fees`, `period_fees_taxes`, `period_start`, `period_taxes`. Intervallo inclusivo [period_start, period_end].
- **Currency fields/semantics**: `cost_effects`, `period_fees`, `period_fees_taxes`, `period_taxes`, `target_currency`. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_portfolio_fees_taxes` in `backend/app/services/ai_export/components/portfolio_financial.py:434`; model `PortfolioFeesTaxesPayload` in `backend/app/services/ai_export/components/portfolio_financial.py:421`.

### `portfolio.reconciliation`

- **Domain**: portfolio
- **Used by datasets**: portfolio.performance_flows (required), portfolio.all_data (required)
- **Required sources/services**: PortfolioService.get_report / PortfolioCalculationEngine
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=portfolio.reconciliation].payload`
- **Scalar/object fields**: `period_end`: string; `period_fees_taxes?`: Currency | null; `period_income?`: Currency | null; `period_other_result?`: Currency | null; `period_pnl?`: Currency | null; `period_realized_gain_loss?`: Currency | null; `period_start`: string; `period_unrealized_gain_loss_delta?`: Currency | null; `reconciled?`: boolean | null; `residual?`: Currency | null; `target_currency`: string
- **Collections**: nessuna
- **Collection semantics**: Ordine e completezza definiti dal builder/output model; nessun filtro per detail rilevato.
- **Temporal fields/policy**: `period_end`, `period_fees_taxes`, `period_income`, `period_other_result`, `period_pnl`, `period_realized_gain_loss`, `period_start`, `period_unrealized_gain_loss_delta`. Intervallo inclusivo [period_start, period_end].
- **Currency fields/semantics**: `period_fees_taxes`, `period_income`, `period_pnl`, `period_realized_gain_loss`, `period_unrealized_gain_loss_delta`, `target_currency`. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_portfolio_reconciliation` in `backend/app/services/ai_export/components/portfolio_financial.py:475`; model `PortfolioReconciliationPayload` in `backend/app/services/ai_export/components/portfolio_financial.py:459`.

### `portfolio.technical_prices`

- **Domain**: portfolio
- **Used by datasets**: portfolio.technical (required), portfolio.all_data (required)
- **Required sources/services**: PortfolioService report + AssetSourceManager.get_prices_bulk + SignalService
- **Applicability**: `aggregated`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=portfolio.technical_prices].payload`
- **Scalar/object fields**: `considered_asset_count`: integer; `eligible_asset_count`: integer
- **Collections**: `assets`: array<AssetPriceSeriesPayload> → {asset_id, buckets, currency, latest_close, latest_date, weight}
- **Collection semantics**: Asset ordinati per asset_id; universo end-of-period eleggibile, ma duplicati multi-broker oggi causano failure.
- **Temporal fields/policy**: nessuno. Periodo visibile = scope period; warm-up interno SignalService; export su BucketPlan adattivo. Meta pubblica non espone calculation_range/earliest_calculation_date.
- **Currency fields/semantics**: nessuno. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `ohlc_bucket`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_portfolio_technical_prices` in `backend/app/services/ai_export/components/portfolio_broker_technical.py:67`; model `PortfolioTechnicalPricesPayload` in `backend/app/services/ai_export/components/technical_payloads.py:109`.

### `portfolio.technical_indicators`

- **Domain**: portfolio
- **Used by datasets**: portfolio.technical (required), portfolio.all_data (required)
- **Required sources/services**: PortfolioService report + AssetSourceManager.get_prices_bulk + SignalService
- **Applicability**: `aggregated`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=portfolio.technical_indicators].payload`
- **Scalar/object fields**: `considered_asset_count`: integer; `eligible_asset_count`: integer
- **Collections**: `assets`: array<AssetIndicatorsPayload> → {asset_id, indicators, weight}
- **Collection semantics**: Asset ordinati per asset_id; indicatori in ordine bundle; righe in ordine bucket.
- **Temporal fields/policy**: nessuno. Periodo visibile = scope period; warm-up interno SignalService; export su BucketPlan adattivo. Meta pubblica non espone calculation_range/earliest_calculation_date.
- **Currency fields/semantics**: nessuno. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `signal_profile_bucket`
- **Possible omission conditions**: SignalResult UNAVAILABLE/FAILED o senza serie → indicatore omesso senza warning nel payload.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_portfolio_technical_indicators` in `backend/app/services/ai_export/components/portfolio_broker_technical.py:143`; model `UniverseIndicatorsPayload` in `backend/app/services/ai_export/components/technical_payloads.py:261`.

### `portfolio.technical_breadth`

- **Domain**: portfolio
- **Used by datasets**: portfolio.technical (required), portfolio.all_data (required)
- **Required sources/services**: PortfolioService report + AssetSourceManager.get_prices_bulk + SignalService
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=portfolio.technical_breadth].payload`
- **Scalar/object fields**: `considered_asset_count`: integer; `covered_asset_count`: integer; `eligible_asset_count`: integer; `total_weight`: number
- **Collections**: `states`: array<BreadthStateBucket> → {output_key, signal_code, state, unweighted_count, unweighted_ratio, weighted_ratio}
- **Collection semantics**: Stati ordinati per `(signal_code, output_key, state)`; denominatore per indicatore non serializzato.
- **Temporal fields/policy**: nessuno. Periodo visibile = scope period; warm-up interno SignalService; export su BucketPlan adattivo. Meta pubblica non espone calculation_range/earliest_calculation_date.
- **Currency fields/semantics**: nessuno. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Asset/indicatori non calcolabili o senza reference levels esclusi dal denominatore specifico.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_portfolio_technical_breadth` in `backend/app/services/ai_export/components/portfolio_broker_technical.py:178`; model `UniverseBreadthPayload` in `backend/app/services/ai_export/components/technical_payloads.py:350`.

### `portfolio.technical_events`

- **Domain**: portfolio
- **Used by datasets**: portfolio.technical (required), portfolio.all_data (required)
- **Required sources/services**: PortfolioService report + AssetSourceManager.get_prices_bulk + SignalService
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=portfolio.technical_events].payload`
- **Scalar/object fields**: `total_event_count`: integer
- **Collections**: `buckets`: array<TechnicalEventBucket> → {calendar_days, end_date, event_count, events, start_date}
- **Collection semantics**: Bucket temporali; eventi preservati e deduplicati per asset/istanza/key/data.
- **Temporal fields/policy**: `buckets`. Periodo visibile = scope period; warm-up interno SignalService; export su BucketPlan adattivo. Meta pubblica non espone calculation_range/earliest_calculation_date.
- **Currency fields/semantics**: nessuno. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Eventi di SignalResult non OK/PARTIAL o annotazioni unavailable assenti; nessun placeholder.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_portfolio_technical_events` in `backend/app/services/ai_export/components/portfolio_broker_technical.py:227`; model `TechnicalEventsPayload` in `backend/app/services/ai_export/components/technical_payloads.py:318`.

### `portfolio.fifo_summary`

- **Domain**: portfolio
- **Used by datasets**: portfolio.fifo (required), portfolio.all_data (required)
- **Required sources/services**: LotsAnalysisService/FifoLotEngine + asset/broker metadata
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=portfolio.fifo_summary].payload`
- **Scalar/object fields**: `asset_count`: integer; `period_end`: string; `period_start`: string; `target_currency`: string; `total_closed_lots`: integer; `total_open_lots`: integer; `total_partial_lots`: integer; `total_residual_cost_basis`: Currency
- **Collections**: `assets?`: array<FifoAssetSummaryRow> → {asset_id, asset_name, asset_ticker, closed_lot_count, has_open_position, open_lot_count, partial_lot_count, residual_cost_basis}
- **Collection semantics**: Righe asset ordinate per asset_id; conteggi su tutti i lotti eleggibili.
- **Temporal fields/policy**: `period_end`, `period_start`. Intervallo inclusivo [period_start, period_end].
- **Currency fields/semantics**: `target_currency`, `total_residual_cost_basis`. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Nessun lotto/transazione → payload vuoto valido; cutoff = period_start, non tre mesi fissi.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_portfolio_fifo_summary` in `backend/app/services/ai_export/components/portfolio_financial.py:531`; model `PortfolioFifoSummaryPayload` in `backend/app/services/ai_export/components/portfolio_financial.py:517`.

### `portfolio.fifo_lots`

- **Domain**: portfolio
- **Used by datasets**: portfolio.fifo (required), portfolio.all_data (required)
- **Required sources/services**: LotsAnalysisService/FifoLotEngine + asset/broker metadata
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=portfolio.fifo_lots].payload`
- **Scalar/object fields**: `lot_count`: integer; `period_end`: string; `period_start`: string; `target_currency`: string
- **Collections**: `lots?`: array<FifoLotRow> → {asset_id, asset_name, asset_ticker, closing_date, cumulative_proceeds, direction, fees, income, net_metrics_status, net_total_pnl, open_quantity, open_value, opening_broker_id, opening_broker_name, opening_date, opening_unit_price, original_cost, original_quantity, realized_pnl, realized_quantity, residual_cost_basis, states, status, taxes, total_pnl, unrealized_pnl, value_source}
- **Collection semantics**: Ordine `(asset_id, opening_date, lot_id interno)`; lot_id eliminato; nessun limite per detail.
- **Temporal fields/policy**: `period_end`, `period_start`. Intervallo inclusivo [period_start, period_end].
- **Currency fields/semantics**: `target_currency`. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Nessun lotto/transazione → payload vuoto valido; cutoff = period_start, non tre mesi fissi.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_portfolio_fifo_lots` in `backend/app/services/ai_export/components/portfolio_financial.py:594`; model `PortfolioFifoLotsPayload` in `backend/app/services/ai_export/components/portfolio_financial.py:584`.

### `broker.summary`

- **Domain**: broker
- **Used by datasets**: broker.overview (required), broker.all_data (required)
- **Required sources/services**: PortfolioService.get_report / PortfolioCalculationEngine
- **Applicability**: `as_of`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=broker.summary].payload`
- **Scalar/object fields**: `as_of`: string; `broker_id`: integer; `cash_total`: Currency; `market_value?`: Currency | null; `mwrr_annualized_percent?`: number | string | null; `mwrr_cumulative_percent?`: number | string | null; `net_deposited_capital?`: Currency | null; `net_worth`: Currency; `open_cost_basis?`: Currency | null; `period_start`: string; `position_count`: integer; `simple_roi_percent`: number | string; `target_currency`: string; `total_deposited?`: Currency | null; `total_gain_loss`: Currency; `total_gain_loss_percent`: number | string; `total_invested`: Currency; `total_withdrawn?`: Currency | null; `twrr_percent?`: number | string | null; `unrealized_gain_loss?`: Currency | null
- **Collections**: `cash_balances?`: array<Currency> → {amount, code}
- **Collection semantics**: Ordine e completezza definiti dal builder/output model; nessun filtro per detail rilevato.
- **Temporal fields/policy**: `as_of`, `period_start`. Fotografia a snapshot_as_of = period_end.
- **Currency fields/semantics**: `cash_balances`, `cash_total`, `market_value`, `open_cost_basis`, `target_currency`, `total_gain_loss`, `total_gain_loss_percent`, `total_invested`, `unrealized_gain_loss`. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_broker_summary` in `backend/app/services/ai_export/components/broker_financial.py:133`; model `BrokerSummaryPayload` in `backend/app/services/ai_export/components/broker_financial.py:107`.

### `broker.positions`

- **Domain**: broker
- **Used by datasets**: broker.overview (required), broker.all_data (required)
- **Required sources/services**: PortfolioService.get_report / PortfolioCalculationEngine
- **Applicability**: `as_of`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=broker.positions].payload`
- **Scalar/object fields**: `as_of`: string; `broker_id`: integer; `position_count`: integer; `target_currency`: string
- **Collections**: `positions?`: array<PositionRow> → {allocation_percent, asset_id, asset_name, asset_ticker, asset_type, broker_id, broker_name, current_price, current_value, gain_loss, gain_loss_percent, nav_weight_percent, quantity, valuation_source, wac_per_unit}
- **Collection semantics**: Chiave `(broker_id, asset_id)`; scope singolo broker; nessun top-N.
- **Temporal fields/policy**: `as_of`. Fotografia a snapshot_as_of = period_end.
- **Currency fields/semantics**: `target_currency`. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_broker_positions` in `backend/app/services/ai_export/components/broker_financial.py:179`; model `BrokerPositionsPayload` in `backend/app/services/ai_export/components/broker_financial.py:169`.

### `broker.allocation_concentration`

- **Domain**: broker
- **Used by datasets**: broker.overview (required), broker.all_data (required)
- **Required sources/services**: PortfolioService.get_report / PortfolioCalculationEngine
- **Applicability**: `as_of`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=broker.allocation_concentration].payload`
- **Scalar/object fields**: `as_of`: string; `broker_id`: integer; `cash_total`: Currency; `herfindahl_index_percent?`: number | string | null; `largest_position_weight_percent?`: number | string | null; `market_value?`: Currency | null; `position_count`: integer; `target_currency`: string
- **Collections**: `cash_balances?`: array<Currency> → {amount, code}
- **Collection semantics**: Ordine e completezza definiti dal builder/output model; nessun filtro per detail rilevato.
- **Temporal fields/policy**: `as_of`. Fotografia a snapshot_as_of = period_end.
- **Currency fields/semantics**: `cash_balances`, `cash_total`, `market_value`, `target_currency`. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_broker_allocation_concentration` in `backend/app/services/ai_export/components/broker_financial.py:220`; model `BrokerAllocationConcentrationPayload` in `backend/app/services/ai_export/components/broker_financial.py:193`.

### `broker.provenance`

- **Domain**: broker
- **Used by datasets**: broker.overview (required), broker.all_data (required)
- **Required sources/services**: BuildScope + static runtime methodology
- **Applicability**: `none`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=broker.provenance].payload`
- **Scalar/object fields**: `broker_id`: integer; `domain`: string; `engine_source`: string; `fifo_methodology`: string; `period_end`: string; `period_start`: string; `target_currency`: string; `valuation_semantics`: string
- **Collections**: `notes?`: array<ProvenanceNote> → {subject, text}
- **Collection semantics**: Ordine e completezza definiti dal builder/output model; nessun filtro per detail rilevato.
- **Temporal fields/policy**: `period_end`, `period_start`. Nessuna propria aggregazione temporale.
- **Currency fields/semantics**: `target_currency`. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: `engine_source`, `notes`, `valuation_semantics`
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_broker_provenance` in `backend/app/services/ai_export/components/broker_financial.py:271`; model `BrokerProvenancePayload` in `backend/app/services/ai_export/components/broker_financial.py:257`.

### `broker.performance`

- **Domain**: broker
- **Used by datasets**: broker.performance_flows (required), broker.all_data (required)
- **Required sources/services**: PortfolioService.get_report / PortfolioCalculationEngine
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=broker.performance].payload`
- **Scalar/object fields**: `broker_id`: integer; `bucket_count`: integer; `contributor_count`: integer; `gross_gains`: Currency; `gross_losses`: Currency; `mwrr_annualized_percent?`: number | string | null; `mwrr_cumulative_percent?`: number | string | null; `period_end`: string; `period_pnl?`: Currency | null; `period_start`: string; `simple_roi_percent?`: number | string | null; `target_currency`: string; `twrr_percent?`: number | string | null
- **Collections**: `buckets?`: array<PerformanceBucketRow> → {end_date, end_value, has_data, index, max_value, min_value, net_external_flow, period_pnl, reconciliation_diff, return_percent, start_date, start_value}; `contributors?`: array<ContributionRow> → {asset_id, asset_name, asset_ticker, asset_type, broker_id, broker_name, end_value, is_fully_sold, period_fees_taxes, period_income, period_pnl, period_pnl_percent, period_realized_gain_loss, period_unrealized_delta, start_value}
- **Collection semantics**: Bucket in ordine temporale; contributor ordinati `(broker_id, asset_id)`; universo broker completo.
- **Temporal fields/policy**: `bucket_count`, `buckets`, `period_end`, `period_pnl`, `period_start`. Intervallo inclusivo [period_start, period_end].
- **Currency fields/semantics**: `gross_gains`, `gross_losses`, `period_pnl`, `target_currency`. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_broker_performance` in `backend/app/services/ai_export/components/broker_financial.py:356`; model `BrokerPerformancePayload` in `backend/app/services/ai_export/components/broker_financial.py:296`.

### `broker.flows_income_costs`

- **Domain**: broker
- **Used by datasets**: broker.performance_flows (required), broker.all_data (required)
- **Required sources/services**: PortfolioService.get_report / PortfolioCalculationEngine
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=broker.flows_income_costs].payload`
- **Scalar/object fields**: `broker_id`: integer; `net_deposited_capital?`: Currency | null; `period_end`: string; `period_fees?`: Currency | null; `period_fees_taxes?`: Currency | null; `period_income?`: Currency | null; `period_net_flows?`: Currency | null; `period_start`: string; `period_taxes?`: Currency | null; `target_currency`: string; `total_deposited?`: Currency | null; `total_withdrawn?`: Currency | null
- **Collections**: `effects?`: array<EffectRow> → {broker_id, broker_name, category, description, period_pnl}; `unallocated?`: array<UnallocatedRow> → {broker_id, broker_name, unallocated_fees_taxes, unallocated_income}
- **Collection semantics**: Unallocated ordinati per broker; effetti Income+Cost combinati.
- **Temporal fields/policy**: `period_end`, `period_fees`, `period_fees_taxes`, `period_income`, `period_net_flows`, `period_start`, `period_taxes`. Intervallo inclusivo [period_start, period_end].
- **Currency fields/semantics**: `period_fees`, `period_fees_taxes`, `period_income`, `period_taxes`, `target_currency`. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_broker_flows_income_costs` in `backend/app/services/ai_export/components/broker_financial.py:407`; model `BrokerFlowsIncomeCostsPayload` in `backend/app/services/ai_export/components/broker_financial.py:388`.

### `broker.reconciliation`

- **Domain**: broker
- **Used by datasets**: broker.performance_flows (required), broker.all_data (required)
- **Required sources/services**: PortfolioService.get_report / PortfolioCalculationEngine
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=broker.reconciliation].payload`
- **Scalar/object fields**: `broker_id`: integer; `period_end`: string; `period_fees_taxes?`: Currency | null; `period_income?`: Currency | null; `period_other_result?`: Currency | null; `period_pnl?`: Currency | null; `period_realized_gain_loss?`: Currency | null; `period_start`: string; `period_unrealized_gain_loss_delta?`: Currency | null; `reconciled?`: boolean | null; `residual?`: Currency | null; `target_currency`: string
- **Collections**: nessuna
- **Collection semantics**: Ordine e completezza definiti dal builder/output model; nessun filtro per detail rilevato.
- **Temporal fields/policy**: `period_end`, `period_fees_taxes`, `period_income`, `period_other_result`, `period_pnl`, `period_realized_gain_loss`, `period_start`, `period_unrealized_gain_loss_delta`. Intervallo inclusivo [period_start, period_end].
- **Currency fields/semantics**: `period_fees_taxes`, `period_income`, `period_pnl`, `period_realized_gain_loss`, `period_unrealized_gain_loss_delta`, `target_currency`. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_broker_reconciliation` in `backend/app/services/ai_export/components/broker_financial.py:455`; model `BrokerReconciliationPayload` in `backend/app/services/ai_export/components/broker_financial.py:438`.

### `broker.technical_indicators`

- **Domain**: broker
- **Used by datasets**: broker.technical (required), broker.all_data (required)
- **Required sources/services**: PortfolioService report + AssetSourceManager.get_prices_bulk + SignalService
- **Applicability**: `aggregated`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=broker.technical_indicators].payload`
- **Scalar/object fields**: `considered_asset_count`: integer; `eligible_asset_count`: integer
- **Collections**: `assets`: array<AssetIndicatorsPayload> → {asset_id, indicators, weight}
- **Collection semantics**: Asset ordinati per asset_id; indicatori in ordine bundle; righe in ordine bucket.
- **Temporal fields/policy**: nessuno. Periodo visibile = scope period; warm-up interno SignalService; export su BucketPlan adattivo. Meta pubblica non espone calculation_range/earliest_calculation_date.
- **Currency fields/semantics**: nessuno. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `signal_profile_bucket`
- **Possible omission conditions**: SignalResult UNAVAILABLE/FAILED o senza serie → indicatore omesso senza warning nel payload.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_broker_technical_indicators` in `backend/app/services/ai_export/components/portfolio_broker_technical.py:147`; model `UniverseIndicatorsPayload` in `backend/app/services/ai_export/components/technical_payloads.py:261`.

### `broker.technical_breadth`

- **Domain**: broker
- **Used by datasets**: broker.technical (required), broker.all_data (required)
- **Required sources/services**: PortfolioService report + AssetSourceManager.get_prices_bulk + SignalService
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=broker.technical_breadth].payload`
- **Scalar/object fields**: `considered_asset_count`: integer; `covered_asset_count`: integer; `eligible_asset_count`: integer; `total_weight`: number
- **Collections**: `states`: array<BreadthStateBucket> → {output_key, signal_code, state, unweighted_count, unweighted_ratio, weighted_ratio}
- **Collection semantics**: Stati ordinati per `(signal_code, output_key, state)`; denominatore per indicatore non serializzato.
- **Temporal fields/policy**: nessuno. Periodo visibile = scope period; warm-up interno SignalService; export su BucketPlan adattivo. Meta pubblica non espone calculation_range/earliest_calculation_date.
- **Currency fields/semantics**: nessuno. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Asset/indicatori non calcolabili o senza reference levels esclusi dal denominatore specifico.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_broker_technical_breadth` in `backend/app/services/ai_export/components/portfolio_broker_technical.py:183`; model `UniverseBreadthPayload` in `backend/app/services/ai_export/components/technical_payloads.py:350`.

### `broker.technical_events`

- **Domain**: broker
- **Used by datasets**: broker.technical (required), broker.all_data (required)
- **Required sources/services**: PortfolioService report + AssetSourceManager.get_prices_bulk + SignalService
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=broker.technical_events].payload`
- **Scalar/object fields**: `total_event_count`: integer
- **Collections**: `buckets`: array<TechnicalEventBucket> → {calendar_days, end_date, event_count, events, start_date}
- **Collection semantics**: Bucket temporali; eventi preservati e deduplicati per asset/istanza/key/data.
- **Temporal fields/policy**: `buckets`. Periodo visibile = scope period; warm-up interno SignalService; export su BucketPlan adattivo. Meta pubblica non espone calculation_range/earliest_calculation_date.
- **Currency fields/semantics**: nessuno. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Eventi di SignalResult non OK/PARTIAL o annotazioni unavailable assenti; nessun placeholder.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_broker_technical_events` in `backend/app/services/ai_export/components/portfolio_broker_technical.py:231`; model `TechnicalEventsPayload` in `backend/app/services/ai_export/components/technical_payloads.py:318`.

### `broker.fifo_lots`

- **Domain**: broker
- **Used by datasets**: broker.fifo (required), broker.all_data (required)
- **Required sources/services**: LotsAnalysisService/FifoLotEngine + asset/broker metadata
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=broker.fifo_lots].payload`
- **Scalar/object fields**: `broker_id`: integer; `lot_count`: integer; `period_end`: string; `period_start`: string; `target_currency`: string
- **Collections**: `lots?`: array<FifoLotRow> → {asset_id, asset_name, asset_ticker, closing_date, cumulative_proceeds, direction, fees, income, net_metrics_status, net_total_pnl, open_quantity, open_value, opening_broker_id, opening_broker_name, opening_date, opening_unit_price, original_cost, original_quantity, realized_pnl, realized_quantity, residual_cost_basis, states, status, taxes, total_pnl, unrealized_pnl, value_source}
- **Collection semantics**: Ordine `(asset_id, opening_date, lot_id interno)`; scope broker; nessun limite per detail.
- **Temporal fields/policy**: `period_end`, `period_start`. Intervallo inclusivo [period_start, period_end].
- **Currency fields/semantics**: `target_currency`. Importi in target_currency; dati tecnici prezzo dichiarano una currency per asset.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Nessun lotto/transazione → payload vuoto valido; cutoff = period_start, non tre mesi fissi.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_broker_fifo_lots` in `backend/app/services/ai_export/components/broker_financial.py:509`; model `BrokerFifoLotsPayload` in `backend/app/services/ai_export/components/broker_financial.py:498`.

### `asset.identity`

- **Domain**: asset
- **Used by datasets**: asset.overview (required), asset.all_data (required)
- **Required sources/services**: Asset/provider metadata DB
- **Applicability**: `none`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=asset.identity].payload`
- **Scalar/object fields**: `active`: boolean; `asset_id`: integer; `asset_type`: string; `classification`: AssetClassification; `currency`: string; `display_name`: string; `identifiers`: AssetIdentifiers; `quote_base_quantity`: integer
- **Collections**: nessuna
- **Collection semantics**: Ordine e completezza definiti dal builder/output model; nessun filtro per detail rilevato.
- **Temporal fields/policy**: nessuno. Nessuna propria aggregazione temporale.
- **Currency fields/semantics**: `currency`. Valori portfolio/lotti in target_currency; asset.ohlc_returns dichiara una sola currency per l'intera serie.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_identity` in `backend/app/services/ai_export/components/asset_core.py:115`; model `AssetIdentityPayload` in `backend/app/services/ai_export/components/asset_payloads.py:98`.

### `asset.market_snapshot`

- **Domain**: asset
- **Used by datasets**: asset.overview (required), asset.all_data (required)
- **Required sources/services**: AssetSourceManager.get_prices_bulk + FX conversion + SignalService
- **Applicability**: `as_of`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=asset.market_snapshot].payload`
- **Scalar/object fields**: `as_of_date`: string; `asset_id`: integer; `conversion?`: AssetFxConversionProvenance | null; `converted_price?`: Currency | null; `observed?`: AssetPriceObservation | null; `target_currency`: string
- **Collections**: nessuna
- **Collection semantics**: Ordine e completezza definiti dal builder/output model; nessun filtro per detail rilevato.
- **Temporal fields/policy**: `as_of_date`. Fotografia a snapshot_as_of = period_end.
- **Currency fields/semantics**: `converted_price`, `target_currency`. Observed in valuta nativa + converted_price target con rate_date/direction.
- **Provenance/coverage fields**: `conversion`
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Nessun prezzo osservato → payload valido con observed/converted_price/conversion null.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_market_snapshot` in `backend/app/services/ai_export/components/asset_core.py:157`; model `AssetMarketSnapshotPayload` in `backend/app/services/ai_export/components/asset_payloads.py:140`.

### `asset.position_scope`

- **Domain**: asset
- **Used by datasets**: asset.overview (required), asset.all_data (required)
- **Required sources/services**: PortfolioService.get_report scoped to asset/brokers
- **Applicability**: `as_of`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=asset.position_scope].payload`
- **Scalar/object fields**: `as_of_date`: string; `asset_id`: integer; `broker_count?`: integer; `target_currency`: string; `total_quantity?`: number | string
- **Collections**: `brokers?`: array<AssetPositionScopeBroker> → {broker_id, broker_name, quantity}
- **Collection semantics**: Una riga per broker in scope; nessun peso di portafoglio.
- **Temporal fields/policy**: `as_of_date`. Fotografia a snapshot_as_of = period_end.
- **Currency fields/semantics**: `target_currency`. Valori portfolio/lotti in target_currency; asset.ohlc_returns dichiara una sola currency per l'intera serie.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Nessuna posizione/esposizione → collection vuota valida.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_position_scope` in `backend/app/services/ai_export/components/asset_core.py:201`; model `AssetPositionScopePayload` in `backend/app/services/ai_export/components/asset_payloads.py:172`.

### `asset.provenance`

- **Domain**: asset
- **Used by datasets**: asset.overview (required), asset.all_data (required)
- **Required sources/services**: Asset metadata DB + static runtime semantics
- **Applicability**: `none`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=asset.provenance].payload`
- **Scalar/object fields**: `asset_id`: integer; `price_provenance_note`: string; `provider?`: AssetProviderAssignmentInfo | null
- **Collections**: `valuation_source_semantics`: array<AssetValuationSourceSemantic> → {code, description}
- **Collection semantics**: Ordine e completezza definiti dal builder/output model; nessun filtro per detail rilevato.
- **Temporal fields/policy**: nessuno. Nessuna propria aggregazione temporale.
- **Currency fields/semantics**: `price_provenance_note`. Valori portfolio/lotti in target_currency; asset.ohlc_returns dichiara una sola currency per l'intera serie.
- **Provenance/coverage fields**: `price_provenance_note`, `valuation_source_semantics`
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_provenance` in `backend/app/services/ai_export/components/asset_core.py:225`; model `AssetProvenancePayload` in `backend/app/services/ai_export/components/asset_payloads.py:215`.

### `asset.positions_by_broker`

- **Domain**: asset
- **Used by datasets**: asset.position_performance (required), asset.all_data (required)
- **Required sources/services**: PortfolioService.get_report scoped to asset/brokers
- **Applicability**: `as_of`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=asset.positions_by_broker].payload`
- **Scalar/object fields**: `as_of_date`: string; `asset_id`: integer; `target_currency`: string
- **Collections**: `positions?`: array<AssetBrokerPosition> → {broker_id, broker_name, current_price, current_value, quantity, unrealized_gain_loss, unrealized_gain_loss_percent, valuation_source, wac_per_unit}
- **Collection semantics**: Una riga per broker; nessuna selezione per detail.
- **Temporal fields/policy**: `as_of_date`. Fotografia a snapshot_as_of = period_end.
- **Currency fields/semantics**: `target_currency`. Valori portfolio/lotti in target_currency; asset.ohlc_returns dichiara una sola currency per l'intera serie.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Nessuna posizione/esposizione → collection vuota valida.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_positions_by_broker` in `backend/app/services/ai_export/components/asset_core.py:251`; model `AssetPositionsByBrokerPayload` in `backend/app/services/ai_export/components/asset_payloads.py:252`.

### `asset.cost_value_pl`

- **Domain**: asset
- **Used by datasets**: asset.position_performance (required), asset.all_data (required)
- **Required sources/services**: PortfolioService.get_report scoped to asset/brokers
- **Applicability**: `as_of`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=asset.cost_value_pl].payload`
- **Scalar/object fields**: `as_of_date`: string; `asset_id`: integer; `coverage`: AssetAggregateCoverage; `target_currency`: string; `total_cost_basis?`: number | string | null; `total_current_value?`: number | string | null; `total_unrealized_gain_loss?`: number | string | null
- **Collections**: `brokers?`: array<AssetBrokerCostValuePl> → {broker_id, broker_name, cost_basis, current_value, quantity, unrealized_gain_loss, unrealized_gain_loss_percent, wac_per_unit}
- **Collection semantics**: Tutte le righe broker; coverage identifica quelle escluse dai totali.
- **Temporal fields/policy**: `as_of_date`. Fotografia a snapshot_as_of = period_end.
- **Currency fields/semantics**: `target_currency`, `total_cost_basis`, `total_current_value`, `total_unrealized_gain_loss`. Valori portfolio/lotti in target_currency; asset.ohlc_returns dichiara una sola currency per l'intera serie.
- **Provenance/coverage fields**: `coverage`
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_cost_value_pl` in `backend/app/services/ai_export/components/asset_core.py:285`; model `AssetCostValuePlPayload` in `backend/app/services/ai_export/components/asset_payloads.py:313`.

### `asset.performance`

- **Domain**: asset
- **Used by datasets**: asset.position_performance (required), asset.all_data (required)
- **Required sources/services**: PortfolioService.get_report scoped to asset/brokers
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=asset.performance].payload`
- **Scalar/object fields**: `asset_id`: integer; `coverage`: AssetAggregateCoverage; `period`: DateRangeModel; `target_currency`: string; `total_end_value?`: number | string | null; `total_period_pnl?`: number | string | null; `total_period_pnl_percent?`: number | string | null; `total_start_value?`: number | string | null
- **Collections**: `brokers?`: array<AssetBrokerPeriodPerformance> → {broker_id, broker_name, end_value, is_fully_sold, period_fees_taxes, period_income, period_pnl, period_pnl_percent, period_realized_gain_loss, period_unrealized_delta, start_value}
- **Collection semantics**: Tutte le righe broker; coverage identifica quelle escluse dai totali.
- **Temporal fields/policy**: `period`, `total_period_pnl`, `total_period_pnl_percent`. Intervallo inclusivo [period_start, period_end].
- **Currency fields/semantics**: `target_currency`, `total_end_value`, `total_period_pnl`, `total_period_pnl_percent`, `total_start_value`. Valori portfolio/lotti in target_currency; asset.ohlc_returns dichiara una sola currency per l'intera serie.
- **Provenance/coverage fields**: `coverage`
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_performance` in `backend/app/services/ai_export/components/asset_core.py:347`; model `AssetPerformancePayload` in `backend/app/services/ai_export/components/asset_payloads.py:358`.

### `asset.lot_detail`

- **Domain**: asset
- **Used by datasets**: asset.position_performance (optional), asset.all_data (optional)
- **Required sources/services**: LotsAnalysisService/FifoLotEngine
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=asset.lot_detail].payload`
- **Scalar/object fields**: `asset_id`: integer; `omitted_degraded_lot_count?`: integer; `period`: DateRangeModel; `target_currency`: string
- **Collections**: `lots?`: array<AssetLotDetailRow> → {closing_date, current_custody, open_quantity, opening_broker_id, opening_date, opening_unit_price, original_quantity}
- **Collection semantics**: Ordine `(opening_date, opening_broker_id)`; open/partial + chiusi nel periodo; chiusi senza closing_date omessi e contati.
- **Temporal fields/policy**: `period`. Intervallo inclusivo [period_start, period_end].
- **Currency fields/semantics**: `target_currency`. Valori portfolio/lotti in target_currency; asset.ohlc_returns dichiara una sola currency per l'intera serie.
- **Provenance/coverage fields**: `omitted_degraded_lot_count`
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Lotti chiusi prima del periodo esclusi; chiusi senza closing_date omessi e contati; failure builder omessa silenziosamente perché componente optional.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_lot_detail` in `backend/app/services/ai_export/components/asset_core.py:418`; model `AssetLotDetailPayload` in `backend/app/services/ai_export/components/asset_payloads.py:416`.

### `asset.ohlc_returns`

- **Domain**: asset
- **Used by datasets**: asset.market_technical (required), asset.all_data (required)
- **Required sources/services**: AssetSourceManager.get_prices_bulk + FX conversion + SignalService
- **Applicability**: `aggregated`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=asset.ohlc_returns].payload`
- **Scalar/object fields**: `asset_id`: integer; `currency`: string; `latest_close?`: number | null; `latest_date?`: string | null
- **Collections**: `buckets`: array<PriceBucket> → {calendar_days, end_date, first, last, maximum, minimum, observation_count, simple_return, start_date}
- **Collection semantics**: Ordine e completezza definiti dal builder/output model; nessun filtro per detail rilevato.
- **Temporal fields/policy**: `buckets`, `latest_date`. Periodo visibile = scope period; warm-up interno SignalService; export su BucketPlan adattivo. Meta pubblica non espone calculation_range/earliest_calculation_date.
- **Currency fields/semantics**: `currency`. Valori portfolio/lotti in target_currency; asset.ohlc_returns dichiara una sola currency per l'intera serie.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `ohlc_bucket`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_asset_ohlc_returns` in `backend/app/services/ai_export/components/asset_fx_technical.py:73`; model `AssetOhlcReturnsPayload` in `backend/app/services/ai_export/components/technical_payloads.py:97`.

### `asset.indicators`

- **Domain**: asset
- **Used by datasets**: asset.market_technical (required), asset.all_data (required)
- **Required sources/services**: AssetSourceManager.get_prices_bulk + FX conversion + SignalService
- **Applicability**: `aggregated`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=asset.indicators].payload`
- **Scalar/object fields**: nessuno
- **Collections**: `indicators`: array<IndicatorTablePayload> → {category, columns, instance_id, rows, semantic_description, semantic_id, signal_code}
- **Collection semantics**: Ordine e completezza definiti dal builder/output model; nessun filtro per detail rilevato.
- **Temporal fields/policy**: nessuno. Periodo visibile = scope period; warm-up interno SignalService; export su BucketPlan adattivo. Meta pubblica non espone calculation_range/earliest_calculation_date.
- **Currency fields/semantics**: nessuno. Valori portfolio/lotti in target_currency; asset.ohlc_returns dichiara una sola currency per l'intera serie.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `signal_profile_bucket`
- **Possible omission conditions**: SignalResult UNAVAILABLE/FAILED o senza serie → indicatore omesso senza warning nel payload.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_asset_indicators` in `backend/app/services/ai_export/components/asset_fx_technical.py:112`; model `SingleTargetIndicatorsPayload` in `backend/app/services/ai_export/components/technical_payloads.py:271`.

### `asset.states_events`

- **Domain**: asset
- **Used by datasets**: asset.market_technical (required), asset.all_data (required)
- **Required sources/services**: AssetSourceManager.get_prices_bulk + FX conversion + SignalService
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=asset.states_events].payload`
- **Scalar/object fields**: `total_event_count`: integer
- **Collections**: `buckets`: array<TechnicalEventBucket> → {calendar_days, end_date, event_count, events, start_date}
- **Collection semantics**: Bucket temporali; eventi preservati; nessun cap.
- **Temporal fields/policy**: `buckets`. Periodo visibile = scope period; warm-up interno SignalService; export su BucketPlan adattivo. Meta pubblica non espone calculation_range/earliest_calculation_date.
- **Currency fields/semantics**: nessuno. Valori portfolio/lotti in target_currency; asset.ohlc_returns dichiara una sola currency per l'intera serie.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Eventi di SignalResult non OK/PARTIAL o annotazioni unavailable assenti; nessun placeholder.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_asset_states_events` in `backend/app/services/ai_export/components/asset_fx_technical.py:139`; model `TechnicalEventsPayload` in `backend/app/services/ai_export/components/technical_payloads.py:318`.

### `fx.pair_identity`

- **Domain**: fx
- **Used by datasets**: fx.overview (required), fx.all_data (required)
- **Required sources/services**: BuildScope only
- **Applicability**: `none`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=fx.pair_identity].payload`
- **Scalar/object fields**: `base_currency`: string; `direction`: FxRateDirection; `quote_currency`: string; `rate_semantics?`: string; `stored_base_currency`: string; `stored_quote_currency`: string
- **Collections**: nessuna
- **Collection semantics**: Ordine e completezza definiti dal builder/output model; nessun filtro per detail rilevato.
- **Temporal fields/policy**: nessuno. Nessuna propria aggregazione temporale.
- **Currency fields/semantics**: `base_currency`, `quote_currency`, `rate_semantics`, `stored_base_currency`, `stored_quote_currency`. Rate = quote per 1 base; esposizioni riportano linked_currency, native/target amount e conversion provenance.
- **Provenance/coverage fields**: `direction`, `rate_semantics`
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_pair_identity` in `backend/app/services/ai_export/components/fx_core.py:183`; model `FxPairIdentityPayload` in `backend/app/services/ai_export/components/fx_payloads.py:66`.

### `fx.current_rate`

- **Domain**: fx
- **Used by datasets**: fx.overview (required), fx.all_data (required)
- **Required sources/services**: convert_bulk/FxRate + SignalService for technical components
- **Applicability**: `as_of`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=fx.current_rate].payload`
- **Scalar/object fields**: `base_currency`: string; `direction`: FxRateDirection; `effective_date`: string; `is_backward_filled`: boolean; `quote_currency`: string; `rate`: number | string; `requested_date`: string; `staleness_days`: integer
- **Collections**: nessuna
- **Collection semantics**: Ordine e completezza definiti dal builder/output model; nessun filtro per detail rilevato.
- **Temporal fields/policy**: `effective_date`, `requested_date`. Fotografia a snapshot_as_of = period_end.
- **Currency fields/semantics**: `base_currency`, `quote_currency`, `rate`. Rate = quote per 1 base; esposizioni riportano linked_currency, native/target amount e conversion provenance.
- **Provenance/coverage fields**: `direction`, `staleness_days`
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_current_rate` in `backend/app/services/ai_export/components/fx_core.py:202`; model `FxCurrentRatePayload` in `backend/app/services/ai_export/components/fx_payloads.py:103`.

### `fx.conversion_provenance`

- **Domain**: fx
- **Used by datasets**: fx.overview (required), fx.all_data (required)
- **Required sources/services**: convert_bulk/FxRate + SignalService for technical components
- **Applicability**: `none`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=fx.conversion_provenance].payload`
- **Scalar/object fields**: `base_currency`: string; `direction`: FxRateDirection; `effective_date`: string; `is_backward_filled`: boolean; `quote_currency`: string; `requested_date`: string; `source`: string
- **Collections**: nessuna
- **Collection semantics**: Ordine e completezza definiti dal builder/output model; nessun filtro per detail rilevato.
- **Temporal fields/policy**: `effective_date`, `requested_date`. Nessuna propria aggregazione temporale.
- **Currency fields/semantics**: `base_currency`, `quote_currency`. Rate = quote per 1 base; esposizioni riportano linked_currency, native/target amount e conversion provenance.
- **Provenance/coverage fields**: `direction`, `source`
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_conversion_provenance` in `backend/app/services/ai_export/components/fx_core.py:225`; model `FxConversionProvenancePayload` in `backend/app/services/ai_export/components/fx_payloads.py:146`.

### `fx.rate_ohlc`

- **Domain**: fx
- **Used by datasets**: fx.market_technical (required), fx.all_data (required)
- **Required sources/services**: convert_bulk/FxRate + SignalService for technical components
- **Applicability**: `aggregated`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=fx.rate_ohlc].payload`
- **Scalar/object fields**: `base_currency`: string; `latest_date?`: string | null; `latest_rate?`: number | null; `quote_currency`: string
- **Collections**: `buckets`: array<PriceBucket> → {calendar_days, end_date, first, last, maximum, minimum, observation_count, simple_return, start_date}
- **Collection semantics**: Ordine e completezza definiti dal builder/output model; nessun filtro per detail rilevato.
- **Temporal fields/policy**: `buckets`, `latest_date`. Periodo visibile = scope period; warm-up interno SignalService; export su BucketPlan adattivo. Meta pubblica non espone calculation_range/earliest_calculation_date.
- **Currency fields/semantics**: `base_currency`, `latest_rate`, `quote_currency`. Rate = quote per 1 base; esposizioni riportano linked_currency, native/target amount e conversion provenance.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `ohlc_bucket`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_fx_rate_ohlc` in `backend/app/services/ai_export/components/asset_fx_technical.py:165`; model `FxRateOhlcPayload` in `backend/app/services/ai_export/components/technical_payloads.py:362`.

### `fx.returns_volatility`

- **Domain**: fx
- **Used by datasets**: fx.market_technical (required), fx.all_data (required)
- **Required sources/services**: convert_bulk/FxRate + SignalService for technical components
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=fx.returns_volatility].payload`
- **Scalar/object fields**: `base_currency`: string; `quote_currency`: string
- **Collections**: `buckets`: array<ReturnVolatilityBucket> → {calendar_days, end_date, first, last, maximum, minimum, observation_count, start_date, volatility}
- **Collection semantics**: Ordine e completezza definiti dal builder/output model; nessun filtro per detail rilevato.
- **Temporal fields/policy**: `buckets`. Periodo visibile = scope period; warm-up interno SignalService; export su BucketPlan adattivo. Meta pubblica non espone calculation_range/earliest_calculation_date.
- **Currency fields/semantics**: `base_currency`, `quote_currency`. Rate = quote per 1 base; esposizioni riportano linked_currency, native/target amount e conversion provenance.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_fx_returns_volatility` in `backend/app/services/ai_export/components/asset_fx_technical.py:233`; model `FxReturnsVolatilityPayload` in `backend/app/services/ai_export/components/technical_payloads.py:374`.

### `fx.indicators`

- **Domain**: fx
- **Used by datasets**: fx.market_technical (required), fx.all_data (required)
- **Required sources/services**: convert_bulk/FxRate + SignalService for technical components
- **Applicability**: `aggregated`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=fx.indicators].payload`
- **Scalar/object fields**: nessuno
- **Collections**: `indicators`: array<IndicatorTablePayload> → {category, columns, instance_id, rows, semantic_description, semantic_id, signal_code}
- **Collection semantics**: Ordine e completezza definiti dal builder/output model; nessun filtro per detail rilevato.
- **Temporal fields/policy**: nessuno. Periodo visibile = scope period; warm-up interno SignalService; export su BucketPlan adattivo. Meta pubblica non espone calculation_range/earliest_calculation_date.
- **Currency fields/semantics**: nessuno. Rate = quote per 1 base; esposizioni riportano linked_currency, native/target amount e conversion provenance.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `signal_profile_bucket`
- **Possible omission conditions**: SignalResult UNAVAILABLE/FAILED o senza serie → indicatore omesso senza warning nel payload.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_fx_indicators` in `backend/app/services/ai_export/components/asset_fx_technical.py:263`; model `SingleTargetIndicatorsPayload` in `backend/app/services/ai_export/components/technical_payloads.py:271`.

### `fx.states_events`

- **Domain**: fx
- **Used by datasets**: fx.market_technical (required), fx.all_data (required)
- **Required sources/services**: convert_bulk/FxRate + SignalService for technical components
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=fx.states_events].payload`
- **Scalar/object fields**: `total_event_count`: integer
- **Collections**: `buckets`: array<TechnicalEventBucket> → {calendar_days, end_date, event_count, events, start_date}
- **Collection semantics**: Bucket temporali; eventi preservati; nessun cap.
- **Temporal fields/policy**: `buckets`. Periodo visibile = scope period; warm-up interno SignalService; export su BucketPlan adattivo. Meta pubblica non espone calculation_range/earliest_calculation_date.
- **Currency fields/semantics**: nessuno. Rate = quote per 1 base; esposizioni riportano linked_currency, native/target amount e conversion provenance.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Eventi di SignalResult non OK/PARTIAL o annotazioni unavailable assenti; nessun placeholder.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_fx_states_events` in `backend/app/services/ai_export/components/asset_fx_technical.py:286`; model `TechnicalEventsPayload` in `backend/app/services/ai_export/components/technical_payloads.py:318`.

### `fx.exposure_base_quote`

- **Domain**: fx
- **Used by datasets**: fx.direct_exposure (required), fx.all_data (required)
- **Required sources/services**: PortfolioService report + Asset metadata + convert_bulk/FxRate
- **Applicability**: `windowed`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=fx.exposure_base_quote].payload`
- **Scalar/object fields**: `as_of`: string; `base_currency`: string; `quote_currency`: string; `target_currency`: string
- **Collections**: `broker_scope?`: array<integer>; `rows?`: array<FxExposureRow> → {asset_id, broker_id, conversion, kind, linkage, linked_currency, native_amount, target_amount, valuation_source}
- **Collection semantics**: Righe ordinate per kind/linkage/currency/broker/asset; ogni esposizione diretta mantenuta.
- **Temporal fields/policy**: `as_of`. Intervallo inclusivo [period_start, period_end].
- **Currency fields/semantics**: `base_currency`, `quote_currency`, `target_currency`. Rate = quote per 1 base; esposizioni riportano linked_currency, native/target amount e conversion provenance.
- **Provenance/coverage fields**: nessuno
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Nessuna posizione/esposizione → collection vuota valida.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_exposure_base_quote` in `backend/app/services/ai_export/components/fx_core.py:527`; model `FxExposureBaseQuotePayload` in `backend/app/services/ai_export/components/fx_payloads.py:334`.

### `fx.exposure_provenance`

- **Domain**: fx
- **Used by datasets**: fx.direct_exposure (required), fx.all_data (required)
- **Required sources/services**: PortfolioService report + Asset metadata + convert_bulk/FxRate
- **Applicability**: `none`; dataset catalog statico, nessun filtro per detail.
- **Output YAML path**: `sections[component_id=fx.exposure_provenance].payload`
- **Scalar/object fields**: `base_currency`: string; `quote_currency`: string; `target_currency`: string
- **Collections**: `conversions?`: array<FxExposureConversionSummary> → {direction, effective_date, is_backward_filled, linked_currency, requested_date, source, target_currency}
- **Collection semantics**: Una conversione deduplicata per linked_currency; ENGINE_VALUATION-only omessa.
- **Temporal fields/policy**: nessuno. Nessuna propria aggregazione temporale.
- **Currency fields/semantics**: `base_currency`, `quote_currency`, `target_currency`. Rate = quote per 1 base; esposizioni riportano linked_currency, native/target amount e conversion provenance.
- **Provenance/coverage fields**: `conversions`
- **Aggregation or bucket policy**: `nessuno`
- **Possible omission conditions**: Payload vuoto/null è successo se il builder ritorna normalmente; nessuna omissione basata su token/detail.
- **Failure behavior**: eccezione builder/resource → `snapshot_source_failure` se required; omissione silenziosa se optional; payload vuoto ritornato normalmente = successo.
- **Source**: builder `_build_exposure_provenance` in `backend/app/services/ai_export/components/fx_core.py:589`; model `FxExposureProvenancePayload` in `backend/app/services/ai_export/components/fx_payloads.py:404`.

## Contenuto effettivo di `portfolio.technical`

### `portfolio.technical_prices`

- Universo: righe `positions_contribution` end-of-period; `considered_asset_count` prima del filtro, `eligible_asset_count` dopo `not fully sold && end_value != 0`.
- Bug multi-broker: nessuna aggregazione per asset prima della query; stesso asset su più broker → duplicati e 503.
- Serie: solo `close`, non OHLC reale; open/high/low disponibili upstream ma scartati (`portfolio_broker_technical.py:67-98`).
- Valuta: query target currency, ma conversioni parziali lasciano punti nativi; una sola `currency` viene presa dal primo punto.
- Bucket: first/min/max/last del close, senza date reali di min/max; observation_count include calendar-backfill.
- `simple_return = last/first - 1` interno al bucket: bucket da un giorno sempre zero; manca previous bucket last.
- Giorni senza mercato: backward-fill giornaliero; nessun flag/provenance nel payload tecnico.
- Warm-up: caricato e usato da SignalService, ma non serializzato; meta pubblica mantiene `calculation_range=None` e `earliest_calculation_date=None` (`runtime_service.py:512-521`).

### `portfolio.technical_indicators`

- Bundle fisso 20 istanze Asset per ogni asset eleggibile.
- Ogni tabella contiene semantic metadata, colonne e celle datate per bucket.
- Non serializza `implementation_version`, `normalized_params`, status, availability, warmup, warning o error presenti in `SignalResult` (`schemas/signals.py:996-1008`; `technical_payloads.py:219-248`).
- Multi-output: colonne separate; band lower/middle/upper indipendenti; cella single o first/min/max/last con date.
- UNAVAILABLE/FAILED/no series → tabella assente senza spiegazione.

### `portfolio.technical_events`

- Topologia esplicita AI Export, non derivata dal catalogo plugin.
- Detection su osservazioni estese prima del bucket; bucket conserva tutti gli eventi, quindi la compressione non li perde.
- Il payload non conserva instance_id, state before/after, observed/effective source date o warning.
- `observed_only=false`, `epsilon=0`, no min gap/limit: eventi su backward-fill e rumore float.

### `portfolio.technical_breadth`

- Output classifiable: AROON.oscillator, CCI.cci, MFI.mfi, PPO.ppo, ROC.roc, RSI.rsi, STOCH_RSI.k.
- Per stato: signal_code, output_key, state, unweighted_count, unweighted_ratio, weighted_ratio.
- Top-level: considered/eligible/covered asset count e total_weight.
- Mancano per indicatore: evaluated count, evaluated weight, matching weight assoluto, state date, category/family.
- Denominatore reale è `covered_count` locale e `covered_weight`, calcolati ma non serializzati (`technical_shared.py:1003-1034`).
- Indicatori non calcolabili non partecipano; nessun elenco omissioni.

### Completezza per detail

Compact/Standard/Full usano lo stesso universo e lo stesso bundle. Non esiste selezione entità per detail. La completezza può comunque ridursi per duplicate asset failure, assenza price result, conversion incomplete o signal unavailable.

## Indicatori e Signal Plugin

Il runtime usa `17` plugin distinti (`20` istanze Asset, `12` FX). Tutti dichiarano version `1.0.0`, output metadata e aggregation profile. Nessuno override `describe_for_ai`; la descrizione AI deriva dai campi semantic del plugin (`signal_plugins/base.py:84-150`). Solo MFI e OBV override `validate_input`; nessuno override `validate_output`, ma SignalService applica validazione centrale di count/metadata/date/cardinality (`signal_service.py:1220-1252`).

### `ADX` — `AdxSignalPlugin`

- **Implementation/version**: `backend/app/services/signal_plugins/adx.py:66`, `1.0.0`
- **Used by components**: `asset.indicators`, `asset.states_events`, `portfolio.technical_indicators`, `portfolio.technical_events`, `portfolio.technical_breadth`, `broker.technical_indicators`, `broker.technical_events`, `broker.technical_breadth`
- **Input series/required fields**: price fields `high`, `low`, `close`; events=False; meaningful_volume=False
- **Minimum history/warm-up**: asset:adx_14 params={"period": 14} warmup=28+224=252
- **Parameters**: schema-owned; defaults `{"period": 14}`
- **Outputs**: `adx` kind=line, unit=index, aggregation=last_with_range; `plus_di` kind=line, unit=index, aggregation=last_with_range; `minus_di` kind=line, unit=index, aggregation=last_with_range
- **Validation rules/output validation**: validate_input base no-op; validate_output base no-op; central SignalService metadata/date/cardinality validation
- **AI description**: `average_directional_index` — Measures trend strength from directional price movement without indicating trend direction. (default `SignalPlugin.describe_for_ai`, plugin metadata).
- **Possible states**: nessuno
- **Possible events in AI Export topology**: `asset:adx_14_trend_25`
- **Omission conditions**: status UNAVAILABLE/FAILED, no series, missing required fields/history; MFI/OBV additionally require meaningful observed volume.

### `AROON` — `AroonSignalPlugin`

- **Implementation/version**: `backend/app/services/signal_plugins/aroon.py:73`, `1.0.0`
- **Used by components**: `asset.indicators`, `asset.states_events`, `portfolio.technical_indicators`, `portfolio.technical_events`, `portfolio.technical_breadth`, `broker.technical_indicators`, `broker.technical_events`, `broker.technical_breadth`
- **Input series/required fields**: price fields `high`, `low`; events=False; meaningful_volume=False
- **Minimum history/warm-up**: asset:aroon_25 params={"period": 25} warmup=26+0=26
- **Parameters**: schema-owned; defaults `{"period": 14}`
- **Outputs**: `up` kind=line, unit=index, aggregation=last_with_range; `down` kind=line, unit=index, aggregation=last_with_range; `oscillator` kind=line, unit=index, aggregation=last_with_range, levels=zero=0.0
- **Validation rules/output validation**: validate_input base no-op; validate_output base no-op; central SignalService metadata/date/cardinality validation
- **AI description**: `aroon` — Measures how recently lookback-period highs and lows occurred. (default `SignalPlugin.describe_for_ai`, plugin metadata).
- **Possible states**: above_zero, at_zero, below_zero
- **Possible events in AI Export topology**: nessuno
- **Omission conditions**: status UNAVAILABLE/FAILED, no series, missing required fields/history; MFI/OBV additionally require meaningful observed volume.

### `ATR` — `AtrSignalPlugin`

- **Implementation/version**: `backend/app/services/signal_plugins/atr.py:55`, `1.0.0`
- **Used by components**: `asset.indicators`, `asset.states_events`, `portfolio.technical_indicators`, `portfolio.technical_events`, `portfolio.technical_breadth`, `broker.technical_indicators`, `broker.technical_events`, `broker.technical_breadth`
- **Input series/required fields**: price fields `high`, `low`, `close`; events=False; meaningful_volume=False
- **Minimum history/warm-up**: asset:atr_14 params={"period": 14} warmup=15+153=168
- **Parameters**: schema-owned; defaults `{"period": 14}`
- **Outputs**: `atr` kind=line, unit=price, aggregation=max_with_range
- **Validation rules/output validation**: validate_input base no-op; validate_output base no-op; central SignalService metadata/date/cardinality validation
- **AI description**: `average_true_range` — Measures absolute price variability from true range. (default `SignalPlugin.describe_for_ai`, plugin metadata).
- **Possible states**: nessuno
- **Possible events in AI Export topology**: nessuno
- **Omission conditions**: status UNAVAILABLE/FAILED, no series, missing required fields/history; MFI/OBV additionally require meaningful observed volume.

### `BOLLINGER` — `BollingerSignalPlugin`

- **Implementation/version**: `backend/app/services/signal_plugins/bollinger.py:67`, `1.0.0`
- **Used by components**: `asset.indicators`, `asset.states_events`, `portfolio.technical_indicators`, `portfolio.technical_events`, `portfolio.technical_breadth`, `broker.technical_indicators`, `broker.technical_events`, `broker.technical_breadth`, `fx.indicators`, `fx.states_events`
- **Input series/required fields**: price fields `close`; events=False; meaningful_volume=False
- **Minimum history/warm-up**: asset:bollinger_20_2 params={"multiplier": 2.0, "period": 20} warmup=20+0=20; fx:bollinger_20_2 params={"multiplier": 2.0, "period": 20} warmup=20+0=20
- **Parameters**: schema-owned; defaults `{"multiplier": 2.0, "period": 20}`
- **Outputs**: `bands` kind=band, unit=price, aggregation=band_envelope
- **Validation rules/output validation**: validate_input base no-op; validate_output base no-op; central SignalService metadata/date/cardinality validation
- **AI description**: `bollinger_bands` — Describes a moving-average envelope scaled by recent price dispersion. (default `SignalPlugin.describe_for_ai`, plugin metadata).
- **Possible states**: nessuno
- **Possible events in AI Export topology**: `asset:price_bollinger_lower`, `asset:price_bollinger_middle`, `asset:price_bollinger_upper`, `fx:rate_bollinger_lower`, `fx:rate_bollinger_middle`, `fx:rate_bollinger_upper`
- **Omission conditions**: status UNAVAILABLE/FAILED, no series, missing required fields/history; MFI/OBV additionally require meaningful observed volume.

### `CCI` — `CciSignalPlugin`

- **Implementation/version**: `backend/app/services/signal_plugins/cci.py:117`, `1.0.0`
- **Used by components**: `asset.indicators`, `asset.states_events`, `portfolio.technical_indicators`, `portfolio.technical_events`, `portfolio.technical_breadth`, `broker.technical_indicators`, `broker.technical_events`, `broker.technical_breadth`
- **Input series/required fields**: price fields `high`, `low`, `close`; events=False; meaningful_volume=False
- **Minimum history/warm-up**: asset:cci_20 params={"period": 20} warmup=20+0=20
- **Parameters**: schema-owned; defaults `{"period": 14}`
- **Outputs**: `cci` kind=line, unit=index, aggregation=last_with_range, levels=oversold=-100.0,zero=0.0,overbought=100.0
- **Validation rules/output validation**: validate_input base no-op; validate_output base no-op; central SignalService metadata/date/cardinality validation
- **AI description**: `commodity_channel_index` — Measures typical-price deviation from its recent average. (default `SignalPlugin.describe_for_ai`, plugin metadata).
- **Possible states**: neutral, overbought, oversold
- **Possible events in AI Export topology**: nessuno
- **Omission conditions**: status UNAVAILABLE/FAILED, no series, missing required fields/history; MFI/OBV additionally require meaningful observed volume.

### `DONCHIAN` — `DonchianSignalPlugin`

- **Implementation/version**: `backend/app/services/signal_plugins/donchian.py:56`, `1.0.0`
- **Used by components**: `asset.indicators`, `asset.states_events`, `portfolio.technical_indicators`, `portfolio.technical_events`, `portfolio.technical_breadth`, `broker.technical_indicators`, `broker.technical_events`, `broker.technical_breadth`
- **Input series/required fields**: price fields `high`, `low`; events=False; meaningful_volume=False
- **Minimum history/warm-up**: asset:donchian_20 params={"period": 20} warmup=20+0=20
- **Parameters**: schema-owned; defaults `{"period": 20}`
- **Outputs**: `channels` kind=band, unit=price, aggregation=band_envelope
- **Validation rules/output validation**: validate_input base no-op; validate_output base no-op; central SignalService metadata/date/cardinality validation
- **AI description**: `donchian_channels` — Describes recent high and low boundaries over a rolling window. (default `SignalPlugin.describe_for_ai`, plugin metadata).
- **Possible states**: nessuno
- **Possible events in AI Export topology**: `asset:price_donchian_lower`, `asset:price_donchian_middle`, `asset:price_donchian_upper`
- **Omission conditions**: status UNAVAILABLE/FAILED, no series, missing required fields/history; MFI/OBV additionally require meaningful observed volume.

### `EMA` — `EmaSignalPlugin`

- **Implementation/version**: `backend/app/services/signal_plugins/ema.py:67`, `1.0.0`
- **Used by components**: `asset.indicators`, `asset.states_events`, `portfolio.technical_indicators`, `portfolio.technical_events`, `portfolio.technical_breadth`, `broker.technical_indicators`, `broker.technical_events`, `broker.technical_breadth`, `fx.indicators`, `fx.states_events`
- **Input series/required fields**: price fields `close`; events=False; meaningful_volume=False
- **Minimum history/warm-up**: asset:ema_20 params={"offset": 0.0, "period": 20} warmup=20+100=120; asset:ema_50 params={"offset": 0.0, "period": 50} warmup=50+250=300; asset:ema_200 params={"offset": 0.0, "period": 200} warmup=200+1000=1200; fx:ema_20 params={"offset": 0.0, "period": 20} warmup=20+100=120; fx:ema_50 params={"offset": 0.0, "period": 50} warmup=50+250=300; fx:ema_200 params={"offset": 0.0, "period": 200} warmup=200+1000=1200
- **Parameters**: schema-owned; defaults `{"offset": 0.0, "period": 14}`
- **Outputs**: `ema` kind=line, unit=price, aggregation=last_with_range
- **Validation rules/output validation**: validate_input base no-op; validate_output base no-op; central SignalService metadata/date/cardinality validation
- **AI description**: `exponential_moving_average` — Smooths prices with greater weight on recent observations. (default `SignalPlugin.describe_for_ai`, plugin metadata).
- **Possible states**: nessuno
- **Possible events in AI Export topology**: `asset:price_ema_20`, `asset:ema_20_ema_50`, `asset:ema_50_ema_200`, `fx:rate_ema_20`, `fx:ema_20_ema_50`, `fx:ema_50_ema_200`
- **Omission conditions**: status UNAVAILABLE/FAILED, no series, missing required fields/history; MFI/OBV additionally require meaningful observed volume.

### `KAMA` — `KamaSignalPlugin`

- **Implementation/version**: `backend/app/services/signal_plugins/kama.py:55`, `1.0.0`
- **Used by components**: `asset.indicators`, `asset.states_events`, `portfolio.technical_indicators`, `portfolio.technical_events`, `portfolio.technical_breadth`, `broker.technical_indicators`, `broker.technical_events`, `broker.technical_breadth`, `fx.indicators`, `fx.states_events`
- **Input series/required fields**: price fields `close`; events=False; meaningful_volume=False
- **Minimum history/warm-up**: asset:kama_20 params={"period": 20} warmup=30+210=240; fx:kama_20 params={"period": 20} warmup=30+210=240
- **Parameters**: schema-owned; defaults `{"period": 10}`
- **Outputs**: `kama` kind=line, unit=price, aggregation=last_with_range
- **Validation rules/output validation**: validate_input base no-op; validate_output base no-op; central SignalService metadata/date/cardinality validation
- **AI description**: `kaufman_adaptive_moving_average` — Smooths prices with responsiveness adjusted by market efficiency. (default `SignalPlugin.describe_for_ai`, plugin metadata).
- **Possible states**: nessuno
- **Possible events in AI Export topology**: nessuno
- **Omission conditions**: status UNAVAILABLE/FAILED, no series, missing required fields/history; MFI/OBV additionally require meaningful observed volume.

### `MACD` — `MacdSignalPlugin`

- **Implementation/version**: `backend/app/services/signal_plugins/macd.py:100`, `1.0.0`
- **Used by components**: `asset.indicators`, `asset.states_events`, `portfolio.technical_indicators`, `portfolio.technical_events`, `portfolio.technical_breadth`, `broker.technical_indicators`, `broker.technical_events`, `broker.technical_breadth`, `fx.indicators`, `fx.states_events`
- **Input series/required fields**: price fields `close`; events=False; meaningful_volume=False
- **Minimum history/warm-up**: asset:macd_12_26_9 params={"fastPeriod": 12, "signalPeriod": 9, "slowPeriod": 26} warmup=34+174=208; fx:macd_12_26_9 params={"fastPeriod": 12, "signalPeriod": 9, "slowPeriod": 26} warmup=34+174=208
- **Parameters**: schema-owned; defaults `{"fastPeriod": 12, "signalPeriod": 9, "slowPeriod": 26}`
- **Outputs**: `macd` kind=line, unit=price, aggregation=last_with_range; `signal` kind=line, unit=price, aggregation=last_with_range; `histogram` kind=bar, unit=price, aggregation=last_with_range
- **Validation rules/output validation**: validate_input base no-op; validate_output base no-op; central SignalService metadata/date/cardinality validation
- **AI description**: `moving_average_convergence_divergence` — Compares fast and slow exponential price trends. (default `SignalPlugin.describe_for_ai`, plugin metadata).
- **Possible states**: nessuno
- **Possible events in AI Export topology**: `asset:macd_signal`, `asset:macd_histogram_zero`
- **Omission conditions**: status UNAVAILABLE/FAILED, no series, missing required fields/history; MFI/OBV additionally require meaningful observed volume.

### `MFI` — `MfiSignalPlugin`

- **Implementation/version**: `backend/app/services/signal_plugins/mfi.py:151`, `1.0.0`
- **Used by components**: `asset.indicators`, `asset.states_events`, `portfolio.technical_indicators`, `portfolio.technical_events`, `portfolio.technical_breadth`, `broker.technical_indicators`, `broker.technical_events`, `broker.technical_breadth`
- **Input series/required fields**: price fields `high`, `low`, `close`, `volume`; events=False; meaningful_volume=True
- **Minimum history/warm-up**: asset:mfi_14 params={"overbought": 80.0, "oversold": 20.0, "period": 14} warmup=15+0=15
- **Parameters**: schema-owned; defaults `{"overbought": 80, "oversold": 20, "period": 14}`
- **Outputs**: `mfi` kind=line, unit=index, aggregation=last_with_range, levels=oversold=20.0,overbought=80.0
- **Validation rules/output validation**: plugin validate_input override; validate_output base no-op; central SignalService metadata/date/cardinality validation
- **AI description**: `money_flow_index` — Measures price-and-volume flow over a rolling window. (default `SignalPlugin.describe_for_ai`, plugin metadata).
- **Possible states**: neutral, overbought, oversold
- **Possible events in AI Export topology**: `asset:mfi_14_oversold_20`, `asset:mfi_14_overbought_80`
- **Omission conditions**: status UNAVAILABLE/FAILED, no series, missing required fields/history; MFI/OBV additionally require meaningful observed volume.

### `NATR` — `NatrSignalPlugin`

- **Implementation/version**: `backend/app/services/signal_plugins/natr.py:55`, `1.0.0`
- **Used by components**: `asset.indicators`, `asset.states_events`, `portfolio.technical_indicators`, `portfolio.technical_events`, `portfolio.technical_breadth`, `broker.technical_indicators`, `broker.technical_events`, `broker.technical_breadth`
- **Input series/required fields**: price fields `high`, `low`, `close`; events=False; meaningful_volume=False
- **Minimum history/warm-up**: asset:natr_14 params={"period": 14} warmup=15+153=168
- **Parameters**: schema-owned; defaults `{"period": 14}`
- **Outputs**: `natr` kind=line, unit=percentage, aggregation=max_with_range
- **Validation rules/output validation**: validate_input base no-op; validate_output base no-op; central SignalService metadata/date/cardinality validation
- **AI description**: `normalized_average_true_range` — Measures true-range variability relative to price. (default `SignalPlugin.describe_for_ai`, plugin metadata).
- **Possible states**: nessuno
- **Possible events in AI Export topology**: nessuno
- **Omission conditions**: status UNAVAILABLE/FAILED, no series, missing required fields/history; MFI/OBV additionally require meaningful observed volume.

### `OBV` — `ObvSignalPlugin`

- **Implementation/version**: `backend/app/services/signal_plugins/obv.py:42`, `1.0.0`
- **Used by components**: `asset.indicators`, `asset.states_events`, `portfolio.technical_indicators`, `portfolio.technical_events`, `portfolio.technical_breadth`, `broker.technical_indicators`, `broker.technical_events`, `broker.technical_breadth`
- **Input series/required fields**: price fields `close`, `volume`; events=False; meaningful_volume=True
- **Minimum history/warm-up**: asset:obv params={} warmup=1+0=1
- **Parameters**: schema-owned; defaults `{}`
- **Outputs**: `obv` kind=line, unit=volume, aggregation=last_with_range
- **Validation rules/output validation**: plugin validate_input override; validate_output base no-op; central SignalService metadata/date/cardinality validation
- **AI description**: `on_balance_volume` — Accumulates volume according to closing-price direction. (default `SignalPlugin.describe_for_ai`, plugin metadata).
- **Possible states**: nessuno
- **Possible events in AI Export topology**: nessuno
- **Omission conditions**: status UNAVAILABLE/FAILED, no series, missing required fields/history; MFI/OBV additionally require meaningful observed volume.

### `PPO` — `PpoSignalPlugin`

- **Implementation/version**: `backend/app/services/signal_plugins/ppo.py:107`, `1.0.0`
- **Used by components**: `asset.indicators`, `asset.states_events`, `portfolio.technical_indicators`, `portfolio.technical_events`, `portfolio.technical_breadth`, `broker.technical_indicators`, `broker.technical_events`, `broker.technical_breadth`, `fx.indicators`, `fx.states_events`
- **Input series/required fields**: price fields `close`; events=False; meaningful_volume=False
- **Minimum history/warm-up**: asset:ppo_12_26_9 params={"fastPeriod": 12, "signalPeriod": 9, "slowPeriod": 26} warmup=34+174=208; fx:ppo_12_26_9 params={"fastPeriod": 12, "signalPeriod": 9, "slowPeriod": 26} warmup=34+174=208
- **Parameters**: schema-owned; defaults `{"fastPeriod": 12, "signalPeriod": 9, "slowPeriod": 26}`
- **Outputs**: `ppo` kind=line, unit=percentage, aggregation=last_with_range, levels=zero=0.0; `signal` kind=line, unit=percentage, aggregation=last_with_range; `histogram` kind=bar, unit=percentage, aggregation=last_with_range
- **Validation rules/output validation**: validate_input base no-op; validate_output base no-op; central SignalService metadata/date/cardinality validation
- **AI description**: `percentage_price_oscillator` — Compares fast and slow exponential trends as a percentage. (default `SignalPlugin.describe_for_ai`, plugin metadata).
- **Possible states**: above_zero, at_zero, below_zero
- **Possible events in AI Export topology**: `fx:ppo_signal`, `fx:ppo_histogram_zero`
- **Omission conditions**: status UNAVAILABLE/FAILED, no series, missing required fields/history; MFI/OBV additionally require meaningful observed volume.

### `ROC` — `RocSignalPlugin`

- **Implementation/version**: `backend/app/services/signal_plugins/roc.py:63`, `1.0.0`
- **Used by components**: `asset.indicators`, `asset.states_events`, `portfolio.technical_indicators`, `portfolio.technical_events`, `portfolio.technical_breadth`, `broker.technical_indicators`, `broker.technical_events`, `broker.technical_breadth`, `fx.indicators`, `fx.states_events`
- **Input series/required fields**: price fields `close`; events=False; meaningful_volume=False
- **Minimum history/warm-up**: asset:roc_20 params={"period": 20} warmup=21+0=21; fx:roc_20 params={"period": 20} warmup=21+0=21
- **Parameters**: schema-owned; defaults `{"period": 12}`
- **Outputs**: `roc` kind=line, unit=percentage, aggregation=last_with_range, levels=zero=0.0
- **Validation rules/output validation**: validate_input base no-op; validate_output base no-op; central SignalService metadata/date/cardinality validation
- **AI description**: `rate_of_change` — Measures percentage change from the price one lookback period earlier. (default `SignalPlugin.describe_for_ai`, plugin metadata).
- **Possible states**: above_zero, at_zero, below_zero
- **Possible events in AI Export topology**: `fx:roc_20_zero`
- **Omission conditions**: status UNAVAILABLE/FAILED, no series, missing required fields/history; MFI/OBV additionally require meaningful observed volume.

### `RSI` — `RsiSignalPlugin`

- **Implementation/version**: `backend/app/services/signal_plugins/rsi.py:144`, `1.0.0`
- **Used by components**: `asset.indicators`, `asset.states_events`, `portfolio.technical_indicators`, `portfolio.technical_events`, `portfolio.technical_breadth`, `broker.technical_indicators`, `broker.technical_events`, `broker.technical_breadth`, `fx.indicators`, `fx.states_events`
- **Input series/required fields**: price fields `close`; events=False; meaningful_volume=False
- **Minimum history/warm-up**: asset:rsi_14 params={"overbought": 70.0, "oversold": 30.0, "period": 14} warmup=15+209=224; fx:rsi_14 params={"overbought": 70.0, "oversold": 30.0, "period": 14} warmup=15+209=224
- **Parameters**: schema-owned; defaults `{"overbought": 70, "oversold": 30, "period": 14}`
- **Outputs**: `rsi` kind=line, unit=index, aggregation=last_with_range, levels=oversold=30.0,overbought=70.0
- **Validation rules/output validation**: validate_input base no-op; validate_output base no-op; central SignalService metadata/date/cardinality validation
- **AI description**: `relative_strength_index` — Measures recent gain and loss magnitude on a bounded scale. (default `SignalPlugin.describe_for_ai`, plugin metadata).
- **Possible states**: neutral, overbought, oversold
- **Possible events in AI Export topology**: `asset:rsi_14_oversold_30`, `asset:rsi_14_overbought_70`, `fx:rsi_14_oversold_30`, `fx:rsi_14_overbought_70`
- **Omission conditions**: status UNAVAILABLE/FAILED, no series, missing required fields/history; MFI/OBV additionally require meaningful observed volume.

### `SMA` — `SmaSignalPlugin`

- **Implementation/version**: `backend/app/services/signal_plugins/sma.py:55`, `1.0.0`
- **Used by components**: `asset.indicators`, `asset.states_events`, `portfolio.technical_indicators`, `portfolio.technical_events`, `portfolio.technical_breadth`, `broker.technical_indicators`, `broker.technical_events`, `broker.technical_breadth`, `fx.indicators`, `fx.states_events`
- **Input series/required fields**: price fields `close`; events=False; meaningful_volume=False
- **Minimum history/warm-up**: asset:sma_50 params={"period": 50} warmup=50+0=50; asset:sma_200 params={"period": 200} warmup=200+0=200; fx:sma_50 params={"period": 50} warmup=50+0=50; fx:sma_200 params={"period": 200} warmup=200+0=200
- **Parameters**: schema-owned; defaults `{"period": 20}`
- **Outputs**: `sma` kind=line, unit=price, aggregation=last_with_range
- **Validation rules/output validation**: validate_input base no-op; validate_output base no-op; central SignalService metadata/date/cardinality validation
- **AI description**: `simple_moving_average` — Averages closing prices over a rolling window. (default `SignalPlugin.describe_for_ai`, plugin metadata).
- **Possible states**: nessuno
- **Possible events in AI Export topology**: nessuno
- **Omission conditions**: status UNAVAILABLE/FAILED, no series, missing required fields/history; MFI/OBV additionally require meaningful observed volume.

### `STOCH_RSI` — `StochRsiSignalPlugin`

- **Implementation/version**: `backend/app/services/signal_plugins/stoch_rsi.py:172`, `1.0.0`
- **Used by components**: `asset.indicators`, `asset.states_events`, `portfolio.technical_indicators`, `portfolio.technical_events`, `portfolio.technical_breadth`, `broker.technical_indicators`, `broker.technical_events`, `broker.technical_breadth`, `fx.indicators`, `fx.states_events`
- **Input series/required fields**: price fields `close`; events=False; meaningful_volume=False
- **Minimum history/warm-up**: asset:stoch_rsi_14_3 params={"dPeriod": 3, "overbought": 80.0, "oversold": 20.0, "period": 14} warmup=30+194=224; fx:stoch_rsi_14_3 params={"dPeriod": 3, "overbought": 80.0, "oversold": 20.0, "period": 14} warmup=30+194=224
- **Parameters**: schema-owned; defaults `{"dPeriod": 3, "overbought": 80, "oversold": 20, "period": 14}`
- **Outputs**: `k` kind=line, unit=index, aggregation=last_with_range, levels=oversold=20.0,overbought=80.0; `d` kind=line, unit=index, aggregation=last_with_range
- **Validation rules/output validation**: validate_input base no-op; validate_output base no-op; central SignalService metadata/date/cardinality validation
- **AI description**: `stochastic_relative_strength_index` — Locates RSI within its recent range and applies smoothing. (default `SignalPlugin.describe_for_ai`, plugin metadata).
- **Possible states**: neutral, overbought, oversold
- **Possible events in AI Export topology**: `asset:stoch_rsi_k_d`, `asset:stoch_rsi_k_oversold_20`, `asset:stoch_rsi_k_overbought_80`, `fx:stoch_rsi_k_d`, `fx:stoch_rsi_k_oversold_20`, `fx:stoch_rsi_k_overbought_80`
- **Omission conditions**: status UNAVAILABLE/FAILED, no series, missing required fields/history; MFI/OBV additionally require meaningful observed volume.

### Plugin disponibili ma non usati dal bundle AI Export

- `RISK_DRAWDOWN` esiste, usa `MIN_WITH_RANGE` e produce area underwater, ma non è in `ASSET_CURATED_SIGNALS` (`signal_plugins/drawdown.py:39-107`, `technical_shared.py:163-205`).
- Rolling return/volatility/sharpe/beta e altri plugin Risk registrati non sono inclusi.
- Conseguenza: le analisi tecniche non ricevono automaticamente tutta la Signal Registry, ma solo il bundle legacy congelato.

### Divergenza annotation capabilities

- ADX dichiara solo `line_crossover`, ma il bundle richiede `threshold_crossing` a 25 (`signal_plugins/adx.py:135-136`, `technical_shared.py:296`).
- Bollinger e Donchian non dichiarano capability, ma il bundle crea tre line crossover ciascuno (`technical_shared.py:293-302`).
- AROON/CCI/OBV dichiarano capability non usate dal bundle.
- `annotation_capabilities` non è validato da SignalService: la topologia effettiva resta duplicata in AI Export.

## Matrice cross, soglie ed eventi

Semantica comune:

- detection su serie observation-level estese; timestamp = requested calendar date;
- equality mantiene la prima data uguale e può emettere il cross lì al cambio di lato;
- `epsilon=0`: differenze minime non sono neutralizzate;
- NaN/non-finite o source missing resettano lo stato; gap cadence >1 giorno resetta, ma il calendar-backfill spesso elimina il gap;
- `observed_only=false`: backward-filled dates sono valide;
- dedup export `(asset_id, instance_id, annotation_key, date)`, first-seen wins;
- bucket assignment preserva ogni evento, nessun cap;
- exported fields: date, key, annotation_type, signal_code, semantic_description generica, direction, values, asset_id optional; niente before/after state.

### Asset / Portfolio / Broker

| Event ID | Plugin | Domain | Left | Right | Threshold | Direction | Parameters | State transition |
|---|---|---|---|---|---:|---|---|---|
| `price_ema_20` | `EMA` | asset | `price.close` | `ema_20.ema` | - | both | obs=False, eps=0.0, gap=0, limit=None | left<right ↔ left>right |
| `ema_20_ema_50` | `EMA` | asset | `ema_20.ema` | `ema_50.ema` | - | both | obs=False, eps=0.0, gap=0, limit=None | left<right ↔ left>right |
| `ema_50_ema_200` | `EMA` | asset | `ema_50.ema` | `ema_200.ema` | - | both | obs=False, eps=0.0, gap=0, limit=None | left<right ↔ left>right |
| `rsi_14_oversold_30` | `RSI` | asset | `rsi_14.rsi` | `-` | 30.0 | both | obs=False, eps=0.0, gap=0, limit=None | below/above 30.0 |
| `rsi_14_overbought_70` | `RSI` | asset | `rsi_14.rsi` | `-` | 70.0 | both | obs=False, eps=0.0, gap=0, limit=None | below/above 70.0 |
| `macd_signal` | `MACD` | asset | `macd_12_26_9.macd` | `macd_12_26_9.signal` | - | both | obs=False, eps=0.0, gap=0, limit=None | left<right ↔ left>right |
| `macd_histogram_zero` | `MACD` | asset | `macd_12_26_9.histogram` | `-` | 0.0 | both | obs=False, eps=0.0, gap=0, limit=None | below/above 0.0 |
| `mfi_14_oversold_20` | `MFI` | asset | `mfi_14.mfi` | `-` | 20.0 | both | obs=False, eps=0.0, gap=0, limit=None | below/above 20.0 |
| `mfi_14_overbought_80` | `MFI` | asset | `mfi_14.mfi` | `-` | 80.0 | both | obs=False, eps=0.0, gap=0, limit=None | below/above 80.0 |
| `price_bollinger_lower` | `BOLLINGER` | asset | `price.close` | `bollinger_20_2.bands.lower` | - | both | obs=False, eps=0.0, gap=0, limit=None | left<right ↔ left>right |
| `price_bollinger_middle` | `BOLLINGER` | asset | `price.close` | `bollinger_20_2.bands.middle` | - | both | obs=False, eps=0.0, gap=0, limit=None | left<right ↔ left>right |
| `price_bollinger_upper` | `BOLLINGER` | asset | `price.close` | `bollinger_20_2.bands.upper` | - | both | obs=False, eps=0.0, gap=0, limit=None | left<right ↔ left>right |
| `adx_14_trend_25` | `ADX` | asset | `adx_14.adx` | `-` | 25.0 | both | obs=False, eps=0.0, gap=0, limit=None | below/above 25.0 |
| `stoch_rsi_k_d` | `STOCH_RSI` | asset | `stoch_rsi_14_3.k` | `stoch_rsi_14_3.d` | - | both | obs=False, eps=0.0, gap=0, limit=None | left<right ↔ left>right |
| `stoch_rsi_k_oversold_20` | `STOCH_RSI` | asset | `stoch_rsi_14_3.k` | `-` | 20.0 | both | obs=False, eps=0.0, gap=0, limit=None | below/above 20.0 |
| `stoch_rsi_k_overbought_80` | `STOCH_RSI` | asset | `stoch_rsi_14_3.k` | `-` | 80.0 | both | obs=False, eps=0.0, gap=0, limit=None | below/above 80.0 |
| `price_donchian_lower` | `DONCHIAN` | asset | `price.close` | `donchian_20.channels.lower` | - | both | obs=False, eps=0.0, gap=0, limit=None | left<right ↔ left>right |
| `price_donchian_middle` | `DONCHIAN` | asset | `price.close` | `donchian_20.channels.middle` | - | both | obs=False, eps=0.0, gap=0, limit=None | left<right ↔ left>right |
| `price_donchian_upper` | `DONCHIAN` | asset | `price.close` | `donchian_20.channels.upper` | - | both | obs=False, eps=0.0, gap=0, limit=None | left<right ↔ left>right |

### FX

| Event ID | Plugin | Domain | Left | Right | Threshold | Direction | Parameters | State transition |
|---|---|---|---|---|---:|---|---|---|
| `rate_ema_20` | `EMA` | fx | `price.close` | `ema_20.ema` | - | both | obs=False, eps=0.0, gap=0, limit=None | left<right ↔ left>right |
| `ema_20_ema_50` | `EMA` | fx | `ema_20.ema` | `ema_50.ema` | - | both | obs=False, eps=0.0, gap=0, limit=None | left<right ↔ left>right |
| `ema_50_ema_200` | `EMA` | fx | `ema_50.ema` | `ema_200.ema` | - | both | obs=False, eps=0.0, gap=0, limit=None | left<right ↔ left>right |
| `rsi_14_oversold_30` | `RSI` | fx | `rsi_14.rsi` | `-` | 30.0 | both | obs=False, eps=0.0, gap=0, limit=None | below/above 30.0 |
| `rsi_14_overbought_70` | `RSI` | fx | `rsi_14.rsi` | `-` | 70.0 | both | obs=False, eps=0.0, gap=0, limit=None | below/above 70.0 |
| `ppo_signal` | `PPO` | fx | `ppo_12_26_9.ppo` | `ppo_12_26_9.signal` | - | both | obs=False, eps=0.0, gap=0, limit=None | left<right ↔ left>right |
| `ppo_histogram_zero` | `PPO` | fx | `ppo_12_26_9.histogram` | `-` | 0.0 | both | obs=False, eps=0.0, gap=0, limit=None | below/above 0.0 |
| `rate_bollinger_lower` | `BOLLINGER` | fx | `price.close` | `bollinger_20_2.bands.lower` | - | both | obs=False, eps=0.0, gap=0, limit=None | left<right ↔ left>right |
| `rate_bollinger_middle` | `BOLLINGER` | fx | `price.close` | `bollinger_20_2.bands.middle` | - | both | obs=False, eps=0.0, gap=0, limit=None | left<right ↔ left>right |
| `rate_bollinger_upper` | `BOLLINGER` | fx | `price.close` | `bollinger_20_2.bands.upper` | - | both | obs=False, eps=0.0, gap=0, limit=None | left<right ↔ left>right |
| `roc_20_zero` | `ROC` | fx | `roc_20.roc` | `-` | 0.0 | both | obs=False, eps=0.0, gap=0, limit=None | below/above 0.0 |
| `stoch_rsi_k_d` | `STOCH_RSI` | fx | `stoch_rsi_14_3.k` | `stoch_rsi_14_3.d` | - | both | obs=False, eps=0.0, gap=0, limit=None | left<right ↔ left>right |
| `stoch_rsi_k_oversold_20` | `STOCH_RSI` | fx | `stoch_rsi_14_3.k` | `-` | 20.0 | both | obs=False, eps=0.0, gap=0, limit=None | below/above 20.0 |
| `stoch_rsi_k_overbought_80` | `STOCH_RSI` | fx | `stoch_rsi_14_3.k` | `-` | 80.0 | both | obs=False, eps=0.0, gap=0, limit=None | below/above 80.0 |

Conferma elenco storico: presenti price/EMA20, EMA20/50, EMA50/200, RSI30/70, MACD/signal+hist/0, MFI20/80, Bollinger lower/middle/upper, ADX25, StochRSI K/D+20/80, Donchian lower/middle/upper; PPO/signal+hist/0 e ROC0 sono FX-only. Non risultano altri eventi curati.

### Dove un evento può essere perso o alterato

- La compressione bucket non perde eventi: `assign_discrete_events` li conserva tutti.
- Source/series mancante → annotation warning nel SignalResult; AI Export scarta warning e quindi l'assenza è invisibile.
- SignalResult non OK/PARTIAL → tutte le sue annotazioni sono escluse.
- Gap di cadence o valore null/non-finite resetta lo stato e impedisce cross attraverso il gap.
- Dedup first-seen elimina collisioni con stessa `(asset, instance, key, date)`.
- Backward-fill e `observed_only=false` possono aggiungere eventi sintetici; `epsilon=0` può aggiungere eventi da rumore.

## Bucket e aggregazioni

### Indicatori

- Scalar: statistiche datate first/min/max/last; representative UI determinato da `LAST|FIRST|MIN|MAX_WITH_RANGE`.
- Band: lower min, middle last, upper max; ogni componente conserva date indipendenti.
- Eventi: verbatim.
- Drawdown plugin dichiara MIN ma non è nel bundle.

### Prezzi/rate/performance

- `PriceBucket` perde le date degli extrema e aggrega solo close/rate.
- `simple_return` è intra-bucket, non previous-last → daily zero.
- `PerformanceBucketRow` perde date min/max e calcola start/end/P&L intra-bucket → daily zero.
- FX return series usa differenze day-over-day sulla serie calendar-backfilled; i weekend aggiungono ritorni zero e influenzano la volatilità.

## FIFO e in-transit

### Modello sorgente

- Transfer pair produce `TRANSFER_DEPART/ARRIVE`, source/destination, pair id e finestra transit (`fifo_lot_engine.py:450-503`).
- Se depart < arrive viene aperto un fragment `custody_type=IN_TRANSIT` con source/destination (`fifo_lot_engine.py:782-825`).
- Stato lot aggiunge `IN_TRANSIT` se esiste un fragment attivo (`fifo_lot_engine.py:313-330`).
- `LotSummarySchema` conserva current_custody; timeline conserva transaction/pair/source/destination/fragment (`schemas/portfolio.py:567-615,641-678`).

### Export effettivo

- Portfolio/Broker `FifoLotRow` conserva quantità, costi, valori, P&L, income/fees/taxes, value source, status e `states`; omette current_custody, transfer IDs e timeline (`payloads/portfolio_broker.py:240-271,359-400`).
- Asset `lot_detail` conserva current_custody BROKER/IN_TRANSIT ma omette P&L, fees/taxes, states, source/destination e timeline (`asset_payloads.py:391-438`).
- Portfolio ha summary+lots; Broker solo lots.
- Cutoff chiusi = `period_start`; open/partial sempre inclusi; nessun 7+3/10 nel runtime corrente.

### Sufficienza prompt FIFO

`portfolio.fifo_review` e `broker.fifo_review` possono identificare il tag IN_TRANSIT, ma non spiegare origine, destinazione, custody corrente, date depart/arrive o pair. Dati esistenti nel modello sorgente non vengono serializzati.

## Review di sufficienza delle 17 analisi

### Composizione catalogica

| Analysis ID | Required datasets | Optional datasets |
|---|---|---|
| `portfolio.pac_planning` | `portfolio.overview`, `portfolio.performance_flows` | nessuno |
| `portfolio.rebalancing` | `portfolio.overview` | `portfolio.performance_flows`, `portfolio.technical` |
| `portfolio.performance_attribution` | `portfolio.overview`, `portfolio.performance_flows` | nessuno |
| `portfolio.income_review` | `portfolio.overview`, `portfolio.performance_flows` | nessuno |
| `portfolio.fifo_review` | `portfolio.overview`, `portfolio.fifo` | nessuno |
| `portfolio.technical_breadth` | `portfolio.overview`, `portfolio.technical` | nessuno |
| `portfolio.description` | `portfolio.overview` | `portfolio.performance_flows`, `portfolio.technical` |
| `broker.review` | `broker.overview`, `broker.performance_flows` | `broker.technical`, `broker.fifo` |
| `broker.cost_efficiency` | `broker.overview`, `broker.performance_flows` | nessuno |
| `broker.concentration_context` | `broker.overview` | `broker.technical` |
| `broker.fifo_review` | `broker.overview`, `broker.fifo` | nessuno |
| `asset.trend_analysis` | `asset.overview`, `asset.market_technical` | nessuno |
| `asset.position_review` | `asset.overview`, `asset.position_performance` | `asset.market_technical` |
| `asset.drawdown_recovery` | `asset.overview`, `asset.market_technical` | `asset.position_performance` |
| `fx.trend_review` | `fx.overview`, `fx.market_technical` | nessuno |
| `fx.conversion_timing` | `fx.overview`, `fx.market_technical` | `fx.direct_exposure` |
| `fx.exposure_impact` | `fx.overview`, `fx.direct_exposure` | `fx.market_technical` |

### Conclusione per analisi

| Analysis ID | Required sufficient | Optional only enrich | Prompt promises unsupported | Missing deterministic fields | Overlap | Recommended change |
|---|---|---|---|---|---|---|
| `portfolio.pac_planning` | yes | n/a | Nessuna se budget/orizzonte/target/rischio sono trattati come input utente. | Budget, orizzonte, target e preferenze rischio: informazioni LLM/user, non generazione tecnica. | nessuna forte | Nessuna modifica obbligatoria. |
| `portfolio.rebalancing` | no, non per tutta la wording corrente | no | Measured costs/taxes e confronto cash-flow-only/one-time/mixed non sono garantiti dal solo overview. | Storico flussi/costi/tasse se `performance_flows` viene omesso. | income_review; performance_attribution | Rendere `performance_flows` required oppure rendere esplicitamente condizionali costi/flussi. |
| `portfolio.performance_attribution` | yes | n/a | Nessuna evidente. | Nessuno deterministico rilevante. | income_review | Nessuna. |
| `portfolio.income_review` | yes | n/a | Nessuna evidente. | Dettaglio per categoria di reddito può dipendere dagli effect descriptions. | performance_attribution | Nessuna prioritaria. |
| `portfolio.fifo_review` | partial | n/a | Transfer/in-transit non spiegabile oltre al tag `IN_TRANSIT`. | current_custody, source/destination broker, pair/timeline. | broker.fifo_review | Arricchire FIFO row o aggiungere componente transfer/custody. |
| `portfolio.technical_breadth` | partial | n/a | Per-indicator evaluated count/weight/date/family assenti; portfolio multi-broker può 503. | Denominatori e date per stato; risk/drawdown family. | asset.trend_analysis | Correggere universo multi-broker e payload breadth. |
| `portfolio.description` | partial | no | Stale values/data quality/coverage non garantiti dall'overview; technical omission è silenziosa. | Staleness per prezzo, diagnostics e coverage esplicita. | overview data export | Rendere wording coverage/stale condizionale o serializzare i metadati. |
| `broker.review` | partial | no | Promette FIFO ma `broker.fifo` opzionale contiene tutti i lotti, senza summary; forte overlap. | Summary FIFO aggregato broker. | broker.fifo_review | Togliere i lotti dalla review generale o introdurre un summary separato. |
| `broker.cost_efficiency` | no | n/a | Efficiency non misurabile senza denominatori di attività/capitale. | Numero operazioni, traded notional, capitale medio, fee categories, FX costs. | broker.review | Rinominare in cost review o aggiungere metriche deterministiche. |
| `broker.concentration_context` | yes | yes | Nessuna evidente. | Nessuno essenziale. | broker.review | Nessuna prioritaria. |
| `broker.fifo_review` | partial | n/a | In-transit senza custody/transfer timeline. | source/destination/current custody/pair. | broker.review | Arricchire il dataset FIFO dedicato. |
| `asset.trend_analysis` | conditional | n/a | Serie può essere mixed-currency; indicatori/eventi omessi senza diagnostica. | Conversion completeness, params/warmup/status. | asset.drawdown_recovery | Fail closed o separare serie native/target e serializzare diagnostica. |
| `asset.position_review` | no per Portfolio Role | yes per market technical | Response contract promette Portfolio Role; `position_scope` non ha peso. FIFO component optional può sparire. | Peso/concentrazione nel portafoglio; custody economica completa. | asset drawdown/trend solo marginale | Aggiungere peso o ridurre la promessa; rendere FIFO condizionale. |
| `asset.drawdown_recovery` | no | yes | Nessun `RISK_DRAWDOWN`; nessuna peak/trough date, durata, recovery, distance-to-peak o episodi. | Drawdown series/episodes e date reali. | asset.trend_analysis | Includere plugin/metriche drawdown o rimuovere l'analisi. |
| `fx.trend_review` | conditional | n/a | Overview dipende dal warm-up tecnico antico; eventi su requested dates backfilled. | Effective-date provenance nelle serie/eventi. | fx.conversion_timing | Disaccoppiare overview dal warm-up e conservare date effettive. |
| `fx.conversion_timing` | conditional | yes | Stesso coupling warm-up; nessuna previsione puntuale, dati sufficienti solo se technical costruisce. | Execution constraints sono input LLM/user. | fx.trend_review | Disaccoppiare overview; mantenere exposure opzionale. |
| `fx.exposure_impact` | partial | yes | Overview può 503 per warm-up; ENGINE_VALUATION senza native amount/sensitivity; nomi asset/broker assenti. | Economic direction/sensitivity, identity labels, native amount quando derivabile. | fx.conversion_timing | Disaccoppiare overview e arricchire righe o rendere l'impatto solo qualitativo. |

### Required/optional con semantica non chiara

- `portfolio.rebalancing`: `performance_flows` optional, ma wording richiede costi/flussi misurati.
- `portfolio.description`: performance/technical optional, ma wording promette performance, technical context, stale/coverage.
- `broker.review`: technical e FIFO optional, ma obiettivo/response contract li nomina esplicitamente.
- `asset.position_review`: `asset.market_technical` è davvero arricchimento; invece `asset.lot_detail` è un componente optional dentro un dataset required e può sparire senza manifest.
- `fx.exposure_impact`: market_technical è arricchimento, ma l'overview required è indirettamente accoppiato allo stesso warm-up tecnico.

### Informazioni tecniche vs informazioni LLM

Devono vincolare la generazione tecnica: identity/scope, valuta, periodo, componenti, conversion completeness, parametri indicatori, warm-up/status, coverage/omissioni, dates/provenance, denominator fields. Possono essere richieste dal LLM: budget PAC, orizzonte, target allocation, tolleranze, preferenze rischio, vincoli fiscali personali, obiettivi di spesa/reinvestimento. Non servono nuovi controlli UI per il secondo gruppo.

## Problemi confermati

| Priorità | Problema | Impatto |
|---|---|---|
| P0 | Portfolio technical duplicate asset across brokers | 503 su portafogli normali; optional technical può sparire silenziosamente |
| P0 | Mixed-currency Asset technical series | currency falsa, return corrotti, indicatori omessi senza warning |
| P0 | Intra-bucket return/P&L | bucket giornalieri sempre zero; perdita del delta inter-bucket |
| P0 | Synthetic/noise annotations | eventi su backward-fill/weekend e cross float |
| P0 | Drawdown analysis senza Drawdown | prompt non supportato dai dati |
| P0 | FX overview accoppiato al warm-up | 503 evitabile su overview/exposure |
| P1 | Silent optional/signal omissions | manifest non auditabile; LLM ignora cosa manca |
| P1 | Indicator payload drops params/status/warmup/version | semantica tecnica incompleta |
| P1 | Breadth denominator/date insufficient | ratio non auditabile per indicatore |
| P1 | FIFO in-transit fields insufficient | review trasferimenti incompleta |
| P1 | Broker review/FIFO overlap | all-lot dump duplicato; nessun broker summary |
| P1 | Cost efficiency missing denominators | efficienza non misurabile |
| P1 | Position Review missing portfolio weight | response contract over-promises |
| P1 | FX impact lacks explicit sensitivity/names | impatto solo parzialmente deterministico |
| P1 | Payload size unbounded | output reale fino a ~666k token stimati |
| P2 | Legacy stack/tests still present | drift, letture errate, test verdi non rappresentativi |

## Correzioni raccomandate, ordinate per priorità

### P0 — correttezza

1. Aggregare l'universo tecnico per asset_id prima della bulk price query e sommare correttamente i pesi multi-broker.
2. Vietare serie mixed-currency: fail closed per asset o separare serie native/target; serializzare conversion completeness.
3. Calcolare ritorni/P&L rispetto al previous bucket last/previous day, non first interno.
4. Impostare `observed_only=true` per asset market e una epsilon esplicita; conservare requested/effective date.
5. Includere RISK_DRAWDOWN e payload episode geometry oppure sospendere/riscrivere drawdown_recovery.
6. Separare rate overview visibile dalla serie tecnica warm-up.

### P1 — auditabilità e sufficienza

7. Esporre diagnostics/omissioni nel manifest e per indicatori: status, params, version, warmup, warnings, availability.
8. Aggiungere date extrema ai price/performance bucket.
9. Breadth: evaluated_count/weight, matching_count/weight, state_date, category.
10. FIFO: current custody + transfer source/destination/date/pair o componente timeline dedicato.
11. Allineare i 17 prompt ai dati: rebalancing, broker review, cost efficiency, position role, FX impact.
12. Definire policy operativa token senza truncation implicita: hard validation/warning o export segmentato esplicito.

### P2 — manutenzione

13. Eliminare o isolare chiaramente legacy task/profile stack e separarne i test.
14. Aggiungere integrazione API/DB reale: multi-broker stesso asset, FX history corta, conversion parziale, in-transit.

## Questioni ancora aperte

- Gli indicatori Asset devono usare sessioni di mercato osservate o calendario backward-filled?
- Per FX, weekend carry-forward deve partecipare a indicatori/volatilità/eventi?
- Il payload deve fallire se una conversione è parziale o mantenere due serie separate?
- Quale budget massimo è accettabile senza violare la regola no-truncation?
- Broker review deve mantenere un FIFO summary aggregato o eliminare del tutto FIFO?
- Drawdown deve esportare singolo episodio corrente o tutti gli episodi comparabili?

## Test e comandi eseguiti

| Comando/diagnostica | Esito |
|---|---|
| pytest composer/runtime/temporal/technical/annotations/plugins/lots | `289 passed in 25.45s` |
| `./dev.py test schemas ai-export` | `112 passed` |
| `./dev.py test api ai-export` | `14 passed` (service HTTP mockato) |
| inventory runtime via registries/Pydantic | 45 componenti, 18 dataset, 17 analisi, 17 plugin usati, 20/12 istanze |
| probe HTTP reale su DB test | 11 selezioni; risultati e failure descritti nell'Executive summary |
| root-cause probe service | duplicate asset IDs; FX warm-up missing ancient rate |
| event diagnostic AAPL | 517 eventi, 52 weekend, float-noise cross |
| bucket diagnostic Full | almeno 16 recenti daily; `simple_return=0` su ogni bucket da 1 giorno |

## Divergenze codice/test/report

- I test API verificano mapping HTTP con `MagicMock` del service (`test_api/test_ai_export_api.py:38-54,150-153`), quindi non rilevano failure DB/componenti reali.
- Il runner schema include ancora test del contratto legacy 19 task insieme al runtime 18/17.
- Commenti e file legacy continuano a descrivere 7+8 sampling, top-N, cap eventi e cutoff tre mesi, mentre il runtime pubblico non li usa.
- Il precedente report di composizione era corretto sulle unioni catalogiche, ma non descriveva omissioni, payload fields, mixed currency, real failure paths o sufficienza dei prompt.
