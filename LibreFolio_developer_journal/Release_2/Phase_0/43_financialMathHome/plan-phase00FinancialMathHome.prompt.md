# Piano — fase 00, 43: una casa sola per la matematica finanziaria (T)

> **Stato**: 🚧 in esecuzione dal 2026-10-11. Avanzamento in §10.
>
> - **Ora**: B1, B2 e B3, poi il checkpoint. Dopo: PL3, BU1 (§P2).
> - **In attesa**: T-1 aspetta F (lotto 41); FE1 aspetta la review C7 dell'onboarding (Q); B3b aspetta il via del coordinatore (§7.1).
>
> - **Workstream T** · worktree `LibreFolio-worktrees/e-alfy-silver-barnacle` · ramo `e-alfy-t-matematica-finanziaria-unica` (rinominato dall'app all'avvio; prima `e-alfy-silver-barnacle`).
> - **Base**: HEAD `b20eac991446833b247291cf0e9cfb85b98feeb4` = target `dev_release2` (treno 32), verificata all'avvio; worktree pulita.
> - **Corsia**: `--test-port 6164 --data-dir /tmp/librefolio-r2-t`, con `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test …`; un comando alla volta. Mai le porte 6040 e 6041.
> - **Coordinatore**: `c8328a01-f208-4ade-a352-0486d1f14de2`.
> - **Due parti**: Parte 1 (§0–§9), la casa unica, ha la priorità. Parte 2 (§P2), il «Code reordering» intero.
> - **Wiki**: `graphify-out/graph.json` assente (atteso in una worktree nuova). Lette direttamente `decisions/financial-math-single-average-cost`, `entities/portfolio-engine`, `entities/lots-analysis-service`. Ingresso di I: §16 del piano 41, non rifatto.
> - **Fonti**: 6 sottoagenti `explore` in sola lettura per l'inventario (backend orchestrazione, backend dati, AI Export, rischio/segnali/PAC, frontend portafoglio, frontend mercati), 3 per la parte 2, più le mie letture.
>   - **✔** = riverificato a mano da me su `b20eac99`.
>   - Le righe senza ✔ vengono dagli inventari: si riverificano quando un lotto le tocca (regola del backlog 38).
> - **Pesi**: scala del backlog 38 (minimo, basso, medio-basso, medio, alto), coi conteggi che li motivano.

## 0. Mandato e decisioni del developer

Testuali, dal kickoff del coordinatore:

1. (10/10, lotto 41) «si sono sempre daccordo nel fattorizzare, specie in matematica, verifica che non ci siano altre zone che rifanno questo calcolo con regole loro e in caso migra anche loro, ma stai attendo a verificare che il risultato finale sia migliore delle parti, se ci sono cose a cui non avevi pensato, prima di buttarle integrale»
2. (11/10) «Riguardo la funzione unica ne sono lieto, se serve un posto dove metterla mettiamola nello stesso modulo dei calcoli matematici, vicino al wac centralizzato.»
3. (11/10) «Anzi, i vari motori matematici che abbiamo fatto, abbiamo già fatto dei lavori di fattorizzazione, quanto sarebbe pesante spostarli in questo modulo, aggiungere alle info salvate in .github di guardare prima e nel caso aggiungere lì quando serve fare le operazioni matematiche finanziarie e in generale di riguardare in tutto il progetto se sono comparse altre implementazioni copie parziali di quelle fattorizzate?»
4. (11/10) «a suo tempo ricordo avevamo fatto anche backend/app/utils/financial , magari anche loro ha senso migrarle a questo service layer»
5. (11/10) «analisi approvata, la stima dei tempi è ragionevole anche se sono fiducioso farai prima, male che vada posticipiano l rilascio, queste sono cose importanti. Riguardo a risk, segnali e pac sono daccordo, la matematica comune deve essere ripresa dal modulo, ma per il resto vive bene dovè»
6. (`TODO_FUTURI.md`, «Code reordering», non ancora committata) moduli dedicati, service layer, niente file di servizio onnivori; e per il frontend: «Discorso simile da fare anche per il frontend, dove i componenti sono cresciuti e vanno raggruppati in cartelle più piccole e coerenti, con nomi chiari e significativi.» Il developer: «si incluiamola nel treno, e se T riesce a fare un analisi anche per quello allora quando poi la applichiamo la cancelliamo».

- **Regola del coordinatore** (entra col treno 33, assente dalla base): la decisione 10 di `copilot-instructions.md` («One home for financial math — … `backend/app/services/financial_math/` …») e la mappa in `backend.instructions.md`.
- **Vincolo**: `portfolio_engine.py`, `portfolio_service.py` e `financial_math/` non si toccano finché il lotto 41 con F non è entrato. Lo spostamento viene dopo F e prima della 1.2.

### 0.1 Autorizzazione (2026-10-11)

- **Developer**, testuale, sulla parte 1 (via il coordinatore, dopo la sintesi con D-1…D-11 e i consigli): «si approvo tutto riguardo a B2, giusto una nota, è 100 per le obbligazioni perchè non si usa il campo che dice che per quell'asset il prezzo rappresenta 100 titoli, bisogna usare la funzione di normalizzazione come nel portafoglio, non semplicemente dividere per 100».
  - Quindi **D-1…D-11 approvate come consigliato** (§8).
  - B2 si corregge con `compute_holding_value` / `normalize_quote_base_quantity`, mai con una divisione per 100.
- **Developer**, testuale, sulla parte 2: «si approvo e andiamo, ma non vietiamoci a prescindere di fare anche il resto, se finiamo in fretta, esendiamo un pezzo alla volta la portata».
  - Quindi **D-P1…D-P6 approvate come consigliato** (§P2.7).
  - Prima della 1.2: **PL3 e BU1**. FE1 aspetta la review C7 dell'onboarding (Q).
  - Il resto si aggiunge un lotto alla volta, sempre passando dal coordinatore.
- **Coordinatore** (2026-10-11), l'ordine:
  1. questo piano nel journal;
  2. B1, B2 e B3, ognuno col suo rosso prima, via `test-author`, sulla corsia 6164; B3 = «—» più la coppia nel banner;
  3. un checkpoint FROZEN, coi messaggi di commit e le righe del CHANGELOG (le scrive lui);
  4. PL3, poi un checkpoint;
  5. BU1: prima di cominciare, l'elenco dei file toccati al coordinatore (lo confronta con I, M e P);
  6. T-1 dopo F.
- **Coordinatore**, sulle dipendenze: `npm ci` approvato, una volta, in `frontend/`, dal lock esistente (`node_modules` assente, confermato).
- **Coordinatore**, sulla probe di B2: niente dati di produzione.
  - Si popola il DB della corsia 6164 con i dati sintetici.
  - Se c'è un asset con `quote_base_quantity ≠ 1`, probe mirata su quello. Altrimenti bastano i test funzionali, e nel checkpoint si scrive «probe non eseguita: nessun qbq≠1 nei dati di test».
- **v1.1.0** (tag `837a8f2c7`, 2026-09-07): i tre bug c'erano già, quindi vanno sotto 🐛 Fixed del capitolo 1.2.
  - B1 da `2fd6a44c2` (2026-03-02);
  - B2 da `3e3f9c41f` (2026-09-01);
  - B3 da `2a647c2f1` (2026-07-16).

## 1. Stato reale (verificato su `b20eac99`)

### 1.1 Le case di oggi

| Casa | File | Righe | Chi la importa (app) | Test |
|---|---|---|---|---|
| Costo medio | `services/financial_math/average_cost.py` | 505 | engine, `portfolio_service`, `lots_analysis_service`, `broker_service` | `test_financial_math/test_average_cost.py` |
| Stato giornaliero | `services/portfolio_engine.py` | 2 837 | `portfolio_service` (8 import pigri), `lots_analysis_service:59`, `portfolio_allocation_source:1319` (pigro) | 19 file, 23 riferimenti |
| Lotti FIFO | `services/fifo_lot_engine.py` | 1 604 | `lots_analysis_service:44`, `yield_on_cost:28` | 2 file |
| Yield on Cost | `services/yield_on_cost.py` | 856 | `portfolio_service:89` | 1 file |
| ROI, TWRR, MWRR | `utils/financial/roi_utils.py` (+ barile pigro `__init__.py`, 75 righe) | 437 | engine:54, lots:62, `portfolio_service:95` | `test_utilities/test_roi_utils.py` (164) **e** `test_financial/test_roi_utils.py` (835) |
| Valore di una posizione | `utils/financial/valuation_utils.py` | 26 | engine:55, lots:63, `portfolio_service:107`, `broker_service:60`, AI `components/fx_core.py:87` | 2 file |
| Prezzo del giorno (fuori mappa) | `services/price_resolver.py` | 298 | engine:51, lots:60 | 12 file |
| Analisi dei lotti (da dividere) | `services/lots_analysis_service.py` | 2 032 | `api/v1/portfolio_api.py:35`, AI `asset_resources.py:42`, `payloads/portfolio_broker.py:61` | 7 file. Il puro (1 412 righe) costruisce `LotsAnalysisService(db=None)` e chiama metodi privati ~80 volte |
| Cambi | `services/fx.py` (`convert_bulk` :1240) | 1 679 | 19 file | resta dov'è: è infrastruttura (sync, salvataggio) |

- **Da spostare**: ~6 600 righe (engine, FIFO, YoC, roi, valuation, price_resolver) + ~800 righe di matematica dei lotti.
- **Superficie d'import** ✔: ~27 righe nell'app, ~50 riferimenti in ~35 file di test, 5 nel runner.

### 1.2 Dipendenze ✔

- **Nessun ciclo**: nessun modulo da spostare importa servizi d'orchestrazione (`portfolio_service`, `broker_service`, `transaction_service`, `lots_analysis_service`), API o AI Export. L'unica menzione è una docstring (`price_resolver.py:261`).
- **Il layer legge già dal DB**. L'engine importa `settings_service.get_effective_base_currency`, `fx.convert_bulk`, `price_resolver`, `data_quality_thresholds`, `utils/cache_utils`, `roi_utils`, `valuation_utils`, `average_cost`, e carica i dati da sé (`PortfolioCalculationEngine`). YoC carica transazioni e split (`_load_transaction_context`, `_load_split_records`). La regola attuale («prende i dati semplici del problema») va emendata (§3.2).
- **Gli 8 import pigri** dell'engine in `portfolio_service` (`:590`, `:688`, `:1287`, `:1439`, `:1490`, `:1675`, `:1742`, `:2117`) non rompono cicli. Restano pigri; cambia solo il percorso.
- **Un uso improprio**: `lots_analysis_service.py:867` costruisce un `DerivedViewsBuilder([], …)` vuoto solo per chiamarne `build_data_quality_report`.
- **Un nome privato importato da fuori**: `portfolio_allocation_source.py:1320` prende `_QUANTITY_DUST_THRESHOLD` da `portfolio_service`. È un alias di `data_quality_thresholds.QUANTITY_DUST_THRESHOLD`.
- **Identificatori-contratto che contengono nomi di modulo: non si toccano**:
  - `source_ref="portfolio_engine.PortfolioCalculationEngine"` (`portfolio_allocation_source.py:311`, evidenza salvata del PAC);
  - `Literal["portfolio_engine_market_value"]` (`schemas/portfolio.py:1435`, `portfolio_allocation_source.py:1427`);
  - `requires_lots_analysis_service` (9 volte in `ai_export/datasets/catalog.py`).
- **Presentazione nel layer**: `SECTOR_EMOJIS` (`portfolio_engine.py:76`) finisce nell'allocazione esportata (`:2043`).

### 1.3 I mock dei test decidono la strategia degli import ✔

I test patchano **variabili globali del modulo**, importato come oggetto:

- `portfolio_engine_module.convert_bulk` (`test_portfolio_engine_vnext.py:893`, `test_broker_internal_flows.py:1229`);
- `yoc_module.convert_bulk` e `_run_component_replay` (`test_yield_on_cost.py:1448`, `:1545`, `:1577`, `:1677`);
- `module.convert_bulk` dei lotti (`test_lots_analysis_pure.py:1383`, `:1397`);
- `average_cost.convert_bulk` (`test_average_cost.py:130`, `:136`; `test_portfolio_cost_currency.py:799`);
- `roi_utils.scipy_newton` (`test_utilities/test_roi_utils.py:36-151`, 5 volte);
- `portfolio_engine.PortfolioCalculationEngine`, letto dall'import pigro del PAC (`test_portfolio_allocation_source.py:2187`).

Le patch sugli attributi di classe (`DailyStateBuilder.build`, `_internal_transfer_flows`, `PortfolioCalculationEngine.calculate`, `LotsAnalysisService.get_lots_analysis`) non dipendono dal percorso.

**Conseguenza**: uno shim al vecchio percorso, che ri-esporta il nuovo modulo, rende **muta** ogni patch sulle globali.
- Il test patcha lo shim, il codice legge il modulo vero: il finto non scatta e il test può passare a vuoto.
- Dopo il taglio in sotto-moduli, ogni patch punta al **modulo che definisce** il nome usato (es. `financial_math.portfolio.engine.convert_bulk`), mai al pacchetto.

