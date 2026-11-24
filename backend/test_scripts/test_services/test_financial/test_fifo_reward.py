"""Guards the REWARD in the FIFO/LIFO lot engine (project 79, STK-1, plan §5 golden lot cases).

A REWARD of q units valued V is a BUY of q at V/q with no cash: it opens a dated lot at its ``cost_basis_override`` in
``cost_basis_currency``, with no reference price. Its income V is allocated like a DIVIDEND to the lots held at D-1 at
its broker; with none held (Q-D) to the lot it opens itself (``REWARD_OWN_LOT``), and only when it opened no LONG lot
(its units covered a short) to orphan income. In Yield on Cost such a reward is the acquisition, not a yield: it is
left out of the numerator and counts in the WAC only. Pure:
``run_fifo_lot_engine`` on hand-written inputs, no DB, no FX.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

import backend.app.services.financial_math.yield_on_cost as yoc_module
from backend.app.db.models import Transaction, TransactionType
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio.yield_on_cost import YieldOnCostStatus, YieldOnCostUnavailableReason
from backend.app.services.financial_math.fifo.engine import run_fifo_lot_engine
from backend.app.services.financial_math.fifo.models import (
    EconomicAllocationGroup,
    EconomicEvent,
    FifoEngineResult,
    FifoInputTransaction,
    LotMatchingMethod,
    ReferencePriceResolution,
)
from backend.app.services.financial_math.portfolio.models import ClassifiedTransaction
from backend.app.services.financial_math.yield_on_cost import YieldOnCostPositionInput
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs

D = Decimal
ASSET = 7901
BROKER = 1

LOT_A, LOT_B, REWARD_ID, SELL_ID = 1, 2, 3, 4
DAY_A = date(2024, 1, 10)
DAY_B = date(2025, 6, 10)
REWARD_DAY = date(2026, 3, 1)
SELL_DAY = date(2026, 4, 1)


def _buy(tx_id: int, quantity: str, unit_price: str, on: date, *, currency: str = "EUR") -> FifoInputTransaction:
    return FifoInputTransaction(id=tx_id, broker_id=BROKER, asset_id=ASSET, date=on, type="BUY", quantity=D(quantity), amount=-(D(quantity) * D(unit_price)), currency=currency)


def _sell(tx_id: int, quantity: str, unit_price: str, on: date, *, currency: str = "EUR") -> FifoInputTransaction:
    return FifoInputTransaction(id=tx_id, broker_id=BROKER, asset_id=ASSET, date=on, type="SELL", quantity=-D(quantity), amount=D(quantity) * D(unit_price), currency=currency)


def _reward(tx_id: int, quantity: str, unit_value: str | None, on: date, *, currency: str | None = "EUR") -> FifoInputTransaction:
    """A REWARD as stored: units in, amount 0 and no cash currency, the per-unit value in cost_basis_*."""
    return FifoInputTransaction(
        id=tx_id,
        broker_id=BROKER,
        asset_id=ASSET,
        date=on,
        type="REWARD",
        quantity=D(quantity),
        amount=D("0"),
        currency=None,
        cost_basis_override=None if unit_value is None else D(unit_value),
        cost_basis_currency=currency,
    )


def _income_event(tx_id: int, economic_type: str, amount: str, on: date, *, currency: str = "EUR") -> EconomicEvent:
    """An income event as ``build_income_economic_events`` builds it (same currency: target = native)."""
    return EconomicEvent(transaction_id=tx_id, broker_id=BROKER, asset_id=ASSET, date=on, economic_type=economic_type, native_amount=D(amount), native_currency=currency, target_amount=D(amount), target_currency="EUR")


def _run(transactions, events=(), *, method=LotMatchingMethod.FIFO, shorting=False, reference_price_lookup=None) -> FifoEngineResult:
    return run_fifo_lot_engine(transactions, {BROKER: shorting}, economic_events=list(events), target_currency="EUR", matching_method=method, reference_price_lookup=reference_price_lookup)


def _golden(sell_quantity: str) -> list[FifoInputTransaction]:
    """Lot A 500 @0.30, lot B 500 @0.60, REWARD 20 @0.50 (V = 10), then a sale @0.70."""
    return [
        _buy(LOT_A, "500", "0.30", DAY_A),
        _buy(LOT_B, "500", "0.60", DAY_B),
        _reward(REWARD_ID, "20", "0.50", REWARD_DAY),
        _sell(SELL_ID, sell_quantity, "0.70", SELL_DAY),
    ]


def _realized(result: FifoEngineResult, sell_id: int) -> Decimal:
    closures = [closure for closure in result.closures if closure.transaction_id == sell_id]
    assert closures, f"no closure for transaction {sell_id}"
    assert all(closure.realized_pnl is not None for closure in closures)
    return sum((closure.realized_pnl for closure in closures), D("0"))


def _gross_income(result: FifoEngineResult, lot_id: int) -> Decimal:
    accumulator = result.economic_accumulators_by_lot.get(lot_id)
    return accumulator.gross_income if accumulator is not None else D("0")


def _group(result: FifoEngineResult, source_id: int) -> EconomicAllocationGroup:
    matching = [group for group in result.economic_allocation_groups if source_id in group.source_transaction_ids]
    assert len(matching) == 1, [group.source_transaction_ids for group in result.economic_allocation_groups]
    return matching[0]


def _issue_codes(result: FifoEngineResult) -> set[str]:
    return {issue.code for issue in result.issues}


# =============================================================================
# 1. The golden lot cases
# =============================================================================


class TestGoldenLots:
    def test_reward_opens_a_dated_lot_at_its_value(self):
        result = _run(_golden("20"))
        lot = result.get_lot(REWARD_ID)
        assert (lot.direction, lot.opening_date, lot.original_quantity, lot.opening_unit_price, lot.original_cost, lot.currency) == ("LONG", REWARD_DAY, D("20"), D("0.50"), D("10.00"), "EUR")

    def test_fifo_sale_of_20_realizes_8(self):
        """FIFO takes the 20 from lot A: 20 × (0.70 − 0.30) = 8.00."""
        result = _run(_golden("20"))
        assert _realized(result, SELL_ID) == D("8.00")
        assert {closure.lot_id for closure in result.closures if closure.transaction_id == SELL_ID} == {LOT_A}

    def test_lifo_sale_of_20_realizes_4(self):
        """LIFO takes the 20 from the REWARD's lot, the newest: 20 × (0.70 − 0.50) = 4.00."""
        result = _run(_golden("20"), method=LotMatchingMethod.LIFO)
        assert _realized(result, SELL_ID) == D("4.00")
        assert {closure.lot_id for closure in result.closures if closure.transaction_id == SELL_ID} == {REWARD_ID}

    def test_income_10_split_5_5_to_the_lots_held_the_day_before(self):
        result = _run(_golden("20"), [_income_event(REWARD_ID, "REWARD", "10.00", REWARD_DAY)])
        assert _gross_income(result, LOT_A) == D("5.00")
        assert _gross_income(result, LOT_B) == D("5.00")
        assert _gross_income(result, REWARD_ID) == D("0")
        assert result.asset_orphan_income == D("0")
        group = _group(result, REWARD_ID)
        assert (group.economic_type, group.rule, group.target_pool_total) == ("REWARD", "ASSET_INCOME_HOLDINGS", D("10.00"))
        allocated = {allocation.lot_id: allocation.target_amount for operation in group.operation_allocations for allocation in operation.lot_allocations}
        assert allocated == {LOT_A: D("5.00"), LOT_B: D("5.00")}
        assert "ASSET_INCOME_NO_ELIGIBLE_LOTS" not in _issue_codes(result)

    def test_full_sale_realizes_254_and_with_income_264(self):
        """1 020 @0.70: 500 × 0.40 + 500 × 0.10 + 20 × 0.20 = 254 realized; + 10 income = 264."""
        result = _run(_golden("1020"), [_income_event(REWARD_ID, "REWARD", "10.00", REWARD_DAY)])
        realized = _realized(result, SELL_ID)
        assert realized == D("254.00")
        income = sum((_gross_income(result, lot_id) for lot_id in (LOT_A, LOT_B, REWARD_ID)), D("0")) + result.asset_orphan_income
        assert realized + income == D("264.00")
        assert all(result.get_lot(lot_id).open_quantity == D("0") for lot_id in (LOT_A, LOT_B, REWARD_ID))


