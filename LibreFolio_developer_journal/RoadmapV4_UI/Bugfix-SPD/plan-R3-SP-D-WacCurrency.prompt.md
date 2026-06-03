# Plan: R3-SP-D-WacCurrency — WAC Target Currency Selector

**Date**: 3 Giugno 2026
**Status**: ✅ DONE
**Priority**: P1
**Parent**: [`plan-R3-SP-D-BugfixRound2.prompt.md`](./plan-R3-SP-D-BugfixRound2.prompt.md)
**Origin**: Walktest Round 1 — colonna PMC con valute miste, currency non selezionabile

---

## 🎯 Obiettivo

Permettere all'utente di scegliere la valuta target del calcolo WAC (PMC). Eliminare l'euristica "maggioranza" e sostituirla con:
- **Default**: valuta dell'ultima acquisizione (deterministica)
- **Override**: l'utente sceglie dal chip valuta nella riga suggestion

---

## Principi di Design

| Principio | Decisione |
|-----------|-----------|
| Nessun campo nuovo | Riuso di `cost_basis_override.code` come currency hint quando `cost_basis_mode` è "auto"/"auto-detail" |
| Sentinella | `override: {code: "KRW", amount: "0"}` = "calcola WAC in KRW". Amount=0 placeholder (backend lo sovrascrive) |
| Null = backend decide | `override: null` + mode auto → backend usa "ultima acquisizione" |
| Default deterministico | `determine_target_currency()` = valuta della TX acquisizione più recente (non più maggioranza) |
| Chip valuta | Appare nella riga PMC suggestion, opaco sempre (anche in auto). Cambio valuta ≠ switch a manual |
| Bulk | Ogni riga ha il suo `cost_basis_override.code` hint — persistito nel draft |
| Analytics | Futuro `/analytics/wac-preview?currency=KRW` mappa allo stesso parametro |

---

## Protocollo Frontend ↔ Backend

