"""``LIBREFOLIO_DEFAULT_CURRENCY`` and ``LIBREFOLIO_DEFAULT_TIMEZONE``: the instance defaults before an administrator chose them (release 2.0, workstream H, checkpoint 1, lot CL-13).

Same rule as ``LIBREFOLIO_DEFAULT_LANGUAGE`` (CL-10, ``test_default_language_variable.py``), now for three keys:

| Variable | Reader | Valid | Sets the global setting |
|---|---|---|---|
| ``LIBREFOLIO_DEFAULT_CURRENCY`` | ``accounts.default_currency()`` | an ISO 4217 code, any case, returned upper-case | ``default_currency`` |
| ``LIBREFOLIO_DEFAULT_TIMEZONE`` | ``accounts.default_timezone()`` | an IANA name the server resolves | ``scheduler_timezone`` |

- The readers: unset or blank gives ``None``; surrounding spaces are stripped; the SAME check as the setting (the one of
  ``validate_global_setting_value``); anything else is a ``ValueError`` naming the variable (the startup audit stops on it:
  pinned in ``test_accounts_checks.py``).
- The rule: a variable is the value of its key **only while no administrator ever wrote the setting**: the row is missing,
  or its ``updated_by_user_id`` is NULL (the seeded row). Once an administrator saved it the row wins, even when it equals
  the default again. ``effective_stored_value`` applies the rule per key; a key without a variable (``default_theme``,
  ``session_ttl_hours``) is untouched, and an administrator's save of one key does not release another.
- Where it shows: ``get_setting_value`` (so the scheduler and a new account's currency), ``get_global_setting`` and
  ``get_all_global_settings`` (what the administrator sees in Settings; ``GET /api/v1/settings/global`` is a thin wrapper of
  the latter and CL-10 has no API pin, so these are service-level too).

How: a private SQLite file under ``tmp_path`` with the whole ORM schema and the seeded global settings; the variables set
through ``monkeypatch``. Isolation: pure. No lane database, no server, no network, no clock.

Red today: the readers do not exist, and ``effective_stored_value`` knows only ``default_language``, so every case that
expects the variable's value reads the row's seeded one.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.config import accounts
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import GlobalSetting, User
from backend.app.schemas.settings import SETTINGS_REGISTRY
from backend.app.services.accounts import settings_service
from backend.app.services.accounts.global_settings_service import get_setting_value
from backend.app.services.platform.scheduler import settings as scheduler_settings
from backend.test_scripts.test_utils import print_section, print_success

CURRENCY_VARIABLE = "LIBREFOLIO_DEFAULT_CURRENCY"
TIMEZONE_VARIABLE = "LIBREFOLIO_DEFAULT_TIMEZONE"
LANGUAGE_VARIABLE = "LIBREFOLIO_DEFAULT_LANGUAGE"
CURRENCY_KEY = SETTINGS_REGISTRY.global_.DEFAULT_CURRENCY.key
TIMEZONE_KEY = SETTINGS_REGISTRY.global_.SCHEDULER_TIMEZONE.key
LANGUAGE_KEY = SETTINGS_REGISTRY.global_.DEFAULT_LANGUAGE.key
THEME_KEY = SETTINGS_REGISTRY.global_.DEFAULT_THEME.key
TTL_KEY = SETTINGS_REGISTRY.global_.SESSION_TTL_HOURS.key


@dataclass(frozen=True)
class Case:
    """One variable and what it stands for."""

    variable: str
    constant: str  # the name of the module constant that holds the variable name
    reader: str  # the name of the reader in backend.app.config.accounts
    key: str  # the global setting it sets
    seeded: str  # what the startup seeding writes in the row
    value: str  # a valid value, as the reader returns it
    other: str  # another valid value, different from the seeded one and from ``value``
    padded: tuple[str, str]  # (raw, expected) with surrounding spaces and, for the currency, lower-case
    invalid: tuple[str, ...]


CURRENCY = Case(
    variable=CURRENCY_VARIABLE,
    constant="DEFAULT_CURRENCY_VARIABLE",
    reader="default_currency",
    key=CURRENCY_KEY,
    seeded="EUR",
    value="USD",
    other="GBP",
    padded=("  usd\t", "USD"),
    invalid=("EURO", "XXXX", "E", "12", "e u r", "US-D"),
)
TIMEZONE = Case(
    variable=TIMEZONE_VARIABLE,
    constant="DEFAULT_TIMEZONE_VARIABLE",
    reader="default_timezone",
    key=TIMEZONE_KEY,
    seeded="UTC",
    value="Europe/Rome",
    other="America/New_York",
    padded=(" Europe/Rome ", "Europe/Rome"),
    invalid=("Mars/Olympus", "Rome", "Europe/Rome Italy", "1", "Europe/"),
)
CASES = [pytest.param(CURRENCY, id="currency"), pytest.param(TIMEZONE, id="timezone")]


@pytest.fixture(autouse=True)
def _no_inherited_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """A test sees only the values it sets itself."""
    for name in (CURRENCY_VARIABLE, TIMEZONE_VARIABLE, LANGUAGE_VARIABLE):
        monkeypatch.delenv(name, raising=False)


def _reader(case: Case) -> Any:
    """The reader of ``case`` in ``backend.app.config.accounts``, or a red of CL-13 while it is not there."""
    reader = getattr(accounts, case.reader, None)
    if reader is None:
        pytest.fail(f"red until CL-13: backend.app.config.accounts has no {case.reader}", pytrace=False)
    return reader


def _set_or_unset(monkeypatch: pytest.MonkeyPatch, name: str, raw: str | None) -> None:
    if raw is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, raw)


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file with the whole ORM schema and the default global settings (``updated_by_user_id`` NULL everywhere)."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'default_currency_timezone.db'}", poolclass=NullPool)
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
    username = f"cl13_{label}_{uuid4().hex[:8]}"
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=f"{username}@example.com", hashed_password="marker-hash-not-bcrypt", is_active=True)
        session.add(user)
        await session.commit()
    return user


async def _admin_saves(engine: AsyncEngine, key: str, value: str) -> None:
    """An administrator saves ``key`` through the service the API uses (``update_global_settings``), which records who."""
    admin = await _add_user(engine, "admin")
    async with AsyncSession(engine) as session:
        written = await settings_service.update_global_settings([(key, value)], admin.id, session)
    assert [(item.key, item.value, item.updated_by) for item in written] == [(key, value, admin.id)], f"Barrier: the administrator's save is recorded with their id: {written}"


async def _row(engine: AsyncEngine, key: str) -> GlobalSetting | None:
    async with AsyncSession(engine) as session:
        return (await session.execute(select(GlobalSetting).where(GlobalSetting.key == key))).scalar_one_or_none()


async def _effective(engine: AsyncEngine, key: str) -> Any:
    async with AsyncSession(engine) as session:
        return await get_setting_value(session, key, "?")


async def _seeded_row_is_untouched(engine: AsyncEngine, case: Case) -> None:
    """Barrier: the row is the one the startup seeding wrote, with no administrator behind it."""
    row = await _row(engine, case.key)
    assert row is not None and (row.value, row.updated_by_user_id) == (case.seeded, None), f"Barrier: the seeded {case.key} says {case.seeded!r} and was never saved by an administrator: {row!r}"


# =============================================================================
# (0) the readers
# =============================================================================


@pytest.mark.parametrize("case", CASES)
def test_the_variable_names_are_exported_as_constants(case: Case) -> None:
    """CL-13-0a: ``accounts`` exports the variable's name as a constant, as ``DEFAULT_LANGUAGE_VARIABLE``."""
    assert getattr(accounts, case.constant, None) == case.variable, f"red until CL-13: accounts.{case.constant} must be {case.variable!r}"


