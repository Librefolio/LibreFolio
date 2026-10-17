# Workstream R — Fattorizzazione colori a parità di aspetto · analisi di implementazione

> Sessione R (`b7658ba9…`), worktree `e-alfy-literate-tribble`, branch `e-alfy-r-fattorizzazione-colori`.
> Base verificata: HEAD = `b631308d5ef5482a8ffdc2878a4459fcf6909827` = base del kickoff (dopo ff del coordinatore). Worktree pulito.
> Coordinatore: `aec04834-1532-4d86-9e3f-f942e82aca89`. Corsia: porta **6154**, dati **`/tmp/librefolio-r2-r`**.
> Piano nel repo (da creare solo dopo l'autorizzazione): `LibreFolio_developer_journal/Release_2/Phase_0/55_colorSystem/R-colorRefactor/plan-phase00ColorRefactor.prompt.md`.
> Stato: **FROZEN** — nessun file del repo modificato. Grafo graphify assente (atteso): consultate le pagine wiki committate.
> Inventario di partenza (sola lettura, fuori repo): `files/inventory-b631308/`, `files/zones.out`, `files/sign_ternaries.txt`.

## 0. Problema e approccio

Spostare i colori in pochi moduli centrali **senza cambiare un pixel**. Le divergenze di oggi restano, ma con un nome.
Approccio: tabelle di valori identici + un solo punto di scelta del tema (`themed()`); si cambiano le **definizioni**, non
le chiamate, dove i test fissano il testo sorgente; ogni ondata ha una **prova di equivalenza a livello di codice** prima
della gallery dello stesso giorno.

## 1. Verifica sul codice (R-1…R-4) — righe a `b631308`

`frontend/src` è identico a `6d0b1266c` (commit dell'analisi): le righe dell'analisi valgono, salvo le correzioni sotto.

### R-1 grafici — confermato, con correzioni
- Perimetro reale (cartelle grafici + PAC result): **530 hex** (446 in script `.svelte`, 84 in `.ts`) + **51 funzioni colore** (coerente con le 571 del progetto Lab).
- Palette P1–P11 alle righe dell'analisi: `AllocationPieChart.svelte:110-111`, `SemiDonutChart.svelte:68`, `AllocationHistoryChart.svelte:173-174`, `GrowthChart.svelte:348-362` (COLORS) e `:367-379` (BROKER_PALETTE/brokerColor), `ChartSignal.ts:194`, `signalVisualStyle.ts:3-9`, `GeographyMap.svelte:297`, `ExposureMaps.svelte:60-61` (commento: «stessi colori di GeographyMap»), `CorrelationHeatmap.svelte:131-132`.
- Set neutri: `chartCoreHelpers.ts:47-53`, `echartsTooltipHelpers.ts:26-31` e `:161-164`, copie inline `CandlestickChart.svelte:191-202, 321-322, 541-547`, `LineChart.svelte:639-706`, `PriceChartFull.svelte:868-918`.
- **Correzioni:**
  - `lineChartHelpers.ts`: `hexToRgba` è a **:18** (non :21); `COLORS` :45-52; in più `:540-561` (primitive di riferimento `#cbd5e1/#64748b`).
  - `colors.ts` (report 04 sbaglia, report 03 giusto): `getPriorityBadgeStyle` :113, `hslToHex` :123, `hexToHsl` :153.
  - `priceChartHelpers.ts`: colore del Δ a **:594**; `registry.ts:37` è un commento (il default `#3b82f6` è `DEFAULT_SIGNAL_COLORS[0]`).
  - Non censiti: neutri scatter `scatterChartHelpers.ts:250-266`; fallback asse secondario `chartCoreHelpers.ts:234`; note tooltip `color:#94a3b8` fisse nei due temi (`LineChart.svelte:760-783`, `PriceChartFull.svelte:958-1032`); Performance `#166534/#16a34a` (:450, :526); neutri mappa `GeographyMap.svelte:316-325` = `ExposureMaps.svelte:158-159`.
  - **Osservatori del tema: 16, non 17.** `OtherPeriodEffectsTable.svelte:208` osserva `data-row-id`, non il tema. Dei 16, **12** ridisegnano a ogni cambio di classe di `<html>`; **4** (`ScatterChart:82`, `CorrelationHeatmap:300`, `ExposureBars:48`, `ExposureMaps:100`) aggiornano solo uno `$state dark` → ridisegnano solo quando cambia il tema. `SemiDonutChart` non ha osservatore. Letture `classList.contains('dark')`: 24 in 19 file.
- Formule da spostare **verbatim** (stessa aritmetica): `ExposureTreemap.svelte:488-497` `pnlColor`, `KpiSection.svelte:248-252` `timingColor`.

### R-2 segno/stati/badge — confermato, con correzioni
- Ternari di segno: **~37 siti in 20 file**, **8 famiglie di classi** (emerald-600 vs red-500; green-600 vs red-500 (+ gray zero); green-600 vs red-600; emerald-600 vs red-600; green-700 vs red-700 + gray-800; barre green-500 vs red-400 «invertite»; barre green-500 vs red-500; rosso/blu correlazione; Tornado emerald-500/80 vs red-500/80). Elenco: `files/sign_ternaries.txt` + `KpiDivergingFlowBar.svelte:88-89` (prop di default).
- **Correzioni:** i ternari «neutri» (`UnifiedLotsTable:205,214`, `ExposureTable:136`, `ContributionTable:169`) sono **a tre stati** (>0 verde, <0 rosso, 0 grigio), non «tutto il resto grigio». Soglie diverse da conservare: `OtherPeriodEffectsTable:91` manda lo zero al rosso; `KpiSection:352` manda `null` al rosso.
- Mappe: 11 tabelle in 9 file, righe confermate (`syncHelpers.ts:97`, PAC `ui.ts:80-94`, `TargetsStep.svelte:29-30`, `ToastContainer.svelte:16`, `ReportSetCard.svelte:308`, `AssetGroupStep.svelte:229`, `FileSetBadges.svelte:17`, `AssetChip.svelte:42`, `DataQualityBanner.svelte:80`). `STATUS_COLORS` è usato solo da `SyncResultRow.svelte` (le modali passano da lì).
- `BADGE_CLASS_MAP` (`assetTypes.ts:109`) e `PROVIDER_COLORS` (`providerHelpers.ts:22`) sono già centrali e fissati da test/mock (4 file mockano `providerHelpers`): **restano dove sono**.

### R-3 hex nei `<style>` (P8) — confermato, numeri esatti
- In perimetro (13 file con `<style>`): **747 hex + 75 funzioni + ~70 colori con nome (`white`/`black`) ≈ 880 dichiarazioni colore**; regole `:global(.dark)` gemelle ovunque (DataTable 56). Casi particolari: `!important` (DataTable 20, ImageCropper 51), keyframes con colori, variabili già esistenti (`--highlight-*`, `--broker-*` con fallback, `--stale-opacity`).
- Script nei file P8: `FilePreviewModal.svelte:636-675` = tema scuro cheetah-grid (27 hex, libreria canvas come ECharts → costanti TS); `LazyImage.svelte:42-57` = SVG placeholder in stringa (non può leggere variabili CSS → eccezione documentata); `AssetPickerModal.svelte:265` `color:#dc2626` inline.
- Piccoli `<style>` nelle cartelle grafici: `UnifiedLotsTable`, `OtherPeriodEffectsTable`, `RiskReturnLevel`.
- Fuori dall'elenco del kickoff (stesso schema): `routes/(app)/files/+page.svelte` (66 hex), `ImportBrokerMismatchModal` (49+7), `BrokerImportFilesModal` (26), `CompactCashCell` (13 fn) → decisione D5.

### R-4 funzioni fragili e refusi — confermato, con correzioni
- `hexToRgba` (`lineChartHelpers.ts:18`) accetta solo `#rrggbb`; oggi riceve **solo** `#rrggbb` (nessun chiamante passa `lineColor`; colori segnali da `<input type=color>`/palette hex) → versione robusta = output identico.
- Concatenazioni alfa: **4, non 1**: `AllocationHistoryChart.svelte:716` (`+ '88'`) e `GrowthChart.svelte:1693, 1705, 1717` (`+ '44'`).
- `withAlpha` (`lotChartShared.ts:71`) gestisce solo `hsl()` e `#rrggbb`; input raggiungibili: solo quelle due forme.
- Meta `theme-color` `#156534` in **3** punti: `themeStore.ts:59`, `app.html:26`, **`static/offline.html:521`** (mancava). Commento «matches sidebar» → refuso di `#166534` (`app.css:294`). Cambia solo la barra del browser: gallery neutra.
- Duplicato `hexToHue` (`registry.ts:38`) vs `hexToHsl`: unificarlo può cambiare, nei pareggi, il colore di default di un nuovo segnale → **escluso** (solo annotato).

### Wiki
- `concepts/echarts-chart-gotchas`: oro dividendi `#b08d00/#facc15` scelto per contrasto 3:1 → non toccare.
- `features/F-007` dice che i grafici seguono il tema via «store reattivi»: in realtà `MutationObserver` per grafico (drift da segnalare allo storico).

## 2. Architettura proposta — `frontend/src/lib/theme/`

| File | Contenuto | API |
|---|---|---|
| `themePair.ts` | primitiva comune | `ThemePair {light, dark}`; `themed(pair, dark)` = **unico punto di scelta del tema** (la fase B lo reindirizza ai ruoli); `both(v)` = colore uguale nei due temi, con nome |
| `colorAlpha.ts` (R-4) | alfa robusti | `toRgba(color, a)` (ex `hexToRgba`), `withAlpha(color, a)` (da `lotChartShared`), `withAlphaByte(color, '88')` (ex `+ '88'`): stesse stringhe di oggi per `#rrggbb`/`hsl()`; `#rgb`, `rgb()`, `hsl()`, `oklch()` gestiti; mai `NaN` |
| `chartTheme.ts` (R-1) | colori ECharts per significato | `CHART_NEUTRALS` (set con nome: `core`, `tooltip`, `tooltipCandlestick`, `grid`, `scatter`…), `GAIN_LOSS` (`gainLine`, `gainWac`, `gainDelta`, `lossLine` `#ef4444`, `lossBar` `#dc2626`, `lossWac`…), serie per famiglia (Growth, Performance, scatter, lotti/Gantt/WAC, rischio), formule treemap/timing; sezione librerie canvas (cheetah-grid) |
| `chartPalettes.ts` (R-1) | palette categoriali e scale | `ALLOCATION_PIE`, `SEMI_DONUT` (solo chiaro, così si vede), `ALLOCATION_HISTORY`, `GROWTH_BROKERS`, `SIGNAL_DEFAULTS`, `SIGNAL_ROLES`, `GEO_CHOROPLETH` (+ neutri mappa), `CORRELATION_SCALE` |
| `toneClasses.ts` (R-2) | classi Tailwind letterali | `SIGN_TEXT.{market,portfolio,kpi,brokerCard,riskMetric…}`, `SIGN_BAR.{…}`, `STATUS_TONES`, `BADGE_TONES` |
| `components/{table,media,files,dialogs}.css` (R-3) | token di componente su `:root` | `--lf-cmp-<area>-<ruolo>` e gemella `…-dark`; importati dallo `<script>` dei componenti |
| `themeMode.ts` (ondata 8, opzionale) | lettura tema | `isDarkTheme()`, `onThemeClassChange(cb)` con **un** `MutationObserver` condiviso, stessa semantica (qualunque cambio di classe) |

**Regole:**
1. Stessi valori e stesse stringhe (maiuscole, formato) di oggi.
2. Mai unire due valori diversi; un nome raggruppa solo valori identici con lo stesso significato. Stesso valore con
   significati diversi → nomi diversi (P5 resta visibile).
3. I nomi dicono significato e divergenza (`lossLine`/`lossBar`, `tooltip`/`tooltipCandlestick`).
4. Le API per grafico restano come adattatori sottili (`getChartColors`, `buildTooltipTheme`, `buildGridColors`,
   `lotStateColor`, `colorForRole`, `cc()` di Growth, `palette()` di Performance): i loro test diventano l'oracolo.
5. Classi Tailwind sempre letterali e complete (scansione automatica di Tailwind v4 via `@tailwindcss/postcss`; `.ts` in `src/lib` già scansionati).
6. Gate HTML: le chiavi interpolate negli HTML dei tooltip non finiscono con `note`, `tooltip`, `name`, `symbol`, `url`… (`TEXT_SUFFIXES` di `htmlInterpolation.gate.test.ts`).
7. Esportare solo ciò che si usa (knip).

**R-3, meccanica «variabili gemelle»:** ogni letterale in una regola chiara diventa `var(--lf-cmp-…)`, in una regola
`:global(.dark)` diventa `var(--lf-cmp-…-dark)`; definizioni su `:root` senza ridefinizioni per tema. Selettori,
specificità, ordine, `!important` invariati → valore calcolato identico per costruzione; nessun rischio con i portali.

**Compatibilità fase B (§2 piano generale):** B reindirizza `themed()` ai ruoli `--lf-*` (lettura per revisione, in
cache); le chiavi delle tabelle si mappano sui ruoli (più chiavi → un ruolo quando la designer decide); B fa puntare
`--lf-cmp-*` a `var(--lf-<ruolo>)` e solo allora fonde le gemelle e toglie le regole `:global(.dark)`. Nota per B: ECharts
non interpreta `oklch()` nei suoi calcoli (enfasi, sfumature): i token OKLCH vanno convertiti in sRGB prima dei grafici.

**Compatibilità Designer Lab (per valore):** valori invariati → L1/L2/L3 funzionano; la provenienza nel catalogo passa a
`lib/theme/**` (una riga per nome); `--lf-cmp-*` su `:root` diventano modificabili anche da L1. Da comunicare a L: lo
scanner deve trattare `lib/theme/chart*.ts` come zona grafici; il conteggio «impatto per file» scende per i letterali
spostati; i 4 grafici a `$state dark` **non** si ridisegnano col tick `lf-lab-tick`.

## 3. Ondate (rischio crescente)

Prova di codice per ogni ondata + gallery per lotto (D6). Statico sempre: `front check`, `front format --check`, `lint --dead-code --scope frontend`.

| Ondata | Contenuto | File | Test | Prova di equivalenza | Dim. |
|---|---|---|---|---|---|
| W0 | R-4: `colorAlpha.ts`; 4 concatenazioni; `withAlpha` spostato; (D3) meta | `lineChartHelpers.ts`, `chartCoreHelpers.ts`, `LineChart`, `CandlestickChart`, `lotChartShared.ts`, `LotComparisonChart`, `LotGanttChart`, `GrowthChart` (3 righe), `AllocationHistoryChart` (1), `allocationHierarchy.ts` (commento); D3: `themeStore.ts`, `app.html`, `static/offline.html` | golden su input raggiungibili; adattare `lineChartHelpers.test.ts`, `lotChartShared.test.ts` | stringhe identiche sugli input reali | S |
| W1 | R-2a: `SIGN_TEXT`/`SIGN_BAR` | ~20 file (fx, assets, dashboard, brokers, risk, MeasurePanel, ui/display) | `AssetTable`, `RiskMetricCard`, `KpiDivergingFlowBar`, `KpiSection`… + nuovo test tabelle | **CSS Tailwind compilato identico** (build prima/dopo) | M |
| W2 | R-2b: `STATUS_TONES`/`BADGE_TONES` | 9 file (sync, PAC, toast, import, files, risk, DataQualityBanner) | test dei componenti toccati | CSS compilato identico | M |
| — | **Cancello A** (gallery) | | | | |
| W3 | R-1a: `themePair.ts`, `chartTheme.ts` neutri + gain/loss | helper core, `priceChartHelpers`, `scatterChartHelpers`, LineChart, PriceChartFull, Candlestick, PriceChartCompact, copie tooltip in Pie/SemiDonut/History, GeographyMap | `lineChartHelpers`, `chartCoreHelpers`, `echartsTooltipHelpers`, `priceChartHelpers`, `scatterChartHelpers`, test di componente | dump `setOption` prima/dopo dai test di componente esistenti (harness fuori repo) + conservazione dei valori | M |
| W4 | R-1b: `chartPalettes.ts` | Pie, SemiDonut, History, Growth (broker), segnali (`ChartSignal`, `registry`, `signalVisualStyle`, `SignalVisualLegend`), GeographyMap, ExposureMaps, CorrelationHeatmap | **adattare** i lettori di palette (5 file) + `registry.test.ts` | idem | M |
| W5 | R-1c: serie e formule | Growth (`COLORS` + 6 definizioni di `cc`: le chiamate restano), Performance (`palette()`), Treemap, KpiSection, ExposureBars, lotti (4 helper + 3 grafici), RiskAnalysisPanel, L4Simulation, CorrelationHeatmap | test lotti, `chartCoreHelpers.test.ts` (asserzioni `cc('…')` restano verdi), Growth/Performance/Treemap/KPI | idem | L |
| — | **Cancello B** (gallery; lotti in schermate instabili → occhio o attesa di G) | | | | |
| W6 | R-3a tabelle | `DataTable`, `DataTableColumnFilter`, `DataTablePagination`, `DataTableToolbar` → `components/table.css` | test esistenti | **CSS compilato dei componenti identico dopo sostituzione delle `var()`** (script fuori repo) | L |
| W7 | R-3b media/file/dialoghi | `ImageEditModal`, `AssetPickerModal`, `FileUploader`, `FileEditModal`, `ImageCropper`, `FileGrid`, `FilePreviewModal` (+ tema cheetah-grid in TS), `FilesTable`, `ConfirmModal`, `ContextMenu`, piccoli `<style>` di UnifiedLotsTable/OtherPeriodEffectsTable/RiskReturnLevel | idem | idem | L |
| — | **Cancello C** (gallery) | | | | |
| W8 (D4) | osservatori: `themeMode.ts` | 16 grafici + `FilePreviewModal`, `scatterChartHelpers` | test helper + toggle tema | gallery (il cambio tema in gallery è un click + 100 ms) | M |
| W9 (D5) | P8 fuori elenco | 4 file | idem | idem | M |
| W10 | chiusura | (D7) gate a cricchetto; inventario prima/dopo; backlog R ✅; `wiki-file`; handoff | | | S |

Selettori: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6154 --data-dir /tmp/librefolio-r2-r front-utility core-unit | front-asset asset-unit | front-portfolio allocation-unit`; iterazione rapida `cd frontend && ./node_modules/.bin/vitest run <file>`. Gallery candidata: `scripts/visual_review/gallery_snapshot.sh r-<cancello>-cand --checkout <worktree> --port 6154 --data-dir /tmp/librefolio-r2-r`, diff con `--ignore-masks`/`--stability` del rumore dello stesso giorno; riferimento del coordinatore **sullo stesso SHA di base**. `npm ci` (pre-approvato) al primo comando frontend.

## 4. Test da adattare (da `test-author`)

- Lettori di palette dai sorgenti: `src/__tests__/sourcePalettes.ts`/`.test.ts`, `lib/utils/__tests__/colors.test.ts`, `lib/components/charts/__tests__/allocationHierarchy.test.ts`, `…/allocationRings.test.ts`, `lib/components/dashboard/AllocationHistoryChart.test.ts:568` → proposta: import diretto da `chartPalettes.ts` e ritiro del lettore (restano `paletteDefects`, `PALETTE_SLOTS`).
- Import spostati: `lineChartHelpers.test.ts:10` (`COLORS`, `hexToRgba`), `lotChartShared.test.ts:24` (`withAlpha`), `registry.test.ts:5` (`DEFAULT_SIGNAL_COLORS`).
- Restano verdi senza modifiche (oracolo): `chartCoreHelpers.test.ts` (testo `cc('…')` di Growth), `echartsTooltipHelpers.test.ts`, `priceChartHelpers.test.ts`, `scatterChartHelpers.test.ts`, test lotti, `AssetTable`/`RiskMetricCard`/`KpiDivergingFlowBar`/`TransactionFormModal` (classi), `assetTypeTables.test.ts:255`, mock di `providerHelpers` (4 file).
- Gate: `htmlInterpolation` (naming), `moneyRenderSites`, `flagFont` — da tenere verdi.
- Nuovi: `themePair`, `colorAlpha` (golden), tabelle `toneClasses`, concordanza meta (D3), gate a cricchetto (D7). Registrazione nel catalogo del runner (superficie condivisa, `test-author`).

## 5. Conflitti previsti

- **L:** nessun file in comune (L: `vite.config.ts`, `+layout.svelte`, `app.d.ts`, `lib/dev/designer-lab/**`). Contratto semantico: (1) R conserva il ridisegno «a qualunque cambio di classe di `<html>`» (anche in W8); (2) informazione per L: 4 grafici non ridisegnano col tick e `OtherPeriodEffectsTable` non è un grafico; (3) lo scanner di L deve conoscere `lib/theme/**` e i `--lf-cmp-*`.
- **G:** nessun file in comune (G: `gallery.spec.ts`, fixture gallery, `AnimatedBackground`). Possibile sovrapposizione se G corregge lo scorrimento del pannello lotti in `brokers/lots/**` (W5) → ordine da concordare. Le schermate `*/fifo-lots-*` e `auth/*` sono instabili: per W5 serve l'occhio o la correzione di G.
- **Catalogo del runner** (`scripts/test_runner/_frontend_*.py`): aggiunte di `test-author` anche da L/G → conflitti testuali additivi.
- Base del riferimento gallery: se `dev_release2` avanza (L/G) tra riferimento e candidata, il riferimento va catturato sullo **stesso SHA di base** del mio worktree.

## 6. Rischi (cosa può cambiare un pixel)

1. Refuso trascrivendo un valore → conservazione dei valori + test + gallery.
2. Fondere valori «quasi uguali» (`#e2e8f0` vs `#e5e7eb`) → vietato dalla regola 2.
3. Classi Tailwind spostate non più letterali → CSS compilato identico come prova.
4. Cascata CSS in R-3 (specificità, ordine, portali, keyframes, `!important`) → gemelle su `:root` + prova sul CSS compilato.
5. Caricamento del CSS centrale importato dai componenti (stesso chunk; verificare in dev e build).
6. HTML dei tooltip: spazi/virgolette nelle stringhe, naming per il gate → test dei builder.
7. Tempi del ridisegno (W8) col toggle della gallery → ultima ondata, opzionale.
8. Formule in virgola mobile → spostate verbatim.
9. Helper alfa robusti → cambiano solo input oggi irraggiungibili (golden sugli altri).
10. Divergenze da **non** «aggiustare»: SemiDonut solo chiaro, tooltip Δ uguali nei due temi, scale treemap invertite.
11. Punti ciechi della gallery: hover, enfasi, tooltip, schermi wide-gamut → prove a livello di codice.
12. Schermate instabili proprio sulle superfici R (lotti) → occhio o attesa di G.

## 7. Decisioni per il developer

- **D1** — variabili R-3: (a) centrali su `:root` in `lib/theme/components/*.css` **[racc.]**; (b) locali nel `<style>` di ogni componente.
- **D2** — tema scuro in R-3: (a) gemelle `--x`/`--x-dark`, regole `:global(.dark)` invariate **[racc.]**; (b) una variabile ridefinita sotto `.dark` (lavoro da fase B).
- **D3** — meta `#156534`→`#166534` in `app.html`, `static/offline.html`, `themeStore.ts` (superfici T) + test di concordanza: (a) in R **[racc.]**; (b) a T.
- **D4** — osservatori (W8): (a) helper unico, stessa semantica, ultima ondata **[racc.]**; (b) tutto a B. Sotto-domanda: dare ai 4 grafici a `$state dark` una revisione per il tick di L, in R o in L?
- **D5** — P8 fuori elenco (pagina file, `ImportBrokerMismatchModal`, `BrokerImportFilesModal`, `CompactCashCell`): (a) W9 in R **[racc.]**; (b) a P/fase B.
- **D6** — cadenza gallery: (a) una per lotto (A, B, C, eventuale D) con prova di codice per ondata **[racc.]**; (b) una per ondata.
- **D7** — gate a cricchetto (nessun nuovo colore nei file migrati fuori da `lib/theme/**`): (a) in R, a fine lavoro **[racc.]**; (b) in fase B.
- Proposte non bloccanti: prefisso `--lf-cmp-*`; nome `chartTheme.ts` (B lo evolve); ritiro del lettore `sourcePalettes`; `hexToHue` lasciato; nessuna voce di changelog; pagina MkDocs con B, `wiki-file` ora.
- Dal coordinatore: cartella di lavoro delle snapshot, rumore dello stesso giorno, date delle catture.

## 8. Definition of done

- R-1…R-4 consegnati secondo le decisioni; ogni lotto con gallery dello stesso giorno `identical` (eccetto instabili) e prove di codice registrate nel piano.
- Inventario prima/dopo: nei file migrati nessun colore fuori da `lib/theme/**`, salvo eccezioni motivate (generatori HSL, SVG di `LazyImage`, alfa parziali).
- Test e gate verdi; backlog R aggiornato nella mia sezione; piano aggiornato a ogni passo; `wiki-file`; server fermo, porta 6154 libera.
