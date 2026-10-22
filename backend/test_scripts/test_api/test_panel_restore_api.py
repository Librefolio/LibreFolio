"""
The hosting panel's restore route (LibreFolio 1.3, workstream H, lot H-62): contract L3 §5, with §6 for the mode it
works in, and the coordinator's answers Q5, Q7 and Q8 (``h62_contract.md``).

Under test, all of it written by H-62 and missing today:

- ``backend.app.api.v1.backup.panel_restore``: ``panel_restore_router``, registered under ``/api/v1/backup`` with the tag
  «Hosting panel», route class ``NoInputEchoRoute``, seven endpoints: ``upload_panel_restore_archive`` (``PUT
  …/panel/restore/upload``, raw body, 201 ``{upload_id, size, kind}``), ``start_panel_restore_check`` (``POST …/stage``,
  202 ``PanelRestoreStage``), ``get_panel_restore_check`` (``GET …/stage/{stage_id}``), ``confirm_panel_restore_check``
  (``POST …/stage/{stage_id}/confirm``, 202 ``PanelRestoreStatus``), ``restart_panel_restore`` (``POST …/restart``, 202
  ``PanelRestoreStatus``, no outcome ticket), ``get_panel_restore_status`` (``GET …/status``) and
  ``cancel_panel_pending_restore`` (``DELETE …/pending``, 204 / 404 ``restore_not_pending``).
- ``PanelScope.BACKUP_RESTORE`` (``"backup:restore"``), a ticket-only scope: no token variable. Without
  ``LIBREFOLIO_PANEL_PUBLIC_KEYS`` → 404 ``Not Found``; any L1 token (backup, wake, status) → 401
  ``backup_restore_unauthorized``, counted; a ticket of scope ``backup`` → 401 ``panel_ticket_wrong_scope``; replayed →
  ``panel_ticket_replayed``; keys or registry unusable → 503 ``backup_restore_unavailable`` (Q8).
- The order of the refusals, on each of the seven: the credential first (404, 401, 429, 503), THEN a blocked instance →
  423 ``instance_blocked``, THEN outside the mode → 409 ``restore_mode_required``. A caller without a valid ticket never
  learns the mode nor the block: every credential refusal is the same in the four states (normal, awaiting restore,
  blocked, both).
- The upload (same writer, limit and space as the admin's): an ``.lfbk`` → 201 ``kind: envelope``; a zip or the
  coordinator's ``.tar`` → 400 ``restore_envelope_required`` and nothing left on disk; over
  ``LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`` → 413 ``backup_too_large`` with ``limit_mb``; R3: a ticket that expires while the
  body is still arriving → 201 all the same.
- The check: a wrong password → 400 ``wrong_password``, the upload kept, the right one then 202; the report seen by the
  panel is ``PanelRestoreStageReport`` (``extra="forbid"``, exactly 20 fields): a real check of a backup with two
  administrators and differences in the control totals answers ``administrators_count == 2`` and no username, no email,
  no amount, currency or broker of the differences.
- Confirm: 202 ``pending``, ``confirmed_via == "panel"``, no ``confirmed_by``; again → 202, the same status; another
  stage while one is pending → 409 ``restore_already_pending``; a log line of the confirmation, beside the access line,
  carries the ticket's ``kid``. Restart: pending → 202 and exactly one ``restart.request_restart`` after the answer; in
  progress or committed → 202 with that state, no second call; nothing recorded → 409 ``restore_not_pending``. Status and
  the cancel. No echo: a 422 of ``POST …/stage`` never repeats the password, and no log record of the requests holds it.

``# Needs B (Q1..Q4)``, kept apart at the end of the file (class ``TestNeedsB``): what workstream B must add first —
Q1, a stage started by the admin route or the CLI (``restore_jobs.start_check`` without the panel's origin) is not the
panel's: 404 ``restore_stage_not_found`` to its poll and its confirmation; Q2, ``confirmed_via`` is stored in the state
(``RestoreState.confirmed_via``), so a restore confirmed by an administrator reads ``admin`` through the panel, without
the username; Q4, the same ``upload_id`` while its check runs → 202 with the same ``stage_id``, another → 409
``restore_busy``. (Q3 is a route of the mode, in ``test_await_restore_mode_api.py``.)

How. The mode is read from the process environment, so nothing here runs on the lane's backend: the app of
``backend/app/main.py`` runs in this process through ``httpx.ASGITransport`` (its lifespan does not run), every
variable is set through ``monkeypatch``, from a public peer (``203.0.113.62``). The data directory is ``tmp_path/data``
(test mode, ``LIBREFOLIO_TEST_DATA_DIR``), where the restore and the registry of used tickets write; the database
session of every request is a stand-in that fails the test if anything reaches it; the checks run in the fake threads of
``test_backup_restore.py`` (at once, or held); ``restart.request_restart`` records instead of signalling; the panel's
attempts limiter is one of the test's own, on a clock that never moves. The keys are Ed25519 keys from fixed seeds,
tickets signed with PyJWT. Real archives: the head database of ``test_backup_staging.py`` (``databases``), with a ledger
and two administrators whose names are canaries, its control totals rewritten in the manifest, sealed in an ``.lfbk``
with ``envelope.encrypt_file``. The only wait on the clock is R3's, which is the subject: the body's last piece is
sent once the wall clock is past the ticket's ``exp``, polled with a deadline.

Every name of H-62 (and of B) is imported by the test that needs it, so the file collects and each test reports its
own red. Red today: the module, the routes, the scope and the schemas do not exist (each route answers the plain 404
of a path that does not exist, which the presence barrier of each case turns into a red naming the route).

Isolation: pure. No server, no lane database, no network, no file outside ``tmp_path``.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import importlib
import io
import json
import logging
import secrets
import tarfile
import time
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import FastAPI
from fastapi.routing import APIRoute, iter_route_contexts
from structlog.contextvars import merge_contextvars
from structlog.testing import capture_logs

from backend.app.config import API_V1_PREFIX, get_data_dir, is_test_mode
from backend.app.db.session import get_session_generator
from backend.app.services.platform import client_address as client_address_module
from backend.app.services.platform.hosting_panel import access as access_module
from backend.app.services.platform.hosting_panel import ticket_registry
from backend.app.services.platform.instance_backup import apply as apply_module
from backend.app.services.platform.instance_backup import restart as restart_module
from backend.app.services.platform.instance_backup import restore_jobs
from backend.app.services.platform.instance_backup.envelope import encrypt_file
from backend.app.services.platform.instance_backup.paths import SWAPPED_FOLDERS, restore_dir, restore_state_path, upload_path, uploads_dir
from backend.app.services.platform.instance_backup.staging import read_report
from backend.app.services.platform.sleep_wake import activity as activity_module
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.app.utils.runtime.version import get_git_version
from backend.test_scripts.test_api import test_backup_restore as api
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utils import print_section, print_success

# The real databases of lot B2a (alembic upgrade, once per module), re-exported for the archives of this file.
databases = cases.databases

# =============================================================================
# THE CONTRACT, SPELLED OUT
# =============================================================================

ROUTES_MODULE = "backend.app.api.v1.backup.panel_restore"
#: SEC-review point 6: the module-level flag of ``panel_restore`` that remembers a restart already asked in this process.
RESTART_FLAG = "_restart_requested"
SCHEMAS_MODULE = "backend.app.schemas.hosting_panel"
ACCESS_MODULE = "backend.app.services.platform.hosting_panel.access"

BASE = f"{API_V1_PREFIX}/backup/panel/restore"
UPLOAD = f"{BASE}/upload"
STAGE = f"{BASE}/stage"
STAGE_ITEM = f"{STAGE}/{{stage_id}}"
CONFIRM = f"{STAGE}/{{stage_id}}/confirm"
RESTART = f"{BASE}/restart"
STATUS = f"{BASE}/status"
PENDING = f"{BASE}/pending"

#: The scope of the restore, and the one of the backup jobs (a ticket of it must not open the restore).
RESTORE_SCOPE = "backup:restore"
BACKUP_SCOPE = "backup"

#: The variables of the hosting panel (``config/hosting_panel.py``, ``config/backup.py``, ``config/sleep_wake.py``).
BACKUP_TOKEN_VARIABLE = "LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN"
WAKE_TOKEN_VARIABLE = "LIBREFOLIO_WAKE_TOKEN"
STATUS_TOKEN_VARIABLE = "LIBREFOLIO_PANEL_STATUS_TOKEN"
TOKEN_VARIABLES = (BACKUP_TOKEN_VARIABLE, WAKE_TOKEN_VARIABLE, STATUS_TOKEN_VARIABLE)
KEYS_VARIABLE = "LIBREFOLIO_PANEL_PUBLIC_KEYS"
SKEW_VARIABLE = "LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
FILE_SUFFIX = "_FILE"
PANEL_ENVIRONMENT = (*TOKEN_VARIABLES, *(name + FILE_SUFFIX for name in TOKEN_VARIABLES), KEYS_VARIABLE, KEYS_VARIABLE + FILE_SUFFIX, SKEW_VARIABLE, PUBLIC_URL_VARIABLE)
#: The two switches of the instance, read at each call.
AWAIT_VARIABLE = "LIBREFOLIO_AWAIT_RESTORE"
BLOCKED_VARIABLE = "LIBREFOLIO_BLOCKED"
DELETION_DATE_VARIABLE = "LIBREFOLIO_DELETION_DATE"
LIMIT_VARIABLE = "LIBREFOLIO_BACKUP_MAX_UPLOAD_MB"
MAX_RESTORE_VARIABLE = "LIBREFOLIO_BACKUP_MAX_RESTORE_MB"

#: The four states a credential refusal must not tell apart.
STATES: dict[str, dict[str, str]] = {
    "normal": {},
    "awaiting-restore": {AWAIT_VARIABLE: "1"},
    "blocked": {BLOCKED_VARIABLE: "1"},
    "blocked-and-awaiting-restore": {BLOCKED_VARIABLE: "1", AWAIT_VARIABLE: "1"},
}
STATE_CASES = [pytest.param(name, id=name) for name in STATES]

#: The answers of the scope (Q8) and of the gates, whole where the contract gives them whole.
OFF_ANSWER = (404, {"detail": "Not Found"})
UNAUTHORIZED_CODE = "backup_restore_unauthorized"
UNAVAILABLE_CODE = "backup_restore_unavailable"
TOO_MANY_CODE = "panel_too_many_attempts"
WRONG_SCOPE_CODE = "panel_ticket_wrong_scope"
REPLAYED_CODE = "panel_ticket_replayed"
BLOCKED_CODE = "instance_blocked"
MODE_REQUIRED_CODE = "restore_mode_required"
AWAITING_CODE = "instance_awaiting_restore"
#: What no request that passed the credential and the two gates can answer.
GATE_CODES = frozenset({UNAUTHORIZED_CODE, UNAVAILABLE_CODE, TOO_MANY_CODE, BLOCKED_CODE, MODE_REQUIRED_CODE, AWAITING_CODE}) | {
    "panel_ticket_expired",
    "panel_ticket_not_yet_valid",
    "panel_ticket_wrong_audience",
    WRONG_SCOPE_CODE,
    "panel_ticket_invalid",
    REPLAYED_CODE,
    "panel_ticket_unknown_key",
}

#: The panel's views (``schemas/hosting_panel.py``), exactly.
REPORT_FIELDS = frozenset(
    {
        "backup_created_at",
        "backup_app_version",
        "backup_origin",
        "backup_revision",
        "app_version",
        "head_revision",
        "action",
        "migrations",
        "post_migration_fixes",
        "instance_key_included",
        "encrypted",
        "secrets_rekeyed",
        "secrets_unreadable",
        "warnings",
        "blockers",
        "control_totals",
        "control_totals_differences_count",
        "restorable",
        "expires_at",
        "administrators_count",
    }
)
STAGE_FIELDS = frozenset({"stage_id", "status", "phase", "done_bytes", "total_bytes", "created_at", "finished_at", "error_code", "report"})
STATUS_FIELDS = frozenset({"state", "stage_id", "confirmed_at", "confirmed_via", "backup_created_at", "backup_app_version", "action", "finished_at", "reason", "waiting", "upload_limit_mb"})
UPLOAD_FIELDS = frozenset({"upload_id", "size", "kind"})

#: The archives' password, as the coordinator makes one (43 URL-safe characters); test values only.
PASSWORD = "h62PanelRestorePassword-0123456789abcdefABC"
WRONG_PASSWORD = "h62WrongRestorePassword-0123456789abcdefABC"
#: The cheapest key cost a reader accepts: the archives of this file are opened many times.
TEST_LOG2_N = 14
#: The accounts of the backup checked here: two active administrators and a user, their names canaries of this file.
CANARY_ACCOUNTS = (("h62canary_admin_one", 1, 1), ("h62canary_plain_user", 1, 0), ("h62canary_admin_two", 1, 1))
CANARY_ADMINISTRATORS = ["h62canary_admin_one", "h62canary_admin_two"]
CANARY_MARK = "h62canary"
#: The amounts and the currency of the control totals' differences: distinctive, so a search of the raw text proves
#: something.
BUMP = Decimal("7314159.265")
EXTRA_BALANCE = "8271828.18"
EXTRA_CURRENCY = "SEK"
EXTRA_BROKER = 4242

PEER = ("203.0.113.62", 50062)
BASE_URL = "http://h62.test"
PUBLIC_URL = "https://folio-h62.example.com"
AUDIENCE = "https://folio-h62.example.com"
TICKET_TYP = "lf-panel+jwt"
ATTEMPT_LIMIT = 20
ATTEMPT_WINDOW_SECONDS = 600
FROZEN_CLOCK_SECONDS = 1_000_000.0
TIMEOUT = 60.0
#: R3: how far past the ticket's expiry the last piece of the body leaves, and the most the wait may take.
R3_PAST_EXPIRY_SECONDS = 0.5
R3_DEADLINE_SECONDS = 15.0
LOG_CANARY = "H-62 panel restore test: a line written inside the capture reaches it"


# =============================================================================
# H-62'S NAMES, IMPORTED WHEN A TEST NEEDS THEM
# =============================================================================

_MISSING = object()


def h62(module: str, name: str | None = None) -> Any:
    """``module`` (or ``module.name``) of H-62, imported by the test that needs it: the file collects before H-62, and
    each test fails on its own, naming what is missing."""
    try:
        imported = importlib.import_module(module)
    except ModuleNotFoundError as error:
        if error.name is None or not (module == error.name or module.startswith(f"{error.name}.")):
            raise
        imported = None
    if imported is None:
        pytest.fail(f"H-62: {module} does not exist yet")
    if name is None:
        return imported
    value = getattr(imported, name, _MISSING)
    if value is _MISSING:
        pytest.fail(f"H-62: {module} gives no {name}")
    return value


# =============================================================================
# THE KEYS AND THE TICKETS
# =============================================================================


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


@dataclass(frozen=True)
class SigningKey:
    kid: str
    private: Ed25519PrivateKey
    public_text: str

    @property
    def entry(self) -> str:
        return f"{self.kid}:{self.public_text}"


SEED_TEXT = "LibreFolio H-62, test_panel_restore_api.py, a test key never used in production: {label}"


def signing_key(kid: str, label: str) -> SigningKey:
    seed = hashlib.sha256(SEED_TEXT.format(label=label).encode("utf-8")).digest()
    private = Ed25519PrivateKey.from_private_bytes(seed)
    return SigningKey(kid, private, b64url(private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)))


KEY = signing_key("h62-key-a", "key A")


@dataclass(frozen=True)
class Ticket:
    value: str
    kid: str
    jti: str

    @property
    def authorization(self) -> str:
        return f"Bearer {self.value}"


def ticket(scope: str = RESTORE_SCOPE, *, iat: int | None = None, exp: int | None = None) -> Ticket:
    """A ticket of the panel for ``scope``, signed by ``KEY``: valid by default (issued 5 s ago, 240 s of life), a new
    ``jti`` each time."""
    issued = int(time.time()) - 5 if iat is None else iat
    claims = {"aud": AUDIENCE, "scope": scope, "iat": issued, "exp": issued + 240 if exp is None else exp, "jti": secrets.token_urlsafe(16)}
    value = jwt.encode(claims, KEY.private, algorithm="EdDSA", headers={"typ": TICKET_TYP, "kid": KEY.kid})
    return Ticket(value, KEY.kid, claims["jti"])


def a_token() -> str:
    return secrets.token_hex(32)


# =============================================================================
# THE APP IN PROCESS, THE DATA DIRECTORY, THE PANEL OF A TEST
# =============================================================================


@pytest.fixture(scope="module")
def app() -> FastAPI:
    """The app the server runs, in this process (test mode: importing it never reaches the production data)."""
    assert is_test_mode(), "Precondition: test mode, so the app in process never reaches the production data directory"
    from backend.app.main import app as main_app  # noqa: PLC0415 — the server's own app, imported by the fixture that needs it

    return main_app


class NoDatabase:
    """The database session of every request: nothing of the panel's restore may reach it."""

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__"):
            raise AttributeError(name)
        raise AssertionError(f"the database was reached: session.{name}")


