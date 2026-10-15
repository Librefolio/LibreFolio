"""``backend.app.services.email.flows``: the language of an account's emails, and the test email (plan phase01Email §3.3, §3.4, decisions D-E1, D-E9, lot E2a).

``account_language`` decides the language every email of an account is written in; ``send_test_email`` is the email an
administrator sends to themselves from the «Email» tab (``POST /email/test``, tested over HTTP in
``test_api/test_email_api.py``). The flows decide content, recipient and language only: ``delivery.send_email`` checks
the configuration and the hourly budget, sends and logs (``test_email_delivery.py``). The contract pinned here:

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

Pure: every database is a private SQLite file under ``tmp_path`` built with ``create_all`` and the default global
settings (NullPool, disposed at teardown), users written as rows; no server of the lane, no network beyond 127.0.0.1.
An autouse fixture removes every inherited ``LIBREFOLIO_SMTP_*`` (until C-96 lands a lane carries the developer's
``.env``) and each test sets its own with ``monkeypatch``; another replaces ``delivery.INSTANCE_BUDGET`` with a private
limiter on a fake clock; ``smtp.SMTP_TIMEOUT_SECONDS`` is 5 s, a bound for a defect that hangs, never a wait. Every SMTP
conversation is with ``FakeSmtpServer`` on 127.0.0.1, on a port the OS picks. Nothing is timed.
"""

from __future__ import annotations

import asyncio
import inspect
import os
import threading
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import GlobalSetting, User, UserSettings
from backend.app.schemas.settings import SETTINGS_REGISTRY
from backend.app.services.accounts.settings_service import get_user_settings, initialize_global_settings
from backend.app.services.email import delivery, smtp
from backend.app.services.email.delivery import EmailError, EmailUnavailableError
from backend.app.services.email.flows import account_language, send_test_email
from backend.app.services.email.messages import EmailRecipientError, build_test_message, email_language, supported_email_language
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.fixtures.email.fake_smtp import FakeSmtpServer
from backend.test_scripts.test_utils import print_section, print_success

SMTP_PREFIX = "LIBREFOLIO_SMTP_"
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
#: A theme outside light/dark/auto, as an older or newer release could leave in a row: ``UserSettingsRead`` refuses it.
STALE_THEME = "sepia"

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
def _no_inherited_smtp_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every ``LIBREFOLIO_SMTP_*`` the lane inherited is removed: a test sees only the variables it sets itself."""
    for name in list(os.environ):
        if name.startswith(SMTP_PREFIX):
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


async def _add_user(engine: AsyncEngine, username: str, *, email: str | None = None) -> User:
    """An active account written as a row, ``<username>@example.com`` unless ``email`` says otherwise, without a ``user_settings`` row; returned detached, its columns loaded."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=email or f"{username}@example.com", hashed_password=MARKER_HASH)
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
