"""N92 (i) with «clear» (developer's decisions of 19/10): the write model of a manual price, and an answer model that
checks no sign.

Measured before the cure: one model, ``FAPricePoint``, serves the manual write (``FAUpsert.prices``, what
``POST /assets/prices`` parses), the provider's history (``FAHistoricalData.prices``), the query's answer and a sync's
``changed_points``. Its parser turns every value into ``Decimal(str(v))``, so the text ``"clear"`` — or ``"d"``, or
``""`` — raises ``decimal.InvalidOperation``, which is no ``ValidationError``: the endpoint answers 500, not 422. Its
checks refuse a close not above 0 and a negative open/high/low/volume, except exactly ``-1``, the F.4 sentinel «set
NULL». A provider's day with a negative price therefore raises inside the plugin that builds it, and the whole history
download fails.

The contract (N92 (i), «clear»):

* ``backend.app.schemas.prices.FAPriceWritePoint``, write-only, a ``StrictModel`` whose fields are ``date``, ``open``,
  ``high``, ``low``, ``close``, ``volume`` and ``currency`` — none of the answer's (``original_*``,
  ``source_plugin_key``, ``backward_fill_info``).
* ``open``, ``high``, ``low``, ``volume``: ``"clear" | Decimal | None``, read left to right. ``"clear"`` stays the text
  ``"clear"``, never a Decimal (the store sets the column NULL); a float or an int becomes ``Decimal(str(v))`` (``0.1``
  stays ``0.1``); a number written as text is a Decimal (``"12.5"``); ``None`` or absent stays None (the store leaves the
  stored value). A negative number — ``-1`` included, the old sentinel — is refused; so is any text that is neither
  ``"clear"`` nor a number (``"d"``, ``"Clear"``, ``""``), a value that is not finite, and a boolean.
* ``close``: a Decimal above 0, required; ``0``, a negative and ``"clear"`` are refused.
* ``currency``: optional, checked as ``FAPricePoint`` checks it today.
* ``FAUpsert.prices`` holds ``FAPriceWritePoint``: a JSON body with ``"clear"`` is read, one with ``-1`` or ``"d"`` is
  refused with a ``ValidationError`` located on the field (HTTP 422).
* ``FAPricePoint``, the provider's and the answer's model, checks no sign: a close of -5 or 0, a low of -1, a negative
  open, high or volume are built as given. The sign of a provider's day is the refresh's business (discarded and named,
  ``test_current_price_storable.py``, N92 section).

RED (expected failure before the cure): every test but the one GUARD. ``FAPriceWritePoint`` does not exist yet: it is
looked up inside each test (``_write_model``), so the file collects and each red fails on its own, naming the missing
model; ``FAPricePoint`` refuses the signs above (``close price must be positive (> 0)``, ``price/volume fields must be
>= 0``). GUARD (green before and after): ``FAPricePoint`` takes ``-1`` on open/high/low/volume — before as the sentinel,
after as a number like any other.

A refusal is checked as a ``ValidationError`` located on its field: an ``InvalidOperation`` instead is the 500 of today,
and fails the case.

Pure: no database, no server, no network, no file.
"""

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from backend.app.schemas import prices as prices_schemas
from backend.app.schemas.prices import FAPricePoint, FAUpsert

DAY = date(2024, 6, 10)

#: The fields «clear» may empty, and that a number may write or ``None`` leave as stored.
OPTIONAL_FIELDS = ("open", "high", "low", "volume")

#: The fields of the write model: a manual price, nothing of an answer.
WRITE_FIELDS = {"date", "open", "high", "low", "close", "volume", "currency"}


def _write_model() -> type:
    """``FAPriceWritePoint``, looked up when a test runs: before N92 it does not exist, and the test fails saying so."""
    model = getattr(prices_schemas, "FAPriceWritePoint", None)
    if model is None:
        pytest.fail("N92: backend.app.schemas.prices has no FAPriceWritePoint, the write model of a manual price")
    return model


def _write(**fields: Any):
    """A write point of ``DAY``, close ``"10"`` unless given, read from a body that carries ``fields`` as JSON would."""
    return _write_model().model_validate({"date": DAY.isoformat(), "close": "10", **fields})


def _refused_at(refusal: ValidationError, *path: object) -> bool:
    """Whether one of ``refusal``'s errors is located on ``path`` (a union may add the tag of its branch after it)."""
    return any(tuple(error["loc"][: len(path)]) == path for error in refusal.errors())


