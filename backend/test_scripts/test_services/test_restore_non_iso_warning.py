"""
The restore check's warning ``non_iso_currencies`` — lot E-19b1 (workstream E), item 4.

Since E-18 a request that writes a currency takes only an ISO 4217 alphabetic code, while older versions stored what the
lenient rule accepted, as given (``978``, ``EURO``). E-19a finds such stored values
(``backend/app/services/platform/stored_currencies.py``, ``./dev.py db currencies``). A restored backup can bring them
back at any time, so the check of an archive for a restore says so, with a new warning code: ``non_iso_currencies``,
the restored copy holds stored currency values that are not ISO 4217 codes. Like every warning, it lets the restore go
on.

Under test, the four places a warning code lives:

1. **The API schema** (``backend/app/schemas/backup.py``): ``RestoreStageReport.warnings`` is a
   ``list[Literal[...]]``; it must accept ``"non_iso_currencies"``, and so must its JSON schema, which the frontend
   client is generated from (RNW-001).
2. **The staging report builder** (``staging._report``): it gains the keyword argument
   ``non_iso_currencies: bool = False``. With ``True`` the code is in ``report.warnings``, once, after the codes the
   other arguments raise; with ``False``, or omitted, it is not. It is a warning, not a blocker: ``blockers`` and
   ``restorable`` are those the other arguments give (RNW-002, RNW-003). **These stay red longest**: ``staging.py`` is
   changed last, after lot B-43 enters. Every comparison is made between the same arguments with and without the flag,
   never against a list of today's codes, so a warning B-43 adds does not turn them red.
3. **The CLI** (``scripts/backup_cli.py``): ``_STAGE_WARNINGS["non_iso_currencies"]`` exists and its text names
   ``db currencies``, the command that lists the values (RNW-004); ``_print_stage_report`` prints that text, not the
   bare code (RNW-005).
4. **Parity**: every code of the schema's ``Literal`` (read with ``typing.get_args``) has a ``_STAGE_WARNINGS`` entry,
   and the ``Literal`` holds the new code: red today because the code is new, green after (RNW-006). And every warning
   ``_report`` gives, in every scenario, is a code of the schema and has a CLI text (RNW-007): without the flag a GUARD,
   green today, which also catches a code another lot adds to the builder alone; with the flag, red until E-19b1.
5. **The check of an archive, end to end** (``staging.stage_archive``). Planned for E-19b1: after the control totals,
   ``_stage`` reads the copy's database (read only, ``trusted_schema`` off first, as ``_administrators`` does) with
   E-19a's ``find_stored_currency_findings`` and passes ``non_iso_currencies=bool(findings)`` to ``_report``. Each
   archive holds the ledger of ``test_backup_staging.py`` (every currency an ISO code) and assets whose currency is
   stored as a version before E-18 left it, by SQL. A copy holding ``978``, ``eur`` or ``EURO``, or the three at once
   after a broken reference of the backup's own, is warned: its warnings are those of its twin (the same archive, every
   stored currency ``EUR``, checked in the same data directory) followed by ``non_iso_currencies``, once; ``blockers``
   and ``restorable`` are the twin's (RNW-101), without an active administrator too (RNW-104). The twin alone is not
   warned (RNW-102, GUARD). ``report.json``, which the API reads back (``read_report``), carries the same warnings, and
   the API schema takes them (RNW-103). An archive at an older revision (``OLDER`` of ``test_backup_staging.py``, the
   released ``004_release_1_2_0_schema``) is checked on its copy after the upgrade (simulated, as that module does: the
   head stamped, no ``alembic`` process): a value the upgrade keeps is warned (RNW-105), a value it corrects is not
   (RNW-106, GUARD).
   A read of the copy's stored currencies that fails never ends the check (B-29's precedent): the copy holds ``978``,
   ``staging.find_stored_currency_findings`` raises ``sqlite3.OperationalError``, and the check returns the warnings,
   blockers and verdict of its twin, without the code, ``report.json`` written; the log has one warning on the stored
   currency codes, with the stage id and the error's class name, neither a path nor the error's text (RNW-107, red at
   its setup until staging imports that function). Before any assertion on the warning, the E-19a audit reads the database the archive carries and the copy the check
   left, so a red is about the check alone. The connections the check opens on its copy are traced by
   ``test_backup_staging.py`` (``trusted_schema`` off first), not here.

   Lot E-19b1.3 (B's review of E-19b1): what that read cannot read as text. A currency the copy stores as a BLOB (a
   TEXT column keeps one bound as bytes; a crafted archive carries it) is no ISO code: the check warns of it as of any
   other, after the twin's warnings, and goes on (RNW-108; red until then: the audit gives the bytes to
   ``json.dumps``, whose ``TypeError`` escapes the read and ends the check). A read that fails never ends the check,
   whatever it raises: RNW-107 also has the audit raise a ``TypeError`` and a ``ValueError`` (red until then: only an
   ``sqlite3.Error`` is caught); the audit's own failure stays pinned there, by injected errors. A REAL error no longer
   reaches the audit: a currency stored as TEXT that is not UTF-8, in a place only the audit read before lot B-49, makes
   ``sqlite3`` raise an ``OperationalError`` whose message quotes the archive's bytes, and since B-49 (B's lot; RNW-109
   rewritten by B, coordinator's decision) the check reads every text of its copy first and refuses such an archive,
   ``database_damaged``, its message naming text that is not UTF-8: no report, the copy removed, the audit never run
   and no line of its, no line of the log holding those bytes or the words of a decode error; its twin, ``EUR`` stored
   there, is checked to its end, unwarned (RNW-109, red until B-49: today the audit fails on the copy, logs its warning,
   and the check goes on to its report). What these archives store is read by SQL: a plain read, on ``sqlite3``'s
   default text factory as the server reads, is what fails on it (since E-20 the E-19a audit reads such a text as its
   bytes).

Lot L3 (workstream B): every report ends with ``credentials_from_backup``, once, after every other warning. So
"after the others" reads here "after the others, before ``credentials_from_backup``": the code stands second to last
(``_then_code``). The comparisons stay relative (the same arguments, the same archive's twin), and the twin's warnings
carry ``credentials_from_backup`` too.

"RED" tests (marked ``# red until E-19b1``) fail before E-19b1, those marked ``# red until E-19b1.3`` before that lot,
the one marked ``# red until B-49`` before that lot; "GUARD (green today)" ones pass before and after. The
new keyword is looked up inside each test (``inspect.signature``), never at import: the file collects, and each red
fails on its own with what is missing.

Sections 1 to 4 are pure: the arguments of ``_report`` are built here, the way ``test_backup_staging.py`` builds them
(``description``, ``synthetic_manifest``), with no archive, no copy and no database; ``staging.get_version`` is replaced
by a fixed version, so no ``git`` process runs. Section 5 builds real archives under ``tmp_path``, from the module
databases of ``test_backup_staging.py`` (``databases``: ``alembic upgrade`` to the head and to its ``OLDER``, each in a
process of its own, once for this module), and checks them in a live data directory of the test, as that module makes
it (``instance``: its database open in WAL mode; every path of it but ``.restore/`` unchanged at the end). Every test,
the pure ones too, runs with a production data directory of the test that must stay absent (``configured_data_dir``,
autouse, with ``LF_APP_VERSION`` set). No lane database, no server, no network.
"""

