# Report finale — Refinement FIFO UI v1

Piano sorgente: [`refinment-work-v1.md`](./refinment-work-v1.md). Log passo-passo: [`fifo-ui-refinement-v1-implementation-log.md`](./fifo-ui-refinement-v1-implementation-log.md).

## 1. Diagnosi iniziale

Metodo: chiamate reali a `POST /portfolio/lots/analysis` (BTC id=6, semplice; AAPL id=1, ricco — 10 lotti, tutti i tipi di evento) + screenshot browser reali via Playwright contro il server di test, non solo lettura statica del codice.

**Scoperta metodologica**: un sub-agent "explore" dedicato all'analisi del Gantt, leggendo solo il codice, aveva concluso che il componente fosse "già quasi corretto" (asse temporale, custom series, spessore/colore/opacità tutti presenti). Lo screenshot reale ha mostrato l'esatto opposto: nessuna barra visibile, solo una lista verticale. Questo ha guidato la decisione di **non delegare il fix del Gantt** e di procedere con debug visivo iterativo in prima persona.

Causa radice per area (dettaglio completo nel log):

| Problema | Causa | Categoria diagnostica |
|---|---|---|
| Gantt = lista verticale | `grid-cols-[240px,minmax(720px,1fr)]` — virgola invalida in CSS, doveva essere underscore | Configurazione CSS errata |
| Gantt canvas vuoto (dopo fix CSS) | `renderItem` leggeva `params.data?.meta`, sempre `undefined` per custom series con item-object in ECharts 6 | Bug applicativo (non backend) |
| Click/dblclick Gantt non selezionavano | Limitazione nota ECharts: eventi sui children di un `group` da `renderItem` non risalgono a `chart.on('click')` | Bug applicativo (non backend) |
| Tooltip Gantt con chiavi i18n grezze | Pattern `$t(key) \|\| fallback` non funziona: la libreria i18n ritorna la chiave stessa, non una stringa vuota | Bug applicativo |
| Marker WAC mancanti | Backend correttto; orchestratore non richiedeva mai `EVENT_HISTORY` | Analisi non richiesta dal frontend |
| Rendimento comparativo vuoto per BUY | `reference_unit_price` popolato solo per ADJUSTMENT_IN | Dato assente dal backend |
| Prezzo comparativo con label generiche + WAC cumulato indebito | Nessuna prop `brokers`; nessun gate su numero broker detentori | DTO/props incompleto |
| Tabella: colonne mancanti, click Custodia rompeva selezione | Colonne non aggiunte; `event.stopPropagation()` mancante | Dato non renderizzato / bug propagazione |
| Modale: history incompleta | Riceveva solo `custody_history` (subset), non l'`EVENT_HISTORY` completo | Analisi non richiesta dal frontend |

## 2. Decisioni assunte

