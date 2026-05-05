# Plan B — DeleteModal + PickerModal + Broker Access Visibility

**Date**: 2026-05-05
**Status**: ⏳ DRAFT v2
**Parent**: [`plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md`](./plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md) (Steps 7 + 9 + Broker Access)
**Estimated effort**: ~9–11h

---

## Obiettivo

Tre macro-aree, **ordinate per dipendenza** (Broker Access → DeleteModal → PickerModal):

1. **Broker Access Visibility** — icone ruolo (Crown/Pencil/Eye/Lock lucide, stesse della pagina Brokers) nei dropdown broker, nelle righe tabella/bulk, nei form. Gestione "partner inaccessibile". Backend enforce dual-broker access su paired mutations. Test data con 4 scenari asimmetrici.
2. **`TransactionDeleteModal`** — riepilogo ricco con dettagli transazione per singola e paired. Toggle "solo questa / entrambe". Tiene conto dell'accesso broker (Layout C per partner inaccessibile).
3. **`TransactionPickerModal`** — cerca e aggiungi TX DB esistenti alla BulkModal. Riusa `mainRows` dal parent (zero fetch aggiuntivo).

---

## Incongruenze trovate nella verifica del codice

### I1 — Icone ruolo: lucide, non emoji
La pagina Brokers usa **componenti lucide** (Crown, Pencil, Eye da `lucide-svelte`) con classi colore (`text-amber-500`, `text-blue-500`, `text-gray-400`). Il piano precedente usava emoji (👑/✏️/👁). **Correzione**: usare gli stessi componenti lucide ovunque. Il `getRoleIcon()` già esiste in `BrokerSharingModal.svelte` (riga 357) — va **estratto** come utility condivisa e riusato.

### I2 — `BrokerBadge.svelte` esiste ma non mostra il ruolo
C'è già un componente centralizzato `BrokerBadge` in `frontend/src/lib/components/ui/BrokerBadge.svelte` (icona + nome). Va esteso con prop opzionale `showRole?: boolean` + `role?: string` per mostrare l'icona ruolo inline. Questo è il punto di intervento centralizzato — **non** duplicare nei vari componenti.

### I3 — Backend rifiuta delete singola di paired (`pairDeleteIncomplete`)
Il backend `commit()` riga 992-1003 emette issue `pairDeleteIncomplete` se si tenta di eliminare una sola metà di una coppia. Questo blocca l'opzione **"Solo questa"** del toggle nel DeleteModal. **Serve modificare il backend**: quando si elimina una sola metà, il partner sopravvissuto deve essere "scollegato" (nullificare `link_uuid` e `related_transaction_id`), non rifiutato. L'issue `pairDeleteIncomplete` va sostituito con una logica di auto-cleanup.

### I4 — `BrokerSearchSelect.BrokerSelectItem` non ha `user_role`
L'interfaccia `BrokerSelectItem` nel dropdown non include `user_role`. Va aggiunto per mostrare l'icona ruolo nelle opzioni. Alternativa: il `BrokerSearchSelect` riceve i broker dal `brokerStore` che ha già `user_role` — basta esporre il campo nell'interfaccia.

### I5 — BulkModal undo delete: GIÀ ESISTE
L'azione `mark-delete` (riga 1089-1104 della BulkModal) fa già toggle: se lo status è `delete`, il label diventa "Restore" e riporta a `edited`. Nessuna modifica necessaria.

### I6 — `getRoleIcon/getRoleIconColor/getRoleShortLabel` duplicati
Queste funzioni sono definite inline in `BrokerSharingModal.svelte`. Vanno estratte in un utility condiviso (es. `frontend/src/lib/utils/brokerRoleHelpers.ts`) per il riuso in BrokerBadge, BrokerSearchSelect, TransactionsTable, BulkModal.

---

## Steps (riordinati per dipendenza)

### FASE 1 — Broker Access Visibility (Steps 1–4)

