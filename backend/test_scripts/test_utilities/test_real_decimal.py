"""C-97a (workstream W, GitHub #43): crypto quantities and prices keep their decimals -- the column type and the digit limits.

Measured before the lot (SQLite 3.54, SQLAlchemy 2.0.52): ``Transaction.quantity`` and the five
``PriceHistory`` price columns are ``Numeric(18, 6)``. The value is written as a float (a REAL that
keeps all its digits in the file) and ``Numeric`` rounds it to 6 decimals ON READ (``'%.6f'``): a BTC
buy of 0.12345678 reads back 0.123457, a PEPE close of 0.0000034573 reads back 0.000003. Raising the
declared scale alone is no cure: the read then shows the double's noise (12345678.9 at scale 10 reads
12345678.9000000004, 65000.123456 at scale 12 reads 65000.123456000001).

The contract (developer's decisions of 16/10):

* ``backend/app/db/real_decimal.py``: ``RealDecimal(precision, scale)``, a ``TypeDecorator`` over
  ``Numeric``. It writes as today (a float: REAL, or the INTEGER SQLite keeps for a whole value) and
  reads back the shortest decimal of the double (its ``repr``), at most 15 significant digits, rounded
  to the column scale when it has more decimals, padded to 6 decimals when it has fewer (today's form:
  10 reads back 10.000000).
* ``Transaction.quantity`` is ``RealDecimal(22, 10)``; ``Transaction.cost_basis_override`` (a PER-UNIT price,
  decision D5) and ``PriceHistory`` open, high, low, close and adjusted_close are ``RealDecimal(24, 12)``.
  Unchanged: ``amount``, ``AssetEvent.value`` (``Numeric(18, 6)``), ``volume`` (``Numeric(24, 0)``),
  ``FxRate.rate`` (``Numeric(24, 10)``).
* ``db/precision.py``: ``get_model_column_precision`` reads a ``RealDecimal`` column;
  ``truncate_to_db_precision`` / ``truncate_priceHistory`` cut to the scale, then, on a ``RealDecimal``
  column, to 15 significant digits, both ``ROUND_DOWN``; ``truncate_fx_rate`` is unchanged. New
  ``decimal_limit_issue(value, model, column_name)``: ``("decimalPlacesExceeded", <scale>)`` when the
  decimals, trailing zeros not counted, exceed the column scale, otherwise
  ``("significantDigitsExceeded", 15)`` beyond 15 significant digits, ``None`` within both.
* Decision D6: a value a BRIM plugin COMPUTES (a per-unit cost ``cost / qty``, a bond price ``price / 100``) is
  rounded by the plugin with ``round_computed_value(value, model, column_name)``: the column scale,
  ``ROUND_HALF_EVEN``, then, on a ``RealDecimal`` column, 15 significant digits, ``ROUND_HALF_EVEN``; the result
  always passes ``decimal_limit_issue``. A value READ from a file stays as read (decision D2).

Reds fail at run time, never at collection: the column types are read from the models when a test
runs (``Transaction.__table__.c.quantity.type``), and ``decimal_limit_issue`` and ``round_computed_value`` are
looked up on ``backend.app.db.precision`` at call time, so the guards of this file stay green before the cure.
Every red says what the user faces. A GUARD passes before and after the cure.

Isolation: PURE. A round trip runs on a private in-memory SQLite engine of its own test, disposed at
teardown: the lane database is never opened. Everything else is a function over values.
"""

from decimal import Decimal

import pytest
from sqlalchemy import Column, Engine, Integer, MetaData, Numeric, Table, create_engine, select, text
from sqlalchemy.types import TypeDecorator, TypeEngine

from backend.app.db import precision
from backend.app.db.models import AssetEvent, FxRate, PriceHistory, Transaction

# The columns C-97a moves to RealDecimal, with their new (precision, scale): seven, the cost basis included (D5).
_REAL_DECIMAL_COLUMNS = [
    pytest.param(Transaction, "quantity", (22, 10), id="Transaction.quantity"),
    pytest.param(Transaction, "cost_basis_override", (24, 12), id="Transaction.cost_basis_override"),
    pytest.param(PriceHistory, "open", (24, 12), id="PriceHistory.open"),
    pytest.param(PriceHistory, "high", (24, 12), id="PriceHistory.high"),
    pytest.param(PriceHistory, "low", (24, 12), id="PriceHistory.low"),
    pytest.param(PriceHistory, "close", (24, 12), id="PriceHistory.close"),
    pytest.param(PriceHistory, "adjusted_close", (24, 12), id="PriceHistory.adjusted_close"),
]

