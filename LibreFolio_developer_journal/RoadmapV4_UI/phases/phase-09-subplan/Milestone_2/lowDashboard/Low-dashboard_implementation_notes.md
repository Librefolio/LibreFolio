# Low Dashboard — Implementation Notes (Holdings / Performance refactor)

Data: 2026-07-06. Esecuzione in 4 stage (backend sequenziale → frontend parallelo → integrazione → rifinitura),
basata su `Low-dashboard_refactor.md` (design) e `Low-dashboard_gap_analysis.md` (gap analysis preliminare).

## 1. File modificati/creati

### Backend
- `backend/app/services/portfolio_service.py` — riscritto `get_summary()` (Holdings date-aware), fixato
  `get_positions_contribution()` (bias temporali), aggiunto `_compute_period_summary_metrics()` (dedup logica NAV/P&L
  periodo, riusata sia da `get_summary()` che da `get_positions_contribution()`), popolamento `other_effects`.
- `backend/app/services/portfolio_engine.py` — piccolo fix di corredo: `dataQuality.transactionImplied` ora
  include `as_of_date` (data dell'ultimo daily state) nei `message_params`, così il banner qualità dati può
  mostrare la data di riferimento del prezzo mancante invece di un messaggio generico. Chiave i18n aggiornata
  con placeholder `{as_of_date}` in tutte e 4 le lingue (nessun cambio frontend necessario: `DataQualityBanner.svelte`
  spreadga già genericamente `message_params` nell'interpolazione i18n).
- `backend/app/schemas/portfolio.py` — `AssetPeriodContribution` esteso con `start_value`/`end_value`; nuovo schema
  `OtherPeriodEffect`; `PositionsContribution.other_effects: List[OtherPeriodEffect]`.
- `backend/test_scripts/test_services/test_financial/test_portfolio_service.py` — nuova classe
  `TestPortfolioServiceDateAwareDashboardData` (2 test: holdings snapshot a `date_to`, positions_contribution
  date-aware + other_effects).
- `backend/test_scripts/test_api/test_portfolio_api.py` — nuovo test `test_report_positions_contribution_is_date_aware`.

### Frontend
- `frontend/src/lib/components/dashboard/ExposureTable.svelte` — riscritto in tabella **Holdings**: rimossa modalità
  closed e colonne periodo (Realized/Costs/Δ1D); aggiunte `P&L % / Quantity / Price / PMC`. Props ora:
  `{holdings, navAmount, displayCurrency, brokers?}` (rimossi `positionFilter`/`contribution`).
- `frontend/src/lib/components/dashboard/ExposureTreemap.svelte` — nessuna modifica funzionale necessaria (già
  compatibile: area=Value, colore=Unrealized P&L%, nessun concetto "closed" al suo interno); verificata icone/i18n
  tipo asset già corrette.
- `frontend/src/lib/components/dashboard/ContributionTable.svelte` — riscritto in tabella **Performance** unificata
  (aperte+chiuse insieme): aggiunte colonne `Unrealized Δ / Realized Sales / Income / Costs / Start Value /
  End Value / Status`; rimossa `Period P&L %`; `Status` è colonna filtrabile nativa DataTable (enum filter,
  valori `open_at_period_end`/`closed_by_period_end`), non più toggle esterno al pannello. Props ora:
  `{positions, displayCurrency?, brokers?}` — il genitore NON pre-filtra più open/closed.
- `frontend/src/lib/components/dashboard/OtherPeriodEffectsTable.svelte` (**nuovo**) — sezione compatta sotto la
  tabella Performance per righe non asset-specific (`Description/Category/Period P&L/Broker`), nascosta se vuota.
  Categoria tradotta (vedi §4), non più mostrata come stringa raw dal backend.
- `frontend/src/lib/components/dashboard/PerformanceChart.svelte` (**nuovo**) — stacked diverging horizontal bar
  chart ECharts: componenti split per segno (stack `positive`/`negative` separati, non un unico stack lineare),
  costs sempre trattato come negativo nel grafico (`period_fees_taxes` è positivo nel DTO ma rappresenta un costo),
  sezione "Other Period Effects" inclusa sotto un divider, tooltip con Status/Start/End Value/Broker.
- `frontend/src/lib/components/dashboard/ContributionTreemap.svelte` — **rimosso** (sostituito interamente da
  `PerformanceChart.svelte`; nessun altro riferimento residuo nel codebase, verificato prima della rimozione).
- `frontend/src/lib/components/dashboard/PositionsPanel.svelte` — tab rinominate `Exposure/Contribution` →
  `Holdings/Performance` (con back-compat automatico per il valore cached in localStorage); **rimosso il toggle
  globale Open/Closed** (Holdings non ne ha più bisogno, Performance lo gestisce internamente via colonna Status);
  wiring dei 5 componenti Stage 2; `Other Period Effects` montato sotto la tabella Performance.
- `frontend/src/lib/components/charts/echartsTreemapZoomGuard.ts` — fix pan: ECharts dispatcha un'azione separata
  per il pan (`treemapMove`) rispetto allo zoom (`treemapRender`); il guard ora ascolta entrambi gli eventi,
  impedendo che il pan sposti il treemap oltre i bordi del container a qualunque livello di zoom.
- `frontend/src/lib/i18n/{en,it,fr,es}.json` — rimosse chiavi morte `dashboard.exposure`/`dashboard.contribution`;
  aggiunte 17 nuove chiavi `dashboard.*` (colonne Holdings/Performance, tab label, Other Period Effects, status,
  resetZoom, categorie) + `common.category` in tutte e 4 le lingue. Fix chiave stale `assets.types.CROWDFUND_LOAN`
  → `assets.types.CROWDFUND` (rename backend enum di un round precedente mai riflesso in i18n).
- `frontend/e2e/portfolio/broker-icons.spec.ts` — aggiornato ai nuovi `data-testid` (`positions-toggle-holdings`
  al posto di `positions-toggle-exposure`/`positions-toggle-open`, rimossi).

## 2. Componenti riusati (nessuna riscrittura da zero)

- `ExposureTable`/`ExposureTreemap`: asset/broker cell, formatter valuta, `BrokerBadge`, wiring `DataTable`.
- `ContributionTable`: mapping asset+broker, sort per `abs(period_pnl)`, navigazione dettaglio asset via
  doppio click/long press.
- `PerformanceChart`: tema/tooltip da `echartsTooltipHelpers.ts`, pattern lifecycle ECharts (init/resize/dispose)
  già usato dai treemap.
- Endpoint `/portfolio/report` confermato come entrypoint unico — nessun nuovo endpoint creato.

## 3. Componenti rimossi/deprecati

- `ContributionTreemap.svelte` — eliminato (sostituito da `PerformanceChart.svelte`).
- Toggle globale Open/Closed nel pannello (`positions-filter-toggle`) — eliminato (Status ora è filtro colonna
  nella tabella Performance).
- Chiavi i18n `dashboard.exposure`/`dashboard.contribution` — eliminate (dead code, nessun riferimento residuo).

## 4. Garanzie di coerenza temporale

- **Holdings**: fonte dati passata da `get_summary()`'s current/today-biased loop (`today = date_type.today()`,
  `_get_latest_price()`, quantità netta all-time) a `engine_result.position_states_end`, calcolato dal motore
  ESATTAMENTE a `self.date_to` (`portfolio_engine.py`). Filtro `quantity > 0` garantisce solo posizioni aperte a
  `date_to`. `price_change_1d` ora calcolato relativo a `date_to`, non a "oggi".
- **Performance**: `qty_at_end` ora filtra `tx.date <= effective_end` (prima non filtrava, includeva transazioni
  future rispetto al periodo); lato finale usa `price_at_or_before(date_to)` invece di `_get_latest_price()`;
  `is_fully_sold`/Status quindi riferito correttamente a `date_to`. Righe income-only/fees-only ora hanno
  `is_fully_sold=True, start_value=0, end_value=0` (prima `is_fully_sold=False` hard-coded, errato).
- **Filtro posizioni irrilevanti**: aggiunto skip per asset senza attività di periodo E senza posizione al
  confine (`qty_at_start=0 and qty_at_end=0`), per non includere righe fantasma non pertinenti al periodo.
- `get_report()` ora passa `_precomputed_engine_result` a `get_positions_contribution()` per evitare un secondo
  giro completo del motore quando `get_summary()` è già stato calcolato nella stessa richiesta.

## 5. Riconciliazione Performance + Other Period Effects vs `summary.period_pnl`

Garantita **per costruzione algebrica**, non solo verificata empiricamente:

```
period_other_result = period_pnl_total − period_ugl_delta − total_realized − total_income + total_fees
```

dove `total_realized/income/fees` sommano SIA le componenti per-asset SIA quelle unallocated. Questo residuo
diventa una riga esplicita "Other / reconciliation residual" (categoria "Other", broker=null) in `other_effects`
quando ≠ 0. Per costruzione algebrica:

```
Σ(positions[].period_pnl) + Σ(other_effects[].period_pnl) ≡ summary.period_pnl
```

sempre, qualunque sia il caso (nessuna divergenza silenziosa possibile — un eventuale disallineamento dei dati
di origine si manifesta come residuo più grande in "Other Period Effects", non come bug nascosto). Verificato
concretamente nel test `test_positions_contribution_uses_date_to_and_other_effects` (caso con
`100 + 15 = 115 = summary.period_pnl`) e via test API `test_report_positions_contribution_is_date_aware`.

## 6. Esito verifiche finali

- **Backend**: `pytest backend/test_scripts/test_api/test_portfolio_api.py
  backend/test_scripts/test_services/test_financial/test_portfolio_service.py` → **35/35 PASSED**.
  `ruff check` + `black --check` su `portfolio_service.py`/`portfolio.py` → puliti.
  (6 fallimenti pre-esistenti e NON correlati in `test_transaction_implied.py`, causati da un mismatch di firma
  in `DailyStateBuilder.__init__` — nessun parametro `wac_series` nella versione attuale del costruttore — bug
  pre-esistente scoperto durante la verifica, non introdotto da questo lavoro, e out of scope per questo task.)
- **Frontend**: `svelte-check` → **0 errori, 0 warning**. `npm run build:debug` → build completa OK, nessun
  warning nuovo. `prettier --check` → pulito su tutti i file toccati.
- TypeScript client rigenerato (`./dev.py api sync`) dopo le modifiche DTO backend.

## 7. Limiti residui / edge case aperti

- **`test_transaction_implied.py`** (6 test) resta rotto per un problema pre-esistente non correlato
  (`DailyStateBuilder` — parametro test obsoleto `wac_series`) — da sistemare in un task dedicato separato.
- **PMC/Price in valuta nativa vs display currency**: restano convertiti in target/display currency come già
  in precedenza; il design non specificava esplicitamente questo comportamento — nessuna modifica.
- **Duplicati asset su broker diversi**: sia tabella che chart restano keyed per `(asset_id, broker_id)`, quindi
  lo stesso asset su due broker produce due righe distinte — comportamento coerente con la colonna Broker
  esistente, non modificato.
- **Resize colonne DataTable**: l'utente aveva segnalato in passato che l'icona di resize appare ma il click non
  ha effetto in alcune tabelle — non affrontato in questo giro (componente `DataTable` condiviso, fuori scope;
  segnalato dagli agenti Stage 2 ma non investigato a fondo).
- Nessun altro limite noto oltre a quelli sopra elencati.
