"""
The «awaiting restore» mode through the API (LibreFolio 1.3, workstream H, lot H-62): contract L3 §6, with R4, and the
coordinator's answers Q5 (the mode's 423 is for anyone, no session asked) and Q7, replaced by D7 (developer, contract L3
§10, option A: ``GET /panel/status`` with a restore state it cannot read answers 200, ``restore.state == "unreadable"``
with the reader's ``reason``, instead of Q7's 500 ``restore_state_unreadable``).

Under test, written by H-62 and missing today:

- ``backend.app.api.v1.instance_block.refuse_when_awaiting_restore``, a dependency of the ``/api/v1`` router right after
  ``refuse_when_blocked``, with ``INSTANCE_AWAITING_RESTORE_CODE = "instance_awaiting_restore"`` and the allowed set
  ``ALLOWED_WHEN_AWAITING_RESTORE``: the health probes, readiness, the version, the public configuration, the scheduled
  wake-up, the panel's status, the four backup jobs of the panel and the seven routes of the panel's restore. With
  ``LIBREFOLIO_AWAIT_RESTORE`` on, every other ``/api/v1`` route answers 423 ``instance_awaiting_restore`` to anyone —
  registration, the first administrator's ``/auth/setup``, the login and ``/auth/me`` included. The set is pinned by
  name and route, as ``test_instance_block.py`` pins ``ALLOWED_WHEN_BLOCKED``.
- ``GET /system/ready`` → 200 with ``mode: awaiting_restore`` (``ReadinessResponse.mode``, ``normal|awaiting_restore``);
  ``GET /system/instance`` → ``mode: awaiting_restore`` (``InstanceConfigResponse.mode``); both ``normal`` outside it.
  ``POST /system/wake-sync`` with its token → 200, ``status: awaiting_restore``, no job, nothing past the scheduler's
  switches.
- Both switches on: a signed-in user meets 423 on a user route (either code). R4: after a committed restore, a process
  with ``LIBREFOLIO_BLOCKED=1`` and without ``LIBREFOLIO_AWAIT_RESTORE`` answers 423 ``instance_blocked`` at the first
  request of a signed-in user — the switches are read at each call, no window opens between the mode and the block.
- ``GET /panel/status`` adds ``mode`` (``normal|awaiting_restore``) and ``restore``: null without a restore recorded,
  else exactly ``{state, reason, waiting, backup_created_at, stage_id}``, ``state`` as ``RestoreStatus.state`` (a
  restore being applied is ``in_progress``), never the name of whoever confirmed it; a state it cannot read (D7) → 200,
  ``restore == {"state": "unreadable", "reason": <io|not_a_file|invalid>, "waiting": null, "backup_created_at": null,
  "stage_id": null}``. ``PanelRestoreSummary.state`` admits ``unreadable``, its ``reason`` the reasons of a rollback or of
  an unreadable state. Red until D7: the route answers Q7's 500.

``# Needs B (Q3)``, apart at the end (class ``TestNeedsB``): ``POST /backup/panel/jobs`` in the mode → 409
``backup_awaiting_restore``, and no backup starts (a backup of an empty volume never exists).

How. The switches are read from the process environment, so nothing here runs on the lane's backend: the app of
``backend/app/main.py`` runs in this process through ``httpx.ASGITransport`` (its lifespan does not run), every
variable set through ``monkeypatch``. Test mode on ``tmp_path/data``; every request's database session is on a private
SQLite file under ``tmp_path`` with the ORM schema, the default settings of a new install and ``alembic_version`` at the
head (so readiness can answer ready); a signed-in user is an account of that file with a session cookie this process
mints, as a login would. The panel's attempts limiter and the activity record are the test's own. The scheduler's
collaborators past its switches are traps in the wake-up case. Every name of H-62 (and B) is imported by the test that
needs it, so the file collects and each test reports its own red; the case that sends a request to every route checks
first that the mode's dependency guards each of them, so before H-62 it sends nothing.

Isolation: pure. No server, no lane database, no network, no file outside ``tmp_path``.
"""

from __future__ import annotations

import errno
import importlib
import json
import os
import re
import secrets
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, NoReturn
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.routing import APIRoute, iter_route_contexts
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.api.v1.auth import SESSION_COOKIE_NAME
from backend.app.api.v1.instance_block import refuse_when_blocked
from backend.app.api.v1.system import wake as wake_module
from backend.app.config import API_V1_PREFIX, get_data_dir, is_test_mode
from backend.app.db.base import SQLModel  # imports every model: the private database gets the whole ORM schema
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.services.accounts.auth_service import create_jwt_token
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.platform import client_address as client_address_module
from backend.app.services.platform.hosting_panel import access as access_module
from backend.app.services.platform.instance_backup import apply as apply_module
from backend.app.services.platform.instance_backup import jobs as backup_jobs
from backend.app.services.platform.instance_backup.paths import SWAPPED_FOLDERS, restore_state_path
from backend.app.services.platform.readiness import alembic_head_revision
from backend.app.services.platform.scheduler import scheduler
from backend.app.services.platform.sleep_wake import activity as activity_module
from backend.app.services.platform.sleep_wake import idle_monitor
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.test_utils import print_section, print_success

# =============================================================================
# THE CONTRACT, SPELLED OUT
# =============================================================================