# The numeric columns C-97a leaves as they are.
_UNCHANGED_COLUMNS = [
    pytest.param(Transaction, "amount", (18, 6), id="Transaction.amount"),
    pytest.param(AssetEvent, "value", (18, 6), id="AssetEvent.value"),
    pytest.param(PriceHistory, "volume", (24, 0), id="PriceHistory.volume"),
    pytest.param(FxRate, "rate", (24, 10), id="FxRate.rate"),
]

# The columns the round trips exercise: a quantity (scale 10 after the cure), a per-unit cost basis and a price (scale 12).
_ROUND_TRIP_COLUMNS = [
    pytest.param(Transaction, "quantity", id="Transaction.quantity"),
    pytest.param(Transaction, "cost_basis_override", id="Transaction.cost_basis_override"),
    pytest.param(PriceHistory, "close", id="PriceHistory.close"),
]


def _column_type(model, column: str) -> TypeEngine:
    """The type the model declares for ``column``, read when the test runs."""
    return model.__table__.c[column].type


# --------------------------------------------------------------------------- #
# Round trips through the real column types, on a private in-memory database
# --------------------------------------------------------------------------- #


@pytest.fixture
def memory_engine():
    """A private in-memory SQLite database for one test: the lane database is never opened."""
    engine = create_engine("sqlite://")
    yield engine
    engine.dispose()


def _write_and_read(engine: Engine, column_type: TypeEngine, value: object, *, raw: bool = False) -> tuple[object, str]:
    """Store ``value`` in a column of ``column_type``, read it back through that type.

    Returns the value read and SQLite's storage class for it (``typeof``). The column is declared from
    the type, as the migrations declare it: NUMERIC affinity. ``raw=True`` binds the Python float
    itself, skipping the type: a REAL written by an older version or by another tool.
    """
    metadata = MetaData()
    table = Table("c97a_round_trip", metadata, Column("id", Integer, primary_key=True), Column("value", column_type))
    with engine.begin() as conn:
        metadata.create_all(conn)
        if raw:
            conn.execute(text("INSERT INTO c97a_round_trip (id, value) VALUES (1, :value)"), {"value": value})
        else:
            conn.execute(table.insert().values(id=1, value=value))
        read = conn.execute(select(table.c.value).where(table.c.id == 1)).scalar_one()
        storage = conn.execute(text("SELECT typeof(value) FROM c97a_round_trip WHERE id = 1")).scalar_one()
    return read, storage


@pytest.mark.parametrize(
    ("model", "column", "typed", "story"),
    [
        pytest.param(Transaction, "quantity", "0.12345678", "a BTC buy of 0.12345678", id="quantity-8-decimals"),
        pytest.param(Transaction, "quantity", "-0.12345678", "a BTC sell of -0.12345678", id="quantity-sell"),
        pytest.param(Transaction, "quantity", "0.1234567891", "a quantity of 0.1234567891 (10 decimals, the new maximum)", id="quantity-10-decimals"),
        pytest.param(PriceHistory, "close", "0.0000034573", "a PEPE close of 0.0000034573 EUR", id="close-pepe"),
        pytest.param(Transaction, "cost_basis_override", "0.0000034573", "a PEPE cost basis of 0.0000034573 EUR per unit", id="cost-basis-pepe"),
        pytest.param(PriceHistory, "close", "0.000003457312", "a close of 0.000003457312 EUR (12 decimals, the new maximum)", id="close-12-decimals"),
        pytest.param(PriceHistory, "close", "123.456789012345", "a close of 123.456789012345 EUR (15 significant digits, the maximum)", id="close-15-significant-digits"),
    ],
)
def test_a_value_within_the_column_limits_reads_back_exactly(memory_engine, model, column, typed, story):
    """Red. Before: ``Numeric(18, 6)`` rounds on read: 0.12345678 reads 0.123457, 0.0000034573 reads 0.000003.

    Contract: whatever fits the column (10 decimals for a quantity, 12 for a price, 15 significant
    digits) reads back exactly.
    """
    read, _storage = _write_and_read(memory_engine, _column_type(model, column), Decimal(typed))

    assert read == Decimal(typed), f"{story} reads back as {read}"


