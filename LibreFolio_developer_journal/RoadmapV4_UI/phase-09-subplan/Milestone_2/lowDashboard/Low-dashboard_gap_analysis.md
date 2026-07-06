# Low dashboard gap analysis

_Analisi eseguita sul codice attuale il 2026-07-06. Ho usato `dashboard-formulas-report.md` come baseline, ma quando report precedente e codice non coincidono, in questo documento prevale sempre il codice._

Riferimenti principali:
- Design desiderato: `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/lowDashboard/Low-dashboard_refactor.md:27-353`
- Report formule precedente: `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/lowDashboard/dashboard-formulas-report.md:317-551`

## 1. Executive summary

- **Gap più grande lato backend/semantico:** l’attuale sorgente di `Exposure`/`Holdings` non è uno snapshot a `date_to`; `PortfolioService.get_summary()` costruisce `summary.holdings` con `today`, quantità all-time e latest price (`backend/app/services/portfolio_service.py:631, 781-829`). Quindi tabella/treemap attuali non rispettano il significato “fotografia a fine periodo”.
- **Gap più grande lato Performance:** il backend ha già quasi tutti i componenti di P&L per asset (`period_unrealized_delta`, `period_realized_gain_loss`, `period_income`, `period_fees_taxes`, `period_pnl`, `is_fully_sold`), ma frontend oggi mostra solo `Period P&L`, `Period P&L %`, `Broker` (`backend/app/schemas/portfolio.py:285-323`, `frontend/src/lib/components/dashboard/ContributionTable.svelte:27-37, 131-196`).
- **Bug/deriva temporale da segnalare:** `get_positions_contribution()` oggi calcola `qty_at_end` senza filtro `<= date_to` e usa `_get_latest_price()` per il lato finale (`backend/app/services/portfolio_service.py:1439-1505`). Quindi `Status`, end-side valuation e parte della logica Contribution/Performance sono current-biased quando `date_to` è nel passato.
- **Treemap Holdings:** componente quasi riusabile as-is; semantica area/colore è già quella giusta (`ExposureTreemap.svelte:154-229, 263-271`), ma la fonte dati è sbagliata nel tempo.
- **Chart Performance:** non esiste già un componente riusabile per uno stacked diverging bar chart. Esistono solo treemap dedicate e helper per bar verticali tipo MACD, non per barre orizzontali divergenti con stack positivo/negativo (`ContributionTreemap.svelte:1-472`, `LineChart.svelte:281-309`, `lineChartHelpers.ts:370-394`).
- **Other Period Effects:** backend espone solo bucket aggregati `unallocated_income` / `unallocated_fees_taxes` per broker e un `period_other_result` aggregato di summary; manca shape UX-ready con `Description / Category / Period P&L / Broker` (`backend/app/schemas/portfolio.py:305-323, 341-373`).

## 2. Current implementation map

### 2.1 Frontend map

| Pezzo | File | Ruolo attuale |
|---|---|---|
| Dashboard page | `frontend/src/routes/(app)/dashboard/+page.svelte` | Carica report unificato, mantiene `summary`, `history`, `allocationHistoryFromReport`, `positionsContribution`, passa tutto a `PositionsPanel` e `RecentTransactionsPanel` (`+page.svelte:49-57, 203-225, 482-493`). |
| Portfolio store | `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts` | Wrapper cache per `POST /api/v1/portfolio/report`; `include_positions_contribution` è opzionale/lazy (`portfolioStore.svelte.ts:23-66, 124-170`). |
| Positions container | `frontend/src/lib/components/dashboard/PositionsPanel.svelte` | Gestisce semantic toggle `Exposure/Contribution`, visual toggle `Table/Map`, open/closed filter persistito in localStorage, e decide quale componente renderizzare (`PositionsPanel.svelte:33-44, 50-69, 95-145, 154-236`). |
| Exposure table | `frontend/src/lib/components/dashboard/ExposureTable.svelte` | Vista tabellare di `summary.holdings` (open) oppure `positions_contribution.positions.filter(is_fully_sold)` (closed) (`ExposureTable.svelte:37-44, 149-200, 249-364`). |
| Exposure treemap | `frontend/src/lib/components/dashboard/ExposureTreemap.svelte` | Treemap Broker → Asset Type → Asset; area=`current_value`, colore=`gain_loss_percent` (`ExposureTreemap.svelte:154-229, 263-379`). |
| Contribution table | `frontend/src/lib/components/dashboard/ContributionTable.svelte` | Tabella per-asset period attribution; oggi mostra solo `Asset / Period P&L / Period P&L % / Broker`; esclude esplicitamente righe unallocated (`ContributionTable.svelte:1-14, 27-37, 54-87, 131-196`). |
| Contribution treemap | `frontend/src/lib/components/dashboard/ContributionTreemap.svelte` | Doppia treemap gains/losses separata; area=`abs(period_pnl)`, colore=fisso per segno (`ContributionTreemap.svelte:1-12, 189-255, 312-399, 413-472`). |
| Recent transactions | `frontend/src/lib/components/dashboard/RecentTransactionsPanel.svelte` | Lista compatta read-only di transazioni recenti, separata da `/portfolio/report` (`RecentTransactionsPanel.svelte:34-45, 72-99, 114-142`). |