def _frozen_clock() -> float:
    return FROZEN_CLOCK_SECONDS


@contextmanager
def client_address_state_kept() -> Iterator[None]:
    """What a request leaves in ``client_address``'s process state, put back as it was."""
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
class Panel:
    """What a test works with: the app, the data directory, the fake threads of the checks, the attempts limiter, the
    restarts asked, and the monkeypatch to change the environment."""

    app: FastAPI
    root: Path
    threads: Any
    limiter: SlidingWindowLimiter
    monkeypatch: pytest.MonkeyPatch
    restarts: list[bool | None] = field(default_factory=list)
    answered: Any = None

    def state(self, name: str) -> None:
        """The instance in one of ``STATES``: the two switches unset, then set as the state says."""
        for variable in (AWAIT_VARIABLE, BLOCKED_VARIABLE, DELETION_DATE_VARIABLE):
            self.monkeypatch.delenv(variable, raising=False)
        for variable, value in STATES[name].items():
            self.monkeypatch.setenv(variable, value)

    def keys_off(self) -> None:
        self.monkeypatch.delenv(KEYS_VARIABLE, raising=False)

    @property
    def key(self) -> str | None:
        return client_address_module.client_rate_key(PEER[0])

    def counted(self) -> int:
        return self.limiter.count(self.key)

    def snapshot(self) -> dict[str, tuple]:
        """Everything below ``.restore``: what a refused request must leave as it was."""
        folder = restore_dir(self.root)
        return api.tree(folder) if folder.is_dir() else {}