@pytest.mark.parametrize(("model", "column"), _ROUND_TRIP_COLUMNS)
def test_a_stored_double_with_17_significant_digits_reads_back_with_15(memory_engine, model, column):
    """Red. A REAL already in the file carries 17 significant digits (repr 12345.123456789011): a double holds 15.

    Before: read at 6 decimals, 12345.123457. Contract: its first 15 significant digits,
    12345.1234567890, which fits both scales.
    """
    stored = float("12345.123456789012")

    read, storage = _write_and_read(memory_engine, _column_type(model, column), stored, raw=True)

    assert storage == "real", f"the fixture itself is wrong: {stored!r} was stored as {storage}"
    assert read == Decimal("12345.123456789"), f"the REAL {stored!r} in {model.__name__}.{column} reads back as {read}: expected its 15 significant digits, 12345.1234567890"


@pytest.mark.parametrize(
    ("model", "column", "expected"),
    [
        pytest.param(Transaction, "quantity", "0.1234567890", id="Transaction.quantity-scale-10"),
        pytest.param(Transaction, "cost_basis_override", "0.123456789012", id="Transaction.cost_basis_override-scale-12"),
        pytest.param(PriceHistory, "close", "0.123456789012", id="PriceHistory.close-scale-12"),
    ],
)
def test_a_stored_double_with_more_decimals_than_the_scale_reads_back_rounded_to_the_scale(memory_engine, model, column, expected):
    """Red. A REAL with more decimals than the column keeps (repr 0.12345678901234566) is rounded to the column scale.

    Before: rounded to 6 decimals, 0.123457. Contract: 0.1234567890 for a quantity (scale 10),
    0.123456789012 for a price (scale 12). The digit after the scale is 1, 2 or 3: any rounding agrees.
    """
    stored = float("0.12345678901234567")

    read, _storage = _write_and_read(memory_engine, _column_type(model, column), stored, raw=True)

    assert read == Decimal(expected), f"the REAL {stored!r} in {model.__name__}.{column} reads back as {read}: expected {expected}, rounded to the column scale"


@pytest.mark.parametrize(
    ("model", "column", "typed", "form"),
    [
        pytest.param(Transaction, "quantity", "12345678.9", "12345678.900000", id="Transaction.quantity-12345678.9"),
        pytest.param(PriceHistory, "close", "65000.123456", "65000.123456", id="PriceHistory.close-65000.123456"),
    ],
)
def test_guard_the_noise_of_the_double_never_shows(memory_engine, model, column, typed, form):
    """GUARD (green before and after): a cure that only raises the declared scale turns this red.

    Six decimals hide the noise of the double today. ``Numeric(22, 10)`` would read 12345678.9 back
    as 12345678.9000000004, ``Numeric(24, 12)`` 65000.123456 as 65000.123456000001 (measured).
    """
    read, _storage = _write_and_read(memory_engine, _column_type(model, column), Decimal(typed))

    assert isinstance(read, Decimal), f"{model.__name__}.{column} reads back a {type(read).__name__}, not a Decimal"
    assert str(read) == form, f"{typed} in {model.__name__}.{column} reads back as {read}: expected {form}, the double's noise must never show"


@pytest.mark.parametrize(("model", "column"), _ROUND_TRIP_COLUMNS)
@pytest.mark.parametrize(
    ("typed", "form"),
    [
        pytest.param("10", "10.000000", id="10"),
        pytest.param("0.5", "0.500000", id="0.5"),
        pytest.param("100.5", "100.500000", id="100.5"),
    ],
)
def test_guard_a_value_with_fewer_than_6_decimals_reads_back_in_todays_form(memory_engine, model, column, typed, form):
    """GUARD (green before and after): what fits today reads back as today, form included (padded to 6 decimals).

    ``10`` is stored as an INTEGER (NUMERIC affinity), ``0.5`` and ``100.5`` as REALs.
    """
    read, _storage = _write_and_read(memory_engine, _column_type(model, column), Decimal(typed))

    assert isinstance(read, Decimal), f"{model.__name__}.{column} reads back a {type(read).__name__}, not a Decimal"
    assert str(read) == form, f"{typed} in {model.__name__}.{column} reads back as {read}: today, and after C-97a, {form}"


