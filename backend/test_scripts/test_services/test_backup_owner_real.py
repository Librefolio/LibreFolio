"""
The owner's account after a restore, with A's REAL function (workstream B, lot B5-1e). Selector: ``services backup-owner-real``.

``test_backup_owner.py`` plays ``assign_owner_and_send_reset`` with a fake behind ``owner._assign_owner``. Here nothing of
the chain is played but the mail: a real backup at the migration head (accounts, ``users.is_instance_owner``) is confirmed
from the app on the ``managed`` profile, applied and committed by the real lifecycle, and ``owner.assign_restored_owner``
calls the real ``instance_owner.assign_owner_and_send_reset`` on the restored database. The email goes to an outbox
(``instance_owner.send_email``, as A's ``test_owner_assignment.py`` fakes it) and the SMTP transport is a tripwire.

(a) The whole round: the chosen account is the owner (address, administrator, active, ``is_instance_owner``; the backup's
    password opens nothing; no other account marked); ONE live password-reset link exists (the planted one, dated in the
    future, is gone); the outbox got one email to the owner's address; ``owner_outcome`` is ``sent``; the link is in no
    place the restore writes or prints (``restore.json``, ``read_restore``, ``backup pending`` with and without ``--json``,
    the log).
(b) The email cannot go (the outbox raises, or SMTP is off): ``link_only``. The link is in the instance log, on A's own
    line, and nowhere else: not in the state file, ``read_restore``, the ``backup pending`` outputs, nor in any other log line
    (so none of this module's ``instance_backup.owner``).
(c) The fail-closed round: another account holds the owner's address and the chosen one is a different account: the real
    function raises ``EMAIL_TAKEN``, recorded as ``error:EMAIL_TAKEN``; the guard's hook says so; the database is not changed
    by the refusal. Once the administrator frees the address, ``backup pending --recover owner`` (nobody serving) runs the
    real call again: exit 0, the owner assigned, the hook says ``None``.
(d) A crash between A's call and our record: the next start calls A again; the previous link is dead, ONE link is live, a
    second email goes, the outcome is recorded.
(e) Only the chosen id goes to A: the spy sees ``(user_id)`` and nothing else — no ``since``, no ``now`` — on a fresh session.

Pure: the data directory is under ``tmp_path`` (the helpers of ``test_backup_apply.py``), the restore is real, only the
mail is fake. No lane database, no server, no network.
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import json
import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

from backend.app.services.accounts import auth_service, user_service
from backend.app.services.email import delivery, smtp
from backend.app.services.email.messages import EmailContent
from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY
from backend.test_scripts.test_services import test_backup_apply as base
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_services import test_session_version as sessions
from backend.test_scripts.test_utilities import test_backup_cli as cli
from backend.test_scripts.test_utilities import test_backup_cli_recover as recover
from backend.test_scripts.test_utils import print_section, print_success

# The module fixtures of the restore tests, re-exported (autouse there, so here): the real databases and the checked copy,
# the configured data directory that must stay absent, the JWT secret, the boots cache, no inherited block.
databases = cases.databases
head_archive = cases.head_archive
checked = base.checked
configured_data_dir = cases.configured_data_dir
secret = sessions.secret
fresh_boots = base.fresh_boots
no_inherited_block = base.no_inherited_block

INSTANCE_OWNER = "backend.app.services.accounts.instance_owner"
OWNER_MODULE = "backend.app.services.platform.instance_backup.owner"
#: The owner's address (the hoster's variable), distinctive.
OWNER_EMAIL = "owner.b51e@zq-real.example.com"
#: What the instance sends from and links to: an email that can go (A's ``test_owner_assignment.py`` uses the same pair).
SMTP_HOST = "smtp.zq-real.example.com"
SENDER_HEADER = "LibreFolio <noreply@example.com>"
PUBLIC_URL = "https://folio.zq-real.example.com:8443/app"
#: Variables a developer's shell may carry that the cases set themselves.
CLEAN_PREFIXES = ("LIBREFOLIO_ADMIN_", "LIBREFOLIO_SMTP_")
CLEAN_NAMES = ("LIBREFOLIO_PUBLIC_URL", "LIBREFOLIO_REGISTRATION", "LIBREFOLIO_MAX_USERS", "LIBREFOLIO_PROFILE")
#: The account the owner chooses, the one that holds the address (case c), and the planted token's date.
CHOSEN = base.ADA
FAR_FUTURE = datetime(2126, 1, 1, tzinfo=UTC)


# =============================================================================
# The mail, played; everything else is real
# =============================================================================


@dataclass(frozen=True)
class SentEmail:
    content: EmailContent
    to: str
    user_id: int | None


@dataclass
class Outbox:
    """``instance_owner.send_email`` replaced: each attempt recorded, then ``failure`` raised when set."""

    attempts: list[SentEmail] = field(default_factory=list)
    failure: BaseException | None = None

    async def send_email(self, content: EmailContent, *, to: str, user_id: int | None = None) -> None:
        self.attempts.append(SentEmail(content=content, to=to, user_id=user_id))
        if self.failure is not None:
            raise self.failure

    def token_of(self, attempt: int = -1) -> str:
        """The token in the link of an email: what only the owner's mailbox should hold."""
        link = next(line.strip() for line in self.attempts[attempt].content.text.splitlines() if line.startswith("http"))
        return link.split("token=", 1)[1]


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.startswith(CLEAN_PREFIXES) or name in CLEAN_NAMES:
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def cheap_bcrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)


