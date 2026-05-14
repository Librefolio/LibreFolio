# Plan D2 Bugfix 4 — Split Payload, Suggest, PMC Auto-calc, Override, UX

**Date**: 2026-05-14
**Status**: ⏳ IN PROGRESS
**Priority**: P0-P3 (mixed)
**Estimated effort**: ~20h (~4-5 days)

**Parent**: [`plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_3_UXModalPayloadSuggestE2E.prompt.md`](./plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_3_UXModalPayloadSuggestE2E.prompt.md)

---

## 🎯 Obiettivo

Post-walktest bugfix round 4. Core: split payload errato (main table + BulkModal saved), promote-suggest non funzionante (tolerance hardcoded + amount/quantity non inviati + constraint fallisce), link_uuid divergente dopo edit+apply, PMC auto-calc mancante su TRANSFER create, cost_basis_override applicato erroneamente su entrambe le TX nel promote, broker perso in edit paired (regressione), UX polish su slider/banner/modali, docs + tooltip.

---

## 📋 Bugs catalogati

| ID | P | Area | Descrizione |
|----|---|------|-------------|
| B1 | P0 | BE | **PMC auto-calc su TRANSFER create**: quando il ricevente (qty>0) ha `cost_basis_override=null`, il backend deve calcolarlo come media ponderata degli acquisti dell'asset sul broker sorgente. Creare helper `compute_weighted_avg_cost(session, broker_id, asset_id, as_of_date) → Decimal` e chiamarla nel step 5 di `execute_batch` dopo la creazione del TRANSFER ricevente |
| B2 | P0 | BE | **Promote: cost_basis_override solo su ricevente**: riga 1266-1270 di `transaction_service.py` applica `cost_basis_override` su entrambe le TX. Deve andare **solo** sulla TX con qty>0; forzare null sulla TX con qty<0 |
| B3 | P1 | BE | **Promote-suggest: constraint check fallisce** perché `_PromoteCandidate.amount = Decimal("0")` quando `inp.amount is None`. Il `or Decimal("0")` a riga 863 trasforma None in 0, facendo fallire `cash_amount: opposite`. Fix: se `amount` è None, skip il constraint `cash_amount` (non possibile verificarlo, non fallire). Stessa logica per `quantity` |
| B4 | P0 | FE | **Main table split payload**: `confirmSplit()` invia `{id}` → deve inviare `{id_a, id_b}` |
| B5 | P0 | FE | **BulkModal split saved rows**: NON mutare `fields.type`. Aggiungere a `pendingSplits`. Escludere da updates/validate. Colonna status: badge viola "✂️ split". Colonna type: "TRANSFER → ✂️ ADJUSTMENT" con icone. Undo split: rimuove da pendingSplits, elimina riga partner, ripristina partnerId |
| B6 | P0 | FE | **link_uuid diverge dopo edit+apply**: `patchDualRowFromForm` deve sincronizzare lo stesso link_uuid tra main e partner |
| B7 | P1 | FE | **Promote-suggest tolerance_days hardcoded a 7** → usare `maxDeltaDays` |
| B8 | P1 | FE | **Promote-suggest non invia `amount`/`quantity`** nell'input → aggiungere `amount: Number(cash?.amount) \|\| null`, `quantity: Number(qty) \|\| null` |
| B9 | P1 | FE | **Promote-suggest non ri-scatta dopo Apply** → invalidare `lastSuggestKey` in `handleFormPushed` e nelle azioni split/promote/undo |
| B10 | P1 | FE | **FormModal perde broker partner in edit** (regressione) + test E2E non-regressione |
| B11 | P1 | FE | **cost_basis_override non riflesso in FormModal** read/edit: `applyPartnerToDualTo` non copia il campo. Vincolo: solo ricevente (qty>0) ha override, mittente forzato null. In promote frontend: forzare null su lato mittente |
| B12 | P1 | FE | **Delta-days slider** (range 0-14) + icona mobile + toolbar alignment |
| B13 | P2 | FE | **Suggest banner layout**: `<ul>` con bullet, formato "Merge TYPE (icon) and TYPE (icon) → one TargetLabel (icon)" |
| B14 | P2 | FE | **TransactionActionModal split UX**: no bordi amber, tipo centrato, mostrare qty/tags/desc |
| B15 | P2 | FE | **PromoteMergeModal UX**: bottoni globali in fondo, frecce invertite "Accetta Tutti ▶ \| ⟷ \| ◀ Accetta Tutti", textarea auto-grow |
| B16 | P3 | FE | **Toast generico errori commit** + TODO_FUTURI multi-merge |
| B17 | P2 | DOC | **adjustment.en.md** + tooltip info: espandere "Impact on Cost Basis", aggiungere link tooltip nel FormModal |
| B18 | P2 | FE | **Warning UI per ADJUSTMENT qty>0 senza override**: nel FormModal, quando type=ADJUSTMENT e qty>0 e `cost_basis_override` è vuoto, mostrare warning giallo non bloccante: "No cost basis set — lot will be created with zero cost. Set a value if this is not a stock split or gift." |

