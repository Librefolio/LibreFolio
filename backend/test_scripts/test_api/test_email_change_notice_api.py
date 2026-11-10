"""The emails of an email change, scheduled by ``PUT /auth/profile`` (lot E4b, on workstream A's A6e; two since UA2), over HTTP, in-process.

A6e made an email change ask for the current password, end every other session of the account and give this one a new
session cookie. E4a wrote the notice, ``flows.email_changed_work`` (its own rules are EMF-043…052 and EMF-059, its limits
EMF-054…058, in ``test_services/test_email_flows.py``); E4b schedules it from A's route. Since decision P18 (lot E4c on
E's side), A's route and the notice tell two addresses apart with one rule, ``user_service.same_email``: A–Z in any
case, every other character as written, nothing stripped. Since UA2 the work writes to both addresses once the change is
complete: the notice to the old one, then the confirmation to the new one. This module pins the hook. The contract:

1. An email change accepted — the right current password, email ready —: the answer is A's, 200 ``{user: {email: <the
   new address>}, message: "Profile updated successfully"}`` with a new ``session`` cookie that signs in as the new
   address; after it, exactly two emails, the old address first, each to its address only (envelope and ``To``, no
   ``Cc``/``Bcc``), in the account's language — its own, else the instance's — with «LibreFolio» as the instance (no
   ``LIBREFOLIO_PUBLIC_URL``: neither carries a link), both greeting nobody by name. To the old address exactly what
   ``build_email_changed`` writes, carrying no part of the new address — neither its local part nor its domain, in its
   text, its HTML or a header (decision N62) —; to the new address exactly what ``build_email_changed_new_address``
   writes, carrying no part of the old address and no username (UA2). Two units of the hourly budget; the work's
   ``info`` lines «Email change notice sent to the previous address» then «… to the new address», each with the
   account's id and the language.
2. The work starts after the answer is complete, never before — the user does not wait on an SMTP server —, queued once
   with the account's id, the address it had, the address it has now and the engine of the request's own session, never
   the process's default database.
3. No email change, no notice: a username-only change, the stored address sent again, an empty body — 200 as before, the
   session goes on —: no SMTP conversation, no event of E, the budget untouched.
4. The same address in other capitals (``Zq-Vera@example.com`` → ``zq-vera@example.com``) is no email change, for A as
   for E: ``same_email`` folds A–Z. Asked without the current password: 200 with A's message and the new form, which is
   stored; no session ended — the answer sets no session cookie, and the one the browser signed in with still signs
   in —; and no notice: no SMTP conversation, no event of E, the budget untouched.
5. Email off (no ``LIBREFOLIO_SMTP_*``, the default of a self-hosted instance): the same answer and the same new cookie;
   E logs one ``info`` line, «Email change notice: email is off, nothing sent», with the account's id — no warning, no
   error.
6. A refused change — no current password (400 ``CURRENT_PASSWORD_REQUIRED``), a wrong one (400
   ``CURRENT_PASSWORD_INVALID``), an address another account has (400 «Email already registered») —: the stored address
   unchanged, no SMTP conversation, no event of E.
7. One address refused by the SMTP server — the old one, or the new one —: A's answer as in 1 — 200, the new address
   stored, the new cookie signs in —; the work's warning «Email change notice: not sent» with ``recipient``
   (``previous`` or ``new``), ``EmailDeliveryError`` and ``RECIPIENT_REFUSED``, and the other address still gets its
   email, with its ``info`` line (UA2).
8. The limits of a change's emails (E4b; per recipient since UA2): an account that had 3 changes with emails in the hour
   gets no emails for a fourth, but its email change is never limited. The fourth change in the hour, with the right
   current password, answers as in 1 — 200, the new address stored, a new cookie that signs in —, and sends nothing: no
   SMTP conversation, no budget unit; E logs one ``info`` line, «Email change notice: past its limits, nothing sent»,
   with the account's id — no warning. (The limit per recipient mailbox, and the window, are EMF-054…058 and
   EMF-061…066.)
9. A letter beyond A–Z in another case (``zq-vÉra@example.com`` → ``zq-véra@example.com``) makes another address, for
   A as for E: ``same_email`` compares it as written (P18's documented limit). With the right current password the
   change answers as in 1 — 200 with the new address and A's message, a new session cookie that signs in as it, the
   new address stored —, and the emails go as in 1: exactly two, to the old address then the new one exactly as stored
   (the envelope's recipient: the fake server advertises ``SMTPUTF8`` and takes an address beyond ASCII), two units of
   the budget, the work's ``info`` lines with the account's id.

E's events are the notice's lines («Email change notice…») and the delivery's («Email sent», «Email not sent…», «Email
configuration…»). Wherever a case has them (1, 5, 7, 8, 9), they name neither the old address nor the new one, nor
either's local part: the delivery logs the recipient's domain alone, and redacts the address a server quotes in its
refusal. The lines of A's route and of ``user_service.update_profile`` are A's, and are not looked at here.

Pure: the real auth router runs in-process on a private SQLite file under ``tmp_path`` (NullPool, disposed at teardown);
accounts are rows with a real bcrypt hash at cost 4, signed in through ``POST /auth/login`` by a client that keeps the
cookie. An autouse fixture removes every inherited ``LIBREFOLIO_SMTP_*``, ``LIBREFOLIO_PUBLIC_URL`` and
``LIBREFOLIO_BLOCKED``; each test sets its own with ``monkeypatch``. The hourly budget and the two limiters of a change's emails
(``flows.EMAIL_CHANGE_NOTICES_BY_ACCOUNT``, ``flows.EMAIL_CHANGE_NOTICES_BY_MAILBOX``, with the shipped limits) are
private, on a fake clock: every database here is new, so its accounts repeat their ids and addresses from test to test,
which the process's limiters would count across tests. ``socket.getaddrinfo`` resolves the loopback only; every SMTP
conversation is with ``FakeSmtpServer`` on 127.0.0.1. Nothing is timed.
"""

