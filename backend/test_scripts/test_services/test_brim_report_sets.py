"""
Test Suite: BRIM report sets, phase A1 — schemas, plugin contract, combined-file storage

Written red-first, before the code (plan step 4, §3 A1). Every new symbol is looked
up inside the test that needs it, through ``_schema``, ``_service`` and the
``_require_*`` helpers: collection always succeeds, and each test fails on its own,
naming what phase A1 still has to add. The one test whose docstring starts with
"Fixture guard" checks the test-only plugin, not the product: it passes before and
after A1.

Covered, by item of the A1 interface:

- 1–10 schemas: ``BRIMReportRole``, ``BRIMPluginInfo.report_roles``, ``BRIMCoverage``,
  ``BRIMMemberSummary`` (whose account fingerprint is never serialised),
  ``BRIMSetShape``, ``BRIMCombinedTable``, ``BRIMDerivedRef``, the new
  ``BRIMFileInfo`` fields, the truth points (``BRIMTruthCash`` to
  ``BRIMVerification``) and their place in ``BRIMParseOutput`` and
  ``BRIMParseResponse``;
- 11–13 plugin contract: ``BRIMSetRequiredError``, the ``BRIMProvider`` defaults
  that leave every existing plugin unchanged, and a two-role fake plugin that is
  registered in ``BRIMProviderRegistry`` for the duration of one test only;
- 14–20 storage: ``batch_id`` at upload, ``write_combined_csv``,
  ``save_combined_file``, ``find_reusable_combined``, ``combine_is_stale``, the
  links ``delete_file`` keeps honest, and ``list_files``.

No server and no database. BRIM storage is redirected to ``tmp_path`` (the
``isolated_brim_dir`` pattern of ``test_brim_versioning.py``), and the registry is
put back exactly as it was after every test that registers the fake. All data is
synthetic: no value comes from a real bank export.

Phase A2 (second half of this file) is written red-first the same way, through
``_sets`` for the new service module ``backend.app.services.brim_report_sets`` and
the ``phase="A2"`` lookups for the additions to the schemas, the contract and the
storage. It covers:

- A the ``BRIMProvider.history_tag`` default;
- B the request and response schemas of ``POST /sets/preview`` and ``/sets/combine``;
- C ``read_combine_summary``;
- D the service: ``get_set_plugin``, ``collect_members`` (the set is one upload,
  D-S22), ``history_start`` (D-S25), ``build_preview`` (roles, ``missing``, coverage
  warnings, ``mixed_accounts``, H0 and gap-fix warnings), ``preview_set``,
  ``combine_set`` (reuse, generated name, refusal of an incomplete set),
  ``ensure_parseable`` (D-S4) and ``apply_history`` (the checkpoints kept at parse).

The API server parses through a process pool and, under the runner, lives in its
own process: the fake cannot be registered there. So everything a set contains is
tested here, and ``test_api/test_brim_api.py`` covers routing, permissions and
validation. Where H0 needs transactions, each test gets a private in-memory SQLite
database with the ORM schema (``db_session``): never the shared test database.
The A2 tests whose docstring starts with "Fixture guard" check that infrastructure
(the database, the fake's ``describe_set``, the plugin variants, the helpers), not
the product: they pass before and after A2.

Phase F2 (plan F2.0, U2-B) adds two fields to ``BRIMSetPreview``, for the timeline of
the set card: ``history_end``, the date of the newest broker transaction carrying the
plugin's history tag as an exact tag, and ``history_count``, how many there are (gap-fix
corrections included). Written red-first in ``TestSetSchemas`` (defaults, round trip,
strictness) and ``TestPreviewSet`` (filled by ``preview_set``), through
``_require_history_fields``.

Phase G (plan §14 G.2, D) lets the user leave files out of a set: ``BRIMSetRequest``
gains ``exclude_file_ids`` (empty by default, the model still strict), ``collect_members``
drops the excluded originals and ``preview_set`` / ``combine_set`` pass them through; an
excluded id that is not an original of that broker and upload is ``BRIMSetExcludeUnknown``
(422, ``exclude_unknown``), and excluding every member is the 404 of today. Written
red-first at the end of this file, through ``_excluding`` and ``_exclude_request``.
``TestSetSchemas.test_request_fields_are_required`` now compares the three fields it
sends, so the new default does not turn it red.

Step 5 (plan-phase00BrimDanskeBankStep5PluginRedetection, §4), red-first after phase G:
item 8, a Danske pair uploaded together but detected before item 8 (sidecars that keep
their ``batch_id`` but have no ``plugins_signature`` and no plugin recorded) is detected
again on read and forms its set (``collect_members``, the preview); F1, two concurrent
``combine_set`` of one set leave one combined file, the second answering ``reused=True``.
A guard written afterwards, from 1.1.0's own sidecar, pins the limitation of a pair
uploaded with 1.1.0, which recorded no ``batch_id``: detected again, it forms no set and
must be uploaded again, together. The rules of the detection and of the broker lock are
in ``test_brim_parse_race.py``.

Design: LibreFolio_developer_journal/Release_2/Phase_0/26_brimDanskeBank/design-phase00BrimReportSets.md (v5.3), §3.1–§3.5 and §3.8
Plan: LibreFolio_developer_journal/Release_2/Phase_0/26_brimDanskeBank/plan-phase00BrimDanskeBankStep4Implementation.prompt.md, §3 A1 and A2
"""

from __future__ import annotations

import asyncio
import contextlib
import csv
import importlib
import inspect
import json
import shutil
import threading
import uuid
from collections.abc import AsyncIterator, Iterator, Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Optional, Tuple

import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

from backend.app.db.models import Broker, Transaction, TransactionType
from backend.app.schemas import brim as brim_schemas
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMEvidence, BRIMFileInfo, BRIMFileStatus, BRIMNotice, BRIMParseOutput, BRIMParseResponse, BRIMPluginInfo
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services import brim_provider
from backend.app.services.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.provider_registry import BRIMProviderRegistry

BROKER_ID = 42
OTHER_BROKER_ID = 43
USER_ID = 7
UPLOADED_AT = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)

FAKE_CODE = "test_fake_two_role"
CUSTODY_MARKER = "lf_fake_custody"
CASH_MARKER = "lf_fake_cash"
CUSTODY_COLUMNS = ("trade_date", "asset", "quantity")
CASH_COLUMNS = ("value_date", "amount", "currency", "description")
FAKE_ACCOUNT = "fake-custody-account-0001"
FAKE_SET_NOTICE = "fake_set_described"
COMBINED_FILENAME = f"{FAKE_CODE} — combined 2025-01-02…2025-01-17.csv"
NEW_FILE_INFO_FIELDS = ("batch_id", "kind", "derived_from", "combined_into", "combine_is_stale")

# Synthetic member exports. The cash description carries a ";" and quotes and the
# custody asset an umlaut, so the combined file has to keep them verbatim.
CUSTODY_CSV = f"{CUSTODY_MARKER};trade_date;asset;quantity\nrow;2025-01-02;ACME Oyj;10\nrow;2025-01-15;Äijä Holding;-4\n".encode()
CASH_CSV = f'{CASH_MARKER};value_date;amount;currency;description\nrow;2025-01-06;-100.00;EUR;"Osto; ACME ""A"""\nrow;2025-01-17;52.50;EUR;Myynti Äijä\n'.encode()
GENERIC_CSV = b"date,type,quantity,amount,currency,asset\n2025-01-01,DEPOSIT,0,100,EUR,\n"

# The single-file plugins shipped before report sets, frozen on 2026-09-30. A plugin
# that is *meant* to declare roles (Danske, phase B) is deliberately absent, so its
# arrival does not turn the "no existing plugin changes" contract red.
EXISTING_PLUGIN_CODES = (
    "broker_avanza",
    "broker_bitvavo",
    "broker_bux",
    "broker_coinbase",
    "broker_cointracking",
    "broker_credit_agricole",
    "broker_cryptocom",
    "broker_degiro",
    "broker_delta",
    "broker_directa",
    "broker_disnat",
    "broker_etoro",
    "broker_fineco",
    "broker_finpension",
    "broker_freetrade",
    "broker_generic_csv",
    "broker_ibkr",
    "broker_intesa",
    "broker_investengine",
    "broker_investimental",
    "broker_parqet",
    "broker_rabobank",
    "broker_relai",
    "broker_revolut",
    "broker_saxo",
    "broker_schwab",
    "broker_swissquote",
    "broker_traderepublic",
    "broker_trading212",
    "broker_xtb",
)


# =============================================================================
# HELPERS — new symbols are looked up inside each test, never at import time
# =============================================================================


def _missing(what: str, phase: str = "A1") -> None:
    """Fail the current test (not the collection), naming what the phase has to add."""
    pytest.fail(f"{what}: not implemented yet (BRIM report sets, phase {phase})", pytrace=False)


def _schema(name: str, phase: str = "A1") -> Any:
    """A new schema class from ``backend.app.schemas.brim``."""
    found = getattr(brim_schemas, name, None)
    if found is None:
        _missing(f"backend.app.schemas.brim.{name} does not exist", phase)
    return found


def _service(name: str, phase: str = "A1") -> Any:
    """A new function or exception from ``backend.app.services.brim_provider``."""
    found = getattr(brim_provider, name, None)
    if found is None:
        _missing(f"backend.app.services.brim_provider.{name} does not exist", phase)
    return found


def _require_fields(model: Any, *names: str) -> None:
    """The model declares every field in ``names``."""
    absent = [name for name in names if name not in model.model_fields]
    if absent:
        _missing(f"{model.__name__} has no field {', '.join(absent)}")


def _require_contract(*names: str, phase: str = "A1") -> None:
    """``BRIMProvider`` itself, not a subclass, defines every member in ``names``."""
    absent = [name for name in names if not hasattr(BRIMProvider, name)]
    if absent:
        _missing(f"BRIMProvider has no {', '.join(absent)}", phase)


def _require_param(function: Any, name: str) -> None:
    """``function`` accepts a parameter called ``name``."""
    if name not in inspect.signature(function).parameters:
        _missing(f"{function.__name__}() has no '{name}' parameter")


def _write(folder: Path, name: str, content: bytes) -> Path:
    path = folder / name
    path.write_bytes(content)
    return path


def _upload(role: str, *, broker_id: int = BROKER_ID, batch_id: Optional[str] = None) -> BRIMFileInfo:
    """Upload one synthetic member through the real ``save_uploaded_file``; ``batch_id`` is sent only when given."""
    extra: Dict[str, Any] = {}
    if batch_id is not None:
        _require_param(brim_provider.save_uploaded_file, "batch_id")
        extra["batch_id"] = batch_id
    content = CUSTODY_CSV if role == "custody" else CASH_CSV
    return brim_provider.save_uploaded_file(content, f"{role}.csv", user_id=USER_ID, broker_id=broker_id, **extra)


def _refs(*members: Tuple[str, BRIMFileInfo]) -> List[Any]:
    """The ``BRIMDerivedRef`` of each ``(role, uploaded file)``, in order."""
    derived_ref = _schema("BRIMDerivedRef")
    return [derived_ref(file_id=info.file_id, role=role, filename=info.filename) for role, info in members]


def _save_combined(plugin: BRIMProvider, *members: Tuple[str, BRIMFileInfo], plugin_version: Optional[str] = None) -> Tuple[Any, Any]:
    """Combine the members with the fake plugin and store the result, as the A2 combine service will."""
    save_combined_file = _service("save_combined_file")
    paths: Dict[str, List[Path]] = {}
    for role, info in members:
        paths.setdefault(role, []).append(brim_provider.get_file_path(info.file_id))
    table = plugin.combine(paths)
    combined = save_combined_file(broker_id=BROKER_ID, plugin_code=FAKE_CODE, plugin_version=plugin_version or plugin.plugin_version, members=_refs(*members), table=table, filename=COMBINED_FILENAME, user_id=USER_ID)
    return combined, table


def _info(file_id: str) -> BRIMFileInfo:
    """``get_file_info`` for a file that must exist and must still build."""
    info = brim_provider.get_file_info(file_id)
    assert info is not None, f"get_file_info({file_id!r}) is None: the sidecar is gone or no longer builds a BRIMFileInfo"
    return info


def _listed(file_id: str) -> BRIMFileInfo:
    """The one ``list_files()`` entry for ``file_id``."""
    matches = [info for info in brim_provider.list_files() if info.file_id == file_id]
    assert len(matches) == 1, f"{file_id} listed {len(matches)} times"
    return matches[0]


def _sidecar(root: Path, file_id: str) -> Dict[str, Any]:
    """The raw JSON sidecar of a file in the broker's ``uploaded`` folder."""
    path = root / BRIMFileStatus.UPLOADED.value / f"broker_{BROKER_ID}" / f"{file_id}.json"
    assert path.exists(), f"no sidecar at {path}"
    return json.loads(path.read_text())


def _write_legacy_file(root: Path) -> str:
    """A file exactly as ``save_uploaded_file`` stored it before A1: data plus a sidecar with none of the new keys."""
    file_id = str(uuid.uuid4())
    folder = root / BRIMFileStatus.UPLOADED.value / f"broker_{BROKER_ID}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{file_id}.csv").write_bytes(CUSTODY_CSV)
    sidecar = {
        "file_id": file_id,
        "filename": "legacy.csv",
        "extension": ".csv",
        "size_bytes": len(CUSTODY_CSV),
        "status": "uploaded",
        "uploaded_at": "2026-01-02T03:04:05+00:00",
        "processed_at": None,
        "compatible_plugins": ["broker_generic_csv"],
        "error_message": None,
        "uploaded_by_user_id": USER_ID,
        "target_broker_id": BROKER_ID,
        "last_parse_result": None,
    }
    (folder / f"{file_id}.json").write_text(json.dumps(sidecar, indent=2))
    return file_id


# =============================================================================
# THE TEST-ONLY TWO-ROLE PLUGIN AND THE FIXTURES
# =============================================================================


class _FakeTwoRoleProvider(BRIMProvider):
    """Test-only report-set plugin: a ``custody`` export and a ``cash`` export, both ``;``-separated CSV.

    It exists before the feature does: whatever needs a phase-A1 type builds it
    lazily. It is registered in ``BRIMProviderRegistry`` only while a test holds
    the ``fake_plugin`` fixture, and it recognises its members by a marker in the
    header row, so every other CSV is left to the real plugins.
    """

    @property
    def provider_code(self) -> str:
        return FAKE_CODE

    @property
    def provider_name(self) -> str:
        return "Fake two-role report set (tests)"

    @property
    def description(self) -> str:
        return "Test-only report-set plugin with a custody role and a cash role."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def report_roles(self) -> List[Any]:
        role = _schema("BRIMReportRole")
        return [
            role(code="custody", required=True, multiple=True, extensions=[".csv"], description="Fake custody export: one row per trade, dated by trade date"),
            role(code="cash", required=True, multiple=True, extensions=[".csv"], description="Fake cash export: one row per movement, dated by value date", must_cover="custody"),
        ]

    def detect_role(self, file_path: Path) -> Optional[str]:
        header = self._header(file_path)
        if CUSTODY_MARKER in header:
            return "custody"
        if CASH_MARKER in header:
            return "cash"
        return None

    def can_parse(self, file_path: Path) -> bool:
        """True for its two members and for the combined files it produces (design §3.8)."""
        if file_path.suffix.lower() != ".csv":
            return False
        header = self._header(file_path)
        return self.detect_role(file_path) is not None or (header[:2] == ["lf_row_kind", "lf_source"] and f"custody:{CUSTODY_COLUMNS[0]}" in header)

    def describe_member(self, file_path: Path) -> Any:
        """Rows and covered dates of one member: trade dates for custody, value dates for cash.

        A custody header may carry an ``account=<id>`` cell, which becomes the member's
        account fingerprint (``FAKE_ACCOUNT`` when absent): that is how a test mixes two
        custody accounts in one set.
        """
        member_summary, coverage = _schema("BRIMMemberSummary"), _schema("BRIMCoverage")
        role = self.detect_role(file_path)
        if role is None:
            return member_summary(role=None, rows=0)
        dates = [date.fromisoformat(cells[1]) for _line, cells in self._rows(file_path)]
        spans = [coverage(axis="trade" if role == "custody" else "value", start=min(dates), end=max(dates))] if dates else []
        account = None
        if role == "custody":
            account = next((cell.split("=", 1)[1] for cell in self._header(file_path) if cell.startswith("account=")), FAKE_ACCOUNT)
        return member_summary(role=role, rows=len(dates), coverage=spans, account_fingerprint=account)

    def describe_set(self, members: Dict[str, List[Path]]) -> Any:
        """Segments are the custody trade spans, merged when they overlap or touch; each space between two segments is a gap.

        Also one info notice (``FAKE_SET_NOTICE``), so a test can see the plugin's notices reach the preview.
        """
        spans = sorted((span.start, span.end) for path in members.get("custody", []) for span in self.describe_member(path).coverage)
        merged: List[List[date]] = []
        for start, end in spans:
            if merged and start <= merged[-1][1] + timedelta(days=1):
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        segments = [DateRangeModel(start=start, end=end) for start, end in merged]
        gaps = [DateRangeModel(start=before.end + timedelta(days=1), end=after.start - timedelta(days=1)) for before, after in zip(segments, segments[1:], strict=False)]
        notice = BRIMNotice(severity="info", code=FAKE_SET_NOTICE, message="Fake set: segments come from the custody exports")
        return _schema("BRIMSetShape")(segments=segments, gaps=gaps, notices=[notice])

    def combine(self, members: Dict[str, List[Path]]) -> Any:
        """Pure: one ``standalone`` row per member row, its values copied verbatim under ``<role>:<column>``."""
        combined_table = _schema("BRIMCombinedTable")
        headers = ["lf_row_kind", "lf_source", *(f"custody:{column}" for column in CUSTODY_COLUMNS), *(f"cash:{column}" for column in CASH_COLUMNS)]
        custody = [["standalone", f"custody:{line}", *cells[1:], *([""] * len(CASH_COLUMNS))] for path in members.get("custody", []) for line, cells in self._rows(path)]
        cash = [["standalone", f"cash:{line}", *([""] * len(CUSTODY_COLUMNS)), *cells[1:]] for path in members.get("cash", []) for line, cells in self._rows(path)]
        summary = {"rows": {"custody": len(custody), "cash": len(cash)}, "outcomes": {"standalone": len(custody) + len(cash)}}
        return combined_table(headers=headers, rows=custody + cash, summary=summary)

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        """Nothing to import yet: parsing a combined file is phase A2."""
        return BRIMParseOutput(transactions=[], warnings=[], extracted_assets={})

    def _header(self, file_path: Path) -> List[str]:
        head = self._read_file_head(file_path, num_lines=1)
        return [cell.strip() for cell in head.rstrip("\r\n").split(";")] if head else []

    def _rows(self, file_path: Path) -> List[Tuple[int, List[str]]]:
        """Data rows below the header, each with its 1-based line number in the file."""
        with self._open_text(file_path, newline="") as handle:
            reader = csv.reader(handle, delimiter=";")
            next(reader, None)
            return [(reader.line_num, cells) for cells in reader]


