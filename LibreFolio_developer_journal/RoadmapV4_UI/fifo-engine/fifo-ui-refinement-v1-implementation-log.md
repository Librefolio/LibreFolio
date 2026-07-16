# Log implementazione — Refinement FIFO UI v1

Piano sorgente: [`refinment-work-v1.md`](./refinment-work-v1.md) (869 righe). Segue la stessa fase FIFO Lot Engine v2 di cui è la rifinitura visuale/funzionale — vedi [`fifo-lot-engine-v2-implementation-log.md`](./fifo-lot-engine-v2-implementation-log.md) per il contesto originale.

## Fase 0 — Diagnosi (obbligatoria, prima di ogni modifica)

- [x] Diagnosi completa — 2026-07-16
> **Note implementazione**: diagnosi eseguita con chiamate reali a `POST /portfolio/lots/analysis` (asset BTC id=6 semplice, AAPL id=1 ricco — 10 lotti, tutti gli eventi) + screenshot browser reali via Playwright (login `e2e_test_user`, dashboard→Positions→riga→"Analizza Lotti") contro il server di test. 4 sub-agent "explore" paralleli hanno approfondito Gantt/WAC-marker/comparison-chart/tabella-modale.
> **⚠️ Scoperta critica**: un sub-agent "explore" (lettura statica del solo codice) aveva concluso che il Gantt fosse "già quasi corretto" (xAxis time-based, custom series renderItem, thickness/color/opacity già implementati). Lo screenshot reale ha dimostrato il contrario: il Gantt appariva come una lista verticale, zero barre visibili. Decisione presa: non delegare la Fase Gantt senza verifica visiva empirica — confermata necessaria da questo episodio.
> Causa radice #1 (CSS): `LotGanttChart.svelte:817` — `grid-cols-[240px,minmax(720px,1fr)]` usa una virgola invece di un underscore nella sintassi arbitrary-value di Tailwind. Verificato via `getComputedStyle`: `grid-template-columns` risolveva a un solo valore (`"1126px"`) invece di due, causando l'impilamento verticale delle due colonne (etichette + canvas) invece dell'affiancamento. Il canvas del grafico finiva 720px più in basso, fuori dall'area scrollabile visibile.
> Causa radice #2 (WAC marker): confermato che il backend calcola correttamente `lot_events` (EVENT_HISTORY) se richiesto, ma l'orchestratore (`LotsAnalysisPanel.svelte`) non lo richiedeva mai né lo passava a `LotWacPriceChart`.
> Causa radice #3 (Rendimento comparativo vuoto): `fifo_lot_engine.py` `_apply_buy()` passa sempre `reference_resolution=None`; solo `_apply_adjustment_in()` popola `reference_unit_price`. `return_history`/`relative_return` erano quindi sempre vuoti per lotti BUY.
> Causa radice #4 (Prezzo comparativo): `LotComparisonChart.svelte` non aveva alcuna prop `brokers` (label generiche "WAC broker #N") e mostrava il WAC cumulato anche con un solo broker.

## STEP A — Fondamenta (eseguite personalmente, file condivisi)

- [x] A1 Backend: campo `total_return` + generalizzazione Open Return — 2026-07-16 (delegato ad agente, verificato)
> **Note implementazione**: nuovo campo additivo `LotReturnHistoryPoint.total_return` in `schemas/portfolio.py`. Nuovo helper privato `_opening_reference_price()` in `lots_analysis_service.py` che generalizza il fallback: usa `reference_unit_price` (ADJUSTMENT_IN, comportamento invariato) se disponibile, altrimenti `opening_unit_price` (BUY, nuovo fallback — sempre disponibile). Nuovo helper condiviso `_value_snapshot_on_date()` factorizzato per evitare duplicazione di formula tra `_build_value_history` e `_build_return_history`. Bonus: l'agente ha corretto un bug latente pre-esistente — il gate di registrazione FX-need era condizionato solo su `LOT_SUMMARY in analyses`, causando `relative_return` sempre `None` quando si richiedeva `RETURN_HISTORY` da solo con valute diverse (esattamente il pattern usato dall'orchestratore) — ora il gate include anche `RETURN_HISTORY`.
> **⚠️ Bug trovato**: un test API scritto dall'agente (`test_return_history_for_plain_buy_populates_total_and_open_return`) usava `"date_to": "..."` come campo flat invece del corretto `"date_range": {"end": "..."}` (schema `LotsAnalysisQuery` con `extra="forbid"`) — causava 422. Corretto direttamente. Suite completa: 52/52 passanti dopo il fix.

