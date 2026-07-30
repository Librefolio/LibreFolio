"""Unified per-asset daily price resolver (the single valuation-mark source).

This module is the architectural centrepiece of the "one price aggregator" design:
given an asset's **asset-system prices** and its **observed transactions**, it answers
the single question every engine needs — *what is the per-unit mark of asset X on day D?* —
with one coherent daily model, so charts, valuation (NAV) and metrics (MWRR/TWRR/ROI)
all read from the **same** numbers.

Daily model (per asset, per day ``D``)::

    1. asset-system price exists on D            -> MARKET     (exact real quote)
    2. else same-day transactions exist          -> TRADE_AVG  (average of their unit prices)
    3. else carry the last observation <= D      -> CARRIED    (LOCF; may be MARKET- or TRADE-origin)
    4. else (nothing on/before D)                -> MISSING

Staleness of a ``CARRIED`` mark is reported with the project-wide
:class:`~backend.app.schemas.common.BackwardFillInfo` pattern (``actual_rate_date`` +
``days_back``) — the *same* contract FX and asset pricing already expose, so the frontend
can render the "value fades with age" line (see ``FxCard`` / ``FxDataEditorSection``) for
free. ``estimated`` is ``True`` whenever the value did not come from a real asset-system
quote (i.e. it is TRADE-derived), **independently** of freshness — a real quote carried
forward is *stale but not estimated*, matching the existing lots-analysis semantics.

Design contract:

* **Two layers.** :class:`AssetPriceSeries` is a *pure, synchronous, immutable* calculator
  built from pre-normalized observations — **no I/O, no DB, no async, no FX** — so engines
  (which are themselves pure) can query it and "trust it blindly". Data acquisition (prices
  via the asset-source service, transactions via the transaction service, FX via the fx
  service) happens **once per calculation** in the async caller, which then feeds normalized
  observations here. This mirrors the ``_FxRateResolver`` load-once / query-sync shape.
* **Currency & scale agnostic.** Observations must already be expressed in a single common
  currency and scale chosen by the builder. :func:`build_asset_price_series` normalizes to
  *target currency* at the *market ×quote_base_quantity* scale (the scale
  ``price_history.close`` uses), so a qbq=100 bond lands on its ~100 par axis and per-unit
  trade prices are lifted to the same axis. FX staleness (``fx_backward_fill``) is composed
  at the adoption layer from the fx service, alongside the price staleness this module owns.
* **Never for realized / cost basis.** The mark is for *open-position valuation* and the
  *price line* only. Realized P&L and cost basis must always come from the actual transaction
  prices, never from this estimate.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from datetime import date as date_type
from decimal import Decimal
from enum import StrEnum
from typing import Callable, Optional, Sequence

from backend.app.db.models import Transaction
from backend.app.schemas.common import BackwardFillInfo


class MarkSource(StrEnum):
    """How a resolved mark was produced on the requested day."""

    MARKET = "MARKET"  # exact asset-system price on the requested day
    TRADE_AVG = "TRADE_AVG"  # average of same-day observed transactions
    CARRIED = "CARRIED"  # last-known observation carried forward (LOCF)
    MISSING = "MISSING"  # no observation on/before the requested day


class ObservationKind(StrEnum):
    """Origin of a single price observation fed into the resolver."""

    MARKET = "MARKET"  # an asset-system quote (price_history)
    TRADE = "TRADE"  # a transaction-implied unit price (BUY/SELL/priced ADJUSTMENT)


@dataclass(frozen=True, slots=True)
class PriceObservation:
    """A normalized per-unit price observation for one asset on one day.

    ``unit_price`` is already expressed in the single common currency and scale chosen by
    the builder (target currency, market ×quote_base_quantity scale). The pure resolver is
    agnostic to currency/scale: it only carries the number and its origin.
    """

    date: date_type
    unit_price: Decimal
    kind: ObservationKind


@dataclass(frozen=True, slots=True)
class ResolvedMark:
    """The resolver's answer for (asset, day): the mark plus its provenance and staleness.

    * ``unit_price`` — per-unit mark in the builder's common currency/scale (0 when MISSING).
    * ``source`` — :class:`MarkSource` resolution mode on the requested day.
    * ``as_of_date`` — the underlying observation's date (``None`` when MISSING).
    * ``price_backward_fill`` — ``None`` for an exact same-day observation; a
      :class:`BackwardFillInfo` (``actual_rate_date`` + ``days_back``) when the value was
      carried forward (LOCF). Drives the frontend "fade with age" rendering.
    * ``estimated`` — ``True`` when the value is not a real asset-system quote (TRADE-origin),
      regardless of freshness. A real quote carried forward is stale but **not** estimated.
    """

    unit_price: Decimal
    source: MarkSource
    as_of_date: Optional[date_type]
    price_backward_fill: Optional[BackwardFillInfo]
    estimated: bool

    @property
    def is_missing(self) -> bool:
        return self.source is MarkSource.MISSING


_MISSING_MARK = ResolvedMark(
    unit_price=Decimal("0"),
    source=MarkSource.MISSING,
    as_of_date=None,
    price_backward_fill=None,
    estimated=True,
)


class AssetPriceSeries:
    """Immutable, pure, synchronous daily price resolver for a single asset.

    Collapses a stream of :class:`PriceObservation` into one observation per day (a MARKET
    observation on a day wins; otherwise same-day TRADE observations are averaged), then
    answers :meth:`resolve` with the daily model (MARKET/TRADE_AVG exact, else CARRIED via
    LOCF, else MISSING). O(log n) per query via ``bisect``.
    """

    __slots__ = ("_dates", "_values", "_is_market")

    def __init__(self, observations: Sequence[PriceObservation]) -> None:
        market_by_day: dict[date_type, Decimal] = {}
        trades_by_day: dict[date_type, list[Decimal]] = {}
        for obs in observations:
            if obs.kind is ObservationKind.MARKET:
                # Last MARKET observation on a day wins (price_history has one row per day,
                # but be defensive against duplicates).
                market_by_day[obs.date] = obs.unit_price
            else:
                trades_by_day.setdefault(obs.date, []).append(obs.unit_price)

        collapsed: dict[date_type, tuple[Decimal, bool]] = {}
        for day in market_by_day.keys() | trades_by_day.keys():
            if day in market_by_day:
                collapsed[day] = (market_by_day[day], True)
            else:
                same_day = trades_by_day[day]
                average = sum(same_day, Decimal("0")) / Decimal(len(same_day))
                collapsed[day] = (average, False)

        self._dates: list[date_type] = sorted(collapsed)
        self._values: list[Decimal] = [collapsed[day][0] for day in self._dates]
        self._is_market: list[bool] = [collapsed[day][1] for day in self._dates]

    @property
    def has_observations(self) -> bool:
        return bool(self._dates)

    def resolve(self, query_date: date_type) -> ResolvedMark:
        """Resolve the per-unit mark for ``query_date`` under the daily model."""
        if not self._dates:
            return _MISSING_MARK
        idx = bisect.bisect_right(self._dates, query_date) - 1
        if idx < 0:
            return _MISSING_MARK
        obs_date = self._dates[idx]
        value = self._values[idx]
        is_market = self._is_market[idx]
        estimated = not is_market
        if obs_date == query_date:
            source = MarkSource.MARKET if is_market else MarkSource.TRADE_AVG
            return ResolvedMark(unit_price=value, source=source, as_of_date=obs_date, price_backward_fill=None, estimated=estimated)
        days_back = (query_date - obs_date).days
        return ResolvedMark(
            unit_price=value,
            source=MarkSource.CARRIED,
            as_of_date=obs_date,
            price_backward_fill=BackwardFillInfo(actual_rate_date=obs_date, days_back=days_back),
            estimated=estimated,
        )

    def latest(self) -> ResolvedMark:
        """The most recent observation, as an exact mark (no backward-fill)."""
        if not self._dates:
            return _MISSING_MARK
        value = self._values[-1]
        is_market = self._is_market[-1]
        source = MarkSource.MARKET if is_market else MarkSource.TRADE_AVG
        return ResolvedMark(unit_price=value, source=source, as_of_date=self._dates[-1], price_backward_fill=None, estimated=not is_market)


# Convert (amount, currency, on_date) -> amount in target currency, or None when the FX rate
# is unavailable. Callers wire this to the fx service's loaded resolver (sync query side).
ConvertFn = Callable[[Decimal, Optional[str], date_type], Optional[Decimal]]


def build_asset_price_series(
    *,
    price_rows: Sequence[tuple[date_type, Optional[Decimal], str]],
    transactions: Sequence[Transaction],
    split_linked_tx_ids: set[int],
    asset_currency: str,
    quote_base_quantity: int,
    convert: ConvertFn,
) -> AssetPriceSeries:
    """Normalize asset-system prices + observed transactions into an :class:`AssetPriceSeries`.

    Both sources are lifted to *target currency* at the *market ×quote_base_quantity* scale
    (the scale ``price_history.close`` already uses):

    * **MARKET** observations come from ``price_rows`` (``(date, close, currency)``); ``close``
      is per quote_base_quantity, so it is converted but **not** re-scaled.
    * **TRADE** observations come from BUY/SELL (``|amount| / |quantity|``) and priced
      ADJUSTMENT carryovers (``cost_basis_override``), which are per-unit and therefore
      multiplied by ``quote_base_quantity`` to reach the market scale. Split-linked rows and
      pure quantity adjustments carry no price and are skipped.

    Mirrors the historical ``_build_market_price_map`` / ``_build_trade_price_points`` math so
    adoption is behaviour-preserving; the added value here is the unified series + staleness.
    """
    scale = Decimal(quote_base_quantity if quote_base_quantity and quote_base_quantity > 0 else 1)
    observations: list[PriceObservation] = []

    for price_date, close, currency in price_rows:
        if close is None:
            continue
        converted = convert(close, currency, price_date)
        value = converted if converted is not None else close
        observations.append(PriceObservation(date=price_date, unit_price=value, kind=ObservationKind.MARKET))

    for tx in transactions:
        if tx.id in split_linked_tx_ids:
            continue
        quantity = tx.quantity or Decimal("0")
        if quantity == Decimal("0"):
            continue
        tx_type = str(getattr(tx.type, "value", tx.type))
        unit_target: Optional[Decimal] = None
        if tx_type in ("BUY", "SELL"):
            if tx.amount:
                currency = tx.currency or asset_currency
                converted = convert(abs(tx.amount), currency, tx.date)
                total = converted if converted is not None else abs(tx.amount)
                unit_target = total / abs(quantity)
        elif tx_type == "ADJUSTMENT" and tx.cost_basis_override not in (None, Decimal("0")):
            currency = tx.cost_basis_currency or asset_currency
            converted = convert(tx.cost_basis_override, currency, tx.date)
            unit_target = converted if converted is not None else tx.cost_basis_override
        if unit_target is None:
            continue
        observations.append(PriceObservation(date=tx.date, unit_price=unit_target * scale, kind=ObservationKind.TRADE))

    return AssetPriceSeries(observations)
