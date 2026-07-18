# FIFO UI v3 — Implementation Log

Spec: `highLevel-v3.md` + messaggio [[PLAN]] (§1–18). Report finale: `final-report-v3.md`.

## Wave 0 — Diagnosi (completata)

Decisioni utente: full autopilot · nuova sezione "Altri effetti" dentro il pannello lotti (riuso `OtherPeriodEffectsTable`) · verifica visiva finale = checklist manuale.

### Backend
- `LotSummarySchema` (`schemas/portfolio.py:509-535`) HA: realized_pnl, cumulative_proceeds (≈sale_proceeds), open_value, total_value, pnl (=market+realized, no income), relative_return (≈open_return), reference_price_source, original_cost (≈opening_value), open_quantity, original_quantity, opening_unit_price.
- MANCANO per-lotto: `asset_income`, `market_pnl`, `total_pnl`, `cash_yield`, `total_return`, `value_source`.
- Dividendi/interessi asset-linked NON allocati: FIFO engine gestisce solo BUY/SELL/ADJ/TRANSFER/SPLIT (`fifo_lot_engine.py:369-432`); `_load_transactions` esclude `quantity IS NULL or ==0` (`lots_analysis_service.py:449-451`) → DIVIDEND/INTEREST fuori dal load.
- Estimated-at-cost NON implementato: con `market_price None` i punti value/return vengono saltati (`1179-1180`, `1227-1228`) → grafici vuoti; nessun `value_source`, nessun `CURRENT_PRICE_ASSUMED_AT_COST`.
- Range origin-based GIÀ corretto: `computed_from = transactions[0].date`, `date_from` limita solo la history (`204`, `230`). → verifica + test.
- Proventi non allocati (no asset_id) GIÀ gestiti dal Portfolio Engine → righe "Unallocated income/costs" per broker (`portfolio_service.py:1656-1702,1921-1988`), `OtherPeriodEffect` (`schemas/portfolio.py:327-348`, category Income/Cost/Other), rese da `OtherPeriodEffectsTable`.

Helper chiave riusabili: `_open_quantity_on_date(fragments, date)` (`1388-1389`), `_closure_proceeds_prefix` (`1364`), `_value_snapshot_on_date` (`1268`), `_lot_history_end_date` (`1357`), `_build_market_price_map` (`609`), `_FxRateResolver` (need/convert/load), `active_fragments`, `get_lot_states`.

### Frontend
- `LotGanttChart`: ECharts custom series (nessuna colonna HTML fissa), lane `LANE_ROW_HEIGHT=72` (→26-30px), NO asse sticky, NO lane figlie per transfer, NO marker eventi. Highlight già reattivo nel codice.
- `LotComparisonChart`: modi value/return/price; toggle Aggregato/Per-lotto implicito; tooltip fix per-serie. Selezione vuota ≠ tutti (§13 da implementare).
- `UnifiedLotsTable`/`DataTable`: search box (rimuovere), column selector (fixare), rowActions; NIENTE footer/aggregazione (net-new).
- `LotCustodyModal`: mancano asset_income/cash_yield/market_pnl/total_pnl/total_return/value_source.

## Wave 1 — Backend (in corso)

### Design metriche (formule)
- `market_pnl = pnl - realized_pnl` (identità: pnl esistente = market+realized). In estimated: `market_pnl = 0`.
- `asset_income` = somma allocazioni pro-rata dividendi/interessi asset-linked (target currency).
- `total_pnl = pnl + asset_income` (estimated: `realized_pnl + asset_income`).
- `cash_yield = asset_income / opening_value` (opening_value = converted original_cost; guard >0).
- `total_return = total_pnl / opening_value` (guard >0). Coerente col last point di return_history.
- `open_return = relative_return` (invariato).
- `value_source ∈ {MARKET_PRICE, ESTIMATED_AT_COST}`.

### Allocazione proventi (§4.2)
Per tx DIVIDEND/INTEREST con asset_id in scope, alla `transaction.date`: pesi `w_i = openQty_i / Σ openQty` sui lotti LONG aperti; `Income_i = convert(tx.amount) · w_i`; conservazione `Σ = total` con residuo arrotondamento assegnato deterministicamente. Cumulativo per-lotto (scalare + prefix per-data per value/return history).

### Estimated-at-cost (§9)
`has_market = price_lookup.latest() is not None`. Se no prezzo: `open_value = openQty · converted_opening_unit_price`, `market_pnl = 0`, `value_source = ESTIMATED_AT_COST`, DQ issue `CURRENT_PRICE_ASSUMED_AT_COST`. Value/return history: emettere punti stimati invece di saltarli.