---

## 🧠 Scoperte tecniche

### PMC auto-calc (cost_basis_override)

Il campo `cost_basis_override` su `Transaction` (modello DB riga 648-657) è un **prezzo di carico congelato** per un TRANSFER ricevente:
- Quando un asset viene trasferito dal broker A al broker B, il backend calcola il PMC (Prezzo Medio di Carico) come media ponderata degli acquisti al broker sorgente
- Questo valore viene salvato in `cost_basis_override` sulla TX ricevente (qty > 0), così il broker di destinazione non deve mai interrogare lo storico del broker sorgente
- Può essere sovrascritto manualmente (Exit Tax, eredità, regole fiscali particolari)
- Se null **e tipo TRANSFER ricevente** → il backend deve auto-calcolarlo al commit
- **Solo la TX ricevente** (quantity > 0) ha `cost_basis_override`. La TX mittente (quantity < 0) DEVE averlo `null`

### Promote-suggest: perché risultati vuoti

Il frontend chiama `POST /transactions/promote-suggest` ma:
1. `tolerance_days` è hardcoded a 7 nel codice (riga 1852) invece di usare il valore UI `maxDeltaDays`
2. Il mapping input NON invia `amount` e `quantity` → il backend riceve `None` → `_PromoteCandidate.amount = Decimal("0")` → constraint `cash_amount: opposite` confronta `0 != -(-500)` → **fail** → array vuoto
3. Dopo Apply dal FormModal, il `$effect` non ri-scatta perché `lastSuggestKey` non viene invalidato

### BulkModal split saved: algoritmo target

**EVENTO: utente clicca Split su riga R (op='edit', txId=74, partnerId=75)**

1. Aggiungere `{id_a: 74, id_b: 75}` a `pendingSplits[]`
2. **NON mutare** `R.fields.type` — resta TRANSFER come da DB
3. Creare un edit op per il partner (txId=75) da `txStoreGet(75)` e aggiungerla a `ops[]` come nuova riga visibile
4. Svuotare i campi paired display su entrambe le righe (`partnerId = undefined`, `partnerBrokerId = undefined`, ecc.)
5. Triggerare reattività: `ops = [...ops]`

**VISUALIZZAZIONE**:
- Colonna status: badge viola "✂️ split" (stessa posizione di new/edit/del)
- Colonna type: preview "TRANSFER → ✂️ ADJUSTMENT" con icona originale → icona target
- Le righe NON sono editabili per il campo type (il backend gestisce il cambio)

**UNDO: utente clicca Undo Split**

1. Rimuovere da `pendingSplits[]` l'entry con id_a=74 o id_b=74
2. Rimuovere da `ops[]` la riga partner (txId=75)
3. Ripristinare su R: `partnerId = 75`, `partnerBrokerId`, `partnerCash`, `partnerDate` (rileggendo da `txStoreGet`)
4. Triggerare reattività

**COMMIT — costruzione payload**:

