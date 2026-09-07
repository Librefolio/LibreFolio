# AI Export F1 — Contratto task, profili e detail overlay

**Versione contratto**: 1
**Data**: 27 luglio 2026
**Stato**: 🟡 estensione FIFO in implementazione

← Piano:
[AI Export Backend Snapshot e Hard Cutover](./plan-phase00AiExportBackendSnapshotImplementation.prompt.md)

## 1. Regola di composizione

Il catalogo contiene:

- 19 task spec;
- 3 detail overlay;
- 57 profili risolti.

```text
profile = task_spec + detail_overlay
profile_id = <domain>.<task>.<detail_level>
```

Non esiste:

- un default profile nascosto;
- un top-N globale;
- auto-enrollment dal Signal Plugin Registry;
- un task selezionabile senza response contract frontend.

Ogni profilo usa:

```yaml
schema_version: 1
profile_version: 1
frontend_response_contract_version: 1
```

## 2. Detail overlay

### 2.1 Compact

- facts e stati latest;
- aggregati completi;
- serie assenti salvo eccezione task-specifica;
- eventi recenti limitati;
- massimo 10 eventi dopo deduplica;
- selezione entità dichiarata dal task;
- metadata obbligatori:
  - `total_entity_count`;
  - `included_entity_count`;
  - `selection_rule`;
  - `total_nav_weight_pct`;
  - `included_nav_weight_pct`.

Asset e FX sono single-entity: compact riduce campi/serie, non l'entità.

### 2.2 Standard

- tutte le posizioni aperte;
- tutte le contribution previste dal task;
- nessun top-N;
- technical summary per tutti gli asset eleggibili;
- ultimi 7 punti osservati daily;
- fino a 8 punti weekly precedenti;
- eventi curati;
- massimo 40 eventi dopo deduplica;
- allocazioni complete.

### 2.3 Full

- tutte le entità;
- tutte le contribution;
- bundle tecnico full allow-listed;
- weekly sull'intera technical window;
- ultimi 7 daily;
- annotazioni;
- massimo 120 eventi dopo deduplica;
- FIFO per-lot sintetico dove previsto, senza timeline;
- nessun top-N.

## 3. Bundle tecnici

I parametri sono parte del profilo e non arrivano dal browser.

### 3.1 Asset compact

- EMA20;
- EMA50;
- EMA200;
- RSI14;
- MACD12/26/9;
- Bollinger20/2;
- NATR14;
- latest state soltanto;
- recent core events;
- MFI14 solo con volume eleggibile.

### 3.2 Asset standard

- EMA20/50/200;
- ADX14;
- Donchian20;
- RSI14;
- MACD12/26/9;
- Stochastic RSI14/%D3;
- Bollinger20/2;
- NATR14;
- MFI14 se volume eleggibile;
- OBV state/event-only se volume eleggibile.

### 3.3 Asset full

Bundle statico:

- EMA20/50/200;
- SMA50/200;
- KAMA20;
- Aroon25;
- ADX14;
- Donchian20;
- RSI14;
- MACD12/26/9;
- PPO12/26/9;
- ROC20;
- Stochastic RSI14/%D3;
- CCI20;
- Bollinger20/2;
- ATR14;
- NATR14;
- MFI14 se volume eleggibile;
- OBV se volume eleggibile.

### 3.4 FX compact

- EMA20/50/200;
- RSI14;
- PPO12/26/9;
- Bollinger20/2;
- latest state ed eventi core.

### 3.5 FX standard

- EMA20/50/200;
- RSI14;
- PPO12/26/9;
- Bollinger20/2;
- ROC20;
- Stochastic RSI14/%D3;
- KAMA20.

### 3.6 FX full

- EMA20/50/200;
- SMA50/200;
- KAMA20;
- RSI14;
- MACD12/26/9;
- PPO12/26/9;
- ROC20;
- Stochastic RSI14/%D3;
- Bollinger20/2.

## 4. Annotazioni core

