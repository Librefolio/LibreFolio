# Plan — Phase 07 · Part 4 · Round 2 — Tabella refactor + Cache entity bugfix

**Date**: 2026-04-27
**Status**: ✅ COMPLETATO (Step 1–6 ✅; Step 3 ✅ currency-stack per-valuta; Step 7 deferito — test E2E entity-cache-refresh; Step 8 ✅ cross-link)
**Priority**: P1 (regressioni UX + bug latente cache cross-pagina)
**Estimated effort**: ~1 day

**Parent plan**: [`plan-phase07-transaction-Part4.prompt.md`](./plan-phase07-transaction-Part4.prompt.md)
**Predecessor**: [`plan-phase07-transaction-Part4_Round1-tableRefactorBugfix.prompt.md`](./plan-phase07-transaction-Part4_Round1-tableRefactorBugfix.prompt.md) (Round 1 ✅)

---

## 🎯 Obiettivo

Chiudere i bug emersi al walkthrough finale di Round 1 e generalizzare la gestione cache delle entità (asset/broker) con un **pattern condiviso** invocabile in futuro per qualunque entità "lista bounded + lookup by id". In particolare:

- Tooltip/visualizzazione valuta consistente con il resto dell'app (`$ 🇺🇸 USD`).
- Eliminare i `title=""` HTML nativi nelle celle TX, usando solo [`Tooltip.svelte`](../../frontend/src/lib/components/ui/Tooltip.svelte).
- Filtro `currency-stack` con titolo ricco e min/max **per-valuta** (bug riproducibile anche su `assets/lastPrice`).
- Linked-pair: pair-grouping/forced-pagination **solo** quando filtri+sort sono inattivi; con filtri/sort attivi le ghost rows diventano righe ordinarie.
- Risolvere la cache stantia `assetStore` (mai invalidata dai mutation callsite) introducendo `createEntityStore<T>()` riusato per asset e nuovo `brokerStore`.

**Esplicitamente fuori scope**:
- Modifiche all'API di `DataTable` per supportare tooltip multipli interni (decisione: il refactor sta lato consumer).
- Migrazione di `fxStoreRegistry` (è un caso diverso — TimeSeriesStore con gap-detection).
- Nuovi endpoint backend.

---

## 🐞 Issues raccolte

| ID | Severity | Descrizione | Step |
|----|----------|-------------|------|
| R2-1 | ⚠ UX | Tooltip evento in `/transactions` mostra `1,000.00 USD` invece di `1,000.00 $ 🇺🇸 USD`. Causa: `currencyStore` non caricato → `getCurrencyInfo` ritorna fallback con `symbol = code` e flag `🏳️` | 1 |
| R2-2 | ⚠ UX | Su hover prolungato compare il tooltip nativo del browser (HTML `title=`) sopra/al posto di `<Tooltip>`. Celle interessate: `cash`, `links` (event-dot + link-icon), `broker` | 2 |
| R2-3 | ⚠ UX | Pannello filtro `currency-stack`: titolo riga è solo `EUR`/`USD` (no flag/simbolo); il dual-slider min/max usa il range globale della colonna anziché il range della singola valuta. Lo stesso bug si vede in `/assets` colonna "ultimo prezzo" | 3 |
| R2-4 | ⚠ UX | Le righe linked-pair forzano la coabitazione nella stessa pagina e l'ordinamento le tiene insieme: l'utente vuole righe normali, raggruppate solo a filtri+sort vuoti | 4 |
| R2-5 | ❌ bug | Modificando l'icona di un asset il frontend non la aggiorna fino a F5. Causa: `assetStore.invalidateAfterMutation` mai chiamato dai callsite di `AssetModal`. Latente anche su brokers (nessuno store: i fetch ad-hoc cross-page non si parlano) | 5–6 |

---

## 📋 Steps

### Step 1 — Tooltip valuta evento TX

- In [`+page.svelte`](../../frontend/src/routes/(app)/transactions/+page.svelte) `onMount`: `await ensureCurrenciesLoaded($language);`
- In [`TransactionsTable.svelte`](../../frontend/src/lib/components/transactions/TransactionsTable.svelte): nei cell builder che chiamano `formatCurrencyAmountPlain`/`formatCurrencyAmountHtml` aggiungere `void $currencyStoreVersion` per re-trigger quando le valute caricano async dopo il primo render.
- Verificare che l'event-dot tooltip e i tooltip sui cash cell mostrino `1,000.00 $ 🇺🇸 USD`.

### Step 2 — Eliminare `title=""` nativi (refactor lato consumer)

