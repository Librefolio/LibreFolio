"""
An unreadable restore state serves no data, through the API (LibreFolio 1.3, workstream H, lot B-33, the start's part).
Developer decision (22/10, via the coordinator): while the state of the restore cannot be read, the instance serves no
data; the web app shows «the restore stopped half way: call the administrator», and the administrator chooses with
``./dev.py backup pending --recover`` (workstream B). D7 (developer, contract L3 §10 option A), the last lot of wave
4: ``panel/status`` says it (200, ``restore.state == "unreadable"`` with its reason, instead of Q7's 500), and the
panel's backup does not start in this state.

Under test, written by B-33 (H) and missing today:

- ``backend.app.api.v1.instance_block.refuse_when_restore_interrupted``, the THIRD dependency of the ``/api/v1``
  router, after ``refuse_when_blocked`` and ``refuse_when_awaiting_restore``; ``INSTANCE_RESTORE_INTERRUPTED_CODE =
  "instance_restore_interrupted"``; ``ALLOWED_WHEN_RESTORE_INTERRUPTED``, the same set as
  ``ALLOWED_WHEN_AWAITING_RESTORE`` (pinned equal, and by name and route). While
  ``restore_guard.restore_interrupted()`` every other ``/api/v1`` route answers 423
  ``{"detail": {"code": "instance_restore_interrupted", "message": ...}}`` to anyone, no session asked: login,
  registration, ``/auth/setup``, ``/auth/me`` and every data route included.
- ``GET /system/instance``: ``restore_interrupted: bool`` (default False; ``InstanceConfigResponse``), true while
  interrupted.
- ``POST /system/wake-sync`` (its token) while interrupted: 200, ``status: restore_interrupted``, no job, nothing past
  the scheduler's switches.
- ``GET /panel/status`` while interrupted: still allowed, never the 423; an unreadable state → 200 with ``restore ==
  {"state": "unreadable", "reason": <io|not_a_file|invalid>, "waiting": null, "backup_created_at": null, "stage_id":
  null}`` (D7; red until D7, the route answers Q7's 500).
- D7, ``POST /backup/panel/jobs`` while interrupted: with its valid token → 409 ``{"detail": {"code":
  "backup_restore_interrupted", "message": ...}}``, no job created (``job_views.start_job`` never called), refused by
  ``refuse_when_restore_interrupted`` for that endpoint only. The credential first: no token configured → 404, a token
  configured and none (or another) presented → 401 ``backup_panel_unauthorized``, the same answers as outside the state,
  never the 409. ``GET …/jobs/{id}``, ``…/file`` and ``DELETE …/jobs/{id}`` stay allowed (their own 404, not 409, not
  423); outside the state the start works as before (guard).

How. As ``test_await_restore_mode_api.py`` (H-62), whose fixtures and helpers this file reuses: the app of
``backend/app/main.py`` in this process through ``httpx.ASGITransport`` (its lifespan does not run, so nothing probes
the restore: the process starts not interrupted), every request's session on a private SQLite file under ``tmp_path``,
the switches through ``monkeypatch``; the interruption is ``restore_guard._interrupted``, set with ``monkeypatch`` as
the contract says and restored after each case. Every name of B-33 is read by the test that needs it, so the file
collects and each test reports its own red; the case that sends a request to every route checks first that the
dependency guards each of them, so before B-33 it sends nothing.

Isolation: pure. No server, no lane database, no network, no file outside ``tmp_path``.
"""

from __future__ import annotations