@pytest.mark.parametrize("raw", [None, "", "   ", "\t \n"], ids=["unset", "empty", "blank", "whitespace"])
@pytest.mark.parametrize("case", CASES)
def test_the_reader_gives_nothing_when_unset_or_blank(monkeypatch: pytest.MonkeyPatch, case: Case, raw: str | None) -> None:
    """CL-13-0b: unset, empty or blank: ``None``, no effect."""
    reader = _reader(case)
    _set_or_unset(monkeypatch, case.variable, raw)

    value = reader()

    assert value is None, f"{case.variable}={raw!r} must give None, got {value!r}"


@pytest.mark.parametrize("case", CASES)
def test_the_reader_gives_the_valid_value(monkeypatch: pytest.MonkeyPatch, case: Case) -> None:
    """CL-13-0c: a valid value comes back as the setting would store it."""
    reader = _reader(case)
    monkeypatch.setenv(case.variable, case.value)

    value = reader()

    assert value == case.value and type(value) is str, f"{case.variable}={case.value!r} must give {case.value!r}, got {value!r}"


@pytest.mark.parametrize("case", CASES)
def test_the_reader_strips_and_normalises(monkeypatch: pytest.MonkeyPatch, case: Case) -> None:
    """CL-13-0d: surrounding spaces are stripped; a currency in lower case comes back upper-case (the setting's own normalisation)."""
    reader = _reader(case)
    raw, expected = case.padded
    monkeypatch.setenv(case.variable, raw)

    value = reader()

    assert value == expected, f"{case.variable}={raw!r} must give {expected!r}, got {value!r}"