@pytest.fixture(autouse=True)
def private_owner_knowledge(monkeypatch: pytest.MonkeyPatch) -> None:
    """``note_recorded_owner`` keeps the owner's id for the life of a process: put back after every test."""
    if hasattr(user_service, "_recorded_owner"):
        monkeypatch.setattr(user_service, "_recorded_owner", user_service._recorded_owner)


@pytest.fixture(autouse=True)
def no_smtp_conversation(monkeypatch: pytest.MonkeyPatch) -> Any:
    attempts: list[str] = []

    def refuse(_server: object, message: object) -> None:
        attempts.append(type(message).__name__)
        raise AssertionError("a real-owner test reached the SMTP transport")

    monkeypatch.setattr(smtp, "deliver", refuse)
    yield attempts
    assert attempts == []


@pytest.fixture
def instance_owner() -> ModuleType:
    return importlib.import_module(INSTANCE_OWNER)


@pytest.fixture
def owner() -> ModuleType:
    return importlib.import_module(OWNER_MODULE)


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch, instance_owner: ModuleType) -> Outbox:
    box = Outbox()
    monkeypatch.setattr(instance_owner, "send_email", box.send_email)
    return box


def email_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    """The instance can send email and knows its public address."""
    monkeypatch.setenv("LIBREFOLIO_SMTP_HOST", SMTP_HOST)
    monkeypatch.setenv("LIBREFOLIO_SMTP_FROM", SENDER_HEADER)
    monkeypatch.setenv("LIBREFOLIO_PUBLIC_URL", PUBLIC_URL)
    assert delivery.email_config_state().usable, "barrier: the email configuration is usable"


# =============================================================================
# A real restore, up to the commit
# =============================================================================


@dataclass
class Restored:
    """A committed restore on the managed profile: the instance, the chosen account's id, the planted token's hash, and the
    password hash every account of the backup held."""

    instance: base.Instance
    chosen_id: int
    planted: str
    backup_hashes: dict[str, str]

    @property
    def root(self) -> Path:
        return self.instance.root

    @property
    def database(self) -> Path:
        return self.instance.root / DATABASE_ENTRY


def plant_reset(database: Path, user_id: int) -> str:
    """A live password-reset token of the chosen account, dated in the far future: whoever prepared the backup wrote it.
    Its hash."""

    def stored(moment: datetime) -> str:
        return moment.astimezone(UTC).replace(tzinfo=None).isoformat(sep=" ", timespec="microseconds")

    planted = hashlib.sha256(b"b51e-planted").hexdigest()
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute(
            "INSERT INTO account_tokens (purpose, token_hash, user_id, email, grants_admin, created_at, expires_at) VALUES ('password_reset', ?, ?, ?, 0, ?, ?)",
            (planted, user_id, "planted@other-instance.example.net", stored(FAR_FUTURE), stored(FAR_FUTURE + timedelta(days=1))),
        )
    return planted


