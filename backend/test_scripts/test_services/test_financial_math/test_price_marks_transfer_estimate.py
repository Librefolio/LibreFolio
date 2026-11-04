"""W-B94 road (b) — the cost of an incoming TRANSFER is an estimated price until the asset has a real one.

Module under test: ``backend/app/services/financial_math/price_marks.py`` (``build_asset_price_series``,
``AssetPriceSeries.resolve``).

Developer decision (30/10/2026, W-B94 road (b)). Today a TRANSFER is never a price observation: an asset received only
by a transfer has no mark at all, and the engine values it at its book cost (``ESTIMATED_AT_COST``). The new rule:

* the cost of an incoming TRANSFER leg — ``cost_basis_override``, per unit, in ``cost_basis_currency`` — becomes an
  observation of kind TRADE (so ``estimated=True``) **only while, on or before its day, the asset has no market quote
  and no operation other than another incoming TRANSFER** («nessuna quotazione né operazione»): a quote, a BUY/SELL,
  an ADJUSTMENT (with or without a cost) or an outgoing leg on or before its day stops it (the coordinator's
  refinement of the first reading, which counted only quotes and BUY/SELL);
* its unit price is lifted to the market axis like a trade: ``cost_basis_override × quote_base_quantity``; its currency
  is ``cost_basis_currency`` (a TRANSFER row has no amount and no currency of its own);
* only a TRANSFER with quantity > 0 and a positive ``cost_basis_override`` with a currency; a split-linked row is
  skipped; an ADJUSTMENT is never a price (P2, J-17); an outgoing TRANSFER never;
* several incoming legs before the first real observation all count (same day averaged, as trades), and the estimate is
  carried forward like any observation until a real one replaces it;
* the motivating example it must not break: an ETF quoted 200 up to Friday, bought years ago at 50, transferred between
  the owner's brokers on Saturday — Saturday and Sunday stay the carried 200 (MARKET), never 50.

RED on HEAD ``0d6eb0df7``: ``TestTransferOnlyAsset``, ``TestTransferBeforeTheFirstRealObservation`` and
``TestSeveralIncomingLegs`` — HEAD builds no observation from a TRANSFER, so every resolve there is MISSING (or, before
a quote, the quote's day is the first observation) — except
``TestTransferOnlyAsset::test_the_day_before_the_transfer_is_still_missing``. Declared parity guards, green on HEAD and
after the fix: that one, ``TestNeverAPrice`` (ADJUSTMENT with a cost, outgoing TRANSFER, no cost, zero cost, a cost without its currency,
split-linked), ``TestAnyOtherOperationStopsTheEstimate`` (written after the fix, for the refinement: green on HEAD,
where no transfer is ever a price, and on the fix — but for its last test, red on HEAD) and ``TestRealObservationsWin`` (the ETF weekend, a transfer on a BUY's or a quote's day, a transfer after
a real observation) — they lock what the fix must not change.

Every transaction double carries the eight fields the rule reads (``id``, ``type``, ``date``, ``quantity``, ``amount``,
``currency``, ``cost_basis_override``, ``cost_basis_currency``). A TRANSFER row has ``amount=None`` and
``currency=None``, as a stored one does: the estimate cannot come from ``|amount| / |quantity|`` nor from
``tx.currency``.

Isolation: PURE — no database, no server, no network, no clock. Runs in ``./dev.py test services financial-math``;
alone: ``./dev.py test services financial-math test_price_marks_transfer_estimate``.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from backend.app.db.models import TransactionType
from backend.app.schemas.common import BackwardFillInfo
from backend.app.services.financial_math.price_marks import AssetPriceSeries, MarkSource, build_asset_price_series

D = Decimal
EUR = "EUR"
USD = "USD"

# 2025-01-01 is a Wednesday: THU 01-02, FRI 01-03, SAT 01-04, SUN 01-05, MON 01-06.
WED, THU, FRI, SAT, SUN, MON = (date(2025, 1, day) for day in (1, 2, 3, 4, 5, 6))
YEARS_AGO = date(2021, 3, 15)
PREV_MON = date(2024, 12, 30)


def _tx(
    tx_id: int,
    tx_type: str,
    day: date,
    quantity: str,
    *,
    amount: str | None = None,
    currency: str | None = None,
    cost: str | None = None,
    cost_currency: str | None = None,
) -> SimpleNamespace:
    """A Transaction row as ``build_asset_price_series`` reads it: the eight fields, nothing else."""
    return SimpleNamespace(
        id=tx_id,
        type=TransactionType(tx_type),
        date=day,
        quantity=D(quantity),
        amount=None if amount is None else D(amount),
        currency=currency,
        cost_basis_override=None if cost is None else D(cost),
        cost_basis_currency=cost_currency,
    )


def _transfer_in(tx_id: int, day: date, quantity: str = "10", cost: str | None = "50", cost_currency: str | None = EUR) -> SimpleNamespace:
    return _tx(tx_id, "TRANSFER", day, quantity, cost=cost, cost_currency=cost_currency)


def _buy(tx_id: int, day: date, quantity: str, amount: str, currency: str = EUR) -> SimpleNamespace:
    return _tx(tx_id, "BUY", day, quantity, amount=amount, currency=currency)


def _series(*, transactions=(), closes=(), quote_base: int = 1, asset_currency: str = EUR, split_linked: set[int] | None = None) -> AssetPriceSeries:
    return build_asset_price_series(
        price_rows=[(day, D(close), asset_currency) for day, close in closes],
        transactions=list(transactions),
        split_linked_tx_ids=split_linked or set(),
        asset_currency=asset_currency,
        quote_base_quantity=quote_base,
    )


def _check(series: AssetPriceSeries, day: date, expected: tuple) -> None:
    """``(source, unit_price, currency, as_of_date, estimated)`` of the mark on ``day``, the whole tuple in a red."""
    mark = series.resolve(day)
    actual = (mark.source, mark.unit_price, mark.currency, mark.as_of_date, mark.estimated)
    assert actual == expected, f"{day}: (source, unit_price, currency, as_of_date, estimated) = {_show(actual)}, expected {_show(expected)}"


def _show(fields: tuple) -> str:
    source, unit_price, currency, as_of_date, estimated = fields
    return f"({source.value}, {unit_price}, {currency}, {as_of_date}, {estimated})"


class TestTransferOnlyAsset:
    """An asset received only by an incoming TRANSFER at a cost of 50, never quoted nor traded."""

    def test_the_transfer_day_is_an_estimated_trade_average_at_the_cost(self):
        """HEAD: MISSING (0, None, None, True) — a TRANSFER is never an observation."""
        series = _series(transactions=[_transfer_in(1, THU)])
        _check(series, THU, (MarkSource.TRADE_AVG, D("50"), EUR, THU, True))
        assert series.resolve(THU).price_backward_fill is None

    def test_later_days_carry_the_estimate(self):
        """Carried like any observation: CARRIED 50, still estimated, staleness counted from the transfer day."""
        series = _series(transactions=[_transfer_in(1, THU)])
        _check(series, MON, (MarkSource.CARRIED, D("50"), EUR, THU, True))
        assert series.resolve(MON).price_backward_fill == BackwardFillInfo(actual_rate_date=THU, days_back=4)

    def test_the_day_before_the_transfer_is_still_missing(self):
        """Parity inside a red class: nothing is invented before the transfer day."""
        series = _series(transactions=[_transfer_in(1, THU)])
        assert series.resolve(WED).source is MarkSource.MISSING

    def test_the_series_has_the_transfer_day_as_its_only_observation(self):
        """The estimate is an observation like a trade's: the series has one, on the transfer day; no market day."""
        series = _series(transactions=[_transfer_in(1, THU)])
        assert series.has_observations, "a transfer-only asset has an estimated observation"
        assert series.observation_dates == (THU,)
        assert series.last_market_date(MON) is None
        latest = series.latest()
        assert (latest.source, latest.unit_price, latest.as_of_date, latest.estimated) == (MarkSource.TRADE_AVG, D("50"), THU, True)

    def test_the_cost_is_lifted_to_the_market_axis(self):
        """Quote base 100 (a bond's): the per-unit cost 50 is 5 000 on the market axis, like a trade's unit price."""
        series = _series(transactions=[_transfer_in(1, THU)], quote_base=100)
        _check(series, THU, (MarkSource.TRADE_AVG, D("5000"), EUR, THU, True))

    def test_the_currency_is_the_cost_basis_currency(self):
        """Asset in EUR, cost basis in USD, the row's own currency None: the mark is in USD."""
        series = _series(transactions=[_transfer_in(1, THU, cost_currency=USD)], asset_currency=EUR)
        _check(series, THU, (MarkSource.TRADE_AVG, D("50"), USD, THU, True))
        _check(series, SAT, (MarkSource.CARRIED, D("50"), USD, THU, True))


