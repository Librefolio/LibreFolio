"""``backend.app.services.email.verification``: the verification of an email address at sign-up (developer decision 44, plan phase01Email lot E5a).

With ``require_email_verification`` on, an account created by signing up waits for its owner to click a link before it
can sign in. A's hooks (``register_user``, the login's 403 ``EMAIL_NOT_VERIFIED``, ``user_usage``, the changes of
status, the setting) are not written yet: this module calls the functions of ``verification`` directly, and calls
``hold_for_verification`` itself where a registration is needed. The routes are tested over HTTP in
``test_api/test_email_verification_api.py``. The contract pinned here:

1. The surface: coroutine functions with their signatures (``first``, ``now``, ``engine``, ``identifier``, ``password``,
   ``address`` keyword-only; ``first`` and ``address`` required); the shipped limits — «resend» 10 requests per 15
   minutes per client address, per account one verification email every 5 minutes and 3 an hour, per recipient
   mailbox 3 verification emails an hour —, a link that lives
   24 hours on the page ``/verify-email``; every refusal an ``EmailError`` with its code (``EMAIL_VERIFICATION_UNAVAILABLE``,
   ``EMAIL_VERIFICATION_NOT_NEEDED``, ``INVALID_CREDENTIALS``, ``ACCOUNT_DISABLED``, ``USER_LIMIT_REACHED``, and the
   token's status for a refused link).
2. The option is the global setting ``require_email_verification``, off on a new install. ``links_can_go()`` is true only
   when the instance is not blocked (``LIBREFOLIO_BLOCKED`` blocking or unreadable), email is usable and links are ready,
   the configuration read off the event loop; ``ensure_verification_can_be_enabled()`` raises
   ``EmailVerificationUnavailableError`` otherwise. Neither connects to anything.
3. ``hold_for_verification(session, user, *, first)``: the instance's first account, or the option off, never waits —
   ``False``, nothing changed, whatever email can do. With the option on and no email with a link able to go out, the
   registration is refused: ``RegistrationError("EMAIL_VERIFICATION_UNAVAILABLE")``, nothing changed. Otherwise
   ``True``: the account inactive and one verification token of its own without an address (the hold), living 24 hours,
   flushed and not committed — the caller's rollback leaves nothing. The hold's text never leaves: not returned, not
   logged.
4. An account waits (``awaiting_verification``) when it is inactive and holds a verification token of its own that is
   neither consumed nor revoked, live or expired; an active account, an inactive one with only spent links, a
   password-reset link or another account's link never wait.
5. ``registration_email_work(user_id, *, engine)``, for an account that still waits: a new token carrying the account's
   address replaces its other verification tokens and goes by email — exactly what ``build_verification`` writes in the
   account's language, with the ``LIBREFOLIO_PUBLIC_URL`` link of ``/verify-email``, 24 hours, the host of that address
   as the instance, greeting nobody by name (no username: whoever signs up chooses it, decision N62) —, committed before
   the email, one unit of the hourly budget spent; the emailed link verifies the account. Nothing at all for an account
   that no longer waits. When the instance is blocked, email or links are not
   usable, the budget is spent or the recipient's mailbox had its three verification emails of the hour, nothing is
   made and the hold stays live (logged «not sent»). When anything fails once the new token is
   committed — reading the account's language, building the link or the email, ``send_email`` (the SMTP server
   refusing, or any other error) —, the new token stays unspent but loses its address (an UPDATE, committed) and the
   failure goes on: the account still waits, the token verifies nothing, and it is not counted as an email. A second
   email within five minutes is refused by the count made again inside the write transaction, which rolls everything
   back. The work never raises; a refusal is a warning with its type and code, an unexpected error an error with its
   type alone, without a traceback.
6. ``confirm_email(session, token)``: a live verification link only — ``expired``, ``consumed``, ``revoked``, ``unknown``
   otherwise, a token of another purpose being ``unknown``. A link without an address — the hold, or a link whose email
   did not go out as far as LibreFolio knows — is refused as ``revoked`` but left as it is: it may be the account's
   only unspent token, and revoking it would end the wait (a lockout); the account still waits and «resend» works. A
   link emailed to an address the account no longer has is revoked and refused as ``revoked``: the two compared by
   ``user_service.same_email``, A's one rule of decision P18 (lot E4c) — A–Z in any case, every other character as
   written, nothing stripped —, so the account's own address in other capitals is the same address, and with a letter
   beyond A–Z in another case another one, refused on the safe side. On success the account is active,
   ``email_verified_at`` is the moment, the link is consumed by its account, the account's other verification tokens
   are revoked, other purposes and other accounts untouched; committed. A link spent meanwhile is ``consumed``, and
   nothing changes.
7. ``resend_verification(session, *, identifier, password, address)``: the counter per client address first
   (``delivery.ADDRESS_BUDGET``, 20 an hour, shared with the registrations and «forgot password», keyed by H's
   ``client_rate_key`` and skipped without an address), only looked at before any password is checked — a full one
   refuses with the longest wait of that counter and the instance's hourly budget when it is spent too, a try costs it
   nothing — and spent by the email that really goes, just before it (not by a wrong password, nor by a resend that the
   limit per account or per mailbox, or the budget, refuses; it stays spent if the SMTP server then fails); then the password as the
   login checks it — a dummy hash for an unknown account, one refusal ``INVALID_CREDENTIALS`` for both —; an active
   account is ``EMAIL_VERIFICATION_NOT_NEEDED``, an inactive one that does not wait ``ACCOUNT_DISABLED``; then the
   block, email and links; then the limits per account, counted on the links emailed — tokens carrying an address,
   spent or not; the hold never counts —, the wait being the longest of the two; then, when no link of the account is
   live any more, a place under ``LIBREFOLIO_MAX_USERS`` (``USER_LIMIT_REACHED``); then the hourly budget; then the
   recipient's mailbox — three verification emails an hour per mailbox, whatever accounts they are for, letter case
   and surrounding spaces aside, and the aliases of one mailbox folded by ``delivery.mailbox_budget_key`` (E-9 a: a
   ``+tag`` on any domain, the dots of a Gmail local part, ``googlemail.com`` for ``gmail.com``), each email still going
   to its account's address as stored —, counted on the emails that went out only (``EmailRateLimitedError`` with the
   wait); then the email of contract 5, returning its language. Whatever fails once the new token is committed is raised,
   and the new token stays without its address: it confirms nothing and counts for nothing, so «resend» may be asked
   again at once. A link emailed meanwhile by another request rolls everything back: ``EmailRateLimitedError``.
   Inside the write transaction the account's unspent links are revoked first: none left means it stopped waiting
   meanwhile (its link clicked, or an administrator's decision) — rolled back, ``EMAIL_VERIFICATION_NOT_NEEDED`` when
   it is active now, ``ACCOUNT_DISABLED`` otherwise, no new link —; when it held no place (``needs_place``: its link
   expired), the user limit is counted again with the new link, and a place taken meanwhile rolls it back
   (``USER_LIMIT_REACHED``).
8. No log event holds a token, a password, an identifier or an address. Wrong credentials for «resend» are a warning,
   «Verification resend refused: wrong credentials», without the identifier.

Pure: every database is a private SQLite file under ``tmp_path`` built with ``create_all`` and the default global
settings (NullPool, disposed at teardown), the option set in that file only; accounts written as rows with a real
bcrypt hash at cost 4; tokens issued by A's token service with the ``now`` the case needs. An autouse fixture removes
every inherited ``LIBREFOLIO_SMTP_*``, ``LIBREFOLIO_PUBLIC_URL``, ``LIBREFOLIO_BLOCKED``, ``LIBREFOLIO_MAX_USERS``,
``LIBREFOLIO_REGISTRATION`` and ``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS``; each test sets its own with ``monkeypatch``.
The hourly budget, ``delivery.ADDRESS_BUDGET`` (the counter per client address) and
``VERIFICATION_BY_MAILBOX`` are private limiters on a fake clock; ``socket.getaddrinfo`` resolves the loopback only.
Every SMTP conversation is with ``FakeSmtpServer`` on 127.0.0.1, on a port the OS picks. Nothing is timed.
"""

from __future__ import annotations

import asyncio
import inspect
import os
import re
import socket
from collections.abc import AsyncIterator, Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import pytest
import pytest_asyncio
from sqlalchemy import select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import AccountToken, AccountTokenPurpose, GlobalSetting, User, UserSettings
from backend.app.schemas.settings import SETTINGS_REGISTRY
from backend.app.services.accounts import auth_service, token_service, user_service
from backend.app.services.accounts.registration_service import RegistrationError
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.accounts.token_service import DEFAULT_TTL, IssuedToken, TokenStatus
from backend.app.services.email import delivery, smtp, verification
from backend.app.services.email.delivery import EmailDeliveryError, EmailError, EmailRateLimitedError, EmailUnavailableError
from backend.app.services.email.links import EmailLinksUnavailableError, email_link
from backend.app.services.email.messages import EmailRecipientError, build_verification
from backend.app.utils.datetime_utils import ensure_utc, utcnow
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.fixtures.email.fake_smtp import FakeSmtpServer
from backend.test_scripts.test_utils import print_section, print_success

SMTP_PREFIX = "LIBREFOLIO_SMTP_"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
BLOCKED_VARIABLE = "LIBREFOLIO_BLOCKED"
MAX_USERS_VARIABLE = "LIBREFOLIO_MAX_USERS"
#: Removed before every test besides the SMTP ones: each changes what this module decides.
SIGNUP_PER_ADDRESS = "LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS"
INHERITED = (PUBLIC_URL_VARIABLE, BLOCKED_VARIABLE, MAX_USERS_VARIABLE, "LIBREFOLIO_REGISTRATION", SIGNUP_PER_ADDRESS)

#: The public address of the instance, with a port and a path prefix; its host with the port is the email's instance.
PUBLIC_URL = "https://folio.zq-public.example.com:8443/app"
PUBLIC_HOST = "folio.zq-public.example.com:8443"
#: An http(s) address no link can start from (a space inside).
NO_LINK_FROM_IT = "https://folio.zq-space.example.com/my folio"
SENDER_HEADER = "LibreFolio <noreply@example.com>"
SENDER = ("LibreFolio", "noreply@example.com")
#: A host nothing ever connects to, for the steps that read the configuration and never send.
UNUSED_HOST = "smtp.zq-host.example.com"
LOOPBACK_NAMES = frozenset({"127.0.0.1", "::1", "localhost"})

OPTION_KEY = SETTINGS_REGISTRY.global_.REQUIRE_EMAIL_VERIFICATION.key
DEFAULT_LANGUAGE_KEY = SETTINGS_REGISTRY.global_.DEFAULT_LANGUAGE.key

ACCOUNT_PASSWORD = "Verify-Me-Pass-2026"
WRONG_PASSWORD = "Not-The-Pass-2026"
#: Alice waits for her link, Bob is active, Carol was deactivated by an administrator.
ALICE = "zq_alice"
BOB = "zq_bob"
CAROL = "zq_carol"
ADMIN = "zq_admin"
NOBODY = "zq_nobody"

VERIFICATION = AccountTokenPurpose.EMAIL_VERIFICATION
PASSWORD_RESET = AccountTokenPurpose.PASSWORD_RESET
INVITE = AccountTokenPurpose.INVITE
TTL = DEFAULT_TTL[VERIFICATION]
PAGE = "/verify-email"
NEVER_ISSUED = "never-issued-verification-0123456789abcdefghij"

ADDRESS = "198.51.100.7"
OTHER_ADDRESS = "203.0.113.9"
#: Two client addresses of one IPv6 /64, which counts once.
SAME_64 = ("2001:db8:1:2::10", "2001:db8:1:2:ffff::1")
SAME_64_KEY = "2001:db8:1:2::/64"
#: ADDRESS as an IPv4-mapped IPv6 address: the same client.
MAPPED = "::ffff:198.51.100.7"

#: The process's counter per client address (shared by the registrations, «resend» and «forgot password»), as shipped (the fixture below puts a private one in its place).
SHIPPED_RESEND = delivery.ADDRESS_BUDGET
#: The process's limiter of verification emails per recipient mailbox, as shipped (a fixture below replaces it too).
SHIPPED_MAILBOX = verification.VERIFICATION_BY_MAILBOX
#: One mailbox written four ways, each the address of an account of its own: the limiter keys them all as MAILBOX. The
#: ways differ in the case of ``ï`` and ``ç`` alone, in NFC (one code point each): since P18 an address is unique
#: regardless of A–Z case (``ux_users_email_lower``).
MAILBOX_VARIANTS = ("zq-v\u00cf\u00e7@example.com", "zq-v\u00ef\u00e7@example.com", "zq-v\u00cf\u00c7@example.com", "zq-v\u00ef\u00c7@example.com")
MAILBOX = "zq-v\u00ef\u00e7@example.com"
START = 1_000.0

POSITIONAL = inspect.Parameter.POSITIONAL_OR_KEYWORD
KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY


class FakeClock:
    """A clock that moves only when the test sets it: ``clock.now = …``."""

    def __init__(self, start: float = START) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture(autouse=True)
def _no_inherited_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every ``LIBREFOLIO_SMTP_*`` and every variable of INHERITED the lane inherited is removed: a test sees only the variables it sets itself."""
    for name in list(os.environ):
        if name.startswith(SMTP_PREFIX) or name in INHERITED:
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _nothing_reported_yet() -> Iterator[None]:
    """``delivery._report_invalid`` remembers for the whole process what it logged: each test starts, and leaves, with nothing reported."""
    delivery._report_invalid.cache_clear()
    yield
    delivery._report_invalid.cache_clear()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture(autouse=True)
def budget(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> SlidingWindowLimiter:
    """A private hourly budget on the fake clock in place of the process's: no test spends, or depends on, the real one."""
    limiter = SlidingWindowLimiter(50, 3600, max_keys=1, clock=clock)
    monkeypatch.setattr(delivery, "INSTANCE_BUDGET", limiter)
    return limiter