@pytest.mark.parametrize(("model", "column"), _ROUND_TRIP_COLUMNS)
@pytest.mark.parametrize(
    ("typed", "storage"),
    [
        pytest.param("0.12345678", "real", id="fraction-real"),
        pytest.param("10", "integer", id="whole-integer"),
    ],
)
def test_guard_the_value_is_still_written_as_a_float(memory_engine, model, column, typed, storage):
    """GUARD (green before and after): C-97a writes as today, a float -- REAL, or the INTEGER SQLite keeps for a whole value."""
    _read, stored_as = _write_and_read(memory_engine, _column_type(model, column), Decimal(typed))

    assert stored_as == storage, f"{typed} is stored in {model.__name__}.{column} as {stored_as}: expected {storage}, as today"


@pytest.mark.parametrize(("model", "column"), _ROUND_TRIP_COLUMNS)
def test_guard_null_reads_back_as_none(memory_engine, model, column):
    """GUARD (green before and after): a missing price (open/high/low may be NULL) stays missing."""
    read, storage = _write_and_read(memory_engine, _column_type(model, column), None)

    assert (read, storage) == (None, "null")


# --------------------------------------------------------------------------- #
# Column declarations
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("model", "column", "declared"), _REAL_DECIMAL_COLUMNS)
def test_the_column_is_a_real_decimal(model, column, declared):
    """Red. Before: ``Numeric(18, 6)``. Contract: ``backend.app.db.real_decimal.RealDecimal``, a TypeDecorator over Numeric."""
    column_type = _column_type(model, column)
    kind = f"{type(column_type).__module__}.{type(column_type).__qualname__}"

    assert kind == "backend.app.db.real_decimal.RealDecimal", f"{model.__name__}.{column} is a {kind}: every value it reads is rounded to {getattr(column_type, 'scale', '?')} decimals (C-97a: RealDecimal{declared})"
    assert isinstance(column_type, TypeDecorator), f"RealDecimal must be a TypeDecorator, it is a {type(column_type).__mro__}"
    assert isinstance(column_type.impl, Numeric), f"RealDecimal must decorate Numeric, it decorates {column_type.impl!r}"


@pytest.mark.parametrize(("model", "column", "declared"), _REAL_DECIMAL_COLUMNS)
def test_get_model_column_precision_reads_the_new_declaration(model, column, declared):
    """Red. Before: (18, 6) -- a quantity keeps 6 decimals, a price 6. Contract: (22, 10) for the quantity, (24, 12) for a price."""
    found = precision.get_model_column_precision(model, column)

    assert found == declared, f"{model.__name__}.{column} is declared {found}: a BTC buy of 0.12345678, a PEPE close of 0.0000034573 cannot be kept (C-97a: {declared})"


@pytest.mark.parametrize(("model", "column", "declared"), _UNCHANGED_COLUMNS)
def test_guard_the_other_numeric_columns_keep_their_type_and_declaration(model, column, declared):
    """GUARD (green before and after): amounts, cost basis, event values, volume and FX rates are not part of C-97a."""
    column_type = _column_type(model, column)

    assert type(column_type) is Numeric, f"{model.__name__}.{column} became a {type(column_type).__name__}: C-97a leaves it Numeric{declared}"
    assert precision.get_model_column_precision(model, column) == declared


# --------------------------------------------------------------------------- #
# Truncation on write: to the scale, then to 15 significant digits on a RealDecimal column, ROUND_DOWN
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("column", ["open", "high", "low", "close", "adjusted_close"])
def test_truncate_price_history_keeps_12_decimals(column):
    """Red. Before: truncated to 6 decimals, 0.000003. Contract: 12 decimals, ROUND_DOWN: 0.000003457312."""
    found = precision.truncate_priceHistory(Decimal("0.00000345731234567"), column)

    assert found == Decimal("0.000003457312"), f"a provider's PEPE {column} of 0.00000345731234567 EUR is stored as {found}: expected 0.000003457312 (12 decimals, ROUND_DOWN)"


