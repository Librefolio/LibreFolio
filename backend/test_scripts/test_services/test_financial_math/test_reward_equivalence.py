"""THE GOLDEN TEST of project 79, STK-1: a REWARD is worth exactly a DIVIDEND of V reinvested the same day in a BUY.

Ledger A holds DEPOSIT, BUY, REWARD (q units at V/q, no cash) and a later SELL; ledger B holds the same with a
DIVIDEND of V plus a BUY of q at V/q on the REWARD's day instead. The portfolio replay (``DailyStateBuilder``, with the
average costs and native cash ``calculate()`` would hand it) must read every day the same NAV, cash, capital, total
P&L and open cost — the whole daily state and the end positions — the same realized sales, the same income and the
same period identity — and the same K/R pool split (cash from contributed capital vs generated returns): since STK1-1
the day's cash income replays before its position rows, so the pair's dividend reaches R before its BUY draws on it, as
the REWARD's rule says (Q-C: "R += V, then the BUY draws V from R" leaves K and R unchanged). Only the acquisition
funding differs, by construction: the pair's BUY is a purchase reinvesting V, the REWARD buys nothing. A has no
funding on the reward day, and its cash split equals that of ledger C, the same ledger with neither the reward nor the
pair, up to the day before the SELL.

``TestDividendReinvestedSameDay`` is the developer's example of STK1-1 (P-21, 24/11/2026): deposit 1 000 €, an ETF
bought for 900 €, then a 30 € DIVIDEND (or INTEREST) reinvested the same day in a 30 € BUY.

Three variants: EUR at share 1, EUR at an owner share of 0.4, and the asset, cash and reward in USD with a USD→EUR
rate map. Also: the average cost of a REWARD of explicit value 0 (Q-A) is known, one without a value is not.
Pure: no database, no FX service.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.db.models import Transaction, TransactionType
from backend.app.services.financial_math.income import INCOME_TYPES
from backend.app.services.financial_math.native_cash import NativeCash
from backend.app.services.financial_math.portfolio import period as period_math
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.models import ClassifiedTransaction, DailyPortfolioState, PortfolioCalculationResult
from backend.app.services.financial_math.price_marks import build_asset_price_series
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash

D = Decimal
ASSET = 1
BROKER = 1
DATE_FROM = date(2025, 1, 1)
DATE_TO = date(2025, 1, 12)
DEPOSIT_DAY = date(2025, 1, 1)
BUY_DAY = date(2025, 1, 2)
REWARD_DAY = date(2025, 1, 5)
SELL_DAY = date(2025, 1, 8)

QTY_BUY = D("500")
PRICE_BUY = D("0.30")
REWARD_QTY = D("20")
REWARD_UNIT = D("0.50")
REWARD_VALUE = REWARD_QTY * REWARD_UNIT  # V = 10.00
SELL_QTY = D("100")
PRICE_SELL = D("0.70")

#: Daily prices of the asset, in its currency: the trade days at their trade prices.
PRICES = {
    BUY_DAY: D("0.30"),
    date(2025, 1, 3): D("0.40"),
    date(2025, 1, 4): D("0.45"),
    REWARD_DAY: D("0.50"),
    date(2025, 1, 6): D("0.55"),
    date(2025, 1, 7): D("0.60"),
    SELL_DAY: D("0.70"),
    date(2025, 1, 10): D("0.65"),
}


def _days():
    day = DATE_FROM
    while day <= DATE_TO:
        yield day
        day += timedelta(days=1)


def _tx(tx_id, tx_type, day, *, quantity="0", amount="0", currency=None, cbo=None, cbo_ccy=None, asset_id=ASSET) -> Transaction:
    tx = Transaction()
    tx.id = tx_id
    tx.broker_id = BROKER
    tx.asset_id = asset_id
    tx.type = tx_type
    tx.date = day
    tx.quantity = D(quantity)
    tx.amount = D(amount)
    tx.currency = currency
    tx.cost_basis_override = cbo
    tx.cost_basis_currency = cbo_ccy
    tx.related_transaction_id = None
    tx.updated_at = day
    return tx


def _ledger(kind: str, ccy: str) -> list[Transaction]:
    """``kind`` "A": the REWARD; "B": a DIVIDEND of V and a BUY of q at V/q on the same day; "C": neither."""
    common = [
        _tx(1, TransactionType.DEPOSIT, DEPOSIT_DAY, amount="1000", currency=ccy, asset_id=None),
        _tx(2, TransactionType.BUY, BUY_DAY, quantity=str(QTY_BUY), amount=str(-QTY_BUY * PRICE_BUY), currency=ccy),
    ]
    if kind == "A":
        middle = [_tx(3, TransactionType.REWARD, REWARD_DAY, quantity=str(REWARD_QTY), cbo=REWARD_UNIT, cbo_ccy=ccy)]
    elif kind == "C":
        middle = []
    else:
        middle = [
            _tx(3, TransactionType.DIVIDEND, REWARD_DAY, amount=str(REWARD_VALUE), currency=ccy),
            _tx(4, TransactionType.BUY, REWARD_DAY, quantity=str(REWARD_QTY), amount=str(-REWARD_VALUE), currency=ccy),
        ]
    sell = [_tx(5, TransactionType.SELL, SELL_DAY, quantity=str(-SELL_QTY), amount=str(SELL_QTY * PRICE_SELL), currency=ccy)]
    return common + middle + sell


@dataclass(frozen=True)
class Variant:
    name: str
    currency: str
    share: Decimal
    fx_rate_map: dict

    @property
    def rate_on_reward_day(self) -> Decimal:
        return self.fx_rate_map.get((self.currency, "EUR", REWARD_DAY), D("1"))


def _usd_rates() -> dict:
    """USD→EUR 0.90 through the 6th, then 0.95: a rate change between the REWARD and the SELL."""
    return {("USD", "EUR", day): (D("0.90") if day <= date(2025, 1, 6) else D("0.95")) for day in _days()}


VARIANTS = [
    Variant("eur_share_1", "EUR", D("1"), {}),
    Variant("eur_share_0_4", "EUR", D("0.4"), {}),
    Variant("usd_with_fx", "USD", D("1"), _usd_rates()),
]


@dataclass
class Run:
    result: PortfolioCalculationResult
    native_cash: NativeCash


def _run(kind: str, variant: Variant) -> Run:
    """The replay of ledger ``kind``."""
    return _replay(_ledger(kind, variant.currency), variant, PRICES)


def _replay(ledger: list[Transaction], variant: Variant, prices: dict[date, Decimal]) -> Run:
    """The replay of ``ledger``, built as ``test_portfolio_engine_vnext._build`` builds it."""
    classification = ScopeAwareTransactionClassifier(scope_broker_ids={BROKER}, all_transactions=ledger, broker_shares={BROKER: variant.share}).classify()
    txs = classification.classified
    currencies = {ASSET: variant.currency}
    price_map = {ASSET: [(day, price, variant.currency) for day, price in sorted(prices.items())]}
    series = build_asset_price_series(
        price_rows=price_map[ASSET],
        transactions=[ctxn.tx for ctxn in txs if ctxn.tx.asset_id == ASSET],
        split_linked_tx_ids=set(),
        asset_currency=variant.currency,
        quote_base_quantity=1,
    )
    native_cash = engine_native_cash(txs, target_currency="EUR", fx_rate_map=variant.fx_rate_map, date_to=DATE_TO)
    result = DailyStateBuilder(
        classified_txs=txs,
        in_transit_intervals=[],
        external_cash_flows=classification.external_cash_flows,
        price_map=price_map,
        quote_base_map={},
        fx_rate_map=variant.fx_rate_map,
        asset_classifications={},
        asset_types={ASSET: "CRYPTO"},
        asset_currencies=currencies,
        average_costs=engine_average_costs(txs, asset_currencies=currencies, target_currency="EUR", fx_rate_map=variant.fx_rate_map, date_to=DATE_TO),
        native_cash=native_cash,
        target_currency="EUR",
        date_from=DATE_FROM,
        date_to=DATE_TO,
        split_linked_tx_ids=set(),
        mark_series={ASSET: series} if series.has_observations else {},
        compute_acquisition_funding=True,
    ).build()
    return Run(result=result, native_cash=native_cash)


def _v(variant: Variant) -> Decimal:
    """V as the report reads it: at the owner's share, in EUR at the REWARD's date."""
    return REWARD_VALUE * variant.share * variant.rate_on_reward_day


#: The daily-state fields read off the K/R pool split: checked for the REWARD against the rule (``TestRewardPoolSplit``).
def _without_funding(state: DailyPortfolioState) -> DailyPortfolioState:
    """The state without its acquisition funding: the pair's BUY reinvests V, the REWARD buys nothing."""
    return dataclasses.replace(state, acquisition_funding=None)


