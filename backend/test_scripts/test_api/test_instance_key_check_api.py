"""
The instance key check, through the API (LibreFolio 1.3, workstream H, lot H5-7, decision D6).
Selector: ``api instance-key-check``. Written RED before H5-7; the module's own contract is in
``test_services/test_instance_key_check.py``, whose helpers this file reuses.

With a wrong instance key only the hosting panel's backup jobs and ``wake-sync`` stop; the instance keeps serving:

- ``GET /panel/status`` holds ``instance_key: ok|mismatch`` (nine keys since H5-8), from the check file beside the key (or, with no file, from the
  stored secrets), on a blocked, awaiting and restore-interrupted instance too; never an impression of the check value;
- ``POST /backup/panel/jobs`` answers 409 ``backup_instance_key_mismatch`` and starts NO job on a mismatch, after the panel credential
  (a caller without one learns nothing) and not on an instance awaiting a restore (its own 409); the poll, the download and the delete
  of a job, and the panel's restore, are untouched;
- ``POST /system/wake-sync`` answers ``status: instance_key_mismatch`` and runs nothing;
- a user's session is served, ``GET /system/instance`` unchanged; the administrator's Security list holds ``platform.instance_key_check``.

The lesson of H5-5: the state is read at EVERY request. The way back (the developer's question «if the backups stop, how do they
resume?») is pinned on real files: the key comes back, the very next request says ``ok`` and the backup is accepted, nothing stored
between; or the administrator accepts the new key for one start, and the old key is then the mismatch.

Pure: the app of ``backend/app/main.py`` in this process (ASGI), every request's session on a private SQLite file under ``tmp_path``
(the fixtures of ``test_await_restore_mode_api.py`` and ``test_restore_interrupted_api.py``), the data directory and the key in
``tmp_path``/environment, real check files that the product reads; the backup start is stubbed at ``job_views.start_job`` as the panel
backup tests do. No server, no lane database, no network.
"""

from __future__ import annotations

import json
import os
import secrets
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

from backend.app.api.v1.auth import SESSION_COOKIE_NAME
from backend.app.api.v1.system import wake as wake_module
from backend.app.config import API_V1_PREFIX
from backend.app.db.models import User
from backend.app.schemas.hosting_panel import PanelStatusResponse
from backend.app.schemas.sleep_wake import WakeSyncResponse
from backend.app.services.accounts.auth_service import create_jwt_token
from backend.app.services.platform.scheduler import scheduler
from backend.app.services.platform.sleep_wake import idle_monitor
from backend.test_scripts.test_api import test_restore_interrupted_api as ri
from backend.test_scripts.test_api.test_await_restore_mode_api import (
    AWAITING_CODE,
    PANEL_STATUS_KEYS,
    PAST_THE_SWITCHES,
    WAKE_TOKEN_VARIABLE,
    Instance,
    _api_routes,
    _settled_at_once,
    _trap,
    code,
    panel_status,
    send,
    shown,
    signed_in,
)
from backend.test_scripts.test_services.test_instance_key_check import ACCEPT_VARIABLE, KEY_A, KEY_B, expected_value, ikc_name

# The fixtures of the interrupted restore's API tests, reused: the app of main.py and a test's instance.
app = ri.app
instance = ri.instance

MISMATCH_CODE = "backup_instance_key_mismatch"
JOBS_PATH = ri.JOBS_PATH
STATUS_PATH = f"{API_V1_PREFIX}/panel/status"
CHECKS_PATH = f"{API_V1_PREFIX}/security/checks"
WAKE_PATH = f"{API_V1_PREFIX}/system/wake-sync"
#: ID COLLISION (reported to the coordinator): the contract names this check ``platform.instance_key_check``, which ``config_audit.check_instance_key`` already uses
#: (key file unusable / loose modes, in ``CONFIG_CHECKS``, ``checkGuides.json``): two checks cannot share an id in the Security list and the guide map. Until the
#: coordinator decides, the new check is ``platform.instance_key_check``; its i18n keys are the contract's (the ``ok`` text is shared, ``mismatch`` is new).
CHECK_ID = "platform.instance_key_check"
NEW_KEY = "instance_key"