@pytest.fixture
def isolated_brim_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Redirect BRIM storage to a temp directory (the pattern of ``test_brim_versioning.py``)."""
    tmp_root = tmp_path / "broker_reports"
    tmp_root.mkdir()
    monkeypatch.setattr(brim_provider, "get_broker_reports_dir", lambda: tmp_root)
    yield tmp_root
    shutil.rmtree(tmp_root, ignore_errors=True)


@pytest.fixture
def fake_plugin() -> Iterator[BRIMProvider]:
    """Register the two-role fake for this test only, then put the registry back exactly as it was.

    Discovery runs first, so the snapshot holds every real plugin: restoring a
    snapshot taken before discovery would empty the registry for the rest of the
    process.
    """
    BRIMProviderRegistry.auto_discover()
    registered = BRIMProviderRegistry._providers
    snapshot = dict(registered)
    assert FAKE_CODE not in snapshot, "the fake plugin leaked out of a previous test"
    BRIMProviderRegistry.register(_FakeTwoRoleProvider)
    try:
        plugin = BRIMProviderRegistry.get_provider_instance(FAKE_CODE)
        assert isinstance(plugin, _FakeTwoRoleProvider)
        yield plugin
    finally:
        registered.clear()
        registered.update(snapshot)


# =============================================================================
# SCHEMAS (items 1–10)
# =============================================================================


class TestReportRoleSchema:
    """1 — ``BRIMReportRole``: one export a report-set plugin needs."""

    def test_defaults(self) -> None:
        """Given only ``code``, ``extensions`` and ``description``, a role is required, single-file, with no depth limit and nothing to cover."""
        role = _schema("BRIMReportRole")(code="custody", extensions=[".xlsx"], description="Custody export")

        assert role.required is True
        assert role.multiple is False
        assert role.max_history is None
        assert role.must_cover is None

    def test_every_field_round_trips(self) -> None:
        """All seven fields survive ``model_dump`` and JSON unchanged."""
        report_role = _schema("BRIMReportRole")
        payload = {"code": "cash", "required": False, "multiple": True, "extensions": [".csv"], "description": "Cash export", "max_history": "P5Y", "must_cover": "custody"}

        role = report_role.model_validate(payload)

        assert role.model_dump() == payload
        assert report_role.model_validate_json(role.model_dump_json()) == role

    def test_extensions_cannot_be_empty(self) -> None:
        """A role without an extension could never be matched to an uploaded file."""
        report_role = _schema("BRIMReportRole")

        with pytest.raises(ValidationError):
            report_role(code="custody", extensions=[], description="Custody export")

    @pytest.mark.parametrize("missing", ["code", "extensions", "description"])
    def test_required_fields(self, missing: str) -> None:
        """``code``, ``extensions`` and ``description`` have no default."""
        report_role = _schema("BRIMReportRole")
        payload = {"code": "custody", "extensions": [".xlsx"], "description": "Custody export"}
        del payload[missing]

        with pytest.raises(ValidationError):
            report_role.model_validate(payload)


class TestNewSchemasAreStrict:
    """1, 3, 4, 5, 7, 9 — every new ``StrictModel``: an unknown key is an error, not a value that silently goes nowhere."""

    @pytest.mark.parametrize(
        ("name", "valid"),
        [
            pytest.param("BRIMReportRole", {"code": "custody", "extensions": [".xlsx"], "description": "Custody export"}, id="1-BRIMReportRole"),
            pytest.param("BRIMCoverage", {"axis": "trade", "start": "2025-01-02", "end": "2025-01-15"}, id="3-BRIMCoverage"),
            pytest.param("BRIMMemberSummary", {"role": "custody", "rows": 2}, id="4-BRIMMemberSummary"),
            pytest.param("BRIMSetShape", {}, id="5-BRIMSetShape"),
            pytest.param("BRIMDerivedRef", {"file_id": "f-1", "filename": "custody.csv"}, id="7-BRIMDerivedRef"),
            pytest.param("BRIMTruthCash", {"currency": "EUR", "amount": "1"}, id="9-BRIMTruthCash"),
            pytest.param("BRIMTruthPosition", {"asset_id": 1, "quantity": "1", "exactness": "exact"}, id="9-BRIMTruthPosition"),
            pytest.param("BRIMAbsorbed", {}, id="9-BRIMAbsorbed"),
            pytest.param("BRIMCheckpoint", {"as_of": "2024-12-31", "kind": "opening"}, id="9-BRIMCheckpoint"),
            pytest.param("BRIMVerification", {"as_of": "2025-01-17"}, id="9-BRIMVerification"),
        ],
    )
    def test_rejects_an_unknown_key(self, name: str, valid: Dict[str, Any]) -> None:
        """The baseline payload is valid, and the same payload plus one unknown key is not."""
        model = _schema(name)
        model.model_validate(valid)

        with pytest.raises(ValidationError):
            model.model_validate({**valid, "unexpected_key": "x"})


class TestPluginInfoReportRoles:
    """2 — ``BRIMPluginInfo.report_roles``: the roles travel with the plugin catalogue (``GET /plugins``)."""

    def test_defaults_to_empty_list(self) -> None:
        """Built the way every plugin builds it today, a plugin info has no roles."""
        _require_fields(BRIMPluginInfo, "report_roles")

        info = BRIMPluginInfo(code="broker_x", name="Broker X", description="Broker X exports", plugin_version="1.0.0")

        assert info.report_roles == []
        assert info.model_dump()["report_roles"] == []

    def test_roles_are_typed_and_ordered(self) -> None:
        """Roles given as dicts or as models come back as ``BRIMReportRole``, in the declared order."""
        _require_fields(BRIMPluginInfo, "report_roles")
        report_role = _schema("BRIMReportRole")
        roles = [{"code": "custody", "extensions": [".xlsx"], "description": "Custody"}, report_role(code="cash", extensions=[".csv"], description="Cash", must_cover="custody")]

        info = BRIMPluginInfo(code="broker_x", name="Broker X", description="Broker X exports", plugin_version="1.0.0", report_roles=roles)

        assert all(isinstance(role, report_role) for role in info.report_roles)
        assert [(role.code, role.must_cover) for role in info.report_roles] == [("custody", None), ("cash", "custody")]


class TestCoverageSchema:
    """3 — ``BRIMCoverage``: the first and last date a member covers, on one axis."""

    @pytest.mark.parametrize("axis", ["trade", "value"])
    def test_accepts_both_axes(self, axis: str) -> None:
        span = _schema("BRIMCoverage")(axis=axis, start=date(2025, 1, 2), end=date(2025, 1, 15))

        assert (span.axis, span.start, span.end) == (axis, date(2025, 1, 2), date(2025, 1, 15))

    def test_single_day_is_valid(self) -> None:
        """``start == end`` is one covered day, not an error; ISO strings are parsed."""
        span = _schema("BRIMCoverage").model_validate({"axis": "value", "start": "2025-01-06", "end": "2025-01-06"})

        assert span.start == span.end == date(2025, 1, 6)

    def test_start_after_end_is_rejected(self) -> None:
        coverage = _schema("BRIMCoverage")

        with pytest.raises(ValidationError):
            coverage(axis="trade", start=date(2025, 1, 15), end=date(2025, 1, 2))

    def test_unknown_axis_is_rejected(self) -> None:
        """Only ``trade`` (custody: trade date) and ``value`` (cash: value date) exist."""
        coverage = _schema("BRIMCoverage")

        with pytest.raises(ValidationError):
            coverage(axis="settlement", start=date(2025, 1, 2), end=date(2025, 1, 15))


class TestMemberSummarySchema:
    """4 — ``BRIMMemberSummary``: what the preview learns about one member, never its account number."""

    def test_defaults(self) -> None:
        summary = _schema("BRIMMemberSummary")(role="cash", rows=0)

        assert (summary.role, summary.rows, summary.coverage, summary.account_fingerprint) == ("cash", 0, [], None)

    def test_role_may_be_unrecognised(self) -> None:
        """A file whose role was not recognised still gets a summary, with ``role=None``."""
        summary = _schema("BRIMMemberSummary")(role=None, rows=3)

        assert summary.role is None

    def test_rows_cannot_be_negative(self) -> None:
        member_summary = _schema("BRIMMemberSummary")

        with pytest.raises(ValidationError):
            member_summary(role="cash", rows=-1)

    def test_coverage_is_typed(self) -> None:
        member_summary = _schema("BRIMMemberSummary")
        coverage = _schema("BRIMCoverage")

        summary = member_summary.model_validate({"role": "custody", "rows": 2, "coverage": [{"axis": "trade", "start": "2025-01-02", "end": "2025-01-15"}]})

        assert summary.coverage == [coverage(axis="trade", start=date(2025, 1, 2), end=date(2025, 1, 15))]

    def test_account_fingerprint_stays_in_memory(self) -> None:
        """Readable for the in-memory ``mixed_accounts`` check, absent from every dump (design §3.3: never shown, never saved)."""
        summary = _schema("BRIMMemberSummary")(role="custody", rows=2, account_fingerprint=FAKE_ACCOUNT)

        assert summary.account_fingerprint == FAKE_ACCOUNT
        assert "account_fingerprint" not in summary.model_dump()
        assert "account_fingerprint" not in summary.model_dump(mode="json")
        assert FAKE_ACCOUNT not in summary.model_dump_json()


class TestSetShapeSchema:
    """5 — ``BRIMSetShape``: the proven segments and gaps of a set, with its notices."""

    def test_defaults_are_empty(self) -> None:
        shape = _schema("BRIMSetShape")()

        assert (shape.segments, shape.gaps, shape.notices) == ([], [], [])

    def test_segments_and_gaps_are_date_ranges(self) -> None:
        set_shape = _schema("BRIMSetShape")
        payload = {
            "segments": [{"start": "2025-01-02", "end": "2025-03-31"}, {"start": "2025-06-02", "end": "2025-09-30"}],
            "gaps": [{"start": "2025-04-01", "end": "2025-06-01"}],
            "notices": [{"severity": "warning", "code": "gap", "message": "Custody export missing from 2025-04-01 to 2025-06-01"}],
        }

        shape = set_shape.model_validate(payload)

        assert all(isinstance(span, DateRangeModel) for span in shape.segments + shape.gaps)
        assert shape.gaps == [DateRangeModel(start=date(2025, 4, 1), end=date(2025, 6, 1))]
        assert all(isinstance(notice, BRIMNotice) for notice in shape.notices)
        assert [notice.code for notice in shape.notices] == ["gap"]

    def test_inverted_segment_is_rejected(self) -> None:
        """``DateRangeModel`` keeps its own rule inside a shape: a segment cannot end before it starts."""
        set_shape = _schema("BRIMSetShape")

        with pytest.raises(ValidationError):
            set_shape.model_validate({"segments": [{"start": "2025-03-31", "end": "2025-01-02"}]})


class TestCombinedTableSchema:
    """6 — ``BRIMCombinedTable``: what a plugin's ``combine`` hands to the core."""

    HEADERS = ("lf_row_kind", "lf_source", "custody:asset", "cash:amount")

    def test_valid_table_with_default_summary(self) -> None:
        rows = [["pair", "custody:2 + cash:3", "ACME Oyj", "-100.00"], ["standalone", "cash:4", "", "52.50"]]

        table = _schema("BRIMCombinedTable")(headers=list(self.HEADERS), rows=rows)

        assert (table.headers, table.rows, table.summary) == (list(self.HEADERS), rows, {})

    def test_summary_is_kept_as_given(self) -> None:
        summary = {"outcomes": {"pair": 1}, "checkpoints": [{"as_of": "2024-12-31", "absorbed": 3}]}

        table = _schema("BRIMCombinedTable")(headers=list(self.HEADERS), rows=[["pair", "custody:2 + cash:3", "ACME Oyj", "-100.00"]], summary=summary)

        assert table.summary == summary

    @pytest.mark.parametrize(
        ("headers", "rows"),
        [
            pytest.param(["lf_row_kind", "lf_source", "cash:amount"], [["pair", "cash:3", "-100.00"], ["standalone", "cash:4"]], id="a-later-row-too-short"),
            pytest.param(["lf_row_kind", "lf_source", "cash:amount"], [["pair", "cash:3", "-100.00", "surplus"]], id="row-too-long"),
            pytest.param(["lf_row_kind", "lf_source", "cash:amount", "cash:amount"], [["pair", "cash:3", "-100.00", "-100.00"]], id="duplicate-header"),
            pytest.param(["lf_source", "cash:amount"], [["cash:3", "-100.00"]], id="no-lf_row_kind"),
            pytest.param(["lf_row_kind", "cash:amount"], [["pair", "-100.00"]], id="no-lf_source"),
        ],
    )
    def test_malformed_table_is_rejected(self, headers: List[str], rows: List[List[str]]) -> None:
        combined_table = _schema("BRIMCombinedTable")

        with pytest.raises(ValidationError):
            combined_table(headers=headers, rows=rows)


class TestDerivedRefSchema:
    """7 — ``BRIMDerivedRef``: one original a combined file was built from."""

    def test_defaults(self) -> None:
        ref = _schema("BRIMDerivedRef")(file_id="f-1", filename="custody.csv")

        assert (ref.role, ref.deleted) == (None, False)

    def test_round_trip(self) -> None:
        derived_ref = _schema("BRIMDerivedRef")
        payload = {"file_id": "f-2", "role": "cash", "filename": "cash.csv", "deleted": True}

        assert derived_ref.model_validate(payload).model_dump() == payload

    @pytest.mark.parametrize("missing", ["file_id", "filename"])
    def test_required_fields(self, missing: str) -> None:
        derived_ref = _schema("BRIMDerivedRef")
        payload = {"file_id": "f-1", "filename": "custody.csv"}
        del payload[missing]

        with pytest.raises(ValidationError):
            derived_ref.model_validate(payload)


class TestFileInfoReportSetFields:
    """8 — ``BRIMFileInfo``: upload batch, kind, and the links between originals and combined files."""

    def test_defaults_describe_an_unlinked_original(self) -> None:
        _require_fields(BRIMFileInfo, *NEW_FILE_INFO_FIELDS)

        info = BRIMFileInfo(file_id="f-1", filename="custody.csv", size_bytes=10, status=BRIMFileStatus.UPLOADED, uploaded_at=UPLOADED_AT)

        assert (info.batch_id, info.kind, info.derived_from, info.combined_into, info.combine_is_stale) == (None, "original", [], [], False)

    def test_links_round_trip(self) -> None:
        """A combined file lists its originals as typed refs; an original lists the combined files built from it."""
        _require_fields(BRIMFileInfo, *NEW_FILE_INFO_FIELDS)
        derived_ref = _schema("BRIMDerivedRef")
        batch = str(uuid.uuid4())

        combined = BRIMFileInfo(file_id="c-1", filename=COMBINED_FILENAME, size_bytes=10, status=BRIMFileStatus.UPLOADED, uploaded_at=UPLOADED_AT, batch_id=batch, kind="combined", derived_from=[{"file_id": "f-1", "role": "custody", "filename": "custody.csv"}], combine_is_stale=True)
        original = BRIMFileInfo(file_id="f-1", filename="custody.csv", size_bytes=10, status=BRIMFileStatus.UPLOADED, uploaded_at=UPLOADED_AT, batch_id=batch, combined_into=["c-1"])

        assert (combined.kind, combined.batch_id, combined.combine_is_stale) == ("combined", batch, True)
        assert combined.derived_from == [derived_ref(file_id="f-1", role="custody", filename="custody.csv")]
        assert (original.kind, original.combined_into) == ("original", ["c-1"])
        assert BRIMFileInfo.model_validate_json(combined.model_dump_json()) == combined

    def test_unknown_kind_is_rejected(self) -> None:
        """Only ``original`` and ``combined`` exist."""
        _require_fields(BRIMFileInfo, "kind")

        with pytest.raises(ValidationError):
            BRIMFileInfo(file_id="f-1", filename="custody.csv", size_bytes=10, status=BRIMFileStatus.UPLOADED, uploaded_at=UPLOADED_AT, kind="merged")


class TestTruthPointSchemas:
    """9 — truth points: what the bank states at a date, as a checkpoint (may correct) or a verification (only compares)."""

    def test_cash_currency_is_normalised(self) -> None:
        cash = _schema("BRIMTruthCash")(currency="eur", amount="1234.50")

        assert (cash.currency, cash.amount) == ("EUR", Decimal("1234.50"))

    def test_cash_currency_must_be_iso_4217(self) -> None:
        """Validated like every currency code, with ``Currency.validate_code``."""
        with pytest.raises(ValueError):
            Currency.validate_code("ZZZ")  # precondition: not an ISO 4217 code
        truth_cash = _schema("BRIMTruthCash")

        with pytest.raises(ValidationError):
            truth_cash(currency="ZZZ", amount="1")

    def test_cash_amount_is_a_safe_decimal(self) -> None:
        """``SafeDecimal``: JSON carries plain notation, never ``1E+3``."""
        cash = _schema("BRIMTruthCash")(currency="EUR", amount=Decimal("1E+3"))

        assert cash.model_dump(mode="json")["amount"] == "1000"

    def test_position_defaults(self) -> None:
        """A position proven for a fake asset id, with no known unit cost; its quantity is a ``SafeDecimal`` too."""
        position = _schema("BRIMTruthPosition")(asset_id=FAKE_ASSET_ID_BASE, quantity=Decimal("1.2E+1"), exactness="exact")

        assert (position.asset_id, position.quantity, position.exactness, position.unit_cost) == (FAKE_ASSET_ID_BASE, Decimal("12"), "exact", None)
        assert position.model_dump(mode="json")["quantity"] == "12"

    def test_position_unit_cost_is_a_currency(self) -> None:
        position = _schema("BRIMTruthPosition").model_validate({"asset_id": 1, "quantity": "3", "exactness": "at_least", "unit_cost": {"code": "eur", "amount": "31.25"}})

        assert position.unit_cost == Currency(code="EUR", amount=Decimal("31.25"))

    def test_position_exactness_is_exact_or_at_least(self) -> None:
        truth_position = _schema("BRIMTruthPosition")

        with pytest.raises(ValidationError):
            truth_position(asset_id=1, quantity="3", exactness="approximate")

    def test_absorbed_defaults(self) -> None:
        absorbed = _schema("BRIMAbsorbed")()

        assert (absorbed.count, absorbed.cash) == (0, [])

    def test_checkpoint_defaults(self) -> None:
        checkpoint = _schema("BRIMCheckpoint").model_validate({"as_of": "2024-12-31", "kind": "opening"})
        absorbed = _schema("BRIMAbsorbed")

        assert checkpoint.as_of == date(2024, 12, 31)
        assert (checkpoint.cash, checkpoint.positions, checkpoint.evidence) == ([], [], [])
        assert checkpoint.absorbed == absorbed()

    def test_checkpoint_kind_is_opening_or_gap(self) -> None:
        brim_checkpoint = _schema("BRIMCheckpoint")

        with pytest.raises(ValidationError):
            brim_checkpoint.model_validate({"as_of": "2024-12-31", "kind": "closing"})

    def test_checkpoint_round_trips_through_json(self) -> None:
        """Cash per currency, exact and minimum positions, absorbed rows and evidence all survive JSON, decimals included."""
        brim_checkpoint = _schema("BRIMCheckpoint")
        payload = {
            "as_of": "2024-12-31",
            "kind": "gap",
            "cash": [{"currency": "EUR", "amount": "1523.40"}, {"currency": "SEK", "amount": "-12.00"}],
            "positions": [{"asset_id": FAKE_ASSET_ID_BASE, "quantity": "10", "exactness": "exact"}, {"asset_id": FAKE_ASSET_ID_BASE - 1, "quantity": "4", "exactness": "at_least", "unit_cost": {"code": "EUR", "amount": "31.25"}}],
            "absorbed": {"count": 3, "cash": [{"currency": "EUR", "amount": "-250.00"}]},
            "evidence": [{"title": "Cash balance on 2024-12-31", "headers": ["value_date", "balance"], "rows": [["2024-12-31", "1523.40"]], "comment": "Running balance of the cash export"}],
        }

        checkpoint = brim_checkpoint.model_validate(payload)

        assert brim_checkpoint.model_validate_json(checkpoint.model_dump_json()) == checkpoint
        assert all(isinstance(item, BRIMEvidence) for item in checkpoint.evidence)
        assert checkpoint.model_dump(mode="json")["cash"] == payload["cash"]

    def test_verification_compares_cash_only(self) -> None:
        """A verification has a date, cash and evidence; no positions, because it never corrects anything."""
        brim_verification = _schema("BRIMVerification")

        verification = brim_verification.model_validate({"as_of": "2025-01-17", "cash": [{"currency": "eur", "amount": "1475.90"}]})

        assert verification.as_of == date(2025, 1, 17)
        assert [(cash.currency, cash.amount) for cash in verification.cash] == [("EUR", Decimal("1475.90"))]
        assert verification.evidence == []
        assert "positions" not in brim_verification.model_fields


class TestParseTruthPoints:
    """10 — ``BRIMParseOutput`` and ``BRIMParseResponse`` carry checkpoints and verifications; the response also ``history_start``."""

    def test_parse_output_defaults_to_no_truth_points(self) -> None:
        _require_fields(BRIMParseOutput, "checkpoints", "verifications")

        output = BRIMParseOutput()

        assert (output.checkpoints, output.verifications) == ([], [])

    def test_parse_output_types_its_truth_points(self) -> None:
        _require_fields(BRIMParseOutput, "checkpoints", "verifications")
        brim_checkpoint, brim_verification = _schema("BRIMCheckpoint"), _schema("BRIMVerification")

        output = BRIMParseOutput(checkpoints=[{"as_of": "2024-12-31", "kind": "opening"}], verifications=[{"as_of": "2025-01-17"}])

        assert all(isinstance(item, brim_checkpoint) for item in output.checkpoints)
        assert all(isinstance(item, brim_verification) for item in output.verifications)
        assert [item.as_of for item in output.checkpoints + output.verifications] == [date(2024, 12, 31), date(2025, 1, 17)]

    def test_existing_plugin_output_has_no_truth_points(self, tmp_path: Path) -> None:
        """Retro-compatibility: a single-file plugin parses as before, with no checkpoints and no verifications."""
        plugin = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")
        output = plugin.parse(_write(tmp_path, "generic.csv", GENERIC_CSV), broker_id=1)
        assert isinstance(output, BRIMParseOutput)  # precondition, true before A1 too
        _require_fields(BRIMParseOutput, "checkpoints", "verifications")

        dumped = output.model_dump(mode="json")

        assert (output.checkpoints, output.verifications) == ([], [])
        assert (dumped["checkpoints"], dumped["verifications"]) == ([], [])

    def test_parse_response_defaults(self) -> None:
        _require_fields(BRIMParseResponse, "checkpoints", "verifications", "history_start")

        response = BRIMParseResponse(file_id="f-1", plugin_code="broker_x", broker_id=1)

        assert (response.checkpoints, response.verifications, response.history_start) == ([], [], None)

    def test_parse_response_carries_history_start(self) -> None:
        _require_fields(BRIMParseResponse, "checkpoints", "verifications", "history_start")

        response = BRIMParseResponse(file_id="f-1", plugin_code="broker_x", broker_id=1, checkpoints=[{"as_of": "2024-12-31", "kind": "opening", "cash": [{"currency": "EUR", "amount": "1523.40"}]}], verifications=[{"as_of": "2025-01-17"}], history_start="2025-01-02")

        dumped = response.model_dump(mode="json")
        assert response.history_start == date(2025, 1, 2)
        assert dumped["history_start"] == "2025-01-02"
        assert dumped["checkpoints"][0]["cash"] == [{"currency": "EUR", "amount": "1523.40"}]
        assert BRIMParseResponse.model_validate_json(response.model_dump_json()) == response

    def test_parse_response_cached_before_a1_still_validates(self) -> None:
        """A response cached in a sidecar before A1, with none of the new keys, validates with empty truth points and no history start."""
        _require_fields(BRIMParseResponse, "checkpoints", "verifications", "history_start")
        cached = {"file_id": "f-1", "plugin_code": "broker_x", "broker_id": 1, "transactions": [], "asset_mappings": [], "duplicates": None, "warnings": [], "validation_issues": [], "field_todos": []}

        response = BRIMParseResponse.model_validate(cached)

        assert (response.checkpoints, response.verifications, response.history_start) == ([], [], None)


# =============================================================================
# PLUGIN CONTRACT (items 11–13)
# =============================================================================


class TestSetRequiredError:
    """11 — ``BRIMSetRequiredError``: a member of a report-set plugin parsed on its own."""

    def test_is_a_parse_error_naming_the_missing_roles(self) -> None:
        set_required_error = _service("BRIMSetRequiredError")

        error = set_required_error("Upload the cash export too", missing_roles=["cash"])

        assert isinstance(error, BRIMParseError)
        assert (error.message, str(error), error.missing_roles) == ("Upload the cash export too", "Upload the cash export too", ["cash"])

    def test_is_caught_where_parse_errors_are(self) -> None:
        """An ``except BRIMParseError`` clause catches it, missing roles included."""
        set_required_error = _service("BRIMSetRequiredError")

        with pytest.raises(BRIMParseError) as caught:
            raise set_required_error("Upload the custody and cash exports", missing_roles=["custody", "cash"])

        assert caught.value.missing_roles == ["custody", "cash"]