@pytest.fixture(autouse=True)
def address_limit(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> SlidingWindowLimiter:
    """A private «resend» limiter with the shipped limit, on the fake clock: no test counts in, or is counted by, the process's."""
    limiter = SlidingWindowLimiter(SHIPPED_RESEND.limit, SHIPPED_RESEND.window_seconds, clock=clock)
    monkeypatch.setattr(delivery, "ADDRESS_BUDGET", limiter)
    return limiter


@pytest.fixture(autouse=True)
def mailbox_limit(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> SlidingWindowLimiter:
    """A private per-mailbox limiter with the shipped limit, on the fake clock: an email of one test never counts against another's mailbox."""
    limiter = SlidingWindowLimiter(SHIPPED_MAILBOX.limit, SHIPPED_MAILBOX.window_seconds, clock=clock)
    monkeypatch.setattr(verification, "VERIFICATION_BY_MAILBOX", limiter)
    return limiter


@pytest.fixture(autouse=True)
def _bounded_smtp_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """5 s instead of 20: a defect that hangs fails sooner. No test waits for it."""
    monkeypatch.setattr(smtp, "SMTP_TIMEOUT_SECONDS", 5.0)


@pytest.fixture(autouse=True)
def _cheap_bcrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    """bcrypt at cost 4: the hashes are real, the checks cheap."""
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)


@pytest.fixture(autouse=True)
def network(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """``socket.getaddrinfo`` resolves the loopback only; any other name is refused and recorded here: a host name configured for a step that never sends is never looked up."""
    resolve = socket.getaddrinfo
    refused: list[str] = []

    def loopback_only(host: Any, *args: Any, **kwargs: Any) -> Any:
        name = host.decode() if isinstance(host, bytes) else host
        if name is not None and name not in LOOPBACK_NAMES:
            refused.append(str(name))
            raise socket.gaierror(socket.EAI_NONAME, f"the email verification tests resolve the loopback only, not {name!r}")
        return resolve(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", loopback_only)
    return refused


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file under tmp_path with the whole ORM schema and the default global settings (the option off, ``default_language`` ``en``); disposed at teardown."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'verification.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            await initialize_global_settings(session)
        yield engine
    finally:
        await engine.dispose()


async def _add_user(engine: AsyncEngine, username: str, *, email: str | None = None, active: bool = True) -> User:
    """An account written as a row, ``<username>@example.com`` unless ``email`` says otherwise, with a real bcrypt hash of ACCOUNT_PASSWORD; returned detached, its columns loaded."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=email or f"{username}@example.com", hashed_password=auth_service.hash_password(ACCOUNT_PASSWORD), is_active=active)
        session.add(user)
        await session.commit()
    return user


async def _option(engine: AsyncEngine, value: str) -> None:
    """The global setting ``require_email_verification`` of the private database says ``value``."""
    async with AsyncSession(engine) as session:
        result = await session.execute(update(GlobalSetting).where(GlobalSetting.key == OPTION_KEY).values(value=value))
        assert result.rowcount == 1, "setup: initialize_global_settings did not seed require_email_verification"
        await session.commit()


async def _set_account_language(engine: AsyncEngine, user_id: int, language: str) -> None:
    async with AsyncSession(engine) as session:
        session.add(UserSettings(user_id=user_id, language=language, theme="light"))
        await session.commit()


async def _set_default_language(engine: AsyncEngine, value: str) -> None:
    async with AsyncSession(engine) as session:
        result = await session.execute(update(GlobalSetting).where(GlobalSetting.key == DEFAULT_LANGUAGE_KEY).values(value=value))
        assert result.rowcount == 1, "setup: initialize_global_settings did not seed the default_language row"
        await session.commit()


def _configure(monkeypatch: pytest.MonkeyPatch, variables: dict[str, str | None]) -> None:
    """Set ``LIBREFOLIO_SMTP_<NAME>`` for each ``name: value``, ``None`` leaving it unset."""
    for name, value in variables.items():
        variable = SMTP_PREFIX + name.upper()
        if value is None:
            monkeypatch.delenv(variable, raising=False)
        else:
            monkeypatch.setenv(variable, value)


def _ready(monkeypatch: pytest.MonkeyPatch, fake: FakeSmtpServer, **extra: str | None) -> None:
    """Email through ``fake`` — its address and port, no TLS on the loopback, this module's sender, ``extra`` on top — and links ready on PUBLIC_URL."""
    _configure(monkeypatch, {"host": fake.host, "port": str(fake.port), "tls": "none", "from": SENDER_HEADER, **extra})
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)


def _usable_without_a_server(monkeypatch: pytest.MonkeyPatch, **extra: str | None) -> None:
    """A usable SMTP configuration towards UNUSED_HOST, for the steps that read the configuration and never send; links ready."""
    _configure(monkeypatch, {"host": UNUSED_HOST, "from": SENDER_HEADER, **extra})
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)


def _set_up(monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    """The configuration a case names, on top of a usable one towards UNUSED_HOST with links ready."""
    if case == "email-off":
        monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)
        return
    _usable_without_a_server(monkeypatch)
    if case == "email-unusable":
        _configure(monkeypatch, {"tls": "ssl"})
    elif case == "links-missing":
        monkeypatch.delenv(PUBLIC_URL_VARIABLE, raising=False)
    elif case == "links-invalid":
        monkeypatch.setenv(PUBLIC_URL_VARIABLE, NO_LINK_FROM_IT)
    elif case == "blocked":
        monkeypatch.setenv(BLOCKED_VARIABLE, "1")
    elif case == "block-unreadable":
        monkeypatch.setenv(BLOCKED_VARIABLE, "maybe")
    else:
        assert case == "ready", case


async def _issue(engine: AsyncEngine, purpose: AccountTokenPurpose, **arguments: object) -> IssuedToken:
    """A token issued by A's token service, committed."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, purpose, **arguments)
        await session.commit()
    return issued


async def _spend(engine: AsyncEngine, issued: IssuedToken, how: str) -> None:
    """``issued`` consumed or revoked, committed."""
    async with AsyncSession(engine) as session:
        if how == "consumed":
            assert await token_service.consume_token(session, issued.token, issued.record.purpose) is not None, "setup: consumed"
        else:
            assert await token_service.revoke_tokens(session, token_id=issued.record.id) == 1, "setup: revoked"
        await session.commit()


async def _waiting(engine: AsyncEngine, username: str, *, created: datetime, email: str | None = None) -> tuple[User, IssuedToken]:
    """An account as ``hold_for_verification`` leaves it once committed: inactive, with a verification token of its own without an address (the hold) issued at ``created``."""
    user = await _add_user(engine, username, email=email, active=False)
    return user, await _issue(engine, VERIFICATION, user_id=user.id, now=created)


async def _emailed(engine: AsyncEngine, user: User, *, created: datetime, how: str = "live", email: str | None = None) -> IssuedToken:
    """A verification link emailed to the account at ``created``: a token carrying its address (or ``email``); ``how`` consumed or revoked spends it."""
    issued = await _issue(engine, VERIFICATION, user_id=user.id, email=email or user.email, now=created)
    if how != "live":
        await _spend(engine, issued, how)
    return issued


async def _hold(engine: AsyncEngine, user_id: int, *, first: bool = False, now: datetime | None = None) -> bool:
    """``hold_for_verification`` for the account, in a session of its own, committed: what ``register_user`` will do."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(User, user_id)
        held = await verification.hold_for_verification(session, user, first=first, now=now)
        await session.commit()
    return held


async def _account(engine: AsyncEngine, user_id: int) -> User:
    """The account as stored, read fresh."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await session.get(User, user_id)


async def _rows(engine: AsyncEngine, user_id: int, purpose: AccountTokenPurpose = VERIFICATION) -> list[AccountToken]:
    """Every token row of the account for ``purpose``, oldest first, read fresh."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        statement = select(AccountToken).where(AccountToken.purpose == purpose, AccountToken.user_id == user_id).order_by(AccountToken.id)
        return list((await session.execute(statement)).scalars().all())


def _states(rows: list[AccountToken]) -> list[tuple[int, str | None, bool, bool]]:
    """``(id, email, consumed, revoked)`` of each row: what a step changed, or did not."""
    return [(row.id, row.email, row.consumed_at is not None, row.revoked_at is not None) for row in rows]


async def _status(engine: AsyncEngine, token: str, purpose: AccountTokenPurpose = VERIFICATION) -> TokenStatus:
    """What A's token service says of ``token`` now, read fresh."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return (await token_service.inspect_token(session, token, purpose)).status


async def _awaits(engine: AsyncEngine, user_id: int) -> bool:
    """``awaiting_verification`` of the account as stored."""
    async with AsyncSession(engine) as session:
        return await verification.awaiting_verification(session, await session.get(User, user_id))


async def _resend(engine: AsyncEngine, identifier: str, password: str = ACCOUNT_PASSWORD, *, address: str | None = ADDRESS, now: datetime | None = None) -> str:
    """``resend_verification`` in a session of its own, as the route calls it."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await verification.resend_verification(session, identifier=identifier, password=password, address=address, now=now)


async def _confirm(engine: AsyncEngine, token: str, *, now: datetime | None = None) -> User:
    """``confirm_email`` in a session of its own, as the route calls it."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await verification.confirm_email(session, token, now=now)


def _loop_running() -> bool:
    """Whether the calling thread runs an event loop right now."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


def _mailboxes(header: object) -> list[tuple[str, str]]:
    return [(address.display_name, address.addr_spec) for address in header.addresses]


def _lines(text: str) -> str:
    """``text`` without the line-ending differences of a MIME round trip."""
    return text.replace("\r\n", "\n").rstrip("\n")


def _text(received: object) -> str:
    """The plain-text part of a received message."""
    return received.message.get_body(preferencelist=("plain",)).get_content()


def _html(received: object) -> str:
    """The HTML part of a received message."""
    return received.message.get_body(preferencelist=("html",)).get_content()


def _token_in(text: str) -> str:
    """The token of the PUBLIC_URL verification link an email text carries; fails when it carries none."""
    match = re.search(re.escape(f"{PUBLIC_URL}{PAGE}#") + r"(\S+)", text)
    assert match, f"no {PUBLIC_URL}{PAGE} link in the email: {text!r}"
    return parse_qs(match.group(1))["token"][0]


def _expected(token: str, *, language: str = "en") -> object:
    """What ``build_verification`` writes for the PUBLIC_URL link of ``token``: 24 hours, the public host as the instance, no username (decision N62)."""
    return build_verification(language=language, link=email_link(VERIFICATION, token), ttl=TTL, instance=PUBLIC_HOST)


def _assert_is(received: object, expected: object) -> None:
    """The message is exactly the content a builder wrote: subject, text and HTML."""
    assert received.message["Subject"] == expected.subject
    assert _lines(_text(received)) == _lines(expected.text)
    assert _lines(_html(received)) == _lines(expected.html)


def _holding(events: list[dict[str, Any]], *needles: str) -> list[dict[str, Any]]:
    """The log events whose rendering holds one of ``needles``."""
    return [event for event in events if any(needle in repr(event) for needle in needles)]


def _named(events: list[dict[str, Any]], prefix: str) -> list[dict[str, Any]]:
    """The log events whose message starts with ``prefix``."""
    return [event for event in events if str(event.get("event", "")).startswith(prefix)]


# =============================================================================
# 1. THE SURFACE
# =============================================================================


def test_the_functions_are_coroutine_functions_with_their_signatures() -> None:
    """EMV-001 — contract 1: every function of the flow is a coroutine function; ``first``, ``now``, ``engine``, ``identifier``, ``password`` and ``address`` are keyword-only; ``first`` and ``address`` have no default (a caller says them), ``now`` and ``engine`` default to None."""
    print_section("EMV-001: signatures")
    expected = {
        "verification_required": [("session", POSITIONAL)],
        "links_can_go": [],
        "ensure_verification_can_be_enabled": [],
        "awaiting_verification": [("session", POSITIONAL), ("user", POSITIONAL)],
        "hold_for_verification": [("session", POSITIONAL), ("user", POSITIONAL), ("first", KEYWORD_ONLY), ("now", KEYWORD_ONLY)],
        "registration_email_verdict": [("address", POSITIONAL)],
        "registration_email_work": [("user_id", POSITIONAL), ("engine", KEYWORD_ONLY), ("now", KEYWORD_ONLY)],
        "confirm_email": [("session", POSITIONAL), ("token", POSITIONAL), ("now", KEYWORD_ONLY)],
        "resend_verification": [("session", POSITIONAL), ("identifier", KEYWORD_ONLY), ("password", KEYWORD_ONLY), ("address", KEYWORD_ONLY), ("now", KEYWORD_ONLY)],
    }
    for name, parameters in expected.items():
        function = getattr(verification, name)
        assert inspect.iscoroutinefunction(function), f"{name} must be a coroutine function"
        signature = inspect.signature(function)
        assert [(parameter.name, parameter.kind) for parameter in signature.parameters.values()] == parameters, name
        for parameter in signature.parameters.values():
            if parameter.name in ("now", "engine"):
                assert parameter.default is None, f"{name}({parameter.name}) defaults to None"
            if parameter.name in ("first", "address"):
                assert parameter.default is inspect.Parameter.empty, f"{name}({parameter.name}) is said by every caller"
    print_success(f"{len(expected)} coroutine functions")


def test_the_shipped_limits_lifetime_and_page() -> None:
    """EMV-002 — contract 1: the counter per client address, 20 per 3600 s (``delivery.ADDRESS_BUDGET``, shared by the registrations, «resend» and «forgot password»; no ``RESEND_BY_ADDRESS`` any more); per account one verification email every 5 minutes and 3 an hour; per recipient mailbox 3 verification emails per 3600 s; a verification link lives 24 hours and opens ``/verify-email`` with the token in the fragment."""
    print_section("EMV-002: limits, lifetime, page")

    assert (SHIPPED_RESEND.limit, SHIPPED_RESEND.window_seconds) == (20, 3600)
    assert not hasattr(verification, "RESEND_BY_ADDRESS") and not hasattr(verification, "REGISTRATION_EMAILS_BY_ADDRESS"), "the counter per address has one home, delivery.ADDRESS_BUDGET"
    assert isinstance(SHIPPED_MAILBOX, SlidingWindowLimiter) and (SHIPPED_MAILBOX.limit, SHIPPED_MAILBOX.window_seconds) == (3, 3600)
    assert (verification.VERIFICATION_EMAIL_MIN_INTERVAL, verification.VERIFICATION_EMAILS_PER_HOUR) == (timedelta(minutes=5), 3)
    assert verification.VERIFICATION is VERIFICATION and TTL == timedelta(hours=24)
    assert token_service.token_path(VERIFICATION, "zq-token") == f"{PAGE}#token=zq-token"
    print_success("20/3600 s per address, 1 per 5 min and 3 per hour per account, 3/3600 s per mailbox, 24 h, /verify-email#token=")


@pytest.mark.parametrize(
    ("make", "code"),
    [
        pytest.param(verification.EmailVerificationUnavailableError, "EMAIL_VERIFICATION_UNAVAILABLE", id="unavailable"),
        pytest.param(verification.EmailVerificationNotNeededError, "EMAIL_VERIFICATION_NOT_NEEDED", id="not-needed"),
        pytest.param(verification.VerificationCredentialsError, "INVALID_CREDENTIALS", id="credentials"),
        pytest.param(verification.VerificationAccountDisabledError, "ACCOUNT_DISABLED", id="account-disabled"),
        pytest.param(verification.VerificationUserLimitError, "USER_LIMIT_REACHED", id="user-limit"),
        pytest.param(lambda: verification.EmailVerificationLinkInvalidError("expired"), "expired", id="link-invalid-carries-the-status"),
    ],
)
def test_each_refusal_is_an_email_error_with_its_code(make: Any, code: str) -> None:
    """EMV-003 — contract 1: each refusal of the flow is an ``EmailError`` whose ``code`` the routes answer with; a refused link carries the status of its token."""
    print_section(f"EMV-003: {code}")
    error = make()

    assert isinstance(error, EmailError) and error.code == code, repr(error)
    print_success(f"{type(error).__name__}: {code}")


# =============================================================================
# 2. THE OPTION, AND WHETHER AN EMAIL WITH A LINK CAN GO
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(("stored", "expected"), [pytest.param(None, False, id="a-new-install"), pytest.param("true", True, id="on"), pytest.param("false", False, id="off")])
async def test_the_option_is_the_global_setting(engine: AsyncEngine, stored: str | None, expected: bool) -> None:
    """EMV-004 — contract 2: ``verification_required`` says what the global setting ``require_email_verification`` says; a new install has it off."""
    print_section(f"EMV-004: require_email_verification={stored!r}")
    if stored is not None:
        await _option(engine, stored)

    async with AsyncSession(engine) as session:
        required = await verification.verification_required(session)

    assert required is expected
    print_success(f"verification_required: {required}")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case", "can_go"),
    [
        pytest.param("email-off", False, id="email-off"),
        pytest.param("email-unusable", False, id="email-unusable"),
        pytest.param("links-missing", False, id="links-missing"),
        pytest.param("links-invalid", False, id="links-invalid"),
        pytest.param("blocked", False, id="blocked"),
        pytest.param("block-unreadable", False, id="block-unreadable"),
        pytest.param("ready", True, id="ready"),
    ],
)
async def test_whether_an_email_with_a_link_can_go(monkeypatch: pytest.MonkeyPatch, network: list[str], case: str, can_go: bool) -> None:
    """EMV-005 — contract 2: an email with a link can go only with the instance not blocked (``LIBREFOLIO_BLOCKED`` blocking or unreadable), email usable and links ready; ``ensure_verification_can_be_enabled`` raises ``EmailVerificationUnavailableError`` otherwise and returns None when it can. No host name is looked up."""
    print_section(f"EMV-005: {case}")
    _set_up(monkeypatch, case)

    assert await verification.links_can_go() is can_go
    if can_go:
        assert await verification.ensure_verification_can_be_enabled() is None
    else:
        with pytest.raises(verification.EmailVerificationUnavailableError) as refused:
            await verification.ensure_verification_can_be_enabled()
        assert refused.value.code == "EMAIL_VERIFICATION_UNAVAILABLE"
    assert network == []
    print_success(f"links_can_go: {can_go}")


