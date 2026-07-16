# Report finale — FIFO UI v2, Round 2: bugfix da feedback utente reale

Piano di sessione: vedi `plan.md` della sessione (non versionato nel journal — round gestito come bugfix
diretto, non come nuovo `.prompt.md`). Segue `fifo-ui-refinement-v2-final-report.md` (Consolidamento
visuale, concluso). L'utente ha usato l'implementazione reale in browser e riportato 7 problemi puntuali,
alcuni regressioni introdotte dal round precedente, altri bug pre-esistenti mai notati prima.

Metodo: diagnosi via browser reale (server di test, porta 6041) PRIMA di ogni fix, mai solo lettura
statica del codice — coerente con la metodologia già stabilita nei round precedenti per bug di
rendering/interazione ECharts.

## 1. Tooltip Gantt assente (regressione)

**Causa radice**: l'overlay trasparente `<button>` introdotto nel round precedente per
selezione/doppio-click testabili (`pointer-events:auto` implicito) copre l'intera riga della lane e
intercetta l'hover prima che raggiunga il canvas ECharts sottostante, impedendo il trigger nativo del
tooltip.

**Fix** (`LotGanttChart.svelte`): granularità overlay cambiata da "1 per lane" a "1 per segmento
renderizzato" (`OverlayRect` ora porta anche `dataIndex`); `computeOverlayRects()` riscritta per iterare
`segmentSeriesData` invece di `renderedLanes`. Su `mouseenter`/`mousemove`/`mouseleave`/`focus`/`blur`
dell'overlay, il tooltip nativo è guidato esplicitamente con
`chartInstance.dispatchAction({type:'showTip'|'hideTip', seriesIndex, dataIndex})` — bypassa l'hit-testing
del browser bloccato dall'overlay. Click/dblclick/selezione restano invariati sull'overlay.
`segmentsSeriesIndex()` risolve l'indice della serie `'__segments'` per nome, non hardcoded.

Verificato dal vivo: tooltip corretto per segmenti normali e in-transit, nessuna regressione su
clipping/zoom/pan/selezione.

## 2. Selettore "Entrambi" nel grafico Valore

L'utente si aspettava lo stesso pattern tri-state di Asset Global (`assets/+page.svelte`): due toggle
indipendenti, senza un 3° pulsante esplicito — se nessuno o entrambi sono attivi, si vede tutto.

**Fix** (`LotComparisonChart.svelte`): rimosso `valuePresentation:'aggregate'|'individual'|'both'`
(single-select), sostituito con due `$state<boolean>` indipendenti (`showAggregateValue` default `true`,
`showIndividualValue` default `false`) + logica derivata `effectiveShowAggregateValue`/
`effectiveShowIndividualValue` identica a quella di `assets/+page.svelte` (righe ~110-122/225-234).
Rimossi il 3° pulsante, il test-id `lots-value-both-toggle` e la chiave i18n
`brokers.lots.valuePresentationBoth` (4 lingue). Test E2E `brokers-detail.spec.ts` riscritto per la
semantica a 2 pulsanti.

## 3. Linee dei lotti che scompaiono su hover (bug più esteso del previsto)