# =============================================================================
# Helpers
# =============================================================================


@pytest_asyncio.fixture
async def keyed(instance: Instance):
    """The instance with the key A configured, no accept variable, no key file variable; no panel's variable but the ones a test sets."""
    for variable in ("LIBREFOLIO_INSTANCE_KEY_FILE", ACCEPT_VARIABLE):
        instance.monkeypatch.delenv(variable, raising=False)
    instance.monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", KEY_A)
    instance.switches()
    return instance


def check_file(target: Instance):
    return target.root / "secrets" / "instance.key.check"


def write_value_of(target: Instance, key: str):
    """The check file as a start of an instance with ``key`` leaves it: its value, ``0600`` in a folder ``0700``."""
    path = check_file(target)
    path.parent.mkdir(mode=0o700, exist_ok=True)
    path.write_text(expected_value(key) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return path


def files_under(target: Instance) -> list[str]:
    return sorted(str(path.relative_to(target.root)) for path in target.root.rglob("*") if path.is_file())


async def restart(target: Instance, key: str, *, accept: bool = False) -> None:
    """A start of the instance with ``key``: the environment says which key (and whether to accept it), then the start step runs on this test's database."""
    target.monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", key)
    if accept:
        target.monkeypatch.setenv(ACCEPT_VARIABLE, "1")
    else:
        target.monkeypatch.delenv(ACCEPT_VARIABLE, raising=False)
    async with AsyncSession(target.engine) as session:
        await ikc_name("check_instance_key_at_start")(session)


def assert_no_check_value(*texts: str) -> None:
    joined = " ".join(texts)
    for key in (KEY_A, KEY_B):
        assert expected_value(key) not in joined, f"the check value of {key[:12]}... reached an answer"
        assert key not in joined, f"the key {key[:12]}... reached an answer"


async def status_body(target: Instance) -> dict:
    response = await panel_status(target)
    assert response.status_code == 200, f"the panel's status answers 200: {shown(response)}"
    assert_no_check_value(response.text)
    return response.json()


async def instance_key(target: Instance) -> str:
    body = await status_body(target)
    assert NEW_KEY in body, f"H5-7: the panel's status holds no {NEW_KEY}: {sorted(body)}"
    return body[NEW_KEY]


async def admin_session(target: Instance) -> dict[str, str]:
    """An active administrator of the private database, and the Cookie header of a session this process mints for it."""
    username = f"h57admin_{uuid4().hex[:12]}"
    async with AsyncSession(target.engine, expire_on_commit=False) as session:
        account = User(username=username, email=f"{username}@example.com", hashed_password="not-a-password-hash", is_superuser=True)
        session.add(account)
        await session.commit()
        with capture_logs():
            token = create_jwt_token(account.id, 1, account.session_version)
    return {"Cookie": f"{SESSION_COOKIE_NAME}={token}"}


def prepare_wake(target: Instance) -> tuple[dict[str, str], list[str]]:
    """The wake-up route with its token and the real ``run_due_jobs``; everything the scheduler reaches past its switches is a trap that records."""
    target.monkeypatch.setattr(wake_module, "run_due_jobs", scheduler.run_due_jobs)
    target.monkeypatch.delenv("LIBREFOLIO_NO_SCHEDULER", raising=False)
    target.monkeypatch.setattr(scheduler, "settle_clock", _settled_at_once, raising=False)
    target.monkeypatch.setattr(idle_monitor, "request_idle_check", lambda *_args, **_kwargs: None, raising=False)
    reached: list[str] = []
    for name in PAST_THE_SWITCHES:
        target.monkeypatch.setattr(scheduler, name, _trap(name, reached), raising=False)
    target.monkeypatch.setattr(scheduler, "scheduler_run_lock", _trap("scheduler_run_lock", reached), raising=False)
    token = secrets.token_hex(32)
    target.monkeypatch.setenv(WAKE_TOKEN_VARIABLE, token)
    return {"Authorization": f"Bearer {token}"}, reached


# =============================================================================
# GET /panel/status
# =============================================================================


def test_the_panel_status_declares_instance_key_required_and_after_the_owners_change():
    """The model: ``instance_key`` is a REQUIRED ``ok``/``mismatch`` choice declared right after ``owner_email_change``; the pinned key set of the panel's status holds nine keys (H5-8 adds ``users_over_limit`` after it)."""
    assert NEW_KEY in PANEL_STATUS_KEYS and len(PANEL_STATUS_KEYS) == 9, f"H5-7, H5-8: the pinned key set of test_await_restore_mode_api.py holds {NEW_KEY} (nine keys): {sorted(PANEL_STATUS_KEYS)}"
    schema = PanelStatusResponse.model_json_schema()
    properties = schema.get("properties", {})
    assert NEW_KEY in properties, f"H5-7: PanelStatusResponse has no {NEW_KEY}: {sorted(PanelStatusResponse.model_fields)}"
    assert set(properties[NEW_KEY].get("enum", [])) == {"ok", "mismatch"}, f"an ok/mismatch choice: {properties[NEW_KEY]}"
    assert NEW_KEY in schema.get("required", []), "required: no default, a panel that reads it never meets an absent state"
    order = list(PanelStatusResponse.model_fields)
    assert order.index(NEW_KEY) == order.index("owner_email_change") + 1, f"declared right after owner_email_change: {order}"
    assert len(order) == 9, f"nine keys: {order}"


def test_the_openapi_says_it_the_start_409_and_the_wake_status(app):
    """OpenAPI: the schema of the status holds ``instance_key`` (enum, required); the start of the panel's backup describes ``backup_instance_key_mismatch`` in its 409; the wake-up's ``status`` documents ``instance_key_mismatch``."""
    document = app.openapi()
    status_schema = document["components"]["schemas"]["PanelStatusResponse"]
    assert NEW_KEY in status_schema["properties"] and NEW_KEY in status_schema.get("required", []), f"H5-7: instance_key in the OpenAPI schema, required: {sorted(status_schema['properties'])}"
    assert set(status_schema["properties"][NEW_KEY].get("enum", [])) == {"ok", "mismatch"}, status_schema["properties"].get(NEW_KEY)
    start = document["paths"][f"{API_V1_PREFIX}/backup/panel/jobs"]["post"]["responses"]
    assert "409" in start and MISMATCH_CODE in start["409"]["description"], f"H5-7: the 409 of the start names {MISMATCH_CODE}: {start.get('409')}"
    assert "instance_key_mismatch" in (WakeSyncResponse.model_json_schema()["properties"]["status"].get("description") or ""), "H5-7: the wake-up's status documents instance_key_mismatch"


@pytest.mark.asyncio
async def test_the_panel_status_says_ok_with_this_keys_check_file_and_holds_nine_keys(keyed):
    """A check file of the key in force: ``instance_key`` is ``ok``, the answer holds exactly the nine keys, never the value."""
    write_value_of(keyed, KEY_A)
    body = await status_body(keyed)
    assert set(body) == PANEL_STATUS_KEYS, f"exactly {sorted(PANEL_STATUS_KEYS)}: {sorted(body)}"
    assert body[NEW_KEY] == "ok", f"the file holds this key's value: {body}"


@pytest.mark.asyncio
async def test_the_panel_status_says_mismatch_with_a_check_file_of_another_key(keyed):
    """A check file written with another key: ``instance_key`` is ``mismatch`` (200: the panel always reads it), never the value."""
    write_value_of(keyed, KEY_B)
    body = await status_body(keyed)
    assert body.get(NEW_KEY) == "mismatch", f"another key's value in the file: {body}"
    assert set(body) == PANEL_STATUS_KEYS, f"the other fields are there as ever: {sorted(body)}"


@pytest.mark.asyncio
async def test_without_a_check_file_and_without_secrets_the_panel_status_says_ok(keyed):
    """A fresh instance: no file, no stored secret: ``ok``; and the read created nothing."""
    before = files_under(keyed)
    assert await instance_key(keyed) == "ok"
    assert files_under(keyed) == before and not (keyed.root / "secrets").exists(), "a status read writes nothing"


@pytest.mark.asyncio
async def test_without_a_check_file_the_panel_status_follows_the_stored_secrets(keyed):
    """No file: only foreign secrets (system and user) say ``mismatch``; one readable one says ``ok`` (R1 through the route)."""
    from backend.app.db.models import PluginSystemSetting  # noqa: PLC0415
    from backend.app.services.plugin_settings.crypto import encrypt_secret, key_id_of, secret_aad, settings_subkey  # noqa: PLC0415

    foreign = bytes([7]) * 32

    async def add(field_key: str, subkey: bytes) -> None:
        blob = encrypt_secret(subkey, secret_aad("asset", "lab", field_key, "system", None), "x")
        async with AsyncSession(keyed.engine) as session:
            session.add(PluginSystemSetting(family="asset", plugin_code="lab", field_key=field_key, secret_ciphertext=blob, key_id=key_id_of(subkey)))
            await session.commit()

    await add("one", foreign)
    assert await instance_key(keyed) == "mismatch", "every stored secret is under another key"
    await add("two", settings_subkey())
    assert await instance_key(keyed) == "ok", "one readable secret: the instance can still read some"


@pytest.mark.asyncio
async def test_the_panel_status_follows_the_file_at_the_very_next_request(keyed):
    """The lesson of H5-5, through the route: one process, the file and the key changed between requests; no answer is stale."""
    write_value_of(keyed, KEY_A)
    answers = [await instance_key(keyed)]
    write_value_of(keyed, KEY_B)
    answers.append(await instance_key(keyed))
    write_value_of(keyed, KEY_A)
    answers.append(await instance_key(keyed))
    keyed.monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", KEY_B)
    answers.append(await instance_key(keyed))
    check_file(keyed).unlink()
    answers.append(await instance_key(keyed))
    assert answers == ["ok", "mismatch", "ok", "mismatch", "ok"], f"each request answers for now (no file and no secret is ok): {answers}"


@pytest.mark.asyncio
async def test_after_the_accept_rewrote_the_file_the_next_request_says_ok(keyed):
    """A wrong file (key B's) and key A: ``mismatch``; a start with the accept variable rewrites it; the next request says ``ok`` with no restart of the app."""
    write_value_of(keyed, KEY_B)
    assert await instance_key(keyed) == "mismatch"
    await restart(keyed, KEY_A, accept=True)
    assert check_file(keyed).read_text(encoding="utf-8").strip() == expected_value(KEY_A), "the accept rewrote the file"
    keyed.monkeypatch.delenv(ACCEPT_VARIABLE, raising=False)
    assert await instance_key(keyed) == "ok", "the very next request: ok, the variable no longer needed"


@pytest.mark.asyncio
@pytest.mark.parametrize("condition", ["blocked", "awaiting", "interrupted"])
async def test_the_panel_status_answers_with_instance_key_on_a_blocked_awaiting_or_interrupted_instance(keyed, condition):
    """The status is allowed in all three states and says ``instance_key`` like the other fields do."""
    write_value_of(keyed, KEY_B)
    if condition == "interrupted":
        ri.interrupt(keyed)
    else:
        keyed.switches(awaiting=condition == "awaiting", blocked=condition == "blocked")
    body = await status_body(keyed)
    assert body.get(NEW_KEY) == "mismatch" and set(body) == PANEL_STATUS_KEYS, f"{condition}: the state is told: {body}"
    assert body["mode"] == ("awaiting_restore" if condition == "awaiting" else "normal"), f"{condition}: the mode as ever: {body['mode']}"


# =============================================================================
# POST /backup/panel/jobs
# =============================================================================


@pytest.mark.asyncio
async def test_a_mismatch_stops_the_panels_backup_start_with_409_and_starts_no_job(keyed):
    """File of another key, token presented: 409 ``backup_instance_key_mismatch`` (a code and a message), no job started, the backup service not reached. Barrier: the same token passes the credential (the poll of an unknown job answers its own 404)."""
    recorder, reached = ri.no_backup(keyed)
    headers = ri.backup_token(keyed)
    write_value_of(keyed, KEY_B)
    barrier = await send(keyed, "GET", f"{JOBS_PATH}/{ri.UNKNOWN_JOB_ID}", headers=headers)
    assert code(barrier) == (404, "backup_job_not_found"), f"Barrier: the token passes the credential: {shown(barrier)}"

    refused = await send(keyed, "POST", JOBS_PATH, headers=headers)

    detail = ri._detail(refused)
    assert code(refused) == (409, MISMATCH_CODE), f"H5-7: a panel backup on a mismatch → 409 {MISMATCH_CODE}: {shown(refused)}"
    assert isinstance(detail, dict) and set(detail) == {"code", "message"} and detail["message"], f"a code and a message: {detail}"
    assert (recorder.calls, reached) == ([], []), f"no backup starts: {recorder.calls}, {reached}"
    assert_no_check_value(refused.text)


@pytest.mark.asyncio
async def test_without_a_mismatch_the_panels_backup_starts_as_before(keyed):
    """Guard: the file of this key, or no file at all: 202, one start, for the panel."""
    recorder, reached = ri.no_backup(keyed)
    headers = ri.backup_token(keyed)
    write_value_of(keyed, KEY_A)
    with_file = await send(keyed, "POST", JOBS_PATH, headers=headers)
    check_file(keyed).unlink()
    without_file = await send(keyed, "POST", JOBS_PATH, headers=headers)
    assert (with_file.status_code, without_file.status_code) == (202, 202), f"both start: {shown(with_file)} / {shown(without_file)}"
    assert len(recorder.calls) == 2 and all(call[0][:1] == ("panel",) for call in recorder.calls) and reached == [], f"two starts, for the panel: {recorder.calls}"


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["no-token-configured", "no-credential", "another-token"])
async def test_on_a_mismatch_the_panels_backup_start_checks_the_credential_first(keyed, case):
    """The credential first: a caller without one gets its 404 / 401, the same answer on a mismatch as on a matching key, and learns nothing; no job either way."""
    recorder, reached = ri.no_backup(keyed)
    headers: dict[str, str] = {}
    if case != "no-token-configured":
        ri.backup_token(keyed)
    if case == "another-token":
        headers = {"Authorization": f"Bearer {secrets.token_hex(32)}"}
    expected = ri.NOT_FOUND_ANSWER if case == "no-token-configured" else (401, ri.BACKUP_UNAUTHORIZED_CODE)
    answers = {}
    for key in (KEY_A, KEY_B):
        write_value_of(keyed, key)
        response = await send(keyed, "POST", JOBS_PATH, headers=headers)
        answers[key] = ri._answer(response) if case == "no-token-configured" else code(response)
    assert answers == {KEY_A: expected, KEY_B: expected}, f"{case}: the credential's answer {expected}, matching key or not, never the 409: {answers}"
    assert (recorder.calls, reached) == ([], []), f"no backup starts without the credential: {recorder.calls}, {reached}"


