---
title: "Blur detection: compare formatDecimalForDisplay() strings (not numeric tolerance)"
category: decision
status: resolved
date: 2026-06-04
tags: [frontend, transactions, wac, ux, precision, svelte5]
related_features: [F-097]
related_problems:
  - problems/wac-feedback-loop
---

# Blur Detection via formatDecimalForDisplay() String Comparison

## Context

The WAC auto field shows a computed value (e.g. "170.33") but the backend returns full precision (e.g. "170.3261122757978..."). When the user clicks the field and blurs without changing anything, the CompactCashCell emits the full-precision value. The naive comparison (`next !== current`) triggers a spurious switch to Manual mode.

## Decision

**Compare `formatDecimalForDisplay(currentRaw)` with `formatDecimalForDisplay(nextRaw)`.** If the displayed representations are identical, treat as no-change (no-op on blur).

```typescript
function handleValueChange(next: {code: string; amount: string} | null) {
    if (mode === 'auto') {
        if (next.code !== value?.code) { onCurrencyChange?.(next.code); return; }
        const currentDisplay = formatDecimalForDisplay(value?.amount ?? '');
        const nextDisplay = formatDecimalForDisplay(next.amount);
        if (currentDisplay === nextDisplay) return; // blur without visual change → no-op
        onModeChange?.('manual');
    }
    onChange(next);
}
```

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| Numeric tolerance (abs diff < 0.01) | Arbitrary threshold, locale-dependent |
| Raw string equality | Fails because backend sends 17 decimals, display shows 8 |
| Track "user actually typed" flag | Complex, fragile with paste/autofill |

## Consequences

- Zero false positives: if user sees "170.33" and blurs, it stays auto
- Any actual edit (even last decimal) correctly triggers manual switch
- `formatDecimalForDisplay()` is the single source of truth for "what the user sees"

## Source files

| Role | Path |
|------|------|
| WacPreviewSection (handleValueChange) | `frontend/src/lib/components/transactions/WacPreviewSection.svelte` |
| formatDecimalForDisplay | `frontend/src/lib/utils/formatters.ts` |
| Plan | `…/Bugfix-SPD/plan-R3-SP-D-WacFxEnrich.prompt.md` (F10) |

