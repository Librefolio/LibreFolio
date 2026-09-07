---
title: "CompactCashCell feedback loop erased the decimal separator mid-typing (T1)"
category: problem
status: resolved
date: 2026-09-02
tags: [frontend, transactions, decimal, svelte5, ux, beta-feedback]
related:
  - decisions/blur-detection-format-string-comparison
---

# CompactCashCell feedback loop erased the decimal separator mid-typing

## Summary

Typing `12,` in a cash amount field was rewritten to `12` on the same keystroke:
the child's `emit()` normalized and pushed the value up, the parent stored a NEW
object, the prop came back down, and the sync-down `$effect` compared
**display strings** (`formatDecimalForDisplay("12.") = "12"` ≠ `"12,"`), so it
"helpfully" overwrote the buffer being typed into. Caught live on the prod test
server and reproduced in jsdom with a parent-loop harness.

## Details

- Root cause shape: controlled-component feedback loop. The child's own emission
  returns indistinguishable from an external change.
- Fix (strategy A): in the sync effect compare **normalized numbers**
  (`Number(normalizeDecimalInput(x))`, both sides non-empty, finite). If equal,
  the incoming value is our own echo — do not touch the buffer. Genuinely
  different external values (FX sync, external clear) still sync down.
- Same family: the quantity field in `TransactionFormModal` started pre-filled
  with `"0"`, forcing arrow-key gymnastics to type decimals → default is now `''`
  (validation already rejects empty/zero).
- Related decision (different layer, blur-time no-op detection):
  [[decisions/blur-detection-format-string-comparison]].
- Regression coverage: `frontend/src/lib/components/ui/display/CompactCashCell.test.ts`
  (parent-loop via `rerender`, char-by-char `12,5` survives; external update still syncs).

> Trap for test authors: `locator.isVisible({timeout})` does NOT wait — it answers
> for the current instant. A probe written as
> `await tooltip.isVisible({timeout: 2000}).catch(() => false)` silently became
> always-false the day `Tooltip` gained a 500ms hover-open delay (T2). Use
> `waitFor({state: 'visible', timeout})` / retrying `expect` for time-dependent UI.

## Source files

| Role | Path |
|------|------|
| Fix (sync effect) | `frontend/src/lib/components/ui/display/CompactCashCell.svelte` |
| Quantity default | `frontend/src/lib/components/transactions/modals/TransactionFormModal.svelte` |
| Normalizer | `frontend/src/lib/utils/core/parseDecimalInput.ts` |
| Component test | `frontend/src/lib/components/ui/display/CompactCashCell.test.ts` |