import importlib
import json
import secrets
from datetime import UTC, datetime
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.backup import job_views
from backend.app.api.v1.instance_block import ALLOWED_WHEN_AWAITING_RESTORE, refuse_when_awaiting_restore, refuse_when_blocked
from backend.app.api.v1.system import wake as wake_module
from backend.app.config import API_V1_PREFIX
from backend.app.db.models import User
from backend.app.schemas.backup import InstanceBackupJob
from backend.app.services.platform.instance_backup import jobs as backup_jobs
from backend.app.services.platform.scheduler import scheduler
from backend.app.services.platform.sleep_wake import idle_monitor
from backend.test_scripts.test_api import test_await_restore_mode_api as h62
from backend.test_scripts.test_api.test_await_restore_mode_api import (
    ALLOWED_WHEN_AWAITING_RESTORE_ROUTES,
    AWAITING_CODE,
    BACKUP_TOKEN_VARIABLE,
    BLOCKED_CODE,
    DOCUMENTATION_PATHS,
    PANEL_STATUS_KEYS,
    PAST_THE_SWITCHES,
    UNREADABLE_REASONS,
    WAKE_TOKEN_VARIABLE,
    Instance,
    _api_routes,
    _concrete,
    _endpoint_name,
    _settled_at_once,
    _trap,
    code,
    panel_status,
    send,
    shown,
    signed_in,
    unreadable_restore,
    write_unreadable_state,
)
from backend.test_scripts.test_utils import print_section, print_success

# =============================================================================
# THE CONTRACT, SPELLED OUT
# =============================================================================

#: H-62's fixtures, reused: the app of main.py, and a test's instance on its private database.
app = h62.app
instance = h62.instance

BLOCK_MODULE = "backend.app.api.v1.instance_block"
GUARD_MODULE = "backend.app.services.platform.restore_guard"
INTERRUPTED_CODE = "instance_restore_interrupted"
PASSWORD = "RestoreInterruptedPass123!"
NEW_USERNAME = "b33ri_reg"

_MISSING = object()


def b33(module: str, name: str) -> Any:
    """``module.name`` of B-33, read by the test that needs it: each test fails on its own while it is missing."""
    try:
        imported = importlib.import_module(module)
    except ModuleNotFoundError as exc:
        if exc.name != module:
            raise
        pytest.fail(f"B-33: there is no {module}")
    value = getattr(imported, name, _MISSING)
    if value is _MISSING:
        pytest.fail(f"B-33: {module} gives no {name}")
    return value


