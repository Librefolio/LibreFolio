"""
Gate: every direct reader of ``fx_rates`` skips the rates no read may use, or is a named raw reader (X-R45).

The defect, on HEAD 16e837153. A 1.2 install could store FX rates no reader can use: 0 (a manual ``1E-11`` truncated to
the column's 10 decimals), an infinite REAL (``1E+400`` written as a double) or a rate of ``1E+14`` and above. X-R38
stops new ones (``storable_fx_rate``) and named the bounds of a usable rate, ``usable_fx_rate_bounds()``: ``1E-10`` <=
rate < ``1E+14``. Two readers skip the others, each with an inline copy of the condition (``convert_bulk``,
``_first_rate_days_inside``); three read the table without it and compute with what they find: the planner's saved FX
quotes (``pac_allocator/source/fx_quotes._load_latest_planner_fx_rows``), its WAC evidence
(``pac_allocator/source/wac._load_wac_fx_rows``) and the history sync's last saved dates
(``platform/scheduler/jobs._last_fx_dates``).

The cure's contract, pinned here:

1. ``usable_fx_rate_clause()`` in ``backend/app/db/precision.py``, next to ``usable_fx_rate_bounds()``: the SQLAlchemy
   condition ``fx_rates.rate >= smallest AND fx_rates.rate < first refused``, its two values those of
   ``usable_fx_rate_bounds()``, so the bounds are written once. On a private in-memory ``fx_rates`` it keeps 1E-10, 1.5
   and 99999999999999 and drops 0, 1E-11, -1.5, inf, 1E+14 and 1E+19, stored as SQLite stores them (a REAL, or an
   INTEGER when whole).
2. Every function of ``backend/app`` with a ``select(...)`` naming ``FxRate`` in its arguments — whole rows,
   ``FxRate.rate``, a date aggregate, any column — calls ``usable_fx_rate_clause()``, or is one of
   ``RAW_FX_RATE_READERS``: the readers that must see every stored row, each with its reason. ``select`` is SQLAlchemy's
   or SQLModel's under any name it is imported as (``sql_select``), or ``<module>.select``; a ``select_from``, ``join``
   or ``outerjoin`` naming ``FxRate`` counts too. The scan is column-blind on purpose: whoever adds a read of
   ``fx_rates`` decides, here, whether it may see a rate no read may use — ``fx_core._load_rate_source`` reads only
   ``FxRate.source`` and is listed for that reason. A select in a nested function belongs to the outermost one
   (``_load_rate_source`` for its ``_loader``), a method is ``Class.method``, and the clause counts anywhere in that
   function: ``convert_bulk`` builds it once for its two selects.
3. The list stays true: each entry still selects from ``fx_rates`` and does not call the clause. A raw reader that
   filters loses rows it must see; an entry that no longer reads is stale.

The scanner first proves, on an in-memory module, that it sees each shape of read and leaves the other statements alone.

Red on HEAD 16e837153:

- ``test_usable_fx_rate_clause_exists``, ``test_usable_fx_rate_clause_compares_the_rate_with_usable_fx_rate_bounds`` and
  ``test_usable_fx_rate_clause_keeps_what_a_read_may_use_and_drops_the_rest``: ``precision`` has no
  ``usable_fx_rate_clause``;
- ``test_every_direct_reader_of_fx_rates_uses_the_usable_fx_rate_clause_or_is_a_raw_reader``: five readers, the two
  inline copies (``fx.conversion convert_bulk``, ``fx.period_changes _first_rate_days_inside``) and the three unfiltered
  ones (``pac_allocator.source.fx_quotes _load_latest_planner_fx_rows``, ``pac_allocator.source.wac _load_wac_fx_rows``,
  ``platform.scheduler.jobs _last_fx_dates``).

Green before and after (guards): the scanner's two control cases and
``test_every_raw_fx_rate_reader_is_still_a_raw_reader``.

What the scan does not see, and why it may: raw SQL text (``services/platform/stored_currencies.py`` counts
``fx_rates.base`` and ``fx_rates.quote`` to list the stored currencies — every row, rightly), ``session.get(FxRate, …)``,
a ``where`` naming ``FxRate`` under a select of another table. None reads a rate today.

What the three readers the cure adds the clause to answer is pinned on real SQLite elsewhere:
``test_services/test_bulk_reads_chunked.py`` (section 4: the planner's saved quotes and its WAC evidence) and
``test_services/test_scheduler_last_fx_dates.py`` (the history sync's last saved dates).

Isolation: PURE. The clause runs on a private in-memory SQLite engine per test, disposed at teardown; the gate reads the
sources of ``backend/app`` with ``ast``, never importing them; the control module is an in-memory string. No lane
database, no server, no network, no writes.
"""