### Step 1 — Estrarre utility ruolo + estendere `BrokerBadge` (~1h)

**New file**: [`frontend/src/lib/utils/brokerRoleHelpers.ts`](frontend/src/lib/utils/brokerRoleHelpers.ts)
**Modified**: [`frontend/src/lib/components/ui/BrokerBadge.svelte`](frontend/src/lib/components/ui/BrokerBadge.svelte), [`frontend/src/lib/components/brokers/BrokerSharingModal.svelte`](frontend/src/lib/components/brokers/BrokerSharingModal.svelte), [`frontend/src/lib/stores/brokerStore.ts`](frontend/src/lib/stores/brokerStore.ts)

**1a — `brokerRoleHelpers.ts`** (estratto da `BrokerSharingModal`):
```ts
import {Crown, Pencil, Eye, Lock} from 'lucide-svelte';
import type {ComponentType} from 'svelte';

export function getRoleIcon(role: string | null | undefined): ComponentType {
    switch (role) {
        case 'OWNER': return Crown;
        case 'EDITOR': return Pencil;
        case 'VIEWER': return Eye;
        default: return Lock;
    }
}

export function getRoleIconColor(role: string | null | undefined): string {
    switch (role) {
        case 'OWNER': return 'text-amber-500';
        case 'EDITOR': return 'text-blue-500';
        case 'VIEWER': return 'text-gray-400';
        default: return 'text-red-400';
    }
}

export function getRoleShortLabel(role: string | null | undefined, t: (key: string) => string): string {
    switch (role) {
        case 'OWNER': return t('brokers.sharing.roleOwnerShort');
        case 'EDITOR': return t('brokers.sharing.roleEditorShort');
        case 'VIEWER': return t('brokers.sharing.roleViewerShort');
        default: return '—';
    }
}

/** True if user can mutate (edit/delete) transactions on this broker. */
export function canEditWithRole(role: string | null | undefined): boolean {
    return role === 'OWNER' || role === 'EDITOR';
}
```

**1b — `brokerStore` helpers**:
```ts
export function getBrokerRole(brokerId: number): string | null { ... }
export function canEditBroker(brokerId: number): boolean { ... }
export function canEditPaired(brokerIdA: number, brokerIdB: number): boolean { ... }
```

**1c — `BrokerBadge.svelte`**: aggiungere props opzionali:
- `showRole?: boolean = false`
- `role?: string | null`
- Quando `showRole && role`: mostrare `<svelte:component this={getRoleIcon(role)} size={size * 0.7} class={getRoleIconColor(role)} />` dopo il nome.

**1d — `BrokerSharingModal.svelte`**: rimuovere le funzioni locali `getRoleIcon/getRoleIconColor/getRoleShortLabel` e importare da `brokerRoleHelpers.ts`.

---

### Step 2 — Icone ruolo nei dropdown broker e nelle tabelle (~1h)

**Files**: [`BrokerSearchSelect.svelte`](frontend/src/lib/components/ui/select/BrokerSearchSelect.svelte), [`TransactionsTable.svelte`](frontend/src/lib/components/transactions/TransactionsTable.svelte), [`TransactionBulkModal.svelte`](frontend/src/lib/components/transactions/TransactionBulkModal.svelte)

**2a — `BrokerSearchSelect`**:
- Aggiungere `user_role?: string | null` a `BrokerSelectItem`
- Nei snippet `item` e `selectedItem`: aggiungere icona ruolo dopo il nome usando il componente lucide appropriato (da `getRoleIcon`)

**2b — `TransactionsTable` colonna broker**:
- Nella cella HTML della colonna broker, aggiungere icona ruolo (piccola, 11px, dopo il nome, colore per ruolo). Dato che le celle broker usano HTML inline (non componenti Svelte), usare un span con classe CSS per il colore + testo Unicode fallback, oppure un mini SVG inline. **Alternativa più pulita**: convertire la cella broker in un componente custom cell (`type: 'custom'`, `component: BrokerBadge`).

