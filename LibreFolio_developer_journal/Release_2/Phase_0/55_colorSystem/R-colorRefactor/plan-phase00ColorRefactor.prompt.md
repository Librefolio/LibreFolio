# Piano R — Fattorizzazione dei colori a parità di aspetto

> Workstream **R** del programma colori 55. Sessione `R - fattorizzazione colori`, worktree `e-alfy-literate-tribble`,
> branch `e-alfy-r-fattorizzazione-colori`. Coordinatore: sessione `aec04834-1532-4d86-9e3f-f942e82aca89`.
> Base: `dev_release2` @ `b631308d5ef5482a8ffdc2878a4459fcf6909827`. Corsia: porta **6154**, dati **`/tmp/librefolio-r2-r`**.
> Piano generale: [`../plan-phase00ColorSystemThemeLab.prompt.md`](../plan-phase00ColorSystemThemeLab.prompt.md), riga R del §5.
> Fonti: [`../analysis/`](../analysis/00_SINTESI.md) (report 01–04). Backlog: sezione «R» di
> [`../../BACKLOG_POST_1.2.md`](../../BACKLOG_POST_1.2.md).

## ⏸️ Pausa del 14/10 (richiesta del developer, inoltrata dal coordinatore) — ▶️ ripresa alle 19:15

> Chiusa: il coordinatore ha scritto «RIPRENDI» alle 19:15, con base (`b1fcc3c48`), worktree (3 righe) e porta 6154
> verificati. Il lavoro è ripreso da W3 come annotato qui sotto.

- **Ultimo passo completo:** lotto A (W0–W2), committato dal coordinatore (`d80b9e0cd`; base aggiornata con il merge
  `b1fcc3c48`). Il cancello A aspetta il merge di G.
- **Passo in corso: W3.** Toccati solo due file nuovi, completi e non ancora importati da nessuno:
  `frontend/src/lib/theme/themePair.ts` e `frontend/src/lib/theme/chartTheme.ts`. Nessun file di grafico modificato.
  Il resto di W3, già deciso, è descritto al passo «W3».
- **Primo comando alla ripresa:**
  `git -C /Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-literate-tribble rev-parse HEAD` più `status --porcelain`.
  Atteso: HEAD `b1fcc3c48e2b578cbc2436685dd9e86a42a0ca99` e 3 righe (questo piano, i due file nuovi). Se HEAD è
  cambiato, verificare che nessun file del perimetro W3 sia cambiato, poi riprendere i chiamanti di W3.
- **Attese aperte:** merge di G, poi riallineamento della base e cancello A (riferimento del coordinatore, candidato di
  R, stesso giorno, avviso prima di ogni gallery completa). Nessuna decisione pendente del developer.
- **Corsia:** nessun server avviato da R; porta 6154 libera; nessun dato in `/tmp/librefolio-r2-r`. Gli artefatti delle
  prove (`conserve.py`, `w1_apply.py`, `add_import.py`, CSS e log della baseline) stanno nella cartella della sessione R,
  non in `/tmp`. Nessun sotto-agente in esecuzione (il test-author di W0 ha finito).

## ✅ Decisioni del developer (14/10/2026)

Richiesta, testuale: «già che ci siamo iniziamo anche a fattorizzare e correggere gli errori che avevi già identificato
a livello di progetto per i colori, e poi quando la designer arriva aggiorniamo i colori».

Approvazione, testuale (inoltrata dal coordinatore): «Approvo R con tutte le opzioni (a) e la regola «conta lo stile»».

