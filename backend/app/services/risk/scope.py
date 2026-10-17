"""A risk request's scope: who may read it, which assets it holds with which weights, and their prepared series."""

from __future__ import annotations

from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from pydantic import ValidationError
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetProviderAssignment, BrokerUserAccess, PriceHistory
from backend.app.logging_config import get_logger
from backend.app.schemas.assets.metadata import FAClassificationParams
from backend.app.schemas.common import DateRangeModel, OpenDateRangeModel
from backend.app.schemas.portfolio import (
    DataQualityExclusionReason,
    DataQualityReport,
    PortfolioReportQuery,
    PortfolioReportResponse,
)
from backend.app.schemas.prices import FAPriceQueryItem
from backend.app.schemas.risk import (
    AssetRiskScope,
    AssetSetRiskScope,
    PortfolioRiskScope,
    PreparedAssetSeriesSet,
    RiskExcludedAsset,
    RiskQueryRequest,
    RiskWarning,
)
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.financial_math.weights import share_of
from backend.app.services.market_series import prepare_asset_series_set
from backend.app.services.portfolio_service import PortfolioService
from backend.app.services.risk.base import RiskAssetClassification, resource_limit_error
from backend.app.services.risk.scenario_catalog import get_loaded_risk_scenario_catalog
from backend.app.utils.date_range_limits import BulkTooManyDaysError, range_span_floor
from backend.app.utils.datetime_utils import latest_range_end

logger = get_logger(__name__)


class RiskScopeNotFoundError(ValueError):
    """Requested risk scope does not exist."""


class RiskScopeAccessError(PermissionError):
    """Current user cannot access the requested risk scope."""


@dataclass(frozen=True, slots=True)
class ScopeInputs:
    requested_asset_ids: tuple[int, ...]
    weights: dict[int, float]
    asset_values: dict[int, Decimal]
    cash_weight: float
    scope_value: Optional[Decimal]
    portfolio_report: Optional[PortfolioReportResponse]
    data_quality: DataQualityReport
    warnings: tuple[RiskWarning, ...]
    composition_error: Optional[str] = None
    broker_ids: tuple[int, ...] = ()
    composition_as_of: Optional[date] = None
    slice_asset_ids: tuple[int, ...] = ()


def bounded_range(date_range: DateRangeModel) -> DateRangeModel:
    """``date_range`` as a risk analysis may walk it, day by day over prices (R13-SEC8-1b).

    It ends by ``latest_range_end()`` (tomorrow) and starts no earlier than ``range_span_floor()`` of that end
    (``RANGE_SPAN_LIMIT_DAYS``, 100 years before it: X-R55's span limit); a start after that end moves to it. The price
    query bounds only the end and backward-fills a range from its start, so without the floor a price stored long ago
    would let a range starting just after it walk every day since. A range already within those bounds comes back as
    it is.
    """
    requested_end = date_range.end or date_range.start
    end = min(requested_end, latest_range_end())
    start = min(max(date_range.start, range_span_floor(end)), end)
    if (start, end) == (date_range.start, requested_end):
        return date_range
    return DateRangeModel(start=start, end=end)


def scope_reference(
    request: RiskQueryRequest,
    *,
    broker_ids: tuple[int, ...] = (),
    slice_asset_ids: tuple[int, ...] = (),
) -> str:
    scope = request.scope
    if isinstance(scope, AssetRiskScope):
        return f"asset:{scope.asset_id}"
    if isinstance(scope, AssetSetRiskScope):
        return "asset_set:" + ",".join(str(asset_id) for asset_id in scope.asset_ids)
    suffix = ",".join(str(broker_id) for broker_id in broker_ids) or "none"
    reference = f"portfolio:{suffix}"
    if slice_asset_ids:
        reference += "/assets:" + ",".join(str(asset_id) for asset_id in sorted(slice_asset_ids))
    return reference


