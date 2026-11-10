"""``account_links``: every account link of the instance as administrators see it, and its revocation (release 1.3, lot UA3).

An account link is one row of ``account_tokens``. The contract pinned here:

1. ``link_state(record, now)`` reads the state in ``token_service.inspect_token``'s order: ``revoked`` first — a retired
   link, revoked and consumed at once (``token_service.retire_tokens``), reads revoked —, then ``used``, then
   ``expired`` (at ``expires_at`` exactly, as the token service says), else ``open``.
2. ``list_links(session, now=)`` lists every link, newest first (``created_at``, then ``id``, descending), each with its
   state at ``now`` and the usernames it refers to: ``username`` of the account it acts on (none for an invitation),
   ``created_by_username`` of whoever issued it (none once that account is deleted: the foreign key sets it null), and,
   for a used link only, ``used_by_user_id``/``used_by_username``: the account recorded as its consumer, or, for a
   link that acts on an existing account and recorded nobody, that account; an invitation that recorded nobody names
   nobody. ``revocable`` is true for an open link of ``REVOCABLE_PURPOSES`` only — invite, password_reset,
   email_verification.
3. ``revoke_link(session, link_id, now=)`` → ``revoked`` for an open link of those purposes, its row revoked at ``now``
   and nothing else written; ``not_found`` for an id that is not an open link — unknown, used, expired, revoked,
   retired —, read before the purpose: an expired setup link is ``not_found``, not ``not_revocable``; ``not_revocable``
   for an open ``admin_setup`` or ``email_change`` link. A refusal changes nothing. It flushes and does not commit: a
   rollback undoes it.

Replaces ``registration_service.revoke_invite`` (removed by UA3) and the tests that pinned it in
``test_registration_service.py``: a revoked invitation is still out of ``list_pending_invites``.

Every database is a private SQLite file under ``tmp_path`` built with ``create_all``, opened as production opens its own
(aiosqlite, NullPool, the PRAGMA listener of ``backend.app.db.session``: foreign keys on). No server, no lane database,
no clock wait: every moment is passed as ``now``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import AccountToken, AccountTokenPurpose, User
from backend.app.services.accounts import account_links, registration_service
from backend.app.services.accounts.token_service import DEFAULT_TTL, IssuedToken, TokenStatus, consume_token, inspect_token, issue_token, retire_tokens, revoke_tokens
from backend.app.utils.datetime_utils import ensure_utc, utcnow
from backend.test_scripts.test_utils import print_section, print_success

LinkState = account_links.LinkState

INVITE = AccountTokenPurpose.INVITE
PASSWORD_RESET = AccountTokenPurpose.PASSWORD_RESET
EMAIL_VERIFICATION = AccountTokenPurpose.EMAIL_VERIFICATION
ADMIN_SETUP = AccountTokenPurpose.ADMIN_SETUP
EMAIL_CHANGE = AccountTokenPurpose.EMAIL_CHANGE

SEEDED_HASH = "$argon2id$seeded-account"  # a marker: the accounts seeded here never log in
#: Far above any id a private database of a few rows reaches.
NEVER_ISSUED_ID = 987_654_321
#: The moment every state is read at, in the list and revoke cases: fixed, never the clock.
NOW = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file under tmp_path with the whole ORM schema, opened as production opens its own, disposed at teardown."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'account_links.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


# =============================================================================
# HELPERS
# =============================================================================


async def _add_users(engine: AsyncEngine, *names: str) -> dict[str, int]:
    """Accounts written as rows (``name@example.com``, a marker hash). Their ids, by name."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        created = {name: User(username=name, email=f"{name}@example.com", hashed_password=SEEDED_HASH) for name in names}
        session.add_all(created.values())
        await session.commit()
    return {name: int(user.id) for name, user in created.items()}


