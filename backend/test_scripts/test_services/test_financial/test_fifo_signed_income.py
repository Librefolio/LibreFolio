"""MF-F1 — decision D-MF3: a negative DIVIDEND/INTEREST correction REDUCES the income of the lots (FIFO lot engine).

Workstream MF «financial math», release 1.3. Pure: ``run_fifo_lot_engine`` on hand-written
``FifoInputTransaction`` / ``EconomicEvent`` rows and, at the lots-analysis level, the in-memory ``Transaction``
rows that ``lots/economic_events.py`` turns into engine inputs — no DB, no server, no FX I/O (a resolver whose
rate table is filled by hand stands in for ``FxRateResolver.load``).

THE RULE — developer decision D-MF3 (16/10), in ``backend/app/services/financial_math/fifo/engine.py``
(``FifoLotEngine._allocate_income_pools``):

1. An income pool — key (broker, date, economic type, native currency, target currency) — sums the SIGNED
   ``native_amount`` and ``target_amount`` of its events. A negative DIVIDEND/INTEREST correction (legacy rows and
   imports: the API forbids new ones) therefore reduces the pool, as the Dashboard reduces ``period_income``
   (``portfolio_service.py``, ``signed_by_type``) and the per-position income (``native_cash.flows``,
   ``income_by_position``).
2. Allocation is unchanged: by eligible quantity as of D-1, running remainder, the last lot (by id) gets the rest,
   so the signed total is conserved exactly.
3. A pool with no eligible lot is orphan income with its signed total; ``ASSET_INCOME_NO_ELIGIBLE_LOTS`` keeps its
   params, its ``target_amount`` now signed.
4. FEE/TAX are out of scope: the Dashboard counts them in absolute value (``absolute_by_type``,
   ``costs_by_position``), so the cost pools keep ``abs`` (``_allocate_cost_pools``).

Before MF-F1 the income pools summed ``abs(event.native_amount)`` / ``abs(event.target_amount)``: a −4 correction
became +4 of income for the lots. Every red test's docstring keeps the value it read then. GUARD marks a control:
its values are the same before and after MF-F1.
"""

from datetime import date
from decimal import Decimal

from backend.app.db.models import Transaction, TransactionType
from backend.app.services.financial_math.fifo.engine import run_fifo_lot_engine
from backend.app.services.financial_math.fifo.models import (
    EconomicAllocationGroup,
    EconomicEvent,
    EconomicLotAllocation,
    FifoDataQualityIssue,
    FifoEngineResult,
    FifoInputTransaction,
)
from backend.app.services.financial_math.lots.conversions import FxRateResolver
from backend.app.services.financial_math.lots.economic_events import build_income_economic_events, extract_income_outputs, map_economic_groups

D = Decimal
ASSET_ID = 5301
BROKER = 1

# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #


def _buy(tx_id: int, quantity: str, unit_price: str, *, on: str, currency: str = "EUR") -> FifoInputTransaction:
    """A purchase of ``quantity`` at ``unit_price`` a unit: amount = −quantity × unit price."""
    return FifoInputTransaction(
        id=tx_id,
        broker_id=BROKER,
        asset_id=ASSET_ID,
        date=date.fromisoformat(on),
        type="BUY",
        quantity=D(quantity),
        amount=-(D(quantity) * D(unit_price)),
        currency=currency,
    )


def _sell(tx_id: int, quantity: str, unit_price: str, *, on: str, currency: str = "EUR") -> FifoInputTransaction:
    """A sale of ``quantity`` at ``unit_price`` a unit: quantity negative, amount = quantity × unit price."""
    return FifoInputTransaction(
        id=tx_id,
        broker_id=BROKER,
        asset_id=ASSET_ID,
        date=date.fromisoformat(on),
        type="SELL",
        quantity=-D(quantity),
        amount=D(quantity) * D(unit_price),
        currency=currency,
    )