BLOCK_MODULE = "backend.app.api.v1.instance_block"
AWAIT_VARIABLE = "LIBREFOLIO_AWAIT_RESTORE"
BLOCKED_VARIABLE = "LIBREFOLIO_BLOCKED"
DELETION_DATE_VARIABLE = "LIBREFOLIO_DELETION_DATE"
AWAITING_CODE = "instance_awaiting_restore"
BLOCKED_CODE = "instance_blocked"
MODES = ("normal", "awaiting_restore")

#: Every endpoint the mode lets through, by name, with the one route it serves (§6). An addition goes through the
#: developer first: this pin makes it show in review.
ALLOWED_WHEN_AWAITING_RESTORE_ROUTES = {
    "backend.app.api.v1.system.health.health_check": ("GET", "/api/v1/system/health"),
    "backend.app.api.v1.system.health.test_lane_health": ("GET", "/api/v1/system/test-lane-health"),
    "backend.app.api.v1.system.ready.get_readiness": ("GET", "/api/v1/system/ready"),
    "backend.app.api.v1.system.info.get_system_info": ("GET", "/api/v1/system/info"),
    "backend.app.api.v1.system.instance.get_instance_config": ("GET", "/api/v1/system/instance"),
    "backend.app.api.v1.system.wake.wake_sync": ("POST", "/api/v1/system/wake-sync"),
    "backend.app.api.v1.panel.get_panel_status": ("GET", "/api/v1/panel/status"),
    "backend.app.api.v1.backup.panel.start_panel_backup": ("POST", "/api/v1/backup/panel/jobs"),
    "backend.app.api.v1.backup.panel.get_panel_backup_job": ("GET", "/api/v1/backup/panel/jobs/{job_id}"),
    "backend.app.api.v1.backup.panel.download_panel_backup": ("GET", "/api/v1/backup/panel/jobs/{job_id}/file"),
    "backend.app.api.v1.backup.panel.delete_panel_backup_job": ("DELETE", "/api/v1/backup/panel/jobs/{job_id}"),
    "backend.app.api.v1.backup.panel_restore.upload_panel_restore_archive": ("PUT", "/api/v1/backup/panel/restore/upload"),
    "backend.app.api.v1.backup.panel_restore.start_panel_restore_check": ("POST", "/api/v1/backup/panel/restore/stage"),
    "backend.app.api.v1.backup.panel_restore.get_panel_restore_check": ("GET", "/api/v1/backup/panel/restore/stage/{stage_id}"),
    "backend.app.api.v1.backup.panel_restore.confirm_panel_restore_check": ("POST", "/api/v1/backup/panel/restore/stage/{stage_id}/confirm"),
    "backend.app.api.v1.backup.panel_restore.restart_panel_restore": ("POST", "/api/v1/backup/panel/restore/restart"),
    "backend.app.api.v1.backup.panel_restore.get_panel_restore_status": ("GET", "/api/v1/backup/panel/restore/status"),
    "backend.app.api.v1.backup.panel_restore.cancel_panel_pending_restore": ("DELETE", "/api/v1/backup/panel/restore/pending"),
}

#: The routes under /api/v1 no router dependency reaches: the API documentation (``test_instance_block.py`` pins them).
DOCUMENTATION_PATHS = frozenset({"/api/v1/docs", "/api/v1/docs/swagger-init.js", "/api/v1/openapi.json", "/api/v1/redoc", "/api/v1/redoc/redoc-init.js"})

#: The panel's variables, cleared before each test; the status, wake and backup tokens of the cases that need them.
STATUS_TOKEN_VARIABLE = "LIBREFOLIO_PANEL_STATUS_TOKEN"
WAKE_TOKEN_VARIABLE = "LIBREFOLIO_WAKE_TOKEN"
BACKUP_TOKEN_VARIABLE = "LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN"
PANEL_ENVIRONMENT = tuple(name for variable in (STATUS_TOKEN_VARIABLE, WAKE_TOKEN_VARIABLE, BACKUP_TOKEN_VARIABLE, "LIBREFOLIO_PANEL_PUBLIC_KEYS") for name in (variable, variable + "_FILE")) + ("LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS", "LIBREFOLIO_PUBLIC_URL")

#: ``GET /panel/status``: the keys of its answer, and of its ``restore``.
PANEL_STATUS_KEYS = frozenset({"admin_setup", "setup_expires_at", "mode", "restore"})
PANEL_RESTORE_KEYS = frozenset({"state", "reason", "waiting", "backup_created_at", "stage_id"})
STAGE_ID = "0123456789abcdef0123456789abcdef"
BACKUP_CREATED_AT = datetime(2026, 10, 23, 3, 0, 12, tzinfo=UTC)
#: Whoever confirmed a restore: a canary, never in the panel's status.
CONFIRMED_BY = "h62canary_confirmer"

#: D7: the reasons B's reader gives a restore state it cannot read (``apply.RestoreStateUnreadableError.reason``), and
#: the panel status's ``restore`` for each (contract L3 §10, option A).
UNREADABLE_REASONS = ("io", "not_a_file", "invalid")
#: The reasons of a rolled-back restore (``RestoreStatus.reason``), which ``PanelRestoreSummary.reason`` keeps taking.
ROLLBACK_REASONS = ("first_start_failed", "swap_interrupted", "swap_failed", "stage_missing")
UNREADABLE_STATE = "unreadable"


