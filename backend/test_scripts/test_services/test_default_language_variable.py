"""``LIBREFOLIO_DEFAULT_LANGUAGE``: the instance's default language before an administrator chose one (release 2.0, workstream H, checkpoint 1, lot CL-10).

A hosting provider that sells to an Italian customer sets ``LIBREFOLIO_DEFAULT_LANGUAGE=it`` on the instance: the
emails (the setup link, a verification, an invitation) go out in Italian from the very first one, and a new account
starts in Italian. The variable is read by ``backend.app.config.accounts.default_language()`` (its own cases are in
``test_registration_service.py``; the startup audit stops on an unusable value in ``test_accounts_checks.py``).

The rule under test is where the variable meets the global setting ``default_language``:

- The variable is the instance default **only while no administrator ever wrote the setting**: its row is missing, or its
  ``updated_by_user_id`` is NULL (the row ``initialize_global_settings`` seeds at startup, with ``en``, has it NULL).
- Once an administrator saved the setting (``update_global_settings`` sets ``updated_by_user_id``) the row wins, even when
  it says ``en``: the variable never overrides a choice.
- Where it lives: ``global_settings_service.get_setting_value`` (so every reader of the setting follows) and the readers
  ``settings_service.get_global_setting`` / ``get_all_global_settings`` (so the administrator sees the effective value).
- What follows: ``email.flows.instance_language`` and ``account_language`` (for an account without a settings row; an
  account's own language is still its own), and ``get_or_create_user_settings`` (a new account is seeded with it).
- The variable touches nothing but the key ``default_language``.

How: a private SQLite file under ``tmp_path`` with the whole ORM schema and the seeded global settings; the variable set
through ``monkeypatch``. Isolation: pure. No lane database, no server, no network, no clock.

Red today: the variable is not read anywhere, so every case that expects ``it`` reads the row's ``en``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import GlobalSetting, User, UserSettings
from backend.app.schemas.settings import SETTINGS_REGISTRY
from backend.app.services.accounts import settings_service
from backend.app.services.accounts.global_settings_service import get_setting_value
from backend.app.services.email import flows
from backend.test_scripts.test_utils import print_section, print_success

VARIABLE = "LIBREFOLIO_DEFAULT_LANGUAGE"
KEY = SETTINGS_REGISTRY.global_.DEFAULT_LANGUAGE.key
CURRENCY_KEY = SETTINGS_REGISTRY.global_.DEFAULT_CURRENCY.key
THEME_KEY = SETTINGS_REGISTRY.global_.DEFAULT_THEME.key
#: What the startup seeding writes: English, untouched by any administrator.
SEEDED_LANGUAGE = "en"


@pytest.fixture(autouse=True)
def _no_inherited_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """A test sees only the value it sets itself."""
    monkeypatch.delenv(VARIABLE, raising=False)


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file with the whole ORM schema and the default global settings (``default_language`` ``en``, ``updated_by_user_id`` NULL)."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'default_language.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            await settings_service.initialize_global_settings(session)
        yield engine
    finally:
        await engine.dispose()


async def _add_user(engine: AsyncEngine, label: str) -> User:
    """An account written as a row, without a ``user_settings`` row; returned detached, its columns loaded."""
    username = f"cl10_{label}_{uuid4().hex[:8]}"
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=f"{username}@example.com", hashed_password="marker-hash-not-bcrypt", is_active=True)
        session.add(user)
        await session.commit()
    return user


async def _admin_saves(engine: AsyncEngine, value: str) -> None:
    """An administrator saves ``default_language`` through the service the API uses (``update_global_settings``), which records who."""
    admin = await _add_user(engine, "admin")
    async with AsyncSession(engine) as session:
        written = await settings_service.update_global_settings([(KEY, value)], admin.id, session)
    assert [(item.key, item.value, item.updated_by) for item in written] == [(KEY, value, admin.id)], f"Barrier: the administrator's save is recorded with their id: {written}"


async def _row(engine: AsyncEngine) -> GlobalSetting | None:
    async with AsyncSession(engine) as session:
        return (await session.execute(select(GlobalSetting).where(GlobalSetting.key == KEY))).scalar_one_or_none()


async def _effective(engine: AsyncEngine) -> Any:
    async with AsyncSession(engine) as session:
        return await get_setting_value(session, KEY, "en")


async def _seeded_row_is_untouched(engine: AsyncEngine) -> None:
    """Barrier: the row is the one the startup seeding wrote, ``en`` and no administrator behind it."""
    row = await _row(engine)
    assert row is not None and (row.value, row.updated_by_user_id) == (SEEDED_LANGUAGE, None), f"Barrier: the seeded row says {SEEDED_LANGUAGE!r} and was never saved by an administrator: {row!r}"


# =============================================================================
# (1) get_setting_value: the variable while no administrator wrote the row
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("variable", ["it", "fr", "es", " IT ", "Fr"], ids=["it", "fr", "es", "padded-upper", "mixed-case"])
async def test_an_untouched_row_gives_way_to_the_variable(engine, monkeypatch, variable):
    """CL-10-1a: the seeded row (``en``, nobody saved it) and the variable set: ``get_setting_value`` answers the variable's value, lower-case."""
    print_section(f"CL-10-1a: {VARIABLE}={variable!r}, the seeded row")
    await _seeded_row_is_untouched(engine)
    monkeypatch.setenv(VARIABLE, variable)

    value = await _effective(engine)

    assert value == variable.strip().lower(), f"{VARIABLE}={variable!r} over an untouched row: the effective default language is {variable.strip().lower()!r}, got {value!r}"
    print_success(f"{variable!r}: {value!r}")


