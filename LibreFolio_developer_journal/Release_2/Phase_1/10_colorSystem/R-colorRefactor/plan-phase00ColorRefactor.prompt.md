# Piano R — Fattorizzazione dei colori a parità di aspetto

> Workstream **R** del programma colori 55. Sessione `R - fattorizzazione colori`, worktree `e-alfy-literate-tribble`,
> branch `e-alfy-r-fattorizzazione-colori`. Coordinatore: sessione `aec04834-1532-4d86-9e3f-f942e82aca89`.
> Base: `dev_release2` @ `b631308d5ef5482a8ffdc2878a4459fcf6909827`. Corsia: porta **6154**, dati **`/tmp/librefolio-r2-r`**.
> Piano generale: [`../plan-phase00ColorSystemThemeLab.prompt.md`](../plan-phase00ColorSystemThemeLab.prompt.md), riga R del §5.
> Fonti: [`../analysis/`](../analysis/00_SINTESI.md) (report 01–04). Backlog: sezione «R» di
> [`../../../Phase_0/BACKLOG_POST_1.2.md`](../../../Phase_0/BACKLOG_POST_1.2.md).
>
> **Stato finale (15/10/2026): ✅ chiuso.**
> - Lotti A–D in `dev_release2` da `8fd8e494b` (merge del target nel ramo R, poi avanzamento veloce del target), più
>   `23f6578f3` (`fix(pwa)`, il timbro del service worker).
> - Cancello gallery unico A+B+C+D superato.
> - W10 chiuso: vedi «W10 — chiusura» e il §7.

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
| `drawnColors.ts` (W7) | colori che una `var()` non raggiunge: tema di cheetah-grid, SVG in data URL (`LazyImage`, avatar di `FilesTable`) |
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
  - `r3.py verify`: a livello di sorgente, dichiarazione per dichiarazione, con lo stesso esbuild di Vite.
  - `r3_css_compare.py`: sulla build, regola per regola, contro la baseline.
  - `r3_reach.py`: sul manifest Vite, ogni entry che usa un token carica anche la sua definizione.
  - `w7_ts.py`: con controllo di annullamento, per i colori disegnati fuori dal CSS.

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

### Cancello A — gallery dopo il merge di G (coordinatore avvisato prima) ✅ (15/10/2026, cancello unico A+B+C+D)

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
### Cancello B — gallery dopo il merge di G (coordinatore avvisato prima) ✅ (15/10/2026, cancello unico A+B+C+D)

> **Stato del lotto B (W3–W5), 14/10:** codice e prove di codice completi.
> - 229 siti in 33 file; nel perimetro grafici restano solo commenti, due eccezioni motivate (il generatore `lotColor`
>   e il `#000` di un segnale dimostrativo che non si disegna) e i `<style>` di W7. Erano 530 hex e 51 funzioni colore.
> - Conservazione: 30 file identici con i valori reinseriti, 3 differenze spiegate (W4, W5).
> - **CSS compilato identico** alla baseline (23 file); `svelte-check` 0 errori e 0 avvisi; Vitest completi
>   **364 file / 11.213 test verdi** (lotto A: 11.217; −14 del lettore ritirato, +5 strutturali, +2 torta, +3 scuro
>   dello storico); knip invariato; `check-orphans` pulito; Prettier e `git diff --check` puliti.
> - Il target ha 4 commit di soli documenti dopo la base comune `c942889e1`: nessun file di `frontend/` o del runner.

### W6–W7 — R-3 `<style>` (tabelle; media, file, dialoghi)

**Metodo (vale per W6 e W7).** Strumento di sessione `r3.py`, che legge sempre l'originale da `git show HEAD:` e quindi
si può rilanciare.
- Ogni colore letterale di un `<style>` diventa `var(--lf-cmp-<componente>-<ruolo>)`, oppure la gemella `-dark`
  nelle regole `.dark`, che restano dove sono. Lo stesso vale per hex, `rgb()`/`hsl()` e i nomi (`white`, `black`, i
  nomi CSS dentro `color-mix()`).
- Le definizioni stanno su `:root` in `lib/theme/components/<area>.css`, importato dallo `<script>` del componente.
- Selettori, ordine, specificità e `!important` non cambiano.
- **Valori come li emetteva la build.** Esbuild di Vite (0.27.2, target `chrome107/edge107/firefox104/safari16`)
  quantizza i colori delle dichiarazioni normali (`rgb(0 0 0 / 0.1)` → `#0000001a`, alfa 26/255), ma **non tocca** le
  custom property. Se nella definizione restasse il letterale originale, l'alfa cambierebbe di un livello.
  - Ogni definizione porta quindi il testo esatto che la build emetteva per quel letterale, con l'originale in commento
    quando è diverso.
  - Le custom property già esistenti (`--highlight-base`…) e i fallback dentro `var()` restano scritti come prima: la
    build li lasciava intatti.
- **Ruoli.**
  - Un ruolo raggruppa le dichiarazioni dello stesso componente con lo stesso tipo di proprietà e la stessa coppia
    chiaro/scuro.
  - La coppia chiaro/scuro si trova dal selettore senza `.dark`: prima lista uguale, poi lista contenuta, poi
    sovrapposta.
  - I nomi sono curati a mano (`r3_names.json`). I ruoli condivisi hanno nomi di funzione (`surface-bg`, `border`,
    `muted-text`, `accent-bg`, `on-accent-text`, `field-*`), gli altri il nome dell'elemento.
  - **Un nome = un significato:** quando lo stesso valore serve concetti diversi, il ruolo si divide. Per esempio
    riga selezionata e badge di successo, intestazione e hover della riga, testo della cella e badge neutro.
- **Colore parametrico:** `rgba(245, 158, 11, var(--stale-opacity, 0.04))` (righe stale di DataTable) diventa
  `rgba(var(--lf-cmp-datatable-row-stale-rgb), var(--stale-opacity, 0.04))`, con la variabile che contiene solo i tre
  canali.