### Wave 1 — COMPLETATA ✅ (backend)

File modificati:
- `backend/app/schemas/portfolio.py`: `IssueCode.CURRENT_PRICE_ASSUMED_AT_COST`; `LotValueSource` literal; `LotSummarySchema` +asset_income/market_pnl/total_pnl/cash_yield/total_return/value_source; `LotValueHistoryPoint.income`; `LotReturnHistoryPoint.income` + total_return include income.
- `backend/app/services/lots_analysis_service.py`: `_load_income_transactions` (DIVIDEND/INTEREST asset-linked, no quantity filter); `_allocate_asset_income` (pro-rata su LONG aperti, conservazione running-remainder, prefix per-data); estimated-at-cost in `_build_lot_summaries`/`_build_value_history`/`_build_return_history`; registrazione fx needs income+estimated prima di `fx_resolver.load`; DQ issue `CURRENT_PRICE_ASSUMED_AT_COST`; message key.
- `frontend/src/lib/i18n/{en,it,fr,es}.json`: `dataQuality.currentPriceAssumedAtCost`.
- `frontend/src/lib/api/generated.ts` + `openapi.json`: rigenerati via `./dev.py api sync`.

Test: `test_lots_analysis_service.py` 14/14 (10 pre-esistenti invariati + 4 nuovi: pro-rata+partial sell+conservazione, FX income, estimated-at-cost crowdfunding, income dopo lotto chiuso). `TestLotsAnalysisEndpoint` 7/7. ruff+black OK. i18n 1674/1674.

Formule verificate: `market_pnl = pnl - realized_pnl` (identità); `total_pnl = market_pnl+realized+income`; estimated → open_value=cost·open/orig, market_pnl=0, total_pnl=realized+income. Range origin-based già corretto (nessuna modifica). Proventi senza asset → già Portfolio Engine (Wave 2 render).

### Wave 2 — frontend (in corso)

#### Fleet I/§14 (parziale) — LotCustodyModal metriche v3 ✅
File: `frontend/src/lib/components/brokers/lots/LotCustodyModal.svelte`.
- Derived nuovi: `lotAssetIncome`, `lotMarketPnl`, `lotTotalPnl`, `lotCashYield`, `lotTotalReturn`, `lotValueSource`, `lotIsEstimated`, `lotHasIncome`.
- Righe summary aggiunte (condizionali): Proventi (`asset_income`, solo se ≠0), Market P&L, P&L complessivo (`total_pnl`), Rendimento complessivo (`total_return`), Rendimento da proventi (`cash_yield`, solo se income). Nota "Valore stimato al costo" sotto Valore corrente quando `value_source=ESTIMATED_AT_COST`.
- testid: `lot-custody-modal-{asset-income,market-pnl,total-pnl,total-return,cash-yield,value-source}`.
- i18n `brokers.lots.modal.{assetIncome,marketPnl,totalPnl,cashYield,totalReturn,estimatedAtCost}` in 4 lingue.
- Formattazione numeri: `formatQuantity` usa già `formatDecimalForDisplay(minFrac:0)` → interi senza zeri di coda ("1 CHIP", non "1.000000 CHIP"). Nessun fix necessario.

Verifica: `svelte-check` 0 errori/0 warning; `./dev.py i18n audit` 1679/1679 (0 incomplete). Client generato già contiene i 6 campi (Wave 1 api sync).

