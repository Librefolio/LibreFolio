"""``backend.app.services.email.flows``: the language of an account's emails, the test email, the links an administrator emails and the forgotten password (plan phase01Email §3.3, §3.4, decisions D-E1, D-E9, 45, lots E2a and E3).

``account_language`` decides the language every email of an account is written in; ``send_test_email`` is the email an
administrator sends to themselves from the «Email» tab (``POST /email/test``, tested over HTTP in
``test_api/test_email_api.py``); ``send_link_email`` emails a link an administrator has just created
(``POST /email/links``); ``admit_forgotten_password`` and ``forgotten_password_work`` are the two halves of «forgot
password» (``POST /email/password-reset``). The flows decide content, recipient and language only: ``delivery.send_email``
checks the configuration and the hourly budget, sends and logs (``test_email_delivery.py``), and every link comes from
``links.email_link`` (``test_email_links.py``). The contract pinned here:

1. Both are coroutine functions: ``account_language(session, user_id)`` and ``send_test_email(session, user, *,
   instance)``, ``instance`` keyword-only.
2. ``account_language``: the account's own ``user_settings.language`` when it names one of the four, reduced by
   ``supported_email_language`` — ``it``, ``IT``, ``it-IT`` and ``it_IT`` are ``it`` —, whatever the instance's
   ``default_language`` says: an explicit ``en`` included.
3. An own language that names none of the four counts as unset, like an empty one (decision of lot E2a): without a
   ``user_settings`` row, or with one saying ``de``, ``de-DE`` or nothing, the instance's ``default_language`` (``fr`` →
   ``fr``); another account's row counts for nothing.
4. With neither usable — and a ``default_language`` that is not one of the four languages, empty, or a row that is
   missing — English. ``account_language`` reads the language column alone: a row the read model ``UserSettingsRead``
   refuses (a theme outside light/dark/auto, written as a row) still gives its language. It never creates nor changes a
   ``user_settings`` row: reading a language changes nothing.
5. ``send_test_email`` sends one message through ``send_email``: to the account's own address, from the configured
   sender; its subject and its text are those ``build_test_message`` writes for the account's language, the text naming
   ``instance`` and the user name. It returns that language and spends one unit of the hourly budget.
6. Email off, or set but unusable: ``EmailUnavailableError`` with ``EMAIL_NOT_CONFIGURED`` or the problem of the
   configuration; no connection is opened, nothing is sent, nothing is spent.
7. The configuration — and with it the file of ``LIBREFOLIO_SMTP_PASSWORD_FILE`` — is read off the event loop
   (``send_email`` reads it through ``asyncio.to_thread``), and the password that file holds is the one the server sees.
8. ``messages.supported_email_language``: the email language a tag names — ``it``, ``IT``, ``it-IT``, ``it_IT`` → ``it``
   — or ``None`` when it names none of the four: missing, empty, blank, ``de``, ``de-DE``, ``pt_BR``; ``email_language``
   is that language, or English. (It belongs with ``email_language`` in ``test_email_messages.py``, contract 1: it is
   here only until that file, committed with lot E1, is reopened.)
9. ``send_test_email`` to an account whose address is not one address: ``EmailRecipientError``, a ``ValueError`` — the one
   error ``POST /email/test`` turns into its 422 —; no connection is opened, nothing is spent.
10. ``send_link_email`` refuses in this order, before anything is sent or spent: email not usable
    (``EmailUnavailableError``), links not ready (``EmailLinksUnavailableError`` with ``PUBLIC_URL_MISSING`` or
    ``PUBLIC_URL_INVALID`` — an http(s) address no link can start from, with a space inside or a query, is invalid
    too, and refused before the token is looked at), a token that is not a live link of that purpose
    (``EmailLinkInvalidError`` with its status: ``expired``, ``consumed``, ``revoked``, ``unknown`` — a token of the
    other purpose is ``unknown``), then the recipient. An invitation goes to ``to``, else to the address written in it —
    neither is ``EmailRecipientRequiredError`` —, in the language asked for, else the instance's; a reset link goes only
    to the address of its account, in the account's language: any ``to``, its own address included, is
    ``EmailRecipientNotAllowedError``. The email is exactly what the builder writes for that language with the
    ``LIBREFOLIO_PUBLIC_URL`` link of the token, the host of that address as the instance, the administrator as the
    inviter and the administrator's role sentence when the invitation grants it; one unit spent. The token is in no
    log event.
11. ``admit_forgotten_password`` reads the configuration first — email, then links —, counting nothing when it refuses;
    then 5 requests per 15 minutes per client address and 3 per hour per identifier (stripped, case-insensitive), each
    refusal an ``EmailRateLimitedError`` with the seconds until the window frees; then the instance's hourly budget,
    peeked, never spent. Without a client address (a unix socket) the limit per address does not apply — one shared
    count would let a single client block everyone —, while the limit per identifier and the budget still do. The
    shipped limits are 5/900 s, 3/3600 s, and per account one email every 5 minutes and 3 an hour.
12. ``forgotten_password_work`` finds the account as the login does — by username or email, spaces around ignored —,
    active only; per account at most one reset link every 5 minutes and 3 an hour, counted on every password-reset row
    whatever made it or became of it. It then reads the configuration again — the instance not blocked, email usable,
    links ready, a unit of the hourly budget free —, and only then makes the new reset link: when one of them is gone,
    nothing is made and the account's earlier live links stay live. Making it revokes the account's earlier live reset
    links; the new one is emailed, valid, in the account's language, built from ``LIBREFOLIO_PUBLIC_URL``, and when
    anything stops the email after the link was made — the server refusing, an error while the email is built or while
    the account's language is read — the new link is revoked: no live link reaches nobody. Unknown, inactive, past its
    limits, the configuration gone, the email refused, an unexpected error: nothing is sent and nothing is raised.
    Neither the identifier nor the token is in any log event.
13. A blocked instance (``LIBREFOLIO_BLOCKED`` blocking, or unreadable) sends nothing through any flow, and every flow
    asks it first: ``send_test_email``, ``send_link_email`` and ``admit_forgotten_password`` raise
    ``EmailUnavailableError`` with ``INSTANCE_BLOCKED`` before the configuration, the links, the token or a limiter is
    looked at — the links still live, nothing counted, nothing spent —; ``forgotten_password_work`` ends in silence
    without making a reset row or revoking any.

Pure: every database is a private SQLite file under ``tmp_path`` built with ``create_all`` and the default global
settings (NullPool, disposed at teardown), users written as rows, tokens issued by A's token service with the ``now``
the case needs; no server of the lane, no network beyond 127.0.0.1. An autouse fixture removes every inherited
``LIBREFOLIO_SMTP_*``, ``LIBREFOLIO_PUBLIC_URL`` and ``LIBREFOLIO_BLOCKED`` (C-96 removes them from the lanes; a
developer's shell may still carry them) and each test sets its own with ``monkeypatch``; others replace
``delivery.INSTANCE_BUDGET`` and the two «forgot password» limiters (``flows.FORGOT_BY_ADDRESS``,
``flows.FORGOT_BY_IDENTIFIER``, with the shipped limits) with private limiters on a fake clock;
``smtp.SMTP_TIMEOUT_SECONDS`` is 5 s, a bound for a defect that hangs, never a wait. Every SMTP conversation is with
``FakeSmtpServer`` on 127.0.0.1, on a port the OS picks. Nothing is timed.
"""

from __future__ import annotations

import asyncio
import inspect
import os
import re
import threading
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs

import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import AccountToken, AccountTokenPurpose, GlobalSetting, User, UserSettings
from backend.app.schemas.settings import SETTINGS_REGISTRY
from backend.app.services.accounts import token_service
from backend.app.services.accounts.settings_service import get_user_settings, initialize_global_settings
from backend.app.services.accounts.token_service import DEFAULT_TTL, IssuedToken, TokenInspection, TokenStatus
from backend.app.services.email import delivery, flows, smtp
from backend.app.services.email.delivery import EmailError, EmailRateLimitedError, EmailUnavailableError
from backend.app.services.email.flows import account_language, send_test_email
from backend.app.services.email.links import EmailLinksUnavailableError, email_link
from backend.app.services.email.messages import EmailRecipientError, build_invite, build_password_reset, build_test_message, email_language, supported_email_language
from backend.app.utils.datetime_utils import utcnow
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.fixtures.email.fake_smtp import FakeSmtpServer
from backend.test_scripts.test_utils import print_section, print_success

SMTP_PREFIX = "LIBREFOLIO_SMTP_"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
#: The hosting provider's block: a blocked instance sends nothing.
BLOCKED_VARIABLE = "LIBREFOLIO_BLOCKED"
#: An http(s) address no link can start from (a space inside): ``PUBLIC_URL_INVALID``.
NO_LINK_FROM_IT = "https://folio.zq-space.example.com/my folio"
#: The public address of the instance, with a port and a path prefix: the links prove both kept.
PUBLIC_URL = "https://folio.zq-public.example.com:8443/app"
#: How the emails name the instance: the host of PUBLIC_URL, with its port.
PUBLIC_HOST = "folio.zq-public.example.com:8443"
DEFAULT_LANGUAGE_KEY = SETTINGS_REGISTRY.global_.DEFAULT_LANGUAGE.key

