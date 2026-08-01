"""FX-domain AI Export snapshot assembler."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, localcontext
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset
from backend.app.schemas.ai_export import (
    AiExportDomain,
    AiExportFxExposureKind,
    AiExportFxExposureLink,
    AiExportFxExposureLinkage,
    AiExportFxExtrema,
    AiExportFxFacts,
    AiExportFxIdentity,
    AiExportFxPairTargetReference,
    AiExportFxRatePoint,
    AiExportFxSnapshotRequest,
    AiExportFxSnapshotResponse,
    AiExportFxTask,
    AiExportFxVolatility,
    AiExportMetricSemantic,
)
from backend.app.schemas.common import BackwardFillInfo, Currency, DateRangeModel, OpenDateRangeModel
from backend.app.schemas.portfolio import PortfolioReportQuery
from backend.app.schemas.signals import SignalPricePoint
from backend.app.services.ai_export.assemblers.shared import (
    AiExportSourceFailureError,
    AiExportTaskNotApplicableError,
    Clock,
    build_methodology,
    build_semantics,
    build_snapshot_meta,
    finalize_response,
    neutral_export_stats,
    profile_allows,
    resolve_ranges,
    utc_now,
)
from backend.app.services.ai_export.normalization import (
    ObservedSourcePoint,
    build_normalized_return,
    relative_distance_pct,
)
from backend.app.services.ai_export.sampling import (
    NumericPoint,
    round_fx_rate,
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
from backend.app.services.fx import convert_bulk
from backend.app.services.portfolio_service import PortfolioService

AssetLoader = Callable[[AsyncSession, int], Awaitable[Asset | None]]
ConvertBulk = Callable[..., Awaitable[Any]]
PortfolioServiceFactory = Callable[[AsyncSession], Any]
TechnicalPreparer = Callable[..., PreparedTechnicalTarget | None]
TechnicalExecutor = Callable[..., Awaitable[Any]]


@dataclass(frozen=True, slots=True)
class _CashExposureCandidate:
    linked_currency: str
    amount: Decimal
    broker_id: int | None


@dataclass(frozen=True, slots=True)
class _PositionExposureCandidate:
    linked_currency: str
    linkage: AiExportFxExposureLinkage
    current_value: Decimal | None
    asset_id: int
    broker_id: int | None


@dataclass(frozen=True, slots=True)
class _EffectiveRate:
    requested_date: date
    actual_date: date
    rate: Decimal
    backward_filled: bool


async def _default_asset_loader(session: AsyncSession, asset_id: int) -> Asset | None:
    return await session.get(Asset, asset_id)


def _inclusive_dates(date_range: DateRangeModel) -> tuple[date, ...]:
    end = date_range.end or date_range.start
    count = (end - date_range.start).days
    return tuple(date_range.start + timedelta(days=offset) for offset in range(count + 1))


def _cash_candidates(summary: Any, pair: frozenset[str]) -> list[_CashExposureCandidate]:
    candidates: list[_CashExposureCandidate] = []
    if summary is None:
        return candidates
    broker_breakdown = summary.by_broker
    if broker_breakdown:
        sources = [(breakdown.broker_id, balance) for breakdown in broker_breakdown for balance in breakdown.cash_balances]
    else:
        sources = [(None, balance) for balance in summary.cash_balances]
    for broker_id, balance in sources:
        amount = Decimal(str(balance.amount))
        if balance.code in pair and not amount.is_zero():
            candidates.append(
                _CashExposureCandidate(
                    linked_currency=balance.code,
                    amount=amount,
                    broker_id=broker_id,
                )
            )
    return sorted(
        candidates,
        key=lambda item: (
            item.linked_currency,
            item.broker_id is None,
            item.broker_id or 0,
            item.amount,
        ),
    )


async def _position_exposure_candidates(
    *,
    summary: Any,
    pair: frozenset[str],
    session: AsyncSession,
    asset_loader: AssetLoader,
) -> list[_PositionExposureCandidate]:
    if summary is None:
        return []
    candidates: list[_PositionExposureCandidate] = []
    asset_cache: dict[int, Asset] = {}
    for holding in sorted(
        summary.holdings,
        key=lambda item: (
            item.asset_id,
            item.broker_id is None,
            item.broker_id or 0,
        ),
    ):
        asset = asset_cache.get(holding.asset_id)
        if asset is None:
            try:
                asset = await asset_loader(session, holding.asset_id)
            except Exception as exc:
                raise AiExportSourceFailureError(
                    "asset_store",
                    "load_exposure_asset",
                    context={"asset_id": holding.asset_id},
                ) from exc
            if asset is None:
                raise AiExportSourceFailureError(
                    "asset_store",
                    "load_exposure_asset",
                    context={"asset_id": holding.asset_id},
                )
            asset_cache[holding.asset_id] = asset
        if asset.currency in pair:
            linked_currency = asset.currency
            linkage = AiExportFxExposureLinkage.TRADING_CURRENCY
        elif holding.valuation_effective_currency in pair:
            linked_currency = holding.valuation_effective_currency
            linkage = AiExportFxExposureLinkage.VALUATION_CURRENCY
        else:
            continue
        current_value = Decimal(str(holding.current_value)) if holding.current_value is not None else None
        candidates.append(
            _PositionExposureCandidate(
                linked_currency=linked_currency,
                linkage=linkage,
                current_value=current_value,
                asset_id=holding.asset_id,
                broker_id=holding.broker_id,
            )
        )
    return candidates


def _valued_position_links(
    candidates: Sequence[_PositionExposureCandidate],
    target_currency: str,
) -> list[AiExportFxExposureLink]:
    links: list[AiExportFxExposureLink] = []
    for candidate in candidates:
        if candidate.current_value is None or not candidate.current_value.is_finite():
            raise AiExportSourceFailureError(
                "portfolio_service",
                "exposure_valuation_unavailable",
                context={
                    "asset_id": candidate.asset_id,
                    "broker_id": candidate.broker_id,
                    "linked_currency": candidate.linked_currency,
                },
            )
        links.append(
            AiExportFxExposureLink(
                kind=AiExportFxExposureKind.POSITION,
                linkage=candidate.linkage,
                linked_currency=candidate.linked_currency,
                exposure_amount=Currency(
                    code=target_currency,
                    amount=candidate.current_value,
                ),
                asset_id=candidate.asset_id,
                broker_id=candidate.broker_id,
            )
        )
    return links


def _parse_conversion_result(
    requested_date: date,
    result: tuple[Currency, date, bool] | None,
    expected_currency: str,
) -> _EffectiveRate | None:
    if result is None:
        return None
    converted, actual_date, backward_filled = result
    if converted.code != expected_currency or converted.amount <= 0 or actual_date > requested_date:
        raise AiExportSourceFailureError(
            "fx_service",
            "invalid_conversion_result",
            context={
                "requested_date": requested_date.isoformat(),
                "expected_currency": expected_currency,
            },
        )
    return _EffectiveRate(
        requested_date=requested_date,
        actual_date=actual_date,
        rate=Decimal(str(converted.amount)),
        backward_filled=bool(backward_filled),
    )


def _signal_rates(rates: Sequence[_EffectiveRate]) -> tuple[SignalPricePoint, ...]:
    return tuple(
        SignalPricePoint(
            date=item.requested_date,
            close=item.rate,
            backward_fill_info=(
                BackwardFillInfo(
                    actual_rate_date=item.actual_date,
                    days_back=max(
                        0,
                        (item.requested_date - item.actual_date).days,
                    ),
                )
                if item.backward_filled or item.actual_date != item.requested_date
                else None
            ),
        )
        for item in rates
    )


def _deduplicated_observed_rates(
    rates: Sequence[_EffectiveRate],
) -> tuple[NumericPoint, ...]:
    by_actual_date: dict[date, Decimal] = {}
    for item in rates:
        existing = by_actual_date.get(item.actual_date)
        if existing is None:
            by_actual_date[item.actual_date] = item.rate
        elif existing != item.rate:
            raise AiExportSourceFailureError(
                "fx_service",
                "inconsistent_actual_rate",
                context={"actual_rate_date": item.actual_date.isoformat()},
            )
    return tuple(NumericPoint(date=point_date, value=by_actual_date[point_date]) for point_date in sorted(by_actual_date))


def _selected_points(
    points: Sequence[NumericPoint],
    selected_range: DateRangeModel,
) -> tuple[NumericPoint, ...]:
    return tuple(point for point in points if selected_range.start <= point.date <= selected_range.end)


def _annualized_volatility(points: Sequence[NumericPoint]) -> Decimal | None:
    if len(points) < 3:
        return None
    with localcontext() as context:
        context.prec = 40
        log_returns = [(current.value / previous.value).ln() for previous, current in zip(points, points[1:], strict=False)]
        mean = sum(log_returns, start=Decimal("0")) / Decimal(len(log_returns))
        variance = sum(
            ((value - mean) ** 2 for value in log_returns),
            start=Decimal("0"),
        ) / Decimal(len(log_returns) - 1)
        return round_percentage(variance.sqrt() * Decimal("252").sqrt() * Decimal("100"))


def _max_drawdown(points: Sequence[NumericPoint]) -> Decimal | None:
    if len(points) < 2:
        return None
    peak = points[0].value
    maximum_drawdown = Decimal("0")
    for point in points:
        peak = max(peak, point.value)
        drawdown = point.value / peak * Decimal("100") - Decimal("100")
        maximum_drawdown = min(maximum_drawdown, drawdown)
    return round_percentage(maximum_drawdown)


def _fx_extrema(points: Sequence[NumericPoint]) -> AiExportFxExtrema | None:
    if not points:
        return None
    low = min(points, key=lambda point: (point.value, point.date))
    high_value = max(point.value for point in points)
    high = next(point for point in points if point.value == high_value)
    return AiExportFxExtrema(
        low_rate=round_fx_rate(low.value),
        low_date=low.date,
        high_rate=round_fx_rate(high.value),
        high_date=high.date,
    )


def _fx_volatility(
    points: Sequence[NumericPoint],
) -> AiExportFxVolatility | None:
    if len(points) < 2:
        return None
    period_return = round_percentage(relative_distance_pct(points[-1].value, points[0].value)) if len(points) >= 2 else None
    return AiExportFxVolatility(
        period_return_pct=period_return,
        annualized_volatility_pct=_annualized_volatility(points),
        max_drawdown_pct=_max_drawdown(points),
    )


def _metric_semantics(
    *,
    ranges: Any,
    facts: AiExportFxFacts,
) -> list[AiExportMetricSemantic]:
    semantics: list[AiExportMetricSemantic] = []
    if facts.normalized_return is not None:
        semantics.append(
            AiExportMetricSemantic(
                metric_code="fx.normalized_return",
                unit="percentage_points",
                denominator="first_observed_rate_in_window",
                method="observed_only_simple_return",
                period=ranges.technical_window,
                cumulative=True,
            )
        )
    if facts.volatility is not None:
        if facts.volatility.period_return_pct is not None:
            semantics.append(
                AiExportMetricSemantic(
                    metric_code="fx.period_return_pct",
                    unit="percentage_points",
                    denominator="first_observed_rate",
                    method="simple_return",
                    period=ranges.selected_range,
                    cumulative=True,
                )
            )
        if facts.volatility.annualized_volatility_pct is not None:
            semantics.append(
                AiExportMetricSemantic(
                    metric_code="fx.annualized_volatility_pct",
                    unit="percentage_points",
                    method="daily_log_return_sample_stddev",
                    period=ranges.selected_range,
                    annualized=True,
                    cumulative=False,
                )
            )
        if facts.volatility.max_drawdown_pct is not None:
            semantics.append(
                AiExportMetricSemantic(
                    metric_code="fx.max_drawdown_pct",
                    unit="percentage_points",
                    denominator="running_peak_rate",
                    method="peak_to_trough",
                    period=ranges.selected_range,
                    cumulative=False,
                )
            )
    if facts.exposure_links:
        semantics.append(
            AiExportMetricSemantic(
                metric_code="fx.linked_exposure",
                unit="target_currency",
                method="cash_or_position_currency_linkage",
                period=DateRangeModel(
                    start=ranges.snapshot_as_of,
                    end=ranges.snapshot_as_of,
                ),
                universe="authenticated_broker_scope",
                cumulative=False,
            )
        )
    return semantics


class AiExportFxAssembler:
    """Assemble all resolved FX task/detail profiles."""

    def __init__(
        self,
        *,
        convert_bulk_fn: ConvertBulk = convert_bulk,
        portfolio_service_factory: PortfolioServiceFactory = PortfolioService,
        asset_loader: AssetLoader = _default_asset_loader,
        technical_preparer: TechnicalPreparer = prepare_technical_target,
        technical_executor: TechnicalExecutor = execute_technical_target,
        clock: Clock = utc_now,
    ) -> None:
        self._convert_bulk = convert_bulk_fn
        self._portfolio_service_factory = portfolio_service_factory
        self._asset_loader = asset_loader
        self._technical_preparer = technical_preparer
        self._technical_executor = technical_executor
        self._clock = clock

    async def assemble(
        self,
        prepared: AiExportPreparedRequest,
        session: AsyncSession,
    ) -> AiExportFxSnapshotResponse:
        request = prepared.request
        if not isinstance(request, AiExportFxSnapshotRequest):
            raise TypeError("FX assembler requires AiExportFxSnapshotRequest")

        initial_ranges = resolve_ranges(prepared)
        target = AiExportFxPairTargetReference(
            kind="fx_pair",
            base_currency=request.base_currency,
            quote_currency=request.quote_currency,
        )
        prepared_technical = self._technical_preparer(
            prepared.resolved_profile,
            target,
            initial_ranges.technical_window,
            target_currency=request.quote_currency,
        )
        ranges = resolve_ranges(
            prepared,
            calculation_range=(prepared_technical.calculation_range if prepared_technical is not None else initial_ranges.technical_window),
            calculation_warmup_start=(prepared_technical.calculation_warmup_start if prepared_technical is not None else initial_ranges.technical_window.start),
        )

        portfolio_report = None
        cash_candidates: list[_CashExposureCandidate] = []
        position_candidates: list[_PositionExposureCandidate] = []
        position_links: list[AiExportFxExposureLink] = []
        pair = frozenset({request.base_currency, request.quote_currency})
        if request.task == AiExportFxTask.FX_EXPOSURE_IMPACT:
            if not prepared.broker_scope:
                raise AiExportTaskNotApplicableError(
                    prepared.resolved_profile.applicability_code,
                    "no_linked_exposure",
                    context={"broker_ids": []},
                )
            query = PortfolioReportQuery(
                broker_ids=list(prepared.broker_scope),
                date_range=OpenDateRangeModel(
                    start=ranges.selected_range.start,
                    end=ranges.selected_range.end,
                ),
                target_currency=request.target_currency,
                include_summary=True,
                include_history=False,
                include_allocation_history=False,
                include_breakdown=True,
                include_positions_contribution=False,
            )
            try:
                portfolio_report = await self._portfolio_service_factory(session).get_report(prepared.user_id, query)
            except Exception as exc:
                raise AiExportSourceFailureError(
                    "portfolio_service",
                    "get_report",
                    context={
                        "base_currency": request.base_currency,
                        "quote_currency": request.quote_currency,
                    },
                ) from exc
            if portfolio_report.summary is None:
                raise AiExportSourceFailureError(
                    "portfolio_service",
                    "missing_summary",
                )
            cash_candidates = _cash_candidates(
                portfolio_report.summary,
                pair,
            )
            position_candidates = await _position_exposure_candidates(
                summary=portfolio_report.summary,
                pair=pair,
                session=session,
                asset_loader=self._asset_loader,
            )
            if not cash_candidates and not position_candidates:
                raise AiExportTaskNotApplicableError(
                    prepared.resolved_profile.applicability_code,
                    "no_linked_exposure",
                    context={
                        "broker_ids": list(prepared.broker_scope),
                        "base_currency": request.base_currency,
                        "quote_currency": request.quote_currency,
                    },
                )
            position_links = _valued_position_links(
                position_candidates,
                request.target_currency,
            )

        load_range = DateRangeModel(
            start=min(ranges.selected_range.start, ranges.calculation_range.start),
            end=max(ranges.selected_range.end, ranges.calculation_range.end),
        )
        requested_dates = _inclusive_dates(load_range)
        conversions: list[tuple[Currency, str, date]] = [
            (
                Currency(
                    code=request.base_currency,
                    amount=Decimal("1"),
                ),
                request.quote_currency,
                requested_date,
            )
            for requested_date in requested_dates
        ]
        conversions.extend(
            (
                Currency(
                    code=candidate.linked_currency,
                    amount=candidate.amount,
                ),
                request.target_currency,
                ranges.snapshot_as_of,
            )
            for candidate in cash_candidates
        )
        try:
            conversion_output = await self._convert_bulk(
                session,
                conversions,
                raise_on_error=False,
            )
        except Exception as exc:
            raise AiExportSourceFailureError(
                "fx_service",
                "convert_bulk",
                retryable=False,
                context={
                    "base_currency": request.base_currency,
                    "quote_currency": request.quote_currency,
                },
            ) from exc
        if isinstance(conversion_output, tuple) and len(conversion_output) == 2:
            conversion_results, _conversion_errors = conversion_output
        else:
            conversion_results = conversion_output
        if len(conversion_results) != len(conversions):
            raise AiExportSourceFailureError(
                "fx_service",
                "invalid_bulk_result_count",
                context={
                    "expected_results": len(conversions),
                    "actual_results": len(conversion_results),
                },
            )
        daily_results = conversion_results[: len(requested_dates)]
        effective_rates = tuple(
            parsed
            for requested_date, result in zip(
                requested_dates,
                daily_results,
                strict=True,
            )
            if (
                parsed := _parse_conversion_result(
                    requested_date,
                    result,
                    request.quote_currency,
                )
            )
            is not None
        )
        current = (
            max(
                (item for item in effective_rates if item.actual_date <= ranges.snapshot_as_of),
                key=lambda item: (item.actual_date, item.requested_date),
            )
            if effective_rates
            else None
        )
        if current is None:
            raise AiExportSourceFailureError(
                "fx_service",
                "rate_not_found",
                context={
                    "base_currency": request.base_currency,
                    "quote_currency": request.quote_currency,
                    "snapshot_as_of": ranges.snapshot_as_of.isoformat(),
                },
            )

        signal_rates = _signal_rates(effective_rates)
        technical_signal_rates = tuple(point for point in signal_rates if ranges.calculation_range.start <= point.date <= ranges.calculation_range.end)
        if prepared_technical is not None:
            try:
                technical_result = await self._technical_executor(
                    prepared_technical,
                    technical_signal_rates,
                    (),
                    events_loaded=True,
                )
            except Exception as exc:
                raise AiExportSourceFailureError(
                    "technical_runner",
                    "execute",
                    context={
                        "base_currency": request.base_currency,
                        "quote_currency": request.quote_currency,
                    },
                ) from exc
            technical = combine_technical_results([technical_result])
        else:
            technical = combine_technical_results([])

        observed = _deduplicated_observed_rates(effective_rates)
        selected_observed = _selected_points(
            observed,
            ranges.selected_range,
        )
        technical_observed = _selected_points(
            observed,
            ranges.technical_window,
        )
        sampled = sample_and_round_numeric_points(
            technical_observed,
            prepared.resolved_profile.detail_overlay.sampling,
            round_fx_rate,
        )
        normalized_return = (
            build_normalized_return(
                [
                    ObservedSourcePoint(
                        date=point.date,
                        source_value=point.value,
                    )
                    for point in observed
                ],
                ranges.technical_window,
                prepared.resolved_profile.detail_overlay.sampling,
                source_rounding=round_fx_rate,
            )
            if profile_allows(
                prepared.resolved_profile,
                "facts.normalized_return",
            )
            else None
        )

        cash_links: list[AiExportFxExposureLink] = []
        cash_results = conversion_results[len(requested_dates) :]
        for candidate, result in zip(
            cash_candidates,
            cash_results,
            strict=True,
        ):
            if result is None:
                raise AiExportSourceFailureError(
                    "fx_service",
                    "exposure_conversion_unavailable",
                    context={
                        "linked_currency": candidate.linked_currency,
                        "broker_id": candidate.broker_id,
                        "target_currency": request.target_currency,
                    },
                )
            try:
                converted, _actual_date, _backward_filled = result
            except (TypeError, ValueError) as exc:
                raise AiExportSourceFailureError(
                    "fx_service",
                    "exposure_conversion_unavailable",
                    context={
                        "linked_currency": candidate.linked_currency,
                        "broker_id": candidate.broker_id,
                        "target_currency": request.target_currency,
                    },
                ) from exc
            if converted.code != request.target_currency:
                raise AiExportSourceFailureError(
                    "fx_service",
                    "invalid_exposure_conversion_currency",
                    context={
                        "expected_currency": request.target_currency,
                        "actual_currency": converted.code,
                    },
                )
            cash_links.append(
                AiExportFxExposureLink(
                    kind=AiExportFxExposureKind.CASH,
                    linkage=AiExportFxExposureLinkage.CASH_CURRENCY,
                    linked_currency=candidate.linked_currency,
                    exposure_amount=Currency(
                        code=request.target_currency,
                        amount=converted.amount,
                    ),
                    broker_id=candidate.broker_id,
                )
            )
        exposure_links = sorted(
            [*cash_links, *position_links],
            key=lambda link: (
                link.kind.value,
                link.linked_currency,
                link.broker_id is None,
                link.broker_id or 0,
                link.asset_id is None,
                link.asset_id or 0,
                link.exposure_amount.amount,
            ),
        )

        facts = AiExportFxFacts(
            identity=AiExportFxIdentity(
                base_currency=request.base_currency,
                quote_currency=request.quote_currency,
            ),
            current_rate=AiExportFxRatePoint(
                date=current.actual_date,
                rate=round_fx_rate(current.rate),
            ),
            sampled_rates=[
                AiExportFxRatePoint(
                    date=point.date,
                    rate=point.value,
                )
                for point in sampled
            ],
            extrema=(
                _fx_extrema(selected_observed)
                if profile_allows(
                    prepared.resolved_profile,
                    "facts.extrema",
                )
                else None
            ),
            volatility=(
                _fx_volatility(selected_observed)
                if profile_allows(
                    prepared.resolved_profile,
                    "facts.volatility",
                )
                else None
            ),
            normalized_return=normalized_return,
            exposure_links=exposure_links,
        )
        response = AiExportFxSnapshotResponse(
            domain=AiExportDomain.FX,
            task=request.task,
            detail_level=request.detail_level,
            meta=build_snapshot_meta(
                prepared,
                ranges,
                clock=self._clock,
            ),
            methodology=build_methodology(),
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
                trading_currency=request.base_currency,
                valuation_currency=request.target_currency,
            ),
            domain_notes=[],
            export_stats=neutral_export_stats(),
        )
        return finalize_response(response)


async def assemble_fx_snapshot(
    prepared: AiExportPreparedRequest,
    session: AsyncSession,
    *,
    assembler: AiExportFxAssembler | None = None,
) -> AiExportFxSnapshotResponse:
    return await (assembler or AiExportFxAssembler()).assemble(
        prepared,
        session,
    )


__all__ = [
    "AiExportFxAssembler",
    "assemble_fx_snapshot",
]
