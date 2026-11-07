"""
The storage bar's numbers (lot FB-29 backend, interface §3, §4): ``GET /api/v1/backup/instance/storage``, and the guard that
the hosting panel's routes and its status do not move.

Under test: ``backend/app/api/v1/backup/instance.py`` (``get_instance_storage``), ``backend/app/schemas/backup.py``
(``InstanceStorage``) and the service ``services/platform/storage_usage.py``, which has its own suite, ``services
storage-usage``.

Contract (``B6r-fb29-interface.md`` §4, §6):

- STORAGE-001, who: without a session 401, an ordinary user 403, an administrator 200.
- STORAGE-002, the answer: exactly the fields of ``InstanceStorage`` (``extra="forbid"``) and of the service's
  ``StorageUsage``: the five parts, ``data_bytes``, the three ``volume_*`` and ``limit_mb`` / ``limit_locked``.
- STORAGE-003, the parts reflect the files the test plants (a file in ``custom-uploads/``, one in ``broker_reports/``,
  a kept backup folder, the database, a log); a later request shows a later file (nothing is cached).
- STORAGE-004, the limit: ``limit_mb`` / ``limit_locked`` are the row ``storage_limit_mb`` (0 is ``null``), unlocked; the
  variable ``LIBREFOLIO_STORAGE_LIMIT_MB`` when set and valid, locked (0 is ``null``, locked); an invalid variable is ignored
  and the row speaks, unlocked.
- STORAGE-005, a measurement that fails is never a 500: 200, the byte fields 0 and the volume ``null``.
- STORAGE-006, the route is a plain ``def`` (not ``async``: it walks a folder), and it is NOT in
  ``ALLOWED_WHEN_BLOCKED``.
- STORAGE-007, OpenAPI: ``GET /backup/instance/storage`` answers ``InstanceStorage`` for a session, not the panel's token;
  no new route under ``/backup/panel``.
- STORAGE-008 (GUARD, green before and after): ``GET /panel/status`` is unchanged, ``PanelStatusResponse`` holds exactly the
  ten keys it held at the base commit and none starts with ``storage``.

Pure (``isolation="pure"``): an app of the test holds ``backup_router`` under ``/api/v1``; ``get_current_user`` answers
the administrator (or an ordinary user, or the real one for the 401), so the real ``require_admin`` decides. The data
directory is a folder under ``tmp_path`` configured as the process's, the row of the limit is in a private SQLite file read
through a synchronous engine put in place of the process's (``get_sync_engine``), so no lane database, server, data
directory or network is reached. Every assertion is about files the test planted.
"""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.routing import iter_route_contexts
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from backend.app.api.v1 import instance_block
from backend.app.api.v1.auth import get_current_user
from backend.app.api.v1.backup import backup_router
from backend.app.api.v1.backup import instance as instance_api
from backend.app.api.v1.panel import panel_router
from backend.app.config import get_data_dir
from backend.app.db.base import SQLModel
from backend.app.db.models import GlobalSetting
from backend.app.schemas.hosting_panel import PanelStatusResponse
from backend.test_scripts.test_api.test_backup_api import BACKUP_ROUTES
from backend.test_scripts.test_api.test_panel_status_api import ANSWER_KEYS as PANEL_STATUS_KEYS
from backend.test_scripts.test_utils import print_section, print_success

IN_PROCESS = "http://in-process"
STORAGE = "/api/v1/backup/instance/storage"
VARIABLE = "LIBREFOLIO_STORAGE_LIMIT_MB"
KEY = "storage_limit_mb"
SERVICE = "backend.app.services.platform.storage_usage"

ADMIN = SimpleNamespace(id=1, username="fb29-admin", is_superuser=True)
REGULAR = SimpleNamespace(id=2, username="fb29-user", is_superuser=False)

BYTE_FIELDS = ["database_bytes", "uploads_bytes", "broker_reports_bytes", "backups_bytes", "other_bytes", "restore_bytes", "data_bytes"]
VOLUME_FIELDS = ["volume_total_bytes", "volume_used_bytes", "volume_free_bytes"]
FIELDS = {*BYTE_FIELDS, *VOLUME_FIELDS, "limit_mb", "limit_locked"}