- In [`TransactionsTable.svelte`](../../frontend/src/lib/components/transactions/TransactionsTable.svelte) trasformare le tre colonne `cash`, `links`, `broker` da `HtmlCell` (con `title=...` inline) a **`CustomCell` con snippet Svelte**.
- Lo snippet monta istanze reali di [`Tooltip.svelte`](../../frontend/src/lib/components/ui/Tooltip.svelte), uno per elemento interattivo:
  - `cash`: 1 Tooltip wrapping `tx-cash-cell`.
  - `links`: 2 Tooltip distinti — uno su `tx-event-dot` (testo da `eventTooltipText`), uno su `tx-link-icon` (testo da `linkedPairTooltip`).
  - `broker`: 1 Tooltip wrapping `tx-broker-cell`.
- **Zero modifiche** a `DataTable`, `DataTableColumnFilter`, o all'union `CellContent`.

### Step 3 — Filtro `currency-stack`: titolo ricco + min/max per-valuta

- In [`DataTable.svelte`](../../frontend/src/lib/components/table/DataTable.svelte) aggiungere `getCurrencyMinMaxByCode(column): Map<string,{min,max}>` (analogo a `getColumnMinMax`, ma usa `getCurrencyValue` per indicizzare per `code`). Passare la mappa al filter come nuova prop `currencyMinMaxByCode`.
- In [`DataTableColumnFilter.svelte`](../../frontend/src/lib/components/table/DataTableColumnFilter.svelte):
  - Sostituire `<span class="currency-stack-code">{item.code}</span>` con rendering `simbolo + 🇺🇸 + codice` via `getCurrencyInfo` (riusare il pattern di `formatCurrencyAmountHtml` o estrarre `formatCurrencyCodeHtml` in [`utils/currencyFormat.ts`](../../frontend/src/lib/utils/currencyFormat.ts)).
  - Nel range editor della singola riga, leggere `currencyMinMaxByCode.get(item.code)` invece di `numberMin`/`numberMax` globali. Etichette slider e tick devono riflettere il range della valuta selezionata.
- Validare anche su [`AssetTable.svelte`](../../frontend/src/lib/components/assets/AssetTable.svelte) (colonna `lastPrice`).

### Step 4 — Linked-pair condizionale + esporre `sortState`

- In [`DataTable.svelte`](../../frontend/src/lib/components/table/DataTable.svelte) aggiungere prop `onSortChange?: (state: SortState | null) => void` invocata quando `sortState` viene aggiornato (linee ~508–515).
- In [`TransactionsTable.svelte`](../../frontend/src/lib/components/transactions/TransactionsTable.svelte) tracciare `let activeSort = $state<SortState | null>(null)` collegato al callback.
- Modificare `displayRows`/`pages`:
  - Se `Object.keys(activeColumnFilters).length === 0 && activeSort == null` → comportamento attuale (giver+receiver adiacenti, paginator `wouldSplitPair`).
  - Altrimenti → emettere ghost rows come righe indipendenti, ordinate dal `DataTable` con le altre, paginazione standard.
- Frecce ⬇/⬆ e badge `tx-row-receiver` restano sempre visibili: il tooltip risolve l'ambiguità a distanza.

### Step 5 — Pattern condiviso `createEntityStore<T>()`

- Creare [`stores/entityStore.ts`](../../frontend/src/lib/stores/entityStore.ts):
  ```text
  createEntityStore<T, Id>({
      loader: () => Promise<T[]>,
      getId: (item) => Id,
      normalize?: (raw) => T,
      requiredFields?: (keyof T)[],     // skip merge se mancano
  }): {
      ensureLoaded(...args): Promise<void>,
      refreshAll(): Promise<void>,
      get(id): T | null,
      getAll(): T[],
      merge(items: ReadonlyArray<Partial<T> | Record<string, unknown>>): void,
      invalidate(idOrIds: Id | ReadonlyArray<Id>): void,   // setta loaded=false se rimuove
      version: Readable<number>,
      isLoaded(): boolean,
  }
  ```
