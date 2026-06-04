# Plan: D2 Round 2 — Walktest Feedback Round (v3 — final)

Post-walktest round: fix UX + 3 feature bloccanti (cost_basis con valuta+FX, AssetEvent picker riusando DataEditor, paired TX store-first). Ordine: backend → test backend → frontend. 18 step, organizzati in 5 sotto-piani.

**Parent plan**: `plan-PlanD2_FrontendSplitPromoteUI.prompt.md`
**Previous bugfix**: `plan-bugfix4_SplitSuggestPmcOverrideUx.prompt.md`

---

## Steps — BACKEND

### Step 1: DB + Schema — `cost_basis_override` → `Currency`

In `backend/app/db/models.py` riga 653, aggiungere `cost_basis_currency: Optional[str]` con `_validate_currency_field`. In `backend/alembic/versions/001_initial.py` aggiungere colonna `cost_basis_currency VARCHAR(3)`. In `backend/app/schemas/transactions.py` cambiare `cost_basis_override: Optional[SafeDecimal]` → `cost_basis_override: Optional[Currency]` (oggetto `{code, amount}`). Adattare `TXCreateItem`, `TXUpdateItem`, `TXReadItem`. Eseguire `./dev.py db create-clean` + `./dev.py api sync`.

### Step 2: Schema — `WACResult` + `WACConversionInfo`

Nuovi modelli in `backend/app/schemas/transactions.py`:

- `WACConversionInfo(tx_id, from_currency, to_currency, rate, rate_date, stale_days)`
- `WACResult(wac: Optional[Currency], conversions: list[WACConversionInfo], missing_pairs: list[str])`
- Aggiungere campo opzionale `wac_info: Optional[WACResult]` in `TXBatchResultItem`.

### Step 3: Service — `compute_weighted_avg_cost` con FX

In `backend/app/services/transaction_service.py` riga 59:

- Nuovo parametro `target_currency: str`.
- Per ogni BUY/TRANSFER con valuta ≠ `target_currency` → convertire via FX rate del giorno della TX.
- Se **anche una sola** conversione FX impossibile → return `WACResult(wac=None, conversions=[...], missing_pairs=[...])`.
- Logica valuta target: maggioritaria tra TX, pareggio → valuta asset, se non corrisponde → prima alfabeticamente.
- Quando `total_qty == 0` e nessun errore FX → `WACResult(wac=Currency(code=target, amount="0"), ...)`.
- Restituire sempre `WACResult`.

### Step 4: Service — auto-calc adattato

In `transaction_service.py` righe 1353-1362 e 1409-1424, usare nuovo `compute_weighted_avg_cost` con `WACResult`. Quando `wac is None` → `receiver.cost_basis_override = None`, `receiver.cost_basis_currency = None`. Propagare `wac_info` nel `TXBatchResultItem`.

### Step 5: Nuovo endpoint — POST `/api/v1/transactions/recalc-wac`

Accetta `{tx_ids: list[int]}`. Validazioni: tutte le TX devono riferirsi allo **stesso asset** (non necessariamente stesso broker). Per ciascuna TX TRANSFER ricevente, ricalcola WAC, salva, restituisce lista di `WACResult`. Endpoint leggero in `transactions.py`, con TODO per futura categoria `analytics/`.

### Step 6: Test backend — cost_basis con valuta + recalc-wac

In `backend/test_scripts/test_api/test_transactions_wac.py`: 10 test WAC-1→WAC-10 (vedi sezione test). Aggiornare 3 file test esistenti. Mock data additions.

---

## Steps — FRONTEND

### Step 7: BulkModal toolbar → allineamento a destra

In `TransactionBulkModal.svelte` toolbar, `justify-between` con left-group e right-group.

### Step 8: BulkModal split — edit apre come ADJUSTMENT + "undo" label

`handleEditRowClick()`: se `splitTxIdsSet.has(op.txId)` → tipo target. Azione "undo-split" → "undo".

### Step 9: BulkModal split type preview

`[icon originale] → [icon target] Target Label`. No label originale, no `↔`.

### Step 10: Suggest — filtro sottrattivo + formato human-readable + 💡 lightbulb

Escludere candidati DB già in ops. Formato: `• [🔗] Merge Tx Row#N (icon) and DB#ID (icon) → Target (icon) (ΔNd)`. Multi-match → nested sub-list. Lightbulb per-row + toolbar. Banner solo se TX suggerite già in bulk.

### Step 11: PromoteMergeModal — rimuovere date/cost_basis + layout bottoni

Rimuovere `diffDate`, `diffCostBasis`. `justify-between`. ⟷ senza label, solo icona centrata.

