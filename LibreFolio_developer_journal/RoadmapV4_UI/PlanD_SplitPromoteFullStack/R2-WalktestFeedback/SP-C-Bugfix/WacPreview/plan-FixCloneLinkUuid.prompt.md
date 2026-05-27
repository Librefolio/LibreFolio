# Plan: Fix Clone `link_uuid` + Simplify WAC linkUuidMap

> **✅ STATUS (2026-05-27)**: COMPLETATO — `link_uuid` promosso a top-level, clone e collapsePairedOps generano UUID per paired types, WAC semplificato a lettura diretta, 25/25 E2E ✅.

**Parent plan**: [`plan-ReactiveWacBulkModal.prompt.md`](./plan-ReactiveWacBulkModal.prompt.md) (Piano v6, Step v6.1 — workaround attuale)

---

## Problema

Il clone di paired rows (TRANSFER, FX_CONVERSION, CASH_TRANSFER) da righe DB **non genera `link_uuid`** perché la condizione riga 867 è:

```typescript
link_uuid: src.op === 'create' && src.link_uuid ? generateUUID() : null,
```

Se `src` è una edit op (riga DB), `src.op === 'create'` è `false` → `link_uuid: null`. Ma il tipo è paired → serve un UUID condiviso per il backend.

Questo obbliga `fetchBatchWac()` a costruire una `linkUuidMap` complessa con 3 branch (create with link_uuid, pairedWith, getPartnerOp) come workaround.

### Root Cause

Il clone non tratta "tipo paired" ma "source aveva link_uuid" — logica sbagliata. Una transazione clonata è identica a una "new" pre-compilata. Se il tipo è paired → deve avere `link_uuid`.

---

## Steps

### Step 1: Estendere tipo `PendingOp` — `link_uuid` al livello comune ✅

**Completato**: 2026-05-27

> **Note implementazione**: `link_uuid` spostato dalla union `{op:'create'; link_uuid}` al livello comune `& {...; link_uuid?: string | null; ...}`. Zero errori di tipo — tutte le reference esistenti funzionano perché il campo era già acceduto tramite type narrowing o cast.

**File**: `TransactionBulkModal.svelte`, riga 94

Spostare `link_uuid` dalla union `create`-only al livello comune, opzionale su entrambi:

```typescript
// BEFORE
type PendingOp = ({op: 'create'; link_uuid: string | null} | {op: 'edit'; ...}) & {tempId; fields; pairedWith?; ...};

// AFTER
type PendingOp = ({op: 'create'} | {op: 'edit'; txId: number; markedDelete: boolean; addedViaPicker?: boolean}) & {tempId: string; fields: DraftFields; pairedWith?: string; link_uuid?: string | null; inaccessible?: boolean};
```

Questo permette sia create che edit ops di avere `link_uuid`.

### Step 2: Fix `cloneRow()` — generare `link_uuid` per tipi paired ✅

**Completato**: 2026-05-27

> **Note implementazione**: Cambiato `src.op === 'create' && src.link_uuid ? generateUUID() : null` → `getTypeRule(src.fields.type as TransactionTypeCode)?.requiresPair ? generateUUID() : null`. Ora il clone genera UUID in base al tipo, non al source.

**File**: `TransactionBulkModal.svelte`, funzione `cloneRow()` ~riga 867

```typescript
// BEFORE
link_uuid: src.op === 'create' && src.link_uuid ? generateUUID() : null,

// AFTER
link_uuid: getTypeRule(src.fields.type as TransactionTypeCode)?.requiresPair ? generateUUID() : null,
```

### Step 3: Propagare `link_uuid` in `collapsePairedOps()` — edit ops paired ✅

**Completato**: 2026-05-27

> **Note implementazione**: Aggiunto `link_uuid` condiviso in 3 punti: (1) Pass 2 — collapse di edit ops in-batch entrambe presenti; (2) W4b placeholder (inaccessible partner); (3) hidden partner creato da txStore. In tutti i casi, `generateUUID()` condiviso tra main e partner.

**File**: `TransactionBulkModal.svelte`, funzione `collapsePairedOps()` ~riga 713

Dopo `opArr[toIdx].pairedWith = opArr[fromIdx].tempId;`, generare UUID condiviso:

```typescript
opArr[toIdx].pairedWith = opArr[fromIdx].tempId;
// Generate shared link_uuid for WAC payload
const sharedUuid = generateUUID();
opArr[fromIdx].link_uuid = sharedUuid;
opArr[toIdx].link_uuid = sharedUuid;
```

E per le hidden partner ops create da txStore (~riga 741-746):

```typescript
const sharedUuid = generateUUID();
d.link_uuid = sharedUuid;
const partnerOp: PendingOp = {
    op: 'edit', txId: relId, markedDelete: false,
    tempId: generateUUID(), fields: fieldsFromTx(partnerTx),
    pairedWith: d.tempId,
    link_uuid: sharedUuid,
};
```

### Step 4: Semplificare `linkUuidMap` in `fetchBatchWac()` ✅

**Completato**: 2026-05-27

> **Note implementazione**: Eliminata completamente la `linkUuidMap` (30 righe, 3 branch). Sostituita con lettura diretta `link_uuid: o.link_uuid ?? undefined` nel `.map()`. La Map intermedia non serve più perché tutte le paired ops hanno già `link_uuid` assegnato alla creazione.

**File**: `TransactionBulkModal.svelte`, funzione `fetchBatchWac()` ~righe 337-365

Sostituire i 3 branch con un semplice loop:

```typescript
// Build link_uuid map — all paired ops already have link_uuid set
const linkUuidMap = new Map<string, string>();
for (const o of nonDeleteOps) {
    if (o.link_uuid) linkUuidMap.set(o.tempId, o.link_uuid);
}
```

### Step 5: Aggiornare `createOp()` e `createOpFromClone()` + cleanup cast ✅

**Completato**: 2026-05-27

> **Note implementazione**: `createOpEmpty()` e `createOpFromClone()` non necessitavano modifiche — settavano già `link_uuid` che ora è top-level. Rimossi ~18 `(x as any).link_uuid` cast sparsi nel file. Rimossi guard `&& .op === 'create'` non più necessari su 4 assegnamenti `link_uuid`. Restano 2 cast legittimi su `(r as any).link_uuid` dove `r` è un `TXReadItem` (tipo API, non PendingOp).

Verificare che `createOp()` (riga 157) e `createOpFromClone()` (riga 200+) producano `link_uuid` coerente col nuovo schema. Il campo ora è top-level → aggiornare di conseguenza.

### Step 6: Verificare `opToTxFields()` ✅

**Completato**: 2026-05-27

> **Note implementazione**: Cambiato `d.op === 'create' ? d.link_uuid : null` → `d.link_uuid ?? null`. Ora edit ops paired passano il `link_uuid` a `buildCreatePayload`/`buildUpdateDiff` correttamente per il commit payload.

**File**: `TransactionBulkModal.svelte`, riga 1074

```typescript
// BEFORE
function opToTxFields(d: PendingOp): TxFields {
    return {...d.fields, link_uuid: d.op === 'create' ? d.link_uuid : null};
}

// AFTER — link_uuid is now on all ops
function opToTxFields(d: PendingOp): TxFields {
    return {...d.fields, link_uuid: d.link_uuid ?? null};
}
```

### Step 7: Run tests + type-check ✅

**Completato**: 2026-05-27

> **Note implementazione**: `get_errors` → 0 type errors (solo warnings pre-esistenti). E2E: `tx-commit-all-types` 19/19 + `tx-split-promote` 6/6 = 25/25 passed.

- `./dev.py front check` — 0 errors
- `npx playwright test e2e/transactions/tx-split-promote.spec.ts e2e/transactions/tx-commit-all-types.spec.ts --project desktop`

---

## Test Criteria

- [x] `./dev.py front check` — 0 errors
- [x] E2E `tx-split-promote` ✅
- [x] E2E `tx-commit-all-types` ✅
- [x] WAC `fetchBatchWac` `linkUuidMap` è un semplice 3-line loop (no branch pairedWith/getPartnerOp)
- [x] Clone di TRANSFER da riga DB → entrambe le create ops hanno `link_uuid` condiviso

---

## Note

- `pairedWith` **resta** come meccanismo UI (visibleOps, getPartnerOp, render, commit) — non viene eliminato dall'architettura
- `link_uuid` viene **promosso** da create-only a campo comune — necessario per il WAC payload delle edit ops paired
- Dopo questo fix, il link_uuid nel WAC payload è letto direttamente → nessun workaround necessario