- **Bug fix integrato**: `invalidate` deve resettare `loaded = false` quando rimuove entry (il bug attuale di `assetStore` è proprio che `ensureAssetsLoaded` resta no-op dopo invalidate).
- Refactorare [`assetStore.ts`](../../frontend/src/lib/stores/assetStore.ts) come istanza del factory mantenendo l'API pubblica esistente (`ensureAssetsLoaded`, `getAssetInfo`, `mergeAssets`, `invalidateAfterMutation`, `refreshAllAssets`, `assetStoreVersion`) per non rompere callsite. Conservare il `normalize()` esistente (flatten Zod artifacts).
- Creare [`stores/brokerStore.ts`](../../frontend/src/lib/stores/brokerStore.ts) come seconda istanza: campi `{id, name, icon_url, portal_url, default_import_plugin}`. Esporre `ensureBrokersLoaded`, `getBrokerInfo`, `getAllBrokers`, `mergeBrokers`, `invalidateBroker`, `refreshAllBrokers`, `brokerStoreVersion`.
- Migrare i 3 callsite a `brokerStore`:
  - [`/transactions/+page.svelte`](../../frontend/src/routes/(app)/transactions/+page.svelte)
  - [`/files/+page.svelte`](../../frontend/src/routes/(app)/files/+page.svelte)
  - [`/brokers/+page.svelte`](../../frontend/src/routes/(app)/brokers/+page.svelte)

  Ogni callsite usa `ensureBrokersLoaded()` + lettura via `getAllBrokers()` reagendo a `$brokerStoreVersion` (no più `let brokers = $state([])` locale).

### Step 6 — Wire-up invalidazione nei callsite di mutation

In [`AssetModal.svelte`](../../frontend/src/lib/components/assets/AssetModal.svelte):
- `saveCreate` post-success: `mergeAssets([{id: result.asset_id, ...createPayload}])` (la response BE porta solo `asset_id`, ma il FE conosce i campi inviati).
- `saveEdit` post-success: `mergeAssets([{id: assetId, ...patchItem}])` (idem; merge upserta sui campi cached).
- Currency-change wipe-confirm flow: idem, dopo il PATCH retry.

In [`/assets/+page.svelte`](../../frontend/src/routes/(app)/assets/+page.svelte) e [`/assets/[id]/+page.svelte`](../../frontend/src/routes/(app)/assets/[id]/+page.svelte):
- Su delete asset → `invalidateAfterMutation(id)`.
- Su wipe asset → `invalidateAfterMutation(id)` + `refreshAllAssets()` se i campi `has_metadata` sono cambiati.

In [`BrokerModal.svelte`](../../frontend/src/lib/components/brokers/BrokerModal.svelte) (e callsite delete in `/brokers`): pattern speculare con `mergeBrokers` / `invalidateBroker`.

### Step 7 — Test E2E mirato (regression guard)

- Aggiungere test Playwright in [`e2e/`](../../frontend/e2e/) (file dedicato `entity-cache-refresh.spec.ts`):
  1. Apre `/assets`, modifica icona di un asset (upload nuova), conferma → l'icona aggiornata appare in `AssetCard` **senza F5**.
  2. Naviga a `/transactions` → la cella asset della relativa transazione mostra la nuova icona.
  3. Idem per broker: modifica icona broker → `/transactions` cella broker e `/files` la mostrano aggiornata.
- Selettori via `data-testid` (mai testo/CSS).

### Step 8 — Naming, cross-link, archive

- Forward-link da Round 1 nella sezione "Successor": → `Round 2`.
- Back-link da questo file → Round 1 e Part 4.
- Quando completato, header `Status: ✅ COMPLETED`, archiviare con `plan-archive` skill nella struttura `phases/phase-07-subplan/Bugfix-Step5/Round2/`.

---

## 📦 Deliverables

- Modifiche: `+page.svelte` transactions, `TransactionsTable.svelte`, `DataTable.svelte`, `DataTableColumnFilter.svelte`, `AssetModal.svelte`, `BrokerModal.svelte`, `/assets/+page.svelte`, `/assets/[id]/+page.svelte`, `/brokers/+page.svelte`, `/files/+page.svelte`.
- Nuovi file: `stores/entityStore.ts`, `stores/brokerStore.ts`, `e2e/entity-cache-refresh.spec.ts`.
- `assetStore.ts` refactorato come istanza factory (API pubblica invariata).
- Eventuale helper `formatCurrencyCodeHtml` in `utils/currencyFormat.ts` (estratto se utile).

## 🔍 Verification

- `./dev.py front lint` + `./dev.py front type-check` puliti.
- Walkthrough manuale: replicare i 5 issue R2-1…R2-5 e verificare risoluzione.
- Test Playwright `entity-cache-refresh.spec.ts` PASS in CI.

## 📝 Wiki

A fine round, registrare in `LibreFolio_devWiki/`:
- Pagina concept `entity-store-pattern.md` (factory + invariante "invalidate resets loaded").
- Aggiornare entity page `assetStore` e creare `brokerStore`.
- Decisione: "Tooltip nelle celle DataTable → solo via CustomCell snippet, mai via `title=` HTML".

---

## 🐞 Round 2.5 — Feedback dal walkthrough (2026-04-28)

