---
title: "AI Export drawdown recovery rejected valid selected-period history when the technical window was empty"
category: problem
status: resolved
date: 2026-07-26
updated: 2026-07-27
mkdocs: "developer/architecture/patterns/ai_export_snapshot.md"
tags: [backend, ai-export, asset, drawdown, applicability, history, technical-window]
related:
  - sources/phase00-ai-export-backend-snapshot
  - decisions/ai-export-versioned-snapshot-boundary
  - entities/ai-export-snapshot-service
---

# Problem: AI Export drawdown recovery rejected valid selected-period history when the technical window was empty

## Symptom

An Asset `drawdown_recovery` request could have two valid observed prices in the selected historical period, including a measurable prior maximum, yet return HTTP 409 `task_not_applicable` when no observations existed in the trailing technical window.

## Root Cause

Market facts were built only from technical-window observations. An empty technical window therefore produced no market context, and the later drawdown applicability guard reported `drawdown_metric_unavailable` even though the selected period itself contained sufficient observed history. Presentation context had accidentally become a stricter requirement than the task contract.

## Solution

- Build market context from technical observations when they exist, otherwise from selected observed history.
- Continue calculating period change and drawdown against `selected_observed`, not against the fallback choice.
- Keep applicability unchanged: at least two selected observations and a measurable prior maximum.

The implementation is the explicit fallback `technical_observed or selected_observed`.

## Prevention

Keep context windows separate from applicability windows. Regression coverage must include a selected historical period whose last observation predates the technical window and must still produce the correct current selected-period price and drawdown.

## Impact

The bug rejected valid historical drawdown analysis with a user-visible 409. It did not alter stored prices or drawdown mathematics.

## Final verification

The targeted Asset assembler regression remained green in the final canonical gate, and the completed Phase 0 build received desktop/mobile approval on 27 July 2026. The manual approval covers the integrated AI Export surfaces; the selected-history rule itself remains enforced by backend regression tests.

## Links

- [[sources/phase00-ai-export-backend-snapshot]]
- [[decisions/ai-export-versioned-snapshot-boundary]]
- [[entities/ai-export-snapshot-service]]

## Source files

| Role | Path |
|------|------|
| Final plan and archive index | `LibreFolio_developer_journal/Release_2/phases/01_signalMigration/02_aiExport/plan-phase00AiExportBackendSnapshotImplementation.prompt.md`, `LibreFolio_developer_journal/Release_2/phases/01_signalMigration/02_aiExport/README.md` |
| Drawdown component (direct successor — carries this fix) | `backend/app/services/ai_export/components/drawdown_context.py` |
| Asset payload components | `backend/app/services/ai_export/components/asset_payloads.py`, `backend/app/services/ai_export/components/asset_core.py` |
| Applicability contract (successor to the deleted profile) | `backend/app/services/ai_export/analyses/spec.py`, `backend/app/services/ai_export/components/spec.py` |
| Regression tests (successors) | `backend/test_scripts/test_services/test_ai_export_components_drawdown_context.py`, `backend/test_scripts/test_services/test_ai_export_components_asset_fx_integration.py` |
| HTTP 409 problem mapping | `backend/app/api/v1/ai_export.py` |
| Developer architecture | `mkdocs_src/docs/developer/architecture/patterns/ai_export_snapshot.md` |

> ### Path note (2026-09-01) — the modules this page names were **dismantled**, not moved
>
> `ai_export/assemblers/` and `ai_export/profiles/` still exist as directories, but they
> contain nothing except `__pycache__` — stale bytecode of files that are gone. That litter
> is the only reason `ls` still shows them, and it is what makes them look like a move.
> They were **deleted** in commit **`615a52eb` (2026-08-05)**, *"refactor(ai-export): remove
> legacy runtime"*, which removed **22 233 lines against 1 577 added**: the whole
> `assemblers/` + `profiles/` + `resolver.py` + `sampling.py` + `technical.py` +
> `normalization.py` + `service.py` stack, and the tests that covered it.
>
> The commit states the reason in one sentence: *"Keep one production path so catalog,
> prompts, and tests cannot drift between V3 composition and **an unreachable
> profile/assembler stack**."* It was not dead weight being tidied — it was a **second
> path that could still be reached by some callers and had begun to disagree with the
> first**. The fix was to delete the loser, not to reconcile them. Compare
> [[problems/registered-but-unreachable-test-actions]] and
> [[concepts/silent-no-op-option]]: same family — code that is present, plausible, and
> not the one that runs.
>
> The surviving path is **V3 composition**: `components/` (one module per payload),
> `datasets/` and `analyses/` (catalog + spec), `temporal/`, `composer.py` and
> `runtime_service.py`. The table above points there.
>
> **This page was written on 2026-08-31, twenty-six days after the deletion.** It named
> the deleted modules because it was written from the plan that proposed them, not from
> the tree — the same failure that produced the invented `scripts/test_runner/` paths.

> **How the defect was actually settled.** The successor module does not contain a better
> fallback — it contains **no fallback**. `components/drawdown_context.py:31` says so in
> as many words: *"never fails — there is deliberately no success-shaped fallback."*
> A failed or unavailable drawdown now returns an explicit `FAILED` / `UNAVAILABLE` status
> with a message naming the scope and period (`:288`, `:320`), instead of quietly
> substituting a different history and returning something success-shaped. That is the
> same lesson as [[concepts/silent-no-op-option]], reached from the other direction.
