# Plan: C3 — Completamento Refactor Architetturale: DraftRow → PendingOp

**Date**: 2026-05-11
**Status**: ✅ COMPLETATO (2026-05-12)
**Origine**: Piano C (txStore) ha raggiunto ~80% dell'architettura target. Restano 3 item strutturali (R1 parziale, R4, R5) interdipendenti e bloccanti per Piano D (Split/Promote). Questo piano completa la migrazione a `PendingOp` + rimozione legacy `DraftRow` clone, elimina le props legacy morte, rinomina `drafts` → `ops`, e stringe il tipo di `_partnerFormPayload` da `Record<string,unknown>` a `TxFields | null`.

**Link back**: [`plan-phase07-transaction-Part4_Round6_PlanC2Round2_FixRegressionsAndMockFX.prompt.md`](./plan-phase07-transaction-Part4_Round6_PlanC2Round2_FixRegressionsAndMockFX.prompt.md)

---

## Specchio Architetturale — Prima vs Dopo Piano C (stato sorgenti 2026-05-11)

### Stato PRE–Piano C (Round 5, fine 2026-05-07)

```
+page.svelte (1035 LOC)
├── allMainRows: TXReadItem[]         ← copia 1 dei dati
├── allPartnerRows: TXReadItem[]      ← copia 2 dei dati
├── bulkInitial: TXReadItem[]         ← costruito inline in 10+ punti
├── bulkAutoOpenForm: string          ← prop separata
├── bulkInitialStatus: 'delete'       ← prop separata
├── filterEditableRows() inline       ← duplicata
└── <BulkModal initialRows={bulkInitial} autoOpenForm={…} initialStatus={…}>

TransactionBulkModal.svelte (1766 LOC)
├── interface DraftRow { tempId, status, ...27 campi copiati da TXReadItem, original? }
├── fromTx()                          ← clone intero TXReadItem → DraftRow (~35 LOC)
├── mergePairedRows()                 ← coppia via link_uuid + getTypeRule (~60 LOC)
├── _hidden row pattern               ← partner nascosto nel drafts[], filtrato in visibleDrafts
├── patchDualRowFromForm()            ← partner match via link_uuid, fragile (~70 LOC)
├── patchRowFromForm()                ← marca status='edited' manualmente in 6+ punti
├── link_uuid generato in 4+ punti   ← causa 5 classi di bug
├── status marcato manualmente        ← causa 3 classi di bug "edited falso"
└── Props: initialRows, autoOpenForm, initialStatus, availableTags, onClose, onCommitted

TransactionPickerModal.svelte
├── Props: mainRows, partnerRows, brokers  ← 3 grandi array passati come props
└── Paginazione gestita dal parent
```

**Root cause di 17+ bug documentati**: 3 copie dei dati divergenti; `link_uuid` generato in 4+ punti → orphaned partners; status marcato manualmente → "edited falso"; `_hidden` pattern → partner orfano dopo reset.

### Stato ATTUALE (post Piano C + C2 + C2R2, 2026-05-11)

