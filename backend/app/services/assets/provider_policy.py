"""What the instance decides about each asset provider, in one place.

Today: where a provider stands in the asset search (F21). The plugin declares its ``tier`` and ``search_priority``
(``AssetSourceProvider``); an instance overrides them with ``LIBREFOLIO_ASSET_PROVIDERS_PREMIUM`` and
``LIBREFOLIO_ASSET_PROVIDERS_ORDER`` (``config/plugins.py``). The variables are read at every call, never cached.

- ``provider_tier(code)`` and ``provider_priority(code)``: the effective values, as ``GET /assets/provider`` shows them.
- ``search_rank(code)``: the key the search sorts by, premium first and then lower priority. Sort with a **stable**
  sort, so that ties, a repeated code included, keep the given order.
- ``search_order(codes)``: the providers in the order the search lists them. With every value at its default the
  order is the given one, so a self-hosted instance without a premium provider searches exactly as before (D-X3).

A code in a variable that no registered provider has is ignored, and logged once per process.
"""

import functools
from collections.abc import Sequence

from backend.app.config.plugins import asset_providers_order, asset_providers_premium
from backend.app.logging_config import get_logger
from backend.app.schemas.provider import DEFAULT_SEARCH_PRIORITY, FAProviderTier
from backend.app.services.assets.registry import AssetProviderRegistry

logger = get_logger(__name__)

_PREMIUM_VARIABLE = "LIBREFOLIO_ASSET_PROVIDERS_PREMIUM"
_ORDER_VARIABLE = "LIBREFOLIO_ASSET_PROVIDERS_ORDER"


@functools.cache
def _report_unknown(variable: str, codes: tuple[str, ...]) -> None:
    """Log, once per process, the codes of a variable that no registered provider has."""
    logger.warning("Unknown asset providers in the configuration", variable=variable, codes=list(codes), consequence="ignored")


def _registered(variable: str, codes: tuple[str, ...]) -> tuple[str, ...]:
    """The codes of registered providers, in their order; the others are logged once and dropped."""
    unknown = tuple(code for code in codes if AssetProviderRegistry.get_plugin(code) is None)
    if unknown:
        _report_unknown(variable, unknown)
    return tuple(code for code in codes if code not in unknown)


def provider_tier(code: str) -> FAProviderTier:
    """The provider's effective tier: in ``LIBREFOLIO_ASSET_PROVIDERS_PREMIUM`` when it is set, else declared."""
    premium = asset_providers_premium()
    if premium is not None:
        return FAProviderTier.PREMIUM if code in _registered(_PREMIUM_VARIABLE, premium) else FAProviderTier.COMMUNITY
    plugin = AssetProviderRegistry.get_plugin(code)
    return plugin.tier if plugin is not None else FAProviderTier.COMMUNITY


def provider_priority(code: str) -> int:
    """The provider's effective place in the search inside its tier, lower first.

    Its declared ``search_priority``. With ``LIBREFOLIO_ASSET_PROVIDERS_ORDER``, the listed providers get 0, 1, 2… in
    that order, and the others follow, at the length of the list plus their declared priority.
    """
    plugin = AssetProviderRegistry.get_plugin(code)
    declared = plugin.search_priority if plugin is not None else DEFAULT_SEARCH_PRIORITY
    order = asset_providers_order()
    if order is None:
        return declared
    listed = _registered(_ORDER_VARIABLE, order)
    if code in listed:
        return listed.index(code)
    return len(listed) + declared


def search_rank(code: str) -> tuple[int, int]:
    """The provider's place in the search, to sort by: ``0`` for premium and ``1`` for community, then its effective
    priority. Use it with a stable sort (``sorted``, ``list.sort``): ties keep the given order."""
    return (0 if provider_tier(code) == FAProviderTier.PREMIUM else 1, provider_priority(code))


def search_order(codes: Sequence[str]) -> list[str]:
    """``codes`` in the order the search lists them: premium first, then lower priority; ties, a repeated code included,
    keep the given order."""
    return sorted(codes, key=search_rank)
