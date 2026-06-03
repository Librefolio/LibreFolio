# Plan: R3-SP-D Bugfix Round 2 — Event Picker Polish + Currency Format + UX

**Date**: 3 Giugno 2026
**Status**: ✅ DONE (2026-06-03)
**Priority**: P2
**Parent**: [`plan-R3-SP-D-BugfixRound1.prompt.md`](./plan-R3-SP-D-BugfixRound1.prompt.md)
**Origin**: Walktest manuale Round 1

---

## 🎯 Obiettivo

7 fix emersi dal walktest del Round 1: traduzioni mancanti, delta nell'event picker, slider integrato nel dropdown, hint DIVIDEND, formattazione valuta, balance issue globale.

---

## Bug List

| # | Area | Bug | Gravità |
|---|------|-----|---------|
| **R1** | i18n | Chiavi `eventPickerNone` + `eventPickerPlaceholder` mancanti (4 lingue) | Media |
| **R2** | EventPicker | Delta: (a) manca nel selectedItem compatto (b) non appare se valute diverse | Media |
| **R3** | EventPicker | Slider fuori dal dropdown → creare `AssetEventPicker` con slider integrato | Media |
| **R4** | FormModal | Hint "deve essere 0" visibile quando qty è nascosta — nasconderlo + riformulare label cash | Bassa |
| **R5** | AssetSelect | Valuta plain `USD` → formattare con symbol + flag emoji | Bassa |
| **R6** | BulkModal | Event cell valuta plain `0.25 USD` → formattare | Bassa |
| **R7** | BulkModal | Balance issue `index=-1` → label "?" inutile → "🏦 Broker Name" | Bassa |

---

## Decisioni di Design

| Decisione | Scelta | Rationale |
|---|---|---|
| R2a — Delta valute diverse | **(B) Mostrare con indicatore "≠ valuta"** | L'importo non è comparabile 1:1 ma il delta grezzo aiuta comunque. Suffisso `≠` grigio. |
| R3 — Slider | **(A) Nuovo componente `AssetEventPicker`** con slider come header interno al dropdown | Il SimpleSelect non supporta header slot nativamente. Meglio un componente dedicato. |
| R4 — Hint qty nascosta | **Nascondere SEMPRE** `hintSignZero` quando `quantityMode === 'forbidden'`. Label cash: `"Importo {tipo}" + hint "(totale)"` | Il cash è SEMPRE importo totale (confermato: DIVIDEND, INTEREST, DEPOSIT, WITHDRAWAL, FEE, TAX, FX_CONVERSION, CASH_TRANSFER tutti usano il totale). |
| R7 — Balance globale | **(A) "🏦 {broker_name}"** + messaggio formattato | Usare `brokerId` dai params per risolvere il nome broker. |

---

## Step 1 — R1: Aggiungere chiavi i18n mancanti ✅ (2026-06-03)

> **Note implementazione**: Aggiunte `eventPickerNone` e `cashLabelTotal` in tutte e 4 le lingue (EN/IT/FR/ES). La chiave `eventPickerPlaceholder` esisteva già.

### Chiavi da aggiungere in `transactions.form`:

| Key | EN | IT | FR | ES |
|-----|----|----|----|----|
| `eventPickerNone` | No linked event | Nessun evento collegato | Aucun événement lié | Sin evento vinculado |
| `eventPickerPlaceholder` | Select event… | Seleziona evento… | Sélectionner événement… | Seleccionar evento… |
| `cashLabelTotal` | Total amount | Importo totale | Montant total | Importe total |

### File: `frontend/src/lib/i18n/{en,it,fr,es}.json`

---

## Step 2 — R4: Nascondere hint "deve essere 0" + label cash ✅ (2026-06-03)