# =============================================================================
# 2. REWARD == DIVIDEND V + BUY q @ V/q on the same day
# =============================================================================


class TestRewardEqualsDividendPlusBuy:
    def test_same_lot_and_same_income(self):
        reward_run = _run(_golden("20"), [_income_event(REWARD_ID, "REWARD", "10.00", REWARD_DAY)])
        ledger_b = [
            _buy(LOT_A, "500", "0.30", DAY_A),
            _buy(LOT_B, "500", "0.60", DAY_B),
            _buy(REWARD_ID, "20", "0.50", REWARD_DAY),
            _sell(SELL_ID, "20", "0.70", SELL_DAY),
        ]
        dividend_run = _run(ledger_b, [_income_event(99, "DIVIDEND", "10.00", REWARD_DAY)])

        reward_lot, buy_lot = reward_run.get_lot(REWARD_ID), dividend_run.get_lot(REWARD_ID)
        fields = ("direction", "opening_date", "original_quantity", "opening_unit_price", "original_cost", "currency", "open_quantity")
        assert {name: getattr(reward_lot, name) for name in fields} == {name: getattr(buy_lot, name) for name in fields}
        for lot_id in (LOT_A, LOT_B, REWARD_ID):
            assert _gross_income(reward_run, lot_id) == _gross_income(dividend_run, lot_id), lot_id
        assert _realized(reward_run, SELL_ID) == _realized(dividend_run, SELL_ID)

    def test_lifo_same_realized(self):
        ledger_b = [_buy(LOT_A, "500", "0.30", DAY_A), _buy(LOT_B, "500", "0.60", DAY_B), _buy(REWARD_ID, "20", "0.50", REWARD_DAY), _sell(SELL_ID, "20", "0.70", SELL_DAY)]
        assert _realized(_run(_golden("20"), method=LotMatchingMethod.LIFO), SELL_ID) == _realized(_run(ledger_b, method=LotMatchingMethod.LIFO), SELL_ID)