@pytest.mark.asyncio
async def test_an_instance_awaiting_a_restore_keeps_its_own_409_over_the_mismatch(keyed):
    """Awaiting a restore and a mismatch: the start answers ``backup_awaiting_restore`` (its own 409), not the mismatch's; no job."""
    recorder, reached = ri.no_backup(keyed)
    headers = ri.backup_token(keyed)
    write_value_of(keyed, KEY_B)
    keyed.switches(awaiting=True)
    response = await send(keyed, "POST", JOBS_PATH, headers=headers)
    assert code(response) == (409, "backup_awaiting_restore"), f"awaiting wins: {shown(response)}"
    assert AWAITING_CODE != MISMATCH_CODE and (recorder.calls, reached) == ([], []), f"no job: {recorder.calls}"


@pytest.mark.asyncio
@pytest.mark.parametrize(("method", "suffix"), [("GET", "/{job_id}"), ("GET", "/{job_id}/file"), ("DELETE", "/{job_id}")], ids=["poll", "download", "delete"])
async def test_on_a_mismatch_the_panels_other_backup_routes_answer_on_their_own_terms(keyed, method, suffix):
    """The poll, the download and the delete of a job are not refused by the mismatch (neither 409 nor 423): an unknown job answers its own 404."""
    headers = ri.backup_token(keyed)
    write_value_of(keyed, KEY_B)
    response = await send(keyed, method, JOBS_PATH + suffix.format(job_id=ri.UNKNOWN_JOB_ID), headers=headers)
    assert code(response) == (404, "backup_job_not_found"), f"{method} …/jobs{suffix} stays allowed on a mismatch: {shown(response)}"


