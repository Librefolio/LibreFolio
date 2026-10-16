"""
Restoring a backup, the confirmation through the API (workstream B, lot B3, contract §5, §6 and §11): the four new routes
of ``/api/v1/backup/restore``, and what they change in the two of lot B2b that drop and prune a checked copy.

Written before the code (red until lot B3 lands): ``apply.py`` and ``restart.py`` do not exist yet. Every name of lot B3
is imported inside the test that needs it (``product``), so the file collects, and each test fails on its own. The
``instance_blocked`` cases (§11, P7) were written red the same way, before P7.

Under test: ``backend/app/api/v1/backup/restore.py`` (the routes), ``restore_jobs.confirm_check`` / ``remove_check`` /
``prune``, ``instance_backup/apply.py`` as the routes reach it, ``instance_backup/restart.py`` (``send_signal``) and
``RestoreStatus`` of ``backend/app/schemas/backup.py``.

(a) ``POST /backup/restore/stage/{stage_id}/confirm``: 202 ``RestoreStatus`` ``pending``. On disk,
    ``.restore/restore.json`` (0600): ``pending``, the stage, the data directory resolved, ``confirmed_by`` the
    administrator's username, ``confirmed_at`` the time of the request, ``backup_created_at``, ``backup_app_version`` and
    ``action`` from the check's report, nothing of a swap yet. The copy and its check are kept as they were; nothing else
    of the data directory is touched. ``GET /status`` answers the same. A second confirmation, of this copy or another,
    while a restore is ACTIVE (pending, applying, applied, rolling back): 409 ``restore_already_pending``, the state
    unchanged.
(b) The refusals of a confirmation, each code of §6, nothing written: 404 ``restore_stage_not_found`` (no such check;
    its copy's database or its report gone), 409 ``restore_stage_running``, 409 ``restore_not_restorable`` (a report
    with a blocker; a failed check), 410 ``restore_stage_expired``, 409 ``restore_stage_outdated`` (the report's head is
    not this LibreFolio's; ``apply.alembic_head_revision`` moved; not judged when it is ``None``); never a path in the
    answer. Once the check ended, ``.restore`` a link or a file: 500 ``restore_folder_unusable`` (``confirm_check`` checks
    it first: it writes there); a link in place of ``checks/`` or ``stage/``: the check or its copy is not found, 404
    ``restore_stage_not_found``. Nothing written through any of them, nor anywhere in the data directory.
(c) ``GET /backup/restore/status``: ``none`` without a restore, and nothing created to say so; each phase on disk as
    its state (applying, applied and rolling back are ``in_progress``), its fields as recorded; a pending restore says
    why a start left it waiting, for each of the four reasons (§11, P7: ``instance_blocked``, on an instance not blocked
    itself, since a blocked one answers no restore route); a ``restore.json`` that is a link is never followed, one that
    cannot be read is ``none``.
(d) ``DELETE /backup/restore/pending``: 204, the state removed, the copy kept, which can be confirmed again. Without a
    state file, 404 ``restore_not_pending`` and nothing created, not even ``.restore/apply.lock`` (the lock is taken only
    once a state file is found); a restore being applied or finished, 404 too, its state unchanged.
(e) ``POST /backup/restore/restart``: 202 ``RestoreStatus`` (pending); after the answer is sent, a SIGTERM to the
    server's process (``restart.server_pid()``), through ``restart.send_signal`` and nothing else; the state unchanged.
    409 ``restore_not_pending`` otherwise, and no signal.
(f) The copy of an ACTIVE restore: ``DELETE /backup/restore/stage/{id}`` is 409 ``restore_pending`` and keeps it;
    another check is dropped as before, and so is the copy of a finished restore. ``prune``, however old everything
    looks, keeps the ACTIVE restore's check and copy, the command line's copy that no check records included; a
    finished restore's old copy is pruned as before.
(g) Administrators only: a regular user gets 403 from each new route, and nothing changes, no signal. None of the four
    is allowed on a blocked instance. OpenAPI: the four operations carry ``Backup & Export``, their success and model,
    and document their refusals with their codes; the drop documents ``restore_pending``; ``RestoreStatus.waiting``
    lists exactly the four reasons, ``instance_blocked`` included (§11).
(h) ``upload_limit_mb`` (§6), in every ``RestoreStatus`` answer, ``none`` included: the largest archive the upload
    accepts now, in MB, read by ``backup_max_upload_mb()`` when the answer is built: 0 unset and self-hosted, 500 unset
    and managed, the variable's value when set (over the profile), ``null`` when it cannot be read, with one error
    logged naming the variable, as the upload's 503 logs it. The same in the answers of confirm, status and restart; a
    change of the variable between two answers shows in the second. In the ``RestoreStatus`` schema.

Pure, as ``test_backup_restore.py`` (lot B2b), whose fixtures and helpers are imported: an app of each test holds
``backup_router``, ``get_current_user`` overridden; the data directory of the routes under ``tmp_path`` (``apply``'s
``get_data_dir`` as well), the process configured with another folder that must stay absent; ``threading`` as
``restore_jobs`` sees it replaced. Real archives from the module fixtures of ``test_backup_staging.py``. No signal is
ever sent: ``restart.send_signal`` records in every test, and ``os.kill`` as ``restart`` sees it records too (it must
stay unused). States of a restore that only a start can reach (applying, applied, rolling back, committed, rolled back)
are written as ``apply.RestoreState`` would write them. ``prune`` is called with a ``now`` far ahead: no file is aged,
no clock waited for.
"""

from __future__ import annotations

import importlib
import json
import os
import signal
import stat
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from structlog.testing import capture_logs

from backend.app.api.v1.backup import restore
from backend.app.api.v1.instance_block import ALLOWED_WHEN_BLOCKED
from backend.app.services.platform.instance_backup import restore_jobs
from backend.app.services.platform.instance_backup import staging as staging_service
from backend.app.services.platform.instance_backup.paths import check_state_path, restore_dir, stage_dir
from backend.app.services.platform.instance_backup.staging import STAGE_LIFETIME, StagingReport, read_report
from backend.test_scripts.test_api import test_backup_restore as api
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utils import print_section, print_success

# The fixtures of lot B2b's tests, re-exported: ``instance`` (autouse: the data directory of the routes, the fake threads,
# the configured data directory that must stay absent) and the real databases and archives.
instance = api.instance
databases = api.databases
head_archive = api.head_archive

