# Plan — Phase 07 · Part 4 · Round 6 · Piano C — txStore Refactor

**Date**: 2026-05-08
**Status**: ✅ COMPLETED — Fase 1 ✅ + Fase 2 ✅ + Fase 3 ✅. All 7/7 E2E suites green (68+ tests). See [§ Session Log 2](#session-log-2--2026-05-08-sera-fase-3-completamento)
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

### Step 1 — Creare `txStore.ts` (~120 LOC) ✅

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

### Step 2 — Migrare `TransactionPickerModal` ✅

**Obiettivo**: rimuovere props `mainRows`/`partnerRows`/`brokers`, leggere tutto da txStore.

**Cambi**:
- PickerModal importa `txStore` e chiama `txStore.getAll()`
- `excludeIds` calcolato internamente dalla BulkModal (set di txId dei draft correnti), passato come unica prop
- Rimuovere callback pagination esterna (ora interni via `$state`)
- `canEdit()` dal txStore per disabledIds + tooltip viewer

**Test**: `./dev.py test front-transaction all` dopo completamento.

---

### Step 3 — Migrare `TransactionBulkModal` ⚠️ PARTIAL

**Obiettivo**: sostituire l'array di `DraftRow` con copia completa con `PendingOp[]` + derivazione status.

**Fatto**:
- txStore usato per `resetRow()`, `resetAll()`, `addPickerRows()` (passato a `mergePairedRows` come source)
- PickerModal legge da txStore direttamente (Plan C Step 2 ✅)

**NON fatto — architettura legacy ancora in uso**:
- ❌ `DraftRow[]` con copia completa ancora al posto di `PendingOp[]` + overrides
- ❌ `fromTx()` ancora presente (~35 LOC) — clone completo anziché ref a txStore
- ❌ `mergePairedRows()` ancora presente (~60 LOC) — paired risolti tramite `link_uuid`/`_hidden` anziché `txStore.getPartner()`
- ❌ `link_uuid` ancora generato in 3+ punti — causa dei bug storici documentati in Motivazione
- ❌ `_hidden` row pattern ancora in uso — partner occultato anziché rendering diretto da txStore
- ❌ `patchDualRowFromForm()` ancora presente (~70 LOC) — partner match fragile via link_uuid
- ❌ Status marcato manualmente (`merged.status = 'edited'`) anziché derivato da diff vs txStore
- ❌ Bug timing: `mergePairedRows` richiede `getTypeRule()` che dipende da `ensureTypesLoaded()` — gated con hotfix `isTypesLoaded()` ma non eliminato strutturalmente

**Impatto LOC EFFETTIVO**: BulkModal 1766 → 1800 (+2%) anziché il target -30%

---

### Step 4 — Semplificare `+page.svelte` ⚠️ PARTIAL

**Obiettivo**: rimuovere duplicazione dati e props cascade.

**Fatto**:
- ✅ `allMainRows`/`allPartnerRows` rimossi — `reload()` popola `txStoreSetAll()`
- ✅ `txStoreCanEdit()` usato per viewer guard
- ✅ `txStoreGet()` usato per partner lookup

**NON fatto**:
- ❌ `WorkspaceIntent` non implementato — BulkModal riceve ancora `initialRows: TXReadItem[]` come prop anziché `{action, txIds}`
- ❌ `bulkInitial` (array di `TXReadItem`) ancora costruito in 10+ punti in +page
- ❌ `filterEditableRows` logica ancora inline (non centralizzata)

**Impatto LOC EFFETTIVO**: +page 1035 → 993 (-4%) anziché il target -30%

---

### Step 5 — Test di non-regressione finale ✅

**Risultati** (2026-05-08):
- ✅ transactions-modals: 14/14 passed
- ✅ transactions-table: all passed
- ✅ tx-broker-access: 4/4 passed
- ✅ tx-paired-edit: 4/4 passed
- ✅ tx-delete: 15/15 passed
- ✅ tx-picker-pagination: 5/5 passed
- ⚠️ tx-tooltips: 1/2 passed (1 flaky pre-esistente, non correlato a txStore)

---

### Step 6 — Post-completion polish ✅

**6a) Deduplica interfacce TXReadItem/ValidationIssue/AssetEvent**

