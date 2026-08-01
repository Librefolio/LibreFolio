"""Portfolio-domain AI Export snapshot assembler."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum
from types import MappingProxyType
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, Broker
from backend.app.schemas.ai_export import (
    AiExportAllocationEntry,
    AiExportAssetTargetReference,
    AiExportCashContext,
    AiExportContribution,
    AiExportDetailLevel,
    AiExportDomain,
    AiExportDomainNote,
    AiExportMetricSemantic,
    AiExportNoteSource,
    AiExportNoteSubject,
    AiExportOtherPeriodEffect,
    AiExportPortfolioAllocations,
    AiExportPortfolioFacts,
    AiExportPortfolioSnapshotRequest,
    AiExportPortfolioSnapshotResponse,
    AiExportPortfolioSummary,
    AiExportPortfolioTask,
    AiExportPosition,
    AiExportSelectionMetadata,
    AiExportTechnicalSnapshot,
    AiExportUnallocatedContribution,
    AiExportValuationSource,
)
from backend.app.schemas.assets import FAClassificationParams
from backend.app.schemas.common import BackwardFillInfo, Currency, DateRangeModel, OpenDateRangeModel
from backend.app.schemas.portfolio import LotAnalysisType, PortfolioReportQuery
from backend.app.schemas.prices import FAAssetEventPointOut, FAPricePoint, FAPriceQueryItem
from backend.app.schemas.signals import SignalEventPoint, SignalPricePoint
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
from backend.app.services.ai_export.assemblers.shared import (
    AiExportAssemblerError,
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
from backend.app.services.ai_export.sampling import round_money, round_percentage
from backend.app.services.ai_export.service import AiExportPreparedRequest
from backend.app.services.ai_export.technical import (
    PreparedTechnicalTarget,
    TechnicalTargetResult,
    combine_technical_results,
    deduplicate_and_limit_events,
    execute_technical_target,
    prepare_technical_target,
)
from backend.app.services.asset_source import AssetSourceManager
from backend.app.services.fx import convert_bulk
from backend.app.services.lots_analysis_service import LotsAnalysisService
from backend.app.services.portfolio_service import PortfolioService

PortfolioServiceFactory = Callable[[AsyncSession], Any]
PriceBulkLoader = Callable[[list[FAPriceQueryItem], AsyncSession], Awaitable[Any]]
ConvertBulk = Callable[..., Awaitable[Any]]
AssetMetadataLoader = Callable[[AsyncSession, Sequence[int]], Awaitable[Mapping[int, Asset] | Sequence[Asset]]]
BrokerMetadataLoader = Callable[[AsyncSession, Sequence[int]], Awaitable[Mapping[int, Broker] | Sequence[Broker]]]
TechnicalPreparer = Callable[..., PreparedTechnicalTarget | None]
TechnicalExecutor = Callable[..., Awaitable[TechnicalTargetResult]]
LotsServiceFactory = Callable[[AsyncSession], Any]

PositionKey = tuple[int, int]


@dataclass(frozen=True, slots=True)
class _RawHoldingValue:
    quantity: Decimal
    market_value: Decimal | None
    nav_weight_pct: Decimal | None


@dataclass(frozen=True, slots=True)
class _RawHoldingMaps:
    by_position: Mapping[PositionKey, _RawHoldingValue]
    position_nav_weights: Mapping[PositionKey, Decimal]
    asset_nav_weights: Mapping[int, Decimal]


async def _default_asset_metadata_loader(session: AsyncSession, asset_ids: Sequence[int]) -> Mapping[int, Asset]:
    if not asset_ids:
        return {}
    result = await session.execute(select(Asset).where(Asset.id.in_(sorted(set(asset_ids)))))
    return {asset.id: asset for asset in result.scalars().all() if asset.id is not None}


async def _default_broker_metadata_loader(session: AsyncSession, broker_ids: Sequence[int]) -> Mapping[int, Broker]:
    if not broker_ids:
        return {}
    result = await session.execute(select(Broker).where(Broker.id.in_(sorted(set(broker_ids)))))
    return {broker.id: broker for broker in result.scalars().all() if broker.id is not None}


def _enum_value(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _decimal(value: object) -> Decimal:
    if isinstance(value, bool):
        raise TypeError("boolean is not a decimal")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("value is not a decimal") from exc
    if not result.is_finite():
        raise ValueError("decimal must be finite")
    return result


def _optional_decimal(value: object | None) -> Decimal | None:
    return None if value is None else _decimal(value)


def _money(code: str, amount: object | None) -> Currency | None:
    value = _optional_decimal(amount)
    return Currency(code=code, amount=round_money(value)) if value is not None else None


def _ratio_pct(value: object | None) -> Decimal | None:
    ratio = _optional_decimal(value)
    return round_percentage(ratio * Decimal("100")) if ratio is not None else None


def _percent(value: object | None) -> Decimal | None:
    percentage = _optional_decimal(value)
    return round_percentage(percentage) if percentage is not None else None


def _required_attr(value: object, field: str, operation: str) -> object:
    if not hasattr(value, field) or getattr(value, field) is None:
        raise AiExportSourceFailureError(
            "portfolio_service",
            operation,
            context={"missing_field": field},
        )
    return getattr(value, field)


def _required_currency(value: object, field: str, target_currency: str, operation: str) -> Currency:
    source = _required_attr(value, field, operation)
    code = _required_attr(source, "code", operation)
    amount = _required_attr(source, "amount", operation)
    if str(code).upper() != target_currency:
        raise AiExportSourceFailureError(
            "portfolio_service",
            operation,
            context={
                "field": field,
                "expected_currency": target_currency,
                "actual_currency": str(code),
            },
        )
    result = _money(target_currency, amount)
    if result is None:
        raise AiExportSourceFailureError(
            "portfolio_service",
            operation,
            context={"missing_field": f"{field}.amount"},
        )
    return result


def _optional_currency(value: object, field: str, target_currency: str) -> Currency | None:
    source = getattr(value, field, None)
    if source is None:
        return None
    code = getattr(source, "code", None)
    amount = getattr(source, "amount", None)
    if code is None or amount is None:
        raise AiExportSourceFailureError(
            "portfolio_service",
            "invalid_summary_field",
            context={"field": field},
        )
    if str(code).upper() != target_currency:
        raise AiExportSourceFailureError(
            "portfolio_service",
            "summary_currency_mismatch",
            context={
                "field": field,
                "expected_currency": target_currency,
                "actual_currency": str(code),
            },
        )
    return _money(target_currency, amount)


def _native_currency(amount: object | None, code: object | None, *, field: str) -> Currency | None:
    if amount is None and code is None:
        return None
    if amount is None or code is None:
        raise AiExportSourceFailureError(
            "portfolio_service",
            "invalid_position_field",
            context={"field": field},
        )
    result = _money(str(code).upper(), amount)
    if result is None:
        raise AiExportSourceFailureError(
            "portfolio_service",
            "invalid_position_field",
            context={"field": field},
        )
    return result


def _entity_map(raw: Mapping[int, Any] | Sequence[Any]) -> dict[int, Any]:
    if isinstance(raw, Mapping):
        return {int(entity_id): entity for entity_id, entity in raw.items()}
    result: dict[int, Any] = {}
    for entity in raw:
        entity_id = getattr(entity, "id", None)
        if entity_id is None:
            continue
        result[int(entity_id)] = entity
    return result


def _parse_classification(asset: Asset | Any) -> FAClassificationParams | None:
    raw = getattr(asset, "classification_params", None)
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


def _valuation_source(holding: Any) -> AiExportValuationSource:
    raw = (_enum_value(getattr(holding, "valuation_source", None)) or "").upper()
    if raw == "MARKET_PRICE" and getattr(holding, "current_value", None) is None:
        return AiExportValuationSource.MISSING
    mapped = {
        "MARKET_PRICE": AiExportValuationSource.MARKET_PRICE,
        "LAST_TRADE_PRICE": AiExportValuationSource.LAST_OBSERVED_TRADE_PRICE,
        "MISSING": AiExportValuationSource.MISSING,
    }.get(raw)
    if mapped is None:
        raise AiExportSourceFailureError(
            "portfolio_service",
            "invalid_valuation_source",
            context={
                "asset_id": getattr(holding, "asset_id", None),
                "broker_id": getattr(holding, "broker_id", None),
                "valuation_source": raw or None,
            },
        )
    return mapped


def _position_key(value: Any, *, operation: str) -> PositionKey:
    asset_id = getattr(value, "asset_id", None)
    broker_id = getattr(value, "broker_id", None)
    if asset_id is None or broker_id is None:
        raise AiExportSourceFailureError(
            "portfolio_service",
            operation,
            context={
                "asset_id": asset_id,
                "broker_id": broker_id,
            },
        )
    return int(asset_id), int(broker_id)


def _build_raw_holding_maps(holdings: Sequence[Any]) -> _RawHoldingMaps:
    by_position: dict[PositionKey, _RawHoldingValue] = {}
    position_nav_weights: dict[PositionKey, Decimal] = {}
    asset_nav_weights: dict[int, Decimal] = defaultdict(Decimal)
    for holding in sorted(holdings, key=lambda item: _position_key(item, operation="invalid_holding_key")):
        key = _position_key(holding, operation="invalid_holding_key")
        if key in by_position:
            raise AiExportSourceFailureError(
                "portfolio_service",
                "duplicate_holding_key",
                context={"asset_id": key[0], "broker_id": key[1]},
            )
        quantity = _decimal(_required_attr(holding, "quantity", "missing_holding_field"))
        if quantity.is_zero():
            continue
        source = _valuation_source(holding)
        market_value = _optional_decimal(getattr(holding, "current_value", None))
        nav_weight_pct = _optional_decimal(getattr(holding, "nav_weight_percent", None))
        if source == AiExportValuationSource.MISSING:
            market_value = None
            nav_weight_pct = None
        by_position[key] = _RawHoldingValue(
            quantity=quantity,
            market_value=market_value,
            nav_weight_pct=nav_weight_pct,
        )
        gross_weight = abs(nav_weight_pct) if nav_weight_pct is not None else Decimal("0")
        position_nav_weights[key] = gross_weight
        asset_nav_weights[key[0]] += gross_weight
    return _RawHoldingMaps(
        by_position=MappingProxyType(by_position),
        position_nav_weights=MappingProxyType(position_nav_weights),
        asset_nav_weights=MappingProxyType(dict(asset_nav_weights)),
    )


def _build_contributions(
    rows: Sequence[Any],
    *,
    assets: Mapping[int, Any],
    brokers: Mapping[int, Any],
    target_currency: str,
) -> tuple[list[AiExportContribution], dict[PositionKey, Any]]:
    source_by_key: dict[PositionKey, Any] = {}
    exported: list[AiExportContribution] = []
    for row in sorted(rows, key=lambda item: _position_key(item, operation="invalid_contribution_key")):
        key = _position_key(row, operation="invalid_contribution_key")
        if key in source_by_key:
            raise AiExportSourceFailureError(
                "portfolio_service",
                "duplicate_contribution_key",
                context={"asset_id": key[0], "broker_id": key[1]},
            )
        source_by_key[key] = row
        asset = assets.get(key[0])
        broker = brokers.get(key[1])
        name = getattr(asset, "display_name", None) or getattr(row, "asset_name", None)
        if not name:
            raise AiExportSourceFailureError(
                "asset_store",
                "missing_asset_metadata",
                context={"asset_id": key[0]},
            )
        exported.append(
            AiExportContribution(
                asset_id=key[0],
                name=str(name),
                ticker=(getattr(asset, "identifier_ticker", None) or getattr(row, "asset_ticker", None)),
                asset_type=(_enum_value(getattr(asset, "asset_type", None)) or getattr(row, "asset_type", None)),
                broker_id=key[1],
                broker_name=(getattr(broker, "name", None) or getattr(row, "broker_name", None)),
                period_unrealized_delta_amount=_money(target_currency, getattr(row, "period_unrealized_delta", None)),
                period_realized_pnl_amount=_money(target_currency, getattr(row, "period_realized_gain_loss", None)),
                period_pnl_amount=_money(target_currency, getattr(row, "period_pnl", None)),
                period_income_amount=_money(target_currency, getattr(row, "period_income", None)),
                fees_taxes_amount=_money(target_currency, getattr(row, "period_fees_taxes", None)),
                contribution_pct=_ratio_pct(getattr(row, "period_pnl_percent", None)),
                start_value=_money(target_currency, getattr(row, "start_value", None)),
                end_value=_money(target_currency, getattr(row, "end_value", None)),
                is_fully_sold=bool(getattr(row, "is_fully_sold", False)),
            )
        )
    return exported, source_by_key


def _has_selected_period_contribution_data(
    positions: Sequence[Any],
    unallocated: Sequence[Any],
    other_effects: Sequence[Any],
) -> bool:
    if positions:
        return True
    for row in unallocated:
        if any(
            value is not None and not _decimal(value).is_zero()
            for value in (
                getattr(row, "unallocated_income", None),
                getattr(row, "unallocated_fees_taxes", None),
            )
        ):
            return True
    for row in other_effects:
        value = _required_attr(row, "period_pnl", "invalid_other_period_effect")
        if not _decimal(value).is_zero():
            return True
    return False


def _build_unallocated_contributions(
    rows: Sequence[Any],
    *,
    brokers: Mapping[int, Any],
    target_currency: str,
) -> list[AiExportUnallocatedContribution]:
    exported: list[AiExportUnallocatedContribution] = []
    seen: set[int] = set()
    for row in sorted(rows, key=lambda item: int(_required_attr(item, "broker_id", "invalid_unallocated_contribution"))):
        broker_id = int(_required_attr(row, "broker_id", "invalid_unallocated_contribution"))
        if broker_id in seen:
            raise AiExportSourceFailureError(
                "portfolio_service",
                "duplicate_unallocated_contribution",
                context={"broker_id": broker_id},
            )
        seen.add(broker_id)
        broker = brokers.get(broker_id)
        exported.append(
            AiExportUnallocatedContribution(
                broker_id=broker_id,
                broker_name=(getattr(broker, "name", None) or getattr(row, "broker_name", None)),
                unallocated_income_amount=_money(target_currency, getattr(row, "unallocated_income", None)),
                unallocated_fees_taxes_amount=_money(target_currency, getattr(row, "unallocated_fees_taxes", None)),
            )
        )
    return exported


def _build_other_period_effects(
    rows: Sequence[Any],
    *,
    brokers: Mapping[int, Any],
    target_currency: str,
) -> list[AiExportOtherPeriodEffect]:
    def sort_key(row: Any) -> tuple[str, str, bool, int, Decimal]:
        broker_id = getattr(row, "broker_id", None)
        return (
            str(_required_attr(row, "category", "invalid_other_period_effect")),
            str(_required_attr(row, "description", "invalid_other_period_effect")),
            broker_id is None,
            int(broker_id or 0),
            _decimal(_required_attr(row, "period_pnl", "invalid_other_period_effect")),
        )

    exported: list[AiExportOtherPeriodEffect] = []
    for row in sorted(rows, key=sort_key):
        broker_id_raw = getattr(row, "broker_id", None)
        broker_id = int(broker_id_raw) if broker_id_raw is not None else None
        broker = brokers.get(broker_id) if broker_id is not None else None
        amount = _money(target_currency, _required_attr(row, "period_pnl", "invalid_other_period_effect"))
        if amount is None:
            raise AiExportSourceFailureError("portfolio_service", "invalid_other_period_effect")
        exported.append(
            AiExportOtherPeriodEffect(
                description=str(_required_attr(row, "description", "invalid_other_period_effect")),
                category=str(_required_attr(row, "category", "invalid_other_period_effect")),
                period_pnl_amount=amount,
                broker_id=broker_id,
                broker_name=(getattr(broker, "name", None) or getattr(row, "broker_name", None)),
            )
        )
    return exported


def _build_positions(
    holdings: Sequence[Any],
    *,
    contribution_by_key: Mapping[PositionKey, Any],
    assets: Mapping[int, Any],
    brokers: Mapping[int, Any],
    target_currency: str,
) -> list[AiExportPosition]:
    exported: list[AiExportPosition] = []
    seen: set[PositionKey] = set()
    for holding in sorted(holdings, key=lambda item: _position_key(item, operation="invalid_holding_key")):
        key = _position_key(holding, operation="invalid_holding_key")
        if key in seen:
            raise AiExportSourceFailureError(
                "portfolio_service",
                "duplicate_holding_key",
                context={"asset_id": key[0], "broker_id": key[1]},
            )
        seen.add(key)
        quantity = _decimal(_required_attr(holding, "quantity", "missing_holding_field"))
        if quantity.is_zero():
            continue
        asset = assets.get(key[0])
        if asset is None:
            raise AiExportSourceFailureError(
                "asset_store",
                "missing_asset_metadata",
                context={"asset_id": key[0]},
            )
        broker = brokers.get(key[1])
        contribution = contribution_by_key.get(key)
        source = _valuation_source(holding)
        wac = _optional_decimal(getattr(holding, "wac_per_unit", None))
        cost_basis = wac * quantity if wac is not None else None
        current_value = getattr(holding, "current_value", None)
        current_price = getattr(holding, "current_price", None)
        gain_loss = getattr(holding, "gain_loss", None)
        weight = _percent(getattr(holding, "nav_weight_percent", None))
        if source == AiExportValuationSource.MISSING:
            current_value = None
            current_price = None
            gain_loss = None
            weight = None
        exported.append(
            AiExportPosition(
                asset_id=key[0],
                name=str(getattr(asset, "display_name", None) or getattr(holding, "asset_name", f"Asset {key[0]}")),
                ticker=(getattr(asset, "identifier_ticker", None) or getattr(holding, "asset_ticker", None)),
                asset_type=(_enum_value(getattr(asset, "asset_type", None)) or getattr(holding, "asset_type", None)),
                broker_id=key[1],
                broker_name=(getattr(broker, "name", None) or getattr(holding, "broker_name", None)),
                broker_ids=[key[1]],
                quantity=quantity,
                trading_currency=str(_required_attr(asset, "currency", "missing_asset_currency")).upper(),
                valuation_currency=target_currency,
                valuation_source=source,
                current_unit_price=_money(target_currency, current_price),
                valuation_effective_unit_price=_native_currency(
                    getattr(holding, "valuation_effective_unit_price", None),
                    getattr(holding, "valuation_effective_currency", None),
                    field="valuation_effective_unit_price",
                ),
                valuation_reference_date=getattr(holding, "valuation_reference_date", None),
                valuation_reference_unit_price=_native_currency(
                    getattr(holding, "valuation_reference_unit_price", None),
                    getattr(holding, "valuation_reference_currency", None),
                    field="valuation_reference_unit_price",
                ),
                valuation_split_adjusted=bool(getattr(holding, "valuation_split_adjusted", False)),
                missing_fx_pair=getattr(holding, "missing_fx_pair", None),
                average_unit_cost=_money(target_currency, wac),
                cost_basis=_money(target_currency, cost_basis),
                market_value=_money(target_currency, current_value),
                weight_pct=weight,
                period_pnl_amount=(_money(target_currency, getattr(contribution, "period_pnl", None)) if contribution is not None else None),
                period_pnl_pct=(_ratio_pct(getattr(contribution, "period_pnl_percent", None)) if contribution is not None else None),
                realized_pnl_amount=(_money(target_currency, getattr(contribution, "period_realized_gain_loss", None)) if contribution is not None else None),
                unrealized_pnl_amount=_money(target_currency, gain_loss),
                period_unrealized_delta_amount=(_money(target_currency, getattr(contribution, "period_unrealized_delta", None)) if contribution is not None else None),
                period_income_amount=(_money(target_currency, getattr(contribution, "period_income", None)) if contribution is not None else None),
                period_fees_taxes_amount=(_money(target_currency, getattr(contribution, "period_fees_taxes", None)) if contribution is not None else None),
            )
        )
    return exported


def _portfolio_is_empty(summary: Any) -> bool:
    fields = ("net_worth", "market_value", "cash_total")
    amounts: list[Decimal] = []
    for field in fields:
        value = getattr(summary, field, None)
        amount = getattr(value, "amount", None)
        if amount is None:
            return False
        amounts.append(_decimal(amount))
    return not getattr(summary, "holdings", None) and all(amount.is_zero() for amount in amounts)


def _build_summary(summary: Any, *, target_currency: str, empty_portfolio: bool) -> AiExportPortfolioSummary:
    nav = _required_currency(summary, "net_worth", target_currency, "missing_summary_field")
    market_value = _required_currency(summary, "market_value", target_currency, "missing_summary_field")
    cash = _required_currency(summary, "cash_total", target_currency, "missing_summary_field")
    book_value = _optional_currency(summary, "book_value", target_currency)
    if book_value is None:
        if not empty_portfolio:
            raise AiExportSourceFailureError(
                "portfolio_service",
                "missing_summary_field",
                context={"missing_field": "book_value"},
            )
        book_value = Currency(code=target_currency, amount=Decimal("0"))
    net_capital = _optional_currency(summary, "total_invested", target_currency)
    lifetime_pnl = _optional_currency(summary, "total_gain_loss", target_currency)
    if net_capital is None or lifetime_pnl is None:
        missing = "total_invested" if net_capital is None else "total_gain_loss"
        raise AiExportSourceFailureError(
            "portfolio_service",
            "missing_summary_field",
            context={"missing_field": missing},
        )
    return AiExportPortfolioSummary(
        base_currency=target_currency,
        nav=nav,
        market_value=market_value,
        cash=cash,
        book_value=book_value,
        net_contributed_capital=net_capital,
        start_nav=_optional_currency(summary, "period_nav_start", target_currency),
        net_deposits=_optional_currency(summary, "period_net_flows", target_currency),
        lifetime_pnl_amount=lifetime_pnl,
        period_pnl_amount=_optional_currency(summary, "period_pnl", target_currency),
        realized_pnl_amount=_optional_currency(summary, "period_realized_gain_loss", target_currency),
        unrealized_pnl_amount=_optional_currency(summary, "unrealized_gain_loss", target_currency),
        income_amount=_optional_currency(summary, "period_income", target_currency),
        fees_taxes_amount=_optional_currency(summary, "period_fees_taxes", target_currency),
        twrr_cumulative_pct=_ratio_pct(getattr(summary, "twrr_percent", None)),
        mwrr_annualized_pct=_ratio_pct(getattr(summary, "mwrr_annualized_percent", None)),
        roi_cumulative_pct=_ratio_pct(getattr(summary, "simple_roi_percent", None)),
    )


def _build_cash_context(
    history: Sequence[Any],
    *,
    target_currency: str,
    empty_portfolio: bool,
) -> AiExportCashContext:
    if not history:
        if not empty_portfolio:
            raise AiExportSourceFailureError(
                "portfolio_service",
                "missing_history_point",
            )
        zero = Currency(code=target_currency, amount=Decimal("0"))
        return AiExportCashContext(
            total_cash=zero,
            cash_from_capital=zero.model_copy(deep=True),
            cash_from_generated_returns=zero.model_copy(deep=True),
        )
    latest = max(history, key=lambda point: _required_attr(point, "date", "missing_history_field"))
    return AiExportCashContext(
        total_cash=_required_currency(latest, "cash_value", target_currency, "missing_history_field"),
        cash_from_capital=_required_currency(latest, "cash_from_contributed_capital", target_currency, "missing_history_field"),
        cash_from_generated_returns=_required_currency(latest, "cash_from_generated_returns", target_currency, "missing_history_field"),
    )


def _aggregate_native_cash_balances(balances: Sequence[Any], *, operation: str) -> dict[str, Decimal]:
    amounts: dict[str, Decimal] = defaultdict(Decimal)
    for balance in balances:
        code_raw = _required_attr(balance, "code", operation)
        try:
            code = Currency.validate_code(code_raw)
        except Exception as exc:
            raise AiExportSourceFailureError(
                "portfolio_service",
                operation,
                context={"currency": str(code_raw)},
            ) from exc
        amounts[code] += _decimal(_required_attr(balance, "amount", operation))
    return {code: amount for code, amount in sorted(amounts.items()) if not amount.is_zero()}


def _native_cash_balances(summary: Any) -> dict[str, Decimal]:
    breakdown = list(getattr(summary, "by_broker", ()) or ())
    broker_balances = [balance for row in breakdown for balance in (getattr(row, "cash_balances", ()) or ())]
    summary_balances = list(getattr(summary, "cash_balances", ()) or ())
    by_broker = _aggregate_native_cash_balances(broker_balances, operation="invalid_broker_cash_balances")
    aggregate = _aggregate_native_cash_balances(summary_balances, operation="invalid_summary_cash_balances")
    if by_broker and aggregate and by_broker != aggregate:
        raise AiExportSourceFailureError(
            "portfolio_service",
            "cash_balance_source_mismatch",
            context={
                "broker_currencies": sorted(by_broker),
                "summary_currencies": sorted(aggregate),
            },
        )
    return by_broker or aggregate


async def _target_valued_cash_by_native_currency(
    summary: Any,
    *,
    target_currency: str,
    snapshot_as_of: date,
    session: AsyncSession,
    convert_bulk_fn: ConvertBulk,
) -> dict[str, Decimal]:
    native_balances = _native_cash_balances(summary)
    expected_cash = _required_currency(summary, "cash_total", target_currency, "invalid_summary_field")
    if not native_balances:
        if not expected_cash.amount.is_zero():
            raise AiExportSourceFailureError(
                "portfolio_service",
                "missing_native_cash_balances",
                context={"cash_total": str(expected_cash.amount)},
            )
        return {}

    target_values = {target_currency: native_balances[target_currency]} if target_currency in native_balances else {}
    source_currencies = sorted(code for code in native_balances if code != target_currency)
    conversions = [
        (
            Currency(code=code, amount=native_balances[code]),
            target_currency,
            snapshot_as_of,
        )
        for code in source_currencies
    ]
    if conversions:
        try:
            conversion_output = await convert_bulk_fn(
                session,
                conversions,
                raise_on_error=False,
            )
        except Exception as exc:
            raise AiExportSourceFailureError(
                "fx_service",
                "convert_portfolio_cash_bulk",
                context={
                    "source_currencies": source_currencies,
                    "target_currency": target_currency,
                    "snapshot_as_of": snapshot_as_of.isoformat(),
                },
            ) from exc
        if isinstance(conversion_output, tuple) and len(conversion_output) == 2:
            conversion_results, conversion_errors = conversion_output
        else:
            conversion_results, conversion_errors = conversion_output, ()
        try:
            results = list(conversion_results)
        except TypeError as exc:
            raise AiExportSourceFailureError("fx_service", "invalid_portfolio_cash_bulk_result") from exc
        if conversion_errors:
            raise AiExportSourceFailureError(
                "fx_service",
                "portfolio_cash_conversion_failed",
                context={
                    "source_currencies": source_currencies,
                    "target_currency": target_currency,
                    "error_count": len(conversion_errors),
                },
            )
        if len(results) != len(conversions):
            raise AiExportSourceFailureError(
                "fx_service",
                "invalid_portfolio_cash_bulk_result_count",
                context={
                    "expected_results": len(conversions),
                    "actual_results": len(results),
                },
            )
        for source_currency, result in zip(source_currencies, results, strict=True):
            if result is None:
                raise AiExportSourceFailureError(
                    "fx_service",
                    "portfolio_cash_conversion_unavailable",
                    context={
                        "source_currency": source_currency,
                        "target_currency": target_currency,
                    },
                )
            try:
                converted, actual_date, _backward_filled = result
                converted_code = Currency.validate_code(converted.code)
                converted_amount = _decimal(converted.amount)
                if not isinstance(actual_date, date):
                    raise TypeError("conversion date must be a date")
            except Exception as exc:
                raise AiExportSourceFailureError(
                    "fx_service",
                    "invalid_portfolio_cash_conversion",
                    context={"source_currency": source_currency},
                ) from exc
            if converted_code != target_currency or actual_date > snapshot_as_of:
                raise AiExportSourceFailureError(
                    "fx_service",
                    "invalid_portfolio_cash_conversion",
                    context={
                        "source_currency": source_currency,
                        "expected_currency": target_currency,
                        "actual_currency": converted_code,
                        "snapshot_as_of": snapshot_as_of.isoformat(),
                    },
                )
            target_values[source_currency] = converted_amount

    return dict(sorted(target_values.items()))


def _allocation_entries(items: Sequence[Any], target_currency: str) -> list[AiExportAllocationEntry]:
    entries = [
        AiExportAllocationEntry(
            key=str(_required_attr(item, "name", "invalid_allocation")),
            label=str(_required_attr(item, "name", "invalid_allocation")),
            amount=_money(target_currency, getattr(item, "amount", None)),
            weight_pct=round_percentage(_decimal(_required_attr(item, "value", "invalid_allocation"))),
        )
        for item in items
    ]
    return sorted(entries, key=lambda item: (-item.weight_pct, item.key))


def _build_allocations(
    summary: Any,
    *,
    positions: Sequence[AiExportPosition],
    target_valued_cash_by_currency: Mapping[str, Decimal],
    assets: Mapping[int, Any],
    brokers: Mapping[int, Any],
    target_currency: str,
) -> AiExportPortfolioAllocations:
    nav = _decimal(_required_attr(_required_attr(summary, "net_worth", "invalid_summary_field"), "amount", "invalid_summary_field"))

    asset_amounts: dict[int, Decimal] = defaultdict(Decimal)
    asset_weights: dict[int, Decimal] = defaultdict(Decimal)
    currency_amounts: dict[str, Decimal] = defaultdict(Decimal)
    for position in positions:
        if position.market_value is None or position.weight_pct is None:
            continue
        asset_amounts[position.asset_id] += position.market_value.amount
        asset_weights[position.asset_id] += position.weight_pct
        if position.trading_currency is not None:
            currency_amounts[position.trading_currency] += position.market_value.amount

    by_asset = [
        AiExportAllocationEntry(
            key=str(asset_id),
            label=str(getattr(assets.get(asset_id), "display_name", f"Asset {asset_id}")),
            amount=_money(target_currency, amount),
            weight_pct=round_percentage(asset_weights[asset_id]),
        )
        for asset_id, amount in asset_amounts.items()
    ]
    cash = _required_currency(summary, "cash_total", target_currency, "invalid_summary_field")
    if cash.amount != 0:
        cash_weight = Decimal("0") if nav.is_zero() else cash.amount / nav * Decimal("100")
        by_asset.append(
            AiExportAllocationEntry(
                key="cash",
                label="Cash / Liquidity",
                amount=cash,
                weight_pct=round_percentage(cash_weight),
            )
        )
    for native_currency, target_amount in target_valued_cash_by_currency.items():
        currency_amounts[native_currency] += target_amount

    # Engine cash is transaction-date FX valued, while native cash exposure is
    # snapshot-date FX valued. Use the exposure total as this allocation's own
    # denominator so its amounts stay factual and its weights remain coherent.
    currency_exposure_total = sum(currency_amounts.values(), start=Decimal("0"))
    by_currency = [
        AiExportAllocationEntry(
            key=currency,
            label=currency,
            amount=_money(target_currency, amount),
            weight_pct=round_percentage(Decimal("0") if currency_exposure_total.is_zero() else amount / currency_exposure_total * Decimal("100")),
        )
        for currency, amount in currency_amounts.items()
    ]

    breakdown = _required_attr(summary, "by_broker", "missing_broker_breakdown")
    by_broker: list[AiExportAllocationEntry] = []
    for row in breakdown:
        broker_id = int(_required_attr(row, "broker_id", "invalid_broker_breakdown"))
        broker_nav = _required_currency(row, "net_worth", target_currency, "invalid_broker_breakdown")
        weight = Decimal("0") if nav.is_zero() else broker_nav.amount / nav * Decimal("100")
        by_broker.append(
            AiExportAllocationEntry(
                key=str(broker_id),
                label=str(getattr(brokers.get(broker_id), "name", None) or getattr(row, "broker_name", f"Broker {broker_id}")),
                amount=broker_nav,
                weight_pct=round_percentage(weight),
            )
        )

    return AiExportPortfolioAllocations(
        by_asset=sorted(by_asset, key=lambda item: (-item.weight_pct, item.key)),
        by_asset_type=_allocation_entries(getattr(summary, "allocation_by_type", ()), target_currency),
        by_sector=_allocation_entries(getattr(summary, "allocation_by_sector", ()), target_currency),
        by_geography=_allocation_entries(getattr(summary, "allocation_by_geography", ()), target_currency),
        by_currency=sorted(by_currency, key=lambda item: (-item.weight_pct, item.key)),
        by_broker=sorted(by_broker, key=lambda item: (-item.weight_pct, item.key)),
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


def _signal_prices(prices: Sequence[FAPricePoint], target_currency: str) -> tuple[SignalPricePoint, ...]:
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


def _technical_ranges(
    prepared: AiExportPreparedRequest,
    targets: Sequence[PreparedTechnicalTarget],
) -> AiExportResolvedRanges:
    if not targets:
        return resolve_ranges(prepared)
    return resolve_ranges(
        prepared,
        calculation_range=DateRangeModel(
            start=min(target.calculation_range.start for target in targets),
            end=max((target.calculation_range.end or target.calculation_range.start) for target in targets),
        ),
        calculation_warmup_start=min(target.calculation_warmup_start for target in targets),
    )


def _price_results(raw: Any) -> list[Any]:
    if hasattr(raw, "results"):
        return list(raw.results)
    if hasattr(raw, "items") and not isinstance(raw, (list, tuple)):
        return list(raw.items)
    return list(raw)


def _technical_asset_id(value: Any) -> int | None:
    target = getattr(value, "target", None)
    if isinstance(target, AiExportAssetTargetReference):
        return target.asset_id
    return None


def _filter_technical_targets(
    technical: AiExportTechnicalSnapshot | None,
    selected_asset_ids: set[int],
) -> AiExportTechnicalSnapshot | None:
    if technical is None:
        return None
    targets = [target for target in technical.targets if _technical_asset_id(target) in selected_asset_ids]
    return AiExportTechnicalSnapshot(targets=targets) if targets else None


def _filter_entity_scoped_details(values: Sequence[Any], selected_asset_ids: set[int]) -> list[Any]:
    return [value for value in values if (asset_id := _technical_asset_id(value)) is None or asset_id in selected_asset_ids]


def _compact_events(
    technical_results: Sequence[TechnicalTargetResult],
    selected_asset_ids: set[int],
) -> list[Any]:
    raw_events = tuple(event for result in technical_results for event in result.events)
    selected_events = [event for event in raw_events if _technical_asset_id(event) in selected_asset_ids]
    if not selected_events:
        return []
    event_limits = {result.event_limit for result in technical_results}
    if len(event_limits) != 1:
        raise ValueError("technical results must share one common event limit")
    return list(deduplicate_and_limit_events(selected_events, event_limits.pop()))


def _position_model_key(position: AiExportPosition) -> PositionKey:
    if position.broker_id is None:
        raise ValueError("portfolio position requires broker_id")
    return position.asset_id, position.broker_id


def _contribution_model_key(contribution: AiExportContribution) -> PositionKey:
    if contribution.broker_id is None:
        raise ValueError("portfolio contribution requires broker_id")
    return contribution.asset_id, contribution.broker_id


def _pac_satellite_metric(key: PositionKey, raw_holdings: Mapping[PositionKey, _RawHoldingValue]) -> Decimal | None:
    raw = raw_holdings.get(key)
    if raw is None:
        raise AiExportSourceFailureError(
            "portfolio_service",
            "missing_holding_selection_source",
            context={"asset_id": key[0], "broker_id": key[1]},
        )
    if raw.market_value is not None:
        gross_market_value = abs(raw.market_value)
        return gross_market_value if gross_market_value > 0 else None
    return raw.quantity if raw.quantity > 0 else None


def _selection_metadata(
    *,
    rule: str,
    limit: int,
    all_keys: Sequence[PositionKey | int],
    selected_keys: set[PositionKey | int],
    weights: Mapping[PositionKey | int, Decimal],
) -> AiExportSelectionMetadata:
    total_weight = sum((abs(weights.get(key, Decimal("0"))) for key in all_keys), start=Decimal("0"))
    included_weight = sum((abs(weights.get(key, Decimal("0"))) for key in selected_keys), start=Decimal("0"))
    return AiExportSelectionMetadata(
        rule=rule,
        limit=limit,
        total_entity_count=len(all_keys),
        included_entity_count=len(selected_keys),
        total_nav_weight_pct=round_percentage(total_weight),
        included_nav_weight_pct=round_percentage(included_weight),
    )


def _select_compact_details(
    task: AiExportPortfolioTask,
    *,
    profile: Any,
    positions: Sequence[AiExportPosition],
    raw_holdings: _RawHoldingMaps,
    contributions: Sequence[AiExportContribution],
    technical_events: Sequence[Any],
    fifo_lots_by_asset: Mapping[int, Sequence[Any]] | None = None,
) -> tuple[set[PositionKey], set[int], AiExportSelectionMetadata]:
    spec = profile.compact_selection
    parameters = spec.parameters
    positions_by_key = {_position_model_key(position): position for position in positions}
    contributions_by_key = {_contribution_model_key(contribution): contribution for contribution in contributions}
    position_weights = raw_holdings.position_nav_weights

    selected_position_keys: set[PositionKey] = set()
    selected_asset_ids: set[int] = set()
    metadata: AiExportSelectionMetadata

    if task == AiExportPortfolioTask.PAC_PLANNING:
        largest_count = int(parameters.get("largest_count", 6))
        smallest_count = int(parameters.get("smallest_count", 6))
        largest = sorted(positions_by_key, key=lambda key: (-position_weights[key], key))[:largest_count]
        satellite_metrics = {key: metric for key in positions_by_key if (metric := _pac_satellite_metric(key, raw_holdings.by_position)) is not None}
        smallest = sorted(satellite_metrics, key=lambda key: (satellite_metrics[key], key))[:smallest_count]
        selected_position_keys = set(largest) | set(smallest)
        metadata = _selection_metadata(
            rule=spec.rule,
            limit=spec.entity_limit,
            all_keys=list(positions_by_key),
            selected_keys=selected_position_keys,
            weights=position_weights,
        )
    elif task in {AiExportPortfolioTask.REBALANCING, AiExportPortfolioTask.PORTFOLIO_DESCRIPTION}:
        selected_position_keys = set(sorted(positions_by_key, key=lambda key: (-position_weights[key], key))[: spec.entity_limit])
        metadata = _selection_metadata(
            rule=spec.rule,
            limit=spec.entity_limit,
            all_keys=list(positions_by_key),
            selected_keys=selected_position_keys,
            weights=position_weights,
        )
    elif task == AiExportPortfolioTask.PERFORMANCE_ATTRIBUTION:
        positive_count = int(parameters.get("positive_count", 5))
        negative_count = int(parameters.get("negative_count", 5))

        def pnl(key: PositionKey) -> Decimal:
            value = contributions_by_key[key].period_pnl_amount
            return value.amount if value is not None else Decimal("0")

        positive = sorted((key for key in contributions_by_key if pnl(key) > 0), key=lambda key: (-pnl(key), key))[:positive_count]
        negative = sorted((key for key in contributions_by_key if pnl(key) < 0), key=lambda key: (pnl(key), key))[:negative_count]
        selected_position_keys = set(positive) | set(negative)
        metadata = _selection_metadata(
            rule=spec.rule,
            limit=spec.entity_limit,
            all_keys=list(contributions_by_key),
            selected_keys=selected_position_keys,
            weights=position_weights,
        )
    elif task == AiExportPortfolioTask.INCOME_REVIEW:

        def income(key: PositionKey) -> Decimal:
            value = contributions_by_key[key].period_income_amount
            return value.amount if value is not None else Decimal("0")

        selected_position_keys = set(sorted((key for key in contributions_by_key if income(key) > 0), key=lambda key: (-income(key), key))[: spec.entity_limit])
        metadata = _selection_metadata(
            rule=spec.rule,
            limit=spec.entity_limit,
            all_keys=list(contributions_by_key),
            selected_keys=selected_position_keys,
            weights=position_weights,
        )
    elif task == AiExportPortfolioTask.TECHNICAL_BREADTH:
        asset_weights = raw_holdings.asset_nav_weights
        all_asset_ids = sorted({position.asset_id for position in positions})
        latest_event: dict[int, date] = {}
        for event in technical_events:
            asset_id = _technical_asset_id(event)
            if asset_id is not None and (asset_id not in latest_event or event.date > latest_event[asset_id]):
                latest_event[asset_id] = event.date
        with_events = sorted(
            (asset_id for asset_id in all_asset_ids if asset_id in latest_event),
            key=lambda asset_id: (-latest_event[asset_id].toordinal(), -asset_weights.get(asset_id, Decimal("0")), asset_id),
        )
        fallback = sorted(
            (asset_id for asset_id in all_asset_ids if asset_id not in latest_event),
            key=lambda asset_id: (-asset_weights.get(asset_id, Decimal("0")), asset_id),
        )
        selected_asset_ids = set((with_events + fallback)[: spec.entity_limit])
        selected_position_keys = {key for key in positions_by_key if key[0] in selected_asset_ids}
        metadata = _selection_metadata(
            rule=spec.rule,
            limit=spec.entity_limit,
            all_keys=all_asset_ids,
            selected_keys=selected_asset_ids,
            weights=asset_weights,
        )
    elif task == AiExportPortfolioTask.PORTFOLIO_FIFO_LOT_REVIEW:
        if fifo_lots_by_asset is None:
            raise AiExportSourceFailureError(
                "lots_analysis_service",
                "missing_compact_fifo_selection_source",
            )
        asset_weights = raw_holdings.asset_nav_weights
        all_asset_ids = sorted({position.asset_id for position in positions})
        ranked = sorted(
            all_asset_ids,
            key=lambda asset_id: (
                -asset_residual_cost_basis(fifo_lots_by_asset.get(asset_id, ())),
                -asset_weights.get(asset_id, Decimal("0")),
                asset_id,
            ),
        )
        selected_asset_ids = set(ranked[: spec.entity_limit])
        selected_position_keys = {key for key in positions_by_key if key[0] in selected_asset_ids}
        metadata = _selection_metadata(
            rule=spec.rule,
            limit=spec.entity_limit,
            all_keys=all_asset_ids,
            selected_keys=selected_asset_ids,
            weights=asset_weights,
        )
    else:
        raise ValueError(f"unsupported Portfolio task: {task}")

    if not selected_asset_ids:
        selected_asset_ids = {key[0] for key in selected_position_keys}
    return selected_position_keys, selected_asset_ids, metadata


def _domain_notes(
    *,
    assets: Mapping[int, Any],
    brokers: Mapping[int, Any],
    profile: Any,
    selected_asset_ids: set[int] | None = None,
    selected_broker_ids: set[int] | None = None,
) -> list[AiExportDomainNote]:
    if not profile_allows(profile, "domain_notes"):
        return []
    notes: list[AiExportDomainNote] = []
    for broker_id, broker in sorted(brokers.items()):
        if selected_broker_ids is not None and broker_id not in selected_broker_ids:
            continue
        text = getattr(broker, "description", None)
        if isinstance(text, str) and text.strip():
            notes.append(
                AiExportDomainNote(
                    subject=AiExportNoteSubject.BROKER,
                    source=AiExportNoteSource.USER,
                    text=text[:4000],
                    subject_reference=f"broker:{broker_id}",
                )
            )
    for asset_id, asset in sorted(assets.items()):
        if selected_asset_ids is not None and asset_id not in selected_asset_ids:
            continue
        classification = _parse_classification(asset)
        text = classification.short_description if classification is not None else None
        if isinstance(text, str) and text.strip():
            notes.append(
                AiExportDomainNote(
                    subject=AiExportNoteSubject.ASSET,
                    source=AiExportNoteSource.PROVIDER_OR_USER,
                    text=text[:4000],
                    subject_reference=f"asset:{asset_id}",
                )
            )
    return sorted(notes, key=lambda note: (note.subject.value, note.subject_reference or "", note.text))


def _metric_semantics(
    *,
    ranges: AiExportResolvedRanges,
    facts: AiExportPortfolioFacts,
) -> list[AiExportMetricSemantic]:
    snapshot_period = DateRangeModel(start=ranges.snapshot_as_of, end=ranges.snapshot_as_of)
    selected = ranges.selected_range
    semantics = [
        AiExportMetricSemantic(metric_code="portfolio.nav", unit="target_currency", method="portfolio_engine_snapshot", period=snapshot_period, universe="authenticated_broker_scope"),
        AiExportMetricSemantic(metric_code="portfolio.market_value", unit="target_currency", method="portfolio_engine_snapshot", period=snapshot_period, universe="valued_open_positions"),
        AiExportMetricSemantic(metric_code="portfolio.cash", unit="target_currency", method="portfolio_engine_snapshot", period=snapshot_period, universe="authenticated_broker_scope"),
        AiExportMetricSemantic(metric_code="portfolio.book_value", unit="target_currency", method="portfolio_engine_snapshot", period=snapshot_period, universe="authenticated_broker_scope"),
    ]
    optional_summary = (
        ("portfolio.net_contributed_capital", facts.summary.net_contributed_capital, "target_currency", "portfolio_service_total_invested_lifetime", None, False, True),
        ("portfolio.start_nav", facts.summary.start_nav, "target_currency", "selected_period_start_nav", selected, False, False),
        ("portfolio.net_deposits", facts.summary.net_deposits, "target_currency", "portfolio_service_period_net_flows", selected, False, True),
        ("portfolio.lifetime_pnl_amount", facts.summary.lifetime_pnl_amount, "target_currency", "portfolio_service_lifetime_gain_loss", snapshot_period, False, True),
        ("portfolio.period_pnl_amount", facts.summary.period_pnl_amount, "target_currency", "nav_change_net_external_flows", selected, False, True),
        ("portfolio.realized_pnl_amount", facts.summary.realized_pnl_amount, "target_currency", "weighted_average_cost_realized", selected, False, True),
        ("portfolio.unrealized_pnl_amount", facts.summary.unrealized_pnl_amount, "target_currency", "market_value_minus_book_value", snapshot_period, False, False),
        ("portfolio.income_amount", facts.summary.income_amount, "target_currency", "period_income", selected, False, True),
        ("portfolio.fees_taxes_amount", facts.summary.fees_taxes_amount, "target_currency", "period_fees_taxes_positive_cost", selected, False, True),
        ("portfolio.twrr_cumulative_pct", facts.summary.twrr_cumulative_pct, "percentage_points", "time_weighted_return", selected, False, True),
        ("portfolio.mwrr_annualized_pct", facts.summary.mwrr_annualized_pct, "percentage_points", "money_weighted_return_xirr", selected, True, False),
        ("portfolio.roi_cumulative_pct", facts.summary.roi_cumulative_pct, "percentage_points", "simple_roi", selected, False, True),
    )
    for code, value, unit, method, period, annualized, cumulative in optional_summary:
        if value is not None:
            semantics.append(
                AiExportMetricSemantic(
                    metric_code=code,
                    unit=unit,
                    method=method,
                    period=period,
                    universe="authenticated_broker_scope",
                    annualized=annualized,
                    cumulative=cumulative,
                )
            )
    if facts.positions:
        semantics.append(
            AiExportMetricSemantic(
                metric_code="portfolio.position_weight_pct",
                unit="percentage_points",
                denominator="portfolio_nav",
                method="signed_authoritative_nav_weight",
                period=snapshot_period,
                universe="open_positions",
                cumulative=False,
            )
        )
    if any(position.period_pnl_pct is not None for position in facts.positions):
        semantics.append(
            AiExportMetricSemantic(
                metric_code="portfolio.position_period_pnl_pct",
                unit="percentage_points",
                denominator="absolute_position_start_value",
                method="portfolio_service_period_contribution",
                period=selected,
                universe="period_contributions",
                cumulative=True,
            )
        )
    if facts.contributions:
        semantics.append(
            AiExportMetricSemantic(
                metric_code="portfolio.contribution_pct",
                unit="percentage_points",
                denominator="absolute_position_start_value",
                method="portfolio_service_period_contribution",
                period=selected,
                universe="period_contributions",
                cumulative=True,
            )
        )
    if any(item.unallocated_income_amount is not None for item in facts.unallocated_contributions):
        semantics.append(
            AiExportMetricSemantic(
                metric_code="portfolio.unallocated_income_amount",
                unit="target_currency",
                method="portfolio_service_unallocated_period_income",
                period=selected,
                universe="broker_level_unallocated_contributions",
                cumulative=True,
            )
        )
    if any(item.unallocated_fees_taxes_amount is not None for item in facts.unallocated_contributions):
        semantics.append(
            AiExportMetricSemantic(
                metric_code="portfolio.unallocated_fees_taxes_amount",
                unit="target_currency",
                method="portfolio_service_unallocated_period_fees_taxes",
                period=selected,
                universe="broker_level_unallocated_contributions",
                cumulative=True,
            )
        )
    if facts.other_period_effects:
        semantics.append(
            AiExportMetricSemantic(
                metric_code="portfolio.other_period_effect_pnl_amount",
                unit="target_currency",
                method="portfolio_service_other_period_effect",
                period=selected,
                universe="non_position_period_effects",
                cumulative=True,
            )
        )
    allocation_semantics = (
        ("portfolio.allocation_by_asset_pct", facts.allocations.by_asset, "portfolio_nav", "position_nav_weight_and_cash"),
        ("portfolio.allocation_by_asset_type_pct", facts.allocations.by_asset_type, "portfolio_nav", "portfolio_engine_allocation"),
        ("portfolio.allocation_by_sector_pct", facts.allocations.by_sector, "portfolio_nav", "portfolio_engine_allocation"),
        ("portfolio.allocation_by_geography_pct", facts.allocations.by_geography, "invested_market_value", "portfolio_engine_allocation"),
        (
            "portfolio.allocation_by_currency_pct",
            facts.allocations.by_currency,
            "trading_currency_positions_plus_native_cash_snapshot_value",
            "trading_currency_positions_plus_native_cash_snapshot_conversion",
        ),
        ("portfolio.allocation_by_broker_pct", facts.allocations.by_broker, "portfolio_nav", "portfolio_service_broker_breakdown"),
    )
    for code, entries, denominator, method in allocation_semantics:
        if entries:
            semantics.append(
                AiExportMetricSemantic(
                    metric_code=code,
                    unit="percentage_points",
                    denominator=denominator,
                    method=method,
                    period=snapshot_period,
                    universe="authenticated_broker_scope",
                    cumulative=False,
                )
            )
    if facts.fifo_summary is not None:
        semantics.append(
            AiExportMetricSemantic(
                metric_code="portfolio.fifo_residual_cost_basis",
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
                metric_code="portfolio.fifo_lot_residual_cost_basis",
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
                metric_code="portfolio.fifo_lot_selection_nav_weight_pct",
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
                metric_code="portfolio.selection_nav_weight_pct",
                unit="percentage_points",
                denominator="gross_absolute_candidate_nav_exposure",
                method=f"{facts.selection.rule}_with_gross_nav_coverage",
                period=snapshot_period,
                universe="compact_selection_candidates",
                cumulative=False,
            )
        )
    return semantics


class AiExportPortfolioAssembler:
    """Assemble all resolved Portfolio task/detail profiles."""

    def __init__(
        self,
        *,
        portfolio_service_factory: PortfolioServiceFactory = PortfolioService,
        portfolio_service: Any | None = None,
        lots_service_factory: LotsServiceFactory = LotsAnalysisService,
        lots_service: Any | None = None,
        price_bulk_loader: PriceBulkLoader = AssetSourceManager.get_prices_bulk,
        convert_bulk_fn: ConvertBulk = convert_bulk,
        asset_metadata_loader: AssetMetadataLoader = _default_asset_metadata_loader,
        broker_metadata_loader: BrokerMetadataLoader = _default_broker_metadata_loader,
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
        self._convert_bulk = convert_bulk_fn
        self._asset_metadata_loader = asset_metadata_loader
        self._broker_metadata_loader = broker_metadata_loader
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
        broker_ids: Sequence[int],
        ranges: AiExportResolvedRanges,
        required: bool,
    ) -> dict[int, list[Any]] | None:
        service = self._lots_service or self._lots_service_factory(session)
        scoped_broker_ids = sorted(set(broker_ids))
        lots_by_asset: dict[int, list[Any]] = {}
        for asset_id in sorted(set(asset_ids)):
            try:
                response = await service.get_lots_analysis(
                    user_id=prepared.user_id,
                    asset_id=asset_id,
                    broker_ids=scoped_broker_ids,
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
                        "broker_ids": scoped_broker_ids,
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
                        "broker_ids": scoped_broker_ids,
                        "calculation_status": status or None,
                    },
                )
            lots_by_asset[asset_id] = list(lots)
        return lots_by_asset

    async def assemble(
        self,
        prepared: AiExportPreparedRequest,
        session: AsyncSession,
    ) -> AiExportPortfolioSnapshotResponse:
        request = prepared.request
        if not isinstance(request, AiExportPortfolioSnapshotRequest):
            raise TypeError("portfolio assembler requires AiExportPortfolioSnapshotRequest")

        initial_ranges = resolve_ranges(prepared)
        report_query = PortfolioReportQuery(
            broker_ids=list(prepared.broker_scope),
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
                context={"broker_ids": list(prepared.broker_scope)},
            ) from exc

        summary = getattr(report, "summary", None)
        history = getattr(report, "history", None)
        contribution_section = getattr(report, "positions_contribution", None)
        if summary is None:
            raise AiExportSourceFailureError("portfolio_service", "missing_summary")
        if history is None:
            raise AiExportSourceFailureError("portfolio_service", "missing_history")
        if contribution_section is None:
            raise AiExportSourceFailureError("portfolio_service", "missing_positions_contribution")
        contribution_rows = list(getattr(contribution_section, "positions", ()))
        unallocated_rows = list(getattr(contribution_section, "unallocated", ()))
        other_effect_rows = list(getattr(contribution_section, "other_effects", ()))

        try:
            has_contribution_data = _has_selected_period_contribution_data(
                contribution_rows,
                unallocated_rows,
                other_effect_rows,
            )
        except AiExportAssemblerError:
            raise
        except Exception as exc:
            raise AiExportSourceFailureError("portfolio_service", "invalid_positions_contribution") from exc
        if request.task == AiExportPortfolioTask.PERFORMANCE_ATTRIBUTION and not has_contribution_data:
            raise AiExportTaskNotApplicableError(
                prepared.resolved_profile.applicability_code,
                "selected_range_has_no_contributions",
                context={
                    "broker_ids": list(prepared.broker_scope),
                    "history_points": len(history),
                    "contribution_rows": len(contribution_rows),
                    "unallocated_rows": len(unallocated_rows),
                    "other_effect_rows": len(other_effect_rows),
                },
            )

        holdings = list(getattr(summary, "holdings", ()))
        asset_ids = sorted({int(row.asset_id) for row in (*holdings, *contribution_rows) if getattr(row, "asset_id", None) is not None})
        historical_asset_ids: set[int] = set()
        if request.task == AiExportPortfolioTask.PORTFOLIO_FIFO_LOT_REVIEW:
            try:
                historical_asset_ids = await self._transaction_asset_ids_loader(
                    session,
                    list(prepared.broker_scope),
                    initial_ranges.snapshot_as_of,
                )
            except Exception as exc:
                raise AiExportSourceFailureError(
                    "transaction_store",
                    "load_transaction_asset_ids",
                    context={"broker_ids": list(prepared.broker_scope)},
                ) from exc
            asset_ids = sorted(set(asset_ids) | historical_asset_ids)
        broker_ids = sorted(
            set(prepared.broker_scope)
            | {int(row.broker_id) for row in (*holdings, *contribution_rows, *unallocated_rows, *other_effect_rows) if getattr(row, "broker_id", None) is not None}
            | {int(row.broker_id) for row in (getattr(summary, "by_broker", ()) or ()) if getattr(row, "broker_id", None) is not None}
        )
        try:
            raw_assets = await self._asset_metadata_loader(session, asset_ids)
        except Exception as exc:
            raise AiExportSourceFailureError(
                "asset_store",
                "load_assets_bulk",
                context={"asset_ids": asset_ids},
            ) from exc
        try:
            raw_brokers = await self._broker_metadata_loader(session, broker_ids)
        except Exception as exc:
            raise AiExportSourceFailureError(
                "broker_store",
                "load_brokers_bulk",
                context={"broker_ids": broker_ids},
            ) from exc
        assets = _entity_map(raw_assets)
        brokers = _entity_map(raw_brokers)

        try:
            raw_holdings = _build_raw_holding_maps(holdings)
            all_contributions, contribution_by_key = _build_contributions(
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
                contribution_by_key=contribution_by_key,
                assets=assets,
                brokers=brokers,
                target_currency=request.target_currency,
            )
            empty_portfolio = _portfolio_is_empty(summary)
            portfolio_summary = _build_summary(
                summary,
                target_currency=request.target_currency,
                empty_portfolio=empty_portfolio,
            )
            cash_context = _build_cash_context(
                history,
                target_currency=request.target_currency,
                empty_portfolio=empty_portfolio,
            )
            target_valued_cash_by_currency = await _target_valued_cash_by_native_currency(
                summary,
                target_currency=request.target_currency,
                snapshot_as_of=initial_ranges.snapshot_as_of,
                session=session,
                convert_bulk_fn=self._convert_bulk,
            )
            allocations = _build_allocations(
                summary,
                positions=all_positions,
                target_valued_cash_by_currency=target_valued_cash_by_currency,
                assets=assets,
                brokers=brokers,
                target_currency=request.target_currency,
            )
        except AiExportAssemblerError:
            raise
        except Exception as exc:
            raise AiExportSourceFailureError(
                "portfolio_service",
                "map_report",
            ) from exc

        asset_weights = raw_holdings.asset_nav_weights
        held_asset_ids = sorted({position.asset_id for position in all_positions})

        fifo_required = request.task == AiExportPortfolioTask.PORTFOLIO_FIFO_LOT_REVIEW and profile_requires(
            prepared.resolved_profile,
            "facts.fifo_summary",
        )
        fifo_scope_asset_ids = sorted(set(held_asset_ids) | historical_asset_ids) if request.task == AiExportPortfolioTask.PORTFOLIO_FIFO_LOT_REVIEW else []
        fifo_lots_by_asset = (
            await self._load_fifo_lots(
                prepared=prepared,
                session=session,
                asset_ids=fifo_scope_asset_ids,
                broker_ids=broker_ids,
                ranges=initial_ranges,
                required=fifo_required,
            )
            if fifo_required
            else None
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
                            "broker_ids": broker_ids,
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
                            "broker_ids": broker_ids,
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
                            context={"broker_ids": broker_ids},
                        ) from exc
        if fifo_required and fifo_summary is None:
            raise AiExportSourceFailureError(
                "lots_analysis_service",
                "missing_open_lot_summary",
                context={"broker_ids": broker_ids},
            )

        fifo_rows: list[Any] = []
        fifo_lot_selection: AiExportSelectionMetadata | None = None
        if request.task == AiExportPortfolioTask.PORTFOLIO_FIFO_LOT_REVIEW:
            if fifo_lots_by_asset is None:
                raise AiExportSourceFailureError(
                    "lots_analysis_service",
                    "missing_fifo_lot_rows_source",
                    context={"broker_ids": broker_ids},
                )
            extra_broker_ids = sorted({int(lot.opening_broker_id) for lots in fifo_lots_by_asset.values() for lot in lots} - set(brokers))
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
                    context={"broker_ids": broker_ids},
                ) from exc
            if request.detail_level == AiExportDetailLevel.COMPACT:
                selected_fifo_candidates = select_compact_fifo_lots(fifo_candidates)
                fifo_lot_selection = build_fifo_lot_selection_metadata(
                    rule=FIFO_LOT_SELECTION_RULE,
                    limit=COMPACT_TOTAL_LIMIT,
                    candidates=fifo_candidates,
                    selected=selected_fifo_candidates,
                    asset_nav_weights=asset_weights,
                )
            else:
                selected_fifo_candidates = fifo_candidates
            fifo_rows = [candidate.row for candidate in selected_fifo_candidates]
            if not fifo_rows:
                raise AiExportSourceFailureError(
                    "lots_analysis_service",
                    "missing_fifo_lot_rows",
                    context={"broker_ids": broker_ids},
                )

        prepared_targets: list[PreparedTechnicalTarget] = []
        for asset_id in held_asset_ids:
            target = AiExportAssetTargetReference(kind="asset", asset_id=asset_id)
            try:
                technical_target = self._technical_preparer(
                    prepared.resolved_profile,
                    target,
                    initial_ranges.technical_window,
                    target_currency=request.target_currency,
                    nav_weight_pct=asset_weights.get(asset_id, Decimal("0")),
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
                raw_prices = await self._price_bulk_loader(price_queries, session)
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
        for target in sorted(prepared_targets, key=lambda item: item.target.asset_id if isinstance(item.target, AiExportAssetTargetReference) else 0):
            if not isinstance(target.target, AiExportAssetTargetReference):
                raise AiExportSourceFailureError("technical_runner", "invalid_asset_target")
            asset_id = target.target.asset_id
            price_result = price_result_by_asset.get(asset_id)
            signal_prices = _signal_prices(getattr(price_result, "prices", ()), request.target_currency) if price_result is not None else ()
            signal_events = _signal_events(getattr(price_result, "events", ())) if price_result is not None else ()
            signal_prices = tuple(point for point in signal_prices if target.calculation_range.start <= point.date <= (target.calculation_range.end or target.calculation_range.start))
            signal_events = tuple(point for point in signal_events if target.calculation_range.start <= point.date <= (target.calculation_range.end or target.calculation_range.start))
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

        selection = None
        selected_position_keys = {_position_model_key(position) for position in all_positions}
        selected_asset_ids = set(held_asset_ids)
        if request.detail_level == AiExportDetailLevel.COMPACT:
            selected_position_keys, selected_asset_ids, selection = _select_compact_details(
                request.task,
                profile=prepared.resolved_profile,
                positions=all_positions,
                raw_holdings=raw_holdings,
                contributions=all_contributions,
                technical_events=tuple(event for result in technical_results for event in result.events),
                fifo_lots_by_asset=fifo_lots_by_asset,
            )

        exported_positions = [position for position in all_positions if _position_model_key(position) in selected_position_keys]
        if profile_allows(prepared.resolved_profile, "facts.contributions"):
            exported_contributions = [contribution for contribution in all_contributions if _contribution_model_key(contribution) in selected_position_keys] if request.detail_level == AiExportDetailLevel.COMPACT else list(all_contributions)
        else:
            exported_contributions = []
        exported_unallocated_contributions = list(all_unallocated_contributions) if profile_allows(prepared.resolved_profile, "facts.unallocated_contributions") else []
        exported_other_period_effects = list(all_other_period_effects) if profile_allows(prepared.resolved_profile, "facts.other_period_effects") else []
        exported_allocations = allocations if profile_allows(prepared.resolved_profile, "facts.allocations") else AiExportPortfolioAllocations()
        exported_cash_context = cash_context if profile_allows(prepared.resolved_profile, "facts.cash_context") else None
        exported_technical = _filter_technical_targets(technical.technical, selected_asset_ids) if request.detail_level == AiExportDetailLevel.COMPACT else technical.technical
        exported_states = _filter_entity_scoped_details(technical.states, selected_asset_ids) if request.detail_level == AiExportDetailLevel.COMPACT else list(technical.states)
        exported_events = _compact_events(technical_results, selected_asset_ids) if request.detail_level == AiExportDetailLevel.COMPACT else list(technical.events)
        selected_broker_ids = {position.broker_id for position in exported_positions if position.broker_id is not None}

        facts = AiExportPortfolioFacts(
            summary=portfolio_summary,
            positions=exported_positions,
            contributions=exported_contributions,
            unallocated_contributions=exported_unallocated_contributions,
            other_period_effects=exported_other_period_effects,
            allocations=exported_allocations,
            cash_context=exported_cash_context,
            fifo_summary=fifo_summary,
            fifo_lots=fifo_rows,
            fifo_lot_selection=fifo_lot_selection,
            selection=selection,
        )
        response = AiExportPortfolioSnapshotResponse(
            domain=AiExportDomain.PORTFOLIO,
            task=request.task,
            detail_level=request.detail_level,
            meta=build_snapshot_meta(
                prepared,
                ranges,
                clock=self._clock,
            ),
            methodology=build_methodology(
                uses_weighted_average_cost=True,
                uses_runtime_fifo=fifo_summary is not None,
                uses_portfolio_cash_decomposition=exported_cash_context is not None,
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
                selected_asset_ids=(selected_asset_ids if request.detail_level == AiExportDetailLevel.COMPACT else None),
                selected_broker_ids=(selected_broker_ids if request.detail_level == AiExportDetailLevel.COMPACT else None),
            ),
            export_stats=neutral_export_stats(),
        )
        return finalize_response(response)


async def assemble_portfolio_snapshot(
    prepared: AiExportPreparedRequest,
    session: AsyncSession,
    *,
    assembler: AiExportPortfolioAssembler | None = None,
) -> AiExportPortfolioSnapshotResponse:
    return await (assembler or AiExportPortfolioAssembler()).assemble(prepared, session)


__all__ = [
    "AiExportPortfolioAssembler",
    "assemble_portfolio_snapshot",
]
