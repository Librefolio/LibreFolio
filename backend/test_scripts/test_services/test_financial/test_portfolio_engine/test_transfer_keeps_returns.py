"""J2 (D-MF4 = a) — a linked cash transfer or currency conversion keeps the generated returns it moves.

The Dashboard splits the cash into ``cash_from_contributed_capital`` and ``cash_from_generated_returns`` from two
pools per broker: K (capital) and R (returns). Before J2 a linked-internal CASH_TRANSFER / FX_CONVERSION left its
broker from R first, then from K, and arrived **all into K** («Approximate»): moving or converting cash turned
generated returns into contributed capital. With J2 the departure records ``(from_r, sent)`` by its transaction id,
and the arrival (its ``paired_tx``), worth ``amount``, brings back what the departure took from each pool:
``K += sent - from_r``, ``R += from_r + (amount - sent)``. The two legs' amounts can differ (a conversion's spread,
two dates' rates, brokers owned at different shares): that gap ``amount - sent`` is a result, never capital — booked
like an exchange result on cash at rest (docs §6 «Exchange Result on Foreign Cash»): a gain goes to R, a loss comes
out of R first and then of K, as a FEE (``R < 0`` -> ``K += R``, ``R = 0``). An arrival whose departure is unknown, or
whose departure was worth 0, still arrives all in K. A same-day arrival is processed after its departure, whatever
their ids. Only the gap changes the total cash, and only by itself.

- ``TestCrossBrokerCashTransfer`` — A (K 1000, R 300) sends cash to B, in one day: the returns travel.
- ``TestSameBrokerFxConversion`` — EUR -> USD at one broker: each pool comes back, the gap is a result.
- ``TestConversionLossBeyondTheReturns`` — a conversion losing more than the returns it moves: K absorbs the rest.
- ``TestBrokersOwnedAtDifferentShares`` — each leg weighted by its broker's share: the gap is the P&L's, R's too.
- ``TestCashInTransit`` — the arrival two days later brings the returns back; the window in between is the rescale's.
- ``TestSameDayArrivalBeforeItsDeparture`` — the arrival's id is lower than its departure's: it still carries.
- ``TestArrivalWithoutKnownDeparture`` — a departure with no amount, or outside the scope: nothing is carried.
- ``TestDepartureWithoutReturns`` — R 0 at the sender: the arrival is all capital, as before.
- ``TestMoveLinkedCash`` / ``TestApplyPoolRuleWithSplits`` — ``_move_linked_cash`` and
  ``_apply_pool_rule(..., transfer_splits)`` as pure functions.

On HEAD ca2f00c35 (before J2): ``TestCrossBrokerCashTransfer``, ``TestSameBrokerFxConversion``,
``TestConversionLossBeyondTheReturns.test_the_loss_also_takes_the_receivers_own_returns``,
``TestBrokersOwnedAtDifferentShares.test_a_loss_comes_out_of_the_returns_moved`` and ``…test_a_gain_goes_to_returns``,
``TestCashInTransit.test_the_arrival_brings_the_returns_back``, ``TestSameDayArrivalBeforeItsDeparture`` red (every
value they check is quoted, "HEAD:", in their docstrings); ``TestMoveLinkedCash`` and ``TestApplyPoolRuleWithSplits``
red (no ``_move_linked_cash``, and ``_apply_pool_rule`` takes no ``transfer_splits``); the in-transit window,
``TestConversionLossBeyondTheReturns.test_at_one_broker_capital_absorbs_the_rest``,
``TestBrokersOwnedAtDifferentShares.test_a_loss_beyond_the_returns_moved_comes_out_of_capital``,
``TestArrivalWithoutKnownDeparture`` and ``TestDepartureWithoutReturns`` green (parity pins).

Notation: target EUR; brokers A = 10, B = 20 (owned at 100 % unless a test gives a share); X = 100 a EUR stock;
D0 = 2025-01-01 ... D4 = 2025-01-05. Rates are exact-day ``("USD", "EUR", day)`` entries. Cash and pools are in EUR, at
the scope's share.

Pure tests — no DB, no server. Helpers are copies of test_broker_internal_flows.py / test_single_replay.py (this
directory has no cross-test-module imports). ``_move_linked_cash`` is read from the module inside its tests, so that
on a builder without it only those tests fail, not the module's import.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

import backend.app.services.financial_math.portfolio.daily_state as daily_state_module
from backend.app.db.models import TransactionType
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.models import ClassifiedTransaction, PortfolioCalculationResult
from backend.app.services.financial_math.price_marks import build_asset_price_series
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash

A, B = 10, 20
X = 100

D0 = date(2025, 1, 1)
D1 = date(2025, 1, 2)
D2 = date(2025, 1, 3)
D3 = date(2025, 1, 4)
D4 = date(2025, 1, 5)

# =============================================================================
# HELPERS — copies of test_broker_internal_flows.py / test_single_replay.py
# =============================================================================


def _tx(
    *,
    id: int | None = 1,
    broker_id: int = A,
    type: str = "DEPOSIT",
    dt: date = D0,
    amount: str = "0",
    currency: str | None = "EUR",
    quantity: str = "0",
    asset_id: int | None = None,
    related_id: int | None = None,
) -> MagicMock:
    tx = MagicMock()
    tx.id = id
    tx.broker_id = broker_id
    tx.type = TransactionType(type)
    tx.date = dt
    tx.amount = Decimal(amount)
    tx.currency = currency
    tx.quantity = Decimal(quantity)
    tx.asset_id = asset_id
    tx.related_transaction_id = related_id
    tx.cost_basis_override = None
    tx.cost_basis_currency = None
    return tx


def _ctxn(tx: MagicMock, classification: str = "normal", paired: MagicMock | None = None) -> ClassifiedTransaction:
    return ClassifiedTransaction(tx=tx, classification=classification, share=Decimal("1"), paired_tx=paired)


def _cash_pair(
    out_id: int,
    in_id: int,
    *,
    sender: int,
    receiver: int,
    out_dt: date,
    in_dt: date,
    out_amount: str,
    in_amount: str,
    out_currency: str = "EUR",
    in_currency: str = "EUR",
    type: str = "CASH_TRANSFER",
) -> tuple[MagicMock, MagicMock]:
    """Two linked cash legs: -out_amount on the sender, +in_amount on the receiver."""
    out_leg = _tx(id=out_id, broker_id=sender, type=type, dt=out_dt, amount=f"-{out_amount}", currency=out_currency, related_id=in_id)
    in_leg = _tx(id=in_id, broker_id=receiver, type=type, dt=in_dt, amount=in_amount, currency=in_currency, related_id=out_id)
    return out_leg, in_leg


def _usd_rates(rates: dict[date, str]) -> dict[tuple[str, str, date], Decimal]:
    """USD->EUR on the given days only (the map is exact-day: any other day has no rate)."""
    return {("USD", "EUR", day): Decimal(rate) for day, rate in rates.items()}


def _classify(txs, scope, *, shares=None, external_paired=None):
    """Run the real classifier, transactions in loading order (date, id); share 1 unless ``shares`` gives a broker's."""
    broker_shares = dict.fromkeys(scope, Decimal("1"))
    broker_shares.update({broker_id: Decimal(share) for broker_id, share in (shares or {}).items()})
    classifier = ScopeAwareTransactionClassifier(
        scope_broker_ids=set(scope),
        all_transactions=sorted(txs, key=lambda tx: (tx.date, tx.id)),
        broker_shares=broker_shares,
    )
    return classifier.classify(external_paired=external_paired)


