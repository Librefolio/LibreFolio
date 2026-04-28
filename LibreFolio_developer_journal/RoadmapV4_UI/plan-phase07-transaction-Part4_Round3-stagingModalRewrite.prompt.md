# Plan — Phase 7 · Part 4 · Round 4 — Staging Modal greenfield rewrite

**Date**: 2026-04-28
**Status**: 🔧 BUGFIX-1 IN PROGRESS — implementazione iniziale completata, in corso di rifinitura UX/correttezza
**Priority**: P0 (UX bloccante per CRUD transazioni)
**Estimated effort**: ~2 days + 1 day di bugfix

**Bugfix sub-plan**: [`plan-phase07-transaction-Part4_Round3_Bugfix1-formModalRedesign.prompt.md`](./plan-phase07-transaction-Part4_Round3_Bugfix1-formModalRedesign.prompt.md) — feedback walkthrough utente (2026-04-28).

---

## 📊 Status snapshot (post-crash recovery 2026-04-28)

| Step | Descrizione | Stato | Note |
|------|-------------|-------|------|
| 1 | Scaffolding & utility (`transactionTypeRules.ts`, `useValidateScheduler.svelte.ts`, `CompactCashCell.svelte`) | ✅ done | File creati, `svelte-check` clean. Funzioni "unused" risolte automaticamente con il wire-up dello Step 5. |
| 2 | `TransactionFormModal.svelte` | ✅ done | Single create/edit/duplicate/view, sectioned form, savewithretry. |
| 3 | `TransactionBulkModal.svelte` | ✅ done | Costruita su `DataTable` con editable cells + column visibility + N>50 auto-validate disable. |
| 4 | `PromotePairWizardModal.svelte` | ✅ done (post-crash fix) | **Crash recovery**: rimossi import inutili (`onMount`, `FormTX`), corretto alias API (`query_transactions_api_v1_transactions_get` ← era `list_…`), spostata default di `fromSource`/`toSource` a `'saved'` con setup nel `$effect` di reset. |
| 5 | Wire-up `+page.svelte` (sostituisci `TransactionStagingModal` e `TransferPromoteModal`) | ✅ done | Stati `formOpen/Mode/Initial`, `bulkOpen/Mode/Initial`, `wizardOpen/SeedFrom/SeedTo/BulkContext`. Aggiunta `onViewRow` a `TransactionsTable.svelte` con icona `Eye`. `Promote pair` sempre visibile in SelectionBar (seed automatico se `canSeedPromote`). File legacy eliminati. `svelte-check`: **0 errori 0 warning**. |
| 6a | i18n EN/IT/FR/ES | ✅ done | 75 chiavi nuove (`transactions.{form,bulk,promote,validate}.*` + `transactions.actions.view` + `common.{next,created,updated}`), aggiunte via script `/tmp/libreFolio_i18n_round4.py`. |
| 6b | E2E specs (`transactions-form.spec.ts`, `-bulk`, `-promote`) | ⏳ pending | Nessun spec legacy presente — sono tutti file nuovi. |
| 6c | Wiki update (F-048 + 2 concept pages) | ⏳ pending | Da delegare al `project-historian` agent al termine del walkthrough utente. |

**Recovery note**: durante Step 4 la connessione è caduta prima della verifica con `svelte-check`. Errori risolti in chat di follow-up.

---

**Parent plan**: [`plan-phase07-transaction-Part4.prompt.md`](./plan-phase07-transaction-Part4.prompt.md) §Step 7 (override)
**Predecessor**: [`plan-phase07-transaction-Part4_Round2-tableRefactorBugfix.prompt.md`](./plan-phase07-transaction-Part4_Round2-tableRefactorBugfix.prompt.md) (Round 1 → 2 → 3 → 3.5 → 4 chiusi sulla pagina principale)

---

## 🎯 Obiettivo

L'attuale [`TransactionStagingModal.svelte`](../../frontend/src/lib/components/transactions/TransactionStagingModal.svelte) è un placeholder hand-rolled con `<table>` nativa e ignora l'ecosistema [`DataTable`](../../frontend/src/lib/components/table/DataTable.svelte) costruito durante Round 1–2. Va **rifatto da zero**, splittando le responsabilità in **tre componenti specializzati** che riusano editable cells, `ColumnVisibilityToggle`, `DataTableColumnFilter`, `Tooltip`, `CurrencySearchSelect`:

1. `TransactionFormModal` — single add / edit / duplicate / view-readonly (form verticale).
2. `TransactionBulkModal` — bulk create-many / edit-many costruito **sopra `DataTable`** con cell editabili (riusa pattern editbuffer e column-visibility per gating campi optional/advanced).
3. `PromotePairWizardModal` — wizard 3-step che sostituisce [`TransferPromoteModal.svelte`](../../frontend/src/lib/components/transactions/TransferPromoteModal.svelte), con pair-picker che cerca in 3 source diverse (in-bulk / saved / create-new).

