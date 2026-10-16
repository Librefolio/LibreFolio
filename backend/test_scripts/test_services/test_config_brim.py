"""
The BRIM section of the configuration: ``LIBREFOLIO_BRIM_PREWARM`` (W-B53, design change N56).

Under test: ``backend/app/config/brim.py`` (owner W). Starting the BRIM parse pool's forkserver at startup — preloaded with
the BRIM module and its plugins, so that the first parse after a start forks a ready worker (W-B53) — is opt-in.
``brim_prewarm_enabled()`` reads the variable when it is called, never at import:

- unset or blank: ``is_test_mode()`` decides: a test server warms up, an install does not;
- ``1``, ``true``, ``yes``, ``on``: on; ``0``, ``false``, ``no``, ``off``: off — in any case, stripped, whatever the mode;
- anything else raises ``BrimConfigError``, a ``ValueError`` carrying the variable's name in ``.variable``. The startup step
  logs it and starts nothing (``test_app_lifecycle.py``).

The test mode is read only through ``backend.app.config.is_test_mode()``. Each case sets ``LIBREFOLIO_TEST_MODE`` as its
input and checks its premise through ``is_test_mode()`` (a barrier: the case runs in the mode it names), never by reading
the variable again. Each word is checked against the mode that would give the other answer by default — an "on" word in
production, an "off" word in test mode — so the answer can only come from the variable. Production is checked both ways
it can look: ``LIBREFOLIO_TEST_MODE=0``, and unset as an install has it.

Red before N56's cure: ``backend.app.config.brim`` does not exist. It is imported when each test runs, never at collection,
so the rest of the category still runs. Pure: the environment through ``monkeypatch`` only.
"""

from __future__ import annotations

import importlib
from types import ModuleType

import pytest

from backend.app.config import is_test_mode
from backend.test_scripts.test_utils import print_section, print_success

#: The variable, written out: an operator sets this name, so the module's constant is checked against it.
BRIM_PREWARM_VARIABLE = "LIBREFOLIO_BRIM_PREWARM"
#: The test mode's variable, only ever set here, as the input of a case: ``is_test_mode()`` reads it.
TEST_MODE_VARIABLE = "LIBREFOLIO_TEST_MODE"
CONFIG_BRIM_MODULE = "backend.app.config.brim"

#: ``LIBREFOLIO_TEST_MODE`` as a case sets it, and the mode ``is_test_mode()`` must then report. ``None`` unsets it.
MODES = [
    pytest.param("1", True, id="test-mode"),
    pytest.param("0", False, id="production"),
    pytest.param(None, False, id="production-mode-unset"),
]

ON_WORDS = [
    pytest.param("1", id="1"),
    pytest.param("true", id="true"),
    pytest.param("yes", id="yes"),
    pytest.param("on", id="on"),
    pytest.param("TRUE", id="TRUE-any-case"),
    pytest.param("Yes", id="Yes-any-case"),
    pytest.param(" On ", id="On-stripped"),
    pytest.param("\tON\n", id="ON-stripped-of-tab-and-newline"),
]

OFF_WORDS = [
    pytest.param("0", id="0"),
    pytest.param("false", id="false"),
    pytest.param("no", id="no"),
    pytest.param("off", id="off"),
    pytest.param("FALSE", id="FALSE-any-case"),
    pytest.param("No", id="No-any-case"),
    pytest.param(" Off ", id="Off-stripped"),
    pytest.param("\toff\n", id="off-stripped-of-tab-and-newline"),
]

INVALID_VALUES = [
    pytest.param("2", id="2"),
    pytest.param("-1", id="minus-1"),
    pytest.param("y", id="y"),
    pytest.param("n", id="n"),
    pytest.param("enabled", id="enabled"),
    pytest.param("prewarm", id="prewarm"),
    pytest.param("true false", id="two-words"),
    pytest.param("1.0", id="1.0"),
]


def brim_config() -> ModuleType:
    """``backend.app.config.brim``, imported when the test runs: before N56's cure it does not exist, and only the tests
    that need it fail."""
    return importlib.import_module(CONFIG_BRIM_MODULE)


def _set_variable(monkeypatch: pytest.MonkeyPatch, name: str, value: str | None) -> None:
    """``None`` unsets ``name``; any string, the empty one included, sets it."""
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


def _set_the_mode_and_the_setting(monkeypatch: pytest.MonkeyPatch, test_mode: str | None, in_test_mode: bool, value: str | None) -> None:
    """The case's input, ``LIBREFOLIO_TEST_MODE`` and ``LIBREFOLIO_BRIM_PREWARM``; its premise checked through
    ``is_test_mode()``, the one reader of the mode."""
    _set_variable(monkeypatch, TEST_MODE_VARIABLE, test_mode)
    _set_variable(monkeypatch, BRIM_PREWARM_VARIABLE, value)
    assert is_test_mode() is in_test_mode, f"barrier: with {TEST_MODE_VARIABLE}={test_mode!r}, is_test_mode() is {is_test_mode()}, not {in_test_mode}: the case would test another mode"


