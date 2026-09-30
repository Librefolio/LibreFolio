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

Design: LibreFolio_developer_journal/Release_2/Phase_0/26_brimDanskeBank/design-phase00BrimReportSets.md (v5.3), §3.1–§3.5 and §3.8
Plan: LibreFolio_developer_journal/Release_2/Phase_0/26_brimDanskeBank/plan-phase00BrimDanskeBankStep4Implementation.prompt.md, §3 A1
"""

from __future__ import annotations

import csv
import inspect
import json
import shutil
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest
from pydantic import ValidationError

from backend.app.schemas import brim as brim_schemas
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMEvidence, BRIMFileInfo, BRIMFileStatus, BRIMNotice, BRIMParseOutput, BRIMParseResponse, BRIMPluginInfo
from backend.app.schemas.common import Currency, DateRangeModel
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


def _missing(what: str) -> None:
    """Fail the current test (not the collection), naming what phase A1 has to add."""
    pytest.fail(f"{what}: not implemented yet (BRIM report sets, phase A1)", pytrace=False)


def _schema(name: str) -> Any:
    """A new schema class from ``backend.app.schemas.brim``."""
    found = getattr(brim_schemas, name, None)
    if found is None:
        _missing(f"backend.app.schemas.brim.{name} does not exist")
    return found


def _service(name: str) -> Any:
    """A new function or exception from ``backend.app.services.brim_provider``."""
    found = getattr(brim_provider, name, None)
    if found is None:
        _missing(f"backend.app.services.brim_provider.{name} does not exist")
    return found


def _require_fields(model: Any, *names: str) -> None:
    """The model declares every field in ``names``."""
    absent = [name for name in names if name not in model.model_fields]
    if absent:
        _missing(f"{model.__name__} has no field {', '.join(absent)}")


def _require_contract(*names: str) -> None:
    """``BRIMProvider`` itself, not a subclass, defines every member in ``names``."""
    absent = [name for name in names if not hasattr(BRIMProvider, name)]
    if absent:
        _missing(f"BRIMProvider has no {', '.join(absent)}")


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
        """Rows and covered dates of one member: trade dates for custody, value dates for cash."""
        member_summary, coverage = _schema("BRIMMemberSummary"), _schema("BRIMCoverage")
        role = self.detect_role(file_path)
        dates = [date.fromisoformat(cells[1]) for _line, cells in self._rows(file_path)]
        spans = [coverage(axis="trade" if role == "custody" else "value", start=min(dates), end=max(dates))] if dates else []
        return member_summary(role=role, rows=len(dates), coverage=spans, account_fingerprint=FAKE_ACCOUNT if role == "custody" else None)

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
        """A sidecar written before A1, with none of the new keys, still builds, as an unlinked original."""
        legacy = _info(_write_legacy_file(isolated_brim_dir))  # precondition, true before A1 too
        _require_fields(BRIMFileInfo, *NEW_FILE_INFO_FIELDS)

        assert (legacy.batch_id, legacy.kind, legacy.derived_from, legacy.combined_into, legacy.combine_is_stale) == (None, "original", [], [], False)
        assert (legacy.filename, legacy.target_broker_id, legacy.compatible_plugins) == ("legacy.csv", BROKER_ID, ["broker_generic_csv"])


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
