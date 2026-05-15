---
title: "Phase 07 Part 4 Round 6 — Plan D2 Bugfix 1: Split/Promote Polish"
category: source
source_type: plan
date_ingested: 2026-05-31
original_path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_1_SplitPromotePolish.prompt.md
tags: [phase07, transactions, bugfix, split, promote, ux, race-condition, findPromoteMatch, constraints]
related:
  - sources/phase07-part4-round6-pland2-frontend-split-promote
  - sources/phase07-part4-round6-pland2-bugfix2
  - features/F-048
---

# Source: Plan D2 Bugfix 1 — Split/Promote Polish

## Summary
Post-D2 polish round fixing 21 bugs found in manual testing. Key fixes: BulkModal first-open race condition (getTypeRule FALLBACK_RULE before types loaded), BulkModal split treating split as type-change update instead of split operation, promote toolbar not appearing for standalone selections, suggest banner showing wrong target type (FX_CONVERSION instead of CASH_TRANSFER), and promote collapsing leaving 2 separate rows instead of 1 paired.

## Key Takeaways
- **B1 (P0)**: Split Main Table sent only `{splits:[{id:38}]}` — backend handles internally but balance walk failed due to unbalanced mock data
- **B4 (P0)**: BulkModal first-open race — `$effect` assigned `ops` before `ensureTypesLoaded()` completed → `getTypeRule()` returned `FALLBACK_RULE` (requiresPair:false) → paired rows rendered as singles. Fix: deferred `ops` assignment with dual-path (fast=cached, slow=loading)
- **B5 (P0)**: BulkModal split treated as type update, not split operation — backend rejected "Cannot change type from TRANSFER to ADJUSTMENT"
- **B12 (P0)**: Promote toolbar not appearing — selection detection `selectedForPromote` wasn't resolving correctly
- **B14 (P0)**: `findPromoteMatch` returned wrong type — lacked broker/currency constraint verification
- **B16 (P0)**: Promote via suggest left 2 separate rows — local promote needs to collapse into 1 paired row
- **DD-BF1**: Split saved in BulkModal = remove from batch + accumulate in `pendingSplits` (later corrected in Bugfix 2)
- **DD-BF2**: Collapse post-promote: `collapseIntoPaired(opA, opB)` helper rather than reusing `collapsePairedOps()`
- **DD-BF3**: getTypeRule FALLBACK_RULE fix — deferred ops assignment
- **DD-BF4**: `findPromoteMatch` enriched with `brokerA`, `brokerB`, `currencyA`, `currencyB` for client-side constraint check
- **DD-BF5**: PromoteMergeModal tags use existing `TagInput.svelte`
- **DD-BF6**: Validation error codes centralized via `TXValidationCode` StrEnum exposed in `GET /transactions/types`
- **B20 (P0)**: Mock data balance fixed — added BUY Apple qty=+5 on IB to cover promote-test ADJUSTMENT -2
- **21 bugs** catalogued: 6 P0 critical, 9 P1 UX, 4 P1 tech, 2 P2

## Wiki Pages Updated
- [[features/F-048]] — updated (bugfix 1 status entry)

