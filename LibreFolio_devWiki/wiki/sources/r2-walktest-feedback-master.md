---
title: "R2 Walktest Feedback Round — Master Plan (D2-Round2)"
category: source
source_type: plan
date_ingested: 2026-06-01
original_path: LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/plan-R2-WalktestFeedbackRound.prompt.md
tags: [phase07, transactions, wac, cost-basis, fx, asset-event, store-first, walktest]
related:
  - sources/r2-sp-a-cost-basis-wac
  - sources/r2-sp-b-backend-tests
  - sources/r2-sp-c-bulkmodal-suggest-ux
  - sources/phase07-part4-round6-pland-split-promote-master
  - decisions/cost-basis-currency-object
  - features/F-048
  - features/F-097
---

# Source: R2 Walktest Feedback Round — Master Plan

## Summary
Post-walktest round (2026-05-24, in-progress) addressing 3 blocking UX/feature gaps discovered during manual testing: (1) `cost_basis_override` upgraded from bare `SafeDecimal` to rich `Currency` object with FX cross-currency WAC calculation, (2) AssetEvent picker modal reusing DataEditor, (3) paired TX store-first fetch pattern. 18 steps organized into 5 sub-plans (SP-A through SP-E). SP-A/B/C complete, SP-D next, SP-E TODO.

## Key Takeaways
- **cost_basis_override → Currency object**: DB gains `cost_basis_currency VARCHAR(3)`; schema changes `Optional[SafeDecimal]` → `Optional[Currency]` (`{code, amount}`) on TXCreateItem, TXUpdateItem, TXReadItem
- **WAC with FX cross-currency**: `compute_weighted_avg_cost` rewritten with `target_currency` param; converts BUY amounts via FX rate at TX date; returns `WACResult` (wac, conversions[], missing_pairs[])
- **Target currency logic**: majority among TX currencies → asset currency on tie → alphabetical
- **WACResult propagation**: `wac_info: Optional[WACResult]` added to `TXBatchResultItem`; available in commit/promote response (NOT in GET /transactions)
- **recalc-wac endpoint**: `POST /transactions/recalc-wac` — accepts `{tx_ids}`, validates same-asset constraint, recalculates WAC for TRANSFER receivers
- **AssetEvent picker modal** (SP-D): reuses DataEditor from asset detail tab, radio selection, Δ days slider, date constraint, Import CSV + Add row
- **Paired TX store-first** (SP-D): `txStoreGet` first, GET in parallel, reactive update, silent fallback
- **BulkModal suggest overhaul** (SP-C): subtractive filter (exclude ops already in grid), human-readable format, lightbulb per-row icon, multi-match nested sub-list
- **PromoteMergeModal simplified** (SP-C): date and cost_basis fields removed — resolved in FormModal post-promote
- **Old format rejected**: bare `SafeDecimal` string for cost_basis → 422 (no backward compat)
- **Backend tests**: 13 WAC tests (WAC-1→WAC-13) + 11 financial-utils tests (P1→P11) in dedicated file

## Sub-plan chain
| Sub-plan | Status | Focus | Commit |
|----------|--------|-------|--------|
| SP-A — Cost Basis Currency + WAC Service | ✅ | DB + schema + service + recalc-wac endpoint | `92f4b1ba` |
| SP-B — Backend Tests | ✅ | 13 WAC tests + mock data + financial-utils tests | `473d2611` |
| SP-C — BulkModal Suggest UX | ✅ | Toolbar, split preview, suggest overhaul, PromoteMergeModal, ActionModal, E2E | multiple commits |
| SP-C Bugfix 1-11 | ✅ | WAC Preview modal + 11 walktest bugs | 2026-05-30 |
| SP-D — FormModal Features | ⏳ | CompactCash, AssetEvent picker, WAC Info modal, store-first | NEXT |
| SP-E — E2E Tests | 🔲 | Full E2E coverage for all WAC/suggest/picker features | TODO |

## Coherence issues identified
| # | Problem | Resolution |
|---|---------|-----------|
| C1 | cost_basis SafeDecimal → Currency breaks existing tests | SP-A+B |
| C2 | compute_weighted_avg_cost return type change | SP-A+B |
| C3 | Zero test for auto-calc WAC on TRANSFER create | WAC-2 |
| C4 | Zero test for WAC cross-currency FX | WAC-3, WAC-4 |
| C5 | Zero E2E for split BulkModal, lightbulb, WAC Info | SP-E |

## Wiki Pages Created/Updated
- [[features/F-097]] — NEW: WAC (Weighted Average Cost) feature
- [[decisions/cost-basis-currency-object]] — NEW: cost_basis as Currency decision
- [[features/F-048]] — updated (R2 walktest feedback status entries)