def guard() -> ModuleType:
    try:
        return importlib.import_module(GUARD_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != GUARD_MODULE:
            raise
        pytest.fail(f"B-33: there is no {GUARD_MODULE}")


def interrupt(target: Instance, value: bool = True) -> None:
    """The process's interruption, set as the contract says (``restore_guard._interrupted``); restored after the case."""
    module = guard()
    if not hasattr(module, "_interrupted"):
        pytest.fail(f"B-33: {GUARD_MODULE} keeps no _interrupted")
    target.monkeypatch.setattr(module, "_interrupted", value)


def _detail(response: Any) -> Any:
    try:
        body = response.json()
    except ValueError:
        return None
    return body.get("detail") if isinstance(body, dict) else None


# =============================================================================
# RI-001..003: THE DEPENDENCY, ITS CODE, ITS ALLOWED SET, ITS PLACE
# =============================================================================


def test_the_interruption_has_its_dependency_its_code_and_the_allowed_set_of_the_mode(app):
    """RI-001: ``refuse_when_restore_interrupted`` exists, ``INSTANCE_RESTORE_INTERRUPTED_CODE`` is
    ``"instance_restore_interrupted"``, and ``ALLOWED_WHEN_RESTORE_INTERRUPTED`` is ``ALLOWED_WHEN_AWAITING_RESTORE``:
    the same endpoints, each serving its one pinned route."""
    print_section("B-33: the allowed set while the restore is interrupted")
    dependency = b33(BLOCK_MODULE, "refuse_when_restore_interrupted")
    code_value = b33(BLOCK_MODULE, "INSTANCE_RESTORE_INTERRUPTED_CODE")
    allowed = b33(BLOCK_MODULE, "ALLOWED_WHEN_RESTORE_INTERRUPTED")

    assert callable(dependency) and code_value == INTERRUPTED_CODE, f"the dependency, and its code {INTERRUPTED_CODE!r}: {code_value!r}"
    assert set(allowed) == set(
        ALLOWED_WHEN_AWAITING_RESTORE
    ), f"ALLOWED_WHEN_RESTORE_INTERRUPTED must equal ALLOWED_WHEN_AWAITING_RESTORE: only here {sorted(map(_endpoint_name, set(allowed) - set(ALLOWED_WHEN_AWAITING_RESTORE)))}, missing {sorted(map(_endpoint_name, set(ALLOWED_WHEN_AWAITING_RESTORE) - set(allowed)))}"
    names = sorted(_endpoint_name(endpoint) for endpoint in allowed)
    assert names == sorted(ALLOWED_WHEN_AWAITING_RESTORE_ROUTES), f"ALLOWED_WHEN_RESTORE_INTERRUPTED changed:\n  expected {sorted(ALLOWED_WHEN_AWAITING_RESTORE_ROUTES)}\n  got      {names}"
    routes: dict[str, set[tuple[str, str]]] = {}
    for context in _api_routes(app):
        if context.endpoint in allowed:
            routes.setdefault(_endpoint_name(context.endpoint), set()).update((method, context.path) for method in context.methods or ())
    assert routes == {name: {route} for name, route in ALLOWED_WHEN_AWAITING_RESTORE_ROUTES.items()}, f"each allowed endpoint serves exactly its one route: {routes}"
    print_success(f"{len(names)} endpoints allowed while interrupted, the set of the mode")


def test_every_route_under_api_v1_resolves_the_block_the_mode_then_the_interruption_first(app):
    """RI-002: every API route under /api/v1 (but the documentation) resolves ``refuse_when_blocked``,
    ``refuse_when_awaiting_restore`` and ``refuse_when_restore_interrupted`` as its first three dependencies, in this
    order (AM-002 keeps pinning the first two)."""
    dependency = b33(BLOCK_MODULE, "refuse_when_restore_interrupted")
    contexts = [context for context in _api_routes(app) if context.path not in DOCUMENTATION_PATHS]
    assert len(contexts) > 50, f"Barrier: the walk reaches the API routes: {len(contexts)}"

    wrong = {}
    for context in contexts:
        calls = [item.call for item in context.dependant.dependencies[:3]]
        if calls != [refuse_when_blocked, refuse_when_awaiting_restore, dependency]:
            wrong[f"{sorted(context.methods or ())} {context.path}"] = [getattr(call, "__name__", call) for call in calls]
    assert wrong == {}, f"these routes do not resolve block, mode, interruption first: {dict(list(wrong.items())[:10])} ({len(wrong)} in all)"


def test_the_public_configuration_declares_restore_interrupted_a_boolean_false_by_default():
    """RI-003: ``InstanceConfigResponse.restore_interrupted``: a boolean, false by default."""
    from backend.app.schemas.system import InstanceConfigResponse  # noqa: PLC0415

    prop = InstanceConfigResponse.model_json_schema().get("properties", {}).get("restore_interrupted")
    assert prop is not None, f"B-33: InstanceConfigResponse has no restore_interrupted: {sorted(InstanceConfigResponse.model_fields)}"
    assert (prop.get("type"), prop.get("default")) == ("boolean", False), f"restore_interrupted is a boolean, false by default: {prop}"


# =============================================================================
# RI-010..014: WHILE INTERRUPTED, 423 FOR ANYONE BUT THE ALLOWED SET
# =============================================================================


@pytest.mark.asyncio
async def test_while_interrupted_every_route_outside_the_set_answers_423_to_anyone(instance):
    """RI-010: interrupted, neither switch: each method of each API route outside the allowed set, sent without a
    session and without a body, answers 423 ``instance_restore_interrupted`` with a message. Barrier: the dependency
    guards every route, checked first, so that before B-33 nothing is sent."""
    dependency = b33(BLOCK_MODULE, "refuse_when_restore_interrupted")
    allowed = b33(BLOCK_MODULE, "ALLOWED_WHEN_RESTORE_INTERRUPTED")
    contexts = [context for context in _api_routes(instance.app) if context.path not in DOCUMENTATION_PATHS and context.endpoint not in allowed]
    unguarded = [context.path for context in contexts if dependency not in [item.call for item in context.dependant.dependencies]]
    assert unguarded == [], f"Barrier: the interruption's dependency guards every route: {unguarded[:10]}"
    instance.switches()
    interrupt(instance)

    answers = {}
    messages = set()
    for context in contexts:
        for method in sorted((context.methods or set()) - {"HEAD", "OPTIONS"}):
            response = await send(instance, method, _concrete(context.path))
            answers[f"{method} {context.path}"] = code(response)
            detail = _detail(response)
            messages.add(isinstance(detail, dict) and isinstance(detail.get("message"), str) and bool(detail["message"]))

    wrong = {name: result for name, result in answers.items() if result != (423, INTERRUPTED_CODE)}
    assert len(answers) > 50, f"Barrier: many routes were asked: {len(answers)}"
    assert wrong == {}, f"while interrupted these routes did not answer 423 {INTERRUPTED_CODE} to an anonymous caller: {dict(list(wrong.items())[:15])} ({len(wrong)} of {len(answers)})"
    assert messages == {True}, "every refusal carries a message beside its code"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        pytest.param("POST", "/auth/register", {"username": NEW_USERNAME, "email": f"{NEW_USERNAME}@example.com", "password": PASSWORD}, id="register"),
        pytest.param("POST", "/auth/setup", {"token": "b33-not-a-setup-token", "password": PASSWORD}, id="setup"),
        pytest.param("POST", "/auth/login", {"username": NEW_USERNAME, "password": PASSWORD}, id="login"),
        pytest.param("GET", "/auth/me", None, id="me"),
        pytest.param("GET", "/brokers", None, id="data-route"),
    ],
)
@pytest.mark.parametrize("with_session", [False, True], ids=["anonymous", "signed-in"])
async def test_registration_setup_login_me_and_data_answer_423_while_interrupted(instance, method, path, body, with_session):
    """RI-011: while interrupted, registration, the first administrator's setup, the login, ``/auth/me`` and a data
    route answer 423 ``instance_restore_interrupted``, anonymous or signed in; no account is created. Barrier: not
    interrupted, the same session reads ``/auth/me`` and ``/brokers``."""
    session = await signed_in(instance)
    me = await send(instance, "GET", f"{API_V1_PREFIX}/auth/me", headers=session)
    brokers = await send(instance, "GET", f"{API_V1_PREFIX}/brokers", headers=session)
    assert (me.status_code, brokers.status_code) == (200, 200), f"Barrier: not interrupted the session reads /auth/me and /brokers: {shown(me)} / {shown(brokers)}"
    interrupt(instance)

    response = await send(instance, method, f"{API_V1_PREFIX}{path}", json=body, headers=session if with_session else {})

    assert code(response) == (423, INTERRUPTED_CODE), f"{method} {path} while interrupted → 423 {INTERRUPTED_CODE}: {shown(response)}"
    async with AsyncSession(instance.engine) as db:
        created = (await db.execute(select(func.count()).select_from(User).where(User.username == NEW_USERNAME))).scalar_one()
    assert created == 0, "no account is created while interrupted"