from __future__ import annotations

import ast
import functools
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, select, text
from sqlalchemy.dialects import sqlite

from backend.app.db import precision
from backend.app.db.models import FxRate
from backend.test_scripts.test_utils import print_section, print_success

REPO_ROOT = Path(__file__).resolve().parents[3]
# The scanned tree, by path: if it moves, the gate fails loudly instead of scanning nothing.
APP_DIR = REPO_ROOT / "backend" / "app"

CLAUSE_NAME = "usable_fx_rate_clause"


# =============================================================================
# 1. THE CLAUSE: ONE CONDITION FOR A USABLE RATE, BUILT FROM usable_fx_rate_bounds()
# =============================================================================

CLAUSE_DAY0 = date(1987, 6, 1)

#: (case, the rate as the test binds it, whether a read may use it). In a NUMERIC column SQLite keeps a whole double as an
#: INTEGER (0, 99999999999999, 1E+14) and the others as a REAL: inf is ``1E+400`` as a 1.2 install could write it, 0 a
#: manual ``1E-11`` truncated to the column's 10 decimals, 1E-11 a REAL another tool wrote, 1E+19 X-R38's rate of 20 digits.
CLAUSE_CASES = (
    ("smallest-1E-10", 1e-10, True),
    ("ordinary-1.5", 1.5, True),
    ("largest-99999999999999", 99999999999999.0, True),
    ("zero", 0.0, False),
    ("1E-11", 1e-11, False),
    ("negative-1.5", -1.5, False),
    ("inf", float("inf"), False),
    ("first-refused-1E+14", 1e14, False),
    ("1E+19", 1e19, False),
)


def _usable_fx_rate_clause() -> Callable[[], object]:
    """The cure's clause, looked up when a test runs: this file must import on HEAD 16e837153, where it does not exist."""
    clause = getattr(precision, CLAUSE_NAME, None)
    if clause is None:
        pytest.fail(f"backend/app/db/precision.py has no {CLAUSE_NAME}(): each reader of fx_rates writes the bounds of a usable rate itself, or forgets them (X-R45)")
    return clause


@pytest.fixture
def fx_rates_engine() -> Iterator[Engine]:
    """A private in-memory SQLite database holding ``fx_rates`` as the model declares it (``NUMERIC(24, 10)``, as the
    migration does): the lane database is never opened."""
    engine = create_engine("sqlite://")
    try:
        FxRate.__table__.create(engine)
        yield engine
    finally:
        engine.dispose()


def _plant_clause_cases(engine: Engine) -> dict[date, str]:
    """One ERN/STN rate per case, each on its own day, written with raw SQL past the model; the cases by day.

    Barrier: SQLite reads back, with raw SQL, the very rates planted — an inf stays inf, a 0 stays 0.
    """
    days = {CLAUSE_DAY0 + timedelta(days=index): case for index, (case, _rate, _usable) in enumerate(CLAUSE_CASES)}
    rates = {case: rate for case, rate, _usable in CLAUSE_CASES}
    with engine.begin() as connection:
        for day, case in days.items():
            connection.execute(
                text("INSERT INTO fx_rates (date, base, quote, rate, source, fetched_at) VALUES (:day, 'ERN', 'STN', :rate, 'X-R45', CURRENT_TIMESTAMP)"),
                {"day": day.isoformat(), "rate": rates[case]},
            )
        stored = {date.fromisoformat(day): rate for day, rate in connection.execute(text("SELECT date, rate FROM fx_rates")).all()}
    planted = {day: rates[case] for day, case in days.items()}
    assert stored == planted, f"the fixture itself is wrong: raw SQL reads back {stored}, not the rates planted, {planted}"
    return days