# =============================================================================
# 3. No lot held the day before (Q-D): the income goes to the reward's own lot
# =============================================================================


class TestRewardWithoutPriorLots:
    def test_income_goes_to_its_own_lot(self):
        result = _run([_reward(REWARD_ID, "20", "0.50", REWARD_DAY)], [_income_event(REWARD_ID, "REWARD", "10.00", REWARD_DAY)])
        assert _gross_income(result, REWARD_ID) == D("10.00")
        assert result.asset_orphan_income == D("0")
        assert "ASSET_INCOME_NO_ELIGIBLE_LOTS" not in _issue_codes(result)
        assert result.analysis_status == "COMPLETE"
        group = _group(result, REWARD_ID)
        assert (group.rule, group.target_pool_total, group.target_orphan) == ("REWARD_OWN_LOT", D("10.00"), D("0"))
        operations = [(operation.context, operation.operation_transaction_id, tuple((allocation.lot_id, allocation.target_amount) for allocation in operation.lot_allocations)) for operation in group.operation_allocations]
        assert operations == [("OPENING", REWARD_ID, ((REWARD_ID, D("10.00")),))]

    def test_lot_held_only_from_the_same_day_is_not_eligible(self):
        """A BUY on the REWARD's day is not held at D-1: the reward still earns on its own lot."""
        result = _run([_buy(LOT_A, "100", "0.40", REWARD_DAY), _reward(REWARD_ID, "20", "0.50", REWARD_DAY)], [_income_event(REWARD_ID, "REWARD", "10.00", REWARD_DAY)])
        assert (_gross_income(result, REWARD_ID), _gross_income(result, LOT_A)) == (D("10.00"), D("0"))
        assert _group(result, REWARD_ID).rule == "REWARD_OWN_LOT"

    def test_dividend_without_lots_stays_orphan(self):
        """GUARD: the own-lot rule is the REWARD's alone; a DIVIDEND with no lot is still orphan income."""
        result = _run([_buy(LOT_A, "100", "0.40", date(2026, 5, 1))], [_income_event(50, "DIVIDEND", "3", REWARD_DAY)])
        assert result.asset_orphan_income == D("3")
        assert "ASSET_INCOME_NO_ELIGIBLE_LOTS" in _issue_codes(result)

    def test_reward_covering_a_short_falls_back_to_orphan(self):
        """A REWARD whose units all close a short opens no LONG lot: its pool is orphan income, with the issue."""
        result = _run(
            [_sell(LOT_A, "20", "0.70", date(2026, 2, 1)), _reward(REWARD_ID, "20", "0.50", REWARD_DAY)],
            [_income_event(REWARD_ID, "REWARD", "10.00", REWARD_DAY)],
            shorting=True,
        )
        assert REWARD_ID not in {lot.lot_id for lot in result.lots}
        assert result.asset_orphan_income == D("10.00")
        orphan_issues = [issue for issue in result.issues if issue.code == "ASSET_INCOME_NO_ELIGIBLE_LOTS"]
        assert [issue.params["economic_type"] for issue in orphan_issues] == ["REWARD"]
        group = _group(result, REWARD_ID)
        assert (group.rule, group.target_orphan) == ("ASSET_INCOME_HOLDINGS", D("10.00"))