### 2.2 Backend / API map

| Pezzo | File | Ruolo attuale |
|---|---|---|
| Unified endpoint | `backend/app/api/v1/portfolio_api.py` | `POST /portfolio/report` ritorna `PortfolioReportResponse` e delega a `PortfolioService.get_report()` (`portfolio_api.py:155-174`). |
| Report DTO | `backend/app/schemas/portfolio.py` | `PortfolioHolding`, `AssetPeriodContribution`, `UnallocatedContribution`, `PositionsContribution`, `PortfolioSummary`, `PortfolioReportQuery`, `PortfolioReportResponse` (`portfolio.py:265-323, 341-383, 498-530`). |
| Holdings builder | `backend/app/services/portfolio_service.py` | `get_summary()` costruisce `summary.holdings` in loop separato dal motore giornaliero (`portfolio_service.py:655-933`). |
| Contribution builder | `backend/app/services/portfolio_service.py` | `get_positions_contribution()` calcola righe per `(broker_id, asset_id)` e bucket unallocated (`portfolio_service.py:1286-1595`). |
| Unified orchestration | `backend/app/services/portfolio_service.py` | `get_report()` lancia engine una volta per summary/history/allocation, ma poi richiama comunque `get_positions_contribution()` separatamente (`portfolio_service.py:1664-1772`). |
| Engine snapshots | `backend/app/services/portfolio_engine.py` | `DailyPositionState`, `position_states_end`, `per_realized`, `per_income`, `per_fees_taxes`, `unalloc_*` esistono già nel risultato engine (`portfolio_engine.py:347-365, 904-955, 1320-1339`). |

## 3. Desired design summary

Dal documento `Low-dashboard_refactor.md`:

- Tab semantiche da rinominare da `Exposure / Contribution` a `Holdings / Performance` (`Low-dashboard_refactor.md:5-23, 339-353`).
- **Holdings** = sole posizioni aperte a `date_to`; tabella con `Asset / Value / Weight / Unrealized P&L / P&L% / Quantity / Price / PMC / Broker`, treemap con `area = Value`, `color = Unrealized P&L %` (`Low-dashboard_refactor.md:27-105`).
- **Performance** = contributo al P&L del periodo; include posizioni aperte e chiuse rilevanti a `date_to`; tabella con `Asset / Period P&L / Unrealized Δ / Realized Sales / Income / Costs / Start Value / End Value / Status / Broker` (`Low-dashboard_refactor.md:109-150`).
- **Other Period Effects** = sezione separata sotto Performance per voci non asset-specific (`Description / Category / Period P&L / Broker`) (`Low-dashboard_refactor.md:154-181`).
- **Performance chart** = nuovo stacked diverging bar chart orizzontale con componenti `Unrealized Δ / Realized Sales / Income / Costs`; nessuna treemap Contribution nel design finale (`Low-dashboard_refactor.md:185-335`).
- **Recent Transactions** resta invariato nel concept (`Low-dashboard_refactor.md:17-22`).

## 4. Gap analysis by area

### 4.1 Holdings table

#### Componente attuale

- Container: `PositionsPanel` passa a `ExposureTable` queste props: `holdings`, `navAmount`, `displayCurrency`, `positionFilter`, `contribution`, `brokers` (`frontend/src/lib/components/dashboard/PositionsPanel.svelte:226-227`).
- Contratto locale di `ExposureTable`: `holdings`, `navAmount`, `displayCurrency`, `positionFilter`, `contribution`, `brokers` (`frontend/src/lib/components/dashboard/ExposureTable.svelte:37-44`).
- Shape locale del dato `Holding` consumato da `ExposureTable`: `asset_id`, `asset_name`, `asset_ticker`, `asset_type`, `broker_id`, `broker_name`, `current_value`, `nav_weight_percent`, `gain_loss`, `gain_loss_percent`, `price_change_1d` (`ExposureTable.svelte:23-35`).
- Colonne attuali in open mode: `Asset / Value / Weight / Δ1D % / Δ1D / Unrealized P&L / Realized / Costs / Broker` (`ExposureTable.svelte:289-364`).
- Colonne attuali in closed mode: `Asset / Realized / Costs / Period P&L / Broker` (`ExposureTable.svelte:249-286`).

#### Confronto col design desiderato