### Step 12: TransactionActionModal — tipo su entrambe le colonne + campi AFTER

Tipo+icona su From e To. AFTER con quantity, tags, description.

### Step 13: FormModal — `showCostBasisField` include ADJUSTMENT + CompactCash + tooltip

Condizione: `TRANSFER || ADJUSTMENT`. Sostituire input numerico con `CompactCash` (amount + currency selector). Tooltip info con link doc PMC. Warning se ADJUSTMENT qty>0 senza override. Segno FX "From" positivo con indicatori ±.

### Step 14: AssetEvent picker modale (riuso DataEditor)

Nuova modale `AssetEventPickerModal.svelte` che riusa `DataEditor` dell'asset detail, tab eventi. Slider Δ days, vincolo date, radio selection, Import CSV + Add row, chip nel form.

```
┌──────────────────────────────────────────────────────────┐
│ 📅 Select Asset Event                                [×]│
├──────────────────────────────────────────────────────────┤
│ Asset: MWRD — Amundi Core MSCI World      EUR 🇪🇺       │
│ TX Date: 2026-05-14    Δ days: [════●════] 7            │
├──────────────────────────────────────────────────────────┤
│ [📤 Import CSV]  [+ Add row]          1 new  👁         │
├────┬──────────┬────────────┬──────────┬─────────┬───────┤
│ ○  │ Date     │ Type       │ Amount   │ Notes   │ Acts  │
├────┼──────────┼────────────┼──────────┼─────────┼───────┤
│ ○  │2026-05-10│ 💰DIVIDEND │ 0.25     │Q1 pay   │ 🗑 ↩  │
│ ○  │2026-05-12│ ✂️ SPLIT   │ 2.00     │2:1      │ 🗑 ↩  │
│ +  │2026-05-14│ [enum ▼]   │ [____]   │[____]   │ 🗑 ↩  │
├────┴──────────┴────────────┴──────────┴─────────┴───────┤
│ [Save (1)]  [Cancel]                                    │
│                             [Cancel picker] [✓ Select]  │
└──────────────────────────────────────────────────────────┘
```

### Step 15: FormModal — WAC Info modal post-commit

Modale informativa con conversioni FX, missing pairs, Sync All FX, Recalculate, Docs link.

```
┌──────────────────────────────────────────────────────────┐
│ 📊 Cost Basis Calculation Report                     [×]│
├──────────────────────────────────────────────────────────┤
│                                                          │
│  WAC calculated: 168.74 EUR                              │
│                                                          │
│  ┌ FX Conversions Applied ──────────────────────────┐   │
│  │ TX#12 BUY    50.00 USD → EUR  @0.9231  2026-05-10│   │
│  │              ⚠️ rate stale by 2 days               │   │
│  │ TX#15 BUY   100.00 GBP → EUR  @1.1654  2026-05-13│   │
│  │              ✅ rate fresh                          │   │
│  └──────────────────────────────────────────────────────┘│
│                                                          │
│  ┌ ⚠️ Missing FX Pairs ────────────────────────────────┐ │
│  │ CHF/EUR — no rate available                         │ │
│  │ → Add this pair in FX settings                      │ │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ℹ️ Stale rates may produce inaccurate results.          │
│  You can override the cost basis manually or sync        │
│  FX rates and recalculate.                               │
│  📖 How cost basis is calculated                         │
│                                                          │
├──────────────────────────────────────────────────────────┤
│ [🔄 Sync All FX]  [📖 Docs]         [Recalculate] [OK] │
└──────────────────────────────────────────────────────────┘
```

### Step 16: Paired TX — store-first con refresh

In `fetchPartner()`: `txStoreGet` prima, GET in parallelo con entrambi gli id, update reattivo, fallback silenzioso.

### Step 17: BulkModal — paired column `#62 ↔ #63`

### Step 18: i18n chiavi nuove (incrementale in SP-C e SP-D)

---

## Coherence Analysis & Test Gap Assessment

### Copertura attuale

| Area | File di test | Cosa copre |
|------|-------------|------------|
| Split TRANSFER batch | `test_transactions_batch_split_promote.py` B1.1 | split → 2 ADJUSTMENT |
| Promote suggest | `test_transactions_batch_split_promote.py` B3.1-B3.6 | tolerance, self-exclude |
| Schema TRANSFER | `test_transaction_schemas.py` | link_uuid, asset, qty, no cash |
| Service cost_basis | `test_transaction_service.py::test_get_cost_basis` | BUY sum (single currency) |
| E2E cost_basis | `tx-commit-all-types.spec.ts` | TRANSFER con override string |
| E2E split guards | `tx-split-promote.spec.ts` | hidden on standalone |

