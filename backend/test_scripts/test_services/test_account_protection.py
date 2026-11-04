"""A5-1: on a managed instance the paying administrator cannot be removed (release 1.3, workstream A, lot A5-1).

The hook of lot A7, ``user_service.account_protection(user) -> Optional[str]``, was a stub that protected nobody. Now:

- ``config.accounts.owner_admin_email()`` reads ``LIBREFOLIO_ADMIN_EMAIL`` at every call: the value stripped, ``None`` when
  it is unset, blank or not an address. Unlike ``admin_bootstrap_config()`` it NEVER raises: it is asked on every request
  that touches an account, and a bad variable is the startup audit's business.
- ``account_protection(user)`` answers ``PAYING_ADMINISTRATOR`` (``"paying_administrator"``) for the account whose email is
  that address (A-Z case aside, ``same_email``) when ``get_settings().LIBREFOLIO_PROFILE`` is ``managed``; ``None`` for
  every other account and for every account in any other profile. By email alone: administrator or not.
- The command line (``./dev.py user deactivate``, and the demotion) calls the services directly and stays ABOVE the protection:
  it is the emergency exit of the operator of the server. It has no delete command.

Cases: UPROT-001 the reader; UPROT-002 the hook with the profile managed; UPROT-003 the hook in the other profile and with
a variable it cannot use; UPROT-010 and UPROT-011 the command line can still deactivate and demote the owner, the
protection being live (barrier); UPROT-012 so can the service that deletes.

Pure: no lane database, no server. The hook cases build ``User`` objects in memory; the command-line cases use a private
SQLite file under ``tmp_path`` (``create_all``), the command line run in this process on that file with ``get_async_engine``
replaced. The profile and the variable are set with ``monkeypatch`` (``get_settings()`` reads the environment at every call;
test mode keeps ``.env`` out of it), and every case checks with a barrier that ``get_settings()`` reads the profile it set.
"""

from __future__ import annotations

import importlib
from collections.abc import AsyncIterator
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.api.v1 import users as users_api
from backend.app.config import accounts, get_settings
from backend.app.db.base import SQLModel  # imports every model
from backend.app.db.models import User
from backend.app.services.accounts import auth_service, user_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.test_scripts.test_utils import print_section, print_success

PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
ADMIN_EMAIL_VARIABLE = "LIBREFOLIO_ADMIN_EMAIL"
#: The reason, as the API sends it in ``detail.reason``: written out, a stable word.
REASON = "paying_administrator"
OWNER_EMAIL = "owner.a51@example.com"
USER_CLI_MODULE = "scripts.user_cli"