@pytest.mark.parametrize(
    ("delivered", "expected", "rule"),
    [
        pytest.param("65432.123456789012", "65432.123456789", "15 significant digits, ROUND_DOWN", id="15-significant-digits"),
        pytest.param("99999.9999999999999", "99999.9999999999", "15 significant digits, ROUND_DOWN: never rounded up to 100000", id="significant-digits-round-down"),
        pytest.param("1.9999999999999", "1.999999999999", "12 decimals, ROUND_DOWN: never rounded up to 2", id="decimals-round-down"),
    ],
)
def test_truncate_price_history_cuts_to_12_decimals_then_15_significant_digits(delivered, expected, rule):
    """Red. Before: truncated to 6 decimals (65432.123456, 99999.999999, 1.999999). Contract: 12 decimals, then 15 significant digits, both ROUND_DOWN."""
    found = precision.truncate_priceHistory(Decimal(delivered))

    assert found == Decimal(expected), f"a provider close of {delivered} is stored as {found}: expected {expected} ({rule})"


@pytest.mark.parametrize(
    ("typed", "expected", "rule"),
    [
        pytest.param("0.123456789012", "0.1234567890", "10 decimals, ROUND_DOWN", id="10-decimals"),
        pytest.param("1234567890.12345678", "1234567890.12345", "15 significant digits, ROUND_DOWN", id="15-significant-digits"),
    ],
)
def test_truncate_to_db_precision_cuts_a_quantity_to_10_decimals_then_15_significant_digits(typed, expected, rule):
    """Red. Before: truncated to 6 decimals (0.123456, 1234567890.123456). Contract: 10 decimals, then 15 significant digits."""
    found = precision.truncate_to_db_precision(Decimal(typed), Transaction, "quantity")

    assert found == Decimal(expected), f"a quantity of {typed} truncates to {found}: expected {expected} ({rule})"


@pytest.mark.parametrize(
    ("typed", "expected", "rule"),
    [
        pytest.param("0.00000345731234567", "0.000003457312", "12 decimals, ROUND_DOWN", id="12-decimals"),
        pytest.param("65432.123456789012", "65432.123456789", "15 significant digits, ROUND_DOWN", id="15-significant-digits"),
    ],
)
def test_truncate_to_db_precision_cuts_a_cost_basis_to_12_decimals_then_15_significant_digits(typed, expected, rule):
    """Red. Before: truncated to 6 decimals (0.000003, 65432.123456). Contract (D5): a per-unit cost basis is cut like a price."""
    found = precision.truncate_to_db_precision(Decimal(typed), Transaction, "cost_basis_override")

    assert found == Decimal(expected), f"a per-unit cost basis of {typed} EUR truncates to {found}: expected {expected} ({rule})"


def test_guard_a_price_that_fits_is_not_changed_by_truncation():
    """GUARD (green before and after): a 6-decimal price is kept as it is."""
    assert precision.truncate_priceHistory(Decimal("175.123456")) == Decimal("175.123456")


def test_guard_an_amount_gets_no_significant_digit_cut():
    """GUARD (green before and after): the 15-significant-digit cut is for RealDecimal columns only; ``amount`` stays Numeric(18, 6)."""
    found = precision.truncate_to_db_precision(Decimal("1234567890123.4567891"), Transaction, "amount")

    assert found == Decimal("1234567890123.456789"), f"an amount of 1234567890123.4567891 truncates to {found}: expected 1234567890123.456789 (6 decimals, no significant-digit cut)"


@pytest.mark.parametrize(
    ("rate", "expected"),
    [
        pytest.param("1.123456789012345", "1.1234567890", id="10-decimals"),
        pytest.param("12345678.123456789012", "12345678.1234567890", id="18-significant-digits-kept"),
    ],
)
def test_guard_truncate_fx_rate_is_unchanged(rate, expected):
    """GUARD (green before and after): FX rates keep 10 decimals and get no significant-digit cut."""
    found = precision.truncate_fx_rate(Decimal(rate))

    assert found == Decimal(expected), f"an FX rate of {rate} truncates to {found}: expected {expected}, as today"


