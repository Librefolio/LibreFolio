"""
Series exports, CSV formula injection (lot B-39): ``backend/app/services/platform/series_export.py``.

The series exports of ``/api/v1/backup/*`` (prices, events, FX rates) stream CSV through ``stream_rows_as_csv``. A cell
a spreadsheet reads as a formula — text starting with ``=``, ``+``, ``-``, ``@``, a tab or a carriage return — runs when
the file is opened (OWASP, «CSV injection»), and a note or a source is user text. Under test, as the contract of lot
B-39 froze it:

(a) Escaped: a cell whose text, as ``_to_str`` writes it today, starts with one of those characters — or with
    apostrophes followed by one, so that removing the one apostrophe added gives the text back exactly (the pattern
    ``FORMULA_START``) — is written with one leading ``'``: ``=1+1`` → ``'=1+1``, ``@SUM(A1)``, ``-2+3``,
    ``+cmd|' /C calc'!A0``, ``\\t=1``, ``\\r=1``, ``\\r`` alone, ``'=x`` → ``''=x``, ``''@y`` → ``'''@y``, and a value
    that is no ``str`` but is written as one. In a row of the events' schema, only that cell.
(b) Never escaped: a plain number, whatever its type (``Decimal``, ``int``, text), which matches ``PLAIN_NUMBER`` in
    full: ``-1.5``, ``+2``, ``-1E+2``, ``-0``, ``-3``.
(c) Unchanged: dates, datetimes with a ``+00:00`` offset, ``None`` (an empty cell), text starting with anything else
    (``EUR``, ``DIVIDEND``, ``a = b``, ``'hello``: apostrophes that no formula character follows); the header row of
    each schema and the ``;`` delimiter.
(d) JSON: ``stream_rows_as_json`` writes every value as it is, without an apostrophe.

Every assertion is on the cells ``csv.reader`` (``;``) reads back out of the stream, never on its bytes: how ``csv``
quotes a cell is not the question.

Pure: the two stream functions called directly; no database, no server, no network, no file.

Written RED, before B-39: today every value is written as it is, so each case of (a) fails on the cell it reads back
(``=1+1`` where ``'=1+1`` is expected). (b), (c) and (d) are guards, green before B-39 as after it.
"""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from backend.app.services.platform.series_export import EVENT_COLUMNS, FX_RATE_COLUMNS, PRICE_COLUMNS, BackupScope, _to_str, stream_rows_as_csv, stream_rows_as_json
from backend.test_scripts.test_utils import print_section, print_success

#: The one column of the exports these tests write a value into.
COLUMN = "cell"
#: What a spreadsheet reads as the start of a formula, behind any apostrophes (contract): a cell whose text it starts is
#: escaped, unless the text is a plain number. The apostrophes keep the round trip exact: an importer removing the one
#: apostrophe added gets back ``'=x``, never ``=x``.
FORMULA_START = re.compile(r"'*[=+\-@\t\r]")
#: A plain number, never escaped whatever starts it (contract): matched in full.
PLAIN_NUMBER = re.compile(r"[+-]?\d+(\.\d+)?([eE][+-]?\d+)?")
#: A note that opens a link when the file is opened in a spreadsheet: user text, in the events' schema.
HYPERLINK = '=HYPERLINK("http://example.test/steal","click")'


class Text:
    """A value that is no ``str`` but is written as one: ``_to_str`` gives its ``str``, which the rule reads."""

    def __init__(self, text: str) -> None:
        self.text = text

    def __str__(self) -> str:
        return self.text

    def __repr__(self) -> str:
        return f"Text({self.text!r})"


def parsed(fieldnames: list[str], rows: list[dict[str, Any]]) -> list[list[str]]:
    """The cells ``csv.reader`` (``;``) reads back out of the CSV the export streams, the header row first."""
    text = "".join(stream_rows_as_csv(fieldnames, rows))
    return list(csv.reader(io.StringIO(text, newline=""), delimiter=";"))