@pytest.mark.asyncio
async def test_links_can_go_reads_the_configuration_off_the_event_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    """EMV-006 — contract 2: ``links_can_go`` reads the email configuration — which may read a password file — in a worker thread, never on the event loop."""
    print_section("EMV-006: off the event loop")
    _usable_without_a_server(monkeypatch)
    read = delivery.email_config_state
    on_the_loop: list[bool] = []

    def recording() -> object:
        on_the_loop.append(_loop_running())
        return read()

    monkeypatch.setattr(delivery, "email_config_state", recording)

    assert await verification.links_can_go() is True
    assert on_the_loop == [False]
    print_success("read once, in a worker thread")


# =============================================================================
# 3. hold_for_verification
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("first", "option", "case"),
    [
        pytest.param(True, "true", "ready", id="the-first-account-option-on"),
        pytest.param(True, "true", "email-off", id="the-first-account-option-on-email-off"),
        pytest.param(False, "false", "ready", id="option-off"),
        pytest.param(False, "false", "email-off", id="option-off-email-off"),
    ],
)
async def test_the_first_account_or_the_option_off_never_waits(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, first: bool, option: str, case: str) -> None:
    """EMV-007 — contract 3: the instance's first account, or any account with the option off, does not wait: ``False``, the account active, no verification token — whether or not an email could go."""
    print_section(f"EMV-007: first={first}, option {option}, {case}")
    await _option(engine, option)
    _set_up(monkeypatch, case)
    alice = await _add_user(engine, ALICE)

    held = await _hold(engine, alice.id, first=first)

    assert held is False
    assert (await _account(engine, alice.id)).is_active is True
    assert await _rows(engine, alice.id) == []
    assert budget.count() == 0
    print_success("False, active, no token")


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["email-off", "email-unusable", "links-missing", "blocked"])
async def test_with_the_option_on_and_no_email_that_can_go_the_registration_is_refused(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, network: list[str], case: str) -> None:
    """EMV-008 — contract 3: the option on, and no email with a link can go out: ``RegistrationError("EMAIL_VERIFICATION_UNAVAILABLE")`` (the safe side); the account untouched — active, no token."""
    print_section(f"EMV-008: {case}")
    await _option(engine, "true")
    _set_up(monkeypatch, case)
    alice = await _add_user(engine, ALICE)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(User, alice.id)
        with pytest.raises(RegistrationError) as refused:
            await verification.hold_for_verification(session, user, first=False)
        assert user.is_active is True, "the account must not be changed before the refusal"
        await session.rollback()

    assert refused.value.code == "EMAIL_VERIFICATION_UNAVAILABLE"
    assert (await _account(engine, alice.id)).is_active is True
    assert await _rows(engine, alice.id) == []
    assert network == []
    print_success("EMAIL_VERIFICATION_UNAVAILABLE, the account untouched")


@pytest.mark.asyncio
async def test_the_hold_makes_the_account_wait_flushed_not_committed(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, network: list[str]) -> None:
    """EMV-009 — contract 3: the option on, an email with a link able to go: ``True``; the account inactive and one verification token of its own without an address — the hold —, issued now, living 24 hours, neither consumed nor revoked, made by nobody. Flushed, not committed: until the caller commits, another session sees the account active and no token. The hold's text never leaves: the answer is the boolean alone and no log event holds it; the one log line names the account by its id. Nothing is sent or spent."""
    print_section("EMV-009: the hold")
    await _option(engine, "true")
    _usable_without_a_server(monkeypatch)
    alice = await _add_user(engine, ALICE)
    moment = utcnow()
    issued: list[IssuedToken] = []
    issue = token_service.issue_token

    async def recording(session: AsyncSession, purpose: AccountTokenPurpose, **arguments: object) -> IssuedToken:
        result = await issue(session, purpose, **arguments)
        issued.append(result)
        return result

    monkeypatch.setattr(token_service, "issue_token", recording)
    with capture_logs() as events:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user = await session.get(User, alice.id)
            held = await verification.hold_for_verification(session, user, first=False, now=moment)
            seen_before_commit = ((await _account(engine, alice.id)).is_active, await _rows(engine, alice.id))
            await session.commit()

    assert held is True
    assert seen_before_commit == (True, []), f"flushed, not committed: another session saw {seen_before_commit}"
    account = await _account(engine, alice.id)
    assert (account.is_active, account.email_verified_at) == (False, None)
    rows = await _rows(engine, alice.id)
    assert len(issued) == 1 and [row.id for row in rows] == [issued[0].record.id]
    hold = rows[0]
    assert (hold.email, hold.user_id, hold.created_by_user_id, hold.grants_admin, hold.consumed_at, hold.revoked_at) == (None, alice.id, None, False, None, None)
    assert (ensure_utc(hold.created_at), ensure_utc(hold.expires_at)) == (moment, moment + TTL)
    assert await _awaits(engine, alice.id) is True
    assert _holding(events, issued[0].token) == [], "the hold's text must never leave"
    waits = _named(events, "Registration waits for email verification")
    assert [(event.get("log_level"), event.get("user_id")) for event in waits] == [("info", alice.id)], events
    assert (budget.count(), network) == (0, [])
    print_success("inactive, one hold of 24 h without an address, its text nowhere")


@pytest.mark.asyncio
async def test_a_registration_rolled_back_leaves_nothing(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine) -> None:
    """EMV-010 — contract 3: ``hold_for_verification`` commits nothing itself: when the registration's transaction is rolled back, the account is as it was and there is no token."""
    print_section("EMV-010: rolled back")
    await _option(engine, "true")
    _usable_without_a_server(monkeypatch)
    alice = await _add_user(engine, ALICE)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        assert await verification.hold_for_verification(session, await session.get(User, alice.id), first=False) is True
        await session.rollback()

    assert (await _account(engine, alice.id)).is_active is True
    assert await _rows(engine, alice.id) == []
    print_success("active, no token")


# =============================================================================
# 4. awaiting_verification
# =============================================================================


async def _alice_in(engine: AsyncEngine, case: str, moment: datetime) -> User:
    """Alice in the state ``case`` names (EMV-011)."""
    alice = await _add_user(engine, ALICE, active=case.startswith("active"))
    if case.endswith("a-live-hold"):
        await _issue(engine, VERIFICATION, user_id=alice.id, now=moment)
    elif case == "inactive-with-an-expired-hold":
        await _issue(engine, VERIFICATION, user_id=alice.id, now=moment - TTL - timedelta(hours=1))
    elif case == "inactive-with-a-live-emailed-link":
        await _emailed(engine, alice, created=moment)
    elif case == "inactive-with-a-consumed-link-only":
        await _emailed(engine, alice, created=moment, how="consumed")
    elif case == "inactive-with-a-revoked-link-only":
        await _emailed(engine, alice, created=moment, how="revoked")
    elif case == "inactive-with-a-live-reset-link-only":
        await _issue(engine, PASSWORD_RESET, user_id=alice.id, now=moment)
    elif case == "inactive-with-another-accounts-link":
        bob = await _add_user(engine, BOB, active=False)
        await _issue(engine, VERIFICATION, user_id=bob.id, now=moment)
    else:
        assert case == "inactive-without-a-token", case
    return alice


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case", "waits"),
    [
        pytest.param("active-with-a-live-hold", False, id="active-with-a-live-hold"),
        pytest.param("inactive-with-a-live-hold", True, id="inactive-with-a-live-hold"),
        pytest.param("inactive-with-an-expired-hold", True, id="inactive-with-an-expired-hold"),
        pytest.param("inactive-with-a-live-emailed-link", True, id="inactive-with-a-live-emailed-link"),
        pytest.param("inactive-with-a-consumed-link-only", False, id="inactive-with-a-consumed-link-only"),
        pytest.param("inactive-with-a-revoked-link-only", False, id="inactive-with-a-revoked-link-only"),
        pytest.param("inactive-without-a-token", False, id="inactive-without-a-token"),
        pytest.param("inactive-with-a-live-reset-link-only", False, id="inactive-with-a-live-reset-link-only"),
        pytest.param("inactive-with-another-accounts-link", False, id="inactive-with-another-accounts-link"),
    ],
)
async def test_an_account_waits_when_inactive_with_an_unspent_verification_token(engine: AsyncEngine, case: str, waits: bool) -> None:
    """EMV-011 — contract 4: inactive, with a verification token of its own neither consumed nor revoked — live or expired —: the account waits. Active, with only spent links, with a password-reset link only, or with another account's link: it does not."""
    print_section(f"EMV-011: {case}")
    alice = await _alice_in(engine, case, utcnow())

    assert await _awaits(engine, alice.id) is waits
    print_success(f"waits: {waits}")


# =============================================================================
# 5. registration_email_work
# =============================================================================


@pytest.mark.asyncio
async def test_the_registration_email_replaces_the_hold_with_an_emailed_link(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter) -> None:
    """EMV-012 — contract 5: after a real hold, the work sends one message: to the account's address, from the configured sender, exactly what ``build_verification`` writes in English with the PUBLIC_URL ``/verify-email`` link of a new token, 24 hours, the public host as the instance — greeting nobody by name: the username its owner chose is in no part of it (decision N62). The new token carries the account's address, was issued now and is live; the hold is revoked now; the account still waits. One unit spent; the work returns None and logs the link emailed by ids and language, never the token nor the address."""
    print_section("EMV-012: the registration email")
    await _option(engine, "true")
    alice = await _add_user(engine, ALICE)
    moment = utcnow()

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        assert await _hold(engine, alice.id, now=moment) is True, "setup: the registration holds the account"
        with capture_logs() as events:
            returned = await verification.registration_email_work(alice.id, engine=engine, now=moment)

    assert returned is None
    assert len(fake.messages) == 1
    received = fake.messages[0]
    assert received.rcpt_tos == [alice.email]
    assert (_mailboxes(received.message["To"]), _mailboxes(received.message["From"])) == ([("", alice.email)], [SENDER])
    token = _token_in(_text(received))
    assert ALICE not in _text(received) + _html(received), "the verification email greets nobody by name: whoever signs up chooses the username (N62)"
    _assert_is(received, _expected(token))
    hold, emailed = await _rows(engine, alice.id)
    assert (hold.email, ensure_utc(hold.revoked_at), hold.consumed_at) == (None, moment, None)
    assert (emailed.email, emailed.consumed_at, emailed.revoked_at, emailed.token_hash) == (alice.email, None, None, token_service.hash_token(token))
    assert (ensure_utc(emailed.created_at), ensure_utc(emailed.expires_at)) == (moment, moment + TTL)
    assert await _status(engine, token) == TokenStatus.VALID
    assert (await _account(engine, alice.id)).is_active is False and await _awaits(engine, alice.id) is True
    assert budget.count() == 1
    emailed_events = _named(events, "Verification link emailed")
    assert [(event.get("user_id"), event.get("token_id"), event.get("language")) for event in emailed_events] == [(alice.id, emailed.id, "en")], events
    assert _holding(events, token, alice.email) == [], "no log event may hold the token or the address"
    print_success("one email, the hold revoked, the new link live with the address")


@pytest.mark.asyncio
@pytest.mark.parametrize(("own", "default", "language"), [pytest.param("it", "fr", "it", id="its-own-language"), pytest.param(None, "fr", "fr", id="the-instances-language")])
async def test_the_registration_email_is_in_the_accounts_language(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, own: str | None, default: str, language: str) -> None:
    """EMV-013 — contract 5: the email is written in the account's language — its own, else the instance's ``default_language`` (``flows.account_language``) — and the work logs that language."""
    print_section(f"EMV-013: own {own!r}, default {default!r}")
    moment = utcnow()
    alice, _hold_token = await _waiting(engine, ALICE, created=moment)
    await _set_default_language(engine, default)
    if own is not None:
        await _set_account_language(engine, alice.id, own)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with capture_logs() as events:
            await verification.registration_email_work(alice.id, engine=engine, now=moment)

    assert len(fake.messages) == 1
    _assert_is(fake.messages[0], _expected(_token_in(_text(fake.messages[0])), language=language))
    assert [event.get("language") for event in _named(events, "Verification link emailed")] == [language]
    print_success(f"written in {language}")