```
+page.svelte (938 LOC, −9%)
├── bulkIntent: WorkspaceIntent       ← solo {action, txIds} — nessun dato
├── txStoreSetAll() in reload()       ← popola l'unica fonte di verità
├── txStoreCanEdit() per viewer guard ← centralizzato
└── <BulkModal intent={bulkIntent}>   ← API dichiarativa, zero props legacy

txStore.svelte.ts (103 LOC) — NUOVO ✅
├── Map<number, TXReadItem>          ← unica fonte di verità per tutte le TX
├── txStoreGet/GetPartner/GetAll     ← lookup O(1), partner via related_transaction_id
├── txStoreCanEdit()                 ← viewer guard centralizzato
└── txStoreSetAll/Invalidate         ← lifecycle

types.ts (51 LOC) — NUOVO ✅
├── TXReadItem                       ← canonical source (era duplicato in 6 file)
├── ValidationIssue                  ← canonical source
└── AssetEvent                       ← canonical source

txPayloadHelpers.ts (217 LOC) — NUOVO ✅
├── TxFields, TxOriginal             ← interfacce condivise FormModal ↔ BulkModal
├── PATCHABLE_FIELDS                 ← set unico dei campi ammessi in UPDATE
├── buildCreatePayload               ← SSoT per CREATE payload
├── buildUpdateDiff                  ← SSoT per UPDATE diffing
├── diffDualItem                     ← diff partner da collectDualUpdates
├── applySignRules, fieldEq          ← helpers condivisi

TransactionBulkModal.svelte (1819 LOC — target era −30%, in realtà +3%)
│
│ ── ✅ COMPLETATI ──
├── WorkspaceIntent type              ← API dichiarativa
├── resolveInitialRows()              ← intent → rows via txStore
├── collapsePairedDrafts()            ← related_transaction_id (niente link_uuid)
├── deriveStatus()                    ← status derivato da diff vs txStore
├── getBulkContextExcluding()         ← contesto bulk per FormModal validate
├── _partnerId + _partnerFormPayload  ← partner senza _hidden row
│
│ ── ❌ LEGACY DA ELIMINARE (questo piano) ──
├── interface DraftRow                ← 27 campi clonati + original? + status
├── fromTx() (~35 LOC)               ← clone completo, con copia di original
├── patchDualRowFromForm() (~20 LOC)  ← semplificata ma ancora su DraftRow flat
├── link_uuid in DraftRow             ← residuo nel tipo (usato solo come parametro API)
├── d.original per diff               ← ridondante — txStore.get(id) è l'originale
├── Props: initialRows, autoOpenForm, initialStatus ← DEAD CODE, mai più passate
│
TransactionPickerModal.svelte         ← ✅ legge da txStore direttamente
```

**Bug risolti strutturalmente (17 totali)**: pair resolution via `related_transaction_id` (5 bug); status derivato `deriveStatus()` (3 bug); fonte unica txStore (4 bug); partner senza `_hidden` (3 bug); viewer guard centralizzato (2 bug).

---

## Obiettivo di Piano C3

Portare il `TransactionBulkModal` dall'80% al 100% dell'architettura target:

1. Eliminare `interface DraftRow` → introdurre `PendingOp` (variante `create` | `edit`) + `DraftFields`
2. Eliminare `fromTx()` → `editOpFromTx()` (legge da txStore, zero copie) + `createOpFromClone()`
3. Eliminare `d.original` → l'originale è SEMPRE `txStoreGet(op.txId)`, mai copiato
4. Rinominare `drafts` → `ops` per coerenza semantica
5. Rimuovere props legacy morte (`initialRows`, `autoOpenForm`, `initialStatus`)
6. Stringere `_partnerFormPayload: Record<string,unknown>` → `TxFields | null`
7. Cleanup dead code e commenti legacy

**Scope**: solo `TransactionBulkModal.svelte`. Nessun altro file cambia.

---

## Steps

### Step 1 — Rimuovere props legacy dalla `interface Props`

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

**Azioni**:

1. Rimuovere 3 campi dall'interfaccia `Props` (righe 111, 122, 124):
   - `initialRows?: TXReadItem[]`
   - `autoOpenForm?: 'create' | 'edit' | null`
   - `initialStatus?: 'delete'`

2. Aggiornare destructured props (riga 129): rimuovere `initialRows = []`, `autoOpenForm = null`, `initialStatus`

3. Rimuovere il ramo legacy in `resolveInitialRows()` (righe 276-277):
   ```typescript
   // Era:
   return {rows: initialRows, status: initialStatus, autoForm: autoOpenForm};
   // Diventa:
   throw new Error('BulkModal: intent prop is required');
   ```

4. Rimuovere il riferimento a `initialRows` nella funzione `allDraftTags` (righe 1351-1358):
   ```typescript
   // Rimuovere questo loop — i dati sono già nei drafts:
   for (const r of initialRows) for (const tg of r.tags ?? []) if (tg) seen.add(tg);
   ```

**LOC stimato**: −15 netti.

**Test**: `./dev.py test front-transaction all` — nessuna regressione (nessun callsite passa quelle props).

---

### Step 2 — Introdurre `DraftFields` e `PendingOp`, eliminare `DraftRow`

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

**Nuove interfacce** (sostituiscono `interface DraftRow` righe 76-106):