```
┌─────────────────────────────────────────────────────────────────────────┐
│  CASO 1: Auto, nessun hint (1° calcolo)                                 │
│                                                                          │
│  Request:  cost_basis_mode: "auto-detail"                                │
│            cost_basis_override: null                                      │
│                                                                          │
│  Backend:  target = last_acquisition_currency (es. EUR)                  │
│            → calcola WAC in EUR                                          │
│                                                                          │
│  Response: wac: {code: "EUR", amount: "50.00"}                           │
│            wac_qualifying_txs: [...]                                      │
│                                                                          │
│  Frontend: chip mostra [€ 🇪🇺 EUR ▼]                                     │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│  CASO 2: Auto, utente sceglie KRW                                        │
│                                                                          │
│  Request:  cost_basis_mode: "auto-detail"                                │
│            cost_basis_override: {code: "KRW", amount: "0"}               │
│                                                                          │
│  Backend:  target = "KRW" (dal override.code, mode è auto)               │
│            → converte tutte le TX in KRW → calcola WAC                   │
│                                                                          │
│  Response: wac: {code: "KRW", amount: "72500"}                           │
│            wac_qualifying_txs: [...] (con frecce EUR→KRW)                │
│                                                                          │
│  Frontend: chip mostra [₩ 🇰🇷 KRW ▼]                                    │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│  CASO 3: Missing pair                                                    │
│                                                                          │
│  Request:  come Caso 2 ma EUR/KRW non configurata                        │
│                                                                          │
│  Response: wac: null                                                     │
│            wac_missing_pairs: ["EUR/KRW"]                                │
│                                                                          │
│  Frontend: chip resta [₩ 🇰🇷 KRW ▼], errore nel banner                  │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│  CASO 4: Commit                                                          │
│                                                                          │
│  Request:  cost_basis_mode: "auto"                                       │
│            cost_basis_override: {code: "KRW", amount: "0"}               │
│                                                                          │
│  Backend:  calcola WAC in KRW → SCRIVE nel DB:                           │
│            cost_basis_override = 72500                                    │
│            cost_basis_currency = "KRW"                                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Estetica — Chip Valuta nel PMC Suggestion

### Layout (Opzione C con chip nel risultato)

**Stato iniziale (loading / 🏳️):**
```
┌──────────────────────────────────────────────────────────────────────┐
│  Override costo medio ⓘ  [💱 FX]              [ Auto | Manuale ]     │
│                                                                       │
│  💡 PMC: …  [🏳️ ▼] ⏳                                               │
└──────────────────────────────────────────────────────────────────────┘
```

**Stato calcolato (auto, backend ha risposto):**
```
┌──────────────────────────────────────────────────────────────────────┐
│  Override costo medio ⓘ  [💱 FX]              [ Auto | Manuale ]     │
│                                                                       │
│  💡 PMC: 50.00  [€ 🇪🇺 EUR ▼]  (8 TX)        ▶ dettagli             │
└──────────────────────────────────────────────────────────────────────┘
```

**Utente cambia valuta (ricalcolo in volo):**
```
┌──────────────────────────────────────────────────────────────────────┐
│  Override costo medio ⓘ  [💱 FX]              [ Auto | Manuale ]     │
│                                                                       │
│  💡 PMC: …  [₩ 🇰🇷 KRW ▼] ⏳                 ▶ dettagli             │
└──────────────────────────────────────────────────────────────────────┘
```

**Risultato con override valuta:**
```
┌──────────────────────────────────────────────────────────────────────┐
│  Override costo medio ⓘ  [💱 FX]              [ Auto | Manuale ]     │
│                                                                       │
│  💡 PMC: 72,500  [₩ 🇰🇷 KRW ▼]  (8 TX)      ▶ dettagli             │
└──────────────────────────────────────────────────────────────────────┘
```

### Dropdown chip valuta (click su [€ EUR ▼])

```
┌─────────────────────┐
│  € 🇪🇺 EUR        ✓ │  ← attualmente selezionata
│  $ 🇺🇸 USD          │  ← vista nelle TX dell'asset
│  ₩ 🇰🇷 KRW          │
└─────────────────────┘
```

Le opzioni sono le **valute uniche trovate nelle transazioni dell'asset** (tutte le acquisizioni per quell'asset su tutti i broker). Il backend le può ritornare nel response oppure il frontend le deriva dai qualifying_txs.

### Regole UX chip

| Regola | Comportamento |
|--------|---------------|
| **Sfondo chip** | Sempre **opaco** (mai semi-trasparente), sia in Auto che con override |
| **Cambio valuta** | NON causa switch Auto→Manual. Resta in Auto con currency hint |
| **Switch Manual→Auto** | Il chip riappare con la valuta del risultato precedente (o 🏳️ se primo calcolo) |
| **Switch Auto→Manual** | Il chip scompare (la valuta è nell'input manual direttamente) |
| **Loading** | Chip mostra la valuta scelta + ⏳ spinner piccolo accanto |
| **Errore FX** | Chip resta sulla valuta scelta, errore nel banner (non nel chip) |

---

## Step 1 — Backend: `determine_target_currency` → "ultima acquisizione" ✅ 2026-06-03

> **Note implementazione**: Riscritta `determine_target_currency()` → usa `max(acquisitions, key=date)` per l'ultima acquisizione. Aggiunto `target_currency_override: str | None` a `compute_wac_iterative()`. In `transaction_service._compute_wac_for_auto_items` il hint viene estratto da `schema_item.cost_basis_override.code` e passato come override.

### File: `backend/app/utils/financial_utils.py`

Sostituire la logica "maggioranza con tiebreaker" con:

```python
def determine_target_currency(txs: list[WACInputTX], asset_currency: str) -> str:
    """Last acquisition currency (most recent date, qty > 0).
    Deterministic: no majority/tie logic.
    Fallback: asset_currency.
    """
    acquisitions = [tx for tx in txs if tx.quantity > 0]
    if not acquisitions:
        return asset_currency
    latest = max(acquisitions, key=lambda t: t.date)
    return latest.original_currency or asset_currency
