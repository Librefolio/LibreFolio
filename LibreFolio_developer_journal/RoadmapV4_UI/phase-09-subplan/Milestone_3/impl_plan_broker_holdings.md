# Piano Implementativo: Broker Holdings & Pannello Lotti FIFO (Milestone_3 — Fase 2)

> **Deriva da**: [`plan_ui_broker_holdings.md`](./plan_ui_broker_holdings.md) (disegno UI + requisiti dati,
> raffinato 2026-07-08/10 — §1/§1bis/§1ter/§2/§3).
> **Fase correlata (già implementata)**: [`impl_plan_broker_overview.md`](./impl_plan_broker_overview.md)
> (Fase 1 — shell a tab, `PositionsPanel` montato nel tab Posizioni).
> **Ambito**: tab Posizioni (click/dblclick su tutti i 4 sotto-componenti) + pannello inline Lotti FIFO
> (Bubble Timeline + WAC/Prezzo `[EUR|%]` + tabelle Aperti/Chiusi). Nessun redesign del tab Transazioni
> (Fase 3, già chiusa) né della shell (Fase 1, già implementata).
>
> **Stato: ✅ implementato (2026-07-10, esecuzione fleet parallela)** — vedi "Note implementazione" ad ogni
> step sotto. Codice in working tree, non ancora committato (per scelta dell'utente, coerente con la Fase 3).
>
> **✅ Evoluzione multi-broker (2026-07-11)** — vedi sezione dedicata in fondo al documento. Il pannello e i
> suoi 5 componenti ora accettano liste di broker (non solo 1), con colonna/colore per broker sui lotti e
> serie WAC combinata sul grafico quando >1 broker. Mai committato nemmeno questo giro.

## Principio guida

> Riusare ovunque i componenti/utility già scritti, evitare di ricostruire ciò che esiste già (`GET
> /portfolio/lots` invariato, `<DataTable>`/`navigateToRowId()`, `queryParams.ts`, pattern `?tab=` di
> `files/+page.svelte`). I 2 soli elementi di infrastruttura genuinamente nuovi sono il guard
> click-vs-dblclick e il pannello inline con `transition:slide` — motivati in `plan_ui_broker_holdings.md`
> §1ter/§2 (nessun precedente equivalente nel codebase, verificato via grep).

## Decisioni prese (non più aperte)

| Decisione | Scelta |
|---|---|
| Contenitore Lotti FIFO | Pannello inline sotto `PositionsPanel` (Opzione 4), non modale — query-param `?asset=<id>` (Opzione 5) |
| Interazione riga/tile/barra | Click singolo → pannello, doppio click → `goto('/assets/'+assetId)` invariato — su **tutti e 4** i sotto-componenti (`ExposureTable`, `ContributionTable`, `ExposureTreemap`, `PerformanceChart`), non solo le tabelle |
| MWRR per-asset nel grafico WAC/Prezzo `[%]` | **Droppato** (2026-07-10) — si calcolano solo `roi`+`twrr`; `mwrr_annualized`/`mwrr_cumulative` **rimossi** da `AssetHistoryPoint`, non lasciati `None` |
| Lotti FIFO in Asset Detail (Opzione B) | Scartata per Milestone_3 (vedi `plan_ui_broker_holdings.md` §1bis) |
| Diff Fase 3 (Transazioni) non committato | Ignorato — questo piano lavora sopra quel diff così com'è |
| Dipendenza da `timeSeriesAggregation.ts`/chart-resolution | **Esplicitamente esclusa** — WIP di un'altra sessione in parallelo, non toccare. Bubble Timeline e WAC/Prezzo usano risoluzione giornaliera fissa |

## Ordine di implementazione

```
STEP 1 (Backend, sequenziali sullo stesso file di test)
 ├─ 1.1 Ripristino GET /portfolio/asset-history — vista [EUR]
 └─ 1.2 Calcolo roi/twrr in get_asset_history() — vista [%] (dopo 1.1, stesso test file)
         │
STEP 2 (Frontend, infra condivisa — nessuna dipendenza da Step 1)
 ├─ 2.1 clickVsDblClick.ts (nuova utility)
 ├─ 2.2 assetPanelUrl.ts (helper ?asset=<id>)
 └─ 2.3 Campo assetId isolato su PerformanceChart::AssetRow
         │
         ▼
STEP 3 (Frontend, cablaggio click — dipende da Step 2)
 ├─ 3.1 ExposureTable/ContributionTable: onRowClick (dipende da 2.1)
 └─ 3.2 ExposureTreemap/PerformanceChart: click/dblclick ECharts (dipende da 2.1, 2.3)
         │
         ▼
STEP 4 (Frontend, componenti grafico — Bubble/Tabelle indipendenti da Step 1; WAC/Prezzo dipende da 1.1)
 ├─ 4.1 BubbleLotTimeline.svelte (0 dipendenze backend, GET /portfolio/lots già pronto)
 ├─ 4.2 OpenLotsTable/ClosedLotsTable.svelte (0 dipendenze backend, idem)
 └─ 4.3 AssetWacPriceChart.svelte [EUR|%] (dipende da 1.1; [%] tollera null se 1.2 non pronto)
         │
         ▼
STEP 5 (Frontend, convergenza) → FIFOLotsPanel.svelte + wiring in brokers/[id]/+page.svelte
         │
         ▼
STEP 6 — i18n + validazione finale
```

---

## STEP 1 — Backend

> ✅ **Note implementazione** (2026-07-10): entrambi i sotto-step completati come da piano, nessuna
> deviazione. `roi`/`twrr` calcolati riusando `_get_transactions()`/`calculate_simple_roi_series`/
> `calculate_twrr_series` esattamente come descritto in 1.2. Aggiunto `model_config =
> ConfigDict(extra="forbid")` ad `AssetHistoryPoint` (non esplicitamente richiesto dal piano ma coerente
> con la convenzione del file, verificato sulle classi vicine). 23/23 test di `test_portfolio_api.py`
> passano (incluso il nuovo `test_asset_history_populates_roi_twrr_and_omits_mwrr_fields`), 0 lint error.

### 1.1 Ripristino `GET /portfolio/asset-history` — vista `[EUR]`

- **Non è un gap da progettare, è una regressione da ripristinare** (verificato via `git log`/`git show`):
  la route esisteva (commit `06613074`), rimossa per errore nel commit `3184a969` insieme a un cleanup di
  endpoint realmente superseduti (`/summary`, `/history`, `/allocation-history`) — `/asset-history` non lo
  era (non superseduto da `/report`, non citato nel commento del commit, docstring del file lo elenca
  ancora oggi come disponibile).
- **File**: `backend/app/api/v1/portfolio_api.py` — reintrodurre la route esattamente come rimossa (stesso
  path/firma):
  ```python
  @portfolio_router.get(
      "/asset-history",
      response_model=list[AssetHistoryPoint],
      summary="Asset WAC vs market price history",
      description="Time series of WAC (cost basis per unit) vs market price for a specific asset.",
  )
  async def get_asset_history(
      asset_id: int = Query(..., description="Asset ID"),
      broker_id: Optional[int] = Query(None, description="Optional broker filter"),
      session: AsyncSession = Depends(get_session_generator),
      current_user: User = Depends(get_current_user),
  ) -> list[AssetHistoryPoint]:
      """Return WAC vs market price series for a specific asset."""
      service = PortfolioService(session)
      return await service.get_asset_history(
          user_id=current_user.id,
          asset_id=asset_id,
          broker_id=broker_id,
      )
  ```
  Ripristinare gli import mancanti (`AssetHistoryPoint`, `Optional`) in cima al file, e la riga di docstring
  del modulo (già presente, non serve modificarla).
- **Nessuna modifica al servizio in questo sotto-step**: `PortfolioService.get_asset_history()`
  (`backend/app/services/portfolio_service.py:1953`) è già intatto e produce `date`/`wac`/`market_price` —
  la vista `[EUR]` funziona subito dopo il ripristino della route.
- **Test**: ripristinare in `backend/test_scripts/test_api/test_portfolio_api.py` la classe
  `TestAssetHistoryEndpoint` rimossa nello stesso commit (3 test): `test_unauthenticated` (401 senza auth),
  `test_missing_asset_id` (422 se `asset_id` manca), `test_nonexistent_asset` (200 con array vuoto per
  asset inesistente, nessun 500).
- Eseguire pytest mirato su questi 3 test dopo il ripristino.

### 1.2 Calcolo `roi`/`twrr` per-asset — vista `[%]`

- **Non è un ripristino, è un gap di calcolo reale**: verificato che `roi`/`twrr`/`mwrr_annualized`/
  `mwrr_cumulative` erano dichiarati in `AssetHistoryPoint` fin dalla nascita dell'endpoint (commit
  `06613074`) ma **mai popolati** — il corpo di `get_asset_history()` in quel commit è identico carattere
  per carattere a quello orfano di oggi (confrontato via `git show`).
