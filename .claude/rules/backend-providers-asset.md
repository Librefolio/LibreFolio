---
paths:
  - "backend/app/services/asset_source_providers/**"
  - "backend/app/services/assets/**"
---

# Asset Source Providers

## Architecture

All asset providers extend `AssetSourceProvider` (abstract base in `assets/base.py`) and are auto-discovered via `@register_provider(AssetProviderRegistry)`.

### Base Class

The abstract base class `AssetSourceProvider` is defined in `backend/app/services/assets/base.py`, with `AssetSourceError`. Read that file for the full contract (abstract methods, properties, return types). Key elements: `get_current_value()`, `get_history_value()`, `search()` (optional), `fetch_asset_metadata()` (optional), `params_schema` property for dynamic frontend forms.

### Thread Isolation

All provider calls go through `_run_provider_in_thread()` in `assets/core.py` — each call runs in a dedicated thread with its own event loop. Providers can use **sync I/O directly** (no `asyncio.to_thread()` needed inside providers).

### Cache Core (5 caches)

| Cache | TTL | Scope |
|-------|-----|-------|
| `asset_history_fetch` | 15 min | Smart range per-date |
| `asset_current_fetch` | 2 min | Frontend polling |
| `asset_metadata_fetch` | 30 min | Explicit refresh |
| `search_queries` | 15 min | Exact query dedup |
| `search_results` | 24h | Individual items |

`probe_provider_config()` bypasses cache (dry-run testing).

## Providers

| Provider | File | Identifier | `provider_params` | Search |
|----------|------|-----------|-------------------|--------|
| **yfinance** | `yahoo_finance/plugin.py` | Ticker (AAPL) | None | ✅ |
| **justetf** | `justetf/plugin.py` | ISIN (IE00B4L5Y983) | None | ✅ |
| **borsa_italiana** | `borsa_italiana/plugin.py` | ISIN (IT0003128367) | None | ✅ |
| **cssscraper** | `css_scraper/plugin.py` | Web page URL | `{current_css_selector, currency, decimal_format?}` | ❌ |
| **scheduled_investment** | `scheduled_investment/plugin.py` | asset_id | `FAScheduledInvestmentSchedule` | ❌ |
| **mockprov** | `mockprov/plugin.py` | any | None | ✅ (testing only, hidden from UI) |

## Adding a New Provider

1. Create the folder `backend/app/services/asset_source_providers/my_provider/` with `__init__.py` (the provider's
   docstring only, no re-export) and `plugin.py` (the code); helpers private to it go beside as `_*.py`
2. Extend `AssetSourceProvider`
3. Decorate with `@register_provider(AssetProviderRegistry)` (`AssetProviderRegistry` from `services/assets/registry.py`, the
   decorator from `services/provider_registry.py`)
4. Implement required abstract methods
5. Set `params_schema` property if provider needs extra config. Its UI texts (`assets.providerParams.my_provider.*`) live
   in the provider's own `i18n/` fragment: `./dev.py i18n add <key> --en … --it … --fr … --es …
   --into asset_source_providers/my_provider` (see skill `devpy-i18n`)
6. Add icon in `static/` directory
7. Provider is auto-discovered — no manual registration needed. Import its names, and patch them, from
   `backend.app.services.asset_source_providers.my_provider.plugin`
8. Settings (an API key, a user's preference): declare `settings_fields` and read them with `self.settings`; the core
   delivers them, the interface draws the form (Settings › Plugins, «Configure»). Labels under
   `pluginSettings.asset.my_provider.*` in the same fragment. A personal field cannot be `required`. **Never put a
   secret in `get_asset_url()`, in `cooldown_scope()`, or in a request whose host comes from `identifier` or
   `provider_params`**: any user can probe with any of them, and an asset URL is shown to users (the probe withholds
   one that shows a secret). Details: `mkdocs_src/docs/developer/architecture/patterns/plugin_settings.md`

