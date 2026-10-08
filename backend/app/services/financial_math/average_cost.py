"""Average cost of positions — the single implementation used across LibreFolio.

:func:`compute_average_costs` folds the movements that change a position's quantity into
a running pool and returns, for every position, the historical cost in the report
currency T and in the asset currency A, the pool state after each movement, and every
conversion it could not make.

The problem is described by plain data only:

* :class:`CostMovement` — an acquisition with the amount actually paid (or with no known
  cost), a reduction, or a split, in the order the caller recorded them;
* the currencies: T for the report, A for each position.

Each acquisition is converted at its own date through the FX service, with one batched
``convert_bulk`` per call: an amount already in T is taken as it is, so a purchase paid
in the report currency never needs a rate. The cost in A goes through T with the same
day's rate (``c_A = c_T × r(T→A, d)``), so the exchange effect is zero on the day of the
purchase. A missing rate never becomes a zero: the quantity is still added, the cost is
not, the pool is marked incomplete and the pair is reported with every date it was
needed on.

Pool rules:

* same-day movements: additions first, then reductions; within each group the caller's
  order is kept;
* a reduction removes ``C × q / Q`` on both legs (the whole cost when it empties the pool),
  so the cost is conserved exactly; quantity beyond the pool is clamped and reported;
* a split changes the quantity and keeps the cost;
* an emptied pool starts again from zero and complete.
"""

from __future__ import annotations

import bisect
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date as date_type
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from backend.app.schemas.common import Currency
from backend.app.services.fx import convert_bulk

_ZERO = Decimal("0")
_ONE = Decimal("1")

CostLeg = Literal["report", "asset"]


class CostMovementKind(StrEnum):
    """What a movement does to the pool."""

    ACQUISITION = "acquisition"
    REDUCTION = "reduction"
    SPLIT = "split"


class CostEffect(StrEnum):
    """How a movement changed the pool."""

    ADD = "add"
    ADD_ZERO_COST = "add_zero_cost"
    ADD_UNKNOWN_COST = "add_unknown_cost"
    ADD_MISSING_FX = "add_missing_fx"
    REDUCE = "reduce"
    SPLIT_RESCALE = "split_rescale"


@dataclass(frozen=True, slots=True)
class CostMovement:
    """One movement of a position's quantity.

    ``cost_amount`` is the total actually paid for an acquisition, in ``cost_currency``;
    ``None`` means the cost is not known, ``0`` a free acquisition.
    """

    movement_id: int | None
    transaction_type: str
    date: date_type
    kind: CostMovementKind
    quantity: Decimal
    cost_amount: Decimal | None = None
    cost_currency: str | None = None

    def __post_init__(self) -> None:
        if self.quantity == 0:
            raise ValueError("a cost movement must move quantity")
        if self.kind == CostMovementKind.ACQUISITION and self.quantity < 0:
            raise ValueError("an acquisition adds quantity")
        if self.kind == CostMovementKind.REDUCTION and self.quantity > 0:
            raise ValueError("a reduction removes quantity")
        if self.kind != CostMovementKind.ACQUISITION and self.cost_amount is not None:
            raise ValueError("only an acquisition carries a cost")
        if self.cost_amount is not None and not self.cost_currency:
            raise ValueError("a cost needs its currency")


@dataclass(frozen=True, slots=True)
class CostPosition:
    """The movements of one position, identified by a caller-chosen key."""

    key: Hashable
    asset_currency: str
    movements: tuple[CostMovement, ...]


@dataclass(frozen=True, slots=True)
class CostConversion:
    """Provenance of an acquisition converted into the report currency."""

    original_amount: Decimal
    original_currency: str
    converted_amount: Decimal
    rate: Decimal
    rate_date: date_type
    days_back: int


@dataclass(frozen=True, slots=True)
class MissingConversion:
    """A pair that could not be converted, with every date it was needed on."""

    pair: str
    dates: tuple[date_type, ...]
    leg: CostLeg


def _share_of(cost: Decimal, part: Decimal, whole: Decimal) -> Decimal:
    """``cost`` of ``whole`` units scaled to ``part`` units; exactly ``cost`` for the whole pool."""
    if whole <= 0:
        return _ZERO
    if part == whole:
        return cost
    return cost * part / whole


