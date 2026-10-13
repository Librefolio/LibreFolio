# Piano — fase 00, 51: quello che non entra sui telefoni (R-1, R-2, R-4), più i marcatori persi (R-5)

> **Stato**: ✅ chiuso il 2026-10-13, checkpoint al coordinatore (§3, passo 7).
> - **R-1**: da 320 a 390 px, nelle quattro lingue, la pillola Attivi/Inattivi tiene intere le sue etichette (`flex-1 min-w-max` in oneColumn). T2 è passato dal rosso al verde.
> - **R-2**: in compatto l'ultima etichetta degli assi a categoria finisce sul suo tick (`alignMaxLabel: 'right'`). Gli assi del tempo restano come sono: il loro fratello va al coordinatore (§1). T1 è passato dal rosso al verde.
> - **R-4**: la sweep prova anche l'inglese, 24 su 24.
> - **R-5**: un evento dell'ultima settimana o dell'ultimo mese ancora aperti compare sul punto del suo periodo. T4 è passato dal rosso al verde. La riga 🐛 è proposta (passo 7).
>
> - **Mandato**: coordinatore di Release 2 (`c8328a01-…`), lotto 51. **Origine**: i rilievi a margine della verifica a runtime del CHANGELOG (`/tmp/libreFolio_cl_runtime_I.md`, R-1, R-2, R-4; R-3 non si riproduce e resta fuori).
> - **Workstream I**. Ramo `e-alfy-performance-charts-plan`. Base `eb06ab960` (treno 84), worktree pulito, porta 6157 libera.
> - **Corsia**: `--test-port 6157 --data-dir /tmp/librefolio-r2-i-charts`, con `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test …`; un comando alla volta, **1 worker** (V usa i 4 worker sulla sua corsia). Mai le porte 6040 e 6041, mai la galleria, mai `front build` a mano.
> - **Tocca**: `frontend/src/routes/(app)/assets/+page.svelte` (R-1), `frontend/src/lib/components/charts/responsiveXAxis.ts` (R-2), `frontend/src/lib/components/charts/priceChartHelpers.ts` (R-5), i test (`chartCoreHelpers.test.ts`, `priceChartHelpers.test.ts`, `e2e/layout/toolbar-width-sweep.spec.ts`), la descrizione del runner (`scripts/test_runner/_frontend_utility.py`, superficie condivisa: la segnalo al checkpoint) e questo piano.
> - **Non tocca** `PriceChartFull.svelte`: ci lavora T (le date dei tooltip).
> - **La cartella** `51_narrowFitFixes` è una mia proposta: il coordinatore ha dato il numero del lotto, non il nome.

## 0. Autorizzazione (2026-10-13)

Il coordinatore: «**Lotto 51, nella 1.2** (codice di prodotto piccolo, corsia 6157):

1. **R-1, la pillola Attivi/Inattivi della pagina Assets**: è nata con `3e5313d3e`, quindi va curata prima del rilascio e non vuole una riga nel CHANGELOG. In spagnolo a 320–330 px il testo si perde.
   - La cura: `min-w-0 truncate` più un `title` sui due bottoni, oppure quella che serve perché l'etichetta resti leggibile.
   - Il test-author la prova rossa prima della cura, per esempio con `scrollWidth ≤ clientWidth` sul testo della pillola a 320 px in es.
2. **R-2, l'ultima etichetta dell'asse x tagliata sui telefoni** («Oct 1…» a 360/390): `responsiveXAxis.ts:160-162`, con `alignMaxLabel: 'right'` o l'equivalente.
   - Verifica da quale commit nasce: se il difetto c'era già nella `v1.1.0`, dimmelo, perché serve una riga 🐛.
   - Un test unitario sull'opzione dell'asse.
3. **R-4, la sweep `toolbar-width-sweep.spec.ts:124`**: aggiungi `en` alle lingue, perché oggi prova solo fr, it ed es.

**Come**: analisi brevissima nel tuo piano, poi parti. Per le prove, spec singole a 1 worker. Checkpoint FROZEN col manifest. Gli scatti della pagina Assets e dei grafici cambieranno: la galleria finale di M arriva dopo i lotti di V, T e tuo. R-3: niente, non si riproduce.»