def scope_exclusions(
    scope_asset_ids: tuple[int, ...],
    prepared: PreparedAssetSeriesSet,
    never_priced_asset_ids: frozenset[int] = frozenset(),
) -> tuple[RiskExcludedAsset, ...]:
    """The scope assets left without a return series, each with the reason the preparation recorded.

    `insufficient_history` when it recorded none: the asset has prices, but no return series came out
    of them. A missing price is `no_price_source` for an asset nothing has ever priced — a permanent
    state, where `missing_price` is an occasional one.
    """
    usable_asset_ids = {item.returns.asset_id for item in prepared.series if item.returns.points}
    recorded = {item.asset_id: item.reason.value for item in prepared.data_quality.unusable_assets}
    exclusions: list[RiskExcludedAsset] = []
    for asset_id in scope_asset_ids:
        if asset_id in usable_asset_ids:
            continue
        reason = recorded.get(asset_id, "insufficient_history")
        if reason == DataQualityExclusionReason.MISSING_PRICE and asset_id in never_priced_asset_ids:
            reason = "no_price_source"
        exclusions.append(RiskExcludedAsset(asset_id=asset_id, reason=reason))
    return tuple(exclusions)


async def load_scope_inputs(  # noqa: C901 — scope-variant dispatch + sequential composition validation
    db: AsyncSession,
    *,
    user_id: int,
    request: RiskQueryRequest,
) -> ScopeInputs:
    scope = request.scope
    if isinstance(scope, AssetRiskScope):
        return ScopeInputs(
            requested_asset_ids=(scope.asset_id,),
            weights={},
            asset_values={},
            cash_weight=0,
            scope_value=None,
            portfolio_report=None,
            data_quality=DataQualityReport(),
            warnings=(),
        )
    if isinstance(scope, AssetSetRiskScope):
        return ScopeInputs(
            requested_asset_ids=tuple(scope.asset_ids),
            weights={},
            asset_values={},
            cash_weight=0,
            scope_value=None,
            portfolio_report=None,
            data_quality=DataQualityReport(),
            warnings=(),
        )

    if not isinstance(scope, PortfolioRiskScope):  # pragma: no cover - discriminated Pydantic union prevents this
        raise TypeError(f"Unsupported risk scope: {type(scope).__name__}")

    accessible_broker_ids = await load_accessible_broker_ids(db, user_id)
    requested_broker_ids = tuple(scope.broker_ids or ())
    if requested_broker_ids:
        inaccessible_broker_ids = tuple(sorted(set(requested_broker_ids) - set(accessible_broker_ids)))
        if inaccessible_broker_ids:
            broker_list = ", ".join(str(broker_id) for broker_id in inaccessible_broker_ids)
            raise RiskScopeAccessError(f"Broker subset is not fully accessible: {broker_list}")
        effective_broker_ids = requested_broker_ids
        report_broker_ids: Optional[list[int]] = list(effective_broker_ids)
    else:
        effective_broker_ids = accessible_broker_ids
        report_broker_ids = None

    # R13-SEC7-1: the report (and the composition date) end by latest_range_end(); a start after that end moves to it
    date_end = min(request.date_range.end or request.date_range.start, latest_range_end())
    report = await PortfolioService(db).get_report(
        user_id=user_id,
        query=PortfolioReportQuery(
            broker_ids=report_broker_ids,
            date_range=OpenDateRangeModel(
                start=min(request.date_range.start, date_end),
                end=date_end,
            ),
            target_currency=request.target_currency,
            include_summary=True,
            include_history=True,
            include_allocation_history=False,
            include_breakdown=False,
            include_positions_contribution=False,
        ),
    )
    summary = report.summary
    if summary is None:
        raise RuntimeError("Portfolio report omitted required summary")

    requested_asset_ids = tuple(sorted({holding.asset_id for holding in summary.holdings}))
    warnings: list[RiskWarning] = []
    slice_asset_ids: tuple[int, ...] = ()
    if scope.asset_ids:
        held_asset_ids = set(requested_asset_ids)
        slice_asset_ids = tuple(asset_id for asset_id in scope.asset_ids if asset_id in held_asset_ids)
        if not slice_asset_ids:
            raise RiskScopeNotFoundError(f"No requested asset is held in the selected portfolio scope: {sorted(scope.asset_ids)}")
        unheld_asset_ids = tuple(asset_id for asset_id in scope.asset_ids if asset_id not in held_asset_ids)
        if unheld_asset_ids:
            warnings.append(
                RiskWarning(
                    code="slice_assets_not_held",
                    message="Some requested assets are not held in the selected portfolio scope and were ignored.",
                    details={"asset_ids": list(unheld_asset_ids)},
                    message_i18n_key="risk.warnings.slice_assets_not_held",
                )
            )
        requested_asset_ids = slice_asset_ids

    asset_values: dict[int, Decimal] = {asset_id: Decimal("0") for asset_id in requested_asset_ids}
    for holding in summary.holdings:
        if holding.asset_id in asset_values and holding.current_value is not None:
            asset_values[holding.asset_id] += holding.current_value

    # A slice is renormalized to 100% of itself (D59): its denominator is the slice
    # value, not net worth, so monetary outputs stay coherent with its weights.
    scope_value = sum(asset_values.values(), Decimal("0")) if slice_asset_ids else summary.net_worth.amount
    weights: dict[int, float] = {}
    composition_error: Optional[str] = None
    if scope_value > 0:
        weights = {asset_id: float(share_of(value, scope_value)) for asset_id, value in asset_values.items() if value >= 0}
        if any(value < 0 for value in asset_values.values()):
            composition_error = "Negative asset values are outside the current-composition contract"
    elif requested_asset_ids:
        composition_error = "Current composition requires positive slice value" if slice_asset_ids else "Current composition requires positive scope NAV"

    asset_weight = sum(weights.values())
    if asset_weight > 1 + 1e-9:
        composition_error = "Negative cash or leveraged composition is outside the first-wave contract"
        cash_weight = 0.0
    else:
        cash_weight = max(0.0, 1.0 - asset_weight)

    # A slice carries no cash residual, so the in-transit comparison below — which
    # only describes the zero-return residual of a whole scope — does not apply.
    explicit_cash_weight = float(summary.cash_total.amount / scope_value) if scope_value > 0 else 0.0
    if not slice_asset_ids and summary.in_transit_market_value is not None and summary.in_transit_market_value.amount != 0 and not abs(cash_weight - explicit_cash_weight) < 1e-9:
        warnings.append(
            RiskWarning(
                code="zero_risk_residual_includes_in_transit",
                message="The zero-return residual includes in-transit value not represented by an asset return series.",
                message_i18n_key="risk.warnings.zero_risk_residual_includes_in_transit",
            )
        )

    return ScopeInputs(
        requested_asset_ids=requested_asset_ids,
        weights=weights,
        asset_values=asset_values,
        cash_weight=cash_weight,
        scope_value=scope_value,
        portfolio_report=report,
        data_quality=report.data_quality or DataQualityReport(),
        warnings=tuple(warnings),
        composition_error=composition_error,
        broker_ids=effective_broker_ids,
        composition_as_of=date_end,
        slice_asset_ids=slice_asset_ids,
    )


