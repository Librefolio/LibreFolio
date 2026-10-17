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

X-R59 (rule 10, decision N80) adds ``range_start``, optional on both items: the first day of the range whose change the
Assets cards and the FX Δ Abs / Δ % show. Same floor as ``as_of`` (1900-01-01, the type ``PeriodChangesAsOf``), and not
after the item's ``as_of``. On HEAD (a275ec8af, 46bbbb1e3) the field does not exist, and a ``StrictModel`` refuses it
too — with an ``extra_forbidden`` error on ``range_start``. So each refusal below also asserts the error is the rule's
(``value_error``), not that one: without it, «refused» would be green on HEAD for the wrong reason.

The limits of a whole request — how many items, how many distinct days — are not the items': both routes refuse them
through ``schemas/common.py::period_changes_request_refusal(items)`` (coordinator's decision, aligned with Z-25), the
422 ``detail`` or None. It is tested here pure, on plain objects that only have ``as_of`` and ``range_start``: at most
1 000 items (Z-25's ``MAX_BULK_ITEMS``) — ``{"code": "bulk_too_many_items", "message", "max_items", "items"}`` —, at most
5 distinct ``as_of`` and 5 distinct ``range_start`` — ``{"code": "period_changes_too_many_days", "message", "field",
"max_days", "days"}`` —, the items before the days. The message is never matched. RED on HEAD 46bbbb1e3: the function
does not exist (looked up on the module when called). The routes' answers are ``test_api/test_period_changes_api.py``.

Pure: no database, no server, no network. Nothing is computed, only validated.
"""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.app.schemas import common as common_schemas
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


def _range(range_start: date | None) -> dict:
    """The ``range_start`` key, only when one is given: an item without it is the request every table sends today."""
    return {} if range_start is None else {"range_start": range_start.isoformat()}


def _asset_item(as_of: date, range_start: date | None = None) -> FAPeriodChangesQueryItem:
    return FAPeriodChangesQueryItem.model_validate({"asset_id": 1, "as_of": as_of.isoformat(), **_range(range_start)})


def _fx_item(as_of: date, range_start: date | None = None) -> FXPeriodChangesRequest:
    return FXPeriodChangesRequest.model_validate({"base": "AWG", "quote": "TMT", "as_of": as_of.isoformat(), **_range(range_start)})


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


# ============================================================================
# X-R59: range_start
# ============================================================================

#: The ``as_of`` of the range tests: any day after the floor.
AS_OF = date(1987, 3, 15)

#: Days after ``AS_OF``: a range that would end before it starts.
AFTER_AS_OF = [
    pytest.param(AS_OF + timedelta(days=1), id="the-day-after"),
    pytest.param(date(9999, 12, 31), id="9999-12-31"),
]

#: ``(range_start, as_of)`` pairs inside the rules: from the floor, up to ``as_of`` included.
ACCEPTED_RANGES = [
    pytest.param(AS_OF, AS_OF, id="equal-to-as_of"),
    pytest.param(AS_OF - timedelta(days=1), AS_OF, id="the-day-before"),
    pytest.param(FLOOR, AS_OF, id="from-the-floor"),
    pytest.param(FLOOR, FLOOR, id="both-on-the-floor"),
    pytest.param(date(9999, 12, 31), date(9999, 12, 31), id="both-on-the-last-day"),
]


def _rule_errors(refused: ValidationError) -> list:
    """The refusal's errors, once proven not to be ``extra_forbidden``: HEAD refuses ``range_start`` as an unknown field."""
    errors = refused.errors()
    assert all(error["type"] != "extra_forbidden" for error in errors), f"refused as an unknown field, not by a rule: {errors}"
    return errors


@pytest.mark.parametrize("range_start", BEFORE_THE_FLOOR)
@pytest.mark.parametrize("build", ITEMS)
def test_item_refuses_range_start_before_1900(build, range_start):
    """RED: a ``range_start`` before 1900-01-01 is refused on ``range_start`` alone, by the floor ``as_of`` has — the
    item's ``as_of`` is the floor itself, so the range is otherwise in order."""
    with pytest.raises(ValidationError) as refused:
        build(FLOOR, range_start)
    errors = _rule_errors(refused.value)
    assert [(error["loc"], error["type"]) for error in errors] == [(("range_start",), "value_error")], errors


@pytest.mark.parametrize("range_start", AFTER_AS_OF)
@pytest.mark.parametrize("build", ITEMS)
def test_item_refuses_range_start_after_as_of(build, range_start):
    """RED: a ``range_start`` after the item's ``as_of`` is refused: one error, a ``value_error``, on the item (a model
    validator) or on ``range_start`` (a field validator) — where the rule sits is the implementation's choice."""
    with pytest.raises(ValidationError) as refused:
        build(AS_OF, range_start)
    errors = _rule_errors(refused.value)
    assert len(errors) == 1 and errors[0]["type"] == "value_error" and errors[0]["loc"] in ((), ("range_start",)), errors


@pytest.mark.parametrize(("range_start", "as_of"), ACCEPTED_RANGES)
@pytest.mark.parametrize("build", ITEMS)
def test_item_accepts_range_start_from_1900_up_to_as_of(build, range_start, as_of):
    """RED: a ``range_start`` from the floor up to ``as_of`` included — equal to it too — is accepted and kept."""
    item = build(as_of, range_start)
    assert (item.range_start, item.as_of) == (range_start, as_of)


@pytest.mark.parametrize("build", ITEMS)
def test_item_without_range_start_has_none(build):
    """RED by absence (the attribute does not exist on HEAD): ``range_start`` is optional and None by default, so every
    request the tables send today stays valid and asks no range change."""
    item = build(AS_OF)
    assert item.range_start is None


# ============================================================================
# The limits of a request: period_changes_request_refusal (Z-25 alignment)
# ============================================================================

#: The limits, written out: Z-25's MAX_BULK_ITEMS, and the distinct days of either field.
MAX_ITEMS = 1_000
MAX_DAYS = 5
ITEMS_KEYS = {"code", "message", "max_items", "items"}
DAYS_KEYS = {"code", "message", "field", "max_days", "days"}


def _days(count: int) -> list[date]:
    """``count`` distinct days, all on or before ``AS_OF``."""
    return [AS_OF - timedelta(days=offset) for offset in range(count)]


def _items(count: int, as_ofs: int = 1, range_starts: int = 0) -> list[SimpleNamespace]:
    """``count`` plain items cycling through ``as_ofs`` distinct ``as_of`` and ``range_starts`` distinct ``range_start``
    (None on every item when 0): the only attributes the function may read."""
    as_of_days, range_days = _days(as_ofs), _days(range_starts)
    return [SimpleNamespace(as_of=as_of_days[index % as_ofs], range_start=range_days[index % range_starts] if range_starts else None) for index in range(count)]


def _refusal(items: list) -> dict | None:
    """``period_changes_request_refusal(items)``, looked up when called: it does not exist on HEAD 46bbbb1e3."""
    return common_schemas.period_changes_request_refusal(items)


@pytest.mark.parametrize(
    ("count", "as_ofs", "range_starts"),
    [
        pytest.param(0, 1, 0, id="empty"),
        pytest.param(1, 1, 0, id="one-item"),
        pytest.param(1, 1, 1, id="one-item-with-range"),
        pytest.param(MAX_ITEMS, MAX_DAYS, MAX_DAYS, id="every-limit-reached"),
        pytest.param(MAX_DAYS * 3, MAX_DAYS, 0, id="days-repeated"),
    ],
)
def test_request_refusal_is_none_within_the_limits(count, as_ofs, range_starts):
    """RED by absence: up to 1 000 items, 5 distinct ``as_of`` and 5 distinct ``range_start`` — however often each is
    repeated — the request is not refused; an item without ``range_start`` asks no range day."""
    assert _refusal(_items(count, as_ofs, range_starts)) is None


def test_request_refusal_does_not_count_a_missing_range_start():
    """Five distinct ``range_start`` and items without one: None is not a sixth day."""
    items = [*_items(MAX_DAYS, range_starts=MAX_DAYS), *_items(3)]

    assert _refusal(items) is None


@pytest.mark.parametrize("count", [MAX_ITEMS + 1, 2 * MAX_ITEMS], ids=["1001", "2000"])
def test_request_refusal_too_many_items(count):
    """RED: more than 1 000 items is Z-25's ``bulk_too_many_items``, with the cap and the count."""
    detail = _refusal(_items(count))

    assert detail is not None and set(detail) == ITEMS_KEYS, detail
    assert (detail["code"], detail["max_items"], detail["items"]) == ("bulk_too_many_items", MAX_ITEMS, count), detail
    assert isinstance(detail["message"], str) and detail["message"], detail


@pytest.mark.parametrize("days", [MAX_DAYS + 1, MAX_DAYS + 3], ids=["6", "8"])
@pytest.mark.parametrize("field", ["as_of", "range_start"])
def test_request_refusal_too_many_days(field, days):
    """RED: more than 5 distinct days of one field is ``period_changes_too_many_days`` naming that field, with the cap
    and the count — the other field within its limit."""
    items = _items(days, as_ofs=days, range_starts=1) if field == "as_of" else _items(days, as_ofs=1, range_starts=days)

    detail = _refusal(items)

    assert detail is not None and set(detail) == DAYS_KEYS, detail
    assert (detail["code"], detail["field"], detail["max_days"], detail["days"]) == ("period_changes_too_many_days", field, MAX_DAYS, days), detail
    assert isinstance(detail["message"], str) and detail["message"], detail


def test_request_refusal_checks_the_items_before_the_days():
    """RED: 1 001 items with 6 distinct ``as_of`` and 6 distinct ``range_start`` are refused for their number, first."""
    detail = _refusal(_items(MAX_ITEMS + 1, as_ofs=MAX_DAYS + 1, range_starts=MAX_DAYS + 1))

    assert detail is not None and (detail["code"], detail["items"]) == ("bulk_too_many_items", MAX_ITEMS + 1), detail


def test_request_refusal_with_both_fields_over_names_one_of_them():
    """RED: 6 distinct ``as_of`` and 6 distinct ``range_start``: refused for its days, naming one of the two fields —
    which one is checked first is the implementation's."""
    detail = _refusal(_items(MAX_DAYS + 1, as_ofs=MAX_DAYS + 1, range_starts=MAX_DAYS + 1))

    assert detail is not None and detail["code"] == "period_changes_too_many_days" and detail["field"] in {"as_of", "range_start"}, detail
    assert detail["days"] == MAX_DAYS + 1, detail