class TestProviderContractDefaults:
    """12 — the report-set contract on ``BRIMProvider`` has defaults, so every existing plugin is unchanged."""

    @pytest.fixture
    def generic(self) -> BRIMProvider:
        plugin = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")
        assert plugin is not None
        return plugin

    def test_report_roles_default_to_empty(self, generic: BRIMProvider) -> None:
        _require_contract("report_roles")

        assert generic.report_roles == []

    def test_is_not_a_report_set_plugin(self, generic: BRIMProvider) -> None:
        """``is_report_set_plugin`` is ``bool(report_roles)``."""
        _require_contract("is_report_set_plugin")

        assert generic.is_report_set_plugin is False

    def test_detect_role_defaults_to_none(self, generic: BRIMProvider, tmp_path: Path) -> None:
        _require_contract("detect_role")

        assert generic.detect_role(_write(tmp_path, "generic.csv", GENERIC_CSV)) is None

    @pytest.mark.parametrize("method", ["describe_member", "describe_set", "combine"])
    def test_set_methods_are_not_implemented(self, generic: BRIMProvider, tmp_path: Path, method: str) -> None:
        """A single-file plugin cannot describe or combine a set: the defaults raise ``NotImplementedError``."""
        _require_contract(method)
        path = _write(tmp_path, "generic.csv", GENERIC_CSV)
        argument = path if method == "describe_member" else {"custody": [path]}

        with pytest.raises(NotImplementedError):
            getattr(generic, method)(argument)

    def test_settlement_lag_defaults_to_zero(self, generic: BRIMProvider) -> None:
        _require_contract("settlement_lag_business_days")

        assert generic.settlement_lag_business_days == 0

    def test_pre_checkpoint_policy_defaults_to_summarize(self, generic: BRIMProvider) -> None:
        _require_contract("pre_checkpoint_policy")

        assert generic.pre_checkpoint_policy == "summarize"

    def test_to_plugin_info_carries_empty_roles(self, generic: BRIMProvider) -> None:
        _require_fields(BRIMPluginInfo, "report_roles")

        assert generic.to_plugin_info().report_roles == []

    def test_every_existing_plugin_keeps_single_file_defaults(self) -> None:
        """No plugin shipped before report sets declares a role: for all 30, ``to_plugin_info().report_roles == []`` and ``is_report_set_plugin`` is False."""
        registered = set(BRIMProviderRegistry.list_plugin_codes())
        assert set(EXISTING_PLUGIN_CODES) <= registered, f"no longer registered: {sorted(set(EXISTING_PLUGIN_CODES) - registered)}"
        _require_fields(BRIMPluginInfo, "report_roles")
        _require_contract("is_report_set_plugin")

        plugins = {code: BRIMProviderRegistry.get_provider_instance(code) for code in EXISTING_PLUGIN_CODES}
        declaring = sorted(code for code, plugin in plugins.items() if plugin.to_plugin_info().report_roles != [] or plugin.is_report_set_plugin is not False)

        assert declaring == []


class TestFakeTwoRolePlugin:
    """13 — a report-set plugin as the contract lets one declare itself (test-only, registered for one test)."""

    def test_fixture_guard_detects_members_by_marker(self, fake_plugin: BRIMProvider, tmp_path: Path) -> None:
        """Fixture guard (passes before and after A1): the fake is registered under its code, tells its two members apart by the header marker, and leaves any other CSV alone."""
        custody, cash, other = _write(tmp_path, "custody.csv", CUSTODY_CSV), _write(tmp_path, "cash.csv", CASH_CSV), _write(tmp_path, "generic.csv", GENERIC_CSV)

        assert isinstance(BRIMProviderRegistry.get_provider_instance(FAKE_CODE), _FakeTwoRoleProvider)
        assert [fake_plugin.detect_role(path) for path in (custody, cash, other)] == ["custody", "cash", None]
        assert FAKE_CODE in BRIMProviderRegistry.get_compatible_plugins(custody)
        assert FAKE_CODE in BRIMProviderRegistry.get_compatible_plugins(cash)
        assert FAKE_CODE not in BRIMProviderRegistry.get_compatible_plugins(other)

    def test_plugin_info_round_trips_report_roles(self, fake_plugin: BRIMProvider) -> None:
        """``to_plugin_info`` carries the declared roles unchanged, through ``model_dump`` and JSON."""
        _require_fields(BRIMPluginInfo, "report_roles")

        info = fake_plugin.to_plugin_info()

        assert info.report_roles == fake_plugin.report_roles
        assert [(role.code, role.required, role.multiple, role.extensions, role.must_cover) for role in info.report_roles] == [("custody", True, True, [".csv"], None), ("cash", True, True, [".csv"], "custody")]
        assert BRIMPluginInfo.model_validate(info.model_dump()) == info
        assert BRIMPluginInfo.model_validate_json(info.model_dump_json()) == info

    def test_is_a_report_set_plugin(self, fake_plugin: BRIMProvider) -> None:
        """``is_report_set_plugin`` comes from the base class: the fake only declares roles."""
        _require_contract("is_report_set_plugin")

        assert fake_plugin.is_report_set_plugin is True

    def test_plugin_catalogue_lists_its_roles(self, fake_plugin: BRIMProvider) -> None:
        """``BRIMProviderRegistry.list_plugin_info`` (what ``GET /plugins`` serves) shows the fake's roles beside the empty ones of the real plugins."""
        _require_fields(BRIMPluginInfo, "report_roles")

        catalogue = {info.code: info for info in BRIMProviderRegistry.list_plugin_info()}

        assert [role.code for role in catalogue[FAKE_CODE].report_roles] == ["custody", "cash"]
        assert catalogue["broker_generic_csv"].report_roles == []

    def test_describe_member_reports_rows_and_coverage(self, fake_plugin: BRIMProvider, tmp_path: Path) -> None:
        """Custody covers trade dates and cash value dates; the account fingerprint is kept for the in-memory check only."""
        custody = fake_plugin.describe_member(_write(tmp_path, "custody.csv", CUSTODY_CSV))
        cash = fake_plugin.describe_member(_write(tmp_path, "cash.csv", CASH_CSV))
        coverage = _schema("BRIMCoverage")

        assert (custody.role, custody.rows, custody.coverage) == ("custody", 2, [coverage(axis="trade", start=date(2025, 1, 2), end=date(2025, 1, 15))])
        assert (cash.role, cash.rows, cash.coverage) == ("cash", 2, [coverage(axis="value", start=date(2025, 1, 6), end=date(2025, 1, 17))])
        assert custody.account_fingerprint == FAKE_ACCOUNT
        assert "account_fingerprint" not in custody.model_dump()


# =============================================================================
# STORAGE (items 14–20)
# =============================================================================


class TestUploadBatchId:
    """14 — ``save_uploaded_file(batch_id=...)``: files uploaded together form a set."""

    def test_batch_id_is_stored_and_exposed(self, isolated_brim_dir: Path) -> None:
        """The sidecar stores it; the returned info and ``get_file_info`` expose it."""
        batch = str(uuid.uuid4())

        uploaded = _upload("custody", batch_id=batch)

        assert _sidecar(isolated_brim_dir, uploaded.file_id)["batch_id"] == batch
        assert uploaded.batch_id == batch
        assert _info(uploaded.file_id).batch_id == batch

    def test_upload_without_batch_is_an_unlinked_original(self, isolated_brim_dir: Path) -> None:
        """An old client sends no ``batch_id``: the file is an upload of its own."""
        uploaded = _upload("custody")
        _require_fields(BRIMFileInfo, *NEW_FILE_INFO_FIELDS)

        for info in (uploaded, _info(uploaded.file_id)):
            assert (info.batch_id, info.kind, info.derived_from, info.combined_into, info.combine_is_stale) == (None, "original", [], [], False)

    def test_legacy_sidecar_reads_with_defaults(self, isolated_brim_dir: Path) -> None:
        """A sidecar written before A1, with none of the new keys, still builds, as an unlinked original; having no ``plugins_signature``, its plugin list is detected again from its data file (item 8)."""
        legacy = _info(_write_legacy_file(isolated_brim_dir))  # precondition, true before A1 too
        _require_fields(BRIMFileInfo, *NEW_FILE_INFO_FIELDS)

        assert (legacy.batch_id, legacy.kind, legacy.derived_from, legacy.combined_into, legacy.combine_is_stale) == (None, "original", [], [], False)
        assert (legacy.filename, legacy.target_broker_id, legacy.compatible_plugins) == ("legacy.csv", BROKER_ID, BRIMProviderRegistry.get_compatible_plugins(brim_provider.get_file_path(legacy.file_id)))


class TestWriteCombinedCsv:
    """15 — ``write_combined_csv``: the one combined-file format (D-S2), written by the core and never by a plugin."""

    def test_bom_semicolons_minimal_quoting_and_lf(self, tmp_path: Path) -> None:
        """UTF-8 with BOM, ``;`` between cells, quotes only where a value needs them (doubled inside), LF after every row."""
        write_combined_csv, combined_table = _service("write_combined_csv"), _schema("BRIMCombinedTable")
        path = tmp_path / "combined.csv"
        table = combined_table(headers=["lf_row_kind", "lf_source", "cash:Selite"], rows=[["pair", "custody:2 + cash:3", "Osto ACME"], ["excluded", "cash:4", "a;b"], ["standalone", "cash:5", 'Maksu "Äijä"']])

        write_combined_csv(path, table)

        expected = 'lf_row_kind;lf_source;cash:Selite\npair;custody:2 + cash:3;Osto ACME\nexcluded;cash:4;"a;b"\nstandalone;cash:5;"Maksu ""Äijä"""\n'
        assert path.read_bytes() == b"\xef\xbb\xbf" + expected.encode()

    def test_round_trips_through_csv_reader(self, tmp_path: Path) -> None:
        """Read back the way the contract reads it, the file gives exactly the headers and the rows, with ``;``, quotes, ä and ö."""
        write_combined_csv, combined_table = _service("write_combined_csv"), _schema("BRIMCombinedTable")
        headers = ["lf_row_kind", "lf_source", "custody:Arvopaperi", "cash:Selite", "cash:Summa"]
        rows = [["pair", "custody:2 + cash:3", "Äijä Holding", 'Osto; "ACME"', "-100,00"], ["standalone", "cash:4", "", "Säästötili; öljy", "52,50"]]
        path = tmp_path / "combined.csv"

        write_combined_csv(path, combined_table(headers=headers, rows=rows))

        with open(path, encoding="utf-8-sig", newline="") as handle:
            assert list(csv.reader(handle, delimiter=";")) == [headers, *rows]

    def test_empty_and_multiline_values_survive(self, tmp_path: Path) -> None:
        """Exactness beyond the three listed cases: an empty cell and a cell with a line break come back unchanged."""
        write_combined_csv, combined_table = _service("write_combined_csv"), _schema("BRIMCombinedTable")
        headers = ["lf_row_kind", "lf_source", "cash:Selite"]
        rows = [["standalone", "cash:4", ""], ["standalone", "cash:5", "first line\nsecond line"]]
        path = tmp_path / "combined.csv"

        write_combined_csv(path, combined_table(headers=headers, rows=rows))

        with open(path, encoding="utf-8-sig", newline="") as handle:
            assert list(csv.reader(handle, delimiter=";")) == [headers, *rows]


class TestSaveCombinedFile:
    """16 — ``save_combined_file``: the combined CSV and its sidecar beside the originals, linked both ways."""

    def test_returns_a_combined_file_info(self, isolated_brim_dir: Path, fake_plugin: BRIMProvider) -> None:
        """The returned info and ``get_file_info`` agree: a ``combined`` file of the broker, compatible with its plugin only, derived from the members."""
        custody, cash = _upload("custody"), _upload("cash")

        combined, _ = _save_combined(fake_plugin, ("custody", custody), ("cash", cash))

        assert combined.file_id not in {custody.file_id, cash.file_id}
        for info in (combined, _info(combined.file_id)):
            assert (info.kind, info.status, info.filename) == ("combined", BRIMFileStatus.UPLOADED, COMBINED_FILENAME)
            assert (info.compatible_plugins, info.target_broker_id) == ([FAKE_CODE], BROKER_ID)
            assert info.derived_from == _refs(("custody", custody), ("cash", cash))
            assert (info.combined_into, info.combine_is_stale) == ([], False)

    def test_writes_data_and_sidecar_beside_the_originals(self, isolated_brim_dir: Path, fake_plugin: BRIMProvider, tmp_path: Path) -> None:
        """A ``.csv`` in the broker's ``uploaded`` folder, byte for byte what ``write_combined_csv`` writes, plus a sidecar with the combine provenance."""
        custody, cash = _upload("custody"), _upload("cash")

        combined, table = _save_combined(fake_plugin, ("custody", custody), ("cash", cash))

        data_path = isolated_brim_dir / BRIMFileStatus.UPLOADED.value / f"broker_{BROKER_ID}" / f"{combined.file_id}.csv"
        reference = tmp_path / "reference.csv"
        _service("write_combined_csv")(reference, table)
        assert brim_provider.get_file_path(combined.file_id) == data_path
        assert data_path.read_bytes() == reference.read_bytes()
        assert combined.size_bytes == data_path.stat().st_size
        with open(data_path, encoding="utf-8-sig", newline="") as handle:
            assert list(csv.reader(handle, delimiter=";")) == [table.headers, *table.rows]
        sidecar = _sidecar(isolated_brim_dir, combined.file_id)
        assert (sidecar["combine_plugin_code"], sidecar["combine_plugin_version"]) == (FAKE_CODE, fake_plugin.plugin_version)
        assert sidecar["combine_summary"] == table.summary
        assert sidecar.get("members_key"), "the sidecar needs a members_key to recognise the same member set later"

    def test_members_list_every_combined_built_from_them(self, isolated_brim_dir: Path, fake_plugin: BRIMProvider) -> None:
        """Each save appends the new id to every member's ``combined_into``, in the sidecar and in ``get_file_info``."""
        custody, cash = _upload("custody"), _upload("cash")

        first, _ = _save_combined(fake_plugin, ("custody", custody), ("cash", cash))
        second, _ = _save_combined(fake_plugin, ("custody", custody), ("cash", cash), plugin_version="1.1.0")

        for member in (custody, cash):
            assert _sidecar(isolated_brim_dir, member.file_id)["combined_into"] == [first.file_id, second.file_id]
            assert _info(member.file_id).combined_into == [first.file_id, second.file_id]

    def test_shared_batch_id_is_inherited(self, isolated_brim_dir: Path, fake_plugin: BRIMProvider) -> None:
        """Members uploaded together hand their ``batch_id`` to the combined file."""
        _service("save_combined_file")
        batch = str(uuid.uuid4())
        custody, cash = _upload("custody", batch_id=batch), _upload("cash", batch_id=batch)

        combined, _ = _save_combined(fake_plugin, ("custody", custody), ("cash", cash))

        assert combined.batch_id == batch
        assert _info(combined.file_id).batch_id == batch

    @pytest.mark.parametrize("cash_has_batch", [pytest.param(True, id="two-batches"), pytest.param(False, id="cash-without-batch")])
    def test_mixed_batches_give_no_batch_id(self, isolated_brim_dir: Path, fake_plugin: BRIMProvider, cash_has_batch: bool) -> None:
        """Members that do not share one ``batch_id`` give the combined file none."""
        _service("save_combined_file")
        custody = _upload("custody", batch_id=str(uuid.uuid4()))
        cash = _upload("cash", batch_id=str(uuid.uuid4()) if cash_has_batch else None)

        combined, _ = _save_combined(fake_plugin, ("custody", custody), ("cash", cash))

        assert combined.batch_id is None
        assert _info(combined.file_id).batch_id is None

    def test_signature_is_keyword_only(self) -> None:
        """Every argument is keyword-only, and ``user_id`` is optional."""
        parameters = inspect.signature(_service("save_combined_file")).parameters
        expected = ("broker_id", "plugin_code", "plugin_version", "members", "table", "filename", "user_id")

        assert {name: parameters[name].kind for name in expected if name in parameters} == dict.fromkeys(expected, inspect.Parameter.KEYWORD_ONLY)
        assert parameters["user_id"].default is None


class TestFindReusableCombined:
    """17 — ``find_reusable_combined``: same members, plugin, version and broker means reuse (D-S6)."""

    def test_finds_the_same_member_set_in_any_order(self, isolated_brim_dir: Path, fake_plugin: BRIMProvider) -> None:
        find_reusable_combined = _service("find_reusable_combined")
        custody, cash = _upload("custody"), _upload("cash")
        combined, _ = _save_combined(fake_plugin, ("custody", custody), ("cash", cash))

        for member_ids in ([custody.file_id, cash.file_id], [cash.file_id, custody.file_id]):
            found = find_reusable_combined(broker_id=BROKER_ID, plugin_code=FAKE_CODE, plugin_version=fake_plugin.plugin_version, member_ids=member_ids)
            assert found is not None, f"no reusable combined for {member_ids}"
            assert (found.file_id, found.kind) == (combined.file_id, "combined")

    def test_nothing_to_reuse_before_the_first_combine(self, isolated_brim_dir: Path, fake_plugin: BRIMProvider) -> None:
        find_reusable_combined = _service("find_reusable_combined")
        custody, cash = _upload("custody"), _upload("cash")

        assert find_reusable_combined(broker_id=BROKER_ID, plugin_code=FAKE_CODE, plugin_version=fake_plugin.plugin_version, member_ids=[custody.file_id, cash.file_id]) is None

    @pytest.mark.parametrize("change", ["fewer-members", "more-members", "other-version", "other-plugin", "other-broker"])
    def test_no_reuse_when_anything_differs(self, isolated_brim_dir: Path, fake_plugin: BRIMProvider, change: str) -> None:
        """Presence first (the unchanged query finds it), so each ``None`` is caused by the one thing that changed."""
        find_reusable_combined = _service("find_reusable_combined")
        custody, cash, extra = _upload("custody"), _upload("cash"), _upload("cash")
        _save_combined(fake_plugin, ("custody", custody), ("cash", cash))
        query = {"broker_id": BROKER_ID, "plugin_code": FAKE_CODE, "plugin_version": fake_plugin.plugin_version, "member_ids": [custody.file_id, cash.file_id]}
        assert find_reusable_combined(**query) is not None, "presence barrier: the unchanged query must find the combined file"
        changes = {
            "fewer-members": {"member_ids": [custody.file_id]},
            "more-members": {"member_ids": [custody.file_id, cash.file_id, extra.file_id]},
            "other-version": {"plugin_version": "9.9.9-other"},
            "other-plugin": {"plugin_code": "broker_generic_csv"},
            "other-broker": {"broker_id": OTHER_BROKER_ID},
        }

        assert find_reusable_combined(**{**query, **changes[change]}) is None

    def test_signature_is_keyword_only(self) -> None:
        parameters = inspect.signature(_service("find_reusable_combined")).parameters
        expected = ("broker_id", "plugin_code", "plugin_version", "member_ids")

        assert {name: parameters[name].kind for name in expected if name in parameters} == dict.fromkeys(expected, inspect.Parameter.KEYWORD_ONLY)


class TestCombineIsStale:
    """18 — ``combine_is_stale``: a combined file built by another version of its plugin."""

    def test_fresh_combined_is_not_stale(self, isolated_brim_dir: Path, fake_plugin: BRIMProvider) -> None:
        _require_fields(BRIMFileInfo, "combine_is_stale")
        custody, cash = _upload("custody"), _upload("cash")

        combined, _ = _save_combined(fake_plugin, ("custody", custody), ("cash", cash))

        assert (combined.combine_is_stale, _info(combined.file_id).combine_is_stale, _listed(combined.file_id).combine_is_stale) == (False, False, False)

    def test_plugin_version_bump_makes_it_stale(self, isolated_brim_dir: Path, fake_plugin: BRIMProvider, monkeypatch: pytest.MonkeyPatch) -> None:
        _require_fields(BRIMFileInfo, "combine_is_stale")
        custody, cash = _upload("custody"), _upload("cash")
        combined, _ = _save_combined(fake_plugin, ("custody", custody), ("cash", cash))

        monkeypatch.setattr(_FakeTwoRoleProvider, "plugin_version", "2.0.0-stale-test")

        assert BRIMProviderRegistry.get_provider_instance(FAKE_CODE).plugin_version == "2.0.0-stale-test"
        assert _info(combined.file_id).combine_is_stale is True
        assert _listed(combined.file_id).combine_is_stale is True

    def test_combined_saved_with_another_version_is_stale(self, isolated_brim_dir: Path, fake_plugin: BRIMProvider) -> None:
        """The comparison is with the registered plugin's current version, whichever side is older."""
        _require_fields(BRIMFileInfo, "combine_is_stale")
        custody, cash = _upload("custody"), _upload("cash")

        combined, _ = _save_combined(fake_plugin, ("custody", custody), ("cash", cash), plugin_version="0.9.0")

        assert _info(combined.file_id).combine_is_stale is True

    def test_originals_are_never_combine_stale(self, isolated_brim_dir: Path, fake_plugin: BRIMProvider, monkeypatch: pytest.MonkeyPatch) -> None:
        _require_fields(BRIMFileInfo, "combine_is_stale")
        custody, cash = _upload("custody"), _upload("cash")
        _save_combined(fake_plugin, ("custody", custody), ("cash", cash))

        monkeypatch.setattr(_FakeTwoRoleProvider, "plugin_version", "2.0.0-stale-test")

        for member in (custody, cash):
            assert (_info(member.file_id).combine_is_stale, _listed(member.file_id).combine_is_stale) == (False, False)


class TestDeleteFileLinks:
    """19 — ``delete_file`` keeps the links honest: a combined file outlives its originals (A17)."""

    def test_deleting_an_original_marks_it_deleted_in_every_combined(self, isolated_brim_dir: Path, fake_plugin: BRIMProvider) -> None:
        """Both combined files stay readable; only the deleted original's ref changes, role and name kept."""
        _require_fields(BRIMFileInfo, "derived_from", "combined_into")
        custody, cash = _upload("custody"), _upload("cash")
        first, _ = _save_combined(fake_plugin, ("custody", custody), ("cash", cash))
        second, _ = _save_combined(fake_plugin, ("custody", custody), ("cash", cash), plugin_version="1.1.0")

        assert brim_provider.delete_file(custody.file_id) is True

        assert brim_provider.get_file_info(custody.file_id) is None
        for combined in (first, second):
            info = _info(combined.file_id)
            refs = {ref.file_id: ref for ref in info.derived_from}
            assert (info.kind, set(refs)) == ("combined", {custody.file_id, cash.file_id})
            assert (refs[custody.file_id].deleted, refs[custody.file_id].role, refs[custody.file_id].filename) == (True, "custody", "custody.csv")
            assert refs[cash.file_id].deleted is False
            assert brim_provider.get_file_path(combined.file_id) is not None
        assert _info(cash.file_id).combined_into == [first.file_id, second.file_id]

    def test_deleting_a_combined_unlinks_it_from_its_members(self, isolated_brim_dir: Path, fake_plugin: BRIMProvider) -> None:
        """Only its own id leaves the members' ``combined_into``; the other combined file is untouched."""
        _require_fields(BRIMFileInfo, "derived_from", "combined_into")
        custody, cash = _upload("custody"), _upload("cash")
        first, _ = _save_combined(fake_plugin, ("custody", custody), ("cash", cash))
        second, _ = _save_combined(fake_plugin, ("custody", custody), ("cash", cash), plugin_version="1.1.0")

        assert brim_provider.delete_file(first.file_id) is True

        assert (brim_provider.get_file_info(first.file_id), brim_provider.get_file_path(first.file_id)) == (None, None)
        for member in (custody, cash):
            assert _info(member.file_id).combined_into == [second.file_id]
            assert _sidecar(isolated_brim_dir, member.file_id)["combined_into"] == [second.file_id]
        assert _info(second.file_id).derived_from == _refs(("custody", custody), ("cash", cash))