**2c — `TransactionBulkModal` `renderBrokerHtml()`**:
- Aggiungere icona ruolo al broker name. Stessa logica di 2b: HTML inline con indicatore testuale del ruolo (es. `<span class="text-amber-500 text-[10px]" title="Owner">♛</span>`) — dato che le celle bulk usano HTML string e non componenti Svelte, il lucide component non è direttamente utilizzabile. Usare un piccolo SVG inline o un carattere Unicode (♛/✎/◉) con il colore appropriato.

---

### Step 3 — Backend: enforce dual-broker access + soft delete orfano (~1.5h)

**Files**: [`backend/app/services/transaction_service.py`](backend/app/services/transaction_service.py)

**3a — Enforce dual-broker access per paired mutations**:
- Aggiungere helper `_check_paired_access(tx: Transaction, user_id: int) -> Optional[str]`:
  - Se `tx.link_uuid` è null → return None
  - Fetch partner via `link_uuid` (SELECT WHERE link_uuid = ? AND id != tx.id)
  - Se partner non trovato → return None (orfano)
  - `_check_broker_access(partner.broker_id, user_id, min_role=EDITOR)`
  - Se accesso negato → return `"paired_access_denied:{partner.broker_id}"`
- Applicare in `_update_single` e nei futuri `split`/`promote`.

**3b — Soft delete: permettere delete singola di paired con auto-cleanup**:
- Modificare la logica riga 992-1003: **rimuovere** l'issue `pairDeleteIncomplete`
- Al suo posto: se `tx.related_transaction_id` e il partner non è nel batch `deletes`:
  - Fetch il partner
  - Nullificare `partner.link_uuid` e `partner.related_transaction_id` (scollega)
  - Mutare il tipo del partner da paired a standalone (es. CASH_TRANSFER→DEPOSIT, TRANSFER→ADJUSTMENT), usando la stessa mappa di tipo che Split userebbe
  - Il partner sopravvive come transazione standalone
- Se invece il partner è nel batch `deletes`: eliminare entrambi come oggi

**3c — Enforce paired access anche sulla delete**:
- Nella delete: se la riga è paired, verificare che l'utente abbia EDITOR su entrambi i broker **solo se** sta eliminando entrambe le metà. Se elimina "solo questa", basta EDITOR sul proprio broker (il partner viene scollegato, non modificato in modo sostanziale).

**3d — `GET /brokers` ritorna TUTTI i broker con ruolo o null**:
- Modificare `BrokerService.get_all()`: attualmente fa JOIN con `BrokerUserAccess` e ritorna solo i broker accessibili. Cambiare in LEFT JOIN → ritorna tutti i broker, con `user_role = role.value` se l'utente ha accesso, oppure `user_role = null` se non ha alcun accesso.
- Il frontend `brokerStore` riceve così la lista completa — può mostrare il nome del broker nei placeholder "🔒 Broker «Scalable» non accessibile" e nella futura sezione "broker non accessibili" della pagina broker.
- Nessun cambio allo schema `BRReadItem` (il campo `user_role: Optional[str]` già supporta `null`).
- `./dev.py api sync` probabilmente non necessario (schema invariato), ma verificare.

---

### Step 4 — Frontend: partner inaccessibile — UI coerente (~2.5h)

**Files**: [`TransactionsTable.svelte`](frontend/src/lib/components/transactions/TransactionsTable.svelte), [`TransactionFormModal.svelte`](frontend/src/lib/components/transactions/TransactionFormModal.svelte), [`TransactionBulkModal.svelte`](frontend/src/lib/components/transactions/TransactionBulkModal.svelte), [`+page.svelte`](frontend/src/routes/(app)/transactions/+page.svelte)

**4a — Tabella principale** (3 scenari per icona link 🔗):