def _event(
    tx_id: int,
    economic_type: str,
    native_amount: str,
    *,
    on: str,
    native_currency: str = "EUR",
    target_amount: str | None = None,
    target_currency: str = "EUR",
) -> EconomicEvent:
    """An economic event as the service hands it over: the stored (signed) native amount and its target amount.

    ``target_amount`` defaults to the native amount (same currency); a cross-currency event carries the target
    amount the service already converted at the event's date.
    """
    return EconomicEvent(
        transaction_id=tx_id,
        broker_id=BROKER,
        asset_id=ASSET_ID,
        date=date.fromisoformat(on),
        economic_type=economic_type,
        native_amount=D(native_amount),
        native_currency=native_currency,
        target_amount=D(target_amount if target_amount is not None else native_amount),
        target_currency=target_currency,
    )


def _dividend(tx_id: int, amount: str, *, on: str, **kwargs) -> EconomicEvent:
    return _event(tx_id, "DIVIDEND", amount, on=on, **kwargs)


def _interest(tx_id: int, amount: str, *, on: str, **kwargs) -> EconomicEvent:
    return _event(tx_id, "INTEREST", amount, on=on, **kwargs)


def _fee(tx_id: int, amount: str, *, on: str, **kwargs) -> EconomicEvent:
    return _event(tx_id, "FEE", amount, on=on, **kwargs)


def _tax(tx_id: int, amount: str, *, on: str, **kwargs) -> EconomicEvent:
    return _event(tx_id, "TAX", amount, on=on, **kwargs)


def _run(transactions: list[FifoInputTransaction], events: list[EconomicEvent], *, target_currency: str = "EUR") -> FifoEngineResult:
    return run_fifo_lot_engine(transactions, {BROKER: False}, economic_events=events, target_currency=target_currency)


# --------------------------------------------------------------------------- #
# Readers — every pool, lot and issue is found by what the test created, never by position
# --------------------------------------------------------------------------- #


def _lot_income(result: FifoEngineResult, lot_id: int) -> Decimal:
    accumulator = result.economic_accumulators_by_lot.get(lot_id)
    return accumulator.gross_income if accumulator is not None else D("0")


def _lot_fees(result: FifoEngineResult, lot_id: int) -> Decimal:
    accumulator = result.economic_accumulators_by_lot.get(lot_id)
    return accumulator.allocated_fees if accumulator is not None else D("0")


def _lot_taxes(result: FifoEngineResult, lot_id: int) -> Decimal:
    accumulator = result.economic_accumulators_by_lot.get(lot_id)
    return accumulator.allocated_taxes if accumulator is not None else D("0")


def _pool(result: FifoEngineResult, *source_ids: int) -> EconomicAllocationGroup:
    """The one audit group whose sources are exactly ``source_ids``."""
    wanted = tuple(sorted(source_ids))
    matching = [group for group in result.economic_allocation_groups if group.source_transaction_ids == wanted]
    assert len(matching) == 1, f"expected one pool with sources {wanted}, got {[group.source_transaction_ids for group in result.economic_allocation_groups]}"
    return matching[0]


def _lot_allocations(group: EconomicAllocationGroup) -> dict[int, EconomicLotAllocation]:
    """Lot id -> its allocation in ``group`` (an income pool has one HOLDING operation, each lot once)."""
    allocations: dict[int, EconomicLotAllocation] = {}
    for operation in group.operation_allocations:
        for allocation in operation.lot_allocations:
            assert allocation.lot_id not in allocations, f"lot {allocation.lot_id} allocated twice in pool {group.source_transaction_ids}"
            allocations[allocation.lot_id] = allocation
    return allocations


def _issues(result: FifoEngineResult, code: str) -> list[FifoDataQualityIssue]:
    return [issue for issue in result.issues if issue.code == code]