def restored_instance(tmp_path: Path, databases: cases.Databases, checked: base.Checked, monkeypatch: pytest.MonkeyPatch, *, holder: str | None = None) -> Restored:
    """The backup's accounts given the backup's password, a planted reset token for the chosen account, the restore
    confirmed from the app naming the chosen account, applied and committed. ``holder``: the username of another account of
    the backup that holds the owner's address (the check's report, hand-made, still says none does)."""
    apply = base.apply_module()
    instance = base.owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[base.ADA, base.ZOE])
    copy_database = instance.copy / DATABASE_ENTRY
    if holder is not None:
        cases.execute(copy_database, f"UPDATE users SET email = '{OWNER_EMAIL}' WHERE username = '{holder}'")
    hashes = base.with_backup_passwords(copy_database)
    chosen_id = CHOSEN["user_id"]
    assert base.accounts_of(copy_database)[CHOSEN["username"]]["id"] == chosen_id, "precondition: the chosen account's id in the backup"
    assert base.OWNER_COLUMN in base.accounts_of(copy_database)[CHOSEN["username"]], "precondition: the backup is at the head, with A's is_instance_owner column"
    planted = plant_reset(copy_database, chosen_id)
    state, _events = base.committed_after(apply, instance, owner_user_id=chosen_id)
    assert (state.status, state.owner_user_id, state.owner_outcome) == ("committed", chosen_id, None), f"precondition: committed, the owner chosen, nothing recorded yet: {state}"
    return Restored(instance=instance, chosen_id=chosen_id, planted=planted, backup_hashes=hashes)


def run(coroutine: Any) -> Any:
    return asyncio.run(coroutine)


def step(owner: ModuleType, restored: Restored) -> tuple[Any, list[dict[str, Any]]]:
    """``assign_restored_owner`` on the restored data, what it returned and what was logged."""
    with capture_logs() as events:
        returned = run(owner.assign_restored_owner(restored.root))
    return returned, list(events)


# =============================================================================
# What the database and the files say
# =============================================================================


def user_row(database: Path, user_id: int) -> dict[str, Any]:
    with closing(cases.read_only(database)) as conn:
        cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, cursor.fetchone(), strict=True))


def reset_links(database: Path, user_id: int) -> list[tuple[str, str | None, str | None, str | None]]:
    """The ``password_reset`` rows of an account: (token_hash, email, consumed_at, revoked_at), by id. A row is told by its
    hash, not its id: the table reuses the id of a row that was deleted."""
    return cases.rows_of(database, f"SELECT token_hash, email, consumed_at, revoked_at FROM account_tokens WHERE purpose = 'password_reset' AND user_id = {user_id} ORDER BY id")


def owners(database: Path) -> list[int]:
    return [row[0] for row in cases.rows_of(database, "SELECT id FROM users WHERE is_instance_owner = 1 ORDER BY id")]


def snapshot(database: Path) -> dict[str, list[tuple]]:
    return {table: cases.rows_of(database, f"SELECT * FROM {table} ORDER BY 1") for table in ("users", "account_tokens")}


def assert_the_owner(restored: Restored) -> None:
    """The chosen account holds the owner's role; the backup's password opens nothing; nobody else is the owner."""
    row = user_row(restored.database, restored.chosen_id)
    assert (row["email"], row["is_superuser"], row["is_active"], row["is_instance_owner"]) == (OWNER_EMAIL, 1, 1, 1), f"the owner's address, an active administrator, the instance owner: {row['email']}, {row['is_superuser']}, {row['is_active']}, {row['is_instance_owner']}"
    assert row["hashed_password"] != restored.backup_hashes[CHOSEN["username"]], "the backup's hash is gone"
    assert not auth_service.verify_password(base.BACKUP_PASSWORD, row["hashed_password"]), "the backup's password opens nothing"
    assert owners(restored.database) == [restored.chosen_id], f"the chosen account is the only owner: {owners(restored.database)}"