Caso (a/b) — full access o editor su partner:
```
│ ... │ 🔗 #25 IB ✏️   │ ✎ 📋 🗑 👁 │   ← tutte le azioni visibili
```

Caso (c) — viewer su partner:
```
│ ... │ 🔗 #25 Fineco 👁 │ 👁         │   ← solo view (clone parziale non ha senso)
```

Caso (d) — partner inaccessibile:
```
│ ... │ 🔗 [Tooltip: "Partner su broker «Scalable» — non accessibile"] │ 👁 │
```

**4b — Azioni condizionate all'accesso**:
- Row actions (`edit`, `delete`, `clone`): `visible` gated da `canEditBroker` / `canEditPaired`
  - Standalone: `canEditBroker(row.tx.broker_id)` per edit/delete; clone sempre visibile
  - Paired con full/editor access: edit/delete/clone visibili
  - Paired con viewer su partner: solo `view` (clone parziale non ha senso)
  - Paired con partner inaccessibile: solo `view`
  - `view`: **sempre visibile**
- `+page.svelte` bottone ✏️ view→edit (`onSwitchToEdit`): passare `null` se non `canEditPaired` → la FormModal non mostra il bottone
- ContextMenu: stessi predicati `visible` (già wired dal DataTable)

---

**4c — FormModal: dual paired per livello di accesso**

**Caso (a) — Owner+Owner**: form dual completo, tutto editabile
```
┌──────────────────────────────────────────────────────────┐
│  ✎ ↔ Transfer  #24 ↔ #25                        [✏][X] │
│                                                          │
│  ┌─── From: ──────────────────┐ ┌─── To: ──────────────┐│
│  │ Broker: [Directa 👑 ▾]    │ │ Broker: [IB 👑 ▾]    ││
│  │ Date:   [2025-03-15]      │ │ Date:   [2025-03-15]  ││
│  └────────────────────────────┘ └───────────────────────┘│
│  Asset:    [VWCE.DE ▾]                                   │
│  Quantity: [10]                                          │
│  Tags:     [rebalance] [+]                               │
│                                                          │
│                              [Cancel] [✓ Apply]          │
└──────────────────────────────────────────────────────────┘
```

**Caso (b) — Owner+Editor**: form dual completo, tutto editabile (editor è sufficiente)
```
┌──────────────────────────────────────────────────────────┐
│  ✎ ↔ Transfer  #24 ↔ #25                        [✏][X] │
│                                                          │
│  ┌─── From: ──────────────────┐ ┌─── To: ──────────────┐│
│  │ Broker: [Directa 👑 ▾]    │ │ Broker: [IB ✏️ ▾]    ││
│  │ Date:   [2025-03-15]      │ │ Date:   [2025-03-15]  ││
│  └────────────────────────────┘ └───────────────────────┘│
│  (identico al caso a — editor ha write access)           │
│                              [Cancel] [✓ Apply]          │
└──────────────────────────────────────────────────────────┘
```

**Caso (c) — Owner+Viewer**: form in **view mode forzato**, no bottone ✏️
```
┌──────────────────────────────────────────────────────────┐
│  👁 ↔ Transfer  #24 ↔ #25                           [X] │
│                                                          │
│  ┌─── From: ──────────────────┐ ┌─── To: ──────────────┐│
│  │ Broker: Directa 👑         │ │ Broker: Fineco 👁     ││
│  │ Date:   2025-03-15         │ │ Date:   2025-03-15    ││
│  └────────────────────────────┘ └───────────────────────┘│
│  Asset:    VWCE.DE                                       │
│  Quantity: 10                                            │
│                                                          │
│  ⓘ Edit blocked: viewer access on partner broker.       │
│                                                      [X] │
└──────────────────────────────────────────────────────────┘
```
- Nessun bottone ✏️ nel header (manca `onSwitchToEdit`)
- Tutti i campi in read-only
- Info banner in basso spiega perché non è editabile