### Coherence issues

| # | Problema | Impatto |
|---|---------|---------|
| C1 | cost_basis da SafeDecimal → Currency. Test con `"42.50"` rompono. | SP-A+B |
| C2 | compute_weighted_avg_cost da `Decimal\|None` → `WACResult`. | SP-A+B |
| C3 | Zero test auto-calc WAC su TRANSFER create. | WAC-2 |
| C4 | Zero test WAC cross-currency FX. | WAC-3, WAC-4 |
| C5 | Zero test E2E per split BulkModal, lightbulb, picker, WAC Info. | SP-E |
| C6 | TXBatchResultItem senza wac_info. Zod rigenera. | SP-E |

### Test plan — Backend (`test_transactions_wac.py`)

| ID | Scenario | Verifica |
|----|----------|----------|
| WAC-1 | TRANSFER con `cost_basis_override: {code:"EUR", amount:"42.50"}` | Accettato, salvato, GET = Currency |
| WAC-2 | TRANSFER senza override, BUY tutti EUR | auto-calc WAC EUR |
| WAC-3 | TRANSFER senza override, BUY EUR+USD con FX pair | WAC convertito, conversions |
| WAC-4 | TRANSFER senza override, BUY EUR+CHF senza FX pair | null, missing_pairs |
| WAC-5 | TRANSFER senza override, nessun BUY | {code:target, amount:"0"} |
| WAC-6 | recalc-wac 2 TX stesso asset, broker diversi | Entrambi aggiornati |
| WAC-7 | recalc-wac TX asset diversi | 400 |
| WAC-8 | recalc-wac TX non-TRANSFER | Ignorate |
| WAC-9 | old format `"42.50"` | 422 |
| WAC-10 | invalid currency `{code:"INVALID"}` | 422 |

### Test plan — Frontend E2E

| File | Test |
|------|------|
| `tx-wac-cost-basis.spec.ts` | FE-CB-1→4: CompactCash, auto-calc, warning, tooltip |
| `tx-split-ux.spec.ts` | FE-SP-1→5: split+commit, edit ADJUSTMENT, undo, preview, AFTER |
| `tx-suggest-ux.spec.ts` | FE-SG-1→5: banner, filtro, slider, lightbulb, MergeModal |
| `tx-event-picker.spec.ts` | FE-EP-1→4: modale, select→chip, date vincolo, CSV |

### Non-regression

| NR | Rischio | Test |
|----|---------|------|
| NR-1 | Schema cost_basis rompe tutti i tipi TX | `tx-commit-all-types.spec.ts` |
| NR-2 | WACResult rompe parsing | Zod rigenerato |
| NR-3 | MergeModal rompe promote | `tx-crud-full.spec.ts` |
| NR-4 | Store-first rompe loading | `tx-paired-edit.spec.ts` |
| NR-5 | Picker rompe flow evento | `transactions-modals.spec.ts` |

---

## Sub-Plan Architecture

```
  ┌─────────────┐
  │  SP-A        │ Cost Basis Currency + WAC Service (Steps 1-5)
  │  🔴 DETAILED │ Breaking change DB → schema → service → endpoint
  └──────┬───────┘
         │
  ┌──────▼───────┐
  │  SP-B        │ Backend Tests + Mock Data (Step 6 + updates)
  │  🟡 GROUPED  │ 10 nuovi test + 3 aggiornamenti + mock data
  └──────┬───────┘
         │
    ═══ ./dev.py db create-clean && ./dev.py api sync ═══
         │
  ┌──────▼───────┐
  │  SP-C        │ BulkModal UX + Suggest + Modals (Steps 7-12, 17)
  │  🔴 DETAILED │ UX polish + suggest overhaul + lightbulb
  └──────┬───────┘
         │
  ┌──────▼──────────────────────────┐
  │  SP-D                           │
  │  🔴 DETAILED                    │
  │  FormModal features + i18n      │
  │  Steps 13-16, 18               │
  └──────────────┬──────────────────┘
                 │
  ┌──────────────▼───────────────┐
  │  SP-E                        │
  │  🟡 GROUPED                  │
  │  E2E tests + NR + runner     │
  └──────────────────────────────┘
```

