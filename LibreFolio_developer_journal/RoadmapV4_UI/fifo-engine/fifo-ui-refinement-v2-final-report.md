# Report finale — FIFO UI v2: Consolidamento visuale

Piano sorgente: `refinment-work-v2.md` (732 righe). Log passo-passo: `fifo-ui-refinement-v2-implementation-log.md`.

## Diagnosi iniziale

Riprodotto lo stato reale su server di test (porta 6041) con 2 casi: Coinbase/Bitcoin (1 lotto, caso
semplice) e AAPL via Dashboard "All brokers" (10 lotti, 17 segmenti Gantt, 4 broker — Interactive Brokers,
DEGIRO, eToro, Coinbase, Directa SIM). Screenshot reali + lettura codice hanno confermato tutti i gap del
piano (colonna fissa Gantt, disallineamento assi, marker cerchio/diamante, assenza ROI/TWRR, checkbox
custom nel comparativo, colonne/context-menu mancanti in tabella). Dettaglio completo nel log.

## Decisioni prese

- **ROI/TWRR asset-level**: nuovo ricostruttore NAV/cash-flow in `LotsAnalysisService`, riusa al 100%
  `roi_utils.calculate_twrr_series`/`calculate_simple_roi_series` (già usate a livello portfolio). TRANSFER
  che attraversa il confine del filtro broker = cash-flow esterno; altrimenti interno. ADJUSTMENT a costo
  zero = nessun cash-flow (coerente con "dividendo in azioni").
- **Testabilità Gantt senza colonna fissa**: overlay `<button>` trasparente per-lane, riposizionato ad ogni
  evento `'rendered'` di ECharts via `convertToPixel` — nuovo pattern per la codebase, verificato sia in
  diagnosi manuale che in E2E reale.
- **Grid allineato**: sia Gantt che WAC chart passati a `containLabel:false` con `left`/`right` numerici
  identici (56/18) — elimina la deriva pixel introdotta da `containLabel:true` dinamico.
- **Legenda comparativo**: rimosse le 3 checkbox HTML custom, sostituite con legenda nativa ECharts (stesso
  hide/show visuale richiesto dal piano, senza duplicare `selectedLotIds`).
- **Colonne tabella raggruppate per ordine, non per header di gruppo**: `ColumnVisibilityToggle` è generico
  e condiviso da altre tabelle — non estesso per evitare un sistema parallelo o regressioni altrove.
- **Titolo modale**: non rinominato letteralmente — verificato che mostra già "Lot {Asset} — {data}", non
  "Custody"; il gap reale era di accesso (context menu) e contenuto (2 campi), non di copy.

## Backend — file modificati

- `backend/app/schemas/portfolio.py`: `LotAnalysisType.PERFORMANCE_HISTORY`, `PerformanceHistoryPoint`,
  campo additivo `LotsAnalysisResponse.performance_history`.
- `backend/app/services/lots_analysis_service.py`: nuovo `_build_performance_history` + helper
  (`_open_value_on_date`, `_fragment_in_scope`, `_converted_external_amount`,
  `_adjustment_cash_flow_cost`), riuso di `_build_value_history`/`_value_snapshot_on_date` per NAV(t) e di
  `roi_utils` per la matematica. Nessuna formula finanziaria nuova.
- Test: `test_lots_analysis_service.py` (+10 test: solo BUY, SELL parziale, transfer dentro/fuori scope,
  prezzo mancante), `test_portfolio_api.py` (+1 contratto HTTP).

## Frontend — file modificati

- `LotGanttChart.svelte`: rimossa colonna fissa HTML (240px) e `AssetIcon`/`BrokerBadge`/`requiredBrokerLike`
  ormai inutilizzati nel lane-header; identità del lotto (data con anno, broker, quantità) migrata nella
  label del custom series ECharts con troncamento a priorità (data > broker > quantità > testo "Lotto");
  freccia di clipping sinistra aggiunta (oltre a quella destra già esistente per `isOpen`); overlay
  trasparente per-lane per selezione/doppio-click testabili; grid allineato con WAC chart.
