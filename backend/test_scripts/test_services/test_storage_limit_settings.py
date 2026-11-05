"""The limit of the storage bar (lot FB-29, contract ``B6r-fb29-interface`` §1, §2): ``LIBREFOLIO_STORAGE_LIMIT_MB`` and the
global setting ``storage_limit_mb``.

0 means no limit on a self-hosted instance. The setting is a global ``int``; the variable, when the operator sets it,
**wins and locks** the setting: its value is the one in force even over a row an administrator saved earlier, and a save
of the setting is refused. The measuring itself is ``test_storage_usage.py``'s.

(a) ``GLOBAL_SETTINGS_DEFAULTS["storage_limit_mb"]`` is an ``int`` defaulting to ``"0"`` with a description, in
    ``SETTINGS_REGISTRY.global_.STORAGE_LIMIT_MB``; a save accepts ``0`` to ``10485760`` (whole numbers, surrounding spaces
    dropped) and refuses the rest; the startup seeds the row with ``0``, written by nobody.
(b) The value in force (``effective_stored_value``, ``get_setting_value``, ``get_global_setting``,
    ``get_all_global_settings``): variable set and valid: always the variable's value, as an ``int`` in
    ``get_setting_value``, whatever the row says (seeded, or written by an administrator); ``0`` is a value too. Variable
    unset or blank: the row (0 when never written). Variable set but invalid: it pins nothing, the row speaks.
(c) ``update_global_settings`` of ``storage_limit_mb`` with the variable set (and not blank): ``GlobalSettingLockedError``
    naming the key and the variable, nothing written, nothing of the same save written either. Without the variable the
    save works.
(d) ``storage_limit_override_mb()`` of ``config/backup.py``: ``None`` when unset or blank; a whole number of ASCII digits
    (0 included, surrounding spaces dropped, as ``backup_max_upload_mb()`` does) otherwise; anything else raises
    ``BackupConfigError`` (a ``ValueError``) with ``variable`` = the variable and ``code`` = ``STORAGE_LIMIT_MB_INVALID``,
    the message never quoting the value.

How: as ``test_backup_cleanup_settings.py`` (a private SQLite file under ``tmp_path`` with the whole ORM schema and the
seeded global settings; its fixtures are reused). Isolation: pure. No lane database, no server, no network.

Not tested, the contract is silent: a save while the variable is set but *invalid* (the reader of the lock is the
operator's, ``registration_mode`` locks on any non-blank value).
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import backup as backup_config
from backend.app.schemas.settings import GLOBAL_SETTINGS_DEFAULTS, SETTINGS_REGISTRY, validate_global_setting_value
from backend.app.services.accounts import settings_service
from backend.app.services.accounts.global_settings_service import effective_stored_value
from backend.app.services.accounts.settings_service import GlobalSettingLockedError
from backend.test_scripts.test_services import test_backup_cleanup_settings as sibling
from backend.test_scripts.test_utils import print_section, print_success

# The fixtures and helpers of the sibling suite (a private database with the seeded settings).
database = sibling.database
engine = sibling.engine
_add_admin = sibling._add_admin
_effective = sibling._effective
_listed = sibling._listed
_row = sibling._row
_save = sibling._save

VARIABLE = "LIBREFOLIO_STORAGE_LIMIT_MB"
PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
KEY = "storage_limit_mb"
LARGEST = 10485760
OTHER_KEY = "backup_cleanup_max_days"


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Self-hosted, and the variable unset unless the test sets it."""
    monkeypatch.setenv(PROFILE_VARIABLE, "selfhosted")
    monkeypatch.delenv(VARIABLE, raising=False)


