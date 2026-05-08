# Plan — Phase 07 · Part 4 · Round 6 · Piano C — txStore Refactor

**Date**: 2026-05-08
**Status**: ⏳ NOT STARTED
**Parent**: [`plan-phase07-transaction-Part4_Round6_PlanB23_Appendix1_UIPolish.prompt.md`](./plan-phase07-transaction-Part4_Round6_PlanB23_Appendix1_UIPolish.prompt.md)

---

## TL;DR

Estrarre le transazioni caricate dal DB in un `txStore.ts` standalone, unica fonte di verità. La BulkModal mantiene solo le "modifiche pendenti" (lista di istruzioni: create/edit/delete). Il diff store↔pendenti determina automaticamente lo status e il payload per commit/validate. Migrazione incrementale in 4 step.

---

## Motivazione — Root Cause strutturale

| Categoria bug | Occorrenze | Root cause | Risolto da txStore? |
|---|---|---|---|
| link_uuid fragile | 5 bug (R5B1, R5B2, B23-P3b, App1-D, oggi) | Generato in 4+ punti, ogni mutazione lo rigenera → orphaned partners | ✅ partner risolto via `related_transaction_id` dal DB |
| "edited" falso | 3 bug (B23, App1, oggi) | `patchRowFromForm` marca sempre edited, nessun diff | ✅ status derivato da diff vs txStore |
| dati duplicati/stale | 4 bug (R2, R5B2, B23-R2, App1-D) | 3 copie dei dati, copie divergono dopo mutazioni | ✅ fonte unica txStore |
| paired split dopo reset | 3 bug (B23-R3-Bug4, App1-Fix, oggi) | `resetRow` non chiama `mergePairedRows`, partner orfano | ✅ paired sempre risolti da `txStore.getPartner()` |
| props cascade viewer-only | 2 bug (B23-R2-Bug1, App1-D) | guard viewer duplicato in 3+ punti | ✅ centralizzato in `txStore.canEdit()` |

---

## Architettura proposta

```text
txStore (nuovo, ~120 LOC)
├── Map<number, TXReadItem>     ← unica fonte di verità
├── setAll(main, partners)      ← chiamato da reload()
├── get(id) → TXReadItem        
├── getPartner(id) → TXReadItem ← via related_transaction_id
├── getAll() → TXReadItem[]     ← per Picker, tabella
├── getFiltered(filterFn)       ← filtri custom
├── canEdit(id) → boolean       ← viewer guard centralizzato
└── invalidate()                ← dopo commit/delete
```

```typescript
WorkspaceIntent = 
  | { action: 'create' }                          // UC1, UC2
  | { action: 'edit', txIds: number[] }            // UC4-UC8
  | { action: 'delete', txIds: number[] }          // UC13
  | { action: 'clone', txIds: number[] }           // UC9, UC10
```

```typescript
// Modifiche pendenti nella BulkModal
PendingOp =
  | { op: 'create', draft: TxFields }             // nuova TX
  | { op: 'edit', txId: number, overrides: Partial<TxFields> }  // modifica
  | { op: 'delete', txId: number }                // marcata per eliminazione
```

**Status derivato**:
- `op=create` → `new`
- `op=edit` e overrides non vuoti → `edited`
- `op=delete` → `delete`
- altrimenti → `original`

---

## Catalogo Use Case coperti (26+2 future)

### CREATE
| # | Use Case | Come funziona con txStore |
|---|---|---|
| UC1 | Add singola TX | `workspace.open({action:'create'})` → BulkModal apre FormModal vuota → draft con txId=undefined, status=new |
| UC2 | Add paired TX | `workspace.open({action:'create'})` → FormModal in modalità dual → draft senza txId |
| UC3 | Add N TX da grid bulk | BulkModal → FormModal(create) → push draft con op=create |

### EDIT
| # | Use Case | Come funziona con txStore |
|---|---|---|
| UC4 | Edit singola standalone | `workspace.open({action:'edit', txIds:[38]})` → BulkModal legge `txStore.get(38)` → FormModal |
| UC5 | Edit singola paired | `workspace.open({action:'edit', txIds:[38]})` → `txStore.get(38)` + `txStore.getPartner(38)` → merge automatico → FormModal dual |
| UC6 | Edit bulk N righe | `workspace.open({action:'edit', txIds:[...]})` → `canEdit` check → draft per ogni id |
| UC7 | Edit da BulkModal grid | Dblclick → `txStore.get(draft.txId)` per popolare FormModal |
| UC8 | Edit paired da BulkModal | Dblclick → `txStore.getPartner()` → FormModal dual |