@pytest.mark.asyncio
async def test_without_the_variable_the_row_is_the_answer(engine, monkeypatch):
    """CL-10-1b: the variable unset (or blank): the row's value, as ever; so a row an administrator wrote is read as written. Control of the cases around it."""
    print_section("CL-10-1b: no variable")
    await _seeded_row_is_untouched(engine)
    assert await _effective(engine) == SEEDED_LANGUAGE, "the seeded row, no variable: en"
    monkeypatch.setenv(VARIABLE, "   ")
    assert await _effective(engine) == SEEDED_LANGUAGE, "a blank variable counts as unset: en"
    monkeypatch.delenv(VARIABLE)
    await _admin_saves(engine, "fr")
    assert await _effective(engine) == "fr", "an administrator's choice, no variable: fr"
    print_success("en, en, fr")


@pytest.mark.asyncio
@pytest.mark.parametrize("saved", ["en", "fr", "es"])
async def test_a_row_saved_by_an_administrator_wins_even_when_it_says_english(engine, monkeypatch, saved):
    """CL-10-1c: the variable says ``it``; an administrator saves ``saved`` (``update_global_settings``): from then on the row wins, ``en`` included — the variable never overrides a choice. Barrier: before the save the variable did apply."""
    print_section(f"CL-10-1c: {VARIABLE}=it, then an administrator saves {saved!r}")
    monkeypatch.setenv(VARIABLE, "it")
    before = await _effective(engine)
    await _admin_saves(engine, saved)

    after = await _effective(engine)

    assert before == "it", f"Barrier: before any save the variable decides, got {before!r}"
    assert after == saved, f"an administrator saved {saved!r}: the row wins over {VARIABLE}=it, got {after!r}"
    print_success(f"{before!r} -> {after!r}")