- **Prove:**
  1. sorgente (`r3.py verify`): dichiarazioni allineate a quelle di HEAD, con le `var()` sostituite dai valori
     centrali e minificate con lo stesso esbuild e lo stesso target, devono dare testo identico;
  2. CSS compilato (`r3_css_compare.py`): a valle della build, `var()` sostituite e hash svelte normalizzati, ogni
     file di asset deve risultare identico regola per regola al riferimento (liste di selettori espanse).

#### W6 — tabelle ✅ (14/10/2026)

> **Note implementazione**: `lib/theme/components/table.css`, 241 definizioni per 7 componenti:
> - `DataTable` (55 ruoli), `DataTableColumnFilter` (34), `DataTablePagination` (18), `DataTableToolbar` (11);
> - le tre tabelle di dominio: `UnifiedLotsTable` (3), `OtherPeriodEffectsTable` (2), `RiskReturnLevel` (3).
>
> 383 letterali in 382 dichiarazioni. Evidenze:
> - `r3.py verify`: OK, nessuna definizione inutilizzata;
> - build e `r3_css_compare.py` contro la baseline: **OK**, 4 file identici regola per regola (`trySave`,
>   `DataTableToolbar`, `RiskPartialNotice`, `assetPanelUrl`) e gli altri 19 identici byte per byte;
> - Prettier pulito, `svelte-check` 0 errori e 0 avvisi;
> - Vitest correlati: 43 file e 1.291 test verdi; gate dei sorgenti: 5 file e 67 test verdi;
> - knip invariato (38 righe).
>
> Il blocco `:root` finisce nel CSS condiviso `trySave`, che contiene già gli stili di DataTable. Il manifest Vite lo
> conferma: arriva a tutte le 11 pagine che usano i componenti.
>
> **⚠️ Fuori pista**:
> - Il primo abbinamento chiaro/scuro falliva sulle liste di selettori (spazi dopo la virgola normalizzati in ordine
>   diverso). Corretto, e aggiunto l'abbinamento per lista contenuta o sovrapposta.
> - In modalità dev (server Vite, senza minificazione) i colori con alfa ora valgono come in produzione: per esempio
>   26/255 invece di 0,1. La produzione, cioè gallery e utenti, è identica.
> - Pilota su `ContextMenu` riportato a HEAD prima di W6: rientra in W7.

#### W7 — media, file, dialoghi; colori disegnati fuori dal CSS ✅ (14/10/2026)

