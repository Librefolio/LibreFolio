"""Native cash of every broker — the single reconstruction used across LibreFolio.

:func:`compute_native_cash` takes every movement that changes a broker's cash, in the
currency it was recorded in, and returns a :class:`NativeCash`: the balance of each broker
in each currency, the value of those balances in the report currency T on any day, and the
period flows by type and by position, each converted at its own date.

The problem is described by plain data only:

* :class:`CashMovement` — one cash amount, signed as stored, with its broker, its position
  (when it has one), its currency and the share of the broker the caller counts;
* the report currency T, and the last day the rates are needed on.

All the conversions go to the FX service: every foreign movement at its own date (the flows) in one ``convert_bulk``
call, and one unit of every foreign currency on every day from its first movement on (the valuation), in one
``unit_rate_steps`` call — the same rates, kept as the days a stored rate changes (P3), so a movement centuries back
costs its stored rows, not its days. An amount already in T is taken as it is, so
cash held only in the report currency never needs a rate. A conversion that cannot be made
never becomes a zero: the movement stays out of values and flows, and its pair is reported
with every date it was needed on.

Rules:

* a balance is valued at the latest rate on or before the day, so foreign cash is revalued
  every day; the difference from the cash converted at each movement's date is the exchange
  result on cash (:meth:`NativeCash.exchange_results`, by broker and window);
* a zero amount changes no figure and never needs a rate;
* the share scales every amount: an owner counts its own share, any other role the whole
  broker (:func:`effective_share`).
"""

from __future__ import annotations

import bisect
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date as date_type
from decimal import Decimal
from typing import Any

from backend.app.schemas.common import Currency
from backend.app.services.financial_math.fx_rates import AskedDayRates
from backend.app.services.fx.conversion import convert_bulk, unit_rate_steps

_ZERO = Decimal("0")
_ONE = Decimal("1")
_OWNER = "OWNER"
_INCOME_TYPES = frozenset({"DIVIDEND", "INTEREST"})
_COST_TYPES = frozenset({"FEE", "TAX"})

# Below this size an exchange result is conversion dust, not a result: the same cash converted
# twice, once at its movement's date and once through the day's unit rate, can differ in the
# last of Decimal's 28 digits. A caller showing an exchange result leaves out anything smaller.
CONVERSION_DUST = Decimal("1e-9")


def effective_share(role: Any, share_percentage: Decimal | None) -> Decimal:
    """The share of a broker a user counts: an owner its own share, any other role the whole broker.

    Editors and viewers see a broker's figures in full. An owner's share scales them, a zero
    share included; an owner with no recorded share counts the whole broker.
    """
    if str(getattr(role, "value", role)) != _OWNER:
        return _ONE
    return _ONE if share_percentage is None else share_percentage


@dataclass(frozen=True, slots=True)
class CashMovement:
    """One change of a broker's cash, in the currency it was recorded in.

    ``amount`` is signed as stored; ``share`` is the part of the broker the caller counts.
    """

    movement_id: int | None
    transaction_type: str
    date: date_type
    broker_id: int
    asset_id: int | None
    currency: str
    amount: Decimal
    share: Decimal = _ONE

    @property
    def native(self) -> Decimal:
        """The counted amount, in the movement's own currency."""
        return self.amount * self.share


def cash_movement_from_transaction(tx: Any, *, share: Decimal = _ONE) -> CashMovement | None:
    """The cash movement of a transaction, or None when it records no cash amount.

    A zero amount is kept: it changes no balance, but the movement still belongs to the
    broker's history.
    """
    if tx.amount is None or not tx.currency:
        return None
    return CashMovement(
        movement_id=tx.id,
        transaction_type=str(getattr(tx.type, "value", tx.type)),
        date=tx.date,
        broker_id=tx.broker_id,
        asset_id=tx.asset_id,
        currency=tx.currency,
        amount=tx.amount,
        share=share,
    )


@dataclass(frozen=True, slots=True)
class MissingCashConversion:
    """A pair that could not be converted, with every date it was needed on."""

    pair: str
    dates: tuple[date_type, ...]