def cell_of(value: Any) -> str:
    """The cell ``value`` becomes, alone in a one-column export, as read back."""
    table = parsed([COLUMN], [{COLUMN: value}])
    assert len(table) == 2 and table[0] == [COLUMN] and len(table[1]) == 1, f"precondition: the header and one row of one cell: {table!r}"
    return table[1][0]


# =============================================================================
# (a) Escaped
# =============================================================================


ESCAPED = [
    pytest.param("=1+1", id="equals"),
    pytest.param("@SUM(A1)", id="at"),
    pytest.param("-2+3", id="minus-not-a-number"),
    pytest.param("+cmd|' /C calc'!A0", id="plus-a-command"),
    pytest.param("\t=1", id="tab"),
    pytest.param("\r=1", id="carriage-return"),
    pytest.param("\r", id="a-carriage-return-alone"),
    pytest.param("'=x", id="an-apostrophe-then-equals"),
    pytest.param("''@y", id="two-apostrophes-then-at"),
    pytest.param(Text(HYPERLINK), id="no-str-written-as-one"),
]


@pytest.mark.parametrize("value", ESCAPED)
def test_a_cell_a_spreadsheet_would_read_as_a_formula_is_written_with_one_leading_apostrophe(value):
    """(a) The text as ``_to_str`` writes it starts like a formula, behind any apostrophes, and is no plain number: the
    cell read back is that text behind one ``'`` more, which a spreadsheet shows and never runs, and an importer
    removing that one ``'`` gives back exactly (``'=x`` → ``''=x``)."""
    print_section("B-39: a cell that starts like a formula")
    text = _to_str(value)
    assert text is not None and FORMULA_START.match(text) and not PLAIN_NUMBER.fullmatch(text), f"precondition: {text!r} starts like a formula and is no plain number"
    expected = "'" + text
    written = cell_of(value)
    assert written == expected, f"{value!r}: read back {written!r}, expected {expected!r}"
    print_success(f"{text!r} → {written!r}")


def test_in_a_row_of_the_events_schema_only_the_cell_that_starts_like_a_formula_is_escaped():
    """(a) A whole event row, as the export of an asset's events writes it: the note that starts like a formula is
    escaped; its date, type, negative value, currency, source, empty provider and the two UTC datetimes are not."""
    row = {
        "date": date(2026, 10, 17),
        "type": "DIVIDEND",
        "value": Decimal("-1.5"),
        "currency": "EUR",
        "source": "MANUAL",
        "provider_assignment_id": None,
        "notes": HYPERLINK,
        "created_at": datetime(2026, 10, 17, 9, 30, tzinfo=UTC),
        "updated_at": datetime(2026, 10, 17, 9, 31, tzinfo=UTC),
    }
    assert list(row) == EVENT_COLUMNS, f"precondition: a row of the events' schema, in its order: {EVENT_COLUMNS}"
    expected = ["2026-10-17", "DIVIDEND", "-1.5", "EUR", "MANUAL", "", "'" + HYPERLINK, "2026-10-17T09:30:00+00:00", "2026-10-17T09:31:00+00:00"]
    table = parsed(EVENT_COLUMNS, [row])
    assert table == [EVENT_COLUMNS, expected], f"the header, then the row with only its note escaped: {table!r}"
    print_success("only the note escaped")


# =============================================================================
# (b) Never escaped: a plain number
# =============================================================================


PLAIN_NUMBERS = [
    pytest.param(Decimal("-1.5"), id="decimal-negative"),
    pytest.param("-1.5", id="text-negative"),
    pytest.param("+2", id="text-with-a-plus"),
    pytest.param("-1E+2", id="text-with-an-exponent"),
    pytest.param(Decimal("-1E+2"), id="decimal-with-an-exponent"),
    pytest.param("-0", id="text-minus-zero"),
    pytest.param(-3, id="int-negative"),
]