@pytest.mark.asyncio
async def test_a_missing_row_gives_way_to_the_variable_and_to_the_default_without_it(engine, monkeypatch):
    """CL-10-1d: no ``default_language`` row at all: the variable's value; without the variable, English (the registry default), as today."""
    print_section("CL-10-1d: the row is missing")
    async with AsyncSession(engine) as session:
        await session.execute(delete(GlobalSetting).where(GlobalSetting.key == KEY))
        await session.commit()
    assert await _row(engine) is None, "Barrier: the row is gone"
    assert await _effective(engine) == "en", "no row, no variable: the registry default, en"

    monkeypatch.setenv(VARIABLE, "es")

    assert await _effective(engine) == "es", "no row: the variable decides"
    print_success("en without the variable, es with it")


@pytest.mark.asyncio
async def test_a_row_nobody_saved_is_untouched_whatever_it_says(engine, monkeypatch):
    """CL-10-1e: the rule is «never written by an administrator», not «still says en»: a row whose value is ``fr`` but whose ``updated_by_user_id`` is NULL (an old install, a restore) still gives way to the variable."""
    print_section("CL-10-1e: fr in the row, nobody behind it")
    async with AsyncSession(engine) as session:
        await session.execute(update(GlobalSetting).where(GlobalSetting.key == KEY).values(value="fr", updated_by_user_id=None))
        await session.commit()
    row = await _row(engine)
    assert row is not None and (row.value, row.updated_by_user_id) == ("fr", None), f"Barrier: the row says fr and has no author: {row!r}"
    monkeypatch.setenv(VARIABLE, "it")

    assert await _effective(engine) == "it", "no administrator wrote it: the variable decides, whatever the row says"
    print_success("it")


@pytest.mark.asyncio
async def test_the_variable_touches_no_other_setting(engine, monkeypatch):
    """CL-10-1f: ``default_currency`` and ``default_theme`` keep their rows' values with the variable set."""
    print_section("CL-10-1f: the other display defaults")
    async with AsyncSession(engine) as session:
        before = (await get_setting_value(session, CURRENCY_KEY, "?"), await get_setting_value(session, THEME_KEY, "?"))
    monkeypatch.setenv(VARIABLE, "it")
    async with AsyncSession(engine) as session:
        after = (await get_setting_value(session, CURRENCY_KEY, "?"), await get_setting_value(session, THEME_KEY, "?"))

    assert before == after == ("EUR", "auto"), f"the variable moves only default_language: {before} -> {after}"
    assert await _effective(engine) == "it", "Barrier: the variable is read for default_language"
    print_success("currency and theme unchanged")


# =============================================================================
# (1b) the readers the administrator's page uses
# =============================================================================


@pytest.mark.asyncio
async def test_the_readers_of_the_settings_page_show_the_effective_value(engine, monkeypatch):
    """CL-10-1g: ``get_global_setting`` and ``get_all_global_settings`` (what the administrator sees) show ``it`` while the row is untouched, and the row's own value once an administrator saved it; ``updated_by`` stays what the row says (None, then the administrator). Barrier: the row itself still says ``en`` while the variable applies."""
    print_section("CL-10-1g: settings_service readers")
    monkeypatch.setenv(VARIABLE, "it")
    await _seeded_row_is_untouched(engine)

    async with AsyncSession(engine) as session:
        single = await settings_service.get_global_setting(KEY, session)
        everything = {item.key: item for item in await settings_service.get_all_global_settings(session)}
    assert single is not None and KEY in everything, f"Barrier: the readers find the row: {single!r}"
    assert (single.value, everything[KEY].value) == ("it", "it"), f"untouched row: the readers show the effective value it, got {single.value!r} and {everything[KEY].value!r}"
    assert single.updated_by is None and everything[KEY].updated_by is None, "nobody saved it: updated_by stays empty"
    assert everything[CURRENCY_KEY].value == "EUR" and everything[THEME_KEY].value == "auto", "the other settings are shown as stored"

    await _admin_saves(engine, "en")

    async with AsyncSession(engine) as session:
        single = await settings_service.get_global_setting(KEY, session)
        everything = {item.key: item for item in await settings_service.get_all_global_settings(session)}
    assert single is not None and (single.value, everything[KEY].value) == ("en", "en"), f"saved by an administrator: the readers show their en, got {single!r}"
    assert single.updated_by is not None, "the administrator is recorded"
    print_success("it, then en")