```
splitTxIds = Set di tutti gli id presenti in pendingSplits (sia id_a che id_b)

for each op in ops:
  status = deriveStatus(op)

  if op.op === 'edit' AND op.txId ∈ splitTxIds:
    → SKIP (non generare né update né delete per questa riga)
    → Il backend riceverà splits[{id_a, id_b}] e farà tutto lui

  else if status === 'new':
    → creates.push(collectCreate(op))
    → se ha partnerPayload → creates.push(buildCreatePayload(partner))

  else if status === 'edited':
    → updates.push(collectUpdate(op))
    → se ha partnerPayload + partnerId → updates.push(diffDualItem(partner))

  else if status === 'delete':
    → deletes.push(op.txId)
    → se ha partnerId → deletes.push(partnerId)

payload finale:
  { creates[], updates[], deletes[], splits: pendingSplits, promotes: pendingPromotes }
```

Stessa logica per validate: le righe con txId in `splitTxIds` vanno escluse.

---

## 📝 Steps

### Fase 1 — Backend

#### Step 1: Helper PMC + auto-calc su TRANSFER (B1)

**File**: `backend/app/services/transaction_service.py`

Creare funzione `compute_weighted_avg_cost(session, broker_id, asset_id, as_of_date) → Decimal | None`:
- Query: tutte le TX dell'asset su quel broker con `date <= as_of_date` e:
  - type = BUY (usa `abs(amount) / quantity` come unit price)
  - type = TRANSFER con qty>0 e `cost_basis_override is not None` (usa `cost_basis_override` come unit price)
- Calcolo: media ponderata `sum(qty * unit_price) / sum(qty)`
- Se nessuna TX trovata o qty totale = 0 → return None

Nel step 5 di `execute_batch` (riga 1170+), dopo `session.add(tx)` e `flush()`:
- Se `tx.type == TRANSFER` e `tx.quantity > 0` e `tx.cost_basis_override is None`:
  - Trovare il partner nel `link_uuid_map` per ottenere il broker sorgente (il partner ha qty<0, il suo `broker_id` è il sorgente)
  - Chiamare `await compute_weighted_avg_cost(session, source_broker_id, tx.asset_id, tx.date)`
  - Se risultato non None → `tx.cost_basis_override = result`

#### Step 2: Promote cost_basis_override solo su ricevente (B2)

**File**: `backend/app/services/transaction_service.py` riga 1266-1270

Per `cost_basis_override` in `resolved_fields`:
- Applicare SOLO sulla TX con `quantity > 0`
- Forzare `cost_basis_override = None` sulla TX con `quantity < 0`

Se il target type è TRANSFER, dopo il type-change:
- Se nessun `cost_basis_override` in `resolved_fields` e il ricevente ha override null → chiamare `compute_weighted_avg_cost` per auto-calcolarlo

#### Step 3: Promote-suggest constraint fix (B3)

**File**: `backend/app/services/transaction_service.py`

- Riga 863: cambiare `amount=inp.amount or Decimal("0")` → `amount=inp.amount` (keep None)
- In `_check_promote_constraints` (riga 805-806): se `tx_a.amount is None` o `tx_b.amount is None`, skip il constraint `cash_amount: opposite` (return True per quel singolo constraint, continuare con gli altri). Stessa logica per `quantity: opposite` (riga 808-809)

### Fase 2 — Backend Tests + DB Populate

#### Step 4: Test backend PMC + populate verify

- Aggiungere test in `test_transactions_api.py` o file dedicato: creare BUY → TRANSFER → verificare che `cost_basis_override` sia auto-calcolato sul ricevente
- Test promote: verificare che dopo promote a TRANSFER, il ricevente abbia `cost_basis_override` calcolato e il mittente abbia null
- Test promote-suggest: verificare che con `amount` e `quantity` passati, il suggest restituisca candidati
- Eseguire `./dev.py db create-clean --test` + `./dev.py db populate --test` per verificare compatibilità con nuove regole
- I TRANSFER nel mock data usano ORM diretto (non `execute_batch`), quindi il PMC auto-calc non viene triggerato — verificare che non si rompa nulla