@pytest.mark.asyncio
async def test_the_emailed_link_verifies_the_account(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine) -> None:
    """EMV-014 — contracts 5 and 6: from the registration to the click: the link of the registration email verifies the account — active, ``email_verified_at`` the moment of the click, the link consumed by the account — and the account no longer waits."""
    print_section("EMV-014: registration, email, click")
    await _option(engine, "true")
    alice = await _add_user(engine, ALICE)
    moment = utcnow()
    clicked = moment + timedelta(minutes=10)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        await _hold(engine, alice.id, now=moment)
        await verification.registration_email_work(alice.id, engine=engine, now=moment)
    token = _token_in(_text(fake.messages[0]))
    verified = await _confirm(engine, token, now=clicked)

    assert (verified.id, verified.username, verified.is_active) == (alice.id, ALICE, True)
    account = await _account(engine, alice.id)
    assert (account.is_active, ensure_utc(account.email_verified_at)) == (True, clicked)
    emailed = (await _rows(engine, alice.id))[-1]
    assert (ensure_utc(emailed.consumed_at), emailed.consumed_by_user_id) == (clicked, alice.id)
    assert await _awaits(engine, alice.id) is False
    print_success("active, verified at the click, the link consumed")


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["activated-meanwhile", "deactivated-meanwhile", "no-such-account"])
async def test_nothing_is_sent_to_an_account_that_no_longer_waits(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, case: str) -> None:
    """EMV-015 — contract 5: between the registration and the work an administrator activated the account (its hold still live), or deactivated it (its hold revoked), or the id names no account: nothing is sent, made or revoked, nothing spent; the work logs that the account no longer waits."""
    print_section(f"EMV-015: {case}")
    moment = utcnow()
    alice, hold = await _waiting(engine, ALICE, created=moment)
    if case == "activated-meanwhile":
        async with AsyncSession(engine) as session:
            await session.execute(update(User).where(User.id == alice.id).values(is_active=True))
            await session.commit()
    elif case == "deactivated-meanwhile":
        await _spend(engine, hold, "revoked")
    before = _states(await _rows(engine, alice.id))
    user_id = alice.id if case != "no-such-account" else alice.id + 1_000

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with capture_logs() as events:
            returned = await verification.registration_email_work(user_id, engine=engine, now=moment)

    assert returned is None
    assert (fake.connections, budget.count()) == (0, 0)
    assert _states(await _rows(engine, alice.id)) == before
    assert [(event.get("log_level"), event.get("user_id")) for event in _named(events, "Verification email: the account no longer waits")] == [("info", user_id)], events
    print_success("nothing sent, nothing made")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case", "reason", "code"),
    [
        pytest.param("email-off", "EmailUnavailableError", "EMAIL_NOT_CONFIGURED", id="email-off"),
        pytest.param("email-unusable", "EmailUnavailableError", "SMTP_TLS_INVALID", id="email-unusable"),
        pytest.param("links-missing", "EmailLinksUnavailableError", "PUBLIC_URL_MISSING", id="links-missing"),
        pytest.param("links-invalid", "EmailLinksUnavailableError", "PUBLIC_URL_INVALID", id="links-invalid"),
        pytest.param("blocked", "EmailUnavailableError", "INSTANCE_BLOCKED", id="blocked"),
        pytest.param("budget-spent", "EmailRateLimitedError", "EMAIL_RATE_LIMITED", id="budget-spent"),
    ],
)
async def test_the_work_makes_nothing_when_no_email_can_go(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, clock: FakeClock, network: list[str], case: str, reason: str, code: str) -> None:
    """EMV-016 — contract 5: the configuration changed between the registration and the work — email off or unusable, links missing or invalid, the instance blocked, the hourly budget spent —: no token is made or revoked, the hold stays live and the only token, the account still waits; nothing is sent and the work logs a warning with the type and the code of the refusal. Nothing raised, no host looked up."""
    print_section(f"EMV-016: {case}")
    moment = utcnow()
    alice, hold = await _waiting(engine, ALICE, created=moment)
    if case == "budget-spent":
        _usable_without_a_server(monkeypatch, max_per_hour="1")
        clock.now = START
        assert budget.hit(limit=1).allowed, "setup: the only unit of the hour"
        clock.now = START + 60
    else:
        _set_up(monkeypatch, case)

    with capture_logs() as events:
        returned = await verification.registration_email_work(alice.id, engine=engine, now=moment)

    assert returned is None
    assert _states(await _rows(engine, alice.id)) == [(hold.record.id, None, False, False)]
    assert await _status(engine, hold.token) == TokenStatus.VALID and await _awaits(engine, alice.id) is True
    warnings = _named(events, "Verification email: not sent")
    assert [(event.get("log_level"), event.get("reason"), event.get("code")) for event in warnings] == [("warning", reason, code)], events
    assert network == []
    print_success(f"{reason} {code}: nothing made, the hold live")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure", "level", "logged_as", "spent"),
    [
        pytest.param("smtp-refuses-the-address", "warning", "EmailDeliveryError", 1, id="smtp-refuses-the-address"),
        pytest.param("an-address-that-is-not-one-address", "warning", "EmailRecipientError", 0, id="an-address-that-is-not-one-address"),
        pytest.param("send-raises-an-unexpected-error", "error", "RuntimeError", 0, id="send-raises-an-unexpected-error"),
        pytest.param("the-language-read-fails", "error", "RuntimeError", 0, id="the-language-read-fails"),
        pytest.param("the-link-cannot-be-built", "warning", "EmailLinksUnavailableError", 0, id="the-link-cannot-be-built"),
        pytest.param("the-builder-raises", "error", "RuntimeError", 0, id="the-builder-raises"),
    ],
)
async def test_a_registration_email_that_does_not_go_leaves_a_token_without_its_address(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, failure: str, level: str, logged_as: str, spent: int) -> None:
    """EMV-017 — contract 5: the work committed its token, then something failed — ``send_email`` (the SMTP server refusing the address, an address that is not one address, any other error), reading the account's language once it has queried the database, building the link, building the email —: nothing is sent and nothing raised; the hold is revoked and the new token stays unspent but without its address, so the account still waits; the work logs the failure by type. That token verifies nothing: confirming it is ``revoked``, and it is left as it is — still live, the account still inactive and still waiting."""
    print_section(f"EMV-017: {failure}")
    moment = utcnow()
    address = "zq_alice@example.com, zq-other@example.com" if failure == "an-address-that-is-not-one-address" else None
    alice, hold = await _waiting(engine, ALICE, created=moment - timedelta(minutes=1), email=address)
    #: (token, id) of each token the work issued, read at once: the work's rollback expires its row object.
    issued: list[tuple[str, int]] = []
    issue = token_service.issue_token

    async def recording(session: AsyncSession, purpose: AccountTokenPurpose, **arguments: object) -> IssuedToken:
        result = await issue(session, purpose, **arguments)
        issued.append((result.token, result.record.id))
        return result

    async def failing_send(*arguments: object, **keywords: object) -> None:
        raise RuntimeError("zq-send failure")

    async def failing_language(session: AsyncSession, user_id: int) -> str:
        await session.execute(select(UserSettings.language).where(UserSettings.user_id == user_id))
        raise RuntimeError("zq-language failure")

    def failing_link(*arguments: object) -> str:
        raise EmailLinksUnavailableError("PUBLIC_URL_MISSING")

    def failing_builder(**arguments: object) -> object:
        raise RuntimeError("zq-builder failure")

    replaced = {
        "send-raises-an-unexpected-error": ("send_email", failing_send),
        "the-language-read-fails": ("account_language", failing_language),
        "the-link-cannot-be-built": ("email_link", failing_link),
        "the-builder-raises": ("build_verification", failing_builder),
    }
    with FakeSmtpServer(refuse_recipients={alice.email} if failure == "smtp-refuses-the-address" else ()) as fake:
        _ready(monkeypatch, fake)
        monkeypatch.setattr(token_service, "issue_token", recording)
        if failure in replaced:
            monkeypatch.setattr(verification, *replaced[failure])
        with capture_logs() as events:
            returned = await verification.registration_email_work(alice.id, engine=engine, now=moment)
        monkeypatch.setattr(token_service, "issue_token", issue)

    assert returned is None
    assert fake.messages == []
    assert len(issued) == 1, "barrier: the work made its token before the failure"
    token, token_id = issued[0]
    assert _states(await _rows(engine, alice.id)) == [(hold.record.id, None, False, True), (token_id, None, False, False)]
    assert await _awaits(engine, alice.id) is True
    failures = [event for event in _named(events, "Verification email:") if event.get("log_level") in ("warning", "error")]
    assert [(event.get("log_level"), event.get("reason") or event.get("error")) for event in failures] == [(level, logged_as)], events
    assert budget.count() == spent
    with pytest.raises(verification.EmailVerificationLinkInvalidError) as refused:
        await _confirm(engine, token, now=moment)
    assert refused.value.code == "revoked"
    assert await _status(engine, token) == TokenStatus.VALID, "refused, but not revoked: it may be the account's only token"
    account = await _account(engine, alice.id)
    assert (account.is_active, account.email_verified_at) == (False, None)
    assert await _awaits(engine, alice.id) is True
    print_success(f"{logged_as}: the token kept without its address; refused, left live, the account waiting")


@pytest.mark.asyncio
async def test_after_a_registration_email_that_did_not_go_resend_works_at_once(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine) -> None:
    """EMV-018 — contracts 5 and 7: the registration email was refused by the SMTP server; thirty seconds later its owner asks for the link again: the token that reached nobody is not counted as an email — no 429 —, a new link goes out, exactly the verification email, and replaces it."""
    print_section("EMV-018: resend after a failed registration email")
    moment = utcnow()
    alice, hold = await _waiting(engine, ALICE, created=moment - timedelta(minutes=1))

    with FakeSmtpServer(refuse_recipients={alice.email}) as refusing:
        _ready(monkeypatch, refusing)
        await verification.registration_email_work(alice.id, engine=engine, now=moment)
    assert refusing.messages == [] and len(await _rows(engine, alice.id)) == 2, "setup: the registration email did not go"
    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        language = await _resend(engine, ALICE, now=moment + timedelta(seconds=30))

    assert language == "en" and len(fake.messages) == 1
    token = _token_in(_text(fake.messages[0]))
    _assert_is(fake.messages[0], _expected(token))
    rows = await _rows(engine, alice.id)
    assert [(email, consumed, revoked) for _id, email, consumed, revoked in _states(rows)] == [(None, False, True), (None, False, True), (alice.email, False, False)]
    assert await _status(engine, token) == TokenStatus.VALID
    print_success("no 429: a new link went out")


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["the-builder-raises", "a-database-error-holding-the-address"])
async def test_an_unexpected_error_of_the_work_is_logged_as_its_type_alone(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, failure: str) -> None:
    """EMV-019 — contract 5: an unexpected error — while the email is built, or a database error whose statement parameters hold the account's address (the precondition: its text does) —: the work returns, raises nothing, sends nothing, and logs ``Verification email: the request failed`` at error level with the error's type alone — no traceback (``exc_info``), whose rendering would print the parameters —; no log event holds the address."""
    print_section(f"EMV-019: {failure}")
    moment = utcnow()
    alice, _hold_token = await _waiting(engine, ALICE, created=moment)
    error = OperationalError("SELECT users.id FROM users WHERE users.email = ?", (alice.email,), Exception("database is locked"))
    assert alice.email in str(error), "precondition: the error's text holds the address"

    def failing_builder(**arguments: object) -> object:
        raise RuntimeError("zq-unexpected failure")

    async def failing_lookup(session: AsyncSession, user_id: int) -> User:
        raise error

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        if failure == "the-builder-raises":
            monkeypatch.setattr(verification, "build_verification", failing_builder)
        else:
            monkeypatch.setattr(user_service, "get_user_by_id", failing_lookup)
        with capture_logs() as events:
            returned = await verification.registration_email_work(alice.id, engine=engine, now=moment)

    assert returned is None
    assert fake.messages == []
    failures = [event for event in events if event.get("log_level") in ("warning", "error")]
    expected_type = "RuntimeError" if failure == "the-builder-raises" else "OperationalError"
    assert [(event.get("event"), event.get("log_level"), event.get("error")) for event in failures] == [("Verification email: the request failed", "error", expected_type)], failures
    assert "exc_info" not in failures[0], f"no traceback: {failures[0]}"
    assert _holding(events, alice.email) == [], f"a log event holds the address: {events}"
    print_success(f"logged as {expected_type}, no traceback, no address")


@pytest.mark.asyncio
async def test_the_work_never_emails_twice_within_five_minutes(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter) -> None:
    """EMV-020 — contract 5: the account was emailed a link two minutes ago, still live (it waits through it): counted again inside the write transaction, the new link would be the second in five minutes, so the work rolls everything back — no token of its own, the earlier link live again —, sends nothing, spends nothing, raises nothing, and logs ``EmailRateLimitedError``."""
    print_section("EMV-020: twice within five minutes")
    moment = utcnow()
    alice = await _add_user(engine, ALICE, active=False)
    earlier = await _emailed(engine, alice, created=moment - timedelta(minutes=2))

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with capture_logs() as events:
            returned = await verification.registration_email_work(alice.id, engine=engine, now=moment)

    assert returned is None
    assert (fake.connections, budget.count()) == (0, 0)
    assert _states(await _rows(engine, alice.id)) == [(earlier.record.id, alice.email, False, False)]
    assert await _status(engine, earlier.token) == TokenStatus.VALID
    assert [(event.get("reason"), event.get("code")) for event in _named(events, "Verification email: not sent")] == [("EmailRateLimitedError", "EMAIL_RATE_LIMITED")], events
    print_success("rolled back: the earlier link live, nothing sent")


# =============================================================================
# 6. confirm_email
# =============================================================================


