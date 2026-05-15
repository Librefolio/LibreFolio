---
title: "Phase 07 Part 4 Round 6 — Plan D2 Bugfix 2: Payload + Split Preview UX"
category: source
source_type: plan
date_ingested: 2026-05-31
original_path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_2_PayloadSplitPreviewUX.prompt.md
tags: [phase07, transactions, bugfix, split-preview, payload, pipeline-reorder, batch-result-ids, access-guard]
related:
  - sources/phase07-part4-round6-pland2-bugfix1
  - sources/phase07-part4-round6-pland2-bugfix3
  - features/F-048
  - features/F-046
---

# Source: Plan D2 Bugfix 2 — Payload, Split Preview, Access Guard, UX

## Summary
Bugfix 2 (completed 2026-05-13) corrected the split-in-BulkModal design: instead of removing the row (DD-BF1), split now shows editable preview rows (DD-R2.1). Also reordered backend pipeline (splits before updates), changed `TXBatchResultItem.id` to `ids: list[int]`, fixed payload issues (cost_basis_override, link_uuid), added broker access guard for promote, and fixed i18n duplicate objects.

## Key Takeaways
- **DD-R2.1 — Split preview editability** (corrects DD-BF1): split in BulkModal adds `{id}` to `pendingSplits` AND replaces the paired row with 2 standalone edit ops showing post-split types; user can edit these before commit; edits generate `updates[]` alongside `splits[]`
- **DD-R2.2 — Pipeline reorder**: splits moved before updates (`deletes(3) → splits(3b) → updates(4) → creates(5) → promotes(5c) → links(6) → balance(7)`); necessary because "split + edit post-split" requires type mutation before field updates
- **DD-R2.3 — `TXBatchResultItem.ids`**: `id: int` → `ids: list[int]`; split returns `[tx_from.id, tx_to.id]`; promote returns `[tx_a.id, tx_b.id]`; create/update/delete return `[single_id]`
- **Payload fix**: `partnerPayload` pushed raw bypassed `buildCreatePayload()` → `cost_basis_override: ""` and missing `link_uuid`; fixed by routing through `buildCreatePayload`
- **i18n fix**: duplicate `"promote": {}` objects in JSON → parser kept last, losing earlier keys
- **Access guard**: promote on VIEWER broker → backend `accessDenied`; frontend now checks `getEditableBrokers()` before allowing promote action
- **11 bugs** catalogued and fixed: M2-1 through M4-UX3

## Wiki Pages Updated
- [[features/F-048]] — updated (split preview, pipeline reorder)
- [[features/F-046]] — updated (pipeline reorder, ids[] schema)

