"""Typed raw resources and `ResourceKey` loaders for the Asset core components.

This module owns the Asset-domain (workstream E2, "Asset core" wave)
request-scoped raw resource loaders for the eight non-technical
`ComponentSpec` builders in `asset_core.py`:
`asset.identity`, `asset.market_snapshot`, `asset.position_scope`,
`asset.provenance`, `asset.positions_by_broker`, `asset.cost_value_pl`,
`asset.performance`, `asset.lot_detail`.

Deliberately kept separate from `backend.app.services.ai_export.components.
resources` (the shared cross-domain resource module). Technical prices use a
native-market series, while `asset.market_snapshot` uses a distinct
target-currency request because the two consumers have different currency
semantics.

Every loader is a plain callable `(AsyncSession) -> Awaitable[T]` meant to be
passed to `BuildContext.db_resource`, which memoizes it (success or failure)
for the lifetime of one request - see `backend.app.services.ai_export.
dependencies.BuildContext`. No loader here ever serializes a raw resource
directly as a section payload; that is the job of the builders in
`asset_core.py`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date as Date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetProviderAssignment
from backend.app.schemas.assets import FAClassificationParams
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.portfolio import LotAnalysisType, LotsAnalysisResponse, OpenDateRangeModel, PortfolioReportQuery, PortfolioReportResponse
from backend.app.schemas.prices import FAPriceQueryItem, FAPriceQueryResult
from backend.app.services.ai_export.components.resources import PriceResultsResource
from backend.app.services.ai_export.components.types import BuildScope, ResourceKey
from backend.app.services.asset_source import AssetSourceManager
from backend.app.services.lots_analysis_service import LotsAnalysisService
from backend.app.services.portfolio_service import PortfolioService


class AssetNotFoundError(ValueError):
    """Typed failure raised when `BuildScope.asset_id` has no matching `Asset` row.

    Every Asset-core component (see `asset_core.py`) resolves
    `ASSET_METADATA_RESOURCE` before doing anything else, so this failure is
    consistently surfaced (wrapped as `ResourceLoadError`/
    `RequiredComponentBuildError` by `BuildContext`) regardless of which
    component_id a caller happens to request first - not only `asset.identity`.
    """


@dataclass(frozen=True, slots=True)
class AssetMetadataResource:
    """Extracted, immutable snapshot of one `Asset` row plus its provider assignment (if any).

    Deliberately holds plain scalar/tuple values rather than the live ORM
    `Asset` instance: builders consuming this resource must never trigger a
    lazy-load or otherwise touch the session outside `db_resource`'s
    serialization boundary.
    """

    asset_id: int
    display_name: str
    currency: str
    asset_type: str
    quote_base_quantity: int
    active: bool
    identifier_isin: str | None
    identifier_ticker: str | None
    identifier_cusip: str | None
    identifier_sedol: str | None
    identifier_figi: str | None
    identifier_other: tuple[str, ...]
    classification: FAClassificationParams | None
    provider_code: str | None
    provider_identifier: str | None
    provider_identifier_type: str | None
    provider_last_fetch_date: Date | None


def load_asset_metadata(scope: BuildScope):
    """Builds the `db_resource` loader for `ASSET_METADATA_RESOURCE`.

    Raises `AssetNotFoundError` if `scope.asset_id` has no matching `Asset`
    row - the canonical "missing asset" typed failure every Asset-core
    component guards against.
    """

    async def _load(session: AsyncSession) -> AssetMetadataResource:
        asset = await session.get(Asset, scope.asset_id)
        if asset is None:
            raise AssetNotFoundError(f"Asset {scope.asset_id} not found")

        classification: FAClassificationParams | None = None
        if asset.classification_params:
            classification = FAClassificationParams.model_validate_json(asset.classification_params)

        assignment_stmt = select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == scope.asset_id)
        assignment = (await session.execute(assignment_stmt)).scalars().first()

        return AssetMetadataResource(
            asset_id=scope.asset_id,
            display_name=asset.display_name,
            currency=asset.currency,
            asset_type=str(asset.asset_type.value if hasattr(asset.asset_type, "value") else asset.asset_type),
            quote_base_quantity=asset.quote_base_quantity or 1,
            active=asset.active,
            identifier_isin=asset.identifier_isin,
            identifier_ticker=asset.identifier_ticker,
            identifier_cusip=asset.identifier_cusip,
            identifier_sedol=asset.identifier_sedol,
            identifier_figi=asset.identifier_figi,
            identifier_other=tuple(asset.identifier_other or ()),
            classification=classification,
            provider_code=assignment.provider_code if assignment else None,
            provider_identifier=assignment.identifier if assignment else None,
            provider_identifier_type=(str(assignment.identifier_type.value if hasattr(assignment.identifier_type, "value") else assignment.identifier_type) if assignment else None),
            provider_last_fetch_date=(assignment.last_fetch_at.date() if assignment and assignment.last_fetch_at else None),
        )

    return _load


@dataclass(frozen=True, slots=True)
class AssetPriceObservationData:
    """One observed daily close price for the asset, in its native currency."""

    date: Date
    close: Decimal
    currency: str
    source_plugin_key: str


@dataclass(frozen=True, slots=True)
class AssetMarketSnapshotResource:
    """Latest observed price (native currency) plus its target-currency conversion, if any.

    `observation` is `None` when no priced observation exists at or before
    `snapshot_as_of` - a valid, empty-but-successful outcome (see the
    component-runtime "empty is a property of the data" semantics), never a
    build failure by itself. FX conversion failures (e.g. no rate available)
    DO propagate as build failures - see `market_snapshot_from_price_result`.
    """

    observation: AssetPriceObservationData | None
    converted_amount: Currency | None
    conversion_rate_date: Date | None
    conversion_direction: str | None  # "identity" | "direct" | "inverse"
    conversion_backward_fill_applied: bool | None


_EMPTY_MARKET_SNAPSHOT = AssetMarketSnapshotResource(
    observation=None,
    converted_amount=None,
    conversion_rate_date=None,
    conversion_direction=None,
    conversion_backward_fill_applied=None,
)


def market_snapshot_from_price_result(result: FAPriceQueryResult | None, scope: BuildScope) -> AssetMarketSnapshotResource:
    """Derives the observed-price market snapshot from an already-loaded `FAPriceQueryResult`.

    Consolidates what used to be this module's own raw-SQL `PriceHistory`
    query (single most-recent-row lookup) into the *same* canonical
    `PriceResultsResource` the technical sibling wave loads via
    `backend.app.services.ai_export.components.technical_shared.
    load_asset_price_results` (`ASSET_PRICE_RESULTS_RESOURCE`): both
    `asset.market_snapshot` and `asset.ohlc_returns`/`asset.indicators`/
    `asset.states_events` now share one DB read per request for Asset
    prices, regardless of which component resolves it first (parent
    integration gate, requirement 4).

    Selects the most recent point at or before `scope.snapshot_as_of` whose
    *price* was genuinely observed on that calendar date -
    `point.backward_fill_info is None` (no backward-fill of any kind) or
    `point.backward_fill_info.days_back == 0` (the composed
    `AssetBackwardFillInfo` may still carry a *separate* `fx_days_back > 0`
    when only the currency conversion fell back to an older FX rate - see
    `AssetBackwardFillInfo`'s decoupled price/FX staleness dimensions -
    the price itself was not carried forward from an earlier trading day
    either way). A point with `days_back > 0` (the asset price itself was
    backward-filled) is never selected, even when no earlier genuinely
    observed point exists within the loaded range: `observation=None`
    remains a valid, empty-but-successful outcome, exactly like the
    previous "no PriceHistory row" case.

    `native_price`/`native_currency` are recovered from
    `original_close`/`original_currency` when the bulk loader already
    converted the point to `scope.target_currency` (both are `None` when no
    conversion happened, i.e. the asset's own currency already IS
    `scope.target_currency`) - this module never re-derives or re-fetches
    the native-currency price separately.
    """
    if result is None or not result.prices:
        return _EMPTY_MARKET_SNAPSHOT

    candidates = [point for point in result.prices if point.date <= scope.snapshot_as_of and (point.backward_fill_info is None or point.backward_fill_info.days_back == 0)]
    if not candidates:
        return _EMPTY_MARKET_SNAPSHOT

    point = max(candidates, key=lambda candidate: candidate.date)
    native_currency = point.original_currency or point.currency
    native_close = point.original_close if point.original_close is not None else point.close
    observation = AssetPriceObservationData(date=point.date, close=native_close, currency=native_currency, source_plugin_key=point.source_plugin_key)

    if native_currency == scope.target_currency:
        return AssetMarketSnapshotResource(
            observation=observation,
            converted_amount=Currency(code=scope.target_currency, amount=point.close),
            conversion_rate_date=point.date,
            conversion_direction="identity",
            conversion_backward_fill_applied=False,
        )

    bfi = point.backward_fill_info
    fx_rate_date = bfi.fx_rate_date if bfi is not None and bfi.fx_rate_date is not None else point.date
    fx_backward_fill_applied = bool(bfi is not None and bfi.fx_days_back is not None and bfi.fx_days_back > 0)
    direction = "direct" if native_currency < scope.target_currency else "inverse"
    return AssetMarketSnapshotResource(
        observation=observation,
        converted_amount=Currency(code=scope.target_currency, amount=point.close),
        conversion_rate_date=fx_rate_date,
        conversion_direction=direction,
        conversion_backward_fill_applied=fx_backward_fill_applied,
    )


def load_asset_report(scope: BuildScope):
    """Builds the `db_resource` loader for `ASSET_REPORT_RESOURCE`.

    Runs `PortfolioService.get_report` exactly once per request (memoized by
    `BuildContext.db_resource`), scoped to `scope.broker_scope` (empty =
    every accessible broker) and the AI Export period, with
    `include_positions_contribution=True` so per-asset period P&L
    attribution is available without a second engine run. Holdings/
    contributions are filtered down to `scope.asset_id` by each consuming
    builder in `asset_core.py`, not here - this resource is intentionally
    scope-wide (shared by `position_scope`, `positions_by_broker`,
    `cost_value_pl` and `performance`) so it is loaded at most once.
    """

    async def _load(session: AsyncSession) -> PortfolioReportResponse:
        query = PortfolioReportQuery(
            broker_ids=list(scope.broker_scope) if scope.broker_scope else None,
            date_range=OpenDateRangeModel(start=scope.period_start, end=scope.period_end),
            target_currency=scope.target_currency,
            include_summary=True,
            include_history=False,
            include_allocation_history=False,
            include_breakdown=False,
            include_positions_contribution=True,
        )
        return await PortfolioService(session).get_report(user_id=scope.user_id, query=query)

    return _load


def load_asset_market_prices(scope: BuildScope):
    """Build the target-currency price loader for `asset.market_snapshot`."""

    async def _load(session: AsyncSession) -> PriceResultsResource:
        results = await AssetSourceManager.get_prices_bulk(
            [
                FAPriceQueryItem(
                    asset_id=scope.asset_id,  # type: ignore[arg-type]
                    date_range=DateRangeModel(
                        start=scope.period_start,
                        end=scope.period_end,
                    ),
                    include_price=True,
                    include_events=False,
                    target_currency=scope.target_currency,
                )
            ],
            session,
        )
        return PriceResultsResource.from_results(results)

    return _load


def load_asset_lots(scope: BuildScope):
    """Builds the `db_resource` loader for `ASSET_LOTS_RESOURCE` (LOT_SUMMARY only).

    Requests the full lot history (`date_from=None`) up to
    `scope.period_end` so `asset_core.build_lot_detail` can apply the
    "all open/partial + closed with closing_date >= period_start" rule
    itself - restricting `date_from` here would silently drop lots this
    component is required to retain.
    """

    async def _load(session: AsyncSession) -> LotsAnalysisResponse:
        return await LotsAnalysisService(session).get_lots_analysis(
            user_id=scope.user_id,
            asset_id=scope.asset_id,  # type: ignore[arg-type]  # ASSET scope guarantees asset_id is set
            broker_ids=list(scope.broker_scope) if scope.broker_scope else None,
            date_from=None,
            date_to=scope.period_end,
            target_currency=scope.target_currency,
            selected_lot_ids=None,
            requested_analyses=[LotAnalysisType.LOT_SUMMARY],
        )

    return _load


ASSET_METADATA_RESOURCE = ResourceKey("asset.core.metadata", AssetMetadataResource)
ASSET_REPORT_RESOURCE = ResourceKey("asset.core.report", PortfolioReportResponse)
ASSET_LOTS_RESOURCE = ResourceKey("asset.core.lots", LotsAnalysisResponse)
ASSET_MARKET_PRICES_RESOURCE = ResourceKey(
    "asset.core.market_prices",
    PriceResultsResource,
)


def scoped_holdings(report: PortfolioReportResponse, asset_id: int) -> Sequence:
    """Deterministically ordered (by broker_id) holdings for `asset_id` within `report`."""
    holdings = [] if report.summary is None else [h for h in report.summary.holdings if h.asset_id == asset_id and h.broker_id is not None]
    return tuple(sorted(holdings, key=lambda h: h.broker_id))


def all_open_holdings(report: PortfolioReportResponse) -> Sequence:
    """Every open-position holding leg in the scoped report, ordered by (asset_id, broker_id).

    Unlike `scoped_holdings` (which narrows to one asset), this returns the
    whole scoped-portfolio open-position universe the `asset.position_scope`
    portfolio-role denominator aggregates over. The report is already scoped
    to `BuildScope.broker_scope` at load time (see `load_asset_report`), so
    this is exactly the accessible/whole or broker-scoped portfolio depending
    on whether a broker scope was requested. Legs with a `None` `broker_id`
    (broker-less reconciliation rows) are excluded, matching `scoped_holdings`.
    """
    holdings = [] if report.summary is None else [h for h in report.summary.holdings if h.broker_id is not None]
    return tuple(sorted(holdings, key=lambda h: (h.asset_id, h.broker_id)))


def scoped_contributions(report: PortfolioReportResponse, asset_id: int) -> Sequence:
    """Deterministically ordered (by broker_id) period contributions for `asset_id` within `report`."""
    if report.positions_contribution is None:
        return ()
    contributions = [c for c in report.positions_contribution.positions if c.asset_id == asset_id]
    return tuple(sorted(contributions, key=lambda c: c.broker_id))


__all__ = [
    "ASSET_LOTS_RESOURCE",
    "ASSET_MARKET_PRICES_RESOURCE",
    "ASSET_METADATA_RESOURCE",
    "ASSET_REPORT_RESOURCE",
    "AssetMarketSnapshotResource",
    "AssetMetadataResource",
    "AssetNotFoundError",
    "AssetPriceObservationData",
    "load_asset_lots",
    "load_asset_market_prices",
    "load_asset_metadata",
    "load_asset_report",
    "market_snapshot_from_price_result",
    "scoped_contributions",
    "scoped_holdings",
    "all_open_holdings",
]