def _income(cash: NativeCash, date_from: date | None, date_to: date) -> Decimal:
    signed = cash.flows(date_from, date_to).signed_by_type
    return sum((signed.get(income_type, D("0")) for income_type in INCOME_TYPES), D("0"))


def _realized(result: PortfolioCalculationResult, date_from: date | None, date_to: date) -> tuple[Decimal, Decimal]:
    sales = period_math.period_realized_sales(result.realized_sales, date_from, date_to)
    return sum((sale.proceeds for sale in sales), D("0")), sum((sale.cost for sale in sales), D("0"))


@pytest.fixture(params=VARIANTS, ids=[variant.name for variant in VARIANTS])
def pair(request) -> tuple[Variant, Run, Run]:
    variant = request.param
    return variant, _run("A", variant), _run("B", variant)


class TestRewardEqualsDividendPlusBuy:
    def test_every_day_reads_the_same(self, pair):
        """The whole daily state is equal, the K/R cash split included, but for the acquisition funding (STK1-1)."""
        variant, a, b = pair
        states_a = {state.date: state for state in a.result.daily_states}
        states_b = {state.date: state for state in b.result.daily_states}
        assert set(states_a) == set(states_b) == set(_days())
        for day in _days():
            sa, sb = states_a[day], states_b[day]
            got_a = (sa.nav_value, sa.cash_value, sa.market_value, sa.cumulative_external_cash_flow, sa.total_pnl, sa.open_cost_basis, sa.unrealized_gain_loss)
            got_b = (sb.nav_value, sb.cash_value, sb.market_value, sb.cumulative_external_cash_flow, sb.total_pnl, sb.open_cost_basis, sb.unrealized_gain_loss)
            assert got_a == got_b, f"{variant.name} {day}: A {got_a} != B {got_b}"
            # STK1-1: the pair's dividend reaches R before its BUY draws on it, so the cash split is the REWARD's.
            assert _without_funding(sa) == _without_funding(sb), f"{variant.name} {day}"

    def test_the_pair_reinvests_the_dividend(self, pair):
        """STK1-1: on the reward day the pair's BUY is paid with the dividend it follows — V reinvested, no new capital."""
        variant, _a, b = pair
        funding = b.result.daily_states.state_on(REWARD_DAY).acquisition_funding
        assert funding is not None, variant.name
        assert (funding.from_new_capital, funding.from_reinvested) == (D("0"), _v(variant)), variant.name

    def test_positions_equal(self, pair):
        _variant, a, b = pair
        assert a.result.position_states_end == b.result.position_states_end
        assert a.result.position_states_start == b.result.position_states_start

    def test_the_reward_is_no_capital_contribution(self, pair):
        """The capital is the deposit alone, before and after the REWARD."""
        variant, a, _b = pair
        deposit = D("1000") * variant.share * variant.fx_rate_map.get((variant.currency, "EUR", DEPOSIT_DAY), D("1"))
        for state in a.result.daily_states:
            assert state.cumulative_external_cash_flow == deposit, f"{variant.name} {state.date}"

    def test_the_reward_moves_no_cash(self, pair):
        """Cash in the asset's currency: 1000 − 150 on the REWARD's day in both ledgers."""
        variant, a, b = pair
        expected = {BROKER: {variant.currency: (D("1000") - QTY_BUY * PRICE_BUY) * variant.share}}
        assert a.native_cash.balances(REWARD_DAY) == b.native_cash.balances(REWARD_DAY) == expected

    def test_realized_sales_equal(self, pair):
        variant, a, b = pair
        proceeds_a, cost_a = _realized(a.result, None, DATE_TO)
        assert (proceeds_a, cost_a) == _realized(b.result, None, DATE_TO)
        sell_rate = variant.fx_rate_map.get((variant.currency, "EUR", SELL_DAY), D("1"))
        assert proceeds_a == SELL_QTY * PRICE_SELL * variant.share * sell_rate

    def test_income_equal_and_worth_v(self, pair):
        variant, a, b = pair
        expected = REWARD_VALUE * variant.share * variant.rate_on_reward_day
        assert _income(a.native_cash, None, DATE_TO) == _income(b.native_cash, None, DATE_TO) == expected
        assert a.native_cash.flows(None, DATE_TO).signed_by_type.get("REWARD") == expected
        assert b.native_cash.flows(None, DATE_TO).signed_by_type.get("DIVIDEND") == expected
        assert a.native_cash.flows(None, DATE_TO).income_by_position == b.native_cash.flows(None, DATE_TO).income_by_position == {(BROKER, ASSET): expected}

    def test_position_income_steps_equal(self, pair):
        variant, a, b = pair
        expected = REWARD_VALUE * variant.share * variant.rate_on_reward_day
        steps_a = a.native_cash.position_flow_steps(None, DATE_TO)
        assert steps_a == b.native_cash.position_flow_steps(None, DATE_TO)
        assert steps_a == {(BROKER, ASSET): [(REWARD_DAY, expected, D("0"))]}

    @pytest.mark.parametrize("window", [(date(2025, 1, 3), DATE_TO), (date(2025, 1, 4), date(2025, 1, 6)), (None, DATE_TO)])
    def test_period_identity_components_equal(self, pair, window):
        """Over a window holding the REWARD: P&L, Δ unrealized, realized, income and the other result are the same."""
        variant, a, b = pair
        date_from, as_of = window

        def components(run: Run):
            pnl = period_math.period_pnl(run.result.daily_states, date_from, as_of)
            assert pnl is not None
            proceeds, cost = _realized(run.result, date_from, as_of)
            income = _income(run.native_cash, date_from, as_of)
            other = period_math.period_other_result(pnl.pnl, pnl.ugl_delta, proceeds - cost, income, D("0"))
            residual = period_math.period_identity_residual(pnl.pnl, pnl.ugl_delta, proceeds - cost, income, D("0"), other)
            assert period_math.is_reconciled(residual)
            return pnl.pnl, pnl.net_flows, pnl.ugl_delta, proceeds - cost, income, other

        got_a, got_b = components(a), components(b)
        assert got_a == got_b, f"{variant.name} {window}: A {got_a} != B {got_b}"
        assert got_a[4] == REWARD_VALUE * variant.share * variant.rate_on_reward_day

    def test_acquisition_funding_equal_off_the_reward_day(self, pair):
        """Off the REWARD's day the funding series of A and B are the same (on it: ``TestRewardPoolSplit``)."""
        variant, a, b = pair
        funding_a = {state.date: state.acquisition_funding for state in a.result.daily_states}
        funding_b = {state.date: state.acquisition_funding for state in b.result.daily_states}
        for day in _days():
            if day != REWARD_DAY:
                assert funding_a[day] == funding_b[day], f"{variant.name} {day}"


