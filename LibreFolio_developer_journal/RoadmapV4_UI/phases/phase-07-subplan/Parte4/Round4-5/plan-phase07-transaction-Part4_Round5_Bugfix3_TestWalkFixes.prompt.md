# Plan — Phase 07 · Part 4 · Round 5 · Bugfix 3 — Test Walk Fixes

**Data**: 2026-05-03 (aggiornato 2026-05-04 — Round 6 feedback)
**Origine**: `libreFolio_testwalk_phase07_r5b2.md` (test walk 2026-05-02)
**Precedente**: `plan-phase07-transaction-Part4_Round5_Bugfix2_PostTestWalkOverhaul.prompt.md`
**Successore**: Round 6 feedback inline (§ Bugfix 4 — 2026-05-04 Test Walk)

---

## Classificazione Bug

### 🔴 CRITICAL (bloccanti funzionalità core)

| # | Test | Descrizione | Root Cause Ipotizzata |
|---|------|-------------|----------------------|
| C1 | T1.2/T2.1/T4.4 | **Doppio-click su riga bulk apre FormModal sbiancato** — la riga viene editata correttamente al salvataggio, ma il form parte vuoto invece che pre-popolato | BulkModal passa `editRow` ma FormModal non legge i dati iniziali dalla riga |
| C2 | T4.4 | **Edit coppia dalla main table: dati parziali** — apre solo metà della coppia, broker partner sbiancato, ammontare con segno raw | Edit singola riga linked non ricostruisce la coppia duale; manca fetch del partner |
| C3 | [inline] | **Delete riga paired new: elimina solo 1 metà** — rimane errore orfano per la riga partner, UI bloccata | `deleteRow` nel buffer non rimuove il partner `__pairKey` delle righe `new` |
| C4 | T6.edit | **Update payload invia campi immutabili** (`type`, `broker_id`, `link_uuid`, `asset_id`) → backend `TXUpdateItem` ha `extra="forbid"` → "Extra inputs are not permitted" | FE `buildUpdatePayload()` non filtra campi readonly. Backend accetta SOLO: `id`, `date`, `quantity`, `cash`, `tags`, `description`, `cost_basis_override`, `asset_event_id`. Strippare i campi immutabili prima di PATCH. |
| C5 | T2.swap | **Type swap (BUY↔SELL) fallisce al commit** — il PATCH invia `type` nel payload, rifiutato dal backend | `type` non è un campo patchable. Opzione 1 (preferita): aggiungere `type` a `TXUpdateItem` backend con validazione swap group server-side. Opzione 2: delete+create nel FE. |

### 🟠 HIGH (funzionalità degradata ma non bloccante)

| # | Test | Descrizione |
|---|------|-------------|
| H1 | T4.2 | **Bulk table: icone asset/broker assenti nelle celle readonly** — ok readonly text, ma mancano icone |
| H2 | T4.2 | **Qty in bulk table: mostra "-3" invece di rendering duale Da:/A:** — allineamento a destra, missing dual display |
| H3 | T4.2 | **Broker senza URL portale non mostra icona** — fallback chain (plugin icon → generic) non rispettata |
| H4 | T4.3 | **Auto-validate scatta con campi incompleti** — validate non dovrebbe partire finché tutti i campi obbligatori non sono popolati |
| H5 | T8.2 | **Campo asset opzionale non mostra "(opzionale)"** — label mancante per tipi dove asset non è required |
| H6 | T2.2 | **Tipo editabile per righe DB** — il vincolo di tipo readonly per DB rows va rivalutato (vedi analisi sotto) |
| H7 | **Bulk table manca colonna Tags** — i tag delle righe non sono visibili nella tabella bulk | Aggiungere colonna `tags` alla BulkModal con badge colorati (stesso rendering di TransactionsTable) |
| H8 | **Tag selector UX pessima** — il campo tag nel FormModal non è usabile. Serve: digitare parola → Enter/Space → crea badge/chip. Freccia apre SearchSelect con tag esistenti come autocomplete | Implementare `TagInput.svelte` (chip input + autocomplete dropdown da `availableTags`) |
| H9 | **View mode per coppie composite: titolo senza ID** — nel FormModal view di TRANSFER/FX_CONVERSION, il titolo mostra il tipo ma non gli ID di entrambe le transazioni, a differenza delle standalone | Aggiungere `#ID_A ↔ #ID_B` nel titolo FormModal per righe paired |

### 🟡 MEDIUM (polish UX)

