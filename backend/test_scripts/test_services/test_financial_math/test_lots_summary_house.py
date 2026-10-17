"""
MF-E1 (workstream MF): the lot summary's figures in the house, one residual-cost formula.

Module under test: ``backend/app/services/financial_math/lots/summary.py``, new. Two of its functions are
pinned here, by name and signature:

* ``residual_cost(original_cost, open_quantity, original_quantity)``: the original cost of the still-open
  quantity, ``original_cost × |open_quantity| / |original_quantity|``. ``0`` when nothing is open, whatever
  the cost (a closed lot has no residual); ``None`` when the lot is open and its cost unknown (a missing FX
  rate); ``0`` on a zero original quantity once the cost is known. It is HEAD's
  ``ai_export/components/payloads/portfolio_broker.py::lot_residual_cost_basis``, which delegates to it
  after MF-E1;
* ``lot_value(direction, open_value, proceeds, buybacks, original_cost) -> (total_value, pnl)``: a LONG
  lot is worth what is still open plus what it sold for, its P&L that minus its cost; a SHORT lot is worth
  what it sold for minus what it bought back minus what it still owes at market, and that is its P&L. It
  is HEAD's two copies of the branch, ``lots_analysis_service._build_lot_summaries`` and
  ``financial_math/lots/histories.py::_value_snapshot_on_date``.

The summary's other figures move into the house as well (``lot_summary_figures``), with a signature this
file does not pin: their parity is the existing lots-analysis service tests' (``services lots-analysis-pure``,
``test_financial/test_lots_analysis_service.py`` in ``services roi-fifo-utils``), unchanged.

Each old formula is written inline below, as it stood at HEAD (5c9ad06d7), and compared with the new
function on ``str()`` — value *and* exponent: the move must not change a digit. ``residual_cost`` is
also compared with the live ``lot_residual_cost_basis``, the AI Export's entry point, so its delegation
cannot drift either.

Red by absence before MF-E1: the module is imported while each test runs (``_summary()``), never at
module level, so the file collects on HEAD and every test fails on ``ModuleNotFoundError``.

Pure: no database, no server, no network.
"""

from __future__ import annotations

import importlib
from decimal import Decimal
from types import ModuleType, SimpleNamespace

import pytest

SUMMARY_MODULE = "backend.app.services.financial_math.lots.summary"


def _summary() -> ModuleType:
    """``financial_math/lots/summary.py``, imported when a test runs: until MF-E1 it does not exist."""
    return importlib.import_module(SUMMARY_MODULE)


def _d(text: str | None) -> Decimal | None:
    return None if text is None else Decimal(text)


def _text(value: Decimal | None) -> str | None:
    """``str()`` of a figure — value and exponent — or None."""
    return None if value is None else str(value)


# =============================================================================
# residual_cost
# =============================================================================


def _head_lot_residual_cost_basis(original_cost: Decimal | None, open_quantity: Decimal, original_quantity: Decimal) -> Decimal | None:
    """HEAD's ``lot_residual_cost_basis``, its reads of the lot's attributes replaced by the three arguments."""
    open_quantity = abs(open_quantity)
    if open_quantity.is_zero():
        return Decimal("0")
    if original_cost is None:
        return None
    original_quantity = abs(original_quantity)
    if original_quantity.is_zero():
        return Decimal("0")
    return original_cost * open_quantity / original_quantity


# (original_cost, open_quantity, original_quantity) — shorts carry negative quantities.
_RESIDUAL_CORPUS = [
    pytest.param("1000", "10", "10", id="long-whole-lot-open"),
    pytest.param("1000", "5", "10", id="long-partial"),
    pytest.param("1000.00", "5", "10", id="long-partial-cost-with-cents-keeps-its-exponent"),
    pytest.param("1000.50", "3", "7", id="long-repeating-quotient"),
    pytest.param("123.456", "0.5", "1.5", id="long-fractional-quantities"),
    pytest.param("0", "5", "10", id="long-zero-cost"),
    pytest.param("1000", "-10", "-10", id="short-whole-lot-open"),
    pytest.param("1500", "-4", "-10", id="short-partial"),
    pytest.param("2000", "-1", "-3", id="short-repeating-quotient"),
    pytest.param("1000", "-5", "10", id="mixed-signs-read-as-absolute-quantities"),
    pytest.param("1000", "0", "10", id="long-closed"),
    pytest.param("1000", "0.000", "10", id="long-closed-zero-with-exponent"),
    pytest.param("1500", "0", "-10", id="short-closed"),
    pytest.param(None, "0", "10", id="closed-with-unknown-cost-is-zero"),
    pytest.param(None, "0", "-10", id="short-closed-with-unknown-cost-is-zero"),
    pytest.param(None, "5", "10", id="open-with-unknown-cost-is-unknown"),
    pytest.param(None, "-5", "-10", id="short-open-with-unknown-cost-is-unknown"),
    pytest.param("1000", "5", "0", id="zero-original-quantity-is-zero"),
    pytest.param(None, "1", "0", id="zero-original-quantity-with-unknown-cost-is-unknown"),
]


