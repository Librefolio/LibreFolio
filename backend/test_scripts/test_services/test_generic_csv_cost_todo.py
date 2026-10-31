"""
The generic CSV asks for the inherited cost only where it is missing (W6-5, J-64).

The plugin puts the blocking todo ``corporate_action`` (field ``cost_basis_override``) on an ADJUSTMENT that adds units and
has no cost. Two defects were found in it (19/10/2026):

- a cost of 0 counted as missing (``float(amount) == 0``): a gift recorded at 0 arrived with the todo and the user had to
  write 0 again, against the decision «0 is a true cost» (Q-J57-3). The cure: ``needs_cost_basis_todo`` asks only when the
  cost is ``None``.
- an outgoing ADJUSTMENT takes no cost (``required_qty_pos``), so a todo on it never closes. Already cured (N78-1,
  ``added_tx.quantity > 0``); pinned here so it stays so.

The generic CSV reads no cost column, so a file cannot carry the 0 today: the rule is pinned on the function that decides,
with the rows a parse of a real file produces as the guard.

Pure: no database, no server; the CSV files live under ``tmp_path``.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from backend.app.config import PROJECT_ROOT  # noqa: F401  (puts the project on sys.path as the other suites do)
from backend.app.db.models import TransactionType
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.services.brim_providers.broker_generic_csv.plugin import GenericCSVBrokerProvider, needs_cost_basis_todo

ASSET_ID = 2**31 - 1
COST_REASON = "corporate_action"


def _adjustment(quantity: str, cost: str | None) -> TXCreateItem:
    """An ADJUSTMENT of ``quantity`` units; ``cost`` is the per-unit cost the row carries, ``None`` for none."""
    return TXCreateItem(
        broker_id=1,
        asset_id=ASSET_ID,
        type=TransactionType.ADJUSTMENT,
        date=date(2025, 3, 1),
        quantity=Decimal(quantity),
        cost_basis_override=None if cost is None else Currency(code="EUR", amount=Decimal(cost)),
    )


class TestWhoIsAskedForACost:
    """The function that decides: one row, one answer."""

    @pytest.mark.parametrize("cost", ("0", "0.00", "12.5"))
    def test_a_cost_written_by_the_user_is_never_missing(self, cost):
        """RED before the cure for 0 and 0.00: a typed 0 was read as «no cost»."""
        assert needs_cost_basis_todo(_adjustment("3", cost)) is False, f"an incoming ADJUSTMENT with a cost of {cost} got the todo"

    def test_an_incoming_adjustment_without_a_cost_is_asked(self):
        """Guard, green before and after."""
        assert needs_cost_basis_todo(_adjustment("3", None)) is True

    def test_an_outgoing_adjustment_is_never_asked(self):
        """Guard (N78-1): an outgoing ADJUSTMENT takes no cost (``TXCreateItem`` refuses one), so a todo on it could never be
        closed."""
        assert needs_cost_basis_todo(_adjustment("-3", None)) is False

    def test_another_type_is_never_asked(self):
        """Guard: only an ADJUSTMENT inherits a cost."""
        deposit = TXCreateItem(broker_id=1, type=TransactionType.DEPOSIT, date=date(2025, 3, 1), cash=Currency(code="EUR", amount=Decimal("10")))
        assert needs_cost_basis_todo(deposit) is False


class TestWhatAParseProduces:
    """Guard, green before and after: the todos of a real file."""

    def test_only_the_incoming_adjustment_gets_the_todo(self, tmp_path: Path):
        csv_file = tmp_path / "adjustments.csv"
        csv_file.write_text("date,type,asset,quantity\n2025-03-01,adjustment,ACME,3\n2025-03-02,adjustment,ACME,-3\n", encoding="utf-8")

        output = GenericCSVBrokerProvider().parse(csv_file, broker_id=1)

        assert [(tx.type, tx.quantity) for tx in output.transactions] == [(TransactionType.ADJUSTMENT, Decimal("3")), (TransactionType.ADJUSTMENT, Decimal("-3"))], f"the rows were not parsed as written: {output.warnings}"
        todos = [(todo.tx_index, todo.field, todo.reason_code) for todo in output.field_todos]
        assert todos == [(0, "cost_basis_override", COST_REASON)], f"only the incoming row (index 0) must ask for a cost, got {todos}"
