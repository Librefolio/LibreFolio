# Audit della matematica finanziaria — 16/10/2026

Audit in sola lettura su `dev_release2`, HEAD `3d5ee174d`. Non ho lanciato test, server o build.

**Attenzione:** alle 11:17, mentre l'audit era in corso, il treno 107 ha unito **J CP-7a** (`4f9e94420`).
Ho riletto sulla nuova HEAD i file che ha toccato: `lots/*`, `fifo/engine.py`, `returns.py`,
`portfolio_service.py` e `brokers/summary.py`. Tutti i numeri di riga sotto si riferiscono a `3d5ee174d`.

Regole usate come metro: decisione 10 di `copilot-instructions.md`, `financial-math.instructions.md`,
`backend.instructions.md` («Financial Math — One Home»), la pagina sviluppatori `financial_math.md`, e le pagine
del devWiki `decisions/financial-math-one-home.md` e `decisions/financial-math-single-average-cost.md`. In più la
regola del cambio dettata oggi: ogni importo va convertito al cambio del giorno della sua transazione, e ogni
calcolo si fa nella valuta del report.

---

## 1. In breve

- **La fattorizzazione pre-1.2 ha retto sul valore del portafoglio nel tempo.** Tutti i percorsi che valutano
  l'intero portafoglio o un broker giorno per giorno passano da `PortfolioCalculationEngine`: Dashboard, KPI della
  pagina broker, AI Export portafoglio e broker, Risk, pesi del PAC. Non ho trovato una sesta copia del NAV.
- **Le perdite sono al livello della singola posizione.** Ho contato circa **15 duplicati veri**, cioè copie che
  possono dare un numero diverso, e circa 15 copie parziali innocue o quasi.
- **Il più grave è `get_positions_contribution`** (`portfolio_service.py:1467`). Valuta da sé ogni posizione agli
  estremi del periodo: prezzo proprio, quantità propria, cambio preso alla data del prezzo e non a quella del
  periodo, cambio mancante scartato in silenzio. Alimenta la tabella Performance della Dashboard e i pesi
  tecnici dell'AI Export, e la differenza con il motore finisce nella riga «Other».
- **Cambi: nessun tasso «a caso».** La primitiva è una sola, `convert_bulk`. I movimenti si convertono alla loro
  data e le valutazioni al giorno di valutazione. Le eccezioni sono 3 reali e 1 latente, elencate al §4. CP-7a ha
  appena chiuso quella dei lotti.
- **Frontend: 4 calcoli derivati non dichiarati**, oltre ai già noti P19 e W7.
- **Algoritmo più contorto: `DailyStateBuilder.build`**, circa 610 righe. Ha le regole dei 3 pool scritte due
  volte e in disaccordo tra loro, e il ramo pre-frame è morto in produzione.

---

## 2. Calcoli fuori dalla casa

Le gravità usate nella tabella:

- **D**: duplicato che può divergere.
- **P**: copia parziale; oggi coincide, ma è una seconda implementazione.
- **V**: aritmetica di sola visualizzazione, innocua.

### Backend

