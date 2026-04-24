---
title: "MANUAL FX Provider as Sentinel"
category: decision
date: 2026
status: resolved
tags: [fx, providers, backend, sentinel]
related_features: [F-019, F-015]
---

# Decision: MANUAL FX Provider as Sentinel

## Context
Every FX pair in the system must have at least one provider assigned to it so it can appear in the pair list and be managed by the user. However, users may want to track a currency pair without any automatic data source (e.g., exotic pairs not covered by ECB/FED/BOE/SNB, or pairs managed via manual CSV upload).

## Decision
`MANUAL` is implemented as a special **sentinel** `FXRateProvider` that:
- Accepts any currency pair
- Never fetches rates from any external source (returns empty results during sync)
- Is **auto-inserted** with `priority=999` when a pair has no real providers assigned
- Is **auto-removed** when a real provider is added to the pair
- Is **re-inserted** when the last real provider is removed from the pair
- Is **hidden from the public API provider list** (`list_providers` filters it out)

## Alternatives considered
- **Require at least one real provider per pair** — rejected: blocks users from tracking pairs with no supported automatic source.
- **Allow pairs with zero providers** — rejected: creates a degenerate state where the pair has no route and sync silently does nothing with no indication.
- **Nullable provider field** — rejected: more complex query logic; sentinel is self-documenting.

## Rationale
The sentinel prevents the degenerate "pair with no provider" state while remaining invisible to end users. Auto-management (insert/remove/reinstate) means no manual intervention is needed when providers are added or removed.

## Consequences
- Backend logic that adds/removes providers must call the auto-management routines.
- `MANUAL` must be excluded from provider lists shown to users.
- Sync jobs must silently skip `MANUAL` (no error, no warning).
- `MANUAL_PRIORITY = 999` ensures real providers always take precedence.

## Related
- [[F-019]] — MANUAL Sentinel FX Provider feature
- [[F-015]] — FX Provider Registry (where providers are registered)

## Source files

| Role | Path |
|------|------|
| MANUAL provider | `backend/app/services/fx_providers/manual.py` |
| FX service (sentinel logic) | `backend/app/services/fx.py` |
| mkdocs | `mkdocs_src/docs/developer/backend/fx/architecture.md` |