class TestListFilesReportSetFields:
    """20 — ``list_files`` shows the new fields for originals, combined files and legacy sidecars alike."""

    def test_lists_kinds_batches_and_links(self, isolated_brim_dir: Path, fake_plugin: BRIMProvider) -> None:
        _require_fields(BRIMFileInfo, *NEW_FILE_INFO_FIELDS)
        batch = str(uuid.uuid4())
        custody, cash = _upload("custody", batch_id=batch), _upload("cash", batch_id=batch)
        combined, _ = _save_combined(fake_plugin, ("custody", custody), ("cash", cash))
        legacy_id = _write_legacy_file(isolated_brim_dir)

        listed = {info.file_id: info for info in brim_provider.list_files(broker_ids=[BROKER_ID])}

        assert {custody.file_id, cash.file_id, combined.file_id, legacy_id} <= set(listed)
        for member in (custody, cash):
            info = listed[member.file_id]
            assert (info.kind, info.batch_id, info.derived_from, info.combined_into, info.combine_is_stale) == ("original", batch, [], [combined.file_id], False)
        info = listed[combined.file_id]
        assert (info.kind, info.batch_id, info.combined_into, info.combine_is_stale) == ("combined", batch, [], False)
        assert info.derived_from == _refs(("custody", custody), ("cash", cash))
        legacy = listed[legacy_id]
        assert (legacy.kind, legacy.batch_id, legacy.derived_from, legacy.combined_into, legacy.combine_is_stale) == ("original", None, [], [], False)


# =============================================================================
# PHASE A2 — data, plugin variants, helpers and fixtures
# =============================================================================

A2 = "A2"
SETS_MODULE = "backend.app.services.brim_report_sets"
HISTORY_TAG = "danske_bank"
OTHER_ACCOUNT = "fake-custody-account-0002"
FAKE_PROVIDER_NAME = "Fake two-role report set (tests)"
# Member names a combined file must never repeat (design §3.4.4: Danske's CSV name carries the IBAN).
CUSTODY_NAME = "custody-export-4711.csv"
CASH_NAME = "cash-statement-4711.csv"
# Every set error: its HTTP status and its stable code.
SET_ERRORS = {
    "BRIMSetPluginNotFound": (404, "plugin_not_found"),
    "BRIMSetPluginNotASet": (400, "plugin_not_a_set"),
    "BRIMSetMembersNotFound": (404, "members_not_found"),
    "BRIMSetIncomplete": (422, "set_incomplete"),
}
COVERAGE_CODES = {"coverage_starts_late", "coverage_ends_early"}


def _custody_csv(*trade_dates: str, account: Optional[str] = None) -> bytes:
    """A synthetic custody export, one trade per date; ``account`` adds the ``account=<id>`` header cell."""
    header = [CUSTODY_MARKER, *CUSTODY_COLUMNS, *([f"account={account}"] if account else [])]
    return "".join(f"{line}\n" for line in [";".join(header), *(f"row;{day};ACME Oyj;1" for day in trade_dates)]).encode()


def _cash_csv(*value_dates: str) -> bytes:
    """A synthetic cash export, one movement per value date."""
    header = [CASH_MARKER, *CASH_COLUMNS]
    return "".join(f"{line}\n" for line in [";".join(header), *(f"row;{day};-1.00;EUR;Liike {day}" for day in value_dates)]).encode()


# The spans every A2 test reasons about: custody on the trade axis, cash on the value axis.
CUSTODY_JAN = _custody_csv("2025-01-02", "2025-01-15")
CUSTODY_MAR = _custody_csv("2025-03-03", "2025-03-20")
CASH_JAN = _cash_csv("2025-01-01", "2025-01-06", "2025-01-17")  # covers CUSTODY_JAN from its eve to past its end
CASH_JAN_MAR = _cash_csv("2025-01-01", "2025-02-10", "2025-03-20")  # covers both custody spans
JAN_SEGMENT = DateRangeModel(start=date(2025, 1, 2), end=date(2025, 1, 15))
MAR_SEGMENT = DateRangeModel(start=date(2025, 3, 3), end=date(2025, 3, 20))


class _FakeSingleCustodyProvider(_FakeTwoRoleProvider):
    """The fake with a custody role that takes one file only (``multiple=False``)."""

    @property
    def report_roles(self) -> List[Any]:
        role = _schema("BRIMReportRole")
        return [
            role(code="custody", required=True, multiple=False, extensions=[".csv"], description="Fake custody export, one file per set"),
            role(code="cash", required=True, multiple=True, extensions=[".csv"], description="Fake cash export", must_cover="custody"),
        ]


class _FakeOptionalRoleProvider(_FakeTwoRoleProvider):
    """The fake plus an optional third role that no file ever fills."""

    @property
    def report_roles(self) -> List[Any]:
        role = _schema("BRIMReportRole")
        return [*super().report_roles, role(code="statement", required=False, multiple=False, extensions=[".csv"], description="Fake optional statement")]


class _FakeNoShapeProvider(_FakeTwoRoleProvider):
    """The fake whose set description proves no segment at all."""

    def describe_set(self, members: Dict[str, List[Path]]) -> Any:
        return _schema("BRIMSetShape")()


class _FakeBankProvider(_FakeTwoRoleProvider):
    """The fake under a ``broker_`` code, so its history tag (``fake_bank``) differs from its code."""

    @property
    def provider_code(self) -> str:
        return "broker_fake_bank"


class _FakeBankImportPolicyProvider(_FakeBankProvider):
    """``_FakeBankProvider`` importing the rows before its first checkpoint (policy ``import``, as CA will)."""

    @property
    def pre_checkpoint_policy(self) -> str:
        return "import"


class _FakeInfixProvider(_FakeTwoRoleProvider):
    """A code with ``broker_`` in the middle: only a leading ``broker_`` is dropped."""

    @property
    def provider_code(self) -> str:
        return "fake_broker_bank"