| Colonna desiderata | Stato attuale | Tipo gap | Note concrete |
|---|---|---|---|
| Asset | **Già presente** | FE riusabile | `assetColumn` esiste già in `ExposureTable.svelte:203-222`. |
| Value | **Già presente** | Semantic | Oggi usa `holding.current_value`, ma quel valore è current/today, non snapshot a `date_to` (`portfolio_service.py:799-829, 871-883`). |
| Weight | **Già presente** | Semantic | `nav_weight_percent` esiste già, ma oggi miscela `current_value` current con `engine_nav` a `date_to` (`portfolio_service.py:926-933`). |
| Unrealized P&L | **Già presente** | Semantic | Campo `gain_loss` già esposto (`portfolio.py:278-279`), ma è lifetime/current, non snapshot storico a `date_to`, perché deriva da holdings loop current (`portfolio_service.py:840-869`). |
| P&L % | **Dato backend esiste, UI no** | FE | `gain_loss_percent` è nel DTO (`portfolio.py:279`) e già usato dal treemap (`ExposureTreemap.svelte:208-227, 263-271`), ma la tabella non lo renderizza: compare solo nel type locale, poi sparisce (`ExposureTable.svelte:33`). |
| Quantity | **Dato backend esiste, UI no** | FE | `PortfolioHolding.quantity` esiste (`portfolio.py:274`). Frontend lo riceve già altrove: `aiExportBuilder.ts:210` legge `h.quantity`. `ExposureTable` però non lo dichiara né lo mostra (`ExposureTable.svelte:23-35`). |
| Price | **Dato backend esiste, UI no** | FE + Semantic | `PortfolioHolding.current_price` esiste (`portfolio.py:276`), ma `ExposureTable` non lo consuma. Inoltre oggi è prezzo latest/current in target currency, non prezzo a `date_to` (`portfolio_service.py:799-815`). |
| PMC | **Dato backend esiste, UI no** | FE + Semantic | `PortfolioHolding.wac_per_unit` esiste (`portfolio.py:275`) ed è già letto da `aiExportBuilder.ts:215`, ma `ExposureTable` non lo dichiara. Oggi è WAC as-of `today`, non as-of `date_to` (`portfolio_service.py:781-787`). |
| Broker | **Già presente** | FE riusabile | `brokerColumn` con `BrokerBadge` è già pronto (`ExposureTable.svelte:224-247`). |

#### Gap strutturali/semantici

- **Semantic gap:** `Holdings` nel design = sole posizioni aperte a `date_to`. L’attuale `ExposureTable` ha un intero branch `positionFilter === 'closed'` (`ExposureTable.svelte:149-171, 249-286`) che nel design finale non dovrebbe stare nella tab Holdings.
- **Semantic gap:** l’open mode attuale miscela colonne snapshot (`Value`, `Weight`, `Unrealized P&L`) con colonne period-based (`Realized`, `Costs`) via merge con `positions_contribution` (`ExposureTable.svelte:193-196, 342-361`). Nel design `Holdings` non dovrebbe mostrare P&L periodo.
- **BE/Semantic gap:** `get_summary()` usa `today = date_type.today()`, `compute_wac_iterative(... as_of_date=today)`, `net_qty = sum(...)` all-time, `_get_latest_price()`, `price_change_1d` vs yesterday (`portfolio_service.py:631, 781-829`). Quindi:
  - una posizione aperta a `date_to` ma chiusa oggi sparisce dalla Holdings attuale;
  - una posizione comprata dopo `date_to` può entrare nella Holdings attuale se oggi è aperta;
  - `Price`, `PMC`, `Value`, `Weight`, `Unrealized P&L` non sono storici.

### 4.2 Holdings chart (treemap)

#### Componente attuale

- `PositionsPanel` rende `ExposureTreemap` solo per `semanticMode === 'exposure' && visualMode === 'map'`; se il filtro è `closed`, switcha invece a `ContributionTreemap` (`frontend/src/lib/components/dashboard/PositionsPanel.svelte:228-236`).
- Props di `ExposureTreemap`: `holdings`, `displayCurrency` (`frontend/src/lib/components/dashboard/ExposureTreemap.svelte:37-42`).
- Semantica attuale:
  - gerarchia `Broker -> Asset Type -> Asset` (`ExposureTreemap.svelte:154-259`);
  - area = `current_value` (`ExposureTreemap.svelte:175-229`);
  - colore = `pnlColor(gain_loss_percent)` (`ExposureTreemap.svelte:208-227, 263-271`);
  - tooltip con `Value`, `NAV weight`, `Unrealized P&L`, `%` (`ExposureTreemap.svelte:310-327`).

#### Valutazione vs design