# =============================================================================
# The instance of a test, the app, the requests
# =============================================================================


class Instance:
    """A data directory of the test (the process's own for the test) and the row of the limit in a private database."""

    def __init__(self, data: Path, database: Path):
        self.data = data
        self.database = database

    def plant(self, relative: str, size: int) -> None:
        path = self.data / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * size)

    def set_limit(self, value: str | None) -> None:
        """The row ``storage_limit_mb`` of the private database: ``value``, or no row at all for None."""
        engine = create_engine(f"sqlite:///{self.database}", poolclass=NullPool)
        try:
            with Session(engine) as session:
                for row in session.query(GlobalSetting).filter(GlobalSetting.key == KEY):  # type: ignore[arg-type]
                    session.delete(row)
                if value is not None:
                    session.add(GlobalSetting(key=KEY, value=value, value_type="int", description="", updated_by_user_id=None))
                session.commit()
        finally:
            engine.dispose()


@pytest.fixture
def instance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Instance]:
    """An empty data directory configured as this process's, and a private database for the limit's row put in place of
    the process's own (outside the data directory, so it weighs nothing there)."""
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.delenv("LIBREFOLIO_TEST_MODE", raising=False)
    monkeypatch.delenv("LIBREFOLIO_TEST_DATA_DIR", raising=False)
    monkeypatch.setenv("LIBREFOLIO_DATA_DIR", str(data))
    monkeypatch.delenv(VARIABLE, raising=False)
    assert get_data_dir() == data.resolve(), f"precondition: the configured data directory must be the test's, not {get_data_dir()}"

    database = tmp_path / "limit.db"
    engine = create_engine(f"sqlite:///{database}", poolclass=NullPool)
    SQLModel.metadata.create_all(engine)
    engine.dispose()

    def make():
        return create_engine(f"sqlite:///{database}", poolclass=NullPool)

    for name in ("backend.app.db.session", "backend.app.db"):
        monkeypatch.setattr(importlib.import_module(name), "get_sync_engine", make)
    try:
        monkeypatch.setattr(importlib.import_module(SERVICE), "get_sync_engine", make, raising=False)
    except ModuleNotFoundError as exc:
        if exc.name != SERVICE:
            raise
    yield Instance(data, database)


def service():
    """The service module; absent, every test that needs it is red with this reason."""
    try:
        return importlib.import_module(SERVICE)
    except ModuleNotFoundError as exc:
        if exc.name != SERVICE:
            raise
        pytest.fail(f"[new] {SERVICE} does not exist yet: lot FB-29 brings it (§3)", pytrace=False)


def backup_app(user: SimpleNamespace | None = ADMIN) -> FastAPI:
    """``backup_router`` under ``/api/v1``; ``get_current_user`` answers ``user``, so the real ``require_admin`` decides;
    None leaves the real one, which refuses a request with no session (401)."""
    app = FastAPI()
    app.include_router(backup_router, prefix="/api/v1")
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return app


async def call(method: str, path: str, *, app: FastAPI | None = None, **request: Any) -> httpx.Response:
    """One request to an app of the test, an administrator's by default. An exception a route does not turn into an
    answer comes back as a plain 500 and fails an assertion instead of erroring."""
    transport = httpx.ASGITransport(app=app or backup_app(), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url=IN_PROCESS) as client:
        return await client.request(method, path, **request)


def shown(response: httpx.Response) -> str:
    return f"{response.request.method} {response.request.url} answered {response.status_code}: {response.text[:600]}"


async def storage() -> dict:
    response = await call("GET", STORAGE)
    assert response.status_code == 200, f"an administrator reads the storage: {shown(response)}"
    return response.json()


# =============================================================================
# STORAGE-001 / 002: who, and the shape
# =============================================================================


