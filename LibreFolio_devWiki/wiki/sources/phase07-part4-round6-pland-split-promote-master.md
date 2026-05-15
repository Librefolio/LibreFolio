---
title: "Phase 07 Part 4 Round 6 — Plan D: Split/Promote Full Stack (master plan)"
category: source
source_type: plan
date_ingested: 2026-05-31
original_path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD_SplitPromoteFullStack.prompt.md
tags: [phase07, transactions, split, promote, batch-pipeline, promote-suggest, merge-modal, fullstack]
related:
  - sources/phase07-part4-round6-pland1-backend-batch-suggest
  - sources/phase07-part4-round6-pland2-frontend-split-promote
  - sources/phase07-part4-round6-pland2-bugfix1
  - sources/phase07-part4-round6-pland2-bugfix2
  - sources/phase07-part4-round6-pland2-bugfix3
  - sources/phase07-part4-round6-pland2-bugfix4
  - decisions/cash-transfer-split-promote
  - decisions/unified-batch-pipeline
  - features/F-048
  - features/F-046
---

# Source: Phase 07 Part 4 Round 6 — Plan D: Split/Promote Full Stack

## Summary
Master plan (2026-05-12, in-progress) for integrating split and promote operations into the unified batch pipeline. Decomposed into D1 (backend ✅), D2 (frontend ✅), D2-bugfix1-4 (polish ✅), and D2-round2 (⏳ planning). D3 (E2E tests) was absorbed into D2-bugfix3. The plan eliminates standalone `/split` and `/promote` endpoints (DD2), extends `TXMixedBatch` with `splits[]` and `promotes[]`, creates `POST /transactions/promote-suggest` for DB candidate matching, and builds PromoteMergeModal for resolving divergent fields between promote candidates.

## Key Takeaways
- **Split/promote in batch pipeline**: `TXMixedBatch` extended with `splits: List[dict]` and `promotes: List[dict]`; pipeline steps: Step 5b (splits after creates) → Step 5c (promotes)
- **Standalone endpoints eliminated** (DD2): `POST /transactions/split` and `POST /transactions/promote` were never used in production — removed entirely from codebase
- **`POST /transactions/promote-suggest`**: new endpoint; takes list of TX (real or fake ID), returns DB candidates matching promote_from rules within ±tolerance_days
- **`SPLIT_TYPE_MAP`**: TRANSFER→(ADJUSTMENT,ADJUSTMENT), CASH_TRANSFER→(WITHDRAWAL,DEPOSIT), FX_CONVERSION→(WITHDRAWAL,DEPOSIT); promote is the inverse
- **`promote_from` rules**: ADJUSTMENT+ADJUSTMENT→TRANSFER, WITHDRAWAL+DEPOSIT(same currency, diff broker)→CASH_TRANSFER, WITHDRAWAL+DEPOSIT(diff currency, same broker)→FX_CONVERSION
- **`consumed_link_uuids`** (DD4): prevents Step 6 link resolution from re-processing link_uuids already consumed by promotes in Step 5c
- **PromoteMergeModal**: 3-column diff UI (left readonly / center editable / right readonly) for description, tags, date, cost_basis_override; ◀/⟷/▸ buttons
- **18 backend tests** covering split in batch, promote (saved+saved, new+new, saved+new), promote-suggest
- **D3 merged into D2-bugfix3**: E2E test scope absorbed into the largest bugfix round
- **D2-round2 still planning**: cost_basis with FX, AssetEvent picker, paired TX store-first pattern

## Sub-plan chain
| Sub-plan | Status | Focus |
|----------|--------|-------|
| D1 — Backend Batch + Suggest | ✅ | Pipeline extensions, endpoint elimination, promote-suggest, 18 tests |
| D2 — Frontend Split/Promote UI | ✅ | PromoteMergeModal, BulkModal split/promote, Main Table migration, suggest banner |
| D2-bugfix1 — Polish | ✅ | 21 bugs, UX edge cases, findPromoteMatch constraint enrichment |
| D2-bugfix2 — Payload + Split Preview | ✅ | Split preview editability (corrects DD-BF1), pipeline reorder, ids[] schema |
| D2-bugfix3 — UX + Payload + Suggest + E2E | ✅ | Biggest round: PromoteMergeModal polish, split schema {id_a,id_b}, E2E (absorbed D3) |
| D2-bugfix4 — Split Suggest + PMC Override | ✅ | PMC auto-calc, promote cost_basis only on receiver, suggest constraint fix |
| D2-round2 — Walktest Feedback | ⏳ | NOT ingested (still planning) |
| ~~D3 — E2E Tests~~ | ⛔ | Merged into D2-bugfix3 |

## Wiki Pages Updated
- [[decisions/cash-transfer-split-promote]] — updated (standalone endpoints eliminated → batch-only)
- [[features/F-048]] — updated (Plan D status entries, split/promote architecture)