- **Quasi compatibile as-is:** il design chiede esattamente `area = Value`, `color = Unrealized P&L %` (`Low-dashboard_refactor.md:66-71`). Questa è già la semantica di `ExposureTreemap`.
- **Gap principale = fonte dati:** il treemap eredita lo stesso problema temporale della Holdings table, perché usa `summary.holdings` current/today (`portfolio_service.py:655-933`).
- **FE/semantic gap:** il design non prevede più il caso “Holdings + closed”. Oggi `PositionsPanel` ha una branch speciale che in `Exposure + Map + Closed` monta `ContributionTreemap` (`PositionsPanel.svelte:228-230`). Quel comportamento è fuori dal design desiderato.
- **Open question minima:** l’attuale gerarchia `Broker -> Asset Type -> Asset` è un arricchimento UX già pronto; il documento di design non la vieta, ma neanche la prescrive.

### 4.3 Performance table

#### Componente attuale

- `PositionsPanel` passa a `ContributionTable` `positions={filteredContributionPositions}`, `displayCurrency`, `brokers` (`frontend/src/lib/components/dashboard/PositionsPanel.svelte:233-234`).
- `filteredContributionPositions` è filtrato da `positionFilter`:
  - open = `!p.is_fully_sold`
  - closed = `p.is_fully_sold`
  (`PositionsPanel.svelte:121-127`).
- Contratto locale di `ContributionTable`: il type `Position` dichiara solo `asset_*`, `broker_*`, `period_pnl`, `period_pnl_percent`, `is_fully_sold` (`ContributionTable.svelte:27-37`).
- Colonne attuali: `Asset / Period P&L / Period P&L % / Broker` (`ContributionTable.svelte:131-196`).
- Status attuale: non c’è colonna dedicata; `is_fully_sold` produce solo italic + tag `(closed)` nella cella asset (`ContributionTable.svelte:118-120, 143-149`).

#### Confronto col design desiderato

| Colonna desiderata | Stato attuale | Tipo gap | Note concrete |
|---|---|---|---|
| Asset | **Già presente** | FE riusabile | `ContributionTable.svelte:133-152`. |
| Period P&L | **Già presente** | FE riusabile | `ContributionTable.svelte:154-163`; campo backend `period_pnl` già esiste (`portfolio.py:300`). |
| Unrealized Δ | **Backend sì, UI no** | FE | `AssetPeriodContribution.period_unrealized_delta` esiste (`portfolio.py:296`), ma `ContributionTable` non lo dichiara né lo usa (`ContributionTable.svelte:27-37`). |
| Realized Sales | **Backend sì, UI no** | FE + Semantic | `period_realized_gain_loss` esiste (`portfolio.py:297`), ma la tabella non lo usa. Inoltre l’attuale Exposure open usa una nozione diversa di “Realized” = realized + income (`ExposureTable.getRealizedAmount()`, `ExposureTable.svelte:93-99`). |
| Income | **Backend sì, UI no** | FE | `period_income` esiste (`portfolio.py:298`), ma `ContributionTable` non lo usa. |
| Costs | **Backend sì, UI no** | FE + Semantic | `period_fees_taxes` esiste (`portfolio.py:299`), ma la tabella non lo usa. Oggi il backend somma **fee + tax**, quindi va deciso se `Costs` nel design include anche le tasse. |
| Start Value | **Calcolato internamente, non esposto** | API/BE | `start_value` esiste come variabile locale in `get_positions_contribution()` (`portfolio_service.py:1452, 1479, 1507, 1528-1529`) ma non è nel DTO `AssetPeriodContribution`. |
| End Value | **Calcolato solo implicitamente, non esposto** | API/BE + Semantic | `mv_end` viene calcolato localmente (`portfolio_service.py:1503`) ma mai serializzato. Per le posizioni chiuse, il design vorrebbe `0` a `date_to`; oggi non c’è campo dedicato. |
| Status | **Derivabile ma non affidabile oggi** | FE + BE/Semantic | `is_fully_sold` esiste (`portfolio.py:302`) ma la UI lo usa solo come style/tag. Inoltre oggi è calcolato su `qty_at_end` all-time, non su `date_to` (`portfolio_service.py:1439-1447`). |
| Broker | **Già presente** | FE riusabile | `ContributionTable.svelte:175-195`. |

#### Gap strutturali/semantici

- **FE gap:** il design vuole una tabella unica con aperte + chiuse e colonna `Status`. Oggi il container separa il dataset con toggle `Open/Closed` (`PositionsPanel.svelte:184-201, 124-127`).
- **FE gap:** `ContributionTable` oggi è volutamente minimal e non consuma i campi backend già disponibili (`period_unrealized_delta`, `period_realized_gain_loss`, `period_income`, `period_fees_taxes`).
- **BE/Semantic gap critico:** `get_positions_contribution()` oggi ha tre derive rispetto al design:
  1. `qty_at_end += q * share` non filtra `tx.date <= date_to` (`portfolio_service.py:1439-1445`);
  2. `is_fully_sold = qty_at_end <= 0` quindi descrive stato “oggi”, non stato a fine periodo (`portfolio_service.py:1447`);
  3. lato finale usa `_get_latest_price()` invece di `price_at_or_before(date_to)` (`portfolio_service.py:1481-1505`).
