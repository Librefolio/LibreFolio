---
title: "txStore as single source of truth — eliminate prop cascade for transactions"
category: decision
status: resolved
date: 2026-05-08
tags: [frontend, transactions, stores, architecture, refactor, svelte5]
related:
  - concepts/txstore-pattern
  - concepts/entity-store-pattern
  - decisions/bulkmodal-mode-removal
  - features/F-048
  - problems/dual-form-collect-duplication
---

# Decision: txStore as Single Source of Truth for Transactions

## Context

After Round 6 Plans A/B/B1/B23, the transactions frontend had accumulated 5 categories of recurring bugs (17+ individual occurrences) all rooted in the same structural problem: transaction data existed in 3+ copies (`allMainRows` prop, `allPartnerRows` prop, internal BulkModal draft copies) that diverged after mutations. Every fix for one category introduced regressions in another.

## Options Considered

1. **Continue patching** — keep the prop cascade, add workarounds per bug category
   - Pros: no rewrite risk, immediate
   - Cons: 3 workaround layers for link_uuid alone, manutenibility declining, Piano D (Split/Promote) would require yet more branching in 3 files

2. **txStore refactor** — centralized `Map<number, TXReadItem>` populated once, components read from store
   - Pros: eliminates all 5 bug categories structurally, -30% LOC in BulkModal and +page.svelte, Piano D becomes trivial (+1 intent, ~50 LOC)
   - Cons: ~2-3 days effort, medium regression risk (mitigated by 48+ E2E tests)

## Decision

**Option 2: txStore refactor.** The recurring bug pattern made clear that the prop cascade was a structural liability, not a fixable set of individual bugs. The 48+ E2E test suite provided confidence for safe incremental migration.

## Consequences

- **Created**: `frontend/src/lib/stores/txStore.svelte.ts` (~120 LOC)
- **Created**: `frontend/src/lib/components/transactions/types.ts` (interface deduplication)
- **Simplified**: BulkModal 1766→~1200 LOC (-30%), +page.svelte 1035→~700 LOC (-30%)
- **Eliminated**: `allMainRows`/`allPartnerRows` variables and their prop drilling
- **Eliminated**: `link_uuid` generation (partners resolved via `related_transaction_id` from DB)
- **Eliminated**: manual `markEdited()` calls (status derived from diff)
- **Eliminated**: `mergePairedRows()` complexity (partners from `txStore.getPartner()`)
- **Enabled**: Piano D (Split/Promote) can be implemented as 1 new WorkspaceIntent + ~50 LOC
- **Execution order updated**: in master plan, old "Piano C" (Split/Promote) → "Piano D", txStore inserted as new "Piano C" prerequisite

## Links

- [[concepts/txstore-pattern]]
- [[concepts/entity-store-pattern]]
- Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanC_TxStoreRefactor.prompt.md`