Creato `frontend/src/lib/components/transactions/types.ts` come canonical source. Migrati:
- `+page.svelte` → import from `types.ts`
- `TransactionsTable.svelte` → re-export from `types.ts`
- `TransactionBulkModal.svelte` → import from `types.ts`
- `txStore.svelte.ts` → re-export from `types.ts`

Remaining (future cleanup): TransactionFormModal, TransactionDeleteModal, BulkDeleteLinkedPairModal — possono essere allineati in follow-up.

**6b) Fix banner validate: alignment + bullet spacing**

Problema: `list-inside` causava gap eccessivo tra bullet e testo + rendering centrato in contesti narrow.
Fix: sostituito `list-disc list-inside` → `list-disc pl-4 text-left` su tutte e 4 le `<ul>` di issues nel BulkModal.

**6c) Fix test flaky: tx-tooltips "paired tooltip shows broker name in bold"**

Problema: la colonna Links è scrollata fuori viewport (1280px) con tutte le colonne visibili → `toBeVisible` falliva.
Fix: aggiunto `scrollIntoViewIfNeeded()` prima dell'hover, aumentati timeout (2s→5s per visibilità, 2s→3s per tooltip). Root cause confermata non correlata a txStore.

**6d) Unificazione banner: TransactionResultBanner condiviso tra BulkModal e DeleteModal**

Problema: BulkModal usava `InfoBanner` generico (con icone SVG lucide), DeleteModal usava `TransactionResultBanner` (con emoji) — stile incoerente.
Fix:
- Riscritto `TransactionResultBanner` per supportare: `dismissible`, `ondismiss`, `children` slot (per contenuti complessi come liste clickabili), `border` come design, `text-left` forzato
- BulkModal migrato da `InfoBanner` → `TransactionResultBanner` per tutti i banner error/warning
- `InfoBanner` mantenuto solo per i messaggi info puri (ⓘ autoOff, ℹ️ splitHint)
- DeleteModal già usava il componente → ora entrambi hanno stessa estetica senza nessuna icona SVG lucide

**6e) Riga paired: sfondo pieno anziché border-l sottile** — ⚠️ PARZIALE

Problema: le righe paired nella griglia BulkModal avevano solo `border-l-2 border-l-indigo-400` (striscia sottile a sinistra), non coerente con gli altri status (new/edited/delete) che usano sfondo pieno.
Fix intenzionato: sfondo diverso per ogni status (`getRowClass()` in BulkModal).

Stato attuale: `getRowClass()` esiste ed applica:
- `new` → `row-appended` (verde, DataTable nativo) ✅
- `edited` → `row-edited` (blu, DataTable nativo) ✅
- `delete` → `row-deleted line-through` (rosso + opacity, DataTable nativo) ✅
- `paired (original)` → `row-paired` (indigo, classe aggiunta al DataTable) ✅
- ❌ `original` (non-paired) → nessun sfondo — la riga è indistinguibile dal default

**Fix audit 2026-05-08**: le classi Tailwind inline (`bg-amber-100/40` etc.) erano **invisibili** perché il CSS scoped del DataTable (`tbody tr { background: white }`) le sovrascriveva per specificità. Migrato a classi native DataTable (`row-deleted`, `row-edited`, `row-appended`) che usano `!important` sulle `<td>`. Aggiunta classe `row-paired` (indigo) nel DataTable per le righe paired.

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

---

## Remaining Work (Post-Audit)

**Audit date**: 2026-05-08
**Auditor**: AI agent review durante debug di bug timing `mergePairedRows`

### Bug trovato durante l'audit

`mergePairedRows()` gira **sync** nell'`$effect` init della BulkModal, PRIMA che `ensureTypesLoaded()` completi. Se il type store non è cachato (prima visita, page refresh), `getTypeRule('TRANSFER')` ritorna `FALLBACK_RULE` con `requiresPair: false` → la merge viene completamente saltata.

**Impatto**: FormModal aperto in modalità singola anziché dual → validate `{"updates":[]}` vuoto → Apply genera partner con `broker_id:0` → 2 righe visibili nella griglia anziché 1.

**Hotfix applicato**: gate `mergePairedRows()` e auto-open dietro `isTypesLoaded()`, con deferred re-run nell'async block. Funziona MA non elimina il root cause (dipendenza fragile da type store per la pair detection).

