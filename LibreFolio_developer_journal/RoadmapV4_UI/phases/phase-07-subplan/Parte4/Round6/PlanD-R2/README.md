# PlanD-R2 — Walktest Feedback Round (WAC Feature)

> **Phase**: 07 (Transactions) → Parte4 → Round6 → PlanD-R2
> **Period**: 2026-05-10 → 2026-06-01
> **Status**: ✅ SP-A/B/C COMPLETED | ⏳ SP-D/E pending (separate plan chain)
> **Master Plan**: [plan-R2-WalktestFeedbackRound.prompt.md](./plan-R2-WalktestFeedbackRound.prompt.md)

## Summary

18-step master plan implementing Weighted Average Cost (WAC) with cross-currency support, backend test suite, and full frontend BulkModal UX including 8 deep bugfix iterations.

## Sub-Plans

| # | File | Scope | Status |
|---|------|-------|--------|
| **SP-A** | [SP-A-CostBasisWAC/](./SP-A-CostBasisWAC/) | Backend: Currency schema, WAC service, recalc-wac endpoint | ✅ |
| **SP-B** | [SP-B-BackendTests/](./SP-B-BackendTests/) | Backend: 13 WAC API tests (WAC-1→WAC-13) | ✅ |
| **SP-C** | [SP-C-BulkModalSuggestUX/](./SP-C-BulkModalSuggestUX/) | Frontend: suggest overhaul, PromoteMergeModal, split UX | ✅ |

### SP-C Bugfix Chain

| # | File | Problem Solved | Status |
|---|------|---------------|--------|
| 1 | `plan-SP-C-BugfixRound1.prompt.md` | 12 bugs: concurrency, double-submit, form reset, FX display | ✅ |
| 2 | `plan-SP-C-BugfixRound2-WacPreview.prompt.md` | 13 bugs + introduced WAC preview section | ✅ |
| 3 | `plan-SP-C-FxImpliedRateSpread.prompt.md` | Implied FX rate and spread in BulkModal | ✅ |

### SP-C WacPreview Deep Bugfixes

| # | File | Problem Solved | Status |
|---|------|---------------|--------|
| 4 | `plan-BugfixRound3-UnifiedPartnerArch.prompt.md` | Unified partner: pairedWith, getPartnerOp, visibleOps | ✅ |
| 5 | `plan-ReactiveWacBulkModal.prompt.md` | Reactive WAC: auto-recalc, FX cache, CostBasisFieldMode | ✅ |
| 6 | `plan-FixCloneLinkUuid.prompt.md` | Clone creating duplicate link_uuid | ✅ |
| 7 | `plan-FixWacFeedbackLoop.prompt.md` | Infinite loop: WAC recalc → field update → WAC recalc | ✅ |
| 8 | `plan-WacInlineValidateCommit.prompt.md` | Validate Now button, pending indicator, apply/discard | ✅ |
| 9 | `plan-FixWacPartnerRows.prompt.md` | Partner rows not showing WAC data (index remapping) | ✅ |
| 10 | `plan-StatelessWacPreview.prompt.md` | Mode persistence across edit cycles (stateless section) | ✅ |
| 11 | `plan-WacBackendCleanup.prompt.md` | Backend dead code removal, simplified interfaces | ✅ |

## Key Patterns Established

- **CostBasisFieldMode** state machine: `auto` → `manual` → `auto-detail`
- **pairedWith / getPartnerOp**: unified partner linking for TRANSFER pairs
- **Stateless preview**: WacPreviewSection receives mode from parent, doesn't hold internal state
- **fxMarketCache**: per-validate FX rate cache to avoid redundant API calls
- **wac_results remapping**: backend returns by payload index, frontend maps to visible operation index

## Related Wiki Pages

- Feature: F-097 (WAC — Weighted Average Cost)
- Feature: F-048 (BulkModal / Suggest / Promote)
- Decision: cost-basis-currency-object