# --------------------------------------------------------------------------- #
# decimal_limit_issue: what a refusal names
# --------------------------------------------------------------------------- #


def _decimal_limit_issue():
    """``precision.decimal_limit_issue``, looked up when the test runs: the function is new in C-97a."""
    found = getattr(precision, "decimal_limit_issue", None)
    if found is None:
        pytest.fail("backend/app/db/precision.py has no decimal_limit_issue: nothing can tell a user that a value has more digits than its column keeps, so it is cut without a word")
    return found


@pytest.mark.parametrize(
    ("typed", "model", "column", "expected"),
    [
        pytest.param("0.12345678901", Transaction, "quantity", ("decimalPlacesExceeded", 10), id="quantity-11-decimals"),
        pytest.param("0.1234567890", Transaction, "quantity", None, id="quantity-10-decimals"),
        pytest.param("1.50000000000000", Transaction, "quantity", None, id="quantity-trailing-zeros-not-counted"),
        pytest.param("1234567890123.456", Transaction, "quantity", ("significantDigitsExceeded", 15), id="quantity-16-significant-digits"),
        pytest.param("12345.6789012345", Transaction, "quantity", None, id="quantity-15-significant-digits-10-decimals"),
        pytest.param("1234567890.12345678901", Transaction, "quantity", ("decimalPlacesExceeded", 10), id="quantity-both-exceeded-decimals-first"),
        pytest.param("-0.12345678901", Transaction, "quantity", ("decimalPlacesExceeded", 10), id="quantity-sell-11-decimals"),
        pytest.param("0", Transaction, "quantity", None, id="quantity-zero"),
        pytest.param("1.1234567", Transaction, "amount", ("decimalPlacesExceeded", 6), id="amount-7-decimals"),
        pytest.param("0.0000034573", PriceHistory, "close", None, id="close-pepe"),
        pytest.param("0.0000034573", Transaction, "cost_basis_override", None, id="cost-basis-pepe"),
        pytest.param("0.0000000000001", Transaction, "cost_basis_override", ("decimalPlacesExceeded", 12), id="cost-basis-13-decimals"),
        pytest.param("0.0000000000001", PriceHistory, "close", ("decimalPlacesExceeded", 12), id="close-13-decimals"),
        pytest.param("123.456789012345", PriceHistory, "close", None, id="close-15-significant-digits-12-decimals"),
        pytest.param("3333.333333333333", PriceHistory, "close", ("significantDigitsExceeded", 15), id="close-16-significant-digits"),
        pytest.param("1.1234567", AssetEvent, "value", ("decimalPlacesExceeded", 6), id="event-7-decimals"),
        pytest.param("1234567890.123456", AssetEvent, "value", ("significantDigitsExceeded", 15), id="event-16-significant-digits"),
        pytest.param("123456789.123456", AssetEvent, "value", None, id="event-15-significant-digits-6-decimals"),
    ],
)
def test_decimal_limit_issue(typed, model, column, expected):
    """Red (the function does not exist). Contract: ``("decimalPlacesExceeded", <scale>)`` when the decimals, trailing zeros
    not counted, exceed the column scale; otherwise ``("significantDigitsExceeded", 15)`` beyond 15 significant digits;
    ``None`` within both.
    """
    found = _decimal_limit_issue()(Decimal(typed), model, column)

    assert found == expected, f"decimal_limit_issue({typed}, {model.__name__}, {column!r}) = {found!r}: expected {expected!r}"


# --------------------------------------------------------------------------- #
# round_computed_value: how a plugin rounds what it computes (decision D6)
# --------------------------------------------------------------------------- #


def _round_computed_value():
    """``precision.round_computed_value``, looked up when the test runs: the function is new in C-97a (D6)."""
    found = getattr(precision, "round_computed_value", None)
    if found is None:
        pytest.fail("backend/app/db/precision.py has no round_computed_value: a per-unit cost a BRIM plugin computes (1000.00 EUR / 3 units = 333.3333333333333333333333333) keeps 28 digits, and the batch refuses the whole import")
    return found


