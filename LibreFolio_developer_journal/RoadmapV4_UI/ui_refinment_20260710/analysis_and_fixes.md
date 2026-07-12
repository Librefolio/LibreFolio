# UI Refinement — Feedback nightly 2026-07-10

Fonte: feedback raccolto dall'utente dopo alcuni giorni di test della build nightly
self-hosted. Sei aree di feedback, analizzate singolarmente e implementate.

## 1. KPI Card 1 (Period P&L) — delta % tra parentesi

**File**: `frontend/src/lib/components/dashboard/KpiSection.svelte`

La card mostrava già il delta assoluto giorno-prima (`data-testid="kpi-pnl-delta-day"`).
Aggiunta la percentuale tra parentesi sulla stessa riga.

**Formula implementata** (confermata con l'utente):
```
pnlDeltaDay        = lastHistoryPoint.total_pnl − prevHistoryPoint.total_pnl
periodPnlYesterday = prevHistoryPoint.total_pnl − firstHistoryPoint.total_pnl   (periodo calcolato a ieri)
pctDelta           = pnlDeltaDay / periodPnlYesterday × 100
```
Guard: percentuale omessa (solo assoluto mostrato) se `periodPnlYesterday` è nullo/assente
o `|periodPnlYesterday| < 0.01`.

## 2. KPI Card 3 (Net Worth) — P&L totale assoluto + delta %

**File**: `frontend/src/lib/components/dashboard/KpiSection.svelte`

Sostituita la riga `kpi-nav-delta-day` (delta NAV) con una nuova riga
`kpi-total-pnl-delta`: P&L totale assoluto (`summary.total_gain_loss`) + delta %
tra parentesi.

**Formula implementata**:
```
totalPnlAmt = summary.total_gain_loss.amount
pctDelta    = pnlDeltaDay / prevHistoryPoint.total_pnl × 100   (stesso pnlDeltaDay di sopra)
```
Guard sullo stesso principio (denominatore ~0 → niente percentuale). Variabile
`navDeltaDay` (ormai inutilizzata) rimossa; nessun test e2e referenziava il vecchio
testid.

## 3. Toolbox troppo in basso — layout instabile al primo render

**Root cause reale**: non "scroll Y" ma dimensioni ECharts stale al primissimo render
mobile, mentre il layout circostante (KPI cards, font emoji) si assesta ancora. Il fix
esisteva solo in `GrowthChart.svelte`. Estratto in helper condiviso
`scheduleFirstRenderStabilityFix()` in `frontend/src/lib/components/charts/echartsTooltipHelpers.ts`
(con un miglioramento aggiuntivo: usa anche `document.fonts.ready`, non solo
`window.load`, per un segnale più preciso sul FOUT dei font).

Applicato a: `AllocationHistoryChart.svelte` (priorità — istogrammi allocazione),
`PerformanceChart.svelte`, `ExposureTreemap.svelte`, `GeographyMap.svelte`,
`AllocationPieChart.svelte`, `SemiDonutChart.svelte`, `PriceChartFull.svelte`,
`LineChart.svelte`, `CandlestickChart.svelte`, e `GrowthChart.svelte` (refactored per
usare lo stesso helper condiviso).

**Verifica**: `./dev.py front check` → 0 errori. Verifica visiva del posizionamento
tooltip al cold-reload mobile lasciata a verifica manuale dell'utente.

## 4. Grafici a torta — tooltip sotto al dito invece che sopra

**File**: `AllocationPieChart.svelte`, `SemiDonutChart.svelte`

Nessuno dei due impostava `tooltip.position` (default ECharts = sotto/a lato del
cursore). Agganciata `tooltipPositionAboveFinger` (già presente ma inutilizzata in
`echartsTooltipHelpers.ts`) a entrambi.

## 5. Treemap holding mobile — pan non funzionante

**File**: `frontend/src/lib/components/dashboard/ExposureTreemap.svelte`

`roam: isTouchDevice ? 'scale' : true` → `roam: true` incondizionato. La guard
esistente (`echartsTreemapZoomGuard.ts`) gestiva già sia zoom che pan, quindi il
clamping funziona senza modifiche a quel file.

**⚠️ Rischio aperto, non verificabile da CLI**: ECharts/zrender potrebbe catturare il
gesto touchmove sull'intera area del grafico anche quando il pan risultante è
geometricamente un no-op (zoom 1:1, nulla da pannare) — bloccando lo scroll pagina
anche quando l'utente non ha zoomato. **Verifica manuale richiesta**: su device touch
reale o Chrome DevTools con emulazione touch — (a) zoom-in poi drag → deve pannare;
(b) a zoom default 1:1, drag verticale sul grafico → la pagina deve continuare a
scrollare. Se (b) fallisce, serve un secondo giro con guardia gestuale custom
(pointer/touch handling con `preventDefault` condizionale) — non promesso come già
risolto in questo giro.

## 6. AI Export — clipboard falliva

**File**: `frontend/src/lib/features/ai-export/aiExportClipboard.ts`

Root cause: `navigator.clipboard` è `undefined` in contesti non sicuri (HTTP semplice,
non HTTPS/localhost) — tipico di self-hosted via LAN. Applicato lo stesso fallback già
presente in `FileGrid.svelte` (`textarea` + `document.execCommand('copy')` quando
`navigator.clipboard`/`isSecureContext` non disponibili).

**Non toccato, segnalato come rumore non correlato**: il 401 su `/api/v1/auth/me` e gli
errori "message channel closed" nel dump console originale — sessione JWT scaduta dopo
giorni di test + artefatti di un'estensione Chrome, nessuna relazione con l'export
(verificato: `aiExportBuilder.ts` non fa chiamate API proprie).

## 7. Holdings + Performance — colonna "Δ P&L vs giorno prima"

**Backend**: `PortfolioHolding` (schema) + `portfolio_service.py` — nuovi campi
`gain_loss_change_1d` e `gain_loss_change_1d_percent`, calcolati riusando il prezzo di
ieri già fetchato per `price_change_1d` (nessuna nuova query):
```
gain_loss_change_1d         = (current_price − prev_price_base) × quantity
gain_loss_yesterday         = gain_loss − gain_loss_change_1d
gain_loss_change_1d_percent = gain_loss_change_1d / |gain_loss_yesterday| × 100   (None se |gain_loss_yesterday| ≤ 0.01)
```
`./dev.py api sync` eseguito per rigenerare il client TS.

**Frontend Holdings** (`ExposureTable.svelte`): nuova colonna diretta con i 2 campi.

**Frontend Performance** (`ContributionTable.svelte`): nessun cambio all'endpoint
`AssetPeriodContribution` — join client-side contro `summary.holdings` (già disponibile
in `PositionsPanel.svelte`), chiave `${asset_id}-${broker_id}`. Le posizioni chiuse
(assenti dallo snapshot holdings) mostrano "—" automaticamente.

**Test**: estesa `test_holding_price_change_1d` in
`backend/test_scripts/test_services/test_financial/test_portfolio_service.py` con le
nuove asserzioni (importo di acquisto nel fixture adattato da -500 a -450 per rendere
il P&L di ieri non-zero e quindi la percentuale verificabile — l'asserzione originale su
`price_change_1d` resta intatta e passa invariata).

## Round 2 — Feedback dopo verifica del round 1

### 8. Mappa geografica — stesso bug di pan del treemap

**File**: `frontend/src/lib/components/charts/GeographyMap.svelte`

Stesso pattern esatto del treemap: `roam: isTouchDevice ? 'scale' : true` → `roam: true`
incondizionato. Rimossa anche la vecchia euristica di touch-detection
(`'ontouchstart' in window || navigator.maxTouchPoints > 0`, la stessa già corretta nel
treemap) diventata inutilizzata. Nessuna zoom-guard dedicata presente in questo file (a
differenza del treemap) — non necessaria per il tipo `map` di ECharts, lasciata così.

### 9. Menù AI Export (e broker-filter) tagliato sui device piccoli

**File**: `frontend/src/routes/(app)/dashboard/+page.svelte`

Root cause reale: non principalmente z-index (già `z-50`, ampiamente sufficiente), ma
il contenitore radice di `PageToolbar.svelte` ha `overflow-hidden` (necessario per gli
angoli arrotondati) che taglia qualunque dropdown `position:absolute` al suo interno
quando eccede i bordi della toolbar su schermi stretti. Non toccato `PageToolbar.svelte`
(componente condiviso, e in modifica concorrente da un altro workstream in questo
momento). Fix applicato localmente: entrambi i menu (AI export + filtro broker, stesso
identico bug, corretto insieme) convertiti a `position: fixed` con coordinate calcolate
da `getBoundingClientRect()` del trigger, clampate al viewport con margine 8px e flip
verticale se necessario (stesso principio già usato in `ContextMenu.svelte`),
ricalcolate su resize/scroll.

### 10. Colonne P&L giorno-prima rinominate

Etichette colonna (`ExposureTable.svelte`, `ContributionTable.svelte`) abbreviate in
**"Δ1" / "Δ1%"** in tutte le 4 lingue (i tooltip descrittivi restano invariati e più
estesi).

### 11. Bug latente confermato — scaling prezzo bond (`quote_base_quantity`)

**Segnalazione originale**: un BTP mostrava un delta "di un giorno" di +1900,00€ /
+93.60% su una posizione di soli 9870€ — palesemente impossibile.

**Investigazione**: verificato sul DB di prod (`backend/data/prod/sqlite/app.db`,
query in sola lettura) che l'asset (`Btp Piu' Sc Fb33 Eur`, id=4) ha
`quote_base_quantity=100` (i BTP sono quotati "per 100 di nominale"). Il motore di
calcolo (`portfolio_engine.py`) applica correttamente questo fattore per
`market_value`/`unrealized_pnl` tramite `compute_holding_value(qty, price, quote_base)`
(`valuation_utils.py`), ma il campo `gain_loss_change_1d` introdotto nel round 1
calcolava `(current_price − prev_price_base) × quantity` **senza** questo fattore —
inflazionando il delta giornaliero di un fattore ≈100 per qualunque asset con
`quote_base_quantity ≠ 1` (bond in generale).

**Fix**: `backend/app/services/portfolio_service.py` — `gain_loss_change_1d` ora usa
`compute_holding_value()` per entrambe le gambe (prezzo corrente e prezzo di ieri),
esattamente come già fa `market_value`. Il campo `price_change_1d` preesistente NON era
affetto (è un rapporto percentuale, invariante alla scala).

**Test**: nuovo test `test_holding_gain_loss_change_1d_respects_quote_base_quantity` in
`test_portfolio_service.py` con un asset BOND sintetico (`quote_base_quantity=100`,
quantità nominale 10.000) — verificato che **fallisce** con il codice pre-fix (dava
1900 invece di 19.00) e **passa** con il fix. Intera suite `test_portfolio_service.py`
(35 test) verde dopo il fix; `black`/`ruff` puliti.

**Nota a margine (non toccata)**: la fixture preesistente `test_asset` in questo stesso
file usa `Asset(..., ticker="PFTEST", type=AssetType.STOCK)` — questi non sono i nomi
reali dei campi sul modello (`identifier_ticker`, `asset_type`); Pydantic/SQLModel li
ignora silenziosamente come kwarg sconosciuti, quindi quella fixture crea in realtà un
asset con ticker=None e asset_type=OTHER (default), non STOCK/"PFTEST" come sembrerebbe.
Non è collegato al bug segnalato e non l'ho corretto (fuori scope), ma lo segnalo qui
perché potrebbe confondere in test futuri che si aspettano quei valori.

## Round 3 — Pan mobile ancora non funzionante: analisi approfondita

Il fix "roam: true" del round 2 non ha risolto il pan a 1 dito su mobile (confermato
dall'utente anche DOPO aver zoomato prima di provare il drag, escludendo che fosse solo
colpa del clamp-a-scala-1:1 della nostra zoomGuard). Investigazione nel codice sorgente
reale di ECharts/zrender installato (`node_modules/echarts`, `node_modules/zrender`,
non solo documentazione):

- `RoamController.js` (`_pinchHandler`): il gesto a 2 dita invia **sempre e solo** zoom
  (rapporto di distanza tra le dita) — nessuna logica, nemmeno opzionale, riconosce "le
  dita si muovono in blocco" come pan. La proposta utente (2 dita: distanza=zoom,
  traslazione parallela=pan) **non è supportata nativamente** da ECharts.
- `HandlerProxy.js`: il `touchmove` viene tradotto in un `mousemove` sintetico che
  raggiunge correttamente la logica di pan — il codice "ci prova" già oggi.
- Causa reale identificata: senza dichiarare `touch-action: none` sul contenitore, il
  browser mantiene la priorità sul gesto a 1 dito per lo scroll nativo della pagina,
  competendo con (e spesso vincendo su) il tentativo di pan di ECharts — specialmente al
  primo movimento del gesto. `echarts.init()` **non ha** un'opzione `touchAction` in
  questa versione installata (verificato: zero occorrenze nei sorgenti) — il meccanismo
  reale è il CSS standard `touch-action`, già usato in questo codebase per lo stesso
  identico problema (`FilePreviewModal.svelte` → `.image-stage.pannable { touch-action:
  none }`, per il pan dell'immagine in preview).

**Fix applicato**: `touch-action: none` sul contenitore di `ExposureTreemap.svelte`
(style inline) e `GeographyMap.svelte` (classe Tailwind `touch-none`). Nessuna
reimplementazione custom necessaria — riusa tutta la gestione nativa di ECharts.
**Trade-off accettato** (stesso comportamento di Google/Apple Maps embed): toccare il
grafico blocca lo scroll nativo della pagina in quel punto specifico; si scrolla
partendo da fuori l'area del grafico.

**Percorso concordato con l'utente**: provare prima questo fix (più semplice, riusa
tutto); se non risolve o il blocco scroll risulta scomodo, valutare come step successivo
l'implementazione custom del gesto a 2 dita (pro/contro dettagliati discussi con
l'utente: nessun trade-off sullo scroll ma richiede reimplementare da zero
centroide/scala/traslazione, in due punti — treemap e mappa — con calibrazione delicata
per distinguere zoom da pan in un gesto umano reale che è quasi sempre un misto dei due).

## Round 4 — touch-action statico blocca lo scroll anche quando non c'è nulla da pannare

**Segnalazione**: con `touch-action: none` statico, lo scroll verticale della pagina resta
bloccato SEMPRE quando si tocca il grafico — anche a zoom 1:1, quando il treemap/mappa
non hanno nulla da pannare (il contenuto è già tutto visibile).

**Causa**: `touch-action` è una proprietà CSS statica — non può dipendere dallo stato
runtime "c'è qualcosa da pannare in questo momento?". Impostarla fissa a `none` blocca lo
scroll nativo incondizionatamente, indipendentemente dal livello di zoom corrente.

**Fix — `touch-action` dinamico, sincronizzato con lo zoom reale**:
- `echartsTreemapZoomGuard.ts`: aggiunto un callback opzionale `onScaleChange`, invocato
  con la scala cumulativa VERA (già corretta dalla guard) ad ogni evento
  `treemaprender`/`treemapmove`.
- `ExposureTreemap.svelte`: nuovo stato `isZoomedIn` aggiornato dal callback; il
  container passa da `touch-action:auto` (scala 1:1, il pan sarebbe comunque un no-op
  per la guard esistente, quindi nessun costo a lasciare lo scroll nativo) a
  `touch-action:none` solo quando effettivamente zoomato (`scale > 1.01`).
- `GeographyMap.svelte`: stesso principio, agganciato all'evento `'georoam'` che ECharts
  emette ad ogni zoom/pan sulla mappa (verificato nei sorgenti: `chart.on()` usa nomi
  evento minuscoli, quindi `'georoam'` non `'geoRoam'`). Lo zoom vero (cumulativo, non il
  delta del singolo tick) viene letto da `chart.getOption().series[0].zoom` — verificato
  nei sorgenti che l'action handler `geoRoam` chiama `seriesModel.setZoom()`, che
  persiste nel model dell'opzione, quindi `getOption()` riflette lo stato vero.

Il pinch-zoom (2 dita) non compete mai con lo scroll nativo a 1 dito, quindi funziona
comunque anche mentre `touch-action` è ancora `auto`; una volta zoomato, l'evento di
zoom aggiorna `touch-action` a `none` PRIMA che l'utente stacchi le dita e inizi un
nuovo gesto di drag — quindi il pan a 1 dito funziona in modo affidabile una volta
zoomati, mentre lo scroll pagina resta libero quando non serve.

`svelte-check`: 0 errori nei file toccati (1 errore preesistente rilevato in un file
completamente non tracciato di un altro workstream concorrente — `brokers/lots/
FIFOLotsPanel.svelte` — non toccato, fuori scope).

## Round 5 — la causa era un livello più sotto: zrender esclude il touch dal pan

**Segnalazione**: sulla mappa, appena zoomata anche di poco, lo scroll si blocca (touch-
action dinamico funziona) ma il pan NON parte — funzionano solo i click sulle nazioni.

**Causa definitiva** (verificata riga per riga in `node_modules/zrender`, non dedotta):
su qualunque browser mobile moderno che supporta le Pointer Events (`'onpointerdown' in
window`, praticamente tutti oggi), `zrender/lib/dom/HandlerProxy.js` gestisce così i
puntatori:
```js
pointerdown: (event) => { /* sempre tradotto in mousedown interno */ }
pointermove: (event) => { if (!isPointerFromTouch(event)) { /* tradotto in mousemove interno */ } }
pointerup:   (event) => { /* sempre tradotto in mouseup interno */ }
```
Il movimento originato da touch è **esplicitamente escluso** dalla traduzione in
"mousemove" interno — l'unico evento che `RoamController` (il modulo di ECharts che
gestisce il pan) ascolta per calcolare lo spostamento. `pointerdown`/`pointerup` non
hanno questa esclusione, quindi un tap continua a funzionare come click/selezione — ma
il passaggio che calcola il delta di pan non scatta mai per il touch, **indipendentemente
da `roam` o da `touch-action`**. Questo spiega perché nessuno dei fix precedenti (roam:
true, touch-action statico, touch-action dinamico) poteva mai far funzionare
davvero il pan — potevano solo influire su SE lo scroll nativo veniva bloccato insieme
al tentativo di pan, mai sul fatto che il pan stesso partisse.

**Fix**: bypassato interamente il pan nativo di ECharts per il touch. Aggiunti listener
touch manuali (`touchstart`/`touchmove`/`touchend`, non soggetti alla stessa esclusione
di zrender) su `ExposureTreemap.svelte` e `GeographyMap.svelte`, che calcolano dx/dy e
dispacciano **le stesse identiche action native** che il drag col mouse da desktop
avrebbe dispacciato:
- Treemap: nuova `panTreemapBy()` in `echartsTreemapZoomGuard.ts`, che dispaccia
  `treemapMove` con il `rootRect` corrente + delta — il rect corrente arriva dal
  callback `onScaleChange` della guard esistente (esteso per riportare anche il rect,
  non solo la scala), quindi il clamping di zoom/pan già presente si applica
  automaticamente anche a questi pan manuali, nessuna logica duplicata.
- Mappa: dispaccio diretto di `geoRoam` con `dx`/`dy` e un `seriesId` esplicito e
  stabile (`geo-distribution-map`), lo stesso schema che ECharts usa internamente
  (`roamHelper.js`).

Nessuna matematica di pan reinventata: si riusa in entrambi i casi la stessa action
nativa di ECharts, cambia solo CHI la dispaccia (noi, manualmente, invece del bridge
interno di zrender che su touch è rotto). Il pan si attiva solo quando `isZoomedIn` è
vero (stesso stato dinamico del round precedente), preservando il rilascio dello scroll
pagina quando non c'è nulla da pannare.

`svelte-check`: 0 errori sui file toccati.

## Round 6 — limite fondamentale del browser: pan a 1 dito → pan a 2 dita

**Segnalazione**: (a) nel simulatore mobile la rotellina del mouse sopra un grafico non
scrolla la pagina nemmeno a 1:1; (b) il treemap zoomato pannava correttamente, ma
arrivato al bordo si fermava — **non** passava a scrollare la pagina nello stesso gesto.

**Punto (a) — chiarito, non è un bug**: comportamento standard e preesistente di
ECharts (`zoomOnMouseWheel: true` di default su qualunque grafico `roam`), separato
dalla logica touch — la rotellina/trackpad sopra un grafico interattivo lo zooma, non
scrolla la pagina, esattamente come su Google Maps desktop. Non introdotto da nessuno
dei fix di questo thread. **Confermato con l'utente di lasciarlo com'è** (costo di
disabilitarlo: si perderebbe lo zoom da rotellina/trackpad su desktop).

**Punto (b) — limite reale della piattaforma web, non risolvibile con altro codice
sullo stesso approccio**: un browser decide, **una sola volta all'inizio del gesto**,
se quel gesto touch è "scroll nativo" o "gestito da JS" — e non permette di cambiare
idea a metà dito-giù. Una volta che il nostro drag a 1 dito ha iniziato a pannare il
treemap zoomato, non può "restituire" il gesto alla pagina quando il treemap finisce lo
spazio nello stesso gesto continuo — serve staccare il dito e ritoccare. È lo stesso
motivo per cui Google Maps embedded in una pagina scrollabile richiede spesso "usa due
dita per muovere la mappa".

**Fix — pan a 2 dita invece di 1** (confermato con l'utente): un dito è **sempre e solo**
riservato allo scroll pagina (mai intercettato, zero eccezioni, zero casi limite sul
bordo); il pan (quando zoomato) si attiva con **2 dita**, calcolando lo spostamento dal
centroide dei due tocchi invece del punto singolo. Riusa TUTTA l'infrastruttura già
costruita (`panTreemapBy`, dispatch di `geoRoam` con dx/dy) — cambia solo il conteggio
dita e il calcolo del punto di riferimento. Rimossa la logica dinamica di `touch-action`
(non più necessaria: un gesto a 2 dita non compete mai con lo scroll nativo a 1 dito).
Il pinch-to-zoom esistente resta indipendente e continua a funzionare come prima; pan e
zoom si compongono naturalmente su un gesto reale a 2 dita che sia insieme una piccola
traslazione e una piccola variazione di distanza.

`svelte-check`: 0 errori sui file toccati.

## Nota — ambiente condiviso

Durante l'implementazione sono state rilevate modifiche concorrenti non correlate,
provenienti da un altro workstream/sessione nello stesso ambiente (feature "broker
lots/FIFO" e "risoluzione dinamica dei grafici", riferite ai piani
`LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_3/`), interleaved
nei seguenti file toccati anche da questo lavoro:
`backend/app/services/portfolio_service.py`, `backend/app/schemas/portfolio.py`,
`ExposureTable.svelte`, `ContributionTable.svelte`, `AllocationHistoryChart.svelte`,
`GrowthChart.svelte`, `PriceChartFull.svelte`, `LineChart.svelte`. Verificato che le due
serie di modifiche coesistono correttamente (`./dev.py front check` → 0 errori;
`pytest backend/test_scripts/test_services/test_financial/test_portfolio_service.py` →
tutti verdi), ma **prima di qualunque commit va usato uno staging selettivo** (es.
`git add -p`) per non mischiare accidentalmente le due serie di modifiche in un unico
commit.