def _configure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, profile: Optional[str], admin_email: Optional[str]) -> None:
    """Make ``get_settings()`` read the profile ``profile`` (None: unset) and the variable ``admin_email`` (None: unset) from this environment alone."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")  # no .env read: only this environment
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv(PROFILE_VARIABLE, raising=False)
    monkeypatch.delenv(ADMIN_EMAIL_VARIABLE, raising=False)
    if profile is not None:
        monkeypatch.setenv(PROFILE_VARIABLE, profile)
    if admin_email is not None:
        monkeypatch.setenv(ADMIN_EMAIL_VARIABLE, admin_email)
    expected = profile or "selfhosted"
    resolved = get_settings().LIBREFOLIO_PROFILE
    assert resolved == expected, f"barrier: with {PROFILE_VARIABLE}={profile!r}, get_settings() reads the profile {resolved!r}, not {expected!r}"


def _reader() -> Any:
    """``config.accounts.owner_admin_email``, read when the case asks for it: before it exists, that case fails here."""
    reader = getattr(accounts, "owner_admin_email", None)
    if reader is None:
        pytest.fail("A5-1: backend.app.config.accounts has no owner_admin_email()")
    return reader


def _account(email: str, *, admin: bool = False, username: str = "someone") -> User:
    """An account in memory: the hook reads the address and nothing else."""
    return User(id=1, username=username, email=email, hashed_password="x", is_superuser=admin, is_active=True)


# =============================================================================
# THE READER
# =============================================================================


@pytest.mark.parametrize(
    ("written", "expected"),
    [
        pytest.param(OWNER_EMAIL, OWNER_EMAIL, id="an-address"),
        pytest.param(f"  {OWNER_EMAIL}  ", OWNER_EMAIL, id="spaces-are-stripped"),
        pytest.param(None, None, id="unset"),
        pytest.param("", None, id="empty"),
        pytest.param("   ", None, id="blank"),
        pytest.param("not-an-address", None, id="not-an-address"),
        pytest.param("two@@example.com", None, id="two-ats"),
        pytest.param("@example.com", None, id="no-local-part"),
    ],
)
def test_owner_admin_email_reads_the_variable_and_never_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, written: Optional[str], expected: Optional[str]) -> None:
    """UPROT-001: ``owner_admin_email()`` answers the variable stripped when it is an address, ``None`` when it is unset, blank or not an address; it never raises (``admin_bootstrap_config()`` does, for the same values)."""
    print_section(f"UPROT-001: owner_admin_email() with {written!r}")
    _configure(monkeypatch, tmp_path, profile="managed", admin_email=written)

    answer = _reader()()

    assert answer == expected, f"{ADMIN_EMAIL_VARIABLE}={written!r}: expected {expected!r}, got {answer!r}"
    print_success(f"{written!r} → {answer!r}")


def test_owner_admin_email_is_read_at_every_call(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """UPROT-001b: the variable is read at every call, never cached: set, changed, then removed, the answer follows."""
    _configure(monkeypatch, tmp_path, profile="managed", admin_email=OWNER_EMAIL)
    reader = _reader()
    first = reader()
    monkeypatch.setenv(ADMIN_EMAIL_VARIABLE, "other.a51@example.com")
    second = reader()
    monkeypatch.delenv(ADMIN_EMAIL_VARIABLE)
    third = reader()
    assert (first, second, third) == (OWNER_EMAIL, "other.a51@example.com", None), f"the reader must follow the environment: {(first, second, third)}"


# =============================================================================
# THE HOOK
# =============================================================================


@pytest.mark.parametrize("admin", [pytest.param(True, id="administrator"), pytest.param(False, id="ordinary-account")])
@pytest.mark.parametrize("typed", [pytest.param(OWNER_EMAIL, id="same-case"), pytest.param(OWNER_EMAIL.upper(), id="upper-case"), pytest.param(OWNER_EMAIL.title(), id="capitalized")])
def test_managed_protects_the_account_of_the_variable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, typed: str, admin: bool) -> None:
    """UPROT-002: managed, ``LIBREFOLIO_ADMIN_EMAIL`` an address: the account with that address — any A-Z case, administrator or not — has the reason ``paying_administrator``; the constant is exported next to the function. Barrier: an account with another address has none."""
    print_section(f"UPROT-002: managed, the account {typed!r}")
    _configure(monkeypatch, tmp_path, profile="managed", admin_email=OWNER_EMAIL)

    reason = user_service.account_protection(_account(typed, admin=admin))
    other = user_service.account_protection(_account("someone.else.a51@example.com", admin=admin))

    assert getattr(user_service, "PAYING_ADMINISTRATOR", None) == REASON, f"user_service.PAYING_ADMINISTRATOR must be {REASON!r}: {getattr(user_service, 'PAYING_ADMINISTRATOR', '<missing>')!r}"
    assert reason == REASON, f"the account {typed!r} on a managed instance must be protected with {REASON!r}, got {reason!r}"
    assert other is None, f"Barrier: another address must not be protected, got {other!r}"
    print_success(f"{typed!r} → {reason}")


def test_managed_protects_nobody_else_and_a_prefix_is_not_the_address(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """UPROT-002b: managed: an address that merely contains, starts with or ends like the variable's is not the account; and a non-ASCII twin (``fold`` is A-Z only) is not either."""
    _configure(monkeypatch, tmp_path, profile="managed", admin_email=OWNER_EMAIL)
    barrier = user_service.account_protection(_account(OWNER_EMAIL))
    assert barrier == REASON, f"Barrier: the owner itself must be protected, got {barrier!r}"
    near = [f"x{OWNER_EMAIL}", f"{OWNER_EMAIL}.x", OWNER_EMAIL.replace("owner", "owne"), OWNER_EMAIL.replace("a51", "á51")]
    answers = {address: user_service.account_protection(_account(address)) for address in near}
    assert all(answer is None for answer in answers.values()), f"only the address itself is protected: {answers}"