from __future__ import annotations

import inspect
import sqlite3
import zipfile
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, get_args

import pytest
from pydantic import ValidationError

from backend.app.schemas.backup import RestoreSecretCounts, RestoreStageReport, RestoreTableRows
from backend.app.services.platform.instance_backup import staging
from backend.app.services.platform.instance_backup.archive import BuiltArchive
from backend.app.services.platform.instance_backup.manifest import BackupManifest, ManifestDatabase, ManifestFile
from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY, STAGE_DATA_FOLDER, stage_dir
from backend.app.services.platform.instance_backup.snapshot import DatabaseDescription
from backend.app.services.platform.instance_backup.staging import StagedBackup, StagingReport, TableRows
from backend.app.services.platform.instance_backup.totals import TotalsComparison
from backend.app.services.platform.stored_currencies import find_stored_currency_findings
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utils import print_section, print_success
from scripts import backup_cli

# Section 5. The module fixtures of test_backup_staging.py (lot B2a), re-exported: two databases made once by alembic
# (at the head and at its OLDER), and the live data directory a check runs in (its database open in WAL mode, every path
# of it but .restore unchanged at the end of the test).
databases = cases.databases
instance = cases.instance
# Autouse, for every test of this file: the production data directory of this process is a folder of the test that must
# stay absent, and LF_APP_VERSION is set, so no git process runs (test_backup_staging.py). The pure sections write
# nothing there either.
configured_data_dir = cases.configured_data_dir

#: The new warning code.
CODE = "non_iso_currencies"
#: The keyword argument of ``staging._report`` that raises it.
FLAG = "non_iso_currencies"
#: What the CLI text points to: the command that lists the stored values (E-19a).
CLI_COMMAND = "db currencies"
#: Lot L3: the warning every report carries, last; ``non_iso_currencies`` stands just before it.
CREDENTIALS_FROM_BACKUP = "credentials_from_backup"
#: The warnings the API schema accepts today, written out: the positive control of RNW-001.
WARNINGS_OF_TODAY = ("rows_changed", "foreign_key_violations", "foreign_key_violations_added", "control_totals_changed", "control_totals_unreadable")

APP_VERSION = "v0.0.0-e19b1-restore-warning-test"
HEAD = "head_e19b1"
OLDER = "older_e19b1"
VALID_ID = "0123456789abcdef0123456789abcdef"
CREATED = datetime(2026, 10, 15, 10, 15, tzinfo=UTC)
ADMINISTRATORS = ("ada_admin", "zoe_admin")


def _then_code(warnings: list[str]) -> list[str]:
    """``warnings`` (a report's without the code) with ``non_iso_currencies`` once, after every other warning but
    ``credentials_from_backup``, which every report carries last (lot L3)."""
    return [*(code for code in warnings if code != CREDENTIALS_FROM_BACKUP), CODE, CREDENTIALS_FROM_BACKUP]


@pytest.fixture(autouse=True)
def _fixed_version(monkeypatch):
    """``_report`` names this LibreFolio's version: a fixed one, so that no ``git describe`` runs."""
    monkeypatch.setattr(staging, "get_version", lambda: APP_VERSION)


# =============================================================================
# THE ARGUMENTS OF _report, AS test_backup_staging.py BUILDS THEM
# =============================================================================


def _description(tables: dict[str, int], foreign_key_violations: int) -> DatabaseDescription:
    """A database as ``describe_database`` would describe it: intact, these broken references and rows per table."""
    return DatabaseDescription(size=8192, sha256="a" * 64, integrity_check="ok", foreign_key_violations=foreign_key_violations, tables=dict(tables), alembic_revision=OLDER)


def _manifest(tables: dict[str, int]) -> BackupManifest:
    return BackupManifest(
        created_at=CREATED,
        origin="cli",
        app_version=APP_VERSION,
        alembic_revision=OLDER,
        database=ManifestDatabase(integrity_check="ok", foreign_key_violations=0, tables=dict(tables)),
        files=[ManifestFile(path=DATABASE_ENTRY, size=8192, sha256="a" * 64)],
    )


@dataclass(frozen=True)
class Scenario:
    """The other arguments of ``_report``, and the codes they must raise without the flag (the scenario's precondition)."""

    name: str
    before: dict[str, int] = field(default_factory=lambda: {"users": 3})
    after: dict[str, int] = field(default_factory=lambda: {"users": 3})
    violations_before: int = 0
    violations_after: int = 0
    #: A status of ``TotalsComparison``; None: no comparison given (``absent``).
    totals: str | None = None
    administrators: tuple[str, ...] = ADMINISTRATORS
    raises: tuple[str, ...] = ()


SCENARIOS = (
    Scenario("nothing-to-warn"),
    Scenario("rows-changed", after={"users": 4}, raises=("rows_changed",)),
    Scenario("foreign-keys-kept", violations_before=1, violations_after=1, raises=("foreign_key_violations",)),
    Scenario("foreign-keys-added", violations_after=2, raises=("foreign_key_violations_added",)),
    Scenario("totals-changed", totals="changed", raises=("control_totals_changed",)),
    Scenario("totals-unreadable", totals="unreadable", raises=("control_totals_unreadable",)),
    Scenario("every-other-warning", after={"users": 4}, violations_after=2, totals="changed", raises=("rows_changed", "foreign_key_violations_added", "control_totals_changed")),
    Scenario("no-administrator", administrators=()),
)


def _build(scenario: Scenario, **flag: bool) -> StagingReport:
    """``staging._report`` with the scenario's arguments, and the flag when one is given."""
    totals = TotalsComparison(scenario.totals) if scenario.totals is not None else None
    return staging._report(
        VALID_ID,
        _manifest(scenario.before),
        _description(scenario.before, scenario.violations_before),
        _description(scenario.after, scenario.violations_after),
        "same",
        [],
        HEAD,
        [],
        list(scenario.administrators),
        totals,
        **flag,
    )


def _flag_parameter() -> inspect.Parameter:
    """The keyword argument ``non_iso_currencies`` of ``staging._report``, or the test fails: changed last, after B-43."""
    parameter = inspect.signature(staging._report).parameters.get(FLAG)
    if parameter is None:
        pytest.fail(f"red until E-19b1: staging._report(...) takes no keyword argument {FLAG} yet (staging.py is changed last, after lot B-43)", pytrace=False)
    return parameter


def _build_with_flag(scenario: Scenario, value: bool) -> StagingReport:
    _flag_parameter()
    return _build(scenario, **{FLAG: value})


# =============================================================================
# THE REPORT OF THE API, BUILT FROM ITS FIELDS
# =============================================================================


