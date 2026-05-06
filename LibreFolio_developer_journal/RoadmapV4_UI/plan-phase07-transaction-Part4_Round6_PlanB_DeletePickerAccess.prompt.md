# Plan B — DeleteModal + PickerModal + Broker Access Visibility

**Date**: 2026-05-05
**Status**: ⏳ FASE 1 IMPLEMENTATA — bugfix in corso
**Parent**: [`plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md`](./plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md) (Steps 7 + 9 + Broker Access)
**Estimated effort**: ~9–11h

---

## Obiettivo

Tre macro-aree, **ordinate per dipendenza** (Broker Access → DeleteModal → PickerModal):

1. **Broker Access Visibility** — icone ruolo (Crown/Pencil/Eye/Lock lucide, stesse della pagina Brokers) nei dropdown broker, nelle righe tabella/bulk, nei form. Gestione "partner inaccessibile". Backend enforce dual-broker access su paired mutations. Test data con 4 scenari asimmetrici.
2. **`TransactionDeleteModal`** — riepilogo ricco con dettagli transazione per singola e paired. Paired = sempre delete entrambe (per eliminare solo una metà, prima Split). Tiene conto dell'accesso broker (Layout C per partner inaccessibile/viewer = delete bloccata).
3. **`TransactionPickerModal`** — cerca e aggiungi TX DB esistenti alla BulkModal. Riusa `mainRows` dal parent (zero fetch aggiuntivo).

---

## Incongruenze trovate nella verifica del codice

### I1 — Icone ruolo: lucide, non emoji
La pagina Brokers usa **componenti lucide** (Crown, Pencil, Eye da `lucide-svelte`) con classi colore (`text-amber-500`, `text-blue-500`, `text-gray-400`). Il piano precedente usava emoji (👑/✏️/👁). **Correzione**: usare gli stessi componenti lucide ovunque. Il `getRoleIcon()` già esiste in `BrokerSharingModal.svelte` (riga 357) — va **estratto** come utility condivisa e riusato.

### I2 — `BrokerBadge.svelte` esiste ma non mostra il ruolo
C'è già un componente centralizzato `BrokerBadge` in `frontend/src/lib/components/ui/BrokerBadge.svelte` (icona + nome). Va esteso con prop opzionale `showRole?: boolean` + `role?: string` per mostrare l'icona ruolo inline. Questo è il punto di intervento centralizzato — **non** duplicare nei vari componenti.

### I3 — Backend rifiuta delete singola di paired (`pairDeleteIncomplete`) — CORRETTO
Il backend `commit()` riga 992-1003 emette issue `pairDeleteIncomplete` se si tenta di eliminare una sola metà di una coppia. Questo comportamento è **corretto e va mantenuto**: la delete di una paired elimina sempre entrambe le metà. Se l'utente vuole eliminare solo una metà, deve prima usare **Split** (Piano C) per scollegare la coppia, poi eliminare la transazione standalone risultante. Nessuna modifica backend necessaria per questo aspetto.

### I4 — `BrokerSearchSelect.BrokerSelectItem` non ha `user_role`
L'interfaccia `BrokerSelectItem` nel dropdown non include `user_role`. Va aggiunto per mostrare l'icona ruolo nelle opzioni. Alternativa: il `BrokerSearchSelect` riceve i broker dal `brokerStore` che ha già `user_role` — basta esporre il campo nell'interfaccia.

### I5 — BulkModal undo delete: GIÀ ESISTE
L'azione `mark-delete` (riga 1089-1104 della BulkModal) fa già toggle: se lo status è `delete`, il label diventa "Restore" e riporta a `edited`. Nessuna modifica necessaria.

### I6 — `getRoleIcon/getRoleIconColor/getRoleShortLabel` duplicati
Queste funzioni sono definite inline in `BrokerSharingModal.svelte`. Vanno estratte in un utility condiviso (es. `frontend/src/lib/utils/brokerRoleHelpers.ts`) per il riuso in BrokerBadge, BrokerSearchSelect, TransactionsTable, BulkModal.

---

## Steps (riordinati per dipendenza)

