---
title: "Static export of constant metadata at compile-time (deferred)"
category: decision
status: open
date: 2026-05-26
tags: [backend, frontend, architecture, api-sync, transactions, metadata, performance]
related: [decisions/server-driven-type-rules, features/F-046, concepts/entity-store-pattern]
---

# Decision: Static Export of Constant Metadata at Compile-Time

## Context

Several endpoints serve constant metadata that never changes between deployments:

| Endpoint | Data | Consumer |
|----------|------|----------|
| `GET /transactions/types` | `TX_TYPE_METADATA` — type rules, swap groups | `transactionTypeStore.ts` |
| _(future)_ | Asset types enum | frontend selects/filters |
| _(future)_ | Currency codes (ISO 4217) | currency pickers |

These are true constants: they change only when the backend code changes, never at runtime. Yet today they are fetched via HTTP, costing 1 request per session per endpoint.

This decision is a direct follow-up to [[decisions/server-driven-type-rules]], which moved type rules from hardcoded frontend files to a runtime endpoint. The runtime approach works well, but the data is inherently static.

## Options Considered

1. **Keep runtime endpoints (current)** — each constant-data endpoint is called once per session, result cached in a Svelte store. Simple, already working.
2. **Static JSON export at `./dev.py api sync` time** — during the existing OpenAPI codegen step, also extract constant metadata into static JSON files (e.g. `frontend/src/lib/api/tx-type-metadata.json`). Frontend imports them as ES modules — zero HTTP calls at runtime.
3. **Bundle as TypeScript constants** — generate `.ts` files instead of `.json`, gaining type safety but coupling the generator to TypeScript.

## Decision

**Deferred to Phase 8+.** Keep the current runtime approach for now.

### Rationale

- The current cost is 1 HTTP request per session per constant endpoint — negligible.
- Static export requires:
  - A new step in `dev.py api sync` to invoke the backend, serialize metadata, and write files.
  - Refactoring `transactionTypeStore` to support both static import (dev/build) and lazy-loaded data (fallback/testing).
  - CI pipeline awareness so generated files stay in sync.
- The ROI is low until more constant-data endpoints accumulate. When there are 4-5 such endpoints, the pattern becomes worthwhile.

## Future Implementation Sketch

When implemented, the flow would be:

```
./dev.py api sync
  └─ 1. openapi codegen (existing)
  └─ 2. metadata export (new)
       ├─ Start backend in export mode
       ├─ Fetch GET /transactions/types → write tx-type-metadata.json
       ├─ Fetch GET /assets/types       → write asset-types.json
       ├─ Fetch GET /fx/currencies      → write currency-codes.json
       └─ Stop backend
```

Frontend import would look like:
```typescript
import txTypeMetadata from '$lib/api/tx-type-metadata.json';
// or: const txTypeMetadata = await import('$lib/api/tx-type-metadata.json');
```

## Consequences

- **Now**: no change, no effort. Runtime endpoints continue to work.
- **Later**: when this is implemented, the `transactionTypeStore` will need a dual-source pattern (static import for production, HTTP fetch for development hot-reload).
- **Trigger**: revisit when a 3rd or 4th constant-metadata endpoint is added.

## Source files

| Role | Path |
|------|------|
| TX_TYPE_METADATA definition | `backend/app/schemas/transactions.py` |
| Runtime type-rules endpoint | `backend/app/api/v1/transactions.py` |
| Frontend store (consumer) | `frontend/src/lib/stores/transactionTypeStore.ts` |
| Sync pipeline CLI | `dev.py` (`api sync` command) |

## Links

- [[decisions/server-driven-type-rules]] — the decision that created the runtime endpoint this would replace
- [[features/F-046]] — Transaction data model (owns TX_TYPE_METADATA)

