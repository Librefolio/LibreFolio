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
| R4 | `portfolio_service.py:1926-1976` | P&L di periodo della posizione, % su \|inizio\|, annualizzato con base di ripiego; per i chiusi P&L/costo impiegato | contributi | (b) | U5, con B8 di I |
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
| X5 ✔ | `portfolio_service.py:540-560` (`_convert_to_base`, una chiamata per importo) e `:1517-1567` (per transazione) | conversioni una a una | summary, storici di entrate, costi e depositi | (a) | F (i movimenti); U1/U5 (le 4 conversioni dei prezzi) |
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
| W1 | `portfolio_service.py:1028-1034` | % di allocazione su Σ valori, senza il valore in viaggio; peso sul NAV con denominatore 1 se NAV ≤ 0 | holdings | (a)/(b) | U7 |
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
| P1 | `portfolio_service.py:595-665` (`_compute_period_summary_metrics`); lo stato d'inizio periodo ripetuto in `:318-357` | P&L di periodo = NAV fine − NAV inizio − flussi | summary, report | (a) | U4 |
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
| B3b | Lotti, campi base, Gantt ed eventi economici a «—». Col cambio di contratto | medio-alto (riverificato) | 🚧 dal 2026-10-11 (treno 37 integrato) |
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

### Checkpoint B1–B3a ✅ (2026-10-11, treno 37)

> Consegnato al coordinatore FROZEN (messaggio del 2026-10-11): 13 file tracciati modificati + questo piano.
> - Commit e righe di CHANGELOG proposti nel messaggio.
> - Base `b20eac99`; il target è avanzato a `251067435` (treni 33–36) senza file in comune con questo delta.

> **Integrato nel treno 37**: `dev_release2` = `41ddc61cb`, commit `9fab65f4a`…`9bb2b0c16`, merge `bfd962b9c`. Il coordinatore ha accorciato il soggetto del commit del piano: `docs(journal): plan 43, financial math home`. Worktree riallineata a `41ddc61cb` in fast-forward (contiene H di I, P, M).

### Riconciliazione con l'analisi di F di I (coordinatore, 2026-10-11)

- **F chiude O2 e X5 sui giri del portafoglio**: G1–G4, cioè il passo 1 del motore, `get_summary`, i 3 storici e i contributi, più la card `:983`. Chiude anche B13 e B14 di I. U1 e U3 escludono quei siti.
- **B9 di I va in U3**, nella descrizione del developer:
  - nel patrimonio lo 0 di Viewer ed Editor è giusto (la Dashboard passa solo i broker propri con quota > 0);
  - il difetto è l'export dalla pagina di un broker solo visto: cifre del report piene, turnover moltiplicato per la quota grezza 0 (`broker_cost_efficiency.py:150-157`), più l'`abs` sul reddito (`portfolio_income.py:379`).