class TestTransferBeforeTheFirstRealObservation:
    """The estimate holds until a real observation replaces it, then the real one rules."""

    def test_an_estimate_until_the_first_quote(self):
        """Transfer-in at 50 on THU, first quote 62 on SAT. HEAD: THU and FRI MISSING."""
        series = _series(transactions=[_transfer_in(1, THU)], closes=[(SAT, "62")])
        _check(series, THU, (MarkSource.TRADE_AVG, D("50"), EUR, THU, True))
        _check(series, FRI, (MarkSource.CARRIED, D("50"), EUR, THU, True))
        _check(series, SAT, (MarkSource.MARKET, D("62"), EUR, SAT, False))
        _check(series, MON, (MarkSource.CARRIED, D("62"), EUR, SAT, False))
        assert series.last_market_date(FRI) is None
        assert series.last_market_date(MON) == SAT
        assert series.observation_dates == (THU, SAT)

    def test_an_estimate_until_the_first_buy(self):
        """Transfer-in at 50 on THU, BUY of 10 for 600 (60 a unit) on SAT. HEAD: THU and FRI MISSING."""
        series = _series(transactions=[_transfer_in(1, THU), _buy(2, SAT, "10", "-600")])
        _check(series, FRI, (MarkSource.CARRIED, D("50"), EUR, THU, True))
        _check(series, SAT, (MarkSource.TRADE_AVG, D("60"), EUR, SAT, True))
        _check(series, MON, (MarkSource.CARRIED, D("60"), EUR, SAT, True))