### FASE 1 — Broker Access Visibility (Steps 1–4)

> **Bugfix**: 7 bug + 1 enhancement trovati nel test walk T1-T8. Vedi [`plan-phase07-transaction-Part4_Round6_PlanB_BugfixRound1.prompt.md`](./plan-phase07-transaction-Part4_Round6_PlanB_BugfixRound1.prompt.md)

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
- Convertire la cella broker da HTML inline a **`cellComponent: BrokerBadge`** con `showRole=true`. La DataTable già supporta `cellComponent` per custom rendering. Questo garantisce coerenza con BrokerCard (stessi componenti lucide Crown/Pencil/Eye, stessi colori).

**2c — `TransactionBulkModal` `renderBrokerHtml()`**:
- Stessa logica di 2b: convertire da HTML string a uso di `BrokerBadge` con `showRole=true`. Se il rendering nella BulkModal usa stringhe HTML per le celle custom, valutare se la `DataTable` interna della BulkModal supporta `cellComponent`. Se sì, usare `BrokerBadge`. Se no (celle generate via `innerHTML`), usare gli stessi SVG inline dei componenti lucide (Crown/Pencil/Eye) con le stesse classi colore (`text-amber-500`, `text-blue-500`, `text-gray-400`, `text-red-400`).

---

### Step 3 — Backend: enforce dual-broker access + GET /brokers completo (~1.5h)

**Files**: [`backend/app/services/transaction_service.py`](backend/app/services/transaction_service.py), [`backend/app/services/broker_service.py`](backend/app/services/broker_service.py)

**3a — Enforce dual-broker access per paired mutations**:
- Aggiungere helper `_check_paired_access(tx: Transaction, user_id: int) -> Optional[str]`:
  - Se `tx.link_uuid` è null → return None
  - Fetch partner via `link_uuid` (SELECT WHERE link_uuid = ? AND id != tx.id)
  - Se partner non trovato → return None (orfano)
  - `_check_broker_access(partner.broker_id, user_id, min_role=EDITOR)`
  - Se accesso negato → return `"paired_access_denied:{partner.broker_id}"`
- Applicare in `_update_single`, `_delete_single` e nei futuri `split`/`promote`.
- **Delete paired**: il backend già richiede entrambe le metà nel batch (`pairDeleteIncomplete`). Aggiungere anche il check che l'utente abbia EDITOR su entrambi i broker. Se non ha accesso al partner → issue `paired_access_denied` (il frontend non dovrebbe mai arrivarci perché nasconde il bottone delete, ma serve come guardia).

**3b — `GET /brokers` ritorna TUTTI i broker con ruolo o null**:
- Modificare `BrokerService.get_all()`: attualmente fa JOIN con `BrokerUserAccess` e ritorna solo i broker accessibili. Cambiare in LEFT JOIN → ritorna tutti i broker, con `user_role = role.value` se l'utente ha accesso, oppure `user_role = null` se non ha alcun accesso.
- Il frontend `brokerStore` riceve così la lista completa — può mostrare il nome del broker nei placeholder "🔒 Broker «Scalable» non accessibile" e nella futura sezione "broker non accessibili" della pagina broker.
- Nessun cambio allo schema `BRReadItem` (il campo `user_role: Optional[str]` già supporta `null`).
- `./dev.py api sync` probabilmente non necessario (schema invariato), ma verificare.

**Impatto sui consumer esistenti**:
- **`brokerStore`**: aggiungere helper `getAccessibleBrokers()` (filtra `user_role != null`) e `getEditableBrokers()` (filtra OWNER/EDITOR). I consumer che usano la lista per operazioni (creare transazioni, assegnare broker) devono usare questi filtri.
- **Pagina `/brokers`**: mostra solo `getAccessibleBrokers()` nella sezione principale. I broker con `user_role === null` saranno mostrati in una sezione "Altri broker" separata (deferred al parent plan).
- **`BrokerSearchSelect`** (dropdown form): mostra solo `getEditableBrokers()` — l'utente può creare/modificare transazioni solo su broker dove ha OWNER o EDITOR.
- **Nessun breaking change** per chi oggi itera su `$brokerStore` — il set di broker con ruolo non-null è identico al set attuale.

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
- Row actions (`edit`, `delete`, `clone`): `visible` gated da `getPairedAccessLevel`
  - Standalone: `canEditBroker(row.tx.broker_id)` per edit/delete/clone
  - Paired con `full`: edit/delete/clone visibili
  - Paired con `viewer`: solo `view` (edit/delete/clone nascosti)
  - Paired con `none`: solo `view`
  - `view`: **sempre visibile**