def _refusal_of(build, story: str) -> ValidationError:
    """The ``ValidationError`` ``build()`` raises; acceptance, or any other exception (a 500 at the endpoint), fails."""
    try:
        built = build()
    except ValidationError as refusal:
        return refusal
    except Exception as exc:  # noqa: BLE001 — any other exception is the defect under test (a 500, not a 422)
        pytest.fail(f"N92: {story} raised {exc!r} instead of a ValidationError: POST /assets/prices answers 500, not 422")
    pytest.fail(f"N92: {story} was accepted as {built!r}: it must be refused (422)")


# --------------------------------------------------------------------------- #
# The write model: its fields, «clear», numbers, null
# --------------------------------------------------------------------------- #


def test_n92_the_write_model_holds_the_seven_fields_of_a_manual_price():
    """RED: ``schemas.prices`` has no ``FAPriceWritePoint``.

    Contract: its fields are date, open, high, low, close, volume and currency, none of the answer's; a key it does not
    declare is refused (``StrictModel``), so a misspelled field is a 422, never a value gone nowhere.
    """
    model = _write_model()

    assert set(model.model_fields) == WRITE_FIELDS, f"N92: FAPriceWritePoint declares {sorted(model.model_fields)}: expected the seven fields of a manual price, {sorted(WRITE_FIELDS)}"
    refusal = _refusal_of(lambda: model.model_validate({"date": DAY.isoformat(), "close": "10", "source_plugin_key": "MANUAL"}), "a write point carrying source_plugin_key")
    assert _refused_at(refusal, "source_plugin_key"), refusal.errors()


@pytest.mark.parametrize("field", OPTIONAL_FIELDS)
def test_n92_clear_stays_the_text_clear(field):
    """RED: no ``FAPriceWritePoint`` (and ``FAPricePoint`` raises ``InvalidOperation`` on ``"clear"``).

    Contract: ``"clear"`` is kept as the text ``"clear"``, never turned into a Decimal: the store reads it as «set NULL».
    """
    value = getattr(_write(**{field: "clear"}), field)

    assert isinstance(value, str) and not isinstance(value, Decimal) and value == "clear", f"N92: {field}='clear' was read as {value!r}: expected the text 'clear'"


def test_n92_every_optional_field_may_be_cleared_at_once():
    """RED: no ``FAPriceWritePoint``. Contract: the four fields cleared together, the close written."""
    point = _write(open="clear", high="clear", low="clear", volume="clear", close="12.5")

    assert (point.open, point.high, point.low, point.volume, point.close) == ("clear", "clear", "clear", "clear", Decimal("12.5")), point


#: A number as a JSON body or a caller gives it, and the Decimal the write model holds: a float through its text.
NUMBERS = [
    pytest.param(12.5, Decimal("12.5"), id="float-12.5"),
    pytest.param(0.1, Decimal("0.1"), id="float-0.1-through-its-text"),
    pytest.param(3, Decimal("3"), id="int-3"),
    pytest.param("12.5", Decimal("12.5"), id="text-12.5"),
    pytest.param(Decimal("0.000003457312"), Decimal("0.000003457312"), id="decimal"),
    pytest.param(0, Decimal("0"), id="int-zero"),
    pytest.param("0", Decimal("0"), id="text-zero"),
]


@pytest.mark.parametrize("field", OPTIONAL_FIELDS)
@pytest.mark.parametrize(("given", "expected"), NUMBERS)
def test_n92_a_number_not_below_zero_is_a_decimal(field, given, expected):
    """RED: no ``FAPriceWritePoint``.

    Contract: a finite number ≥ 0 is written: held as a Decimal, a float or an int as ``Decimal(str(v))`` — ``0.1`` stays
    ``0.1``, not its binary expansion — and 0 is a value, not an erase.
    """
    value = getattr(_write(**{field: given}), field)

    assert isinstance(value, Decimal) and value == expected and str(value) == str(expected), f"N92: {field}={given!r} was read as {value!r}: expected Decimal({str(expected)!r})"


@pytest.mark.parametrize("field", OPTIONAL_FIELDS)
def test_n92_null_or_absent_stays_none(field):
    """RED: no ``FAPriceWritePoint``. Contract: ``null`` and an absent field are None: the stored value is left as it is."""
    assert getattr(_write(**{field: None}), field) is None
    assert getattr(_write(), field) is None


# --------------------------------------------------------------------------- #
# The write model: what it refuses
# --------------------------------------------------------------------------- #

#: Negative numbers: the old sentinel -1 in every form a caller may send it, and two others.
NEGATIVES = [
    pytest.param(-1, id="int-minus-1-the-old-sentinel"),
    pytest.param("-1", id="text-minus-1"),
    pytest.param(Decimal("-1"), id="decimal-minus-1"),
    pytest.param(-0.01, id="float-minus-0.01"),
    pytest.param("-1E-12", id="text-minus-1E-12"),
]


