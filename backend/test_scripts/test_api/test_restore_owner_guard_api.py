"""
A restore whose owner has no account yet serves no data, through the API (LibreFolio 1.3, workstream H, lot H5-3).
Selector: ``api restore-owner-guard``. Written RED before H5-3; the guard's own contract is in
``test_services/test_restore_owner_guard.py``.

While ``restore_guard._owner_problem`` is set (``pending``, or the code of A's refusal) the instance answers as it does for
an interrupted restore (B-33, ``test_restore_interrupted_api.py``, whose fixtures and helpers this file reuses):

- every ``/api/v1`` route but ``ALLOWED_WHEN_RESTORE_INTERRUPTED`` answers 423 ``instance_restore_interrupted`` to anyone
  (login, registration, setup, me and data included); the allowed set answers on its own terms; the panel's backup start
  answers 409 ``backup_restore_interrupted`` after its credential;
- ``refuse_when_restore_interrupted`` first awaits ``refresh_restore_state()``: a ``pending`` state whose last check is
  at least ``OWNER_RECHECK_SECONDS`` old is asked again (``apply.owner_assignment_problem``, patched here with a fake and the
  guard's patched clock), so it heals once another worker records the outcome; a ``<CODE>`` never does; a request asks nothing
  when it is not due;
- ``GET /system/instance``: ``restore_interrupted`` is true for both reasons, ``restore_interrupted_reason`` says which
  (``restore_state`` wins over ``owner_assignment``), None when serving;
- ``POST /system/wake-sync`` answers ``restore_interrupted`` and runs nothing.

Pure: the app of ``backend/app/main.py`` in this process (ASGI), every request's session on a private SQLite file under
``tmp_path``; the guard's variables and clock, and B's hook, through ``monkeypatch``. No server, no lane database.
"""

from __future__ import annotations

import json
import secrets

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.system import wake as wake_module
from backend.app.config import API_V1_PREFIX
from backend.app.db.models import User
from backend.app.services.platform.scheduler import scheduler
from backend.app.services.platform.sleep_wake import idle_monitor
from backend.test_scripts.test_api import test_restore_interrupted_api as ri
from backend.test_scripts.test_api.test_await_restore_mode_api import (
    ALLOWED_WHEN_AWAITING_RESTORE_ROUTES,
    DOCUMENTATION_PATHS,
    PAST_THE_SWITCHES,
    WAKE_TOKEN_VARIABLE,
    Instance,
    _api_routes,
    _concrete,
    _settled_at_once,
    _trap,
    code,
    send,
    shown,
    signed_in,
)
from backend.test_scripts.test_services.test_restore_owner_guard import Asker, Clock, arm, guard_name, install

# The fixtures of the interrupted restore's API tests, reused: the app of main.py and a test's instance.
app = ri.app
instance = ri.instance

INTERRUPTED_CODE = ri.INTERRUPTED_CODE
PROBLEMS = ("pending", "EMAIL_TAKEN")
PASSWORD = "RestoreOwnerGuardPass123!"
NEW_USERNAME = "h53og_reg"


def block(instance: Instance, *, problem: str | None, interrupted: bool = False, now: float = 0.0, answers: tuple[str | None, ...] = (None,)) -> tuple[Clock, Asker]:
    """The process's state and B's hook, as the contract says: neither switch, the guard's variables and clock, and
    ``apply.owner_assignment_problem`` replaced by a fake that answers ``answers`` in turn."""
    instance.switches()
    clock = arm(instance.monkeypatch, problem=problem, interrupted=interrupted, now=now)
    return clock, install(instance.monkeypatch, Asker(*answers))


async def brokers(instance: Instance, session: dict[str, str]):
    return await send(instance, "GET", f"{API_V1_PREFIX}/brokers", headers=session)