# =============================================================================
# 4. The lot a REWARD opens: unknown value, currency, no reference price
# =============================================================================


class TestRewardLot:
    def test_without_value_opens_at_zero(self):
        result = _run([_reward(REWARD_ID, "20", None, REWARD_DAY)])
        lot = result.get_lot(REWARD_ID)
        assert (lot.original_quantity, lot.opening_unit_price, lot.original_cost) == (D("20"), D("0"), D("0"))

    def test_explicit_zero_value_opens_at_zero(self):
        lot = _run([_reward(REWARD_ID, "20", "0", REWARD_DAY)]).get_lot(REWARD_ID)
        assert (lot.opening_unit_price, lot.original_cost, lot.currency) == (D("0"), D("0"), "EUR")

    def test_usd_cost_basis_currency_gives_a_usd_lot(self):
        lot = _run([_reward(REWARD_ID, "4", "1.25", REWARD_DAY, currency="USD")]).get_lot(REWARD_ID)
        assert (lot.currency, lot.opening_unit_price, lot.original_cost) == ("USD", D("1.25"), D("5.00"))

    @pytest.mark.parametrize("lookup_result", [None, ReferencePriceResolution(price=D("0.45"), source="fallback")])
    def test_no_reference_price_issue(self, lookup_result):
        """A REWARD's value is its cost, as a purchase's price is: no reference price is asked, no REFERENCE_PRICE_* issue."""
        asked: list[tuple[int, date]] = []

        def lookup(asset_id: int, opened_at: date):
            asked.append((asset_id, opened_at))
            return lookup_result

        result = _run([_reward(REWARD_ID, "20", "0.50", REWARD_DAY)], reference_price_lookup=lookup)
        assert not any(code.startswith("REFERENCE_PRICE_") for code in _issue_codes(result))
        assert asked == []
        lot = result.get_lot(REWARD_ID)
        assert (lot.reference_unit_price, lot.reference_price_source) == (None, None)

    def test_reward_is_an_inflow_before_a_same_day_sale(self):
        """Phase 3 like a BUY: a same-day SELL of the rewarded units finds them (no short, no oversell)."""
        result = _run([_reward(REWARD_ID, "20", "0.50", REWARD_DAY), _sell(SELL_ID, "20", "0.70", REWARD_DAY)])
        assert _realized(result, SELL_ID) == D("4.00")
        assert result.analysis_status == "COMPLETE"