**Caso (d) — Owner+Nessun accesso**: form in **view mode**, metà partner nascosta
```
┌──────────────────────────────────────────────────────────┐
│  👁 ↔ Transfer  #24 ↔ ?                             [X] │
│                                                          │
│  ┌─── From: ──────────────────┐ ┌─── To: ──────────────┐│
│  │ Broker: Directa 👑         │ │                       ││
│  │ Date:   2025-03-15         │ │  🔒 Broker            ││
│  │ Qty:    -10                │ │  «Scalable»           ││
│  │                            │ │  non accessibile      ││
│  └────────────────────────────┘ └───────────────────────┘│
│                                                          │
│  ⓘ Partner on broker «Scalable» — not accessible.       │
│                                                      [X] │
└──────────────────────────────────────────────────────────┘
```
- Titolo mostra `#24 ↔ ?` (ID partner sconosciuto)
- Metà "To" mostra solo il placeholder locked
- Nessun bottone ✏️

---

**4d — BulkModal: riga paired per livello di accesso**

Ogni riga della BulkModal con rendering Da:/A: mostra diversamente in base all'accesso:

**Caso (a/b) — Full/Editor access**: riga normal con double-click → edit
```
│ ☐ │ Da:#24 │ [ico]↔Transfer │ Da:2025-03-15 │ -10 📉 │ Da:[ico]Directa 👑 │ ✎ 📋 🗑 │
│   │ A: #25 │    Titoli      │ A: 2025-03-15 │ +10 📈 │ A: [ico]IB ✏️      │         │
```

**Caso (c) — Viewer su partner**: riga readonly, no azioni edit
```
│ ☐ │ Da:#24 │ [ico]↔Transfer │ Da:2025-03-15 │ -10 📉 │ Da:[ico]Directa 👑 │ 👁     │
│   │ A: #25 │    Titoli      │ A: 2025-03-15 │ +10 📈 │ A: [ico]Fineco 👁  │        │
```
- Double-click → apre FormModal in **view mode** (non edit)
- Azioni: solo view (no ✎, no 🗑)

**Caso (d) — Partner inaccessibile**: riga parziale
```
│ ☐ │ #24    │ [ico]↔Transfer │ 2025-03-15    │ -10 📉 │ [ico]Directa 👑            │ 👁     │
│   │        │    Titoli      │               │        │ 🔒 «Scalable» non access.    │        │
```
- Da:/A: non mostrato (non sappiamo i dati del partner)
- Solo riga singola con indicatore 🔒 nella colonna broker
- Double-click → FormModal view mode con placeholder locked (caso d sopra)

---

**4e — Implementazione tecnica**:

Helper per determinare il livello di accesso paired:
```ts
type PairedAccessLevel = 'full' | 'editor' | 'viewer' | 'none';

function getPairedAccessLevel(tx: TXReadItem, partnerRows: TXReadItem[]): PairedAccessLevel {
    if (tx.related_transaction_id == null) return 'full'; // standalone
    const partner = partnerRows.find(p => p.id === tx.related_transaction_id);
    if (!partner) return 'none'; // partner inaccessibile
    const partnerRole = getBrokerRole(partner.broker_id);
    if (canEditWithRole(partnerRole)) return canEditWithRole(getBrokerRole(tx.broker_id)) ? 'full' : 'viewer';
    if (partnerRole === 'VIEWER') return 'viewer';
    return 'none';
}
```

---

### Step 5 — `populate_mock_data.py`: 4 transazioni paired con accesso asimmetrico (~1h)

**File**: [`backend/test_scripts/test_db/populate_mock_data.py`](backend/test_scripts/test_db/populate_mock_data.py)

Creare 4 TRANSFER paired per `e2e_test_user`, tutte visibili ad admin (owner su tutti i broker):