def test_the_start_resolves_the_instance_key_check_right_after_the_panel_credential(app):
    """The order of the dependencies is the order of the checks: the start has the dependencies of the poll (the three switches, then the panel credential) and exactly ONE more, after them, that no other panel backup route has."""
    by_endpoint = {context.endpoint.__name__: [item.call for item in context.dependant.dependencies] for context in _api_routes(app) if context.path.startswith(f"{API_V1_PREFIX}/backup/panel/jobs")}
    start, poll, download, delete = (by_endpoint[name] for name in ("start_panel_backup", "get_panel_backup_job", "download_panel_backup", "delete_panel_backup_job"))
    assert poll == download == delete, "Barrier: the other three routes carry the same dependencies"
    assert start[: len(poll)] == poll, f"H5-7: the start begins with the poll's dependencies, the credential last of them: {start}"
    assert len(start) == len(poll) + 1, f"H5-7: and has exactly one more, after the credential: {len(start)} dependencies against {len(poll)}"
    assert start[-1] not in poll, "the extra dependency is the instance key check"


# =============================================================================
# POST /system/wake-sync
# =============================================================================


@pytest.mark.asyncio
async def test_the_wake_up_on_a_mismatch_answers_instance_key_mismatch_and_runs_nothing(keyed):
    """Token and the real ``run_due_jobs``: 200, ``status: instance_key_mismatch``, dates, no job, nothing past the scheduler's switches. Barrier: with this key's file the same wake-up goes past the switches."""
    headers, reached = prepare_wake(keyed)
    write_value_of(keyed, KEY_A)
    barrier = await send(keyed, "POST", WAKE_PATH, headers=headers)
    barrier_body = json.loads(barrier.content)
    assert barrier.status_code == 200 and barrier_body.get("status") != "instance_key_mismatch" and reached != [], f"Barrier: with a matching key the run goes on: {barrier_body}, {reached}"
    reached.clear()
    write_value_of(keyed, KEY_B)

    response = await send(keyed, "POST", WAKE_PATH, headers=headers)

    assert response.status_code == 200, f"the wake-up answers 200: {shown(response)}"
    body = json.loads(response.content)
    assert (body.get("status"), body.get("jobs")) == ("instance_key_mismatch", []), f"H5-7: status instance_key_mismatch, no job: {body}"
    assert body.get("started_at") and body.get("finished_at"), f"the run's dates are there: {body}"
    assert reached == [], f"nothing past the switches: {reached}"
    assert_no_check_value(response.text)


