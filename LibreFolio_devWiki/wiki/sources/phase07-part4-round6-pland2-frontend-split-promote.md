---
title: "Phase 07 Part 4 Round 6 — Plan D2: Frontend Split/Promote UI + Suggest Banner"
category: source
source_type: plan
date_ingested: 2026-05-31
original_path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD2_FrontendSplitPromoteUI.prompt.md
tags: [phase07, transactions, frontend, split, promote, promote-suggest, promote-merge-modal, bulk-modal, i18n]
related:
  - sources/phase07-part4-round6-pland1-backend-batch-suggest
  - sources/phase07-part4-round6-pland-split-promote-master
  - features/F-048
  - features/F-047
---

# Source: Plan D2 — Frontend Split/Promote UI + Suggest Banner

## Summary
D2 (completed 2026-05-12, ~10h) built the frontend split/promote UI: PromoteMergeModal for divergent field resolution, split/promote row actions in BulkModal and Main Table, migration of Main Table promote from deprecated `/promote` endpoint to batch `{promotes:[]}`, and the promote-suggest green banner with DB and local candidate detection.

## Key Takeaways
- **PromoteMergeModal** (C5): new greenfield component; 3-column diff (left readonly, center editable, right readonly) for description/tags/date/cost_basis_override; ◀/⟷/▸ auto-populate buttons; merge=default (concat desc, union tags, latest date); skipped entirely if all fields identical
- **Main Table split** (C1): new `onSplitRow` prop on TransactionsTable with `Unlink` icon; ConfirmModal with pair summary; commits via `{splits: [{id}]}` through batch endpoint
- **Main Table promote** (C2): migrated from dead `zodiosApi.promote_pairs` to batch `{promotes: [{id_a, id_b, resolved_fields}]}`; if fields diverge → PromoteMergeModal; if identical → direct ConfirmModal
- **BulkModal split** (C3): client-side `SPLIT_TYPE_MAP` (mirror of backend); saved paired → `pendingSplits[]` accumulator + commit in `batch.splits`; new paired → local transformation (remove link_uuid, mutate types, separate ops)
- **BulkModal promote** (C4): selection-based toolbar when 2 standalone rows selected + `findPromoteMatch()`; 2 saved → `pendingPromotes[]` in batch; 2 new → local transform (assign shared link_uuid, mutate types); 1 saved + 1 new → batch + link_uuid
- **Promote-suggest banner** (C6): green banner above grid; DB candidates via `$effect` debounce 500ms calling `/promote-suggest`; local candidates via `$derived` `findPromoteMatch()` on new standalone ops; click 🔗 auto-selects + opens MergeModal
- **DD-D2.1–D2.5**: local split/promote (new ops) avoids API calls; constraint check deferred to backend for manual promote; `resolved_fields` applied to both sides by backend
- **17 i18n keys** added in 4 languages (actions.split, split.*, promote.*, promoteSuggest.*)
- **5 files modified**: PromoteMergeModal.svelte (new), TransactionsTable.svelte, +page.svelte, TransactionBulkModal.svelte, i18n JSONs

## Wiki Pages Updated
- [[features/F-048]] — updated (split/promote actions, MergeModal, suggest banner)
- [[features/F-047]] — updated (split row action, promote migration)

