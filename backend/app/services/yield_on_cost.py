"""Transaction-ledger Yield on Cost for portfolio holding snapshots."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Literal, Sequence

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AssetEvent, AssetEventType, Broker, BrokerUserAccess, Transaction, TransactionType
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import (
    YieldOnCostFxProvenance,
    YieldOnCostProvenance,
    YieldOnCostResult,
    YieldOnCostStatus,
    YieldOnCostUnavailableReason,
)
from backend.app.schemas.wac import WACMissingPairInfo
from backend.app.services.fifo_lot_engine import (
    FifoEngineResult,
    FifoEvent,
    FragmentInterval,
    eligible_income_quantity,
    run_fifo_lot_engine,
)
from backend.app.services.fx import convert_bulk

logger = structlog.get_logger(__name__)

PositionKey = tuple[int, int]
_INCOME_TYPES = {TransactionType.DIVIDEND, TransactionType.INTEREST}
_SPLIT_QUANTITY_ABS_TOLERANCE = Decimal("0.000001")
_SPLIT_QUANTITY_REL_TOLERANCE = Decimal("0.000000001")


@dataclass(frozen=True, slots=True)
class YieldOnCostPositionInput:
    """Residual WAC input for one open position at report end."""

    asset_id: int
    broker_id: int
    wac_per_unit: Decimal | None
    wac_currency: str | None


@dataclass(frozen=True, slots=True)
class YieldOnCostPositionCalculation:
    """Public calculation plus converted WAC reused by PortfolioService."""

    result: YieldOnCostResult
    wac_per_unit: Decimal | None
    missing_fx_pairs: tuple[WACMissingPairInfo, ...] = ()


@dataclass(frozen=True, slots=True)
class _SplitRecord:
    transaction_id: int
    event_id: int
    transaction_asset_id: int
    event_asset_id: int
    broker_id: int
    transaction_type: TransactionType
    transaction_quantity: Decimal | None
    transaction_date: date_type
    event_date: date_type
    ratio: Decimal | None


@dataclass(frozen=True, slots=True)
class _ConversionSpec:
    position_key: PositionKey
    purpose: Literal["income", "wac"]
    requested_date: date_type
    from_currency: str
    transaction_id: int | None = None


@dataclass(frozen=True, slots=True)
class _TransactionContext:
    replay_transactions: list[Transaction]
    first_pair_date: dict[PositionKey, date_type]
    income_by_key: dict[PositionKey, list[Transaction]]


@dataclass(frozen=True, slots=True)
class _ReplayContext:
    replay_by_key: dict[PositionKey, FifoEngineResult]
    invalid_keys: set[PositionKey]
    failed_keys: set[PositionKey]


@dataclass(frozen=True, slots=True)
class _ConversionContext:
    wac_by_key: dict[PositionKey, Decimal]
    income_by_transaction: dict[int, Decimal]
    provenance_by_key: dict[PositionKey, list[YieldOnCostFxProvenance]]
    missing_by_key: dict[PositionKey, tuple[str | None, date_type]]
    missing_pairs_by_key: dict[PositionKey, list[WACMissingPairInfo]]


async def compute_yield_on_cost_dependency_identity(
    db: AsyncSession,
    *,
    user_id: int,
    scope_transactions: Sequence[Transaction],
    as_of_date: date_type,
) -> str:
    """Fingerprint the cross-broker ledger inputs used only by YOC replay."""
    asset_ids = {transaction.asset_id for transaction in scope_transactions if transaction.asset_id is not None}
    if not asset_ids:
        return "no_yoc"

    visible_stmt = select(BrokerUserAccess.broker_id).where(BrokerUserAccess.user_id == user_id)
    visible_broker_ids = set((await db.execute(visible_stmt)).scalars().all())
    if not visible_broker_ids:
        return "no_yoc"

    tx_stmt = select(Transaction).where(Transaction.asset_id.in_(asset_ids)).where(Transaction.broker_id.in_(visible_broker_ids)).where(Transaction.date <= as_of_date).order_by(Transaction.date, Transaction.id)
    historical_transactions = list((await db.execute(tx_stmt)).scalars().all())
    replay_transactions = await _include_external_transfer_legs(db, historical_transactions, asset_ids)
    split_records = await _load_split_records(db, replay_transactions)
    replay_broker_ids = {transaction.broker_id for transaction in replay_transactions}
    shorting_stmt = select(Broker.id, Broker.allow_asset_shorting).where(Broker.id.in_(replay_broker_ids)).order_by(Broker.id)
    shorting_rows = (await db.execute(shorting_stmt)).all() if replay_broker_ids else []

    payload = {
        "replay_brokers": sorted(replay_broker_ids),
        "transactions": [
            (
                transaction.id,
                transaction.broker_id,
                transaction.asset_id,
                getattr(transaction.type, "value", transaction.type),
                transaction.date.isoformat(),
                str(transaction.quantity),
                str(transaction.amount),
                transaction.currency,
                str(transaction.cost_basis_override) if transaction.cost_basis_override is not None else None,
                transaction.cost_basis_currency,
                transaction.related_transaction_id,
                transaction.asset_event_id,
                transaction.updated_at.isoformat(),
            )
            for transaction in replay_transactions
        ],
        "broker_shorting": [(broker_id, allow_shorting) for broker_id, allow_shorting in shorting_rows],
        "splits": [
            (
                record.transaction_id,
                record.event_id,
                record.transaction_asset_id,
                record.event_asset_id,
                record.broker_id,
                record.transaction_date.isoformat(),
                record.event_date.isoformat(),
                str(record.ratio),
            )
            for record in split_records
        ],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


async def calculate_yield_on_cost_for_positions(
    db: AsyncSession,
    *,
    user_id: int,
    positions: Sequence[YieldOnCostPositionInput],
    target_currency: str,
    as_of_date: date_type,
) -> dict[PositionKey, YieldOnCostPositionCalculation]:
    """Calculate transaction-ledger YOC for every supplied open position."""
    if not positions:
        return {}

    target_currency = Currency.validate_code(target_currency)
    position_by_key = {(position.asset_id, position.broker_id): position for position in positions}
    window_start = as_of_date - timedelta(days=364)
    transaction_context = await _load_transaction_context(
        db,
        user_id=user_id,
        position_keys=set(position_by_key),
        asset_ids={position.asset_id for position in positions},
        selected_broker_ids={position.broker_id for position in positions},
        window_start=window_start,
        as_of_date=as_of_date,
    )
    replay_context = await _build_replay_context(
        db,
        transaction_context,
        position_keys=set(position_by_key),
    )
    conversion_context = await _resolve_conversion_context(
        db,
        position_by_key=position_by_key,
        income_by_key=transaction_context.income_by_key,
        target_currency=target_currency,
        as_of_date=as_of_date,
    )
    return {
        key: _calculate_position(
            key=key,
            position=position_by_key[key],
            transaction_context=transaction_context,
            replay_context=replay_context,
            conversion_context=conversion_context,
            target_currency=target_currency,
            window_start=window_start,
            as_of_date=as_of_date,
        )
        for key in sorted(position_by_key)
    }


async def _load_transaction_context(
    db: AsyncSession,
    *,
    user_id: int,
    position_keys: set[PositionKey],
    asset_ids: set[int],
    selected_broker_ids: set[int],
    window_start: date_type,
    as_of_date: date_type,
) -> _TransactionContext:
    visible_stmt = select(BrokerUserAccess.broker_id).where(BrokerUserAccess.user_id == user_id)
    visible_broker_ids = set((await db.execute(visible_stmt)).scalars().all()) | selected_broker_ids
    tx_stmt = select(Transaction).where(Transaction.asset_id.in_(asset_ids)).where(Transaction.broker_id.in_(visible_broker_ids)).where(Transaction.date <= as_of_date).order_by(Transaction.date, Transaction.id)
    historical_transactions = list((await db.execute(tx_stmt)).scalars().all())
    replay_transactions = await _include_external_transfer_legs(db, historical_transactions, asset_ids)

    first_pair_date: dict[PositionKey, date_type] = {}
    income_by_key: dict[PositionKey, list[Transaction]] = defaultdict(list)
    for transaction in historical_transactions:
        if transaction.asset_id is None:
            continue
        key = (transaction.asset_id, transaction.broker_id)
        if key not in position_keys:
            continue
        first_pair_date.setdefault(key, transaction.date)
        if transaction.type in _INCOME_TYPES and window_start <= transaction.date <= as_of_date:
            income_by_key[key].append(transaction)
    return _TransactionContext(
        replay_transactions=replay_transactions,
        first_pair_date=first_pair_date,
        income_by_key=dict(income_by_key),
    )


async def _include_external_transfer_legs(
    db: AsyncSession,
    historical_transactions: Sequence[Transaction],
    asset_ids: set[int],
) -> list[Transaction]:
    replay_transactions = list(historical_transactions)
    replay_ids = {transaction.id for transaction in replay_transactions if transaction.id is not None}
    external_pair_ids = {transaction.related_transaction_id for transaction in replay_transactions if transaction.type == TransactionType.TRANSFER and transaction.quantity != 0 and transaction.related_transaction_id is not None and transaction.related_transaction_id not in replay_ids}
    if external_pair_ids:
        paired_stmt = select(Transaction).where(Transaction.id.in_(external_pair_ids)).where(Transaction.asset_id.in_(asset_ids))
        replay_transactions.extend((await db.execute(paired_stmt)).scalars().all())
    return sorted(replay_transactions, key=lambda transaction: (transaction.date, transaction.id or 0))


async def _build_replay_context(
    db: AsyncSession,
    transaction_context: _TransactionContext,
    *,
    position_keys: set[PositionKey],
) -> _ReplayContext:
    if not transaction_context.income_by_key:
        return _ReplayContext(replay_by_key={}, invalid_keys=set(), failed_keys=set())

    quantitative_transactions = [transaction for transaction in transaction_context.replay_transactions if transaction.asset_id is not None and transaction.quantity is not None and transaction.quantity != 0]
    split_records = await _load_split_records(db, transaction_context.replay_transactions)
    split_ratios_by_asset, split_event_ids_by_asset, invalid_brokers_by_asset = _index_split_records(split_records)
    broker_ids = {transaction.broker_id for transaction in quantitative_transactions}
    shorting_stmt = select(Broker.id, Broker.allow_asset_shorting).where(Broker.id.in_(broker_ids))
    broker_shorting = dict((await db.execute(shorting_stmt)).all()) if broker_ids else {}
    transactions_by_asset: dict[int, list[Transaction]] = defaultdict(list)
    for transaction in quantitative_transactions:
        if transaction.asset_id is not None:
            transactions_by_asset[transaction.asset_id].append(transaction)

    replay_by_key: dict[PositionKey, FifoEngineResult] = {}
    invalid_keys: set[PositionKey] = set()
    failed_keys: set[PositionKey] = set()
    income_keys = set(transaction_context.income_by_key)
    income_assets = {asset_id for asset_id, _broker_id in income_keys}
    for asset_id in sorted(income_assets):
        transactions = transactions_by_asset.get(asset_id)
        if not transactions:
            failed_keys.update(key for key in income_keys if key[0] == asset_id)
            continue
        for component in _broker_components(transactions):
            component_keys = {key for key in income_keys if key[0] == asset_id and key[1] in component}
            if not component_keys:
                continue
            if component & invalid_brokers_by_asset.get(asset_id, set()):
                invalid_keys.update(component_keys)
                continue
            component_transactions = [transaction for transaction in transactions if transaction.broker_id in component]
            component_tx_ids = {transaction.id for transaction in component_transactions if transaction.id is not None}
            replay = _run_component_replay(
                asset_id=asset_id,
                component=component,
                transactions=component_transactions,
                component_tx_ids=component_tx_ids,
                broker_shorting=broker_shorting,
                split_ratios_by_asset=split_ratios_by_asset,
                split_event_ids_by_asset=split_event_ids_by_asset,
            )
            failure = _component_replay_failure(replay)
            if failure is not None:
                {"failed": failed_keys, "invalid": invalid_keys}[failure].update(component_keys)
                continue
            assert replay is not None
            replay_by_key.update(dict.fromkeys(component_keys, replay))
    return _ReplayContext(
        replay_by_key=replay_by_key,
        invalid_keys=invalid_keys,
        failed_keys=failed_keys,
    )


def _run_component_replay(
    *,
    asset_id: int,
    component: set[int],
    transactions: Sequence[Transaction],
    component_tx_ids: set[int],
    broker_shorting: dict[int, bool],
    split_ratios_by_asset: dict[int, dict[int, Decimal]],
    split_event_ids_by_asset: dict[int, dict[int, int]],
) -> FifoEngineResult | None:
    try:
        return run_fifo_lot_engine(
            transactions=transactions,
            broker_shorting=broker_shorting,
            split_ratios_by_tx_id={transaction_id: ratio for transaction_id, ratio in split_ratios_by_asset.get(asset_id, {}).items() if transaction_id in component_tx_ids},
            split_event_ids_by_tx_id={transaction_id: event_id for transaction_id, event_id in split_event_ids_by_asset.get(asset_id, {}).items() if transaction_id in component_tx_ids},
        )
    except (AssertionError, KeyError, ValueError, ZeroDivisionError) as exc:
        logger.warning("yield_on_cost_replay_failed", asset_id=asset_id, broker_ids=sorted(component), error=str(exc))
        return None


def _component_replay_failure(
    replay: FifoEngineResult | None,
) -> Literal["failed", "invalid"] | None:
    if replay is None or replay.analysis_status == "FAILED":
        return "failed"
    if _has_incoherent_split_quantity(replay):
        return "invalid"
    return None


def _has_incoherent_split_quantity(replay: FifoEngineResult) -> bool:
    for event in replay.classified_events:
        if event.kind != "SPLIT":
            continue
        if event.quantity is None or event.ratio is None:
            return True
        snapshot = replay.split_quantities_by_transaction_id.get(event.transaction_id)
        if snapshot is None:
            return True

        ratio_delta = event.ratio - Decimal("1")
        candidates = (
            snapshot.scoped_quantity * ratio_delta,
            snapshot.broker_custody_quantity * ratio_delta,
        )
        if all(abs(event.quantity - candidate) > _SPLIT_QUANTITY_ABS_TOLERANCE + max(abs(event.quantity), abs(candidate)) * _SPLIT_QUANTITY_REL_TOLERANCE for candidate in candidates):
            return True
    return False


def _index_split_records(
    split_records: Sequence[_SplitRecord],
) -> tuple[dict[int, dict[int, Decimal]], dict[int, dict[int, int]], dict[int, set[int]]]:
    ratios_by_asset: dict[int, dict[int, Decimal]] = defaultdict(dict)
    event_ids_by_asset: dict[int, dict[int, int]] = defaultdict(dict)
    invalid_brokers_by_asset: dict[int, set[int]] = defaultdict(set)
    seen_events: set[tuple[int, int]] = set()
    for record in split_records:
        identity = (record.event_id, record.broker_id)
        invalid = (
            identity in seen_events
            or record.transaction_type != TransactionType.ADJUSTMENT
            or record.transaction_quantity is None
            or record.transaction_quantity == 0
            or record.transaction_asset_id != record.event_asset_id
            or record.transaction_date != record.event_date
            or record.ratio is None
            or not record.ratio.is_finite()
            or record.ratio <= 0
        )
        seen_events.add(identity)
        if invalid:
            invalid_brokers_by_asset[record.transaction_asset_id].add(record.broker_id)
            continue
        ratios_by_asset[record.transaction_asset_id][record.transaction_id] = record.ratio
        event_ids_by_asset[record.transaction_asset_id][record.transaction_id] = record.event_id
    return dict(ratios_by_asset), dict(event_ids_by_asset), dict(invalid_brokers_by_asset)


def _broker_components(transactions: Sequence[Transaction]) -> list[set[int]]:
    graph: dict[int, set[int]] = defaultdict(set)
    by_id = {transaction.id: transaction for transaction in transactions if transaction.id is not None}
    for transaction in transactions:
        graph.setdefault(transaction.broker_id, set())
        if transaction.type != TransactionType.TRANSFER or transaction.related_transaction_id is None:
            continue
        pair = by_id.get(transaction.related_transaction_id)
        if pair is None or pair.asset_id != transaction.asset_id:
            continue
        graph[transaction.broker_id].add(pair.broker_id)
        graph[pair.broker_id].add(transaction.broker_id)

    components: list[set[int]] = []
    remaining = set(graph)
    while remaining:
        frontier = [min(remaining)]
        component: set[int] = set()
        while frontier:
            broker_id = frontier.pop()
            if broker_id in component:
                continue
            component.add(broker_id)
            frontier.extend(sorted(graph[broker_id] - component, reverse=True))
        components.append(component)
        remaining -= component
    return components


async def _resolve_conversion_context(
    db: AsyncSession,
    *,
    position_by_key: dict[PositionKey, YieldOnCostPositionInput],
    income_by_key: dict[PositionKey, list[Transaction]],
    target_currency: str,
    as_of_date: date_type,
) -> _ConversionContext:
    specs: list[_ConversionSpec] = []
    inputs: list[tuple[Currency, str, date_type]] = []
    missing_by_key: dict[PositionKey, tuple[str | None, date_type]] = {}
    for key, position in position_by_key.items():
        if position.wac_per_unit is None or not position.wac_currency:
            continue
        _append_conversion(
            specs,
            inputs,
            position_key=key,
            purpose="wac",
            requested_date=as_of_date,
            from_currency=position.wac_currency,
            target_currency=target_currency,
            amount=position.wac_per_unit,
        )
    for key in sorted(income_by_key):
        for transaction in income_by_key[key]:
            if transaction.id is None or not transaction.currency:
                missing_by_key.setdefault(key, (None, transaction.date))
                continue
            _append_conversion(
                specs,
                inputs,
                position_key=key,
                purpose="income",
                requested_date=transaction.date,
                from_currency=transaction.currency,
                target_currency=target_currency,
                amount=transaction.amount,
                transaction_id=transaction.id,
            )

    results, _errors = await convert_bulk(db, inputs, raise_on_error=False)
    return _index_conversions(specs, results, target_currency, missing_by_key)


def _index_conversions(
    specs: Sequence[_ConversionSpec],
    results: Sequence[tuple[Currency, date_type, bool] | None],
    target_currency: str,
    missing_by_key: dict[PositionKey, tuple[str | None, date_type]],
) -> _ConversionContext:
    wac_by_key: dict[PositionKey, Decimal] = {}
    income_by_transaction: dict[int, Decimal] = {}
    provenance_by_key: dict[PositionKey, list[YieldOnCostFxProvenance]] = defaultdict(list)
    missing_pairs_by_key: dict[PositionKey, list[WACMissingPairInfo]] = defaultdict(list)
    seen_provenance: dict[PositionKey, set[tuple[str, date_type, date_type, str, str]]] = defaultdict(set)
    for spec, conversion in zip(specs, results, strict=True):
        if conversion is None:
            pair = f"{spec.from_currency}/{target_currency}"
            missing_by_key.setdefault(spec.position_key, (pair, spec.requested_date))
            missing_pairs_by_key[spec.position_key].append(WACMissingPairInfo(pair=pair, dates=[spec.requested_date]))
            continue
        converted, rate_date, _backfilled = conversion
        if spec.purpose == "wac":
            wac_by_key[spec.position_key] = converted.amount
        elif spec.transaction_id is not None:
            income_by_transaction[spec.transaction_id] = converted.amount
        if spec.from_currency != target_currency:
            _append_fx_provenance(
                provenance_by_key,
                seen_provenance,
                spec=spec,
                target_currency=target_currency,
                rate_date=rate_date,
            )
    return _ConversionContext(
        wac_by_key=wac_by_key,
        income_by_transaction=income_by_transaction,
        provenance_by_key=dict(provenance_by_key),
        missing_by_key=missing_by_key,
        missing_pairs_by_key=dict(missing_pairs_by_key),
    )


def _append_fx_provenance(
    provenance_by_key: dict[PositionKey, list[YieldOnCostFxProvenance]],
    seen_provenance: dict[PositionKey, set[tuple[str, date_type, date_type, str, str]]],
    *,
    spec: _ConversionSpec,
    target_currency: str,
    rate_date: date_type,
) -> None:
    identity = (spec.purpose, spec.requested_date, rate_date, spec.from_currency, target_currency)
    if identity in seen_provenance[spec.position_key]:
        return
    seen_provenance[spec.position_key].add(identity)
    provenance_by_key[spec.position_key].append(
        YieldOnCostFxProvenance(
            purpose=spec.purpose,
            requested_date=spec.requested_date,
            rate_date=rate_date,
            from_currency=spec.from_currency,
            to_currency=target_currency,
            days_back=(spec.requested_date - rate_date).days,
        )
    )


def _calculate_position(
    *,
    key: PositionKey,
    position: YieldOnCostPositionInput,
    transaction_context: _TransactionContext,
    replay_context: _ReplayContext,
    conversion_context: _ConversionContext,
    target_currency: str,
    window_start: date_type,
    as_of_date: date_type,
) -> YieldOnCostPositionCalculation:
    income_transactions = transaction_context.income_by_key.get(key, [])
    provenance = YieldOnCostProvenance(
        window_start=window_start,
        window_end=as_of_date,
        first_pair_transaction_date=transaction_context.first_pair_date.get(key),
        gross_income_transaction_count=len(income_transactions),
        fx=conversion_context.provenance_by_key.get(key, []),
    )
    base_failure = _base_failure_reason(key, position, conversion_context)
    if base_failure is not None:
        reason, issue_pair, issue_date = base_failure
        return _unavailable(
            provenance.model_copy(update={"issue_pair": issue_pair, "issue_date": issue_date}),
            reason,
            conversion_context.wac_by_key.get(key),
            conversion_context.missing_pairs_by_key.get(key, []),
        )
    converted_wac = conversion_context.wac_by_key[key]
    if converted_wac <= 0:
        return _unavailable(
            provenance,
            YieldOnCostUnavailableReason.NON_POSITIVE_WAC,
            converted_wac,
        )
    if not income_transactions:
        return _calculate_no_income(
            provenance,
            converted_wac,
            target_currency,
            window_start,
        )

    if key in replay_context.invalid_keys:
        return _unavailable(provenance, YieldOnCostUnavailableReason.INVALID_SPLIT, converted_wac)
    if key in replay_context.failed_keys or key not in replay_context.replay_by_key:
        return _unavailable(provenance, YieldOnCostUnavailableReason.REPLAY_INCONSISTENT, converted_wac)
    return _calculate_income_position(
        key=key,
        income_transactions=income_transactions,
        replay=replay_context.replay_by_key[key],
        conversion_context=conversion_context,
        provenance=provenance,
        converted_wac=converted_wac,
        target_currency=target_currency,
        as_of_date=as_of_date,
    )


def _base_failure_reason(
    key: PositionKey,
    position: YieldOnCostPositionInput,
    conversion_context: _ConversionContext,
) -> tuple[YieldOnCostUnavailableReason, str | None, date_type | None] | None:
    if position.wac_per_unit is None or not position.wac_currency:
        return YieldOnCostUnavailableReason.MISSING_WAC, None, None
    if position.wac_per_unit <= 0:
        return YieldOnCostUnavailableReason.NON_POSITIVE_WAC, None, None
    if key in conversion_context.missing_by_key or key not in conversion_context.wac_by_key:
        issue_pair, issue_date = conversion_context.missing_by_key.get(key, (None, None))
        return YieldOnCostUnavailableReason.MISSING_FX, issue_pair, issue_date
    return None


def _calculate_no_income(
    provenance: YieldOnCostProvenance,
    converted_wac: Decimal,
    target_currency: str,
    window_start: date_type,
) -> YieldOnCostPositionCalculation:
    if provenance.first_pair_transaction_date is None or provenance.first_pair_transaction_date > window_start:
        return _unavailable(
            provenance,
            YieldOnCostUnavailableReason.INSUFFICIENT_HISTORY,
            converted_wac,
        )
    return YieldOnCostPositionCalculation(
        result=YieldOnCostResult(
            status=YieldOnCostStatus.NO_INCOME,
            value=Decimal("0"),
            provenance=provenance.model_copy(update={"gross_income_per_unit": Currency(code=target_currency, amount=Decimal("0"))}),
        ),
        wac_per_unit=converted_wac,
    )


def _calculate_income_position(
    *,
    key: PositionKey,
    income_transactions: Sequence[Transaction],
    replay: FifoEngineResult,
    conversion_context: _ConversionContext,
    provenance: YieldOnCostProvenance,
    converted_wac: Decimal,
    target_currency: str,
    as_of_date: date_type,
) -> YieldOnCostPositionCalculation:
    asset_id, broker_id = key
    fragments_by_lot: dict[int, list[FragmentInterval]] = defaultdict(list)
    for fragment in replay.fragment_intervals:
        fragments_by_lot[fragment.lot_id].append(fragment)
    split_events = [event for event in replay.classified_events if event.kind == "SPLIT" and event.date <= as_of_date]

    gross_income_per_unit = Decimal("0")
    for transaction in income_transactions:
        eligible_quantity = _eligible_position_quantity(
            replay,
            fragments_by_lot,
            broker_id,
            transaction.date - timedelta(days=1),
        )
        if eligible_quantity <= 0:
            return _unavailable(
                provenance.model_copy(update={"issue_date": transaction.date}),
                YieldOnCostUnavailableReason.INCOME_WITHOUT_ELIGIBLE_QUANTITY,
                converted_wac,
            )
        split_ratio = _current_unit_split_ratio(
            split_events,
            income_date=transaction.date,
            broker_id=broker_id,
        )
        if split_ratio is None:
            return _unavailable(provenance, YieldOnCostUnavailableReason.INVALID_SPLIT, converted_wac)
        if transaction.id is None or transaction.id not in conversion_context.income_by_transaction:
            issue_pair, issue_date = conversion_context.missing_by_key.get(key, (None, transaction.date))
            return _unavailable(
                provenance.model_copy(update={"issue_pair": issue_pair, "issue_date": issue_date}),
                YieldOnCostUnavailableReason.MISSING_FX,
                converted_wac,
                conversion_context.missing_pairs_by_key.get(key, []),
            )
        gross_income_per_unit += conversion_context.income_by_transaction[transaction.id] / eligible_quantity / split_ratio

    final_provenance = provenance.model_copy(
        update={
            "gross_income_per_unit": Currency(code=target_currency, amount=gross_income_per_unit),
            "net_zero": gross_income_per_unit == 0,
        }
    )
    return YieldOnCostPositionCalculation(
        result=YieldOnCostResult(
            status=YieldOnCostStatus.AVAILABLE,
            value=gross_income_per_unit / converted_wac,
            provenance=final_provenance,
        ),
        wac_per_unit=converted_wac,
        missing_fx_pairs=tuple(conversion_context.missing_pairs_by_key.get(key, [])),
    )


def _eligible_position_quantity(
    replay: FifoEngineResult,
    fragments_by_lot: dict[int, list[FragmentInterval]],
    broker_id: int,
    cutoff: date_type,
) -> Decimal:
    return sum(
        (
            eligible_income_quantity(
                fragments_by_lot.get(lot.lot_id, ()),
                broker_id,
                cutoff,
            )
            for lot in replay.lots
            if lot.direction == "LONG"
        ),
        Decimal("0"),
    )


def _current_unit_split_ratio(
    split_events: Sequence[FifoEvent],
    *,
    income_date: date_type,
    broker_id: int,
) -> Decimal | None:
    ratio = Decimal("1")
    grouped: dict[tuple[str, int], list[FifoEvent]] = defaultdict(list)
    for event in split_events:
        if event.date >= income_date:
            identity = ("event", event.asset_event_id) if event.asset_event_id is not None else ("transaction", event.transaction_id)
            grouped[identity].append(event)

    for events in grouped.values():
        ratios = {event.ratio for event in events}
        own_events = [event for event in events if event.broker_id == broker_id]
        if len(ratios) != 1 or None in ratios or not own_events:
            return None
        event_ratio = ratios.pop()
        if not event_ratio.is_finite() or event_ratio <= 0:
            return None
        ratio *= event_ratio
    return ratio


def _append_conversion(
    specs: list[_ConversionSpec],
    inputs: list[tuple[Currency, str, date_type]],
    *,
    position_key: PositionKey,
    purpose: Literal["income", "wac"],
    requested_date: date_type,
    from_currency: str,
    target_currency: str,
    amount: Decimal,
    transaction_id: int | None = None,
) -> None:
    normalized_currency = Currency.validate_code(from_currency)
    specs.append(
        _ConversionSpec(
            position_key=position_key,
            purpose=purpose,
            requested_date=requested_date,
            from_currency=normalized_currency,
            transaction_id=transaction_id,
        )
    )
    inputs.append(
        (
            Currency(code=normalized_currency, amount=amount),
            target_currency,
            requested_date,
        )
    )


def _unavailable(
    provenance: YieldOnCostProvenance,
    reason: YieldOnCostUnavailableReason,
    wac_per_unit: Decimal | None,
    missing_fx_pairs: Sequence[WACMissingPairInfo] = (),
) -> YieldOnCostPositionCalculation:
    return YieldOnCostPositionCalculation(
        result=YieldOnCostResult(
            status=YieldOnCostStatus.UNAVAILABLE,
            reason=reason,
            provenance=provenance,
        ),
        wac_per_unit=wac_per_unit,
        missing_fx_pairs=tuple(missing_fx_pairs),
    )


async def _load_split_records(
    db: AsyncSession,
    transactions: Sequence[Transaction],
) -> list[_SplitRecord]:
    linked_ids = [transaction.id for transaction in transactions if transaction.id is not None and transaction.asset_event_id is not None]
    if not linked_ids:
        return []
    stmt = (
        select(
            Transaction.id,
            AssetEvent.id,
            Transaction.asset_id,
            AssetEvent.asset_id,
            Transaction.broker_id,
            Transaction.type,
            Transaction.quantity,
            Transaction.date,
            AssetEvent.date,
            AssetEvent.value,
        )
        .join(AssetEvent, Transaction.asset_event_id == AssetEvent.id)
        .where(Transaction.id.in_(linked_ids))
        .where(AssetEvent.type == AssetEventType.SPLIT)
        .order_by(Transaction.id)
    )
    return [
        _SplitRecord(
            transaction_id=transaction_id,
            event_id=event_id,
            transaction_asset_id=transaction_asset_id,
            event_asset_id=event_asset_id,
            broker_id=broker_id,
            transaction_type=transaction_type,
            transaction_quantity=transaction_quantity,
            transaction_date=transaction_date,
            event_date=event_date,
            ratio=ratio,
        )
        for (
            transaction_id,
            event_id,
            transaction_asset_id,
            event_asset_id,
            broker_id,
            transaction_type,
            transaction_quantity,
            transaction_date,
            event_date,
            ratio,
        ) in (await db.execute(stmt)).all()
        if transaction_asset_id is not None
    ]
