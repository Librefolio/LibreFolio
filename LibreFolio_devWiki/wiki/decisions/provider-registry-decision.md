---
title: "Provider Auto-Discovery via Decorator Registry"
category: decision
date: 2026
status: resolved
tags: [backend, providers, architecture, extensibility]
related_features: [F-059, F-015]
---

# Decision: Provider Auto-Discovery via Decorator Registry

## Context
LibreFolio has three provider families: FX providers (central banks), Asset source providers (yfinance, JustETF, CSS Scraper), and BRIM broker import plugins. Each family needs a way to enumerate available providers at runtime. We needed to decide how providers register themselves.

## Decision
Use a `@register_provider(Registry)` decorator pattern for **auto-discovery**. Each provider class decorates itself with `@register_provider(FXProviderRegistry)` (or the appropriate registry), and the registry auto-discovers all providers in the corresponding `*_providers/` folder via import-time side effects.

## Alternatives considered
- **Config file (YAML/TOML listing provider classes)** — rejected: config files drift from code; adding a provider requires editing two separate files (the class + the config).
- **Manual list in a central file** — rejected: same drift problem; easy to forget to register; creates a coupling point that must be updated for every new provider.
- **Plugin entry points (setuptools)** — rejected: overkill for a monorepo; adds packaging complexity with no benefit.

## Rationale
The decorator is co-located with the class — you cannot create a provider without also registering it. This makes adding a provider a purely self-contained, single-file operation. The registry pattern also enables runtime introspection (list available providers, get by code, validate config).

## Consequences
- All provider files must be imported at startup for registration to occur (ensured by the `*_providers/` folder scan).
- Provider codes must be unique within each registry.
- The `params_schema` property on providers drives dynamic frontend forms — this is only possible because the registry exposes provider metadata at runtime.

## Related
- [[F-059]] — Provider Registry Pattern (the feature implementing this decision)
- [[F-015]] — FX Provider Registry (FX application of this pattern)

## Source files

| Role | Path |
|------|------|
| Provider registry | `backend/app/services/provider_registry.py` |
| FX abstract base | `backend/app/services/fx.py` |
| Asset abstract base | `backend/app/services/asset_source.py` |
| BRIM abstract base | `backend/app/services/brim_provider.py` |
| mkdocs | `mkdocs_src/docs/developer/architecture/patterns/registry_pattern.md` |