@pytest.mark.parametrize("profile", [pytest.param(None, id="profile-unset"), pytest.param("selfhosted", id="selfhosted")])
def test_another_profile_protects_nobody(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile: Optional[str]) -> None:
    """UPROT-003: the default (selfhosted) profile with ``LIBREFOLIO_ADMIN_EMAIL`` set to the account's own address: ``None`` for everybody. Regression zero."""
    _configure(monkeypatch, tmp_path, profile=profile, admin_email=OWNER_EMAIL)
    assert _reader()() == OWNER_EMAIL, "Barrier: the variable is set and readable, so only the profile can be what protects nobody"

    answers = [user_service.account_protection(_account(OWNER_EMAIL, admin=admin)) for admin in (True, False)]

    assert answers == [None, None], f"profile {profile!r}: nobody is protected, got {answers}"


@pytest.mark.parametrize("written", [pytest.param(None, id="unset"), pytest.param("", id="empty"), pytest.param("   ", id="blank"), pytest.param("not-an-address", id="not-an-address")])
def test_managed_without_a_usable_variable_protects_nobody_and_raises_nothing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, written: Optional[str]) -> None:
    """UPROT-003b: managed, ``LIBREFOLIO_ADMIN_EMAIL`` unset, blank or not an address: ``None`` for an account of any address, and no exception (the hook runs on every request that touches an account)."""
    _configure(monkeypatch, tmp_path, profile="managed", admin_email=written)

    answers = [user_service.account_protection(_account(address)) for address in (OWNER_EMAIL, "not-an-address", "")]

    assert answers == [None, None, None], f"managed with {written!r}: nobody is protected, got {answers}"


# =============================================================================
# THE COMMAND LINE STAYS ABOVE THE PROTECTION
# =============================================================================


@pytest_asyncio.fixture
async def engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file with the whole ORM schema and the global settings the startup seeds; disposed at teardown. bcrypt at cost 4."""
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)
    private = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'protection.db'}", poolclass=NullPool)
    try:
        async with private.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(private) as session:
            await initialize_global_settings(session)
        yield private
    finally:
        await private.dispose()


@pytest.fixture
def user_cli(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """``scripts/user_cli.py`` in this process, its ``get_async_engine`` the private file's engine."""
    module = importlib.import_module(USER_CLI_MODULE)
    monkeypatch.setattr(module, "get_async_engine", lambda: engine)
    return module