@dataclass(frozen=True, slots=True)
class CostStep:
    """The pool after one movement."""

    movement: CostMovement
    effect: CostEffect
    quantity: Decimal
    cost_report: Decimal
    cost_asset: Decimal | None
    cost_report_change: Decimal
    cost_asset_change: Decimal | None
    report_complete: bool
    asset_complete: bool
    conversion: CostConversion | None = None

    @property
    def unit_cost_report(self) -> Decimal:
        return self.cost_report / self.quantity if self.quantity > 0 else _ZERO

    @property
    def unit_cost_asset(self) -> Decimal | None:
        if self.cost_asset is None:
            return None
        return self.cost_asset / self.quantity if self.quantity > 0 else _ZERO

    def cost_report_for(self, quantity: Decimal) -> Decimal:
        """Report-currency cost of ``quantity`` units of this pool."""
        return _share_of(self.cost_report, quantity, self.quantity)

    def cost_asset_for(self, quantity: Decimal) -> Decimal | None:
        """Asset-currency cost of ``quantity`` units of this pool; None when the leg is off."""
        if self.cost_asset is None:
            return None
        return _share_of(self.cost_asset, quantity, self.quantity)


@dataclass(frozen=True, slots=True)
class AverageCost:
    """The average cost of one position: its timeline and what could not be computed."""

    key: Hashable
    report_currency: str
    asset_currency: str
    asset_leg: bool
    steps: tuple[CostStep, ...] = ()
    missing: tuple[MissingConversion, ...] = ()
    unknown_cost_movement_ids: tuple[int | None, ...] = ()
    oversold_movement_ids: tuple[int | None, ...] = ()
    _step_dates: tuple[date_type, ...] = field(init=False, repr=False, compare=False)
    _steps_by_id: dict[int, CostStep] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_step_dates", tuple(step.movement.date for step in self.steps))
        object.__setattr__(self, "_steps_by_id", {step.movement.movement_id: step for step in self.steps if step.movement.movement_id is not None})

    @property
    def quantity(self) -> Decimal:
        return self.steps[-1].quantity if self.steps else _ZERO

    @property
    def cost_report(self) -> Decimal:
        return self.steps[-1].cost_report if self.steps else _ZERO

    @property
    def cost_asset(self) -> Decimal | None:
        if self.steps:
            return self.steps[-1].cost_asset
        return _ZERO if self.asset_leg else None

    @property
    def report_complete(self) -> bool:
        return self.steps[-1].report_complete if self.steps else True

    @property
    def asset_complete(self) -> bool:
        return self.steps[-1].asset_complete if self.steps else self.asset_leg

    @property
    def unit_cost_report(self) -> Decimal:
        return self.steps[-1].unit_cost_report if self.steps else _ZERO

    @property
    def unit_cost_asset(self) -> Decimal | None:
        if self.steps:
            return self.steps[-1].unit_cost_asset
        return _ZERO if self.asset_leg else None

    @property
    def has_missing_report_fx(self) -> bool:
        return any(item.leg == "report" for item in self.missing)

    def state_at(self, day: date_type) -> CostStep | None:
        """The pool after the last movement dated on or before ``day``; None before the first one."""
        index = bisect.bisect_right(self._step_dates, day)
        return self.steps[index - 1] if index else None

    def step_for(self, movement_id: int) -> CostStep | None:
        return self._steps_by_id.get(movement_id)


@dataclass(frozen=True, slots=True)
class _ConversionRequest:
    source_currency: str
    target_currency: str
    date: date_type
    amount: Decimal


@dataclass(frozen=True, slots=True)
class _ResolvedConversion:
    amount: Decimal
    rate_date: date_type


def cost_movement_from_transaction(tx: Any, *, asset_currency: str, split_linked: bool, share: Decimal = _ONE) -> CostMovement | None:
    """The movement a transaction makes on its position, or None when it moves no quantity.

    ``share`` scales quantity and cost (the owner's share of a broker). A BUY costs the cash
    paid; another acquisition costs its ``cost_basis_override`` per unit, or nothing known.
    """
    raw_quantity = tx.quantity
    if raw_quantity is None or raw_quantity == 0:
        return None
    quantity = raw_quantity * share
    if quantity == 0:
        return None
    transaction_type = str(getattr(tx.type, "value", tx.type))
    if split_linked:
        return CostMovement(movement_id=tx.id, transaction_type=transaction_type, date=tx.date, kind=CostMovementKind.SPLIT, quantity=quantity)
    if raw_quantity < 0:
        return CostMovement(movement_id=tx.id, transaction_type=transaction_type, date=tx.date, kind=CostMovementKind.REDUCTION, quantity=quantity)
    if transaction_type == "BUY":
        paid = abs(tx.amount) * share if tx.amount else _ZERO
        return CostMovement(
            movement_id=tx.id,
            transaction_type=transaction_type,
            date=tx.date,
            kind=CostMovementKind.ACQUISITION,
            quantity=quantity,
            cost_amount=paid,
            cost_currency=tx.currency or asset_currency,
        )
    if tx.cost_basis_override is not None:
        return CostMovement(
            movement_id=tx.id,
            transaction_type=transaction_type,
            date=tx.date,
            kind=CostMovementKind.ACQUISITION,
            quantity=quantity,
            cost_amount=tx.cost_basis_override * quantity,
            cost_currency=tx.cost_basis_currency or asset_currency,
        )
    return CostMovement(movement_id=tx.id, transaction_type=transaction_type, date=tx.date, kind=CostMovementKind.ACQUISITION, quantity=quantity)