def _mark_series_from(classified_txs, asset_currencies):
    """Mirror PortfolioCalculationEngine: one AssetPriceSeries per asset from its trades (no quote here)."""
    txs_by_asset: dict[int, list] = {}
    for ctxn in classified_txs:
        if ctxn.tx.asset_id is not None:
            txs_by_asset.setdefault(ctxn.tx.asset_id, []).append(ctxn.tx)
    mark_series = {}
    for aid, transactions in txs_by_asset.items():
        series = build_asset_price_series(price_rows=[], transactions=transactions, split_linked_tx_ids=set(), asset_currency=asset_currencies.get(aid, "EUR"), quote_base_quantity=1)
        if series.has_observations:
            mark_series[aid] = series
    return mark_series


def _build(classification, *, date_to: date, fx_rate_map=None) -> PortfolioCalculationResult:
    """Build the states D0..date_to of a classified ledger; every asset is a EUR "Stock" with no classification."""
    fx_rate_map = fx_rate_map or {}
    classified = classification.classified
    asset_ids = {ctxn.tx.asset_id for ctxn in classified if ctxn.tx.asset_id is not None}
    asset_currencies = dict.fromkeys(asset_ids, "EUR")
    return DailyStateBuilder(
        classified_txs=classified,
        in_transit_intervals=classification.in_transit_intervals,
        external_cash_flows=classification.external_cash_flows,
        price_map={},
        quote_base_map={},
        fx_rate_map=fx_rate_map,
        asset_classifications=dict.fromkeys(asset_ids),
        asset_types=dict.fromkeys(asset_ids, "Stock"),
        asset_currencies=asset_currencies,
        mark_series=_mark_series_from(classified, asset_currencies),
        average_costs=engine_average_costs(classified, asset_currencies=asset_currencies, target_currency="EUR", fx_rate_map=fx_rate_map, date_to=date_to),
        native_cash=engine_native_cash(classified, target_currency="EUR", fx_rate_map=fx_rate_map, date_to=date_to),
        target_currency="EUR",
        date_from=D0,
        date_to=date_to,
    ).build()


def _classifications(classification) -> dict[int, str]:
    return {ctxn.tx.id: ctxn.classification for ctxn in classification.classified}


def _breakdown_problems(result: PortfolioCalculationResult, expected: dict[date, tuple[str, str, str]]) -> list[str]:
    """``expected``: {day: (cash, cash_from_contributed_capital, cash_from_generated_returns)}, cash in transit
    included. Collects every mismatch, so a red shows the whole line; and checks that the two halves make the cash."""
    states = {s.date: s for s in result.daily_states}
    problems: list[str] = []
    for day, (cash, contributed, generated) in expected.items():
        state = states.get(day)
        if state is None:
            problems.append(f"{day}: no state emitted")
            continue
        actual = (state.cash_value + state.in_transit_cash_value, state.cash_from_contributed_capital, state.cash_from_generated_returns)
        if actual != (Decimal(cash), Decimal(contributed), Decimal(generated)):
            problems.append(f"{day}: (cash, contributed, generated)=({actual[0]}, {actual[1]}, {actual[2]}), expected ({cash}, {contributed}, {generated})")
        if state.cash_from_contributed_capital + state.cash_from_generated_returns != actual[0]:
            problems.append(f"{day}: contributed + generated = {state.cash_from_contributed_capital + state.cash_from_generated_returns} != cash {actual[0]}")
    return problems


def _pool_problems(result: PortfolioCalculationResult, capital: dict[int, str], returns: dict[int, str]) -> list[str]:
    """Each broker's K and R after the last day (``end_state``); a broker the replay never touched counts as 0."""
    problems: list[str] = []
    for label, pool, expected in (("K", result.end_state.capital_pool, capital), ("R", result.end_state.returns_pool, returns)):
        for broker_id, value in expected.items():
            actual = pool.get(broker_id, Decimal("0"))
            if actual != Decimal(value):
                problems.append(f"{label}[{broker_id}]={actual}, expected {value}")
    return problems


def _baseline_problems(result: PortfolioCalculationResult, expected: dict[date, str]) -> list[str]:
    """``expected``: {day: capital baseline}; the contributed cash must equal it (``cumulative_external_cash_flow``)."""
    states = {s.date: s for s in result.daily_states}
    problems: list[str] = []
    for day, baseline in expected.items():
        state = states[day]
        if state.cumulative_external_cash_flow != Decimal(baseline):
            problems.append(f"{day}: cumulative_external_cash_flow={state.cumulative_external_cash_flow}, expected {baseline}")
        if state.cash_from_contributed_capital != state.cumulative_external_cash_flow:
            problems.append(f"{day}: contributed {state.cash_from_contributed_capital} != capital baseline {state.cumulative_external_cash_flow}")
    return problems