# =============================================================================
# 423 while an owner problem is set
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("problem", PROBLEMS)
async def test_while_the_owner_has_no_account_every_route_outside_the_set_answers_423_to_anyone(instance, problem):
    """Every method of every API route outside the allowed set, sent without a session and without a body, answers 423
    ``instance_restore_interrupted`` with a message, while ``_owner_problem`` is ``problem``; no request is due, so the guard
    asks nothing. Barrier: the same app serves a signed-in user with no owner problem, and the dependency guards every route."""
    allowed = ri.b33(ri.BLOCK_MODULE, "ALLOWED_WHEN_RESTORE_INTERRUPTED")
    dependency = ri.b33(ri.BLOCK_MODULE, "refuse_when_restore_interrupted")
    contexts = [context for context in _api_routes(instance.app) if context.path not in DOCUMENTATION_PATHS and context.endpoint not in allowed]
    unguarded = [context.path for context in contexts if dependency not in [item.call for item in context.dependant.dependencies]]
    assert unguarded == [], f"Barrier: the interruption's dependency guards every route: {unguarded[:10]}"
    session = await signed_in(instance)
    _clock, asker = block(instance, problem=None)
    served = await brokers(instance, session)
    assert served.status_code == 200, f"Barrier: with no owner problem the session reads /brokers: {shown(served)}"
    _clock, asker = block(instance, problem=problem)

    answers, messages = {}, set()
    for context in contexts:
        for method in sorted((context.methods or set()) - {"HEAD", "OPTIONS"}):
            response = await send(instance, method, _concrete(context.path))
            answers[f"{method} {context.path}"] = code(response)
            detail = ri._detail(response)
            messages.add(isinstance(detail, dict) and isinstance(detail.get("message"), str) and bool(detail["message"]))

    wrong = {name: result for name, result in answers.items() if result != (423, INTERRUPTED_CODE)}
    assert len(answers) > 50, f"Barrier: many routes were asked: {len(answers)}"
    assert wrong == {}, f"owner problem {problem!r}: these routes did not answer 423 {INTERRUPTED_CODE}: {dict(list(wrong.items())[:15])} ({len(wrong)} of {len(answers)})"
    assert messages == {True}, "every refusal carries a message beside its code"
    assert asker.calls == [], f"nothing was due, so nothing was asked: {asker.calls}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        pytest.param("POST", "/auth/register", {"username": NEW_USERNAME, "email": f"{NEW_USERNAME}@example.com", "password": PASSWORD}, id="register"),
        pytest.param("POST", "/auth/setup", {"token": "h53-not-a-setup-token", "password": PASSWORD}, id="setup"),
        pytest.param("POST", "/auth/login", {"username": NEW_USERNAME, "password": PASSWORD}, id="login"),
        pytest.param("GET", "/auth/me", None, id="me"),
        pytest.param("GET", "/brokers", None, id="data-route"),
    ],
)
@pytest.mark.parametrize("with_session", [False, True], ids=["anonymous", "signed-in"])
async def test_registration_setup_login_me_and_data_answer_423_while_the_owner_is_pending(instance, method, path, body, with_session):
    """Registration, the first administrator's setup, the login, ``/auth/me`` and a data route answer 423
    ``instance_restore_interrupted`` while the owner is ``pending``, anonymous or signed in; no account is created. Barrier:
    with no owner problem the same session reads ``/auth/me`` and ``/brokers``."""
    session = await signed_in(instance)
    block(instance, problem=None)
    me = await send(instance, "GET", f"{API_V1_PREFIX}/auth/me", headers=session)
    served = await brokers(instance, session)
    assert (me.status_code, served.status_code) == (200, 200), f"Barrier: with no owner problem the session is served: {shown(me)} / {shown(served)}"
    block(instance, problem="pending")

    response = await send(instance, method, f"{API_V1_PREFIX}{path}", json=body, headers=session if with_session else {})

    assert code(response) == (423, INTERRUPTED_CODE), f"{method} {path} with the owner pending → 423 {INTERRUPTED_CODE}: {shown(response)}"
    async with AsyncSession(instance.engine) as db:
        created = (await db.execute(select(func.count()).select_from(User).where(User.username == NEW_USERNAME))).scalar_one()
    assert created == 0, "no account is created while the owner is pending"