@dataclass(frozen=True, slots=True)
class CashFlows:
    """The cash movements of a period, in the report currency, by type and by position.

    Income (DIVIDEND, INTEREST) keeps its sign; costs (FEE, TAX) are absolute amounts. A
    movement with no position is unallocated, by broker.
    """

    signed_by_type: dict[str, Decimal]
    absolute_by_type: dict[str, Decimal]
    income_by_position: dict[tuple[int, int], Decimal]
    costs_by_position: dict[tuple[int, int], Decimal]
    unallocated_income: dict[int, Decimal]
    unallocated_costs: dict[int, Decimal]


@dataclass(frozen=True, slots=True)
class _Balance:
    """Running balance of one broker in one currency: counted rows only, by date."""

    dates: tuple[date_type, ...]
    totals: tuple[Decimal, ...]

    def at(self, day: date_type) -> Decimal | None:
        """The balance after the last row dated on or before ``day``; None before the first one."""
        index = bisect.bisect_right(self.dates, day)
        return self.totals[index - 1] if index else None


@dataclass(frozen=True, slots=True)
class NativeCash:
    """Every broker's cash in its own currencies, and its value in the report currency.

    ``converted[i]`` is ``movements[i].amount`` in the report currency at the movement's
    date (None when the rate is missing); ``unit_rates[(currency, day)]`` is the value of one
    unit of ``currency`` on ``day``.
    """

    report_currency: str
    movements: tuple[CashMovement, ...]
    converted: tuple[Decimal | None, ...]
    unit_rates: Mapping[tuple[str, date_type], Decimal]
    _balances: dict[int, dict[str, _Balance]] = field(init=False, repr=False, compare=False)
    _first_counted: dict[int, date_type] = field(init=False, repr=False, compare=False)
    _rate_days: dict[str, tuple[date_type, ...]] = field(init=False, repr=False, compare=False)
    _rate_values: dict[str, tuple[Decimal, ...]] = field(init=False, repr=False, compare=False)
    _change_days: tuple[date_type, ...] = field(init=False, repr=False, compare=False)
    _foreign_brokers: frozenset[int] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        movements = tuple(self.movements)
        converted = tuple(self.converted)
        if len(converted) != len(movements):
            raise ValueError(f"{len(converted)} converted amounts for {len(movements)} cash movements")
        object.__setattr__(self, "movements", movements)
        object.__setattr__(self, "converted", converted)

        counted = [movement for movement, value in zip(movements, converted, strict=True) if self._is_counted(movement, value)]
        foreign = [movement for movement in counted if movement.currency != self.report_currency]
        # P3: a view on steps gives its steps, not every asked day: the last rate on or before a day, and the days a rate
        # changes, are the same on the steps (between two of them the rate does not move)
        rate_days, rate_values = _step_rate_series(self.unit_rates) if isinstance(self.unit_rates, AskedDayRates) else _rate_series(self.unit_rates)
        object.__setattr__(self, "_balances", _running_balances(counted))
        object.__setattr__(self, "_first_counted", _first_dates(counted))
        object.__setattr__(self, "_rate_days", rate_days)
        object.__setattr__(self, "_rate_values", rate_values)
        held = {movement.currency for movement in foreign}
        calendar = sorted({day for currency in held for day in rate_days.get(currency, ())})
        object.__setattr__(self, "_change_days", change_days(self._rate_at, held, calendar))
        object.__setattr__(self, "_foreign_brokers", frozenset(movement.broker_id for movement in foreign))

    def _is_counted(self, movement: CashMovement, value: Decimal | None) -> bool:
        return movement.amount != 0 and value is not None

    def _is_missing(self, movement: CashMovement, value: Decimal | None) -> bool:
        return movement.currency != self.report_currency and movement.amount != 0 and value is None

    def _rate_at(self, currency: str, day: date_type) -> Decimal | None:
        days = self._rate_days.get(currency)
        if not days:
            return None
        index = bisect.bisect_right(days, day)
        return self._rate_values[currency][index - 1] if index else None

    def value_at(self, as_of: date_type) -> dict[int, Decimal]:
        """Each broker's cash on ``as_of`` in the report currency, foreign balances at that day's rate.

        Only brokers with a counted movement on or before ``as_of`` appear. A movement whose
        conversion is missing is left out.
        """
        values: dict[int, Decimal] = {}
        for broker_id, by_currency in self._balances.items():
            if self._first_counted[broker_id] > as_of:
                continue
            value = _ZERO
            report_balance = by_currency.get(self.report_currency)
            if report_balance is not None:
                report_total = report_balance.at(as_of)
                if report_total is not None:
                    value += report_total
            for currency in sorted(by_currency):
                if currency == self.report_currency:
                    continue
                foreign = self._foreign_value(by_currency[currency], currency, as_of)
                if foreign is not None:
                    value += foreign
            values[broker_id] = value
        return values

    def _foreign_value(self, balance: _Balance, currency: str, day: date_type) -> Decimal | None:
        """A foreign balance on ``day`` at that day's rate; None while it is absent or zero."""
        total = balance.at(day)
        if total is None or total == 0:
            return None
        rate = self._rate_at(currency, day)
        if rate is None:
            raise ValueError(f"no {currency}/{self.report_currency} rate on or before {day} for a non-zero balance")
        return total * rate

    @property
    def foreign_cash_broker_ids(self) -> frozenset[int]:
        """Brokers with at least one counted movement outside the report currency."""
        return self._foreign_brokers

    def exchange_results(self, date_from: date_type | None, date_to: date_type) -> dict[int, Decimal]:
        """Each foreign-cash broker's exchange result on cash over ``(date_from, date_to]``.

        What the rates did to the cash the broker held: the change in value of its foreign
        balances, each at its day's rate, less the window's foreign movements converted at
        their own dates. Cash in the report currency has none. Every broker of
        :attr:`foreign_cash_broker_ids` is listed, ascending, a zero result included; an empty
        window lists none.

        The difference is returned whole: below :data:`CONVERSION_DUST` it is the rounding of
        two conversions, not a result, and a caller showing it leaves it out.
        """
        if date_from is not None and date_from >= date_to:
            return {}
        booked: dict[int, Decimal] = {}
        for movement, value in zip(self.movements, self.converted, strict=True):
            if movement.currency == self.report_currency or not self._is_counted(movement, value) or not _in_window(movement.date, date_from, date_to):
                continue
            booked[movement.broker_id] = booked.get(movement.broker_id, _ZERO) + value * movement.share
        results: dict[int, Decimal] = {}
        for broker_id in sorted(self._foreign_brokers):
            result = _ZERO
            for currency, balance in sorted(self._balances[broker_id].items()):
                if currency == self.report_currency:
                    continue
                closing = self._foreign_value(balance, currency, date_to)
                if closing is not None:
                    result += closing
                opening = None if date_from is None else self._foreign_value(balance, currency, date_from)
                if opening is not None:
                    result -= opening
            results[broker_id] = result - booked.get(broker_id, _ZERO)
        return results

    def rate_change_days(self, date_from: date_type | None, date_to: date_type) -> tuple[date_type, ...]:
        """Days in ``[date_from, date_to]`` on which the rate of a held foreign currency changes.

        The first rate of a currency counts as a change. A currency whose movements were all
        zero or all missing has no change days.
        """
        start = 0 if date_from is None else bisect.bisect_left(self._change_days, date_from)
        end = bisect.bisect_right(self._change_days, date_to)
        return self._change_days[start:end]

    def balances(self, as_of: date_type | None = None) -> dict[int, dict[str, Decimal]]:
        """Each broker's balance in each currency on ``as_of`` (every movement when None); see :func:`native_balances`."""
        return native_balances(self.movements, as_of)

    def flows(self, date_from: date_type | None = None, date_to: date_type | None = None) -> CashFlows:
        """The movements dated in ``(date_from, date_to]``, converted at their own dates.

        Missing conversions are left out (see :meth:`missing_conversions`).
        """
        signed_by_type: dict[str, Decimal] = {}
        absolute_by_type: dict[str, Decimal] = {}
        income_by_position: dict[tuple[int, int], Decimal] = {}
        costs_by_position: dict[tuple[int, int], Decimal] = {}
        unallocated_income: dict[int, Decimal] = {}
        unallocated_costs: dict[int, Decimal] = {}
        for movement, value in zip(self.movements, self.converted, strict=True):
            if value is None or not _in_window(movement.date, date_from, date_to):
                continue
            signed = value * movement.share
            absolute = abs(value) * movement.share
            kind = movement.transaction_type
            signed_by_type[kind] = signed_by_type.get(kind, _ZERO) + signed
            absolute_by_type[kind] = absolute_by_type.get(kind, _ZERO) + absolute
            if kind in _INCOME_TYPES:
                if movement.asset_id is not None:
                    key = (movement.broker_id, movement.asset_id)
                    income_by_position[key] = income_by_position.get(key, _ZERO) + signed
                else:
                    unallocated_income[movement.broker_id] = unallocated_income.get(movement.broker_id, _ZERO) + signed
            elif kind in _COST_TYPES:
                if movement.asset_id is not None:
                    key = (movement.broker_id, movement.asset_id)
                    costs_by_position[key] = costs_by_position.get(key, _ZERO) + absolute
                else:
                    unallocated_costs[movement.broker_id] = unallocated_costs.get(movement.broker_id, _ZERO) + absolute
        return CashFlows(
            signed_by_type=signed_by_type,
            absolute_by_type=absolute_by_type,
            income_by_position=income_by_position,
            costs_by_position=costs_by_position,
            unallocated_income=unallocated_income,
            unallocated_costs=unallocated_costs,
        )

    def position_flow_steps(self, date_from: date_type | None = None, date_to: date_type | None = None) -> dict[tuple[int, int], list[tuple[date_type, Decimal, Decimal]]]:
        """Each position's income and costs of ``(date_from, date_to]`` as running totals, on the days they change.

        ``(broker_id, asset_id)`` → ``[(day, income, costs)]``, ascending, one entry per day holding an income (DIVIDEND,
        INTEREST) or cost (FEE, TAX) movement of the position: the totals from ``date_from`` (excluded) through that day,
        by the rules of :meth:`flows` — income signed, costs absolute, at the movement's share, a missing conversion left
        out. One pass instead of a :meth:`flows` call a day (#48); with the movements in date order (the engine's), each
        entry equals ``flows(date_from, day)``'s figures for the position exactly.
        """
        order = sorted(range(len(self.movements)), key=lambda index: self.movements[index].date)
        totals: dict[tuple[int, int], list[Decimal]] = {}
        steps: dict[tuple[int, int], list[tuple[date_type, Decimal, Decimal]]] = {}
        for index in order:
            movement, value = self.movements[index], self.converted[index]
            kind = movement.transaction_type
            if value is None or movement.asset_id is None or not _in_window(movement.date, date_from, date_to):
                continue
            if kind not in _INCOME_TYPES and kind not in _COST_TYPES:
                continue
            key = (movement.broker_id, movement.asset_id)
            total = totals.setdefault(key, [_ZERO, _ZERO])
            if kind in _INCOME_TYPES:
                total[0] = total[0] + value * movement.share
            else:
                total[1] = total[1] + abs(value) * movement.share
            entries = steps.setdefault(key, [])
            if entries and entries[-1][0] == movement.date:
                entries[-1] = (movement.date, total[0], total[1])
            else:
                entries.append((movement.date, total[0], total[1]))
        return steps

    def sums_by_date(
        self,
        date_from: date_type | None,
        date_to: date_type | None,
        transaction_types: Iterable[str] | None = None,
    ) -> dict[date_type, dict[str, Decimal]]:
        """Counted movements in ``(date_from, date_to]`` summed by date and type, dates ascending."""
        wanted = None if transaction_types is None else frozenset(transaction_types)
        sums: dict[date_type, dict[str, Decimal]] = {}
        for movement, value in zip(self.movements, self.converted, strict=True):
            if not self._is_counted(movement, value) or not _in_window(movement.date, date_from, date_to):
                continue
            if wanted is not None and movement.transaction_type not in wanted:
                continue
            by_type = sums.setdefault(movement.date, {})
            by_type[movement.transaction_type] = by_type.get(movement.transaction_type, _ZERO) + value * movement.share
        return {day: sums[day] for day in sorted(sums)}

    def missing_conversions(
        self,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        transaction_types: Iterable[str] | None = None,
    ) -> list[MissingCashConversion]:
        """The pairs that could not be converted for movements in ``(date_from, date_to]``, by pair."""
        wanted = None if transaction_types is None else frozenset(transaction_types)
        dates_by_pair: dict[str, set[date_type]] = {}
        for movement, value in zip(self.movements, self.converted, strict=True):
            if not self._is_missing(movement, value) or not _in_window(movement.date, date_from, date_to):
                continue
            if wanted is not None and movement.transaction_type not in wanted:
                continue
            dates_by_pair.setdefault(f"{movement.currency}/{self.report_currency}", set()).add(movement.date)
        return [MissingCashConversion(pair=pair, dates=tuple(sorted(dates))) for pair, dates in sorted(dates_by_pair.items()) if dates]


