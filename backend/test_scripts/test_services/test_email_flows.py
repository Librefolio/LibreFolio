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
   missing — English. ``account_language`` reads the language column alone: a row whose theme this version does not
   know (outside light/dark/auto, written as a row), which the schema ``UserSettingsRead`` refuses, still gives its
   language. It never creates nor changes a ``user_settings`` row: reading a language changes nothing.
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
    ``EmailRecipientNotAllowedError``, and the reset link of an inactive account is ``EmailAccountInactiveError``
    (``EMAIL_ACCOUNT_INACTIVE``), the link left live. The email is exactly what the builder writes for that language
    with the ``LIBREFOLIO_PUBLIC_URL`` link of the token, the host of that address as the instance, the administrator as
    the inviter and the administrator's role sentence when the invitation grants it; one unit spent. The token is in no
    log event.
11. ``admit_forgotten_password`` ships open (lot E4 removed its hold, ``FORGOT_PASSWORD_HELD``, once changing an
    account's email asked for the current password). It reads the configuration first — email, then links —,
    counting nothing when it refuses; then 10 requests per 15 minutes per client address — keyed
    by workstream H's ``client_rate_key``, the one home of the per-client key (decision P17; ``flows`` keeps no copy):
    an IPv4 address as is, an IPv6 one by its /64 (a zone ignored), an IPv4-mapped one as the IPv4, anything else as
    written — and 3 per hour per identifier (stripped, case-insensitive), each refusal an
    ``EmailRateLimitedError`` with the seconds until the window frees; then the instance's hourly budget, peeked, never
    spent. Without a client address (a unix socket) the limit per address does not apply — one shared count would let
    a single client block everyone —, while the limit per identifier and the budget still do. The shipped limits are
    10/900 s per address, 3/3600 s per identifier and per mailbox, and per account one email every 5 minutes and 3 an
    hour.
12. ``forgotten_password_work`` finds the account as the login does — by username or email, spaces around ignored —,
    active only; per account at most one reset link every 5 minutes and 3 an hour, counted on every password-reset row
    whatever made it or became of it; an administrator's reset link still live stops it, nothing made nor revoked. It
    then reads the configuration again — the instance not blocked, email usable, links ready, a unit of the hourly
    budget free —, counts the recipient's mailbox (3 an hour, without case, whatever the account), and only then makes
    the new reset link: when one of them is missing, nothing is made and the account's earlier live links stay live.
    Making it revokes the account's earlier live reset links; counted again inside the write transaction, its own link
    included, more than one in five minutes or more than three in the hour — a link made meanwhile by another request —
    rolls it all back, what it revoked live again. The new link is emailed, valid, in the account's language, built from
    ``LIBREFOLIO_PUBLIC_URL``, and when anything stops the email after the link was made — the server refusing, an error
    while the email is built or while the account's language is read — the new link is revoked: no live link reaches
    nobody. Unknown, inactive, past its limits, the configuration gone, the email refused, an unexpected error: nothing
    is sent and nothing is raised; an unexpected error is logged as its type alone, without a traceback (whose rendering
    would print a database error's parameters). Neither the identifier nor the token is in any log event.
13. A blocked instance (``LIBREFOLIO_BLOCKED`` blocking, or unreadable) sends nothing through any flow, and every flow
    asks it first: ``send_test_email``, ``send_link_email`` and ``admit_forgotten_password`` raise
    ``EmailUnavailableError`` with ``INSTANCE_BLOCKED`` before the configuration, the links, the token or a limiter is
    looked at — the links still live, nothing counted, nothing spent —; ``forgotten_password_work`` ends in silence
    without making a reset row or revoking any.
14. ``email_changed_work(user_id, old_address, new_address, *, engine)`` (lot E4a), the notice of an email change: one
    message to the OLD address only — never the new one —, exactly what ``build_email_changed`` writes in the account's
    language — greeting nobody by name, and carrying no part of the new address, neither its local part nor its domain
    (decision N62, E-9 b and c) —, the instance being the host of ``LIBREFOLIO_PUBLIC_URL`` when links are ready and
    ``INSTANCE_FALLBACK`` («LibreFolio») otherwise — never a request's host —; one unit spent. Nothing when the two
    addresses are the same by ``user_service.same_email`` — A's one rule of decision P18 (lot E4c): A–Z in any case,
    every other character as written, nothing stripped —, nothing logged either; a letter beyond A–Z in another case
    makes another address, whose notice goes to the old one as written. Email off — the self-hosted default — is an
    ``info`` line and no warning, decided before any session is opened; the account gone is an ``info`` line, and so is
    a notice past its limits (contract 15); email set but unusable or the instance blocked, the budget spent, the server
    refusing, an old address that is not one address: a warning ``not sent`` with the reason's type and code; any other
    error an error with its type alone, without a traceback. It never raises, reads the configuration off the event
    loop, and no log event holds either address.
15. The limits of the notice (lot E4b, security review): ``EMAIL_CHANGE_NOTICES_BY_ACCOUNT`` and
    ``EMAIL_CHANGE_NOTICES_BY_MAILBOX`` ship as two ``SlidingWindowLimiter`` of 3 per 3600 s, keyed by the account's id
    and by the old mailbox, letter case aside. Before it writes anything, the work asks both: when the account, or the
    old mailbox — whatever the account and however its letters are written —, already had 3 notices in the window, one
    ``info`` line «past its limits, nothing sent» with the account's id, no warning and neither address; nothing is
    composed, no SMTP conversation is opened, no unit of the budget is spent, and neither limiter counts it. A notice
    counts under both only once it went: one the server refused counts for neither, so the next one goes. The window
    slides: 3600 s after the first of three notices, the next one goes.
16. Aliases of one mailbox share its budget (E-9 a): ``FORGOT_BY_MAILBOX`` and ``EMAIL_CHANGE_NOTICES_BY_MAILBOX`` key a
    mailbox by ``delivery.mailbox_budget_key`` — the ``+tag`` cut on every domain, the dots of a Gmail local part
    removed, ``googlemail.com`` read as ``gmail.com``, letter case aside —, never by the address as written. Four aliases
    of one Gmail mailbox get three reset emails, or three notices, between them, each at its account's stored address
    — or the address its change left — exactly as written (the key is never a recipient); the fourth is held like any
    past the mailbox's limit, with the same ``info`` line. Outside Gmail a dot is part of the mailbox: ``zq.a@`` and
    ``zqa@outlook.com`` keep a budget each.

Pure: every database is a private SQLite file under ``tmp_path`` built with ``create_all`` and the default global
settings (NullPool, disposed at teardown), users written as rows, tokens issued by A's token service with the ``now``
the case needs; no server of the lane, no network beyond 127.0.0.1. An autouse fixture removes every inherited
``LIBREFOLIO_SMTP_*``, ``LIBREFOLIO_PUBLIC_URL`` and ``LIBREFOLIO_BLOCKED`` (C-96 removes them from the lanes; a
developer's shell may still carry them) and each test sets its own with ``monkeypatch``; others replace
``delivery.INSTANCE_BUDGET``, the three «forgot password» limiters (``flows.FORGOT_BY_ADDRESS``,
``flows.FORGOT_BY_IDENTIFIER``, ``flows.FORGOT_BY_MAILBOX``) and the two of the notice
(``flows.EMAIL_CHANGE_NOTICES_BY_ACCOUNT``, ``flows.EMAIL_CHANGE_NOTICES_BY_MAILBOX``), these five with the shipped
limits, with private limiters on a fake clock — «forgot password» has no hold left to lift (lot E4); the accounts of
these new databases repeat their ids and addresses from test to test, which the process's limiters would count across
tests —;
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
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import AccountToken, AccountTokenPurpose, GlobalSetting, User, UserSettings
from backend.app.schemas.settings import SETTINGS_REGISTRY, UserSettingsRead
from backend.app.services.accounts import token_service, user_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.accounts.token_service import DEFAULT_TTL, IssuedToken, TokenInspection, TokenStatus
from backend.app.services.email import delivery, flows, smtp
from backend.app.services.email.delivery import EmailError, EmailRateLimitedError, EmailUnavailableError
from backend.app.services.email.flows import account_language, send_test_email
from backend.app.services.email.links import EmailLinksUnavailableError, email_link
from backend.app.services.email.messages import EmailRecipientError, build_email_changed, build_invite, build_password_reset, build_test_message, email_language, supported_email_language
from backend.app.services.platform.client_address import client_rate_key
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
SHIPPED_BY_MAILBOX = flows.FORGOT_BY_MAILBOX
#: The limiters of the email-change notice as the module ships them (lot E4b), read before any fixture replaces them.
SHIPPED_NOTICES_BY_ACCOUNT = flows.EMAIL_CHANGE_NOTICES_BY_ACCOUNT
SHIPPED_NOTICES_BY_MAILBOX = flows.EMAIL_CHANGE_NOTICES_BY_MAILBOX
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
    """The three «forgot password» limiters of a test: per client address, per identifier, per recipient mailbox."""

    by_address: SlidingWindowLimiter
    by_identifier: SlidingWindowLimiter
    by_mailbox: SlidingWindowLimiter


@pytest.fixture(autouse=True)
def forgot_limits(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> ForgotLimits:
    """Private «forgot password» limiters with the shipped limits, on the fake clock: no test counts in, or is counted by, the process's."""
    limits = ForgotLimits(
        by_address=SlidingWindowLimiter(SHIPPED_BY_ADDRESS.limit, SHIPPED_BY_ADDRESS.window_seconds, clock=clock),
        by_identifier=SlidingWindowLimiter(SHIPPED_BY_IDENTIFIER.limit, SHIPPED_BY_IDENTIFIER.window_seconds, clock=clock),
        by_mailbox=SlidingWindowLimiter(SHIPPED_BY_MAILBOX.limit, SHIPPED_BY_MAILBOX.window_seconds, clock=clock),
    )
    monkeypatch.setattr(flows, "FORGOT_BY_ADDRESS", limits.by_address)
    monkeypatch.setattr(flows, "FORGOT_BY_IDENTIFIER", limits.by_identifier)
    monkeypatch.setattr(flows, "FORGOT_BY_MAILBOX", limits.by_mailbox)
    return limits


@dataclass(frozen=True)
class NoticeLimits:
    """The two limiters of the email-change notice of a test: per account, per old mailbox."""

    by_account: SlidingWindowLimiter
    by_mailbox: SlidingWindowLimiter


@pytest.fixture(autouse=True)
def notice_limits(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> NoticeLimits:
    """Private limiters of the email-change notice with the shipped limits, on the fake clock: every database here is new, so its accounts repeat their ids and addresses from test to test, and the process's limiters would count them across tests."""
    limits = NoticeLimits(
        by_account=SlidingWindowLimiter(SHIPPED_NOTICES_BY_ACCOUNT.limit, SHIPPED_NOTICES_BY_ACCOUNT.window_seconds, clock=clock),
        by_mailbox=SlidingWindowLimiter(SHIPPED_NOTICES_BY_MAILBOX.limit, SHIPPED_NOTICES_BY_MAILBOX.window_seconds, clock=clock),
    )
    monkeypatch.setattr(flows, "EMAIL_CHANGE_NOTICES_BY_ACCOUNT", limits.by_account)
    monkeypatch.setattr(flows, "EMAIL_CHANGE_NOTICES_BY_MAILBOX", limits.by_mailbox)
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


def _unknown_theme_refusal() -> str:
    """The precondition, verified: the schema ``UserSettingsRead`` refuses ``STALE_THEME``, a theme this version does not know; what it said."""
    with pytest.raises(ValidationError) as refused:
        UserSettingsRead(language="it", base_currency="EUR", theme=STALE_THEME)
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
async def test_a_theme_this_version_does_not_know_still_gives_its_language(engine: AsyncEngine) -> None:
    """EMF-009 — contract 4: Alice's row holds ``it`` with a theme this version does not know (``sepia``, written as a row), the instance says ``fr``: ``account_language`` is ``it`` — it reads the language column alone — and the row is left as it was.

    Barrier first: the schema ``UserSettingsRead`` refuses that theme with a ``ValidationError`` naming it — otherwise
    this would only be one more row with a valid theme.
    """
    print_section("EMF-009: a theme this version does not know")
    refusal = _unknown_theme_refusal()
    assert "theme" in refusal, f"barrier: the schema must refuse the theme: {refusal}"
    alice = await _add_user(engine, ALICE)
    await _set_account_language(engine, alice.id, "it", theme=STALE_THEME)
    await _set_default_language(engine, "fr")

    language = await _language_of(engine, alice.id)

    assert language == "it", f"the account says 'it' with a theme this version does not know, the instance 'fr': got {language!r}"
    assert await _settings_row(engine, alice.id) == ("it", STALE_THEME), "account_language must leave the row as it was"
    print_success("'it' from a row with a theme this version does not know; the row untouched")


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
    """EMF-017 — contract 10: a reset link goes to the address of its account, in the account's language (its own, else the instance's ``fr``); the email is exactly ``build_password_reset`` with the PUBLIC_URL link and PUBLIC_URL's host, and greets nobody by name — the username is in no part of it (decision N62) —; ``LinkEmailSent(the account's address, language)``; one unit spent."""
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
    assert ALICE not in _text(fake.messages[0]) + _html(fake.messages[0]), "a reset email greets nobody by name: the username is text its owner chose (N62)"
    _assert_is(fake.messages[0], build_password_reset(language=language, link=link, ttl=DEFAULT_TTL[PASSWORD_RESET], instance=PUBLIC_HOST))
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
async def test_ten_requests_per_address_every_fifteen_minutes(monkeypatch: pytest.MonkeyPatch, clock: FakeClock, forgot_limits: ForgotLimits) -> None:
    """EMF-021 — contract 11: ten requests from one IPv4 address pass, each for another identifier, and are counted under that address as is; two minutes later the eleventh is ``EmailRateLimitedError`` with ``900 - 120`` seconds to wait; another address passes meanwhile; fifteen minutes after the first ten, the address passes again."""
    print_section("EMF-021: per address")
    _usable_without_a_server(monkeypatch)

    clock.now = START
    for index in range(10):
        await flows.admit_forgotten_password(ADDRESS, f"zq_user_{index}")
    counted = forgot_limits.by_address.count(ADDRESS)
    clock.now = START + 120
    with pytest.raises(EmailRateLimitedError) as refused:
        await flows.admit_forgotten_password(ADDRESS, "zq_user_10")
    await flows.admit_forgotten_password(OTHER_ADDRESS, "zq_user_10")
    clock.now = START + 900
    await flows.admit_forgotten_password(ADDRESS, "zq_user_11")

    assert counted == 10, f"the ten requests from {ADDRESS} must be counted under it: {counted}"
    assert refused.value.retry_after == pytest.approx(900 - 120)
    print_success(f"the eleventh refused for {refused.value.retry_after:.0f} s; another address and the next window pass")


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
    """EMF-024 — contract 11: the module ships ``FORGOT_BY_ADDRESS`` 10 per 900 s, ``FORGOT_BY_IDENTIFIER`` 3 per 3600 s, ``FORGOT_BY_MAILBOX`` 3 per 3600 s (all ``SlidingWindowLimiter``), and per account one email every 5 minutes and 3 an hour."""
    print_section("EMF-024: shipped limits")

    assert isinstance(SHIPPED_BY_ADDRESS, SlidingWindowLimiter) and (SHIPPED_BY_ADDRESS.limit, SHIPPED_BY_ADDRESS.window_seconds) == (10, 900)
    assert isinstance(SHIPPED_BY_IDENTIFIER, SlidingWindowLimiter) and (SHIPPED_BY_IDENTIFIER.limit, SHIPPED_BY_IDENTIFIER.window_seconds) == (3, 3600)
    assert isinstance(SHIPPED_BY_MAILBOX, SlidingWindowLimiter) and (SHIPPED_BY_MAILBOX.limit, SHIPPED_BY_MAILBOX.window_seconds) == (3, 3600)
    assert (flows.RESET_EMAIL_MIN_INTERVAL, flows.RESET_EMAILS_PER_HOUR) == (timedelta(minutes=5), 3)
    print_success("10/15 min per address, 3/h per identifier and per mailbox; per account 1/5 min, 3/h")


@pytest.mark.asyncio
async def test_without_a_client_address_only_the_limit_per_address_is_skipped(monkeypatch: pytest.MonkeyPatch, clock: FakeClock, budget: SlidingWindowLimiter, forgot_limits: ForgotLimits) -> None:
    """EMF-032 — contract 11: ``address=None`` — a unix socket —: eleven admissions for eleven identifiers pass, more than the ten one address may make, and the limiter per address holds no key at all, not even a shared one. The limit per identifier still applies — ``ZQ_ALICE`` a minute after three ``zq_alice``: ``3600 - 60`` seconds —, and so does the hourly budget (``LIBREFOLIO_SMTP_MAX_PER_HOUR=1``, its unit spent: ``3600 - 30`` seconds)."""
    print_section("EMF-032: no client address")
    _usable_without_a_server(monkeypatch, max_per_hour="1")

    clock.now = START
    for index in range(11):
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
    """EMF-025 — contract 12: by username, by email address, or with spaces around: one email to the account's address, exactly ``build_password_reset`` in the account's language (``it``) with the PUBLIC_URL link of a new token — valid, of that account, its only reset row —, greeting nobody by name: the username, which whoever holds the account chose, is in no part of it (decision N62); one unit spent; no log event holds the identifier or the token.

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
    assert ALICE not in _text(fake.messages[0]) + _html(fake.messages[0]), "a reset email greets nobody by name: the username is text its owner chose (N62)"
    _assert_is(fake.messages[0], build_password_reset(language="it", link=f"{PUBLIC_URL}/reset-password#token={token}", ttl=DEFAULT_TTL[PASSWORD_RESET], instance=PUBLIC_HOST))
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
    """EMF-027 — contract 12: an administrator made the account a reset link ``age`` before the request, and revoked it a second later — every reset row counts, whoever made it and whatever became of it; revoked, it is no live administrator's link, which would stop the work on its own —: 4 min 59 s ago, nothing is sent and no row added; 5 min ago, the email goes and a row is added."""
    print_section(f"EMF-027: a reset row {age} old")
    admin = await _add_user(engine, ADMIN)
    alice = await _add_user(engine, ALICE)
    moment = utcnow()
    made = await _issue(engine, PASSWORD_RESET, user_id=alice.id, created_by_user_id=admin.id, now=moment - age)
    async with AsyncSession(engine) as session:
        assert await token_service.revoke_tokens(session, token_id=made.record.id, now=moment - age + timedelta(seconds=1)) == 1, "setup: revoked"
        await session.commit()

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
    """EMF-029 — contract 12: a live reset link an earlier request made ten minutes before — no administrator made it — is revoked by the work, and the emailed one is valid."""
    print_section("EMF-029: earlier links revoked")
    alice = await _add_user(engine, ALICE)
    moment = utcnow()
    earlier = await _issue(engine, PASSWORD_RESET, user_id=alice.id, now=moment - timedelta(minutes=10))
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
    """EMF-030 — contract 12: the configuration admitted the request; before the work, ``LIBREFOLIO_PUBLIC_URL`` went away or became an address no link can start from, ``LIBREFOLIO_SMTP_HOST`` went away, the hourly budget was spent (``LIBREFOLIO_SMTP_MAX_PER_HOUR=1``, its unit taken), or the hosting provider blocked the instance. The work checks again before it makes the link: no new reset row, the live link an earlier request made ten minutes before still live — nothing revoked it —, no connection, nothing more spent, nothing raised. It logs why it stopped: the barrier that it went past the account and its limits."""
    print_section(f"EMF-030: {gone} before the work")
    alice = await _add_user(engine, ALICE)
    moment = utcnow()
    earlier = await _issue(engine, PASSWORD_RESET, user_id=alice.id, now=moment - timedelta(minutes=10))

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
    """EMF-031 — contract 12: after the work made the link, the SMTP server refuses the account's address, a ``ValueError`` or an unexpected ``RuntimeError`` happens while the email is built, or reading the account's language fails once it has queried the database: the work returns, raises nothing, sends nothing, and logs the failure without the identifier (the account's address) — an unexpected one as its type alone, without a traceback. Whatever stopped it, the link the work made — the account's only reset row — is revoked: no live link reaches nobody."""
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
    if failure in ("unexpected-error-while-building", "language-fails-after-reading"):
        logged = failures[-1]
        assert (logged.get("event"), logged.get("log_level"), logged.get("error")) == ("Forgotten password: the request failed", "error", "RuntimeError"), logged
        assert "exc_info" not in logged, f"an unexpected failure is logged as its type alone, without a traceback: {logged}"
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
    earlier = await _issue(engine, PASSWORD_RESET, user_id=bob.id, now=moment - timedelta(minutes=10))

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


# =============================================================================
# 14. AFTER THE SECURITY REVIEW OF E3
# =============================================================================

#: One mailbox written four ways: accounts are distinct rows, the mailbox is one (compared without case). The ways differ
#: in the case of ``ä`` and ``ö`` alone, in NFC (one code point each): since P18 an address is unique regardless of A–Z
#: case (``ux_users_email_lower``).
ONE_MAILBOX = ["zq-sh\u00e4r\u00f6d@example.com", "zq-sh\u00c4r\u00d6d@example.com", "zq-sh\u00e4r\u00d6d@example.com", "zq-sh\u00c4r\u00f6d@example.com"]


def test_the_key_of_a_client_address_has_one_home() -> None:
    """EMF-036 — contract 11: one home for the per-client key (decision P17). ``flows`` keys ``FORGOT_BY_ADDRESS`` with workstream H's ``client_rate_key`` — the very object ``backend.app.services.platform.client_address`` defines, not a copy — and keeps no key of its own: no ``address_key`` any more. The rule itself — an IPv4 address as is, an IPv4-mapped IPv6 one as the IPv4 it maps, any other IPv6 one by its /64 in canonical form, a zone ignored, anything that is not an IP address as written, no key without an address or with an empty one — is H's to pin, value by value, in ``test_services/test_client_address.py``, section (f); EMF-037 proves the limit per address counts by it."""
    print_section("EMF-036: one home for the per-client key")
    used = getattr(flows, "client_rate_key", None)

    assert used is client_rate_key, f"flows.client_rate_key is {used!r}, not workstream H's client_rate_key: the key of FORGOT_BY_ADDRESS has one home (P17)"
    assert not hasattr(flows, "address_key"), "flows still carries address_key, a second copy of the per-client key: its home is workstream H's client_rate_key (P17)"
    print_success("flows holds H's client_rate_key itself, and no address_key of its own")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("members", "one_more", "outsider", "key"),
    [
        pytest.param([f"2001:db8:1:2::{index:x}" for index in range(1, 11)], "2001:db8:1:2:ffff:ffff:ffff:fffe", "2001:db8:1:3::1", "2001:db8:1:2::/64", id="ipv6-one-64"),
        pytest.param(["198.51.100.7", "::ffff:198.51.100.7"] * 5, "::ffff:198.51.100.7", "198.51.100.8", "198.51.100.7", id="ipv4-and-its-mapped-form"),
    ],
)
async def test_the_limit_per_address_counts_by_the_key(monkeypatch: pytest.MonkeyPatch, clock: FakeClock, forgot_limits: ForgotLimits, members: list[str], one_more: str, outsider: str, key: str) -> None:
    """EMF-037 — contract 11: ten admissions from addresses with one key — ten addresses of one IPv6 /64, or an IPv4 address and its IPv4-mapped form in turn — pass; an eleventh from another address with that key is ``EmailRateLimitedError`` — one subscriber, one count —, while an address with another key passes. Each request names another identifier: only the limit per address can refuse."""
    print_section(f"EMF-037: the count of {key}")
    _usable_without_a_server(monkeypatch)

    clock.now = START
    for index, address in enumerate(members):
        await flows.admit_forgotten_password(address, f"zq_user_{index}")
    with pytest.raises(EmailRateLimitedError) as refused:
        await flows.admit_forgotten_password(one_more, "zq_user_one_more")
    await flows.admit_forgotten_password(outsider, "zq_user_outsider")

    assert refused.value.retry_after == pytest.approx(900)
    assert (forgot_limits.by_address.count(key), forgot_limits.by_address.count(client_rate_key(outsider))) == (10, 1)
    print_success(f"ten under {key}, the eleventh refused; another key passes")


@pytest.mark.asyncio
async def test_three_reset_emails_an_hour_per_mailbox_whatever_the_account(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, clock: FakeClock, budget: SlidingWindowLimiter, forgot_limits: ForgotLimits) -> None:
    """EMF-038 — contract 12: four accounts whose addresses are one mailbox written four ways (a mailbox is compared without case; the four differ in the case of ``ä`` and ``ö`` alone, since P18 makes an address unique regardless of A–Z case); each asks once, each well within its own limits. The first three get their email; the fourth gets nothing — the mailbox had three this hour —: no new row, its live link from an earlier request (ten minutes old) still live, nothing more spent, nothing raised. An hour later, by the limiters' clock, the same request for the fourth goes: the mailbox was all that held it."""
    print_section("EMF-038: per mailbox")
    assert len({address.casefold() for address in ONE_MAILBOX}) == 1, "precondition: four spellings of one mailbox"
    assert len({user_service.email_fold(address) for address in ONE_MAILBOX}) == len(ONE_MAILBOX), "precondition: four accounts on one mailbox: one casefold key, four addresses for the A–Z unique index (P18)"
    moment = utcnow()
    accounts = [await _add_user(engine, f"zq_shared_{index}", email=address) for index, address in enumerate(ONE_MAILBOX)]
    earlier = await _issue(engine, PASSWORD_RESET, user_id=accounts[3].id, now=moment - timedelta(minutes=10))

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        clock.now = START
        for account in accounts:
            assert await flows.forgotten_password_work(account.username, engine=engine, now=moment) is None
        held_back = (len(fake.messages), budget.count(), [row.id for row in await _reset_rows(engine, accounts[3].id)], (await _inspect(engine, earlier.token, PASSWORD_RESET)).status)
        clock.now = START + 3600
        await flows.forgotten_password_work(accounts[3].username, engine=engine, now=moment)

    assert [message.rcpt_tos for message in fake.messages[:3]] == [[address] for address in ONE_MAILBOX[:3]]
    assert held_back == (3, 3, [earlier.record.id], TokenStatus.VALID), f"past the mailbox's limit nothing may be made or revoked: {held_back}"
    assert [message.rcpt_tos for message in fake.messages[3:]] == [[ONE_MAILBOX[3]]], "an hour later the fourth request goes"
    print_success("three emails to one mailbox, the fourth held, then sent an hour later")


@pytest.mark.asyncio
@pytest.mark.parametrize(("state", "sent"), [pytest.param("live", False, id="live-stops-the-work"), pytest.param("consumed", True, id="consumed"), pytest.param("revoked", True, id="revoked"), pytest.param("expired", True, id="expired")])
async def test_an_administrators_live_reset_link_stops_the_work(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, state: str, sent: bool) -> None:
    """EMF-039 — contract 12: an administrator made the account a reset link ten minutes ago — past the account's own limits — or, for the expired one, just over its lifetime ago. While it is live, the work stops before making anything: no email, no new row, nothing spent, the administrator's link still live — a stranger's request must not cancel it. Consumed, revoked or expired, it stops nothing: the email goes, with a new link."""
    print_section(f"EMF-039: an administrator's link, {state}")
    admin = await _add_user(engine, ADMIN)
    alice = await _add_user(engine, ALICE)
    moment = utcnow()
    age = DEFAULT_TTL[PASSWORD_RESET] + timedelta(minutes=1) if state == "expired" else timedelta(minutes=10)
    made = await _issue(engine, PASSWORD_RESET, user_id=alice.id, created_by_user_id=admin.id, now=moment - age)
    async with AsyncSession(engine) as session:
        if state == "consumed":
            assert await token_service.consume_token(session, made.token, PASSWORD_RESET, now=moment - age + timedelta(minutes=1)) is not None, "setup: consumed"
        elif state == "revoked":
            assert await token_service.revoke_tokens(session, token_id=made.record.id, now=moment - age + timedelta(minutes=1)) == 1, "setup: revoked"
        await session.commit()

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        await flows.forgotten_password_work(ALICE, engine=engine, now=moment)

    rows = [row.id for row in await _reset_rows(engine, alice.id)]
    if sent:
        assert (len(fake.messages), len(rows)) == (1, 2), f"{len(fake.messages)} message(s), rows {rows}"
    else:
        assert (fake.connections, budget.count(), rows) == (0, 0, [made.record.id])
        assert (await _inspect(engine, made.token, PASSWORD_RESET)).status == TokenStatus.VALID, "the administrator's link must stay live"
    print_success("sent, with a new link" if sent else "nothing made, the administrator's link live")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("earlier_ages", "rival_age", "rival_by_an_administrator"),
    [
        pytest.param((), timedelta(seconds=1), True, id="an-administrators-link-made-meanwhile"),
        pytest.param((50, 30), timedelta(minutes=10), False, id="the-third-link-of-the-hour-made-meanwhile"),
    ],
)
async def test_a_reset_link_made_meanwhile_rolls_the_work_back(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, earlier_ages: tuple[int, ...], rival_age: timedelta, rival_by_an_administrator: bool) -> None:
    """EMF-040 — contract 12: the account passes the work's first count; between that count and the link, another request gives the account a reset link — committed by another session inside ``user_service.create_password_reset``, just before the real one —: an administrator's link a second old, or the third link of the hour. Counted again inside the write transaction, its own link included, the account has more than one in five minutes, or more than three in the hour: the work rolls back — its own row never existed, and the rival link, which making it had revoked, is live again —, sends nothing, spends nothing, raises nothing."""
    print_section(f"EMF-040: a rival link {rival_age} old")
    admin = await _add_user(engine, ADMIN)
    alice = await _add_user(engine, ALICE)
    moment = utcnow()
    earlier = [await _issue(engine, PASSWORD_RESET, user_id=alice.id, now=moment - timedelta(minutes=minutes)) for minutes in earlier_ages]
    rivals: list[IssuedToken] = []
    create = user_service.create_password_reset

    async def create_after_a_rival(session: AsyncSession, user: User, **arguments: object) -> IssuedToken:
        async with AsyncSession(engine, expire_on_commit=False) as other:
            rival = await token_service.issue_token(other, PASSWORD_RESET, user_id=user.id, created_by_user_id=admin.id if rival_by_an_administrator else None, now=moment - rival_age)
            await other.commit()
        rivals.append(rival)
        return await create(session, user, **arguments)

    monkeypatch.setattr(user_service, "create_password_reset", create_after_a_rival)
    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        returned = await flows.forgotten_password_work(ALICE, engine=engine, now=moment)

    assert returned is None
    assert len(rivals) == 1, "barrier: the work went past its first count and made its link"
    assert (fake.connections, budget.count()) == (0, 0)
    rows = [row.id for row in await _reset_rows(engine, alice.id)]
    assert rows == [*(issued.record.id for issued in earlier), rivals[0].record.id], f"the work's own row must be rolled back: {rows}"
    assert (await _inspect(engine, rivals[0].token, PASSWORD_RESET)).status == TokenStatus.VALID, "what making the link revoked must be live again"
    print_success("rolled back: no row of its own, the rival link live, nothing sent")


@pytest.mark.asyncio
async def test_a_reset_link_of_an_inactive_account_is_not_emailed(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter) -> None:
    """EMF-041 — contract 10: an administrator emails the live reset link of an inactive account: ``EmailAccountInactiveError`` — an ``EmailError``, ``EMAIL_ACCOUNT_INACTIVE`` —: it would set a password nobody can use yet. Nothing sent, nothing spent, the link still live."""
    print_section("EMF-041: a reset link of an inactive account")
    admin = await _add_user(engine, ADMIN)
    dora = await _add_user(engine, "zq_dora", active=False)
    issued = await _issue(engine, PASSWORD_RESET, user_id=dora.id, created_by_user_id=admin.id)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        async with AsyncSession(engine) as session:
            with pytest.raises(EmailError) as raised:
                await flows.send_link_email(session, admin=admin, purpose="password_reset", token=issued.token)

    assert (type(raised.value), raised.value.code) == (flows.EmailAccountInactiveError, "EMAIL_ACCOUNT_INACTIVE"), repr(raised.value)
    assert (fake.connections, budget.count()) == (0, 0)
    assert (await _inspect(engine, issued.token, PASSWORD_RESET)).status == TokenStatus.VALID
    print_success("EMAIL_ACCOUNT_INACTIVE, nothing sent, the link live")


@pytest.mark.asyncio
async def test_a_database_error_is_logged_as_its_type_without_the_identifier(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine) -> None:
    """EMF-042 — contract 12: the account lookup fails with a database error whose statement parameters hold the identifier, as SQLAlchemy's errors do (the precondition: its text names it). The work returns, raises nothing, and logs ``Forgotten password: the request failed`` at error level with the error's type alone — no traceback (``exc_info``), whose rendering would print the parameters —; no log event holds the identifier."""
    print_section("EMF-042: a database error in the work")
    identifier = f"{ALICE}@example.com"
    error = OperationalError("SELECT users.id FROM users WHERE users.username = ? OR users.email = ?", (identifier, identifier), Exception("database is locked"))
    assert identifier in str(error), "precondition: the error's text holds the identifier"

    async def failing_lookup(session: AsyncSession, written: str) -> User:
        raise error

    monkeypatch.setattr(user_service, "get_user_by_username_or_email", failing_lookup)
    with capture_logs() as events:
        returned = await flows.forgotten_password_work(identifier, engine=engine)

    assert returned is None
    failures = [event for event in events if event.get("log_level") in ("warning", "error")]
    assert [(event.get("event"), event.get("log_level"), event.get("error")) for event in failures] == [("Forgotten password: the request failed", "error", "OperationalError")], failures
    assert "exc_info" not in failures[0], f"no traceback: {failures[0]}"
    assert [event for event in events if identifier in repr(event)] == [], f"a log event holds the identifier: {events}"
    print_success("logged as OperationalError, no traceback, no identifier")


# =============================================================================
# 15. THE NOTICE OF AN EMAIL CHANGE (lot E4a)
# =============================================================================

#: The address an account changes to: a local part of its own, never shown, never a recipient.
NEW_ADDRESS = "zq.new-alice.secret@example.org"
NEW_LOCAL_PART = "zq.new-alice.secret"
#: Its domain, a host name its new owner chose: since decision N62 the notice shows no part of the new address.
NEW_DOMAIN = "example.org"
#: An old address that is not one address.
NOT_ONE_ADDRESS = "zq_alice@example.com, zq-other@example.com"
#: An address and the same letters with ``á`` in another case, in NFC (one code point each): beyond A–Z
#: ``user_service.same_email`` compares a letter as written, so they are two addresses (EMF-059).
ACCENTED_OLD = "zq_\u00e1lice@example.com"
ACCENTED_NEW = "zq_\u00c1lice@example.com"


def _notices(events: list[dict[str, object]]) -> list[dict[str, object]]:
    """The log events of the notice."""
    return [event for event in events if str(event.get("event", "")).startswith("Email change notice")]


def _lookups(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Records every account the work looks up — none means no session was put to work."""
    lookups: list[int] = []
    lookup = user_service.get_user_by_id

    async def recording(session: AsyncSession, user_id: int) -> User | None:
        lookups.append(user_id)
        return await lookup(session, user_id)

    monkeypatch.setattr(user_service, "get_user_by_id", recording)
    return lookups


def test_email_changed_work_has_its_signature_and_its_fallback_name() -> None:
    """EMF-043 — contract 14: a coroutine function ``email_changed_work(user_id, old_address, new_address, *, engine=None)``; the instance's name without a usable public address is «LibreFolio»."""
    print_section("EMF-043: signature")
    parameters = inspect.signature(flows.email_changed_work).parameters

    assert inspect.iscoroutinefunction(flows.email_changed_work)
    assert [(parameter.name, parameter.kind) for parameter in parameters.values()] == [("user_id", POSITIONAL), ("old_address", POSITIONAL), ("new_address", POSITIONAL), ("engine", KEYWORD_ONLY)]
    assert parameters["engine"].default is None
    assert flows.INSTANCE_FALLBACK == "LibreFolio"
    print_success("email_changed_work(user_id, old_address, new_address, *, engine=None); «LibreFolio»")


@pytest.mark.asyncio
@pytest.mark.parametrize(("own", "default", "language"), [pytest.param("it", "fr", "it", id="its-own-language"), pytest.param(None, "fr", "fr", id="the-instances-language"), pytest.param(None, "en", "en", id="english")])
async def test_the_notice_goes_to_the_old_address_only_in_the_accounts_language(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, own: str | None, default: str, language: str) -> None:
    """EMF-044 — contract 14: one message, to the old address only — the new one neither a recipient nor in a header —, from the configured sender, exactly what ``build_email_changed`` writes in the account's language with the public host as the instance: no part of the new address — neither its local part nor its domain — and no username in its text or its HTML (decision N62); one unit spent; returns None and logs the notice sent by the account's id and the language."""
    print_section(f"EMF-044: the notice in {language}")
    alice = await _add_user(engine, ALICE)
    await _set_default_language(engine, default)
    if own is not None:
        await _set_account_language(engine, alice.id, own)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with capture_logs() as events:
            returned = await flows.email_changed_work(alice.id, alice.email, NEW_ADDRESS, engine=engine)

    assert returned is None
    assert len(fake.messages) == 1
    received = fake.messages[0]
    assert received.rcpt_tos == [alice.email]
    assert (_mailboxes(received.message["To"]), _mailboxes(received.message["From"])) == ([("", alice.email)], [SENDER])
    assert (received.message["Cc"], received.message["Bcc"]) == (None, None)
    shown = [part for part in (NEW_LOCAL_PART, NEW_DOMAIN, ALICE) if part in _text(received) + _html(received)]
    assert shown == [], f"the notice shows {shown}: no part of the new address and no username, text whoever holds the account chose (N62)"
    _assert_is(received, build_email_changed(language=language, instance=PUBLIC_HOST))
    assert budget.count() == 1
    assert [(event.get("event"), event.get("log_level"), event.get("user_id"), event.get("language")) for event in _notices(events)] == [("Email change notice sent to the previous address", "info", alice.id, language)]
    print_success(f"to the old address only, in {language}")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("public_url", "instance"),
    [
        pytest.param(PUBLIC_URL, PUBLIC_HOST, id="the-public-host-when-links-are-ready"),
        pytest.param(None, "LibreFolio", id="librefolio-without-a-public-url"),
        pytest.param(NO_LINK_FROM_IT, "LibreFolio", id="librefolio-with-a-public-url-no-link-starts-from"),
    ],
)
async def test_the_instance_is_the_public_host_or_librefolio(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, public_url: str | None, instance: str) -> None:
    """EMF-045 — contract 14: the notice carries no link, so it goes without ``LIBREFOLIO_PUBLIC_URL`` too; the instance it names is the host of that address when links are ready, else «LibreFolio» — the work takes no request, so no request's host can reach it."""
    print_section(f"EMF-045: instance {instance}")
    alice = await _add_user(engine, ALICE)

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake)
        if public_url is not None:
            monkeypatch.setenv(PUBLIC_URL_VARIABLE, public_url)
        await flows.email_changed_work(alice.id, alice.email, NEW_ADDRESS, engine=engine)

    assert len(fake.messages) == 1
    _assert_is(fake.messages[0], build_email_changed(language="en", instance=instance))
    print_success(f"named {instance}")


@pytest.mark.asyncio
@pytest.mark.parametrize("new", [pytest.param("zq_alice@example.com", id="the-same-address"), pytest.param("ZQ_Alice@Example.COM", id="the-same-address-in-other-capitals")])
async def test_nothing_when_the_address_did_not_change(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, new: str) -> None:
    """EMF-046 — contract 14: the same address by ``user_service.same_email`` (decision P18), as written or with A–Z in other capitals: nothing is sent, no account is looked up, nothing is spent, nothing is logged. No case with spaces around: both addresses come from the database, where ``EmailStr`` stripped them, and ``same_email`` strips nothing (A's contract), so a space would make another address. The boundary, a letter beyond A–Z in another case, is EMF-059."""
    print_section(f"EMF-046: {new!r}")
    alice = await _add_user(engine, ALICE)
    lookups = _lookups(monkeypatch)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with capture_logs() as events:
            returned = await flows.email_changed_work(alice.id, alice.email, new, engine=engine)

    assert returned is None
    assert (fake.connections, budget.count(), lookups) == (0, 0, [])
    assert _notices(events) == []
    print_success("nothing")


@pytest.mark.asyncio
async def test_another_case_beyond_a_to_z_is_another_address_and_the_notice_goes(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter) -> None:
    """EMF-059 — contract 14, the boundary of EMF-046: Alice's address ``zq_álice@example.com`` changes to ``zq_Álice@example.com``, apart in the case of ``á`` alone, a letter beyond A–Z, which ``user_service.same_email`` compares as written (decision P18's documented limit): two addresses. The notice goes as for any change: the account looked up, one message, to the old address exactly as written (the envelope's recipient: the fake server takes an address beyond ASCII with ``SMTPUTF8``), one unit spent, the notice sent logged with her id."""
    print_section("EMF-059: another case beyond A–Z")
    assert ACCENTED_OLD.casefold() == ACCENTED_NEW.casefold() and not user_service.same_email(ACCENTED_OLD, ACCENTED_NEW), "precondition: one mailbox for casefold, two addresses for P18's rule"
    alice = await _add_user(engine, ALICE, email=ACCENTED_OLD)
    lookups = _lookups(monkeypatch)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with capture_logs() as events:
            returned = await flows.email_changed_work(alice.id, alice.email, ACCENTED_NEW, engine=engine)

    assert returned is None
    assert [message.rcpt_tos for message in fake.messages] == [[ACCENTED_OLD]], "one message, to the old address exactly as written"
    assert (lookups, budget.count()) == ([alice.id], 1)
    assert [(event.get("event"), event.get("log_level"), event.get("user_id")) for event in _notices(events)] == [("Email change notice sent to the previous address", "info", alice.id)]
    print_success("two addresses: the notice to the old one, as written")


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["off", "off-with-links-ready", "off-and-blocked"])
async def test_email_off_is_an_info_line_before_any_session(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, case: str) -> None:
    """EMF-047 — contract 14: email off — not configured, the default of a self-hosted instance —, with or without a public address, blocked or not: one ``info`` line «email is off, nothing sent» with the account's id, no warning nor error at all; decided before any session is put to work (no account looked up); nothing sent or spent."""
    print_section(f"EMF-047: {case}")
    alice = await _add_user(engine, ALICE)
    lookups = _lookups(monkeypatch)
    if case != "off":
        monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)
    if case == "off-and-blocked":
        monkeypatch.setenv(BLOCKED_VARIABLE, "1")

    with capture_logs() as events:
        returned = await flows.email_changed_work(alice.id, alice.email, NEW_ADDRESS, engine=engine)

    assert returned is None
    assert (lookups, budget.count()) == ([], 0)
    assert [(event.get("event"), event.get("log_level"), event.get("user_id")) for event in _notices(events)] == [("Email change notice: email is off, nothing sent", "info", alice.id)]
    assert [event for event in events if event.get("log_level") in ("warning", "error")] == [], events
    print_success("info: email is off")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case", "reason", "code"),
    [
        pytest.param("email-unusable", "EmailUnavailableError", "SMTP_TLS_INVALID", id="email-set-but-unusable"),
        pytest.param("blocked", "EmailUnavailableError", "INSTANCE_BLOCKED", id="blocked"),
        pytest.param("block-unreadable", "EmailUnavailableError", "INSTANCE_BLOCKED", id="block-unreadable"),
        pytest.param("budget-spent", "EmailRateLimitedError", "EMAIL_RATE_LIMITED", id="budget-spent"),
        pytest.param("smtp-refuses", "EmailDeliveryError", "RECIPIENT_REFUSED", id="the-server-refuses-the-old-address"),
        pytest.param("not-one-address", "EmailRecipientError", None, id="an-old-address-that-is-not-one-address"),
    ],
)
async def test_a_notice_that_cannot_go_is_a_warning_never_raised(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter, clock: FakeClock, case: str, reason: str, code: str | None) -> None:
    """EMF-048 — contract 14: email set but unusable, the instance blocked (blocking or unreadable), the hourly budget spent, the server refusing the old address, an old address that is not one address: nothing delivered, nothing raised, and one warning «not sent» with the reason's type and code."""
    print_section(f"EMF-048: {case}")
    alice = await _add_user(engine, ALICE)
    old = NOT_ONE_ADDRESS if case == "not-one-address" else alice.email

    with FakeSmtpServer(refuse_recipients={alice.email} if case == "smtp-refuses" else ()) as fake:
        _ready(monkeypatch, fake, **({"max_per_hour": "1"} if case == "budget-spent" else {"tls": "ssl"} if case == "email-unusable" else {}))
        if case in ("blocked", "block-unreadable"):
            monkeypatch.setenv(BLOCKED_VARIABLE, "1" if case == "blocked" else "maybe")
        if case == "budget-spent":
            clock.now = START
            assert budget.hit(limit=1).allowed, "setup: the only unit of the hour"
            clock.now = START + 60
        with capture_logs() as events:
            returned = await flows.email_changed_work(alice.id, old, NEW_ADDRESS, engine=engine)

    assert returned is None
    assert fake.messages == []
    assert [(event.get("event"), event.get("log_level"), event.get("reason"), event.get("code")) for event in _notices(events)] == [("Email change notice: not sent", "warning", reason, code)]
    print_success(f"warning: {reason} {code}")