CONFIRM = f"{api.STAGE}/{{stage_id}}/confirm"
STATUS = f"{api.API}/status"
PENDING = f"{api.API}/pending"
RESTART = f"{api.API}/restart"
#: The administrator who confirms: ``confirmed_by`` must be its username, not a constant.
B3_ADMIN = SimpleNamespace(id=7, username="b3-admin", is_superuser=True)
#: Every field of ``RestoreStatus`` (``extra="forbid"``): an answer has these and no other.
STATUS_FIELDS = {"state", "stage_id", "confirmed_at", "confirmed_by", "backup_created_at", "backup_app_version", "action", "finished_at", "reason", "waiting", "upload_limit_mb"}
ACTIVE = ["pending", "applying", "applied", "rolling_back"]
TERMINAL = ["committed", "rolled_back"]
#: The state ``GET /status`` answers for each phase on disk.
STATE_OF = {"pending": "pending", "applying": "in_progress", "applied": "in_progress", "rolling_back": "in_progress", "committed": "committed", "rolled_back": "rolled_back"}
#: The fields a hand-written state carries for its phase, as a start leaves them.
CONFIRMED_AT = datetime(2026, 10, 15, 22, 0, tzinfo=UTC)
BACKUP_CREATED_AT = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)
FINISHED_AT = datetime(2026, 10, 15, 23, 0, tzinfo=UTC)
#: Everything older than a check's lifetime, as ``prune`` judges it with this ``now``.
FAR_AHEAD = timedelta(days=30)


# =============================================================================
# Lot B3's names, imported when a test needs them
# =============================================================================


def product(name: str) -> ModuleType:
    """A module of the application, imported when a test needs it: this file collects before lot B3's modules exist,
    and each test that needs one fails on its own until it does."""
    return importlib.import_module(f"backend.app.{name}")


def apply_module() -> ModuleType:
    return product("services.platform.instance_backup.apply")


def restart_module() -> ModuleType:
    return product("services.platform.instance_backup.restart")


def state_path(root: Path) -> Path:
    """``.restore/restore.json``, as ``paths.restore_state_path`` gives it (lot B3)."""
    return product("services.platform.instance_backup.paths").restore_state_path(root)


def optional(module: str) -> ModuleType | None:
    """The module, or ``None`` while lot B3 has not written it."""
    try:
        return product(module)
    except ModuleNotFoundError:
        return None


class Answered:
    """The app of a test, wrapped: ``done`` turns true once the last byte of the answer has been sent."""

    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self.done = False

    async def __call__(self, scope, receive, send) -> None:
        async def sending(message) -> None:
            await send(message)
            if message.get("type") == "http.response.body" and not message.get("more_body", False):
                self.done = True

        await self.app(scope, receive, sending)


class OsWithoutKill:
    """``os`` as ``restart`` sees it, ``kill`` recorded instead of sent: a restart goes through ``send_signal``."""

    def __init__(self, calls: list) -> None:
        self._calls = calls

    def __getattr__(self, name: str) -> Any:
        return getattr(os, name)

    def kill(self, pid: int, sig: int) -> None:
        self._calls.append((pid, sig))


@dataclass
class Signals:
    """The signals of a test: those ``restart.send_signal`` was asked to send, as (pid, signal, whether the answer had
    been sent then), and those tried with ``os.kill`` around it (there must be none)."""

    sent: list[tuple[int, int, bool | None]] = field(default_factory=list)
    around: list[tuple[int, int]] = field(default_factory=list)
    answered: Answered | None = None

    def send(self, pid: int, sig: int) -> None:
        self.sent.append((pid, sig, self.answered.done if self.answered is not None else None))


@pytest.fixture(autouse=True)
def signals(instance, monkeypatch) -> Signals:
    """Every test: ``apply`` uses the data directory of the routes, and no signal can reach this process."""
    recorded = Signals()
    apply = optional("services.platform.instance_backup.apply")
    if apply is not None:
        monkeypatch.setattr(apply, "get_data_dir", lambda: instance.root, raising=False)
    restart = optional("services.platform.instance_backup.restart")
    if restart is not None:
        monkeypatch.setattr(restart, "send_signal", recorded.send, raising=False)
        monkeypatch.setattr(restart, "os", OsWithoutKill(recorded.around), raising=False)
    return recorded


# =============================================================================
# Requests and states
# =============================================================================


async def confirm(stage_id: str, *, user: SimpleNamespace = B3_ADMIN) -> httpx.Response:
    return await api.call("POST", CONFIRM.format(stage_id=stage_id), user=user)


async def restore_status(*, user: SimpleNamespace = B3_ADMIN) -> httpx.Response:
    return await api.call("GET", STATUS, user=user)


async def cancel(*, user: SimpleNamespace = B3_ADMIN) -> httpx.Response:
    return await api.call("DELETE", PENDING, user=user)


async def restart(*, user: SimpleNamespace = B3_ADMIN, answered: Signals | None = None) -> httpx.Response:
    """``POST /restart``; with ``answered``, the app is wrapped so the signals it records say whether the answer had
    been sent."""
    app = Answered(api.restore_app(user))
    if answered is not None:
        answered.answered = app
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://in-process") as client:
        return await client.post(RESTART)


async def checked(archive) -> str:
    """``archive`` uploaded and checked through the routes, restorable: its stage id."""
    state = await api.ended(archive.path.read_bytes())
    assert state["status"] == "done" and state["report"]["restorable"], f"precondition: a restorable check: {state}"
    return state["stage_id"]


async def confirmed(archive) -> str:
    stage_id = await checked(archive)
    response = await confirm(stage_id)
    assert response.status_code == 202, f"precondition: the restore is confirmed: {api.shown(response)}"
    return stage_id