**Aggiunta del coordinatore, lo stesso giorno (in sintesi): R-5.** A risoluzione settimanale o mensile, il marcatore di un evento che cade nell'**ultimo periodo parziale** sparisce. Lo ha confermato V a runtime (`/tmp/libreFolio_v_events_probe.md`, 8 scatti). C'è dalla `v1.0.0` (`222a77c5e`), quindi vuole una riga 🐛, da proporre al checkpoint. La cura va negli helper, non in `PriceChartFull.svelte`; prima un test rosso sugli helper, con un periodo parziale. Da guardare anche la pagina FX (`fx/[pair]/+page.svelte:1459`), che passa `eventMarkers`.

## 1. Analisi

### R-1 — la pillola Attivi/Inattivi (`assets/+page.svelte:1287,1331`)

- **La causa.** In oneColumn (barra < 400 px) Cerca e la pillola condividono la riga 1 con la stessa classe, `flex-1 min-w-0` (`:1287`). La pillola ha `overflow-hidden` per gli angoli arrotondati, quindi il suo minimo è 0; i due bottoni sono `whitespace-nowrap` e non scendono sotto il loro testo. A metà riga non ci stanno, e la pillola li taglia.
- **Le misure** (verifica a runtime, barra della pagina Assets, sporgenza del bottone oltre la pillola): es 320 → 20,7 px, 330 → 15,7, 340 → 10,7, 342 → 9,7; en 320 → 7,4, 330 → 2,4; fr 320 → 2,0; it mai. Le etichette: «Activos/Inactivos», «Active/Inactive», «Actifs/Inactifs», «Attivi/Inattivi».
- **La provenienza**: `3e5313d3e`, dopo `v1.1.0`. Niente riga nel CHANGELOG.
- **La cura**: una classe propria per la pillola in oneColumn, `flex-1 min-w-max` al posto di `flex-1 min-w-0`.
  - Se le etichette stanno nella metà riga, le due metà restano uguali, come oggi.
  - Se non ci stanno, la pillola prende la larghezza del suo contenuto e Cerca cede il resto (circa 96 px su una barra di 254 px, in es).
  - Il testo resta intero: niente troncamento e niente `title`. Gli altri layout non cambiano.
- **Scartata la proposta `truncate` + `title`.** Il difetto c'è solo sui telefoni, dove il `title` non si vede; e «Inact…» accanto ad «Act…» non si legge. Scartato anche il padding ridotto, che regge solo finché nessuna lingua si allunga.
- **Il commento** sopra la pillola (`:1325-1330`, «fixed w-44 … so the pill splits evenly») va aggiornato: in oneColumn la colonna con la riga 2 regge solo finché le etichette ci stanno.

### R-2 — l'ultima etichetta dell'asse x (`responsiveXAxis.ts:21-29,154-166`)

- **La causa.** In modalità compatta (larghezza utile < 480 px, o meno di 24 px per punto) la politica forza `showMinLabel` e `showMaxLabel`. ECharts centra ogni etichetta sul suo tick: quella dell'ultimo tick sporge di mezza larghezza oltre il bordo, e sui telefoni il margine destro non basta. Lo scatto: `/tmp/libreFolio_i_rt_shots/228_tooltip_360_viewport.png`, PriceChartFull a 360 px, «Oct 13» letto «Oct 1».
- **La provenienza**: introdotto nella 1.2. `showMaxLabel` compatto entra con `2d22130bd` (17/09); poi `4c05c1d85`, `8682f0bbd` e `ff7c96fd0`. Tutti vengono dopo il tag `v1.1.0` (`837a8f2c7`), e in `v1.1.0` `frontend/src` non ha nessun `showMaxLabel`. **Niente riga 🐛.**
- **La cura** (prima versione, **superata**: vedi il fuori pista qui sotto): `alignMinLabel: 'left'` e `alignMaxLabel: 'right'` nell'`axisLabel` compatto, e solo lì, più il tipo `ResponsiveXAxisPolicy.axisLabel`.
  - ECharts 6.0.0 li applica alla prima e all'ultima etichetta della lista (`AxisBuilder.js:874-875`); i tipi li espongono (`shared.d.ts:2734-2735`).
  - In compatto quelle due etichette sono per costruzione gli estremi dell'asse, perché `showMinLabel` e `showMaxLabel` le includono, anche dentro una finestra di zoom.
  - Nel percorso largo no: l'ultima etichetta può cadere a metà asse, e allinearla a destra la staccherebbe dal suo tick.