def _in_window(day: date_type, date_from: date_type | None, date_to: date_type | None) -> bool:
    return (date_from is None or day > date_from) and (date_to is None or day <= date_to)


def _running_balances(counted: Sequence[CashMovement]) -> dict[int, dict[str, _Balance]]:
    """Running balance per broker and currency; same-day rows keep their order (stable sort)."""
    rows: dict[int, dict[str, list[tuple[date_type, Decimal]]]] = {}
    for movement in counted:
        rows.setdefault(movement.broker_id, {}).setdefault(movement.currency, []).append((movement.date, movement.native))
    balances: dict[int, dict[str, _Balance]] = {}
    for broker_id, by_currency in rows.items():
        balances[broker_id] = {}
        for currency, dated in by_currency.items():
            dated.sort(key=lambda item: item[0])
            running = _ZERO
            totals: list[Decimal] = []
            for _day, native in dated:
                running += native
                totals.append(running)
            balances[broker_id][currency] = _Balance(dates=tuple(day for day, _native in dated), totals=tuple(totals))
    return balances


def _first_dates(counted: Sequence[CashMovement]) -> dict[int, date_type]:
    """Each broker's first counted row."""
    first: dict[int, date_type] = {}
    for movement in counted:
        current = first.get(movement.broker_id)
        if current is None or movement.date < current:
            first[movement.broker_id] = movement.date
    return first