| SP | Steps | Tipo | Stima | Dipende da | Detailed Plan | Status |
|----|-------|------|-------|------------|---------------|--------|
| **SP-A** | 1-5 | 🔴 DETAILED | ~10h | — | [`plan-R2-SP-A-CostBasisWAC`](./R2-WalktestFeedback/plan-R2-SP-A-CostBasisWAC.prompt.md) | ✅ DONE (commit `92f4b1ba`) |
| **SP-B** | 6 + updates + mock | 🟡 GROUPED | ~4h | SP-A | [`plan-R2-SP-B-BackendTests`](./R2-WalktestFeedback/plan-R2-SP-B-BackendTests.prompt.md) | ✅ DONE (commit `473d2611`) |
| **SP-C** | 7-12, 17 | 🔴 DETAILED | ~10h | api sync | [`plan-R2-SP-C-BulkModalSuggestUX`](./R2-WalktestFeedback/plan-R2-SP-C-BulkModalSuggestUX.prompt.md) | ✅ DONE (commits `834028ba`..`9b908c26`) |
| **SP-C Bugs 1-11** | walktest WAC | — | — | SP-C | SP-C-Bugfix/ + WacPreview/ (8 piani) | ✅ ALL DONE (2026-05-30) |
| **SP-D** | 13-16, 18 | 🔴 DETAILED | ~12h | SP-C | [`plan-R3-SP-D`](../plan-R3-SP-D-FormModalEventPickerWacFx.prompt.md) + [`Bugfix-SPD/`](../Bugfix-SPD/) | ✅ DONE (2026-06-04) |
| **SP-E** | E2E tests | 🟡 GROUPED | ~6h | SP-D | — | 🔲 TODO |

**Totale**: ~42h (~8-9 giorni) — SP-A/B/C completati, restano SP-D + SP-E (~18h)

### Execution sequence

```
✅ Week 1 (backend):  SP-A → SP-B → db create-clean + api sync         DONE
✅ Week 2 (frontend): SP-C (+ BugfixRound1/2/3 + Round6.1 + ADJUSTMENT) DONE
✅ Week 2b (bugs):    SP-C Bugs ALL (8 plans in WacPreview/)             DONE
✅ Week 3 (frontend): SP-D (FormModal features)                          DONE
✅ Week 4 (testing):  SP-E (E2E) — assorbito in SP-C bugs + SP-D bugfix   DONE
```

Al termine di questo lavoro di sviluppo, aggiornare la wiki con le nuove funzionalità, i nuovi test, e qualsiasi decisione o insight emerso durante l'implementazione. Eseguire `graphify corpus/ --update` per rendere tutto immediatamente consultabile.
Quindi, basandosi sul report "LibreFolio_devWiki/code-reality-check.md", identificare eventuali discrepanze tra codice e wiki, e aggiornare la wiki per allinearla alla realtà del codice, seguendo le linee guida di filing e coherence analysis già illustrate.

---

## Sub-Plan Prompts

### SP-A: Cost Basis Currency + WAC Service

> **File**: `plan-R2-SP-A-CostBasisWAC.prompt.md`

```
# Task: SP-A — Cost Basis Override con Currency + WAC Service + recalc-wac endpoint

## Context
Leggi il piano master `plan-R2-WalktestFeedbackRound.prompt.md`
per il contesto completo. Leggi anche `bugfix_4_SplitSuggestPmcOverrideUx` per lo stato attuale
del cost_basis_override (oggi SafeDecimal, domani Currency).

## Scope — Steps 1-5 del piano master
Tutto il backend: DB model, Alembic, Pydantic schemas (TXCreateItem/TXUpdateItem/TXReadItem + WACResult +
WACConversionInfo + TXBatchResultItem), service compute_weighted_avg_cost con FX cross-currency,
auto-calc adattato ai 2 call-site, nuovo endpoint recalc-wac.

## What to implement
1. DB + Alembic: cost_basis_currency VARCHAR(3) + ORM field con validator.
2. Schema: cost_basis_override da SafeDecimal → Currency su Create/Update/Read.
   Nuovi modelli WACConversionInfo + WACResult. Campo wac_info su TXBatchResultItem.
3. Service: riscrivere compute_weighted_avg_cost() — target_currency, FX conversion,
   WACResult return. Se una sola conversione FX impossibile → wac=None + missing_pairs.
   Valuta target: maggioritaria, pareggio → asset currency, altrimenti → alfabetica.
   total_qty==0 → Currency(code=target, amount="0").
4. Auto-calc: adattare i 2 call-site in transaction_service.py.
5. Endpoint recalc-wac: POST, validazione stesso asset, ricalcolo per TRANSFER riceventi.

## Key files to read first
- backend/app/db/models.py — Transaction model, cost_basis fields
- backend/app/schemas/transactions.py — TXCreateItem, TXUpdateItem, TXReadItem, TXBatchResultItem
- backend/app/schemas/common.py — Currency class
- backend/app/services/transaction_service.py — compute_weighted_avg_cost, auto-calc call-sites
- backend/app/services/fx.py — FX rate lookup per data
- backend/alembic/versions/001_initial.py — transactions table

## Constraints
- Conversione FX impossibile → WACResult(wac=None), TX riceve null
- total_qty == 0 senza errori FX → Currency(amount="0"), NON None
- Vecchio formato (SafeDecimal puro) → 422, no backward compatibility
- Alla fine: ./dev.py db create-clean + ./dev.py api sync devono passare
- Aggiornare i test backend esistenti che rompono (breaking changes)
```