- **Clone**: visibile solo se l'utente può inserire transazioni su TUTTI i broker coinvolti (standalone: 1 broker, paired: 2 broker). Clone parziale (solo una metà) non ha senso.
- `+page.svelte` bottone ✏️ view→edit (`onSwitchToEdit`): passare `null` se non `full` → la FormModal non mostra il bottone
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

Helper per determinare il livello di accesso paired.
Logica: **min(ruolo su broker A, ruolo su broker B)** — il livello della coppia è il minimo tra i due lati.

Gerarchia: `OWNER > EDITOR > VIEWER > null(none)`

```ts
type PairedAccessLevel = 'full' | 'viewer' | 'none';

const ROLE_RANK: Record<string, number> = {OWNER: 3, EDITOR: 2, VIEWER: 1};

function getRoleRank(role: string | null | undefined): number {
    return role ? (ROLE_RANK[role] ?? 0) : 0;
}

function getPairedAccessLevel(tx: TXReadItem, partnerRows: TXReadItem[]): PairedAccessLevel {
    if (tx.related_transaction_id == null) {
        // Standalone: derive from own broker role
        return canEditBroker(tx.broker_id) ? 'full' : 'viewer';
    }
    const partner = partnerRows.find(p => p.id === tx.related_transaction_id);
    if (!partner) return 'none'; // partner inaccessibile (broker senza accesso)
    // Min of the two roles
    const minRank = Math.min(getRoleRank(getBrokerRole(tx.broker_id)),
                              getRoleRank(getBrokerRole(partner.broker_id)));
    if (minRank >= 2) return 'full';   // both EDITOR+
    if (minRank >= 1) return 'viewer'; // at least one is VIEWER
    return 'none';                     // shouldn't happen (would not be visible)
}
```

**Azioni per livello**:
| Level | edit | delete | clone | view | double-click |
|-------|------|--------|-------|------|-------------|
| `full` | ✅ | ✅ | ✅ | ✅ | → edit |
| `viewer` | ❌ | ❌ | ❌ | ✅ | → view |
| `none` | ❌ | ❌ | ❌ | ✅ | → view (locked partner) |