> **⚠️ Nota**: i18n JSON NON vanno passati a `prettier` (config repo `tabWidth:4` → riscrive l'intero file a 4 spazi; il repo li tiene a 2 spazi). Usare edit mirati o `json.dump(indent=2, ensure_ascii=False)`. `.prettierignore` non li esclude ancora — potenziale trappola.
> **Nota**: trovato blocco `fx.aiExportMenu/aiExport/aiExportBuilding` già presente come modifica non committata nel working tree (feature "AI Export" FX, estranea a questo task) — lasciato invariato.

### Wave 2 — restante (stream pesanti ECharts/tabella, verifica visiva manuale)
Per preferenza utente (verifica UI manuale, non screenshot automatici) i seguenti stream restano da implementare con verifica dal vivo nel browser:
- Fleet E Gantt (`LotGanttChart.svelte`): lane 26-30px, branch gerarchici, asse sticky, marker eventi, reattività selezione, tooltip lotto (bug hover infobox mancante), min-width Stato/Custodia.
- Fleet F Bolle Performance (nuovo `LotPerformanceBubbleChart.svelte`): Timeline/Performance, ABS/%, LONG only.
- Fleet G Tabella (`UnifiedLotsTable.svelte`): rimuovere ricerca globale, fix column selector, ordine/default, colonna Azioni ⋮, footer aggregato (net-new in DataTable), min-width Stato/Custodia.
- Fleet H Grafici/proventi + sezione "Altri effetti del periodo" (riuso `OtherPeriodEffectsTable`): marker dividend/interest, styling estimated, bug "linee scompaiono su hover", date solo mese/giorno nel 3° grafico.
- Fleet I Navigazione tx: "Vai alla transazione di apertura" → view-mode modal + scroll + pulse.
- Trasversali: selezione implicita §13 (vuoto=tutti visibili), doppio click eventi §9, i18n WAC→PMC (IT).

---

### Wave 2 — COMPLETATA ✅ (frontend, lead + 5 fleet)

**Dispatch**: 4 fleet leaf-component paralleli (owner unico per file) + lead che possiede `LotsAnalysisPanel.svelte`, `LotWacPriceChart.svelte`, i18n JSON e client generato. 1 fleet dedicato per la navigazione tx.

#### Fleet E — Gantt (`LotGanttChart.svelte`) ✅
Ricostruito: lane compatte 30px / gap 4px / branch figlio 24px; highlight sul **segmento** (non fascia). Branch gerarchici: lane figlia nasce **solo alla data di biforcazione** (transfer/split). Marker inferiti sulla vita del lotto (BUY ▲, SELL ▼, TRANSFER ◆, ADJ+ +, ADJ− ×, SPLIT │); spessore cambia dopo l'evento. **Asse X sticky** su scroll verticale (area lane scrollabile + asse sticky sincronizzato su date_from/to/zoom/pan/tick/formatter/grid col grafico sopra). **Reattività selezione immediata** (custom series si aggiornano su cambio `selectedLotIds` senza zoom/resize). Tooltip lotto arricchito (Opening/Size/Current/Result con asset_income, market_pnl, cash_yield via `translatedOr`). `export function pulseLot(id)` preservata. Nuova prop opzionale `events={lotEvents}`.

#### Fleet F — Bolle Performance (nuovo `LotPerformanceBubbleChart.svelte`) ✅
Toggle interno `[ABS][%]` (testid `lot-bubble-mode-abs/-pct`); `x = OpeningDate` (fisso); ABS `y = total_pnl`, % `y = total_return`; linea verticale zero→risultato (verde positivo / rosso negativo / neutro ≈0); dimensione bolla = valore apertura (remapping min/max leggibile); colore = segno; broker via tooltip. **Solo LONG** (SHORT esclusi con grazia). Selezione implicita.

#### Fleet G — Tabella (`UnifiedLotsTable.svelte` + core `DataTable.svelte`) ✅
Rimossa ricerca globale. Fix column selector (toggle immediato + persistenza policy DataTable). Nuovo ordine/default colonne (§12.3); condizionali Stato/Direzione/Proventi. min-width ridotte per Stato/Custodia. Colonna Azioni `⋮` (stesso menu: dettaglio / gantt / tx apertura / copia id, con tooltip identificativo). **Footer aggregato net-new** in `DataTable` (somme + medie ponderate; usa righe selezionate se esistono, altrimenti visibili; allineato alle sole colonne visibili).

#### Fleet H — Grafici, proventi & Altri effetti (`LotComparisonChart.svelte`, `LotsOtherEffectsSection.svelte`) ✅
Marker proventi (linee verticali tratteggiate: DIVIDEND teal, INTEREST viola) su 1° grafico + Valore/Rendimento; tooltip tipo/data/broker/importo/lotti. Styling "valore stimato al costo" dove `value_source=ESTIMATED_AT_COST`. Nuova sezione **"Altri effetti del periodo"** (`LotsOtherEffectsSection`) nel pannello, riusando i dati del Portfolio Engine (`positions_contribution.{unallocated, other_effects}`) filtrati ai broker dell'asset — nessuna duplicazione del calcolo.

#### Fleet I — Navigazione transazione (`routes/(app)/transactions/+page.svelte`) ✅
"Vai alla transazione di apertura" → naviga a `/transactions?highlight=<id>`, consuma il param, centra la riga, apre la Transaction Modal in **view mode**; alla chiusura pulse sulla riga. Nessuna chiave i18n nuova. Back preservato.

#### Backend §11 — income events markers (lead, `be-income-events`) ✅
Estensione contratto per esporre i marker proventi: `LotAnalysisType.INCOME_EVENTS`, `LotIncomeEventKind`, `LotIncomeEventSchema` (type/date/broker_id/transaction_id/amount/lot_ids), campo `LotsAnalysisResponse.income_events`. `_allocate_asset_income` ora ritorna anche il payload per-transazione degli eventi allocati (solo quando `total_qty>0`); `income_events` gated su `INCOME_EVENTS in analyses`, trimmato a `display_from..actual_to`. `./dev.py api sync` rigenerato. Test: +`test_income_events_payload_exposes_allocated_income_markers` (15/15 service). 37/37 lots+portfolio API tests verdi.

#### Integrazione lead (`LotsAnalysisPanel.svelte`) ✅
- Toggle `[Timeline][Performance]` (Gantt vs Bubble).
- `events={lotEvents}` al Gantt; `{incomeEvents}` a `LotComparisonChart` **e** `LotWacPriceChart` (quest'ultimo esteso con prop `incomeEvents` + helper marker/tooltip/colore).
- `INCOME_EVENTS` in `requested_analyses`; mapping `response.income_events → incomeEvents`.
- **§13 selezione implicita**: `selectedLotIds=[]` = tutti i visibili (bolle/Valore/Rendimento/Prezzo/footer); niente checkbox tutte selezionate all'avvio.
- **§9 doppio click eventi** (1° grafico): `onEventDoubleClick={handleEventDoubleClick}` su `LotWacPriceChart` → mappa evento→lot_ids coinvolti (match `transaction_id`/`related_transaction_id`, copre coppie TRANSFER), aggiorna selezione, passa a Timeline, `pulseLot` sul primo lotto.
- Sezione "Altri effetti del periodo" (`LotsOtherEffectsSection`) con fetch `fetchReport(...includeContribution)`.

#### i18n (lead) ✅
Scan robusto (letterali + dinamici `valueSource.${...}`) su tutti i componenti lots → 44 chiavi mancanti aggiunte in EN/IT/FR/ES sotto `brokers.lots.*` (flat + `tooltip.*` + `valueSource.*`) + 2 chiavi toggle (`viewTimeline`, `viewPerformance`). WAC→PMC(it)/CMP(fr)/PMC(es) già in Wave 1. Rimossa chiave orfana `brokers.lots.searchPlaceholder` (ricerca globale rimossa §15). Metodo: `json.dump(indent=2, ensure_ascii=False)+'\n'` (byte-identico al repo, **mai prettier**).

**Validazione finale Wave 2**:
- `./dev.py front check` → **0 errors, 0 warnings**.
- `./dev.py i18n audit` → **1726/1726 complete, 0 incomplete** (48 "unused" = falsi positivi: chiavi `brokers.lots.tooltip.*` usate via `translatedOr()`, helper non riconosciuto dallo scanner statico).
- `pytest` lots_analysis + portfolio_api + income_events → **37 passed**.
- `prettier --check` su tutti i componenti lots + tx page + DataTable → **All matched files use Prettier code style**.

**Fuori scope / segnalato all'utente** (non corretto silenziosamente):
- **Bug responsività WAC modal** (switch desktop↔mobile non ricalcola il layout della sezione WAC): diagnosi checkpoint 011 → nessuna cattura JS della larghezza in `WacPreviewSection`/`CompactCashCell`/`ModalBase` (tutto CSS/Tailwind `sm:`); il probe Playwright con resize reale della finestra **riflette correttamente** (non riproducibile via real resize). Probabile causa: emulazione device DevTools o build stale. Richiede repro esatto dall'utente (finestra vs device toolbar) → richiesta separata.
- **BRIM FEE/TAX asset-linked ai lotti** (`TODO_ProssimeAttivita.md`): task dedicato successivo (tocca cost basis/WAC engine, decisione di prodotto).

---

## Round bugfix 2 (18 lug 2026) — review manuale utente

6 fix estetici frontend + 1 verifica matematica backend. Vincoli: matematica → verifica + test; estetica → implementa + verifica build (svelte-check/build), **niente** E2E/gallery; riferire click-path manuali.

#### fix2 — toggle presentazione lotti (`LotComparisonChart.svelte`) ✅
Rimossi i due `<span>✓` dai bottoni `Aggregato`/`Per lotto`. Container toggle passato a `w-fit self-start` → eliminato il "3° pulsante" fantasma che si estendeva a tutta la larghezza (era il container `flex` block-level che ereditava la larghezza del `flex-col` genitore).

#### fix4 — marker/infobox per-lotto in modalità Rendimento (`LotComparisonChart.svelte`) ✅
Root cause: le righe per-lotto usano `trigger:'item'` (workaround del bug ECharts 6.0.0 axis-trigger che fa sparire le linee) → in Rendimento nessuna serie guida il `tooltip.trigger:'axis'` a livello di grafico → `params` vuoto → nessun infobox. Fix: `ensureAxisTriggerAnchor()` antepone una serie linea nascosta (opacity 0, `symbol:'none'`, id `axis-trigger-anchor`, dati `[[min,0],[max,0]]`) **solo** quando nessuna serie-dati partecipa all'asse; l'ancora è filtrata da tutti i tooltip builder via `seriesId`. Soppressi anche i "cerchietti sui primi 2 segnali" (`symbol:'none'` su `value-residual`/`value-proceeds`, le uniche serie value senza override). Nota limite ECharts confermata: non è possibile mettere marker on-line per-lotto sulle linee; l'indicatore resta la linea verticale d'asse + righe infobox con pallino colorato per-lotto che compaiono/scompaiono con la selezione.

#### fix5 — Gantt: barra sparisce zoomando oltre lo start (`LotGanttChart.svelte`) ✅
`filterMode:'filter'` → `filterMode:'none'` sui dataZoom (main + asse). Ora la barra viene clippata al bordo del range invece di scomparire quando la sua x di start esce dalla finestra (`renderItem` già clippava correttamente).

#### fix6 — bolle Performance migrate su PMC/Prezzo (`LotWacPriceChart.svelte`) ✅
Rimosso il toggle `[Timeline][Performance]` + il componente `LotPerformanceBubbleChart` (file eliminato); il Gantt è ora sempre renderizzato. Overlay bolle migrato in `LotWacPriceChart`: ABS → y = `price_at_opening × (1 + total_return)` (unit-safe: il rapporto assorbe `quote_base_quantity`/FX), connettore verticale tratteggiato dal prezzo del giorno alla bolla (verde se return>0, rosso se <0, grigio se ~0), raggio ∝ `open_quantity`; % → y = `total_return×100`, raggio ∝ `original_cost`, nessun connettore. Colore = colore broker (`getBrokerColor`), bordo tratteggiato se `ESTIMATED_AT_COST`. Selezione implicita ([] = tutti; altrimenti dim non selezionati); click sulla bolla seleziona il lotto. Nuove prop `lots`/`selectedLotIds`/`onSelectionChange`.

#### fix7 — "Altri effetti del periodo" rimossa dal pannello lotti (`LotsAnalysisPanel.svelte`) ✅
Rimossi component `LotsOtherEffectsSection` (file eliminato), `loadOtherEffects` + `$effect`, stato `otherEffects*`, derived `assetBrokerIds`, import `fetchReport`. Resta la tabella portafoglio in `PositionsPanel` (sopra), unica fonte. Rimosse 13 chiavi i18n orfane sotto `brokers.lots.*` in EN/IT/FR/ES (`json.dump`, mai prettier).

#### verify — valore corrente per-lotto NON è un bug (backend) ✅
Segnalazione utente: 4 lotti stesso asset con valore corrente diverso (304,20 / 304,20 / 338,00 / 304,20). Verifica: `open_value = open_quantity × latest_market_price` (`lots_analysis_service.py:1014`), con `latest_market_price` scalare unico condiviso da tutti i lotti dell'asset (`:989`). → il valore per-unità è uniforme (8,45 €); la differenza è **solo** la quantità (40 vs 36). Nuovo test `test_same_asset_open_value_scales_with_quantity_only` riproduce i numeri reali dell'utente e asserisce uniformità per-unità + coerenza dei totali (148 × 8,45 = 1250,60). **Corretto, non un bug.**

**Validazione round 2**:
- `./dev.py front check` → **0 errors, 0 warnings** dopo ogni file.
- `./dev.py front build` → build produzione OK.
- `prettier --check` sui 4 componenti lots → clean.
- `./dev.py i18n audit` → **1714/1714 complete, 0 incomplete** (dopo rimozione 13 orfane).
- `pytest test_lots_analysis_service.py` → **16 passed** (incl. il nuovo test di verifica).
- **Nessun** E2E/gallery lanciato (come da vincolo utente).
