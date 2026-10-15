---
title: "Provider Shutdown: Generic Lifecycle vs Hardcoded"
category: decision
status: resolved
date: 2026-04-10
tags: [backend, providers, lifecycle, architecture]
related_features: [F-059, F-060, F-025]
---

# Decision: Generic Provider Shutdown Mechanism

## Context
JustETF provider uses persistent WebSocket threads for live quotes. The original `main.py` lifespan contained a hardcoded `try/except` block importing `shutdown_live_feeds` directly from the JustETF module — fragile and non-extensible.

## Problem
```python
# Old main.py — WRONG
try:
    from backend.app.services.asset_source_providers.justetf import shutdown_live_feeds
    shutdown_live_feeds()
except ImportError:
    pass
```

- Not extensible: any new provider needing cleanup required a new `try/except`
- Tight coupling between main.py and a specific provider
- Inconsistent with the Provider Registry Pattern ([[F-059]])

## Decision
Add `shutdown()` as a **no-op method in all provider ABCs**, overridden only by providers that need cleanup.

```python
# ABC (no-op by default)
class AssetSourceProvider:
    def shutdown(self) -> None:
        pass

# JustETFProvider overrides it
class JustETFProvider(AssetSourceProvider):
    def shutdown(self) -> None:
        shutdown_live_feeds()
```

`AbstractProviderRegistry.shutdown_all_providers()` iterates all registered providers and calls `shutdown()` — no `hasattr` checks needed.

The lifespan now calls, in its `providers` shutdown step (`services/platform/app_lifespan.py` since CP2b of 1.3.0):
```python
AssetProviderRegistry.shutdown_all_providers()
FXProviderRegistry.shutdown_all_providers()
BRIMProviderRegistry.shutdown_all_providers()
```

## Consequences
- Any future provider needing cleanup only needs to override `shutdown()`
- Zero changes to `main.py` for new providers
- The JustETF live-quote WebSocket also disconnects silently: [[problems/justetf-websocket-disconnect]]

## Resolved
✅ Completed 2026-04-10 — `changelog_2026-04-10_live-ticker-and-provider-lifecycle.md`

## Source files

| Role | Path |
|------|------|
| Provider registry | `backend/app/services/provider_registry.py` |
| Asset service (thread isolation) | `backend/app/services/assets/core.py` |
| FastAPI app lifecycle | `backend/app/services/platform/app_lifespan.py` |