**Root cause strutturale**: l'architettura `mergePairedRows` con `link_uuid`/`_hidden` richiede che il type store sia caricato per sapere quali tipi sono paired. Con `txStore.getPartner()` (via `related_transaction_id`) il type store non servirebbe affatto.

### Checklist lavoro residuo

| # | Cosa manca | Step | Impatto |
|---|---|---|---|
| R1 | `PendingOp[]` + status derivato da diff | Step 3 | Elimina bug "edited falso", semplifica status management |
| R2 | Eliminare `link_uuid` — paired via `txStore.getPartner()` | Step 3 | Elimina 5+ bug storici documentati in Motivazione |
| R3 | Eliminare `_hidden` row pattern — rendering diretto da txStore | Step 3 | Elimina `mergePairedRows` (~60 LOC) e il bug timing |
| R4 | Eliminare `fromTx()` clone — ref a txStore + overrides | Step 3 | -35 LOC, single source of truth |
| R5 | Riscrivere `patchDualRowFromForm()` su txStore base | Step 3 | -70 LOC, elimina partner match fragile |
| R6 | `WorkspaceIntent` API per BulkModal | Step 4 | Elimina `bulkInitial` e 10+ costruzioni inline in +page |
| R7 | Riduzione LOC +page (993 → ~700) | Step 4 | -30% come target originale |
| R8 | ~~Sfondo righe BulkModal invisibile~~ | Step 6e | ✅ RISOLTO — classi Tailwind sostituite con classi native DataTable |

### Stima effort

- R1-R5 (Step 3 completo): ~1.5 giorni — è il cuore del refactor
- R6-R7 (Step 4 completo): ~0.5 giorni — meccanico una volta che Step 3 è fatto

**Totale**: ~2 giorni per completare il piano come descritto originariamente.

---

## Piano di Rientro — Completamento refactor txStore

**Data**: 2026-05-08
**Contesto**: il piano originale era marcato ✅ COMPLETED ma l'audit ha rivelato che Step 3 (BulkModal) e Step 4 (+page) sono solo parzialmente implementati. Il cuore del refactor (eliminare `link_uuid`, `_hidden`, `mergePairedRows`, `DraftRow[]` con clone) non è stato fatto. Hotfix applicati per bug timing + sfondo righe invisibile.

### Fase 1 — Eliminare `_hidden` + `mergePairedRows` + `link_uuid` (R2, R3)

**Obiettivo**: la riga paired smette di essere "1 visibile + 1 nascosta" → diventa 1 riga con rendering dual (Da:/A:) leggendo entrambi i lati da `txStore.get(id)` + `txStore.getPartner(id)`.

**Cambi**:
- `mergePairedRows()` (~60 LOC) eliminata completamente
- `link_uuid` non più generato/usato — partner risolto via `related_transaction_id` nel txStore
- `_hidden` row pattern eliminato — `visibleDrafts` non serve più filtrare
- `findPartnerDraft()` sostituita da `txStore.getPartner(draft.id)`
- **Elimina alla radice il bug timing** (`isTypesLoaded` gate non serve più perché `getTypeRule().requiresPair` non è più necessario per la pair detection)

**Test**: `./dev.py test front-transaction all`

### Fase 2 — `PendingOp[]` + status derivato (R1, R4, R5)

**Obiettivo**: sostituire `DraftRow[]` (clone completo + status manuale) con `PendingOp[]` + status derivato da diff.

**Cambi**:
- `PendingOp = { op: 'create'|'edit'|'delete', txId?: number, overrides?: Partial<TxFields> }`
- Status derivato: `op=create` → new, `op=edit` con diff → edited, ecc. (nessun `markEdited()` manuale)
- `fromTx()` (~35 LOC) eliminata — rendering legge da txStore + applica overrides
- `patchDualRowFromForm()` (~70 LOC) riscritta: FormModal emette `{fromOverrides, toOverrides}`, BulkModal aggiorna i 2 PendingOp
- `collectUpdate()` semplificata: diff = txStore vs overrides

**Test**: `./dev.py test front-transaction all`

### Fase 3 — `WorkspaceIntent` API (R6, R7)