SENDER_HEADER = "LibreFolio <noreply@example.com>"
SENDER = ("LibreFolio", "noreply@example.com")
SMTP_USER_NAME = "zq-mailer"
#: Recognisable, and only ever in a password file here: the server must see exactly this.
SMTP_PASSWORD = "c4nary-SMTP-p4ss-of-the-flows"
#: The instance as the test email names it: distinctive, the host and port a browser would show.
INSTANCE = "zq-folio.example.com:8443"
#: What the users written here hold for a hash: nobody signs in, nothing checks it.
MARKER_HASH = "marker-hash-not-bcrypt"
ALICE = "zq_alice"
BOB = "zq_bob"
ADMIN = "zq_admin"
#: Addresses without an account: where an invitation goes.
GUEST = "zq-guest@example.com"
OTHER_GUEST = "zq-other-guest@example.com"
#: A theme outside light/dark/auto, as an older or newer release could leave in a row: ``UserSettingsRead`` refuses it.
STALE_THEME = "sepia"

INVITE = AccountTokenPurpose.INVITE
PASSWORD_RESET = AccountTokenPurpose.PASSWORD_RESET
#: The purposes ``send_link_email`` takes, as the API names them.
PURPOSES = {"invite": INVITE, "password_reset": PASSWORD_RESET}
#: The page of each kind of link, after PUBLIC_URL.
PAGES = {INVITE: "/invite", PASSWORD_RESET: "/reset-password"}
NEVER_ISSUED = "never-issued-flows-0123456789abcdefghijklmnopq"
DEAD_KINDS = ("expired", "consumed", "revoked", "unknown", "other-purpose")

#: The «forgot password» limiters as the module ships them, read before any fixture replaces them.
SHIPPED_BY_ADDRESS = flows.FORGOT_BY_ADDRESS
SHIPPED_BY_IDENTIFIER = flows.FORGOT_BY_IDENTIFIER
#: The fake clock's start: the first request of every limiter test.
START = 1_000.0

POSITIONAL = inspect.Parameter.POSITIONAL_OR_KEYWORD
KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY


class FakeClock:
    """A clock that moves only when the test sets it: ``clock.now = …``."""

    def __init__(self, start: float = 1_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture(autouse=True)
def _no_inherited_email_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every ``LIBREFOLIO_SMTP_*``, ``LIBREFOLIO_PUBLIC_URL`` and ``LIBREFOLIO_BLOCKED`` the lane inherited is removed: a test sees only the variables it sets itself."""
    for name in list(os.environ):
        if name.startswith(SMTP_PREFIX) or name in (PUBLIC_URL_VARIABLE, BLOCKED_VARIABLE):
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


@dataclass(frozen=True)
class ForgotLimits:
    """The two «forgot password» limiters of a test: per client address, per identifier."""

    by_address: SlidingWindowLimiter
    by_identifier: SlidingWindowLimiter


@pytest.fixture(autouse=True)
def forgot_limits(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> ForgotLimits:
    """Private «forgot password» limiters with the shipped limits, on the fake clock: no test counts in, or is counted by, the process's."""
    limits = ForgotLimits(
        by_address=SlidingWindowLimiter(SHIPPED_BY_ADDRESS.limit, SHIPPED_BY_ADDRESS.window_seconds, clock=clock),
        by_identifier=SlidingWindowLimiter(SHIPPED_BY_IDENTIFIER.limit, SHIPPED_BY_IDENTIFIER.window_seconds, clock=clock),
    )
    monkeypatch.setattr(flows, "FORGOT_BY_ADDRESS", limits.by_address)
    monkeypatch.setattr(flows, "FORGOT_BY_IDENTIFIER", limits.by_identifier)
    return limits


@pytest.fixture(autouse=True)
def _bounded_smtp_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """5 s instead of 20: a defect that hangs fails sooner. No test waits for it."""
    monkeypatch.setattr(smtp, "SMTP_TIMEOUT_SECONDS", 5.0)


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file under tmp_path with the whole ORM schema and the default global settings (``default_language`` ``en``); disposed at teardown."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'flows.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            await initialize_global_settings(session)
        yield engine
    finally:
        await engine.dispose()


async def _add_user(engine: AsyncEngine, username: str, *, email: str | None = None, active: bool = True) -> User:
    """An account written as a row, ``<username>@example.com`` unless ``email`` says otherwise, active unless ``active`` is false, without a ``user_settings`` row; returned detached, its columns loaded."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=email or f"{username}@example.com", hashed_password=MARKER_HASH, is_active=active)
        session.add(user)
        await session.commit()
    return user


async def _set_account_language(engine: AsyncEngine, user_id: int, language: str, *, theme: str = "light") -> None:
    """The account's ``user_settings`` row, its language ``language`` and its theme ``theme`` as stored — written as a row: a table model does not validate —, the other columns at their defaults."""
    async with AsyncSession(engine) as session:
        session.add(UserSettings(user_id=user_id, language=language, theme=theme))
        await session.commit()


async def _set_default_language(engine: AsyncEngine, value: str | None) -> None:
    """The instance's ``default_language`` row says ``value`` — written as a row, the API's choices not applied —; ``None`` deletes the row."""
    async with AsyncSession(engine) as session:
        if value is None:
            await session.execute(delete(GlobalSetting).where(GlobalSetting.key == DEFAULT_LANGUAGE_KEY))
        else:
            result = await session.execute(update(GlobalSetting).where(GlobalSetting.key == DEFAULT_LANGUAGE_KEY).values(value=value))
            assert result.rowcount == 1, "setup: initialize_global_settings did not seed the default_language row"
        await session.commit()


async def _settings_rows(engine: AsyncEngine) -> list[tuple[int, str]]:
    """Every ``user_settings`` row of the database, as ``(user_id, language)``, read fresh."""
    async with AsyncSession(engine) as session:
        rows = (await session.execute(select(UserSettings.user_id, UserSettings.language).order_by(UserSettings.user_id))).all()
    return [tuple(row) for row in rows]


async def _settings_row(engine: AsyncEngine, user_id: int) -> tuple[str, str] | None:
    """``(language, theme)`` of the account's ``user_settings`` row, read fresh; ``None`` without a row."""
    async with AsyncSession(engine) as session:
        row = (await session.execute(select(UserSettings.language, UserSettings.theme).where(UserSettings.user_id == user_id))).one_or_none()
    return None if row is None else tuple(row)


async def _refused_by_the_read_model(engine: AsyncEngine, user_id: int) -> str:
    """The precondition, verified: ``get_user_settings``, the read model the rest of the app reads the row through, refuses the account's row; what it said."""
    async with AsyncSession(engine) as session:
        with pytest.raises(ValidationError) as refused:
            await get_user_settings(user_id, session)
    return str(refused.value)


async def _language_of(engine: AsyncEngine, user_id: int) -> str:
    async with AsyncSession(engine) as session:
        return await account_language(session, user_id)


def _configure(monkeypatch: pytest.MonkeyPatch, variables: dict[str, str | None]) -> None:
    """Set ``LIBREFOLIO_SMTP_<NAME>`` for each ``name: value``, ``None`` leaving it unset."""
    for name, value in variables.items():
        variable = SMTP_PREFIX + name.upper()
        if value is None:
            monkeypatch.delenv(variable, raising=False)
        else:
            monkeypatch.setenv(variable, value)


def _point_at(monkeypatch: pytest.MonkeyPatch, fake: FakeSmtpServer, **extra: str | None) -> None:
    """Email configured to go through ``fake``: its address and port, no TLS on the loopback, this module's sender; ``extra`` on top."""
    _configure(monkeypatch, {"host": fake.host, "port": str(fake.port), "tls": "none", "from": SENDER_HEADER, **extra})


def _mailboxes(header: object) -> list[tuple[str, str]]:
    return [(address.display_name, address.addr_spec) for address in header.addresses]


def _lines(text: str) -> str:
    """``text`` without the line-ending differences of a MIME round trip."""
    return text.replace("\r\n", "\n").rstrip("\n")


def _loop_running() -> bool:
    """Whether the calling thread runs an event loop right now."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


def _ready(monkeypatch: pytest.MonkeyPatch, fake: FakeSmtpServer, **extra: str | None) -> None:
    """Email through ``fake`` (``_point_at``, ``extra`` on top) and links ready on PUBLIC_URL."""
    _point_at(monkeypatch, fake, **extra)
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)


def _usable_without_a_server(monkeypatch: pytest.MonkeyPatch, **extra: str | None) -> None:
    """A usable SMTP configuration towards a host nothing ever connects to, for the steps that read the configuration and never send; links ready."""
    _configure(monkeypatch, {"host": "smtp.zq-host.example.com", "from": SENDER_HEADER, **extra})
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)


async def _issue(engine: AsyncEngine, purpose: AccountTokenPurpose, **arguments: object) -> IssuedToken:
    """A token issued by A's token service, committed: what a route of A has just handed to the administrator."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, purpose, **arguments)
        await session.commit()
    return issued


def _owned(purpose: AccountTokenPurpose, owner_id: int) -> dict[str, object]:
    """What a token of ``purpose`` needs: an invitation carries the guest's address, a reset link its account."""
    return {"email": GUEST} if purpose == INVITE else {"user_id": owner_id}


async def _dead_token(engine: AsyncEngine, purpose: AccountTokenPurpose, kind: str, owner_id: int) -> str:
    """A token that is not a live link of ``purpose``: never issued, expired, consumed, revoked, or a live token of the other purpose."""
    if kind == "unknown":
        return NEVER_ISSUED
    if kind == "other-purpose":
        other = PASSWORD_RESET if purpose == INVITE else INVITE
        return (await _issue(engine, other, **_owned(other, owner_id))).token
    if kind == "expired":
        return (await _issue(engine, purpose, now=utcnow() - DEFAULT_TTL[purpose] - timedelta(days=1), **_owned(purpose, owner_id))).token
    issued = await _issue(engine, purpose, **_owned(purpose, owner_id))
    async with AsyncSession(engine) as session:
        if kind == "consumed":
            assert await token_service.consume_token(session, issued.token, purpose) is not None, "setup: consumed"
        else:
            assert await token_service.revoke_tokens(session, token_id=issued.record.id) == 1, "setup: revoked"
        await session.commit()
    return issued.token


async def _inspect(engine: AsyncEngine, token: str, purpose: AccountTokenPurpose) -> TokenInspection:
    """What A's token service says of ``token`` now, read fresh."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await token_service.inspect_token(session, token, purpose)


async def _reset_rows(engine: AsyncEngine, user_id: int) -> list[AccountToken]:
    """Every password-reset row of the account, oldest first, read fresh."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        statement = select(AccountToken).where(AccountToken.purpose == PASSWORD_RESET, AccountToken.user_id == user_id).order_by(AccountToken.id)
        return list((await session.execute(statement)).scalars().all())


def _text(received: object) -> str:
    """The plain-text part of a received message."""
    return received.message.get_body(preferencelist=("plain",)).get_content()


def _html(received: object) -> str:
    """The HTML part of a received message."""
    return received.message.get_body(preferencelist=("html",)).get_content()


def _token_in(text: str, purpose: AccountTokenPurpose) -> str:
    """The token of the PUBLIC_URL link of ``purpose`` an email text carries; fails when it carries none."""
    match = re.search(re.escape(f"{PUBLIC_URL}{PAGES[purpose]}#") + r"(\S+)", text)
    assert match, f"no {PUBLIC_URL}{PAGES[purpose]} link in the email: {text!r}"
    return parse_qs(match.group(1))["token"][0]


def _assert_is(received: object, expected: object) -> None:
    """The message is exactly the content a builder wrote: subject, text and HTML."""
    assert received.message["Subject"] == expected.subject
    assert _lines(_text(received)) == _lines(expected.text)
    assert _lines(_html(received)) == _lines(expected.html)


# =============================================================================
# 1. THE SIGNATURES
# =============================================================================


def test_the_flows_are_coroutine_functions_with_their_signatures() -> None:
    """EMF-001 — contract 1: ``account_language(session, user_id)`` and ``send_test_email(session, user, *, instance)``, both coroutine functions, ``instance`` keyword-only."""
    print_section("EMF-001: signatures")

    assert inspect.iscoroutinefunction(account_language) and inspect.iscoroutinefunction(send_test_email)
    assert [(parameter.name, parameter.kind) for parameter in inspect.signature(account_language).parameters.values()] == [("session", POSITIONAL), ("user_id", POSITIONAL)]
    assert [(parameter.name, parameter.kind) for parameter in inspect.signature(send_test_email).parameters.values()] == [("session", POSITIONAL), ("user", POSITIONAL), ("instance", KEYWORD_ONLY)]
    print_success("account_language(session, user_id); send_test_email(session, user, *, instance)")


# =============================================================================
# 2-4. account_language
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        pytest.param("it", "it", id="it"),
        pytest.param("it-IT", "it", id="regional-it-IT"),
        pytest.param("it_IT", "it", id="regional-it_IT"),
        pytest.param("IT", "it", id="IT"),
        pytest.param("es", "es", id="es"),
        pytest.param("en", "en", id="explicit-en-over-the-instance"),
        pytest.param("de", "fr", id="unknown-de-is-unset"),
        pytest.param("de-DE", "fr", id="unknown-de-DE-is-unset"),
        pytest.param("", "fr", id="empty-is-unset"),
    ],
)
async def test_the_accounts_own_language_wins_when_it_names_an_email_language(engine: AsyncEngine, stored: str, expected: str) -> None:
    """EMF-002 — contracts 2 and 3: the account's row says ``stored``, the instance's ``default_language`` says ``fr``. A language that names one of the four wins, reduced — ``it-IT``, ``it_IT`` and ``IT`` are ``it``, and an explicit ``en`` is English, not the instance's ``fr`` —; one that names none of them — ``de``, ``de-DE`` — counts as unset, like an empty one: the instance's ``fr``. The row is left as it was."""
    print_section(f"EMF-002: the account says {stored!r}, the instance 'fr'")
    alice = await _add_user(engine, ALICE)
    await _set_account_language(engine, alice.id, stored)
    await _set_default_language(engine, "fr")

    language = await _language_of(engine, alice.id)

    assert language == expected, f"the account says {stored!r}, the instance says 'fr': expected {expected!r}, got {language!r}"
    assert await _settings_rows(engine) == [(alice.id, stored)], "reading the language must leave the account's row as it was"
    print_success(f"{stored!r} → {language!r}")


