# PlanD-D1D2 — Split/Promote Full Stack (Pre-R2)

> **Phase**: 07 (Transactions) → Parte4 → Round6 → PlanD-D1D2
> **Period**: 2026-05-12 → 2026-05-19
> **Status**: ✅ ALL COMPLETED
> **Master Plan**: [`plan-phase07-PlanD_SplitPromoteFullStack.prompt.md`](../plan-phase07-PlanD_SplitPromoteFullStack.prompt.md) (✅ DONE)

## Summary

Backend batch pipeline for split/promote, frontend UI with PromoteMergeModal, suggest banner, and centralized payload/commit helpers. 4 bugfix rounds followed D2.

## Sub-Plans

| # | File | Scope | Status |
|---|------|-------|--------|
| **D1** | `plan-PlanD1_BackendBatchSuggest.prompt.md` | Backend: batch pipeline + promote-suggest endpoint | ✅ |
| **D2** | `plan-PlanD2_FrontendSplitPromoteUI.prompt.md` | Frontend: split action, promote banner, PromoteMergeModal | ✅ |
| **Centralize** | `plan-CentralizePayloadCommit.prompt.md` | txPayloadHelpers.ts + txCommitApi.ts (9 callsite migration) | ✅ |

### Bugfix Rounds

| # | File | Problems Solved | Status |
|---|------|----------------|--------|
| 1 | `Bugfix/plan-bugfix1_SplitPromotePolish.prompt.md` | F1+F6 done; F2-F14 absorbed by later rounds | ✅ |
| 2 | `Bugfix/plan-bugfix2_PayloadSplitPreviewUX.prompt.md` | Payload alignments, split preview rendering | ✅ |
| 3 | `Bugfix/plan-bugfix3_UXModalPayloadSuggestE2E.prompt.md` | PromoteMergeModal polish, E2E tests (absorbed D3) | ✅ |
| 4 | `Bugfix/plan-bugfix4_SplitSuggestPmcOverrideUx.prompt.md` | Split suggest logic, PMC override UX | ✅ |

## Key Decisions

- **DD1**: Constraint check duck-typing (`_PromoteCandidate` dataclass)
- **DD2**: Eliminated standalone `/split` and `/promote` endpoints (batch-only)
- Centralized payload: `resolveOps()` → `ResolvedOp[]` → API call (single path for all 9 callers)