- **Restano a T**: L1/L2 (U6), R1 (U4, dopo la 1.2). C1 di I (`_wac_qualifying_txs`, il costo unitario dell'anteprima) lo colloco io: in U4, come già nel §7.1.
- **File**: F non tocca `schemas/portfolio.py`; riscrive `portfolio_engine.py` e `portfolio_service.py` e crea `financial_math/native_cash.py`. B3b, PL3, BU1 e FE1 non toccano questi file; uno spostamento di BU1 che tocca moduli importati dal motore o dal servizio va dopo F.
- **Indice dopo la 1.2** (`Phase_0/BACKLOG_POST_1.2.md`, sezione T): da ora le voci le scrivo io, nello stesso checkpoint.
- **Ordine**: B3b, PL3, BU1 (prima l'elenco dei file al coordinatore), FE1 (idem; P lavora su `TransactionBulkModal.svelte`, che importa da `$lib/features/onboarding/` `:89-91`), poi T-1 dopo F.

### B3b — Lotti, campi base, Gantt ed eventi economici a «—» ✅ (2026-10-11)

**Disegno**, approfondito sul codice il 2026-10-11 e mandato al coordinatore per il perimetro:
- **Campi base della sintesi.**
  - `original_cost` e `opening_unit_price` sono la conversione alla data d'apertura, oppure `None`.
  - `realized_pnl` e `cumulative_proceeds` vengono da `_known_realized_pnl()` / `_known_cumulative_proceeds()`, oppure sono `None`.
  - Spariscono `_converted_realized_pnl()` e `_converted_cumulative_proceeds()`.
- **Gantt**: `unit_price` è la conversione oppure `None`.
- **Eventi economici**, senza toccare il motore FIFO:
  - Un evento di reddito, di costo o di tassa senza cambio entra nel motore col suo importo nativo, solo come segnaposto per collocarlo. Il motore ne ricava la struttura dell'allocazione.
  - Il suo id va in `unconvertible_event_ids`.
  - I trade di BUY/SELL senza cambio passano `target_amount=None` (stesso peso di oggi, `_trade_target_value`) e finiscono in `unconvertible_trade_ids`.
- **Pool degradato** (un `EconomicAllocationGroup` del motore), in due casi:
  - le sue `source_transaction_ids` contengono un evento senza cambio;
  - è un pool di FEE/TAX pesato su trade (`SAME_DAY_TRADES`, `SAME_DAY_MIXED_TRADES`, `PREVIOUS_DAY_TRADES`), con un trade senza cambio e trade in valute diverse. Con trade tutti nella stessa valuta i rapporti nativi sono esatti e il pool non è degradato.
- **Cosa si trattiene** sui lotti di un pool degradato, dalla data del pool:
  - il reddito, i costi e le tasse della sintesi (`None`), con `net_metrics_status = "UNAVAILABLE"`: il disegno v4, che la UI mostra già;
  - negli storici `income`, `allocated_fees`, `allocated_taxes` e `net_pnl` del valore, e `income`, `total_return` e `net_total_return` del rendimento;
  - i derivati della sintesi (`total_pnl`, `cash_yield`, `net_*`, annualizzato).
- **Altri valori a `None`**:
  - l'`amount` dell'evento di reddito senza cambio;
  - gli orfani di un tipo, se un pool degradato di quel tipo è orfano;
  - nell'audit di un pool degradato, `target_pool_total`, `target_orphan` e il `target_amount` per lotto (le cifre native restano, sono giuste).
- **Il segnaposto nativo non arriva mai alla risposta**: ogni uscita di un pool degradato è trattenuta.
- **Schemi** (`schemas/portfolio.py`, solo la sezione dei lotti), campi che diventano Optional:
  - `LotSummarySchema`: i 4 campi base, più asset_income, allocated_fees e allocated_taxes;
  - `GanttSegmentSchema.unit_price`;
  - `LotValueHistoryPoint`: income, allocated_fees, allocated_taxes, net_pnl;
  - `LotReturnHistoryPoint`: income;
  - `LotIncomeEventSchema`: amount;
  - `EconomicAllocationGroupSchema`: target_pool_total, target_orphan; `EconomicLotAllocationSchema`: target_amount;
  - `LotsAnalysisResponse`: asset_orphan_*.
- **Poi**: `api sync`; i 6 componenti dei lotti (UnifiedLotsTable, LotCustodyModal, LotWacPriceChart, LotGanttChart, LotComparisonChart, LotsAnalysisPanel).
- **AI Export**: `AssetLotDetailRow`, `FifoLotRow` (con `residual_cost_basis`) e `summarize_fifo_asset_rows`, dove una somma con una parte ignota diventa `None`. Le versioni dei componenti le decide il coordinatore (opzione A, bump più la mappa compatta; opzione B, nessun bump).

**Perimetro approvato dal coordinatore** (2026-10-11, opzione A, su delega del developer): i campi Optional solo nella sezione dei lotti; i 6 componenti; nell'AI Export `AssetLotDetailRow`, `FifoLotRow` e `summarize_fifo_asset_rows`, con i bump `asset.lot_detail` 2→3 e `fifo_lots` 1→2 (`fifo_summary` solo se cambia forma); in `snapshotDataRenderer.ts` solo le voci di `COMPACT_COMPONENT_VERSIONS` più il loro test.

#### Passo 1 — backend dei lotti ✅ (2026-10-11)
> **Note implementazione**:
> - **Schemi**: 22 campi Optional nella sezione dei lotti di `schemas/portfolio.py`. Il `weight` del lotto resta obbligatorio: è un rapporto di quantità, sempre noto.
> - **Servizio**:
>   - `_WithheldEconomics` raccoglie, per lotto, la data da cui reddito, costi e tasse sono ignoti, più gli indici dei pool degradati, gli eventi senza cambio e gli orfani ignoti; `reaches(lot_id)` decide `net_metrics_status = "UNAVAILABLE"`.
>   - Funzioni nuove: `_unconvertible_ids()`, `_withheld_economics()`, `_economics_on_date()`, `_lot_returns()`, `_known_prefix_on_date()`.
>   - `_converted_external_amount()` diventa `_engine_target_amount()`: il nome dice che l'importo nativo è solo il segnaposto per il motore.
>   - Spariscono `_converted_realized_pnl()` e `_converted_cumulative_proceeds()`.
>   - Gli storici del valore e del rendimento prendono `withheld=` e usano, a ogni data, solo i pool già noti.
> - **Test** (test-author): 4 rossi in `test_lots_analysis_pure.py` e 9 in `test_financial/test_lots_analysis_service.py`, più una guardia; i 3 test di `_converted_cumulative_proceeds` migrati a `_known_cumulative_proceeds`.
> - **Evidenze**:
>   - `services lots-analysis-pure` → 121 passed;
>   - `services roi-fifo-utils` → 599 passed;
>   - ruff e black puliti.
>
> **⚠️ Fuori pista**:
> - Il disegno diceva «nell'audit di un pool degradato restano le cifre native». Vale per il pool con un evento senza cambio.
> - Non vale per il pool di FEE/TAX diviso su trade in valute diverse. Lì il motore pesa con l'importo nativo del trade senza cambio, quindi sono sbagliati il peso dell'operazione e l'importo nativo per lotto. Anche questi sono `None`.
> - Il totale nativo del pool e il peso per lotto dentro l'operazione restano: sono giusti.

#### Scoperte sul renderer dell'AI Export (2026-10-11, mandate al coordinatore)
- **`asset.lot_detail` è in `PAYLOAD YAML FALLBACK` dalla v1.1.0.**
  - F6 (`3e3f9c41f`) l'ha portato a v2, ma il renderer della v1.1.0 accettava solo `component_version === 1`.
  - `COMPACT_COMPONENT_VERSIONS` oggi conosce solo le due provenance.
  - Domanda al coordinatore: con v3, compatto o YAML?
- **Nelle tabelle compatte `null` resta il testo `null`** (`null=explicitly unavailable` nel preambolo), non una cella vuota. Una colonna sparisce solo se è `null` in tutte le righe.
- **`fifo_summary` cambia forma**: 7 campi della riga Asset e `total_residual_cost_basis` diventano nullable. Quindi va a v2 anche lui (portfolio e broker).

**Decisioni del coordinatore sulle tre scoperte** (2026-10-11, «Tutti e tre sì»):
1. **`asset.lot_detail` v3 compatto**, nella mappa, con lo stesso renderer generico di `fifo_lots`.
   - Il motivo: il YAML è la riserva per le versioni sconosciute. Esserci rimasti dalla v2 di F6 è stata una regressione silenziosa, non una scelta.
   - Va fatta una sonda mirata sulla corsia 6164: un Asset con lotti, solo dati sintetici.
   - Nel checkpoint servono il prima e il dopo del blocco lotti nel prompt dell'Asset: forma, lunghezza, nessun dato perso.
   - Il CHANGELOG dice che il dettaglio dei lotti torna una tabella compatta, mentre dalla 1.1.0 usciva in un blocco YAML più lungo.
2. **Nelle tabelle compatte un valore ignoto è il testo `null`**: il test prova `null`, mai `0` e mai YAML.
3. **`fifo_summary` va a v2**, portfolio e broker, con {1,2} nella mappa.

**Una quarta decisione del coordinatore** (2026-10-11, «Sì al contatore, adesso»):
- `unavailable_amount_lot_count` va in `asset.lot_detail` v3 e nei due `fifo_lots` v2, come riga della SUMMARY sempre visibile, anche a 0. Il motivo è la regola dei prompt: dichiarare cosa è parziale o non disponibile, mai lasciarlo implicito.
- La sonda mirata deve mostrare un caso con valore > 0: un Asset in VND senza cambi, sui dati sintetici della 6164.
- La regola esistente delle colonne nulle in tutte le righe si descrive nella doc developer, insieme al contatore.
- La regola generale (segnalare le colonne tolte in tutti i componenti) va dopo la 1.2: riga T-B7 dell'indice.

#### Passo 2 — AI Export ✅ (2026-10-11)
> **Note implementazione**:
> - **Righe**: in `AssetLotDetailRow` diventano nullable 7 campi, in `FifoLotRow` 8 (con `residual_cost_basis`), in `FifoAssetSummaryRow` 7.
> - **`lot_residual_cost_basis()`**: è `None` quando il lotto è aperto e il costo è ignoto. Il costo si controlla prima della quantità originale a zero.
> - **`summarize_fifo_asset_rows()`**:
>   - le 7 somme del costo sono complete oppure `None`;
>   - la valuta si prende da ogni importo noto: un lotto può avere ignoti tutti i costi e noto il valore di mercato;
>   - nuova `total_fifo_residual_cost_basis()`.
> - **Versioni**: `asset.lot_detail` 3, i quattro `fifo_lots`/`fifo_summary` 2, nelle spec reali e nei segnaposto del catalogo.
> - **Contatore**: `unavailable_amount_lot_count` è obbligatorio e ≥ 0.
>   - Lo calcolano `count_unavailable_amount_lots()` (FIFO) e `_has_unavailable_amount()` (`asset_core.py`).
>   - Conta solo i campi che B3b rende nulli. Quelli già opzionali prima (valore di mercato, P&L di mercato, riferimento d'apertura) hanno la loro copertura.
> - **Test** (test-author): 26 rossi, poi 36 rossi del contatore e 3 fissaggi. `services ai-export` → **999 passed**.
>
> **⚠️ Fuori pista**:
> - Il C901 di `summarize_fifo_asset_rows` è salito a 12. L'ho riportato sotto 10 con quattro helper di modulo (`_fifo_rows_currency`, `_fifo_value_coverage_status`, `_sum_complete_amounts`, `_sum_known_amounts`), senza `noqa`.
> - Ruff ha chiesto di riordinare gli import (I001) e `__all__` (RUF022).

#### Passo 3 — frontend dei lotti ✅ (2026-10-11)
> **Note implementazione**:
> - **`api sync`**. Il generatore trasformava `Optional[SafeDecimal] = Field(default=0)` in `.default(0)`, un numero su un'unione di stringhe: 12 errori di svelte-check in `generated.ts`. Il default è ora `Decimal("0")`.
> - **Helper con test**:
>   - `isUnknownOrNonZero()` e `addOrNull()` in `lotChartShared.ts`;
>   - `parseValueSeriesPoint()`, `pnlWithIncome()`, `comprehensiveValue()`, `aggregateValuePoints()` e `aggregateReturnPoints()` in `lotComparisonChartHelpers.ts`, tolti dal componente;
>   - `sumCompleteOrNull()` e `weightedAverageCompleteOrNull()` in `unifiedLotsTableHelpers.ts`;
>   - `isSplitTransition()` e `inferredTransitionKind()` accettano un prezzo ignoto.
> - **Componenti**:
>   - `UnifiedLotsTable`: tutti i totali e le due medie del piede sono «—» appena un lotto è ignoto, anche il valore corrente, per coerenza; le colonne restano visibili se un valore è ignoto.
>   - `LotCustodyModal`: le righe di reddito e costi restano visibili con «—».
>   - `LotGanttChart`: prezzo del segmento nullable; tooltip con «—»; il «P&L totale» non ripiega più su `pnl`, che è senza reddito.
>   - `LotComparisonChart`: le linee si fermano dove il valore diventa ignoto, e la ritenuta dura fino in fondo, quindi non ci sono buchi a metà; un marcatore di reddito senza altezza nota non si disegna; l'importo dell'evento è «—».
>   - `LotWacPriceChart`: bolle con importi nullable, tooltip «—».
>   - `LotsAnalysisPanel`: il tipo dell'importo.
> - **Test** (test-author): 46 + 7 + 4 vitest.
> - **Evidenze**:
>   - i 9 file dei lotti → 467 passed;
>   - la suite vitest intera → **347 file, 10 328 passed**;
>   - `front check` → 0 errori;
>   - Prettier pulito.
>
> **⚠️ Fuori pista**:
> - Il Gantt riconosce uno split dal nozionale, cioè quantità × prezzo. Con un prezzo ignoto non lo riconosce più.
> - Però quello è solo il ripiego per un grafico senza eventi: la pagina dei lotti passa `lot_events`, con il SPLIT del backend. Il caso è fissato da un test.

#### Passo 4 — renderer dell'AI Export ✅ (2026-10-11)
> **Note implementazione**:
> - `COMPACT_COMPONENT_VERSIONS`: `asset.lot_detail` → {1, 2, 3}; `portfolio/broker.fifo_lots` e `.fifo_summary` → {1, 2}. Nient'altro nel file.
> - **Test** (test-author): 12 rossi, poi 9 per la riga del contatore, che non chiede modifiche al renderer.
>   - Una colonna nulla in ogni riga sparisce, e il test la fissa come regola esistente.
>   - Il contatore resta nella SUMMARY.
> - `snapshotDataRenderer.test.ts` → **65 passed**; i 12 file dell'AI Export → 142 passed.

#### Passo 5 — sonda mirata ✅ (2026-10-11)
> **Note implementazione**:
> - **Dati**: `test db populate --force --clean` sulla corsia; poi un Asset in VND senza cambi (asset 18, broker 1) con due acquisti, una vendita parziale e un dividendo, inseriti come nei test di servizio.
> - **Sonda**: quella ufficiale (`ai_export_real_prompt_probe.py`), lanciata da un involucro temporaneo fuori dal repo.
>   - L'involucro cambia solo l'alias dell'utente (`e2e_test_user`) e l'Asset dell'ambito: la CLI non sa scegliere né l'uno né l'altro.
>   - Il resto è il percorso ufficiale: DB copiato, HTTP, costruttore della richiesta e renderer del frontend, hash e scansione dei segreti.
>   - Selezione: `asset.position_and_history`, 1Y, full, porta 6164.
> - **Esito della sonda**: snapshot HTTP 200, sorgente invariata, scansione dei segreti passata, porta libera.
>   - Lo stato della sonda è però «1 fallimento» per ciascun caso: il controllo pubblico `raw_ratio_weight_name` trova `portfolio_weight_ratio` nella tabella `portfolio_role.unavailable` di `asset.position_scope`.
>   - È preesistente (`ea0558b3c`), non è B3b, ed è segnalato al coordinatore.
> - **Prima e dopo del blocco lotti**, renderer ufficiale caricato come lo carica la sonda.
>   - Il «dopo» coincide byte per byte col blocco del prompt salvato dalla sonda.
>   - Il «prima» è il percorso della versione sconosciuta (YAML), lo stesso che prendeva la v2 a HEAD: il renderer di HEAD differisce solo nella mappa, e l'intestazione del blocco non porta la versione.
> - **Apple** (10 lotti, contatore 0):
>   - dopo: 3 094 caratteri, 22 righe, ~774 token;
>   - prima: 11 126 caratteri, 312 righe, ~2 782 token;
>   - quindi **−72%**;
>   - 230 celle verificate, 0 differenze, e nessun dato perso: l'unica colonna tolta è `closing_date`, nulla in tutti i lotti;
>   - il YAML esponeva 30 id grezzi di broker.
> - **VND** (2 lotti, **contatore 2**):
>   - dopo: 930 caratteri;
>   - 11 colonne nulle ovunque sono tolte (costo, prezzo d'apertura, reddito, valore, P&L…), e il contatore ne è la traccia;
>   - realizzato e incassi mostrano `null` (L1, venduto senza cambio) accanto a `0` (L2);
>   - entrambi i lotti sono `UNAVAILABLE`.
> - Le prove sono nella cartella della sessione (`files/b3b_probe/`), fuori dal repo.
>
> **⚠️ Fuori pista**:
> - Il primo Asset scelto dalla sonda (Bitcoin, asset 6) dava 503 su `asset.identity`: i dati sintetici scrivono la vecchia forma di `classification_params` (`populate_mock_data.py:793-881`), che `FAClassificationParams` rifiuta. È preesistente ed è segnalato al coordinatore.
> - `--base-url` vuol dire «server già avviato»; senza, la sonda avvia il suo.
> - `asset.position_performance` non è pubblico, quindi ho usato `asset.position_and_history`.

#### Passo 6 — documentazione e due buchi trovati dal docs-writer ✅ (2026-10-11)
> **Note implementazione**:
> - **Doc developer** (docs-writer, solo inglese):
>   - `lots_analysis_service.md`: tolto l'avviso «Transitional native fallback»; nuova sezione «Economic events and degraded pools»; la nota su `net_metrics_status` dice che `UNAVAILABLE` ora si emette.
>   - `lots-analysis.md`: la visibilità delle colonne nette e il dettaglio del modale; i 5 `data-testid` mancanti del modale.
>   - `ai_export_composition.md`: nuova sezione «Snapshot Data Tables», con `null` letterale, la regola delle colonne nulle in ogni riga, la SUMMARY e il contatore.
>   - `ai_export_probe_workflow.md`: le diagnostiche delle colonne tolte.
>   - `mkdocs build` (strict) e `check-links` (95) passano.
>
> **⚠️ Fuori pista**: rileggendo il codice, il docs-writer ha trovato due buchi, chiusi in B3b con il rosso prima.
> - **Il segnaposto nativo usciva dal `data_quality`.** Un pool orfano con un evento senza cambio dava al suo avviso (`ASSET_INCOME/COST_NO_ELIGIBLE_LOTS`) l'importo nativo nella valuta di destinazione: il banner avrebbe letto «70 EUR» per 70 VND.
>   - Ora `_orphan_issue_params()` dà il pool nella sua valuta («70 VND»); i nomi delle chiavi restano `target_`.
>   - Test: 3 rossi (dividendo, FEE, TAX) e 3 controlli convertiti.
> - **`total_pnl` e `net_total_pnl` della sintesi FIFO erano somme parziali senza copertura.** Ora sono `None` appena manca una parte.
>   - Il valore aperto, il P&L non realizzato e il potenziale restano parziali, perché la loro copertura è dichiarata.
>   - Una differenza di insiemi fra queste due somme va dopo la 1.2 (T-B8).
>   - Test: 2 rossi più un controllo.
> - **`api portfolio`: `test_target_currency_conversion` codificava il ripiego nativo**, con un'asserzione tautologica.
>   - Il test-author l'ha riscritto sul contratto B3b: legge il caso dai `missing_fx_pairs` della risposta stessa e lo verifica in modo stretto.
>   - Ha provato anche il ramo «con cambio» una volta, con una riga di cambio propria, poi cancellata.

#### Gate finali (2026-10-11)
> - `services lots-analysis-pure` → 121 passed.
> - `services roi-fifo-utils` → **611 passed**.
> - `services ai-export` → **1002 passed**.
> - `api portfolio` → 51 passed.
> - `api ai-export` → 15 passed.
> - `front-broker detail` (E2E) → 35 passed.
> - `front-portfolio privacy-masking` (E2E) → 18 passed.
> - vitest: i lotti e l'AI Export → 21 file, 609 passed; la suite intera, prima dei due ultimi fix (solo backend) → 347 file, 10 328 passed.
> - `front check` → 0 errori. Ruff, black e Prettier puliti. `git diff --check` pulito.
> - La porta 6164 è libera dopo ogni comando.
> - Non eseguito: la suite E2E intera e `--workers 4`.

### Checkpoint B3b 🧊 (2026-10-11) — FROZEN, in attesa del coordinatore
- **Cinque commit proposti** (soggetti ≤ 50): `fix(lots): withhold pools without a rate`, `fix(lots): show unknown lot amounts as a dash`, `fix(ai-export): null lot amounts, compact lots`, `docs: lots withholding, AI Export null columns`, `docs(journal): plan 43 B3b, T post-1.2 index`.
- **CHANGELOG**: due righe in 1.2.0 «Fixed», entrambe «Present since v1.1.0»: B3 per i lotti, e il dettaglio dei lotti compatto dell'AI Export. Le scrive il coordinatore nel CL del treno, copiate parola per parola.
  > **⚠️ Fuori pista**: `CHANGELOG.md` è un file condiviso con un solo scrittore, il coordinatore. L'avevo modificato io: riportato al contenuto di `HEAD`. D'ora in poi le righe del CHANGELOG vanno nel messaggio di handoff, mai nel file.
- **Dopo la 1.2**: le righe sono nella sezione T dell'indice, scritte da T (T-B6, T-B7, T-B8 nuove; U1 e U8 estese).
- **Segnalate al coordinatore, per altre aree**:
  - `asset.position_scope` espone `portfolio_weight_ratio`;
  - i dati sintetici scrivono la vecchia forma di `classification_params`;
  - la CLI della sonda non sceglie l'Asset né l'utente sintetico.
- **Prossimo**: PL3, poi BU1 e FE1, ciascuno con l'elenco dei file prima di scrivere codice, poi T-1 dopo F.

### Treno 38 e decisioni dopo B3b (coordinatore, 2026-10-11)
- **B3b** è nel batch 36, treno 38: `dev_release2` = `b578f4fec`, i commit da `59a7c3e2f` a `7269f4085`, il merge `0e44fa787`. Il developer ha approvato le decisioni di B3b prese dal coordinatore al suo posto (opzione A col bump, `lot_detail` compatto, il contatore).
- **BU1: opzione A**, niente prima della 1.2. Il motivo è lo strato: `schemas/` non importa mai `services/`, e `db/models.py` importa solo `utils/`; `sector_fin_utils`, `geo_utils` e `identifier_utils` sono importati da `schemas/assets.py:58-60` e `db/models.py:36`. `currency_utils` aspetta `services/fx/` (PL4, dopo F). BU1 si unisce a BU2 dopo la 1.2, in attesa di **D-P7**: aiuti puri di dominio in `backend/app/domain/` senza I/O, oppure in `utils/` con la regola scritta. La riga è nell'indice, sezione T.
- **PL3, file condivisi assegnati**: `backend.instructions.md`, le righe della tabella `:32-37`. Niente `risk_plugin_guide.md` e niente `mkdocs.yml`: la guida del rischio esiste già in `risk/architecture.md` (`#plugin-contract`, `#adding-an-analytic`).
- **FE1, file condivisi assegnati**: `routes/(app)/+layout.svelte` (4 import), `scripts/test_runner/_frontend_utility.py:325-330`.
- **Ordine**: PL3, poi FE1, con un checkpoint solo se restano piccoli; T-1 dopo F.

### PL3 — doc, skill e istruzioni di segnali, rischio e tools ✅ (2026-10-11)
> **Note implementazione**:
> - **Skill nuove**, sul modello in cinque sezioni di `asset-plugin`:
>   - `.github/skills/signal-tools/signal-plugin/SKILL.md`;
>   - `.github/skills/risk-tools/risk-plugin/SKILL.md`, che rimanda alle sezioni di `risk/architecture.md`.
> - **Skill spostata**: `tool-plugin` passa in `.github/skills/tool-tools/tool-plugin/SKILL.md`. Il corpo è identico; solo la description è fra virgolette, come le altre.
> - **Istruzioni nuove** (`applyTo` e file coperti, contati sul repo):
>   - `backend-signals.instructions.md`: `services/signal_plugins/**`, `services/signal_*.py`, `services/series_preparation.py` → 30 file;
>   - `backend-risk.instructions.md`: `services/risk/**`, `services/risk_plugins/**`, `services/series_preparation.py` → 47 file;
>   - `backend-tools.instructions.md`: `services/tools/**`, `services/tool_plugins/**` → 13 file.
>   - Ognuna dice l'architettura, le regole del contratto e del dato, dove si aggiunge un plugin e i test. Tutte ripetono la regola della casa unica: la matematica comune da `financial_math/` e dalla mappa di `backend.instructions.md`.
> - **`backend.instructions.md`**: tre righe nella tabella delle istruzioni (Technical Signals, Risk Engine, Tool Platform).
> - **`registry_pattern.md`**: la riga del rischio nella tabella delle guide (docs-writer).
> - Nessun controllo del repo valida skill o istruzioni; i nomi citati sono verificati sul codice (simboli, azioni del runner).
> - **`registry_pattern.md`** (docs-writer): la riga **Risk** tra Signals e Tools, verso `../../backend/risk/architecture.md#adding-an-analytic`; tolta la frase sotto la tabella. `mkdocs build` (strict, ancore controllate) e `check-links` (95) passano.
> - **Note del docs-writer, lasciate a PL2** (i registri):
>   - la docstring di `get_plugin_diagnostics` dice «all plugin registries» ma non copre il rischio;
>   - `RiskAnalyticRegistry` manca dall'`__all__` di `provider_registry.py`;
>   - nella pagina, «every later lookup raises» tace che anche la lookup che avvia la scoperta solleva l'errore.

### FE1 — l'onboarding unito in `features/onboarding/` ✅ (2026-10-11)
> **Note implementazione**:
> - **Spostati**: i 15 file di `lib/components/onboarding/` (9 `.svelte` e 6 test) in `lib/features/onboarding/components/`, come `features/tools/components/`. Gli spostamenti sono fatti con `mv`, senza `git mv` né stage. Nessun import `../` dentro i file spostati, e nessuna collisione.
> - **Import**:
>   - 7 righe: `routes/(app)/+layout.svelte:23-26` (assegnato), `routes/+page.svelte:15`, `routes/(app)/welcome/+page.svelte:8`, `components/settings/tabs/PreferencesTab.svelte:19`;
>   - 9 `vi.mock`: `PreferencesTab.test.ts:150`, `layout.authGate.test.ts:120-123`, `layout.gate.test.ts:116-119`;
>   - la stringa di `features/onboarding/guideCopy.test.ts:63`.
>   - Invariati: la logica e gli alias `$lib/features/onboarding/...`, compresi quelli di P in `TransactionBulkModal.svelte:89-91`.
> - **Runner**: `_frontend_utility.py:325-330` (il comando `vitest run`, assegnato).
> - **Skill**: `.github/skills/onboarding-tools/onboarding-guide/SKILL.md:78`.
> - **Evidenze**:
>   - `front check` → 0 errori;
>   - vitest (onboarding, layout, Preferences, store) → 14 file, 498 passed;
>   - E2E `front-utility onboarding-tour` → 10 passed, `onboarding-guides` → 24 passed;
>   - Prettier pulito.
>
> **⚠️ Fuori pista**: `_frontend_utility.py` ha una seconda copia dei 6 percorsi alle `:593-598`, la tupla `tests=(...)` della registrazione `onboarding-component-unit` che legge `check-orphans`; l'inventario l'aveva mancata.
> - Il coordinatore ha esteso l'assegnazione e io ho cambiato i percorsi.
> - `check-orphans` è pulito: 347 test unitari registrati e raggiungibili da `all`.
> - `front-utility onboarding-component-unit` → 15 file, 429 passed.
>
> **Doc** (docs-writer, con un secondo tentativo perché il primo è caduto per la rete): `developer/frontend/onboarding.md:92-95` e `:501`, `components/features/settings.md:70`. `mkdocs build` (strict) e `check-links` (95) passano.
> **Nota, fuori dal lotto**: l'albero «Directory Structure» di `developer/frontend/index.md` non ha `lib/features/`: un buco già presente, da sistemare con FE2–FE11.

### Etichette di durata (trovate da M, assegnate dal coordinatore, 2026-10-11) ✅
- **Cosa**: tre punti scrivono le durate in inglese nel codice:
  - il periodo dell'AI Export, `features/ai-export/ui.ts:60-63` (`'3M'`, `'6M'`, `'1Y'`);
  - le colonne Δ di `AssetTable.svelte` e `FxTable.svelte`: le dinamiche `Δ ${period.key}` e la fissa `'Δ 1D'`.
- **Come**: con le chiavi `datePicker.presets.{days,weeks,months,years}` (`{n}`), come il picker e la finestra mobile di P. Un helper puro, `deltaPeriodLabel(key, t)` in `utils/assetPriceDerived.ts`, accanto a `DELTA_PERIODS`, lascia invariata una chiave che non riconosce.
- **L'AI Export**: `periodPresetLabels` è letto solo dai bottoni di `AiExportOptionsPanel.svelte:259`, mai dal renderer del prompt. I byte del prompt non cambiano.
- **Catalogo** (coordinatore: «sì», un blocco diverso da quelli di M nel lotto 16): una chiave nuova `datePicker.presets.days`, en `{n}D`, it `{n}G`, fr `{n}J`, es `{n}D`, accanto a `weeks`.
- **Test** (test-author): i rossi senza testo tradotto, con il marcatore `qaa` o un `t` marcatore, in file già registrati: `aiExportUi.test.ts`, `assetPriceDerived.test.ts`, `AssetTable.test.ts`. FxTable non ha un file di test, e il runner non è assegnato.
> **Note implementazione** (2026-10-11):
> - **Helper**: `deltaPeriodLabel(key, t)` riconosce `^(\d+)([DWMY])$` e restituisce invariata ogni altra chiave.
> - **Le tabelle**: le colonne `Δ 1D` e dinamiche di AssetTable e FxTable passano per l'helper. I titoli prendono la forma a funzione, `() => …`, come gli altri titoli, quindi seguono il cambio di lingua.
> - **L'AI Export**: `periodPresetLabels` in `ui.ts` usa `t('datePicker.presets.months'|'years', {values: {n}})`.
> - **I rossi** (test-author): 7 rossi più una guardia che legge i 4 cataloghi, nei file registrati.
> - **Evidenze**:
>   - i 4 file → 33 passed;
>   - `front check` → 0 errori;
>   - `i18n audit`: 4348 chiavi complete, 0 inutilizzate;
>   - le stringhe inglesi sono identiche a prima (`Δ 1W`, `3M`), quindi gli E2E in inglese non cambiano.
> - **Cosa c'era già nella v1.1.0**: le tre etichette.
> - **Note fuori dal lotto**: la pagina FX tiene una sua copia di `DELTA_PERIODS` (`routes/(app)/fx/+page.svelte:159`), e FxTable non ha un file di test. Le ho messe nella riga FE2–FE11 dell'indice.

### C-50 — `portfolio_weight_ratio` grezzo nel prompt (developer: «C-50 prima della 1.2, lo fa T dopo le durate») — analisi
- **Il difetto**: la tabella `portfolio_role.unavailable` di `asset.position_scope` nomina i campi del payload. Il renderer rinomina la colonna `portfolio_weight_ratio` in `portfolio_weight_percent` (`PUBLIC_RATIO_FIELD_NAMES`, `genericFieldName`), ma non i riferimenti nel valore `field`. Così il prompt nomina un campo che non mostra, e il controllo pubblico della sonda (`raw_ratio_weight_name`) fallisce appena una gamba non ha valore corrente.
- **Dove correggere: nel renderer.**
  - Il payload resta canonico, cioè nomina i propri campi, e la versione del componente non cambia.
  - I byte del prompt cambiano solo dove un riferimento nomina un campo rinominato. Oggi è soltanto `asset_core.py:276,283`; `missing_fields` (`asset_core.py:398,464`) nomina solo campi non rinominati.
  - Correggere il payload vorrebbe dire nominare nel JSON un campo che il JSON non ha, e cambiare il contratto del componente.
- **Regola**: le foglie `field` e `missing_fields` passano per `PUBLIC_RATIO_FIELD_NAMES`, la stessa mappa delle colonne.
- **Prove**:
  - un rosso nel test del renderer;
  - la sonda mirata sulla 6164: un Asset con una gamba senza valore corrente (l'asset KRW dei dati sintetici non ha cambi), con il controllo pubblico verde;
  - la doc «Snapshot Data Tables».

#### C-50 — implementazione ✅ (2026-10-11)
> **Note implementazione**:
> - **Renderer**: `FIELD_REFERENCE_KEYS = {'field', 'missing_fields'}` in `snapshotDataRenderer.ts`. In `genericLeaf`, una stringa sotto queste chiavi che è nella mappa `PUBLIC_RATIO_FIELD_NAMES` esce col nome pubblico; il testo libero, come `reason`, non cambia. Payload e versione del componente sono invariati.
> - **Test** (test-author): 2 rossi e 2 controlli; il test copia la regex `raw_ratio_weight_name` della sonda. I test dell'AI Export → 12 file, 147 passed.
> - **Sonda mirata** (6164, dati sintetici, Apple):
>   - **Primo giro** (`20261011T200013`): la gamba senza valore non c'era, il peso era noto (31,2%) e la tabella assente. Il caso non era esercitato.
>   - **Secondo giro** (`20261011T200040`), dopo aver rimesso l'Asset VND senza cambi del seme di B3b:
>     - `TABLE portfolio_role.unavailable` dà `|2|portfolio_weight_percent|…|`, uguale alla SUMMARY `portfolio_role.portfolio_weight_percent|null`;
>     - 0 nomi grezzi;
>     - la sonda ha 0 fallimenti, controlli pubblici compresi;
>     - UI e sonda identiche, stringa e byte UTF-8.
> - **Cosa c'era già nella v1.1.0**: il difetto (`ea0558b3c`).

### T-1 — inventario sulla base con F (2026-10-12) — 🧊 in attesa dell'ok del coordinatore
- **Base**: `5d62658bb` (treno 42, con F). Worktree pulita, corsia 6164 libera.
- **Riverifiche** (le righe di §3.1 erano su `b20eac99`):
  - `portfolio_engine.py`, 2 872 righe:
    - modelli `:115-229`, `:448-619`, `:1826-1872`;
    - classificatore `:237-436`;
    - `DailyStateBuilder` `:627-1817`;
    - `build_cost_positions` `:1875-1901`;
    - `DerivedViewsBuilder` `:1909-2336`;
    - identità della cache `:2344-2428`;
    - `load_configured_fx_pair_sets` `:2431-2445`;
    - `PortfolioCalculationEngine` `:2448-2872`.
  - `EngineEndState` e `PortfolioCalculationResult` sono definiti dopo `DailyStateBuilder`, ma lui li usa → vanno in `portfolio/models.py`.
  - `build_data_quality_report` è un metodo di `DerivedViewsBuilder`, non una funzione. B lo estrae in `data_quality.py`; i lotti lo chiamano su un builder vuoto (`lots_analysis_service.py:954`).
  - Lo slug doppio c'è ancora: `portfolio_engine.py:65` `(pair)` e `PortfolioService._normalize_fx_pair_slug(base_or_pair, quote=None)` (`portfolio_service.py:580`), che lo contiene → una sola funzione, con la firma più larga.
  - `fifo_lot_engine.py` usa solo la stdlib:
    - modelli `:16-372`, con `_require_*` (`:1589-1604`) che servono a `FifoInputTransaction`;
    - `eligible_income_quantity` `:1542-1564`;
    - motore `:375-1539`.
  - `native_cash.py` (di F) importa solo `fx` e `schemas.common`: nessun ciclo col motore spostato.
  - Gli import pigri del motore: in `portfolio_service` `:593`, `:691`, `:1232`, `:1384`, `:1435`, `:1606`, `:1674`, `:2044`; nel PAC `:1319-1320`.
  - **Test**: 32 file da toccare, solo per import e per la stringa di percorso in `test_data_quality_thresholds.py:57`.
  - **Runner**: `_backend_utils.py:121`, `_backend_services.py:584`, `:626` e `:607` (questa con B). `services financial-math` esegue la cartella, quindi la guardia nuova non va registrata.
  - **Doc**: 13 pagine dev da aggiornare, più 1 nuova.
  - **`.github`**: solo la sezione «One Home» di `backend.instructions.md` (`:56-77`).
  - **devWiki**: 61 righe «Source files» in 46 pagine. `check_source_paths.py` sulla base dà **6** inesistenti (9 occorrenze) in 6 pagine: il DoD diventa «resta a 6».
- **Nessun riferimento per stringa**: niente filtri per nome di logger, niente `importlib`.
- **Inventario completo**: nei file della sessione (`t1/inventory_5d62658bb.md`). La base `all-backend` di §7.3 è in corso sulla 6164.

### T-1 — via libera del coordinatore (2026-10-12)
- **Nessun ramo attivo** tocca il motore, il FIFO, i lotti o `portfolio_service.py`. A e B entrano nel target con **un treno solo**.
- **A in un commit a sé**: il coordinatore lo committa sul ramo di T senza integrarlo, così git vede le rinomine al ~99 %. Poi B sopra.
- **File condivisi assegnati a T**:
  - il runner (`_backend_utils.py`, `_backend_services.py`, compresi `:572-574` e la `desc` di `financial-math`);
  - `pyproject.toml:83-85`;
  - la voce di nav in `mkdocs.yml`;
  - `backend.instructions.md:56-77`;
  - una riga di `frontend.instructions.md`;
  - D-11, `financial-math.instructions.md`: lo scrive T dopo B;
  - `TODO_FUTURI.md:2033` e `:2040`, riverificando le righe citate;
  - le 61 righe «Source files» della devWiki, con `project-historian` nella worktree di T.
- Niente CHANGELOG. Identificatori di contratto invariati. In `asset_core.py` e `fx_core.py` cambia solo l'import: niente sonda.

#### Base prima di T-1 ✅ (2026-10-12)
> **Note implementazione**:
> - `all-backend` sulla 6164, su `5d62658bb`: 7/7, **12 353 passed, 28 skipped, 0 failed** (22 min 56 s). I conteggi per sessione sono nei file della sessione (`t1/baseline_all_backend_summaries.txt`).
> - **Statici**:
>   - il backend è pulito per ruff e black: i 197 reperti di ruff e i 29 file di black sono tutti in `dev.py` e `scripts/`, fuori dai file di T-1;
>   - dead code: 38 reperti;
>   - `api sync`: presi gli hash dei 5 file generati.
> - `check_source_paths.py`: 6 percorsi inesistenti (9 occorrenze).

#### Passo A — rinomina ✅ (2026-10-12)
> **Note implementazione**:
> - **Spostati con `mv`**, niente shim (script `/tmp/libreFolio_t1_a_apply.py`):
>   - `roi_utils` → `returns.py`, `valuation_utils` → `valuation.py`;
>   - `yield_on_cost.py` resta col suo nome;
>   - `price_resolver` → `price_marks.py`;
>   - `fifo_lot_engine` → `fifo/engine.py`, `portfolio_engine` → `portfolio/engine.py`.
>   - Spariscono il barile `utils/financial/__init__.py` e la sua cartella.
>   - `fifo/__init__.py` e `portfolio/__init__.py` hanno solo la docstring.
> - **Import riscritti in 43 file**: 8 dell'app, 33 di test, 2 del runner.
>   - La forma del PAC (`from backend.app.services import portfolio_engine, portfolio_service`) l'ho riscritta a mano.
>   - In 11 file `ruff --select I --fix` ha solo riordinato gli import.
> - **Testo**: aggiornate 5 menzioni nei commenti dell'app (`price_resolver`, `roi_utils`, `asset_sources/core.py:300`) e 5 nei docstring dei test. Restano, di proposito:
>   - le menzioni storiche con lo SHA (`test_broker_internal_flows.py:3`, `test_foreign_cash_revaluation.py:3`);
>   - il valore di contratto `"valuation_source": "portfolio_engine"`.
> - **`financial_math/__init__.py`**: la regola emendata (§3.2) e la mappa dei moduli. **`pyproject.toml:83-85`**: ora i barili sono 4.
> - **⚠️ Fuori pista**: `ROIResult` (`returns.py`) restava vivo solo grazie all'`__all__` del barile, e senza il barile vulture lo segnala. Non ha riferimenti in app, test, frontend, doc e wiki; è un contenitore di 3 campi, senza logica da integrare. L'ho tolto (9 righe).
> - **Gate**:
>   - grep dei vecchi percorsi a 0 in `backend/`, `scripts/`, `dev.py`, `pyproject.toml`;
>   - `import backend.app.main` ok;
>   - ruff e black puliti sui 53 file toccati;
>   - mirati verdi: `financial-math` 175, `roi-fifo-utils` 652, `portfolio-engine` 40, `lots-analysis-pure` 121, `portfolio-allocation-source` 89, `utils roi-utils` 9;
>   - `api sync`: hash identici;
>   - dead code: uguale alla base, meno i 2 reperti del barile.
>   - `all-backend` sulla 6164: 7/7, **12 353 passed, 28 skipped, 0 failed** (20 min 05 s). Identico alla base anche in ognuna delle 23 invocazioni. Porta 6164 libera.

#### Proposte di I (treno 43, `d27a2f729`, solo journal) ✅ (2026-10-12)
> **Note implementazione**:
> - Le righe dell'inventario seguono la ripartizione di §17.6 del piano 41:
>   - P1 → U4;
>   - R4 → U5, con B8 di I;
>   - W1 → U7;
>   - X5: F ha chiuso i movimenti, mentre le 4 conversioni dei prezzi restano in U1/U5.
> - Nell'indice, sezione T: U1 dice «X5 sui movimenti»; U4, U5 e U7 nominano P1, R4 e W1.
> - Il commento PURE di `financial-math` nel runner («each module's only I/O is convert_bulk, which every test replaces on its module with a double») entra con B, insieme alla `desc` e alla guardia.

### Passo B — il taglio (2026-10-12)
> Il coordinatore ha committato A sul ramo di T (`1cc9cd8f5` refactor, `528ef2fe1` journal), senza integrarlo. B parte da `528ef2fe1`. `risk/service.py:1304` e il suo import sono assegnati a T.

#### B1 — FIFO in tre moduli ✅ (2026-10-12)
> **Note implementazione**:
> - Script `/tmp/libreFolio_t1_b_split.py`: ogni definizione di primo livello, coi commenti sopra, va nel modulo assegnato. Gli spazi originali restano fra le definizioni vicine, e ruff toglie poi gli import inutili.
> - Risultato: `fifo/models.py` (tipi, dataclass, risultato, `_require_*`), `fifo/eligibility.py` (`eligible_income_quantity`) e `fifo/engine.py` (`FifoLotEngine`, `run_fifo_lot_engine` e gli aiuti privati). Il grafo è senza cicli: models → eligibility → engine.
> - Gli import di 4 file puntano al modulo che definisce il nome (script `/tmp/libreFolio_t1_b_imports.py`).
> - Mirati: `roi-fifo-utils` 652, `lots-analysis-pure` 121, gli stessi conteggi.
> - **⚠️ Fuori pista**: alla prima passata lo script metteva due righe vuote fra alias `Literal` che nell'originale sono adiacenti. Ho ripristinato `fifo/engine.py` con `git show HEAD:… >` e ho rifatto la passata conservando gli spazi originali.

#### B2 — motore del portafoglio in sei moduli ✅ (2026-10-12)
> **Note implementazione**:
> - `portfolio/models.py`, `classifier.py`, `daily_state.py`, `data_quality.py`, `derived_views.py` ed `engine.py`. Il grafo è senza cicli: models → classifier → daily_state; data_quality → derived_views; tutti → engine.
>   - `EngineEndState` e `PortfolioCalculationResult` vanno in `models`.
>   - `_cumulative_split_ratio` va in `daily_state`, `_EXTERNAL_CASH_TYPES` in `classifier`.
>   - La docstring d'architettura del vecchio motore ora è in `portfolio/__init__.py`, coi nomi dei moduli.
> - **Qualità dei dati**:
>   - il report è una funzione, `data_quality.build_data_quality_report(daily_states, …)`, con lo stesso corpo;
>   - `DerivedViewsBuilder` tiene un metodo di una riga che le passa i suoi stati, così le 2 chiamate del servizio e le 38 del test dedicato restano uguali;
>   - i lotti (`lots_analysis_service.py:944`) e `test_risk_asset_set.py:1861` costruivano un builder vuoto solo per il report: ora chiamano la funzione.
> - **Slug unico**: `normalize_fx_pair_slug(pair)`, pubblico, in `data_quality.py`.
>   - Via `PortfolioService._normalize_fx_pair_slug`, la cui forma a due argomenti non era usata da nessuno.
>   - `risk/service.py:1304` chiama la funzione unica.
> - **PAC**: `QUANTITY_DUST_THRESHOLD` pubblico da `data_quality_thresholds`, al posto di `_QUANTITY_DUST_THRESHOLD` di `portfolio_service`.
>   - L'import del motore resta pigro, ma per un'altra ragione: il test sostituisce `PortfolioCalculationEngine` sul suo modulo. Ho aggiornato il commento.
> - **Import**: 23 file puntano al modulo che definisce il nome.
>   - Le 10 letture di `portfolio_engine_module.DailyStateBuilder` (3 test) importano `DailyStateBuilder` da `daily_state`.
>   - `TransactionType` arriva da `db.models`.
> - **Percorsi nel testo**:
>   - `test_data_quality_thresholds.py:57` → `daily_state.py`;
>   - `test_native_cash_guard.py:260` → `classifier.py`;
>   - `fx_core.py:355` → `daily_state`;
>   - il commento di `schemas/portfolio.py:165` → `data_quality.build_data_quality_report`.
> - **Mirati**:
>   - `portfolio-engine` 40, `roi-fifo-utils` 652, `lots-analysis-pure` 121, `portfolio-allocation-source` 89;
>   - `risk-asset-set` 51, `fx-core` 23, `financial-math` 175;
>   - `risk-all -k data_quality_thresholds` 31.
> - ruff e black puliti sui 38 file toccati.
> - **Reperto, fuori lotto**: `risk/service.py:439` chiama il privato `PortfolioService._get_configured_fx_pair_sets()`, che avvolge `load_configured_fx_pair_sets`. Non lo tocco: la riga assegnata è solo `:1304`.

#### B3 — matematica dei lotti in `financial_math/lots/` (T-1f) ✅ (2026-10-12)
> **Note implementazione**:
> - Script `/tmp/libreFolio_t1_lots.py`. Ogni metodo puro di `LotsAnalysisService` diventa una funzione:
>   - stesso corpo, de-indentato, senza `self` e senza `@staticmethod`;
>   - le chiamate agli altri metodi spostati diventano chiamate di funzione.
>   - I nomi letti fra moduli diventano pubblici (`FxRateResolver`, `WithheldEconomics`, `ALL_BROKERS`, …). La mappa di 50 nomi è in `/tmp/libreFolio_t1_lots_map.txt`.
> - **Moduli** (grafo senza cicli: prices → conversions → economic_events → histories; average_cost_lines da solo):
>   - `prices.py` (69 righe): `PriceHistoryLookup`, `opening_reference_price`;
>   - `conversions.py` (181): `FxRateResolver`, i bisogni di cambio;
>   - `economic_events.py` (336);
>   - `histories.py` (558);
>   - `average_cost_lines.py` (55).
> - **Il servizio resta** (2 274 → 1 172 righe): orchestrazione, caricamenti dal DB, i DTO (sintesi, Gantt, righe degli eventi), il report di qualità dei lotti e `_compute_average_cost_lines`, che passa da `compute_average_costs`.
> - **⚠️ Fuori pista**: il nome nuovo `known_realized_pnl` coincideva con una variabile locale di `_build_lot_summaries` (F823). La variabile ora si chiama `lot_realized_pnl`. Una scansione `ast` non trova altre collisioni fra parametri, locali e nomi nuovi.
> - **Prove**: import dell'app ok; ruff e black puliti; `roi-fifo-utils` 652 (compreso il test end-to-end dei lotti) e `ai-export` 1 002.
> - `test_lots_analysis_pure.py` (121 test, 45 chiamate a metodi privati) lo riscrive test-author, e scrive anche la guardia T-1g.
> - **test-author**: `test_lots_analysis_pure.py` riscritto.
>   - Le chiamate ai metodi spostati diventano chiamate di funzione; `ALL_BROKERS` arriva da `average_cost_lines`.
>   - La patch di `convert_bulk` va su `lots.conversions`, il modulo che lo legge; il test lo conferma (`calls == [1]`).
>   - 121 test e 130 assert, come prima. `lots-analysis-pure` 121 passed.

#### T-1g — guardie dello strato ✅ (2026-10-12)
> **Note implementazione** (test-author): `test_financial_math/test_layer_boundaries.py`, 270 righe, solo `ast`, senza import dell'app.
> - **(a)** Gli import vietati, un test per ognuno dei 24 file dello strato. Conta ogni import, anche pigro o sotto `TYPE_CHECKING`; risolve i relativi, e `from a import b` vale anche come `a.b`.
> - **(b)** I 4 `__init__.py` contengono solo la docstring.
> - **(c)** Le 5 vecchie case non esistono più. Una cartella `utils/financial/` con il solo `__pycache__` non conta: git lascia quella cache sui checkout che hanno girato il codice vecchio.
> - **4 test di controllo**:
>   - il riconoscitore segnala 18 import vietati e nessuno dei 12 permessi, compreso `import signal` della libreria standard;
>   - il controllo degli `__init__` segnala import, assegnazioni, `__all__` e una seconda stringa;
>   - il controllo delle vecchie case gira in una cartella temporanea;
>   - la scansione deve trovare i moduli noti dello strato.
> - `financial-math`: 212 passed, cioè 175 + 37.
> - `check-orphans` pulito.

#### B4 — devWiki ✅ (2026-10-12)
> **Note implementazione** (project-historian, nella worktree di T, solo le righe «Source files»):
> - 58 righe in 46 pagine: diff di 58+/58−, solo righe di tabella. Il controllo trova esattamente le 58 occorrenze dei percorsi spostati; la stima di 61 contava anche righe che esistono ancora.
>   - Per vecchio file: `portfolio_engine` 25, `fifo_lot_engine` 18, `roi_utils` 10, `yield_on_cost` 3, `price_resolver` 1, `valuation_utils` 1.
>   - 10 righe citano 2 o 3 sotto-moduli, nella forma con le virgole già usata da 64 righe della wiki.
> - `check_source_paths.py`: prima 12 percorsi inesistenti (67 occorrenze), dopo **6 (9 occorrenze, 6 pagine)**, cioè quelli di prima di T-1, invariati.
> - Restano di proposito 7 righe su `lots_analysis_service.py`, che esiste ancora: le linee del costo medio e i buchi si calcolano ancora lì.
> - **Dopo la 1.2** (T-W1 nell'indice): 50 menzioni dei vecchi percorsi nella prosa, in 28 file, fuori dalle tabelle. Fra queste `domains/calculations.md:70`, che chiama «FIFO engine» `transaction_service.py`.

#### Runner, `.github`, `TODO_FUTURI` ✅ (2026-10-12)
> **Note implementazione**:
> - **Runner** (`_backend_services.py`):
>   - `financial-math`: docstring, sezione e `print_info` con la guardia;
>   - la `desc` è la formulazione di I, allargata con «boundaries of the whole layer»;
>   - il commento PURE è quello di I, più la riga sulla guardia;
>   - `lots-analysis-pure` → `financial_math/lots/`;
>   - `portfolio-engine` → `daily_state.py`;
>   - «price resolver» → «price marks» (2 righe).
> - **`.github`**:
>   - la sezione «One Home» di `backend.instructions.md`: tabella coi percorsi finali (più `native_cash`, `lots/`, `price_marks`), la riga su rischio, segnali e PAC, e il rimando al file d'istruzioni nuovo;
>   - `frontend.instructions.md`: la sezione «Financial numbers», una riga;
>   - nuovo `financial-math.instructions.md` (D-11): `applyTo` `backend/app/services/financial_math/**`, coi moduli, le regole, come aggiungere un calcolo, le guardie e i test.
> - **`TODO_FUTURI.md`**, sulle sole righe citate:
>   - `:2033` → `financial_math/portfolio/engine.py:312`;
>   - `:2036` → `:246`;
>   - `:2038` → `daily_state.py:366`;
>   - `:2040` → `financial_math/price_marks.py:146`;
>   - `:2046` → `:312`.
>   - Ho verificato le righe sul codice del 01/10 (`5405f25a1`), il commit che le ha scritte.
>   - La menzione `portfolio_engine` a `:2030` resta: non è fra le righe assegnate.
> - **Docstring dello strato e dei pacchetti**: la mappa con i sotto-moduli di `fifo`, `portfolio` e `lots`.

#### B5 — doc per sviluppatori ✅ (2026-10-12)
> **Note implementazione** (docs-writer, solo EN):
> - Pagina nuova `developer/backend/financial_math.md`, con la mappa dei pacchetti, il motore del portafoglio passo per passo, le regole con un diagramma, come aggiungere un calcolo, le guardie e i selettori.
> - Voce di nav fra Scheduler e Risk Engine.
> - 13 pagine aggiornate. Nel farlo ha corretto:
>   - la firma vecchia di `run_fifo_lot_engine` nella pagina del FIFO, che non aveva 3 parametri;
>   - il passo 2 della pipeline dei lotti;
>   - «due moduli importano il resolver», che oggi sono tre.
> - **Cose segnalate, sistemate da T**:
>   - il punto di lettura `load_configured_fx_pair_sets` ora è nominato nella regola (docstring dello strato e D-11);
>   - le eccezioni del frontend «devono essere dichiarate»: oggi nel codice non lo sono;
>   - `architecture/overview.md:76` e `developer/index.md` puntano alla pagina nuova;
>   - le docstring di `returns.py` e `portfolio_service.py` usano i nomi nuovi.

#### Gate finali di T-1 ✅ (2026-10-12)
> - **`all-backend`** sulla 6164: 7/7, **12 390 passed, 28 skipped, 0 failed** (20 min 12 s).
>   - In 22 invocazioni su 23 i conteggi sono uguali alla base.
>   - Nei `services` ci sono 37 test in più, quelli della guardia.
> - **Docstring toccate durante il giro**: le ho riprovate dopo con `financial-math` 212, `utils roi-utils` 9 e `roi-fifo-utils` 652.
> - **Statici**:
>   - ruff e black come la base;
>   - dead code come la base, meno i 2 reperti del barile;
>   - `api sync`: `generated.ts` e altri 3 file identici. `openapi.json` cambia solo in `info.version`, che viene da `git describe` (la HEAD è `528ef2fe1`). Rigenerato da `HEAD` in una copia, è l'unica differenza.
> - **Doc**: `mkdocs build` stretto ok; `check-links` 95 link validi.
> - **devWiki**: `check_source_paths.py` a 6, come la base.
> - **Grep dei vecchi percorsi** (`backend/`, `scripts/`, `dev.py`, `.github/`, `mkdocs_src/docs/developer/`, `pyproject.toml`): 9 righe, tutte volute. Sono le vecchie case nella sezione delle guardie del file d'istruzioni e la tabella vecchio → nuovo della pagina nuova.
> - `git diff --check` pulito; porta 6164 libera.

### Checkpoint B 🧊 (2026-10-12) — FROZEN, in attesa del coordinatore
- Quattro commit proposti: refactor (codice, test, guardia, runner), doc, devWiki, journal.
- Niente CHANGELOG.
- Due voci per dopo la 1.2 nella sezione T dell'indice: T-W1 e T-R1.

### Treno 45 (coordinatore, 2026-10-12)
- T-1 è nel target (merge `76a7b099b`, commit `a57a43fbd`, `4e4ae37e5`, `09c089147`, `8e0c4f245`). P-5 del 38 è chiusa da `1cc9cd8f5`.

### C-53 — `reconciled` falso per un residuo di arrotondamento (developer: approvata per la 1.2) — analisi (2026-10-12)
- **Base**: `378338fed` (treno 46). Corsia 6164.
- **Il difetto**: `portfolio_financial.py:490` e `broker_financial.py:435` (le stesse righe anche dopo T-1) fanno `reconciled = residual_amount == Decimal("0")`.
  - Il residuo è `period_pnl − (Δ non realizzato + realizzato + entrate − costi e tasse + altro)`.
  - Il servizio calcola `period_other_result` come termine di chiusura della stessa scomposizione (`portfolio_service.py`, `:1959`), quindi il residuo è zero per costruzione. Quando non lo è, resta l'arrotondamento dei Decimal a 28 cifre (1e-24).
  - Succede in 5 snapshot su 33, prima e dopo F: non dipende dalla cassa estera.
- **Nel prompt**: il renderer stampa un residuo monetario più piccolo dell'unità minima della valuta come `0` (`monetary_residuals_zeroed`). Così il prompt dice `reconciled: false` accanto a `residual: 0`: si contraddice.
- **La cura** (proposta di I, approvata dal developer):
  - `reconciled = abs(residual) < CONVERSION_DUST` (`financial_math/native_cash.py`, 1e-9), sempre. La regola del servizio con la cassa estera riguarda un'altra cifra, la riga del residuo dopo «FX on cash».
  - `residual` resta la differenza esatta.
- **Versioni** (regola del developer: +1 rispetto alla 1.1): `portfolio.reconciliation` e `broker.reconciliation` sono alla v1 sia in `v1.1.0` sia in HEAD, quindi passano alla v2.
  - La versione è scritta in due posti: lo spec e il segnaposto del catalogo congelato (`components/catalog.py:111`, `:136`). Il registro controlla che coincidano.
  - `COMPACT_COMPONENT_VERSIONS` prende {1, 2} per i due componenti nello stesso cambio. Senza, la v2 cadrebbe nello YAML (la lezione di B3b).
- **Doc**: nessuna pagina descrive `reconciled`. Una riga in «Snapshot Data Tables» di `ai_export_composition.md`, via docs-writer.
- **Rossi** (test-author):
  - backend: un residuo di 1e-24 dà `reconciled` vero; uno pari o sopra la tolleranza dà falso, per il portafoglio e per il broker; la v2 nello spec e nel segnaposto;
  - frontend: la v2 si stampa come la v1, e la v3 cade nello YAML.
- **Sonda mirata**: sui dati sintetici della 6164, portafoglio e broker; cerco un caso con il residuo di arrotondamento.

### D-P7 — `utils/` e gli aiuti di dominio: decisa dal developer (2026-10-12)
> «diciamo che utils era nata come logica per essere quello che tu vuoi fare in domain, sarebbero le funzioni "foglie" quelle più basiche, non serve quindi spostare o rinominare, al più creare dentro utils delle cartelle per raggruppare le tipologie di utility, quello sarebbe inteligente. Ti ho fatto creare un service layer per la finanza, perchè se iniziamo a chiedere cambi, asset e altro, non è più una funzione terminale, ma diventa parte dello stack di servizi e ha senso raccogliere queste cose in dei layer ordinati che si usano l'un l'altro»
- **Niente `backend/app/domain/`**: `utils/` resta la casa delle funzioni foglia, quelle che non chiamano servizi. Oggi è già così: i moduli di `utils/` importano solo altri `utils` e, in `decimal_utils`, `db.models`.
- **BU1 e BU2 si riscrivono**, dopo la 1.2: niente spostamenti sotto `services/`. Al più si fanno sottocartelle dentro `utils/` per tipo di utility. Le proposte di §P2.3 (`platform/`, `services/fx/`, `api/` per i moduli di `utils/`) decadono.
- **Quello che chiede** cambi, asset o altri servizi sta negli strati di servizio, come `financial_math`.
- **Applicato nel checkpoint di C-53** (assegnazioni del coordinatore):
  - la regola in `backend.instructions.md`, due righe dopo la sezione «One Home»: «`utils/` holds leaf functions only: they never import services; anything that needs FX, assets or other services belongs to a service layer»;
  - la riga T-BU1+BU2 della sezione T dell'indice, riscritta.

#### C-53 — implementazione ✅ (2026-10-12)
> **Note implementazione**:
> - **Rossi** (test-author), che falliscono per le ragioni attese:
>   - backend, 10 su 22: 6 casi di polvere e 2 di chiusura col formula del servizio (cambio 1,09, residuo 1E-24) danno `False` invece di `True`; 2 test di versione danno (1, 1) invece di (2, 2);
>   - controlli verdi: zero esatto, 899, `None`, ±`CONVERSION_DUST` (contro un `<=` o un `abs` dimenticato), −99;
>   - frontend, 4 su 403: la v2 cade nello YAML.
> - **Cura**:
>   - `reconciled = abs(residual_amount) < CONVERSION_DUST` nei due builder, con l'import da `financial_math/native_cash.py`;
>   - `version=2` sui due spec e sui due segnaposti di `components/catalog.py`;
>   - `COMPACT_COMPONENT_VERSIONS` {1, 2} per i due componenti, col commento;
>   - `residual` invariato.
> - **Test** (test-author): i blocchi C-53 del test del renderer stanno in un `describe` proprio; il blocco B3b è identico byte per byte a HEAD.
> - **Verde**: `services ai-export` 1 021 (1 002 + 19); `front-ai-export unit` 403; svelte-check 0 errori; ruff, black e prettier puliti; `api sync`: client generato identico.
> - **Sonda mirata** (6164, dati sintetici, `portfolio.overview_and_history` e `broker.overview_and_history` su tutti e 7 i broker):
>   - EUR: 24 casi (3M, 6M, 1Y);
>   - GBP: 10 casi, con la valuta base cambiata sulla sola corsia, poi ripopolata;
>   - tutte le sezioni sono v2, compatte; `reconciled` vale `True` col residuo esattamente zero (`0E-24` e simili), `None` per il broker senza posizioni;
>   - **i dati sintetici non producono un residuo di polvere**: il caso reale lo riproduce il test di chiusura.
>   - 3 fallimenti, preesistenti e fuori da C-53: il broker senza posizioni (`broker_anon_07`) fa fallire il controllo pubblico «invalid HHI points» di `broker.allocation_concentration` e `broker.concentration_context` (HTTP 200).
> - **Equivalenza UI/sonda**: col renderer ufficiale (vite SSR, `/tmp/libreFolio_c53_compare.mjs`), 34 blocchi su 34 sono identici al prompt salvato. Sui dati sintetici il «prima» (v1, regola `== 0`) è identico al «dopo».
>   - Il backend scrive gli importi in notazione piana. Iniettando la polvere nel JSON canonico prima del parse, come la servirebbe il backend:
>     - prima: `|reconciled|false|` accanto a `|residual.amount|0|`;
>     - dopo: `|reconciled|true|` accanto a `|residual.amount|0|`.
> - **Doc** (docs-writer): un paragrafo in «Snapshot Data Tables» di `ai_export_composition.md` (`:422-426`); build stretto e check-links verdi.
> - **Cosa c'era già nella v1.1.0**: il difetto (`== 0` in entrambi i componenti alla v1).
> - **Dopo la 1.2** (T-B9): un residuo reale fra `CONVERSION_DUST` e l'unità minima della valuta si stamperebbe `0` accanto a `reconciled` falso. È improbabile, perché il riepilogo chiude la scomposizione per costruzione.

### BU1 e BU2 nella 1.2 (developer, 2026-10-12, via coordinatore)
- Riformulati con D-P7, dopo il checkpoint di C-53, col metodo di T-1: prima il raggruppamento esatto e l'elenco dei file (76 importatori fra app, test, script e `dev.py`), FROZEN; poi un commit di sole rinomine e uno per BU2, con la suite backend identica come gate.
- **BU1**: sottocartelle per tipo dentro `utils/`, senza spostamenti fuori:
  - `utils/asset/`: sector, geo, identifier, translation;
  - `utils/fx/`: currency;
  - `utils/platform/`: version, network, cache;
  - per datetime, json e decimal decide la proposta di T.
- **BU2**: le due eccezioni alla regola della foglia.
  - Il troncamento di `decimal_utils`, che importa `db.models` (`FxRate`, `PriceHistory`), esce da `utils/`; `parse_decimal_value` resta.
  - I 3 import pigri di `clear_cache` in `fx.py` (`:1218`, `:1533`, `:1674`) si tolgono se il ciclo «utils→services» non esiste più: `fx.py` importa già `cache_utils` in cima, e `cache_utils` non importa servizi.

### Checkpoint C-53 🧊 (2026-10-12) — FROZEN, in attesa del coordinatore
- **Tre commit proposti**:
  - `fix(ai-export)`: codice, test e il paragrafo della doc;
  - `docs(rules)`: la regola su `utils/`;
  - `docs(journal)`: piano e indice.
- **Riga di CHANGELOG** proposta al coordinatore, in «🐛 Fixed» › «🤖 AI Export and signal contracts».
- **Dopo il checkpoint**: BU1 e BU2, cominciando dall'elenco dei file.

### Treno 47 (coordinatore, 2026-10-12)
- C-53 è nel target: merge `e25eb913d`, CL `5d0585595`, commit `876d2b430`, `45691452a`, `25e358eb0`.
- Il reperto HHI sul broker senza posizioni è registrato come C-55, da verificare dopo la 1.2.

### BU1/BU2 — analisi (2026-10-12) 🧊 in attesa dell'ok
- **Base**: `5d0585595`. 74 file importano i moduli di `utils/` (45 nell'app, 28 nei test, più `dev.py`). Nessuna migrazione, `scripts/` o `frontend/scripts` li importa.
- **Nessun test patcha** `clear_cache` o altre globali di `cache_utils`. L'unica patch su un modulo è in `test_version.py` (`version_utils.get_git_version`, sull'oggetto modulo).
- **Dipendenze fra moduli**: `currency_utils` → `geo_utils`, `translation_utils`; `geo_utils` → `decimal_utils`, `translation_utils`; `decimal_utils` → `db.models`. Quindi oggi geo e currency caricano i modelli del DB al momento dell'import.
- **Stringhe**:
  - `.github/workflows/release.yml:131`: la CI importa `backend.app.utils.version`;
  - il runner (`_backend_utils.py`, `print_info`);
  - `dev.py`: 3 import pigri di `version`;
  - `TODO_FUTURI.md:1006`, `:1025`;
  - commenti in `frontend/e2e/utilities.spec.ts:9-12` e `frontend/src/lib/i18n/index.ts:12`;
  - 4 pagine dev;
  - 13 righe «Source files» della devWiki, in 11 pagine;
  - il campione di import permesso nella guardia (`test_layer_boundaries.py:169`).
- **Proposta**:
  - `utils/asset/{sector,geo,identifier,translation}.py`, `utils/fx/currency.py`, `utils/platform/{version,network,cache}.py`;
  - datetime, json e decimal restano nella radice di `utils/`;
  - senza il suffisso `_utils` dentro le cartelle;
  - BU2: `db/precision.py` coi 4 troncamenti, e via i 3 import pigri di `clear_cache` in `fx.py`.

### BU1/BU2 — via libera (coordinatore, 2026-10-12)
- **(a)** datetime, json e decimal restano nella radice di `utils/`.
- **(b)** Dentro le cartelle i file non hanno il suffisso `_utils`.
- **(c)** La terza cartella è `utils/runtime/`, scelta del developer («runtime»), non `platform`.
- **(d)** L'import pigro di `version` in `config.py:321` entra in BU2, se il ciclo non esiste.
- **File condivisi assegnati**:
  - le righe `print_info` del runner (`_backend_utils.py`);
  - `.github/workflows/release.yml:131`, col `python -c` provato in locale;
  - i 3 import pigri di `dev.py`;
  - `TODO_FUTURI.md:1006` e `:1025`;
  - due commenti del frontend (`frontend/e2e/utilities.spec.ts:9-12`, `frontend/src/lib/i18n/index.ts:12`);
  - la regola su `utils/` e la mappa in `backend.instructions.md`;
  - la doc, con docs-writer: `financial_math.md:123`, `release-pipeline.md:181`, `settings_cache.md:5`, `:13`. M toccherà `release-pipeline.md` dopo, quindi va chiusa presto.
- **La devWiki la scrive solo W** (l'historian del passo 3), dopo che BU1 entra nel target. Nel gate `check_source_paths.py` resterà alto per quelle righe, ed è previsto.
- **Ordine**: la base `all-backend`; BU1 (sole rinomine) con i suoi gate e un checkpoint; il commit del coordinatore; poi BU2 con i suoi gate e il checkpoint finale. `fx.py` e `config.py` li toccano tutti e due i commit.

#### Base prima di BU ✅ (2026-10-12)
> `all-backend` sulla 6164, su `5d0585595`: 7/7, **12 409 passed, 28 skipped, 0 failed** (23 min 11 s). Presi anche gli statici: ruff, black, dead code e gli hash di `api sync`.

#### BU1 — le cartelle di `utils/` ✅ (2026-10-12)
> **Note implementazione**:
> - **Rinomine con `mv`** (script `/tmp/libreFolio_bu1_apply.py`):
>   - `asset/{sector,geo,identifier,translation}.py`;
>   - `fx/currency.py`;
>   - `runtime/{version,network,cache}.py`.
>   - I 3 `__init__.py` nuovi hanno solo la docstring. La docstring della radice è riscritta con la regola della foglia e la mappa.
> - **Import in 32 file** (21 dell'app, 2 moduli spostati, 8 test, il runner). In 7 file `ruff --select I --fix` ha riordinato gli import.
>   - `dev.py`, che non è pulito per black già nella base, l'ho toccato a mano: 3 righe, e i reperti di ruff restano 43.
> - **Condivisi assegnati**:
>   - le 6 righe `print_info` del runner;
>   - `.github/workflows/release.yml:131`: il `python -c` provato in locale scrive `v1.1.0-1264-g5d0585595-dirty`, e il `VERSION` creato è stato tolto;
>   - `TODO_FUTURI.md:1006`, `:1025`;
>   - due commenti del frontend;
>   - la regola su `utils/` con la mappa in `backend.instructions.md`.
> - **Doc** (docs-writer): 4 righe (`financial_math.md:123`, `release-pipeline.md:181`, `settings_cache.md:5`, `:13`); build stretto e check-links verdi.
> - **Testo**: aggiornate 6 menzioni dei vecchi nomi, nei commenti e nei percorsi delle fixture (`portfolio_allocation_source.py:155`, `test_system_api.py:11`, `test_i18n_usage_gate.py`, 4 righe).
>   - Il gate i18n legge le sorgenti con `rglob("*.py")`, quindi trova anche i moduli spostati.
> - **Gate**:
>   - import dell'app ok;
>   - mirati: geo-utils 4, version 11, sector-normalization 60, currency-utils 23, cache-utils 20, translation-utils 2, gate-i18n-usage 195, financial-math 212, api system 86;
>   - API, dead code, ruff e black come la base.
>   - `all-backend` sulla 6164: 7/7, **12 409 passed, 28 skipped, 0 failed** (25 min 14 s), identico alla base in ognuna delle 23 invocazioni. Porta libera.
> - **In coda dopo BU2** (coordinatore, 2026-10-12, trovata da W): scrivere la regola delle versioni dell'AI Export, «un solo +1 rispetto all'ultima versione rilasciata finché la release non esce; se cambiano solo i valori, nessun bump».
>   - Va in 2 o 3 righe di `ai-development.instructions.md` (assegnato) e in un paragrafo di `ai_export_composition.md` (docs-writer).
>   - Link alla devWiki: `decisions/ai-export-version-bump-once-per-release` (treno 49).
>   - La metto nel checkpoint di BU2.

#### BU1 — correzione prima del commit (coordinatore, 2026-10-12) ✅
> **⚠️ Fuori pista**: `utils/runtime/version.py` calcolava la radice con quattro `.parent`, scritti per la vecchia posizione. Dopo lo spostamento arrivavano a `backend/`.
> - In sviluppo il difetto non si vede: il `VERSION` non c'è e `git describe` trova il repo anche da una sottocartella.
> - Nell'immagine, senza `.git`, l'app avrebbe cercato `/app/backend/VERSION` invece di `/app/VERSION` (`Dockerfile:111`), e la versione sarebbe stata `unknown`.
> - L'ha trovato il coordinatore nella verifica. Né i miei gate né i 12 409 test potevano vederlo.
> **Note implementazione**:
> - **Rossi** (test-author) in `test_version.py`:
>   - `test_git_describe_runs_in_repository_root` (`git describe` girava in `backend/`);
>   - `test_image_layout_reads_version_file_without_git`: un albero come quello dell'immagine in `tmp_path`, il modulo copiato, `app/VERSION`, nessun git nel `PATH`. Stampava `unknown`.
> - **Cura**: `_project_root()` restituisce `Path(__file__).resolve().parents[__name__.count(".")]`. Dipende dal nome puntato del modulo, non dalla profondità a mano, quindi resta giusta anche se il file si sposta ancora.
> - **Verde**: `utils version` 13 (11 + 2), `api system` 86, `brim-parse-race` 42. Nessun `VERSION` lasciato nel repo.
> - **Lezione**: in una rinomina si cercano anche i percorsi calcolati dal file stesso (`__file__`, `parents`), oltre agli import.

### Treno 50 (coordinatore, 2026-10-12)
- BU1 è nel target: commit `346b7e292` e `390ba7d9a`, merge `bdc078efc`. W aggiorna le righe «Source files» dei moduli spostati.

#### BU2 — le due eccezioni alla regola della foglia ✅ (2026-10-12)
> **Note implementazione**:
> - **Precisione del DB**: `backend/app/db/precision.py` (nuovo) prende, invariati, `get_model_column_precision`, `truncate_to_db_precision`, `truncate_priceHistory` e `truncate_fx_rate`, con la docstring d'uso.
>   - `utils/decimal_utils.py` tiene solo `parse_decimal_value` e non importa più `db.models`, SQLModel né SQLAlchemy. Così `asset/geo` e `fx/currency` non caricano più i modelli al momento dell'import.
>   - Import riscritti in 7 file: `asset_sources/{price_store,refresh}`, `fx` e i 4 test. `test_decimal_utils` ora importa da due moduli.
> - **Import pigri**:
>   - `fx.py`: via i 3 import pigri di `clear_cache`; si aggiunge a quello in cima (`clear_cache, get_ttl_cache`). Nessun test patcha `clear_cache`, quindi nessuna patch diventa muta.
>   - `config.py`: l'import di `get_git_version` va in cima. `version` non importa niente dall'app, e la patch di `test_version.py` è letta da `get_version_info()` dentro il modulo stesso.
>   - Con l'import di `backend.app.config` e di `backend.app.main` si vede che non c'è nessun ciclo.
> - **Testo**: la riga `print_info` di `decimal-precision` nel runner, la docstring di `utils/`, e una frase su `db/precision.py` nel paragrafo di `utils/` in `backend.instructions.md`.
> - **Regola delle versioni dell'AI Export** (in coda da W):
>   - una sezione «Versions» in `ai-development.instructions.md`;
>   - un paragrafo in «ComponentSpec» di `ai_export_composition.md` (docs-writer, `:23-28`), con la devWiki citata come testo (`decisions/ai-export-version-bump-once-per-release`).
>   - docs-writer ha verificato le affermazioni sul codice: la corrispondenza col segnaposto la controlla `catalog.py` all'import, non il registro.
> - **Mirati**: decimal-precision 21, numeric-truncation 3, asset-source 61, fx-core 23, fx-conversion 18, version 13, cache-utils 20, financial-math 212.
> - **Statici** come la base: client generato, dead code, ruff, black. Build stretto e check-links verdi.
> - `all-backend` sulla 6164: 7/7, **12 411 passed, 28 skipped, 0 failed** (25 min 05 s). Rispetto a BU1 cambia solo un'invocazione, +2: i test della radice di `version.py`. Porta libera; nessun `VERSION` nel repo.
> - `check_source_paths.py`: 11 percorsi inesistenti (20 occorrenze, 16 pagine). Sono le righe dei moduli di BU1, che aggiorna W.

### Checkpoint BU2 ✅ (2026-10-12) — committato e integrato dal coordinatore
- Commit `8dae5cc6e`, `4388db8df`, `f038ce39a`; manifest e blob verificati dal coordinatore, funzioni spostate identiche all'AST.

### Treno 53 (coordinatore, 2026-10-12)
- BU2 e la regola delle versioni dell'AI Export sono nel target: `dev_release2` = `f0f3de0d9`, worktree in fast-forward lì.

### C-55 — analisi (2026-10-12) ✅ approvata dal developer
> **Richiesta** (coordinatore): solo analisi. Dove sta il difetto «invalid HHI points», cosa vede l'utente, la cura con la versione rispetto a `v1.1.0`, i rossi, la stima.
>
> **Base**: HEAD `f0f3de0d9`, worktree pulita, corsia 6164 (`/tmp/librefolio-r2-t`). Porta libera prima e dopo ogni sonda.

**Dove sta il difetto: nel controllo della sonda.** Il payload e il backend sono corretti.
- **La sonda**: `backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py:847-853`, in `audit_snapshot_semantics`.
  - Segna violazione ogni `herfindahl_index_points` che vale `None`, `< 0` o `> 10 000`. Non prevede l'insieme vuoto.
  - La violazione solleva `ProbeError` a `:2864-2865`, dopo il rendering e prima della misura: il caso esce dal corpus.
- **Il payload è il contratto voluto**. Le tre componenti sono `broker.allocation_concentration`, `broker.concentration_context` e `portfolio.allocations_cash`.
  - L'HHI e il peso massimo vengono dalla stessa lista di pesi, e valgono `None` insieme quando nessuna posizione ha un peso: `broker_financial.py:205-212`, `broker_concentration_context.py:88-103`.
  - L'HHI di un insieme vuoto, 0, direbbe «diversificazione perfetta», che è falso.
  - Il rischio documenta la stessa scelta: `risk/acquired.py:169-192`, «a fully liquid scope rather than a zero-concentration one».
  - Un test esistente fissa `None` sul broker vuoto: `test_ai_export_components_broker_adequacy.py:301` (`test_empty_broker_builds_successfully`).
- **Il backend non valida i range dell'HHI**. I campi sono `SafeDecimal | None`: la risposta HTTP 200 è giusta.
- **Il renderer** stampa `null`, e il preambolo del prompt lo definisce: `null=explicitly unavailable` (`snapshotDataRenderer.ts:62`).

**Sulla corsia (dati sintetici)**:
- **S1, mai detenuto**: Charles Schwab, 0 transazioni.
- **S2, tutto chiuso**: seme solo sulla corsia, `/tmp/libreFolio_c55_seed_closed.py`. Deposito di 2 000 USD, BUY di 5 AAPL, SELL di 5; cassa residua 2 225,20 EUR.
  - Le posizioni chiuse escono dai holdings a `portfolio_service.py:775` (`quantity > QUANTITY_DUST_THRESHOLD`), quindi S2 si comporta come S1.
- In S1 e S2 le due componenti hanno `position_count 0`, `herfindahl_index_points null`, `largest_position_weight_percent null` e `market_value 0`.
  - `broker.concentration_comparison` è `unavailable`, col messaggio «This broker has no valued positions…».
  - La sonda fallisce con HTTP 200 e 0 prompt su 1 misurati.
- **Matrice**: portfolio più i 7 broker, per 3M, 6M e 1Y, cioè 24 casi.
  - Prima: 21 su 24 misurati, 3 fallimenti, tutti Charles Schwab, uno per periodo.
  - Con la regola proposta, simulata a runtime (`/tmp/libreFolio_c55_probe_patched.py`, nessun file del repo toccato): **24 su 24, 0 fallimenti**.
    - Le tolleranze sono esattamente 6: 2 componenti per 3 periodi, tutte sul broker vuoto.
    - I 24 prompt sono identici al byte fra prima e dopo.
    - Sui casi del broker vuoto il renderer e la sonda coincidono.

**Cosa vede l'utente**: nessun difetto.
- L'export funziona.
- L'IA riceve `|position_count|0|`, `|herfindahl_index_points|null|` e `|largest_position_weight_percent|null|`, con la legenda `null=explicitly unavailable`.
- Il confronto col portafoglio spiega in chiaro che il broker non ha posizioni valorizzate.
- Il costo è solo nella sonda:
  - il caso del broker vuoto esce dalle misure;
  - una matrice completa sui dati sintetici esce con codice 1, e così nasconde i rossi veri.

**La cura proposta, solo nella sonda**:
- `None` è valido solo se lo stesso record porta `largest_position_weight_percent` e anche quello vale `null`, cioè nessuna posizione ha un peso.
- Resta violazione:
  - `None` accanto a un peso massimo valorizzato: una regressione del builder;
  - `None` senza il campo fratello: una componente nuova dovrà decidere in modo consapevole;
  - un valore non numerico, `< 0` o `> 10 000`;
  - l'HHI reso come percentuale.
- Un contatore `hhi.unavailable` nel blocco `hhi` (`:1020-1024`) e nei totali (`:3207`, `:3248`), così i casi vuoti si vedono invece di sparire.

**La versione**: nessun bump. Non cambiano né builder, né payload, né renderer.
- Le 4 componenti di concentrazione restano alla v1, come in `v1.1.0`.
- I byte del prompt sono invariati, 24 su 24.
- Niente CHANGELOG: la sonda è uno strumento interno.

**Alternative scartate**:
- **HHI = 0 per l'insieme vuoto**: falso, e contraddice il rischio e il test esistente.
- **Un campo di stato o motivo** nelle 3 componenti:
  - porta la v2 su 3 componenti, più i segnaposti del catalogo e `COMPACT_COMPONENT_VERSIONS`, altrimenti la sezione ricade sul YAML;
  - cambia i byte di ogni export di broker e portafoglio;
  - dice cose già presenti (`position_count 0`, la legenda, il messaggio del confronto).

**I rossi**, con test-author in `test_ai_export_real_prompt_probe.py`, azione `utils ai-export-probe-helpers`:
- Rossi oggi:
  - l'insieme vuoto sulle 3 componenti: `position_count 0` e i due campi `null` danno 0 violazioni e `unavailable` = 3;
  - le posizioni senza peso: `position_count 2` e i due `null` danno 0 violazioni.
- Guardie che devono restare verdi:
  - `None` con il peso valorizzato;
  - `None` senza il campo fratello;
  - `-1`, `10001` e un valore non numerico;
  - il simbolo `%` nel prompt.
- Il test esistente `:1283` resta invariato.

**Stima**: circa 1 h – 1 h 30.
- Rossi: 30 min.
- Cura: 20 min.
- Gate:
  - `utils ai-export-probe-helpers`;
  - ruff e black sui 2 file;
  - la matrice reale da 24 casi sulla 6164, con 0 fallimenti e i byte confrontati con la corsa «prima».

**Rischi**: bassi. La sonda è diagnostica e non tocca l'app.
- La regola lega l'HHI `null` al fratello: una componente futura senza `largest_position_weight_percent` sarà rossa per costruzione, ed è voluto.

**Reperti adiacenti, già tracciati o minori, fuori da C-55**:
- **W3 → T-U7**: l'HHI è calcolato due volte nell'AI Export (`broker_financial.py:205-212` e `broker_concentration_context.py:88-103`). La casa è `financial_math`, dopo la 1.2.
- **W1 → T-U7**: `portfolio_service.py:959` usa denominatore 1 se il NAV è ≤ 0.
  - I pesi diventano valore × 100 e l'HHI supera 10 000.
  - La sonda lo segnerebbe, a ragione. Non è riprodotto sui dati sintetici.
- **Minore**: il `reason_code` del confronto è `broker_summary_unavailable` (`broker_concentration_context.py:390`) anche in S2, dove il riepilogo c'è ma è senza holdings.
  - Il messaggio è esatto, il codice è impreciso.
  - Candidato per T-U9: cambiarlo è un cambio del contratto, quindi la v2.

### C-55 — via libera (developer, 2026-10-12, via coordinatore)
- Testuale: «Sì, nella 1.2: la cura della sonda più i test rossi, circa 1 ora e mezza».
- Portata:
  - la cura solo in `ai_export_real_prompt_probe.py` (`:847-853`, contatore `hhi.unavailable`);
  - prima i rossi via test-author in `test_ai_export_real_prompt_probe.py` (`utils ai-export-probe-helpers`), con le guardie che restano verdi;
  - poi la matrice reale dei 24 casi coi byte confrontati, sulla 6164;
  - niente bump, niente CHANGELOG; il `reason_code` impreciso va in T-U9, dopo la 1.2.
- Base `f0f3de0d9`, uguale al target. Entrambi i file sono puliti per ruff e black sulla base.
- **Correzione all'analisi**: il riepilogo del broker c'è anche in S1 (`market_value` 0, non `null`). Quindi il `reason_code` `broker_summary_unavailable` è impreciso in S1 e in S2, non solo in S2.

Passi:
1. I rossi, con test-author.
2. La cura nella sonda.
3. Verdi e statici.
4. La matrice reale, coi byte confrontati.
5. Il backlog: T-U9, e la chiusura di T-BU1+BU2.
6. Il checkpoint.

#### C-55 passo 1 — i rossi ✅ (2026-10-12)
> **Note implementazione**: test-author ha scritto 16 test nuovi in `test_ai_export_real_prompt_probe.py`, alle righe 1445–1604, più l'import di `build_quality_summary` alla riga 33. Nessun altro file.
> - **I rossi**:
>   - R1, l'insieme vuoto sulle 3 componenti vere;
>   - R2, le posizioni senza peso, su 3 parametri;
>   - R3, il totale `hhi_unavailable` del riepilogo di qualità, contato solo sulle voci `ok`; un blocco senza contatore vale 0.
> - **Le guardie**, verdi oggi e dopo:
>   - G1: `null` accanto a un peso valorizzato;
>   - G2: `null` senza il campo fratello;
>   - G3: il fratello `null` su un altro record;
>   - G4: `-1`, `10000.01`, `abc` e `NaN` accanto a un peso `null`;
>   - G5: i bordi `0` e `10000`, compreso `0` accanto a un peso `null`, così un'esenzione basata su «falso» invece che su `None` viene presa;
>   - G6: il `%` nel prompt.
> - Le guardie asseriscono la lista esatta delle violazioni. I prompt finti hanno sempre una riga `position_count`, così nessuna colonna è tutta `null`.
> - **Comando**: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6164 --data-dir /tmp/librefolio-r2-t utils ai-export-probe-helpers`.
>   - Esito: **5 failed, 68 passed** (57 test esistenti + 16 nuovi).
>   - I 5 rossi sono R1, R2 ×3 e R3. I motivi: `"<component>: invalid HHI points"` nella lista, e `KeyError: 'hhi_unavailable'`.
>   - Log: `/tmp/libreFolio_c55_reds_run2.log`.
> - ruff e black puliti sul file di test. La sonda non è stata toccata.

#### C-55 passi 2–4 — cura, verdi, matrice reale ✅ (2026-10-12)
> **Note implementazione**:
> - **La cura** (`ai_export_real_prompt_probe.py`, 5 punti, applicata con `/tmp/libreFolio_c55_apply.py`):
>   - in `audit_snapshot_semantics`, un `herfindahl_index_points` grezzo `None` non è una violazione se lo stesso record ha la chiave `largest_position_weight_percent`, anch'essa `None`. Conta in `hhi_unavailable`, con un commento sul perché;
>   - il test usa il valore grezzo, non `_as_decimal`, così `abc` e `NaN` accanto a un peso `null` restano rossi;
>   - il blocco `hhi` ha la chiave `unavailable`;
>   - `build_quality_summary` ha il totale `hhi_unavailable`, letto con `.get("unavailable") or 0`.
> - **Verdi**: `utils ai-export-probe-helpers`, **73 passed** (log `/tmp/libreFolio_c55_green.log`). ruff e black puliti sui 2 file; `git diff --check` pulito.
>   - Solo il file dei test importa la sonda: le pagine della doc la citano per percorso, senza dire nulla sull'HHI. L'azione quindi copre tutto.
> - **Matrice reale** sulla 6164: portfolio più i 7 broker, per 3M, 6M e 1Y; wrapper `/tmp/libreFolio_t_probe_synthetic.py`, script `/tmp/libreFolio_c55_matrix.sh`.
>   - **24 su 24 misurati, 0 fallimenti** (prima 21 su 24).
>   - `quality_summary`: `hhi_checks` 45, `hhi_unavailable` **6** (solo `broker_anon_07`, 2 componenti × 3 periodi), `hhi_violations` 0, `public_output_violations` 0, `renderer_equivalence_violations` 0. Secret scan superato; sorgente invariata.
>   - **Byte**: i 24 prompt sono identici, per SHA-256, sia alla corsa «prima» (`/tmp/libreFolio_c55_matrix_before`) sia alla simulazione (`/tmp/libreFolio_c55_matrix_after`). La cura cambia solo l'esito del controllo, mai il prompt.
>   - Nessuna nuova revisione qualitativa, perché i byte non cambiano. I blocchi di concentrazione del broker vuoto li ho letti nell'analisi.
> - **S2 con la cura vera** (il seme del broker che chiude tutto, poi `db populate --force --clean`): 1 su 1 misurato, `hhi_unavailable` 2, 0 violazioni. Il prompt è identico a quello della simulazione di S2.
> - Alla fine la corsia è ripopolata pulita (broker 7 senza transazioni) e la porta è libera.

#### C-55 passo 5 — backlog ✅ (2026-10-12)
> **Note implementazione**: nella sezione T dell'indice post-1.2:
> - **T-U9**: il `reason_code` `broker_summary_unavailable` di `broker.concentration_comparison`, che esce anche col riepilogo presente e senza posizioni; cambiarlo porta la v2.
> - **T-BU1+BU2 chiusa**: BU1 nel treno 50, BU2 nel treno 53.
> - La riga C-55 della sezione C resta al coordinatore.

### Checkpoint C-55 ✅ (2026-10-12) — committato e integrato dal coordinatore
- Base `f0f3de0d9`, uguale al target. 4 file modificati, nessun file nuovo.
- Due commit proposti:
  1. `fix(ai-export): probe accepts an unavailable HHI`: la sonda e il suo file di test (`/tmp/libreFolio_commit_t_c55_1.txt`);
  2. `docs(journal): record C-55`: questo piano e `BACKLOG_POST_1.2.md`, solo la sezione T (`/tmp/libreFolio_commit_t_c55_2.txt`).
- Niente CHANGELOG e niente bump: la sonda è uno strumento interno e i prompt non cambiano.
- Esclusi: gli artefatti delle sonde, i semi e gli script in `/tmp`, il DB della corsia.

### Treno 56 (coordinatore, 2026-10-12)
- C-55 è nel target, col treno 56 (merge `767eb2e31`). La worktree è in fast-forward a `e7d698c4d`.

### CL — CHANGELOG localizzato, parte frontend: analisi (2026-10-12) ✅ approvata
> **Richiesta** (developer, via coordinatore, testuale): «T prende la parte frontend del CHANGELOG localizzato al posto di I: I resta su asse x, rifinitura UI e M-18, e U può dividere prima i cataloghi».
> - **Il contratto di M**: `CHANGELOG.{it,fr,es}.md` alla radice; le righe `## [x.y.z] - data` identiche alla sorgente; un capitolo non tradotto manca dal file; il frontend mostra il capitolo tradotto se c'è, altrimenti quello inglese, con la versione come chiave.
> - Base `e7d698c4d`, worktree pulita, corsia 6164. I file `CHANGELOG*.md` non li tocco.

**Stato attuale, verificato**:
- `changelog.ts:9` importa `CHANGELOG.md?raw` in modo statico; il parser è a `:40`. La modale si importa in modo statico da `Sidebar.svelte:13` e `AboutTab.svelte:19`.
  - Quindi l'inglese sta nella shell. Nella build locale è in un chunk da 177 KB, con 106 KB di testo.
- I test jsdom mockano il modulo: `ChangelogModal.test.ts:40` e `AboutTab.test.ts:96`.
- Il Dockerfile non costruisce il frontend: copia `frontend/build/` (`Dockerfile:52`), che la CI costruisce con `dev.py front build` (`release.yml:158`, `:209`) su un checkout completo.
- Non c'è un service worker.

**Prove sulla corsia**, con file temporanei poi cancellati; porta libera e worktree pulita alla fine:
- **Vitest, ambiente node**: un `import.meta.glob` pigro con `?raw` sui file della radice carica il testo.
- **Vitest, jsdom**: `Error: Denied ID …/CHANGELOG.md?raw`, la stessa ragione dei mock di oggi.
- **vite dev sulla 6164**: il glob diventa `import("/@fs/…/CHANGELOG.md?import&raw")`, e la richiesta risponde 200.
- **Il pattern `[a-z][a-z]`**: sui cataloghi trova esattamente `en/es/fr/it.json`; su `CHANGELOG.[a-z][a-z].md` oggi dà `{}`, senza errori.

**La proposta**:
1. **Caricamento**:
   - l'inglese resta com'è;
   - le traduzioni passano da `import.meta.glob('…/CHANGELOG.[a-z][a-z].md', {query: '?raw', import: 'default'})`, non eager: un chunk per lingua, scaricato solo quando la modale si apre in quella lingua, con una cache per lingua;
   - un glob eager porterebbe nella shell circa 330 KB in più.
2. **Fusione**:
   - l'ordine e l'insieme dei capitoli vengono dall'inglese;
   - la chiave è la stringa fra le parentesi;
   - un capitolo tradotto con contenuto vince, altrimenti si mostra l'inglese;
   - la data viene sempre dall'inglese: una data tradotta diversa non scarta la traduzione (da confermare);
   - un capitolo tradotto vuoto conta come mancante; un capitolo tradotto senza corrispondente inglese si ignora;
   - un errore del chunk fa mostrare tutto in inglese.
   - La lingua è quella della UI (`$locale`, ridotto alla lingua base); `en` o una lingua senza file mostrano solo l'inglese.
   - Ricerca, espandi/comprimi e indice lavorano sui capitoli mostrati.
3. **L'etichetta**:
   - una pillola discreta accanto alla data, solo su un capitolo in inglese dentro una UI tradotta;
   - `lang` su ogni capitolo e `data-version` per i test;
   - una chiave nuova, `changelog.notTranslated`: en «Not translated yet», it «Non ancora tradotto», fr «Pas encore traduit», es «Aún sin traducir». Non esiste un valore simile;
   - al primo caricamento, `common.loading`.
4. **I test** (test-author):
   - Vitest node in `changelog.test.ts`: fusione, loader e cache, e una guardia sui file veri (versioni note, ordine, nessuna copia inglese);
   - jsdom in `ChangelogModal.test.ts`, più il mock in `AboutTab.test.ts`;
   - un E2E consigliato, `e2e/layout/changelog-locale.spec.ts`, neutro rispetto al contenuto. Va registrato nel runner, che è un file condiviso.
5. **La stima**: 4–5 h, più 1–1,5 h con l'E2E.

**I conflitti**:
- La galleria di M (`gallery.spec.ts:1984`) cerca `'Added'`: con i capitoli tradotti non trova risultati in it, fr ed es.
- I cataloghi sono condivisi con U e M.
- «Changelog Rules» in `.github/copilot-instructions.md` è del coordinatore.

### CL — via libera (coordinatore, 2026-10-12)
- Decisioni:
  1. data diversa: tollerante;
  2. l'E2E sì, `e2e/layout/changelog-locale.spec.ts`, con la registrazione in `_frontend_utility.py` (solo il mio blocco);
  3. la chiave subito, in un checkpoint a sé;
  4. «View on GitHub» sul file inglese;
  5. DOMPurify sui capitoli tradotti, meglio se su tutti per una sola via, con il `why` di `htmlSink.gate.test.ts:74` aggiornato;
  6. la doc `about.en.md` con docs-writer; it, fr ed es li fa M;
  7. la pillola va bene.
- Ordine: la chiave, poi i rossi via test-author, poi il resto e il checkpoint finale. La galleria la sistema M; «Changelog Rules» la scrive il coordinatore.

#### CL passo 0 — la chiave ✅ (2026-10-12)
> **Note implementazione**: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py i18n add "changelog.notTranslated" --en "Not translated yet" --it "Non ancora tradotto" --fr "Pas encore traduit" --es "Aún sin traducir"`.
> - Diff: +2 −1 per catalogo, in coda al namespace `changelog`.
> - Prettier pulito; i 4 cataloghi hanno la stessa parità di chiavi (4 350).
> - `dev.py i18n audit`: l'unica chiave «Likely Unused» è `changelog.notTranslated`, com'è giusto finché non entra la modale.
> - Il gate `utils gate-i18n-usage` prova il classificatore su dati sintetici, non sul catalogo vero, quindi non diventa rosso.
> - Checkpoint a sé, FROZEN. Commit proposto `/tmp/libreFolio_commit_t_cl_key.txt`.

### CL — via al resto (coordinatore, 2026-10-12)
- CL-0 è nel target: `a8691bd27` (la chiave) e `0aca4948f` (il piano), treno 57, `dev_release2` = `37304d716`. Worktree in fast-forward lì, pulita.
- **Il contratto** del modulo `changelog.ts`: gli export di oggi restano invariati. Gli export nuovi:
  - `DisplayedChapter` (`ChangelogChapter` + `lang`);
  - `baseLanguage(locale)`;
  - `mergeChapters(english, translated, lang)`;
  - `translationLoaders(globRecord)`;
  - `createLocalizedChangelog(english, loaders)` → `{peek, load}`, dove `load` non va mai in errore e mette in cache solo i successi;
  - `changelogTranslationLoaders`, dal glob pigro `CHANGELOG.[a-z][a-z].md`;
  - `localizedChangelog`.
- **La modale**:
  - `$locale` → `baseLanguage`; `peek` subito, altrimenti caricamento (`changelog-loading`, `aria-busy`) e `load`, solo con la modale aperta;
  - `<section data-version lang>`;
  - la pillola `changelog-not-translated-{ci}`, col `lang` della UI, solo se il `lang` del capitolo è diverso da quello della UI;
  - `{@html sanitizeHtml(renderHighlighted(…))}` sulle 3 uscite, con l'output di marked in cache per corpo;
  - la voce di `htmlSink.gate.test.ts` per la modale si toglie: ora l'uscita è sanificata, e il gate lo verifica da sé.
- **Passi**:
  1. i rossi (test-author): Vitest node, jsdom, E2E con il blocco del runner;
  2. la cura;
  3. verdi, statici e build;
  4. la doc (docs-writer);
  5. il checkpoint.
- Deroga concessa dal coordinatore: un `CHANGELOG.it.md` sintetico, non tracciato, da cancellare subito dopo; nel checkpoint `git status` e un «Fuori pista». In più gli è stato assegnato `scripts/cli_base.py`, ma solo `check_frontend_needs_build()`.

#### CL passo 1 — i rossi ✅ (2026-10-12)
> **Note implementazione** (test-author; log in `/tmp/libreFolio_cl_reds_*.log`):
> - **`changelog.test.ts`** (node), righe 296–678: `baseLanguage`, `mergeChapters`, `translationLoaders`, `createLocalizedChangelog` e una guardia sui file tradotti veri, vuota oggi.
>   - La guardia controlla anche che i loader trovati corrispondano ai file su disco.
>   - Esito: **30 rossi**, per gli export mancanti; 23 test esistenti verdi.
> - **`ChangelogModal.test.ts`** (jsdom): un fake di `localizedChangelog` alle righe 58–165, i test CL alle righe 1030–1304.
>   - Esito: **8 rossi**: `data-version`, `changelog-loading`, `load` mai chiamato, la ricerca, l'espandi tutto, la sanificazione. 76 verdi.
> - **`AboutTab.test.ts`**: solo il mock, completato con `baseLanguage` e `localizedChangelog`.
> - **E2E nuovo** `e2e/layout/changelog-locale.spec.ts`:
>   - non dipende dal contenuto: legge `CHANGELOG.it.md` dal disco, e senza file si aspetta tutto in `en` con la pillola;
>   - solo desktop; la lingua passa dal selettore dell'header, cioè dal localStorage di quel contesto;
>   - esito: **2 rossi**, perché `data-version` è `null`.
> - **Runner**, `_frontend_utility.py`: `front_changelog_locale` (426–433) e `add_test` (624–632). Solo il blocco assegnato.
> - **`test_runtime_isolation.py`**: `TestFrontendBuildStaleness` (1803–1871), con un progetto finto e mtime fissati con `os.utime`.
>   - Esito: **2 rossi** (`CHANGELOG.md` e `CHANGELOG.it.md` più nuovi della build); 3 guardie e 153 test esistenti verdi.

#### CL passo 2 — la cura ✅ (2026-10-12)
> **Note implementazione** (`/tmp/libreFolio_tcl_apply.py`, sostituzioni esatte e controllate):
> - **`changelog.ts`**: l'intestazione, e dopo `CHANGELOG_REMOTE_URL`:
>   - `DisplayedChapter`, `baseLanguage`, `mergeChapters`;
>   - `translationLoaders`, con la regex `CHANGELOG.([a-z]{2}).md` e `en` escluso;
>   - `createLocalizedChangelog`: peek e load, una richiesta condivisa per lingua, cache dei soli successi, ripiego sull'inglese;
>   - `changelogTranslationLoaders`, dal glob pigro `CHANGELOG.[a-z][a-z].md`;
>   - `localizedChangelog`.
> - **`ChangelogModal.svelte`**:
>   - `uiLanguage`, poi `ready` / `chapters` / `loading`, ricavati da `peek` e dall'ultimo `load`;
>   - un `$effect` che carica solo a modale aperta;
>   - `changelog-loading` con `aria-busy`;
>   - `<section data-version lang>` e la pillola `changelog-not-translated-{ci}` col `lang` della UI;
>   - `{@html sanitizeHtml(renderHighlighted(…))}` sulle 3 uscite, e l'output di marked in cache per corpo.
> - **`htmlSink.gate.test.ts`**: tolta la voce della modale. Le uscite ora sono sanificate, e una voce che non copre più nulla farebbe fallire il gate.
> - **`scripts/cli_base.py`**: 2 righe fra gli input di `check_frontend_needs_build()`, `*sorted(project_root.glob("CHANGELOG*.md"))` con un commento. Limite noto: una cancellazione non si vede dagli mtime.
>
> **⚠️ Fuori pista**:
> - In `setAll` una variabile locale `chapters` oscurava il nuovo `$derived`: 3 rossi in component-unit, uno su un test preesistente. Rinominate le locali in `chapterFolds` e `sectionFolds`.
> - `scripts/cli_base.py` non è pulito per black già sulla base: 72 righe di diff di black, identiche prima e dopo, e nessuna è mia. Niente black sul file; ruff è pulito.

#### CL passo 3 — verdi, statici e build ✅ (2026-10-12)
> **Note implementazione**:
> - Tutto sulla 6164, in sequenza, con `bash /tmp/libreFolio_t1_run.sh`:
>   - `front-utility core-unit`: 121 file, **3 766 passed**;
>   - `front-utility component-unit`: 112 file, **2 992 passed**;
>   - `utils runtime-isolation`: **158 passed**;
>   - `check-orphans`: pulito (e2e 109, unit 347, backend 259, tutti raggiungibili);
>   - `front-utility changelog-locale`: **2 passed**.
> - `dev.py front check`: svelte-check con 0 errori e 0 avvisi. prettier pulito sui 7 file del frontend.
> - Alla fine la porta è libera.
>
> **⚠️ Fuori pista (deroga del coordinatore)**: un `CHANGELOG.it.md` sintetico, mai tracciato. Conteneva 1.1.0 con una data diversa, 1.0.1, e un capitolo orfano 0.9.0.
> - **Con il file**: `dev.py front build`.
>   - Il chunk pigro `_app/immutable/chunks/BtiW0acR.js` (438 byte) contiene il testo italiano.
>   - Il chunk inglese (`Bu-IDQsZ.js`, 148 KB) non contiene il marcatore e richiama l'altro per nome.
>   - E2E: **2 passed**, col ramo tradotto davvero esercitato: 1.1.0 e 1.0.1 attesi `it`, letti dal file.
> - **Dopo**: file cancellato e `dev.py front build` esplicito, perché la cancellazione non si vede dagli mtime.
>   - Nella build non resta nessun chunk italiano.
>   - E2E: **2 passed**, tutto `en` con la pillola.
>   - `git status` senza `CHANGELOG.it.md`.

#### CL passo 4 — la doc ✅ (2026-10-12)
> **Note implementazione** (docs-writer): `mkdocs_src/docs/user/settings/about.en.md`, §Changelog Modal.
> - La prima frase ora dice che la modale mostra il changelog nella lingua dell'interfaccia.
> - Un paragrafo nuovo dice che una release non ancora tradotta appare in inglese con l'etichetta **Not translated yet**, il valore EN di `changelog.notTranslated`.
> - Il `mkdocs build` stretto è verde, senza avvisi, con 3 012 URL relativi risolti.
> - Niente `translate-stamp`: it, fr ed es li traduce M. Il debito: la prima frase e il paragrafo nuovo, fra le due liste.
> - Effetto sul rendering: il paragrafo separa le due liste, che prima uscivano fuse in una sola.

### Checkpoint CL ✅ (2026-10-12) — committato dal coordinatore, treno 60
- Base `37304d716`. 11 file modificati e 1 nuovo, `e2e/layout/changelog-locale.spec.ts`.
- Quattro commit proposti:
  1. `feat(changelog)`: il codice, i test e il blocco del runner;
  2. `fix(runner)`: `cli_base.py` e `test_runtime_isolation.py`;
  3. `docs(user)`: `about.en.md`;
  4. `docs(journal)`: questo piano.
- Niente CHANGELOG. Il `CHANGELOG.it.md` sintetico è stato cancellato.

### Treno 60 (coordinatore, 2026-10-12)
- Il CHANGELOG localizzato è committato sul ramo di T: `8f67f89de`, `ee8a19384`, `b02bf6c54`, `fba291f53` (albero `7d4b685304f4`). Entra nel treno 60.

### M-18 — i numeri scritti con `toFixed`: analisi (2026-10-12) — superata dalla nuova regola qui sotto
> **Richiesta**: dal developer, via coordinatore, testuale: «T prende M-18 in parallelo: I resta sulla rifinitura UI».
> - Le fonti: il giro 12 di M, §11 (`27_releaseImages/plan-phase00TranslationRound12.prompt.md:658`, `:663`).
> - Base `fba291f53`, corsia 6164.

**Lo stato verificato**:
- Nel frontend ci sono 138 `toFixed`, fuori dai test.
- `formatPercent` (`utils/core/formatPercent.ts:71`) ha già l'opzione `locale`; senza, stampa la forma fissa `12.50%`. Ci sono 51 chiamate senza `locale`, in 16 file, che quindi stampano il punto: per esempio il «−10.7%» del laboratorio rischio. Altre 12 passano `$currentLanguage`.
- **Due regole convivono per la locale dei numeri.**
  - La locale della macchina: gli importi (`currencyFormat.ts:39`, `:61`, `toLocaleString(undefined…)`), le date (`formatDateTime.ts:16-18`) e gli assi dei lotti. Quest'ultima la scrive `lotChartShared.ts:85-90`: «the machine locale, which is what both charts deliberately use for numbers (as opposed to `$currentLanguage`, which they use for words)».
  - La lingua della UI: le 12 chiamate di `formatPercent` con `$currentLanguage` (`DistributionEditor`, `BrokerSharingPanel`, `BrokerCard`, la pagina del broker) e il PAC.
- I test seguono la macchina, cioè en-US qui e in CI. `currencyFormat.test.ts:39` calcola l'atteso con lo stesso `toLocaleString(undefined…)`.
- Con Intl, en-US resta com'è (`14.07%`) salvo il raggruppamento da 1 000 % in su. Le altre lingue:
  - it: `14,07%`;
  - fr: `14,07 %`, con uno spazio stretto;
  - es: `14,07 %`.

**L'inventario**: script `/tmp/libreFolio_m18_classify.py`, dati `/tmp/libreFolio_m18_inventory.json`. «ᶠᵖ» = chiamata a `formatPercent` senza `locale`; «†» = file nato dopo la 1.1.
### Percentuali — 99 punti, 46 file
- `components/assets/AssetCard.svelte`: 236
- `components/assets/AssetPriceSummary.svelte`: 117
- `components/assets/ProviderComparisonModal.svelte`: 228
- `components/brokers/lots/LotComparisonChart.svelte`: 642ᶠᵖ,859ᶠᵖ
- `components/brokers/lots/LotCustodyModal.svelte`: 353ᶠᵖ,358ᶠᵖ,389ᶠᵖ,401ᶠᵖ
- `components/brokers/lots/LotWacPriceChart.svelte`: 1047ᶠᵖ,1473ᶠᵖ,1608
- `components/brokers/lots/UnifiedLotsTable.svelte`: 216ᶠᵖ
- `components/brokers/lots/unifiedLotsTableHelpers.ts`: 88ᶠᵖ
- `components/charts/GeographyMap.svelte`: 292
- `components/charts/LineChart.svelte`: 673
- `components/charts/MeasurePanel.svelte`: 296,303,308
- `components/charts/ScatterChart.svelte` †: 110ᶠᵖ,151ᶠᵖ
- `components/charts/SemiDonutChart.svelte`: 236,251
- `components/charts/candlestickChartHelpers.ts`: 92
- `components/charts/chartCoreHelpers.ts`: 87
- `components/charts/echartsTooltipHelpers.ts`: 94,126
- `components/charts/priceChartHelpers.ts`: 573,578
- `components/dashboard/AllocationHistoryChart.svelte`: 597
- `components/dashboard/ContributionTable.svelte`: 188
- `components/dashboard/ExposureTable.svelte`: 143,363
- `components/dashboard/ExposureTreemap.svelte`: 591,598
- `components/dashboard/GrowthChart.svelte`: 2113,2314
- `components/dashboard/KpiCard.svelte`: 70
- `components/dashboard/KpiSection.svelte`: 252,253,254,255,268,299ᶠᵖ,351ᶠᵖ
- `components/dashboard/YieldOnCostCell.svelte` †: 100,134
- `components/fx/FxCard.svelte`: 224
- `components/fx/FxPriceSummary.svelte`: 46
- `components/fx/FxTable.svelte`: 122
- `components/risk/AssetRiskScenariosView.svelte`: 56
- `components/risk/AssetSetLossComparisonSection.svelte` †: 107ᶠᵖ,112ᶠᵖ
- `components/risk/CorrelationHeatmap.svelte`: 489
- `components/risk/RiskAnalysisPanel.svelte`: 654ᶠᵖ,655ᶠᵖ,677ᶠᵖ,678ᶠᵖ,688ᶠᵖ,699ᶠᵖ,700ᶠᵖ,733ᶠᵖ,734ᶠᵖ,817ᶠᵖ,835ᶠᵖ,836ᶠᵖ,871ᶠᵖ,873ᶠᵖ,874ᶠᵖ,948ᶠᵖ,1063ᶠᵖ,1064ᶠᵖ,1065ᶠᵖ,1074ᶠᵖ,1075ᶠᵖ,1076ᶠᵖ,1077ᶠᵖ
- `components/risk/RiskResultFrame.svelte`: 43
- `components/risk/RiskReturnLevel.svelte` †: 107ᶠᵖ,112ᶠᵖ
- `components/risk/levels/L1HowMuchItHurts.svelte` †: 91ᶠᵖ
- `components/risk/levels/L2Diversification.svelte` †: 197ᶠᵖ,224ᶠᵖ
- `components/risk/levels/RiskLevelSection.svelte` †: 249
- `components/risk/levels/RiskLevelsPanel.svelte` †: 312,313
- `components/risk/levels/l1/UnderwaterChart.svelte` †: 50ᶠᵖ
- `components/risk/levels/l1/l1Helpers.ts` †: 195ᶠᵖ
- `components/risk/levels/l4/L4Replay.svelte` †: 274
- `components/risk/levels/l4/L4Shock.svelte` †: 164,175
- `components/risk/levels/l4/L4Simulation.svelte` †: 143,218
- `components/risk/levels/shareFormat.ts` †: 25ᶠᵖ,27ᶠᵖ,31ᶠᵖ
- `features/tools/pac-allocator/planner/format.ts` †: 225ᶠᵖ,233ᶠᵖ
- `utils/currency/fxConversionHelper.ts`: 126

### Byte — 3 punti, 1 file
- `utils/files/upload.ts`: 57,58,59

### Durate — 5 punti, 4 file
- `components/assets/ProviderAssignmentSection.svelte`: 585,616
- `components/settings/CachePanel.svelte`: 92
- `components/settings/SchedulerLogModal.svelte`: 235
- `utils/sync/syncHelpers.ts`: 110

### Altri decimali mostrati — 56 punti, 29 file
- `components/assets/AssetCard.svelte`: 223,230
- `components/assets/AssetPriceSummary.svelte`: 96,109
- `components/assets/AssetTable.svelte`: 115
- `components/assets/ProviderAssignmentSection.svelte`: 333
- `components/assets/providerProbe.ts`: 115,126
- `components/charts/CandlestickChart.svelte`: 513
- `components/charts/LineChart.svelte`: 675,676,677,757,768
- `components/charts/MeasurePanel.svelte`: 297,298,530
- `components/charts/PriceChartFull.svelte`: 782,785,850,1011
- `components/charts/candlestickChartHelpers.ts`: 93,94,95,100
- `components/charts/chartCoreHelpers.ts`: 89,90,91,264,265,266
- `components/dashboard/KpiSection.svelte`: 138
- `components/fx/FxCard.svelte`: 219
- `components/fx/FxPriceSummary.svelte`: 39
- `components/fx/FxTable.svelte`: 116,188
- `components/risk/AssetRiskScenariosView.svelte`: 57
- `components/risk/CorrelationHeatmap.svelte`: 487,506
- `components/risk/CorrelationPairsList.svelte` †: 91
- `components/risk/RiskResultFrame.svelte`: 48
- `components/risk/levels/RiskLevelSection.svelte` †: 255
- `components/risk/riskAnalysisHelpers.ts`: 142
- `components/transactions/events/AssetEventPicker.svelte`: 179
- `components/transactions/events/EventCreateMiniModal.svelte`: 157
- `components/transactions/modals/ImportWizardModal.svelte`: 2345
- `components/transactions/modals/TransactionBulkModal.svelte`: 1908,1913,3432
- `components/transactions/modals/TransactionFormModal.svelte`: 1701
- `components/transactions/wac/WacPreviewSection.svelte`: 314,567,588
- `utils/currency/fxConversionHelper.ts`: 116,118
- `utils/transactions/pairCellHtml.ts` †: 24

### Interni (restano) — 26 punti, 17 file
- `components/assets/scheduleSerialization.ts`: 119,127
- `components/charts/geographyMapHelpers.ts`: 38,71
- `components/risk/levels/l1/l1Helpers.ts` †: 35,196
- `components/risk/levels/l4/L4Shock.svelte` †: 144
- `components/risk/levels/l4/TornadoChart.svelte` †: 89
- `components/risk/levels/shareFormat.ts` †: 30
- `components/transactions/events/EventCreateMiniModal.svelte`: 76,86
- `components/transactions/modals/ImportWizardModal.svelte`: 1648,1782
- `components/ui/TweenedValue.svelte`: 17,56
- `components/ui/input/DistributionEditor.svelte`: 193,277,386
- `components/ui/media/ImageEditModal.svelte`: 419
- `features/tools/pac-allocator/planner/result/model.ts` †: 152
- `features/tools/pac-allocator/planner/steps/AssetEditor.svelte` †: 102
- `utils/core/formatPercent.ts`: 78
- `utils/core/parseDecimalInput.ts`: 110
- `utils/transactions/importDedup.ts`: 180
- `utils/transactions/splitRowCharges.ts`: 72,86

Correzioni al conteggio automatico:
- `KpiSection.svelte:138` (`absRoiPct`) è una percentuale, perché la riga `:382` la stampa con «%».
- In `UnifiedLotsTable.svelte` la chiamata vera è a `:89`, `sharedFormatPercent(value, {scale: 100})`. La riga `:216` usa l'alias.

**La proposta**:
1. **La locale dei numeri**: quella della macchina, come gli importi e le date. Così una percentuale non si scontra con l'importo che ha accanto («+4788,01 €» / «14,07%»), qualunque sia la coppia fra browser e lingua della UI.
2. **Un punto solo per la regola**: `utils/core/numberLocale.ts` → `numberLocale()`, che oggi restituisce `undefined`, cioè la macchina.
   - I test lo mockano a `fr` o `it` per i rossi.
   - Se un giorno la regola diventa la lingua della UI, si cambia lì.
3. **`formatPercent`**: senza `locale` usa `numberLocale()` e localizza.
   - Le 51 chiamate senza `locale` si correggono senza toccarle. Fra queste c'è `UnifiedLotsTable.svelte:89`, quindi il file di I non si tocca.
   - La forma fissa non serve a nessun export: l'unico clipboard dei lotti copia l'id.
4. **`formatFixed(value, digits, {signed, locale})`**: un file nuovo in `utils/core/`, cioè il `toFixed` localizzato. Lo usano i byte, le durate e gli altri decimali.
5. **Le 48 percentuali scritte a mano** passano a `formatPercent`, con `scale`, `digits`, `signed` e `suffix` del sito. Il segno `−` (U+2212) del rischio si tiene.
6. **I byte**: `formatBytes` usa `formatFixed`, con le etichette di oggi. **Le durate**: `formatFixed` più il simbolo di oggi (`s`, `h`). Nessuna chiave i18n nuova.
7. **Gli interni restano**: 26 punti, fra input, chiavi, payload, CSS, confronti e dati numerici dei grafici.

**Da decidere**:
- (a) La macchina, come consiglio, oppure la lingua della UI. La seconda vorrebbe dire cambiare anche importi e date: fuori portata.
- (b) Le 12 chiamate con `$currentLanguage`: allinearle alla regola (consiglio) oppure lasciarle.
- (c) Gli altri decimali (56) adesso, come consiglio, perché nella stessa card il tasso e la variazione % si scontrerebbero; oppure dopo la 1.2.
- (d) Anche `currencyFormat.ts:39`, `:61` passa per `numberLocale()`: nessun cambio di comportamento, una sola fonte.

**I test** (test-author, prima i rossi):
- Unità (node): `formatFixed`; il default di `formatPercent` con `numberLocale` mockato; `formatBytes`; `formatElapsed`.
- Componenti (jsdom), uno per famiglia, con `numberLocale` = `fr` o `it`:
  - percentuali: `KpiSection`;
  - byte: una cella di dimensione;
  - durate: `SyncResultRow`;
  - altri decimali: `FxCard`.
- Da aggiornare: `formatPercent.test.ts`, che oggi fissa la forma senza locale.

**La stima**: circa 1 giorno; 4–5 h in meno se gli altri decimali vanno dopo la 1.2.

**I conflitti**:
- `UnifiedLotsTable.svelte`: nessuna riga, grazie al punto 3.
- `KpiSection.svelte`: le righe `:138`, `:252-255`, `:268`, `:382`, non la `:304` di V.
- I cataloghi: nessuna chiave nuova.
- La galleria di M: le percentuali in it, fr ed es cambiano negli scatti.

**Il CHANGELOG 🐛**: i punti che c'erano nella 1.1.
- In 1.1: la dashboard (KPI, esposizione, contributi, crescita, allocazione), i grafici di prezzo, linea e candele con la misura, asset e FX (card, tabelle, riepiloghi), i lotti (custodia, grafici WAC e confronto, tabella), le transazioni (WAC, cambio, modali), le dimensioni dei file, il registro dello scheduler e le durate dei sync, la cache, il pannello di analisi del rischio e la heatmap delle correlazioni.
- Nati nella 1.2: i livelli di rischio L1–L4, lo scatter, lo Yield on Cost e il PAC.

### M-18 — nuova regola: la lingua della UI per tutto (developer, 2026-10-12)
> **Decisione** del developer, testuale: «Lingua della UI per tutto, importi e date compresi: lavoro più grande, con più rischio sulla 1.2».
> - Del coordinatore: (b) le 12 chiamate con `$currentLanguage` passano dalla fonte unica; (c) i 56 decimali si fanno adesso; (d) `currencyFormat` passa dalla fonte unica.
> - **Analisi rifatta, senza codice**, letta sul target `55304116f` con `git grep` in sola lettura: il target ha 12 file del frontend che mancano alla mia base (`responsiveXAxis.ts`, i grafici). Script `/tmp/libreFolio_m18b_grep.sh`.

**1. La fonte unica**: `uiLocale()`, in un modulo `.svelte.ts` che legge `currentLanguage` con `fromStore`, così è reattiva.
- **La mappa**: lingua della UI L, tag principale del browser B (`navigator.language`).
  - Se la lingua di B è L, si usa B, con la sua regione.
  - Altrimenti si usa il default di L: `it`, `fr`, `es`, e per l'inglese **`en-GB`** (proposta).
  - Si guarda solo il tag principale: Chrome mette `en-US` come lingua secondaria a quasi tutti, e un italiano con la UI inglese finirebbe nelle convenzioni americane.
- **Le conseguenze sulle date**, provate con Node:
  - `en` da solo equivale a en-US: `10/12/2026`, `Oct 12, 2026`, `2:05 PM`;
  - en-GB: `12/10/2026`, `12 Oct 2026`, `14:05`;
  - i numeri sono identici nei due casi.
- **Le regioni contano anche per i numeri**:
  - it-CH `4788.01` (col punto);
  - fr-CH `4'788,01`;
  - es-MX `4,788.01`;
  - fr-CA ha le date `2026-10-12`.
- **La galleria** (`GALLERY_LOCALES`: en-US, it-IT, fr-FR, es-ES) dà lo stesso risultato della lingua da sola: importi e date negli scatti non cambiano.
- **Il segno meno** è ASCII in tutte e quattro le lingue e nelle loro regioni comuni. U+2212 compare solo in locale che non sono della UI, come lo svedese.

**2. La reattività**
- Con i formattatori che leggono `uiLocale()` per default, ogni chiamata fatta in un template, in un `$derived` o in un `$effect` segue il cambio di lingua senza toccare il sito: le 52+13 di `currencyFormat`, le 64 di `formatPercent` e le altre. Il badge della quota (`brokers-detail.spec.ts:1644`, `:1655`) funziona già così.
- **Dove la lettura va resa esplicita**:
  - **I grafici**: l'effect che costruisce le opzioni deve leggere la locale, perché i formatter di ECharts girano fuori dal tracciamento.
    - Cinque grafici oggi non dipendono da nessuna lingua: `AllocationPieChart`, `GeographyMap`, `ScatterChart`†, `SemiDonutChart`, `ExposureBars`†.
    - Gli altri 12 leggono `$currentLanguage` o `$locale`: passano a `uiLocale()`, e per ognuno va verificato che la lettura stia dentro l'effect.
  - **Le stringhe costruite in un callback asincrono e salvate in `$state`** restano nella lingua di quel momento. Sono transitorie: il dettaglio della sonda (`ProviderAssignmentSection:333`) e i toast.
- Nessun `$:` legacy e nessuno store Svelte 4 formatta numeri o date: ho cercato, sono 0.

**3. L'inventario esteso** (†: nato nella 1.2)
- **Importi**:
  - `currencyFormat.ts:39`, `:61`, con 65 chiamate in 27 file che non si toccano;
  - 15 `toLocaleString(undefined…)` o `Intl.NumberFormat(undefined…)`: `LotGanttChart:283`, `ExposureTable:153`, `GrowthChart:2130`, `:2166`, `KpiSection:347`, `PerformanceChart:175`, `:188`, `:194`, `DataTableColumnFilter:170`, `:171`, `FixFlaggedStep:426`, `txDisplayHelpers:20`, `DataEditor:205`, `planner/format.ts`†`:254`, `resolveValidationMessage:193`;
  - senza argomenti: `RiskAnalysisPanel:122`.
- **Date**:
  - `formatDateTime.ts`, 3 chiamate;
  - 9 siti con `undefined`: `SchedulerLogModal:222`, `dataTableLogic:328`, `:344`, `AssetEventPicker:188`, `EventCreateMiniModal:155`, `ImportWizardModal:3773`, `TransactionBulkModal:1900`, `:1901`, `importReportSets`†`:287`, la pagina del broker `:443`;
  - 5 senza argomenti: `dataTableLogic:326`, `:342`, `GlobalSettingsTab:726` («Last updated:», M-17), `:755`, la pagina dell'asset `:3524`;
  - fissi: `DataEditor:106` (`'en-US'`, i giorni della settimana) e `DateRangePicker:1109` (`'en'`, M-17).
- **Siti già nella lingua della UI, da far passare dalla fonte**: 27.
  - assi: `formatAxisDate` (5 chiamate), `formatAxisNumber` (3);
  - lotti: `lotComparisonChartHelpers:206`, `:222`, `lotGanttChartHelpers:105`, `unifiedLotsTableHelpers:63`;
  - grafici: `priceChartHelpers:216`, `responsiveXAxis`†`:48`, `growthLadderAxis`†`:169`, `GrowthChart:1356`;
  - rischio: `eligibility`†`:124`, `TornadoChart`†`:63`, `scenarioHelpers`†`:384`, `:389`, `riskAnalysisHelpers:166`;
  - `ProfileTab:23`;
  - PAC e Tool: `planner/format`†`:286`, `:304`, `KpiCards`†`:115-118`, `BackendTimingBar`†`:79-80`, `ToolDiagnosticsPanel`†`:65`, `ToolExecutionMetrics`†`:37`;
  - `aiExportOptions:81`;
  - `LotComparisonChart:229`, `:235`, `:384`, `LotCustodyModal:68`, `LotGanttChart:258`, `AllocationHistoryChart:548`.
- **Assi**: `lotChartShared.ts:85-98`, dove la regola «numeri dalla macchina» va riscritta; `responsiveXAxis`†, che nomina già i giorni nella lingua dell'app, passa dalla fonte; le cifre degli assi della famiglia N, cioè `chartCoreHelpers`, `LineChart`, `PriceChartFull` e `Candlestick`.
- **Il prompt dell'AI Export**: nessuna formattazione con la locale. `snapshotDataRenderer:226` usa `'en'` solo per leggere le cifre minori di una valuta, e resta così. I byte del prompt non cambiano; li sorvegliano `promptRenderer.test` e la sonda.
- **PDF ed export**: nel frontend non ce ne sono. Il backup è binario, e i clipboard copiano id, URL, il prompt e le info di sistema.
- **I date picker**:
  - i nomi dei mesi e dei giorni vengono dalle chiavi i18n e vanno bene;
  - `DateRangePicker:1109` passa dalla fonte (sovrapposizione con M-17);
  - gli `<input type="date">` nativi (`RiskAnalysisPanel:902`, `:906`) seguono il browser: è un limite noto.
- **Le famiglie della prima analisi** restano tutte: percentuali (48 a mano, 51 di default, 12 con `$currentLanguage`), byte (3), durate (5), altri decimali (56), interni (26).
- **Documentazione da riscrivere**: `lotChartShared.ts:85-90`, `formatDateTime.ts:16-18` e `L2Diversification.svelte:211`, che chiama questo «a known debt».

**4. I test**
- **Da rifare**:
  - `formatPercent.test.ts`, 34 asserzioni: senza `locale` la forma non è più fissa;
  - `GrowthChart.test.ts`: il contratto D23/D23b «la locale del browser», con `inLocale` che modifica `Number.prototype.toLocaleString`, diventa quello della UI;
  - `currencyFormat.test.ts` calcola l'atteso con `undefined`: va calcolato con la fonte. In inglese l'esito è identico.
- **Restano validi**:
  - i 2 E2E del badge: `fr` col browser en-US dà `fr` da solo, come `$currentLanguage` oggi;
  - `growthLadderAxis.test` e `TornadoChart.test`, che usano locale esplicite;
  - il prezzo live di `asset-detail`, la cui describe è in inglese;
  - gli altri E2E che passano a it, fr o es, che non asseriscono numeri né date.
- **La galleria**: importi e date non cambiano. Percentuali, byte, durate e decimali sì, in it, fr ed es.
- **Rossi nuovi**:
  - la mappa;
  - uno per famiglia, in it o fr col browser en-US: percentuali, byte, durate, decimali, importi, date, assi;
  - la reattività: un test di componente, e un E2E della dashboard da en a it che controlla importo e percentuale di un KPI.

**5. Stima, rischi e taglio**
- **CP1**, circa 1 giorno: la fonte, poi percentuali, byte, durate e i decimali fuori dai grafici.
- **CP2**, circa 1,5 giorni: importi, date, assi, il ridisegno dei grafici, le cifre dei grafici e i contratti dei test.
- **Rischi**:
  - l'ampiezza: circa 400 siti, toccati per lo più attraverso i default;
  - la scelta per l'inglese (en-US o en-GB);
  - qualche grafico che non si ridisegna;
  - i contratti D23 di GrowthChart e dei lotti, cioè il piano 47 di I;
  - un cambio visibile per chi ha browser e UI diversi, ed è voluto;
  - gli input data nativi.

#### M-18 — aggiunta: M-17 passa a T, e i file di I (coordinatore, 2026-10-12)
- **M-17** (🐛, c'era già nella 1.1.0) entra nel perimetro.
  - `DateRangePicker.svelte:1109`: il `'en'` fisso passa a `uiLocale()`.
  - `GlobalSettingsTab.svelte:726`: «Last updated:» diventa `{$_('common.updated')}:`. La chiave esiste in tutti e 4 i cataloghi («Updated», «Aggiornato», «Mis à jour», «Actualizado»): nessuna chiave nuova.
  - Le date di `GlobalSettingsTab.svelte:726` e `:755` passano dalla fonte.
  - `DataEditor.svelte:106`: il giorno della settimana, oggi `'en-US'`, passa dalla fonte.
  - Le altre date trovate da I erano già nell'inventario esteso.
- **I file di I** (per circa 2 giorni) e le mie righe, lette sul target:
  - `ConnectionSecurityIndicator`, `utils/clipboard.ts`, `AboutTab`, `AskAdminModal`, `FilesTable`: nessuna riga mia.
  - `BrokerIcon`, `brokerIconChain` e `ImportBrokerMismatchModal` non esistono sul target: sono file nuovi di I, nessuna riga mia.
  - `FilePreviewModal:123` (`formatBytes`), `FileGrid:73` (`formatDateTime`) e `:177` (`formatBytes`), `UnifiedLotsTable` (`formatCurrencyAmountPlain` e `formatPercent`): passano dai default dei formattatori, **senza modifiche**.
  - `ProviderAssignmentSection`: le righe **`:333`** (prezzo), **`:585`** e **`:616`** (durate). Le sposto nel CP2, su una base che contiene il cambio di I a `:591-596`.
- **Così il CP1 non tocca nessun file di I.**
- **M-17 nel CP2**, con le altre date. Se lo vuoi prima, può entrare nel CP1: i suoi 3 file non sono di I.
- **CHANGELOG**: la riga 🐛 di I, «The date range picker and the settings dates follow the app's language», si può fondere con la 🐛 di M-18; più una riga 🔄 per chi ha browser e UI in lingue diverse.

### M-18 CP1 — via libera (coordinatore, 2026-10-12)
- **Decisioni**: l'inglese senza regione ripiega su `en-GB` (developer); si usa solo il tag principale del browser (coordinatore); M-17 e `ProviderAssignmentSection` vanno nel CP2.
- Base `55304116f`: il coordinatore mi ha fatto avanzare in fast-forward; il piano è rimasto modificato. Il CP1 non tocca nessun file di I.
- **Note di I**, recepite:
  - in un componente **legacy** la lettura dentro un helper è untracked (wiki `problems/legacy-component-language-untracked`);
  - `formatBytes` ha le unità con `get(_)`;
  - test: si monta in `en`, poi `currentLanguage.set('it')`, e l'atteso si calcola con `Intl`.
- **Il disegno del CP1**:
  1. `stores/app/uiLocale.ts`:
     - `resolveUiLocale(lingua, tagBrowser)` è pura. Se la lingua coincide si tiene il tag; altrimenti `en` → `en-GB`, e le altre lingue restano da sole;
     - `uiLocaleStore` = `derived(currentLanguage, …)` serve ai template **legacy** (`$uiLocaleStore`);
     - `uiLocale()` = `fromStore(uiLocaleStore).current` serve al codice runes e ai default dei formattatori.
  2. `utils/core/formatFixed.ts`: `formatFixed(value, digits, {signed, locale = uiLocale()})`, cioè il `toFixed` localizzato.
  3. `formatPercent`: `locale = uiLocale()` per default; il `%` passa da `Intl`, le altre unità da `formatFixed`. La forma fissa non c'è più.
  4. `formatBytes(bytes, translate, locale = uiLocale())` e le durate passano da `formatFixed`.
  5. Le 12 chiamate con `$currentLanguage`:
     - nei componenti runes (`DistributionEditor` ×4, `BrokerSharingPanel` ×6) si toglie l'argomento;
     - in quelli legacy (`BrokerCard`, la pagina del broker) diventa `$uiLocaleStore`.
  6. I `formatBytes` nei legacy (`FileUploader`, `FileEditModal`, la pagina `files`) ricevono `$_` e `$uiLocaleStore` nel template.
  7. I 70 `toFixed` del CP1, in 35 file, passano a `formatPercent` o `formatFixed`.
- Chiesta al coordinatore l'assegnazione di `_frontend_utility.py`, solo per aggiungere i Vitest nuovi alle liste.

#### M-18 CP1 — blocco ambiente (2026-10-12, 17:23)
> **⚠️ Fuori pista (ambiente, non codice)**: il `brew upgrade` del developer ha rotto `node` (`dyld: Library not loaded: libsimdjson.33.dylib`).
> - Per ordine del coordinatore, niente comandi frontend nuovi; un rosso con quell'errore è dell'ambiente.
> - Ho detto a test-author di fermare i comandi e di riferire quali rossi ha già visto prima del guasto.
> - La cura (`/tmp/libreFolio_m18_cp1_apply.py`, 42 file, e `/tmp/libreFolio_m18_cp1_core.py`) è pronta e la prova a secco è passata, ma **non l'applico** finché ogni rosso non è stato visto rosso.
> - Nota dal coordinatore: T-SG e T-DI sono già nella mia sezione del backlog (`bf831ef10`). Non vanno duplicate; le voci nuove vanno in fondo.

#### M-18 CP1 passo 1 — i rossi ✅ (2026-10-12)
> **Note implementazione** (test-author): tutti i rossi visti rossi su `node` sano (v26.11.1), in sequenza fra le 17:41 e le 17:46. Log in `/tmp/libreFolio_m18_reds_final_*.log`.
> - **Runner**:
>   - `front-utility core-unit`: 7 rossi (`formatPercent.test.ts`), 3 767 passed;
>   - `front-utility component-unit`: 4 rossi (`KpiSection` ×2, `SyncResultRow` ×2), 2 994 passed;
>   - `front-portfolio risk-frame-component`: 2 rossi (`RiskResultFrame`), 18 passed.
> - **File nuovi**, con `node_modules/.bin/vitest run`: 34 rossi e 2 controlli verdi. I file sono `stores/app/uiLocale.test.ts`, `utils/core/__tests__/formatFixed.test.ts` e `utils/files/upload.test.ts` (node), e `components/ui/media/FileEditModal.test.ts` (jsdom, legacy).
> - **I motivi**:
>   - la forma inglese fissa (`'+12.50%'` invece di `'+12,50 %'`; `'1234.50%'` invece di `'1,234.50%'`);
>   - i moduli mancanti;
>   - nessun aggiornamento quando la lingua cambia sul posto.
> - **Indicazioni per la cura**:
>   - per il `%`, pre-arrotondare come `toFixed`: altrimenti `formatPercent(1.2345, {digits: 3})` dà `+1.235%`;
>   - nei template legacy servono **sia** `$_` **sia** `$uiLocaleStore`, perché il catalogo francese arriva dopo il cambio di lingua;
>   - `KpiSection.test.ts:212` (`'+20000.00%'`) va aggiornato al raggruppamento.
>
> **⚠️ Fuori pista**: nella finestra del guasto è fallita una sola corsa, `component-unit` alle 17:21:30, per `dyld`. È stata ripetuta.

#### M-18 CP1 passi 2–4 — cura, verdi, E2E ✅ (2026-10-12)
> **Note implementazione**:
> - **La cura**:
>   - `/tmp/libreFolio_m18_cp1_core.py`: i moduli nuovi `stores/app/uiLocale.ts` e `utils/core/formatFixed.ts`; `formatPercent` con `locale = uiLocale()`;
>   - `/tmp/libreFolio_m18_cp1_apply.py`: 42 file, cioè i 70 `toFixed`, le 12 chiamate con `$currentLanguage` e i `formatBytes` legacy con `$t`/`$_` e `$uiLocaleStore`.
>   - Dopo la cura restano solo i `toFixed` interni del CP1: `L4Shock:145`, `EventCreateMiniModal:77,87` e `ImportWizardModal:1649,1783`.
>   - Nessun file di I toccato.
> - **Runner**: in `_frontend_utility.py`, core-unit + `formatFixed.test.ts`, `uiLocale.test.ts`, `upload.test.ts`; component-unit + `FileEditModal.test.ts`, `FileUploader.test.ts`.
> - **Verdi** (6164, in sequenza): 19 azioni Vitest, circa 10 930 test.
>   - core-unit 124 file, **3 825**; component-unit 114 file, **3 006**; risk-frame-component 20.
>   - Più le altre 16 azioni Vitest di ai-export, asset, broker, fx, portfolio, transaction, user e onboarding, tutte verdi.
>   - `check-orphans` pulito. `dev.py front check`: 0 errori e 0 avvisi. Prettier pulito su tutti i file.
> - **E2E** (6164):
>   - il badge della quota in `brokers-detail`: 2 passed (in francese all'apertura, e passando in francese sul posto);
>   - `asset-classification`: 4 passed;
>   - `tx-import-asset-inspector`: 5 passed.
> - **Sovrapposizioni**: il target è ora a `0c8412745` (treno 67) e ha cambiato 418 file, nessuno dei miei. Non aggiunge `toFixed`, non passa `$currentLanguage` a `formatPercent` e non ha mock parziali nuovi di `$lib/i18n`.
>
> **⚠️ Fuori pista**:
> - **Arrotondamento**: Intl arrotonda il decimale più corto che rilegge il valore (`1.45` → `1.5`), mentre `toFixed` arrotonda il valore stesso (`1.4`). Quindi `formatFixed` e `formatPercent` pre-arrotondano con `toFixed`. Per il `%` serve anche a evitare lo spostamento dato da `/100` (`1.2345` a tre cifre).
> - **Negativo minuscolo**: resta `-0.00` / `-0.00%`, come con `toFixed` (`formatPercent.test.ts:65`). Ho tolto un `|| 0`.
> - **Riparazioni di test** (test-author):
>   - il registro di `moneyRenderSites`: due snippet riscritti;
>   - il mock di `$lib/i18n` in `SchedulerLogModal.test.ts`, ora parziale con `importOriginal`;
>   - `MeasurePanel.test.ts:346` → `'1,000.0000'`;
>   - `KpiSection.test.ts:212` → `'+20,000.00%'`;
>   - le descrizioni di `formatPercent.test.ts:166` e `:212`.
> - **`FileUploader.test.ts`** è arrivato dopo la cura. Per vederlo rosso ho tolto per poco `$t, $uiLocaleStore` da `FileUploader.svelte:242`: i 2 test del cambio sul posto sono falliti, il controllo e il montaggio in italiano no. Poi ho rimesso la riga e verificato.
> - **Il segno sullo zero**: le percentuali e i decimali scritti a mano mettevano `+` anche sullo zero (`+0.00%`). Ora seguono la regola condivisa di `formatPercent`: niente segno sullo zero. Nessun test del CP1 lo fissava. I rischi del livello L4 tengono il loro `−`/`+`.

### Checkpoint M-18 CP1 🧊 (2026-10-12) — inviato dopo «riparti» (19:24), FROZEN fino al commit
- Base `55304116f`. 52 file modificati e 7 nuovi; nessuno è di I.
- Due commit proposti:
  1. `fix(i18n): write figures in the interface language`: codice, test e righe del runner (`/tmp/libreFolio_commit_t_m18cp1_1.txt`);
  2. `docs(journal): record M-18 CP1`: questo piano (`/tmp/libreFolio_commit_t_m18cp1_2.txt`).
- I testi del CHANGELOG li scrive il coordinatore all'integrazione; le proposte sono nel messaggio.
- **Trovato rileggendo, per il CP2** (⚠️ scarto dalla regola del developer):
  - con un browser il cui tag primario è un `en` nudo, `resolveUiLocale` (`uiLocale.ts:42`) tiene `en`, e `en` scrive le date all'americana (10/12/2026, 2:05 PM). La regola dice: inglese senza regione → `en-GB`;
  - nel CP1 non si vede: per numeri, percentuali, byte e durate `en`, `en-GB` ed `en-US` scrivono uguale;
  - **cura, primo passo del CP2**, col suo rosso via test-author: tenere il tag del browser solo se porta una regione.
- Restano per il CP2:
  - importi, date e assi, con il ridisegno dei grafici;
  - M-17;
  - `ProviderAssignmentSection` (`:333`, `:352`, `:585`, `:616`);
  - le cifre dei grafici;
  - la regola in `lotChartShared.ts:85-90`, `formatDateTime.ts:16-18` e `L2Diversification.svelte:211`.

### ⏸️ STOP del developer (2026-10-12) — FROZEN fino a «riparti»
- **Fatto**:
  - il CP1 è completo e verde (§M-18 CP1, passi 2–4);
  - dopo il passo 4, altri tre E2E sulla 6164, tutti verdi: `front-portfolio risk` 38 passed, `front-portfolio risk-lab` 44 passed, `front-transaction tx-fx-implied-rate` 3 passed (log `/tmp/libreFolio_t1_m18cp1e2e2_*`);
  - il materiale del checkpoint, in `/tmp`: il manifest (`libreFolio_m18cp1_manifest.final.txt`, 59 blob) e i due messaggi di commit (`libreFolio_commit_t_m18cp1_{1,2}.txt`, ASCII).
- **A metà**:
  - il checkpoint CP1 non è stato inviato al coordinatore;
  - il blob del piano nel manifest è vecchio: questa nota cambia il file, quindi va ricalcolato prima dell'invio.
- **Trovato, da decidere** (il file non è mio):
  - la guardia `frontend/e2e/fixtures/galleryReportSets.ts:565` (`expectOfflinePricesDrawn`, scatto «Asset list page» della galleria) si aspetta sulla card il prezzo scritto con `Number(price.value).toFixed(2)`;
  - con il CP1 la card lo scrive con `formatFixed`, nella lingua della UI. Quindi la guardia diventa rossa:
    - in it, fr ed es sempre;
    - in inglese per i prezzi da 1 000 in su (`4116.60` → `4,116.60`, `10956.03` → `10,956.03`).
  - Le altre E2E che fissano cifre usano valori sotto 1 000 con la UI inglese e il browser en-US, quindi non cambiano.
  - **Cura proposta**, una riga. Due strade:
    - confrontare le sole cifre (`replace(/\D/g, '')`), come fa già `tx-import-degiro.spec.ts:583-584`;
    - oppure formattare il prezzo atteso con `GALLERY_LOCALES[lang]`.
  - La docstring di `galleryLocale.ts:4-7` («the app formats with it wherever it passes no locale») invecchia con il CP2: la aggiorna M.
- **Prossimo passo, dopo «riparti»**:
  1. ricalcolare il blob del piano nel manifest e inviare il checkpoint CP1, con le proposte per il CHANGELOG e la guardia della galleria;
  2. restare FROZEN fino all'integrazione;
  3. poi il CP2.
- **Stato**:
  - nessun server; porta 6164 libera; nessun sotto-agente in volo;
  - worktree con 59 voci (52 file modificati, 7 nuovi), nessuno di I.
- **▶️ Riparti** (2026-10-12 19:24, coordinatore):
  - il checkpoint CP1 parte subito, col blob del piano ricalcolato;
  - poi FROZEN sul CP1 fino al commit, quindi il CP2;
  - la run completa con coverage del coordinatore gira sulla 6176: se un mio E2E scade, prima lo rilancio da solo, poi indago.

### M-18 CP2 — via (coordinatore, 2026-10-12 sera)
- **Base**: `a5653f9ef` (treno 68, il CP1 è dentro: `5b2aad5c4`, `d00c06685`). Worktree pulita, porta 6164 libera.
- **Dal coordinatore**:
  - galleria: proposta A, passata a M con la docstring di `galleryLocale.ts:4-7`;
  - CHANGELOG: una sola volta, col CP2;
  - il primo passo è `en` senza regione → `en-GB`, col suo rosso;
  - `ProviderAssignmentSection` per ultimo, dopo il cambio di I (`:591-596`, non ancora nel target);
  - `_frontend_utility.py` passa a M: registrazioni solo chiedendo.
- **Inventario riverificato** sulla base (script in sola lettura `/tmp/libreFolio_m18cp2_inv.py`):
  - dopo la mia base, il target ha toccato un solo file del perimetro, `AboutTab` (una riga, di I);
  - `currencyFormat`: 65 chiamate, 61 in componenti runes e 4 in `.ts` chiamati da runes, nessuna legacy;
  - `formatDateTime`: un solo chiamante legacy, la pagina `files` (`:686`);
  - altri legacy con date: `ProfileTab:480` (passa già `$currentLanguage`) e la pagina del broker (`:783`, `:800`).

#### Disegno del CP2
1. **`uiLocale.ts:42`**: il tag del browser si tiene solo se ha la lingua della UI **e una regione** (`Intl.Locale(tag).region`). `en` o `en-Latn` → `en-GB`; `es-419` resta.
2. **Importi**:
   - `currencyFormat`: opzione `locale`, per default `uiLocale()`;
   - i 15 `toLocaleString(undefined…)`/`Intl.NumberFormat(undefined…)` passano dalla fonte;
   - `RiskAnalysisPanel:122` diventa un `$derived`.
3. **Date**:
   - `formatDateTime(value, locale = uiLocale())`; la pagina `files` passa `$uiLocaleStore`;
   - i 9 siti con `undefined` e i 5 senza argomenti passano dalla fonte;
   - la pagina del broker: `formatDate(str, locale)`, con `$uiLocaleStore` dal template;
   - `ProfileTab:480`: `$uiLocaleStore`.
4. **M-17**:
   - `DateRangePicker:1109` passa dalla fonte;
   - `GlobalSettingsTab:726` → `{$_('common.updated')}:` più la data dalla fonte; `:755` uguale;
   - `DataEditor:106` (il giorno della settimana) e `:205` passano dalla fonte.
5. **I siti nella lingua della UI** (`$currentLanguage`, `$locale`, `language`, `tag`) passano dalla fonte:
   - gli helper con `locale?` prendono il default `uiLocale()`: `formatAxisNumber`, `formatAxis{Percent,Currency,Amount}`, `formatQuantity`, `formatLotQuantity*`, `formatMonthLabel`, `dayFormatter`, `formatPlanner*`, `buildResponsiveXAxisPolicy`, `formatAxisDate`;
   - le chiamate che passano la lingua la tolgono (runes) o passano `uiLocale()`;
   - `UnifiedLotsTable` (di I) non passa nessuna locale: segue la fonte senza essere toccato.
6. **Restano sulla lingua** (testo, non cifre):
   - `ensureCountriesLoaded($currentLanguage)`;
   - `GeographyMap language=` (i nomi dei paesi);
   - `localizedScenarioText`, `replayOptions`, `shockOptions`;
   - `nameComparator`;
   - `Intl.ListFormat` (`AssetSetRiskReturnSection:161`);
   - la lingua della risposta dell'AI Export.
7. **AI Export**:
   - `AiExportMenu:330` passa `uiLocale()`;
   - il messaggio «copiato» (`ui.ts:97-105`) oggi scrive token e byte nella forma della lingua della **risposta**, dentro una frase nella lingua della UI: passa dalla fonte;
   - il prompt non cambia di un byte.
8. **Le cifre dei grafici** (famiglia N, circa 45 `toFixed`): `chartCoreHelpers`, `LineChart`, `candlestickChartHelpers`, `priceChartHelpers`, `PriceChartFull`, `CandlestickChart`, `SemiDonutChart` (anche `'{b}: {c}%'`), `GeographyMap` (`visualMap`), `AllocationHistoryChart`, `ExposureTreemap`, `GrowthChart`, `LotWacPriceChart`, `CorrelationHeatmap`, `echartsTooltipHelpers`, il default di `TweenedValue`.
   - Regole: `formatPercent` / `formatFixed`; zero senza `+`; `candlestick` tiene «almeno un decimale» sotto 1.
9. **Il ridisegno**:
   - ogni effetto che chiama `setOption` legge `uiLocale()`;
   - `void $currentLanguage` → `void uiLocale()`, con la stessa tempistica, perché lo store deriva dalla lingua;
   - lo aggiungono `AllocationPieChart`, `ScatterChart`, `SemiDonutChart`, `GeographyMap`, `ExposureBars` e `CorrelationHeatmap`.
10. **Commenti da riscrivere**: `lotChartShared.ts:85-90`, `formatDateTime.ts:16-18`, `formatAxisDate.ts:8-10`, `LotWacPriceChart.svelte:293`, `L2Diversification.svelte:211`, `GrowthChart.svelte:742`, `l1Helpers.ts:35`.
11. **Fuori**:
    - `formatDecimalForDisplay` e gli `<input type="date">` nativi: sono input, localizzarli chiede di localizzare anche la lettura; T-DI;
    - il fuso orario (`GlobalSettingsTab:105`, `:108`);
    - le cifre minori di una valuta lette con `'en'` (`snapshotDataRenderer:226`, `planner/format:36`).
- **Domanda al coordinatore**: `DataEditor:154` (`'Date'`) e `:180` (`title="N days stale"`) sono testo inglese scritto a mano, accanto al giorno della settimana di M-17. Le chiavi esistono già (`common.date`, `chart.tooltip.stale`). Entrano nel CP2?

- **Risposte del coordinatore** (2026-10-12 sera):
  - `DataEditor:154` (`'Date'` → `common.date`) e `:180` (il titolo → `chart.tooltip.stale`) **entrano nel CP2**, rosso prima, zero chiavi nuove.
  - Verifica di `chart.tooltip.stale`: lo stesso `{days}` nelle 4 lingue, ma nessun plurale ICU («day(s)», «giorno/i», «jour(s)», «día(s)»), come i tooltip di `CandlestickChart:520` e `LineChart:777`. Il badge `⚠️ {N}d` ha una «d» inglese.
  - **Scelta (A)**: il titolo usa la chiave com'è, nessun catalogo toccato. Il plurale vero e la «d» sono la voce **T-ST** del backlog, scritta in fondo alla mia sezione.
- **Rossi in corso**, tre test-author in parallelo su file distinti, ognuno lancia solo vitest sui propri file:
  - A: `uiLocale.test.ts`;
  - B: importi, date, M-17 (11 file);
  - C: grafici, assi, ridisegno, contratti D23 e `+0.00%` (10 file).

#### Passi
1. 🔴 `en` senza regione → 🟢 (test-author A, `uiLocale.test.ts`).
2. 🔴 importi, date, M-17 (test-author B) e grafici, assi, ridisegno, contratti (test-author C): solo file esistenti, già registrati.
3. Cura, nell'ordine 2–10 del disegno.
4. Verdi: le 19 azioni Vitest del CP1, `check-orphans`, `front check`, Prettier; poi gli E2E che cambiano lingua.
5. `ProviderAssignmentSection` (`:333`, `:585`, `:616`), se il cambio di I è entrato.
6. Checkpoint, coi testi del CHANGELOG (🐛 finale e 🔄), poi FROZEN.

#### M-18 CP2 passo 1 — `en` senza regione → `en-GB` ✅ (2026-10-12)
> **Note implementazione**:
> - **Rosso** (test-author A, `uiLocale.test.ts`), visto rosso anche da me con `node_modules/.bin/vitest run src/lib/stores/app/uiLocale.test.ts`: 3 rossi, 28 verdi.
>   - `(en, en) → en-GB`: `expected 'en' to be 'en-GB'`;
>   - `(en, en-Latn) → en-GB`: `expected 'en-Latn' to be 'en-GB'`;
>   - con il browser `en` nudo, entrambe le forme danno `{store: 'en', getter: 'en'}`.
>   - Le guardie restano verdi: `(es, es-419)`, `(it, it)`, `(fr, fr)`.
> - **Cura** (`uiLocale.ts`, `resolveUiLocale`): il tag del browser si tiene solo se `new Intl.Locale(tag)` ha la lingua della UI **e** una `region`. Docstring aggiornata: un browser senza regione prende il default della lingua.
> - **Verde**: 31/31; Prettier pulito.

#### M-18 CP2 — cura preparata, non applicata (2026-10-12 sera)
> **Note implementazione**:
> - **Script** `/tmp/libreFolio_m18_cp2_apply.py`. Ogni sostituzione verifica quante volte compare; `--dry-run` non scrive niente e mette il diff in `/tmp/libreFolio_m18_cp2_dry.diff`.
>   - Dry-run: **294 operazioni su 78 file**, tutte col conteggio atteso.
>   - Toglie 14 import `currentLanguage` e 14 `locale` rimasti senza uso: 13 file del PAC e dei Tools, più `GrowthChart`.
>   - Prima di applicarlo, ogni rosso dev'essere visto rosso.
> - **Rossi in corso**: A ✅ (passo 1); B (importi, date, M-17); C (grafici, assi, ridisegno, D23); **D**:
>   - il messaggio «copiato» dell'AI Export (`aiExportUi.test.ts`), che cambia contratto: le cifre seguono la UI, non la lingua della risposta;
>   - le date del PAC;
>   - i default di `riskAnalysisHelpers` e degli helper dei lotti;
>   - `TornadoChart` col browser `it-CH`.
> - **Fuori perimetro, trovati**:
>   - `PriceChartFull.svelte:785-788` ha testo inglese scritto a mano nel tooltip: «orig.», «Nd back», «fx @»;
>   - `dataTableLogic.ts:341` (`${days}d ago`) sta in un ramo che nessuna colonna usa;
>   - `files/+page.svelte:685` (`formatDate`) è codice morto.
> - **`GeographyMap`** si ridisegna già al cambio di lingua: il suo effetto sul prop `language` (`:111-116`) richiama `renderChart`. Basta il `formatPercent` nel `visualMap`.
> - **E2E da rilanciare dopo la cura**:
>   - `front-utility toolbar-width-sweep`: i campi del `DateRangePicker` in fr/it/es cambiano larghezza;
>   - `front-asset asset-mobile-layout`, `front-fx fx-editor`, `front-asset asset-detail`, `front-broker detail`, `front-utility files-uploader`, `front-transaction transactions-modals`, `front-portfolio dashboard`.
>   - Nessun E2E fissa `+0.00%` o cifre da 1 000 in su senza separatore.
> - **Doc** (docs-writer, solo EN, dopo la cura): `developer/frontend/i18n.md` (la regola delle cifre) e la tabella degli store in `developer/frontend/state/app-state.md` (`uiLocale`).

#### M-18 CP2 passo 2 — i rossi ✅ (2026-10-12 sera)
> **Note implementazione**: tutti visti rossi anche da me, con vitest diretto sui soli file dei rossi (fuori dalla corsia), ognuno su un'asserzione:
> - **B**: 33 rossi in 11 file: importi, `KpiSection`, date, `dataTableLogic`, `SchedulerLogModal`, `ProfileTab` (legacy, browser `it-IT`), M-17 (`DateRangePicker`, `GlobalSettingsTab`, `DataEditor`: giorno della settimana, intestazione, titolo del badge `stale`);
> - **C**: 40 rossi in 10 file:
>   - assi `chartCoreHelpers`, `candlestick`, `priceChart`, `lotChartShared`, tooltip;
>   - `PerformanceChart` e `GrowthChart`, dove D23 ora forza `uiLocale` in `sv-SE` con un mock al posto del prototipo patchato;
>   - `ExposureTable`;
>   - il ridisegno di `AllocationPieChart` e `ScatterChart`;
> - **D**: 13 rossi in 6 file: il messaggio «copiato» dell'AI Export, le date del PAC, `riskAnalysisHelpers`, gli helper dei lotti, `TornadoChart` con `it-CH`.
>
> **⚠️ Fuori pista**: C ha trovato percentuali stampate grezze (`${value}%`), fuori dall'inventario costruito su `toFixed`/`toLocale*`/`Intl`. Un grep dedicato ne trova 25:
> - **sono cifre**: la torta (`:445`, `:447`, `:450`, `:515`), `geographyMapHelpers:142`, `chartSignalsHelpers:49`, l'asse di `AllocationHistoryChart:771` e i badge di `CorrelationHeatmap:357-358`;
> - **non lo sono**: CSS (`hsl`, raggi, gap), il prompt dell'AI Export (neutro per costruzione), e le etichette inglesi dei segnali what-if (`Linear`/`Compound`/`Sine`), che sono testo fuori perimetro.
>
> **Cura**: un'opzione **`trim`** di `formatPercent`, dove `digits` diventa il massimo, così le cifre restano quelle di oggi (`44.5%`, `44%`).
>
> C ha segnalato anche un bug possibile: con la dipendenza dalla lingua, la scorciatoia «solo dati» della torta terrebbe la mappa dei nomi della legenda della lingua di prima. Cura: ricostruzione completa al cambio di lingua (`lastLocale`), come al cambio di tema.
>
> **Rossi in corso** (C, secondo turno): `formatPercent.test` (`trim`), `AllocationPieChart.test` (percentuali e legenda), `geographyMapHelpers.test`, `chartSignalsHelpers.test`, `AllocationHistoryChart.test`. Cura pronta: `/tmp/libreFolio_m18_cp2_apply2.py`, dry-run con 19 operazioni su 6 file.

#### M-18 CP2 passo 3 — la cura, primo blocco ✅ (2026-10-12 sera)
> **Note implementazione**:
> - `/tmp/libreFolio_m18_cp2_apply.py`: 294 operazioni su 78 file, più `uiLocale.ts` del passo 1. Prettier: nessun cambio.
> - **Verde** dei file dei rossi, vitest diretto: 27 file, **1 714 verdi**, 1 rosso.
>   - Il rosso è un test che legge il sorgente: `chartCoreHelpers.test.ts:2138` fissa `locale: $locale ?? undefined` di `GrowthChart`, da rifissare a `uiLocale()`. Va a test-author.
> - **Da riparare**: il registro dei siti monetari (`moneyRenderSites.test.ts:218`) è indicizzato sullo snippet `${Number(value).toFixed(4)}…` di `PriceChartFull`, ora `formatFixed`. Va a test-author, dopo le 19 azioni.
> - **In corso**:
>   - le 19 azioni Vitest del CP1 sulla 6164 (log `/tmp/libreFolio_t1_m18cp2g1_*`);
>   - docs-writer su `developer/frontend/i18n.md` e `state/app-state.md`.
> **⚠️ Fuori pista (2026-10-12 20:38, coordinatore)**: «non toccare le pagine della doc (`mkdocs_src/`)». Dopo il CP2, M allinea le cifre della doc (`preferences`, `kpi-cards`, `positions`, `brokers/index`) e aggiunge in `preferences` una frase sulla regola.
> - docs-writer era già partito sulle due pagine developer. Gli ho mandato lo STOP; alle 20:38 non aveva ancora scritto niente in `mkdocs_src/`.
> - Il testo che produce lo salvo in `/tmp` come proposta, e le pagine tornano come in HEAD.
> - **Nel CP2 consegno**: l'elenco dei formati visibili che cambiano (importi, percentuali, date, assi), con un esempio per lingua, come riferimento per M.

#### M-18 CP2 passo 4a — le 19 azioni Vitest dopo il primo blocco (2026-10-12 sera)
> **Esito** (6164, in sequenza; log `/tmp/libreFolio_t1_m18cp2g1_*`): 15 azioni verdi su 19.
> - Verdi: component-unit **3 041**, growth-chart-memo 141, broker 53, fx 138, risk-* (248, 20, 102, 13, …), store, tx, user, onboarding.
> - Rossi:
>   - core-unit, 3: il gate `htmlInterpolation`, due falsi positivi su `LineChart:771`; il registro di `moneyRenderSites`, 2;
>   - ai-export e asset-unit, 1 ciascuna: il contratto sul sorgente in `chartCoreHelpers.test.ts:2138`;
>   - allocation-unit, 3: i rossi nuovi di C sulla torta, attesi.
> - **Il gate HTML**: si fida di `x[k].toFixed(n)` (`NUMERIC_FORMATS`) ma non della forma funzione `formatFixed(x[k], n)`.
>   - Cura nel gate, via test-author E: `formatFixed` e `formatPercent` col numero come primo argomento rendono numeri, come `toFixed`; più l'auto-test del gate.
>   - Il registro dei siti monetari prende lo snippet nuovo di `PriceChartFull`; il contratto di `GrowthChart` si rifissa a `uiLocale()`.
>
> **⚠️ Fuori pista**:
> - **C, secondo turno**: 13 rossi nuovi, visti rossi anche da me (117 verdi). I due rossi della torta del primo turno, il ridisegno e l'importo, ora passano col primo blocco.
> - **C ha trovato un altro sito**: `problemCount` (`chartSignalsHelpers.ts:31-33`, `String(value)`) passa conteggi e copertura ai messaggi dei segnali.
>   - Cura: `formatFixed(value, 1, {trim: true})`. In inglese un conteggio da 1 000 in su si scrive raggruppato.
>   - Rosso chiesto a C. La cura è nel passo 2: `/tmp/libreFolio_m18_cp2_apply2.py`, 21 operazioni su 6 file.
> - **Il target è andato avanti**: `e37770d5e` (treno 70). L'unico file in comune è `BACKLOG_POST_1.2.md`, in sezioni diverse. M ha già applicato la proposta A della galleria (`e8d5a5668`). `ProviderAssignmentSection` di I non è ancora entrato.
> - **Il riferimento per M** (formati visibili per lingua): `/tmp/libreFolio_m18cp2_examples.txt`, calcolato con Intl.

#### M-18 CP2 passo 5 — seconda parte della cura, decisioni (2026-10-12 sera)
> **Note implementazione**:
> - **Rossi del secondo giro di C**, visti rossi anche da me: 16. Sono 13 su `formatPercent({trim})`, le percentuali e la legenda della torta, la mappa, la copertura dei segnali e l'asse di `AllocationHistoryChart`; più 3 su `problemCount`.
> - **Cura** `/tmp/libreFolio_m18_cp2_apply2.py`: 22 operazioni su 6 file.
>   - `formatPercent({trim})`;
>   - le percentuali grezze;
>   - `problemCount` con `formatFixed(…, 1, {trim: true})`;
>   - la torta ricostruita per intero al cambio di lingua (`lastLocale`);
>   - nel commento di `formatPercent`, lo spazio francese prima di `%`: è U+00A0, non U+202F (segnalato da docs-writer).
> - **Verde**: i 5 file, 136/136; Prettier pulito; `dev.py front check` con 0 errori e 0 avvisi.
>
> **Decisioni del coordinatore** (2026-10-12, sera):
> 1. Le percentuali grezze e la torta ricostruita **nel CP2** ✅.
> 2. I **decimali esatti** (`formatDecimalForDisplay`, 15 punti di sola lettura) vanno nel **CP3**, subito dopo il CP2: è un formattatore nuovo che passa la stringa a Intl senza passare da un float. Fa parte della 1.2.
> 3. Le **due pagine developer** (`developer/frontend/i18n.md`, `state/app-state.md`, solo EN) le scrivo io nel CP3 con docs-writer, partendo da `/tmp/libreFolio_m18cp2_devdocs_proposal.patch`. Devono coprire la regola completa, decimali compresi. U-4 toccherà `i18n.md` dopo. Lo stop valeva solo per le pagine utente di M.
> 4. **T-ICU** nel backlog, scritta nel CP2: le cifre dentro i messaggi ICU (`{x, number, percent}`, il `#` dei 74 plurali) seguono la lingua senza regione.
> 5. Il **CHANGELOG** lo scrive il coordinatore una volta sola, dopo il CP3. Nell'handoff del CP2: i formati visibili per lingua. Nel CP3: i decimali.
>
> **Ancora aperto per il CP2**: le riparazioni di E (il gate HTML, il registro monetario, il contratto di `GrowthChart`), poi le 19 azioni, `check-orphans` e gli E2E. `ProviderAssignmentSection` aspetta ancora I e, se non entra prima, va nel CP3.
> **Triage di `front-utility toolbar-width-sweep`** (skill `test-triage`, verdetto **ambiente/soglie, preesistente: V-19**):
> - **I rossi**: 2, solo in spagnolo. In denseRow il gruppo delle azioni («Exportación IA …») esce dalla barra.
>   - `assetDetail · es`: +6,8 / +16,8 / +4,8 / +14,8 px a vw 1200 / 1190 / 930 / 920;
>   - `dashboard · es`: +6,0 / +16,0 / +14,0 px a vw 1300 / 1290 / 1020;
>   - 13 passed.
> - **Ipotesi scartate**: §1 la forma della risposta non c'entra, è geometria; §2 non sono attese a tempo; §3 l'asset è creato dal test e la scatola che esce è il gruppo delle azioni, testo tradotto.
> - **Dal coordinatore**: è **V-19** (`BACKLOG_POST_1.2.md:763`), deterministico anche a 1 worker, visto da V sulla stessa base.
>   - Causa: il cambio dei termini `7c66234a7` («Exportación IA»), già nel treno 68.
>   - Le date spagnole, più corte, spostano gli stessi rossi di circa 20 px.
>   - La cura è nel lotto 48 di I (C5, soglie denseRow). **Non li tocco.** Chi entra per secondo rilancia la sweep sulla revisione combinata.

#### M-18 CP2 passo 6 — riparazioni ed E2E (2026-10-12 sera)
> **Note implementazione**:
> - **Riparazioni** (test-author E), ognuna verde sul suo file:
>   - `htmlInterpolation.gate.test.ts`: `NUMERIC_FORMAT_CALLS = {formatFixed, formatPercent}` col solo primo argomento, fidato come `x[k].toFixed(n)`. L'auto-test del gate copre i casi «non segnalato» e «ancora segnalato», e la prova che il gate morde (tre modifiche temporanee, ripristinate).
>   - `moneyRenderSites.test.ts`: lo snippet nuovo di `PriceChartFull`, stesso stato, più una frase nel `why`.
>   - `chartCoreHelpers.test.ts:2138`: rifissato su `locale: uiLocale(),`.
> - **E2E** (6164, in sequenza; log `/tmp/libreFolio_t1_m18cp2e2e_*`):
>
>   | azione | esito |
>   |---|---|
>   | `toolbar-width-sweep` | 13 passed, 2 failed: solo `es`, V-19, preesistente (triage sopra) |
>   | `asset-mobile-layout` | 21 passed |
>   | `fx-editor` | 4 passed |
>   | `broker detail` | 37 passed |
>   | `files-uploader` | 8 passed |
>   | `transactions-modals` | 19 passed |
>   | `asset-classification` | 4 passed |
>   | `dashboard` | 27 passed |
>   | `risk` | 38 passed |
>   | `risk-lab` | 44 passed |
>   | `asset-detail` | 32 passed |

### Checkpoint M-18 CP2 🧊 (2026-10-12 sera) — FROZEN, in attesa del coordinatore
- **Base**: `a5653f9ef` (treno 68). **Target**: `e37770d5e` (treno 70). In comune solo `BACKLOG_POST_1.2.md`, in sezioni diverse: C-61..C-64 del coordinatore, T-ST e T-ICU in fondo alla sezione T.
- **Delta**: 119 file modificati (82 di prodotto, 35 di test, il piano e il backlog). Nessun file nuovo, niente in stage.
- **I rossi visti rossi**: 105. A 3, B 33, C 40 + 16, D 13.
- **Riparazioni**: il gate HTML, il registro dei siti monetari, e due contratti sul sorgente (`GrowthChart`, la torta).
- **Verdi**:
  - le 19 azioni Vitest, 11 069 test;
  - `check-orphans`;
  - `front check` con 0 errori e 0 avvisi;
  - Prettier e `git diff --check`;
  - E2E, 11 azioni: tutte verdi tranne i 2 rossi preesistenti di V-19 (sweep `es`).
- **Commit proposti** (ASCII):
  1. `fix(i18n): amounts and dates in the UI language`: il prodotto e i test (`/tmp/libreFolio_commit_t_m18cp2_1.txt`);
  2. `docs(journal): record M-18 CP2`: il piano e il backlog (`/tmp/libreFolio_commit_t_m18cp2_2.txt`).
- **Per M**: il riferimento dei formati visibili per lingua è nel messaggio di checkpoint (calcolato con Intl, `/tmp/libreFolio_m18cp2_examples.txt`).
- **CP3**:
  - i decimali esatti (`formatDecimalForDisplay`, 15 punti di sola lettura);
  - le due pagine developer, con docs-writer, partendo da `/tmp/libreFolio_m18cp2_devdocs_proposal.patch`;
  - `ProviderAssignmentSection` (`:333`, `:585`, `:616`), se entra il cambio di I.

### M-18 CP3a — via (coordinatore, 2026-10-12 21:44)
- **Base**: `64a3ddccc`, cioè il CP2 committato (`ff7c96fd0`, 117 file, e `64a3ddccc`, il journal). Worktree pulita. Il coordinatore non mi porta ancora il target.
- **Sequenza**:
  1. **CP3a** sulla mia base: i decimali esatti, le 2 pagine developer dalla patch, e le due righe già sbagliate di `app-state.md`;
  2. il treno 72 porta il lotto 48 di I (con `ProviderAssignmentSection`) e la 2b di V; poi checkpoint del CP3a, e il coordinatore mi porta il target (U-2, I e V);
  3. **CP3b**: `ProviderAssignmentSection` e **una sola validazione della revisione combinata** (CP2 + CP3 + U-2 + I + V), compresa `toolbar-width-sweep`, che con la cura di I deve uscire verde anche in es; poi il treno 73.
- I punti 1–4 dei trovati fuori perimetro diventano voci T-* nel backlog: **T-EN1, T-EN2, T-COL, T-DEAD**, scritte. Nessuna chiave nuova: U sta dividendo i cataloghi.

#### Disegno del CP3a
- **`formatExactDecimal(value, {minFrac = 0, maxFrac = 8, locale = uiLocale()})`** in `formatFixed.ts`, accanto al `toFixed` localizzato. I test vanno nel file esistente, quindi nessuna registrazione nel runner.
  - Le cifre sono quelle di `formatDecimalForDisplay`: taglio, zeri finali via, padding.
  - Intl le scrive ricevendo la **stringa**: decimale esatto (`Intl.StringNumericLiteral`, lib `esnext`). Provato con Node: `12345678901234.123456789012` esce intero.
- **I 12 punti di sola lettura**:
  - PAC: `planner/format.ts:161`, `:174`, `:212`;
  - `LotWacPriceChart:489`, `:1360`;
  - `LotCustodyModal:77`, `:144`, `:160`, `:191`;
  - `WacPreviewSection:554`, `AssetEventPicker:453`, `GapFixStep:72`.
- **Restano a `formatDecimalForDisplay`**, perché sono input o logica: `ExactDecimalInput`, `ExactQuantityInput`, il buffer di `CompactCashCell`, `pluralCount` (`:188`) e il confronto di `WacPreviewSection:296-297`.
- **Cura pronta**: `/tmp/libreFolio_m18_cp3_apply.py`, dry-run con 18 operazioni su 7 file.
- **Rossi** (test-author F): `formatFixed.test.ts`, `planner/format.test.ts`, `WacPreviewSection.test.ts`, `GapFixStep.test.ts`.
- **Doc** (docs-writer, solo EN, dopo la cura):
  - la patch `/tmp/libreFolio_m18cp2_devdocs_proposal.patch`, estesa ai decimali esatti;
  - in `app-state.md`, la riga Language («Reacts to changes in the Settings store», falsa) e la frase sull'adattatore del PAC («not in the source tree yet», il file esiste).

#### M-18 CP3a passi 1–2 — rossi e cura ✅ (2026-10-12 sera)
> **Note implementazione**:
> - **Rossi** (test-author F): 53. Li ho visti rossi anche io, con vitest diretto: 130 verdi.
>   - `formatFixed.test.ts`: 38;
>   - `planner/format.test.ts`: 11, compresa una riga di contratto (il conteggio del solutore, che in inglese ora si raggruppa: `≈1,234.57`);
>   - `WacPreviewSection.test.ts`: 2;
>   - `GapFixStep.test.ts`: 2.
>   - F ha provato con sostituti temporanei, poi rimossi, che dopo la cura vanno verdi. Ha fissato anche il raggruppamento di default di Intl: niente `useGrouping: true`, perché it ed es non raggruppano le 4 cifre.
> - **Cura**: `/tmp/libreFolio_m18_cp3_apply.py`, 18 operazioni su 7 file. `formatExactDecimal` in `formatFixed.ts`, più i 12 punti di sola lettura. Prettier: nessun cambio.
> - **Verde**: i 4 file passano, 155 + 28.
>   - **⚠️ Fuori pista**: alla prima corsa `GapFixStep.test.ts` è andato in timeout nel suo hook di caricamento (60 s, `:138`), col carico della macchina a 47–50, prima di ogni asserzione. Verdetto: **ambiente** (CPU contesa da altre sessioni). Rilanciato da solo: 28/28. F l'aveva visto anche lui, col carico intorno a 98.
> - **Doc**: ho riapplicato la patch con `patch -p1` (121 righe). docs-writer, riaperto, la estende ai decimali esatti e ai gate, aggiunge T-ICU e corregge le due righe di `app-state.md`.
> - **Gate in corso**: le 19 azioni e `check-orphans` sulla 6164 (log `/tmp/libreFolio_t1_m18cp3g1_*`).

#### M-18 CP3a passi 3–4 — doc e gate ✅ (2026-10-12 sera)
> **Note implementazione**:
> - **Doc** (docs-writer, solo EN):
>   - `developer/frontend/i18n.md`, +132: la sezione `#ui-locale` con la regola, la mappa, i formattatori (`formatExactDecimal` compreso), cosa non usare, la reattività, le eccezioni (con T-ICU) e i gate;
>   - `state/app-state.md`, +18/−6: la riga dello store `uiLocale`; la riga Language corretta (nessuno ascolta lo store delle impostazioni; la lingua la mettono l'auth al login, Preferences e Welcome dopo la scrittura, o il selettore); il paragrafo dell'adattatore del PAC al presente, allineato al codice.
>   - `dev.py mkdocs build` verde (solo l'avviso solito di Material); `check-links` con 95 link validi.
> - **⚠️ Fuori pista**:
>   - **L'esempio di T-ICU era sbagliato**: l'unico percento non ha decimali, quindi it e it-CH scrivono entrambi `13%`. Ora c'è es-MX: `1234` contro `1,234`, e `13 %` contro `13%`, provato con Node.
>   - **Il gate HTML non si fida di `formatExactDecimal`, ed è giusto**: per un valore che non è un decimale restituisce l'ingresso com'è, quindi può portare testo.
> - **Gate** (6164; log `/tmp/libreFolio_t1_m18cp3g1_*`):
>   - le 19 azioni Vitest, **11 124 test** (core-unit 3 943, component-unit 3 043, tx 887);
>   - `check-orphans` pulito;
>   - `front check` con 0 errori e 0 avvisi;
>   - Prettier e `diff --check` puliti.
> - **Sovrapposizione col target** `0071b9703`, che non contiene ancora il CP2. Vera sovrapposizione rispetto alla base `a5653f9ef`:
>   - `BACKLOG_POST_1.2.md`, in sezioni diverse;
>   - la pagina dell'asset, toccata da I (`7f8febd9d`, toolbar spagnola) e dal CP2 (una data e un import), in pezzi diversi. Simulazione del coordinatore: pulita.

### Checkpoint M-18 CP3a 🧊 (2026-10-12 sera) — FROZEN, in attesa del coordinatore
- **Base**: `64a3ddccc` (CP2 sul ramo). **Delta**: 15 file modificati: 7 di prodotto, 4 di test, 2 pagine developer, il piano e il backlog. Nessun file nuovo.
- **Commit proposti** (ASCII), in `/tmp/libreFolio_commit_t_m18cp3a_{1,2,3}.txt`:
  1. `fix(i18n): exact decimals in the UI language`: prodotto e test;
  2. `docs(dev): figures in the interface language`: le 2 pagine;
  3. `docs(journal): record M-18 CP3a`: il piano e il backlog.
- **Poi il CP3b**, sul target: `ProviderAssignmentSection` (`:333`, `:585`, `:616`, sulla base che contiene il cambio di I) e la validazione combinata unica, compresa la sweep anche in es.

### M-18 CP3b — via (coordinatore, 2026-10-12 22:39)
- **Il CP3a è committato**: `c17d39d5a` (11 file), `133259913` (le 2 pagine developer), `052b9f8bd` (journal).
- **Il target del treno 72 è fuso sul ramo**: HEAD `c272d93b4`, merge pulito. Contiene U-2, il lotto 48 di I (clipboard, `ProviderAssignmentSection`) e la 2b di V.
  - U-2: i cataloghi sono `src/lib/i18n/base/<lang>.json`. `src/lib/i18n/<lang>.json` è generato dagli hook (`predev`, `prebuild`, `precheck`, il `globalSetup` di Vitest) e non è più tracciato.
  - `package.json` aggiunge solo gli hook: nessuna dipendenza nuova, niente `npm ci`.
  - Niente chiavi nuove.
- **I siti di `ProviderAssignmentSection`** (runes; `testResults = $derived.by(buildTestResults)`, quindi reattivo):
  - `:334`: il prezzo della sonda, `formatFixed(…, 2)`;
  - `:354`: il conteggio dello storico, `formatFixed(…, 0)`. La parola «points» resta in inglese ed è finita in T-EN1;
  - `:586` e `:618`: le durate in secondi, `formatFixed(…, 2)`.
- **Cura pronta**: `/tmp/libreFolio_m18_cp3b_apply.py`, dry-run con 5 operazioni. Rossi: test-author G su `ProviderAssignmentSection.test.ts`.
- **La validazione combinata unica**, dopo la cura, sulla 6164:
  - `check-orphans`, `front check`, le 19 Vitest;
  - `toolbar-width-sweep`, che deve dare 15/15, anche in es;
  - gli E2E del CP2: broker detail, risk-lab, risk, asset-detail, dashboard, asset-mobile-layout, transactions-modals, files-uploader, fx-editor, asset-classification;
  - più `connection-security` e `support-copy-and-go` (chiesti dal coordinatore) e `settings`, che aggiungo io perché il CP2 ha toccato `GlobalSettingsTab`.

#### M-18 CP3b passi 1–2 — rossi e cura ✅ (2026-10-12 sera)
> **Note implementazione**:
> - **Rossi** (test-author G, `ProviderAssignmentSection.test.ts`): 4. Li ho visti rossi anche io; i 26 esistenti restano verdi.
>   - italiano due volte (prezzo `1234,50` e `12.345,50`, conteggio `12.345`, tempi `1,23s`, totale `2,47s`);
>   - il cambio di lingua sul posto en → it → en;
>   - la guardia inglese, col contratto nuovo `12,345`.
> - **Cura**: `/tmp/libreFolio_m18_cp3b_apply.py`, 5 operazioni. Verde: 30/30.
> - **`front check` sulla revisione combinata**: 0 errori e 0 avvisi; prima gira l'hook dei cataloghi di U-2.
> - **Validazione combinata in corso** (log `/tmp/libreFolio_t1_m18cp3bv_*`).

#### M-18 CP3b passo 3 — la validazione combinata unica ✅ (2026-10-12 notte)
> **Revisione**: `c272d93b4` (CP2 + CP3a + il target del treno 72: U-2, il lotto 48 di I, la 2b di V) più la cura del CP3b. Corsia 6164, 34 azioni in una sola corsa, tutte `exit=0` (log `/tmp/libreFolio_t1_m18cp3bv_*`).
> - `check-orphans` pulito; `front check` con 0 errori e 0 avvisi.
> - **Vitest**: 19 azioni, **11 309 test**. Tra queste core-unit 4 090, component-unit 3 077, tx 887, ai-export 433, asset 762, risk-levels 493 + 248.
> - **`toolbar-width-sweep`: 15/15, anche in es**, con la cura di I (C5). I 2 rossi di V-19 non ci sono più.
> - **E2E**:
>
>   | azione | passed |
>   |---|---|
>   | broker detail | 37 |
>   | risk-lab | 44 |
>   | risk | 38 |
>   | asset-detail | 32 |
>   | dashboard | 27 |
>   | asset-mobile-layout | 21 |
>   | transactions-modals | 19 |
>   | files-uploader | 8 |
>   | fx-editor | 4 |
>   | asset-classification | 4 |
>   | connection-security | 8 |
>   | support-copy-and-go | 16 |
>   | settings | 45 |
>
> - **Dopo la validazione il target si è mosso**: `bcd502912` porta i treni 73 (M, W) e 74 (U-3, il catalogo diviso per sottosistema e per plugin).
>   - Delle mie modifiche (CP2 + CP3) tocca solo `BACKLOG_POST_1.2.md`.
>   - Con U-3 le chiavi cambiano file sorgente (`chart.tooltip.stale` sta ora in `i18n/charts/`), ma il catalogo generato `src/lib/i18n/<lang>.json` resta allo stesso percorso, quello che importano 7 dei miei test.
>   - La validazione sopra **non contiene U-3**.

### Checkpoint M-18 CP3b 🧊 (2026-10-12 notte) — FROZEN, in attesa del coordinatore
- **Base**: `c272d93b4`. **Delta**: 4 file: `ProviderAssignmentSection.svelte` e il suo test, il piano, il backlog (T-EN1 con «points»).
- **Commit proposti**:
  1. `fix(i18n): probe figures in the UI language` (`/tmp/libreFolio_commit_t_m18cp3b_1.txt`);
  2. `docs(journal): record M-18 CP3b` (`/tmp/libreFolio_commit_t_m18cp3b_2.txt`).
- **Per il CHANGELOG del coordinatore**: M-18 è completo. Le cifre di ogni tipo (percentuali, decimali, byte, durate, importi, date, assi, decimali esatti) seguono la lingua dell'interfaccia; M-17 è risolto. Le voci aperte di backlog sono T-DI, T-ST, T-ICU, T-EN1, T-EN2, T-COL e T-DEAD.

### T-EN1 + T-EN2 — via (coordinatore, 2026-10-12 23:54)
- **Base**: HEAD `104ba23d0` = target `dev_release2` (treno 75: il CP2 e il CP3 di M-18 sono dentro), worktree pulita. Corsia 6164.
- **Mandato**: le chiavi con `dev.py i18n add`, che sceglie la sorgente giusta (dopo lo split di U-3); il controllo con `dev.py i18n where`; prima i rossi, via test-author; il gate `utils gate-plugin-i18n-ownership` resta verde; `toolbar-width-sweep` non serve, salvo un'etichetta che allarghi una barra. Restano dopo la 1.2: T-ICU, T-COL, T-DEAD, T-DI, T-ST. La galleria di M aspetta questo lotto.

#### T-EN — analisi (2026-10-12 notte)
**I siti** (riverificati su `104ba23d0`):
- **T-EN1, il tooltip degli eventi del grafico dei prezzi**. `PriceChartFull.svelte:776-792` (`formatEventEntry`): quando il valore dell'evento è convertito, scrive in ogni lingua:
  - «orig.» (`:786`);
  - «(Nd back)» (`:788`);
  - «fx @» (`:789`).
- **T-EN1, la sonda dello storico**. `ProviderAssignmentSection.svelte:354` scrive «points». È anche sbagliata al singolare: «1 points».
- **T-EN2, le etichette dei segnali what-if**: `LinearSignal.ts:75`, `CompoundSignal.ts:97`, `SineSignal.ts:87`.
  - `getLabel()` diventa `RenderedSignal.label` (`ChartSignal.ts:408`), cioè il nome della serie nella legenda e nel tooltip.
  - Le parole sono inglesi; le cifre sono stampate grezze (`${rate}%`, `${per}d`).
  - Chi la chiama: i `$derived` delle sovrapposizioni, in 4 pagine (`assets/[id]`, `assets`, `fx/[pair]`, `fx`) e nell'anteprima di `ChartSettingsModal`. Tutti in modalità runes.

**Le chiavi**, 7. La sorgente è quella indicata da `where`.

| chiave | sorgente | en | it | fr | es |
|---|---|---|---|---|---|
| `chart.tooltip.originalValue` | `i18n/charts/` | `orig. {value}` | `orig. {value}` | `orig. {value}` | `orig. {value}` |
| `chart.tooltip.fxRateDate` | `i18n/charts/` | `fx @ {date}` | `cambio al {date}` | `change au {date}` | `cambio al {date}` |
| `chart.tooltip.fxDaysBack` | `i18n/charts/` | `({days}d back)` | `({days}g prima)` | `({days}j avant)` | `({days}d antes)` |
| `chartSettings.signals.linearLabel` | `i18n/charts/` | `Linear {rate}/yr` | `Lineare {rate}/anno` | `Linéaire {rate}/an` | `Lineal {rate}/año` |
| `chartSettings.signals.compoundLabel` | `i18n/charts/` | `Compound {rate}/yr` | `Composta {rate}/anno` | `Composée {rate}/an` | `Compuesto {rate}/año` |
| `chartSettings.signals.sineLabel` | `i18n/charts/` | `Sine ±{amplitude} / {period}d` | `Sinusoide ±{amplitude} / {period}g` | `Sinusoïde ±{amplitude} / {period}j` | `Sinusoide ±{amplitude} / {period}d` |
| `assets.probe.points` | `i18n/assets/` | `{count, plural, one {{n} point} other {{n} points}}` | `… one {{n} punto} other {{n} punti}` | `… one {{n} point} many {{n} points} other {{n} points}` | `… one {{n} punto} other {{n} puntos}` |

**Le scelte**:
- **Le cifre entrano già scritte**, da `formatPercent` e `formatFixed` nella lingua della UI.
  - Un segnaposto semplice `{x}` stampa `String(value)`, quindi la cifra la scrive il formattatore di M-18, non ICU: nessun nuovo caso T-ICU.
  - Il conteggio della sonda usa la forma dei `stepUnits` del PAC: `count` sceglie il plurale, `{n}` porta la cifra scritta.
  - Il francese ha un ramo `many` uguale a `other`: un testo ICU identico in due cataloghi terrebbe le regole del primo che lo compila (cache di svelte-i18n, gate `catalogIcuLocale.test.ts`).
- **L'inglese resta com'è**: le stesse parole.
  - Cambiano solo i tassi e i periodi da 1 000 in su, ora raggruppati (`1,000%/yr`, `3,650d`), che è il contratto di M-18.
  - E il singolare «1 point».
  - «orig.» è la stessa abbreviazione nelle 4 lingue, ma con la chiave si può tradurre.
- **Le parole delle etichette nei segnali**: un traduttore tracciato in `ChartSignal`, `fromStore(_)`, lo stesso modello di `uiLocale()`.
  - Letto dentro il `$derived` che disegna le sovrapposizioni, è tracciato. Al cambio di lingua l'etichetta si riscrive, insieme alle cifre (`formatPercent` legge `uiLocale()`).
  - Non cambiano le firme di `render`, `renderMulti` e `getLabel`, e i 5 chiamanti non si toccano.
  - **Costo**: i test che chiamano `getLabel()` o `render()` senza i18n devono avviarlo (`setupI18n`). Sono `syntheticSignals`, `registry` e `localSignalRegression`.
  - **L'alternativa scartata**: passare `$t` come parametro, come `backendRenderer` e `translateOr`. Avrebbe toccato 6 classi e 5 chiamanti, fra cui la pagina dell'asset e le pagine FX, che altri workstream toccano spesso.

**Trovati fuori perimetro** (al coordinatore):
- **Q1**: l'editor dei parametri dei 3 segnali what-if scrive il suffisso grezzo (`ChartSignalsSection.svelte:612`): «%/yr» e «days» in ogni lingua.
  - I segnali del backend lo traducono già con `signals.units.*` (`SignalParamControl.svelte:39-44`; `signals.units.days` c'è nelle 4 lingue).
  - **Proposta**:
    - la stessa ricerca nel ramo locale;
    - `suffix: 'percentPerYear'` nei 2 descrittori, che diventano gettoni come quelli del backend;
    - 1 chiave, `signals.units.percentPerYear`.
- **F1**: le date d'osservazione ISO grezze.
  - Nei tooltip del grafico dei prezzi: `valueAt`, `↩`, `💱`, la data dell'evento a `:778`, `fxRateDate`.
  - Nella sonda: `cpDate`, `date_range`.
  - M-18 le ha lasciate ISO. Proposta: una voce di backlog.
- **F2**: i ripieghi inglesi `Asset #N` e `Asset` (`AssetComparisonSignal.ts:169-174`, `assets/[id]/+page.svelte:870`, `:893`) e `FX Pair` (`FxPairSignal.ts:94`). Si vedono solo se l'asset di confronto manca. Proposta: backlog.

**I passi**:
1. le 7 chiavi, poi `where`, `i18n check` e `i18n build`;
2. i rossi, via test-author;
3. la cura;
4. i gate:
   - `i18n check`;
   - `utils gate-plugin-i18n-ownership`, `gate-i18n-usage`, `gate-i18n-catalog`;
   - `front-utility core-unit` e `component-unit`, `front-asset asset-unit`;
   - `check-orphans`, `front check`.

**Le decisioni del coordinatore** (2026-10-13, 00:0x):
1. **Q1 sì**: il suffisso dell'editor dei what-if, con la chiave `signals.units.percentPerYear` (en `%/yr`, it `%/anno`, fr `%/an`, es `%/año`) e i descrittori a gettone. Le chiavi diventano 8.
2. **Nessuna sovrapposizione su `PriceChartFull.svelte`**: il lotto 49 di I tocca solo `asset-detail.spec.ts`.
3. **F1 e F2 diventano voci T-\*** nella mia sezione del backlog, scritte nel journal di questo lotto. Non si fanno ora.

#### T-EN passo 1 — le 8 chiavi ✅ (2026-10-13)
> **Note implementazione**: `/tmp/libreFolio_ten_keys.sh`, 8 volte `dev.py i18n add`.
> - 7 chiavi in `i18n/charts/` e `assets.probe.points` in `i18n/assets/`, nelle 4 lingue. `where` le conferma tutte e 8.
> - `dev.py i18n check`: 4 359 chiavi in modalità stretta.
> - Il diff è fatto solo di aggiunte (8 file sorgente, una virgola per blocco).

#### T-EN passo 2 — i rossi ✅ (2026-10-13)
> **Note implementazione**: test-author H ha scritto 16 rossi e 6 guardie. Li ho visti rossi anche io: `vitest run` sugli 8 file toccati dà 16 falliti e 134 verdi (log `/tmp/libreFolio_ten_reds_before.log`). Ogni rosso fallisce sull'asserzione finale e per il motivo giusto: inglese, o un'etichetta che non si riscrive.
>
> **I rossi**:
>
> | file | rossi | cosa legge |
> |---|---|---|
> | `syntheticSignals.test.ts` | 6 | in it e fr: le etichette con tasso, offset con segno, ampiezza e periodo; i default; la stessa etichetta passata da `renderMulti` |
> | `syntheticSignals.languageSwitch.test.ts` (nuovo, jsdom) | 2 | l'etichetta letta in un effetto (`recordReads`) si riscrive al cambio di lingua sul posto, en → it e en → fr |
> | `ChartSignalsSection.test.ts` | 2 | le unità dell'editor in it e fr |
> | `PriceChartFull.test.ts` (nuovo, jsdom; ECharts registrato) | 3 | le tre righe della conversione in it e fr; un caso con una locale di marcatori, che prova che ogni riga viene dalla sua chiave (`orig.` è uguale nelle 4 lingue) |
> | `ProviderAssignmentSection.test.ts` | 3 | «12.345 punti» in italiano; «1 point» al singolare in inglese e in francese |
>
> - **Le guardie**:
>   - le etichette inglesi sotto 1 000;
>   - `%` resta `%`;
>   - le righe inglesi del tooltip;
>   - «12,345 points»;
>   - `catalogIcuLocale.test.ts`.
> - **Avviano i18n in inglese** (`beforeAll(setupI18n('en'))`): `registry.test.ts`, `localSignalRegression.test.ts` e `syntheticSignals.test.ts`. Senza, dopo la cura, svelte-i18n solleverebbe un errore.
> - **Nel runner** (`_frontend_utility.py`), solo le 2 righe dei file nuovi:
>   - `syntheticSignals.languageSwitch.test.ts` in `front_utility_unit`, accanto a `signalLabel.test.ts`, anch'esso jsdom;
>   - `PriceChartFull.test.ts` in `front_component_unit`.
> - **Le note di test-author**:
>   - il test del cambio di lingua morde solo al primo passaggio: la precondizione è che il catalogo di arrivo non sia ancora caricato;
>   - lo sfasamento di 3 giorni si scrive uguale in ogni lingua, quindi non distingue `formatFixed` dalla cifra grezza;
>   - da 1 000 in su l'inglese raggruppa (`1,000%/yr`, `3,650d`): è già nella mia analisi.
> - **⚠️ Fuori pista**: nei titoli dei test le etichette T-EN1 e T-EN2 sono scambiate per la sonda e per i segnali. Le correggo con test-author dopo la cura.

#### T-EN passo 3 — la cura ✅ (2026-10-13)
> **Note implementazione**: `/tmp/libreFolio_ten_apply.py`, 15 operazioni su 7 file, provate prima a secco. Gli 8 file di test passano 150/150 (log `/tmp/libreFolio_ten_after.log`).
>
> **Cosa cambia, file per file**:
> - **`ChartSignal.ts`**:
>   - `protected static text(key, values)`, il catalogo letto con `fromStore(_)`. Il lettore nasce alla prima etichetta, così un modulo che non etichetta nessun segnale non tocca svelte-i18n: serve ai test che sostituiscono `$lib/i18n` per intero.
>   - Il commento di `suffix`: ora è un gettone tradotto con `signals.units.<gettone>`, come l'`x-suffix` del backend.
> - **`LinearSignal.ts`, `CompoundSignal.ts`, `SineSignal.ts`**:
>   - `getLabel()` passa dal catalogo, con le cifre di `formatPercent` (`signed: false, trim: true`; l'offset col segno) e di `formatFixed(…, 2, {trim: true})`;
>   - `annualRate.suffix` diventa `'percentPerYear'`.
> - **`ChartSignalsSection.svelte:613`**: il ramo locale scrive `translateOr($t, 'signals.units.' + suffix, suffix)`, cioè lo stesso esito del ramo backend (`SignalParamControl`).
> - **`PriceChartFull.svelte:786-789`**: le tre righe vengono da `chart.tooltip.*`; i giorni di sfasamento sono scritti con `formatFixed(…, 0)`.
> - **`ProviderAssignmentSection.svelte:354-355`**: `assets.probe.points`, con `count` per il plurale e `n` per la cifra.
>
> **Backlog**:
> - T-EN1 e T-EN2 sono marcate ✅; il commit lo aggiunge il coordinatore.
> - Le voci nuove T-ISO (F1) e T-FB (F2) sono in fondo alla sezione T.

#### T-EN passo 4 — i gate ✅ (2026-10-13)
> **Note implementazione**:
> - **Etichette dei test**: test-author ha corretto quelle scambiate (T-EN1 per la sonda, T-EN2 per i segnali). Ancora 150/150.
> - **Corsia 6164**, 8 azioni in sequenza, tutte `exit=0` (log `/tmp/libreFolio_t1_tenv_*`):
>
>   | azione | risultato |
>   |---|---|
>   | `utils gate-plugin-i18n-ownership` (R1–R4) | 45 |
>   | `utils gate-i18n-usage` | 195 |
>   | `utils gate-i18n-catalog` | 176 |
>   | `front-utility core-unit` | 4 099 |
>   | `front-utility component-unit` | 3 090 |
>   | `front-asset asset-unit` | 762 |
>   | `check-orphans` | pulito |
>   | `front-asset asset-detail` (E2E, prova a runtime della pagina coi grafici e i segnali) | 32 |
>
>   Alla fine la porta 6164 è libera.
> - **Statici e catalogo**:
>   - `dev.py front check`: 0 errori, 0 avvisi; Prettier pulito sui file toccati.
>   - `dev.py i18n check`: 4 359 chiavi in modalità stretta.
> - **`dev.py i18n audit`**:
>   - 0 chiavi morte e 0 traduzioni mancanti.
>   - Le chiavi nuove risultano usate, tranne `signals.units.percentPerYear`, che è «non verificata». È il limite noto della skill: chi costruisce la chiave è `ChartSignalsSection`, mentre il gettone sta in `LinearSignal.ts`, a due import di distanza, come per `chartSettings.params.amplitude`.
>   - «Non verificata» non vuol dire morta, e nessun gate la conta.
> - **v1.1.0**: le quattro scritte inglesi c'erano già. Per il CHANGELOG serve quindi una riga 🐛.

### Checkpoint T-EN 🧊 (2026-10-13) — FROZEN, in attesa del coordinatore
- **Base**: `104ba23d0`. **Delta**: 23 file modificati più 2 nuovi, 25 in tutto.
- **Commit proposti**:
  1. `/tmp/libreFolio_commit_t_ten_1.txt`, `fix(i18n): chart and probe texts in UI language`: codice, test, cataloghi, runner;
  2. `/tmp/libreFolio_commit_t_ten_2.txt`, `docs(journal): record T-EN1 and T-EN2`: il piano e il backlog.

### T-SHK + T-CL — via (coordinatore, 2026-10-13 03:15)
- **Base**: `273b188ea` (treno 82), pulita. Corsia 6164.
- **Carico**: finché il coordinatore non dà il «via», solo spec singole a 1 worker, perché gira la galleria di M.
- **Mandato**:
  1. **D5, la tabella dello shock** (README della 02, «Difetti noti»): etichette leggibili al posto degli id dei bucket; la prima colonna col nome della dimensione; i gruppi a peso zero non diventano righe, nel frontend, senza cambiare l'API.
  2. **D8**: il drawdown massimo allineato nei cataloghi fr e it.
  3. **D14**: il suggerimento della favicon, la descrizione del provider BoE, il commento di `fmtCurrency`.
- **Regole**: prima un'analisi breve, poi si parte senza aspettare. Ci si ferma solo per un cambio di API o di backend, o per una scelta di prodotto che non è nel mandato. Test via test-author, rossi prima.

#### T-SHK — analisi (2026-10-13)
**Le superfici** (verificate su `273b188ea`):
- `levels/l4/L4Shock.svelte`:
  - `rowLabel` (`:100-106`) restituisce `row.bucketId` grezzo;
  - anche l'editor del dettaglio scrive l'id grezzo (`:136-148`: testo, `title`, `aria-label`). È lo stesso difetto e lo curo insieme;
  - `data-bucket-id` resta.
- `levels/l4/TornadoChart.svelte:101`: la prima colonna ha sempre `risk.levels.l4.table.asset`. Il componente è condiviso col replay, che deve tenere «Asset».
- `levels/l4/scenarioHelpers.ts:164-176` (`tornadoRows`): un bucket con peso 0 diventa una riga a 0,0 %. Il peso è `bucketShares`, cioè la stessa colonna *Weight* che il lettore vede.
- **La resa del pannello legacy**: `RiskAnalysisPanel.svelte:357-365` (`stressBucketLabel`):
  - `Other` → `common.other`;
  - `european_union` → `risk.stress.europeanUnion`;
  - una classe → `assets.types.<TIPO>`;
  - un settore → emoji + `sectors.<chiave>`;
  - un paese → bandiera + nome. I dati di riferimento si caricano per lingua (`ensureCountriesLoaded`, `ensureSectorsLoaded`).
- **Il nome della dimensione esiste già**: `risk.stress.dimensions.{asset_class,sector,geography}` nelle 4 lingue («Asset class», «Sector», «Geography»). Nessuna chiave nuova.

**La cura scelta**:
1. **Una resa sola.** `stressBucketLabel(bucket, dimension, words)` diventa una funzione pura in `components/risk/riskAnalysisHelpers.ts`, col vocabolario iniettato (traduttore, emoji del settore, paese).
   - Il pannello legacy la chiama, e la sua funzione locale diventa una riga; L4Shock la usa per le righe e per l'editor del dettaglio.
   - Un codice senza traduzione (tipo o settore sconosciuto) o un paese sconosciuto si scrive com'è, mai come chiave del catalogo: è la stessa regola di `exposureCategoryLabel` del PAC.
2. **L4Shock**:
   - `rowLabel` diventa una funzione `$derived`: si riscrive al cambio di lingua e quando arrivano i dati di riferimento (un contatore, come nel pannello legacy);
   - la dimensione è quella della risposta (`stressImpactDimension(output.dimension, …)`).
3. **`TornadoChart`**:
   - una prop facoltativa `nameHeader`; senza, resta «Asset» (il replay non cambia), e L4Shock passa `risk.stress.dimensions.<dimensione>`;
   - `columns` legge `label` e `nameHeader` dentro il `$derived`, così un'etichetta nuova ridisegna la tabella.
4. **`tornadoRows`**: nel ramo dei bucket, con i pesi noti (`shares !== null`), un bucket a peso 0 non diventa riga. Senza pesi il ramo è già vuoto (`contribution_return` è `null`). L'API non cambia.

**Le scelte notate**:
- l'ordine dell'editor del dettaglio resta quello degli id;
- un portafoglio senza nessun bucket posseduto non mostra la tabella (`rows.length === 0`, il comportamento di oggi), ma il totale resta;
- la seconda resa delle categorie, `exposureCategoryLabel` del PAC, va in una voce di backlog: unirle è un riordino dopo la 1.2.

**I test (test-author)**:
- **Rossi**:
  - `scenarioHelpers.test.ts`: niente riga a peso 0, con le guardie per i bucket posseduti, il ramo per asset e lo scope senza pesi;
  - `L4Shock.test.ts`, nuovo (jsdom, controller vero con `setResult('stress', …)`, come `L4Replay.test.ts`): le etichette di classi, settori, paesi, `Other` e `european_union` dal catalogo e dai dati di riferimento, in it o fr; l'intestazione; l'editor del dettaglio; il cambio di lingua sul posto;
  - `TornadoChart.test.ts`: la guardia del default «Asset» per il replay.
- **E2E**: `front-portfolio risk` (shock con lo stub) a 1 worker, dopo la cura.

#### T-CL — analisi (2026-10-13)
**D8, il drawdown massimo**:
- Le chiavi sono `risk.metrics.maxDrawdown` (pannello legacy, `:192`) e `risk.levels.l1.technical.worst` (L1, `:400`).
- Oggi: it «Drawdown massimo» contro «Massimo drawdown»; fr «Repli maximal» contro «Perte maximale». In en ed es sono già uguali.
- **Il termine del glossario**: `cd0b404d2` fissa «repli» per *drawdown*, ma la tabella del glossario (`mkdocs_src/aphra-pipeline/glossaries/glossary.json`) dà per *maximum drawdown* it «drawdown massimo» e fr «perte maximale». La doc usa questi due 40 e 45 volte, gli altri due zero.
- **Cura**: it `risk.levels.l1.technical.worst` → «Drawdown massimo»; fr `risk.metrics.maxDrawdown` → «Perte maximale», con `dev.py i18n update`.
- **Rosso**: un test di catalogo, «le due etichette del drawdown massimo coincidono in ogni lingua».

**D14** (testi e commenti, senza test rossi; il comportamento è coperto altrove):
- **`brokers.iconUrlHint`** (`brokers/*.json:15`) diventa l'ordine reale di `brokerIconChain.svelte.ts:88-106`: icona personale, poi quella del plugin di import predefinito (se non è generico), poi la favicon del portale, poi l'icona di un plugin generico. Con `dev.py i18n update`.
- **BoE** (`fx_providers/boe/plugin.py:91-94`, `description_i18n` in linea; i plugin FX non hanno frammenti i18n): «il provider di LibreFolio copre 15 valute». Solo il testo: l'API non cambia.
- **`GrowthChart.svelte`** (commento di `fmtCurrency`, ~`:2156`): il segno viene da `uiLocale()`, non dalla locale del browser. Ho verificato su Node: `-` (U+002D) in en-GB, en-US, it, fr, es e nelle loro regioni.

#### T-SHK + T-CL — tre aggiunte (coordinatore, 2026-10-13 03:39, dalla galleria completa di M)
1. **Priorità alta, blocca il tag.** `ProviderComparisonModal`: `data-dist-pct` è la stringa mostrata e, da `5b2aad5c4` (M-18 CP1), segue la lingua (`100,00%`). La galleria (`e2e/fixtures/galleryProviderCompare.ts:309`) si aspetta `'100.00%'` e diventa rossa su desktop e mobile.
   - **Cura**: il nome dell'attributo non cambia. `formatDistribution` dà a ogni voce `pct` (mostrato, localizzato) e `hook` (`(v×100).toFixed(2)%`, uguale in ogni lingua), e l'attributo legge `hook`.
   - È l'aggancio stabile che `ProviderComparisonModal.test.ts:38` documenta: né la galleria né i test vanno cambiati.
   - Rosso prima, in it o fr.
2. **`AssetModal.svelte:1949`**: il placeholder «Brief description of the asset…» è scritto fisso. Chiave nuova `assets.modal.descriptionPlaceholder` (`where` → `i18n/assets/`), con `dev.py i18n add`. Rosso prima.
3. **I campi DU/AU del `DateRangePicker` in ISO**: è una scelta, non un residuo.
   - Tutte le toolbar di pagina usano `compact`, e `displayDate` restituisce l'ISO apposta (`DateRangePicker.svelte:1108`, «fits narrow cells»), già nella v1.1.0.
   - Non si tocca: risposta data al coordinatore.
- **Ordine**:
  1. i rossi del primo giro (D5, D8) visti rossi;
  2. lo script del catalogo (`/tmp/libreFolio_shk_i18n.sh`: D8, la favicon, la chiave del placeholder);
  3. i rossi delle aggiunte 1 e 2;
  4. la cura del codice (`/tmp/libreFolio_shk_apply.py`, 21 operazioni su 8 file più un file nuovo, provata a secco).
- **Carico**: la galleria è finita; io resto a spec singole sulla 6164.

#### T-SHK + T-CL passo 1 — i rossi del primo giro e il catalogo ✅ (2026-10-13)
> **Note implementazione**: test-author I ha scritto 19 rossi; li ho visti rossi anch'io, un file alla volta a 1 worker (log `/tmp/libreFolio_shk_red_*.log`).
>
> | file | rossi | verdi |
> |---|---|---|
> | `scenarioHelpers.test.ts` | 2 | 59 |
> | `L4Shock.test.ts` (nuovo, jsdom) | 16 | 5 |
> | `TornadoChart.test.ts` (3 guardie nuove: «Asset» senza la prop) | 0 | 27 |
> | `riskGlossary.test.ts` (nuovo) | 1 | 3 |
>
> - **Cosa leggono i rossi di `L4Shock`**: le etichette di classi, settori e paesi; il codice sconosciuto scritto com'è; l'intestazione della dimensione; i bucket non posseduti; l'editor del dettaglio; il cambio di lingua.
> - **Nel runner**, una riga per file nuovo:
>   - `L4Shock.test.ts` in `front_portfolio_risk_levels_component` (`_frontend_portfolio.py`);
>   - `riskGlossary.test.ts` in `front_utility_unit` (`_frontend_utility.py`).
> - **Le note di test-author, accettate**:
>   - il blocco dello shock carica da sé i nomi dei paesi per lingua;
>   - con pesi ma senza `bucket_audit` la tabella sparirebbe, ma oggi il backend lo manda sempre;
>   - un gruppo geografico definito dall'host, diverso da `european_union`, resta un id grezzo.
>
>   Questi ultimi due sono limiti noti, da scrivere nel checkpoint.
> - **Il catalogo** (`/tmp/libreFolio_shk_i18n.sh`, `dev.py i18n update/add`, log `/tmp/libreFolio_shk_i18n.log`):
>   - it `risk.levels.l1.technical.worst` → «Drawdown massimo»; fr `risk.metrics.maxDrawdown` → «Perte maximale»;
>   - `brokers.iconUrlHint` nelle 4 lingue;
>   - la chiave nuova `assets.modal.descriptionPlaceholder`;
>   - `i18n check`: 4 360 chiavi in modalità stretta; diff di 10 file sorgente.
> - **In corso**: i rossi delle aggiunte 1 e 2, dallo stesso test-author.

#### T-SHK + T-CL passo 2 — i rossi delle aggiunte e la cura ✅ (2026-10-13)
> **Note implementazione**:
> - **Rossi del secondo giro** (stesso test-author), visti rossi da me:
>   - `ProviderComparisonModal.test.ts`: 2 rossi, it `60,00%` e fr `60,00 %` contro `60.00%`; più le guardie del testo localizzato. 22 verdi;
>   - `AssetModal.test.ts`: 2 rossi, il placeholder inglese in it e fr; più la guardia inglese. 30 verdi.
> - **Cura**: `/tmp/libreFolio_shk_apply.py --apply`, 21 operazioni su 8 file, più il file nuovo `components/risk/stressBucketLabel.ts`.
> - **Verde, file per file a 1 worker**:
>
>   | file | test |
>   |---|---|
>   | `scenarioHelpers` | 61/61 |
>   | `L4Shock` | 21/21 |
>   | `TornadoChart` | 27/27 |
>   | `riskGlossary` | 4/4 |
>   | `ProviderComparisonModal` | 24/24 |
>   | `AssetModal` | 32/32 |
>
> - **I vicini**: `riskAnalysisHelpers` 96, `stressBuckets` 5, `riskPanelController` 102, `RiskResultFrame` 20, `RiskCardGrid` 7, `L4Replay` 40.
> - **I gate che leggono i sorgenti**: `htmlInterpolation` 26, `htmlSink` 7, `moneyRenderSites` 6, `catalogIcuLocale` 17. Tutti verdi.

#### T-SHK + T-CL passo 3 — i gate ✅ (2026-10-13)
> **Note implementazione** (corsia 6164, un'azione alla volta, E2E a 1 worker; log `/tmp/libreFolio_t1_shkv_*`):
>
> | controllo | risultato |
> |---|---|
> | `utils gate-plugin-i18n-ownership` | 45 |
> | `utils gate-i18n-usage` | 195 |
> | `utils gate-i18n-catalog` | 176 |
> | `check-orphans` | pulito |
> | E2E `front-portfolio risk` (lo shock con lo stub) | 38/38 |
> | E2E `front-portfolio risk-asset-detail` (il pannello legacy) | 5/5 |
> | E2E `front-transaction tx-import-asset-inspector` (il dialogo dell'asset) | 5/5 |
>
> - `dev.py front check`: 0 errori, 0 avvisi; Prettier pulito.
> - `ruff` e `black --check` puliti su `boe/plugin.py`.
> - `dev.py i18n audit`: 0 chiavi morte e 0 traduzioni mancanti; le «non verificate» restano le 4 di prima.
> - Porta 6164 libera.
> - **Backlog**: T-CAT (due rese delle categorie: PAC e rischio) e T-GRP (i gruppi geografici dell'host, e il limite dei pesi senza `bucket_audit`).
> - **README della 02**: la voce «L4, la tabella dello shock» di «Difetti noti» è marcata risolta.
> - **CHANGELOG**: la tabella dello shock è nata nella 1.2, quindi niente 🐛 a parte. Le correzioni entrano nella riga che la descrive (L316 a `273b188ea`).
>   - Il placeholder della descrizione c'era già nella v1.1.0: vale una riga 🐛 minima, oppure si unisce alle righe «follow your language».
>   - D8 rende vera L263 («drawdown is named the same way»).

### Checkpoint T-SHK + T-CL 🧊 (2026-10-13) — FROZEN, in attesa del coordinatore
- **Base**: `273b188ea`.
- **Commit proposti**:
  1. `/tmp/libreFolio_commit_t_shk_1.txt`, `fix(assets): stable dist hook, translated hint`;
  2. `/tmp/libreFolio_commit_t_shk_2.txt`, `fix(risk): name shock buckets, hide unheld ones`;
  3. `/tmp/libreFolio_commit_t_shk_3.txt`, `fix(i18n): one drawdown term, real icon order`;
  4. `/tmp/libreFolio_commit_t_shk_4.txt`, `docs(journal): record T-SHK and T-CL`.
- I file per commit sono nel manifest `/tmp/libreFolio_shk_manifest.txt`.