async def load_accessible_broker_ids(db: AsyncSession, user_id: int) -> tuple[int, ...]:
    result = await db.execute(select(BrokerUserAccess.broker_id).where(BrokerUserAccess.user_id == user_id))
    return tuple(sorted(set(result.scalars().all())))


async def load_existing_asset_ids(db: AsyncSession, asset_ids: set[int]) -> set[int]:
    if not asset_ids:
        return set()
    result = await db.execute(select(Asset.id).where(Asset.id.in_(asset_ids)))
    return set(result.scalars().all())


async def load_never_priced_asset_ids(db: AsyncSession, asset_ids: tuple[int, ...]) -> frozenset[int]:
    """The assets among `asset_ids` that no provider is assigned to and no price was ever stored for.

    Nothing will price them, so their missing price is permanent (developer's decision of
    29/09/2026). Both facts are asked in one statement, issued only for a request that excludes
    some asset for a missing price.
    """
    if not asset_ids:
        return frozenset()
    sourced = exists().where(AssetProviderAssignment.asset_id == Asset.id)
    priced = exists().where(PriceHistory.asset_id == Asset.id)
    result = await db.execute(select(Asset.id).where(Asset.id.in_(asset_ids), ~sourced, ~priced))
    return frozenset(result.scalars().all())


