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
  Unchanged by C-97a: ``amount``, ``AssetEvent.value`` (``Numeric(18, 6)``, until W-B60 below), ``volume``
  (``Numeric(24, 0)``), ``FxRate.rate`` (``Numeric(24, 10)``).
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

R13-SEC2 (W-B58, E's security review of 17/10): a value of any magnitude. Measured before the cure: reading a stored
±inf raises ``TypeError`` (the exponent ``'F'`` of ``Decimal('Infinity')`` compared with an int), a stored double from
1e54 up ``InvalidOperation`` (padding it to 6 decimals in a 60-digit context); nothing refuses ``Decimal('1E+400')`` on
write, which becomes a REAL inf; ``decimal_limit_issue`` raises ``decimal.Overflow`` on ``1E+1000000`` and
``InvalidOperation`` on ``sNaN``, lets ``1E-2000000`` through (it underflows to 0), answers None for ±Infinity and NaN,
and has no magnitude limit (``1E+60``: one digit, no decimals). The cure's contract:

* reading never raises: a stored ±inf reads ``None`` (logged); a stored finite double of any magnitude (1e54, 1e60,
  the largest double) reads a finite Decimal numerically equal to the double's shortest repr at 15 significant digits
  (1e60 reads ``1E+60``); a normal value reads as before (the guards above);
* ``RealDecimal.process_bind_param`` (new): a value that becomes ±inf as a float (``Decimal('1E+400')``) raises
  ``ValueError``, its message containing "finite"; a finite value and None pass unchanged;
* ``precision.INTEGER_DIGITS_EXCEEDED = "integerDigitsExceeded"``; ``decimal_limit_issue`` never raises for any
  Decimal, and checks decimal places, then significant digits, then the integer digits: more than the column keeps
  (trailing zeros not counted, as today) answers ``("integerDigitsExceeded", max_integer_digits(model, column))``, and
  so does a non-finite value (±Infinity, NaN). The results of C-97a are unchanged (``1234567890123.456`` is still
  ``significantDigitsExceeded``);
* ``max_integer_digits(model, column) -> int`` (new; the coordinator's decision N63 of 17/10): 15
  (``REAL_SIGNIFICANT_DIGITS``) for ``Transaction.quantity`` and ``Transaction.amount``; for every other column the
  integer digits its declaration gives, ``precision - scale``: 12 for the per-unit cost basis, the five prices and an
  event value, 24 for the volume;
* ``integer_digits_issue(value, model, column)`` (new): the magnitude and the finiteness alone, no decimal or
  significant-digit check: a volume of ``1E+400`` → ``("integerDigitsExceeded", 24)``, of ``1.5`` → None;
* ``storable_value(value, model, column)`` (new): a provider's value truncated to the column
  (``truncate_to_db_precision``), or None when ``integer_digits_issue`` is not None; it never raises.

X-R38 (workstream X, the FX side of W-B58, reported as W-B61): an exchange rate no column can keep. Measured before the
cure: ``truncate_fx_rate`` raises ``InvalidOperation`` from ``1E+50`` up and on ±Infinity, gives 0 for ``1E-11``, and
nothing measures the 14 digits ``fx_rates.rate`` (``Numeric(24, 10)``) keeps before the decimal point; the new
``storable_fx_rate`` is a stub raising ``NotImplementedError``. The cure's contract: ``storable_fx_rate(value)`` is the
value as ``truncate_fx_rate`` gives it, or None when it is not finite, has more digits before the decimal point than
``max_integer_digits`` gives for ``FxRate.rate`` (14), or is 0 once truncated to the 10 decimal places; a negative rate
is the caller's business (``upsert_rates_bulk`` refuses it), not refused here; it never raises.

X-R50 (E's review R13-SEC5 on X-R38): the double limit. SQLite keeps an exchange rate as a double, so a rate of 14 digits
before the decimal point a few thousandths below ``1E+14`` is stored as ``1E+14``. Measured before the cure:
``storable_fx_rate`` keeps it as ``truncate_fx_rate`` gives it (``float(Decimal("99999999999999.995")) == 1e14``, while
``99999999999999.992`` is ``99999999999999.98``): a manual rate is answered «inserted» and a synced one stored, and every
conversion then skips it (``convert_bulk`` reads only ``1E-10 <= rate < 1E+14``). The cure's contract: ``storable_fx_rate``
also answers None when the double of the truncated rate, ``float(truncate_fx_rate(value))``, is ``1E+14`` or more; a rate
whose double stays below it is kept as before. X-R50 reverses the X-R38 case ``14-integer-digits-cut-at-10-decimals``
(``99999999999999.99999999999``, kept as ``99999999999999.9999999999``, whose double is ``1E+14``): it moved to the X-R50 reds.

W-B60 (17/10, the follow-up of W-B58): ``Transaction.amount`` and ``AssetEvent.value`` are still plain ``Numeric(18, 6)``.
Measured before the cure: SQLAlchemy reads them through ``'%.6f'`` of the stored double, so from about 11 integer digits
the double's noise lands in the 6 decimals — ``123456789012.345`` reads ``123456789012.345001``, ``12345678901.2345``
``12345678901.234501``, ``-99999999999999.9`` ``-99999999999999.906250``; a stored REAL ±inf reads
``Decimal('Infinity')``; nothing refuses ``Decimal('1E+400')`` on write; ``truncate_to_db_precision`` keeps 19
significant digits of an amount and ``round_computed_value`` 16, more than the column gives back. The cure's contract:

* both columns become ``RealDecimal(18, 6)``: the same precision and scale, the same DDL (``NUMERIC(18, 6) NOT NULL``),
  no migration, the value written as today (a REAL, or the INTEGER SQLite keeps for a whole value);
* the read-back is exact, always with 6 decimals as today: ``123456789012.345`` → ``123456789012.345000``,
  ``-99999999999999.9`` → ``-99999999999999.900000``, ``12345678901.2345`` → ``12345678901.234500``, whatever the input
  limits of the column; what reads well today reads the same, form included (``-100`` → ``-100.000000``, ``0.000001``
  → ``0.000001``, ``999999999999999`` → ``999999999999999.000000``);
* a stored REAL ±inf reads ``None``; binding a value a double cannot hold (``Decimal('1E+400')``) raises the
  ``ValueError`` of W-B58, naming "finite" — through the engine, a ``StatementError`` whose ``orig`` it is;
* like every ``RealDecimal`` column, ``truncate_to_db_precision`` cuts an amount to 6 decimals, then 15 significant
  digits, both ``ROUND_DOWN`` (``1234567890123.4567891`` → ``1234567890123.45``), and ``round_computed_value`` rounds it
  to 6 decimals, then 15 significant digits, both ``ROUND_HALF_EVEN`` (``1234567890.1234567`` → ``1234567890.12346``).

Reds fail at run time, never at collection: the column types are read from the models when a test
runs (``Transaction.__table__.c.quantity.type``), and ``decimal_limit_issue``, ``round_computed_value``,
``max_integer_digits``, ``integer_digits_issue``, ``storable_value``, ``storable_fx_rate`` and ``INTEGER_DIGITS_EXCEEDED``
are looked up on ``backend.app.db.precision`` at call time, ``RealDecimal.process_bind_param`` on the column's type, so the guards
of this file stay green before the cure. A red whose call raises today is turned into a failure that names the
exception. Every red says what the user faces. A GUARD passes before and after the cure.

Isolation: PURE. A round trip runs on a private in-memory SQLite engine of its own test, disposed at
teardown: the lane database is never opened. Everything else is a function over values.
"""

from decimal import ROUND_HALF_EVEN, Context, Decimal

import pytest
from sqlalchemy import Column, Engine, Integer, MetaData, Numeric, Table, create_engine, select, text
from sqlalchemy.dialects import sqlite
from sqlalchemy.exc import StatementError
from sqlalchemy.schema import CreateColumn
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

# The numeric columns C-97a and W-B60 leave as they are: an amount and an event value go to RealDecimal in W-B60.
_UNCHANGED_COLUMNS = [
    pytest.param(PriceHistory, "volume", (24, 0), id="PriceHistory.volume"),
    pytest.param(FxRate, "rate", (24, 10), id="FxRate.rate"),
]

# The columns W-B60 moves to RealDecimal, with the declaration they keep, (18, 6): a transaction amount, an event value.
_AMOUNT_COLUMNS = [
    pytest.param(Transaction, "amount", id="Transaction.amount"),
    pytest.param(AssetEvent, "value", id="AssetEvent.value"),
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
    """GUARD (green before and after): the volume and FX rates are part of neither C-97a nor W-B60. An amount and an event
    value left this list with W-B60 (``test_an_amount_and_an_event_value_are_real_decimals``)."""
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


@pytest.mark.parametrize(
    ("model", "column", "typed", "expected", "rule"),
    [
        pytest.param(Transaction, "amount", "1234567890123.4567891", "1234567890123.45", "6 decimals, then 15 significant digits, ROUND_DOWN", id="Transaction.amount-15-significant-digits"),
        pytest.param(Transaction, "amount", "999999999999999.9999999", "999999999999999", "15 significant digits, ROUND_DOWN: never rounded up to 1E+15", id="Transaction.amount-significant-digits-round-down"),
        pytest.param(AssetEvent, "value", "1234567890123.4567891", "1234567890123.45", "6 decimals, then 15 significant digits, ROUND_DOWN", id="derived-AssetEvent.value-15-significant-digits"),
    ],
)
def test_truncate_to_db_precision_cuts_an_amount_to_6_decimals_then_15_significant_digits(model, column, typed, expected, rule):
    """Red today: the column is a plain ``Numeric(18, 6)``, so the cut stops at the scale — 1234567890123.456789 keeps 19
    significant digits, 999999999999999.999999 21: more than the column gives back, so what is compared before a write is
    not what is read after it.

    Contract (W-B60): like every ``RealDecimal`` column, 6 decimals, then 15 significant digits, both ``ROUND_DOWN``:
    1234567890123.45, and 999999999999999, never rounded up to 1E+15. This test replaces the C-97a guard
    ``test_guard_an_amount_gets_no_significant_digit_cut``, which pinned the cut stopping at the scale. The event value
    is derived from "both columns become ``RealDecimal(18, 6)``".
    """
    found = precision.truncate_to_db_precision(Decimal(typed), model, column)

    assert found == Decimal(expected), f"{model.__name__}.{column}: {typed} truncates to {found}: expected {expected} ({rule})"


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
        pytest.param(Decimal(1) / Decimal(3), Transaction, "amount", "0.333333", id="amount-1-over-3-6-decimals"),
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


@pytest.mark.parametrize(
    ("model", "column"),
    [
        pytest.param(Transaction, "amount", id="Transaction.amount"),
        pytest.param(AssetEvent, "value", id="derived-AssetEvent.value"),
    ],
)
def test_round_computed_value_rounds_an_amount_to_6_decimals_then_15_significant_digits(model, column):
    """Red today: the column is a plain ``Numeric(18, 6)``, so the rounding stops at the scale: 1234567890.1234567 comes
    back 1234567890.123457, 16 significant digits, which ``decimal_limit_issue`` refuses and a REAL does not give back.

    Contract (W-B60): like every ``RealDecimal`` column, 6 decimals, then 15 significant digits, both ``ROUND_HALF_EVEN``:
    1234567890.12346 (…123457 rounds up at the 15th digit), which ``decimal_limit_issue`` accepts. The event value is
    derived from "both columns become ``RealDecimal(18, 6)``".
    """
    found = _round_computed_value()(Decimal("1234567890.1234567"), model, column)

    assert found == Decimal("1234567890.12346"), f"round_computed_value(1234567890.1234567, {model.__name__}, {column!r}) = {found}: expected 1234567890.12346 (6 decimals, then 15 significant digits, ROUND_HALF_EVEN)"
    issue = _decimal_limit_issue()(found, model, column)
    assert issue is None, f"round_computed_value(1234567890.1234567, {model.__name__}, {column!r}) = {found}, which decimal_limit_issue refuses: {issue}"


# --------------------------------------------------------------------------- #
# R13-SEC2 (W-B58): reading never raises, whatever the file holds
# --------------------------------------------------------------------------- #

#: What a read gives back of a stored double: its shortest repr, at ``REAL_SIGNIFICANT_DIGITS`` (15) significant digits.
_SHORTEST_AT_15 = Context(prec=15, rounding=ROUND_HALF_EVEN)

#: Finite doubles today's read cannot give back: from 1e54 up, padding them to 6 decimals needs more than 60 digits.
_HUGE_FINITE_DOUBLES = [
    pytest.param(1e54, id="1e54"),
    pytest.param(1e60, id="1e60"),
    pytest.param(1.7976931348623157e308, id="largest-double"),
]


def _read_back_never_raising(engine: Engine, model, column: str, stored: float) -> tuple[object, str]:
    """``stored`` written raw (a REAL already in the file: an older version, another tool), read back through the column's
    type; a read that raises fails the test, naming the exception."""
    try:
        return _write_and_read(engine, _column_type(model, column), stored, raw=True)
    except (TypeError, ArithmeticError) as exc:
        pytest.fail(f"a REAL {stored!r} in {model.__name__}.{column}: reading it back raised {exc!r}. Every list that reads the row answers 500 (the asset list reads every user's quantities), and deleting the row loads it (R13-SEC2: reading never raises)")


@pytest.mark.parametrize(("model", "column"), _ROUND_TRIP_COLUMNS)
@pytest.mark.parametrize("stored", [pytest.param(float("inf"), id="plus-inf"), pytest.param(float("-inf"), id="minus-inf")])
def test_a_stored_infinite_double_reads_back_as_none(memory_engine, model, column, stored):
    """Red today: the read builds ``Decimal('Infinity')`` and compares its exponent, ``'F'``, with an int: ``TypeError``.

    Contract (R13-SEC2): a REAL ±inf — what ``Decimal('1E+400')`` became before the cure, or what another tool wrote —
    reads back ``None`` (logged): the row loads, is listed, and can be deleted.
    """
    read, storage = _read_back_never_raising(memory_engine, model, column, stored)

    assert storage == "real", f"the fixture itself is wrong: {stored!r} was stored as {storage}"
    assert read is None, f"a REAL {stored!r} in {model.__name__}.{column} reads back {read!r}: expected None, since no Decimal of the column is infinite"


@pytest.mark.parametrize(("model", "column"), _ROUND_TRIP_COLUMNS)
@pytest.mark.parametrize("stored", _HUGE_FINITE_DOUBLES)
def test_a_stored_finite_double_of_any_magnitude_reads_back_as_its_shortest_decimal(memory_engine, model, column, stored):
    """Red today: ``InvalidOperation``: the read pads the value to 6 decimals in a context of 60 digits, and from 1e54 up
    the padded value needs more.

    Contract (R13-SEC2): a finite Decimal numerically equal to the double's shortest repr at 15 significant digits:
    1e60 reads ``1E+60``, the largest double ``1.79769313486232E+308``. A value beyond the column's integer digits is
    not dropped: a database of an older version may hold one, never checked, and reading it as None would lose a position.
    """
    expected = _SHORTEST_AT_15.create_decimal(repr(stored))

    read, storage = _read_back_never_raising(memory_engine, model, column, stored)

    assert storage == "real", f"the fixture itself is wrong: {stored!r} was stored as {storage}"
    assert isinstance(read, Decimal) and read.is_finite(), f"a REAL {stored!r} in {model.__name__}.{column} reads back {read!r}: expected a finite Decimal"
    assert read == expected, f"a REAL {stored!r} in {model.__name__}.{column} reads back {read}: expected {expected}, its shortest repr at 15 significant digits"


@pytest.mark.parametrize(("model", "column"), _ROUND_TRIP_COLUMNS)
def test_guard_a_stored_double_just_below_1e54_reads_back_as_its_value(memory_engine, model, column):
    """Guard: green today and after. 1e53 padded to 6 decimals still fits the 60 digits of today's read; it reads back
    a finite Decimal equal to ``1E+53``, before the cure and after (the form is not asserted)."""
    read, storage = _read_back_never_raising(memory_engine, model, column, 1e53)

    assert storage == "real", f"the fixture itself is wrong: 1e53 was stored as {storage}"
    assert isinstance(read, Decimal) and read.is_finite() and read == Decimal("1E+53"), f"a REAL 1e53 in {model.__name__}.{column} reads back {read!r}: expected 1E+53"


# --------------------------------------------------------------------------- #
# R13-SEC2 (W-B58): writing refuses what a double cannot hold
# --------------------------------------------------------------------------- #

_SQLITE = sqlite.dialect()

#: Values a double cannot hold: each becomes ±inf as a float.
_BEYOND_A_DOUBLE = [
    pytest.param(Decimal("1E+400"), id="Decimal-1E+400"),
    pytest.param(Decimal("-1E+400"), id="Decimal--1E+400"),
    pytest.param(Decimal("Infinity"), id="Decimal-Infinity"),
    pytest.param(float("inf"), id="float-inf"),
]


def _process_bind_param(model, column: str):
    """The column type's own ``process_bind_param``, looked up when the test runs: ``RealDecimal`` has none before R13-SEC2
    (``TypeDecorator``'s raises ``NotImplementedError``), and a plain ``Numeric`` none at all (W-B60: an amount and an
    event value before their cure)."""
    column_type = _column_type(model, column)
    own = getattr(type(column_type), "process_bind_param", None)
    if own is None or own is TypeDecorator.process_bind_param:
        pytest.fail(f"{type(column_type).__name__} ({model.__name__}.{column}) has no process_bind_param of its own: Decimal('1E+400') goes to SQLite as float('inf'), a REAL inf that no read gives back as a number (R13-SEC2, W-B60)")
    return column_type.process_bind_param


@pytest.mark.parametrize(("model", "column"), _ROUND_TRIP_COLUMNS)
@pytest.mark.parametrize("value", _BEYOND_A_DOUBLE)
def test_binding_a_value_a_double_cannot_hold_raises_a_value_error_naming_finite(model, column, value):
    """Red today: ``RealDecimal`` has no ``process_bind_param``; the value is bound as ``float('inf')``.

    Contract (R13-SEC2): ``process_bind_param`` raises ``ValueError``, its message containing "finite", for any value
    that becomes ±inf as a float, whoever writes it: a safety net under every input check.
    """
    bind = _process_bind_param(model, column)

    with pytest.raises(ValueError, match="finite"):
        bind(value, _SQLITE)


@pytest.mark.parametrize(("model", "column"), _ROUND_TRIP_COLUMNS)
@pytest.mark.parametrize(
    "value",
    [
        pytest.param(Decimal("0.12345678"), id="0.12345678"),
        pytest.param(Decimal("-65000.123456"), id="-65000.123456"),
        pytest.param(Decimal("1E+60"), id="1E+60-finite-as-a-double"),
        pytest.param(None, id="None"),
    ],
)
def test_binding_a_finite_value_or_none_passes_it_unchanged(model, column, value):
    """Red today: ``RealDecimal`` has no ``process_bind_param`` (the lookup fails).

    Contract (R13-SEC2): a finite value passes unchanged, a magnitude past the column's integer digits included (the
    input checks refuse it, not the type), and None stays None.
    """
    bind = _process_bind_param(model, column)

    bound = bind(value, _SQLITE)

    if value is None:
        assert bound is None, f"process_bind_param(None) on {model.__name__}.{column} returned {bound!r}"
    else:
        assert type(bound) is type(value) and bound == value, f"process_bind_param({value!r}) on {model.__name__}.{column} returned {bound!r}: a finite value passes unchanged"


@pytest.mark.parametrize(("model", "column"), _ROUND_TRIP_COLUMNS)
def test_writing_a_value_a_double_cannot_hold_is_refused_before_it_reaches_the_file(memory_engine, model, column):
    """Red today: ``Decimal('1E+400')`` is written, a REAL inf, and reading it back raises ``TypeError``.

    Contract (R13-SEC2): the INSERT fails with a ``StatementError`` whose ``orig`` is the ``ValueError`` of
    ``process_bind_param``, naming "finite": nothing reaches the file.
    """
    try:
        read, storage = _write_and_read(memory_engine, _column_type(model, column), Decimal("1E+400"))
    except StatementError as refusal:
        assert isinstance(refusal.orig, ValueError) and "finite" in str(refusal.orig), f"Decimal('1E+400') in {model.__name__}.{column} was refused with {refusal.orig!r}: expected the ValueError of process_bind_param, naming 'finite'"
        return
    except (TypeError, ArithmeticError) as exc:
        pytest.fail(f"Decimal('1E+400') was written to {model.__name__}.{column} (a REAL inf), and reading it back raised {exc!r} (R13-SEC2: refuse it on write)")
    pytest.fail(f"Decimal('1E+400') was written to {model.__name__}.{column} as {storage} and reads back {read!r} (R13-SEC2: refuse it on write)")


# --------------------------------------------------------------------------- #
# R13-SEC2 (W-B58): the integer digits, in decimal_limit_issue and its two new helpers
# --------------------------------------------------------------------------- #


def _never_raising(function, typed: str, model, column: str):
    """``function(Decimal(typed), model, column)``; an exception fails the test, naming it: a request carrying the value
    would answer 500 instead of a refusal."""
    try:
        return function(Decimal(typed), model, column)
    except (ArithmeticError, TypeError, ValueError) as exc:
        pytest.fail(f"{function.__name__}({typed}, {model.__name__}, {column!r}) raised {exc!r}: a request carrying it answers 500 instead of a refusal (R13-SEC2: it never raises)")


def _integer_digits_issue():
    """``precision.integer_digits_issue``, looked up when the test runs: the function is new in R13-SEC2."""
    found = getattr(precision, "integer_digits_issue", None)
    if found is None:
        pytest.fail("backend/app/db/precision.py has no integer_digits_issue: a provider's volume of 1E+400 is written as a REAL inf, and nothing measures the magnitude of a value apart from its decimals")
    return found


def _storable_value():
    """``precision.storable_value``, looked up when the test runs: the function is new in R13-SEC2."""
    found = getattr(precision, "storable_value", None)
    if found is None:
        pytest.fail("backend/app/db/precision.py has no storable_value: a provider's close of 1E+60 reaches truncate_priceHistory, which raises InvalidOperation in the middle of a refresh")
    return found


def _max_integer_digits():
    """``precision.max_integer_digits``, looked up when the test runs: the function is new in R13-SEC2 (decision N63)."""
    found = getattr(precision, "max_integer_digits", None)
    if found is None:
        pytest.fail("backend/app/db/precision.py has no max_integer_digits: nothing says how many digits before the decimal point a column keeps, so a quantity of 1E+60 is stored")
    return found


@pytest.mark.parametrize(
    ("model", "column", "expected"),
    [
        pytest.param(Transaction, "quantity", 15, id="Transaction.quantity-15-N63"),
        pytest.param(Transaction, "amount", 15, id="Transaction.amount-15-N63"),
        pytest.param(Transaction, "cost_basis_override", 12, id="Transaction.cost_basis_override-12"),
        pytest.param(PriceHistory, "open", 12, id="PriceHistory.open-12"),
        pytest.param(PriceHistory, "high", 12, id="PriceHistory.high-12"),
        pytest.param(PriceHistory, "low", 12, id="PriceHistory.low-12"),
        pytest.param(PriceHistory, "close", 12, id="PriceHistory.close-12"),
        pytest.param(PriceHistory, "adjusted_close", 12, id="PriceHistory.adjusted_close-12"),
        pytest.param(PriceHistory, "volume", 24, id="PriceHistory.volume-24"),
        pytest.param(AssetEvent, "value", 12, id="AssetEvent.value-12"),
        pytest.param(FxRate, "rate", 14, id="derived-FxRate.rate-14"),
    ],
)
def test_max_integer_digits(model, column, expected):
    """Red today: the function does not exist.

    Contract (R13-SEC2, the coordinator's decision N63 of 17/10): 15, ``REAL_SIGNIFICANT_DIGITS``, for
    ``Transaction.quantity`` and ``Transaction.amount``; for every other column the integer digits its declaration gives,
    ``precision - scale`` — 12 for the per-unit cost basis, the five prices and an event value, 24 for the volume.
    ``FxRate.rate`` (24, 10), 14, is derived from "every other column".
    """
    found = _max_integer_digits()(model, column)

    assert found == expected, f"max_integer_digits({model.__name__}, {column!r}) = {found!r}: expected {expected}"
    assert type(found) is int, f"max_integer_digits({model.__name__}, {column!r}) returned a {type(found).__name__}, not an int"


def test_the_integer_digits_code_is_named():
    """Red today: ``precision`` has no ``INTEGER_DIGITS_EXCEEDED``. Contract (R13-SEC2): ``"integerDigitsExceeded"``, the
    value of ``TXValidationCode.INTEGER_DIGITS_EXCEEDED``."""
    found = getattr(precision, "INTEGER_DIGITS_EXCEEDED", None)

    assert found == "integerDigitsExceeded", f"precision.INTEGER_DIGITS_EXCEEDED is {found!r}: expected 'integerDigitsExceeded'"


@pytest.mark.parametrize(
    ("typed", "model", "column", "expected"),
    [
        pytest.param("1E+60", Transaction, "quantity", ("integerDigitsExceeded", 15), id="quantity-1E+60"),
        pytest.param("1E+15", Transaction, "quantity", ("integerDigitsExceeded", 15), id="quantity-1E+15-is-16-integer-digits"),
        pytest.param("1000000000000000", Transaction, "quantity", ("integerDigitsExceeded", 15), id="quantity-16-integer-digits"),
        pytest.param("-1E+15", Transaction, "amount", ("integerDigitsExceeded", 15), id="amount--1E+15"),
        pytest.param("1E+13", Transaction, "cost_basis_override", ("integerDigitsExceeded", 12), id="cost-basis-1E+13"),
        pytest.param("1000000000000", Transaction, "cost_basis_override", ("integerDigitsExceeded", 12), id="cost-basis-13-integer-digits"),
        pytest.param("1E+13", PriceHistory, "close", ("integerDigitsExceeded", 12), id="close-1E+13"),
        pytest.param("1234567890123.4", PriceHistory, "close", ("integerDigitsExceeded", 12), id="close-13-integer-digits-within-the-other-limits"),
        pytest.param("1E+48", PriceHistory, "close", ("integerDigitsExceeded", 12), id="close-1E+48"),
        pytest.param("1E+13", AssetEvent, "value", ("integerDigitsExceeded", 12), id="event-1E+13"),
        pytest.param("1E+25", PriceHistory, "volume", ("integerDigitsExceeded", 24), id="volume-1E+25"),
        pytest.param("1E+1000000", Transaction, "quantity", ("integerDigitsExceeded", 15), id="quantity-1E+1000000-no-overflow"),
        pytest.param("1E-2000000", PriceHistory, "close", ("decimalPlacesExceeded", 12), id="close-1E-2000000-no-underflow"),
        pytest.param("Infinity", Transaction, "quantity", ("integerDigitsExceeded", 15), id="quantity-Infinity"),
        pytest.param("-Infinity", Transaction, "amount", ("integerDigitsExceeded", 15), id="amount--Infinity"),
        pytest.param("NaN", PriceHistory, "close", ("integerDigitsExceeded", 12), id="close-NaN"),
        pytest.param("sNaN", PriceHistory, "volume", ("integerDigitsExceeded", 24), id="derived-volume-sNaN"),
    ],
)
def test_decimal_limit_issue_refuses_more_integer_digits_than_the_column_keeps(typed, model, column, expected):
    """Red today: the limit has no magnitude, so ``1E+60``, ``1E+15``, 16 integer digits, ``-1E+15``, ``1E+13``, 13
    integer digits, ``1E+48`` and ``1E+25`` pass (few digits, no decimals); ±Infinity and NaN pass too (their exponent
    is no int); ``1E+1000000`` raises ``decimal.Overflow`` and ``sNaN`` ``InvalidOperation`` (``normalize`` in a context
    of 60 digits); ``1E-2000000`` underflows to 0 there and passes.

    Contract (R13-SEC2, limits of decision N63): computed from the digits, without a context, never raising: decimal
    places, then significant digits, then integer digits — more than ``max_integer_digits`` (15 for a quantity and an
    amount, 12 for a cost basis, a price and an event value, 24 for a volume) answers ``("integerDigitsExceeded",
    max)``, as does a non-finite value. ``1E-2000000`` has two million decimal places. ``sNaN`` is derived from "never
    raises for any Decimal".
    """
    found = _never_raising(precision.decimal_limit_issue, typed, model, column)

    assert found == expected, f"decimal_limit_issue({typed}, {model.__name__}, {column!r}) = {found!r}: expected {expected!r}"


@pytest.mark.parametrize(
    ("typed", "model", "column", "expected"),
    [
        pytest.param("999999999999999", Transaction, "quantity", None, id="quantity-15-integer-digits"),
        pytest.param("-999999999999999", Transaction, "amount", None, id="amount-15-integer-digits"),
        pytest.param("-1E+13", Transaction, "amount", None, id="amount--1E+13-14-integer-digits"),
        pytest.param("1000000000000", Transaction, "quantity", None, id="quantity-13-integer-digits"),
        pytest.param("999999999999999.0000000000", Transaction, "quantity", None, id="quantity-15-integer-digits-trailing-zeros"),
        pytest.param("999999999999", Transaction, "cost_basis_override", None, id="cost-basis-12-integer-digits"),
        pytest.param("999999999999.999", PriceHistory, "close", None, id="close-12-integer-digits-15-significant-digits"),
        pytest.param("0E+70", Transaction, "quantity", None, id="zero-with-a-large-exponent"),
        pytest.param("0E-2000000", PriceHistory, "close", None, id="zero-with-a-small-exponent"),
        pytest.param("1234567890123.456", Transaction, "quantity", ("significantDigitsExceeded", 15), id="quantity-16-significant-digits-still-significant"),
        pytest.param("1234567890123456.7", Transaction, "quantity", ("significantDigitsExceeded", 15), id="order-quantity-significant-digits-before-integer-digits"),
        pytest.param("1234567890123456.7", Transaction, "amount", ("significantDigitsExceeded", 15), id="order-amount-significant-digits-before-integer-digits"),
        pytest.param("10000000000000000.12345678901", Transaction, "quantity", ("decimalPlacesExceeded", 10), id="order-decimal-places-before-integer-digits"),
        pytest.param("1234567890123.45678", Transaction, "cost_basis_override", ("significantDigitsExceeded", 15), id="order-cost-basis-significant-digits-before-integer-digits"),
    ],
)
def test_guard_decimal_limit_issue_keeps_its_results_at_and_around_the_integer_limit(typed, model, column, expected):
    """Guard: green today and after. The integer limit is reached, not passed: 15 digits for a quantity and an amount
    (decision N63: a quantity of 13 digits and an amount of -1E+13 are accepted), 12 for a cost basis and a price;
    trailing zeros are not counted; a zero is a zero whatever its exponent; and the order keeps the results of C-97a: a
    value past two limits gets the code of the first (decimal places, then significant digits), so a quantity of 16
    digits still reads ``significantDigitsExceeded``.
    """
    found = _never_raising(precision.decimal_limit_issue, typed, model, column)

    assert found == expected, f"decimal_limit_issue({typed}, {model.__name__}, {column!r}) = {found!r}: expected {expected!r}, as today"


@pytest.mark.parametrize(
    ("typed", "model", "column", "expected"),
    [
        pytest.param("1E+400", PriceHistory, "volume", ("integerDigitsExceeded", 24), id="volume-1E+400"),
        pytest.param("1.5", PriceHistory, "volume", None, id="volume-1.5-decimals-not-checked"),
        pytest.param("1E+25", PriceHistory, "volume", ("integerDigitsExceeded", 24), id="derived-volume-1E+25"),
        pytest.param("999999999999999999999999", PriceHistory, "volume", None, id="derived-volume-24-integer-digits"),
        pytest.param("1E+13", PriceHistory, "close", ("integerDigitsExceeded", 12), id="derived-close-1E+13"),
        pytest.param("0.0000000000001", PriceHistory, "close", None, id="derived-close-13-decimals-not-checked"),
        pytest.param("3333.333333333333", PriceHistory, "close", None, id="derived-close-16-significant-digits-not-checked"),
        pytest.param("1E-2000000", PriceHistory, "close", None, id="derived-close-1E-2000000-magnitude-only"),
        pytest.param("1E+15", Transaction, "quantity", ("integerDigitsExceeded", 15), id="derived-quantity-1E+15"),
        pytest.param("999999999999999", Transaction, "quantity", None, id="derived-quantity-15-integer-digits"),
        pytest.param("1E+1000000", Transaction, "quantity", ("integerDigitsExceeded", 15), id="derived-quantity-1E+1000000"),
        pytest.param("Infinity", PriceHistory, "close", ("integerDigitsExceeded", 12), id="derived-close-Infinity"),
        pytest.param("NaN", PriceHistory, "volume", ("integerDigitsExceeded", 24), id="derived-volume-NaN"),
    ],
)
def test_integer_digits_issue_measures_the_magnitude_and_the_finiteness_alone(typed, model, column, expected):
    """Red today: the function does not exist.

    Contract (R13-SEC2): ``integer_digits_issue(value, model, column)`` checks only the magnitude, against
    ``max_integer_digits``, and the finiteness — the volume, a count read back rounded, has no other limit: a volume of
    ``1E+400`` → ``("integerDigitsExceeded", 24)``, of ``1.5`` → None (the brief's two examples); the ``derived-`` cases
    read the same rule (no decimal or significant-digit check, never raising).
    """
    found = _never_raising(_integer_digits_issue(), typed, model, column)

    assert found == expected, f"integer_digits_issue({typed}, {model.__name__}, {column!r}) = {found!r}: expected {expected!r}"


@pytest.mark.parametrize(
    ("typed", "model", "column", "expected"),
    [
        pytest.param("1E+400", PriceHistory, "close", None, id="close-1E+400"),
        pytest.param("1E+60", PriceHistory, "close", None, id="close-1E+60"),
        pytest.param("1E+48", PriceHistory, "close", None, id="close-1E+48"),
        pytest.param("Infinity", PriceHistory, "close", None, id="close-Infinity"),
        pytest.param("123.4567890123456", PriceHistory, "close", Decimal("123.456789012345"), id="close-truncated-to-15-significant-digits"),
        pytest.param("1E+13", PriceHistory, "close", None, id="derived-close-13-integer-digits"),
        pytest.param("-1E+60", PriceHistory, "open", None, id="derived-open--1E+60"),
        pytest.param("NaN", PriceHistory, "high", None, id="derived-high-NaN"),
        pytest.param("1E+1000000", PriceHistory, "low", None, id="derived-low-1E+1000000"),
        pytest.param("999999999999.9999999", PriceHistory, "close", Decimal("999999999999.999"), id="derived-close-12-integer-digits-truncated"),
    ],
)
def test_storable_value_truncates_a_provider_value_or_answers_none(typed, model, column, expected):
    """Red today: the function does not exist; the provider paths call ``truncate_priceHistory``, which raises
    ``InvalidOperation`` from ``1E+48`` up (12 decimals in 60 digits) and on any non-finite value.

    Contract (R13-SEC2): ``storable_value(value, model, column)`` is the value truncated to the column
    (``truncate_to_db_precision``: 12 decimals then 15 significant digits, ``ROUND_DOWN``), or None when
    ``integer_digits_issue`` is not None; it never raises. The ``derived-`` cases read the same rule.
    """
    found = _never_raising(_storable_value(), typed, model, column)

    assert found == expected, f"storable_value({typed}, {model.__name__}, {column!r}) = {found!r}: expected {expected!r}"
    if expected is not None:
        assert isinstance(found, Decimal), f"storable_value({typed}) returned a {type(found).__name__}, not a Decimal"


# --------------------------------------------------------------------------- #
# X-R38 (the FX side of W-B58): storable_fx_rate, an exchange rate as fx_rates.rate keeps it
# --------------------------------------------------------------------------- #


def _storable_fx_rate_never_raising(typed: str):
    """``precision.storable_fx_rate(Decimal(typed))``, looked up when the test runs. Any exception fails the test naming
    it, the stub's ``NotImplementedError`` included: a provider sync meeting the rate loses its pair, a manual rate
    carrying it answers 500 (X-R38: it never raises)."""
    storable_fx_rate = getattr(precision, "storable_fx_rate", None)
    if storable_fx_rate is None:
        pytest.fail("backend/app/db/precision.py has no storable_fx_rate: nothing says which exchange rate fx_rates.rate can keep, so 1E+400 is stored as a REAL inf and 1E-11 as 0")
    try:
        return storable_fx_rate(Decimal(typed))
    except Exception as exc:  # noqa: BLE001 — any exception is the defect under test, the stub's NotImplementedError included
        pytest.fail(f"storable_fx_rate({typed}) raised {exc!r}: a provider sync meeting the rate loses its pair, a manual rate carrying it answers 500 (X-R38: it never raises)")


@pytest.mark.parametrize(
    "typed",
    [
        pytest.param("100000000000000", id="15-integer-digits"),
        pytest.param("1E+14", id="1E+14-15-integer-digits"),
        pytest.param("1E+15", id="1E+15"),
        pytest.param("1E+50", id="1E+50-truncate_fx_rate-raises"),
        pytest.param("1E+400", id="1E+400"),
        pytest.param("1E+1000000", id="derived-1E+1000000"),
        pytest.param("1E-11", id="1E-11-0-once-truncated"),
        pytest.param("0.000000000099", id="derived-0.000000000099-0-once-truncated"),
        pytest.param("1E-2000000", id="derived-1E-2000000-0-once-truncated"),
        pytest.param("0", id="0"),
        pytest.param("Infinity", id="Infinity"),
        pytest.param("-Infinity", id="-Infinity"),
        pytest.param("NaN", id="NaN"),
        pytest.param("sNaN", id="derived-sNaN"),
    ],
)
def test_xr38_storable_fx_rate_answers_none_for_a_rate_no_column_can_keep(typed):
    """Red today: ``storable_fx_rate`` is a stub raising ``NotImplementedError``. What the FX writers call instead,
    ``truncate_fx_rate``, raises ``InvalidOperation`` from ``1E+50`` up and on ±Infinity, and gives 0 for ``1E-11``.

    Contract (X-R38): None, never an exception, when the rate is not finite, has more digits before the decimal point
    than ``max_integer_digits(FxRate, "rate")`` (14: ``100000000000000`` and ``1E+14`` have 15), or is 0 once truncated to
    the 10 decimal places of ``fx_rates.rate`` (a rate is never 0: its inverse and the conversions divide by it). The
    ``derived-`` cases read the same rule.
    """
    found = _storable_fx_rate_never_raising(typed)

    assert found is None, f"storable_fx_rate({typed}) = {found!r}: expected None, fx_rates.rate cannot keep it"


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        pytest.param("1.0850123456", "1.0850123456", id="10-decimals"),
        pytest.param("1.08501234567890", "1.0850123456", id="cut-at-10-decimals-round-down"),
        pytest.param("99999999999999", "99999999999999", id="14-integer-digits"),
        pytest.param("1E+13", "10000000000000", id="1E+13-14-integer-digits"),
        pytest.param("1E-10", "0.0000000001", id="1E-10-the-smallest-rate-kept"),
        pytest.param("0.00000000019", "0.0000000001", id="cut-to-1E-10"),
        pytest.param("1.50000000000000000000", "1.5", id="trailing-zeros"),
        pytest.param("-1.25", "-1.25", id="negative-the-callers-business"),
    ],
)
def test_xr38_storable_fx_rate_keeps_a_rate_as_truncate_fx_rate_gives_it(typed, expected):
    """Red today: ``storable_fx_rate`` is a stub raising ``NotImplementedError``.

    Contract (X-R38): a rate the column can keep comes back as ``truncate_fx_rate`` gives it, 10 decimal places
    ``ROUND_DOWN``, its form included. 14 digits before the decimal point and ``1E-10`` are the limits, not past them. A
    negative rate is not refused here: that is the caller's business (``upsert_rates_bulk`` refuses a rate of 0 or less).
    X-R50 adds the double: the case ``14-integer-digits-cut-at-10-decimals`` (``99999999999999.99999999999``), whose
    double is ``1E+14``, moved to ``test_xr50_storable_fx_rate_answers_none_for_a_rate_whose_double_is_1E14``.
    """
    found = _storable_fx_rate_never_raising(typed)

    truncated = precision.truncate_fx_rate(Decimal(typed))
    assert found == Decimal(expected), f"storable_fx_rate({typed}) = {found!r}: expected {expected}"
    assert isinstance(found, Decimal) and found.as_tuple() == truncated.as_tuple(), f"storable_fx_rate({typed}) = {found!r}: expected the value as truncate_fx_rate gives it, {truncated!r}"


# --------------------------------------------------------------------------- #
# X-R50 (E's review R13-SEC5 on X-R38): storable_fx_rate and the double SQLite keeps
# --------------------------------------------------------------------------- #


def _xr50_double(typed: str) -> float:
    """The double SQLite keeps for the rate as ``truncate_fx_rate`` gives it: ``fx_rates.rate`` is a REAL in the file."""
    return float(precision.truncate_fx_rate(Decimal(typed)))


@pytest.mark.parametrize(
    "typed",
    [
        pytest.param("99999999999999.995", id="14-integer-digits-double-1E+14"),
        pytest.param("99999999999999.9999999999", id="14-integer-digits-10-decimals-double-1E+14"),
        pytest.param("99999999999999.99999999999", id="14-integer-digits-cut-at-10-decimals-double-1E+14-kept-by-X-R38"),
        pytest.param("99999999999999.9921875", id="derived-halfway-below-1E+14-rounds-to-1E+14"),
    ],
)
def test_xr50_storable_fx_rate_answers_none_for_a_rate_whose_double_is_1E14(typed):
    """Red today: kept, as ``truncate_fx_rate`` gives it (``99999999999999.9950000000``): 14 digits before the decimal
    point are the X-R38 limit, not past it. SQLite keeps the rate as a double, ``1E+14``: a manual rate is answered
    «inserted» and a synced one stored, and every conversion then skips it as unusable (``convert_bulk`` reads only
    ``1E-10 <= rate < 1E+14``). The case ``…-kept-by-X-R38`` is the X-R38 case ``14-integer-digits-cut-at-10-decimals``,
    moved here from the test that keeps a rate: X-R50 reverses it.

    Contract (X-R50): None, never an exception, also when the double of the truncated rate is ``1E+14`` or more. The
    ``derived-`` case reads the same rule at its edge: halfway between the double below ``1E+14``
    (``99999999999999.984375``) and ``1E+14``, the rate rounds to ``1E+14`` (to even).
    """
    integer_digits = Decimal(typed).adjusted() + 1
    assert integer_digits == precision.max_integer_digits(FxRate, "rate"), f"barrier: {typed} has {integer_digits} digits before the decimal point, not the 14 X-R38 lets through: the digits would refuse it, not the double"
    double = _xr50_double(typed)
    assert double >= 1e14, f"barrier: the double of {typed}, cut to 10 decimal places, is {double!r}, below 1E+14"

    found = _storable_fx_rate_never_raising(typed)

    assert found is None, f"storable_fx_rate({typed}) = {found!r}: expected None, SQLite keeps it as {double!r}, a rate every conversion skips (X-R50)"


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        pytest.param("99999999999999.99", "99999999999999.99", id="14-integer-digits-double-99999999999999.98"),
        pytest.param("99999999999999.9921874999", "99999999999999.9921874999", id="derived-just-below-halfway-double-99999999999999.98"),
    ],
)
def test_xr50_guard_storable_fx_rate_keeps_a_rate_whose_double_stays_below_1E14(typed, expected):
    """Guard: green today and after. A rate of 14 digits before the decimal point whose double stays below ``1E+14``
    (``99999999999999.99`` is the double ``99999999999999.98``) comes back as ``truncate_fx_rate`` gives it, its form
    included: X-R50 refuses from the double ``1E+14``, never a margin below it. The function alone, no round trip. The
    ``derived-`` case reads the same rule at its edge, just below halfway."""
    double = _xr50_double(typed)
    assert double < 1e14, f"barrier: the double of {typed}, cut to 10 decimal places, is {double!r}, not below 1E+14"

    found = _storable_fx_rate_never_raising(typed)

    truncated = precision.truncate_fx_rate(Decimal(typed))
    assert found == Decimal(expected), f"storable_fx_rate({typed}) = {found!r}: expected {expected}, its double {double!r} is below 1E+14 (X-R50 refuses from 1E+14 only)"
    assert isinstance(found, Decimal) and found.as_tuple() == truncated.as_tuple(), f"storable_fx_rate({typed}) = {found!r}: expected the value as truncate_fx_rate gives it, {truncated!r}"


# --------------------------------------------------------------------------- #
# W-B60: an amount and an event value read back exactly
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("model", "column"), _AMOUNT_COLUMNS)
def test_an_amount_and_an_event_value_are_real_decimals(model, column):
    """Red today: both are a plain ``Numeric(18, 6)``, read through ``'%.6f'`` of the stored double.

    Contract (W-B60): ``backend.app.db.real_decimal.RealDecimal``, a TypeDecorator over Numeric, as the seven columns of
    C-97a.
    """
    column_type = _column_type(model, column)
    kind = f"{type(column_type).__module__}.{type(column_type).__qualname__}"

    assert kind == "backend.app.db.real_decimal.RealDecimal", f"{model.__name__}.{column} is a {kind}: from about 11 integer digits its read shows the double's noise in the 6 decimals (W-B60: RealDecimal(18, 6))"
    assert isinstance(column_type, TypeDecorator), f"RealDecimal must be a TypeDecorator, it is a {type(column_type).__mro__}"
    assert isinstance(column_type.impl, Numeric), f"RealDecimal must decorate Numeric, it decorates {column_type.impl!r}"


@pytest.mark.parametrize(("model", "column"), _AMOUNT_COLUMNS)
def test_guard_an_amount_and_an_event_value_keep_their_declaration_and_ddl(model, column):
    """GUARD (green before and after): W-B60 changes how the value is read, not the column — still (18, 6), and the same
    DDL, ``NUMERIC(18, 6) NOT NULL``, so no migration and every file already written stays readable."""
    table_column = model.__table__.c[column]

    assert precision.get_model_column_precision(model, column) == (18, 6), f"{model.__name__}.{column} is declared {precision.get_model_column_precision(model, column)}: W-B60 keeps (18, 6)"
    ddl = str(CreateColumn(table_column).compile(dialect=_SQLITE))
    assert ddl == f"{column} NUMERIC(18, 6) NOT NULL", f"{model.__name__}.{column} is created as {ddl!r}: W-B60 keeps {column} NUMERIC(18, 6) NOT NULL, without a migration"


@pytest.mark.parametrize(("model", "column"), _AMOUNT_COLUMNS)
@pytest.mark.parametrize(
    ("typed", "form"),
    [
        pytest.param("123456789012.345", "123456789012.345000", id="123456789012.345"),
        pytest.param("-99999999999999.9", "-99999999999999.900000", id="-99999999999999.9"),
        pytest.param("12345678901.2345", "12345678901.234500", id="12345678901.2345"),
    ],
)
def test_an_amount_or_an_event_value_reads_back_exactly_with_6_decimals(memory_engine, model, column, typed, form):
    """Red today: ``'%.6f'`` of the stored double shows its noise in the 6 decimals — 123456789012.345 reads
    123456789012.345001, -99999999999999.9 -99999999999999.906250, 12345678901.2345 12345678901.234501.

    Contract (W-B60): the value written, always with 6 decimals as today. Compared as text, so the 6 decimals are pinned.
    The read does not depend on the input limits: -99999999999999.9, past an event value's 12 integer digits, is a double
    like any other.
    """
    read, _storage = _write_and_read(memory_engine, _column_type(model, column), Decimal(typed))

    assert isinstance(read, Decimal), f"{model.__name__}.{column} reads back a {type(read).__name__}, not a Decimal"
    assert str(read) == form, f"{typed} in {model.__name__}.{column} reads back as {read}: expected {form}, the value written with 6 decimals (W-B60)"


@pytest.mark.parametrize(("model", "column"), _AMOUNT_COLUMNS)
@pytest.mark.parametrize(
    ("typed", "form", "storage"),
    [
        pytest.param("-100", "-100.000000", "integer", id="-100"),
        pytest.param("0.000001", "0.000001", "real", id="0.000001"),
        pytest.param("999999999999999", "999999999999999.000000", "integer", id="999999999999999"),
    ],
)
def test_guard_an_amount_or_an_event_value_that_reads_well_today_reads_the_same(memory_engine, model, column, typed, form, storage):
    """GUARD (green before and after): what ``Numeric(18, 6)`` reads without noise today reads the same after W-B60, form
    included, and is written as today: a whole value as an INTEGER, a fraction as a REAL."""
    read, stored_as = _write_and_read(memory_engine, _column_type(model, column), Decimal(typed))

    assert isinstance(read, Decimal), f"{model.__name__}.{column} reads back a {type(read).__name__}, not a Decimal"
    assert (str(read), stored_as) == (form, storage), f"{typed} in {model.__name__}.{column} reads back as {read}, stored as {stored_as}: today, and after W-B60, {form}, stored as {storage}"


@pytest.mark.parametrize(("model", "column"), _AMOUNT_COLUMNS)
@pytest.mark.parametrize("stored", [pytest.param(float("inf"), id="plus-inf"), pytest.param(float("-inf"), id="minus-inf")])
def test_a_stored_infinite_amount_or_event_value_reads_back_as_none(memory_engine, model, column, stored):
    """Red today: ``Numeric(18, 6)`` reads a REAL ±inf as ``Decimal('Infinity')`` (``'%.6f'`` of inf), which breaks
    later, wherever the value is summed or sent.

    Contract (W-B60): ``None``, as in every ``RealDecimal`` column (W-B58): no amount or event value is infinite.
    """
    read, storage = _read_back_never_raising(memory_engine, model, column, stored)

    assert storage == "real", f"the fixture itself is wrong: {stored!r} was stored as {storage}"
    assert read is None, f"a REAL {stored!r} in {model.__name__}.{column} reads back {read!r}: expected None, since no Decimal of the column is infinite (W-B60)"


@pytest.mark.parametrize(("model", "column"), _AMOUNT_COLUMNS)
@pytest.mark.parametrize("value", _BEYOND_A_DOUBLE)
def test_binding_a_value_a_double_cannot_hold_into_an_amount_or_an_event_value_raises_naming_finite(model, column, value):
    """Red today: a plain ``Numeric`` has no ``process_bind_param``; the value is bound as ``float('inf')``.

    Contract (W-B60): the ``process_bind_param`` of ``RealDecimal`` (W-B58) raises ``ValueError``, its message containing
    "finite", for any value that becomes ±inf as a float — ``Decimal('1E+400')`` the brief's, the others those W-B58
    refuses on every ``RealDecimal`` column.
    """
    bind = _process_bind_param(model, column)

    with pytest.raises(ValueError, match="finite"):
        bind(value, _SQLITE)


@pytest.mark.parametrize(("model", "column"), _AMOUNT_COLUMNS)
def test_writing_a_value_a_double_cannot_hold_into_an_amount_or_an_event_value_is_refused(memory_engine, model, column):
    """Red today: ``Decimal('1E+400')`` is written, a REAL inf, and reads back ``Decimal('Infinity')``.

    Contract (W-B60): the INSERT fails with a ``StatementError`` whose ``orig`` is the ``ValueError`` of
    ``process_bind_param``, naming "finite": nothing reaches the file.
    """
    try:
        read, storage = _write_and_read(memory_engine, _column_type(model, column), Decimal("1E+400"))
    except StatementError as refusal:
        assert isinstance(refusal.orig, ValueError) and "finite" in str(refusal.orig), f"Decimal('1E+400') in {model.__name__}.{column} was refused with {refusal.orig!r}: expected the ValueError of process_bind_param, naming 'finite'"
        return
    pytest.fail(f"Decimal('1E+400') was written to {model.__name__}.{column} as {storage} and reads back {read!r} (W-B60: refuse it on write)")