@pytest.fixture(params=VARIANTS, ids=[variant.name for variant in VARIANTS])
def reward_and_plain(request) -> tuple[Variant, Run, Run]:
    """Ledger A (the REWARD) and ledger C (neither the REWARD nor the DIVIDEND+BUY pair)."""
    variant = request.param
    return variant, _run("A", variant), _run("C", variant)


class TestRewardPoolSplit:
    """Q-C: a REWARD is a DIVIDEND of V reinvested in full the same day: R += V, then the BUY draws V from R. K and R
    end the day unchanged, so nothing funds an acquisition and the cash split is that of a ledger without it."""

    def test_no_funding_on_the_reward_day(self, reward_and_plain):
        variant, a, _c = reward_and_plain
        funding = a.result.daily_states.state_on(REWARD_DAY).acquisition_funding
        # None is how a day with nothing funded is published: 0 from new capital, 0 from reinvested
        assert funding is None, f"{variant.name}: {funding}"

    def test_cash_split_equals_a_ledger_without_the_reward(self, reward_and_plain):
        """Up to the day before the SELL (from it on the sale's cost differs: A holds the 20 rewarded units too)."""
        variant, a, c = reward_and_plain
        states_c = {state.date: state for state in c.result.daily_states}
        compared = 0
        for state_a in a.result.daily_states:
            if state_a.date >= SELL_DAY:
                continue
            state_c = states_c[state_a.date]
            got_a = (state_a.cash_from_contributed_capital, state_a.cash_from_generated_returns, state_a.acquisition_funding)
            got_c = (state_c.cash_from_contributed_capital, state_c.cash_from_generated_returns, state_c.acquisition_funding)
            assert got_a == got_c, f"{variant.name} {state_a.date}: A {got_a} != C {got_c}"
            compared += 1
        assert compared == (SELL_DAY - DATE_FROM).days


