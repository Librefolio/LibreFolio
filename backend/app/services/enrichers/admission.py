"""The calls an enricher makes outside its reads, counted on the account it shares (82 CG-C).

A read is counted binding by binding (``refresh.py``, project 76 K1). «Recognize», the search and the test reach the source
too: for an enricher whose settings group shares one account's credits (``shares_credits``: CoinGecko, whose price
provider spends the same ones) each of them is counted, and refused when a limit of the group is full, before it leaves.
An enricher with an account of its own, or none, is not counted here: the limits an administrator set for it are about its
reads, as before.
"""

from __future__ import annotations

from backend.app.services.enrichers.base import EnricherPlugin, EnricherRateLimited
from backend.app.services.platform import call_counter
from backend.app.services.plugin_settings.groups import get_group


def _shares_credits(plugin: EnricherPlugin) -> bool:
    groups = (get_group(name) for name in getattr(type(plugin), "settings_groups", ()) or ())
    return any(group is not None and group.shares_credits for group in groups)


async def count_shared_call(plugin: EnricherPlugin) -> None:
    """Count one call of ``plugin`` on the account it shares; ``EnricherRateLimited``, before the call, when a limit of it
    is full. Nothing for an enricher that shares none, or calls nothing out. A counter that fails lets the call go."""
    if not getattr(plugin, "calls_external_service", False) or not _shares_credits(plugin):
        return
    family, owner, limits = call_counter.call_owner(plugin, "enricher")
    try:
        await call_counter.count_and_check(family, owner, limits)
    except call_counter.CallLimitReached as full:
        raise EnricherRateLimited(f"{plugin.name}: the {full.window} call limit of the shared account is reached ({full.limit})", retry_after=full.retry_after) from full
