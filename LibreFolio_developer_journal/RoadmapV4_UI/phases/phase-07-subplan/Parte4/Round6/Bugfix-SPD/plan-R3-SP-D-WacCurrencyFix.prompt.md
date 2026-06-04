# Plan: R3-SP-D-WacCurrencyFix — WAC Currency UX Polish

**Date**: 3 Giugno 2026
**Status**: ✅ DONE (2026-06-03)
**Priority**: P1
**Parent**: [`plan-R3-SP-D-WacCurrency.prompt.md`](./plan-R3-SP-D-WacCurrency.prompt.md)
**Origin**: Walktest manuale post-implementazione WacCurrency

---

## 🎯 Obiettivo

6 fix per allineare il comportamento del selettore WAC currency alla target situation concordata. Il campo cost_basis deve comportarsi come un input "smart": mostra il valore calcolato in Auto, diventa libero in Manual, e il cambio valuta non rompe il flusso.

---

## Target Situation (concordata)

### Stati del campo Cost Basis

**Auto + calcolato:** Campo mostra il WAC (es. "170.33"), valuta mostra la currency del risultato. Editabile ma qualsiasi modifica → switch Manual.

**Auto + in volo:** Campo vuoto con placeholder "auto", valuta mostra la scelta corrente. Messaggio "⏳ Calcolo in corso…"

**Auto + FX fallito:** Campo vuoto con placeholder "auto", valuta resta la scelta utente. Errore informativo sotto con elenco puntato pairs mancanti. NON forza Manual.

**Manual:** Campo editabile libero. Nessuna suggestion line. Nessuna qualifying table.

### Invarianti

| Regola | Comportamento |
|--------|---------------|
| Switch a Manual | SOLO se: (1) click toggle "Manuale", (2) **modifica effettiva** del numero |
| Click + blur senza modifica | Nessun effetto |
| Cambio valuta in Auto | Resta Auto. Triggera ricalcolo. |
| FX mancante | NON forza Manual. Errore informativo. |
| Warning "nessun costo base" | SOLO in Manual quando campo vuoto |
| Toggle Auto→Manual→Auto | Clear stale data, ri-validate immediato |
| HTML nei banner issues | Usa `{@html}` per currency flags |

---

## Gap e Fix

### G1 — Warning condition errata

**Problema**: Il warning "Nessun costo base impostato" (riga ~1926 FormModal) controlla `draft.cost_basis_override?.amount?.trim()` che è vuoto in Auto mode (il valore visualizzato viene da `displayedCostBasis`, non dal draft).

**Fix**: Mostrare il warning SOLO quando `costBasisMode === 'manual'` E il campo è vuoto.

```svelte
<!-- PRIMA -->
{#if Number(draft.quantity) > 0 && !draft.cost_basis_override?.amount?.trim()}

<!-- DOPO -->
{#if Number(draft.quantity) > 0 && costBasisMode !== 'auto' && !draft.cost_basis_override?.amount?.trim()}
```

**File**: `TransactionFormModal.svelte` (2 occorrenze: ADJUSTMENT inline + TRANSFER single)

---

### G2 — Switch Manual su blur senza modifica

**Problema**: `CompactCashCell` emette `emit()` on blur anche se il valore non è cambiato. `handleValueChange` in WacPreviewSection vede un "cambio" spurio e switcha a Manual.

**Fix**: In `handleValueChange`, confrontare il nuovo amount con il valore corrente. Se identico → no-op.

```typescript
function handleValueChange(next: {code: string; amount: string} | null) {
    if (!next) { onChange(next); return; }

    if (mode === 'auto') {
        // Currency changed → WAC currency override (stay auto)
        if (next.code !== value?.code) {
            onCurrencyChange?.(next.code);
            return;
        }
        // Amount changed EFFECTIVELY → switch to manual
        const currentAmount = value?.amount ?? '';
        if (next.amount === currentAmount) return; // blur senza modifica → no-op
        onModeChange?.('manual');
    }
    onChange(next);
}
```

**File**: `WacPreviewSection.svelte`

---

### G3 — `forcedManual` forza Manual su FX mancante

**Problema**: Quando `hasMissingPairs = true`, un `$effect` chiama `onModeChange('manual')`. L'utente perde il controllo e non può restare in Auto per sincronizzare FX.

**Fix**: Rimuovere l'`$effect` di `forcedManual`. Al suo posto, mostrare solo l'errore informativo (elenco puntato) nel WacPreview.

```svelte
// RIMUOVERE questo $effect:
$effect(() => {
    if (forcedManual && mode === 'auto') {
        onModeChange?.('manual');
    }
});
```

Il template già mostra il banner missing pairs. Basta non forzare il mode.

**File**: `WacPreviewSection.svelte`

---

### G4 — HTML literal nel banner issues

**Problema**: I messaggi di issue contengono HTML (`<span class="currency-symbol">`) ma il template li renderizza con testo normale, mostrando i tag come stringa.

**Fix**: Usare `{@html}` nel rendering delle issues nel FormModal.

```svelte
<!-- PRIMA -->
<li>{issue.message}</li>

<!-- DOPO -->
<li>{@html issue.message}</li>
```

**File**: `TransactionFormModal.svelte` — sezione banner issues (cercare `data-testid="tx-form-issue"`)

---

### G5 — Qualifying table non si resetta su Manual→Auto

