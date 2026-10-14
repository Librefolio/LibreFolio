# Piano R — Fattorizzazione dei colori a parità di aspetto

> Workstream **R** del programma colori 55. Sessione `R - fattorizzazione colori`, worktree `e-alfy-literate-tribble`,
> branch `e-alfy-r-fattorizzazione-colori`. Coordinatore: sessione `aec04834-1532-4d86-9e3f-f942e82aca89`.
> Base: `dev_release2` @ `b631308d5ef5482a8ffdc2878a4459fcf6909827`. Corsia: porta **6154**, dati **`/tmp/librefolio-r2-r`**.
> Piano generale: [`../plan-phase00ColorSystemThemeLab.prompt.md`](../plan-phase00ColorSystemThemeLab.prompt.md), riga R del §5.
> Fonti: [`../analysis/`](../analysis/00_SINTESI.md) (report 01–04). Backlog: sezione «R» di
> [`../../BACKLOG_POST_1.2.md`](../../BACKLOG_POST_1.2.md).

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

### W0 — R-4 helper dell'alfa e refuso della meta
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

### W3–W5 — R-1 colori dei grafici (neutri e guadagno/perdita; palette; serie e formule)
### Cancello B
### W6–W7 — R-3 `<style>` (tabelle; media, file, dialoghi)
### Cancello C
### W8 — osservatori (D4) · W9 — P8 fuori elenco (D5) · W10 — cricchetto (D7), inventario, backlog, wiki, handoff

## 5. Test da adattare (`test-author`)

- Lettori di palette dai sorgenti: `src/__tests__/sourcePalettes.ts`/`.test.ts`, `lib/utils/__tests__/colors.test.ts`,
  `lib/components/charts/__tests__/allocationHierarchy.test.ts`, `…/allocationRings.test.ts`,
  `lib/components/dashboard/AllocationHistoryChart.test.ts`.
- Import spostati: `lineChartHelpers.test.ts`, `lotChartShared.test.ts`, `registry.test.ts`.
- Oracolo che resta verde: `chartCoreHelpers.test.ts` (testo `cc('…')` di Growth), test degli helper e dei lotti, test
  con classi (`AssetTable`, `RiskMetricCard`, `KpiDivergingFlowBar`, `TransactionFormModal`).

## 6. Conflitti e rischi

- **L:** nessun file in comune. R conserva il ridisegno a ogni cambio di classe. Lo scanner di L deve conoscere
  `lib/theme/**` e i `--lf-cmp-*`.
- **G:** nessun file in comune, salvo una correzione di G nel pannello dei lotti (`brokers/lots/**`) da ordinare con W5.
- **Catalogo del runner:** aggiunte additive anche da L e G.
- **Rischi per i pixel:** refusi nei valori; classi non più letterali; cascata in R-3; caricamento del CSS importato; HTML
  dei tooltip; tempi di ridisegno in W8; punti ciechi della gallery (hover, tooltip). Divergenze da non «aggiustare»:
  SemiDonut solo chiaro, Δ dei tooltip uguali nei due temi, scala del treemap invertita.

## 7. Registro di esecuzione
