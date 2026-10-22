"""Conversions of the lots analysis: the FX resolver loaded once per request, and the conversions each view needs."""

from __future__ import annotations

from collections import ChainMap, defaultdict
from dataclasses import dataclass
from datetime import date as date_type
from decimal import Decimal
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import PriceHistory, Transaction
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import (
    LotAnalysisType,
)
from backend.app.schemas.wac import WACMissingPairInfo
from backend.app.services.financial_math.fifo.models import FifoEvent, FifoInputTransaction, FifoLot, FragmentInterval, LotClosure
from backend.app.services.financial_math.fx_rates import AskedDayRates
from backend.app.services.financial_math.lots.prices import opening_reference_price
from backend.app.services.financial_math.price_marks import AssetPriceSeries
from backend.app.services.financial_math.returns import realized_gain
from backend.app.services.fx.conversion import unit_rate_steps

#: One unit of a currency: the amount every rate of the resolver converts.
_ONE = Decimal("1")


@dataclass(frozen=True, slots=True)
class _UnitIdentity:
    """The rate of a currency asked under another spelling of the target (``eur`` for ``EUR``): one, every day, as
    ``convert_bulk`` answered such an identity — no stored row, no first day."""

    days: tuple[date_type, ...] = ()
    values: tuple[Decimal, ...] = ()

    def at(self, _day: date_type) -> Decimal:
        return _ONE


class FxRateResolver:
    """The rates of one lots analysis into ``target_currency``: asked by day, loaded at once, read without I/O.

    ``need`` asks one day, ``need_days`` every day of a window (the market series asks each of its currencies from the
    first transaction to the end). ``load`` reads every rate asked since the previous load in one ``unit_rate_steps``
    call (L1b, «formule veloci», on P3): one unit of each currency in the target on every asked day — the amount
    ``convert_bulk`` gave for it, to the digit and the exponent — read on the days a stored rate changes instead of a
    request a day. A day nobody asked has no rate (``AskedDayRates``), as when the rates were a map filled a day at a
    time. Each currency is still read as ``Currency`` writes it (``usd`` reads the USD rates; a code ``Currency`` refuses
    raises at load), and one that is the target under another spelling converts at exactly one.

    ``convert`` turns an amount at the rate of its day, or gives None and records the day as a gap of its pair
    (``missing_pairs``).
    """

    def __init__(self, target_currency: str) -> None:
        self.target_currency = target_currency
        #: The days asked one by one, each once, in the order asked.
        self._needs: list[tuple[str, date_type]] = []
        self._seen: set[tuple[str, date_type]] = set()
        #: The windows asked by ``need_days``, by currency: a day inside one needs no ``need`` of its own.
        self._windows: dict[str, list[tuple[date_type, date_type]]] = defaultdict(list)
        #: What the next ``load`` reads: the windows asked since the last one, and how many of ``_needs`` it already read.
        self._pending_windows: dict[str, list[tuple[date_type, date_type]]] = defaultdict(list)
        self._needs_loaded = 0
        #: The rates read so far, one map per load (``AskedDayRates``) after a first map that is empty — the one the pure
        #: tests fill by hand.
        self._rates: ChainMap[tuple[str, date_type], Decimal] = ChainMap()
        self._missing: dict[str, set[date_type]] = defaultdict(set)

    def need(self, currency: str | None, as_of_date: date_type) -> None:
        """Ask the rate of ``currency`` on one day."""
        if not currency or currency == self.target_currency:
            return
        key = (currency, as_of_date)
        if key in self._seen or any(first <= as_of_date <= last for first, last in self._windows.get(currency, ())):
            return
        self._seen.add(key)
        self._needs.append(key)

    def need_days(self, currency: str | None, first: date_type, last: date_type) -> None:
        """Ask the rate of ``currency`` on every day of ``[first, last]``; nothing when the window ends before it starts."""
        if not currency or currency == self.target_currency or last < first:
            return
        self._windows[currency].append((first, last))
        self._pending_windows[currency].append((first, last))

    async def load(self, session: AsyncSession) -> None:
        """Read the rates asked since the previous load: one ``unit_rate_steps`` call, none when nothing is asked."""
        windows: dict[str, list[tuple[date_type, date_type]]] = defaultdict(list)
        for currency, asked in self._pending_windows.items():
            windows[currency].extend(asked)
        for currency, as_of_date in self._needs[self._needs_loaded :]:
            windows[currency].append((as_of_date, as_of_date))
        if not windows:
            return
        # The code as ``convert_bulk``'s callers built it, ``Currency(code=…)``: normalised, and refused when invalid.
        codes = {currency: Currency(code=currency, amount=_ONE).code for currency in windows}
        requests: dict[tuple[str, str], list[tuple[date_type, date_type]]] = defaultdict(list)
        for currency, asked in windows.items():
            if codes[currency] != self.target_currency:
                requests[(codes[currency], self.target_currency)].extend(asked)
        steps = await unit_rate_steps(session, requests) if requests else {}
        readers = {}
        for currency in windows:
            reader = _UnitIdentity() if codes[currency] == self.target_currency else steps.get((codes[currency], self.target_currency))
            if reader is not None:
                readers[(currency, self.target_currency)] = reader
        self._rates.maps.append(AskedDayRates(readers, {(currency, self.target_currency): asked for currency, asked in windows.items()}, fixed_destination=self.target_currency))
        self._pending_windows = defaultdict(list)
        self._needs_loaded = len(self._needs)

    def convert(self, amount: Decimal | None, currency: str | None, as_of_date: date_type) -> Decimal | None:
        if amount is None:
            return None
        if not currency or currency == self.target_currency:
            return amount
        rate = self._rates.get((currency, as_of_date))
        if rate is None:
            self._missing[f"{currency}/{self.target_currency}"].add(as_of_date)
            return None
        return amount * rate

    def missing_pairs(self) -> list[WACMissingPairInfo]:
        """Every conversion asked for and not made, one entry per pair, as the data-quality report lists them."""
        return [WACMissingPairInfo(pair=pair, dates=sorted(dates)) for pair, dates in sorted(self._missing.items())]