def write_state(root: Path, status: str, stage_id: str) -> bytes:
    """A restore in phase ``status`` for the stage ``stage_id``, as a start leaves it on disk: its bytes."""
    apply = apply_module()
    fields: dict[str, Any] = {}
    if status in ("applying", "applied", "rolling_back"):
        fields["swap"] = [apply.SwapEntry(name=name, live=True, staged=True) for name in ("sqlite", "custom-uploads", "broker_reports", "scenario_catalog")]
        fields["boot"] = apply.Boot(pid=999_999, started=1_760_000_000.0)
    if status in ("applied", "committed"):
        fields["applied_at"] = FINISHED_AT - timedelta(minutes=5)
    if status == "rolling_back":
        fields["reason"] = "first_start_failed"
    if status in TERMINAL:
        fields["finished_at"] = FINISHED_AT
    if status == "rolled_back":
        fields["reason"] = "first_start_failed"
    if status == "committed":
        fields["session_version"] = int(FINISHED_AT.timestamp() * 1000)
    state = apply.RestoreState(
        status=status,
        stage_id=stage_id,
        data_dir=str(root.resolve()),
        confirmed_at=CONFIRMED_AT,
        confirmed_by="b3-admin",
        backup_created_at=BACKUP_CREATED_AT,
        backup_app_version="v1.2.0",
        action="upgrade",
        **fields,
    )
    path = state_path(root)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(state.model_dump_json(), encoding="utf-8")
    path.chmod(0o600)
    return path.read_bytes()


def rewrite_report(root: Path, stage_id: str, **changes: Any) -> None:
    """The report of a check, some of its fields changed, written back where the check left it."""
    path = stage_dir(root, stage_id) / "report.json"
    report: StagingReport = read_report(root, stage_id).model_copy(update=changes)
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")


def no_path_in(response: httpx.Response, root: Path) -> None:
    for form in (str(root), str(root.resolve()), ".restore"):
        assert form not in response.text, f"no path in the answer: {response.text}"


# =============================================================================
# (a) A confirmation
# =============================================================================


@pytest.mark.asyncio
async def test_a_confirmed_restore_waits_for_the_next_start_with_its_state_on_disk(instance, head_archive):
    print_section("POST /backup/restore/stage/{id}/confirm")
    root = instance.root
    stage_id = await checked(head_archive)
    report = read_report(root, stage_id)
    copy_before = api.tree(stage_dir(root, stage_id))
    started = datetime.now(UTC)
    response = await confirm(stage_id)
    ended = datetime.now(UTC)
    assert response.status_code == 202, f"a checked, restorable copy is confirmed: {api.shown(response)}"
    body = response.json()
    assert set(body) == STATUS_FIELDS, f"a RestoreStatus, nothing more: {sorted(body)}"
    assert (body["state"], body["stage_id"], body["confirmed_by"], body["action"]) == ("pending", stage_id, B3_ADMIN.username, report.action), f"pending, confirmed by the administrator who asked: {body}"
    assert (api.moment(body["backup_created_at"]), body["backup_app_version"]) == (report.backup.created_at, report.backup.app_version), f"the backup, as the report says it: {body}"
    assert (body["finished_at"], body["reason"], body["waiting"]) == (None, None, None), f"nothing of a start yet: {body}"
    path = state_path(root)
    assert path == restore_dir(root) / "restore.json", f"the state of the restore is .restore/restore.json: {path}"
    if os.name != "nt":
        assert stat.S_IMODE(path.lstat().st_mode) == 0o600, f"the state is readable by its owner only: {oct(stat.S_IMODE(path.lstat().st_mode))}"
    state = json.loads(path.read_text(encoding="utf-8"))
    expected = {"format": 1, "status": "pending", "stage_id": stage_id, "data_dir": str(root.resolve()), "confirmed_by": B3_ADMIN.username, "backup_app_version": report.backup.app_version, "action": report.action}
    assert {key: state.get(key) for key in expected} == expected, f"the state written: {state}"
    nothing_yet = {key: state.get(key) for key in ("swap", "boot", "applied_at", "finished_at", "reason", "waiting", "session_version")}
    assert nothing_yet == {"swap": [], "boot": None, "applied_at": None, "finished_at": None, "reason": None, "waiting": None, "session_version": None}, f"nothing of a start yet: {nothing_yet}"
    assert api.moment(state["backup_created_at"]) == report.backup.created_at, f"backup_created_at from the report: {state['backup_created_at']}"
    assert started <= api.moment(state["confirmed_at"]) <= ended and api.moment(body["confirmed_at"]) == api.moment(state["confirmed_at"]), f"confirmed now: {state['confirmed_at']}"
    assert api.tree(stage_dir(root, stage_id)) == copy_before and check_state_path(root, stage_id).is_file(), "the copy and its check are kept as they were"
    status = await restore_status()
    assert (status.status_code, status.json()) == (200, body), f"GET /status says the same: {api.shown(status)}"
    print_success(f"202 pending, restore.json 0600, confirmed by {B3_ADMIN.username}")


@pytest.mark.asyncio
async def test_a_second_confirmation_is_refused_while_a_restore_is_pending(instance, head_archive):
    """(a) The same copy again, or another one: 409 ``restore_already_pending``, the state as it was."""
    root = instance.root
    first = await confirmed(head_archive)
    before = state_path(root).read_bytes()
    second = await checked(head_archive)
    answers = {name: api.code(await confirm(stage_id)) for name, stage_id in (("the same copy", first), ("another copy", second))}
    assert answers == dict.fromkeys(answers, (409, "restore_already_pending")), f"one restore at a time: {answers}"
    assert state_path(root).read_bytes() == before, "the pending restore is unchanged"
    print_success("409 restore_already_pending, twice")


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ACTIVE[1:])
async def test_no_confirmation_while_a_restore_is_being_applied(instance, head_archive, phase):
    """(a) A restore being applied (or undone) is ACTIVE too: no other may be confirmed meanwhile."""
    root = instance.root
    applying = await checked(head_archive)
    before = write_state(root, phase, applying)
    other = await checked(head_archive)
    response = await confirm(other)
    assert api.code(response) == (409, "restore_already_pending"), f"{phase}: 409 restore_already_pending: {api.shown(response)}"
    assert state_path(root).read_bytes() == before, f"{phase}: the restore's state is unchanged"
    print_success(f"{phase}: 409 restore_already_pending")


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", TERMINAL)
async def test_a_finished_restore_does_not_stop_the_next_confirmation(instance, head_archive, phase):
    """(a) A committed or rolled back restore is over: a new one can be confirmed, its state replacing the old."""
    root = instance.root
    write_state(root, phase, await checked(head_archive))
    stage_id = await checked(head_archive)
    response = await confirm(stage_id)
    assert response.status_code == 202, f"after a {phase} restore, a new one is confirmed: {api.shown(response)}"
    state = json.loads(state_path(root).read_text(encoding="utf-8"))
    assert (state["status"], state["stage_id"]) == ("pending", stage_id), f"the new restore's state: {state}"
    print_success(f"{phase}, then 202 pending")