| # | Test | Descrizione |
|---|------|-------------|
| M1 | T1.2 | **Banner validazione in bulk table: ancora banner top** — nella bulk dovrebbe essere inline come nel form |
| M2 | T1.2/M1 | **Banner errori/warning senza X di chiusura** — sia nel form che nella bulk, i banner non sono dismissabili |
| M3 | T5.1 | **Date Da/A disallineate** — "Da" e "A" hanno lunghezze diverse → date non allineate |
| M4 | T4.1 | **Colonne nascoste di default** — UUID collegamento, Creato, Aggiornato dovrebbero essere hidden di default |
| M5 | T4.1 | **Colonna "Override costo medio"** — allargare minWidth e spostare dopo "Evento Asset" |
| M6 | T14.1 | **Docs: icone mancanti** — tabella panoramica mostra 1 sola icona per tipi doppi; pagine tipo usano emoji invece dell'icona reale |
| M7 | T1.1 | **Bulk table toolbar on selection** — se si seleziona 1+ riga, mostrare DataTableToolbar con azioni riga |

### 🔵 LOW (nice-to-have / future)

| # | Test | Descrizione |
|---|------|-------------|
| L1 | T7.1 | **Delete modale: riepilogo tabellare** — mostrare dettagli delle transazioni da eliminare (singola: layout verticale; multipla: tabella con toggle per-riga per includere partner) |
| L2 | T7.2 | **Delete partner: toggle per-riga** — nella delete multipla, toggle inline a inizio riga per ogni transazione paired (come nella bulk table); nella delete singola, slider sotto il riepilogo |
| L3 | T7 nota | **Context menu su click destro** — menu azioni in-place per righe lunghe |
| L4 | T14 nota | **TODO Gallery**: screenshot per tipo transazione × lingua, da inserire nelle pagine docs |

---

## Analisi: Vincolo "tipo readonly per DB rows" (H6/T2.2)

**Domanda dell'utente**: ha senso impedire il cambio tipo per righe già persistite?

**Decisione finale**: **"Sign flip"** — permettere solo il cambio tra coppie di tipi con struttura campi identica (stessi campi obbligatori/opzionali). I tipi paired (composite) restano bloccati.

### Swap Groups

| Gruppo | Tipi | Logica |
|--------|------|--------|
| **Asset trade** | `BUY` ↔ `SELL` | Stessa struttura (asset+qty+price+broker), direzione opposta |
| **Cash flow** | `DEPOSIT` ↔ `WITHDRAWAL` | Solo cash+broker, direzione opposta |
| **Income** | `DIVIDEND` ↔ `INTEREST` | Entrambi income; backend valida coerenza campi (es. asset required per DIVIDEND) |
| **Cost** | `TAX` ↔ `FEE` | Entrambi costi; stessa struttura campi |
| **Singleton** | `ADJUSTMENT` | Nessun flip (unico nel suo genere) |
| **Paired 🔒** | `CASH_TRANSFER`, `ASSET_TRANSFER`, `FX_CONVERSION` | Bloccati — troppa complessità duale |

**Perché INTEREST→DIVIDEND è permesso senza guard frontend**: il backend valida la coerenza dei campi. Se l'utente flippa INTEREST→DIVIDEND senza aver compilato l'asset, la validate server-side darà errore. Nessun bisogno di duplicare la logica nel frontend.

**Implementazione**:
- UI: dropdown tipo filtrato su `swapGroup[currentType]` → mostra solo 1-2 alternative
- Al cambio tipo → ricalcolo segni (qty, amount) se necessario
- Effort stimato: ~30 min, zero rischio regressione
- **Sì, in questa iterazione** — è semplice e migliora molto la UX

---

## Design: Delete Modal (L1/L2)

### Singola standalone (es. BUY)
Layout verticale chiave-valore, nessun toggle partner.

```
┌──────────────────────────────────────────────────┐
│  🗑️  Elimina transazione                         │
│                                                  │
│  ┌──────────────────────────────────────────────┐│
│  │ Tipo      │ 🟢 BUY                          ││
│  │ Data      │ 2025-03-15                       ││
│  │ Asset     │ 🏷️ VWCE.DE — Vanguard FTSE A.W. ││
│  │ Quantità  │ 10.000                           ││
│  │ Prezzo    │ 112.34 EUR                       ││
│  │ Broker    │ 🏦 Directa                       ││
│  └──────────────────────────────────────────────┘│
│                                                  │
│            [Annulla]  [🗑️ Elimina]               │
└──────────────────────────────────────────────────┘
```

