"""Conversions of the lots analysis: the FX resolver loaded once per request, and the conversions each view needs."""

from __future__ import annotations

from collections import defaultdict
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import PriceHistory, Transaction
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import (
    LotAnalysisType,
)
from backend.app.schemas.wac import WACMissingPairInfo
from backend.app.services.financial_math.fifo.models import FifoEvent, FifoLot, FragmentInterval, LotClosure
from backend.app.services.financial_math.lots.prices import PriceHistoryLookup, opening_reference_price
from backend.app.services.fx.conversion import convert_bulk


class FxRateResolver:
    def __init__(self, target_currency: str) -> None:
        self.target_currency = target_currency
        self._needs: list[tuple[str, date_type]] = []
        self._seen: set[tuple[str, date_type]] = set()
        self._loaded: set[tuple[str, date_type]] = set()
        self._rates: dict[tuple[str, date_type], Decimal] = {}
        self._missing: dict[str, set[date_type]] = defaultdict(set)

    def need(self, currency: str | None, as_of_date: date_type) -> None:
        if not currency or currency == self.target_currency:
            return
        key = (currency, as_of_date)
        if key in self._seen:
            return
        self._seen.add(key)
        self._needs.append(key)

    async def load(self, session: AsyncSession) -> None:
        pending = [key for key in self._needs if key not in self._loaded]
        if not pending:
            return
        conversions = [(Currency(code=currency, amount=Decimal("1")), self.target_currency, as_of_date) for currency, as_of_date in pending]
        results, _errors = await convert_bulk(session, conversions, raise_on_error=False)
        for idx, key in enumerate(pending):
            self._loaded.add(key)
            result = results[idx] if idx < len(results) else None
            if result is None:
                continue
            converted, _rate_date, _backfilled = result
            self._rates[key] = converted.amount

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


def collect_fx_needs(  # noqa: C901 — independent per-analysis fx-need collection blocks, no decision tree
    *,
    fx_resolver: FxRateResolver,
    analyses: Sequence[LotAnalysisType],
    lots_by_id: dict[int, FifoLot],
    selected_ids: Sequence[int],
    transactions: Sequence[Transaction],
    price_lookup: PriceHistoryLookup,
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
            raw_reference_price, raw_reference_currency, reference_date, _reference_source = opening_reference_price(lot, price_lookup)
            if raw_reference_price is not None and raw_reference_currency is not None:
                fx_resolver.need(raw_reference_currency, reference_date)
            for closure in [c for c in closures if c.lot_id == lot_id]:
                fx_resolver.need(lot.currency, closure.close_date)

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
                lot = lots_by_id[closure.lot_id]
                fx_resolver.need(lot.currency, closure.close_date)

    if needs_market_series(analyses):
        current = computed_from
        # The unified resolver marks each day from asset-system prices AND observed trades
        # (BUY/SELL + priced ADJUSTMENT), each in its native currency; both the valuation and
        # chart lines convert those marks to target at the *valuation* date. Register the fx
        # needs for every price- and trade-currency across the whole window so a foreign mark
        # carried forward still translates on the day it is read (mirrors build_asset_price_series).
        currencies = {price.currency for price in prices}
        for tx in transactions:
            if tx.id in split_ratios_by_tx_id:
                continue
            tx_type = str(getattr(tx.type, "value", tx.type))
            if tx_type in ("BUY", "SELL") and tx.amount:
                currencies.add(tx.currency or asset_currency)
            elif tx_type == "ADJUSTMENT" and tx.cost_basis_override not in (None, Decimal("0")):
                currencies.add(tx.cost_basis_currency or asset_currency)
        currencies.discard(None)
        while current <= actual_to:
            for currency in currencies:
                fx_resolver.need(currency, current)
            current += timedelta(days=1)


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


def collect_performance_fx_needs(
    *,
    fx_resolver: FxRateResolver,
    analyses: Sequence[LotAnalysisType],
    transactions: Sequence[Transaction],
    closures: Sequence[LotClosure],
    lots_by_id: dict[int, FifoLot],
    asset_currency: str,
) -> None:
    if LotAnalysisType.PERFORMANCE_HISTORY not in analyses:
        return
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
        elif tx_type == "ADJUSTMENT" and tx.quantity < 0 and tx.cost_basis_override not in (None, Decimal("0")):
            fx_resolver.need(tx.cost_basis_currency or asset_currency, tx.date)
    for closure in closures:
        lot = lots_by_id.get(closure.lot_id)
        if lot is not None and lot.direction == "LONG" and closure.close_reason == "SELL":
            fx_resolver.need(lot.currency or asset_currency, closure.close_date)


def unconvertible_ids(transactions: Sequence[Transaction], fx_resolver: FxRateResolver, asset_currency: str) -> set[int]:
    """Ids of the transactions whose amount has no rate to the target currency on their date."""
    return {tx.id for tx in transactions if tx.id is not None and tx.amount is not None and fx_resolver.convert(tx.amount, tx.currency or asset_currency, tx.date) is None}