# =============================================================================
# (b) The refusals of a confirmation
# =============================================================================


@dataclass
class Setting:
    """What a refusal's case may need to prepare its stage."""

    root: Path
    instance: Any
    archive: Any
    databases: Any
    tmp_path: Path
    monkeypatch: pytest.MonkeyPatch


async def no_such_check(s: Setting) -> str:
    return api.UNKNOWN_ID


async def copy_database_gone(s: Setting) -> str:
    stage_id = await checked(s.archive)
    (stage_dir(s.root, stage_id) / "data" / "sqlite" / "app.db").unlink()
    return stage_id


async def copy_folder_a_link(s: Setting) -> str:
    """A folder of the copy replaced by a link: the copy is not one a restore may move into place."""
    stage_id = await checked(s.archive)
    folder = stage_dir(s.root, stage_id) / "data" / "custom-uploads"
    elsewhere = s.tmp_path / "elsewhere-uploads"
    folder.rename(elsewhere)
    folder.symlink_to(elsewhere, target_is_directory=True)
    return stage_id


async def report_gone(s: Setting) -> str:
    stage_id = await checked(s.archive)
    (stage_dir(s.root, stage_id) / "report.json").unlink()
    return stage_id


async def check_running(s: Setting) -> str:
    s.instance.threads.hold = True
    return (await api.started(s.archive.path.read_bytes()))["stage_id"]


async def blocked_report(s: Setting) -> str:
    source = s.tmp_path / "source"
    archive = cases.build_into(cases.make_data_dir(source / "data", s.databases.head, accounts=cases.WITHOUT_ADMINISTRATOR), source / "work")
    state = await api.ended(archive.path.read_bytes())
    assert state["status"] == "done" and state["report"]["blockers"] == ["no_administrator"], f"precondition: a check whose report has a blocker: {state}"
    return state["stage_id"]


async def failed_check(s: Setting) -> str:
    state = await api.ended(b"these are not the bytes of a backup")
    assert (state["status"], state["error_code"]) == ("failed", "not_a_backup"), f"precondition: a failed check: {state}"
    return state["stage_id"]


async def expired(s: Setting) -> str:
    stage_id = await checked(s.archive)
    now = datetime.now(UTC)
    rewrite_report(s.root, stage_id, staged_at=now - STAGE_LIFETIME - timedelta(minutes=1), expires_at=now - timedelta(minutes=1))
    return stage_id


async def checked_before_an_update(s: Setting) -> str:
    """The report says another head than this LibreFolio's: it was checked before an update."""
    stage_id = await checked(s.archive)
    rewrite_report(s.root, stage_id, head_revision=cases.OLDER)
    return stage_id


async def head_moved(s: Setting) -> str:
    """This LibreFolio's head, as ``apply`` reads it, is no longer the report's."""
    stage_id = await checked(s.archive)
    s.monkeypatch.setattr(apply_module(), "alembic_head_revision", lambda: "999_from_an_update")
    return stage_id


REFUSALS = [
    pytest.param(no_such_check, 404, "restore_stage_not_found", id="no-such-check"),
    pytest.param(copy_database_gone, 404, "restore_stage_not_found", id="copy-database-gone"),
    pytest.param(copy_folder_a_link, 404, "restore_stage_not_found", id="copy-folder-a-link", marks=pytest.mark.skipif(os.name == "nt", reason="symbolic links need a privilege on Windows")),
    pytest.param(report_gone, 404, "restore_stage_not_found", id="report-gone"),
    pytest.param(check_running, 409, "restore_stage_running", id="check-running"),
    pytest.param(blocked_report, 409, "restore_not_restorable", id="report-with-a-blocker"),
    pytest.param(failed_check, 409, "restore_not_restorable", id="failed-check"),
    pytest.param(expired, 410, "restore_stage_expired", id="expired"),
    pytest.param(checked_before_an_update, 409, "restore_stage_outdated", id="report-of-another-head"),
    pytest.param(head_moved, 409, "restore_stage_outdated", id="head-moved"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("prepare", "status_code", "error"), REFUSALS)
async def test_a_confirmation_that_cannot_be_made_is_refused_with_its_code(instance, head_archive, databases, tmp_path, monkeypatch, prepare, status_code, error):
    """(b) Each refusal of §6, with its status and code; no restore written, the copy as it was, no path said."""
    root = instance.root
    stage_id = await prepare(Setting(root, instance, head_archive, databases, tmp_path, monkeypatch))
    copy_before = api.tree(stage_dir(root, stage_id)) if stage_dir(root, stage_id).is_dir() else None
    response = await confirm(stage_id)
    assert api.code(response) == (status_code, error), f"{status_code} {error} expected: {api.shown(response)}"
    assert not state_path(root).exists(), f"{error}: no restore written: {api.files_in(restore_dir(root))}"
    if copy_before is not None:
        assert api.tree(stage_dir(root, stage_id)) == copy_before, f"{error}: the copy is left as it was"
    no_path_in(response, root)
    instance.threads.run_held()
    print_success(f"{status_code} {error}")


@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="symbolic links need a privilege on Windows")
async def test_a_state_file_that_is_a_link_is_replaced_never_written_through(instance, head_archive, tmp_path):
    """(a) The state is written beside, then renamed into place: a ``restore.json`` that is a link (a finished restore's
    state is not ACTIVE, and a link is never read) is replaced by the new state, its target left as it was."""
    root = instance.root
    stage_id = await checked(head_archive)
    elsewhere = tmp_path / "elsewhere.json"
    elsewhere.write_text("a file a link points to", encoding="utf-8")
    state_path(root).symlink_to(elsewhere)
    response = await confirm(stage_id)
    assert response.status_code == 202, f"confirmed: {api.shown(response)}"
    assert not state_path(root).is_symlink() and json.loads(state_path(root).read_text(encoding="utf-8"))["stage_id"] == stage_id, "the link is replaced by the state"
    assert elsewhere.read_text(encoding="utf-8") == "a file a link points to", "nothing written through the link"
    print_success("restore.json a link: replaced, target untouched")


@pytest.mark.asyncio
async def test_a_head_that_cannot_be_read_does_not_refuse_a_confirmation(instance, head_archive, monkeypatch):
    """(b) ``restore_stage_outdated`` is judged only when ``apply.alembic_head_revision`` gives a revision."""
    stage_id = await checked(head_archive)
    monkeypatch.setattr(apply_module(), "alembic_head_revision", lambda: None)
    response = await confirm(stage_id)
    assert response.status_code == 202, f"no head to compare with: confirmed: {api.shown(response)}"
    print_success("head unknown → 202")


