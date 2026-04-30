---
title: "Phase 07 Part 4 Round 4 — Unified Batch Pipeline"
category: source
source_type: plan
date_ingested: 2026-05-25
original_path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round4_UnifiedBatchPipeline.prompt.md
tags: [phase07, transactions, backend, api, unified-pipeline, lenient-parse, validate, commit, breaking-change]
related: [sources/phase07-part4-round3-bugfix2, decisions/unified-batch-pipeline, features/F-046]
---

# Source: Phase 07 Part 4 Round 4 — Unified Batch Pipeline

## Summary

Major backend refactoring that merged 4 transaction mutation endpoints into 2 unified endpoints sharing a single `TXMixedBatch` body with `List[dict]` for lenient per-row parsing. Fixes the Pydantic 422 pre-emption problem (W21–W23) where schema errors killed the handler before balance validation could run. Also includes error display unification in frontends (commit failures use same translated issue banners as validation) and anti-bounce protection (10s dedup for validate+commit).

## Key Takeaways

- **4 endpoints → 2**: Removed `POST /bulk`, `PATCH /bulk`, `DELETE /bulk`. Replaced with `POST /validate` (dry-run, always rollback) and `POST /commit` (commit if clean). Both accept `TXMixedBatch { creates: List[dict], updates: List[dict], deletes: List[int] }`
- **Lenient per-row parse**: `_parse_lenient()` does `Model.model_validate(raw)` per row in try/except, collecting schema errors while continuing to parse valid rows. Valid rows proceed to balance walk. Schema + business + balance errors coexist in one response
- **Unified pipeline**: `execute_batch()` is the single entry point for all tx mutations. `promote_transfer` and `broker_service` initial deposits also migrated to use it
- **`TXBatchResponse`** replaces 4 old response types: `{ committed: bool, issues: List[TXValidationIssue], results?: List[TXBatchResultItem] }`. HTTP 200 always (committed=false is semantic, not an error)
- **Frontend error display unification**: commit failures now show same translated, categorised issue list as validation (red ⛔ banner vs yellow ⚠). Balance errors (index=-1) separated from field errors (index≥0)
- **Anti-bounce**: 10s deduplication on validate+commit when draftKey unchanged. Tracks `lastValidatedDraftKey` + `lastCommitDraftKey`
- **Balance error sentinel**: `index=-1` for broker-level balance violations (not attributable to a specific row). Frontend BulkModal does client-side row attribution by matching `brokerId + assetId/currency`
- **Net code reduction**: backend −290 lines, frontend −18 lines, tests +195 lines. 7 deprecated schemas deleted, 3 deprecated service methods deleted

## Wiki Pages Updated

- [[features/F-046]] — endpoints table updated with new /validate + /commit
- [[decisions/unified-batch-pipeline]] — new decision page