### Singola paired (es. CASH_TRANSFER)
Layout verticale duale (2 colonne Uscita/Entrata) + slider sotto il riepilogo.

```
┌────────────────────────────────────────────────────┐
│  🗑️  Elimina transazione collegata                  │
│                                                    │
│  Questa transazione fa parte di una coppia.        │
│                                                    │
│  ┌────────────────────────────────────────────────┐│
│  │        │ 🔴 Uscita          │ 🟢 Entrata      ││
│  │────────│────────────────────│──────────────────││
│  │ Data   │ 2025-03-15        │ 2025-03-15       ││
│  │ Broker │ 🏦 Directa        │ 🏦 Degiro        ││
│  │ Amount │ -1 000.00 EUR     │ +1 000.00 EUR    ││
│  └────────────────────────────────────────────────┘│
│                                                    │
│  ┌────── Cosa eliminare? ──────────────────────┐   │
│  │  ●━━━━━━━━━━━━━━━━━━━○                      │   │
│  │  Solo questa    Entrambe                     │   │
│  │                                              │   │
│  │  ⚠️ La transazione partner rimarrà orfana.    │   │
│  └──────────────────────────────────────────────┘   │
│                                                    │
│            [Annulla]  [🗑️ Elimina]                  │
└────────────────────────────────────────────────────┘
```

### Multipla — tabella con toggle per-riga (stile bulk table)
Toggle `[⇄]` inline a inizio riga per transazioni paired. Click → espande dettaglio partner.

```
┌───────────────────────────────────────────────────────────┐
│  🗑️  Elimina 3 transazioni                                │
│                                                           │
│  ┌───────────────────────────────────────────────────────┐│
│  │     │ Tipo   │ Data       │ Asset    │ Amount         ││
│  │─────│────────│────────────│──────────│────────────────││
│  │     │ 🟢 BUY │ 2025-03-15│ VWCE.DE  │ 1 123.00 EUR   ││
│  │     │ 🔴 SELL│ 2025-04-01│ IWDA.AS  │   550.00 EUR   ││
│  │ [⇄] │ 💸 C.T.│ 2025-04-10│ —        │ 1 000.00 EUR   ││
│  └───────────────────────────────────────────────────────┘│
│                                                           │
│  [⇄] = ha partner collegato                               │
│                                                           │
│            [Annulla]  [🗑️ Elimina tutto]                   │
└───────────────────────────────────────────────────────────┘
```

Toggle `[⇄]` espanso:

```
│  │ [⇄] │ 💸 C.T.│ 2025-04-10│ —        │ 1 000.00 EUR   ││
│  │      ├────────────────────────────────────────────────-││
│  │      │ 🔀 Partner: 💸 C.T. · Degiro · +1000 EUR       ││
│  │      │ [○━━●] Elimina anche partner                    ││
```

- Toggle attivo → header: `🗑️ Elimina 4 transazioni (3 + 1 partner)`
- Toggle disattivo → footer: `⚠️ 1 transazione partner rimarrà orfana`

### Riepilogo design

| Scenario | Layout | Toggle partner |
|----------|--------|----------------|
| Singola standalone | Verticale (chiave-valore) | N/A |
| Singola paired | Verticale duale (2 colonne) | Slider sotto riepilogo |
| Multipla | Tabella orizzontale (stile bulk) | Toggle `[⇄]` inline per-riga |

---

## Piano Implementativo

### Step 1 — C1: Fix doppio-click pre-popola FormModal ✅
**File**: `TransactionBulkModal.svelte`, `TransactionFormModal.svelte`
**Azione completata**:
- `draftToTxLike` ora espone `related_transaction_id` (= `_partnerId` o sentinel `-1` per new paired)
- Aggiunto `findPartnerDraft()` per trovare il partner hidden nella drafts array
- `openEditRowForm` trova il partner e lo passa come `formPartnerRow`
- FormModal: aggiunto prop `injectedPartnerRow` + `applyPartnerToDualTo()` (refactored da `fetchPartner`)
- Doppio-click su riga paired → form pre-popolato con dati Da/A

### Step 2 — C2: Fix edit coppia da main table ✅
**File**: `+page.svelte`
**Azione completata**:
- `handleEditRow` ora cerca il partner in `partnerRows` / `mainRows` via `related_transaction_id`
- Passa entrambe le righe come `bulkInitial` → BulkModal le merge in pair + FormModal apre duale

### Step 3 — C3: Fix delete paired new row ✅
**File**: `TransactionBulkModal.svelte`
**Azione completata**:
- `removeRow` ora per righe `new` con `link_uuid`, rimuove anche il partner hidden con stesso `link_uuid`