def _total_income(result: FifoEngineResult) -> Decimal:
    """Asset-level income: allocated to lots plus orphan — the figure the Dashboard's signed sum must match."""
    allocated = sum((accumulator.gross_income for accumulator in result.economic_accumulators_by_lot.values()), D("0"))
    return allocated + result.asset_orphan_income


# --------------------------------------------------------------------------- #
# 1. A correction on a later day, while the lot is still held
# --------------------------------------------------------------------------- #


class TestCorrectionOnALaterDay:
    def test_a_later_negative_dividend_reduces_the_lot_income(self):
        """10 units held; DIVIDEND +10 on 20 Jan, DIVIDEND −4 (correction) on 10 Feb: the lot earned 6.

        Before MF-F1: lot income 14, the correction pool's totals and its lot allocation +4.
        """
        result = _run(
            [_buy(1, "10", "100", on="2025-01-01")],
            [_dividend(90, "10", on="2025-01-20"), _dividend(91, "-4", on="2025-02-10")],
        )

        assert _lot_income(result, 1) == D("6")

        dividend = _pool(result, 90)
        assert (dividend.native_pool_total, dividend.target_pool_total) == (D("10"), D("10"))
        assert _lot_allocations(dividend)[1].target_amount == D("10")

        correction = _pool(result, 91)
        assert correction.economic_type == "DIVIDEND"
        assert correction.rule == "ASSET_INCOME_HOLDINGS"
        assert (correction.native_pool_total, correction.target_pool_total) == (D("-4"), D("-4"))
        assert (correction.native_orphan, correction.target_orphan) == (D("0"), D("0"))
        allocation = _lot_allocations(correction)[1]
        assert allocation.weight == D("1")
        assert (allocation.native_amount, allocation.target_amount) == (D("-4"), D("-4"))

        assert result.asset_orphan_income == D("0")
        assert result.issues == []
        assert _total_income(result) == D("6")


# --------------------------------------------------------------------------- #
# 2. A correction in the same pool as the dividend it corrects
# --------------------------------------------------------------------------- #


class TestCorrectionInTheSamePool:
    def test_a_same_day_correction_nets_the_pool(self):
        """DIVIDEND +10 and DIVIDEND −4, same day, broker and currency: one pool of 6, all to the only lot.

        Before MF-F1: pool totals 14, lot income 14.
        """
        result = _run(
            [_buy(1, "10", "100", on="2025-01-01")],
            [_dividend(90, "10", on="2025-01-20"), _dividend(91, "-4", on="2025-01-20")],
        )

        pool = _pool(result, 90, 91)
        assert (pool.native_pool_total, pool.target_pool_total) == (D("6"), D("6"))
        assert _lot_allocations(pool)[1].target_amount == D("6")
        assert _lot_income(result, 1) == D("6")
        assert result.asset_orphan_income == D("0")
        assert result.issues == []

    def test_the_net_pool_is_split_by_eligible_quantity_and_conserved(self):
        """Lots of 6 and 4 units; the netted pool of 6 splits 3.6 / 2.4, and the split adds back to 6 exactly.

        Weights 0.6 / 0.4 (unchanged by MF-F1); the last lot takes the running remainder.
        Before MF-F1: pool 14, split 8.4 / 5.6.
        """
        result = _run(
            [_buy(1, "6", "100", on="2025-01-01"), _buy(2, "4", "100", on="2025-01-05")],
            [_dividend(90, "10", on="2025-01-20"), _dividend(91, "-4", on="2025-01-20")],
        )

        pool = _pool(result, 90, 91)
        assert (pool.native_pool_total, pool.target_pool_total) == (D("6"), D("6"))
        allocations = _lot_allocations(pool)
        assert set(allocations) == {1, 2}
        assert (allocations[1].weight, allocations[2].weight) == (D("0.6"), D("0.4"))
        assert (allocations[1].target_amount, allocations[2].target_amount) == (D("3.6"), D("2.4"))
        assert (allocations[1].native_amount, allocations[2].native_amount) == (D("3.6"), D("2.4"))
        assert allocations[1].target_amount + allocations[2].target_amount == pool.target_pool_total
        assert allocations[1].native_amount + allocations[2].native_amount == pool.native_pool_total

        assert (_lot_income(result, 1), _lot_income(result, 2)) == (D("3.6"), D("2.4"))
        assert _total_income(result) == D("6")


