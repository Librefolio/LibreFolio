"""CP-16 — decision 47: a negative ADJUSTMENT that carries a cost hands its units over at that cost (FIFO lot engine).

Workstream J «Numeri e analisi», release 1.3. Pure engine: ``run_fifo_lot_engine`` on hand-written
``FifoInputTransaction`` rows — no DB, no server, no FX.

THE RULES — decision 47 (J-11, «the same principle in the opposite direction») and the coordinator's decisions
of 15/10, in ``backend/app/services/financial_math/fifo/engine.py``:

1. A negative ADJUSTMENT with ``cost_basis_override`` (per unit, in ``cost_basis_currency``) hands its units
   over at that cost. READING (b): every consumed fragment closes at the override — the ROW's average cost,
   not the fragment's own FIFO cost (``_apply_adjustment_out``) — so ``realized_pnl = q × (override − fragment
   unit price)`` and ``proceeds = q × override``: the value handed over at cost counts as proceeds
   (``_close_position_piece``). That keeps the lot summary's ``pnl = open value + Σ proceeds − cost`` equal to
   the Dashboard's, which reads the same row as a capital distribution at the pool's average cost
   (``DailyStateBuilder._is_capital_adjustment``). With one lot readings (a) and (b) coincide (the decision's
   example); with several, only (b) keeps lots = Dashboard and a split pair neutral (pair test).
2. Without an override the units leave at 0 — proceeds 0, realized −cost — as a quantity correction.
3. Currency — CP-7a, developer's decision 26 (D-J1, option B): the override always applies, in its own
   currency. Every consumed fragment closes at the override, and the closure carries the currency of that price
   as ``close_currency``: ``cost_basis_currency``, or the lot's currency when it is None; without an override
   (rule 2) the lot's currency. A lot whose ``currency`` is None counts as the engine's ``target_currency``
   (that is how the lots FX resolver reads None). When the closure's currency differs from the lot's the
   closure is mixed: the engine has no rates, so its native ``realized_pnl`` is None, and so are the lot's
   ``realized_pnl`` and ``cumulative_proceeds`` from then on, while ``proceeds = q × override`` stay, native in
   ``close_currency``. The lots analysis converts each leg at its own date (``lots/conversions.py``,
   ``convert_closure``). Before CP-7a such a fragment left at its OWN FIFO cost — close price = fragment unit
   price, realized 0, proceeds = q × that cost: CP-16's declared fallback, which CP-7a removed.
4. J-9: a lot opened by a positive ADJUSTMENT whose price comes from ``cost_basis_override`` is in
   ``cost_basis_currency``; without an override it keeps the row's ``currency``.

Before CP-16 every negative ADJUSTMENT closed at price 0, with or without an override, and only a SELL had
proceeds: units leaving with a cost read as destroyed (realized −cost, proceeds 0) while the Dashboard read them
as handed over at cost; and a priced ADJUSTMENT-in opened its lot in the row's ``currency``, often None. Each
docstring keeps the values its test read then. GUARD (in a docstring or a parameter id) marks a test whose values
CP-16 left as they were. CP-7a rewrote rule 3: the docstrings of ``TestCurrencyOfTheHandover`` say what each test
read before it, when a closure had no ``close_currency``.
"""

from datetime import date
from decimal import Decimal

import pytest

from backend.app.services.financial_math.fifo.engine import run_fifo_lot_engine
from backend.app.services.financial_math.fifo.models import FifoEngineResult, FifoInputTransaction, FifoLot, LotClosure

D = Decimal
ASSET_ID = 4716
BROKER_A = 1
BROKER_B = 2
PRICE_P = D("30")  # the pair test's valuation price


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #


def _buy(tx_id: int, quantity: str, unit_price: str, *, on: str, broker_id: int = BROKER_A, currency: str | None = "EUR") -> FifoInputTransaction:
    """A purchase of ``quantity`` at ``unit_price`` a unit: amount = −quantity × unit price, in ``currency``."""
    return FifoInputTransaction(
        id=tx_id,
        broker_id=broker_id,
        asset_id=ASSET_ID,
        date=date.fromisoformat(on),
        type="BUY",
        quantity=D(quantity),
        amount=-(D(quantity) * D(unit_price)),
        currency=currency,
    )