> **Note implementazione**: Rimosso il `<span data-testid="tx-form-quantity-locked">` con `hintSignZero` dal branch "only cash" (quantityMode=forbidden). Aggiunto hint `💡 cashLabelTotal` sotto il campo CompactCashCell. Il testo è "Total amount (not per share)" / equivalenti nelle 4 lingue.

### Root cause

```svelte
<!-- TransactionFormModal.svelte:1800-1806 — "only cash" branch -->
<span class="text-xs ...">
    Importo * (+)
    <span ... data-testid="tx-form-quantity-locked">· {$t('transactions.form.hintSignZero')}</span>
</span>
```

Il messaggio "deve essere 0" si riferisce alla **quantity nascosta** ma è renderizzato accanto al label "Importo" → confuso per l'utente.

### Fix

1. **Rimuovere** il `<span data-testid="tx-form-quantity-locked">` dal branch "only cash" (righe 1800-1806)
2. **Riformulare label**: da `Importo *` a `Importo {tipo} *` dove tipo è tradotto (es. "Importo dividendo *")
3. **Aggiungere hint sotto** il campo: `💡 {$t('transactions.form.cashLabelTotal')}` (piccolo, grigio, italic)

### Design DOPO:

```
┌──────────────────────────────────────────────────────────────────────┐
│  Importo dividendo * (+)                                              │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  7.00                                              $ 🇺🇸 USD ▼ │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  💡 Importo totale (non per singola azione)                           │
└──────────────────────────────────────────────────────────────────────┘
```

### File: `TransactionFormModal.svelte` + i18n

---

## Step 3 — R2: Delta nel selectedItem + valute diverse ✅ (2026-06-03)

> **Note implementazione**: Riscritta `computeDelta()` per restituire `DeltaResult | null` con `label`, `color`, `crossCurrency`. Rimossa la condizione `txCash.code !== eventCode` che bloccava il delta cross-currency: ora mostra `Δ+X.XX ≠` in grigio. Aggiunto delta nel snippet `selectedItem` (compatto post-selezione).

### Fix (a) — Delta nel compatto

Aggiungere delta anche nel snippet `selectedItem` (riga 205-220 di AssetEventSelect):

```svelte
{#snippet selectedItem(option)}
    {@const d = option.data as any}
    {#if option.value === NONE_VALUE}
        <span class="text-xs text-gray-400 italic">{$t('transactions.form.eventPickerNone')}</span>
    {:else if d}
        {@const delta = computeDelta(d.amount, d.code)}
        <div class="flex items-center gap-1.5 min-w-0">
            <span class="shrink-0 w-5 h-5 ... ">{d.icon}</span>
            <span class="truncate text-xs">{shortDate(d.date)}</span>
            {#if d.notes}
                <span class="text-[10px] text-gray-400 truncate">· {d.notes}</span>
            {/if}
            <!-- Delta compatto -->
            {#if delta != null}
                <span class="text-[10px] font-mono {delta.color} shrink-0">
                    Δ{delta.label}
                </span>
            {/if}
        </div>
    {/if}
{/snippet}
```

### Fix (b) — Delta con valute diverse

Modificare `computeDelta()` per restituire un oggetto richer:

```typescript
interface DeltaResult {
    value: number;
    label: string;      // "+0.01" o "+0.01 ≠"
    color: string;      // tailwind class
    crossCurrency: boolean;
}

function computeDelta(eventAmount: string, eventCode: string): DeltaResult | null {
    if (!txCash?.amount) return null;
    const txAmt = parseFloat(txCash.amount);
    const evtAmt = parseFloat(eventAmount);
    if (isNaN(txAmt) || isNaN(evtAmt) || txAmt === 0) return null;
    
    const diff = txAmt - evtAmt;
    const crossCurrency = txCash.code !== eventCode;
    const close = Math.abs(diff) < 0.05;
    
    return {
        value: diff,
        label: `${diff >= 0 ? '+' : ''}${diff.toFixed(2)}${crossCurrency ? ' ≠' : ''}`,
        color: crossCurrency ? 'text-gray-400' : (close ? 'text-green-600 dark:text-green-400' : 'text-amber-500'),
        crossCurrency,
    };
}
```