def test_usable_fx_rate_clause_exists():
    """Red on HEAD 16e837153: ``backend/app/db/precision.py`` has no ``usable_fx_rate_clause``.

    Contract (X-R45): a function next to ``usable_fx_rate_bounds()`` returning the condition every reader of ``fx_rates``
    adds, instead of two inline copies of the bounds and three readers without them.
    """
    print_section("X-R45: usable_fx_rate_clause() in db/precision.py")
    clause = _usable_fx_rate_clause()
    assert callable(clause), f"precision.{CLAUSE_NAME} is {clause!r}, not a function returning the condition"
    print_success(f"✓ precision.{CLAUSE_NAME}() exists")


def test_usable_fx_rate_clause_compares_the_rate_with_usable_fx_rate_bounds():
    """Red on HEAD 16e837153: no ``usable_fx_rate_clause``.

    Contract (X-R45): built from ``usable_fx_rate_bounds()``, so the bounds are written once. Compiled for SQLite it is
    ``fx_rates.rate >= ? AND fx_rates.rate < ?``, and its two values are those bounds, 1E-10 and 1E+14 — however they
    are bound (a Decimal or a float), compared as numbers.
    """
    print_section("X-R45: usable_fx_rate_clause() is built from usable_fx_rate_bounds()")
    clause = _usable_fx_rate_clause()

    compiled = clause().compile(dialect=sqlite.dialect())
    sql = str(compiled)
    values = sorted(Decimal(str(value)) for value in compiled.params.values())
    bounds = sorted(precision.usable_fx_rate_bounds())

    assert re.search(r"\bfx_rates\.rate >= \?", sql) and re.search(r"\bfx_rates\.rate < \?", sql), f"{CLAUSE_NAME}() compiles to {sql!r}: expected fx_rates.rate >= ? AND fx_rates.rate < ? (X-R45)"
    assert values == bounds, f"{CLAUSE_NAME}() compares fx_rates.rate with {values}: expected the values of usable_fx_rate_bounds(), {bounds} (X-R45)"
    print_success(f"✓ {sql}, with {values}")


def test_usable_fx_rate_clause_keeps_what_a_read_may_use_and_drops_the_rest(fx_rates_engine):
    """Red on HEAD 16e837153: no ``usable_fx_rate_clause``.

    Contract (X-R45): on ``fx_rates`` as SQLite holds it, the clause keeps the rates a read may use — 1E-10 and
    99999999999999, the bounds, and an ordinary 1.5 — and drops every other one: 0, 1E-11, -1.5, inf, 1E+14 (the first
    refused) and 1E+19. All the cases share one table, so the clause must tell them apart row by row.
    """
    print_section("X-R45: what usable_fx_rate_clause() keeps on a private SQLite")
    clause = _usable_fx_rate_clause()
    days = _plant_clause_cases(fx_rates_engine)

    with fx_rates_engine.connect() as connection:
        kept_days = set(connection.execute(select(FxRate.date).where(clause())).scalars().all())

    kept = sorted(days[day] for day in kept_days)
    expected = sorted(case for case, _rate, usable in CLAUSE_CASES if usable)
    assert kept == expected, f"{CLAUSE_NAME}() keeps {kept}: expected {expected}, the rates within usable_fx_rate_bounds() (X-R45)"
    print_success(f"✓ kept {kept}, dropped the {len(CLAUSE_CASES) - len(kept)} others")