# =============================================================================
# Average cost of a REWARD (Q-A): an explicit 0 is a known cost, a missing value is not
# =============================================================================


class TestRewardAverageCost:
    @staticmethod
    def _cost(cbo) -> tuple:
        txs = [ClassifiedTransaction(tx=_tx(3, TransactionType.REWARD, REWARD_DAY, quantity="20", cbo=cbo, cbo_ccy="EUR"), classification="normal", share=D("1"))]
        costs = engine_average_costs(txs, asset_currencies={ASSET: "EUR"}, target_currency="EUR", fx_rate_map={}, date_to=DATE_TO)
        position = costs[(ASSET, BROKER)]
        return position.quantity, position.cost_report, position.unknown_cost_movement_ids

    def test_valued_reward_opens_at_its_value(self):
        assert self._cost(D("0.50")) == (D("20"), D("10.00"), ())

    def test_explicit_zero_is_a_known_cost(self):
        quantity, cost, unknown = self._cost(D("0"))
        assert (quantity, cost, unknown) == (D("20"), D("0"), ())

    def test_missing_value_is_an_unknown_cost(self):
        quantity, cost, unknown = self._cost(None)
        assert quantity == D("20")
        assert unknown == (3,)


# =============================================================================
# STK1-1: a cash income reinvested the same day (the developer's example, P-21)
# =============================================================================