**Standalone**: stessa logica ma con un solo broker. `canEditBroker(tx.broker_id)` → full; else → viewer. Clone sempre visibile per standalone (l'utente può cambiare broker nel form).

---

### Step 5 — `populate_mock_data.py`: 4 transazioni paired con accesso asimmetrico (~1h)

**File**: [`backend/test_scripts/test_db/populate_mock_data.py`](backend/test_scripts/test_db/populate_mock_data.py)

Mapping esplicito dei broker esistenti e ruoli `e2e_test_user`:

| Index | Broker | user role (da logica `i==0` owner, `i%2==0` editor, `i%2!=0` viewer) |
|-------|--------|------|
| 0 | Interactive Brokers | **OWNER** (30%) |
| 1 | DEGIRO | **VIEWER** |
| 2 | Directa SIM | **EDITOR** |
| 3 | eToro | **VIEWER** |
| 4 | Coinbase | **EDITOR** |
| 5 | Recrowd | **VIEWER** |
| — | Hidden Admin Broker | **nessun accesso** (solo admin è OWNER) |

4 TRANSFER paired per `e2e_test_user`:

| # | Broker A (from) | Ruolo user | Broker B (to) | Ruolo user | Scenario |
|---|-----------------|------------|---------------|------------|----------|
| a | Interactive Brokers (i=0) | **OWNER** | Directa SIM (i=2) | **EDITOR** | ✅ Full access (min=EDITOR) |
| b | Interactive Brokers (i=0) | **OWNER** | Coinbase (i=4) | **EDITOR** | ✅ Full access (min=EDITOR) |
| c | Interactive Brokers (i=0) | **OWNER** | DEGIRO (i=1) | **VIEWER** | ⚠️ View only (min=VIEWER) |
| d | Interactive Brokers (i=0) | **OWNER** | Hidden Admin Broker | **nessuno** | 🔒 Partner invisibile |

**Nota caso (a) vs (b)**: entrambi sono "full" ma con broker diversi, utile per verificare che il clone funzioni su entrambi. Se serve un caso OWNER+OWNER esplicito, aggiungere un 5° test: IB (OWNER) ↔ IB (OWNER) come transazione intra-broker (non ha molto senso per TRANSFER, skip).

Per admin: accesso OWNER su tutti → tutti e 4 i casi sono fully editable.

**Dopo**: `./dev.py db create-clean`

---

### FASE 2 — DeleteModal (Steps 6–7)

> ⏸️ **Test walk sospeso** — in attesa di risoluzione dei bug Fase 1 (vedi [BugfixRound1](./plan-phase07-transaction-Part4_Round6_PlanB_BugfixRound1.prompt.md))### Step 6 — Creare `TransactionDeleteModal.svelte` (~2h)

**New file**: [`frontend/src/lib/components/transactions/TransactionDeleteModal.svelte`](frontend/src/lib/components/transactions/TransactionDeleteModal.svelte)

**Props**:
```ts
interface Props {
    open: boolean;
    transaction: TXReadItem;
    partner?: TXReadItem | null;
    partnerInaccessible?: boolean;  // true → Layout C (delete bloccata)
    partnerBrokerName?: string;     // nome broker inaccessibile (da brokerStore)
    onConfirm: () => void;          // sempre "delete entrambe" (per paired) o "delete questa" (standalone)
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
Elimina **sempre entrambe** le metà. Nessun toggle. Se l'utente vuole eliminare solo una metà, deve prima usare Split.
```
┌────────────────────────────────────────────────────┐
│  🗑️  Delete linked transaction                [X] │
│                                                    │
│  Both transactions in this pair will be deleted.   │
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
│  ⓘ To delete only one side, first use Split        │
│    to unlink the pair.                             │
│                                                    │
│            [Cancel]  [🗑️ Delete both]              │
└────────────────────────────────────────────────────┘
```

**Layout C — Paired con partner inaccessibile o viewer** (`related_transaction_id != null` ma accesso insufficiente):
Delete **bloccata** — l'utente non ha accesso EDITOR su entrambi i broker, quindi non può eliminare la coppia. Non può nemmeno fare Split (richiede accesso a entrambi). Mostra solo informazioni.
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
│  │ Quantity  │ -10 📉             │  «Scalable»  ││
│  │ Broker    │ [ico] Directa [👑] │  not access. ││
│  └────────────────────────────────────────────────┘│
│                                                    │
│  ⚠️ Cannot delete: you need Editor access on both  │
│     brokers to delete a linked pair.               │
│     Contact the owner of «Scalable» for access.    │
│                                                    │
│                                          [Close]   │
└────────────────────────────────────────────────────┘
```
- Nessun bottone "Delete" — solo "Close"
- Warning spiega perché è bloccata e suggerisce di contattare l'owner

**Nota**: In pratica il frontend non dovrebbe mai mostrare il Layout C perché il bottone delete è già nascosto (Step 4b). Il Layout C è una guardia aggiuntiva nel caso il DeleteModal venga aperto in modo imprevisto.

---

### Step 7 — Integrare DeleteModal in `+page.svelte` (~45min)

**File**: [`+page.svelte`](frontend/src/routes/(app)/transactions/+page.svelte)

- `handleDeleteRow(row)` → 1 riga → `TransactionDeleteModal` (Layout A/B/C)
- Multi-selezione → `BulkDeleteLinkedPairModal` invariato
- `onConfirm()`:
  - Layout A (standalone): `POST /transactions/commit {deletes: [tx.id]}` → `reload({soft:true})`
  - Layout B (paired): `POST /transactions/commit {deletes: [tx.id, partner.id]}` → `reload({soft:true})`
  - Layout C: non raggiungibile (nessun bottone Delete)
- Rimuovere `ConfirmModal` "simpleDelete" ridondante
- BulkModal delete: invariato (toggle già esistente, confermato da I5)

---

### FASE 3 — PickerModal (Steps 8–9)

> ⏸️ **Test walk sospeso** — in attesa di risoluzione dei bug Fase 1 (vedi [BugfixRound1](./plan-phase07-transaction-Part4_Round6_PlanB_BugfixRound1.prompt.md))

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

2. **Icone ruolo: componenti Svelte, non HTML inline**: ✅ **DECISIONE** — usare `BrokerBadge` con `showRole=true` ovunque possibile (TransactionsTable, DeleteModal). Dove il rendering è HTML string (BulkModal `renderBrokerHtml`), usare gli stessi SVG inline dei componenti lucide con le stesse classi colore. Coerenza garantita con BrokerCard.

3. **Delete paired = sempre entrambe** (I3 risolta): il backend `pairDeleteIncomplete` resta invariato — è il comportamento corretto. La delete di una coppia elimina sempre entrambe le metà. Per eliminare solo una metà → prima Split (Piano C), poi delete della standalone risultante. Il DeleteModal Layout B non ha toggle: mostra solo riepilogo + conferma "Delete both". Layout C (accesso insufficiente) mostra solo info + "Close" senza bottone Delete.

4. **`mainRows` al PickerModal**: il `+page.svelte` carica TUTTE le transazioni accessibili in `mainRows` (il filtraggio è solo client-side nella DataTable). Quindi passare `mainRows` al PickerModal via BulkModal → zero fetch aggiuntivi, dati già completi.

5. **`broker_role` non in `TXReadItem`**: ✅ confermato — il frontend usa `brokerStore.user_role` (già caricato e cached). Helper `getBrokerRole(brokerId)` nel `brokerStore`.

6. **Nome broker inaccessibile — backend change richiesto**: il `GET /brokers` attualmente ritorna **solo** i broker a cui l'utente ha accesso (JOIN su `BrokerUserAccess`). Questo significa che il frontend non ha il nome dei broker senza accesso. **Fix necessario**: modificare `BrokerService.get_all()` per ritornare TUTTI i broker del sistema, con `user_role` impostato al ruolo effettivo (`OWNER`/`EDITOR`/`VIEWER`) oppure `null` quando l'utente non ha alcun accesso. Il frontend usa già `user_role` in `brokerStore` — basta aggiungere il supporto per `null` come "nessun accesso". Questo abilita: (a) mostrare il nome broker nei placeholder inaccessibili, (b) la futura sezione "broker non accessibili" nella pagina broker. Aggiungere questo al **Step 3** del piano come Step 3d.

7. **Clone paired con viewer/no access**: ✅ **DECISIONE** — clone nascosto per paired quando l'utente non ha EDITOR+ su **entrambi** i broker. Un clone parziale (senza la metà partner) non ha senso. Per standalone, clone visibile solo se `canEditBroker(tx.broker_id)`.

8. **`GET /brokers` impatto sui consumer**: ✅ **DECISIONE** — `brokerStore` espone `getAccessibleBrokers()` e `getEditableBrokers()`. Pagina `/brokers` usa `getAccessibleBrokers()` (broker con `user_role === null` nella futura sezione "Altri broker", deferred). `BrokerSearchSelect` usa `getEditableBrokers()`. Nessun breaking change per i consumer attuali.

9. **`getPairedAccessLevel` — logica min()**: ✅ **DECISIONE** — il livello di accesso di una coppia è il **minimo** tra i ruoli sui due broker. `min(OWNER, EDITOR) = full`, `min(OWNER, VIEWER) = viewer`, `min(OWNER, null) = none`. Semplifica i predicati `visible` nelle row actions a un singolo check: `level === 'full'` per edit/delete/clone.

