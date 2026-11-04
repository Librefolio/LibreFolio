"""A lot's figures: what its open quantity is worth, its P&L and its returns — the lot summary of the lots analysis.

The lot summary (``LotSummarySchema``) and the lot histories value a lot with the same two rules, here: the original cost
of the quantity still open (:func:`residual_cost`, also the AI Export's residual cost basis) and a lot's total value and
P&L by direction (:func:`lot_value`). :func:`lot_summary_figures` composes the summary from them; the service only
gathers its inputs (conversions, closures, income and costs) and maps the result.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_type
from decimal import Decimal

from backend.app.services.financial_math.fifo.models import FifoLot
from backend.app.services.financial_math.returns import cumulative_to_annualized, price_return
from backend.app.services.financial_math.valuation import compute_holding_value

_ZERO = Decimal("0")


def residual_cost(original_cost: Decimal | None, open_quantity: Decimal, original_quantity: Decimal) -> Decimal | None:
    """The original cost of the quantity still open: ``cost × |open| / |original|``, unrounded.

    0 for a closed lot whatever its cost, and for a lot of no original quantity; None for an open lot whose cost is
    unknown (a missing rate).
    """
    if open_quantity == 0:
        return _ZERO
    if original_cost is None:
        return None
    if original_quantity == 0:
        return _ZERO
    return original_cost * abs(open_quantity) / abs(original_quantity)


def lot_value(direction: str, open_value: Decimal, proceeds: Decimal, buybacks: Decimal, original_cost: Decimal) -> tuple[Decimal, Decimal]:
    """A lot's total value and P&L: ``(total_value, pnl)``.

    LONG: the open quantity's value plus what its closures brought in, less its cost. SHORT: what it sold, less what it
    bought back, less what buying back the rest would cost — its P&L is that value.
    """
    if direction == "LONG":
        total_value = open_value + proceeds
        return total_value, total_value - original_cost
    total_value = proceeds - buybacks - open_value
    return total_value, total_value


@dataclass(frozen=True, slots=True)
class LotSummaryFigures:
    """The computed figures of a lot summary, in the analysis currency; None where a part is unknown."""

    open_value: Decimal | None
    total_value: Decimal | None
    pnl: Decimal | None
    relative_return: Decimal | None
    market_pnl: Decimal | None
    total_pnl: Decimal | None
    cash_yield: Decimal | None
    total_return: Decimal | None
    net_total_pnl: Decimal | None
    net_total_return: Decimal | None
    annualized_return: Decimal | None
    value_source: str | None


def lot_summary_figures(
    *,
    lot: FifoLot,
    original_cost: Decimal | None,
    known_proceeds: Decimal | None,
    known_buybacks: Decimal | None,
    realized_pnl: Decimal | None,
    latest_market_price: Decimal | None,
    reference_unit_price: Decimal | None,
    income: Decimal | None,
    fees: Decimal | None,
    taxes: Decimal | None,
    estimated_mode: bool,
    quote_base_quantity: int,
    closing_date: date_type | None,
    analysis_end: date_type,
) -> LotSummaryFigures:
    """A lot summary's figures from its converted inputs; every figure reads converted amounts only.

    With a market price the open quantity is valued at it (``MARKET_PRICE``); without one, in estimated mode, an open
    LONG lot is valued at its residual cost and its market P&L is 0 (``ESTIMATED_AT_COST``). Total P&L = market P&L +
    realized + income; net = total − fees − taxes; the returns divide by the lot's cost, and the net return is annualized
    over the lot's life (to its closing date, else to ``analysis_end``).
    """
    open_value = total_value = pnl = relative_return = market_pnl = None
    value_source: str | None = None
    if latest_market_price is not None:
        value_source = "MARKET_PRICE"
        open_value = compute_holding_value(lot.open_quantity, latest_market_price, quote_base_quantity)
        if known_proceeds is not None and (lot.direction == "LONG" or known_buybacks is not None):
            total_value, pnl = lot_value(lot.direction, open_value, known_proceeds, known_buybacks or _ZERO, original_cost or _ZERO)
            if lot.direction == "LONG" and original_cost is None:
                pnl = None  # a LONG lot's P&L needs its cost; its value does not
        if pnl is not None and realized_pnl is not None:
            market_pnl = pnl - realized_pnl
        relative_return = price_return(reference_unit_price, latest_market_price)
    elif estimated_mode and lot.direction == "LONG" and lot.original_quantity != 0 and original_cost is not None:
        value_source = "ESTIMATED_AT_COST"
        open_value = residual_cost(original_cost, lot.open_quantity, lot.original_quantity)
        market_pnl = _ZERO
        if known_proceeds is not None and open_value is not None:
            total_value, pnl = lot_value(lot.direction, open_value, known_proceeds, _ZERO, original_cost)

    total_pnl = market_pnl + realized_pnl + income if market_pnl is not None and realized_pnl is not None and income is not None else None
    has_cost = original_cost is not None and original_cost > 0
    cash_yield = income / original_cost if has_cost and income is not None else None
    total_return = total_pnl / original_cost if has_cost and total_pnl is not None else None
    net_total_pnl = total_pnl - fees - taxes if total_pnl is not None and fees is not None and taxes is not None else None
    net_total_return = net_total_pnl / original_cost if has_cost and net_total_pnl is not None else None
    annualized_return = None
    if net_total_return is not None:
        lot_end = closing_date if closing_date is not None else analysis_end
        annualized_return = cumulative_to_annualized(net_total_return, (lot_end - lot.opening_date).days)
    return LotSummaryFigures(
        open_value=open_value,
        total_value=total_value,
        pnl=pnl,
        relative_return=relative_return,
        market_pnl=market_pnl,
        total_pnl=total_pnl,
        cash_yield=cash_yield,
        total_return=total_return,
        net_total_pnl=net_total_pnl,
        net_total_return=net_total_return,
        annualized_return=annualized_return,
        value_source=value_source,
    )