def _adjustment(
    tx_id: int,
    quantity: str,
    *,
    on: str,
    broker_id: int = BROKER_A,
    override: str | None = None,
    override_currency: str | None = None,
    currency: str | None = None,
) -> FifoInputTransaction:
    """An ADJUSTMENT: no cash (amount 0), a per-unit ``cost_basis_override`` in ``override_currency`` or none.

    ``currency`` is the row's own, None by default: the app leaves it empty when the amount is 0.
    """
    return FifoInputTransaction(
        id=tx_id,
        broker_id=broker_id,
        asset_id=ASSET_ID,
        date=date.fromisoformat(on),
        type="ADJUSTMENT",
        quantity=D(quantity),
        amount=D("0"),
        currency=currency,
        cost_basis_override=None if override is None else D(override),
        cost_basis_currency=override_currency,
    )


def _transfer_pair(
    out_id: int,
    in_id: int,
    quantity: str,
    *,
    on: str,
    out_broker_id: int,
    in_broker_id: int,
    in_override: str | None = None,
    in_override_currency: str | None = None,
) -> tuple[FifoInputTransaction, FifoInputTransaction]:
    """A linked TRANSFER pair, both legs on one day; the receiving leg may carry a cost basis.

    The engine moves the FIFO fragments themselves, at their own cost: it never reads the receiving
    leg's cost basis.
    """
    out_leg = FifoInputTransaction(
        id=out_id,
        broker_id=out_broker_id,
        asset_id=ASSET_ID,
        date=date.fromisoformat(on),
        type="TRANSFER",
        quantity=-D(quantity),
        related_transaction_id=in_id,
    )
    in_leg = FifoInputTransaction(
        id=in_id,
        broker_id=in_broker_id,
        asset_id=ASSET_ID,
        date=date.fromisoformat(on),
        type="TRANSFER",
        quantity=D(quantity),
        related_transaction_id=out_id,
        cost_basis_override=None if in_override is None else D(in_override),
        cost_basis_currency=in_override_currency,
    )
    return out_leg, in_leg


def _run(transactions: list[FifoInputTransaction], *, target_currency: str = "EUR") -> FifoEngineResult:
    """The engine as the lots analysis calls it, in ``target_currency``, without shorting.

    No reference price lookup: a lot opened by an ADJUSTMENT-in may then carry REFERENCE_PRICE_UNAVAILABLE,
    which nothing here is about — no test asserts the absence of issues.
    """
    return run_fifo_lot_engine(transactions, {BROKER_A: False, BROKER_B: False}, target_currency=target_currency)


def _closures_by_lot(result: FifoEngineResult, transaction_id: int) -> dict[int, dict]:
    """What one transaction closed, lot by lot: found by the transaction's id, never by position."""
    closures = [closure for closure in result.closures if closure.transaction_id == transaction_id]
    by_lot = {closure.lot_id: _closure_view(closure) for closure in closures}
    assert len(by_lot) == len(closures), f"precondition: one closure per lot for transaction {transaction_id}, got {closures}"
    return by_lot


def _closure_view(closure: LotClosure) -> dict:
    return {
        "close_reason": closure.close_reason,
        "quantity": closure.quantity,
        "open_unit_price": closure.open_unit_price,
        "close_unit_price": closure.close_unit_price,
        "realized_pnl": closure.realized_pnl,
        "proceeds": closure.proceeds,
    }


def _lot_view(lot: FifoLot) -> dict:
    return {
        "open_quantity": lot.open_quantity,
        "realized_quantity": lot.realized_quantity,
        "realized_pnl": lot.realized_pnl,
        "cumulative_proceeds": lot.cumulative_proceeds,
    }