from __future__ import annotations

import contextlib
import os
import socket
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.api.v1 import auth as auth_api
from backend.app.config import API_V1_PREFIX
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import User, UserSettings
from backend.app.db.session import get_session_generator
from backend.app.services.accounts import auth_service, user_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.email import delivery, flows, smtp
from backend.app.services.email.messages import build_email_changed, build_email_changed_new_address
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.fixtures.email.fake_smtp import FakeSmtpServer
from backend.test_scripts.test_utils import print_section, print_success

LOGIN = f"{API_V1_PREFIX}/auth/login"
ME = f"{API_V1_PREFIX}/auth/me"
PROFILE = f"{API_V1_PREFIX}/auth/profile"
BASE_URL = "http://test"
TIMEOUT = 30.0
CLIENT = ("198.51.100.9", 40002)

SMTP_PREFIX = "LIBREFOLIO_SMTP_"
INHERITED = ("LIBREFOLIO_PUBLIC_URL", "LIBREFOLIO_BLOCKED")
SENDER_HEADER = "LibreFolio <noreply@example.com>"
LOOPBACK_NAMES = frozenset({"127.0.0.1", "::1", "localhost"})

PASSWORD = "Notice-Pass-2026"
WRONG_PASSWORD = "Not-The-Notice-Pass-2026"
VERA = "zq_vera"
OTHER = "zq_other"
OLD = "zq-vera@example.com"
OLD_LOCAL_PART = "zq-vera"
#: On another domain than the old address, so that this domain found in the notice could only be the new address's: the
#: notice shows no part of it (decision N62).
NEW = "zq-north@moved.example.com"
NEW_LOCAL_PART = "zq-north"
NEW_DOMAIN = "moved.example.com"
#: One address in two spellings, apart in the case of A–Z alone: the same address for A and for E, who compare two
#: addresses with one rule, ``user_service.same_email`` (decision P18).
CASE_OLD = "Zq-Vera@example.com"
CASE_NEW = "zq-vera@example.com"
#: Two addresses apart in the case of ``é`` alone, in NFC (one code point each): beyond A–Z ``same_email`` compares a
#: letter as written, so they are two addresses for A and for E alike (ECN-009).
ACCENTED_OLD = "zq-v\u00c9ra@example.com"
ACCENTED_NEW = "zq-v\u00e9ra@example.com"
#: The addresses one account goes through in ECN-008, four changes in the hour: each change leaves the one before it.
MOVES = (OLD, "zq-vera-1@moved.example.com", "zq-vera-2@moved.example.com", "zq-vera-3@moved.example.com", "zq-vera-4@moved.example.com")
UPDATED = "Profile updated successfully"
NO_CHANGES = "No changes requested"
#: How E's log events begin: the notice's lines and the delivery's. A's own lines are A's, not looked at here.
E_EVENTS = ("Email change notice", "Email sent", "Email not sent", "Email configuration")
#: The work's line when the account already had its 3 changes with emails in the hour (E4b).
PAST_ITS_LIMITS = "Email change notice: past its limits, nothing sent"
#: The work's lines of each email that went (UA2): the old address's, then the new one's.
NOTICE_SENT = "Email change notice sent to the previous address"
NEW_SENT = "Email change notice sent to the new address"
#: What E logs, in order, for a change whose two emails went: each email's delivery line, then the work's.
BOTH_SENT = [("Email sent", "info"), (NOTICE_SENT, "info"), ("Email sent", "info"), (NEW_SENT, "info")]
START = 1_000.0
#: The notice's limiters as the module ships them (E4b), read before the fixture below replaces them.
SHIPPED_NOTICES_BY_ACCOUNT = flows.EMAIL_CHANGE_NOTICES_BY_ACCOUNT
SHIPPED_NOTICES_BY_MAILBOX = flows.EMAIL_CHANGE_NOTICES_BY_MAILBOX