class TestSeveralIncomingLegs:
    """Every incoming leg before the first real observation counts; same day averaged, as trades."""

    def test_two_legs_on_different_days(self):
        """Transfer-in at 50 on WED and at 56 on FRI, quote 70 on MON. HEAD: WED..SUN MISSING."""
        series = _series(transactions=[_transfer_in(1, WED), _transfer_in(2, FRI, cost="56")], closes=[(MON, "70")])
        _check(series, THU, (MarkSource.CARRIED, D("50"), EUR, WED, True))
        _check(series, FRI, (MarkSource.TRADE_AVG, D("56"), EUR, FRI, True))
        _check(series, SUN, (MarkSource.CARRIED, D("56"), EUR, FRI, True))
        _check(series, MON, (MarkSource.MARKET, D("70"), EUR, MON, False))

    def test_two_legs_on_the_same_day_are_averaged(self):
        """Transfer-in at 50 and at 56 on THU (two brokers handing over): the day's mark is their average, 53, as two
        trades' would be (an average of unit prices, not weighted by quantity)."""
        series = _series(transactions=[_transfer_in(1, THU, quantity="10"), _transfer_in(2, THU, quantity="30", cost="56")])
        _check(series, THU, (MarkSource.TRADE_AVG, D("53"), EUR, THU, True))
        _check(series, FRI, (MarkSource.CARRIED, D("53"), EUR, THU, True))

    def test_a_leg_after_the_first_real_observation_is_ignored(self):
        """Transfer-in at 50 on WED (counts), quote 62 on THU, transfer-in at 40 on SAT (after a real one: ignored).
        SAT and SUN carry THU's quote."""
        series = _series(transactions=[_transfer_in(1, WED), _transfer_in(2, SAT, cost="40")], closes=[(THU, "62")])
        _check(series, WED, (MarkSource.TRADE_AVG, D("50"), EUR, WED, True))
        _check(series, SAT, (MarkSource.CARRIED, D("62"), EUR, THU, False))
        assert series.observation_dates == (WED, THU)