@pytest.mark.parametrize("raw", ["eur", "Eur", "eUr"])
def test_the_currency_is_accepted_in_any_case_and_returned_upper_case(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    """CL-13-0e: ``eur`` is ``EUR``: the check of the setting accepts any case."""
    reader = _reader(CURRENCY)
    monkeypatch.setenv(CURRENCY_VARIABLE, raw)

    assert reader() == "EUR"


@pytest.mark.parametrize(
    ("case", "raw"),
    [pytest.param(case, raw, id=f"{case.reader}-{raw!r}") for case in (CURRENCY, TIMEZONE) for raw in case.invalid],
)
def test_the_reader_refuses_an_unusable_value_naming_the_variable(monkeypatch: pytest.MonkeyPatch, case: Case, raw: str) -> None:
    """CL-13-0f: a value the setting would refuse is a ``ValueError`` naming the variable and the value, never a fallback."""
    reader = _reader(case)
    monkeypatch.setenv(case.variable, raw)

    with pytest.raises(ValueError) as refused:
        reader()

    assert case.variable in str(refused.value), f"the error must name {case.variable}: {refused.value!r}"
    assert raw.strip() in str(refused.value), f"the error should show the value {raw!r}: {refused.value!r}"


# =============================================================================
# (1) get_setting_value: the variable while no administrator wrote the row
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES)
async def test_an_untouched_row_gives_way_to_the_variable(engine, monkeypatch, case: Case):
    """CL-13-1a: the seeded row (nobody saved it) and the variable set: ``get_setting_value`` answers the variable's value, normalised (spaces stripped, currency upper-case)."""
    print_section(f"CL-13-1a: {case.variable}, the seeded row")
    await _seeded_row_is_untouched(engine, case)
    raw, expected = case.padded
    monkeypatch.setenv(case.variable, raw)

    value = await _effective(engine, case.key)

    assert value == expected, f"{case.variable}={raw!r} over an untouched row: the effective {case.key} is {expected!r}, got {value!r}"
    print_success(f"{raw!r}: {value!r}")


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES)
async def test_without_the_variable_the_row_is_the_answer(engine, monkeypatch, case: Case):
    """CL-13-1b: the variable unset (or blank): the row's value, as ever; a row an administrator wrote is read as written. Control of the cases around it."""
    await _seeded_row_is_untouched(engine, case)
    assert await _effective(engine, case.key) == case.seeded, "the seeded row, no variable"
    monkeypatch.setenv(case.variable, "   ")
    assert await _effective(engine, case.key) == case.seeded, "a blank variable counts as unset"
    monkeypatch.delenv(case.variable)
    await _admin_saves(engine, case.key, case.other)
    assert await _effective(engine, case.key) == case.other, "an administrator's choice, no variable"


