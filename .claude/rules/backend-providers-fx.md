---
paths:
  - "backend/app/services/fx_providers/**"
  - "backend/app/services/fx/**"
---

# FX Providers

## Architecture

All FX providers extend `FXRateProvider` (abstract base in `services/fx/base.py`) and are auto-discovered via `@register_provider(FXProviderRegistry)`; the registry lives in `services/fx/registry.py`, the decorator in `services/platform/provider_registry.py`.

Each provider represents a central bank or financial data source that provides exchange rates.

## Providers

| Provider | File | Code | Base Currency | Source |
|----------|------|------|---------------|--------|
| **ECB** | `ecb/plugin.py` | `ECB` | EUR | SDMX JSON, one request per currency |
| **FED** | `fed/plugin.py` | `FED` | USD | FRED CSV, one series per currency (each declares its direction) |
| **BOE** | `boe/plugin.py` | `BOE` | GBP | IADB CSV, one series per currency |
| **SNB** | `snb/plugin.py` | `SNB` | CHF | JSON cube, monthly averages |
| **BDI** | `bdi/plugin.py` | `BDI` | EUR | JSON time series per currency (~149), convention C checked |
| **BCB** | `bcb/plugin.py` | `BCB` | USD | PTAX CSV per currency (fixed `ChkMoeda` table, `_parse.py`), BRL from the USD cotação |
| **NORGES** | `norges/plugin.py` | `NORGES` | NOK | SDMX CSV, every currency in one request |
| **NBU** | `nbu/plugin.py` | `NBU` | UAH | JSON range per currency, every day incl. weekends |
| **BOC** | `boc/plugin.py` | `BOC` | CAD | Valet JSON, one group request |
| **BANXICO** | `banxico/plugin.py` | `BANXICO` | MXN | SIE JSON, every series in one request; free token (`token`, a secret setting, in a header) |
| **CNB** | `cnb/plugin.py` | `CNB` | CZK | Text fixing, one `year.txt` per year, units from the header |
| **SARB** | `sarb/plugin.py` | `SARB` | ZAR | JSON series per currency, three at once |
| **BOK** | `bok/plugin.py` | `BOK` | KRW | ECOS JSON, one series per currency, three at once; free key (`api_key`, in the URL path: never log a URL) |
| **MANUAL** | `manual/plugin.py` | `MANUAL` | Any | Sentinel (no sync) |

A provider's note (`warning_i18n`) has a level, `warning_level`: `"warning"` (⚠️, a data limit that can mislead: SNB,
BOC, BDI, SARB, BOK) or `"info"` (ℹ️, a fact worth knowing: FED, NORGES, NBU, BCB, BANXICO, CNB). Unit and direction tests: one
`test_fx_<code>*.py` per provider, registered in `services provider-errors`; answers are synthetic, never downloaded.

## MANUAL Provider (Sentinel)

The MANUAL provider is a special sentinel that handles pairs not covered by any real provider:
- **Auto-insert**: When a pair has no real provider, MANUAL is assigned with priority=999
- **Auto-remove**: When a real provider is added for the pair, MANUAL is removed
- **Auto-reinstate**: When the last real provider is removed, MANUAL is re-added
- Hidden from the public API list (`list_providers` filters it out)

## Multi-Provider Fallback

FX pairs can have multiple providers with priority ordering. When syncing rates, the system tries providers in priority order (lower = higher priority). The order is the user's: each route has a priority.

## Adding a New FX Provider

The abstract base class `FXRateProvider` is defined in `backend/app/services/fx/base.py`. Read that file for the full contract.

1. Create the folder `backend/app/services/fx_providers/my_bank/` with `__init__.py` (the provider's docstring only,
   no re-export) and `plugin.py` (the code); import its names, and patch them, from `….fx_providers.my_bank.plugin`
2. Extend `FXRateProvider` (from `services/fx/base.py`)
3. Decorate with `@register_provider(FXProviderRegistry)` (`FXProviderRegistry` from `services/fx/registry.py`)
4. Implement the required abstract methods and properties (see base class)
5. Add icon in `static/` directory
6. Set `docs_url` property for documentation link

