---
title: "GET /brokers response shape drift: bare list → BRListResponse{items, inaccessible}"
category: problem
status: resolved
date: 2026-07-13
tags: [backend, frontend, api-contract, testing, brokers]
related: []
---

# Problem: Several Callers Still Treated `/brokers` as a Bare Array

## Summary

`BrokerService.get_all()` (and the `GET /api/v1/brokers` endpoint that returns it directly)
was changed at some point to return `BRListResponse` — `{items: BRReadItem[], inaccessible:
BRDiscoveryItem[]}` — to support the broker-sharing "discover brokers you don't have access
to" feature. Several call sites, written against the older bare-list contract, were never
updated and broke in different ways depending on how they consumed the response:

- `backend/test_scripts/test_services/test_broker_service.py` — `isinstance(result, list)`
  failed outright (`AssertionError`); `for b in result` silently iterated Pydantic's own
  `(field_name, value)` tuples instead of `items`, since `BaseModel.__iter__` yields field
  tuples, not raising an error — a much sneakier failure mode than a `TypeError`.
- `frontend/e2e/transactions/tx-bulk-suggest-ux.spec.ts` — `data.filter(...)` threw
  `TypeError: data.filter is not a function` (a plain object has no `.filter`).
- `frontend/e2e/portfolio/broker-icons.spec.ts` — `brokers.map(...)` threw the same way,
  inside a `page.route()` handler; the thrown error broke the mocked response, so the request
  silently fell through to the real backend (no crash visible to the test — see the tab/route
  fix in the same file's history for how this was actually diagnosed).

## Fix Pattern

Wherever a caller treats the `/brokers` JSON as `Array<...>`, change it to read `.items`
(and optionally `.inaccessible` if it needs the discovery list):

```ts
// before
const data = (await resp.json()) as Array<{id: number; ...}>;
data.filter(...)

// after
const data = (await resp.json()) as {items: Array<{id: number; ...}>};
data.items.filter(...)
```

When *patching* a mocked response (not just reading it), preserve the wrapper shape:

```ts
await route.fulfill({response, json: {...brokers, items: patchedItems}});
```

## Prevention

`get_all()` has an explicit return type (`-> BRListResponse`) and a docstring — the drift
happened because call sites outside the typed API-client path (raw `fetch`/`page.request`
calls in tests, or unit tests calling the service directly) aren't caught by TypeScript/mypy.
Prefer the generated Zodios client over raw `fetch` in E2E tests when hitting endpoints whose
response shape can evolve.

## Source files

| Role | Path |
|------|------|
| Contract | `backend/app/schemas/brokers.py` (`BRListResponse`) |
| Producer | `backend/app/services/broker_service.py::get_all` |
| Fixed (backend) | `backend/test_scripts/test_services/test_broker_service.py` |
| Fixed (frontend) | `frontend/e2e/transactions/tx-bulk-suggest-ux.spec.ts`, `frontend/e2e/portfolio/broker-icons.spec.ts` |