def _lots_total(lots: list[FifoLot], price: Decimal) -> Decimal:
    """The lots' P&L at ``price``, in one currency: Σ (open quantity × price + cumulative proceeds − original cost)."""
    return sum((lot.open_quantity * price + lot.cumulative_proceeds - lot.original_cost for lot in lots), D("0"))


def _close_currencies(result: FifoEngineResult, transaction_id: int) -> dict[int, str | None]:
    """The currency each closure of one transaction carries, lot by lot: CP-7a's ``LotClosure.close_currency``."""
    return {closure.lot_id: closure.close_currency for closure in result.closures if closure.transaction_id == transaction_id}


def _money(value: str | None) -> Decimal | None:
    """An expected amount; None where CP-7a leaves a native figure unknown, its two currencies having no rate in the engine."""
    return None if value is None else D(value)


def _closure(close_reason: str, quantity: str, open_unit_price: str, close_unit_price: str, realized_pnl: str | None, proceeds: str) -> dict:
    """An expected closure, in the shape of ``_closure_view``."""
    return {
        "close_reason": close_reason,
        "quantity": D(quantity),
        "open_unit_price": D(open_unit_price),
        "close_unit_price": D(close_unit_price),
        "realized_pnl": _money(realized_pnl),
        "proceeds": D(proceeds),
    }


def _lot(open_quantity: str, realized_quantity: str, realized_pnl: str | None, cumulative_proceeds: str | None) -> dict:
    """An expected lot, in the shape of ``_lot_view``."""
    return {
        "open_quantity": D(open_quantity),
        "realized_quantity": D(realized_quantity),
        "realized_pnl": _money(realized_pnl),
        "cumulative_proceeds": _money(cumulative_proceeds),
    }


# --------------------------------------------------------------------------- #
# One lot: decision 47's example, and the row without a cost
# --------------------------------------------------------------------------- #


class TestOneLotHandedOverAtCost:
    def test_the_decision_47_example_hands_four_units_over_at_their_cost(self):
        """Decision 47's example: 10 bought at 20 EUR, 4 handed over by an ADJUSTMENT −4 carrying 20 EUR a unit.

        One lot, so readings (a) and (b) coincide: the 4 units close at 20 — realized 4 × (20 − 20) = 0 — and the
        80 EUR handed over at cost are the closure's proceeds, which is what makes the lot summary read
        6 × 30 + 80 − 200 = 60 like the Dashboard (test_adjustment_out_with_cost_numbers.py).
        Before CP-16: close price 0, realized −80, proceeds 0 — the 4 units read as destroyed.
        """
        result = _run(
            [
                _buy(1, "10", "20", on="2018-10-01"),
                _adjustment(2, "-4", on="2018-10-03", override="20", override_currency="EUR"),
            ]
        )

        observed = {"closures of the ADJUSTMENT": _closures_by_lot(result, 2), "lot 1": _lot_view(result.get_lot(1))}

        assert observed == {
            "closures of the ADJUSTMENT": {1: _closure("ADJUSTMENT_OUT", "4", "20", "20", "0", "80")},
            "lot 1": _lot("6", "4", "0", "80"),
        }

    def test_without_an_override_the_units_still_leave_at_zero(self):
        """GUARD (rule 2), the contrast with decision 47's example: the same ADJUSTMENT −4 without a cost.

        Nothing tells the engine what the units were worth, so they close at 0 — realized −80, proceeds 0 — and the
        closure keeps its reason ADJUSTMENT_OUT: the values of before CP-16, unchanged.
        """
        result = _run(
            [
                _buy(1, "10", "20", on="2018-10-01"),
                _adjustment(2, "-4", on="2018-10-03"),
            ]
        )

        observed = {"closures of the ADJUSTMENT": _closures_by_lot(result, 2), "lot 1": _lot_view(result.get_lot(1))}

        assert observed == {
            "closures of the ADJUSTMENT": {1: _closure("ADJUSTMENT_OUT", "4", "20", "0", "-80", "0")},
            "lot 1": _lot("6", "4", "-80", "0"),
        }