### CLONE
| # | Use Case | Come funziona con txStore |
|---|---|---|
| UC9 | Clone singola | `workspace.open({action:'clone', txIds:[id]})` → draft con txId=undefined, campi copiati da `txStore.get(id)` |
| UC10 | Clone bulk N | `workspace.open({action:'clone', txIds:[...]})` → N draft senza txId |

### DELETE
| # | Use Case | Come funziona con txStore |
|---|---|---|
| UC11 | Delete singola standalone | Invariato — DeleteModal legge da `txStore.get(id)` anziché da prop |
| UC12 | Delete singola paired | DeleteModal legge `txStore.get(id)` + `txStore.getPartner(id)` |
| UC13 | Delete bulk N | BulkModal: draft con op=delete → al commit incluso in deletes[] |
| UC14 | Mark delete in BulkModal | `draft.op = 'delete'` |
| UC15 | Unmark delete = reset | `draft.overrides = {}` → status torna original |

### PICKER
| # | Use Case | Come funziona con txStore |
|---|---|---|
| UC16 | Picker add TX dal DB | PickerModal legge `txStore.getAll()` direttamente → zero props |
| UC17 | Picker paginazione | PickerModal: stato interno via `$state` |
| UC18 | Picker guard viewer-only | `txStore.canEdit(id)` per disabledIds |

### RESET
| # | Use Case | Come funziona con txStore |
|---|---|---|
| UC19 | Reset singola riga | `draft.overrides = {}` → status torna original (dato letto da `txStore.get(txId)`) |
| UC20 | Reset tutte | Reset overrides di tutti i draft |
| UC21 | Reset selezionati | Reset overrides dei selezionati |
| UC22 | Remove from batch (picker) | Rimuove draft da array → tx torna disponibile nel Picker |

### VALIDATE
| # | Use Case | Come funziona con txStore |
|---|---|---|
| UC23 | Validate live (auto) | Diff calcolato: overrides vs `txStore.get(txId)` → payload per /validate |
| UC24 | Validate now (manual) | Stessa logica, trigger manuale |

### COMMIT
| # | Use Case | Come funziona con txStore |
|---|---|---|
| UC25 | Commit batch | `creates` = draft senza txId, `updates` = draft con txId + diff non vuoto, `deletes` = draft con op=delete |
| UC26 | Confirm delete | DeleteModal chiama DELETE direttamente → `txStore.invalidate()` → reload |

### FUTURE (Piano D)
| # | Use Case | Come funziona con txStore |
|---|---|---|
| UC27 | Promote pair | `workspace.open({action:'promote', txIds:[a,b]})` → nuovo intent, ~50 LOC |
| UC28 | Split pair | `workspace.open({action:'split', txIds:[id]})` → nuovo intent, ~50 LOC |

---

## Steps

### Step 1 — Creare `txStore.ts` (~120 LOC)

**File**: `frontend/src/lib/stores/txStore.ts` (o `.svelte.ts` se serve reattività Svelte 5)

**API**:
- `setAll(main: TXReadItem[], partners: TXReadItem[])` — sovrascrive in blocco, popola Map
- `get(id: number) → TXReadItem | undefined`
- `getPartner(id: number) → TXReadItem | undefined` — via `related_transaction_id`
- `getAll() → TXReadItem[]`
- `getFiltered(filterFn: (tx: TXReadItem) => boolean) → TXReadItem[]`
- `canEdit(id: number) → boolean` — viewer guard centralizzato (controlla broker access)
- `invalidate()` — svuota + segnala che serve reload

**Popolamento**: chiamato UNA volta da `+page.svelte` nel `reload()`, passando i risultati delle fetch attuali.

**Test**: dopo Step 1, i test E2E devono ancora passare (txStore è solo addizionale, non usato ancora).

---

### Step 2 — Migrare `TransactionPickerModal`

**Obiettivo**: rimuovere props `mainRows`/`partnerRows`/`brokers`, leggere tutto da txStore.

**Cambi**:
- PickerModal importa `txStore` e chiama `txStore.getAll()`
- `excludeIds` calcolato internamente dalla BulkModal (set di txId dei draft correnti), passato come unica prop
- Rimuovere callback pagination esterna (ora interni via `$state`)
- `canEdit()` dal txStore per disabledIds + tooltip viewer

**Test**: `./dev.py test front-transaction all` dopo completamento.

---