**Rendering nel dropdown:**
```
┌──────────────────────────────────────────────────────────────────────┐
│  [💰] 31 mag 2026 · Recent dividend    0.25 $ 🇺🇸 USD   Δ+0.01      │  ← stessa valuta: verde
│  [💰] 28 mag 2026 · Q4 dividend        0.22 $ 🇺🇸 USD   Δ+0.03      │  ← stessa: amber
│  [💰] 15 mag 2026 · Special div        5.00 € 🇪🇺 EUR   Δ+2.00 ≠    │  ← cross: grigio + ≠
│  [ ∅ ] Nessun evento collegato                                        │
└──────────────────────────────────────────────────────────────────────┘
```

**Nel compatto (post-selezione):**
```
┌──────────────────────────────────────────────────────────────────────┐
│  [💰] 31 mag 2026 · Recent dividend   Δ+0.01              ▼          │
└──────────────────────────────────────────────────────────────────────┘
```

### File: `AssetEventSelect.svelte`

---

## Step 4 — R3: Nuovo componente `AssetEventPicker` ✅ (2026-06-03)

> **Note implementazione**: Creato `AssetEventPicker.svelte` — componente self-contained con dropdown fixed (no SimpleSelect), slider integrato nel header del dropdown, card-style items con emoji+delta, keyboard nav, click-outside. Importato in TransactionFormModal al posto di AssetEventSelect. Eliminato `AssetEventSelect.svelte`. Aggiornati E2E test per aprire il dropdown prima di verificare il slider. 4/4 test passano.

### Architettura

`AssetEventPicker` = componente wrapper che NON usa SimpleSelect ma gestisce il dropdown custom con:
- **Trigger button** (come SimpleSelect, stessa estetica)
- **Dropdown panel** (fixed position, come SimpleSelect) con:
  - **Header**: slider range ± Ngg
  - **Body**: lista eventi (card-style, riutilizza rendering attuale)

Il componente sostituisce `AssetEventSelect` (che attualmente wrappa SimpleSelect + slider esterno).

### Design

**Chiuso (trigger button):**
```
┌──────────────────────────────────────────────────────────────────────┐
│  [💰] 31 mag 2026 · Recent dividend   Δ+0.01              ▼          │
└──────────────────────────────────────────────────────────────────────┘
```

**Aperto (dropdown con header slider):**
```
┌──────────────────────────────────────────────────────────────────────┐
│  [💰] 31 mag 2026 · Recent dividend   Δ+0.01              ▲          │
├══════════════════════════════════════════════════════════════════════╡
│  🔍 ± 7 giorni  ═══════●══════════════════════════════  30          │
├──────────────────────────────────────────────────────────────────────┤
│  [ ∅ ] Nessun evento collegato                                        │
├──────────────────────────────────────────────────────────────────────┤
│  [💰] 31 mag 2026 · Recent dividend    0.25 $ 🇺🇸 USD   Δ+0.01  ✓   │
├──────────────────────────────────────────────────────────────────────┤
│  [💰] 28 mag 2026 · Q4 dividend        0.22 $ 🇺🇸 USD   Δ+0.03      │
├──────────────────────────────────────────────────────────────────────┤
│  [✂️]  1 gen 2026 · 2:1 stock split     —                             │
└──────────────────────────────────────────────────────────────────────┘
```

**Senza eventi nel range:**
```
┌──────────────────────────────────────────────────────────────────────┐
│  [ ∅ ] Seleziona evento…                                   ▼          │
├══════════════════════════════════════════════════════════════════════╡
│  🔍 ± 3 giorni  ══●════════════════════════════════════  30          │
├──────────────────────────────────────────────────────────────────────┤
│  [ ∅ ] Nessun evento collegato                              ✓         │
├──────────────────────────────────────────────────────────────────────┤
│       😶 Nessun evento trovato in questo range                        │
│       Prova ad allargare il range ↑                                   │
└──────────────────────────────────────────────────────────────────────┘
```