- [x] A2 Frontend orchestratore — 2026-07-16 (fatto personalmente)
> **Note implementazione**: `LotsAnalysisPanel.svelte` — sostituito `CUSTODY_HISTORY` con `EVENT_HISTORY` nel fetch principale (superset, stesso costo backend — `lot_events` è già calcolato incondizionatamente); nuovo stato `lotEvents` passato sia a `LotWacPriceChart` (marker) sia a `LotCustodyModal` (history completa, non più filtrata su `_CUSTODY_KINDS`). Filtro Aperti/Tutti spostato da stato locale di `LotGanttChart` a stato condiviso `lotFilterMode` nell'orchestratore (`visibleLots` derivato, passato sia a Gantt che a Tabella) — il controllo UI resta visivamente sopra il Gantt. Nuova prop `brokers` passata a `LotComparisonChart`. `LotGanttChart.svelte` modificato in tandem: `filterMode`/`onFilterModeChange` diventano prop+callback (pattern identico a `selectedLotIds`/`onSelectionChange`), rimossa la `$state` interna.
> **⚠️ Bug trovato durante la verifica**: `visibleLots` derivato usava `lot.open_quantity > 0` (confronto numerico su un campo tipizzato `string` dal client Zodios generato, per `SafeDecimal`) e `lot.states.includes(...)` senza considerare che `states` è tipizzato optional dal generatore nonostante abbia sempre un default lato Pydantic — 2 errori TS reali intercettati da `svelte-check` durante l'avvio del server di test. Corretto con `Number.parseFloat(lot.open_quantity) > 0` e `(lot.states ?? [])`.

- [x] A3 Gantt: fix CSS + debug rendering + rifinitura — 2026-07-16 (fatto personalmente, verifica visiva iterativa)
> **Note implementazione**: fix CSS confermato (virgola→underscore). Verificato sperimentalmente via CSS injection in-browser (nessun file toccato) che il fix CSS da solo produce un layout a 2 colonne corretto ma un **canvas vuoto** — secondo bug indipendente.
> **⚠️ Bug #2 trovato (il più insidioso)**: `renderItem(params, api)` leggeva `params.data?.meta` per recuperare i metadati del segmento — sempre `undefined` per QUALSIASI custom series con item-object `{name, value, meta}` in questa versione di ECharts (6.0.0), nonostante `params.dataIndex` fosse correttamente popolato (0..16). Diagnosticato con log diagnostici temporanei (poi rimossi) che mostravano `meta=null` per ogni chiamata. **Fix**: sostituito ogni lookup `params.data?.meta` con `segmentSeriesData[params.dataIndex]?.meta` (lookup diretto nell'array `$derived` via closure, bypassando il problema di serializzazione interna di ECharts). Applicato in 3 punti: `renderItem` del segmentSeries, `renderItem` del laneHighlightSeries (`laneHighlightData[params.dataIndex]`), formatter del tooltip.
> **⚠️ Bug #3 trovato (click/dblclick)**: dopo il fix #2 il rendering e il tooltip funzionavano (verificato via screenshot reale — barre visibili, tooltip con contenuto corretto), ma click/dblclick per la selezione non scattavano affatto (0 eventi ricevuti da `chartInstance.on('click', ...)`, verificato con log diagnostici + click DOM sintetico diretto sul canvas). Causa: limitazione nota di ECharts — i click sui **children** di un `group` restituito da `renderItem` non risalgono a `chart.on('click')` (confermato leggendo `node_modules/echarts/lib/chart/custom/CustomSeries.js`: `getDataParams(dataIndex, dataType, el)` legge `customInnerStore(el).info`, non un generico `dataIndex` bubblato dal child). **Fix**: aggiunto `info: {lotId: meta.lotId}` sulla shape `rect` restituita da `renderItem`; `chart.on('click'/'dblclick', params => params.info?.lotId)` invece di `params.data`/`dataIndex`. Verificato: click su una barra → riga tabella selezionata (checkbox ✓) → grafico comparativo popolato con serie temporale reale.
> **⚠️ Bug i18n trovato**: tooltip del Gantt mostrava le chiavi i18n grezze `dashboard.direction` e `common.dateRange` (chiavi inesistenti) perché il codice usava il pattern naive `$t(key) || fallback` — ma le librerie i18n di questo progetto restituiscono la CHIAVE STESSA (non una stringa vuota) quando la traduzione manca, quindi `|| fallback` non scatta mai. Il pattern corretto già usato altrove nello stesso file è `translated === key ? fallback : translated`. Corretto: `dashboard.direction` → `brokers.lots.direction` (chiave esistente); aggiunta nuova chiave `brokers.lots.dateRange` in EN/IT/FR/ES (nessuna chiave equivalente pre-esistente).
> Tutto il resto della spec §4 (spessore proporzionale, colore per broker, pattern tratteggiato IN_TRANSIT, opacità per stato, frecce per rami aperti, clipping, niente lane vuote) era già correttamente implementato nel codice esistente — confermato via screenshot reale una volta risolti i bug #1/#2/#3.