async def _issue(engine: AsyncEngine, purpose: AccountTokenPurpose, *, now: datetime, **arguments: Any) -> IssuedToken:
    """A token issued by the token service at ``now``, committed: the scene is set without the service under test."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await issue_token(session, purpose, now=now, **arguments)
        await session.commit()
    return issued


async def _consume(engine: AsyncEngine, issued: IssuedToken, purpose: AccountTokenPurpose, consumer: Optional[int], *, now: datetime) -> None:
    async with AsyncSession(engine) as session:
        assert await consume_token(session, issued.token, purpose, consumed_by_user_id=consumer, now=now) is not None, "setup: the token must be consumed"
        await session.commit()


async def _revoke(engine: AsyncEngine, token_id: int, *, now: datetime) -> None:
    async with AsyncSession(engine) as session:
        assert await revoke_tokens(session, token_id=token_id, now=now) == 1, "setup: the token must be revoked"
        await session.commit()


async def _retire(engine: AsyncEngine, user_id: int, purpose: AccountTokenPurpose, *, now: datetime) -> None:
    async with AsyncSession(engine) as session:
        assert await retire_tokens(session, user_id=user_id, purpose=purpose, now=now) >= 1, "setup: the token must be retired"
        await session.commit()


async def _row(engine: AsyncEngine, token_id: int) -> tuple[Any, Any]:
    """(consumed_at, revoked_at) of a token, read fresh."""
    async with AsyncSession(engine) as session:
        record = await session.get(AccountToken, token_id)
        assert record is not None, f"token {token_id} is not in the database"
        return record.consumed_at, record.revoked_at


async def _revoke_link(engine: AsyncEngine, link_id: int, *, now: datetime = NOW) -> str:
    """``revoke_link`` in a session of its own, committed afterwards — after a refusal too: a refusal must have written nothing."""
    async with AsyncSession(engine) as session:
        outcome = await account_links.revoke_link(session, link_id, now=now)
        await session.commit()
    return outcome


def _record(*, expires_at: datetime, consumed_at: Optional[datetime] = None, revoked_at: Optional[datetime] = None, purpose: AccountTokenPurpose = INVITE) -> AccountToken:
    """A row in memory only: ``link_state`` reads its columns and nothing else."""
    return AccountToken(purpose=purpose, token_hash="0" * 64, created_at=expires_at - timedelta(days=1), expires_at=expires_at, consumed_at=consumed_at, revoked_at=revoked_at)


# =============================================================================
# 1. LINK_STATE: THE ORDER OF THE READING
# =============================================================================


LINK_STATE_CASES = [
    pytest.param({"expires_at": NOW + timedelta(seconds=1)}, LinkState.OPEN, id="open-one-second-before-its-expiry"),
    pytest.param({"expires_at": NOW}, LinkState.EXPIRED, id="expired-at-expires-at-exactly"),
    pytest.param({"expires_at": NOW - timedelta(days=1)}, LinkState.EXPIRED, id="expired"),
    pytest.param({"expires_at": NOW + timedelta(days=1), "consumed_at": NOW - timedelta(hours=1)}, LinkState.USED, id="used"),
    pytest.param({"expires_at": NOW - timedelta(days=1), "consumed_at": NOW - timedelta(days=2)}, LinkState.USED, id="used-before-expired"),
    pytest.param({"expires_at": NOW + timedelta(days=1), "revoked_at": NOW - timedelta(hours=1)}, LinkState.REVOKED, id="revoked"),
    pytest.param({"expires_at": NOW - timedelta(days=1), "revoked_at": NOW - timedelta(days=2)}, LinkState.REVOKED, id="revoked-before-expired"),
    pytest.param({"expires_at": NOW + timedelta(days=1), "consumed_at": NOW - timedelta(hours=1), "revoked_at": NOW - timedelta(hours=1)}, LinkState.REVOKED, id="retired-reads-revoked"),
    pytest.param({"expires_at": (NOW + timedelta(seconds=1)).replace(tzinfo=None)}, LinkState.OPEN, id="naive-expiry-read-as-utc"),
]


@pytest.mark.parametrize(("columns", "expected"), LINK_STATE_CASES)
def test_link_state_reads_revoked_then_used_then_expired_then_open(columns: dict[str, datetime], expected: LinkState) -> None:
    """Contract 1: revoked before used before expired before open; a retired link (revoked and consumed) reads revoked; expired at ``expires_at`` exactly; a naive stored moment is UTC."""
    assert account_links.link_state(_record(**columns), NOW) == expected


@pytest.mark.asyncio
async def test_link_state_agrees_with_the_token_service_on_real_rows(engine: AsyncEngine) -> None:
    """Contract 1, on rows the token service wrote: each state ``link_state`` reads is the status ``inspect_token`` gives the same token — open/valid, used/consumed, expired, revoked, and the retired setup link revoked/revoked."""
    print_section("Contract 1: link_state and inspect_token agree")
    users = await _add_users(engine, "owner", "pending")
    now = utcnow()
    scene: dict[str, tuple[IssuedToken, AccountTokenPurpose]] = {}
    scene["open"] = (await _issue(engine, INVITE, now=now), INVITE)
    scene["used"] = (await _issue(engine, PASSWORD_RESET, now=now, user_id=users["owner"]), PASSWORD_RESET)
    await _consume(engine, scene["used"][0], PASSWORD_RESET, users["owner"], now=now)
    scene["expired"] = (await _issue(engine, INVITE, now=now - DEFAULT_TTL[INVITE] - timedelta(minutes=1)), INVITE)
    scene["revoked"] = (await _issue(engine, EMAIL_VERIFICATION, now=now, user_id=users["owner"]), EMAIL_VERIFICATION)
    await _revoke(engine, scene["revoked"][0].record.id, now=now)
    scene["retired"] = (await _issue(engine, ADMIN_SETUP, now=now, user_id=users["pending"]), ADMIN_SETUP)
    await _retire(engine, users["pending"], ADMIN_SETUP, now=now)

    readings: dict[str, tuple[str, str]] = {}
    async with AsyncSession(engine) as session:
        for name, (issued, purpose) in scene.items():
            inspection = await inspect_token(session, issued.token, purpose)
            assert inspection.record is not None, f"setup: the {name} token must be found"
            readings[name] = (account_links.link_state(inspection.record, utcnow()).value, inspection.status.value)

    expected = {
        "open": ("open", TokenStatus.VALID.value),
        "used": ("used", TokenStatus.CONSUMED.value),
        "expired": ("expired", TokenStatus.EXPIRED.value),
        "revoked": ("revoked", TokenStatus.REVOKED.value),
        "retired": ("revoked", TokenStatus.REVOKED.value),
    }
    assert readings == expected, f"(link_state, inspect_token) by scene: expected {expected}, got {readings}"
    print_success("five states, read as the token service reads them")


# =============================================================================
# 2. LIST_LINKS: EVERY LINK, NEWEST FIRST, WITH ITS NAMES
# =============================================================================


@pytest.mark.asyncio
async def test_list_links_lists_every_link_newest_first_with_its_state_and_usernames(engine: AsyncEngine) -> None:
    """Contract 2: ten links of every purpose and state, each listed once, newest first, with its state at ``now``, ``username`` of its account, ``created_by_username`` of its issuer (none once that account is deleted), ``used_by`` the recorded consumer or — not for an invitation — the link's own account, and ``revocable`` for the open links of the three revocable purposes only."""
    print_section("Contract 2: list_links")
    users = await _add_users(engine, "ann", "bob", "cara", "dan")
    ann, bob, cara, dan = users["ann"], users["bob"], users["cara"], users["dan"]
    at = [NOW - timedelta(hours=10 - step) for step in range(10)]  # one moment per link, oldest first

    invite_used = await _issue(engine, INVITE, now=at[0], created_by_user_id=ann)
    await _consume(engine, invite_used, INVITE, cara, now=at[0] + timedelta(minutes=1))
    invite_spent_by_nobody = await _issue(engine, INVITE, now=at[1], created_by_user_id=ann)
    await _consume(engine, invite_spent_by_nobody, INVITE, None, now=at[1] + timedelta(minutes=1))
    reset_used_unrecorded = await _issue(engine, PASSWORD_RESET, now=at[2], user_id=bob, created_by_user_id=ann)
    await _consume(engine, reset_used_unrecorded, PASSWORD_RESET, None, now=at[2] + timedelta(minutes=1))
    reset_used_recorded = await _issue(engine, PASSWORD_RESET, now=at[3], user_id=bob, created_by_user_id=ann)
    await _consume(engine, reset_used_recorded, PASSWORD_RESET, bob, now=at[3] + timedelta(minutes=1))
    invite_revoked = await _issue(engine, INVITE, now=at[4], created_by_user_id=ann)
    await _revoke(engine, invite_revoked.record.id, now=at[4] + timedelta(minutes=1))
    invite_expired = await _issue(engine, INVITE, now=NOW - DEFAULT_TTL[INVITE] - timedelta(minutes=1), created_by_user_id=ann)
    invite_by_dan = await _issue(engine, INVITE, now=at[5], created_by_user_id=dan, email="guest@example.com", grants_admin=True)
    verification_open = await _issue(engine, EMAIL_VERIFICATION, now=at[6], user_id=bob, email="bob-new@example.com")
    setup_open = await _issue(engine, ADMIN_SETUP, now=at[7], user_id=cara)
    change_open = await _issue(engine, EMAIL_CHANGE, now=at[8], user_id=ann, email="ann-new@example.com")
    async with AsyncSession(engine) as session:
        await session.execute(delete(User).where(User.id == dan))  # type: ignore[arg-type]
        await session.commit()

    async with AsyncSession(engine) as session:
        views = await account_links.list_links(session, now=NOW)

    found = {view.record.id: (view.state.value, view.username, view.created_by_username, view.used_by_user_id, view.used_by_username, view.revocable) for view in views}
    expected = {
        invite_used.record.id: ("used", None, "ann", cara, "cara", False),
        invite_spent_by_nobody.record.id: ("used", None, "ann", None, None, False),
        reset_used_unrecorded.record.id: ("used", "bob", "ann", bob, "bob", False),
        reset_used_recorded.record.id: ("used", "bob", "ann", bob, "bob", False),
        invite_revoked.record.id: ("revoked", None, "ann", None, None, False),
        invite_expired.record.id: ("expired", None, "ann", None, None, False),
        invite_by_dan.record.id: ("open", None, None, None, None, True),
        verification_open.record.id: ("open", "bob", None, None, None, True),
        setup_open.record.id: ("open", "cara", None, None, None, False),
        change_open.record.id: ("open", "ann", None, None, None, False),
    }
    violations: list[str] = []
    if found != expected:
        violations += [f"link {link_id}: expected (state, username, created_by, used_by_id, used_by, revocable) {expected.get(link_id)}, got {found.get(link_id)}" for link_id in sorted(set(found) | set(expected)) if found.get(link_id) != expected.get(link_id)]
    if len(views) != len(found):
        violations.append(f"a link is listed more than once: {[view.record.id for view in views]}")
    order = [view.record.id for view in views]
    newest_first = [view.record.id for view in sorted(views, key=lambda view: (ensure_utc(view.record.created_at), view.record.id), reverse=True)]
    if order != newest_first:
        violations.append(f"the list must be newest first: {order}, expected {newest_first}")
    dan_invite = next((view for view in views if view.record.id == invite_by_dan.record.id), None)
    if dan_invite is not None and dan_invite.record.created_by_user_id is not None:
        violations.append(f"a deleted issuer must leave created_by_user_id null: {dan_invite.record.created_by_user_id}")
    assert not violations, "list_links broke its contract:\n- " + "\n- ".join(violations)
    print_success("ten links, newest first, states and names as expected")


