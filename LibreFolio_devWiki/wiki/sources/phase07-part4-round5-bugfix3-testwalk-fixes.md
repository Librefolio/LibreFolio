---
title: "Phase 07 Part 4 Round 5 Bugfix 3 — TestWalk Fixes"
category: source
source_type: plan
date_ingested: 2026-05-28
original_path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round5_Bugfix3_TestWalkFixes.prompt.md
tags: [phase07, transactions, patchable-fields, type-swap, tagInput, safeDecimal, test-split, close-confirmation, validate-chip]
related:
  - sources/phase07-part4-round5-bugfix2-testwalk-overhaul
  - features/F-048
  - features/F-047
  - concepts/safe-decimal-pattern
  - problems/dual-form-collect-duplication
---

# Source: Phase 07 Part 4 Round 5 Bugfix 3 — TestWalk Fixes

## Summary
Comprehensive bugfix round from manual testing (2026-05-02–05-04). Fixes 22/25 issues across 5 severity levels. Introduces PATCHABLE_FIELDS allowlist, backend type swap with swap_group semantics, TagInput.svelte chip input component, SafeDecimal systemic fix for scientific notation, and test infrastructure split for broker tests. 3 bugs deferred to Round 6 (R7-C1, R7-H1, R7-H2).

## Key Takeaways
- **PATCHABLE_FIELDS allowlist**: update payloads now strip immutable fields (type, broker_id, link_uuid, asset_id) before sending to backend; allowlist pattern instead of blocklist
- **Type swap in backend**: `type` added to `TXUpdateItem` with swap_group validation — only swaps within same structural group allowed (BUY↔SELL, DEPOSIT↔WITHDRAWAL, DIVIDEND↔INTEREST, TAX↔FEE); paired types locked
- **TagInput.svelte**: new chip input component with autocomplete dropdown from available tags, Enter/Space to create, X to remove
- **SafeDecimal**: systemic fix for Python Decimal scientific notation in JSON responses (see [[concepts/safe-decimal-pattern]])
- **Delete modal**: ConfirmModal for standalone delete, BulkDeleteLinkedPairModal for paired (design L1/L2 mockups but not yet built)
- **Paired title**: FormModal shows `#ID_A ↔ #ID_B` for paired transactions
- **Column ID**: `#N` monospace grey column added to main table
- **Tag badges**: colored chips using `getStringColor()` with inline styles (not CSS custom properties)
- **R7-C1 bug**: edit paired creates partner as new instead of update — deferred to Round 6
- **R7-H1 bug**: type swap qty doesn't propagate in table — deferred to Round 6
- **R7-H2 bug**: TagInput dropdown anti-bounce — deferred to Round 6
- **Test split**: separate `front-broker` runner + `brokers-detail.spec.ts` for isolation

## Wiki Pages Updated
- [[features/F-048]] — PATCHABLE_FIELDS, TagInput, type swap
- [[features/F-047]] — ID column, tag badges