def pin(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    monkeypatch.setenv(VARIABLE, text)


# =============================================================================
# (a) the setting, its default and its constraint
# =============================================================================


def test_the_setting_is_an_integer_that_defaults_to_zero():
    entry = GLOBAL_SETTINGS_DEFAULTS.get(KEY)
    assert entry is not None, f"red until FB-29: GLOBAL_SETTINGS_DEFAULTS has no {KEY}"
    assert (entry["value"], entry["type"]) == ("0", "int"), f"{KEY} is an int whose default is 0: {entry}"
    assert entry["description"], "and it says what it is"


def test_the_setting_is_in_the_registry():
    spec = getattr(SETTINGS_REGISTRY.global_, "STORAGE_LIMIT_MB", None)
    assert spec is not None, "red until FB-29: SETTINGS_REGISTRY.global_ has no STORAGE_LIMIT_MB"
    assert spec.key == KEY


def test_a_save_accepts_zero_to_ten_million_and_nothing_else():
    """(a) ``0..10485760`` MB, whole numbers, spaces dropped, over the real validator."""
    for text, stored in (("0", "0"), ("1", "1"), (" 250 ", "250"), (str(LARGEST), str(LARGEST))):
        assert validate_global_setting_value(KEY, text, "int") == stored, f"{text!r} is accepted as {stored}"
    for text in ("-1", str(LARGEST + 1), "abc", "1.5", "", "1e3", "0x10"):
        with pytest.raises(ValueError):
            validate_global_setting_value(KEY, text, "int")


@pytest.mark.asyncio
async def test_the_startup_seeds_the_row_with_zero_and_no_author(engine):
    row = await _row(engine, KEY)
    assert row is not None, f"red until FB-29: the startup seeds no {KEY} row"
    assert (row.value, row.value_type, row.updated_by_user_id) == ("0", "int", None), f"the seeded row: {row!r}"


# =============================================================================
# (b) the value in force
# =============================================================================


@pytest.mark.asyncio
async def test_without_the_variable_the_row_is_the_value_as_an_integer(engine):
    value = await _effective(engine, KEY)
    assert value == 0 and type(value) is int, f"seeded: 0 as an int, got {value!r}"
    await _save(engine, (KEY, "100"))
    value = await _effective(engine, KEY)
    assert value == 100 and type(value) is int, f"an administrator saved 100: {value!r}"
    assert (await _listed(engine))[KEY] == "100", "and GET /settings/global says the same"


@pytest.mark.asyncio
async def test_the_variable_is_the_value_in_force_as_an_integer(engine, monkeypatch):
    """(b) Seeded row, no row, and the single-setting and list readers: 250."""
    print_section("variable set: 250")
    pin(monkeypatch, "250")
    value = await _effective(engine, KEY)
    assert value == 250 and type(value) is int, f"the variable's value as an int: {value!r}"
    assert str((await _listed(engine))[KEY]) == "250", "the list of settings (GET /settings/global) says 250"
    async with AsyncSession(engine) as session:
        single = await settings_service.get_global_setting(KEY, session)
    assert single is not None and str(single.value) == "250", f"and so does the setting read alone: {single}"
    print_success("250 everywhere")


@pytest.mark.asyncio
@pytest.mark.parametrize(("text", "expected"), [("250", 250), ("0", 0), (" 40 ", 40)])
async def test_the_variable_wins_even_over_a_row_an_administrator_saved(engine, monkeypatch, text, expected):
    """(b) Saved before the variable was set: the row says 100, the variable says what it says (0 included)."""
    await _save(engine, (KEY, "100"))
    row = await _row(engine, KEY)
    assert row is not None and row.updated_by_user_id is not None, "premise: an administrator wrote 100"
    pin(monkeypatch, text)
    value = await _effective(engine, KEY)
    assert value == expected and type(value) is int, f"the variable {text!r} wins over the saved 100: {value!r}"
    assert str((await _listed(engine))[KEY]) == str(expected), "and the list says it"
    assert (await _row(engine, KEY)).value == "100", "the row itself is left as it was"


@pytest.mark.parametrize("text", ["250", "0", " 250 "])
def test_effective_stored_value_is_the_variable_for_every_kind_of_row(monkeypatch, text):
    """(b) Missing row, a row nobody wrote, a row an administrator wrote: the variable's value, as text."""
    pin(monkeypatch, text)
    from backend.app.db.models import GlobalSetting  # noqa: PLC0415

    seeded = GlobalSetting(key=KEY, value="0", value_type="int", description="", updated_by_user_id=None)
    written = GlobalSetting(key=KEY, value="7", value_type="int", description="", updated_by_user_id=1)
    expected = str(int(text))
    assert str(effective_stored_value(KEY, None)) == expected, "no row"
    assert str(effective_stored_value(KEY, seeded)) == expected, "a row nobody wrote"
    assert str(effective_stored_value(KEY, written)) == expected, "a row an administrator wrote: the variable still wins"


@pytest.mark.parametrize("text", [None, "", "   "])
def test_effective_stored_value_pins_nothing_without_a_usable_variable_unset_or_blank(monkeypatch, text):
    if text is not None:
        pin(monkeypatch, text)
    from backend.app.db.models import GlobalSetting  # noqa: PLC0415

    written = GlobalSetting(key=KEY, value="7", value_type="int", description="", updated_by_user_id=1)
    assert effective_stored_value(KEY, None) is None and effective_stored_value(KEY, written) is None


@pytest.mark.parametrize("text", ["abc", "-1", "1.5", "１２", "250MB"])
def test_an_invalid_variable_pins_nothing(monkeypatch, text):
    pin(monkeypatch, text)
    from backend.app.db.models import GlobalSetting  # noqa: PLC0415

    seeded = GlobalSetting(key=KEY, value="0", value_type="int", description="", updated_by_user_id=None)
    written = GlobalSetting(key=KEY, value="7", value_type="int", description="", updated_by_user_id=1)
    assert [effective_stored_value(KEY, row) for row in (None, seeded, written)] == [None, None, None]


@pytest.mark.asyncio
async def test_an_invalid_variable_leaves_the_row_in_force(engine, monkeypatch):
    pin(monkeypatch, "abc")
    assert await _effective(engine, KEY) == 0, "the seeded row"
    await _save(engine, (KEY, "100"))
    assert await _effective(engine, KEY) == 100, "the administrator's row"


@pytest.mark.asyncio
async def test_a_blank_variable_leaves_the_row_in_force(engine, monkeypatch):
    pin(monkeypatch, "  ")
    await _save(engine, (KEY, "100"))
    assert await _effective(engine, KEY) == 100


# =============================================================================
# (c) what a save does with the variable set
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["250", "0"])
async def test_a_save_is_refused_while_the_variable_is_set_and_writes_nothing(engine, monkeypatch, text):
    """(c) ``GlobalSettingLockedError`` naming the key and the variable; the row, and the other setting of the same save,
    as they were."""
    print_section(f"locked by {VARIABLE}={text}")
    pin(monkeypatch, text)
    admin = await _add_admin(engine)
    async with AsyncSession(engine) as session:
        with pytest.raises(GlobalSettingLockedError) as refused:
            await settings_service.update_global_settings([(KEY, "100"), (OTHER_KEY, "7")], admin.id, session)
    assert refused.value.key == KEY and refused.value.variable == VARIABLE, f"the key and the variable: {refused.value.key!r}, {refused.value.variable!r}"
    assert VARIABLE in str(refused.value), "the message names the variable too"
    for key in (KEY, OTHER_KEY):
        row = await _row(engine, key)
        assert row is not None and (row.value, row.updated_by_user_id) == ("0", None), f"{key} was not written: {row!r}"
    print_success("refused, nothing written")