async def load_asset_classifications(
    db: AsyncSession,
    asset_ids: tuple[int, ...],
) -> dict[int, RiskAssetClassification]:
    if not asset_ids:
        return {}
    result = await db.execute(
        select(
            Asset.id,
            Asset.asset_type,
            Asset.classification_params,
        ).where(Asset.id.in_(asset_ids))
    )
    classifications: dict[int, RiskAssetClassification] = {}
    for asset_id, asset_type, raw_classification in result.all():
        parsed: Optional[FAClassificationParams] = None
        metadata_error: Optional[str] = None
        if raw_classification:
            try:
                parsed = FAClassificationParams.model_validate_json(raw_classification) if isinstance(raw_classification, str) else FAClassificationParams.model_validate(raw_classification)
            except (TypeError, ValueError, ValidationError) as exc:
                metadata_error = "invalid_classification_metadata"
                logger.exception(
                    "Invalid asset classification metadata",
                    asset_id=asset_id,
                    error=str(exc),
                )
        classifications[int(asset_id)] = RiskAssetClassification(
            asset_class=(asset_type.value if hasattr(asset_type, "value") else str(asset_type)),
            sector_exposures=({bucket: float(weight) for bucket, weight in parsed.sector_area.distribution.items()} if parsed is not None and parsed.sector_area is not None else None),
            geography_exposures=({bucket: float(weight) for bucket, weight in parsed.geographic_area.distribution.items()} if parsed is not None and parsed.geographic_area is not None else None),
            metadata_error=metadata_error,
        )
    return classifications


def geography_group_members() -> dict[str, frozenset[str]]:
    catalog = get_loaded_risk_scenario_catalog()
    return {group.id: frozenset(group.members) for group in catalog.geography_groups}


async def prepare_asset_series(
    db: AsyncSession,
    *,
    asset_ids: tuple[int, ...],
    date_range: DateRangeModel,
    target_currency: str,
    market_holidays: AbstractSet[date] = frozenset(),
) -> PreparedAssetSeriesSet:
    if not asset_ids:
        return prepare_asset_series_set(
            [],
            requested_range=date_range,
            target_currency=target_currency,
            market_holidays=market_holidays,
        )
    date_end = date_range.end or date_range.start
    load_start = date_range.start
    if load_start > date.min:
        load_start -= timedelta(days=1)
    try:
        price_results = await AssetSourceManager.get_prices_bulk(
            [
                FAPriceQueryItem(
                    asset_id=asset_id,
                    date_range=DateRangeModel(
                        start=load_start,
                        end=date_end,
                    ),
                    target_currency=target_currency,
                )
                for asset_id in asset_ids
            ],
            db,
        )
    except BulkTooManyDaysError as exc:
        # J-50: the prices of these assets over this period are more per-day points than one request may build (Z-25):
        # a size limit, refused as every other one is (D379), with the settings that bring it back within reach.
        raise resource_limit_error(
            f"The prices of {len(asset_ids)} asset(s) over this period would build {exc.item_days} per-day points, more than {exc.max_item_days}",
            metric="price_item_days",
            actual=exc.item_days,
            limit=exc.max_item_days,
        ) from exc
    return prepare_asset_series_set(
        price_results,
        requested_range=date_range,
        target_currency=target_currency,
        market_holidays=market_holidays,
    )