> **Note implementazione**:
> - **`<style>`.** 9 componenti, 528 letterali, 363 definizioni:
>   - `media.css`, 239 definizioni: `ImageEditModal` 43 ruoli, `AssetPickerModal` 25 + 1, `FileUploader` 29,
>     `FileEditModal` 28, `ImageCropper` 19;
>   - `files.css`, 78 definizioni: `FileGrid` 22, `FilePreviewModal` 23;
>   - `dialogs.css`, 46 definizioni: `ConfirmModal` 19, `ContextMenu` 8.
>
>   Ruoli particolari:
>   - Le custom property di cropperjs (`--theme-color`, `--cropper-backdrop-color`,
>     `--cropper-selection-outline-color`) puntano ai token. I nomi restano quelli della libreria.
>   - Le maniglie laterali del cropper (bianche nei due temi) sono un solo ruolo, `handle-side-bg`: la regola scura
>     copre tutte e quattro le maniglie.
> - **Stile inline** di `AssetPickerModal`: il rosso del pulsante che svuota l'URL diventa
>   `var(--lf-cmp-asset-picker-url-clear-btn-text)`, `#dc2626` come prima. Gli stili inline non passano da esbuild,
>   quindi il valore resta quello scritto.
> - **Colori disegnati fuori dal CSS** → nuovo `lib/theme/drawnColors.ts`:
>   - tema scuro di cheetah-grid, spostato alla lettera (funzione che crea un oggetto nuovo a ogni chiamata);
>   - bordi del tema chiaro (`{...SPREADSHEET_LIGHT_BORDERS}`, sempre un oggetto nuovo);
>   - ambra delle righe indicate;
>   - colori delle SVG segnaposto di `LazyImage`, interpolati nella stessa stringa;
>   - iniziale bianca degli avatar di `FilesTable`.
>
> Evidenze:
> - `r3.py verify` sui 16 componenti: **908 dichiarazioni, 604 definizioni, nessuna inutilizzata, OK**. Il controllo
>   riporta lo spostamento di `FilePreviewModal` sul testo di HEAD.
> - `w7_ts.py`: annullando ogni sostituzione si riottiene il testo d'ingresso, byte per byte. `conserve.py` OK su
>   `FilesTable` (1) e `LazyImage` (11).
> - Build e `r3_css_compare.py`: **OK**, 8 file identici regola per regola e 15 byte per byte.
> - `r3_reach.py`, sul manifest Vite: ognuna delle 36 entry, statiche e dinamiche, che carica una regola con
>   `var(--lf-cmp-…)` carica anche la definizione.
> - `svelte-check` 0 errori e 0 avvisi. Prettier pulito.
> - Vitest correlati: 60 file e 1.664 test. **Vitest completo: 364 file e 11.213 test verdi**, come nel lotto B.
> - knip invariato (38 righe); `check-orphans` pulito; `git diff --check` pulito.
> - **Gate nuovo** `src/themeComponentTokens.gate.test.ts`, scritto da `test-author` e registrato in `core-unit`
>   accanto a `themeColorMeta`. Controlli:
>   - (a) ogni `var(--lf-cmp-…)` di un `.svelte` nomina, per intero, un token definito una volta sola;
>   - (b) ogni componente che legge un token importa il file d'area che lo definisce (il messaggio dice la riga da
>     aggiungere);
>   - (c) nessun token definito due volte, nessuno non letto;
>   - (d) ogni file d'area è un solo `:root` di dichiarazioni, e fuori dai file d'area un token si nomina solo come
>     lettura di un componente;
>   - (e) controlli positivi: la scansione legge qualcosa.
>
>   17 test alla prima stesura (8 su alberi sintetici che rompono ogni regola, 9 sui file veri, di cui uno che li
>   altera in memoria e vede ogni controllo diventare rosso); 18 dopo il ritocco del percorso (vedi «Cancello C»).
>   `check-orphans`: 365 file unitari raggiungibili.
>
>   Note del `test-author`, verificate:
>   - 3 gemelle `-dark` senza chiaro: ruoli solo scuri, come nel sorgente;
>   - 6 gemelle uguali al chiaro: le regole `.dark` ridichiaravano lo stesso valore; da unire nella fase B;
>   - 3 `white` senza commento: la build li lasciava `white`, cioè nello shorthand `border` e in `color-mix()`; lo
>     conferma la baseline compilata.
>
> **⚠️ Fuori pista**:
> - Tre valori `rgba()` che la build lasciava in forma di funzione (nello shorthand `border` e nell'`outline`):
>   esbuild li comprimeva (`rgba(255,255,255,.6)`) e Prettier li riallargava. Ora sono scritti come nel sorgente; la
>   custom property li porta invariati.
> - **`LazyImage` non è più un'eccezione del cricchetto.** L'analisi la escludeva per le SVG in stringa, ma i due
>   colori si interpolano nella stessa stringa: la data URL è identica.
> - Eccezioni che restano per W10:
>   - il generatore `lotColor`;
>   - il `#000` dimostrativo di `ChartSettingsModal`;
>   - `hslToHex` di `MeasurePanel`;
>   - il viola `#a855f7` della linea di anteprima in `assets/AssetDataEditorSection.svelte:248` e
>     `fx/FxDataEditorSection.svelte:129`: cartelle della 1.3, fuori perimetro, voce R-6 del backlog, decisione del
>     coordinatore al checkpoint B.

### Cancello C ✅ (15/10/2026, cancello unico A+B+C+D)

> **Stato del lotto C (W6–W7), 14/10:** codice e prove di codice completi.
> - 16 componenti e 908 dichiarazioni → 604 token `--lf-cmp-*` in 4 file centrali.
> - 3 file con colori disegnati fuori dal CSS → `drawnColors.ts`.
> - CSS compilato identico.
> - Aspetta il merge di G e il via del coordinatore per la gallery, eventualmente insieme ad A e B.
> - **Deciso il 14/10 alle 23:35:** un solo cancello gallery per A+B+C+D, dopo la misura di G e l'aggiornamento della
>   base con G (vedi «Merge della base con T-1», «Prossimi passi»).
>
> **Inventario** (`scripts/visual_review/color_inventory.py`, solo codice di prodotto). Letterali fuori da `lib/theme/**`
> e da `app.css`, dalla base `b631308` al lotto C:
> - hex: 1.554 → 229;
> - funzioni colore: 198 → 72.
>
> Nel perimetro di R restano solo:
> - commenti che citano un valore;
> - le eccezioni (generatori `lotColor` e `colors.ts`, il `#000` dimostrativo);
> - funzioni costruite su token (`color-mix()` dei lotti, `rgba(var(…))` delle righe stale).
>
> W9 ne toglie altri 163. Ciò che resta fuori dal perimetro (`TransactionsTable`, `supportLinks`, `ChangelogModal`,
> `AnimatedBackground`, `LoadingSpinner`…) lo blocca il cricchetto M2 di T, che dal 14/10 prende la parte «colori
> letterali» di W10 (vedi W10).
>
> **⏸️ Finestra di quiete 21:25–22:45 ✅ chiusa in anticipo alle 22:20** (coordinatore: misura finale del rumore
> della gallery di G).
> - Nella finestra solo codice, piano e analisi statica.
> - Il ritocco del percorso del gate l'ha scritto un nuovo `test-author`, in sola modifica (il primo non esisteva
>   più); il nuovo l'ha verificato dopo l'apertura.
>
> **Ritocco del gate ✅ (14/10/2026, 22:25).** `themeComponentTokens.gate.test.ts` non legge più:
> - i percorsi del Designer Lab, per intero (D7): il Lab legge, compone e sovrascrive i token dal vivo, per mestiere;
> - i file di test (`*.test.ts`, `__tests__/`, `__mocks__/`), come nei gate fratelli: un test non è un lettore di
>   produzione, e T (B5) scriverà test che nominano i `--lf-cmp-*`.
>
> > **Note implementazione**:
> > - Nuovo filtro `isScanned(path)`, applicato sia alla scansione di `src` sia agli alberi sintetici; `SELF` tolto.
> > - 18 test. Nuovi casi:
> >   - il filtro, su 18 percorsi, compresi i quasi omonimi che vanno letti;
> >   - un file di test o del Lab può nominare token in ogni forma, mentre lo stesso testo in un percorso normale
> >     diventa rosso;
> >   - un token letto solo dal Lab risulta non usato per (c).
> > - Prova di efficacia del `test-author`: tre mutazioni del filtro, ciascuna fa diventare rossi i test giusti.
> > - Prefissi verificati sul design di L: la rotta è `src/routes/designer-lab/`, fuori dai gruppi.
> > - Evidenze:
> >   - Vitest sul file: 18/18; Prettier invariato;
> >   - `core-unit`, corsia 6154: **132 file e 4.242 test verdi**; il gate gira dentro `core-unit` (registrato
> >     accanto a `themeColorMeta`, verde nei risultati delle 22:26);
> >   - `check-orphans`: 365 file unitari raggiungibili;
> >   - `git diff --check` pulito; porta 6154 libera.
### W8 — osservatori (D4) · W9 — P8 fuori elenco (D5) · W10 — cricchetto (D7), inventario, backlog, wiki, handoff ✅ (15/10/2026)