@pytest.mark.asyncio
async def test_list_links_reads_the_state_at_the_moment_asked_and_by_the_clock(engine: AsyncEngine) -> None:
    """Contract 2: the same open link reads ``open`` at a moment before its expiry and ``expired`` at its expiry; without ``now``, the clock decides (a link issued now is open); an empty instance lists nothing."""
    async with AsyncSession(engine) as session:
        assert await account_links.list_links(session, now=NOW) == [], "an instance without links lists nothing"
    issued = await _issue(engine, INVITE, now=utcnow())
    expires_at = ensure_utc(issued.record.expires_at)

    async with AsyncSession(engine) as session:
        before = [view.state for view in await account_links.list_links(session, now=expires_at - timedelta(seconds=1))]
        at_expiry = [view.state for view in await account_links.list_links(session, now=expires_at)]
        by_clock = [view.state for view in await account_links.list_links(session)]

    assert (before, at_expiry, by_clock) == ([LinkState.OPEN], [LinkState.EXPIRED], [LinkState.OPEN]), f"(before its expiry, at it, by the clock): {(before, at_expiry, by_clock)}"


# =============================================================================
# 3. REVOKE_LINK
# =============================================================================


async def _revocable_scene(engine: AsyncEngine, purpose: AccountTokenPurpose) -> IssuedToken:
    """An open link of ``purpose`` at NOW, for an account of the scene when the purpose acts on one."""
    owner = (await _add_users(engine, "owner"))["owner"]
    arguments: dict[str, Any] = {} if purpose == INVITE else {"user_id": owner}
    return await _issue(engine, purpose, now=NOW - timedelta(minutes=5), **arguments)