@pytest.mark.asyncio
async def test_while_interrupted_the_allowed_routes_never_answer_the_refusal(instance):
    """RI-012: while interrupted the allowed routes answer on their own terms, never 423: health, readiness, the
    version and the public configuration 200; the lane probe, the wake-up, the panel's status, its backup jobs and its
    restore routes their own answers while off. Barrier: a data route is 423 ``instance_restore_interrupted``."""
    interrupt(instance)
    barrier = await send(instance, "GET", f"{API_V1_PREFIX}/brokers")
    answers = {}
    for name, (method, path) in ALLOWED_WHEN_AWAITING_RESTORE_ROUTES.items():
        answers[name] = code(await send(instance, method, _concrete(path)))

    assert code(barrier) == (423, INTERRUPTED_CODE), f"Barrier: a data route is 423 while interrupted: {shown(barrier)}"
    wrong = {name: result for name, result in answers.items() if result[0] == 423 or result[1] == INTERRUPTED_CODE}
    assert wrong == {}, f"an allowed route answered the interruption's refusal: {wrong}"
    public = {name: answers[name][0] for name in ("backend.app.api.v1.system.health.health_check", "backend.app.api.v1.system.ready.get_readiness", "backend.app.api.v1.system.info.get_system_info", "backend.app.api.v1.system.instance.get_instance_config")}
    assert public == dict.fromkeys(public, 200), f"health, readiness, version and configuration answer 200 while interrupted: {public}"