@pytest.mark.asyncio
async def test_the_wake_up_follows_the_file_at_the_next_request(keyed):
    """Mismatch, then the right file, then mismatch again: each wake-up answers for now."""
    headers, reached = prepare_wake(keyed)
    statuses = []
    for key in (KEY_B, KEY_A, KEY_B):
        write_value_of(keyed, key)
        statuses.append(json.loads((await send(keyed, "POST", WAKE_PATH, headers=headers)).content).get("status") == "instance_key_mismatch")
    assert statuses == [True, False, True], f"mismatch, goes on, mismatch: {statuses}"


@pytest.mark.asyncio
@pytest.mark.parametrize("switch", ["awaiting", "interrupted"])
async def test_the_wake_up_keeps_its_other_refusals_over_the_mismatch(keyed, switch):
    """Awaiting a restore, or an interrupted one, wins over the mismatch (the mismatch is checked after them)."""
    headers, reached = prepare_wake(keyed)
    write_value_of(keyed, KEY_B)
    if switch == "interrupted":
        ri.interrupt(keyed)
    else:
        keyed.switches(awaiting=True)
    body = json.loads((await send(keyed, "POST", WAKE_PATH, headers=headers)).content)
    assert body.get("status") == ("restore_interrupted" if switch == "interrupted" else "awaiting_restore"), f"{switch} first: {body}"
    assert reached == [], f"nothing past the switches: {reached}"