- **BE/API gap:** il backend non espone `start_value` / `end_value`, quindi la frontend Performance table non può comporre il layout desiderato senza arricchire il DTO.
- **BE/Semantic gap:** il report formule precedente affermava `qty_at_end <= date_to`, `mv_end = price_at_date_to`, ed esclusione delle posizioni già chiuse prima del periodo (`dashboard-formulas-report.md:346-372`), ma il codice attuale non lo fa (`portfolio_service.py:1439-1547`). Quindi quella parte del report precedente è ormai stale.
- **BE/Semantic gap:** le righe “income-only / fees-only” create a `portfolio_service.py:1549-1568` vengono marcate `is_fully_sold=False` hard-coded; una futura colonna `Status` le classificherebbe male se l’asset non è davvero open a `date_to`.

### 4.4 Performance chart (stacked diverging bar — nuovo)

#### Stato attuale

- Oggi `PositionsPanel` usa solo `ContributionTreemap` per la vista chart di Contribution (`PositionsPanel.svelte:235-236`).
- `ContributionTreemap` si aspetta `positions`, `grossGains`, `grossLosses`, `displayCurrency` (`ContributionTreemap.svelte:38-45`).
- Shape locale consumata dal chart: solo `asset_*`, `broker_*`, `period_pnl`, `period_pnl_percent` (`ContributionTreemap.svelte:28-36`).
- Semantica attuale del chart:
  - due treemap separate gains/losses (`ContributionTreemap.svelte:1-12, 419-464`);
  - area box = `abs(period_pnl)` (`ContributionTreemap.svelte:244-255`);
  - colore = fisso verde o rosso per pannello (`ContributionTreemap.svelte:381-398`);
  - nessun breakdown per `Unrealized Δ / Realized / Income / Costs`;
  - nessun `Status`, `Start Value`, `End Value` in tooltip.

#### Esiste già un componente ECharts riusabile per stacked diverging bar?

**Risposta breve: no.**

Evidenze concrete:

- In `frontend/src/lib/components/charts/` non esiste nessun `BarChart.svelte` dedicato; i chart generici presenti sono `LineChart.svelte`, `CandlestickChart.svelte`, `AllocationPieChart.svelte`, `SemiDonutChart.svelte` (search file-name fatta in `frontend/src/lib/components/charts/`).
- `LineChart.svelte` supporta serie `seriesType === 'bar'` solo come overlay verticale stile MACD su asse temporale (`LineChart.svelte:281-309`).
- `lineChartHelpers.ts` ha `buildBarSeries()` che crea una singola serie ECharts `type: 'bar'` con colore per segno, ma:
  - non gestisce stack positivo/negativo;
  - non gestisce barre orizzontali per categoria asset;
  - non gestisce total label o doppio lato divergente.
  (`lineChartHelpers.ts:370-394`).
- `CandlestickChart.svelte` usa anch’esso barre per MACD, non per dashboard positions (`CandlestickChart.svelte` match su `type: 'bar'`).

#### Gap concettuali per arrivare al design

- **FE gap:** serve un componente nuovo o una nuova modalità chart con:
  - asse Y categoriale (`asset` / `other effect row`);
  - asse X numerico centrato su zero;
  - serie multiple per componenti `unrealized_delta`, `realized`, `income`, `costs`;
  - stack separati per segno (componenti positive a destra, negative a sinistra);
  - label finale = net `period_pnl`;
  - tooltip con `Status`, `Start Value`, `End Value`, `Broker`.
- **API/BE gap:** il dataset attuale frontend non include `start_value`, `end_value` né un dataset UX-ready per `Other Period Effects`.
- **Reuse limitata ma utile:** restano riusabili
  - `echartsTooltipHelpers.ts` per tema/tooltip HTML (`echartsTooltipHelpers.ts:22-61, 139-144`);
  - pattern lifecycle ECharts già usato dai treemap;
  - parsing numerico dei campi contribution già presente in `aiExportBuilder.ts:233-239`.

### 4.5 Other Period Effects

#### Stato attuale

- Il backend ha già una separazione concettuale tra righe asset-specific e righe non asset-specific:
  - `PositionsContribution.positions[]`
  - `PositionsContribution.unallocated[]`
  (`backend/app/schemas/portfolio.py:316-324`).
- `UnallocatedContribution` però ha solo:
  - `broker_id`
  - `broker_name`
  - `unallocated_income`
  - `unallocated_fees_taxes`
  (`portfolio.py:305-313`).
