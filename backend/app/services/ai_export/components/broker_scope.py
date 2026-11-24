"""The brokers an AI Export build reads (78 L10b, D13).

An empty `BuildScope.broker_scope` means **no broker**: the request named none and the user owns none. It never means
«every broker the user can access». The services below the AI Export read `broker_ids=None` (and even an empty list)
as «every accessible broker», so a reader that passed an empty scope through would hand the user the brokers only
shared with them: the opposite of D13. Every reader therefore asks `scope_broker_ids`, which refuses an empty scope.

`prepare_request` keeps an empty scope away from these readers: a selection that reads brokers is refused before the
build (`no_owned_brokers`). `scope_broker_ids` is the guard behind that gate, so a gap fails loudly instead of widening.
"""

from __future__ import annotations

from backend.app.services.ai_export.components.types import BuildScope

REASON_NO_OWNED_BROKERS = "no_owned_brokers"
"""The user owns no broker and the request named none: there is no position, exposure or portfolio to read."""

ASSET_FX_BROKER_COMPONENT_IDS: frozenset[str] = frozenset(
    {
        "asset.position_scope",
        "asset.positions_by_broker",
        "asset.cost_value_pl",
        "asset.performance",
        "asset.lot_detail",
        "fx.exposure_base_quote",
    }
)
"""The Asset and FX components whose builders read the scope's brokers (the asset report and lots, the FX exposure
report). Every Portfolio component reads them. The other Asset and FX components read market data only: they stay
available to a user who owns no broker."""


class NoBrokerScopeError(RuntimeError):
    """A reader met an empty broker scope: it refuses rather than read every accessible broker."""

    reason_code = REASON_NO_OWNED_BROKERS

    def __init__(self, reader: str) -> None:
        self.reader = reader
        super().__init__(f"{reader}: the scope holds no broker (the user owns none and the request named none)")


def scope_broker_ids(scope: BuildScope, *, reader: str) -> list[int]:
    """The scope's brokers, for a service that reads `None` or `[]` as «every accessible broker»; never empty."""
    if not scope.broker_scope:
        raise NoBrokerScopeError(reader)
    return list(scope.broker_scope)


__all__ = [
    "ASSET_FX_BROKER_COMPONENT_IDS",
    "REASON_NO_OWNED_BROKERS",
    "NoBrokerScopeError",
    "scope_broker_ids",
]