#: The ETF at 1 € a unit every day: the example's figures read straight off the cash.
FLAT_PRICES = {day: D("1") for day in _days()}


def _drip_ledger(income_type: TransactionType) -> list[Transaction]:
    """Deposit 1 000 €, an ETF bought for 900 €, then 30 € of income reinvested the same day in a 30 € BUY.

    The BUY is listed first and carries the lower id: the day's own order, not the ledger's, must put the income first.
    """
    income_asset = ASSET if income_type == TransactionType.DIVIDEND else None
    return [
        _tx(1, TransactionType.DEPOSIT, DEPOSIT_DAY, amount="1000", currency="EUR", asset_id=None),
        _tx(2, TransactionType.BUY, BUY_DAY, quantity="900", amount="-900", currency="EUR"),
        _tx(3, TransactionType.BUY, REWARD_DAY, quantity="30", amount="-30", currency="EUR"),
        _tx(4, income_type, REWARD_DAY, amount="30", currency="EUR", asset_id=income_asset),
    ]


@pytest.fixture(params=[TransactionType.DIVIDEND, TransactionType.INTEREST], ids=["dividend", "interest"])
def drip(request) -> Run:
    return _replay(_drip_ledger(request.param), VARIANTS[0], FLAT_PRICES)


class TestDividendReinvestedSameDay:
    """The income reaches R before the BUY of its day draws on R: K keeps the 100 € deposited, the 30 € are reinvested."""

    def test_the_cash_left_is_all_contributed(self, drip):
        state = drip.result.daily_states.state_on(REWARD_DAY)
        assert (state.cash_from_contributed_capital, state.cash_from_generated_returns) == (D("100"), D("0"))

    def test_the_buy_is_reinvested_income(self, drip):
        funding = drip.result.daily_states.state_on(REWARD_DAY).acquisition_funding
        assert funding is not None
        assert (funding.from_new_capital, funding.from_reinvested) == (D("0"), D("30"))

    def test_nav_pnl_and_income_are_unchanged(self, drip):
        """What the order never moved: NAV 1 030 € (ETF 930 € + cash 100 €), P&L 30 €, income 30 €."""
        state = drip.result.daily_states.state_on(REWARD_DAY)
        assert (state.nav_value, state.market_value, state.cash_value, state.total_pnl) == (D("1030"), D("930"), D("100"), D("30"))
        assert _income(drip.native_cash, None, DATE_TO) == D("30")

    def test_a_withheld_tax_is_paid_from_the_dividend(self):
        """A DRIP with withholding: 30 € dividend, 4.50 € tax, 25.50 € reinvested, the tax and the BUY listed first.

        The dividend reaches R first, the BUY reinvests 25.50 € of it and the tax takes the rest: the 100 € left are all
        contributed. Before STK1-1 the BUY and the tax came out of K (70 € contributed, 30 € generated).
        """
        ledger = [
            _tx(1, TransactionType.DEPOSIT, DEPOSIT_DAY, amount="1000", currency="EUR", asset_id=None),
            _tx(2, TransactionType.BUY, BUY_DAY, quantity="900", amount="-900", currency="EUR"),
            _tx(3, TransactionType.TAX, REWARD_DAY, amount="-4.50", currency="EUR"),
            _tx(4, TransactionType.BUY, REWARD_DAY, quantity="25.50", amount="-25.50", currency="EUR"),
            _tx(5, TransactionType.DIVIDEND, REWARD_DAY, amount="30", currency="EUR"),
        ]
        state = _replay(ledger, VARIANTS[0], FLAT_PRICES).result.daily_states.state_on(REWARD_DAY)
        assert (state.cash_value, state.cash_from_contributed_capital, state.cash_from_generated_returns) == (D("100.00"), D("100.00"), D("0"))
        assert state.acquisition_funding is not None
        assert (state.acquisition_funding.from_new_capital, state.acquisition_funding.from_reinvested) == (D("0"), D("25.50"))