# --------------------------------------------------------------------------- #
# 3. INTEREST: its own economic type, the same signed rule
# --------------------------------------------------------------------------- #


class TestInterestCorrection:
    def test_a_later_negative_interest_reduces_the_lot_income(self):
        """INTEREST +10 on 20 Jan, INTEREST −4 on 10 Feb, lot still held: the lot earned 6.

        Before MF-F1: lot income 14, the correction pool +4.
        """
        result = _run(
            [_buy(1, "10", "100", on="2025-01-01")],
            [_interest(90, "10", on="2025-01-20"), _interest(91, "-4", on="2025-02-10")],
        )

        correction = _pool(result, 91)
        assert correction.economic_type == "INTEREST"
        assert (correction.native_pool_total, correction.target_pool_total) == (D("-4"), D("-4"))
        assert _lot_allocations(correction)[1].target_amount == D("-4")
        assert _lot_income(result, 1) == D("6")
        assert result.issues == []

    def test_a_same_day_interest_correction_nets_its_pool(self):
        """INTEREST +10 and INTEREST −4 on the same day: one INTEREST pool of 6.

        Before MF-F1: pool 14, lot income 14.
        """
        result = _run(
            [_buy(1, "10", "100", on="2025-01-01")],
            [_interest(90, "10", on="2025-01-20"), _interest(91, "-4", on="2025-01-20")],
        )

        pool = _pool(result, 90, 91)
        assert pool.economic_type == "INTEREST"
        assert (pool.native_pool_total, pool.target_pool_total) == (D("6"), D("6"))
        assert _lot_income(result, 1) == D("6")

    def test_an_interest_correction_beside_a_dividend_stays_its_own_pool(self):
        """DIVIDEND +10 and INTEREST −4 on the same day: two pools by economic type (+10 and −4); lot income 6.

        Before MF-F1: the INTEREST pool +4, lot income 14.
        """
        result = _run(
            [_buy(1, "10", "100", on="2025-01-01")],
            [_dividend(90, "10", on="2025-01-20"), _interest(91, "-4", on="2025-01-20")],
        )

        dividend = _pool(result, 90)
        interest = _pool(result, 91)
        assert (dividend.economic_type, interest.economic_type) == ("DIVIDEND", "INTEREST")
        assert dividend.target_pool_total == D("10")
        assert (interest.native_pool_total, interest.target_pool_total) == (D("-4"), D("-4"))
        assert _lot_allocations(interest)[1].target_amount == D("-4")
        assert _lot_income(result, 1) == D("6")


# --------------------------------------------------------------------------- #
# 4. A correction with no eligible lot is NEGATIVE orphan income
# --------------------------------------------------------------------------- #