| # | Decisione |
|---|---|
| D1 | Le variabili dei `<style>` (R-3) stanno in file centrali `lib/theme/components/*.css`, su `:root`, importati dai componenti |
| D2 | Variabili gemelle `--x` / `--x-dark`; le regole `:global(.dark)` restano come sono |
| D3 | Il refuso della meta `theme-color` (`#156534` → `#166534`) si corregge in R, con un test di concordanza |
| D4 | Un solo helper per gli osservatori del tema, nell'ultima ondata. Il ridisegno a **qualunque** cambio di classe di `<html>` resta. Nessuna revisione per i 4 grafici con il solo stato `dark`: il Lab riapplica dal vivo |
| D5 | I quattro file P8 fuori dall'elenco iniziale entrano in R (ondata W9) |
| D6 | Una gallery per lotto (A, B, C, eventuale D) più una prova di codice a ogni ondata |
| D7 | Gate «a cricchetto» alla fine, con esenzione dei percorsi di L (`src/lib/dev/designer-lab/**`, `src/routes/designer-lab/**`, `frontend/scripts/designer-lab/**`) |

**Regola «conta lo stile»** (developer: «basta che lo stile lo sia… non la correttezza del contenuto»):
- le prove di codice restano strette;
- nella gallery le differenze di solo contenuto si accettano; quelle di stile o di colore sono regressioni.

**Sequenza decisa:** W0–W2 subito, con le prove di codice. Le gallery A/B/C dopo il merge di G, lo stesso giorno: il
riferimento lo cattura il coordinatore sul target allo SHA della base di R, il candidato lo cattura R. Avvisare il
coordinatore prima di ogni gallery completa. Snapshot in `/Users/ea_enel/Documents/00_My/LibreFolio_subRepo/LibreFolio_visual_review/`
(`LF_VISUAL_REVIEW_DIR` oppure `--work-dir`).

**Vincolo 1.3:** la sessione «Release 1.3 planning» lavora sullo stesso checkout di `dev_release2`. Se un file del
perimetro di R cambia nel target, fermarsi e avvisare il coordinatore.

**Fuori da R** (aspetta il report della designer): rimozione degli override scuri di `app.css` (P1), unificazione
green/emerald, errori in ambra, info sky/blue, contrasto, palette dei grafici, token per ruolo.

## 1. Stato verificato sul codice (14/10, `b631308`)

`frontend/src` è identico al commit dell'analisi (`6d0b1266c`). Correzioni all'analisi:

- **R-1 grafici.** Perimetro: 530 hex (446 negli script `.svelte`, 84 nei `.ts`) e 51 funzioni colore.
  - `hexToRgba` è a `lineChartHelpers.ts:18`, non :21. In `colors.ts`: `getPriorityBadgeStyle` :113, `hslToHex` :123,
    `hexToHsl` :153 (il report 04 aveva righe sbagliate). Il colore del Δ nel tooltip è a `priceChartHelpers.ts:594`.
  - Non censiti: neutri dello scatter (`scatterChartHelpers.ts:250-266`), fallback dell'asse secondario
    (`chartCoreHelpers.ts:234`), note dei tooltip `#94a3b8` uguali nei due temi (`LineChart.svelte:760-783`,
    `PriceChartFull.svelte:958-1032`), `#166534/#16a34a` di Performance (:450, :526), neutri della mappa
    (`GeographyMap.svelte:316-325` = `ExposureMaps.svelte:158-159`).
  - **Osservatori del tema: 16, non 17.** `OtherPeriodEffectsTable.svelte:208` osserva `data-row-id`. Dei 16, 12
    ridisegnano a ogni cambio di classe; 4 (`ScatterChart:82`, `CorrelationHeatmap:300`, `ExposureBars:48`,
    `ExposureMaps:100`) aggiornano solo uno stato `dark`. `SemiDonutChart` non ha osservatore.
- **R-2 segno, stati, badge.** 42 siti di segno in 20 file, 8 famiglie di classi. I ternari «neutri» sono a tre stati
  (>0, <0, 0). Soglie da conservare: `KpiSection:352` manda il `null` al rosso; `OtherPeriodEffectsTable:90` manda zero
  e `null` al grigio prima del ternario; `FxTable`/`AssetTable` hanno un neutro proprio per «nessun delta»
  (`gray-400/gray-500`). 11 mappe di stato in 9 file; `STATUS_COLORS` è usato solo da `SyncResultRow`. `BADGE_CLASS_MAP` e
  `PROVIDER_COLORS` sono già centrali e fissati da test e mock: restano dove sono.