@pytest.mark.asyncio
@pytest.mark.parametrize("problem", PROBLEMS)
async def test_while_the_owner_has_no_account_the_allowed_routes_never_answer_the_refusal(instance, problem):
    """The allowed set answers on its own terms, never 423 ``instance_restore_interrupted``: health, readiness, version and
    the public configuration 200. Barrier: a data route is refused with the same state."""
    block(instance, problem=problem)
    barrier = await send(instance, "GET", f"{API_V1_PREFIX}/brokers")
    answers = {}
    for name, (method, path) in ALLOWED_WHEN_AWAITING_RESTORE_ROUTES.items():
        answers[name] = code(await send(instance, method, _concrete(path)))

    assert code(barrier) == (423, INTERRUPTED_CODE), f"Barrier: a data route is 423 with the owner problem: {shown(barrier)}"
    wrong = {name: result for name, result in answers.items() if result[0] == 423 or result[1] == INTERRUPTED_CODE}
    assert wrong == {}, f"an allowed route answered the refusal: {wrong}"
    public = {name: answers[name][0] for name in ("backend.app.api.v1.system.health.health_check", "backend.app.api.v1.system.ready.get_readiness", "backend.app.api.v1.system.info.get_system_info", "backend.app.api.v1.system.instance.get_instance_config")}
    assert public == dict.fromkeys(public, 200), f"health, readiness, version and configuration answer 200: {public}"


# =============================================================================
# The recheck, through the dependency
# =============================================================================


@pytest.mark.asyncio
async def test_a_pending_owner_that_heals_in_the_files_stops_refusing_after_the_interval(instance):
    """The hook answers ``pending`` once, then None, with the guard's clock: at t=0 a signed-in user meets 423 and nothing
    is asked; at t=2.5 (past ``OWNER_RECHECK_SECONDS``) the request asks, finds ``pending``, and is still refused; at t=100
    it asks again, finds None, and is served — and every later request asks nothing."""
    session = await signed_in(instance)
    clock, asker = block(instance, problem="pending", answers=("pending", None))

    first = await brokers(instance, session)
    assert code(first) == (423, INTERRUPTED_CODE) and asker.calls == [], f"t=0: refused, nothing asked: {shown(first)}, {asker.calls}"
    clock.now = 2.5
    second = await brokers(instance, session)
    assert code(second) == (423, INTERRUPTED_CODE) and len(asker.calls) == 1, f"t=2.5: asked once, still pending, refused: {shown(second)}, {asker.calls}"
    clock.now = 100.0
    third = await brokers(instance, session)
    assert third.status_code == 200 and len(asker.calls) == 2, f"t=100: asked again, healed, served: {shown(third)}, {asker.calls}"
    clock.now = 100_000.0
    again = await brokers(instance, session)
    assert again.status_code == 200 and len(asker.calls) == 2, f"healed for good: served, nothing asked again: {shown(again)}, {asker.calls}"


@pytest.mark.asyncio
async def test_a_pending_owner_still_pending_is_not_asked_by_every_request(instance):
    """(inferred from "cheap when not due"; confirm with the coordinator) After a re-ask that finds ``pending`` again, the
    requests of the next 2.0 s ask nothing."""
    session = await signed_in(instance)
    clock, asker = block(instance, problem="pending", now=10.0, answers=("pending",))
    clock.now = 20.0
    for _ in range(3):
        response = await brokers(instance, session)
        assert code(response) == (423, INTERRUPTED_CODE), f"refused: {shown(response)}"
    assert len(asker.calls) == 1, f"three requests at the same instant, one question: {asker.calls}"