@pytest.mark.asyncio
@pytest.mark.parametrize("default", ["fr", "es"])
async def test_without_a_row_the_instance_default_language_and_no_row_is_created(engine: AsyncEngine, default: str) -> None:
    """EMF-003 — contracts 3 and 4: Alice has no ``user_settings`` row, Bob has one saying ``it``, the instance's ``default_language`` says ``default``: Alice's language is ``default`` — not Bob's ``it``, not English — and she still has no row afterwards."""
    print_section(f"EMF-003: no row, the instance says {default!r}")
    alice = await _add_user(engine, ALICE)
    bob = await _add_user(engine, BOB)
    await _set_account_language(engine, bob.id, "it")
    await _set_default_language(engine, default)

    language = await _language_of(engine, alice.id)

    assert language == default, f"no row for the account, the instance says {default!r} and another account 'it': got {language!r}"
    assert await _settings_rows(engine) == [(bob.id, "it")], "account_language must never create a user_settings row"
    print_success(f"the instance's {default!r}; no row created")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("own", "default"),
    [
        pytest.param(None, "de", id="no-row-instance-de"),
        pytest.param(None, "", id="no-row-instance-empty"),
        pytest.param(None, None, id="no-row-instance-row-missing"),
        pytest.param("de", "de", id="own-de-instance-de"),
        pytest.param("", None, id="own-empty-instance-row-missing"),
    ],
)
async def test_with_neither_usable_the_language_is_english(engine: AsyncEngine, own: str | None, default: str | None) -> None:
    """EMF-004 — contract 4: the account has no row, or one saying a language the emails do not speak or nothing; the instance's ``default_language`` row says a language the emails do not speak, says nothing, or is missing altogether: English. No row created, the account's row left as it was."""
    print_section(f"EMF-004: the account says {own!r}, the instance {default!r}")
    alice = await _add_user(engine, ALICE)
    if own is not None:
        await _set_account_language(engine, alice.id, own)
    await _set_default_language(engine, default)

    language = await _language_of(engine, alice.id)

    assert language == "en", f"neither the account ({own!r}) nor the instance ({default!r}) gives a usable language: got {language!r}"
    assert await _settings_rows(engine) == ([] if own is None else [(alice.id, own)]), "account_language must never create nor change a user_settings row"
    print_success("English; no row created or changed")


@pytest.mark.asyncio
async def test_a_settings_row_the_read_model_refuses_still_gives_its_language(engine: AsyncEngine) -> None:
    """EMF-009 — contract 4: Alice's row says ``it`` with a theme outside light/dark/auto (``sepia``, written as a row), the instance says ``fr``: ``account_language`` is ``it`` — it reads the language column alone — and the row is left as it was.

    Barrier first: ``get_user_settings``, the read model the rest of the app reads the row through, refuses that row with
    a ``ValidationError`` naming the theme — otherwise this would only be one more row with a valid theme.
    """
    print_section("EMF-009: a row the read model refuses")
    alice = await _add_user(engine, ALICE)
    await _set_account_language(engine, alice.id, "it", theme=STALE_THEME)
    await _set_default_language(engine, "fr")
    refusal = await _refused_by_the_read_model(engine, alice.id)
    assert "theme" in refusal, f"barrier: the read model must refuse the row for its theme: {refusal}"

    language = await _language_of(engine, alice.id)

    assert language == "it", f"the account says 'it' in a row the read model refuses, the instance 'fr': got {language!r}"
    assert await _settings_row(engine, alice.id) == ("it", STALE_THEME), "account_language must leave the row as it was"
    print_success("'it' from a row the read model refuses; the row untouched")