> **Preparazione offline (14/10, durante la finestra di quiete).** Niente scritto nel worktree: gli script stanno
> nella sessione e si applicano dopo il commit del lotto C.
>
> **W8 (`w8_apply.py`)**, nuovo `lib/theme/themeMode.ts`:
> - `isDarkTheme()`;
> - `onThemeClassChange(onChange)`: osserva `class` su `<html>` e restituisce il `MutationObserver` già attivo.
>
> I file si trovano per contenuto, quindi gli spostamenti della 1.3 non lo toccano. Il dry-run trova:
> - 19 file;
> - **16 osservatori del tema**, tutti con `{attributes: true, attributeFilter: ['class']}` su
>   `document.documentElement`;
> - 23 controlli `classList.contains('dark')` nel codice e 1 in un commento (`scatterChartHelpers.ts`);
> - 8 osservatori non di tema lasciati stare (`Header`, onboarding, `RiskCardGrid`, `scrollOnOverflow`, visibilità di
>   `AllocationHistoryChart`, `OtherPeriodEffectsTable`).
>
> Il controllo di annullamento dà OK.
> - **Nomi delle variabili invariati** (`darkModeObserver`, `observer`, `darkObserver`) e così `disconnect()`:
>   `chartCoreHelpers.test.ts` cerca `\n    let darkModeObserver` nel sorgente di GrowthChart per delimitare il
>   watcher del resize.
> - Stesso ridisegno a ogni cambio di classe e stessa consegna in microtask; la callback ora non riceve argomenti:
>   nessuna la usava.
> - Test da chiedere a `test-author` per `themeMode`:
>   - qualunque classe scatena, gli altri attributi no;
>   - nessun argomento alla callback;
>   - dopo `disconnect()` niente più chiamate;
>   - solo `<html>`.
>
> **W9 (`r3.py`, 4 componenti in più):**
> - `routes/(app)/files/+page.svelte` → `files.css`, 28 ruoli;
> - `brokers/BrokerImportFilesModal.svelte` → `files.css`, 11;
> - `transactions/modals/ImportBrokerMismatchModal.svelte` → `dialogs.css`, 27;
> - `ui/display/CompactCashCell.svelte` → `table.css`, 10.
>
> In tutto 172 letterali e 76 ruoli, con nomi curati. Ritocchi a `r3.py`:
> - riscrive solo le sezioni dei componenti selezionati e conserva le altre (prova di andata e ritorno sui 4 file
>   d'area: identici);
> - controlla le definizioni inutilizzate solo per i componenti selezionati;
> - accetta i componenti sotto `routes/`.
>
> Divergenza da lasciare: il focus di `CompactCashCell` è `#10b981` (emerald) mentre il commento dice «libre-green».
>
> **W10 e il cricchetto M2 di T** (proposta del coordinatore, 14/10 alle 21:56; risposta di R alle 22:05).
> - **Proposta.** M2, il gate di T (workstream «token e tema», corsia 6155), prende la parte «colori letterali» del
>   cricchetto di D7: hex, `rgb()`, `hsl()` e `oklch()` fuori da `lib/theme/**`, `app.css`, `app.html` e `static/`,
>   contati per file, solo in discesa, tollerante alle rinomine.
> - **Risposta di R: d'accordo, con 6 buchi segnalati** (scansione statica in sola lettura, `m2_holes.py` nella sessione):
>   1. i nomi CSS: 13 in 7 file, 4 dopo W9; R-3 ne aveva tolti circa 70;
>   2. i test, da escludere: 44 file con letterali, 8 toccati o creati da R;
>   3. gli scambi a conteggio pari: 9 letterali nei commenti in 6 file; meglio confrontare i valori per file;
>   4. le classi Tailwind di R-2: se T non ha un cricchetto sulle classi di palette, la protezione resta in W10 fino
>      a B2;
>   5. l'esenzione D7 dei percorsi di L;
>   6. la base: i cali vanno accettati senza un file condiviso fra le corsie.
> - **Eccezioni consegnate** per l'elenco di T:
>   - `lotColor`;
>   - i generatori di `colors.ts` (:57-62, :100-103);
>   - `MeasurePanel` (`hslToHex`, nessun letterale);
>   - il `#000` di `ChartSettingsModal`;
>   - il `#a855f7` (R-6);
>   - i due `rgba(var(--lf-cmp-…-rgb), …)` di `DataTable`, costruiti su token.
> - **W10 ridotto a:**
>   - la consegna dell'elenco;
>   - un gate su D4: il tema si legge solo da `themeMode.ts`;
>   - inventario, backlog, wiki, handoff.
> - **Confermato dal coordinatore** (22:05):
>   - T recepisce in M2 i 6 punti e le eccezioni.
>   - Il punto 4 lo copre M1 di T, il cricchetto per file sulle classi legacy: nessuna aggiunta per R-2.
>   - Il punto 6 è già la regola di T: i cali passano senza toccare la sua baseline, che T stringe ai checkpoint.
>   - W10 resta come descritto sopra.
>   - I gate `themeColorMeta` e `themeComponentTokens` restano; quello della meta passa a T con T-4.

#### Lotto D — base `74e94dee6` (lotto C committato in `0b660632f`, piano spostato in `Phase_1/10_colorSystem`)

#### W8 — un solo punto per leggere il tema (D4) ✅ (14/10/2026)

> **Note implementazione**: `w8_apply.py`; il dry-run sulla nuova base dava gli stessi conteggi.
> - Nuovo `lib/theme/themeMode.ts`: `isDarkTheme()` e `onThemeClassChange(onChange)`, che restituisce il
>   `MutationObserver` già attivo.
> - 19 file:
>   - 16 osservatori del tema, diventati `X = onThemeClassChange(callback)`;
>   - 23 letture di `classList.contains('dark')` in codice, diventate `isDarkTheme()`;
>   - 1 commento (`scatterChartHelpers.ts`) allineato.
> - Restano invariati:
>   - i nomi delle variabili e i `disconnect()`;
>   - il ridisegno a ogni cambio di classe di `<html>`;
>   - la consegna in microtask.
> - 8 osservatori non di tema lasciati stare. Nessuno, oltre a `themeMode.ts`, osserva più `<html>`.
>   `AllocationHistoryChart` osserva gli antenati del grafico per la visibilità; `app.html` e `themeStore` scrivono la
>   classe e non la leggono.
>
> Evidenze:
> - controllo di annullamento byte per byte OK;
> - `conserve.py` OK sui 19 file (colori invariati);
> - Prettier pulito; `svelte-check` 0/0;
> - Vitest correlati: 25 file e 766 test verdi;
> - CSS compilato: i 17 file che W9 non tocca sono identici byte per byte alla build del lotto C, quindi W8 non
>   cambia il CSS.
>
> **Test (`test-author`) ✅**:
> - `lib/theme/themeMode.test.ts`, 19 test in jsdom: qualunque classe di `<html>` scatena; nient'altro; nessun
>   argomento; più modifiche nello stesso turno arrivano in una sola chiamata; dopo `disconnect()`, più niente.
>   L'attesa è in microtask, senza orologio. 9 versioni guaste degli helper fanno diventare rossi i test giusti.
> - Gate D4 `src/themeModeReads.gate.test.ts`, 24 test, anticipato da W10. Fuori da `themeMode.ts`:
>   - (a) nessuna lettura della classe `dark`;
>   - (b) nessun osservatore che possa vedere la classe di `<html>`;
>   - (c) ogni `onThemeClassChange` assegnato e poi `disconnect()`;
>   - (d) controlli positivi.
>
>   Esenti i test e il Lab (D7). Un test fissa i punti ciechi dichiarati: un alias di `<html>`,
>   `querySelector('html')`, `matches('.dark')`.
> - Registrati entrambi in `core-unit`.
>
> **Evidenze finali del lotto D**:
> - Vitest completo: **367 file e 11.274 test verdi**;
> - `core-unit` nella corsia 6154: 134 file e 4.285 test verdi;
> - `check-orphans`: 367 file unitari raggiungibili;
> - knip invariato (38 righe); `git diff --check` pulito.
>
> **⚠️ Fuori pista** (osservazioni del `test-author`, verificate; tutte precedenti a W8, nessuna toccata):
> - `SemiDonutChart` e l'anteprima a tabella di `FilePreviewModal` leggono il tema al disegno ma non hanno
>   osservatore. A un cambio di tema restano con i colori vecchi fino al ridisegno successivo o alla riapertura.
>   Correggerlo cambia il comportamento, quindi non è di R: voce **R-7** del backlog, per T (B4) e per il Lab, che
>   riapplica dal vivo.
> - Il ciclo di visibilità di `AllocationHistoryChart` sale fino a `<html>`, quindi vede anche la classe del tema.
>   Non è un osservatore di tema: `syncVisibilityState()` esce subito se la visibilità non cambia. Innocuo.
> - `LotGanttChart` crea l'osservatore in un `$effect` senza dipendenze reattive. Oggi gira una volta sola; se un
>   giorno acquistasse una dipendenza, la sua pulizia staccherebbe anche i watcher del resize. Fragilità latente,
>   nessun difetto oggi.

#### W9 — i quattro file P8 fuori elenco (D5) ✅ (14/10/2026)

> **Note implementazione**: `r3.py`, con i nomi curati offline nella finestra di quiete.
> - 4 componenti, 172 letterali → 76 ruoli, 124 definizioni:
>   - `routes/(app)/files/+page.svelte` → `files.css`, 28 ruoli;
>   - `brokers/BrokerImportFilesModal.svelte` → `files.css`, 11;
>   - `transactions/modals/ImportBrokerMismatchModal.svelte` → `dialogs.css`, 27;
>   - `ui/display/CompactCashCell.svelte` → `table.css`, 10.
> - I file d'area sono solo cresciuti: le sezioni del lotto C sono intatte, cambia la riga d'intestazione e si
>   aggiungono le sezioni nuove in coda.
> - In tutto 728 token, in 4 file d'area.
>
> Evidenze:
> - `r3.py verify` sui 4: 172 dichiarazioni identiche a HEAD dopo la sostituzione e la minificazione; nessuna
>   definizione inutilizzata;
> - build e `r3_css_compare.py` contro la baseline **`b631308`** (prova cumulativa dei lotti C e D): **OK**, 11 file
>   identici regola per regola e 12 byte per byte;
> - `r3_reach.py`: le 36 entry caricano le definizioni che usano;
> - i 6 CSS cambiati rispetto al lotto C contengono tutti token di W9;
> - Prettier pulito; `svelte-check` 0/0;
> - Vitest correlati: 1.388 test verdi; gate `themeComponentTokens` e `themeColorMeta`: 28 test verdi.

#### Merge della base con T-1 ✅ (14/10/2026, 23:35)

> **Note implementazione**: il coordinatore ha committato il lotto D (`98731240d`, 32 file) e ha aperto il merge di
> `dev_release2` (`6ab653dd4`, con T-1 dentro). R l'ha risolto e validato senza committare; il coordinatore l'ha
> chiuso in **`418ea8042`**, con genitori `98731240d` e `6ab653dd4`.
> - **Conflitto, solo nel runner** (`_frontend_utility.py`, lista di `core-unit` dopo `clipboardSink`). Tenute tutte
>   e cinque le righe, le tre di R (`themeColorMeta`, `themeComponentTokens`, `themeModeReads`) e le due di T
>   (`themeRoles`, `themeTokens`); il `desc` è quello di T. Stage del solo file risolto.
> - **Fusi da soli:** in `BACKLOG_POST_1.2.md` la sezione R è identica al lotto D e la sezione T è presente alla
>   lettera; nessun marcatore di conflitto nell'albero.
> - **Un rosso, deciso dal coordinatore.** Il cricchetto di T (`theme-roles.mjs --check`, gate `themeRoles`)
>   segnalava `R2 m2 lib/stores/app/themeStore.ts: colour literals beyond its record: #166534`.
>   - La correzione D3 del lotto A (`#156534` → `#166534`) è uno scambio di colore. La baseline di T, registrata
>     prima di R, la leggeva come una crescita.
>   - Su autorizzazione del coordinatore (23:33): `--accept src/lib/stores/app/themeStore.ts --reason "D3
>     (developer, 14/10): …"`. Cambia una riga della baseline e se ne aggiunge una `~accept` con la motivazione;
>     stage di quel file solo.
>   - Quando T-4 sposterà la meta sul verde della testata, la riga cambierà di nuovo: lo farà T.
>
> Evidenze sulla revisione combinata:
> - `theme-roles.mjs --check`: pulito («81 files dropped below their record»: stringe T);
> - `core-unit` nella corsia 6154: **136 file e 4.335 test verdi**, con i gate di T e di R;
> - `svelte-check` 0/0;
> - **nuovo CSS di riferimento** = la build del merge (sessione, `merge-css`), 23 file;
> - **prova combinata.** Il target `dev_release2` è stato costruito in una copia usa e getta in `/tmp`, poi
>   cancellata: `git archive` più gli stessi input generati, cioè API e cataloghi i18n, senza differenze nei
>   sorgenti backend o i18n (script `build_target.sh` nella sessione). Il confronto tra target e merge con
>   `r3_css_compare.py`, con i 728 token sostituiti, dà **OK**: 11 file identici regola per regola e 12 byte per
>   byte. T-1 e R non si toccano nel CSS compilato;
> - `r3_reach.py` sul merge: 36 entry OK.
>
> **⚠️ Fuori pista**:
> - La build del target nella copia chiedeva anche `scripts/` (l'hook `prebuild` di npm genera il catalogo i18n) e
>   `CHANGELOG.md` (importato con `?raw` dal changelog). Estratti anche questi da `dev_release2`.
> - T-1 ha aggiunto `@source not './theme*.gate.test.ts'` ad `app.css`. Copre anche i gate di R: Tailwind non legge
>   più le loro stringhe sintetiche, e il CSS compilato resta identico.
>
> **Prossimi passi** (coordinatore, 23:35):
> - un solo cancello gallery per i lotti A+B+C+D, domani, dopo la misura di G;
> - prima di quel cancello il coordinatore aggiorna la base con G;
> - W10 (chiusura) dopo il cancello; fino ad allora niente lavoro nuovo sul codice.

#### Merge della base con T-2 ✅ (15/10/2026, validato alle 10:25)

> **Note implementazione**: il coordinatore ha aperto il merge di `dev_release2` (`2338aaf79`) dentro `2c8508efb`.
> Contenuto: T-2, gli spostamenti A2 di auth, settings e support in `lib/features/`, l'endpoint `/system/instance` di H.
> R l'ha risolto e validato senza committare; il coordinatore l'ha chiuso in **`87b7c34b8`** (genitori `2c8508efb` e
> `2338aaf79`).
> - **Unico conflitto: `frontend/src/themeRoles.baseline.tsv`**, in fondo al file. È la stretta di T-2
>   (`routes/+error.svelte` a 0, `routes/+page.svelte` da 5 a 1) accanto alla riga `~accept` di D3.
>   - `theme-roles.mjs --resolve` ha di nuovo tolto `#166534` dal record di `themeStore.ts`. `mergeBaselines` dà a una
>     riga presente sui due lati solo i colori che entrambi hanno, senza guardare la base né l'`~accept`. Previsto con
>     una prova a secco (`resolveConflict` + `compareWithBaseline`, senza scrivere) e segnalato prima di agire.
>   - Su autorizzazione del coordinatore (09:07), lo stesso `--accept` di D3: il record torna `0 #166534 #1a4031`, con
>     una sola riga `~accept`. Rispetto al target cambiano solo queste due righe, rispetto al lato R solo la stretta di
>     T-2. Stage della sola baseline.
>   - La correzione di `mergeBaselines` va a T: voce **R-8** del backlog.
> - **Fusi da soli, controllati:** il runner aggiunge al target solo le 6 righe di R, e i 668 percorsi registrati
>   esistono; nel backlog la sezione R è quella del lato R, il resto è il target alla lettera.
> - Nessun file di R rinominato dai 79 spostamenti; nessun manifest di dipendenze cambiato.
>
> Evidenze sulla revisione combinata (corsia 6154, dopo il via delle 10:15):
> - `theme-roles.mjs --check` pulito (81 file sotto il loro record: stringe T);
> - `core-unit`: **140 file e 4.380 test verdi**; i 6 file colore di R e i 2 gate di T verdi nei risultati;
> - `front check`: al primo giro 2 errori in `features/instance`, perché il client API generato era più vecchio di
>   `/system/instance`; `front build` sincronizza l'API, e il secondo giro dà **0 errori e 0 avvisi**;
> - **nuovo CSS di riferimento** = la build del merge (23 file, sessione `merge3-css`). Rispetto a quella del 14/10
>   cambiano solo i chunk `0` e `2`, uguali tra target e merge: vengono dal target;
> - **prova combinata**: target costruito in una copia `/tmp`, poi cancellata. `r3_css_compare.py` **OK**: 11 file
>   identici regola per regola e 12 byte per byte, con i 728 token sostituiti; `r3_reach.py`: 36 entry OK;
> - `check-orphans` pulito: 376 unitari, 118 E2E, 277 backend.

#### Cancello unico A+B+C+D ✅ (15/10/2026)

> **Gallery** catturata dal coordinatore, tolleranza 0, maschere del rumore r1↔r2 della misura di G:
> - riferimento `g-final3-r1` sul target `2338aaf79` (09:14);
> - candidata `g-final3-candR` su `87b7c34b8`, nella corsia 6154 (10:29).
>
> Risultato:
> - **2.370 immagini identiche e 454 cambiate**. Solo 9 superano il rumore del proprio scatto: 8 `files/static-grid`
>   (orario di caricamento e miniatura del DB della corsia: contenuto) e 1 `detail-signals` (max Δ5 su 255).
> - **Revisione di R delle 15 immagini cambiate in scatti stabili**, quelle che il report indica come «probabilmente
>   reali»:
>   - `brokers/import-modal` (4, max Δ211 in un riquadro di 17×11 px): è l'ora nella colonna «Uploaded»
>     (`Oct 15, 2026, 0…` alle 09:14, `…1…` alle 10:29). Contenuto;
>   - `risk/whatif-simulation` (1, Δ15): lo stato transitorio della «×» di chiusura del riquadro, che R non tocca;
>   - le altre 10, con Δ ≤ 3: antialiasing.
> - Con la regola «conta lo stile», nessuna differenza di stile o di colore. **Cancello superato** (coordinatore,
>   15/10).
> - Evidenze: `LibreFolio_visual_review/diffs/g-final3__r1__vs__candR/` (`report.md`, `summary.json`, `composites/`).

#### Ingresso in `dev_release2` ✅ (15/10/2026, 11:21)

> - `8fd8e494b`: merge del target (`6ed99c694`) nel ramo R, poi avanzamento veloce di `dev_release2`.
> - `23f6578f3` `fix(pwa): restamp the service worker`: `dev_release2` è a `23f6578f3`.
>
> **⚠️ Fuori pista** (lotto A, W0):
> - La correzione D3 ha cambiato `static/offline.html` senza aggiornare il timbro di `static/sw.js`, cioè l'MD5 di
>   `offline.html`.
> - Il timbro lo scrive `stamp_service_worker()` di `dev.py`, dentro `copy_docs_assets()`. Lo chiamano la build della
>   documentazione (`mkdocs build/serve/deploy`), le risorse di Docker e `auto_build_mkdocs()` all'avvio del server di
>   test, non `front build`. Per questo le build di R non sporcavano il worktree, e la run della candidata sì.
> - La guardia esiste (`backend/test_scripts/test_utilities/test_pwa_assets.py`), ma è un test backend, fuori dai
>   selettori frontend di R. Corretto dal coordinatore all'ingresso.
> - Lezione: chi tocca `offline.html` ritimbra e committa `sw.js` nella stessa modifica, e lancia `test_pwa_assets`.
>   È nella pagina wiki `features/F-098`.

#### W10 — chiusura ✅ (15/10/2026)

> **Note implementazione**: solo documenti. Nessun comando pesante: la finestra delle candidate di L e T era ancora
> aperta. Solo l'inventario statico.
> - **Elenco delle eccezioni** (consegnato a T il 14/10, verificato sul codice di `23f6578f3`).
>   `LITERAL_EXCEPTIONS` di `frontend/scripts/theme/theme-roles.mjs` contiene tutte le eccezioni di R, con i percorsi
>   aggiornati dopo gli spostamenti:
>   - `lotColor`, l'`hsl()` generato dall'id del lotto (`brokers/lots/lotComparisonChartHelpers.ts`);
>   - i generatori `hsl()`/`hsla()` di `lib/utils/colors.ts`;
>   - il `#000` del segnale dimostrativo, mai disegnato (`charts/ChartSettingsModal.svelte`);
>   - il `#a855f7` della linea di anteprima (`assets/AssetDataEditorSection.svelte`, `fx/FxDataEditorSection.svelte`;
>     R-6).
>
>   Non servono eccezioni per: `hslToHex` di `MeasurePanel` (nessun letterale); i due
>   `rgba(var(--lf-cmp-datatable-row-stale-rgb…), …)` di `DataTable` (costruiti su token: per T non sono letterali); i
>   commenti (M2 li ignora). I marchi dei social di `supportLinks.ts` sono un'eccezione di T, ora in
>   `lib/features/support/`.
> - **Gate D4**: anticipato in W8 (`themeModeReads`). Sul codice di `23f6578f3`, fuori da `themeMode.ts`, non resta
>   nessuna lettura della classe `dark` né alcun osservatore della classe di `<html>`.
> - **Inventario finale** (`scripts/visual_review/color_inventory.py`, codice di prodotto, `23f6578f3`). Letterali fuori
>   da `lib/theme/**` e da `app.css`:
>
>   | | base `b631308` | lotto C | lotto D | finale |
>   |---|---:|---:|---:|---:|
>   | hex | 1.554 | 229 | 88 | **85** |
>   | funzioni colore | 198 | 72 | 50 | **50** |
>
>   Restano 34 file. Sono fuori dal perimetro di R (`TransactionsTable`, `ChangelogModal`, `AnimatedBackground`,
>   `LoadingSpinner`, `Tooltip`…) oppure eccezioni dichiarate; li sorveglia il cricchetto M2 di T.
> - **Backlog**, sezione R:
>   - R-1…R-4 chiuse ✅, con data e commit;
>   - link riallineati a `../Phase_1/10_colorSystem/…`;
>   - nuova **R-8** per T (`mergeBaselines`);
>   - restano aperte R-5, R-6 e R-7.
> - **Wiki**: proposte nel worktree, che il coordinatore committa dopo la revisione.
>   - Pagine nuove:
>     - `wiki/decisions/colour-factorisation-at-pixel-parity.md`;
>     - `wiki/problems/esbuild-colour-minify-skips-custom-properties.md`;
>     - `wiki/problems/colour-ratchet-resolve-drops-an-accept.md`.
>   - Pagine aggiornate:
>     - `wiki/features/F-007.md`, corretta la deriva: i grafici seguono il tema con `onThemeClassChange()`, non con
>       «store reattivi»;
>     - `wiki/features/F-098.md`, il timbro di `sw.js`;
>     - `wiki/problems/front-check-does-not-check-what-you-think.md`, il client generato invecchiato da un merge.
>   - Aggiornati anche `index.md` e `log.md`; `check_source_paths.py` pulito.
>   - Grafo non aggiornato: graphify non è disponibile in questo worktree (P-6).
> - **Handoff finale** al coordinatore.

## 5. Test da adattare (`test-author`)

- ✅ Lettori di palette dai sorgenti (W4): `colors`, `allocationHierarchy`, `allocationRings`, `AllocationHistoryChart`
  importano da `chartPalettes`; `sourcePalettes.ts`/`.test.ts` ritirati, `src/__tests__/palettes.ts` al loro posto.
- ✅ Import spostati (W0): `lineChartHelpers.test.ts`, `lotChartShared.test.ts`. `registry.test.ts` non è cambiato:
  `DEFAULT_SIGNAL_COLORS` resta il nome pubblico.
- ✅ Oracolo rimasto verde senza modifiche: `chartCoreHelpers.test.ts` (testo `cc('…')` di Growth), test degli helper e
  dei lotti, test con classi (`AssetTable`, `RiskMetricCard`, `KpiDivergingFlowBar`, `TransactionFormModal`).
- ✅ Test e gate nuovi di R, tutti scritti da `test-author` e registrati in `core-unit`, salvo `palettes` in
  `allocation-unit`:
  - W0: `lib/theme/colorAlpha.test.ts`; `src/themeColorMeta.gate.test.ts` (D3, passa a T con T-4);
  - W4: `lib/theme/chartTheme.test.ts`; `src/__tests__/palettes.ts`/`.test.ts`, al posto di `sourcePalettes`;
  - W6–W7: `src/themeComponentTokens.gate.test.ts` (R-3, 18 test), che non legge il Designer Lab né i test;
  - W8: `lib/theme/themeMode.test.ts` (19 test) e `src/themeModeReads.gate.test.ts` (gate D4, 24 test).

## 6. Conflitti e rischi

- **L:** nessun file in comune. R conserva il ridisegno a ogni cambio di classe. Lo scanner di L deve conoscere
  `lib/theme/**` e i `--lf-cmp-*`.
- **G:** nessun file in comune, salvo una correzione di G nel pannello dei lotti (`brokers/lots/**`) da ordinare con W5.
- **Catalogo del runner:** aggiunte additive anche da L e G.
- **Rischi per i pixel:** refusi nei valori; classi non più letterali; cascata in R-3; caricamento del CSS importato; HTML
  dei tooltip; tempi di ridisegno in W8; punti ciechi della gallery (hover, tooltip). Divergenze da non «aggiustare»:
  SemiDonut solo chiaro, Δ dei tooltip uguali nei due temi, scala del treemap invertita.
- **Esito (15/10):** nessuno dei rischi per i pixel si è verificato; il cancello unico A+B+C+D è superato.
- **T** (aperto il 14/10):
  - conflitti solo testuali: righe aggiuntive nel runner e la baseline del cricchetto `themeRoles.baseline.tsv`;
  - la correzione D3 è stata accettata con `--accept` due volte, autorizzata dal coordinatore. La prima perché la
    baseline di T era stata registrata prima di R; la seconda perché `--resolve` l'aveva tolta (R-8).
- **1.3** (A2, spostamenti in `lib/features/`): nessun file di R rinominato; i percorsi delle eccezioni li ha
  aggiornati T.
- **Service worker:** chi cambia `static/offline.html` ritimbra e committa `static/sw.js` (lezione del lotto A, vedi
  «Ingresso in `dev_release2`»).

## 7. Registro di esecuzione

Il ramo R in prima linea, dalla base `b631308`.

| Data | Commit | Cosa |
|---|---|---|
| 14/10 18:05 | `d80b9e0cd` | Lotto A (W0–W2): `refactor(theme): central alpha and tone classes` |
| 14/10 18:06 | `b1fcc3c48` | Merge della base (`c942889e1`) |
| 14/10 20:07 | `75c45d923` | Lotto B (W3–W5): `refactor(theme): chart colours in lib/theme` |
| 14/10 20:07 | `f53d979ef` | Merge della base (`e6d293e41`) |
| 14/10 22:29 | `0b660632f` | Lotto C (W6–W7): `refactor(theme): component style colours in lib/theme` |
| 14/10 22:29 | `85e61abe8` | Merge della base (`aa2adbbf5`) |
| 14/10 22:29 | `74e94dee6` | Piano spostato in `Phase_1/10_colorSystem` |
| 14/10 23:17 | `98731240d` | Lotto D (W8–W9): `refactor(theme): one theme reader, last P8 styles` |
| 14/10 23:35 | `418ea8042` | Merge della base con T-1 (`6ab653dd4`) |
| 15/10 08:45 | `2c8508efb` | Registro del merge con T-1 |
| 15/10 10:26 | `87b7c34b8` | Merge della base con T-2 (`2338aaf79`) |
| 15/10 11:21 | `8fd8e494b` | Merge del target (`6ed99c694`), poi avanzamento veloce di `dev_release2` |
| 15/10 11:21 | `23f6578f3` | `fix(pwa): restamp the service worker` (vedi «Ingresso in `dev_release2`») |
| 15/10 | — | W10: piano, backlog, wiki (da committare a cura del coordinatore) |