```typescript
/** Fields displayed & editable in the grid — pure data, no metadata. */
interface DraftFields {
    broker_id: number;
    asset_id: number | null;
    type: TransactionTypeCode;
    date: string;
    quantity: string;
    cash: {code: string; amount: string} | null;
    tags: string[];
    description: string;
    asset_event_id: number | null;
    cost_basis_override: string;
}

/** Partner display data for paired rendering (Da:/A: columns). */
interface PartnerDisplay {
    partnerId?: number;
    partnerBrokerId?: number;
    partnerCash?: {code: string; amount: string} | null;
    partnerDate?: string;
    /** Full partner payload from FormModal.
     *  For new pairs: complete CREATE payload with link_uuid.
     *  For edited pairs: payload to diff against txStoreGet(partnerId). */
    partnerPayload?: TxFields | null;
}

/** Pending operation — one per visible row in the BulkModal grid. */
type PendingOp = (
    | {
          op: 'create';
          /** link_uuid for the backend to connect paired creates.
           *  This is a payload parameter, not an internal matching mechanism. */
          link_uuid: string | null;
      }
    | {
          op: 'edit';
          txId: number;
          markedDelete: boolean;
          /** True for rows added via PickerModal (removable without DB delete). */
          addedViaPicker?: boolean;
      }
) & {
    tempId: string;
    fields: DraftFields;
} & PartnerDisplay;
```

**Perché questa struttura**:
- `DraftFields` contiene SOLO i campi editabili — niente metadata (`tempId`, `status`, `original`, `_partnerId`)
- `PartnerDisplay` contiene i dati partner per rendering — estratto perché condiviso tra `create` e `edit`
- `PendingOp` è un tagged union: `op: 'create'` ha `link_uuid`, `op: 'edit'` ha `txId` + `markedDelete`
- `original` **eliminato** — l'originale è `txStoreGet(op.txId)`, mai copiato
- `status` **eliminato** — derivato da `deriveStatus(op)` ogni volta
- `_partnerFormPayload` → `partnerPayload: TxFields | null` — tipo stretto

**Migrazione state**:
```typescript
// Era:
let drafts = $state<DraftRow[]>([]);
// Diventa:
let ops = $state<PendingOp[]>([]);
```

---

### Step 3 — Eliminare `fromTx()`, creare `editOpFromTx()` e `createOpFromClone()`

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

**Eliminare**: `fromTx()` (righe 162-197, ~35 LOC).

**Nuova `fieldsFromTx(tx: TXReadItem): DraftFields`** (~12 LOC):
```typescript
/** Extract display-ready DraftFields from a TXReadItem.
 *  Applies auto-sign: shows positive values for types with negative rules. */
function fieldsFromTx(tx: TXReadItem): DraftFields {
    const rule = getTypeRule(tx.type);
    let qty = tx.quantity;
    if (rule.quantityRule === 'negative' && Number(qty) < 0) qty = String(Math.abs(Number(qty)));
    let cash = tx.cash ? {code: tx.cash.code, amount: tx.cash.amount} : null;
    if (cash && rule.cashSign === 'negative' && Number(cash.amount) < 0) {
        cash = {code: cash.code, amount: String(Math.abs(Number(cash.amount)))};
    }
    return {
        broker_id: tx.broker_id,
        asset_id: tx.asset_id ?? null,
        type: tx.type as TransactionTypeCode,
        date: tx.date,
        quantity: qty,
        cash,
        tags: [...(tx.tags ?? [])],
        description: tx.description ?? '',
        asset_event_id: tx.asset_event_id ?? null,
        cost_basis_override: tx.cost_basis_override ?? '',
    };
}
```

**Nuova `editOpFromTx(txId: number): PendingOp`** (~8 LOC):
```typescript
/** Create an edit PendingOp from an existing DB transaction. */
function editOpFromTx(txId: number): PendingOp {
    const tx = txStoreGet(txId)!;
    return {op: 'edit', tempId: generateUUID(), txId, fields: fieldsFromTx(tx), markedDelete: false};
}
```

**Nuova `createOpFromClone(tx: TXReadItem, linkUuid?: string | null): PendingOp`** (~5 LOC):
```typescript
/** Create a create PendingOp by cloning fields from a TXReadItem. */
function createOpFromClone(tx: TXReadItem, linkUuid?: string | null): PendingOp {
    const fields = fieldsFromTx(tx);
    fields.date = todayIso();
    return {op: 'create', tempId: generateUUID(), fields, link_uuid: linkUuid ?? null};
}
```