@pytest.mark.parametrize("value", PLAIN_NUMBERS)
def test_a_plain_number_is_never_escaped_whatever_its_type(value):
    """(b) A guard, green before B-39 too: a number starts with ``-`` or ``+`` as a formula does, yet a spreadsheet reads
    it as a number; it is written as ``_to_str`` writes it."""
    text = _to_str(value)
    assert text is not None and FORMULA_START.match(text) and PLAIN_NUMBER.fullmatch(text), f"precondition: {text!r} starts like a formula and is a plain number"
    written = cell_of(value)
    assert written == text, f"{value!r}: read back {written!r}, expected it as it is"
    print_success(f"{text!r} as it is")


# =============================================================================
# (c) Unchanged
# =============================================================================


UNCHANGED = [
    pytest.param(date(2026, 10, 17), "2026-10-17", id="date"),
    pytest.param(datetime(2026, 10, 17, 9, 30, tzinfo=UTC), "2026-10-17T09:30:00+00:00", id="datetime-utc"),
    pytest.param(None, "", id="none-an-empty-cell"),
    pytest.param(Decimal("12.50"), "12.50", id="decimal"),
    pytest.param("EUR", "EUR", id="currency"),
    pytest.param("DIVIDEND", "DIVIDEND", id="event-type"),
    pytest.param("a = b", "a = b", id="an-equals-sign-inside"),
    pytest.param("'hello", "'hello", id="an-apostrophe-no-formula-character-follows"),
]


@pytest.mark.parametrize(("value", "expected"), UNCHANGED)
def test_a_cell_that_does_not_start_like_a_formula_is_written_as_today(value, expected):
    """(c) A guard, green before B-39 too: dates, UTC datetimes (their ``+`` is inside), an empty cell for ``None``, text
    that starts with anything else — apostrophes included, when no formula character follows them."""
    assert value is None or not FORMULA_START.match(str(_to_str(value))), f"precondition: {value!r} does not start like a formula"
    written = cell_of(value)
    assert written == expected, f"{value!r}: read back {written!r}, expected {expected!r}"
    print_success(f"{expected!r} as today")


SCHEMAS = [pytest.param(PRICE_COLUMNS, id="prices"), pytest.param(EVENT_COLUMNS, id="events"), pytest.param(FX_RATE_COLUMNS, id="fx-rates")]


@pytest.mark.parametrize("fieldnames", SCHEMAS)
def test_the_header_row_and_the_semicolon_are_unchanged(fieldnames):
    """(c) A guard, green before B-39 too: each schema's header row, its names as they are, and every row split by
    ``;`` into as many cells as the header names (read with any other delimiter, a line would be one cell)."""
    table = parsed(fieldnames, [dict.fromkeys(fieldnames, "x")])
    assert table == [fieldnames, ["x"] * len(fieldnames)], f"the header, then one row, split by ';': {table!r}"
    print_success(f"{len(fieldnames)} columns, ';'")


# =============================================================================
# (d) JSON
# =============================================================================


def test_the_json_export_writes_every_value_as_it_is():
    """(d) A guard, green before B-39 too: the JSON export is not a spreadsheet's input; the text that starts like a
    formula is written as it is, no apostrophe added, and a ``Decimal`` as its text."""
    values: list[Any] = ["=1+1", "@SUM(A1)", "-2+3", "+cmd|' /C calc'!A0", "\t=1", "\r=1", "'=x", "''@y", "'hello", HYPERLINK, "-1.5", Decimal("-1.5"), "EUR"]
    document = json.loads("".join(stream_rows_as_json(BackupScope.EVENTS, {"asset_id": 1}, [{COLUMN: value} for value in values])))
    written = [row[COLUMN] for row in document["rows"]]
    assert written == [str(value) for value in values], f"every value as it is: {written!r}"
    assert document["row_count"] == len(values), f"the envelope counts the rows: {document['row_count']}"
    print_success(f"{len(values)} values as they are")