def _sets_module() -> Optional[ModuleType]:
    """The new service module, or None while it does not exist. An import error *inside* it is not swallowed."""
    try:
        return importlib.import_module(SETS_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != SETS_MODULE:
            raise
        return None


def _sets(name: str) -> Any:
    """A function or exception of the new service module ``backend.app.services.brim_report_sets``."""
    module = _sets_module()
    if module is None:
        _missing(f"{SETS_MODULE} does not exist", A2)
    found = getattr(module, name, None)
    if found is None:
        _missing(f"{SETS_MODULE}.{name} does not exist", A2)
    return found


def _member(content: bytes, filename: str, *, batch_id: Optional[str] = None, broker_id: int = BROKER_ID) -> BRIMFileInfo:
    """Store one synthetic export through the real ``save_uploaded_file``, as ``POST /upload`` does."""
    return brim_provider.save_uploaded_file(content, filename, user_id=USER_ID, broker_id=broker_id, batch_id=batch_id)


def _rewrite_sidecar(root: Path, file_id: str, **changes: Any) -> None:
    """Overwrite keys of an uploaded file's sidecar, as if it had been stored differently (e.g. at another time)."""
    path = root / BRIMFileStatus.UPLOADED.value / f"broker_{BROKER_ID}" / f"{file_id}.json"
    metadata = json.loads(path.read_text())
    metadata.update(changes)
    path.write_text(json.dumps(metadata, indent=2))


def _file_info(kind: str) -> BRIMFileInfo:
    """A stored-file description of the given kind, for the parse guard (which never opens the file)."""
    return BRIMFileInfo(file_id="f-1", filename="custody.csv", size_bytes=10, status=BRIMFileStatus.UPLOADED, uploaded_at=UPLOADED_AT, compatible_plugins=[FAKE_CODE], target_broker_id=BROKER_ID, kind=kind)


def _codes(preview: Any) -> List[str]:
    """The notice codes of a preview's warnings, in order."""
    return [notice.code for notice in preview.warnings]


def _roles(preview: Any) -> Dict[str, Any]:
    """The preview's role statuses, by role code."""
    return {role.code: role for role in preview.roles}


def _preview(plugin: BRIMProvider, members: Sequence[BRIMFileInfo], *, history_start: Optional[date] = None, gap_fix_dates: Sequence[date] = ()) -> Any:
    """``build_preview`` for the fake's code on ``BROKER_ID``, in batch ``batch-a2``."""
    build_preview = _sets("build_preview")
    return build_preview(plugin, list(members), broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id="batch-a2", history_start=history_start, gap_fix_dates=list(gap_fix_dates))


def _combined_files() -> List[BRIMFileInfo]:
    """Every combined file of ``BROKER_ID`` in the isolated storage (a collection each test owns entirely)."""
    return [info for info in brim_provider.list_files(broker_ids=[BROKER_ID]) if info.target_broker_id == BROKER_ID and info.kind == "combined"]


# Phase F2 (plan F2.0, U2-B): the preview also says where the history LibreFolio holds ends
# (``history_end``) and how many transactions it has (``history_count``), for the timeline.
F2 = "F2"
HISTORY_FIELDS = ("history_end", "history_count")


def _require_history_fields() -> Any:
    """``BRIMSetPreview``, failing the test (not the collection) while it lacks the two F2 fields."""
    set_preview = _schema("BRIMSetPreview", A2)
    absent = [name for name in HISTORY_FIELDS if name not in set_preview.model_fields]
    if absent:
        _missing(f"BRIMSetPreview has no field {', '.join(absent)}", F2)
    return set_preview


async def _seed_history(session: AsyncSession, rows: Sequence[Tuple[int, date, Optional[str]]]) -> None:
    """Both brokers, and one transaction per ``(broker_id, date, tags)``; ``tags`` exactly as stored (comma-separated)."""
    for broker_id in sorted({BROKER_ID, OTHER_BROKER_ID, *(row[0] for row in rows)}):
        session.add(Broker(id=broker_id, name=f"Report-set broker {broker_id}"))
    for broker_id, day, tags in rows:
        session.add(Transaction(broker_id=broker_id, type=TransactionType.DEPOSIT, date=day, amount=Decimal("1"), currency="EUR", tags=tags))
    await session.commit()


def _parse_output(*, transactions: Sequence[str] = (), checkpoints: Sequence[Tuple[str, str]] = (), verifications: Sequence[str] = ()) -> BRIMParseOutput:
    """A parse output of a combined file: deposits on the given dates, checkpoints ``(as_of, kind)`` and verifications."""
    checkpoint, verification = _schema("BRIMCheckpoint"), _schema("BRIMVerification")
    return BRIMParseOutput(
        transactions=[TXCreateItem(broker_id=BROKER_ID, type=TransactionType.DEPOSIT, date=date.fromisoformat(day), cash=Currency(code="EUR", amount=Decimal("10"))) for day in transactions],
        checkpoints=[checkpoint(as_of=date.fromisoformat(as_of), kind=kind) for as_of, kind in checkpoints],
        verifications=[verification(as_of=date.fromisoformat(as_of)) for as_of in verifications],
    )


@pytest.fixture
def set_storage(isolated_brim_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """``isolated_brim_dir``, extended to the set service should it keep its own reference to the storage root."""
    module = _sets_module()
    if module is not None and hasattr(module, "get_broker_reports_dir"):
        monkeypatch.setattr(module, "get_broker_reports_dir", lambda: isolated_brim_dir)
    return isolated_brim_dir


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """A private in-memory SQLite database with the ORM schema, for H0: never the shared test database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


# =============================================================================
# A2 · A — CONTRACT: history_tag
# =============================================================================


class TestHistoryTag:
    """A — ``BRIMProvider.history_tag``: the tag H0 looks for; by default the code without a leading ``broker_``."""

    def test_real_plugin(self) -> None:
        _require_contract("history_tag", phase=A2)

        assert BRIMProviderRegistry.get_provider_instance("broker_credit_agricole").history_tag == "credit_agricole"

    def test_every_existing_plugin_gets_the_default(self) -> None:
        """None of the 30 single-file plugins overrides it."""
        _require_contract("history_tag", phase=A2)

        tags = {code: BRIMProviderRegistry.get_provider_instance(code).history_tag for code in EXISTING_PLUGIN_CODES}

        assert tags == {code: code.removeprefix("broker_") for code in EXISTING_PLUGIN_CODES}

    def test_fake_without_the_prefix_keeps_its_code(self, fake_plugin: BRIMProvider) -> None:
        _require_contract("history_tag", phase=A2)

        assert fake_plugin.history_tag == FAKE_CODE

    @pytest.mark.parametrize(("provider", "expected"), [pytest.param(_FakeBankProvider, "fake_bank", id="leading-prefix-dropped"), pytest.param(_FakeInfixProvider, "fake_broker_bank", id="infix-kept")])
    def test_only_a_leading_prefix_is_dropped(self, provider: type, expected: str) -> None:
        _require_contract("history_tag", phase=A2)

        assert provider().history_tag == expected


# =============================================================================
# A2 · B — SCHEMAS
# =============================================================================


class TestSetSchemas:
    """B — the request and response schemas of ``POST /sets/preview`` and ``POST /sets/combine``."""

    FILE_INFO = {"file_id": "c-1", "filename": "combined.csv", "size_bytes": 10, "status": "uploaded", "uploaded_at": "2026-09-30T12:00:00+00:00"}

    @pytest.mark.parametrize(
        ("name", "valid"),
        [
            pytest.param("BRIMSetRequest", {"broker_id": 7, "plugin_code": FAKE_CODE, "batch_id": "b-1"}, id="BRIMSetRequest"),
            pytest.param("BRIMSetMemberInfo", {"file_id": "f-1", "filename": "custody.csv"}, id="BRIMSetMemberInfo"),
            pytest.param("BRIMSetRoleStatus", {"code": "cash", "required": True, "multiple": True, "status": "present"}, id="BRIMSetRoleStatus"),
            pytest.param("BRIMSetMissing", {"role": "cash"}, id="BRIMSetMissing"),
            pytest.param("BRIMSetPreview", {"broker_id": 7, "plugin_code": FAKE_CODE, "batch_id": "b-1"}, id="BRIMSetPreview"),
            pytest.param("BRIMSetCombineResponse", {"combined": FILE_INFO}, id="BRIMSetCombineResponse"),
        ],
    )
    def test_rejects_an_unknown_key(self, name: str, valid: Dict[str, Any]) -> None:
        """Every one is a ``StrictModel``: the baseline payload is valid, the same plus one unknown key is not."""
        model = _schema(name, A2)
        model.model_validate(valid)

        with pytest.raises(ValidationError):
            model.model_validate({**valid, "unexpected_key": "x"})

    @pytest.mark.parametrize("missing", ["broker_id", "plugin_code", "batch_id"])
    def test_request_fields_are_required(self, missing: str) -> None:
        set_request = _schema("BRIMSetRequest", A2)
        payload = {"broker_id": 7, "plugin_code": FAKE_CODE, "batch_id": "b-1"}
        # The three fields sent, compared alone: phase G adds ``exclude_file_ids`` with an empty default.
        assert set_request.model_validate(payload).model_dump(include=set(payload)) == payload
        del payload[missing]

        with pytest.raises(ValidationError):
            set_request.model_validate(payload)

    @pytest.mark.parametrize("broker_id", [0, -1])
    def test_request_broker_id_is_positive(self, broker_id: int) -> None:
        set_request = _schema("BRIMSetRequest", A2)

        with pytest.raises(ValidationError):
            set_request(broker_id=broker_id, plugin_code=FAKE_CODE, batch_id="b-1")

    def test_member_info_defaults_and_coverage(self) -> None:
        """A member whose role is unknown has no rows and no coverage; a recognised one carries typed spans."""
        member_info, coverage = _schema("BRIMSetMemberInfo", A2), _schema("BRIMCoverage")

        bare = member_info(file_id="f-1", filename="custody.csv")
        full = member_info.model_validate({"file_id": "f-2", "filename": "cash.csv", "role": "cash", "rows": 3, "coverage": [{"axis": "value", "start": "2025-01-01", "end": "2025-01-17"}]})

        assert (bare.role, bare.rows, bare.coverage) == (None, 0, [])
        assert full.coverage == [coverage(axis="value", start=date(2025, 1, 1), end=date(2025, 1, 17))]

    @pytest.mark.parametrize("status", ["present", "missing", "excess"])
    def test_role_status_values(self, status: str) -> None:
        role_status = _schema("BRIMSetRoleStatus", A2)(code="cash", required=True, multiple=False, status=status)

        assert (role_status.status, role_status.file_ids) == (status, [])

    def test_role_status_rejects_other_values(self) -> None:
        role_status = _schema("BRIMSetRoleStatus", A2)

        with pytest.raises(ValidationError):
            role_status(code="cash", required=True, multiple=False, status="partial")

    def test_missing_has_no_period_by_default(self) -> None:
        missing = _schema("BRIMSetMissing", A2)(role="custody")

        assert (missing.role, missing.start, missing.end) == ("custody", None, None)

    def test_preview_defaults(self) -> None:
        """Nothing known yet: no member, no role, nothing missing, no span, no H0, not complete."""
        preview = _schema("BRIMSetPreview", A2)(broker_id=7, plugin_code=FAKE_CODE, batch_id="b-1")

        assert (preview.members, preview.roles, preview.missing, preview.segments, preview.gaps, preview.history_start, preview.warnings, preview.complete) == ([], [], [], [], [], None, [], False)

    def test_preview_round_trips_through_json(self) -> None:
        set_preview = _schema("BRIMSetPreview", A2)
        payload = {
            "broker_id": 7,
            "plugin_code": FAKE_CODE,
            "batch_id": "b-1",
            "members": [{"file_id": "f-1", "filename": "custody.csv", "role": "custody", "rows": 2, "coverage": [{"axis": "trade", "start": "2025-01-02", "end": "2025-01-15"}]}],
            "roles": [{"code": "custody", "required": True, "multiple": True, "status": "present", "file_ids": ["f-1"]}, {"code": "cash", "required": True, "multiple": True, "status": "missing"}],
            "missing": [{"role": "cash", "start": "2025-01-01", "end": "2025-01-15"}],
            "segments": [{"start": "2025-01-02", "end": "2025-01-15"}],
            "gaps": [],
            "history_start": "2025-01-02",
            "warnings": [{"severity": "warning", "code": "coverage_starts_late", "message": "Cash starts late", "context": {"role": "cash", "covered_role": "custody", "date": "2025-01-01"}}],
            "complete": False,
        }

        preview = set_preview.model_validate(payload)

        assert set_preview.model_validate_json(preview.model_dump_json()) == preview
        assert preview.segments == [JAN_SEGMENT]
        assert (preview.missing[0].start, preview.history_start) == (date(2025, 1, 1), date(2025, 1, 2))
        assert all(isinstance(notice, BRIMNotice) for notice in preview.warnings)

    def test_combine_response_defaults(self) -> None:
        response = _schema("BRIMSetCombineResponse", A2).model_validate({"combined": self.FILE_INFO})

        assert isinstance(response.combined, BRIMFileInfo)
        assert (response.combined.file_id, response.summary, response.reused) == ("c-1", {}, False)

    def test_preview_history_end_and_count_default_to_no_history(self) -> None:
        """F2 (U2-B): a preview built without them has no history end and counts nothing."""
        set_preview = _require_history_fields()

        preview = set_preview(broker_id=7, plugin_code=FAKE_CODE, batch_id="b-1")

        assert (preview.history_start, preview.history_end, preview.history_count) == (None, None, 0)

    def test_preview_history_end_and_count_are_typed_round_trip_and_stay_strict(self) -> None:
        """F2 (U2-B): the end is a date, the count an int; both survive JSON, and an unknown key is still refused."""
        set_preview = _require_history_fields()
        payload = {"broker_id": 7, "plugin_code": FAKE_CODE, "batch_id": "b-1", "history_start": "2025-01-08", "history_end": "2025-03-15", "history_count": 4}

        preview = set_preview.model_validate(payload)

        assert (preview.history_start, preview.history_end, preview.history_count) == (date(2025, 1, 8), date(2025, 3, 15), 4)
        assert set_preview.model_validate_json(preview.model_dump_json()) == preview
        with pytest.raises(ValidationError):
            set_preview.model_validate({**payload, "history_rows": 4})


# =============================================================================
# A2 · C — STORAGE: read_combine_summary
# =============================================================================


class TestReadCombineSummary:
    """C — ``read_combine_summary``: the combine summary kept in a combined file's sidecar, ``{}`` for anything else."""

    def test_combined_file_gives_its_summary(self, isolated_brim_dir: Path, fake_plugin: BRIMProvider) -> None:
        read_combine_summary = _service("read_combine_summary", A2)
        custody, cash = _upload("custody"), _upload("cash")
        combined, table = _save_combined(fake_plugin, ("custody", custody), ("cash", cash))
        assert table.summary, "precondition: the fake's combine summary is not empty"

        assert read_combine_summary(combined.file_id) == table.summary

    def test_original_gives_an_empty_summary(self, isolated_brim_dir: Path, fake_plugin: BRIMProvider) -> None:
        """Even an original that already went into a combined file."""
        read_combine_summary = _service("read_combine_summary", A2)
        custody, cash = _upload("custody"), _upload("cash")
        _save_combined(fake_plugin, ("custody", custody), ("cash", cash))

        assert read_combine_summary(custody.file_id) == {}

    def test_unknown_id_gives_an_empty_summary(self, isolated_brim_dir: Path) -> None:
        read_combine_summary = _service("read_combine_summary", A2)

        assert read_combine_summary(str(uuid.uuid4())) == {}


# =============================================================================
# A2 · D — SERVICE: errors and plugin lookup
# =============================================================================


class TestSetErrors:
    """D — one ``BRIMSetError`` family; each error carries its HTTP status and its stable code (asserted where raised)."""

    def test_family(self) -> None:
        base = _sets("BRIMSetError")

        assert issubclass(base, Exception)
        assert {name: issubclass(_sets(name), base) for name in SET_ERRORS} == dict.fromkeys(SET_ERRORS, True)


class TestGetSetPlugin:
    """D1 — ``get_set_plugin``: only a registered plugin that declares report roles."""

    def test_unknown_code(self) -> None:
        get_set_plugin = _sets("get_set_plugin")

        with pytest.raises(_sets("BRIMSetPluginNotFound")) as caught:
            get_set_plugin("no_such_plugin_a2")

        assert (caught.value.status_code, caught.value.code) == SET_ERRORS["BRIMSetPluginNotFound"]

    def test_single_file_plugin(self) -> None:
        get_set_plugin = _sets("get_set_plugin")

        with pytest.raises(_sets("BRIMSetPluginNotASet")) as caught:
            get_set_plugin("broker_generic_csv")

        assert (caught.value.status_code, caught.value.code) == SET_ERRORS["BRIMSetPluginNotASet"]

    def test_report_set_plugin(self, fake_plugin: BRIMProvider) -> None:
        get_set_plugin = _sets("get_set_plugin")

        plugin = get_set_plugin(FAKE_CODE)

        assert isinstance(plugin, _FakeTwoRoleProvider)
        assert plugin.provider_code == FAKE_CODE


# =============================================================================
# A2 · D2 — SERVICE: collect_members
# =============================================================================


class TestCollectMembers:
    """D2 — ``collect_members``: the set is one upload for one broker and one plugin (D-S22), never the rest of the archive (A16)."""

    def test_collects_the_originals_of_one_upload(self, set_storage: Path, fake_plugin: BRIMProvider) -> None:
        """Each distractor shares something with the set and none belongs to it; a member already parsed by another plugin still does."""
        collect_members = _sets("collect_members")
        batch = str(uuid.uuid4())
        custody = _member(CUSTODY_JAN, CUSTODY_NAME, batch_id=batch)
        cash = _member(CASH_JAN, CASH_NAME, batch_id=batch)
        _member(CUSTODY_MAR, "custody-other-broker.csv", batch_id=batch, broker_id=OTHER_BROKER_ID)
        _member(CUSTODY_MAR, "custody-other-batch.csv", batch_id=str(uuid.uuid4()))
        _member(CUSTODY_MAR, "custody-no-batch.csv")
        other_plugin = _member(GENERIC_CSV, "generic.csv", batch_id=batch)
        failed = _member(CUSTODY_MAR, "custody-failed.csv", batch_id=batch)
        assert brim_provider.move_to_failed(failed.file_id, "synthetic failure")
        combined, _ = _save_combined(fake_plugin, ("custody", custody), ("cash", cash))
        assert brim_provider.move_to_parsed(cash.file_id)
        assert FAKE_CODE not in other_plugin.compatible_plugins, "precondition: the fake does not read the generic CSV"
        assert _info(combined.file_id).batch_id == batch, "precondition: the combined file shares the upload's batch"

        members = collect_members(broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch)

        assert {member.file_id for member in members} == {custody.file_id, cash.file_id}
        assert len(members) == 2, [member.filename for member in members]
        assert all(isinstance(member, BRIMFileInfo) and member.kind == "original" for member in members)

    def test_orders_by_upload_time_then_filename(self, set_storage: Path, fake_plugin: BRIMProvider) -> None:
        """Earliest upload first; on the same instant, by filename. The first by name is the last by time."""
        collect_members = _sets("collect_members")
        batch = str(uuid.uuid4())
        latest = _member(CASH_JAN_MAR, "a-cash.csv", batch_id=batch)
        tie_b = _member(CUSTODY_JAN, "b-custody.csv", batch_id=batch)
        tie_a = _member(CUSTODY_MAR, "a-custody.csv", batch_id=batch)
        _rewrite_sidecar(set_storage, latest.file_id, uploaded_at="2026-09-30T12:00:00+00:00")
        _rewrite_sidecar(set_storage, tie_b.file_id, uploaded_at="2026-09-30T11:00:00+00:00")
        _rewrite_sidecar(set_storage, tie_a.file_id, uploaded_at="2026-09-30T11:00:00+00:00")

        members = collect_members(broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch)

        assert [member.file_id for member in members] == [tie_a.file_id, tie_b.file_id, latest.file_id]

    @pytest.mark.parametrize("scenario", ["unknown-batch", "only-non-members"])
    def test_no_member_raises(self, set_storage: Path, fake_plugin: BRIMProvider, scenario: str) -> None:
        collect_members = _sets("collect_members")
        members_not_found = _sets("BRIMSetMembersNotFound")
        batch = str(uuid.uuid4())
        if scenario == "only-non-members":
            _member(GENERIC_CSV, "generic.csv", batch_id=batch)
            _member(CUSTODY_JAN, "custody-other-broker.csv", batch_id=batch, broker_id=OTHER_BROKER_ID)
            failed = _member(CUSTODY_JAN, "custody-failed.csv", batch_id=batch)
            assert brim_provider.move_to_failed(failed.file_id, "synthetic failure")

        with pytest.raises(members_not_found) as caught:
            collect_members(broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch)

        assert (caught.value.status_code, caught.value.code) == SET_ERRORS["BRIMSetMembersNotFound"]


# =============================================================================
# A2 · D3 — SERVICE: history_start (H0, D-S25)
# =============================================================================


def _own(day: str, tags: Optional[str]) -> Tuple[int, date, Optional[str]]:
    """A transaction of the broker whose H0 is asked for."""
    return (BROKER_ID, date.fromisoformat(day), tags)


def _foreign(day: str, tags: Optional[str]) -> Tuple[int, date, Optional[str]]:
    """A transaction of another broker: never part of this broker's history."""
    return (OTHER_BROKER_ID, date.fromisoformat(day), tags)


# (transactions in the database, expected H0 for BROKER_ID and tag "danske_bank")
HISTORY_CASES = [
    pytest.param([], None, id="empty-broker"),
    pytest.param([_own("2024-06-01", None), _own("2024-07-01", "manual")], None, id="manual-history-without-the-tag"),
    pytest.param([_own("2025-03-10", "import,danske_bank"), _own("2025-01-02", "danske_bank,import"), _own("2025-02-01", "danske_bank")], date(2025, 1, 2), id="oldest-tagged-row-any-tag-position"),
    pytest.param([_own("2024-01-01", None), _own("2024-02-01", "import"), _own("2025-01-02", "import,danske_bank")], date(2025, 1, 2), id="older-rows-without-the-tag-do-not-count"),
    pytest.param([_own("2024-12-31", "import,danske_bank,gap_fix"), _own("2025-01-02", "import,danske_bank")], date(2025, 1, 1), id="gap-fix-counts-from-the-next-day"),
    pytest.param([_own("2024-12-31", "import,danske_bank,gap_fix")], date(2025, 1, 1), id="gap-fix-alone"),
    pytest.param([_own("2024-12-31", "import,danske_bank,gap_fix"), _own("2024-12-31", "import,danske_bank")], date(2024, 12, 31), id="row-on-the-gap-fix-day-wins"),
    pytest.param([_own("2025-01-02", "import,danske_bank"), _own("2025-06-30", "import,danske_bank,gap_fix")], date(2025, 1, 2), id="later-gap-fix-does-not-move-it"),
    pytest.param([_own("2024-06-30", "import,credit_agricole,gap_fix"), _own("2025-01-02", "import,danske_bank")], date(2025, 1, 2), id="another-plugins-gap-fix-does-not-count"),
    pytest.param([_own("2024-01-01", "import,danske_bank_old"), _own("2024-02-01", "old_danske_bank"), _own("2024-03-01", "import,danske_bankx"), _own("2025-01-02", "import,danske_bank")], date(2025, 1, 2), id="exact-tag-only"),
    pytest.param([_own("2024-01-01", "danske_bank_old,import"), _own("2024-02-01", "xdanske_bank")], None, id="near-miss-tags-alone"),
    pytest.param([_foreign("2023-01-01", "import,danske_bank"), _foreign("2023-01-01", "import,danske_bank,gap_fix"), _own("2025-01-02", "import,danske_bank")], date(2025, 1, 2), id="other-broker-never-counts"),
    pytest.param([_foreign("2023-01-01", "import,danske_bank")], None, id="other-broker-alone"),
]


class TestHistoryStart:
    """D3 — ``history_start``: the first day LibreFolio already has this plugin's history for the broker (D-S25, A2, A3, A14)."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("rows", "expected"), HISTORY_CASES)
    async def test_cases(self, db_session: AsyncSession, rows: List[Tuple[int, date, Optional[str]]], expected: Optional[date]) -> None:
        history_start = _sets("history_start")
        await _seed_history(db_session, rows)

        assert await history_start(db_session, broker_id=BROKER_ID, history_tag=HISTORY_TAG) == expected


# =============================================================================
# A2 · D4 — SERVICE: build_preview
# =============================================================================


class TestBuildPreview:
    """D4 — ``build_preview``: what is in the set, read through the plugin without combining (§3.3)."""

    def test_complete_set(self, set_storage: Path, fake_plugin: BRIMProvider) -> None:
        coverage = _schema("BRIMCoverage")
        custody, cash = _member(CUSTODY_JAN, CUSTODY_NAME), _member(CASH_JAN, CASH_NAME)

        preview = _preview(fake_plugin, [custody, cash])

        assert isinstance(preview, _schema("BRIMSetPreview", A2))
        assert (preview.broker_id, preview.plugin_code, preview.batch_id, preview.history_start) == (BROKER_ID, FAKE_CODE, "batch-a2", None)
        members = {member.file_id: member for member in preview.members}
        assert set(members) == {custody.file_id, cash.file_id}
        assert (members[custody.file_id].filename, members[custody.file_id].role, members[custody.file_id].rows) == (CUSTODY_NAME, "custody", 2)
        assert members[custody.file_id].coverage == [coverage(axis="trade", start=date(2025, 1, 2), end=date(2025, 1, 15))]
        assert (members[cash.file_id].filename, members[cash.file_id].role, members[cash.file_id].rows) == (CASH_NAME, "cash", 3)
        assert members[cash.file_id].coverage == [coverage(axis="value", start=date(2025, 1, 1), end=date(2025, 1, 17))]
        roles = _roles(preview)
        assert set(roles) == {"custody", "cash"}
        assert (roles["custody"].required, roles["custody"].multiple, roles["custody"].status, roles["custody"].file_ids) == (True, True, "present", [custody.file_id])
        assert (roles["cash"].required, roles["cash"].multiple, roles["cash"].status, roles["cash"].file_ids) == (True, True, "present", [cash.file_id])
        assert (preview.missing, preview.segments, preview.gaps) == ([], [JAN_SEGMENT], [])
        assert _codes(preview) == [FAKE_SET_NOTICE], "a clean set carries the plugin's notices and nothing from the core"
        assert preview.complete is True

    def test_missing_role_period_comes_from_must_cover(self, set_storage: Path, fake_plugin: BRIMProvider) -> None:
        """Cash must cover custody: ``missing`` asks for it from the eve of the first trade to the last trade, across every custody file."""
        missing = _schema("BRIMSetMissing", A2)
        jan, mar = _member(CUSTODY_JAN, "custody-jan.csv"), _member(CUSTODY_MAR, "custody-mar.csv")

        preview = _preview(fake_plugin, [jan, mar])

        roles = _roles(preview)
        assert (roles["custody"].status, sorted(roles["custody"].file_ids)) == ("present", sorted([jan.file_id, mar.file_id]))
        assert (roles["cash"].status, roles["cash"].file_ids) == ("missing", [])
        assert preview.missing == [missing(role="cash", start=date(2025, 1, 1), end=date(2025, 3, 20))]
        assert preview.complete is False

    def test_incomplete_set_is_not_described(self, set_storage: Path, fake_plugin: BRIMProvider) -> None:
        """``describe_set`` is asked only once every required role is present: before that, no segment, no gap, no plugin notice."""
        preview = _preview(fake_plugin, [_member(CUSTODY_JAN, CUSTODY_NAME)])

        assert (preview.segments, preview.gaps) == ([], [])
        assert FAKE_SET_NOTICE not in _codes(preview)

    def test_missing_role_without_must_cover_has_no_period(self, set_storage: Path, fake_plugin: BRIMProvider) -> None:
        missing = _schema("BRIMSetMissing", A2)

        preview = _preview(fake_plugin, [_member(CASH_JAN, CASH_NAME)])

        assert preview.missing == [missing(role="custody")]
        assert preview.complete is False

    def test_nothing_recognised(self, set_storage: Path, fake_plugin: BRIMProvider) -> None:
        """Without custody the cash period cannot be computed either: both missing roles come without dates."""
        stray = _member(GENERIC_CSV, "generic.csv")

        preview = _preview(fake_plugin, [stray])

        assert {item.role: (item.start, item.end) for item in preview.missing} == {"custody": (None, None), "cash": (None, None)}
        assert [(member.file_id, member.role) for member in preview.members] == [(stray.file_id, None)]
        assert preview.complete is False

    def test_unrecognised_member_is_reported_and_ignored(self, set_storage: Path, fake_plugin: BRIMProvider) -> None:
        """Listed with no role and flagged ``unknown_role`` (context: its file id); completeness is decided without it."""
        custody, cash, stray = _member(CUSTODY_JAN, CUSTODY_NAME), _member(CASH_JAN, CASH_NAME), _member(GENERIC_CSV, "generic.csv")

        preview = _preview(fake_plugin, [custody, cash, stray])

        members = {member.file_id: member for member in preview.members}
        assert (members[stray.file_id].filename, members[stray.file_id].role, members[stray.file_id].rows, members[stray.file_id].coverage) == ("generic.csv", None, 0, [])
        unknown = [notice for notice in preview.warnings if notice.code == "unknown_role"]
        assert [(notice.context or {}).get("file_id") for notice in unknown] == [stray.file_id]
        assert all(stray.file_id not in role.file_ids for role in preview.roles)
        assert preview.complete is True

    def test_two_files_for_a_single_file_role_are_excess(self, set_storage: Path) -> None:
        jan, mar, cash = _member(CUSTODY_JAN, "custody-jan.csv"), _member(CUSTODY_MAR, "custody-mar.csv"), _member(CASH_JAN_MAR, CASH_NAME)

        preview = _preview(_FakeSingleCustodyProvider(), [jan, mar, cash])

        custody = _roles(preview)["custody"]
        assert (custody.multiple, custody.status, sorted(custody.file_ids)) == (False, "excess", sorted([jan.file_id, mar.file_id]))
        assert "excess_files" in _codes(preview)
        assert preview.missing == []
        assert preview.complete is False

    def test_one_file_for_a_single_file_role_is_present(self, set_storage: Path) -> None:
        preview = _preview(_FakeSingleCustodyProvider(), [_member(CUSTODY_JAN, CUSTODY_NAME), _member(CASH_JAN, CASH_NAME)])

        assert _roles(preview)["custody"].status == "present"
        assert "excess_files" not in _codes(preview)
        assert preview.complete is True

    def test_optional_role_may_stay_missing(self, set_storage: Path) -> None:
        """Listed as ``missing``, but ``missing`` names required roles only, and the set is complete without it."""
        preview = _preview(_FakeOptionalRoleProvider(), [_member(CUSTODY_JAN, CUSTODY_NAME), _member(CASH_JAN, CASH_NAME)])

        statement = _roles(preview)["statement"]
        assert (statement.required, statement.status, statement.file_ids) == (False, "missing", [])
        assert preview.missing == []
        assert preview.complete is True

    @pytest.mark.parametrize(
        ("cash_dates", "expected"),
        [
            pytest.param(("2025-01-01", "2025-01-15"), set(), id="from-the-eve-to-the-last-trade"),
            pytest.param(("2024-12-01", "2025-02-28"), set(), id="wider"),
            pytest.param(("2025-01-02", "2025-01-17"), {"coverage_starts_late"}, id="starts-on-the-first-trade-day"),
            pytest.param(("2025-01-06", "2025-01-17"), {"coverage_starts_late"}, id="starts-late"),
            pytest.param(("2025-01-01", "2025-01-14"), {"coverage_ends_early"}, id="ends-the-day-before-the-last-trade"),
            pytest.param(("2025-01-05", "2025-01-10"), {"coverage_starts_late", "coverage_ends_early"}, id="both"),
        ],
    )
    def test_cash_coverage_against_custody(self, set_storage: Path, fake_plugin: BRIMProvider, cash_dates: Tuple[str, str], expected: set) -> None:
        """Cash must cover custody from the eve of its first trade to its last one (``must_cover``): a shortfall warns, it does not block."""
        preview = _preview(fake_plugin, [_member(CUSTODY_JAN, CUSTODY_NAME), _member(_cash_csv(*cash_dates), CASH_NAME)])

        found = [notice for notice in preview.warnings if notice.code in COVERAGE_CODES]
        assert {notice.code for notice in found} == expected
        for notice in found:
            assert notice.context is not None and {"role", "covered_role", "date"} <= set(notice.context), notice.context
            assert (notice.context["role"], notice.context["covered_role"]) == ("cash", "custody")
            assert notice.context["date"] is not None
        assert preview.complete is True

    def test_two_custody_accounts_are_mixed(self, set_storage: Path, fake_plugin: BRIMProvider) -> None:
        """Two deposit accounts in one set: not complete, and neither account number leaves memory (§3.3)."""
        jan = _member(CUSTODY_JAN, "custody-jan.csv")
        mar = _member(_custody_csv("2025-03-03", "2025-03-20", account=OTHER_ACCOUNT), "custody-mar.csv")
        cash = _member(CASH_JAN_MAR, CASH_NAME)
        assert fake_plugin.describe_member(brim_provider.get_file_path(mar.file_id)).account_fingerprint == OTHER_ACCOUNT  # precondition

        preview = _preview(fake_plugin, [jan, mar, cash])

        assert "mixed_accounts" in _codes(preview)
        assert preview.complete is False
        dumped = preview.model_dump_json()
        assert FAKE_ACCOUNT not in dumped and OTHER_ACCOUNT not in dumped

    def test_one_custody_account_is_not_mixed(self, set_storage: Path, fake_plugin: BRIMProvider) -> None:
        preview = _preview(fake_plugin, [_member(CUSTODY_JAN, "custody-jan.csv"), _member(CUSTODY_MAR, "custody-mar.csv"), _member(CASH_JAN_MAR, CASH_NAME)])

        assert "mixed_accounts" not in _codes(preview)
        assert preview.complete is True
        assert FAKE_ACCOUNT not in preview.model_dump_json()

    @pytest.mark.parametrize(
        ("history_start", "flagged"),
        [
            pytest.param(None, 0, id="no-history"),
            pytest.param(date(2025, 1, 15), 0, id="h0-on-the-last-day-of-the-first-segment"),
            pytest.param(date(2025, 1, 16), 1, id="h0-the-day-after-the-first-segment"),
            pytest.param(date(2025, 3, 3), 1, id="h0-on-the-first-day-of-the-second-segment"),
        ],
    )
    def test_segment_before_history_start(self, set_storage: Path, fake_plugin: BRIMProvider, history_start: Optional[date], flagged: int) -> None:
        """A segment that ends before H0 is history already: warned, never imported (D-S21). Segments and gaps are the plugin's."""
        members = [_member(CUSTODY_JAN, "custody-jan.csv"), _member(CUSTODY_MAR, "custody-mar.csv"), _member(CASH_JAN_MAR, CASH_NAME)]

        preview = _preview(fake_plugin, members, history_start=history_start)

        assert (preview.segments, preview.gaps) == ([JAN_SEGMENT, MAR_SEGMENT], [DateRangeModel(start=date(2025, 1, 16), end=date(2025, 3, 2))])
        assert preview.history_start == history_start
        assert _codes(preview).count("before_history_segment") == flagged

    @pytest.mark.parametrize(
        ("gap_fix_dates", "warned"),
        [
            pytest.param([], False, id="none"),
            pytest.param([date(2025, 1, 10)], True, id="inside"),
            pytest.param([date(2025, 1, 2)], True, id="first-day"),
            pytest.param([date(2025, 1, 15)], True, id="last-day"),
            pytest.param([date(2025, 1, 1)], False, id="the-eve-a-previous-opening"),
            pytest.param([date(2025, 1, 1), date(2025, 2, 1)], False, id="outside-only"),
        ],
    )
    def test_gap_fix_inside_a_segment(self, set_storage: Path, fake_plugin: BRIMProvider, gap_fix_dates: List[date], warned: bool) -> None:
        """A gap-fix already inside a segment of the set would count its cash twice: warned (D-S21)."""
        preview = _preview(fake_plugin, [_member(CUSTODY_JAN, CUSTODY_NAME), _member(CASH_JAN, CASH_NAME)], gap_fix_dates=gap_fix_dates)

        assert ("covers_gap_fix" in _codes(preview)) is warned


# =============================================================================
# A2 · D5 — SERVICE: preview_set
# =============================================================================


class TestPreviewSet:
    """D5 — ``preview_set``: the plugin, the members of one upload, H0 and the gap-fix dates from the database."""

    @pytest.mark.asyncio
    async def test_reads_history_and_gap_fixes_from_the_database(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        preview_set = _sets("preview_set")
        batch = str(uuid.uuid4())
        custody = _member(CUSTODY_JAN, CUSTODY_NAME, batch_id=batch)
        cash = _member(CASH_JAN, CASH_NAME, batch_id=batch)
        earlier_upload = _member(_custody_csv("2023-05-02", "2023-05-31"), "custody-2023.csv", batch_id=str(uuid.uuid4()))
        await _seed_history(db_session, [(BROKER_ID, date(2025, 1, 8), f"import,{FAKE_CODE}"), (BROKER_ID, date(2025, 1, 9), f"import,{FAKE_CODE},gap_fix")])

        preview = await preview_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch)

        assert (preview.broker_id, preview.plugin_code, preview.batch_id) == (BROKER_ID, FAKE_CODE, batch)
        assert preview.history_start == date(2025, 1, 8)
        assert "covers_gap_fix" in _codes(preview)
        assert {member.file_id for member in preview.members} == {custody.file_id, cash.file_id}
        assert earlier_upload.file_id not in preview.model_dump_json(), "another upload of the same broker is never read (A16)"
        assert preview.segments == [JAN_SEGMENT]
        assert preview.complete is True

    @pytest.mark.asyncio
    async def test_other_brokers_history_is_ignored(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        preview_set = _sets("preview_set")
        batch = str(uuid.uuid4())
        _member(CUSTODY_JAN, CUSTODY_NAME, batch_id=batch)
        _member(CASH_JAN, CASH_NAME, batch_id=batch)
        await _seed_history(db_session, [(OTHER_BROKER_ID, date(2025, 1, 5), f"import,{FAKE_CODE}"), (OTHER_BROKER_ID, date(2025, 1, 9), f"import,{FAKE_CODE},gap_fix")])

        preview = await preview_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch)

        assert preview.history_start is None
        assert "covers_gap_fix" not in _codes(preview)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("plugin_code", "error"), [("no_such_plugin_a2", "BRIMSetPluginNotFound"), ("broker_generic_csv", "BRIMSetPluginNotASet"), (FAKE_CODE, "BRIMSetMembersNotFound")])
    async def test_errors(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession, plugin_code: str, error: str) -> None:
        preview_set = _sets("preview_set")

        with pytest.raises(_sets(error)) as caught:
            await preview_set(db_session, broker_id=BROKER_ID, plugin_code=plugin_code, batch_id=str(uuid.uuid4()))

        assert (caught.value.status_code, caught.value.code) == SET_ERRORS[error]

    # --- Phase F2 (U2-B): where the history LibreFolio holds ends, and how many transactions it has ---

    async def _preview_with_history(self, db_session: AsyncSession, rows: Sequence[Tuple[int, date, Optional[str]]]) -> Any:
        """``preview_set`` of a complete set of the fake on ``BROKER_ID``, with ``rows`` in the database (tags verbatim)."""
        _require_history_fields()
        preview_set = _sets("preview_set")
        batch = str(uuid.uuid4())
        _member(CUSTODY_JAN, CUSTODY_NAME, batch_id=batch)
        _member(CASH_JAN, CASH_NAME, batch_id=batch)
        await _seed_history(db_session, rows)
        return await preview_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch)

    @pytest.mark.asyncio
    async def test_history_end_and_count_include_the_gap_fix(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        """F2: the end is the newest row with the history tag, a gap-fix correction included, and every such row counts (H0 unchanged)."""
        preview = await self._preview_with_history(db_session, [(BROKER_ID, date(2025, 1, 8), f"import,{FAKE_CODE}"), (BROKER_ID, date(2025, 1, 9), f"import,{FAKE_CODE},gap_fix")])

        assert (preview.history_start, preview.history_end, preview.history_count) == (date(2025, 1, 8), date(2025, 1, 9), 2)

    @pytest.mark.asyncio
    async def test_history_end_and_count_read_this_brokers_exact_tag_only(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        """F2: every row of this broker with the exact tag counts, two on one day included; nothing else counts, not even for the end.

        Not another broker's rows (newer than any of this broker's), not a tag that merely contains the
        history tag (``broker_<tag>``, ``<tag>_old``), not a row without the tag.
        """
        preview = await self._preview_with_history(
            db_session,
            [
                (BROKER_ID, date(2025, 1, 8), f"import,{FAKE_CODE}"),
                (BROKER_ID, date(2025, 1, 8), f"{FAKE_CODE},import"),
                (BROKER_ID, date(2025, 3, 15), FAKE_CODE),
                (BROKER_ID, date(2025, 6, 1), f"import,broker_{FAKE_CODE}"),
                (BROKER_ID, date(2025, 7, 1), f"import,{FAKE_CODE}_old"),
                (BROKER_ID, date(2025, 8, 1), "manual"),
                (BROKER_ID, date(2025, 9, 1), None),
                (OTHER_BROKER_ID, date(2025, 12, 1), f"import,{FAKE_CODE}"),
                (OTHER_BROKER_ID, date(2025, 12, 2), f"import,{FAKE_CODE},gap_fix"),
            ],
        )

        assert (preview.history_start, preview.history_end, preview.history_count) == (date(2025, 1, 8), date(2025, 3, 15), 3)

    @pytest.mark.asyncio
    async def test_no_history_has_no_end_and_counts_nothing(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        """F2: this broker holds none of the plugin's history (another broker does): no H0, no end, a zero count."""
        preview = await self._preview_with_history(db_session, [(OTHER_BROKER_ID, date(2025, 1, 5), f"import,{FAKE_CODE}"), (BROKER_ID, date(2025, 1, 6), "manual")])

        assert (preview.history_start, preview.history_end, preview.history_count) == (None, None, 0)

    @pytest.mark.asyncio
    async def test_a_lone_gap_fix_is_the_end_and_counts(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        """F2: only the opening correction — H0 is the day after it (D-S25), the end is its own date, and it counts as one."""
        preview = await self._preview_with_history(db_session, [(BROKER_ID, date(2024, 12, 31), f"import,{FAKE_CODE},gap_fix")])

        assert (preview.history_start, preview.history_end, preview.history_count) == (date(2025, 1, 1), date(2024, 12, 31), 1)


# =============================================================================
# A2 · D6 — SERVICE: combine_set
# =============================================================================


class TestCombineSet:
    """D6 — ``combine_set``: preview, then reuse or ``plugin.combine`` + ``save_combined_file`` (§3.4, D-S6)."""

    @pytest.mark.asyncio
    async def test_combines_and_saves_a_complete_set(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        combine_set = _sets("combine_set")
        batch = str(uuid.uuid4())
        custody = _member(CUSTODY_JAN, CUSTODY_NAME, batch_id=batch)
        cash = _member(CASH_JAN, CASH_NAME, batch_id=batch)

        result = await combine_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, user_id=USER_ID)

        expected = fake_plugin.combine({"custody": [brim_provider.get_file_path(custody.file_id)], "cash": [brim_provider.get_file_path(cash.file_id)]})
        assert isinstance(result, _schema("BRIMSetCombineResponse", A2))
        assert (result.reused, result.summary) == (False, expected.summary)
        combined = result.combined
        assert (combined.kind, combined.status, combined.target_broker_id, combined.compatible_plugins) == ("combined", BRIMFileStatus.UPLOADED, BROKER_ID, [FAKE_CODE])
        assert (combined.batch_id, combined.uploaded_by_user_id) == (batch, USER_ID)
        assert {ref.file_id: (ref.role, ref.filename, ref.deleted) for ref in combined.derived_from} == {custody.file_id: ("custody", CUSTODY_NAME, False), cash.file_id: ("cash", CASH_NAME, False)}
        with open(brim_provider.get_file_path(combined.file_id), encoding="utf-8-sig", newline="") as handle:
            assert list(csv.reader(handle, delimiter=";")) == [expected.headers, *expected.rows]
        for member in (custody, cash):
            assert combined.file_id in _info(member.file_id).combined_into

    @pytest.mark.asyncio
    async def test_generated_name_never_repeats_a_member_name(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        """``<provider name> — combined <first segment start>…<last segment end>.csv``: the members' names (Danske: an IBAN) stay out."""
        combine_set = _sets("combine_set")
        batch = str(uuid.uuid4())
        members = [_member(CUSTODY_JAN, CUSTODY_NAME, batch_id=batch), _member(CASH_JAN, CASH_NAME, batch_id=batch)]

        result = await combine_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, user_id=USER_ID)

        assert result.combined.filename == f"{FAKE_PROVIDER_NAME} — combined 2025-01-02…2025-01-15.csv"
        for member in members:
            assert member.filename not in result.combined.filename and Path(member.filename).stem not in result.combined.filename

    @pytest.mark.asyncio
    async def test_generated_name_spans_every_segment(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        combine_set = _sets("combine_set")
        batch = str(uuid.uuid4())
        _member(CUSTODY_JAN, "custody-jan.csv", batch_id=batch)
        _member(CUSTODY_MAR, "custody-mar.csv", batch_id=batch)
        _member(CASH_JAN_MAR, CASH_NAME, batch_id=batch)

        result = await combine_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, user_id=USER_ID)

        assert result.combined.filename == f"{FAKE_PROVIDER_NAME} — combined 2025-01-02…2025-03-20.csv"

    @pytest.mark.asyncio
    async def test_generated_name_without_segments(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        combine_set = _sets("combine_set")
        batch = str(uuid.uuid4())
        _member(CUSTODY_JAN, CUSTODY_NAME, batch_id=batch)
        _member(CASH_JAN, CASH_NAME, batch_id=batch)
        # Same code, a plugin that proves no segment. `fake_plugin` restores the whole registry afterwards.
        BRIMProviderRegistry._providers[FAKE_CODE] = _FakeNoShapeProvider

        result = await combine_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, user_id=USER_ID)

        assert result.combined.filename == f"{FAKE_PROVIDER_NAME} — combined.csv"

    @pytest.mark.asyncio
    async def test_same_members_reuse_the_combined_file(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        """The second combine returns the first file and its stored summary, and writes nothing (D-S6)."""
        combine_set = _sets("combine_set")
        batch = str(uuid.uuid4())
        _member(CUSTODY_JAN, CUSTODY_NAME, batch_id=batch)
        _member(CASH_JAN, CASH_NAME, batch_id=batch)
        first = await combine_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, user_id=USER_ID)
        assert first.reused is False  # presence barrier: the first call does combine

        second = await combine_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, user_id=USER_ID)

        assert (second.reused, second.combined.file_id) == (True, first.combined.file_id)
        assert second.summary == first.summary and second.summary
        assert [info.file_id for info in _combined_files()] == [first.combined.file_id]

    @pytest.mark.asyncio
    async def test_new_plugin_version_combines_again(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
        """A bumped plugin writes a new combined file; the old one stays, marked stale."""
        combine_set = _sets("combine_set")
        batch = str(uuid.uuid4())
        _member(CUSTODY_JAN, CUSTODY_NAME, batch_id=batch)
        _member(CASH_JAN, CASH_NAME, batch_id=batch)
        first = await combine_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, user_id=USER_ID)
        monkeypatch.setattr(_FakeTwoRoleProvider, "plugin_version", "2.0.0-a2-test")

        second = await combine_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, user_id=USER_ID)

        assert second.reused is False
        assert second.combined.file_id != first.combined.file_id
        assert (_info(first.combined.file_id).combine_is_stale, _info(second.combined.file_id).combine_is_stale) == (True, False)

    @pytest.mark.asyncio
    async def test_incomplete_set_is_refused(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        combine_set = _sets("combine_set")
        batch = str(uuid.uuid4())
        _member(CUSTODY_JAN, CUSTODY_NAME, batch_id=batch)

        with pytest.raises(_sets("BRIMSetIncomplete")) as caught:
            await combine_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, user_id=USER_ID)

        assert (caught.value.status_code, caught.value.code) == SET_ERRORS["BRIMSetIncomplete"]
        assert caught.value.missing_roles == ["cash"]
        assert _combined_files() == []

    @pytest.mark.asyncio
    async def test_mixed_accounts_set_is_refused(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        """Every role is there, but two deposit accounts make the set incomplete: nothing is missing, nothing is written."""
        combine_set = _sets("combine_set")
        batch = str(uuid.uuid4())
        _member(CUSTODY_JAN, "custody-jan.csv", batch_id=batch)
        _member(_custody_csv("2025-03-03", "2025-03-20", account=OTHER_ACCOUNT), "custody-mar.csv", batch_id=batch)
        _member(CASH_JAN_MAR, CASH_NAME, batch_id=batch)

        with pytest.raises(_sets("BRIMSetIncomplete")) as caught:
            await combine_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, user_id=USER_ID)

        assert caught.value.missing_roles == []
        assert _combined_files() == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("plugin_code", "error"), [("no_such_plugin_a2", "BRIMSetPluginNotFound"), ("broker_generic_csv", "BRIMSetPluginNotASet"), (FAKE_CODE, "BRIMSetMembersNotFound")])
    async def test_errors(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession, plugin_code: str, error: str) -> None:
        combine_set = _sets("combine_set")

        with pytest.raises(_sets(error)) as caught:
            await combine_set(db_session, broker_id=BROKER_ID, plugin_code=plugin_code, batch_id=str(uuid.uuid4()), user_id=USER_ID)

        assert (caught.value.status_code, caught.value.code) == SET_ERRORS[error]


# =============================================================================
# A2 · D7 — SERVICE: ensure_parseable (the parse guard, D-S4)
# =============================================================================


class TestEnsureParseable:
    """D7 — ``ensure_parseable``: an original of a report-set plugin cannot be parsed on its own; everything else passes."""

    def test_original_of_a_set_plugin_is_refused(self, fake_plugin: BRIMProvider) -> None:
        ensure_parseable = _sets("ensure_parseable")

        with pytest.raises(_service("BRIMSetRequiredError")) as caught:
            ensure_parseable(fake_plugin, _file_info("original"))

        assert isinstance(caught.value, BRIMParseError)
        assert sorted(caught.value.missing_roles) == ["cash", "custody"]

    def test_only_required_roles_are_named(self) -> None:
        ensure_parseable = _sets("ensure_parseable")

        with pytest.raises(_service("BRIMSetRequiredError")) as caught:
            ensure_parseable(_FakeOptionalRoleProvider(), _file_info("original"))

        assert sorted(caught.value.missing_roles) == ["cash", "custody"]

    def test_combined_file_passes(self, fake_plugin: BRIMProvider) -> None:
        ensure_parseable = _sets("ensure_parseable")

        assert ensure_parseable(fake_plugin, _file_info("combined")) is None

    def test_single_file_plugin_passes(self) -> None:
        ensure_parseable = _sets("ensure_parseable")

        assert ensure_parseable(BRIMProviderRegistry.get_provider_instance("broker_generic_csv"), _file_info("original")) is None


# =============================================================================
# A2 · D8 — SERVICE: apply_history (H0 at parse time)
# =============================================================================


class TestApplyHistory:
    """D8 — ``apply_history``: H0 at parse time, and the checkpoints kept from its eve on (D-S21, D-S25)."""

    @pytest.mark.asyncio
    async def test_history_in_the_database(self, db_session: AsyncSession) -> None:
        """H0 comes from the plugin's history tag (``fake_bank``, not the code); checkpoints before its eve go, verifications all stay."""
        apply_history = _sets("apply_history")
        await _seed_history(db_session, [(BROKER_ID, date(2025, 3, 3), "import,fake_bank"), (BROKER_ID, date(2024, 1, 2), "import,broker_fake_bank")])
        output = _parse_output(checkpoints=[("2024-12-31", "opening"), ("2025-03-01", "gap"), ("2025-03-02", "gap"), ("2025-06-30", "gap")], verifications=["2024-06-30", "2025-12-31"])

        checkpoints, verifications, h0 = await apply_history(db_session, broker_id=BROKER_ID, plugin=_FakeBankProvider(), output=output)

        assert h0 == date(2025, 3, 3)
        assert sorted(item.as_of for item in checkpoints) == [date(2025, 3, 2), date(2025, 6, 30)]
        assert verifications == output.verifications

    @pytest.mark.asyncio
    async def test_reimport_keeps_the_opening_checkpoint(self, db_session: AsyncSession) -> None:
        """Scenario 4, the same set again: the opening gap-fix counts from the next day, so its checkpoint (the eve) stays."""
        apply_history = _sets("apply_history")
        await _seed_history(db_session, [(BROKER_ID, date(2024, 12, 31), "import,fake_bank,gap_fix"), (BROKER_ID, date(2025, 1, 2), "import,fake_bank")])
        output = _parse_output(checkpoints=[("2024-12-31", "opening")])

        checkpoints, _verifications, h0 = await apply_history(db_session, broker_id=BROKER_ID, plugin=_FakeBankProvider(), output=output)

        assert h0 == date(2025, 1, 1)
        assert [item.as_of for item in checkpoints] == [date(2024, 12, 31)]

    @pytest.mark.asyncio
    async def test_first_import_summarize_starts_after_the_first_checkpoint(self, db_session: AsyncSession) -> None:
        """No history of this plugin here (another broker's does not count): H0 is the day after the earliest checkpoint, whatever the rows say."""
        apply_history = _sets("apply_history")
        await _seed_history(db_session, [(OTHER_BROKER_ID, date(2020, 1, 1), "import,fake_bank"), (BROKER_ID, date(2020, 1, 1), "manual")])
        output = _parse_output(transactions=["2024-11-05"], checkpoints=[("2025-06-30", "gap"), ("2024-12-31", "opening")], verifications=["2025-12-31"])

        checkpoints, verifications, h0 = await apply_history(db_session, broker_id=BROKER_ID, plugin=_FakeBankProvider(), output=output)

        assert h0 == date(2025, 1, 1)
        assert sorted(item.as_of for item in checkpoints) == [date(2024, 12, 31), date(2025, 6, 30)]
        assert verifications == output.verifications

    @pytest.mark.asyncio
    async def test_first_import_summarize_without_checkpoints(self, db_session: AsyncSession) -> None:
        apply_history = _sets("apply_history")
        output = _parse_output(transactions=["2025-01-02"], verifications=["2025-01-17"])

        checkpoints, verifications, h0 = await apply_history(db_session, broker_id=BROKER_ID, plugin=_FakeBankProvider(), output=output)

        assert (h0, checkpoints) == (None, [])
        assert verifications == output.verifications

    @pytest.mark.asyncio
    async def test_first_import_import_policy_starts_at_the_oldest_row(self, db_session: AsyncSession) -> None:
        apply_history = _sets("apply_history")
        output = _parse_output(transactions=["2025-02-01", "2024-11-05"], checkpoints=[("2024-10-01", "opening"), ("2024-12-31", "gap")])

        checkpoints, _verifications, h0 = await apply_history(db_session, broker_id=BROKER_ID, plugin=_FakeBankImportPolicyProvider(), output=output)

        assert h0 == date(2024, 11, 5)
        assert [item.as_of for item in checkpoints] == [date(2024, 12, 31)]

    @pytest.mark.asyncio
    async def test_first_import_import_policy_without_rows_falls_back_to_the_checkpoint(self, db_session: AsyncSession) -> None:
        apply_history = _sets("apply_history")
        output = _parse_output(checkpoints=[("2024-12-31", "opening")])

        checkpoints, _verifications, h0 = await apply_history(db_session, broker_id=BROKER_ID, plugin=_FakeBankImportPolicyProvider(), output=output)

        assert h0 == date(2025, 1, 1)
        assert [item.as_of for item in checkpoints] == [date(2024, 12, 31)]


# =============================================================================
# A2 · FIXTURE GUARDS
# =============================================================================


class TestA2FixtureGuards:
    """Fixture guards (pass before and after A2): the A2 test infrastructure works, so every A2 red is about the product.

    Most A2 tests look up the missing piece first and never reach their helpers
    before the cure; without these, a broken helper would only surface afterwards,
    looking like a product defect.
    """

    @pytest.mark.asyncio
    async def test_fixture_guard_private_database(self, db_session: AsyncSession) -> None:
        """Fixture guard: ``_seed_history`` writes both brokers and the transactions, tags verbatim, into this test's own database."""
        await _seed_history(db_session, [_own("2024-12-31", "import,danske_bank,gap_fix"), _foreign("2024-01-01", None)])

        brokers = (await db_session.execute(select(Broker.id))).scalars().all()
        rows = (await db_session.execute(select(Transaction.broker_id, Transaction.date, Transaction.tags))).all()

        assert sorted(brokers) == [BROKER_ID, OTHER_BROKER_ID]
        assert sorted((row.broker_id, row.date, row.tags or "") for row in rows) == [(BROKER_ID, date(2024, 12, 31), "import,danske_bank,gap_fix"), (OTHER_BROKER_ID, date(2024, 1, 1), "")]

    def test_fixture_guard_fake_describes_its_set(self, isolated_brim_dir: Path, fake_plugin: BRIMProvider) -> None:
        """Fixture guard: the fake's ``describe_set`` merges custody spans that overlap or touch, and proves a gap between the others."""
        jan, mar, touching = (brim_provider.get_file_path(_member(content, name).file_id) for content, name in ((CUSTODY_JAN, "jan.csv"), (CUSTODY_MAR, "mar.csv"), (_custody_csv("2025-01-16", "2025-01-20"), "touching.csv")))

        shape = fake_plugin.describe_set({"custody": [mar, jan]})
        merged = fake_plugin.describe_set({"custody": [jan, touching]})

        assert (shape.segments, shape.gaps) == ([JAN_SEGMENT, MAR_SEGMENT], [DateRangeModel(start=date(2025, 1, 16), end=date(2025, 3, 2))])
        assert [notice.code for notice in shape.notices] == [FAKE_SET_NOTICE]
        assert (merged.segments, merged.gaps) == ([DateRangeModel(start=date(2025, 1, 2), end=date(2025, 1, 20))], [])

    def test_fixture_guard_account_fingerprint(self, isolated_brim_dir: Path, fake_plugin: BRIMProvider) -> None:
        """Fixture guard: a custody header's ``account=<id>`` cell is the fingerprint; without it, ``FAKE_ACCOUNT``; cash has none; a stranger file has no role."""
        contents = ((CUSTODY_JAN, "jan.csv"), (_custody_csv("2025-03-03", account=OTHER_ACCOUNT), "mar.csv"), (CASH_JAN, "cash.csv"), (GENERIC_CSV, "generic.csv"))
        paths = [brim_provider.get_file_path(_member(content, name).file_id) for content, name in contents]

        assert [fake_plugin.describe_member(path).account_fingerprint for path in paths] == [FAKE_ACCOUNT, OTHER_ACCOUNT, None, None]
        assert [fake_plugin.detect_role(path) for path in paths] == ["custody", "custody", "cash", None]
        assert (fake_plugin.describe_member(paths[-1]).role, fake_plugin.describe_member(paths[-1]).rows) == (None, 0)

    def test_fixture_guard_plugin_variants(self) -> None:
        """Fixture guard: each variant differs from the fake in exactly what its docstring says."""
        assert [(role.code, role.multiple) for role in _FakeSingleCustodyProvider().report_roles] == [("custody", False), ("cash", True)]
        assert [(role.code, role.required) for role in _FakeOptionalRoleProvider().report_roles] == [("custody", True), ("cash", True), ("statement", False)]
        assert _FakeNoShapeProvider().describe_set({}) == _schema("BRIMSetShape")()
        assert (_FakeBankProvider().provider_code, _FakeBankProvider().pre_checkpoint_policy) == ("broker_fake_bank", "summarize")
        assert (_FakeBankImportPolicyProvider().provider_code, _FakeBankImportPolicyProvider().pre_checkpoint_policy) == ("broker_fake_bank", "import")
        assert _FakeInfixProvider().provider_code == "fake_broker_bank"

    def test_fixture_guard_parse_output_and_sidecar_rewrite(self, isolated_brim_dir: Path) -> None:
        """Fixture guard: ``_parse_output`` builds valid rows and truth points; ``_rewrite_sidecar`` changes what ``get_file_info`` reads."""
        output = _parse_output(transactions=["2024-11-05"], checkpoints=[("2024-12-31", "opening")], verifications=["2025-01-17"])
        stored = _member(CUSTODY_JAN, CUSTODY_NAME)

        _rewrite_sidecar(isolated_brim_dir, stored.file_id, uploaded_at="2026-09-30T11:00:00+00:00")

        assert [(tx.type, tx.date) for tx in output.transactions] == [(TransactionType.DEPOSIT, date(2024, 11, 5))]
        assert ([item.as_of for item in output.checkpoints], [item.as_of for item in output.verifications]) == ([date(2024, 12, 31)], [date(2025, 1, 17)])
        assert _info(stored.file_id).uploaded_at == datetime(2026, 9, 30, 11, 0, tzinfo=UTC)


# =============================================================================
# PHASE B — the test_sample_sets contract, and two fixes of the set framework
# =============================================================================
#
# Written red-first with the Danske Bank plugin (plan §4 B0, last lines): the
# ``test_sample_sets`` contract property, ``apply_history`` on a later import (what
# precedes H0 is already in LibreFolio, so the kept checkpoints must not absorb it
# again) and ``combine_set`` turning a plugin error into a 422 (``BRIMSetCombineFailed``).
#
# Phase E (plan E.0, point 1) extends ``TestApplyHistoryLaterImport``, red-first too: on
# a later import a kept checkpoint dated from H0 on closes a gap in the history LibreFolio
# already holds, so it is a ``gap`` even when the plugin, which cannot know that history,
# marks it ``opening``. The eve of H0 and a first import stay as the plugin made them.

B = "B"


def _set_symbol(name: str, phase: str) -> Any:
    """A symbol of ``brim_report_sets`` that ``phase`` adds (``_sets`` names phase A2 in its message)."""
    module = _sets_module()
    found = None if module is None else getattr(module, name, None)
    if found is None:
        _missing(f"{SETS_MODULE}.{name} does not exist", phase)
    return found


def _cash_of(items: Sequence[Any]) -> Dict[str, Decimal]:
    """``{currency: amount}`` of truth-cash entries, zero amounts left out (an empty sum may be written either way)."""
    return {item.currency: item.amount for item in items if item.amount != 0}


def _absorbed(rows: Sequence[Tuple[str, str]], *, opening: Optional[str] = None) -> Any:
    """A ``BRIMAbsorbed`` of EUR rows ``(value date, amount)``, count and cash from the rows, ``opening_cash`` when given."""
    absorbed_row, absorbed, truth_cash = _schema("BRIMAbsorbedRow", B), _schema("BRIMAbsorbed", B), _schema("BRIMTruthCash", B)
    items = [absorbed_row(as_of=date.fromisoformat(day), currency="EUR", amount=Decimal(amount), label=f"Rivi {day}") for day, amount in rows]
    total = sum((item.amount for item in items), Decimal(0))
    return absorbed(
        count=len(items),
        cash=[truth_cash(currency="EUR", amount=total)] if items else [],
        rows=items,
        opening_cash=[] if opening is None else [truth_cash(currency="EUR", amount=Decimal(opening))],
    )


def _truth_checkpoint(as_of: str, kind: str, absorbed: Any) -> Any:
    """A checkpoint stating 1000 EUR, with the given absorbed rows."""
    checkpoint, truth_cash = _schema("BRIMCheckpoint", B), _schema("BRIMTruthCash", B)
    return checkpoint(as_of=date.fromisoformat(as_of), kind=kind, cash=[truth_cash(currency="EUR", amount=Decimal("1000"))], absorbed=absorbed)


def _proven_checkpoint(as_of: str, kind: str, absorbed: Any) -> Any:
    """``_truth_checkpoint`` with the rest of what a bank proves: an exact position with its unit cost, a minimum one, and an evidence table."""
    truth_position = _schema("BRIMTruthPosition")
    positions = [
        truth_position(asset_id=FAKE_ASSET_ID_BASE, quantity=Decimal("100"), exactness="exact", unit_cost=Currency(code="EUR", amount=Decimal("12.50"))),
        truth_position(asset_id=FAKE_ASSET_ID_BASE - 1, quantity=Decimal("180"), exactness="at_least"),
    ]
    evidence = [BRIMEvidence(title="Saldo", headers=["Pvm", "Saldo"], rows=[[as_of, "1000,00"]], row_numbers=[21])]
    return _truth_checkpoint(as_of, kind, absorbed).model_copy(update={"positions": positions, "evidence": evidence})


def _all_but_kind_and_absorbed(checkpoint: Any) -> Dict[str, Any]:
    """A checkpoint as the bank states it: its date, cash, positions and evidence (everything but its kind and its absorbed rows)."""
    return checkpoint.model_dump(exclude={"kind", "absorbed"})


# Phase E: why a checkpoint of a later import, dated from H0 on, must not stay ``opening``.
LATER_IMPORT_GAP = "on a later import a checkpoint dated from H0 on closes a gap in the history LibreFolio already holds: kind 'gap' — not implemented yet (BRIM report sets, phase E)"


class _FakeCombineParseErrorProvider(_FakeTwoRoleProvider):
    """The fake whose ``combine`` refuses its members the way a plugin reports a file it cannot read."""

    failure: type = BRIMParseError

    def combine(self, members: Dict[str, List[Path]]) -> Any:
        raise self.failure("fake combine failure: the cash export does not cover the custody period")


class _FakeCombineValueErrorProvider(_FakeCombineParseErrorProvider):
    """The same failure raised as a ``ValueError``."""

    failure = ValueError


class TestSampleSetsContract:
    """B — ``BRIMProvider.test_sample_sets``: the sample sets a report-set plugin declares; ``[]`` by default, like ``test_file_patterns``."""

    def test_defaults_to_no_set(self) -> None:
        _require_contract("test_sample_sets", phase=B)

        assert BRIMProviderRegistry.get_provider_instance("broker_generic_csv").test_sample_sets == []

    def test_every_existing_plugin_keeps_the_default(self) -> None:
        _require_contract("test_sample_sets", phase=B)

        declaring = sorted(code for code in EXISTING_PLUGIN_CODES if BRIMProviderRegistry.get_provider_instance(code).test_sample_sets != [])

        assert declaring == []


class TestApplyHistoryLaterImport:
    """B, fix 1 — ``apply_history`` when H0 comes from the database: what precedes H0 is already represented.

    The kept checkpoints lose ``opening_cash`` and the absorbed rows dated before H0, and
    their count and cash follow the rows kept. Otherwise the gap-fix explanation would
    subtract the opening balance a second time. A first import is left unchanged.

    Phase E (plan E.0, point 1): a kept checkpoint dated from H0 on becomes ``gap``. The
    plugin marks the first segment of every set ``opening`` (it cannot know the broker's
    history), so after a skipped year the correction would show as a starting point. The
    checkpoint on the eve of H0 (the first set imported again) stays as the plugin made it.
    """

    @pytest.mark.asyncio
    async def test_later_import_drops_what_precedes_h0(self, db_session: AsyncSession) -> None:
        apply_history = _sets("apply_history")
        await _seed_history(db_session, [(BROKER_ID, date(2025, 3, 3), "import,fake_bank")])
        eve = _truth_checkpoint("2025-03-02", "opening", _absorbed([("2025-01-10", "500"), ("2025-03-02", "-3.5")], opening="400"))
        later = _truth_checkpoint("2025-06-30", "gap", _absorbed([("2025-03-02", "-20"), ("2025-03-03", "-100"), ("2025-05-15", "250")]))

        checkpoints, _verifications, h0 = await apply_history(db_session, broker_id=BROKER_ID, plugin=_FakeBankProvider(), output=BRIMParseOutput(checkpoints=[eve, later]))

        assert h0 == date(2025, 3, 3)
        kept = {item.as_of: item for item in checkpoints}
        assert sorted(kept) == [date(2025, 3, 2), date(2025, 6, 30)]
        first, second = kept[date(2025, 3, 2)], kept[date(2025, 6, 30)]
        assert (first.kind, first.cash, second.kind, second.cash) == ("opening", eve.cash, "gap", later.cash)
        assert (first.absorbed.count, first.absorbed.rows, _cash_of(first.absorbed.cash), first.absorbed.opening_cash) == (0, [], {}, [])
        assert [(row.as_of, row.amount) for row in second.absorbed.rows] == [(date(2025, 3, 3), Decimal("-100")), (date(2025, 5, 15), Decimal("250"))]
        assert (second.absorbed.count, _cash_of(second.absorbed.cash), second.absorbed.opening_cash) == (2, {"EUR": Decimal("150")}, [])

    @pytest.mark.asyncio
    async def test_reimport_of_the_same_set_keeps_the_opening_empty(self, db_session: AsyncSession) -> None:
        """Scenario 4: the opening gap-fix is in the database, so H0 is the next day; the opening checkpoint stays, with nothing to explain again."""
        apply_history = _sets("apply_history")
        await _seed_history(db_session, [(BROKER_ID, date(2024, 12, 31), "import,fake_bank,gap_fix"), (BROKER_ID, date(2025, 1, 2), "import,fake_bank")])
        opening = _truth_checkpoint("2024-12-31", "opening", _absorbed([("2024-06-03", "1000"), ("2024-12-31", "-3.5")], opening="3.5"))

        checkpoints, _verifications, h0 = await apply_history(db_session, broker_id=BROKER_ID, plugin=_FakeBankProvider(), output=BRIMParseOutput(checkpoints=[opening]))

        assert h0 == date(2025, 1, 1)
        assert len(checkpoints) == 1
        kept = checkpoints[0]
        assert (kept.as_of, kept.kind, kept.cash) == (opening.as_of, "opening", opening.cash)
        assert (kept.absorbed.count, kept.absorbed.rows, _cash_of(kept.absorbed.cash), kept.absorbed.opening_cash) == (0, [], {}, [])

    @pytest.mark.asyncio
    async def test_first_import_is_unchanged(self, db_session: AsyncSession) -> None:
        """Guard (passes before and after the fix): no history in the database, so the checkpoints come back as the plugin made them."""
        apply_history = _sets("apply_history")
        opening = _truth_checkpoint("2024-12-31", "opening", _absorbed([("2024-06-03", "1000"), ("2024-12-31", "-3.5")], opening="3.5"))
        gap = _truth_checkpoint("2025-06-30", "gap", _absorbed([("2025-03-10", "-100")]))

        checkpoints, _verifications, h0 = await apply_history(db_session, broker_id=BROKER_ID, plugin=_FakeBankProvider(), output=BRIMParseOutput(checkpoints=[opening, gap]))

        assert h0 == date(2025, 1, 1)
        assert checkpoints == [opening, gap]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("plugin", [_FakeBankProvider, _FakeBankImportPolicyProvider], ids=["summarize-policy", "import-policy"])
    async def test_after_a_skipped_year_the_first_checkpoint_is_a_gap(self, db_session: AsyncSession, plugin: type) -> None:
        """Phase E: LibreFolio's history starts with an earlier set (its opening gap-fix is dated 2023-12-31, so H0 is 2024-01-01), and 2025 was never imported.

        The next set's first checkpoint (2025-12-31) is ``opening`` for the plugin, which cannot know that
        history; it closes a gap in it, so it comes back ``gap``, whatever the plugin's policy. The next one
        stays ``gap``. Everything else is what a later import already gives: date, cash, positions and
        evidence untouched, the absorbed rows from H0 on, no opening balance.
        """
        apply_history = _sets("apply_history")
        await _seed_history(db_session, [(BROKER_ID, date(2023, 12, 31), "import,fake_bank,gap_fix"), (BROKER_ID, date(2024, 2, 5), "import,fake_bank")])
        opening = _proven_checkpoint("2025-12-31", "opening", _absorbed([("2025-11-03", "300"), ("2025-12-31", "-50")], opening="750"))
        gap = _proven_checkpoint("2026-06-30", "gap", _absorbed([("2026-03-10", "-100")]))

        checkpoints, _verifications, h0 = await apply_history(db_session, broker_id=BROKER_ID, plugin=plugin(), output=BRIMParseOutput(checkpoints=[opening, gap]))

        # Barrier: H0 comes from the database (the day after the opening gap-fix), and both checkpoints are kept.
        assert h0 == date(2024, 1, 1)
        kept = {item.as_of: item for item in checkpoints}
        assert sorted(kept) == [date(2025, 12, 31), date(2026, 6, 30)]
        first, second = kept[date(2025, 12, 31)], kept[date(2026, 6, 30)]
        # What a later import already gives, and keeps giving: phase E changes the kind only.
        assert (_all_but_kind_and_absorbed(first), _all_but_kind_and_absorbed(second)) == (_all_but_kind_and_absorbed(opening), _all_but_kind_and_absorbed(gap))
        assert [(row.as_of, row.amount) for row in first.absorbed.rows] == [(date(2025, 11, 3), Decimal("300")), (date(2025, 12, 31), Decimal("-50"))]
        assert (first.absorbed.count, _cash_of(first.absorbed.cash), first.absorbed.opening_cash) == (2, {"EUR": Decimal("250")}, [])
        assert (second.absorbed.count, _cash_of(second.absorbed.cash), second.absorbed.opening_cash) == (1, {"EUR": Decimal("-100")}, [])
        # Subject.
        assert {day: item.kind for day, item in kept.items()} == {date(2025, 12, 31): "gap", date(2026, 6, 30): "gap"}, LATER_IMPORT_GAP

    @pytest.mark.asyncio
    async def test_a_checkpoint_on_h0_is_a_gap(self, db_session: AsyncSession) -> None:
        """Phase E, the boundary: from H0 itself, not from the day after.

        The history starts on 2025-03-03 (H0); a set whose first segment starts the next day has its
        first checkpoint on H0: ``gap``. Its absorbed rows before H0 go, and its opening balance with
        them, as on any later import. The eve of H0 stays as the plugin made it
        (``test_later_import_drops_what_precedes_h0``, ``test_reimport_of_the_same_set_keeps_the_opening_empty``).
        """
        apply_history = _sets("apply_history")
        await _seed_history(db_session, [(BROKER_ID, date(2025, 3, 3), "import,fake_bank")])
        opening = _proven_checkpoint("2025-03-03", "opening", _absorbed([("2025-02-20", "40"), ("2025-03-03", "-100")], opening="1060"))

        checkpoints, _verifications, h0 = await apply_history(db_session, broker_id=BROKER_ID, plugin=_FakeBankProvider(), output=BRIMParseOutput(checkpoints=[opening]))

        assert h0 == date(2025, 3, 3)
        assert [item.as_of for item in checkpoints] == [date(2025, 3, 3)]
        kept = checkpoints[0]
        assert _all_but_kind_and_absorbed(kept) == _all_but_kind_and_absorbed(opening)
        assert [(row.as_of, row.amount) for row in kept.absorbed.rows] == [(date(2025, 3, 3), Decimal("-100"))]
        assert (kept.absorbed.count, _cash_of(kept.absorbed.cash), kept.absorbed.opening_cash) == (1, {"EUR": Decimal("-100")}, [])
        assert kept.kind == "gap", LATER_IMPORT_GAP

    @pytest.mark.asyncio
    async def test_first_import_keeps_an_opening_dated_after_h0(self, db_session: AsyncSession) -> None:
        """Guard (passes before and after phase E): with the ``import`` policy a first import starts H0 at its oldest row, so its opening checkpoint falls after H0.

        There is no history yet, so no gap to close: the checkpoints come back as the plugin made them.
        Only a later import (H0 from the database) turns a checkpoint into a ``gap``.
        """
        apply_history = _sets("apply_history")
        opening = _proven_checkpoint("2024-12-31", "opening", _absorbed([]))
        gap = _proven_checkpoint("2025-06-30", "gap", _absorbed([("2025-03-10", "-100")]))
        rows = [TXCreateItem(broker_id=BROKER_ID, type=TransactionType.DEPOSIT, date=date(2024, 11, 5), cash=Currency(code="EUR", amount=Decimal("10")))]

        checkpoints, _verifications, h0 = await apply_history(db_session, broker_id=BROKER_ID, plugin=_FakeBankImportPolicyProvider(), output=BRIMParseOutput(transactions=rows, checkpoints=[opening, gap]))

        assert h0 == date(2024, 11, 5)
        assert checkpoints == [opening, gap]


class TestCombineSetPluginFailure:
    """B, fix 2 — ``combine_set``: a ``BRIMParseError`` or ``ValueError`` of ``plugin.combine`` is ``BRIMSetCombineFailed``: 422, ``combine_failed``.

    The message says what the plugin said; nothing is written; the members stay ``uploaded`` with their sidecars untouched.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("provider", [_FakeCombineParseErrorProvider, _FakeCombineValueErrorProvider], ids=["BRIMParseError", "ValueError"])
    async def test_a_plugin_error_is_a_422(self, provider: type, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        combine_set, failed, set_error = _sets("combine_set"), _set_symbol("BRIMSetCombineFailed", B), _sets("BRIMSetError")
        batch = str(uuid.uuid4())
        members = [_member(CUSTODY_JAN, CUSTODY_NAME, batch_id=batch), _member(CASH_JAN, CASH_NAME, batch_id=batch)]
        sidecars = {member.file_id: _sidecar(set_storage, member.file_id) for member in members}
        # Same code, a plugin whose combine fails. `fake_plugin` restores the whole registry afterwards.
        BRIMProviderRegistry._providers[FAKE_CODE] = provider

        with pytest.raises(failed) as caught:
            await combine_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, user_id=USER_ID)

        assert issubclass(failed, set_error)
        assert (caught.value.status_code, caught.value.code) == (422, "combine_failed")
        assert "the cash export does not cover the custody period" in caught.value.message
        assert _combined_files() == []
        assert {member.file_id: _sidecar(set_storage, member.file_id) for member in members} == sidecars
        assert [_info(member.file_id).status for member in members] == [BRIMFileStatus.UPLOADED, BRIMFileStatus.UPLOADED]

    def test_fixture_guard_the_failing_fakes(self, tmp_path: Path) -> None:
        """Fixture guard: each variant fails with its own exception type, and only in ``combine``."""
        for provider, failure in ((_FakeCombineParseErrorProvider, BRIMParseError), (_FakeCombineValueErrorProvider, ValueError)):
            plugin = provider()
            assert plugin.detect_role(_write(tmp_path, "custody.csv", CUSTODY_CSV)) == "custody"
            with pytest.raises(failure):
                plugin.combine({})


# =============================================================================
# PHASE G — the user chooses how a set is read: the files left out (D)
# =============================================================================
#
# Written red-first (plan §14 G.2, D). The set request names the originals of the upload
# the user left out of the set — read alone, or removed from it: ``exclude_file_ids``,
# empty by default, so every existing caller is unchanged, and the model stays strict.
# ``collect_members`` drops them; ``preview_set`` and ``combine_set`` pass them through. An
# excluded id that is not an original of that broker and upload is
# ``BRIMSetExcludeUnknown`` (422, ``exclude_unknown``); excluding every member is the 404 of
# today (``members_not_found``). The responses do not change, and a combined file is still
# reused for the exact same members only: the same exclusion reuses it, dropping the
# exclusion builds another one.

G = "G"
EXCLUDE = "exclude_file_ids"
EXCLUDE_UNKNOWN = (422, "exclude_unknown")
# A second cash export of the January set, after it: the cash role takes several files, so
# leaving this one out keeps the set complete.
CASH_FEB = _cash_csv("2025-02-03", "2025-02-17")


def _excluding(name: str) -> Any:
    """A set-service function that takes ``exclude_file_ids``; the test fails, naming it, until it does."""
    function = _sets(name)
    if EXCLUDE not in inspect.signature(function).parameters:
        _missing(f"{SETS_MODULE}.{name}() has no '{EXCLUDE}' parameter", G)
    return function


def _exclude_request() -> Any:
    """``BRIMSetRequest`` with its ``exclude_file_ids`` field; the test fails, naming it, until it has one."""
    set_request = _schema("BRIMSetRequest", A2)
    if EXCLUDE not in set_request.model_fields:
        _missing(f"BRIMSetRequest has no field {EXCLUDE}", G)
    return set_request


def _exclude_unknown() -> Any:
    """The new error of a set request that names a file which is not an original of its upload."""
    return _set_symbol("BRIMSetExcludeUnknown", G)


def _two_member_set() -> Tuple[str, BRIMFileInfo, BRIMFileInfo]:
    """One upload of the fake on ``BROKER_ID``: a custody export and the one cash export that covers it."""
    batch = str(uuid.uuid4())
    return batch, _member(CUSTODY_JAN, CUSTODY_NAME, batch_id=batch), _member(CASH_JAN, CASH_NAME, batch_id=batch)


def _three_member_set() -> Tuple[str, BRIMFileInfo, BRIMFileInfo, BRIMFileInfo]:
    """``_two_member_set`` plus a second cash export, which can be left out without making the set incomplete."""
    batch, custody, cash = _two_member_set()
    return batch, custody, cash, _member(CASH_FEB, "cash-statement-feb.csv", batch_id=batch)


def _ids(files: Sequence[Any]) -> set:
    return {item.file_id for item in files}


class TestSetRequestExclusions:
    """G · D — ``BRIMSetRequest.exclude_file_ids``: the originals left out of the set; empty by default, the model still strict."""

    BASE = {"broker_id": 7, "plugin_code": FAKE_CODE, "batch_id": "b-1"}

    def test_defaults_to_nothing_left_out(self) -> None:
        """An old client sends the three fields only: nothing is left out."""
        set_request = _exclude_request()

        request = set_request.model_validate(self.BASE)

        assert request.exclude_file_ids == []
        assert request.model_dump() == {**self.BASE, EXCLUDE: []}

    def test_carries_the_file_ids_as_sent(self) -> None:
        set_request = _exclude_request()

        request = set_request.model_validate({**self.BASE, EXCLUDE: ["f-2", "f-1"]})

        assert request.exclude_file_ids == ["f-2", "f-1"]
        assert set_request.model_validate_json(request.model_dump_json()) == request

    @pytest.mark.parametrize(
        ("extra", "field"),
        [
            pytest.param({EXCLUDE: [], "exclude_files": ["f-1"]}, "exclude_files", id="unknown-key-beside-it"),
            pytest.param({EXCLUDE: "f-1"}, EXCLUDE, id="a-string-instead-of-a-list"),
        ],
    )
    def test_stays_strict(self, extra: Dict[str, Any], field: str) -> None:
        set_request = _exclude_request()

        with pytest.raises(ValidationError) as caught:
            set_request.model_validate({**self.BASE, **extra})

        assert field in {str(error["loc"][0]) for error in caught.value.errors()}, caught.value.errors()


class TestSetExcludeUnknownError:
    """G · D — ``BRIMSetExcludeUnknown``: one more ``BRIMSetError``, 422 with the stable code ``exclude_unknown``."""

    def test_is_a_set_error_with_its_status_and_code(self) -> None:
        exclude_unknown = _exclude_unknown()

        assert issubclass(exclude_unknown, _sets("BRIMSetError"))
        assert (exclude_unknown.status_code, exclude_unknown.code) == EXCLUDE_UNKNOWN


class TestCollectMembersExclusions:
    """G · D — ``collect_members(..., exclude_file_ids=())``: the originals left out are no members."""

    def test_the_excluded_originals_are_dropped(self, set_storage: Path, fake_plugin: BRIMProvider) -> None:
        collect_members = _excluding("collect_members")
        batch, custody, cash, cash_feb = _three_member_set()

        members = collect_members(broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, exclude_file_ids=[cash_feb.file_id])

        assert _ids(members) == {custody.file_id, cash.file_id}
        assert len(members) == 2, [member.filename for member in members]

    def test_nothing_is_left_out_by_default(self, set_storage: Path, fake_plugin: BRIMProvider) -> None:
        """Called as before, the set is still every original of the upload the plugin reads."""
        collect_members = _excluding("collect_members")
        batch, custody, cash, cash_feb = _three_member_set()

        members = collect_members(broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch)

        assert _ids(members) == {custody.file_id, cash.file_id, cash_feb.file_id}

    @pytest.mark.parametrize("stranger", ["unknown-id", "one-of-several", "other-broker", "other-batch", "the-combined-file"])
    def test_an_id_that_is_not_an_original_of_the_upload_is_refused(self, set_storage: Path, fake_plugin: BRIMProvider, stranger: str) -> None:
        """An id that does not exist, an original of another broker (same batch) or of another upload, the set's own combined file:
        none is an original of this broker and upload, and one of them is enough to refuse the request."""
        collect_members, exclude_unknown = _excluding("collect_members"), _exclude_unknown()
        batch, custody, cash, cash_feb = _three_member_set()
        if stranger == "unknown-id":
            excluded = [str(uuid.uuid4())]
        elif stranger == "one-of-several":
            excluded = [cash_feb.file_id, str(uuid.uuid4())]
        elif stranger == "other-broker":
            excluded = [_member(CASH_FEB, "cash-other-broker.csv", batch_id=batch, broker_id=OTHER_BROKER_ID).file_id]
        elif stranger == "other-batch":
            excluded = [_member(CASH_FEB, "cash-other-batch.csv", batch_id=str(uuid.uuid4())).file_id]
        else:
            combined, _table = _save_combined(fake_plugin, ("custody", custody), ("cash", cash))
            assert (_info(combined.file_id).kind, _info(combined.file_id).batch_id) == ("combined", batch), "precondition: the combined file shares the upload"
            excluded = [combined.file_id]

        with pytest.raises(exclude_unknown) as caught:
            collect_members(broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, exclude_file_ids=excluded)

        assert isinstance(caught.value, _sets("BRIMSetError"))
        assert (caught.value.status_code, caught.value.code) == EXCLUDE_UNKNOWN

    @pytest.mark.parametrize("bystander", ["read-by-another-plugin", "failed"])
    def test_any_original_of_the_upload_may_be_named(self, set_storage: Path, fake_plugin: BRIMProvider, bystander: str) -> None:
        """An original of this broker and upload that is no member (another plugin's file, a failed one) is not unknown: nothing changes."""
        collect_members = _excluding("collect_members")
        batch, custody, cash, cash_feb = _three_member_set()
        if bystander == "read-by-another-plugin":
            other = _member(GENERIC_CSV, "generic.csv", batch_id=batch)
            assert FAKE_CODE not in other.compatible_plugins, "precondition: the fake does not read the generic CSV"
        else:
            other = _member(CASH_FEB, "cash-failed.csv", batch_id=batch)
            assert brim_provider.move_to_failed(other.file_id, "synthetic failure")

        members = collect_members(broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, exclude_file_ids=[other.file_id])

        assert _ids(members) == {custody.file_id, cash.file_id, cash_feb.file_id}

    def test_leaving_out_every_member_is_members_not_found(self, set_storage: Path, fake_plugin: BRIMProvider) -> None:
        collect_members = _excluding("collect_members")
        batch, custody, cash, cash_feb = _three_member_set()

        with pytest.raises(_sets("BRIMSetMembersNotFound")) as caught:
            collect_members(broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, exclude_file_ids=[custody.file_id, cash.file_id, cash_feb.file_id])

        assert (caught.value.status_code, caught.value.code) == SET_ERRORS["BRIMSetMembersNotFound"]


class TestPreviewSetExclusions:
    """G · D — ``preview_set(..., exclude_file_ids=...)``: the preview of the set without the files left out."""

    @pytest.mark.asyncio
    async def test_a_file_left_out_is_no_member(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        preview_set = _excluding("preview_set")
        batch, custody, cash, cash_feb = _three_member_set()

        preview = await preview_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, exclude_file_ids=[cash_feb.file_id])

        assert _ids(preview.members) == {custody.file_id, cash.file_id}
        assert _roles(preview)["cash"].file_ids == [cash.file_id]
        assert preview.complete is True
        assert cash_feb.file_id not in preview.model_dump_json()

    @pytest.mark.asyncio
    async def test_leaving_out_the_only_file_of_a_required_role_makes_it_missing(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        preview_set = _excluding("preview_set")
        batch, custody, cash = _two_member_set()

        preview = await preview_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, exclude_file_ids=[cash.file_id])

        assert [member.file_id for member in preview.members] == [custody.file_id]
        assert (_roles(preview)["cash"].status, _roles(preview)["cash"].file_ids) == ("missing", [])
        assert [item.role for item in preview.missing] == ["cash"]
        assert preview.complete is False

    @pytest.mark.asyncio
    async def test_an_unknown_file_is_refused(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        preview_set, exclude_unknown = _excluding("preview_set"), _exclude_unknown()
        batch, _custody, _cash = _two_member_set()

        with pytest.raises(exclude_unknown) as caught:
            await preview_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, exclude_file_ids=[str(uuid.uuid4())])

        assert (caught.value.status_code, caught.value.code) == EXCLUDE_UNKNOWN

    @pytest.mark.asyncio
    async def test_leaving_out_every_member_is_members_not_found(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        preview_set = _excluding("preview_set")
        batch, custody, cash = _two_member_set()

        with pytest.raises(_sets("BRIMSetMembersNotFound")) as caught:
            await preview_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, exclude_file_ids=[custody.file_id, cash.file_id])

        assert (caught.value.status_code, caught.value.code) == SET_ERRORS["BRIMSetMembersNotFound"]


class TestCombineSetExclusions:
    """G · D — ``combine_set(..., exclude_file_ids=...)``: the combined file of the kept members, reused for the same members only."""

    @pytest.mark.asyncio
    async def test_the_combined_file_holds_the_kept_members_only(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        combine_set = _excluding("combine_set")
        batch, custody, cash, cash_feb = _three_member_set()

        result = await combine_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, user_id=USER_ID, exclude_file_ids=[cash_feb.file_id])

        expected = fake_plugin.combine({"custody": [brim_provider.get_file_path(custody.file_id)], "cash": [brim_provider.get_file_path(cash.file_id)]})
        assert result.reused is False
        assert _ids(result.combined.derived_from) == {custody.file_id, cash.file_id}
        assert result.summary == expected.summary
        assert _info(cash_feb.file_id).combined_into == [], "the file left out is not linked to the combined file"
        assert [info.file_id for info in _combined_files()] == [result.combined.file_id]

    @pytest.mark.asyncio
    async def test_the_same_exclusion_reuses_it_and_no_exclusion_builds_another(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        combine_set = _excluding("combine_set")
        batch, custody, cash, cash_feb = _three_member_set()
        first = await combine_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, user_id=USER_ID, exclude_file_ids=[cash_feb.file_id])
        assert first.reused is False  # presence barrier: the first call does combine

        again = await combine_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, user_id=USER_ID, exclude_file_ids=[cash_feb.file_id])
        whole = await combine_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, user_id=USER_ID)

        assert (again.reused, again.combined.file_id) == (True, first.combined.file_id)
        assert whole.reused is False
        assert whole.combined.file_id != first.combined.file_id
        assert _ids(whole.combined.derived_from) == {custody.file_id, cash.file_id, cash_feb.file_id}
        assert {info.file_id for info in _combined_files()} == {first.combined.file_id, whole.combined.file_id}

    @pytest.mark.asyncio
    async def test_leaving_out_a_required_role_is_refused_and_writes_nothing(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        combine_set = _excluding("combine_set")
        batch, _custody, cash = _two_member_set()

        with pytest.raises(_sets("BRIMSetIncomplete")) as caught:
            await combine_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, user_id=USER_ID, exclude_file_ids=[cash.file_id])

        assert (caught.value.status_code, caught.value.code, caught.value.missing_roles) == (*SET_ERRORS["BRIMSetIncomplete"], ["cash"])
        assert _combined_files() == []

    @pytest.mark.asyncio
    async def test_an_unknown_file_is_refused_and_writes_nothing(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        combine_set, exclude_unknown = _excluding("combine_set"), _exclude_unknown()
        batch, _custody, _cash = _two_member_set()

        with pytest.raises(exclude_unknown) as caught:
            await combine_set(db_session, broker_id=BROKER_ID, plugin_code=FAKE_CODE, batch_id=batch, user_id=USER_ID, exclude_file_ids=[str(uuid.uuid4())])

        assert (caught.value.status_code, caught.value.code) == EXCLUDE_UNKNOWN
        assert _combined_files() == []


# =============================================================================
# STEP 5 — a set detected before item 8, a pair uploaded with 1.1.0, and one combined file per set (F1)
# =============================================================================
#
# Written red-first (plan-phase00BrimDanskeBankStep5PluginRedetection, §4). Item 8: ``compatible_plugins`` was computed
# once, at upload. A pair uploaded together (one ``batch_id``) by a build before item 8, whose catalogue did not read
# it, keeps sidecars without ``plugins_signature`` and with ``[]``, so ``collect_members`` never finds it. Read again
# after the update, its files are detected again and the pair forms its set without a new upload. The rules of the
# detection (signature, combined files, missing data file) and of the broker lock are in test_brim_parse_race.py.
#
# That model keeps the ``batch_id``: the 1.2 development builds before item 8 already stored it; 1.1.0 did not, it came
# with report sets, after 1.1.0. A pair uploaded with 1.1.0 is detected again too, but belongs to no set: such exports
# must be uploaded again, together. ``TestDanskePairUploadedWith1_1_0`` pins that documented limitation with sidecars
# written as 1.1.0's ``save_uploaded_file`` wrote them; it was written after the product, and pins a limit, not a cure.
#
# F1 (plan §0; step 4, §19.10): two ``combine_set`` of the same set at once each found nothing to reuse, and each saved
# a combined file. With the broker lock around reuse → build → save, the second waits, finds the first one's file and
# answers ``reused=True``. The first combine is parked inside the plugin until the second reaches the plugin too (the
# defect: it found nothing to reuse) or a grace runs out (the cure: it is waiting for the lock).

DANSKE_CODE = "broker_danske_bank"
DANSKE_SAMPLE_DIR = Path(__file__).resolve().parents[2] / "app" / "services" / "brim_providers" / "sample_reports"
DANSKE_PAIR = (("danske_bank-custody.xlsx", "custody"), ("danske_bank-cash.csv", "cash"))
# Every wait for something that must happen is bounded by this: a regression fails the test, it never hangs the suite.
_WAIT_SECONDS = 30.0
# How long the second combine is given to reach the plugin while the first is parked inside it. It only bounds the
# chance the DEFECT gets to show itself (the second combine's preview and reuse check take milliseconds); with the cure
# the second combine waits for the broker lock, the grace runs out and the first is released whatever the value.
_OVERLAP_GRACE_SECONDS = 3.0


def _as_detected_before_item_8(root: Path, file_id: str) -> None:
    """The sidecar as a build before item 8 left it, its catalogue not reading the export: no ``plugins_signature``, and no plugin.

    Its ``batch_id`` stays: those builds already stored it. Not 1.1.0's sidecar, which had none: see ``_store_as_1_1_0_did``.
    """
    path = root / BRIMFileStatus.UPLOADED.value / f"broker_{BROKER_ID}" / f"{file_id}.json"
    metadata = json.loads(path.read_text())
    metadata.pop("plugins_signature", None)
    metadata["compatible_plugins"] = []
    path.write_text(json.dumps(metadata, indent=2))


def _danske_pair_detected_before_item_8(root: Path) -> Tuple[str, Dict[str, BRIMFileInfo]]:
    """The synthetic Danske main pair, uploaded in one batch on ``BROKER_ID``, then left as a build before item 8 left it."""
    batch = str(uuid.uuid4())
    uploaded: Dict[str, BRIMFileInfo] = {}
    for name, role in DANSKE_PAIR:
        info = _member((DANSKE_SAMPLE_DIR / name).read_bytes(), name, batch_id=batch)
        assert DANSKE_CODE in info.compatible_plugins, f"premise: today's catalogue reads {name} as Danske: {info.compatible_plugins}"
        _as_detected_before_item_8(root, info.file_id)
        uploaded[role] = info
    return batch, uploaded


def _plugins_on_record() -> Dict[str, List[str]]:
    """The plugins each file of ``BROKER_ID`` is read with now, for a failure message."""
    return {info.filename: info.compatible_plugins for info in brim_provider.list_files(broker_ids=[BROKER_ID]) if info.target_broker_id == BROKER_ID}


class TestDanskePairDetectedBeforeItem8:
    """Item 8 — a Danske pair uploaded together, but detected before item 8, forms its set after the update without being uploaded again."""

    def test_collect_members_finds_both_files(self, set_storage: Path) -> None:
        collect_members, members_not_found = _sets("collect_members"), _sets("BRIMSetMembersNotFound")
        batch, uploaded = _danske_pair_detected_before_item_8(set_storage)

        try:
            members = collect_members(broker_id=BROKER_ID, plugin_code=DANSKE_CODE, batch_id=batch)
        except members_not_found as caught:
            pytest.fail(f"the set does not form ({caught.message}): its files are still read with the plugins stored before item 8: {_plugins_on_record()}", pytrace=False)

        assert _ids(members) == _ids(uploaded.values())
        assert all(DANSKE_CODE in member.compatible_plugins for member in members), [member.compatible_plugins for member in members]

    @pytest.mark.asyncio
    async def test_the_set_preview_is_complete(self, set_storage: Path, db_session: AsyncSession) -> None:
        preview_set, members_not_found = _sets("preview_set"), _sets("BRIMSetMembersNotFound")
        batch, uploaded = _danske_pair_detected_before_item_8(set_storage)

        try:
            preview = await preview_set(db_session, broker_id=BROKER_ID, plugin_code=DANSKE_CODE, batch_id=batch)
        except members_not_found as caught:
            pytest.fail(f"the set does not form ({caught.message}): its files are still read with the plugins stored before item 8: {_plugins_on_record()}", pytrace=False)

        assert {member.file_id: member.role for member in preview.members} == {uploaded["custody"].file_id: "custody", uploaded["cash"].file_id: "cash"}
        assert (preview.complete, preview.missing) == (True, []), (preview.missing, _codes(preview))


# An upload made while 1.1.0 (2026-09-07) was the release.
UPLOADED_WITH_1_1_0_AT = "2026-09-15T09:30:00+00:00"


def _store_as_1_1_0_did(root: Path, name: str) -> str:
    """One Danske sample, stored on ``BROKER_ID`` as 1.1.0's ``save_uploaded_file`` stored an upload; returns its file id.

    The data file, then a sidecar with the twelve keys 1.1.0 wrote and no other: no ``batch_id``, no
    ``plugins_signature``, no ``kind`` (``git show v1.1.0:backend/app/services/brim_provider.py``).
    ``compatible_plugins`` is what 1.1.0's catalogue detected: nothing, it had no Danske plugin.
    """
    content = (DANSKE_SAMPLE_DIR / name).read_bytes()
    file_id = str(uuid.uuid4())
    ext = Path(name).suffix.lower() or ".dat"
    folder = root / BRIMFileStatus.UPLOADED.value / f"broker_{BROKER_ID}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{file_id}{ext}").write_bytes(content)
    sidecar = {
        "file_id": file_id,
        "filename": name,
        "extension": ext,
        "size_bytes": len(content),
        "status": BRIMFileStatus.UPLOADED.value,
        "uploaded_at": UPLOADED_WITH_1_1_0_AT,
        "processed_at": None,
        "compatible_plugins": [],
        "error_message": None,
        "uploaded_by_user_id": USER_ID,
        "target_broker_id": BROKER_ID,
        "last_parse_result": None,
    }
    (folder / f"{file_id}.json").write_text(json.dumps(sidecar, indent=2))
    return file_id