# --------------------------------------------------------------------------- #
# Several lots: reading (b), the row's average cost
# --------------------------------------------------------------------------- #


class TestSeveralLotsReadingB:
    """Reading (b), chosen by the coordinator (15/10): every fragment leaves at the ROW's average cost.

    A: 10 bought at 10 (lot 1), 10 bought at 20 (lot 2); the Auto cost of the pool is their average, 15. Under
    (b) lot 1's units realize the difference between their FIFO cost and the average they leave at, +5 a unit;
    under (a) they would leave at their own 10 and realize nothing — the coordinator ruled out (a), so no test pins it.
    """

    def test_a_handover_of_the_first_lot_closes_it_at_the_rows_average_cost(self):
        """−10 at 15 consumes lot 1 whole: closed at 15, realized 10 × (15 − 10) = +50, proceeds 150; lot 2 untouched.

        Before CP-16: lot 1 closed at 0, realized −100, proceeds 0.
        """
        result = _run(
            [
                _buy(1, "10", "10", on="2025-01-01"),
                _buy(2, "10", "20", on="2025-01-02"),
                _adjustment(3, "-10", on="2025-01-03", override="15", override_currency="EUR"),
            ]
        )

        observed = {
            "closures of the ADJUSTMENT": _closures_by_lot(result, 3),
            "lot 1": _lot_view(result.get_lot(1)),
            "lot 2": _lot_view(result.get_lot(2)),
        }

        assert observed == {
            "closures of the ADJUSTMENT": {1: _closure("ADJUSTMENT_OUT", "10", "10", "15", "50", "150")},
            "lot 1": _lot("0", "10", "50", "150"),
            "lot 2": _lot("10", "0", "0", "0"),
        }

    def test_a_handover_that_crosses_two_lots_closes_both_at_the_rows_average_cost(self):
        """−15 at 15: lot 1's 10 at 15 (+50, proceeds 150), then 5 of lot 2 at 15 (5 × (15 − 20) = −25, proceeds 75).

        Together: realized +25 and proceeds 225 = 15 × 15, the cost the row hands over; lot 2 keeps 5 open.
        Before CP-16: both pieces closed at 0 — realized −100 and −100, proceeds 0.
        """
        result = _run(
            [
                _buy(1, "10", "10", on="2025-01-01"),
                _buy(2, "10", "20", on="2025-01-02"),
                _adjustment(3, "-15", on="2025-01-03", override="15", override_currency="EUR"),
            ]
        )
        lots = [result.get_lot(1), result.get_lot(2)]

        observed = {
            "closures of the ADJUSTMENT": _closures_by_lot(result, 3),
            "lot 1": _lot_view(lots[0]),
            "lot 2": _lot_view(lots[1]),
            "realized, both lots": sum((lot.realized_pnl for lot in lots), D("0")),
            "proceeds, both lots": sum((lot.cumulative_proceeds for lot in lots), D("0")),
        }

        assert observed == {
            "closures of the ADJUSTMENT": {
                1: _closure("ADJUSTMENT_OUT", "10", "10", "15", "50", "150"),
                2: _closure("ADJUSTMENT_OUT", "5", "20", "15", "-25", "75"),
            },
            "lot 1": _lot("0", "10", "50", "150"),
            "lot 2": _lot("5", "5", "-25", "75"),
            "realized, both lots": D("25"),
            "proceeds, both lots": D("225"),
        }


# --------------------------------------------------------------------------- #
# Why (b): a pair split into two adjustments creates no P&L
# --------------------------------------------------------------------------- #


def _intact_book() -> list[FifoInputTransaction]:
    """A: 10 at 10 and 10 at 20; on 3 Jan 10 units move A → B by a linked TRANSFER, B's leg costed at 15 EUR."""
    return [
        _buy(1, "10", "10", on="2025-01-01"),
        _buy(2, "10", "20", on="2025-01-02"),
        *_transfer_pair(3, 4, "10", on="2025-01-03", out_broker_id=BROKER_A, in_broker_id=BROKER_B, in_override="15", in_override_currency="EUR"),
    ]