- **File**: `backend/app/services/portfolio_service.py`, dentro `get_asset_history()` (riga 1953). Per ogni
  asset, riusare `_get_transactions()` (stesso pattern già usato da `get_lots()`, righe ~2024) per ottenere
  le transazioni BUY/SELL dell'asset sul broker target, e costruire:
  - una serie di quantità posseduta cumulativa per data (BUY aggiunge, SELL sottrae — stessa logica già
    presente in `fifo_inputs`/FIFO, non serve reimplementarla da zero, solo una somma cumulativa parallela);
  - `NAVSnapshot(date=ph.date, nav=qty_held_at(ph.date) * ph.close)` per ogni punto prezzo già iterato nel
    loop esistente (non un NAV di portafoglio, un "NAV" della sola posizione asset);
  - `CashFlowInput(date=tx.date, amount=...)` per ogni transazione BUY (importo negativo, costo pagato) e
    SELL (importo positivo, incasso) dell'asset.
  Passare le 2 liste a `calculate_simple_roi_series`/`calculate_twrr_series`
  (`backend/app/utils/financial/roi_utils.py:108,207` — già generici, **nessuna modifica a quel file**) e
  mergiare i risultati (per data) in `roi`/`twrr` di ogni `AssetHistoryPoint`.
- **File**: `backend/app/schemas/portfolio.py` — `AssetHistoryPoint` (righe 437-446). **Rimuovere**
  `mwrr_annualized`/`mwrr_cumulative` (deciso con l'utente 2026-07-10, non lasciarli sempre `None`).
- Dopo la modifica: `./dev.py api sync`.
- **Test**: estendere (stesso file di 1.1, eseguire questo sotto-step **dopo** 1.1 per evitare conflitti di
  merge sullo stesso file test) con assert su `roi`/`twrr` popolati per un asset con storico noto, e
  verificare che `mwrr_annualized`/`mwrr_cumulative` non esistano più nella response.

---

## STEP 2 — Frontend: infrastruttura condivisa

> ✅ **Note implementazione** (2026-07-10): tutti i 3 sotto-step completati come da piano. `clickVsDblClick.ts`
> esporta `createClickGuard<T>(onSingleClick, onDoubleClick, delayMs=250) → {handleClick, handleDblClick,
> dispose}`. `assetPanelUrl.ts` esporta `getAssetPanelAssetId(searchParams)`/`buildAssetPanelUrl(currentUrl,
> assetId)`. 10/10 unit test (vitest) passano, 0 svelte-check error.

### 2.1 `clickVsDblClick.ts` — guard condiviso

- **Nuovo file**: `frontend/src/lib/utils/interaction/clickVsDblClick.ts` (cartella nuova — nessun
  precedente equivalente nel codebase, verificato via grep su `dblclick`/`clickTimeout`).
- Pattern standard: `setTimeout` ~250ms per il click singolo, annullato se arriva un secondo click entro la
  finestra (→ scatta solo il dblclick). Esporta una funzione (es. `createClickGuard(onSingle, onDouble)`)
  riusabile sia da handler `onclick`/`ondblclick` su `<DataTable>` sia da listener nativi ECharts.
- **Test**: `frontend/src/lib/utils/interaction/__tests__/clickVsDblClick.test.ts` (pattern esistente:
  `frontend/src/lib/utils/__tests__/*.test.ts`, runner `vitest`, `npm run test:unit`).

### 2.2 `assetPanelUrl.ts` — helper query-param

- **Nuovo file**: `frontend/src/lib/utils/broker/assetPanelUrl.ts` (stessa cartella di
  `brokerColors.ts`/`brokerHelpers.ts`).
- Wrapper su `frontend/src/lib/utils/url/queryParams.ts` (già esistente, non modificarlo): lettura con
  `getOptionalNumberParam(searchParams, 'asset')`, scrittura con `setOptionalNumberParam(...)`.
- Pattern di navigazione da riusare in STEP 5: `goto(newUrl, {replaceState:true, noScroll:true})`, stesso
  approccio di `frontend/src/routes/(app)/files/+page.svelte` (righe 222/236-240) per `?tab=`.

### 2.3 Campo `assetId` isolato su `PerformanceChart::AssetRow`

- **File**: `frontend/src/lib/components/dashboard/PerformanceChart.svelte` — interfaccia `AssetRow`
  (righe 56-67): aggiungere `assetId: number`, popolato da `position.asset_id` nel derived `chartRows`
  (riga ~258, oggi solo incastonato nella stringa `key`).
- Nessun'altra modifica in questo sotto-step — serve solo a rendere possibile 3.2.

---

## STEP 3 — Frontend: cablaggio click/dblclick

> ✅ **Note implementazione** (2026-07-10): entrambi i sotto-step completati come da piano. Aggiunta non
> prevista dal piano: `PositionsPanel.svelte` (il contenitore dei 4 sotto-componenti, mai citato come file
> da toccare in questo documento) necessitava di un piccolo forwarding — nuova prop `onAnalyze` sulla sua
> stessa `Props` interface, passata as-is a tutti i 4 figli — senza questo passaggio la callback non
> sarebbe mai arrivata dalla pagina ai componenti. Fatto in STEP 5 insieme al resto del wiring.

### 3.1 `ExposureTable`/`ContributionTable` — click singolo

- **File**: `frontend/src/lib/components/dashboard/ExposureTable.svelte` e `ContributionTable.svelte`.
- Nuova prop callback (es. `onAnalyze?: (assetId: number) => void`), passata a `<DataTable
  onRowClick={...}>` avvolta nel guard di 2.1: click singolo → `onAnalyze(row.assetId)`; il dblclick
  esistente (`goto('/assets/'+assetId)`, `ExposureTable.svelte:296-298,318`) resta **invariato**.
- `enableActions`/`enableContextMenu` restano disattivati (invariato, non serve una colonna azioni).

### 3.2 `ExposureTreemap`/`PerformanceChart` — click/dblclick nativi ECharts

- **`ExposureTreemap.svelte`**: aggiungere listener `click` nativo ECharts (`chartInstance.on('click',
  ...)`, stessa guardia `meta?.level === 'asset'` del `dblclick` esistente, righe 417-423/459), avvolto nel
  guard di 2.1, che chiama la stessa prop `onAnalyze`.
- **`PerformanceChart.svelte`**: oggi zero interazione — aggiungere sia `click` sia `dblclick` nativi
  ECharts sulla barra (usa il campo `assetId` di 2.3): `click` (guardato da 2.1) → `onAnalyze`; `dblclick`
  → `goto('/assets/'+assetId)` (nuovo per questo componente). Escludere le righe `kind === 'other'`
  ("Other period effects") da entrambi gli handler — nessun lotto da mostrare per loro.

---

## STEP 4 — Frontend: componenti grafico

> ✅ **Note implementazione** (2026-07-10): tutti e 3 i sotto-step completati come da piano, in parallelo.
> `OpenLotsTable`/`ClosedLotsTable` derivano "Valore Att."/"P&L %" per i lotti aperti solo da campi già in
> `OpenLotSchema` (`residualCostBasis + unrealized_pnl`, `unrealized_pnl / residualCostBasis`), nessun prop
> aggiuntivo necessario. `AssetWacPriceChart` gestisce correttamente lo stato `roi`/`twrr` tutti-null (visto
> durante lo sviluppo in parallelo con 1.2) con uno stato vuoto dedicato invece di un grafico rotto.

### 4.1 `BubbleLotTimeline.svelte`

- **Nuovo file**: `frontend/src/lib/components/brokers/lots/BubbleLotTimeline.svelte`.
- Bubble chart ECharts: bolla = lotto, x = data acquisto, y = gain% (derivato client-side da
  `unrealized_pnl`/`buy_price`/`quantity` per i lotti aperti e da `realized_pnl` per i chiusi — tutti già
  in valuta nativa asset, verificato in `portfolio_service.py:2061-2089`, **nessun dato backend
  aggiuntivo**), dimensione/tratteggio bolla = quota residua vs originale (lotti aperti).
- Consuma `GET /portfolio/lots` (`OpenLotSchema`/`ClosedLotSchema`) — già montato, invariato, **0
  dipendenze da STEP 1**.
- Click su bolla → prop callback (es. `onLotClick(buyTransactionId)`) per il collegamento "Goto & Pulse"
  con le tabelle di 4.2 (wiring finale in STEP 5).
- Risoluzione temporale fissa giornaliera — **non dipendere da `timeSeriesAggregation.ts`**.

### 4.2 `OpenLotsTable.svelte` / `ClosedLotsTable.svelte`

- **Nuovo/i file**: `frontend/src/lib/components/brokers/lots/OpenLotsTable.svelte` +
  `ClosedLotsTable.svelte` (o un solo file con 2 `<DataTable>`, a discrezione di chi implementa).
- Colonne esattamente come da `OpenLotSchema` (buy_date, buy_price, original/remaining_quantity,
  unrealized_pnl) e `ClosedLotSchema` (buy_date, sell_date, quantity, buy/sell_price, realized_pnl) di `GET
  /portfolio/lots` — nessun gap dati, **0 dipendenze da STEP 1**.
- Esporre/riusare il metodo pubblico `navigateToRowId()` di `DataTable.svelte` per il "Goto & Pulse" da 4.1.

### 4.3 `AssetWacPriceChart.svelte` `[EUR|%]`

- **Nuovo file**: `frontend/src/lib/components/brokers/lots/AssetWacPriceChart.svelte`.
- Linee WAC vs prezzo mercato con switch `[EUR|%]` (EUR: `wac`/`market_price` assoluti; %: `roi`/`twrr`).
- Consuma `GET /portfolio/asset-history` — disponibile per `[EUR]` dopo 1.1; `roi`/`twrr` potrebbero essere
  `null` se 1.2 non ancora completato nello stesso run: gestire con stato vuoto/placeholder sul toggle `%`,
  nessun crash. Dipende da 1.1 (route deve esistere per sviluppo/test end-to-end).
- Risoluzione temporale fissa giornaliera — **non dipendere da `timeSeriesAggregation.ts`**.

---

## STEP 5 — Frontend: pannello inline (convergenza)

> ✅ **Note implementazione** (2026-07-10): completato, eseguito direttamente (non delegato a fleet, come
> previsto — task di convergenza singolo). Currency dell'asset (nativa, richiesta da tutti i componenti
> figli) recuperata da `assetStore` (`getAssetInfo(assetId)?.currency`, store già esistente e già usato da
> `ExposureTable` — non era esplicitato nel piano che questo store fosse la fonte, scoperta in
> implementazione: `PortfolioHolding`/`AssetPeriodContribution` NON portano la currency nativa, solo valori
> già convertiti in target/display currency). `ensureAssetsLoaded()` aggiunto al `Promise.all` di `onMount`
> della pagina broker. Stato `activeAssetId` sincronizzato bidirezionalmente con `?asset=` via un blocco
> reattivo `$:` (il file `brokers/[id]/+page.svelte` è interamente in sintassi Svelte legacy, non runes —
> mantenuta coerenza con lo stile esistente del file invece di introdurre `$state`/`$effect` solo qui).
> `PositionsPanel.svelte` estesa con forwarding `onAnalyze` (vedi nota STEP 3).