def _returns_by_income() -> list[MagicMock]:
    """A deposits 1000 on D0 and earns 300 of INTEREST on D1: K_A 1000, R_A 300."""
    return [_tx(id=1, dt=D0, amount="1000"), _tx(id=2, type="INTEREST", dt=D1, amount="300")]


def _returns_by_realized_gain() -> list[MagicMock]:
    """A deposits 1000 and buys 5 X for 500 on D0, sells them for 800 on D1 (cost 500, gain 300): K_A 1000, R_A 300."""
    return [
        _tx(id=1, dt=D0, amount="1000"),
        _tx(id=2, type="BUY", dt=D0, amount="-500", quantity="5", asset_id=X),
        _tx(id=3, type="SELL", dt=D1, amount="800", quantity="-5", asset_id=X),
    ]


# =============================================================================
# 1 — CASH TRANSFER BETWEEN TWO BROKERS, ONE DAY
# =============================================================================


class TestCrossBrokerCashTransfer:
    """A holds K 1000 and R 300 on D1; a linked CASH_TRANSFER moves cash A -> B on D2 (date_to D3)."""

    @pytest.mark.parametrize("returns_ledger", [pytest.param(_returns_by_income, id="interest"), pytest.param(_returns_by_realized_gain, id="realized_gain")])
    def test_the_returns_travel_with_the_cash(self, returns_ledger):
        """650 leaves A from R 300 then K 350, and arrives at B as R 300 / K 350 (same amount: no gap).

        J2: from D2 the scope reads contributed 1000 / generated 300 of a cash of 1300; K {A 650, B 350}, R {A 0, B 300}.
        HEAD: contributed 1300 / generated 0 from D2; K {A 650, B 650}, R {A 0, B 0}.
        """
        out_leg, in_leg = _cash_pair(4, 5, sender=A, receiver=B, out_dt=D2, in_dt=D2, out_amount="650", in_amount="650")
        classification = _classify([*returns_ledger(), out_leg, in_leg], {A, B})
        assert _classifications(classification)[4] == _classifications(classification)[5] == "linked_internal"
        assert classification.in_transit_intervals == []

        result = _build(classification, date_to=D3)

        problems = _breakdown_problems(result, {D1: ("1300", "1000", "300"), D2: ("1300", "1000", "300"), D3: ("1300", "1000", "300")})
        problems += _pool_problems(result, capital={A: "650", B: "350"}, returns={A: "0", B: "300"})
        assert not problems, "\n".join(problems)
        assert result.end_state.cumulative_cash_by_broker == {A: Decimal("650"), B: Decimal("650")}
        assert result.end_state.cumulative_ecf == Decimal("1000"), "an internal transfer is not capital"

    def test_a_departure_within_the_returns_arrives_as_returns_only(self):
        """200 leaves A entirely from R (300): R_A 100, K_A 1000; B receives R 200, K 0.

        J2: contributed 1000 / generated 300 from D2. HEAD: 1200 / 100, K_B 200, R_B 0.
        """
        out_leg, in_leg = _cash_pair(4, 5, sender=A, receiver=B, out_dt=D2, in_dt=D2, out_amount="200", in_amount="200")
        result = _build(_classify([*_returns_by_income(), out_leg, in_leg], {A, B}), date_to=D3)

        problems = _breakdown_problems(result, {D2: ("1300", "1000", "300"), D3: ("1300", "1000", "300")})
        problems += _pool_problems(result, capital={A: "1000", B: "0"}, returns={A: "100", B: "200"})
        assert not problems, "\n".join(problems)

    def test_a_round_trip_brings_the_returns_back(self):
        """A -> B 650 on D2 (R 300 travels), B -> A 500 on D3: B leaves R 300 then K 200, A receives R 300 / K 200.

        J2: K {A 850, B 150}, R {A 300, B 0}; contributed 1000 / generated 300 on D2 and D3.
        HEAD: K {A 1150, B 150}, R {A 0, B 0}; 1300 / 0 on D2 and D3.
        """
        a_out, b_in = _cash_pair(4, 5, sender=A, receiver=B, out_dt=D2, in_dt=D2, out_amount="650", in_amount="650")
        b_out, a_in = _cash_pair(6, 7, sender=B, receiver=A, out_dt=D3, in_dt=D3, out_amount="500", in_amount="500")
        result = _build(_classify([*_returns_by_income(), a_out, b_in, b_out, a_in], {A, B}), date_to=D3)

        problems = _breakdown_problems(result, {D2: ("1300", "1000", "300"), D3: ("1300", "1000", "300")})
        problems += _pool_problems(result, capital={A: "850", B: "150"}, returns={A: "300", B: "0"})
        assert not problems, "\n".join(problems)


# =============================================================================
# 2 — CURRENCY CONVERSION AT ONE BROKER
# =============================================================================