class TestNeverAPrice:
    """Parity guards (green on HEAD and after the fix): what the rule never turns into a price."""

    def test_an_adjustment_with_a_cost_stays_missing(self):
        """P2 / J-17: an ADJUSTMENT-in with a cost is a cost, never a price — with no other row, still MISSING."""
        series = _series(transactions=[_tx(1, "ADJUSTMENT", THU, "10", cost="50", cost_currency=EUR)])
        assert not series.has_observations
        assert series.resolve(FRI).source is MarkSource.MISSING

    def test_an_outgoing_transfer_is_nothing(self):
        """An outgoing leg (quantity < 0) with a cost: never an observation."""
        series = _series(transactions=[_tx(1, "TRANSFER", THU, "-10", cost="50", cost_currency=EUR)])
        assert not series.has_observations
        assert series.resolve(FRI).source is MarkSource.MISSING

    def test_an_incoming_transfer_without_a_cost_is_nothing(self):
        series = _series(transactions=[_transfer_in(1, THU, cost=None, cost_currency=None)])
        assert not series.has_observations

    def test_an_incoming_transfer_at_cost_zero_is_nothing(self):
        """Only a positive cost is a price."""
        series = _series(transactions=[_transfer_in(1, THU, cost="0")])
        assert not series.has_observations

    def test_an_incoming_transfer_whose_cost_has_no_currency_is_nothing(self):
        """A cost with no currency cannot label a mark (the asset's currency is not guessed for it)."""
        series = _series(transactions=[_transfer_in(1, THU, cost_currency=None)])
        assert not series.has_observations

    def test_a_split_linked_transfer_is_nothing(self):
        series = _series(transactions=[_transfer_in(1, THU)], split_linked={1})
        assert not series.has_observations


class TestRealObservationsWin:
    """Parity guards (green on HEAD and after the fix): on or after a real observation the transfer's cost is no price."""

    def test_the_etf_weekend_keeps_fridays_quote(self):
        """The motivating example: ETF bought years ago at 50, quoted 200 up to FRI, transferred between the owner's
        brokers on SAT at its cost 50 (in on the receiving broker, out on the giving one). SAT and SUN carry FRI's 200,
        a real quote, never 50."""
        transactions = [
            _buy(1, YEARS_AGO, "10", "-500"),
            _tx(2, "TRANSFER", SAT, "-10", cost="50", cost_currency=EUR),
            _transfer_in(3, SAT),
        ]
        series = _series(transactions=transactions, closes=[(WED, "198"), (THU, "199"), (FRI, "200")])
        _check(series, SAT, (MarkSource.CARRIED, D("200"), EUR, FRI, False))
        _check(series, SUN, (MarkSource.CARRIED, D("200"), EUR, FRI, False))
        assert SAT not in series.observation_dates

    def test_the_etf_weekend_without_the_old_buy(self):
        """Same weekend, the old BUY at another broker outside the rows read: FRI's quote alone already precedes the
        transfer, so SAT and SUN still carry 200."""
        series = _series(transactions=[_transfer_in(3, SAT)], closes=[(THU, "199"), (FRI, "200")])
        _check(series, SUN, (MarkSource.CARRIED, D("200"), EUR, FRI, False))

    def test_a_transfer_on_a_buys_day_is_ignored(self):
        """BUY of 10 for 600 (60 a unit) and a transfer-in at 50 on THU, nothing before: the mark is the BUY's 60, not
        the 55 a transfer averaged in would give."""
        series = _series(transactions=[_buy(1, THU, "10", "-600"), _transfer_in(2, THU)])
        _check(series, THU, (MarkSource.TRADE_AVG, D("60"), EUR, THU, True))
        _check(series, FRI, (MarkSource.CARRIED, D("60"), EUR, THU, True))

    def test_a_transfer_on_a_quotes_day_is_ignored(self):
        """Quote 62 and a transfer-in at 50 on THU, nothing before: MARKET 62."""
        series = _series(transactions=[_transfer_in(1, THU)], closes=[(THU, "62")])
        _check(series, THU, (MarkSource.MARKET, D("62"), EUR, THU, False))

    def test_a_transfer_after_a_buy_is_ignored(self):
        """BUY at 60 on WED, transfer-in at 50 on FRI: FRI and SAT carry the BUY's 60."""
        series = _series(transactions=[_buy(1, WED, "10", "-600"), _transfer_in(2, FRI)])
        _check(series, FRI, (MarkSource.CARRIED, D("60"), EUR, WED, True))
        _check(series, SAT, (MarkSource.CARRIED, D("60"), EUR, WED, True))
        assert series.observation_dates == (WED,)