| # | Broker A (from) | Ruolo user su A | Broker B (to) | Ruolo user su B | Scenario |
|---|-----------------|-----------------|---------------|-----------------|----------|
| a | Broker esistente (owner) | **owner** | Broker esistente (owner) | **owner** | ✅ Full access — caso attuale |
| b | Broker esistente (owner) | **owner** | Broker esistente (editor) | **editor** | ✅ Edit consentito |
| c | Broker esistente (owner) | **owner** | Broker esistente (viewer) | **viewer** | ⚠️ View only partner — edit bloccato |
| d | Broker esistente (owner) | **owner** | Broker senza accesso user (es. «Scalable») | **nessuno** | 🔒 Partner invisibile |

Per il caso (d): verificare se esiste già un broker a cui `e2e_test_user` non ha accesso ma `e2e_test_admin` sì. Se non esiste, crearne uno dedicato.

**Nota**: l'assegnazione dei ruoli per broker di `e2e_test_user` è già mista (riga 266-286 del populate): broker `i=0` owner, `i pari` editor, `i dispari` viewer. Riusare questa distribuzione.

**Dopo**: `./dev.py db create-clean`

---

### FASE 2 — DeleteModal (Steps 6–7)

### Step 6 — Creare `TransactionDeleteModal.svelte` (~2h)

**New file**: [`frontend/src/lib/components/transactions/TransactionDeleteModal.svelte`](frontend/src/lib/components/transactions/TransactionDeleteModal.svelte)

**Props**:
```ts
interface Props {
    open: boolean;
    transaction: TXReadItem;
    partner?: TXReadItem | null;
    partnerInaccessible?: boolean;
    onConfirm: (deletePartner: boolean) => void;
    onCancel: () => void;
}
```

**Layout A — Standalone** (no partner, `related_transaction_id == null`):
```
┌──────────────────────────────────────────────────┐
│  🗑️  Delete transaction                      [X] │
│                                                  │
│  ┌──────────────────────────────────────────────┐│
│  │ Type      │ [icon] BUY                       ││
│  │ Date      │ 2025-03-15                       ││
│  │ Asset     │ [icon] VWCE.DE                   ││
│  │ Quantity  │ 10.000                           ││
│  │ Amount    │ 🇪🇺 -1,123.00 EUR                ││
│  │ Broker    │ [icon] Directa [Crown]           ││
│  │ Tags      │ [rebalance] [core]               ││
│  └──────────────────────────────────────────────┘│
│                                                  │
│            [Cancel]  [🗑️ Delete]                 │
└──────────────────────────────────────────────────┘
```

**Layout B — Paired** (partner accessibile, entrambi i broker con EDITOR+):
```
┌────────────────────────────────────────────────────┐
│  🗑️  Delete linked transaction                [X] │
│                                                    │
│  This transaction is part of a linked pair.        │
│                                                    │
│  ┌────────────────────────────────────────────────┐│
│  │           │ From:               │ To:          ││
│  │───────────│─────────────────────│──────────────││
│  │ Date      │ 2025-03-15         │ 2025-03-15   ││
│  │ Asset     │ [ico] VWCE.DE      │ [ico] VWCE.DE││
│  │ Quantity  │ -10 📉             │ +10 📈       ││
│  │ Broker    │ [ico] Directa [👑] │ [ico] IB [✏]││
│  │ Amount    │ —                  │ —             ││
│  └────────────────────────────────────────────────┘│
│                                                    │
│  ┌────── What to delete? ──────────────────────┐   │
│  │                                              │   │
│  │  [ Only this ]  ●━━━━━━━━━━━━●  [  Both  ]  │   │
│  │                                              │   │
│  │  ⚠️ The partner transaction will remain       │   │
│  │     orphaned (converted to standalone).       │   │
│  └──────────────────────────────────────────────┘   │
│                                                    │
│            [Cancel]  [🗑️ Delete]                    │
└────────────────────────────────────────────────────┘
```

