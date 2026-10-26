"""Average cost lines of the lots analysis: the per-broker and cumulative WAC history points."""

from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from typing import Sequence

from backend.app.schemas.portfolio import (
    BrokerWACHistoryPoint,
    CumulativeWACHistoryPoint,
)
from backend.app.services.financial_math.average_cost import AverageCost

# Key of the average-cost line that pools every broker in scope (the cumulative WAC line).
ALL_BROKERS = "__all__"


def build_broker_wac_history(
    broker_ids: Sequence[int],
    lines: dict[int | str, AverageCost],
    history_dates: Sequence[date_type],
) -> list[BrokerWACHistoryPoint]:
    points: list[BrokerWACHistoryPoint] = []
    for broker_id in broker_ids:
        line = lines.get(broker_id)
        if line is None:
            continue
        points.extend(BrokerWACHistoryPoint(date=point_date, through=point_date, broker_id=broker_id, wac=wac_amount, pool_qty=pool_qty) for point_date, wac_amount, pool_qty in average_cost_points(line, history_dates))
    return points


def build_cumulative_wac_history(
    lines: dict[int | str, AverageCost],
    history_dates: Sequence[date_type],
) -> list[CumulativeWACHistoryPoint]:
    line = lines.get(ALL_BROKERS)
    if line is None:
        return []
    return [CumulativeWACHistoryPoint(date=point_date, through=point_date, wac=wac_amount, pool_qty=pool_qty) for point_date, wac_amount, pool_qty in average_cost_points(line, history_dates)]


def average_cost_points(line: AverageCost, history_dates: Sequence[date_type]) -> list[tuple[date_type, Decimal, Decimal]]:
    """(date, WAC, pool quantity) for each history date from the first movement on.

    A date on which the pool lacks part of its cost (a missing conversion) has no point:
    the gap is reported in the data quality instead of drawing a wrong average.
    """
    points: list[tuple[date_type, Decimal, Decimal]] = []
    for current_date in history_dates:
        state = line.state_at(current_date)
        if state is None or not state.report_complete:
            continue
        points.append((current_date, state.unit_cost_report, state.quantity))
    return points