Confermato con screenshot baseline/durante-hover/dopo-hover: le linee "Per lotto" (Valore e Rendimento)
sparivano **completamente** (non solo il marker — l'intera polilinea, passato e futuro) per tutta la
durata del tooltip, riapparendo istantaneamente al termine dell'hover.

**Causa radice isolata via debug empirico dal vivo** (hook temporaneo
`window.__debugComparisonChart = chartInstance` + `page.evaluate()` per decine di ipotesi senza rebuild):
bug di ECharts 6.0.0 quando `tooltip.trigger:'axis'` coesiste con più serie `line` che hanno intervalli di
date diversi (es. lotti aperti in date diverse). **Escluso** (verificato uno per uno, nessuno risolutivo):
`emphasis`/`blur`, `z`/`zlevel`, `stack`, disallineamento dati (anche con backbone di date condiviso e
`null` espliciti), `connectNulls`, `hoverLayerThreshold`, `clip`, `sampling`/`large`/`progressive`,
`animation`, campi `name` per punto, `renderer:'canvas'` vs `'svg'` (bug identico in entrambi — esclude
teorie di dirty-rect repaint specifiche del canvas), `tooltip.position` custom, tutte le varianti di
`axisPointer.type`.

**Fix**: override di `tooltip:{trigger:'item'}` a livello di singola serie sulle linee "per lotto"
(mantenendo `tooltip.trigger:'axis'` a livello di chart per le serie Aggregato, confermate non
affette) — la configurazione di serie si unisce, non sostituisce, quella di chart, ed è sufficiente a far
uscire quelle linee dal calcolo bacato di axis-trigger. Costante `PER_LOT_LINE_TOOLTIP_OVERRIDE` (con
commento esteso che documenta l'indagine) applicata alle 3 serie per-lotto: `value-total-${lotId}`
(Valore), `return-${lotId}` (Rendimento), `price-opening-${lotId}` (Prezzo — stesso pattern di serie a
copertura-date variabile, fix applicato preventivamente).

Trade-off UX minore: l'hover su una linea per-lotto specifica mostra ora solo il tooltip di quella linea
(item-trigger) invece di unirsi al tooltip multi-serie condiviso — ma le linee non spariscono mai più.

Verificato dal vivo con sweep di hover su più posizioni X, in tutte e 3 le modalità (Valore/Entrambi,
Rendimento, Prezzo): nessuna linea sparisce in nessun punto del range.

## 4. Colonne "Stato" e "Custodia" troppo larghe

**Fix** (`UnifiedLotsTable.svelte`): `status` `width/minWidth` 210/190 → 150/120; `custody` 210/190 →
160/130. Verificato che badge singoli/doppi e pill "N broker" non vengano troncati.

## 5. Date nel tooltip del 3° grafico solo mese+giorno (nessun anno)

**Causa radice**: `formatAxisDate()` (senza anno, corretto per le label asse X) era riusata anche per
l'header dei tooltip (`buildValueTooltip`/`buildReturnTooltip`/`buildPriceTooltip`).

**Fix** (`LotComparisonChart.svelte`): 3 call-site passati a `formatLongDate(rawDate)` (con anno). Le
label dell'asse X restano su `formatAxisDate` (compatte, coerenti con Gantt/WAC chart).

**Regressione intermedia scoperta e corretta durante il fix**: `formatLongDate` accettava solo `string`;
`rawDate` è spesso un timestamp numerico in ms (non stringa) — `new Date(String(timestampMs))` non
parsifica correttamente (mostra le cifre grezze). Risolto allargando la firma a
`formatLongDate(value: number | string)` e rimuovendo il wrapping `String(...)` ai 3 call-site.

## 6. Traduzione "WAC" non localizzata (mostra "WAC" anche in italiano)

**Causa radice**: 2 literal hardcoded bypassavano l'i18n — `LotWacPriceChart.svelte` (`wac:'WAC'`, titolo
grafico) e `LotComparisonChart.svelte` (`` `WAC — ${brokerName(brokerId)}` ``); inoltre la chiave
`brokers.lots.cumulativeWac` esisteva già ma conteneva ancora "WAC" letterale in IT/FR/ES.

**Fix**: riusata la chiave i18n già esistente e corretta `dashboard.pmc` (EN "Avg. Cost", IT "PMC", FR
"PRU", ES "PMC" — già usata identicamente in `ExposureTable.svelte`) al posto di entrambi i literal
hardcoded. Aggiornate le 4 traduzioni di `cumulativeWac` (EN "Cumulative Avg. Cost", IT "PMC cumulato", FR
"PRU cumulé", ES "PMC acumulado"). Verificato dal vivo in italiano: titolo e legenda del grafico WAC e il
grafico comparativo mostrano "PMC" ovunque, nessuna nuova chiave introdotta.

## 7. Modale dettaglio lotto — troppi zeri decimali (es. "1.000000 CHIP")

**Causa radice**: `LotCustodyModal.svelte` chiamava `formatDecimalForDisplay(abs, {minFrac:6, maxFrac:8})`
— `minFrac:6` forza sempre 6 decimali anche per quantità intere, annullando lo strip degli zeri finali che
la utility farebbe di default. `UnifiedLotsTable.svelte` usa correttamente `minimumFractionDigits:0` per
lo stesso dato — la modale era l'unica incoerente.

**Fix**: `minFrac` cambiato da `6` a `0` in `formatQuantity`. Verificato: quantità intere mostrano "10
AAPL" invece di "10.000000 AAPL"; quantità frazionarie reali continuano a mostrare i decimali necessari
senza perdita di precisione (fino a `maxFrac:8`).

## File modificati

- `frontend/src/lib/components/brokers/lots/LotGanttChart.svelte` — fix #1
- `frontend/src/lib/components/brokers/lots/LotComparisonChart.svelte` — fix #2, #3, #5, #6
- `frontend/src/lib/components/brokers/lots/LotWacPriceChart.svelte` — fix #6
- `frontend/src/lib/components/brokers/lots/UnifiedLotsTable.svelte` — fix #4
- `frontend/src/lib/components/brokers/lots/LotCustodyModal.svelte` — fix #7
- `frontend/src/lib/i18n/{en,it,fr,es}.json` — fix #2 (rimossa `valuePresentationBoth`), fix #6
  (aggiornata `cumulativeWac`)
- `frontend/e2e/brokers/brokers-detail.spec.ts` — test toggle Valore riscritto per design a 2 pulsanti

Nessun file backend toccato in questo round (nessun dato mancante — tutti i 7 problemi erano di
rendering/stato/i18n frontend).

## Riuso

Nessuna nuova libreria introdotta. Riusati: pattern tri-state di `assets/+page.svelte`, chiave i18n
`dashboard.pmc` già usata in `ExposureTable.svelte`, `formatLongDate`/`formatAxisDate`/
`formatDecimalForDisplay` già esistenti, meccanismo `dispatchAction` nativo di ECharts (nessun nuovo
helper di tooltip).

## Test e comandi eseguiti

- `svelte-check`: 0 errori, 0 warning (verificato ad ogni file toccato e in validazione finale).
- `./dev.py i18n audit`: 1664/1664 chiavi complete, 42 chiavi inutilizzate preesistenti e non correlate
  (nessuna nuova chiave morta introdotta; `valuePresentationBoth` rimossa correttamente).
- `./dev.py test front-broker detail`: **22/22 passati**, incluso il test riscritto del toggle Valore
  (verifica esplicita della semantica tri-state a 2 pulsanti) e tutti i test Gantt/tooltip/context-menu
  preesistenti — nessuna regressione.

## Verifica E2E manuale (screenshot reali)

Tutti i 7 fix verificati dal vivo su server di test (porta 6041), inclusi:

- Tooltip Gantt su segmenti normali e in-transit.
- Toggle Valore: nessuno premuto → mostra entrambe le serie; un solo toggle premuto → filtro esclusivo;
  entrambi premuti → mostra entrambe.
- Sweep di hover multi-punto su Valore/Entrambi, Rendimento e Prezzo (quest'ultimo non esplicitamente
  segnalato dall'utente, verificato comunque data la stessa causa strutturale): nessuna linea sparisce in
  nessuna posizione, su un lotto reale a 4 aperture (Interactive Brokers, AAPL).
- Tooltip del 3° grafico con anno completo (es. "May 30, 2026").
- Colonne Stato/Custodia più compatte.
- "PMC" al posto di "WAC" in italiano (titolo, legenda, tooltip).
- Quantità nella modale senza zeri decimali superflui.

## Limitazioni residue

- Il fix del bug hover (#3) introduce un compromesso UX minore: hover su una linea "per lotto" specifica
  mostra solo il tooltip di quella linea (item-trigger) invece di un tooltip condiviso multi-serie — scelta
  necessaria per eliminare la sparizione delle linee ed esplicitamente documentata nel codice
  (`PER_LOT_LINE_TOOLTIP_OVERRIDE` in `LotComparisonChart.svelte`).
- Il fix preventivo sulla serie Prezzo (`price-opening-${lotId}`) non era stato esplicitamente segnalato
  come rotto dall'utente, ma condivide la stessa caratteristica strutturale (serie con copertura-date
  variabile) — verificato comunque dal vivo in questo round, nessuna anomalia.