| ID | Severity | Descrizione | Fix applicato |
|----|----------|-------------|---------------|
| R2.5-1 | ⚠ UX | Tooltip `<Tooltip.svelte>` sulla cella `cash` mostra esattamente lo stesso contenuto della cella — ridondante e inutile. | ✅ Rimosso: la cella `cash` ora è un semplice `HtmlCell` senza wrapper `TxTooltipCell`. Rimossa anche la funzione morta `formatCash()`. |
| R2.5-2 | ⚠ UX | Con sort attivo, le transazioni linked (ghost receiver) venivano ancora appese in fondo alla pagina anziché ordinarsi normalmente. Causa: `TransactionsTable` pre-paginava e poi passava la slice a `DataTable` che sortava solo all'interno della pagina. | ✅ In flat mode (`isGrouped=false`, cioè sort/filtri attivi) ora `visibleRows = displayRows` (dataset completo) e `enablePagination={!isGrouped}` — DataTable gestisce sort+filter+pagination internamente. In grouped mode resta il paginator custom pair-never-split. L'external `DataTablePagination` si mostra solo in grouped mode. |
| R2.5-3 | ✅ OK | Immagini asset/broker si aggiornano immediatamente dopo modifica (Step 5-6 funzionanti). | — |
| R2.5-4 | ⚠ UX | Cursore min/max nel filtro `currency-stack` si ricalcolava man mano che il filtro restringeva i dati. I boundary devono essere calcolati rispetto il dataset totale (mainRows + partnerRows), non la vista filtrata. | ✅ Aggiunta prop `fullData?: T[]` a `DataTable`. `getColumnMinMax()` e `getCurrencyMinMaxByCode()` ora usano `boundaryData = fullData ?? data`. `TransactionsTable` passa `fullData={displayRows}` (intero dataset senza filtri). |

### Cose ancora da testare

- [ ] Verificare che il sort in flat mode pagini correttamente con DataTable interno (cambiare pagina, cambiare page-size).
- [ ] Verificare che il toggle grouped↔flat (click sort → click sort per toglierlo) ripristini correttamente il paginator custom.
- [ ] Testare filtro `currency-stack` su `/assets` (colonna "ultimo prezzo") — il boundary deve essere stabile.
- [ ] Step 7 (E2E test `entity-cache-refresh.spec.ts`) — ancora da implementare.

---

## 🐞 Round 3 — Feedback walkthrough (2026-04-28)

| ID | Severity | Descrizione | Fix applicato |
|----|----------|-------------|---------------|
| R3-1 | ⚠ UX | Paginatore esterno (grouped mode) non si aggiorna quando "show selected only" è attivo in DataTable — totalItems resta il count totale, non filtra per selezione. In altre tabelle funziona perché DataTable gestisce pagination internamente. | ✅ Aggiunto `onShowSelectedOnlyChange` callback in `DataTable`. TransactionsTable traccia `showSelectedOnlyActive` + `selectedIdSet` e computa `externalPaginatorTotal` che filtra `filteredDisplayRows` per selezione quando attivo. |
| R3-2 | ⚠ UX | Pulse/navigazione al linked partner non funziona quando la transazione collegata è su un'altra pagina — `handleLinkedPairClick` trovava solo nel DOM corrente (pagina visibile). | ✅ Aggiunto `navigateToPartner(partnerId)` in TransactionsTable. In flat mode delega a `DataTable.navigateToRowId`. In grouped mode cerca la pagina nel pair-never-split paginator e naviga con `onPageChange`. `handleLinkedPairClick` in `+page.svelte` ora è async: tenta DOM lookup → se fallisce chiama `navigateToPartner` → attende render → pulse. |
| R3-3 | ✅ OK | Colonna "ultimo prezzo" funziona correttamente ora. | — |
| R3-4 | ℹ️ Info | Domanda: lo slider è logaritmico con range negativo→positivo? Risposta: lo slider per i numeri (cash, amount) usa scala **LINEARE** (`numToSliderPos`/`sliderPosToNum`). Solo il size filter (bytes) usa scala logaritmica. I range negativi funzionano nativamente con il mapping lineare. |
| R3-5 | ⚠ UX | I cursori min/max nello slider possono invertirsi (min > max). Anche se il clamping li corregge, UX confusa. | ✅ Clamping già presente; rafforzato con snap-to-extreme (vedi R3-6) che rende più facile raggiungere i confini. |
| R3-6 | ⚠ UX | Slider: arrotondamento impedisce di raggiungere esattamente min/max globali. Serve uno "snap" che agganci all'estremo se entro ~10px. | ✅ Aggiunta costante `SNAP = 3` (3 unità su 100 ≈ 7–10 px su trackbar ~250px). Applicata a tutti e 3 gli slider: number (`updateNumMin/MaxFromSlider`), size (`updateSizeMin/MaxFromSlider`), currency-stack (`updateCurrencyMin/MaxSlider`). Quando position ≤ SNAP → snap a 0 + value = boundary min. Quando position ≥ 100−SNAP → snap a 100 + value = boundary max. |

