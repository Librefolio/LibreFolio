---
title: "The colour ratchet's --resolve drops a colour accepted on one side"
category: problem
status: workaround
date: 2026-10-15
tags: [frontend, colour, tooling, git, merge, ratchet, gates]
related: [decisions/colour-factorisation-at-pixel-parity]
---

# Problem: The colour ratchet's `--resolve` drops a colour accepted on one side

## Symptom
On 15/10, merging `dev_release2` into workstream R's branch (the base merge with T-2), `themeRoles.baseline.tsv`
conflicted. `node frontend/scripts/theme/theme-roles.mjs --resolve` wrote a file with no conflict markers, but
`--check` turned red:

```
R2 m2 lib/stores/app/themeStore.ts: colour literals beyond its record: #166534
```

The `~accept` line declared for that file the day before was still in the baseline.

## Root Cause
`--resolve` merges the three index stages of the conflicted file with `mergeBaselines`. For a line present on both
sides, it keeps the lower m1 and **only the m2 values both sides hold**. It compares neither side with the base, and
it ignores the `~accept` declarations. The three stages of the line were:

| Stage | Line |
|---|---|
| base | `lib/stores/app/themeStore.ts 0 #156534 #1a4031` |
| R's side | `lib/stores/app/themeStore.ts 0 #166534 #1a4031`, the D3 fix accepted with `--accept` on 14/10 |
| target | `lib/stores/app/themeStore.ts 0 #156534 #1a4031`; the target did not have R yet |

Only `#1a4031` is on both sides, so the accepted colour disappeared, although the target never touched the line. A
real three-way merge would have taken R's side, since the target's side equals the base.

## Solution (workaround)
Run the same `--accept` again on the merged tree, with the same reason, then `--check`, then stage the baseline.
`writeBaseline` removes duplicate declarations, so the `~accept` line stays single. `--accept` widens a record, so it
needs the colour coordinator's OK every time.

Proposed fix, backlog R-8 (for T): make `mergeBaselines` a real three-way merge, where the side that differs from the
base wins when the other side equals the base; or let the side that declares an `~accept` for the file win its line.

## Prevention
- After `--resolve`, always run `--check` before staging.
- If it flags a file that one side had accepted, run that side's `--accept` again (with the OK) instead of editing
  the baseline by hand.
- A dry run predicts the outcome without writing: `resolveConflict()` then `compareWithBaseline(scanTree(), merged)`,
  both exported by `theme-roles.mjs`.

## Impact
Minutes. The dry run had predicted the red before the file was touched, and the coordinator authorised the re-run.

## Source files
| Role | Path |
|------|------|
| Ratchet (`mergeBaselines`, `resolveConflict`, `acceptFile`) | `frontend/scripts/theme/theme-roles.mjs` |
| Baseline | `frontend/src/themeRoles.baseline.tsv` |
| The accepted file | `frontend/src/lib/stores/app/themeStore.ts` |
| Ratchet gate | `frontend/src/themeRoles.gate.test.ts` |