def _rate_series(unit_rates: Mapping[tuple[str, date_type], Decimal]) -> tuple[dict[str, tuple[date_type, ...]], dict[str, tuple[Decimal, ...]]]:
    """The unit rates of every currency, as parallel tuples sorted by day."""
    by_currency: dict[str, list[tuple[date_type, Decimal]]] = {}
    for (currency, day), rate in unit_rates.items():
        by_currency.setdefault(currency, []).append((day, rate))
    rate_days: dict[str, tuple[date_type, ...]] = {}
    rate_values: dict[str, tuple[Decimal, ...]] = {}
    for currency, series in by_currency.items():
        series.sort(key=lambda item: item[0])
        rate_days[currency] = tuple(day for day, _rate in series)
        rate_values[currency] = tuple(rate for _day, rate in series)
    return rate_days, rate_values


def _step_rate_series(unit_rates: AskedDayRates) -> tuple[dict[str, tuple[date_type, ...]], dict[str, tuple[Decimal, ...]]]:
    """The steps of every currency (P3): the days a rate starts and its values, sorted by day."""
    series = unit_rates.step_series()
    return {currency: days for currency, (days, _values) in series.items()}, {currency: values for currency, (_days, values) in series.items()}


def change_days(read: Callable[[str, date_type], Decimal | None], currencies: Iterable[str], days: Iterable[date_type]) -> tuple[date_type, ...]:
    """The days of the calendar ``days``, in its order, on which ``read`` gives a currency of ``currencies`` another
    rate than on the calendar's previous day — the one home of «the day a rate changes».

    The caller chooses the reading and the calendar: the native cash reads the last rate known on or before the day,
    on the calendar of its rate points; the portfolio engine reads the rate of the exact day, on the days a rate can
    change and the day before each (``DailyStateBuilder._reading_calendar``). A rate that appears or disappears is a change, and so is a rate on the calendar's first day.
    """
    watched = tuple(sorted(set(currencies)))
    changed: list[date_type] = []
    previous: dict[str, Decimal | None] = dict.fromkeys(watched)
    for day in days:
        rates = {currency: read(currency, day) for currency in watched}
        if rates != previous:
            changed.append(day)
        previous = rates
    return tuple(changed)