### Fase 3 — Frontend Bugs

#### Step 5: Split payload main table (B4)

**File**: `frontend/src/routes/(app)/transactions/+page.svelte` riga 637

Cambiare:
```typescript
// PRIMA
{splits: [{id: splitConfirmTx.id}]}
// DOPO
{splits: [{id_a: splitConfirmTx.id, id_b: splitConfirmPartner!.id}]}
```
Aggiungere guard: se `splitConfirmPartner` è null, mostrare toast errore e non procedere.

#### Step 6: BulkModal split saved (B5)

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

Case A di `handleSplitRow` (riga 650+):
- **NON mutare `row.fields.type`** né `partnerOp.fields.type`
- Solo aggiungere a `pendingSplits` e creare edit op per partner
- Svuotare display paired su entrambe

Commit loop + validate loop (riga 1022+ e 864+):
- Creare `splitTxIds = new Set(pendingSplits.flatMap(s => [s.id_a, s.id_b]))`
- Skip ops con `op.op === 'edit' && splitTxIds.has(op.txId)`

Colonna status (riga 1182):
- Aggiungere caso: se `op.op === 'edit' && splitTxIds.has(op.txId)` → badge viola "✂️ split"

Colonna type (riga 1236):
- Se `splitTxIds.has(opTxId(row))` → rendere "TYPE → ✂️ TARGET" con icone di entrambi i tipi, leggendo da `SPLIT_TYPE_MAP`

Azione riga `undo-split`:
- `visible`: `op.op === 'edit' && splitTxIds.has(op.txId)`
- `onClick`: rimuovere da `pendingSplits`, rimuovere partner da `ops`, ripristinare display paired

#### Step 7: link_uuid sincrono (B6)

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

In `patchDualRowFromForm` (riga 1648) e `addDualRowFromForm` (riga 1628):
- Dopo aver applicato items[0] e items[1], forzare lo stesso `link_uuid`:
  ```typescript
  const sharedUuid = items[0].link_uuid ?? items[1].link_uuid ?? generateUUID();
  if (fromOp.op === 'create') (fromOp as any).link_uuid = sharedUuid;
  (merged.partnerPayload as any).link_uuid = sharedUuid;
  ```

#### Step 8: Promote-suggest frontend (B7+B8+B9)

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

- Riga 1852: `tolerance_days: maxDeltaDays` (era hardcoded a 7)
- Riga 1838-1845: aggiungere al mapping inputs:
  ```typescript
  amount: Number(o.fields.cash?.amount ?? 0) || null,
  quantity: Number(o.fields.quantity ?? 0) || null,
  ```
- Invalidare `lastSuggestKey = ''` in:
  - `handleFormPushed` (dopo riga 1621)
  - `handleSplitRow` (fine funzione)
  - Undo split handler
  - Dopo promote execution

#### Step 9: Broker perso in edit paired (B10)

**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`

Investigare `applyPartnerToDualTo` (riga 426+) e `fetchPartner` (riga 388+):
- Il `dualTo.broker_id` viene settato dal partner, ma se il partner fetch fallisce o il layout non è riconosciuto, si perde
- Verificare che per tutti i layout (`transfer_asset`, `transfer_cash`, `fx`) il `dualTo.broker_id` sia sempre popolato dal partner
- Se il pre-populate via `partner_broker_id` (riga 326-328) è corretto, verificare che `fetchPartner` non lo sovrascriva con un valore errato

#### Step 10: cost_basis_override frontend (B11)

**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`

In `applyPartnerToDualTo` layout `transfer_asset` (riga 444-456):
- Dopo lo swap `draft = fromTx(partner)` / `dualTo = ...`, copiare il `cost_basis_override`:
  - Se il draft (sender, qty<0) ha `cost_basis_override` → forzarlo a ''
  - Se il partner (receiver, qty>0) ha `cost_basis_override` → preservarlo nel draft o dualTo a seconda di quale lato è il ricevente