@pytest.mark.asyncio
async def test_an_account_gone_is_an_info_line(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, budget: SlidingWindowLimiter) -> None:
    """EMF-049 — contract 14: the account no longer exists: one ``info`` line naming its id, no warning; nothing sent or spent."""
    print_section("EMF-049: the account is gone")
    gone = 4_242

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with capture_logs() as events:
            returned = await flows.email_changed_work(gone, "zq_gone@example.com", NEW_ADDRESS, engine=engine)

    assert returned is None
    assert (fake.connections, budget.count()) == (0, 0)
    assert [(event.get("event"), event.get("log_level"), event.get("user_id")) for event in _notices(events)] == [("Email change notice: the account no longer exists, nothing sent", "info", gone)]
    print_success("info: no such account")


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["the-builder-raises", "a-database-error-holding-both-addresses"])
async def test_any_other_error_is_logged_as_its_type_alone(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, failure: str) -> None:
    """EMF-050 — contract 14: an unexpected error — while the email is built, or a database error whose statement parameters hold both addresses (the precondition: its text does) —: nothing raised, nothing sent, and one error «the request failed» with the error's type alone, without a traceback; no log event holds either address."""
    print_section(f"EMF-050: {failure}")
    alice = await _add_user(engine, ALICE)
    error = OperationalError("UPDATE users SET email = ? WHERE users.email = ?", (NEW_ADDRESS, alice.email), Exception("database is locked"))
    assert NEW_ADDRESS in str(error) and alice.email in str(error), "precondition: the error's text holds both addresses"

    def failing_builder(**arguments: object) -> object:
        raise RuntimeError("zq-builder failure")

    async def failing_lookup(session: AsyncSession, user_id: int) -> User:
        raise error

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        if failure == "the-builder-raises":
            monkeypatch.setattr(flows, "build_email_changed", failing_builder)
        else:
            monkeypatch.setattr(user_service, "get_user_by_id", failing_lookup)
        with capture_logs() as events:
            returned = await flows.email_changed_work(alice.id, alice.email, NEW_ADDRESS, engine=engine)

    assert returned is None
    assert fake.messages == []
    expected_type = "RuntimeError" if failure == "the-builder-raises" else "OperationalError"
    failures = [event for event in events if event.get("log_level") in ("warning", "error")]
    assert [(event.get("event"), event.get("log_level"), event.get("error")) for event in failures] == [("Email change notice: the request failed", "error", expected_type)], failures
    assert "exc_info" not in failures[0], f"no traceback: {failures[0]}"
    assert [event for event in events if NEW_ADDRESS in repr(event) or alice.email in repr(event)] == []
    print_success(f"logged as {expected_type}, no traceback, no address")