class FakeClock:
    """A clock that moves only when the test sets it: ``clock.now = …``."""

    def __init__(self, start: float = START) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def _no_inherited_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.startswith(SMTP_PREFIX) or name in INHERITED:
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _nothing_reported_yet() -> Iterator[None]:
    delivery._report_invalid.cache_clear()
    yield
    delivery._report_invalid.cache_clear()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture(autouse=True)
def budget(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> SlidingWindowLimiter:
    limiter = SlidingWindowLimiter(50, 3600, max_keys=1, clock=clock)
    monkeypatch.setattr(delivery, "INSTANCE_BUDGET", limiter)
    return limiter


@dataclass(frozen=True)
class NoticeLimits:
    """The two limiters of the emails of an email change of a test: per account, per recipient mailbox."""

    by_account: SlidingWindowLimiter
    by_mailbox: SlidingWindowLimiter


@pytest.fixture(autouse=True)
def notice_limits(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> NoticeLimits:
    """Private limiters of a change's emails with the shipped limits, on the fake clock: every database here is new, so its accounts repeat their ids and addresses from test to test, and the process's limiters would count them across tests."""
    limits = NoticeLimits(
        by_account=SlidingWindowLimiter(SHIPPED_NOTICES_BY_ACCOUNT.limit, SHIPPED_NOTICES_BY_ACCOUNT.window_seconds, clock=clock),
        by_mailbox=SlidingWindowLimiter(SHIPPED_NOTICES_BY_MAILBOX.limit, SHIPPED_NOTICES_BY_MAILBOX.window_seconds, clock=clock),
    )
    monkeypatch.setattr(flows, "EMAIL_CHANGE_NOTICES_BY_ACCOUNT", limits.by_account)
    monkeypatch.setattr(flows, "EMAIL_CHANGE_NOTICES_BY_MAILBOX", limits.by_mailbox)
    return limits


@pytest.fixture(autouse=True)
def _bounded_smtp_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smtp, "SMTP_TIMEOUT_SECONDS", 5.0)


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


@dataclass(frozen=True)
class _Private:
    engine: AsyncEngine
    app: FastAPI


def _app(engine: AsyncEngine) -> FastAPI:
    """The real auth router under the API prefix; sessions on ``engine``."""
    app = FastAPI()
    app.include_router(auth_api.router, prefix=API_V1_PREFIX)

    async def private_session() -> AsyncIterator[AsyncSession]:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session_generator] = private_session
    return app


@pytest_asyncio.fixture
async def private(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[_Private]:
    """An empty instance on a private SQLite file: schema and default settings, no account; bcrypt at cost 4."""
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)
    monkeypatch.setattr(auth_api, "SESSION_COOKIE_SECURE_MODE", "auto")
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'notice.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            await initialize_global_settings(session)
        yield _Private(engine=engine, app=_app(engine))
    finally:
        await engine.dispose()


# =============================================================================
# HELPERS
# =============================================================================