class TestResidualCost:
    """``residual_cost`` is HEAD's ``lot_residual_cost_basis``, digit for digit."""

    @pytest.mark.parametrize(("original_cost", "open_quantity", "original_quantity"), _RESIDUAL_CORPUS)
    def test_parity_with_the_old_formula(self, original_cost, open_quantity, original_quantity):
        residual_cost = _summary().residual_cost
        arguments = (_d(original_cost), _d(open_quantity), _d(original_quantity))

        assert _text(residual_cost(*arguments)) == _text(_head_lot_residual_cost_basis(*arguments))

    @pytest.mark.parametrize(("original_cost", "open_quantity", "original_quantity"), _RESIDUAL_CORPUS)
    def test_the_ai_export_entry_point_gives_the_same_figure(self, original_cost, open_quantity, original_quantity):
        """``lot_residual_cost_basis`` reads a lot's three attributes and delegates: the same figure for the same lot."""
        residual_cost = _summary().residual_cost
        from backend.app.services.ai_export.components.payloads.portfolio_broker import lot_residual_cost_basis  # noqa: PLC0415 — test-local, as the module under test

        lot = SimpleNamespace(original_cost=_d(original_cost), open_quantity=_d(open_quantity), original_quantity=_d(original_quantity))

        assert _text(lot_residual_cost_basis(lot)) == _text(residual_cost(lot.original_cost, lot.open_quantity, lot.original_quantity))

    def test_the_figures_of_the_contract(self):
        """The rules in plain numbers, so a wrong oracle could not hide behind parity."""
        residual_cost = _summary().residual_cost

        assert {
            "half of a long lot open": residual_cost(Decimal("1000"), Decimal("5"), Decimal("10")),
            "four tenths of a short lot open": residual_cost(Decimal("1500"), Decimal("-4"), Decimal("-10")),
            "closed, cost known": residual_cost(Decimal("1000"), Decimal("0"), Decimal("10")),
            "closed, cost unknown": residual_cost(None, Decimal("0"), Decimal("10")),
            "open, cost unknown": residual_cost(None, Decimal("5"), Decimal("10")),
            "zero original quantity": residual_cost(Decimal("1000"), Decimal("5"), Decimal("0")),
        } == {
            "half of a long lot open": Decimal("500"),
            "four tenths of a short lot open": Decimal("600"),
            "closed, cost known": Decimal("0"),
            "closed, cost unknown": Decimal("0"),
            "open, cost unknown": None,
            "zero original quantity": Decimal("0"),
        }


# =============================================================================
# lot_value
# =============================================================================


def _head_lot_value(direction: str, open_value: Decimal, proceeds: Decimal, buybacks: Decimal, original_cost: Decimal) -> tuple[Decimal, Decimal]:
    """HEAD's branch, as ``_value_snapshot_on_date`` and ``_build_lot_summaries`` both wrote it."""
    if direction == "LONG":
        total_value = open_value + proceeds
        pnl = total_value - original_cost
    else:
        total_value = proceeds - buybacks - open_value
        pnl = total_value
    return total_value, pnl


# (direction, open_value, proceeds, buybacks, original_cost)
_VALUE_CORPUS = [
    pytest.param("LONG", "1014", "676", "0", "1200", id="long-partial-gain"),
    pytest.param("LONG", "500.00", "0", "0", "1000", id="long-untouched-loss-keeps-its-exponent"),
    pytest.param("LONG", "0", "1350.5", "0", "1000", id="long-closed"),
    pytest.param("LONG", "333.3333333333333333333333333", "0.01", "0", "1000.10", id="long-repeating-open-value"),
    pytest.param("LONG", "1200", "0", "0", "1200", id="long-break-even"),
    pytest.param("LONG", "800", "200", "75", "1000", id="long-ignores-buybacks"),
    pytest.param("SHORT", "400", "1000", "0", "1000", id="short-open-gain"),
    pytest.param("SHORT", "1300", "1000", "0", "1000", id="short-open-loss"),
    pytest.param("SHORT", "0", "1000", "850.25", "1000", id="short-bought-back"),
    pytest.param("SHORT", "250.50", "1000.00", "400", "999", id="short-partly-bought-back-ignores-cost"),
]


class TestLotValue:
    """``lot_value`` is HEAD's LONG/SHORT branch, digit for digit, in both of its copies."""

    @pytest.mark.parametrize(("direction", "open_value", "proceeds", "buybacks", "original_cost"), _VALUE_CORPUS)
    def test_parity_with_the_old_formula(self, direction, open_value, proceeds, buybacks, original_cost):
        lot_value = _summary().lot_value
        arguments = (Decimal(open_value), Decimal(proceeds), Decimal(buybacks), Decimal(original_cost))

        total_value, pnl = lot_value(direction, *arguments)

        assert (str(total_value), str(pnl)) == tuple(str(figure) for figure in _head_lot_value(direction, *arguments))

    def test_the_figures_of_the_contract(self):
        """The rules in plain numbers: a long lot gains on its cost, a short lot's value is its P&L."""
        lot_value = _summary().lot_value

        assert {
            "long, 6 open at 169 and 4 sold for 676, cost 1200": lot_value("LONG", Decimal("1014"), Decimal("676"), Decimal("0"), Decimal("1200")),
            "short, sold for 1000, 300 bought back, 400 still owed": lot_value("SHORT", Decimal("400"), Decimal("1000"), Decimal("300"), Decimal("1000")),
        } == {
            "long, 6 open at 169 and 4 sold for 676, cost 1200": (Decimal("1690"), Decimal("490")),
            "short, sold for 1000, 300 bought back, 400 still owed": (Decimal("300"), Decimal("300")),
        }