**`emptyDraft()` → `createOpEmpty()`** (~10 LOC): sostanzialmente identica all'attuale `emptyDraft()`, ritorna `PendingOp` con `op: 'create'`.

**Impatto callsite**:
- `resolveInitialRows()` riga 291: `rows.map(r => fromTx(r, initSt))` → riscritto per usare `editOpFromTx()` / `createOpFromClone()` a seconda dell'intent
- `resetRow()` riga 555: `fromTx(d.original!)` → `editOpFromTx(op.txId)` — l'originale viene direttamente dal txStore
- `resetAll()` riga 568: stessa logica
- `cloneRow()` riga 538: `{...src, ...}` → `createOpFromClone(draftToTxLike(src))`

**LOC stimato**: `fromTx` 35 LOC → `fieldsFromTx` 12 + `editOpFromTx` 8 + `createOpFromClone` 5 = **−10 netti**.

---

### Step 4 — Migrare mutatori e sanitizers a `PendingOp`

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

**`applyFormPayload(target: DraftFields, p: Record<string, unknown>)`** — cambia il tipo del primo argomento da `DraftRow` a `DraftFields`. Rimuovere l'assegnazione di `link_uuid` (riga 507) — `link_uuid` non è in `DraftFields`, è sul variant `create`.

**`patchRowFromForm(tempId, payload)`** — opera su `op.fields` anziché sullo spread flat:
```typescript
function patchRowFromForm(tempId: string, payload: Record<string, unknown>) {
    ops = ops.map((op) => {
        if (op.tempId !== tempId) return op;
        const updated = {...op, fields: {...op.fields}};
        applyFormPayload(updated.fields, payload);
        return updated;
    });
}
```

**`patchDualRowFromForm(tempId, payload)`** — stessa logica, opera su `op.fields` + `op.partnerPayload`:
```typescript
function patchDualRowFromForm(tempId: string, payload: Record<string, unknown>) {
    const items = payload._items as Record<string, unknown>[];
    if (!items || items.length < 2) { patchRowFromForm(tempId, payload); return; }
    ops = ops.map((op) => {
        if (op.tempId !== tempId) return op;
        const updated = {...op, fields: {...op.fields}};
        applyFormPayload(updated.fields, items[0]);
        updated.partnerBrokerId = (items[1].broker_id as number) ?? 0;
        updated.partnerCash = (items[1].cash as {code: string; amount: string} | null) ?? null;
        updated.partnerDate = (items[1].date as string) ?? updated.fields.date;
        updated.partnerPayload = items[1] as unknown as TxFields;
        return updated;
    });
}
```

**`addDualRowFromForm(payload)`** — stesso pattern: crea `createOpEmpty()`, applica `items[0]` a `fields`, salva `items[1]` in `partnerPayload`.

**`markDelete(tempId)`** — per `op='edit'`: toggle `markedDelete`. Per `op='create'`: rimuovere dalla lista (non ha senso "marcare per cancellazione" qualcosa che non esiste ancora).

**`removeRow(tempId)`** — invariato (`ops = ops.filter(...)`).

**`resetRow(tempId)`** — per `op='edit'`: `editOpFromTx(op.txId)` + preservare `addedViaPicker`. Per `op='create'`: reset fa `createOpEmpty()`.

**`resetAll()`** — stessa logica, iterare.

**`collectCreate(op)`** e **`collectUpdate(op)`** — usano `opToTxFields(op)` anziché `draftToTxFields(d)`:
```typescript
function opToTxFields(op: PendingOp): TxFields {
    return {
        ...op.fields,
        link_uuid: op.op === 'create' ? op.link_uuid : null,
    };
}
```
`collectUpdate` non ha più bisogno di `d.original` — legge da `txStoreGet(op.txId)`:
```typescript
function collectUpdate(op: PendingOp & {op: 'edit'}): Record<string, unknown> | null {
    const orig = txStoreGet(op.txId);
    if (!orig) return null;
    const rule = getTypeRule(op.fields.type);
    const origRule = getTypeRule(orig.type as TransactionTypeCode);
    return buildUpdateDiff(opToTxFields(op), orig as unknown as TxOriginal, rule, origRule);
}
```