### Step 3 — Migrare `TransactionBulkModal`

**Obiettivo**: sostituire l'array di `DraftRow` con copia completa con `PendingOp[]` + derivazione status.

**Cambi**:
- Le "modifiche pendenti" diventano un array tipizzato
- Il rendering della griglia fa `txStore.get(txId)` + merge con overrides
- Status derivato automaticamente (nessun `markEdited()` manuale)
- `fromTx()`, `mergePairedRows()`, `resetRow()`, `patchDualRowFromForm()` riscritti sulla nuova base
- **link_uuid scompare** — paired risolti da `txStore.getPartner()`
- Hidden row non serve più: riga paired renderizzata come "riga doppia" leggendo entrambi i lati dallo store

**Impatto LOC stimato**: BulkModal 1766 → ~1200 (-30%)

**Test**: `./dev.py test front-transaction all` dopo completamento.

---

### Step 4 — Semplificare `+page.svelte`

**Obiettivo**: rimuovere duplicazione dati e props cascade.

**Cambi**:
- Rimuovere variabili `allMainRows`/`allPartnerRows`
- Rimuovere `filterEditableRows` (ora `txStore.canEdit()`)
- Rimuovere duplicazione partner lookup
- Le azioni toolbar passano solo `{action, txIds}` alla BulkModal (WorkspaceIntent)
- `reload()` popola `txStore.setAll()` e basta

**Impatto LOC stimato**: +page 1035 → ~700 (-30%)

**Test**: `./dev.py test front-transaction all` dopo completamento.

---

### Step 5 — Test di non-regressione finale

- `./dev.py test front-transaction all` — tutti i 5 spec file
- Verifica manuale: create, edit, clone, delete (singola + paired + bulk)
- Verifica Picker funzionante
- Verifica guard viewer-only

---

## Further Considerations

1. **DraftRow con overrides vs copia completa?** → Raccomando la **copia completa** (più semplice per il rendering) con status derivato da diff vs `txStore.get(txId)`. Il diff è un semplice `Object.keys(draft).filter(k => draft[k] !== txStore.get(txId)[k])`.

2. **txStore vs mantenerlo in +page?** → Lo store SPA-wide è necessario perché sia Picker che BulkModal ne hanno bisogno senza props. Un `Map<number, TXReadItem>` con 500 TX ≈ 200KB — trascurabile.

3. **Migrazione incrementale possibile?** → Sì: (1) creare txStore + popolarlo → (2) migrare Picker → (3) migrare BulkModal → (4) semplificare +page. Ogni step testabile indipendentemente.

4. **Paired rendering in griglia BulkModal**: il partner si ottiene con `txStore.getPartner(txId)` — un solo punto, zero `mergePairedRows`. La hidden row scompare.

5. **FormModal**: resta invariata — riceve `initialRow` + opzionale `partnerRow`. La BulkModal glieli passa leggendo da txStore + applicando overrides.

6. **DeleteModal**: impatto minimo — continua a ricevere transaction + partner come props, ma il parent li legge da txStore.

---

## Pro/Contro

| Aspetto | Refactor (txStore) | Status quo (patch) |
|---|---|---|
| Effort | ~2-3 giorni | Già fatto (patch) |
| Bug link_uuid | ✅ Eliminato (non serve più) | ⚠️ 3 workaround stratificati |
| Bug edited falso | ✅ Status derivato automaticamente | ⚠️ 1 workaround (diff check) |
| Bug paired reset | ✅ Partner sempre da txStore | ⚠️ 2 workaround (re-merge) |
| Copertura UC | ✅ Tutti i 28 UC coperti | ✅ Funzionano (con patch) |
| LOC nette | BulkModal: -30%, +page: -30%, +txStore ~120 | BulkModal: 1766+patch |
| Rischio regressione | 🟡 Medio — test E2E mitigano | 🟢 Basso |
| Manutenibilità futura | ✅ Split/Promote = +1 intent, ~50 LOC | ⚠️ +branching in 3 file |
| Piano D (Split/Promote) | Triviale: nuovo intent + endpoint | Serve piano dettagliato |
| Part 5 (BRIM staging) | Triviale: txStore già alimentato | Serve altra prop cascade |

---

## Successors

- **Piano D**: Split/Promote full stack (UC27-UC28) — dipende da questo piano (descritto nel master plan Round 6)
- **Part 5 (BRIM staging)**: `plan-phase07-transaction-Part5_BRIMStaging.prompt.md` — beneficia di txStore


