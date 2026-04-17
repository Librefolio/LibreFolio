---
applyTo: "backend/app/services/fx_providers/**,backend/app/services/fx.py"
---

# FX Providers

## Architecture

All FX providers extend `FXProvider` (abstract base in `fx.py`) and are auto-discovered via `@register_provider(FXProviderRegistry)`.

Each provider represents a central bank or financial data source that provides exchange rates.

## Providers

| Provider | File | Code | Base Currency | Source |
|----------|------|------|---------------|--------|
| **ECB** | `ecb.py` | `ECB` | EUR | XML feed |
| **FED** | `fed.py` | `FED` | USD | JSON API |
| **BOE** | `boe.py` | `BOE` | GBP | JSON API |
| **SNB** | `snb.py` | `SNB` | CHF | JSON API |
| **MANUAL** | `manual.py` | `MANUAL` | Any | Sentinel (no sync) |

## MANUAL Provider (Sentinel)

The MANUAL provider is a special sentinel that handles pairs not covered by any real provider:
- **Auto-insert**: When a pair has no real provider, MANUAL is assigned with priority=999
- **Auto-remove**: When a real provider is added for the pair, MANUAL is removed
- **Auto-reinstate**: When the last real provider is removed, MANUAL is re-added
- Hidden from the public API list (`list_providers` filters it out)

## Multi-Provider Fallback

FX pairs can have multiple providers with priority ordering. When syncing rates, the system tries providers in priority order (lower = higher priority). If ECB fails, it falls back to FED, then BOE, then SNB.

## Adding a New FX Provider

The abstract base class `FXProvider` is defined in `backend/app/services/fx.py`. Read that file for the full contract.

1. Create `backend/app/services/fx_providers/my_bank.py`
2. Extend `FXProvider` (from `fx.py`)
3. Decorate with `@register_provider(FXProviderRegistry)`
4. Implement the required abstract methods and properties (see base class)
5. Add icon in `static/` directory
6. Set `docs_url` property for documentation link