- **I consumatori non cambiano.** GrowthChart, LineChart, PriceChartFull, CandlestickChart, AllocationHistoryChart e i grafici dei lotti (via `buildLotXAxisPolicy`) stendono `policy.axisLabel`.
  - Il passaggio da compatto a largo sostituisce l'asse intero, quindi le due chiavi nuove spariscono come `showMinLabel` e `showMaxLabel`.
  - L'asse a scaglioni di GrowthChart non usa la politica.
- **Gli effetti da sapere.**
  - Spostata verso l'interno, un'etichetta di bordo può coprire la vicina: `fixMinMaxLabelShow` di ECharts nasconde allora quella interna, non quella di bordo. Va bene.
  - Sulle Candele (`boundaryGap: true`) le etichette di bordo si allineano al centro della prima e dell'ultima candela: un poco asimmetriche, ma intere.
- **Nessun E2E legge l'allineamento**: `dashboard.spec.ts:905` legge solo il formatter via `getOption()`.

> **⚠️ Fuori pista (2026-10-13) — la simulazione cambia la cura: solo assi a categoria, solo `alignMaxLabel`.**
>
> - **Il dubbio.** Rileggendo T1 è emerso un rischio: un'etichetta di bordo spostata verso l'interno può essere lei quella nascosta. Ho misurato prima di toccare il prodotto, con una simulazione Vitest SSR temporanea (`zz_lot51_r2_sim.test.ts`, non tracciata, cancellata prima del checkpoint): 4 configurazioni (PriceChartFull e LineChart a categoria; Growth a tempo con `containLabel`; lotti a tempo senza), 4 lingue, larghezze 260–800 px, intervalli da 7 a 1825 giorni. Esiti in `/tmp/libreFolio_i_l51_r2sim_summary.json` e `…_rows.tsv`.
> - **Perché sul tempo non va.** ECharts 6 ordina le etichette di un asse del tempo per livello del tick (`z2 = 10 + time.level`, `AxisBuilder.js:877`) prima di `hideOverlap` (`labelLayoutHelper.js:389-434`), e `fixMinMaxLabelShow` (`:647-707`) nasconde solo la vicina immediata. Un'etichetta di bordo tirata dentro copre il tick del mese o dell'anno accanto, che vince: sparisce lei. Quindi la frase sopra, «nasconde quella interna, non quella di bordo», vale solo per gli assi a categoria, dove le etichette hanno tutte la stessa priorità.
> - **I numeri** (casi compatti):
>   - categoria, tipo PriceChartFull: ultima tagliata 235 → 0, nascosta 0 → 0;
>   - categoria, tipo LineChart: 163 → 0, nascosta 0 → 0;
>   - tempo, tipo Growth: ultima tagliata 240 → 0, ma nascosta 60 → 181; e 26 dei 48 casi in cui l'ultima etichetta era intera la perdono;
>   - tempo, tipo lotti (senza `containLabel`): mai tagliata già sulla base; l'allineamento è solo una regressione (intera 304 → 228, nascosta 44 → 120).
>   - La prima etichetta **non è mai tagliata** sulla base, in nessuna configurazione: sporge al massimo nella colonna delle etichette dell'asse y, a sinistra, che resta dentro il grafico (motivazione corretta al passo 4). `alignMinLabel` serve solo a nascondere più etichette (sul tempo 34 → 81).
> - **La cura nuova**: in `buildResponsiveXAxisPolicy`, ramo compatto, `alignMaxLabel: 'right'` **solo se `axisType === 'category'`**; niente `alignMinLabel`; più la chiave opzionale nel tipo. Cambiano LineChart, PriceChartFull e CandlestickChart; gli assi del tempo (Growth, AllocationHistory, lotti) restano come sono. Il passaggio da compatto a largo rifà l'opzione intera (`setOption(option, true)` in tutti e tre), quindi la chiave non resta.
> - **Il fratello sul tempo, da segnalare al coordinatore.** Growth, AllocationHistory e LotComparison (tempo, `containLabel: true`) tagliano anche loro l'ultima etichetta sui telefoni (simulazione, tipo Growth sulla base: da 260 a 440 px l'ultima etichetta è tagliata in 40–54 casi su 60 per larghezza). È nato nella 1.2 anche lui, col `showMaxLabel` forzato. La causa: il bundle intero di ECharts registra `LegacyGridContainLabel` (`index.js:261`), che con `containLabel: true` riserva solo lo spazio verticale. Due strade, entrambe sui consumatori e coi loro test e controlli visivi: (a) `outerBoundsMode: 'same'` + `outerBoundsContain: 'axisLabel'` al posto di `containLabel` (ultima tagliata 240 → 20, ma più prime nascoste, 34 → 64); (b) `alignMaxLabel` su richiesta del consumatore (niente tagli, ma metà nascoste). Fuori da questo lotto: lo decide il coordinatore.