def determine_target_currency(movements: Sequence[CostMovement], asset_currency: str) -> str:
    """Currency of the most recent movement adding quantity — deterministic; the asset currency otherwise.

    Among movements on the same latest date the first one in ``movements`` wins. A split or an
    acquisition with no known cost stands for the asset currency.
    """
    latest: CostMovement | None = None
    for movement in movements:
        if movement.quantity > 0 and (latest is None or movement.date > latest.date):
            latest = movement
    if latest is None or latest.kind != CostMovementKind.ACQUISITION or latest.cost_amount is None:
        return asset_currency
    return latest.cost_currency or asset_currency


async def compute_average_costs(
    session: Any,
    positions: Sequence[CostPosition],
    *,
    report_currency: str,
    asset_leg: bool = True,
) -> dict[Hashable, AverageCost]:
    """Average cost of every position, in the report currency and (with ``asset_leg``) in its asset currency.

    All the conversions of all the positions go to the FX service in one ``convert_bulk`` call,
    at each movement's date; none is made, and ``session`` is not used, when every amount is
    already in the currency it is needed in.
    """
    _check_unique_keys(positions)
    requests = _conversion_requests(positions, report_currency, asset_leg)
    resolved: dict[_ConversionRequest, _ResolvedConversion | None] = {}
    if requests:
        results, _errors = await convert_bulk(
            session,
            [(Currency(code=request.source_currency, amount=request.amount), request.target_currency, request.date) for request in requests],
            raise_on_error=False,
        )
        for index, request in enumerate(requests):
            result = results[index] if index < len(results) else None
            resolved[request] = None if result is None else _ResolvedConversion(amount=result[0].amount, rate_date=result[1])
    return _fold_average_costs(positions, report_currency=report_currency, asset_leg=asset_leg, resolved=resolved)


def _check_unique_keys(positions: Sequence[CostPosition]) -> None:
    seen: set[Hashable] = set()
    for position in positions:
        if position.key in seen:
            raise ValueError(f"duplicate cost position key: {position.key!r}")
        seen.add(position.key)


def _ordered(movements: Sequence[CostMovement]) -> list[CostMovement]:
    return sorted(movements, key=lambda movement: (movement.date, 0 if movement.quantity > 0 else 1))


def _conversion_requests(positions: Sequence[CostPosition], report_currency: str, asset_leg: bool) -> list[_ConversionRequest]:
    """Every conversion the fold needs, once each, in first-use order."""
    requests: dict[_ConversionRequest, None] = {}
    for position in positions:
        asset_currency = position.asset_currency
        for movement in position.movements:
            if movement.kind != CostMovementKind.ACQUISITION or not movement.cost_amount:
                continue
            paid_currency = movement.cost_currency or asset_currency
            if paid_currency != report_currency:
                requests.setdefault(_ConversionRequest(paid_currency, report_currency, movement.date, movement.cost_amount), None)
            if asset_leg and asset_currency != report_currency and paid_currency != asset_currency:
                requests.setdefault(_ConversionRequest(report_currency, asset_currency, movement.date, _ONE), None)
    return list(requests)


def _fold_average_costs(
    positions: Sequence[CostPosition],
    *,
    report_currency: str,
    asset_leg: bool,
    resolved: Mapping[_ConversionRequest, _ResolvedConversion | None],
) -> dict[Hashable, AverageCost]:
    """Pure fold of every position over already-resolved conversions; no I/O."""
    _check_unique_keys(positions)
    return {position.key: _fold_position(position, report_currency, asset_leg, resolved) for position in positions}