| file:line | cosa calcola | equivalente nella casa | gravità |
|---|---|---|---|
| `portfolio_service.py:1586-1643` | P&L non realizzato di inizio e fine periodo per posizione. Quantità sommata dalle transazioni × quota (1598), prezzo da `_get_price_at_date` (489: ultima chiusura ≤ data, ignora prezzi da trade e split), cambio d'inizio a `date_from` (1623) e di fine a `price_date_e`, la data del prezzo (1641). Il cambio mancante va perso: `price_s_base, _ =` e `price_e_base, _ =` | stati del motore (`price_marks` + `fx_rate_map` del giorno), `period.period_boundaries` | **D**, il più grave |
| `portfolio_service.py:1812` | residuo «Other» scritto a mano | `period.period_other_result` (`period.py:111`), che `get_summary` già usa | **D** (oggi è la stessa formula) |
| `portfolio_service.py:1672, 1683, 1706` | % del P&L di periodo su \|start_value\|, base per annualizzare, rendimento delle posizioni chiuse | `returns.gain_loss_ratio` | **P** |
| `portfolio_service.py:720-747` | variazione di 1 giorno (prezzo, P&L, %) con un prezzo letto a parte (724) e un rapporto scritto a mano (733, 747) | `returns.price_return`, `gain_loss_ratio`; marca del giorno prima da `price_marks` | **D**: ignora la marca del motore, cioè trade-avg, carried e split |
| `portfolio_service.py:824-831` | NAV e utile per broker ricomposti: valore di mercato delle posizioni finali + `native_cash.value_at` + in transito. Il commento a 824 («the engine re-values a day only when something happens») è superato da CP-6 | `BrokerDailyContribution.nav_contribution` / `pnl_contribution` dell'ultimo stato (`daily_state.py:648-660`) | **D** |
| `portfolio_service.py:856, 858` | `allocation_percent` e `nav_weight_percent` per holding | nessuna funzione «pesi» nella casa; `derived_views._alloc` ha la stessa formula per dimensione | **P**. Casi limite già noti (NAV ≤ 0, posizione a valore zero) |
| `portfolio_service.py:360-396` `_oldest_open_lot_date`, `:399-424` `_closed_position_window` | mini-FIFO sulle sole quantità, per broker, per la data del lotto aperto più vecchio e per la finestra delle posizioni chiuse. Un trasferimento apre un lotto nuovo, dove il motore FIFO conserva la data d'origine; uno split inverso consuma i lotti più vecchi | `fifo/engine` (date dei lotti) | **D** (scelta documentata nel docstring, ma è una seconda FIFO) |
| `portfolio_service.py:871-893` | regole d'orchestrazione dell'MWRR del sommario: guardia `period_net_invested > 0`, NAV iniziale di ripiego copiato «per coerenza» da `calculate_mwrr_series` | `returns.calculate_mwrr` / `calculate_mwrr_series` | **D**: sommario e ultimo punto dello storico possono scegliere radici diverse (§5.2) |
| `portfolio_service.py:161`, `brokers/summary.py:225`, `lots_analysis_service.py:580`, `financial_math/yield_on_cost.py:823`, `financial_math/portfolio/engine.py:220` | quali righe sono ADJUSTMENT legati a uno SPLIT: 5 caricamenti uguali | nessuno; decide se il costo medio fa «split» o «add/reduce» | **P** |
| `brokers/summary.py:99-150, 242-253` | `BRSummary.holdings`: prezzo «ultimo in assoluto», senza filtro `as_of` e senza leggere la valuta del prezzo (250 seleziona solo `asset_id, close`); valore e P&L in valuta dell'asset. L'interfaccia non li usa (la pagina broker legge solo `cash_balances`), ma l'API li espone | motore + `price_marks` | **D** |
| `lots_analysis_service.py:757-796` (`_build_lot_summaries`) | P&L del lotto: open value, total value LONG/SHORT, market P&L, total e net return, «estimated at cost» (777) | `lots/histories._value_snapshot_on_date` (335) e `_lot_returns` (539) | **D**. La copia ha appena prodotto un bug: la storia SHORT dava −100% a pareggio, il sommario 0%. CP-7a l'ha corretto (`histories.py:317-319`), ma le formule restano due |
| `lots_analysis_service.py:773`, `lots/histories.py:315` | `relative_return` = prezzo/riferimento − 1 | `returns.price_return` | **P** |
| `financial_math/fifo/engine.py:877-878` (nella casa) | i pool di reddito sommano `abs(native_amount)`: una correzione negativa di DIVIDEND/INTEREST diventa reddito positivo del lotto | la Dashboard tiene il segno (`daily_state.py`, `native_cash.flows().signed_by_type`) | **D** interno alla casa: due regole del segno |
| `financial_math/fifo/engine.py:1125` (nella casa) | peso di ripartizione delle commissioni: importo nativo se manca quello convertito, quindi valute miste negli stessi pesi | regola 3 «mai l'importo non convertito» | **P** (pesa solo le quote) |
| `transactions/balances.py:136-150` `_get_balances_before_date`, `:168-173` `get_asset_holdings` | saldi di cassa e quantità con `func.sum` SQL, che su SQLite passa da float | `ledger_totals.position_quantities`, `native_cash.native_balances` | **D**, famiglia di W-B19. `get_asset_holdings` alimenta `BRSummary`, `get_balances_at_end_of` il gap-fix BRIM (`brim/brim_gap_fix.py:74`) |
| `pac_allocator/source/loaders.py:15-39, 42-76, 79-110` | istantanea propria del PAC: quantità e cassa con `func.sum` SQL, «ultimo prezzo ≤ as_of» | `ledger_totals`, `native_balances`, `price_marks` (i pesi in `distribution.py:63` usano già il motore) | **D** |
| `pac_allocator/source/wac.py:29-79, 168-200` | rilegge le righe `FxRate` per «provare» il cambio usato dal costo medio, con un proprio backward-fill e una tolleranza (`_rates_match`) | `CostStep.conversion` ha già `rate`, `rate_date`, `days_back` | **P** (seconda lettura del cambio) |
| `risk/service.py:544-549` | pesi delle posizioni (valore / NAV o / fetta) | nessuno nella casa (vedi «pesi») | **P** |
| `risk/service.py:1154`, `risk_plugins/comparison/plugin.py:237` | fattore di annualizzazione osservato `n·365/giorni` | `series_preparation.observed_annualization` (67-82) | **P** (3 copie) |
| `risk_plugins/comparison/plugin.py:58-66` `_compounded` | composizione dei rendimenti | `risk/metrics.compounded_return` (128) | **P** |
| `ai_export/components/portfolio_income.py:349-380` (wired, `datasets/catalog.py:193`) | timeline dei redditi: rilegge le transazioni, moltiplica per `share_percentage` grezzo (EDITOR/VIEWER → 0, dove il report usa 1) e per `abs(amount)`, mentre il report tiene il segno (§4.4). Il docstring afferma che coincide con il report: non è vero | `native_cash.flows()` / `sums_by_date` con `effective_share` | **D** |
| `ai_export/components/broker_cost_efficiency.py:152-168` | turnover × `share_percentage` grezzo | `native_cash.effective_share` | **D** (stesso difetto) |
| `ai_export/components/technical_shared.py:467-485` `compute_nav_weights` | pesi lordi da `end_value` di `positions_contribution`, cioè dalla valutazione divergente sopra | pesi del motore | **D** (eredita il primo difetto) |
| `ai_export/components/broker_financial.py:205-212` e `broker_concentration_context.py:88-104` | massimo peso e HHI, due copie («Mirrors exactly»), calcolati da `nav_weight_percent` già arrotondato allo 0,01% | nessuno | **D** (due copie dello stesso numero) |
| `ai_export/components/payloads/portfolio_broker.py:372, 391-399` | concatenazione TWRR tra bucket (1+b)/(1+a)−1 | `returns.calculate_twrr_period_series`, `risk/metrics.period_returns_from_cumulative` (461) | **P** |
| `ai_export/components/payloads/portfolio_broker.py:173` | costo residuo = costo × aperta/originale (terza copia, dopo `lots_analysis_service.py:777` e `histories.py:472`) | nessuno | **P** |
| `ai_export/components/fx_core.py:353-372, 448-466` | importo nativo «Mirrors exactly» la valutazione del motore; cassa × cambio a `as_of` | marca del motore; `native_cash.value_at` | **P** |
| `ai_export/components/technical_shared.py:819`, `drawdown_context.py:498`, `fx_timing_context.py:323, 329, 333` | rendimento semplice ultimo/precedente − 1 | `returns.price_return` | **P** |
| `ai_export/components/broker_cost_efficiency.py:550-568` | NAV medio e rapporti costi/NAV | nessuno (fatto nuovo dell'AI Export) | **P** |
| `financial_math/yield_on_cost.py:452-460` | il costo medio passato viene convertito a `as_of_date` (vedi §4) | — | latente |

### Frontend

| file:line | cosa calcola | gravità |
|---|---|---|
| `features/dashboard/KpiSection.svelte:80-85, 99-102, 131-134` | variazione del P&L totale di 1 giorno dalla storia, in % del NAV di ieri e del P&L di ieri (float) | **D**: cifra finanziaria derivata nel frontend, regola 6 |
| `features/dashboard/KpiSection.svelte:243` | «timing effect» = MWRR cumulato − TWRR cumulato | **P** (sottrazione, ma è una cifra nuova) |
| `features/brokers/lots/lotComparisonChartHelpers.ts:150-171` | rendimento aggregato dei lotti selezionati, (P&L + reddito) / costo | **D** (selezione interattiva: o si dichiara come eccezione o va al backend) |
| `utils/assetPriceDerived.ts:161, 184`, `routes/(app)/assets/[id]/+page.svelte:561`, `stores/fxStoreRegistry.ts:64` | variazioni % di prezzo e di cambio (1D, periodi) | **P** (copie di `price_return`) |
| `features/brokers/lots/LotWacPriceChart.svelte:903, 1413`; `AllocationHistoryChart.svelte:333`; `PerformanceChart.svelte:410`; grafici `timeSeriesAggregation.ts` | medie e somme per posizionare o impilare | **V** |
| `charts/signals/MeasureSignal.ts`, `CompoundSignal.ts`, `LinearSignal.ts` | eccezioni dichiarate | **V** |

---

## 3. Percorsi di valutazione del portafoglio

| Percorso | Passa dal motore? |
|---|---|
| Dashboard: KPI, storia, allocazione, P&L per broker, candele, finanziamento (`get_report` → un solo `engine.calculate`, `portfolio_service.py:1950`) | **Sì** |
| Dashboard, righe holding: valore e P&L | **Sì**, da `position_states_end`. La variazione di 1 giorno no (`:720-747`) |
| Dashboard, ripartizione per broker | **Parziale**: ricomposta nel servizio (`:824-831`) invece di leggere `BrokerDailyContribution` |
| Dashboard, tabella Performance (`get_positions_contribution`) | **No** per l'unrealized di periodo (`:1586-1643`). Il realizzato e i flussi vengono dal motore |
| Pagina broker: KPI e posizioni (report filtrato sul broker) | **Sì** |
| Pagina broker: cassa (`GET /brokers/{id}/summary`) | **Sì** (`native_balances`) |
| `BRSummary.holdings` (solo API) | **No** (`brokers/summary.py:99-150`) |
| Analisi lotti | **Sì**: FIFO della casa + `price_marks` come cervello unico dei prezzi. Il sommario del lotto però è una copia (`lots_analysis_service.py:757-796`) |
| Storia «performance» dei lotti (`lots/histories.py:50-162`) | Nella casa, ma è un **secondo mini-motore** a livello asset: NAV dei frammenti più flussi BUY/ADJ/SELL/trasferimenti, con regole diverse dal motore di portafoglio (niente reddito, ADJ come flusso). Il segno dei lotti SHORT nel NAV (riga 72) è **non verificato** |
| AI Export portafoglio e broker (`portfolio_financial.py:300`, `broker_financial.py:270`) | **Sì**, via `get_report` |
| AI Export: timeline dei redditi, efficienza dei costi, pesi tecnici, HHI | **No** (§2) |
| Strumento PAC: pesi correnti (`distribution.py:63`) | **Sì** |
| Strumento PAC: istantanea delle posizioni, cassa, prezzi, prova del cambio del WAC | **No** (`loaders.py`, `wac.py`) |
| Risk: pesi e TWRR del portafoglio | **Sì**, via `get_report` (`risk/service.py:497`) |
| Risk: serie degli asset | Percorso serie (`price_query` + `series_preparation`); ogni punto è convertito alla sua data. Va bene, non è una valutazione di portafoglio |
| Yield on Cost | Nella casa; rifà un replay FIFO per componente di broker (§5.5) |
| Backup: totali di controllo | **Sì** (`ledger_totals`) |
| Transazioni: anteprima del WAC, costo automatico | **Sì** (facciata `compute_wac_iterative` → `average_cost`) |
| Transazioni: validazione dei saldi, gap-fix BRIM | **No** (W-B19 e `balances.py:136-150`) |

---

## 4. Cambi

Lo strumento è uno solo, `fx/conversion.convert_bulk`. La casa però ha 5 adattatori di conversione:

- `average_cost` (conversioni per data);
- `native_cash` (cambi unitari);
- `portfolio/engine._preload_fx_rates` → `fx_rate_map`;
- `lots/conversions.FxRateResolver`;
- `yield_on_cost._resolve_conversion_context`.

Fuori dalla casa, `convert_bulk` è chiamato direttamente in circa 10 punti:

- `portfolio_service`, solo per le righe di §2;
- `price_query`, `event_store`, `risk/eligibility`;
- 4 componenti dell'AI Export;
- l'API dei cambi.

I movimenti si convertono alla loro data e le valutazioni al giorno valutato: il motore converte la marca alla
data di valutazione (`daily_state.py`, `_market_value_for`).

**Eccezioni:**

1. `portfolio_service.py:1641`: il prezzo di fine periodo è convertito alla **data del prezzo** (`price_date_e`), non
   alla fine del periodo; l'inizio invece usa `date_from` (1623). In più il cambio mancante viene scartato (`_`), e
   questo viola la regola 3 «no silent fallback».
2. `portfolio_service.py:729`: il prezzo di ieri è convertito alla data di quel prezzo, che con il backward-fill può
   essere più vecchia di ieri. Minore.
3. `brokers/summary.py:250`: il prezzo è letto senza la sua valuta e moltiplicato come se fosse nella valuta
   dell'asset. Se le due valute differiscono, mescola valute (è il caso del problema wiki `asset-currency-mismatch`).
4. **Latente**, `financial_math/yield_on_cost.py:452-460`: il costo medio (storico) è convertito a `as_of_date`. Oggi
   non ha effetto, perché il solo chiamante passa `wac_currency` = valuta del report. Basta un altro chiamante per
   convertire un costo storico al cambio di oggi.
5. **Scelte documentate da confermare con la regola:**
   - `daily_state.py` `_compute_in_transit`: il costo dei titoli in transito è convertito alla data d'**arrivo**.
   - `pac_allocator/source/fx_quotes.py:23-50`: il PAC usa l'ultimo cambio ≤ `as_of`. Qui è una valutazione «a
     oggi», quindi coerente.
6. **Già noti:**
   - J-24 (ADJUSTMENT in uscita al costo storico sulla Dashboard).
   - CP-7a (lotti convertiti gamba per gamba): unito alle 11:17 di oggi; la vecchia conversione della chiusura alla
     data di chiusura non c'è più (`lots_analysis_service.py:1055` → `convert_closure`).

---

## 5. Algoritmi della casa

### Moduli, in breve

| Modulo | Cosa fa | Complessità |
|---|---|---|
| `average_cost.py` | Costo medio per posizione: costo storico nella valuta del report e in quella dell'asset, ogni acquisto convertito alla sua data, in un solo batch; segnala le conversioni mancanti | lineare (`_fold_position` ha un ramo per tipo di movimento: essenziale) |
| `native_cash.py` | Cassa per broker e valuta: saldi, valore a ogni giorno, flussi per tipo e posizione, risultato di cambio, giorni di cambio del tasso | chiaro |
| `ledger_totals.py` | Totali di controllo esatti per il backup | banale |
| `valuation.py` | quantità / `quote_base` × prezzo | banale |
| `price_marks.py` | Marca giornaliera: quotazione, media dei trade del giorno, ultimo valore riportato, mancante | chiaro (J-17 già noto) |
| `returns.py` | ROI, TWRR, MWRR (puntuali e in serie), annualizzazione, rebase del periodo, rapporti | il solutore MWRR è contorto (§5.2) |
| `yield_on_cost.py` | Reddito degli ultimi 365 giorni sul costo, con replay FIFO per l'idoneità D-1 e controlli di coerenza degli split | medio (§5.5) |
| `fifo/` | Classificazione degli eventi, replay di lotti e frammenti, ripartizione di reddito e costi | grande ma ben diviso (§5.4) |
| `portfolio/classifier.py` | Interno, esterno, in transito | ok |
| `portfolio/daily_state.py` | Replay giornaliero: NAV, 3 pool, in transito, contributi per broker | **il peggiore** (§5.1) |
| `portfolio/derived_views.py` | Viste dagli stati | semplice; la formula `amt/total*100` è scritta due volte (`_alloc`, `build_allocation_history`) |
| `portfolio/data_quality.py` | Assemblaggio del report | lungo ma piatto |
| `portfolio/period.py` | Estremi del periodo, P&L, identità | semplice |
| `portfolio/engine.py` | Caricamento, precaricamento dei cambi, cache blob | medio; ramo «forward extension» vuoto (298-303) |
| `lots/` | Prezzi, conversioni, eventi economici, storie, linee del costo medio | `histories.build_performance_history` è un mini-motore (§5.3) |

### 5.1 `DailyStateBuilder.build`: `portfolio/daily_state.py:157-765`

- **Cosa fa.** Riproduce ogni giorno: cassa, quantità, passi del costo medio, i 3 pool capitale/rendimenti/
  prelevato (K/R/W), giorni «sporchi», valutazione, in transito, contributi per broker, candele. Emette uno stato
  per giorno.
- **Perché è complesso.** Circa 610 righe in un solo metodo, e:
  - **le regole dei pool K/R/W sono scritte due volte**, pre-frame (270-313) e frame (529-575), e **non coincidono**.
    Nel pre-frame una SELL mette tutto il ricavato in K (298); nel frame il costo va in K e il guadagno in R;
  - **il pre-frame è morto in produzione**: nessun chiamante passa `frame_start` (solo i test) e tutti i servizi
    chiamano con `date_from=None`;
  - i giorni sporchi sono costruiti in linea (346-385);
  - un giorno pulito ricopia a mano 33 campi (391-429);
  - le approssimazioni sul K/R («use K as default», 311 e 574) sono poi coperte da un **riscalamento** dei pool
    quando la loro somma si scosta dalla cassa di più di 0,01 (665-683).
- **Essenziale o accidentale.** Sono essenziali la scomposizione K/R/W, il transito, i giorni sporchi (decisione
  28) e i contributi additivi. Sono accidentali il doppio ramo, il codice morto, la copia campo per campo e il
  riscalamento che nasconde la deriva.
- **Alternativa più lineare.**
  1. Togliere il pre-frame, oppure renderlo lo stesso `_apply_day` con l'emissione spenta.
  2. Una sola funzione `apply_pool_rule(tx_type, amount, sell_cost, pools)` chiamata una volta.
  3. `collect_dirty_days(...)` come funzione pura.
  4. `dataclasses.replace(prev, date=…, external_cash_flow=0, acquisition_funding=None)` per i giorni puliti.
  5. Passare all'arrivo la ripartizione K/R della partenza, così il riscalamento non serve più.

### 5.2 MWRR: `returns.py:410-…` (`_solve_xirr`), `:461` (`calculate_mwrr`), `:508` (`calculate_mwrr_series`)

- **Cosa fa.** Trova l'XIRR: prima Newton; se fallisce, una griglia di 801 punti con Brent su ogni cambio di segno,
  e tiene la radice verificata più vicina a `x0`. La serie lo ripete per ogni giorno con un warm start.
- **Perché è complesso.**
  - Due costruttori dei flussi quasi identici, nel puntuale e nella serie.
  - La serie aggiunge una seconda politica di scelta della radice, con un limite adattivo, un nuovo tentativo da
    0,1 e la preferenza per |r| più piccolo (≈572-590). Il puntuale usa solo «la più vicina a 0,1».
  - Il servizio aggiunge una terza regola, il NAV iniziale di ripiego (`portfolio_service.py:885`).
  - Risultato: con più radici, l'MWRR della card e l'ultimo punto del grafico possono differire.
- **Essenziale o accidentale.** La ricerca di radici, che possono essere più d'una o nessuna, è essenziale. Le tre
  politiche sono accidentali.
- **Alternativa più lineare.** Un `_mwrr_flows(start, start_nav, flows, end, end_nav)` e **una** politica di scelta
  dentro `_solve_xirr`. Il sommario legge l'ultimo punto della serie, oppure la serie chiama `calculate_mwrr`.

### 5.3 `lots/histories.build_performance_history`: `lots/histories.py:50-162`

- **Cosa fa.** Ricostruisce, per un asset e un ambito di broker, un NAV (somma dei frammenti × prezzo) e i flussi
  (BUY, ADJUSTMENT col costo, ricavi di vendita LONG, trasferimenti esterni valutati a mercato). Poi applica ROI e
  TWRR.
- **Perché è complesso.** È un secondo motore di «portafoglio», piccolo, con regole proprie: niente reddito,
  ADJUSTMENT come flusso invece del routing del capitale del motore. Ha 4 cicli di raccolta con guardie, un
  troncamento a `invalid_external_flow_from` e un flusso riportato al primo NAV.
- **Essenziale o accidentale.** Il TWRR di un sotto-portafoglio è essenziale. Ricostruire NAV e flussi con regole
  diverse dal motore principale è accidentale.
- **Alternativa più lineare.** Dichiarare le regole dei flussi in un solo posto, condiviso con il motore. Come minimo,
  documentare le differenze con il motore e verificare il segno dei lotti SHORT nel NAV (riga 72, **non
  verificato**).

### 5.4 Ripartizione economica FIFO: `fifo/engine.py:825-1260`

- **Cosa fa.** Ripartisce reddito, FEE e TAX sui lotti secondo la scala decisa:
  - TAX: reddito del giorno → trade del giorno → giorno prima → posizioni → orfano;
  - FEE: trade del giorno → trade del giorno prima → posizioni → orfano.
- **Perché è complesso.**
  - Il ciclo pro-rata con «resto all'ultimo» è scritto 4 volte (918, 1143, 1230 e dentro `_split_trade_cost`).
  - Il reddito è preso in valore assoluto (877).
  - Il peso ricade sull'importo nativo quando manca quello convertito (1125).
- **Essenziale o accidentale.** La scala è essenziale (decisione `fifo-v4-cost-allocation-ladder`) ed è leggibile.
  Il ciclo ripetuto e il segno sono accidentali.
- **Alternativa più lineare.** Un `allocate_pro_rata(native_total, target_total, weights)` e la scala come lista di
  coppie (regola, cercatore). La scala non va riscritta.

### 5.5 `yield_on_cost.py`

- **Cosa fa.** Per ogni posizione aperta: reddito degli ultimi 365 giorni, convertito alla sua data, diviso per il
  costo medio. Per l'idoneità D-1 esegue `run_fifo_lot_engine` per componente di broker (`_build_replay_context`).
- **Perché è complesso.** Fa un secondo replay FIFO oltre a quello dell'analisi lotti, ha un caricatore di split
  proprio e un'euristica di coerenza degli split con due tolleranze (`_has_incoherent_split_quantity`).
- **Essenziale o accidentale.** Per lo più essenziale. Sono accidentali il caricatore duplicato e la conversione
  latente del WAC (§4).
- **Alternativa più lineare.** Usare il caricatore unico degli split e controllare `wac_currency == target`. Nient'altro.

---

## 6. Proposte di lotto

| # | Lotto | Owner | Dimensione |
|---|---|---|---|
| A | **Contributo per posizione sul motore.** Il motore espone lo stato di una posizione a una data qualunque (o a `date_from`); `get_positions_contribution` lo legge e smette di usare `_get_price_at_date` e `_convert_to_base`. Usa `period_other_result` e `gain_loss_ratio`. Questo sistema anche i pesi tecnici dell'AI Export (`technical_shared.py:467`) | J + owner `portfolio_service` | grande |
| B | **Ripartizione per broker dal motore**: leggere `BrokerDailyContribution` e togliere il commento superato (`portfolio_service.py:824-831`) | J | piccola |
| C | **Una funzione «pesi» nella casa**, con i casi limite già noti NAV ≤ 0 e valore 0. La usano `derived_views`, `portfolio_service.py:856/858`, `risk/service.py:548`, `technical_shared.py:485`. L'HHI va nella casa o in risk, con **una** sola copia nell'AI Export | J (+ owner AI Export, Risk) | piccola |
| D | **Rapporti e rendimenti di prezzo** tramite `price_return` e `gain_loss_ratio`: `portfolio_service.py:733/747/1672/1683/1706`, `lots_analysis_service.py:773`, `histories.py:315`, AI Export (`technical_shared.py:819`, `drawdown_context.py:498`, `fx_timing_context.py:323-333`, `portfolio_broker.py:372-399`). Risk: un solo `observed_annualization` e un solo `compounded_return` | J + owner AI Export, Risk | piccola |
| E | **Sommario del lotto nella casa**: spostare la matematica di `_build_lot_summaries` in `lots/`, riusando `_value_snapshot_on_date` e `_lot_returns`, con un'unica formula del costo residuo. È la copia che ha prodotto il −100% sugli SHORT | J | media |
| F | **Segno del reddito**: decidere una regola sola (con segno come la Dashboard) per i pool FIFO (`fifo/engine.py:877`). AI Export `portfolio_income.py` su `native_cash`, con `effective_share` e segno | J + owner AI Export | piccola |
| G | **Somme di quantità e cassa senza SQL SUM**: `balances.py:136-173` (allargare W-B19) e i loader del PAC su `ledger_totals` e `native_balances` | owner transazioni (W) + owner PAC | piccola/media |
| H | **Data del lotto più vecchio**: `_oldest_open_lot_date` e `_closed_position_window` derivati dal FIFO, oppure spostati nella casa come variante «per broker» dichiarata | J | piccola |
| I | **Caricatore unico degli split** (5 copie) | J | piccola |
| J | **Semplificare `DailyStateBuilder`** (§5.1): togliere il pre-frame morto e il ramo vuoto di `engine.py:298-303`, una sola regola dei pool, giorni sporchi estratti, `replace` per i giorni puliti, niente riscalamento | J | media |
| K | **MWRR unico** (§5.2): un costruttore di flussi, una politica di radice; il sommario coerente con la serie | J | piccola |
| L | **`BRSummary.holdings`**: toglierli (l'interfaccia non li usa) oppure valutarli col motore; leggere la valuta del prezzo e `as_of` | owner broker | piccola |
| M | **PAC**: prova del cambio del WAC presa da `CostStep.conversion` invece di rileggere `FxRate` (`wac.py:29-79`) | owner PAC | piccola |
| N | **AI Export**: `broker_cost_efficiency` con `effective_share` | owner AI Export | piccola |
| O | **Yield on Cost**: rifiutare o convertire storicamente un `wac_currency` ≠ target (`yield_on_cost.py:452-460`) | J | minima |
| P | **Frontend**: variazioni di 1 giorno e timing effect come campi del backend; rendimento aggregato dei lotti al backend oppure dichiarato come misura interattiva; variazioni di prezzo e cambio dichiarate o dal backend. P19 e W7 già in corso | owner frontend Dashboard/Lotti | piccola |

---

## Già noti, non indagati di nuovo

- **CP-7a**: unito oggi alle 11:17; ha corretto anche la divergenza SHORT tra storia e sommario.
- **J-17**: ADJUSTMENT come osservazione di prezzo in `price_marks.py`.
- **J-24**: ADJUSTMENT in uscita al costo storico.
- **W-B19**: somma della cassa nella validazione batch (`balances.py:32`).
- **P19**: `levelHelpers.ts:359`; la stessa formula c'è nel backend, `risk/metrics.py:392`.
- **Y W7**: `ExposureTable.svelte:181`.
- **`portfolio_service.py:856/858`**: i casi limite del peso sul NAV.

## Non verificato

- Il segno dei lotti SHORT nel NAV di `build_performance_history` (`histories.py:72`).
- Il dettaglio interno di `risk/quant/`, `pac_allocator/evaluation/` e `ai_export/temporal/aggregators.py`: li ho
  letti solo con grep mirati.
- Le ricerche del frontend erano per pattern, quindi un calcolo scritto in forma insolita può essermi sfuggito.