# =============================================================================
# (2) the language of the emails
# =============================================================================


@pytest.mark.asyncio
async def test_emails_to_an_account_without_settings_and_to_a_guest_go_out_in_the_variables_language(engine, monkeypatch):
    """CL-10-2a: ``instance_language`` (the language of an email to someone without an account) and ``account_language`` for an account with no ``user_settings`` row follow the variable: an Italian customer's first emails are Italian. ``account_language`` creates no row."""
    print_section("CL-10-2a: instance_language / account_language follow the variable")
    user = await _add_user(engine, "mail")
    monkeypatch.setenv(VARIABLE, "it")

    async with AsyncSession(engine) as session:
        instance = await flows.instance_language(session)
        account = await flows.account_language(session, user.id)
    async with AsyncSession(engine) as session:
        rows = (await session.execute(select(UserSettings.user_id).where(UserSettings.user_id == user.id))).all()

    assert (instance, account) == ("it", "it"), f"{VARIABLE}=it, an untouched default: instance_language and account_language answer it, got {instance!r} and {account!r}"
    assert rows == [], "account_language creates nothing"
    print_success("it, it")


@pytest.mark.asyncio
async def test_an_accounts_own_language_and_an_administrators_choice_still_win_for_emails(engine, monkeypatch):
    """CL-10-2b: an account that chose French is written to in French; and once an administrator saved ``en`` as the instance default the settings-less account gets English, the variable notwithstanding. Barrier: before the save the same account got Italian."""
    print_section("CL-10-2b: own language, administrator's choice")
    chooser = await _add_user(engine, "chooser")
    plain = await _add_user(engine, "plain")
    async with AsyncSession(engine) as session:
        session.add(UserSettings(user_id=chooser.id, language="fr"))
        await session.commit()
    monkeypatch.setenv(VARIABLE, "it")

    async with AsyncSession(engine) as session:
        own = await flows.account_language(session, chooser.id)
        before = await flows.account_language(session, plain.id)
    await _admin_saves(engine, "en")
    async with AsyncSession(engine) as session:
        after = await flows.account_language(session, plain.id)
        guest = await flows.instance_language(session)

    assert own == "fr", f"an account's own language is its own: {own!r}"
    assert before == "it", f"Barrier: before any save the settings-less account is written to in the variable's language, got {before!r}"
    assert (after, guest) == ("en", "en"), f"after an administrator saved en the row wins over the variable: {after!r}, {guest!r}"
    print_success("fr own, it before, en after the save")


# =============================================================================
# (3) a new account's settings
# =============================================================================


@pytest.mark.asyncio
async def test_a_new_accounts_settings_are_seeded_with_the_variables_language(engine, monkeypatch):
    """CL-10-3: ``get_or_create_user_settings`` seeds a new account with ``it`` while the default is the variable's; an account created after an administrator saved ``fr`` starts in French; one created earlier keeps what it was given."""
    print_section("CL-10-3: get_or_create_user_settings")
    monkeypatch.setenv(VARIABLE, "it")
    first = await _add_user(engine, "first")
    second = await _add_user(engine, "second")

    async with AsyncSession(engine) as session:
        created_first = await settings_service.get_or_create_user_settings(first.id, session)
    await _admin_saves(engine, "fr")
    async with AsyncSession(engine) as session:
        created_second = await settings_service.get_or_create_user_settings(second.id, session)
        again_first = await settings_service.get_or_create_user_settings(first.id, session)

    assert created_first.language == "it", f"a new account starts in the variable's language, got {created_first.language!r}"
    assert created_second.language == "fr", f"after an administrator saved fr, a new account starts in fr, got {created_second.language!r}"
    assert again_first.language == "it", f"the first account keeps the language it was given, got {again_first.language!r}"
    print_success("it, fr, it")