- **R-3 `<style>`.** 13 file nel perimetro iniziale, circa 880 dichiarazioni colore (747 hex, 75 funzioni, circa 70
  `white`/`black`). `FilePreviewModal` ha anche un tema cheetah-grid nello script (27 hex); `LazyImage` ha SVG in
  stringa (eccezione).
- **R-4.** Le concatenazioni dell'alfa sono 4, non 1: `AllocationHistoryChart.svelte:716` (`+ '88'`),
  `GrowthChart.svelte:1693, 1705, 1717` (`+ '44'`). `hexToRgba` oggi riceve solo `#rrggbb`. `#156534` è in tre punti:
  `themeStore.ts:59`, `app.html:26` e `static/offline.html:521`.
- **Escluso:** l'unificazione di `hexToHue` (`registry.ts:38`) con `hexToHsl`: nei pareggi cambierebbe il colore di
  default di un nuovo segnale.
- **Wiki:** `features/F-007` dice che i grafici seguono il tema con «store reattivi»; sono `MutationObserver` per grafico.

## 2. Architettura — `frontend/src/lib/theme/`

| File | Contenuto |
|---|---|
| `colorAlpha.ts` | `toRgba` (ex `hexToRgba`), `withAlpha` (da `lotChartShared.ts`), `withHexAlpha` (ex `+ '88'`): stesse stringhe di oggi sugli input reali, mai `NaN` |
| `themePair.ts` | `ThemePair {light, dark}`, `themed(pair, dark)` (unico punto di scelta del tema), `both(v)` |
| `chartTheme.ts` | colori ECharts per significato: neutri con nome, guadagno/perdita (`lossLine`, `lossBar`…), serie per famiglia, formule |
| `chartPalettes.ts` | palette categoriali e scale |
| `toneClasses.ts` | classi Tailwind letterali per segno, stati e badge |
| `components/{table,media,files,dialogs}.css` | token di componente `--lf-cmp-<area>-<ruolo>` e gemelle `-dark`, su `:root` |
| `themeMode.ts` (W8) | `isDarkTheme()`, `onThemeClassChange(cb)` |

Regole:
1. Stessi valori e stesse stringhe di oggi.
2. Mai unire valori diversi; un nome = un valore + un significato.
3. I nomi dicono significato e divergenza.
4. Le API dei grafici restano come adattatori: i loro test fanno da oracolo.
5. Classi Tailwind sempre letterali e complete.
6. Le chiavi interpolate negli HTML dei tooltip non finiscono con i suffissi del gate HTML (`note`, `tooltip`, `name`…).
7. Si esporta solo ciò che si usa.

## 3. Prove di codice (sessione, fuori repo)

- **Conservazione** (`conserve.py`): per ogni file toccato, colori letterali, coppie chiaro/scuro e classi Tailwind del
  file originale = quelli del file nuovo dopo aver sostituito i riferimenti a `lib/theme/**` con i loro valori.
- **CSS Tailwind compilato** (W1, W2): build prima e dopo, CSS identico.
- **CSS dei componenti** (W6, W7): CSS compilato di ogni componente identico dopo la sostituzione delle `var()`.

## 4. Passi

### Passo 0 — Preparazione ✅ (14/10/2026)
- [x] Base verificata: HEAD = `b631308`, worktree pulito.
- [x] `npm ci` pre-approvato (14/10): `node_modules` mancava.
- [x] Baseline: build del frontend (23 CSS, hash salvati nella sessione), `svelte-check` 0 errori e 0 avvisi, Vitest
  completi **361 file / 11.193 test verdi**.

> **Note implementazione**: comandi `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front build`
> e `cd frontend && ./node_modules/.bin/vitest run --reporter=dot`. Le prove di codice (`conserve.py`, hash dei CSS)
> stanno negli artefatti della sessione R, fuori dal repo.
>
> **⚠️ Fuori pista**: `npm ci` (npm 11) blocca gli script di installazione (esbuild, fsevents); build e Vitest
> funzionano lo stesso.