- `PortfolioSummary` espone anche `period_other_result`, cioè residuo aggregato che chiude l’identità del P&L periodo (`portfolio.py:373`, `portfolio_service.py:1057-1059, 1129`).
- Frontend attuale non rende nulla di tutto questo nel pannello posizioni:
  - `ContributionTable` commenta esplicitamente “No synthetic unallocated rows” (`ContributionTable.svelte:4-7, 54`);
  - `PositionsPanel` non ha slot/sezione aggiuntiva sotto Performance.

#### Gap vs design

- **FE gap:** manca completamente una sezione UI “Other Period Effects”.
- **API gap:** manca una shape già pronta con `Description / Category / Period P&L / Broker`.
- **BE/Semantic gap:** l’attuale `unallocated` è aggregato per broker e per bucket (`income` vs `fees_taxes`), non per voce descrittiva; non può produrre righe tipo `Cash interest`, `Broker custody fee`, `FX residual` senza nuovo shaping.
- **BE/API gap:** `period_other_result` è un singolo residuo aggregato, non itemizzato né broker-split. Utile per riconciliazione, non sufficiente per la UX desiderata.
- **BE/API gap:** il DTO corrente non rappresenta righe globali senza broker (`Broker = —`), perché `UnallocatedContribution` richiede sempre `broker_id` e `broker_name`.

#### Cosa è già compatibile / quasi compatibile

- **Compatibile concettualmente:** la decisione attuale di non mescolare righe “non allocate” nella tabella asset (`ContributionTable.svelte:4-7`) è in linea con il design che vuole una sezione separata.
- **Quasi compatibile lato dati:** `unallocated_income` e `unallocated_fees_taxes` possono diventare almeno due righe generiche per broker (`Income` / `Cost`) anche senza nuovo calcolo; ma non coprono `FX residual` né una `Description` utile.

### 4.6 Recent Transactions (verifica stato attuale, no redesign)

#### Stato attuale verificato

- Props: `limit`, `brokerIds`, `transactionsHref`, `onViewRow` (`frontend/src/lib/components/dashboard/RecentTransactionsPanel.svelte:34-45`).
- Sorgente dati: `zodiosApi.query_transactions_api_v1_transactions_get()` con solo `limit` e filtro broker, nessun filtro date range (`RecentTransactionsPanel.svelte:76-80`).
- Post-processing locale:
  1. fetch per broker o in blocco;
  2. merge/dedup per `tx.id`;
  3. sort `date DESC`, poi `id DESC`;
  4. elimina partner rows (`related_transaction_id`);
  5. `slice(0, limit)`.
  (`RecentTransactionsPanel.svelte:82-93`).
- Colonne visibili: `Date`, `Type`, `Quantity`, `Cash`, `Asset`, `Broker`.
  - `RecentTransactionsPanel` nasconde `links`, `tags`, `id`, `description` (`RecentTransactionsPanel.svelte:107, 139`);
  - `TransactionsTable` definisce `date`, `typeIcon`, `quantity`, `cash`, `asset`, `broker`, `tags`, `id`, `description` (`TransactionsTable.svelte:619-780, 800, 822, 836`).
- Interattività:
  - `compact={true}` (`RecentTransactionsPanel.svelte:139`);
  - in compact mode `TransactionsTable` disabilita pagination, sorting, filters, column visibility, context menu (`TransactionsTable.svelte:984-992`);
  - double-click apre callback view (`RecentTransactionsPanel.svelte:109-111, 139`).

#### Valutazione vs design

- **Allineato** sul punto principale: il pannello dati è indipendente dal date range dashboard.
- **Nessun redesign necessario** sulla base del documento.
- **Piccola nota semantica:** il pannello dati è indipendente dal date range, ma il link `See all` punta a `/transactions?start=...&end=...` costruito in `+page.svelte` (`+page.svelte:174-175, 485-489`). Non impatta il pannello in sé, ma va tenuto presente come comportamento attuale.

## 5. Reuse opportunities

1. **`/portfolio/report` può restare endpoint unico.**  
   Il flusso pagina → store → endpoint è già giusto:
   - `portfolioStore.fetchReport()` supporta già `include_positions_contribution` (`frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts:124-157`);
   - `+page.svelte` ha già lazy-loading contribution (`+page.svelte:219-228`).
   Non serve necessariamente un endpoint separato; è più naturale arricchire `positions_contribution` o aggiungere una sezione sibling nel `PortfolioReportResponse`.

2. **`ExposureTreemap.svelte` è quasi già il chart Holdings.**  
   Area/colore/tooltip sono già coerenti col design (`ExposureTreemap.svelte:154-229, 310-327, 333-375`). Serve soprattutto correggere la sorgente dati e togliere il caso closed.