def unreadable_restore(reason: str) -> dict[str, Any]:
    """The panel status's ``restore`` for a state that cannot be read (D7): its state and reason, nothing else known."""
    return {"state": UNREADABLE_STATE, "reason": reason, "waiting": None, "backup_created_at": None, "stage_id": None}


#: What the scheduler reaches past its switches (``test_system_wake.py``): none of it in the mode.
PAST_THE_SWITCHES = ("am_i_leader", "load_scheduler_settings", "load_state", "save_state", "due_current_price", "due_history_sync", "run_current_price_refresh", "run_history_sync")

PASSWORD = "AwaitRestorePass123!"
BASE_URL = "http://h62-mode.test"
TIMEOUT = 60.0
_PATH_PARAMETER = re.compile(r"\{[^}]+\}")


_MISSING = object()


def h62(module: str, name: str) -> Any:
    """``module.name`` of H-62, read by the test that needs it: each test fails on its own while it is missing."""
    imported = importlib.import_module(module)
    value = getattr(imported, name, _MISSING)
    if value is _MISSING:
        pytest.fail(f"H-62: {module} gives no {name}")
    return value


# =============================================================================
# THE APP IN PROCESS, ON A PRIVATE DATABASE
# =============================================================================


@pytest.fixture(scope="module")
def app() -> FastAPI:
    assert is_test_mode(), "Precondition: test mode, so the app in process never reaches the production data directory"
    from backend.app.main import app as main_app  # noqa: PLC0415 — the server's own app, imported by the fixture that needs it

    return main_app


@contextmanager
def client_address_state_kept() -> Iterator[None]:
    module = client_address_module
    noted = {peer_class: set(names) for peer_class, names in module._untrusted_forwarding.items()}
    warned = list(module._warned)
    try:
        yield
    finally:
        for peer_class, names in module._untrusted_forwarding.items():
            names.clear()
            names.update(noted.get(peer_class, set()))
        module._warned[:] = warned


@dataclass
class Instance:
    """The app of a test, its data directory, its private database, and the monkeypatch of its environment."""

    app: FastAPI
    root: Path
    engine: Any
    monkeypatch: pytest.MonkeyPatch

    def switches(self, *, awaiting: bool = False, blocked: bool = False) -> None:
        for variable in (AWAIT_VARIABLE, BLOCKED_VARIABLE, DELETION_DATE_VARIABLE):
            self.monkeypatch.delenv(variable, raising=False)
        if awaiting:
            self.monkeypatch.setenv(AWAIT_VARIABLE, "1")
        if blocked:
            self.monkeypatch.setenv(BLOCKED_VARIABLE, "1")


