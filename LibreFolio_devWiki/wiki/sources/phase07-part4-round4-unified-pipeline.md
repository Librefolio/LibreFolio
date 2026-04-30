---
title: "Phase 7 Part 4 Round 4 — Unified Batch Pipeline"
category: source
source_type: plan
date_ingested: 2026-05-25
original_path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round4_UnifiedBatchPipeline.prompt.md
tags: [phase07, transactions, backend, frontend, architecture, pipeline, api, breaking-change, lenient-parse]
related: [sources/phase07-part4-round3-bugfix2, features/F-046, features/F-048, decisions/unified-batch-pipeline]
---

# Source: Phase 7 Part 4 Round 4 — Unified Batch Pipeline

## Summary
Merged 4 transaction mutation endpoints (`POST /bulk`, `PATCH /bulk`, `DELETE /bulk`, `POST /validate`) into 2 endpoints (`POST /validate` dry-run, `POST /commit` real) sharing a single `TXMixedBatch` body with `List[dict]` for creates/updates (lenient per-row parse). Fixes the Pydantic 422 pre-emption problem where FastAPI's schema validation blocked service-layer balance checking. Backend diff: −290 lines net. All deprecated schemas and service methods deleted. Frontend migrated all 4 modal components (FormModal, BulkModal, CashTransactionModal, BulkDeleteLinkedPairModal).

## Key Takeaways
- **2 endpoints replace 4**: `POST /validate` (dry-run) + `POST /commit` (real) — same `_execute_batch()` pipeline internally
- **`List[dict]` body**: FastAPI doesn't validate individual rows; `_parse_lenient()` does per-row `model_validate()` in try/except → schema errors coexist with balance violations
- **Pipeline flow**: parse → access check → apply (delete→update→create) → balance walk → commit/rollback
- **`TXBatchResponse`**: `{committed: bool, issues: List[TXValidationIssue], results?: List[TXBatchResultItem]}` — replaces 4 old response types
- **HTTP 200 for committed:false**: Correct by design — structured response, not an error
- **promote_transfer migrated**: Now calls `execute_batch` (delete originals + create new pair)
- **Anti-bounce 10s**: Both validate and commit skip when draftKey unchanged + < 10s elapsed
- **Balance error sentinel**: `index=-1` for broker-level errors; frontend does client-side row attribution

## Wiki Pages Updated
- [[decisions/unified-batch-pipeline]] — new decision page
- [[features/F-046]] — API endpoints updated
- [[features/F-048]] — commit calls migrated