@pytest.mark.asyncio
@pytest.mark.parametrize("interrupted", [False, True], ids=["readable", "interrupted"])
async def test_the_public_configuration_says_whether_the_restore_is_interrupted(instance, interrupted):
    """RI-013: ``GET /system/instance`` → 200 with ``restore_interrupted`` as the process's answer, ``mode`` normal
    (neither switch)."""
    interrupt(instance, interrupted)
    response = await send(instance, "GET", f"{API_V1_PREFIX}/system/instance")

    assert response.status_code == 200, f"the public configuration answers 200: {shown(response)}"
    body = response.json()
    assert (body.get("restore_interrupted"), body.get("mode")) == (interrupted, "normal"), f"restore_interrupted {interrupted}, mode normal: {body}"


@pytest.mark.asyncio
async def test_a_process_that_never_probed_serves_and_says_not_interrupted(instance):
    """RI-014: the in-process app never ran its startup, so nothing probed the restore: ``restore_interrupted()`` is
    False, the public configuration says ``restore_interrupted: false`` and a signed-in user reads a data route."""
    answer = b33(GUARD_MODULE, "restore_interrupted")()
    session = await signed_in(instance)
    brokers = await send(instance, "GET", f"{API_V1_PREFIX}/brokers", headers=session)
    config = await send(instance, "GET", f"{API_V1_PREFIX}/system/instance")

    assert answer is False, "a process that never probed is not interrupted"
    assert brokers.status_code == 200, f"not interrupted, a data route serves: {shown(brokers)}"
    assert config.status_code == 200 and config.json().get("restore_interrupted") is False, f"restore_interrupted false: {shown(config)}"


@pytest.mark.asyncio
async def test_guard_outside_the_interruption_a_signed_in_user_is_served(instance):
    """Guard: neither switch and nothing probed, a signed-in user reads ``/auth/me`` and a data route (what the reds
    above use as their barrier)."""
    instance.switches()
    session = await signed_in(instance)
    me = await send(instance, "GET", f"{API_V1_PREFIX}/auth/me", headers=session)
    brokers = await send(instance, "GET", f"{API_V1_PREFIX}/brokers", headers=session)

    assert (me.status_code, brokers.status_code) == (200, 200), f"outside the interruption the session is served: {shown(me)} / {shown(brokers)}"


# =============================================================================
# RI-020: THE SCHEDULED WAKE-UP WHILE INTERRUPTED
# =============================================================================