@pytest.mark.asyncio
@pytest.mark.parametrize("purpose", [INVITE, PASSWORD_RESET, EMAIL_VERIFICATION], ids=lambda purpose: purpose.value)
async def test_revoke_link_revokes_an_open_link_of_a_revocable_purpose_once(engine: AsyncEngine, purpose: AccountTokenPurpose) -> None:
    """Contract 3: ``revoked`` for an open invitation, reset link or verification link; its row revoked at ``now`` and not consumed; it then reads revoked; a second call ``not_found``, the revocation moment kept. A revoked invitation is out of ``list_pending_invites``."""
    print_section(f"Contract 3: revoke_link on an open {purpose.value}")
    issued = await _revocable_scene(engine, purpose)

    first = await _revoke_link(engine, issued.record.id)
    after_first = await _row(engine, issued.record.id)
    second = await _revoke_link(engine, issued.record.id, now=NOW + timedelta(minutes=1))

    assert (first, second) == ("revoked", "not_found"), f"revoking an open {purpose.value}: revoked, then not_found; got {(first, second)}"
    consumed_at, revoked_at = after_first
    assert consumed_at is None and revoked_at is not None and ensure_utc(revoked_at) == NOW, f"the row must be revoked at {NOW}, not consumed: {after_first}"
    assert await _row(engine, issued.record.id) == after_first, "a refused second revocation must keep the first moment"
    async with AsyncSession(engine) as session:
        assert (await inspect_token(session, issued.token, purpose)).status == TokenStatus.REVOKED
        if purpose == INVITE:
            assert issued.record.id not in {item.id for item in await registration_service.list_pending_invites(session, now=NOW)}, "a revoked invitation must leave the pending list"
    print_success(f"{purpose.value}: revoked once, not_found the second time")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["unknown", "used", "expired", "revoked", "retired", "expired-admin-setup"])