class TestOrphanCorrection:
    def test_a_correction_with_no_eligible_lot_is_negative_orphan_income(self):
        """The lot is sold on 5 Jan; DIVIDEND −4 on 20 Jan finds no eligible lot: orphan income −4.

        The issue keeps its params, ``target_amount`` signed. Analysis status DEGRADED either way.
        Before MF-F1: orphan +4, issue target_amount +4, pool totals and orphan residuals +4.
        """
        result = _run(
            [_buy(1, "10", "100", on="2025-01-01"), _sell(2, "10", "120", on="2025-01-05")],
            [_dividend(90, "-4", on="2025-01-20")],
        )

        assert result.asset_orphan_income == D("-4")
        assert _lot_income(result, 1) == D("0")

        issues = _issues(result, "ASSET_INCOME_NO_ELIGIBLE_LOTS")
        assert len(issues) == 1
        issue = issues[0]
        assert (issue.transaction_id, issue.broker_id) == (90, BROKER)
        assert issue.params == {"economic_type": "DIVIDEND", "as_of_date": "2025-01-20", "target_amount": D("-4"), "target_currency": "EUR"}
        assert result.analysis_status == "DEGRADED"

        pool = _pool(result, 90)
        assert pool.operation_allocations == ()
        assert (pool.native_pool_total, pool.target_pool_total) == (D("-4"), D("-4"))
        assert (pool.native_orphan, pool.target_orphan) == (D("-4"), D("-4"))

    def test_an_orphan_pool_nets_its_correction(self):
        """DIVIDEND +10 and −4 on the same day with no eligible lot: orphan income 6, the issue's target_amount 6.

        Before MF-F1: orphan 14, issue target_amount 14.
        """
        result = _run(
            [_buy(1, "10", "100", on="2025-01-01"), _sell(2, "10", "120", on="2025-01-05")],
            [_dividend(90, "10", on="2025-01-20"), _dividend(91, "-4", on="2025-01-20")],
        )

        assert result.asset_orphan_income == D("6")
        issues = _issues(result, "ASSET_INCOME_NO_ELIGIBLE_LOTS")
        assert len(issues) == 1
        assert issues[0].params["target_amount"] == D("6")
        pool = _pool(result, 90, 91)
        assert (pool.native_orphan, pool.target_orphan) == (D("6"), D("6"))

    def test_a_correction_after_the_sale_reduces_the_asset_total(self):
        """DIVIDEND +10 while held goes to the lot; the −4 correction after the full sale is orphan −4.

        The lot keeps its 10; the asset total (lots + orphan) is 6, the Dashboard's signed sum.
        Before MF-F1: orphan +4, asset total 14.
        """
        result = _run(
            [_buy(1, "10", "100", on="2025-01-01"), _sell(2, "10", "120", on="2025-02-01")],
            [_dividend(90, "10", on="2025-01-20"), _dividend(91, "-4", on="2025-02-10")],
        )

        assert _lot_income(result, 1) == D("10")
        assert result.asset_orphan_income == D("-4")
        assert _total_income(result) == D("6")
        issues = _issues(result, "ASSET_INCOME_NO_ELIGIBLE_LOTS")
        assert len(issues) == 1
        assert issues[0].transaction_id == 91
        assert issues[0].params["target_amount"] == D("-4")


# --------------------------------------------------------------------------- #
# 5. Controls — GUARD: positive income and FEE/TAX (abs kept) are untouched by MF-F1
# --------------------------------------------------------------------------- #