class Answered:
    """The app wrapped: ``done`` turns true once the last byte of the answer has been sent."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.done = False

    async def __call__(self, scope, receive, send) -> None:
        async def sending(message) -> None:
            await send(message)
            if message.get("type") == "http.response.body" and not message.get("more_body", False):
                self.done = True

        await self.app(scope, receive, sending)


@pytest.fixture
def panel(app: FastAPI, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Panel]:
    """Every request of a test: no variable of the panel, the mode, the block or the limits from the runner; the panel's
    keys and public address set (L2 on); the instance in the normal state; test mode on ``tmp_path/data``; a fresh
    activity record, attempts limiter and fake threads; ``restart.request_restart`` recording; the database never
    reached. At the end, a check left held has its lock let go, as its server would."""
    for name in (*PANEL_ENVIRONMENT, AWAIT_VARIABLE, BLOCKED_VARIABLE, DELETION_DATE_VARIABLE, LIMIT_VARIABLE, MAX_RESTORE_VARIABLE):
        monkeypatch.delenv(name, raising=False)
    root = (tmp_path / "data").resolve()
    root.mkdir()
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(root))
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "selfhosted")
    monkeypatch.setenv("LF_APP_VERSION", cases.APP_VERSION)
    get_git_version.cache_clear()
    assert get_data_dir() == root, f"Precondition: the data directory is this test's own, not {get_data_dir()}"
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)
    monkeypatch.setenv(KEYS_VARIABLE, KEY.entry)
    monkeypatch.setattr(activity_module, "ACTIVITY", activity_module.Activity())
    limiter = SlidingWindowLimiter(ATTEMPT_LIMIT, ATTEMPT_WINDOW_SECONDS, clock=_frozen_clock)
    monkeypatch.setattr(access_module, "PANEL_ATTEMPTS", limiter)
    monkeypatch.setattr(client_address_module, "_configured_header", lambda: None)
    threads = api.Threads()
    monkeypatch.setattr(restore_jobs, "threading", threads)
    monkeypatch.setitem(app.dependency_overrides, get_session_generator, NoDatabase)
    made = Panel(app=app, root=root, threads=threads, limiter=limiter, monkeypatch=monkeypatch)

    def recorded_restart(*, pid: int | None = None) -> int:
        made.restarts.append(made.answered.done if made.answered is not None else None)
        return 0

    monkeypatch.setattr(restart_module, "request_restart", recorded_restart)
    monkeypatch.setattr(restart_module, "send_signal", lambda pid, sig: pytest.fail(f"a signal was sent: {pid} {sig}"))
    # SEC-review point 6: the process remembers a restart already asked (``panel_restore._restart_requested``); each test
    # starts as a fresh process would, and the flag is put back at its end. ``raising=False``: set even before the cure.
    monkeypatch.setattr(importlib.import_module(ROUTES_MODULE), RESTART_FLAG, False, raising=False)
    with client_address_state_kept():
        try:
            yield made
        finally:
            for thread in threads.held:
                if thread.lock is not None:
                    thread.lock.release()
            get_git_version.cache_clear()


# =============================================================================
# REQUESTS
# =============================================================================


async def send(panel: Panel, method: str, path: str, *, authorization: str | None = None, wrap: Any = None, **kwargs: Any) -> httpx.Response:
    """One request to the app in process, from ``PEER``; ``authorization`` the whole header value."""
    headers = dict(kwargs.pop("headers", None) or {})
    if authorization is not None:
        headers["Authorization"] = authorization
    transport = httpx.ASGITransport(app=wrap or panel.app, raise_app_exceptions=False, client=PEER)
    async with asyncio.timeout(TIMEOUT), httpx.AsyncClient(transport=transport, base_url=BASE_URL) as client:
        return await client.request(method, path, headers=headers, **kwargs)


def code(response: httpx.Response) -> tuple[int, str | None]:
    return api.code(response)


def answer(response: httpx.Response) -> tuple[int, Any]:
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, response.text[:400]


def shown(response: httpx.Response) -> str:
    return api.shown(response)


def passed_the_gates(response: httpx.Response) -> bool:
    """Whether the request went past the credential and the two gates: a JSON answer (or a 204), not the plain 404 of a
    path that does not exist, no 405 of the web app's catch-all, no code of a gate, no 401, 423, 429 or 503."""
    if response.status_code != 204 and not response.headers.get("content-type", "").startswith("application/json"):
        return False
    if answer(response) == OFF_ANSWER:
        return False
    status_code, error = code(response)
    return error not in GATE_CODES and status_code not in (401, 405, 423, 429, 503)


def served_by(app: FastAPI, endpoint: Endpoint) -> list[str]:
    """The functions that serve ``endpoint``'s method and path in the app's route table, as ``<module>.<function>``."""
    return [f"{context.endpoint.__module__}.{context.endpoint.__name__}" for context in iter_route_contexts(app.routes) if isinstance(context.original_route, APIRoute) and context.path == endpoint.path and endpoint.method in (context.methods or ())]


@dataclass(frozen=True)
class Endpoint:
    """One route of the panel's restore: the function that serves it, its method and path, and a request that reaches it
    without any state of the restore (an unknown id where it takes one)."""

    name: str
    function: str
    method: str
    path: str

    def url(self, stage_id: str = api.UNKNOWN_ID) -> str:
        return self.path.format(stage_id=stage_id)

    def body(self) -> dict[str, Any]:
        if self.name == "upload":
            return {"content": b"h62: a body that is not an envelope", "headers": {"Content-Type": "application/octet-stream"}}
        if self.name == "stage":
            return {"json": {"upload_id": api.UNKNOWN_ID, "password": PASSWORD}}
        return {}


ENDPOINTS = (
    Endpoint("upload", "upload_panel_restore_archive", "PUT", UPLOAD),
    Endpoint("stage", "start_panel_restore_check", "POST", STAGE),
    Endpoint("poll", "get_panel_restore_check", "GET", STAGE_ITEM),
    Endpoint("confirm", "confirm_panel_restore_check", "POST", CONFIRM),
    Endpoint("restart", "restart_panel_restore", "POST", RESTART),
    Endpoint("status", "get_panel_restore_status", "GET", STATUS),
    Endpoint("cancel", "cancel_panel_pending_restore", "DELETE", PENDING),
)
ENDPOINT_CASES = [pytest.param(endpoint, id=endpoint.name) for endpoint in ENDPOINTS]


async def call(panel: Panel, endpoint: Endpoint, authorization: str | None) -> httpx.Response:
    return await send(panel, endpoint.method, endpoint.url(), authorization=authorization, **endpoint.body())


async def served_barrier(panel: Panel, endpoint: Endpoint) -> None:
    """Presence barrier of every refusal case: in the mode, with a valid ticket, the route is served and lets the request
    past its gates. Without it, the plain 404 of a missing route would pass for «off». The instance is put back in the
    normal state."""
    served = served_by(panel.app, endpoint)
    assert served == [f"{ROUTES_MODULE}.{endpoint.function}"], f"H-62: {endpoint.method} {endpoint.path} must be served by {ROUTES_MODULE}.{endpoint.function} alone: {served}"
    panel.state("awaiting-restore")
    response = await call(panel, endpoint, ticket().authorization)
    panel.state("normal")
    assert passed_the_gates(response), f"H-62: {endpoint.method} {endpoint.path} ({ROUTES_MODULE}.{endpoint.function}) must be served, and a valid ticket in the mode must pass its gates: {shown(response)}"


# =============================================================================
# THE ARCHIVES
# =============================================================================


@dataclass(frozen=True)
class Archives:
    """The archives of this module: the backup with the canary administrators and its rewritten control totals, sealed
    (``changed_lfbk``) and as a plain zip (``zip_bytes``); the coordinator's ``.tar`` holding the sealed one; a second
    sealed backup (``other_lfbk``) for a second check; and the amounts of the differences."""

    changed_lfbk: bytes
    other_lfbk: bytes
    zip_bytes: bytes
    tar_bytes: bytes
    bumped: str


def seal(source: Path, target: Path, password: str = PASSWORD) -> bytes:
    encrypt_file(source, target, password, log2_n=TEST_LOG2_N)
    return target.read_bytes()


@pytest.fixture(scope="module")
def archives(databases, tmp_path_factory) -> Archives:
    root = tmp_path_factory.mktemp("h62-archives")
    with pytest.MonkeyPatch.context() as patch:
        cases.configure(patch, root / "configured-data-dir")
        built = cases.ledger_archive(root / "source", databases.head, accounts=CANARY_ACCOUNTS)
        other = cases.ledger_archive(root / "other", databases.head, accounts=CANARY_ACCOUNTS)
        get_git_version.cache_clear()
    real = cases.recorded_totals(built.manifest)
    assert isinstance(real, dict) and real["cash"] and real["quantities"], f"precondition: the totals of a ledger with cash and positions: {real}"
    first = real["cash"][0]
    bumped = str(Decimal(first["balance"]) + BUMP)
    recorded = {**real, "cash": [{**first, "balance": bumped}, *real["cash"][1:], {"broker_id": EXTRA_BROKER, "currency": EXTRA_CURRENCY, "balance": EXTRA_BALANCE}], "quantities": real["quantities"][:-1]}
    changed_zip = cases.pack(root / "changed.zip", cases.entries_of(built), cases.manifest_with_totals(built, recorded))
    changed_lfbk = seal(changed_zip, root / "backup.lfbk")
    other_lfbk = seal(other.path, root / "other.lfbk")
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        for name, data in (("manifest.json", json.dumps({"format": 1, "lfbk_size": len(changed_lfbk)}).encode()), ("backup.lfbk", changed_lfbk)):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = 1_760_000_000
            tar.addfile(info, io.BytesIO(data))
    return Archives(changed_lfbk=changed_lfbk, other_lfbk=other_lfbk, zip_bytes=changed_zip.read_bytes(), tar_bytes=tar_buffer.getvalue(), bumped=bumped)


def tiny_envelope(tmp_path: Path, password: str) -> bytes:
    """A small envelope, not a backup inside: enough for the password's refusals, whose check never starts."""
    source = tmp_path / f"tiny-{secrets.token_hex(4)}.bin"
    source.write_bytes(b"h62: not a backup zip, only something sealed\n" * 64)
    return seal(source, tmp_path / f"{source.stem}.lfbk", password)


# =============================================================================
# THE STEPS OF A RESTORE THROUGH THE PANEL
# =============================================================================


async def upload(panel: Panel, content: bytes | AsyncIterator[bytes], *, authorization: str | None = None) -> httpx.Response:
    return await send(panel, "PUT", UPLOAD, authorization=authorization or ticket().authorization, content=content, headers={"Content-Type": "application/octet-stream"})


async def uploaded(panel: Panel, content: bytes) -> str:
    response = await upload(panel, content)
    assert response.status_code == 201, f"precondition: the archive is received: {shown(response)}"
    return response.json()["upload_id"]


async def stage(panel: Panel, upload_id: str, password: str | None = PASSWORD) -> httpx.Response:
    body: dict[str, Any] = {"upload_id": upload_id}
    if password is not None:
        body["password"] = password
    return await send(panel, "POST", STAGE, authorization=ticket().authorization, json=body)


async def poll(panel: Panel, stage_id: str) -> httpx.Response:
    return await send(panel, "GET", STAGE_ITEM.format(stage_id=stage_id), authorization=ticket().authorization)