class TestSameBrokerFxConversion:
    """A holds K 1000 and R 300 (EUR) on D1; on D2 it converts 650 EUR into USD (USD->EUR 0.92 on D2, 0.94 on D3).
    The departure leaves R 300 then K 350; the arrival brings K 350 back, and R 300 plus the gap between the two legs."""

    def _result(self, usd_received: str):
        out_leg, in_leg = _cash_pair(3, 4, sender=A, receiver=A, out_dt=D2, in_dt=D2, out_amount="650", in_amount=usd_received, in_currency="USD", type="FX_CONVERSION")
        classification = _classify([*_returns_by_income(), out_leg, in_leg], {A})
        assert _classifications(classification) == {1: "normal", 2: "normal", 3: "linked_internal", 4: "linked_internal"}
        return _build(classification, date_to=D3, fx_rate_map=_usd_rates({D2: "0.92", D3: "0.94"}))

    def test_a_conversion_gain_is_a_result_not_capital(self):
        """715 USD arrive as 657.80 EUR at D2's rate: 7.80 more than the 650 that left. K gets its 350 back (1000), R
        its 300 plus the 7.80 (307.80). On D3 the rate moves to 0.94: the 715 USD revalue by +14.30, an exchange
        result, into R (322.10). Contributed stays the capital baseline, the 1000 deposited: a conversion adds none.

        J2: D2 cash 1307.80 = contributed 1000 + generated 307.80; D3 1322.10 = 1000 + 322.10.
        HEAD: D2 1307.80 = 1307.80 + 0; D3 1322.10 = 1307.80 + 14.30.
        """
        result = self._result("715")

        problems = _breakdown_problems(result, {D1: ("1300", "1000", "300"), D2: ("1307.80", "1000", "307.80"), D3: ("1322.10", "1000", "322.10")})
        problems += _pool_problems(result, capital={A: "1000"}, returns={A: "322.10"})
        problems += _baseline_problems(result, {D2: "1000", D3: "1000"})
        assert not problems, "\n".join(problems)

    def test_a_conversion_loss_comes_out_of_the_returns(self):
        """690 USD arrive as 634.80 EUR at D2's rate: 15.20 less than the 650 that left. K gets its 350 back (1000), R
        its 300 less the 15.20 (284.80). On D3 the 690 USD revalue at 0.94 by +13.80, into R (298.60).

        J2: D2 cash 1284.80 = contributed 1000 + generated 284.80; D3 1298.60 = 1000 + 298.60.
        HEAD: D2 1284.80 = 1284.80 + 0; D3 1298.60 = 1284.80 + 13.80.
        """
        result = self._result("690")

        problems = _breakdown_problems(result, {D2: ("1284.80", "1000", "284.80"), D3: ("1298.60", "1000", "298.60")})
        problems += _pool_problems(result, capital={A: "1000"}, returns={A: "298.60"})
        problems += _baseline_problems(result, {D2: "1000", D3: "1000"})
        assert not problems, "\n".join(problems)


# =============================================================================
# 2b — A CONVERSION LOSS LARGER THAN THE RETURNS
# =============================================================================


def _small_returns() -> list[MagicMock]:
    """A deposits 1000 on D0 and earns 10 of INTEREST on D1: K_A 1000, R_A 10."""
    return [_tx(id=1, dt=D0, amount="1000"), _tx(id=2, type="INTEREST", dt=D1, amount="10")]


class TestConversionLossBeyondTheReturns:
    """On D2 650 EUR are converted into 690 USD at 0.92 = 634.80 EUR: a loss of 15.20, more than the 10 of returns the
    departure takes. Like a FEE, the loss empties R and the remaining 5.20 comes out of K."""

    def test_at_one_broker_capital_absorbs_the_rest(self):
        """A: K 1000, R 10. The departure leaves R 10 then K 640 (K 360, R 0); the arrival brings K 640 back (1000) and
        R 10 - 15.20 = -5.20, which K absorbs: K 994.80, R 0. Cash 1010 - 650 + 634.80 = 994.80, all contributed.

        Parity pin: at one broker the departure has already drained R, so the arrival all into K (HEAD) lands on the
        same K 994.80 / R 0 (both are K0 + R0 + gap).
        """
        out_leg, in_leg = _cash_pair(3, 4, sender=A, receiver=A, out_dt=D2, in_dt=D2, out_amount="650", in_amount="690", in_currency="USD", type="FX_CONVERSION")
        result = _build(_classify([*_small_returns(), out_leg, in_leg], {A}), date_to=D2, fx_rate_map=_usd_rates({D2: "0.92"}))

        problems = _breakdown_problems(result, {D1: ("1010", "1000", "10"), D2: ("994.80", "994.80", "0")})
        problems += _pool_problems(result, capital={A: "994.80"}, returns={A: "0"})
        assert not problems, "\n".join(problems)

    def test_the_loss_also_takes_the_receivers_own_returns(self):
        """The conversion goes A -> B, and B holds K 100, R 3 of its own (DEPOSIT 100, INTEREST 3). A leaves R 10 then
        K 640 (K_A 360, R_A 0); at B the arrival brings K 640 back and R 10 - 15.20: R_B = 3 + 10 - 15.20 = -2.20, which
        K_B absorbs: K_B = 100 + 640 - 2.20 = 737.80, R_B 0. Cash 1113 - 650 + 634.80 = 1097.80, all contributed.

        J2: D2 contributed 1097.80 / generated 0; K {A 360, B 737.80}, R {A 0, B 0}.
        HEAD: D2 contributed 1094.80 / generated 3; K {A 360, B 734.80}, R {A 0, B 3}.
        """
        b_ledger = [_tx(id=5, broker_id=B, dt=D0, amount="100"), _tx(id=6, broker_id=B, type="INTEREST", dt=D1, amount="3")]
        out_leg, in_leg = _cash_pair(7, 8, sender=A, receiver=B, out_dt=D2, in_dt=D2, out_amount="650", in_amount="690", in_currency="USD", type="FX_CONVERSION")
        classification = _classify([*_small_returns(), *b_ledger, out_leg, in_leg], {A, B})
        assert _classifications(classification)[7] == _classifications(classification)[8] == "linked_internal"

        result = _build(classification, date_to=D2, fx_rate_map=_usd_rates({D2: "0.92"}))

        problems = _breakdown_problems(result, {D1: ("1113", "1100", "13"), D2: ("1097.80", "1097.80", "0")})
        problems += _pool_problems(result, capital={A: "360", B: "737.80"}, returns={A: "0", B: "0"})
        assert not problems, "\n".join(problems)


# =============================================================================
# 2c — BROKERS OWNED AT DIFFERENT SHARES
# =============================================================================


def _pnl_problems(result: PortfolioCalculationResult, expected: dict[date, tuple[str, str]]) -> list[str]:
    """``expected``: {day: (capital baseline, total P&L)} of the scope."""
    states = {s.date: s for s in result.daily_states}
    problems: list[str] = []
    for day, (baseline, pnl) in expected.items():
        state = states[day]
        if (state.cumulative_external_cash_flow, state.total_pnl) != (Decimal(baseline), Decimal(pnl)):
            problems.append(f"{day}: (baseline, total_pnl)=({state.cumulative_external_cash_flow}, {state.total_pnl}), expected ({baseline}, {pnl})")
    return problems