@pytest.mark.asyncio
async def test_a_live_emailed_link_verifies_and_revokes_the_accounts_other_verification_tokens(engine: AsyncEngine) -> None:
    """EMV-021 — contract 6: Alice, inactive, holds a leftover hold, a link emailed an hour ago and the one emailed ten minutes ago, which she clicks; she also holds a live password-reset link, and Bob a live verification link. The answer is Alice, active; stored: active, ``email_verified_at`` the moment, the clicked link consumed then by Alice, her hold and older link revoked then; her reset link and Bob's link still live, Bob still waiting. Committed: a fresh session reads it. The log names the account and the token by id, never the token."""
    print_section("EMV-021: a live link verifies")
    moment = utcnow()
    alice = await _add_user(engine, ALICE, active=False)
    hold = await _issue(engine, VERIFICATION, user_id=alice.id, now=moment - timedelta(hours=2))
    older = await _emailed(engine, alice, created=moment - timedelta(hours=1))
    clicked = await _emailed(engine, alice, created=moment - timedelta(minutes=10))
    reset = await _issue(engine, PASSWORD_RESET, user_id=alice.id, now=moment)
    bob = await _add_user(engine, BOB, active=False)
    bobs = await _emailed(engine, bob, created=moment)

    with capture_logs() as events:
        verified = await _confirm(engine, clicked.token, now=moment)

    assert (verified.id, verified.username, verified.is_active) == (alice.id, ALICE, True)
    account = await _account(engine, alice.id)
    assert (account.is_active, ensure_utc(account.email_verified_at)) == (True, moment)
    by_id = {row.id: row for row in await _rows(engine, alice.id)}
    assert (ensure_utc(by_id[clicked.record.id].consumed_at), by_id[clicked.record.id].consumed_by_user_id, by_id[clicked.record.id].revoked_at) == (moment, alice.id, None)
    assert [ensure_utc(by_id[issued.record.id].revoked_at) for issued in (hold, older)] == [moment, moment]
    assert await _status(engine, reset.token, PASSWORD_RESET) == TokenStatus.VALID
    assert await _status(engine, bobs.token) == TokenStatus.VALID and await _awaits(engine, bob.id) is True
    assert [(event.get("user_id"), event.get("token_id")) for event in _named(events, "Email verified")] == [(alice.id, clicked.record.id)], events
    assert _holding(events, clicked.token, hold.token, older.token) == []
    print_success("active, verified now, the link consumed, the others revoked")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "status"),
    [
        pytest.param("expired", "expired", id="expired"),
        pytest.param("consumed", "consumed", id="consumed"),
        pytest.param("revoked", "revoked", id="revoked"),
        pytest.param("never-issued", "unknown", id="never-issued"),
        pytest.param("the-accounts-reset-link", "unknown", id="the-accounts-reset-link"),
        pytest.param("an-invitation", "unknown", id="an-invitation"),
    ],
)
async def test_a_link_that_is_not_a_live_verification_link_is_refused_with_its_status(engine: AsyncEngine, kind: str, status: str) -> None:
    """EMV-022 — contract 6: an expired, consumed or revoked verification link, a token never issued, and a live token of another purpose — the account's own reset link, an invitation to its address — are refused with ``EmailVerificationLinkInvalidError`` and their status (another purpose's token is ``unknown``). Nothing changes: the account inactive and unverified, its live link still live, a token of another purpose still live for its purpose."""
    print_section(f"EMV-022: {kind}")
    moment = utcnow()
    alice = await _add_user(engine, ALICE, active=False)
    keeper = await _emailed(engine, alice, created=moment - timedelta(minutes=30))
    other_purpose: tuple[IssuedToken, AccountTokenPurpose] | None = None
    if kind == "expired":
        token = (await _emailed(engine, alice, created=moment - TTL - timedelta(hours=1))).token
    elif kind in ("consumed", "revoked"):
        token = (await _emailed(engine, alice, created=moment - timedelta(minutes=40), how=kind)).token
    elif kind == "never-issued":
        token = NEVER_ISSUED
    elif kind == "the-accounts-reset-link":
        other_purpose = (await _issue(engine, PASSWORD_RESET, user_id=alice.id, now=moment), PASSWORD_RESET)
        token = other_purpose[0].token
    else:
        other_purpose = (await _issue(engine, INVITE, email=alice.email, now=moment), INVITE)
        token = other_purpose[0].token

    with pytest.raises(verification.EmailVerificationLinkInvalidError) as refused:
        await _confirm(engine, token, now=moment)

    assert refused.value.code == status
    account = await _account(engine, alice.id)
    assert (account.is_active, account.email_verified_at) == (False, None)
    assert await _status(engine, keeper.token) == TokenStatus.VALID
    if other_purpose is not None:
        assert await _status(engine, other_purpose[0].token, other_purpose[1]) == TokenStatus.VALID
    print_success(f"refused: {status}, nothing changed")


@pytest.mark.asyncio
async def test_a_token_without_an_address_verifies_nothing_and_is_left_live(engine: AsyncEngine) -> None:
    """EMV-023 — contract 6: a verification token without an address — the hold, whose text never leaves — verifies nothing: refused as ``revoked``, and left as it is — still live —, for it may be the account's only unspent token and revoking it would end the wait. The account stays inactive, unverified and waiting. The log says the link's email did not go out, naming the account and the token by id."""
    print_section("EMV-023: the hold")
    moment = utcnow()
    alice, hold = await _waiting(engine, ALICE, created=moment)

    with capture_logs() as events:
        with pytest.raises(verification.EmailVerificationLinkInvalidError) as refused:
            await _confirm(engine, hold.token, now=moment)

    assert refused.value.code == "revoked"
    assert await _status(engine, hold.token) == TokenStatus.VALID
    account = await _account(engine, alice.id)
    assert (account.is_active, account.email_verified_at) == (False, None)
    assert await _awaits(engine, alice.id) is True
    refusals = _named(events, "Email verification refused")
    assert [(event.get("event"), event.get("user_id"), event.get("token_id")) for event in refusals] == [("Email verification refused: the link's email did not go out", alice.id, hold.record.id)], events
    assert _holding(events, hold.token) == []
    print_success("refused as revoked, left live, the account waiting")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("own", "sent_to", "verifies"),
    [
        pytest.param(None, "zq-old-alice@example.com", False, id="an-address-the-account-no-longer-has"),
        pytest.param(None, "ZQ_Alice@Example.COM", True, id="the-same-address-in-other-capitals"),
        pytest.param("zq_\u00e1lice@example.com", "zq_\u00c1lice@example.com", False, id="another-case-beyond-a-to-z-is-another-address"),
    ],
)
async def test_a_link_emailed_to_another_address_is_revoked(engine: AsyncEngine, own: str | None, sent_to: str, verifies: bool) -> None:
    """EMV-024 — contract 6: the address a live link was emailed to, against the account's, by ``user_service.same_email`` (A's one rule, decision P18). An address the account no longer has: the link revoked and refused as ``revoked``, the account inactive and unverified, the log saying the link was sent to another address. The account's own address in other A–Z capitals is the same address: the link verifies. The account's ``zq_álice@example.com`` and a link emailed to ``zq_Álice@example.com``, apart in the case of ``á`` alone — a letter beyond A–Z, compared as written —: another address, refused as the first, on the safe side. No case with spaces around: both addresses come from the database, where ``EmailStr`` stripped them, and ``same_email`` strips nothing (A's contract)."""
    print_section(f"EMV-024: sent to {sent_to!r}")
    moment = utcnow()
    alice = await _add_user(engine, ALICE, email=own, active=False)
    link = await _emailed(engine, alice, created=moment - timedelta(minutes=5), email=sent_to)

    if verifies:
        assert (await _confirm(engine, link.token, now=moment)).is_active is True
        assert (await _account(engine, alice.id)).is_active is True
    else:
        with capture_logs() as events:
            with pytest.raises(verification.EmailVerificationLinkInvalidError) as refused:
                await _confirm(engine, link.token, now=moment)
        assert refused.value.code == "revoked"
        assert await _status(engine, link.token) == TokenStatus.REVOKED
        account = await _account(engine, alice.id)
        assert (account.is_active, account.email_verified_at) == (False, None)
        assert [event.get("event") for event in _named(events, "Email verification refused")] == ["Email verification refused: the link was sent to another address"], events
    print_success("verified" if verifies else "revoked")


@pytest.mark.asyncio
async def test_a_link_spent_meanwhile_is_consumed_and_changes_nothing(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine) -> None:
    """EMV-025 — contract 6: the link passes the check, and another request spends it before this one does (committed by another session inside ``token_service.consume_token``, just before the real one): ``consumed``; this request's transaction is rolled back — the account not activated nor verified by it, its other unspent token not revoked."""
    print_section("EMV-025: spent meanwhile")
    moment = utcnow()
    alice, hold = await _waiting(engine, ALICE, created=moment - timedelta(hours=1))
    link = await _emailed(engine, alice, created=moment - timedelta(minutes=10))
    consume = token_service.consume_token
    raced: list[str] = []

    async def consumed_first(session: AsyncSession, token: str, purpose: AccountTokenPurpose, **arguments: object) -> AccountToken | None:
        if not raced:
            async with AsyncSession(engine) as other:
                assert await consume(other, token, purpose, now=moment) is not None, "setup: the other request spends the link"
                await other.commit()
            raced.append(token)
        return await consume(session, token, purpose, **arguments)

    monkeypatch.setattr(token_service, "consume_token", consumed_first)
    with pytest.raises(verification.EmailVerificationLinkInvalidError) as refused:
        await _confirm(engine, link.token, now=moment)

    assert refused.value.code == "consumed" and raced == [link.token]
    account = await _account(engine, alice.id)
    assert (account.is_active, account.email_verified_at) == (False, None)
    assert await _status(engine, hold.token) == TokenStatus.VALID
    print_success("consumed: nothing changed by this request")


@pytest.mark.asyncio
async def test_a_link_whose_account_is_gone_is_unknown(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine) -> None:
    """EMV-026 — contract 6: a live link whose account cannot be found any more is ``unknown``; the link is left as it was."""
    print_section("EMV-026: the account is gone")
    moment = utcnow()
    alice = await _add_user(engine, ALICE, active=False)
    link = await _emailed(engine, alice, created=moment)

    async def no_account(session: AsyncSession, user_id: int) -> None:
        return None

    monkeypatch.setattr(user_service, "get_user_by_id", no_account)
    with pytest.raises(verification.EmailVerificationLinkInvalidError) as refused:
        await _confirm(engine, link.token, now=moment)

    assert refused.value.code == "unknown"
    assert await _status(engine, link.token) == TokenStatus.VALID
    print_success("unknown, the link untouched")


@pytest.mark.asyncio
async def test_a_link_whose_email_failed_after_the_data_is_refused_and_the_account_still_waits(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine) -> None:
    """EMV-027 — contracts 5 and 6: the registration email reached the SMTP server — the link was in the data it took — and the server refused it after the data: as far as LibreFolio knows the email did not go, so the link lost its address. Its presenter, who has it all the same, is refused as ``revoked``, and the link is left live: the account still waits, unverified. «Resend» then works at once, its new link verifies the account, and the link that failed is revoked by it."""
    print_section("EMV-027: the email failed after the data, the link presented anyway")
    moment = utcnow()
    alice, _hold_token = await _waiting(engine, ALICE, created=moment - timedelta(minutes=1))
    send = verification.send_email
    handed: list[str] = []

    async def recording_send(content: object, **keywords: object) -> None:
        handed.append(content.text)
        await send(content, **keywords)

    with FakeSmtpServer(refuse_data=True) as refusing:
        _ready(monkeypatch, refusing)
        monkeypatch.setattr(verification, "send_email", recording_send)
        await verification.registration_email_work(alice.id, engine=engine, now=moment)
        monkeypatch.setattr(verification, "send_email", send)
    assert (refusing.connections, refusing.messages, len(handed)) == (1, [], 1), "setup: the data reached the server, which refused it"
    failed = _token_in(handed[0])

    with pytest.raises(verification.EmailVerificationLinkInvalidError) as refused:
        await _confirm(engine, failed, now=moment + timedelta(minutes=1))
    assert refused.value.code == "revoked"
    assert await _status(engine, failed) == TokenStatus.VALID
    assert (await _account(engine, alice.id)).is_active is False and await _awaits(engine, alice.id) is True

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        assert await _resend(engine, ALICE, now=moment + timedelta(minutes=2)) == "en"
    assert len(fake.messages) == 1
    fresh = _token_in(_text(fake.messages[0]))
    assert await _status(engine, failed) == TokenStatus.REVOKED
    assert (await _confirm(engine, fresh, now=moment + timedelta(minutes=3))).is_active is True
    account = await _account(engine, alice.id)
    assert (account.is_active, ensure_utc(account.email_verified_at)) == (True, moment + timedelta(minutes=3))
    print_success("refused and left live; resend worked; the new link verified")