def _api_report(**changes: Any) -> RestoreStageReport:
    """A valid ``RestoreStageReport``: a backup at the head, nothing changed, one administrator; ``changes`` on top."""
    fields: dict[str, Any] = {
        "backup_created_at": CREATED,
        "backup_app_version": APP_VERSION,
        "backup_origin": "cli",
        "backup_revision": HEAD,
        "app_version": APP_VERSION,
        "head_revision": HEAD,
        "action": "same",
        "migrations": [],
        "post_migration_fixes": [],
        "tables": {"users": RestoreTableRows(before=3, after=3)},
        "foreign_key_violations_before": 0,
        "foreign_key_violations_after": 0,
        "files": 0,
        "files_size": 0,
        "database_size": 8192,
        "instance_key_included": False,
        "encrypted": False,
        "secrets_rekeyed": 0,
        "secrets_unreadable": RestoreSecretCounts(system=0, user=0),
        "administrators": ["ada_admin"],
        "warnings": [],
        "blockers": [],
        "control_totals": "absent",
        "control_totals_differences": [],
        "control_totals_differences_count": 0,
        "restorable": True,
        "expires_at": CREATED + timedelta(hours=24),
    }
    fields.update(changes)
    return RestoreStageReport(**fields)


def _schema_warning_codes() -> tuple[str, ...]:
    """The codes of ``RestoreStageReport.warnings``, a ``list[Literal[...]]``, read with ``typing.get_args``."""
    annotation = RestoreStageReport.model_fields["warnings"].annotation
    (literal,) = get_args(annotation)
    codes = get_args(literal)
    assert codes and all(isinstance(code, str) for code in codes), f"precondition: RestoreStageReport.warnings is a list of a Literal of codes: {annotation}"
    return codes


def _stage_report(warnings: list[str]) -> StagingReport:
    """A report of a check as staging writes it, carrying these warnings (as the CLI tests build one)."""
    return StagingReport(
        stage_id=VALID_ID,
        staged_at=CREATED,
        expires_at=CREATED + timedelta(hours=24),
        backup=StagedBackup(created_at=CREATED, app_version="v1.2.0", origin="ui", alembic_revision=HEAD),
        app_version=APP_VERSION,
        head_revision=HEAD,
        action="same",
        migrations=[],
        post_migration_fixes=[],
        tables={"users": TableRows(before=3, after=3)},
        foreign_key_violations_before=0,
        foreign_key_violations_after=0,
        files=0,
        files_size=0,
        database_size=8192,
        instance_key_included=False,
        administrators=["ada_admin"],
        warnings=warnings,
        blockers=[],
    )


# =============================================================================
# 1. The API schema
# =============================================================================


def test_the_api_report_accepts_the_warning():  # red until E-19b1
    """RNW-001 — RED: ``RestoreStageReport`` takes ``warnings=["non_iso_currencies"]``, alone and after every warning of
    today, and its JSON schema (what the frontend client is generated from) lists the code among those of ``warnings``.

    The positive control, the same report with today's five warnings, validates: a refusal is about the new code alone.
    """
    print_section("RNW-001: RestoreStageReport takes non_iso_currencies")
    assert _api_report(warnings=list(WARNINGS_OF_TODAY)).warnings == list(WARNINGS_OF_TODAY), "positive control: the report with today's warnings validates"
    try:
        alone = _api_report(warnings=[CODE])
        after_the_others = _api_report(warnings=[*WARNINGS_OF_TODAY, CODE])
    except ValidationError as refused:
        pytest.fail(f"red until E-19b1: RestoreStageReport refuses the warning {CODE!r}: {[error['msg'] for error in refused.errors()]}", pytrace=False)
    assert (alone.warnings, after_the_others.warnings) == ([CODE], [*WARNINGS_OF_TODAY, CODE])
    assert (alone.restorable, alone.blockers) == (True, []), "a warning, not a blocker"
    listed = RestoreStageReport.model_json_schema()["properties"]["warnings"]["items"].get("enum", [])
    assert CODE in listed, f"the JSON schema of warnings lists {CODE!r}, so the generated client accepts it: {listed}"
    print_success(f"{CODE} accepted, alone and after the others")


# =============================================================================
# 2. The staging report builder (red longest: changed after lot B-43)
# =============================================================================


def test_report_takes_the_flag_as_a_keyword_defaulting_to_false():  # red until E-19b1
    """RNW-002 — RED: ``staging._report`` has the keyword argument ``non_iso_currencies``, ``False`` by default, so every
    call of today keeps its meaning."""
    parameter = _flag_parameter()
    assert parameter.kind in (inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD), f"{FLAG} is passed by keyword: {parameter.kind}"
    assert parameter.default is False, f"{FLAG} defaults to False: {parameter.default!r}"


@pytest.mark.parametrize("scenario", [pytest.param(scenario, id=scenario.name) for scenario in SCENARIOS])
def test_the_flag_adds_the_warning_after_the_others_and_nothing_else(scenario):  # red until E-19b1
    """RNW-003 — RED: with the same other arguments, ``_report(..., non_iso_currencies=True)`` gives the warnings of
    ``non_iso_currencies=False`` followed by ``non_iso_currencies``, once; ``False`` gives no such code, and so does a
    call without the flag, whose warnings are those of ``False``. ``blockers`` and ``restorable`` are the same in the
    three: a warning lets the restore go on (and does not lift ``no_administrator``).

    The precondition of each scenario: without the flag, it raises the codes it is named after.
    """
    omitted = _build(scenario)
    assert set(scenario.raises) <= set(omitted.warnings), f"precondition: {scenario.name} raises {scenario.raises}: {omitted.warnings}"
    without = _build_with_flag(scenario, False)
    with_flag = _build_with_flag(scenario, True)
    assert CODE not in without.warnings and CODE not in omitted.warnings, f"no {CODE} without the flag: {without.warnings}, {omitted.warnings}"
    assert omitted.warnings == without.warnings, f"omitted is False: {omitted.warnings} != {without.warnings}"
    assert with_flag.warnings == _then_code(without.warnings), f"{CODE} once, after the others, before {CREDENTIALS_FROM_BACKUP}: {with_flag.warnings}"
    assert (with_flag.blockers, with_flag.restorable) == (without.blockers, without.restorable) == (omitted.blockers, omitted.restorable), f"a warning, not a blocker: {with_flag.blockers}"


# =============================================================================
# 3. The CLI
# =============================================================================


def test_the_cli_has_a_text_for_the_warning_naming_db_currencies():  # red until E-19b1
    """RNW-004 — RED: ``scripts.backup_cli._STAGE_WARNINGS["non_iso_currencies"]`` exists, and its text names
    ``db currencies``, the command that lists the stored values that are not ISO codes."""
    texts = backup_cli._STAGE_WARNINGS
    if CODE not in texts:
        pytest.fail(f"red until E-19b1: scripts/backup_cli.py has no text for the warning {CODE!r}: {sorted(texts)}", pytrace=False)
    assert CLI_COMMAND in texts[CODE], f"the text names {CLI_COMMAND!r}: {texts[CODE]!r}"


def test_the_cli_prints_the_text_not_the_code(capsys):  # red until E-19b1
    """RNW-005 — RED: ``_print_stage_report`` of a report carrying the warning prints the warning's text, which names
    ``db currencies``, and never the bare code (what it prints for a code without a text)."""
    backup_cli._print_stage_report(_stage_report([CODE]))
    lines = capsys.readouterr().out.splitlines()
    text = backup_cli._STAGE_WARNINGS.get(CODE)
    bare = [line for line in lines if line.split()[1:] == [CODE]]
    printed = [line for line in lines if text is not None and line.endswith(text)]
    if text is None or bare or not printed:
        pytest.fail(f"red until E-19b1: the CLI prints the bare code for {CODE}, not a text: {bare or lines}", pytrace=False)
    assert all(CLI_COMMAND in line for line in printed), f"the printed warning names {CLI_COMMAND!r}: {printed}"


