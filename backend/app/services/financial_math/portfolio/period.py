"""The boundaries of a portfolio period and the P&L between them, read from the engine's daily states.

A period is measured between two states: the last state on or before its start date, and the state
of its end date. The Dashboard's period figures and its unrealized breakdown read the same two states,
so the rows of the breakdown add up to the period's change exactly.
"""

from __future__ import annotations

import bisect
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal

from backend.app.services.financial_math.native_cash import CONVERSION_DUST
from backend.app.services.financial_math.portfolio.models import DailyPortfolioState, DailyStates, MarketValueTransfer
from backend.app.services.financial_math.returns import change_ratio


def state_as_of(daily_states: Sequence[DailyPortfolioState], as_of: date_type) -> DailyPortfolioState | None:
    """The last daily state dated on or before ``as_of``; None when there is none.

    ``daily_states`` are sorted by date. The engine's states should already end at the requested date;
    looking the end up by date guards against a cached result that reaches further.
    """
    if isinstance(daily_states, DailyStates):
        return daily_states.state_as_of(as_of)
    if not daily_states:
        return None
    dates = [state.date for state in daily_states]
    index = bisect.bisect_right(dates, as_of) - 1
    if index < 0:
        return None
    return daily_states[index]


@dataclass(frozen=True)
class DayChange:
    """How the total P&L moved over the last day: the amount, and that amount as a fraction of the day before's P&L
    and NAV (``returns.change_ratio``: the change's sign, None on a zero base)."""

    pnl_change: Decimal
    vs_total_pnl: Decimal | None
    vs_nav: Decimal | None


def day_change(daily_states: Sequence[DailyPortfolioState], as_of: date_type) -> DayChange | None:
    """The change of the total P&L from the calendar day before ``as_of`` to ``as_of``.

    Both states are the engine's, looked up by date (:func:`state_as_of`), so the day before is the calendar day — a
    weekend carries Friday's state — never the previous point of a sampled series. None when either day has no state
    (a portfolio born on ``as_of``).
    """
    end = state_as_of(daily_states, as_of)
    previous = state_as_of(daily_states, as_of - timedelta(days=1))
    if end is None or previous is None:
        return None
    change = end.total_pnl - previous.total_pnl
    return DayChange(pnl_change=change, vs_total_pnl=change_ratio(change, previous.total_pnl), vs_nav=change_ratio(change, previous.nav_value))


@dataclass(frozen=True)
class PeriodBoundaries:
    """The two states a period is measured between; ``start`` is None when the period starts empty."""

    start: DailyPortfolioState | None
    end: DailyPortfolioState


def period_boundaries(daily_states: Sequence[DailyPortfolioState], date_from: date_type | None, as_of: date_type) -> PeriodBoundaries | None:
    """The states the period from ``date_from`` to ``as_of`` is measured between; None without a period.

    There is no period with fewer than two states, or without a state on or before ``as_of``. The start
    is the last state on or before ``date_from``; without ``date_from``, or when every state is later,
    the period starts empty and every start figure is zero.
    """
    if len(daily_states) < 2:
        return None
    end = state_as_of(daily_states, as_of)
    if end is None:
        return None
    start = state_as_of(daily_states, date_from) if date_from else None
    return PeriodBoundaries(start=start, end=end)


@dataclass(frozen=True)
class PeriodPnl:
    """A period's P&L and the figures it is made of, in the report currency."""

    nav_start: Decimal
    net_flows: Decimal
    pnl: Decimal
    ugl_start: Decimal
    ugl_end: Decimal
    ugl_delta: Decimal
    book_value_start: Decimal
    market_value_start: Decimal


def period_pnl(daily_states: Sequence[DailyPortfolioState], date_from: date_type | None, as_of: date_type) -> PeriodPnl | None:
    """The P&L of the period from ``date_from`` to ``as_of``: end NAV − start NAV − net external flows.

    The unrealized gain or loss at each boundary is market value less open cost basis. A period that
    starts empty starts from zero, and its net flows are every external flow up to its end. None
    without a period (:func:`period_boundaries`).
    """
    boundaries = period_boundaries(daily_states, date_from, as_of)
    if boundaries is None:
        return None
    zero = Decimal("0")
    start, end = boundaries.start, boundaries.end
    ugl_end = end.market_value - end.open_cost_basis
    if start is not None:
        nav_start = start.nav_value
        book_value_start = start.book_value
        market_value_start = start.market_value
        ugl_start = start.market_value - start.open_cost_basis
        net_flows = end.cumulative_external_cash_flow - start.cumulative_external_cash_flow
    else:
        nav_start = zero
        book_value_start = zero
        market_value_start = zero
        ugl_start = zero
        net_flows = end.cumulative_external_cash_flow
    return PeriodPnl(
        nav_start=nav_start,
        net_flows=net_flows,
        pnl=end.nav_value - nav_start - net_flows,
        ugl_start=ugl_start,
        ugl_end=ugl_end,
        ugl_delta=ugl_end - ugl_start,
        book_value_start=book_value_start,
        market_value_start=market_value_start,
    )


def period_other_result(pnl: Decimal, ugl_delta: Decimal, realized: Decimal, income: Decimal, fees_taxes: Decimal) -> Decimal:
    """The part of a period's P&L that its breakdown does not explain: what closes the identity.

    ``pnl = ugl_delta + realized + income − fees_taxes + other_result``.
    """
    return pnl - ugl_delta - realized - income + fees_taxes


def market_value_transfer_results(transfers: Iterable[MarketValueTransfer], date_from: date_type | None, end: date_type) -> dict[int, Decimal]:
    """By broker, the gain accrued elsewhere by the securities that crossed the scope's boundary in ``(date_from, end]`` (B5).

    A leg is in-kind capital at market value while its position's cost moves with it, so the period's other result holds
    cost − capital for it: + (market value − cost) for securities sent, − for securities received. Each broker with a
    leg in the window gets the sum of its legs (0 included); without ``date_from`` every leg up to ``end`` counts.
    """
    results: dict[int, Decimal] = {}
    for transfer in transfers:
        if (date_from is not None and transfer.date <= date_from) or transfer.date > end:
            continue
        results[transfer.broker_id] = results.get(transfer.broker_id, Decimal("0")) + (transfer.cost - transfer.capital)
    return results


def period_identity_residual(pnl: Decimal, ugl_delta: Decimal, realized: Decimal, income: Decimal, fees_taxes: Decimal, other_result: Decimal) -> Decimal:
    """What the identity leaves once its five terms are taken from the period's P&L (J-14).

    ``pnl − (ugl_delta + realized + income − fees_taxes + other_result)``, in this association: the AI Export's
    reconciliation always computed it so, and Decimal arithmetic on converted amounts may round a different
    association differently in the last digit. With ``other_result`` from :func:`period_other_result` it is that
    rounding alone (:func:`is_reconciled`).
    """
    return pnl - (ugl_delta + realized + income - fees_taxes + other_result)


def is_reconciled(residual: Decimal) -> bool:
    """The identity closes: a residual below ``CONVERSION_DUST`` is the rounding of Decimal arithmetic on converted
    amounts, not a gap."""
    return abs(residual) < CONVERSION_DUST