@pytest.mark.asyncio
async def test_an_allowed_route_also_refreshes_the_state(instance):
    """The refresh comes first, before the allowed set is looked at: the public configuration, read by the app, shows the
    owner pending, then the owner set once the hook answers None and the interval has passed."""
    clock, asker = block(instance, problem="pending", answers=(None,))
    before = await send(instance, "GET", f"{API_V1_PREFIX}/system/instance")
    clock.now = 5.0
    after = await send(instance, "GET", f"{API_V1_PREFIX}/system/instance")

    assert before.status_code == 200 and after.status_code == 200, f"the configuration answers 200: {shown(before)} / {shown(after)}"
    assert (before.json().get("restore_interrupted"), before.json().get("restore_interrupted_reason")) == (True, "owner_assignment"), f"t=0: owner pending: {before.json()}"
    assert (after.json().get("restore_interrupted"), after.json().get("restore_interrupted_reason")) == (False, None), f"t=5: healed: {after.json()}"
    assert len(asker.calls) == 1, f"one question, at t=5: {asker.calls}"


@pytest.mark.asyncio
@pytest.mark.parametrize("problem", ["EMAIL_TAKEN", "USER_NOT_FOUND"])
async def test_a_code_is_never_healed_however_late(instance, problem):
    """A ``<CODE>`` is final for the process: with the hook ready to answer None and 100 000 s gone, the user still meets 423
    and nothing is asked."""
    session = await signed_in(instance)
    clock, asker = block(instance, problem=problem, answers=(None,))
    clock.now = 100_000.0

    response = await brokers(instance, session)

    assert code(response) == (423, INTERRUPTED_CODE), f"{problem}: still refused: {shown(response)}"
    assert asker.calls == [], f"a code is never asked again: {asker.calls}"


@pytest.mark.asyncio
async def test_without_an_owner_problem_a_request_asks_nothing(instance):
    """No owner problem, much later: a signed-in user is served and the guard asks nothing: no request reads a file."""
    session = await signed_in(instance)
    clock, asker = block(instance, problem=None, answers=("pending",))
    clock.now = 100_000.0

    response = await brokers(instance, session)

    assert response.status_code == 200, f"served: {shown(response)}"
    assert asker.calls == [], f"nothing is asked without an owner problem: {asker.calls}"


# =============================================================================
# GET /system/instance
# =============================================================================


def test_the_public_configuration_declares_the_reason_of_the_interruption():
    """``InstanceConfigResponse.restore_interrupted_reason``: null by default, otherwise ``restore_state`` or
    ``owner_assignment``."""
    from backend.app.schemas.system import InstanceConfigResponse  # noqa: PLC0415

    prop = InstanceConfigResponse.model_json_schema().get("properties", {}).get("restore_interrupted_reason")
    assert prop is not None, f"H5-3: InstanceConfigResponse has no restore_interrupted_reason: {sorted(InstanceConfigResponse.model_fields)}"
    enums = {value for branch in prop.get("anyOf", [prop]) for value in branch.get("enum", [])}
    nullable = any(branch.get("type") == "null" for branch in prop.get("anyOf", []))
    assert (enums, nullable, prop.get("default", "<missing>")) == ({"restore_state", "owner_assignment"}, True, None), f"a nullable choice of the two reasons, null by default: {prop}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("interrupted", "problem", "expected", "reason"),
    [
        pytest.param(False, None, False, None, id="serving"),
        pytest.param(False, "pending", True, "owner_assignment", id="owner-pending"),
        pytest.param(False, "EMAIL_TAKEN", True, "owner_assignment", id="owner-code"),
        pytest.param(True, None, True, "restore_state", id="state-unreadable"),
        pytest.param(True, "pending", True, "restore_state", id="state-wins"),
    ],
)
async def test_the_public_configuration_says_whether_and_why_the_restore_is_interrupted(instance, interrupted, problem, expected, reason):
    """``GET /system/instance`` → 200: ``restore_interrupted`` is true for both reasons, ``restore_interrupted_reason`` names
    it (``restore_state`` wins), None when serving; ``mode`` stays normal."""
    block(instance, problem=problem, interrupted=interrupted)

    response = await send(instance, "GET", f"{API_V1_PREFIX}/system/instance")

    assert response.status_code == 200, f"the public configuration answers 200: {shown(response)}"
    body = response.json()
    assert (body.get("restore_interrupted"), body.get("restore_interrupted_reason"), body.get("mode")) == (expected, reason, "normal"), f"interrupted={interrupted}, owner problem={problem!r}: {body}"