# =============================================================================
# 4. Parity: the schema, the builder and the CLI name the same codes
# =============================================================================


def test_every_warning_of_the_schema_has_a_cli_text():  # red until E-19b1
    """RNW-006 — GUARD/parity, red today because the code is new: the ``Literal`` of ``RestoreStageReport.warnings``
    holds ``non_iso_currencies``, and every one of its codes has a ``_STAGE_WARNINGS`` entry. Green after, for every code
    added later."""
    codes = _schema_warning_codes()
    if CODE not in codes:
        pytest.fail(f"red until E-19b1: the Literal of RestoreStageReport.warnings has no {CODE!r}: {codes}", pytrace=False)
    missing = [code for code in codes if code not in backup_cli._STAGE_WARNINGS]
    assert missing == [], f"warnings of the API schema the CLI prints as bare codes: {missing}"


@pytest.mark.parametrize("flag", [pytest.param(False, id="without-the-flag-GUARD"), pytest.param(True, id="with-the-flag")])
@pytest.mark.parametrize("scenario", [pytest.param(scenario, id=scenario.name) for scenario in SCENARIOS])
def test_every_warning_the_builder_gives_reaches_the_api_and_the_cli(scenario, flag):  # red until E-19b1 (with the flag)
    """RNW-007 — every warning ``_report`` gives is a code of the API schema (or the check's report could not be served)
    and has a CLI text (or ``dev.py backup restore`` would print a bare code).

    Without the flag: GUARD (green today), which also catches a code another lot adds to the builder alone. With the
    flag: RED until E-19b1.
    """
    report = _build_with_flag(scenario, True) if flag else _build(scenario)
    if flag:
        assert CODE in report.warnings, f"precondition: the flag raises {CODE}: {report.warnings}"
    codes = set(_schema_warning_codes())
    outside_the_schema = [code for code in report.warnings if code not in codes]
    without_text = [code for code in report.warnings if code not in backup_cli._STAGE_WARNINGS]
    assert (outside_the_schema, without_text) == ([], []), f"{scenario.name}: codes the API refuses {outside_the_schema}, codes without a CLI text {without_text}"


# =============================================================================
# 5. The check of an archive, end to end (red as long as _report: staging.py is changed last, after lot B-43)
# =============================================================================
#
# Real archives under tmp_path, checked by ``staging.stage_archive`` in the live data directory of the test. A warned
# archive is compared with its twin, checked in the same data directory: the same archive, every currency it stores an
# ISO code. Before any assertion on the warning, the E-19a audit reads what the archive carries and what the copy holds.

#: Where this section stores its currencies: the currency of an asset, the column the E-19a audit names so. The ledger
#: of ``test_backup_staging.py`` (``add_ledger``) holds the assets 1 to 3; this section's begin at 4.
PLACE = "assets.currency"
FIRST_ASSET_ID = 4
#: The ISO code a twin stores where its archive stores a lenient form of it; the code the upgrade of RNW-106 writes.
CANONICAL = "EUR"
#: Why each red of this section fails until E-19b1.
STAGE_RED = "red until E-19b1: staging._stage does not read the copy's stored currencies yet (staging.py is changed last, after lot B-43)"
#: A broken reference of the backup's own (``test_backup_staging.py`` (j)): the check keeps it and warns of it.
BROKEN_REFERENCE = f"INSERT INTO user_settings (user_id, created_at, updated_at) VALUES (999, '{cases.CREATED}', '{cases.CREATED}')"


def _findings(database: Path) -> list[tuple[str, str]]:
    """What the E-19a audit finds in ``database``, opened read only: (place, value) of each finding, sorted."""
    with closing(cases.read_only(database)) as conn:
        return sorted((finding.place, finding.value) for finding in find_stored_currency_findings(conn))


def _expected_findings(stored: tuple[str, ...]) -> list[tuple[str, str]]:
    """The findings of a database whose assets of this section store ``stored``: each value but ``CANONICAL``, once,
    sorted. Written out here, never asked of the product."""
    return sorted({(PLACE, value) for value in stored if value != CANONICAL})


def _archive(root: Path, database: Path, stored: tuple[str | bytes, ...], *, accounts=cases.ACCOUNTS, statements: tuple[str, ...] = (), verify: Callable[[Path], None] | None = None) -> BuiltArchive:
    """The archive of a data directory made in ``root`` from ``database``, a module database of
    ``test_backup_staging.py``: ``accounts``, ``FILES``, the ledger of that module (``add_ledger``: assets and
    transactions, every currency an ISO code) and one asset more per value of ``stored``, its currency stored as given —
    by SQL, no validator, as a version before E-18 left it; ``bytes`` as a BLOB —; then ``statements``.

    Verified, not assumed: the database the archive carries holds, as the E-19a audit reads it, the findings of
    ``stored`` and no other. Or, given ``verify``, what it checks of that database by SQL instead: what the audit
    cannot read (E-19b1.3: a BLOB before that lot, a text that is not UTF-8).
    """
    data = cases.make_data_dir(root / "data", database, accounts=accounts)
    cases.add_ledger(data / DATABASE_ENTRY)
    assets = [(FIRST_ASSET_ID + index, f"Stored currency {index}", value, "STOCK", cases.CREATED, cases.CREATED) for index, value in enumerate(stored)]
    with closing(sqlite3.connect(data / DATABASE_ENTRY)) as conn, conn:
        conn.executemany(cases.INSERT_ASSET, assets)
        for statement in statements:
            conn.execute(statement)
    built = cases.build_into(data, root / "work")
    carried = root / "carried.db"
    with zipfile.ZipFile(built.path) as archive:
        carried.write_bytes(archive.read(DATABASE_ENTRY))
    if verify is not None:
        verify(carried)
        return built
    found = _findings(carried)
    assert found == _expected_findings(stored), f"precondition: the archive carries {_expected_findings(stored) or 'only ISO codes'}, as the E-19a audit reads it: {found}"
    return built


def _copy_of(data_dir: Path, stage_id: str) -> Path:
    """The database of the copy a check left: what a confirmed restore puts in place."""
    return stage_dir(data_dir, stage_id) / STAGE_DATA_FOLDER / DATABASE_ENTRY


def _check(archive: BuiltArchive, data_dir: Path, holds: list[tuple[str, str]]) -> StagingReport:
    """``staging.stage_archive`` of ``archive`` in ``data_dir``, its report returned. Verified, not assumed: the copy the
    check left, what a confirmed restore puts in place, holds the findings ``holds`` (sorted), as the E-19a audit reads
    it."""
    report = staging.stage_archive(archive.path, data_dir)
    found = _findings(stage_dir(data_dir, report.stage_id) / STAGE_DATA_FOLDER / DATABASE_ENTRY)
    assert found == holds, f"precondition: the copy the check left holds {holds or 'only ISO codes'}: {found}"
    return report


