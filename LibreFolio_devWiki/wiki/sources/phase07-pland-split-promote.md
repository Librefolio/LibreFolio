---
title: "Phase 07 — PlanD-D1D2: Split/Promote Full Stack"
category: source
source_type: plan
date_ingested: 2026-06-30
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/PlanD-D1D2/README.md
tags: [phase07, transactions, split, promote, batch-pipeline, backend, frontend, centralized-payload]
related:
  - decisions/batch-only-split-promote
  - concepts/centralized-tx-payload
  - features/F-048
  - features/F-046
---

# Source: Phase 07 — PlanD-D1D2 Split/Promote Full Stack

## Summary

This source group covers the archived sub-plan bundle for split and promote operations (D1+D2+Centralize+4 bugfix rounds), executed 2026-05-12 to 2026-05-19. D1 integrated split and promote into the unified `execute_batch` pipeline and eliminated the standalone `/split` and `/promote` endpoints. D2 delivered the frontend PromoteMergeModal, suggest banner, and the `resolveOps()` → `ResolvedOp[]` → API call pattern. The `plan-CentralizePayloadCommit.prompt.md` unified all 9 API callsites into `txPayloadHelpers.ts` + `txCommitApi.ts`. Four bugfix rounds polished the UX: split preview rendering, PMC override logic, and E2E tests.

## Key Takeaways

- **DD1 — `_PromoteCandidate` duck-typing**: `_check_promote_constraints` was generalized to accept any object with `broker_id`, `currency`, `amount`, `quantity`, `asset_id` attributes. New `_PromoteCandidate` dataclass (namedtuple) used for `promote-suggest` input without requiring real `Transaction` objects.
- **DD2 — Endpoint elimination**: Standalone `POST /transactions/split` and `POST /transactions/promote` eliminated entirely. All split/promote passes exclusively through `/validate` + `/commit` via `splits[]` and `promotes[]` in `TXMixedBatch`.
- **DD3 — Schema cleanup**: `TXSplitItem`, `TXSplitRequest`, `TXSplitResponse`, `TXPromoteItem`, etc. removed. `split_pairs()` and `promote_pairs()` service methods absorbed into `execute_batch`.
- **DD4 — `consumed_link_uuids`**: Set tracks which `link_uuid` values were consumed by promotes in a batch, so Step 6 (link resolution) doesn't process them twice.
- **Centralized payload layer**: `txPayloadHelpers.ts` + `txCommitApi.ts` replace 9 scattered callsites (FormModal, BulkModal, BulkDeleteLinkedPairModal, +page.svelte) with a single `resolveOps()` → `ResolvedOp[]` → `buildBatchPayload()` → `commitBatch()` path.
- **PMC override UX**: Override available in split suggest UI only when WAC differs from market price; otherwise auto-calculated PMC is shown read-only.
- **New `POST /transactions/promote-suggest` endpoint**: Bulk endpoint, accepts `TXPromoteSuggestInput[]`, returns `TXPromoteSuggestResponse` map of input_id → `TXPromoteSuggestCandidate[]`.
- `saveWithRetry` renamed to `trySave` (semantically: never retries, is a try/catch wrapper).

## Wiki Pages Created/Updated

- [[decisions/batch-only-split-promote]] — new: eliminated standalone split/promote endpoints
- [[concepts/centralized-tx-payload]] — new: txPayloadHelpers.ts + txCommitApi.ts pattern
- [[features/F-048]] — updated: split/promote fullstack implementation
- [[features/F-046]] — updated: promote-suggest backend endpoint

## Source files

| Role | Path |
|------|------|
| Sub-plan index | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/PlanD-D1D2/README.md` |
| Backend D1 | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/PlanD-D1D2/plan-PlanD1_BackendBatchSuggest.prompt.md` |
| Frontend D2 | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/PlanD-D1D2/plan-PlanD2_FrontendSplitPromoteUI.prompt.md` |
| Payload centralization | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/PlanD-D1D2/plan-CentralizePayloadCommit.prompt.md` |
| Transaction schemas | `backend/app/schemas/transactions.py` |
| Transaction service | `backend/app/services/transaction_service.py` |
| Payload helpers (FE) | `frontend/src/lib/utils/txPayloadHelpers.ts` |
| Commit API (FE) | `frontend/src/lib/utils/txCommitApi.ts` |
| BulkModal | `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte` |