@pytest.mark.asyncio
async def test_no_log_event_of_the_notice_holds_an_address(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine) -> None:
    """EMF-051 — contract 14: through a notice sent, the same address, email off, email unusable, an account gone, a refused address and an old address that is not one address, the work logs (the barrier), and no event holds the old address, the new one or its local part."""
    print_section("EMF-051: no address in the logs")
    alice = await _add_user(engine, ALICE)

    with capture_logs() as events:
        await flows.email_changed_work(alice.id, alice.email, NEW_ADDRESS, engine=engine)
        with FakeSmtpServer(refuse_recipients={"zq_refused@example.com"}) as fake:
            _ready(monkeypatch, fake)
            await flows.email_changed_work(alice.id, alice.email, NEW_ADDRESS, engine=engine)
            await flows.email_changed_work(alice.id, alice.email, alice.email.upper(), engine=engine)
            await flows.email_changed_work(4_242, "zq_gone@example.com", NEW_ADDRESS, engine=engine)
            await flows.email_changed_work(alice.id, "zq_refused@example.com", NEW_ADDRESS, engine=engine)
            await flows.email_changed_work(alice.id, NOT_ONE_ADDRESS, NEW_ADDRESS, engine=engine)
            _configure(monkeypatch, {"tls": "ssl"})
            await flows.email_changed_work(alice.id, alice.email, NEW_ADDRESS, engine=engine)

    assert len(fake.messages) == 1 and len(_notices(events)) == 6, f"barrier: the work logged: {_notices(events)}"
    secrets = (alice.email, NEW_ADDRESS, NEW_LOCAL_PART, "zq_gone@example.com", "zq_refused@example.com", "zq-other@example.com")
    assert [event for event in events if any(secret in repr(event) for secret in secrets)] == [], events
    print_success(f"{len(events)} events, no address")