async def _add_user(engine: AsyncEngine, username: str, email: str, *, language: str | None = None) -> User:
    """An active member with a real bcrypt hash; with ``language``, a ``user_settings`` row saying it."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=email, hashed_password=auth_service.hash_password(PASSWORD), is_active=True)
        session.add(user)
        await session.commit()
        if language is not None:
            session.add(UserSettings(user_id=user.id, language=language))
            await session.commit()
    return user


async def _stored_email(engine: AsyncEngine, user_id: int) -> str:
    async with AsyncSession(engine) as session:
        return (await session.execute(select(User.email).where(User.id == user_id))).scalar_one()


def _ready(monkeypatch: pytest.MonkeyPatch, fake: FakeSmtpServer) -> None:
    """Email ready towards ``fake``; no ``LIBREFOLIO_PUBLIC_URL``: neither email of a change carries a link."""
    for name, value in {"HOST": fake.host, "PORT": str(fake.port), "TLS": "none", "FROM": SENDER_HEADER}.items():
        monkeypatch.setenv(SMTP_PREFIX + name, value)


@contextlib.asynccontextmanager
async def _browser(app: Any) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app, client=CLIENT)
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL, timeout=TIMEOUT) as browser:
        yield browser


@contextlib.asynccontextmanager
async def _signed_in(app: Any, username: str = VERA) -> AsyncIterator[httpx.AsyncClient]:
    """A browser of its own, signed in as ``username`` through ``POST /auth/login``: it keeps the session cookie."""
    async with _browser(app) as browser:
        signed_in = await browser.post(LOGIN, json={"username": username, "password": PASSWORD})
        assert signed_in.status_code == 200, f"setup: {username} could not sign in: {signed_in.text}"
        assert _cookie(browser), "setup: the sign-in set no session cookie"
        yield browser


def _cookie(browser: httpx.AsyncClient) -> str | None:
    """The session cookie the browser holds now."""
    return browser.cookies.get(auth_api.SESSION_COOKIE_NAME)


async def _change(browser: httpx.AsyncClient, body: dict[str, Any]) -> tuple[httpx.Response, list[dict[str, Any]]]:
    """``PUT /auth/profile`` with ``body``, and every log event of the request, its work after the answer included."""
    with capture_logs() as events:
        response = await browser.put(PROFILE, json=body)
    return response, events


def _assert_renewed(response: httpx.Response, before: str | None) -> None:
    """The answer sets a new session cookie (A6e): the change ended every session, this one carries on."""
    renewed = response.cookies.get(auth_api.SESSION_COOKIE_NAME)
    assert renewed and renewed != before, f"the answer of an email change sets a new session cookie: {response.headers.get_list('set-cookie')}"


def _assert_not_renewed(response: httpx.Response) -> None:
    """The answer sets no session cookie, matched by name in its ``Set-Cookie`` headers: no email change, no session ended."""
    written = [header for header in response.headers.get_list("set-cookie") if header.split(";", 1)[0].partition("=")[0].strip() == auth_api.SESSION_COOKIE_NAME]
    assert written == [], f"no email change, no new session cookie: {response.headers.get_list('set-cookie')}"


def _answer_recorded(app: FastAPI, order: list[str]) -> Any:
    """``app``, writing ``answered`` in ``order`` once the answer to ``PUT /auth/profile`` is complete: its last body part sent."""

    async def recorded(scope: dict[str, Any], receive: Any, send: Any) -> None:
        async def send_and_record(message: dict[str, Any]) -> None:
            await send(message)
            if scope.get("path") == PROFILE and message["type"] == "http.response.body" and not message.get("more_body", False):
                order.append("answered")

        await app(scope, receive, send_and_record)

    return recorded


def _text(received: object) -> str:
    """The plain-text part of a received message."""
    return received.message.get_body(preferencelist=("plain",)).get_content()


def _html(received: object) -> str:
    """The HTML part of a received message."""
    return received.message.get_body(preferencelist=("html",)).get_content()


def _lines(text: str) -> str:
    """``text`` without the line-ending differences of a MIME round trip."""
    return text.replace("\r\n", "\n").rstrip("\n")


def _mailboxes(header: object) -> list[tuple[str, str]]:
    return [(address.display_name, address.addr_spec) for address in header.addresses]


def _assert_is(received: object, expected: object) -> None:
    """The message is exactly the content a builder wrote: subject, text and HTML."""
    assert received.message["Subject"] == expected.subject
    assert _lines(_text(received)) == _lines(expected.text)
    assert _lines(_html(received)) == _lines(expected.html)


def _e_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """E's log events: the notice's lines and the delivery's."""
    return [event for event in events if str(event.get("event", "")).startswith(E_EVENTS)]