#: A folder of the restore replaced once the check ended, and the answer of a confirmation: ``.restore`` is where it
#: writes, checked first (500); behind ``checks/`` or ``stage/``, the check or its copy is simply not found (404).
NOT_PLAIN = [
    pytest.param(".restore", "link", 500, "restore_folder_unusable", id="restore-a-link"),
    pytest.param(".restore", "file", 500, "restore_folder_unusable", id="restore-a-file"),
    pytest.param("checks", "link", 404, "restore_stage_not_found", id="checks-a-link"),
    pytest.param("stage", "link", 404, "restore_stage_not_found", id="stage-a-link"),
]


@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="symbolic links need a privilege on Windows")
@pytest.mark.parametrize(("name", "replaced_by", "status_code", "error"), NOT_PLAIN)
async def test_a_confirmation_never_writes_through_a_restore_folder_that_is_not_a_plain_folder(instance, head_archive, tmp_path, name, replaced_by, status_code, error):
    """(b) The folder moved aside (behind a link in its place, or a file in place of ``.restore``): refused with its code;
    nothing written where the folder went, nor anywhere in the data directory (no state, no lock)."""
    root = instance.root
    stage_id = await checked(head_archive)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    if replaced_by == "link":
        moved = api.moved_behind_a_link(root, name, elsewhere)
    else:
        moved = elsewhere / "restore"
        restore_dir(root).rename(moved)
        restore_dir(root).write_bytes(b"a file where the restore's folder should be")
    before = (api.tree(moved), api.tree(root))
    response = await confirm(stage_id)
    assert api.code(response) == (status_code, error), f"{name} a {replaced_by}: {status_code} {error}: {api.shown(response)}"
    after = (api.tree(moved), api.tree(root))
    assert after == before, f"{name} a {replaced_by}: nothing written: {cases.changed(before[0], after[0]) + cases.changed(before[1], after[1])}"
    no_path_in(response, root)
    print_success(f"{name} a {replaced_by}: {status_code} {error}")


# =============================================================================
# (c) GET /status
# =============================================================================


@pytest.mark.asyncio
async def test_without_a_restore_the_status_is_none_and_nothing_is_created(instance):
    print_section("GET /backup/restore/status")
    response = await restore_status()
    assert response.status_code == 200, api.shown(response)
    assert response.json() == {**dict.fromkeys(STATUS_FIELDS), "state": "none", "upload_limit_mb": 0}, f"none, the upload limit of a self-hosted instance (0), every other field null: {response.json()}"
    assert not restore_dir(instance.root).exists(), "a status read creates nothing, not even .restore"
    print_success("none, nothing created")


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ACTIVE + TERMINAL)
async def test_the_status_of_each_phase_is_what_its_state_records(instance, phase):
    """(c) Applying, applied and rolling back are ``in_progress``; each field as recorded."""
    write_state(instance.root, phase, api.UNKNOWN_ID)
    state = json.loads(state_path(instance.root).read_text(encoding="utf-8"))
    response = await restore_status()
    assert response.status_code == 200, api.shown(response)
    body = response.json()
    assert body["state"] == STATE_OF[phase], f"{phase} reads as {STATE_OF[phase]}: {body}"
    for key in ("stage_id", "confirmed_by", "backup_app_version", "action", "reason", "waiting"):
        assert body[key] == state.get(key), f"{phase}: {key} as recorded: {body[key]!r}, {state.get(key)!r}"
    for key in ("confirmed_at", "backup_created_at", "finished_at"):
        assert (body[key] and api.moment(body[key])) == (state.get(key) and api.moment(state[key])), f"{phase}: {key} as recorded"
    print_success(f"{phase} → {body['state']}")


#: Why a start left a restore pending (contract §2; §10: another server process serves the data directory; §11, P7: the
#: hosting provider blocked the instance).
WAIT_REASONS = ["backup_running", "other_data_directory", "server_running", "instance_blocked"]


@pytest.mark.asyncio
@pytest.mark.parametrize("waiting", WAIT_REASONS)
async def test_a_restore_waiting_says_why(instance, waiting):
    """(c) A pending restore a start could not apply says why: ``waiting``. ``instance_blocked`` (§11) too, read here on
    an instance that is not blocked itself: a blocked one answers none of the restore routes. The reason is written in
    the state file as a start writes it, whatever the models of this LibreFolio accept: the answer is under test."""
    write_state(instance.root, "pending", api.UNKNOWN_ID)
    path = state_path(instance.root)
    record = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps({**record, "waiting": waiting}), encoding="utf-8")
    response = await restore_status()
    assert response.status_code == 200, f"{waiting}: the status answers: {api.shown(response)}"
    body = response.json()
    assert (body["state"], body["waiting"]) == ("pending", waiting), f"pending, waiting {waiting}: {body}"
    print_success(f"pending, waiting {waiting}")


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["a-link", "unreadable"])
async def test_a_state_file_that_is_a_link_or_unreadable_reads_as_no_restore(instance, tmp_path, case):
    """(c) A ``restore.json`` that is a link is never followed, even to a valid state; one that cannot be read is no
    restore either."""
    root = instance.root
    if case == "a-link":
        valid = write_state(root, "pending", api.UNKNOWN_ID)
        elsewhere = tmp_path / "elsewhere.json"
        elsewhere.write_bytes(valid)
        state_path(root).unlink()
        state_path(root).symlink_to(elsewhere)
    else:
        restore_dir(root).mkdir(mode=0o700)
        state_path(root).write_text("{not a state", encoding="utf-8")
    body = (await restore_status()).json()
    assert body["state"] == "none", f"{case}: no restore: {body}"
    print_success(f"{case}: none")