@pytest.mark.asyncio
async def test_the_storage_is_for_administrators_only(instance):
    """STORAGE-001: no session 401, an ordinary user 403, an administrator 200. Red today: no such route (404)."""
    print_section("STORAGE-001: GET /backup/instance/storage, who")
    anonymous = await call("GET", STORAGE, app=backup_app(None))
    ordinary = await call("GET", STORAGE, app=backup_app(REGULAR))
    admin = await call("GET", STORAGE)
    assert anonymous.status_code == 401, f"without a session the route answers 401: {shown(anonymous)}"
    assert ordinary.status_code == 403, f"an ordinary user gets 403: {shown(ordinary)}"
    assert admin.status_code == 200, f"an administrator gets 200: {shown(admin)}"
    print_success("401 / 403 / 200")


@pytest.mark.asyncio
async def test_the_answer_has_exactly_the_fields_of_the_schema(instance):
    """STORAGE-002: the twelve fields (C9-7: restore_bytes), no more, no fewer; byte fields are integers, the volume integers or null."""
    body = await storage()
    assert set(body) == FIELDS, f"exactly {sorted(FIELDS)}: extra {sorted(set(body) - FIELDS)}, missing {sorted(FIELDS - set(body))}"
    for name in BYTE_FIELDS:
        assert type(body[name]) is int and body[name] >= 0, f"{name} is a whole number of bytes: {body[name]!r}"
    for name in VOLUME_FIELDS:
        assert body[name] is None or (type(body[name]) is int and body[name] >= 0), f"{name} is bytes, or null: {body[name]!r}"
    assert body["limit_mb"] is None or type(body["limit_mb"]) is int
    assert type(body["limit_locked"]) is bool
    assert body["data_bytes"] == sum(body[name] for name in BYTE_FIELDS if name != "data_bytes"), "the parts add up to the whole"


def test_the_schema_forbids_extra_fields_and_holds_the_eleven():
    from backend.app.schemas import backup as schemas  # noqa: PLC0415

    schema = getattr(schemas, "InstanceStorage", None)
    assert schema is not None, "red until FB-29: backend/app/schemas/backup.py has no InstanceStorage"
    assert set(schema.model_fields) == FIELDS, f"the fields of the contract: {sorted(schema.model_fields)}"
    assert schema.model_config.get("extra") == "forbid", "extra='forbid', as the other schemas of the module"
    with pytest.raises(ValueError):
        schema(**dict.fromkeys(FIELDS, 0), surprise=1)


# =============================================================================
# STORAGE-003: the parts reflect the files
# =============================================================================


@pytest.mark.asyncio
async def test_the_parts_reflect_the_files_the_test_planted(instance):
    """STORAGE-003: a file in each part, then one more in the uploads: the second request shows it."""
    print_section("STORAGE-003: the parts")
    instance.plant("sqlite/app.db", 100)
    instance.plant("custom-uploads/a/photo.bin", 300)
    instance.plant("broker_reports/report.csv", 70)
    instance.plant("backups/librefolio-backup-20261001-000000-ui-0123abcd/archive.zip", 1000)
    instance.plant("backups/.jobs/job/state.json", 10)
    instance.plant("logs/app.log", 20)

    body = await storage()
    assert (body["database_bytes"], body["uploads_bytes"], body["broker_reports_bytes"], body["backups_bytes"], body["other_bytes"]) == (100, 300, 70, 1010, 20), f"the parts as planted: {body}"
    assert body["data_bytes"] == 1500

    instance.plant("custom-uploads/b.bin", 5)
    later = await storage()
    assert (later["uploads_bytes"], later["data_bytes"]) == (305, 1505), "a file planted later shows in the next answer"
    print_success("parts exact, and read fresh each time")


@pytest.mark.asyncio
async def test_an_empty_data_directory_weighs_nothing(instance):
    body = await storage()
    assert [body[name] for name in BYTE_FIELDS] == [0] * len(BYTE_FIELDS), f"nothing planted, nothing weighed: {body}"


# =============================================================================
# STORAGE-004: the limit
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(("row", "expected"), [(None, None), ("0", None), ("300", 300), ("abc", None)])
async def test_the_limit_is_the_row_when_no_variable_is_set(instance, row, expected):
    instance.set_limit(row)
    body = await storage()
    assert (body["limit_mb"], body["limit_locked"]) == (expected, False), f"row {row!r}: {body}"


