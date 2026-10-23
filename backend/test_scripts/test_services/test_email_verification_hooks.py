"""The hooks of email verification in workstream A's services (lot E5b, developer decision 44).

``test_api/test_email_verification_hooks_api.py`` pins the routes; this module pins the services they call, once the
hooks of E5b are in place. The contract:

1. ``registration_service.user_usage`` counts, besides the active accounts and the live invitations, the inactive
   accounts that wait for their email verification with a live link — once per account however many live links it
   holds; a link expired, revoked or consumed takes no place, and an active account is counted once, as active.
2. ``registration_service.register_user``, the option on: with an email with a link able to go out, the account is
   created inactive with its hold, an invitation spent, and the limit counts it (``USER_LIMIT_REACHED`` rolls it all
   back); without one, ``RegistrationError("EMAIL_VERIFICATION_UNAVAILABLE")`` and everything rolled back — no account,
   no token, the invitation still live.
3. ``user_service.update_user_status`` revokes the account's verification tokens when it changes ``is_active`` — an
   administrator decided —, and when it deactivates an account that waits, already inactive (revised 16/10, after the
   security review of E5b): its wait ends, committed and logged. An inactive account without links told inactive:
   nothing changes, nothing is committed or logged. Other purposes are untouched. ``user_service.set_user_active``
   revokes them either way: activating a waiting account makes it active, deactivating it ends its wait.
4. ``verification.holds_place(session, user)``: inactive with a live verification link (neither consumed, revoked nor
   expired at ``now``); ``verification.place_holders(session)`` is the set of such accounts' ids, each once.
5. ``settings_service._refuse_what_cannot_turn_on``: ``GlobalSettingUnavailableError(key, "EMAIL_VERIFICATION_UNAVAILABLE")``
   for ``require_email_verification`` going from off to on while no email with a link can go out; nothing for on → on,
   on → off, off → off, another setting, or when such an email can go.
6. ``verification.registration_email_verdict(address)``: whether the email of a registration may go, by two counters —
   the client address's (``delivery.ADDRESS_BUDGET``, shared with «send the link again» and «forgot password»: 20 an hour
   by default, or what ``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS`` says, read at every call so that a change is seen at
   once and no module is reloaded; keyed by workstream H's ``client_rate_key``, an IPv6 client by its /64, decision P17;
   none for a request without an address) and the instance's hourly budget (only while email is usable). Both are
   peeked first and the address's hit is recorded only when both admit, so a refused registration counts for nothing;
   a refusal carries the longest wait of the counters that refuse. A value that cannot be used never raises here (the
   startup checks report it, and email is off then): the default applies.

Pure: every database is a private SQLite file under ``tmp_path`` built with ``create_all`` and the default global
settings (NullPool, disposed at teardown); a new instance registers by invitation (workstream A), so the cases that
register without one set ``registration_mode`` to ``open`` in their file — never through ``LIBREFOLIO_REGISTRATION``,
which would lock it —, while the invited case keeps the default. Accounts are rows; tokens are issued by A's token
service with the ``now`` the case needs. An autouse fixture removes every inherited ``LIBREFOLIO_SMTP_*``,
``LIBREFOLIO_PUBLIC_URL``, ``LIBREFOLIO_BLOCKED``, ``LIBREFOLIO_MAX_USERS``, ``LIBREFOLIO_REGISTRATION`` and
``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS``. No server,
no SMTP conversation: the configuration is usable towards a host nothing connects to, and ``socket.getaddrinfo``
resolves the loopback only.

Red until E5b is applied (``holds_place``, ``place_holders``, ``GlobalSettingUnavailableError``).
"""

from __future__ import annotations

import os
import socket
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import AccountToken, AccountTokenPurpose, GlobalSetting, User
from backend.app.schemas.settings import SETTINGS_REGISTRY
from backend.app.services.accounts import registration_service, settings_service, token_service, user_service
from backend.app.services.accounts.registration_service import RegistrationError
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.accounts.token_service import DEFAULT_TTL, IssuedToken, TokenStatus
from backend.app.services.email import delivery, verification
from backend.app.services.platform.client_address import client_rate_key
from backend.app.utils.datetime_utils import utcnow
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.test_utils import print_section, print_success

