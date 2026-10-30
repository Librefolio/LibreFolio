# Brief — workstream Y · Cruscotto e grafici · Y-39b (anteprima come il dettaglio, colore della base sulle schede)

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-redesigned-spork`
**Branch**: `e-alfy-y-cruscotto-e-grafici`
**HEAD di partenza (da verificare)**: `89e8b2e61` (= `dev_release2`, con dentro il treno 6; il coordinatore ha portato il tuo ramo avanti in fast-forward: Y-39a è già in dev).
**Corsia**: porta `6189`, cartella dati `/tmp/librefolio-r13-y`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/09_dashboardCharts/plan-phase01DashboardCharts.prompt.md`. Leggi solo: «Il contratto di Y-39b» (riga ~7979), «Le risposte del coordinatore (20/10 13:34)» con «Le condizioni di DV per F-2 su `LineChart.svelte`» (riga ~8024-8045). Riga di stato Y-39b ~495.

## Dove eri rimasto
Y-39a (un solo modulo `frontend/src/lib/charts/chartSignalRendering.ts` per schede e anteprima) è in `dev_release2` dal treno 6. Le risposte del 20/10 valgono ancora: due checkpoint (T-Y39-1 sì), la terza vista dell'anteprima va in Y-40 (T-Y39-2 sì), l'aspetto dell'anteprima P-Y39 approvato.

## Cosa fare ora (un solo lotto: Y-39b)
1. **F-1**: sull'anteprima del grafico del dettaglio, `PriceChartFull` al posto di `LineChart` (dati assoluti, `externalViewMode`, segnali, aspetto e scale delle impostazioni in modifica; barra nascosta, solo linea, niente eventi/misure/modifica, ~220 px, zoom con la rotella).
2. **F-2 (a)**: `LineChart` applica `colorByBaseline` anche in compatto (oggi `colorByBaseline && !compact`, `:450`), con la prop facoltativa **`baselineValue`** (inoltrata da `PriceChartCompact`): è la stessa cosa dell'osservazione **O2** della revisione di Z-29s-a (`backendRenderer.ts:356` usa `baseData[0]`, che con le schede ridotte è il primo secchio e non `sample_bounds.first`). Valuta se `backendRenderer.ts` va allineato nello stesso lotto o lasciato a Z-29b: scrivilo nel checkpoint, non decidere in silenzio.
3. Le **condizioni di DV** su `LineChart.svelte` sono vincolanti: non toccare `echarts.init(…, chartInitOptions(chartContainer))`; colori identici a oggi (`COLORS.greenLight/greenDark/redLight/redDark`), nessun letterale, nessun nuovo `isDark ? … : …`, `chartTheme.ts` non si tocca; unico chiamante compatto `PriceChartCompact`.
4. Verdi leggeri (carico sotto 8): `LineChart.test.ts`, `chartCoreHelpers.test.ts`, poi dentro `flock`: `LC_ALL=en_US.UTF-8 … front-portfolio chart-safety-unit`, `front check` (dopo `api sync`). Prova a mano nei due temi cambiando tema senza ricaricare (screenshot nella tua cartella di lavoro, non nella galleria).
5. Doc (`charts.md` e pagine utente delle impostazioni dei grafici, solo inglese, `docs-writer`), due righe 🔄 proposte per il CHANGELOG.
6. **E2E solo con lo slot del coordinatore**: `fx-settings`, `fx-list`, `asset-list` (in `flock`, `LC_ALL=en_US.UTF-8`). Chiedi lo slot nel checkpoint se non l'hai.

## Non fare
- **Non toccare** `frontend/src/routes/(app)/assets/+page.svelte`, `AssetCard.svelte`, `bulkBatches.ts`, `timeSeriesAggregation.ts`: sono di **Z-29b**, che lavora in parallelo. Su `LineChart.svelte` Z-29b tocca solo la soglia della densità (`:193`, `:296-301`): tu solo `:450` e la prop nuova. Se ti serve altro in quel file, chiedi.
- Nessun colore nuovo, nessuna classe di palette (ratchet `theme-roles --check`). `ChartAestheticsSection.svelte` è della sessione colori C1: non toccarlo.
- Niente galleria (si fa una volta, in fondo, con la macchina ferma).

## Fatto quando
Rossi diventati verdi per la causa giusta, `chart-safety-unit` e i due Vitest verdi, `front check` 0/0, prova nei due temi descritta, doc e piano aggiornati, righe di CHANGELOG proposte, poi **CHECKPOINT READY** e **FROZEN**. L'E2E lo lanci quando il coordinatore ti dà lo slot.
