---
title: "Phase 07 Part 4 Round 6 — Plan D2 Bugfix 4: Split Suggest, PMC Override, UX"
category: source
source_type: plan
date_ingested: 2026-05-31
original_path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_4_SplitSuggestPmcOverrideUx.prompt.md
tags: [phase07, transactions, bugfix, pmc-auto-calc, cost-basis-override, promote-suggest, split-payload, link-uuid, slider, ux]
related:
  - sources/phase07-part4-round6-pland2-bugfix3
  - sources/phase07-part4-round6-pland-split-promote-master
  - features/F-048
  - features/F-046
---

# Source: Plan D2 Bugfix 4 — Split Suggest, PMC Override, UX

## Summary
Bugfix 4 (completed 2026-05-14, ~20h) addressed PMC auto-calculation on TRANSFER creates, cost_basis_override semantics (only on receiver), promote-suggest constraint fix (None amount/qty skipped instead of failing), split payload fixes for both Main Table and BulkModal, link_uuid synchronization after edit+apply, delta-days slider UX, and documentation updates.

## Key Takeaways
- **B1 (P0) — PMC auto-calc on TRANSFER create**: new helper `compute_weighted_avg_cost(session, broker_id, asset_id, as_of_date) → Decimal | None`; queries BUY TXs + incoming TRANSFERs with frozen cost_basis; computes weighted average; auto-assigned to receiver (qty>0) when `cost_basis_override` is null at commit time
- **B2 (P0) — Promote cost_basis_override only on receiver**: previously applied to both TX sides; now only set on TX with qty>0; sender (qty<0) forced to null. On promote to TRANSFER, if receiver has no override → auto-calc via `compute_weighted_avg_cost`
- **B3 (P1) — Promote-suggest constraint fix**: `_PromoteCandidate.amount = Decimal("0")` when `inp.amount is None` caused constraint `cash_amount: opposite` to always fail. Fix: if amount/quantity is None, skip that constraint (can't verify, don't fail)
- **B4 (P0) — Main table split payload**: `confirmSplit()` sent `{id}` → now sends `{id_a, id_b}` (matching bugfix3 schema change)
- **B5 (P0) — BulkModal split saved**: no longer mutates `fields.type`; adds to `pendingSplits` only; badge purple "✂️ split"; column shows "TYPE → ✂️ TARGET"; undo-split action removes from pendingSplits and restores paired display; commit loop skips ops with txId in `splitTxIds`
- **B6 (P0) — link_uuid sync**: `patchDualRowFromForm` and `addDualRowFromForm` now force shared link_uuid between main and partner after apply
- **B7–B9 (P1) — Promote-suggest fixes**: tolerance_days now uses `maxDeltaDays` (was hardcoded 7); inputs now include `amount`/`quantity`; `lastSuggestKey` invalidated after apply/split/promote/undo
- **B10 (P1) — Broker lost in edit paired**: `applyPartnerToDualTo` investigated; resolved via B11 improvements
- **B11 (P1) — cost_basis_override in FormModal**: `applyPartnerToDualTo` now copies override correctly; frontend forces null on sender side in promote
- **B12 (P2) — Delta-days slider**: range 0-14 instead of number input; `accent-libre-green`; font-mono display
- **B18 (P2) — Warning UI for ADJUSTMENT**: InfoBanner variant=warning when type=ADJUSTMENT, qty>0, cost_basis_override empty: "No cost basis set — lot will be created with zero cost"
- **B17 (P2) — Docs**: `adjustment.en.md` expanded with "Automatic Cost Basis on Transfers" section documenting WAC formula and manual override scenarios
- **18 bugs** catalogued: 4 P0, 6 P1, 5 P2, 3 P3

## Deviations from plan
- Step 6: BulkModal split — types NOT mutated per plan; backend handles via `splits[]` (aligned with intent)
- Step 9: Broker regression — resolved via B11 improvements, no separate fix needed
- Step 14: Tooltip with docs link — deferred (requires Tooltip refactoring for clickable links)

## Wiki Pages Updated
- [[features/F-048]] — updated (PMC auto-calc, split preview, suggest fixes)
- [[features/F-046]] — updated (PMC auto-calc, cost_basis semantics)

