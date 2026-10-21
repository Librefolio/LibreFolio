---
paths:
  - "backend/app/services/fx_providers/**"
  - "backend/app/services/fx/**"
---

# FX Providers

## Architecture

All FX providers extend `FXRateProvider` (abstract base in `services/fx/base.py`) and are auto-discovered via `@register_provider(FXProviderRegistry)`; the registry lives in `services/fx/registry.py`, the decorator in `services/provider_registry.py`.

Each provider represents a central bank or financial data source that provides exchange rates.

## Providers

| Provider | File | Code | Base Currency | Source |
|----------|------|------|---------------|--------|
| **ECB** | `ecb/plugin.py` | `ECB` | EUR | XML feed |
| **FED** | `fed/plugin.py` | `FED` | USD | JSON API |
| **BOE** | `boe/plugin.py` | `BOE` | GBP | JSON API |
| **SNB** | `snb/plugin.py` | `SNB` | CHF | JSON API |
| **MANUAL** | `manual/plugin.py` | `MANUAL` | Any | Sentinel (no sync) |

## MANUAL Provider (Sentinel)

The MANUAL provider is a special sentinel that handles pairs not covered by any real provider:
- **Auto-insert**: When a pair has no real provider, MANUAL is assigned with priority=999
- **Auto-remove**: When a real provider is added for the pair, MANUAL is removed
- **Auto-reinstate**: When the last real provider is removed, MANUAL is re-added
- Hidden from the public API list (`list_providers` filters it out)

## Multi-Provider Fallback

FX pairs can have multiple providers with priority ordering. When syncing rates, the system tries providers in priority order (lower = higher priority). If ECB fails, it falls back to FED, then BOE, then SNB.

## Adding a New FX Provider

The abstract base class `FXRateProvider` is defined in `backend/app/services/fx/base.py`. Read that file for the full contract.

1. Create the folder `backend/app/services/fx_providers/my_bank/` with `__init__.py` (the provider's docstring only,
   no re-export) and `plugin.py` (the code); import its names, and patch them, from `….fx_providers.my_bank.plugin`
2. Extend `FXRateProvider` (from `services/fx/base.py`)
3. Decorate with `@register_provider(FXProviderRegistry)` (`FXProviderRegistry` from `services/fx/registry.py`)
4. Implement the required abstract methods and properties (see base class)
5. Add icon in `static/` directory
6. Set `docs_url` property for documentation link

