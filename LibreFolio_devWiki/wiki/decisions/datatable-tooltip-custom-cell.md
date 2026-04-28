---
title: "DataTable Tooltip via CustomCell — no title= HTML attribute"
category: decision
tags: [frontend, datatable, tooltip, svelte5, ux]
status: active
date: 2026-04-28
related:
  - features/F-047
  - sources/phase07-part4-round2
---

# Decision: DataTable Tooltip via CustomCell (not title="")

## Status: Active

## Context

Early cells in the TransactionsTable used `title="..."` HTML attributes for tooltip text (native browser tooltip). In Round 2, feedback item R2-2 noted that browser native tooltips conflict with `<Tooltip.svelte>` (the LibreFolio component). Both show simultaneously or fight for display, producing overlapping/broken UX. `title` also has a variable appearance delay and can't be styled.

## Decision

**All tooltips inside DataTable cells MUST use `<Tooltip.svelte>` via a `CustomCell` snippet.** `title=""` attributes are prohibited on interactive DataTable cell content.

## Implementation Pattern

```svelte
<!-- In column definition (DataTable columnDefs array): -->
{
    key: 'transaction_type',
    cell: {
        type: 'custom',
        snippet: txTypeCell,    // Svelte snippet
    }
}

<!-- In the .svelte file (snippet definition): -->
{#snippet txTypeCell(row)}
    <Tooltip.svelte>
        {#snippet trigger()}
            <TxTypeIconCell type={row.transaction_type} />
        {/snippet}
        {#snippet content()}
            {txLabel(row.transaction_type)}
        {/snippet}
    </Tooltip.svelte>
{/snippet}
```

## Exceptions

- `title=""` is acceptable on non-DataTable content (regular page elements where native tooltip is fine)
- Purely decorative content with no interactive/hover intent may omit tooltip entirely

## Affected Files

- `frontend/src/lib/components/transactions/TransactionsTable.svelte` — all custom cells use Tooltip.svelte
- `frontend/src/lib/components/table/DataTable.svelte` — `CustomCell` snippet support

## Source

R2-2 decision documented in:
`LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round2-tableRefactorBugfix.prompt.md`, Round 2 Step 2.