def _warned_once_after_the_others(report: StagingReport, twin: StagingReport, red: str = STAGE_RED) -> None:
    """``report`` carries ``non_iso_currencies`` once, after every other warning: its warnings are those of ``twin``, the
    same archive whose stored currencies are ISO codes, then the code; ``blockers`` and ``restorable`` are the twin's.
    The twin is not warned (precondition). Without the code, the test fails with ``red``: why it is red until its lot."""
    assert CODE not in twin.warnings, f"precondition: the twin, every stored currency an ISO code, is not warned {CODE}: {twin.warnings}"
    if CODE not in report.warnings:
        pytest.fail(f"{red}: the copy holds stored currencies that are not ISO codes, yet the check warns {report.warnings}", pytrace=False)
    assert report.warnings.count(CODE) == 1, f"{CODE} once, whatever the number of findings: {report.warnings}"
    assert report.warnings[-2:] == [CODE, CREDENTIALS_FROM_BACKUP], f"{CODE} after every other warning, before {CREDENTIALS_FROM_BACKUP}: {report.warnings}"
    assert report.warnings == _then_code(twin.warnings), f"the twin's warnings, {CODE} before {CREDENTIALS_FROM_BACKUP}: {report.warnings} != {_then_code(twin.warnings)}"
    assert (report.blockers, report.restorable) == (twin.blockers, twin.restorable), f"a warning, not a blocker: {report.blockers}, restorable={report.restorable}; the twin's: {twin.blockers}, restorable={twin.restorable}"


#: The lenient forms of the euro an older version stored as given (``Currency.validate_code`` took a numeric code or a
#: name, in any case): (the currencies stored, the statements run after them, the warnings the twin must raise).
STORED_FORMS = [
    pytest.param(("978",), (), (), id="numeric-978"),
    pytest.param(("eur",), (), (), id="lower-case-eur"),
    pytest.param(("EURO",), (), (), id="name-EURO"),
    pytest.param(("978", "eur", "EURO"), (BROKEN_REFERENCE,), ("foreign_key_violations",), id="three-forms-after-a-broken-reference"),
]


@pytest.mark.parametrize(("stored", "statements", "raises"), STORED_FORMS)
def test_a_copy_holding_currencies_that_are_not_iso_codes_is_warned_once_after_the_others(instance, databases, tmp_path, stored, statements, raises):  # red until E-19b1
    """RNW-101 — RED: an archive at the head whose copy holds stored currencies that are not ISO codes — ``978`` (a
    numeric code), ``eur`` (a code not in upper case), ``EURO`` (a name), or the three at once — is warned
    ``non_iso_currencies``: its warnings are its twin's (the same archive, every stored currency ``EUR``) followed by the
    code, once, whatever the number of findings; ``blockers`` and ``restorable`` are the twin's: restorable, a warning
    lets the restore go on.

    The precondition of the last case: the twin is warned of the backup's broken reference, so the code comes after
    another warning.
    """
    print_section(f"RNW-101: a copy holding {stored}")
    twin = _check(_archive(tmp_path / "twin", databases.head, (CANONICAL,) * len(stored), statements=statements), instance.root, [])
    assert twin.restorable and set(raises) <= set(twin.warnings), f"precondition: the twin can be restored and raises {raises}: {twin.blockers}, {twin.warnings}"
    report = _check(_archive(tmp_path / "stored", databases.head, stored, statements=statements), instance.root, _expected_findings(stored))
    _warned_once_after_the_others(report, twin)
    print_success(f"{report.warnings}, restorable")


def test_the_same_copy_holding_only_iso_codes_is_not_warned(instance, databases, tmp_path):
    """RNW-102 — GUARD (green today): the twin alone, every currency it stores an ISO code (the ledger's EUR, USD, CHF, GBP
    and JPY, its asset's EUR): no ``non_iso_currencies``. After E-19b1, it is what catches a check that warns of a copy
    for holding currencies at all."""
    report = _check(_archive(tmp_path / "iso", databases.head, (CANONICAL,)), instance.root, [])
    assert CODE not in report.warnings, f"only ISO codes stored: no {CODE}: {report.warnings}"


def test_the_report_written_beside_the_copy_carries_the_warning_as_the_api_reads_it(instance, databases, tmp_path):  # red until E-19b1
    """RNW-103 — RED: ``report.json``, which the API reads back with ``staging.read_report`` and serves, is the report
    the check returned: it carries ``non_iso_currencies``, once, last; and the API's ``RestoreStageReport`` takes its
    warnings, blockers and verdict as written."""
    report = _check(_archive(tmp_path / "stored", databases.head, ("978",)), instance.root, [(PLACE, "978")])
    written = staging.read_report(instance.root, report.stage_id)
    assert written == report, "report.json is the report the check returned"
    if CODE not in written.warnings:
        pytest.fail(f"{STAGE_RED}: report.json carries the warnings {written.warnings}", pytrace=False)
    assert (written.warnings.count(CODE), written.warnings[-2:]) == (1, [CODE, CREDENTIALS_FROM_BACKUP]), f"{CODE} once, last but {CREDENTIALS_FROM_BACKUP}: {written.warnings}"
    try:
        served = _api_report(warnings=written.warnings, blockers=written.blockers, restorable=written.restorable)
    except ValidationError as refused:
        pytest.fail(f"the API's RestoreStageReport refuses what report.json carries: {[error['msg'] for error in refused.errors()]}", pytrace=False)
    assert (served.warnings, served.blockers, served.restorable) == (written.warnings, written.blockers, written.restorable), "served as written"


def test_the_warning_lifts_no_blocker_without_an_active_administrator(instance, databases, tmp_path):  # red until E-19b1
    """RNW-104 — RED: without an active administrator (a user, an administrator whose account is disabled), the twin is
    blocked ``no_administrator``; the copy holding ``978`` is warned as in RNW-101 and blocked the same: the warning
    lifts no blocker, as it adds none."""
    twin = _check(_archive(tmp_path / "twin", databases.head, (CANONICAL,), accounts=cases.WITHOUT_ADMINISTRATOR), instance.root, [])
    assert "no_administrator" in twin.blockers and not twin.restorable, f"precondition: the twin is blocked: {twin.blockers}"
    report = _check(_archive(tmp_path / "stored", databases.head, ("978",), accounts=cases.WITHOUT_ADMINISTRATOR), instance.root, [(PLACE, "978")])
    _warned_once_after_the_others(report, twin)


def test_an_older_backup_is_warned_on_its_copy_after_the_upgrade(instance, databases, tmp_path, monkeypatch):  # red until E-19b1
    """RNW-105 — RED: an archive at ``OLDER`` of ``test_backup_staging.py`` holding ``978``, upgraded on the copy —
    simulated, as that module's (j) and (k) do: the head stamped, no ``alembic`` process — by an upgrade that keeps the
    value: warned as at the head, compared with its twin upgraded the same way."""
    monkeypatch.setattr(staging, "_upgrade", cases.stamp_head)
    twin = _check(_archive(tmp_path / "twin", databases.older, (CANONICAL,)), instance.root, [])
    report = _check(_archive(tmp_path / "stored", databases.older, ("978",)), instance.root, [(PLACE, "978")])
    assert (twin.action, report.action) == ("upgrade", "upgrade"), f"precondition: both upgraded on the copy: {twin.action}, {report.action}"
    _warned_once_after_the_others(report, twin)