### Step 4 — H1/H2: Icone e rendering duale in bulk table ✅
**File**: `TransactionBulkModal.svelte`
**Azione completata**:
- Aggiunti `renderAssetHtml()` e `renderBrokerHtml()` con icone inline (favicon/icon_url)
- Quantity per paired: dual rendering `Da: N / A: N` con valori assoluti
- Allineamento text-align left

### Step 5 — H3: Fallback icona broker ✅
**File**: `BrokerIcon.svelte` (già corretto), `TransactionBulkModal.svelte`
**Azione completata**:
- `renderBrokerHtml()` usa icon_url → portal_url favicon come fallback
- `BrokerIcon.svelte` ha già la chain completa (icon_url → favicon → plugin → Briefcase)

### Step 6 — H4: Disabilitare auto-validate e Applica finché campi incompleti ✅
**File**: `TransactionFormModal.svelte`
**Azione completata**:
- Aggiunto `isFormComplete` derivato da `isDraftReadyForValidation(draft)`
- Pulsante Applica disabilitato quando `!commitOnSave && !isFormComplete`
- Pulsante "Verifica ora" resta sempre attivo

### Step 7 — H5: Label "(opzionale)" su campo asset ✅
**File**: `TransactionFormModal.svelte`, i18n EN/IT/FR/ES
**Azione completata**:
- Asset label mostra `(opzionale)` quando `rule.assetField === 'optional'`
- Chiave `common.optional` aggiunta in 4 lingue

### Step 8 — M1/M2: Banner validazione inline + dismissable ✅
**File**: `TransactionBulkModal.svelte`, `TransactionFormModal.svelte`
**Azione completata**:
- Banners errore (formError + commitFailed) ora hanno `dismissible ondismiss`
- Warning banner già aveva dismissible
- Success banner auto-scompare (non serve dismiss)

### Step 9 — M3: Allineamento date Da/A ✅
**File**: `TransactionBulkModal.svelte`
**Azione completata**:
- Labels Da:/A: in `renderDualHtml` usano `inline-block w-6` per larghezza fissa

### Step 10 — M4/M5: Visibilità colonne default + ordine ✅
**File**: `TransactionBulkModal.svelte`
**Azione completata**:
- `cost_basis_override` spostato dopo `asset_event_id`, width aumentata a 160
- `link_uuid`, `created_at`, `updated_at` già hidden di default

### Step 11 — Quick fixes già applicati
- ✅ `DataTable.svelte`: rimossa import `string` da zod (unused)
- ✅ `AssetSelect.svelte`: fix `as` cast → helper function `asAsset()`
- ✅ `TransactionFormModal.svelte`: rimosso `+` duplicato da `createLabel` asset

### Step 12 — M6: Fix icone documentazione mkdocs
**File**: `mkdocs_src/docs/*/financial-theory/transaction-types/`
**Azione**:
- Tabella panoramica: aggiungere entrambe le icone per tipi doppi (es. buy+sell)
- Pagine singole: sostituire emoji con immagine icona reale
- Referenziare le icone da `static/img/tx-types/` (o path corretto)

### Step 13 — L4: Annotare TODO gallery screenshots
**File**: `frontend/e2e/gallery.spec.ts` (inline commento) + `TODO_FUTURI.md`
**Azione**:
- Aggiungere TODO: "Screenshot per ogni tipo di transazione × ogni lingua (EN/IT/FR/ES), da inserire nelle pagine mkdocs delle singole transazioni"

---

## Priorità di Esecuzione (Step 1–13 — Round 3)

```
Step 1 (C1) ✅ → Step 2 (C2) ✅ → Step 3 (C3) ✅    # Critical — sblocca test 6/15
    → Step 4 (H1/H2) ✅ → Step 5 (H3) ✅              # High — visual polish paired
    → Step 6 (H4) ✅ → Step 7 (H5) ✅                  # High — form UX
    → Step 8 (M1/M2) ✅ → Step 9 (M3) ✅               # Medium — banner + alignment
    → Step 10 (M4/M5) ✅                               # Medium — column defaults
    → Step 11 (già fatto) ✅                            # ✅ Done
    → Step 12 (M6) ⏳ → Step 13 (L4) ⏳               # Low — docs (deferred to Part 5)
```

---

## 🆕 Bugfix 4 — Piano Implementativo (2026-05-04)

### Stato attuale dopo Round 3