---

### Step 5 — Migrare `deriveStatus()`, commit, validate, serialize

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

**`deriveStatus(op: PendingOp)`** — semplificato:
```typescript
function deriveStatus(op: PendingOp): 'new' | 'edited' | 'original' | 'delete' {
    if (op.op === 'create') return 'new';
    if (op.markedDelete) return 'delete';
    const orig = txStoreGet(op.txId);
    if (!orig) return 'original';
    const diff = collectUpdate(op as PendingOp & {op: 'edit'});
    if (diff && Object.keys(diff).length > 1) return 'edited';
    if (op.partnerPayload && op.partnerId != null) {
        const partnerOrig = txStoreGet(op.partnerId);
        if (partnerOrig) {
            const partnerUpd = diffDualItem(
                op.partnerPayload as unknown as Record<string, unknown>,
                partnerOrig as unknown as TxOriginal,
            );
            if (Object.keys(partnerUpd).length > 1) return 'edited';
        }
    }
    return 'original';
}
```

**`commit()`** (righe 817-898) — stessa logica, cambia `d.id` → `op.txId`, `d._partnerId` → `op.partnerId`, ecc. Meccanico.

**`getBulkContextExcluding()`** (righe 602-628) — stessa logica, cambia accesso campi.

**`serializeDrafts()`** (riga 346) → rinominare `serializeOps()`. Serializza `op.fields` + (se edit) `op.txId`. Eliminare il confronto con `d.original`.

**Validate scheduler** — `enabled` e `validateFn` usano `ops` anziché `drafts`.

**`collapsePairedDrafts()`** — rinominare `collapsePairedOps()`. Opera su `PendingOp[]` anziché `DraftRow[]`, accede a `op.fields.broker_id` ecc. Per il confronto `cashAmt`: nel caso `op='edit'` legge l'`original` da `txStoreGet(op.txId)` per determinare from/to.

---

### Step 6 — Migrare rendering: `draftToTxLike`, colonne, row actions

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

**`draftToTxLike(op: PendingOp): TXReadItem`** — per passare alla FormModal:
```typescript
function opToTxLike(op: PendingOp): TXReadItem {
    return {
        id: op.op === 'edit' ? op.txId : 0,
        broker_id: op.fields.broker_id,
        asset_id: op.fields.asset_id,
        type: op.fields.type,
        date: op.fields.date,
        quantity: op.fields.quantity,
        cash: op.fields.cash,
        related_transaction_id: op.partnerId ?? (op.partnerBrokerId != null ? -1 : null),
        tags: op.fields.tags,
        description: op.fields.description,
        cost_basis_override: op.fields.cost_basis_override || null,
        asset_event_id: op.fields.asset_event_id,
    };
}
```

**Column `renderFn`** — tutte le colonne che accedono a `row.broker_id`, `row.date`, `row.type` ecc. devono diventare `row.fields.broker_id`, `row.fields.date`, `row.fields.type`. Sono ~20 punti nel blocco colonne (righe ~900-1200). Cambiamento meccanico, nessuna logica diversa.

**`getRowClass(op: PendingOp)`** — già usa `deriveStatus()`, nessun cambio funzionale.

**`openEditRowForm(op: PendingOp)`** — usa `opToTxLike(op)` anziché `draftToTxLike(row)`.

**`populatePartnerDisplay(op: PendingOp)`** — accede a `op.fields` per la parte "from", legge txStore per partner. Cambia i nomi dei campi: `op._partnerId` → `op.partnerId`, `op._partnerFormPayload` → `op.partnerPayload`.

**Row actions** — `markDelete`, `cloneRow`, `resetRow`, `removeRow` — i callback ricevono `op.tempId`, invariato come parametro.

---

### Step 7 — Rinominare `drafts` → `ops` globalmente

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

Atomic find-and-replace: `drafts` → `ops` in tutte le ~80 occorrenze. Include:
- `let ops = $state<PendingOp[]>([])` (riga 203)
- Tutti i `.map()`, `.filter()`, `.find()`, `.some()`, `.length` references
- Template bindings (`{#each}`, `{#if ops.length}`)
- `serializeOps(ops)` (era `serializeDrafts(drafts)`)