@pytest.mark.asyncio
@pytest.mark.parametrize(("text", "expected"), [("500", 500), ("0", None), (" 40 ", 40)])
async def test_the_variable_wins_and_locks(instance, monkeypatch, text, expected):
    """A row of 300 is saved; the variable decides, the answer says locked (0 is null, still locked)."""
    instance.set_limit("300")
    monkeypatch.setenv(VARIABLE, text)
    body = await storage()
    assert (body["limit_mb"], body["limit_locked"]) == (expected, True), f"variable {text!r}: {body}"


@pytest.mark.asyncio
async def test_an_invalid_variable_is_ignored_and_does_not_lock(instance, monkeypatch):
    instance.set_limit("300")
    monkeypatch.setenv(VARIABLE, "abc")
    body = await storage()
    assert (body["limit_mb"], body["limit_locked"]) == (300, False), f"the row speaks: {body}"


# =============================================================================
# STORAGE-005: a failing measurement is never a 500
# =============================================================================


def patch_measure(monkeypatch: pytest.MonkeyPatch, replacement) -> None:
    """``measure_storage`` replaced wherever the route may reach it: the service module, and the route's module were it to
    bind the name."""
    monkeypatch.setattr(service(), "measure_storage", replacement)
    monkeypatch.setattr(instance_api, "measure_storage", replacement, raising=False)


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [OSError("disk gone"), PermissionError("denied"), RuntimeError("anything")])
async def test_a_measurement_that_fails_is_a_200_of_zeros(instance, monkeypatch, error):
    """STORAGE-005: the service raises (it should not, but the route does not rely on it): 200, the six byte fields 0, the
    volume null; the limit fields keep their types."""
    instance.plant("custom-uploads/a.bin", 123)

    def failing(*_args, **_kwargs):
        raise error

    patch_measure(monkeypatch, failing)
    response = await call("GET", STORAGE)
    assert response.status_code == 200, f"a failing measure is not a 500: {shown(response)}"
    body = response.json()
    assert set(body) == FIELDS, f"the same eleven fields: {sorted(body)}"
    assert [body[name] for name in BYTE_FIELDS] == [0] * len(BYTE_FIELDS), f"the bytes read 0: {body}"
    assert [body[name] for name in VOLUME_FIELDS] == [None] * 3, f"and the volume null: {body}"
    assert type(body["limit_locked"]) is bool


@pytest.mark.asyncio
async def test_the_route_hands_the_limit_it_read_to_the_service(instance, monkeypatch):
    """STORAGE-005b: the route reads the limit (``read_limit``) and measures the process's data directory with it."""
    real = service().measure_storage
    calls: list[tuple[Path, dict]] = []

    def spy(data_dir, **kwargs):
        calls.append((Path(data_dir).resolve(), kwargs))
        return real(data_dir, **kwargs)

    patch_measure(monkeypatch, spy)
    instance.set_limit("300")
    monkeypatch.setenv(VARIABLE, "500")
    body = await storage()
    assert calls, "the route measured through measure_storage"
    data_dir, kwargs = calls[-1]
    assert data_dir == instance.data.resolve(), f"the data directory of the process: {data_dir}"
    assert (kwargs.get("limit_mb"), kwargs.get("limit_locked")) == (500, True), f"measure_storage was given the limit read: {kwargs}"
    assert (body["limit_mb"], body["limit_locked"]) == (500, True)


# =============================================================================
# STORAGE-006: a plain def, and not allowed on a blocked instance
# =============================================================================


def test_the_route_is_a_plain_def_registered_between_the_list_and_the_job():
    endpoint = getattr(instance_api, "get_instance_storage", None)
    assert endpoint is not None, "red until FB-29: instance.py has no get_instance_storage"
    assert not inspect.iscoroutinefunction(endpoint), "a plain def: it walks a folder, FastAPI runs it in a thread"
    # This FastAPI keeps an included router as one wrapper in `.routes`: `iter_route_contexts` yields the effective routes.
    contexts = list(iter_route_contexts(backup_router.routes))
    served = [ctx for ctx in contexts if getattr(ctx, "path", "").endswith("/instance/storage")]
    assert len(served) == 1 and served[0].endpoint is endpoint and served[0].methods == {"GET"}, f"one GET route: {served}"
    names = [getattr(ctx, "name", "") for ctx in contexts]
    assert names.index("get_instance_storage") == names.index("list_instance_backups") + 1, f"registered right after the list of the kept backups: {names[:8]}"
    assert names.index("get_instance_storage") + 1 == names.index("get_instance_backup_job"), "and before /instance/jobs/{job_id}"