@pytest.mark.asyncio
async def test_the_other_settings_still_save_with_the_variable_set(engine, monkeypatch):
    pin(monkeypatch, "250")
    await _save(engine, (OTHER_KEY, "7"))
    assert await _effective(engine, OTHER_KEY) == 7


@pytest.mark.asyncio
@pytest.mark.parametrize("text", [None, "", "   "])
async def test_without_the_variable_a_save_works(engine, monkeypatch, text):
    if text is not None:
        pin(monkeypatch, text)
    written = await _save(engine, (KEY, "100"))
    assert [(item.key, str(item.value)) for item in written] == [(KEY, "100")], f"saved: {written}"
    assert await _effective(engine, KEY) == 100


# =============================================================================
# (d) the reader of the variable
# =============================================================================


def reader():
    """``storage_limit_override_mb``; absent, the test is red with this reason."""
    function = getattr(backup_config, "storage_limit_override_mb", None)
    if function is None:
        pytest.fail("[new] backend.app.config.backup.storage_limit_override_mb does not exist yet: lot FB-29 brings it (§1)", pytrace=False)
    return function


def test_the_variable_has_its_name():
    assert getattr(backup_config, "STORAGE_LIMIT_VARIABLE", None) == VARIABLE, "red until FB-29: config/backup.py has no STORAGE_LIMIT_VARIABLE"


@pytest.mark.parametrize("text", [None, "", "   ", "\t"])
def test_unset_or_blank_is_none(monkeypatch, text):
    if text is not None:
        pin(monkeypatch, text)
    assert reader()() is None


@pytest.mark.parametrize(("text", "expected"), [("0", 0), ("250", 250), (" 250 ", 250), ("10485760", 10485760), ("007", 7)])
def test_a_whole_number_of_ascii_digits_is_taken_as_an_int(monkeypatch, text, expected):
    pin(monkeypatch, text)
    value = reader()()
    assert value == expected and type(value) is int


def test_unset_is_none_in_the_managed_profile_too(monkeypatch):
    """(d) The reader has no profile default: a managed instance without the variable has no pin."""
    monkeypatch.setenv(PROFILE_VARIABLE, "managed")
    assert reader()() is None


@pytest.mark.parametrize("text", ["abc", "-1", "+5", "1.5", "1e3", "0x10", "250MB", "２５０", "１２", "1 000", "--"])
def test_anything_else_raises_a_backup_config_error_that_does_not_quote_the_value(monkeypatch, text):
    pin(monkeypatch, text)
    with pytest.raises(backup_config.BackupConfigError) as refused:
        reader()()
    error = refused.value
    assert isinstance(error, ValueError), "a BackupConfigError is a ValueError"
    assert (error.variable, error.code) == (VARIABLE, "STORAGE_LIMIT_MB_INVALID"), f"the variable and the code: {error.variable!r}, {error.code!r}"
    assert VARIABLE in str(error), "the message names the variable"
    assert text.strip() not in str(error), "and never quotes the value"