def test_a_value_the_upgrade_corrects_on_the_copy_is_not_warned(instance, databases, tmp_path, monkeypatch):
    """RNW-106 — GUARD (green today): the archive at ``OLDER`` carries ``978`` (verified on the archive), and the upgrade
    of the copy corrects it, as a later migration may (simulated: the head stamped, the asset's currency set to ``EUR``).
    The copy holds only ISO codes, so no ``non_iso_currencies``. After E-19b1, it is what catches a check of the
    archive's database before its upgrade instead of the copy after it."""

    def upgrade_correcting_the_currency(database: Path) -> None:
        cases.stamp_head(database)
        cases.execute(database, f"UPDATE assets SET currency = '{CANONICAL}' WHERE id = {FIRST_ASSET_ID}")

    monkeypatch.setattr(staging, "_upgrade", upgrade_correcting_the_currency)
    report = _check(_archive(tmp_path / "stored", databases.older, ("978",)), instance.root, [])
    assert report.action == "upgrade", f"precondition: upgraded on the copy: {report.action}"
    assert CODE not in report.warnings, f"the copy holds only ISO codes after its upgrade: no {CODE}: {report.warnings}"


#: RNW-107: the text of the ``sqlite3.OperationalError`` the read of the copy's stored currencies fails with. The
#: error's text is never logged: no line of the log may hold it.
UNREADABLE = "disk I/O error"
#: RNW-107: what the read of the copy's stored currencies fails with, its class and its text: the ``OperationalError`` of
#: a disk; and errors that are no ``sqlite3.Error`` (E-19b1.3): a ``TypeError``, what ``json.dumps`` raised on a BLOB
#: before that lot, and a ``ValueError``. Each text is the test's own, so that no line of the log holds it by chance.
FAILED_READS = [
    pytest.param(sqlite3.OperationalError, UNREADABLE, id="OperationalError"),
    pytest.param(TypeError, "rnw107 TypeError text: Object of type bytes is not JSON serializable", id="TypeError"),
    pytest.param(ValueError, "rnw107 ValueError text", id="ValueError"),
]
#: Why RNW-107 fails until E-19b1, at its setup: staging has nothing of that name to replace yet.
SEAM_RED = "red until E-19b1: staging does not import find_stored_currency_findings yet, so a read of the copy's stored currencies that fails cannot be simulated where _stage makes it (staging.py is changed last, after lot B-43)"
#: Why RNW-107 fails until E-19b1.3 with an error that is no ``sqlite3.Error``.
CATCH_RED = "red until E-19b1.3: staging._holds_non_iso_currencies catches only sqlite3.Error, so any other error of the read ends the check"
#: The levels at which a line of the log is loud.
LOUD = ("warning", "error", "critical")
#: What the text of the warning on the stored currency codes holds, in any case: «currency» or «currencies».
CURRENCY_WORD = "currenc"


def _the_failed_read_is_logged(events: list[dict[str, Any]], stage_id: str, paths: tuple[str, ...], *, error: str = "OperationalError", untold: tuple[str, ...] = (UNREADABLE,)) -> None:
    """``events``, what ``cases.staging_logs`` captured of a check (its canary aside), hold one loud line on the stored
    currencies: a warning — never an error, the check goes on — with the stage id and the error's class name, ``error``,
    no traceback and none of ``paths``. No line of them holds any of ``untold``: the error's text."""
    lines = [event for event in events if event.get("event") != cases.LOG_CANARY]
    about = [event for event in lines if event.get("log_level") in LOUD and CURRENCY_WORD in str(event.get("event", "")).lower()]
    assert [event.get("log_level") for event in about] == ["warning"], f"one warning on the stored currency codes, and no error: {[(event.get('log_level'), event.get('event')) for event in lines]}"
    warning = about[0]
    fields = {key: value for key, value in warning.items() if key not in ("event", "log_level")}
    assert stage_id in fields.values(), f"the warning carries the stage id, {stage_id}: {fields}"
    assert any(isinstance(value, str) and error in value for value in fields.values()), f"the warning carries the error's class name, {error}: {fields}"
    assert not warning.get("exc_info"), f"no traceback, which holds the error's text: {fields}"
    leaked = [path for path in paths if path in repr(warning)]
    assert leaked == [], f"the warning holds no path ({leaked}): {warning}"
    told = [event for event in lines if any(fragment in repr(event) for fragment in untold)]
    assert told == [], f"no line of the log holds the error's text, {untold!r}: {told}"


@pytest.mark.parametrize(("error", "text"), FAILED_READS)
def test_a_read_of_the_copy_s_currencies_that_fails_is_logged_and_the_check_goes_on_unwarned(instance, databases, tmp_path, monkeypatch, error, text):  # red until E-19b1; TypeError, ValueError: red until E-19b1.3
    """RNW-107 — the copy holds ``978``, but reading its stored currencies fails: the E-19a audit, where ``_stage`` calls
    it (``staging.find_stored_currency_findings``), raises ``error`` — ``sqlite3.OperationalError`` («disk I/O error»),
    or an error that is no ``sqlite3.Error``, a ``TypeError`` or a ``ValueError``. B-29's precedent, a read that fails
    never ends the check, whatever it raises: ``stage_archive`` returns its report, without ``non_iso_currencies``; its
    warnings, blockers and verdict are those of the twin, read without a failure (both keep a broken reference of the
    backup's own, so the twin has a warning the failed read must leave as it is); ``report.json``, which the API reads
    back, is that report. The log has one warning on the stored currency codes, with the stage id and the error's class
    name; neither a path of the test nor the error's text.

    Barriers: the replacement ran, and the copy holds ``978`` as the E-19a audit reads it (the warning was due, had the
    read not failed). RED until E-19b1 at its setup: staging had no ``find_stored_currency_findings`` to replace. The
    ``TypeError`` and ``ValueError`` cases RED until E-19b1.3: ``_holds_non_iso_currencies`` catches ``sqlite3.Error``
    alone, so they end the check today.
    """
    print_section(f"RNW-107: a read of the copy's stored currencies that fails with {error.__name__}")
    twin = _check(_archive(tmp_path / "twin", databases.head, (CANONICAL,), statements=(BROKEN_REFERENCE,)), instance.root, [])
    assert twin.restorable and "foreign_key_violations" in twin.warnings and CODE not in twin.warnings, f"precondition: the twin can be restored, is warned of its broken reference, not {CODE}: {twin.blockers}, {twin.warnings}"
    stored = _archive(tmp_path / "stored", databases.head, ("978",), statements=(BROKEN_REFERENCE,))
    reads: list[tuple[Any, ...]] = []

    def unreadable(*args: Any, **kwargs: Any) -> list[Any]:
        reads.append(args)
        raise error(text)

    try:
        monkeypatch.setattr(staging, "find_stored_currency_findings", unreadable)
    except AttributeError:
        pytest.fail(SEAM_RED, pytrace=False)
    with cases.staging_logs() as events:
        try:
            report = staging.stage_archive(stored.path, instance.root)
        except Exception as exc:
            red = "" if issubclass(error, sqlite3.Error) else f"{CATCH_RED}: "
            pytest.fail(f"{red}a read of the copy's stored currencies that fails ends the check, which it never does (B-29): it raised {type(exc).__name__}: {exc}", pytrace=False)
    assert reads, "barrier: the check read the copy's stored currencies through staging.find_stored_currency_findings, which failed"
    held = _findings(_copy_of(instance.root, report.stage_id))
    assert held == [(PLACE, "978")], f"precondition: the copy the check left holds 978, as the E-19a audit reads it: {held}"
    assert CODE not in report.warnings, f"a read that failed finds nothing: no {CODE}: {report.warnings}"
    assert (report.warnings, report.blockers, report.restorable) == (twin.warnings, twin.blockers, twin.restorable), f"the twin's warnings, blockers and verdict: {report.warnings}, {report.blockers}, {report.restorable} != {twin.warnings}, {twin.blockers}, {twin.restorable}"
    written = staging.read_report(instance.root, report.stage_id)
    assert written == report, "report.json, which the API reads back, is the report the check returned"
    _the_failed_read_is_logged(events, report.stage_id, (str(tmp_path), str(instance.root)), error=error.__name__, untold=(text,))
    print_success(f"{report.warnings}, restorable, one warning logged")