- **Nuovo file**: `frontend/src/lib/components/brokers/lots/FIFOLotsPanel.svelte` — pannello inline con
  `transition:slide` (prima adozione nel codebase; il precedente più vicino è `transition:fade` in
  `BrokerImportFilesModal.svelte`, area upload). Assembla 4.1 + 4.3 + 4.2, collega bubble→tabella via
  `navigateToRowId()`.
- **Wiring**: `frontend/src/routes/(app)/brokers/[id]/+page.svelte`, tab Posizioni. Stato apertura pilotato
  da query-param `?asset=<id>` (helper 2.2). Le callback `onAnalyze` di 3.1/3.2 aprono il pannello passando
  `asset_id` (dalla riga/tile/barra cliccata) + `broker_id` (fisso di pagina).

---

## STEP 6 — i18n + validazione finale

> ✅ **Note implementazione** (2026-07-10): completato. i18n audit → 100% coverage (1530/1530 chiavi, +2
> nuove: `brokers.lots.detailTitle`/`brokers.lots.loadFailed`, aggiunte sotto lo stesso namespace nidificato
> `brokers.lots.*` già stabilito dai componenti STEP 4 — non il namespace flat originariamente usato in una
> prima stesura di `FIFOLotsPanel.svelte`, corretto per coerenza). Pytest backend: 23/23 su
> `test_portfolio_api.py` (intero file, nessuna regressione sulle classi pre-esistenti). Svelte-check: 0
> errori. Vitest: 10/10. E2e: 4 nuovi test in `brokers-detail.spec.ts` (apertura da click, chiusura +
> query-param, dblclick invariato, switch `[EUR|%]`) — tutti passano contro dati reali dell'utente di test.
> Vedi "Rischi / note aperte" sotto per un bug e2e pre-esistente scoperto (non introdotto da questa fase).