SMTP_PREFIX = "LIBREFOLIO_SMTP_"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
MAX_USERS_VARIABLE = "LIBREFOLIO_MAX_USERS"
SIGNUP_PER_ADDRESS = "LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS"
#: The process's counter per client address, as shipped: the fixtures replace it with private ones.
SHIPPED_ADDRESS_BUDGET = delivery.ADDRESS_BUDGET
INHERITED = (PUBLIC_URL_VARIABLE, "LIBREFOLIO_BLOCKED", MAX_USERS_VARIABLE, "LIBREFOLIO_REGISTRATION", SIGNUP_PER_ADDRESS)
PUBLIC_URL = "https://folio.zq-public.example.com:8443/app"
LOOPBACK_NAMES = frozenset({"127.0.0.1", "::1", "localhost"})
OPTION_KEY = SETTINGS_REGISTRY.global_.REQUIRE_EMAIL_VERIFICATION.key
#: Who may register. A new instance registers by invitation (workstream A): the cases that register without one set it
#: to ``open`` in their private file, as an administrator would; the invited ones keep the default.
REGISTRATION_MODE_KEY = SETTINGS_REGISTRY.global_.REGISTRATION_MODE.key
OTHER_BOOL_KEY = SETTINGS_REGISTRY.global_.SCHEDULER_ENABLED.key
PASSWORD = "Hooks-Pass-2026"
VERIFICATION = AccountTokenPurpose.EMAIL_VERIFICATION
TTL = DEFAULT_TTL[VERIFICATION]


@pytest.fixture(autouse=True)
def _no_inherited_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.startswith(SMTP_PREFIX) or name in INHERITED:
            monkeypatch.delenv(name, raising=False)
    delivery._report_invalid.cache_clear()


@pytest.fixture(autouse=True)
def network(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    resolve = socket.getaddrinfo
    refused: list[str] = []

    def loopback_only(host: Any, *args: Any, **kwargs: Any) -> Any:
        name = host.decode() if isinstance(host, bytes) else host
        if name is not None and name not in LOOPBACK_NAMES:
            refused.append(str(name))
            raise socket.gaierror(socket.EAI_NONAME, f"these tests resolve the loopback only, not {name!r}")
        return resolve(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", loopback_only)
    return refused


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'hooks.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            await initialize_global_settings(session)
        yield engine
    finally:
        await engine.dispose()


def _links_can_go(monkeypatch: pytest.MonkeyPatch) -> None:
    """Email usable towards a host nothing connects to, and links ready."""
    monkeypatch.setenv(SMTP_PREFIX + "HOST", "smtp.zq-host.example.com")
    monkeypatch.setenv(SMTP_PREFIX + "FROM", "LibreFolio <noreply@example.com>")
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)


async def _add_user(engine: AsyncEngine, username: str, *, active: bool = True, admin: bool = False) -> User:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=f"{username}@example.com", hashed_password="marker-hash-not-bcrypt", is_active=active, is_superuser=admin)
        session.add(user)
        await session.commit()
    return user


async def _issue(engine: AsyncEngine, purpose: AccountTokenPurpose, **arguments: object) -> IssuedToken:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, purpose, **arguments)
        await session.commit()
    return issued


async def _link(engine: AsyncEngine, user: User, state: str, *, now: datetime) -> IssuedToken:
    """A verification link of the account: ``live``, ``expired``, ``revoked`` or ``consumed``."""
    created = now - TTL - timedelta(hours=1) if state == "expired" else now - timedelta(minutes=5)
    issued = await _issue(engine, VERIFICATION, user_id=user.id, email=user.email, now=created)
    if state in ("revoked", "consumed"):
        async with AsyncSession(engine) as session:
            if state == "consumed":
                assert await token_service.consume_token(session, issued.token, VERIFICATION, now=now) is not None
            else:
                assert await token_service.revoke_tokens(session, token_id=issued.record.id, now=now) == 1
            await session.commit()
    return issued


async def _option_on(engine: AsyncEngine) -> None:
    async with AsyncSession(engine) as session:
        await session.execute(update(GlobalSetting).where(GlobalSetting.key == OPTION_KEY).values(value="true"))
        await session.commit()


async def _registration_open(engine: AsyncEngine) -> None:
    """``registration_mode`` set to ``open`` in the private file: a registration without an invitation is admitted.

    A new instance registers by invitation (``GLOBAL_SETTINGS_DEFAULTS``, workstream A): only the cases that register
    without one call this, as an administrator opening registration would; the invited cases keep the default.
    ``LIBREFOLIO_REGISTRATION`` stays unset: it would lock the mode.
    """
    async with AsyncSession(engine) as session:
        result = await session.execute(update(GlobalSetting).where(GlobalSetting.key == REGISTRATION_MODE_KEY).values(value="open"))
        assert result.rowcount == 1, "setup: registration_mode was not seeded"
        await session.commit()