3. **`ExposureTable.svelte` può essere base della tabella Holdings.**  
   Asset cell, broker cell, DataTable wiring, formatters valuta e percentuali sono già pronti (`ExposureTable.svelte:112-139, 203-247, 378-396`).

4. **Il backend ha già molti campi utili per Holdings senza nuovo endpoint.**  
   `PortfolioHolding` contiene già `quantity`, `wac_per_unit`, `current_price`, `current_value`, `gain_loss`, `gain_loss_percent`, `nav_weight_percent` (`portfolio.py:274-282`).

5. **Il backend ha già molti campi utili per Performance senza nuovo calcolo di base.**  
   `AssetPeriodContribution` contiene già `period_unrealized_delta`, `period_realized_gain_loss`, `period_income`, `period_fees_taxes`, `period_pnl`, `is_fully_sold` (`portfolio.py:296-303`).

6. **`ContributionTable.svelte` è buona base per Performance table.**  
   Ha già mapping per asset + broker, sort per impatto (`abs(period_pnl)`), badge broker, navigazione a dettaglio asset (`ContributionTable.svelte:68-87, 118-129, 131-196`).

7. **`ContributionTable` già spinge nella direzione “Other Period Effects separati”.**  
   Il commento iniziale dice esplicitamente che le righe unallocated non devono stare nella tabella asset (`ContributionTable.svelte:4-7`).

8. **Il motore portfolio ha già snapshot per-position a `date_to`.**  
   `PortfolioCalculationResult.position_states_end` e `DailyPositionState` già esistono (`portfolio_engine.py:347-365, 950-959, 1320-1339`). Questo è il miglior candidato per costruire Holdings storica corretta senza continuare a dipendere dal holdings loop current.

9. **Il motore ha già anche accumulatori periodo riusabili.**  
   `PortfolioCalculationResult` contiene già `per_realized`, `per_income`, `per_fees_taxes`, `unalloc_income`, `unalloc_fees` (`portfolio_engine.py:1327-1332`), ma `get_report()` oggi chiama comunque `get_positions_contribution()` separatamente (`portfolio_service.py:1763-1772`). C’è quindi una chiara opportunità di ridurre logica duplicata.

10. **Frontend già consuma questi campi in un altro punto.**  
   `aiExportBuilder.ts` legge già `quantity`, `wac_per_unit`, `gain_loss_percent`, `period_unrealized_delta`, `period_realized_gain_loss`, `period_income`, `period_fees_taxes` (`frontend/src/lib/features/ai-export/aiExportBuilder.ts:210-238`). Quindi non c’è solo backend readiness: parte del parsing frontend esiste già.

## 6. Missing backend/data requirements

### 6.1 Per Holdings

- **Correggere semantica snapshot a `date_to`.**
  - O si rende `get_summary().holdings` date-aware;
  - oppure si smette di usare il loop current e si serializza Holdings da `engine_result.position_states_end`.
- **Esporre quantità/prezzo/PMC con semantica storica corretta.**
  - I campi esistono già nel DTO, ma oggi i valori sono current-biased.
- **Facoltativo ma utile:** esporre anche `valuation_source` del motore (`MARKET_PRICE`, `LAST_BUY_PRICE`, `MISSING`) se si vuole gestire bene prezzi mancanti/stale (`portfolio_engine.py:360-365, 1008-1044`).

### 6.2 Per Performance

- **Calcolare `qty_at_end` e `Status` a `date_to`, non all-time.**
- **Usare `price_at_or_before(date_to)` per il lato finale**, non `_get_latest_price()`.
- **Esporre `start_value` e `end_value` nel DTO** (`AssetPeriodContribution` o DTO nuovo).
- **Filtrare o classificare esplicitamente le posizioni “no period relevance”** già chiuse prima del periodo.
- **Decidere il meaning di `Costs`:**
  - tenere l’attuale `fees + taxes`;
  - oppure separare `fees` e `taxes`.

### 6.3 Per Other Period Effects

- **Nuovo shape dati UX-ready**, per esempio una collezione tipo:
  - `description`
  - `category`
  - `period_pnl`
  - `broker_id?`
  - `broker_name?`
- **Rappresentazione di residui globali** (`FX residual`, `unallocated result`, ecc.) con broker nullable.
- **Decisione di riconciliazione:** come mappare `summary.period_other_result` nella nuova sezione.

### 6.4 Per il chart Performance

- Nessun blocco backend “matematico” per i componenti principali: `unrealized_delta`, `realized`, `income`, `fees_taxes` esistono già.
- Manca però dataset completo per tooltip/metadata (`status`, `start_value`, `end_value`) e per righe non-asset-specific.

## 7. Suggested implementation phases