# =============================================================================
# The instance keeps serving
# =============================================================================


@pytest.mark.asyncio
async def test_on_a_mismatch_the_instance_keeps_serving_its_users(keyed):
    """A signed-in user reads a data route (200) and the public configuration is unchanged: no new key in it, the same keys as with a matching key."""
    session = await signed_in(keyed)
    write_value_of(keyed, KEY_A)
    matching = await send(keyed, "GET", f"{API_V1_PREFIX}/system/instance")
    write_value_of(keyed, KEY_B)
    served = await send(keyed, "GET", f"{API_V1_PREFIX}/brokers", headers=session)
    me = await send(keyed, "GET", f"{API_V1_PREFIX}/auth/me", headers=session)
    config = await send(keyed, "GET", f"{API_V1_PREFIX}/system/instance")
    assert (served.status_code, me.status_code) == (200, 200), f"a mismatch stops the panel's jobs, never the users: {shown(served)} / {shown(me)}"
    assert config.status_code == 200 and set(config.json()) == set(matching.json()), f"the public configuration is unchanged: {sorted(config.json())} / {sorted(matching.json())}"
    assert not any("instance_key" in key or "key_check" in key for key in config.json()), f"no new key in the public configuration: {sorted(config.json())}"
    assert_no_check_value(config.text)