@pytest_asyncio.fixture
async def instance(app: FastAPI, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AsyncIterator[Instance]:
    """Neither switch, no variable of the panel; test mode on ``tmp_path/data``; every request's session on a private
    SQLite file (schema, default settings, ``alembic_version`` at the head); a fresh activity record and attempts
    limiter. The engine is disposed on the way out."""
    for name in (*PANEL_ENVIRONMENT, AWAIT_VARIABLE, BLOCKED_VARIABLE, DELETION_DATE_VARIABLE):
        monkeypatch.delenv(name, raising=False)
    root = (tmp_path / "data").resolve()
    root.mkdir()
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(root))
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "selfhosted")
    assert get_data_dir() == root, f"Precondition: the data directory is this test's own, not {get_data_dir()}"
    monkeypatch.setattr(activity_module, "ACTIVITY", activity_module.Activity())
    monkeypatch.setattr(access_module, "PANEL_ATTEMPTS", SlidingWindowLimiter(20, 600, clock=lambda: 1_000_000.0))
    monkeypatch.setattr(client_address_module, "_configured_header", lambda: None)
    head = alembic_head_revision()
    assert head is not None, "Precondition: the head revision of the migration scripts can be read"
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'instance.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
            await connection.exec_driver_sql("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
            await connection.exec_driver_sql("INSERT INTO alembic_version (version_num) VALUES (?)", (head,))
        async with AsyncSession(engine) as session:
            await initialize_global_settings(session)

        async def private_session() -> AsyncIterator[AsyncSession]:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                yield session

        monkeypatch.setitem(app.dependency_overrides, get_session_generator, private_session)
        with client_address_state_kept():
            yield Instance(app=app, root=root, engine=engine, monkeypatch=monkeypatch)
    finally:
        await engine.dispose()


async def send(instance: Instance, method: str, path: str, **kwargs: Any) -> httpx.Response:
    transport = httpx.ASGITransport(app=instance.app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL, timeout=TIMEOUT) as client:
        return await client.request(method, path, **kwargs)


def code(response: httpx.Response) -> tuple[int, str | None]:
    try:
        body = response.json()
    except ValueError:
        return response.status_code, None
    detail = body.get("detail") if isinstance(body, dict) else None
    return response.status_code, detail.get("code") if isinstance(detail, dict) else None


def shown(response: httpx.Response) -> str:
    return f"{response.status_code} {response.text[:600]}"


async def signed_in(instance: Instance) -> dict[str, str]:
    """An active account of the private database, and the Cookie header of a session this process mints for it."""
    username = f"h62mode_{uuid4().hex[:12]}"
    async with AsyncSession(instance.engine, expire_on_commit=False) as session:
        account = User(username=username, email=f"{username}@example.com", hashed_password="not-a-password-hash")
        session.add(account)
        await session.commit()
        with capture_logs():
            token = create_jwt_token(account.id, 1, account.session_version)
    return {"Cookie": f"{SESSION_COOKIE_NAME}={token}"}


def write_state(root: Path, status: str, *, waiting: str | None = None) -> None:
    """A restore of ``STAGE_ID`` in phase ``status``, as a confirmation and the starts after it leave it on disk."""
    finished = datetime(2026, 10, 23, 3, 30, tzinfo=UTC)
    fields: dict[str, Any] = {}
    if status in ("applying", "applied", "rolling_back"):
        fields["swap"] = [apply_module.SwapEntry(name=name, live=True, staged=True) for name in SWAPPED_FOLDERS]
        fields["boot"] = apply_module.Boot(pid=999_999, started=1_760_000_000.0)
    if status == "committed":
        fields.update(applied_at=finished - timedelta(minutes=5), finished_at=finished, session_version=int(finished.timestamp() * 1000))
    if waiting is not None:
        fields["waiting"] = waiting
    state = apply_module.RestoreState(
        status=status,
        stage_id=STAGE_ID,
        data_dir=str(root.resolve()),
        confirmed_at=datetime(2026, 10, 23, 2, 0, tzinfo=UTC),
        confirmed_by=CONFIRMED_BY,
        backup_created_at=BACKUP_CREATED_AT,
        backup_app_version="v1.3.0",
        action="same",
        **fields,
    )
    path = restore_state_path(root)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(state.model_dump_json(), encoding="utf-8")
    path.chmod(0o600)


def write_unreadable_state(root: Path, reason: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """The restore's state on disk, in a form B's reader refuses with ``reason`` (D7): a folder in its place
    (``not_a_file``), bytes that are no state this LibreFolio reads (``invalid``), or a file the system refuses to read
    (``io``: the reader's ``read_regular_file`` raising ``EACCES``, through ``monkeypatch``, so the case does not depend
    on the user the tests run as). Barrier: ``apply.read_restore`` raises with that very reason."""
    path = restore_state_path(root)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if reason == "not_a_file":
        path.mkdir(mode=0o700)
    else:
        path.write_text('{"status": "d7: no state this LibreFolio reads"}', encoding="utf-8")
        path.chmod(0o600)
    if reason == "io":

        def refused(*_args: Any, **_kwargs: Any) -> NoReturn:
            raise PermissionError(errno.EACCES, os.strerror(errno.EACCES))

        monkeypatch.setattr(apply_module, "read_regular_file", refused)
    try:
        apply_module.read_restore(root)
    except apply_module.RestoreStateUnreadableError as exc:
        assert exc.reason == reason, f"Barrier: the reader refuses the state with {reason!r}, not {exc.reason!r}"
    else:
        pytest.fail(f"Barrier: the state written for {reason!r} must be unreadable to apply.read_restore")


def _endpoint_name(endpoint: Any) -> str:
    return f"{endpoint.__module__}.{endpoint.__qualname__}"


def _api_routes(app: FastAPI) -> list[Any]:
    """The effective API routes under /api/v1."""
    return [context for context in iter_route_contexts(app.routes) if isinstance(context.original_route, APIRoute) and (context.path or "").startswith(API_V1_PREFIX + "/")]


def _concrete(path: str) -> str:
    return _PATH_PARAMETER.sub("1", path)


# =============================================================================
# AM-001..003: THE DEPENDENCY, ITS CODE AND ITS ALLOWED SET
# =============================================================================


def test_the_mode_has_its_dependency_its_code_and_its_allowed_set_pinned_by_name_and_route(app):
    """AM-001 (§6): ``refuse_when_awaiting_restore`` exists, ``INSTANCE_AWAITING_RESTORE_CODE`` is
    ``"instance_awaiting_restore"``, and ``ALLOWED_WHEN_AWAITING_RESTORE`` holds exactly the pinned endpoints, each
    serving its one route."""
    print_section("H-62 §6: the allowed set of the mode")
    dependency = h62(BLOCK_MODULE, "refuse_when_awaiting_restore")
    code_value = h62(BLOCK_MODULE, "INSTANCE_AWAITING_RESTORE_CODE")
    allowed = h62(BLOCK_MODULE, "ALLOWED_WHEN_AWAITING_RESTORE")

    assert callable(dependency) and code_value == AWAITING_CODE, f"the dependency, and its code {AWAITING_CODE!r}: {code_value!r}"
    names = sorted(_endpoint_name(endpoint) for endpoint in allowed)
    assert names == sorted(ALLOWED_WHEN_AWAITING_RESTORE_ROUTES), f"ALLOWED_WHEN_AWAITING_RESTORE changed:\n  expected {sorted(ALLOWED_WHEN_AWAITING_RESTORE_ROUTES)}\n  got      {names}"
    routes: dict[str, set[tuple[str, str]]] = {}
    for context in _api_routes(app):
        if context.endpoint in allowed:
            routes.setdefault(_endpoint_name(context.endpoint), set()).update((method, context.path) for method in context.methods or ())
    assert routes == {name: {route} for name, route in ALLOWED_WHEN_AWAITING_RESTORE_ROUTES.items()}, f"each allowed endpoint serves exactly its one route: {routes}"
    print_success(f"{len(names)} endpoints allowed in the mode, each on its route")


def test_every_route_under_api_v1_resolves_the_block_then_the_mode_first(app):
    """AM-002 (§6, R4): every API route under /api/v1 (but the documentation) has ``refuse_when_blocked`` as its first
    dependency and ``refuse_when_awaiting_restore`` right after it: no user route answers before both switches were
    read."""
    dependency = h62(BLOCK_MODULE, "refuse_when_awaiting_restore")
    contexts = [context for context in _api_routes(app) if context.path not in DOCUMENTATION_PATHS]
    assert len(contexts) > 50, f"Barrier: the walk reaches the API routes: {len(contexts)}"

    wrong = {}
    for context in contexts:
        calls = [item.call for item in context.dependant.dependencies[:2]]
        if calls != [refuse_when_blocked, dependency]:
            wrong[f"{sorted(context.methods or ())} {context.path}"] = [getattr(call, "__name__", call) for call in calls]
    assert wrong == {}, f"these routes do not resolve refuse_when_blocked then refuse_when_awaiting_restore first: {dict(list(wrong.items())[:10])} ({len(wrong)} in all)"


# =============================================================================
# AM-010..013: IN THE MODE, 423 FOR ANYONE BUT THE ALLOWED SET
# =============================================================================


@pytest.mark.asyncio
async def test_in_the_mode_every_route_outside_the_set_answers_423_to_anyone(instance):
    """AM-010 (§6, Q5): ``LIBREFOLIO_AWAIT_RESTORE=1``: each method of each API route outside the allowed set, sent
    without a session and without a body, answers 423 ``instance_awaiting_restore``. Barrier: the mode's dependency
    guards every route (AM-002), checked first, so that before H-62 nothing is sent."""
    dependency = h62(BLOCK_MODULE, "refuse_when_awaiting_restore")
    allowed = h62(BLOCK_MODULE, "ALLOWED_WHEN_AWAITING_RESTORE")
    contexts = [context for context in _api_routes(instance.app) if context.path not in DOCUMENTATION_PATHS and context.endpoint not in allowed]
    unguarded = [context.path for context in contexts if dependency not in [item.call for item in context.dependant.dependencies]]
    assert unguarded == [], f"Barrier: the mode's dependency guards every route: {unguarded[:10]}"
    instance.switches(awaiting=True)

    answers = {}
    for context in contexts:
        for method in sorted((context.methods or set()) - {"HEAD", "OPTIONS"}):
            response = await send(instance, method, _concrete(context.path))
            answers[f"{method} {context.path}"] = code(response)

    wrong = {name: result for name, result in answers.items() if result != (423, AWAITING_CODE)}
    assert len(answers) > 50, f"Barrier: many routes were asked: {len(answers)}"
    assert wrong == {}, f"in the mode these routes did not answer 423 {AWAITING_CODE} to an anonymous caller: {dict(list(wrong.items())[:15])} ({len(wrong)} of {len(answers)})"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        pytest.param("POST", "/auth/register", {"username": "h62mode_reg", "email": "h62mode_reg@example.com", "password": PASSWORD}, id="register"),
        pytest.param("POST", "/auth/setup", {"token": "h62-not-a-setup-token", "password": PASSWORD}, id="setup"),
        pytest.param("POST", "/auth/login", {"username": "h62mode_reg", "password": PASSWORD}, id="login"),
        pytest.param("GET", "/auth/me", None, id="me"),
    ],
)
@pytest.mark.parametrize("with_session", [False, True], ids=["anonymous", "signed-in"])
async def test_registration_setup_login_and_me_answer_423_in_the_mode(instance, method, path, body, with_session):
    """AM-011 (§6: «compresi registrazione, primo account e /auth/setup»): in the mode, registration, the first
    administrator's setup, the login and ``/auth/me`` answer 423 ``instance_awaiting_restore``, anonymous or signed in;
    no account is created. Barrier: outside the mode the same signed-in session reads ``/auth/me``."""
    session = await signed_in(instance)
    me = await send(instance, "GET", f"{API_V1_PREFIX}/auth/me", headers=session)
    assert me.status_code == 200, f"Barrier: outside the mode the session reads /auth/me: {shown(me)}"
    instance.switches(awaiting=True)

    response = await send(instance, method, f"{API_V1_PREFIX}{path}", json=body, headers=session if with_session else {})

    assert code(response) == (423, AWAITING_CODE), f"{method} {path} in the mode → 423 {AWAITING_CODE}: {shown(response)}"
    async with AsyncSession(instance.engine) as db:
        created = (await db.execute(select(func.count()).select_from(User).where(User.username == "h62mode_reg"))).scalar_one()
    assert created == 0, "no account is created in the mode"