def assert_one_live_link(restored: Restored) -> str:
    """ONE password-reset row for the chosen account, live, marked with the owner's address; the planted one is gone. Its hash."""
    rows = reset_links(restored.database, restored.chosen_id)
    assert len(rows) == 1, f"one password-reset link: {rows}"
    link_hash, email, consumed_at, revoked_at = rows[0]
    assert link_hash != restored.planted and (email, consumed_at, revoked_at) == (OWNER_EMAIL, None, None), f"the planted link is gone, the new one is live and marked with the owner's address: {rows}"
    return link_hash


def state_text(root: Path) -> str:
    return base.state_file(root).read_text(encoding="utf-8")


def assert_no_secret_where_we_write(restored: Restored, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, *secrets: str) -> None:
    """Neither ``secrets`` (a token, the path of a link) nor any link is in what the restore writes or prints: ``restore.json``,
    what ``read_restore`` reads, ``backup pending`` and ``backup pending --json``."""
    cli.point_at(monkeypatch, restored.root)
    human = recover.go(capsys, "pending")
    machine = recover.go(capsys, "pending", "--json")
    read = repr(base.apply_module().read_restore(restored.root).model_dump())
    places = {"restore.json": state_text(restored.root), "read_restore": read, "pending": human.out + human.err, "pending --json": machine.out + machine.err}
    assert (human.code, machine.code) == (0, 0), f"pending reads: {human.code}, {machine.code}"
    shown = [(place, secret) for place, text in places.items() for secret in (*secrets, "reset-password", "owner_reset_path") if secret and secret in text]
    assert shown == [], f"a secret in what the restore writes or prints: {shown}"


def link_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The events A writes with the link: the instance log's own line, for ``link_only``."""
    return [event for event in events if "link" in event]


def secret_in(events: list[dict[str, Any]], token: str) -> list[dict[str, Any]]:
    return [event for event in events if token in repr(event)]


# =============================================================================
# (a) The whole round, the email goes
# =============================================================================


def test_the_real_round_makes_the_chosen_account_the_owner_and_emails_one_link(tmp_path, databases, checked, monkeypatch, capsys, outbox, owner):
    """(a) B5-1e: a restore from the app on the managed profile, committed; the real function then gives the chosen account
    the owner's address, administrator, active, the instance-owner mark; its password opens nothing; ONE reset link is live
    (the planted one, dated in the future, is gone) and goes by email to the owner's address; ``sent`` is recorded; the token
    is in the email only: no state file, no ``read_restore``, no ``pending`` output, no log line holds it."""
    print_section("(a) B5-1e the real round: sent")
    email_ready(monkeypatch)
    restored = restored_instance(tmp_path, databases, checked, monkeypatch)
    returned, events = step(owner, restored)
    assert returned is not None and (returned.status, returned.owner_user_id, returned.owner_outcome) == ("committed", restored.chosen_id, "sent"), f"the step recorded sent: {returned}"
    assert_the_owner(restored)
    assert_one_live_link(restored)
    assert [(mail.to, mail.user_id, mail.content.kind) for mail in outbox.attempts] == [(OWNER_EMAIL, restored.chosen_id, "password_reset")], f"one email, to the owner's address: {outbox.attempts}"
    token = outbox.token_of()
    assert secret_in(events, token) == [], f"the link is in no log line when the email went: {secret_in(events, token)}"
    assert base.apply_module().read_restore(restored.root).owner_outcome == "sent"
    assert base.apply_module().owner_assignment_problem(restored.root) is None, "nothing keeps the owner out"
    assert_no_secret_where_we_write(restored, capsys, monkeypatch, token)
    print_success("sent: the owner, one link, no secret")


# =============================================================================
# (b) The whole round, the email cannot go
# =============================================================================