def _notices(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The log events of the notice itself."""
    return [event for event in events if str(event.get("event", "")).startswith("Email change notice")]


def _naming(events: list[dict[str, Any]], *needles: str) -> list[dict[str, Any]]:
    """The events in which a value — the message included — holds one of ``needles``, in any letter case."""
    folded = [needle.casefold() for needle in needles]
    return [event for event in events if any(needle in str(value).casefold() for value in event.values() for needle in folded)]


# =============================================================================
# 1–2. AN EMAIL CHANGE: THE ANSWER, THEN THE EMAILS TO BOTH ADDRESSES
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(("own", "language"), [pytest.param(None, "en", id="the-instances-language"), pytest.param("it", "it", id="its-own-language")])
async def test_an_email_change_answers_as_before_then_emails_both_addresses(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, own: str | None, language: str) -> None:
    """ECN-001 — contract 1: the right current password, email ready. The answer: 200 with the new address and A's message, a new session cookie, and ``GET /auth/me`` with it says the new address. Then two emails, the old address first, each to its address only, in the account's language with «LibreFolio» as the instance: to the old address exactly ``build_email_changed``, with no part of the new address — neither its local part nor its domain — and no username in its text, its HTML or a header (decision N62); to the new address exactly ``build_email_changed_new_address``, with no part of the old address and no username (UA2). Two budget units; the work's two ``info`` lines with the account's id and the language. E's events name neither address."""
    print_section(f"ECN-001: an email change, both emails in {language}")
    vera = await _add_user(private.engine, VERA, OLD, language=own)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        async with _signed_in(private.app) as browser:
            before = _cookie(browser)
            response, events = await _change(browser, {"email": NEW, "current_password": PASSWORD})
            me = await browser.get(ME)

    assert response.status_code == 200, response.text
    assert (response.json()["user"]["email"], response.json()["message"]) == (NEW, UPDATED)
    _assert_renewed(response, before)
    assert (me.status_code, me.json()["user"]["email"]) == (200, NEW), f"the new cookie signs in as the new address: {me.status_code} {me.text}"
    assert await _stored_email(private.engine, vera.id) == NEW

    assert [message.rcpt_tos for message in fake.messages] == [[OLD], [NEW]], "exactly two emails, the old address first, each to its address only"
    notice, confirmation = fake.messages
    for received, address in ((notice, OLD), (confirmation, NEW)):
        assert _mailboxes(received.message["To"]) == [("", address)]
        assert (received.message["Cc"], received.message["Bcc"]) == (None, None)
    shown = _text(notice) + _html(notice) + " ".join(str(value) for value in notice.message.values())
    assert [part for part in (NEW, NEW_LOCAL_PART, NEW_DOMAIN) if part.casefold() in shown.casefold()] == [], "the notice carries no part of the new address, neither its local part nor its domain: its new owner chose them (N62)"
    assert VERA not in shown, "the notice greets nobody by name: the username is its owner's text (N62)"
    body = _text(confirmation) + _html(confirmation)
    headers = " ".join(str(value) for value in confirmation.message.values())
    # The old domain is the sender's too (``From``, ``Message-ID``): looked for in the body only.
    assert [part for part in (OLD, OLD_LOCAL_PART, "example.com") if part.casefold() in body.casefold()] + [part for part in (OLD, OLD_LOCAL_PART) if part.casefold() in headers.casefold()] == [], "the email to the new address carries no part of the old one: a stranger may read it"
    assert VERA not in body + headers, "the email to the new address greets nobody by name"
    _assert_is(notice, build_email_changed(language=language, instance=flows.INSTANCE_FALLBACK))
    _assert_is(confirmation, build_email_changed_new_address(language=language, instance=flows.INSTANCE_FALLBACK))
    assert budget.count() == 2

    assert [(event["event"], event["log_level"]) for event in _e_events(events)] == BOTH_SENT
    assert [(event.get("user_id"), event.get("language")) for event in _notices(events)] == [(vera.id, language)] * 2
    assert _naming(_e_events(events), OLD, OLD_LOCAL_PART, NEW, NEW_LOCAL_PART) == [], "E's events name neither address: the delivery logs the recipient's domain alone"
    print_success(f"200 and a new cookie; the notice to {OLD}, the confirmation to {NEW}, in {language}")


@pytest.mark.asyncio
async def test_the_notice_is_queued_after_the_answer_with_both_addresses_and_the_requests_engine(private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
    """ECN-002 — contract 2: the work starts once the answer is complete — its last body part sent —, never before; it is queued once, with the account's id, the address it had, the address it has now and the engine of the request's own session (the private file here), not the process's default database."""
    print_section("ECN-002: queued after the answer, with both addresses and the request's engine")
    vera = await _add_user(private.engine, VERA, OLD)
    order: list[str] = []
    calls: list[tuple[int, str, str, Any]] = []

    async def queued(user_id: int, old_address: str, new_address: str, *, engine: AsyncEngine | None = None) -> None:
        order.append("notice")
        calls.append((user_id, old_address, new_address, engine))

    monkeypatch.setattr(flows, "email_changed_work", queued)
    async with _signed_in(_answer_recorded(private.app, order)) as browser:
        response = await browser.put(PROFILE, json={"email": NEW, "current_password": PASSWORD})

    assert response.status_code == 200, response.text
    assert order == ["answered", "notice"], f"the notice once, after the complete answer: {order}"
    assert [call[:3] for call in calls] == [(vera.id, OLD, NEW)]
    assert calls[0][3] is private.engine, f"the work reads the request's database, not {calls[0][3]!r}"
    print_success("after the answer; (id, old, new) and the request's engine")


# =============================================================================
# 3–4. NO EMAIL CHANGE, NO NOTICE
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body", "message"),
    [
        pytest.param({"username": "zq_vera_renamed"}, UPDATED, id="a-username-only-change"),
        pytest.param({"email": OLD}, UPDATED, id="the-stored-address-sent-again"),
        pytest.param({}, NO_CHANGES, id="an-empty-body"),
    ],
)
async def test_no_notice_without_an_email_change(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, body: dict[str, Any], message: str) -> None:
    """ECN-003 — contract 3: email ready, and nothing asks to change the address — a username-only change, the stored address sent again (no password needed), an empty body —: 200 with A's message and the old address, the session goes on; no SMTP conversation, no event of E, no budget unit."""
    print_section(f"ECN-003: {sorted(body) or 'an empty body'}")
    vera = await _add_user(private.engine, VERA, OLD)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        async with _signed_in(private.app) as browser:
            response, events = await _change(browser, body)
            me = await browser.get(ME)

    assert response.status_code == 200, response.text
    assert (response.json()["message"], response.json()["user"]["email"]) == (message, OLD)
    assert me.status_code == 200, f"the session goes on: {me.status_code} {me.text}"
    assert await _stored_email(private.engine, vera.id) == OLD
    assert (fake.connections, budget.count()) == (0, 0)
    assert _e_events(events) == []
    print_success("200; no email, no event of E")


@pytest.mark.asyncio
async def test_the_same_address_in_other_capitals_is_no_change_and_no_notice(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter) -> None:
    """ECN-004 — contract 4: stored ``Zq-Vera@example.com``, asked ``zq-vera@example.com`` without the current password. A and E compare two addresses with one rule, ``user_service.same_email`` (decision P18): apart in the case of A–Z alone, they are the same address, so this is no email change. 200 with A's message and the new form, which is stored; the answer sets no session cookie, and the one the browser signed in with still signs in: no session ended. And no notice: no SMTP conversation, no event of E, no budget unit."""
    print_section("ECN-004: the same address in other capitals")
    assert CASE_OLD != CASE_NEW and user_service.same_email(CASE_OLD, CASE_NEW), "precondition: one address, apart in the case of A–Z alone"
    vera = await _add_user(private.engine, VERA, CASE_OLD)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        async with _signed_in(private.app) as browser:
            before = _cookie(browser)
            response, events = await _change(browser, {"email": CASE_NEW})
            held = _cookie(browser)
            me = await browser.get(ME)

    assert response.status_code == 200, response.text
    assert (response.json()["user"]["email"], response.json()["message"]) == (CASE_NEW, UPDATED)
    _assert_not_renewed(response)
    assert held == before, "the browser still holds the cookie it signed in with"
    assert (me.status_code, me.json()["user"]["email"]) == (200, CASE_NEW), f"that cookie still signs in, the new form shown: {me.status_code} {me.text}"
    assert await _stored_email(private.engine, vera.id) == CASE_NEW, "the new form stored: the same address, written as asked"
    assert (fake.connections, budget.count()) == (0, 0), "the same address: no notice"
    assert _e_events(events) == []
    print_success(f"{CASE_OLD} → {CASE_NEW}: no password asked, the session goes on, no notice")


# =============================================================================
# 5–7. EMAIL OFF, A REFUSED CHANGE, A REFUSED ADDRESS
# =============================================================================


@pytest.mark.asyncio
async def test_email_off_answers_as_before_with_an_info_line(private: _Private, budget: SlidingWindowLimiter) -> None:
    """ECN-005 — contract 5: no ``LIBREFOLIO_SMTP_*``. The email change answers as with email ready — 200, the new address, A's message, a new cookie that signs in —; E logs exactly one line, «Email change notice: email is off, nothing sent», ``info``, with the account's id — no warning, no error of E —; no budget unit."""
    print_section("ECN-005: email off")
    vera = await _add_user(private.engine, VERA, OLD)

    async with _signed_in(private.app) as browser:
        before = _cookie(browser)
        response, events = await _change(browser, {"email": NEW, "current_password": PASSWORD})
        me = await browser.get(ME)

    assert response.status_code == 200, response.text
    assert (response.json()["user"]["email"], response.json()["message"]) == (NEW, UPDATED)
    _assert_renewed(response, before)
    assert (me.status_code, me.json()["user"]["email"]) == (200, NEW)
    assert budget.count() == 0
    assert [(event["event"], event["log_level"], event.get("user_id")) for event in _e_events(events)] == [("Email change notice: email is off, nothing sent", "info", vera.id)]
    print_success("200 and a new cookie; one info line")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body", "code", "taken"),
    [
        pytest.param({"email": NEW}, "CURRENT_PASSWORD_REQUIRED", False, id="no-current-password"),
        pytest.param({"email": NEW, "current_password": WRONG_PASSWORD}, "CURRENT_PASSWORD_INVALID", False, id="a-wrong-current-password"),
        pytest.param({"email": NEW, "current_password": PASSWORD}, None, True, id="an-address-another-account-has"),
    ],
)
async def test_a_refused_change_sends_nothing(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, body: dict[str, Any], code: str | None, taken: bool) -> None:
    """ECN-006 — contract 6: email ready, the change refused — no current password, a wrong one (A6e's coded 400s), or an address another account has (400 «Email already registered») —: the stored address unchanged; no SMTP conversation, no event of E, no budget unit."""
    print_section(f"ECN-006: refused, {code or 'the address taken'}")
    vera = await _add_user(private.engine, VERA, OLD)
    if taken:
        await _add_user(private.engine, OTHER, NEW)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        async with _signed_in(private.app) as browser:
            response, events = await _change(browser, body)

    assert response.status_code == 400, response.text
    detail = response.json()["detail"]
    if code is not None:
        assert detail["error_code"] == code, detail
    else:
        assert "already registered" in str(detail).lower(), detail
    assert await _stored_email(private.engine, vera.id) == OLD
    assert (fake.connections, budget.count()) == (0, 0)
    assert _e_events(events) == []
    print_success("400; nothing sent")


