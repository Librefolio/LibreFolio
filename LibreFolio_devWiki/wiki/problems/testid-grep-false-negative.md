---
title: "Grepping for a testid can return zero when the testid exists"
category: problem
date: 2026-09-18
tags: [frontend, testing, e2e, selectors, ui-primitives]
---

# Grepping for a testid can return zero when the testid exists

## Summary

Several UI primitives build their child test ids by **suffixing** a `testId` prop at
runtime — `SimpleSelect` emits `${testId}-button`, `SearchSelect` emits `${testId}-trigger`,
`-dropdown`, `-search`. A literal `grep -c "risk-broker-filter-button"` over the source
therefore returns `0` even though the attribute is present in the DOM on every render.
Concluding "that selector is gone" from such a grep produces a false report. Verify a
missing selector by **running** the spec, or by grepping the primitive for its suffix
composition — never by searching the assembled string in the consuming component.

## Details

The composition happens inside the primitive, so the full string never appears anywhere:

```svelte
<!-- ui/select/SimpleSelect.svelte -->
<button data-testid={testId ? `${testId}-button` : undefined}>

<!-- ui/select/SearchSelect.svelte -->
<button data-testid={testId ? `${testId}-trigger` : undefined}>
```

A consumer passes only the stem — `testId="risk-broker-filter"` — and the E2E spec uses
the assembled `risk-broker-filter-button`. Three files, one string, never written down.

### The inverse error is worse

The same mechanism hides a real gap. `AssetSelect` wraps `SearchSelect` in its own
`<div data-testid={testid}>` but **does not forward `testId` to the inner `SearchSelect`**.
So for an `AssetSelect`, the stem resolves but `${stem}-trigger` genuinely does not exist —
the opposite conclusion from the same kind of grep.

And the obvious repair is itself a trap: forwarding `testId` makes `SearchSelect` render
`<div data-testid={testId}>` too, which **duplicates** the id already on the `AssetSelect`
wrapper. Two nodes with one test id is a Playwright strict-mode violation, and four import
wizard specs resolve `[data-testid="asset-select"] input[type="text"]` against that
wrapper. A correct fix forwards the prop **and** drops the wrapper's own id, then
re-verifies those four specs.

**Rule of thumb**: a test id you did not find is a hypothesis. A test run is the fact.

## Source files

| Role | Path |
|------|------|
| Suffix composition | `frontend/src/lib/components/ui/select/SimpleSelect.svelte` |
| Suffix composition | `frontend/src/lib/components/ui/select/SearchSelect.svelte` |
| Non-forwarding wrapper | `frontend/src/lib/components/ui/select/AssetSelect.svelte` |
| Consumer passing the stem | `frontend/src/lib/components/risk/AssetSetRiskPanel.svelte` |
| Specs bound to the wrapper id | `frontend/e2e/transactions/tx-import-resolution.spec.ts` |

Related: [[problems/front-check-does-not-check-what-you-think]]
