"""
The ``as_of`` floor of a fixed-period changes item — R13-SEC8 (E's review of MF-P2), lot MF-P2b.

Before: ``FAPeriodChangesQueryItem`` (``POST /assets/prices/period-changes``) and ``FXPeriodChangesRequest``
(``POST /fx/currencies/period-changes``) took any ``as_of``. The services value ``fixed_period_dates(as_of)``, which is
``as_of − days`` for every period up to 5Y (1825 days): on or before 0005-12-30 that subtraction overflows ``date``, an
``OverflowError`` the route turns into a bare 500; and every day before 1900 is a day nothing is valued on.

Now: ``as_of`` is 1900-01-01 or later (``EARLIEST_RANGE_START``, the replay floor), a ``ValueError`` in the item's
validation, so a pydantic ``ValidationError`` — a 422 on the routes. There is no upper bound: a future ``as_of`` costs
what any other does.

The floor is written out here, not imported: it is the contract R13-SEC8 fixed, and a test that read it from the module
would follow any change of it.

Each refused item is otherwise valid (an asset id, two distinct ISO codes), so the only rule it can break is the floor:
the error's ``loc`` names ``as_of`` and nothing else. A refusal never matches the message text. The days are given as ISO
strings, as the routes receive them.

"Red" tests fail on the code before the fix: it accepts what they expect refused. "Guard" tests pass before and after:
the floor itself is accepted, and so is the last day ``date`` has.

The routes' list caps and the cap on distinct ``as_of`` live on the routes, not on the items: they are covered in
``test_api/test_period_changes_api.py``.

Pure: no database, no server, no network. Nothing is computed, only validated.
"""

from datetime import date

import pytest
from pydantic import ValidationError

from backend.app.schemas.fx import FXPeriodChangesRequest
from backend.app.schemas.prices import FAPeriodChangesQueryItem

# The R13-SEC8 contract, written out (see the module docstring).
FLOOR = date(1900, 1, 1)

#: Days before the floor: the day before it; the first day whose 5Y reference exists (``0001-01-01``) and the day before
#: it, the last whose 5Y reference overflows ``date``; the first day.
BEFORE_THE_FLOOR = [
    pytest.param(date(1899, 12, 31), id="1899-12-31"),
    pytest.param(date(5, 12, 31), id="0005-12-31"),
    pytest.param(date(5, 12, 30), id="0005-12-30"),
    pytest.param(date(1, 1, 1), id="0001-01-01"),
]

#: Days on or after the floor: the floor itself and the last day ``date`` has (no upper bound).
FROM_THE_FLOOR = [
    pytest.param(FLOOR, id="1900-01-01"),
    pytest.param(date(9999, 12, 31), id="9999-12-31"),
]


def _asset_item(as_of: date) -> FAPeriodChangesQueryItem:
    return FAPeriodChangesQueryItem.model_validate({"asset_id": 1, "as_of": as_of.isoformat()})


def _fx_item(as_of: date) -> FXPeriodChangesRequest:
    return FXPeriodChangesRequest.model_validate({"base": "AWG", "quote": "TMT", "as_of": as_of.isoformat()})


ITEMS = [
    pytest.param(_asset_item, id="FAPeriodChangesQueryItem"),
    pytest.param(_fx_item, id="FXPeriodChangesRequest"),
]


@pytest.mark.parametrize("as_of", BEFORE_THE_FLOOR)
@pytest.mark.parametrize("build", ITEMS)
def test_item_refuses_as_of_before_1900(build, as_of):
    """RED: an ``as_of`` before 1900-01-01 is refused, on ``as_of`` alone."""
    with pytest.raises(ValidationError) as refused:
        build(as_of)
    assert [error["loc"] for error in refused.value.errors()] == [("as_of",)], refused.value.errors()


@pytest.mark.parametrize("as_of", FROM_THE_FLOOR)
@pytest.mark.parametrize("build", ITEMS)
def test_item_accepts_as_of_from_1900(build, as_of):
    """Guard: the floor itself is accepted, and so is any later day."""
    assert build(as_of).as_of == as_of