- `LotWacPriceChart.svelte`: marker BUY cerchio→triangolo, SELL diamante→triangolo ruotato 180°; grid
  allineato; 2 nuove serie ROI/TWRR (solo modalità %, gated su dati disponibili), nuova prop
  `performanceHistory`.
- `LotComparisonChart.svelte`: rimossi 3 blocchi checkbox custom + stato associato (`lotVisibility`,
  `valueSeriesVisibility`, `priceOverlayVisibility`) e i relativi `$effect` di sincronizzazione; legenda
  nativa ECharts attivata; nuova serie esplicita "Valore complessivo"; selettore
  Aggregato/Per lotto/Entrambi (`lots-value-presentation-filter` + 3 toggle); fix bug hover con
  `emphasis:{scale:false,focus:'none'}` + `z`/`zlevel` espliciti su tutte le serie, in tutte le modalità;
  titolo Prezzo rinominato "Prezzo dei lotti selezionati".
- `UnifiedLotsTable.svelte`: fix fallback "Valore corrente" (ora `open_value` puro); 4 nuove colonne
  (Quantità iniziale, Valore apertura, Incassi cumulati, Open Return) con visibilità default corretta;
  context menu abilitato (`enableContextMenu`) con 4 azioni riusando il meccanismo generico di `DataTable`
  (`rowActions`), nessun nuovo componente.
- `LotCustodyModal.svelte`: 2 nuovi campi riepilogo (Valore apertura, Incassi cumulati).
- `LotsAnalysisPanel.svelte`: `PERFORMANCE_HISTORY` aggiunto al fetch principale; callback context-menu
  collegate a logica già esistente (`ganttRef.pulseLot`, `handleGotoTransaction`).
- `frontend/e2e/brokers/brokers-detail.spec.ts`: riscritto il test Gantt per il nuovo overlay (era rotto
  dalla rimozione della colonna fissa); +3 nuovi test (context menu "View lot detail" su lotto senza
  transfer, context menu "Go to lot in Gantt", toggle Aggregato/Per lotto/Entrambi).
- i18n: nuove chiavi in tutte le 4 lingue (en/it/fr/es) per label Gantt, ROI/TWRR (riusate `dashboard.roi`/
  `dashboard.twrr` esistenti), toggle Valore, azioni context menu, campi modale, titolo Prezzo.

## Materiale esistente riutilizzato

- `DataTable.svelte`: `enableContextMenu`+`rowActions` (già generico, mai usato da questa tabella prima).
- `ColumnVisibilityToggle.svelte`: nessuna modifica, solo nuove `ColumnDef` con `hiddenByDefault`.
- `roi_utils.calculate_twrr_series`/`calculate_simple_roi_series`: stesse funzioni usate da
  `portfolio_service.py` a livello portfolio, ora anche a livello asset.
- Pattern segmented-toggle inline Tailwind (già usato da Aperti/Tutti e ABS/%): replicato per
  Aggregato/Per lotto/Entrambi, nessun nuovo componente.
- Legenda nativa ECharts (`type:'scroll'`, stile già in `LotWacPriceChart.svelte`): replicata in
  `LotComparisonChart.svelte`.

## Modifiche API/DTO

Additive, nessun campo esistente toccato: `LotAnalysisType.PERFORMANCE_HISTORY`, `PerformanceHistoryPoint`,
`LotsAnalysisResponse.performance_history`. `./dev.py api sync` eseguito (implicitamente ad ogni rebuild
del server di test) — client TypeScript rigenerato correttamente, verificato con `grep` su `generated.ts`.

## Comportamento finale (verificato con screenshot reali)

1. **Gantt**: nessuna colonna fissa; ogni lotto interamente nella timeline; asse X e dataZoom
   pixel-allineati col grafico WAC (verificato: marker BUY del 27/05 e inizio barra Gantt dello stesso
   lotto coincidono orizzontalmente); label con data+anno, broker, quantità; troncamento a priorità su
   segmenti corti; nessuna icona asset ripetuta; overlay invisibile per selezione/doppio-click.