async def confirm(panel: Panel, stage_id: str, *, as_ticket: Ticket | None = None) -> httpx.Response:
    return await send(panel, "POST", CONFIRM.format(stage_id=stage_id), authorization=(as_ticket or ticket()).authorization)


async def restart(panel: Panel) -> httpx.Response:
    panel.answered = Answered(panel.app)
    return await send(panel, "POST", RESTART, authorization=ticket().authorization, wrap=panel.answered)


async def restore_status(panel: Panel) -> httpx.Response:
    return await send(panel, "GET", STATUS, authorization=ticket().authorization)


async def cancel(panel: Panel) -> httpx.Response:
    return await send(panel, "DELETE", PENDING, authorization=ticket().authorization)


async def checked(panel: Panel, content: bytes) -> dict:
    """``content`` uploaded and checked through the panel's routes (the check runs at once): the ended stage."""
    started = await stage(panel, await uploaded(panel, content))
    assert started.status_code == 202, f"precondition: the check starts: {shown(started)}"
    ended = await poll(panel, started.json()["stage_id"])
    assert ended.status_code == 200 and ended.json()["status"] == "done", f"precondition: the check has ended done: {shown(ended)}"
    return ended.json()


async def confirmed(panel: Panel, content: bytes) -> str:
    stage_id = (await checked(panel, content))["stage_id"]
    response = await confirm(panel, stage_id)
    assert response.status_code == 202, f"precondition: the restore is confirmed through the panel: {shown(response)}"
    return stage_id


def rewrite_state(root: Path, status: str) -> None:
    """The restore recorded in ``root`` moved to ``status``, as a start leaves it on disk."""
    state = apply_module.read_restore(root)
    assert state is not None, "precondition: a restore is recorded"
    finished = datetime(2026, 10, 23, 3, 30, tzinfo=UTC)
    fields: dict[str, Any] = {"status": status}
    if status in ("applying", "applied", "rolling_back"):
        fields["swap"] = [apply_module.SwapEntry(name=name, live=True, staged=True) for name in SWAPPED_FOLDERS]
        fields["boot"] = apply_module.Boot(pid=999_999, started=1_760_000_000.0)
    if status == "committed":
        fields.update(applied_at=finished - timedelta(minutes=5), finished_at=finished, session_version=int(finished.timestamp() * 1000))
    path = restore_state_path(root)
    path.write_text(state.model_copy(update=fields).model_dump_json(), encoding="utf-8")
    path.chmod(0o600)


# =============================================================================
# PR-001..010: THE SCOPE AND THE ORDER OF THE REFUSALS, ON EACH OF THE SEVEN
# =============================================================================


def test_the_scope_is_backup_restore_and_has_a_dependency_of_its_own():
    """PR-001 (Q8): ``PanelScope.BACKUP_RESTORE`` is ``"backup:restore"``, and ``panel_access`` gives it a dependency of its
    own, the same object at each call."""
    scope_class = h62(ACCESS_MODULE, "PanelScope")
    member = getattr(scope_class, "BACKUP_RESTORE", None)
    assert member is not None and member.value == RESTORE_SCOPE, f"H-62: PanelScope.BACKUP_RESTORE must be {RESTORE_SCOPE!r}: {list(scope_class)}"
    dependency = access_module.panel_access(member)
    assert dependency is access_module.panel_access(member), "panel_access gives the same object for the same scope"
    assert dependency not in {access_module.panel_access(other) for other in scope_class if other is not member}, "the restore scope has a dependency of its own"


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ENDPOINT_CASES)
async def test_without_the_panel_keys_each_route_answers_404_in_every_state(panel, endpoint):
    """PR-002 (§5): ticket only, so without ``LIBREFOLIO_PANEL_PUBLIC_KEYS`` each route answers ``404 Not Found``, as a
    path that does not exist, in each of the four states, without a credential and with any L1 token set and presented;
    nothing written, nothing counted, no restart."""
    await served_barrier(panel, endpoint)
    panel.keys_off()
    tokens = {variable: a_token() for variable in TOKEN_VARIABLES}
    for variable, value in tokens.items():
        panel.monkeypatch.setenv(variable, value)
    before, counted = panel.snapshot(), panel.counted()
    answers = {}
    for state in STATES:
        panel.state(state)
        for label, authorization in (("none", None), *((variable, f"Bearer {value}") for variable, value in tokens.items())):
            answers[f"{state}, {label}"] = answer(await call(panel, endpoint, authorization))

    assert answers == dict.fromkeys(answers, OFF_ANSWER), f"{endpoint.name}: without the keys, 404 Not Found whatever the state and the token: {answers}"
    assert (panel.snapshot(), panel.counted(), panel.restarts) == (before, counted, []), "nothing written, nothing counted, no restart"


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ENDPOINT_CASES)
async def test_without_a_credential_each_route_answers_its_401_in_every_state_and_counts_it(panel, endpoint):
    """PR-003 (§5, Q8): the keys set, no ``Authorization``: 401 ``backup_restore_unauthorized`` with ``WWW-Authenticate:
    Bearer``, the same in the four states (the caller learns neither the mode nor the block), each refusal counted."""
    await served_barrier(panel, endpoint)
    before = panel.snapshot()
    results = {}
    for state in STATES:
        panel.state(state)
        counted = panel.counted()
        response = await call(panel, endpoint, None)
        results[state] = (code(response), response.headers.get("www-authenticate"), panel.counted() - counted)

    assert results == dict.fromkeys(STATES, ((401, UNAUTHORIZED_CODE), "Bearer", 1)), f"{endpoint.name}: no credential → the scope's 401, counted, in every state: {results}"
    assert (panel.snapshot(), panel.restarts) == (before, []), "nothing written, no restart"


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ENDPOINT_CASES)
async def test_no_l1_token_opens_the_restore_and_each_one_is_counted(panel, endpoint):
    """PR-004 (§5: «nessun token L1 vale per questo scopo»): the backup download token, the wake token and the status
    token, each set and presented: 401 ``backup_restore_unauthorized``, counted once, in every state."""
    await served_barrier(panel, endpoint)
    tokens = {variable: a_token() for variable in TOKEN_VARIABLES}
    for variable, value in tokens.items():
        panel.monkeypatch.setenv(variable, value)
    before = panel.snapshot()
    results = {}
    for state in STATES:
        panel.state(state)
        for variable, value in tokens.items():
            counted = panel.counted()
            response = await call(panel, endpoint, f"Bearer {value}")
            results[f"{state}, {variable}"] = (code(response), panel.counted() - counted)

    assert results == dict.fromkeys(results, ((401, UNAUTHORIZED_CODE), 1)), f"{endpoint.name}: an L1 token is refused with the scope's 401 and counted: {results}"
    assert (panel.snapshot(), panel.restarts) == (before, []), "nothing written, no restart"


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ENDPOINT_CASES)
async def test_a_ticket_of_the_backup_scope_is_the_wrong_scope_in_every_state(panel, endpoint):
    """PR-005 (§5): a ticket of the panel signed for ``backup`` (the jobs' scope) → 401 ``panel_ticket_wrong_scope``,
    never counted (a valid signature), in every state."""
    await served_barrier(panel, endpoint)
    before = panel.snapshot()
    results = {}
    for state in STATES:
        panel.state(state)
        counted = panel.counted()
        response = await call(panel, endpoint, ticket(BACKUP_SCOPE).authorization)
        results[state] = (code(response), panel.counted() - counted)

    assert results == dict.fromkeys(STATES, ((401, WRONG_SCOPE_CODE), 0)), f"{endpoint.name}: a backup ticket is the wrong scope, not counted: {results}"
    assert (panel.snapshot(), panel.restarts) == (before, []), "nothing written, no restart"


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ENDPOINT_CASES)
async def test_a_ticket_used_once_is_replayed_the_second_time(panel, endpoint):
    """PR-006 (§5): in the mode, a valid ticket passes once; the same ticket again → 401 ``panel_ticket_replayed``."""
    served = served_by(panel.app, endpoint)
    assert served == [f"{ROUTES_MODULE}.{endpoint.function}"], f"H-62: {endpoint.method} {endpoint.path} must be served by {ROUTES_MODULE}.{endpoint.function} alone: {served}"
    panel.state("awaiting-restore")
    used = ticket()
    first = await call(panel, endpoint, used.authorization)
    second = await call(panel, endpoint, used.authorization)

    assert passed_the_gates(first), f"H-62: {endpoint.method} {endpoint.path} must let a valid ticket through in the mode: {shown(first)}"
    assert code(second) == (401, REPLAYED_CODE), f"{endpoint.name}: the same ticket again is replayed: {shown(second)}"


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ENDPOINT_CASES)
async def test_an_address_over_the_limit_gets_429_even_with_a_valid_ticket_in_every_state(panel, endpoint):
    """PR-007 (§5: «429 panel_too_many_attempts»): an address that sent 20 refused credentials gets 429 with
    ``Retry-After`` even with a valid ticket, in every state: the credential comes before the block and the mode."""
    await served_barrier(panel, endpoint)
    for _ in range(ATTEMPT_LIMIT):
        panel.limiter.hit(panel.key)
    before = panel.snapshot()
    results = {}
    for state in STATES:
        panel.state(state)
        response = await call(panel, endpoint, ticket().authorization)
        results[state] = (code(response), bool(response.headers.get("retry-after")))

    assert results == dict.fromkeys(STATES, ((429, TOO_MANY_CODE), True)), f"{endpoint.name}: over the limit → 429 with Retry-After, whatever the state: {results}"
    assert (panel.snapshot(), panel.restarts) == (before, []), "nothing written, no restart"


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ENDPOINT_CASES)
@pytest.mark.parametrize("broken", ["keys", "registry"])
async def test_unusable_keys_or_registry_answer_503_backup_restore_unavailable_in_every_state(panel, endpoint, broken):
    """PR-008 (Q8): keys the server cannot use, or a registry of used tickets out of reach → 503
    ``backup_restore_unavailable``, in every state."""
    await served_barrier(panel, endpoint)
    if broken == "keys":
        panel.monkeypatch.setenv(KEYS_VARIABLE, "not-a-key")
    else:

        def unreachable(*_args: Any, **_kwargs: Any) -> bool:
            raise ticket_registry.TicketRegistryError("the registry of the test is out of reach")

        panel.monkeypatch.setattr(ticket_registry, "record", unreachable)
    before = panel.snapshot()
    results = {}
    for state in STATES:
        panel.state(state)
        results[state] = code(await call(panel, endpoint, ticket().authorization))

    assert results == dict.fromkeys(STATES, (503, UNAVAILABLE_CODE)), f"{endpoint.name}: unusable {broken} → 503 {UNAVAILABLE_CODE}: {results}"
    assert (panel.snapshot(), panel.restarts) == (before, []), "nothing written, no restart"


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ENDPOINT_CASES)
@pytest.mark.parametrize("state", ["blocked", "blocked-and-awaiting-restore"])
async def test_a_valid_ticket_on_a_blocked_instance_gets_423_instance_blocked(panel, endpoint, state):
    """PR-009 (§5: «mai su un'istanza bloccata»): after the credential, a blocked instance → 423 ``instance_blocked``,
    with or without the mode (the block wins); nothing written, no restart."""
    await served_barrier(panel, endpoint)
    before = panel.snapshot()
    panel.state(state)
    response = await call(panel, endpoint, ticket().authorization)

    assert code(response) == (423, BLOCKED_CODE), f"{endpoint.name}, {state}: a valid ticket on a blocked instance → 423 {BLOCKED_CODE}: {shown(response)}"
    assert (panel.snapshot(), panel.restarts) == (before, []), "nothing written, no restart"


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ENDPOINT_CASES)
async def test_a_valid_ticket_outside_the_mode_gets_409_restore_mode_required(panel, endpoint):
    """PR-010 (§5): after the credential, on an instance not blocked and not in the mode → 409 ``restore_mode_required``;
    nothing written, no restart."""
    await served_barrier(panel, endpoint)
    before = panel.snapshot()
    panel.state("normal")
    response = await call(panel, endpoint, ticket().authorization)

    assert code(response) == (409, MODE_REQUIRED_CODE), f"{endpoint.name}: outside the mode → 409 {MODE_REQUIRED_CODE}: {shown(response)}"
    assert (panel.snapshot(), panel.restarts) == (before, []), "nothing written, no restart"


