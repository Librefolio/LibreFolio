"""Guards the lots-analysis pieces that read a REWARD's income (project 79, STK-1).

``build_income_economic_events`` turns a REWARD into an income event worth its value on receipt (``income_value``), in
its cost basis's currency, and skips one of unknown value; ``extract_income_outputs`` marks it
``LotIncomeEventKind.REWARD``; ``unconvertible_ids`` checks the rate of that value, never of the zero cash amount.
Pure: ``Transaction`` rows in memory and an ``FxRateResolver`` whose rate table is filled by hand (as in
``test_fifo_signed_income.py``).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.app.db.models import Transaction, TransactionType
from backend.app.schemas.portfolio.lots import LotIncomeEventKind
from backend.app.services.financial_math.fifo.engine import run_fifo_lot_engine
from backend.app.services.financial_math.lots.conversions import FxRateResolver, unconvertible_ids
from backend.app.services.financial_math.lots.economic_events import build_income_economic_events, extract_income_outputs

D = Decimal
ASSET = 7902
BROKER = 1
REWARD_DAY = date(2026, 3, 1)


def _row(tx_id: int, tx_type: TransactionType, on: date, *, quantity="0", amount="0", currency=None, cbo=None, cbo_ccy=None) -> Transaction:
    tx = Transaction()
    tx.id = tx_id
    tx.broker_id = BROKER
    tx.asset_id = ASSET
    tx.type = tx_type
    tx.date = on
    tx.quantity = D(quantity)
    tx.amount = D(amount)
    tx.currency = currency
    tx.cost_basis_override = None if cbo is None else D(cbo)
    tx.cost_basis_currency = cbo_ccy
    tx.related_transaction_id = None
    return tx


def _reward(tx_id: int = 3, *, cbo="0.50", cbo_ccy="EUR", quantity="20", on: date = REWARD_DAY) -> Transaction:
    return _row(tx_id, TransactionType.REWARD, on, quantity=quantity, cbo=cbo, cbo_ccy=cbo_ccy)


def _resolver(target: str = "EUR", rates: dict[tuple[str, date], Decimal] | None = None) -> FxRateResolver:
    """An FxRateResolver whose rate table is filled by hand: ``load()`` is its only part that needs a session."""
    resolver = FxRateResolver(target)
    for key, rate in (rates or {}).items():
        resolver._rates[key] = rate
    return resolver


class TestBuildIncomeEconomicEvents:
    def test_reward_event_is_its_value_in_cost_basis_currency(self):
        events = build_income_economic_events(income_transactions=[_reward()], fx_resolver=_resolver(), asset_currency="EUR", target_currency="EUR")
        by_id = {event.transaction_id: event for event in events}
        assert set(by_id) == {3}
        event = by_id[3]
        assert (event.economic_type, event.native_amount, event.native_currency, event.target_amount, event.target_currency) == ("REWARD", D("10.00"), "EUR", D("10.00"), "EUR")
        assert (event.broker_id, event.asset_id, event.date) == (BROKER, ASSET, REWARD_DAY)

    def test_usd_reward_converted_at_its_date(self):
        events = build_income_economic_events(
            income_transactions=[_reward(cbo="1.25", cbo_ccy="USD", quantity="4")],
            fx_resolver=_resolver("EUR", {("USD", REWARD_DAY): D("0.9")}),
            asset_currency="EUR",
            target_currency="EUR",
        )
        event = next(event for event in events if event.transaction_id == 3)
        assert (event.native_amount, event.native_currency, event.target_amount) == (D("5.00"), "USD", D("4.500"))

    def test_asset_currency_when_no_cost_basis_currency(self):
        events = build_income_economic_events(income_transactions=[_reward(cbo_ccy=None)], fx_resolver=_resolver("USD"), asset_currency="USD", target_currency="USD")
        event = next(event for event in events if event.transaction_id == 3)
        assert (event.native_currency, event.native_amount) == ("USD", D("10.00"))

    def test_reward_without_value_makes_no_event(self):
        dividend = _row(4, TransactionType.DIVIDEND, REWARD_DAY, amount="2", currency="EUR")
        events = build_income_economic_events(income_transactions=[_reward(cbo=None), dividend], fx_resolver=_resolver(), asset_currency="EUR", target_currency="EUR")
        assert {event.transaction_id for event in events} == {4}

    def test_reward_of_explicit_zero_value_makes_a_zero_event(self):
        """Q-A: an explicit 0 is a value, not a missing one."""
        events = build_income_economic_events(income_transactions=[_reward(cbo="0")], fx_resolver=_resolver(), asset_currency="EUR", target_currency="EUR")
        event = next(event for event in events if event.transaction_id == 3)
        assert (event.economic_type, event.native_amount, event.target_amount) == ("REWARD", D("0"), D("0"))


class TestExtractIncomeOutputs:
    def test_reward_marker_on_the_lots_held_the_day_before(self):
        buy = _row(1, TransactionType.BUY, date(2026, 1, 10), quantity="100", amount="-40", currency="EUR")
        reward = _reward()
        events = build_income_economic_events(income_transactions=[reward], fx_resolver=_resolver(), asset_currency="EUR", target_currency="EUR")
        result = run_fifo_lot_engine([buy, reward], {BROKER: False}, economic_events=events, target_currency="EUR")

        income_by_lot, income_prefix_by_lot, payload = extract_income_outputs(result, events)

        assert income_by_lot == {1: D("10.00")}
        assert income_prefix_by_lot == {1: {REWARD_DAY: D("10.00")}}
        markers = {marker.transaction_id: marker for marker in payload}
        assert set(markers) == {3}
        assert (markers[3].type, markers[3].amount, markers[3].lot_ids, markers[3].date) == (LotIncomeEventKind.REWARD, D("10.00"), [1], REWARD_DAY)

    def test_reward_without_prior_lots_marks_its_own_lot(self):
        """Q-D: no lot held the day before, the income sits on the lot the reward opens."""
        reward = _reward()
        events = build_income_economic_events(income_transactions=[reward], fx_resolver=_resolver(), asset_currency="EUR", target_currency="EUR")
        result = run_fifo_lot_engine([reward], {BROKER: False}, economic_events=events, target_currency="EUR")

        income_by_lot, _prefix, payload = extract_income_outputs(result, events)

        assert income_by_lot == {3: D("10.00")}
        marker = next(marker for marker in payload if marker.transaction_id == 3)
        assert (marker.type, marker.lot_ids) == (LotIncomeEventKind.REWARD, [3])


class TestUnconvertibleIds:
    def test_usd_reward_without_a_rate_is_flagged(self):
        assert unconvertible_ids([_reward(cbo_ccy="USD")], _resolver("EUR"), "EUR") == {3}

    def test_usd_reward_with_a_rate_is_not(self):
        assert unconvertible_ids([_reward(cbo_ccy="USD")], _resolver("EUR", {("USD", REWARD_DAY): D("0.9")}), "EUR") == set()

    def test_reward_in_the_target_currency_is_not(self):
        assert unconvertible_ids([_reward(cbo_ccy="EUR")], _resolver("EUR"), "EUR") == set()

    def test_reward_without_value_is_not(self):
        """Unknown income is reported elsewhere (MISSING_COST_BASIS), never as a missing rate."""
        assert unconvertible_ids([_reward(cbo=None, cbo_ccy="USD")], _resolver("EUR"), "EUR") == set()

    def test_guard_cash_rows_still_read_their_amount(self):
        dividend = _row(5, TransactionType.DIVIDEND, REWARD_DAY, amount="2", currency="USD")
        fee = _row(6, TransactionType.FEE, REWARD_DAY, amount="-1", currency="USD")
        assert unconvertible_ids([dividend, fee, _reward(cbo_ccy="EUR")], _resolver("EUR"), "EUR") == {5, 6}