# =============================================================================
# 5. Q-E: a same-day charge never hooks to a REWARD as SAME_DAY_INCOME
# =============================================================================


class TestChargesBesideAReward:
    @pytest.mark.parametrize("charge", ["FEE", "TAX"])
    def test_unlinked_charge_on_a_reward_day_is_not_same_day_income(self, charge):
        """No trade on the day or the day before: the charge falls to the held lots (the FEE has no income rung at all;
        the TAX is the case that can see a REWARD taken for income)."""
        result = _run(
            [_buy(LOT_A, "100", "0.40", DAY_B), _reward(REWARD_ID, "20", "0.50", REWARD_DAY)],
            [_income_event(REWARD_ID, "REWARD", "10.00", REWARD_DAY), _income_event(60, charge, "1", REWARD_DAY)],
        )
        assert _group(result, 60).rule == "OPEN_LOTS_FALLBACK"

    def test_guard_tax_on_a_dividend_day_is_same_day_income(self):
        """GUARD: the same TAX beside a DIVIDEND does hook as SAME_DAY_INCOME, so the test above can see the rule."""
        result = _run(
            [_buy(LOT_A, "100", "0.40", DAY_B)],
            [_income_event(70, "DIVIDEND", "10.00", REWARD_DAY), _income_event(60, "TAX", "1", REWARD_DAY)],
        )
        assert _group(result, 60).rule == "SAME_DAY_INCOME"


# =============================================================================
# 6. Yield on Cost mirrors Q-D: a reward with nothing held the day before earns on its own units
# =============================================================================


def _yield_on_cost(rows: list[Transaction], incomes: list[tuple[Transaction, Decimal]], wac: Decimal):
    """The YoC of one position through ``_calculate_position``, with the contexts built in memory as in
    ``test_yield_on_cost_date_min.py``: the replay over the rows that move quantity, each income already in EUR."""
    key = (ASSET, BROKER)
    as_of = date(2026, 12, 31)
    replay = run_fifo_lot_engine(transactions=[row for row in rows if row.quantity != 0], broker_shorting={BROKER: False})
    calculation = yoc_module._calculate_position(
        key=key,
        position=YieldOnCostPositionInput(asset_id=ASSET, broker_id=BROKER, wac_per_unit=wac, wac_currency="EUR"),
        transaction_context=yoc_module._TransactionContext(replay_transactions=rows, first_pair_date={key: min(row.date for row in rows)}, income_by_key={key: sorted((tx for tx, _amount in incomes), key=lambda tx: (tx.date, tx.id))}),
        replay_context=yoc_module._ReplayContext(replay_by_key={key: replay}, invalid_keys=set(), failed_keys=set()),
        conversion_context=yoc_module._ConversionContext(income_by_transaction={tx.id: amount for tx, amount in incomes}, provenance_by_key={}, missing_by_key={}, missing_pairs_by_key={}),
        target_currency="EUR",
        window_start=as_of - timedelta(days=364),
        as_of_date=as_of,
    )
    return calculation.result


def _orm(tx_id: int, tx_type: TransactionType, on: date, *, quantity="0", amount="0", currency="EUR", cbo=None, cbo_ccy=None) -> Transaction:
    return Transaction(
        id=tx_id,
        broker_id=BROKER,
        asset_id=ASSET,
        type=tx_type,
        date=on,
        quantity=D(quantity),
        amount=D(amount),
        currency=currency,
        cost_basis_override=None if cbo is None else D(cbo),
        cost_basis_currency=cbo_ccy,
    )


