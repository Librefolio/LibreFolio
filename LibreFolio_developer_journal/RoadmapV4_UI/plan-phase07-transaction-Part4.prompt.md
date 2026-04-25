# Plan — Phase 7 Part 4: `/transactions` page + Manual Staging + Promote

**Date**: 2026-04-25
**Status**: 🔨 IN CORSO (Steps 1–9 ✅, Step 6 e Step 10 con follow-up minori — vedi note inline)
**Priority**: P0 (MVP)
**Estimated effort**: ~2 days
**Predecessors**:
- ✅ Part 1 (DB & Schema realignment) — `phases/phase-07-subplan/Parte1/`
- ✅ Part 2 (BRIM Revisione 2) — `phases/phase-07-subplan/Parte2/`
- ✅ Part 3 (API Consolidation + I-bis closure + Block G — backend coverage 87.06%) — `phases/phase-07-subplan/Parte3/`

**Successors**:
- ⏳ Part 4b (File Preview System) — autonomous, scheduled in parallel
- ⏳ Part 5 (Staging Modal — BRIM mode + asset resolver + event-suggest) — extends `TransactionStagingModal` introduced here

**Macro plan parent**: [`phases/phase-07-transactions.md`](./phases/phase-07-transactions.md) §"Parte 4"

---

## 🎯 Obiettivo

Costruire la pagina `/transactions` come **DataTable read-view** con filtri header URL-driven, e introdurre la prima versione **manual-only** della Staging Modal con tre flussi atomici (`create-many`, `edit-many`, bulk delete con linked-pair extender). In aggiunta:

1. **Promote transfer** UX completa (DEPOSIT + WITHDRAWAL → TRANSFER / FX_CONVERSION) usando l'endpoint backend già esistente `POST /transactions/transfers/promote`.
2. **Always-pair-adjacent rendering**: le linked transactions (TRANSFER, FX_CONVERSION) sono sempre rese adiacenti — giver sopra (out), receiver sotto (in) — anche quando uno dei due è filtrato fuori (in tal caso appare come **ghost row viola**). Conseguenza: il GoTo `🔗` diventa scroll locale + pulse, niente URL manipulation.
3. **`assetStore` enriched** con merge opportunistico, riusabile via nuovo `AssetSelect.svelte`. Gemella `transactionTypes.ts` per icona + enum, replicando il pattern `assetTypes.ts`.
4. **E2E spec deferito da Parte 1** (`asset-event-delete.spec.ts`, 4 scenari) introdotto qui insieme al badge `●evt`.