### W0 — R-4 helper dell'alfa e refuso della meta ✅ (14/10/2026)
- [x] `lib/theme/colorAlpha.ts` (`toRgba`, `withAlpha`, `withHexAlpha`); `hexToRgba` tolto da `lineChartHelpers.ts`,
  `withAlpha` tolto da `lotChartShared.ts`; chiamanti aggiornati (`chartCoreHelpers.ts`, `LineChart`,
  `CandlestickChart`, `LotGanttChart`, `LotComparisonChart`); 4 concatenazioni → `withHexAlpha` (`GrowthChart` ×3,
  `AllocationHistoryChart` ×1).
- [x] Meta `theme-color` `#166534` in `themeStore.ts:59`, `app.html:26`, `static/offline.html:521`.
- [x] Test (`test-author`): `lib/theme/colorAlpha.test.ts` (19: golden contro il vecchio `hexToRgba`, `withAlpha`
  spostato byte per byte, `withHexAlpha`, «mai NaN» con controllo positivo), `src/themeColorMeta.gate.test.ts` (10:
  le tre copie della meta concordano; contenuto statico e `manifest.json` = valore chiaro; coppia = barra laterale di
  `app.css`; nessun altro scrittore), `lineChartHelpers.test.ts` e `lotChartShared.test.ts` adattati; registrazione in
  `front_utility_unit` (`core-unit`); `check-orphans` pulito (363 file).
- [x] Prove: conservazione (scarti solo voluti: la meta nei 3 file e i corpi delle funzioni spostate).

> **Note implementazione** (14/10): W0 ✅. Vitest dei 4 file 96 verdi; prove di mutazione del test-author (7 guasti sul
> gate, 8 su `colorAlpha`) tutte rosse dove atteso.
>
> **⚠️ Fuori pista**: `withAlpha('hsl(210 68% 44%)', a)` produce `hsla(210 68% 44%, a)`, sintassi mista non valida
> (comportamento preesistente, fissato dai test spostati). Oggi è irraggiungibile: a `withAlpha` arrivano solo hex e
> `hsl()` con virgole (`getBrokerColor`); `lotColor` (hsl con spazi) non ci passa. Correggerlo non cambierebbe pixel
> oggi, ma è fuori da W0: annotato nel backlog. Anche `toRgba` con tinte negative dà un colore sbagliato (non `NaN`):
> nessun grafico ne produce.
>
> **⚠️ Fuori pista**: per le prove di mutazione il test-author ha lavorato su una copia usa e getta in `/tmp`, con un
> `git init`/`commit` locale a quella copia, poi cancellata. Il git del worktree non è stato toccato.

### W1 — R-2a classi di segno ✅ (14/10/2026)
- [x] `lib/theme/toneClasses.ts`: `SIGN_TEXT` (`market`, `portfolio`, `kpi`, `headline`, `brokerCard`), `SIGN_BAR`
  (`kpi`, `accent`, `tornado`), `POLARITY_TONES` (correlazione, contributi al rischio, divergenza L2).
- [x] 42 siti in 20 file; soglie e condizioni invariate.
- [x] Prove: conservazione 20/20 file; CSS compilato identico; test dei componenti verdi.

> **Note implementazione**: sostituzioni esatte con conteggio atteso (script `w1_apply.py` della sessione); import
> inseriti dopo l'ultimo import dello script. `KpiSection.svelte` riformattato da Prettier solo sulle righe toccate.

### W2 — R-2b classi di stato e badge ✅ (14/10/2026)
- [x] `STATUS_TONES` (`syncIcon`, `pacBadge`, `pacNotice`, `pacTargetBar`, `pacTargetTotal`, `toast`, `reportSet`,
  `fileSet`, `riskAssetChip`, `dataQuality`) e `KIND_TONES.identifier`.
- [x] Chiamanti: `SyncResultRow` (e `STATUS_COLORS` tolto da `syncHelpers.ts`), PAC `ui.ts` (`BADGE`, `NOTICE`: layout
  nel kit, colori nella tabella), `TargetsStep`, `ToastContainer`, `ReportSetCard`, `FileSetBadges`, `AssetChip`,
  `DataQualityBanner`, `AssetGroupStep`.