def broken_state(root: Path, case: str) -> None:
    """A state file as a start writes it, then one of its values changed into one no restore can hold (§10)."""
    write_state(root, "applying", api.UNKNOWN_ID)
    path = state_path(root)
    record = json.loads(path.read_text(encoding="utf-8"))
    if case == "stage-id-a-path":
        record["stage_id"] = "../../" + "0" * 26
    elif case == "stage-id-uppercase":
        record["stage_id"] = api.UNKNOWN_ID.upper()
    elif case == "stage-id-31-digits":
        record["stage_id"] = api.UNKNOWN_ID[:31]
    elif case == "stage-id-trailing-newline":
        # ``$`` of Python's re matches before a final line feed; the pattern must not.
        record["stage_id"] = api.UNKNOWN_ID + "\n"
    elif case == "swap-entry-secrets":
        record["swap"][0]["name"] = "secrets"
    else:
        record["swap"][0]["name"] = "../sqlite"
    path.write_text(json.dumps(record), encoding="utf-8")


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["stage-id-a-path", "stage-id-uppercase", "stage-id-31-digits", "stage-id-trailing-newline", "swap-entry-secrets", "swap-entry-a-path"])
async def test_a_state_no_restore_can_hold_reads_as_no_restore(instance, case):
    """(c) §10, a strict state: its ``stage_id`` 32 lowercase hexadecimal digits, each swap entry one of the swapped
    folders. A state file that breaks either is unreadable: no restore, an error logged, and nothing it names is ever
    followed."""
    root = instance.root
    broken_state(root, case)
    before = api.tree(root)
    with capture_logs() as events:
        response = await restore_status()
    assert (response.status_code, response.json()["state"]) == (200, "none"), f"{case}: no restore: {api.shown(response)}"
    errors = [event for event in events if event.get("log_level") == "error"]
    assert errors, f"{case}: the unreadable state is logged as an error: {events}"
    assert api.tree(root) == before, f"{case}: nothing created or changed: {cases.changed(before, api.tree(root))}"
    print_success(f"{case}: none, logged")


# =============================================================================
# (d) DELETE /pending
# =============================================================================


@pytest.mark.asyncio
async def test_a_pending_restore_is_cancelled_and_its_copy_kept_for_another_confirmation(instance, head_archive):
    print_section("DELETE /backup/restore/pending")
    root = instance.root
    stage_id = await confirmed(head_archive)
    copy_before = api.tree(stage_dir(root, stage_id))
    response = await cancel()
    assert (response.status_code, response.content) == (204, b""), f"cancelled: {api.shown(response)}"
    assert not state_path(root).exists(), "the state of the restore is removed"
    assert api.tree(stage_dir(root, stage_id)) == copy_before and check_state_path(root, stage_id).is_file(), "the copy and its check stay, until they expire"
    assert (await restore_status()).json()["state"] == "none", "no restore any more"
    again = await confirm(stage_id)
    assert again.status_code == 202, f"the copy can be confirmed again: {api.shown(again)}"
    print_success("204, copy kept, confirmed again")


@pytest.mark.asyncio
@pytest.mark.parametrize("found", ["nothing", "a-checked-copy"])
async def test_a_cancel_without_a_restore_is_404_and_creates_nothing(instance, head_archive, found):
    """(d) No state file, in an empty data directory or beside a checked copy: 404 ``restore_not_pending``, and nothing
    created, not even ``.restore/apply.lock``: the lock is taken only once a state file is found."""
    root = instance.root
    if found == "a-checked-copy":
        await checked(head_archive)
    before = api.tree(root)
    response = await cancel()
    assert api.code(response) == (404, "restore_not_pending"), f"{found}: 404 restore_not_pending: {api.shown(response)}"
    assert api.tree(root) == before, f"{found}: nothing created: {cases.changed(before, api.tree(root))}"
    print_success(f"{found}: 404, nothing created")


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", [*ACTIVE[1:], *TERMINAL])
async def test_only_a_pending_restore_can_be_cancelled(instance, phase):
    """(d) A restore being applied or undone, or one finished: 404 ``restore_not_pending``, its state as it was."""
    root = instance.root
    before = write_state(root, phase, api.UNKNOWN_ID)
    response = await cancel()
    assert api.code(response) == (404, "restore_not_pending"), f"{phase}: 404 restore_not_pending: {api.shown(response)}"
    assert state_path(root).read_bytes() == before, f"{phase}: the state is as it was"
    print_success(f"{phase}: 404")


# =============================================================================
# (e) POST /restart
# =============================================================================


@pytest.mark.asyncio
async def test_a_restart_answers_then_stops_the_server_with_sigterm(instance, head_archive, signals):
    """(e) The answer first, then ``request_restart``: a SIGTERM to the server's process, once, through
    ``restart.send_signal``. Under Docker the container comes back by itself."""
    print_section("POST /backup/restore/restart")
    root = instance.root
    stage_id = await confirmed(head_archive)
    before = state_path(root).read_bytes()
    response = await restart(answered=signals)
    assert response.status_code == 202, f"a pending restore: 202: {api.shown(response)}"
    body = response.json()
    assert set(body) == STATUS_FIELDS and (body["state"], body["stage_id"]) == ("pending", stage_id), f"the pending restore: {body}"
    pid = restart_module().server_pid()
    assert signals.sent == [(pid, signal.SIGTERM, True)], f"one SIGTERM to the server ({pid}), once the answer was sent: {signals.sent}"
    assert signals.around == [], f"no signal outside restart.send_signal: {signals.around}"
    assert state_path(root).read_bytes() == before, "the restart changes nothing of the restore: the next start applies it"
    print_success(f"202, then SIGTERM to {pid}")


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", [None, *ACTIVE[1:], *TERMINAL])
async def test_no_restart_without_a_pending_restore(instance, signals, phase):
    root = instance.root
    if phase:
        write_state(root, phase, api.UNKNOWN_ID)
    response = await restart(answered=signals)
    assert api.code(response) == (409, "restore_not_pending"), f"{phase or 'no restore'}: 409 restore_not_pending: {api.shown(response)}"
    assert (signals.sent, signals.around) == ([], []), f"{phase or 'no restore'}: no signal: {signals.sent} {signals.around}"
    print_success(f"{phase or 'no restore'}: 409, no signal")