class TestControls:
    def test_an_ordinary_positive_dividend_is_unchanged(self):
        """GUARD: DIVIDEND +10 on a held lot of 10 units — pool 10, lot income 10, no issue."""
        result = _run([_buy(1, "10", "100", on="2025-01-01")], [_dividend(90, "10", on="2025-01-20")])

        pool = _pool(result, 90)
        assert (pool.native_pool_total, pool.target_pool_total) == (D("10"), D("10"))
        assert _lot_allocations(pool)[1].target_amount == D("10")
        assert _lot_income(result, 1) == D("10")
        assert result.asset_orphan_income == D("0")
        assert result.issues == []

    def test_a_negative_fee_still_counts_as_a_cost_of_its_magnitude(self):
        """GUARD: FEE −2 with no trade that day or the day before falls back on the held lot: a cost of +2.

        FEE stays in absolute value, as on the Dashboard (``absolute_by_type``); no income is touched.
        """
        result = _run([_buy(1, "10", "100", on="2025-01-01")], [_fee(80, "-2", on="2025-01-20")])

        pool = _pool(result, 80)
        assert pool.economic_type == "FEE"
        assert pool.rule == "OPEN_LOTS_FALLBACK"
        assert (pool.native_pool_total, pool.target_pool_total) == (D("2"), D("2"))
        assert _lot_allocations(pool)[1].target_amount == D("2")
        assert _lot_fees(result, 1) == D("2")
        assert _lot_income(result, 1) == D("0")
        assert result.issues == []

    def test_a_negative_tax_still_counts_as_a_cost_of_its_magnitude(self):
        """GUARD: TAX −3 on a held lot, no income or trade around it: a tax of +3 (abs kept)."""
        result = _run([_buy(1, "10", "100", on="2025-01-01")], [_tax(81, "-3", on="2025-01-20")])

        pool = _pool(result, 81)
        assert pool.economic_type == "TAX"
        assert (pool.native_pool_total, pool.target_pool_total) == (D("3"), D("3"))
        assert _lot_taxes(result, 1) == D("3")
        assert _lot_income(result, 1) == D("0")

    def test_an_orphan_fee_keeps_its_magnitude(self):
        """GUARD: FEE −2 after the full sale, no trade around it: orphan fees +2, its issue target_amount +2."""
        result = _run(
            [_buy(1, "10", "100", on="2025-01-01"), _sell(2, "10", "120", on="2025-01-05")],
            [_fee(80, "-2", on="2025-01-20")],
        )

        assert result.asset_orphan_fees == D("2")
        assert result.asset_orphan_income == D("0")
        issues = _issues(result, "ASSET_COST_NO_ELIGIBLE_LOTS")
        assert len(issues) == 1
        assert issues[0].params["target_amount"] == D("2")


# --------------------------------------------------------------------------- #
# 6. Cross-currency: native pool and target pool are both signed sums
# --------------------------------------------------------------------------- #


class TestCrossCurrencyCorrection:
    def test_a_usd_correction_nets_the_native_and_the_target_pool(self):
        """USD dividend +10 (9.0 EUR) and correction −4 (−3.6 EUR), same day, target EUR: native pool 6 USD,
        target pool 5.4 EUR = 9.0 + (−3.6); the lot gets 5.4 EUR.

        Before MF-F1: native pool 14 USD, target pool 12.6 EUR, lot income 12.6.
        """
        result = _run(
            [_buy(1, "10", "100", on="2025-01-01", currency="USD")],
            [
                _dividend(90, "10", on="2025-01-20", native_currency="USD", target_amount="9.0"),
                _dividend(91, "-4", on="2025-01-20", native_currency="USD", target_amount="-3.6"),
            ],
        )

        pool = _pool(result, 90, 91)
        assert (pool.native_currency, pool.target_currency) == ("USD", "EUR")
        assert pool.native_pool_total == D("6")
        assert pool.target_pool_total == D("9.0") + D("-3.6") == D("5.4")
        allocation = _lot_allocations(pool)[1]
        assert (allocation.native_amount, allocation.target_amount) == (D("6"), D("5.4"))
        assert _lot_income(result, 1) == D("5.4")

    def test_a_later_usd_correction_counts_at_its_own_rate(self):
        """USD +10 at 0.9 (9.0 EUR) on 20 Jan, USD −4 at 0.8 (−3.2 EUR) on 10 Feb: lot income 5.8 EUR.

        Before MF-F1: the correction pool 4 USD / 3.2 EUR, lot income 12.2.
        """
        result = _run(
            [_buy(1, "10", "100", on="2025-01-01", currency="USD")],
            [
                _dividend(90, "10", on="2025-01-20", native_currency="USD", target_amount="9.0"),
                _dividend(91, "-4", on="2025-02-10", native_currency="USD", target_amount="-3.2"),
            ],
        )

        correction = _pool(result, 91)
        assert (correction.native_pool_total, correction.target_pool_total) == (D("-4"), D("-3.2"))
        assert _lot_allocations(correction)[1].native_amount == D("-4")
        assert _lot_income(result, 1) == D("5.8")