@dataclass(frozen=True, slots=True)
class ConvertedClosure:
    """One closure in the target currency, each leg at its own date; None where a rate is missing.

    ``cost`` is the leg a closure gives up: a long lot's purchase cost of the units sold, a short lot's cost of
    the purchase that closes it.
    """

    open_unit_price: Decimal | None
    close_unit_price: Decimal | None
    proceeds: Decimal | None
    cost: Decimal | None
    realized_pnl: Decimal | None


def convert_closure(closure: LotClosure, lot: FifoLot, fx_resolver: FxRateResolver) -> ConvertedClosure:
    """A closure's prices, proceeds, cost and realized P&L in the target currency (decision 26).

    The lot's side converts from the lot's currency at the lot's opening date — the purchase rate — and the
    closing side from the closure's currency at the close date — the sale rate. A long lot realizes its proceeds
    minus the cost of the units it gives up; a short lot the proceeds of its opening sale minus the cost of the
    purchase that closes it. A fully closed lot so keeps no market P&L, and its realized P&L is the Dashboard's.
    The engine's native realized P&L is never read: it is unknown when the two currencies differ.
    """
    opening_leg = fx_resolver.convert(closure.quantity * closure.open_unit_price, lot.currency, lot.opening_date)
    closing_leg = fx_resolver.convert(closure.quantity * closure.close_unit_price, closure.close_currency, closure.close_date)
    if lot.direction == "LONG":
        cost, realized_pnl = opening_leg, realized_gain(closing_leg, opening_leg)
    else:
        cost, realized_pnl = closing_leg, realized_gain(opening_leg, closing_leg)
    return ConvertedClosure(
        open_unit_price=fx_resolver.convert(closure.open_unit_price, lot.currency, lot.opening_date),
        close_unit_price=fx_resolver.convert(closure.close_unit_price, closure.close_currency, closure.close_date),
        proceeds=fx_resolver.convert(closure.proceeds, closure.close_currency, closure.close_date),
        cost=cost,
        realized_pnl=realized_pnl,
    )


def need_closure_rates(fx_resolver: FxRateResolver, closure: LotClosure, lot: FifoLot) -> None:
    """Ask for the two rates ``convert_closure`` reads: the closure's currency at its date, the lot's at its opening."""
    fx_resolver.need(closure.close_currency, closure.close_date)
    fx_resolver.need(lot.currency, lot.opening_date)