**Vincoli architetturali confermati** (dalle 5 considerazioni dell'utente):

1. **Riuso prima di tutto**: usare le `EditableTextCell`/`EditableSelectCell`/`EditableNumberCell`/`CustomCell` di [`types.ts`](../../frontend/src/lib/components/table/types.ts) e [`DataTable.svelte`](../../frontend/src/lib/components/table/DataTable.svelte). Solo dove indispensabile creare nuovi componenti **generici** (es. `CompactCashCell`).
2. **Cash unificato**: 1 sola colonna `Cash` = numeric input + [`CurrencySearchSelect`](../../frontend/src/lib/components/ui/select/CurrencySearchSelect.svelte) compact.
3. **Validazione 100% backend** via `POST /transactions/validate`. Nessun cap sul numero di righe; sopra 50 righe l'auto-validate è disattivata, resta solo il bottone manuale `⚡ Validate now`. Su commit fallito (`rolled_back=true`) il banner mostra gli stessi `issues[]` del payload `/validate` e la modale non si chiude.
4. Trigger validate: debounce 1 s + bottone manuale + auto-fire dopo 60 s di inattività. Idle timer **resettato solo su change effettivo**, non su click validate.
5. `id`, `created_at`, `updated_at` mostrati **readonly** (popolati dal backend, non editabili).

**Esplicitamente fuori scope**:
- BRIM mode (Part 5).
- File preview (Part 4b).
- Endpoint backend nuovi.
- Modifiche al motore di rendering della tabella principale.

---

## 🗺 Modal interaction graph

```
                          /transactions  (+page.svelte)
                                    │
        ┌───────────────────────────┼──────────────────────────────┐
        │                           │                              │
        ▼                           ▼                              ▼
   [+ Add]                  row action ✎ / 📋 / 👁          SelectionBar (N≥1)
        │                           │                              │
        │                           │                ┌─────────────┼──────────┬────────────┐
        │                           │                │             │          │            │
        ▼                           ▼                ▼             ▼          ▼            ▼
  TransactionFormModal  TransactionFormModal  TransactionBulk  Bulk  Bulk     Promote
   mode='create'         mode='edit'|             Modal         Clone Delete   Pair
                        'duplicate'|              (create-many  →    →         Wizard
                        'view'                    /edit-many)  Bulk  BulkDelete Modal
        │                           │                │         │  LinkedPairModal │
        │ ┌─────────────────────────┘                │         │                  │
        ▼ ▼                                          │         │                  │
  POST/PATCH /transactions/bulk (1 item, atomico)    │         │                  │
                                                     │         │                  │
                                       ┌─────────────┘         │                  │
                                       ▼                       ▼                  ▼
                          POST/PATCH /transactions/bulk     DELETE       POST /transfers/promote
                              (N items, atomico)         /transactions/    │
                                       │                  bulk?ids=…       │
                                       │                       │           │
                                       │     ┌─────────────────┼───────────┘
                                       │     │                 │
                                       ▼     ▼                 ▼
                                 banner rolled_back? → keep open + show issues[]
                                                  ↑ same payload schema as /validate
```

### Stack-modale relations (modal-on-modal)

```
TransactionBulkModal
   │
   ├─ row chip "pair partner #43" ─────► TransactionFormModal (mode='view'|'edit')
   │                                          ▲ on close → return to bulk
   │
   └─ ⚡ Promote pair (button) ──────────► PromotePairWizardModal
                                              │
                                              ├─ slot source = "In bulk modal"  → list current draftRows
                                              │
                                              ├─ slot source = "Saved tx"       → search in mainRows + GET /tx?only_unlinked
                                              │
                                              └─ slot source = "Create new"     → TransactionFormModal mode='create'
                                                                                    ▲ on save → fills slot with new id
                                                                                      (modale-on-wizard-on-bulk, max depth 3)

TransactionFormModal (mode='edit')
   │
   └─ chip "pair partner #43" ─────────► TransactionFormModal (another instance, mode='view')
                                              ▲ stack depth 2
```

### Auto-validate behavior

```
N rows in bulk:
  N ≤ 50  →  [debounce 1s on change] + [idle 60s auto] + [manual ⚡ Validate]
  N >  50  →  only [manual ⚡ Validate]   (toolbar shows ⓘ "auto-validate disabled — too many rows")

idle timer reset ONLY on real change (not on manual Validate click)
```

---

## 🎨 ASCII art — TransactionFormModal (mode=create, type=BUY)

```
╔══════════════════════════════════════════════════════════════════════════════╗
║ ➕ New transaction                                                     [✕]  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ┌─ Required ─────────────────────────────────────────────────────────────┐   ║
║ │ Type        [🛒 BUY                            ▾]                       │   ║
║ │ Broker      [🟦 Degiro                         ▾]                       │   ║
║ │ Date        [2026-04-28                       📅]                       │   ║
║ │ Asset       🔍 [VWCE — Vanguard FTSE All-World ▾] (auto-EUR)            │   ║
║ │ Quantity    [+10.000              ] (must be > 0 for BUY)               │   ║
║ │ Cash        [-1,050.00 ] [$ 🇪🇺 EUR ▾] (must be < 0 for BUY)           │   ║
║ └─────────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
║ ▸ + Show optional (tags, description)                                        ║
║ ▸ + Show advanced (asset_event_id, cost_basis_override, link_uuid)           ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ✓ valid · last check 2 s ago         [⚡ Validate now]   [Cancel] [Save ▸]   ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### TransactionFormModal (mode=edit, with banner + advanced expanded)

```
╔══════════════════════════════════════════════════════════════════════════════╗
║ ✎ Edit transaction #42  ·  ⚠ 1 issue                                  [✕]  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ⚠ DIVIDEND requires asset_event_id when linked to event #88                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ┌─ Required ─────────────────────────────────────────────────────────────┐   ║
║ │ Type        [💵 DIVIDEND                ] (immutable in edit)            │   ║
║ │ Broker      [🟦 Degiro                  ] (immutable in edit)            │   ║
║ │ Date        [2026-04-15                📅]                              │   ║
║ │ Asset       🔍 [VWCE                    ▾]                              │   ║
║ │ Quantity    [0.000                     ] (must = 0 for DIVIDEND)         │   ║
║ │ Cash        [+12.40    ] [$ 🇺🇸 USD ▾] (must > 0 for DIVIDEND)         │   ║
║ └─────────────────────────────────────────────────────────────────────────┘   ║
║ ▾ Optional                                                                   ║
║   Tags         [div ⓧ] [q1-2026 ⓧ] [+ add]                                  ║
║   Description  [Quarterly distribution                                  ]    ║
║ ▾ Advanced                                                                   ║
║   Asset event  [⚡ Q1 2026 dividend · 2026-04-15 ▾]    [unlink ⓧ]            ║
║   Pair partner — (none)                                                      ║
║                                                                              ║
║ ┌─ Read-only ────────────────────────────────────────────────────────────┐   ║
║ │ ID #42 · Created 2026-04-15 12:30 UTC · Updated 2026-04-20 09:11 UTC   │   ║
║ └─────────────────────────────────────────────────────────────────────────┘   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ⌛ validating…                       [⚡ Validate now]   [Cancel] [Save ▸]   ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

## 🎨 ASCII art — TransactionBulkModal (DataTable editabile)

```
╔════════════════════════════════════════════════════════════════════════════════════════════╗
║ ✎ Bulk edit — 3 of 4 modified · ✓ valid                                            [✕]    ║
╠════════════════════════════════════════════════════════════════════════════════════════════╣
║ [+ Add row]  [Reset all]  [👁 Columns▾]  [⚡ Validate now]  ⏱ checked 8 s ago             ║
╠════════════════════════════════════════════════════════════════════════════════════════════╣
║ │ st │ ID  │ Date       │ Type     │ Asset            │ Qty       │ Cash             │ ⚙ ║
║ │────┼─────┼────────────┼──────────┼──────────────────┼───────────┼──────────────────┼───║
║ │ ●  │ #42 │ 2026-04-15 │ 🛒 BUY   │ 🔍 VWCE        ▾ │ +10.000   │ −1,050.00 [€EUR▾]│ ↺ ║
║ │edit│ #43 │ 2026-04-10 │ 🛒 BUY   │ 🔍 VWCE        ▾ │ +5.000  ✎ │ −525.00   [€EUR▾]│ ↺ ║
║ │edit│ #50 │ 2026-04-08 │ 💵 DIV   │ 🔍 AAPL        ▾ │ 0.000     │ +12.40  ✎ [$USD▾]│ ↺ ║
║ │new │  —  │ 2026-04-28 │ 💰 DEP   │ —              ▾ │ 0.000     │ +2,000.00 [€EUR▾]│ ✕ ║
║                                                                                          ║
║ Hidden columns (eye ▾): broker, tags, description, asset_event_id, cost_basis_override,  ║
║                         link_uuid, created_at, updated_at                                 ║
╠════════════════════════════════════════════════════════════════════════════════════════════╣
║ Type & broker are immutable in edit. Use Promote pair for TRANSFER/FX_CONVERSION.         ║
║                                                                  [Cancel] [Commit 3 ▸]    ║
╚════════════════════════════════════════════════════════════════════════════════════════════╝
```

### TransactionBulkModal — N > 50 (auto-validate off)

```
╔════════════════════════════════════════════════════════════════════════════════════════════╗
║ ➕ New transactions — 87 drafts · last validate: never                              [✕]   ║
╠════════════════════════════════════════════════════════════════════════════════════════════╣
║ [+ Add row]  [Reset all]  [👁 Columns▾]  [⚡ Validate now]                                 ║
║ ⓘ Auto-validate is OFF (87 rows > 50) — press Validate now to check before commit         ║
╠════════════════════════════════════════════════════════════════════════════════════════════╣
║ … (rows omitted) …                                                                          ║
╠════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                  [Cancel] [Commit 87 ▸]    ║
╚════════════════════════════════════════════════════════════════════════════════════════════╝
```

### TransactionBulkModal — commit fallito (rolled_back, banner persistente)

```
╔════════════════════════════════════════════════════════════════════════════════════════════╗
║ ➕ New transactions — 87 drafts · ⛔ rolled back                                    [✕]   ║
╠════════════════════════════════════════════════════════════════════════════════════════════╣
║ ⛔ Commit rolled back — nothing was saved. 3 issues from server (= same as /validate):    ║
║   ▸ Row 12 (#none): DIVIDEND requires asset_id        [scroll to row]                      ║
║   ▸ Row 27 (#none): TRANSFER requires link_uuid       [scroll to row]                      ║
║   ▸ Row 41 (#none): FX_CONVERSION should not have asset_id   [scroll to row]               ║
╠════════════════════════════════════════════════════════════════════════════════════════════╣
║ [+ Add row]  [Reset all]  [👁 Columns▾]  [⚡ Validate now]                                 ║
║ … (rows, with rows 12/27/41 highlighted in red) …                                          ║
╠════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                  [Cancel] [Commit 87 ▸]    ║
╚════════════════════════════════════════════════════════════════════════════════════════════╝
```

## 🎨 ASCII art — PromotePairWizardModal Step 1 (pair-picker)

```
╔══════════════════════════════════════════════════════════════════════════════╗
║ ⚡ Promote pair — Step 1/3 · pick the two sides                       [✕]  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ┌─ FROM (giver, cash out) ──────────────────────────────────────────────┐   ║
║ │ Source: (●) In bulk modal  ( ) Saved transactions  ( ) Create new    │   ║
║ │ ────────────────────────────────────────────────────────────────────  │   ║
║ │ 🔍 [search by amount / date / broker…              ]                 │   ║
║ │   ☑ #58 WITHDRAWAL · Degiro · 2026-04-08 · −€1,000.00                │   ║
║ │   ☐ #71 WITHDRAWAL · IBKR   · 2026-04-12 · −$1,000.00 (USD)          │   ║
║ │   ☐ … 4 more matches                                                 │   ║
║ └───────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
║ ┌─ TO (receiver, cash in) ──────────────────────────────────────────────┐   ║
║ │ Source: ( ) In bulk modal  (●) Saved transactions  ( ) Create new    │   ║
║ │ ────────────────────────────────────────────────────────────────────  │   ║
║ │ 🔍 [≈ €1,000 ± 5%   only_unlinked=true   types=DEPOSIT      ]        │   ║
║ │   ☑ #59 DEPOSIT · IBKR · 2026-04-08 · +€1,000.00                     │   ║
║ │   ☐ #72 DEPOSIT · IBKR · 2026-04-12 · +€921.50                       │   ║
║ │   ☐ … 2 more matches                                                 │   ║
║ │                                                                       │   ║
║ │  ⚠ Brokers you cannot edit are filtered out (BrokerUserAccess)       │   ║
║ └───────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
║   "Create new" picks open inline → reuses TransactionFormModal              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                  [Cancel]  [Next ▸]          ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### PromotePairWizardModal Step 2 (choose new_type)

```
╔══════════════════════════════════════════════════════════════════════════════╗
║ ⚡ Promote pair — Step 2/3 · choose target type                      [✕]   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ Selected pair:                                                              ║
║   FROM #58 WITHDRAWAL · Degiro · −€1,000.00                                 ║
║   TO   #59 DEPOSIT    · IBKR   · +€1,000.00                                 ║
║                                                                              ║
║ Promote to:                                                                  ║
║   (●) 🔄 TRANSFER       — different brokers, same currency        ✓         ║
║   ( ) 💱 FX_CONVERSION  — same broker, different currencies      ✗ greyed   ║
║                            reason: brokers differ ∧ currencies match         ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                  [◂ Back]  [Cancel]  [Next ▸]               ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### PromotePairWizardModal Step 3 (TRANSFER details)

```
╔══════════════════════════════════════════════════════════════════════════════╗
║ ⚡ Promote → 🔄 TRANSFER — Step 3/3                                   [✕]  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ Asset moved      🔍 [VWCE                                    ▾] (required)  ║
║ Quantity              [10.000                                ] (required)   ║
║                                                                              ║
║ ▾ Advanced                                                                   ║
║   Cost basis override [auto                                  ] (optional)   ║
║                                                                              ║
║ ⚠ This will DELETE #58/#59 and CREATE 2 linked TRANSFER rows atomically.   ║
║   On rollback nothing is changed.                                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ✓ valid · last check 4 s ago    [⚡ Validate now]   [◂ Back] [Promote ▸]    ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

## 🎨 ASCII art — CompactCashCell (riusabile, generico)

```
┌──────────────────────────────────────────────┐
│  ┌──────────────────┐  ┌─────────────────┐   │
│  │ −1,050.00      ✎ │  │ $ 🇪🇺 EUR    ▾ │   │   ← CurrencySearchSelect
│  └──────────────────┘  └─────────────────┘   │      compact mode
│  ┊←── numeric input ─→┊┊──── popover ────→┊  │
└──────────────────────────────────────────────┘
   On change → emits `{amount: Decimal, code: string} | null`
   Sign indicator inline:  + / − pill colored by transactionTypeRules
   Empty amount or code → null (cleared)
```

## 🎨 Validate scheduler — flow

```
user types ──▶ debounce 1s ─▶ POST /validate ─▶ set lastValidatedAt
                                       │
                                       ▼
                              update banner + chip
                                       ▲
[⚡ Validate now] click ────────────────┤
                                       │
idle 60 s since last change ───────────┘
   (timer reset only on real change, NOT on manual Validate click)
   (auto-trigger globally disabled when N > 50 rows)
```

---

## 🧱 Steps di implementazione

### Step 1 — Scaffolding & utility condivise

**Files**:
- ❌ delete `frontend/src/lib/components/transactions/TransactionStagingModal.svelte`
- ❌ delete `frontend/src/lib/components/transactions/TransferPromoteModal.svelte` (sostituita dal wizard)
- ✨ new `frontend/src/lib/utils/transactionTypeRules.ts`
- ✨ new `frontend/src/lib/utils/useValidateScheduler.ts`
- ✨ new `frontend/src/lib/components/ui/CompactCashCell.svelte`

**Deliverable**:

- `transactionTypeRules.ts`: mapping puro per **gating UI** (non duplica la business validation, che resta server-side):
  ```ts
  export interface TypeRule {
      assetField:   'required' | 'optional' | 'forbidden';
      cashField:    'required' | 'optional' | 'forbidden';
      quantityRule: 'positive' | 'negative' | 'zero' | 'nonzero';
      cashSign:     'positive' | 'negative' | 'either' | 'none';
      eventLinkable: boolean;     // DIVIDEND/INTEREST/ADJUSTMENT
      requiresPair:  boolean;     // TRANSFER/FX_CONVERSION → use wizard, not bulk
  }
  export const TX_TYPE_RULES: Record<TransactionType, TypeRule> = { /* … */ };
  ```

- `useValidateScheduler.ts`: factory `createValidateScheduler({ enabled, debounceMs:1000, idleMs:60000, validateFn })` → returns `{ trigger(reason: 'change'|'manual'|'idle'), state: $state({ isValidating, lastValidatedAt, issuesCount }), dispose() }`. Idle timer **resettato solo su `trigger('change')`**.

- `CompactCashCell.svelte`: input numerico + `CurrencySearchSelect compact` affiancati. Props `value: { amount: string; code: string } | null`, `onChange`, `signHint?: 'positive'|'negative'|'either'`, `compact?: boolean`, `disabled?`, `data-testid`. Riusabile in qualsiasi tabella editabile (FX, Asset prices).

**Tests**: vitest unit per `transactionTypeRules` (lookup completeness su tutti i `TransactionType.options`); snapshot Playwright minimo per `CompactCashCell` (positive/negative pill).

**Stima**: 1.5 h

---

### Step 2 — `TransactionFormModal.svelte`

**Files**:
- ✨ new `frontend/src/lib/components/transactions/TransactionFormModal.svelte`

**Deliverable**:
- Props: `mode: 'create'|'edit'|'duplicate'|'view'`, `initialRow?: TXReadItem`, `forcedBroker?: number` (per stack-modale dal wizard), `onClose`, `onCommitted?`.
- `ModalBase maxWidth=4xl` + form verticale a 3 sezioni:
  - **Required** (sempre visibile): Type (`<select>` con `TransactionTypeBadge`, immutable in edit), Broker (immutable in edit, riusa [`brokerStore`](../../frontend/src/lib/stores/brokerStore.ts)), Date, Asset (`AssetSelect`, gated by `transactionTypeRules.assetField`), Quantity (`<input type="number">`), Cash (`CompactCashCell`).
  - **Optional** (`<details>` collassabile): tags (chip input), description (textarea).
  - **Advanced** (`<details>`): `asset_event_id` (visibile solo se `rules.eventLinkable && asset_id`), `cost_basis_override` (visibile solo per receiver TRANSFER), `link_uuid` (readonly), pair-partner chip (cliccabile → stack-modale `mode='view'`).
  - **Readonly footer** (in edit/view): `ID #{id} · Created … · Updated …`.
- Validate scheduler attivo (1 row → sempre <50 → debounce + idle abilitati).
- Commit: `POST /transactions/bulk` con 1 elemento (create/duplicate) o `PATCH /transactions/bulk` con 1 elemento (edit). Riusa [[concepts/savewithretry-frontend-pattern]] per error extraction.
- On `rolled_back=true` → banner persistente + `issues[]` (la modale è 1-row quindi niente scroll, basta evidenziare il campo offending).
- `data-testid`: `tx-form-modal`, `tx-form-{type|broker|date|asset|qty|cash|tags|description|event|cost-basis|link-uuid}`, `tx-form-validate-now`, `tx-form-save`, `tx-form-cancel`.

**Stima**: 4 h

---

### Step 3 — `TransactionBulkModal.svelte` (DataTable editabile)

**Files**:
- ✨ new `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

**Deliverable**:
- Props: `mode: 'create-many'|'edit-many'`, `initialRows?: TXReadItem[]`, `onClose`, `onCommitted?`.
- Stato: `drafts: DraftRow[]` con `{ tempId, status: 'new'|'edited'|'original', original?, draft }`. Computa `next` localmente PRIMA di assegnare a `drafts` (cfr. [[problems/svelte5-effect-read-write-loop]]).
- Body = `<DataTable>` con:
  - `data = drafts`, `getRowId = (d) => d.tempId`.
  - `enableSelection=false`, `enableColumnFilters=false`, `enablePagination=false`, `enableColumnVisibility=true`.
  - Columns:
    - `status` (HtmlCell badge `● new / ✎ edited / · original`).
    - `id` (HtmlCell readonly `#42`/`—`, `hiddenByDefault: mode==='create-many'`).
    - `date` (CustomCell con `<input type="date">`).
    - `type` (EditableSelectCell, disabled if `mode==='edit-many'`).
    - `asset` (CustomCell wrapping `AssetSelect`, disabled if `rules.assetField==='forbidden'`).
    - `quantity` (EditableNumberCell con sign hint da `rules.quantityRule`).
    - `cash` (CustomCell wrapping `CompactCashCell`, disabled if `rules.cashField==='forbidden'`).
    - `broker` (EditableSelectCell, `hiddenByDefault:true`, disabled if `mode==='edit-many'`).
    - `tags` (CustomCell wrapping chip-input, `hiddenByDefault:true`).
    - `description` (EditableTextCell, `hiddenByDefault:true`).
    - `asset_event_id` (CustomCell, `hiddenByDefault:true`).
    - `cost_basis_override` (EditableTextCell, `hiddenByDefault:true`).
    - `link_uuid` (HtmlCell readonly, `hiddenByDefault:true`).
    - `created_at` / `updated_at` (HtmlCell readonly, `hiddenByDefault:true`).
- Toolbar custom (sopra DataTable): `[+ Add row]` `[Reset all]` `[👁 Columns ▾]` (riusa [`ColumnVisibilityToggle`](../../frontend/src/lib/components/table/ColumnVisibilityToggle.svelte) puntato al `tableRef`) `[⚡ Validate now]` + chip stato (`✓ valid` / `⌛ validating` / `⚠ N issues` / `ⓘ auto-validate disabled (N>50)` / `⛔ rolled back`).
- `useValidateScheduler({ enabled: () => drafts.length <= 50, … })`. Click manuale `Validate now` SEMPRE attivo.
- Commit `POST/PATCH /transactions/bulk` (multi-broker atomico). Su `rolled_back=true` → banner persistente con `issues[]` clickable; click su issue → `tableRef.navigateToRowId(tempId)` + scroll + pulse rosso. **La modale non si chiude**.
- ⚡ `Promote pair` button mostrato in toolbar (sempre disponibile) → apre `PromotePairWizardModal` come stack-modale, passando i `drafts` correnti come source "In bulk modal".
- `data-testid`: `tx-bulk-modal`, `tx-bulk-row-{tempId}`, `tx-bulk-cell-{col}-{tempId}`, `tx-bulk-add-row`, `tx-bulk-reset-all`, `tx-bulk-validate-now`, `tx-bulk-commit`, `tx-bulk-cancel`.

**Stima**: 6 h (la più grossa — riuso aggressivo del DataTable mitiga il costo)

---

### Step 4 — `PromotePairWizardModal.svelte`

**Files**:
- ✨ new `frontend/src/lib/components/transactions/PromotePairWizardModal.svelte`

**Deliverable**:
- Props: `bulkContext?: { drafts: DraftRow[] }` (passato quando aperto sopra il bulk), `seedFrom?: TXReadItem`, `seedTo?: TXReadItem`, `onClose`, `onCommitted?`.
- **Step 1** = pair picker. Per ogni slot (`from` / `to`) 3 source radio:
  1. **In bulk modal** — visibile solo se `bulkContext` è settato; lista filtra `drafts` con `status==='new'` e `type ∈ {DEPOSIT, WITHDRAWAL}` con `related_transaction_id==null`.
  2. **Saved transactions** — `GET /transactions?only_unlinked=true&types=DEPOSIT,WITHDRAWAL` con eventuale `amount_abs_min/max` derivato dall'altro slot (±5%) — endpoint già esiste.
  3. **Create new** — bottone `[+ Create]` apre `TransactionFormModal mode='create'` come stack-modale (`forcedBroker` pre-selezionato dall'altro slot quando già scelto, ma editabile). Su save (1-row commit), il `new_id` dalla response popola lo slot.
- BrokerUserAccess enforcement: filtra ovunque solo broker accessibili.
- **Step 2** = scelta `new_type`. Le radio vengono greyed-out con motivazione inline (replicate UI delle regole `TRANSFER`/`FX_CONVERSION` già definite in [`TransferPromoteModal.svelte`](../../frontend/src/lib/components/transactions/TransferPromoteModal.svelte)).
- **Step 3** = campi specifici (TRANSFER: `asset_id` + `quantity` + advanced `cost_basis_override`; FX_CONVERSION: nessun campo, solo summary + implied rate).
- Commit `POST /transactions/transfers/promote`. Su `rolled_back=true` → banner persistente.
- `data-testid`: `tx-promote-wizard`, `tx-promote-step{1|2|3}`, `tx-promote-slot-{from|to}-source-{bulk|saved|new}`, `tx-promote-create-new`, `tx-promote-next`, `tx-promote-back`, `tx-promote-commit`.

**Stima**: 4 h

---

### Step 5 — Wire-up `+page.svelte` + cleanup legacy

**Files**:
- 🔧 `frontend/src/routes/(app)/transactions/+page.svelte`

**Deliverable**:
- Sostituire i 3 `stagingMode/Initial/Open` legacy con 3 stati separati: `formModalState`, `bulkModalState`, `wizardState`.
- Header `+ Add` → `TransactionFormModal mode='create'`.
- Row actions: `✎ Edit` → `mode='edit'`, `📋 Duplicate` → `mode='duplicate'`, `👁 View` → `mode='view'`.
- SelectionBar:
  - `✎ Edit bulk` (N≥1) → `TransactionBulkModal mode='edit-many'`.
  - `📋 Clone` (N≥1) → `TransactionBulkModal mode='create-many'` con `id` strippati, `link_uuid` rigenerato per ogni pair (riusa `crypto.randomUUID()`), `date=today`.
  - `🗑 Delete` → `BulkDeleteLinkedPairModal` (esistente, invariata).
  - `⚡ Promote pair` (sempre visibile, non più solo con 2 selezionate) → `PromotePairWizardModal` con `seedFrom/seedTo` derivati dalla selezione se compatibile, altrimenti vuoto.
- Rimuovere `TransferPromoteModal` import (file eliminato in Step 1).
- `onCommitted` di tutte le modali → ri-fetcha mainRows + partnerRows + opportunistic merge.

**Stima**: 2 h

---

### Step 6 — i18n + e2e + wiki

**Files**:
- 🔧 `frontend/src/lib/i18n/{en,it,fr,es}.json`
- ✨ new `frontend/e2e/transactions-form.spec.ts` (sostituisce `transactions-staging.spec.ts`)
- ✨ new `frontend/e2e/transactions-bulk.spec.ts`
- ✨ new `frontend/e2e/transactions-promote.spec.ts` (sostituisce vecchio omonimo)
- 🔧 wiki `LibreFolio_devWiki/wiki/features/F-048.md` (split tre componenti, server-only validation, no row cap, auto-disable >50, modal stacking)
- ✨ new wiki `LibreFolio_devWiki/wiki/concepts/transaction-type-rules.md`
- ✨ new wiki `LibreFolio_devWiki/wiki/concepts/validate-scheduler.md`

**Deliverable**:
- Chiavi i18n nuove: `transactions.{form,bulk,promote,validate}.*` × 4 lingue. Eseguire `./dev.py i18n add` come da skill `devpy-i18n`.
- E2E:
  - `transactions-form.spec.ts`: create / edit / duplicate / view; advanced fields gated per type; rollback banner.
  - `transactions-bulk.spec.ts`: 1 row, N=10 rows, N>50 (verifica `ⓘ auto-validate OFF`), column visibility toggle, rollback banner with click-to-row.
  - `transactions-promote.spec.ts`: pair picker source = in-bulk / saved / create-new; broker access filter; greyed type rule; rollback.
- svelte-check + lint:format-frontend pass clean.
- `data-testid` ovunque (cfr. [[concepts/e2e-data-testid-rule]]).

**Stima**: 3 h

---

## 🧪 Strategia test

| Spec | Cosa copre |
|------|-----------|
| `transactions-form.spec.ts` | create/edit/duplicate/view modes; advanced disclosure; pair-partner chip stack-modal; rollback banner |
| `transactions-bulk.spec.ts` | DataTable rendering w/ editable cells; column visibility (eye toggle); +Add row / Reset all; auto-validate ON (N≤50) / OFF (N>50); rollback banner with click-to-row navigation |
| `transactions-promote.spec.ts` | Wizard 3-step; pair source = in-bulk / saved / create-new (stack-modal); broker access filter; type rule greyed |
| `transactions-list.spec.ts` (esistente) | invariata |
| `transactions-bulk-delete.spec.ts` (esistente) | invariata |

Coverage backend: nessun gap (no endpoint nuovi).

---

## 🚧 Open Questions / decisioni residue

1. **Stack depth limit** — pair-partner chip dentro un Form aperto da Wizard aperto da Bulk → potenziale stack 4. Decisione proposta: **cap a 3** con disable della terza apertura (toast informativo). Da confermare.
2. **Create-new dentro wizard, broker forced** — pre-select del broker dall'altro slot se già scelto, ma editabile. Server-side validation bloccherà combinazioni illegali. ✅ confermato.
3. **CompactCashCell location** — `lib/components/ui/CompactCashCell.svelte` (generico, riusabile in FX e Asset prices) anziché `lib/components/transactions/`. ✅ confermato.
4. **Idle timer source-of-truth** — reset solo su change effettivo, non su manual Validate. ✅ confermato.
5. **Auto-validate threshold** — 50 righe. Sopra: solo manuale. Senza cap totale. ✅ confermato.
6. **`POST /transactions/validate` riuso** — chiamato sempre con UNA sola lista popolata (`creates` per create-many/single, `updates` per edit-many/single). Mixed mode resta disponibile per Part 5.

---

## 🔗 Cross-link

**Parent macro plan**: [`plan-phase07-transaction-Part4.prompt.md`](./plan-phase07-transaction-Part4.prompt.md) — questo Round 4 sostituisce lo Step 7 (TransactionStagingModal) e lo Step 9 (TransferPromoteModal).
**Predecessor**: [`plan-phase07-transaction-Part4_Round2-tableRefactorBugfix.prompt.md`](./plan-phase07-transaction-Part4_Round2-tableRefactorBugfix.prompt.md) (Round 1–3.5 pagina principale chiusi).

**devWiki rilevante**:
- [[features/F-048]] — Staging Modal (da aggiornare a 3 componenti)
- [[concepts/entity-store-pattern]] — `brokerStore` / `assetStore` riuso reattivo
- [[concepts/editbuffer-pattern]] — RowStatus per `drafts: DraftRow[]`
- [[concepts/savewithretry-frontend-pattern]] — error extraction per FormModal
- [[problems/svelte5-effect-read-write-loop]] — pattern `next` poi assegna
- [[decisions/datatable-tooltip-custom-cell]] — niente `title=` HTML
- [[decisions/multi-broker-atomic-tx]] — atomicità bulk endpoints
- [[decisions/tx-link-uuid-semantics]] — pair handling regole
- [[concepts/e2e-data-testid-rule]] — selettori test
- **(NEW)** `concepts/transaction-type-rules` — gating UI per-tipo
- **(NEW)** `concepts/validate-scheduler` — debounce + idle + manual

---

## 📝 Commit strategy

6 commit incrementali:

1. `feat(transactions): add transactionTypeRules + useValidateScheduler + CompactCashCell + remove legacy modals`
2. `feat(transactions): TransactionFormModal (single create/edit/duplicate/view) with sectioned form + savewithretry`
3. `feat(transactions): TransactionBulkModal built on DataTable with editable cells + column visibility gating + N>50 auto-validate disable`
4. `feat(transactions): PromotePairWizardModal 3-step with in-bulk/saved/create-new pair source + stack-modal Form`
5. `feat(transactions): wire form/bulk/wizard to /transactions page, replace legacy staging stack`
6. `feat(transactions): i18n EN/IT/FR/ES + e2e form/bulk/promote specs + wiki update`

---

## ✅ Final-check

**Implementation status (2026-04-28)**:

- [x] Step 1 — utilities + `CompactCashCell` create
- [x] Step 2 — `TransactionFormModal` complete
- [x] Step 3 — `TransactionBulkModal` complete (DataTable-based)
- [x] Step 4 — `PromotePairWizardModal` complete (post-crash fix applicato: alias API, import puliti, init `fromSource`/`toSource`)
- [x] Step 5 — wire-up `+page.svelte` + delete legacy `TransactionStagingModal` + `TransferPromoteModal` + `onViewRow` aggiunta a `TransactionsTable`
- [x] Step 6a — i18n EN/IT/FR/ES (75 chiavi)
- [ ] Step 6b — 3 e2e specs
- [ ] Step 6c — wiki update (F-048 + 2 concept pages — al `project-historian`)

**Architectural checks**:

- ✅ Riusa `DataTable` + editable cells + `ColumnVisibilityToggle` (no più `<table>` hand-rolled).
- ✅ `CompactCashCell` generico in `lib/components/ui/`.
- ✅ Tre componenti specializzati (Form / Bulk / Wizard) con responsabilità chiara.
- ✅ Validation 100% backend; nessun cap di righe; auto-disable a N>50.
- ✅ Manual Validate sempre disponibile + idle 60 s reset solo su change.
- ✅ `id`/`created_at`/`updated_at` readonly.
- ✅ Pair-partner chip cliccabile (stack-modal).
- ✅ Wizard con 3 source per slot incluso "create new" che riusa Form.
- ✅ BrokerUserAccess enforcement nel wizard picker.
- ✅ Rolled-back banner persistente con `issues[]` clickable + scroll-to-row.
- ✅ `data-testid` esplicitamente menzionato.
- ✅ ASCII art per Form (create/edit), Bulk (normale, N>50, rolled-back), Wizard (step 1/2/3), CompactCashCell, validate scheduler.
- ✅ Cross-link a wiki e plan parent.
- ✅ Plan auto-contenuto (leggibile da nuova sessione).