def test_the_variable_is_librefolio_brim_prewarm():
    print_section("N56: the variable's name")
    assert brim_config().BRIM_PREWARM_VARIABLE == BRIM_PREWARM_VARIABLE, "the variable an operator sets is LIBREFOLIO_BRIM_PREWARM"
    print_success(f"✓ {BRIM_PREWARM_VARIABLE}")


@pytest.mark.parametrize(("test_mode", "in_test_mode"), MODES)
@pytest.mark.parametrize("value", [pytest.param(None, id="unset"), pytest.param("", id="empty"), pytest.param(" \t ", id="blank")])
def test_unset_or_blank_follows_the_test_mode(monkeypatch, value, test_mode, in_test_mode):
    """Unset, empty or blank: what ``is_test_mode()`` says — on for a test server, off for an install."""
    print_section(f"N56: {BRIM_PREWARM_VARIABLE}={value!r}, {TEST_MODE_VARIABLE}={test_mode!r}")
    config = brim_config()
    _set_the_mode_and_the_setting(monkeypatch, test_mode, in_test_mode, value)

    assert config.brim_prewarm_enabled() is is_test_mode(), f"{BRIM_PREWARM_VARIABLE}={value!r}: unset or blank, the prewarm follows is_test_mode(), here {is_test_mode()}"
    print_success(f"✓ {is_test_mode()}")


@pytest.mark.parametrize("value", ON_WORDS)
def test_an_on_word_turns_it_on_even_in_production(monkeypatch, value):
    """``1``, ``true``, ``yes``, ``on``, in any case and stripped: on, in production, where the default is off."""
    print_section(f"N56: {BRIM_PREWARM_VARIABLE}={value!r} in production")
    config = brim_config()
    _set_the_mode_and_the_setting(monkeypatch, "0", False, value)

    assert config.brim_prewarm_enabled() is True, f"{BRIM_PREWARM_VARIABLE}={value!r} turns the prewarm on, in production too"
    print_success("✓ True")


@pytest.mark.parametrize("value", OFF_WORDS)
def test_an_off_word_turns_it_off_even_in_test_mode(monkeypatch, value):
    """``0``, ``false``, ``no``, ``off``, in any case and stripped: off, in test mode, where the default is on."""
    print_section(f"N56: {BRIM_PREWARM_VARIABLE}={value!r} in test mode")
    config = brim_config()
    _set_the_mode_and_the_setting(monkeypatch, "1", True, value)

    assert config.brim_prewarm_enabled() is False, f"{BRIM_PREWARM_VARIABLE}={value!r} turns the prewarm off, in test mode too"
    print_success("✓ False")


@pytest.mark.parametrize(("test_mode", "in_test_mode"), MODES)
@pytest.mark.parametrize("value", INVALID_VALUES)
def test_any_other_value_raises_brim_config_error_naming_the_variable(monkeypatch, value, test_mode, in_test_mode):
    """A value outside the eight words is an error carrying the variable's name, never a guess either way, in either mode."""
    print_section(f"N56: {BRIM_PREWARM_VARIABLE}={value!r}, {TEST_MODE_VARIABLE}={test_mode!r}")
    config = brim_config()
    _set_the_mode_and_the_setting(monkeypatch, test_mode, in_test_mode, value)

    assert issubclass(config.BrimConfigError, ValueError), "BrimConfigError is a ValueError"
    with pytest.raises(config.BrimConfigError) as raised:
        config.brim_prewarm_enabled()
    assert raised.value.variable == BRIM_PREWARM_VARIABLE, f"the error names the variable in .variable: {raised.value.variable!r}"
    print_success(f"✓ {raised.value!r}")


def test_the_variable_and_the_test_mode_are_read_at_each_call(monkeypatch):
    """Read when called, never kept from an earlier call or from the import: a server restarted with a new value sees it."""
    print_section("N56: read at each call")
    config = brim_config()
    # (LIBREFOLIO_TEST_MODE, its premise, LIBREFOLIO_BRIM_PREWARM, the answer): every answer differs from the one before.
    calls = (("0", False, "1", True), ("0", False, "0", False), ("1", True, None, True), ("0", False, None, False), ("1", True, "1", True), ("1", True, "off", False))
    seen = []
    for test_mode, in_test_mode, value, _answer in calls:
        _set_the_mode_and_the_setting(monkeypatch, test_mode, in_test_mode, value)
        seen.append(config.brim_prewarm_enabled())

    assert seen == [answer for *_, answer in calls], f"each call reads the environment as it is then: {seen}"
    print_success(f"✓ {seen}")