- `./dev.py i18n audit` dopo STEP 5, aggiungere le chiavi mancanti (titoli pannello, switch `[EUR|%]`,
  empty states, tooltip bubble, header tabelle lotti) nelle 4 lingue (EN/IT/FR/ES).
- Pytest backend mirato (asset-history, lots, roi/twrr). Svelte-check + lint/format frontend sui file
  toccati. E2e Playwright: estendere `frontend/e2e/brokers/brokers-detail.spec.ts` (apertura pannello da
  riga/tile/barra, click vs dblclick, switch `[EUR|%]`, "Goto & Pulse").
- Aggiornare questo documento con "✅ Note implementazione" per ogni step completato (convenzione repo).
- Aggiornare `README.md` di Milestone_3 (riga Fase 2 → stato implementato).

---

## Riepilogo componenti riusati (invariati)

`PositionsPanel` (montato in Fase 1) · `ExposureTable`/`ContributionTable`/`ExposureTreemap`/
`PerformanceChart` (estesi con click, non ricreati) · `<DataTable>` (`onRowClick`, `navigateToRowId()`) ·
`GET /portfolio/lots` (invariato) · `queryParams.ts` (`getOptionalNumberParam`/`setOptionalNumberParam`) ·
`calculate_simple_roi_series`/`calculate_twrr_series` (`roi_utils.py`, invariati) · pattern
`goto(...,{replaceState:true})` di `files/+page.svelte`.