# =============================================================================
# 5-7, 9. send_test_email
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("own", "default", "language"),
    [
        pytest.param("it", "fr", "it", id="own-it-over-default-fr"),
        pytest.param("fr-FR", "es", "fr", id="own-fr-FR-over-default-es"),
        pytest.param("de", "es", "es", id="own-unknown-de-default-es"),
        pytest.param(None, "es", "es", id="no-row-default-es"),
        pytest.param(None, "de", "en", id="neither-english"),
    ],
)
async def test_the_test_email_goes_to_the_accounts_own_address_in_its_language(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, own: str | None, default: str, language: str) -> None:
    """EMF-005 — contracts 3 and 5: one message, to Alice's own address, from the configured sender; its subject, its text and its HTML are ``build_test_message`` in Alice's language (her row when it names one of the four — ``de`` does not —, else the instance's, else English), the text naming the instance and her user name, ``Content-Language`` that language; ``send_test_email`` returns it and one unit of the budget is spent.

    The precondition is verified, not assumed: in every language but English the expected subject differs from the
    English one, so a flow that always wrote English could not pass.
    """
    print_section(f"EMF-005: own {own!r}, instance {default!r} → {language}")
    alice = await _add_user(engine, ALICE)
    if own is not None:
        await _set_account_language(engine, alice.id, own)
    await _set_default_language(engine, default)
    expected = build_test_message(language=language, username=ALICE, instance=INSTANCE)
    english = build_test_message(language="en", username=ALICE, instance=INSTANCE)
    assert language == "en" or expected.subject != english.subject, f"precondition: the {language} subject must differ from the English one"

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake)
        async with AsyncSession(engine) as session:
            returned = await send_test_email(session, alice, instance=INSTANCE)

    assert returned == language
    assert (fake.connections, len(fake.messages)) == (1, 1)
    received = fake.messages[0]
    assert (received.mail_from, received.rcpt_tos) == (SENDER[1], [alice.email])
    message = received.message
    assert _mailboxes(message["From"]) == [SENDER]
    assert _mailboxes(message["To"]) == [("", alice.email)]
    assert message["Subject"] == expected.subject
    assert message["Content-Language"] == language
    text = message.get_body(preferencelist=("plain",)).get_content()
    assert _lines(text) == _lines(expected.text)
    assert _lines(message.get_body(preferencelist=("html",)).get_content()) == _lines(expected.html)
    assert INSTANCE in text and ALICE in text, f"the text must name the instance and the user: {text!r}"
    assert budget.count() == 1
    print_success(f"one message to {alice.email} in {language}: {expected.subject!r}")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        pytest.param({"host": None}, "EMAIL_NOT_CONFIGURED", id="off"),
        pytest.param({"tls": "ssl"}, "SMTP_TLS_INVALID", id="tls-invalid"),
    ],
)
async def test_email_off_or_unusable_raises_and_sends_nothing(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, overrides: dict[str, str | None], code: str) -> None:
    """EMF-006 — contract 6: every variable points at a running fake but the host is unset (off) or the TLS mode cannot be used: ``EmailUnavailableError`` with ``code``; the fake accepted no connection and nothing was spent."""
    print_section(f"EMF-006: {code}")
    alice = await _add_user(engine, ALICE)

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake, **overrides)
        async with AsyncSession(engine) as session:
            with pytest.raises(EmailUnavailableError) as caught:
                await send_test_email(session, alice, instance=INSTANCE)

    assert isinstance(caught.value, EmailError)
    assert caught.value.code == code
    assert (fake.connections, fake.messages, budget.count()) == (0, [], 0)
    print_success(f"{code}: no connection, nothing spent")


@pytest.mark.asyncio
async def test_the_configuration_and_its_password_file_are_read_off_the_event_loop(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, tmp_path: Path) -> None:
    """EMF-007 — contract 7: the password comes from ``LIBREFOLIO_SMTP_PASSWORD_FILE``; every read of it during ``send_test_email`` (``delivery.smtp_password``, wrapped) happens on a thread that is not the loop's and runs no loop; the server saw that password and took the message of that user.

    Barrier first: the reads are recorded at all — otherwise «none on the loop» would hold for a send that never read
    the configuration through ``delivery.smtp_password``.
    """
    print_section("EMF-007: configuration read off the event loop")
    password_file = tmp_path / "zq-smtp-password"
    password_file.write_text(f"{SMTP_PASSWORD}\n", encoding="utf-8")
    loop_thread = threading.get_ident()
    reads: list[tuple[int, bool]] = []
    read_password = delivery.smtp_password

    def recording_password() -> str | None:
        reads.append((threading.get_ident(), _loop_running()))
        return read_password()

    monkeypatch.setattr(delivery, "smtp_password", recording_password)
    alice = await _add_user(engine, ALICE)

    with FakeSmtpServer(credentials=(SMTP_USER_NAME, SMTP_PASSWORD)) as fake:
        _point_at(monkeypatch, fake, user=SMTP_USER_NAME, password_file=str(password_file))
        async with AsyncSession(engine) as session:
            await send_test_email(session, alice, instance=INSTANCE)

    assert reads, "barrier: send_test_email never read the password through delivery.smtp_password"
    on_the_loop = [(thread, running) for thread, running in reads if thread == loop_thread or running]
    assert on_the_loop == [], f"{len(on_the_loop)} of {len(reads)} configuration reads ran on the event loop: the password file must be read through asyncio.to_thread"
    assert fake.auth_attempts == [(SMTP_USER_NAME, SMTP_PASSWORD)]
    assert [message.user for message in fake.messages] == [SMTP_USER_NAME]
    print_success(f"{len(reads)} read(s), none on the loop; the password from the file authenticated")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "address",
    [
        pytest.param("zq-alice-without-a-domain", id="no-at"),
        pytest.param("zq_alice@example.com, zq_bob@example.com", id="two-addresses"),
    ],
)
async def test_an_address_that_is_not_one_address_is_an_email_recipient_error(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, address: str) -> None:
    """EMF-010 — contract 9: email ready towards a running fake; Alice's stored address is not one address (a row no form would write). ``send_test_email`` raises ``EmailRecipientError`` — a ``ValueError``, so that a caller catching ``ValueError`` still catches it, and the exact class ``POST /email/test`` turns into its 422 —; the fake accepted no connection and nothing was spent."""
    print_section(f"EMF-010: the address {address!r}")
    alice = await _add_user(engine, ALICE, email=address)

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake)
        async with AsyncSession(engine) as session:
            with pytest.raises(EmailRecipientError) as caught:
                await send_test_email(session, alice, instance=INSTANCE)

    assert issubclass(EmailRecipientError, ValueError) and isinstance(caught.value, ValueError)
    assert type(caught.value) is EmailRecipientError, f"expected EmailRecipientError itself: {type(caught.value)!r}"
    assert (fake.connections, fake.messages, budget.count()) == (0, [], 0)
    print_success("EmailRecipientError, a ValueError; no connection, nothing spent")


# =============================================================================
# 8. supported_email_language
# =============================================================================


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        pytest.param("en", "en", id="en"),
        pytest.param("it", "it", id="it"),
        pytest.param("fr", "fr", id="fr"),
        pytest.param("es", "es", id="es"),
        pytest.param("IT", "it", id="IT"),
        pytest.param("it_IT", "it", id="it_IT"),
        pytest.param("it-IT", "it", id="it-IT"),
        pytest.param("fr-CA", "fr", id="fr-CA"),
        pytest.param("de", None, id="unknown-de"),
        pytest.param("de-DE", None, id="unknown-de-DE"),
        pytest.param("pt_BR", None, id="unknown-pt_BR"),
        pytest.param("", None, id="empty"),
        pytest.param("   ", None, id="blank"),
        pytest.param(None, None, id="missing"),
    ],
)
def test_supported_email_language_names_one_of_the_four_or_none(language: str | None, expected: str | None) -> None:
    """EMF-008 — contract 8: ``supported_email_language`` is the email language the tag names — the case and the region dropped — or ``None``, never English by default, when it names none of the four; ``email_language`` is that language, or English."""
    print_section(f"EMF-008: supported_email_language({language!r})")

    supported = supported_email_language(language)

    assert (supported, type(supported)) == (expected, type(expected)), f"{language!r}: expected {expected!r}, got {supported!r}"
    assert email_language(language) == (expected or "en")
    print_success(f"→ {supported!r}; email_language → {email_language(language)!r}")