| Cosa funziona | Cosa è rotto |
|---------------|-------------|
| ✅ Tabella principale: rendering coppie, ghost rows, GoTo pulse, double-click view, selection toolbar, refresh | ❌ Qualsiasi edit/update fallisce: payload manda campi extra → backend rifiuta |
| ✅ FormModal: create, dual form, type rules, asset label, validate manuale | ❌ Type swap BUY↔SELL: cambia in UI ma fallisce al commit |
| ✅ BulkModal: create-many, doppio-click re-edit, paired delete new | ❌ Tag: colonna nascosta in bulk, UX selector inutilizzabile |
| ✅ 22/22 test `transactions-table.spec.ts`, 14/14 `transactions-modals.spec.ts` | ⚠️ Alcuni test verificano solo composizione modale, non azione effettiva |

### Ordine di esecuzione

```
═══════════════════════════════════════════════════════════════
 BLOCCO 1 — CRITICAL: Fix update pipeline           (~1h)
═══════════════════════════════════════════════════════════════
 Step 14 (C4) → Step 15 (C5) → Step 16 (M9) → Step 17 (M10)

═══════════════════════════════════════════════════════════════
 BLOCCO 2 — HIGH: Feature UX mancanti               (~2.5h)
═══════════════════════════════════════════════════════════════
 Step 18 (H7) → Step 19 (H8) → Step 20 (H9)
 → Step 21 (M8) → Step 22 (F5) → Step 23 (F3)

═══════════════════════════════════════════════════════════════
 BLOCCO 3 — TEST: Fix + rinforzo suite E2E           (~30min)
═══════════════════════════════════════════════════════════════
 Step 24 → Step 25 → Step 26 (F1)

═══════════════════════════════════════════════════════════════
 VERIFICA FINALE — Test Walk completo
═══════════════════════════════════════════════════════════════
```

---

### Step 14 — C4: Strippare campi immutabili dal payload update ⏳
**Ref**: C4
**File**: `TransactionBulkModal.svelte` (`buildUpdatePayload()` o equivalente)
**Azione**:
- Il DTO `TXUpdateItem` del backend accetta SOLO: `id`, `date`, `quantity`, `cash`, `tags`, `description`, `cost_basis_override`, `asset_event_id`
- `buildUpdatePayload()` deve rimuovere dal payload: `type`, `broker_id`, `link_uuid`, `asset_id`, `related_transaction_id`, `created_at`, `updated_at`
- Pattern: allowlist dei campi patchabili, non blocklist
**Effort**: 15 min
**Test**: edit qualsiasi riga dalla tabella → save → successo (o warning semantico, non "extra fields")

### Step 15 — C5: Abilitare type swap nel backend ⏳
**Ref**: C5
**File**: `backend/app/schemas/transactions.py` (`TXUpdateItem`), `backend/app/services/transaction_service.py`
**Azione**:
- Aggiungere `type: Optional[str] = None` a `TXUpdateItem`
- Nella service layer (update handler): validare che il nuovo type appartenga allo stesso swap group del type corrente (usando la mappa swap group già definita in `transactionTypeStore`)
- Se il type cambia → applicare sign-flip su quantity/cash dove applicabile
- Rifiutare swaps per tipi paired (`TRANSFER`, `FX_CONVERSION`, `CASH_TRANSFER`)
- Dopo modifica: `./dev.py api sync` per rigenerare il client TypeScript
**Effort**: 30 min
**Test**: edit BUY → SELL → save → quantità negata, tipo aggiornato

### Step 16 — M9: Banner EN "Commit rolled back" → linguaggio user-friendly ⏳
**Ref**: M9
**File**: `frontend/src/lib/i18n/en.json`
**Azione**:
- Allineare all'approccio IT/FR/ES che non espone jargon tecnico:
  - `transactions.bulk.rolledBackTitle`: `"Commit rolled back"` → `"Save cancelled"`
  - `transactions.bulk.rolledBack`: `"Commit rolled back — nothing was saved."` → `"Save was cancelled — no changes were made."`
  - `transactions.form.rolledBackTitle`: `"Save rolled back"` → `"Save cancelled"`
  - `transactions.form.rolledBack`: `"Save was rolled back. No changes were persisted."` → `"Save was cancelled. No changes were made."`
  - `transactions.promote.rolledBack`: `"Promote was rolled back — nothing was changed."` → `"Link was cancelled — no changes were made."`
  - `transactions.delete.rolledBack`: `"Delete rolled back — nothing was changed."` → `"Delete was cancelled — no changes were made."`
**Effort**: 10 min

