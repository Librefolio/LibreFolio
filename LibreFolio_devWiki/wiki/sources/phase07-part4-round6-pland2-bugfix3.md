---
title: "Phase 07 Part 4 Round 6 — Plan D2 Bugfix 3: UX Modal + Payload + Suggest + E2E"
category: source
source_type: plan
date_ingested: 2026-05-31
original_path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_3_UXModalPayloadSuggestE2E.prompt.md
tags: [phase07, transactions, bugfix, promote-merge-modal, split-schema, suggest-banner, e2e, validate-scheduler, cash-sign, d3-absorbed]
related:
  - sources/phase07-part4-round6-pland2-bugfix2
  - sources/phase07-part4-round6-pland2-bugfix4
  - features/F-048
  - features/F-046
---

# Source: Plan D2 Bugfix 3 — UX Modal Unification, Payload, Suggest, E2E

## Summary
Biggest bugfix round (completed 2026-05-14, ~16h). Absorbed D3 E2E scope. Key changes: split schema changed from `{id}` to `{id_a, id_b}` with pair validation, validate scheduler payload fix (bypassed `buildCreatePayload`), cash sign rendering fix in BulkModal grid, suggest banner redesign with delta-days and icons, PromoteMergeModal polish, TransactionActionModal unified layout for split/promote, and full E2E test suite.

## Key Takeaways
- **Split schema change**: `TXSplitBatchItem{id: int}` → `{id_a: int, id_b: int}` with `@model_validator` requiring `id_a != id_b`; both IDs of the pair must be provided for explicit validation
- **Validate scheduler payload fix** (R3-1): validate scheduler at line ~811 pushed `partnerPayload` raw → bypassed `buildCreatePayload()` → `cost_basis_override: ""` and missing `link_uuid`. Fixed by routing through `buildCreatePayload` (same fix applied to `commit()` and `getBulkContextExcluding()` already existed)
- **Cash sign rendering** (R3-2): `fieldsFromTx()` normalizes amounts to abs() for form editing (user enters positive, rule applies sign). BulkModal grid column showed normalized (+500 for WITHDRAWAL). Fix: reconstruct display sign before rendering based on `rule.cashSign`
- **PromoteMergeModal polish** (R3-5, R3-6): green background, footer buttons, textarea auto-grow (`field-sizing: content`), TagInput reuse, global buttons (All Left/Merge/All Right)
- **Suggest banner redesign** (R3-7): `<ul>` with bullet points, format "Merge TYPE (icon) and TYPE (icon) → TargetLabel (icon) (Δ Nd)", delta-days display
- **TransactionActionModal unification** (R3-4): unified tabular layout for split/promote confirmation modals (matching DeleteModal's detail level)
- **D3 absorbed**: E2E test suite for split/promote completed as part of this bugfix round; `tx-split-promote.spec.ts` with 10 scenarios
- **DB populate validation** (R3-8): added post-populate balance validation via service layer to catch inconsistent mock data early
- **link_uuid divergence** (embedded in walktest): edit + apply on paired TX caused link_uuid divergence between main and partner → tracked for fix in bugfix4
- **8 bugs** catalogued: 3 P0, 4 P1, 1 P2

## Wiki Pages Updated
- [[features/F-048]] — updated (bugfix 3 status, split schema, E2E absorbed)
- [[features/F-046]] — updated (split schema, pipeline changes)