def native_balances(movements: Iterable[CashMovement], as_of: date_type | None = None) -> dict[int, dict[str, Decimal]]:
    """Each broker's balance in each currency on ``as_of`` (every movement when None).

    Needs no rate, so a caller that only wants native balances calls it without building a
    :class:`NativeCash`. Zero and missing movements are included: a balance in its own currency
    needs no rate, and a currency with movements that cancel out keeps its line at zero.
    """
    result: dict[int, dict[str, Decimal]] = {}
    for movement in movements:
        if as_of is not None and movement.date > as_of:
            continue
        by_currency = result.setdefault(movement.broker_id, {})
        by_currency[movement.currency] = by_currency.get(movement.currency, _ZERO) + movement.native
    return result


async def compute_native_cash(
    session: Any,
    movements: Sequence[CashMovement],
    *,
    report_currency: str,
    rates_until: date_type | None = None,
) -> NativeCash:
    """Every broker's native cash, with its conversions into ``report_currency``.

    One ``convert_bulk`` call converts each foreign movement at its own date; one ``unit_rate_steps`` call gives one unit
    of each foreign currency on every day from its first movement through ``rates_until`` (its last movement when None),
    as steps (P3): the same rates as a request a day, read on the days a rate changes. None is made, and ``session`` is
    not used, when every non-zero amount is already in the report currency.
    """
    movements = tuple(movements)
    amount_indexes = [index for index, movement in enumerate(movements) if movement.currency != report_currency and movement.amount != 0]
    if not amount_indexes:
        return NativeCash(report_currency=report_currency, movements=movements, converted=tuple(movement.amount for movement in movements), unit_rates={})

    unit_windows = _unit_windows([movements[index] for index in amount_indexes], rates_until)
    requests = [(Currency(code=movements[index].currency, amount=movements[index].amount), report_currency, movements[index].date) for index in amount_indexes]
    results, _errors = await convert_bulk(session, requests, raise_on_error=False)
    windows = {(currency, report_currency): asked for currency, asked in unit_windows.items()}
    steps = await unit_rate_steps(session, windows) if windows else {}

    def _result(position: int) -> Decimal | None:
        result = results[position] if position < len(results) else None
        return None if result is None else result[0].amount

    converted: list[Decimal | None] = [movement.amount for movement in movements]
    for position, index in enumerate(amount_indexes):
        converted[index] = _result(position)
    unit_rates = AskedDayRates(steps, windows, fixed_destination=report_currency)
    return NativeCash(report_currency=report_currency, movements=movements, converted=tuple(converted), unit_rates=unit_rates)


def _unit_windows(foreign: Sequence[CashMovement], rates_until: date_type | None) -> dict[str, list[tuple[date_type, date_type]]]:
    """By currency, the window of days a foreign balance may need a rate on (P3: the days a request a day asked).

    Every day from the currency's first movement to ``rates_until`` (else its last movement), even when it is centuries
    back: the rates are read as steps (``unit_rate_steps``), so the cost follows the stored rows, not the days (no date
    floor, MF-PAV-L1).
    """
    first: dict[str, date_type] = {}
    last: dict[str, date_type] = {}
    for movement in foreign:
        currency = movement.currency
        if currency not in first or movement.date < first[currency]:
            first[currency] = movement.date
        if currency not in last or movement.date > last[currency]:
            last[currency] = movement.date
    windows: dict[str, list[tuple[date_type, date_type]]] = {}
    for currency in sorted(first):
        end = last[currency] if rates_until is None else rates_until
        if first[currency] <= end:
            windows[currency] = [(first[currency], end)]
    return windows