@pytest.mark.parametrize("field", OPTIONAL_FIELDS)
@pytest.mark.parametrize("given", NEGATIVES)
def test_n92_a_negative_number_is_refused(field, given):
    """RED: no ``FAPriceWritePoint`` (and ``FAPricePoint`` takes ``-1`` as the sentinel «set NULL»).

    Contract: a negative number is refused, ``-1`` included: it no longer clears a field (⚠️ breaking for a client that
    sends it; ``"clear"`` does).
    """
    refusal = _refusal_of(lambda: _write(**{field: given}), f"a write point with {field}={given!r}")

    assert _refused_at(refusal, field), refusal.errors()


#: Neither «clear» nor a finite number: other texts (the marker is case-sensitive), not-finite values, booleans.
NOT_A_NUMBER = [
    pytest.param("d", id="d"),
    pytest.param("Clear", id="Clear"),
    pytest.param("CLEAR", id="CLEAR"),
    pytest.param("", id="empty"),
    pytest.param("NaN", id="text-NaN"),
    pytest.param("Infinity", id="text-Infinity"),
    pytest.param(float("nan"), id="float-nan"),
    pytest.param(float("inf"), id="float-inf"),
    pytest.param(True, id="true"),
]


@pytest.mark.parametrize("field", OPTIONAL_FIELDS)
@pytest.mark.parametrize("given", NOT_A_NUMBER)
def test_n92_neither_clear_nor_a_finite_number_is_refused(field, given):
    """RED: no ``FAPriceWritePoint`` (and ``FAPricePoint`` raises ``InvalidOperation`` on a text that is no number: a 500).

    Contract: refused with a ``ValidationError`` on the field (a 422), never an ``InvalidOperation``.
    """
    refusal = _refusal_of(lambda: _write(**{field: given}), f"a write point with {field}={given!r}")

    assert _refused_at(refusal, field), refusal.errors()


#: Closes the write model refuses: not above 0, the marker (a close is never cleared), no value, no number.
CLOSES_REFUSED = [
    pytest.param("0", id="text-zero"),
    pytest.param(0, id="int-zero"),
    pytest.param("-5", id="minus-5"),
    pytest.param(-1, id="minus-1"),
    pytest.param("clear", id="clear"),
    pytest.param(None, id="null"),
    pytest.param("d", id="d"),
]


@pytest.mark.parametrize("given", CLOSES_REFUSED)
def test_n92_a_close_not_above_zero_is_refused(given):
    """RED: no ``FAPriceWritePoint``.

    Contract: the close is a Decimal above 0: 0, a negative, ``"clear"`` and null are refused on ``close`` (a row is
    removed with the DELETE endpoint, never cleared).
    """
    refusal = _refusal_of(lambda: _write(close=given), f"a write point with close={given!r}")

    assert _refused_at(refusal, "close"), refusal.errors()


def test_n92_a_point_without_a_close_is_refused():
    """RED: no ``FAPriceWritePoint``. Contract: the close is required."""
    model = _write_model()

    refusal = _refusal_of(lambda: model.model_validate({"date": DAY.isoformat(), "open": "10"}), "a write point without a close")

    assert _refused_at(refusal, "close"), refusal.errors()


@pytest.mark.parametrize(("given", "expected"), [pytest.param("0.000001", Decimal("0.000001"), id="text"), pytest.param(12.5, Decimal("12.5"), id="float"), pytest.param(3, Decimal("3"), id="int")])
def test_n92_a_close_above_zero_is_a_decimal(given, expected):
    """RED: no ``FAPriceWritePoint``. Contract: a close above 0 is held as a Decimal, a float through its text."""
    close = _write(close=given).close

    assert isinstance(close, Decimal) and close == expected and str(close) == str(expected), f"N92: close={given!r} was read as {close!r}"


@pytest.mark.parametrize(
    "code",
    [
        pytest.param("usd", id="usd-lower-case"),
        pytest.param(" eur ", id="eur-padded"),
        pytest.param("GBP", id="GBP"),
        pytest.param("ZZZ", id="ZZZ-not-a-currency"),
        pytest.param("", id="empty"),
    ],
)
def test_n92_the_currency_is_checked_as_the_answer_model_checks_it(code):
    """RED: no ``FAPriceWritePoint``.

    Contract: ``currency`` is optional and checked as today: the write model keeps what ``FAPricePoint`` keeps (``usd``
    becomes ``USD``), and refuses what it refuses.
    """
    try:
        expected: object = FAPricePoint.model_validate({"date": DAY.isoformat(), "close": "10", "currency": code}).currency
    except ValidationError:
        expected = ValidationError

    if expected is ValidationError:
        refusal = _refusal_of(lambda: _write(currency=code), f"a write point with currency={code!r}, which FAPricePoint refuses")
        assert _refused_at(refusal, "currency"), refusal.errors()
    else:
        assert _write(currency=code).currency == expected
    assert _write().currency is None


