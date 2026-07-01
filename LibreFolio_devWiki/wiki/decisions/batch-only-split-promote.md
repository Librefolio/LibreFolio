---
title: "Batch-only split/promote — eliminate standalone endpoints"
category: decision
status: resolved
date: 2026-05-12
tags: [backend, transactions, split, promote, batch-pipeline, api, endpoint-elimination]
related:
  - decisions/unified-batch-pipeline
  - decisions/cash-transfer-split-promote
  - concepts/centralized-tx-payload
  - features/F-048
  - features/F-046
---

# Decision: Batch-Only Split/Promote — Eliminate Standalone Endpoints

## Context

Split and promote operations were originally implemented as standalone `POST /transactions/split` and `POST /transactions/promote` endpoints (predisposed but never used in production). When Phase 07 Part4 introduced the unified `execute_batch` pipeline (`/validate` + `/commit`), the standalone endpoints became redundant. All new split/promote functionality (including the suggest banner and PromoteMergeModal UX) was built assuming the batch pipeline.

## Options Considered

1. **Thin wrappers** — keep the standalone endpoints but have them delegate to `execute_batch` internally.
   - Pro: backward compatibility (in principle), no callsite migration needed.
   - Con: never actually used in production (no callsites existed); creates dead code; two code paths to maintain.

2. **Batch-only (chosen)** — eliminate standalone endpoints entirely. Split/promote pass exclusively through `/validate` + `/commit` via `splits[]` and `promotes[]` fields in `TXMixedBatch`.
   - Pro: single code path; clean; consistent with `creates`, `updates`, `deletes` already in batch.
   - Con: none — no backward compat needed.

## Decision

**Option 2 chosen**: Standalone `POST /transactions/split` and `POST /transactions/promote` deleted. Associated schemas (`TXSplitRequest`, `TXSplitResponse`, `TXPromoteRequest`, `TXPromoteResponse`, etc.) and service methods (`split_pairs()`, `promote_pairs()`) removed. Logic absorbed into `execute_batch()`.

Two new batch item types added to `TXMixedBatch`:
```python
splits: List[TXSplitBatchItem]     # each has id (pair member to split)
promotes: List[TXPromoteBatchItem] # each has id_a/link_uuid_a + id_b/link_uuid_b + resolved_fields
```

## Consequences

- **`_PromoteCandidate` duck-typing**: `_check_promote_constraints` now accepts any object with `broker_id`, `currency`, `amount`, `quantity`, `asset_id` attributes (not just `Transaction`). New `_PromoteCandidate` dataclass used for the `promote-suggest` path.
- **`consumed_link_uuids` set**: prevents double-processing — when a promote consumes a `link_uuid` from the same batch, Step 6 (link resolution) skips it.
- **New endpoint added**: `POST /transactions/promote-suggest` (bulk, not a standalone mutation) — input `TXPromoteSuggestInput[]`, output candidates map.
- **Frontend unified**: all 9 callsites (FormModal, BulkModal, BulkDeleteLinkedPairModal, +page.svelte) migrated to `txPayloadHelpers.ts` + `txCommitApi.ts`.

## Links

- [[decisions/unified-batch-pipeline]] — parent decision: 4 endpoints → 2
- [[decisions/cash-transfer-split-promote]] — CASH_TRANSFER enum + split/promote batch
- [[concepts/centralized-tx-payload]] — frontend payload layer
- Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/PlanD-D1D2/plan-PlanD1_BackendBatchSuggest.prompt.md`

## Source files

| Role | Path |
|------|------|
| Transaction schemas | `backend/app/schemas/transactions.py` |
| Transaction service | `backend/app/services/transaction_service.py` |
| TX API endpoints | `backend/app/api/v1/transactions.py` |
| BulkModal (FE) | `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte` |