async def _admins(engine: AsyncEngine) -> tuple[int, int]:
    """The owner (the address of the variable) and a second active administrator, written as rows; their ids."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        owner = User(username="a51_owner", email=OWNER_EMAIL, hashed_password=auth_service.hash_password("Cli-Protection-2026"), is_active=True, is_superuser=True)
        peer = User(username="a51_peer", email="peer.a51@example.com", hashed_password=auth_service.hash_password("Cli-Protection-2026"), is_active=True, is_superuser=True)
        session.add_all([owner, peer])
        await session.commit()
        return owner.id, peer.id


async def _state(engine: AsyncEngine, user_id: int) -> Optional[tuple[bool, bool]]:
    """(is_active, is_superuser) of the committed row; None when there is none."""
    async with AsyncSession(engine) as session:
        row = (await session.execute(select(User.is_active, User.is_superuser).where(User.id == user_id))).one_or_none()
    return None if row is None else (bool(row[0]), bool(row[1]))


async def _protection_of(engine: AsyncEngine, user_id: int) -> Optional[str]:
    async with AsyncSession(engine) as session:
        user = await session.get(User, user_id)
        assert user is not None
        return user_service.account_protection(user)


@pytest.mark.asyncio
async def test_the_command_line_deactivates_the_protected_owner(engine: AsyncEngine, user_cli: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """UPROT-010: managed, the owner (an active administrator, with another active administrator in the instance) is protected — barrier —, and ``cmd_set_user_active(owner, False)`` (``./dev.py user deactivate``) still deactivates it: truthy, the row inactive. The operator of the server is above the protection."""
    print_section("UPROT-010: the command line deactivates the owner")
    _configure(monkeypatch, tmp_path, profile="managed", admin_email=OWNER_EMAIL)
    owner_id, _ = await _admins(engine)
    protection = await _protection_of(engine, owner_id)
    assert protection == REASON, f"Barrier: the owner must be protected while this case runs, or it proves nothing: {protection!r}"

    answer = await user_cli.cmd_set_user_active("a51_owner", False)

    assert answer is True, f"the command line must deactivate the protected owner, got {answer!r}"
    assert await _state(engine, owner_id) == (False, True), "the owner must be inactive and still an administrator"
    print_success("deactivated from the command line")


@pytest.mark.asyncio
async def test_the_command_line_demotes_the_protected_owner(engine: AsyncEngine, user_cli: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """UPROT-011: as UPROT-010 for ``cmd_set_admin(owner, False)`` (the demotion by the command line): truthy, the row no longer an administrator, still active."""
    print_section("UPROT-011: the command line demotes the owner")
    _configure(monkeypatch, tmp_path, profile="managed", admin_email=OWNER_EMAIL)
    owner_id, _ = await _admins(engine)
    protection = await _protection_of(engine, owner_id)
    assert protection == REASON, f"Barrier: the owner must be protected while this case runs, or it proves nothing: {protection!r}"

    answer = await user_cli.cmd_set_admin("a51_owner", False)

    assert answer is True, f"the command line must demote the protected owner, got {answer!r}"
    assert await _state(engine, owner_id) == (True, False), "the owner must be active and no longer an administrator"
    print_success("demoted from the command line")


@pytest.mark.asyncio
async def test_the_service_deletes_the_protected_owner(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """UPROT-012: the service that deletes an account (``delete_user``, which the API reaches after its own check) does not look at the protection: it is the route's, so the operator's tools above the route stay free. The owner is protected — barrier — and ``delete_user`` removes it."""
    print_section("UPROT-012: delete_user does not ask the hook")
    _configure(monkeypatch, tmp_path, profile="managed", admin_email=OWNER_EMAIL)
    owner_id, peer_id = await _admins(engine)
    protection = await _protection_of(engine, owner_id)
    assert protection == REASON, f"Barrier: the owner must be protected while this case runs, or it proves nothing: {protection!r}"

    async with AsyncSession(engine) as session:
        deleted = await user_service.delete_user(session, owner_id)

    assert deleted is not None, "delete_user must delete the account"
    assert await _state(engine, owner_id) is None, "the owner must be gone"
    assert await _state(engine, peer_id) == (True, True), "the other administrator must be untouched"


@pytest.mark.asyncio
async def test_the_command_line_and_the_services_still_reset_end_sessions_and_change_the_email(engine: AsyncEngine, user_cli: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """UPROT-013 (A5-1 extension): managed, the owner protected — barrier —: ``cmd_reset_password`` and ``cmd_reset_link`` (``./dev.py user reset`` / ``reset-link``) succeed, ``cmd_set_email`` changes the address (and ends the sessions: the version rises), and ``user_service.end_sessions`` ends the sessions: the routes that refuse these for the owner (409 ACCOUNT_PROTECTED) are the app's, the operator on the server stays above them."""
    print_section("UPROT-013: the command line resets, links, changes the email")
    _configure(monkeypatch, tmp_path, profile="managed", admin_email=OWNER_EMAIL)
    owner_id, _ = await _admins(engine)
    protection = await _protection_of(engine, owner_id)
    assert protection == REASON, f"Barrier: the owner must be protected while this case runs, or it proves nothing: {protection!r}"

    async def version() -> int:
        async with AsyncSession(engine) as session:
            return int((await session.execute(select(User.session_version).where(User.id == owner_id))).scalar_one())

    start = await version()
    reset = await user_cli.cmd_reset_password("a51_owner", "Cli-Reset-2026!x")
    after_reset = await version()
    link = await user_cli.cmd_reset_link("a51_owner")
    moved = await user_cli.cmd_set_email("a51_owner", "owner.moved.a51@example.com")
    after_email = await version()
    async with AsyncSession(engine) as session:
        owner = await session.get(User, owner_id)
        assert owner is not None
        await user_service.end_sessions(session, owner)
        await session.commit()
    capsys.readouterr()

    assert (reset, link, moved) == (True, True, True), f"the command line must reset, link and change the email of the protected owner: {(reset, link, moved)}"
    assert after_reset > start and after_email > after_reset, f"the password reset and the email change end the sessions: {start}, {after_reset}, {after_email}"
    assert await version() > after_email, "the service must end the sessions of the protected owner"
    async with AsyncSession(engine) as session:
        stored = (await session.execute(select(User.email).where(User.id == owner_id))).scalar_one()
    assert stored == "owner.moved.a51@example.com", f"the address must be the new one: {stored!r}"