**Loading:**
```
┌──────────────────────────────────────────────────────────────────────┐
│  🔍 ± 12 giorni ═══════════════●═══════════════════════  30          │
├──────────────────────────────────────────────────────────────────────┤
│       ⏳ Ricerca eventi…                                              │
└──────────────────────────────────────────────────────────────────────┘
```

### Struttura componente

```text
frontend/src/lib/components/transactions/AssetEventPicker.svelte
```

**Props** (stesse di AssetEventSelect + nessun cambio esterno):
```typescript
interface Props {
    assetId: number;
    txDate: string;
    value: number | null;
    disabled?: boolean;
    onChange: (eventId: number | null) => void;
    txCash?: {amount: string; code: string} | null;
}
```

**Struttura interna:**
1. Stato: `isOpen`, `daysRange`, `events[]`, `loading`, `highlightedIndex`
2. **Trigger**: button identico a SimpleSelect compact (stesso stile)
3. **Dropdown**: `position:fixed` (stesso pattern di SimpleSelect per evitare overflow clip)
4. **Header**: slider con `± {N}d` label + range input
5. **Items**: lista scrollabile con card-style (riuso del rendering attuale)
6. **Keyboard**: ↑↓ per navigare, Enter per selezionare, Escape per chiudere
7. **Click outside**: chiudi dropdown

### Implementazione

- **Riutilizzare** tutta la logica fetch/state/delta da `AssetEventSelect.svelte` (copiarla dentro)
- **Riutilizzare** il positioning logic da SimpleSelect (getBoundingClientRect + fixed)
- **NON usare** SimpleSelect — il componente è self-contained
- Dopo la creazione, `AssetEventSelect.svelte` diventa deprecato (ma non eliminato subito per non rompere)

### Migrazione

1. Creare `AssetEventPicker.svelte`
2. In `TransactionFormModal.svelte`: sostituire `<AssetEventSelect>` con `<AssetEventPicker>`
3. Verificare funzionamento
4. Eliminare `AssetEventSelect.svelte`

### File:
- `frontend/src/lib/components/transactions/AssetEventPicker.svelte` (NUOVO)
- `TransactionFormModal.svelte` (import swap)
- Eliminare `AssetEventSelect.svelte`

---

## Step 5 — R5: AssetSelect valuta formattata ✅ (2026-06-03)

> **Note implementazione**: Importato `getCurrencyInfo` dal currencyStore. Nel `selectedItem` snippet: valuta formattata come `· {symbol} {flag} {code}`. Nel dropdown `item` snippet: sostituito plain uppercase con inline-flex `{symbol} {flag} {code}`. Usa classe `emoji-flag` per Noto font.

### Root cause

```svelte
<!-- AssetSelect.svelte:106 -->
<div class="text-xs text-gray-500 truncate">{option.label}{a?.currency ? ` · ${a.currency}` : ''}</div>
<!-- AssetSelect.svelte:118 -->
<span class="ml-auto text-[10px] font-mono uppercase opacity-60 shrink-0">{a.currency}</span>
```

### Fix

Usare la funzione `getCurrencyInfo()` per ottenere symbol + flag emoji:

```typescript
import {getCurrencyInfo} from '$lib/utils/currencyFormat';
```

**SelectedItem (riga 106):**
```svelte
{#if a?.currency}
    {@const ci = getCurrencyInfo(a.currency)}
    · <span class="inline-flex items-center gap-0.5">
        {#if ci.symbol && ci.symbol !== a.currency}<span>{ci.symbol}</span>{/if}
        {#if ci.flag_emoji}<span class="emoji-flag">{ci.flag_emoji}</span>{/if}
        <span>{a.currency}</span>
    </span>
{/if}
```