# =============================================================================
# 7. resend_verification
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("by", ["username", "email"])
async def test_resend_emails_a_new_link_to_a_waiting_account(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, address_limit: SlidingWindowLimiter, by: str) -> None:
    """EMV-028 — contract 7: the right password for a waiting account, by username or by email address: the answer is the email's language; one message to the account's address, exactly the verification email of a new link; the hold revoked now, the new token carrying the address, issued now and live; the account still waits. One unit of the budget spent, one request counted for the client address."""
    print_section(f"EMV-028: by {by}")
    moment = utcnow()
    alice, hold = await _waiting(engine, ALICE, created=moment - timedelta(hours=1))

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        language = await _resend(engine, ALICE if by == "username" else alice.email, now=moment)

    assert language == "en"
    assert len(fake.messages) == 1 and fake.messages[0].rcpt_tos == [alice.email]
    token = _token_in(_text(fake.messages[0]))
    _assert_is(fake.messages[0], _expected(token))
    revoked_hold, emailed = await _rows(engine, alice.id)
    assert (revoked_hold.id, ensure_utc(revoked_hold.revoked_at)) == (hold.record.id, moment)
    assert (emailed.email, ensure_utc(emailed.created_at), emailed.token_hash) == (alice.email, moment, token_service.hash_token(token))
    assert await _status(engine, token) == TokenStatus.VALID and await _awaits(engine, alice.id) is True
    assert (budget.count(), address_limit.count(ADDRESS)) == (1, 1)
    print_success("en: a new link to the account's address")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("who", "password"),
    [
        pytest.param(NOBODY, ACCOUNT_PASSWORD, id="an-unknown-account"),
        pytest.param(ALICE, WRONG_PASSWORD, id="a-wrong-password-for-the-waiting-account"),
        pytest.param(BOB, WRONG_PASSWORD, id="a-wrong-password-for-an-active-account"),
        pytest.param(CAROL, WRONG_PASSWORD, id="a-wrong-password-for-a-deactivated-account"),
    ],
)
async def test_the_password_is_checked_as_the_login_checks_it(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, who: str, password: str) -> None:
    """EMV-029 — contract 7: an unknown account, or a wrong password — for a waiting, an active or a deactivated account —: one refusal, ``VerificationCredentialsError`` (``INVALID_CREDENTIALS``), before anything is said about the account. The password is checked once, through ``verify_password_or_dummy``, against the account's hash — or, for an unknown account, against none, which costs the same bcrypt check. Nothing sent, made or spent."""
    print_section(f"EMV-029: {who}, {'the right' if password == ACCOUNT_PASSWORD else 'a wrong'} password")
    moment = utcnow()
    accounts = {ALICE: (await _waiting(engine, ALICE, created=moment))[0], BOB: await _add_user(engine, BOB), CAROL: await _add_user(engine, CAROL, active=False)}
    checked: list[tuple[str, str | None]] = []
    verify = verification.verify_password_or_dummy

    def recording(plain: str, hashed: str | None) -> bool:
        checked.append((plain, hashed))
        return verify(plain, hashed)

    monkeypatch.setattr(verification, "verify_password_or_dummy", recording)
    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with pytest.raises(verification.VerificationCredentialsError) as refused:
            await _resend(engine, who, password, now=moment)

    assert refused.value.code == "INVALID_CREDENTIALS"
    assert checked == [(password, accounts[who].hashed_password if who in accounts else None)]
    assert (fake.connections, budget.count()) == (0, 0)
    assert [len(await _rows(engine, account.id)) for account in accounts.values()] == [1, 0, 0]
    print_success("INVALID_CREDENTIALS, the password checked once")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "error", "code"),
    [
        pytest.param("active", verification.EmailVerificationNotNeededError, "EMAIL_VERIFICATION_NOT_NEEDED", id="an-active-account"),
        pytest.param("deactivated", verification.VerificationAccountDisabledError, "ACCOUNT_DISABLED", id="a-deactivated-account"),
        pytest.param("deactivated-its-link-revoked", verification.VerificationAccountDisabledError, "ACCOUNT_DISABLED", id="a-deactivated-account-its-link-revoked"),
        pytest.param("verified-then-deactivated", verification.VerificationAccountDisabledError, "ACCOUNT_DISABLED", id="a-verified-then-deactivated-account"),
    ],
)
async def test_an_account_that_does_not_wait_gets_nothing(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, state: str, error: type[EmailError], code: str) -> None:
    """EMV-030 — contract 7: the right password for an account that does not wait: active — ``EMAIL_VERIFICATION_NOT_NEEDED`` —, or inactive without an unspent verification token — deactivated by an administrator, whose change of status revoked its link, or deactivated after its link was spent — ``ACCOUNT_DISABLED``. Nothing sent, made, revoked or spent."""
    print_section(f"EMV-030: {state}")
    moment = utcnow()
    carol = await _add_user(engine, CAROL, active=state == "active")
    if state == "deactivated-its-link-revoked":
        await _emailed(engine, carol, created=moment - timedelta(hours=1), how="revoked")
    elif state == "verified-then-deactivated":
        await _emailed(engine, carol, created=moment - timedelta(hours=1), how="consumed")
    before = _states(await _rows(engine, carol.id))

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with pytest.raises(error) as refused:
            await _resend(engine, CAROL, now=moment)

    assert refused.value.code == code
    assert (fake.connections, budget.count()) == (0, 0)
    assert _states(await _rows(engine, carol.id)) == before
    print_success(code)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("who", "case", "error", "code"),
    [
        pytest.param(NOBODY, "email-off", verification.VerificationCredentialsError, "INVALID_CREDENTIALS", id="unknown-email-off"),
        pytest.param(NOBODY, "blocked", verification.VerificationCredentialsError, "INVALID_CREDENTIALS", id="unknown-blocked"),
        pytest.param(BOB, "email-off", verification.EmailVerificationNotNeededError, "EMAIL_VERIFICATION_NOT_NEEDED", id="active-email-off"),
        pytest.param(CAROL, "email-off", verification.VerificationAccountDisabledError, "ACCOUNT_DISABLED", id="deactivated-email-off"),
        pytest.param(ALICE, "email-off", EmailUnavailableError, "EMAIL_NOT_CONFIGURED", id="waiting-email-off"),
        pytest.param(ALICE, "email-unusable", EmailUnavailableError, "SMTP_TLS_INVALID", id="waiting-email-unusable"),
        pytest.param(ALICE, "blocked", EmailUnavailableError, "INSTANCE_BLOCKED", id="waiting-blocked"),
        pytest.param(ALICE, "block-unreadable", EmailUnavailableError, "INSTANCE_BLOCKED", id="waiting-block-unreadable"),
        pytest.param(ALICE, "links-missing", EmailLinksUnavailableError, "PUBLIC_URL_MISSING", id="waiting-links-missing"),
        pytest.param(ALICE, "links-invalid", EmailLinksUnavailableError, "PUBLIC_URL_INVALID", id="waiting-links-invalid"),
    ],
)
async def test_the_credentials_and_the_account_come_before_the_configuration(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, network: list[str], who: str, case: str, error: type[EmailError], code: str) -> None:
    """EMV-031 — contract 7: the configuration is asked only once the password is right and the account waits: with email off or the instance blocked an unknown account is still ``INVALID_CREDENTIALS``, an active one ``EMAIL_VERIFICATION_NOT_NEEDED``, a deactivated one ``ACCOUNT_DISABLED``; a waiting account gets the instance's refusal — the block (blocking or unreadable), then email, then links. Nothing made, no host looked up."""
    print_section(f"EMV-031: {who}, {case}")
    moment = utcnow()
    alice, hold = await _waiting(engine, ALICE, created=moment)
    await _add_user(engine, BOB)
    await _add_user(engine, CAROL, active=False)
    _set_up(monkeypatch, case)

    with pytest.raises(error) as refused:
        await _resend(engine, who, now=moment)

    assert (type(refused.value), refused.value.code) == (error, code)
    assert _states(await _rows(engine, alice.id)) == [(hold.record.id, None, False, False)]
    assert network == []
    print_success(f"{error.__name__}: {code}")


@pytest.mark.asyncio
async def test_a_full_address_counter_refuses_before_the_password_and_costs_nothing(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, clock: FakeClock, address_limit: SlidingWindowLimiter) -> None:
    """EMV-032 — contract 7: ``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS=3``, the address's counter full since START (three emails that went). A request a minute later, with the right password, is refused before any password is checked — the counter is only looked at —: ``EmailRateLimitedError`` with ``3600 - 60`` seconds, and the refusal spends nothing (still 3). Another address is not counted with it and gets its link. Once the window has passed, the first address reaches the password again."""
    print_section("EMV-032: a full counter, looked at before the password")
    monkeypatch.setenv(SIGNUP_PER_ADDRESS, "3")
    moment = utcnow()
    await _waiting(engine, ALICE, created=moment)
    checked: list[str] = []
    verify = verification.verify_password_or_dummy

    def recording(plain: str, hashed: str | None) -> bool:
        checked.append(plain)
        return verify(plain, hashed)

    monkeypatch.setattr(verification, "verify_password_or_dummy", recording)
    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        clock.now = START
        for _spent in range(3):
            assert delivery.address_budget_hit(ADDRESS).allowed, "setup: three emails of the address"
        clock.now = START + 60
        with pytest.raises(EmailRateLimitedError) as limited:
            await _resend(engine, ALICE, now=moment)
        counted_after_the_refusal = address_limit.count(ADDRESS)
        checked_before_the_other_address = len(checked)
        assert await _resend(engine, ALICE, address=OTHER_ADDRESS, now=moment) == "en"
        clock.now = START + 3600
        with pytest.raises(verification.VerificationCredentialsError):
            await _resend(engine, ALICE, WRONG_PASSWORD, now=moment)

    assert limited.value.retry_after == 3540.0
    assert checked_before_the_other_address == 0, "a full counter must refuse before any password is checked"
    assert counted_after_the_refusal == 3, "the refusal spends nothing"
    assert len(fake.messages) == 1
    assert (address_limit.count(ADDRESS), address_limit.count(OTHER_ADDRESS)) == (0, 1)
    print_success("refused for 3540 s, its password unchecked, nothing spent")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("first", "other_form", "key"),
    [
        pytest.param(SAME_64[0], SAME_64[1], SAME_64_KEY, id="two-addresses-of-one-ipv6-64"),
        pytest.param(ADDRESS, MAPPED, ADDRESS, id="an-ipv4-address-and-its-mapped-form"),
    ],
)
async def test_the_counter_per_address_is_keyed_by_client_rate_key(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, address_limit: SlidingWindowLimiter, first: str, other_form: str, key: str) -> None:
    """EMV-033 — contract 7: the emails are counted by workstream H's ``client_rate_key``, the one home of the per-client key (decision P17): two addresses of one IPv6 /64 are one client, and an IPv4-mapped IPv6 address is the IPv4 address. ``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS=2``: two waiting accounts get their link, one from each form, counted under ONE key; a third waiting account, from either form, is refused."""
    print_section(f"EMV-033: {first} then {other_form}")
    monkeypatch.setenv(SIGNUP_PER_ADDRESS, "2")
    moment = utcnow()
    for name in (ALICE, BOB, CAROL):
        await _waiting(engine, name, created=moment)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        assert await _resend(engine, ALICE, address=first, now=moment) == "en"
        assert await _resend(engine, BOB, address=other_form, now=moment) == "en"
        with pytest.raises(EmailRateLimitedError):
            await _resend(engine, CAROL, address=first, now=moment)
        with pytest.raises(EmailRateLimitedError):
            await _resend(engine, CAROL, address=other_form, now=moment)

    assert len(fake.messages) == 2
    assert address_limit.count(key) == 2 and len(address_limit) == 1
    print_success(f"two emails under {key}, the third refused from either form")


@pytest.mark.asyncio
async def test_wrong_passwords_never_use_the_address_counter(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, address_limit: SlidingWindowLimiter) -> None:
    """EMV-036 — a try is not an email: six wrong passwords and requests for an unknown account from one client address (``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS=3``) leave the counter at 0 — the sign-in's limit on wrong passwords is what brakes them —, so a registration still passes the counter afterwards, and the right password then gets its link, counted once."""
    print_section("EMV-036: wrong passwords cost the counter nothing")
    monkeypatch.setenv(SIGNUP_PER_ADDRESS, "3")
    moment = utcnow()
    await _waiting(engine, ALICE, created=moment)
    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        for attempt in range(6):
            with pytest.raises(verification.VerificationCredentialsError):
                await _resend(engine, NOBODY if attempt % 2 else ALICE, WRONG_PASSWORD, now=moment)
        after_the_wrong_ones = address_limit.count(ADDRESS)
        registration = await verification.registration_email_verdict(ADDRESS)
        language = await _resend(engine, ALICE, now=moment)

    assert after_the_wrong_ones == 0
    assert registration.allowed is True, "wrong passwords did not use up the registrations of the address"
    assert language == "en" and len(fake.messages) == 1
    assert address_limit.count(ADDRESS) == 2, "the registration's unit and the one email that went"
    print_success("0 after six wrong passwords; then a registration and the one email that went")


@pytest.mark.asyncio
async def test_a_resend_stopped_by_the_account_or_the_mailbox_does_not_use_the_address_counter(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, address_limit: SlidingWindowLimiter, mailbox_limit: SlidingWindowLimiter) -> None:
    """EMV-037 — the address's unit is spent at the last moment, when the email is about to leave: a resend refused by the limit per account (a link emailed two minutes ago: 180 s) or by the limit per recipient mailbox (three verification emails this hour) leaves the counter at 0, and nothing is created."""
    print_section("EMV-037: refused by the account or the mailbox")
    moment = utcnow()
    alice, _hold = await _waiting(engine, ALICE, created=moment - timedelta(minutes=10))
    await _emailed(engine, alice, created=moment - timedelta(minutes=2))
    bob, _hold = await _waiting(engine, BOB, created=moment - timedelta(minutes=10))
    for _spent in range(3):
        mailbox_limit.hit(delivery.mailbox_budget_key(bob.email))
    rows_before = (len(await _rows(engine, alice.id)), len(await _rows(engine, bob.id)))

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with pytest.raises(EmailRateLimitedError) as by_account:
            await _resend(engine, ALICE, now=moment)
        with pytest.raises(EmailRateLimitedError):
            await _resend(engine, BOB, now=moment)

    assert by_account.value.retry_after == 180.0
    assert address_limit.count(ADDRESS) == 0 and fake.messages == []
    assert (len(await _rows(engine, alice.id)), len(await _rows(engine, bob.id))) == rows_before
    print_success("0 units spent by two refusals")


@pytest.mark.asyncio
async def test_the_address_counter_is_spent_when_the_email_is_about_to_leave_and_stays_spent_if_smtp_fails(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, address_limit: SlidingWindowLimiter) -> None:
    """EMV-038 — ``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS=2``: a resend that sends spends one unit; one whose email the SMTP server refuses (``RECIPIENT_REFUSED``) also does — an email was tried, and the link stays a hold, so the account still waits —; the next resend from that address, even with the right password, is refused with the true wait (3600 s: all its units were spent together)."""
    print_section("EMV-038: spent before the email, kept when SMTP fails")
    monkeypatch.setenv(SIGNUP_PER_ADDRESS, "2")
    moment = utcnow()
    alice, _hold = await _waiting(engine, ALICE, created=moment - timedelta(minutes=10))
    await _waiting(engine, BOB, created=moment - timedelta(minutes=10))
    await _waiting(engine, CAROL, created=moment - timedelta(minutes=10))

    with FakeSmtpServer(refuse_recipients={alice.email}) as refusing:
        _ready(monkeypatch, refusing)
        with pytest.raises(EmailDeliveryError):
            await _resend(engine, ALICE, now=moment)
    counted_after_the_failure = address_limit.count(ADDRESS)
    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        assert await _resend(engine, BOB, now=moment) == "en"
        with pytest.raises(EmailRateLimitedError) as refused:
            await _resend(engine, CAROL, now=moment)

    assert counted_after_the_failure == 1, "the failed email used its unit"
    assert address_limit.count(ADDRESS) == 2 and len(fake.messages) == 1
    assert refused.value.retry_after == pytest.approx(3600)
    assert await _awaits(engine, alice.id) is True
    print_success("a failed email stays counted; the third is refused with the true wait")


@pytest.mark.asyncio
async def test_without_a_client_address_the_limit_per_address_does_not_apply(engine: AsyncEngine, address_limit: SlidingWindowLimiter) -> None:
    """EMV-034 — contract 7: without a client address (a unix socket) nothing is counted per address — one shared count would let one client block everyone —: twenty-two requests all reach the password."""
    print_section("EMV-034: no client address")
    await _waiting(engine, ALICE, created=utcnow())

    for _attempt in range(22):
        with pytest.raises(verification.VerificationCredentialsError):
            await _resend(engine, ALICE, WRONG_PASSWORD, address=None)

    assert len(address_limit) == 0
    print_success("twenty-two requests, none counted")