def _fold_position(  # noqa: C901 — one flat branch per movement kind and per currency case
    position: CostPosition,
    report_currency: str,
    asset_leg: bool,
    resolved: Mapping[_ConversionRequest, _ResolvedConversion | None],
) -> AverageCost:
    asset_currency = position.asset_currency
    quantity = _ZERO
    cost_report = _ZERO
    cost_asset = _ZERO
    report_complete = True
    asset_complete = True
    steps: list[CostStep] = []
    missing_dates: dict[tuple[str, CostLeg], set[date_type]] = {}
    unknown: list[int | None] = []
    oversold: list[int | None] = []

    for movement in _ordered(position.movements):
        conversion: CostConversion | None = None
        report_change = _ZERO
        asset_change = _ZERO

        if movement.kind == CostMovementKind.SPLIT:
            effect = CostEffect.SPLIT_RESCALE
            new_quantity = quantity + movement.quantity
            if new_quantity > 0:
                quantity = new_quantity
            else:
                quantity = cost_report = cost_asset = _ZERO
                report_complete = asset_complete = True

        elif movement.kind == CostMovementKind.REDUCTION:
            effect = CostEffect.REDUCE
            wanted = -movement.quantity
            if wanted > quantity:
                oversold.append(movement.movement_id)
            taken = min(wanted, quantity)
            if taken > 0:
                removed_report = _share_of(cost_report, taken, quantity)
                removed_asset = _share_of(cost_asset, taken, quantity)
                cost_report -= removed_report
                cost_asset -= removed_asset
                quantity -= taken
                report_change = -removed_report
                asset_change = -removed_asset
            if quantity == 0:
                cost_report = cost_asset = _ZERO
                report_complete = asset_complete = True

        else:
            quantity += movement.quantity
            if movement.cost_amount is None:
                effect = CostEffect.ADD_UNKNOWN_COST
                unknown.append(movement.movement_id)
                report_complete = asset_complete = False
            elif movement.cost_amount == 0:
                effect = CostEffect.ADD_ZERO_COST
            else:
                paid_currency = movement.cost_currency or asset_currency
                added_report: Decimal | None
                if paid_currency == report_currency:
                    added_report = movement.cost_amount
                else:
                    found = resolved.get(_ConversionRequest(paid_currency, report_currency, movement.date, movement.cost_amount))
                    if found is None:
                        added_report = None
                        missing_dates.setdefault((f"{paid_currency}/{report_currency}", "report"), set()).add(movement.date)
                    else:
                        added_report = found.amount
                        conversion = CostConversion(
                            original_amount=movement.cost_amount,
                            original_currency=paid_currency,
                            converted_amount=found.amount,
                            rate=found.amount / movement.cost_amount,
                            rate_date=found.rate_date,
                            days_back=max((movement.date - found.rate_date).days, 0),
                        )

                added_asset: Decimal | None = None
                if asset_leg:
                    if paid_currency == asset_currency:
                        added_asset = movement.cost_amount
                    elif asset_currency == report_currency:
                        added_asset = added_report
                    elif added_report is not None:
                        unit_rate = resolved.get(_ConversionRequest(report_currency, asset_currency, movement.date, _ONE))
                        if unit_rate is None:
                            missing_dates.setdefault((f"{asset_currency}/{report_currency}", "asset"), set()).add(movement.date)
                        else:
                            added_asset = added_report * unit_rate.amount

                if added_report is None:
                    effect = CostEffect.ADD_MISSING_FX
                    report_complete = False
                else:
                    effect = CostEffect.ADD
                    cost_report += added_report
                    report_change = added_report
                if asset_leg:
                    if added_asset is None:
                        asset_complete = False
                    else:
                        cost_asset += added_asset
                        asset_change = added_asset

        steps.append(
            CostStep(
                movement=movement,
                effect=effect,
                quantity=quantity,
                cost_report=cost_report,
                cost_asset=cost_asset if asset_leg else None,
                cost_report_change=report_change,
                cost_asset_change=asset_change if asset_leg else None,
                report_complete=report_complete,
                asset_complete=asset_complete and asset_leg,
                conversion=conversion,
            )
        )

    return AverageCost(
        key=position.key,
        report_currency=report_currency,
        asset_currency=asset_currency,
        asset_leg=asset_leg,
        steps=tuple(steps),
        missing=tuple(MissingConversion(pair=pair, dates=tuple(sorted(dates)), leg=leg) for (pair, leg), dates in missing_dates.items()),
        unknown_cost_movement_ids=tuple(unknown),
        oversold_movement_ids=tuple(oversold),
    )