1. **Phase 1 — allineare semantica backend**  
   Rendere storici a `date_to` Holdings e Contribution/Performance; correggere `qty_at_end`, end price, filtro posizioni rilevanti; decidere shape di `Other Period Effects`.

2. **Phase 2 — stabilizzare DTO/report**  
   Estendere `PortfolioHolding`/`AssetPeriodContribution` o `PortfolioReportResponse` con i campi mancanti (`start_value`, `end_value`, other effects rows), mantenendo `/portfolio/report` come entrypoint unico.

3. **Phase 3 — migrare tabella Holdings**  
   Riutilizzare `ExposureTable` come base, rimuovere colonne period-scoped, aggiungere `P&L % / Quantity / Price / PMC`, togliere logica closed da questa tab.

4. **Phase 4 — migrare tabella Performance + Other Period Effects**  
   Riutilizzare `ContributionTable` come base, aggiungere colonne componenti, unificare open/closed in una sola vista con `Status`, aggiungere sezione separata other effects.

5. **Phase 5 — sostituire chart Contribution**  
   Tenere `ExposureTreemap` per Holdings; introdurre nuovo chart stacked diverging per Performance usando helper tooltip/theme esistenti.

6. **Phase 6 — rifinitura UX e riconciliazione**  
   Rinominare toggle/i18n (`Exposure`→`Holdings`, `Contribution`→`Performance`), rimuovere/ridefinire open-closed toggle, verificare che somme Performance + Other Period Effects riconcilino con `summary.period_pnl`.

## 8. Risks / edge cases / open questions

1. **Il vecchio formulas report è parzialmente stale.**  
   In particolare la sezione `get_positions_contribution` del report precedente (`dashboard-formulas-report.md:342-374`) non corrisponde più al codice attuale su:
   - `qty_at_end`
   - `mv_end`
   - esclusione posizioni irrilevanti.

2. **Dubbio storico sul P&L periodo di posizioni chiuse: matematicamente la formula base oggi è corretta per il caso semplice.**  
   Per una posizione completamente venduta nel periodo, senza buy intermedi e senza income/fees, il codice attuale fa:
   - `unrealized_delta = 0 - ug_start`
   - `realized = sell_proceeds - cost_basis_sold`
   - quindi `period_pnl = sell_proceeds - start_value`
   (`portfolio_service.py:1454-1525`).  
   Quindi il dubbio “dovrebbe essere NAV inizio periodo − NAV finale di vendita” risulta **sostanzialmente risolto** per quel caso.  
   **Resta però aperto** il problema più ampio: status e lato finale oggi non sono davvero ancorati a `date_to` quando il range è storico.

3. **Duplicati asset su broker diversi.**  
   Tutta la catena attuale è keyed per `(asset_id, broker_id)` (`ExposureTable.svelte:89-91`, `portfolio_service.py:1319-1323, 1383-1389`). Questo è coerente con la colonna `Broker`, ma nel chart Performance potrebbe generare più righe con lo stesso nome asset.

4. **Costs oggi include anche taxes.**  
   `period_fees_taxes` aggrega `FEE` + `TAX` (`portfolio.py:299`, `portfolio_service.py:1364-1368`). Il design parla di “Costs”/commissioni/fee: serve decisione esplicita.

5. **Price e PMC oggi sono già convertiti in target/display currency, non necessariamente currency nativa asset.**  
   Questo può essere desiderabile oppure no; il design non lo specifica esplicitamente.

6. **Righe income-only / fee-only.**  
   `get_positions_contribution()` aggiunge righe con `period_income` anche se non esiste una posizione BUY/SELL tracciata in `position_info` (`portfolio_service.py:1549-1568`). Serve definire come valorizzare `Status`, `Start Value`, `End Value` in questi casi.

7. **`period_other_result` non ha semantica UX definita.**  
   Oggi è un residuo di riconciliazione (`portfolio_service.py:1057-1059, 1129`). Va deciso se diventa:
   - una riga esplicita “Unallocated result”;
   - una scomposizione più dettagliata;
   - o solo un warning di riconciliazione.

8. **Recent Transactions: link vs dati.**  
   Il pannello dati è indipendente dal date range, ma il link “See all” porta a `/transactions` con `start/end` correnti. Comportamento attuale da tenere a mente, anche se il design non lo tocca.

9. **I18n rename non ancora pronto.**
   - `dashboard.exposure` / `dashboard.contribution` esistono e sono usati da `PositionsPanel` (`frontend/src/lib/i18n/en.json:857-860`, `frontend/src/lib/i18n/it.json:857-860`);
   - `dashboard.performance` non compare oggi nelle traduzioni;
   - `dashboard.holdings` esiste già ma come label heading “Your Holdings” / “Le tue Posizioni”, non come tab label breve (`frontend/src/lib/i18n/en.json:853`, `frontend/src/lib/i18n/it.json:853`).