@pytest.mark.asyncio
async def test_a_resend_refused_by_the_address_says_the_longest_wait_with_the_instance(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, clock: FakeClock, budget: SlidingWindowLimiter, address_limit: SlidingWindowLimiter) -> None:
    """EMV-035 — the wait of a resend stopped by the address's counter is the longest among the counters that stop it. ``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS=1``, the address's only unit spent at START, the instance's budget (``LIBREFOLIO_SMTP_MAX_PER_HOUR=1``) spent at START + 600: at START + 700 the resend is ``EmailRateLimitedError`` with ``3600 - 100`` seconds (the instance's, spent at START + 600, longer than the address's ``3600 - 700``); with the budget whole it is the address's own. Neither counter changes: a refused hit is not recorded."""
    print_section("EMV-035: the longest wait")
    monkeypatch.setenv(SIGNUP_PER_ADDRESS, "1")
    _usable_without_a_server(monkeypatch, max_per_hour="1")
    await _waiting(engine, ALICE, created=utcnow())

    clock.now = START
    assert delivery.address_budget_hit(ADDRESS).allowed, "setup: the address's only unit"
    clock.now = START + 700
    with pytest.raises(EmailRateLimitedError) as address_alone:
        await _resend(engine, ALICE)
    clock.now = START + 600
    assert budget.hit(limit=1).allowed, "setup: the only unit of the hour"
    clock.now = START + 700
    with pytest.raises(EmailRateLimitedError) as with_the_instance:
        await _resend(engine, ALICE)

    assert address_alone.value.retry_after == pytest.approx(3600 - 700)
    assert with_the_instance.value.retry_after == pytest.approx(3600 - 100)
    assert (address_limit.count(ADDRESS), budget.count()) == (1, 1)
    print_success("the address's wait alone; the instance's when it is longer")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("links", "wait"),
    [
        pytest.param(((2, "live"),), 180.0, id="a-link-emailed-two-minutes-ago"),
        pytest.param(((50, "revoked"), (30, "revoked"), (10, "live")), 600.0, id="three-links-emailed-in-the-hour"),
        pytest.param(((50, "revoked"), (30, "revoked"), (2, "live")), 600.0, id="three-in-the-hour-the-last-recent-the-longer-wait"),
        pytest.param(((50, "consumed"), (30, "revoked"), (10, "live")), 600.0, id="spent-links-count-too"),
    ],
)
async def test_the_limits_per_account_count_the_links_emailed(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, links: tuple[tuple[int, str], ...], wait: float) -> None:
    """EMV-035 — contract 7: per account, one verification email every 5 minutes and 3 an hour, counted on the links emailed — tokens carrying an address, spent or not —: a link emailed two minutes ago waits 180 s more; three in the hour wait until the oldest leaves it; both at once, the longer wait. ``EmailRateLimitedError`` with exactly that wait; nothing sent, made, revoked or spent."""
    print_section(f"EMV-035: emailed {[minutes for minutes, _how in links]} minutes ago")
    moment = utcnow()
    alice = await _add_user(engine, ALICE, active=False)
    for minutes, how in links:
        await _emailed(engine, alice, created=moment - timedelta(minutes=minutes), how=how)
    before = _states(await _rows(engine, alice.id))

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with pytest.raises(EmailRateLimitedError) as limited:
            await _resend(engine, ALICE, now=moment)

    assert limited.value.retry_after == wait
    assert (fake.connections, budget.count()) == (0, 0)
    assert _states(await _rows(engine, alice.id)) == before
    print_success(f"wait {wait:.0f} s")


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["holds-never-count", "links-older-than-an-hour", "another-accounts-links"])
async def test_what_the_limits_per_account_do_not_count(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, case: str) -> None:
    """EMV-036 — contract 7: tokens without an address — four holds made in the last minute — never count; links emailed more than an hour ago do not; nor do another account's links emailed a minute ago: the link goes out."""
    print_section(f"EMV-036: {case}")
    moment = utcnow()
    alice = await _add_user(engine, ALICE, active=False)
    if case == "holds-never-count":
        for seconds in (60, 45, 30, 15):
            await _issue(engine, VERIFICATION, user_id=alice.id, now=moment - timedelta(seconds=seconds))
    elif case == "links-older-than-an-hour":
        for minutes, how in ((80, "revoked"), (70, "revoked"), (61, "live")):
            await _emailed(engine, alice, created=moment - timedelta(minutes=minutes), how=how)
    else:
        await _issue(engine, VERIFICATION, user_id=alice.id, now=moment - timedelta(minutes=10))
        bob = await _add_user(engine, BOB, active=False)
        for seconds in (90, 60, 30):
            await _emailed(engine, bob, created=moment - timedelta(seconds=seconds))

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        assert await _resend(engine, ALICE, now=moment) == "en"

    assert len(fake.messages) == 1
    print_success("not counted: the link went out")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("link", "max_users", "allowed"),
    [
        pytest.param("expired", "1", False, id="the-link-expired-and-the-instance-is-full"),
        pytest.param("expired", "2", True, id="the-link-expired-and-a-place-is-free"),
        pytest.param("expired", None, True, id="the-link-expired-and-no-limit"),
        pytest.param("live", "1", True, id="a-live-link-keeps-its-place-on-a-full-instance"),
    ],
)
async def test_an_expired_link_needs_a_place_again(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, link: str, max_users: str | None, allowed: bool) -> None:
    """EMV-037 — contract 7: the instance holds one active account. A waiting account whose link is still live keeps its place: its link goes out even on a full instance. One whose link expired needs a place again: with ``LIBREFOLIO_MAX_USERS`` reached, ``VerificationUserLimitError`` (``USER_LIMIT_REACHED``) and nothing sent, made or spent; with a place free, or no limit, the link goes out."""
    print_section(f"EMV-037: link {link}, LIBREFOLIO_MAX_USERS={max_users!r}")
    moment = utcnow()
    await _add_user(engine, ADMIN)
    alice, hold = await _waiting(engine, ALICE, created=moment - (TTL + timedelta(hours=1) if link == "expired" else timedelta(hours=1)))
    if max_users is not None:
        monkeypatch.setenv(MAX_USERS_VARIABLE, max_users)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        if allowed:
            assert await _resend(engine, ALICE, now=moment) == "en"
        else:
            with pytest.raises(verification.VerificationUserLimitError) as refused:
                await _resend(engine, ALICE, now=moment)
            assert refused.value.code == "USER_LIMIT_REACHED"

    if allowed:
        assert len(fake.messages) == 1
    else:
        assert (fake.connections, budget.count()) == (0, 0)
        assert _states(await _rows(engine, alice.id)) == [(hold.record.id, None, False, False)]
    print_success("sent" if allowed else "USER_LIMIT_REACHED")


@pytest.mark.asyncio
async def test_a_spent_budget_refuses_before_anything_is_made(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, clock: FakeClock) -> None:
    """EMV-038 — contract 7: the hourly budget of the instance spent ten minutes ago: ``EmailRateLimitedError`` with the 3000 s until it frees; no token made or revoked, no connection."""
    print_section("EMV-038: the budget")
    moment = utcnow()
    alice, hold = await _waiting(engine, ALICE, created=moment)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake, max_per_hour="1")
        clock.now = START
        assert budget.hit(limit=1).allowed, "setup: the only unit of the hour"
        clock.now = START + 600
        with pytest.raises(EmailRateLimitedError) as limited:
            await _resend(engine, ALICE, now=moment)

    assert limited.value.retry_after == 3000.0
    assert fake.connections == 0
    assert _states(await _rows(engine, alice.id)) == [(hold.record.id, None, False, False)]
    print_success("3000 s, nothing made")


@pytest.mark.asyncio
async def test_a_refusal_of_the_smtp_server_is_raised_and_resend_works_at_once(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine) -> None:
    """EMV-039 — contract 7: the SMTP server refuses the account's address: ``EmailDeliveryError`` (``RECIPIENT_REFUSED``) is raised; the hold is revoked and the new token stays unspent without its address, so the account still waits. Asked again thirty seconds later, the link goes out — the failed one was not counted as an email."""
    print_section("EMV-039: the SMTP server refuses")
    moment = utcnow()
    alice, hold = await _waiting(engine, ALICE, created=moment - timedelta(minutes=1))

    with FakeSmtpServer(refuse_recipients={alice.email}) as refusing:
        _ready(monkeypatch, refusing)
        with pytest.raises(EmailDeliveryError) as raised:
            await _resend(engine, ALICE, now=moment)
    assert raised.value.code == "RECIPIENT_REFUSED" and refusing.messages == []
    rows = await _rows(engine, alice.id)
    assert [(email, consumed, revoked) for _id, email, consumed, revoked in _states(rows)] == [(None, False, True), (None, False, False)]
    assert await _awaits(engine, alice.id) is True
    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        assert await _resend(engine, ALICE, now=moment + timedelta(seconds=30)) == "en"

    assert len(fake.messages) == 1
    print_success("RECIPIENT_REFUSED raised; thirty seconds later the link went out")


@pytest.mark.asyncio
async def test_an_address_that_is_not_one_address_is_refused_before_any_connection(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter) -> None:
    """EMV-040 — contract 7: the account's address is not one address: ``EmailRecipientError`` — a ``ValueError`` — is raised; no connection, nothing spent; the new token stays without an address and the account still waits."""
    print_section("EMV-040: not one address")
    moment = utcnow()
    alice, _hold_token = await _waiting(engine, ALICE, created=moment, email="zq_alice@example.com, zq-other@example.com")

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with pytest.raises(EmailRecipientError) as raised:
            await _resend(engine, ALICE, now=moment)

    assert isinstance(raised.value, ValueError)
    assert (fake.connections, budget.count()) == (0, 0)
    assert [email for _id, email, _consumed, revoked in _states(await _rows(engine, alice.id)) if not revoked] == [None]
    assert await _awaits(engine, alice.id) is True
    print_success("EmailRecipientError, nothing spent")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("earlier", "rival_age"),
    [
        pytest.param((), timedelta(seconds=1), id="a-link-emailed-a-second-ago-meanwhile"),
        pytest.param(((50, "revoked"), (30, "live")), timedelta(minutes=10), id="the-fourth-link-of-the-hour-meanwhile"),
    ],
)
async def test_a_link_emailed_meanwhile_rolls_resend_back(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, earlier: tuple[tuple[int, str], ...], rival_age: timedelta) -> None:
    """EMV-041 — contract 7: the account passes the first count; between that count and its new link, another request emails it a link — committed by another session inside ``token_service.revoke_tokens``, just before the real one —: a link a second old, or the fourth link of the hour. Counted again inside the write transaction, its own link included, the account has more than one in five minutes or more than three in the hour: ``EmailRateLimitedError`` (300 s), everything rolled back — no token of its own, the rival link and the account's other tokens live again —; nothing sent or spent."""
    print_section(f"EMV-041: a rival link {rival_age} old")
    moment = utcnow()
    alice = await _add_user(engine, ALICE, active=False)
    if not earlier:
        await _issue(engine, VERIFICATION, user_id=alice.id, now=moment - timedelta(minutes=20))
    for minutes, how in earlier:
        await _emailed(engine, alice, created=moment - timedelta(minutes=minutes), how=how)
    before = _states(await _rows(engine, alice.id))
    rivals: list[IssuedToken] = []
    revoke = token_service.revoke_tokens

    async def revoke_after_a_rival(session: AsyncSession, **arguments: object) -> int:
        if not rivals:
            async with AsyncSession(engine, expire_on_commit=False) as other:
                rivals.append(await token_service.issue_token(other, VERIFICATION, user_id=alice.id, email=alice.email, now=moment - rival_age))
                await other.commit()
        return await revoke(session, **arguments)

    monkeypatch.setattr(token_service, "revoke_tokens", revoke_after_a_rival)
    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with pytest.raises(EmailRateLimitedError) as limited:
            await _resend(engine, ALICE, now=moment)

    assert limited.value.retry_after == 300.0
    assert len(rivals) == 1, "barrier: the resend went past its first count"
    assert (fake.connections, budget.count()) == (0, 0)
    assert _states(await _rows(engine, alice.id)) == [*before, (rivals[0].record.id, alice.email, False, False)]
    assert await _status(engine, rivals[0].token) == TokenStatus.VALID
    print_success("rolled back: no link of its own, the rival live, nothing sent")


# =============================================================================
# 8. THE LOGS
# =============================================================================


@pytest.mark.asyncio
async def test_no_log_event_holds_a_token_a_password_an_identifier_or_an_address(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine) -> None:
    """EMV-042 — contract 8: through a registration email, refused requests — a wrong password, an unknown account, a request within five minutes —, a «resend» by email address, a dead link and the verifying click: the flow logs (the barrier), and no event holds a token, a password, an identifier, the account's address or the client's address."""
    print_section("EMV-042: the logs")
    moment = utcnow()
    alice, hold = await _waiting(engine, ALICE, created=moment)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with capture_logs() as events:
            await verification.registration_email_work(alice.id, engine=engine, now=moment)
            for identifier, password in ((ALICE, WRONG_PASSWORD), (NOBODY, ACCOUNT_PASSWORD)):
                with pytest.raises(verification.VerificationCredentialsError):
                    await _resend(engine, identifier, password, now=moment)
            with pytest.raises(EmailRateLimitedError):
                await _resend(engine, ALICE, now=moment + timedelta(minutes=1))
            assert await _resend(engine, alice.email, now=moment + timedelta(minutes=6)) == "en"
            first, second = (_token_in(_text(received)) for received in fake.messages)
            with pytest.raises(verification.EmailVerificationLinkInvalidError):
                await _confirm(engine, first, now=moment + timedelta(minutes=7))
            await _confirm(engine, second, now=moment + timedelta(minutes=7))

    assert len(_named(events, "Verification link emailed")) == 2 and len(_named(events, "Email verified")) == 1, f"barrier: the flow logged: {events}"
    secrets = (hold.token, first, second, ACCOUNT_PASSWORD, WRONG_PASSWORD, alice.email, ALICE, NOBODY, ADDRESS)
    assert _holding(events, *secrets) == [], f"a log event holds a token, a password, an identifier or an address: {_holding(events, *secrets)}"
    print_success(f"{len(events)} events, none holding a secret")


# =============================================================================
# 9. AFTER THE SECURITY REVIEW OF E5b
# =============================================================================


async def _mailbox_accounts(engine: AsyncEngine, created: datetime) -> list[tuple[User, IssuedToken]]:
    """Four waiting accounts, each with its hold issued at ``created``, whose addresses are MAILBOX written four ways."""
    return [await _waiting(engine, f"zq_vic_{index}", created=created, email=written) for index, written in enumerate(MAILBOX_VARIANTS)]