async def test_revoke_link_answers_not_found_for_what_is_not_an_open_link_and_changes_nothing(engine: AsyncEngine, kind: str) -> None:
    """Contract 3: an unknown id, a used, an expired, a revoked or a retired link → ``not_found``, and the row stays as it was. An expired setup link is ``not_found`` too: the state is read before the purpose.

    Presence barrier first: an open invitation of the same scene is revoked, or the ``not_found`` below would prove nothing.
    """
    owner = (await _add_users(engine, "owner"))["owner"]
    barrier = await _issue(engine, INVITE, now=NOW - timedelta(minutes=5))
    assert await _revoke_link(engine, barrier.record.id) == "revoked", "presence barrier: an open invitation must be revoked"
    target = NEVER_ISSUED_ID
    if kind == "used":
        issued = await _issue(engine, PASSWORD_RESET, now=NOW - timedelta(minutes=5), user_id=owner)
        await _consume(engine, issued, PASSWORD_RESET, owner, now=NOW - timedelta(minutes=4))
        target = issued.record.id
    elif kind == "expired":
        target = (await _issue(engine, INVITE, now=NOW - DEFAULT_TTL[INVITE] - timedelta(minutes=1))).record.id
    elif kind == "revoked":
        issued = await _issue(engine, EMAIL_VERIFICATION, now=NOW - timedelta(minutes=5), user_id=owner)
        await _revoke(engine, issued.record.id, now=NOW - timedelta(minutes=4))
        target = issued.record.id
    elif kind == "retired":
        target = (await _issue(engine, ADMIN_SETUP, now=NOW - timedelta(minutes=5), user_id=owner)).record.id
        await _retire(engine, owner, ADMIN_SETUP, now=NOW - timedelta(minutes=4))
    elif kind == "expired-admin-setup":
        target = (await _issue(engine, ADMIN_SETUP, now=NOW - DEFAULT_TTL[ADMIN_SETUP] - timedelta(minutes=1), user_id=owner)).record.id
    before = await _row(engine, target) if kind != "unknown" else None

    outcome = await _revoke_link(engine, target)

    assert outcome == "not_found", f"revoke_link on the {kind} link must answer not_found, got {outcome!r}"
    if before is not None:
        assert await _row(engine, target) == before, f"the {kind} link must stay as it was: {before} → {await _row(engine, target)}"