**Esplicitamente fuori scope** (Parte 5 / Parte 4b / future):
- BRIM staging (Parte 5: lo `TransactionStagingModal` introdotto qui ha solo manual modes; Parte 5 aggiunge `mode='create-brim'` + asset resolver + duplicates + event-suggest tolerance slider).
- File Preview System (Parte 4b).
- Editing inline sulla tabella principale `/transactions` — la tabella resta una pura read-view.
- Endpoint backend nuovi: nessuno richiesto.
- `POST /transactions/commit` mixed (atomic creates+updates+deletes in una call): **non aggiunto**, decisione esplicita (vedi §Open Questions #1).

---

## 📊 Situazione di partenza

| Cosa | Stato | Path |
|------|-------|------|
| Route placeholder `/transactions` | Da sostituire | `frontend/src/routes/(app)/transactions/+page.svelte` |
| Zodios client (sync già fatto) | ✅ Pronto | `frontend/src/lib/api/generated.ts` |
| `DataTable` generico | ✅ Pronto | `frontend/src/lib/components/table/DataTable.svelte` |
| Pattern SelectionBar | ✅ Da clonare | `frontend/src/lib/components/brokers/BrokerImportFilesModal.svelte` |
| Pattern dual-view + filtri header | ✅ Da clonare | `frontend/src/lib/components/{assets/AssetTable,fx/FxTable}.svelte` |
| Pattern utility centralizzata enum+icone | ✅ Da clonare | `frontend/src/lib/utils/assetTypes.ts` |
| Pattern session cache + version counter | ✅ Da clonare | `frontend/src/lib/stores/{currencyStore,currencyGraphStore}.ts` |
| Pattern lazy provider cache | ✅ Riferimento | `frontend/src/lib/utils/providerHelpers.ts` (sezione 3 Asset Provider) |
| Pattern EditBuffer / RowStatus | ✅ Riferimento concettuale | `frontend/src/lib/components/ui/data-editor/DataEditorTypes.ts` + wiki `concepts/editbuffer-pattern` |
| Golden-ratio color generator | ✅ Pronto | `frontend/src/lib/utils/colors.ts → getIndexColor()` |
| Icone TX (PNG) | ✅ Già presenti | `frontend/static/icons/transactions/{buy,sell,dividend,interest,deposit,withdrawal,fee,tax,transfer,fx-conversion,adjustment}.png` |
| Backend transactions API multi-broker | ✅ DONE Parte 3 | `backend/app/api/v1/transactions.py` |
| `Transaction.asset_event_id` FK + sentinel `=0` per unlink | ✅ DONE Parte 1 | `backend/app/db/models.py` + `backend/app/schemas/transactions.py` |

**Note di allineamento (post-Parte 3)**:
- Endpoint bulk sono **multi-broker** (`POST/PATCH/DELETE /transactions/bulk`), **non** broker-scoped. Decisione: [`devWiki/wiki/decisions/multi-broker-atomic-tx.md`].
- `GET /transactions/{id}` è stato rimosso — usare `GET /transactions?ids=N` (ordering preservato).
- `POST /transactions/validate` accetta mixed `{creates, updates, deletes}` (cap 500/ciascuno). Il FE in Parte 4 lo chiama sempre con **una sola lista popolata** per modalità (vedi §Open Questions #1).
- `POST /transactions/transfers/promote` (Block H.4) → orientato a Parte 4 in questo plan.

---

## 🔌 Contratto frontend ↔ backend

| Endpoint reale | Quando usato in Parte 4 | Payload | Risposta |
|----------------|-------------------------|---------|----------|
| `GET /transactions` (con filtri) | Page load step 1 (main rows) | Query params: `broker_id`, `asset_id`, `types`, `date_start`, `date_end`, `tags`, `currency`, `limit`, `offset`, `sort` | `List[TXReadItem]` filtered by `BrokerUserAccess` |
| `GET /transactions?ids=…` | Page load step 2 (partner completion); also bulk-delete linked-pair lookup; also navigation-target lookup | Query: `ids=42,43,…` | `List[TXReadItem]` ordered as input, server filters per accesso |
| `GET /transactions/types` | Page load — popola `txTypeStore` | — | `List[TXTypeMetadata]` (icona logica, regole, traduzioni) |
| `GET /brokers` | Page load — popola `brokerColors` index | — | `List[BrokerInfo]` |
| `POST /assets/query` | Page load — popola `assetStore` per ids visibili; modal-open refresh | `{ ids: [...] }` (o filtri) | `List[AssetInfo]` |
| `POST /assets/events/query` | Page load — pre-fetch eventi linkati per tooltip `●evt` | `{ ids: [...] }` | `List[AssetEvent]` |
| `POST /transactions/validate` | Live validate inside Staging Modal (debounced 500ms) | `{ creates?, updates?, deletes? }` con **una sola** lista popolata | `TXValidateResponse { would_rollback, issues, balance_preview, holdings_preview }` |
| `POST /transactions/bulk` | Staging Modal mode `create-many` commit | `List[TXCreateItem]` | `TXBulkCreateResponse { rolled_back, results, success_count, errors }` |
| `PATCH /transactions/bulk` | Staging Modal mode `edit-many` commit | `List[TXUpdateItem]` (sentinel `asset_event_id=0` = unlink) | `TXBulkUpdateResponse { rolled_back, results, success_count, errors }` |
| `DELETE /transactions/bulk?ids=…` | Bulk delete (con eventuale auto-include partner) | Query: `ids=…` | `TXBulkDeleteResponse { rolled_back, results, total_deleted, errors }` |
| `POST /transactions/transfers/promote` | TransferPromoteModal commit | `{ from_tx_id, to_tx_id, new_type, asset_id?, quantity?, cost_basis_override? }` | `TXTransferPromoteResponse { rolled_back, new_from_tx_id, new_to_tx_id, errors }` |

**Atomicità** (per costruzione, vedi `decisions/multi-broker-atomic-tx`): ogni endpoint bulk è atomico **anche cross-broker**. EDITOR check 1× per ogni `broker_id` distinto nel batch. Qualsiasi violazione → rollback totale + `rolled_back=true`. La pagina presenta sempre `errors[]` come banner rosso quando `rolled_back=true`.

---

## 🧱 Step di implementazione

### Step 1 — Utility centralizzate (icone + colori) ✅ DONE

**Files**:
- `frontend/src/lib/utils/transactionTypes.ts` (nuovo)
- `frontend/src/lib/utils/brokerColors.ts` (nuovo)

**Deliverable**:
- `transactionTypes.ts` clone strutturale di `assetTypes.ts`:
  ```ts
  export const TX_TYPES = schemas.TransactionType.options; // from generated.ts Zod
  const PNG_MAP: Record<string, string> = {
    BUY: 'buy', SELL: 'sell', DIVIDEND: 'dividend', INTEREST: 'interest',
    DEPOSIT: 'deposit', WITHDRAWAL: 'withdrawal', FEE: 'fee', TAX: 'tax',
    TRANSFER: 'transfer', FX_CONVERSION: 'fx-conversion', ADJUSTMENT: 'adjustment',
  };
  export function getTransactionTypeIconUrl(type: string | null | undefined): string {
    const filename = PNG_MAP[(type ?? '').toUpperCase()] ?? 'other';
    return `/icons/transactions/${filename}.png`;
  }
  export function buildTransactionTypeOptions(t: (key: string) => string): SelectOption[] { ... }
  ```
- `brokerColors.ts`: helper `getBrokerColor(brokerId: number, brokers: BrokerInfo[]): ColorSet` che mappa `brokerId → indexInSortedBrokersById → getIndexColor(index)` (golden-ratio infinito da `colors.ts`). Deterministic per stesso elenco brokers.

**Tests**: unit test (jest/vitest) — mapping enum→PNG, fallback su `other`, deterministicità color map.

**Stima**: 0.5h

---

### Step 2 — Stores ✅ DONE

**Files**:
- `frontend/src/lib/stores/txTypeStore.ts` (nuovo)
- `frontend/src/lib/stores/assetStore.ts` (nuovo)

**Deliverable**:
- `txTypeStore`: lazy session cache `Map<TransactionType, TXTypeMetadata>` da `GET /transactions/types`. API: `ensureLoaded()`, `getMetadata(type)`. Pattern identico a `currencyStore`. Reactive `txTypeStoreVersion`.
- `assetStore`: cache **piena** `Map<assetId, AssetInfo>` con `{display_name, currency, asset_type, icon_url, provider_code, active, identifier_*}`. API:
  - `ensureAssetsLoaded(ids: number[]): Promise<void>` — fetcha solo ids mancanti via `POST /assets/query`.
  - `getAssetInfo(id: number): AssetInfo | null` — sync lookup.
  - `merge(items: AssetInfo[]): void` — **opportunistic ingress universale**: chiunque abbia dati asset freschi li deposita qui. Upsert + bump `assetStoreVersion`.
  - `invalidateAfterMutation(idOrIds: number | number[]): void` — utility centralizzata per i callsite di mutation (AssetModal save, asset delete, asset wipe). Rimuove dalla cache → next access re-fetcha.
  - `refreshAll(): Promise<void>` — manual reload (pulsante ↻).
  - `assetStoreVersion: writable(0)` — counter reattivo per `void $assetStoreVersion` in derived computations.

**Migrazione opportunistic refresh** (callsite identificati):
- `frontend/src/routes/(app)/assets/+page.svelte → loadAssets()` → dopo response chiama `assetStore.merge(response)`.
- `AssetModal.save` handler → dopo response chiama `assetStore.merge([response])`.
- `AssetSearchAutocomplete.onselect` → quando il selezionato è un asset DB (non un nuovo da provider), chiama `assetStore.merge([selected])`.
- Eventuali altri durante implementazione (annotare e centralizzare).

**Tests**:
- Unit: `merge` upsert idempotency, `invalidateAfterMutation` rimuove correttamente, `ensureAssetsLoaded` fa solo i fetch necessari.

**Stima**: 1.5h

---

### Step 3 — Componenti riusabili (`AssetSelect`, `TransactionTypeBadge`) ✅ DONE

> **Nota implementativa**: la migrazione di `DistributionEditor` ad `AssetSelect` è stata **rimandata** — quel componente non gestisce attualmente picker di asset_id (usa CountrySearchSelect/SectorSearchSelect). I primi consumer reali di `AssetSelect` saranno `TransactionStagingModal` (Step 7) e `TransferPromoteModal` (Step 9). Aggiornerò questo punto se nuovi callsite emergono durante l'implementazione.

**Files**:
- `frontend/src/lib/components/ui/select/AssetSelect.svelte` (nuovo)
- `frontend/src/lib/components/transactions/TransactionTypeBadge.svelte` (nuovo)

**Deliverable**:
- `AssetSelect.svelte`: wrapper di `SearchSelect` con options derivate da `assetStore`. Props `bind:value: number | null`, `disabled`, `filter?: (a: AssetInfo) => boolean`, `placeholder`, `data-testid`. Re-derive su `$assetStoreVersion`. Ogni option mostra `[icon] display_name [currency]`, asset inattivi grigi.
- `TransactionTypeBadge.svelte`: badge con icona PNG da `getTransactionTypeIconUrl(type)` + label localizzata (i18n `transactions.types.{TYPE}`). Riusato in tabella, modali, future BRIM staging.

**Migrazione `DistributionEditor.svelte`** (se contiene asset picker): sostituire con `AssetSelect`. Verificare durante implementazione gli altri callsite di asset_id picker.

**Tests**: Playwright snapshot test ridotto su entrambi (visual check icona, currency, disabled state).

**Stima**: 2h

---

### Step 4 — Page load + URL filters ✅ DONE

> **Nota implementativa**: niente `+page.ts` separato — pattern del progetto (vedi `/files`) è caricare in `onMount` del `+page.svelte`. Filtri scalari (`broker_id`, `asset_id`, ecc.) gestiti con parser/builder locali; i filtri richi delle header-cell (text/enum/size/date) si appoggeranno a `$lib/utils/urlFilters.ts` in Step 5.

**Files**:
- `frontend/src/routes/(app)/transactions/+page.ts` (nuovo)
- `frontend/src/routes/(app)/transactions/+page.svelte` (riscrittura completa)

**Deliverable**:
- **Tutti i filtri sempre in URL** (parità con `/files`): `broker_id`, `asset_id`, `types`, `date_start`, `date_end`, `tags`, `currency`, `highlight_id`, `page`, `page_size`, `sort`.
- **Two-stage fetch**:
  1. `mainRows = GET /transactions` con filtri parsed da URL.
  2. `missingPartnerIds = mainRows.flatMap(r => r.related_transaction_id).filter(id => !mainRowsIds.has(id))`. Se non vuoto: `partnerRows = GET /transactions?ids=...`. Server filtra per `BrokerUserAccess` → eventuali partner non accessibili semplicemente non tornano (mostriamo un'icona grigia "linked but inaccessible").
- **Idratazione parallela**:
  - `txTypeStore.ensureLoaded()`.
  - `brokers = GET /brokers` (per color map).
  - `assetStore.ensureAssetsLoaded([...distinctAssetIds(main+partner)])`.
  - `eventTooltipMap = POST /assets/events/query` con `[...distinctEventIds]` se non vuoto.
- **URL ↔ filters bidirezionale** via `$effect` + `goto(url, { replaceState:true, keepFocus:true })`.

**Tests**: E2E `transactions-list.spec.ts` (vedi §Test strategy).

**Stima**: 1.5h

---

### Step 5 — `TransactionsTable.svelte` con always-pair-adjacent ✅ DONE

> **Note implementative**:
> - Algoritmo always-pair-adjacent + pair-never-split paginator implementati.
> - Color band + broker badge usano CSS variables iniettate via `getRowStyle`.
> - Click delegation per `🔗` / `●evt` icone (HtmlCell) sul container `tx-table-wrap`.
> - Ghost rows con tinta viola tenue + chip "ghost".
> - Selezione include sia righe normali che ghost (decisione plan §Open Q4).
> - i18n keys minime aggiunte (EN); IT/FR/ES restano per Step 10.

**Files**:
- `frontend/src/lib/components/transactions/TransactionsTable.svelte` (nuovo)

**Deliverable**:

**Algoritmo di rendering** (eseguito su client su `mainRows + partnerRows`):
1. Sort `mainRows` per `sort` corrente (default `date desc`).
2. Costruisci `displayRows[]` iterando `mainRows`:
   - Se la riga ha `related_transaction_id` e il partner non è ancora apparso → push self, push partner subito sotto (preso da `mainRows` se presente, altrimenti da `partnerRows` con flag `isGhost=true`).
   - Se la riga è il partner di una già renderizzata → skip (deduplica).
3. **Within-pair sort**: giver (out) sopra, receiver (in) sotto. Determinazione:
   - TRANSFER: `quantity < 0` = giver, `quantity > 0` = receiver.
   - FX_CONVERSION: `cash.amount < 0` = giver, `cash.amount > 0` = receiver.
4. Applica paginazione **rispettando i pair-group**: se la pair sarebbe split a cavallo di pagina, posticipa la pair intera alla pagina successiva. Target `page_size` = 50, effettivo 49–51 accettato (vedi Open Questions #2).

**Colonne**: `[select] [color-band] [date] [type-badge] [asset] [qty] [cash] [broker-badge] [tags] [link-icon] [event-icon] [actions]`.

- `color-band` (4px sinistra): `getBrokerColor(row.broker_id, brokers).bg`.
- `type-badge`: `<TransactionTypeBadge type={row.type} />`.
- `asset`: `assetStore.getAssetInfo(row.asset_id)?.display_name ?? '—'`. Re-derive su `$assetStoreVersion`.
- `qty`: formatted decimal con segno; receiver mostra prefisso `↳` per indicare "in-pair receiver".
- `cash`: `Currency.format(row.cash)` o `—`.
- `broker-badge`: chip colorato (stesso hue della band) + nome broker.
- `link-icon` (lucide `Link2`): visibile se `related_transaction_id != null`. Click → handler GoTo (Step 6).
- `event-icon` (badge viola): visibile se `asset_event_id != null`. Tooltip da `eventTooltipMap`.
- **Ghost row** (partner filtrato fuori, `isGhost=true`): tinta viola tenue su tutto lo sfondo riga + chip "out of filter" che mostra il filtro che esclude la riga + bottone `✕` (locale, non persistito) per nasconderla; bottone `+` per re-includerla.
- **Header filters** per ogni colonna (popover identico a `AssetTable`/`FxTable`).
- `data-testid` ovunque: `tx-row-{id}`, `tx-row-{id}-ghost`, `tx-cell-{col}-{id}`, `tx-filter-{col}`, `tx-link-icon-{id}`, `tx-event-badge-{id}`, `tx-pair-group-{giverId}`.

**Stima**: 4h

---

### Step 6 — GoTo locale + `●evt` tooltip + spec deferita 🔨 PARZIALE

> **Done in Step 5+6**:
> - GoTo locale: click su 🔗 setta `highlight_id`, scroll smooth sulla partner row, pulse animation, auto-clear dopo 1.6s.
> - ●evt tooltip: `title` attribute alimentato dalla `eventTooltipMap` pre-fetched al load (lookup sincrono, no lazy network).
>
> **Follow-ups (rimandati alla fase di QA finale, Step 10)**:
> - Popover-on-click sul `●evt` con link "Open in /assets/{asset_id}#events" (oggi è solo title).
> - `frontend/e2e/asset-event-delete.spec.ts` — 4 scenari Parte 1 (richiede dev server + populate_mock_data run).
> - `populate_mock_data.py` extension (≥1 DIVIDEND con asset_event_id, ≥1 TRANSFER cross-broker, ≥30 TX su 2-3 broker).

**Files**:
- (modifiche in `TransactionsTable.svelte`)
- `frontend/e2e/asset-event-delete.spec.ts` (nuovo, deferito da Parte 1)
- `backend/test_scripts/test_db/populate_mock_data.py` (estensione)

**Deliverable**:
- **GoTo**: click su 🔗 = scroll local + animate-pulse sulla `tx-row-{related_transaction_id}` (sempre nella stessa pagina grazie ad always-pair-adjacent). Niente URL change. `$effect` su `highlight_id` (param URL): se settato all'ingresso pagina, scroll+pulse su quella row dopo render.
- **`●evt` tooltip**: lookup sincrono da `eventTooltipMap` pre-fetched al load (NO lazy network). Tooltip mostra `[type · date · value currency · auto/manual]`. Click su badge → opzionale popover con link `Open in /assets/{asset_id}#events`.
- **Spec E2E `asset-event-delete.spec.ts`** (4 scenari Parte 1, naturali con il badge `●evt` ora visibile):
  1. Delete evento NON referenziato → riga scompare + toast success.
  2. Delete evento referenziato da tx accessibile → toast warning con `accessible_transactions` elencate, riga resta.
  3. Delete evento referenziato solo da tx di altri utenti → toast warning con `hidden_transactions_count`, riga resta.
  4. Delete bulk misto (deleted + in_use + not_found) → sparisce solo la riga `deleted`.
- **Mock data extension**: `populate_mock_data.py` aggiungere ≥1 DIVIDEND con `asset_event_id` valorizzato (test `●evt` + always-pair-adjacent ghost), ≥1 TRANSFER cross-broker (test pair rendering), ≥30 TX su 2-3 broker (test paginazione + color band).

**Stima**: 2h

---

### Step 7 — `TransactionStagingModal.svelte` (manual-only) ✅ DONE

> **Note implementative**:
> - ModalBase usata come shell. Tabella inline con input/select nativi + AssetSelect per asset_id.
> - DraftRow con status `new` / `edited` / `original`.
> - Live-validate debounced 500ms via `POST /transactions/validate` con SOLO la lista corrispondente popolata (creates per `create-many`, updates per `edit-many`).
> - All'apertura: `ensureAssetsLoaded()` per refresh asset display name.
> - Type + broker immutabili in `edit-many`.
> - Wired: `+ Add transaction` (header) e `Edit bulk` / `Clone` (SelectionBar inline).
> - Edit single-row dalla tabella → mode=`edit-many` con N=1.
> - On `rolled_back=true`: banner rosso persistente, modale resta aperta.
>
> **Endpoint alias usati** (dal client Zodios):
> - `create_transactions_bulk_api_v1_transactions_bulk_post`
> - `update_transactions_bulk_api_v1_transactions_bulk_patch`
> - `validate_transactions_api_v1_transactions_validate_post`

**Files**:
- `frontend/src/lib/components/transactions/TransactionStagingModal.svelte` (nuovo)

**Deliverable**:
- Props: `mode: 'create-many' | 'edit-many'`, `initialRows: TXCreateItem[] | TXReadItem[]`, `onCommitted?: (response) => void`, `onClose: () => void`.
- Stato locale: `draftRows: DraftRow[]` con `status: 'new' | 'edited' | 'original'` (RowStatus pattern, vivo SOLO dentro la modale; la tabella principale `/transactions` resta read-view).
- **Live validate** debounced 500ms → `POST /transactions/validate` con SOLO il branch corrispondente popolato (creates per `create-many`, updates per `edit-many`). Banner top con `issues[]` clickabili (click → scroll alla riga).
- **All'apertura modale**: `assetStore.ensureAssetsLoaded([...distinctAssetIds(initialRows)])` — refresh fresco per evitare stale display_name cross-client.
- Color-band sinistra dentro la modale = stesso `getBrokerColor`.
- Asset selection inline via `AssetSelect`.
- Type **immutable** in `edit-many` (regola backend); broker immutable in `edit-many` (regola backend, broker_id non patchable via PATCH).
- Commit:
  - `create-many` → `POST /transactions/bulk` con N `TXCreateItem`.
  - `edit-many` → `PATCH /transactions/bulk` con N `TXUpdateItem`.
- On `rolled_back=true`: banner rosso persistente con `errors`/per-item `status`, modale resta aperta con stato draft invariato. Su success → `onCommitted(response)` chiude la modale, chiama refresh della list.

**ASCII art — `mode: create-many`**:
```
╔════════════════════════════════════════════════════════════════════════════════════╗
║ ➕ New transactions — 3 drafts · 1 issue                                  [✕]    ║
╠════════════════════════════════════════════════════════════════════════════════════╣
║ ⚠ 1 issue: Row 2 — DIVIDEND requires asset_id                                     ║
╠════════════════════════════════════════════════════════════════════════════════════╣
║   │ Date 🔽    │ Type 🔽    │ Asset 🔍🔽       │ Qty 🔽   │ Cash 🔽       │Broker🔽│⚙║
║───┼────────────┼────────────┼──────────────────┼──────────┼───────────────┼────────┼─║
║🟦 │ 2026-04-15 │ 🛒 BUY     │ VWCE             │ +10.00   │ -€1,050.00    │ Degiro │✕║
║🟥 │ 2026-04-10 │ 💵 DIV     │ — (required ⚠)   │  0       │ +€12.40       │ IBKR   │✕║
║🟦 │ 2026-04-08 │ 💰 DEP     │ —                │  0       │ +€2,000.00    │ Degiro │✕║
║───┴────────────┴────────────┴──────────────────┴──────────┴───────────────┴────────┴─║
║   [+ Add row]                                                                       ║
╠════════════════════════════════════════════════════════════════════════════════════╣
║ Balance preview (Degiro): Cash EUR +€950 · Holdings VWCE +10                      ║
║                                                                                    ║
║                              [Cancel]  [Validate (auto)]  [Commit 3 ▸]            ║
╚════════════════════════════════════════════════════════════════════════════════════╝
```

**ASCII art — `mode: edit-many`**:
```
╔════════════════════════════════════════════════════════════════════════════════════╗
║ ✎ Edit transactions — 4 selected · 0 issues                                [✕]   ║
╠════════════════════════════════════════════════════════════════════════════════════╣
║ ☑ Show only modified                                                                ║
╠════════════════════════════════════════════════════════════════════════════════════╣
║   │ ID  │ Date 🔽    │ Type     │ Asset           │ Qty      │ Cash         │Status║
║───┼─────┼────────────┼──────────┼─────────────────┼──────────┼──────────────┼──────║
║🟦 │ #42 │ 2026-04-15 │ 🛒 BUY   │ VWCE            │ +10.00   │ -€1,050.00   │  ●   ║
║🟦 │ #43 │ 2026-04-10 │ 🛒 BUY   │ VWCE            │ +5.00 ✎  │ -€525.00     │ edit ║
║🟥 │ #50 │ 2026-04-08 │ 💵 DIV   │ AAPL            │  0       │ +€12.40 ✎    │ edit ║
║🟦 │ #55 │ 2026-04-05 │ 💰 DEP   │ —               │  0       │ +€2,000      │  ●   ║
║                                                                                    ║
║ Type and broker are immutable. Use Clone for restructuring.                        ║
╠════════════════════════════════════════════════════════════════════════════════════╣
║                              [Cancel] [Reset all] [Validate (auto)] [Commit 2 ▸]  ║
╚════════════════════════════════════════════════════════════════════════════════════╝
```

**Stima**: 4h

---

### Step 8 — Bulk delete con linked-pair extender modal ✅ DONE

> **Note implementative**:
> - Pre-scan in `+page.svelte::onBulkDelete`: per ogni riga selezionata con `related_transaction_id != null`, controlla se il partner è già selezionato (no-op), in memoria (push problem), o da fetchare (`GET /transactions?ids=[missing]`).
> - Toggle globale + per-riga (`extend` / `remove`).
> - Bulk delete commit: `delete_transactions_bulk_api_v1_transactions_bulk_delete(undefined, {queries:{ids}})` (pattern Zodios per DELETE).
> - Quando non ci sono problematic rows la modale serve comunque come "confirm semplice" (le clean rows passano direttamente al payload). Una `ConfirmModal` dedicata può essere aggiunta in futuro per ridurre il rumore visivo nei casi clean-only.

**Files**:
- `frontend/src/lib/components/transactions/BulkDeleteLinkedPairModal.svelte` (nuovo)

**Deliverable**:
- Pre-scan delle righe selezionate: per ogni `row.related_transaction_id != null` controlla se il partner è già nella selezione. Se manca:
  - prima cerca nel dataset corrente (`mainRows + partnerRows`),
  - altrimenti `GET /transactions?ids=<missing>` (rispetta access control server-side).
- Apre `BulkDeleteLinkedPairModal` solo se ci sono "problematic rows" (almeno 1 selezionata con partner mancante). Altrimenti `ConfirmModal` semplice + `DELETE /transactions/bulk?ids=…` direttamente.
- Toggle globale in alto: `( ) Remove all problematic   (●) Extend all problematic` → sincronizza tutti i radio per-riga.
- Per-riga radio: `Remove (= rimuovi dalla selezione)` o `Extend (= aggiungi anche il partner)`.
- Final batch summary: "X selected + Y partners auto-included = Z total to delete".
- Click `Delete Z` → singola call `DELETE /transactions/bulk?ids=…` (atomic, multi-broker).
- On `rolled_back=true`: banner rosso, modale resta aperta.

**ASCII art**:
```
╔══════════════════════════════════════════════════════════════════════════════════╗
║ 🗑 Confirm delete — 5 selected, 2 with linked partners              [✕]        ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Linked transactions must be deleted together (TRANSFER, FX_CONVERSION).         ║
║                                                                                  ║
║ Apply to all problematic rows: ( ) Remove from selection   (●) Extend selection ║
║                                                                                  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Selected ID │ Type        │ Partner │ Action                                   ║
║─────────────┼─────────────┼─────────┼──────────────────────────────────────────║
║ #42 BTC →   │ 🔄 TRANSFER │ #43 ↩   │ ( ) Remove #42   (●) Extend → also #43  ║
║ #58 USD→EUR │ 💱 FX       │ #59 ↩   │ ( ) Remove #58   (●) Extend → also #59  ║
║                                                                                  ║
║ Other 3 selected rows have no linked partner — will be deleted as-is.           ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Final batch: 7 transactions to delete (5 selected + 2 partners auto-included)   ║
║                                                                                  ║
║                                              [Cancel]   [Delete 7 ▸]            ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

**Stima**: 2h

---

### Step 9 — `TransferPromoteModal.svelte` ✅ DONE

> **Note implementative**:
> - Trigger: button condizionale `⚡ Promote pair` mostrato in SelectionBar SOLO quando 2 righe sono selezionate, una `DEPOSIT` + una `WITHDRAWAL`, entrambe con `related_transaction_id == null`.
> - Step 1 modal: scelta tra TRANSFER (greyed se brokers uguali o currency diverse) e FX_CONVERSION (greyed se brokers diversi o currency uguali).
> - Step 2 modal: per TRANSFER → AssetSelect + quantity + cost_basis_override (advanced); per FX_CONVERSION → solo riepilogo + implied rate.
> - Backend: `promote_transfer_api_v1_transactions_transfers_promote_post`.
> - On success: page mostra il highlight pulse sul nuovo `from_tx_id` (auto-clear dopo 1.6s).
> - On `rolled_back=true`: banner rosso, modal resta aperta.

**Files**:
- `frontend/src/lib/components/transactions/TransferPromoteModal.svelte` (nuovo)

**Deliverable**:
- Trigger: SelectionBar mostra `⚡ Promote pair…` **solo** quando le righe selezionate sono **esattamente 2** e match il pattern `1 DEPOSIT + 1 WITHDRAWAL` con `related_transaction_id=null` su entrambe.
- Backend: `POST /transactions/transfers/promote` con `{ from_tx_id, to_tx_id, new_type, asset_id?, quantity?, cost_basis_override? }`.
- Variants e regole (validate UX prima del submit, replicando le check del service):
  - **TRANSFER**: brokers DEVONO essere distinti, currencies UGUALI; richiede `asset_id` + `quantity`.
  - **FX_CONVERSION**: stesso broker, currencies DIVERSE; nessun asset_id.
- Se i due TX selezionati non sono compatibili con uno dei due target → quel radio è disabled con motivazione inline (greyed out).
- Asset selection via `AssetSelect`.
- On `rolled_back=true` (validation server fail) → banner rosso con `errors`, modale resta aperta. Su success → `onCommitted({new_from_tx_id, new_to_tx_id})` chiude la modale, refresha la list, GoTo highlight sulla nuova pair.

**ASCII art — Step 1 (choose new_type)**:
```
╔══════════════════════════════════════════════════════════════════════════════════╗
║ ⚡ Promote cash pair                                                  [✕]      ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Selected pair:                                                                  ║
║                                                                                  ║
║   #58 WITHDRAWAL  Degiro · 2026-04-08 · −€1,000.00                              ║
║   #59 DEPOSIT     IBKR   · 2026-04-08 · +€1,000.00                              ║
║                                                                                  ║
║ Promote to:                                                                      ║
║   (●) 🔄 TRANSFER         — same currency, different brokers (asset move)       ║
║   ( ) 💱 FX_CONVERSION    — same broker, different currencies (greyed out:      ║
║                              brokers differ, currencies match)                   ║
║                                                                                  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                              [Cancel]   [Next ▸]                ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

**ASCII art — Step 2 (TRANSFER details)**:
```
╔══════════════════════════════════════════════════════════════════════════════════╗
║ ⚡ Promote → 🔄 TRANSFER                                              [✕]      ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ From: Degiro #58 (WITHDRAWAL −€1,000)                                           ║
║ To:   IBKR   #59 (DEPOSIT    +€1,000)                                           ║
║                                                                                  ║
║ Asset moved:        🔍 [VWCE                          ▾]  (required)            ║
║ Quantity:                       [10.000               ]   (required)            ║
║                                                                                  ║
║ ◢ Advanced ▾                                                                     ║
║   Cost basis override:          [auto                 ]   (optional, frozen      ║
║                                                            for TRANSFER_IN)     ║
║                                                                                  ║
║ ⚠ This will DELETE #58/#59 and CREATE 2 new linked TRANSFER rows atomically.   ║
║   On rollback nothing is changed.                                                ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                              [◂ Back]  [Cancel]  [Promote ▸]                    ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

**ASCII art — Step 2 (FX_CONVERSION)**:
```
╔══════════════════════════════════════════════════════════════════════════════════╗
║ ⚡ Promote → 💱 FX_CONVERSION                                         [✕]      ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Same broker (IBKR), distinct currencies — auto-detected:                        ║
║                                                                                  ║
║ Out: #71 WITHDRAWAL IBKR · 2026-04-12 · −$1,000.00 (USD)                        ║
║ In:  #72 DEPOSIT    IBKR · 2026-04-12 · +€921.50  (EUR)                         ║
║                                                                                  ║
║ Implied rate: 1 USD = 0.9215 EUR                                                ║
║                                                                                  ║
║ No additional fields required.                                                   ║
║                                                                                  ║
║ ⚠ This will DELETE #71/#72 and CREATE 2 new linked FX_CONVERSION rows atomic.  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                              [◂ Back]  [Cancel]  [Promote ▸]                    ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

**Stima**: 2h

---

### Step 10 — Bulk actions wiring + Import menu + i18n + final QA 🔨 PARZIALE

> **Done**:
> - Header buttons: `+ Add transaction` apre StagingModal `create-many` vuota.
> - SelectionBar inline (visibile quando N>0): `✎ Edit bulk`, `📋 Clone`, `🗑 Delete`, `⚡ Promote pair` (condizionale).
> - Single-row ✎ in colonna actions → mode `edit-many` con N=1.
> - i18n EN/IT/FR/ES tutte propagate via `./dev.py i18n update` (927 keys complete, 0 incomplete).
> - svelte-check pulito (0 errori 0 warning).
> - `data-testid` ovunque richiesto dal plan.
>
> **Follow-ups (separati, da chiudere a fine Phase 7 — non bloccanti per Part 4)**:
> - **Import ▾ menu**: `BrokerImportFilesModal` richiede `brokerId` esplicito. A page-level su `/transactions` serve un broker picker preliminare. Per ora il button mostra console warning; UX corretta arriverà con Part 5 (BRIM staging completo).
> - `BulkDeleteLinkedPairModal` quando non ci sono problematic rows → potrebbe usare un `ConfirmModal` più snello.
> - `frontend/e2e/asset-event-delete.spec.ts` (4 scenari Part 1) + le 5 spec Part 4 (`transactions-list`, `-goto`, `-staging`, `-bulk-delete`, `-promote`).
> - `populate_mock_data.py` extension (≥1 DIVIDEND con `asset_event_id`, ≥1 TRANSFER cross-broker, ≥30 TX su 2-3 broker).
> - SelectionBar inline → estrarre in `frontend/src/lib/components/transactions/SelectionBar.svelte` riusabile (oggi è inline nella page).
> - Popover-on-click per badge `●evt` con link → `/assets/{id}#events`.

**Files**:
- `frontend/src/lib/components/transactions/SelectionBar.svelte` (nuovo, clone pattern `BrokerImportFilesModal`)
- `frontend/src/routes/(app)/transactions/+page.svelte` (action wiring)
- `frontend/src/lib/i18n/{en,it,fr,es}.json` (extend)

**Deliverable**:
- **Header buttons**:
  - `+ Add transaction` → `TransactionStagingModal` mode `create-many` con 1 riga vuota.
  - `Import ▾` → solo voce "From broker file…" che apre `BrokerImportFilesModal` esistente (il flow BRIM completo è di Parte 5).
- **SelectionBar** (visibile quando N>0 selezionati):
  - `✎ Edit bulk` → mode `edit-many` con N righe.
  - `📋 Clone to staging` → mode `create-many` pre-popolato con N righe clonate (id stripped, `link_uuid` rigenerato per le pair, `date=today`).
  - `🗑 Delete` → `BulkDeleteLinkedPairModal` (Step 8) o `ConfirmModal` semplice.
  - `⚡ Promote pair` (condizionale: 2 selezionate + 1 DEP + 1 WD + entrambe `related_transaction_id=null`) → `TransferPromoteModal` (Step 9).
  - Banner informativo "spans N brokers" se la selezione attraversa più broker (informativo, non bloccante — l'atomicità è garantita dal backend).
- **Single-row** ✎ in colonna actions → mode `edit-many` con N=1.
- **i18n**: chiavi `transactions.{table,filters,actions,bulk,staging,promote,delete,types,pair}.*` × 4 lingue (EN/IT/FR/ES). Eseguire `./dev.py i18n add`.
- **`data-testid`** su tutti i selettori (mai CSS classes o text content).
- svelte-check + lint:format-frontend (skill `lint-format-frontend`).

**Stima**: 2h

---

## 🧪 Strategia test

### Playwright E2E (6 spec)

| Spec | Cosa copre |
|------|-----------|
| `transactions-list.spec.ts` | Load, filtri header URL-synced, paginazione, broker color band (golden-ratio), type-badge PNG, ●evt tooltip pre-fetched, **always-pair-adjacent rendering** (linked TX adiacenti anche con sort by-amount), **ghost row viola** quando partner filtrato fuori |
| `transactions-goto.spec.ts` | Click 🔗 = scroll+pulse locale; nessun URL change; case "entrambi in filtro" e case "partner ghost" |
| `transactions-staging.spec.ts` | create-many (1 row, N rows, +Add), edit-many (modify, validate live banner, commit), clone, rollback banner |
| `transactions-bulk-delete.spec.ts` | Selection multi-broker, BulkDeleteLinkedPairModal con per-row + global toggle, rollback handling |
| `transactions-promote.spec.ts` | DEPOSIT+WITHDRAWAL → TRANSFER (cross-broker, same currency); → FX_CONVERSION (same-broker, diff currency); rollback su validation error |
| `asset-event-delete.spec.ts` | 4 scenari deferiti da Parte 1 (`deleted` / `in_use accessible` / `in_use hidden` / bulk misto) |

### Unit / svelte-check
- Unit (vitest) su `transactionTypes.ts`, `brokerColors.ts`, `assetStore` (merge, invalidate, ensureLoaded).
- svelte-check + lint:format-frontend pass clean.

### Backend coverage
- Nessun gap atteso (Parte 3 chiusa a 87.06%). Niente endpoint nuovi → niente coverage delta.

### Mock data
- `backend/test_scripts/test_db/populate_mock_data.py` esteso con: ≥1 DIVIDEND `asset_event_id`, ≥1 TRANSFER cross-broker, ≥30 TX su 2-3 broker.

---

## 🚧 Open Questions / decisioni residue

1. **Mixed validate vs split validate** — `POST /transactions/validate` accetta mixed `creates+updates+deletes` ma il FE in Parte 4 chiama sempre con UNA sola lista popolata. Decisione: **tenere l'endpoint mixed così com'è** (no breaking, ben testato 87.06%, Parte 5 potrebbe rivolerlo misto se serve "edit during BRIM staging"). FE call style documentato. Reversibile in futuro se serve scorporo.
2. **Pagination & always-pair-adjacent** — pair never-split può causare pagine con N+1 righe (se la pair "spinge" giù un'altra). Decisione: accettare leggera variabilità nel `page_size` (target 50, effettivo 49–51) per preservare adjacency. UX preferibile a pageoraggio strict.
3. **Always-pair-adjacent + sort by-amount conflict** — se l'utente ordina per `qty desc`, il giver (qty<0) e receiver (qty>0) vivono in metà opposte. Adjacency forza a renderizzarli insieme. Decisione: la pair viene ancorata alla posizione sort del **giver**, receiver immediatamente sotto. Documentato in tooltip dell'header sort.
4. **Ghost rows e selezione bulk** — una ghost row è selezionabile? **Sì**, le operazioni bulk delete/edit/clone/promote sui partner ghost sono operazioni legittime. SelectionBar conta ghost+native uniformemente.
5. **Always-pair-adjacent come opzione utente** — settings toggle? In Parte 4 default fisso `on`, settings toggle posticipato.
6. **`assetStore` cross-client edits** — pattern session+version+invalidate-on-modal-open + opportunistic merge. Cross-client edits proattivi richiederebbero WebSocket/SSE (fuori scope LibreFolio attuale). Limitazione documentata in nuova wiki page (vedi §Cross-link).
7. **Promote scope strict** — solo `1 DEPOSIT + 1 WITHDRAWAL` con `related_transaction_id=null`. "Smart auto-detection" (pair-finder su molte righe per `amount` opposti + `date` close) è feature futura, fuori scope.
8. **Asset/event invalidation centralization** — `assetStore.invalidateAfterMutation()` esportata da `assetStore.ts` stesso, callsite identificati: `AssetModal.save`, `assets/+page.svelte:onDelete/onWipe`, eventuali futuri annotati durante implementazione.

---

## 🔗 Cross-link

**Parent macro plan**: [`phases/phase-07-transactions.md`](./phases/phase-07-transactions.md) §"Parte 4"
**Predecessori (archiviati)**:
- [`phases/phase-07-subplan/Parte1/`](./phases/phase-07-subplan/Parte1/) — DB & Schema
- [`phases/phase-07-subplan/Parte2/`](./phases/phase-07-subplan/Parte2/) — BRIM Revisione 2
- [`phases/phase-07-subplan/Parte3/`](./phases/phase-07-subplan/Parte3/) — API Consolidation + Closure 1+2 + Block G

**Successori**:
- Parte 4b — File Preview System (autonoma, parallelizzabile)
- Parte 5 — Staging Modal full (estende `TransactionStagingModal` introdotto qui con `mode='create-brim'` + asset resolver + duplicates + event-suggest tolerance slider)

**devWiki rilevante**:
- `decisions/multi-broker-atomic-tx` — endpoint bulk multi-broker, atomicità cross-broker
- `decisions/brim-parser-only` — BRIM Revisione 2 (contesto)
- `connections/transactions-connections` — F-046 → F-047 (TX list page) → F-048 (Staging Modal) → F-051 (TX↔AssetEvent)
- `concepts/editbuffer-pattern` — RowStatus pattern (riferimento concettuale per draft tracking dentro Staging Modal)
- `concepts/e2e-data-testid-rule` — selettori test
- `concepts/svelte5-runes` — `$state`/`$derived`/`$effect`
- `concepts/dual-view-pattern` — non applicabile qui (TX usa solo DataTable, niente card grid)
- **(NEW)** `concepts/opportunistic-cache-merge` — da filare a fine sessione (pattern `assetStore.merge` come ingress universale per dati freschi)
- **(NEW)** `problems/cross-client-cache-staleness` — da filare a fine sessione (limitazione attuale + mitigazioni)

---

## 📝 Commit strategy

Conventional Commits, 10 commit incrementali (uno per step principale), ognuno verde su lint+typecheck+E2E del proprio scope:

1. `feat(transactions): add transactionTypes utility + brokerColors helper (golden-ratio)`
2. `feat(transactions): add txTypeStore + enriched assetStore with merge/invalidate API`
3. `feat(ui): add AssetSelect reusable component backed by assetStore + migrate DistributionEditor`
4. `feat(transactions): scaffold /transactions page with URL-synced filters + two-stage fetch (main+partner)`
5. `feat(transactions): TransactionsTable with always-pair-adjacent rendering + ghost rows + color band`
6. `feat(transactions): GoTo local scroll + ●evt prefetch tooltip + asset-event-delete e2e`
7. `feat(transactions): TransactionStagingModal manual mode (create-many, edit-many) with live validate`
8. `feat(transactions): bulk delete with linked-pair extender modal`
9. `feat(transactions): TransferPromoteModal (DEPOSIT/WITHDRAWAL → TRANSFER/FX_CONVERSION)`
10. `feat(transactions): bulk actions wiring + Import menu + i18n EN/IT/FR/ES + mock data`

---

## ✅ Final-check (eseguito su questo plan)

- ✅ Tutti i contratti API citati esistono nel codice (`backend/app/api/v1/transactions.py`).
- ✅ Solo `asset_event_id` (mai `related_asset_event_id`).
- ✅ Solo `error_code` / `detail` (mai `e.code`).
- ✅ Niente endpoint singolari `/transactions/{id}` proposti — sempre `?ids=N`.
- ✅ Nessun input "currency" libero asset-correlato (deriva da `assetStore.getAssetInfo(id).currency`).
- ✅ Lista delle azioni bulk coerente con SelectionBar pattern di `BrokerImportFilesModal`.
- ✅ `data-testid` esplicitamente menzionato nel piano test.
- ✅ Plan auto-contenuto (leggibile da nuova sessione senza saltare fra file).
- ✅ Atomicità per-modalità rispettata (1 modale = 1 endpoint = 1 batch atomic).
- ✅ ASCII art per Staging (create+edit), BulkDelete, Promote (step1+step2 TRANSFER+FX).
- ✅ Filtri sempre in URL (parità con `/files`).
- ✅ Pattern `assetTypes.ts` replicato in `transactionTypes.ts` (single source of truth).
- ✅ Opportunistic cache merge (`assetStore.merge`) come ingress universale per dati freschi.
- ✅ Always-pair-adjacent rendering elimina la complessità del GoTo cross-broker.
- ✅ Pre-check linked-pair su bulk delete con per-row + global toggle.
- ✅ `promote_transfer` in scope (era originariamente deferito).