- [x] Prove: conservazione (la mappa `STATUS_COLORS` spostata in `STATUS_TONES.syncIcon`, valori verificati identici);
  **CSS compilato identico** alla baseline (23 file, stessi nomi e hash); Vitest dei componenti toccati
  **37 file / 1.235 test verdi**; gate (`htmlInterpolation`, `htmlSink`, `flagFont`, `clipboardSink`,
  `moneyRenderSites`, `layout`) **6 / 66 verdi**; `svelte-check` pulito sul codice di produzione; knip senza
  segnalazioni sui file toccati.

> **Note implementazione**: in `NOTICE` del PAC l'ordine delle classi cambia (layout prima dei colori): stesso insieme di
> classi, nessun test fissa l'ordine. `AssetChip` ricompone `border`/`border-dashed` con il tono: stringhe identiche.

### Cancello A — gallery dopo il merge di G (coordinatore avvisato prima)

> **Stato del lotto A (W0–W2), 14/10:** codice e prove di codice completi. `svelte-check` 0 errori e 0 avvisi; Vitest
> completi **363 file / 11.217 test verdi** (baseline 11.193, più 29 nuovi, meno 5 spostati); Prettier pulito sui file
> toccati (`static/offline.html` era già fuori formato a `HEAD`: lasciato così); `git diff --check` pulito. Gallery in
> attesa del merge di G.
>
> **Checkpoint (14/10):** il coordinatore ha committato il lotto A (`d80b9e0cd`,
> `refactor(theme): central alpha and tone classes`, 52 file) e aggiornato la base con il merge di `dev_release2`
> (`b1fcc3c48`, solo documenti e script). Il lotto entra in `dev_release2` solo dopo il cancello A: prima entra G, poi
> la base di R viene riallineata, poi le due catture dello stesso giorno.

### W3 — R-1a neutri, guadagno/perdita, tooltip e scatter della famiglia prezzi ✅ (14/10/2026)
- [x] `lib/theme/themePair.ts`: `ThemePair {light, dark}` e `themed(pair, dark)`, l'unico punto che sceglie il tema.
- [x] `lib/theme/chartTheme.ts`: `PRICE_SERIES`, `CHART_GAIN_LOSS` (`price`, `tooltipDelta`), `CHART_NEUTRALS`
  (`priceAxis`, `dashboardGrid`, `secondaryAxisFallback`, `referenceLevelLabel`), `CHART_TOOLTIP_COLORS` (`box`,
  `candlestickBox`, `aside`, `staleWarning`), `RISK_RETURN_COLORS`. Valori copiati da 9 file, nessuno unito.
- [x] Chiamanti, 68 siti in 9 file (sostituzioni esatte con conteggio, script `w3_apply.py` della sessione, atomico):
  `LineChart` 16, `PriceChartFull` 14, `CandlestickChart` 14 (compreso `#888` a 3 cifre), `PriceChartCompact` 1,
  `lineChartHelpers.ts` 2 (`COLORS` resta come adattatore, con i valori delle tabelle), `chartCoreHelpers.ts` 4,
  `echartsTooltipHelpers.ts` 6, `priceChartHelpers.ts` 3 (+ il commento che cita gli hex), `scatterChartHelpers.ts` 7.
- [x] Prove: `conserve.py --diff` → **tutti e 9 i file conservati**, e con i valori reinseriti il testo coincide con
  `HEAD` riga per riga (differenze solo negli import, in una riga di documentazione di `COLORS`, nel commento di
  `buildDeltaHtml` e in una riga vuota); `vitest related` sui file toccati **30 file / 1.388 test verdi**; Prettier
  pulito; `svelte-check` 0 errori e 0 avvisi.