```

### File: `backend/app/services/wac_service.py`

Aggiungere parametro `target_currency_override`:

```python
async def compute_wac_iterative(
    session: AsyncSession,
    broker_id: int,
    asset_id: int,
    as_of_date: date_type,
    asset_currency: str,
    excluded_tx_ids: list[int] | None = None,
    target_currency_override: str | None = None,  # NEW
) -> WACPreviewResultItem:
    ...
    # At line 106, replace:
    if target_currency_override:
        target_currency = target_currency_override
    else:
        target_currency = determine_target_currency(pre_txs, asset_currency)
```

### File: `backend/app/services/transaction_service.py`

Nel punto dove chiama `compute_wac_iterative`, estrarre il hint:

```python
# Extract currency hint from cost_basis_override when mode is auto
ccy_hint = None
if item.cost_basis_mode in ("auto", "auto-detail") and item.cost_basis_override:
    ccy_hint = item.cost_basis_override.code

wac_result = await compute_wac_iterative(
    ...,
    target_currency_override=ccy_hint,
)
```

---

## Step 2 — Backend: validazione schema (permettere override in auto) ✅ 2026-06-03

> **Note implementazione**: Verificato che nessun validator blocca `cost_basis_override` quando mode è auto. Il model_validator in `TXCreateItem` (Rule 12) controlla solo che `cost_basis_mode` sia usato su TRANSFER/ADJUSTMENT receiver. Nessuna modifica necessaria.

### File: `backend/app/schemas/transactions.py`

Attualmente c'è un validator che potrebbe rifiutare `cost_basis_override` quando `mode` è "auto"? Verificare e rimuovere il blocco se presente. La nuova semantica è:
- `mode: "auto" + override != null` → override.code è il currency hint, amount è ignorato

---

## Step 3 — Frontend: stato `wacCurrencyHint` nel FormModal ✅ 2026-06-03

> **Note implementazione**: Aggiunto `wacCurrencyHint = $state<string | null>(null)`. Viene popolato dalla prima risposta WAC (`formWacResult.wac.code`). `draftToTxFields()` ora costruisce `cost_basis_override: {code: hint, amount: '0'}` quando in auto con hint. Aggiunto `onWacCurrencyChange(code)` che setta l'hint e triggera validate. Il draft key include `wacCurrencyHint` per dedup corretta. Reset a null su apertura modal.

### File: `TransactionFormModal.svelte`

Aggiungere stato:
```typescript
let wacCurrencyHint = $state<string | null>(null); // null = backend decide
```

Quando il validate risponde con `wac.code`:
```typescript
if (!wacCurrencyHint) {
    wacCurrencyHint = response.wac?.code ?? null;
}
```

Quando l'utente cambia il chip:
```typescript
function onWacCurrencyChange(code: string) {
    wacCurrencyHint = code;
    // Ri-trigger validate (NON switch a manual)
    triggerValidate();
}
```

Nel payload validate/commit, costruire override:
```typescript
const costBasisPayload = draft.cost_basis_mode?.startsWith('auto')
    ? {
        cost_basis_mode: draft.cost_basis_mode,
        cost_basis_override: wacCurrencyHint
            ? { code: wacCurrencyHint, amount: '0' }
            : null,
    }
    : { /* manual: come prima */ };