## Componenti nuovi (minimi, motivati)

`clickVsDblClick.ts` (guard, 1 solo precedente nel codebase da evitare di duplicare 4 volte) ·
`assetPanelUrl.ts` (wrapper sottile) · `BubbleLotTimeline.svelte` · `AssetWacPriceChart.svelte` ·
`OpenLotsTable.svelte`/`ClosedLotsTable.svelte` · `FIFOLotsPanel.svelte`.

## Componenti ritirati

Nessuno in questa fase.

## Rischi / note aperte

- **🆕 Bug e2e pre-esistente scoperto (fuori scope, non corretto qui, solo segnalato)**: il test
  `broker detail page shows holdings section` (`frontend/e2e/brokers/brokers-detail.spec.ts:97`, non
  toccato da questa fase né da Fase 3) fallisce — verifica `broker-holdings` visibile senza prima navigare
  al tab Posizioni, ma quel blocco è gated dietro `activeTab === 'posizioni'` da quando Fase 1 ha introdotto
  la shell a tab (il default è `panoramica`). Il test non è mai stato aggiornato per quel redesign — stessa
  categoria di problema già risolto per `import-files-button` in Fase 3, ma questo caso specifico è rimasto
  indietro. **Non corretto in questa fase** (fuori dallo scope assegnato, per convenzione va segnalato non
  adattato silenziosamente) — richiede una riga `await goToPosizioniTab(page)` prima dell'assert, stesso
  fix già applicato altrove nello stesso file.
- `AssetWacPriceChart` sviluppato/testato prima che 1.2 fosse pronto avrebbe mostrato `[%]` vuoto — non
  accaduto nella pratica (1.2 e 4.3 sono finiti nello stesso giro di esecuzione), ma il fallback resta in
  piedi per run futuri.
- Non toccare `timeSeriesAggregation.ts` né i componenti chart attualmente in WIP su un'altra sessione
  (`GrowthChart`, `PriceChartFull`, `CandlestickChart`, `AllocationHistoryChart`) — fuori scope. **Nota**:
  un comando `./dev.py front format` lanciato senza scoping durante questa fase ha riformattato (solo
  whitespace/quote, nessuna modifica semantica) alcuni di questi file in WIP — nessun contenuto perso, ma
  da evitare in futuro: preferire sempre `npx prettier --write <file-list>` scoped ai soli file della fase
  corrente.
- Dopo ogni modifica di schema/endpoint backend (STEP 1): `./dev.py api sync` prima di toccare il frontend
  che li consuma (4.3).

---

## Evoluzione multi-broker (2026-07-11)