### Cose ancora da testare (Round 3)

- [x] Verificare che "show selected only" + paginator esterno funzioni: selezionare righe, attivare filtro, paginatore deve mostrare solo il count degli selezionati.
- [x] Testare pulse cross-page: in flat mode (sort attivo), cliccare 🔗 quando il partner è su altra pagina → deve navigare + pulse.
- [ ] Verificare snap slider su tutti e 3 i tipi (number, size, currency-stack).
- [ ] Verificare che l'inversione min/max sia prevenuta su tutti gli slider.

---

## 🐞 Round 3.5 — Feedback walkthrough slider (2026-04-28)

| ID | Severity | Descrizione | Fix applicato |
|----|----------|-------------|---------------|
| R3.5-1 | ⚠ UX | Range summary nella riga currency-stack mostra troppi decimali (`10799.72602739726`), allarga il panel con un flash. Causa: `item.min`/`item.max` mostrati raw senza formattazione. | ✅ Range summary ora usa `fmtNum()` → `10,800`. Aggiunta CSS `max-width: 120px` + `text-overflow: ellipsis` su `.currency-stack-range` per prevenire flash del panel. |
| R3.5-2 | ⚠ UX | `curSliderPosToNum` e `sliderPosToNum` producono 1 decimale per range > 100, ma per range > 1000 (es. 96→10800) servono interi. | ✅ Aggiunto case `if (range < 1000) ... else Math.round(raw)` in entrambe le funzioni. |
| R3.5-3 | ⚠ UX | Slider currency-stack: i pallini min/max possono ancora invertirsi visivamente. Causa: il currency slider usa `value={}` (one-way) — il browser ignora il clamp/snap durante il drag perché non è un `bind:value`. | ✅ I handler `updateCurrencyMinSlider` / `updateCurrencyMaxSlider` ora accettano `el: HTMLInputElement` e forzano `el.value = String(pos)` dopo il clamp. Il browser rispetta il valore forzato durante l'`oninput` e il thumb resta bloccato al confine dell'altro. |
| R3.5-4 | ⚠ UX | Snap: la barra si colora correttamente ma il thumb non si riallinea all'estremo al rilascio del mouse. Causa: snap posizionale durante `oninput` lotta col browser (ogni frame il browser riporta la posizione del mouse). | ✅ Strategia split oninput/onchange: durante `oninput` snap solo il VALORE (non la posizione) → niente jitter. Su `onchange` (mouseup) snap la POSIZIONE via `finalizeNumSliders`/`finalizeSizeSliders`/`finalizeCurrencySlider` → thumb salta all'estremo al rilascio. Applicato a tutti e 3 gli slider (number, size, currency-stack). |

### Cose ancora da testare (Round 3.5)

- [x] Verificare che il thumb snappa alla posizione 0 o 100 al rilascio del mouse (non durante il drag).
- [x] Verificare che il clamp previene inversione sul currency-stack slider (el.value forcing).
- [x] Verificare che i numeri nel range summary siano arrotondati (`fmtNum` → no decimali per valori > 1000).
- [x] Verificare che il panel non flashi più in larghezza con l'ellipsis CSS.

---

## 🐞 Round 4 — Icona tipo transazione: interazione mobile/desktop (2026-04-28)

| ID | Severity | Descrizione | Fix applicato |
|----|----------|-------------|---------------|
| R4-1 | ⚠ UX | L'icona tipo TX (`<a href>`) apriva la doc MkDocs al singolo click/tap su qualsiasi dispositivo. L'utente vuole: **desktop** → double click apre doc, single click solo tooltip. **Mobile** → long press apre doc, tap solo tooltip. | ✅ Creato `TxTypeIconCell.svelte` (CustomCell): sostituisce il `<a>` con `<span>` gestito da event handler. Desktop: `ondblclick` → `window.open(docUrl)`. Mobile: `ontouchstart` timer 500ms → `window.open(docUrl)`, cancellato su touchend/touchmove. Il Tooltip Svelte gestisce hover/tap per il nome tipo. Flag `suppressClick` previene il click spurio dopo un long-press riuscito. |

