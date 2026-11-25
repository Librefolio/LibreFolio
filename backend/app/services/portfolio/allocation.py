"""The filtered allocation of ``PortfolioService`` (``POST /portfolio/allocation``, lane 80, issue #89)."""

from __future__ import annotations

import asyncio
import dataclasses
from datetime import date as date_type

from backend.app.schemas.portfolio.allocation import PortfolioAllocationQuery, PortfolioAllocationResponse
from backend.app.services.financial_math.portfolio.allocation_view import (
    BUCKETS_BY_DIMENSION,
    EXCLUDABLE_BUCKETS,
    AllocationDimension,
    AllocationFilters,
    build_allocation_view,
)
from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder
from backend.app.utils.datetime_utils import latest_range_end


class PortfolioAllocationMixin:
    """The «Allocazione» tab's view. Mixed into ``PortfolioService``, which provides ``db`` and the data helpers."""

    async def get_allocation(self, user_id: int, query: PortfolioAllocationQuery) -> PortfolioAllocationResponse:
        """The view of the period's last day, from the page's engine run.

        ``_engine_run`` (FB-14) is the report's run: the same blob-cache key as the report of that period and scope, so a
        change of the filters or of the dimension reads the run the page built and replays nothing. The dates resolve as
        the report's. A broker the user cannot read is left out of the run (an empty view when none is left, as the
        report's).
        """
        today = date_type.today()
        base_currency = query.target_currency or await self._get_base_currency(user_id)
        date_from = query.date_range.resolved_start() if query.date_range else None
        date_to = query.date_range.resolved_end() if query.date_range else None
        if date_to is not None:
            date_to = min(date_to, latest_range_end())
        effective_end = date_to or today
        if date_from is not None:
            date_from = min(date_from, effective_end)

        dimension = AllocationDimension(query.dimension)
        filters = AllocationFilters(
            classes=frozenset(query.classes) if query.classes is not None else None,
            types=frozenset(query.types),
            exclude_buckets=frozenset(query.exclude_buckets),
            exclude_asset_ids=frozenset(query.exclude_asset_ids),
        )
        states, asset_types, asset_classifications = [], {}, {}
        if await self._get_user_broker_access(user_id, query.broker_ids):
            result = await self._engine_run(user_id=user_id, broker_ids=query.broker_ids, date_from=date_from, date_to=date_to, target_currency=base_currency, apply_ownership_share=query.apply_ownership_share)
            states, asset_types, asset_classifications = result.daily_states, result.asset_types, result.asset_classifications

        asset_ids = DerivedViewsBuilder(states, base_currency).allocation_asset_ids(date_from) if states else set()
        if states:
            asset_ids |= set(states[-1].by_asset)
        assets = await self._get_assets_map(asset_ids)
        # Pure CPU, and long with the history (every asset split again on every change row: ~0.2–0.7 s on 2000 segments ×
        # 20 assets): off the event loop. to_thread copies the context, the Decimal context included
        view = await asyncio.to_thread(
            build_allocation_view,
            states,
            asset_types=asset_types,
            asset_classifications=asset_classifications,
            dimension=dimension,
            filters=filters,
            date_from=date_from,
            include_history=query.include_history,
            names={asset_id: asset.display_name for asset_id, asset in assets.items()},
            target_currency=base_currency,
        )

        payload = dataclasses.asdict(view)
        for row in payload["assets"]:
            asset = assets.get(row["asset_id"])
            row["name"] = asset.display_name if asset else f"Asset {row['asset_id']}"
            row["ticker"] = asset.identifier_ticker if asset else None
            row["asset_type"] = asset.asset_type.value if asset and asset.asset_type is not None else None
            row["icon_url"] = (asset.icon_url or None) if asset else None
        payload["history"] = payload["history"] if query.include_history else None
        return PortfolioAllocationResponse.model_validate(
            {
                **payload,
                "currency": base_currency,
                "date_from": date_from,
                "applicable_buckets": sorted(BUCKETS_BY_DIMENSION[dimension] & EXCLUDABLE_BUCKETS),
            }
        )