```

---

## Step 4 — Frontend: chip valuta nella riga suggestion ✅ 2026-06-03

> **Note implementazione**: Creato `CurrencyChip.svelte` (self-contained, getCurrencyInfo per flag/symbol, dropdown con click-outside). Integrato in WacPreviewSection con nuove props: `wacCurrency`, `onCurrencyChange`, `availableCurrencies`. Chip appare dopo il button "qualifying txs" nella suggestion line. Tutte e 3 le istanze di WacPreviewSection nel FormModal aggiornate.

### File: `WacPreviewSection.svelte`

Aggiungere prop + chip:
```typescript
interface Props {
    // ...existing...
    wacCurrency: string | null;       // current WAC currency (from response or hint)
    onCurrencyChange: (code: string) => void;
    availableCurrencies: string[];    // currencies found in qualifying TXs
}
```

Chip rendering nella riga PMC suggestion:
```svelte
<!-- PMC suggestion line -->
<div class="flex items-center gap-1 ...">
    <span>💡 PMC suggerito: {formattedWac}</span>
    
    <!-- Currency chip — SEMPRE opaco -->
    <CurrencyChip
        value={wacCurrency}
        options={availableCurrencies}
        loading={wacLoading}
        onChange={onCurrencyChange}
    />
    
    <span>({qualifyingCount} TX)</span>
    <button>▶ dettagli</button>