2. **WAC/Prezzo**: BUY=▲, SELL=▼ (legenda nativa aggiornata automaticamente); modalità % mostra Rendimento
   mercato + Variazione WAC (già esistenti) + ROI + TWRR (nuovi), verificato con dati reali (AAPL: ROI
   ~52%, TWRR ~58% a fine periodo).
3. **Tabella**: 12 colonne totali (8 visibili di default + 4 dietro selettore), context menu con 4 azioni
   verificato via screenshot e test E2E.
4. **Modale**: accessibile sia da cella Custodia sia da context menu, verificato su lotto Partial/LONG con
   custodia mono-broker (nessuna dipendenza da transfer); 2 nuovi campi visibili.
5. **Comparativo**: 3 modalità Valore (Aggregato/Per lotto/Entrambi) verificate via screenshot; hover
   testato con mouse-move reale — nessuna serie scompare, tooltip mostra tutti i valori; Prezzo rinominato.

## Test e comandi eseguiti

```bash
pipenv run pytest backend/test_scripts/test_services/test_financial/ -q          # 219 passed
pipenv run pytest backend/test_scripts/test_api/test_portfolio_api.py -q         # 22 passed
pipenv run ruff check backend/app/services/lots_analysis_service.py backend/app/schemas/portfolio.py   # clean
pipenv run black --check ...                                                      # clean
cd frontend && npx svelte-check --tsconfig ./tsconfig.json                        # 0 errors, 0 warnings
./dev.py i18n audit                                                               # 1665/1665, 0 missing
./dev.py mkdocs build                                                             # success
./dev.py test front-broker detail                                                # 22 passed (19 esistenti + 3 nuovi)
```

## Limitazioni residue

- I 42 "unused" segnalati da `i18n audit` sono **tutti pre-esistenti e non correlati** a questo lavoro
  (broker deposit/withdraw, dashboard P&L breakdown, alcuni codici Data Quality, più un probabile
  falso-positivo dell'audit tool sul pattern `label(key, fallback)` usato per gli stati lotto). Non
  toccati, come da preferenza di segnalare invece di correggere fuori scope.
- Non testati in modo automatico (per preferenza dell'utente di evitare test automatici estesi sulle
  verifiche puramente visive): dark mode pixel-perfect, layout mobile del Gantt/overlay, comportamento del
  doppio click/pulse esatto dentro al canvas ECharts durante lo zoom. Verificati invece via screenshot
  manuali durante l'implementazione; percorso di verifica manuale suggerito: Dashboard → Positions →
  riga asset → "Analizza Lotti" su `localhost:6040`, provare Gantt (pan/zoom/click/doppio-click), WAC %
  (ROI/TWRR), tabella (context menu, colonne), comparativo (3 modalità Valore, hover).
- Trovato un problema **Data Quality pre-esistente e non correlato** sul lotto Coinbase/BTC di test
  ("A transfer is missing its paired transaction, or the pair is invalid" ×2) — segnalato qui, non
  corretto, fuori scope di questo piano.
- Overlay di testabilità del Gantt: pattern nuovo per la codebase, funziona e verificato in E2E reale, ma
  non ha ancora altri precedenti nel progetto — utile documentarlo se altri chart ECharts avranno lo stesso
  bisogno in futuro.

## Stato: ✅ COMPLETATO

Tutti i 10 criteri di completamento del piano verificati:
1. ✅ Gantt e WAC hanno assi X allineati (verificato pixel-per-pixel via screenshot).
2. ✅ Nessuna colonna fissa nel Gantt.
3. ✅ Label scorrono con i segmenti (ancorate a `rectShape.x`, ricalcolate ad ogni render).
4. ✅ Marker BUY = triangolo.
5. ✅ Modalità % mostra mercato, WAC, ROI, TWRR.
6. ✅ Tabella espone tutte le colonne tramite selettore esistente.
7. ✅ Dettaglio lotto raggiungibile da context menu (+ cella Custodia).
8. ✅ Grafico Valore supporta Aggregato/Per lotto/Entrambi.
9. ✅ Tabella unica fonte di selezione (checkbox custom rimosse).
10. ✅ Nessuna serie scompare durante hover (verificato con mouse-move reale + screenshot prima/dopo).