## STEP B — Componenti (3 agenti paralleli, dopo A1+A2)

- [x] B1 Marker WAC (`LotWacPriceChart.svelte`) — 2026-07-16 (agente, verificato)
> **Note implementazione**: 5 serie scatter (Acquisti/cerchio, Vendite/diamante, Trasferimenti/freccia doppia path custom, Rettifiche/quadrato, Split/barra verticale path custom), tutte visibili di default e togglabili da legenda. Y = prezzo di mercato alla data (mai sulla linea WAC), con fallback all'ultimo prezzo precedente. Intervallo di transito ricostruito tramite pairing `TRANSFER_DEPART`/`TRANSFER_ARRIVE` su `related_transaction_id`/`fragment_id`; fallback a data singola per trasferimenti istantanei (senza DEPART, il caso comune nei dati reali). Marker coincidenti gestiti con offset verticale deterministico. i18n: nuovo namespace `brokers.lots.chartMarkers.*` in 4 lingue.
> Verificato: screenshot luce/buio su asset reali (AAPL 17 eventi, BTC 3 eventi) + conferma diretta nell'app live durante il debug del Gantt (marker visibili sul grafico WAC/Market Price).

- [x] B2 Grafico comparativo (`LotComparisonChart.svelte`) — 2026-07-16 (agente, verificato)
> **Note implementazione**: modalità Valore riscritta come serie temporale (area stacked: valore residuo + incassi cumulati, aggregata di default; linee "Total Value" per singolo lotto disponibili ma nascoste da legenda). Modalità Rendimento usa il nuovo campo `total_return` come serie primaria per lotto, Open Return (`relative_return`) come info secondaria in tooltip; empty-state ora condizionato sui dati realmente assenti, non più incondizionato. Modalità Prezzo: nuova prop `brokers`, nomi/colori broker reali (via `getBrokerColor`), WAC cumulato mostrato solo con ≥2 broker che detengono realmente quantità >0 (mirror della logica già corretta in `LotWacPriceChart.svelte`).
> Verificato via screenshot reali (Value/Return/Price) su selezione di 3 lotti AAPL: Return mode non vuoto per lotti BUY, Price mode con nomi broker reali in legenda ("WAC — Interactive Brokers", "WAC — DEGIRO", ecc.), Cumulative WAC correttamente mostrato (5 broker detentori nello scenario AAPL).
> **Pulizia**: rimosse 3 chiavi i18n rese orfane (`comparisonTitle`, `brokerWac`, `originalCostReference`) — verificate morte via grep esaustivo su `frontend/src/` prima della rimozione.

- [x] B3 Tabella + Modale (`UnifiedLotsTable.svelte`, `LotCustodyModal.svelte`) — 2026-07-16 (agente, verificato)
> **Note implementazione**: tabella — aggiunte colonne Prezzo apertura/Valore corrente, rinominata Quantità→Quantità aperta, tooltip Open Return sulla cella P&L FIFO. Modale — aggiunti Valore corrente/P&L FIFO/Open Return al riepilogo; custodia mostrata sia raggruppata per broker (somma quantità) sia a livello di frammento (lineage preservato); history estesa a tutti i tipi di evento (BUY/SELL/ADJUSTMENT_IN/OUT/SPLIT/TRANSFER), non più solo custody-kind.
> **Modifica a componente condiviso**: `DataTable.svelte` — aggiunto `event.stopPropagation()` sul click delle celle con `cellContent.onClick` (bottoni HTML dentro una cella), che prima faceva risalire il click anche al gestore selezione della riga. Verificato via grep esaustivo che questo pattern specifico (`CellContent.onClick`, firma zero-argomenti) è usato SOLO da `UnifiedLotsTable.svelte` nell'intero frontend — nessun altro consumer di `DataTable` è a rischio di regressione (gli altri usi di "onClick" trovati nel grep sono `RowAction.onClick(row)`, una firma diversa, non toccata dal fix).
> Verificato via screenshot reale: modale "Lot Bitcoin" mostra Custodia raggruppata (Coinbase 0.10 + Interactive Brokers 0.05) E frammenti dettagliati (3 righe), history con BUY + 2 TRANSFER.