class TestBrokersOwnedAtDifferentShares:
    """A is owned at 100 %, B at 50 %. Every leg is weighted by its own broker's share (``ClassifiedTransaction.share``,
    the classifier's ``broker_shares``), so 400 EUR moved between them are worth ``sent`` = 400 x s_sender and
    ``amount`` = 400 x s_receiver in the scope. Neither leg is an external flow: the capital baseline does not move, and
    the scope's total P&L moves by the gap on the arrival day. J2 books that gap as a result — R, then K for a loss
    beyond R — so the generated cash follows the P&L.

    Departure and arrival on different days: the cash in transit is valued at the departure broker's share
    (``interval.share``, which the classifier sets from ``broker_shares``), so the full ``sent`` stays in transit and
    the gap appears on the arrival day, booked by the same arrival rule as here.
    """

    def test_a_loss_comes_out_of_the_returns_moved(self):
        """A (K 1000, R 300: DEPOSIT 1000, INTEREST 300) sends 400 to B (empty) on D2: sent 400 x 1, amount 400 x 0.5 =
        200, gap -200. A leaves R 300 then K 100 (K_A 900, R_A 0); B gets K 100 back and R 300 - 200 = 100. The gap
        (-200) is within the returns moved (300): generated stays positive, 100, and equals the total P&L (1100 - 1000).

        J2: D2 cash 1100 = contributed 1000 + generated 100; K {A 900, B 100}, R {A 0, B 100}.
        HEAD: D2 1100 = 1100 + 0 (all 200 into K_B); K {A 900, B 200}, R {A 0, B 0}: generated 0 against a P&L of +100.
        """
        out_leg, in_leg = _cash_pair(3, 4, sender=A, receiver=B, out_dt=D2, in_dt=D2, out_amount="400", in_amount="400")
        classification = _classify([*_returns_by_income(), out_leg, in_leg], {A, B}, shares={B: "0.5"})
        assert [(ctxn.tx.id, ctxn.classification, ctxn.share) for ctxn in classification.classified if ctxn.tx.id in (3, 4)] == [(3, "linked_internal", Decimal("1")), (4, "linked_internal", Decimal("0.5"))]

        result = _build(classification, date_to=D3)

        problems = _breakdown_problems(result, {D1: ("1300", "1000", "300"), D2: ("1100", "1000", "100"), D3: ("1100", "1000", "100")})
        problems += _pool_problems(result, capital={A: "900", B: "100"}, returns={A: "0", B: "100"})
        problems += _pnl_problems(result, {D1: ("1000", "300"), D2: ("1000", "100"), D3: ("1000", "100")})
        assert not problems, "\n".join(problems)
        assert result.end_state.cumulative_cash_by_broker == {A: Decimal("900"), B: Decimal("200")}

    def test_a_loss_beyond_the_returns_moved_comes_out_of_capital(self):
        """Parity pin. The same transfer with A at K 1000, R 100 (INTEREST 100): A leaves R 100 then K 300 (K_A 700); at B
        K 300 back and R 100 - 200 = -100, which K_B absorbs: K_B 200, R_B 0. Generated 0, contributed 900 = cash, and
        the P&L is -100 (900 - 1000). HEAD lands on the same pools: the receiver had no returns of its own, and the
        departure took all of A's."""
        out_leg, in_leg = _cash_pair(3, 4, sender=A, receiver=B, out_dt=D2, in_dt=D2, out_amount="400", in_amount="400")
        ledger = [_tx(id=1, dt=D0, amount="1000"), _tx(id=2, type="INTEREST", dt=D1, amount="100")]
        result = _build(_classify([*ledger, out_leg, in_leg], {A, B}, shares={B: "0.5"}), date_to=D3)

        problems = _breakdown_problems(result, {D1: ("1100", "1000", "100"), D2: ("900", "900", "0"), D3: ("900", "900", "0")})
        problems += _pool_problems(result, capital={A: "700", B: "200"}, returns={A: "0", B: "0"})
        problems += _pnl_problems(result, {D2: ("1000", "-100")})
        assert not problems, "\n".join(problems)

    def test_a_gain_goes_to_returns(self):
        """B (share 0.5) deposits 1000 and earns 200 of INTEREST: K_B 500, R_B 100 in the scope. On D2 B sends 400 to A
        (share 1, empty): sent 400 x 0.5 = 200, amount 400 x 1 = 400, gap +200. B leaves R 100 then K 100 (K_B 400,
        R_B 0); A gets K 100 back and R 100 + 200 = 300. Generated 300 = the total P&L (800 - 500).

        J2: D2 cash 800 = contributed 500 + generated 300; K {A 100, B 400}, R {A 300, B 0}.
        HEAD: D2 800 = 800 + 0 (all 400 into K_A); K {A 400, B 400}, R {A 0, B 0}: generated 0 against a P&L of +300.
        """
        b_ledger = [_tx(id=1, broker_id=B, dt=D0, amount="1000"), _tx(id=2, broker_id=B, type="INTEREST", dt=D1, amount="200")]
        out_leg, in_leg = _cash_pair(3, 4, sender=B, receiver=A, out_dt=D2, in_dt=D2, out_amount="400", in_amount="400")
        classification = _classify([*b_ledger, out_leg, in_leg], {A, B}, shares={B: "0.5"})
        assert [(ctxn.tx.id, ctxn.classification, ctxn.share) for ctxn in classification.classified if ctxn.tx.id in (3, 4)] == [(3, "linked_internal", Decimal("0.5")), (4, "linked_internal", Decimal("1"))]

        result = _build(classification, date_to=D3)

        problems = _breakdown_problems(result, {D1: ("600", "500", "100"), D2: ("800", "500", "300"), D3: ("800", "500", "300")})
        problems += _pool_problems(result, capital={A: "100", B: "400"}, returns={A: "300", B: "0"})
        problems += _pnl_problems(result, {D1: ("500", "100"), D2: ("500", "300"), D3: ("500", "300")})
        assert not problems, "\n".join(problems)
        assert result.end_state.cumulative_cash_by_broker == {A: Decimal("400"), B: Decimal("400")}


# =============================================================================
# 3 — CASH IN TRANSIT
# =============================================================================