# =============================================================================
# 2. THE GATE: EVERY SELECT OF fx_rates IN backend/app IS FILTERED OR A NAMED RAW READER
# =============================================================================

MODEL_NAME = "FxRate"
#: The packages whose ``select`` builds a statement: a ``from sqlalchemy import select as sql_select`` is followed.
SELECT_PACKAGES = frozenset({"sqlalchemy", "sqlmodel"})
#: The methods that put a table into a statement: ``sa.select(...)``, its FROM, or a join.
STATEMENT_METHODS = frozenset({"select", "select_from", "join", "outerjoin"})

#: The readers that must see every stored row, the rates no read may use included: (module, function) → why. Verified
#: against the code by ``test_every_raw_fx_rate_reader_is_still_a_raw_reader``; any other reader calls the clause.
RAW_FX_RATE_READERS: dict[tuple[str, str], str] = {
    ("backend.app.api.v1.backup.exports", "backup_fx_rates"): "the backup of a pair's rates: a complete export of every stored row, so a restore finds what was saved",
    ("backend.app.api.v1.fx.currencies", "delete_rates_endpoint"): "the count of the rows a delete_all of a pair removes: every stored row is removed, an unusable one included",
    ("backend.app.services.ai_export.components.fx_core", "_load_rate_source"): "reads FxRate.source, never the rate, on the exact (pair, date) convert_bulk already chose among the usable rates: (date, base, quote) is unique, so that row is usable by construction",
    ("backend.app.services.financial_math.portfolio.engine", "compute_portfolio_fx_cache_identity"): "the fingerprint of the portfolio caches, not a conversion: any stored row that changes must change the key, an unusable one overwritten by a sync included",
    ("backend.app.services.fx.storage", "delete_rates_bulk"): "the rows a deletion removes: an unusable rate is deleted like any other",
    ("backend.app.services.fx.storage", "upsert_rates_bulk"): "the keys a write updates rather than inserts: an unusable row it overwrites was stored, so the answer is «updated»",
    ("backend.app.services.fx.sync", "_count_actual_changes"): "the sync's change detection: a stored unusable rate compares as a change (X-R38), so the provider's rate overwrites it and is counted",
    ("backend.app.services.fx.sync", "_stored_rates"): "the change detection of ensure_rates_multi_source, as _count_actual_changes for sync_pairs_bulk",
}


@dataclass(frozen=True, order=True)
class FxRateReader:
    """A function that selects from ``fx_rates``: its module, its name, the lines of its selects, whether it calls the clause."""

    module: str
    function: str
    lines: tuple[int, ...]
    filtered: bool

    @property
    def key(self) -> tuple[str, str]:
        return (self.module, self.function)

    def __str__(self) -> str:
        return f"{self.module} {self.function} (line{'s' if len(self.lines) > 1 else ''} {', '.join(str(line) for line in self.lines)})"


def _local_names(tree: ast.Module) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """The names a module binds to a select, to the ``FxRate`` model and to the clause, the aliases of its imports included."""
    selects, models, clauses = {"select", "sql_select"}, {MODEL_NAME}, {CLAUSE_NAME}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        package = (node.module or "").split(".")[0]
        for alias in node.names:
            local = alias.asname or alias.name
            if alias.name == "select" and package in SELECT_PACKAGES:
                selects.add(local)
            elif alias.name == MODEL_NAME:
                models.add(local)
            elif alias.name == CLAUSE_NAME:
                clauses.add(local)
    return frozenset(selects), frozenset(models), frozenset(clauses)


def _names_the_model(node: ast.AST, models: frozenset[str]) -> bool:
    """Whether ``node`` names the model: ``FxRate`` or an alias, any ``FxRate.<column>``, ``models.FxRate``."""
    return any((isinstance(sub, ast.Name) and sub.id in models) or (isinstance(sub, ast.Attribute) and sub.attr == MODEL_NAME) for sub in ast.walk(node))