@pytest.mark.asyncio
async def test_the_notice_reads_the_configuration_off_the_event_loop(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine) -> None:
    """EMF-052 — contract 14: every read of the email configuration — whether email is off, then the configuration the email needs — runs in a worker thread, never on the event loop."""
    print_section("EMF-052: off the event loop")
    alice = await _add_user(engine, ALICE)
    read = delivery.email_config_state
    on_the_loop: list[bool] = []

    def recording() -> object:
        on_the_loop.append(_loop_running())
        return read()

    monkeypatch.setattr(delivery, "email_config_state", recording)
    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        await flows.email_changed_work(alice.id, alice.email, NEW_ADDRESS, engine=engine)

    assert len(fake.messages) == 1
    assert on_the_loop and not any(on_the_loop), f"read on the event loop: {on_the_loop}"
    print_success(f"{len(on_the_loop)} reads, all in a worker thread")


# =============================================================================
# 16. «FORGOT PASSWORD» SHIPS OPEN (lot E4b)
# =============================================================================


@pytest.mark.asyncio
async def test_forgot_password_ships_open(monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, forgot_limits: ForgotLimits) -> None:
    """EMF-053 — contract 11: «forgot password» ships open (lot E4). ``flows`` carries no hold any more — no ``FORGOT_PASSWORD_HELD``, no ``ForgottenPasswordHeldError`` — and nothing in this module lifts one: with email and links ready, the first request of an address for an identifier is admitted, counted once under each, the hourly budget peeked, not spent. Where the hold used to answer first (EMF-035, removed with it) the configuration now answers, as EMF-020 (email off, links missing or invalid), EMF-034 (a blocked instance) and EMF-023 (the budget spent) pin."""
    print_section("EMF-053: «forgot password» ships open")
    leftovers = [name for name in ("FORGOT_PASSWORD_HELD", "ForgottenPasswordHeldError") if hasattr(flows, name)]
    _usable_without_a_server(monkeypatch)

    await flows.admit_forgotten_password(ADDRESS, ALICE)

    assert leftovers == [], f"«forgot password» ships open since lot E4: flows still carries {leftovers}"
    assert (forgot_limits.by_address.count(ADDRESS), forgot_limits.by_identifier.count(ALICE), budget.count()) == (1, 1, 0)
    print_success("admitted as shipped: counted once per address and per identifier, the budget peeked")


