# 🧹 Cache Registry & Admin Endpoints

Backend services cache provider responses and computed aggregates in **named TTL caches** built
on [theine](https://github.com/Yiling-J/theine) (Rust-backed core). A small registry in
`backend/app/utils/cache_utils.py` tracks every cache by name, and three endpoints under
`/api/v1/settings/cache/*` expose that registry to the UI.

## 🧱 The named-cache registry

Services obtain a cache through the registry, never by constructing one ad hoc:

```python
from backend.app.utils.cache_utils import get_ttl_cache

_fx_fetch_cache = get_ttl_cache("fx_provider_responses", maxsize=200, ttl=300)
```

`get_ttl_cache(name, maxsize, ttl)` returns a process-global `NamedCache` — a thin wrapper
around `theine.Cache` that binds a default TTL and exposes metadata for the admin views:

- `cache.set(key, value)` / `value, ok = cache.get(key)` / `cache.delete(key)` /
  `cache.clear()` / `len(cache)`;
- `cache.maxsize` / `cache.ttl` for stats.

**Why theine**: W-TinyLFU eviction (adaptive LRU/LFU) when `maxsize` is reached, per-item TTL
on write with expiry handled by a hierarchical timer wheel (no scanning), thread-safe by
default including free-threaded Python 3.13.6+.

!!! warning "`clear()` rebuilds the cache instance — by design"

    theine's own `clear()` empties the entry map but leaves the W-TinyLFU admission filter
    loaded with the frequencies of the dropped keys: once a cache has filled up at least once,
    later `set()` calls are refused against those ghosts and the cache silently stops storing
    (measured on theine 2.0.0). `NamedCache.clear()` therefore swaps in a fresh `Cache` and
    closes the old one (so its timer-wheel thread does not leak). Do not reach for
    `cache._cache.clear()` directly.

Registry-level helpers: `clear_cache(name)`, `clear_all_caches()`, `list_caches()` /
`get_cache_stats(name)` (stats for the admin views), and `close_all_caches()` — called at
application shutdown to stop the timer-wheel threads.

### 🗂️ Caches registered today

Caches register lazily at import time, so the list below is the full registry as of 2026-09-03
(grep `get_ttl_cache(` under `backend/app` to re-derive it):

| Cache | maxsize | TTL | Owner |
|-------|--------:|----:|-------|
| `search_results` | 5000 | 24 h | `asset_source` — individual search items |
| `search_queries` | 500 | 15 min | `asset_source` — query → results |
| `asset_history_fetch` | 500 | 15 min | `asset_source` |
| `asset_current_fetch` | 300 | 2 min | `asset_source` |
| `asset_metadata_fetch` | 200 | 30 min | `asset_source` |
| `fx_provider_responses` | 200 | 5 min | `fx` |
| `portfolio_blob` | 30 | 24 h | `portfolio_engine` |
| `portfolio_layer2` | 20 | 30 min | `portfolio_service` |
| `portfolio_wac` | 200 | 1 h | `portfolio_service` |
| `upload_metadata` | 500 | 1 h | `static_uploads` |
| `justetf_overview` / `justetf_chart` | 500 | 1 h | justETF provider |
| `justetf_etf_list` | 100 | 1 h | justETF provider |
| `yfinance_currency` | 2000 | 24 h | Yahoo Finance provider |
| `scheduled_investment` | 256 | 48 h | scheduled-investment provider |
| `risk_optimization` / `risk_simulation` | 32 | 30 min | risk quant engines |

## 🌐 The three admin endpoints

Defined in `backend/app/api/v1/settings.py`; schemas (`CacheStatusEntry`,
`CacheStatusResponse`, `CacheClearResponse`) live in `backend/app/schemas/settings.py`.

| Endpoint | Access | Behaviour |
|----------|--------|-----------|
| `GET /settings/cache/status` | **any authenticated user** | Lists every registered cache with `current_size`, `maxsize`, `ttl_seconds` |
| `POST /settings/cache/clear/{name}` | **admin only** (`require_admin`) | Clears one cache; `404` on an unknown name |
| `POST /settings/cache/clear-all` | **admin only** | Clears every registered cache; returns the count |

The read-vs-clear split is a **deliberate access decision** (2026-09-03): cache *sizes* are
operational trivia useful to anyone ("is the search cache even populated?"), while *clearing*
forces provider re-fetches for the whole instance and stays behind the admin gate. Both clears
are audit-logged with the admin's id and username.

!!! warning "A clear is a slowdown, not a reset button"

    After a clear, the next fetch of the affected data hits the providers again — expect
    slowdowns comparable to a server restart. The UI says so in a danger-styled confirmation
    modal before either clear action.

## 🖥️ Frontend: `CachePanel.svelte`

`frontend/src/lib/components/settings/CachePanel.svelte` renders the registry as a table
(name, `current_size / maxsize`, human-formatted TTL) inside the **Settings → Global** tab
(`GlobalSettingsTab.svelte`). Status loads for everyone; the per-row **Clear** buttons and
**Clear all** are gated by the `canEdit` prop, which mirrors the Global-settings lock — the
panel shows data to all users and destructive actions to unlocked admins only. See
[Settings components](../frontend/components/features/settings.md).

## 🧪 Tests

`backend/test_scripts/test_api/test_cache_admin_api.py` (CAPI-001…CAPI-008) covers the
contract: status readable by a normal user, clears rejected for non-admins (`403`), single
clear on an unknown name (`404`), and a functional round-trip that populates the
`upload_metadata` cache through a real upload, clears it via the endpoint, and verifies the
size drop in a second status read. Tests assert an **intersection** with a known-cache set —
never the full registry — because caches register lazily.