# =============================================================================
# The panel's backup, and the wake-up
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("problem", PROBLEMS)
async def test_while_the_owner_has_no_account_the_panels_backup_start_is_409_and_starts_nothing(instance, problem):
    """The backup token configured and presented: ``POST /backup/panel/jobs`` → 409 ``backup_restore_interrupted`` (a code and
    a message); no job started. The credential first: a wrong token is 401 ``backup_panel_unauthorized``, never the 409. The
    poll of an unknown job stays on its own 404. Barrier: with no owner problem the start answers 202."""
    recorder, reached = ri.no_backup(instance)
    headers = ri.backup_token(instance)
    block(instance, problem=None)
    outside = await send(instance, "POST", ri.JOBS_PATH, headers=headers)
    assert outside.status_code == 202 and len(recorder.calls) == 1, f"Barrier: with no owner problem the panel's backup starts: {shown(outside)}"
    recorder.calls.clear()
    block(instance, problem=problem)

    refused = await send(instance, "POST", ri.JOBS_PATH, headers=headers)
    other = await send(instance, "POST", ri.JOBS_PATH, headers={"Authorization": f"Bearer {secrets.token_hex(32)}"})
    poll = await send(instance, "GET", f"{ri.JOBS_PATH}/{ri.UNKNOWN_JOB_ID}", headers=headers)

    detail = ri._detail(refused)
    assert code(refused) == (409, ri.RESTORE_INTERRUPTED_BACKUP_CODE), f"owner problem {problem!r}: 409 {ri.RESTORE_INTERRUPTED_BACKUP_CODE}: {shown(refused)}"
    assert isinstance(detail, dict) and set(detail) == {"code", "message"} and detail["message"], f"a code and a message: {detail}"
    assert code(other) == (401, ri.BACKUP_UNAUTHORIZED_CODE), f"the credential first: {shown(other)}"
    assert code(poll) == (404, "backup_job_not_found"), f"the poll stays allowed, its own 404: {shown(poll)}"
    assert (recorder.calls, reached) == ([], []), f"no backup starts: {recorder.calls}, {reached}"


@pytest.mark.asyncio
async def test_the_panels_backup_starts_again_once_a_pending_owner_heals(instance):
    """``pending`` at t=0 → 409; the hook answers None and the interval has passed → the same start answers 202."""
    recorder, reached = ri.no_backup(instance)
    headers = ri.backup_token(instance)
    clock, asker = block(instance, problem="pending", answers=(None,))

    before = await send(instance, "POST", ri.JOBS_PATH, headers=headers)
    clock.now = 5.0
    after = await send(instance, "POST", ri.JOBS_PATH, headers=headers)

    assert code(before) == (409, ri.RESTORE_INTERRUPTED_BACKUP_CODE), f"t=0: refused: {shown(before)}"
    assert after.status_code == 202 and len(recorder.calls) == 1 and reached == [], f"t=5: healed, one start: {shown(after)}, {recorder.calls}"
    assert len(asker.calls) == 1, f"one question: {asker.calls}"


@pytest.mark.asyncio
@pytest.mark.parametrize("problem", PROBLEMS)
async def test_the_wake_up_while_the_owner_has_no_account_answers_restore_interrupted_and_runs_nothing(instance, problem):
    """With its token and the real ``run_due_jobs``: ``POST /system/wake-sync`` → 200, ``status: restore_interrupted``, no
    job, and nothing past the scheduler's switches reached."""
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
    block(instance, problem=problem)

    response = await send(instance, "POST", f"{API_V1_PREFIX}/system/wake-sync", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200, f"the wake-up answers 200: {shown(response)}"
    body = json.loads(response.content)
    assert (body.get("status"), body.get("jobs")) == ("restore_interrupted", []), f"status restore_interrupted, no job: {body}"
    assert reached == [], f"nothing past the switches: {reached}"
    assert guard_name("restore_interrupted")() is True, "the guard says interrupted"