**Problema**: Quando l'utente switcha Manual→Auto, la vecchia tabella qualifying resta visibile. Il campo mostra "auto" ma i dati sotto sono stale.

**Fix**: Nel `$effect` che monitora `mode`, clear `previewResult` quando torna ad Auto:

```svelte
$effect(() => {
    if (mode === 'auto' && previewResult) {
        // Clear stale data — will be repopulated by next validate
        previewResult = null;
    }
});
```

Oppure nel FormModal, quando `costBasisMode` torna a 'auto', clear `formWacResult`:

```typescript
// Già esistente:
$effect(() => {
    if (costBasisMode === 'manual') formWacResult = null;
});
// AGGIUNGERE:
$effect(() => {
    if (costBasisMode === 'auto') formWacResult = null; // force re-fetch
});
```

**File**: `TransactionFormModal.svelte`

---

### G6 — Cambio valuta: campo torna momentaneamente a USD

**Problema**: Quando l'utente sceglie EUR, il `displayedCostBasis` derived mostra ancora il vecchio WAC result (in USD) finché il nuovo validate non risponde. L'utente vede il valore USD lampeggiare prima di "auto".

**Fix**: Quando `wacCurrencyHint` cambia, clear `formWacResult` (così `displayedCostBasis` cade nel branch `{code: hint, amount: ''}` = placeholder "auto").

In `onWacCurrencyChange`:
```typescript
function onWacCurrencyChange(code: string) {
    wacCurrencyHint = code;
    formWacResult = null; // ← clear stale result to show placeholder
    scheduler.trigger('change');
}
```

**File**: `TransactionFormModal.svelte`

---

### Stato 8 — Elenco puntato per FX missing pairs

**Problema**: Quando FX fallisce, il WacPreview mostra un singolo messaggio. Deve mostrare elenco puntato con tutte le pairs mancanti (come da design Round 1 Step 10).

**Fix**: Già implementato nel template (`data-testid="tx-form-cost-basis-missing-pairs"` con `<ul><li>` per ogni pair). Verificare che funzioni correttamente dopo la rimozione di `forcedManual`. Se la sezione è nascosta da un `{#if !hasMissingPairs}` gate, rimuovere quel gate per il blocco errore.

**File**: `WacPreviewSection.svelte` — verificare visibilità del blocco missing pairs in Auto mode

---

## Ordine di Esecuzione

```
✅ G1  (Warning condition)              ← 2026-06-03
  ↓
✅ G3  (Rimuovere forcedManual)         ← 2026-06-03
  ↓
✅ G2  (Blur senza modifica)            ← 2026-06-03
  ↓
✅ G6  (Clear stale su cambio valuta)   ← 2026-06-03
  ↓
✅ G5  (Clear su Manual→Auto)           ← 2026-06-03
  ↓
✅ G4  (HTML nei banner issues)         ← 2026-06-03
  ↓
✅ Stato 8 verify (elenco puntato)      ← 2026-06-03
```

> **Note implementazione**: Tutti i 6 gap fix applicati con edit mirati. G1: aggiunto `costBasisMode !== 'auto'` alla condizione warning. G3: rimosso `$effect` forcedManual e reso `forcedManual = false` costante. G2: aggiunto confronto `next.amount === currentAmount` → no-op su blur senza modifica. G6: aggiunto `formWacResult = null` in `onWacCurrencyChange`. G5: consolidato gli effect in un unico `$effect` che traccia `costBasisMode` e resetta `formWacResult`. G4: tutte le `<li>` con issue messages ora usano `{@html}`. Stato 8: verificato che il banner missing pairs è già visibile in Auto mode (nessuna modifica necessaria post-G3).

Tempo effettivo: ~15 min

---

## Walktest post-fix

| # | Scenario | Risultato atteso |
|---|----------|------------------|
| **W1** | ADJUSTMENT Apple +5, Auto, attendi risposta | PMC 170.33 USD nel campo. NO warning. |
| **W2** | W1 + click campo + blur senza scrivere | Resta Auto, nessun switch |
| **W3** | W1 + scrivi "200" nel campo | Switch a Manual, suggestion sparisce |
| **W4** | W3 + toggle Manual→Auto | Campo "auto", tabella sparisce, ricalcolo parte |
| **W5** | W1 + cambia valuta a EUR | Campo "auto", messaggio "ricalcolo", resta Auto |
| **W6** | W5 + FX disponibile | Valore EUR nel campo + frecce in qualifying |
| **W7** | W5 + FX non disponibile | Campo "auto" + elenco puntato pairs mancanti + banner Sync FX in alto |
| **W8** | W7 + l'utente NON è forzato a Manual | Toggle resta su Auto |
| **W9** | TRANSFER paired, Auto, stesso flusso W1-W8 | Identico comportamento |

---

## 🔗 Cross-links

- **Parent**: [`plan-R3-SP-D-WacCurrency.prompt.md`](./plan-R3-SP-D-WacCurrency.prompt.md)
- **Grandparent (Round 2)**: [`plan-R3-SP-D-BugfixRound2.prompt.md`](./plan-R3-SP-D-BugfixRound2.prompt.md)
- **Child**: [`plan-R3-SP-D-WacFxEnrich.prompt.md`](./plan-R3-SP-D-WacFxEnrich.prompt.md) — WAC FX missing pairs UX + backend date enrichment
- **Phase 7 macro**: [`../phases/phase-07-transactions.md`](../phases/phase-07-transactions.md)