def _wac(rows: list[Transaction]) -> Decimal:
    """The average cost per unit the position reaches, as ``calculate()`` computes it (``compute_average_costs``)."""
    classified = [ClassifiedTransaction(tx=row, classification="normal", share=D("1")) for row in rows]
    position = engine_average_costs(classified, asset_currencies={ASSET: "EUR"}, target_currency="EUR", fx_rate_map={})[(ASSET, BROKER)]
    return position.cost_report / position.quantity


class TestYieldOnCostReward:
    """Yield on Cost (consultant, 23/11): a REWARD with nothing held the day before is the position's acquisition, not a
    yield. It stays out of the numerator; its value still counts in the WAC, the denominator."""

    def test_airdrop_is_skipped_and_a_later_reward_counts(self):
        """Airdrop REWARD 100 @1 (nothing held before), then a REWARD 5 @1: only the 5 counts, over the 100 held at its
        D-1: 5 / 100 = 0.05 a unit; WAC (100 + 5) / 105 = 1, so YoC 0.05. Never the airdrop's 100."""
        airdrop = _orm(REWARD_ID, TransactionType.REWARD, date(2026, 2, 1), quantity="100", currency=None, cbo="1", cbo_ccy="EUR")
        later = _orm(5, TransactionType.REWARD, REWARD_DAY, quantity="5", currency=None, cbo="1", cbo_ccy="EUR")
        wac = _wac([airdrop, later])
        assert wac == D("1")
        result = _yield_on_cost([airdrop, later], [(airdrop, D("100")), (later, D("5"))], wac)
        assert result.status == YieldOnCostStatus.AVAILABLE
        assert result.provenance.gross_income_per_unit == Currency(code="EUR", amount=D("0.05"))
        assert result.value == D("0.05")

    def test_airdrop_alone_is_not_income_without_eligible_quantity(self):
        """The airdrop alone in the window: skipped, never INCOME_WITHOUT_ELIGIBLE_QUANTITY. Observed: AVAILABLE with a
        gross income per unit of 0 (net_zero), so YoC 0."""
        airdrop = _orm(REWARD_ID, TransactionType.REWARD, REWARD_DAY, quantity="100", currency=None, cbo="1", cbo_ccy="EUR")
        result = _yield_on_cost([airdrop], [(airdrop, D("100"))], _wac([airdrop]))
        assert result.reason != YieldOnCostUnavailableReason.INCOME_WITHOUT_ELIGIBLE_QUANTITY
        assert result.status == YieldOnCostStatus.AVAILABLE
        assert result.provenance.gross_income_per_unit == Currency(code="EUR", amount=D("0"))
        assert result.value == D("0")

    def test_reward_with_prior_lots_divides_by_the_units_held_the_day_before(self):
        """100 units held at D-1: 10 EUR / 100 = 0.1 a unit (the reward's own 20 do not count); over 0.5 = 0.2."""
        buy = _orm(LOT_A, TransactionType.BUY, DAY_B, quantity="100", amount="-40")
        reward = _orm(REWARD_ID, TransactionType.REWARD, REWARD_DAY, quantity="20", currency=None, cbo="0.50", cbo_ccy="EUR")
        result = _yield_on_cost([buy, reward], [(reward, D("10.00"))], D("0.50"))
        assert result.status == YieldOnCostStatus.AVAILABLE
        assert result.provenance.gross_income_per_unit == Currency(code="EUR", amount=D("0.1"))
        assert result.value == D("0.2")

    def test_guard_dividend_without_prior_lots_stays_unavailable(self):
        buy = _orm(LOT_A, TransactionType.BUY, REWARD_DAY, quantity="100", amount="-40")
        dividend = _orm(60, TransactionType.DIVIDEND, REWARD_DAY, amount="10")
        result = _yield_on_cost([buy, dividend], [(dividend, D("10"))], D("0.40"))
        assert result.status == YieldOnCostStatus.UNAVAILABLE
        assert result.reason == YieldOnCostUnavailableReason.INCOME_WITHOUT_ELIGIBLE_QUANTITY