def test_the_route_is_not_allowed_on_a_blocked_instance():
    """A blocked instance lets an administrator take the data away (backups), not read the bar: the function is not in
    ``ALLOWED_WHEN_BLOCKED`` (as ``test_address_probe_image.py`` pins it for the probe)."""
    endpoint = getattr(instance_api, "get_instance_storage", None)
    assert endpoint is not None, "red until FB-29: instance.py has no get_instance_storage"
    assert endpoint not in instance_block.ALLOWED_WHEN_BLOCKED, f"{endpoint.__module__}.{endpoint.__name__} must stay outside instance_block.ALLOWED_WHEN_BLOCKED"


# =============================================================================
# STORAGE-007: OpenAPI
# =============================================================================


def schema_ref(operation: dict, status: str = "200") -> str | None:
    content = operation.get("responses", {}).get(status, {}).get("content", {}).get("application/json", {})
    return content.get("schema", {}).get("$ref", "").rsplit("/", 1)[-1] or None


def test_the_route_is_documented_as_instance_storage_for_a_session():
    document = backup_app().openapi()
    operation = document["paths"].get(STORAGE, {}).get("get")
    assert operation is not None, f"GET /backup/instance/storage is documented: {sorted(p for p in document['paths'] if p.startswith('/api/v1/backup/instance'))}"
    assert schema_ref(operation) == "InstanceStorage", f"it answers InstanceStorage: {schema_ref(operation)}"
    schema = document["components"]["schemas"]["InstanceStorage"]
    assert set(schema["properties"]) == FIELDS, f"InstanceStorage holds exactly {sorted(FIELDS)}: {sorted(schema['properties'])}"
    assert schema.get("additionalProperties") is False, f"and forbids any other: {schema}"
    assert "BackupPanelToken" not in repr(operation.get("security")), "it asks for a session, not the panel's token"


def test_no_route_was_added_under_the_panel():
    """GUARD (green before and after): the paths under ``/backup/panel`` are the ones ``BACKUP_ROUTES`` lists, none about storage."""
    document = backup_app().openapi()
    served = {path for path in document["paths"] if path.startswith("/api/v1/backup/panel")}
    expected = {f"/api/v1{path}" for _method, path, _endpoint in BACKUP_ROUTES if path.startswith("/backup/panel")}
    assert served == expected, f"the panel's paths: added {sorted(served - expected)}, removed {sorted(expected - served)}"
    assert not [path for path in served if "storage" in path], "nothing about storage under /backup/panel"


# =============================================================================
# STORAGE-008: GET /panel/status does not change
# =============================================================================


def test_the_panel_status_keeps_its_ten_keys_and_gains_no_storage_key():
    """GUARD (green before and after): ``PanelStatusResponse`` holds exactly the keys the status test pins, none about
    storage (``storage_used_mb`` and ``storage_limit_mb`` stay for after 1.4)."""
    assert set(PanelStatusResponse.model_fields) == PANEL_STATUS_KEYS, f"the keys of GET /panel/status: {sorted(PanelStatusResponse.model_fields)}"
    assert not [name for name in PanelStatusResponse.model_fields if name.startswith("storage")], "no storage_* key in the panel's status"
    app = FastAPI()
    app.include_router(panel_router, prefix="/api/v1/panel")
    document = app.openapi()
    properties = document["components"]["schemas"]["PanelStatusResponse"]["properties"]
    assert set(properties) == PANEL_STATUS_KEYS, f"and so does the document: {sorted(properties)}"
    assert [path for path in document["paths"] if "storage" in path] == [], "no storage route under /panel"