### SP-B: Backend Tests + Mock Data

> **File**: `plan-R2-SP-B-BackendTests.prompt.md`

```
# Task: SP-B — Backend Tests WAC + Mock Data

## Context
SP-A completato: cost_basis è Currency, compute_weighted_avg_cost restituisce WACResult.
Leggi il piano master per la tabella WAC-1→WAC-10 e la lista test da aggiornare.

## Scope — Step 6 + test updates + mock data
1. Nuovo test_transactions_wac.py — 10 test.
2. Aggiornare test_transaction_schemas.py, test_transaction_service.py,
   test_transactions_batch_split_promote.py.
3. Mock data: BUY multi-valuta, FX pair, AssetEvent DIVIDEND, tag wac-test.

## Pass criterion
./dev.py test all-backend → tutti verdi.
```

### SP-C: BulkModal + Suggest + Modals UX

> **File**: `plan-R2-SP-C-BulkModalSuggestUX.prompt.md`

```
# Task: SP-C — BulkModal UX Polish + Suggest Overhaul + Modal Cleanup

## Context
Backend completato (SP-A+B), api sync eseguito. Leggi il piano master Steps 7-12, 17.
Leggi bugfix_4 per lo stato attuale dei componenti.

## Scope — Steps 7, 8, 9, 10, 11, 12, 17

### Quick UX fixes (~4h)
- Toolbar alignment, split edit→ADJUSTMENT, split preview, MergeModal cleanup,
  ActionModal columns, paired column display

### Suggest overhaul (~6h)
- Filtro sottrattivo, banner human-readable Row# cliccabili, nested multi-match,
  lightbulb per-row + toolbar, banner solo se già in bulk

## Verify
Walktest manuale W1-W5, W11-W13, W17.
Aggiungere i18n keys man mano.
```

### SP-D: FormModal Features + i18n

> **File**: `plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-D-FormModalFeaturesI18n.prompt.md`

```
# Task: SP-D — FormModal CompactCash + WAC Info + EventPicker + Store-first + i18n

## Context
SP-C completato. Leggi il piano master Steps 13-16, 18. Verificare stato componenti
dopo SP-C prima di procedere. Questo è l'SP più ampio — feature nuove.

## Scope — Steps 13, 14, 15, 16, 18
- CompactCash per cost_basis (TRANSFER || ADJUSTMENT), tooltip, warning, FX sign
- AssetEventPickerModal riusando DataEditor (slider, vincolo date, radio, CSV, chip)
- WACInfoModal post-commit (conversioni FX, missing pairs, Sync/Recalculate/Docs)
- Store-first fetch (txStoreGet → GET parallelo → update reattivo)
- i18n chiavi rimanenti

## Notes
Feature nuove: il piano di dettaglio deve verificare il DOM attuale.
i18n si aggiunge man mano, non alla fine.
```

### SP-E: E2E Tests

> **File**: `plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-E-E2ETests.prompt.md`

```
# Task: SP-E — E2E Test Suite per Round 2

## Context
SP A-D completati. Frontend nella forma finale.
Leggi il piano master per tabelle test E2E e NR.

## Scope
1. 4 nuovi spec files (18 test totali)
2. Aggiornare 4 file spec esistenti
3. Registrare in _frontend_transaction.py
4. Run NR-1→5
5. ./dev.py test all-frontend → verde

## Notes
Verificare DOM e data-testid attuali prima di scrivere test.
Se mock data mancanti → aggiornare populate_mock_data.py.
```

---

## Further Considerations

1. **SP-A è il gate critico**: eseguire SP-A → SP-B e verificare all-backend prima di toccare frontend.
2. **SP-C e SP-D in sequenza**: SP-D dipende dalle pulizie di SP-C.
3. **Sotto-piani DETAILED uno alla volta**, appena prima di eseguirli.
4. **i18n incrementale**: in SP-C e SP-D, non alla fine.
5. **Stima conservativa**: 42h include imprevisti.