# =============================================================================
# (f) The copy of an ACTIVE restore: never dropped, never pruned
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ACTIVE)
async def test_the_copy_of_an_active_restore_cannot_be_dropped(instance, head_archive, phase):
    """(f) 409 ``restore_pending``: the copy and its check stay as they are. Another check is dropped as before."""
    print_section("The copy of an active restore")
    root = instance.root
    if phase == "pending":
        stage_id = await confirmed(head_archive)
    else:
        stage_id = await checked(head_archive)
        write_state(root, phase, stage_id)
    other = await checked(head_archive)
    before = (api.tree(stage_dir(root, stage_id)), check_state_path(root, stage_id).read_bytes())
    response = await api.drop(stage_id)
    assert api.code(response) == (409, "restore_pending"), f"{phase}: the restore's copy cannot be dropped: {api.shown(response)}"
    assert (api.tree(stage_dir(root, stage_id)), check_state_path(root, stage_id).read_bytes()) == before, f"{phase}: the copy and its check are kept as they were"
    assert (await api.drop(other)).status_code == 204 and not stage_dir(root, other).exists(), f"{phase}: another check is dropped as before"
    print_success(f"{phase}: 409 restore_pending; another check dropped")


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", TERMINAL)
async def test_the_copy_of_a_finished_restore_can_be_dropped(instance, head_archive, phase):
    root = instance.root
    stage_id = await checked(head_archive)
    write_state(root, phase, stage_id)
    response = await api.drop(stage_id)
    assert response.status_code == 204 and not stage_dir(root, stage_id).exists(), f"{phase}: dropped: {api.shown(response)}"
    print_success(f"{phase}: 204")


def prune_far_ahead(root: Path) -> None:
    """``prune`` as if a month had passed: every check, copy and upload is older than a check's lifetime."""
    restore_jobs.prune(root, now=datetime.now(UTC) + FAR_AHEAD)


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ACTIVE)
async def test_prune_keeps_the_check_and_copy_of_an_active_restore_however_old(instance, head_archive, phase):
    """(f) A month on, the ACTIVE restore's check and copy are still there; another ended check is pruned as before."""
    root = instance.root
    if phase == "pending":
        stage_id = await confirmed(head_archive)
    else:
        stage_id = await checked(head_archive)
        write_state(root, phase, stage_id)
    other = await checked(head_archive)
    before = (api.tree(stage_dir(root, stage_id)), check_state_path(root, stage_id).read_bytes())
    prune_far_ahead(root)
    assert (api.tree(stage_dir(root, stage_id)), check_state_path(root, stage_id).read_bytes()) == before, f"{phase}: the restore's check and copy are kept"
    assert not stage_dir(root, other).exists() and not check_state_path(root, other).exists(), f"{phase}: another old check is pruned"
    print_success(f"{phase}: kept; another check pruned")


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", TERMINAL)
async def test_prune_removes_the_old_copy_of_a_finished_restore(instance, head_archive, phase):
    root = instance.root
    stage_id = await checked(head_archive)
    write_state(root, phase, stage_id)
    prune_far_ahead(root)
    assert not stage_dir(root, stage_id).exists() and not check_state_path(root, stage_id).exists(), f"{phase}: pruned as any old check"
    print_success(f"{phase}: pruned")


def test_prune_keeps_the_command_lines_copy_of_a_pending_restore(instance, head_archive):
    """(f) The command line checks on a copy no check records, and confirms it: ``prune`` keeps it however old, while
    the restore is pending; cancelled, it is an old unrecorded copy like any other, and pruned."""
    root = instance.root
    apply = apply_module()
    report = staging_service.stage_archive(head_archive.path, root)
    apply.confirm_restore(report.stage_id, confirmed_by="cli", data_dir=root)
    before = api.tree(stage_dir(root, report.stage_id))
    assert not check_state_path(root, report.stage_id).exists(), "precondition: no check records the copy"
    prune_far_ahead(root)
    assert api.tree(stage_dir(root, report.stage_id)) == before, "the pending restore's copy is kept, however old"
    apply.cancel_restore(data_dir=root)
    prune_far_ahead(root)
    assert not stage_dir(root, report.stage_id).exists(), "once the restore is cancelled, the old copy is pruned"
    print_success("CLI copy kept while pending, pruned once cancelled")


# =============================================================================
# (g) Administrators only, never on a blocked instance, OpenAPI
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["confirm", "status", "cancel", "restart"])
async def test_a_regular_user_is_refused_403_and_nothing_happens(instance, head_archive, signals, route):
    """(g) A restore replaces every user's data: each route is for administrators. A regular user's request is 403;
    nothing is confirmed, read, cancelled or restarted."""
    print_section("Administrators only")
    root = instance.root
    stage_id = await checked(head_archive)
    if route != "confirm":
        assert (await confirm(stage_id)).status_code == 202, "precondition: a pending restore"
    before = api.tree(restore_dir(root))
    requests = {
        "confirm": lambda: confirm(stage_id, user=api.REGULAR_USER),
        "status": lambda: restore_status(user=api.REGULAR_USER),
        "cancel": lambda: cancel(user=api.REGULAR_USER),
        "restart": lambda: restart(user=api.REGULAR_USER, answered=signals),
    }
    response = await requests[route]()
    assert (response.status_code, response.json()) == api.ADMIN_ONLY_ANSWER, f"{route} as a regular user: 403: {api.shown(response)}"
    assert api.tree(restore_dir(root)) == before, f"{route}: nothing changed under .restore"
    assert (signals.sent, signals.around) == ([], []), f"{route}: no signal"
    print_success(f"{route}: 403")


#: The four routes of lot B3, as ``restore_router`` declares them (under the ``/backup`` prefix of ``backup_router``).
NEW_ROUTES = {("POST", "/restore/stage/{stage_id}/confirm"), ("GET", "/restore/status"), ("DELETE", "/restore/pending"), ("POST", "/restore/restart")}


def test_no_new_restore_route_is_allowed_on_a_blocked_instance():
    """(g) The block lets the data leave, never come in, nor the server be stopped: none of the four is in
    ``ALLOWED_WHEN_BLOCKED``."""
    endpoints = {(method, route.path): route.endpoint for route in restore.restore_router.routes for method in getattr(route, "methods", ())}
    missing = sorted(NEW_ROUTES - set(endpoints))
    assert missing == [], f"routes of lot B3 not declared by restore.py: {missing}"
    allowed = sorted(f"{method} {path}" for method, path in NEW_ROUTES if endpoints[(method, path)] in ALLOWED_WHEN_BLOCKED)
    assert allowed == [], f"a restore route allowed on a blocked instance: {allowed}"