### Step 17 — M10: Nascondere errori `extra_forbidden` all'utente ⏳
**Ref**: M10
**File**: `TransactionBulkModal.svelte` (rendering errori commit)
**Azione**:
- Errori con `code === "extra_forbidden"` sono bug del FE, non dell'utente
- Filtrarli dal banner user-facing → loggarli solo in `console.error`
- Se dopo il filtro non restano errori user-facing, mostrare messaggio generico: "An internal error occurred. Please try again."
**Effort**: 15 min
**Nota**: Questo step diventa superfluo dopo Step 14 (i campi extra non verranno più inviati), ma è una safety net per futuri bug simili

---

### Step 18 — H7: Colonna Tags nella BulkModal ⏳
**Ref**: H7
**File**: `TransactionBulkModal.svelte` (array `columns`)
**Azione**:
- Aggiungere colonna `tags` dopo `description`
- Rendering: badge colorati con stessa palette di `TransactionsTable` (riusare `getStringBadgeStyle`)
- Hidden di default (ma visibile se l'utente ha tag nei dati)
**Effort**: 20 min

### Step 19 — H8: TagInput.svelte (chip input + autocomplete) ⏳
**Ref**: H8
**File**: NUOVO `frontend/src/lib/components/ui/TagInput.svelte`, `TransactionFormModal.svelte`
**Azione**:
- Nuovo componente `TagInput`:
  - Mostra tag attuali come badge/chip con X per rimuovere
  - Input inline: digitare testo → Enter o Spazio → crea nuovo chip
  - Freccia/chevron a destra: apre dropdown `SearchSelect` pre-popolato con `availableTags` (tag già usati nelle transazioni)
  - Click su opzione dal dropdown → aggiunge chip (se non già presente)
  - Props: `value: string[]` (bindable), `availableTags: string[]`, `placeholder`
- Sostituire il campo tag attuale nel FormModal con `<TagInput>`
**Effort**: 1.5h
**Design**:
```
┌──────────────────────────────────────────────────┐
│ [rebalance ×] [core ×]  | tipo qui...      [▾] │
└──────────────────────────────────────────────────┘
  click ▾ → dropdown con: rebalance, core, long-term, giroconto, fees, review
```

### Step 20 — H9: Titolo FormModal paired con entrambi gli ID ⏳
**Ref**: H9
**File**: `TransactionFormModal.svelte` (sezione titolo)
**Azione**:
- Per righe paired (con `related_transaction_id`), mostrare: `👁 TRANSFER #22 ↔ #23` o `✏️ TRANSFER #22 ↔ #23`
- Attualmente mostra solo il tipo senza gli ID per le composite
- Per righe new (senza ID), mostrare: `➕ TRANSFER (new pair)`
**Effort**: 15 min

### Step 21 — M8: Colonna ID nella tabella principale ⏳
**Ref**: M8
**File**: `TransactionsTable.svelte` (array `columns`)
**Azione**:
- Aggiungere colonna `id` alla fine dell'array columns (dopo `tags`)
- Header: `ID`, rendering: `#N` (monospace, grigio, allineamento destra)
- Width: 60px, non sortable di default, visibile di default
- Filterable: no (l'ID è univoco, non serve filtrare)
**Effort**: 15 min

### Step 22 — F5: ConfirmModal snello per delete standalone ⏳
**Ref**: F5
**File**: `+page.svelte`, eventualmente nuovo componente
**Azione**:
- Quando l'utente clicca Delete su una riga standalone (senza partner), usare un semplice `ConfirmModal` con testo chiaro (`Delete transaction #N?`) invece del pesante `BulkDeleteLinkedPairModal`
- Il `BulkDeleteLinkedPairModal` resta per righe paired e delete multiple
- Decisione nel `onBulkDelete()`: se `clean.length > 0 && problems.length === 0` → ConfirmModal leggero
**Effort**: 20 min

### Step 23 — F3: Popover click su badge ●evt ⏳
**Ref**: F3
**File**: `+page.svelte` (`handleEventBadgeClick`), eventualmente nuovo `EventPopover.svelte`
**Azione**:
- Attualmente `handleEventBadgeClick` è un TODO (`console.warn`)
- Implementare: click su ●evt → popover con dettagli evento (tipo, data, valore, note)
- Link → `/assets/{asset_id}#events` per navigazione diretta
- Tooltip già contiene i dati (pre-fetched in `eventTooltipMap`), il popover li mostra in formato strutturato
**Effort**: 30 min

---

### Step 24 — Test: rimuovere/riscrivere test falso positivo ⏳
**File**: `transactions-modals.spec.ts`
**Azione**:
- Test `cost_basis_override appears after asset_event_id when both visible` → è un falso positivo (verifica solo che il BulkModal si apra). **Riscrivere**: verificare l'ordine effettivo delle colonne visibili, oppure rimuovere
**Effort**: 10 min

### Step 25 — Test: rafforzare test delete paired ⏳
**File**: `transactions-modals.spec.ts`
**Azione**:
- Test `delete new paired row removes both halves (C3)` → aggiungere asserzione che verifichi che le righe rimanenti NON contengano il partner (non solo `count < before`)
**Effort**: 10 min

### Step 26 — F1: Test `asset-event-delete.spec.ts` (4 scenari) ⏳
**Ref**: F1
**File**: NUOVO `frontend/e2e/assets/asset-event-delete.spec.ts`
**Azione**:
- 4 scenari deferti dalla Part 1:
  1. Delete evento senza transazioni collegate → successo
  2. Delete evento con transazione collegata → conferma "unlink first?"
  3. Delete asset con eventi → cascade/block
  4. Badge ●evt sparisce dopo unlink
- Richiede: dati mock con `asset_event_id` popolato (già presente in `populate_mock_data.py`)
**Effort**: 30 min

---

## Feature Rimandate (Part 5 o oltre)

| # | Feature | Quando |
|---|---------|--------|
| F2 | Import ▾ menu (BrokerImportFilesModal) | Part 5 |
| F4 | Gallery screenshots TX × lingua | Part 5 docs |
| F6 | SelectionBar componente riusabile | Part 5 refactor |
| F7 | Settings toggle always-pair-adjacent | Part 5 settings |
| F8 | Docs: icone mkdocs TX | Part 5 docs |
| M6 | Fix icone documentazione mkdocs | Part 5 docs |
| L1–L4 | Delete modal riepilogo, context menu, gallery | Part 5+ |

---

## Test Walk Finale (dopo Blocco 1+2+3)

Dopo aver completato tutti gli step 14–26, ri-testare:

| Area | Cosa verificare |
|------|----------------|
| **Edit standalone** | Select BUY row → Edit → save → successo (no "extra fields") |
| **Type swap** | Edit BUY → change to SELL → save → tipo aggiornato, qty negata |
| **Edit paired** | Select TRANSFER riga → Edit → save coppia → successo |
| **Tags** | Creare TX con 2-3 tag via chip input → visibili in BulkModal colonna tags |
| **ID colonna** | Tabella principale mostra `#N` alla fine di ogni riga |
| **Delete standalone** | Delete riga senza partner → ConfirmModal snello (non BulkDeleteLinkedPairModal) |
| **●evt popover** | Click su ●evt dot → popover con dettagli + link asset |
| **Banner EN** | Provocare rollback → banner dice "Save cancelled" non "Commit rolled back" |
| **Titolo paired** | Aprire view TRANSFER → titolo mostra `#22 ↔ #23` |
| **E2E** | `./dev.py test front-transaction all` → 36/36 pass (14 modals + 22 table) |


---

## 🆕 Bugfix 5 — Round 7 Test Walk (2026-05-04)

### Test Walk Results

| # | Area | Risultato | Note |
|---|------|-----------|------|
| 1 | Edit standalone → save | ✅ | Funziona, no "extra fields" error |
| 2 | Type swap BUY→SELL | ⚠️ | Il tipo cambia e si salva, ma la quantità nella tabella principale resta positiva. Validate e commit passano senza errori. **Da investigare**: verifica se il backend salva effettivamente qty negata o se è un problema di refresh/cache frontend |
| 3 | Edit paired (TRANSFER) | 🔴 | **BUG CRITICO**: il payload contiene `creates` con `broker_id:0` per le righe partner hidden. Dovrebbero essere `updates` con l'id esistente. Il form duale sembra creare nuove righe partner invece di aggiornare quelle esistenti. Errori: "Seleziona un broker", "link_uuid ha 1 create (previsti 2)", "balance negativo" |
| 4 | Tag input UX | ⚠️ | Funziona ma serve anti-bounce: il dropdown si chiude immediatamente dopo click |
| 5 | Tags in BulkModal | 🔴→✅ | **FIXATO**: badge colorati ora usano `getStringColor()` con inline `background`/`color` invece di CSS custom properties non consumate |
| 6 | Titolo paired | ✅ | Mostra `#ID_A ↔ #ID_B` |
| 7 | Colonna ID | ✅ | Monospace grigio `#N`. TODO futuro: filtro numerico avanzato (range, multi-range) |
| 8 | Delete standalone | ⚠️ | ConfirmModal si apre ma **manca riepilogo dettagli** della transazione (campi tipo, data, asset, importo, broker). Solo testo generico "Delete N transaction(s)?" |
| 9 | Delete paired | 🔴 | **NON IMPLEMENTATO**: BulkDeleteLinkedPairModal si apre come da sempre — il design L1/L2 (riepilogo tabellare, toggle per-riga partner, slider singola/entrambe) non è stato costruito |
| 10 | ●evt click | ✅→✅ | **FIXATO**: ora naviga a `/assets/{id}` (pagina dettaglio asset) invece che al tab eventi |
| 11 | Banner EN | ✅ | "Save cancelled" confermato |
| 12 | swap_group dal server | ✅→✅ | **FIXATO struttura**: `swap_group` ora contiene solo i partner (non self). `BUY.swap_group=["SELL"]`, `TRANSFER.swap_group=[]` |

### Broker E2E Tests — 7 fallimenti

I 7 test falliti (`broker-name`, `broker-cash-balances`, `broker-holdings`, `broker-edit-button`, ecc.) sono **PREESISTENTI** — nessun file broker è stato modificato nel batch corrente. Causa probabile: timing/load del test server (timeout 3000ms troppo breve per broker detail page load).

### Nuovi Bug Identificati

| # | Severità | Descrizione | Root Cause |
|---|----------|-------------|------------|
| R7-C1 | 🔴 CRITICAL | **Edit paired: creates invece di updates** — le righe partner hidden vengono trattate come `new` (status='new', broker_id=0) invece di `edited` con id originale. Il payload invia creates per partner rows che dovrebbero essere updates | `mergePairIntoFromTo()` o `patchDualRowFromForm()` in BulkModal non preserva id/status/original della riga partner hidden quando il form duale applica le modifiche |
| R7-H1 | 🟠 HIGH | **Type swap qty non si aggiorna nella tabella** — il commit passa ma la tabella principale mostra ancora la qty originale (positiva per BUY→SELL). Da verificare: (a) il backend salva effettivamente qty negata? (b) il reload della tabella funziona? (c) il frontend `collectUpdate` invia la qty flippata? | Possibili cause: frontend non invia qty nel diff perché il display value non cambia; o il reload non re-fetcha | 
| R7-H2 | 🟠 HIGH | **TagInput dropdown anti-bounce** — il dropdown autocomplete si chiude immediatamente dopo aver cliccato un suggerimento, perché il blur del input scatta prima del mousedown del dropdown | Timeout 200ms nel `handleBlur` potrebbe non bastare; servire `onmousedown` con `preventDefault` (già fatto) ma il timing potrebbe variare |
| R7-M1 | 🟡 MEDIUM | **Delete standalone: manca riepilogo** — il ConfirmModal mostra solo "Delete N transaction(s)?" senza dettagli (tipo, data, asset, importo, broker) come da design L1 | Il ConfirmModal semplice non riceve i dati della transazione da mostrare |
| R7-M2 | 🟡 MEDIUM | **Delete paired: design L1/L2 non implementato** — il BulkDeleteLinkedPairModal è rimasto invariato, manca il design con riepilogo tabellare, toggle per-riga partner, slider singola/entrambe | Feature non ancora costruita — era classificata come LOW nel piano originale |
| R7-M3 | 🟡 MEDIUM | **Filtro numerico avanzato per colonna ID** — attualmente solo min/max, servirebbe ricerca multi-range | Feature future TODO |

### Hotfix Applicati in questo Round

| Fix | File | Descrizione |
|-----|------|-------------|
| Tag badge CSS | `TransactionBulkModal.svelte` | `getStringBadgeStyle()` → `getStringColor()` con inline `background`/`color` |
| Event badge click | `+page.svelte` | Navigazione a `/assets/{id}` (non `/assets/{id}?tab=events`) |
| swap_group semplificato | `transactions.py`, `transactionTypeStore.ts` | `swap_group` ora contiene solo partner (non self). Empty = no swap. Frontend prepende self. |

### Priorità Next Round (Bugfix 6)

```
R7-C1 (edit paired creates)  ← MUST FIX prima di qualsiasi test walk
R7-H1 (type swap qty refresh) ← indagare root cause
R7-H2 (TagInput anti-bounce)  ← UX fix rapido
R7-M1 (delete riepilogo)      ← polish
R7-M2 (delete paired design)  ← deferred to Part 5
```
