---
title: "BRIM Positive High Fake Asset IDs during Parse"
category: decision
date: 2026
status: resolved
tags: [brim, brokers, transactions, import]
related:
  - features/F-012
  - features/F-049
  - entities/import-wizard-modal
mkdocs: "developer/backend/brim/architecture.md"
---

# Decision: BRIM Positive High Fake Asset IDs during Parse

## Context
When a user imports a broker report, the file often references assets (by ticker, ISIN, name) that may not yet exist in the LibreFolio database. We needed a way to represent transactions referencing unknown assets during the parse phase, before the user has mapped them to real assets.

## Decision
BRIM plugins emit temporary IDs from a reserved **positive high range**. The first
placeholder is `FAKE_ASSET_ID_BASE = 2**31 - 1`; subsequent placeholders decrement.
The frontend matching flow maps them to real asset IDs before handing drafts to the
bulk editor.

The backend helper recognizes values at or above `FAKE_ASSET_ID_BASE - 10000`; the
frontend mirrors that range in `isFakeAssetId.ts`.

## Alternatives considered
- **Require asset pre-creation** — rejected: creates friction; users must know all assets upfront before importing.
- **Store by ISIN/ticker string** — rejected: not all brokers provide ISIN, some only provide names; not uniformly available.
- **Use None/null** — rejected: makes grouping and matching logic harder (all unknowns would collapse to one group).

## Rationale
The reserved high range is easy to detect and allows each unresolved instrument to
remain distinct during review. Since every parser starts at the same base for each file,
the multi-file merge remaps per-file placeholders into one wizard-global sequence before
asset grouping. The two-phase approach (parse → resolve → stage) lets the user inspect,
link, or explicitly create assets before any transaction is committed.

## Consequences
- Fake IDs must never be persisted to the `Transaction` table.
- The frontend must substitute real IDs before handing selected transactions to the bulk editor.
- `is_fake_asset_id()` helper must be used consistently in validation logic.
- A unique current candidate may be selected automatically; ambiguity remains a manual decision.

## Related
- [[F-012]] — BRIM Framework (the feature this decision belongs to)

## Source files

| Role | Path |
|------|------|
| Fake-ID constant and backend detector | `backend/app/schemas/brim.py` |
| Frontend detector | `frontend/src/lib/utils/brim/isFakeAssetId.ts` |
| Per-file fake-ID allocation example | `backend/app/services/brim_providers/broker_generic_csv.py` |
| Multi-file global remapping | `frontend/src/lib/utils/transactions/importMerge.ts` |
| Resolution and final substitution | `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` |
| mkdocs | `mkdocs_src/docs/developer/backend/brim/architecture.md` |