# =============================================================================
# 10. send_link_email
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("email_ready", "public_url", "error", "code"),
    [
        pytest.param(False, None, EmailUnavailableError, "EMAIL_NOT_CONFIGURED", id="email-off-before-links"),
        pytest.param(True, None, EmailLinksUnavailableError, "PUBLIC_URL_MISSING", id="links-missing-before-the-token"),
        pytest.param(True, "ftp://folio.zq-public.example.com", EmailLinksUnavailableError, "PUBLIC_URL_INVALID", id="links-invalid-before-the-token"),
        pytest.param(True, NO_LINK_FROM_IT, EmailLinksUnavailableError, "PUBLIC_URL_INVALID", id="links-with-a-space-before-the-token"),
        pytest.param(True, "https://folio.zq-query.example.com/app?lang=it", EmailLinksUnavailableError, "PUBLIC_URL_INVALID", id="links-with-a-query-before-the-token"),
        pytest.param(True, PUBLIC_URL, flows.EmailLinkInvalidError, "unknown", id="then-the-token"),
    ],
)
async def test_send_link_email_refuses_email_then_links_then_the_token(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, email_ready: bool, public_url: str | None, error: type[EmailError], code: str) -> None:
    """EMF-011 — contract 10: a token never issued, for an invitation without an address — every later step would refuse too —: email off is ``EmailUnavailableError`` whatever the links; email ready and links missing or invalid — not http(s), or an http(s) address no link can start from — is ``EmailLinksUnavailableError`` with the problem, before the token is read; only then the token. Nothing sent, nothing spent."""
    print_section(f"EMF-011: {code}")
    admin = await _add_user(engine, ADMIN)

    with FakeSmtpServer() as fake:
        if email_ready:
            _point_at(monkeypatch, fake)
        if public_url is not None:
            monkeypatch.setenv(PUBLIC_URL_VARIABLE, public_url)
        async with AsyncSession(engine) as session:
            with pytest.raises(EmailError) as raised:
                await flows.send_link_email(session, admin=admin, purpose="invite", token=NEVER_ISSUED)

    assert (type(raised.value), raised.value.code) == (error, code), repr(raised.value)
    assert (fake.connections, budget.count()) == (0, 0)
    print_success(f"{error.__name__}({code}), nothing sent")


@pytest.mark.asyncio
@pytest.mark.parametrize("purpose", list(PURPOSES))
@pytest.mark.parametrize("kind", DEAD_KINDS)
async def test_only_a_live_token_of_that_purpose_is_emailed(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, purpose: str, kind: str) -> None:
    """EMF-012 — contract 10: email and links ready; a token expired, consumed, revoked, never issued, or a live token of the other purpose is ``EmailLinkInvalidError`` with its status — ``unknown`` for the other purpose's —; nothing sent, nothing spent."""
    print_section(f"EMF-012: {purpose}, {kind}")
    admin = await _add_user(engine, ADMIN)
    alice = await _add_user(engine, ALICE)
    token = await _dead_token(engine, PURPOSES[purpose], kind, alice.id)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        async with AsyncSession(engine) as session:
            with pytest.raises(flows.EmailLinkInvalidError) as raised:
                await flows.send_link_email(session, admin=admin, purpose=purpose, token=token)

    assert raised.value.code == ("unknown" if kind == "other-purpose" else kind), repr(raised.value)
    assert (fake.connections, budget.count()) == (0, 0)
    print_success(f"EmailLinkInvalidError({raised.value.code})")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("to", "stored", "recipient"),
    [
        pytest.param(OTHER_GUEST, GUEST, OTHER_GUEST, id="to-over-the-stored-address"),
        pytest.param(None, GUEST, GUEST, id="the-stored-address"),
        pytest.param(OTHER_GUEST, None, OTHER_GUEST, id="to-without-a-stored-address"),
    ],
)
async def test_an_invitation_goes_to_to_else_to_its_stored_address(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, to: str | None, stored: str | None, recipient: str) -> None:
    """EMF-013 — contract 10: an invitation goes to ``to`` when given, else to the address written in it; in the instance's language (``fr``); the email is exactly ``build_invite`` with the PUBLIC_URL link of the token — path prefix and port kept —, PUBLIC_URL's host as the instance and the administrator as the inviter; ``LinkEmailSent(to, language)``; one unit spent."""
    print_section(f"EMF-013: invitation to {recipient}")
    admin = await _add_user(engine, ADMIN)
    await _set_default_language(engine, "fr")
    issued = await _issue(engine, INVITE, email=stored, created_by_user_id=admin.id)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        async with AsyncSession(engine) as session:
            sent = await flows.send_link_email(session, admin=admin, purpose="invite", token=issued.token, to=to)

    assert sent == flows.LinkEmailSent(to=recipient, language="fr")
    assert [message.rcpt_tos for message in fake.messages] == [[recipient]]
    link = f"{PUBLIC_URL}/invite#token={issued.token}"
    assert link in _text(fake.messages[0]), f"the email must carry {link}"
    _assert_is(fake.messages[0], build_invite(language="fr", link=link, ttl=DEFAULT_TTL[INVITE], instance=PUBLIC_HOST, inviter=ADMIN, grants_admin=False))
    assert budget.count() == 1
    print_success(f"to {recipient}, in fr, {link}")


@pytest.mark.asyncio
async def test_an_invitation_without_any_address_is_refused(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter) -> None:
    """EMF-014 — contract 10: no ``to`` and no address written in the invitation: ``EmailRecipientRequiredError`` (``EMAIL_RECIPIENT_REQUIRED``); nothing sent, nothing spent."""
    print_section("EMF-014: an invitation without an address")
    admin = await _add_user(engine, ADMIN)
    issued = await _issue(engine, INVITE, created_by_user_id=admin.id)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        async with AsyncSession(engine) as session:
            with pytest.raises(flows.EmailRecipientRequiredError) as raised:
                await flows.send_link_email(session, admin=admin, purpose="invite", token=issued.token)

    assert raised.value.code == "EMAIL_RECIPIENT_REQUIRED"
    assert (fake.connections, budget.count()) == (0, 0)
    print_success("EMAIL_RECIPIENT_REQUIRED, nothing sent")


@pytest.mark.asyncio
@pytest.mark.parametrize("grants_admin", [False, True], ids=["user-invitation", "admin-invitation"])
async def test_an_invitation_that_grants_the_admin_role_says_so(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, grants_admin: bool) -> None:
    """EMF-015 — contract 10: the email of an invitation is ``build_invite`` with the invitation's ``grants_admin``: the administrator's role sentence exactly when it grants the role. The precondition is verified: the two texts differ."""
    print_section(f"EMF-015: grants_admin={grants_admin}")
    admin = await _add_user(engine, ADMIN)
    issued = await _issue(engine, INVITE, email=GUEST, grants_admin=grants_admin, created_by_user_id=admin.id)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        async with AsyncSession(engine) as session:
            await flows.send_link_email(session, admin=admin, purpose="invite", token=issued.token)

    link = email_link(INVITE, issued.token)
    expected, other = (build_invite(language="en", link=link, ttl=DEFAULT_TTL[INVITE], instance=PUBLIC_HOST, inviter=ADMIN, grants_admin=value) for value in (grants_admin, not grants_admin))
    assert expected.text != other.text, "precondition: the role sentence makes the two invitations differ"
    _assert_is(fake.messages[0], expected)
    print_success(f"the invitation {'with' if grants_admin else 'without'} the role sentence")


@pytest.mark.asyncio
@pytest.mark.parametrize(("asked", "language"), [pytest.param("es", "es", id="asked-es"), pytest.param(None, "fr", id="none-asked-instance-fr"), pytest.param("de", "fr", id="unknown-asked-instance-fr")])
async def test_an_invitation_is_written_in_the_language_asked_else_the_instances(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, asked: str | None, language: str) -> None:
    """EMF-016 — contract 10: the instance says ``fr``; an invitation is in the language asked when it is one of the four, else the instance's. The precondition is verified: the expected subject differs from the English one."""
    print_section(f"EMF-016: asked {asked!r} → {language}")
    admin = await _add_user(engine, ADMIN)
    await _set_default_language(engine, "fr")
    issued = await _issue(engine, INVITE, email=GUEST, created_by_user_id=admin.id)
    expected = build_invite(language=language, link=f"{PUBLIC_URL}/invite#token={issued.token}", ttl=DEFAULT_TTL[INVITE], instance=PUBLIC_HOST, inviter=ADMIN)
    assert expected.subject != build_invite(language="en", link=f"{PUBLIC_URL}/invite#token={issued.token}", ttl=DEFAULT_TTL[INVITE], instance=PUBLIC_HOST).subject, "precondition"

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        async with AsyncSession(engine) as session:
            sent = await flows.send_link_email(session, admin=admin, purpose="invite", token=issued.token, language=asked)

    assert sent.language == language
    _assert_is(fake.messages[0], expected)
    print_success(f"{language}: {expected.subject!r}")


@pytest.mark.asyncio
@pytest.mark.parametrize(("own", "language"), [pytest.param("it", "it", id="own-it-over-instance-fr"), pytest.param(None, "fr", id="no-row-instance-fr")])
async def test_a_reset_link_goes_to_its_account_in_the_accounts_language(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, own: str | None, language: str) -> None:
    """EMF-017 — contract 10: a reset link goes to the address of its account, in the account's language (its own, else the instance's ``fr``); the email is exactly ``build_password_reset`` with the PUBLIC_URL link and PUBLIC_URL's host; ``LinkEmailSent(the account's address, language)``; one unit spent."""
    print_section(f"EMF-017: reset link, {language}")
    admin = await _add_user(engine, ADMIN)
    alice = await _add_user(engine, ALICE)
    if own is not None:
        await _set_account_language(engine, alice.id, own)
    await _set_default_language(engine, "fr")
    issued = await _issue(engine, PASSWORD_RESET, user_id=alice.id, created_by_user_id=admin.id)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        async with AsyncSession(engine) as session:
            sent = await flows.send_link_email(session, admin=admin, purpose="password_reset", token=issued.token)

    assert sent == flows.LinkEmailSent(to=alice.email, language=language)
    assert [message.rcpt_tos for message in fake.messages] == [[alice.email]]
    link = f"{PUBLIC_URL}/reset-password#token={issued.token}"
    _assert_is(fake.messages[0], build_password_reset(language=language, username=ALICE, link=link, ttl=DEFAULT_TTL[PASSWORD_RESET], instance=PUBLIC_HOST))
    assert budget.count() == 1
    print_success(f"to {alice.email}, in {language}")