class TestAnyOtherOperationStopsTheEstimate:
    """The refinement («nessuna quotazione né operazione»): any operation on the asset other than an incoming TRANSFER,
    on or before the transfer's day, keeps the transfer's cost from being a price. Green on HEAD too (no transfer is ever
    a price there), except ``test_an_earlier_incoming_transfer_does_not_stop_the_next``, red on HEAD like
    ``TestSeveralIncomingLegs``."""

    def test_an_adjustment_before_keeps_the_asset_missing(self):
        """ADJUSTMENT-in of 10 at a cost of 20 on MON, TRANSFER-in of 5 at a cost of 40 on WED: no estimate — the
        ADJUSTMENT is a cost, not a price, and it is an operation before the transfer. Still MISSING on WED and after
        (the engine then values the position at its book cost)."""
        series = _series(transactions=[_tx(1, "ADJUSTMENT", PREV_MON, "10", cost="20", cost_currency=EUR), _transfer_in(2, WED, quantity="5", cost="40")])
        assert not series.has_observations
        assert series.resolve(WED).source is MarkSource.MISSING
        assert series.resolve(FRI).source is MarkSource.MISSING

    def test_an_adjustment_without_cost_before_keeps_the_asset_missing(self):
        """An ADJUSTMENT-in with no cost on MON is an operation too: the WED transfer's cost is no price."""
        series = _series(transactions=[_tx(1, "ADJUSTMENT", PREV_MON, "5"), _transfer_in(2, WED)])
        assert not series.has_observations

    def test_an_adjustment_on_the_same_day_keeps_the_asset_missing(self):
        """On or before: an ADJUSTMENT-in on the transfer's own day stops it as well."""
        series = _series(transactions=[_tx(1, "ADJUSTMENT", WED, "10", cost="20", cost_currency=EUR), _transfer_in(2, WED)])
        assert not series.has_observations

    def test_an_outgoing_transfer_before_gives_no_estimate(self):
        """An outgoing TRANSFER of 4 on MON, then a TRANSFER-in at 50 on WED: the outgoing leg is an operation, so
        neither leg is a price."""
        series = _series(transactions=[_tx(1, "TRANSFER", PREV_MON, "-4", cost="45", cost_currency=EUR), _transfer_in(2, WED)])
        assert not series.has_observations
        assert series.resolve(FRI).source is MarkSource.MISSING

    def test_an_earlier_incoming_transfer_does_not_stop_the_next(self):
        """Another incoming TRANSFER is not «an operation» for this rule: legs on MON at 48 and WED at 50 are both
        estimates (the same contract as ``TestSeveralIncomingLegs``, here across a weekend gap)."""
        series = _series(transactions=[_transfer_in(1, PREV_MON, cost="48"), _transfer_in(2, WED)])
        assert series.observation_dates == (PREV_MON, WED)
        _check(series, THU, (MarkSource.CARRIED, D("50"), EUR, WED, True))