def test_openapi_documents_the_four_routes_their_answers_and_codes():
    """(g) Each operation under ``Backup & Export``, its success and model, its refusals documented with their codes;
    the drop of a check documents ``restore_pending``."""
    document = api.restore_app().openapi()
    paths = {("POST", CONFIRM): "post", ("GET", STATUS): "get", ("DELETE", PENDING): "delete", ("POST", RESTART): "post"}
    missing = sorted(f"{method} {path}" for (method, path), verb in paths.items() if verb not in document["paths"].get(path, {}))
    assert missing == [], f"operations missing from OpenAPI: {missing}"
    operations = {key: document["paths"][key[1]][verb] for key, verb in paths.items()}
    tags = {key: operation["tags"] for key, operation in operations.items()}
    assert tags == dict.fromkeys(paths, [api.TAG]), f"each under {api.TAG} and no other: {tags}"
    success = {key: next(status for status in operation["responses"] if status.startswith("2")) for key, operation in operations.items()}
    assert success == {("POST", CONFIRM): "202", ("GET", STATUS): "200", ("DELETE", PENDING): "204", ("POST", RESTART): "202"}, f"the success of each: {success}"
    models = {key: operation["responses"][success[key]].get("content", {}).get("application/json", {}).get("schema") for key, operation in operations.items()}
    status_model = {"$ref": "#/components/schemas/RestoreStatus"}
    assert models == {("POST", CONFIRM): status_model, ("GET", STATUS): status_model, ("DELETE", PENDING): None, ("POST", RESTART): status_model}, f"the model of each success: {models}"
    codes = {
        ("POST", CONFIRM): {"404": ["restore_stage_not_found"], "409": ["restore_stage_running", "restore_not_restorable", "restore_stage_outdated", "restore_already_pending"], "410": ["restore_stage_expired"], "500": ["restore_folder_unusable"]},
        ("DELETE", PENDING): {"404": ["restore_not_pending"]},
        ("POST", RESTART): {"409": ["restore_not_pending"]},
    }
    undocumented: dict[str, list[str]] = {}
    for key, statuses in codes.items():
        for status, names in statuses.items():
            description = operations[key]["responses"].get(status, {}).get("description", "")
            if absent := [name for name in names if name not in description]:
                undocumented[f"{key[0]} {key[1]} {status}"] = absent
    assert undocumented == {}, f"refusals answered but not documented with their code: {undocumented}"
    drop = document["paths"][api.STAGE_ITEM]["delete"]["responses"].get("409", {}).get("description", "")
    assert "restore_pending" in drop, f"the drop of a check documents restore_pending: {drop!r}"
    schema = document["components"]["schemas"]["RestoreStatus"]
    assert set(schema["properties"]) == STATUS_FIELDS, f"RestoreStatus has its 11 fields, upload_limit_mb included: {sorted(schema['properties'])}"
    waiting = schema["properties"]["waiting"]
    reasons = {value for option in waiting.get("anyOf", [waiting]) for value in option.get("enum", [])}
    assert reasons == set(WAIT_REASONS), f"RestoreStatus.waiting lists exactly the four reasons, instance_blocked included (§11): {waiting}"
    print_success("4 operations documented, RestoreStatus with upload_limit_mb")


# =============================================================================
# (h) upload_limit_mb
# =============================================================================


#: (profile, the variable, the limit every RestoreStatus says): the variable wins over the profile when set.
STATUS_LIMITS = [
    pytest.param("selfhosted", None, 0, id="self-hosted-unset"),
    pytest.param("managed", None, 500, id="managed-unset"),
    pytest.param("selfhosted", "250", 250, id="self-hosted-250"),
    pytest.param("managed", "120", 120, id="managed-the-variable-wins"),
    pytest.param("managed", "0", 0, id="managed-0-lifts-the-limit"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("profile", "value", "limit"), STATUS_LIMITS)
async def test_the_status_says_the_upload_limit_without_a_restore(instance, monkeypatch, profile, value, limit):
    """(h) ``state: none`` too: a client learns the limit before it uploads anything."""
    print_section("upload_limit_mb")
    monkeypatch.setenv(api.PROFILE_VARIABLE, profile)
    if value is not None:
        monkeypatch.setenv(api.LIMIT_VARIABLE, value)
    response = await restore_status()
    assert response.status_code == 200, api.shown(response)
    assert (response.json()["state"], response.json()["upload_limit_mb"]) == ("none", limit), f"{profile}, {api.LIMIT_VARIABLE}={value!r}: {limit}: {response.json()}"
    print_success(f"{profile}, {value!r}: {limit}")


@pytest.mark.asyncio
async def test_a_limit_that_cannot_be_read_is_null_and_logged_once_naming_the_variable(instance, monkeypatch):
    """(h) The status still answers, the limit ``null``; one error in the log names the variable, as the upload's 503."""
    monkeypatch.setenv(api.LIMIT_VARIABLE, "abc")
    with capture_logs() as events:
        response = await restore_status()
    assert (response.status_code, response.json()["upload_limit_mb"]) == (200, None), f"200, the limit null: {api.shown(response)}"
    errors = [event for event in events if event.get("log_level") == "error"]
    assert len(errors) == 1 and api.LIMIT_VARIABLE in str(errors[0].get("error")), f"one error in the log, naming the variable: {errors}"
    print_success("unreadable: null, one error naming the variable")


@pytest.mark.asyncio
async def test_confirm_status_and_restart_say_the_same_limit(instance, head_archive, monkeypatch, signals):
    monkeypatch.setenv(api.LIMIT_VARIABLE, "321")
    stage_id = await checked(head_archive)
    answers = {"confirm": await confirm(stage_id), "status": await restore_status(), "restart": await restart(answered=signals)}
    limits = {name: (response.status_code, response.json().get("upload_limit_mb")) for name, response in answers.items()}
    assert limits == {"confirm": (202, 321), "status": (200, 321), "restart": (202, 321)}, f"the same limit in every answer: {limits}"
    print_success("confirm, status, restart: 321")


@pytest.mark.asyncio
async def test_the_limit_is_read_when_each_answer_is_built(instance, head_archive, monkeypatch):
    """(h) Never kept from an earlier answer: the variable changed between two answers shows in the second."""
    monkeypatch.setenv(api.LIMIT_VARIABLE, "100")
    stage_id = await checked(head_archive)
    first = await confirm(stage_id)
    monkeypatch.setenv(api.LIMIT_VARIABLE, "200")
    second = await restore_status()
    monkeypatch.delenv(api.LIMIT_VARIABLE)
    third = await restore_status()
    limits = [(response.status_code, response.json().get("upload_limit_mb")) for response in (first, second, third)]
    assert limits == [(202, 100), (200, 200), (200, 0)], f"each answer reads the variable as it is then: {limits}"
    print_success("100, then 200, then 0")