**Layout C — Paired con partner inaccessibile** (`related_transaction_id != null` ma partner non nelle `partnerRows`, oppure broker VIEWER-only):
```
┌────────────────────────────────────────────────────┐
│  🗑️  Delete linked transaction                [X] │
│                                                    │
│  This transaction is part of a linked pair.        │
│                                                    │
│  ┌────────────────────────────────────────────────┐│
│  │           │ From:               │ To:          ││
│  │───────────│─────────────────────│──────────────││
│  │ Date      │ 2025-03-15         │              ││
│  │ Asset     │ [ico] VWCE.DE      │  🔒 Broker   ││
│  │ Quantity  │ -10 📉             │  not         ││
│  │ Broker    │ [ico] Directa [👑] │  accessible  ││
│  └────────────────────────────────────────────────┘│
│                                                    │
│  ┌────── What to delete? ──────────────────────┐   │
│  │                                              │   │
│  │  [ Only this ●]  ━━━━━━━━━━━━○  [  Both  ]  │   │
│  │                        ↑ forced / disabled   │   │
│  └──────────────────────────────────────────────┘   │
│                                                    │
│            [Cancel]  [🗑️ Delete]                    │
└────────────────────────────────────────────────────┘
```

**Toggle segmented**: due bottoni styled come segmented control.
- Layout B default: "Both" (scelta più sicura)
- Layout C: **forzato** "Only this" (l'utente non controlla il partner)
- Quando "Only this" selezionato in Layout B: warning ⚠️ orfano appare
- `onConfirm(deletePartner)` → `true` = elimina entrambe, `false` = solo questa

Icone ruolo broker nelle celle riepilogo (via `BrokerBadge` con `showRole`).

---

### Step 7 — Integrare DeleteModal in `+page.svelte` (~45min)

**File**: [`+page.svelte`](frontend/src/routes/(app)/transactions/+page.svelte)

- `handleDeleteRow(row)` → 1 riga → `TransactionDeleteModal` (Layout A/B/C)
- Multi-selezione → `BulkDeleteLinkedPairModal` invariato
- `onConfirm(deletePartner)` → `POST /transactions/commit {deletes}` → `reload({soft:true})`
- Rimuovere `ConfirmModal` "simpleDelete" ridondante
- BulkModal delete: invariato (toggle già esistente, confermato da I5)

---

### FASE 3 — PickerModal (Steps 8–9)

### Step 8 — Creare `TransactionPickerModal.svelte` (~1.5h)

**New file**: [`frontend/src/lib/components/transactions/TransactionPickerModal.svelte`](frontend/src/lib/components/transactions/TransactionPickerModal.svelte)

Props: `open`, `mainRows`, `partnerRows`, `brokers`, `excludeIds`, `onAdd`, `onClose`.

```
┌──────────────────────────────────────────────────────────────┐
│  🔍  Select transactions to add                         [X] │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ ☐ │ ID  │ Type     │ Date       │ Asset    │ Broker     ││
│  │───│─────│──────────│────────────│──────────│────────────││
│  │ ☑ │ #5  │ BUY      │ 2025-01-10 │ VWCE.DE  │ Directa   ││
│  │ ☐ │ #8  │ SELL     │ 2025-02-15 │ AAPL     │ IB        ││
│  │ ☑ │ #12 │ DIVIDEND │ 2025-03-01 │ VWCE.DE  │ Directa   ││
│  │ ☐ │ #15 │ BUY      │ 2025-04-20 │ MSFT     │ Degiro    ││
│  │   │     │          │            │          │            ││
│  │   │ (rows already in bulk are hidden — excludeIds)      ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  ⓘ Selecting a paired TX auto-adds its partner.             │
│                                                              │
│            [Cancel]  [✓ Add 2 selected]                      │
└──────────────────────────────────────────────────────────────┘
```

Riusa `TransactionsTable` con `pickerMode`:
- Row actions nascosti, double-click no-op
- Filtra `excludeIds`
- Selezione paired → auto-aggiunge partner + toast
- Footer: `[Annulla] [✓ Aggiungi N]`

`TransactionsTable` modifiche per `pickerMode`:
- Prop `pickerMode?: boolean`, `excludeIds?: Set<number>`
- Quando `true`: nessun row action, no double-click, filtra excludeIds

---

### Step 9 — Integrare PickerModal nella BulkModal (~45min)

**Files**: [`TransactionBulkModal.svelte`](frontend/src/lib/components/transactions/TransactionBulkModal.svelte), [`+page.svelte`](frontend/src/routes/(app)/transactions/+page.svelte)

- BulkModal: nuove props `allMainRows`, `allPartnerRows`; bottone `[🔍 Cerca e aggiungi]` (solo `mode='edit-many'`); `handlePickerAdd(rows)` con dedup + auto-partner
- `+page.svelte`: passare `allMainRows={mainRows}` e `allPartnerRows={partnerRows}`

---

### Step 10 — i18n + Test (~45min)

Chiavi i18n (4 locali) per delete, picker, accesso.

Verifica manuale post `db create-clean`:
- 4 casi asimmetrici con `e2e_test_user`
- Piano E2E tracciato (non implementato qui)

---

## Further Considerations (verificate)

1. **BulkModal undo delete**: ✅ **GIÀ ESISTE** — l'azione `mark-delete` fa toggle (label "Restore" quando `status === 'delete'`). Nessuna modifica necessaria.

2. **Icone ruolo: lucide, non emoji**: ✅ **CONFERMATO** — `BrokerCard.svelte` riga 91 usa `Crown/Pencil/Eye` lucide con `size={11}`. `BrokerSharingModal` riga 357 il `getRoleIcon()` ritorna componenti lucide. Il piano usa gli stessi. Per le celle HTML inline (BulkModal `renderBrokerHtml`, TransactionsTable HTML cells) dove i componenti Svelte non sono utilizzabili, usare SVG inline o Unicode con classe colore.

3. **Soft delete orfano — backend change significativo** (I3): il backend attualmente **rifiuta** la delete singola di una paired (`pairDeleteIncomplete`). Per supportare "Solo questa" nel DeleteModal, va cambiata la logica: il partner sopravvissuto viene scollegato (nullifica `link_uuid`/`related_transaction_id`) e il tipo mutato (TRANSFER→ADJUSTMENT, etc.) — esattamente come farebbe Split. Questo rende Step 3b un prerequisito bloccante per il DeleteModal toggle.

4. **`mainRows` al PickerModal**: il `+page.svelte` carica TUTTE le transazioni accessibili in `mainRows` (il filtraggio è solo client-side nella DataTable). Quindi passare `mainRows` al PickerModal via BulkModal → zero fetch aggiuntivi, dati già completi.

5. **`broker_role` non in `TXReadItem`**: ✅ confermato — il frontend usa `brokerStore.user_role` (già caricato e cached). Helper `getBrokerRole(brokerId)` nel `brokerStore`.

6. **Nome broker inaccessibile — backend change richiesto**: il `GET /brokers` attualmente ritorna **solo** i broker a cui l'utente ha accesso (JOIN su `BrokerUserAccess`). Questo significa che il frontend non ha il nome dei broker senza accesso. **Fix necessario**: modificare `BrokerService.get_all()` per ritornare TUTTI i broker del sistema, con `user_role` impostato al ruolo effettivo (`OWNER`/`EDITOR`/`VIEWER`) oppure `null` quando l'utente non ha alcun accesso. Il frontend usa già `user_role` in `brokerStore` — basta aggiungere il supporto per `null` come "nessun accesso". Questo abilita: (a) mostrare il nome broker nei placeholder inaccessibili, (b) la futura sezione "broker non accessibili" nella pagina broker. Aggiungere questo al **Step 3** del piano come Step 3d.

7. **Clone paired con viewer/no access**: clone nascosto per paired quando l'utente non ha EDITOR+ su entrambi i broker — un clone parziale (senza la metà partner) non ha senso funzionale.