Nota: `visibleDrafts` → `visibleOps` per lo stesso principio.

---

### Step 8 — Cleanup finale: commenti, header, dead code

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

1. Aggiornare commento header (righe 1-31) con nuova terminologia `PendingOp`
2. Rimuovere commenti legacy che referenziano concetti eliminati:
   - `// B1-13: partner data for paired types` → non più necessario (è in `PartnerDisplay`)
   - `// R6-B.4:` prefissi → il bug è risolto strutturalmente
   - `// Bugfix-N §X:` commenti che descrivono workaround ora eliminati
3. Eliminare funzioni morte:
   - `draftToTxFields()` (sostituita da `opToTxFields()`)
   - `draftToTxLike()` (sostituita da `opToTxLike()`)
4. Verificare che nessun `as any` residuo referenzi il vecchio `DraftRow`

---

### Step 9 — Verifiche

```bash
# 1. Type-check — zero errori svelte-check
./dev.py lint-format frontend

# 2. Tutti i 9 transaction spec files (68+ test)
./dev.py test front-transaction all

# 3. Full frontend suite (include asset, FX, utility, broker, user)
./dev.py test all-frontend
```

Tutti i test usano solo `data-testid` e interazione UI → il refactor interno è trasparente. Nessun test contiene `DraftRow`, `fromTx`, `initialRows`.

---

## Riepilogo file modificati

| File | Tipo | Step |
|------|------|------|
| `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` | Refactor: `DraftRow` → `PendingOp` + `DraftFields`, elimina `fromTx`, props legacy, rinomina `drafts` → `ops`, stringe `partnerPayload` type | 1–8 |

**Solo 1 file modificato** — tutto il refactor è interno alla BulkModal. `+page.svelte`, `txStore.svelte.ts`, `txPayloadHelpers.ts`, `TransactionFormModal.svelte`, `TransactionPickerModal.svelte` **non cambiano**.

## LOC target

| File | Prima | Dopo (stima) | Delta |
|------|-------|-------------|-------|
| `TransactionBulkModal.svelte` | 1819 | ~1720 | ~−100 (−5%) |

Il delta LOC è modesto perché il refactor è di **qualità strutturale** (type safety, single source of truth, eliminazione `original` copies) più che di riduzione bruta. Il beneficio è nella manutenibilità: ogni `PendingOp` ha un tipo stretto che rende impossibile i bug eliminati nei Piani C/C2.

## Rischi e mitigazioni

| Rischio | Prob. | Mitigazione |
|---------|-------|-------------|
| Regressione paired edit/create | Media | 68+ E2E test coprono tutti i path paired |
| `DataTable<PendingOp>` type mismatch | Bassa | `getRowId` usa `op.tempId`, col renderFn accede a `.fields.*` |
| Column access `.fields.X` dimenticato | Bassa | svelte-check cattura type errors su `PendingOp.X` inesistente |
| Breaking per BRIM staging (Part 5) | Zero | Part 5 userà `WorkspaceIntent` + `PendingOp` create direttamente |

## Benefici per Piano D (Split/Promote)

| Concetto Piano D | Come beneficia di PendingOp |
|-------------------|-----------------------------|
| Split action | `op.markedDelete = true` su un lato → `ops.push(createOpEmpty())` per il lato sganciato. Nessun `fromTx`/`original` da gestire |
| Promote endpoint | Due `edit` ops con `markedDelete=false` + nuovo `link_uuid` condiviso. Type-safe via variant discriminator |
| WorkspaceIntent estensione | `{action: 'split', txIds: [id]}` → resolveInitialRows aggiunge ~10 LOC |

## Post-implementazione

### Esecuzione (2026-05-11)

Il refactor è stato eseguito in 2 passaggi:

**Passaggio 1** (grep-based bulk rename — parziale):
- Applicato rename `drafts` → `ops` globale
- Applicato rename `DraftRow` → `PendingOp` / `DraftFields`
- Applicato rename `_partnerId` → `partnerId`, `_partnerFormPayload` → `partnerPayload`
- Rimossi props legacy, `fromTx()`, `draftToTxFields()`, `draftToTxLike()`, `mergePairedRows()`
- Introdotti `collectCreate()`, `collectUpdate()`, `opToTxFields()`, `opToTxLike()`
- Aggiornato header comment

