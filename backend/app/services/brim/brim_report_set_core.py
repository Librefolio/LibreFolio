"""Shared building blocks of the report-set plugins (Danske Bank, Crédit Agricole).

A report-set plugin reads several exports of one bank (a custody/securities file and a cash
file, each possibly in several downloads) and combines them into one derived file. What every
such plugin needs, whatever the bank, lives here; what is bank-specific (the columns, the
classification of the rows, the pairing key, the truth points) stays in the plugin.

Contents:

- text and number helpers (``norm``, ``plain``, ``money``, ``source``, ``compatible``);
- spreadsheet and CSV readers and the header scan (``xlsx_rows``, ``csv_rows``, ``layout``, ``find_layout``);
- rule M, several files of one role (``RoleMerge`` and its ``coverage`` / ``by_day`` / ``same_rows``);
- one-to-one pairing without a guess (``assign``, ``best_assignment``, ``pair_by_key``);
- the segments of a timeline and the zone of a date (``merge_spans``, ``Segment``, ``build_timeline``, ``zone``).

Every function is pure and parameterised by what the bank changes (a delimiter, a day accessor,
a settlement lag, a candidate cap): the plugin passes its own constants.

Design: ``LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/design-phase00BrimReportSets.md``;
the extraction itself is step 1 of W5-7 (``plan-phase01ImportTransactions.prompt.md``).
"""

from __future__ import annotations

import csv
import re
import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from itertools import permutations
from pathlib import Path
from typing import Any, Callable, Dict, Hashable, Iterable, List, Optional, Sequence, Set, Tuple

import openpyxl

from backend.app.services.brim.brim_provider import BRIMProvider

CENT = Decimal("0.01")

_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_SPACES_RE = re.compile(r"\s+")


# =============================================================================
# TEXT, NUMBERS AND DATES
# =============================================================================


def norm(value: Any) -> str:
    """Case- and space-insensitive form of a header or a name (``<br/>`` counts as a space)."""
    if value is None:
        return ""
    return _SPACES_RE.sub(" ", _BR_RE.sub(" ", str(value))).strip().casefold()


