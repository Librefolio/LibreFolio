"""
Test Suite: the shared core of the report-set BRIM plugins (``brim_report_set_core``)

``backend.app.services.brim.brim_report_set_core`` holds what every report-set plugin needs whatever the bank
(Danske Bank today, Crédit Agricole next): text and number helpers, the spreadsheet and CSV readers with the header
scan, rule M (several files of one role), one-to-one pairing without a guess, and the segments of a timeline with the
zone of a date. It was extracted from the Danske Bank plugin with behaviour unchanged; these tests pin that behaviour
on small, hand-made, synthetic data, so the second plugin can lean on it.

Covered:

- A text, numbers, dates: ``norm``, ``plain``, ``money``, ``add_business_days``, ``compatible``, ``source``,
  ``match_key_text``;
- B source files: ``layout``, ``find_layout``, ``xlsx_rows`` (an ``.xlsx`` built with openpyxl under ``tmp_path``),
  ``csv_rows`` (a ``;`` and a ``,`` file under ``tmp_path``);
- C rule M: ``coverage``, ``by_day``, ``same_rows``, ``contained_rows`` and ``RoleMerge`` (which file owns which day, which
  rows are superseded, on which days two files contradict; the ``owner`` and ``contradiction`` policies);
- D pairing: ``assign``, ``best_assignment``, ``pair_by_key`` (a pair only when it is certain, else the rows are
  listed as ambiguous), and ``pair_outcome_of`` (the right row decides what a pair imports);
- E timeline: ``merge_spans``, ``build_timeline``, ``zone``, ``Segment.zone``.

Pure: no database, no server, no network, no clock. A row of rule M is a tiny frozen dataclass with a ``day`` and a
``signature``; the files of B live in ``tmp_path``. No assertion counts anything the test did not build itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import openpyxl
import pytest

from backend.app.services.brim import brim_report_set_core as core
from backend.app.services.brim.brim_report_set_core import RoleMerge, Segment

# 2026-03-02 is a Monday: every date below is written as an offset from the Sunday before it, so a weekday is easy to read.
_SUNDAY = date(2026, 3, 1)


def day(offset: int) -> date:
    """``2026-03-01`` (a Sunday) plus ``offset`` days: day(1) is a Monday, day(5) a Friday, day(6) a Saturday."""
    return _SUNDAY + timedelta(days=offset)


# =============================================================================
# A. TEXT, NUMBERS, DATES
# =============================================================================


class TestNorm:
    def test_case_and_surrounding_spaces(self):
        assert core.norm("  Foo   BAR ") == "foo bar"

    def test_br_tags_count_as_a_space(self):
        assert core.norm("Amount<br/>EUR") == "amount eur"
        assert core.norm("Amount<BR>EUR") == "amount eur"
        assert core.norm("Amount<br />EUR") == "amount eur"
        assert core.norm("Amount <br/> EUR") == "amount eur"

    def test_none_is_empty(self):
        assert core.norm(None) == ""

    def test_non_string_is_stringified(self):
        assert core.norm(12) == "12"

    def test_casefold_not_lower(self):
        assert core.norm("Straße") == "strasse"

    def test_tabs_and_newlines_collapse(self):
        assert core.norm("a\t\n b") == "a b"


class TestPlain:
    def test_no_trailing_zeros(self):
        assert core.plain(Decimal("1.500")) == "1.5"
        assert core.plain(Decimal("0.10")) == "0.1"

    def test_integer_keeps_its_zeros(self):
        assert core.plain(Decimal("100")) == "100"
        assert core.plain(Decimal("1E+3")) == "1000"

    def test_no_exponent_for_small_values(self):
        assert core.plain(Decimal("1E-7")) == "0.0000001"

    def test_negative_zero_is_zero(self):
        assert core.plain(Decimal("-0")) == "0"
        assert core.plain(Decimal("-0.00")) == "0"

    def test_zero_with_decimals_is_zero(self):
        assert core.plain(Decimal("0.000")) == "0"

    def test_negative_value_keeps_its_sign(self):
        assert core.plain(Decimal("-12.50")) == "-12.5"


class TestMoney:
    def test_two_places(self):
        assert core.money(Decimal("5")) == "5.00"
        assert core.money(Decimal("2.5")) == "2.50"

    def test_rounds_to_cents(self):
        assert core.money(Decimal("1234.567")) == "1234.57"

    def test_plain_notation_for_large_exponent(self):
        assert core.money(Decimal("1E+2")) == "100.00"


class TestAddBusinessDays:
    def test_zero_days_is_the_same_day_even_on_a_weekend(self):
        assert core.add_business_days(day(1), 0) == day(1)
        assert core.add_business_days(day(6), 0) == day(6)

    def test_friday_plus_one_is_monday(self):
        assert core.add_business_days(day(5), 1) == day(8)

    def test_over_a_weekend(self):
        # Thursday + 3 weekdays: Friday, Monday, Tuesday.
        assert core.add_business_days(day(4), 3) == day(9)

    def test_start_on_a_saturday(self):
        # The Saturday itself is not counted: the first weekday after it is the Monday.
        assert core.add_business_days(day(6), 1) == day(8)

    def test_a_whole_week(self):
        assert core.add_business_days(day(5), 5) == day(12)


class TestCompatible:
    def test_prefix_both_ways(self):
        assert core.compatible("ACME Corporation", "acme")
        assert core.compatible("acme", "ACME Corporation")

    def test_equal_names(self):
        assert core.compatible("Acme", "ACME")

    def test_spacing_and_br_are_ignored(self):
        assert core.compatible("Acme  <br/>Corp", "acme corp")

    def test_different_names(self):
        assert not core.compatible("acme", "beta")

    def test_not_a_prefix_just_a_substring(self):
        assert not core.compatible("corporation acme", "acme")

    def test_empty_is_never_compatible(self):
        assert not core.compatible("", "acme")
        assert not core.compatible("acme", "")
        assert not core.compatible("", "")
        assert not core.compatible("  ", "acme")


class TestSource:
    def test_one_file_has_no_file_number(self):
        assert core.source("sec", 0, 1, 7) == "sec:7"

    def test_several_files_carry_the_file_number(self):
        assert core.source("sec", 2, 3, 7) == "sec#2:7"
        assert core.source("cash", 0, 2, 11) == "cash#0:11"


class TestMatchKeyText:
    def test_date_amount_currency(self):
        assert core.match_key_text(date(2026, 3, 2), Decimal("12.5"), "EUR") == "2026-03-02|12.50|EUR"

    def test_zero_amount_is_a_key(self):
        assert core.match_key_text(date(2026, 3, 2), Decimal("0"), "EUR") == "2026-03-02|0.00|EUR"

    def test_missing_date_gives_empty(self):
        assert core.match_key_text(None, Decimal("12.5"), "EUR") == ""

    def test_missing_amount_gives_empty(self):
        assert core.match_key_text(date(2026, 3, 2), None, "EUR") == ""

    def test_both_missing_gives_empty(self):
        assert core.match_key_text(None, None, "EUR") == ""


# =============================================================================
# B. SOURCE FILES
# =============================================================================

_NAMES: Dict[str, str] = {"date": "day", "booking date": "day", "amount": "amount", "label": "label"}
_REQUIRED = {"day", "amount"}


class TestLayout:
    def test_columns_by_canonical_name(self):
        assert core.layout(["  DATE ", "Label", "Amount"], _NAMES, _REQUIRED) == {"day": 0, "label": 1, "amount": 2}

    def test_unknown_columns_and_non_text_cells_are_ignored(self):
        assert core.layout([None, "Date", 5, "Amount", "Whatever"], _NAMES, _REQUIRED) == {"day": 1, "amount": 3}

    def test_br_in_a_header_is_a_space(self):
        names = {"booking date": "day", "amount": "amount"}
        assert core.layout(["Booking<br/>date", "Amount"], names, _REQUIRED) == {"day": 0, "amount": 1}

    def test_required_missing_is_none(self):
        assert core.layout(["Date", "Label"], _NAMES, _REQUIRED) is None

    def test_optional_missing_is_fine(self):
        assert core.layout(["Date", "Amount"], _NAMES, _REQUIRED) == {"day": 0, "amount": 1}

    def test_duplicate_header_keeps_the_first(self):
        assert core.layout(["Date", "Amount", "Date"], _NAMES, _REQUIRED) == {"day": 0, "amount": 1}

    def test_two_aliases_of_one_column_keep_the_first(self):
        assert core.layout(["Amount", "Booking date", "Date"], _NAMES, _REQUIRED) == {"amount": 0, "day": 1}

    def test_empty_header_is_none(self):
        assert core.layout([], _NAMES, _REQUIRED) is None


class TestFindLayout:
    @staticmethod
    def _detect(row: Sequence[object]) -> Optional[Dict[str, int]]:
        return core.layout(row, _NAMES, _REQUIRED)

    def test_header_on_the_first_row(self):
        rows = [["Date", "Amount"], ["2026-03-02", "1"]]
        assert core.find_layout(rows, self._detect, 5) == (0, {"day": 0, "amount": 1})

    def test_header_on_row_three(self):
        rows = [["Account report"], ["generated on a Monday"], ["Date", "Label", "Amount"], ["2026-03-02", "x", "1"]]
        assert core.find_layout(rows, self._detect, 10) == (2, {"day": 0, "label": 1, "amount": 2})

    def test_header_beyond_scan_rows_is_not_found(self):
        rows = [["a"], ["b"], ["Date", "Amount"]]
        assert core.find_layout(rows, self._detect, 3) == (2, {"day": 0, "amount": 1})
        assert core.find_layout(rows, self._detect, 2) is None

    def test_the_first_accepted_row_wins(self):
        rows = [["Date", "Amount"], ["Amount", "Date"]]
        assert core.find_layout(rows, self._detect, 5) == (0, {"day": 0, "amount": 1})

    def test_no_header_is_none(self):
        assert core.find_layout([["a", "b"], ["c", "d"]], self._detect, 5) is None

    def test_no_rows_is_none(self):
        assert core.find_layout([], self._detect, 5) is None

    def test_detect_receives_each_row_in_order(self):
        seen: List[Sequence[object]] = []

        def detect(row: Sequence[object]) -> Optional[Dict[str, int]]:
            seen.append(row)
            return None

        rows = [["r0"], ["r1"], ["r2"], ["r3"]]
        assert core.find_layout(rows, detect, 3) is None
        assert seen == rows[:3]


def _write_xlsx(path: Path, sheets: Iterable[tuple[str, Sequence[Sequence[object]]]]) -> Path:
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    for title, rows in sheets:
        sheet = workbook.create_sheet(title)
        for row in rows:
            sheet.append(list(row))
    workbook.save(path)
    workbook.close()
    return path


class TestXlsxRows:
    def test_rows_from_row_one(self, tmp_path):
        path = _write_xlsx(tmp_path / "one.xlsx", [("Data", [["Date", "Amount"], [datetime(2026, 3, 2), 12.5], ["x", None]])])
        assert core.xlsx_rows(path) == [["Date", "Amount"], [datetime(2026, 3, 2), 12.5], ["x", None]]

    def test_limit_stops_early(self, tmp_path):
        path = _write_xlsx(tmp_path / "limit.xlsx", [("Data", [[n, n * 2] for n in range(1, 8)])])
        assert core.xlsx_rows(path, limit=3) == [[1, 2], [2, 4], [3, 6]]

    def test_limit_larger_than_the_sheet_returns_every_row(self, tmp_path):
        path = _write_xlsx(tmp_path / "short.xlsx", [("Data", [["a"], ["b"]])])
        assert core.xlsx_rows(path, limit=50) == [["a"], ["b"]]

    def test_empty_first_sheet_is_skipped(self, tmp_path):
        path = _write_xlsx(tmp_path / "skip.xlsx", [("Empty", []), ("Data", [["Date"], ["2026-03-02"]])])
        assert core.xlsx_rows(path) == [["Date"], ["2026-03-02"]]

    def test_first_sheet_with_data_wins_over_later_ones(self, tmp_path):
        path = _write_xlsx(tmp_path / "first.xlsx", [("Empty", []), ("First", [["one"]]), ("Second", [["two"]])])
        assert core.xlsx_rows(path) == [["one"]]

    def test_no_data_anywhere_is_empty(self, tmp_path):
        path = _write_xlsx(tmp_path / "blank.xlsx", [("A", []), ("B", [])])
        assert core.xlsx_rows(path) == []


class TestCsvRows:
    @staticmethod
    def _write(path: Path, text: str, encoding: str = "utf-8") -> Path:
        path.write_bytes(text.encode(encoding))
        return path

    def test_semicolon_is_the_default(self, tmp_path):
        path = self._write(tmp_path / "semi.csv", "date;amount;label\n2026-03-02;1,5;rent\n")
        assert core.csv_rows(path) == [["date", "amount", "label"], ["2026-03-02", "1,5", "rent"]]

    def test_comma_delimiter(self, tmp_path):
        path = self._write(tmp_path / "comma.csv", "date,amount,label\n2026-03-02,1.5,rent\n")
        assert core.csv_rows(path, delimiter=",") == [["date", "amount", "label"], ["2026-03-02", "1.5", "rent"]]

    def test_the_other_delimiter_does_not_split(self, tmp_path):
        path = self._write(tmp_path / "wrong.csv", "a,b;c\n")
        assert core.csv_rows(path, delimiter=";") == [["a,b", "c"]]
        assert core.csv_rows(path, delimiter=",") == [["a", "b;c"]]

    def test_quoted_field_keeps_its_delimiter(self, tmp_path):
        path = self._write(tmp_path / "quoted.csv", 'a;"x;y";z\n')
        assert core.csv_rows(path) == [["a", "x;y", "z"]]

    def test_crlf_line_endings(self, tmp_path):
        path = self._write(tmp_path / "crlf.csv", "a;b\r\nc;d\r\n")
        assert core.csv_rows(path) == [["a", "b"], ["c", "d"]]

    def test_non_utf8_export_is_decoded_by_the_base_class_chain(self, tmp_path):
        path = self._write(tmp_path / "cp1252.csv", "label;amount\nCafé €;1\n", encoding="cp1252")
        assert core.csv_rows(path) == [["label", "amount"], ["Café €", "1"]]

    def test_empty_file_has_no_rows(self, tmp_path):
        path = self._write(tmp_path / "empty.csv", "")
        assert core.csv_rows(path) == []

    def test_rows_are_lists_of_strings(self, tmp_path):
        path = self._write(tmp_path / "types.csv", "1;2\n")
        rows = core.csv_rows(path)
        assert rows == [["1", "2"]]
        assert isinstance(rows[0], list)


# =============================================================================
# C. RULE M: SEVERAL FILES OF ONE ROLE
# =============================================================================


@dataclass(frozen=True)
class _Row:
    day: Optional[date]
    signature: str
    tag: str = ""  # which file the row came from (part of equality, so identity checks on lists are meaningful)


def _day_of(row: _Row) -> Optional[date]:
    return row.day


def _file(tag: str, offsets: Iterable[int], override: Optional[Dict[int, str]] = None) -> List[_Row]:
    """One row per day offset, signature ``s<offset>`` unless overridden."""
    override = override or {}
    return [_Row(day(n), override.get(n, f"s{n}"), tag) for n in offsets]


class TestCoverageByDaySameRows:
    def test_coverage_is_first_and_last_dated_day(self):
        rows = [_Row(day(3), "a"), _Row(day(1), "b"), _Row(None, "c"), _Row(day(5), "d")]
        assert core.coverage(rows, _day_of) == (day(1), day(5))

    def test_coverage_none_when_nothing_is_dated(self):
        assert core.coverage([_Row(None, "a")], _day_of) is None
        assert core.coverage([], _day_of) is None

    def test_coverage_accepts_a_generator(self):
        assert core.coverage((_Row(day(n), "x") for n in (2, 4)), _day_of) == (day(2), day(4))

    def test_by_day_groups_in_file_order_and_drops_undated(self):
        first, second, third, undated = _Row(day(2), "a"), _Row(day(1), "b"), _Row(day(2), "c"), _Row(None, "d")
        groups = core.by_day([first, second, undated, third], _day_of)
        assert groups == {day(2): [first, third], day(1): [second]}

    def test_same_rows_is_a_multiset(self):
        assert core.same_rows([_Row(day(1), "a"), _Row(day(1), "a"), _Row(day(1), "b")], [_Row(day(1), "b"), _Row(day(1), "a"), _Row(day(1), "a")])

    def test_same_rows_counts_copies(self):
        assert not core.same_rows([_Row(day(1), "a"), _Row(day(1), "a")], [_Row(day(1), "a")])

    def test_same_rows_ignores_everything_but_the_signature(self):
        assert core.same_rows([_Row(day(1), "a", "A")], [_Row(day(9), "a", "B")])

    def test_same_rows_different_signature(self):
        assert not core.same_rows([_Row(day(1), "a")], [_Row(day(1), "b")])

    def test_same_rows_two_empty_groups(self):
        assert core.same_rows([], [])


class TestRoleMerge:
    def test_identical_files_keep_one_copy(self):
        a, b = _file("A", [1, 2]), _file("B", [1, 2])
        merge = RoleMerge([a, b], _day_of)
        assert merge.kept == b
        assert merge.superseded == []
        assert merge.mismatch_days == []

    def test_identical_files_tie_goes_to_the_later_one_in_the_list(self):
        a, b = _file("A", [1, 2]), _file("B", [1, 2])
        merge = RoleMerge([b, a], _day_of)
        assert merge.kept == a
        assert merge.superseded == []

    def test_one_file_alone_keeps_everything(self):
        a = _file("A", [1, 2, 3])
        merge = RoleMerge([a], _day_of)
        assert merge.kept == a
        assert merge.superseded == []
        assert merge.mismatch_days == []

    def test_no_files(self):
        merge = RoleMerge([], _day_of)
        assert merge.kept == []
        assert merge.superseded == []
        assert merge.mismatch_days == []

    def test_file_inside_another_keeps_the_outer_one_on_shared_days(self):
        outer, inner = _file("A", [1, 2, 3, 4, 5]), _file("B", [2, 3])
        for files in ([outer, inner], [inner, outer]):
            merge = RoleMerge(files, _day_of)
            assert merge.kept == outer
            assert merge.superseded == []
            assert merge.mismatch_days == []

    def test_later_ending_file_owns_an_overlapping_day(self):
        a, b = _file("A", [1, 2, 3]), _file("B", [3, 4, 5])
        merge = RoleMerge([a, b], _day_of)
        assert merge.kept == a[:2] + b
        assert merge.superseded == []
        assert merge.mismatch_days == []

    def test_three_files_chain(self):
        a, b, c = _file("A", [1, 2, 3]), _file("B", [3, 4, 5]), _file("C", [5, 6, 7])
        merge = RoleMerge([c, a, b], _day_of)
        assert sorted(row.signature for row in merge.kept) == sorted(f"s{n}" for n in (1, 2, 3, 4, 5, 6, 7))
        by_signature = {row.signature: row.tag for row in merge.kept}
        assert by_signature["s3"] == "B"
        assert by_signature["s5"] == "C"
        assert by_signature["s1"] == "A"
        assert merge.superseded == []

    def test_contradicting_day_is_a_mismatch_and_the_loser_is_superseded(self):
        a, b = _file("A", [1, 2, 3]), _file("B", [3, 4, 5], {3: "other"})
        merge = RoleMerge([a, b], _day_of)
        assert merge.mismatch_days == [day(3)]
        assert merge.superseded == [a[2]]
        assert merge.kept == a[:2] + b
        assert a[2] not in merge.kept

    def test_file_cut_mid_day_by_a_later_file_with_more_rows_that_day(self):
        earlier = _file("A", [1, 2, 3])
        later = [_Row(day(3), "s3", "B"), _Row(day(3), "s3-extra", "B"), *_file("B", [4, 5])]
        merge = RoleMerge([earlier, later], _day_of)
        assert merge.mismatch_days == [day(3)]
        assert merge.superseded == [earlier[2]]
        assert merge.kept == earlier[:2] + later

    def test_earlier_ending_file_with_more_rows_loses_them_and_it_is_reported(self):
        earlier = [*_file("A", [1, 2]), _Row(day(3), "s3", "A"), _Row(day(3), "s3-extra", "A")]
        later = _file("B", [3, 4, 5])
        merge = RoleMerge([earlier, later], _day_of)
        assert merge.mismatch_days == [day(3)]
        assert merge.superseded == earlier[2:]
        assert merge.kept == earlier[:2] + later

    def test_a_day_the_owner_has_no_rows_for_is_a_mismatch(self):
        # The longer file is silent on days 2 and 4, the shorter one has rows there: they contradict.
        outer = _file("A", [1, 5])
        inner = _file("B", [2, 4])
        merge = RoleMerge([outer, inner], _day_of)
        assert merge.kept == outer
        assert merge.superseded == inner
        assert merge.mismatch_days == [day(2), day(4)]

    def test_mismatch_days_are_sorted_and_unique(self):
        a = _file("A", [1, 2, 3, 4], {2: "x", 4: "y"})
        b = _file("B", [2, 3, 4, 5], {2: "p", 4: "q"})
        c = _file("C", [4, 5, 6], {4: "r"})
        merge = RoleMerge([c, a, b], _day_of)
        assert merge.mismatch_days == sorted(set(merge.mismatch_days))
        assert merge.mismatch_days == [day(2), day(4)]

    def test_undated_row_is_kept(self):
        undated = _Row(None, "note", "A")
        a = [undated, *_file("A", [1])]
        b = _file("B", [1])
        merge = RoleMerge([a, b], _day_of)
        assert undated in merge.kept
        assert merge.kept == [undated, *b]
        assert merge.superseded == []

    def test_file_with_no_dated_row_keeps_its_rows(self):
        only_undated = [_Row(None, "n1", "A"), _Row(None, "n2", "A")]
        dated = _file("B", [1, 2])
        merge = RoleMerge([only_undated, dated], _day_of)
        assert merge.spans == [None, (day(1), day(2))]
        assert merge.kept == only_undated + dated
        assert merge.superseded == []
        assert merge.mismatch_days == []

    def test_spans_are_the_coverage_of_each_file(self):
        merge = RoleMerge([_file("A", [3, 1]), _file("B", [5])], _day_of)
        assert merge.spans == [(day(1), day(3)), (day(5), day(5))]

    def test_disjoint_files_keep_everything(self):
        a, b = _file("A", [1, 2]), _file("B", [4, 5])
        merge = RoleMerge([b, a], _day_of)
        assert merge.kept == b + a
        assert merge.superseded == []
        assert merge.mismatch_days == []


class TestContainedRows:
    def test_a_subset_is_contained(self):
        assert core.contained_rows([_Row(day(1), "a")], [_Row(day(1), "a"), _Row(day(1), "b")])

    def test_the_same_rows_are_contained(self):
        assert core.contained_rows([_Row(day(1), "a"), _Row(day(1), "b")], [_Row(day(1), "b"), _Row(day(1), "a")])

    def test_an_empty_group_is_part_of_any(self):
        assert core.contained_rows([], [_Row(day(1), "a")])
        assert core.contained_rows([], [])

    def test_a_row_the_outer_lacks_is_not_contained(self):
        assert not core.contained_rows([_Row(day(1), "a"), _Row(day(1), "z")], [_Row(day(1), "a"), _Row(day(1), "b")])

    def test_something_in_nothing_is_not_contained(self):
        assert not core.contained_rows([_Row(day(1), "a")], [])

    def test_a_signature_counts_as_often_as_it_appears(self):
        once, twice = [_Row(day(1), "a")], [_Row(day(1), "a"), _Row(day(1), "a")]
        assert core.contained_rows(once, twice)
        assert not core.contained_rows(twice, once)

    def test_only_the_signature_matters(self):
        assert core.contained_rows([_Row(day(1), "a", "A")], [_Row(day(9), "a", "B")])


class TestRoleMergePolicies:
    """``owner`` and ``contradiction``: the two knobs a bank that only ever cuts an export short (Crédit Agricole) turns."""

    def test_an_unknown_owner_policy_raises(self):
        with pytest.raises(ValueError, match="unknown rule M policy"):
            RoleMerge([_file("A", [1])], _day_of, owner="oldest")

    def test_an_unknown_contradiction_policy_raises(self):
        with pytest.raises(ValueError, match="unknown rule M policy"):
            RoleMerge([_file("A", [1])], _day_of, contradiction="never")

    def test_the_defaults_are_the_ones_danske_uses(self):
        a = [_Row(day(1), "a", "A"), _Row(day(1), "b", "A"), _Row(day(2), "c", "A")]
        b = [_Row(day(1), "a", "B"), _Row(day(3), "d", "B")]
        default, explicit = RoleMerge([a, b], _day_of), RoleMerge([a, b], _day_of, owner="latest", contradiction="differs")
        assert (default.kept, default.superseded, default.mismatch_days) == (explicit.kept, explicit.superseded, explicit.mismatch_days)
        # The file that ends last owns every day it covers, however few rows it has there.
        assert default.kept == b
        assert default.superseded == a

    def test_most_rows_gives_the_day_to_the_bigger_file_even_when_it_ends_earlier(self):
        a = [_Row(day(1), "a", "A"), _Row(day(1), "b", "A"), _Row(day(2), "c", "A")]
        b = [_Row(day(1), "a", "B"), _Row(day(3), "d", "B")]
        merge = RoleMerge([a, b], _day_of, owner="most_rows", contradiction="not_contained")
        assert merge.kept == [*a, b[1]]
        assert merge.superseded == [b[0]]
        assert merge.mismatch_days == []

    @pytest.mark.parametrize("order", [(0, 1), (1, 0)])
    def test_most_rows_does_not_depend_on_the_order_of_the_files(self, order):
        a = [_Row(day(1), "a", "A"), _Row(day(1), "b", "A"), _Row(day(2), "c", "A")]
        b = [_Row(day(1), "a", "B"), _Row(day(3), "d", "B")]
        files = [[a, b][index] for index in order]
        merge = RoleMerge(files, _day_of, owner="most_rows", contradiction="not_contained")
        assert sorted(row.signature for row in merge.kept) == ["a", "b", "c", "d"]
        assert {row.tag for row in merge.kept if row.signature == "a"} == {"A"}
        assert merge.superseded == [b[0]]

    def test_a_tie_goes_to_the_file_that_ends_last(self):
        a = [_Row(day(1), "a", "A"), _Row(day(2), "b", "A")]
        b = [_Row(day(1), "x", "B"), _Row(day(3), "y", "B")]
        merge = RoleMerge([a, b], _day_of, owner="most_rows", contradiction="not_contained")
        assert b[0] in merge.kept
        assert a[0] in merge.superseded
        # Day 2 is inside B's span but B has no row there: A has one, so A keeps it.
        assert a[1] in merge.kept

    def test_a_tie_between_files_with_the_same_span_goes_to_the_later_one_in_the_list(self):
        a, b = [_Row(day(1), "a", "A"), _Row(day(2), "p", "A")], [_Row(day(1), "x", "B"), _Row(day(2), "q", "B")]
        for files, owner_tag in (([a, b], "B"), ([b, a], "A")):
            merge = RoleMerge(files, _day_of, owner="most_rows", contradiction="not_contained")
            assert {row.tag for row in merge.kept} == {owner_tag}

    def test_the_default_contradiction_calls_a_subset_a_mismatch(self):
        a = [_Row(day(1), "a", "A"), _Row(day(1), "b", "A"), _Row(day(1), "c", "A")]
        b = [_Row(day(1), "a", "B"), _Row(day(2), "d", "B")]
        merge = RoleMerge([a, b], _day_of, owner="most_rows")
        assert merge.mismatch_days == [day(1)]
        assert merge.superseded == [b[0]]

    def test_not_contained_does_not_call_a_subset_a_mismatch(self):
        a = [_Row(day(1), "a", "A"), _Row(day(1), "b", "A"), _Row(day(1), "c", "A")]
        b = [_Row(day(1), "a", "B"), _Row(day(2), "d", "B")]
        merge = RoleMerge([a, b], _day_of, owner="most_rows", contradiction="not_contained")
        assert merge.mismatch_days == []
        # The subset still loses the day: its row is not counted twice.
        assert merge.superseded == [b[0]]
        assert merge.kept == [*a, b[1]]

    def test_not_contained_calls_a_row_the_owner_lacks_a_mismatch_when_the_owner_is_bigger(self):
        a = [_Row(day(1), "a", "A"), _Row(day(1), "b", "A"), _Row(day(1), "c", "A")]
        b = [_Row(day(1), "a", "B"), _Row(day(1), "z", "B"), _Row(day(2), "d", "B")]
        merge = RoleMerge([a, b], _day_of, owner="most_rows", contradiction="not_contained")
        assert merge.mismatch_days == [day(1)]
        assert merge.superseded == b[:2]

    def test_not_contained_calls_a_row_the_owner_lacks_a_mismatch_on_a_tie(self):
        a = [_Row(day(1), "a", "A"), _Row(day(1), "b", "A")]
        b = [_Row(day(1), "a", "B"), _Row(day(1), "z", "B"), _Row(day(2), "d", "B")]
        merge = RoleMerge([a, b], _day_of, owner="most_rows", contradiction="not_contained")
        assert merge.mismatch_days == [day(1)]
        assert merge.superseded == a

    def test_not_contained_counts_copies(self):
        # Two identical rows in the owner stay two; a file with the row once is a subset of it.
        owner = [_Row(day(1), "x", "A"), _Row(day(1), "x", "A")]
        cut = [_Row(day(1), "x", "B"), _Row(day(2), "y", "B")]
        merge = RoleMerge([owner, cut], _day_of, owner="most_rows", contradiction="not_contained")
        assert merge.mismatch_days == []
        assert [row for row in merge.kept if row.signature == "x"] == owner
        # The other way round it is not: a file that holds a signature more often than the owner contradicts it.
        twice = [_Row(day(1), "x", "C"), _Row(day(1), "y", "C")]
        owner_b = [_Row(day(1), "x", "D"), _Row(day(1), "z", "D"), _Row(day(2), "w", "D")]
        merge = RoleMerge([twice, owner_b], _day_of, owner="most_rows", contradiction="not_contained")
        assert merge.mismatch_days == [day(1)]

    def test_identical_downloads_count_once_under_every_policy(self):
        a, b = _file("A", [1, 2, 3]), _file("B", [1, 2, 3])
        for owner in ("latest", "most_rows"):
            for contradiction in ("differs", "not_contained"):
                merge = RoleMerge([a, b], _day_of, owner=owner, contradiction=contradiction)
                assert merge.kept == b
                assert merge.superseded == []
                assert merge.mismatch_days == []

    def test_a_single_file_keeps_everything_under_the_ca_policy(self):
        a = _file("A", [1, 1, 2])
        merge = RoleMerge([a], _day_of, owner="most_rows", contradiction="not_contained")
        assert merge.kept == a
        assert merge.superseded == []

    def test_undated_rows_and_empty_files_under_the_ca_policy(self):
        undated = [_Row(None, "n", "A")]
        merge = RoleMerge([undated, [], _file("B", [1])], _day_of, owner="most_rows", contradiction="not_contained")
        assert merge.kept == [*undated, *_file("B", [1])]
        assert merge.superseded == []
        assert merge.mismatch_days == []

    def test_a_day_the_bigger_file_does_not_cover_stays_with_the_other(self):
        a = _file("A", [1, 2])
        b = _file("B", [4, 5])
        merge = RoleMerge([a, b], _day_of, owner="most_rows", contradiction="not_contained")
        assert merge.kept == a + b
        assert merge.superseded == []


# =============================================================================
# D. PAIRING: ONE TO ONE, NEVER A GUESS
# =============================================================================


@dataclass(frozen=True)
class _Left:
    name: str
    outcome: str
    key: str = "k"


@dataclass(frozen=True)
class _Right:
    label: str
    key: str = "k"


def _same_name(left: _Left, right: _Right) -> bool:
    return left.name == right.label


def _outcome(left: _Left) -> str:
    return left.outcome


def _label(right: _Right) -> str:
    return right.label


def _assign(left: List[_Left], right: List[_Right], max_candidates: int = 4, same_name=_same_name):
    return core.assign(left, right, max_candidates=max_candidates, same_name=same_name, outcome_of=_outcome, label_of=_label)


def _never(_left: _Left, _right: _Right) -> bool:
    return False


class TestAssign:
    def test_one_against_one_is_a_pair_whatever_the_names(self):
        left, right = _Left("a", "o1"), _Right("zzz")
        assert _assign([left], [right]) == [(left, right)]

    def test_one_against_one_even_above_a_zero_cap(self):
        left, right = _Left("a", "o1"), _Right("b")
        assert _assign([left], [right], max_candidates=0) == [(left, right)]

    def test_indistinguishable_twins_are_paired_in_order(self):
        l1, l2 = _Left("x", "same"), _Left("y", "same")
        r1, r2 = _Right("ACME"), _Right(" acme ")
        assert _assign([l1, l2], [r1, r2], same_name=_never) == [(l1, r1), (l2, r2)]

    def test_twins_on_the_left_and_one_partner_pair_the_first(self):
        l1, l2 = _Left("x", "same"), _Left("y", "same")
        right = _Right("ACME")
        assert _assign([l1, l2], [right], same_name=_never) == [(l1, right)]

    def test_two_candidates_with_different_outcomes_and_equal_weight_are_ambiguous(self):
        l1, l2 = _Left("a", "o1"), _Left("b", "o2")
        assert _assign([l1, l2], [_Right("c")]) is None

    def test_name_weight_breaks_the_tie(self):
        l1, l2 = _Left("a", "o1"), _Left("b", "o2")
        right = _Right("b")
        assert _assign([l1, l2], [right]) == [(l2, right)]

    def test_name_weight_crosses_the_pairs(self):
        la, lb = _Left("a", "o1"), _Left("b", "o2")
        rb, ra = _Right("b"), _Right("a")
        assert _assign([la, lb], [rb, ra]) == [(la, ra), (lb, rb)]

    def test_equal_outcomes_with_distinct_labels_are_not_an_ambiguity(self):
        l1, l2 = _Left("p", "same"), _Left("q", "same")
        r1, r2 = _Right("c"), _Right("d")
        # The twins import the same thing, so which one gets which partner changes nothing: the first assignment wins.
        assert _assign([l1, l2], [r1, r2]) == [(l1, r1), (l2, r2)]

    def test_above_max_candidates_nothing_is_tried(self):
        lefts = [_Left("x", "same") for _ in range(3)]
        rights = [_Right("acme") for _ in range(3)]
        assert _assign(lefts, rights, max_candidates=2) is None

    def test_at_max_candidates_it_is_still_tried(self):
        lefts = [_Left("x", "same") for _ in range(3)]
        rights = [_Right("acme") for _ in range(3)]
        assert _assign(lefts, rights, max_candidates=3) == list(zip(lefts, rights, strict=True))

    def test_the_cap_counts_either_side(self):
        lefts = [_Left("x", "same")]
        rights = [_Right("acme") for _ in range(3)]
        assert _assign(lefts, rights, max_candidates=2) is None


class TestBestAssignment:
    def test_most_compatible_names_win(self):
        la, lb = _Left("a", "o1"), _Left("b", "o2")
        rb, ra = _Right("b"), _Right("a")
        assert core.best_assignment([la, lb], [rb, ra], same_name=_same_name, outcome_of=_outcome) == [(la, ra), (lb, rb)]

    def test_different_outcomes_at_the_best_weight_are_ambiguous(self):
        l1, l2 = _Left("a", "o1"), _Left("b", "o2")
        assert core.best_assignment([l1, l2], [_Right("c")], same_name=_never, outcome_of=_outcome) is None

    def test_a_clear_winner_among_more_left_rows_than_right(self):
        l1, l2, l3 = _Left("a", "o1"), _Left("b", "o2"), _Left("c", "o3")
        assert core.best_assignment([l1, l2, l3], [_Right("c")], same_name=_same_name, outcome_of=_outcome) == [(l3, _Right("c"))]

    def test_same_outcomes_everywhere_returns_the_first_assignment(self):
        l1, l2 = _Left("a", "same"), _Left("b", "same")
        r1, r2 = _Right("c"), _Right("d")
        assert core.best_assignment([l1, l2], [r1, r2], same_name=_never, outcome_of=_outcome) == [(l1, r1), (l2, r2)]

    def test_more_right_rows_than_left_uses_every_left_row(self):
        la, lb = _Left("a", "o1"), _Left("b", "o2")
        r1, ra, rb = _Right("x"), _Right("a"), _Right("b")
        assert core.best_assignment([la, lb], [r1, ra, rb], same_name=_same_name, outcome_of=_outcome) == [(la, ra), (lb, rb)]


def _by_key(left: _Left, right: _Right):
    """What a pair imports when the right row decides it (a plugin that reads an asset or a withholding from it)."""
    return (left.outcome, right.key)


class TestPairOutcome:
    """``pair_outcome_of``: the outcome of a pair, not of its left row alone."""

    def test_partners_that_differ_for_one_left_row_are_ambiguous(self):
        left = _Left("a", "o1")
        r1, r2 = _Right("x", "k1"), _Right("y", "k2")
        # Without it, which partner the lone left row gets changes nothing it imports: the first one is taken.
        assert core.best_assignment([left], [r1, r2], same_name=_never, outcome_of=_outcome) == [(left, r1)]
        assert core.best_assignment([left], [r1, r2], same_name=_never, outcome_of=_outcome, pair_outcome_of=_by_key) is None

    def test_interchangeable_partners_are_a_pair(self):
        left = _Left("a", "o1")
        r1, r2 = _Right("x", "same"), _Right("y", "same")
        assert core.best_assignment([left], [r1, r2], same_name=_never, outcome_of=_outcome, pair_outcome_of=_by_key) == [(left, r1)]

    def test_a_compatible_name_breaks_the_tie_between_partners(self):
        left = _Left("a", "o1")
        r1, r2 = _Right("a", "k1"), _Right("b", "k2")
        assert core.best_assignment([left], [r1, r2], same_name=_same_name, outcome_of=_outcome, pair_outcome_of=_by_key) == [(left, r1)]

    def test_twins_on_the_left_are_interchangeable_whoever_their_partners_are(self):
        l1, l2 = _Left("x", "same"), _Left("y", "same")
        r1, r2 = _Right("c", "k1"), _Right("d", "k2")
        assert core.best_assignment([l1, l2], [r1, r2], same_name=_never, outcome_of=_outcome, pair_outcome_of=_by_key) == [(l1, r1), (l2, r2)]

    def test_different_left_rows_with_different_partners_are_ambiguous(self):
        l1, l2 = _Left("x", "o1"), _Left("y", "o2")
        r1, r2 = _Right("c", "k1"), _Right("d", "k2")
        assert core.best_assignment([l1, l2], [r1, r2], same_name=_never, outcome_of=_outcome, pair_outcome_of=_by_key) is None

    def test_different_left_rows_with_interchangeable_partners_are_a_pair(self):
        l1, l2 = _Left("x", "o1"), _Left("y", "o2")
        r1, r2 = _Right("c", "k"), _Right("d", "k")
        assert core.best_assignment([l1, l2], [r1, r2], same_name=_never, outcome_of=_outcome, pair_outcome_of=_by_key) == [(l1, r1), (l2, r2)]

    def test_assign_skips_the_twins_shortcut(self):
        left = _Left("a", "o1")
        r1, r2 = _Right("acme", "k1"), _Right("acme", "k2")
        # Same label on the right and a single outcome on the left: the shortcut pairs them without looking further...
        assert core.assign([left], [r1, r2], max_candidates=4, same_name=_never, outcome_of=_outcome, label_of=_label) == [(left, r1)]
        # ...but when the right row decides what is imported the partners are not twins, whatever their label says.
        assert core.assign([left], [r1, r2], max_candidates=4, same_name=_never, outcome_of=_outcome, label_of=_label, pair_outcome_of=_by_key) is None

    def test_assign_pairs_twins_with_the_same_partner_outcome(self):
        l1, l2 = _Left("x", "same"), _Left("y", "same")
        r1, r2 = _Right("acme", "k"), _Right("acme", "k")
        assert core.assign([l1, l2], [r1, r2], max_candidates=4, same_name=_never, outcome_of=_outcome, label_of=_label, pair_outcome_of=_by_key) == [(l1, r1), (l2, r2)]

    def test_assign_compares_the_assignments_by_what_each_pair_imports(self):
        calls: List[tuple] = []

        def spy(left: _Left, right: _Right):
            calls.append((left.name, right.label))
            return _by_key(left, right)

        l1, l2 = _Left("x", "same"), _Left("y", "same")
        r1, r2 = _Right("acme", "k"), _Right("acme", "k")
        core.assign([l1, l2], [r1, r2], max_candidates=4, same_name=_never, outcome_of=_outcome, label_of=_label, pair_outcome_of=spy)
        assert calls  # consulted: the shortcut for twins was not taken

    def test_one_against_one_is_still_a_pair_without_asking(self):
        def never_called(_left: _Left, _right: _Right):
            raise AssertionError("a lone pair needs no comparison")

        left, right = _Left("a", "o1"), _Right("zzz", "k")
        assert core.assign([left], [right], max_candidates=4, same_name=_never, outcome_of=_outcome, label_of=_label, pair_outcome_of=never_called) == [(left, right)]

    def test_above_max_candidates_nothing_is_tried(self):
        lefts = [_Left("x", "same") for _ in range(3)]
        rights = [_Right("acme", "k") for _ in range(3)]
        assert core.assign(lefts, rights, max_candidates=2, same_name=_never, outcome_of=_outcome, label_of=_label, pair_outcome_of=_by_key) is None

    def test_pair_by_key_lists_the_rows_of_a_group_whose_partners_differ(self):
        left = _Left("a", "o1", "k1")
        r1, r2 = _Right("x", "k1"), _Right("y", "k1")
        # Both partners sit on the same pairing key; they differ in what they would import (the extra field ``label``).
        pairs, ambiguous = core.pair_by_key(
            [left],
            [r1, r2],
            left_key=lambda row: row.key,
            right_key=lambda row: row.key,
            assign_group=lambda lg, rg: core.assign(lg, rg, max_candidates=4, same_name=_never, outcome_of=_outcome, label_of=_label, pair_outcome_of=lambda a, b: (a.outcome, b.label)),
        )
        assert pairs == []
        assert ambiguous == [left, r1, r2]


def _group_pairer(left_group: List[_Left], right_group: List[_Right]):
    return _assign(left_group, right_group)


class TestPairByKey:
    def _pair(self, lefts, rights, assign_group=_group_pairer):
        return core.pair_by_key(lefts, rights, left_key=lambda row: row.key, right_key=lambda row: row.key, assign_group=assign_group)

    def test_one_to_one_per_key(self):
        la, lb = _Left("a", "o1", "k1"), _Left("b", "o2", "k2")
        ra, rb = _Right("a", "k1"), _Right("b", "k2")
        pairs, ambiguous = self._pair([la, lb], [ra, rb])
        assert pairs == [(la, ra), (lb, rb)]
        assert ambiguous == []

    def test_pairs_follow_the_sorted_keys_not_the_input_order(self):
        lb, la = _Left("b", "o2", "kb"), _Left("a", "o1", "ka")
        rb, ra = _Right("b", "kb"), _Right("a", "ka")
        pairs, _ = self._pair([lb, la], [rb, ra])
        assert pairs == [(la, ra), (lb, rb)]
        again, _ = self._pair([la, lb], [ra, rb])
        assert again == pairs

    def test_an_ambiguous_key_lists_its_rows_left_then_right(self):
        l1, l2 = _Left("a", "o1", "k1"), _Left("b", "o2", "k1")
        r1 = _Right("c", "k1")
        pairs, ambiguous = self._pair([l1, l2], [r1])
        assert pairs == []
        assert ambiguous == [l1, l2, r1]

    def test_an_ambiguous_key_does_not_block_the_others(self):
        l1, l2 = _Left("a", "o1", "k1"), _Left("b", "o2", "k1")
        r1 = _Right("c", "k1")
        la, ra = _Left("z", "o9", "k2"), _Right("z", "k2")
        pairs, ambiguous = self._pair([l1, l2, la], [r1, ra])
        assert pairs == [(la, ra)]
        assert ambiguous == [l1, l2, r1]

    def test_a_key_on_one_side_only_pairs_nothing_and_is_not_ambiguous(self):
        left_only = _Left("a", "o1", "k1")
        right_only = _Right("b", "k2")
        pairs, ambiguous = self._pair([left_only], [right_only])
        assert pairs == []
        assert ambiguous == []

    def test_a_key_on_one_side_only_never_reaches_assign_group(self):
        calls: List[object] = []

        def spy(left_group, right_group):
            calls.append((left_group, right_group))
            return None

        self._pair([_Left("a", "o1", "k1")], [_Right("b", "k2")], assign_group=spy)
        assert calls == []

    def test_assign_group_receives_the_whole_group_of_a_key(self):
        seen: List[tuple] = []

        def spy(left_group, right_group):
            seen.append((list(left_group), list(right_group)))
            return []

        l1, l2 = _Left("a", "o1", "k1"), _Left("b", "o2", "k1")
        r1 = _Right("c", "k1")
        self._pair([l1, l2], [r1], assign_group=spy)
        assert seen == [([l1, l2], [r1])]

    def test_accepts_generators(self):
        la, ra = _Left("a", "o1", "k1"), _Right("a", "k1")
        pairs, ambiguous = self._pair((row for row in [la]), (row for row in [ra]))
        assert pairs == [(la, ra)]
        assert ambiguous == []

    def test_no_rows(self):
        assert self._pair([], []) == ([], [])


# =============================================================================
# E. SEGMENTS AND ZONES
# =============================================================================


class TestMergeSpans:
    def test_touching_next_day_merges(self):
        assert core.merge_spans([(day(1), day(3)), (day(4), day(6))]) == [(day(1), day(6))]

    def test_a_one_day_gap_does_not_merge(self):
        assert core.merge_spans([(day(1), day(3)), (day(5), day(6))]) == [(day(1), day(3)), (day(5), day(6))]

    def test_overlap_merges(self):
        assert core.merge_spans([(day(1), day(5)), (day(3), day(8))]) == [(day(1), day(8))]

    def test_a_span_inside_another_keeps_the_outer_end(self):
        assert core.merge_spans([(day(1), day(10)), (day(2), day(3))]) == [(day(1), day(10))]

    def test_unsorted_input(self):
        spans = [(day(10), day(12)), (day(1), day(3)), (day(4), day(5)), (day(20), day(21))]
        assert core.merge_spans(spans) == [(day(1), day(5)), (day(10), day(12)), (day(20), day(21))]

    def test_one_day_spans(self):
        assert core.merge_spans([(day(2), day(2)), (day(3), day(3))]) == [(day(2), day(3))]

    def test_empty(self):
        assert core.merge_spans([]) == []

    def test_accepts_a_generator(self):
        assert core.merge_spans(span for span in [(day(1), day(2))]) == [(day(1), day(2))]


class TestBuildTimeline:
    def test_opening_then_gap_kinds(self):
        timeline = core.build_timeline([(day(1), day(5)), (day(15), day(19)), (day(29), day(33))], 2)
        assert [segment.kind for segment in timeline] == ["opening", "gap", "gap"]

    def test_checkpoint_is_the_eve_of_the_start(self):
        timeline = core.build_timeline([(day(1), day(5)), (day(15), day(19))], 2)
        assert [segment.checkpoint for segment in timeline] == [day(0), day(14)]
        assert [segment.start for segment in timeline] == [day(1), day(15)]
        assert [segment.end for segment in timeline] == [day(5), day(19)]

    def test_window_end_is_the_end_plus_the_lag_in_business_days(self):
        timeline = core.build_timeline([(day(1), day(5)), (day(15), day(19))], 2)
        # Friday day(5) + 2 weekdays = Tuesday day(9); Friday day(19) + 2 weekdays = Tuesday day(23).
        assert timeline[0].window_end == day(9)
        assert timeline[1].window_end == day(23)

    def test_window_end_is_clamped_by_the_next_checkpoint(self):
        # The first segment ends on a Friday (day(12)); +2 weekdays is day(16), but the next checkpoint is day(14).
        timeline = core.build_timeline([(day(1), day(12)), (day(15), day(19))], 2)
        assert timeline[0].window_end == day(14)
        assert timeline[1].window_end == day(23)

    def test_the_last_segment_is_never_clamped(self):
        timeline = core.build_timeline([(day(1), day(5))], 3)
        # Friday + 3 weekdays: Monday, Tuesday, Wednesday.
        assert timeline[0].window_end == day(10)

    def test_lag_skips_the_weekend(self):
        timeline = core.build_timeline([(day(4), day(4))], 3)
        # Thursday + 3 weekdays: Friday, Monday, Tuesday.
        assert timeline[0].window_end == day(9)

    def test_border_end_is_the_checkpoint_plus_the_lag_in_business_days(self):
        timeline = core.build_timeline([(day(1), day(5)), (day(15), day(19))], 2)
        # Checkpoint Sunday day(0) + 2 weekdays = Tuesday day(2); checkpoint Saturday day(14) + 2 weekdays = Tuesday day(16).
        assert timeline[0].border_end == day(2)
        assert timeline[1].border_end == day(16)

    def test_zero_lag(self):
        timeline = core.build_timeline([(day(1), day(5)), (day(15), day(19))], 0)
        assert [segment.window_end for segment in timeline] == [day(5), day(19)]
        assert [segment.border_end for segment in timeline] == [day(0), day(14)]

    def test_no_segments(self):
        assert core.build_timeline([], 2) == []


class TestZone:
    @pytest.fixture
    def timeline(self) -> List[Segment]:
        return core.build_timeline([(day(1), day(5)), (day(15), day(19))], 2)

    def test_on_or_before_the_first_checkpoint_is_before(self, timeline):
        assert core.zone(timeline, day(0)) == ("before", 0)
        assert core.zone(timeline, day(-30)) == ("before", 0)

    def test_inside_a_segment_window(self, timeline):
        assert core.zone(timeline, day(1)) == ("window", 0)
        assert core.zone(timeline, day(3)) == ("window", 0)
        assert core.zone(timeline, day(16)) == ("window", 1)

    def test_the_settlement_tail_is_still_the_window(self, timeline):
        assert core.zone(timeline, timeline[0].window_end) == ("window", 0)
        assert core.zone(timeline, timeline[1].window_end) == ("window", 1)

    def test_between_windows_is_the_gap_before_the_next_segment(self, timeline):
        assert core.zone(timeline, timeline[0].window_end + timedelta(days=1)) == ("gap", 1)
        assert core.zone(timeline, timeline[1].checkpoint) == ("gap", 1)

    def test_the_next_checkpoint_day_is_the_last_gap_day(self, timeline):
        assert core.zone(timeline, day(14)) == ("gap", 1)
        assert core.zone(timeline, day(15)) == ("window", 1)

    def test_after_the_last_window(self, timeline):
        assert core.zone(timeline, timeline[1].window_end + timedelta(days=1)) == ("after", 1)
        assert core.zone(timeline, day(400)) == ("after", 1)

    def test_none_day(self, timeline):
        assert core.zone(timeline, None) == ("", -1)

    def test_empty_timeline(self):
        assert core.zone([], day(3)) == ("", -1)
        assert core.zone([], None) == ("", -1)

    def test_clamped_window_leaves_no_hole(self):
        timeline = core.build_timeline([(day(1), day(12)), (day(15), day(19))], 2)
        assert core.zone(timeline, day(14)) == ("window", 0)
        assert core.zone(timeline, day(15)) == ("window", 1)

    def test_single_segment_timeline(self):
        timeline = core.build_timeline([(day(1), day(5))], 2)
        assert core.zone(timeline, day(0)) == ("before", 0)
        assert core.zone(timeline, day(9)) == ("window", 0)
        assert core.zone(timeline, day(10)) == ("after", 0)


class TestSegmentZone:
    def test_opening_segment_is_before(self):
        assert Segment(start=day(1), end=day(2), checkpoint=day(0), kind="opening").zone == "before"

    def test_gap_segment_is_gap(self):
        assert Segment(start=day(1), end=day(2), checkpoint=day(0), kind="gap").zone == "gap"

    def test_built_segments_follow_their_kind(self):
        timeline = core.build_timeline([(day(1), day(2)), (day(8), day(9))], 1)
        assert [segment.zone for segment in timeline] == ["before", "gap"]

    def test_defaults(self):
        segment = Segment(start=day(1), end=day(2), checkpoint=day(0), kind="gap")
        assert segment.window_end == date.min
        assert segment.border_end == date.min