@pytest.mark.asyncio
async def test_a_restore_ticket_does_not_open_the_status_scope(panel):
    """PR-011, guard: a ticket of ``backup:restore`` presented to ``GET /panel/status`` is the wrong scope there: one
    scope, never another."""
    response = await send(panel, "GET", f"{API_V1_PREFIX}/panel/status", authorization=ticket().authorization)
    assert code(response) == (401, WRONG_SCOPE_CODE), f"a restore ticket on the status route → {WRONG_SCOPE_CODE}: {shown(response)}"


# =============================================================================
# PR-020..025: THE UPLOAD
# =============================================================================


@pytest.mark.asyncio
async def test_an_envelope_is_received_as_kind_envelope(panel, archives):
    """PR-020 (§5): in the mode, the ``.lfbk`` as the raw body → 201 with exactly ``upload_id`` (32 hex), ``size`` and
    ``kind: envelope``; the file is on disk, whole."""
    panel.state("awaiting-restore")
    response = await upload(panel, archives.changed_lfbk)

    assert response.status_code == 201, f"an envelope is received: {shown(response)}"
    body = response.json()
    assert set(body) == UPLOAD_FIELDS, f"the answer holds exactly {sorted(UPLOAD_FIELDS)}: {body}"
    assert api.AN_ID.fullmatch(body["upload_id"]) and (body["size"], body["kind"]) == (len(archives.changed_lfbk), "envelope"), f"its id, its size, kind envelope: {body}"
    assert upload_path(panel.root, body["upload_id"]).read_bytes() == archives.changed_lfbk, "the upload is on disk, byte for byte"


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["zip", "tar"])
async def test_a_zip_or_the_tar_is_400_restore_envelope_required_and_nothing_is_left(panel, archives, kind):
    """PR-021 (§5, D2): a plain zip, or the coordinator's ``.tar`` instead of its ``backup.lfbk`` member → 400
    ``restore_envelope_required``, and the uploaded file is removed: nothing left in the uploads folder."""
    panel.state("awaiting-restore")
    response = await upload(panel, archives.zip_bytes if kind == "zip" else archives.tar_bytes)

    assert code(response) == (400, "restore_envelope_required"), f"a {kind} → 400 restore_envelope_required: {shown(response)}"
    assert api.files_in(uploads_dir(panel.root)) == [], f"the {kind} is removed from disk: {api.files_in(uploads_dir(panel.root))}"


@pytest.mark.asyncio
@pytest.mark.parametrize("streamed", [False, True], ids=["with-its-content-length", "streamed"])
async def test_a_body_over_the_limit_is_413_backup_too_large_and_leaves_nothing(panel, streamed):
    """PR-022 (§5): the admin's limit, ``LIBREFOLIO_BACKUP_MAX_UPLOAD_MB``: 1 MB and one byte more, starting with the
    envelope's magic → 413 ``backup_too_large`` with ``limit_mb`` 1, declared or streamed; nothing left."""
    panel.state("awaiting-restore")
    panel.monkeypatch.setenv(LIMIT_VARIABLE, "1")
    # The body starts with the envelope's magic: the subject is the limit, not the kind (refused on its first bytes)
    body = ENVELOPE_MAGIC + b"\0" * (api.MIB + 1 - len(ENVELOPE_MAGIC))
    assert len(body) == api.MIB + 1, "precondition: 1 MB and one byte"
    response = await upload(panel, api.pieces(body) if streamed else body)

    assert api.too_large(response, 1), f"over the limit → 413 backup_too_large, limit_mb 1: {shown(response)}"
    assert api.files_in(uploads_dir(panel.root)) == [], f"nothing left: {api.files_in(uploads_dir(panel.root))}"


@pytest.mark.asyncio
async def test_a_second_upload_gets_a_new_id_and_the_first_is_dropped(panel, archives):
    """PR-023 (§5, «ripetibilità»): a ``PUT`` again → a new ``upload_id``; the earlier upload is dropped."""
    panel.state("awaiting-restore")
    first = await uploaded(panel, archives.changed_lfbk)
    second = await uploaded(panel, archives.other_lfbk)

    assert first != second, "a new upload id"
    assert (upload_path(panel.root, first).exists(), upload_path(panel.root, second).exists()) == (False, True), "the first upload is dropped, the second kept"