@pytest.mark.asyncio
@pytest.mark.parametrize("refused", ["previous", "new"])
async def test_one_address_refused_by_the_server_leaves_the_answer_and_the_other_email(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, refused: str) -> None:
    """ECN-007 — contract 7: the SMTP server refuses one address — the old one, or the new one (UA2) —. A's answer as in ECN-001 — 200, the new address stored, a new cookie that signs in —; the work's warning «Email change notice: not sent» with the account's id, ``recipient`` naming the side, ``EmailDeliveryError`` and ``RECIPIENT_REFUSED``; and the other address still gets its email, exactly as its builder writes it, with its ``info`` line. The server's refusal quotes the refused address: E's events still name neither address."""
    print_section(f"ECN-007: the {refused} address refused by the SMTP server")
    vera = await _add_user(private.engine, VERA, OLD)
    refused_address, other = (OLD, NEW) if refused == "previous" else (NEW, OLD)

    with FakeSmtpServer(refuse_recipients={refused_address}) as fake:
        _ready(monkeypatch, fake)
        async with _signed_in(private.app) as browser:
            before = _cookie(browser)
            response, events = await _change(browser, {"email": NEW, "current_password": PASSWORD})
            me = await browser.get(ME)

    assert response.status_code == 200, response.text
    assert (response.json()["user"]["email"], response.json()["message"]) == (NEW, UPDATED)
    _assert_renewed(response, before)
    assert (me.status_code, me.json()["user"]["email"]) == (200, NEW)
    assert await _stored_email(private.engine, vera.id) == NEW, "the change stays done"
    assert [message.rcpt_tos for message in fake.messages] == [[other]], "the other address still got its email"
    builder = build_email_changed_new_address if refused == "previous" else build_email_changed
    _assert_is(fake.messages[0], builder(language="en", instance=flows.INSTANCE_FALLBACK))
    went = [("Email sent", None), (NEW_SENT if refused == "previous" else NOTICE_SENT, None)]
    failed = [("Email not sent", None), ("Email change notice: not sent", refused)]
    expected = failed + went if refused == "previous" else went + failed
    assert [(event["event"], event.get("recipient")) for event in _e_events(events)] == expected, "each email: the delivery's line, then the work's"
    warning = [(event["log_level"], event.get("user_id"), event.get("recipient"), event.get("reason"), event.get("code")) for event in _notices(events) if event["log_level"] == "warning"]
    assert warning == [("warning", vera.id, refused, "EmailDeliveryError", "RECIPIENT_REFUSED")]
    assert budget.count() == 2, "one unit per attempt: the delivery's rule"
    assert _naming(_e_events(events), OLD, OLD_LOCAL_PART, NEW, NEW_LOCAL_PART) == [], "the refusal quoted the address: E's lines keep its domain at most"
    print_success(f"200 and a new cookie; the {refused} address refused with a warning, the other email sent")