class TestDanskePairUploadedWith1_1_0:
    """Limitation — a Danske pair uploaded with 1.1.0 is detected again after the update, but forms no set: it must be uploaded again, together.

    1.1.0 recorded no ``batch_id``, so its uploads are linked to nothing. Each file is offered Danske again, yet no
    batch's ``collect_members`` takes it (a set request names its batch, a string), and Danske's parse of one file
    alone answers 422 ``set_required``. Documented for users in danske-bank.en.md and for developers in
    brim_plugin_guide.md (the lifecycle of ``compatible_plugins``). Should this turn red because these files now
    belong to a set, the limitation is gone: update both pages with this test.
    """

    def test_is_detected_again_but_forms_no_set_and_must_be_uploaded_again_together(self, set_storage: Path) -> None:
        """The pair stored as 1.1.0 stored it, beside the same two exports uploaded again, together, after the update."""
        collect_members = _sets("collect_members")
        from_1_1_0 = {role: _store_as_1_1_0_did(set_storage, name) for name, role in DANSKE_PAIR}
        again = str(uuid.uuid4())
        uploaded_again = {role: _member((DANSKE_SAMPLE_DIR / name).read_bytes(), name, batch_id=again) for name, role in DANSKE_PAIR}
        assert all(DANSKE_CODE in info.compatible_plugins for info in uploaded_again.values()), f"premise: today's catalogue reads the pair as Danske: {[info.compatible_plugins for info in uploaded_again.values()]}"

        read = {role: _info(file_id) for role, file_id in from_1_1_0.items()}
        batches = sorted({info.batch_id for info in brim_provider.list_files(broker_ids=[BROKER_ID]) if info.batch_id is not None})
        sets = {batch: _ids(collect_members(broker_id=BROKER_ID, plugin_code=DANSKE_CODE, batch_id=batch)) for batch in batches}

        assert {role: info.compatible_plugins for role, info in read.items()} == {"custody": [DANSKE_CODE], "cash": [DANSKE_CODE]}, "the files uploaded with 1.1.0 are not offered Danske after the update"
        assert {role: info.batch_id for role, info in read.items()} == {"custody": None, "cash": None}, "a file uploaded with 1.1.0 reads with a batch, though 1.1.0 recorded none: see the class docstring"
        stored_by_1_1_0 = set(from_1_1_0.values())
        joined = {batch: members & stored_by_1_1_0 for batch, members in sets.items() if members & stored_by_1_1_0}
        assert not joined, f"a file uploaded with 1.1.0 joined a set, by batch: {joined}; the limitation is gone, see the class docstring"
        assert sets == {again: _ids(uploaded_again.values())}, f"uploaded again, together, the pair does not form exactly its own set; the sets on the broker, by batch: {sets}"


