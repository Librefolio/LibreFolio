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
| Final plan and archive index | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/plan-phase00AiExportBackendSnapshotImplementation.prompt.md`, `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/README.md` |
| Asset assembler fix | `backend/app/services/ai_export/assemblers/asset.py` |
| Asset profile/applicability contract | `backend/app/services/ai_export/profiles/asset.py` |
| Regression tests | `backend/test_scripts/test_services/test_ai_export_asset_fx.py` |
| HTTP 409 problem mapping | `backend/app/api/v1/ai_export.py` |
| Developer architecture | `mkdocs_src/docs/developer/architecture/patterns/ai_export_snapshot.md` |
