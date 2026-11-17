"""The simulation's own history: all the common history available, never the page's period (RN-16, developer's Q4 c).

The page's period chose the window the simulation was estimated on, so one asset over one horizon gave a median of
+1 400 % from «3M» and −39 % from «1Y». Like the historical replay, the simulation now prepares a window of its own:
from the day after the latest first quote among the scope's assets — the first day every one of them has a price
behind it — to the end of the data, the same end the page reads up to today. The page's period no longer reaches it.

Two ceilings shape that window before it is read. The price budget of one preparation (J-50, ``MAX_BULK_ITEM_DAYS``
per-day points over every asset) moves its start forward to the most recent days that fit, instead of refusing; the
bootstrap's history ceiling then keeps the most recent observations that cross the process boundary (in the plugin).
The result states the window it was estimated on; `history_truncated` says only the bootstrap's trim — a start moved by
the price budget (over 27 years of prices at 100 holdings) shows in the window's start date alone.
"""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Set as AbstractSet
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.risk.scope import RiskQueryRequest
from backend.app.schemas.risk.vocabulary import RiskErrorCode
from backend.app.services.risk.base import RiskExecutionContext, RiskUnavailableError
from backend.app.services.risk.eligibility import PriceWindowFacts, load_price_window_facts
from backend.app.services.risk.results import build_execution_context
from backend.app.services.risk.scope import ScopeInputs, bounded_range, prepare_asset_series
from backend.app.utils.date_range_limits import MAX_BULK_ITEM_DAYS
from backend.app.utils.datetime_utils import latest_range_end


def simulation_participants(first_quotes: Mapping[int, date | None]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Which holdings the simulation's history is estimated on, and which it leaves out: the one place that decides.

    Today (RN-16, developer's Q4 c — the consultant's reading, 17/11/2026) every quoted holding takes part, so a holding
    listed recently shortens the shared history of all of them and the amber line says how short it is; a holding never
    quoted takes no part (the preparation excludes it, as the page does). Leaving a late starter out — its weight with
    the cash, as the historical replay does — is a product choice put to the developer; if it is made, it is made here.
    """
    quoted = tuple(asset_id for asset_id, first in first_quotes.items() if first is not None)
    left_out = tuple(asset_id for asset_id, first in first_quotes.items() if first is None)
    return quoted, left_out


def simulation_window(facts: Mapping[int, PriceWindowFacts], *, end: date) -> DateRangeModel | None:
    """The window the simulation is estimated on, from the facts of its assets; None when none of them takes part.

    It starts the day after the latest first quote among the holdings that take part (:func:`simulation_participants`) —
    so every one of them has a price on the day before, the baseline the first return is measured from — and no earlier
    than the price budget allows for this many assets: the most recent days that fit (J-50). It ends at ``end``.
    """
    taking_part, _left_out = simulation_participants({asset_id: item.first_quote_ever for asset_id, item in facts.items()})
    if not taking_part:
        return None
    start = max(facts[asset_id].first_quote_ever for asset_id in taking_part) + timedelta(days=1)
    budget_days = MAX_BULK_ITEM_DAYS // len(taking_part)
    start = max(start, end - timedelta(days=budget_days - 2))
    return bounded_range(DateRangeModel(start=min(start, end), end=end))


async def prepare_simulation_context(
    db: AsyncSession,
    *,
    request: RiskQueryRequest,
    scope_inputs: ScopeInputs,
    never_priced_asset_ids: frozenset[int],
    market_holidays: AbstractSet[date] = frozenset(),
) -> RiskExecutionContext:
    """The execution context of a simulation, rebuilt whole from its own window (weights, cash, exclusions, series)."""
    end = latest_range_end()
    facts = await load_price_window_facts(
        db,
        asset_ids=scope_inputs.requested_asset_ids,
        window_start=end,
        window_end=end,
        target_currency=request.target_currency,
        market_holidays=market_holidays,
    )
    window = simulation_window(facts, end=end)
    if window is None:
        raise RiskUnavailableError(
            "No asset of the scope has a price to estimate the simulation on",
            code=RiskErrorCode.INSUFFICIENT_HISTORY,
        )
    prepared = await prepare_asset_series(
        db,
        asset_ids=tuple(sorted(scope_inputs.requested_asset_ids)),
        date_range=window,
        target_currency=request.target_currency,
        market_holidays=market_holidays,
    )
    return build_execution_context(
        request=request.model_copy(update={"date_range": window}),
        scope_inputs=scope_inputs,
        prepared=prepared,
        never_priced_asset_ids=never_priced_asset_ids,
    )