Nel promote frontend (BulkModal `executePromote`):
- Forzare `cost_basis_override = ''` sul lato mittente (qty<0)

#### Step 10b: Warning UI per ADJUSTMENT senza override (B18)

**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`

Quando `draft.type === 'ADJUSTMENT'` e `Number(draft.quantity) > 0` e `draft.cost_basis_override.trim() === ''`:
- Mostrare un `<InfoBanner variant="warning">` non bloccante sotto il campo cost_basis_override:
- Testo: "No cost basis set — lot will be created with zero cost. Set a value if this is not a stock split or gift."
- i18n key: `transactions.costBasisOverride.warningAdjustment`

#### Step 11: Delta-days slider + toolbar (B12)

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` riga 2201-2207

Sostituire `<input type="number" min="0" max="30">` con:
```svelte
<input type="range" min="0" max="14" step="1"
    class="w-20 accent-libre-green"
    bind:value={maxDeltaDays}
    data-testid="promote-suggest-delta-input" />
<span class="text-[11px] font-mono w-5 text-center">{maxDeltaDays}</span>
```
Su mobile: mostrare icona Δ (lucide `GitCompareArrows` o simile).
Toolbar: verificare che `ml-auto` sia sul blocco azioni a destra.

### Fase 4 — Frontend Tests

#### Step 12: Test E2E

- Aggiungere test non-regressione in `tx-commit-all-types.spec.ts`:
  - Creare TRANSFER → riaprire in edit → verificare che broker partner sia popolato (`data-testid="tx-form-broker-to"` non vuoto)
- Ri-lanciare `./dev.py test front-transaction tx-commit-all-types` per 0 regressioni
- Aggiornare selettori/assertioni per le nuove UI (slider, badge split, etc.)

### Fase 5 — UX Polish + Docs

#### Step 13: UX polish (B13+B14+B15+B16)

**Suggest banner** (`TransactionBulkModal.svelte` riga 2141+):
- Wrappare in `<ul class="list-disc list-inside">` con `<li>` per ogni suggestion
- Formato: "Merge TYPE_A (icon) and TYPE_B (icon) → one TargetLabel (icon) (Δ Nd)"

**TransactionActionModal** (`TransactionActionModal.svelte`):
- Rimuovere bordi `border-amber-*`, usare `border-gray-200 dark:border-gray-700`
- Tipo in riga BEFORE: centrare su `colspan="2"` (non mettere 2 colonne From/To per il tipo)
- Aggiungere righe: quantity, tags, description
- Nella tabella AFTER: mostrare gli stessi campi

**PromoteMergeModal** (`PromoteMergeModal.svelte`):
- Spostare bottoni globali (All Left / Merge / All Right) sotto i campi divergenti (sopra il footer)
- Invertire frecce e semplificare testi: "Accetta Tutti ▶" a sinistra, "◀ Accetta Tutti" a destra
- Icona merge al centro: rimuovere testo, solo icona `⟷` più grande (size=24)
- Concat button: allineato al centro
- Textarea: stile `field-sizing: content; max-height: 8rem;` per auto-grow fino a ~5 righe

**Toast generico commit error**:
- Nel `commit()` catch/fallback, se `resp.committed === false` → mostrare toast "Salvataggio impossibile, errore nel server" in aggiunta al banner issues

**TODO_FUTURI.md**: aggiungere nota su multi-merge suggest (mostrare solo primo risultato per coppia, possibilità futura di gestire N-way merge)

#### Step 14: Docs + Tooltip (B17)

**File**: `mkdocs_src/docs/financial-theory/instruments/transaction-types/adjustment.en.md`

Espandere sezione "📐 Impact on Cost Basis":