@pytest.mark.asyncio
async def test_the_wake_up_while_interrupted_answers_restore_interrupted_and_runs_nothing(instance):
    """RI-020: interrupted, with its token and the real ``run_due_jobs``: ``POST /system/wake-sync`` → 200, ``status:
    restore_interrupted``, no job, and nothing past the scheduler's switches reached."""
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
    instance.switches()
    interrupt(instance)

    response = await send(instance, "POST", f"{API_V1_PREFIX}/system/wake-sync", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200, f"the wake-up answers 200 while interrupted: {shown(response)}"
    body = json.loads(response.content)
    assert (body.get("status"), body.get("jobs")) == ("restore_interrupted", []), f"status restore_interrupted, no job: {body}"
    assert reached == [], f"nothing past the switches while interrupted: {reached}"


# =============================================================================
# RI-030..031: THE PANEL'S STATUS, AND THE OTHER SWITCHES
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", UNREADABLE_REASONS)
async def test_while_interrupted_the_panel_status_says_the_state_is_unreadable_with_its_reason(instance, reason):
    """RI-030 (D7, replaces Q7's 500): interrupted, a restore state on disk B's reader refuses with ``reason``: ``GET
    /panel/status`` with its token → 200, ``restore`` exactly ``{state: unreadable, reason, waiting: null,
    backup_created_at: null, stage_id: null}``, ``mode`` normal; never the 423 of the interruption, never the 500."""
    write_unreadable_state(instance.root, reason, instance.monkeypatch)
    interrupt(instance)
    response = await panel_status(instance)

    assert response.status_code == 200, f"D7: while interrupted the panel's status answers 200 for an unreadable state ({reason}): {shown(response)}"
    body = response.json()
    assert set(body) == PANEL_STATUS_KEYS and (body["mode"], body["restore"]) == ("normal", unreadable_restore(reason)), f"D7: restore unreadable with {reason!r}, mode normal: {body}"


@pytest.mark.asyncio
async def test_while_interrupted_the_panel_status_without_a_restore_answers_200(instance):
    """RI-030b: interrupted, no restore recorded on disk: ``GET /panel/status`` with its token → 200, ``restore``
    null, ``mode`` normal — the route is allowed and unchanged."""
    interrupt(instance)
    response = await panel_status(instance)

    assert response.status_code == 200, f"the panel's status is allowed while interrupted: {shown(response)}"
    body = response.json()
    assert (body.get("mode"), body.get("restore")) == ("normal", None), f"mode normal, no restore: {body}"


@pytest.mark.asyncio
@pytest.mark.parametrize(("awaiting", "blocked", "codes"), [pytest.param(True, False, (AWAITING_CODE, INTERRUPTED_CODE), id="awaiting"), pytest.param(False, True, (BLOCKED_CODE, INTERRUPTED_CODE), id="blocked")])
async def test_with_another_switch_on_a_signed_in_user_still_meets_423(instance, awaiting, blocked, codes):
    """RI-031: interrupted and in the mode, or interrupted and blocked: a signed-in user's request to a data route →
    423, the code of either. Barrier: the session reads it with neither switch and not interrupted."""
    session = await signed_in(instance)
    before = await send(instance, "GET", f"{API_V1_PREFIX}/brokers", headers=session)
    assert before.status_code == 200, f"Barrier: the session reads /brokers: {shown(before)}"
    interrupt(instance)
    instance.switches(awaiting=awaiting, blocked=blocked)

    response = await send(instance, "GET", f"{API_V1_PREFIX}/brokers", headers=session)

    assert response.status_code == 423 and code(response)[1] in codes, f"423 with one of {codes}: {shown(response)}"


# =============================================================================
# RI-040..043 (D7): THE PANEL'S BACKUP WHILE INTERRUPTED
# =============================================================================

JOBS_PATH = f"{API_V1_PREFIX}/backup/panel/jobs"
#: A job id of the right shape that no job has.
UNKNOWN_JOB_ID = "0123456789abcdef0123456789abcdef"
RESTORE_INTERRUPTED_BACKUP_CODE = "backup_restore_interrupted"
BACKUP_UNAUTHORIZED_CODE = "backup_panel_unauthorized"
NOT_FOUND_ANSWER = (404, {"detail": "Not Found"})


class StartRecorder:
    """Stands in for ``job_views.start_job``: records each start and answers a running job, so no backup is built."""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple, dict]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> InstanceBackupJob:
        self.calls.append((args, kwargs))
        return InstanceBackupJob(job_id=secrets.token_hex(16), status="running", done_bytes=0, total_bytes=0, created_at=datetime.now(UTC), encrypted=False)


def no_backup(instance: Instance) -> tuple[StartRecorder, list[str]]:
    """The start of a job recorded (``job_views.start_job``) and the backup service a trap (``jobs.start_backup``): what a
    refused start must leave untouched."""
    recorder = StartRecorder()
    reached: list[str] = []
    instance.monkeypatch.setattr(job_views, "start_job", recorder)
    instance.monkeypatch.setattr(backup_jobs, "start_backup", _trap("jobs.start_backup", reached))
    return recorder, reached


def backup_token(instance: Instance) -> dict[str, str]:
    """The panel's backup token configured, and the ``Authorization`` header that presents it."""
    token = secrets.token_hex(32)
    instance.monkeypatch.setenv(BACKUP_TOKEN_VARIABLE, token)
    return {"Authorization": f"Bearer {token}"}


def _answer(response: Any) -> tuple[int, Any]:
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, response.text[:300]