def _split_book() -> list[FifoInputTransaction]:
    """The same move as two ADJUSTMENTs, as «split the pair» leaves it: A −10 at 15 EUR, B +10 at 15 EUR."""
    return [
        _buy(1, "10", "10", on="2025-01-01"),
        _buy(2, "10", "20", on="2025-01-02"),
        _adjustment(3, "-10", on="2025-01-03", broker_id=BROKER_A, override="15", override_currency="EUR"),
        _adjustment(4, "10", on="2025-01-03", broker_id=BROKER_B, override="15", override_currency="EUR"),
    ]


class TestSplitPairInvariance:
    """Reading (b) keeps the combined view neutral: A hands over at 15 and B opens at 15, so no P&L appears or vanishes.

    Valued at P = 30, the intact book's lots are worth 10 × 30 − 100 (lot 1, now at B) + 10 × 30 − 200 (lot 2) =
    300. The split book reads the same: lot 1 closed at 15 (150 − 100 = +50), lot 2 (+100), B's new lot 4 at
    15 (300 − 150 = +150). Under (a) lot 1 would leave at its own 10 and the split book would read 250; before CP-16
    it left at 0 and the split book read 150.
    """

    @pytest.mark.parametrize(
        ("book", "expected_total"),
        [
            pytest.param(_intact_book, D("300"), id="GUARD-intact-transfer-pair"),
            pytest.param(_split_book, D("300"), id="split-into-two-adjustments"),
        ],
    )
    def test_the_combined_lots_total_does_not_depend_on_how_the_units_moved(self, book, expected_total):
        """Σ over every lot of (open quantity × 30 + cumulative proceeds − original cost): 300 for both books.

        The intact book is a GUARD: a TRANSFER moves the fragments themselves, at their own cost, as before CP-16.
        Before CP-16 the split book read 150 (lot 1 −100, lot 2 +100, lot 4 +150).
        """
        result = _run(book())

        assert _lots_total(result.lots, PRICE_P) == expected_total

    def test_in_the_split_book_the_sender_keeps_what_the_dashboard_gives_it(self):
        """A's own lots in the split book: lot 1 +50 (closed at 15) and lot 2 +100 → 150.

        That is the Dashboard's figure for A: NAV 10 × 30 = 300 against a capital of 100 + 200 − 150 = 150 — the two
        purchases, less the 150 handed over at the pool's average cost, which leave the capital. Before CP-16: 0
        (lot 1 −100, lot 2 +100).
        """
        result = _run(_split_book())
        lots_of_a = [lot for lot in result.lots if lot.opening_broker_id == BROKER_A]

        assert {lot.lot_id for lot in lots_of_a} == {1, 2}, "precondition: A's lots are its two purchases"
        assert _lots_total(lots_of_a, PRICE_P) == D("150")


# --------------------------------------------------------------------------- #
# Currency: the units leave at the override, in the override's currency (CP-7a)
# --------------------------------------------------------------------------- #