Richiesta utente: il pannello Lotti FIFO era scoped a 1 solo broker (limite architetturale reale, non
capriccio: `get_lots()` richiedeva `broker_id: int` obbligatorio, `get_asset_history()` pescava "primo
broker accessibile" se omesso). Evoluto per accettare **liste** di broker, con lotti sempre taggati
per-broker (colonna + tinta riga/bolla, mai un merge FIFO cross-broker: FIFO resta un concetto
per-account) e una **serie WAC combinata** aggiuntiva per il grafico WAC/Prezzo quando >1 broker (WAC
è matematicamente "mergeable" — quantità/costo cumulativi — a differenza dell'ordine dei lotti FIFO).

### Decisioni prese

| Decisione | Scelta |
|---|---|
| Forma dati WAC multi-broker | Lista piatta con `broker_id` per punto (stesso pattern dei lotti); `broker_id=null` = serie combinata, presente solo se `len(broker_ids) > 1` |
| Scope pannello in Broker Detail | Resta single-broker (`brokerIds=[broker.id]`, invariato nello spirito) |
| Default Dashboard senza filtro broker attivo | Tutti i broker accessibili (`activeBrokerIds ?? allBrokers.map(b => b.id)`) |
| Lotti FIFO cross-broker | **Mai mergiati** — ogni lotto appartiene a esattamente 1 broker, tag `broker_id` per riga/bolla |

### Ordine di implementazione eseguito (fleet)

```
mb1 (nuova funzione WAC multi-broker)  mb2 (GET /lots multi-broker)
         │                                      │
         ▼                                      ├──────────┬──────────┐
mb3 (GET /asset-history multi-broker)           ▼          ▼          │
         │                              mb4 (tabelle)  mb5 (bubble)   │
         ▼                                      │          │          │
mb6 (grafico WAC per-broker+combinato) ─────────┴──────────┴──────────┘
         │
         ▼
mb7 (FIFOLotsPanel convergenza) → mb8 (wiring pagine) → mb9 (i18n/e2e/doc)
```

### Note implementazione

> ✅ **mb1** — nuova `compute_wac_iterative_multi_broker()` (sibling di `compute_wac_iterative`, MAI
> modificata: 6 call-site esterni troppo rischiosi da toccare), query `Transaction.broker_id.in_(broker_ids)`,
> cache key su tupla ordinata. Test di coerenza vs merge manuale + `compute_wac_from_txlist()`. 36/36 test.

> ✅ **mb2** — `OpenLotSchema`/`ClosedLotSchema` + campo `broker_id: int` (sempre popolato, mai null: ogni
> lotto è di 1 broker). `get_lots()` firma `broker_ids: list[int] | None` (None → tutti i broker
> accessibili). Route `GET /lots?broker_ids=1&broker_ids=2` (repeated query param, stesso stile di
> `query_transactions`'s `ids`). 6/6 test nuova classe.

> ✅ **mb3** — `AssetHistoryPoint` + campo `broker_id: Optional[int]` (`None` = combinata). `get_asset_history()`
> aggiunge la serie combinata solo se `len(broker_ids) > 1`, via `compute_wac_iterative_multi_broker` (mb1)
> + merge di `NAVSnapshot`/`CashFlowInput` cross-broker per roi/twrr combinati. 27/27 test sul file completo
> (incluse le classi pre-esistenti, nessuna regressione).

> ✅ **mb4** — `OpenLotsTable`/`ClosedLotsTable` + prop `brokers`, colonna Broker (stesso pattern
> `brokerColumn` di `ExposureTable`), tinta riga via `getRowStyle`/`getRowClass` + CSS custom properties
> (stesso pattern `brokerStyle()` di `TransactionsTable`, copiato non condiviso — Svelte scoped styles).

> ✅ **mb5** — `BubbleLotTimeline` + prop `brokers`, colore bolla = `getBrokerColor(lot.brokerId, brokers)`
> (light/dark branch), distinzione aperto/chiuso (anello tratteggiato) mantenuta ortogonale al colore.
> Tooltip con nome broker.

> ✅ **mb6** — `AssetWacPriceChart`: prop `brokerId`→`brokerIds`+`brokers`. Raggruppa la risposta piatta per
> `broker_id`: N linee WAC/ROI/TWRR colorate per broker + 1 linea "Combinato" (tratteggiata, colore neutro,
> nuova chiave i18n `brokers.lots.combined`) quando presente. Market Price deduplicato (1 sola linea,
> presa da un gruppo per-broker qualsiasi, mai dal gruppo combinato).

> ✅ **mb7** — `FIFOLotsPanel` (convergenza, eseguito direttamente non da fleet): prop `brokerId`→
> `brokerIds`+`brokers`, propagati a tutti i 4 figli. Verificato: `buy_transaction_id`/`sell_transaction_id`
> sono PK globali del DB, nessuna collisione possibile tra broker nella risoluzione "Goto & Pulse".

> ✅ **mb8** — Wiring pagine (eseguito direttamente). `brokers/[id]/+page.svelte`: `brokerIds={[broker.id]}`
> + `brokers={panelBrokers}` (banale, 1 riga). `dashboard/+page.svelte` (Svelte 5 runes, sintassi diversa
> dalla pagina broker legacy — usato `$state`/`$effect` coerentemente): nuovo `onAnalyze` su
> `<PositionsPanel>` (non wired prima), nuovo `<FIFOLotsPanel>` con `brokerIds={activeBrokerIds ?? allBrokers.map(b => b.id)}`,
> `ensureAssetsLoaded()` aggiunto a `onMount`. `goto` era già importato in quel file, riusato as-is.

> ✅ **mb9** — i18n 100% (1531 chiavi). **Regressione trovata e corretta**: 4 test in
> `test_financial/test_portfolio_service.py::TestPortfolioServiceGetLots` chiamavano `service.get_lots()`
> direttamente con la vecchia kwarg `broker_id=<int>` (non passando per l'API, quindi non coperti dai test
> di mb2) — sistemati in `broker_ids=[<int>]`. 63/63 test backend (2 file) dopo il fix. Svelte-check: 0
> errori. E2e `brokers-detail.spec.ts`: 15/16 (1 fallimento pre-esistente non correlato, già segnalato
> sopra). Nessun e2e Dashboard aggiunto (nessun file spec esistente da estendere, architettura condivisa
> già validata via Broker Detail — valutato non necessario nel tempo a disposizione).

---

## Rifiniture UX (2026-07-12)

5 correzioni segnalate dopo review del pannello: (1) assi X non condivisi tra i 2 grafici, (2) pallini
legenda vuoti, (3) bolle poco leggibili vicino allo zero, (4) meccanismo click/dblclick da rimuovere in
favore di context-menu + colonna azioni (anche fix di un bug: click su `PerformanceChart` non aggiornava
nulla), (5) tabelle Lotti Aperti/Chiusi non foldable.

### Decisioni prese

| Decisione | Scelta |
|---|---|
| Meccanismo interazione righe/tile/barre | **Rimosso** click singolo/doppio ovunque (Dashboard+Broker Detail, tabelle+grafici) — solo right-click (menu contestuale) + colonna azioni (solo tabelle) |
| `clickVsDblClick.ts` | **Rimosso** (dead code dopo la rimozione di tutti i consumer) |
| Bubble Timeline "Goto & Pulse" | **Invariato** — non in conflitto con click/dblclick, meccanismo diverso (naviga dentro il pannello già aperto, non lo apre) |
| Range X condiviso | Unione dei 2 range (asset-history + date lotti), calcolata da `FIFOLotsPanel` (il genitore comune), iniettata in entrambi i grafici |
| Fold lotti | Default espanso se ha righe, chiuso se vuoto; si ricalcola ad ogni asset diverso (non persiste la scelta manuale tra asset) |

### Note implementazione

> ✅ **ux1** (`AssetWacPriceChart`) — `symbol: 'circle'` aggiunto a tutte le serie linea (fix legenda:
> causa era il default ECharts `emptyCircle` per le serie `line` anche con `showSymbol:false`). Nuova prop
> `onRangeComputed?: (min,max)=>void` (riporta il range della propria serie fetchata) + `xAxisRange?:
> {min,max}|null` (override del range asse X). 0 errori.

> ✅ **ux2** (`BubbleLotTimeline`) — accetta `xAxisRange` (stesso contratto di ux1). Nuovo indicatore zero:
> 1 serie scatter `__zero-dot` (puntino pieno fisso 5px, colore da `pnlColor()` esistente, silent, z alto)
> + N serie line `__zero-connector-*` (una per lotto, tratteggiata, stesso colore, silent) — layer
> puramente additivo, bolle broker-colorate esistenti invariate. 0 errori.

> ✅ **ux3** (`FIFOLotsPanel`, coordinatore) — calcola `lotsRange` da `openLots`/`closedLots` già in mano +
> riceve `assetHistoryRange` via `onRangeComputed` da `AssetWacPriceChart`, unisce i 2 in `sharedXAxisRange`,
> lo inietta in entrambi i grafici. Contratto pre-fissato con ux1/ux2 (girati in parallelo senza attese
> reciproche) — verificato integrarsi correttamente a valle. 0 errori.

> ✅ **ux4** (`ExposureTable`+`ContributionTable`) — rimosso `createClickGuard`/`onRowClick`/
> `onRowDoubleClick`. Attivata infra **già esistente e disattivata** in `DataTable.svelte`
> (`enableActions`/`enableContextMenu` erano `false`) con 2 `rowActions` (Vedi Asset/Analizza Lotti) — zero
> nuova infra tabella, solo attivazione. Uniche 2 chiavi i18n nuove (`brokers.lots.viewAsset`/`analyze`)
> scritte qui (unico task che tocca i 4 JSON in questo round, per evitare collisioni tra agenti paralleli).

> ✅ **ux5** (`ExposureTreemap`) — rimosso guard/listener click+dblclick, aggiunto `chartInstance.on(
> 'contextmenu', ...)` (evento nativo ECharts, verificato nei type-def) + `ContextMenu.svelte` (stesso
> componente già usato da `DataTable`, generico a coordinate pixel). Coordinate da `params.event.event.
> clientX/clientY` + `preventDefault()`.

> ✅ **ux6** (`PerformanceChart`) — stesso pattern di ux5. **Il bug segnalato ("click non aggiorna nulla")
> è risolto come effetto collaterale** della riscrittura (l'intero meccanismo click/dblclick difettoso è
> stato rimosso, non solo patchato).

> ✅ **ux7** (cleanup) — verificato via grep 0 usi residui di `createClickGuard`/`clickVsDblClick` fuori dal
> file stesso, rimossi `clickVsDblClick.ts` + il suo test + la cartella `utils/interaction/` (vuota dopo).

> ✅ **ux8** (`OpenLotsTable`/`ClosedLotsTable`) — header cliccabile (chevron+titolo+badge conteggio) che
> wrappa il contenuto in `{#if expanded}` + `transition:slide`. Default ricalcolato ad ogni cambio di
> `lots` (nuovo asset). `navigateToRowId()` (usato da "Goto & Pulse") auto-espande la sezione se era chiusa,
> prima di forwardare la chiamata alla `<DataTable>` interna — altrimenti la riga evidenziata resterebbe
> invisibile.

> ✅ **ux9** (validazione finale) — i18n 100% (1533 chiavi). Svelte-check + prettier: 0 errori su tutto il
> set toccato. E2e: i 4 test Fase-2 che testavano click/dblclick **riscritti** per il nuovo meccanismo
> (click sull'icona in colonna azioni + 1 nuovo test dedicato al right-click/context-menu) — 5/5 pass
> contro dati reali. Suite completa `brokers-detail.spec.ts`: 16/17 (unico fallimento il bug pre-esistente
> di Fase 1 già segnalato, non correlato a questo round).

---

## Rifiniture Round 3 (2026-07-12)

8 correzioni segnalate dopo ulteriore review: (1) trigger bolle click→doppio click, (2) scroll automatico
all'apertura pannello, (3) filtro broker "reali" nel grafico WAC, (4) filtri periodo non applicati a lotti
e grafici, (5) `ColumnVisibilityToggle` nelle tabelle lotti, (6-7) legenda bolle fuorviante rimossa +
legenda broker sotto, (8) rename etichette toggle Posizioni→Portafoglio/Performance→Periodo.

### Decisioni prese (confermate dall'utente)

| Decisione | Scelta |
|---|---|
| Semantica periodo per lotti/WAC | **Snapshot "as of date_to"** (come Holdings) — FIFO calcolato con tutte le transazioni fino a `date_to`, lotti vecchi ancora aperti restano visibili anche filtrando a periodi corti |
| Fix legenda bolle | Rimossi gli swatch colore fittizi Aperto/Chiuso + aggiunta legenda colori-broker (solo se ≥2 broker) |
| Etichette toggle Posizioni/Performance | "Portafoglio" / "Periodo" (4 lingue) |

### Note implementazione

> ✅ **r1** (`BubbleLotTimeline`) — trigger `onLotClick` da `click` a `dblclick` (nessun guard necessario,
> rimosso in un round precedente — il click singolo ora non fa nulla di custom, resta il tooltip hover
> ECharts). Rimossa `legend.data:[openLabel,closedLabel]` (swatch fittizi). Nuova legenda HTML
> `data-testid="bubble-broker-legend"` sotto il grafico, solo se ≥2 broker distinti nei lotti presenti,
> colore da `lotBrokerColor()` già esistente (stesso colore delle bolle grandi).

> ✅ **r2** (`DataTable.svelte`, beneficio condiviso app-wide) — `.highlighted` (Goto & Pulse) ora pulsa
> 3 volte in 1.8s (intensità background, non box-shadow) prima di assestarsi sul colore statico esistente,
> stessa palette viola invariata. Guard `prefers-reduced-motion` aggiunto.

> ✅ **r3** (backend) — `get_lots()`/`GET /portfolio/lots` + `as_of_date` opzionale, riusa
> `_get_transactions(date_to=as_of_date)` già esistente (zero nuova query logic). `./dev.py api sync`
> eseguito (necessario per il nuovo query param — gap scoperto e corretto durante la validazione finale,
> il task backend non lo aveva incluso). 28/28 test sul file completo.

> ✅ **r4** (`OpenLotsTable`/`ClosedLotsTable`) — `<ColumnVisibilityToggle>` nell'header, a destra,
> separata (sibling, non annidata) dal bottone fold/unfold per evitare toggle accidentali.

> ✅ **r5** (`FIFOLotsPanel`, coordinatore) — scroll-into-view su apertura/cambio asset (con `tick()` per
> attendere il mount condizionale). `realBrokerIds` derivati da `openLots`+`closedLots` passati solo ad
> `AssetWacPriceChart` (non a `BubbleLotTimeline`, che non ne ha bisogno) — corregge automaticamente anche
> la soglia "Combinato" lato backend, zero modifiche là. Nuove prop `dateFrom`/`dateTo`/`isAllPeriod`:
> `as_of_date` sul fetch lotti, `sharedXAxisRange` diventa `{dateFrom,dateTo}` diretto quando non "All"
> (altrimenti logica di unione invariata dal round precedente).

> ✅ **r6** (2 pagine) — `brokers/[id]/+page.svelte` (legacy) riusa `dateFrom`/`dateTo`/`isMaxPending` già
> esistenti; `dashboard/+page.svelte` (runes) riusa `dateRangeCtl.start`/`.end`/`.activePreset==='MAX'`
> già esistenti — zero nuovo stato, solo forwarding.

> ✅ **r7** (validazione finale) — rename i18n 4 lingue (100% coverage, 1533 chiavi invariate). Svelte-check
> 0 errori, prettier pulito su tutto il set. Pytest 28/28. E2e 16/17 (stesso fallimento pre-esistente non
> correlato). **Gap scoperto e corretto**: il task backend (r3) non aveva eseguito `./dev.py api sync` —
> senza, `FIFOLotsPanel` non poteva passare `as_of_date` al client TS generato (errore di tipo). Eseguito
> qui in chiusura, verificato 0 errori dopo.