**Dropdown item (riga 118):**
```svelte
{#if a?.currency}
    {@const ci = getCurrencyInfo(a.currency)}
    <span class="ml-auto text-[10px] font-mono opacity-60 shrink-0 inline-flex items-center gap-0.5">
        {#if ci.symbol && ci.symbol !== a.currency}{ci.symbol}{/if}
        {#if ci.flag_emoji}<span class="emoji-flag">{ci.flag_emoji}</span>{/if}
        {a.currency}
    </span>
{/if}
```

### Design DOPO:

**Selected:**
```
┌──────────────────────────────────────────────────────────────────────┐
│  [🍎]  AAPL                                                          │
│        Apple Inc. · $ 🇺🇸 USD                                         │
└──────────────────────────────────────────────────────────────────────┘
```

**Dropdown:**
```
┌──────────────────────────────────────────────────────────────────────┐
│  🍎  AAPL · Apple Inc.                                 $ 🇺🇸 USD     │
│  📊  VWCE · Vanguard FTSE All-World UCITS ETF          € 🇪🇺 EUR     │
│  🪙  BTC · Bitcoin                                     ₿ 🌐 BTC      │
│  🏢  Test KRW Stock                                    ₩ 🇰🇷 KRW     │
└──────────────────────────────────────────────────────────────────────┘
```

### File: `AssetSelect.svelte`

---

## Step 6 — R6: BulkModal event cell valuta formattata ✅ (2026-06-03)

> **Note implementazione**: Importato `getCurrencyInfo` dal currencyStore. Nel cell renderer dell'eventCache: valuta formattata come `{amount} {symbol} {flag} {code}`. Skip se flag è default `🏳️`.

### Root cause (nel cell renderer dell'eventCache):

```html
<span class="font-mono text-gray-500">0.25 USD</span>
```

### Fix

Usare `getCurrencyInfo()` per aggiungere symbol + flag:

```html
<span class="font-mono text-gray-500">0.25 $ 🇺🇸 USD</span>
```

La formattazione viene fatta nel renderer `buildEventCellHtml()` con:
```typescript
const ci = getCurrencyInfo(evt.code);
const sym = ci.symbol && ci.symbol !== evt.code ? `${ci.symbol} ` : '';
const flag = ci.flag_emoji && ci.flag_emoji !== '🏳️' ? `<span class="emoji-flag">${ci.flag_emoji}</span> ` : '';
html = `...${sym}${flag}${evt.code}`;
```

### File: `TransactionBulkModal.svelte`

---

## Step 7 — R7: Balance issue globale → "🏦 Broker Name" ✅ (2026-06-03)

> **Note implementazione**: `getVisualRowLabel()`: per `index < 0`, lookup `brokerId` da `issue.params`, resolve nome broker dall'array `brokers`, format `🏦 {name}`. Banner: per `index < 0` non usa prefisso "Riga N:", mostra direttamente il label. Balance issues senza row: stessa logica con `getVisualRowLabel()` prefix. `jumpToIssue` già aveva early return per `index < 0`.

### Root cause

```typescript
// getVisualRowLabel(issue) — riga 1893:
if (issue.index < 0) return '?';
```

### Fix

Per `index === -1` (balance issue), usare i `params` dell'issue per costruire un label utile:

```typescript
function getVisualRowLabel(issue: ValidationIssue): string {
    if (issue.index < 0) {
        // Balance issue: global, use broker name from params
        if (issue.params?.brokerId) {
            const broker = brokers.find(b => b.id === issue.params.brokerId);
            return broker ? `🏦 ${broker.name}` : `🏦 #${issue.params.brokerId}`;
        }
        return '⚠️';  // generic global
    }
    // ...existing Na/Nb logic...
}
```

Nel banner, il prefisso "Riga" non ha senso per un errore globale:
```typescript
// Nella renderizzazione del banner:
{#if issue.index >= 0}
    {$t('transactions.bulk.rowN', {values: {n: getVisualRowLabel(issue)}})}:
{:else}
    {getVisualRowLabel(issue)}:
{/if}
```

### Design DOPO:

```
┌──────────────────────────────────────────────────────────────────────┐
│ ⚠️ Problemi di validazione                                           │
│                                                                       │
│  • 🏦 Degiro: ❌ Il saldo di Apple Inc. diventa negativo (-6)        │
│    al 12 giu 2020                                                     │
│  • Riga 1a: ⚠️ ...                                                   │
└──────────────────────────────────────────────────────────────────────┘
```

Anche `jumpToIssue` per `index=-1` non deve fare nulla (non c'è una riga da scrollare):

```typescript
function jumpToIssue(issue: ValidationIssue) {
    if (issue.index < 0) return;  // global issue — no row to navigate
    // ...existing logic...
}
```

### File: `TransactionBulkModal.svelte`

---

## Ordine di Esecuzione

```
Step 1  (R1 — i18n keys)              ← 2 min
  ↓
Step 2  (R4 — hide qty hint)          ← 5 min
  ↓
Step 3  (R2 — delta selectedItem)     ← 10 min
  ↓
Step 4  (R3 — AssetEventPicker)       ← 30 min (nuovo componente)
  ↓
Step 5  (R5 — AssetSelect currency)   ← 10 min
  ↓
Step 6  (R6 — event cell currency)    ← 5 min
  ↓
Step 7  (R7 — balance issue label)    ← 10 min
```

---

## Post-completion Polish (2026-06-03)

Miglioramenti applicati dopo il walktest del Round 2:

### P1 — Event cell: Tooltip Svelte + larghezza colonna
- Sostituito native `title` attr con `Tooltip.svelte` via `HtmlCell.tooltip.html` (esteso il tipo in `table/types.ts`)
- DataTable ora supporta `tooltip: { html: string }` per celle HTML (rich tooltip)
- Larghezza colonna event: 110 → 160px
- Tooltip mostra: tipo (bold+emoji), data completa, importo 4 decimali, note

### P2 — Event cell: i18n tooltip
- Traduzione tipo: `$t('assetDetail.eventType.{TYPE}')` (era hardcoded EN)
- Aggiunte chiavi `transactions.bulk.eventTooltipAmount` e `eventTooltipNotes` in 4 lingue
- Colonna `asset_event_id` spostata prima di `description` (allineamento con ordine FormModal)

### P3 — Balance issue: backend batch_index
- `BalanceValidationError` ora porta `batch_index` e `batch_operation`
- `_validate_broker_balances` accetta `batch_tx_ids: dict[int, tuple]` (tx.id → (op, idx))
- Traccia l'ultima batch TX che ha ridotto il bilancio nel giorno della violazione
- Frontend: filtra balance issues per `code` (non più per `index < 0`)
- Rimossa `findRowForBalanceIssue()` — ora il backend fornisce direttamente l'indice corretto
- Balance issues con `index >= 0` sono cliccabili → navigano alla riga colpevole
- Fallback `🏦 Broker Name` solo quando `index = -1` (causa esterna al batch)

---

## 🔗 Cross-links

- **Parent plan (Round 1)**: [`plan-R3-SP-D-BugfixRound1.prompt.md`](./plan-R3-SP-D-BugfixRound1.prompt.md)
- **Child (WAC Currency)**: [`plan-R3-SP-D-WacCurrency.prompt.md`](./plan-R3-SP-D-WacCurrency.prompt.md)
- **Grandparent**: [`../plan-R3-SP-D-FormModalEventPickerWacFx.prompt.md`](../plan-R3-SP-D-FormModalEventPickerWacFx.prompt.md)
- **Phase 7 macro**: [`../phases/phase-07-transactions.md`](../phases/phase-07-transactions.md)