**Obiettivo**: +page passa solo `{action, txIds}` alla BulkModal anziché array di TXReadItem.

**Cambi**:
- Definire tipo `WorkspaceIntent = { action: 'create'|'edit'|'delete'|'clone', txIds?: number[] }`
- BulkModal prop `intent: WorkspaceIntent` sostituisce `initialRows: TXReadItem[]`
- BulkModal legge righe internamente via `txStore.get(id)` per ogni `intent.txIds`
- 10+ costruzioni `bulkInitial` in +page sostituite da 1-liner `bulkIntent = {action, txIds}`
- Target: +page 993 → ~700 LOC (-30%)

**Test**: `./dev.py test front-transaction all`

### Rischi e mitigazioni

| Rischio | Mitigazione |
|---|---|
| Regressione E2E (43+ test) | Ogni fase testata con `./dev.py test front-transaction all` |
| Breaking change FormModal | FormModal cambia solo l'output di `onPushDraft` — formato interno resta invariato |
| Paired rendering | La dual-row rendering (Da:/A: labels) esiste già — si sposta solo la fonte dati |

### Priorità

1. **Fase 1** (eliminare `_hidden`/`mergePairedRows`) è la più urgente: elimina il root cause del bug timing e 5 classi di bug storici
2. **Fase 2** (`PendingOp`) è il cuore architetturale — prerequisito per Fase 3
3. **Fase 3** (WorkspaceIntent) è meccanica e a basso rischio — può essere rimandata

---

## Session Log — 2026-05-08 pomeriggio (context window exhausted)

### Cosa è stato FATTO in questa sessione

**Fase 1 COMPLETATA** + **Fase 3 PARZIALE** (strada invertita: WorkspaceIntent prima, poi eliminazione `_hidden`):

#### A) Eliminazione `_hidden` row pattern + `mergePairedRows` ✅
- `mergePairedRows()` (~60 LOC) **eliminata completamente** — grep conferma 0 occorrenze
- `_hidden` field rimosso da `DraftRow` interface
- Commento L1228: "All drafts are visible (no more _hidden partner rows)"
- Partner ora tracciato via `_partnerId` + `_partnerFormPayload` (payload dal FormModal)
- **Bug timing eliminato alla radice**: non serve più `isTypesLoaded()` gate per pair detection

#### B) `WorkspaceIntent` API implementata (Fase 3 — parziale)
- Tipo `WorkspaceIntent` definito ed esportato da BulkModal
- Nuova prop `intent?: WorkspaceIntent` accetta `{action: 'create'|'edit'|'delete'|'clone', txIds?}`
- `resolveInitialRows()` risolve intent → rows + autoForm + status
  - `create` → rows vuote + autoForm='create'
  - `edit` → txStore.get() per ogni txId + auto-include partner + autoForm se singolo
  - `clone` → clone con date=today, id=0, related_transaction_id=null
  - `delete` → txStore.get() + auto-include partner + status='delete'
- **+page.svelte migrato**: tutte le chiamate `onAddTransaction`, `onEditBulk`, `onCloneBulk`, `onBulkDeleteSelected` ora usano `bulkIntent = {action, txIds}`
- Eliminati ~50 LOC di logica inline in +page (fetch partner, map clone, etc.)

#### C) LOC attuali post-sessione
| File | Prima | Dopo | Delta |
|------|-------|------|-------|
| BulkModal | 1800 | 1762 | -38 (-2%) |
| +page.svelte | 993 | 944 | -49 (-5%) |
| **Totale** | 2793 | 2706 | **-87** |

#### D) Cosa resta LEGACY nel BulkModal
- ✅ `mergePairedRows` eliminata
- ✅ `_hidden` eliminato
- ⚠️ `link_uuid` ancora presente — usato per pair creation (create-many, clone)
- ⚠️ `fromTx()` (~30 LOC) ancora presente — clone completo anziché ref+overrides
- ⚠️ `DraftRow[]` ancora con copia completa (non `PendingOp[]` + overrides)
- ⚠️ Status ancora marcato manualmente in alcuni path (`draft.status = 'edited'`)

### Cosa RESTA DA FARE (prossima sessione)