async def _status(engine: AsyncEngine, token: str, purpose: AccountTokenPurpose = VERIFICATION) -> TokenStatus:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return (await token_service.inspect_token(session, token, purpose)).status


async def _usage(engine: AsyncEngine, now: datetime) -> int:
    async with AsyncSession(engine) as session:
        return (await registration_service.user_usage(session, now=now)).used


# =============================================================================
# 1. user_usage
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case", "used"),
    [
        pytest.param("a-waiting-account-with-a-live-link", 2, id="a-waiting-account-with-a-live-link"),
        pytest.param("two-live-links-of-one-waiting-account", 2, id="two-live-links-of-one-account-count-once"),
        pytest.param("two-waiting-accounts", 3, id="two-waiting-accounts"),
        pytest.param("an-expired-link", 1, id="an-expired-link"),
        pytest.param("a-revoked-link", 1, id="a-revoked-link"),
        pytest.param("a-consumed-link", 1, id="a-consumed-link"),
        pytest.param("an-active-account-with-a-live-link", 2, id="an-active-account-counts-once"),
        pytest.param("a-live-invitation", 2, id="a-live-invitation-as-before"),
    ],
)
async def test_user_usage_counts_the_accounts_waiting_with_a_live_link(engine: AsyncEngine, case: str, used: int) -> None:
    """EVK-001 — contract 1: one active administrator, plus the case: the places taken."""
    print_section(f"EVK-001: {case}")
    now = utcnow()
    admin = await _add_user(engine, "zq_admin", admin=True)
    if case == "a-live-invitation":
        await _issue(engine, AccountTokenPurpose.INVITE, created_by_user_id=admin.id, now=now)
    elif case == "an-active-account-with-a-live-link":
        await _link(engine, await _add_user(engine, "zq_bob"), "live", now=now)
    else:
        vera = await _add_user(engine, "zq_vera", active=False)
        state = {"an-expired-link": "expired", "a-revoked-link": "revoked", "a-consumed-link": "consumed"}.get(case, "live")
        await _link(engine, vera, state, now=now)
        if case == "two-live-links-of-one-waiting-account":
            await _link(engine, vera, "live", now=now)
        if case == "two-waiting-accounts":
            await _link(engine, await _add_user(engine, "zq_wanda", active=False), "live", now=now)

    assert await _usage(engine, now) == used
    print_success(f"used {used}")


# =============================================================================
# 2. register_user
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("invited", [False, True])
async def test_register_user_rolls_back_when_no_email_with_a_link_can_go(engine: AsyncEngine, network: list[str], invited: bool) -> None:
    """EVK-002 — contract 2: the option on, email off: ``RegistrationError("EMAIL_VERIFICATION_UNAVAILABLE")``; no account, no verification token; an invitation given with it still live."""
    print_section(f"EVK-002: invited={invited}")
    admin = await _add_user(engine, "zq_admin", admin=True)
    await _option_on(engine)
    invitation = await _issue(engine, AccountTokenPurpose.INVITE, created_by_user_id=admin.id) if invited else None
    if not invited:
        await _registration_open(engine)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        with pytest.raises(RegistrationError) as refused:
            await registration_service.register_user(session, username="zq_vera", email="zq_vera@example.com", password=PASSWORD, invite_token=invitation.token if invitation else None)

    assert refused.value.code == "EMAIL_VERIFICATION_UNAVAILABLE"
    async with AsyncSession(engine) as session:
        assert (await session.execute(select(User).where(User.username == "zq_vera"))).first() is None
        assert (await session.execute(select(AccountToken).where(AccountToken.purpose == VERIFICATION))).first() is None
    if invitation is not None:
        assert await _status(engine, invitation.token, AccountTokenPurpose.INVITE) == TokenStatus.VALID
    assert network == []
    print_success("refused, all rolled back")


