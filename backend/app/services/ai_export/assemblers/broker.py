"""Broker-domain AI Export snapshot assembler."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Transaction, TransactionType
from backend.app.schemas.ai_export import (
    AiExportAssetTargetReference,
    AiExportBrokerConcentration,
    AiExportBrokerFacts,
    AiExportBrokerSnapshotRequest,
    AiExportBrokerSnapshotResponse,
    AiExportBrokerSummary,
    AiExportBrokerTask,
    AiExportConcentrationEntry,
    AiExportDetailLevel,
    AiExportDomain,
    AiExportLatestTransaction,
    AiExportMetricSemantic,
    AiExportPosition,
    AiExportSelectionMetadata,
    AiExportTechnicalSnapshot,
)
from backend.app.schemas.common import Currency, DateRangeModel, OpenDateRangeModel
from backend.app.schemas.portfolio import LotAnalysisType, PortfolioReportQuery
from backend.app.schemas.prices import FAPriceQueryItem
from backend.app.services.ai_export.assemblers.asset import _fifo_summary
from backend.app.services.ai_export.assemblers.fifo import (
    COMPACT_TOTAL_LIMIT,
    FIFO_LOT_SELECTION_RULE,
    TransactionAssetIdsLoader,
    asset_residual_cost_basis,
    build_fifo_lot_selection_metadata,
    closed_lot_cutoff_date,
    collect_fifo_candidates,
    default_transaction_asset_ids_loader,
    has_nonzero_open_lot,
    select_compact_fifo_lots,
)
from backend.app.services.ai_export.assemblers.portfolio import (
    AssetMetadataLoader,
    BrokerMetadataLoader,
    PortfolioServiceFactory,
    PriceBulkLoader,
    TechnicalExecutor,
    TechnicalPreparer,
    _build_contributions,
    _build_other_period_effects,
    _build_positions,
    _build_raw_holding_maps,
    _build_summary,
    _build_unallocated_contributions,
    _compact_events,
    _decimal,
    _default_asset_metadata_loader,
    _default_broker_metadata_loader,
    _domain_notes,
    _entity_map,
    _enum_value,
    _filter_entity_scoped_details,
    _filter_technical_targets,
    _money,
    _optional_decimal,
    _portfolio_is_empty,
    _price_results,
    _RawHoldingMaps,
    _selection_metadata,
    _signal_events,
    _signal_prices,
    _technical_ranges,
)
from backend.app.services.ai_export.assemblers.shared import (
    AiExportAssemblerError,
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
from backend.app.services.ai_export.sampling import round_decimal_places, round_percentage
from backend.app.services.ai_export.service import AiExportPreparedRequest
from backend.app.services.ai_export.technical import (
    PreparedTechnicalTarget,
    TechnicalTargetResult,
    combine_technical_results,
    execute_technical_target,
    prepare_technical_target,
)
from backend.app.services.asset_source import AssetSourceManager
from backend.app.services.lots_analysis_service import LotsAnalysisService
from backend.app.services.portfolio_service import PortfolioService

LotsServiceFactory = Callable[[AsyncSession], Any]
LatestTransactionLoader = Callable[[AsyncSession, int, date], Awaitable[Any | None]]


async def _default_latest_transaction_loader(
    session: AsyncSession,
    broker_id: int,
    snapshot_as_of: date,
) -> Transaction | None:
    result = await session.execute(
        select(Transaction)
        .where(
            Transaction.broker_id == broker_id,
            Transaction.date <= snapshot_as_of,
        )
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .limit(1)
    )
    return result.scalars().first()


def _validate_single_broker_scope(
    prepared: AiExportPreparedRequest,
    request: AiExportBrokerSnapshotRequest,
) -> int:
    expected = (request.broker_id,)
    if prepared.broker_scope != expected:
        raise ValueError(f"broker assembler requires exact broker scope {expected}")
    return request.broker_id


def _validate_report_scope(
    *,
    broker_id: int,
    summary: Any,
    holdings: Sequence[Any],
    contributions: Sequence[Any],
    unallocated: Sequence[Any],
    other_effects: Sequence[Any],
) -> None:
    scoped_rows = (*holdings, *contributions, *unallocated)
    invalid_ids = sorted({int(row_broker_id) for row in scoped_rows if (row_broker_id := getattr(row, "broker_id", None)) is not None and int(row_broker_id) != broker_id})
    invalid_ids.extend(sorted({int(row_broker_id) for row in other_effects if (row_broker_id := getattr(row, "broker_id", None)) is not None and int(row_broker_id) != broker_id}))
    breakdown = getattr(summary, "by_broker", None)
    if breakdown is None:
        raise AiExportSourceFailureError(
            "portfolio_service",
            "missing_broker_breakdown",
            context={"broker_id": broker_id},
        )
    invalid_ids.extend(sorted({int(row_broker_id) for row in breakdown if (row_broker_id := getattr(row, "broker_id", None)) is not None and int(row_broker_id) != broker_id}))
    if invalid_ids:
        raise AiExportSourceFailureError(
            "portfolio_service",
            "broker_scope_mismatch",
            context={
                "broker_id": broker_id,
                "unexpected_broker_ids": sorted(set(invalid_ids)),
            },
        )


def _build_broker_summary(
    summary: Any,
    *,
    broker: Any,
    broker_id: int,
    target_currency: str,
) -> AiExportBrokerSummary:
    portfolio_summary = _build_summary(
        summary,
        target_currency=target_currency,
        empty_portfolio=_portfolio_is_empty(summary),
    )
    return AiExportBrokerSummary(
        broker_id=broker_id,
        name=str(getattr(broker, "name", None) or f"Broker {broker_id}"),
        base_currency=target_currency,
        nav=portfolio_summary.nav,
        market_value=portfolio_summary.market_value,
        cash=portfolio_summary.cash,
        book_value=portfolio_summary.book_value,
        net_contributed_capital=portfolio_summary.net_contributed_capital,
        start_nav=portfolio_summary.start_nav,
        net_deposits=portfolio_summary.net_deposits,
        lifetime_pnl_amount=portfolio_summary.lifetime_pnl_amount,
        period_pnl_amount=portfolio_summary.period_pnl_amount,
        realized_pnl_amount=portfolio_summary.realized_pnl_amount,
        unrealized_pnl_amount=portfolio_summary.unrealized_pnl_amount,
        income_amount=portfolio_summary.income_amount,
        fees_taxes_amount=portfolio_summary.fees_taxes_amount,
        twrr_cumulative_pct=portfolio_summary.twrr_cumulative_pct,
        mwrr_annualized_pct=portfolio_summary.mwrr_annualized_pct,
        roi_cumulative_pct=portfolio_summary.roi_cumulative_pct,
    )


def _position_by_asset(
    positions: Sequence[AiExportPosition],
) -> dict[int, AiExportPosition]:
    by_asset: dict[int, AiExportPosition] = {}
    for position in positions:
        if position.asset_id in by_asset:
            raise AiExportSourceFailureError(
                "portfolio_service",
                "duplicate_broker_asset_position",
                context={"asset_id": position.asset_id},
            )
        by_asset[position.asset_id] = position
    return by_asset


def _build_concentration(
    positions: Sequence[AiExportPosition],
    *,
    selected_asset_ids: set[int] | None,
) -> AiExportBrokerConcentration:
    positions_by_asset = _position_by_asset(positions)
    gross_market_values = {asset_id: abs(position.market_value.amount) for asset_id, position in positions_by_asset.items() if position.market_value is not None}
    gross_market_value = sum(gross_market_values.values(), start=Decimal("0"))
    ranked_asset_ids = sorted(
        gross_market_values,
        key=lambda asset_id: (
            -gross_market_values[asset_id],
            asset_id,
        ),
    )
    shares = {asset_id: (Decimal("0") if gross_market_value.is_zero() else gross_market_values[asset_id] / gross_market_value) for asset_id in ranked_asset_ids}
    weighted_values = [shares[asset_id] * Decimal("100") for asset_id in ranked_asset_ids]
    entry_asset_ids = ranked_asset_ids if selected_asset_ids is None else [asset_id for asset_id in ranked_asset_ids if asset_id in selected_asset_ids]
    entries = [
        AiExportConcentrationEntry(
            asset_id=asset_id,
            name=positions_by_asset[asset_id].name,
            market_value=positions_by_asset[asset_id].market_value,
            weight_pct=round_percentage(shares[asset_id] * Decimal("100")),
        )
        for asset_id in entry_asset_ids
    ]
    return AiExportBrokerConcentration(
        position_count=len(positions),
        largest_position_weight_pct=(round_percentage(weighted_values[0]) if weighted_values else None),
        top_five_weight_pct=(round_percentage(sum(weighted_values[:5], start=Decimal("0"))) if weighted_values else None),
        herfindahl_index=(
            round_decimal_places(
                sum((shares[asset_id] * shares[asset_id] for asset_id in ranked_asset_ids), start=Decimal("0")),
                6,
            )
            if weighted_values
            else None
        ),
        entries=entries,
    )


def _raw_position_cost(
    asset_id: int,
    broker_id: int,
    contribution_sources: Mapping[tuple[int, int], Any],
) -> Decimal:
    source = contribution_sources.get((asset_id, broker_id))
    value = _optional_decimal(getattr(source, "period_fees_taxes", None)) if source is not None else None
    return abs(value) if value is not None else Decimal("0")


def _select_compact_assets(
    task: AiExportBrokerTask,
    *,
    profile: Any,
    positions: Sequence[AiExportPosition],
    contribution_sources: Mapping[tuple[int, int], Any],
    fifo_lots_by_asset: Mapping[int, Sequence[Any]] | None,
    broker_id: int,
    raw_holdings: _RawHoldingMaps,
) -> tuple[set[int], AiExportSelectionMetadata]:
    spec = profile.compact_selection
    positions_by_asset = _position_by_asset(positions)
    position_asset_ids = sorted(positions_by_asset)
    nav_weights = raw_holdings.asset_nav_weights

    def raw_market_value(asset_id: int) -> Decimal:
        raw = raw_holdings.by_position.get((asset_id, broker_id))
        return abs(raw.market_value) if raw is not None and raw.market_value is not None else Decimal("0")

    if task in {
        AiExportBrokerTask.BROKER_REVIEW,
        AiExportBrokerTask.BROKER_CONCENTRATION_CONTEXT,
    }:
        asset_ids = position_asset_ids
        ranked = sorted(
            asset_ids,
            key=lambda asset_id: (
                -nav_weights.get(asset_id, Decimal("0")),
                -raw_market_value(asset_id),
                asset_id,
            ),
        )
    elif task == AiExportBrokerTask.BROKER_COST_EFFICIENCY:
        contribution_asset_ids = {asset_id for asset_id, contribution_broker_id in contribution_sources if contribution_broker_id == broker_id}
        asset_ids = sorted(set(position_asset_ids) | contribution_asset_ids)
        ranked = sorted(
            asset_ids,
            key=lambda asset_id: (
                -_raw_position_cost(
                    asset_id,
                    broker_id,
                    contribution_sources,
                ),
                -raw_market_value(asset_id),
                -nav_weights.get(asset_id, Decimal("0")),
                asset_id,
            ),
        )
    elif task == AiExportBrokerTask.BROKER_FIFO_LOT_REVIEW:
        asset_ids = position_asset_ids
        if fifo_lots_by_asset is None:
            raise AiExportSourceFailureError(
                "lots_analysis_service",
                "missing_compact_fifo_selection_source",
            )
        ranked = sorted(
            asset_ids,
            key=lambda asset_id: (
                -asset_residual_cost_basis(fifo_lots_by_asset.get(asset_id, ())),
                -nav_weights.get(asset_id, Decimal("0")),
                asset_id,
            ),
        )
    else:
        raise ValueError(f"unsupported Broker task: {task}")

    selected = set(ranked[: spec.entity_limit])
    metadata = _selection_metadata(
        rule=spec.rule,
        limit=spec.entity_limit,
        all_keys=asset_ids,
        selected_keys=selected,
        weights=nav_weights,
    )
    return selected, metadata


def _transaction_currency(
    transaction: Any,
    value: object | None,
    *,
    absolute: bool,
) -> Currency | None:
    if isinstance(value, Currency):
        amount = abs(value.amount) if absolute else value.amount
        return _money(value.code, amount)
    amount = _optional_decimal(value)
    currency = getattr(transaction, "currency", None)
    if amount is None or amount.is_zero() or currency is None:
        return None
    return _money(
        str(currency).upper(),
        abs(amount) if absolute else amount,
    )


def _build_latest_transaction(
    transaction: Any | None,
) -> AiExportLatestTransaction | None:
    if transaction is None:
        return None
    transaction_type = _enum_value(getattr(transaction, "type", None))
    transaction_date = getattr(transaction, "date", None)
    if transaction_type is None or transaction_date is None:
        raise AiExportSourceFailureError(
            "transaction_store",
            "invalid_latest_transaction",
        )
    quantity = _optional_decimal(getattr(transaction, "quantity", None))
    if quantity is not None and quantity.is_zero():
        quantity = None
    explicit_fees = getattr(transaction, "fees_taxes_amount", None)
    is_cost = transaction_type in {
        TransactionType.FEE.value,
        TransactionType.TAX.value,
    }
    amount = getattr(transaction, "amount", None)
    return AiExportLatestTransaction(
        transaction_date=transaction_date,
        transaction_type=transaction_type,
        asset_id=getattr(transaction, "asset_id", None),
        quantity=quantity,
        gross_amount=(
            None
            if is_cost
            else _transaction_currency(
                transaction,
                amount,
                absolute=True,
            )
        ),
        fees_taxes_amount=(
            _transaction_currency(
                transaction,
                explicit_fees if explicit_fees is not None else amount,
                absolute=True,
            )
            if explicit_fees is not None or is_cost
            else None
        ),
    )


def _metric_semantics(
    *,
    ranges: AiExportResolvedRanges,
    facts: AiExportBrokerFacts,
) -> list[AiExportMetricSemantic]:
    snapshot_period = DateRangeModel(
        start=ranges.snapshot_as_of,
        end=ranges.snapshot_as_of,
    )
    selected = ranges.selected_range
    semantics = [
        AiExportMetricSemantic(
            metric_code="broker.nav",
            unit="target_currency",
            method="portfolio_engine_snapshot",
            period=snapshot_period,
            universe="single_authorized_broker",
        ),
        AiExportMetricSemantic(
            metric_code="broker.market_value",
            unit="target_currency",
            method="portfolio_engine_snapshot",
            period=snapshot_period,
            universe="valued_open_positions",
        ),
        AiExportMetricSemantic(
            metric_code="broker.cash",
            unit="target_currency",
            method="portfolio_engine_snapshot",
            period=snapshot_period,
            universe="single_authorized_broker",
        ),
    ]
    optional_summary = (
        (
            "broker.book_value",
            facts.summary.book_value,
            "target_currency",
            "portfolio_engine_snapshot",
            snapshot_period,
            False,
            False,
        ),
        (
            "broker.net_contributed_capital",
            facts.summary.net_contributed_capital,
            "target_currency",
            "portfolio_service_total_invested_lifetime",
            None,
            False,
            True,
        ),
        (
            "broker.start_nav",
            facts.summary.start_nav,
            "target_currency",
            "selected_period_start_nav",
            selected,
            False,
            False,
        ),
        (
            "broker.net_deposits",
            facts.summary.net_deposits,
            "target_currency",
            "portfolio_service_period_net_flows",
            selected,
            False,
            True,
        ),
        (
            "broker.lifetime_pnl_amount",
            facts.summary.lifetime_pnl_amount,
            "target_currency",
            "portfolio_service_lifetime_gain_loss",
            snapshot_period,
            False,
            True,
        ),
        (
            "broker.period_pnl_amount",
            facts.summary.period_pnl_amount,
            "target_currency",
            "nav_change_net_external_flows",
            selected,
            False,
            True,
        ),
        (
            "broker.realized_pnl_amount",
            facts.summary.realized_pnl_amount,
            "target_currency",
            "weighted_average_cost_realized",
            selected,
            False,
            True,
        ),
        (
            "broker.unrealized_pnl_amount",
            facts.summary.unrealized_pnl_amount,
            "target_currency",
            "market_value_minus_book_value",
            snapshot_period,
            False,
            False,
        ),
        (
            "broker.income_amount",
            facts.summary.income_amount,
            "target_currency",
            "period_income",
            selected,
            False,
            True,
        ),
        (
            "broker.fees_taxes_amount",
            facts.summary.fees_taxes_amount,
            "target_currency",
            "period_fees_taxes_positive_cost",
            selected,
            False,
            True,
        ),
        (
            "broker.twrr_cumulative_pct",
            facts.summary.twrr_cumulative_pct,
            "percentage_points",
            "time_weighted_return",
            selected,
            False,
            True,
        ),
        (
            "broker.mwrr_annualized_pct",
            facts.summary.mwrr_annualized_pct,
            "percentage_points",
            "money_weighted_return_xirr",
            selected,
            True,
            False,
        ),
        (
            "broker.roi_cumulative_pct",
            facts.summary.roi_cumulative_pct,
            "percentage_points",
            "simple_roi",
            selected,
            False,
            True,
        ),
    )
    for (
        code,
        value,
        unit,
        method,
        period,
        annualized,
        cumulative,
    ) in optional_summary:
        if value is not None:
            semantics.append(
                AiExportMetricSemantic(
                    metric_code=code,
                    unit=unit,
                    method=method,
                    period=period,
                    universe="single_authorized_broker",
                    annualized=annualized,
                    cumulative=cumulative,
                )
            )
    if facts.positions:
        semantics.append(
            AiExportMetricSemantic(
                metric_code="broker.position_weight_pct",
                unit="percentage_points",
                denominator="broker_nav",
                method="signed_authoritative_nav_weight",
                period=snapshot_period,
                universe="open_positions",
                cumulative=False,
            )
        )
    if facts.contributions:
        semantics.append(
            AiExportMetricSemantic(
                metric_code="broker.contribution_pct",
                unit="percentage_points",
                denominator="absolute_position_start_value",
                method="portfolio_service_period_contribution",
                period=selected,
                universe="complete_period_contributions",
                cumulative=True,
            )
        )
    if facts.unallocated_contributions:
        semantics.append(
            AiExportMetricSemantic(
                metric_code="broker.unallocated_contribution_amount",
                unit="target_currency",
                method="portfolio_service_unallocated_period_contribution",
                period=selected,
                universe="broker_level_unallocated_contributions",
                cumulative=True,
            )
        )
    if facts.other_period_effects:
        semantics.append(
            AiExportMetricSemantic(
                metric_code="broker.other_period_effect_pnl_amount",
                unit="target_currency",
                method="portfolio_service_other_period_effect",
                period=selected,
                universe="non_position_period_effects",
                cumulative=True,
            )
        )
    if facts.concentration is not None:
        concentration_metrics = (
            (
                "broker.largest_position_weight_pct",
                facts.concentration.largest_position_weight_pct,
                "percentage_points",
                "largest_gross_absolute_market_value_weight",
                "gross_absolute_open_position_market_value",
            ),
            (
                "broker.top_five_weight_pct",
                facts.concentration.top_five_weight_pct,
                "percentage_points",
                "top_five_gross_absolute_market_value_weight",
                "gross_absolute_open_position_market_value",
            ),
            (
                "broker.herfindahl_index",
                facts.concentration.herfindahl_index,
                "ratio",
                "sum_squared_gross_absolute_market_value_weight_ratio",
                "gross_absolute_open_position_market_value",
            ),
        )
        for code, value, unit, method, denominator in concentration_metrics:
            if value is not None:
                semantics.append(
                    AiExportMetricSemantic(
                        metric_code=code,
                        unit=unit,
                        denominator=denominator,
                        method=method,
                        period=snapshot_period,
                        universe="valued_open_positions",
                        cumulative=False,
                    )
                )
    if facts.fifo_summary is not None:
        semantics.append(
            AiExportMetricSemantic(
                metric_code="broker.fifo_residual_cost_basis",
                unit="target_currency",
                method="runtime_fifo_open_lot_cost_basis",
                period=snapshot_period,
                universe="all_held_assets",
                cumulative=False,
            )
        )
    if facts.fifo_lots:
        semantics.append(
            AiExportMetricSemantic(
                metric_code="broker.fifo_lot_residual_cost_basis",
                unit="target_currency",
                method="runtime_fifo_per_lot_cost_basis",
                period=snapshot_period,
                universe="eligible_open_partial_and_recently_closed_lots",
                cumulative=False,
            )
        )
    if facts.fifo_lot_selection is not None:
        semantics.append(
            AiExportMetricSemantic(
                metric_code="broker.fifo_lot_selection_nav_weight_pct",
                unit="percentage_points",
                denominator="gross_absolute_candidate_nav_exposure",
                method=f"{facts.fifo_lot_selection.rule}_with_gross_nav_coverage",
                period=snapshot_period,
                universe="compact_fifo_lot_selection_candidates",
                cumulative=False,
            )
        )
    if facts.selection is not None:
        semantics.append(
            AiExportMetricSemantic(
                metric_code="broker.selection_nav_weight_pct",
                unit="percentage_points",
                denominator="gross_absolute_candidate_nav_exposure",
                method=f"{facts.selection.rule}_with_gross_nav_coverage",
                period=snapshot_period,
                universe="compact_selection_candidates",
                cumulative=False,
            )
        )
    return semantics


class AiExportBrokerAssembler:
    """Assemble all resolved Broker task/detail profiles."""

    def __init__(
        self,
        *,
        portfolio_service_factory: PortfolioServiceFactory = PortfolioService,
        portfolio_service: Any | None = None,
        lots_service_factory: LotsServiceFactory = LotsAnalysisService,
        lots_service: Any | None = None,
        price_bulk_loader: PriceBulkLoader = AssetSourceManager.get_prices_bulk,
        asset_metadata_loader: AssetMetadataLoader = _default_asset_metadata_loader,
        broker_metadata_loader: BrokerMetadataLoader = _default_broker_metadata_loader,
        latest_transaction_loader: LatestTransactionLoader = (_default_latest_transaction_loader),
        transaction_asset_ids_loader: TransactionAssetIdsLoader = default_transaction_asset_ids_loader,
        technical_preparer: TechnicalPreparer = prepare_technical_target,
        technical_executor: TechnicalExecutor = execute_technical_target,
        clock: Clock = utc_now,
    ) -> None:
        self._portfolio_service_factory = portfolio_service_factory
        self._portfolio_service = portfolio_service
        self._lots_service_factory = lots_service_factory
        self._lots_service = lots_service
        self._price_bulk_loader = price_bulk_loader
        self._asset_metadata_loader = asset_metadata_loader
        self._broker_metadata_loader = broker_metadata_loader
        self._latest_transaction_loader = latest_transaction_loader
        self._transaction_asset_ids_loader = transaction_asset_ids_loader
        self._technical_preparer = technical_preparer
        self._technical_executor = technical_executor
        self._clock = clock

    async def _load_fifo_lots(
        self,
        *,
        prepared: AiExportPreparedRequest,
        session: AsyncSession,
        asset_ids: Sequence[int],
        broker_id: int,
        ranges: AiExportResolvedRanges,
        required: bool,
    ) -> dict[int, list[Any]] | None:
        service = self._lots_service or self._lots_service_factory(session)
        lots_by_asset: dict[int, list[Any]] = {}
        for asset_id in sorted(set(asset_ids)):
            try:
                response = await service.get_lots_analysis(
                    user_id=prepared.user_id,
                    asset_id=asset_id,
                    broker_ids=[broker_id],
                    date_from=ranges.selected_range.start,
                    date_to=ranges.snapshot_as_of,
                    target_currency=prepared.request.target_currency,
                    selected_lot_ids=None,
                    requested_analyses=[LotAnalysisType.LOT_SUMMARY],
                )
            except Exception as exc:
                if not required:
                    return None
                raise AiExportSourceFailureError(
                    "lots_analysis_service",
                    "get_lots_analysis",
                    context={
                        "asset_id": asset_id,
                        "broker_id": broker_id,
                    },
                ) from exc
            status = (_enum_value(getattr(response, "calculation_status", None)) or "").upper()
            lots = getattr(response, "lots", None)
            if status not in {"COMPLETE", "DEGRADED"} or lots is None:
                if not required:
                    return None
                raise AiExportSourceFailureError(
                    "lots_analysis_service",
                    "unreliable_lot_summary",
                    context={
                        "asset_id": asset_id,
                        "broker_id": broker_id,
                        "calculation_status": status or None,
                    },
                )
            lots_by_asset[asset_id] = list(lots)
        return lots_by_asset

    async def assemble(
        self,
        prepared: AiExportPreparedRequest,
        session: AsyncSession,
    ) -> AiExportBrokerSnapshotResponse:
        request = prepared.request
        if not isinstance(request, AiExportBrokerSnapshotRequest):
            raise TypeError("broker assembler requires AiExportBrokerSnapshotRequest")
        broker_id = _validate_single_broker_scope(prepared, request)
        initial_ranges = resolve_ranges(prepared)

        report_query = PortfolioReportQuery(
            broker_ids=[broker_id],
            date_range=OpenDateRangeModel(
                start=initial_ranges.selected_range.start,
                end=initial_ranges.selected_range.end,
            ),
            target_currency=request.target_currency,
            include_summary=True,
            include_history=True,
            include_allocation_history=False,
            include_breakdown=True,
            include_positions_contribution=True,
        )
        service = self._portfolio_service or self._portfolio_service_factory(session)
        try:
            report = await service.get_report(prepared.user_id, report_query)
        except Exception as exc:
            raise AiExportSourceFailureError(
                "portfolio_service",
                "get_report",
                context={"broker_ids": [broker_id]},
            ) from exc

        summary = getattr(report, "summary", None)
        history = getattr(report, "history", None)
        contribution_section = getattr(report, "positions_contribution", None)
        if summary is None:
            raise AiExportSourceFailureError("portfolio_service", "missing_summary")
        if history is None:
            raise AiExportSourceFailureError("portfolio_service", "missing_history")
        if contribution_section is None:
            raise AiExportSourceFailureError(
                "portfolio_service",
                "missing_positions_contribution",
            )
        if any(not hasattr(contribution_section, field) for field in ("positions", "unallocated", "other_effects")):
            raise AiExportSourceFailureError(
                "portfolio_service",
                "incomplete_positions_contribution",
            )
        holdings = list(getattr(summary, "holdings", ()))
        contribution_rows = list(contribution_section.positions)
        unallocated_rows = list(contribution_section.unallocated)
        other_effect_rows = list(contribution_section.other_effects)
        _validate_report_scope(
            broker_id=broker_id,
            summary=summary,
            holdings=holdings,
            contributions=contribution_rows,
            unallocated=unallocated_rows,
            other_effects=other_effect_rows,
        )

        asset_ids = sorted({int(row.asset_id) for row in (*holdings, *contribution_rows) if getattr(row, "asset_id", None) is not None})
        historical_asset_ids: set[int] = set()
        if request.task == AiExportBrokerTask.BROKER_FIFO_LOT_REVIEW:
            try:
                historical_asset_ids = await self._transaction_asset_ids_loader(
                    session,
                    [broker_id],
                    initial_ranges.snapshot_as_of,
                )
            except Exception as exc:
                raise AiExportSourceFailureError(
                    "transaction_store",
                    "load_transaction_asset_ids",
                    context={"broker_id": broker_id},
                ) from exc
            asset_ids = sorted(set(asset_ids) | historical_asset_ids)
        try:
            raw_assets = await self._asset_metadata_loader(session, asset_ids)
        except Exception as exc:
            raise AiExportSourceFailureError(
                "asset_store",
                "load_assets_bulk",
                context={"asset_ids": asset_ids},
            ) from exc
        try:
            raw_brokers = await self._broker_metadata_loader(session, [broker_id])
        except Exception as exc:
            raise AiExportSourceFailureError(
                "broker_store",
                "load_brokers_bulk",
                context={"broker_ids": [broker_id]},
            ) from exc
        assets = _entity_map(raw_assets)
        brokers = _entity_map(raw_brokers)
        broker = brokers.get(broker_id)
        if broker is None:
            raise AiExportEntityNotFoundError("broker", broker_id)

        try:
            raw_holdings = _build_raw_holding_maps(holdings)
            all_contributions, contribution_sources = _build_contributions(
                contribution_rows,
                assets=assets,
                brokers=brokers,
                target_currency=request.target_currency,
            )
            all_unallocated_contributions = _build_unallocated_contributions(
                unallocated_rows,
                brokers=brokers,
                target_currency=request.target_currency,
            )
            all_other_period_effects = _build_other_period_effects(
                other_effect_rows,
                brokers=brokers,
                target_currency=request.target_currency,
            )
            all_positions = _build_positions(
                holdings,
                contribution_by_key=contribution_sources,
                assets=assets,
                brokers=brokers,
                target_currency=request.target_currency,
            )
            broker_summary = _build_broker_summary(
                summary,
                broker=broker,
                broker_id=broker_id,
                target_currency=request.target_currency,
            )
        except AiExportAssemblerError:
            raise
        except Exception as exc:
            raise AiExportSourceFailureError(
                "portfolio_service",
                "map_broker_report",
            ) from exc

        held_asset_ids = sorted({position.asset_id for position in all_positions})
        nav_weights = raw_holdings.asset_nav_weights
        if request.task == AiExportBrokerTask.BROKER_FIFO_LOT_REVIEW and not held_asset_ids:
            raise AiExportTaskNotApplicableError(
                prepared.resolved_profile.applicability_code,
                "broker_has_no_open_positions_or_lots",
                context={"broker_id": broker_id},
            )

        fifo_required = request.task == AiExportBrokerTask.BROKER_FIFO_LOT_REVIEW and profile_requires(
            prepared.resolved_profile,
            "facts.fifo_summary",
        )
        fifo_requested = fifo_required or (
            request.task == AiExportBrokerTask.BROKER_REVIEW
            and request.detail_level == AiExportDetailLevel.FULL
            and profile_allows(
                prepared.resolved_profile,
                "facts.fifo_summary",
            )
        )
        fifo_scope_asset_ids = sorted(set(held_asset_ids) | historical_asset_ids) if request.task == AiExportBrokerTask.BROKER_FIFO_LOT_REVIEW else held_asset_ids
        fifo_lots_by_asset = (
            await self._load_fifo_lots(
                prepared=prepared,
                session=session,
                asset_ids=fifo_scope_asset_ids,
                broker_id=broker_id,
                ranges=initial_ranges,
                required=fifo_required,
            )
            if fifo_requested
            else None
        )

        selection = None
        selected_asset_ids = set(held_asset_ids)
        if request.detail_level == AiExportDetailLevel.COMPACT:
            selected_asset_ids, selection = _select_compact_assets(
                request.task,
                profile=prepared.resolved_profile,
                positions=all_positions,
                contribution_sources=contribution_sources,
                fifo_lots_by_asset=fifo_lots_by_asset,
                broker_id=broker_id,
                raw_holdings=raw_holdings,
            )

        fifo_summary = None
        if fifo_lots_by_asset is not None:
            fifo_asset_ids = set(held_asset_ids)
            selected_lots_by_asset = {asset_id: fifo_lots_by_asset.get(asset_id, []) for asset_id in sorted(fifo_asset_ids)}
            try:
                missing_open_lot_asset_ids = [asset_id for asset_id, lots in selected_lots_by_asset.items() if not has_nonzero_open_lot(lots)]
            except Exception as exc:
                if fifo_required:
                    raise AiExportSourceFailureError(
                        "lots_analysis_service",
                        "invalid_open_lot_summary",
                        context={
                            "broker_id": broker_id,
                            "asset_ids": sorted(fifo_asset_ids),
                        },
                    ) from exc
                missing_open_lot_asset_ids = sorted(fifo_asset_ids)
            if missing_open_lot_asset_ids:
                if fifo_required:
                    raise AiExportSourceFailureError(
                        "lots_analysis_service",
                        "missing_open_lot_summary",
                        context={
                            "broker_id": broker_id,
                            "asset_ids": missing_open_lot_asset_ids,
                        },
                    )
            elif selected_lots_by_asset:
                combined_lots = [lot for lots in selected_lots_by_asset.values() for lot in lots]
                try:
                    fifo_summary = _fifo_summary(
                        combined_lots,
                        request.target_currency,
                        initial_ranges.snapshot_as_of,
                    )
                except Exception as exc:
                    if fifo_required:
                        raise AiExportSourceFailureError(
                            "lots_analysis_service",
                            "aggregate_lot_summary",
                            context={"broker_id": broker_id},
                        ) from exc
        if fifo_required and fifo_summary is None:
            raise AiExportSourceFailureError(
                "lots_analysis_service",
                "missing_open_lot_summary",
                context={"broker_id": broker_id},
            )

        fifo_rows: list[Any] = []
        fifo_lot_selection: AiExportSelectionMetadata | None = None
        if request.task == AiExportBrokerTask.BROKER_FIFO_LOT_REVIEW:
            if fifo_lots_by_asset is None:
                raise AiExportSourceFailureError(
                    "lots_analysis_service",
                    "missing_fifo_lot_rows_source",
                    context={"broker_id": broker_id},
                )
            extra_broker_ids = sorted(
                {int(lot.opening_broker_id) for lots in fifo_lots_by_asset.values() for lot in lots}
                - set(brokers)
            )
            if extra_broker_ids:
                try:
                    raw_extra_brokers = await self._broker_metadata_loader(session, extra_broker_ids)
                except Exception as exc:
                    raise AiExportSourceFailureError(
                        "broker_store",
                        "load_brokers_bulk",
                        context={"broker_ids": extra_broker_ids},
                    ) from exc
                brokers = {**brokers, **_entity_map(raw_extra_brokers)}
            cutoff = closed_lot_cutoff_date(initial_ranges.snapshot_as_of)
            try:
                fifo_candidates = collect_fifo_candidates(
                    fifo_lots_by_asset,
                    currency_code=request.target_currency,
                    cutoff=cutoff,
                    assets=assets,
                    brokers=brokers,
                )
            except Exception as exc:
                raise AiExportSourceFailureError(
                    "lots_analysis_service",
                    "invalid_fifo_lot_row",
                    context={"broker_id": broker_id},
                ) from exc
            if request.detail_level == AiExportDetailLevel.COMPACT:
                selected_fifo_candidates = select_compact_fifo_lots(fifo_candidates)
                fifo_lot_selection = build_fifo_lot_selection_metadata(
                    rule=FIFO_LOT_SELECTION_RULE,
                    limit=COMPACT_TOTAL_LIMIT,
                    candidates=fifo_candidates,
                    selected=selected_fifo_candidates,
                    asset_nav_weights=nav_weights,
                )
            else:
                selected_fifo_candidates = fifo_candidates
            fifo_rows = [candidate.row for candidate in selected_fifo_candidates]
            if not fifo_rows:
                raise AiExportSourceFailureError(
                    "lots_analysis_service",
                    "missing_fifo_lot_rows",
                    context={"broker_id": broker_id},
                )

        prepared_targets: list[PreparedTechnicalTarget] = []
        for asset_id in held_asset_ids:
            try:
                technical_target = self._technical_preparer(
                    prepared.resolved_profile,
                    AiExportAssetTargetReference(
                        kind="asset",
                        asset_id=asset_id,
                    ),
                    initial_ranges.technical_window,
                    target_currency=request.target_currency,
                    nav_weight_pct=nav_weights.get(
                        asset_id,
                        Decimal("0"),
                    ),
                )
            except Exception as exc:
                raise AiExportSourceFailureError(
                    "technical_runner",
                    "prepare",
                    context={"asset_id": asset_id},
                ) from exc
            if technical_target is not None:
                prepared_targets.append(technical_target)

        ranges = _technical_ranges(prepared, prepared_targets)
        price_result_by_asset: dict[int, Any] = {}
        if prepared_targets:
            price_queries = [
                FAPriceQueryItem(
                    asset_id=target.target.asset_id,
                    date_range=target.calculation_range,
                    include_price=True,
                    include_events=True,
                    target_currency=request.target_currency,
                    signals=[],
                    annotation_requests=[],
                )
                for target in prepared_targets
                if isinstance(target.target, AiExportAssetTargetReference)
            ]
            try:
                raw_prices = await self._price_bulk_loader(
                    price_queries,
                    session,
                )
            except Exception as exc:
                raise AiExportSourceFailureError(
                    "asset_source",
                    "get_prices_bulk",
                    context={"asset_ids": held_asset_ids},
                ) from exc
            for result in _price_results(raw_prices):
                result_asset_id = getattr(result, "asset_id", None)
                if result_asset_id is not None:
                    price_result_by_asset[int(result_asset_id)] = result

        technical_results: list[TechnicalTargetResult] = []
        for target in sorted(
            prepared_targets,
            key=lambda item: (item.target.asset_id if isinstance(item.target, AiExportAssetTargetReference) else 0),
        ):
            if not isinstance(target.target, AiExportAssetTargetReference):
                raise AiExportSourceFailureError(
                    "technical_runner",
                    "invalid_asset_target",
                )
            asset_id = target.target.asset_id
            price_result = price_result_by_asset.get(asset_id)
            signal_prices = (
                _signal_prices(
                    getattr(price_result, "prices", ()),
                    request.target_currency,
                )
                if price_result is not None
                else ()
            )
            signal_events = _signal_events(getattr(price_result, "events", ())) if price_result is not None else ()
            range_end = target.calculation_range.end or target.calculation_range.start
            signal_prices = tuple(point for point in signal_prices if target.calculation_range.start <= point.date <= range_end)
            signal_events = tuple(point for point in signal_events if target.calculation_range.start <= point.date <= range_end)
            try:
                result = await self._technical_executor(
                    target,
                    signal_prices,
                    signal_events,
                    events_loaded=True,
                    source_capability=AssetSourceManager.derive_signal_source_capability(getattr(price_result, "prices", ())),
                )
            except Exception as exc:
                raise AiExportSourceFailureError(
                    "technical_runner",
                    "execute",
                    context={"asset_id": asset_id},
                ) from exc
            technical_results.append(result)
        technical = combine_technical_results(technical_results)

        latest_transaction = None
        if profile_allows(
            prepared.resolved_profile,
            "facts.latest_transaction",
        ):
            try:
                raw_latest_transaction = await self._latest_transaction_loader(
                    session,
                    broker_id,
                    initial_ranges.snapshot_as_of,
                )
                latest_transaction = _build_latest_transaction(raw_latest_transaction)
            except AiExportAssemblerError:
                raise
            except Exception as exc:
                raise AiExportSourceFailureError(
                    "transaction_store",
                    "load_latest_transaction",
                    context={"broker_id": broker_id},
                ) from exc

        exported_positions = [position for position in all_positions if position.asset_id in selected_asset_ids]
        include_contributions = profile_allows(prepared.resolved_profile, "facts.contributions")
        if not include_contributions:
            exported_contributions = []
        elif request.detail_level == AiExportDetailLevel.COMPACT:
            exported_contributions = [contribution for contribution in all_contributions if contribution.asset_id in selected_asset_ids]
        else:
            exported_contributions = list(all_contributions)
        exported_unallocated = list(all_unallocated_contributions) if profile_allows(prepared.resolved_profile, "facts.unallocated_contributions") else []
        exported_other_effects = list(all_other_period_effects) if profile_allows(prepared.resolved_profile, "facts.other_period_effects") else []

        concentration = (
            _build_concentration(
                all_positions,
                selected_asset_ids=(selected_asset_ids if request.detail_level == AiExportDetailLevel.COMPACT else None),
            )
            if profile_allows(
                prepared.resolved_profile,
                "facts.concentration",
            )
            else None
        )
        exported_technical: AiExportTechnicalSnapshot | None = (
            _filter_technical_targets(
                technical.technical,
                selected_asset_ids,
            )
            if request.detail_level == AiExportDetailLevel.COMPACT
            else technical.technical
        )
        exported_states = (
            _filter_entity_scoped_details(
                technical.states,
                selected_asset_ids,
            )
            if request.detail_level == AiExportDetailLevel.COMPACT
            else list(technical.states)
        )
        exported_events = _compact_events(technical_results, selected_asset_ids) if request.detail_level == AiExportDetailLevel.COMPACT else list(technical.events)

        facts = AiExportBrokerFacts(
            summary=broker_summary,
            positions=exported_positions,
            contributions=exported_contributions,
            unallocated_contributions=exported_unallocated,
            other_period_effects=exported_other_effects,
            concentration=concentration,
            latest_transaction=latest_transaction,
            fifo_summary=fifo_summary,
            fifo_lots=fifo_rows,
            fifo_lot_selection=fifo_lot_selection,
            selection=selection,
        )
        response = AiExportBrokerSnapshotResponse(
            domain=AiExportDomain.BROKER,
            task=request.task,
            detail_level=request.detail_level,
            meta=build_snapshot_meta(
                prepared,
                ranges,
                clock=self._clock,
            ),
            methodology=build_methodology(
                uses_weighted_average_cost=bool(exported_positions),
                uses_runtime_fifo=fifo_summary is not None,
            ),
            facts=facts,
            states=exported_states,
            technical=exported_technical,
            events=exported_events,
            coverage=technical.coverage,
            semantics=build_semantics(
                metric_semantics=_metric_semantics(
                    ranges=ranges,
                    facts=facts,
                ),
                signal_semantics=technical.signal_semantics,
                trading_currency=None,
                valuation_currency=request.target_currency,
                underlying_currency_exposure_available=False,
            ),
            domain_notes=_domain_notes(
                assets=assets,
                brokers=brokers,
                profile=prepared.resolved_profile,
                selected_asset_ids=selected_asset_ids,
                selected_broker_ids={broker_id},
            ),
            export_stats=neutral_export_stats(),
        )
        return finalize_response(response)


async def assemble_broker_snapshot(
    prepared: AiExportPreparedRequest,
    session: AsyncSession,
    *,
    assembler: AiExportBrokerAssembler | None = None,
) -> AiExportBrokerSnapshotResponse:
    return await (assembler or AiExportBrokerAssembler()).assemble(
        prepared,
        session,
    )


__all__ = [
    "AiExportBrokerAssembler",
    "assemble_broker_snapshot",
]