**Passaggio 2** (fix errori residui — manuale):
Dopo il primo passaggio restavano 5 errori di compilazione + 1 warning (unused function):

| Riga | Errore | Fix |
|------|--------|-----|
| 339 | `serializeOps(drafts)` — `drafts` non esiste | → `serializeOps(ops)` |
| 554 | `getTypeRule(d.type)` — `PendingOp` non ha `.type` top-level | → `getTypeRule(d.fields.type)` |
| 733 | `drafts[i].broker_id` — `drafts` non esiste + campo flat | → `ops[i].fields.broker_id` |
| 738 | `drafts[i].cash?.code` — idem | → `ops[i].fields.cash?.code` |
| 988 | `row.date` — `PendingOp` ha `.fields.date` | → `row.fields.date` |
| 906 | `assetName()` unused (sostituita da `renderAssetHtml()`) | Rimossa |

**Warnings residui** (3): `onerror` attribute marcato "obsolete" da svelte-check su stringhe HTML template (`renderTypeHtml`, `renderAssetHtml`, `renderBrokerHtml`). Falsi positivi — l'attributo `onerror` è su raw HTML iniettato via `{@html}`, non su elementi Svelte reali. Non richiede intervento.

### LOC effettivi

| File | Prima | Dopo | Delta |
|------|-------|------|-------|
| `TransactionBulkModal.svelte` | 1819 | 1748 | −71 (−4%) |


## Step 9b — Test E2E aggiuntivi (copertura gap pre-Piano D) ✅

Analisi gap sulla suite attuale (84 test / 9 file): tre aree non coperte che diventano critiche con Piano D.

**Esecuzione**: 2026-05-12 — 10/10 passed (59.7s).

### Prerequisito — Aggiungere `data-action-id` al DataTable ✅

**File**: `frontend/src/lib/components/table/DataTable.svelte` (riga ~1358)

**Modifica**: aggiungere `data-action-id={action.id}` al `<button class="action-btn">` nel loop `{#each rowActions as action}`.

```svelte
<!-- Era: -->
<button type="button" class="action-btn" ...>

<!-- Diventa: -->
<button type="button" class="action-btn" data-action-id={action.id} ...>
```

**Motivo**: i title dei bottoni sono i18n → fragili come selector. `data-action-id` è stabile e testabile con `[data-action-id="remove-from-batch"]`.

### Helper — `clickRowAction(row, actionId)` ✅

Aggiungere in cima a `tx-bulk-operations.spec.ts`:

```typescript
/** Hover a BulkModal row and click the action button by its stable action-id. */
async function clickRowAction(row: Locator, actionId: string) {
    await row.hover();
    const btn = row.locator(`[data-action-id="${actionId}"]`);
    await expect(btn).toBeVisible({timeout: 2_000});
    await btn.click();
    await row.page().waitForTimeout(300);
}
```

---

### Test 1 — Picker add → remove from batch (`addedViaPicker`) ✅

**File**: `frontend/e2e/transactions/tx-bulk-operations.spec.ts`

**Flow**:
1. Seleziona 1 riga editable → toolbar Edit → BulkModal apre
2. Chiudi FormModal auto-opened
3. Nota il count iniziale di righe nella griglia BulkModal (`countBefore`)
4. Clicca `[data-testid="tx-bulk-picker"]` → Picker apre
5. Seleziona 1 riga nel Picker (checkbox sulla prima non-disabled) → clicca `[data-testid="tx-picker-add"]`
6. Picker si chiude, griglia BulkModal ha +1 riga (`countBefore + 1`)
7. Sulla riga appena aggiunta (ultima): verifica `[data-action-id="remove-from-batch"]` è visibile (via hover)
8. Click `[data-action-id="remove-from-batch"]` → riga sparisce
9. Griglia torna a `countBefore` righe

**Assertions chiave**:
- `expect(countAfterAdd).toBe(countBefore + 1)`
- action `remove-from-batch` visibile solo sulla riga picker-added
- `expect(countAfterRemove).toBe(countBefore)`

**Perché serve per Piano D**: Split crea righe `addedViaPicker`-like che l'utente deve poter rimuovere.