# =============================================================================
# 8. PAST THE LIMITS OF A CHANGE'S EMAILS, THE CHANGE STILL GOES THROUGH
# =============================================================================


@pytest.mark.asyncio
async def test_past_three_notices_an_hour_the_change_goes_through_without_one(private: _Private, monkeypatch: pytest.MonkeyPatch, clock: FakeClock, budget: SlidingWindowLimiter, notice_limits: NoticeLimits) -> None:
    """ECN-008 — contract 8: email ready; Vera changes her email four times in the hour, a minute apart, each time with the right current password and from the address the change before gave her, so no mailbox gets more than two emails. Every change answers as in ECN-001 — 200 with the new address and A's message, a new session cookie —; the first three each send both emails, the notice to the address they left and the confirmation to the one they reached. The fourth sends none — no SMTP conversation, no budget unit; of E only the ``info`` line «Email change notice: past its limits, nothing sent» with her id —, and still goes through: the new address stored, ``GET /auth/me`` with the new cookie says it. E's events name none of the five addresses."""
    print_section("ECN-008: the fourth change in the hour goes through, without its emails")
    vera = await _add_user(private.engine, VERA, MOVES[0])
    changes: list[tuple[httpx.Response, str | None, list[dict[str, Any]]]] = []

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        async with _signed_in(private.app) as browser:
            for index, new in enumerate(MOVES[1:]):
                clock.now = START + 60 * index
                before = _cookie(browser)
                response, events = await _change(browser, {"email": new, "current_password": PASSWORD})
                changes.append((response, before, events))
            me = await browser.get(ME)

    for (response, before, _events), new in zip(changes, MOVES[1:], strict=True):
        assert response.status_code == 200, response.text
        assert (response.json()["user"]["email"], response.json()["message"]) == (new, UPDATED)
        _assert_renewed(response, before)
    assert (me.status_code, me.json()["user"]["email"]) == (200, MOVES[-1]), f"the fourth change's cookie signs in as its address: {me.status_code} {me.text}"
    assert await _stored_email(private.engine, vera.id) == MOVES[-1]

    assert [message.rcpt_tos for message in fake.messages] == [[address] for index in range(3) for address in (MOVES[index], MOVES[index + 1])], "three changes, each its notice and its confirmation; none for the fourth"
    assert (fake.connections, budget.count()) == (6, 6), "one per email of the first three changes; the fourth: no SMTP conversation, no budget unit"
    sent = [[(event["event"], event["log_level"]) for event in _e_events(events)] for _response, _before, events in changes[:3]]
    assert sent == [BOTH_SENT] * 3, f"barrier: the first three changes each sent both emails: {sent}"
    fourth = [(event["event"], event["log_level"], event.get("user_id")) for event in _e_events(changes[3][2])]
    assert fourth == [(PAST_ITS_LIMITS, "info", vera.id)], fourth
    assert notice_limits.by_account.count(vera.id) == 3, "her three changes; nothing counted for the skipped one"
    assert [notice_limits.by_mailbox.count(address) for address in MOVES] == [1, 2, 2, 1, 0], "each email once under its mailbox; nothing for the fourth change's"
    every_event = [event for _response, _before, events in changes for event in events]
    assert _naming(_e_events(every_event), *MOVES, *(address.partition("@")[0] for address in MOVES)) == [], "E's events name none of the addresses"
    print_success("four changes, each 200 with a new cookie; three with both emails, the fourth without")