1. `total_return` come campo **additivo** su `LotReturnHistoryPoint` (non sostituisce `relative_return`, che resta per l'Open Return secondario).
2. Open Return generalizzato: fallback a `opening_unit_price` quando `reference_unit_price` non è disponibile (lotti BUY).
3. Filtro Aperti/Tutti sollevato da `LotGanttChart` a stato condiviso nell'orchestratore — stesso set di lotti in Gantt e Tabella.
4. `EVENT_HISTORY` fetchato una sola volta, riusato per marker WAC e history completa in modale.
5. Marker TRANSFER: un solo marker per evento (data di arrivo), intervallo di transito ricostruito via pairing quando esiste un DEPART, altrimenti data singola.

## 3. File creati, modificati, rimossi

**Backend modificato**: `backend/app/schemas/portfolio.py` (+1 campo), `backend/app/services/lots_analysis_service.py` (+2 helper, generalizzazione reference price), `backend/test_scripts/test_services/test_financial/test_lots_analysis_service.py` (+7 test), `backend/test_scripts/test_api/test_portfolio_api.py` (+1 test).

**Frontend modificato**: `LotsAnalysisPanel.svelte` (orchestratore — EVENT_HISTORY, filtro condiviso, prop brokers), `LotGanttChart.svelte` (fix CSS, fix meta-lookup, fix click/dblclick via `info`, fix i18n, filtro come prop), `LotWacPriceChart.svelte` (5 serie marker), `LotComparisonChart.svelte` (3 modalità riscritte a serie temporale), `UnifiedLotsTable.svelte` (colonne, stopPropagation, tooltip), `LotCustodyModal.svelte` (summary, custodia raggruppata, history estesa), `DataTable.svelte` (stopPropagation generico su celle clickable — verificato unico consumer = tabella lotti), `frontend/e2e/brokers/brokers-detail.spec.ts` (+2 test).

**i18n**: aggiunte ~25 chiavi nette in 4 lingue (`brokers.lots.chartMarkers.*`, `brokers.lots.dateRange`, `brokers.lots.openQuantity/currentValue/openReturn`, `brokers.lots.modal.*`); rimosse 3 chiavi orfane (`comparisonTitle`, `brokerWac`, `originalCostReference`).

**Nessun file rimosso** in questa fase (rifinitura, non migrazione — i 5 componenti principali restano quelli della v2, solo evoluti).

## 4. Materiale esistente riusato

`DataTable`, `ModalBase`, `BrokerBadge`, `AssetIcon`, `getBrokerColor`, `echartsDataZoomSync`, `echartsDataZoomTouchPan`, `echartsTooltipHelpers` (`buildTooltipHeader/Row/Theme`, `setupTooltipAutoHide`), `chartCoreHelpers` (`buildDataZoom`), `formatCurrencyAmountPlain`, `formatDecimalForDisplay`. Nessuna libreria parallela introdotta.

## 5. Formule e invarianti implementate

- `TotalReturn_i(t) = (OpenValue_i(t) + Proceeds_i(t)) / OriginalCost_i - 1` — calcolato riusando la stessa logica di `_build_value_history` (nessuna duplicazione, helper condiviso `_value_snapshot_on_date`).
- `OpenReturn_i(t) = MarketPrice(t) / OpeningReferencePrice_i - 1`, dove `OpeningReferencePrice_i = reference_unit_price` (ADJUSTMENT_IN) oppure `opening_unit_price` (BUY, fallback nuovo).
- Spessore Gantt: `Thickness(q) = Tmin + (q/Qmax)·(Tmax-Tmin)` — già corretto, solo verificato.
- Opacità Gantt: aperto 90% / in transito 65% / chiuso 45% — già corretto, solo verificato.

## 6. Test e comandi eseguiti (risultati)

| Comando | Risultato |
|---|---|
| `pytest backend/test_scripts/test_services/` | 966/967 (1 fallimento pre-esistente, isolamento test non correlato — §8) |
| `pytest backend/test_scripts/test_api/test_portfolio_api.py` | 21/21 |
| `pytest backend/test_scripts/test_schemas/ test_utilities/` | 479/479 |
| `ruff check backend/app/` | 8 errori, tutti pre-esistenti (diff vuoto sui file interessati) |
| `black --check` | 3 file da riformattare, tutti pre-esistenti (diff vuoto) |
| `./dev.py api sync` | OK — `total_return` presente nel client TS rigenerato |
| `svelte-check` | 0 errori, 0 warning |
| `./dev.py i18n audit` | 1652 chiavi, 100% complete, 42 non usate (tutte pre-esistenti) |
| `./dev.py mkdocs build` | pulito |
| `./dev.py test front-broker detail` (E2E) | 19/19 (17 pre-esistenti + 2 nuovi) |
| `./dev.py mkdocs gallery -f "fifo lots panel"` | 2/2, 16 screenshot (4 lingue × 2 temi) |

## 7. Bug reali trovati e corretti durante l'implementazione

1. **CSS Gantt** (`grid-cols-[240px,minmax(720px,1fr)]` → underscore) — causa radice del Problema #1 del piano.
2. **ECharts `params.data.meta` sempre `undefined`** per custom series con item-object — fix con lookup `array[params.dataIndex]`.
3. **Click/dblclick Gantt non funzionanti** — limitazione nota ECharts (children di group non bubblano a `chart.on`), fix con `info` + `params.info`.
4. **Chiavi i18n grezze nel tooltip Gantt** (`dashboard.direction`, `common.dateRange` inesistenti, pattern fallback errato).
5. **Test API con schema errato** (`date_to` flat invece di `date_range: {end}`) — scritto da un agente, corretto.
6. **Test TS in `visibleLots`** (confronto numerico su stringa, `states` possibilmente undefined) — trovato da svelte-check, corretto.
7. **Bug latente pre-esistente nel backend** (fx-need registrato solo per `LOT_SUMMARY`, mai per `RETURN_HISTORY` da solo) — trovato e corretto dall'agente A1 come effetto collaterale necessario del fix principale.

## 8. Limitazioni e problemi pre-esistenti segnalati (non corretti)

- **Test flaky per isolamento**: `test_buy_sell_summary_converts_to_target_currency` fallisce (UNIQUE constraint su `fx_rates`) SOLO quando eseguito come parte dell'intera suite `test_services/` (966 test), passa in isolamento. Non è stato modificato da questa sessione (confermato via diff). Causa probabile: un altro test nella suite lascia una riga FX che collide. Segnalato per un piano dedicato di pulizia test, non corretto qui (fuori scope).
- **Ambiente**: eseguire `pytest backend/test_scripts/test_api/` per intero (44 file, 39 con server di test live) causa SIGKILL per esaurimento risorse — limite già noto dell'ambiente, non specifico di questa sessione. Mitigato eseguendo i file rilevanti singolarmente/in piccoli gruppi.
- **8 errori ruff e 3 file non formattati black pre-esistenti** nel resto del backend, invariati da questa sessione.

## 9. Attività rinviate (deliberatamente, per rispetto della preferenza utente sul testing manuale)

Non è stata scritta una suite E2E estesa per l'intera lista di interazioni del piano §9 (cambio modalità grafico comparativo, dark mode pixel-perfect, mobile, doppio click/pulse dettagliato). Sono stati aggiunti solo 2 test E2E mirati (estensione del file esistente) per le 2 interazioni che erano REALMENTE rotte e ora sono fisse (selezione Gantt→tabella, click Custodia senza deselezione). Il resto è stato verificato visivamente con screenshot reali durante questa sessione ma non automatizzato ulteriormente.

## Checklist di verifica manuale suggerita

Server: `http://localhost:6040` (dopo rebuild). Percorso: Dashboard o Broker → tab Posizioni → azione riga "Analizza Lotti".

- [ ] Il Gantt ("Lot life & custody") mostra barre orizzontali colorate con etichette broker+quantità, non una lista.
- [ ] Il grafico "WAC / Market Price" mostra pallini/quadrati/rombi colorati (marker) sopra la linea prezzo, con legenda Acquisti/Vendite/Trasferimenti/Rettifiche/Split.
- [ ] Selezionare 2-3 lotti nella tabella → il grafico "Value of selected lots" mostra un'area temporale, non barre statiche.
- [ ] Modalità "Return" del grafico comparativo non è vuota per un lotto normale (BUY).
- [ ] Cliccare la cella Custodia in tabella apre la modale SENZA deselezionare la riga.
- [ ] Nella modale, verificare Valore corrente/P&L FIFO/Open Return e la history completa (BUY/SELL/TRANSFER/ADJUSTMENT/SPLIT se presenti).
- [ ] Toggle Aperti/Tutti sopra il Gantt aggiorna sia Gantt che Tabella in modo coerente.
- [ ] Dark mode e viewport mobile — controllo visivo libero.