class TestCurrencyOfTheHandover:
    """Rule 3 since CP-7a (developer's decision 26, D-J1 option B): every fragment leaves at the override, in its currency.

    The closure carries that currency as ``close_currency``; when it is not the lot's the closure is mixed and the engine
    states no native realized P&L. Before CP-7a an override in another currency than the lot's left the fragment at its
    own FIFO cost (CP-16's declared fallback) and no closure had a currency: each docstring says what its test read then.
    """

    def test_an_override_in_another_currency_hands_the_units_over_at_the_override_in_that_currency(self):
        """10 bought at 20 USD, an ADJUSTMENT −4 costed at 18 EUR, report EUR: the 4 close at 18 in EUR, proceeds 72, no native realized P&L.

        18 EUR less a 20 USD cost has no meaning in the engine, which has no rates: the closure's realized P&L is None, and
        the lot's realized P&L and cumulative proceeds are None from then on. The lots analysis converts each leg at its own
        date (convert_closure). Before CP-7a (CP-16's fallback): close price 20 — the fragment's own FIFO cost — realized 0,
        proceeds 80 in the lot's USD, the 18 EUR nowhere; lot 1 realized 0, cumulative proceeds 80.
        """
        result = _run(
            [
                _buy(1, "10", "20", on="2025-01-01", currency="USD"),
                _adjustment(2, "-4", on="2025-01-03", override="18", override_currency="EUR"),
            ],
            target_currency="EUR",
        )

        observed = {"closures of the ADJUSTMENT": _closures_by_lot(result, 2), "lot 1": _lot_view(result.get_lot(1))}

        assert observed == {
            "closures of the ADJUSTMENT": {1: _closure("ADJUSTMENT_OUT", "4", "20", "18", None, "72")},
            "lot 1": _lot("6", "4", None, None),
        }
        assert _close_currencies(result, 2) == {1: "EUR"}

    def test_an_override_without_a_currency_counts_in_the_lots_currency(self):
        """An override whose cost_basis_currency is None counts in the lot's currency: 10 at 20 USD, −4 at 25, report EUR.

        The 4 units close at 25 in USD, the lot's currency — one currency, so a native realized P&L: 4 × (25 − 20) = +20,
        proceeds 100. Before CP-7a: the same values, and no close_currency. (Before CP-16: close price 0, realized −80,
        proceeds 0.)
        """
        result = _run(
            [
                _buy(1, "10", "20", on="2025-01-01", currency="USD"),
                _adjustment(2, "-4", on="2025-01-03", override="25", override_currency=None),
            ],
            target_currency="EUR",
        )

        observed = {"closures of the ADJUSTMENT": _closures_by_lot(result, 2), "lot 1": _lot_view(result.get_lot(1))}

        assert observed == {
            "closures of the ADJUSTMENT": {1: _closure("ADJUSTMENT_OUT", "4", "20", "25", "20", "100")},
            "lot 1": _lot("6", "4", "20", "100"),
        }
        assert _close_currencies(result, 2) == {1: "USD"}

    def test_without_an_override_a_foreign_lot_hands_over_in_its_own_currency(self):
        """Rule 2 on a lot in USD, report EUR: an ADJUSTMENT −4 without a cost closes at 0 in the lot's currency, USD — never mixed.

        So its native realized P&L stays −80 and the lot's too, proceeds 0: GUARD values, as before CP-7a. Read in the row's
        currency instead (None, the report's EUR) the zero-price correction would be mixed and lose its realized P&L.
        Before CP-7a: the same values, and no close_currency.
        """
        result = _run(
            [
                _buy(1, "10", "20", on="2025-01-01", currency="USD"),
                _adjustment(2, "-4", on="2025-01-03"),
            ],
            target_currency="EUR",
        )

        observed = {"closures of the ADJUSTMENT": _closures_by_lot(result, 2), "lot 1": _lot_view(result.get_lot(1))}

        assert observed == {
            "closures of the ADJUSTMENT": {1: _closure("ADJUSTMENT_OUT", "4", "20", "0", "-80", "0")},
            "lot 1": _lot("6", "4", "-80", "0"),
        }
        assert _close_currencies(result, 2) == {1: "USD"}

    @pytest.mark.parametrize(
        ("target_currency", "expected_realized", "expected_lot_realized", "expected_lot_proceeds"),
        [
            pytest.param("EUR", "100", "100", "100", id="report-EUR-the-override-is-in-the-lots-currency"),
            pytest.param("USD", None, None, None, id="report-USD-the-override-is-in-another-currency"),
        ],
    )
    def test_a_lot_without_a_currency_counts_in_the_report_currency(self, target_currency, expected_realized, expected_lot_realized, expected_lot_proceeds):
        """A lot whose currency is None counts as the report currency, as the lots FX resolver reads it.

        Lot 1: ADJUSTMENT +10 without a cost (currency None, unit price 0); lot 2: 10 bought at 20 EUR; then an
        ADJUSTMENT −10 costed at 10 EUR (the Auto average of 0 and 20), which consumes lot 1 whole at the override:
        close price 10 in EUR, proceeds 100, whatever the report currency.
        - Report EUR: lot 1 counts as EUR, the override's currency — one currency: realized 10 × (10 − 0) = +100. The
          values of before CP-7a, which had no close_currency.
        - Report USD: lot 1 counts as USD ≠ EUR — mixed: no native realized P&L, and lot 1's realized P&L and cumulative
          proceeds are None. Before CP-7a (CP-16's fallback): close price 0, its own cost, realized 0, proceeds 0.
        Lot 2 is untouched either way.
        """
        result = _run(
            [
                _adjustment(1, "10", on="2025-01-01"),
                _buy(2, "10", "20", on="2025-01-02", currency="EUR"),
                _adjustment(3, "-10", on="2025-01-03", override="10", override_currency="EUR"),
            ],
            target_currency=target_currency,
        )

        observed = {
            "closures of the ADJUSTMENT": _closures_by_lot(result, 3),
            "lot 1": _lot_view(result.get_lot(1)),
            "lot 2": _lot_view(result.get_lot(2)),
        }

        assert observed == {
            "closures of the ADJUSTMENT": {1: _closure("ADJUSTMENT_OUT", "10", "0", "10", expected_realized, "100")},
            "lot 1": _lot("0", "10", expected_lot_realized, expected_lot_proceeds),
            "lot 2": _lot("10", "0", "0", "0"),
        }
        assert _close_currencies(result, 3) == {1: "EUR"}