### R-4 — l'inglese nella sweep (`toolbar-width-sweep.spec.ts:124`)

- `LANGUAGES` prova fr, it ed es. L'intestazione (`:12-15`) motiva l'esclusione dell'inglese: «English dominated everywhere», dalla calibrazione del 30/09.
- **La verifica a runtime la smentisce**: sulla pillola di R-1 l'inglese sporge di 7,4 px a 320 px, mentre l'italiano non sporge mai. Si aggiunge `en`, e l'intestazione dice perché.
- **La sweep da sola non vede R-1**, per scelta: salta il contenuto dei contenitori che tagliano. Per questo R-1 ha un test suo (§2).

### R-5 — i marcatori persi nell'ultimo periodo parziale (`priceChartHelpers.ts:502-560`)

- **Il meccanismo**, in tre pezzi che non si parlano:
  - `bucketEventMarkers` (`timeSeriesAggregation.ts:544-563`) mette ogni evento sotto la **fine teorica** del suo periodo (`bucketEnd`: la domenica, l'ultimo del mese);
  - `aggregateLineSeries` (`:168-182`) data ogni punto aggregato col **suo ultimo dato** (`withBucketMeta`, `:125`), e tiene la fine teorica solo nei metadati;
  - `buildEventScatterGroups` cerca la fine teorica fra le date dei punti (`dateIndexMap.get(bucketDate)`, `:544-547`), non la trova e salta l'evento (`continue`).
  - Nei periodi pieni le due date coincidono. Nell'ultimo periodo, ancora aperto (oggi è mercoledì, il mese non è finito), il punto sta all'ultimo dato e l'evento sparisce.
- **Dove si vede.**
  - La pagina dell'asset riempie i fine settimana e chiede gli eventi per lo stesso intervallo (`assets/[id]/+page.svelte:1747-1772`).
  - Il convertitore FX restituisce tutti i giorni di calendario (`backend/app/api/v1/fx.py:559-575`); la pagina della coppia passa solo gli eventi del confronto (`fx/[pair]/+page.svelte:434-453`).
  - Quindi nei periodi interni la fine teorica c'è sempre fra i dati: resta solo la forma stretta, l'ultimo periodo parziale. Il primo periodo parziale non perde niente, perché il suo punto sta comunque alla fine teorica.
  - Le Candele non ricevono `eventMarkers` (nota di V).
- **La provenienza**: `222a77c5e`, già nella `v1.0.0`. **Vuole una riga 🐛.**
- **La cura**, solo in `buildEventScatterGroups`, ramo non giornaliero:
  - una mappa `fine teorica → data del punto`, costruita dai punti della linea risolta (`p.bucketEnd` se c'è, altrimenti `mapDateToBucket(p.date, res).bucketEnd`, già importato);
  - la data del marcatore diventa quella del punto (`renderDate`, con ripiego sulla fine teorica), e da lì valgono indice, valore y e `bucketInfo`;
  - `bucketEventMarkers` non cambia, e nemmeno `PriceChartFull.svelte`.
- **La scelta di prodotto**: un evento nel periodo aperto ma **dopo** l'ultimo dato (per esempio un dividendo annunciato per venerdì, visto mercoledì) compare sulla barra di quel periodo, come accade già al primo periodo parziale. Un evento in un periodo che non ha nessun punto, invece, resta escluso come oggi.
- **Un fratello, non in questo lotto**: nel periodo parziale il tooltip principale dice «valore al» con la fine teorica (`PriceChartFull.svelte:348-351`). Il file è di T, che lavora sulle date dei tooltip: lo segnalo al checkpoint.

## 2. I test (via `test-author`)

- **T1, R-2** (Vitest, `chartCoreHelpers.test.ts`, selettore `front-asset asset-unit`). **Rivisto dopo la simulazione** (§1, fuori pista): la prima stesura chiedeva le due chiavi su entrambi gli assi.
  - (a) la politica compatta **a categoria** ha `alignMaxLabel: 'right'` e non ha `alignMinLabel`; quella compatta **del tempo** non ha nessuna delle due;
  - (b) la politica larga non ha nessuna delle due;
  - (c) il comportamento: l'SVG di ECharts SSR di un asse compatto a categoria, a 360 px, ha la prima etichetta con `text-anchor="middle"` e l'ultima con `"end"`, e i bordi del testo stanno dentro i 360 px;
  - (d) i test della ricostruzione da compatto a largo di Growth (asse del tempo) tornano come sulla base.
  - Rossi sulla base: (a) sul ramo a categoria, e (c) sull'ancora e sul bordo dell'ultima etichetta.
- **T2, R-1** (Playwright): a larghezze oneColumn in en, it, fr ed es:
  - ogni bottone della pillola sta dentro la pillola;
  - né la pillola né i bottoni tagliano il loro contenuto (`scrollWidth ≤ clientWidth`);
  - la riga 1 sta nella barra.
  - Rosso sulla base: es, en e fr a 320 px.
- **T3, R-4**: `en` in `LANGUAGES` e l'intestazione corretta.
- **T4, R-5** (Vitest, `priceChartHelpers.test.ts`, `describe('buildEventScatterGroups')`, selettore `front-utility core-unit`). Il contesto viene dall'aggregazione vera (`aggregateLineSeries`, `downsampleRenderedSignal`) su una serie di giorni di calendario, come nelle due pagine. **Le quattro prove consegnate** (la prima stesura ne prevedeva tre rosse più una guardia: il test-author ha aggiunto il caso del confronto e ha unito la guardia ai casi rossi):
  - (a) `:1303`, settimanale: un evento dell'ultima settimana, parziale, sta sul punto del suo ultimo dato;
  - (b) `:1313`, mensile: un evento del mese aperto sta sulla sua barra, accanto a un mese pieno che non cambia;
  - (c) `:1328`, un evento di confronto della settimana aperta sta sulla sua linea sovrapposta, alla data della barra;
  - (d) `:1347`, un evento datato dopo l'ultimo dato sta sulla barra della sua settimana aperta, mentre uno di una settimana successiva, senza punti, resta fuori.
  - Rosse sulla base: tutte e quattro, con il messaggio «vanished».

## 3. Passi

1. ✅ 2026-10-13 — Base, provenienza di R-2, analisi (§1), questo piano.
2. ✅ 2026-10-13 — test-author: T1, T2, T3 e T4 scritti e rivisti.
   > **Note implementazione**: la prima consegna (2 file, +302/−8) è passata da prettier e svelte-check (0 errori). `tsc -p tsconfig.e2e.json` dà 2 errori già presenti in file non toccati (`e2e/onboarding-tour.spec.ts:863`, `src/lib/types/files.ts:9`). ESLint non è installato nel worktree.
   >
   > **La seconda consegna** (dopo la simulazione del §1): T1 riscritto per la cura nuova, cioè solo categoria e solo `alignMaxLabel`, più la prova geometrica sull'SVG di ECharts (la griglia è quella piena di LineChart, `LineChart.svelte:599-605`, con le etichette y). T4 aggiunto (§2). Vitest diretto sulla base: 7 rossi (3 di T1, 4 di T4), 315 verdi; prettier pulito (`/tmp/libreFolio_lot51_i_vitest_r2r5.log`). I `describe` della ricostruzione di Growth sono identici alla base. Ho riletto i due diff (`/tmp/libreFolio_i_l51_t1_diff.log`, `…_t4_diff.log`).
3. ✅ 2026-10-13 — I rossi sulla base, uno alla volta, 1 worker.
   > **T2, rosso sulla base** (2026-10-13): `… --workers 1 front-utility toolbar-width-sweep 'assets lifecycle pill keeps both labels whole'` → 3 rossi, 1 verde in 3 min 46 s, compresa la build (`/tmp/libreFolio_i_l51_t2_red.log`).
   >
   > | lingua | larghezze rosse (sporgenza del bottone Inattivi oltre la pillola) |
   > |---|---|
   > | en | 320 (8,4 px), 330 (3,4) |
   > | fr | 320 (3,0) |
   > | es | 320 (21,7), 330 (16,7), 340 (11,7), 360 (1,7) |
   > | it | nessuna, verde |
   >
   > Le misure superano di 1 px quelle della verifica a runtime: il test misura dal bordo dove la pillola taglia, la sonda dal suo bordo esterno. Lo spagnolo è rosso anche a 360 px, il caso che la sonda dava al limite (0,7 px).
   >
   > **⚠️ Fuori pista**: `--workers 1` va prima della categoria (`dev.py test … --workers 1 front-utility …`). Messo in coda ai filtri, il parser lo rifiuta (`unrecognized arguments`, exit 2, prima di toccare porta e dati).
   >
   > **T4, rosso sulla base** (2026-10-13): `… --workers 1 front-utility core-unit 'R-5, lot 51'` → 4 rossi su 4, tutti «the marker of the open week/month vanished» (`/tmp/libreFolio_i_l51_t4_red.log`). Il file della simulazione non entra: la lista di core-unit è esplicita (126 file).
   >
   > **T1, rosso sulla base**: `… --workers 1 front-asset asset-unit` → 3 rossi, 764 verdi, 20 file (`/tmp/libreFolio_i_l51_t1_red.log`). I tre: la forma esatta della politica a categoria (piano 47, C3), l'allineamento (`toMatchObject`), la prova sull'SVG («Oct 13» con ancora `middle` invece di `end`, bordo destro a 362,56 px su 360). Il selettore non ha filtro sul nome (`test_names=False`).
4. ✅ 2026-10-13 — Le cure di R-1, R-2 e R-5.
   > **R-1 fatta** (2026-10-13): `assets/+page.svelte`, un `{@const pillWidthClass}` accanto a `filterWidthClass`: `'flex-1 min-w-max'` in oneColumn, altrimenti la classe di prima (`'w-44 min-w-[160px]'`). La pillola lo usa al posto di `filterWidthClass`; il commento sopra la pillola dice ora che sui telefoni la colonna con la riga 2 regge solo finché le etichette stanno nella metà riga.
   >
   > **T2 verde**: lo stesso comando del rosso dà 4 su 4 in 2 min 10 s (`/tmp/libreFolio_i_l51_t2_green.log`). La build servita (05:51:06) è posteriore alla modifica (05:49:21) e contiene `min-w-max`, sia nel nodo della pagina sia nel CSS: il messaggio «Frontend build is up to date» del runner viene dopo la build rifatta all'avvio del backend condiviso.
   >
   > **R-2 fatta**: `responsiveXAxis.ts`, la chiave opzionale `alignMaxLabel?: 'right'` nel tipo `ResponsiveXAxisPolicy.axisLabel`, e nel ramo compatto `...(axisType === 'category' ? {alignMaxLabel: 'right'} : {})` dopo `interval`, con il perché in commento. Nessun consumatore cambia: LineChart, PriceChartFull e CandlestickChart stendono già `policy.axisLabel`, e gli assi del tempo restano come sono.
   >
   > **R-5 fatta**: `priceChartHelpers.ts`, `buildEventScatterGroups`. Nel ramo non giornaliero una mappa `renderDateByBucketEnd`, costruita dai punti della linea risolta (`point.bucketEnd ?? mapDateToBucket(point.date, res).bucketEnd` → `point.date`); il marcatore usa `renderDate` (con ripiego sulla fine teorica) per indice, y, valore e `bucketInfo`. Docstring aggiornata. `EventScatterContext`, `bucketEventMarkers` e `PriceChartFull.svelte` non cambiano.
   >
   > **⚠️ Fuori pista — una motivazione corretta.** Il commento della cura R-2 e due commenti di T1 dicevano che la prima etichetta non si taglia perché «sta mezza banda dentro la griglia». Non regge: in compatto i punti sono tanti, e mezza banda vale pochi pixel. Il motivo vero è la colonna delle etichette dell'asse y a sinistra (`buildPriceYAxis` la mette `position: 'left'`, `chartCoreHelpers.ts:79`; LineChart pure, nel percorso pieno), che la griglia con `containLabel` tiene dentro il grafico. Ho corretto i tre commenti: solo commenti, nessuna asserzione toccata.
5. ✅ 2026-10-13 — I verdi:
   - i selettori del §5, uno alla volta;
   - `front check`;
   - prettier ed eslint sui file toccati.
   > **La sweep intera, con R-1** (2026-10-13): `… --workers 1 front-utility toolbar-width-sweep` → 24 su 24 in 6 min 49 s, exit 0 (`/tmp/libreFolio_i_l51_sweep_full.log`): le 20 sweep, cioè cinque pagine per quattro lingue con l'inglese di T3, più le 4 pillole di T2. Le cure di R-2 e R-5 toccano solo il disegno dentro i grafici, non le barre: questa prova vale anche per la revisione finale.
   >
   > **`front-asset asset-list`**: 28 su 28 in 3 min 45 s (`/tmp/libreFolio_i_l51_asset_list.log`), compreso il test della pillola (`asset-list.spec.ts:390`). In coda il runner stampa «Shared backend ignored SIGTERM»: è C-49, già nel backlog.
   >
   > **I verdi di T1 e T4, dopo le cure di R-2 e R-5**:
   > - Vitest diretto sui due file: 322 su 322 (`/tmp/libreFolio_i_l51_direct_green.log`);
   > - `… --workers 1 front-asset asset-unit` → 767 su 767, 20 file (`/tmp/libreFolio_i_l51_t1_green.log`);
   > - `… --workers 1 front-utility core-unit`, senza filtro, così passano anche i test degli eventi che c'erano già → 4103 su 4103, 126 file (`/tmp/libreFolio_i_l51_t4_green.log`);
   > - lo stesso col filtro `'R-5, lot 51'` → 4 verdi, 4099 saltati (`…_t4_green_filtered.log`).
   > - Nessun altro test legge la forma dell'asse compatto: `PerformanceChart.test.ts:839` guarda solo `showMinLabel`/`showMaxLabel` del suo asse, che non usa la politica.
   >
   > **I controlli statici, sulla revisione finale** (dopo la correzione dei commenti del passo 4):
   > - `… dev.py front check` → 0 errori, 0 avvisi (`/tmp/libreFolio_i_l51_front_check.log`). Il suo hook rifà il catalogo i18n generato: `git status` non mostra altri file;
   > - prettier `--check` sui 6 file del frontend toccati: pulito (`/tmp/libreFolio_i_l51_prettier.log`);
   > - Vitest diretto sui due file dei grafici, rilanciato dopo i commenti: 322 su 322 (`/tmp/libreFolio_i_l51_direct_green2.log`);
   > - `git diff --check` pulito; ruff e black su `_frontend_utility.py` puliti;
   > - ESLint non c'è nel worktree (passo 2): non l'ho lanciato;
   > - cancellato il file della simulazione di R-2 (`zz_lot51_r2_sim.test.ts`, mai tracciato).
6. ✅ 2026-10-13 — La descrizione del runner (`toolbar-width-sweep`: quattro lingue, più il test di T2 se ci va). La documentazione e la wiki solo se sono vecchie.
   > **Note implementazione**:
   > - **Il runner** (`scripts/test_runner/_frontend_utility.py`, superficie condivisa): la docstring e la descrizione di `toolbar-width-sweep` dicono quattro lingue e il test della pillola; la frase di `core-unit` cita i marcatori degli eventi nei periodi parziali.
   > - **La documentazione** (docs-writer): in `mkdocs_src/docs/developer/frontend/components/charts.md` la sezione «Responsive Date Axis» descriveva ancora `formatCompactXAxisDate()`, tolta nel lotto 47. Ora segue il codice: la politica compatta, `alignMaxLabel` solo sugli assi a categoria e il perché, i due formatter, i consumatori. La pagina è solo inglese: nessuna traduzione, niente translate-stamp. `… dev.py mkdocs build` (strict) → exit 0, 0 avvisi (`/tmp/libreFolio_i_l51_docs_build.log`); `… dev.py mkdocs check-links` → 95 validi, 0 rotti (`…_docs_links.log`). Le pagine utente non cambiano: nessuna descrive dove stanno i marcatori o la pillola sui telefoni.
   > - **La wiki**: `LibreFolio_devWiki/wiki/concepts/responsive-4mode-layout.md` diceva FR/IT/ES nella sweep e, per i filtri di Assets in `oneColumn`, solo `flex-1 min-w-0`. Ora dice EN/FR/IT/ES e ha una sezione breve sulla pillola (difetto, cura, scelta scartata, test). `index.md` e `log.md` non li tocco: sono registri condivisi, e la voce di `log.md` la propongo nel checkpoint. `python3 LibreFolio_devWiki/check_source_paths.py` → 5 path inesistenti, tutti in altre pagine e già presenti (le cartelle di coverage generate, e una cartella di prove dell'AI Export); nessuno nella pagina toccata (`/tmp/libreFolio_i_l51_wiki_paths.log`). Il grafo non l'ho aggiornato: `graphify-out` manca nel worktree, e la skill punta al checkout principale.
   >
   > **⚠️ Fuori pista**: le pagine dell'asse del lotto 47 nella wiki (`problems/line-chart-axes-lost-the-day.md`, `sources/phase00-chart-axis-day-labels-2026-10.md`) raccontano la storia, e restano giuste: non le tocco.
7. ✅ 2026-10-13 — Il checkpoint: manifest, messaggi, porta libera, FROZEN.
   > **Note implementazione**:
   > - **Cinque commit proposti**, divisi per file, quindi senza stadi intermedi:
   >   - C1 `fix(assets): keep pill labels whole on phones`: `assets/+page.svelte`, `toolbar-width-sweep.spec.ts` (R-1 con T2; R-4 con T3);
   >   - C2 `fix(charts): keep the last date label on screen`: `responsiveXAxis.ts`, `chartCoreHelpers.test.ts` (R-2 con T1);
   >   - C3 `fix(charts): keep event markers in partial buckets`: `priceChartHelpers.ts`, `priceChartHelpers.test.ts` (R-5 con T4);
   >   - C4 `docs: realign chart axis docs, runner and wiki`: `charts.md`, `_frontend_utility.py`, `responsive-4mode-layout.md`;
   >   - C5 `docs(journal): plan 51, narrow-fit fixes`: questo piano.
   > - **I controlli**: messaggi in ASCII, soggetti entro 50 caratteri, righe entro 72; il manifest ha il blob di ogni file. La privacy è pulita: nei file ci sono solo misure in px e date. `git diff --check` è pulito, la porta 6157 è libera (`lsof` vuoto), niente in stage.
   > - **Il CHANGELOG**: una sola riga 🐛, per R-5, nel blocco `#### 📈 Charts` di 🐛 Fixed: «At weekly or monthly resolution, events in a last week or month that is not over yet no longer disappear from the asset and FX charts: their markers sit on that period's point like the others.» R-1 e R-2 sono nati nella 1.2, R-4 tocca solo i test: per loro nessuna riga.
   > - **Da decidere al coordinatore**: il fratello sul tempo (§1, R-2), con le strade (a) e (b) e i loro numeri.
   > - **Le segnalazioni**:
   >   - a T: il tooltip del periodo parziale (`PriceChartFull.svelte:348-351`);
   >   - per la wiki:
   >     - la regola di ECharts (le etichette del tempo ordinate per livello prima di `hideOverlap`);
   >     - una pagina problema per R-5;
   >     - la voce di `log.md`;
   >   - a M: gli scatti della galleria che cambiano (la pagina Assets sui telefoni, i grafici a categoria in compatto).

## 4. Definizione di fatto

- **R-1**: da 320 a 390 px, nelle quattro lingue, le due etichette della pillola sono intere e Cerca resta usabile; gli altri layout non cambiano (la sweep è verde).
- **R-2**: in compatto l'ultima etichetta degli assi a categoria sta dentro il grafico, allineata a destra; gli assi del tempo e il percorso largo non cambiano; T1 passa dal rosso al verde.
- **R-4**: la sweep prova anche l'inglese, ed è verde.
- **R-5**: a risoluzione settimanale e mensile, un evento dell'ultimo periodo parziale compare sulla sua barra; T4 passa dal rosso al verde, e i test degli eventi che ci sono già restano verdi.
- **Il CHANGELOG**: una sola riga nuova, 🐛 per R-5 (proposta al checkpoint). R-1 e R-2 sono nati nella 1.2, R-4 tocca solo i test.
- `front check` a 0 errori, prettier pulito, `git diff --check` pulito, porta 6157 libera.

## 5. I selettori

- `front-asset asset-unit`: T1, e i test della politica che ci sono già.
- `front-utility core-unit`: T4, e i test degli helper dei prezzi che ci sono già.
- `front-utility toolbar-width-sweep`: T3, e T2 se vive in quel file; T2 da solo col filtro sul nome.
- `front-asset asset-list`: la regressione sul test della pillola (`asset-list.spec.ts:390`).