@pytest.mark.parametrize("why", ["the-outbox-raises", "smtp-is-off"])
def test_the_real_round_without_email_records_link_only_and_keeps_the_link_in_the_instance_log(tmp_path, databases, checked, monkeypatch, capsys, outbox, owner, why):
    """(b) B5-1e: the email cannot go (the transport raises, or SMTP is not configured): ``link_only`` is recorded. The link
    is in the instance log, on A's own line — that is A's design — and in no other: not in any other log line (so none of
    ``instance_backup.owner``'s), not in ``restore.json``, ``read_restore``, nor the outputs of ``backup pending``."""
    print_section(f"(b) B5-1e the real round: link_only ({why})")
    if why == "the-outbox-raises":
        email_ready(monkeypatch)
        outbox.failure = RuntimeError("b51e smtp down")
    restored = restored_instance(tmp_path, databases, checked, monkeypatch)
    returned, events = step(owner, restored)
    assert returned is not None and returned.owner_outcome == "link_only", f"the step recorded link_only: {returned}"
    assert_the_owner(restored)
    assert_one_live_link(restored)
    shown = link_events(events)
    assert len(shown) == 1 and "reset-password" in str(shown[0]["link"]), f"the instance log holds the link once, on A's line: {[event.get('event') for event in events]}"
    token = str(shown[0]["link"]).split("token=", 1)[1]
    elsewhere = [event for event in secret_in(events, token) if event is not shown[0]]
    assert elsewhere == [], f"the link is in no other log line: {[event.get('event') for event in elsewhere]}"
    assert base.apply_module().read_restore(restored.root).owner_outcome == "link_only"
    assert_no_secret_where_we_write(restored, capsys, monkeypatch, token, str(shown[0]["link"]))
    print_success(f"link_only ({why}): the link in the instance log only")


# =============================================================================
# (c) The fail-closed round
# =============================================================================


def test_another_account_holding_the_address_fails_closed_and_the_recover_command_finishes_the_job(tmp_path, databases, checked, monkeypatch, capsys, outbox, owner):
    """(c) B5-1e: the backup's zoe holds the owner's address and the chosen account is another one (the report, written by
    hand, says nobody does). The real function raises ``EMAIL_TAKEN``: ``error:EMAIL_TAKEN`` is recorded, the guard's hook
    says so, and the refusal changed nothing in the database. The administrator frees the address; ``backup pending --recover
    owner`` (nobody serving) runs the real call again: exit 0, the owner assigned, the hook says ``None``."""
    print_section("(c) B5-1e fail closed, then --recover owner")
    email_ready(monkeypatch)
    restored = restored_instance(tmp_path, databases, checked, monkeypatch, holder="zoe_admin")
    apply = base.apply_module()
    before = snapshot(restored.database)
    returned, _events = step(owner, restored)
    assert returned is not None and returned.owner_outcome == "error:EMAIL_TAKEN", f"the refusal recorded: {returned}"
    assert apply.read_restore(restored.root).owner_outcome == "error:EMAIL_TAKEN"
    assert apply.owner_assignment_problem(restored.root) == "EMAIL_TAKEN", "the guard keeps serving nothing"
    assert snapshot(restored.database) == before, "the refusal changed nothing in the database"
    assert outbox.attempts == [], "no email went"
    # The administrator fixes the cause: the other account no longer holds the address.
    cases.execute(restored.database, "UPDATE users SET email = 'zoe.freed.b51e@example.com' WHERE username = 'zoe_admin'")
    cli.point_at(monkeypatch, restored.root)
    ran = recover.go(capsys, "pending", "--recover", "owner")
    assert ran.code == 0, f"--recover owner: exit 0, not {ran.code}\n{ran.out}{ran.err}"
    assert apply.read_restore(restored.root).owner_outcome in ("sent", "link_only"), f"the new outcome recorded: {apply.read_restore(restored.root).owner_outcome}"
    assert apply.owner_assignment_problem(restored.root) is None, "nothing keeps the owner out any more"
    assert_the_owner(restored)
    assert_one_live_link(restored)
    assert [mail.to for mail in outbox.attempts] == [OWNER_EMAIL], f"one email, to the owner: {outbox.attempts}"
    assert outbox.token_of() not in ran.out + ran.err + state_text(restored.root), "the link is not in the command's output nor the state"
    print_success("EMAIL_TAKEN, then --recover owner: the owner")


# =============================================================================
# (d) After a crash between the call and the record
# =============================================================================