async def _issue_and_send_directly(engine: AsyncEngine, user: User, moment: datetime, **arguments: bool) -> str:
    """``_issue_and_send`` in a session of its own, past the checks of «resend»: what a request that passed them meets."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await verification._issue_and_send(session, user, moment, **arguments)


@pytest.mark.asyncio
async def test_a_mailbox_gets_three_registration_emails_an_hour_whatever_the_account(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, clock: FakeClock, mailbox_limit: SlidingWindowLimiter) -> None:
    """EMV-043 — contracts 5 and 7: four accounts registered with one mailbox written four ways (``zq-vÏç@example.com``, ``zq-vïç@…``, ``zq-vÏÇ@…``, ``zq-vïÇ@…``: the case of ``ï`` and ``ç`` alone, since P18 makes an address unique regardless of A–Z case), each waiting with its hold. The registration emails of the first three go out, a minute apart; the fourth's, a minute later, does not: «Verification email: not sent», a warning with ``EmailRateLimitedError`` and ``EMAIL_RATE_LIMITED``, nothing raised. That account still waits with its hold as it was — live, not revoked, no new token —; no fourth message, no fourth unit of the budget; the mailbox counted three times."""
    print_section("EMV-043: three registration emails per mailbox")
    assert {written.casefold() for written in MAILBOX_VARIANTS} == {MAILBOX}, "precondition: four spellings of one mailbox"
    assert len({user_service.email_fold(written) for written in MAILBOX_VARIANTS}) == len(MAILBOX_VARIANTS), "precondition: four accounts on one mailbox: one casefold key, four addresses for the A–Z unique index (P18)"
    moment = utcnow()
    accounts = await _mailbox_accounts(engine, moment - timedelta(minutes=5))
    last, last_hold = accounts[-1]
    before = _states(await _rows(engine, last.id))

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with capture_logs() as events:
            for index, (user, _hold) in enumerate(accounts):
                clock.now = START + 60 * index
                await verification.registration_email_work(user.id, engine=engine, now=moment + timedelta(minutes=index))

    assert [message.rcpt_tos for message in fake.messages] == [[written] for written in MAILBOX_VARIANTS[:3]]
    refused = [(event["log_level"], event.get("reason"), event.get("code")) for event in _named(events, "Verification email: not sent")]
    assert refused == [("warning", "EmailRateLimitedError", "EMAIL_RATE_LIMITED")], refused
    assert _states(await _rows(engine, last.id)) == before and await _awaits(engine, last.id) is True
    assert await _status(engine, last_hold.token) == TokenStatus.VALID
    assert (budget.count(), mailbox_limit.count(MAILBOX)) == (3, 3)
    print_success("three emails, the fourth not sent; that account waits with its hold")


@pytest.mark.asyncio
async def test_an_email_that_did_not_go_does_not_count_for_its_mailbox(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, clock: FakeClock, mailbox_limit: SlidingWindowLimiter) -> None:
    """EMV-044 — contract 7: Vic waits; three «resend» in a row meet an SMTP server that refuses her address — ``EmailDeliveryError`` each time, her mailbox counted for none —; the fourth, a minute later, with a server that takes it, goes: one message, the mailbox counted once. A refused email is not a flood."""
    print_section("EMV-044: a failed email does not count")
    moment = utcnow()
    vic, _hold = await _waiting(engine, "zq_vic", created=moment - timedelta(minutes=1), email=MAILBOX_VARIANTS[0])

    with FakeSmtpServer(refuse_recipients={vic.email}) as refusing:
        _ready(monkeypatch, refusing)
        for attempt in range(3):
            with pytest.raises(EmailDeliveryError):
                await _resend(engine, "zq_vic", now=moment + timedelta(seconds=attempt))
    counted_after_the_refusals = mailbox_limit.count(MAILBOX)
    clock.now = START + 60
    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        assert await _resend(engine, "zq_vic", now=moment + timedelta(minutes=1)) == "en"

    assert counted_after_the_refusals == 0
    assert [message.rcpt_tos for message in fake.messages] == [[vic.email]]
    assert mailbox_limit.count(MAILBOX) == 1
    print_success("three refusals counted nothing; the fourth went")


@pytest.mark.asyncio
async def test_a_place_taken_meanwhile_is_counted_inside_the_write_transaction(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, mailbox_limit: SlidingWindowLimiter) -> None:
    """EMV-045 — contract 7: ``LIBREFOLIO_MAX_USERS=1``, reached by the administrator; Alice's link expired, so she holds no place. ``_issue_and_send(…, needs_place=True)`` is called directly, as by a «resend» that passed the first count before another request took the last place: the user limit, counted again inside the write transaction with her new link, refuses — ``VerificationUserLimitError`` (``USER_LIMIT_REACHED``), everything rolled back: her hold as it was (not revoked), no new token, nothing sent, spent or counted for her mailbox."""
    print_section("EMV-045: the last place taken meanwhile")
    moment = utcnow()
    await _add_user(engine, ADMIN)
    alice, hold = await _waiting(engine, ALICE, created=moment - TTL - timedelta(hours=1))
    monkeypatch.setenv(MAX_USERS_VARIABLE, "1")
    before = _states(await _rows(engine, alice.id))

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with pytest.raises(verification.VerificationUserLimitError) as refused:
            await _issue_and_send_directly(engine, alice, moment, needs_place=True)

    assert refused.value.code == "USER_LIMIT_REACHED"
    assert _states(await _rows(engine, alice.id)) == before == [(hold.record.id, None, False, False)]
    assert (fake.connections, budget.count(), mailbox_limit.count(alice.email.casefold())) == (0, 0, 0)
    print_success("USER_LIMIT_REACHED inside the transaction; the hold as it was")


@pytest.mark.asyncio
async def test_a_live_link_still_holds_its_place_on_a_full_instance(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, mailbox_limit: SlidingWindowLimiter) -> None:
    """EMV-046 — contract 7, the control of EMV-045: ``LIBREFOLIO_MAX_USERS=2``, reached by the administrator and Alice, whose live hold holds her place. ``_issue_and_send(…, needs_place=False)`` goes on the full instance: her hold revoked, one emailed link in its place, one message, her mailbox counted once."""
    print_section("EMV-046: a live link keeps its place")
    moment = utcnow()
    await _add_user(engine, ADMIN)
    alice, hold = await _waiting(engine, ALICE, created=moment - timedelta(hours=1))
    monkeypatch.setenv(MAX_USERS_VARIABLE, "2")

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        assert await _issue_and_send_directly(engine, alice, moment, needs_place=False) == "en"

    states = _states(await _rows(engine, alice.id))
    assert states[0] == (hold.record.id, None, False, True) and [state[1:] for state in states[1:]] == [(alice.email, False, False)], states
    assert [message.rcpt_tos for message in fake.messages] == [[alice.email]]
    assert mailbox_limit.count(alice.email.casefold()) == 1
    print_success("sent on the full instance; the hold replaced")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case", "error", "active"),
    [
        pytest.param("deactivated", verification.VerificationAccountDisabledError, False, id="an-administrator-ended-the-wait-the-links-revoked"),
        pytest.param("clicked", verification.EmailVerificationNotNeededError, True, id="the-link-was-clicked-the-account-active"),
        pytest.param("activated", verification.EmailVerificationNotNeededError, True, id="an-administrator-activated-it-the-links-revoked"),
    ],
)
async def test_an_account_that_stopped_waiting_meanwhile_gets_no_new_link(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, mailbox_limit: SlidingWindowLimiter, case: str, error: type[EmailError], active: bool) -> None:
    """EMV-047 — contract 7: Alice was loaded while she waited, as a «resend» that passed its checks loads her; meanwhile she stopped waiting — an administrator ended the wait (her links revoked, still inactive), her link was clicked (active, the link consumed, the hold revoked) or an administrator activated her (active, her links revoked). ``_issue_and_send`` runs on what it was given: its first write, revoking her unspent links, revokes none, so it stops — rolled back, ``error`` (``ACCOUNT_DISABLED`` inactive, ``EMAIL_VERIFICATION_NOT_NEEDED`` active) —: no new link that would make her wait again, her tokens and her state as they were, nothing sent, spent or counted for her mailbox."""
    print_section(f"EMV-047: {case}")
    moment = utcnow()
    alice, hold = await _waiting(engine, ALICE, created=moment - timedelta(minutes=10))
    if case == "clicked":
        link = await _emailed(engine, alice, created=moment - timedelta(minutes=6))
        await _confirm(engine, link.token, now=moment - timedelta(minutes=1))
    else:
        await _spend(engine, hold, "revoked")
        if case == "activated":
            async with AsyncSession(engine) as session:
                await session.execute(update(User).where(User.id == alice.id).values(is_active=True))
                await session.commit()
    before = _states(await _rows(engine, alice.id))

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with pytest.raises(error):
            await _issue_and_send_directly(engine, alice, moment)

    assert _states(await _rows(engine, alice.id)) == before, "no new link, nothing revoked"
    assert (await _account(engine, alice.id)).is_active is active
    assert (fake.connections, budget.count(), mailbox_limit.count(alice.email.casefold())) == (0, 0, 0)
    print_success(f"{error.__name__}, no new link")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("identifier", "password"),
    [
        pytest.param(ALICE, WRONG_PASSWORD, id="a-wrong-password"),
        pytest.param(NOBODY, ACCOUNT_PASSWORD, id="an-unknown-account"),
    ],
)
async def test_wrong_credentials_are_a_warning_without_the_identifier(engine: AsyncEngine, identifier: str, password: str) -> None:
    """EMV-048 — contract 8: «resend» with wrong credentials — a wrong password for Alice, or a name no account has — logs one warning, «Verification resend refused: wrong credentials», as the login logs its failures; no event holds the identifier, either password, Alice's address or the client's."""
    print_section(f"EMV-048: wrong credentials, {identifier}")
    moment = utcnow()
    alice, _hold = await _waiting(engine, ALICE, created=moment)

    with capture_logs() as events:
        with pytest.raises(verification.VerificationCredentialsError):
            await _resend(engine, identifier, password, now=moment)

    refused = [(event["event"], event["log_level"]) for event in _named(events, "Verification resend refused")]
    assert refused == [("Verification resend refused: wrong credentials", "warning")], f"{events}"
    secrets = (identifier, ALICE, NOBODY, alice.email, ACCOUNT_PASSWORD, WRONG_PASSWORD, ADDRESS)
    assert _holding(events, *secrets) == [], f"a log event holds an identifier, a password or an address: {_holding(events, *secrets)}"
    print_success("one warning, nothing of the credentials")


# =============================================================================
# 10. ALIASES OF ONE MAILBOX SHARE ITS BUDGET (E-9 a)
# =============================================================================

#: One Gmail mailbox written four ways, each the address of a waiting account of its own: a ``+tag``, the dots of the
#: local part and ``googlemail.com`` all deliver to it. ``delivery.mailbox_budget_key`` folds the four into
#: GMAIL_ALIAS_KEY; ``strip().casefold()`` keeps them apart, a budget each.
GMAIL_ALIASES = ("zq.vic+1@gmail.com", "zqvic+2@googlemail.com", "z.q.v.i.c@gmail.com", "zqvic+verify@gmail.com")
GMAIL_ALIAS_KEY = "zqvic@gmail.com"
#: One mailbox outside Gmail written four ways: a ``+tag`` is cut on every domain, so the four share TAGGED_KEY.
TAGGED_ALIASES = ("zq-v+1@example.com", "zq-v+2@example.com", "zq-v+3@example.com", "zq-v@example.com")
TAGGED_KEY = "zq-v@example.com"


@pytest.mark.asyncio
async def test_aliases_of_one_gmail_mailbox_share_its_verification_emails(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, clock: FakeClock, mailbox_limit: SlidingWindowLimiter) -> None:
    """EMV-049 — contracts 5 and 7 (E-9 a): four accounts registered with aliases of one Gmail mailbox — ``zq.vic+1@gmail.com``, ``zqvic+2@googlemail.com``, ``z.q.v.i.c@gmail.com``, ``zqvic+verify@gmail.com`` —, each waiting with its hold. The registration emails of the first three go out, a minute apart, each to its account's stored address exactly — the key is never a recipient —; the fourth's does not: «Verification email: not sent», a warning with ``EmailRateLimitedError`` and ``EMAIL_RATE_LIMITED``, nothing raised, and that account still waits. The mailbox counted three times, under its folded key."""
    print_section("EMV-049: four Gmail aliases, three verification emails")
    assert len({address.casefold() for address in GMAIL_ALIASES}) == len(GMAIL_ALIASES), "precondition: letter case alone keeps the four apart: only folding the aliases makes them one mailbox"
    moment = utcnow()
    accounts = [await _waiting(engine, f"zq_alias_{index}", created=moment - timedelta(minutes=5), email=address) for index, address in enumerate(GMAIL_ALIASES)]
    last = accounts[-1][0]

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with capture_logs() as events:
            for index, (user, _hold) in enumerate(accounts):
                clock.now = START + 60 * index
                await verification.registration_email_work(user.id, engine=engine, now=moment + timedelta(minutes=index))

    assert [message.rcpt_tos for message in fake.messages] == [[address] for address in GMAIL_ALIASES[:3]], "the 4th alias of one mailbox got its own budget: three verification emails an hour per mailbox, however its address is written"
    refused = [(event["log_level"], event.get("reason"), event.get("code"), event.get("user_id")) for event in _named(events, "Verification email: not sent")]
    assert refused == [("warning", "EmailRateLimitedError", "EMAIL_RATE_LIMITED", last.id)], refused
    assert await _awaits(engine, last.id) is True
    assert (budget.count(), mailbox_limit.count(GMAIL_ALIAS_KEY)) == (3, 3), "three emails, counted under the mailbox's folded key"
    print_success("three verification emails to one mailbox under three aliases; the fourth not sent")


@pytest.mark.asyncio
async def test_plus_tags_outside_gmail_share_the_verification_budget(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, clock: FakeClock, mailbox_limit: SlidingWindowLimiter) -> None:
    """EMV-050 — contract 7 (E-9 a): four waiting accounts at ``zq-v+1@example.com``, ``zq-v+2@example.com``, ``zq-v+3@example.com`` and ``zq-v@example.com`` — one mailbox outside Gmail: a ``+tag`` is cut on every domain — each ask «resend» once, a minute apart. The first three get their link, each at its account's stored address exactly, tag included; the fourth's «resend» is ``EmailRateLimitedError``: the mailbox had its three verification emails of the hour. Counted three times, under ``zq-v@example.com``."""
    print_section("EMV-050: +tags outside Gmail, one budget")
    moment = utcnow()
    accounts = [await _waiting(engine, f"zq_tagged_{index}", created=moment - timedelta(minutes=5), email=address) for index, address in enumerate(TAGGED_ALIASES)]

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        for index, (user, _hold) in enumerate(accounts[:3]):
            clock.now = START + 60 * index
            assert await _resend(engine, user.username, now=moment + timedelta(minutes=index)) == "en"
        clock.now = START + 180
        try:
            fourth: object = await _resend(engine, accounts[3][0].username, now=moment + timedelta(minutes=3))
        except EmailRateLimitedError as refused:
            fourth = refused

    assert isinstance(fourth, EmailRateLimitedError), f"the 4th alias of one mailbox got its own budget: «resend» answered {fourth!r} and sent {[message.rcpt_tos for message in fake.messages]}"
    assert [message.rcpt_tos for message in fake.messages] == [[address] for address in TAGGED_ALIASES[:3]], "each link at its account's stored address, tag included"
    assert mailbox_limit.count(TAGGED_KEY) == 3, "three emails, counted under the mailbox's folded key"
    print_success("three links to one mailbox under three addresses; the fourth refused")