class _CombineGate:
    """Parks the first ``combine`` of the fake until it is released; marks the arrival of a second one."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._calls = 0
        self.first_inside = threading.Event()
        self.second_inside = threading.Event()
        self.release_first = threading.Event()

    def enter(self) -> None:
        with self._lock:
            self._calls += 1
            first = self._calls == 1
        if first:
            self.first_inside.set()
            self.release_first.wait(timeout=_WAIT_SECONDS)
        else:
            self.second_inside.set()

    def release_everything(self) -> None:
        """Never leave a thread parked on the gate, whatever happened to the test."""
        self.release_first.set()
        self.first_inside.set()
        self.second_inside.set()


def _gated_fake(gate: _CombineGate) -> type:
    """The two-role fake whose ``combine`` passes ``gate`` first (the registry builds an instance per call: the gate is shared)."""

    class _GatedCombineProvider(_FakeTwoRoleProvider):
        def combine(self, members: Dict[str, List[Path]]) -> Any:
            gate.enter()
            return super().combine(members)

    return _GatedCombineProvider


@contextlib.asynccontextmanager
async def _second_db_session() -> AsyncIterator[AsyncSession]:
    """Another private in-memory database, like ``db_session``: two requests at once have a session each."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


class TestConcurrentCombine:
    """F1 — two ``combine_set`` of one set at once leave one combined file; the second answers ``reused=True`` with it."""

    @pytest.mark.asyncio
    async def test_two_concurrent_combines_of_one_set_build_one_combined_file(self, set_storage: Path, fake_plugin: BRIMProvider, db_session: AsyncSession) -> None:
        """The count is the subject: the combined files of this test's own broker and upload, in its own storage."""
        combine_set = _sets("combine_set")
        batch, custody, cash = _two_member_set()
        gate = _CombineGate()
        # Same code, a fake whose combine is gated. `fake_plugin` restores the whole registry afterwards.
        BRIMProviderRegistry._providers[FAKE_CODE] = _gated_fake(gate)
        request = {"broker_id": BROKER_ID, "plugin_code": FAKE_CODE, "batch_id": batch, "user_id": USER_ID}
        first_inside = overlapped = False
        async with _second_db_session() as second_session:
            calls = [asyncio.create_task(combine_set(db_session, **request))]
            try:
                first_inside = await asyncio.to_thread(gate.first_inside.wait, _WAIT_SECONDS)
                if first_inside:
                    calls.append(asyncio.create_task(combine_set(second_session, **request)))
                    overlapped = await asyncio.to_thread(gate.second_inside.wait, _OVERLAP_GRACE_SECONDS)
            finally:
                gate.release_everything()
                outcomes = await asyncio.wait_for(asyncio.gather(*calls, return_exceptions=True), timeout=_WAIT_SECONDS)

        assert first_inside, f"premise: the first combine never reached the plugin: {outcomes!r}"
        failures = [outcome for outcome in outcomes if isinstance(outcome, BaseException)]
        assert not failures, f"a concurrent combine failed: {failures!r}"
        combined = [info for info in _combined_files() if info.batch_id == batch]
        assert len(combined) == 1, f"two combines of one set at once built {len(combined)} combined files (the second reached the plugin while the first was inside it: {overlapped}): {[info.file_id for info in combined]}"
        assert sorted(outcome.reused for outcome in outcomes) == [False, True], [(outcome.reused, outcome.combined.file_id) for outcome in outcomes]
        assert {outcome.combined.file_id for outcome in outcomes} == {combined[0].file_id}
        assert (_info(custody.file_id).combined_into, _info(cash.file_id).combined_into) == ([combined[0].file_id], [combined[0].file_id])