@pytest.mark.asyncio
@pytest.mark.parametrize("save_kind", ["same-as-default", "different"])
@pytest.mark.parametrize("case", CASES)
async def test_a_row_saved_by_an_administrator_wins_even_when_it_equals_the_default(engine, monkeypatch, case: Case, save_kind: str):
    """CL-13-1c: the variable says one thing; an administrator saves the seeded default again, or another value: from then on the row wins. Barrier: before the save the variable did apply."""
    saved = case.seeded if save_kind == "same-as-default" else case.other
    print_section(f"CL-13-1c: {case.variable}={case.value}, then an administrator saves {saved!r}")
    monkeypatch.setenv(case.variable, case.value)
    before = await _effective(engine, case.key)
    await _admin_saves(engine, case.key, saved)

    after = await _effective(engine, case.key)

    assert before == case.value, f"Barrier: before any save the variable decides, got {before!r}"
    assert after == saved, f"an administrator saved {saved!r}: the row wins over {case.variable}={case.value}, got {after!r}"
    print_success(f"{before!r} -> {after!r}")


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES)
async def test_a_missing_row_gives_way_to_the_variable_and_to_the_default_without_it(engine, monkeypatch, case: Case):
    """CL-13-1d: no row at all: the variable's value; without the variable, the registry default, as today."""
    async with AsyncSession(engine) as session:
        await session.execute(delete(GlobalSetting).where(GlobalSetting.key == case.key))
        await session.commit()
    assert await _row(engine, case.key) is None, "Barrier: the row is gone"
    assert await _effective(engine, case.key) == case.seeded, "no row, no variable: the registry default"

    monkeypatch.setenv(case.variable, case.value)

    assert await _effective(engine, case.key) == case.value, "no row: the variable decides"


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES)
async def test_a_row_nobody_saved_gives_way_whatever_it_says(engine, monkeypatch, case: Case):
    """CL-13-1e: the rule is «never written by an administrator», not «still says the default»: a row with another value but no ``updated_by_user_id`` (an old install, a restore) still gives way."""
    async with AsyncSession(engine) as session:
        await session.execute(update(GlobalSetting).where(GlobalSetting.key == case.key).values(value=case.other, updated_by_user_id=None))
        await session.commit()
    row = await _row(engine, case.key)
    assert row is not None and (row.value, row.updated_by_user_id) == (case.other, None), f"Barrier: the row says {case.other!r} and has no author: {row!r}"
    monkeypatch.setenv(case.variable, case.value)

    assert await _effective(engine, case.key) == case.value, "no administrator wrote it: the variable decides, whatever the row says"


@pytest.mark.asyncio
async def test_the_three_keys_follow_their_own_variable_independently(engine, monkeypatch):
    """CL-13-1f: the rule is per key: the three variables set, an administrator saves ``default_language`` only: language is the row's, currency and timezone still the variables'. Then the administrator saves the currency: the timezone still follows its variable."""
    print_section("CL-13-1f: per-key rule")
    monkeypatch.setenv(LANGUAGE_VARIABLE, "it")
    monkeypatch.setenv(CURRENCY_VARIABLE, "USD")
    monkeypatch.setenv(TIMEZONE_VARIABLE, "Europe/Rome")
    assert [await _effective(engine, key) for key in (LANGUAGE_KEY, CURRENCY_KEY, TIMEZONE_KEY)] == ["it", "USD", "Europe/Rome"], "Barrier: the three variables apply to untouched rows"

    await _admin_saves(engine, LANGUAGE_KEY, "fr")
    assert [await _effective(engine, key) for key in (LANGUAGE_KEY, CURRENCY_KEY, TIMEZONE_KEY)] == ["fr", "USD", "Europe/Rome"], "the language save releases only the language"

    await _admin_saves(engine, CURRENCY_KEY, "GBP")
    assert [await _effective(engine, key) for key in (LANGUAGE_KEY, CURRENCY_KEY, TIMEZONE_KEY)] == ["fr", "GBP", "Europe/Rome"], "the currency save releases only the currency"
    print_success("fr / GBP / Europe/Rome")