def test_after_a_crash_between_the_call_and_the_record_the_next_start_calls_again(tmp_path, databases, checked, monkeypatch, capsys, outbox, owner):
    """(d) B5-1e: A's call happened but the record did not (``record_owner_outcome`` fails once): nothing is recorded and
    the owner stays pending; the next start calls A again: the old link is dead (its row gone), ONE link is live, a second
    email goes, ``sent`` is recorded, the chosen account is still the owner."""
    print_section("(d) B5-1e crash between the call and the record")
    email_ready(monkeypatch)
    restored = restored_instance(tmp_path, databases, checked, monkeypatch)
    apply = base.apply_module()
    real_record = apply.record_owner_outcome
    failed: list[str] = []

    def crashes_once(*args: Any, **kwargs: Any) -> Any:
        if not failed:
            failed.append("once")
            raise OSError("b51e the record could not be written")
        return real_record(*args, **kwargs)

    monkeypatch.setattr(apply, "record_owner_outcome", crashes_once)
    first, _events = step(owner, restored)
    assert first is None and failed == ["once"], f"the record failed, the step went on without it: {first}, {failed}"
    assert apply.read_restore(restored.root).owner_outcome is None, "nothing recorded: the owner is pending"
    assert apply.owner_assignment_problem(restored.root) == "pending"
    assert len(outbox.attempts) == 1, "the first call sent its email"
    first_token = outbox.token_of(0)
    first_link = assert_one_live_link(restored)
    second, _events = step(owner, restored)
    assert second is not None and second.owner_outcome == "sent", f"the next start records what A answered: {second}"
    assert len(outbox.attempts) == 2 and outbox.token_of(1) != first_token, f"a second email with a new link: {len(outbox.attempts)}"
    second_link = assert_one_live_link(restored)
    assert second_link != first_link, "the first link died: its row is gone, a new one is live"
    assert_the_owner(restored)
    assert apply.owner_assignment_problem(restored.root) is None
    print_success("crash: called again, one live link, the owner")


# =============================================================================
# (e) Only the chosen id goes to A
# =============================================================================


def test_only_the_chosen_id_goes_to_a_on_a_fresh_session(tmp_path, databases, checked, monkeypatch, capsys, outbox, owner, instance_owner):
    """(e) B5-1e: the real function is wrapped by a spy: it is called once with the chosen account's id as its only
    argument besides the session (no ``since``, no ``now``, no keyword), on a fresh ``AsyncSession`` with nothing pending in
    it; and a second start calls it again with a session of its own."""
    email_ready(monkeypatch)
    restored = restored_instance(tmp_path, databases, checked, monkeypatch)
    real = instance_owner.assign_owner_and_send_reset
    seen: list[dict[str, Any]] = []

    async def spy(session: AsyncSession, *args: Any, **kwargs: Any) -> Any:
        seen.append({"session": session, "args": args, "kwargs": kwargs, "fresh": not (session.new or session.dirty or session.deleted or session.in_transaction()), "is_async_session": isinstance(session, AsyncSession)})
        return await real(session, *args, **kwargs)

    monkeypatch.setattr(instance_owner, "assign_owner_and_send_reset", spy)
    returned, _events = step(owner, restored)
    assert returned is not None and returned.owner_outcome == "sent", f"the round went through the spy: {returned}"
    assert [(call["args"], call["kwargs"], call["fresh"], call["is_async_session"]) for call in seen] == [((restored.chosen_id,), {}, True, True)], f"only the chosen id, nothing else, a fresh session: {seen}"
    # A restart half way: the state forgets the outcome; the call is repeated with a new session.
    apply = base.apply_module()
    record = json.loads(state_text(restored.root))
    record["owner_outcome"] = None
    base.state_file(restored.root).write_text(json.dumps(record), encoding="utf-8")
    assert apply.read_restore(restored.root).owner_outcome is None
    step(owner, restored)
    assert len(seen) == 2 and seen[1]["session"] is not seen[0]["session"], "a session of its own at each start"
    assert [(call["args"], call["kwargs"]) for call in seen] == [((restored.chosen_id,), {})] * 2, f"the same, only the id: {seen}"
    print_success("A receives the chosen id only")
