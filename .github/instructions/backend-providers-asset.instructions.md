---
applyTo: "backend/app/services/asset_source_providers/**,backend/app/services/asset_source.py"
---

# Asset Source Providers

## Architecture

All asset providers extend `AssetSourceProvider` (abstract base in `asset_source.py`) and are auto-discovered via `@register_provider(AssetProviderRegistry)`.

### Base Class

The abstract base class `AssetSourceProvider` is defined in `backend/app/services/asset_source.py`. Read that file for the full contract (abstract methods, properties, return types). Key elements: `get_current_value()`, `get_history_value()`, `search()` (optional), `fetch_asset_metadata()` (optional), `params_schema` property for dynamic frontend forms.

### Thread Isolation

All provider calls go through `_run_provider_in_thread()` in `asset_source.py` — each call runs in a dedicated thread with its own event loop. Providers can use **sync I/O directly** (no `asyncio.to_thread()` needed inside providers).

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
| **yfinance** | `yahoo_finance.py` | Ticker (AAPL) | None | ✅ |
| **justetf** | `justetf.py` | ISIN (IE00B4L5Y983) | None | ✅ |
| **borsa_italiana** | `borsa_italiana.py` | ISIN (IT0003128367) | None | ✅ |
| **cssscraper** | `css_scraper.py` | Web page URL | `{current_css_selector, currency, decimal_format?}` | ❌ |
| **scheduled_investment** | `scheduled_investment.py` | asset_id | `FAScheduledInvestmentSchedule` | ❌ |
| **mockprov** | `mockprov.py` | any | None | ✅ (testing only, hidden from UI) |

## Adding a New Provider

1. Create `backend/app/services/asset_source_providers/my_provider.py`
2. Extend `AssetSourceProvider`
3. Decorate with `@register_provider(AssetProviderRegistry)`
4. Implement required abstract methods
5. Set `params_schema` property if provider needs extra config
6. Add icon in `static/` directory
7. Provider is auto-discovered — no manual registration needed

