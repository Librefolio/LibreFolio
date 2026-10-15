"""
Asset pricing core: the runtime shared by the asset service modules and every plugin call.

This module provides:
- the provider caches (history, current value, metadata, search results, search queries)
- _run_provider_in_thread(): every provider call runs in a dedicated thread with its own event loop
- the provider parameter helpers (_provider_params_hash, _parse_provider_params)
- _json_safe_details(): the sanitizer of ``AssetSourceError.details`` for API responses

The plugin contract (AssetSourceProvider, AssetSourceError) lives in ``base.py``.

Nothing here backward-fills prices: history is stored exactly as providers return
it, and gaps are filled only when prices are read (assets/price_query.py).

Similar to the FX service (services/fx/) but for price_history table (asset prices vs FX rates).

Key differences from FX:
- Table: price_history (not fx_rates)
- Fields: OHLC (open/high/low/close) + volume (not single rate)
- Lookup: (asset_id, date) not (base, quote, date)
- Synthetic yield: Calculated on-demand for SCHEDULED_YIELD assets

Design principles:
- Bulk-first: All operations have bulk version as PRIMARY
- Singles call bulk with 1 element
- DB optimization: Minimize queries (typically 1-3 max)
- Parallel provider calls where possible
"""

import asyncio
import hashlib
import json
from typing import Optional

from backend.app.logging_config import get_logger
from backend.app.utils.runtime.cache import get_ttl_cache

# Initialize structured logger
logger = get_logger(__name__)

# ============================================================================
# CORE CACHES — automatic TTL expiration via theine timer wheel
# ============================================================================

_asset_history_cache = get_ttl_cache("asset_history_fetch", maxsize=500, ttl=900)  # 15 min
_asset_current_cache = get_ttl_cache("asset_current_fetch", maxsize=300, ttl=120)  # 2 min
_asset_metadata_cache = get_ttl_cache("asset_metadata_fetch", maxsize=200, ttl=1800)  # 30 min
_search_result_cache = get_ttl_cache("search_results", maxsize=5000, ttl=86400)  # 24h — individual items
_search_query_cache = get_ttl_cache("search_queries", maxsize=500, ttl=900)  # 15 min — query→results
_RISK_WARMUP_DAY_MULTIPLIER = 2


def _provider_params_hash(provider_params: Optional[dict]) -> str:
    """
    Stable short hash of `provider_params` for use in cache keys (#R3-4).

    Uses MD5 (non-cryptographic, just for keying) over the JSON-serialized params
    with sorted keys to guarantee determinism regardless of dict iteration order.
    Returns the first 8 hex chars — enough entropy to avoid collisions across the
    small number of concurrently-cached keys per asset.
    """
    if not provider_params:
        return "none"
    try:
        payload = json.dumps(provider_params, sort_keys=True, default=str)
    except Exception:
        payload = repr(sorted(provider_params.items()))
    return hashlib.md5(payload.encode("utf-8")).hexdigest()[:8]


def _parse_provider_params(raw_params):
    """Parse stored provider params into a dictionary."""
    if raw_params is None:
        return {}
    if isinstance(raw_params, dict):
        return raw_params
    if isinstance(raw_params, str):
        try:
            return json.loads(raw_params)
        except Exception:
            return {}
    return {}


# ============================================================================
# THREAD ISOLATION FOR PROVIDER CALLS
# ============================================================================


async def _run_provider_in_thread(coro_factory, *, timeout: float = 60.0):
    """
    Run a provider coroutine in a dedicated thread with its own event loop.

    Protects the main event loop from blocking provider implementations.
    Even a well-written async provider (httpx) works fine — it just uses
    the thread's event loop instead of the main one.

    A badly-written provider that does `requests.get()` directly in an
    async def will block the thread, NOT the main event loop.

    Args:
        coro_factory: Zero-arg callable that returns the coroutine to run.
                     Example: lambda: provider.get_current_value(id, type, params)
        timeout: Maximum time to wait (seconds). Default 60s.

    Returns:
        Result of the coroutine.

    Raises:
        asyncio.TimeoutError: If provider takes longer than timeout.
        Any exception raised by the provider.
    """

    def _sync_runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro_factory())
        finally:
            loop.close()

    return await asyncio.wait_for(
        asyncio.to_thread(_sync_runner),
        timeout=timeout,
    )


# (Pydantic models for API request/response live in backend.app.schemas.assets)
# They are imported by API modules when needed


def _json_safe_details(details: Optional[dict]) -> Optional[dict]:
    """Make an AssetSourceError ``details`` dict safe for a JSON response (I3).

    Providers may put dates, Decimals or other non-primitives in ``details``;
    the probe DTO must serialize, so anything not natively JSON-safe is
    stringified. ``None`` and empty dicts stay ``None`` (field omitted).

    Deliberately NOT :func:`backend.app.utils.json_utils.ensure_json_safe`:
    that one is a *validator* — it rejects non-JSON producer output on contract
    boundaries (signals, AI Export). Here the provider is a third-party plugin
    and the probe must still return a localized error, so we *sanitize*
    (stringify, one list level deep) instead of raising. See
    ``backend/app/utils/json_utils.py`` module docstring (audit 08, report 03 §N-03-A).
    """
    if not details:
        return None
    safe: dict = {}
    for key, value in details.items():
        if value is None or isinstance(value, (str, int, float, bool)):
            safe[str(key)] = value
        elif isinstance(value, (list, tuple)):
            safe[str(key)] = [item if item is None or isinstance(item, (str, int, float, bool)) else str(item) for item in value]
        else:
            safe[str(key)] = str(value)
    return safe