@pytest.mark.asyncio
async def test_a_ticket_that_expires_while_the_body_arrives_still_gets_201(panel, archives):
    """PR-024, R3 (§5): the ticket is checked once, before the body: a ticket whose ``exp`` is two seconds away (clock
    tolerance 0) and a body whose last piece leaves after ``exp`` → 201. Barrier: at that moment a ticket of the same
    ``exp`` is refused as expired, so the first one really expired during the body."""
    panel.state("awaiting-restore")
    panel.monkeypatch.setenv(SKEW_VARIABLE, "0")
    now = int(time.time())
    expiring_exp = now + 2
    expiring = ticket(iat=now - 5, exp=expiring_exp)
    data = archives.changed_lfbk
    sent_after: list[float] = []

    async def slow_body() -> AsyncIterator[bytes]:
        yield data[: len(data) // 2]
        deadline = time.monotonic() + R3_DEADLINE_SECONDS
        while time.time() <= expiring_exp + R3_PAST_EXPIRY_SECONDS:
            assert time.monotonic() < deadline, "R3: the wall clock did not pass the ticket's expiry in time"
            await asyncio.sleep(0.05)
        sent_after.append(time.time())
        yield data[len(data) // 2 :]

    response = await upload(panel, slow_body(), authorization=expiring.authorization)
    expired_twin = await send(panel, "GET", STATUS, authorization=ticket(iat=now - 5, exp=expiring_exp).authorization)

    assert response.status_code == 201 and response.json().get("kind") == "envelope", f"R3: the upload begun with a valid ticket ends 201 though the ticket expired meanwhile: {shown(response)}"
    assert sent_after and sent_after[0] > expiring_exp, f"Barrier: the last piece left after the ticket's exp: {sent_after}, exp {expiring_exp}"
    assert code(expired_twin) == (401, "panel_ticket_expired"), f"Barrier: a ticket of the same exp is expired by now: {shown(expired_twin)}"


# =============================================================================
# PR-030..033: THE CHECK, AND THE PANEL'S REPORT (R1)
# =============================================================================


@pytest.mark.asyncio
async def test_a_wrong_password_is_400_and_keeps_the_upload_for_the_right_one(panel, archives):
    """PR-030 (§5): ``POST …/stage`` with a wrong password → 400 ``wrong_password``, the upload kept; the right password
    then → 202 ``PanelRestoreStage``, exactly its fields."""
    panel.state("awaiting-restore")
    upload_id = await uploaded(panel, archives.changed_lfbk)
    wrong = await stage(panel, upload_id, WRONG_PASSWORD)

    assert code(wrong) == (400, "wrong_password"), f"a wrong password → 400 wrong_password: {shown(wrong)}"
    assert upload_path(panel.root, upload_id).is_file(), "the upload stays, for another try"
    right = await stage(panel, upload_id, PASSWORD)
    assert right.status_code == 202, f"the right password → 202: {shown(right)}"
    assert set(right.json()) == STAGE_FIELDS, f"the answer is PanelRestoreStage, exactly {sorted(STAGE_FIELDS)}: {sorted(right.json())}"


@pytest.mark.asyncio
async def test_the_panels_report_has_its_twenty_fields_and_no_data_of_the_portfolio(panel, archives):
    """PR-031, R1 (§5): a real check of a backup with two administrators (canary usernames) and three differences in the
    control totals. Barrier: the admin's report of that check names both administrators and holds the differences. The
    panel's ``GET …/stage/{id}``: ``report`` has exactly the 20 fields, ``administrators_count == 2``, ``control_totals``
    ``changed`` with 3 differences, restorable; the raw text holds no username or email, no amount, currency or broker
    of the differences."""
    print_section("H-62 R1: the panel's report of a real check")
    panel.state("awaiting-restore")
    ended = await checked(panel, archives.changed_lfbk)
    stage_id = ended["stage_id"]
    admin_view = read_report(panel.root, stage_id)
    assert sorted(admin_view.administrators) == CANARY_ADMINISTRATORS and admin_view.control_totals_differences_count == 3, f"Barrier: the admin's report names both administrators and holds 3 differences: {admin_view.administrators}, {admin_view.control_totals_differences_count}"
    assert archives.bumped in admin_view.model_dump_json(), "Barrier: the admin's report holds the bumped amount"

    response = await poll(panel, stage_id)
    report = response.json().get("report") or {}

    assert set(report) == REPORT_FIELDS, f"the panel's report is exactly the 20 fields of PanelRestoreStageReport: missing {sorted(REPORT_FIELDS - set(report))}, extra {sorted(set(report) - REPORT_FIELDS)}"
    assert (report["administrators_count"], report["control_totals"], report["control_totals_differences_count"], report["restorable"]) == (2, "changed", 3, True), f"administrators_count 2, totals changed with 3 differences, restorable: {report}"
    leaked = [value for value in (CANARY_MARK, archives.bumped, EXTRA_BALANCE, EXTRA_CURRENCY, '"broker_id"', '"asset_id"', "example.test") if value in response.text]
    assert leaked == [], f"the panel's answer holds data of the portfolio or of a person: {leaked}"
    print_success(f"report: {sorted(report)}; administrators_count 2; nothing of the portfolio")


def test_the_panel_views_have_exactly_their_fields_and_forbid_any_other():
    """PR-032 (§5, R1): ``PanelRestoreStageReport`` (``extra="forbid"``) has exactly the 20 fields;
    ``PanelRestoreStage`` its nine, the report typed as the panel's; ``PanelRestoreStatus`` its eleven, ``confirmed_via``
    and never ``confirmed_by``."""
    report_model = h62(SCHEMAS_MODULE, "PanelRestoreStageReport")
    stage_model = h62(SCHEMAS_MODULE, "PanelRestoreStage")
    status_model = h62(SCHEMAS_MODULE, "PanelRestoreStatus")

    assert set(report_model.model_fields) == REPORT_FIELDS, f"PanelRestoreStageReport: missing {sorted(REPORT_FIELDS - set(report_model.model_fields))}, extra {sorted(set(report_model.model_fields) - REPORT_FIELDS)}"
    assert report_model.model_config.get("extra") == "forbid", f"PanelRestoreStageReport forbids any other field: {report_model.model_config}"
    assert set(stage_model.model_fields) == STAGE_FIELDS, f"PanelRestoreStage: {sorted(stage_model.model_fields)}"
    assert report_model in getattr(stage_model.model_fields["report"].annotation, "__args__", (stage_model.model_fields["report"].annotation,)), f"PanelRestoreStage.report is the panel's report: {stage_model.model_fields['report'].annotation}"
    assert set(status_model.model_fields) == STATUS_FIELDS and "confirmed_by" not in status_model.model_fields, f"PanelRestoreStatus: {sorted(status_model.model_fields)}"


def test_the_router_receives_passwords_through_no_input_echo_routes():
    """PR-033 (§5): ``panel_restore_router`` and each of its routes use ``NoInputEchoRoute``, and it holds exactly the
    seven endpoints."""
    from backend.app.api.no_echo import NoInputEchoRoute  # noqa: PLC0415

    router = h62(ROUTES_MODULE, "panel_restore_router")
    assert router.route_class is NoInputEchoRoute, f"the router uses NoInputEchoRoute: {router.route_class!r}"
    names = sorted(route.endpoint.__name__ for route in router.routes)
    assert names == sorted(endpoint.function for endpoint in ENDPOINTS), f"the seven endpoints: {names}"
    assert all(isinstance(route, NoInputEchoRoute) for route in router.routes), "every route is a NoInputEchoRoute"


# =============================================================================
# PR-040..046: CONFIRM, RESTART, STATUS, CANCEL
# =============================================================================


@pytest.mark.asyncio
async def test_a_confirmation_is_pending_via_the_panel_and_carries_the_kid_in_the_log(panel, archives):
    """PR-040 (§5): ``POST …/confirm`` → 202 ``PanelRestoreStatus`` (its eleven fields, no ``confirmed_by``),
    ``pending``, the stage, ``confirmed_via == "panel"``; a line of the request other than the access line carries the
    ticket's ``kid``. Barrier: the capture sees a line of the access module's logger."""
    panel.state("awaiting-restore")
    stage_id = (await checked(panel, archives.changed_lfbk))["stage_id"]
    signed = ticket()
    with capture_logs(processors=[merge_contextvars]) as events:
        access_module.logger.info(LOG_CANARY)
        response = await confirm(panel, stage_id, as_ticket=signed)

    assert any(event.get("event") == LOG_CANARY for event in events), "Barrier: the capture sees the lines"
    assert response.status_code == 202, f"the confirmation → 202: {shown(response)}"
    body = response.json()
    assert set(body) == STATUS_FIELDS, f"PanelRestoreStatus, exactly: {sorted(body)}"
    assert (body["state"], body["stage_id"], body["confirmed_via"]) == ("pending", stage_id, "panel"), f"pending, this stage, via the panel: {body}"
    with_kid = [event for event in events if event.get("event") != access_module.REQUEST_LINE and event.get("kid") == signed.kid]
    assert with_kid, f"a line of the confirmation, beside the access line, carries the ticket's kid {signed.kid!r}: {[event.get('event') for event in events]}"


@pytest.mark.asyncio
async def test_confirming_the_same_stage_again_is_202_with_the_same_status(panel, archives):
    """PR-041 (§5, «ripetibilità»): the same ``stage_id`` confirmed again while pending → 202, the same status."""
    panel.state("awaiting-restore")
    stage_id = await confirmed(panel, archives.changed_lfbk)
    status_before = await restore_status(panel)
    again = await confirm(panel, stage_id)

    assert again.status_code == 202, f"the same stage again → 202, not 409: {shown(again)}"
    assert again.json() == status_before.json(), f"the same status: {again.json()} vs {status_before.json()}"


@pytest.mark.asyncio
async def test_another_stage_while_one_is_pending_is_409_restore_already_pending(panel, archives):
    """PR-042 (§5): another checked stage confirmed while a restore is pending → 409 ``restore_already_pending``; the
    pending one unchanged."""
    panel.state("awaiting-restore")
    pending_stage = await confirmed(panel, archives.changed_lfbk)
    other_stage = (await checked(panel, archives.other_lfbk))["stage_id"]
    response = await confirm(panel, other_stage)

    assert code(response) == (409, "restore_already_pending"), f"another stage → 409 restore_already_pending: {shown(response)}"
    assert apply_module.read_restore(panel.root).stage_id == pending_stage, "the pending restore is unchanged"


@pytest.mark.asyncio
async def test_a_restart_of_a_pending_restore_is_202_and_one_restart_after_the_answer(panel, archives):
    """PR-043 (§5): pending → ``POST …/restart`` 202 ``PanelRestoreStatus`` (no outcome ticket in it), and exactly one
    ``restart.request_restart``, once the answer was sent."""
    panel.state("awaiting-restore")
    stage_id = await confirmed(panel, archives.changed_lfbk)
    response = await restart(panel)

    assert response.status_code == 202, f"restart → 202: {shown(response)}"
    body = response.json()
    assert set(body) == STATUS_FIELDS and (body["state"], body["stage_id"]) == ("pending", stage_id), f"PanelRestoreStatus, pending, no outcome ticket: {body}"
    assert panel.restarts == [True], f"one restart, after the answer was sent: {panel.restarts}"


@pytest.mark.asyncio
@pytest.mark.parametrize(("phase", "state"), [("applying", "in_progress"), ("committed", "committed")])
async def test_a_restart_again_once_the_restore_runs_or_ended_is_202_with_its_state_and_no_restart(panel, archives, phase, state):
    """PR-044 (§5, «ripetibilità»): the restore of the last confirmed stage ``in_progress`` or ``committed`` →
    ``POST …/restart`` 202 with that state, and no second restart."""
    panel.state("awaiting-restore")
    await confirmed(panel, archives.changed_lfbk)
    rewrite_state(panel.root, phase)
    response = await restart(panel)

    assert response.status_code == 202 and response.json().get("state") == state, f"{phase}: 202 with state {state}: {shown(response)}"
    assert panel.restarts == [], f"no restart: {panel.restarts}"


@pytest.mark.asyncio
async def test_a_restart_without_any_restore_is_409_restore_not_pending(panel):
    """PR-045 (§5): no restore recorded → ``POST …/restart`` 409 ``restore_not_pending``, no restart."""
    panel.state("awaiting-restore")
    response = await restart(panel)

    assert code(response) == (409, "restore_not_pending"), f"no restore → 409 restore_not_pending: {shown(response)}"
    assert panel.restarts == [], f"no restart: {panel.restarts}"


@pytest.mark.asyncio
async def test_the_status_and_the_cancel_follow_the_restore(panel, archives):
    """PR-046 (§5): ``GET …/status`` ``none`` without a restore (its eleven fields), ``DELETE …/pending`` then 404
    ``restore_not_pending``; once confirmed, ``pending``; the cancel → 204, and the status ``none`` again."""
    panel.state("awaiting-restore")
    nothing = await restore_status(panel)
    nothing_to_cancel = await cancel(panel)
    assert nothing.status_code == 200 and set(nothing.json()) == STATUS_FIELDS and nothing.json()["state"] == "none", f"no restore → none: {shown(nothing)}"
    assert code(nothing_to_cancel) == (404, "restore_not_pending"), f"nothing pending → 404 restore_not_pending: {shown(nothing_to_cancel)}"

    stage_id = await confirmed(panel, archives.changed_lfbk)
    pending = await restore_status(panel)
    cancelled = await cancel(panel)
    after = await restore_status(panel)

    assert (pending.json()["state"], pending.json()["stage_id"]) == ("pending", stage_id), f"pending, this stage: {shown(pending)}"
    assert cancelled.status_code == 204, f"the cancel → 204: {shown(cancelled)}"
    assert after.json()["state"] == "none", f"none again: {shown(after)}"


# =============================================================================
# PR-050: NO ECHO OF THE PASSWORD
# =============================================================================

BAD_STAGE_BODIES = [
    pytest.param({"upload_id": "not-hex", "password": "{canary}"}, id="malformed-upload-id"),
    pytest.param({"upload_id": api.UNKNOWN_ID, "password": "{canary}", "extra": 1}, id="another-field"),
    pytest.param({"password": "{canary}"}, id="no-upload-id"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("template", BAD_STAGE_BODIES)
async def test_a_422_of_the_check_never_repeats_the_password(panel, template):
    """PR-050 (§5, ``NoInputEchoRoute``): in the mode, with a valid ticket, a body the validation refuses → 422, and the
    password it carries is nowhere in the answer."""
    panel.state("awaiting-restore")
    canary = f"h62-canary-password-{secrets.token_hex(8)}"
    body = {key: (canary if value == "{canary}" else value) for key, value in template.items()}
    response = await send(panel, "POST", STAGE, authorization=ticket().authorization, json=body)

    assert response.status_code == 422, f"a refused body → 422: {shown(response)}"
    assert canary not in response.text, f"the 422 repeats the password: {response.text}"


@pytest.mark.asyncio
async def test_no_log_record_of_the_check_holds_its_password(panel, tmp_path, caplog):
    """PR-051 (§5): the password of a check, wrong then right, appears in no line of the requests, structlog's or the
    standard library's. Barriers: the wrong one is refused 400 ``wrong_password``, the right one starts the check, and
    the capture sees a line of the access module's logger."""
    panel.state("awaiting-restore")
    right = f"h62-canary-right-{secrets.token_hex(8)}"
    wrong = f"h62-canary-wrong-{secrets.token_hex(8)}"
    upload_id = await uploaded(panel, tiny_envelope(tmp_path, right))
    caplog.set_level(logging.DEBUG)
    with capture_logs(processors=[merge_contextvars]) as events:
        access_module.logger.info(LOG_CANARY)
        refused = await stage(panel, upload_id, wrong)
        started = await stage(panel, upload_id, right)

    assert any(event.get("event") == LOG_CANARY for event in events), "Barrier: the capture sees the lines"
    assert code(refused) == (400, "wrong_password") and started.status_code == 202, f"Barrier: wrong refused, right started: {shown(refused)} / {shown(started)}"
    logged = repr(events) + caplog.text + repr([record.args for record in caplog.records])
    assert [value for value in (right, wrong) if value in logged] == [], "a password reached a log line"


# =============================================================================
# PR-060..072: THE CURES OF THE SECURITY REVIEW (SEC-review-backup-H62.md, points 3, 5, 6)
# =============================================================================

#: The envelope's magic (``instance_backup.envelope.MAGIC``): what the first bytes of an accepted upload must be.
ENVELOPE_MAGIC = b"LFBK"
#: The size of the pieces a client streams in the tests of point 3: small, so a body is many pieces.
SMALL_PIECE = 1024


@dataclass
class Pieces:
    """A body streamed from an async generator, recording how many pieces the server pulled from it."""

    chunks: list[bytes] = field(repr=False)
    pulled: int = 0

    async def stream(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            self.pulled += 1
            yield chunk

    @property
    def needed_for_magic(self) -> int:
        """The fewest pieces whose bytes reach the length of the magic."""
        seen = 0
        for index, chunk in enumerate(self.chunks, start=1):
            seen += len(chunk)
            if seen >= len(ENVELOPE_MAGIC):
                return index
        return len(self.chunks)


def split(data: bytes, layout: str) -> list[bytes]:
    """``data`` in pieces: ``SMALL_PIECE`` bytes each (``even``), or its first bytes one, then two, then one at a time
    before the rest (``split-head``: the magic arrives over four pieces)."""
    head: list[bytes] = []
    offset = 0
    if layout == "split-head":
        for size in (1, 2, 1):
            head.append(data[offset : offset + size])
            offset += size
    return head + [data[start : start + SMALL_PIECE] for start in range(offset, len(data), SMALL_PIECE)]


def body_of(archives: Archives, kind: str) -> bytes:
    return {"zip": archives.zip_bytes, "tar": archives.tar_bytes}[kind]


@pytest.mark.asyncio
@pytest.mark.parametrize("layout", ["even", "split-head"])
@pytest.mark.parametrize("kind", ["zip", "tar"])
async def test_a_body_that_is_not_an_envelope_is_refused_on_its_first_bytes_and_never_read_whole(panel, archives, kind, layout):
    """PR-060 (SEC-review point 3): a zip or the ``.tar``, streamed in many pieces → 400 ``restore_envelope_required``
    decided on its first four bytes (``LFBK`` or not): the route pulls no more pieces than those that carry the first
    four bytes, never the body to its end, and nothing of it (no file, no ``.part``) is under the uploads folder."""
    panel.state("awaiting-restore")
    data = body_of(archives, kind)
    assert not data.startswith(ENVELOPE_MAGIC), f"precondition: a {kind} does not start with the magic"
    body = Pieces(split(data, layout))
    assert len(body.chunks) >= 4 and body.needed_for_magic < len(body.chunks), f"precondition: the {kind} is many pieces, more than the magic needs: {len(body.chunks)}"
    response = await upload(panel, body.stream())
    pulled, needed, total = body.pulled, body.needed_for_magic, len(body.chunks)

    assert code(response) == (400, "restore_envelope_required"), f"a {kind} → 400 restore_envelope_required: {shown(response)}"
    assert pulled <= needed, f"the route stops reading at the first four bytes: pulled {pulled} of {total} pieces, the magic needs {needed}"
    assert api.files_in(uploads_dir(panel.root)) == [], f"nothing of the {kind} under the uploads folder: {api.files_in(uploads_dir(panel.root))}"


@pytest.mark.asyncio
@pytest.mark.parametrize("data", [b"P", b"PK", b"LFB", b"x\x00z"], ids=["one-byte", "two-bytes-of-a-zip", "three-bytes-of-the-magic", "three-other-bytes"])
async def test_a_body_shorter_than_the_magic_is_400_restore_envelope_required_and_leaves_nothing(panel, data):
    """PR-061 (SEC-review point 3), guard: one to three bytes, none of them the whole magic → 400
    ``restore_envelope_required``, nothing under the uploads folder."""
    panel.state("awaiting-restore")
    response = await upload(panel, data)

    assert code(response) == (400, "restore_envelope_required"), f"{data!r} → 400 restore_envelope_required: {shown(response)}"
    assert api.files_in(uploads_dir(panel.root)) == [], f"nothing left: {api.files_in(uploads_dir(panel.root))}"


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["zip", "tar"])
async def test_a_refused_upload_keeps_the_previous_good_envelope_on_disk_and_stageable(panel, archives, kind):
    """PR-062 (SEC-review point 3): an ``.lfbk`` received (201), then a zip or the ``.tar`` refused (400
    ``restore_envelope_required``): the good upload is still on disk, the only file of the uploads folder, and its check
    still starts (202). Today the refused body, written whole, first removes the upload it would replace."""
    panel.state("awaiting-restore")
    good = await uploaded(panel, archives.changed_lfbk)
    refused = await upload(panel, body_of(archives, kind))

    assert code(refused) == (400, "restore_envelope_required"), f"a {kind} → 400 restore_envelope_required: {shown(refused)}"
    assert api.files_in(uploads_dir(panel.root)) == [good], f"the good upload stays, alone, after the refused {kind}: {api.files_in(uploads_dir(panel.root))}"
    assert upload_path(panel.root, good).read_bytes() == archives.changed_lfbk, "the good upload is whole"
    started = await stage(panel, good)
    assert started.status_code == 202, f"the good upload is still stageable: {shown(started)}"


@pytest.mark.asyncio
@pytest.mark.parametrize("streamed", [False, True], ids=["no-content", "a-stream-of-no-piece"])
async def test_an_empty_body_is_still_400_backup_upload_empty(panel, streamed):
    """PR-063 (SEC-review point 3), guard: an empty body is not a wrong kind but no archive: 400 ``backup_upload_empty``,
    nothing left."""
    panel.state("awaiting-restore")
    response = await upload(panel, Pieces([]).stream() if streamed else b"")

    assert code(response) == (400, "backup_upload_empty"), f"an empty body → 400 backup_upload_empty: {shown(response)}"
    assert api.files_in(uploads_dir(panel.root)) == [], f"nothing left: {api.files_in(uploads_dir(panel.root))}"


@pytest.mark.asyncio
async def test_an_envelope_whose_magic_is_split_across_two_pieces_is_received_whole(panel, archives):
    """PR-064 (SEC-review point 3), guard: an ``.lfbk`` streamed as ``b"LF"``, ``b"BK…"`` and more pieces → 201, kind
    ``envelope``, its whole size, every piece read, the file on disk byte for byte."""
    panel.state("awaiting-restore")
    data = archives.changed_lfbk
    assert data.startswith(ENVELOPE_MAGIC), "precondition: the envelope starts with the magic"
    body = Pieces([data[:2], data[2:SMALL_PIECE], *(data[start : start + SMALL_PIECE] for start in range(SMALL_PIECE, len(data), SMALL_PIECE))])
    response = await upload(panel, body.stream())
    pulled, total = body.pulled, len(body.chunks)

    assert response.status_code == 201, f"an envelope with its magic split → 201: {shown(response)}"
    received = response.json()
    assert (received["kind"], received["size"], pulled) == ("envelope", len(data), total), f"kind envelope, its whole size, every piece read: {received}, pulled {pulled} of {total}"
    assert upload_path(panel.root, received["upload_id"]).read_bytes() == data, "the upload is on disk, byte for byte"


def answering(*checks: Any) -> tuple[list[tuple], Any]:
    """A stand-in for ``restore_jobs.running_check`` that answers ``checks`` in turn (then the last one again), and the
    list of its calls."""
    calls: list[tuple] = []

    def running_check(*args: Any, **kwargs: Any) -> Any:
        calls.append((args, kwargs))
        return checks[min(len(calls), len(checks)) - 1]

    return calls, running_check


def busy(*_args: Any, **_kwargs: Any) -> Any:
    staging = importlib.import_module("backend.app.services.platform.instance_backup.staging")
    raise staging.StagingBusyError("another archive is being checked (the race of the test)")


@pytest.mark.asyncio
async def test_two_identical_starts_racing_the_loser_answers_202_with_the_winners_check(panel, archives):
    """PR-070 (SEC-review point 5): two identical ``POST …/stage`` race: both see no running check, one takes the lock,
    the other gets ``StagingBusyError``. Simulated: ``running_check`` answers ``None`` first, then the panel's check
    that now runs; ``start_check`` raises ``StagingBusyError`` → the loser answers 202 with that check's ``stage_id``,
    not 409 ``restore_busy``. Barrier: the check really runs, started by the panel."""
    panel.state("awaiting-restore")
    panel.threads.hold = True
    upload_id = await uploaded(panel, archives.changed_lfbk)
    winner = await stage(panel, upload_id)
    assert winner.status_code == 202 and winner.json()["status"] == "running", f"precondition: the winner's check runs: {shown(winner)}"
    running = restore_jobs.running_check(upload_id, data_dir=panel.root)
    assert running is not None and running.origin == "panel" and running.stage_id == winner.json()["stage_id"], f"Barrier: the panel's check runs: {running!r}"

    calls, raced = answering(None, running)
    panel.monkeypatch.setattr(restore_jobs, "running_check", raced)
    panel.monkeypatch.setattr(restore_jobs, "start_check", busy)
    loser = await stage(panel, upload_id)
    panel.threads.hold = False
    panel.threads.run_held()

    assert loser.status_code == 202 and loser.json().get("stage_id") == running.stage_id, f"the loser of the race → 202 with the winner's stage {running.stage_id}: {shown(loser)}"
    assert len(calls) >= 2, f"the route looked again for the running check after StagingBusyError: {len(calls)} call(s)"


@pytest.mark.asyncio
async def test_a_busy_start_with_no_running_check_of_its_upload_is_still_409_restore_busy(panel, archives):
    """PR-071 (SEC-review point 5), guard: ``running_check`` answers ``None`` every time and ``start_check`` raises
    ``StagingBusyError`` (another upload is being checked) → 409 ``restore_busy``."""
    panel.state("awaiting-restore")
    upload_id = await uploaded(panel, archives.changed_lfbk)
    calls, never = answering(None)
    panel.monkeypatch.setattr(restore_jobs, "running_check", never)
    panel.monkeypatch.setattr(restore_jobs, "start_check", busy)
    response = await stage(panel, upload_id)

    assert code(response) == (409, "restore_busy"), f"busy, and no running check of this upload → 409 restore_busy: {shown(response)}"
    assert calls, "Barrier: the route asked for the running check"


@pytest.mark.asyncio
async def test_a_busy_start_whose_running_check_is_an_administrators_is_409_restore_busy(panel, archives):
    """PR-072 (SEC-review point 5), guard: after ``StagingBusyError`` the running check of the same upload is one an
    administrator started (origin ``admin``) → 409 ``restore_busy``: the panel is never answered with a check that is
    not its own. Barrier: that check runs, with the admin's origin."""
    panel.state("awaiting-restore")
    panel.threads.hold = True
    upload_id = await uploaded(panel, archives.changed_lfbk)
    admin_check = restore_jobs.start_check(upload_id, data_dir=panel.root, password=PASSWORD)
    assert admin_check.status == "running" and admin_check.origin == "admin", f"Barrier: the administrator's check runs: {admin_check!r}"

    calls, raced = answering(None, admin_check)
    panel.monkeypatch.setattr(restore_jobs, "running_check", raced)
    panel.monkeypatch.setattr(restore_jobs, "start_check", busy)
    response = await stage(panel, upload_id)
    panel.threads.hold = False
    panel.threads.run_held()

    assert code(response) == (409, "restore_busy"), f"the running check is an administrator's → 409 restore_busy: {shown(response)}"
    assert admin_check.stage_id not in response.text, f"the administrator's stage is not told to the panel: {response.text}"


@pytest.mark.asyncio
async def test_a_restart_asked_twice_while_still_pending_restarts_once(panel, archives):
    """PR-073 (SEC-review point 6): the panel retries ``POST …/restart`` (it lost the first answer) while the restore is
    still ``pending`` (the server has not stopped yet; here the restart is recorded, not real) → both answer 202 with
    the pending status, and ``restart.request_restart`` runs exactly once in the process. Barrier: the state is still
    pending after both."""
    panel.state("awaiting-restore")
    stage_id = await confirmed(panel, archives.changed_lfbk)
    first = await restart(panel)
    second = await restart(panel)

    assert apply_module.read_restore(panel.root).status == "pending", "Barrier: the restore is still pending, as before the server stops"
    for label, response in (("first", first), ("second", second)):
        assert response.status_code == 202 and (response.json().get("state"), response.json().get("stage_id")) == ("pending", stage_id), f"the {label} restart → 202 pending, this stage: {shown(response)}"
    assert panel.restarts == [True], f"one restart in the process, after the first answer: {panel.restarts}"


# =============================================================================
# Needs B (Q1..Q4) — what workstream B adds first; kept apart from H's reds
# =============================================================================


class TestNeedsB:
    """``# Needs B (Q1..Q4)``. Q1: the panel sees only its own stages (``RestoreCheck`` with an origin). Q2:
    ``confirmed_via`` stored in ``RestoreState``. Q4: ``POST …/stage`` repeatable while its check runs. (Q3, the jobs'
    409 in the mode, is in ``test_await_restore_mode_api.py``.)"""

    # Needs B (Q1)
    @pytest.mark.asyncio
    async def test_q1_a_stage_the_panel_did_not_start_is_not_found_for_the_panel(self, panel, archives):
        """Q1 (§5: «il pannello vede solo i suoi stage»): a check started without the panel's origin
        (``restore_jobs.start_check``, as the admin route and the CLI start one) → the panel's poll and confirmation answer
        404 ``restore_stage_not_found``; nothing confirmed. Barrier: the check exists and ended done."""
        panel.state("awaiting-restore")
        upload_id = await uploaded(panel, archives.changed_lfbk)
        check = restore_jobs.start_check(upload_id, data_dir=panel.root, password=PASSWORD)
        assert restore_jobs.read_check(check.stage_id, data_dir=panel.root).status == "done", "Barrier: the admin's check ended done"

        polled = await poll(panel, check.stage_id)
        confirmation = await confirm(panel, check.stage_id)

        assert code(polled) == (404, "restore_stage_not_found"), f"Q1: another origin's stage is not found by the panel's poll: {shown(polled)}"
        assert code(confirmation) == (404, "restore_stage_not_found"), f"Q1: nor by its confirmation: {shown(confirmation)}"
        assert apply_module.read_restore(panel.root) is None, "nothing confirmed"

    # Needs B (Q2)
    @pytest.mark.asyncio
    async def test_q2_the_state_stores_confirmed_via_panel(self, panel, archives):
        """Q2: the panel's confirmation is stored with ``confirmed_via == "panel"`` (``RestoreState.confirmed_via``), so
        an administrator named ``panel`` cannot pass for it."""
        panel.state("awaiting-restore")
        await confirmed(panel, archives.changed_lfbk)
        state = apply_module.read_restore(panel.root)

        assert getattr(state, "confirmed_via", None) == "panel", f"Q2: RestoreState.confirmed_via is 'panel': {state!r}"

    # Needs B (Q2)
    @pytest.mark.asyncio
    async def test_q2_a_restore_an_administrator_confirmed_reads_admin_without_the_username(self, panel, archives):
        """Q2: a restore confirmed by an administrator (``restore_jobs.confirm_check``) reads ``confirmed_via == "admin"``
        through the panel's status, and the username is nowhere in the answer."""
        panel.state("awaiting-restore")
        upload_id = await uploaded(panel, archives.changed_lfbk)
        check = restore_jobs.start_check(upload_id, data_dir=panel.root, password=PASSWORD)
        restore_jobs.confirm_check(check.stage_id, confirmed_by=CANARY_ADMINISTRATORS[0], data_dir=panel.root)
        response = await restore_status(panel)

        assert response.status_code == 200 and response.json().get("confirmed_via") == "admin", f"Q2: confirmed by an administrator → 'admin': {shown(response)}"
        assert CANARY_MARK not in response.text, f"the username is not in the panel's answer: {response.text}"

    # Needs B (Q4)
    @pytest.mark.asyncio
    async def test_q4_the_same_upload_while_its_check_runs_is_the_same_stage_and_another_is_busy(self, panel, archives):
        """Q4 (§5, «ripetibilità»): while the check of an upload runs, ``POST …/stage`` with the same ``upload_id`` → 202
        with the same ``stage_id``; with another upload → 409 ``restore_busy``."""
        panel.state("awaiting-restore")
        panel.threads.hold = True
        first_upload = await uploaded(panel, archives.changed_lfbk)
        first = await stage(panel, first_upload)
        assert first.status_code == 202 and first.json()["status"] == "running", f"precondition: the check runs: {shown(first)}"

        again = await stage(panel, first_upload)
        other_upload = await uploaded(panel, archives.other_lfbk)
        other = await stage(panel, other_upload)
        panel.threads.hold = False
        panel.threads.run_held()

        assert again.status_code == 202 and again.json().get("stage_id") == first.json()["stage_id"], f"Q4: the same upload → 202, the same stage: {shown(again)}"
        assert code(other) == (409, "restore_busy"), f"Q4: another upload → 409 restore_busy: {shown(other)}"