@pytest.mark.parametrize(
    ("computed", "model", "column", "expected"),
    [
        pytest.param(Decimal(1000) / Decimal(3), Transaction, "cost_basis_override", "333.333333333333", id="cost-basis-1000-over-3"),
        pytest.param(Decimal(100000) / Decimal(3), Transaction, "cost_basis_override", "33333.3333333333", id="cost-basis-100000-over-3-15-significant-digits"),
        pytest.param(Decimal(2) / Decimal(3), Transaction, "cost_basis_override", "0.666666666667", id="cost-basis-2-over-3-rounded-up"),
        pytest.param(Decimal(1) / Decimal(3), Transaction, "amount", "0.333333", id="amount-1-over-3-no-significant-digit-step"),
        pytest.param(Decimal(1) / Decimal(3), Transaction, "quantity", "0.3333333333", id="quantity-1-over-3-scale-10"),
        pytest.param(Decimal("1.0000000000005"), Transaction, "cost_basis_override", "1.000000000000", id="tie-at-the-scale-to-even"),
        pytest.param(Decimal("12345.12345678905"), Transaction, "cost_basis_override", "12345.1234567890", id="tie-at-15-significant-digits-to-even"),
    ],
)
def test_round_computed_value(computed, model, column, expected):
    """Red (the function does not exist). Contract (D6): the column scale, ROUND_HALF_EVEN; then, on a RealDecimal
    column, 15 significant digits, ROUND_HALF_EVEN; the result always passes ``decimal_limit_issue``.

    The first four are the coordinator's examples (2/3 rounds UP, so ROUND_DOWN is excluded). Derived from the
    rule: the quantity (scale 10), and the two ties, which only ROUND_HALF_EVEN sends down (ROUND_HALF_UP gives
    1.000000000001 and 12345.1234567891).
    """
    found = _round_computed_value()(computed, model, column)

    assert found == Decimal(expected), f"round_computed_value({computed}, {model.__name__}, {column!r}) = {found}: expected {expected}"
    issue = _decimal_limit_issue()(found, model, column)
    assert issue is None, f"round_computed_value({computed}, {model.__name__}, {column!r}) = {found}, which decimal_limit_issue still refuses: {issue}"


@pytest.mark.parametrize(
    ("computed", "model", "column", "form"),
    [
        pytest.param(Decimal("1.00"), Transaction, "cost_basis_override", "1.00", id="cost-basis-1.00"),
        pytest.param(Decimal("0.9369"), Transaction, "cost_basis_override", "0.9369", id="cost-basis-0.9369"),
        pytest.param(Decimal("100.00") / Decimal(100), Transaction, "cost_basis_override", "1.00", id="cost-basis-bond-100.00-over-100"),
        pytest.param(Decimal("12.5"), Transaction, "amount", "12.5", id="amount-12.5"),
    ],
)
def test_round_computed_value_keeps_the_form_of_a_value_that_fits(computed, model, column, form):
    """Red before the fix: the first version always quantized, which pads the value. Contract (D6, 16/10 19:38):
    a computed value with no more decimals than the column scale, and no more than 15 significant digits, comes
    back as it is, form included: it is quantized only when it has MORE decimals than the scale.

    Found by ``TestCreditAgricoleCanonicalCharacterization[securities]``: a bond unit cost of 100.00 / 100 came
    back 1.000000000000, and 0.9369 as 0.936900000000, which the import wizard would show. Compared with ``str()``:
    the form is what is asserted, the value check is the one of ``test_round_computed_value``.
    """
    found = _round_computed_value()(computed, model, column)

    assert str(found) == form, f"round_computed_value({computed}, {model.__name__}, {column!r}) returns {found}: a computed value that already fits must keep its form, {form}, or the import wizard shows padded zeros"
    assert found == Decimal(form), f"round_computed_value({computed}, {model.__name__}, {column!r}) = {found}: expected {form}"
    issue = _decimal_limit_issue()(found, model, column)
    assert issue is None, f"round_computed_value({computed}, {model.__name__}, {column!r}) = {found}, which decimal_limit_issue refuses: {issue}"