@pytest.mark.asyncio
async def test_in_the_mode_the_allowed_routes_never_answer_the_mode(instance):
    """AM-012 (§6): in the mode the allowed routes answer on their own terms, never 423: health 200; readiness 200;
    the version 200; the public configuration 200; the lane probe, the wake-up, the panel's status, its backup jobs and
    its restore routes their own 404 while off. Barrier: the same request to a user route is 423 in the mode."""
    instance.switches(awaiting=True)
    barrier = await send(instance, "GET", f"{API_V1_PREFIX}/brokers")
    answers = {}
    for name, (method, path) in ALLOWED_WHEN_AWAITING_RESTORE_ROUTES.items():
        answers[name] = code(await send(instance, method, _concrete(path)))

    assert code(barrier) == (423, AWAITING_CODE), f"Barrier: a user route is 423 in the mode: {shown(barrier)}"
    wrong = {name: result for name, result in answers.items() if result[0] == 423 or result[1] == AWAITING_CODE}
    assert wrong == {}, f"an allowed route answered the mode's refusal: {wrong}"
    public = {name: answers[name][0] for name in ("backend.app.api.v1.system.health.health_check", "backend.app.api.v1.system.ready.get_readiness", "backend.app.api.v1.system.info.get_system_info", "backend.app.api.v1.system.instance.get_instance_config")}
    assert public == dict.fromkeys(public, 200), f"health, readiness, version and configuration answer 200 in the mode: {public}"