def _selects_the_model(call: ast.Call, selects: frozenset[str], models: frozenset[str]) -> bool:
    """Whether ``call`` is a select, or a select_from or a join, whose arguments name the model."""
    func = call.func
    statement = (isinstance(func, ast.Name) and func.id in selects) or (isinstance(func, ast.Attribute) and func.attr in STATEMENT_METHODS)
    return statement and any(_names_the_model(argument, models) for argument in [*call.args, *(keyword.value for keyword in call.keywords)])


def _calls_the_clause(scope: ast.AST, clauses: frozenset[str]) -> bool:
    """Whether ``scope`` calls ``usable_fx_rate_clause()``: by its name, an alias, or ``precision.usable_fx_rate_clause()``."""
    return any(isinstance(node, ast.Call) and ((isinstance(node.func, ast.Name) and node.func.id in clauses) or (isinstance(node.func, ast.Attribute) and node.func.attr == CLAUSE_NAME)) for node in ast.walk(scope))


def _owner(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> tuple[str, ast.AST]:
    """The function a select belongs to, and the node to search for the clause: the outermost ``def`` around it, named
    ``Class.method`` inside a class; outside any function, ``<module>`` and the module-level statement holding it."""
    chain = [node]
    while chain[-1] in parents:
        chain.append(parents[chain[-1]])
    functions = [index for index, item in enumerate(chain) if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not functions:
        return "<module>", chain[-2]
    outermost = functions[-1]
    classes = [item.name for item in reversed(chain[outermost + 1 :]) if isinstance(item, ast.ClassDef)]
    return ".".join([*classes, chain[outermost].name]), chain[outermost]


def fx_rate_readers(source: str, module: str) -> list[FxRateReader]:
    """Every function of ``source`` that selects from ``fx_rates``, with the lines of its selects and whether it calls
    the clause, in name order."""
    tree = ast.parse(source)
    selects, models, clauses = _local_names(tree)
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    lines: dict[str, set[int]] = {}
    scopes: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _selects_the_model(node, selects, models):
            name, scope = _owner(node, parents)
            lines.setdefault(name, set()).add(node.lineno)
            scopes.setdefault(name, scope)
    return sorted(FxRateReader(module, name, tuple(sorted(found)), _calls_the_clause(scopes[name], clauses)) for name, found in lines.items())


def unknown_readers(readers: list[FxRateReader], raw_readers: dict[tuple[str, str], str]) -> list[FxRateReader]:
    """The readers that neither call the clause nor are listed as raw readers: the gate's failures."""
    return [reader for reader in readers if not reader.filtered and reader.key not in raw_readers]


def _module_name(path: Path) -> str:
    parts = path.relative_to(REPO_ROOT).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


@functools.cache
def _app_readers() -> tuple[FxRateReader, ...]:
    """Every reader of ``fx_rates`` under ``backend/app``, read with ``ast``: nothing is imported. A source without the
    text ``FxRate`` cannot name the model — an alias is imported by that name, ``models.FxRate`` spells it — so it is not
    parsed."""
    paths = sorted(APP_DIR.rglob("*.py"))
    assert paths, f"no Python file under {APP_DIR}: the gate would be green about nothing — point it at the backend again"
    sources = {path: path.read_text(encoding="utf-8") for path in paths}
    return tuple(reader for path, source in sources.items() if MODEL_NAME in source for reader in fx_rate_readers(source, _module_name(path)))


# -----------------------------------------------------------------------------
# Control cases: the scanner sees each shape of read, and leaves the other statements alone
# -----------------------------------------------------------------------------

CONTROL_SOURCE = """
from sqlalchemy import delete, func, insert
from sqlalchemy import select as pick
from sqlmodel import select

from backend.app.db import models, precision
from backend.app.db.models import Asset, FxRate
from backend.app.db.models import FxRate as Rate
from backend.app.db.precision import usable_fx_rate_clause


async def whole_rows(session):
    return await session.execute(select(FxRate))


async def the_rate_column(session):
    return await session.execute(pick(FxRate.base, FxRate.rate).where(FxRate.base == "EUR"))


async def a_date_aggregate(session):
    return await session.execute(select(func.max(FxRate.date)).group_by(FxRate.base))


async def a_source_lookup(session):
    return await session.execute(select(FxRate.source))


async def an_alias_of_the_model(session):
    return await session.execute(select(Rate.rate))


async def through_the_models_module(session):
    return await session.execute(select(models.FxRate))


async def a_join(session):
    return await session.execute(select(Asset.id).join(FxRate, FxRate.base == Asset.currency))


async def a_count_from(session):
    return await session.execute(select(func.count()).select_from(FxRate))


async def filtered(session):
    usable = usable_fx_rate_clause()
    return await session.execute(select(FxRate).where(usable))


async def filtered_through_the_module(session):
    return await session.execute(select(FxRate.date).where(precision.usable_fx_rate_clause()))


async def filtered_once_for_two_selects(session):
    usable = usable_fx_rate_clause()
    latest = select(func.max(FxRate.date)).where(usable).scalar_subquery()
    return await session.execute(select(FxRate).where(FxRate.date == latest))


async def nested_loader(context):
    async def _loader(session):
        return await session.execute(select(FxRate.source))

    return await context.db_resource(_loader)


class Repository:
    async def method(self, session):
        return await session.execute(select(FxRate))


async def another_table(session):
    return await session.execute(select(Asset).where(Asset.currency == "EUR"))


async def writes(session):
    await session.execute(insert(FxRate).values(rate=1))
    await session.execute(delete(FxRate).where(FxRate.rate == 0))


def a_string_join(rates):
    return ", ".join(str(rate) for rate in rates)


MODULE_LEVEL = select(FxRate.rate)
"""

#: What the scanner must find in ``CONTROL_SOURCE``: reader → whether it calls the clause. ``another_table``, ``writes``
#: and ``a_string_join`` are not readers of fx_rates.
CONTROL_READERS = {
    "<module>": False,
    "Repository.method": False,
    "a_count_from": False,
    "a_date_aggregate": False,
    "a_join": False,
    "a_source_lookup": False,
    "an_alias_of_the_model": False,
    "filtered": True,
    "filtered_once_for_two_selects": True,
    "filtered_through_the_module": True,
    "nested_loader": False,
    "the_rate_column": False,
    "through_the_models_module": False,
    "whole_rows": False,
}


def test_the_scanner_sees_every_shape_of_read_and_whether_it_calls_the_clause():
    """Guard: green before and after. Positive and negative controls on an in-memory module: whole rows, the rate, a date
    aggregate, a column, an alias of the model or of select, ``models.FxRate``, a join, a ``select_from``, a nested
    function (its outermost one), a method (``Class.method``), a module-level select; the clause by name, through the
    module, or once for two selects. Another table, an insert, a delete and a string's ``join`` are not reads. Each
    reported line holds the select.
    """
    print_section("X-R45 gate: what the scanner sees")
    readers = fx_rate_readers(CONTROL_SOURCE, "control")

    found = {reader.function: reader.filtered for reader in readers}
    assert found == CONTROL_READERS, f"the scanner found {found}: expected {CONTROL_READERS}"
    source_lines = CONTROL_SOURCE.splitlines()
    misplaced = [(reader.function, line) for reader in readers for line in reader.lines if not re.search(r"\b(select|pick|join|select_from)\(", source_lines[line - 1])]
    assert not misplaced, f"lines reported that hold no select: {misplaced}"
    print_success(f"✓ {len(readers)} readers found, {sum(found.values())} calling the clause")


def test_the_gate_flags_an_unfiltered_reader_unless_it_is_listed():
    """Guard: green before and after. A reader that does not call the clause is a failure unless its (module, function)
    is listed as a raw reader; a reader that calls it never is, listed or not."""
    print_section("X-R45 gate: what the gate flags")
    readers = fx_rate_readers(CONTROL_SOURCE, "control")
    listed = {("control", "a_source_lookup"): "reads FxRate.source only", ("control", "filtered"): "listed, yet filtered"}

    flagged = sorted(reader.function for reader in unknown_readers(readers, listed))

    expected = sorted(name for name, calls_the_clause in CONTROL_READERS.items() if not calls_the_clause and name != "a_source_lookup")
    assert flagged == expected, f"the gate flags {flagged}: expected {expected}"
    print_success(f"✓ {len(flagged)} flagged, the listed and the filtered readers left alone")


# -----------------------------------------------------------------------------
# The repository
# -----------------------------------------------------------------------------


def test_every_raw_fx_rate_reader_is_still_a_raw_reader():
    """Guard: green before and after. Each ``RAW_FX_RATE_READERS`` entry names a function of ``backend/app`` that still
    selects from ``fx_rates`` and does not call the clause.

    An entry the scan no longer finds is stale: remove it. An entry that calls the clause either loses rows it must see
    — remove the clause — or no longer needs them — remove the entry. Either way the list is a fact about the code.
    """
    print_section("X-R45 gate: the raw readers of fx_rates")
    readers = {reader.key: reader for reader in _app_readers()}

    stale = [f"{module} {function}" for module, function in RAW_FX_RATE_READERS if (module, function) not in readers]
    filtering = [str(readers[key]) for key in RAW_FX_RATE_READERS if key in readers and readers[key].filtered]

    assert not stale, "RAW_FX_RATE_READERS names functions that no longer select from fx_rates — remove them:\n" + "\n".join(f"  {entry}" for entry in stale)
    assert not filtering, f"RAW_FX_RATE_READERS lists readers that call {CLAUSE_NAME}(): a raw reader must see every stored row — remove the clause, or the entry if it no longer needs them:\n" + "\n".join(f"  {entry}" for entry in filtering)
    print_success(f"✓ {len(RAW_FX_RATE_READERS)} raw readers, each still reading every row")


def test_every_direct_reader_of_fx_rates_uses_the_usable_fx_rate_clause_or_is_a_raw_reader():
    """Red on HEAD 16e837153: five readers call no ``usable_fx_rate_clause()`` and are not listed — the two inline copies
    of the bounds (``fx.conversion convert_bulk``, ``fx.period_changes _first_rate_days_inside``) and the three readers
    without them (``pac_allocator.source.fx_quotes _load_latest_planner_fx_rows``, ``pac_allocator.source.wac
    _load_wac_fx_rows``, ``platform.scheduler.jobs _last_fx_dates``).

    Contract (X-R45): one condition for a usable rate. Every function of ``backend/app`` that selects from ``fx_rates``
    calls ``usable_fx_rate_clause()``, or is one of ``RAW_FX_RATE_READERS``, with the reason it must see every row.
    """
    print_section("X-R45 gate: every reader of fx_rates skips the rates no read may use")
    readers = list(_app_readers())
    assert readers, f"the scan found no reader of fx_rates under {APP_DIR}: it would be green about nothing — point it at the code again"

    unknown = unknown_readers(readers, RAW_FX_RATE_READERS)

    assert not unknown, (
        f"Readers of fx_rates without {CLAUSE_NAME}() (X-R45): they read the rates no read may use — 0, inf, 1E+14 and above — as rates. "
        f"Add {CLAUSE_NAME}() to their query, or, for a reader that must see every stored row, add (module, function) to RAW_FX_RATE_READERS with its reason:\n" + "\n".join(f"  {reader}" for reader in unknown)
    )
    print_success(f"✓ {len(readers)} readers of fx_rates: {sum(reader.filtered for reader in readers)} filtered, {len(RAW_FX_RATE_READERS)} raw")