# =============================================================================
# 9. A LETTER BEYOND A–Z IN ANOTHER CASE: ANOTHER ADDRESS, AND ITS EMAILS
# =============================================================================


@pytest.mark.asyncio
async def test_another_case_beyond_a_to_z_is_a_change_and_both_addresses_get_their_email(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter) -> None:
    """ECN-009 — contract 9: stored ``zq-vÉra@example.com``, asked ``zq-véra@example.com`` with the right current password. The two are apart in the case of ``é`` alone, a letter beyond A–Z, which ``user_service.same_email`` compares as written (decision P18's documented limit): two addresses, for A as for E. A's answer as in ECN-001 — 200 with the new address and A's message, a new session cookie that signs in as it, the new address stored —; then the emails as in ECN-001: exactly two, to the old address then the new one exactly as stored (the envelope's recipient: the fake server takes an address beyond ASCII with ``SMTPUTF8``), two budget units, the delivery's and the work's ``info`` lines, the work's with the account's id and its language. E's events name neither address."""
    print_section("ECN-009: another case beyond A–Z")
    assert ACCENTED_OLD.casefold() == ACCENTED_NEW.casefold() and not user_service.same_email(ACCENTED_OLD, ACCENTED_NEW), "precondition: one mailbox for casefold, two addresses for P18's rule"
    vera = await _add_user(private.engine, VERA, ACCENTED_OLD)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        async with _signed_in(private.app) as browser:
            before = _cookie(browser)
            response, events = await _change(browser, {"email": ACCENTED_NEW, "current_password": PASSWORD})
            me = await browser.get(ME)

    assert response.status_code == 200, response.text
    assert (response.json()["user"]["email"], response.json()["message"]) == (ACCENTED_NEW, UPDATED)
    _assert_renewed(response, before)
    assert (me.status_code, me.json()["user"]["email"]) == (200, ACCENTED_NEW), f"the new cookie signs in as the new address: {me.status_code} {me.text}"
    assert await _stored_email(private.engine, vera.id) == ACCENTED_NEW

    assert [message.rcpt_tos for message in fake.messages] == [[ACCENTED_OLD], [ACCENTED_NEW]], "exactly two emails, to the old address then the new one, exactly as stored"
    assert budget.count() == 2
    assert [(event["event"], event["log_level"]) for event in _e_events(events)] == BOTH_SENT
    assert [(event.get("user_id"), event.get("language")) for event in _notices(events)] == [(vera.id, "en")] * 2
    local_parts = [address.partition("@")[0] for address in (ACCENTED_OLD, ACCENTED_NEW)]
    assert _naming(_e_events(events), ACCENTED_OLD, ACCENTED_NEW, *local_parts) == [], "E's events name neither address: the delivery logs the recipient's domain alone"
    print_success(f"{ACCENTED_OLD} → {ACCENTED_NEW}: a change, a new cookie, both emails")
