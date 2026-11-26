"""CoinGecko's official SDK behind one door (project 76; shared by the price provider and the enricher, 82 CG-A): the
client built with the rules of the P0 trial, and its errors translated into the plugins' own.

The rules (journal ``76_cryptoPrices/prove/README.md``):

- **No retry, no sleep.** The SDK retries twice by default and sleeps the ``Retry-After`` of a 429 (60 s measured), in the
  provider's thread. ``max_retries=0``: a refusal leaves at once as ``AssetRateLimitedError`` with its ``Retry-After``,
  and the call boundary pauses the provider.
- **The plan picks the root.** A Demo key answers on ``api.coingecko.com``, a paid key on ``pro-api.coingecko.com``; a key
  on the other root is refused (10010/10011): «wrong plan».
- **The error code hides in three shapes of body** (10012 under ``error.status``, 10005 under ``status``, 10011 at the
  top): ``coingecko_error_code`` looks in all three.
- **The key never leaves.** The SDK sends it in a header; no message built here contains it, and any text taken from a
  response is scrubbed of it.

The SDK is imported when a client is built, never when the provider is discovered.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceError
from backend.app.services.plugin_settings.groups.coingecko import PLAN_PRO
from backend.app.utils.runtime.cooldown import retry_after_seconds

#: What a CoinGecko id looks like («bitcoin», «usd-coin», «pepe»): letters, digits, dots, dashes and underscores, never a
#: path or a query. Anything else is no coin of CoinGecko's and asks nothing.
_COIN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def coin_id(identifier: str) -> str | None:
    """``identifier`` as a CoinGecko id, or None when it is not one (it then asks nothing)."""
    coin = (identifier or "").strip()
    return coin if _COIN_ID.fullmatch(coin) and ".." not in coin else None


def decimal_json(text: str) -> Any:
    """A response's JSON with its decimals as ``Decimal``: the digits CoinGecko wrote, never a float's."""
    return json.loads(text, parse_float=Decimal)


#: How long one request may take, in seconds: below the core's shortest price call (``price_query``, 10 s), so the
#: request ends as CoinGecko's own TIMEOUT before the core cuts the thread. CoinGecko answered in 0.2 s in the trial.
REQUEST_TIMEOUT_SECONDS = 8.0

#: CoinGecko's own error codes the provider tells apart (the P0 recordings).
HISTORY_RANGE_LIMIT = 10012  # a range beyond 365 days on the Demo plan
PAID_ENDPOINT = 10005  # an endpoint of the paid plans
WRONG_ROOT_CODES = frozenset({10010, 10011})  # a Pro key on the Demo root, a Demo key on the Pro root

#: The provider's error codes (``AssetSourceError.error_code``), beside the core's RATE_LIMITED, TIMEOUT and FETCH_ERROR.
PLAN_REQUIRED = "PLAN_REQUIRED"
WRONG_PLAN = "WRONG_PLAN"
INVALID_API_KEY = "INVALID_API_KEY"
PROVIDER_ERROR = "PROVIDER_ERROR"


def build_client(api_key: str, plan: str, *, http_client: Any = None) -> Any:
    """The SDK's client for ``api_key`` on the root of ``plan``: no retry, a bounded timeout.

    ``http_client`` (an ``httpx.Client``) is the tests' door: a client on a fake transport, so no request leaves.
    """
    from coingecko_sdk import Coingecko  # noqa: PLC0415 — the SDK loads when a call needs it, not at discovery

    if plan == PLAN_PRO:
        return Coingecko(pro_api_key=api_key, environment="pro", max_retries=0, timeout=REQUEST_TIMEOUT_SECONDS, http_client=http_client)
    return Coingecko(demo_api_key=api_key, environment="demo", max_retries=0, timeout=REQUEST_TIMEOUT_SECONDS, http_client=http_client)


def call[T](api_key: str, plan: str, request: Callable[[Any], T], *, http_client: Any = None) -> T:
    """Run ``request`` on a client for ``api_key`` on the root of ``plan``; the SDK's errors translated.

    Blocking: a plugin calls it in its own worker thread. A client built here is closed after the call, error or not;
    ``http_client``, the tests' fake transport, is theirs.
    """
    client = build_client(api_key, plan, http_client=http_client)
    try:
        return request(client)
    except Exception as error:  # noqa: BLE001 — every failure of the SDK becomes the plugin's own error, its cause kept
        translated = translate(error, secret=api_key)
        if translated is error:
            raise
        raise translated from error
    finally:
        if http_client is None:
            client.close()


def coingecko_error_code(body: object) -> int | None:
    """CoinGecko's ``error_code`` in any of the three shapes its error bodies take; None when there is none."""
    if not isinstance(body, dict):
        return None
    candidates = [body.get("error_code"), (body.get("status") or {}).get("error_code") if isinstance(body.get("status"), dict) else None]
    error = body.get("error")
    if isinstance(error, dict) and isinstance(error.get("status"), dict):
        candidates.append(error["status"].get("error_code"))
    for candidate in candidates:
        if isinstance(candidate, int) and not isinstance(candidate, bool):
            return candidate
    return None


def translate(error: Exception, *, secret: str | None) -> Exception:
    """The provider's error for an exception of the SDK; any other exception as it is.

    No message here quotes the response's own text: the codes and statuses say enough, and nothing can carry the key.
    """
    import coingecko_sdk  # noqa: PLC0415 — as in build_client

    if isinstance(error, coingecko_sdk.RateLimitError):
        wait = retry_after_seconds(error.response.headers.get("retry-after"))
        return AssetRateLimitedError("CoinGecko refused for too many requests", retry_after=wait)
    if isinstance(error, coingecko_sdk.APITimeoutError):
        return AssetSourceError("CoinGecko did not answer in time", "TIMEOUT")
    if isinstance(error, coingecko_sdk.APIConnectionError):
        return AssetSourceError("CoinGecko could not be reached", "FETCH_ERROR")
    if isinstance(error, coingecko_sdk.APIStatusError):
        code = coingecko_error_code(error.body)
        details = {"http_status": error.status_code, "coingecko_error_code": code}
        if code in WRONG_ROOT_CODES:
            return AssetSourceError("The CoinGecko key does not match the plan set for it (Demo or Pro)", WRONG_PLAN, details)
        if code in (PAID_ENDPOINT, HISTORY_RANGE_LIMIT):
            return AssetSourceError("This CoinGecko request needs a paid plan", PLAN_REQUIRED, details)
        if error.status_code in (401, 403):
            return AssetSourceError("CoinGecko refused the API key", INVALID_API_KEY, details)
        # ``detail`` is what the interface's PROVIDER_ERROR text shows: the status, never the response's own words
        return AssetSourceError(f"CoinGecko answered with HTTP {error.status_code}", PROVIDER_ERROR, {**details, "detail": f"CoinGecko HTTP {error.status_code}"})
    return _scrubbed(error, secret)


def _scrubbed(error: Exception, secret: str | None) -> Exception:
    """An exception the SDK did not shape: kept, unless its text holds the key, which a generic error then replaces."""
    if secret and secret in str(error):
        return AssetSourceError("CoinGecko's client failed", PROVIDER_ERROR)
    return error
