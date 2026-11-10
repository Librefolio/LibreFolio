"""The historical replay of a stress scenario: its assets, its proxies and its verified window."""

from __future__ import annotations

from collections.abc import Set as AbstractSet
from dataclasses import replace
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.risk import (
    RiskErrorCode,
    RiskHistoricalReplayExclusionReason,
)
from backend.app.services.risk.base import (
    RiskExecutionContext,
    RiskHistoricalReplayContext,
    RiskUnavailableError,
)
from backend.app.services.risk.data_quality import merge_data_quality
from backend.app.services.risk.eligibility import (
    PriceWindowFacts,
    load_price_window_facts,
    replay_coverage,
    suggested_replay_range,
)
from backend.app.services.risk.plan import AnalyticPlan
from backend.app.services.risk.scope import ScopeInputs, bounded_range, prepare_asset_series


async def prepare_historical_replay_context(
    db: AsyncSession,
    *,
    plan: AnalyticPlan,
    context: RiskExecutionContext,
    scope_inputs: ScopeInputs,
    existing_asset_ids: set[int],
    target_currency: str,
    market_holidays: AbstractSet[date] = frozenset(),
) -> RiskExecutionContext:
    replay_range = getattr(plan.params, "replay_range", None)
    if not isinstance(replay_range, DateRangeModel):
        raise RiskUnavailableError(
            "Historical replay requires a valid replay range",
            code=RiskErrorCode.INVALID_PARAMETERS,
        )
    # R13-SEC8-1b: the facts, the coverage, the suggested window and the series all read the window bounded; the
    # parameters, and the output's echo of them, keep the request.
    replay_range = bounded_range(replay_range)

    scope_asset_ids = set(scope_inputs.requested_asset_ids)
    proxy_assets = tuple(getattr(plan.params, "proxy_assets", ()))
    excluded_asset_ids = tuple(getattr(plan.params, "excluded_assets", ()))
    proxy_by_asset = {int(proxy.asset_id): int(proxy.proxy_asset_id) for proxy in proxy_assets}
    referenced_scope_asset_ids = set(proxy_by_asset) | set(excluded_asset_ids)
    outside_scope_asset_ids = sorted(referenced_scope_asset_ids - scope_asset_ids)
    if outside_scope_asset_ids:
        raise RiskUnavailableError(
            "Historical replay options reference assets outside the selected scope",
            code=RiskErrorCode.INVALID_PARAMETERS,
            details={"asset_ids": outside_scope_asset_ids},
        )

    missing_proxy_asset_ids = sorted(set(proxy_by_asset.values()) - existing_asset_ids)
    if missing_proxy_asset_ids:
        raise RiskUnavailableError(
            "One or more historical replay proxy assets do not exist",
            code=RiskErrorCode.INVALID_PARAMETERS,
            details={"proxy_asset_ids": missing_proxy_asset_ids},
        )

    excluded_set = set(excluded_asset_ids)
    candidate_ids = [asset_id for asset_id in scope_inputs.requested_asset_ids if asset_id not in excluded_set]
    # Automatic exclusion (developer's decision of 24/09/2026): an asset the user did not proxy,
    # whose own quotes do not cover the replay window at both ends, takes no part in the replay
    # instead of blocking it. It must be left out before the joint series is prepared: kept
    # in, a late starter moves the joint baseline and shortens the replay of every other asset.
    replay_end = replay_range.end or replay_range.start
    own_ids = [asset_id for asset_id in candidate_ids if asset_id not in proxy_by_asset]
    window_facts = await load_price_window_facts(
        db,
        asset_ids=own_ids,
        window_start=replay_range.start,
        window_end=replay_end,
        target_currency=target_currency,
        market_holidays=market_holidays,
    )
    auto_excluded = {asset_id: reason for asset_id in own_ids if (reason := replay_coverage(window_facts[asset_id], replay_range.start, replay_end)) is not None}
    suggested_range, recovers = await verified_replay_range(
        db,
        facts=window_facts,
        auto_excluded=auto_excluded,
        own_ids=own_ids,
        window=(replay_range.start, replay_end),
        target_currency=target_currency,
        market_holidays=market_holidays,
    )
    source_asset_ids = {asset_id: proxy_by_asset.get(asset_id, asset_id) for asset_id in candidate_ids if asset_id not in auto_excluded}
    prepared = await prepare_asset_series(
        db,
        asset_ids=tuple(sorted(set(source_asset_ids.values()))),
        date_range=replay_range,
        target_currency=target_currency,
        market_holidays=market_holidays,
    )
    replay_data_quality = merge_data_quality(
        scope_inputs.data_quality,
        prepared.data_quality,
    )
    return replace(
        context,
        scope_asset_ids=scope_inputs.requested_asset_ids,
        excluded_assets=(),
        execution_warnings=scope_inputs.warnings,
        prepared_data_quality=prepared.data_quality,
        cash_weight=scope_inputs.cash_weight,
        historical_replay=RiskHistoricalReplayContext(
            prepared_series=prepared,
            source_asset_ids=source_asset_ids,
            excluded_asset_ids=tuple(sorted(excluded_asset_ids)),
            data_quality=replay_data_quality,
            auto_excluded_assets=auto_excluded,
            suggested_range=suggested_range,
            suggested_range_recovers=recovers,
        ),
    )


async def verified_replay_range(
    db: AsyncSession,
    *,
    facts: dict[int, PriceWindowFacts],
    auto_excluded: dict[int, RiskHistoricalReplayExclusionReason],
    own_ids: list[int],
    window: tuple[date, date],
    target_currency: str,
    market_holidays: AbstractSet[date] = frozenset(),
) -> tuple[Optional[DateRangeModel], tuple[int, ...]]:
    """A part of the replay window that brings back the assets its edges exclude.

    Proposed only when a second reading of the facts confirms it: every asset it recovers, and
    every asset already covered, is priced at both of its ends. Assets excluded for other reasons
    stay out of the check, since no shorter window brings them back.
    """
    proposal = suggested_replay_range(facts, auto_excluded, window[0], window[1])
    if proposal is None:
        return None, ()
    (start, end), recovers = proposal
    kept = [asset_id for asset_id in own_ids if asset_id not in auto_excluded or asset_id in recovers]
    check = await load_price_window_facts(db, asset_ids=kept, window_start=start, window_end=end, target_currency=target_currency, market_holidays=market_holidays)
    if any(replay_coverage(check[asset_id], start, end) is not None for asset_id in kept):
        return None, ()
    return DateRangeModel(start=start, end=end), recovers
