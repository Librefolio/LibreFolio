"""``native_cash`` for pure ``DailyStateBuilder`` tests: what ``calculate()`` hands the builder.

``PortfolioCalculationEngine.calculate()`` turns every classified transaction dated up to
``actual_to`` into a cash movement (``cash_movement_from_transaction``, at the classifier's
share) and values them with ``compute_native_cash``, which converts every foreign amount at its
own date, and asks the unit rate of every day of the period, through ``fx.convert_bulk``. A
pure builder test has no FX service, only the ``fx_rate_map`` it gives the builder:
:func:`engine_native_cash` builds the same movements and answers the same questions from that
map, on the exact day only (as ``DailyStateBuilder._convert`` reads it), so the builder
revalues the cash a real run would revalue with those rates.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date
from decimal import Decimal

from backend.app.services.financial_math.native_cash import CashMovement, NativeCash, cash_movement_from_transaction
from backend.app.services.financial_math.portfolio.engine import ClassifiedTransaction

FxRateMap = Mapping[tuple[str, str, date], Decimal]


def engine_native_cash(
    classified_txs: Iterable[ClassifiedTransaction],
    *,
    target_currency: str,
    fx_rate_map: FxRateMap,
    date_to: date,
) -> NativeCash:
    """The ``native_cash`` of a builder fed with ``fx_rate_map``, over the transactions dated up to ``date_to``.

    Mirrors what ``calculate()`` does, with the builder's rate map in place of the FX service:
    one movement per classified transaction that carries cash, at its classification share and
    in classification order; every foreign amount converted at the movement's own date; the
    unit rate of every day the map holds, from the currency's first non-zero movement through
    ``date_to``. A rate the map lacks is a missing conversion, as a ``convert_bulk`` without
    that rate would report it — never a zero.
    """
    movements = tuple(_movements(classified_txs, date_to))
    return NativeCash(
        report_currency=target_currency,
        movements=movements,
        converted=tuple(_converted(movement, target_currency, fx_rate_map) for movement in movements),
        unit_rates=_unit_rates(movements, target_currency, fx_rate_map, date_to),
    )


def _movements(classified_txs: Iterable[ClassifiedTransaction], date_to: date) -> list[CashMovement]:
    """The cash movements of the transactions dated up to ``date_to``; a transaction without cash yields none."""
    movements: list[CashMovement] = []
    for ctxn in classified_txs:
        if ctxn.tx.date > date_to:
            continue
        movement = cash_movement_from_transaction(ctxn.tx, share=ctxn.share)
        if movement is not None:
            movements.append(movement)
    return movements


def _converted(movement: CashMovement, target_currency: str, fx_rate_map: FxRateMap) -> Decimal | None:
    """The movement's raw amount in ``target_currency`` at its own date, exact day only.

    A report-currency or zero amount is kept as it is (``compute_native_cash`` asks nothing for
    it); a foreign amount is multiplied by that day's rate, or is ``None`` when the map has none.
    """
    if movement.currency == target_currency or movement.amount == 0:
        return movement.amount
    rate = fx_rate_map.get((movement.currency, target_currency, movement.date))
    return None if rate is None else movement.amount * rate


def _unit_rates(movements: tuple[CashMovement, ...], target_currency: str, fx_rate_map: FxRateMap, date_to: date) -> dict[tuple[str, date], Decimal]:
    """``(currency, day) -> rate`` for every map entry of a foreign currency, from its first non-zero movement through ``date_to``.

    The first movement counts whether or not its own conversion succeeded, as the unit requests
    of ``compute_native_cash`` start from it either way.
    """
    first_day: dict[str, date] = {}
    for movement in movements:
        if movement.currency != target_currency and movement.amount != 0:
            first_day[movement.currency] = min(movement.date, first_day.get(movement.currency, movement.date))
    return {(currency, day): rate for (currency, target, day), rate in sorted(fx_rate_map.items()) if target == target_currency and currency in first_day and first_day[currency] <= day <= date_to}