# --------------------------------------------------------------------------- #
# Lots-analysis level: the builder hands the sign over, the service views read the net income
# --------------------------------------------------------------------------- #


def _row(tx_id: int, tx_type: TransactionType, *, on: date, quantity: str = "0", amount: str, currency: str = "EUR") -> Transaction:
    """An in-memory Transaction row. Never added to a session."""
    return Transaction(
        id=tx_id,
        broker_id=BROKER,
        asset_id=ASSET_ID,
        type=tx_type,
        date=on,
        quantity=D(quantity),
        amount=D(amount),
        currency=currency,
    )


def _resolver(target: str, rates: dict[tuple[str, date], Decimal] | None = None) -> FxRateResolver:
    """An FxRateResolver whose rate table is filled by hand: ``load()`` is its only part that needs a session."""
    resolver = FxRateResolver(target)
    for key, rate in (rates or {}).items():
        resolver._rates[key] = rate
    return resolver


class TestLotsAnalysisWiring:
    def test_the_builder_hands_the_sign_of_a_correction_to_the_engine(self):
        """GUARD: ``build_income_economic_events`` keeps the stored sign, native and converted (−4 USD × 0.9 = −3.6 EUR)."""
        on = date(2024, 3, 1)
        events = build_income_economic_events(
            income_transactions=[
                _row(3, TransactionType.DIVIDEND, on=on, amount="-4", currency="USD"),
                _row(4, TransactionType.INTEREST, on=on, amount="-2", currency="USD"),
            ],
            fx_resolver=_resolver("EUR", {("USD", on): D("0.9")}),
            asset_currency="USD",
            target_currency="EUR",
        )

        by_id = {event.transaction_id: event for event in events}
        assert set(by_id) == {3, 4}
        assert (by_id[3].economic_type, by_id[3].native_amount, by_id[3].target_amount) == ("DIVIDEND", D("-4"), D("-3.6"))
        assert (by_id[4].economic_type, by_id[4].native_amount, by_id[4].target_amount) == ("INTEREST", D("-2"), D("-1.8"))

    def test_the_lot_income_and_its_history_read_the_net_income(self):
        """BUY 10 on 10 Jan, DIVIDEND +10 on 1 Feb, DIVIDEND −4 on 1 Mar, through the lots-analysis pipeline.

        ``income_by_lot`` 6; the lot's cumulative income history 10 then 6; the mapped audit pool of the correction
        −4. The income-event markers already carried the signed amounts (+10, −4) before MF-F1.
        Before MF-F1: ``income_by_lot`` 14, history 10 then 14, mapped correction pool +4.
        """
        buy = _row(1, TransactionType.BUY, on=date(2024, 1, 10), quantity="10", amount="-1000")
        income_rows = [
            _row(2, TransactionType.DIVIDEND, on=date(2024, 2, 1), amount="10"),
            _row(3, TransactionType.DIVIDEND, on=date(2024, 3, 1), amount="-4"),
        ]
        events = build_income_economic_events(income_transactions=income_rows, fx_resolver=_resolver("EUR"), asset_currency="EUR", target_currency="EUR")
        result = run_fifo_lot_engine([buy], {BROKER: False}, economic_events=events, target_currency="EUR")

        income_by_lot, income_prefix_by_lot, payload = extract_income_outputs(result, events)

        assert income_by_lot == {1: D("6")}
        assert income_prefix_by_lot == {1: {date(2024, 2, 1): D("10"), date(2024, 3, 1): D("6")}}
        assert {marker.transaction_id: (marker.amount, marker.lot_ids) for marker in payload} == {2: (D("10"), [1]), 3: (D("-4"), [1])}

        mapped = {tuple(group.source_transaction_ids): group for group in map_economic_groups(result.economic_allocation_groups)}
        assert set(mapped) == {(2,), (3,)}
        assert (mapped[(3,)].native_pool_total, mapped[(3,)].target_pool_total) == (D("-4"), D("-4"))