# --------------------------------------------------------------------------- #
# J-9: the currency of a lot opened by a priced ADJUSTMENT-in
# --------------------------------------------------------------------------- #


class TestLotCurrencyOfAnAdjustmentIn:
    """J-9, CP-16's prerequisite: the lot's currency is the currency its price is in.

    A lot priced by ``cost_basis_override`` is in ``cost_basis_currency``: that is what rule 3 compares the handover's
    currency with, and what the lots analysis converts the lot's cost from. Before CP-16 a lot opened by a positive
    ADJUSTMENT took the row's ``currency`` — usually None, since the row moves no cash — even when its price came from
    the override.
    """

    @pytest.mark.parametrize(
        ("opening", "expected"),
        [
            pytest.param(
                _adjustment(1, "5", on="2025-01-01", override="90", override_currency="USD", currency=None),
                ("USD", D("90"), D("450")),
                id="override-in-USD-row-currency-None",
            ),
            pytest.param(
                _adjustment(1, "5", on="2025-01-01", override="90", override_currency="USD", currency="EUR"),
                ("USD", D("90"), D("450")),
                id="override-in-USD-row-currency-EUR",
            ),
            pytest.param(_adjustment(1, "5", on="2025-01-01", currency=None), (None, D("0"), D("0")), id="GUARD-no-override-row-currency-None"),
            pytest.param(_adjustment(1, "5", on="2025-01-01", currency="EUR"), ("EUR", D("0"), D("0")), id="GUARD-no-override-keeps-the-row-currency"),
            pytest.param(_buy(1, "5", "90", on="2025-01-01", currency="USD"), ("USD", D("90"), D("450")), id="GUARD-buy-in-USD"),
        ],
    )
    def test_the_lot_takes_the_currency_its_price_is_in(self, opening, expected):
        """(currency, opening unit price, original cost) of the lot: J-9 moves only the currency.

        Before CP-16 the two priced ADJUSTMENTs opened their lot in None and in EUR. The GUARDs read as before CP-16:
        without an override the lot keeps the row's currency; a BUY's lot is in the BUY's currency.
        """
        lot = _run([opening], target_currency="EUR").get_lot(1)

        assert (lot.currency, lot.opening_unit_price, lot.original_cost) == expected
