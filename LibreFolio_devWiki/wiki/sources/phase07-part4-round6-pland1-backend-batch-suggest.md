---
title: "Phase 07 Part 4 Round 6 — Plan D1: Backend Batch Pipeline + Promote-Suggest"
category: source
source_type: plan
date_ingested: 2026-05-31
original_path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD1_BackendBatchSuggest.prompt.md
tags: [phase07, transactions, backend, batch-pipeline, split, promote, promote-suggest, consumed-link-uuids, tests]
related:
  - sources/phase07-part4-round6-pland-split-promote-master
  - sources/phase07-part4-round6-pland2-frontend-split-promote
  - decisions/cash-transfer-split-promote
  - decisions/unified-batch-pipeline
  - features/F-046
  - features/F-048
---

# Source: Plan D1 — Backend Batch Pipeline + Promote-Suggest

## Summary
D1 (completed 2026-05-12) extended the backend `execute_batch` pipeline with split and promote operations, eliminated the standalone `/split` and `/promote` endpoints, created the `POST /transactions/promote-suggest` endpoint, and covered everything with 18 backend tests. ~10h effort over ~2 days.

## Key Takeaways
- **DD1 — Constraint check duck-typing**: `_PromoteCandidate` dataclass enables constraint validation with both `Transaction` objects (pipeline) and raw `TXPromoteSuggestInput` (suggest)
- **DD2 — Endpoint elimination**: `POST /transactions/split` and `POST /transactions/promote` removed entirely (never used in production); 8 orphan schemas also removed (`TXSplitItem/Request/Response`, `TXPromoteItem/Request/Response`)
- **DD3 — Schema cleanup**: `split_pairs()` and `promote_pairs()` service methods removed; logic absorbed into pipeline Steps 5b/5c
- **DD4 — `consumed_link_uuids`**: `Set[str]` tracks link_uuids consumed by promotes in Step 5c → Step 6 link resolution skips them, preventing double-processing
- **Pipeline extension**: Step 5b (splits) after creates, Step 5c (promotes) after splits, both before Step 6 link resolution
- **`TXPromoteSuggestInput`**: accepts `id` (real or fake <0), `type`, `broker_id`, `date`, optional `currency`/`asset_id`/`amount`/`quantity`
- **Promote-suggest logic**: per-input query DB for standalone TXs with complementary type ± tolerance_days, validate field_constraints, exclude self-matches
- **Helper `_resolve_promote_ref`**: resolves promote references via `id > 0` → `existing_by_id` lookup, or `link_uuid` → `link_uuid_map` lookup (for new+new promotes)
- **Helper `_find_promote_rule_match`**: scans `TX_TYPE_METADATA.promote_from` rules for {type_a, type_b} combinations + constraint check
- **18 tests** in `test_transactions_batch_split_promote.py`: 5 split tests, 7 promote tests (saved+saved, new+new via link_uuid, saved+new, incompatible, already-paired, resolved_fields, constraint-fail), 6 suggest tests (finds candidate, tolerance, excludes paired, excludes self, multiple inputs, fake ID)
- **Mock data**: 4 standalone TXs tagged `promote-test` added to `populate_mock_data.py`

## Wiki Pages Updated
- [[decisions/cash-transfer-split-promote]] — updated (endpoints eliminated, batch-only)
- [[features/F-046]] — (pipeline extensions documented)

