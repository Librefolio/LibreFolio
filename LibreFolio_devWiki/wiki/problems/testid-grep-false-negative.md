---
title: "Grepping for a testid can return zero when the testid exists"
category: problem
status: recurs
date: 2026-09-18
updated: 2026-09-23
tags: [frontend, testing, e2e, selectors, ui-primitives, method]
related:
  - problems/front-check-does-not-check-what-you-think
  - concepts/span-as-a-detector
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

## Recurrence — 2026-09-23 (workstream F, `risk-lab.spec.ts`)

F's first static probe of `risk-lab.spec.ts` against `frontend/src` reported test ids
"ABSENT". They were composed at runtime by two more primitives, this time through Svelte
attribute interpolation rather than a template literal:

```svelte
<!-- risk/levels/RiskLevelSection.svelte -->
<p data-testid="{testId}-health" …>   <ul data-testid="{testId}-reasons" …>

<!-- risk/levels/l4/TornadoChart.svelte -->
<li data-testid="{testId}-row" …>
```

A second pass, searching the primitives for the suffix composition, found every one. Searching
for `{testId}-` catches both spellings (it is a substring of `${testId}-`); make it
case-insensitive, since `AssetSelect` spells the prop `testid`.

*Recount for this page, on `f1047f766`*: F's plan counts 12 ids composed by those two primitives.
Eleven are (ten by `RiskLevelSection`, one by `TornadoChart`); the twelfth id of that shape in the
spec, `risk-asset-set-l1-row`, is a literal in `AssetSetLossComparisonSection.svelte` — a suffix
match is not a composition either. Five more `getByTestId` literals are composed by interpolation
in the page's own components (`risk-bulk-{action}`, `risk-correlation-ordering-{mode}`). Every one
exists at runtime.

Two lessons:

1. **The probe erred toward red, so it denounced itself.** A false "absent" sends someone to look,
   and looking finds the id; the inverse error above is the quiet one.
2. **This page existed and was not consulted** — no `wiki-search` at the start of the session, so
   the problem was rediscovered instead of looked up (F's plan, F-5). It is the reason this page
   exists.

A sibling zero, R2-112 (21/09): `grep -E` read `max(date)` as "max followed by the group `date`" and
returned nothing on a file that contained it; `grep -F` found it. *"A grep that returns zero does not
say 'absent': it says 'my pattern found nothing'."* For the presence of a literal, use `-F`.

The `AssetSelect` gap described above is closed at `f1047f766`: the wrapper forwards `testId={testid}`
to `SearchSelect` and no longer carries its own id — the fix this page prescribed (`00d8c735b`, 18/09).

## Source files

| Role | Path |
|------|------|
| Suffix composition | `frontend/src/lib/components/ui/select/SimpleSelect.svelte` |
| Suffix composition | `frontend/src/lib/components/ui/select/SearchSelect.svelte` |
| Wrapper — did not forward `testId` when this page was written (`f2ad97dd4`); forwards it since `00d8c735b` | `frontend/src/lib/components/ui/select/AssetSelect.svelte` |
| Consumer passing the stem | `frontend/src/lib/components/risk/AssetSetRiskPanel.svelte` |
| Specs bound to the wrapper id | `frontend/e2e/transactions/tx-import-resolution.spec.ts` |
| Composes `{testId}-health`, `-reasons`, `-errors`, `-metadata`, `-toggle`, `-body`, … | `frontend/src/lib/components/risk/levels/RiskLevelSection.svelte` |
| Composes `{testId}-row`, `-bar`, `-value` | `frontend/src/lib/components/risk/levels/l4/TornadoChart.svelte` |
| Literal `risk-asset-set-l1-row` | `frontend/src/lib/components/risk/AssetSetLossComparisonSection.svelte` |
| The spec probed on 23/09 | `frontend/e2e/portfolio/risk-lab.spec.ts` |
| F's recon (§3) and the missed `wiki-search` (F-5) | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/progress/F-laboratorio-postmerge.md` |

Related: [[problems/front-check-does-not-check-what-you-think]]