#: RNW-108: the currency an asset stores as a BLOB, the bytes of ``EUR`` bound as such (a TEXT column keeps a BLOB; a
#: crafted archive can carry one), and those bytes as SQLite's ``hex()`` writes them.
BLOB = b"EUR"
BLOB_HEX = "455552"
#: Why RNW-108 fails until E-19b1.3.
BLOB_RED = "red until E-19b1.3: _as_text does not handle a BLOB yet: its TypeError escapes the read of the copy's stored currencies and ends the check"


def _blobs(database: Path) -> list[tuple[int, str]]:
    """The assets of ``database`` whose currency is stored as a BLOB: (id, its bytes in hex), read by SQL, never as text."""
    return cases.rows_of(database, "SELECT id, hex(currency) FROM assets WHERE typeof(currency) = 'blob' ORDER BY id")


def _carries_the_blob(database: Path) -> None:
    """Verified by SQL, the E-19a audit being what fails on a BLOB before E-19b1.3: ``database`` stores one currency as a
    BLOB, the bytes of ``EUR``, in this section's asset."""
    held = _blobs(database)
    assert held == [(FIRST_ASSET_ID, BLOB_HEX)], f"precondition: one currency stored as a BLOB, the bytes of EUR, in asset {FIRST_ASSET_ID}: {held}"


def test_a_copy_holding_a_blob_currency_is_warned_and_the_check_goes_on(instance, databases, tmp_path):  # red until E-19b1.3: _as_text does not handle a BLOB yet
    """RNW-108 — RED until E-19b1.3: an archive at the head whose asset stores its currency as a BLOB (the bytes of
    ``EUR``) is checked to its end: ``stage_archive`` returns, ``blockers`` and ``restorable`` the twin's (the same
    archive, the currency stored as the text ``EUR``), its warnings the twin's followed by ``non_iso_currencies``, once:
    a BLOB is no ISO code. ``report.json``, which the API reads back, is that report.

    Preconditions, read by SQL: the archive carries the BLOB, and so does the copy the check left. Today ``_as_text``
    gives the bytes to ``json.dumps``, whose ``TypeError`` escapes ``_holds_non_iso_currencies`` (it catches only
    ``sqlite3.Error``) and ends the check: a restore of such an archive cannot even be checked.
    """
    print_section("RNW-108: a copy holding a currency stored as a BLOB")
    twin = _check(_archive(tmp_path / "twin", databases.head, (CANONICAL,)), instance.root, [])
    stored = _archive(tmp_path / "blob", databases.head, (BLOB,), verify=_carries_the_blob)
    try:
        report = staging.stage_archive(stored.path, instance.root)
    except Exception as exc:
        pytest.fail(f"{BLOB_RED}: it raised {type(exc).__name__}: {exc}", pytrace=False)
    _carries_the_blob(_copy_of(instance.root, report.stage_id))
    _warned_once_after_the_others(report, twin, red=BLOB_RED)
    assert staging.read_report(instance.root, report.stage_id) == report, "report.json, which the API reads back, is the report the check returned"
    print_success(f"{report.warnings}, restorable")


#: RNW-109: a currency stored as TEXT whose bytes are not UTF-8, the archive's own text (a ``CAST`` of its bytes: SQLite
#: checks no encoding). ``sqlite3`` cannot read it back as text: its ``OperationalError`` quotes it, the byte replaced by
#: U+FFFD («Could not decode to UTF-8 column … with text …»).
NOT_UTF8_MARKER = "rnw109-archive-text"
NOT_UTF8 = b"E\xffR " + NOT_UTF8_MARKER.encode()
#: What no line of the log may hold: the stored text (its ASCII part; as the error quotes it) and the words of the error.
NOT_UTF8_FRAGMENTS = (NOT_UTF8_MARKER, "E\ufffdR", "\ufffd", "Could not decode", "with text")
#: RNW-109, since lot B-49: an archive holding such a text is refused before the E-19a audit reads it, with B-43's code
#: and a message naming the cause.
B49_CODE = "database_damaged"
B49_WORDS = "not UTF-8"
#: Nor, since B-49 decodes the text itself, the words of Python's decoder, which name the byte.
DECODER_FRAGMENTS = ("\\xff", "0xff", "can't decode", "invalid start byte")
#: Why RNW-109 fails until lot B-49.
B49_RED = "red until B-49: nothing of the check reads the copy's text before the E-19a audit, which fails on it, logs its warning and lets the check go on to its report"


@dataclass(frozen=True)
class OnlyAuditedPlace:
    """RNW-109: a place of a stored currency that no step of a check but the E-19a audit read before lot B-49 — not the
    post-migration fixes, the control totals (``transactions``), the plugin secrets or the administrators (``users``);
    B-49's read of every text of the copy now comes first. ``store`` gives the statement storing an SQL expression
    there; ``read``, its storage class and value."""

    place: str
    store: Callable[[str], str]
    read: str


ONLY_AUDITED_PLACES = [
    pytest.param(
        OnlyAuditedPlace(
            "user_settings.base_currency",
            store=lambda value: f"INSERT INTO user_settings (user_id, base_currency, created_at, updated_at) SELECT id, {value}, '{cases.CREATED}', '{cases.CREATED}' FROM users WHERE username = 'zoe_admin'",
            read="SELECT typeof(base_currency), base_currency FROM user_settings WHERE user_id IN (SELECT id FROM users WHERE username = 'zoe_admin')",
        ),
        id="user_settings.base_currency",
    ),
    pytest.param(
        OnlyAuditedPlace(
            "global_settings.default_currency",
            store=lambda value: f"INSERT OR REPLACE INTO global_settings (key, value, value_type, updated_at) VALUES ('default_currency', {value}, 'string', '{cases.CREATED}')",
            read="SELECT typeof(value), value FROM global_settings WHERE key = 'default_currency'",
        ),
        id="global_settings.default_currency",
    ),
    pytest.param(
        OnlyAuditedPlace(
            "asset_events.currency",
            store=lambda value: f"INSERT INTO asset_events (asset_id, date, type, value, currency, created_at, updated_at) VALUES (1, '2026-03-02', 'DIVIDEND', 1.5, {value}, '{cases.CREATED}', '{cases.CREATED}')",
            read="SELECT typeof(currency), currency FROM asset_events WHERE asset_id = 1 AND date = '2026-03-02'",
        ),
        id="asset_events.currency",
    ),
    pytest.param(
        OnlyAuditedPlace(
            "fx_rates.base",
            store=lambda value: f"INSERT INTO fx_rates (date, base, quote, rate, source, fetched_at) VALUES ('2026-03-02', {value}, 'USD', 1.1, 'ECB', '{cases.CREATED}')",
            read="SELECT typeof(base), base FROM fx_rates WHERE date = '2026-03-02' AND quote = 'USD'",
        ),
        id="fx_rates.base",
    ),
]