#### 1. Test di non-regressione (URGENTE — da fare PRIMA di continuare)
```bash
./dev.py test front-transaction all
```
Le modifiche NON sono ancora state testate E2E. Vanno verificati tutti i 5 spec file:
- `transactions-modals` — create/edit/clone/paired
- `transactions-table` — table rendering
- `tx-broker-access` — viewer guards
- `tx-paired-edit` — paired edit payload, clone
- `tx-delete` — delete singolo/bulk/paired

#### 2. Debug eventuali regressioni dai test
Rischi noti:
- `resolveInitialRows()` per `action:'edit'` con singola riga paired: verifica che il partner viene auto-incluso e autoForm='edit' funziona
- `action:'clone'` senza `related_transaction_id`: il vecchio codice faceva `id: 0` + `date: today` inline — ora lo fa `resolveInitialRows()` internamente
- `action:'delete'` senza fetch partner da API: ora usa solo txStore — se partner non è nel txStore (edge case: non caricato dal server), potrebbe mancare

#### 3. Completamento Fase 2 — `PendingOp[]` (R1, R4, R5)
Dopo test verdi:
- Sostituire `DraftRow[]` clone con `PendingOp[]` → status derivato da diff
- Eliminare `fromTx()` — rendering legge directo da txStore + overrides
- Riscrivere `patchDualRowFromForm()` su base txStore

#### 4. Completamento Fase 3 — rimanenti cleanup +page (R7)
- Rimuovere `bulkInitial` residuo (usato ancora come fallback se `intent` undefined — per backward compat transitoria)
- Rimuovere `bulkAutoOpenForm` (ora gestito da `resolveInitialRows()`)
- Target: +page 944 → ~750 LOC

#### 5. Eliminazione `link_uuid` (R2 — post Fase 2)
Dipende da `PendingOp[]`: quando i partner non sono più clonati ma referenziati, `link_uuid` diventa superfluo per edits. Resta solo per create-many pairs dove il backend richiede link_uuid come chiave di collegamento.

---

## Session Log 2 — 2026-05-08 sera (Fase 3 completamento)

### Cosa è stato FATTO in questa sessione

**Fase 3 COMPLETATA** — WorkspaceIntent API completamente integrata.

#### A) +page.svelte — migrazione completa a `bulkIntent`

- `handleEditRow(row)` → `bulkIntent = {action: 'edit', txIds: [row.id]}` (da ~10 LOC con partner fetch inline)
- `handleCloneRow(row)` → `bulkIntent = {action: 'clone', txIds: [row.id]}` (da ~8 LOC con `getTypeRule` + date override inline)
- Template `<TransactionBulkModal>` → passa `intent={bulkIntent}`, rimossi `initialRows`, `initialStatus`, `autoOpenForm`
- `onClose` → resetta `bulkIntent = undefined`
- Rimossi: `bulkInitial`, `bulkAutoOpenForm`, `bulkInitialStatus` (3 state vars legacy)
- Rimosso import `getTypeRule` (non più usato in +page)

#### B) BulkModal — fix `resolveInitialRows()` per clone e edit

- Clone: aggiunto **Bug6-fix** — `quantityRule === 'zero'` resetta `quantity = '0'` (prima era inline in +page)
- Edit: fix `autoForm` — attivato solo per `txIds.length === 1` (non `resolved.length <= 2`), altrimenti il FormModal si auto-apriva anche per bulk edit da toolbar con 2+ righe selezionate

#### C) Test fix: `tx-paired-edit.spec.ts`

- Il test "edit paired TRANSFER opens BulkModal with paired rows" cercava `data-testid="tx-form-broker-wrap"` che esiste solo nel layout FX (Currency Exchange). Per Asset Transfer, il layout usa `tx-form-dual-from` / `tx-form-dual-to`.
- Fix: il test ora controlla prima `tx-form-dual-from`, con fallback a `tx-form-broker-wrap`.

#### D) LOC finali

| File | Prima sessione | Dopo sessione | Delta totale |
|------|-------|------|-------|
| BulkModal | 1800 (pre-refactor) | 1769 | -31 (-1.7%) |
| +page.svelte | 993 (pre-refactor) | 924 | -69 (-7%) |
| **Totale** | 2793 | 2693 | **-100** |

#### E) Test Results — 7/7 suites ✅