> **Note implementazione**: allocazione, semi-donut, storico allocazione e mappa passano in W4, con le loro palette, così
> ogni file si tocca una volta sola. Vincoli verificati: i registri dei gate (privacy, HTML) non contengono righe con
> colori scritti a mano; i nomi interpolati negli HTML dei tooltip evitano i suffissi del gate HTML (`note`,
> `tooltip`, `name`…) e nessuna chiave è calcolata. `CHART_GAIN_LOSS.line` rinominato `price` prima dell'uso: in W5
> arriva la famiglia del portafoglio (`#dc2626`).
>
> **⚠️ Fuori pista**: `conserve.py` reso attento alla precedenza (parentesi attorno a una condizione composta e attorno
> al ternario dopo `??`), altrimenti il confronto testuale segnalava `signal?.color ?? (dark ? …)` come diverso.
> `ChartSettingsModal.svelte:209` `color: '#000'`: stile di un segnale usato solo per calcolare punti sintetici, mai
> disegnato → resta, eccezione da dichiarare nel cricchetto (D7).

### W4 — R-1b palette, allocazione, mappe, correlazione, segnali ✅ (14/10/2026)
- [x] `lib/theme/chartPalettes.ts`: `ALLOCATION_PIE_PALETTE`, `SEMI_DONUT_PALETTE` (solo chiaro, si vede dal nome),
  `ALLOCATION_HISTORY_PALETTE`, `SIGNAL_DEFAULT_PALETTE`, `GEO_CHOROPLETH_SCALE`, `CORRELATION_SCALE`.
- [x] `chartTheme.ts` esteso: `ALLOCATION_CHART_COLORS`, `SEMI_DONUT_COLORS`, `GEO_MAP_COLORS`, `CORRELATION_COLORS`,
  `SIGNAL_COLORS` (ruoli, anteprima della legenda, misura); `CHART_NEUTRALS.dashboard` (era `dashboardGrid`) e
  `legendPageIconInactive`.
- [x] Chiamanti, 66 siti in 10 file (`w4_apply.py`, atomico): `AllocationPieChart` 17, `SemiDonutChart` 13,
  `AllocationHistoryChart` 10, `GeographyMap` 8, `ExposureMaps` 3, `CorrelationHeatmap` 9, `ChartSignal.ts`
  (`DEFAULT_SIGNAL_COLORS` resta come nome pubblico), `signalVisualStyle.ts`, `MeasureSignal.ts`, `SignalVisualLegend`.
  Nei componenti restano gli alias locali (`const PALETTE_LIGHT = ALLOCATION_PIE_PALETTE.light;`), così i commenti
  restano attaccati e il confronto testuale resta esatto.
- [x] Prove: `conserve.py --diff` → 18 file su 19 conservati alla lettera. `CorrelationHeatmap`: l'enfasi della cella
  passa da due oggetti scelti col tema a un oggetto con due `themed()`: stesse chiavi nello stesso ordine e stessi valori
  per tema, verificato a mano. Due tooltip passano da `'#fff'` a `'#ffffff'`: stesso colore. Prettier pulito.
- [x] Test (`test-author`): `colors`, `allocationHierarchy`, `allocationRings`, `AllocationHistoryChart` importano le
  palette da `chartPalettes` (stesse asserzioni: conteggi di `expect(`/`it(` uguali a `HEAD`); il lettore
  `src/__tests__/sourcePalettes.ts` e il suo test sono ritirati (14 test del lettore), `PALETTE_SLOTS` e `paletteDefects`
  vivono in `src/__tests__/palettes.ts` (+ `palettes.test.ts`, 4); controllo di comportamento sulla torta (ogni arco
  disegnato = voce della palette al suo rango, chiaro e scuro) e sullo **scuro dello storico allocazione** (3 righe:
  tipo, settore, geografia), con controllo positivo e prova di mutazione rossa; nuovo `lib/theme/chartTheme.test.ts`
  (strutturale: coppie `light`/`dark` complete, notazioni ammesse con i numeri nei limiti, liste senza doppioni e di
  pari lunghezza, `themed()`; 29 export, 137 coppie, 386 colori percorsi). Catalogo: `allocation-unit` aggiornato,
  `core-unit` + `chartTheme.test.ts`; `check-orphans` pulito (364).

