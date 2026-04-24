---
title: "BRIM Fake Asset ID during Parse"
category: decision
date: 2026
status: resolved
tags: [brim, brokers, transactions, import]
related_features: [F-012]
---

# Decision: BRIM Fake Asset ID during Parse

## Context
When a user imports a broker report, the file often references assets (by ticker, ISIN, name) that may not yet exist in the LibreFolio database. We needed a way to represent transactions referencing unknown assets during the parse phase, before the user has mapped them to real assets.

## Decision
BRIM plugins emit **negative integers** as fake asset IDs during parsing. These are never real `asset_id` values (which are always positive). The frontend's matching wizard then maps each fake ID to a real asset before final import.

The schema helper `is_fake_asset_id(v)` checks `v < 0` to distinguish fake from real IDs throughout the codebase.

## Alternatives considered
- **Require asset pre-creation** — rejected: creates friction; users must know all assets upfront before importing.
- **Store by ISIN/ticker string** — rejected: not all brokers provide ISIN, some only provide names; not uniformly available.
- **Use None/null** — rejected: makes grouping and matching logic harder (all unknowns would collapse to one group).

## Rationale
Negative integers are unambiguous (no collision with real IDs), easy to detect, sortable, and allow each unknown asset to be a distinct entity in the matching UI. The two-phase approach (parse → match → import) lets users import files before assets exist in the DB.

## Consequences
- Fake IDs must never be persisted to the `Transaction` table — the import service must validate all IDs are positive before writing.
- Frontend must handle fake IDs in the matching wizard and substitute real IDs before calling `POST /transactions`.
- `is_fake_asset_id()` helper must be used consistently in validation logic.

## Related
- [[F-012]] — BRIM Framework (the feature this decision belongs to)

## Source files

| Role | Path |
|------|------|
| BRIM abstract base (fake ID flow) | `backend/app/services/brim_provider.py` |
| BRIM plugins directory | `backend/app/services/brim_providers/` |
| mkdocs | `mkdocs_src/docs/developer/backend/brim/architecture.md` |