@pytest.mark.asyncio
@pytest.mark.parametrize("to", ["another-address", "the-accounts-own-address"])
async def test_a_reset_link_never_goes_to_an_address_given_with_it(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, to: str) -> None:
    """EMF-018 — contract 10: a reset link with a ``to`` — another address, or even the account's own — is ``EmailRecipientNotAllowedError`` (``EMAIL_RECIPIENT_NOT_ALLOWED``): the address is never the caller's to choose; nothing sent, nothing spent."""
    print_section(f"EMF-018: reset link with to = {to}")
    admin = await _add_user(engine, ADMIN)
    alice = await _add_user(engine, ALICE)
    issued = await _issue(engine, PASSWORD_RESET, user_id=alice.id, created_by_user_id=admin.id)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        async with AsyncSession(engine) as session:
            with pytest.raises(flows.EmailRecipientNotAllowedError) as raised:
                await flows.send_link_email(session, admin=admin, purpose="password_reset", token=issued.token, to=OTHER_GUEST if to == "another-address" else alice.email)

    assert raised.value.code == "EMAIL_RECIPIENT_NOT_ALLOWED"
    assert (fake.connections, budget.count()) == (0, 0)
    print_success("EMAIL_RECIPIENT_NOT_ALLOWED, nothing sent")


@pytest.mark.asyncio
async def test_the_token_of_an_emailed_link_is_never_logged(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine) -> None:
    """EMF-019 — contract 10: an invitation and a reset link emailed: no log event holds either token.

    Barrier first: both sends are logged (``Link emailed by an administrator``, with the id of their token), so the
    capture hears the flow and the absence of the tokens means something.
    """
    print_section("EMF-019: no token in the logs")
    admin = await _add_user(engine, ADMIN)
    alice = await _add_user(engine, ALICE)
    invitation = await _issue(engine, INVITE, email=GUEST, created_by_user_id=admin.id)
    reset = await _issue(engine, PASSWORD_RESET, user_id=alice.id, created_by_user_id=admin.id)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with capture_logs() as events:
            async with AsyncSession(engine) as session:
                await flows.send_link_email(session, admin=admin, purpose="invite", token=invitation.token)
                await flows.send_link_email(session, admin=admin, purpose="password_reset", token=reset.token)

    emailed = [event.get("token_id") for event in events if event.get("event") == "Link emailed by an administrator"]
    assert emailed == [invitation.record.id, reset.record.id], f"barrier: both sends are logged with their token's id: {events}"
    leaked = [event for event in events if invitation.token in repr(event) or reset.token in repr(event)]
    assert leaked == [], f"a log event holds a token: {leaked}"
    assert len(fake.messages) == 2
    print_success(f"{len(events)} events, no token")


# =============================================================================
# 11. admit_forgotten_password
# =============================================================================

ADDRESS = "198.51.100.7"
OTHER_ADDRESS = "198.51.100.8"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("email_usable", "public_url", "error"),
    [
        pytest.param(False, PUBLIC_URL, EmailUnavailableError, id="email-off"),
        pytest.param(True, None, EmailLinksUnavailableError, id="links-missing"),
        pytest.param(True, "ftp://folio.zq-public.example.com", EmailLinksUnavailableError, id="links-invalid"),
    ],
)
async def test_admission_reads_the_configuration_first_and_counts_nothing(monkeypatch: pytest.MonkeyPatch, forgot_limits: ForgotLimits, email_usable: bool, public_url: str | None, error: type[EmailError]) -> None:
    """EMF-020 — contract 11: email off, or links missing or invalid: the admission refuses with ``error`` before any limiter counts the address or the identifier."""
    print_section(f"EMF-020: {error.__name__}")
    if email_usable:
        _usable_without_a_server(monkeypatch)
    if public_url is not None:
        monkeypatch.setenv(PUBLIC_URL_VARIABLE, public_url)
    else:
        monkeypatch.delenv(PUBLIC_URL_VARIABLE, raising=False)

    with pytest.raises(error):
        await flows.admit_forgotten_password(ADDRESS, ALICE)

    assert (forgot_limits.by_address.count(ADDRESS), forgot_limits.by_identifier.count(ALICE)) == (0, 0)
    print_success(f"{error.__name__}, nothing counted")