@pytest.mark.asyncio
async def test_while_interrupted_the_panels_backup_start_is_409_backup_restore_interrupted_and_starts_nothing(instance):
    """RI-040 (D7): interrupted, the backup token configured and presented: ``POST /backup/panel/jobs`` → 409 ``{"detail":
    {"code": "backup_restore_interrupted", "message": ...}}``; no job started, the backup service never reached. Barrier:
    the same token passes the credential while interrupted (``GET …/jobs/{unknown}`` answers the route's own 404)."""
    recorder, reached = no_backup(instance)
    headers = backup_token(instance)
    instance.switches()
    interrupt(instance)
    barrier = await send(instance, "GET", f"{JOBS_PATH}/{UNKNOWN_JOB_ID}", headers=headers)
    assert code(barrier) == (404, "backup_job_not_found"), f"Barrier: the token passes the credential while interrupted: {shown(barrier)}"

    response = await send(instance, "POST", JOBS_PATH, headers=headers)

    detail = _detail(response)
    assert code(response) == (409, RESTORE_INTERRUPTED_BACKUP_CODE), f"D7: a panel backup while interrupted → 409 {RESTORE_INTERRUPTED_BACKUP_CODE}: {shown(response)}"
    assert isinstance(detail, dict) and set(detail) == {"code", "message"} and isinstance(detail["message"], str) and detail["message"], f"the refusal is a code and a message: {detail}"
    assert (recorder.calls, reached) == ([], []), f"D7: no backup starts while interrupted: start_job {recorder.calls}, reached {reached}"


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["no-token-configured", "no-credential", "another-token"])
async def test_while_interrupted_the_panels_backup_start_checks_the_credential_first(instance, case):
    """RI-041 (D7, guard of the credential-first order): no token configured and none presented → 404 ``Not Found``; a
    token configured and none presented, or another one → 401 ``backup_panel_unauthorized``. The same answer interrupted
    or not, never the 409 of the state; no job started either way."""
    recorder, reached = no_backup(instance)
    headers: dict[str, str] = {}
    if case != "no-token-configured":
        backup_token(instance)
    if case == "another-token":
        headers = {"Authorization": f"Bearer {secrets.token_hex(32)}"}
    expected = NOT_FOUND_ANSWER if case == "no-token-configured" else (401, BACKUP_UNAUTHORIZED_CODE)
    instance.switches()
    answers = {}
    for interrupted in (False, True):
        interrupt(instance, interrupted)
        response = await send(instance, "POST", JOBS_PATH, headers=headers)
        answers[interrupted] = _answer(response) if case == "no-token-configured" else code(response)

    assert answers == {False: expected, True: expected}, f"{case}: the credential's answer {expected}, interrupted or not, never the 409: {answers}"
    assert (recorder.calls, reached) == ([], []), f"no backup starts without the credential: {recorder.calls}, {reached}"


@pytest.mark.asyncio
@pytest.mark.parametrize(("method", "suffix"), [("GET", "/{job_id}"), ("GET", "/{job_id}/file"), ("DELETE", "/{job_id}")], ids=["poll", "download", "delete"])
async def test_while_interrupted_the_panels_other_backup_routes_answer_on_their_own_terms(instance, method, suffix):
    """RI-042 (D7, guard): interrupted, the backup token presented: the poll, the download and the delete of a job are
    not refused by the state (neither 409 nor 423): an unknown job answers each route's own 404 ``backup_job_not_found``."""
    headers = backup_token(instance)
    instance.switches()
    interrupt(instance)
    response = await send(instance, method, JOBS_PATH + suffix.format(job_id=UNKNOWN_JOB_ID), headers=headers)

    assert code(response) == (404, "backup_job_not_found"), f"D7: {method} …/jobs{suffix} stays allowed while interrupted, its own 404: {shown(response)}"


@pytest.mark.asyncio
async def test_guard_outside_the_interruption_the_panels_backup_starts_as_before(instance):
    """RI-043 (D7, guard): not interrupted, the backup token presented: ``POST /backup/panel/jobs`` → 202 with the job
    ``job_views.start_job`` answers, started once for the panel."""
    recorder, reached = no_backup(instance)
    headers = backup_token(instance)
    instance.switches()
    interrupt(instance, False)
    response = await send(instance, "POST", JOBS_PATH, headers=headers)

    assert response.status_code == 202, f"outside the interruption the panel's backup starts: {shown(response)}"
    assert len(recorder.calls) == 1 and recorder.calls[0][0][:1] == ("panel",) and reached == [], f"one start, for the panel: {recorder.calls}, reached {reached}"