def _transit_ledger():
    """A: K 1000, R 300 on D0 (DEPOSIT + INTEREST); 650 EUR leave A on D1 and reach B on D3 (in transit D1-D2)."""
    out_leg, in_leg = _cash_pair(3, 4, sender=A, receiver=B, out_dt=D1, in_dt=D3, out_amount="650", in_amount="650")
    classification = _classify([_tx(id=1, dt=D0, amount="1000"), _tx(id=2, type="INTEREST", dt=D0, amount="300"), out_leg, in_leg], {A, B})
    assert [(it.start_date, it.end_date, it.tx_type) for it in classification.in_transit_intervals] == [(D1, D2, "cash")]
    return classification


class TestCashInTransit:
    def test_the_arrival_brings_the_returns_back(self):
        """On D3 the arrival takes up the departure's split, recorded on D1: B receives R 300 / K 350.

        J2: contributed 1000 / generated 300 on D3 and D4; K {A 650, B 350}, R {A 0, B 300}.
        HEAD: 1300 / 0 on D3 and D4; K {A 650, B 650}, R {A 0, B 0}.
        """
        result = _build(_transit_ledger(), date_to=D4)

        problems = _breakdown_problems(result, {D0: ("1300", "1000", "300"), D3: ("1300", "1000", "300"), D4: ("1300", "1000", "300")})
        problems += _pool_problems(result, capital={A: "650", B: "350"}, returns={A: "0", B: "300"})
        assert not problems, "\n".join(problems)

    def test_in_transit_the_rescale_reads_the_cash_as_capital(self):
        """Parity pin, unchanged by J2. On D1-D2 the 650 in transit are in no pool: K 650 (A) and R 0 against a cash of
        1300 (650 at A + 650 in transit). The pools differ from the cash by more than 0.01, so the breakdown rescales
        them: scale = 1300 / 650 = 2, contributed = K x 2 = 1300, generated = 1300 - 1300 = 0. The 300 of returns in
        flight read as capital until the arrival brings them back (the test above).
        """
        result = _build(_transit_ledger(), date_to=D4)

        states = {s.date: s for s in result.daily_states}
        assert [states[day].in_transit_cash_value for day in (D1, D2)] == [Decimal("650"), Decimal("650")]
        problems = _breakdown_problems(result, {D1: ("1300", "1300", "0"), D2: ("1300", "1300", "0")})
        assert not problems, "\n".join(problems)


# =============================================================================
# 4 — SAME DAY, THE ARRIVAL'S ID BEFORE THE DEPARTURE'S
# =============================================================================


class TestSameDayArrivalBeforeItsDeparture:
    def test_the_arrival_is_processed_after_its_departure(self):
        """The arrival (id 3, at B) loads before its departure (id 4, at A) on D1: the day still processes the
        departure first, so the arrival finds its split. A: K 1000, R 300 on D0; 650 move A -> B on D1.

        J2: contributed 1000 / generated 300 on D1 and D2; K {A 650, B 350}, R {A 0, B 300}.
        HEAD: 1300 / 0; K {A 650, B 650}, R {A 0, B 0} (the arrival, first, found no split).
        """
        out_leg, in_leg = _cash_pair(4, 3, sender=A, receiver=B, out_dt=D1, in_dt=D1, out_amount="650", in_amount="650")
        classification = _classify([_tx(id=1, dt=D0, amount="1000"), _tx(id=2, type="INTEREST", dt=D0, amount="300"), out_leg, in_leg], {A, B})
        assert [ctxn.tx.id for ctxn in classification.classified if ctxn.tx.date == D1] == [3, 4], "precondition: the arrival loads first"
        assert _classifications(classification)[3] == _classifications(classification)[4] == "linked_internal"

        result = _build(classification, date_to=D2)

        problems = _breakdown_problems(result, {D1: ("1300", "1000", "300"), D2: ("1300", "1000", "300")})
        problems += _pool_problems(result, capital={A: "650", B: "350"}, returns={A: "0", B: "300"})
        assert not problems, "\n".join(problems)


# =============================================================================
# 5 — AN ARRIVAL WHOSE DEPARTURE IS UNKNOWN
# =============================================================================


class TestArrivalWithoutKnownDeparture:
    """Parity pins: green before and after J2."""

    def test_a_departure_without_amount_carries_nothing(self):
        """Broken data: the departure leg (id 3, at A) has amount 0, so the replay skips it and records no split; its
        arrival (+650 at B) is all capital. A keeps K 1000 / R 300, B gets K 650: cash 1950 = 1650 + 300.
        """
        out_leg, in_leg = _cash_pair(3, 4, sender=A, receiver=B, out_dt=D1, in_dt=D1, out_amount="0", in_amount="650")
        classification = _classify([_tx(id=1, dt=D0, amount="1000"), _tx(id=2, type="INTEREST", dt=D0, amount="300"), out_leg, in_leg], {A, B})
        assert _classifications(classification)[3] == _classifications(classification)[4] == "linked_internal"

        result = _build(classification, date_to=D2)

        problems = _breakdown_problems(result, {D1: ("1950", "1650", "300"), D2: ("1950", "1650", "300")})
        problems += _pool_problems(result, capital={A: "1000", B: "650"}, returns={A: "300", B: "0"})
        assert not problems, "\n".join(problems)

    def test_an_arrival_from_outside_the_scope_takes_no_returns(self):
        """Scope {B}: the departure (at A, whatever returns A holds) is outside it, so the classifier makes the arrival
        a ``linked_external_inflow`` — capital entering the scope, never a linked-internal leg: it consults no split.
        B deposited 100 on D0; the 650 arrive on D1: R_B 0, and the breakdown (pools 100 against a cash of 750,
        rescaled x 7.5) reads contributed 750 / generated 0.
        """
        out_leg, in_leg = _cash_pair(3, 4, sender=A, receiver=B, out_dt=D1, in_dt=D1, out_amount="650", in_amount="650")
        b_deposit = _tx(id=5, broker_id=B, dt=D0, amount="100")
        classification = _classify([b_deposit, in_leg], {B}, external_paired={3: out_leg})
        assert _classifications(classification) == {5: "normal", 4: "linked_external_inflow"}

        result = _build(classification, date_to=D2)

        problems = _breakdown_problems(result, {D1: ("750", "750", "0"), D2: ("750", "750", "0")})
        problems += _pool_problems(result, capital={}, returns={B: "0"})
        assert not problems, "\n".join(problems)
        assert result.end_state.cumulative_ecf == Decimal("750")