# --------------------------------------------------------------------------- #
# FAUpsert: what POST /assets/prices parses
# --------------------------------------------------------------------------- #


def test_n92_fa_upsert_reads_its_prices_as_write_points():
    """RED: no ``FAPriceWritePoint``; ``FAUpsert.prices`` holds ``FAPricePoint``, whose parser raises ``InvalidOperation``
    on ``"clear"``: ``POST /assets/prices`` answers 500.

    Contract: ``FAUpsert.prices`` is a list of ``FAPriceWritePoint``: the JSON body is read as such, ``"clear"`` as the
    text, a number as a Decimal, ``null`` and an absent field as None.
    """
    model = _write_model()
    body = {"asset_id": 1, "prices": [{"date": DAY.isoformat(), "close": "10", "open": "clear", "high": "12.5", "low": None}]}

    try:
        upsert = FAUpsert.model_validate(body)
    except Exception as exc:  # noqa: BLE001 — a refusal of «clear» is the defect under test
        pytest.fail(f"N92: FAUpsert refused a body clearing open: {exc!r}")

    (point,) = upsert.prices
    assert isinstance(point, model), f"N92: FAUpsert.prices holds {type(point).__name__}, not FAPriceWritePoint"
    assert (point.open, point.high, point.low, point.volume, point.close) == ("clear", Decimal("12.5"), None, None, Decimal("10")), point


@pytest.mark.parametrize(
    ("field", "given"),
    [
        pytest.param("open", -1, id="open-minus-1-the-old-sentinel"),
        pytest.param("volume", -1, id="volume-minus-1-the-old-sentinel"),
        pytest.param("high", "d", id="high-d"),
        pytest.param("low", "", id="low-empty"),
    ],
)
def test_n92_fa_upsert_refuses_a_negative_or_a_stray_text_on_its_field(field, given):
    """RED: no ``FAPriceWritePoint``; today ``-1`` is the sentinel (accepted), ``"d"`` and ``""`` raise
    ``InvalidOperation`` (a 500).

    Contract: a ``ValidationError`` located on ``prices.0.<field>``: ``POST /assets/prices`` answers 422, nothing written.
    """
    _write_model()
    body = {"asset_id": 1, "prices": [{"date": DAY.isoformat(), "close": "10", field: given}]}

    refusal = _refusal_of(lambda: FAUpsert.model_validate(body), f"an upsert body with {field}={given!r}")

    assert _refused_at(refusal, "prices", 0, field), refusal.errors()


# --------------------------------------------------------------------------- #
# FAPricePoint: the provider's and the answer's model checks no sign
# --------------------------------------------------------------------------- #

#: A provider's day, or a stored row, the answer model must carry as it is: the sign is checked elsewhere.
UNSIGNED_POINTS = [
    pytest.param({"close": "-5"}, id="close-minus-5"),
    pytest.param({"close": "0"}, id="close-zero"),
    pytest.param({"close": "1.5", "low": "-2"}, id="low-minus-2"),
    pytest.param({"close": "1.5", "open": "-3", "high": "-0.5", "volume": "-10"}, id="open-high-volume-negative"),
    pytest.param({"close": "1.5", "original_close": "-4"}, id="original-close-negative"),
]


@pytest.mark.parametrize("fields", UNSIGNED_POINTS)
def test_n92_the_answer_model_checks_no_sign(fields):
    """RED: ``FAPricePoint`` refuses a close not above 0 («close price must be positive (> 0)») and a negative other than
    ``-1``: a plugin building a provider's day with a negative price raises, and the whole history download fails.

    Contract: ``FAPricePoint`` builds the point as given, each value the Decimal of its text.
    """
    try:
        point = FAPricePoint.model_validate({"date": DAY.isoformat(), **fields})
    except ValidationError as refusal:
        pytest.fail(f"N92: FAPricePoint refused {fields}: {refusal.errors()}")

    held = {name: getattr(point, name) for name in fields}
    assert held == {name: Decimal(text) for name, text in fields.items()}, held


@pytest.mark.parametrize("field", OPTIONAL_FIELDS)
def test_n92_guard_the_answer_model_still_takes_minus_one(field):
    """GUARD (green before and after): ``FAPricePoint`` takes ``-1`` on open/high/low/volume — before N92 as the sentinel,
    after as a number like any other — and keeps it as ``Decimal("-1")``."""
    point = FAPricePoint.model_validate({"date": DAY.isoformat(), "close": "1.5", field: Decimal("-1")})

    assert getattr(point, field) == Decimal("-1")