# =============================================================================
# 17. THE LIMITS OF THE NOTICE (lot E4b)
# =============================================================================

#: The two lines of the notice this section reads: it went, or it was past its limits.
NOTICE_SENT = "Email change notice sent to the previous address"
PAST_ITS_LIMITS = "Email change notice: past its limits, nothing sent"
#: One old mailbox written four ways, each the address an account of its own leaves (EMF-056): every one deliverable, so
#: a limiter that told them apart would let the fourth through. Letter case aside, the limiter keys them all as OLD_MAILBOX.
OLD_MAILBOX_VARIANTS = ("Zq-Old@Example.com", "zq-old@example.com", "ZQ-OLD@EXAMPLE.COM", "zQ-oLd@eXaMpLe.CoM")
OLD_MAILBOX = "zq-old@example.com"


def _composed(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Records the language of every notice the work composes — none means nothing was written."""
    composed: list[str] = []
    build = flows.build_email_changed

    def recording(**arguments: object) -> object:
        composed.append(str(arguments["language"]))
        return build(**arguments)

    monkeypatch.setattr(flows, "build_email_changed", recording)
    return composed


def _notice_lines(events: list[dict[str, object]]) -> list[tuple[object, object, object]]:
    """``(event, level, user_id)`` of each line of the notice among ``events``."""
    return [(event.get("event"), event.get("log_level"), event.get("user_id")) for event in _notices(events)]


def test_the_notices_shipped_limits() -> None:
    """EMF-054 — contract 15: the module ships ``EMAIL_CHANGE_NOTICES_BY_ACCOUNT`` and ``EMAIL_CHANGE_NOTICES_BY_MAILBOX``, two ``SlidingWindowLimiter`` of 3 per 3600 s each."""
    print_section("EMF-054: the notice's shipped limits")

    assert isinstance(SHIPPED_NOTICES_BY_ACCOUNT, SlidingWindowLimiter) and (SHIPPED_NOTICES_BY_ACCOUNT.limit, SHIPPED_NOTICES_BY_ACCOUNT.window_seconds) == (3, 3600)
    assert isinstance(SHIPPED_NOTICES_BY_MAILBOX, SlidingWindowLimiter) and (SHIPPED_NOTICES_BY_MAILBOX.limit, SHIPPED_NOTICES_BY_MAILBOX.window_seconds) == (3, 3600)
    assert SHIPPED_NOTICES_BY_ACCOUNT is not SHIPPED_NOTICES_BY_MAILBOX, "two limiters: one per account, one per mailbox"
    print_success("3/h per account, 3/h per old mailbox")


@pytest.mark.asyncio
async def test_three_notices_an_hour_per_account_the_fourth_skipped(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, clock: FakeClock, budget: SlidingWindowLimiter, notice_limits: NoticeLimits) -> None:
    """EMF-055 — contract 15: Alice changes her email four times, a minute apart, each time from the address the change before gave her, so no mailbox counts twice. The first three notices go, each to the address its change left, each counted once under her account and once under that mailbox. The fourth is skipped: one ``info`` line «past its limits, nothing sent» with her id, no warning, neither of its addresses; nothing composed, no SMTP conversation, no budget unit, nothing counted for it under either limiter."""
    print_section("EMF-055: three notices an hour per account")
    alice = await _add_user(engine, ALICE)
    moves = (alice.email, *(f"zq-alice-{index}@example.org" for index in range(1, 5)))
    composed = _composed(monkeypatch)
    logged: list[list[dict[str, object]]] = []

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        for index in range(4):
            clock.now = START + 60 * index
            with capture_logs() as events:
                await flows.email_changed_work(alice.id, moves[index], moves[index + 1], engine=engine)
            logged.append(events)

    assert [_notice_lines(events) for events in logged] == [[(NOTICE_SENT, "info", alice.id)]] * 3 + [[(PAST_ITS_LIMITS, "info", alice.id)]]
    assert [event for event in logged[3] if event.get("log_level") in ("warning", "error")] == [], logged[3]
    assert [event for event in logged[3] if moves[3] in repr(event) or moves[4] in repr(event)] == [], "the skipped notice's line holds neither address"
    assert [message.rcpt_tos for message in fake.messages] == [[old] for old in moves[:3]], "three notices, each to the address its change left"
    assert (len(composed), fake.connections, budget.count()) == (3, 3, 3), "the fourth: nothing composed, no SMTP conversation, no budget unit"
    assert notice_limits.by_account.count(alice.id) == 3
    assert [notice_limits.by_mailbox.count(old) for old in moves[:4]] == [1, 1, 1, 0], "each mailbox left once; the fourth's counted for nothing"
    print_success("three notices; the fourth skipped with an info line, nothing sent or spent")


@pytest.mark.asyncio
async def test_three_notices_an_hour_per_old_mailbox_whatever_the_account_and_the_case(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, clock: FakeClock, budget: SlidingWindowLimiter, notice_limits: NoticeLimits) -> None:
    """EMF-056 — contract 15: four accounts, a minute apart, each leave one mailbox written its own way — ``Zq-Old@Example.com``, ``zq-old@example.com``, ``ZQ-OLD@EXAMPLE.COM``, then ``zQ-oLd@eXaMpLe.CoM``, every one deliverable —. The first three notices go, each to the address as written, and the mailbox counts three; the fourth account's notice, its first, is skipped: one ``info`` line «past its limits, nothing sent» with its id, no warning, neither of its addresses in any spelling; no SMTP conversation, no budget unit, nothing counted for it under either limiter."""
    print_section("EMF-056: three notices an hour per old mailbox")
    assert {written.casefold() for written in OLD_MAILBOX_VARIANTS} == {OLD_MAILBOX}, "precondition: four spellings of one mailbox"
    accounts = [await _add_user(engine, f"zq_owner_{index}", email=f"zq-moved-{index}@example.org") for index in range(4)]
    logged: list[list[dict[str, object]]] = []

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        for index, (account, old) in enumerate(zip(accounts, OLD_MAILBOX_VARIANTS, strict=True)):
            clock.now = START + 60 * index
            with capture_logs() as events:
                await flows.email_changed_work(account.id, old, account.email, engine=engine)
            logged.append(events)

    assert [_notice_lines(events) for events in logged] == [[(NOTICE_SENT, "info", account.id)] for account in accounts[:3]] + [[(PAST_ITS_LIMITS, "info", accounts[3].id)]]
    assert [event for event in logged[3] if event.get("log_level") in ("warning", "error")] == [], logged[3]
    assert [event for event in logged[3] if OLD_MAILBOX in repr(event).casefold() or accounts[3].email in repr(event)] == [], "the skipped notice's line holds neither address"
    assert [message.rcpt_tos for message in fake.messages] == [[old] for old in OLD_MAILBOX_VARIANTS[:3]], "three notices, each to the address as written"
    assert (fake.connections, budget.count()) == (3, 3), "the fourth: no SMTP conversation, no budget unit"
    assert notice_limits.by_mailbox.count(OLD_MAILBOX) == 3
    assert [notice_limits.by_account.count(account.id) for account in accounts] == [1, 1, 1, 0], "the fourth account counted for nothing"
    print_success("one mailbox in four spellings: three notices, the fourth skipped")


@pytest.mark.asyncio
async def test_a_notice_the_server_refused_counts_for_neither_limit(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, clock: FakeClock, notice_limits: NoticeLimits) -> None:
    """EMF-057 — contract 15: three notices of Alice's to her old address, a minute apart, meet an SMTP server that refuses it — each a warning «not sent», ``EmailDeliveryError`` ``RECIPIENT_REFUSED`` —: counted under neither her account nor that mailbox. So the fourth, to the same address with a server that takes it, goes: one message, counted once under each. A notice that did not go is not one."""
    print_section("EMF-057: a refused notice counts for neither limit")
    alice = await _add_user(engine, ALICE)

    with FakeSmtpServer(refuse_recipients={alice.email}) as refusing:
        _ready(monkeypatch, refusing)
        with capture_logs() as events:
            for index in range(3):
                clock.now = START + 60 * index
                await flows.email_changed_work(alice.id, alice.email, NEW_ADDRESS, engine=engine)
    counted_after_the_refusals = (notice_limits.by_account.count(alice.id), notice_limits.by_mailbox.count(alice.email))
    clock.now = START + 180
    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        await flows.email_changed_work(alice.id, alice.email, NEW_ADDRESS, engine=engine)

    refused = [(event.get("event"), event.get("log_level"), event.get("reason"), event.get("code")) for event in _notices(events)]
    assert refused == [("Email change notice: not sent", "warning", "EmailDeliveryError", "RECIPIENT_REFUSED")] * 3, f"barrier: three attempts, three refusals: {refused}"
    assert refusing.messages == []
    assert counted_after_the_refusals == (0, 0)
    assert [message.rcpt_tos for message in fake.messages] == [[alice.email]]
    assert (notice_limits.by_account.count(alice.id), notice_limits.by_mailbox.count(alice.email)) == (1, 1)
    print_success("three refusals counted nothing; the fourth went")


@pytest.mark.asyncio
async def test_an_hour_after_the_first_of_three_notices_the_next_goes(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, clock: FakeClock, notice_limits: NoticeLimits) -> None:
    """EMF-058 — contract 15: three notices of Alice's to one old address, at 0, 60 and 120 s, fill both limits. At 3599 s the next is still skipped, «past its limits»; at 3600 s the first has left the window — a sliding hour — and the notice goes, counted under both."""
    print_section("EMF-058: an hour later, notices go again")
    alice = await _add_user(engine, ALICE)
    logged: list[list[object]] = []

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        for offset in (0, 60, 120, 3599, 3600):
            clock.now = START + offset
            with capture_logs() as events:
                await flows.email_changed_work(alice.id, alice.email, NEW_ADDRESS, engine=engine)
            logged.append([event.get("event") for event in _notices(events)])

    assert logged == [[NOTICE_SENT]] * 3 + [[PAST_ITS_LIMITS], [NOTICE_SENT]]
    assert [message.rcpt_tos for message in fake.messages] == [[alice.email]] * 4
    assert (notice_limits.by_account.count(alice.id), notice_limits.by_mailbox.count(alice.email)) == (3, 3), "the notices of 60, 120 and 3600 s"
    print_success("skipped at 3599 s, sent again at 3600 s")


# =============================================================================
# 18. ALIASES OF ONE MAILBOX SHARE ITS BUDGET (E-9 a)
# =============================================================================

#: One Gmail mailbox written four ways, each the stored address of an active account of its own: a ``+tag``, the dots of
#: the local part and ``googlemail.com`` all deliver to it. ``delivery.mailbox_budget_key`` folds the four into
#: GMAIL_ALIAS_KEY; ``strip().casefold()`` keeps them apart, a budget each.
GMAIL_ALIASES = ("zqvictim+1@gmail.com", "zq.victim+2@gmail.com", "zqvictim+3@googlemail.com", "zq.vic.tim@gmail.com")
GMAIL_ALIAS_KEY = "zqvictim@gmail.com"
#: The addresses four accounts leave (EMF-061): aliases of one Gmail mailbox, one in letters of its own; one key.
OLD_ALIASES = ("Zq.Old+1@GMail.com", "zqold+2@googlemail.com", "z.q.o.l.d@gmail.com", "zqold+notice@gmail.com")
OLD_ALIAS_KEY = "zqold@gmail.com"
#: Two mailboxes outside Gmail, apart in a dot alone: there a dot is part of the address (EMF-062).
DOTTED = "zq.a@outlook.com"
UNDOTTED = "zqa@outlook.com"
#: The work's line when the recipient's mailbox had its reset emails of the hour.
MAILBOX_SPENT = "Forgotten password: the mailbox had reset emails moments ago, nothing sent"


def _forgot_lines(events: list[dict[str, object]]) -> list[tuple[object, object, object]]:
    """``(event, level, user_id)`` of each line of «forgot password»'s work among ``events``."""
    return [(event.get("event"), event.get("log_level"), event.get("user_id")) for event in events if str(event.get("event", "")).startswith("Forgotten password")]


@pytest.mark.asyncio
async def test_aliases_of_one_mailbox_share_its_reset_emails(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, clock: FakeClock, forgot_limits: ForgotLimits) -> None:
    """EMF-060 — contract 16: four active accounts whose stored addresses are aliases of one Gmail mailbox — ``zqvictim+1@gmail.com``, ``zq.victim+2@gmail.com``, ``zqvictim+3@googlemail.com``, ``zq.vic.tim@gmail.com`` — ask once each, by username, well within their own limits (the work alone runs: the admission's limits per client and per identifier are not on its path); the limiters' clock stands still. The first three get their reset email, each at its account's stored address exactly — tag, dots and domain as written: the key is never a recipient —; the fourth gets nothing: one ``info`` line «the mailbox had reset emails moments ago, nothing sent» with its account's id, and no reset row. The mailbox counted three times, under its folded key."""
    print_section("EMF-060: four aliases of one mailbox, three reset emails")
    assert len({address.casefold() for address in GMAIL_ALIASES}) == len(GMAIL_ALIASES), "precondition: letter case alone keeps the four apart: only folding the aliases makes them one mailbox"
    moment = utcnow()
    accounts = [await _add_user(engine, f"zq_alias_{index}", email=address) for index, address in enumerate(GMAIL_ALIASES)]
    logged: list[list[dict[str, object]]] = []

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        clock.now = START
        for account in accounts:
            with capture_logs() as events:
                await flows.forgotten_password_work(account.username, engine=engine, now=moment)
            logged.append(events)

    assert [message.rcpt_tos for message in fake.messages] == [[address] for address in GMAIL_ALIASES[:3]], "the 4th alias of one mailbox got its own budget: three reset emails an hour per mailbox, however its address is written"
    assert _forgot_lines(logged[3]) == [(MAILBOX_SPENT, "info", accounts[3].id)], logged[3]
    assert await _reset_rows(engine, accounts[3].id) == [], "past the mailbox's limit nothing may be made"
    assert forgot_limits.by_mailbox.count(GMAIL_ALIAS_KEY) == 3, "the three emails counted under the mailbox's folded key"
    print_success("three reset emails to one mailbox under three aliases; the fourth held")


@pytest.mark.asyncio
async def test_aliases_of_one_old_mailbox_share_its_notices(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, clock: FakeClock, notice_limits: NoticeLimits) -> None:
    """EMF-061 — contract 16: four accounts change their email once each, the limiters' clock standing still; the addresses they leave are aliases of one Gmail mailbox — ``Zq.Old+1@GMail.com``, ``zqold+2@googlemail.com``, ``z.q.o.l.d@gmail.com``, ``zqold+notice@gmail.com`` —, so no account comes near its own limit. The first three notices go, each to the address its change left, exactly as written; the fourth is skipped: one ``info`` line «past its limits, nothing sent» with its account's id, nothing counted for it. The old mailbox counted three times, under its folded key."""
    print_section("EMF-061: four aliases of one old mailbox, three notices")
    assert len({address.casefold() for address in OLD_ALIASES}) == len(OLD_ALIASES), "precondition: letter case alone keeps the four apart: only folding the aliases makes them one mailbox"
    accounts = [await _add_user(engine, f"zq_leaver_{index}", email=f"zq-moved-{index}@example.org") for index in range(len(OLD_ALIASES))]
    logged: list[list[dict[str, object]]] = []

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        clock.now = START
        for account, old in zip(accounts, OLD_ALIASES, strict=True):
            with capture_logs() as events:
                await flows.email_changed_work(account.id, old, account.email, engine=engine)
            logged.append(events)

    assert [message.rcpt_tos for message in fake.messages] == [[old] for old in OLD_ALIASES[:3]], "the 4th alias of one mailbox got its own budget: three notices an hour per old mailbox, however its address is written"
    assert _notice_lines(logged[3]) == [(PAST_ITS_LIMITS, "info", accounts[3].id)], logged[3]
    assert notice_limits.by_mailbox.count(OLD_ALIAS_KEY) == 3, "the three notices counted under the old mailbox's folded key"
    assert [notice_limits.by_account.count(account.id) for account in accounts] == [1, 1, 1, 0], "no account near its own limit; the fourth counted for nothing"
    print_success("three notices to one old mailbox under three aliases; the fourth skipped")


@pytest.mark.asyncio
async def test_two_mailboxes_apart_in_a_dot_outside_gmail_keep_two_budgets(monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, clock: FakeClock, forgot_limits: ForgotLimits) -> None:
    """EMF-062 — contract 16, the guard of EMF-060: outside Gmail a dot is part of the mailbox. The account at ``zq.a@outlook.com`` gets three reset emails, five minutes apart — within its own limits —, the limiters' clock standing still: that mailbox is spent. A request for the account at ``zqa@outlook.com`` still gets its email, at that address: another mailbox, another budget. Green before E-9 and after it."""
    print_section("EMF-062: zq.a@ and zqa@outlook.com, two budgets")
    moment = utcnow()
    dotted = await _add_user(engine, "zq_dotted", email=DOTTED)
    undotted = await _add_user(engine, "zq_undotted", email=UNDOTTED)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        clock.now = START
        for minutes in (0, 5, 10):
            await flows.forgotten_password_work(dotted.username, engine=engine, now=moment + timedelta(minutes=minutes))
        spent = not forgot_limits.by_mailbox.peek(DOTTED).allowed
        await flows.forgotten_password_work(undotted.username, engine=engine, now=moment + timedelta(minutes=10))

    assert spent, "barrier: zq.a@outlook.com had its three reset emails of the hour"
    assert [message.rcpt_tos for message in fake.messages] == [[DOTTED]] * 3 + [[UNDOTTED]], "zqa@outlook.com is another mailbox than zq.a@outlook.com: its reset email must go"
    assert (forgot_limits.by_mailbox.count(DOTTED), forgot_limits.by_mailbox.count(UNDOTTED)) == (3, 1)
    print_success("three reset emails to zq.a@outlook.com, then one to zqa@outlook.com")