@pytest.mark.asyncio
@pytest.mark.parametrize("purpose", [ADMIN_SETUP, EMAIL_CHANGE], ids=lambda purpose: purpose.value)
async def test_revoke_link_refuses_an_open_link_of_another_purpose_and_changes_nothing(engine: AsyncEngine, purpose: AccountTokenPurpose) -> None:
    """Contract 3: an open setup link or owner's email change → ``not_revocable``; the row unchanged, the token still valid."""
    owner = (await _add_users(engine, "owner"))["owner"]
    issued = await _issue(engine, purpose, now=utcnow(), user_id=owner, **({"email": "owner-new@example.com"} if purpose == EMAIL_CHANGE else {}))
    before = await _row(engine, issued.record.id)

    outcome = await _revoke_link(engine, issued.record.id, now=utcnow())

    assert outcome == "not_revocable", f"an open {purpose.value} link: expected not_revocable, got {outcome!r}"
    assert await _row(engine, issued.record.id) == before == (None, None), f"the {purpose.value} link must stay open: {before} → {await _row(engine, issued.record.id)}"
    async with AsyncSession(engine) as session:
        assert (await inspect_token(session, issued.token, purpose)).status == TokenStatus.VALID, f"the {purpose.value} link must still work"


@pytest.mark.asyncio
async def test_revoke_link_flushes_and_does_not_commit(engine: AsyncEngine) -> None:
    """Contract 3: the caller commits — a rollback after ``revoked`` leaves the link open."""
    issued = await _revocable_scene(engine, INVITE)

    async with AsyncSession(engine) as session:
        outcome = await account_links.revoke_link(session, issued.record.id, now=NOW)
        await session.rollback()

    assert outcome == "revoked", f"setup: the open invitation must be revoked in the session, got {outcome!r}"
    assert await _row(engine, issued.record.id) == (None, None), "a rolled-back revocation must leave the link open"
    assert await _revoke_link(engine, issued.record.id) == "revoked", "the link is still open, and revocable"


def test_revocable_purposes_are_the_three_the_users_tab_revokes() -> None:
    """Contract 2/3: invitations, password resets and email verifications; never the setup link nor the owner's email change."""
    assert account_links.REVOCABLE_PURPOSES == frozenset({INVITE, PASSWORD_RESET, EMAIL_VERIFICATION})