Asset:

- price/EMA20;
- EMA20/EMA50;
- EMA50/EMA200;
- RSI 30/70;
- MACD/signal;
- MACD histogram/zero;
- ADX threshold;
- Stochastic RSI `%K/%D`;
- Stochastic RSI 20/80;
- MFI 20/80;
- price/Bollinger lower/middle/upper;
- price/Donchian lower/middle/upper.

FX:

- rate/EMA20;
- EMA20/EMA50;
- EMA50/EMA200;
- RSI 30/70;
- PPO/signal;
- PPO histogram/zero;
- ROC/zero;
- Stochastic RSI `%K/%D`;
- Stochastic RSI 20/80;
- rate/Bollinger lower/middle/upper.

Event limit e deduplica sono detail/task-specific.

## 5. Portfolio task

| Task | Compact selection | Tecnica compact/standard/full | User notes | Web research |
|---|---|---|---|---|
| `pac_planning` | union: 6 maggiori NAV + 6 minori posizioni non-zero | latest breadth / standard summary / full | sì | opzionale |
| `rebalancing` | 12 maggiori NAV; nessun target drift inventato | latest breadth / standard summary / full | sì | opzionale |
| `performance_attribution` | 5 migliori + 5 peggiori `period_pnl_amount` | none / latest states / sampled standard | sì | no |
| `income_review` | 10 maggiori `period_income_amount` | none / latest states / sampled standard | sì | no |
| `portfolio_fifo_lot_review` | 7 maggiori residual cost basis aperti/parziali + 3 chiusi più recenti; backfill fino a 10 | none / none / none | sì | no |
| `technical_breadth` | aggregati completi + 10 eventi recenti pesati NAV | breadth only / standard / full | no | opzionale |
| `portfolio_description` | 10 maggiori NAV | none / standard summary / sampled standard | sì | no |

Regole:

- `pac_planning` non inventa target allocation;
- `rebalancing` deve chiedere target/range di tolleranza mancanti;
- `portfolio_fifo_lot_review` segue il filtro broker attivo della Dashboard;
- breadth aggregata usa sempre l'intero universo eleggibile;
- compact limita soltanto il dettaglio entità, non gli aggregati.

## 6. Asset task

| Task | Compact | Standard | Full | User notes | Web research |
|---|---|---|---|---|---|
| `asset_snapshot` | facts + latest states | asset standard | asset full | sì | opzionale |
| `asset_trend_analysis` | latest trend/momentum/volatility | asset standard + series | asset full | sì | opzionale |
| `position_review` | position + latest states | position/FIFO + standard | position/FIFO + full | sì | no |
| `asset_pac_timing_context` | latest neutral context | standard + sampled | full | sì | opzionale |
| `drawdown_recovery` | extrema/drawdown latest | standard + recovery events | full | sì | opzionale |

Applicability:

- `asset_snapshot`: asset esistente;
- `asset_trend_analysis`: asset esistente, tecnica opzionale;
- `position_review`: quantità aperta positiva nello scope;
- `asset_pac_timing_context`: asset esistente;
- `drawdown_recovery`: almeno due osservazioni e un massimo precedente misurabile.

## 7. FX task

| Task | Compact | Standard | Full | User notes | Web research |
|---|---|---|---|---|---|
| `fx_trend_review` | rate + latest states | FX standard | FX full | sì | opzionale |
| `fx_exposure_impact` | exposure aggregate + latest states | linked cash/positions + standard | linked cash/positions + full | sì | opzionale |
| `fx_conversion_timing_context` | latest trend/volatility | standard + sampled | full | sì | opzionale |

Applicability:

- pair ISO valida;
- exposure impact richiede cash balance o posizione collegabile;
- linkage = trading/valuation currency, non look-through;
- nessuna exposure autorevole → `task_not_applicable`.

## 8. Broker task