@pytest.mark.asyncio
async def test_the_variables_touch_no_other_setting(engine, monkeypatch):
    """CL-13-1g: ``default_theme`` and ``session_ttl_hours`` keep their rows' values with both variables set; ``default_language`` is moved by its own variable only."""
    async with AsyncSession(engine) as session:
        before = (await get_setting_value(session, THEME_KEY, "?"), await get_setting_value(session, TTL_KEY, "?"), await get_setting_value(session, LANGUAGE_KEY, "?"))
    monkeypatch.setenv(CURRENCY_VARIABLE, "USD")
    monkeypatch.setenv(TIMEZONE_VARIABLE, "Europe/Rome")
    async with AsyncSession(engine) as session:
        after = (await get_setting_value(session, THEME_KEY, "?"), await get_setting_value(session, TTL_KEY, "?"), await get_setting_value(session, LANGUAGE_KEY, "?"))

    assert before == after, f"the variables move only their own keys: {before} -> {after}"
    assert await _effective(engine, CURRENCY_KEY) == "USD" and await _effective(engine, TIMEZONE_KEY) == "Europe/Rome", "Barrier: the variables are read for their keys"


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES)
async def test_an_unusable_variable_at_read_time_stands_for_nothing(engine, monkeypatch, case: Case):
    """CL-13-1h: an unusable variable is the audit's to stop at the start; ``get_setting_value`` and both readers of the settings page still answer the row's value, without raising."""
    monkeypatch.setenv(case.variable, case.invalid[0])

    assert await _effective(engine, case.key) == case.seeded, "an unusable variable stands for nothing: the row's value"
    async with AsyncSession(engine) as session:
        single = await settings_service.get_global_setting(case.key, session)
        everything = {item.key: item for item in await settings_service.get_all_global_settings(session)}
    assert single is not None and single.value == case.seeded and everything[case.key].value == case.seeded


# =============================================================================
# (1b) the readers the administrator's page uses
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES)
async def test_the_readers_of_the_settings_page_show_the_effective_value(engine, monkeypatch, case: Case):
    """CL-13-2: ``get_global_setting`` and ``get_all_global_settings`` (what the administrator sees) show the variable's value while the row is untouched, and the row's own value once an administrator saved it (the default again included); ``updated_by`` stays what the row says. The other settings are shown as stored."""
    print_section(f"CL-13-2: settings_service readers, {case.variable}")
    monkeypatch.setenv(case.variable, case.value)
    await _seeded_row_is_untouched(engine, case)

    async with AsyncSession(engine) as session:
        single = await settings_service.get_global_setting(case.key, session)
        everything = {item.key: item for item in await settings_service.get_all_global_settings(session)}
    assert single is not None and case.key in everything, f"Barrier: the readers find the row: {single!r}"
    assert (single.value, everything[case.key].value) == (case.value, case.value), f"untouched row: the readers show the effective value {case.value!r}, got {single.value!r} and {everything[case.key].value!r}"
    assert single.updated_by is None and everything[case.key].updated_by is None, "nobody saved it: updated_by stays empty"
    assert everything[THEME_KEY].value == "auto", "the other settings are shown as stored"

    await _admin_saves(engine, case.key, case.seeded)

    async with AsyncSession(engine) as session:
        single = await settings_service.get_global_setting(case.key, session)
        everything = {item.key: item for item in await settings_service.get_all_global_settings(session)}
    assert single is not None and (single.value, everything[case.key].value) == (case.seeded, case.seeded), f"saved by an administrator: the readers show their value, got {single!r}"
    assert single.updated_by is not None, "the administrator is recorded"
    print_success(f"{case.value}, then {case.seeded}")


# =============================================================================
# (2) the scheduler
# =============================================================================