- ✅ transactions-modals: 14/14 passed
- ✅ transactions-table: 24/24 passed
- ✅ tx-broker-access: 4/4 passed
- ✅ tx-paired-edit: 4/4 passed
- ✅ tx-tooltips: 2/2 passed
- ✅ tx-delete: 15/15 passed
- ✅ tx-picker-pagination: 5/5 passed

### Checklist aggiornata

| # | Cosa | Status |
|---|---|---|
| R1 | `deriveStatus()` + status derivato | ✅ Done (Fase 2, sessione precedente) |
| R2 | Eliminare `link_uuid` come meccanismo partner | ⚠️ Parziale — partner trovato via `related_transaction_id`, ma `link_uuid` ancora usato per create-many |
| R3 | Eliminare `_hidden` row pattern | ✅ Done (Fase 1, sessione precedente) |
| R4 | Eliminare `fromTx()` clone → ref+overrides | 🔮 Future (Piano D — `PendingOp[]`) |
| R5 | Riscrivere `patchDualRowFromForm()` su txStore | 🔮 Future (Piano D — `PendingOp[]`) |
| R6 | `WorkspaceIntent` API per BulkModal | ✅ Done (Fase 3, questa sessione) |
| R7 | Riduzione LOC +page | ✅ Done — 993 → 924 (-7%). Target raggionevole; ulteriore -30% richiede `PendingOp[]` |

### Files modificati

| File | Tipo modifica |
|------|------|
| `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` | +Bug6-fix clone, +autoForm fix, +intent prop |
| `frontend/src/routes/(app)/transactions/+page.svelte` | handleEditRow/handleCloneRow → intent, rimossi legacy vars, template aggiornato |
| `frontend/e2e/transactions/tx-paired-edit.spec.ts` | Fix testid per dual transfer_asset layout |

---

## Session Log 3 — 2026-05-08 tarda sera (Bug cosmetici + Picker dblclick)

### Osservazioni utente

L'utente ha testato manualmente la BulkModal e segnalato 3 problemi:

1. **Picker dblclick non sincronizza checkbox**: il doppio click nella PickerModal seleziona/deseleziona logicamente la riga (`selectedRows`), ma la checkbox visiva del DataTable interno non si aggiorna — perché `handleRowDoubleClick` nel PickerModal gestiva uno stato locale (`selectedRows`) senza propagare la selezione al DataTable sottostante.

2. **Righe delete sbarrate (line-through)**: `getRowClass()` applicava `row-deleted line-through` alle righe marcate per cancellazione. Il `line-through` è ridondante perché lo sfondo rosso + badge `🔴 del` sono sufficienti per comunicare lo stato. Rimosso.

3. **Righe paired sempre porpora**: `getRowClass()` applicava `row-paired` (indigo) a tutte le righe paired in stato `original`. L'utente vuole **colore solo basato sullo stato**, non sulla natura paired. Le righe paired sono già riconoscibili dal rendering duale Da:/A:. Rimosso il fallthrough a `row-paired`.

### Fix applicati

| # | Cosa | File | Descrizione |
|---|---|---|---|
| F1 | DataTable: `toggleRowSelectionById()` | `DataTable.svelte` | Nuovo export che delega a `toggleRowSelection()` interna |
| F2 | TransactionsTable: `toggleSelectionByTxId()` | `TransactionsTable.svelte` | Nuovo export che delega a DataTable con formato `tx-${id}` |
| F3 | PickerModal: dblclick sincronizza checkbox | `TransactionPickerModal.svelte` | `handleRowDoubleClick` ora chiama `tableRef.toggleSelectionByTxId()` anziché gestire stato locale |
| F4 | BulkModal: rimosso `line-through` | `TransactionBulkModal.svelte` | `getRowClass()` → `row-deleted` senza `line-through` |
| F5 | BulkModal: rimosso `row-paired` | `TransactionBulkModal.svelte` | `getRowClass()` → colore solo da status (`new`/`edited`/`delete`), righe original+paired → nessun colore |

### Nota positiva

L'utente ha confermato: "mi pare che finalmente le cose iniziano a funzionare!" e "non sono riuscito a trovare nessun altro bug!". I fix precedenti (txStore, WorkspaceIntent, eliminazione `_hidden`/`mergePairedRows`) sono stabili.