> **Note implementazione**: il test strutturale carica i moduli con `vi.importActual`, così knip continua a segnalare una
> tabella che nessun grafico legge più. Rifiuta di proposito `transparent`, i colori con nome e `rgb()` con gli spazi:
> chi li aggiungerà a una tabella estenderà la tabella delle notazioni in testa al test.
>
> **⚠️ Fuori pista**: per le prove di mutazione il test-author ha usato una copia usa e getta in `/tmp` (link a
> `node_modules`, import riscritti, configurazione vitest temporanea), poi cancellata; nessun comando git.

> **Note implementazione**: `vitest related` dopo W4: 42 file verdi, 1 rosso atteso (`AllocationHistoryChart.test.ts`:
> il lettore di palette si ferma con il suo messaggio, come voluto da chi l'ha scritto); rossi attesi anche in
> `colors.test`, `allocationHierarchy.test`, `allocationRings.test`.
>
> **⚠️ Fuori pista**: `conserve.py` corretto due volte. Ora reinserisce anche i riferimenti senza percorso
> (`const PALETTE = SEMI_DONUT_PALETTE`), dopo aver tolto gli import di `lib/theme`, e normalizza i due lati, così i
> file del lotto A, già committati, si confrontano alla pari. Gli hex si confrontano normalizzati (`#fff` = `#ffffff`).

### W5 — R-1c serie e formule; lotti ✅ (14/10/2026)
- [x] `chartTheme.ts`: `CHART_GAIN_LOSS.portfolio` (il rosso `#dc2626` dei grafici di portafoglio, distinto da `price`
  `#ef4444`), `INCOME_EVENT_COLORS` (il dividendo ora è **una voce sola** per Growth e lotti, come chiedevano i due
  commenti «change both together»; l'interesse dei lotti resta diverso: `lotInterest` `#6d28d9`), `GROWTH_SERIES`,
  `GROWTH_CHART_COLORS`, `PERFORMANCE_COLORS`, `TREEMAP_COLORS`, `PAC_EXPOSURE_BAR_COLORS`, `RISK_OVERLAY_COLORS`,
  `LOT_STATE_COLORS`, `LOT_CHART_COLORS`, `LOT_GANTT_COLORS`, `LOT_WAC_COLORS`, `LOT_COMPARISON_COLORS`.
  `chartPalettes.ts`: `GROWTH_BROKER_PALETTE`. Nuovo `lib/theme/chartColorScales.ts`: `treemapPnlColor` e
  `timingEffectColor`, formule spostate parola per parola.
- [x] Chiamanti, 95 siti in 14 file (`w5_apply.py`): `GrowthChart` 11 (`COLORS` e `BROKER_PALETTE` restano come alias
  locali: le chiamate `cc('…')` che `chartCoreHelpers.test.ts` fissa non cambiano), `PerformanceChart` 22,
  `ExposureTreemap` 8, `KpiSection` 1, `ExposureBars` 1, `RiskAnalysisPanel` 2, `L4Simulation` 1, `lotStateVisual.ts` 3,
  `lotGanttChartHelpers.ts` 3, `lotWacPriceChartHelpers.ts` 3, `lotComparisonChartHelpers.ts` 3 (+ commento),
  `LotComparisonChart` 10, `LotGanttChart` 12, `LotWacPriceChart` 15.
- [x] Prove: `conserve.py --diff` → 30 file conservati. Restano tre differenze, tutte spiegate: le due formule spostate
  (verificate testo contro testo: identiche salvo firma, `isDark` passato e `TREEMAP_COLORS.noPnl`) e l'enfasi della
  heatmap (W4). `svelte-check` 0 errori e 0 avvisi; `vitest related` su tutti i sorgenti toccati **46 file / 1.807 test
  verdi**, l'unico rosso è `AllocationHistoryChart.test.ts`, in adattamento (W4). Prettier pulito: due righe mie oltre i
  300 caratteri riflesse da Prettier, conservazione ripetuta dopo.

> **Note implementazione**: lo stato «stimato» dei lotti dell'analisi è in realtà `PARTIAL` (`lotStateVisual.ts`).
> Il generatore dei lotti (`lotColor`, tinta dall'id) resta: è una formula, non un colore; eccezione per il cricchetto.
>
> **⚠️ Fuori pista**: `w5_apply.py` ha **duplicato `lotStateVisual.ts`**: il file non aveva import e l'inseritore dei
> `.ts` di W5, senza il ripiego di W3, ha scritto `text[:None] + import + text[None:]`. Il controllo di conservazione
> l'ha visto subito (colori «guadagnati»). Riparato verificando che le due copie fossero identiche (import in testa più
> una copia; diff finale +6/−3 righe) e corretto lo script. `conserve.py` ora mette tra parentesi anche il ternario
> annidato nel ramo «allora», come fa Prettier: così le parentesi non generano più differenze di testo.
### Cancello B — gallery dopo il merge di G (coordinatore avvisato prima)

> **Stato del lotto B (W3–W5), 14/10:** codice e prove di codice completi.
> - 229 siti in 33 file; nel perimetro grafici restano solo commenti, due eccezioni motivate (il generatore `lotColor`
>   e il `#000` di un segnale dimostrativo che non si disegna) e i `<style>` di W7. Erano 530 hex e 51 funzioni colore.
> - Conservazione: 30 file identici con i valori reinseriti, 3 differenze spiegate (W4, W5).
> - **CSS compilato identico** alla baseline (23 file); `svelte-check` 0 errori e 0 avvisi; Vitest completi
>   **364 file / 11.213 test verdi** (lotto A: 11.217; −14 del lettore ritirato, +5 strutturali, +2 torta, +3 scuro
>   dello storico); knip invariato; `check-orphans` pulito; Prettier e `git diff --check` puliti.
> - Il target ha 4 commit di soli documenti dopo la base comune `c942889e1`: nessun file di `frontend/` o del runner.

### W6–W7 — R-3 `<style>` (tabelle; media, file, dialoghi)
### Cancello C
### W8 — osservatori (D4) · W9 — P8 fuori elenco (D5) · W10 — cricchetto (D7), inventario, backlog, wiki, handoff

## 5. Test da adattare (`test-author`)

- ✅ Lettori di palette dai sorgenti (W4): `colors`, `allocationHierarchy`, `allocationRings`, `AllocationHistoryChart`
  importano da `chartPalettes`; `sourcePalettes.ts`/`.test.ts` ritirati, `src/__tests__/palettes.ts` al loro posto.
- ✅ Import spostati (W0): `lineChartHelpers.test.ts`, `lotChartShared.test.ts`. `registry.test.ts` non è cambiato:
  `DEFAULT_SIGNAL_COLORS` resta il nome pubblico.
- ✅ Oracolo rimasto verde senza modifiche: `chartCoreHelpers.test.ts` (testo `cc('…')` di Growth), test degli helper e
  dei lotti, test con classi (`AssetTable`, `RiskMetricCard`, `KpiDivergingFlowBar`, `TransactionFormModal`).

## 6. Conflitti e rischi

- **L:** nessun file in comune. R conserva il ridisegno a ogni cambio di classe. Lo scanner di L deve conoscere
  `lib/theme/**` e i `--lf-cmp-*`.
- **G:** nessun file in comune, salvo una correzione di G nel pannello dei lotti (`brokers/lots/**`) da ordinare con W5.
- **Catalogo del runner:** aggiunte additive anche da L e G.
- **Rischi per i pixel:** refusi nei valori; classi non più letterali; cascata in R-3; caricamento del CSS importato; HTML
  dei tooltip; tempi di ridisegno in W8; punti ciechi della gallery (hover, tooltip). Divergenze da non «aggiustare»:
  SemiDonut solo chiaro, Δ dei tooltip uguali nei due temi, scala del treemap invertita.

## 7. Registro di esecuzione