# =============================================================================
# 6 — A DEPARTURE WITHOUT RETURNS
# =============================================================================


class TestDepartureWithoutReturns:
    def test_the_arrival_is_all_capital(self):
        """Parity pin. A deposits 1000 on D0 (R 0) and sends 650 to B on D1: the departure leaves K only, the arrival
        brings back K 650 and R 0. K {A 350, B 650}, R 0; contributed 1000 / generated 0.
        """
        out_leg, in_leg = _cash_pair(3, 4, sender=A, receiver=B, out_dt=D1, in_dt=D1, out_amount="650", in_amount="650")
        result = _build(_classify([_tx(id=1, dt=D0, amount="1000"), out_leg, in_leg], {A, B}), date_to=D2)

        problems = _breakdown_problems(result, {D1: ("1000", "1000", "0"), D2: ("1000", "1000", "0")})
        problems += _pool_problems(result, capital={A: "350", B: "650"}, returns={A: "0", B: "0"})
        assert not problems, "\n".join(problems)


# =============================================================================
# 7 — _move_linked_cash / _apply_pool_rule(..., transfer_splits), PURE
# =============================================================================


def _pools(capital: dict[int, str], returns: dict[int, str]) -> tuple[defaultdict, defaultdict]:
    """K and R as the replay holds them (defaultdicts)."""
    return defaultdict(Decimal, {bid: Decimal(v) for bid, v in capital.items()}), defaultdict(Decimal, {bid: Decimal(v) for bid, v in returns.items()})


def _legs(tx_type: str = "CASH_TRANSFER", *, out_id: int | None = 3, in_id: int = 4, out_amount: str = "60", in_amount: str = "60") -> tuple[ClassifiedTransaction, ClassifiedTransaction]:
    """A linked-internal pair A -> B, each leg classified with the other as its ``paired_tx``."""
    out_tx = _tx(id=out_id, broker_id=A, type=tx_type, dt=D1, amount=f"-{out_amount}", related_id=in_id)
    in_tx = _tx(id=in_id, broker_id=B, type=tx_type, dt=D1, amount=in_amount, related_id=out_id)
    return _ctxn(out_tx, "linked_internal", paired=in_tx), _ctxn(in_tx, "linked_internal", paired=out_tx)


def _move(ctxn: ClassifiedTransaction, amount: str, capital, returns, splits) -> None:
    daily_state_module._move_linked_cash(ctxn, Decimal(amount), capital, returns, splits)


def _d(value: str) -> Decimal:
    return Decimal(value)


class TestMoveLinkedCash:
    """``_move_linked_cash(ctxn, amount, K, R, transfer_splits)``: ``amount`` is the leg's absolute value in the
    target currency, the direction is the sign of ``tx.amount``."""

    def test_a_departure_leaves_returns_first_and_records_its_split(self):
        capital, returns = _pools({A: "100"}, {A: "40"})
        splits: dict = {}
        _move(_legs()[0], "60", capital, returns, splits)
        assert (capital[A], returns[A], splits) == (_d("80"), _d("0"), {3: (_d("40"), _d("60"))})

    def test_a_departure_reads_a_negative_returns_pool_as_zero(self):
        """R below zero (a negative income correction, before the day's clamp) gives nothing: all 60 from K."""
        capital, returns = _pools({A: "100"}, {A: "-5"})
        splits: dict = {}
        _move(_legs()[0], "60", capital, returns, splits)
        assert (capital[A], returns[A], splits) == (_d("40"), _d("-5"), {3: (_d("0"), _d("60"))})

    def test_an_arrival_brings_back_each_pool_and_the_gap_goes_to_returns(self):
        """Departure 60 with 40 from R (20 from K); the arrival is worth 90: K += 20, R += 40 + (90 - 60) = 70. The split
        is used up, another departure's stays."""
        capital, returns = _pools({B: "7"}, {B: "3"})
        splits = {3: (_d("40"), _d("60")), 99: (_d("1"), _d("2"))}
        _move(_legs(in_amount="90")[1], "90", capital, returns, splits)
        assert (capital[B], returns[B], splits) == (_d("27"), _d("73"), {99: (_d("1"), _d("2"))})

    def test_a_loss_within_the_returns_comes_out_of_them(self):
        """Departure (40, 60), arrival 50: K += 20, R += 40 - 10 = 30."""
        capital, returns = _pools({B: "7"}, {B: "3"})
        _move(_legs(in_amount="50")[1], "50", capital, returns, {3: (_d("40"), _d("60"))})
        assert (capital[B], returns[B]) == (_d("27"), _d("33"))

    @pytest.mark.parametrize(
        ("returns_before", "capital_after"),
        [
            pytest.param("0", "10", id="receiver_without_returns"),
            pytest.param("5", "15", id="receiver_with_returns_5"),
        ],
    )
    def test_a_loss_beyond_the_returns_comes_out_of_capital_like_a_fee(self, returns_before, capital_after):
        """Departure (40, 60), arrival 10: K += 20, R += 40 - 50 = -10 on top of the receiver's own R. Whatever R cannot
        cover comes out of K, and R ends at 0: K += 10 (R_before 0) or K += 15 (R_before 5). Net +10 either way, the
        arrival's worth."""
        capital, returns = _pools({B: "0"}, {B: returns_before})
        _move(_legs(in_amount="10")[1], "10", capital, returns, {3: (_d("40"), _d("60"))})
        assert (capital[B], returns[B]) == (_d(capital_after), _d("0"))
        assert capital[B] + returns[B] - _d(returns_before) == _d("10")

    def test_the_whole_pair_moves_the_returns_and_keeps_the_total(self):
        capital, returns = _pools({A: "100"}, {A: "40"})
        splits: dict = {}
        out_leg, in_leg = _legs()
        _move(out_leg, "60", capital, returns, splits)
        _move(in_leg, "60", capital, returns, splits)
        assert (capital[A], returns[A], capital[B], returns[B], splits) == (_d("80"), _d("0"), _d("20"), _d("40"), {})
        assert capital[A] + returns[A] + capital[B] + returns[B] == _d("140")

    def test_an_arrival_whose_departure_is_unknown_lands_in_capital(self):
        capital, returns = _pools({B: "7"}, {B: "3"})
        splits = {99: (_d("1"), _d("2"))}
        _move(_legs()[1], "60", capital, returns, splits)
        assert (capital[B], returns[B], splits) == (_d("67"), _d("3"), {99: (_d("1"), _d("2"))})

    def test_a_split_is_taken_up_once(self):
        """A second arrival naming the same departure finds nothing left: all of it into K."""
        capital, returns = _pools({}, {})
        splits = {3: (_d("40"), _d("60"))}
        in_leg = _legs()[1]
        _move(in_leg, "60", capital, returns, splits)
        _move(in_leg, "60", capital, returns, splits)
        assert (capital[B], returns[B]) == (_d("80"), _d("40"))

    def test_a_zero_departure_amount_lands_its_arrival_in_capital(self):
        """A departure worth 0 in the target currency records (0, 0); its arrival is all capital: nothing to bring back."""
        capital, returns = _pools({A: "100"}, {A: "40"})
        splits: dict = {}
        out_leg, in_leg = _legs()
        _move(out_leg, "0", capital, returns, splits)
        assert splits == {3: (_d("0"), _d("0"))}
        _move(in_leg, "60", capital, returns, splits)
        assert (capital[A], returns[A], capital[B], returns[B], splits) == (_d("100"), _d("40"), _d("60"), _d("0"), {})

    def test_a_recorded_zero_amount_is_guarded(self):
        """Even a split (x, 0) recorded by hand: the arrival is all capital, the x is not brought back."""
        capital, returns = _pools({}, {})
        _move(_legs()[1], "60", capital, returns, {3: (_d("5"), _d("0"))})
        assert (capital[B], returns[B]) == (_d("60"), _d("0"))

    def test_without_a_splits_dict_the_arrival_lands_in_capital(self):
        """``transfer_splits=None`` is the rule before J2: departure R first, arrival all K, nothing recorded."""
        capital, returns = _pools({A: "100"}, {A: "40"})
        out_leg, in_leg = _legs()
        _move(out_leg, "60", capital, returns, None)
        _move(in_leg, "60", capital, returns, None)
        assert (capital[A], returns[A], capital[B], returns[B]) == (_d("80"), _d("0"), _d("60"), _d("0"))

    def test_a_departure_without_id_records_nothing(self):
        capital, returns = _pools({A: "100"}, {A: "40"})
        splits: dict = {}
        _move(_legs(out_id=None)[0], "60", capital, returns, splits)
        assert (capital[A], returns[A], splits) == (_d("80"), _d("0"), {})

    def test_an_arrival_without_paired_leg_lands_in_capital(self):
        capital, returns = _pools({}, {})
        in_leg = _ctxn(_tx(id=4, broker_id=B, type="CASH_TRANSFER", dt=D1, amount="60", related_id=3), "linked_internal", paired=None)
        splits = {3: (_d("40"), _d("60"))}
        _move(in_leg, "60", capital, returns, splits)
        assert (capital[B], returns[B], splits) == (_d("60"), _d("0"), {3: (_d("40"), _d("60"))})