### 1.4 Già fatto, contraddetto, da sapere

- **Backlog P-5** («migrare `roi_utils` e `valuation_utils`», `38_postReleaseBacklog/README.md:295`) è dentro questo lotto: si chiude con T-1a.
- **§16, punto 11 del piano 41** dice «`BrokerCard.svelte` e `KpiSection.svelte` leggono soltanto».
  - BrokerCard: ✔ vero (`:146-192`).
  - **KpiSection: ✔ falso**. Calcola il Δ del giorno (`:77-82`), il Δ% su |NAV di ieri| (`:90-99`), il Δ% su |P&L di ieri| (`:128-131`) e l'effetto timing MWRR − TWRR (`:238`).
- **Il limite noto della wiki sui lotti** (ripiego sull'importo non convertito) è ancora vero ✔: `lots_analysis_service.py:963`, `:1646-1647`, `:1731-1732`, `:1927`, `:1957`.
- **devWiki**: `check_source_paths.py` sulla base dà **11 percorsi inesistenti (17 occorrenze) in 12 pagine**, preesistenti. Le tabelle «Source files» citano i moduli da spostare 87 volte, in 50 pagine.
- **ROI**: due file di test per lo stesso modulo (`test_utilities/` e `test_financial/`).
- **`pyproject.toml`**: `:85` nomina il barile `utils/financial/__init__` (eccezione RUF022). `testpaths = ["backend/tests"]` (`:105`) punta a una cartella che non esiste: fuori perimetro, solo segnalato.

## 2. Inventario classificato (A)

### 2.0 Legenda

- **Classi**:
  - **(a)** misura la stessa cosa della casa → chiama la casa;
  - **(b)** ha regole che la casa non ha → prima la regola nella casa, con un test, poi la migrazione;
  - **(c)** misura di proposito altro → resta, col perché.
- **Lotto**: T-1x = spostamento puro; Ux = unificazione; Bx = bug (§7.1). F = lotto 41 di I; P2 = parte 2.
- **Percorsi**: backend relativi a `backend/app/services/` salvo indicazione; frontend relativi a `frontend/src/`.

### 2.1 Rendimenti e annualizzazione — casa: `financial_math/returns.py` (da `roi_utils`)

| # | Dove | Cosa | Chi lo legge | Classe | Lotto |
|---|---|---|---|---|---|
| R1 ✔ | `portfolio_service.py:1040-1098` (summary) e `:1316-1350` (history) | ribasamento del periodo scritto due volte (flusso sintetico −NAV iniziale, filtri, TWRR/MWRR). In entrambe i due rami `if/else` sono identici; solo history antepone lo snapshot iniziale (`:1347-1348`) | summary, storico | (a), con una divergenza | U4 |
| R2 | `portfolio_service.py:2249-2290` | riprova MWRR a freddo quando summary e storico divergono | report | (c) oggi; sparisce con R1 | U4 |
| R3 | `portfolio_service.py:951-958` | rendimento netto del titolo (non realizzato + entrate − costi)/costo, poi CAGR | holdings | (b): la casa non ha un «rendimento netto»; i lotti ne hanno un altro (`lots_analysis_service.py:1333`) | U4 |
| R4 | `portfolio_service.py:1926-1976` | P&L di periodo della posizione, % su \|inizio\|, annualizzato con base di ripiego; per i chiusi P&L/costo impiegato | contributi | (b) | F / B8 |
| R5 ✔ | `portfolio_service.py:1110` | `total_gl_pct = gl/invested`, 0 se ≤ 0 | testata | (a) `calculate_simple_roi` | U4 |
| R6 ✔ | `series_preparation.py:66-81` (`observed_annualization`); copie in `risk/service.py:1153` e `risk_plugins/comparison.py:236` | fattore osservazioni × 365 / giorni | plugin di rischio, segnali | (b) per la casa; (a) le due copie | U4 |
| R7 | `risk/metrics.py:461-468` | da cumulato a periodo (l'inverso del TWRR) | `risk/service.py:1150` | (b) | U4 |
| R8 | `risk/metrics.py:128-135`, `:287-292`; `risk_plugins/comparison.py:58-65` | composizione Π(1+r) − 1 e indice di ricchezza, in float | KPI, confronto, drawdown | (a) dentro risk; (c) rispetto alla casa in Decimal | U4: una copia + test di parità |
| R9 | `risk/metrics.py:208-222`, `risk/quant/riskfolio_worker.py:39-45` | tasso annuo → per periodo, expm1(log1p(R)/f) | Sharpe/Sortino, ottimizzatore | (a) ×2 | U4 |
| R10 | `series_preparation.py:355-359`; `signal_plugins/calendar_rolling_return.py:237` | rendimento semplice close/rif − 1 | rischio, segnali | (b) per la casa; il segnale resta (c) per il riferimento di calendario | U4 |
| R11 | `risk/signal_helpers.py:213-267` | volatilità e Sharpe mobili (pandas), gemelli di `metrics.py` | segnali | (b): manca un test di parità | U4 |
| R12 | AI `components/payloads/portfolio_broker.py:383-390` | ribasamento del TWRR a mano, (1+e)/(1+s) − 1 | bucket di performance | (a) | U9 |
| R13 | AI `technical_shared.py:819`; `technical_context.py:322-329`, `:626-627`; `fx_timing_context.py:323-336`; `asset_fx_technical.py:219`; `drawdown_context.py:498` | rendimenti di prezzo e base 100, 5 copie | fatti tecnici | (c) il fatto; (a) la sotto-matematica | U9 |
| R14 | AI `components/asset_core.py:478-480` | P&L % = Σpnl / \|Σinizio\| | performance dell'asset | (a), con una regola propria del denominatore | U9 |
| R15 ✔ | `routes/(app)/fx/[pair]/+page.svelte:287-295` | Δ% della coppia invertita = −pct | testata della coppia | **bug**: vale primo/ultimo − 1; disallineato da FxCard e FxTable | B1 |
| R16 | `lib/utils/assetPriceDerived.ts:126-146`, `:154-168` (anche nel worker); `routes/(app)/fx/+page.svelte:179-197`; `lib/components/fx/FxTable.svelte:106-119`; `FxCard.svelte:95-103` | Δ% di periodo e d'intervallo, per asset e FX (anche invertiti) | liste e card | (b): il backend non li espone | U8 |
| R17 ✔ | `lib/components/dashboard/KpiSection.svelte:77-131`, `:238` | Δ del giorno, Δ% su \|NAV\| e su \|P&L\|, effetto timing | card KPI | (b) | U8 |
| R18 | `lib/charts/signals/MeasureSignal.ts:99-133` | Δ, Δ%, annualizzato (1+Δ)^(365/g) − 1 **senza** la soglia di 30 giorni della casa | MeasurePanel | (c) misura interattiva, con una regola diversa | D-9 |
| R19 | `lib/utils/chartUtils.ts:12-17`, `lib/charts/signals/backendRenderer.ts:36-39`, `AssetComparisonSignal.ts:66-72`; `CompoundSignal.ts`, `LinearSignal.ts`, `SineSignal.ts` | ribasamento in % per la vista (3 copie, due regole sul primo punto); curve what-if | grafici | (c) | P2: un helper frontend |

### 2.2 Valorizzazione e prezzo del giorno — casa: `financial_math/valuation.py` + `price_marks.py` (D-1)

| # | Dove | Cosa | Chi | Classe | Lotto |
|---|---|---|---|---|---|
| V1 ✔ | `lots_analysis_service.py:99-123` (`_PriceHistoryLookup`) | LOCF sul close, senza ultimo scambio né staleness; flag exact/fallback | lotti | (b) per il flag; per il resto (a) | U5 |
| V2 ✔ | `portfolio_service.py:522` (`_get_price_at_date`) | ultima chiusura (B8). La usa anche la variazione a 1 giorno (`:903-928`), che mischia il prezzo del motore (oggi) e la chiusura grezza (ieri) | contributi, holdings | (a) | B8 / U5 |
| V3 | `broker_service.py:549-562` | ultima chiusura per asset | `GET /brokers/{id}/summary` | (a) | U5 |
| V4 | `portfolio_allocation_source.py:72-105` | ultima chiusura ≤ as_of | PAC | (b)/(c): istantanea esatta dello scenario | D-5 |
| V5 ✔ | `pac_allocator/numeric.py:450-457` (`exact_holding_value`) + `evaluator.py:481`, `:673`, `:2085`; `normalize.py:869`; `constraints.py:207` | qty × prezzo / base, moltiplicando prima (Fraction e Decimal) | solver | (b): l'ordine è più esatto | U5: `holding_value` generica |
| V6 ✔ | AI `components/asset_core.py:548` | valore d'apertura del lotto = `reference_unit_price × quantità`. Il prezzo è per qbq unità (`lots_analysis_service.py:1801-1811`): manca la divisione | AI F6 | **bug** per qbq ≠ 1 (obbligazioni ×100) | B2 |
| V7 ✔ | AI `asset_core.py:347`; `payloads/portfolio_broker.py:582` | `unit_price = valore / quantità` | righe asset e posizioni | (a)? Dipende dal contratto (per unità o per qbq) | U9 |
| V8 | AI `fx_core.py:362-372` | ramo di ripiego qty × prezzo | esposizione FX | (a) | U9 |
| V9 ✔ | `lots_analysis_service.py:1810` | normalizzazione qbq locale | riferimento d'apertura | (a) `normalize_quote_base_quantity` | T-1f |
| V10 | `asset_sources/core.py:298`, `:573` + `price_query.py` | riempimento dei giorni mancanti in lettura | API prezzi | non verificato | U5 |
| V11 | `lib/components/brokers/lots/lotWacPriceChartHelpers.ts:107-109`; `LotWacPriceChart.svelte:1405` | WAC × qbq; valore del BUY = qty × prezzo | grafico dei lotti | (b)/(a) | U8 |

### 2.3 Cambi — casa: `fx.convert_bulk` + nuovo `financial_math/fx_conversions.py`

| # | Dove | Cosa | Chi | Classe | Lotto |
|---|---|---|---|---|---|
| X1 ✔ | `portfolio_engine.py:2737` (`_preload_fx_rates`), `:1474` (`_convert`); letture dirette `:1460`, `:1569` | piano di cambi, mappa, mancanti | motore | futura casa | U1 |
| X2 ✔ | `lots_analysis_service.py:125-166` (`_FxRateResolver`) + 6 ripieghi `… or <non convertito>` | conversione col ripiego silenzioso | lotti | (b) al rovescio: la sua regola è peggiore | B3 / U1 |
| X3 ✔ | `yield_on_cost.py:443-527` | piano di conversioni con provenienza (data del tasso, backfill) | YoC | (b): la provenienza manca altrove | U1 |
| X4 ✔ | `financial_math/average_cost.py:348` (`_conversion_requests`) | richieste in blocco, `MissingConversion` | costo medio | casa (P) | U1 |
| X5 ✔ | `portfolio_service.py:540-560` (`_convert_to_base`, una chiamata per importo) e `:1517-1567` (per transazione) | conversioni una a una | summary, storici di entrate, costi e depositi | (a) | F / U1 |
| X6 ✔ | `asset_sources/price_query.py:476-489` | fattore = close convertito / close; salta la barra se close = 0 | prezzi convertiti (rischio, segnali) | (a): usare il tasso | U1 |
| X7 | `fx.py:1474` (upsert); `api/v1/fx.py:256-261` | inversione 1/rate inline | salvataggio dei tassi | (a) `normalize_rate_for_storage` | U1 |
| X8 | `api/v1/fx.py:664-666` | tasso effettivo ricavato da importi arrotondati | endpoint di conversione | (a) | U1 |
| X9 ✔ | `pac_allocator/evaluator.py:196-206`; `normalize.py:619-631` | coppia diretta o inversa, esatta, senza catene | PAC | (a) ×2 dentro il PAC; (c) l'istantanea | U1: `oriented_rate` |
| X10 | AI `fx_core.py:515`, `:546`; `fx_payloads.py:409-412` | cassa al cambio dell'istantanea | esposizione FX | (b), noto | F (B4 di I) |
| X11 ✔ | `portfolio_engine.py:64` e `portfolio_service.py:577` (`_normalize_fx_pair_slug`) | slug della coppia, due copie | banner | (a) | T-1e |
| X12 | `lib/stores/fxStoreRegistry.ts:50-54`; `FxCard.svelte:100-101`; `FxTable.svelte:113-114`; `lib/charts/signals/FxPairSignal.ts:46`; `FxDataEditorSection.svelte:186`, `:306` | 1/rate nel browser | FX | (c) capovolgimento di vista. I Δ invertiti sono R15 e R16 | U8 |

### 2.4 Costo medio — casa: `financial_math/average_cost.py` (P)

| # | Dove | Cosa | Chi | Classe | Lotto |
|---|---|---|---|---|---|
| C1 | `portfolio_service.py:239-272` | costo unitario per passo nell'anteprima | anteprima WAC | (a): un campo di `CostStep` | U4 |
| C2 | `broker_service.py:420-453` | costo dalla casa ✔; percentuale × 100 | broker summary | (a) per la percentuale | U4 |
| C3 | AI `asset_core.py:380`, `:418-420` | costo = WAC × qty, e le somme | sezione costi | (a): campo del motore | U9 |
| C4 | AI `payloads/portfolio_broker.py:164` | costo residuo pro-rata | lotti | (a): dal FIFO | U9 |
| C5 | `pac_allocator/evaluator.py:1868`; `numeric.py:413` | guadagno stimato sul WAC | PAC | (c) stima di pianificazione | — |
| C6 | `lib/components/transactions/modals/TransactionBulkModal.svelte:1850` | WAC × \|qty\| | cella del bulk | (c) vista; file di P | — |

### 2.5 Lotti e finestre di detenzione — casa: `financial_math/fifo/`

| # | Dove | Cosa | Chi | Classe | Lotto |
|---|---|---|---|---|---|
| L1 ✔ | `portfolio_service.py:393-418` (`_oldest_open_lot_date`) | mini-FIFO sulle sole quantità | holdings (`:844`), contributi (`:1853`) | (a), con due divergenze. Uno split (ADJUSTMENT +q) apre un «lotto» datato allo split. Un trasferimento in entrata è datato all'arrivo, mentre il FIFO tiene la data d'origine | B4 / U6, D-7 |
| L2 ✔ | `portfolio_service.py:432-454` (`_closed_position_window`) | quantità cumulata con la soglia della polvere | contributi dei chiusi (`:1972`) | (b): la soglia non è nel FIFO | U6 |
| L3 | `brim_providers/broker_credit_agricole.py:998-1000` | posizione per nome durante il parsing | parser | (c) | — |

### 2.6 Quote di proprietà — casa proposta: `financial_math/ownership.py`

| # | Dove | Cosa | Chi | Classe | Lotto |
|---|---|---|---|---|---|
| O1 ✔ | `portfolio_engine.py:2489` | OWNER: `share_percentage`, oppure 1; EDITOR/VIEWER: 1 | motore | casa | U3 |
| O2 ✔ | `portfolio_service.py:755`, `:1540`, `:1779` | la stessa regola, tre copie | summary, storici, contributi | (a) | F / U3 |
| O3 ✔ | AI `portfolio_income.py:350`; `broker_cost_efficiency.py:154`, `:353` | quota grezza senza ruolo; `abs` sul reddito (B9) | AI | (b), bug noto | U3 / U9 |
| O4 ✔ | `portfolio_allocation_source.py:543-544`, `:596-597` | qty × `share_percentage`, `None` non gestito | PAC | da verificare: crash, oppure filtro a monte | U3 |

### 2.7 Frazionamenti — casa proposta: `financial_math/splits.py`

| # | Dove | Cosa | Chi | Classe | Lotto |
|---|---|---|---|---|---|
| S1 ✔ | `portfolio_engine.py:130-176` (`SplitRecord`, `_cumulative_split_ratio`); caricamento `:2510-2520` | rapporto cumulato; valida solo «rapporto finito > 0» | valutazione | futura casa | U2 |
| S2 ✔ | `yield_on_cost.py:65`, `:385-411`, `:732-755`, `:805-856` | caricamento con validazione stretta (tipo, quantità, asset, data, duplicati per broker) e rapporto per broker | YoC | (b): la validazione è più stretta | U2 |
| S3 ✔ | `lots_analysis_service.py:645` (`_load_split_ratios`) | caricamento | lotti, FIFO | (a) | U2 |

### 2.8 Pesi e concentrazione — casa: l'allocazione del motore; proposta `financial_math/allocation.py`

| # | Dove | Cosa | Chi | Classe | Lotto |
|---|---|---|---|---|---|
| W1 | `portfolio_service.py:1028-1034` | % di allocazione su Σ valori, senza il valore in viaggio; peso sul NAV con denominatore 1 se NAV ≤ 0 | holdings | (a)/(b) | F / U7 |
| W2 | AI `asset_core.py:253-287`; `technical_shared.py:473-485`, `:531-537` | pesi su \|valore\| lordo, tre definizioni | AI | (b): varianti esplicite nella casa | U7 |
| W3 | AI `broker_financial.py:202-208` = `broker_concentration_context.py:97-103` | HHI e peso massimo: codice identico | AI | (a) | U7 |
| W4 | AI `broker_concentration_context.py:208-214`, `:409`; `technical_shared.py:1405-1441`; `technical_context.py:646-659`; `portfolio_broker_technical.py:157-191` | quote %, rapporti di copertura (3 copie) | AI | (a)/(c) | U9 |
| W5 | `risk/service.py:536-562` | pesi = valore/NAV, cassa = 1 − Σ, rinormalizzazione D59 | rischio | (b)/(c) | U7 |
| W6 | `portfolio_allocation_source.py:1292` | pesi di scenario senza cassa | PAC | (c) | — |
| W7 | `lib/components/dashboard/ExposureTable.svelte:179` | ripiego valore/NAV × 100 | tabella | (a): togliere il ripiego | U8 |
| W8 | `lib/components/dashboard/ExposureTreemap.svelte:442-445` | G/L% del nodo, col costo ricavato come valore − gl | treemap | (b) | U8 |
| W9 | `SemiDonutChart.svelte:207`; `allocationRings.ts:100`, `:186`; `allocationHierarchy.ts:211` | somme di fette per «Altro» e per i tooltip | grafici | (c) | — |

### 2.9 Stato del portafoglio e flussi di periodo — casa: il motore (oltre §16 di I)

| # | Dove | Cosa | Chi | Classe | Lotto |
|---|---|---|---|---|---|
| P1 | `portfolio_service.py:595-665` (`_compute_period_summary_metrics`); lo stato d'inizio periodo ripetuto in `:318-357` | P&L di periodo = NAV fine − NAV inizio − flussi | summary, report | (a) | F |
| P2 | `portfolio_service.py:903-928` | variazione a 1 giorno di prezzo e valore | holdings | (a) | B8 |
| P3 | AI `broker_cost_efficiency.py:550-560` | NAV medio | rapporti di costo | (b): metrica nuova | U9 |
| P4 | `lib/components/dashboard/PerformanceChart.svelte:197-208` | contributo % sul valore d'apertura | tooltip | (b) | U8 |
| P5 | `lib/components/brokers/lots/LotComparisonChart.svelte:592-606`; `unifiedLotsTableHelpers.ts:126-138` | rendimento aggregato dei lotti, totali del piè di tabella | lotti | (b) | U8 |
| §16 | punti 1–10 di I | capitale, NAV e P&L della card e del servizio | — | già classificati da I | F / H |

### 2.10 Interessi e calendario — casa proposta: `financial_math/interest.py` (D-8)

| # | Dove | Cosa | Chi | Classe | Lotto |
|---|---|---|---|---|---|
| I1 | `asset_source_providers/scheduled_investment.py:71-183` | convenzioni ACT/365, ACT/360, ACT/ACT, 30/360; interesse semplice | provider SI | (c) il dominio; le primitive sono generiche | U10 |
| I2 | `scheduled_investment.py:233-400`, `:403-527`, `:529-630` | tre cammini di maturazione (serie, prezzo corrente, mora) | provider SI | (a) dentro il file | U10 |

### 2.11 Statistiche delle serie — casa: `risk/metrics.py` (resta dov'è)

| # | Dove | Cosa | Chi | Classe | Lotto |
|---|---|---|---|---|---|
| Q1 | AI `technical_context.py:855`, `:863`; `fx_timing_context.py:329-362`; `asset_fx_technical.py:229` | rendimenti giornalieri e `pstdev`, 3 copie | AI | (a), con `ddof` esplicito | U9 |
| Q2 | AI `drawdown_context.py:498` | rendimenti locali, poi `drawdown_episodes` della casa | AI | (a) parziale | U9 |

### 2.12 Segni e derivazioni d'importazione — fuori dalla casa (P2)

| # | Dove | Cosa | Chi | Classe | Lotto |
|---|---|---|---|---|---|
| G1 | BRIM, ~15 plugin (`broker_avanza.py:81`, `broker_bux.py:108`, `broker_disnat.py:95`, …) | segni: BUY −, SELL +, FEE/TAX − | BRIM | (a) dentro BRIM | P2 (`_brim_io`) |
| G2 | `broker_credit_agricole.py:1074`; `broker_intesa.py:369`; `broker_danske_bank.py:1529-1535` | costo unitario = costo/qty; prezzo/100 delle obbligazioni; commissioni ricavate dai totali, con la soglia 15 / 1 % | parser | (c) | — |
| G3 | `TransactionFormModal.svelte:1298`; `TransactionBulkModal.svelte:234`, `:1788`, `:2273` | regole di segno nel form | form | da verificare: solo vista o anche payload (file di P) | U8 |

### 2.13 Dove non c'è matematica (controllato)

- **Backend**:
  - nessun calcolo in `fx_providers/*`, `brim_gap_fix.py`, `brim_parse_pool.py`, `brim_report_sets.py`, `scheduler/**`, `market_calendar.py`, `date_sentinel.py`, `asset_source.py`, `db/models.py`;
  - nessuno nemmeno in `settings_service.py`, `global_settings_service.py`, `backup_service.py`, `transaction_batch_context.py`, `transaction_batch_stages.py`;
  - `data_quality_thresholds.py` contiene solo costanti;
  - `transaction_service.py:441-480` somma cassa e quantità solo per validare i saldi: (c), registro di custodia.
- **Frontend** (letto, non calcola): `BrokerCard.svelte` ✔, `ContributionTable`, `YieldOnCostCell`, `AllocationPanel`, il renderer dell'AI Export (`promptRenderer.ts:149` è solo formato), gli helper del rischio (percentuali dell'utente → frazione).
- **Indicatori**: il frontend non li calcola più, arrivano dal backend (`lib/charts/signals/backendRenderer.ts`, `resultMapper.ts`).

## 3. La casa: disposizione proposta (B)

Coerente col «Code reordering»:
- un pacchetto è un service layer, un modulo è un problema;
- nessun file onnivoro: i motori grandi diventano sotto-pacchetti.

### 3.1 Albero

```text
backend/app/services/financial_math/
├── __init__.py            regola del layer + mappa dei moduli (solo docstring, nessuna ri-esportazione)
├── average_cost.py        costo medio (P, invariato)
├── native_cash.py         registro della cassa nativa (F di I; nome da concordare, §6)
├── returns.py             ← utils/financial/roi_utils.py
├── valuation.py           ← utils/financial/valuation_utils.py
├── price_marks.py         ← services/price_resolver.py                              (D-1)
├── yield_on_cost.py       ← services/yield_on_cost.py
├── fifo/
│   ├── __init__.py
│   ├── models.py          ← fifo_lot_engine.py:70-374     protocolli, dataclass, risultati
│   ├── engine.py          ← :375-1540                     FifoLotEngine, run_fifo_lot_engine
│   └── eligibility.py     ← :1542-1604                    eligible_income_quantity, helper
├── portfolio/
│   ├── __init__.py
│   ├── models.py          ← portfolio_engine.py:120-235, 447-622, 1799-1849   stati, risultati, ValuationSource/Result, SplitRecord
│   ├── classifier.py      ← :73-118, 236-446              ScopeAwareTransactionClassifier, tipi collegati
│   ├── daily_state.py     ← :623-1798                     DailyStateBuilder
│   ├── derived_views.py   ← :1850-2318                    build_cost_positions, DerivedViewsBuilder
│   ├── data_quality.py    ← build_data_quality_report, load_configured_fx_pair_sets, slug della coppia
│   └── engine.py          ← :2319-2837                    PortfolioCalculationEngine: caricamenti, preload dei cambi, cache
└── lots/
    ├── __init__.py
    ├── prices.py          ← lots_analysis_service.py:82-123   (provvisorio, fino a U5)
    ├── conversions.py     ← :125-166                          (provvisorio, fino a U1)
    ├── economic_events.py ← :1018-1202                        eventi economici, adattatore al FIFO, estrazioni
    ├── histories.py       ← :915-1017, :1625-1859, :1881-1976 storici di valore, rendimento, performance, prezzo
    └── average_cost_lines.py ← :825-914                       linee del costo medio

backend/app/services/lots_analysis_service.py   resta: orchestrazione, caricamenti dal DB, DTO, qualità dei dati (~1 100 righe)
backend/app/services/fx.py                      resta: infrastruttura dei cambi (convert_bulk è la primitiva)
backend/app/utils/financial/                    sparisce
```

- Le righe sono indicative, su `b20eac99`: F le sposterà.
- `DailyStateBuilder` resta un modulo da ~1 200 righe. Tagliarlo ancora (valutazione, cassa, trasferimenti) è lavoro della parte 2, non dello spostamento.

### 3.2 Regola del layer (emendata)

1. Un calcolo possiede tutto il suo problema (invariato).
2. Il layer chiama i servizi d'infrastruttura che gli servono: `fx.convert_bulk`, la valuta base da `settings_service`, le soglie di `data_quality_thresholds`, la cache.
   - **Può leggere dal DB i dati del proprio problema**, in punti nominati: `portfolio/engine.py`, i caricatori di `yield_on_cost.py` e degli split.
   - Questo emenda «prende i dati semplici»: oggi engine e YoC leggono già dal DB. Separare i caricatori è lavoro della parte 2.
3. Non importa mai servizi d'orchestrazione (`portfolio_service`, `broker_service`, `transaction_service`, `lots_analysis_service`), né API, AI Export, rischio, PAC, segnali. Sono loro a chiamare il layer.
4. Nessun ripiego silenzioso: un cambio, un prezzo o un costo mancante si segnala (`MissingConversion`, `missing_fx`, issue), non diventa mai un numero.
5. Nessuna ri-esportazione: si importa dal modulo che definisce il nome, perché i mock lo richiedono (§1.3).
6. Il frontend non calcola nessuna di queste grandezze. Le eccezioni sono interattive (misura, what-if) e dichiarate (R18, R19).

**Guardie** (T-1g, via `test-author`):
- `test_financial_math/test_layer_boundaries.py` analizza con `ast` ogni modulo del layer. Fallisce su un import vietato (regola 3) e su una ri-esportazione in un `__init__` (regola 5).
- Un secondo test verifica che i vecchi moduli non esistano più: protegge dai rami vecchi che li ricreano con un merge.

### 3.3 Mappa vecchio → nuovo

| Vecchio | Nuovo | Import da riscrivere |
|---|---|---|
| `backend.app.utils.financial.roi_utils` | `backend.app.services.financial_math.returns` | app 4 (+ barile), test 4 in 3 file, runner 1 |
| `backend.app.utils.financial.valuation_utils` | `…financial_math.valuation` | app 5, test 2 |
| `backend.app.utils.financial` (barile) | — (eliminato) | `__init__`, più test e runner che lo nominano |
| `backend.app.services.yield_on_cost` | `…financial_math.yield_on_cost` | app 1, 1 file di test (4 patch) |
| `backend.app.services.price_resolver` | `…financial_math.price_marks` | app 2, 12 file di test |
| `backend.app.services.fifo_lot_engine` | `…financial_math.fifo.{models,engine,eligibility}` | app 2, 2 file di test |
| `backend.app.services.portfolio_engine` | `…financial_math.portfolio.{models,classifier,daily_state,derived_views,data_quality,engine}` | app 10 (8 pigri); test 19 file, 23 riferimenti, 7 patch su globali |
| metodi puri di `LotsAnalysisService` | funzioni in `…financial_math.lots.*` | test puri: ~80 chiamate |

## 4. Strategia dello spostamento (B)

### 4.1 Import diretti, niente shim

- **Contro gli shim, tre motivi concreti**:
  1. le patch mute (§1.3);
  2. uno shim tiene vivo il vecchio percorso, e un ramo vecchio ci riattacca codice;
  3. il developer chiede una casa sola: due nomi per lo stesso modulo sono una seconda casa.
- **A favore degli shim, nessuno**: la superficie d'import è piccola (§1.1).
- **Strumento**:
  - sostituzione esatta dei percorsi puntati; gli import pigri si riscrivono a mano;
  - poi `ruff check` (import inutilizzati e ordine) e `black`;
  - infine un grep dei vecchi percorsi, a zero, in `backend/`, `scripts/`, `.github/`, `mkdocs_src/docs/developer/`.
- Gli identificatori-contratto di §1.2 restano esclusi dalla sostituzione.

### 4.2 Due commit: prima la rinomina, poi il taglio

- **Commit A — rinomina**: `git mv` dei file interi, più gli import. L'engine va in `portfolio/engine.py`, il FIFO in `fifo/engine.py`, gli altri ai nomi finali.
  - La somiglianza resta ~99 %: `git log --follow` e `blame` restano utili.
  - Un ramo vecchio che tocca il file si riapplica sulla rinomina.
- **Commit B — taglio**: i sotto-moduli (`models`, `classifier`, `daily_state`, …) e la matematica dei lotti.
  - Git non segue un file diviso in molti; `git blame -C -C` ritrova le righe spostate nello stesso commit.
  - Da qui in poi, un ramo vecchio che tocca l'engine va in conflitto. Quindi B entra solo quando nessun ramo attivo tocca engine, FIFO o lotti (§7.4).
- I commit li fa il developer. Messaggi proposti:
  - A: `refactor(financial-math): move engines and ROI/valuation helpers into financial_math`
  - B: `refactor(financial-math): split portfolio, FIFO and lots math into modules`
  - doc: `docs(dev): document the financial_math layer`

### 4.3 Mock, runner, configurazione

- **Patch da riscrivere**: le 7 sulle globali di §1.3. Dopo B puntano al sotto-modulo che usa il nome: per `convert_bulk` e `PortfolioCalculationEngine` è `portfolio/engine.py`.
- **Runner** (file condiviso, lo scrive chi indica il coordinatore): le stringhe `print_info` coi percorsi in `_backend_services.py:573`, `:584`, `:608`, `:626` e in `_backend_utils.py:121`.
  - I percorsi dei test non cambiano (D-3): i selettori restano `services financial-math`, `roi-fifo-utils`, `portfolio-engine`, `lots-analysis-pure`, `portfolio-allocation-source` e `utils roi-utils`.
  - `services financial-math` è dichiarato `isolation="pure"`: le guardie nuove devono restare pure.
- **`pyproject.toml:85`**: il commento sul barile eliminato. Vulture punta alla cartella `backend/app`: nessun cambio.
- **API**: nessuna modifica. `api sync` si esegue una volta, solo per provare che il client generato non cambia.

### 4.4 Doc, devWiki, .github

- **Doc per sviluppatori** (solo EN, nessun debito di traduzione), via `docs-writer`:
  - una pagina nuova, `developer/backend/financial_math.md`: la regola, la mappa, i confini, come aggiungere un calcolo, le guardie;
  - percorsi da aggiornare in `developer/backend/transactions/{wac,fifo_lot_engine,lots_analysis_service,price_resolver}.md`, `developer/frontend/data-quality-banner.md`, `developer/lint_gates.md`, `developer/backend/assets/provider_borsa_italiana.md`; i nomi di modulo in altre ~12 pagine;
  - **i percorsi delle pagine restano**: le pagine di teoria, in 4 lingue, linkano `fifo_lot_engine.md` e `lots_analysis_service.md`. Così niente conflitti con M e niente debito;
  - `mkdocs.yml`: una voce di nav (file condiviso).
- **devWiki**: 87 citazioni in 50 tabelle «Source files». Consegno la tabella vecchio → nuovo; la applica lo storico o il coordinatore. `check_source_paths.py` deve restare a 11.
- **`.github`** (file condivisi):
  - la mappa di `backend.instructions.md` (versione del treno 33), coi nuovi percorsi;
  - una riga in `frontend.instructions.md`: il frontend non calcola grandezze finanziarie, mostra i campi del backend, e le misure interattive sono dichiarate;
  - proposta: `.github/instructions/financial-math.instructions.md` (`applyTo: backend/app/services/financial_math/**`), con la regola di §3.2 e le guardie;
  - la decisione 10 di `copilot-instructions.md` resta valida: il percorso non cambia.
- **Docstring di `financial_math/__init__.py`**: la mappa dei moduli e la regola emendata, senza più la frase «will move into this layer in a later refactor».

### 4.5 Codice morto e fuori posto

- **Via**: `utils/financial/__init__.py` (barile pigro, 75 righe) e la cartella.
- **Uso improprio**: `DerivedViewsBuilder([], …)` costruito solo per la qualità dei dati (`lots_analysis_service.py:867`) → una funzione in `portfolio/data_quality.py`.
- **Copia**: `_normalize_fx_pair_slug`, doppio (`portfolio_engine.py:64`, `portfolio_service.py:577`) → uno.
- **Nome privato**: `_QUANTITY_DUST_THRESHOLD`, importato dal PAC (`portfolio_allocation_source.py:1320`) → la costante pubblica di `data_quality_thresholds`.
- **Presentazione**: `SECTOR_EMOJIS` (`portfolio_engine.py:76`, `:2043`) sono dati di presentazione nel layer di calcolo. In T-1 vanno con `derived_views.py`; dove debbano vivere lo dice la parte 2.
- **Verifica**: `lint --dead-code` prima e dopo, senza reperti nuovi.

## 5. Rischio, segnali, PAC (C): restano dove sono

**Cosa prendono già dalla casa**:
- **Rischio**:
  - i cambi da `fx.convert_bulk` (`risk/eligibility.py:37`, `:271`);
  - i prezzi già convertiti da `get_prices_bulk` (`risk/service.py:670`);
  - valori e NAV del motore, via summary (`:536-547`);
  - il TWRR dallo storico (`:1141-1151`).
- **Segnali**:
  - i prezzi convertiti da `get_prices_bulk`;
  - `risk.metrics.underwater_drawdown` (`signal_plugins/drawdown.py:28`);
  - il fattore di R6 (`risk/signal_helpers.py:63`, `signal_plugins/rolling_sharpe.py:141`).
- **PAC**:
  - il costo medio, dalla facciata `compute_wac_iterative` (`portfolio_allocation_source.py:994`, `:1024`);
  - il valore di mercato, dal motore (`:1319-1322`).

**Re-implementazioni locali della matematica comune** (dettaglio in §2):
- R6–R11: rendimenti, annualizzazione, composizione. Il fattore 365 è scritto 3 volte, la conversione annuo → periodo 2, la composizione 3.
- X9: l'orientamento del tasso nel PAC, 2 copie, senza catene.
- V4: il prezzo del PAC, fuori da `price_resolver`.
- V5: la valorizzazione del PAC, in 6 punti.
- O4: la quota del PAC, senza la regola del `None`.
- W5, W6: i pesi.

**Proposta**:
- le primitive comuni vanno nella casa, in forma generica: Decimal e Fraction per la valorizzazione e per l'orientamento del tasso;
- le statistiche in float/numpy restano in `risk/metrics.py`, con un test di parità contro `returns.py`;
- rischio, segnali e PAC importano le primitive;
- la matematica di dominio (covarianza, VaR, ottimizzazione, indicatori, solver del PAC) non si tocca.

**Da segnalare a parte** (non è matematica comune): il Monte Carlo usa 365 passi fissi (`risk/quant/models.py:27`; `quantlib_worker.py:116`, `:195`), contro il fattore osservato usato altrove. È dominio del rischio: lo decide chi lo possiede.

## 6. Coordinamento con I (D)

- **Ordine**: H (T2f, T5b) → T7 (analisi di F) → F → T-1. T-1 parte dalla base che contiene F.
- **Contratto per F**, da passare a I tramite il coordinatore:
  1. il codice nuovo di F va **piatto** in `financial_math/` (proposta: `native_cash.py`), accanto a `average_cost.py`. T-1 non lo sposta;
  2. rispetta già la regola di §3.2: nessun import di servizi d'orchestrazione, import dal modulo che definisce;
  3. F aggiunge una riga per il suo modulo nella docstring di `financial_math/__init__.py`. T-1 la riscrive dopo.
- **Reperti di T per I**, assenti da §16:
  - P1: il P&L di periodo calcolato nel servizio;
  - R1/R2: il ribasamento doppio e la riprova MWRR;
  - R3/R4: il rendimento netto, i contributi;
  - L1/L2: il mini-FIFO e la finestra dei chiusi;
  - X5: i cambi convertiti uno a uno;
  - O2: la quota copiata 3 volte;
  - W1: l'allocazione senza il valore in viaggio;
  - V2/P2: la variazione a 1 giorno;
  - C1: il costo unitario dell'anteprima.

  Chi li fa, F o un lotto U dopo, lo decide il coordinatore. T non tocca `portfolio_service.py` prima di F.
- **§16, punto 11**: da correggere (KpiSection calcola, §1.4).
- **B8 si allarga**: oltre al prezzo dei contributi, anche la variazione a 1 giorno (`portfolio_service.py:903-928`) usa lo stesso prezzo.
- **Finché F non è dentro, T non tocca**: `portfolio_engine.py`, `portfolio_service.py`, `financial_math/`, `test_portfolio_engine/*`, `test_portfolio_service.py`.

## 7. Analisi d'implementazione (E)

### 7.1 Lotti, passi, peso, quando

**T-1 — lo spostamento puro**: dopo F, prima della 1.2. Gli output restano identici per costruzione.

| Passo | Cosa | Conteggi | Peso |
|---|---|---|---|
| T-1a | `roi_utils` → `returns.py`, `valuation_utils` → `valuation.py`; via `utils/financial/`. Chiude P-5 | 9 righe d'import app, 6 riferimenti di test in 5 file, runner 2, pyproject 1 | basso |
| T-1b | `yield_on_cost.py` → `financial_math/` | 1 app, 1 file di test (4 patch) | minimo |
| T-1c | `price_resolver.py` → `price_marks.py` (D-1) | 2 app, 12 file di test | basso |
| T-1d | FIFO → `fifo/`. A: rinomina in `fifo/engine.py`; B: `models`, `eligibility` | 2 app, 2 file di test | basso |
| T-1e | engine → `portfolio/`. A: rinomina in `portfolio/engine.py`; B: i 6 moduli di §3.1, con `data_quality.py` e lo slug unico | 10 app (8 pigri), 19 file di test, 7 patch; `test_external/test_brim_providers.py` costruisce il builder | medio |
| T-1f | matematica dei lotti → `lots/`, come funzioni; il servizio resta orchestrazione e DTO | ~800 righe; i test puri li riscrive `test-author` (~80 chiamate a metodi privati) | medio |
| T-1g | guardie: confini del layer e assenza dei vecchi percorsi, via `test-author` | 1 file di test, in `services financial-math` | basso |
| T-1h | doc (`docs-writer`, EN), nav, docstring del layer, `.github` (mappa, riga frontend, file d'istruzioni), tabella per la devWiki | ~20 pagine dev, 3 file `.github`, 87 righe di wiki | medio-basso |
| T-1i | gate (§7.3) | — | medio (tempo macchina) |

Totale T-1: **medio**. È meccanico ma largo: il rischio sta nei conflitti (§7.4), non nella logica.

**B — bug trovati**. Ognuno ha prima il suo rosso, via `test-author`, sulla corsia 6164. Tutti c'erano già nella v1.1.0 (§0.1). Approvati il 2026-10-11 (D-6).

| # | Cosa | Peso | Stato |
|---|---|---|---|
| B1 | Δ% della coppia FX invertita (R15) | minimo | ✅ 2026-10-11 |
| B2 | AI F6, valore d'apertura del lotto senza qbq (V6) | basso | ✅ 2026-10-11 |
| B3a | Lotti, nessun numero calcolato mescola le valute; ogni conversione mancante va nel banner. Senza cambi di contratto | medio-basso | ✅ 2026-10-11 |
| B3b | Lotti, campi base, Gantt ed eventi economici a «—». Col cambio di contratto | medio | ⏳ dopo il checkpoint di B1–B3a, prima della 1.2 |
| B4 | Data del lotto più vecchio dopo uno split (L1), quindi l'annualizzazione delle posizioni. Dipende da U6 e D-7 | medio | dopo |

**B1, disegno.**
- Un helper puro in `frontend/src/lib/stores/fxStoreRegistry.ts`, accanto a `displayFxRate`: `displayFxDelta(firstRate, lastRate, inverted) → {abs, pct} | null`, calcolato sui tassi mostrati (1/rate se invertito). Quindi, invertito: Δ% = (primo/ultimo − 1) × 100.
- Lo usano la pagina `routes/(app)/fx/[pair]/+page.svelte`, `FxCard.svelte` e `FxTable.svelte`: tre copie → una.
- Rosso: prima la formula della pagina va nell'helper **così com'è** (`inverted ? −pct : pct`), poi `test-author` scrive il test in `src/lib/stores/__tests__/fxStoreRegistry.test.ts` (già nel selettore `front-fx fx-unit`). Infine la correzione.

**B2, disegno.**
- In `backend/app/services/ai_export/components/asset_core.py`, `_build_lot_detail`: `opening_market_value = compute_holding_value(lot.original_quantity, lot.reference_unit_price, metadata.quote_base_quantity)`, con i metadati dell'asset da `_require_asset_metadata(context)`.
- `compute_holding_value` normalizza la base con `normalize_quote_base_quantity`, come il portafoglio: mai una divisione per 100.
- Il prezzo di riferimento è per `quote_base_quantity` unità, sia la quotazione sia il ripiego sul prezzo d'acquisto (`lots_analysis_service.py:1801-1811`).
- Nessun bump di versione del componente: stessa forma e stesso significato dichiarato («market value of the lot at its opening date»); il valore ora lo rispetta.
- Rosso in `backend/test_scripts/test_services/test_ai_export_components_asset.py`, con qbq=100 e qbq=1. Probe mirata se il DB popolato della corsia ha un asset con qbq≠1.

**B3a, disegno** (approvato il 2026-10-11, §10):
1. `_FxRateResolver` registra ogni conversione fallita in `convert()`: coppia e date.
2. Valutazione giornaliera: un prezzo senza cambio non vale più il prezzo nativo. Quel giorno il lotto non è valutato (`market_prices[d] = None`, nessun punto nel grafico del prezzo).
3. Storici del valore e del rendimento: niente punti per un lotto il cui costo d'origine (o i proceeds del corto) non si converte. Niente punti nemmeno dal giorno di una chiusura i cui proceeds non si convertono. È la regola delle linee del WAC.
4. Performance: un flusso esterno (BUY, ADJUSTMENT, SELL) non convertibile rende ROI e TWRR `None` da quella data (il meccanismo `invalid_external_flow_from` esiste già).
5. Sintesi del lotto: i campi derivati già Optional (valore, P&L, P&L di mercato, totale, rendimenti, rendimento annualizzato) diventano `None` quando un loro ingresso manca, mai calcolati dal nativo. Anche il ramo «stimato al costo» smette di valere 0 senza costo.
6. Rapporto: ogni coppia mancante va in `data_quality.missing_fx_pairs`, con le issue FX dello stesso costruttore delle linee del WAC (`build_data_quality_report`), unite senza doppioni. Lo stato diventa DEGRADED.
7. Restano a B3b, approssimati come oggi ma segnalati dal banner: i 4 campi base della sintesi, il `unit_price` del Gantt e gli importi degli eventi economici.

**B3b, disegno** (approvato il 2026-10-11, dopo il checkpoint):
- `LotSummarySchema.original_cost`, `opening_unit_price`, `realized_pnl`, `cumulative_proceeds` e `GanttSegmentSchema.unit_price` diventano facoltativi e si mostrano come «—».
- Gli eventi economici senza cambio sono trattenuti per lotto: reddito, costi e tasse a «—» sui lotti toccati (la regola di D-6).
- Comprende `api sync`, i 4 componenti dei lotti (UnifiedLotsTable, LotCustodyModal, LotWacPriceChart, LotGanttChart) e le righe dell'AI Export (`AssetLotDetailRow`, `payloads/portfolio_broker.py:685-693`).
- Una sola riga di CHANGELOG per B3a e B3b, scritta alla fine di B3b.
- Conflitti verificati dal coordinatore: I non tocca `schemas/portfolio.py`, l'AI Export né i componenti dei lotti.

**U — unificazioni**. Ognuna: rosso, regola nella casa, migrazione. I valori che cambiano si dichiarano prima.

| # | Cosa | Casa | Peso | Quando |
|---|---|---|---|---|
| U1 | un piano dei cambi unico, con mancanti e provenienza (X1–X9) | `fx_conversions.py` | medio | dopo la 1.2 (B3 prima, se D-6) |
| U2 | frazionamenti: caricamento, validazione di YoC come segnalazione, rapporto cumulato (S1–S3) | `splits.py` | medio-basso | dopo |
| U3 | quote di proprietà (O1–O4), con B9 dell'AI | `ownership.py` | basso nel servizio, medio nell'AI | O2 con F, il resto dopo |
| U4 | rendimenti: R1/R2 (ribasamento unico, via la riprova), R3, R5–R11, C1, C2 | `returns.py` (+ parità con `risk/metrics.py`) | medio | dopo; R1 eventualmente con F |
| U5 | prezzo del giorno e valorizzazione (V1–V5, V10) | `price_marks.py`, `valuation.py` | medio-alto: cambiano mark e staleness | dopo |
| U6 | finestre di detenzione dal FIFO (L1, L2), riusando il replay di YoC | `fifo/` | medio | con B4 |
| U7 | pesi e concentrazione (W1–W5) | `allocation.py` | medio | dopo |
| U8 | frontend di sola presentazione (R16, R17, W7, W8, P4, P5, V11, X12, G3): campi del backend, `api sync`, frontend | motore, lotti, API prezzi e FX | medio-alto | dopo |
| U9 | AI Export (C3, C4, V7, V8, R12–R14, W2–W4, Q1, Q2, P3), con la skill delle probe | case varie | medio | dopo |
| U10 | interessi e convenzioni di calendario (I1, I2) | `interest.py` | basso-medio | dopo |

### 7.2 Definizione di fatto (T-1)

- **Vecchi percorsi**: i moduli non esistono più; il grep dei vecchi percorsi puntati dà 0 in `backend/`, `scripts/`, `.github/`, `mkdocs_src/docs/developer/`. Il journal e le sezioni storiche della wiki restano come sono: un piano è una cronaca.
- **Suite**: backend intera verde sulla 6164, con gli **stessi conteggi** della base presa prima di T-1.
- **Statici**: `ruff check` e `black --check` puliti; `lint --dead-code` senza reperti nuovi; `api sync` senza differenze.
- **Doc**: `mkdocs build` stretto e `check-links` verdi; `check_source_paths.py` a 11.
- **Guardie e storia**: le guardie di T-1g verdi; `git diff -M` mostra le rinomine di A con somiglianza ≥ 95 %.
- **Corsia**: porta 6164 libera (`lsof -nP -iTCP:6164 -sTCP:LISTEN` vuoto); il piano aggiornato a ogni passo.

### 7.3 Test

- **Oracolo**: lo spostamento non cambia logica, quindi la suite intera è l'oracolo.
  - Per B, in più, un'istantanea JSON facoltativa sul DB popolato della 6164, prima e dopo, con hash uguali: `/portfolio/report`, storico, lotti, YoC, summary dei broker.
  - Lo script è usa-e-getta, in `/tmp`, mai committato.
- **Base**, presa prima di T-1 sulla base con F: `all-backend` coi conteggi; `lint`, `--dead-code`, `api sync`, `mkdocs build`, `check-links`, `check_source_paths.py`.
- **Mirati dopo ogni passo**, uno alla volta:
  1. `services financial-math`, `services roi-fifo-utils`, `services portfolio-engine`, `services lots-analysis-pure`, `services portfolio-allocation-source` (import pigro), `utils roi-utils`;
  2. `services ai-export`: solo import, quindi nessuna probe;
  3. `api portfolio`;
  4. `external brim-providers`, che costruisce il builder;
  5. poi `all-backend`.
- **Frontend**: nessun cambio in T-1. B1 si prova con vitest e `front check`.
- **Preambolo**: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6164 --data-dir /tmp/librefolio-r2-t <CATEGORIA> <AZIONE>`.

### 7.4 Conflitti previsti

| Chi | Superfici | Conflitto con T-1 | Gestione |
|---|---|---|---|
| I | engine, servizio del portafoglio, `financial_math/` (F), test dell'engine e del servizio, doc della dashboard e del capitale | totale, se in parallelo | T-1 dopo F. A si riapplica su una rinomina; B solo con I fermo |
| P | servizi delle transazioni, `TransactionBulkModal.svelte`, cataloghi i18n | nessuno: `transaction_service.py:959` è un commento su `average_cost`, che non si sposta | U8 (G3, C6) passa da P |
| M | doc e traduzioni | basso: T tocca solo pagine dev (EN, senza traduzioni) e una voce di nav; i percorsi delle pagine restano | nav: scrittore unico |
| Condivisi | runner (`_backend_services.py`, `_backend_utils.py`), `pyproject.toml`, `mkdocs.yml`, `.github/instructions/*`, devWiki | piccoli, testuali | lo scrittore lo assegna il coordinatore |
| Rami vecchi | qualsiasi ramo con base anteriore a T-1 che tocca engine, FIFO o lotti | A: la rinomina si riapplica; B: conflitto | B solo a finestra libera |

### 7.5 Rischi

- **Patch mute**: escluse se non ci sono shim; c'è la guardia sui vecchi percorsi.
- **Un import pigro dimenticato**: lo trovano il grep a zero, `python -c "import backend.app.main"` e la suite.
- **Un identificatore-contratto rinominato per errore** (`source_ref` del PAC, `Literal`, catalogo AI): sono elencati in §1.2 ed esclusi dalla sostituzione.
- **F sposta le righe** citate qui: i numeri di riga si riverificano sulla base con F.
- **Diff grande**: A rinomina ~6 600 righe. La revisione si fa con `git diff -M`.

### 7.6 Specialisti

- `test-author`: T-1f (riscrittura dei test puri dei lotti), T-1g (guardie), i rossi di B1–B4.
- `docs-writer`: T-1h (EN, sviluppatori).
- `project-historian`: la tabella della devWiki, se il coordinatore la assegna.
- Skill: `testing-backend`, `lint-format`, `ai-export-probe-tuning` (B2), `test-triage` se serve.

### 7.7 Cartella del piano

- `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md`. La scrivo dopo l'autorizzazione, da questo piano di sessione.
- La parte 2 genera più lotti: propongo una cartella sua, col numero assegnato dal coordinatore.

## 8. Decisioni del developer — ✅ approvate il 2026-10-11 come consigliato (§0.1)

| # | Domanda | Consiglio (approvato) |
|---|---|---|
| D-1 | `price_resolver.py` nella casa, come `price_marks.py`? | **Sì**: è la regola del mark, metà della valorizzazione; ne esistono 5 copie da unificare (U5) |
| D-2 | Tagliare i motori in sotto-pacchetti dentro T-1, o solo rinominarli? | **Tagliare**, in due commit; B solo a finestra libera |
| D-3 | I test: percorsi invariati in T-1 (solo import), o subito lo specchio dell'albero? | **Invariati**. Lo specchio nella parte 2: `_backend_services.py` codifica 163 percorsi |
| D-4 | Regola del layer: emendarla (§3.2) o separare subito i caricatori? | **Emendarla ora**; la separazione nella parte 2 |
| D-5 | PAC: prezzi e cambi dalla sua istantanea (V4, X9) o dalla casa? | **Gli helper comuni sì** (`oriented_rate`, `holding_value` generica); la scelta del dato resta del PAC, scritta come (c) |
| D-6 | Quali bug prima della 1.2? | **B1 e B2 sì** (piccoli, sicuri). **B3 sì**, se va bene che un lotto senza cambio mostri «—» col banner. **B4 dopo**, con U6 |
| D-7 | Finestra di detenzione dopo un trasferimento: data d'origine del lotto (FIFO) o arrivo al broker (mini-FIFO)? | **Data d'origine**: coerente col costo storico che il trasferimento porta con sé |
| D-8 | Convenzioni di calendario e interessi del provider SI in `financial_math/interest.py`? | **Sì**, dopo la 1.2 |
| D-9 | MeasureSignal annualizza sotto i 30 giorni: soglia della casa o una nota? | **Soglia della casa** (mostra «—»), coerente col backend |
| D-10 | Guardie: solo confini e vecchi percorsi, o anche rilevatori di copie a pattern (`quote_base`, `365` fuori casa)? | **Solo le prime due**: i pattern danno falsi positivi |
| D-11 | Un file d'istruzioni nuovo, `.github/instructions/financial-math.instructions.md`? | **Sì**. Lo scrive il coordinatore, o T su assegnazione |

## 9. Dove porta la stessa logica (ponte verso la parte 2)

Incontrati durante l'inventario; il dettaglio è in §P2:

- **`backend/app/utils/`**:
  - `sector_fin_utils`, `geo_utils`, `identifier_utils` sono del dominio asset;
  - `currency_utils` è del dominio FX;
  - `network_utils` è dell'API;
  - `decimal_utils` importa `db.models` (`:26`): non è una utility pura;
  - `cache_utils` costringe `fx.py` a 3 import pigri.
- **`services/`**: 40 file in cima, senza raggruppamento per dominio; `portfolio_service.py` ha 5 cuciture naturali (§P2).
- **Le famiglie di plugin**: segnali, rischio e tools non seguono lo schema di asset, FX e BRIM (§P2).
- **Il frontend**: `components/` ha 9 cartelle con più di 15 file; `lib/charts` e `lib/risk` raddoppiano `components/charts` e `components/risk` (§P2).

## P2. Code reordering, backend e frontend

> - **Natura**: analisi, nessun codice.
> - **Fonti**: 3 sottoagenti `explore` su `b20eac99` (famiglie di plugin; file grandi e `utils/` del backend; struttura del frontend), più verifiche mie (✔). Righe indicative.
> - **Chiusura**: quando una parte è applicata, la voce di `TODO_FUTURI.md` si cancella (lo fa il coordinatore).

### P2.0 Principi comuni (gli stessi della parte 1)

1. **Un dominio, una cartella**: nel backend un pacchetto di servizi per dominio (service layer). Nel frontend una cartella di feature (UI, stato, client, logica, test), come sono già `features/tools/pac-allocator/` e `features/ai-export/`.
2. **Un modulo, un problema**: i file sopra ~1 000 righe si tagliano lungo le cuciture che hanno già (sezioni, metodi pubblici).
3. **Prima la rinomina, poi il taglio**, in due commit (§4.2): la rinomina sopravvive ai rami vecchi, il taglio no.
4. **Niente shim né barili nuovi** per il codice spostato. Nel backend per le patch mute (§1.3); nel frontend perché `vi.mock` punta al percorso del modulo.
5. **Lotti piccoli e indipendenti**, ognuno coi suoi gate, mai su superfici di un workstream attivo.
6. **I contratti pubblici restano**: URL dell'API e `operationId`, chiavi i18n, `data-testid`, percorsi delle pagine MkDocs linkate dalle traduzioni.

### P2.1 Famiglie di plugin (backend)

**Stato di oggi**:

| Aspetto | Asset | FX | BRIM | Segnali | Rischio | Tools |
|---|---|---|---|---|---|---|
| Cartella dei plugin | `asset_source_providers/` (4 072 righe, 6 plugin) | `fx_providers/` (1 570, 6) | `brim_providers/` (15 246, 31, + `_brim_io`, `_brim_output`, `_scalable`) | `signal_plugins/` (5 141, 23) | `risk_plugins/` (3 474, 15) | `tool_plugins/` (206, 1) |
| Contratto (ABC) | `asset_sources/core.py:251` | `fx.py:52` | `brim_provider.py:118` | **dentro la cartella dei plugin**: `signal_plugins/base.py:62`, esclusa dalla scoperta (`provider_registry.py:333`) | `risk/base.py:169` | `tools/base.py:95` |
| Registro | `provider_registry.py:303` | `:297` | `:395` | `:309` | `:352` | **`tools/registry.py:169`**, con `register` e snapshot propri (`:191`, `:217-245`) |
| Decoratore | `register_provider` | idem | idem | `register_plugin` | idem | `register_plugin(ToolPluginRegistry)` |
| Parametri | `params_schema()` (`core.py:701`) | nessuno | nessuno | `params_model` → `params_schema` (`base.py:116`) | `params_model` → `parameters_schema` (`risk/base.py:202`) | `TypeAdapter` (`tools/base.py:87-93`) |
| Runtime | pacchetto `asset_sources/` (5 609) + shim `asset_source.py` (21) | monolite `fx.py` (1 679) | `brim_provider.py` (2 248) + 4 file `brim_*.py` | 4 file sparsi in cima a `services/` (`signal_service` 1 315, `signal_annotations` 441, `signal_series_preparation` 479, `signal_runtime` 45), più `series_preparation` (457), condiviso col rischio | pacchetto `risk/` (6 447) | pacchetto `tools/` (2 402) + motore `pac_allocator/` (11 079) |
| Router | `api/v1/assets.py` | `api/v1/fx.py` | `api/v1/brokers.py` | nessuno proprio: catalogo ed esecuzione stanno in `assets.py:740` e `fx.py:521-686`; `signals.py` ha 65 righe | `api/v1/risk.py` | `api/v1/tools.py` |
| Guida dei pattern | ✔ | ✔ | ✔ | ✔ | **manca** | ✔ (`tool_plugins.en.md`) |
| Skill / istruzioni | `asset-plugin` / `backend-providers-asset` | — / `backend-providers-fx` | `brim-plugin` / `backend-providers-brim` | — / solo il lato frontend (`frontend-signals`, aggiornata ✔) | — / — | `tool-plugin`, fuori da `*-tools/` / — |

**Differenze da sanare**:

1. Il contratto dei segnali sta nella cartella dei plugin.
2. Il runtime dei segnali non è un pacchetto.
3. **Dipendenza circolare fra rischio e segnali**: `risk/signal_helpers.py` importa `signal_plugins`, e `signal_plugins/{drawdown,rolling_return,rolling_beta}` importano `risk`.
4. Il registro dei tools sta fuori da `provider_registry.py`.
5. I parametri hanno quattro meccanismi; FX e BRIM nessuno.
6. `provider_registry.py:15-29` ri-esporta pigramente `SignalPlugin` e `RiskAnalytic`, con import pigri contro i cicli (`:339`, `:382`).
7. Al rischio mancano guida e skill, ai segnali la skill; la skill dei tools è fuori posto.

**Disposizione proposta**, una forma per tutte le famiglie:

```text
services/<famiglia>/                       runtime della famiglia (service layer)
    __init__.py                            solo docstring
    base.py                                contratto (ABC) e convenzione dei parametri
    registry.py                            il registro della famiglia (D-P1)
    service.py, <moduli per tema>          orchestrazione
services/<famiglia>_providers|_plugins/    un file per plugin; aiuti condivisi `_*.py`
```

| Famiglia | Runtime proposto | Plugin | Cosa cambia |
|---|---|---|---|
| Segnali | `services/signals/`, da: `signal_service.py` (diviso in piano, esecuzione, annotazioni, validazione), `signal_runtime.py`, `signal_annotations.py`, `signal_series_preparation.py`, `signal_plugins/base.py`, `risk/signal_helpers.py` | `signal_plugins/`, senza `base.py` | via il ciclo col rischio. La matematica comune di `signal_helpers` va in `financial_math/returns` (U4) |
| Rischio | `services/risk/` (esiste) | `risk_plugins/` | guida, skill e istruzioni; `signal_helpers.py` esce |
| Tools | `services/tools/` (esiste) | `tool_plugins/` | il registro segue D-P1; la skill va in `.github/skills/tool-tools/tool-plugin` |
| FX | `services/fx/`, da `fx.py` (`base`, `conversion`, `sync`, `storage`) | `fx_providers/` | solo il taglio del monolite |
| BRIM | `services/brim/`, da `brim_provider.py` (`base`, `storage`, `report_sets`, `parsing`, `candidates`, `duplicates`) + `brim_report_sets`, `brim_parse_pool`, `brim_gap_fix` | `brim_providers/` | il taglio, e le regole di segno condivise in `_brim_io` (G1) |
| Asset | `services/asset_sources/` (esiste); `base.py` da `core.py:251-701` | `asset_source_providers/` | via lo shim `asset_source.py` (13 importatori nell'app, 25 nei test) |
| PAC | resta `pac_allocator/`, il motore del tool | — | il taglio di `evaluator.py` è in P2.2 |

`series_preparation.py` (457 righe, condiviso): la matematica (rendimenti, fattore di annualizzazione) va in `financial_math/returns` (U4). L'allineamento delle serie resta un modulo proprio, `services/market_series.py` (nome da decidere).

**Lotti**:

| # | Cosa | Conteggi | Peso | Rischio | Quando |
|---|---|---|---|---|---|
| PL1 | runtime dei segnali in `services/signals/`; `base.py` fuori dai plugin; `signal_helpers` passa dal rischio ai segnali | ~10 importatori nell'app (router `assets`, `fx`, `signals`, AI Export, `price_query`, `main`), ~25 file di test; i 23 plugin importano `base` | medio | il ciclo rischio-segnali | dopo la 1.2 |
| PL2 | registri (D-P1) | `provider_registry.py` (104 importatori, quasi tutti per il decoratore, che resta dov'è) + 6 registri | medio | la scoperta dei plugin | dopo |
| PL3 | doc, skill e istruzioni di segnali, rischio e tools: nessun codice | 3 skill, 3 istruzioni, 2 pagine | basso | nessuno | prima della 1.2, possibile |
| PL4 | `fx.py` → `services/fx/` | 19 importatori nell'app, 10 nei test; `applyTo` di `backend-providers-fx` | medio | `convert_bulk` è usato ovunque: prima la rinomina | dopo |
| PL5 | `brim_provider.py` → `services/brim/` | 38 importatori nell'app (tutti i plugin), 14 nei test; stato di modulo (`_BROKER_LOCKS`, `:658-660`) | medio-alto | i lock condivisi fra le cuciture; i workstream BRIM | dopo |
| PL6 | asset: `base.py` e via lo shim | 13 nell'app, 25 nei test | medio-basso | — | dopo |
| PL7 | un router proprio per i segnali, con gli stessi URL | ~200 righe da `assets.py` e `fx.py` | medio-basso | gli `operationId` del client: va provato con `api sync` senza differenze | dopo |

### P2.2 File troppo grandi (backend, esclusa la parte 1)

| File | Righe | Importatori (app/test) | Cuciture | Proposta | Peso | Quando / chi |
|---|---|---|---|---|---|---|
| `pac_allocator/evaluator.py` | 3 754 | 6 / 9 | validazione 242-401; raggiungibilità 495-660; limiti 664-945; vincoli 946-1461; obiettivi 1462-1550; stato economico 1551-2335; fatti 2336-2865; politica 2866-3553; candidato 3554-3754 | `pac_allocator/evaluation/`, un modulo per tema; `_fx_rate` e `_to_valuation` dalla casa (U1, U5) | medio | dopo; dominio PAC |
| `portfolio_service.py` | 2 455 | 7 / 15 | facciata WAC 122-459; caricamenti 471-668; `get_summary` 669-1271; storici 1272-1710; contributi 1711-2104; `get_report` 2105-2455 | `services/portfolio/` (`wac_preview`, `loaders`, `summary`, `history`, `contribution`, `report`), dopo che la sua matematica è uscita (§6, U4) | medio | dopo F e T-1; file di I |
| `brim_provider.py` | 2 248 | 38 / 14 | contratto 118-638; file e lock 639-1330; report set 1331-1502; parsing 1503-1778; candidati 1779-2062; duplicati 2063-2248 | PL5 | medio-alto | dopo |
| `fx.py` | 1 679 | 19 / 10 | contratto 52-343; normalizzazione 344-400; sync 401-1239; conversione 1240-1436; salvataggio 1437-1679 | PL4 | medio | dopo |
| `portfolio_allocation_source.py` | 1 620 | 1 / 1 | caricamenti 45-143; provenienza 144-246; costruttori 385-882; FX e WAC 883-1280; distribuzione 1281-1435 | `pac_allocator/source/` | medio-basso | dopo |
| `risk/service.py` | 1 455 | 2 / 5 | esecuzione 135-349; ambito 449-650; replay 691-808; risultati 809-1115; qualità dei dati 1116-1450 | moduli in `risk/` | medio-basso | dopo |
| `signal_service.py` | 1 315 | 5 / 10 | piano 172-343; esecuzione 344-633; annotazioni 634-718; `_execute_planned_signal` 719-1076; validazione 1077-1305 | dentro PL1 | — | dopo |
| `transaction_service.py` + `transaction_batch_stages.py` | 1 066 + 1 065 | 5/7 e 1/0 | servizio: accessi, coppie, query, saldi, suggerimenti e promozione, batch e WAC. Stadi: parse, delete/split/update, create/promote, validazione del costo, saldi | `services/transactions/` | medio | dopo P (file di P) |
| `broker_service.py` | 1 000 | 3 / 4 | CRUD 81-362 e 568-794; summary 363-567; accessi 795-1000 | `services/brokers/` | basso | dopo |
| `asset_sources/price_store.py` | 1 020 | 2 / 1 | prezzi 55-472; cambio di valuta 473-628; eventi 629-1020 | 3 moduli | basso | dopo |
| `api/v1/assets.py`, `brokers.py`, `fx.py` | 1 229, 1 193, 1 091 | — | per risorsa: CRUD, provider, prezzi, eventi; accessi, file BRIM, parsing; tassi, conversione, rotte | sotto-router per risorsa, URL invariati | medio-basso | dopo |
| `schemas/pac_allocator.py`, `risk.py`, `portfolio.py`, `signals.py`, `transactions.py`, `assets.py` | da 2 522 a 1 000 | `schemas/__init__.py` è un hub di 698 righe | sezioni già marcate | pacchetti di schemi per dominio; l'hub può restare (gli schemi non si patchano) | medio | dopo |
| `db/models.py` | 1 149 | 100 / 83 | — | **non toccare**: troppi importatori, valore basso | — | — |

**`services/` in cima ha 40 voci.** Raggruppamento proposto per dominio. Lo producono i lotti sopra, non viene prima di loro:

- `assets/`: `asset_sources`, provider, `web_link_finder`, `market_calendar` (`price_resolver` va nella parte 1);
- `fx/`, `brim/`, `transactions/`, `portfolio/`, `signals/`, `risk/`;
- `tools/` + `pac_allocator/`;
- `ai_export/` (esiste);
- `accounts/`: `auth_service`, `user_service`, `settings_service`, `global_settings_service`, `onboarding_service`, `donation_popup_service`;
- `platform/`: `provider_registry`, `container_registry`, `scheduler/`, `date_sentinel`, `data_quality_thresholds`, `backup_service`;
- `files/`: `static_uploads`, `file_preview`.

### P2.3 `utils/` del backend

| Modulo | Righe | Importatori | Oggi | Proposta |
|---|---|---|---|---|
| `datetime_utils` | 112 | 41 | generico | resta |
| `json_utils` | 49 | 3 | generico | resta |
| `cache_utils` | 187 | 13 | generico, con stato di modulo; costringe `fx.py` a 3 import pigri (`:1218`, `:1533`, `:1674`) | `platform/cache.py`; i servizi registrano le proprie cache, e il ciclo sparisce |
| `decimal_utils` | 149 | 8 | importa `db.models` (`:26`): non è una utility pura | il troncamento va in `db/precision.py`; `parse_decimal_value` resta |
| `sector_fin_utils` | 146 | 7 | dominio asset | nel dominio asset |
| `geo_utils` | 210 | 6 | dominio asset, geografia | idem |
| `identifier_utils` | 59 | 3 | dominio asset | idem |
| `currency_utils` | 308 | 2 | dominio FX, API | `services/fx/` |
| `translation_utils` | 47 | 3 | interno a geo e currency | segue quei due |
| `network_utils` | 75 | 3 | HTTP, API | `api/` |
| `version` | 72 | 4 | infrastruttura, esegue git | `platform/version.py` |
| `financial/` | 538 | — | matematica | parte 1 (T-1a) |

- **Risultato**: in `utils/` restano solo `datetime_utils`, `json_utils` e un `decimal` puro.
- **Lotto BU1** (i moduli di dominio: sector, geo, identifier, currency, translation, network, version):
  - peso basso: al massimo 7 importatori per modulo;
  - i mock sulle loro variabili globali vanno verificati prima;
  - possibile prima della 1.2.
- **Lotto BU2** (`cache_utils` e `decimal_utils`, inversione delle dipendenze): medio-basso, dopo la 1.2.

### P2.4 Frontend

**Stato di oggi**:

- **9 cartelle di `lib/components/` hanno più di 15 file allo stesso livello**:

  | Cartella | File | Righe |
  |---|---|---|
  | `assets` | 55 | 18 829 |
  | `charts` | 53 | 21 006 |
  | `risk` | 44 | 21 546 |
  | `risk/levels` | 29 | — |
  | `dashboard` | 28 | 18 247 |
  | `brokers/lots` | 25 | 11 499 |
  | `ui/select` | 29 | — |
  | `settings` | 17 | — |
  | `transactions/modals` | 16 | 17 086 |

- **Case doppie**:
  - `lib/charts` (i segnali) e `components/charts`;
  - `lib/risk` e `components/risk`;
  - l'onboarding è diviso fra `features/onboarding` (logica) e `components/onboarding` (15 file di UI).
- **Logica di dominio in `lib/utils/`**:
  - `utils/transactions/*`: 27 file, usati solo dalle transazioni;
  - `utils/brim/*`, `utils/broker/*`;
  - `assetPriceDerived`, `assetSimilarity`, `assetGrouping`;
  - `urlFilters`: usato solo da files.
- **Inversioni di livello**:
  - `utils` e `stores` importano da `components` (transactions 4, risk 4);
  - `components/ui` importa da domini (assets 2, brokers 3, files 1, risk 1).
- **Lo schema buono esiste già**: `features/tools/pac-allocator/` (UI, stato `.svelte.ts`, client, logica, test; sotto-cartelle `result/`, `shared/`, `steps/`; componenti sotto le 300 righe) e `features/ai-export/`.
- **File enormi**: `ImportWizardModal.svelte` 5 956, `TransactionBulkModal.svelte` 3 741, `routes/(app)/assets/[id]/+page.svelte` 3 578, `GrowthChart.svelte` 2 583, `AssetModal.svelte` 2 510, `DataTable.svelte` 2 424 (870 righe di CSS), `TransactionFormModal.svelte` 2 192, e altri 20 sopra le 1 000.
- **Conteggi superati in `frontend.instructions.md:135-182`**:
  - charts: «14 file, ~5100», in realtà 53 file, 21k righe;
  - assets: «15, ~6300», in realtà 55 file, 18,8k righe.
- **Cosa non si rompe spostando file**: le chiavi i18n non codificano i percorsi; knip usa glob.

**Disposizione proposta**:

```text
frontend/src/lib/
├── components/        solo UI generica, senza dominio: ui/, table/, layout/, charts/ (primitive: LineChart, helper, aggregazione)
├── features/          un dominio = una cartella (UI + stato + client + logica + test)
│   ├── assets/        ← components/assets, assetPriceDerived, assetSimilarity, assetGrouping
│   ├── fx/            ← components/fx, stores/fx*, fxStoreRegistry, currency/fxConversionHelper
│   ├── transactions/  ← components/transactions, utils/transactions, utils/brim, stores/transactions
│   │   └── form/  bulk/  import/ (un componente per step del wizard)  wac/  events/  cells/
│   ├── brokers/       ← components/brokers (+ lots/), utils/broker, lotsAnalysisStore
│   ├── dashboard/     ← components/dashboard, dashboardViewStore, dateRangeController
│   ├── risk/          ← components/risk, lib/risk, stores/risk
│   ├── signals/       ← lib/charts/signals, signalCatalogStore, ChartSignalsSection
│   ├── files/         ← components/files, utils/files, stores/files, urlFilters
│   ├── settings/, auth/, support/
│   ├── onboarding/    ← features/onboarding + components/onboarding
│   └── ai-export/, tools/, changelog/, update-check/   (esistono)
├── stores/            solo stato globale: app/, core/, reference/
└── utils/             solo helper generici: core/, currency (formato), privacy/, dateOnly, storage, text, colors, sync/
```

**Regole**:
- i componenti generici non importano feature;
- `utils` e `stores` non importano componenti;
- una feature ne importa un'altra solo dal suo file pubblico (D-P4).

**Lotti** (indipendenti). Ognuno fa: `git mv`, import `$lib/...`, `svelte-check`, vitest, `front build`, gli E2E del dominio.

| # | Cosa | Import da cambiare | Peso | Conflitti | Quando |
|---|---|---|---|---|---|
| FE1 | onboarding unito in `features/onboarding/` | 16 | basso | il lotto 21 (onboarding), se attivo | prima della 1.2, possibile |
| FE2 | `features/signals/` (da `lib/charts/signals`) e `features/risk/` (da `lib/risk`, `components/risk`, `stores/risk`) | una parte dei 136 di charts, + 19 | medio | rischio | dopo |
| FE3 | `features/files/` | 8, + utils | basso | — | dopo |
| FE4 | `features/fx/` | 13, + store | basso | — | dopo |
| FE5 | `features/assets/`, col taglio di `AssetModal` e della pagina `assets/[id]` | 32 | medio | — | dopo |
| FE6 | `features/dashboard/`, con `GrowthChart` tagliato (1 300 righe di dati derivati → `.ts`) | 12 | medio | I (dashboard, waterfall) | dopo F |
| FE7 | `features/brokers/`, con `lots/` | 31 | medio | I (card) | dopo F |
| FE8 | `features/transactions/`: `ImportWizardModal` diviso in step, `TransactionBulkModal` e `TransactionFormModal` per sezione | 28 + 8 relativi + 27 utils | alto | **P** (proprietario) | dopo P |
| FE9 | `utils/` generici e inversioni di livello | — | medio-basso | — | dopo FE2–FE8 |
| FE10 | `stores/` solo globali | — | basso | — | insieme alle feature |
| FE11 | suffissi (Modal/Dialog, Panel/Section) | — | basso | — | per ultimo, facoltativo |

**Superfici d'impatto**:
- 186 test vitest accanto ai componenti, che si spostano con loro;
- gli harness in `src/__tests__`;
- 10 spec E2E che importano da `src/lib`;
- ~25 pagine `developer/frontend` (EN);
- la devWiki (molte pagine; i file generati di `graphify-out` si ignorano);
- le tabelle di `frontend.instructions.md`, da rifare.

### P2.5 Test, runner, doc (trasversale)

- **Test del backend**:
  - sono organizzati per livello (`test_api`, `test_services`, …), non per dominio, e `_backend_services.py` codifica 163 percorsi;
  - specchiare l'albero (lotto **TS1**) costa molto e rende poco;
  - lo propongo **dopo** tutti gli spostamenti, e solo se il developer lo vuole (D-P5).
- **`pyproject.toml:105`**: `testpaths = ["backend/tests"]` punta a una cartella che non esiste. Una riga in un file condiviso: lotto minimo.
- **Istruzioni `.github`**: quelle con `applyTo` su un file (es. `backend-providers-fx` su `fx.py`) si aggiornano nel lotto che sposta il file.

### P2.6 Ordine e quando

| Prima della 1.2 (consigliato) | Dopo la 1.2 |
|---|---|
| T-1 (parte 1), con B1 e B2 | U1–U10, B3 e B4 se non anticipati (D-6) |
| PL3 (solo doc, skill, istruzioni) | PL1, PL2, PL4–PL7 |
| BU1 (`utils` di dominio) | P2.2 (file grandi), BU2 |
| FE1 (onboarding), se nessuno lo tocca | FE2–FE11, TS1 |

Motivo: prima di un rilascio servono cambi che non spostano superfici usate da altri workstream. I tagli grandi portano conflitti e nessun valore per l'utente.

### P2.7 Decisioni del developer — ✅ approvate il 2026-10-11 come consigliato (§0.1)

> Prima della 1.2: **PL3 e BU1** (BU1 con l'elenco dei file al coordinatore prima di cominciare). FE1 aspetta la review C7 dell'onboarding (Q). Il resto, un lotto alla volta, passando dal coordinatore.

| # | Domanda | Consiglio (approvato) |
|---|---|---|
| D-P1 | Registri: tutti in `provider_registry.py`, o uno per famiglia, nel suo runtime? | **Uno per famiglia**, come fanno già i tools. `provider_registry` tiene le basi e i decoratori |
| D-P2 | Forma comune: runtime e plugin in cartelle sorelle (`<famiglia>/` + `<famiglia>_providers` o `_plugins`), o plugin dentro il runtime (`<famiglia>/plugins/`)? | **Cartelle sorelle**: è già la forma di asset, FX e BRIM, e sposta meno |
| D-P3 | `db/models.py` e l'hub `schemas/__init__.py`: dividerli? | **No** per i modelli. Gli schemi sì, per dominio, con l'hub che resta |
| D-P4 | Frontend: una feature importa le altre solo da un file pubblico (`index.ts`)? | **Sì**, ma senza barili per i moduli presi da `vi.mock`: lì si importa dal file che definisce |
| D-P5 | Test del backend specchiati sul codice? | **Dopo**, e solo se lo si vuole: costo alto, valore basso |
| D-P6 | Quali lotti prima della 1.2, oltre a T-1? | **PL3, BU1, FE1**, quest'ultimo solo se l'onboarding è libero |

## 10. Avanzamento

### T0 — Piano nel journal ✅ (2026-10-11)

> **Note implementazione**: questo file nasce dal piano di sessione dell'analisi (parti 1 e 2), con l'autorizzazione e le decisioni del 2026-10-11 (§0.1) e il disegno dei bug (§7.1). Base `b20eac99`, worktree pulita prima di cominciare.
>
> **⚠️ Fuori pista**:
> - **B3 era più grande della stima.** I ripieghi sull'importo non convertito nel servizio dei lotti non sono 6 ma ~20: valutazione giornaliera (`:401-404`), sintesi, Gantt, storici, proceeds, eventi economici (`_converted_external_amount`).
> - **Il «—» completo chiede un cambio di contratto**: alcuni campi oggi obbligatori dello schema dei lotti, `api sync`, il frontend, l'AI Export.
> - **Il coordinatore ha approvato la divisione**: B3a in questo checkpoint, B3b subito dopo (§7.1).
> - **`npm ci`** (approvato dal coordinatore): 433 pacchetti, dal lock esistente; `package.json` e il lock invariati. npm 11 non ha eseguito gli script d'installazione (esbuild, fsevents): da tenere d'occhio se vitest o la build si lamentano. Log `/tmp/libreFolio_t_npm_ci.log`.

### B1 — Δ% della coppia FX invertita ✅ (2026-10-11)

> **Note implementazione**:
> - **Helper unico** `displayFxDelta(firstRate, lastRate, inverted) → {abs, pct} | null` in `frontend/src/lib/stores/fxStoreRegistry.ts`, sui tassi mostrati.
> - **Ora lo usano tutte e quattro le copie**:
>   - la testata della coppia (`routes/(app)/fx/[pair]/+page.svelte`), dov'era il bug;
>   - `FxCard.svelte` e `FxTable.svelte`, già giuste;
>   - il Δ% di periodo della lista (`routes/(app)/fx/+page.svelte`, `computePeriodDelta`, già giusto; la scelta del punto di riferimento resta lì).
> - **Rosso**: prima la formula della pagina è passata nell'helper così com'era (`inverted ? −pct : pct`). Poi `test-author` ha aggiunto `describe('displayFxDelta')`, 12 test, in `src/lib/stores/__tests__/fxStoreRegistry.test.ts` (`:491-539`).
>   - Comando: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6164 --data-dir /tmp/librefolio-r2-t --log-file /tmp/libreFolio_t_red_b1.log front-fx fx-unit`.
>   - Esito: **3 failed, 134 passed, 1 skipped**; i 3 sono tutti sul Δ% invertito: −25 contro −20, −10 contro −9,09, 50 contro 100.
> - **Verde**: lo stesso comando dà **137 passed, 1 skipped** (lo skip c'era già prima). Log `/tmp/libreFolio_t_green_b1.log`.
> - **Statici**: `prettier --check` pulito sui 6 file; `dev.py front check` → **svelte-check 0 errori, 0 avvisi** (`/tmp/libreFolio_t_front_check_b1.log`).
> - **E2E FX non eseguiti**: nessuno spec controlla il valore del Δ, solo l'ordine delle colonne (`e2e/fx/fx-list.spec.ts:137`).
>
> **⚠️ Fuori pista**: in una worktree nuova `frontend/src/lib/api/generated.ts` non esiste (è in `.gitignore`), quindi vitest non carica `fxStoreRegistry.ts`. È servito `dev.py api sync`: nessun server, nessuna porta, uscite solo in file ignorati da git. Log `/tmp/libreFolio_t_api_sync.log`.

### B2 — AI Export F6, valore d'apertura del lotto con la `quote_base_quantity` ✅ (2026-10-11)

> **Note implementazione**:
> - **Correzione** in `backend/app/services/ai_export/components/asset_core.py`, `_build_lot_detail`: `opening_market_value = compute_holding_value(lot.original_quantity, lot.reference_unit_price, lots_response.quote_base_quantity)`. È la funzione del portafoglio, che normalizza con `normalize_quote_base_quantity`; nessuna divisione per 100, come chiesto dal developer.
> - **La base viene dalla risposta dei lotti**: è la scala con cui il servizio dei lotti ha prodotto quello stesso prezzo di riferimento, quindi prezzo e scala vengono da una fonte sola. Il fake del test la porta uguale ai metadati dell'asset.
> - **Commento F6 aggiornato. Nessun bump di versione** (`asset.lot_detail` resta v2): forma e significato dichiarato sono invariati.
> - **Rosso**: `test-author` ha aggiunto `TestLotDetail::test_opening_market_value_normalizes_the_per_quote_reference_by_quote_base_quantity` (`test_ai_export_components_asset.py:853-882`, parametro `quote_base_quantity` di `_lots_response` a `:271` e `:275`).
>   - Comando: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6164 --data-dir /tmp/librefolio-r2-t --log-file /tmp/libreFolio_t_red_b2.log services ai-export opening_market_value_normalizes`.
>   - Esito: **1 failed, 2 passed**. `[bond_quoted_per_100_nominal]`: `Decimal('98500.0') == Decimal('985')`; le guardie qbq=1 e «senza riferimento» erano verdi.
> - **Verde**: stesso comando → **3 passed** (`/tmp/libreFolio_t_green_b2.log`). `services ai-export` intero → **932 passed** (929 + 3; `/tmp/libreFolio_t_aiexport_b2.log`).
> - **Statici**: `ruff check` e `black --check` puliti su `asset_core.py` e sul file di test.
> - **Probe non eseguita: nessun qbq≠1 nei dati di test.** Prova: `dev.py test --test-port 6164 --data-dir /tmp/librefolio-r2-t db populate --force` → 17 asset, 0 con `quote_base_quantity ≠ 1` (`sqlite3 …/app.db`; log `/tmp/libreFolio_t_populate.log`). Le prove sono i test funzionali, come deciso dal coordinatore.
>
> **⚠️ Fuori pista**: `test-author` propone un caso in più, qbq=10. I due casi attuali non catturano un `/100` applicato solo quando qbq ≠ 1. Lo aggiunge insieme ai rossi di B3a.

### B3a — Lotti, niente ripiego sull'importo non convertito ✅ (2026-10-11)

> **Note implementazione** (`backend/app/services/lots_analysis_service.py`):
> - **Resolver**: `_FxRateResolver.convert()` registra ogni conversione mancata; `missing_pairs() → list[WACMissingPairInfo]`, una voce per coppia `FROM/TO` (lo stesso formato del costo medio), date ordinate.
> - **Valutazione giornaliera**: un prezzo senza cambio vale `None` (giorno non valutato, nessun punto nel grafico del prezzo), non più il nativo.
>   - Si valuta solo quello che serve: ogni giorno per gli storici (valore, rendimento, prezzo, performance), il solo ultimo giorno per la sintesi da sola, nessuno per il resto.
> - **Storici del valore e del rendimento**:
>   - helper comuni `_lot_value_basis()` e `_lot_snapshot_on_date()`, con le stesse espressioni di prima, quindi Decimal identici;
>   - `_LotValueBasis` (dataclass);
>   - `_closure_proceeds_prefix()` ora restituisce anche la data della prima chiusura senza cambio;
>   - tolta la copia doppia del ramo «senza prezzo».
> - **Performance**: un BUY, un ADJUSTMENT in entrata (`_adjustment_native_cost()` + `_adjustment_cash_flow_cost()`, ora stretto) o i proceeds di una SELL senza cambio rendono ROI e TWRR `None` da quella data (`invalid_external_flow_from`).
> - **Sintesi**: i campi derivati Optional sono `None` senza cambio (`_known_realized_pnl()`, `_known_cumulative_proceeds()`); niente più valore «stimato al costo» senza costo convertito.
> - **Rapporto**: `_report_gaps()` (prima `_report_average_cost_gaps()`) gira una volta, dopo tutti i costruttori.
>   - Unisce per coppia le lacune delle linee del WAC e `missing_pairs()`; DEGRADED se c'è una lacuna qualsiasi.
>   - Le righe degli eventi (`_build_lot_event_rows`) si costruiscono solo se CUSTODY_HISTORY o EVENT_HISTORY sono richiesti.
> - **Restano a B3b, segnalati**: i 4 campi obbligatori della sintesi, il `unit_price` del Gantt, gli eventi economici e i pesi dei trade (`_converted_external_amount()`).
>   - Verificato con un grep: nel file non ci sono altri ripieghi.
> - **Rossi** (`test-author`):
>   - 10 puri in `test_lots_analysis_pure.py`: resolver `:305-340`, performance `:964-1033`, sintesi `:1121-1146`, storici `:1294-1348`;
>   - 1 di servizio in `test_financial/test_lots_analysis_service.py:1769-1839`, con un asset in VND senza cambi né rotte;
>   - **10 failed, 106 passed** (puri) e **1 failed** (servizio), ognuno per il motivo giusto (es. `'COMPLETE' == 'DEGRADED'`, valori USD nativi presi per EUR);
>   - in più la guardia di B2 con qbq=10, verde per costruzione.
> - **Verde**, sulla 6164, un comando alla volta, dopo l'ultima modifica:
>   - `services lots-analysis-pure` **116 passed**;
>   - `services roi-fifo-utils` **584 passed**;
>   - `services ai-export` **933 passed**;
>   - `api portfolio` **51 passed**;
>   - log `/tmp/libreFolio_t_final_b3a_{pure,roi,aiexport,apiportfolio}.log`.
> - **Statici e porta**: `ruff check` e `black --check` puliti; `git diff --check` pulito; porta 6164 libera (`lsof` vuoto).
> - **Doc** (`docs-writer`, solo EN, pagine dev senza traduzioni):
>   - `developer/backend/transactions/lots_analysis_service.md`: stato, flusso, «No native fallback», l'avviso transitorio, la nota `net_metrics_status`, «Estimated-at-Cost», le linee del WAC, e un limite noto;
>   - `developer/frontend/data-quality-banner.md`: 2 righe;
>   - `mkdocs build` stretto e `check-links` verdi (95 validi, 0 rotti).
> - **E2E dei lotti non eseguiti**: i dati sintetici hanno i cambi, quindi nulla cambia lì; il contratto dell'API è invariato.
>
> **⚠️ Fuori pista**:
> - **Un test di P è diventato rosso** (`test_portfolio_cost_currency.py::TestLotsAverageCostLines::test_l2_…`): una data in più nel rapporto (03-08).
>   - Causa: `_build_lot_event_rows` girava anche senza richiesta (risultati scartati), con cambi mai caricati; anche la valutazione girava al giorno finale senza serie richieste.
>   - Il test era giusto. Ora si converte solo ciò che si restituisce, e il test è verde senza modifiche.
> - **C901**: `_build_return_history` è salito a 12 (soglia 10). Invece di un `noqa`, i due storici condividono gli helper: meno complessità e una copia in meno.
> - **Limite preesistente, trovato qui, fuori lotto**: `_close_position_piece()` (`fifo_lot_engine.py:905-940`) calcola P&L realizzato e proceeds col prezzo della vendita meno quello del lotto, senza conversione.
>   - Un lotto aperto in una valuta e chiuso da una vendita in un'altra mescola le due valute, e il servizio converte la chiusura con la valuta del lotto.
>   - Documentato nella pagina dev come limite noto. Proposto come voce di backlog (B5).
> - **Spunto per B3b**: `net_metrics_status = "UNAVAILABLE"` (oggi mai emesso) è già pensato per «a degraded economic pool», e la UI lo mostra già («netto non disponibile»). Trattenere per lotto gli eventi economici senza cambio può passare da lì, con meno campi da rendere Optional.

### Checkpoint B1–B3a ⏳ (2026-10-11)

> Consegnato al coordinatore FROZEN (messaggio del 2026-10-11): 13 file tracciati modificati + questo piano.
> - Commit e righe di CHANGELOG proposti nel messaggio.
> - Base `b20eac99`; il target è avanzato a `251067435` (treni 33–36) senza file in comune con questo delta.