@pytest.mark.asyncio
async def test_five_requests_per_address_every_fifteen_minutes(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> None:
    """EMF-021 — contract 11: five requests from one address pass, each for another identifier; two minutes later the sixth is ``EmailRateLimitedError`` with ``900 - 120`` seconds to wait; another address passes meanwhile; fifteen minutes after the first five, the address passes again."""
    print_section("EMF-021: per address")
    _usable_without_a_server(monkeypatch)

    clock.now = START
    for index in range(5):
        await flows.admit_forgotten_password(ADDRESS, f"zq_user_{index}")
    clock.now = START + 120
    with pytest.raises(EmailRateLimitedError) as refused:
        await flows.admit_forgotten_password(ADDRESS, "zq_user_5")
    await flows.admit_forgotten_password(OTHER_ADDRESS, "zq_user_5")
    clock.now = START + 900
    await flows.admit_forgotten_password(ADDRESS, "zq_user_6")

    assert refused.value.retry_after == pytest.approx(900 - 120)
    print_success(f"the sixth refused for {refused.value.retry_after:.0f} s; another address and the next window pass")


@pytest.mark.asyncio
async def test_three_requests_per_identifier_every_hour_whatever_the_case(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> None:
    """EMF-022 — contract 11: `` ZQ_Alice ``, ``zq_alice`` and ``Zq_Alice`` from three addresses are one identifier: a minute later ``ZQ_ALICE`` from a fourth address is ``EmailRateLimitedError`` with ``3600 - 60`` seconds; another identifier passes; an hour after the first three, it passes again."""
    print_section("EMF-022: per identifier")
    _usable_without_a_server(monkeypatch)

    clock.now = START
    for index, written in enumerate((" ZQ_Alice ", "zq_alice", "Zq_Alice")):
        await flows.admit_forgotten_password(f"198.51.100.{10 + index}", written)
    clock.now = START + 60
    with pytest.raises(EmailRateLimitedError) as refused:
        await flows.admit_forgotten_password("198.51.100.20", "ZQ_ALICE")
    await flows.admit_forgotten_password("198.51.100.21", BOB)
    clock.now = START + 3600
    await flows.admit_forgotten_password("198.51.100.22", "zq_alice")

    assert refused.value.retry_after == pytest.approx(3600 - 60)
    print_success(f"the fourth refused for {refused.value.retry_after:.0f} s; another identifier and the next hour pass")


@pytest.mark.asyncio
async def test_the_instance_budget_is_peeked_never_spent(monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, clock: FakeClock) -> None:
    """EMF-023 — contract 11: ``LIBREFOLIO_SMTP_MAX_PER_HOUR=1``: with the budget whole an admission passes and spends nothing; with its only unit spent, 30 s later the next is ``EmailRateLimitedError`` with ``3600 - 30`` seconds, and the budget still holds one unit."""
    print_section("EMF-023: the budget, peeked")
    _usable_without_a_server(monkeypatch, max_per_hour="1")

    clock.now = START
    await flows.admit_forgotten_password(ADDRESS, ALICE)
    spent_by_the_admission = budget.count()
    budget.hit(limit=1)
    clock.now = START + 30
    with pytest.raises(EmailRateLimitedError) as refused:
        await flows.admit_forgotten_password(OTHER_ADDRESS, BOB)

    assert spent_by_the_admission == 0
    assert refused.value.retry_after == pytest.approx(3600 - 30)
    assert budget.count() == 1
    print_success("admitted without spending; refused when spent")


def test_the_shipped_limits() -> None:
    """EMF-024 — contract 11: the module ships ``FORGOT_BY_ADDRESS`` 5 per 900 s, ``FORGOT_BY_IDENTIFIER`` 3 per 3600 s (both ``SlidingWindowLimiter``), and per account one email every 5 minutes and 3 an hour."""
    print_section("EMF-024: shipped limits")

    assert isinstance(SHIPPED_BY_ADDRESS, SlidingWindowLimiter) and (SHIPPED_BY_ADDRESS.limit, SHIPPED_BY_ADDRESS.window_seconds) == (5, 900)
    assert isinstance(SHIPPED_BY_IDENTIFIER, SlidingWindowLimiter) and (SHIPPED_BY_IDENTIFIER.limit, SHIPPED_BY_IDENTIFIER.window_seconds) == (3, 3600)
    assert (flows.RESET_EMAIL_MIN_INTERVAL, flows.RESET_EMAILS_PER_HOUR) == (timedelta(minutes=5), 3)
    print_success("5/15 min, 3/h; per account 1/5 min, 3/h")


@pytest.mark.asyncio
async def test_without_a_client_address_only_the_limit_per_address_is_skipped(monkeypatch: pytest.MonkeyPatch, clock: FakeClock, budget: SlidingWindowLimiter, forgot_limits: ForgotLimits) -> None:
    """EMF-032 — contract 11: ``address=None`` — a unix socket —: seven admissions for seven identifiers pass, more than the five one address may make, and the limiter per address holds no key at all, not even a shared one. The limit per identifier still applies — ``ZQ_ALICE`` a minute after three ``zq_alice``: ``3600 - 60`` seconds —, and so does the hourly budget (``LIBREFOLIO_SMTP_MAX_PER_HOUR=1``, its unit spent: ``3600 - 30`` seconds)."""
    print_section("EMF-032: no client address")
    _usable_without_a_server(monkeypatch, max_per_hour="1")

    clock.now = START
    for index in range(7):
        await flows.admit_forgotten_password(None, f"zq_user_{index}")
    for _ in range(3):
        await flows.admit_forgotten_password(None, ALICE)
    clock.now = START + 60
    with pytest.raises(EmailRateLimitedError) as by_identifier:
        await flows.admit_forgotten_password(None, "ZQ_ALICE")
    assert budget.hit(limit=1).allowed, "setup: the only unit of the hour"
    clock.now = START + 90
    with pytest.raises(EmailRateLimitedError) as by_budget:
        await flows.admit_forgotten_password(None, BOB)

    assert len(forgot_limits.by_address) == 0, "a request without an address must be counted under no key"
    assert by_identifier.value.retry_after == pytest.approx(3600 - 60)
    assert by_budget.value.retry_after == pytest.approx(3600 - 30)
    print_success("no key per address; the identifier and the budget still refuse")


# =============================================================================
# 12. forgotten_password_work
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("written", [ALICE, f"{ALICE}@example.com", f"  {ALICE}  "], ids=["username", "email", "spaces-around"])
async def test_the_work_emails_a_new_valid_reset_link_to_the_account(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, written: str) -> None:
    """EMF-025 — contract 12: by username, by email address, or with spaces around: one email to the account's address, exactly ``build_password_reset`` in the account's language (``it``) with the PUBLIC_URL link of a new token — valid, of that account, its only reset row —; one unit spent; no log event holds the identifier or the token.

    Barrier first: the work's own success is among the captured events, so the capture hears it.
    """
    print_section(f"EMF-025: forgotten password, {written!r}")
    alice = await _add_user(engine, ALICE)
    await _set_account_language(engine, alice.id, "it")

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with capture_logs() as events:
            returned = await flows.forgotten_password_work(written, engine=engine)

    assert returned is None
    assert [message.rcpt_tos for message in fake.messages] == [[alice.email]]
    token = _token_in(_text(fake.messages[0]), PASSWORD_RESET)
    inspection = await _inspect(engine, token, PASSWORD_RESET)
    assert (inspection.status, inspection.record.user_id) == (TokenStatus.VALID, alice.id)
    _assert_is(fake.messages[0], build_password_reset(language="it", username=ALICE, link=f"{PUBLIC_URL}/reset-password#token={token}", ttl=DEFAULT_TTL[PASSWORD_RESET], instance=PUBLIC_HOST))
    assert [row.id for row in await _reset_rows(engine, alice.id)] == [inspection.record.id]
    assert budget.count() == 1
    assert any(event.get("event") == "Forgotten password: reset link emailed" for event in events), f"barrier: the work's success is not among the captured events: {events}"
    leaked = [event for event in events if written.strip() in repr(event) or token in repr(event)]
    assert leaked == [], f"a log event holds the identifier or the token: {leaked}"
    print_success(f"one valid link to {alice.email}, in it")


@pytest.mark.asyncio
@pytest.mark.parametrize("who", ["unknown", "inactive"])
async def test_the_work_sends_nothing_to_an_unknown_or_inactive_account(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, who: str) -> None:
    """EMF-026 — contract 12: an identifier no account has, or an inactive account: nothing sent, no reset row, nothing spent, nothing raised."""
    print_section(f"EMF-026: {who}")
    dora = await _add_user(engine, "zq_dora", active=False)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        returned = await flows.forgotten_password_work("zq_nobody" if who == "unknown" else "zq_dora", engine=engine)

    assert returned is None
    assert (fake.connections, budget.count()) == (0, 0)
    assert await _reset_rows(engine, dora.id) == []
    print_success("nothing sent, no row")


@pytest.mark.asyncio
@pytest.mark.parametrize(("age", "sent"), [pytest.param(timedelta(minutes=5) - timedelta(seconds=1), False, id="4m59s-ago-nothing"), pytest.param(timedelta(minutes=5), True, id="5m-ago-sent")])
async def test_one_reset_email_every_five_minutes_per_account(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, age: timedelta, sent: bool) -> None:
    """EMF-027 — contract 12: the account has a reset link an administrator made ``age`` before the request — every reset row counts, whoever made it —: 4 min 59 s ago, nothing is sent and no row added; 5 min ago, the email goes and a row is added."""
    print_section(f"EMF-027: a reset row {age} old")
    admin = await _add_user(engine, ADMIN)
    alice = await _add_user(engine, ALICE)
    moment = utcnow()
    await _issue(engine, PASSWORD_RESET, user_id=alice.id, created_by_user_id=admin.id, now=moment - age)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        await flows.forgotten_password_work(ALICE, engine=engine, now=moment)

    assert (len(fake.messages), len(await _reset_rows(engine, alice.id))) == ((1, 2) if sent else (0, 1))
    print_success("sent" if sent else "silence")


@pytest.mark.asyncio
@pytest.mark.parametrize(("ages", "sent"), [pytest.param((50, 40, 30), False, id="three-in-the-hour-nothing"), pytest.param((60, 40, 30), True, id="one-exactly-an-hour-ago-not-counted-sent")])
async def test_three_reset_emails_an_hour_per_account_counting_every_row(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, ages: tuple[int, int, int], sent: bool) -> None:
    """EMF-028 — contract 12: three reset rows made ``ages`` minutes before the request — one consumed, one revoked, one left to expire: each counts whatever became of it —: three in the hour, nothing is sent; the oldest exactly an hour ago no longer counts, and the email goes."""
    print_section(f"EMF-028: reset rows {ages} minutes old")
    alice = await _add_user(engine, ALICE)
    moment = utcnow()
    issued = [await _issue(engine, PASSWORD_RESET, user_id=alice.id, now=moment - timedelta(minutes=minutes)) for minutes in ages]
    async with AsyncSession(engine) as session:
        assert await token_service.consume_token(session, issued[0].token, PASSWORD_RESET, now=moment - timedelta(minutes=ages[0] - 1)) is not None, "setup: consumed"
        assert await token_service.revoke_tokens(session, token_id=issued[1].record.id, now=moment - timedelta(minutes=ages[1] - 1)) == 1, "setup: revoked"
        await session.commit()

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        await flows.forgotten_password_work(ALICE, engine=engine, now=moment)

    assert (len(fake.messages), len(await _reset_rows(engine, alice.id))) == ((1, 4) if sent else (0, 3))
    print_success("sent" if sent else "silence")


@pytest.mark.asyncio
async def test_the_work_revokes_the_accounts_earlier_live_reset_links(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine) -> None:
    """EMF-029 — contract 12: a live reset link an administrator made ten minutes earlier is revoked by the work, and the emailed one is valid."""
    print_section("EMF-029: earlier links revoked")
    admin = await _add_user(engine, ADMIN)
    alice = await _add_user(engine, ALICE)
    moment = utcnow()
    earlier = await _issue(engine, PASSWORD_RESET, user_id=alice.id, created_by_user_id=admin.id, now=moment - timedelta(minutes=10))
    assert (await _inspect(engine, earlier.token, PASSWORD_RESET)).status == TokenStatus.VALID, "precondition: the earlier link is live"

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        await flows.forgotten_password_work(ALICE, engine=engine, now=moment)

    token = _token_in(_text(fake.messages[0]), PASSWORD_RESET)
    assert (await _inspect(engine, earlier.token, PASSWORD_RESET)).status == TokenStatus.REVOKED
    assert (await _inspect(engine, token, PASSWORD_RESET)).status == TokenStatus.VALID
    print_success("the earlier link revoked, the new one valid")


@pytest.mark.asyncio
@pytest.mark.parametrize("gone", ["links", "links-no-longer-usable", "email", "budget", "blocked"])
async def test_the_work_makes_nothing_when_the_configuration_went_away(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, gone: str) -> None:
    """EMF-030 — contract 12: the configuration admitted the request; before the work, ``LIBREFOLIO_PUBLIC_URL`` went away or became an address no link can start from, ``LIBREFOLIO_SMTP_HOST`` went away, the hourly budget was spent (``LIBREFOLIO_SMTP_MAX_PER_HOUR=1``, its unit taken), or the hosting provider blocked the instance. The work checks again before it makes the link: no new reset row, the live link an administrator made ten minutes earlier still live — nothing revoked it —, no connection, nothing more spent, nothing raised. It logs why it stopped: the barrier that it went past the account and its limits."""
    print_section(f"EMF-030: {gone} before the work")
    admin = await _add_user(engine, ADMIN)
    alice = await _add_user(engine, ALICE)
    moment = utcnow()
    earlier = await _issue(engine, PASSWORD_RESET, user_id=alice.id, created_by_user_id=admin.id, now=moment - timedelta(minutes=10))

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake, max_per_hour="1")
        if gone == "links":
            monkeypatch.delenv(PUBLIC_URL_VARIABLE)
        elif gone == "links-no-longer-usable":
            monkeypatch.setenv(PUBLIC_URL_VARIABLE, NO_LINK_FROM_IT)
        elif gone == "email":
            monkeypatch.delenv(f"{SMTP_PREFIX}HOST")
        elif gone == "blocked":
            monkeypatch.setenv(BLOCKED_VARIABLE, "1")
        else:
            assert budget.hit(limit=1).allowed, "setup: the only unit of the hour"
        spent = budget.count()
        with capture_logs() as events:
            returned = await flows.forgotten_password_work(ALICE, engine=engine, now=moment)

    assert returned is None
    assert (fake.connections, fake.messages, budget.count()) == (0, [], spent)
    assert [row.id for row in await _reset_rows(engine, alice.id)] == [earlier.record.id], "nothing may be made when the email cannot go"
    assert (await _inspect(engine, earlier.token, PASSWORD_RESET)).status == TokenStatus.VALID, "the earlier link must stay live"
    stopped = [event for event in events if str(event.get("event", "")).startswith("Forgotten password") and event.get("log_level") == "warning"]
    assert stopped, f"barrier: the work went past the account and its limits, and logged why it stopped: {events}"
    print_success(f"no new row, the earlier link live ({stopped[-1]['event']})")


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["smtp-refuses-the-recipient", "value-error-while-building", "unexpected-error-while-building", "language-fails-after-reading"])
async def test_the_work_never_raises_and_revokes_a_link_it_could_not_send(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, failure: str) -> None:
    """EMF-031 — contract 12: after the work made the link, the SMTP server refuses the account's address, a ``ValueError`` or an unexpected ``RuntimeError`` happens while the email is built, or reading the account's language fails once it has queried the database: the work returns, raises nothing, sends nothing, and logs the failure without the identifier (the account's address). Whatever stopped it, the link the work made — the account's only reset row — is revoked: no live link reaches nobody."""
    print_section(f"EMF-031: {failure}")
    alice = await _add_user(engine, ALICE)

    def failing_builder(**arguments: object) -> object:
        raise ValueError("zq-value-error") if failure == "value-error-while-building" else RuntimeError("zq-unexpected failure")

    async def failing_language(session: AsyncSession, user_id: int) -> str:
        await session.execute(select(UserSettings.language).where(UserSettings.user_id == user_id))
        raise RuntimeError("zq-language failure")

    with FakeSmtpServer(refuse_recipients={alice.email} if failure.startswith("smtp") else ()) as fake:
        _ready(monkeypatch, fake)
        if failure.endswith("while-building"):
            monkeypatch.setattr(flows, "build_password_reset", failing_builder)
        elif failure == "language-fails-after-reading":
            monkeypatch.setattr(flows, "account_language", failing_language)
        with capture_logs() as events:
            returned = await flows.forgotten_password_work(alice.email, engine=engine)

    assert returned is None
    assert fake.messages == []
    failures = [event for event in events if str(event.get("event", "")).startswith("Forgotten password") and event.get("log_level") in ("warning", "error")]
    assert failures, f"barrier: the failure must be logged: {events}"
    assert [event for event in events if alice.email in repr(event)] == [], f"a log event holds the identifier: {events}"
    rows = await _reset_rows(engine, alice.id)
    assert len(rows) == 1 and rows[0].revoked_at is not None, f"the link that reached nobody must be revoked: {[(row.id, row.revoked_at) for row in rows]}; the work logged {failures}"
    print_success(f"{failures[-1]['event']}, the link revoked, nothing raised")