@pytest.mark.asyncio
@pytest.mark.parametrize("awaiting", [False, True], ids=["normal", "awaiting-restore"])
async def test_readiness_and_the_public_configuration_say_the_mode(instance, awaiting):
    """AM-013 (§6): ``GET /system/ready`` → 200 ``ready`` with ``mode``; ``GET /system/instance`` → ``mode``:
    ``awaiting_restore`` in the mode, ``normal`` outside it."""
    instance.switches(awaiting=awaiting)
    ready = await send(instance, "GET", f"{API_V1_PREFIX}/system/ready")
    config = await send(instance, "GET", f"{API_V1_PREFIX}/system/instance")

    expected = "awaiting_restore" if awaiting else "normal"
    assert ready.status_code == 200 and ready.json().get("status") == "ready", f"readiness answers 200 ready: {shown(ready)}"
    assert (ready.json().get("mode"), config.status_code, config.json().get("mode")) == (expected, 200, expected), f"mode {expected!r} in readiness and in the public configuration: {shown(ready)} / {shown(config)}"


def test_the_mode_is_a_literal_of_two_values_in_the_three_schemas():
    """AM-014 (§6): ``ReadinessResponse.mode``, ``InstanceConfigResponse.mode`` and ``PanelStatusResponse.mode`` take
    exactly ``normal`` and ``awaiting_restore``."""
    from backend.app.schemas.hosting_panel import PanelStatusResponse  # noqa: PLC0415
    from backend.app.schemas.system import InstanceConfigResponse, ReadinessResponse  # noqa: PLC0415

    found = {}
    for model in (ReadinessResponse, InstanceConfigResponse, PanelStatusResponse):
        schema = model.model_json_schema()
        prop = schema.get("properties", {}).get("mode", {})
        found[model.__name__] = sorted(prop.get("enum", [])) if prop else None
    assert found == dict.fromkeys(found, sorted(MODES)), f"mode is normal|awaiting_restore in each schema: {found}"


# =============================================================================
# AM-020: THE SCHEDULED WAKE-UP IN THE MODE
# =============================================================================


def _trap(name: str, reached: list[str]) -> Any:
    def trapped(*_args: object, **_kwargs: object) -> NoReturn:
        reached.append(name)
        raise AssertionError(f"scheduler.{name} was reached in the mode")

    return trapped


async def _settled_at_once() -> None:
    """``settle_clock`` without its wait."""