@pytest.mark.asyncio
async def test_register_user_holds_the_account_and_the_limit_counts_it(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """EVK-003 — contract 2: the option on, links able to go: the account is created inactive with one hold (no address); with ``LIBREFOLIO_MAX_USERS`` already reached by the administrator and that waiting account, the next registration is ``USER_LIMIT_REACHED`` and leaves nothing behind."""
    print_section("EVK-003: the hold and the limit")
    await _add_user(engine, "zq_admin", admin=True)
    await _option_on(engine)
    await _registration_open(engine)
    _links_can_go(monkeypatch)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        vera = await registration_service.register_user(session, username="zq_vera", email="zq_vera@example.com", password=PASSWORD)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        holds = list((await session.execute(select(AccountToken).where(AccountToken.purpose == VERIFICATION, AccountToken.user_id == vera.id))).scalars().all())
    monkeypatch.setenv(MAX_USERS_VARIABLE, "2")
    async with AsyncSession(engine, expire_on_commit=False) as session:
        with pytest.raises(RegistrationError) as full:
            await registration_service.register_user(session, username="zq_third", email="zq_third@example.com", password=PASSWORD)

    assert vera.is_active is False
    assert [(hold.email, hold.consumed_at, hold.revoked_at) for hold in holds] == [(None, None, None)]
    assert full.value.code == "USER_LIMIT_REACHED"
    async with AsyncSession(engine) as session:
        assert (await session.execute(select(User).where(User.username == "zq_third"))).first() is None
    print_success("inactive with its hold; the next one refused when full")


# =============================================================================
# 3. THE CHANGES OF STATUS
# =============================================================================


@pytest.mark.asyncio
async def test_update_user_status_revokes_the_verification_links_when_it_ends_a_wait(engine: AsyncEngine) -> None:
    """EVK-004 — contract 3: activating a waiting account revokes its verification links and makes it active; its live reset link is untouched. Deactivating an account that waits — already inactive — revokes its verification links too (revised 16/10, after the security review of E5b): its wait ends, committed, and «User status changed» is logged for it."""
    print_section("EVK-004: update_user_status")
    now = utcnow()
    vera = await _add_user(engine, "zq_vera", active=False)
    wanda = await _add_user(engine, "zq_wanda", active=False)
    first, second = await _link(engine, vera, "live", now=now), await _link(engine, vera, "live", now=now)
    reset = await _issue(engine, AccountTokenPurpose.PASSWORD_RESET, user_id=vera.id)
    ended = await _link(engine, wanda, "live", now=now)

    with capture_logs() as events:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            assert await user_service.update_user_status(session, await session.get(User, vera.id), is_active=True) is None
            assert await user_service.update_user_status(session, await session.get(User, wanda.id), is_active=False) is None

    assert [await _status(engine, issued.token) for issued in (first, second)] == [TokenStatus.REVOKED, TokenStatus.REVOKED]
    assert await _status(engine, reset.token, AccountTokenPurpose.PASSWORD_RESET) == TokenStatus.VALID
    assert await _status(engine, ended.token) == TokenStatus.REVOKED, "deactivating an account that waits ends its wait"
    async with AsyncSession(engine) as session:
        assert (await session.get(User, vera.id)).is_active is True
        assert (await session.get(User, wanda.id)).is_active is False
    changed = [event.get("user_id") for event in events if event.get("event") == "User status changed"]
    assert changed == [vera.id, wanda.id], events
    print_success("revoked on activation, and on deactivating a waiting account")


@pytest.mark.asyncio
async def test_deactivating_an_inactive_account_without_links_changes_nothing(engine: AsyncEngine) -> None:
    """EVK-009 — contract 3: an inactive account that does not wait — no verification link at all — told inactive again: nothing changes — its ``updated_at`` as it was, no commit of a change, no «User status changed» —; its live reset link untouched."""
    print_section("EVK-009: an inactive account, told inactive")
    xena = await _add_user(engine, "zq_xena", active=False)
    reset = await _issue(engine, AccountTokenPurpose.PASSWORD_RESET, user_id=xena.id)
    async with AsyncSession(engine) as session:
        updated_before = (await session.get(User, xena.id)).updated_at

    with capture_logs() as events:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            assert await user_service.update_user_status(session, await session.get(User, xena.id), is_active=False) is None

    async with AsyncSession(engine) as session:
        stored = await session.get(User, xena.id)
        assert (stored.is_active, stored.updated_at) == (False, updated_before)
    assert [event for event in events if event.get("event") == "User status changed"] == []
    assert await _status(engine, reset.token, AccountTokenPurpose.PASSWORD_RESET) == TokenStatus.VALID
    print_success("nothing changed, nothing logged")


class FakeClock:
    """A clock that moves only when the test sets it: ``clock.now = …``."""

    def __init__(self, start: float = 1_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


START = 1_000.0


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def address_budget(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> SlidingWindowLimiter:
    """The counter per client address, private and on the fake clock. Its own limit is not what decides (the variable is): it is built for far more than any test spends."""
    limiter = SlidingWindowLimiter(1000, 3600, clock=clock)
    monkeypatch.setattr(delivery, "ADDRESS_BUDGET", limiter)
    return limiter


@pytest.fixture
def instance_budget(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> SlidingWindowLimiter:
    """The hourly budget of the instance, private and on the fake clock, with the shipped 50."""
    limiter = SlidingWindowLimiter(50, 3600, max_keys=1, clock=clock)
    monkeypatch.setattr(delivery, "INSTANCE_BUDGET", limiter)
    return limiter


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("first", "last", "limited"),
    [
        pytest.param("198.51.100.7", "198.51.100.7", True, id="ipv4-the-21st-of-the-hour-held"),
        pytest.param("2001:db8:1:2::10", "2001:db8:1:2:ffff::1", True, id="ipv6-one-64-is-one-client"),
        pytest.param("198.51.100.7", "203.0.113.9", False, id="another-address-is-another-count"),
        pytest.param(None, None, False, id="no-address-not-limited"),
    ],
)
async def test_registration_emails_are_counted_per_client_address(monkeypatch: pytest.MonkeyPatch, clock: FakeClock, address_budget: SlidingWindowLimiter, first: str | None, last: str | None, limited: bool) -> None:
    """EVK-010 — E5b, after the security review, E-26: ``registration_email_verdict(address)`` admits twenty registration emails an hour per client address (the default of ``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS``) — keyed by workstream H's ``client_rate_key`` (decision P17), an IPv6 client by its /64 — and refuses the 21st, a refused one counted for nothing and its wait ``3600 - 60`` seconds; past the hour of the first twenty, the address is admitted again. Another address has a count of its own; a request without an address is not limited by it. The shipped counter is built for 20 an hour."""
    print_section(f"EVK-010: {first} then {last}")
    assert (SHIPPED_ADDRESS_BUDGET.limit, SHIPPED_ADDRESS_BUDGET.window_seconds) == (20, 3600), "the shipped limit"
    clock.now = START

    admitted = [(await verification.registration_email_verdict(first)).allowed for _registration in range(20)]
    clock.now = START + 60
    later = [await verification.registration_email_verdict(last) for _registration in range(2)]
    key = client_rate_key(last)
    counted = address_budget.count(key) if key is not None else len(address_budget)
    clock.now = START + 3600 + 1
    past_the_hour = await verification.registration_email_verdict(last)

    assert admitted == [True] * 20
    assert [verdict.allowed for verdict in later] == ([False, False] if limited else [True, True])
    if limited:
        assert [(verdict.by_address, verdict.by_instance, verdict.retry_after) for verdict in later] == [(True, False, pytest.approx(3600 - 60))] * 2
    assert counted == (20 if limited else 2 if key is not None else 0), "a refused one counts for nothing; no address, no count"
    assert past_the_hour.allowed is True
    print_success("limited" if limited else "not limited")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("configured", "limit"),
    [
        pytest.param(None, 20, id="unset-is-20"),
        pytest.param("", 20, id="empty-is-20"),
        pytest.param("   ", 20, id="spaces-are-20"),
        pytest.param("3", 3, id="3-holds-the-4th"),
        pytest.param(" 7 ", 7, id="stripped"),
        pytest.param("1", 1, id="1-holds-the-2nd"),
    ],
)
async def test_the_limit_of_registration_emails_comes_from_the_variable(monkeypatch: pytest.MonkeyPatch, address_budget: SlidingWindowLimiter, configured: str | None, limit: int) -> None:
    """EVK-011 — ``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS`` sets how many registration emails one client address may send in the hour — 20 unset, empty or blank — and the one after the last is held. The variable is set after the module was imported, on a private counter whose own limit is NOT the configured one: the limit is read from the environment when the registration asks."""
    print_section(f"EVK-011: {configured!r} → {limit}")
    if configured is not None:
        monkeypatch.setenv(SIGNUP_PER_ADDRESS, configured)
    address = "198.51.100.7"

    admitted = [(await verification.registration_email_verdict(address)).allowed for _registration in range(limit)]
    after = await verification.registration_email_verdict(address)

    assert admitted == [True] * limit
    assert after.allowed is False, f"the registration {limit + 1} of the hour was admitted"
    print_success(f"{limit} admitted, the next one held")


@pytest.mark.asyncio
async def test_a_change_of_the_variable_is_seen_at_the_next_registration(monkeypatch: pytest.MonkeyPatch, address_budget: SlidingWindowLimiter) -> None:
    """EVK-012 — the limit is read at every call, as ``send_email`` reads the hourly budget: with the variable at 2 the third registration is held; raised to 3, the next one is admitted (the two counted stay counted, the refused one did not count); lowered to 1, the address is held again."""
    print_section("EVK-012: the variable changes between registrations")
    address = "198.51.100.7"
    monkeypatch.setenv(SIGNUP_PER_ADDRESS, "2")

    first_two = [(await verification.registration_email_verdict(address)).allowed for _registration in range(2)]
    third = (await verification.registration_email_verdict(address)).allowed
    monkeypatch.setenv(SIGNUP_PER_ADDRESS, "3")
    raised = (await verification.registration_email_verdict(address)).allowed
    monkeypatch.setenv(SIGNUP_PER_ADDRESS, "1")
    lowered = (await verification.registration_email_verdict(address)).allowed

    assert (first_two, third, raised, lowered) == ([True, True], False, True, False)
    print_success("2 then 3 then 1, each seen at once")


@pytest.mark.asyncio
@pytest.mark.parametrize("configured", ["0", "-1", "abc", "1.5"])
async def test_a_variable_that_cannot_be_used_never_breaks_a_registration(monkeypatch: pytest.MonkeyPatch, address_budget: SlidingWindowLimiter, configured: str) -> None:
    """EVK-013 — a value that cannot be used is reported by the startup checks (``email.smtp``), and email is off then: ``registration_email_verdict`` does not raise (the account already exists when it is asked) and applies the default of 20."""
    print_section(f"EVK-013: {configured!r}")
    monkeypatch.setenv(SIGNUP_PER_ADDRESS, configured)
    address = "198.51.100.7"

    admitted = [(await verification.registration_email_verdict(address)).allowed for _registration in range(20)]
    after = await verification.registration_email_verdict(address)

    assert admitted == [True] * 20 and after.allowed is False
    print_success("default 20, no exception")


@pytest.mark.asyncio
async def test_the_instance_budget_spent_holds_the_registration_and_the_address_counts_nothing(monkeypatch: pytest.MonkeyPatch, clock: FakeClock, address_budget: SlidingWindowLimiter, instance_budget: SlidingWindowLimiter) -> None:
    """EVK-014 — E-26: with email usable and the hourly budget of the instance spent (``LIBREFOLIO_SMTP_MAX_PER_HOUR=1``, its unit taken at START), a registration from an address whose own counter is empty is held, by the instance alone, with the budget's wait (at START + 100: ``3600 - 100``); the address's counter, peeked first and hit only when the email may go, counts nothing; the budget itself is peeked, never spent by the verdict."""
    print_section("EVK-014: instance budget spent")
    _links_can_go(monkeypatch)
    monkeypatch.setenv(SMTP_PREFIX + "MAX_PER_HOUR", "1")
    clock.now = START
    assert instance_budget.hit(limit=1).allowed, "setup: the only unit of the hour"
    clock.now = START + 100

    verdict = await verification.registration_email_verdict("198.51.100.7")

    assert (verdict.allowed, verdict.by_address, verdict.by_instance) == (False, False, True)
    assert verdict.retry_after == pytest.approx(3600 - 100)
    assert (len(address_budget), instance_budget.count()) == (0, 1), "nothing counted for the address, nothing more spent by the instance"
    print_success("held by the instance, the address's counter untouched")


@pytest.mark.asyncio
async def test_a_registration_stopped_by_both_counters_says_the_longest_wait(monkeypatch: pytest.MonkeyPatch, clock: FakeClock, address_budget: SlidingWindowLimiter, instance_budget: SlidingWindowLimiter) -> None:
    """EVK-015 — E-26: the address's counter full since START (``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS=1``), the instance's budget (``LIBREFOLIO_SMTP_MAX_PER_HOUR=1``) spent at START + 1000: at START + 1500 the registration is held by both, and its wait is the longest, the instance's ``3600 - 500`` (not the address's ``3600 - 1500``). Neither counter changes."""
    print_section("EVK-015: both counters, the longest wait")
    _links_can_go(monkeypatch)
    monkeypatch.setenv(SMTP_PREFIX + "MAX_PER_HOUR", "1")
    monkeypatch.setenv(SIGNUP_PER_ADDRESS, "1")
    address = "198.51.100.7"
    clock.now = START
    assert (await verification.registration_email_verdict(address)).allowed, "setup: the address's only unit"
    clock.now = START + 1000
    assert instance_budget.hit(limit=1).allowed, "setup: the only unit of the hour"
    clock.now = START + 1500

    verdict = await verification.registration_email_verdict(address)

    assert (verdict.allowed, verdict.by_address, verdict.by_instance) == (False, True, True)
    assert verdict.retry_after == pytest.approx(3600 - 500)
    assert (address_budget.count(client_rate_key(address)), instance_budget.count()) == (1, 1)
    print_success("held by both, 3100 s: the longest")


@pytest.mark.asyncio
async def test_an_admitted_registration_spends_the_address_and_not_the_instance(monkeypatch: pytest.MonkeyPatch, address_budget: SlidingWindowLimiter, instance_budget: SlidingWindowLimiter) -> None:
    """EVK-016 — E-26: with email usable and both counters free, the verdict is allowed with no wait, hits the address's counter once and leaves the instance's budget alone (``send_email`` spends it when the email goes)."""
    print_section("EVK-016: admitted")
    _links_can_go(monkeypatch)
    address = "198.51.100.7"

    verdict = await verification.registration_email_verdict(address)

    assert (verdict.allowed, verdict.retry_after, verdict.by_address, verdict.by_instance) == (True, 0.0, False, False)
    assert (address_budget.count(client_rate_key(address)), instance_budget.count()) == (1, 0)
    print_success("allowed: one hit for the address, none for the instance")


@pytest.mark.asyncio
async def test_without_an_address_only_the_instance_budget_can_hold_a_registration(monkeypatch: pytest.MonkeyPatch, clock: FakeClock, address_budget: SlidingWindowLimiter, instance_budget: SlidingWindowLimiter) -> None:
    """EVK-017 — E-26: a request without an address (a unix socket, or behind a proxy nobody trusts) is not limited by the address's counter, which holds no key for it; the instance's spent budget still holds it, by the instance alone."""
    print_section("EVK-017: no address")
    _links_can_go(monkeypatch)
    monkeypatch.setenv(SMTP_PREFIX + "MAX_PER_HOUR", "1")
    monkeypatch.setenv(SIGNUP_PER_ADDRESS, "1")

    free = [(await verification.registration_email_verdict(None)).allowed for _registration in range(3)]
    clock.now = START
    assert instance_budget.hit(limit=1).allowed, "setup: the only unit of the hour"
    held = await verification.registration_email_verdict(None)

    assert free == [True] * 3 and len(address_budget) == 0
    assert (held.allowed, held.by_address, held.by_instance) == (False, False, True)
    print_success("no key for the address; the instance still holds")


@pytest.mark.asyncio
async def test_with_email_off_the_instance_budget_is_not_consulted(monkeypatch: pytest.MonkeyPatch, address_budget: SlidingWindowLimiter, instance_budget: SlidingWindowLimiter) -> None:
    """EVK-018 — E-26: with email not usable (no server; a registration with the option on is refused before it gets here) the instance's budget is not looked at, and the verdict is the address's alone — as before the budget counted."""
    print_section("EVK-018: email off")
    assert instance_budget.hit(limit=1).allowed, "setup: spend the first unit of a budget of one"

    verdict = await verification.registration_email_verdict("198.51.100.7")

    assert verdict.allowed is True
    print_success("allowed: the address's counter alone")


@pytest.mark.asyncio
@pytest.mark.parametrize("active", [True, False])
async def test_set_user_active_revokes_the_verification_links_either_way(engine: AsyncEngine, active: bool) -> None:
    """EVK-005 — contract 3: ``set_user_active`` on a waiting account: its verification links are revoked whichever way; activated it is active, deactivated it no longer waits."""
    print_section(f"EVK-005: set_user_active({active})")
    now = utcnow()
    vera = await _add_user(engine, "zq_vera", active=False)
    link = await _link(engine, vera, "live", now=now)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        assert await user_service.set_user_active(session, "zq_vera", active) == (True, None)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        account = await session.get(User, vera.id)
        waits = await verification.awaiting_verification(session, account)

    assert await _status(engine, link.token) == TokenStatus.REVOKED
    assert (account.is_active, waits) == (active, False)
    print_success("revoked; active" if active else "revoked; the wait is over")


# =============================================================================
# 4. holds_place AND place_holders
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("active", "state", "holds"),
    [
        pytest.param(False, "live", True, id="inactive-with-a-live-link"),
        pytest.param(False, "expired", False, id="inactive-with-an-expired-link"),
        pytest.param(False, "revoked", False, id="inactive-with-a-revoked-link"),
        pytest.param(False, "consumed", False, id="inactive-with-a-consumed-link"),
        pytest.param(False, None, False, id="inactive-without-a-link"),
        pytest.param(True, "live", False, id="active-with-a-live-link"),
    ],
)
async def test_holds_place_and_place_holders(engine: AsyncEngine, active: bool, state: str | None, holds: bool) -> None:
    """EVK-006 — contract 4: ``holds_place`` is true only for an inactive account with a live verification link; ``place_holders`` lists exactly such accounts, once each."""
    print_section(f"EVK-006: active={active}, {state}")
    now = utcnow()
    vera = await _add_user(engine, "zq_vera", active=active)
    if state is not None:
        await _link(engine, vera, state, now=now)
        if state == "live":
            await _link(engine, vera, "live", now=now)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        held = await verification.holds_place(session, await session.get(User, vera.id), now=now)
        holders = await verification.place_holders(session, now=now)

    assert held is holds
    assert holders == ({vera.id} if holds else set())
    print_success(f"holds_place {holds}")


@pytest.mark.asyncio
async def test_a_link_stops_holding_its_place_when_it_expires(engine: AsyncEngine) -> None:
    """EVK-007 — contract 4: the same live link holds the place before its expiry and not after it: ``now`` decides."""
    print_section("EVK-007: at expiry")
    now = utcnow()
    vera = await _add_user(engine, "zq_vera", active=False)
    link = await _link(engine, vera, "live", now=now)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(User, vera.id)
        before = await verification.holds_place(session, user, now=link.record.expires_at - timedelta(seconds=1))
        after = await verification.holds_place(session, user, now=link.record.expires_at + timedelta(seconds=1))

    assert (before, after) == (True, False)
    print_success("held, then freed")


# =============================================================================
# 5. _refuse_what_cannot_turn_on
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("key", "stored", "new", "can_go", "refused"),
    [
        pytest.param(OPTION_KEY, "false", "true", False, True, id="off-to-on-without-email-refused"),
        pytest.param(OPTION_KEY, "false", "true", True, False, id="off-to-on-with-email"),
        pytest.param(OPTION_KEY, "true", "true", False, False, id="on-again-without-email"),
        pytest.param(OPTION_KEY, "true", "false", False, False, id="on-to-off-without-email"),
        pytest.param(OPTION_KEY, "false", "false", False, False, id="off-to-off"),
        pytest.param(OTHER_BOOL_KEY, "false", "true", False, False, id="another-setting"),
    ],
)
async def test_only_turning_verification_on_needs_an_email_with_a_link(monkeypatch: pytest.MonkeyPatch, network: list[str], key: str, stored: str, new: str, can_go: bool, refused: bool) -> None:
    """EVK-008 — contract 5: ``GlobalSettingUnavailableError`` with the key and ``EMAIL_VERIFICATION_UNAVAILABLE`` only for the option going off → on with no email with a link able to go out."""
    print_section(f"EVK-008: {key} {stored} → {new}, can_go={can_go}")
    if can_go:
        _links_can_go(monkeypatch)
    rows = {key: GlobalSetting(key=key, value=stored, value_type="bool")}

    if refused:
        with pytest.raises(settings_service.GlobalSettingUnavailableError) as error:
            await settings_service._refuse_what_cannot_turn_on(rows, [key], [new])
        assert (error.value.key, error.value.code) == (key, "EMAIL_VERIFICATION_UNAVAILABLE")
    else:
        assert await settings_service._refuse_what_cannot_turn_on(rows, [key], [new]) is None
    assert network == []
    print_success("refused" if refused else "allowed")