def plain(value: Decimal) -> str:
    """A decimal in its shortest plain form (no exponent, no trailing zeros)."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def money(value: Decimal) -> str:
    """A decimal at two places, plain notation."""
    return format(value.quantize(CENT), "f")


def add_business_days(start: date, days: int) -> date:
    """``start`` plus ``days`` weekdays (holidays are not known and not skipped)."""
    current, added = start, 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def compatible(first: str, second: str) -> bool:
    """Two names of the same security: a statement truncates its labels, so one is a prefix of the other."""
    a, b = norm(first), norm(second)
    return bool(a) and bool(b) and (a.startswith(b) or b.startswith(a))


def source(role: str, file_index: int, file_count: int, row: int) -> str:
    """The ``lf_source`` text of a row: the role and the row, plus the file number when the role has several files."""
    return f"{role}:{row}" if file_count == 1 else f"{role}#{file_index}:{row}"


def match_key_text(day: Optional[date], amount: Optional[Decimal], currency: str) -> str:
    """The ``lf_match_key`` text of a paired row: ``<date>|<amount>|<currency>``, empty when the date or amount is missing."""
    if day is None or amount is None:
        return ""
    return f"{day.isoformat()}|{money(amount)}|{currency}"


# =============================================================================
# SOURCE FILES
# =============================================================================


def xlsx_rows(path: Path, limit: Optional[int] = None) -> List[List[Any]]:
    """Rows of the first worksheet with data, from row 1 (values only)."""
    with warnings.catch_warnings():
        # openpyxl warns about harmless things in bank exports (default styles, print areas).
        warnings.simplefilter("ignore")
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        for sheet in workbook.worksheets:
            rows = _sheet_rows(sheet, limit)
            if any(cell not in (None, "") for row in rows for cell in row):
                return rows
        return []
    finally:
        workbook.close()


def _sheet_rows(sheet: Any, limit: Optional[int]) -> List[List[Any]]:
    rows: List[List[Any]] = []
    for row in sheet.iter_rows(min_row=1, values_only=True):
        rows.append(list(row))
        if limit is not None and len(rows) >= limit:
            break
    return rows


def csv_rows(path: Path, delimiter: str = ";") -> List[List[str]]:
    """Every row of a delimited text file (encoding sniffed by the base class)."""
    with BRIMProvider._open_text(path, newline="") as handle:
        return [list(row) for row in csv.reader(handle, delimiter=delimiter)]


def layout(header: Sequence[Any], names: Dict[str, str], required: Set[str]) -> Optional[Dict[str, int]]:
    """Column index by canonical name, from a header row; ``None`` when a required column is missing.

    ``names`` maps the normalised header text (see ``norm``) to the canonical column name.
    """
    columns: Dict[str, int] = {}
    for index, cell in enumerate(header):
        name = names.get(norm(cell))
        if name is not None and name not in columns:
            columns[name] = index
    return columns if required <= columns.keys() else None


def find_layout(
    rows: Sequence[Sequence[Any]],
    detect: Callable[[Sequence[Any]], Optional[Dict[str, int]]],
    scan_rows: int,
) -> Optional[Tuple[int, Dict[str, int]]]:
    """The first of the top ``scan_rows`` rows that ``detect`` accepts as a header: ``(row index, columns)``."""
    for index, row in enumerate(rows[:scan_rows]):
        columns = detect(row)
        if columns is not None:
            return index, columns
    return None


# =============================================================================
# RULE M: SEVERAL FILES OF ONE ROLE
# =============================================================================


def coverage(rows: Iterable[Any], day_of: Callable[[Any], Optional[date]]) -> Optional[Tuple[date, date]]:
    """First and last day covered by the rows (``None`` when none is dated)."""
    days = [day for day in (day_of(row) for row in rows) if day is not None]
    return (min(days), max(days)) if days else None


def by_day(rows: Iterable[Any], day_of: Callable[[Any], Optional[date]]) -> Dict[date, List[Any]]:
    """The dated rows grouped by day, in file order."""
    groups: Dict[date, List[Any]] = defaultdict(list)
    for row in rows:
        day = day_of(row)
        if day is not None:
            groups[day].append(row)
    return groups


def same_rows(first: Sequence[Any], second: Sequence[Any]) -> bool:
    """Two groups of rows with the same ``signature``\\ s, each counted as often as it appears."""
    return Counter(row.signature for row in first) == Counter(row.signature for row in second)


def contained_rows(inner: Sequence[Any], outer: Sequence[Any]) -> bool:
    """``inner`` is part of ``outer``: every ``signature`` appears in ``outer`` at least as often (an empty group is part of any)."""
    return not (Counter(row.signature for row in inner) - Counter(row.signature for row in outer))


class RoleMerge:
    """Rule M (design D-S28): for each day, the rows of one file among the files covering it.

    A row must expose ``signature`` (a hashable that is equal for two copies of the same bank row).

    Two policies, both with the default that Danske Bank uses:

    - ``owner``: ``"latest"`` (default) gives the day to the file that ends last; ``"most_rows"`` gives it to the file with
      the most rows that day (a bank can only cut an export short, never add rows; ties go to the file that ends last);
    - ``contradiction``: ``"differs"`` (default) calls a day a mismatch when two files do not hold the same rows;
      ``"not_contained"`` calls it a mismatch only when a file holds a row the owner lacks (a file cut mid-day, whose rows
      are all in the owner, is not a contradiction).
    """

    def __init__(
        self,
        files: List[List[Any]],
        day_of: Callable[[Any], Optional[date]],
        *,
        owner: str = "latest",
        contradiction: str = "differs",
    ):
        if owner not in ("latest", "most_rows") or contradiction not in ("differs", "not_contained"):
            raise ValueError(f"unknown rule M policy: owner={owner!r}, contradiction={contradiction!r}")
        self.files = files
        self.day_of = day_of
        self._owner_policy = owner
        self._contradiction_policy = contradiction
        self.spans = [coverage(rows, day_of) for rows in files]
        self.order = sorted((index for index, span in enumerate(self.spans) if span), key=lambda index: (self.spans[index][1], self.spans[index][0], index))
        self.groups = [by_day(rows, day_of) for rows in files]
        self.kept: List[Any] = []
        self.superseded: List[Any] = []
        for index, rows in enumerate(files):
            for row in rows:
                self._place(index, row)
        self.mismatch_days = sorted(self._mismatch_days())

    def _owner(self, day: date) -> int:
        covering = [index for index in reversed(self.order) if self.spans[index][0] <= day <= self.spans[index][1]]
        if self._owner_policy == "latest":
            return covering[0]
        # Most rows that day; max() keeps the first of equals, and ``covering`` starts with the file that ends last.
        return max(covering, key=lambda index: len(self.groups[index].get(day, [])))

    def _agree(self, other_rows: Sequence[Any], owner_rows: Sequence[Any]) -> bool:
        if self._contradiction_policy == "not_contained":
            return contained_rows(other_rows, owner_rows)
        return same_rows(other_rows, owner_rows)

    def _place(self, index: int, row: Any) -> None:
        day = self.day_of(row)
        owner = index if day is None else self._owner(day)
        if owner == index:
            self.kept.append(row)
        elif not same_rows(self.groups[index].get(day, []), self.groups[owner].get(day, [])):
            self.superseded.append(row)

    def _mismatch_days(self) -> Set[date]:
        days: Set[date] = set()
        for index, span in enumerate(self.spans):
            if span is None:
                continue
            candidates = {day for groups in self.groups for day in groups if span[0] <= day <= span[1]}
            for day in candidates:
                owner = self._owner(day)
                if owner != index and not self._agree(self.groups[index].get(day, []), self.groups[owner].get(day, [])):
                    days.add(day)
        return days


# =============================================================================
# PAIRING: ONE TO ONE, NEVER A GUESS
# =============================================================================


def assignments(left_count: int, right_count: int) -> Iterable[List[Tuple[int, int]]]:
    """Every one-to-one assignment between two groups (all of the smaller group, in every order)."""
    if left_count <= right_count:
        for chosen in permutations(range(right_count), left_count):
            yield list(zip(range(left_count), chosen, strict=True))
    else:
        for chosen in permutations(range(left_count), right_count):
            yield list(zip(chosen, range(right_count), strict=True))


def best_assignment[L, R](
    left: List[L],
    right: List[R],
    *,
    same_name: Callable[[L, R], bool],
    outcome_of: Callable[[L], Hashable],
    pair_outcome_of: Optional[Callable[[L, R], Hashable]] = None,
) -> Optional[List[Tuple[L, R]]]:
    """The assignment with the most compatible names, if every such assignment imports the same rows.

    ``outcome_of`` is what an assigned left row would import (its signature): two assignments that differ
    only in which twin gets which partner import the same thing, so they are not an ambiguity.

    When the right row also decides what is imported (a plugin that reads a withholding or an asset from it),
    ``pair_outcome_of`` gives the outcome of a pair instead: two assignments that give the left rows different
    partners are then an ambiguity unless the partners are interchangeable.
    """
    best_weight, outcomes, best = -1, set(), None
    for pairs in assignments(len(left), len(right)):
        weight = sum(same_name(left[i], right[j]) for i, j in pairs)
        if pair_outcome_of is None:
            outcome = tuple(sorted((outcome_of(left[i]) for i, _ in pairs), key=repr))
        else:
            outcome = tuple(sorted((pair_outcome_of(left[i], right[j]) for i, j in pairs), key=repr))
        if weight > best_weight:
            best_weight, outcomes, best = weight, {outcome}, pairs
        elif weight == best_weight:
            outcomes.add(outcome)
    if best is None or len(outcomes) != 1:
        return None
    return [(left[i], right[j]) for i, j in best]


def assign[L, R](
    left: List[L],
    right: List[R],
    *,
    max_candidates: int,
    same_name: Callable[[L, R], bool],
    outcome_of: Callable[[L], Hashable],
    label_of: Callable[[R], str],
    pair_outcome_of: Optional[Callable[[L, R], Hashable]] = None,
) -> Optional[List[Tuple[L, R]]]:
    """Pairs for one key (the rows that share a date, an amount and a direction); ``None`` when ambiguous.

    One against one is the pair; a larger group is paired only when its twins are indistinguishable
    (same import outcome on the left, same label on the right) or when one assignment wins on the names.
    More than ``max_candidates`` rows on either side is not tried. With ``pair_outcome_of`` (see ``best_assignment``) the
    shortcut for twins is skipped: the assignments are compared by what each pair imports.
    """
    if len(left) == 1 and len(right) == 1:
        return [(left[0], right[0])]
    if max(len(left), len(right)) > max_candidates:
        return None
    if pair_outcome_of is None and len({outcome_of(row) for row in left}) == 1 and len({norm(label_of(row)) for row in right}) == 1:
        return list(zip(left, right, strict=False))
    return best_assignment(left, right, same_name=same_name, outcome_of=outcome_of, pair_outcome_of=pair_outcome_of)


def pair_by_key[L, R](
    left_rows: Iterable[L],
    right_rows: Iterable[R],
    *,
    left_key: Callable[[L], Hashable],
    right_key: Callable[[R], Hashable],
    assign_group: Callable[[List[L], List[R]], Optional[List[Tuple[L, R]]]],
) -> Tuple[List[Tuple[L, R]], List[Any]]:
    """Pair the rows of two sides that share a key: ``(pairs, ambiguous rows)``.

    The caller passes only the rows that can be paired. A key present on one side only pairs nothing and is not
    ambiguous (its rows stay unpaired for the caller to classify).
    """
    left_by_key: Dict[Hashable, List[L]] = defaultdict(list)
    right_by_key: Dict[Hashable, List[R]] = defaultdict(list)
    for row in left_rows:
        left_by_key[left_key(row)].append(row)
    for row in right_rows:
        right_by_key[right_key(row)].append(row)
    pairs: List[Tuple[L, R]] = []
    ambiguous: List[Any] = []
    for key in sorted(left_by_key.keys() & right_by_key.keys(), key=repr):
        chosen = assign_group(left_by_key[key], right_by_key[key])
        if chosen is None:
            ambiguous.extend([*left_by_key[key], *right_by_key[key]])
        else:
            pairs.extend(chosen)
    return pairs, ambiguous


# =============================================================================
# SEGMENTS AND ZONES
# =============================================================================


def merge_spans(spans: Iterable[Tuple[date, date]]) -> List[Tuple[date, date]]:
    """Sort the spans and join the ones that overlap or touch (the next day counts as touching)."""
    merged: List[Tuple[date, date]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1] + timedelta(days=1):
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


@dataclass
class Segment:
    """One stretch of the securities history with its truth checkpoint (the eve of its first day)."""

    start: date
    end: date
    checkpoint: date
    kind: str
    window_end: date = date.min
    border_end: date = date.min

    @property
    def zone(self) -> str:
        return "before" if self.kind == "opening" else "gap"


def build_timeline(segments: List[Tuple[date, date]], lag_business_days: int) -> List[Segment]:
    """The segments with their checkpoint, settlement window and border.

    The checkpoint is the eve of the segment's oldest date, also when the cash statement starts later (A13): a row is
    recorded on its trade date, so the opening precedes every one of them (B-52, the developer, 20/10/2026).
    """
    timeline: List[Segment] = []
    for start, end in segments:
        checkpoint = start - timedelta(days=1)
        timeline.append(Segment(start=start, end=end, checkpoint=checkpoint, kind="gap" if timeline else "opening"))
    for index, segment in enumerate(timeline):
        settled = add_business_days(segment.end, lag_business_days)
        segment.window_end = min(settled, timeline[index + 1].checkpoint) if index + 1 < len(timeline) else settled
        segment.border_end = add_business_days(segment.checkpoint, lag_business_days)
    return timeline


def zone(timeline: List[Segment], day: Optional[date]) -> Tuple[str, int]:
    """Zone of a date and the segment it belongs to (for a gap: the segment after it)."""
    if day is None or not timeline:
        return "", -1
    if day <= timeline[0].checkpoint:
        return "before", 0
    for index, segment in enumerate(timeline):
        if day <= segment.window_end:
            return "window", index
        if index + 1 < len(timeline) and day <= timeline[index + 1].checkpoint:
            return "gap", index + 1
    return "after", len(timeline) - 1