@pytest.mark.asyncio
async def test_the_scheduler_works_in_the_variables_timezone_until_an_administrator_saves_one(engine, monkeypatch):
    """CL-13-3: ``load_scheduler_settings().scheduler_timezone`` is the variable's while the row is untouched, the administrator's once saved (UTC again included). Barrier: without the variable it is the seeded UTC."""
    print_section("CL-13-3: load_scheduler_settings")
    monkeypatch.setattr(scheduler_settings, "get_async_engine", lambda: engine)
    assert (await scheduler_settings.load_scheduler_settings()).scheduler_timezone == "UTC", "Barrier: seeded UTC, no variable"

    monkeypatch.setenv(TIMEZONE_VARIABLE, " Europe/Rome ")
    assert (await scheduler_settings.load_scheduler_settings()).scheduler_timezone == "Europe/Rome", "the scheduler follows the variable"

    await _admin_saves(engine, TIMEZONE_KEY, "UTC")
    assert (await scheduler_settings.load_scheduler_settings()).scheduler_timezone == "UTC", "an administrator saved UTC: the row wins over the variable"

    await _admin_saves(engine, TIMEZONE_KEY, "America/New_York")
    assert (await scheduler_settings.load_scheduler_settings()).scheduler_timezone == "America/New_York", "an administrator saved another timezone: the row wins"
    print_success("UTC, Europe/Rome, UTC, America/New_York")


# =============================================================================
# (3) a new account's currency
# =============================================================================


@pytest.mark.asyncio
async def test_a_new_accounts_currency_is_seeded_with_the_variable(engine, monkeypatch):
    """CL-13-4a: ``get_or_create_user_settings`` seeds a new account's ``base_currency`` from ``default_currency`` (verified in the code): the variable's while untouched, the administrator's after a save; an account created earlier keeps what it was given."""
    print_section("CL-13-4a: get_or_create_user_settings")
    monkeypatch.setenv(CURRENCY_VARIABLE, "usd")
    first = await _add_user(engine, "first")
    second = await _add_user(engine, "second")

    async with AsyncSession(engine) as session:
        created_first = await settings_service.get_or_create_user_settings(first.id, session)
    await _admin_saves(engine, CURRENCY_KEY, "GBP")
    async with AsyncSession(engine) as session:
        created_second = await settings_service.get_or_create_user_settings(second.id, session)
        again_first = await settings_service.get_or_create_user_settings(first.id, session)

    assert created_first.base_currency == "USD", f"a new account starts in the variable's currency, upper-case, got {created_first.base_currency!r}"
    assert created_second.base_currency == "GBP", f"after an administrator saved GBP, a new account starts in GBP, got {created_second.base_currency!r}"
    assert again_first.base_currency == "USD", f"the first account keeps the currency it was given, got {again_first.base_currency!r}"
    print_success("USD, GBP, USD")


@pytest.mark.asyncio
async def test_an_administrators_save_of_the_default_currency_wins_for_a_new_account_even_when_it_says_the_default(engine, monkeypatch):
    """CL-13-4b: the administrator saves EUR (the seeded default) while the variable says USD: a new account starts in EUR."""
    monkeypatch.setenv(CURRENCY_VARIABLE, "USD")
    user = await _add_user(engine, "eur")
    await _admin_saves(engine, CURRENCY_KEY, "EUR")

    async with AsyncSession(engine) as session:
        created = await settings_service.get_or_create_user_settings(user.id, session)

    assert created.base_currency == "EUR", f"the administrator's EUR wins over the variable, got {created.base_currency!r}"


@pytest.mark.asyncio
async def test_the_effective_base_currency_and_a_first_profile_update_follow_the_variable(engine, monkeypatch):
    """CL-13-4c: an account without a settings row has the variable's currency as its effective base currency (``get_effective_base_currency``), and a profile update that names no currency creates the row with it (``update_user_settings``)."""
    monkeypatch.setenv(CURRENCY_VARIABLE, "CHF")
    reader = await _add_user(engine, "reader")
    updater = await _add_user(engine, "updater")

    async with AsyncSession(engine) as session:
        effective = await settings_service.get_effective_base_currency(session, reader.id)
        created = await settings_service.update_user_settings(updater.id, settings_service.UserSettingsUpdate(theme="dark"), session)

    assert effective == "CHF", f"no settings row: the variable's currency, got {effective!r}"
    assert created.base_currency == "CHF", f"the row created by a profile update starts in the variable's currency, got {created.base_currency!r}"