---

### Test 2 — Reset All ripristina tutte le righe modificate ✅

**File**: `frontend/e2e/transactions/tx-bulk-operations.spec.ts`

**Flow**:
1. Seleziona 3+ righe editable → toolbar Edit → BulkModal apre (no auto-form per 3+)
2. Dblclick riga 1 → FormModal → cambia description → Save → torna in griglia
3. Dblclick riga 2 → FormModal → cambia description → Save → torna in griglia
4. Sulla riga 3: `clickRowAction(row3, 'mark-delete')` → riga marcata
5. Verifica header `[data-testid="tx-bulk-title"]` contiene testo con `edit` E `del`
6. Verifica commit non è disabled (c'è almeno 1 azione)
7. Clicca `[data-testid="tx-bulk-reset-all"]`
8. Verifica: nessuna riga ha class `row-edited` o `row-deleted`
9. Verifica: commit IS disabled (nessuna azione pendente)
10. Verifica: header title NON contiene più `edit` o `del`

**Assertions chiave**:
- Pre-reset: `expect(title).toContain('edit')` e `toContain('del')`
- Post-reset: `expect(commitBtn).toBeDisabled()`
- Post-reset: `expect(page.locator('.row-edited, .row-deleted')).toHaveCount(0)`

**Perché serve per Piano D**: Split/Promote modifica più righe simultaneamente — reset all deve annullare tutto atomicamente.

---

### Test 3 — Status CSS classes: new / edited / delete / original ✅

**File**: `frontend/e2e/transactions/tx-bulk-operations.spec.ts`

**Flow**:
1. Seleziona 1 riga editable → toolbar Edit → BulkModal
2. Chiudi FormModal auto-opened
3. **Original**: verifica la riga NON ha classi `row-edited`, `row-deleted`, `row-appended`
4. **Edited**: dblclick → FormModal → cambia description → Save → verifica riga ha class `row-edited`
5. **Delete**: `clickRowAction(row, 'mark-delete')` → verifica riga ha class `row-deleted` (e NON `row-edited` — delete prevale)
6. **Reset → Original**: `clickRowAction(row, 'reset')` → verifica riga NON ha più classi speciali
7. **New (row-appended)**: `clickRowAction(row, 'clone')` → verifica nuova riga (last) ha class `row-appended`

**Assertions chiave**:
- `expect(row).toHaveClass(/row-edited/)` (step 4)
- `expect(row).toHaveClass(/row-deleted/)` (step 5)
- `expect(row).not.toHaveClass(/row-edited|row-deleted|row-appended/)` (steps 3, 6)
- `expect(newRow).toHaveClass(/row-appended/)` (step 7)

**Perché serve per Piano D**: Split cambia lo status di righe esistenti (edit → delete + new) — il feedback visivo deve essere corretto.

---

### Registrazione nel test runner ✅

Nessuna registrazione necessaria: i 3 test vanno in `tx-bulk-operations.spec.ts` che è già registrato nel runner sotto `front-transaction tx-bulk-operations`.

### Riepilogo file modificati (Step 9b)

| File | Modifica |
|------|----------|
| `frontend/src/lib/components/table/DataTable.svelte` | +1 attributo `data-action-id={action.id}` su `button.action-btn` |
| `frontend/e2e/transactions/tx-bulk-operations.spec.ts` | +1 helper `clickRowAction` + 3 test (~120 LOC) |

---

### Verifiche

| Verifica | Stato | Note |
|----------|-------|------|
| `svelte-check --threshold error` | ✅ 0 errors, 0 warnings | Confermato 2026-05-11 |
| `./dev.py test front-transaction tx-bulk-operations` | ✅ 10/10 passed (59.7s) | Confermato 2026-05-12, include 3 nuovi test |
| `./dev.py test front-transaction all` | ✅ 9/9 suites passed | Confermato 2026-05-12 |
| `./dev.py test all-frontend` | ✅ 6/6 suites passed | Confermato 2026-05-12 |
| Ingestione wiki | ✅ Completata | 2026-05-12: 2 nuove pagine + 5 aggiornate |

---

## Link forward

→ **Piano D**: Split/Promote full stack (UC27-UC28) — dipende da questo piano.