@pytest.mark.asyncio
async def test_the_wake_up_in_the_mode_answers_awaiting_restore_and_runs_nothing(instance):
    """AM-020 (§6: «wake-sync, che non fa nulla e risponde awaiting_restore»): in the mode, with its token and the real
    ``run_due_jobs``, ``POST /system/wake-sync`` → 200, ``status: awaiting_restore``, no job, and nothing past the
    scheduler's switches reached."""
    instance.monkeypatch.setattr(wake_module, "run_due_jobs", scheduler.run_due_jobs)
    instance.monkeypatch.delenv("LIBREFOLIO_NO_SCHEDULER", raising=False)
    instance.monkeypatch.setattr(scheduler, "settle_clock", _settled_at_once, raising=False)
    instance.monkeypatch.setattr(idle_monitor, "request_idle_check", lambda *_args, **_kwargs: None, raising=False)
    reached: list[str] = []
    for name in PAST_THE_SWITCHES:
        instance.monkeypatch.setattr(scheduler, name, _trap(name, reached), raising=False)
    instance.monkeypatch.setattr(scheduler, "scheduler_run_lock", _trap("scheduler_run_lock", reached), raising=False)
    token = secrets.token_hex(32)
    instance.monkeypatch.setenv(WAKE_TOKEN_VARIABLE, token)
    instance.switches(awaiting=True)

    response = await send(instance, "POST", f"{API_V1_PREFIX}/system/wake-sync", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200, f"the wake-up answers 200 in the mode: {shown(response)}"
    body = json.loads(response.content)
    assert (body.get("status"), body.get("jobs")) == ("awaiting_restore", []), f"status awaiting_restore, no job: {body}"
    assert reached == [], f"nothing past the switches in the mode: {reached}"


# =============================================================================
# AM-030..032: BOTH SWITCHES, AND R4
# =============================================================================


@pytest.mark.asyncio
async def test_with_both_switches_a_signed_in_user_meets_423(instance):
    """AM-030 (§6, R4: «con tutte e due le variabili accese tutto risponde 423»): blocked and in the mode, a signed-in
    user's request to a user route → 423, with either code. Barrier: the session reads it outside both."""
    session = await signed_in(instance)
    before = await send(instance, "GET", f"{API_V1_PREFIX}/brokers", headers=session)
    assert before.status_code == 200, f"Barrier: the session reads /brokers with neither switch: {shown(before)}"
    instance.switches(awaiting=True, blocked=True)

    response = await send(instance, "GET", f"{API_V1_PREFIX}/brokers", headers=session)

    assert response.status_code == 423 and code(response)[1] in (BLOCKED_CODE, AWAITING_CODE), f"both on → 423: {shown(response)}"


@pytest.mark.asyncio
async def test_r4_after_a_committed_restore_the_block_answers_the_first_request_guard(instance):
    """AM-031, guard of R4 (§6): a committed restore on disk, ``LIBREFOLIO_BLOCKED=1`` and no
    ``LIBREFOLIO_AWAIT_RESTORE``: the first request of a signed-in user to a user route → 423 ``instance_blocked``
    (the switch read at each call)."""
    session = await signed_in(instance)
    write_state(instance.root, "committed")
    instance.switches(blocked=True)

    response = await send(instance, "GET", f"{API_V1_PREFIX}/brokers", headers=session)

    assert code(response) == (423, BLOCKED_CODE), f"R4: blocked after the restore → 423 instance_blocked at the first request: {shown(response)}"


@pytest.mark.asyncio
async def test_r4_from_the_mode_to_the_block_no_request_is_served_in_between(instance):
    """AM-032, R4 (§6, steps 1-3): the same process, a signed-in user: in the mode (a committed restore recorded) → 423
    ``instance_awaiting_restore``; then the coordinator's one update, the mode off and the block on → the very next
    request 423 ``instance_blocked``. No request answers normally in between."""
    session = await signed_in(instance)
    write_state(instance.root, "committed")
    instance.switches(awaiting=True)
    in_the_mode = await send(instance, "GET", f"{API_V1_PREFIX}/brokers", headers=session)
    instance.switches(blocked=True)
    blocked = await send(instance, "GET", f"{API_V1_PREFIX}/brokers", headers=session)

    assert code(in_the_mode) == (423, AWAITING_CODE), f"step 2: committed, still in the mode → 423 {AWAITING_CODE}: {shown(in_the_mode)}"
    assert code(blocked) == (423, BLOCKED_CODE), f"step 3: the block answers the first request: {shown(blocked)}"


# =============================================================================
# AM-040..044: GET /panel/status, ITS MODE AND ITS RESTORE
# =============================================================================


async def panel_status(instance: Instance) -> httpx.Response:
    token = secrets.token_hex(32)
    instance.monkeypatch.setenv(STATUS_TOKEN_VARIABLE, token)
    return await send(instance, "GET", f"{API_V1_PREFIX}/panel/status", headers={"Authorization": f"Bearer {token}"})


def _instant(value: Any) -> datetime | None:
    try:
        moment = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return moment if moment.utcoffset() == timedelta(0) else None


@pytest.mark.asyncio
@pytest.mark.parametrize("awaiting", [False, True], ids=["normal", "awaiting-restore"])
async def test_the_panel_status_says_the_mode_and_no_restore(instance, awaiting):
    """AM-040 (§6): ``GET /panel/status`` holds exactly ``admin_setup``, ``setup_expires_at``, ``mode`` and
    ``restore``; without a restore recorded ``restore`` is null; ``mode`` follows the switch."""
    instance.switches(awaiting=awaiting)
    response = await panel_status(instance)

    assert response.status_code == 200, f"the status answers 200: {shown(response)}"
    body = response.json()
    assert set(body) == PANEL_STATUS_KEYS, f"exactly {sorted(PANEL_STATUS_KEYS)}: {sorted(body)}"
    assert (body["mode"], body["restore"]) == ("awaiting_restore" if awaiting else "normal", None), f"the mode, no restore: {body}"


@pytest.mark.asyncio
@pytest.mark.parametrize(("phase", "state"), [("pending", "pending"), ("applying", "in_progress"), ("committed", "committed")])
async def test_the_panel_status_gives_the_restore_without_who_confirmed_it(instance, phase, state):
    """AM-041 (§6): a restore recorded → ``restore`` is exactly ``{state, reason, waiting, backup_created_at,
    stage_id}``, ``state`` as ``RestoreStatus.state``; the name of whoever confirmed it is nowhere in the answer."""
    write_state(instance.root, phase)
    instance.switches(awaiting=True)
    response = await panel_status(instance)

    assert response.status_code == 200, f"the status answers 200: {shown(response)}"
    restore = response.json().get("restore")
    assert isinstance(restore, dict) and set(restore) == PANEL_RESTORE_KEYS, f"restore is exactly {sorted(PANEL_RESTORE_KEYS)}: {restore}"
    assert (restore["state"], restore["stage_id"], restore["reason"], _instant(restore["backup_created_at"])) == (state, STAGE_ID, None, BACKUP_CREATED_AT), f"{phase} → {state}: {restore}"
    assert CONFIRMED_BY not in response.text, f"the confirmer's name is in the panel's status: {response.text}"


@pytest.mark.asyncio
async def test_the_panel_status_says_why_a_restore_waits(instance):
    """AM-042 (§6: «il blocco vince»): a pending restore a start left waiting for the unblock → ``waiting:
    instance_blocked``."""
    write_state(instance.root, "pending", waiting="instance_blocked")
    response = await panel_status(instance)

    assert response.status_code == 200 and (response.json().get("restore") or {}).get("waiting") == "instance_blocked", f"waiting instance_blocked: {shown(response)}"


@pytest.mark.asyncio
@pytest.mark.parametrize("awaiting", [False, True], ids=["normal", "awaiting-restore"])
@pytest.mark.parametrize("reason", UNREADABLE_REASONS)
async def test_a_restore_state_that_cannot_be_read_is_200_with_restore_unreadable_and_its_reason(instance, reason, awaiting):
    """AM-043 (D7, contract L3 §10 option A; replaces Q7's 500): a restore state on disk that B's reader refuses with
    ``reason`` (``io``, ``not_a_file``, ``invalid``) → ``GET /panel/status`` answers 200 with exactly its four keys,
    ``mode`` as the switch says, and ``restore`` exactly ``{state: unreadable, reason, waiting: null,
    backup_created_at: null, stage_id: null}``; never ``restore: null`` (a restore may wait behind it), never the 500."""
    write_unreadable_state(instance.root, reason, instance.monkeypatch)
    instance.switches(awaiting=awaiting)
    response = await panel_status(instance)

    assert response.status_code == 200, f"D7: an unreadable state ({reason}) → 200, not Q7's 500: {shown(response)}"
    body = response.json()
    assert set(body) == PANEL_STATUS_KEYS, f"exactly {sorted(PANEL_STATUS_KEYS)}: {sorted(body)}"
    assert (body["mode"], body["restore"]) == ("awaiting_restore" if awaiting else "normal", unreadable_restore(reason)), f"D7: restore unreadable with its reason {reason!r}, the mode as the switch says: {body}"


@pytest.mark.parametrize("reason", UNREADABLE_REASONS)
def test_the_panel_restore_summary_admits_unreadable_with_each_reason_of_its_reader(reason):
    """AM-044 (D7): ``PanelRestoreSummary`` validates ``state: unreadable`` with each reason of an unreadable state, and
    keeps its five fields (``extra="forbid"``)."""
    summary_class = h62("backend.app.schemas.hosting_panel", "PanelRestoreSummary")
    summary = summary_class.model_validate({"state": UNREADABLE_STATE, "reason": reason})

    assert set(summary_class.model_fields) == PANEL_RESTORE_KEYS, f"PanelRestoreSummary keeps exactly {sorted(PANEL_RESTORE_KEYS)}: {sorted(summary_class.model_fields)}"
    assert summary.model_dump(mode="json") == unreadable_restore(reason), f"D7: unreadable with {reason!r}: {summary!r}"


def test_guard_the_panel_restore_summary_keeps_the_rollback_reasons_and_refuses_an_unknown_state():
    """Guard of AM-044: the reasons of a rolled-back restore stay valid, and a state nobody defined is refused."""
    from pydantic import ValidationError  # noqa: PLC0415

    summary_class = h62("backend.app.schemas.hosting_panel", "PanelRestoreSummary")
    kept = [summary_class.model_validate({"state": "rolled_back", "reason": reason}).reason for reason in ROLLBACK_REASONS]
    assert kept == list(ROLLBACK_REASONS), f"the rollback reasons stay: {kept}"
    with pytest.raises(ValidationError):
        summary_class.model_validate({"state": "d7_no_such_state"})


# =============================================================================
# Needs B (Q3) — what workstream B adds first; kept apart from H's reds
# =============================================================================


class TestNeedsB:
    """``# Needs B (Q3)``: ``POST /backup/panel/jobs`` in the mode → 409 ``backup_awaiting_restore`` (a line of B's in
    ``api/v1/backup/panel.py``, with H's ``awaiting_restore()``)."""

    # Needs B (Q3)
    @pytest.mark.asyncio
    async def test_q3_a_panel_backup_in_the_mode_is_409_and_starts_nothing(self, instance):
        """Q3 (§6): in the mode, with the backup token, ``POST /backup/panel/jobs`` → 409 ``backup_awaiting_restore``;
        the backup service is never reached."""
        reached: list[str] = []

        def no_backup(*_args: Any, **_kwargs: Any) -> NoReturn:
            reached.append("start_backup")
            raise AssertionError("a backup started in the mode")

        instance.monkeypatch.setattr(backup_jobs, "start_backup", no_backup)
        token = secrets.token_hex(32)
        instance.monkeypatch.setenv(BACKUP_TOKEN_VARIABLE, token)
        instance.switches(awaiting=True)

        response = await send(instance, "POST", f"{API_V1_PREFIX}/backup/panel/jobs", headers={"Authorization": f"Bearer {token}"})

        assert code(response) == (409, "backup_awaiting_restore"), f"Q3: a panel backup in the mode → 409 backup_awaiting_restore: {shown(response)}"
        assert reached == [], "Q3: no backup starts in the mode"