| Task | Compact selection | Tecnica compact/standard/full | User notes | Web research |
|---|---|---|---|---|
| `broker_review` | 10 maggiori NAV | breadth / standard / full | sì | no |
| `broker_cost_efficiency` | 10 maggiori `abs(period_fees_taxes_amount)` | none / latest states / sampled standard | sì | no |
| `broker_concentration_context` | 10 maggiori NAV | breadth / standard / full | sì | no |
| `broker_fifo_lot_review` | 7 maggiori residual cost basis aperti/parziali + 3 chiusi più recenti; backfill fino a 10 | none / none / none | sì | no |

Applicability:

- broker accessibile via `BrokerUserAccess`;
- nessun `last_import_at` inferito;
- `latest_transaction_date` è l'unica attività temporale autorevole F1;
- FIFO richiede almeno un lotto aperto/parziale o chiuso nei tre mesi precedenti;
- standard/full includono tutte le righe FIFO eleggibili;
- nessun livello esporta custody/event/value/return/price history.

### 8.1 Contratto righe FIFO condiviso

- l'universo include tutti i lotti aperti o parziali;
- include inoltre i lotti completamente chiusi con `closing_date` nei tre mesi di
  calendario precedenti `snapshot_as_of`;
- `closing_date` deriva dalle closure autorevoli del `LotsAnalysisService`;
- gli asset sono scoperti anche dallo storico transazioni dello scope, non soltanto
  dalle posizioni correnti;
- la riga usa asset, data di apertura e broker di apertura come identità leggibile;
- `lot_id` e `opening_transaction_id` restano interni e non sono serializzati;
- ogni riga è una fotografia sintetica: quantità, costo residuo, valore, P&L,
  income, fee, tax, stato e fonte valutazione;
- tutti i response contract restano v1 finché il sistema non viene rilasciato.

## 9. Response contract ID

| Domain | Task | Response contract ID |
|---|---|---|
| portfolio | pac_planning | `portfolio.pac_planning` |
| portfolio | rebalancing | `portfolio.rebalancing` |
| portfolio | performance_attribution | `portfolio.performance_attribution` |
| portfolio | income_review | `portfolio.income_review` |
| portfolio | portfolio_fifo_lot_review | `portfolio.portfolio_fifo_lot_review` |
| portfolio | technical_breadth | `portfolio.technical_breadth` |
| portfolio | portfolio_description | `portfolio.portfolio_description` |
| asset | asset_snapshot | `asset.asset_snapshot` |
| asset | asset_trend_analysis | `asset.asset_trend_analysis` |
| asset | position_review | `asset.position_review` |
| asset | asset_pac_timing_context | `asset.asset_pac_timing_context` |
| asset | drawdown_recovery | `asset.drawdown_recovery` |
| fx | fx_trend_review | `fx.fx_trend_review` |
| fx | fx_exposure_impact | `fx.fx_exposure_impact` |
| fx | fx_conversion_timing_context | `fx.fx_conversion_timing_context` |
| broker | broker_review | `broker.broker_review` |
| broker | broker_cost_efficiency | `broker.broker_cost_efficiency` |
| broker | broker_concentration_context | `broker.broker_concentration_context` |
| broker | broker_fifo_lot_review | `broker.broker_fifo_lot_review` |

## 10. Omission e applicability

- asset/position non viene eliminato per segnale mancante;
- `partial` con punti entra;
- indicator/component/series/event vuoto viene omesso;
- nessuna failure prose nel prompt;
- un task non applicabile fallisce typed prima del rendering;
- compact selection è sempre dichiarata;
- standard/full non riducono la cardinalità;
- note non previste dal task non entrano.

## 11. Versioning

Incrementare:

- `schema_version` per cambio incompatibile DTO;
- `profile_version` per cambio dati/selezione/bundle/sampling;
- `frontend_response_contract_version` per cambio struttura risposta richiesta.

Nuovo plugin:

- non entra automaticamente;
- richiede modifica esplicita bundle;
- richiede semantic metadata;
- richiede fixture/profile version bump.
