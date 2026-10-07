"""``average_costs`` for pure ``DailyStateBuilder`` tests: what ``calculate()`` hands the builder.

``PortfolioCalculationEngine.calculate()`` builds the cost positions with
``build_cost_positions`` and gets their average cost from ``compute_average_costs``, which
converts every acquisition at its own date through ``fx.convert_bulk``. A pure builder test
has no FX service, only the ``fx_rate_map`` it gives the builder: :func:`engine_average_costs`
builds the same positions, answers the same conversion requests from that map and runs the
same pure fold, so the builder replays the cost a real run would compute with those rates.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date
from decimal import Decimal

from backend.app.services.financial_math.average_cost import (
    AverageCost,
    _conversion_requests,
    _ConversionRequest,
    _fold_average_costs,
    _ResolvedConversion,
)
from backend.app.services.portfolio_engine import ClassifiedTransaction, build_cost_positions

FxRateMap = Mapping[tuple[str, str, date], Decimal]


def engine_average_costs(
    classified_txs: list[ClassifiedTransaction],
    *,
    asset_currencies: Mapping[int, str],
    target_currency: str,
    fx_rate_map: FxRateMap,
    split_linked_tx_ids: Iterable[int] | None = (),
    date_to: date | None = None,
) -> dict[tuple[int, int], AverageCost]:
    """The ``average_costs`` of a builder fed with ``fx_rate_map``, keyed ``(asset_id, broker_id)``.

    Mirrors what ``calculate()`` does, with the builder's rate map in place of the FX service:
    the same positions (``build_cost_positions``), the asset leg on, every conversion request
    answered at the movement's own date. A rate the map lacks is a missing conversion, as a
    ``convert_bulk`` without that rate would report it — never a zero.
    """
    positions = build_cost_positions(classified_txs, asset_currencies, target_currency, set(split_linked_tx_ids or ()), date_to=date_to)
    resolved = {request: _resolve(request, target_currency, fx_rate_map) for request in _conversion_requests(positions, target_currency, asset_leg=True)}
    return _fold_average_costs(positions, report_currency=target_currency, asset_leg=True, resolved=resolved)


def _resolve(request: _ConversionRequest, target_currency: str, fx_rate_map: FxRateMap) -> _ResolvedConversion | None:
    """One request answered from a map that only holds rates ``(currency, target_currency, day)``."""
    if request.target_currency == target_currency:
        # Report leg: the amount paid, converted P -> T at the acquisition date.
        rate = fx_rate_map.get((request.source_currency, target_currency, request.date))
        return None if rate is None else _ResolvedConversion(amount=request.amount * rate, rate_date=request.date)
    if request.source_currency == target_currency:
        # Asset leg: the unit rate T -> A, the inverse of that day's A -> T rate.
        rate = fx_rate_map.get((request.target_currency, target_currency, request.date))
        return None if rate is None else _ResolvedConversion(amount=request.amount / rate, rate_date=request.date)
    raise ValueError(f"conversion request that involves no report currency: {request}")