# =============================================================================
# A-63 (c): THE PROFILE AND THE OWNER ARE READ ONCE FOR A LIST, NOT ONCE PER ROW
# =============================================================================


def _count_settings_reads(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Replace ``user_service.get_settings`` by a counter around the real one; the list of calls, one entry per read."""
    reads: list[int] = []
    real = user_service.get_settings

    def counted() -> Any:
        reads.append(1)
        return real()

    monkeypatch.setattr(user_service, "get_settings", counted)
    return reads


# red until A-63 (c)
@pytest.mark.asyncio
async def test_the_list_of_accounts_reads_the_settings_once_not_once_per_row(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """UPROT-020 — A-63 (c): ``GET /users`` builds one row per account, and each row asked ``get_settings()`` — which reads ``.env`` — for the profile. Now the list reads the profile and the owner once: with 6 accounts the settings are read at most once, and the rows still say who is protected."""
    print_section("UPROT-020: GET /users reads the settings once")
    _configure(monkeypatch, tmp_path, profile="managed", admin_email=OWNER_EMAIL)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        owner = User(username="a63_owner", email=OWNER_EMAIL, hashed_password="x", is_active=True, is_superuser=True)
        others = [User(username=f"a63_user{i}", email=f"a63.user{i}@example.com", hashed_password="x", is_active=True) for i in range(5)]
        session.add_all([owner, *others])
        await session.commit()
        reads = _count_settings_reads(monkeypatch)
        answer = await users_api.list_accounts(admin=owner, session=session)

    assert len(answer.items) >= 6, "premise: the list holds the six accounts"
    assert len(reads) <= 1, f"the settings must be read once for the whole list, not once per row: {len(reads)} reads for {len(answer.items)} rows"
    assert {item.username: item.protected for item in answer.items}["a63_owner"] is True, "the owner is still protected"
    assert not any(item.protected for item in answer.items if item.username.startswith("a63_user")), "nobody else is"
    print_success(f"{len(reads)} read for {len(answer.items)} rows")


# =============================================================================
# A-63 (a): THE COMMAND LINE STORES THE ADDRESS AS THE SERVER NORMALISES IT
# =============================================================================


async def _address_of(engine: AsyncEngine, username: str) -> Optional[str]:
    async with AsyncSession(engine) as session:
        return (await session.execute(select(User.email).where(User.username == username))).scalar_one_or_none()


# red until A-63 (a)
@pytest.mark.asyncio
async def test_user_create_stores_the_address_as_the_server_normalises_it(engine: AsyncEngine, user_cli: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """UPROT-021 — A-63 (a): ``./dev.py user create`` saved the address as typed, so an owner created with ``Owner@EXAMPLE.com`` did not match the normalised variable the protection compares with. Now the address is validated and normalised like ``user set-email`` does (the domain in lower case): the stored form is the one ``EmailStr`` gives, and the account is protected on a managed instance whose variable is that address."""
    print_section("UPROT-021: user create normalises the address")
    _configure(monkeypatch, tmp_path, profile="managed", admin_email="a63owner@example.com")

    answer = await user_cli.cmd_create_user("a63_cli_owner", "a63owner@EXAMPLE.COM", "Cli-Protection-2026!", True)

    assert answer is True, f"user create must go through: {answer!r}"
    assert await _address_of(engine, "a63_cli_owner") == "a63owner@example.com", "the address is stored in the form the server normalises it to"
    async with AsyncSession(engine) as session:
        user = (await session.execute(select(User).where(User.username == "a63_cli_owner"))).scalar_one()
        assert user_service.account_protection(user) == REASON, "and it is the protected owner"
    print_success("normalised, protected")


# red until A-63 (a)
@pytest.mark.asyncio
async def test_user_create_refuses_a_text_that_is_not_an_address(engine: AsyncEngine, user_cli: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """UPROT-022 — A-63 (a): an address that is not one is refused with ❌ and nothing is created (``set-email`` already does)."""
    print_section("UPROT-022: user create refuses a non-address")
    _configure(monkeypatch, tmp_path, profile=None, admin_email=None)

    answer = await user_cli.cmd_create_user("a63_cli_bad", "not-an-address", "Cli-Protection-2026!", False)

    assert answer is False, f"a text that is not an address must be refused: {answer!r}"
    assert await _address_of(engine, "a63_cli_bad") is None, "nothing is created"
    print_success("refused")


# =============================================================================
# A-64 (a): ON A MANAGED INSTANCE NOBODY ELSE TAKES THE ADDRESS OF THE VARIABLE
# =============================================================================

HOST_ADDRESS = "a64host@example.com"


# red until A-64 (a)
@pytest.mark.asyncio
async def test_registration_and_the_profile_refuse_the_address_the_host_reserved(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """UPROT-030 — A-64 (a): on a managed instance whose ``LIBREFOLIO_ADMIN_EMAIL`` is ``HOST_ADDRESS`` and whose owner has not yet clicked the confirmation link, a user could take that address first — in registration (``create_user`` with the reservation, as ``register_user`` calls it) or in the profile (``update_profile``) — and block the change. Now both answer ``EMAIL_TAKEN`` (the same answer as an address in use, so the reservation is not told) and write nothing. Barriers: another address goes through; the command line (``reserve_owner_address=False``) is the operator's and still can; on a self-hosted instance nothing is reserved."""
    print_section("UPROT-030: the host's address is reserved on a managed instance")
    _configure(monkeypatch, tmp_path, profile="managed", admin_email=HOST_ADDRESS)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        member = User(username="a64_member", email="a64.member@example.com", hashed_password="x", is_active=True)
        session.add(member)
        await session.commit()

        user, error = await user_service.create_user(session, "a64_new", HOST_ADDRESS.upper(), "Reserve-2026!", reserve_owner_address=True)
        assert user is None and getattr(error, "code", None) == "EMAIL_TAKEN", f"registration must be refused with EMAIL_TAKEN: {(user, error)!r}"

        updated, error = await user_service.update_profile(session, member.id, email=HOST_ADDRESS)
        assert updated is None and getattr(error, "code", None) == "EMAIL_TAKEN", f"the profile must be refused with EMAIL_TAKEN: {(updated, error)!r}"

        ok, error = await user_service.create_user(session, "a64_other", "a64.other@example.com", "Reserve-2026!", reserve_owner_address=True)
        assert ok is not None and error is None, f"barrier: another address goes through: {error!r}"

        operator, error = await user_service.update_profile(session, member.id, email=HOST_ADDRESS, reserve_owner_address=False)
        assert operator is not None and error is None, f"the command line is the operator's and may: {error!r}"

    unused = "a64.selfhosted.host@example.com"
    _configure(monkeypatch, tmp_path, profile=None, admin_email=unused)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        taken, taken_error = await user_service.create_user(session, "a64_selfhosted2", unused, "Reserve-2026!", reserve_owner_address=True)
        assert taken is not None, f"self-hosted: nothing is reserved, not even the variable's address: {taken_error!r}"
    print_success("reserved on managed, free elsewhere")


# red until A-64 (a)
@pytest.mark.asyncio
@pytest.mark.parametrize("with_invitation", [pytest.param(False, id="open"), pytest.param(True, id="with-invitation")])
async def test_register_user_refuses_the_address_the_host_reserved(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, with_invitation: bool) -> None:
    """UPROT-031 — A-64 (a), the wiring of registration: ``register_user`` — open, or with a valid invitation — on a managed instance refuses ``HOST_ADDRESS`` with ``ACCOUNT_EXISTS`` (the answer of an address in use) and writes no account. Barrier: another address registers. If someone removed ``reserve_owner_address=True`` from ``register_user``, this is the case that turns red."""
    print_section("UPROT-031: register_user and the host's address")
    from backend.app.services.accounts import registration_service  # noqa: PLC0415 — after _configure, which sets the environment the module reads

    _configure(monkeypatch, tmp_path, profile="managed", admin_email=HOST_ADDRESS)
    monkeypatch.setenv("LIBREFOLIO_REGISTRATION", "open")
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add(User(username="a64_first", email="a64.first@example.com", hashed_password="x", is_active=True, is_superuser=True))
        await session.commit()

        async def invite() -> str | None:
            if not with_invitation:
                return None
            issued = await registration_service.create_invite(session, created_by_user_id=None)
            await session.commit()
            return issued.token

        with pytest.raises(registration_service.RegistrationError) as refused:
            await registration_service.register_user(session, username="a64_reg", email=HOST_ADDRESS, password="Reserve-2026!Aa", invite_token=await invite())
        assert refused.value.code == "ACCOUNT_EXISTS", f"the reserved address is refused as an address in use: {refused.value.code}"
        assert (await session.execute(select(User).where(User.username == "a64_reg"))).scalar_one_or_none() is None, "no account was written"

        user = await registration_service.register_user(session, username="a64_reg", email="a64.reg@example.com", password="Reserve-2026!Aa", invite_token=await invite())
        assert user.id is not None, "barrier: another address registers"
    print_success("refused, nothing written")


# red until A-64 (a)
@pytest.mark.asyncio
async def test_the_recorded_owner_may_hold_the_reserved_address(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """UPROT-032 — A-64 (a), the exemption: the account recorded as owner (``is_instance_owner``) changing its profile to ``HOST_ADDRESS`` is allowed (the reservation is against strangers). Removing ``not user.is_instance_owner`` turns this red; a stranger is refused (UPROT-030)."""
    print_section("UPROT-032: the owner")
    _configure(monkeypatch, tmp_path, profile="managed", admin_email=HOST_ADDRESS)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        owner = User(username="a64_owner", email="a64.oldowner@example.com", hashed_password="x", is_active=True, is_superuser=True, is_instance_owner=True)
        session.add(owner)
        await session.commit()

        changed, error = await user_service.update_profile(session, owner.id, email=HOST_ADDRESS)
        assert changed is not None and error is None, f"the recorded owner may take the address: {error!r}"
    print_success("owner exempt")


# red until A-64 (a)
@pytest.mark.asyncio
async def test_the_command_line_may_give_an_account_the_reserved_address(engine: AsyncEngine, user_cli: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """UPROT-033 — A-64 (a): ``./dev.py user set-email`` is the operator's emergency exit, above the reservation (it passes ``reserve_owner_address=False``). Removing that turns this red."""
    print_section("UPROT-033: the command line")
    _configure(monkeypatch, tmp_path, profile="managed", admin_email=HOST_ADDRESS)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add(User(username="a64_cli_member", email="a64.climember@example.com", hashed_password="x", is_active=True))
        await session.commit()

    assert await user_cli.cmd_set_email("a64_cli_member", HOST_ADDRESS) is True, "the operator's command may"
    print_success("command line exempt")
