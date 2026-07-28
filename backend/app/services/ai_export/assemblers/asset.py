"""Asset-domain AI Export snapshot assembler."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

import pycountry
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset
from backend.app.schemas.ai_export import (
    AiExportAssetFacts,
    AiExportAssetIdentity,
    AiExportAssetMarketFacts,
    AiExportAssetPricePoint,
    AiExportAssetSnapshotRequest,
    AiExportAssetSnapshotResponse,
    AiExportAssetTargetReference,
    AiExportAssetTask,
    AiExportDetailLevel,
    AiExportDomain,
    AiExportDomainNote,
    AiExportFifoSummary,
    AiExportMetricSemantic,
    AiExportNoteSource,
    AiExportNoteSubject,
    AiExportPosition,
    AiExportValuationReference,
    AiExportValuationSource,
)
from backend.app.schemas.assets import FAClassificationParams
from backend.app.schemas.common import BackwardFillInfo, Currency, DateRangeModel, OpenDateRangeModel
from backend.app.schemas.portfolio import LotAnalysisType, PortfolioReportQuery
from backend.app.schemas.prices import FAAssetEventPointOut, FAPricePoint, FAPriceQueryItem
from backend.app.schemas.signals import SignalEventPoint, SignalPricePoint
from backend.app.services.ai_export.assemblers.shared import (
    AiExportEntityNotFoundError,
    AiExportResolvedRanges,
    AiExportSourceFailureError,
    AiExportTaskNotApplicableError,
    Clock,
    build_methodology,
    build_semantics,
    build_snapshot_meta,
    finalize_response,
    neutral_export_stats,
    profile_allows,
    profile_requires,
    resolve_ranges,
    utc_now,
)
from backend.app.services.ai_export.normalization import (
    ObservedSourcePoint,
    build_last_buy_valuation_reference,
    build_last_seed_valuation_reference,
    build_normalized_return,
    relative_distance_pct,
)
from backend.app.services.ai_export.sampling import (
    NumericPoint,
    round_asset_price,
    round_compact_volume,
    round_decimal_places,
    round_money,
    round_percentage,
    sample_and_round_numeric_points,
)
from backend.app.services.ai_export.service import AiExportPreparedRequest
from backend.app.services.ai_export.technical import (
    PreparedTechnicalTarget,
    combine_technical_results,
    execute_technical_target,
    prepare_technical_target,
)
from backend.app.services.asset_source import AssetSourceManager
from backend.app.services.lots_analysis_service import LotsAnalysisService
from backend.app.services.portfolio_service import PortfolioService

AssetLoader = Callable[[AsyncSession, int], Awaitable[Asset | None]]
PriceBulkLoader = Callable[[list[FAPriceQueryItem], AsyncSession], Awaitable[Any]]
PortfolioServiceFactory = Callable[[AsyncSession], Any]
LotsServiceFactory = Callable[[AsyncSession], Any]
TechnicalPreparer = Callable[..., PreparedTechnicalTarget | None]
TechnicalExecutor = Callable[..., Awaitable[Any]]


async def _default_asset_loader(session: AsyncSession, asset_id: int) -> Asset | None:
    return await session.get(Asset, asset_id)


def _enum_value(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _currency(code: str, amount: Decimal | None) -> Currency | None:
    return Currency(code=code, amount=round_money(amount)) if amount is not None else None


def _sum_optional(values: Sequence[Decimal | None]) -> Decimal | None:
    if not values or any(value is None for value in values):
        return None
    return sum((value for value in values if value is not None), start=Decimal("0"))


def _top_distribution_label(distribution: dict[str, Decimal] | None) -> str | None:
    if not distribution:
        return None
    return sorted(distribution.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _parse_classification(asset: Asset) -> FAClassificationParams | None:
    raw = asset.classification_params
    if raw is None:
        return None
    try:
        if isinstance(raw, FAClassificationParams):
            return raw
        if isinstance(raw, str):
            return FAClassificationParams.model_validate_json(raw)
        return FAClassificationParams.model_validate(raw)
    except (TypeError, ValueError):
        return None


def _geography_label(code: str | None) -> str | None:
    if code is None:
        return None
    country = pycountry.countries.get(alpha_3=code)
    return country.name if country is not None else code


def _identity(
    asset: Asset,
    classification: FAClassificationParams | None,
    target_currency: str,
) -> AiExportAssetIdentity:
    sector = _top_distribution_label(classification.sector_area.distribution) if classification is not None and classification.sector_area is not None else None
    geography_code = _top_distribution_label(classification.geographic_area.distribution) if classification is not None and classification.geographic_area is not None else None
    return AiExportAssetIdentity(
        asset_id=asset.id,
        name=asset.display_name,
        ticker=asset.identifier_ticker,
        isin=asset.identifier_isin,
        asset_type=_enum_value(asset.asset_type),
        sector=sector,
        geography=_geography_label(geography_code),
        trading_currency=asset.currency,
        valuation_currency=target_currency,
    )


def _valuation_source(holdings: Sequence[Any], market_value: Decimal | None) -> AiExportValuationSource:
    raw_sources = [_enum_value(holding.valuation_source) or "MISSING" for holding in holdings]
    distinct = set(raw_sources)
    if len(distinct) > 1:
        return AiExportValuationSource.MIXED
    source = raw_sources[0] if raw_sources else None
    mapped = {
        "MARKET_PRICE": AiExportValuationSource.MARKET_PRICE,
        "LAST_BUY_PRICE": AiExportValuationSource.LAST_VISIBLE_BUY_UNIT_PRICE,
        "LAST_SEED_COST": AiExportValuationSource.LAST_SEED_COST,
        "MISSING": AiExportValuationSource.MISSING,
    }.get(source, AiExportValuationSource.MISSING)
    if mapped == AiExportValuationSource.MARKET_PRICE and market_value is None:
        return AiExportValuationSource.MISSING
    return mapped


def _uniform_unit_price(holdings: Sequence[Any]) -> Decimal | None:
    prices = [holding.current_price for holding in holdings]
    if not prices or any(price is None for price in prices):
        return None
    first = prices[0]
    return first if all(price == first for price in prices[1:]) else None


def _aggregate_position(
    *,
    asset: Asset,
    holdings: Sequence[Any],
    contributions: Sequence[Any],
    portfolio_summary: Any,
    target_currency: str,
) -> AiExportPosition | None:
    if not holdings:
        return None

    ordered_holdings = sorted(
        holdings,
        key=lambda holding: (
            holding.broker_id is None,
            holding.broker_id or 0,
        ),
    )
    quantity = sum(
        (Decimal(str(holding.quantity)) for holding in ordered_holdings),
        start=Decimal("0"),
    )
    cost_parts = [(Decimal(str(holding.wac_per_unit)) * Decimal(str(holding.quantity)) if holding.wac_per_unit is not None else None) for holding in ordered_holdings]
    cost_basis_amount = _sum_optional(cost_parts)
    average_cost_amount = cost_basis_amount / quantity if cost_basis_amount is not None and not quantity.is_zero() else None
    market_value_amount = _sum_optional([holding.current_value for holding in ordered_holdings])
    current_unit_price_amount = _uniform_unit_price(ordered_holdings)
    unrealized_amount = _sum_optional([holding.gain_loss for holding in ordered_holdings])

    holding_broker_ids = {holding.broker_id for holding in ordered_holdings}
    contribution_broker_ids = {contribution.broker_id for contribution in contributions}
    contribution_coverage_complete = holding_broker_ids.issubset(contribution_broker_ids)
    ordered_contributions = sorted(
        contributions,
        key=lambda contribution: (
            contribution.broker_id is None,
            contribution.broker_id or 0,
        ),
    )
    if contribution_coverage_complete:
        period_pnl_amount = _sum_optional([contribution.period_pnl for contribution in ordered_contributions])
        realized_amount = _sum_optional([contribution.period_realized_gain_loss for contribution in ordered_contributions])
        income_amount = _sum_optional([contribution.period_income for contribution in ordered_contributions])
        start_value = _sum_optional([contribution.start_value for contribution in ordered_contributions])
    else:
        period_pnl_amount = None
        realized_amount = None
        income_amount = None
        start_value = None
    period_pnl_pct = round_percentage(period_pnl_amount / abs(start_value) * Decimal("100")) if period_pnl_amount is not None and start_value is not None and not start_value.is_zero() else None

    net_worth_amount = portfolio_summary.net_worth.amount if portfolio_summary is not None and portfolio_summary.net_worth is not None else None
    weight_pct = round_percentage(market_value_amount / net_worth_amount * Decimal("100")) if market_value_amount is not None and net_worth_amount is not None and not net_worth_amount.is_zero() else None
    source = _valuation_source(ordered_holdings, market_value_amount)
    if source == AiExportValuationSource.MISSING:
        current_unit_price_amount = None
        market_value_amount = None
        weight_pct = None
        period_pnl_amount = None
        period_pnl_pct = None
        unrealized_amount = None

    return AiExportPosition(
        asset_id=asset.id,
        name=asset.display_name,
        ticker=asset.identifier_ticker,
        broker_ids=sorted({holding.broker_id for holding in ordered_holdings if holding.broker_id is not None}),
        quantity=quantity,
        trading_currency=asset.currency,
        valuation_currency=target_currency,
        valuation_source=source,
        current_unit_price=_currency(target_currency, current_unit_price_amount),
        average_unit_cost=_currency(target_currency, average_cost_amount),
        cost_basis=_currency(target_currency, cost_basis_amount),
        market_value=_currency(target_currency, market_value_amount),
        weight_pct=weight_pct,
        period_pnl_amount=_currency(target_currency, period_pnl_amount),
        period_pnl_pct=period_pnl_pct,
        realized_pnl_amount=_currency(target_currency, realized_amount),
        unrealized_pnl_amount=_currency(target_currency, unrealized_amount),
        period_income_amount=_currency(target_currency, income_amount),
    )


def _signal_backfill(point: FAPricePoint) -> BackwardFillInfo | None:
    source = point.backward_fill_info
    if source is None:
        return None
    candidates: list[tuple[int, date]] = [(source.days_back, source.actual_rate_date)]
    if source.fx_days_back is not None and source.fx_rate_date is not None:
        candidates.append((source.fx_days_back, source.fx_rate_date))
    days_back, actual_date = max(candidates, key=lambda item: item[0])
    return BackwardFillInfo(actual_rate_date=actual_date, days_back=days_back)


def _signal_prices(
    prices: Sequence[FAPricePoint],
    target_currency: str,
) -> tuple[SignalPricePoint, ...]:
    compatible = [point for point in prices if point.currency is None or point.currency == target_currency]
    by_date = {point.date: point for point in compatible}
    return tuple(
        SignalPricePoint(
            date=point.date,
            open=point.open,
            high=point.high,
            low=point.low,
            close=point.close,
            volume=point.volume,
            backward_fill_info=_signal_backfill(point),
        )
        for point in (by_date[point_date] for point_date in sorted(by_date))
    )


def _signal_events(events: Sequence[FAAssetEventPointOut]) -> tuple[SignalEventPoint, ...]:
    return tuple(
        SignalEventPoint(
            date=event.date,
            type=event.type,
            value=event.value.amount,
            metadata={
                "event_id": event.id,
                "is_auto": event.is_auto,
                "currency": event.value.code,
            },
        )
        for event in sorted(events, key=lambda item: (item.date, item.id))
    )


def _is_observed(point: SignalPricePoint) -> bool:
    return point.backward_fill_info is None or point.backward_fill_info.days_back == 0


def _observed_prices(
    points: Sequence[SignalPricePoint],
    selected_range: DateRangeModel,
) -> tuple[SignalPricePoint, ...]:
    return tuple(point for point in points if selected_range.start <= point.date <= selected_range.end and _is_observed(point))


def _market_facts(
    context_observed: Sequence[SignalPricePoint],
    selected_observed: Sequence[SignalPricePoint],
    target_currency: str,
    sampling: Any,
) -> AiExportAssetMarketFacts | None:
    if not context_observed:
        return None
    numeric = tuple(NumericPoint(date=point.date, value=point.close) for point in context_observed)
    sampled = sample_and_round_numeric_points(
        numeric,
        sampling,
        round_asset_price,
    )
    raw_by_date = {point.date: point for point in context_observed}
    latest = context_observed[-1]
    enough_selected_history = len(selected_observed) >= 2
    first = selected_observed[0] if enough_selected_history else None
    selected_latest = selected_observed[-1] if enough_selected_history else None
    prior_high = max((point.close for point in selected_observed[:-1]), default=None) if enough_selected_history else None
    high = max(prior_high, selected_latest.close) if prior_high is not None and selected_latest is not None else None
    return AiExportAssetMarketFacts(
        current_price=Currency(
            code=target_currency,
            amount=round_asset_price(latest.close),
        ),
        price_date=latest.date,
        period_change_pct=(round_percentage(relative_distance_pct(selected_latest.close, first.close)) if first is not None and selected_latest is not None else None),
        drawdown_from_period_high_pct=(round_percentage(relative_distance_pct(selected_latest.close, high)) if selected_latest is not None and high is not None else None),
        sampled_prices=[
            AiExportAssetPricePoint(
                date=point.date,
                close=Currency(code=target_currency, amount=point.value),
                volume=(round_compact_volume(raw_by_date[point.date].volume) if raw_by_date[point.date].volume is not None and raw_by_date[point.date].volume >= 0 else None),
            )
            for point in sampled
        ],
    )


def _normalized_return(
    observed: Sequence[SignalPricePoint],
    selected_range: DateRangeModel,
    sampling: Any,
    target_currency: str,
):
    return build_normalized_return(
        [
            ObservedSourcePoint(
                date=point.date,
                source_value=point.close,
            )
            for point in observed
        ],
        selected_range,
        sampling,
        source_currency=target_currency,
        source_rounding=round_asset_price,
    )


def _uniform_valuation_reference(
    holdings: Sequence[Any],
) -> AiExportValuationReference | None:
    if not holdings:
        return None
    sources = {_enum_value(holding.valuation_source) for holding in holdings}
    if len(sources) != 1:
        return None
    source = next(iter(sources))
    if source not in {"LAST_BUY_PRICE", "LAST_SEED_COST"}:
        return None

    reference_keys = {
        (
            holding.valuation_reference_date,
            holding.valuation_reference_unit_price,
            holding.valuation_reference_currency,
            holding.valuation_effective_unit_price,
            holding.valuation_effective_currency,
            holding.valuation_split_adjusted,
        )
        for holding in holdings
    }
    if len(reference_keys) != 1:
        return None
    (
        reference_date,
        reference_price,
        reference_currency,
        effective_price,
        effective_currency,
        split_adjusted,
    ) = next(iter(reference_keys))
    if reference_date is None or reference_price is None or reference_currency is None:
        return None
    builder = build_last_buy_valuation_reference if source == "LAST_BUY_PRICE" else build_last_seed_valuation_reference
    return builder(
        reference_date,
        Decimal(str(reference_price)),
        reference_currency,
        effective_unit_price=(Decimal(str(effective_price)) if effective_price is not None else None),
        effective_currency=effective_currency,
        split_adjusted=bool(split_adjusted),
    )


def _fifo_summary(
    lots: Sequence[Any],
    target_currency: str,
    snapshot_as_of: date,
) -> AiExportFifoSummary:
    ordered = sorted(lots, key=lambda lot: (lot.opening_date, lot.lot_id))
    open_lots = [lot for lot in ordered if not Decimal(str(lot.open_quantity)).is_zero()]
    partial_lots = [lot for lot in open_lots if not Decimal(str(lot.realized_quantity)).is_zero()]
    closed_lots = [lot for lot in ordered if Decimal(str(lot.open_quantity)).is_zero()]
    ages = [Decimal((snapshot_as_of - lot.opening_date).days) for lot in open_lots]
    residual_cost = Decimal("0")
    for lot in open_lots:
        original_quantity = abs(Decimal(str(lot.original_quantity)))
        if original_quantity.is_zero():
            continue
        residual_cost += Decimal(str(lot.original_cost)) * abs(Decimal(str(lot.open_quantity))) / original_quantity
    market_value = _sum_optional([lot.open_value for lot in open_lots])
    unrealized = _sum_optional([lot.market_pnl for lot in open_lots])
    estimated_lots = [lot for lot in open_lots if _enum_value(lot.value_source) == "ESTIMATED_AT_COST"]
    estimated_value = _sum_optional([lot.open_value for lot in estimated_lots])
    in_transit_quantity = sum(
        (Decimal(str(custody.quantity)) for lot in open_lots for custody in lot.current_custody if custody.custody_type == "IN_TRANSIT"),
        start=Decimal("0"),
    )
    short_quantity = sum(
        (abs(Decimal(str(lot.open_quantity))) for lot in open_lots if lot.direction == "SHORT"),
        start=Decimal("0"),
    )
    return AiExportFifoSummary(
        open_lot_count=len(open_lots),
        partial_lot_count=len(partial_lots),
        closed_lot_count=len(closed_lots),
        average_age_days=(
            round_decimal_places(
                sum(ages, start=Decimal("0")) / Decimal(len(ages)),
                2,
            )
            if ages
            else None
        ),
        oldest_lot_date=(min(lot.opening_date for lot in open_lots) if open_lots else None),
        residual_cost_basis=_currency(target_currency, residual_cost),
        market_value=_currency(target_currency, market_value),
        realized_pnl_amount=_currency(
            target_currency,
            sum(
                (Decimal(str(lot.realized_pnl)) for lot in ordered),
                start=Decimal("0"),
            ),
        ),
        unrealized_pnl_amount=_currency(target_currency, unrealized),
        income_amount=_currency(
            target_currency,
            sum(
                (Decimal(str(lot.asset_income)) for lot in ordered),
                start=Decimal("0"),
            ),
        ),
        in_transit_quantity=(in_transit_quantity if not in_transit_quantity.is_zero() else None),
        short_quantity=(short_quantity if not short_quantity.is_zero() else None),
        estimated_at_cost_value=_currency(
            target_currency,
            estimated_value,
        ),
    )


def _domain_notes(
    *,
    asset: Asset,
    classification: FAClassificationParams | None,
    events: Sequence[FAAssetEventPointOut],
    ranges: AiExportResolvedRanges,
    profile: Any,
) -> list[AiExportDomainNote]:
    if not profile_allows(profile, "domain_notes"):
        return []
    notes: list[AiExportDomainNote] = []
    if classification is not None and classification.short_description:
        notes.append(
            AiExportDomainNote(
                subject=AiExportNoteSubject.ASSET,
                source=AiExportNoteSource.PROVIDER_OR_USER,
                text=classification.short_description[:4000],
                subject_reference=f"asset:{asset.id}",
            )
        )
    if profile_allows(profile, "events"):
        event_notes = [event for event in events if event.notes and ranges.selected_range.start <= event.date <= ranges.selected_range.end]
        limit = profile.detail_overlay.event_limits.max_events
        if limit is not None:
            event_notes = sorted(
                event_notes,
                key=lambda item: (item.date, item.id),
            )[-limit:]
        for event in event_notes:
            notes.append(
                AiExportDomainNote(
                    subject=AiExportNoteSubject.EVENT,
                    source=(AiExportNoteSource.PROVIDER if event.is_auto else AiExportNoteSource.MANUAL),
                    text=event.notes[:4000],
                    subject_reference=f"asset_event:{event.id}",
                    observed_at=event.date,
                )
            )
    return sorted(
        notes,
        key=lambda note: (
            note.observed_at or date.min,
            note.subject.value,
            note.subject_reference or "",
            note.text,
        ),
    )


def _metric_semantics(
    *,
    ranges: AiExportResolvedRanges,
    facts: AiExportAssetFacts,
) -> list[AiExportMetricSemantic]:
    semantics: list[AiExportMetricSemantic] = []
    if facts.market is not None:
        if facts.market.period_change_pct is not None:
            semantics.append(
                AiExportMetricSemantic(
                    metric_code="asset.period_change_pct",
                    unit="percentage_points",
                    denominator="first_observed_price",
                    method="simple_return",
                    period=ranges.selected_range,
                    cumulative=True,
                )
            )
        if facts.market.drawdown_from_period_high_pct is not None:
            semantics.append(
                AiExportMetricSemantic(
                    metric_code="asset.drawdown_from_period_high_pct",
                    unit="percentage_points",
                    denominator="period_high",
                    method="peak_to_latest",
                    period=ranges.selected_range,
                    cumulative=False,
                )
            )
    if facts.normalized_return is not None:
        semantics.append(
            AiExportMetricSemantic(
                metric_code="asset.normalized_return",
                unit="percentage_points",
                denominator="first_observed_price_in_window",
                method="observed_only_simple_return",
                period=ranges.technical_window,
                cumulative=True,
            )
        )
    if facts.current_position is not None and facts.current_position.weight_pct is not None:
        semantics.append(
            AiExportMetricSemantic(
                metric_code="asset.position_weight_pct",
                unit="percentage_points",
                denominator="portfolio_nav",
                method="market_value_share",
                period=DateRangeModel(
                    start=ranges.snapshot_as_of,
                    end=ranges.snapshot_as_of,
                ),
                cumulative=False,
            )
        )
    if facts.lot_summary is not None:
        semantics.append(
            AiExportMetricSemantic(
                metric_code="asset.fifo_lot_summary",
                unit="target_currency",
                method="runtime_fifo",
                period=ranges.selected_range,
                cumulative=True,
            )
        )
    return semantics


class AiExportAssetAssembler:
    """Assemble all resolved Asset task/detail profiles."""

    def __init__(
        self,
        *,
        asset_loader: AssetLoader = _default_asset_loader,
        price_bulk_loader: PriceBulkLoader = AssetSourceManager.get_prices_bulk,
        portfolio_service_factory: PortfolioServiceFactory = PortfolioService,
        lots_service_factory: LotsServiceFactory = LotsAnalysisService,
        technical_preparer: TechnicalPreparer = prepare_technical_target,
        technical_executor: TechnicalExecutor = execute_technical_target,
        clock: Clock = utc_now,
    ) -> None:
        self._asset_loader = asset_loader
        self._price_bulk_loader = price_bulk_loader
        self._portfolio_service_factory = portfolio_service_factory
        self._lots_service_factory = lots_service_factory
        self._technical_preparer = technical_preparer
        self._technical_executor = technical_executor
        self._clock = clock

    async def assemble(
        self,
        prepared: AiExportPreparedRequest,
        session: AsyncSession,
    ) -> AiExportAssetSnapshotResponse:
        request = prepared.request
        if not isinstance(request, AiExportAssetSnapshotRequest):
            raise TypeError("asset assembler requires AiExportAssetSnapshotRequest")

        try:
            asset = await self._asset_loader(session, request.asset_id)
        except Exception as exc:
            raise AiExportSourceFailureError(
                "asset_store",
                "load_asset",
                context={"asset_id": request.asset_id},
            ) from exc
        if asset is None:
            raise AiExportEntityNotFoundError("asset", request.asset_id)

        initial_ranges = resolve_ranges(prepared)
        selected_range = initial_ranges.selected_range
        snapshot_as_of = initial_ranges.snapshot_as_of
        summary = None
        holdings: list[Any] = []
        contributions: list[Any] = []
        if prepared.broker_scope:
            portfolio_query = PortfolioReportQuery(
                broker_ids=list(prepared.broker_scope),
                date_range=OpenDateRangeModel(
                    start=selected_range.start,
                    end=selected_range.end,
                ),
                target_currency=request.target_currency,
                include_summary=True,
                include_history=False,
                include_allocation_history=False,
                include_breakdown=False,
                include_positions_contribution=True,
            )
            try:
                portfolio_report = await self._portfolio_service_factory(session).get_report(prepared.user_id, portfolio_query)
            except Exception as exc:
                raise AiExportSourceFailureError(
                    "portfolio_service",
                    "get_report",
                    context={"asset_id": request.asset_id},
                ) from exc

            summary = portfolio_report.summary
            if summary is None:
                raise AiExportSourceFailureError(
                    "portfolio_service",
                    "missing_summary",
                    context={"asset_id": request.asset_id},
                )
            holdings = [holding for holding in summary.holdings if holding.asset_id == request.asset_id]
            contribution_section = portfolio_report.positions_contribution
            if contribution_section is not None:
                contributions = [contribution for contribution in contribution_section.positions if contribution.asset_id == request.asset_id]

        current_position = _aggregate_position(
            asset=asset,
            holdings=holdings,
            contributions=contributions,
            portfolio_summary=summary,
            target_currency=request.target_currency,
        )
        if request.task == AiExportAssetTask.POSITION_REVIEW and (current_position is None or current_position.quantity <= Decimal("0")):
            raise AiExportTaskNotApplicableError(
                prepared.resolved_profile.applicability_code,
                "no_positive_open_position",
                context={
                    "asset_id": request.asset_id,
                    "broker_ids": list(prepared.broker_scope),
                },
            )

        target = AiExportAssetTargetReference(
            kind="asset",
            asset_id=request.asset_id,
        )
        prepared_technical = self._technical_preparer(
            prepared.resolved_profile,
            target,
            initial_ranges.technical_window,
            target_currency=request.target_currency,
            nav_weight_pct=(abs(current_position.weight_pct) if current_position is not None and current_position.weight_pct is not None else Decimal("0")),
        )
        ranges = resolve_ranges(
            prepared,
            calculation_range=(prepared_technical.calculation_range if prepared_technical is not None else initial_ranges.technical_window),
            calculation_warmup_start=(prepared_technical.calculation_warmup_start if prepared_technical is not None else initial_ranges.technical_window.start),
        )
        load_range = DateRangeModel(
            start=min(
                ranges.selected_range.start,
                ranges.calculation_range.start,
            ),
            end=max(
                ranges.selected_range.end,
                ranges.calculation_range.end,
            ),
        )
        query = FAPriceQueryItem(
            asset_id=request.asset_id,
            date_range=load_range,
            include_price=True,
            include_events=(profile_allows(prepared.resolved_profile, "events") or profile_allows(prepared.resolved_profile, "domain_notes")),
            target_currency=request.target_currency,
            signals=[],
            annotation_requests=[],
        )
        try:
            raw_bulk = await self._price_bulk_loader([query], session)
        except Exception as exc:
            raise AiExportSourceFailureError(
                "asset_source",
                "get_prices_bulk",
                context={"asset_id": request.asset_id},
            ) from exc
        bulk_results = raw_bulk.results if hasattr(raw_bulk, "results") else raw_bulk
        price_result = next(
            (result for result in bulk_results if result.asset_id == request.asset_id),
            None,
        )
        if price_result is None:
            raise AiExportSourceFailureError(
                "asset_source",
                "missing_bulk_result",
                context={"asset_id": request.asset_id},
            )

        signal_prices = _signal_prices(
            price_result.prices,
            request.target_currency,
        )
        signal_events = _signal_events(price_result.events)
        technical_signal_prices = tuple(point for point in signal_prices if ranges.calculation_range.start <= point.date <= ranges.calculation_range.end)
        technical_signal_events = tuple(point for point in signal_events if ranges.calculation_range.start <= point.date <= ranges.calculation_range.end)
        if prepared_technical is not None:
            try:
                technical_result = await self._technical_executor(
                    prepared_technical,
                    technical_signal_prices,
                    technical_signal_events,
                    events_loaded=True,
                    source_capability=AssetSourceManager.derive_signal_source_capability(price_result.prices),
                )
            except Exception as exc:
                raise AiExportSourceFailureError(
                    "technical_runner",
                    "execute",
                    context={"asset_id": request.asset_id},
                ) from exc
            technical = combine_technical_results([technical_result])
        else:
            technical = combine_technical_results([])

        observed_history = tuple(point for point in signal_prices if _is_observed(point))
        selected_observed = _observed_prices(observed_history, ranges.selected_range)
        technical_observed = _observed_prices(observed_history, ranges.technical_window)
        market = _market_facts(
            technical_observed or selected_observed,
            selected_observed,
            request.target_currency,
            prepared.resolved_profile.detail_overlay.sampling,
        )
        normalized_return = (
            _normalized_return(
                observed_history,
                ranges.technical_window,
                prepared.resolved_profile.detail_overlay.sampling,
                request.target_currency,
            )
            if profile_allows(
                prepared.resolved_profile,
                "facts.normalized_return",
            )
            else None
        )
        valuation_reference = (
            _uniform_valuation_reference(holdings)
            if market is None
            and normalized_return is None
            and profile_allows(
                prepared.resolved_profile,
                "facts.valuation_reference",
            )
            else None
        )

        if request.task == AiExportAssetTask.DRAWDOWN_RECOVERY:
            if len(selected_observed) < 2:
                raise AiExportTaskNotApplicableError(
                    prepared.resolved_profile.applicability_code,
                    "insufficient_observed_prices",
                    context={
                        "asset_id": request.asset_id,
                        "observed_points": len(selected_observed),
                    },
                )
            prior_maximum = max((point.close for point in selected_observed[:-1]), default=None)
            if prior_maximum is None:
                raise AiExportTaskNotApplicableError(
                    prepared.resolved_profile.applicability_code,
                    "prior_maximum_unavailable",
                    context={"asset_id": request.asset_id},
                )
            if market is None or market.drawdown_from_period_high_pct is None:
                raise AiExportTaskNotApplicableError(
                    prepared.resolved_profile.applicability_code,
                    "drawdown_metric_unavailable",
                    context={"asset_id": request.asset_id},
                )

        lot_summary = None
        include_lots = (
            request.task == AiExportAssetTask.POSITION_REVIEW
            and request.detail_level != AiExportDetailLevel.COMPACT
            and profile_allows(
                prepared.resolved_profile,
                "facts.lot_summary",
            )
        )
        if include_lots and current_position is not None:
            lot_summary_required = profile_requires(
                prepared.resolved_profile,
                "facts.lot_summary",
            )
            try:
                lots_response = await self._lots_service_factory(session).get_lots_analysis(
                    user_id=prepared.user_id,
                    asset_id=request.asset_id,
                    broker_ids=list(prepared.broker_scope),
                    date_from=selected_range.start,
                    date_to=snapshot_as_of,
                    target_currency=request.target_currency,
                    selected_lot_ids=None,
                    requested_analyses=[LotAnalysisType.LOT_SUMMARY],
                )
            except Exception as exc:
                if lot_summary_required:
                    raise AiExportSourceFailureError(
                        "lots_analysis_service",
                        "get_lots_analysis",
                        context={"asset_id": request.asset_id},
                    ) from exc
            else:
                calculation_status = _enum_value(getattr(lots_response, "calculation_status", None))
                lots = getattr(lots_response, "lots", None)
                if calculation_status in {"COMPLETE", "DEGRADED"} and lots is not None:
                    try:
                        lot_summary = _fifo_summary(
                            lots,
                            request.target_currency,
                            snapshot_as_of,
                        )
                    except Exception as exc:
                        if lot_summary_required:
                            raise AiExportSourceFailureError(
                                "lots_analysis_service",
                                "aggregate_lot_summary",
                                context={
                                    "asset_id": request.asset_id,
                                    "calculation_status": calculation_status,
                                },
                            ) from exc
                elif lot_summary_required:
                    raise AiExportSourceFailureError(
                        "lots_analysis_service",
                        "unreliable_lot_summary",
                        context={
                            "asset_id": request.asset_id,
                            "calculation_status": calculation_status,
                        },
                    )

        classification = _parse_classification(asset)
        exported_position = (
            current_position
            if profile_allows(
                prepared.resolved_profile,
                "facts.current_position",
            )
            else None
        )
        facts = AiExportAssetFacts(
            identity=_identity(
                asset,
                classification,
                request.target_currency,
            ),
            market=market,
            current_position=exported_position,
            lot_summary=lot_summary,
            normalized_return=normalized_return,
            valuation_reference=valuation_reference,
        )
        response = AiExportAssetSnapshotResponse(
            domain=AiExportDomain.ASSET,
            task=request.task,
            detail_level=request.detail_level,
            meta=build_snapshot_meta(
                prepared,
                ranges,
                clock=self._clock,
            ),
            methodology=build_methodology(
                uses_weighted_average_cost=exported_position is not None,
                uses_runtime_fifo=lot_summary is not None,
            ),
            facts=facts,
            states=list(technical.states),
            technical=technical.technical,
            events=list(technical.events),
            coverage=technical.coverage,
            semantics=build_semantics(
                metric_semantics=_metric_semantics(
                    ranges=ranges,
                    facts=facts,
                ),
                signal_semantics=technical.signal_semantics,
                trading_currency=asset.currency,
                valuation_currency=request.target_currency,
            ),
            domain_notes=_domain_notes(
                asset=asset,
                classification=classification,
                events=price_result.events,
                ranges=ranges,
                profile=prepared.resolved_profile,
            ),
            export_stats=neutral_export_stats(),
        )
        return finalize_response(response)


async def assemble_asset_snapshot(
    prepared: AiExportPreparedRequest,
    session: AsyncSession,
    *,
    assembler: AiExportAssetAssembler | None = None,
) -> AiExportAssetSnapshotResponse:
    return await (assembler or AiExportAssetAssembler()).assemble(
        prepared,
        session,
    )


__all__ = [
    "AiExportAssetAssembler",
    "assemble_asset_snapshot",
]