def _read_as_bytes(database: Path, sql: str) -> list[tuple[Any, ...]]:
    """What ``sql`` reads of ``database``, read only, every text as its bytes: a text that is not UTF-8 included."""
    with closing(cases.read_only(database)) as conn:
        conn.text_factory = bytes
        return conn.execute(sql).fetchall()


def _audit_recorded(patch: pytest.MonkeyPatch) -> list[sqlite3.Connection]:
    """RNW-109: ``staging.find_stored_currency_findings``, where ``_stage`` calls the E-19a audit, the real one, each
    call kept: whether a check reached the audit."""
    calls: list[sqlite3.Connection] = []
    audit = staging.find_stored_currency_findings

    def recorded(connection: sqlite3.Connection) -> list[Any]:
        calls.append(connection)
        return audit(connection)

    patch.setattr(staging, "find_stored_currency_findings", recorded)
    return calls


def _nothing_of_the_audit_nor_of_the_text_is_logged(events: list[dict[str, Any]], paths: tuple[str, ...]) -> None:
    """RNW-109: ``events``, what ``cases.staging_logs`` captured of a check refused before the audit (its canary aside),
    hold no line on the stored currency codes — the audit's, «Stored currency codes could not be read on the copy …» —
    and no line holding the stored text, the words of a decode error (``sqlite3``'s or Python's) or any of ``paths``."""
    lines = [event for event in events if event.get("event") != cases.LOG_CANARY]
    about = [event for event in lines if CURRENCY_WORD in str(event.get("event", "")).lower()]
    assert about == [], f"no line of the audit, which never ran: {about}"
    told = [event for event in lines if any(fragment in repr(event) for fragment in (*NOT_UTF8_FRAGMENTS, *DECODER_FRAGMENTS))]
    assert told == [], f"no line of the log holds the stored text or the words of a decode error: {told}"
    leaked = [event for event in lines if any(path in repr(event) for path in paths)]
    assert leaked == [], f"no line of the log holds a path of the test: {leaked}"


@pytest.mark.parametrize("where", ONLY_AUDITED_PLACES)
def test_a_real_error_of_the_read_is_logged_by_its_class_never_with_the_archive_s_text(instance, databases, tmp_path, monkeypatch, where):  # red until B-49
    """RNW-109 — RED until B-49 (rewritten by B, coordinator's decision): the rule of the log (B-28, B's review of
    E-19b1) with a REAL error. An archive at the head stores a currency as TEXT that is not UTF-8, in a place only the
    E-19a audit read before lot B-49; reading it, ``sqlite3`` raises an ``OperationalError`` whose message quotes the
    archive's bytes. Since B-49 the check reads every text of its copy before the audit, and refuses the archive:
    ``StagingError`` ``database_damaged``, its message naming text that is not UTF-8; no report (``read_report`` finds
    none), the copy removed (only the twin's stage left), the lock free, no path said, the archive only read. The audit
    never runs (``staging.find_stored_currency_findings``, wrapped, is never called) and no line of the log is its; no
    line holds the stored text, the words of a decode error (``sqlite3``'s or Python's) or a path of the test. Its
    twin, ``EUR`` stored there, is checked to its end, restorable, unwarned. The audit's own failure, which no longer
    meets this text, stays pinned by RNW-107's injected errors.

    Preconditions, read back as bytes: the archive stores the text, as TEXT; the twin's copy stores ``EUR``. Barrier: a
    plain read of the archive's database (``where.read``), on ``sqlite3``'s default text factory as the server reads,
    does fail with that ``OperationalError``, its message quoting the text, so the log had something to keep out; the
    E-19a audit no longer does, since E-20 it reads such a text as its bytes. Red until B-49: the audit fails on the
    copy, logs its warning (the class name only), and the check goes on to its report.
    """
    print_section(f"RNW-109: a text that is not UTF-8 in {where.place}")

    def carries_the_text(database: Path) -> None:
        held = _read_as_bytes(database, where.read)
        assert held == [(b"text", NOT_UTF8)], f"precondition: {where.place} stores a text that is not UTF-8, as TEXT: {held}"

    twin = _check(_archive(tmp_path / "twin", databases.head, (), statements=(where.store(f"'{CANONICAL}'"),)), instance.root, [])
    assert (twin.blockers, twin.restorable, CODE in twin.warnings) == ([], True, False), f"precondition: the twin, {CANONICAL} stored there, is checked to its end, restorable, unwarned {CODE}: {twin.blockers}, {twin.warnings}"
    assert _read_as_bytes(_copy_of(instance.root, twin.stage_id), where.read) == [(b"text", CANONICAL.encode())], f"precondition: the twin's copy stores {CANONICAL} in {where.place}"
    stored = _archive(tmp_path / "stored", databases.head, (), statements=(where.store(f"CAST(x'{NOT_UTF8.hex()}' AS TEXT)"),), verify=carries_the_text)
    with closing(cases.read_only(cases.database_of(stored.path, tmp_path / "stored.db"))) as conn, pytest.raises(sqlite3.OperationalError) as raised:
        conn.execute(where.read).fetchall()
    assert NOT_UTF8_MARKER in str(raised.value), f"barrier: a plain read of the archive's database, as the server's driver reads it (sqlite3's default text_factory), fails with an error quoting its text, so the log had something to keep out: {raised.value}"
    original, stages = cases.sha256(stored.path.read_bytes()), cases.leftover_stages(instance.root)
    audited = _audit_recorded(monkeypatch)
    stage_id = staging.new_stage_id()
    with cases.staging_logs() as events:
        try:
            report = staging.stage_archive(stored.path, instance.root, stage_id=stage_id)
        except staging.StagingError as exc:
            error = exc
        else:
            pytest.fail(f"{B49_RED}: the archive was checked, warned {report.warnings}, the audit run {len(audited)} time(s)", pytrace=False)
    assert (error.code, B49_WORDS in str(error)) == (B49_CODE, True), f"refused {B49_CODE}, the message naming text that is not UTF-8: {error.code}: {error}"
    assert audited == [], f"refused before the E-19a audit read the copy, yet it ran {len(audited)} time(s)"
    assert (cases.leftover_stages(instance.root), cases.lock_is_free(instance.root)) == (stages, True), f"the copy removed, only the twin's stage left, the lock free: {cases.leftover_stages(instance.root)} (before: {stages})"
    with pytest.raises(FileNotFoundError):
        staging.read_report(instance.root, stage_id)
    cases.holds_no_path(str(error), stored.path, instance.root)
    assert cases.sha256(stored.path.read_bytes()) == original, "the archive is only read"
    _nothing_of_the_audit_nor_of_the_text_is_logged(events, (str(tmp_path), str(instance.root)))
    print_success(f"{where.place}: refused {error.code} before the audit, no report, nothing of the text logged")