## STEP C — Integrazione

- [x] Verifica incrociata — 2026-07-16
> **Note implementazione**: rieseguiti tutti i test E2E esistenti che toccano il pannello lotti (`brokers-detail.spec.ts`, 17/17 prima delle aggiunte) + gallery (`fifo lots panel`, 2/2, 16 screenshot generati EN/IT/FR/ES × light/dark). Verificata sincronizzazione Gantt→tabella (click barra → riga selezionata → grafico comparativo popolato) e Custodia→modale (click cella → modale apre, selezione riga invariata) con screenshot reali. i18n audit: 1652 chiavi, 100% complete, 42 non usate (tutte pre-esistenti/false positive già note, nessuna nuova).

## STEP D — Test

- [x] Test backend — 2026-07-16
> Suite `test_services/` (966/967, 1 fallimento pre-esistente per isolamento test non correlato — vedi report finale), `test_api/test_portfolio_api.py` (21/21), `test_schemas/`+`test_utilities/` (479/479).

- [x] Test E2E — 2026-07-16
> Aggiunti 2 nuovi test in `brokers-detail.spec.ts` (estensione del file esistente, non nuova suite): click lane Gantt → selezione riga tabella; click cella Custodia → modale apre senza alterare la selezione. 19/19 passanti (17 pre-esistenti + 2 nuovi). Per le interazioni rimanenti della lista §9 (cambio modalità grafico comparativo, dark mode, mobile, doppio click/pulse) è stata preferita la verifica visiva manuale (screenshot reali durante questa sessione) invece di una nuova suite E2E estesa, in linea con la preferenza dell'utente per la verifica manuale sulle checklist visive.

## STEP E — Validazione, pulizia, report

- [x] Validazione completa — 2026-07-16
> `ruff check backend/app/` (8 errori, tutti pre-esistenti e non toccati da questa sessione — confermato via diff vuoto sui file interessati); `black --check` (3 file da riformattare, tutti pre-esistenti, diff vuoto confermato); `./dev.py api sync` (campo `total_return` presente nel client rigenerato); `svelte-check` (0 errori/0 warning); `./dev.py i18n audit` (100%); `./dev.py mkdocs build` (pulito).

- [x] Pulizia — 2026-07-16
> Rimossi: filtro Aperti/Tutti interno a `LotGanttChart` (sostituito da stato condiviso); 3 chiavi i18n orfane della vecchia modalità Valore/Prezzo; file di scratch temporanei (`artifacts/`, `agent_artifacts/`, `frontend/marker-review/`, script di debug in `/tmp`).

- [x] Report finale — 2026-07-16
> [`fifo-ui-refinement-v1-final-report.md`](./fifo-ui-refinement-v1-final-report.md)

---

**Rifinitura FIFO UI v1 completata.** Tutti gli 8 criteri di completamento del piano (§14 di `refinment-work-v1.md`) verificati:
1. ✅ Gantt mostra barre temporali reali anche con sole BUY.
2. ✅ WAC e Gantt allineati e sincronizzati (zoom condiviso preservato).
3. ✅ Primo grafico mostra i marker degli eventi (5 categorie).
4. ✅ Valore, Rendimento e Prezzo hanno tutti asse X temporale.
5. ✅ Rendimento di normali BUY non è vuoto (nuovo campo `total_return`).
6. ✅ WAC cumulato assente con un solo broker detentore.
7. ✅ Tooltip, selezione, doppio click, pulse e modale funzionano (verificati con click reali).
8. ✅ Nessuna lane o grafico vuoto senza motivazione dati reale.