# =============================================================================
# The administrator's Security list
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(("key", "severity", "i18n"), [(KEY_A, "ok", "instance.checks.instanceKey.ok"), (KEY_B, "error", "instance.checks.instanceKey.mismatch")], ids=["matching", "mismatch"])
async def test_the_security_checks_list_holds_the_instance_key_check(keyed, key, severity, i18n):
    """``GET /security/checks`` as an administrator lists ``platform.instance_key_check`` once: ``ok`` with a matching file, ``error`` with ``instance.checks.instanceKey.mismatch`` and an empty detail on a mismatch; never the value."""
    cookie = await admin_session(keyed)
    write_value_of(keyed, key)
    response = await send(keyed, "GET", CHECKS_PATH, headers=cookie)
    assert response.status_code == 200, f"the administrator's list answers 200: {shown(response)}"
    items = [item for item in response.json()["items"] if item["check_id"] == CHECK_ID]
    assert len(items) == 1, f"H5-7: {CHECK_ID} listed once: {[item['check_id'] for item in response.json()['items']]}"
    assert (items[0]["severity"], items[0]["i18n_key"], items[0]["detail"]) == (severity, i18n, {}), f"{items[0]}"
    assert_no_check_value(response.text)


# =============================================================================
# The way back: «if the backups stop, how do they resume?»
# =============================================================================