```markdown
## 📐 Impact on Cost Basis

Adjustments with positive quantity **increase** the lot count (FIFO). The cost basis
for adjustment-created lots depends on whether a `cost_basis_override` is provided:

- **With override**: the specified amount is used as the per-unit acquisition cost
- **Without override**: the lot is created with zero cost (free acquisition — e.g. gifts, airdrops)

### 🏦 Automatic Cost Basis on Transfers

When an asset is transferred between brokers, LibreFolio automatically computes the
**weighted average cost (WAC)** at the source broker and freezes it on the receiving
transaction's `cost_basis_override` field. This "snapshot" architecture ensures:

1. The destination broker never needs to query the source broker's transaction history
2. The cost basis is preserved even if the user later loses access to the source broker
3. Manual override remains possible for special cases

The WAC is computed as:

$$WAC = \frac{\sum_{i} q_i \times p_i}{\sum_{i} q_i}$$

where $q_i$ is the quantity and $p_i$ is the per-unit cost of each acquisition lot
(BUY transactions and incoming TRANSFERs with a frozen cost basis).

### ✏️ When to Override Manually

| Scenario | What to set |
|----------|------------|
| **Normal transfer** | Leave empty — auto-calculated |
| **Exit Tax** | Market value at transfer date (jurisdiction-specific) |
| **Inheritance** | Fair market value at date of death (or stepped-up basis) |
| **Gift** | Donor's original cost basis (carryover basis) |
| **Corporate action** | Adjusted basis per corporate action terms |

!!! warning "User Responsibility"

    When manually overriding the cost basis, the user is responsible for the
    correctness of the value. LibreFolio does not validate override amounts
    against tax rules — consult a tax advisor for jurisdiction-specific guidance.
```

**FormModal tooltip**:

**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`

Accanto al campo `cost_basis_override`, aggiungere icona `Info` (lucide) wrappata in `<Tooltip>`:
- Testo: "Override del PMC. Se vuoto, calcolato come media ponderata degli acquisti al salvataggio. Sovrascrivi per Exit Tax, eredità, o regole fiscali particolari."
- Cliccabile → navigare a `/mkdocs/financial-theory/instruments/transaction-types/adjustment/#-automatic-cost-basis-on-transfers`

#### Step 15: i18n

Chiavi nuove in EN/IT/FR/ES:
- `transactions.promoteSuggest.deltaLabel` (slider label)
- `transactions.costBasisOverride.tooltip` (tooltip text)
- `transactions.bulk.splitQueued` / `transactions.bulk.undoSplit` (badge + azione)
- `transactions.commit.serverError` (toast generico)

---

## ✅ Walktest pianificato — Checklist post-fix

| # | Scenario | Cosa verificare |
|---|----------|----------------|
| W1 | Main table split | Clicca split → modale → conferma → payload `{id_a, id_b}` → success |
| W2 | BulkModal split saved | Seleziona TX paired → split → badge viola + preview tipo → commit → solo splits[] nel payload |
| W3 | BulkModal undo split | Split → undo → riga partner rimossa, display paired ripristinato |
| W4 | Promote-suggest | Apri BulkModal con TX standalone → banner suggest appare con candidati DB |
| W5 | Promote-suggest delta | Cambia slider → suggest filtra/appare correttamente |
| W6 | Edit paired + apply | Edit TRANSFER in FormModal → apply → link_uuid identico su entrambe le righe |
| W7 | Edit paired broker | Edit TRANSFER → broker partner visibile e corretto |
| W8 | cost_basis_override | Crea TRANSFER con override → commit → backend salva solo su ricevente |
| W9 | PMC auto-calc | Crea TRANSFER senza override → commit → backend auto-calcola PMC sul ricevente |
| W10 | Tooltip info | Campo override → icona info → tooltip → click → navigazione a doc |
| W11 | Suggest banner | Banner con lista puntata, formato corretto |
| W12 | Split modal UX | No bordi amber, tipo centrato, qty/tags/desc visibili |
| W13 | PromoteMergeModal UX | Bottoni in fondo, frecce invertite, textarea auto-grow |
| W14 | Toast errore | Provocare errore commit → toast generico visibile |
| W15 | Slider delta | Slider 0-14, valore visibile, persiste in sessionStorage |
| W16 | Warning UI ADJUSTMENT | Edit ADJUSTMENT qty>0 senza override → warning UI giallo non bloccante |