</div>
```

### Nuovo componente: `CurrencyChip.svelte`

Micro-dropdown per selezionare valuta:
```typescript
interface Props {
    value: string | null;     // null = 🏳️
    options: string[];        // available currencies
    loading?: boolean;        // show spinner
    onChange: (code: string) => void;
}
```

Rendering:
- **Null**: `[🏳️ ▼]` (placeholder, primo calcolo non ancora tornato)
- **Con valore**: `[€ 🇪🇺 EUR ▼]` (sfondo opaco sempre)
- **Loading**: `[₩ 🇰🇷 KRW ▼] ⏳`
- Click → dropdown SimpleSelect inline con le opzioni

---

## Step 5 — Frontend: fix sfondo semi-trasparente ✅ 2026-06-03

> **Note implementazione**: Già soddisfatto by design: l'`opacity-60` è solo sul div contenente `CompactCashCell` (input amount+currency). Il chip è nella riga suggestion separata, e ha `class="opacity-100"` esplicito nel suo root. Il cambio valuta nel chip chiama `onWacCurrencyChange` che non tocca `costBasisMode`.

### Root cause attuale

Il campo `cost_basis_override` input ha `opacity-60` quando `mode === 'auto'` (per indicare "calcolato, non editabile"). Il chip valuta **non deve** avere questo stile.

### Fix

Separare il chip dalla zona opaca:
- L'input amount + currency selector: `opacity-60 italic` quando auto (come prima)
- Il **chip nella suggestion line**: sempre `opacity-100`, sfondo solido
- Il cambio valuta nel chip **non** triggera il passaggio a manual

---

## Step 6 — Frontend: BulkModal — currency hint per-riga ✅ 2026-06-03

> **Note implementazione**: Aggiunto `wacCurrencyHint?: string | null` a `PendingOp`. `opToTxFields()` ora costruisce `cost_basis_override: {code: hint, amount: '0'}` quando in auto mode con hint. Il FormModal passa `_wac_currency_hint` nel payload push. `patchRowFromForm`, `addRowFromForm`, `addDualRowFromForm` e `patchDualRowFromForm` estraggono il campo e lo persistono sull'op appropriato (receiver per dual).

### File: `TransactionBulkModal.svelte`

Ogni draft con cost_basis auto può avere un hint:
```typescript
// In PendingOp fields or extra state:
interface PendingOp {
    // ...existing...
    wacCurrencyHint?: string | null;  // persisted per-row
}
```

Nel payload validate batch, per ogni item:
```typescript
if (op.fields.cost_basis_mode?.startsWith('auto') && op.wacCurrencyHint) {
    item.cost_basis_override = { code: op.wacCurrencyHint, amount: '0' };
}
```

Il chip nella WacPreview della riga aggiorna `op.wacCurrencyHint` on change.

---

## Step 7 — `availableCurrencies`: da dove vengono? ✅ 2026-06-03

> **Note implementazione**: Usata opzione (A) — derivato da `externalWacResult.qualifying_txs` in FormModal (`wacAvailableCurrencies`). Sempre include asset currency come fallback. Aggiunto anche recovery del `wacCurrencyHint` dallo sentinel override (`amount=0`) quando il FormModal si apre da BulkModal (sia create che edit mode, sia solo che dual/transfer).

Due opzioni:

**(A) Dal response** — il backend ritorna le valute trovate nelle qualifying TXs. Il frontend le estrae:
```typescript
const availableCurrencies = $derived(
    [...new Set(qualifyingTxs.map(q => q.original_currency ?? q.currency))]
        .filter(Boolean)
);
```

**(B) Campo dedicato nel response** — il backend aggiunge `wac_available_currencies: ["EUR", "USD", "KRW"]` al `WACPreviewResultItem`.

**Scelta: (A)** — derivato dai qualifying, nessun campo aggiuntivo nel response.

Nota: alla prima chiamata (qualifying vuoto/non ancora tornato), il dropdown mostra solo la valuta asset come fallback.

---

## Step 8 — Test e walktest ✅ 2026-06-03

> **Note implementazione**: svelte-check: 0 errors, 0 warnings. Playwright tx-event-picker: 4/4 passed. Backend analytics-wac e transactions-wac: tutti passati. Files staged, commit message in `/tmp/libreFolio_commit_WacCurrency.txt`.

### Walktest manuali

| # | Scenario | Azione | Risultato atteso |
|---|----------|--------|------------------|
| **W1** | Default ultima acq | TRANSFER Apple +2 su IB, cost_basis Auto | PMC in EUR (ultime TX Apple su Directa sono in EUR). Chip: [€ EUR ▼] |
| **W2** | Override a USD | W1 + click chip → USD | PMC ricalcolato in USD. Frecce EUR→USD nella qualifying. Chip: [$ USD ▼] |
| **W3** | Missing pair | TRANSFER KRW Stock +5 su IB, Auto, chip → KRW | Errore banner "EUR/KRW mancante". Chip resta [₩ KRW ▼] |
| **W4** | Chip non cambia mode | In Auto, cambia chip valuta | Toggle resta su "Auto" (non switch a Manual) |
| **W5** | Chip opaco | Qualsiasi scenario Auto | Chip ha sfondo solido, non semi-trasparente |
| **W6** | Loading state | Cambia chip → durante ricalcolo | Chip mostra valuta scelta + ⏳ |
| **W7** | Commit preserva hint | W2 → Commit | DB: cost_basis_override=192.30, currency=USD |
| **W8** | Bulk per-riga | BulkModal, 2 TRANSFER diversi, ciascuno con valuta diversa | Ogni riga ha il suo chip indipendente |

---

## Ordine di Esecuzione

```
Step 1  (Backend: determine_target_currency + override param)   ← core logic
  ↓
Step 2  (Backend: schema validation — allow override in auto)
  ↓
Step 3  (Frontend: FormModal state + payload)
  ↓
Step 4  (Frontend: CurrencyChip + WacPreview integration)
  ↓
Step 5  (Frontend: fix opacità)
  ↓
Step 6  (Frontend: BulkModal per-riga hint)
  ↓
Step 7  (Frontend: availableCurrencies derivato)
  ↓
Step 8  (Walktest + E2E)
```

Tempo stimato: ~2h (backend 20min, frontend chip 40min, integration 30min, test 30min)

---

## 🔗 Cross-links

- **Parent (Round 2)**: [`plan-R3-SP-D-BugfixRound2.prompt.md`](./plan-R3-SP-D-BugfixRound2.prompt.md)
- **Grandparent (Round 1)**: [`plan-R3-SP-D-BugfixRound1.prompt.md`](./plan-R3-SP-D-BugfixRound1.prompt.md)
- **Phase 7 macro**: [`../phases/phase-07-transactions.md`](../phases/phase-07-transactions.md)