# =============================================================================
# 13. A BLOCKED INSTANCE
# =============================================================================


@pytest.mark.asyncio
async def test_a_blocked_instance_sends_nothing_through_any_flow_and_makes_no_link(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, forgot_limits: ForgotLimits) -> None:
    """EMF-033 — contract 13: email and links ready towards a running fake, ``LIBREFOLIO_BLOCKED=1``. ``send_test_email``, ``send_link_email`` for a live invitation and a live reset link, and ``admit_forgotten_password`` raise ``EmailUnavailableError`` with ``INSTANCE_BLOCKED``: the links still live, no limiter counting. ``forgotten_password_work`` for Bob — whose reset link made ten minutes ago lets the work past his limits — returns, raises nothing, makes no reset row and revokes nothing: his earlier link is still live and still his only row; the work logs why it stopped (the barrier). No connection, nothing spent."""
    print_section("EMF-033: a blocked instance")
    admin = await _add_user(engine, ADMIN)
    alice = await _add_user(engine, ALICE)
    bob = await _add_user(engine, BOB)
    moment = utcnow()
    invitation = await _issue(engine, INVITE, email=GUEST, created_by_user_id=admin.id)
    reset = await _issue(engine, PASSWORD_RESET, user_id=alice.id, created_by_user_id=admin.id)
    earlier = await _issue(engine, PASSWORD_RESET, user_id=bob.id, created_by_user_id=admin.id, now=moment - timedelta(minutes=10))

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        monkeypatch.setenv(BLOCKED_VARIABLE, "1")
        codes = []
        async with AsyncSession(engine) as session:
            for attempt in (
                lambda: send_test_email(session, admin, instance=INSTANCE),
                lambda: flows.send_link_email(session, admin=admin, purpose="invite", token=invitation.token),
                lambda: flows.send_link_email(session, admin=admin, purpose="password_reset", token=reset.token),
                lambda: flows.admit_forgotten_password(ADDRESS, BOB),
            ):
                with pytest.raises(EmailUnavailableError) as refused:
                    await attempt()
                codes.append(refused.value.code)
        with capture_logs() as events:
            returned = await flows.forgotten_password_work(BOB, engine=engine, now=moment)

    assert codes == ["INSTANCE_BLOCKED"] * 4, codes
    assert returned is None
    assert (fake.connections, budget.count(), len(forgot_limits.by_address), len(forgot_limits.by_identifier)) == (0, 0, 0, 0)
    statuses = [(await _inspect(engine, token, purpose)).status for token, purpose in ((invitation.token, INVITE), (reset.token, PASSWORD_RESET), (earlier.token, PASSWORD_RESET))]
    assert statuses == [TokenStatus.VALID] * 3, statuses
    assert [row.id for row in await _reset_rows(engine, bob.id)] == [earlier.record.id], "a blocked instance must make no reset row"
    stopped = [event for event in events if str(event.get("event", "")).startswith("Forgotten password") and event.get("log_level") == "warning"]
    assert stopped, f"barrier: the work went past Bob and his limits, and logged why it stopped: {events}"
    print_success("INSTANCE_BLOCKED four times; the work made no link and revoked none")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("block", "also"),
    [
        pytest.param("1", "email-off", id="blocked-and-email-off"),
        pytest.param("1", "links-missing", id="blocked-and-links-missing"),
        pytest.param("true", "a-token-never-issued", id="blocked-and-a-token-never-issued"),
        pytest.param("maybe", "nothing-else", id="block-unreadable"),
    ],
)
async def test_the_block_is_asked_before_anything_else_by_every_flow(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, forgot_limits: ForgotLimits, block: str, also: str) -> None:
    """EMF-034 — contract 13: ``LIBREFOLIO_BLOCKED`` blocking — or unreadable — and, besides, email off, links missing or a token never issued: ``send_link_email`` and ``admit_forgotten_password`` raise ``EmailUnavailableError("INSTANCE_BLOCKED")`` itself — not ``EMAIL_NOT_CONFIGURED``, ``EmailLinksUnavailableError`` nor ``EmailLinkInvalidError`` —: the block is asked first. Nothing counted, nothing sent, nothing spent."""
    print_section(f"EMF-034: LIBREFOLIO_BLOCKED={block!r}, {also}")
    admin = await _add_user(engine, ADMIN)
    token = NEVER_ISSUED if also == "a-token-never-issued" else (await _issue(engine, INVITE, email=GUEST, created_by_user_id=admin.id)).token

    with FakeSmtpServer() as fake:
        if also != "email-off":
            _point_at(monkeypatch, fake)
        if also != "links-missing":
            monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)
        monkeypatch.setenv(BLOCKED_VARIABLE, block)
        async with AsyncSession(engine) as session:
            with pytest.raises(EmailError) as linked:
                await flows.send_link_email(session, admin=admin, purpose="invite", token=token)
        with pytest.raises(EmailError) as admitted:
            await flows.admit_forgotten_password(ADDRESS, ALICE)

    for raised in (linked.value, admitted.value):
        assert (type(raised), raised.code) == (EmailUnavailableError, "INSTANCE_BLOCKED"), repr(raised)
    assert (fake.connections, budget.count(), len(forgot_limits.by_address), len(forgot_limits.by_identifier)) == (0, 0, 0, 0)
    print_success("INSTANCE_BLOCKED first, from both")