@pytest.mark.asyncio
async def test_when_the_key_comes_back_the_backups_resume_with_nothing_stored_between(keyed):
    """Key A starts and writes the check file; a restart with key B is a mismatch (status, backup 409, no job); a restart with key A again, with nothing else touched and no accept variable, says ``ok`` at the very next request and the backup is accepted. Nothing was stored between: no flag, no state file, and the check file is the same bytes it was after the first start."""
    recorder, reached = ri.no_backup(keyed)
    headers = ri.backup_token(keyed)

    await restart(keyed, KEY_A)
    original = check_file(keyed).read_bytes()
    assert original.decode("utf-8").strip() == expected_value(KEY_A), "(1) the start step wrote the check file with key A's value"
    stored = files_under(keyed)
    assert stored == ["secrets/instance.key.check"], f"(1) the check file is all the start stored: {stored}"
    assert await instance_key(keyed) == "ok", "(1) key A: ok"

    await restart(keyed, KEY_B)
    assert check_file(keyed).read_bytes() == original, "(2) a restart with another key does not rewrite the file"
    assert await instance_key(keyed) == "mismatch", "(2) key B: mismatch"
    refused = await send(keyed, "POST", JOBS_PATH, headers=headers)
    assert code(refused) == (409, MISMATCH_CODE) and recorder.calls == [], f"(2) the backup start is refused and starts no job: {shown(refused)}, {recorder.calls}"

    await restart(keyed, KEY_A)
    assert await instance_key(keyed) == "ok", "(3) key A again: the very next status says ok"
    resumed = await send(keyed, "POST", JOBS_PATH, headers=headers)
    assert resumed.status_code == 202 and len(recorder.calls) == 1 and reached == [], f"(3) the backup is accepted and a job is started: {shown(resumed)}, {recorder.calls}"
    assert check_file(keyed).read_bytes() == original, "(3) the check file is unchanged byte for byte"
    assert files_under(keyed) == stored, f"(3) nothing was stored between: {files_under(keyed)}"
    assert ACCEPT_VARIABLE not in os.environ, "(3) no accept variable was needed"


@pytest.mark.asyncio
async def test_accepting_the_new_key_for_one_start_resumes_the_backups_and_makes_the_old_key_the_mismatch(keyed):
    """Key A starts; key B alone is a mismatch; key B with ``LIBREFOLIO_INSTANCE_KEY_ACCEPT=1`` for ONE start rewrites the file (``ok``, backup accepted); the variable removed and another start with key B stays ``ok`` and silent (the file holds B's value); then key A again is a mismatch: the accept was a real change."""
    recorder, _reached = ri.no_backup(keyed)
    headers = ri.backup_token(keyed)

    await restart(keyed, KEY_A)
    stored = files_under(keyed)
    await restart(keyed, KEY_B)
    assert await instance_key(keyed) == "mismatch", "key B without accept: mismatch"
    assert code(await send(keyed, "POST", JOBS_PATH, headers=headers)) == (409, MISMATCH_CODE) and recorder.calls == [], "…and the backup is refused"

    await restart(keyed, KEY_B, accept=True)
    assert check_file(keyed).read_text(encoding="utf-8").strip() == expected_value(KEY_B), "the accept rewrote the file with B's value"
    assert await instance_key(keyed) == "ok", "after the accept: ok"
    accepted = await send(keyed, "POST", JOBS_PATH, headers=headers)
    assert accepted.status_code == 202 and len(recorder.calls) == 1, f"the backup is accepted: {shown(accepted)}, {recorder.calls}"

    rewritten = check_file(keyed).read_bytes()
    with capture_logs() as events:
        await restart(keyed, KEY_B)
    assert [event for event in events if event.get("log_level") in ("warning", "error", "critical")] == [], f"the variable removed, the start is silent: {events}"
    assert check_file(keyed).read_bytes() == rewritten and await instance_key(keyed) == "ok", "another start with key B stays ok, the file as it was"

    await restart(keyed, KEY_A)
    assert await instance_key(keyed) == "mismatch", "key A again: the accept was a real change, A is the wrong key now"
    refused = await send(keyed, "POST", JOBS_PATH, headers=headers)
    assert code(refused) == (409, MISMATCH_CODE) and len(recorder.calls) == 1, f"the backup is refused again, no new job: {shown(refused)}, {recorder.calls}"
    assert check_file(keyed).read_bytes() == rewritten, "key A without accept rewrote nothing"
    assert files_under(keyed) == stored, f"nothing but the check file was ever stored: {files_under(keyed)}"
