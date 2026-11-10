---
title: "Provider Auto-Discovery via Decorator Registry"
category: decision
date: 2026
status: resolved
tags: [backend, providers, architecture, extensibility]
related_features: [F-059, F-015]
related: [features/F-059, features/F-015, decisions/plugin-folders-and-split-i18n]
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
- [[F-106]] — the Tool platform reuses the discovery for `tool_plugins/` but changes the collision rule: every claimant
  of a duplicate code is quarantined, and a failed import leaves no partial registration
  ([[decisions/tool-contract-from-pydantic-compiled-renderer]])
- *Delivered on 2026-10-12* (U-1, `0848f26bf`; the translations with U-2 and U-3): every plugin is a folder,
  `<plugin>/plugin.py` loaded by convention (`PLUGIN_MODULE_NAME`), with its own translations —
  [[decisions/plugin-folders-and-split-i18n]]
- *2026-11-07 lint:* the signal and risk plugin families use the same base (`AbstractPluginRegistry`, `@register_plugin`) —
  [[decisions/signal-backend-plugin-architecture]]

## Source files

| Role | Path |
|------|------|
| Provider registry | `backend/app/services/provider_registry.py` |
| FX abstract base | `backend/app/services/fx/base.py` |
| Asset abstract base | `backend/app/services/assets/base.py` |
| BRIM abstract base | `backend/app/services/brim/brim_provider.py` |
| mkdocs | `mkdocs_src/docs/developer/architecture/patterns/registry_pattern.md` |