class TestApplyPoolRuleWithSplits:
    """``_apply_pool_rule(ctxn, amount, K, R, withdrawn, transfer_splits)`` routes the linked-internal cash legs."""

    @pytest.mark.parametrize("tx_type", ["CASH_TRANSFER", "FX_CONVERSION"])
    def test_a_linked_internal_pair_brings_back_each_pool(self, tx_type):
        """Departure 60 (40 from R) at A, arrival 90 at B: K_B += 20, R_B += 40 + 30 = 70. Withdrawn and the BUY split
        untouched."""
        capital, returns = _pools({A: "100", B: "0"}, {A: "40", B: "0"})
        splits: dict = {}
        out_leg, in_leg = _legs(tx_type, in_amount="90")
        after_out = DailyStateBuilder._apply_pool_rule(out_leg, _d("60"), capital, returns, _d("5"), splits)
        assert splits == {3: (_d("40"), _d("60"))}
        after_in = DailyStateBuilder._apply_pool_rule(in_leg, _d("90"), capital, returns, _d("5"), splits)
        assert after_out == after_in == (_d("5"), _d("0"), _d("0"))
        assert (capital[A], returns[A], capital[B], returns[B], splits) == (_d("80"), _d("0"), _d("20"), _d("70"), {})

    @pytest.mark.parametrize("tx_type", ["CASH_TRANSFER", "FX_CONVERSION"])
    @pytest.mark.parametrize("classification", ["normal", "linked_external_inflow", "linked_external_outflow"])
    @pytest.mark.parametrize("signed_amount", ["60", "-60"])
    def test_a_leg_that_is_not_linked_internal_neither_records_nor_takes_up_a_split(self, tx_type, classification, signed_amount):
        capital, returns = _pools({A: "100"}, {A: "40"})
        splits = {4: (_d("40"), _d("60"))}
        paired = _tx(id=4, broker_id=B, type=tx_type, dt=D1, amount="60")
        ctxn = _ctxn(_tx(id=3, type=tx_type, dt=D1, amount=signed_amount, related_id=4), classification, paired=paired)
        assert DailyStateBuilder._apply_pool_rule(ctxn, _d("60"), capital, returns, _d("5"), splits) == (_d("5"), _d("0"), _d("0"))
        assert (capital[A], returns[A], splits) == (_d("100"), _d("40"), {4: (_d("40"), _d("60"))})

    def test_other_movements_ignore_the_splits(self):
        capital, returns = _pools({A: "100"}, {A: "40"})
        splits = {3: (_d("40"), _d("60"))}
        DailyStateBuilder._apply_pool_rule(_ctxn(_tx(id=7, type="DEPOSIT", amount="60")), _d("60"), capital, returns, _d("0"), splits)
        DailyStateBuilder._apply_pool_rule(_ctxn(_tx(id=8, type="INTEREST", amount="10")), _d("10"), capital, returns, _d("0"), splits)
        assert (capital[A], returns[A], splits) == (_d("160"), _d("50"), {3: (_d("40"), _d("60"))})