def collect_fx_needs(  # noqa: C901 — independent per-analysis fx-need collection blocks, no decision tree
    *,
    fx_resolver: FxRateResolver,
    analyses: Sequence[LotAnalysisType],
    lots_by_id: dict[int, FifoLot],
    selected_ids: Sequence[int],
    transactions: Sequence[Transaction | FifoInputTransaction],
    price_series: AssetPriceSeries,
    prices: Sequence[PriceHistory],
    fragments: Sequence[FragmentInterval],
    events: Sequence[FifoEvent],
    closures: Sequence[LotClosure],
    split_ratios_by_tx_id: dict[int, Decimal],
    actual_to: date_type,
    computed_from: date_type,
    asset_currency: str,
) -> None:
    tx_by_id = {tx.id: tx for tx in transactions if tx.id is not None}
    if LotAnalysisType.LOT_SUMMARY in analyses or LotAnalysisType.RETURN_HISTORY in analyses:
        for lot_id in selected_ids:
            lot = lots_by_id[lot_id]
            fx_resolver.need(lot.currency, lot.opening_date)
            raw_reference_price, raw_reference_currency, reference_date, _reference_source = opening_reference_price(lot, price_series)
            if raw_reference_price is not None and raw_reference_currency is not None:
                fx_resolver.need(raw_reference_currency, reference_date)
            for closure in [c for c in closures if c.lot_id == lot_id]:
                need_closure_rates(fx_resolver, closure, lot)

    if LotAnalysisType.GANTT_TOPOLOGY in analyses:
        for fragment in fragments:
            if fragment.lot_id in selected_ids:
                lot = lots_by_id[fragment.lot_id]
                fx_resolver.need(lot.currency, fragment.start_date)

    if LotAnalysisType.CUSTODY_HISTORY in analyses or LotAnalysisType.EVENT_HISTORY in analyses:
        for event in events:
            tx = tx_by_id.get(event.transaction_id)
            if tx is not None:
                fx_resolver.need(tx.currency, event.date)
            # An opening row's price is in its lot's currency (for a priced ADJUSTMENT, its cost basis's).
            if event.kind in ("BUY", "ADJUSTMENT_IN") and event.transaction_id in lots_by_id:
                fx_resolver.need(lots_by_id[event.transaction_id].currency, event.date)
        for closure in closures:
            if closure.lot_id in selected_ids:
                need_closure_rates(fx_resolver, closure, lots_by_id[closure.lot_id])

    # The market price line (Y-30) reads the same marks every day, though it values no lot: it needs their rates too.
    if needs_market_series(analyses) or LotAnalysisType.MARKET_PRICE_HISTORY in analyses:
        # The unified resolver marks each day from asset-system prices AND observed trades
        # (BUY/SELL; never an ADJUSTMENT), each in its native currency; both the valuation and
        # chart lines convert those marks to target at the *valuation* date. Register the fx
        # needs for every price- and trade-currency across the whole window so a foreign mark
        # carried forward still translates on the day it is read (mirrors build_asset_price_series):
        # one window per currency, every day of it asked (L1b).
        currencies = {price.currency for price in prices}
        for tx in transactions:
            if tx.id in split_ratios_by_tx_id:
                continue
            tx_type = str(getattr(tx.type, "value", tx.type))
            # The series' observations: BUY/SELL trades, never an ADJUSTMENT (J-17).
            if tx_type in ("BUY", "SELL") and tx.amount:
                currencies.add(tx.currency or asset_currency)
        currencies.discard(None)
        for currency in currencies:
            fx_resolver.need_days(currency, computed_from, actual_to)


def needs_market_series(analyses: Sequence[LotAnalysisType]) -> bool:
    return any(
        analysis in analyses
        for analysis in (
            LotAnalysisType.LOT_SUMMARY,
            LotAnalysisType.VALUE_HISTORY,
            LotAnalysisType.RETURN_HISTORY,
            LotAnalysisType.PRICE_HISTORY,
            LotAnalysisType.PERFORMANCE_HISTORY,
        )
    )


def _need_cost_rates(fx_resolver: FxRateResolver, lots_by_id: dict[int, FifoLot], at_cost_until: date_type | None) -> None:
    """When some day is valued at cost, each LONG lot's currency at its opening date: the rate that day reads the lot's
    cost at (J-33)."""
    if at_cost_until is None:
        return
    for lot in lots_by_id.values():
        if lot.direction == "LONG":
            fx_resolver.need(lot.currency, lot.opening_date)


def _need_short_proceeds_rates(fx_resolver: FxRateResolver, lots_by_id: dict[int, FifoLot]) -> None:
    """Each SHORT lot's currency at its opening date: its sale's proceeds are a flow at that day's rate (MF-E2); the
    purchase that closes it converts at its own date, a rate the purchase already asks."""
    for lot in lots_by_id.values():
        if lot.direction == "SHORT":
            fx_resolver.need(lot.currency, lot.opening_date)


def collect_performance_fx_needs(
    *,
    fx_resolver: FxRateResolver,
    analyses: Sequence[LotAnalysisType],
    transactions: Sequence[Transaction | FifoInputTransaction],
    closures: Sequence[LotClosure],
    lots_by_id: dict[int, FifoLot],
    asset_currency: str,
    at_cost_until: date_type | None = None,
) -> None:
    if LotAnalysisType.PERFORMANCE_HISTORY not in analyses:
        return
    _need_cost_rates(fx_resolver, lots_by_id, at_cost_until)
    _need_short_proceeds_rates(fx_resolver, lots_by_id)
    for tx in transactions:
        tx_type = str(getattr(tx.type, "value", tx.type))
        if tx_type == "BUY":
            fx_resolver.need(tx.currency or asset_currency, tx.date)
            continue
        if tx_type == "ADJUSTMENT" and tx.quantity > 0:
            if tx.cost_basis_override not in (None, Decimal("0")):
                fx_resolver.need(tx.cost_basis_currency or asset_currency, tx.date)
            elif tx.amount != Decimal("0"):
                fx_resolver.need(tx.currency or asset_currency, tx.date)
    for closure in closures:
        lot = lots_by_id.get(closure.lot_id)
        if lot is not None and lot.direction == "LONG" and closure.close_reason == "SELL":
            need_closure_rates(fx_resolver, closure, lot)


def unconvertible_ids(transactions: Sequence[Transaction], fx_resolver: FxRateResolver, asset_currency: str) -> set[int]:
    """Ids of the transactions whose amount has no rate to the target currency on their date."""
    return {tx.id for tx in transactions if tx.id is not None and tx.amount is not None and fx_resolver.convert(tx.amount, tx.currency or asset_currency, tx.date) is None}
